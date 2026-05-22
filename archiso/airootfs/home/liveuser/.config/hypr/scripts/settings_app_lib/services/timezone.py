"""Timezone listing + apply (uses pkexec for the privileged setter)."""

import subprocess


def list_timezones() -> list[str]:
    try:
        out = subprocess.check_output(["timedatectl", "list-timezones"], text=True)
        return [l.strip() for l in out.splitlines() if l.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def current_timezone() -> str:
    try:
        out = subprocess.check_output(["timedatectl", "show", "--value", "-p", "Timezone"], text=True)
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def set_timezone(tz: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["pkexec", "timedatectl", "set-timezone", tz],
            check=False, capture_output=True, text=True,
        )
        if result.returncode == 0:
            return True, ""
        return False, result.stderr.strip() or "pkexec failed"
    except FileNotFoundError:
        return False, "pkexec not found"
