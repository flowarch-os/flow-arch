"""Journal: feedback log grouped by date with search + goal filter chips."""

from itertools import groupby

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .. import logs as logs_mod, model
from ..widgets.section import scrollable_page, Section
from ..widgets.row import switch_row


def _rating_class(r: float) -> str:
    if r >= 7: return "high"
    if r >= 4: return "mid"
    return "low"


def build(app):
    scrolled, content = scrollable_page(
        "Journal",
        "Every feedback entry from your sessions, grouped by day.",
    )

    state = {"query": "", "goal_filter": None}

    # ---- prompt toggle ----
    settings_section = Section("Behaviour")

    def on_prompt(b: bool):
        app.settings.setdefault("focus", {})["shutdown_feedback"] = b
        app.save()

    settings_section.add(switch_row(
        "Prompt for feedback on shutdown",
        "Show the session-feedback dialog when you log out.",
        model.shutdown_feedback(app.settings),
        on_prompt,
    ))
    content.append(settings_section)

    # ---- search + chips ----
    controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    content.append(controls)

    search = Gtk.SearchEntry()
    search.set_placeholder_text("Search intentions, comments…")
    controls.append(search)

    chips_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    chips_scroll = Gtk.ScrolledWindow()
    chips_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
    chips_scroll.set_child(chips_row)
    controls.append(chips_scroll)

    # ---- entries area ----
    entries_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
    content.append(entries_box)

    def render():
        # Clear chips
        c = chips_row.get_first_child()
        while c:
            n = c.get_next_sibling()
            chips_row.remove(c)
            c = n
        goals = ["All", *model.goals(app.settings)]

        for g in goals:
            btn = Gtk.Button(label=g)
            btn.add_css_class("chip")
            if state["goal_filter"] == g or (g == "All" and state["goal_filter"] is None):
                btn.add_css_class("active")

            def on_click(_b, gg=g):
                state["goal_filter"] = None if gg == "All" else gg
                render()

            btn.connect("clicked", on_click)
            chips_row.append(btn)

        # Clear entries
        c = entries_box.get_first_child()
        while c:
            n = c.get_next_sibling()
            entries_box.remove(c)
            c = n

        feedback = logs_mod.feedback_only(logs_mod.load_logs())
        if state["goal_filter"]:
            feedback = [f for f in feedback if f.get("goal") == state["goal_filter"]]
        q = state["query"].lower()
        if q:
            feedback = [
                f for f in feedback
                if q in (f.get("intention", "") + " " + f.get("comment", "")
                         + " " + f.get("goal", "")).lower()
            ]

        if not feedback:
            empty = Gtk.Label(label="No matching entries.", xalign=0)
            empty.add_css_class("dim-label")
            entries_box.append(empty)
            return

        def by_date(item): return item["dt"].date()

        for date, group in groupby(feedback, key=by_date):
            day_section = Section(date.strftime("%A · %B %d"),
                                  subtitle=date.strftime("%Y-%m-%d"))
            day_entries = list(group)
            for entry in day_entries:
                row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                row.add_css_class("action-row")

                head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                t = entry["dt"].strftime("%I:%M %p")
                tlbl = Gtk.Label(label=t, xalign=0)
                tlbl.add_css_class("dim-label"); tlbl.add_css_class("mono")
                head.append(tlbl)

                glbl = Gtk.Label(label=entry.get("goal", "—"), xalign=0)
                glbl.add_css_class("heading"); glbl.set_hexpand(True)
                head.append(glbl)

                r = entry.get("rating")
                if isinstance(r, (int, float)):
                    pill = Gtk.Label(label=f"{int(r)}/10")
                    pill.add_css_class("rating-pill")
                    pill.add_css_class(_rating_class(float(r)))
                    head.append(pill)
                row.append(head)

                if entry.get("intention"):
                    body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                    arrow = Gtk.Label(label="↳")
                    arrow.add_css_class("dim-label")
                    body.append(arrow)
                    txt = Gtk.Label(label=entry["intention"], xalign=0, wrap=True)
                    body.append(txt)
                    row.append(body)
                if entry.get("comment"):
                    com = Gtk.Label(label=entry["comment"], xalign=0, wrap=True)
                    com.add_css_class("dim-label")
                    com.set_margin_start(14)
                    row.append(com)
                day_section.add(row)
            entries_box.append(day_section)

    def on_search(_e):
        state["query"] = search.get_text()
        render()
    search.connect("search-changed", on_search)

    render()
    scrolled.on_show = render
    return scrolled
