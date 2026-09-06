"""Omaping demo - realistic notification scenes for testing and recording.

CLI:
    omaping-demo              the default scene, paced for watching
    omaping-demo --fast       same scene, tighter, for a recording
    omaping-demo --scene chat only one part of it
    omaping-demo --scene interactive   codes, links and the sender's buttons
    omaping-demo --scene routing       where a click sends you, per source
    omaping-demo --scene reply         inline reply, against a stand-in phone
    omaping-demo --list       what scenes there are
    omaping-demo --loop       keep going until interrupted
    omaping-demo --replay N   re-send last N real notifications from the store

The senders match what actually notifies this desktop - Chrome announcing web
apps via leading anchors, KDE Connect naming a device in the summary, terminals,
backup jobs - because those shapes are what grouping and markup parsing handle.
"""
import argparse
import json
import os
import random
import subprocess
import sys
import time

# Store and icon binaries are installed alongside this package.
def _bin(name: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", name)


STORE = _bin("omaping-store")
ICON = _bin("omaping-icon")

# Chrome puts a link to the origin on the front of every web notification.
def web(host: str, body: str) -> str:
    return f'<a href="https://{host}/">{host}</a>\n\n{body}'


SCENES = {
    "chat": [
        dict(web="app.slack.com", summary="#design",
             body="Gurbinder: new spacing is in Figma, worth a look before standup"),
        dict(web="web.whatsapp.com", summary="Seif Lotfy",
             body="I have to show you this thing I built, are you around later?"),
        dict(web="app.slack.com", summary="Dominic",
             body="can you sanity check the quota panel numbers?"),
        dict(web="x.com", summary="Elon Musk",
             body="replied to your post: this is the part everyone gets wrong"),
        dict(web="app.slack.com", summary="#design", gap=0.7,
             body="Gurbinder: pushed the spacing pass, take a look"),
        dict(web="app.slack.com", summary="#design", gap=0.7,
             body="Dominic: the two-line ones finally breathe"),
        dict(web="app.slack.com", summary="#design", gap=0.7,
             body="Gurbinder: one more go at the icon size and I think that is it"),
        dict(web="app.slack.com", summary="#design",
             body="Dominic: shipping it before standup then"),
    ],
    "work": [
        dict(web="linear.app", summary="AXM-412 assigned to you",
             body="Deck stutters when a notification lands during hover"),
        dict(web="github.com", summary="Review requested",
             body="axiomhq/axiom-web #1841 - <b>tighten the toast layout</b>"),
        dict(app="kitty", icon="kitty", summary="Tests passed",
             body="412 passed, 0 failed in <b>2m 14s</b>"),
        dict(web="app.slack.com", summary="#releases",
             body="0.43 tagged and pushed"),
    ],
    "system": [
        dict(app="Omarchy", icon="system-software-update", summary="Updates available",
             body="14 packages, including linux 6.17.4 and hyprland 0.52"),
        dict(app="Snapshots", icon="LimineSnapperSync", summary="Snapshot complete",
             body="pre-update root snapshot written in 4s"),
        dict(app="ApexShot", icon="apexshot", summary="Screenshot saved",
             body="~/Screenshots/ApexShot-2026-09-03_22-41-08.png"),
    ],
    "routing": [],
    "reply": [],
    "interactive": [
        dict(web="app.slack.com", summary="#design",
             body="Gurbinder: latest build is up, take a look https://axiom.co/preview/1841"),
        dict(web="accounts.google.com", summary="Google",
             body="Your verification code is 482913. Do not share it with anyone."),
        dict(app="KDE Connect", summary="WhatsApp",
             body="Seif Lotfy: are you around later?",
             actions=["read=Mark as read"]),
        dict(app="KDE Connect", summary="Messages",
             body="G-728341 is your Google verification code"),
        dict(app="KDE Connect", summary="Discord",
             body="Ravi: here is my new number, +44 7911 123456",
             actions=["read=Mark as read"]),
        dict(app="kitty", icon="kitty", summary="Tests passed",
             body="412 passed, 0 failed in 2m 14s"),
        dict(web="github.com", summary="Review requested",
             body="axiomhq/axiom \u00b7 sub-second histograms (#4412)"),
    ],
    "personal": [
        dict(app="Spotify", icon="spotify", summary="Now playing",
             body="Money for Nothing - Dire Straits"),
        dict(web="x.com", summary="3 people liked your post",
             body="\u201cthe notification daemon is the whole desktop in miniature\u201d"),
        dict(web="web.whatsapp.com", summary="Seif Lotfy",
             body="seriously, you are going to want to see this one"),
    ],
}


def slug(text: str) -> str:
    out = ""
    for ch in str(text or "").lower():
        out += ch if ch.isalnum() else "-"
    return "-".join(part for part in out.split("-") if part)


def identity(n: dict) -> dict:
    """Derive the daemon's grouping key and icon-resolver fields for a notification."""
    if n.get("web"):
        return dict(key="web:" + n["web"], source=n["web"],
                    app="Google Chrome", icon="google-chrome")
    app = n.get("app") or "notify-send"
    return dict(key="app:" + slug(app), source=app, app=app, icon=n.get("icon") or "")


def scheme() -> str:
    path = os.path.expanduser("~/.local/state/omarchy/current/theme/colors.toml")
    try:
        with open(path) as fh:
            for line in fh:
                if line.strip().startswith("mode"):
                    return "light" if "light" in line else "dark"
    except OSError:
        pass
    return "dark"


def warm(items: list[dict]) -> None:
    """Pre-resolve icons so the demo doesn't show letter tiles on first arrival."""
    seen, wanted = set(), []
    for n in items:
        who = identity(n)
        if who["key"] in seen:
            continue
        seen.add(who["key"])
        wanted.append(who)
    if not wanted:
        return
    print(f"warming {len(wanted)} icons...", file=sys.stderr)
    for who in wanted:
        subprocess.run([ICON, "--key", who["key"], "--source", who["source"],
                        "--app", who["app"], "--app-icon", who["icon"],
                        "--scheme", scheme(), "--fetch"],
                       capture_output=True, check=False)


DEFAULT = ["chat", "work", "personal", "system"]


# Max length for notify-send arguments
_MAX_ARG_LEN = 1024

def _sanitize_arg(s: str) -> str:
    """Sanitize string for notify-send: remove control chars, limit length."""
    if not s:
        return ""
    # Remove control characters except newline/tab
    s = ''.join(ch for ch in s if ch == '\n' or ch == '\t' or ord(ch) >= 32)
    return s[:_MAX_ARG_LEN]

def send(n: dict, timeout: int | None = None) -> None:
    who = identity(n)
    body = _sanitize_arg(n.get("body", ""))
    if n.get("web"):
        body = web(n["web"], body)
    cmd = ["notify-send", "-a", _sanitize_arg(who["app"]), _sanitize_arg(n["summary"]), body]
    if who["icon"]:
        cmd += ["-i", _sanitize_arg(who["icon"]), "-h", "string:desktop-entry:" + _sanitize_arg(who["icon"])]
    if n.get("urgency"):
        cmd += ["-u", _sanitize_arg(str(n["urgency"]))]
    if timeout is not None:
        cmd += ["-t", _sanitize_arg(str(timeout))]
    for action in n.get("actions", []):
        cmd += ["-A", _sanitize_arg(action)]
    if n.get("actions"):
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.run(cmd, check=False)


def replay(limit: int, match: str) -> list[dict]:
    """Re-send real notifications from the store."""
    try:
        raw = subprocess.run([STORE, "history", str(limit)],
                             capture_output=True, text=True, check=False).stdout
        rows = json.loads(raw or "[]")
    except Exception:
        rows = []
    needle = (match or "").lower()
    out = []
    for r in reversed(rows):
        if needle:
            blob = " ".join(str(r.get(k) or "") for k in
                            ("app", "source", "summary", "body")).lower()
            if needle not in blob:
                continue
        out.append(dict(app=r.get("app") or "notify-send",
                        icon=r.get("appIcon") or "",
                        summary=r.get("summary") or "",
                        body=r.get("rawBody") or r.get("body") or ""))
    return out


def open_web_hosts() -> list[str]:
    """Return hosts that have an Omarchy web-app window open (class contains host)."""
    try:
        raw = subprocess.run(["hyprctl", "-j", "clients"],
                             capture_output=True, text=True, check=False).stdout
        clients = json.loads(raw or "[]")
    except Exception:
        return []
    hosts = []
    for c in clients:
        wm = str(c.get("class") or "")
        if not wm.startswith("chrome-"):
            continue
        host = wm[len("chrome-"):].split("__")[0]
        if "." in host and host not in hosts:
            hosts.append(host)
    return hosts


CLOSED_CANDIDATES = ("linear.app", "notion.com", "app.slack.com", "github.com",
                     "figma.com", "example.com")


def routing_scene() -> list[dict]:
    live = open_web_hosts()
    items = []
    for host in live[:2]:
        items.append(dict(web=host, summary=host.split(".")[0].title(),
                          body=f"click me: the window showing {host} should come forward",
                          expect=f"focus the existing {host} window"))
    closed = next((h for h in CLOSED_CANDIDATES if h not in live), "example.com")
    items.append(dict(web=closed, summary=closed.split(".")[0].title(),
                      body=f"click me: nothing is showing {closed}, so it should open",
                      expect=f"open https://{closed}/ (no window for it)"))
    items.append(dict(app="kitty", icon="kitty", summary="Tests passed",
                      body="click me: a local app, so its own default action runs",
                      expect="the sender's own default action"))
    return items


FAKE = os.path.join(os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")),
                    "omarchy", "omaping", "kdeconnect-fake.json")
FAKE_LOG = FAKE.replace(".json", ".log")


def reply_scene() -> list[dict]:
    who, message = "Seif Lotfy", "did you get the build working in the end?"
    os.makedirs(os.path.dirname(FAKE), exist_ok=True)
    with open(FAKE, "w") as fh:
        json.dump([dict(appName="WhatsApp", title=who, text=message,
                        isConversation=True)], fh)
    return [dict(app="KDE Connect", summary="WhatsApp",
                 body=f"{who}: {message}")]


def clear() -> None:
    subprocess.run(["omarchy-shell", "-q", "omaping", "clear"], check=False)


def run_scenes(scenes: list[str], gap: float, timeout: int | None, shuffle: bool) -> None:
    for name in scenes:
        items = list(SCENES[name])
        if shuffle:
            random.shuffle(items)
        for n in items:
            send(n, timeout)
            time.sleep(min(gap, n["gap"]) if "gap" in n else gap)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", action="append", choices=sorted(SCENES),
                    help="just this one (repeatable); default is all of them")
    ap.add_argument("--fast", action="store_true", help="tighter pacing, for recording")
    ap.add_argument("--gap", type=float, help="seconds between notifications")
    ap.add_argument("--timeout", type=int, help="how long each stays up, ms")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--shuffle", action="store_true")
    ap.add_argument("--keep", action="store_true", help="do not clear first")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--replay", type=int, metavar="N",
                    help="re-send the last N real notifications from the store")
    ap.add_argument("--match", help="only replay ones mentioning this")
    args = ap.parse_args()

    if args.list:
        for name, items in sorted(SCENES.items()):
            print(f"{name:<9} {len(items)} notifications")
        return 0

    gap = args.gap if args.gap is not None else (0.9 if args.fast else 3.2)
    scenes = args.scene or DEFAULT

    if args.scene and "reply" in args.scene:
        scenes = [n for n in scenes if n != "reply"]
        SCENES["reply"] = reply_scene()
        scenes.append("reply")
        print("hover the card, press Reply, type something and hit Enter.", file=sys.stderr)
        print(f"it goes to {FAKE_LOG} - not to anyone.", file=sys.stderr)

    if args.scene and "routing" in args.scene:
        scenes = [n for n in scenes if n != "routing"]
        SCENES["routing"] = routing_scene()
        scenes.append("routing")
        print("what each one should do when you click it:", file=sys.stderr)
        for n in SCENES["routing"]:
            print(f"   {n['summary']:<22} {n['expect']}", file=sys.stderr)

    items = []
    for name in scenes:
        items += SCENES[name]
    if not args.replay:
        warm(items)

    if not args.keep:
        clear()
        time.sleep(0.4)

    if args.replay:
        items = replay(args.replay, args.match)
        if not items:
            print("nothing in the store matches", file=sys.stderr)
            return 1
        print(f"replaying {len(items)}")
        for n in items:
            send(n, args.timeout)
            time.sleep(gap)
        return 0

    try:
        run_scenes(scenes, gap, args.timeout, args.shuffle)
        while args.loop:
            time.sleep(gap * 2)
            run_scenes(scenes, gap, args.timeout, args.shuffle)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())