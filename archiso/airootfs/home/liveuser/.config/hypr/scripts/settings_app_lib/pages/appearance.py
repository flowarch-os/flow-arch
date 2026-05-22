"""Appearance: theme picker, wallpaper engine, blue light."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

from .. import model, theme as theme_mod
from ..services import theme_switcher, wallpaper, blue_light
from ..widgets.section import scrollable_page, Section
from ..widgets.row import switch_row, dropdown_row, scale_row, ActionRow


def build(app):
    cycle_btn = Gtk.Button(label="Cycle Theme")
    cycle_btn.add_css_class("flat")
    cycle_btn.connect("clicked", lambda _b: theme_switcher.cycle())

    scrolled, content = scrollable_page(
        "Appearance",
        "Theme, wallpaper engine, and color-temperature controls. Changes apply to the whole desktop.",
        actions=[cycle_btn],
    )

    # ---------- THEME PICKER ----------
    themes = theme_mod.list_themes()
    active = theme_mod.active_theme_name()

    theme_section = Section(
        "Theme",
        f"Active: {active}. Click a swatch to switch the whole desktop.",
    )
    palette_row = Gtk.FlowBox()
    palette_row.set_selection_mode(Gtk.SelectionMode.NONE)
    palette_row.set_max_children_per_line(6)
    palette_row.set_row_spacing(10)
    palette_row.set_column_spacing(10)
    palette_row.set_homogeneous(False)

    swatch_buttons: list[Gtk.Button] = []

    def rebuild_swatches():
        # clear
        c = palette_row.get_first_child()
        while c:
            n = c.get_next_sibling()
            palette_row.remove(c)
            c = n
        swatch_buttons.clear()
        current = theme_mod.active_theme_name()
        for tname in themes:
            p = theme_mod.load_palette(tname)
            cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            cell.set_halign(Gtk.Align.CENTER)

            btn = Gtk.Button()
            btn.set_size_request(72, 56)
            btn.add_css_class("swatch")
            if tname == current:
                btn.add_css_class("active")

            # per-button gradient CSS
            css = f""".swatch.t_{tname} {{ {theme_mod.palette_swatch_css(p)} }}"""
            prov = Gtk.CssProvider()
            prov.load_from_data(css.encode("utf-8"))
            btn.get_style_context().add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            btn.add_css_class(f"t_{tname}")
            btn.set_tooltip_text(tname)

            def on_click(_b, t=tname):
                theme_switcher.switch(t)

            btn.connect("clicked", on_click)
            cell.append(btn)

            lbl = Gtk.Label(label=tname)
            lbl.add_css_class("dim-label")
            cell.append(lbl)
            palette_row.append(cell)
            swatch_buttons.append(btn)

    rebuild_swatches()
    theme_section.add(palette_row)
    content.append(theme_section)

    # ---------- WALLPAPER ----------
    wp_section = Section(
        "Wallpaper",
        "Configure how the active theme's wallpaper is rendered. Each theme has its own manifest.",
    )

    wp_state = {"theme": active}
    theme_dd = Gtk.DropDown.new_from_strings(themes)
    theme_dd.set_selected(themes.index(active) if active in themes else 0)

    engine_dd = Gtk.DropDown.new_from_strings(["hyprpaper (static)", "awww (slideshow)", "mpvpaper (video)"])
    type_to_engine = {"static": 0, "slideshow": 1, "video": 2}
    engine_to_type = {0: ("static", "hyprpaper"), 1: ("slideshow", "swww"), 2: ("video", "mpvpaper")}

    interval_spin = Gtk.SpinButton.new_with_range(10, 3600, 10)
    images_entry = Gtk.Entry()
    video_entry = Gtk.Entry()

    def reload_manifest():
        m = wallpaper.read_manifest(wp_state["theme"])
        engine_dd.set_selected(type_to_engine.get(m.get("type", "static"), 0))
        try:
            interval_spin.set_value(int(m.get("interval", "300")))
        except ValueError:
            interval_spin.set_value(300)
        images_entry.set_text(m.get("images_dir", "images/"))
        video_entry.set_text(m.get("video", "loop.mp4"))

    def on_theme_dd(_dd, _p):
        i = theme_dd.get_selected()
        if 0 <= i < len(themes):
            wp_state["theme"] = themes[i]
            reload_manifest()

    theme_dd.connect("notify::selected", on_theme_dd)

    wp_section.add(ActionRow("Theme to configure", None, theme_dd))
    wp_section.add(ActionRow("Engine", None, engine_dd))
    wp_section.add(ActionRow("Slideshow interval (sec)", None, interval_spin))
    wp_section.add(ActionRow("Images directory (slideshow)", None, images_entry))
    wp_section.add(ActionRow("Video file (mpvpaper)", None, video_entry))

    save_apply = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    save_apply.set_halign(Gtk.Align.END)
    btn_save_wp = Gtk.Button(label="Save manifest")
    btn_apply_wp = Gtk.Button(label="Save & apply")
    btn_apply_wp.add_css_class("suggested-action")
    save_apply.append(btn_save_wp); save_apply.append(btn_apply_wp)
    wp_section.add(save_apply)

    def collect() -> dict:
        e_idx = engine_dd.get_selected()
        t, eng = engine_to_type.get(e_idx, ("static", "hyprpaper"))
        return {
            "type": t,
            "engine": eng,
            "interval": str(int(interval_spin.get_value())),
            "transition": "fade",
            "images_dir": images_entry.get_text().strip() or "images/",
            "video": video_entry.get_text().strip() or "loop.mp4",
            "videos_dir": "",
        }

    def on_save_wp(_b):
        wallpaper.write_manifest(wp_state["theme"], collect())

    def on_apply_wp(_b):
        wallpaper.write_manifest(wp_state["theme"], collect())
        if wp_state["theme"] == theme_mod.active_theme_name():
            wallpaper.restart(wp_state["theme"])

    btn_save_wp.connect("clicked", on_save_wp)
    btn_apply_wp.connect("clicked", on_apply_wp)

    reload_manifest()
    content.append(wp_section)

    # ---------- BLUE LIGHT ----------
    bl = app.settings.setdefault("system", {}).setdefault("blue_light", {
        "enabled": False, "day_temp": 6500, "night_temp": 3500, "brightness": 1.0,
    })

    bl_section = Section(
        "Blue Light",
        "Warm the screen down by lowering blue channel intensity.",
    )

    def on_bl_toggle(b: bool):
        bl["enabled"] = b
        app.save()
        if b:
            blue_light.set_temperature(int(bl.get("night_temp", 3500)))
        else:
            blue_light.turn_off()

    bl_section.add(switch_row(
        "Enable warm screen",
        "Applies a GLSL shader. Toggling here mirrors the gammastep.sh shortcut.",
        bool(bl.get("enabled", False)),
        on_bl_toggle,
    ))

    def on_night(v: float):
        bl["night_temp"] = int(v)
        app.save()
        if bl.get("enabled"):
            blue_light.set_temperature(int(v))

    bl_section.add(scale_row(
        "Night temperature",
        "Cooler = bluer; warmer = redder.",
        float(bl.get("night_temp", 3500)), 1500, 6500, 100,
        on_night, format_fn=lambda v: f"{int(v)} K",
    ))

    def on_day(v: float):
        bl["day_temp"] = int(v)
        app.save()

    bl_section.add(scale_row(
        "Day temperature",
        "Reserved for future day/night auto-cycling.",
        float(bl.get("day_temp", 6500)), 3000, 6500, 100,
        on_day, format_fn=lambda v: f"{int(v)} K",
    ))

    apply_now = Gtk.Button(label="Apply now")
    apply_now.add_css_class("suggested-action")
    apply_now.connect("clicked", lambda _b: blue_light.set_temperature(int(bl.get("night_temp", 3500))))
    bl_section.add(ActionRow("", None, apply_now))

    content.append(bl_section)

    def on_theme_changed_outer():
        rebuild_swatches()

    scrolled.on_theme_changed = on_theme_changed_outer
    scrolled.on_show = rebuild_swatches
    return scrolled
