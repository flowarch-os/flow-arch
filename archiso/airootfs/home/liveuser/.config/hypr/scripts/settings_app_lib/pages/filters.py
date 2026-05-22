"""Web Filters: ad blocking, global blacklist, keywords, visual guard, media blackout, goal-specific."""

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .. import model
from ..services import filters as filter_svc
from ..widgets.section import scrollable_page, Section
from ..widgets.row import switch_row, scale_row, ActionRow


def _clear(box: Gtk.Box) -> None:
    c = box.get_first_child()
    while c:
        n = c.get_next_sibling()
        box.remove(c)
        c = n


def _chip_row(label: str, on_delete) -> Gtk.Box:
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    row.add_css_class("action-row")
    lbl = Gtk.Label(label=label, xalign=0)
    lbl.set_hexpand(True)
    lbl.set_ellipsize(3)
    btn = Gtk.Button(label="Remove")
    btn.add_css_class("flat"); btn.add_css_class("destructive-action")
    btn.connect("clicked", lambda _b: on_delete())
    row.append(lbl); row.append(btn)
    return row


def _domain_input(placeholder: str, on_apply, btn_label: str = "Block") -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    box.add_css_class("action-row")
    e = Gtk.Entry(placeholder_text=placeholder)
    e.set_hexpand(True)
    btn = Gtk.Button(label=btn_label)
    btn.add_css_class("suggested-action")

    def commit():
        text = e.get_text().strip()
        if not text:
            return
        on_apply(text)
        e.set_text("")
    e.connect("activate", lambda _: commit())
    btn.connect("clicked", lambda _: commit())
    box.append(e); box.append(btn)
    return box


def build(app):
    scrolled, content = scrollable_page(
        "Web Filters",
        "Block sites, keywords, and media — system-wide and per-goal.",
    )
    settings = app.settings
    f = settings.setdefault("filters", {})
    f.setdefault("global_blacklist", [])
    f.setdefault("keyword_blacklist", [])
    f.setdefault("goal_filters", {})
    f.setdefault("visual_guard", {"enabled": False, "sensitivity": 50})
    f.setdefault("media_blackout", {"enabled": False, "allowlist": []})

    # ---------- Ad Blocking ----------
    refresh_btn = Gtk.Button(label="Refresh Hosts")
    refresh_btn.add_css_class("flat")
    refresh_btn.set_tooltip_text("Re-download/refresh the ad-block hosts list (sudo).")
    refresh_btn.connect("clicked", lambda _b: filter_svc.refresh_ad_hosts())

    ad_section = Section(
        "Ad Blocking",
        "System-wide hosts-based ad blocking via /etc/hosts.",
        actions=[refresh_btn],
    )

    def on_ad(b: bool):
        f["ad_blocking"] = b
        app.save()
        filter_svc.set_ad_blocking(b)

    ad_section.add(switch_row(
        "Enable ad blocking",
        "Modifies /etc/hosts to block known ad domains.",
        bool(f.get("ad_blocking", False)),
        on_ad,
    ))
    content.append(ad_section)

    # ---------- Global Blacklist ----------
    gb_section = Section(
        "Global Blacklist",
        "Sites you always want blocked, regardless of which goal is active.",
    )
    gb_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

    def add_global(text: str):
        for d in model.clean_and_extract_domains(text):
            if d not in f["global_blacklist"]:
                f["global_blacklist"].append(d)
        app.save(); render_gb()

    def render_gb():
        _clear(gb_list)
        for d in f["global_blacklist"]:
            def make_del(dd=d):
                def _delete():
                    if dd in f["global_blacklist"]:
                        f["global_blacklist"].remove(dd)
                    app.save(); render_gb()
                return _delete
            gb_list.append(_chip_row(d, make_del()))
        if not f["global_blacklist"]:
            empty = Gtk.Label(label="No sites blocked globally.", xalign=0)
            empty.add_css_class("dim-label")
            gb_list.append(empty)

    gb_section.add(_domain_input("e.g. tiktok.com", add_global, "Block"))
    gb_section.add(gb_list)
    content.append(gb_section)
    render_gb()

    # ---------- Keyword Blacklist ----------
    kw_section = Section(
        "Keyword Blacklist",
        "If an active window title contains one of these substrings during a focus session, it gets closed. Enforced by session_manager.",
    )
    kw_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

    def add_kw(text: str):
        for k in [p.strip() for p in text.split(",") if p.strip()]:
            if k not in f["keyword_blacklist"]:
                f["keyword_blacklist"].append(k)
        app.save(); render_kw()

    def render_kw():
        _clear(kw_list)
        for k in f["keyword_blacklist"]:
            def make_del(kk=k):
                def _delete():
                    if kk in f["keyword_blacklist"]:
                        f["keyword_blacklist"].remove(kk)
                    app.save(); render_kw()
                return _delete
            kw_list.append(_chip_row(k, make_del()))
        if not f["keyword_blacklist"]:
            empty = Gtk.Label(label="No keywords blocked.", xalign=0)
            empty.add_css_class("dim-label")
            kw_list.append(empty)

    kw_section.add(_domain_input("e.g. chess, reddit, instagram", add_kw, "Add"))
    kw_section.add(kw_list)
    content.append(kw_section)
    render_kw()

    # ---------- Visual Guard ----------
    vg = f["visual_guard"]
    vg_section = Section(
        "Visual Guard (experimental)",
        "Periodic screen sampling to flag high-skin-tone content. Requires python-pillow.",
    )
    sens_lbl_holder = {"row": None}

    def on_vg_toggle(b: bool):
        vg["enabled"] = b
        app.save()
        # Note: actual daemon control is wired up via session_manager / a separate guard.

    vg_section.add(switch_row(
        "Enable visual scanning", None,
        bool(vg.get("enabled", False)),
        on_vg_toggle,
    ))

    def on_sens(v: float):
        vg["sensitivity"] = int(v)
        app.save()

    vg_section.add(scale_row(
        "Sensitivity", "Lower = stricter; higher = looser.",
        float(vg.get("sensitivity", 50)), 10, 90, 5,
        on_sens, format_fn=lambda v: f"{int(v)}%",
    ))
    content.append(vg_section)

    # ---------- Media Blackout ----------
    mb = f["media_blackout"]
    mb_section = Section(
        "Media Blackout",
        "Forces text-only mode in Chrome/Chromium/Firefox/Brave. Requires a browser restart to take effect.",
    )

    def on_mb_toggle(b: bool):
        mb["enabled"] = b
        app.save()
        filter_svc.set_media_blackout(b, mb.get("allowlist", []))

    mb_section.add(switch_row(
        "Block all images and videos", None,
        bool(mb.get("enabled", False)),
        on_mb_toggle,
    ))

    mb_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

    def add_allow(text: str):
        mb.setdefault("allowlist", [])
        for d in model.clean_and_extract_domains(text):
            if d not in mb["allowlist"]:
                mb["allowlist"].append(d)
        app.save(); render_mb()
        if mb.get("enabled"):
            filter_svc.set_media_blackout(True, mb["allowlist"])

    def render_mb():
        _clear(mb_list)
        for d in mb.get("allowlist", []):
            def make_del(dd=d):
                def _delete():
                    if dd in mb["allowlist"]:
                        mb["allowlist"].remove(dd)
                    app.save(); render_mb()
                    if mb.get("enabled"):
                        filter_svc.set_media_blackout(True, mb["allowlist"])
                return _delete
            mb_list.append(_chip_row(d, make_del()))
        if not mb.get("allowlist"):
            empty = Gtk.Label(label="No exceptions — all media blocked.", xalign=0)
            empty.add_css_class("dim-label")
            mb_list.append(empty)

    mb_section.add(Gtk.Label(label="Allowed sites (media will still load here):", xalign=0))
    mb_section.add(_domain_input("e.g. drive.google.com", add_allow, "Allow"))
    mb_section.add(mb_list)
    content.append(mb_section)
    render_mb()

    # ---------- Goal-Specific ----------
    gs_section = Section(
        "Goal-Specific Filters",
        "Sites blocked only while a specific goal's session is active.",
    )
    goal_picker_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    gs_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

    selected = {"goal": None}

    def render_gs_picker():
        _clear(goal_picker_box)
        goals = model.goals(app.settings)
        if not goals:
            note = Gtk.Label(label="Define goals first.", xalign=0)
            note.add_css_class("dim-label")
            goal_picker_box.append(note)
            selected["goal"] = None
            render_gs_list()
            return
        if selected["goal"] not in goals:
            selected["goal"] = goals[0]
        for g in goals:
            btn = Gtk.Button(label=g)
            btn.add_css_class("chip")
            if g == selected["goal"]:
                btn.add_css_class("active")

            def on_click(_b, gg=g):
                selected["goal"] = gg
                render_gs_picker()
                render_gs_list()

            btn.connect("clicked", on_click)
            goal_picker_box.append(btn)

    def render_gs_list():
        _clear(gs_list)
        goal = selected["goal"]
        if goal is None:
            return
        gf = f["goal_filters"].setdefault(goal, [])

        def add(text: str):
            for d in model.clean_and_extract_domains(text):
                if d not in gf:
                    gf.append(d)
            app.save(); render_gs_list()

        gs_list.append(_domain_input(f"Block during '{goal}'", add, "Block"))
        if not gf:
            empty = Gtk.Label(label="No sites blocked for this goal.", xalign=0)
            empty.add_css_class("dim-label")
            gs_list.append(empty)
            return
        for d in gf:
            def make_del(dd=d):
                def _delete():
                    if dd in gf:
                        gf.remove(dd)
                    app.save(); render_gs_list()
                return _delete
            gs_list.append(_chip_row(d, make_del()))

    gs_section.add(goal_picker_box)
    gs_section.add(gs_list)
    content.append(gs_section)
    render_gs_picker()
    render_gs_list()

    return scrolled
