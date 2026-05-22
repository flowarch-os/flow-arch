"""Stat card: big number + label + optional accent."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class StatCard(Gtk.Box):
    def __init__(self, label: str, value: str, sub: str | None = None, icon: str = ""):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add_css_class("card")
        self.add_css_class("accent-top")

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        if icon:
            i = Gtk.Label(label=icon + "‎ ‎")
            i.add_css_class("mono")
            i.add_css_class("accent-text")
            top.append(i)
        lbl = Gtk.Label(label=label, xalign=0)
        lbl.add_css_class("stat-label")
        top.append(lbl)
        top.set_hexpand(True)
        self.append(top)

        val = Gtk.Label(label=value, xalign=0)
        val.add_css_class("stat-number")
        self.append(val)
        self._val = val

        if sub:
            s = Gtk.Label(label=sub, xalign=0)
            s.add_css_class("dim-label")
            self.append(s)
            self._sub = s
        else:
            self._sub = None

    def set_value(self, value: str, sub: str | None = None) -> None:
        self._val.set_label(value)
        if self._sub is not None and sub is not None:
            self._sub.set_label(sub)
