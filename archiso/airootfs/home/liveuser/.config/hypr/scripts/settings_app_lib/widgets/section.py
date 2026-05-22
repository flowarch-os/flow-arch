"""Reusable Section: titled card with optional subtitle + actions + body slot."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class Section(Gtk.Box):
    def __init__(self, title: str, subtitle: str | None = None,
                 actions: list[Gtk.Widget] | None = None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.add_css_class("section")

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header.add_css_class("section-header")

        text_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_col.set_hexpand(True)
        lbl = Gtk.Label(label=title, xalign=0)
        lbl.add_css_class("section-title")
        text_col.append(lbl)
        if subtitle:
            sub = Gtk.Label(label=subtitle, xalign=0, wrap=True)
            sub.add_css_class("section-subtitle")
            text_col.append(sub)
        header.append(text_col)

        if actions:
            actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            actions_box.set_valign(Gtk.Align.CENTER)
            for a in actions:
                actions_box.append(a)
            header.append(actions_box)

        self.append(header)

        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.body.add_css_class("section-body")
        self.append(self.body)

    def add(self, widget: Gtk.Widget) -> None:
        self.body.append(widget)


class PageHeader(Gtk.Box):
    def __init__(self, title: str, subtitle: str | None = None,
                 actions: list[Gtk.Widget] | None = None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.set_margin_bottom(20)

        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        col.set_hexpand(True)
        t = Gtk.Label(label=title, xalign=0)
        t.add_css_class("page-title")
        col.append(t)
        if subtitle:
            s = Gtk.Label(label=subtitle, xalign=0, wrap=True)
            s.add_css_class("page-subtitle")
            col.append(s)
        self.append(col)
        if actions:
            ab = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            ab.set_valign(Gtk.Align.CENTER)
            for a in actions:
                ab.append(a)
            self.append(ab)


def scrollable_page(title: str, subtitle: str | None = None,
                    actions: list[Gtk.Widget] | None = None) -> tuple[Gtk.ScrolledWindow, Gtk.Box]:
    """Build a standard scrollable page; returns (root, content_box).

    content_box is where pages append their sections.
    """
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scrolled.set_vexpand(True)
    scrolled.set_hexpand(True)

    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    outer.add_css_class("page")
    scrolled.set_child(outer)

    if title:
        outer.append(PageHeader(title, subtitle, actions))

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
    outer.append(content)
    return scrolled, content
