"""Goals: list of goals, each with a theme swatch picker."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

from .. import model, theme as theme_mod
from ..widgets.section import scrollable_page, Section


def _swatch_button(theme_name: str, palette: dict, active: bool,
                   on_click) -> Gtk.Button:
    btn = Gtk.Button()
    btn.add_css_class("swatch")
    if active:
        btn.add_css_class("active")
    btn.set_tooltip_text(theme_name)

    # Use inline CSS via a per-widget provider
    css = f""".swatch.t_{theme_name} {{ {theme_mod.palette_swatch_css(palette)} }}"""
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode("utf-8"))
    btn.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    btn.add_css_class(f"t_{theme_name}")
    btn.connect("clicked", lambda _b: on_click(theme_name))
    return btn


def build(app):
    scrolled, content = scrollable_page(
        "Goals",
        "Define what you're working on. Each goal can have a theme that the desktop switches to during its sessions.",
    )

    # ---- Add goal ----
    add_section = Section("New Goal")
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    entry = Gtk.Entry(placeholder_text="e.g. Build OS")
    entry.set_hexpand(True)
    btn = Gtk.Button(label="Add Goal")
    btn.add_css_class("suggested-action")

    def commit():
        text = entry.get_text().strip()
        if not text:
            return
        goals_ = app.settings.setdefault("focus", {}).setdefault("goals", [])
        if text not in goals_:
            goals_.append(text)
            app.save()
            entry.set_text("")
            render()

    entry.connect("activate", lambda _e: commit())
    btn.connect("clicked", lambda _b: commit())
    row.append(entry); row.append(btn)
    add_section.add(row)
    content.append(add_section)

    # ---- List ----
    list_section = Section("Your Goals")
    list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    list_section.add(list_box)
    content.append(list_section)

    def clear(box):
        c = box.get_first_child()
        while c:
            n = c.get_next_sibling()
            box.remove(c)
            c = n

    def render():
        clear(list_box)
        goals_ = model.goals(app.settings)
        if not goals_:
            empty = Gtk.Label(label="No goals yet. Add one above to start.", xalign=0)
            empty.add_css_class("dim-label")
            list_box.append(empty)
            return

        themes_list = theme_mod.list_themes()

        for goal in goals_:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card.add_css_class("action-row")

            head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            name = Gtk.Label(label=goal, xalign=0)
            name.add_css_class("heading")
            name.set_hexpand(True)
            name.set_wrap(True)
            head.append(name)

            current_theme = model.goal_themes(app.settings).get(goal, "")
            badge = Gtk.Label(label=f"theme · {current_theme or 'default'}", xalign=1)
            badge.add_css_class("dim-label"); badge.add_css_class("mono")
            head.append(badge)

            del_btn = Gtk.Button(label="Remove")
            del_btn.add_css_class("destructive-action")
            del_btn.add_css_class("flat")

            def on_delete(_b, g=goal):
                gs = app.settings.setdefault("focus", {}).setdefault("goals", [])
                if g in gs:
                    gs.remove(g)
                gt = app.settings.setdefault("focus", {}).setdefault("goal_themes", {})
                gt.pop(g, None)
                app.save()
                render()

            del_btn.connect("clicked", on_delete)
            head.append(del_btn)
            card.append(head)

            # Swatch grid
            swatches = Gtk.FlowBox()
            swatches.set_selection_mode(Gtk.SelectionMode.NONE)
            swatches.set_max_children_per_line(12)
            swatches.set_homogeneous(False)
            swatches.set_row_spacing(6); swatches.set_column_spacing(6)

            # "None" swatch
            none_btn = Gtk.Button(label="—")
            none_btn.add_css_class("swatch")
            if not current_theme:
                none_btn.add_css_class("active")
            none_btn.set_tooltip_text("No theme override")

            def on_none(_b, g=goal):
                gt = app.settings.setdefault("focus", {}).setdefault("goal_themes", {})
                gt.pop(g, None)
                app.save()
                badge.set_label("theme · default")
                render()

            none_btn.connect("clicked", on_none)
            swatches.append(none_btn)

            def on_pick(theme_name, g=goal):
                gt = app.settings.setdefault("focus", {}).setdefault("goal_themes", {})
                gt[g] = theme_name
                app.save()
                render()

            for tname in themes_list:
                p = theme_mod.load_palette(tname)
                swatches.append(_swatch_button(tname, p, active=(tname == current_theme), on_click=on_pick))
            card.append(swatches)

            list_box.append(card)

    render()
    scrolled.on_show = render
    return scrolled
