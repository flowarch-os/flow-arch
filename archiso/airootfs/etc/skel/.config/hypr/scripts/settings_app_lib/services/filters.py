"""Wrappers for ad blocking + media blackout."""

import os
import subprocess
from pathlib import Path

HOSTS_MANAGER = Path.home() / ".config/hypr/scripts/hosts_manager.py"
MEDIA_BLACKOUT = Path.home() / ".config/hypr/scripts/media_blackout.py"
MEDIA_GUARD = Path.home() / ".config/hypr/scripts/media_guard.py"


def set_ad_blocking(enabled: bool) -> None:
    if not HOSTS_MANAGER.exists():
        return
    cmd = "on" if enabled else "off"
    subprocess.Popen(["sudo", str(HOSTS_MANAGER), "ads", cmd])


def refresh_ad_hosts() -> None:
    if not HOSTS_MANAGER.exists():
        return
    subprocess.Popen(["sudo", str(HOSTS_MANAGER), "ads", "update"])


def set_media_blackout(enabled: bool, allowlist: list[str]) -> None:
    allowed = ",".join(allowlist)
    if enabled:
        if MEDIA_BLACKOUT.exists():
            subprocess.run(["python3", str(MEDIA_BLACKOUT), "on", allowed],
                           check=False)
        subprocess.run(["pkill", "-f", "media_guard.py"], check=False)
        if MEDIA_GUARD.exists():
            subprocess.Popen(["python3", str(MEDIA_GUARD), allowed])
    else:
        subprocess.run(["pkill", "-f", "media_guard.py"], check=False)
        if MEDIA_BLACKOUT.exists():
            subprocess.run(["python3", str(MEDIA_BLACKOUT), "off", allowed],
                           check=False)
