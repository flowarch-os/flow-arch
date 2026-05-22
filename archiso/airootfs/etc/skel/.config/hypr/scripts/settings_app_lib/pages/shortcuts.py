"""Shortcuts: Hyprland keybinding editor with press-a-key capture."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

from ..services import hyprland as hypr
from ..widgets.section import scrollable_page, Section


MOD_FLAGS = [
    (Gdk.ModifierType.SUPER_MASK,    "SUPER"),
    (Gdk.ModifierType.CONTROL_MASK,  "CTRL"),
    (Gdk.ModifierType.SHIFT_MASK,    "SHIFT"),
    (Gdk.ModifierType.ALT_MASK,      "ALT"),
]


def _decode_mods(state: int) -> str:
    out = []
    for mask, name in MOD_FLAGS:
        if state & mask:
            out.append(name)
    return " ".join(out)


def _format_keysym(keyval: int) -> str:
    name = Gdk.keyval_name(keyval) or ""
    if not name:
        return ""
    if len(name) == 1:
        return name.upper()
    return hypr.humanize_key(name)


def _binding_pretty(b: dict) -> str:
    parts = []
    if b.get("mods"):
        parts.append(b["mods"].upper())
    parts.append(b.get("key", "").upper())
    return " + ".join(p for p in parts if p)


def _action_pretty(b: dict) -> str:
    action = b.get("action", "")
    args = b.get("args", "")
    if action == "exec":
        return f"Run: {args}"
    if action == "workspace":
        return f"Workspace {args}"
    if action == "movetoworkspace":
        return f"Move window to {args}"
    if action == "killactive":
        return "Close active window"
    if action == "togglefloating":
        return "Toggle floating"
    if action == "fullscreen":
        return "Toggle fullscreen"
    return f"{action} {args}".strip()


def build(app):
    actions = []
    save_btn = Gtk.Button(label="Save & Reload Hyprland")
    save_btn.add_css_class("suggested-action")
    reload_btn = Gtk.Button(label="Discard changes")
    reload_btn.add_css_class("flat")
    actions.extend([reload_btn, save_btn])

    scrolled, content = scrollable_page(
        "Shortcuts",
        "Edit Hyprland keybindings. Click a binding's chip to capture a new key combo.",
        actions=actions,
    )

    state = {"bindings": [], "dirty": False}

    list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    content.append(list_box)

    def _clear(b: Gtk.Box):
        c = b.get_first_child()
        while c:
            n = c.get_next_sibling()
            b.remove(c)
            c = n

    def render():
        _clear(list_box)
        sections: dict[str, list[dict]] = {}
        order: list[str] = []
        for b in state["bindings"]:
            sec = b.get("section", "General")
            if sec not in sections:
                sections[sec] = []
                order.append(sec)
            sections[sec].append(b)

        for sec in order:
            s = Section(sec)
            for b in sections[sec]:
                s.add(_binding_row(state, b, on_change=lambda: mark_dirty()))
            list_box.append(s)

    def mark_dirty():
        state["dirty"] = True
        save_btn.set_label("Save & Reload Hyprland *")

    def load():
        state["bindings"] = hypr.load_bindings()
        state["dirty"] = False
        save_btn.set_label("Save & Reload Hyprland")
        render()

    def on_save(_b):
        if not state["bindings"]:
            return
        ok = hypr.save_bindings(state["bindings"])
        if ok:
            state["dirty"] = False
            save_btn.set_label("Save & Reload Hyprland")

    save_btn.connect("clicked", on_save)
    reload_btn.connect("clicked", lambda _b: load())

    load()
    scrolled.on_show = load
    return scrolled


def _binding_row(state, b: dict, on_change) -> Gtk.Box:
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    row.add_css_class("action-row")

    desc = Gtk.Label(label=_action_pretty(b), xalign=0)
    desc.set_hexpand(True)
    desc.set_ellipsize(3)
    desc.add_css_class("row-title")
    row.append(desc)

    chip = Gtk.Button(label=_binding_pretty(b) or "—")
    chip.add_css_class("chip")
    chip.add_css_class("mono")
    chip.set_tooltip_text("Click and press the key combination you want")

    def on_chip(_b):
        _start_capture(chip, b, on_change)

    chip.connect("clicked", on_chip)
    row.append(chip)

    return row


def _start_capture(chip: Gtk.Button, binding: dict, on_change):
    chip.set_label("Press a key…")
    chip.add_css_class("active")
    win = Gtk.Window(title="Capture key")
    win.set_default_size(360, 140)
    win.set_modal(True)
    win.set_transient_for(chip.get_root())

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    box.add_css_class("page")
    box.set_margin_top(20); box.set_margin_bottom(20)
    box.set_margin_start(20); box.set_margin_end(20)
    win.set_child(box)

    title = Gtk.Label(label="Press the new key combination", xalign=0)
    title.add_css_class("page-title")
    box.append(title)

    preview = Gtk.Label(label="…", xalign=0)
    preview.add_css_class("mono")
    preview.add_css_class("section-title")
    box.append(preview)

    btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    btn_row.set_halign(Gtk.Align.END)
    btn_cancel = Gtk.Button(label="Cancel")
    btn_cancel.connect("clicked", lambda _b: win.close())
    btn_row.append(btn_cancel)
    box.append(btn_row)

    key_ctrl = Gtk.EventControllerKey()

    def on_key(_c, keyval, _kcode, modstate):
        # Ignore lone modifier press
        name = Gdk.keyval_name(keyval) or ""
        if name in ("Super_L", "Super_R", "Control_L", "Control_R",
                    "Shift_L", "Shift_R", "Alt_L", "Alt_R", "Meta_L", "Meta_R"):
            preview.set_label(_decode_mods(modstate) + " + …")
            return False
        mods_str = _decode_mods(modstate)
        key_str = _format_keysym(keyval)
        binding["mods"] = mods_str
        binding["key"] = key_str
        chip.set_label(f"{mods_str + ' + ' if mods_str else ''}{key_str}")
        chip.remove_css_class("active")
        on_change()
        win.close()
        return True

    key_ctrl.connect("key-pressed", on_key)
    win.add_controller(key_ctrl)
    win.present()
