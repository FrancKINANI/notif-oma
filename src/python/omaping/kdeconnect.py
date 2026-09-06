"""Omaping KDE Connect bridge - matches desktop notifications to phone reply channels.

CLI:
    omaping-kdeconnect list                     every phone notification, as JSON
    omaping-kdeconnect find APP BODY            the object path of a repliable match
    omaping-kdeconnect reply PATH TEXT          send a reply back to the phone

KDE Connect posts phone notifications to the desktop bus like any other app,
but also keeps an object per notification on its own bus with the part the
spec has no room for: a replyId, and a sendReply method that puts text back
into the conversation on the phone. Matching the two is by app name and body
text, because the desktop notification carries no handle to the object.
"""
import json
import os
import subprocess
import sys
import time

BUS = "org.kde.kdeconnect"
IFACE = "org.kde.kdeconnect.device.notifications.notification"

# Stand-in phone for demos/tests. The real reply channel needs a device on the
# other end holding a conversation open. A fixture file declares notifications
# that behave like repliable ones; replies are written to a log instead of sent.
STATE = os.path.join(os.environ.get("XDG_STATE_HOME",
                                    os.path.expanduser("~/.local/state")),
                     "omarchy", "omaping")
FIXTURE = os.path.join(STATE, "kdeconnect-fake.json")
REPLY_LOG = os.path.join(STATE, "kdeconnect-fake.log")
FIXTURE_MAX_AGE = 30 * 60


def fixture() -> list[dict]:
    try:
        if time.time() - os.path.getmtime(FIXTURE) > FIXTURE_MAX_AGE:
            return []
        with open(FIXTURE) as fh:
            rows = json.load(fh)
    except Exception:
        return []
    out = []
    for i, row in enumerate(rows):
        row = dict(row)
        row.setdefault("replyId", f"demo-{i}")
        row.setdefault("ticker", f"{row.get('title', '')}: {row.get('text', '')}")
        row["path"] = f"fake:{i}"
        out.append(row)
    return out


def run(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True, check=False).stdout


def paths() -> list[str]:
    tree = run(["busctl", "--user", "tree", BUS])
    out = []
    for line in tree.splitlines():
        for token in line.split():
            if "/notifications/" in token and token.rsplit("/", 1)[-1].isdigit():
                out.append(token)
    return out


def properties(path: str) -> dict | None:
    raw = run(["busctl", "--user", "--json=short", "call", BUS, path,
               "org.freedesktop.DBus.Properties", "GetAll", "s", IFACE])
    try:
        data = json.loads(raw)["data"][0]
    except Exception:
        return None
    return {k: v.get("data") for k, v in data.items()}


def listing() -> list[dict]:
    out = list(fixture())
    for path in paths():
        props = properties(path)
        if props is None:
            continue
        props["path"] = path
        out.append(props)
    return out


SMART = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2026": "..."
}


def normalise(text: str) -> str:
    """Comparable text: replace typographic chars, collapse whitespace, lowercase."""
    out = str(text or "")
    for fancy, plain in SMART.items():
        out = out.replace(fancy, plain)
    return " ".join(out.split()).lower()


def find(app: str, body: str) -> dict | None:
    """Find the KDE Connect object matching a desktop notification.

    Matches on app name and body text. Body first: two notifications from the
    same app are common; two with identical text is not.
    """
    want_app, want_body = normalise(app), normalise(body)
    best = None
    for note in listing():
        if not note.get("replyId"):
            continue
        ticker, text = normalise(note.get("ticker", "")), normalise(note.get("text", ""))
        # Require exact match on normalized body to prevent spoofing
        if want_body and want_body == text:
            return note
        # Fallback: exact app name match only if no body match
        if want_app and normalise(note.get("appName", "")) == want_app and best is None:
            best = note
    return best


def main() -> int:
    if len(sys.argv) < 2:
        return 2
    verb = sys.argv[1]

    if verb == "list":
        json.dump(listing(), sys.stdout, separators=(",", ":"))
        return 0

    if verb == "find":
        app = sys.argv[2] if len(sys.argv) > 2 else ""
        body = sys.argv[3] if len(sys.argv) > 3 else ""
        note = find(app, body)
        if note:
            json.dump({"path": note["path"], "title": note.get("title", ""),
                       "appName": note.get("appName", "")}, sys.stdout,
                      separators=(",", ":"))
        return 0

    if verb == "reply":
        path, text = sys.argv[2], sys.argv[3]
        if not text.strip():
            return 1
        if path.startswith("fake:"):
            os.makedirs(STATE, exist_ok=True)
            with open(REPLY_LOG, "a") as fh:
                fh.write(f"{time.strftime('%FT%T')}\t{path}\t{text}\n")
            sys.stdout.write("sent to the demo log")
            return 0
        result = subprocess.run(["busctl", "--user", "call", BUS, path, IFACE,
                                 "sendReply", "s", text],
                                capture_output=True, text=True, check=False)
        if result.returncode != 0:
            sys.stdout.write(result.stderr.strip())
            return result.returncode
        subprocess.run(["busctl", "--user", "call", BUS, path, IFACE, "dismiss"],
                       capture_output=True, text=True, check=False)
        sys.stdout.write("sent")
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())