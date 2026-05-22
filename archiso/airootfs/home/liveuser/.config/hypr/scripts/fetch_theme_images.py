#!/usr/bin/env python3
"""
Fetches theme-appropriate images from Wikimedia Commons.

For each theme runs a set of curated search queries against the Commons API,
downloads up to MAX_PER_THEME unique images (scaled to 1920px wide), and
caches them under themes/<name>/images/. Idempotent — skips files already
on disk.

Usage:
    fetch_theme_images.py                 # fetch all themes
    fetch_theme_images.py nature green    # fetch named themes only
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

THEMES_DIR = Path.home() / ".config/hypr/themes"
API = "https://commons.wikimedia.org/w/api.php"
UA = "MalekHyprlandThemes/1.0 (malek@malekhammoud.com)"

THEMES = {
    "nature":  ["mountain landscape", "alpine valley", "waterfall scenery",
                "ancient forest", "desert canyon", "rainforest vista",
                "fjord landscape", "savanna sunrise"],
    "cyan":    ["glacier landscape", "iceberg ocean", "antarctic vista",
                "turquoise lagoon", "blue ice cave", "frozen lake"],
    "blue":    ["deep ocean", "starry night sky", "blue hour cityscape",
                "stormy sea", "milky way panorama", "blue mountain dusk"],
    "teal":    ["tropical lagoon", "caribbean beach", "coral reef",
                "shallow turquoise sea", "hot spring teal"],
    "red":     ["red rock canyon", "lava flow", "autumn maple forest",
                "red sunset sky", "mars landscape"],
    "orange":  ["sahara dune sunset", "autumn aspen forest", "valley of fire",
                "orange sunrise", "monument valley"],
    "gold":    ["wheat field sunset", "sahara golden hour", "tuscany sunset",
                "golden savanna", "namibia dunes"],
    "green":   ["irish countryside", "tropical jungle", "moss forest",
                "rice terraces", "iceland mossy", "amazon canopy"],
    "purple":  ["lavender field", "aurora borealis purple",
                "purple twilight mountain", "wisteria garden"],
    "magenta": ["cherry blossom landscape", "pink lake",
                "magenta sunset sky", "bougainvillea archway"],
    "gaming":  ["volcano eruption", "lava river", "burning landscape",
                "red nebula", "mars surface", "supercar red",
                "red aurora", "crimson sunset", "red lightning",
                "magma flow", "ferrari", "esports arena lights"],
    "coding":  ["milky way galaxy", "blue nebula", "cyberpunk skyline night",
                "starry night sky", "aurora borealis blue", "deep ocean abyss",
                "tokyo night city", "blue ice cave", "server room blue",
                "data center blue lights", "planetarium"],
}

MAX_PER_THEME = 40
MIN_SOURCE_WIDTH = 2880  # matches the user's 1080p @1.5x scale render canvas
TARGET_WIDTH = 3840      # 4K thumb — sharp at any scale, Wikimedia generates on demand


def api_get(params):
    params = {**params, "format": "json", "formatversion": "2"}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def search_images(query, limit=20):
    """Search Commons file namespace for `query`, return [(title, thumburl)]."""
    out = []
    try:
        data = api_get({
            "action": "query",
            "generator": "search",
            "gsrsearch": f"{query} filetype:bitmap",
            "gsrnamespace": "6",
            "gsrlimit": str(limit),
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "iiurlwidth": str(TARGET_WIDTH),
        })
    except Exception as e:
        print(f"    ! search '{query}' failed: {e}")
        return out
    pages = (data.get("query") or {}).get("pages") or []
    for p in pages:
        info = (p.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        w = info.get("width", 0)
        mime = info.get("mime", "")
        if not url or w < MIN_SOURCE_WIDTH:
            continue
        if mime not in ("image/jpeg", "image/png"):
            continue
        out.append((p["title"], url))
    return out


def safe_name(title):
    n = title.replace("File:", "").replace(" ", "_")
    n = "".join(c for c in n if c.isalnum() or c in "._-")
    # ensure jpg extension for any html-encoded oddities
    if not n.lower().endswith((".jpg", ".jpeg", ".png")):
        n += ".jpg"
    return n


def download(url, dest, max_retries=4):
    # Only consider it cached if the file is plausibly hi-res (>= 800KB after the 4K bump)
    if dest.exists() and dest.stat().st_size > 800_000:
        return f"skip {dest.name}"
    delay = 1.5
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            if len(data) < 30_000:
                return f"tiny {dest.name} ({len(data)}B) — skipped"
            dest.write_bytes(data)
            return f"ok   {dest.name} ({len(data)//1024}KB)"
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            return f"err  {dest.name}: HTTP {e.code}"
        except Exception as e:
            return f"err  {dest.name}: {e}"
    return f"err  {dest.name}: gave up after retries"


def fetch_theme(theme):
    out_dir = THEMES_DIR / theme / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n== {theme} ==  → {out_dir}")
    found = []
    for q in THEMES[theme]:
        print(f"  search: {q!r}")
        results = search_images(q, limit=15)
        print(f"    {len(results)} candidates")
        found.extend(results)
        time.sleep(0.3)  # be polite to the API
    # dedupe
    seen, uniq = set(), []
    for title, url in found:
        if title in seen:
            continue
        seen.add(title)
        uniq.append((title, url))
    uniq = uniq[:MAX_PER_THEME]
    print(f"  downloading {len(uniq)} unique images (serial, throttled)...")
    for title, url in uniq:
        dest = out_dir / safe_name(title)
        result = download(url, dest)
        print(f"    {result}")
        if not result.startswith("skip"):
            time.sleep(0.6)  # throttle: stay well under Wikimedia's rate limits
    final = list(out_dir.glob("*"))
    print(f"  → {len(final)} images in {out_dir}")


def main():
    targets = sys.argv[1:] or list(THEMES.keys())
    for t in targets:
        if t not in THEMES:
            print(f"unknown theme: {t}")
            continue
        fetch_theme(t)


if __name__ == "__main__":
    main()
