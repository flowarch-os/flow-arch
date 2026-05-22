#!/usr/bin/env python3
"""App picker: themed grid-style launcher, replaces wofi --show drun.

Scans .desktop entries, resolves icons against the active icon theme,
spawns AppPicker.qml via qmlscene, and execs the selected app.
"""

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
SCRIPT_DIR = Path(__file__).resolve().parent
QML_PATH = SCRIPT_DIR / "AppPicker.qml"
DATA_JSON = Path("/tmp/app_picker_data.json")

DESKTOP_DIRS = [
    Path("/usr/share/applications"),
    Path("/usr/local/share/applications"),
    HOME / ".local/share/applications",
    Path("/var/lib/flatpak/exports/share/applications"),
    HOME / ".local/share/flatpak/exports/share/applications",
]

ICON_THEME = "Papirus-Dark"
ICON_SIZES = ["scalable", "128x128", "96x96", "64x64", "256x256", "48x48",
              "512x512", "32x32", "24x24", "16x16", "symbolic"]
ICON_DIRS = [
    Path("/usr/share/icons"),
    HOME / ".local/share/icons",
    HOME / ".icons",
]
PIXMAPS = Path("/usr/share/pixmaps")
ICON_EXTS = [".svg", ".png", ".xpm"]

FIELD_CODE_RE = re.compile(r"%[fFuUdDnNickvm]")


# ---------- theme ----------

def active_theme_colors():
    """Return dict with bg/fg/accent/dimAccent (#rrggbb each)."""
    waybar_link = HOME / ".config/waybar/style.css"
    theme = "coding"
    try:
        target = os.readlink(waybar_link)
        m = re.search(r"/themes/([^/]+)/", target)
        if m:
            theme = m.group(1)
    except OSError:
        pass

    colors_file = HOME / f".config/hypr/themes/{theme}/colors"
    vals = {}
    try:
        for line in colors_file.read_text().splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip("'\"")
    except OSError:
        pass

    bg = "#" + vals.get("bg_color", "0a1a2e")
    fg = "#" + vals.get("fg_color", "5fbaff")
    accent = "#" + vals.get("active_border", vals.get("fg_color", "5fbaff"))
    dim = "#" + vals.get("inactive_border", "1a3a5e")
    return {"bgColor": bg, "fgColor": fg, "accent": accent, "dimAccent": dim,
            "themeName": theme}


# ---------- icon resolution ----------

_icon_cache = {}

def _icon_search_roots():
    """Ordered list of (dir, weight) — lower weight wins."""
    roots = []
    for base in ICON_DIRS:
        for theme in (ICON_THEME, "hicolor", "Adwaita"):
            tdir = base / theme
            if not tdir.is_dir():
                continue
            for i, size in enumerate(ICON_SIZES):
                for cat in ("apps", "categories", "devices", "places", "mimetypes"):
                    p = tdir / size / cat
                    if p.is_dir():
                        roots.append(p)
                # Papirus uses size/<cat>; some themes use <cat>/size/
                p2 = tdir / "apps" / size
                if p2.is_dir():
                    roots.append(p2)
    if PIXMAPS.is_dir():
        roots.append(PIXMAPS)
    return roots

_SEARCH_ROOTS = None

def resolve_icon(name):
    if not name:
        return ""
    if name in _icon_cache:
        return _icon_cache[name]
    # Absolute path
    if name.startswith("/"):
        p = Path(name)
        result = str(p) if p.exists() else ""
        _icon_cache[name] = result
        return result

    global _SEARCH_ROOTS
    if _SEARCH_ROOTS is None:
        _SEARCH_ROOTS = _icon_search_roots()

    for root in _SEARCH_ROOTS:
        for ext in ICON_EXTS:
            cand = root / f"{name}{ext}"
            if cand.exists():
                _icon_cache[name] = str(cand)
                return str(cand)
    _icon_cache[name] = ""
    return ""


# ---------- .desktop parsing ----------

def parse_desktop_file(path):
    section = None
    data = {}
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1]
                    continue
                if section != "Desktop Entry":
                    continue
                if "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                # Skip localized variants (e.g. Name[fr])
                if "[" in k:
                    continue
                data[k] = v.strip()
    except OSError:
        return None
    return data


def collect_apps():
    seen = set()  # by basename, so user overrides system
    apps = []
    for d in DESKTOP_DIRS:
        if not d.is_dir():
            continue
        for entry in sorted(d.glob("*.desktop")):
            if entry.name in seen:
                continue
            seen.add(entry.name)
            data = parse_desktop_file(entry)
            if not data:
                continue
            if data.get("Type", "Application") != "Application":
                continue
            if data.get("NoDisplay", "").lower() == "true":
                continue
            if data.get("Hidden", "").lower() == "true":
                continue
            exec_line = data.get("Exec", "").strip()
            if not exec_line:
                continue
            name = data.get("Name", "").strip() or entry.stem
            comment = data.get("Comment", "").strip()
            icon_name = data.get("Icon", "").strip()
            icon_path = resolve_icon(icon_name)
            # Strip field codes
            cleaned = FIELD_CODE_RE.sub("", exec_line).replace("%%", "%").strip()
            cleaned = re.sub(r"\s+", " ", cleaned)
            if data.get("Terminal", "").lower() == "true":
                cleaned = f"kitty -e {cleaned}"
            apps.append({
                "name": name,
                "comment": comment,
                "exec": cleaned,
                "icon": icon_path,
            })
    apps.sort(key=lambda a: a["name"].lower())
    return apps


# ---------- main ----------

def main():
    # Single-instance: if another picker is open, just exit.
    try:
        out = subprocess.run(
            ["pgrep", "-f", "qmlscene.*AppPicker.qml"],
            capture_output=True, text=True,
        )
        if out.stdout.strip():
            return 0
    except FileNotFoundError:
        pass

    apps = collect_apps()
    theme = active_theme_colors()
    DATA_JSON.write_text(json.dumps({"theme": theme, "apps": apps}))

    cmd = ["qmlscene", str(QML_PATH)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print("qmlscene not found; install qt5-declarative", file=sys.stderr)
        return 1

    output = (result.stdout or "") + (result.stderr or "")
    exec_line = None
    for line in output.splitlines():
        idx = line.find("LAUNCH:")
        if idx >= 0:
            exec_line = line[idx + len("LAUNCH:"):].strip()
            break

    if not exec_line:
        return 0

    try:
        parts = shlex.split(exec_line)
    except ValueError:
        parts = exec_line.split()
    if not parts:
        return 0
    subprocess.Popen(
        parts,
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
