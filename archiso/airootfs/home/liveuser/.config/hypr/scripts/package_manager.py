#!/usr/bin/env python3
"""
Hypr Package Manager — a themed GTK4 frontend for pacman + paru/AUR.
Mirrors the visual language of the user's themed Hyprland setup
(JetBrains Mono Nerd Font, translucent dark bg, glowing accent borders).
"""
import os
import re
import shlex
import subprocess
import threading
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib, Gdk, GObject  # noqa: E402

APP_ID = "com.malek.pkgmgr"
TERMINAL = "kitty"
THEMES_DIR = Path.home() / ".config/hypr/themes"
THEME_LINK = Path.home() / ".config/hypr/theme.conf"

# Repo glyphs (Nerd Font)
REPO_GLYPH = {
    "core":      "",
    "extra":     "",
    "multilib":  "",
    "aur":       "",
    "local":     "",
}
REPO_FALLBACK = ""


# ---------- theme loading ----------

def active_theme_name() -> str:
    try:
        target = os.readlink(THEME_LINK)
        return Path(target).parent.name
    except OSError:
        return "blue"

def load_palette() -> dict:
    name = active_theme_name()
    colors_file = THEMES_DIR / name / "colors"
    palette = {"bg": "#000030", "fg": "#00aaff", "border": "#00aaff",
               "inactive": "#000030", "name": name}
    if colors_file.exists():
        for line in colors_file.read_text().splitlines():
            m = re.match(r"(\w+)='?([0-9a-fA-F]{6})'?", line.strip())
            if m:
                key, val = m.group(1), "#" + m.group(2)
                if key == "bg_color":      palette["bg"] = val
                elif key == "fg_color":    palette["fg"] = val
                elif key == "active_border":   palette["border"] = val
                elif key == "inactive_border": palette["inactive"] = val
    return palette


def build_css(p: dict) -> str:
    accent = p["fg"]
    bg = p["bg"]
    # Solid neutral greys read consistently against any theme bg. White-alpha
    # picks up the bg tint (the deep-blue palette especially made them muddy).
    fg1  = "#ededf0"   # primary text
    fg2  = "#9a9aa3"   # secondary text
    fg3  = "#6a6a74"   # tertiary / dim labels
    fg4  = "#4a4a54"   # quaternary / barely-there
    # All backgrounds derive from the theme — no standalone greys that fight
    # the bg color. Dividers use accent at low alpha; hover uses accent tint.
    line = f"alpha({accent}, 0.12)"
    hov  = f"alpha({accent}, 0.07)"
    return f"""
    /* Force every widget transparent so the .root background shows through.
       Adwaita's scrolledwindow/viewport/listbox/entry-text rules otherwise
       paint a grey rectangle on top of our themed bg. */
    * {{
        background-color: transparent;
        background-image: none;
    }}
    window {{
        background-color: {bg};
    }}
    .root {{
        background-color: {bg};
        border-radius: 16px;
        color: {fg1};
        font-family: "JetBrains Mono Nerd Font", "JetBrainsMono Nerd Font", monospace;
    }}
    .titlebar {{
        padding: 18px 22px 6px 22px;
    }}
    .title {{
        font-size: 15px;
        font-weight: bold;
        color: {accent};
        letter-spacing: 0.5px;
    }}
    .subtitle {{
        font-size: 10px;
        color: {fg3};
        margin-top: 2px;
        letter-spacing: 0.3px;
    }}
    .tabbar {{
        padding: 6px 18px 0 18px;
    }}
    .tab {{
        background: transparent;
        border: none;
        color: {fg3};
        padding: 8px 12px;
        margin: 0 2px;
        border-radius: 0;
        font-weight: 500;
        font-size: 12px;
        border-bottom: 2px solid transparent;
    }}
    .tab:hover {{
        color: {fg1};
        background: transparent;
    }}
    .tab.active {{
        color: {accent};
        border-bottom: 2px solid {accent};
        background: transparent;
    }}
    .searchbar {{
        background: transparent;
        border: none;
        border-bottom: 1px solid {line};
        border-radius: 0;
        padding: 12px 22px;
        margin: 0;
        color: {fg1};
        font-size: 13px;
    }}
    .searchbar:focus {{
        border-bottom-color: {accent};
        box-shadow: none;
    }}
    .list scrolledwindow,
    .list listview {{
        background: transparent;
    }}
    .pkgrow {{
        background: transparent;
        border: none;
        border-radius: 8px;
        padding: 9px 18px;
        margin: 1px 10px;
    }}
    .pkgrow:hover {{
        background: {hov};
    }}
    .list row {{
        background: transparent;
        padding: 0;
    }}
    .list row:selected {{
        background: transparent;
    }}
    .list row:selected .pkgrow {{
        background: alpha({accent}, 0.14);
    }}
    .list row:focus {{
        outline: none;
    }}
    .helpbar {{
        background: transparent;
        border-top: 1px solid {line};
        padding: 8px 22px;
        color: {fg4};
        font-size: 10px;
        font-family: "JetBrains Mono Nerd Font", monospace;
        letter-spacing: 0.3px;
    }}
    .helpbar .key {{
        color: {accent};
        font-weight: bold;
    }}
    .pkgname {{
        font-weight: 600;
        color: {fg1};
        font-size: 13px;
    }}
    .pkgver {{
        color: {fg3};
        font-size: 11px;
        margin-left: 10px;
    }}
    .pkgdesc {{
        color: {fg2};
        font-size: 11px;
        margin-top: 2px;
    }}
    .pkgsize {{
        color: {fg2};
        font-size: 11px;
        font-weight: normal;
    }}
    .badge {{
        background: transparent;
        color: alpha({accent}, 0.85);
        border: 1px solid alpha({accent}, 0.3);
        border-radius: 4px;
        padding: 1px 7px;
        font-size: 9px;
        font-weight: 600;
        margin-right: 4px;
        letter-spacing: 0.4px;
    }}
    .badge.aur {{
        color: #ff9ed6;
        border-color: alpha(#ff79c6, 0.35);
    }}
    .badge.orphan {{
        color: #ffd6a0;
        border-color: alpha(#ffb86c, 0.35);
    }}
    .badge.update {{
        color: #80ffa0;
        border-color: alpha(#50fa7b, 0.35);
    }}
    .badge.pinned {{
        color: #d3bcff;
        border-color: alpha(#bd93f9, 0.35);
    }}
    .menubtn {{
        background: transparent;
        border: none;
        color: {fg3};
        padding: 4px 8px;
        margin-left: 2px;
        font-weight: bold;
        min-width: 18px;
    }}
    .menubtn:hover {{
        color: {accent};
    }}
    popover contents {{
        background: alpha({bg}, 0.98);
        border: 1px solid {accent};
        border-radius: 10px;
        padding: 6px;
        color: #ffffff;
    }}
    popover button {{
        background: transparent;
        border: none;
        color: {fg1};
        padding: 8px 16px;
        border-radius: 6px;
        font-size: 12px;
    }}
    popover button:hover {{
        background: alpha({accent}, 0.2);
        color: {accent};
    }}
    .statusbar {{
        padding: 8px 22px 14px 22px;
        border-radius: 0 0 16px 16px;
        color: {fg3};
        font-size: 11px;
    }}
    .actionbtn {{
        background: transparent;
        border: 1px solid alpha({accent}, 0.35);
        border-radius: 6px;
        color: alpha({accent}, 0.9);
        padding: 5px 12px;
        font-weight: 500;
        font-size: 11px;
        margin-left: 4px;
    }}
    .actionbtn:hover {{
        background: alpha({accent}, 0.15);
        color: {accent};
    }}
    .actionbtn.danger {{
        border-color: alpha(#ff5555, 0.35);
        color: alpha(#ff8888, 0.9);
    }}
    .actionbtn.danger:hover {{
        background: alpha(#ff5555, 0.15);
        color: #ff8888;
    }}
    .loading {{
        color: {fg3};
        font-size: 13px;
    }}
    scrollbar {{
        background: transparent;
        border: none;
    }}
    scrollbar slider {{
        background: alpha({accent}, 0.35);
        border-radius: 6px;
        min-width: 6px;
        min-height: 30px;
    }}
    scrollbar slider:hover {{
        background: alpha({accent}, 0.6);
    }}
    """


# ---------- pacman queries ----------

def parse_pacman_Qi(text: str) -> list:
    """Parse `pacman -Qi` output into a list of dicts."""
    pkgs, cur = [], {}
    for line in text.splitlines():
        if not line.strip():
            if cur:
                pkgs.append(cur)
                cur = {}
            continue
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            cur[k.strip()] = v.strip()
        elif cur and line.startswith(" "):
            # continuation line — append to last key
            last = next(reversed(cur))
            cur[last] += " " + line.strip()
    if cur:
        pkgs.append(cur)
    return pkgs


def fmt_size(s: str) -> str:
    """`pacman -Qi` returns size like '12.34 MiB'. Pass through."""
    return s or "?"


def fetch_installed():
    out = subprocess.run(["pacman", "-Qi"], capture_output=True, text=True).stdout
    raw = parse_pacman_Qi(out)
    pkgs = []
    for r in raw:
        pkgs.append({
            "name":   r.get("Name", "?"),
            "ver":    r.get("Version", "?"),
            "desc":   r.get("Description", ""),
            "size":   r.get("Installed Size", "?"),
            "reason": r.get("Install Reason", "?"),
            "repo":   "aur" if r.get("Validated By", "").lower() == "none" else "local",
            "date":   r.get("Install Date", ""),
        })
    return pkgs


def fetch_updates():
    """Use `paru -Qu` (checks both repo + AUR). Returns list of names."""
    try:
        out = subprocess.run(["paru", "-Qu"], capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return []
    names = []
    for line in out.splitlines():
        parts = line.split()
        if parts:
            names.append(parts[0])
    return names


def fetch_orphans():
    out = subprocess.run(["pacman", "-Qtdq"], capture_output=True, text=True).stdout
    return [l.strip() for l in out.splitlines() if l.strip()]


PACMAN_CONF = "/etc/pacman.conf"

def fetch_pins() -> set:
    """Parse IgnorePkg entries from the [options] section of pacman.conf."""
    pins = set()
    in_options = False
    try:
        for line in Path(PACMAN_CONF).read_text().splitlines():
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                in_options = (s == "[options]")
                continue
            if in_options and s and not s.startswith("#"):
                m = re.match(r"IgnorePkg\s*=\s*(.+)", s)
                if m:
                    pins.update(m.group(1).split())
    except OSError:
        pass
    return pins


_PIN_PYSCRIPT = r'''
import sys, re, os, tempfile
name, want_pin = sys.argv[1], sys.argv[2] == "1"
path = "/etc/pacman.conf"
with open(path) as f: lines = f.readlines()
out, in_options, touched = [], False, False
for line in lines:
    s = line.strip()
    if s.startswith("[") and s.endswith("]"):
        in_options = (s == "[options]")
    if in_options and re.match(r"\s*IgnorePkg\s*=", line):
        prefix, _, rhs = line.partition("=")
        items = rhs.split()
        if want_pin and name not in items: items.append(name)
        if not want_pin and name in items: items = [i for i in items if i != name]
        line = prefix + "= " + " ".join(items) + "\n"
        touched = True
    out.append(line)
if want_pin and not touched:
    new = []
    for line in out:
        new.append(line)
        if line.strip() == "[options]":
            new.append("IgnorePkg = " + name + "\n")
    out = new
fd, tmp = tempfile.mkstemp(dir="/etc", prefix="pacman.conf.")
with os.fdopen(fd, "w") as f: f.writelines(out)
os.chmod(tmp, 0o644)
os.replace(tmp, path)
verb = "pinned" if want_pin else "unpinned"
print("\n✓ " + verb + ": " + name)
'''

def build_pin_toggle_cmd(name: str, pin: bool) -> str:
    """Shell command that flips a single package's IgnorePkg state.
    Atomic write via tempfile in /etc, single sudo prompt, prints summary."""
    return (
        f"sudo python3 - {shlex.quote(name)} {'1' if pin else '0'} "
        f"<<'PYEOF'\n{_PIN_PYSCRIPT}\nPYEOF"
    )


def fetch_available_names():
    # pacman -Slq is instant (~0.1s) and covers all enabled repos. AUR is
    # huge and slow to enumerate — query it on-demand via search instead.
    out = subprocess.run(["pacman", "-Slq"], capture_output=True, text=True, timeout=10).stdout
    return [l.strip() for l in out.splitlines() if l.strip()]


def search_aur(query: str):
    """Live AUR search via `paru -Ssa`. Returns list of {name, ver, desc}."""
    if not query or len(query) < 2:
        return []
    try:
        out = subprocess.run(
            ["paru", "-Ssa", query],
            capture_output=True, text=True, timeout=8,
        ).stdout
    except Exception:
        return []
    # Output format (two lines per result):
    #   aur/<name> <version> [+votes ~popularity]
    #       <description>
    results, lines = [], out.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"aur/(\S+)\s+(\S+)", line)
        if m:
            desc = ""
            if i + 1 < len(lines) and lines[i + 1].startswith(" "):
                desc = lines[i + 1].strip()
                i += 1
            results.append({"name": m.group(1), "ver": m.group(2), "desc": desc})
        i += 1
    return results


# ---------- terminal action ----------

def run_in_term(cmd: str):
    """Spawn kitty --hold running a shell command so the user sees output."""
    subprocess.Popen([TERMINAL, "--hold", "sh", "-c", cmd],
                     start_new_session=True)


# ---------- UI ----------

class PkgRow(Gtk.Box):
    __gtype_name__ = "PkgRow"

    def __init__(self, pkg: dict, on_action):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.add_css_class("pkgrow")
        self.pkg = pkg

        repo = pkg.get("repo", "local")
        glyph = REPO_GLYPH.get(repo, REPO_FALLBACK)

        # Icon column
        icon = Gtk.Label(label=glyph)
        icon.add_css_class("pkgname")
        icon.set_xalign(0.5)
        icon.set_size_request(28, -1)
        self.append(icon)

        # Name + desc column
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.set_hexpand(True)
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        name_lbl = Gtk.Label(label=pkg["name"], xalign=0)
        name_lbl.add_css_class("pkgname")
        ver_lbl = Gtk.Label(label=pkg.get("ver", ""), xalign=0)
        ver_lbl.add_css_class("pkgver")
        top.append(name_lbl)
        top.append(ver_lbl)
        info.append(top)
        if pkg.get("desc"):
            d = pkg["desc"]
            if len(d) > 100:
                d = d[:97] + "…"
            desc_lbl = Gtk.Label(label=d, xalign=0)
            desc_lbl.add_css_class("pkgdesc")
            desc_lbl.set_wrap(False)
            desc_lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
            info.append(desc_lbl)
        self.append(info)

        # Badges column
        badges = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        if repo == "aur":
            b = Gtk.Label(label="AUR"); b.add_css_class("badge"); b.add_css_class("aur")
            badges.append(b)
        if pkg.get("reason") == "Explicitly installed":
            b = Gtk.Label(label="explicit"); b.add_css_class("badge")
            badges.append(b)
        if pkg.get("flag") == "update":
            b = Gtk.Label(label="update"); b.add_css_class("badge"); b.add_css_class("update")
            badges.append(b)
        if pkg.get("flag") == "orphan":
            b = Gtk.Label(label="orphan"); b.add_css_class("badge"); b.add_css_class("orphan")
            badges.append(b)
        if pkg.get("pinned"):
            b = Gtk.Label(label=" pinned"); b.add_css_class("badge"); b.add_css_class("pinned")
            badges.append(b)
        self.append(badges)

        # Size
        size_lbl = Gtk.Label(label=fmt_size(pkg.get("size", "")), xalign=1)
        size_lbl.add_css_class("pkgsize")
        size_lbl.set_size_request(90, -1)
        self.append(size_lbl)

        # Action button — explicitly non-focusable so keyboard nav never
        # delegates list-row focus into the button (which would let Enter
        # accidentally activate install/remove).
        action_label, action_kind = pkg.get("_action", ("Info", "info"))
        btn = Gtk.Button(label=action_label)
        btn.add_css_class("actionbtn")
        btn.set_focusable(False)
        btn.set_can_focus(False)
        if action_kind == "remove":
            btn.add_css_class("danger")
        btn.connect("clicked", lambda *_: on_action(pkg, action_kind))
        self.append(btn)

        # Overflow menu — popover is built lazily on first click so we don't
        # construct thousands of unused widgets up front.
        menu_btn = Gtk.MenuButton(label="⋮")
        menu_btn.add_css_class("menubtn")
        self._menu_built = False
        self._menu_btn = menu_btn
        self._menu_pkg = pkg
        self._menu_on_action = on_action
        menu_btn.connect("notify::active", self._lazy_build_menu)
        self.append(menu_btn)

    def _lazy_build_menu(self, btn, _pspec):
        if self._menu_built or not btn.get_active():
            return
        self._menu_built = True
        popover = Gtk.Popover()
        pop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        pkg = self._menu_pkg
        is_installed = pkg.get("_action", ("", ""))[1] in ("remove", "info")
        for label, kind, visible in [
            (" Info",     "info",       True),
            (" Downgrade", "downgrade", is_installed),
            (" Unpin" if pkg.get("pinned") else " Pin",
                          "pin_toggle", is_installed),
        ]:
            if not visible:
                continue
            mb = Gtk.Button(label=label)
            mb.connect("clicked",
                       lambda _b, k=kind: (popover.popdown(),
                                           self._menu_on_action(pkg, k)))
            pop_box.append(mb)
        popover.set_child(pop_box)
        self._menu_btn.set_popover(popover)
        popover.popup()


class PackageManager(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.palette = load_palette()
        self.installed = []
        self.updates_set = set()
        self.orphans_set = set()
        self.pins_set = set()
        self.available = []
        self.current_tab = "installed"
        self.search_text = ""
        self.aur_results = []
        self._aur_search_token = 0
        self._search_debounce_id = 0

    def do_activate(self):
        self._apply_css()

        self.win = Gtk.ApplicationWindow(application=self)
        self.win.set_default_size(1000, 700)
        self.win.set_title("Hypr Package Manager")
        self.win.set_decorated(False)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.add_css_class("root")
        self.win.set_child(root)

        # ── titlebar ────────────────────────────────────────
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        tb.add_css_class("titlebar")

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        t = Gtk.Label(label="  hypr package manager", xalign=0)
        t.add_css_class("title")
        s = Gtk.Label(label=f"theme: {self.palette['name']}", xalign=0)
        s.add_css_class("subtitle")
        title_box.append(t)
        title_box.append(s)
        title_box.set_hexpand(True)
        tb.append(title_box)

        self.status_inline = Gtk.Label(label="loading…")
        self.status_inline.add_css_class("subtitle")
        tb.append(self.status_inline)
        root.append(tb)

        # ── tabs ────────────────────────────────────────────
        self.tabs_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.tabs_box.add_css_class("tabbar")
        self.tab_buttons = {}
        for key, label in [
            ("installed", " Installed"),
            ("explicit",  " Explicit"),
            ("aur",       " AUR"),
            ("updates",   " Updates"),
            ("orphans",   " Orphans"),
            ("available", " Browse"),
        ]:
            b = Gtk.Button(label=label)
            b.add_css_class("tab")
            b.connect("clicked", lambda _b, k=key: self.switch_tab(k))
            self.tab_buttons[key] = b
            self.tabs_box.append(b)
        spacer = Gtk.Box(); spacer.set_hexpand(True)
        self.tabs_box.append(spacer)

        # Update-all button always in tabbar
        upd_btn = Gtk.Button(label=" Update All")
        upd_btn.add_css_class("actionbtn")
        upd_btn.connect("clicked", lambda *_: self._term_and_close("paru -Syu"))
        self.tabs_box.append(upd_btn)
        clean_btn = Gtk.Button(label=" Clean")
        clean_btn.add_css_class("actionbtn")
        clean_btn.connect("clicked", lambda *_: self._term_and_close("paru -Sc && paru -c"))
        self.tabs_box.append(clean_btn)
        root.append(self.tabs_box)

        # ── search ──────────────────────────────────────────
        self.search = Gtk.Entry()
        self.search.set_placeholder_text("  search packages…")
        self.search.add_css_class("searchbar")
        self.search.connect("changed", self._on_search)
        # Swallow Enter — Entry's default "activate" can otherwise propagate
        # and trigger a focused row.
        self.search.connect("activate", lambda *_: None)
        root.append(self.search)

        # ── list ────────────────────────────────────────────
        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.BROWSE)
        # Single-click should NEVER auto-activate a row (would trigger
        # install/remove). Activation only happens via explicit Enter on a
        # focused row — handled in _on_key.
        self.list_box.set_activate_on_single_click(False)
        self.list_box.connect("row-selected", self._on_row_selected)
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_child(self.list_box)
        self.scroll.set_vexpand(True)
        self.scroll.add_css_class("list")
        root.append(self.scroll)

        # ── help bar ────────────────────────────────────────
        help_lbl = Gtk.Label(
            label=(
                "  ↑↓/jk row   ←→/hl tab   enter primary   i info   "
                "d downgrade   p pin   /  search   ctrl+u update   esc close"
            ),
            xalign=0,
        )
        help_lbl.add_css_class("helpbar")
        root.append(help_lbl)

        # ── status bar ──────────────────────────────────────
        self.statusbar = Gtk.Label(label="", xalign=0)
        self.statusbar.add_css_class("statusbar")
        root.append(self.statusbar)

        # Global keyboard map (capture phase so we win over default handlers).
        key = Gtk.EventControllerKey()
        key.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key.connect("key-pressed", self._on_key)
        self.win.add_controller(key)

        self.win.present()
        self.switch_tab("installed")
        self._load_data_async()
        # Focus search by default so the user can type-to-filter immediately.
        GLib.idle_add(lambda: (self.search.grab_focus(), False)[1])

    # ---------- CSS ----------

    def _apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(build_css(self.palette).encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    # ---------- data loading ----------

    def _load_data_async(self):
        # Run all queries in parallel so a slow `paru -Qu` (AUR check) doesn't
        # block the available list or installed view.
        def load_installed():
            installed = fetch_installed()
            orphans = set(fetch_orphans())
            pins = fetch_pins()
            GLib.idle_add(self._installed_loaded, installed, orphans, pins)
        def load_updates():
            GLib.idle_add(self._updates_loaded, set(fetch_updates()))
        def load_available():
            GLib.idle_add(self._available_loaded, fetch_available_names())
        for fn in (load_installed, load_available, load_updates):
            threading.Thread(target=fn, daemon=True).start()

    def _installed_loaded(self, installed, orphans, pins):
        self.installed = installed
        self.orphans_set = orphans
        self.pins_set = pins
        self.refresh_view()
        total = sum(_size_to_mb(p.get("size", "")) for p in installed)
        self.statusbar.set_label(
            f" {len(installed)} packages installed · {total:.0f} MiB total"
        )

    def _updates_loaded(self, updates):
        self.updates_set = updates
        if self.current_tab == "updates":
            self.refresh_view()
        if updates:
            t = self.tab_buttons["updates"].get_label()
            self.tab_buttons["updates"].set_label(f"{t} ({len(updates)})")

    def _available_loaded(self, available):
        self.available = available
        if self.current_tab == "available":
            self.refresh_view()

    # ---------- tabs ----------

    def switch_tab(self, key):
        self.current_tab = key
        for k, b in self.tab_buttons.items():
            if k == key:
                b.add_css_class("active")
            else:
                b.remove_css_class("active")
        self.refresh_view()

    def _on_search(self, entry):
        # Debounce keystrokes so typing doesn't rebuild the list per character.
        if self._search_debounce_id:
            GLib.source_remove(self._search_debounce_id)
        self._search_debounce_id = GLib.timeout_add(
            180, self._apply_search, entry.get_text().lower().strip()
        )

    def _apply_search(self, text):
        self._search_debounce_id = 0
        self.search_text = text
        if self.current_tab == "available" and len(self.search_text) >= 2:
            self._aur_search_token += 1
            token = self._aur_search_token
            q = self.search_text
            def work():
                results = search_aur(q)
                def apply():
                    if token == self._aur_search_token:
                        self.aur_results = results
                        if self.current_tab == "available":
                            self.refresh_view()
                    return False
                GLib.idle_add(apply)
            threading.Thread(target=work, daemon=True).start()
        else:
            self.aur_results = []
        self.refresh_view()
        return False

    # Ordered list of tab keys for cycling and Alt+N shortcuts.
    TAB_ORDER = ["installed", "explicit", "aur", "updates", "orphans", "available"]

    def _focus_list(self):
        """Move focus into the list, selecting the first row if needed.
        We focus the ListBox itself (not the row), so subsequent letter keys
        hit our keymap instead of being eaten by a focusable child button."""
        row = self.list_box.get_selected_row() or self.list_box.get_row_at_index(0)
        if row is not None:
            self.list_box.select_row(row)
        self.list_box.grab_focus()

    def _on_row_selected(self, _box, row):
        if row is None:
            return
        # Scroll the selected row into view (no animation = snappier).
        adj = self.scroll.get_vadjustment()
        if adj is None:
            return
        alloc = row.get_allocation()
        top = alloc.y
        bot = top + alloc.height
        cur = adj.get_value()
        page = adj.get_page_size()
        if top < cur:
            adj.set_value(top)
        elif bot > cur + page:
            adj.set_value(bot - page)

    def _cycle_tab(self, delta: int):
        try:
            idx = self.TAB_ORDER.index(self.current_tab)
        except ValueError:
            idx = 0
        self.switch_tab(self.TAB_ORDER[(idx + delta) % len(self.TAB_ORDER)])

    def _selected_pkg(self):
        row = self.list_box.get_selected_row()
        return getattr(row, "pkg", None) if row else None

    def _row_primary(self, row):
        """Trigger the primary (Install / Remove / Installed-info) action."""
        pkg = getattr(row, "pkg", None)
        if pkg:
            _, kind = pkg.get("_action", ("Info", "info"))
            self._on_action(pkg, kind)

    def _on_key(self, ctrl, keyval, code, state):
        search_focused = self.search.has_focus_within()

        # ── Search-focused branch ───────────────────────────────────────
        # While typing in the search field, ONLY Esc and Down are intercepted.
        # Every other key (letters, ctrl-combos, arrows) is left for the
        # Entry to handle normally. No shortcut can spawn a terminal here.
        if search_focused:
            if keyval == Gdk.KEY_Escape:
                if self.search.get_text():
                    self.search.set_text("")
                else:
                    self.win.close()
                return True
            if keyval == Gdk.KEY_Down:
                self._focus_list()
                return True
            if keyval == Gdk.KEY_Return:
                # consume Enter so the Entry's default activate signal can't
                # bubble to a focused row.
                return True
            return False

        # ── List-focused branch ─────────────────────────────────────────
        ctrl_mod = bool(state & Gdk.ModifierType.CONTROL_MASK)
        alt_mod  = bool(state & Gdk.ModifierType.ALT_MASK)

        if keyval == Gdk.KEY_Escape:
            self.win.close()
            return True

        # Alt+1..6 → direct tab.
        if alt_mod and Gdk.KEY_1 <= keyval <= Gdk.KEY_6:
            self.switch_tab(self.TAB_ORDER[keyval - Gdk.KEY_1])
            return True

        if ctrl_mod and keyval in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab):
            self._cycle_tab(-1 if state & Gdk.ModifierType.SHIFT_MASK else 1)
            return True

        if ctrl_mod and keyval == Gdk.KEY_u:
            self._term_and_close("paru -Syu")
            return True
        if ctrl_mod and keyval == Gdk.KEY_k:
            self._term_and_close("paru -Sc && paru -c")
            return True
        if ctrl_mod and keyval in (Gdk.KEY_f, Gdk.KEY_l):
            self.search.grab_focus()
            return True

        if keyval == Gdk.KEY_slash:
            self.search.grab_focus()
            return True

        # vim j/k → down/up in the list.
        if keyval == Gdk.KEY_j:
            self.list_box.child_focus(Gtk.DirectionType.DOWN); return True
        if keyval == Gdk.KEY_k:
            self.list_box.child_focus(Gtk.DirectionType.UP); return True

        # Left/Right (or h/l) → cycle tabs.
        if keyval in (Gdk.KEY_Left, Gdk.KEY_h):
            self._cycle_tab(-1); return True
        if keyval in (Gdk.KEY_Right, Gdk.KEY_l):
            self._cycle_tab(1); return True

        pkg = self._selected_pkg()
        if pkg is None:
            return False

        if keyval == Gdk.KEY_Return:
            _, kind = pkg.get("_action", ("Info", "info"))
            self._on_action(pkg, kind)
            return True
        if keyval == Gdk.KEY_i:
            self._on_action(pkg, "info"); return True
        if keyval == Gdk.KEY_d:
            # Downgrade only makes sense for installed packages.
            if pkg.get("_action", ("", ""))[1] in ("remove", "info"):
                self._on_action(pkg, "downgrade")
            return True
        if keyval == Gdk.KEY_p:
            if pkg.get("_action", ("", ""))[1] in ("remove", "info"):
                self._on_action(pkg, "pin_toggle")
            return True
        if keyval == Gdk.KEY_r:
            if pkg.get("_action", ("", ""))[1] == "remove":
                self._on_action(pkg, "remove")
            return True
        return False

    # ---------- view rendering ----------

    def _current_rows(self):
        tab = self.current_tab
        if tab == "available":
            # Repo packages (instant filter on the cached name list).
            names = self.available
            if self.search_text:
                names = [n for n in names if self.search_text in n.lower()]
            installed_names = {p["name"] for p in self.installed}
            repo_rows = [{
                "name": n, "ver": "", "desc": "", "size": "",
                "repo": "core" if n not in installed_names else "local",
                "reason": "",
                "_action": ("Installed", "info") if n in installed_names
                           else ("Install", "install"),
            } for n in names[:300]]
            # AUR results (async — populated when search runs).
            aur_rows = [{
                "name": r["name"], "ver": r["ver"], "desc": r["desc"],
                "size": "", "repo": "aur", "reason": "",
                "_action": ("Install", "install"),
            } for r in self.aur_results[:100]]
            return repo_rows + aur_rows
        # All other tabs operate on installed list
        rows = list(self.installed)
        if tab == "explicit":
            rows = [p for p in rows if p.get("reason") == "Explicitly installed"]
        elif tab == "aur":
            rows = [p for p in rows if p.get("repo") == "aur"]
        elif tab == "updates":
            rows = [p for p in rows if p["name"] in self.updates_set]
            for r in rows: r["flag"] = "update"
        elif tab == "orphans":
            rows = [p for p in rows if p["name"] in self.orphans_set]
            for r in rows: r["flag"] = "orphan"
        # installed/all keeps all
        if tab in ("installed", "explicit", "aur", "updates"):
            for r in rows:
                if r["name"] in self.orphans_set:
                    r["flag"] = "orphan"
        for r in rows:
            r["pinned"] = r["name"] in self.pins_set
        if self.search_text:
            q = self.search_text
            rows = [r for r in rows
                    if q in r["name"].lower() or q in r.get("desc", "").lower()]
        for r in rows:
            r["_action"] = ("Update", "install") if tab == "updates" \
                else ("Remove", "remove")
        return rows

    def refresh_view(self):
        # Clear
        child = self.list_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.list_box.remove(child)
            child = nxt

        if self.current_tab == "available" and not self.available:
            lbl = Gtk.Label(label="loading repo index…")
            lbl.add_css_class("loading")
            lbl.set_margin_top(40); lbl.set_margin_bottom(40)
            self.list_box.append(lbl)
            return
        if not self.installed and self.current_tab != "available":
            lbl = Gtk.Label(label="loading packages…")
            lbl.add_css_class("loading")
            lbl.set_margin_top(40); lbl.set_margin_bottom(40)
            self.list_box.append(lbl)
            return

        rows = self._current_rows()
        if not rows:
            msg = " no matches" if self.search_text else " nothing to show"
            lbl = Gtk.Label(label=msg)
            lbl.add_css_class("loading")
            lbl.set_margin_top(40); lbl.set_margin_bottom(40)
            self.list_box.append(lbl)
            return

        # Cap rendered rows — building thousands of GTK widgets blocks the
        # main loop and makes keyboard nav stutter. The search bar is the
        # escape hatch for finding anything beyond the cap.
        ROW_CAP = 200
        total = len(rows)
        self.status_inline.set_label(f"{total} packages")
        for pkg in rows[:ROW_CAP]:
            row = Gtk.ListBoxRow()
            row.set_child(PkgRow(pkg, self._on_action))
            row.pkg = pkg
            self.list_box.append(row)
        if total > ROW_CAP:
            more = Gtk.Label(
                label=f" showing first {ROW_CAP} of {total} — type to filter"
            )
            more.add_css_class("loading")
            more.set_margin_top(12); more.set_margin_bottom(12)
            placeholder = Gtk.ListBoxRow()
            placeholder.set_selectable(False)
            placeholder.set_child(more)
            self.list_box.append(placeholder)
        first = self.list_box.get_row_at_index(0)
        if first is not None:
            self.list_box.select_row(first)

    def _term_and_close(self, cmd):
        run_in_term(cmd)
        self.win.close()

    def _on_action(self, pkg, kind):
        name = pkg["name"]
        q = shlex.quote(name)
        if kind == "install":
            run_in_term(f"paru -S --needed {q}")
        elif kind == "remove":
            run_in_term(f"paru -Rns {q}")
        elif kind == "info":
            run_in_term(f"paru -Si {q} | less -R")
        elif kind == "downgrade":
            # `downgrade` is interactive — lists cached + ALA versions, lets
            # the user pick. Auto-offers to add an IgnorePkg pin after.
            run_in_term(f"sudo downgrade {q}")
        elif kind == "pin_toggle":
            currently_pinned = name in self.pins_set
            run_in_term(build_pin_toggle_cmd(name, pin=not currently_pinned))
        self.win.close()


def _size_to_mb(s: str) -> float:
    m = re.match(r"([\d.]+)\s*(KiB|MiB|GiB|B)", s or "")
    if not m: return 0.0
    val, unit = float(m.group(1)), m.group(2)
    return {"B": val / 1024 / 1024, "KiB": val / 1024,
            "MiB": val, "GiB": val * 1024}.get(unit, 0.0)


if __name__ == "__main__":
    app = PackageManager()
    app.run(None)
