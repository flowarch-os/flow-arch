"""Blue-light / color-temperature controls (delegates to blue_light_control.sh)."""

import subprocess
from pathlib import Path

CONTROL = Path.home() / ".config/hypr/scripts/blue_light_control.sh"
STATE_FILE = Path.home() / ".config/hypr/blue_light_state"
TEMP_FILE = Path.home() / ".config/hypr/blue_light_temp"


def is_active() -> bool:
    return STATE_FILE.exists() and STATE_FILE.read_text().strip() in ("on", "1", "true")


def current_temp() -> int:
    try:
        return int(TEMP_FILE.read_text().strip())
    except (OSError, ValueError):
        return 3500


def set_temperature(kelvin: int) -> None:
    if not CONTROL.exists():
        return
    subprocess.Popen([str(CONTROL), "set_temp", str(int(kelvin))])


def toggle() -> None:
    if not CONTROL.exists():
        return
    subprocess.Popen([str(CONTROL), "toggle"])


def turn_off() -> None:
    """Hide the shader. We hop to 6500K which the script treats as 'off-equivalent'."""
    set_temperature(6500)
