"""Action rows: title + subtitle + control. Used inside Section.body."""

from typing import Callable

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GObject


class ActionRow(Gtk.Box):
    """Base row: title/subtitle on the left, custom widget on the right."""

    def __init__(self, title: str, subtitle: str | None = None, suffix: Gtk.Widget | None = None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.add_css_class("action-row")

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text.set_hexpand(True)
        text.set_valign(Gtk.Align.CENTER)
        t = Gtk.Label(label=title, xalign=0, wrap=True)
        t.add_css_class("row-title")
        text.append(t)
        if subtitle:
            s = Gtk.Label(label=subtitle, xalign=0, wrap=True)
            s.add_css_class("row-subtitle")
            text.append(s)
        self.append(text)

        if suffix is not None:
            suffix.set_valign(Gtk.Align.CENTER)
            self.append(suffix)


def switch_row(title: str, subtitle: str | None, active: bool,
               on_change: Callable[[bool], None]) -> ActionRow:
    sw = Gtk.Switch()
    sw.set_active(active)

    def _cb(switch, state):
        on_change(bool(state))
        return False

    sw.connect("state-set", _cb)
    return ActionRow(title, subtitle, sw)


def spin_row(title: str, subtitle: str | None, value: int,
             lo: int, hi: int, step: int,
             on_change: Callable[[int], None], unit: str = "") -> ActionRow:
    adj = Gtk.Adjustment(value=value, lower=lo, upper=hi, step_increment=step, page_increment=step * 5)
    spin = Gtk.SpinButton(adjustment=adj)
    spin.set_numeric(True)

    if unit:
        wrap = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        wrap.append(spin)
        u = Gtk.Label(label=unit); u.add_css_class("dim-label")
        wrap.append(u)
        suffix = wrap
    else:
        suffix = spin

    def _cb(s):
        on_change(int(s.get_value()))

    spin.connect("value-changed", _cb)
    return ActionRow(title, subtitle, suffix)


def dropdown_row(title: str, subtitle: str | None, choices: list[str],
                 selected: int, on_change: Callable[[int, str], None]) -> ActionRow:
    dd = Gtk.DropDown.new_from_strings(choices)
    dd.set_selected(max(0, min(selected, len(choices) - 1)))

    def _cb(dd_, _pspec):
        i = dd_.get_selected()
        if 0 <= i < len(choices):
            on_change(i, choices[i])

    dd.connect("notify::selected", _cb)
    return ActionRow(title, subtitle, dd)


def scale_row(title: str, subtitle: str | None, value: float,
              lo: float, hi: float, step: float,
              on_change: Callable[[float], None],
              format_fn: Callable[[float], str] | None = None) -> ActionRow:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    box.set_size_request(260, -1)

    adj = Gtk.Adjustment(value=value, lower=lo, upper=hi,
                         step_increment=step, page_increment=step * 5)
    scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
    scale.set_draw_value(False)
    scale.set_hexpand(True)
    scale.set_size_request(180, -1)

    val_lbl = Gtk.Label(label=format_fn(value) if format_fn else f"{value:g}")
    val_lbl.add_css_class("mono")
    val_lbl.set_size_request(70, -1)
    val_lbl.set_xalign(1)

    def _cb(s):
        v = s.get_value()
        val_lbl.set_label(format_fn(v) if format_fn else f"{v:g}")
        on_change(v)

    scale.connect("value-changed", _cb)
    box.append(scale)
    box.append(val_lbl)
    return ActionRow(title, subtitle, box)


def entry_row(title: str, placeholder: str, value: str,
              on_apply: Callable[[str], None],
              button_label: str = "Add") -> ActionRow:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    e = Gtk.Entry(placeholder_text=placeholder, text=value)
    e.set_hexpand(True)
    e.set_size_request(260, -1)
    btn = Gtk.Button(label=button_label)
    btn.add_css_class("suggested-action")

    def commit():
        text = e.get_text().strip()
        if text:
            on_apply(text)
            e.set_text("")

    e.connect("activate", lambda _e: commit())
    btn.connect("clicked", lambda _b: commit())
    box.append(e); box.append(btn)
    return ActionRow(title, None, box)
