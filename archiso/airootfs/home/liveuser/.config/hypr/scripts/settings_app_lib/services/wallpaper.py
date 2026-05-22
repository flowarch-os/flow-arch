"""Wallpaper manifest read/write + engine restart."""

import subprocess
from pathlib import Path

ENGINE = Path.home() / ".config/hypr/scripts/wallpaper_engine.sh"
THEMES = Path.home() / ".config/hypr/themes"


def manifest_path(theme: str) -> Path:
    return THEMES / theme / "wallpaper.conf"


def read_manifest(theme: str) -> dict:
    """Parse the wallpaper.conf shell-vars file into a dict."""
    out = {
        "type": "static",
        "engine": "hyprpaper",
        "images_dir": "images/",
        "interval": "300",
        "transition": "fade",
        "video": "loop.mp4",
        "videos_dir": "",
    }
    mf = manifest_path(theme)
    if not mf.exists():
        return out
    for raw in mf.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip("\"'")
        if k in out:
            out[k] = v
    return out


def write_manifest(theme: str, data: dict) -> bool:
    mf = manifest_path(theme)
    if not mf.parent.exists():
        return False
    try:
        with mf.open("w") as f:
            f.write(f"# wallpaper.conf for {theme}\n")
            for k in ("type", "engine", "images_dir", "interval",
                      "transition", "video", "videos_dir"):
                v = data.get(k, "")
                if v != "":
                    f.write(f'{k}={v}\n')
        return True
    except OSError as e:
        print(f"[wallpaper] write error: {e}")
        return False


def restart(theme: str) -> None:
    if ENGINE.exists():
        subprocess.Popen([str(ENGINE), theme])
