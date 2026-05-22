"""Pomodoro: work/break durations + intention popup toggle, with preset chips."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..widgets.section import scrollable_page, Section
from ..widgets.row import spin_row, switch_row, ActionRow


PRESETS = [
    # (label, work, short, long)
    ("Classic",  25,  5, 15),
    ("Deep",     50, 10, 20),
    ("Sprint",   15,  3, 10),
    ("Marathon", 90, 20, 30),
]


def _set(app, key: str, value) -> None:
    app.settings.setdefault("focus", {}).setdefault("pomodoro", {})[key] = value
    app.save()


def _iter_children(box: Gtk.Box):
    c = box.get_first_child()
    while c:
        nxt = c.get_next_sibling()
        yield c
        c = nxt


def _find_spinbutton(row: ActionRow) -> Gtk.SpinButton | None:
    last = row.get_last_child()
    if isinstance(last, Gtk.SpinButton):
        return last
    if isinstance(last, Gtk.Box):
        for c in _iter_children(last):
            if isinstance(c, Gtk.SpinButton):
                return c
    return None


def build(app):
    scrolled, content = scrollable_page(
        "Pomodoro",
        "Tune the focus / break cadence used during sessions.",
    )

    settings = app.settings.setdefault("focus", {}).setdefault("pomodoro", {})

    # ---- spin controls ----
    config_section = Section("Configuration")
    content.append(config_section)

    work_row = spin_row("Work duration", "Length of one focus block.",
                       int(settings.get("work_duration", 25)), 1, 240, 1,
                       lambda v: _set(app, "work_duration", v), unit="min")
    short_row = spin_row("Short break", "Length of mini-breaks between blocks.",
                        int(settings.get("short_break", 5)), 1, 60, 1,
                        lambda v: _set(app, "short_break", v), unit="min")
    long_row = spin_row("Long break", "Length of the longer break after a cycle.",
                       int(settings.get("long_break", 20)), 1, 120, 1,
                       lambda v: _set(app, "long_break", v), unit="min")
    config_section.add(work_row)
    config_section.add(short_row)
    config_section.add(long_row)

    config_section.add(switch_row(
        "Show intention popup",
        "Ask 'what's the next intention?' before each work block.",
        settings.get("intention_popup", True),
        lambda b: _set(app, "intention_popup", b),
    ))

    spin_work = _find_spinbutton(work_row)
    spin_short = _find_spinbutton(short_row)
    spin_long = _find_spinbutton(long_row)

    # ---- preset chips (above config, but appended after for ordering hack) ----
    preset_section = Section("Presets", "One-click cadence templates.")
    chip_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    preset_section.add(chip_row)
    # Insert before config
    content.remove(config_section)
    content.append(preset_section)
    content.append(config_section)

    chips: list[Gtk.Button] = []

    def is_active(name: str, w: int, s: int, l: int) -> bool:
        return (settings.get("work_duration") == w
                and settings.get("short_break") == s
                and settings.get("long_break") == l)

    def apply_preset(name: str, w: int, s: int, l: int):
        settings.update(work_duration=w, short_break=s, long_break=l)
        app.save()
        if spin_work:  spin_work.set_value(w)
        if spin_short: spin_short.set_value(s)
        if spin_long:  spin_long.set_value(l)
        for c in chips:
            c.remove_css_class("active")
            if c.get_label().startswith(name):
                c.add_css_class("active")

    for name, w, s, l in PRESETS:
        btn = Gtk.Button(label=f"{name}  ·  {w}/{s}")
        btn.add_css_class("chip")
        if is_active(name, w, s, l):
            btn.add_css_class("active")
        btn.connect("clicked", lambda _b, nn=name, ww=w, ss=s, ll=l: apply_preset(nn, ww, ss, ll))
        chip_row.append(btn)
        chips.append(btn)

    return scrolled
