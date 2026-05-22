"""Wrappers for switch_theme.sh / cycle_themes.sh."""

import subprocess
from pathlib import Path

SWITCH = Path.home() / ".config/hypr/scripts/switch_theme.sh"
CYCLE = Path.home() / ".config/hypr/scripts/cycle_themes.sh"


def switch(theme: str) -> None:
    if not SWITCH.exists():
        return
    subprocess.Popen([str(SWITCH), theme])


def cycle() -> None:
    if not CYCLE.exists():
        return
    subprocess.Popen([str(CYCLE)])
