"""Main Gtk.Application — wires sidebar, pages, live theming."""

import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Gio, GLib, GObject  # noqa: E402

from . import model, theme
from .pages.dashboard import build as build_dashboard
from .pages.journal import build as build_journal
from .pages.calendar import build as build_calendar
from .pages.goals import build as build_goals
from .pages.filters import build as build_filters
from .pages.pomodoro import build as build_pomodoro
from .pages.shortcuts import build as build_shortcuts
from .pages.appearance import build as build_appearance
from .pages.system import build as build_system


SIDEBAR_ITEMS = [
    ("dashboard",  "Dashboard",   ""),  # chart-line
    ("journal",    "Journal",     ""),  # book
    ("calendar",   "Calendar",    ""),  # calendar
    ("goals",      "Goals",       ""),  # bullseye
    ("pomodoro",   "Pomodoro",    ""),  # clock
    ("filters",    "Web Filters", ""),  # ban
    ("appearance", "Appearance",  ""),  # palette
    ("shortcuts",  "Shortcuts",   ""),  # keyboard
    ("system",     "System",      ""),  # cog
]


class SettingsApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.malek.hyprsettings",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.settings = model.load()
        self._css_provider = None
        self._sidebar_buttons: dict[str, Gtk.Button] = {}
        self._pages: dict[str, Gtk.Widget] = {}
        self._theme_monitor = None
        self._window = None

    # ---------- lifecycle ----------

    def do_activate(self):
        self._apply_theme()

        self._window = Gtk.ApplicationWindow(application=self, title="Settings")
        self._window.set_default_size(1180, 760)
        self._window.add_css_class("settings-app")

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._window.set_child(root)

        # ---- Sidebar ----
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        sidebar.add_css_class("sidebar")
        sidebar.set_size_request(220, -1)
        root.append(sidebar)

        header = Gtk.Label(label="  Settings", xalign=0)  # hyprland-ish icon
        header.add_css_class("sidebar-header")
        sidebar.append(header)

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(180)
        self._stack.set_hexpand(True)
        self._stack.set_vexpand(True)

        # Build pages
        builders = {
            "dashboard":  build_dashboard,
            "journal":    build_journal,
            "calendar":   build_calendar,
            "goals":      build_goals,
            "pomodoro":   build_pomodoro,
            "filters":    build_filters,
            "appearance": build_appearance,
            "shortcuts":  build_shortcuts,
            "system":     build_system,
        }

        for name, title, icon in SIDEBAR_ITEMS:
            btn = self._make_sidebar_button(name, title, icon)
            sidebar.append(btn)
            self._sidebar_buttons[name] = btn

            try:
                page = builders[name](self)
            except Exception as e:
                page = self._error_placeholder(name, e)
            self._stack.add_named(page, name)
            self._pages[name] = page

        # spacer at bottom
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        sidebar.append(spacer)

        # active theme footer
        self._theme_footer = Gtk.Label(xalign=0)
        self._theme_footer.add_css_class("dim-label")
        self._theme_footer.set_margin_top(8)
        self._theme_footer.set_margin_bottom(4)
        self._theme_footer.set_margin_start(14)
        sidebar.append(self._theme_footer)
        self._update_theme_footer()

        root.append(self._stack)

        self._stack.connect("notify::visible-child-name", self._on_page_changed)
        self._select_page("dashboard")

        # ---- Theme file monitor ----
        try:
            f = Gio.File.new_for_path(str(theme.THEME_LINK))
            # Watch the symlink itself (not the target).
            self._theme_monitor = f.monitor_file(
                Gio.FileMonitorFlags.WATCH_HARD_LINKS, None
            )
            self._theme_monitor.connect("changed", self._on_theme_changed)
        except GLib.Error as e:
            print(f"[settings] theme monitor failed: {e}")

        self._window.present()

    # ---------- sidebar ----------

    def _make_sidebar_button(self, name: str, title: str, icon: str) -> Gtk.Button:
        b = Gtk.Button()
        b.add_css_class("sidebar-row")
        b.set_hexpand(True)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.set_halign(Gtk.Align.START)

        icon_lbl = Gtk.Label(label=icon + "‎ ‎")  # LRM-pad for Nerd Font
        icon_lbl.add_css_class("mono")
        icon_lbl.add_css_class("row-icon")
        row.append(icon_lbl)

        text_lbl = Gtk.Label(label=title)
        row.append(text_lbl)
        b.set_child(row)

        b.connect("clicked", lambda _b, n=name: self._select_page(n))
        return b

    def _select_page(self, name: str):
        if name not in self._pages:
            return
        self._stack.set_visible_child_name(name)

    def _on_page_changed(self, *_):
        active = self._stack.get_visible_child_name()
        for n, btn in self._sidebar_buttons.items():
            if n == active:
                btn.add_css_class("active")
            else:
                btn.remove_css_class("active")
        # refresh dynamic pages on entry
        page = self._pages.get(active)
        if page and hasattr(page, "on_show"):
            try:
                page.on_show()
            except Exception as e:
                print(f"[settings] on_show({active}) failed: {e}")

    # ---------- theming ----------

    def _apply_theme(self):
        palette = theme.load_palette()
        css = theme.generate_css(palette)

        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode("utf-8"))
        display = Gdk.Display.get_default()
        if self._css_provider is not None:
            Gtk.StyleContext.remove_provider_for_display(display, self._css_provider)
        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 100,
        )
        self._css_provider = provider

        Gtk.Settings.get_default().props.gtk_application_prefer_dark_theme = True
        self._palette = theme.derive(palette)

        # Cache active theme in settings for other consumers.
        cur = palette["name"]
        sys_ = self.settings.setdefault("system", {})
        if sys_.get("active_theme") != cur:
            sys_["active_theme"] = cur
            self.save()

    def _on_theme_changed(self, _monitor, _file, _other, event_type):
        if event_type in (
            Gio.FileMonitorEvent.CHANGES_DONE_HINT,
            Gio.FileMonitorEvent.CHANGED,
            Gio.FileMonitorEvent.CREATED,
            Gio.FileMonitorEvent.RENAMED,
        ):
            # debounce
            GLib.timeout_add(120, self._reapply_and_notify)

    def _reapply_and_notify(self) -> bool:
        self._apply_theme()
        self._update_theme_footer()
        # Let pages refresh anything that uses raw palette colors.
        for p in self._pages.values():
            if hasattr(p, "on_theme_changed"):
                try:
                    p.on_theme_changed()
                except Exception as e:
                    print(f"[settings] on_theme_changed: {e}")
        return False

    def _update_theme_footer(self):
        if not hasattr(self, "_theme_footer"):
            return
        name = theme.active_theme_name()
        self._theme_footer.set_label(f"theme · {name}")

    def palette(self) -> dict:
        return self._palette

    # ---------- model ----------

    def save(self) -> None:
        model.save(self.settings)

    def reload_settings(self) -> None:
        self.settings = model.load()

    # ---------- toast ----------

    def toast(self, message: str):
        if self._window is None:
            return
        # Simple inline toast at bottom of window.
        overlay = self._window.get_child()
        revealer = getattr(self, "_toast_revealer", None)
        if revealer is None:
            # Wrap in overlay if not already.
            return
        # (lightweight: just print for now — overlay UX optional)
        print(f"[toast] {message}")

    # ---------- error placeholder ----------

    def _error_placeholder(self, name: str, exc: Exception) -> Gtk.Widget:
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        b.set_margin_top(40); b.set_margin_start(40); b.set_margin_end(40)
        title = Gtk.Label(label=f"Failed to load page: {name}", xalign=0)
        title.add_css_class("page-title")
        sub = Gtk.Label(label=str(exc), wrap=True, xalign=0)
        sub.add_css_class("danger")
        b.append(title); b.append(sub)
        import traceback; traceback.print_exc()
        return b


def run() -> int:
    app = SettingsApp()
    return app.run(sys.argv)
