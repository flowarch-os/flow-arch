"""Pulse / Pipewire sink listing and default-sink switching via pactl."""

import subprocess


def list_sinks() -> list[dict]:
    """Each sink: {name, description, default}."""
    try:
        short = subprocess.check_output(["pactl", "list", "short", "sinks"], text=True)
        info = subprocess.check_output(["pactl", "info"], text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    default_name = ""
    for line in info.splitlines():
        if line.startswith("Default Sink:"):
            default_name = line.split(":", 1)[1].strip()

    sinks = []
    for line in short.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        name = parts[1]
        # description lookup
        desc = name
        try:
            full = subprocess.check_output(["pactl", "list", "sinks"], text=True)
            blocks = full.split("\n\n")
            for blk in blocks:
                if f"Name: {name}" in blk:
                    for ln in blk.splitlines():
                        if "Description:" in ln:
                            desc = ln.split(":", 1)[1].strip()
                            break
                    break
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        sinks.append({"name": name, "description": desc, "default": (name == default_name)})
    return sinks


def set_default_sink(name: str) -> None:
    subprocess.run(["pactl", "set-default-sink", name], check=False)
