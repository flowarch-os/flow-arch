"""Active-theme palette extraction + dynamic CSS generation.

Source of truth: ~/.config/hypr/theme.conf is a symlink. Its target's parent dir
is the theme dir (e.g. ~/.config/hypr/themes/blue/). Inside is a `colors` shell
file with bg_color / fg_color / active_border / inactive_border.
"""

import os
import re
from pathlib import Path

HYPR_CONF = Path.home() / ".config/hypr"
THEME_LINK = HYPR_CONF / "theme.conf"
THEMES_DIR = HYPR_CONF / "themes"

DEFAULT_PALETTE = {
    "bg":             "#000030",
    "fg":             "#00aaff",
    "active_border":  "#00aaff",
    "inactive_border":"#000030",
    "name":           "blue",
}


def _clean(hex_value: str) -> str:
    """Strip quotes, leading rgba()/0x, ensure leading #."""
    v = hex_value.strip().strip("'\"")
    v = re.sub(r"^(0x|rgba\(|rgb\()", "", v).rstrip(")")
    if "," in v:
        v = v.split(",")[0]
    v = v.strip()
    if not v.startswith("#"):
        v = "#" + v
    if len(v) == 9:
        v = v[:7]
    return v.lower()


def _parse_colors_file(path: Path) -> dict:
    out = {}
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = _clean(v)
    except OSError:
        pass
    return out


def active_theme_name() -> str:
    """Resolve the symlink target → theme dir name (e.g. 'blue')."""
    try:
        target = os.readlink(str(THEME_LINK))
        return Path(target).parent.name
    except OSError:
        return DEFAULT_PALETTE["name"]


def load_palette(name: str | None = None) -> dict:
    """Read the colors file for a given theme (or the active one)."""
    if name is None:
        name = active_theme_name()
    colors_file = THEMES_DIR / name / "colors"
    raw = _parse_colors_file(colors_file)
    if not raw:
        p = dict(DEFAULT_PALETTE)
        p["name"] = name or DEFAULT_PALETTE["name"]
        return p
    return {
        "bg":              raw.get("bg_color", DEFAULT_PALETTE["bg"]),
        "fg":              raw.get("fg_color", DEFAULT_PALETTE["fg"]),
        "active_border":   raw.get("active_border", raw.get("fg_color", DEFAULT_PALETTE["active_border"])),
        "inactive_border": raw.get("inactive_border", raw.get("bg_color", DEFAULT_PALETTE["inactive_border"])),
        "name":            name,
    }


def list_themes() -> list[str]:
    if not THEMES_DIR.exists():
        return []
    return sorted(p.name for p in THEMES_DIR.iterdir() if p.is_dir())


# ----- color math -----

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _mix(a: str, b: str, t: float) -> str:
    ar, ag, ab = _hex_to_rgb(a)
    br, bg_, bb = _hex_to_rgb(b)
    return _rgb_to_hex(
        int(ar + (br - ar) * t),
        int(ag + (bg_ - ag) * t),
        int(ab + (bb - ab) * t),
    )


def _alpha(hex_color: str, a: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return f"rgba({r},{g},{b},{a:.3f})"


def _luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def derive(palette: dict) -> dict:
    """Build a richer set of derived colors from the 4 base values."""
    bg = palette["bg"]
    fg = palette["fg"]
    accent = palette["active_border"] or fg
    border = palette["inactive_border"] or bg

    # If bg is dark, lift by mixing white; if light, drop by mixing black.
    dark = _luminance(bg) < 0.5
    surface = _mix(bg, "#ffffff" if dark else "#000000", 0.05)
    surface_hi = _mix(bg, "#ffffff" if dark else "#000000", 0.10)
    surface_input = _mix(bg, "#ffffff" if dark else "#000000", 0.08)

    fg_strong = _mix(fg, "#ffffff" if dark else "#000000", 0.0)
    fg_dim = _mix(fg, bg, 0.45)
    fg_muted = _mix(fg, bg, 0.65)

    # On-accent text: pick black/white based on accent luminance.
    on_accent = "#000000" if _luminance(accent) > 0.55 else "#ffffff"

    return {
        **palette,
        "accent":         accent,
        "on_accent":      on_accent,
        "border":         border,
        "border_subtle":  _alpha(fg, 0.10),
        "border_focus":   accent,
        "bg":             bg,
        "surface":        surface,
        "surface_hi":     surface_hi,
        "surface_input":  surface_input,
        "fg":             fg_strong,
        "fg_dim":         fg_dim,
        "fg_muted":       fg_muted,
        "danger":         "#ff5577",
        "success":        "#3ddc97",
        "warning":        "#f5b041",
        "scrim":          _alpha("#000000", 0.45),
        "is_dark":        dark,
    }


def generate_css(palette: dict) -> str:
    """Build the full GTK4 stylesheet for the app from a derived palette."""
    c = derive(palette)

    return f"""
/* ---------- root ---------- */
window {{
  background-color: {c['bg']};
  color: {c['fg']};
  font-family: "Inter", "Adwaita Sans", system-ui, sans-serif;
  font-size: 14px;
}}

/* ---------- typography ---------- */
.app-title {{ font-size: 22px; font-weight: 700; color: {c['fg']}; }}
.page-title {{ font-size: 26px; font-weight: 700; color: {c['fg']}; margin-bottom: 4px; }}
.page-subtitle {{ font-size: 13px; color: {c['fg_dim']}; margin-bottom: 18px; }}
.section-title {{ font-size: 16px; font-weight: 600; color: {c['fg']}; }}
.section-subtitle {{ font-size: 12px; color: {c['fg_dim']}; }}
.stat-number {{ font-size: 28px; font-weight: 700; color: {c['accent']}; font-family: "JetBrainsMono Nerd Font", monospace; }}
.stat-label {{ font-size: 11px; color: {c['fg_dim']}; text-transform: uppercase; letter-spacing: 0.08em; }}
.heading {{ font-weight: 600; color: {c['fg']}; }}
.dim-label {{ color: {c['fg_dim']}; font-size: 12px; }}
.muted {{ color: {c['fg_muted']}; }}
.mono {{ font-family: "JetBrainsMono Nerd Font", monospace; }}

/* ---------- sidebar ---------- */
.sidebar {{
  background-color: {c['surface']};
  border-right: 1px solid {c['border_subtle']};
  padding: 16px 8px;
}}
.sidebar-header {{
  padding: 6px 14px 18px 14px;
  color: {c['accent']};
  font-weight: 700;
  font-size: 18px;
  font-family: "JetBrainsMono Nerd Font", monospace;
}}
.sidebar-row {{
  padding: 10px 14px;
  border-radius: 8px;
  color: {c['fg_dim']};
  background-color: transparent;
  transition: background-color 120ms ease, color 120ms ease;
}}
.sidebar-row:hover {{ background-color: {c['surface_hi']}; color: {c['fg']}; }}
.sidebar-row.active {{
  background-color: {_alpha(c['accent'], 0.18)};
  color: {c['accent']};
  font-weight: 600;
  box-shadow: inset 3px 0 0 0 {c['accent']};
}}
.sidebar-row .row-icon {{ margin-right: 10px; opacity: 0.85; }}

/* ---------- main content ---------- */
.page {{
  padding: 32px 36px;
  background-color: {c['bg']};
}}
scrolledwindow {{ background: transparent; }}
viewport {{ background: transparent; }}

/* ---------- cards / sections ---------- */
.card {{
  background-color: {c['surface']};
  border: 1px solid {c['border_subtle']};
  border-radius: 14px;
  padding: 18px;
}}
.card.accent-top {{ border-top: 2px solid {c['accent']}; }}
.section {{
  background-color: {c['surface']};
  border: 1px solid {c['border_subtle']};
  border-radius: 14px;
  margin-bottom: 14px;
}}
.section-header {{
  padding: 16px 20px;
  border-bottom: 1px solid {c['border_subtle']};
}}
.section-body {{ padding: 18px 20px; }}
.section-body > * + * {{ margin-top: 10px; }}

/* ---------- rows ---------- */
.action-row {{
  padding: 12px 16px;
  background-color: {c['surface']};
  border-radius: 10px;
  border: 1px solid {c['border_subtle']};
}}
.action-row + .action-row {{ margin-top: 6px; }}
.action-row .row-title {{ font-weight: 600; color: {c['fg']}; }}
.action-row .row-subtitle {{ font-size: 12px; color: {c['fg_dim']}; margin-top: 2px; }}

/* ---------- inputs ---------- */
entry, spinbutton, dropdown {{
  background-color: {c['surface_input']};
  color: {c['fg']};
  border: 1px solid {c['border_subtle']};
  border-radius: 8px;
  padding: 7px 10px;
  caret-color: {c['accent']};
}}
entry:focus-within, spinbutton:focus-within, dropdown:focus {{
  border-color: {c['accent']};
  outline: 0;
  box-shadow: 0 0 0 2px {_alpha(c['accent'], 0.25)};
}}
entry > text {{ color: {c['fg']}; }}
entry > text > placeholder {{ color: {c['fg_muted']}; }}

/* ---------- buttons ---------- */
button {{
  background-color: {c['surface_hi']};
  color: {c['fg']};
  border: 1px solid {c['border_subtle']};
  border-radius: 8px;
  padding: 7px 14px;
  transition: background-color 120ms ease, border-color 120ms ease;
}}
button:hover {{
  background-color: {_alpha(c['accent'], 0.15)};
  border-color: {_alpha(c['accent'], 0.5)};
}}
button:active {{ background-color: {_alpha(c['accent'], 0.25)}; }}
button.flat {{ background-color: transparent; border-color: transparent; }}
button.flat:hover {{ background-color: {c['surface_hi']}; }}
button.suggested-action, button.primary {{
  background-color: {c['accent']};
  color: {c['on_accent']};
  border-color: {c['accent']};
  font-weight: 600;
}}
button.suggested-action:hover, button.primary:hover {{
  background-color: {_mix(c['accent'], '#ffffff', 0.15)};
  border-color: {_mix(c['accent'], '#ffffff', 0.15)};
}}
button.destructive-action {{ color: {c['danger']}; }}
button.destructive-action:hover {{ background-color: {_alpha(c['danger'], 0.15)}; border-color: {_alpha(c['danger'], 0.5)}; }}
button.chip {{
  padding: 4px 10px;
  font-size: 12px;
  border-radius: 999px;
  background-color: {c['surface_hi']};
}}
button.chip.active {{ background-color: {c['accent']}; color: {c['on_accent']}; border-color: {c['accent']}; }}
button.swatch {{
  min-width: 56px;
  min-height: 56px;
  padding: 0;
  border-radius: 12px;
  border: 2px solid {c['border_subtle']};
}}
button.swatch.active {{ border-color: {c['accent']}; box-shadow: 0 0 0 2px {_alpha(c['accent'], 0.5)}; }}
button.icon {{ padding: 6px; min-width: 28px; min-height: 28px; }}

/* ---------- switches / sliders ---------- */
switch {{
  background-color: {c['surface_hi']};
  border: 1px solid {c['border_subtle']};
  border-radius: 999px;
  min-width: 42px;
  min-height: 22px;
}}
switch slider {{
  background-color: {c['fg_muted']};
  border-radius: 999px;
  min-width: 18px;
  min-height: 18px;
}}
switch:checked {{ background-color: {_alpha(c['accent'], 0.45)}; border-color: {c['accent']}; }}
switch:checked slider {{ background-color: {c['accent']}; }}

scale trough {{ background-color: {c['surface_hi']}; min-height: 6px; border-radius: 3px; }}
scale highlight {{ background-color: {c['accent']}; border-radius: 3px; }}
scale slider {{
  background-color: {c['accent']};
  border: 2px solid {c['bg']};
  border-radius: 999px;
  min-width: 14px; min-height: 14px;
}}

/* ---------- list ---------- */
listview, listbox {{ background: transparent; }}
listbox > row {{ background: transparent; padding: 0; }}

/* ---------- separator ---------- */
separator {{ background-color: {c['border_subtle']}; min-width: 1px; min-height: 1px; }}

/* ---------- calendar ---------- */
.calendar-slot {{
  border: 1px solid {_alpha(c['fg'], 0.05)};
  background-color: transparent;
}}
.calendar-slot.hour-start {{ border-top: 1px solid {_alpha(c['fg'], 0.12)}; }}
.calendar-day-header {{
  font-weight: 600;
  color: {c['fg_dim']};
  padding: 8px 4px;
  border-bottom: 1px solid {c['border_subtle']};
}}
.calendar-day-header.today {{ color: {c['accent']}; }}
.calendar-day-header.today-pill {{
  background-color: {c['accent']};
  color: {c['on_accent']};
  border-radius: 999px;
  padding: 2px 8px;
}}
.calendar-time-label {{ color: {c['fg_muted']}; font-size: 11px; padding-right: 8px; }}
.sleep-slot {{ background-color: {_alpha(c['fg'], 0.06)}; }}
.now-line {{ background-color: {c['danger']}; min-height: 2px; }}
.event {{
  border-radius: 8px;
  padding: 4px 8px;
  background-color: {_alpha(c['accent'], 0.25)};
  border-left: 3px solid {c['accent']};
}}
.event .event-title {{ font-weight: 600; color: {c['fg']}; }}
.event .event-intention {{ font-size: 11px; color: {c['fg_dim']}; }}
.event.recurring {{ border-left-style: dashed; }}
.event-ghost {{
  background-color: {_alpha(c['accent'], 0.15)};
  border: 1px dashed {c['accent']};
  border-radius: 8px;
}}
.selection {{
  background-color: {_alpha(c['accent'], 0.30)};
  border: 1px solid {c['accent']};
  border-radius: 8px;
}}

/* month grid */
.month-day {{
  border: 1px solid {c['border_subtle']};
  background-color: {c['surface']};
  border-radius: 6px;
  padding: 6px;
  min-height: 80px;
}}
.month-day.other {{ opacity: 0.4; }}
.month-day.today {{ border-color: {c['accent']}; box-shadow: inset 0 0 0 1px {c['accent']}; }}
.month-day .day-num {{ font-weight: 600; color: {c['fg']}; }}
.month-event {{
  font-size: 11px;
  padding: 1px 5px;
  border-radius: 3px;
  background-color: {_alpha(c['accent'], 0.25)};
  color: {c['fg']};
}}

/* ---------- journal ---------- */
.rating-pill {{
  padding: 2px 9px;
  border-radius: 999px;
  font-weight: 600;
  font-family: "JetBrainsMono Nerd Font", monospace;
  font-size: 12px;
  color: {c['on_accent']};
}}
.rating-pill.low {{ background-color: {c['danger']}; }}
.rating-pill.mid {{ background-color: {c['warning']}; color: #000; }}
.rating-pill.high {{ background-color: {c['accent']}; }}

/* ---------- misc ---------- */
.danger {{ color: {c['danger']}; }}
.success {{ color: {c['success']}; }}
.accent-text {{ color: {c['accent']}; }}
.swatch-dot {{ min-width: 14px; min-height: 14px; border-radius: 999px; }}

.toast {{
  background-color: {c['surface_hi']};
  border: 1px solid {c['accent']};
  border-radius: 10px;
  padding: 10px 14px;
  color: {c['fg']};
}}
""".strip() + "\n"


def palette_swatch_css(palette: dict) -> str:
    """A tiny per-button CSS for theme swatches, used by appearance page."""
    c = derive(palette)
    return f"background: linear-gradient(135deg, {c['bg']} 0%, {c['accent']} 100%);"
