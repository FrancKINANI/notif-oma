"""Omaping store - notification persistence layer.

Commands:
    put              read one notification JSON on stdin, write it to live/
    close KEY WHY    move live/KEY.json into history/, trimmed to size and age
    drop KEY         forget a live notification without recording it
    restore          print the live notifications, oldest first
    history [N]      print the newest N history entries, newest first
    tidy             drop history past its age, and icons nothing has wanted
    quiet            print the quiet state: snoozed sources, and silencing
    quiet-save       read the quiet state as JSON on stdin
    held [N]         print the newest N that were never shown, newest first
    forget-all       empty the history

Everything lives in ~/.local/state/omarchy/omaping/. It is state, not cache:
what you were told should survive a `rm -rf ~/.cache`. History is a log to
read back, not a queue to work through. Keeping it as one file per
notification means a half-written entry costs one notification instead of the
lot, and the daemon can be killed at any point without needing a save step.
"""
import json
import os
import sys
import time

ROOT = os.path.expanduser("~/.local/state/omarchy/omaping")
LIVE = os.path.join(ROOT, "live")
HISTORY = os.path.join(ROOT, "history")
ICONS = os.path.join(ROOT, "icons")
QUIET = os.path.join(ROOT, "quiet.json")
SNOOZES = os.path.join(ROOT, "snoozes.json")     # legacy

# History limits: 7 days or 200 entries, whichever comes first.
HISTORY_MAX = 200
HISTORY_DAYS = 7

# Resolved icons expire after 60 days unused.
ICON_DAYS = 60


def ensure():
    for d in (LIVE, HISTORY, ICONS):
        os.makedirs(d, exist_ok=True)


def safe(name: str) -> str:
    """Sanitize a key for use in a filesystem path."""
    return "".join(c for c in str(name) if c.isalnum() or c in "-_.")[:120]


def write_json(path: str, value) -> None:
    tmp = path + ".part"
    with open(tmp, "w") as f:
        json.dump(value, f, separators=(",", ":"))
    os.replace(tmp, path)
    os.chmod(path, 0o600)


def read_json(path: str):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def cmd_put() -> int:
    entry = json.load(sys.stdin)
    key = safe(entry.get("key", ""))
    if not key:
        return 1
    write_json(os.path.join(LIVE, key + ".json"), entry)
    return 0


def cmd_close(key: str, why: str) -> int:
    key = safe(key)
    src = os.path.join(LIVE, key + ".json")
    entry = read_json(src)
    if entry is None:
        return 0
    # Don't store rawBody in history (may contain tokens, codes, private URLs)
    entry.pop("rawBody", None)
    entry["closed_ts"] = time.time()
    entry["closed_reason"] = why
    stamp = "%013d" % int(entry["closed_ts"] * 1000)
    write_json(os.path.join(HISTORY, f"{stamp}-{key}.json"), entry)
    try:
        os.remove(src)
    except OSError:
        pass
    trim_history()
    return 0


def cmd_drop(key: str) -> int:
    try:
        os.remove(os.path.join(LIVE, safe(key) + ".json"))
    except OSError:
        pass
    return 0


def trim_history() -> int:
    """Remove history entries past age or count limits."""
    files = sorted(f for f in os.listdir(HISTORY) if f.endswith(".json"))
    cutoff = (time.time() - HISTORY_DAYS * 86400) * 1000
    doomed = set(files[:-HISTORY_MAX]) if len(files) > HISTORY_MAX else set()
    for name in files:
        try:
            if int(name.split("-", 1)[0]) < cutoff:
                doomed.add(name)
        except ValueError:
            pass
    for name in doomed:
        try:
            os.remove(os.path.join(HISTORY, name))
        except OSError:
            pass
    return len(doomed)


def trim_icons() -> int:
    """Remove resolved icons not accessed in ICON_DAYS."""
    cutoff = time.time() - ICON_DAYS * 86400
    dropped = 0
    for name in os.listdir(ICONS):
        path = os.path.join(ICONS, name)
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
                dropped += 1
        except OSError:
            pass
    return dropped


def cmd_tidy() -> int:
    sys.stdout.write(f"{trim_history()} history, {trim_icons()} icons")
    return 0


def listing(directory: str, limit: int | None = None, newest_first: bool = False):
    files = sorted(f for f in os.listdir(directory) if f.endswith(".json"))
    if newest_first:
        files.reverse()
    if limit:
        files = files[:limit]
    out = []
    for name in files:
        entry = read_json(os.path.join(directory, name))
        if entry is not None:
            out.append(entry)
    return out


HELD_REASONS = ("snoozed", "silenced")


def cmd_held(limit: int) -> int:
    out = []
    for name in sorted(os.listdir(HISTORY), reverse=True):
        if not name.endswith(".json"):
            continue
        entry = read_json(os.path.join(HISTORY, name))
        if entry is not None and entry.get("closed_reason") in HELD_REASONS:
            out.append(entry)
            if len(out) >= limit:
                break
    json.dump(out, sys.stdout, separators=(",", ":"))
    return 0


def cmd_forget_all() -> int:
    for name in os.listdir(HISTORY):
        try:
            os.remove(os.path.join(HISTORY, name))
        except OSError:
            pass
    return 0


def cmd_quiet_save() -> int:
    value = json.load(sys.stdin)
    if not isinstance(value, dict):
        return 1
    write_json(QUIET, value)
    return 0


def read_quiet():
    state = read_json(QUIET)
    if state is not None:
        return state
    # Legacy: snoozes used to live in a separate file.
    return {"snoozes": read_json(SNOOZES) or {}}


def main() -> int:
    ensure()
    args = sys.argv[1:]
    if not args:
        return 2
    verb = args[0]
    if verb == "put":
        return cmd_put()
    if verb == "close":
        return cmd_close(args[1], args[2] if len(args) > 2 else "")
    if verb == "drop":
        return cmd_drop(args[1])
    if verb == "restore":
        json.dump(listing(LIVE), sys.stdout, separators=(",", ":"))
        return 0
    if verb == "history":
        limit = int(args[1]) if len(args) > 1 else 60
        json.dump(listing(HISTORY, limit, newest_first=True), sys.stdout,
                  separators=(",", ":"))
        return 0
    if verb == "held":
        return cmd_held(int(args[1]) if len(args) > 1 else 60)
    if verb == "forget-all":
        return cmd_forget_all()
    if verb == "quiet":
        json.dump(read_quiet(), sys.stdout, separators=(",", ":"))
        return 0
    if verb == "quiet-save":
        return cmd_quiet_save()
    if verb == "tidy":
        return cmd_tidy()
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        pass