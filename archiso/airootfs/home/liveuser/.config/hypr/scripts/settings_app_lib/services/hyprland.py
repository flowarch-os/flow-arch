"""Hyprland keybinding parser + writer + hyprctl reload."""

import re
import subprocess
from pathlib import Path

KEYBINDINGS_FILE = Path.home() / ".config/hypr/keybindings.conf"

BIND_RE = re.compile(r"^(bindl|bindm|bindel|bindr|binde|bind)\s*=\s*(.+)$")
SECTION_RE = re.compile(r"^#\s*--\s*(.+?)\s*--\s*$")


def load_bindings() -> list[dict]:
    """Return a list of binding dicts (and section headers as separators)."""
    bindings = []
    if not KEYBINDINGS_FILE.exists():
        return bindings
    current_section = "General"
    try:
        for line in KEYBINDINGS_FILE.read_text().splitlines():
            line_stripped = line.strip()
            if not line_stripped:
                continue
            m_sec = SECTION_RE.match(line_stripped)
            if m_sec:
                current_section = m_sec.group(1).strip()
                continue
            m = BIND_RE.match(line_stripped)
            if not m:
                continue
            prefix = m.group(1)
            content = m.group(2)
            parts = [p.strip() for p in content.split(",")]
            if len(parts) < 3:
                continue
            mods, key, action = parts[0], parts[1], parts[2]
            args = ", ".join(parts[3:]) if len(parts) > 3 else ""
            bindings.append({
                "section":  current_section,
                "prefix":   prefix,
                "mods":     mods,
                "key":      key,
                "action":   action,
                "args":     args,
                "original": line_stripped,
            })
    except OSError as e:
        print(f"[hyprland] read error: {e}")
    return bindings


def save_bindings(bindings: list[dict]) -> bool:
    """Group by section, write canonical form, reload hyprland."""
    if not KEYBINDINGS_FILE.exists():
        return False
    sections: dict[str, list[dict]] = {}
    order: list[str] = []
    for b in bindings:
        sec = b.get("section", "General")
        if sec not in sections:
            sections[sec] = []
            order.append(sec)
        sections[sec].append(b)
    try:
        with KEYBINDINGS_FILE.open("w") as f:
            f.write("$mainMod = SUPER\n\n")
            for sec in order:
                f.write(f"# -- {sec} --\n")
                for b in sections[sec]:
                    prefix = b.get("prefix") or "bind"
                    line = f"{prefix} = {b['mods']}, {b['key']}, {b['action']}"
                    if b.get("args"):
                        line += f", {b['args']}"
                    f.write(line + "\n")
                f.write("\n")
    except OSError as e:
        print(f"[hyprland] write error: {e}")
        return False
    reload_hyprland()
    return True


def reload_hyprland() -> None:
    subprocess.run(["hyprctl", "reload"], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ----- key name humanization -----

NAMED_KEYS = {
    "Return": "Enter", "KP_Enter": "Enter", "Escape": "Esc",
    "BackSpace": "Backspace", "space": "Space", "Tab": "Tab",
    "Print": "PrintScr",
}


def humanize_key(name: str) -> str:
    return NAMED_KEYS.get(name, name)
