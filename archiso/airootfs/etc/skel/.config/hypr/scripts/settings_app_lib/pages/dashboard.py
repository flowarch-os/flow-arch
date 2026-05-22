"""Dashboard: stat cards + activity chart + recent activity list."""

from datetime import datetime

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .. import logs as logs_mod
from ..widgets.card import StatCard
from ..widgets.chart import BarChart
from ..widgets.section import scrollable_page, Section


def build(app):
    scrolled, content = scrollable_page(
        "Dashboard",
        "Your focus at a glance.",
    )

    state = {}

    # ---- stat cards ----
    grid = Gtk.Grid(column_spacing=14, row_spacing=14, column_homogeneous=True)
    content.append(grid)

    card_today = StatCard("Focus Today", "0.0 h", icon="")
    card_sessions = StatCard("Sessions Today", "0", icon="")
    card_rating = StatCard("Avg Rating", "0.0", icon="")
    card_streak = StatCard("Streak", "0 d", icon="")

    grid.attach(card_today, 0, 0, 1, 1)
    grid.attach(card_sessions, 1, 0, 1, 1)
    grid.attach(card_rating, 2, 0, 1, 1)
    grid.attach(card_streak, 3, 0, 1, 1)

    # ---- chart section ----
    chart_section = Section("Last 7 Days", "Hours of recorded focus time.")
    chart = BarChart({}, app.palette(), height=180)
    chart_section.add(chart)
    content.append(chart_section)

    # ---- recent activity ----
    recent_section = Section("Recent Activity", "Latest events from your session log.")
    recent_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    recent_section.add(recent_list)
    content.append(recent_section)

    state["cards"] = (card_today, card_sessions, card_rating, card_streak)
    state["chart"] = chart
    state["recent_list"] = recent_list

    def refresh():
        all_logs = logs_mod.load_logs()
        stats = logs_mod.compute_stats(all_logs)
        card_today.set_value(f"{stats['today_hours']:.1f} h")
        card_sessions.set_value(str(stats["session_count"]))
        card_rating.set_value(f"{stats['avg_rating']:.1f}", sub=f"/10 · {stats['total_sessions']} total")
        card_streak.set_value(f"{stats['streak']} d", sub="consecutive days")
        chart.update(stats["history"], app.palette())

        # Rebuild recent list
        child = recent_list.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            recent_list.remove(child)
            child = nxt

        if not stats["recent"]:
            empty = Gtk.Label(label="No activity yet. Start a session to see it here.", xalign=0)
            empty.add_css_class("dim-label")
            recent_list.append(empty)
            return

        for item in stats["recent"]:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.add_css_class("action-row")

            t = item["dt"]
            time_lbl = Gtk.Label(label=t.strftime("%a %H:%M"), xalign=0)
            time_lbl.add_css_class("dim-label")
            time_lbl.add_css_class("mono")
            time_lbl.set_size_request(90, -1)
            row.append(time_lbl)

            type_badge = Gtk.Label(label=item["type"].replace("_", " "), xalign=0)
            type_badge.add_css_class("dim-label")
            type_badge.set_size_request(80, -1)
            row.append(type_badge)

            goal_lbl = Gtk.Label(label=item["goal"], xalign=0)
            goal_lbl.add_css_class("heading")
            goal_lbl.set_hexpand(True)
            goal_lbl.set_ellipsize(3)
            row.append(goal_lbl)

            if item["intention"]:
                int_lbl = Gtk.Label(label=item["intention"], xalign=1)
                int_lbl.add_css_class("dim-label")
                int_lbl.set_ellipsize(3)
                int_lbl.set_max_width_chars(40)
                row.append(int_lbl)

            if item.get("rating") is not None:
                r = float(item["rating"])
                pill = Gtk.Label(label=f"{r:.0f}")
                pill.add_css_class("rating-pill")
                pill.add_css_class("high" if r >= 7 else "mid" if r >= 4 else "low")
                row.append(pill)

            recent_list.append(row)

    refresh()
    scrolled.on_show = refresh
    scrolled.on_theme_changed = lambda: chart.update(state["chart"]._data, app.palette())
    return scrolled
