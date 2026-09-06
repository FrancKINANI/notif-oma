"""Omaping icon resolver - finds the best icon for a notification.

Priority order:
  1. User config (~/.config/omarchy/omaping/icons/)
  2. System icon theme (exact match)
  3. .desktop file lookup
  4. Website fetch (opt-in, cached)

CLI:
    omaping-icon --key web:app.slack.com --app "Google Chrome" \
                 --app-icon google-chrome --source app.slack.com \
                 --scheme dark [--fetch]

Prints a path, or nothing.
"""
import argparse
import idna
import glob
import ipaddress
import json
import os
import re
import socket
import sys
import time
import urllib.parse
import urllib.request

CONFIG = os.path.expanduser("~/.config/omarchy/omaping/icons")
CACHE = os.path.expanduser("~/.local/state/omarchy/omaping/icons")
INDEX = os.path.join(CACHE, "index.json")
RETRY_AFTER = 7 * 86400
TIMEOUT = 6
AGENT = "Mozilla/5.0 (X11; Linux x86_64) omaping"

ICON_DIRS = [
    os.path.expanduser("~/.local/share/icons"),
    "/usr/share/icons",
    "/usr/share/pixmaps",
]
APP_DIRS = [
    os.path.expanduser("~/.local/share/applications"),
    "/usr/share/applications",
]
EXTS = (".png", ".svg", ".jpg", ".jpeg", ".webp", ".ico")

NORM = 128


def is_mono_glyph(im, opaque: bool) -> bool:
    """Detect a one-colour glyph on transparency.

    Such icons are redrawn in the theme's text colour at render time.
    """
    if opaque:
        return False
    small = im.resize((32, 32))
    spread = 0
    lums = []
    for r, g, b, a in small.getdata():
        if a < 40:
            continue
        spread += max(r, g, b) - min(r, g, b)
        lums.append((r * 299 + g * 587 + b * 114) // 1000)
    n = len(lums)
    if n < 24:
        return False
    spread /= float(n)
    mean = sum(lums) / float(n)
    variance = sum((l - mean) ** 2 for l in lums) / float(n)
    coverage = n / float(32 * 32)
    return (spread < 26
            and variance < 1600
            and coverage < 0.82
            and (mean < 90 or mean > 170))


def normalise(path: str) -> str | None:
    """Render an icon to a consistent 128x128 canvas with rounded corners for opaque icons."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return path
    if path.lower().endswith(".svg"):
        return path
    try:
        im = Image.open(path).convert("RGBA")
    except Exception:
        return None
    if im.width < 8 or im.height < 8:
        return None

    box = im.getbbox()
    if box:
        im = im.crop(box)

    alpha = im.getchannel("A")
    opaque = alpha.getextrema()[0] > 250
    mono = is_mono_glyph(im, opaque)

    fill = 0.94 if opaque else 0.82
    side = int(NORM * fill)
    scale = side / float(max(im.width, im.height))
    im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))),
                   Image.LANCZOS)

    if opaque:
        mask = Image.new("L", im.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width - 1, im.height - 1],
                                               radius=int(min(im.size) * 0.22), fill=255)
        im.putalpha(mask)

    canvas = Image.new("RGBA", (NORM, NORM), (0, 0, 0, 0))
    canvas.paste(im, ((NORM - im.width) // 2, (NORM - im.height) // 2), im)

    dest = os.path.join(CACHE, "norm-" + slug(os.path.basename(path))
                        + ("-mono" if mono else "") + ".png")
    try:
        os.makedirs(CACHE, exist_ok=True)
        canvas.save(dest)
    except Exception:
        return None
    return dest


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", str(text or "").lower()).strip("-")


# 1. User config
def from_config(names: list[str]) -> str | None:
    for name in names:
        for ext in EXTS:
            path = os.path.join(CONFIG, slug(name) + ext)
            if os.path.isfile(path):
                return path
    return None


# 2. Icon theme
def from_icon_theme(names: list[str]) -> str | None:
    for name in names:
        for n in [str(name or "").strip(), slug(name)]:
            if not n:
                continue
            for base in ICON_DIRS:
                for pattern in ("%s/hicolor/512x512/apps/%s.*", "%s/hicolor/256x256/apps/%s.*",
                                "%s/hicolor/128x128/apps/%s.*", "%s/hicolor/scalable/apps/%s.*",
                                "%s/hicolor/64x64/apps/%s.*", "%s/*/*/apps/%s.*", "%s/%s.*"):
                    for hit in sorted(glob.glob(pattern % (base, n))):
                        if hit.lower().endswith(EXTS):
                            return hit
    return None


# 3. .desktop entries
def from_desktop_entries(names: list[str]) -> str | None:
    wanted = [slug(n) for n in names if slug(n)]
    if not wanted:
        return None
    for base in APP_DIRS:
        for path in glob.glob(base + "/*.desktop"):
            try:
                with open(path, errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            fields = {}
            for key in ("Name", "Icon", "StartupWMClass", "Exec"):
                m = re.search(r"^%s=(.+)$" % key, text, re.M)
                if m:
                    fields[key] = m.group(1).strip()
            if "Icon" not in fields:
                continue
            haystack = " ".join([slug(os.path.basename(path)[:-8]),
                                 slug(fields.get("Name", "")),
                                 slug(fields.get("StartupWMClass", "")),
                                 slug(fields.get("Exec", ""))])
            for want in wanted:
                if len(want) < 3:
                    continue
                if want in haystack.split("-") or ("-" + want + "-") in ("-" + haystack + "-"):
                    found = from_icon_theme([fields["Icon"]])
                    if found:
                        return found
                    if os.path.isabs(fields["Icon"]) and os.path.isfile(fields["Icon"]):
                        return fields["Icon"]
    return None


# 4. Website fetch
GENERIC_NAMES = {
    "messages", "message", "mail", "email", "phone", "dialer", "camera",
    "clock", "alarm", "calendar", "settings", "files", "photos", "gallery",
    "music", "notes", "weather", "contacts", "downloads", "screenshot",
    "recorder", "voice", "browser", "news", "wallet", "health", "home",
}


def load_index() -> dict:
    try:
        with open(INDEX) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_index(data: dict) -> None:
    os.makedirs(CACHE, exist_ok=True)
    tmp = INDEX + ".part"
    with open(tmp, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    os.replace(tmp, INDEX)


ALLOWED_SCHEMES = ("http", "https")
HOSTNAME = re.compile(
    r"^(?=.{1,253}$)"
    r"(?!\d+$)"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$")


def public_hostname(host: str) -> str | None:
    h = str(host or "").strip().lower().rstrip(".")
    # Decode punycode to prevent homograph attacks
    try:
        h = idna.decode(h)
    except idna.IDNAError:
        return None
    if not HOSTNAME.match(h):
        return None
    if h.split(".")[-1].isdigit():
        return None
    return h


def reachable(url: str) -> str | None:
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return None
    if parts.scheme not in ALLOWED_SCHEMES:
        return None
    if not public_hostname(parts.hostname):
        return None
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or 0, proto=socket.IPPROTO_TCP)
    except (OSError, ValueError):
        return None
    for info in infos:
        try:
            if not ipaddress.ip_address(info[4][0]).is_global:
                return None
        except ValueError:
            return None
    return url


class GuardedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.redirect_count = 0
        self.max_redirects = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not reachable(newurl):
            return None
        self.redirect_count += 1
        if self.redirect_count > self.max_redirects:
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)

    def http_error_302(self, req, fp, code, msg, headers):
        self.redirect_count = 0
        return super().http_error_302(req, fp, code, msg, headers)
    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302


OPENER = urllib.request.build_opener(GuardedRedirect)


def get(url: str) -> tuple[bytes, str]:
    if not reachable(url):
        raise ValueError("refusing to fetch " + str(url)[:80])
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with OPENER.open(req, timeout=TIMEOUT) as r:
        return r.read(600000), r.geturl()


def icon_links(html: str, base: str, scheme: str) -> list[str]:
    out, themed = [], []
    for m in re.finditer(r"<link\s+([^>]+)>", html, re.I):
        attrs = dict(re.findall(r'(\w[\w-]*)\s*=\s*["\']([^"\']*)["\']', m.group(1)))
        rel = (attrs.get("rel") or "").lower()
        href = attrs.get("href")
        if not href:
            continue
        media = (attrs.get("media") or "").lower()
        url = urllib.parse.urljoin(base, href)
        if "apple-touch-icon" in rel:
            (themed if scheme in media else out).append((0, url))
        elif "icon" in rel and "mask" not in rel:
            size = attrs.get("sizes", "")
            n = 1
            try:
                n = -int(size.split("x")[0])
            except Exception:
                pass
            (themed if scheme in media else out).append((n, url))
        elif rel == "manifest":
            out.append((50, ("manifest", url)))
    return [u for _, u in sorted(themed)] + [u for _, u in sorted(out)]


def from_manifest(url: str, base: str) -> list[str]:
    try:
        raw, _ = get(url)
        data = json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        return []
    icons = data.get("icons") or []
    def area(i):
        try:
            return -int(str(i.get("sizes", "0x0")).split("x")[0])
        except Exception:
            return 0
    return [urllib.parse.urljoin(base, i["src"]) for i in sorted(icons, key=area)
            if i.get("src")]


def fetch_site(host: str, scheme: str) -> str | None:
    base = "https://" + host + "/"
    candidates = []
    try:
        raw, final = get(base)
        html = raw.decode("utf-8", "replace")
        for entry in icon_links(html, final, scheme):
            if isinstance(entry, tuple) and entry[0] == "manifest":
                candidates.extend(from_manifest(entry[1], final))
            else:
                candidates.append(entry)
    except Exception:
        pass
    candidates.append(urllib.parse.urljoin(base, "/favicon.ico"))

    os.makedirs(CACHE, exist_ok=True)
    for url in candidates[:6]:
        try:
            data, _ = get(url)
        except Exception:
            continue
        if len(data) < 80:
            continue
        ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
        if ext not in EXTS:
            ext = ".png"
        dest = os.path.join(CACHE, f"web-{slug(host)}-{scheme}{ext}")
        try:
            with open(dest, "wb") as f:
                f.write(data)
        except OSError:
            continue
        return dest
    return None


def host_names(source: str) -> list[str]:
    s = public_hostname(source)
    if not s:
        return []
    labels = [l for l in s.split(".") if l not in ("www", "app", "web", "my", "m")]
    names = [s]
    if len(labels) >= 2:
        names.append(labels[-2])
    if labels:
        names.append(labels[0])
    return names


SECOND_LEVEL = ("co", "com", "org", "net", "ac", "gov", "edu")


def hosts_to_try(host: str) -> list[str]:
    labels = [l for l in str(host or "").split(".") if l]
    out = [host]
    if len(labels) > 2:
        keep = 3 if labels[-2] in SECOND_LEVEL else 2
        root = ".".join(labels[-keep:])
        if root != host:
            out.append(root)
    return out


def resolve(args) -> tuple[str | None, str]:
    web = host_names(args.source)
    app = [n for n in [args.app_icon, args.source, args.app] if n]

    hit = from_config(web + app + ([args.key] if args.key else []))
    if hit:
        return hit, "from_config"

    if web:
        hit = from_icon_theme(web)
        if hit:
            return hit, "from_icon_theme:web"

    if args.app_icon and not web:
        hit = from_icon_theme([args.app_icon])
        if hit:
            return hit, "from_icon_theme:hint"

    if args.fetch and not web:
        bare = slug(args.source) or slug(args.app)
        if bare and "." not in bare and len(bare) >= 3:
            index = load_index()
            note = index.get(bare) or {}
            cached = note.get(args.scheme)
            if cached and os.path.isfile(cached):
                return cached, "cache"
            if bare in GENERIC_NAMES:
                pass
            elif note.get("failed_at", 0) < time.time() - RETRY_AFTER:
                for tld in (".com", ".io", ".app", ".dev"):
                    hit = fetch_site(bare + tld, args.scheme)
                    if hit:
                        note[args.scheme] = hit
                        index[bare] = note
                        save_index(index)
                        return hit, "guessed:" + bare + tld
                note["failed_at"] = time.time()
                index[bare] = note
                save_index(index)

    if args.fetch and web:
        index = load_index()
        for host in hosts_to_try(web[0]):
            note = index.get(host) or {}
            cached = note.get(args.scheme)
            if cached and os.path.isfile(cached):
                return cached, "cache"
            if note.get("failed_at", 0) > time.time() - RETRY_AFTER:
                continue
            hit = fetch_site(host, args.scheme)
            note.setdefault("failed_at", 0)
            if hit:
                note[args.scheme] = hit
            else:
                note["failed_at"] = time.time()
            index[host] = note
            save_index(index)
            if hit:
                return hit, "fetched:" + host

    for step in (from_icon_theme, from_desktop_entries):
        hit = step(app)
        if hit:
            return hit, step.__name__ + ":app"
    return None, "none"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default="")
    ap.add_argument("--app", default="")
    ap.add_argument("--app-icon", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--scheme", default="dark", choices=["dark", "light"])
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--why", action="store_true", help="print where it came from")
    args = ap.parse_args()
    path, how = resolve(args)
    if path:
        path = normalise(path)
    if path:
        sys.stdout.write(path + ("\t" + how if args.why else ""))
    elif args.why:
        sys.stdout.write("\t" + how)
    return 0


if __name__ == "__main__":
    sys.exit(main())