"""System page: timezone, default audio sink, hypridle dim."""

import os
import subprocess
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from ..services import timezone as tz_svc, audio as audio_svc
from ..widgets.section import scrollable_page, Section
from ..widgets.row import ActionRow


HYPRIDLE_CONF = Path.home() / ".config/hypr/hypridle.conf"


def build(app):
    scrolled, content = scrollable_page(
        "System",
        "Timezone, audio output, and idle-timeout controls.",
    )

    # ---------- Timezone ----------
    tz_section = Section("Timezone", f"Currently: {tz_svc.current_timezone() or 'unknown'}")

    tz_search = Gtk.SearchEntry()
    tz_search.set_placeholder_text("Type to filter…")
    tz_section.add(tz_search)

    list_scroll = Gtk.ScrolledWindow()
    list_scroll.set_min_content_height(220)
    list_scroll.set_vexpand(False)

    tz_list = Gtk.ListBox()
    tz_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
    list_scroll.set_child(tz_list)
    tz_section.add(list_scroll)

    all_tz = tz_svc.list_timezones()
    current_tz = tz_svc.current_timezone()

    def rebuild_list(filter_text: str = ""):
        child = tz_list.get_first_child()
        while child:
            n = child.get_next_sibling()
            tz_list.remove(child)
            child = n
        ft = filter_text.lower()
        for t in all_tz[:1500]:
            if ft and ft not in t.lower():
                continue
            lbl = Gtk.Label(label=t, xalign=0)
            lbl.set_margin_top(4); lbl.set_margin_bottom(4)
            lbl.set_margin_start(8); lbl.set_margin_end(8)
            tz_list.append(lbl)
            if t == current_tz:
                # mark selected by row reference at parent
                last_row = tz_list.get_last_child()
                tz_list.select_row(last_row)

    rebuild_list()
    tz_search.connect("search-changed", lambda e: rebuild_list(e.get_text()))

    apply_tz_btn = Gtk.Button(label="Apply timezone")
    apply_tz_btn.add_css_class("suggested-action")
    status_lbl = Gtk.Label(xalign=0)
    status_lbl.add_css_class("dim-label")

    def on_apply_tz(_b):
        row = tz_list.get_selected_row()
        if row is None:
            status_lbl.set_label("Select a timezone first.")
            return
        # Find the label inside the row
        lbl = row.get_child()
        if not isinstance(lbl, Gtk.Label):
            return
        tz = lbl.get_label().strip()
        ok, err = tz_svc.set_timezone(tz)
        if ok:
            status_lbl.set_label(f"Set timezone to {tz}.")
            status_lbl.remove_css_class("danger")
            status_lbl.add_css_class("success")
        else:
            status_lbl.set_label(f"Failed: {err}")
            status_lbl.add_css_class("danger")

    apply_tz_btn.connect("clicked", on_apply_tz)
    tz_section.add(apply_tz_btn)
    tz_section.add(status_lbl)
    content.append(tz_section)

    # ---------- Audio ----------
    audio_section = Section("Default Audio Output", "Pick which sink Pulse/Pipewire routes to by default.")

    sinks = audio_svc.list_sinks()
    sink_names = [s["name"] for s in sinks]
    sink_descs = [s["description"] for s in sinks] or ["(no sinks found)"]
    sink_default_idx = next((i for i, s in enumerate(sinks) if s["default"]), 0)

    sink_dd = Gtk.DropDown.new_from_strings(sink_descs)
    if sinks:
        sink_dd.set_selected(sink_default_idx)
    audio_section.add(ActionRow("Default sink", None, sink_dd))

    apply_sink_btn = Gtk.Button(label="Apply")
    apply_sink_btn.add_css_class("suggested-action")

    def on_apply_sink(_b):
        i = sink_dd.get_selected()
        if 0 <= i < len(sink_names):
            audio_svc.set_default_sink(sink_names[i])

    apply_sink_btn.connect("clicked", on_apply_sink)
    audio_section.add(ActionRow("", None, apply_sink_btn))
    content.append(audio_section)

    # ---------- Hypridle ----------
    idle_section = Section(
        "Idle & Lock",
        "Read-only summary of hypridle.conf — edit the file for full control.",
    )
    summary = _hypridle_summary()
    s_lbl = Gtk.Label(label=summary, xalign=0, wrap=True)
    s_lbl.add_css_class("mono")
    s_lbl.add_css_class("dim-label")
    idle_section.add(s_lbl)

    edit_btn = Gtk.Button(label="Open hypridle.conf")
    edit_btn.add_css_class("flat")

    def on_edit(_b):
        if HYPRIDLE_CONF.exists():
            subprocess.Popen(["xdg-open", str(HYPRIDLE_CONF)])

    edit_btn.connect("clicked", on_edit)

    restart_btn = Gtk.Button(label="Restart hypridle")
    restart_btn.add_css_class("flat")

    def on_restart(_b):
        subprocess.run(["pkill", "-x", "hypridle"], check=False)
        subprocess.Popen(["setsid", "hypridle"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         stdin=subprocess.DEVNULL)

    restart_btn.connect("clicked", on_restart)

    btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    btn_row.set_halign(Gtk.Align.END)
    btn_row.append(edit_btn)
    btn_row.append(restart_btn)
    idle_section.add(btn_row)

    content.append(idle_section)

    return scrolled


def _hypridle_summary() -> str:
    if not HYPRIDLE_CONF.exists():
        return "hypridle.conf not found."
    try:
        text = HYPRIDLE_CONF.read_text()
    except OSError as e:
        return f"Read error: {e}"
    # Pull "timeout = N" lines + the on-timeout commands.
    lines = []
    for ln in text.splitlines():
        l = ln.strip()
        if l.startswith("timeout") or l.startswith("on-timeout") or l.startswith("on-resume"):
            lines.append(l)
    if not lines:
        return text[:400] + ("…" if len(text) > 400 else "")
    return "\n".join(lines[:30])
