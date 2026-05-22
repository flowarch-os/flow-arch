"""Calendar + tasks. Week & month views, drag-create / drag-move / resize, recurrence."""

import time
from datetime import datetime, timedelta, date
from uuid import uuid4

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GObject, GLib

from .. import model, theme as theme_mod


SLOTS_PER_HOUR = 4
MINS_PER_SLOT = 15
TOTAL_SLOTS = 24 * SLOTS_PER_HOUR  # 96
HEADER_ROW = 0
FIRST_SLOT_ROW = 1
LAST_SLOT_ROW = TOTAL_SLOTS  # exclusive
RRULES = ("none", "daily", "weekdays", "weekly")
RRULE_LABELS = ("Does not repeat", "Daily", "Every weekday", "Weekly")


# ---------- time helpers ----------

def _start_of_week(d: date) -> datetime:
    """Monday 00:00 of the week containing d."""
    return datetime.combine(d - timedelta(days=d.weekday()), datetime.min.time())


def _row_for_dt(dt: datetime) -> int:
    """1-based slot row for a datetime's hour:minute."""
    return FIRST_SLOT_ROW + (dt.hour * 60 + dt.minute) // MINS_PER_SLOT


def _row_to_hm(row: int) -> tuple[int, int]:
    mins = (row - FIRST_SLOT_ROW) * MINS_PER_SLOT
    return divmod(mins, 60)


def _expand_recurring(event: dict, week_start: datetime, week_end: datetime) -> list[dict]:
    """Generate instances of an event in [week_start, week_end). Skip exdates."""
    try:
        start_dt = datetime.fromisoformat(event["start"])
        end_dt = datetime.fromisoformat(event["end"])
    except (KeyError, ValueError):
        return []

    rrule = (event.get("rrule") or "none").lower()
    exdates = set(event.get("exdates") or [])
    duration = end_dt - start_dt
    instances: list[dict] = []

    def emit(dt: datetime):
        d_iso = dt.date().isoformat()
        if d_iso in exdates:
            return
        if dt < week_start or dt >= week_end:
            return
        inst = dict(event)
        inst["start"] = dt.isoformat()
        inst["end"] = (dt + duration).isoformat()
        inst["_template_id"] = event.get("id")
        inst["_is_template_origin"] = (dt.date() == start_dt.date())
        instances.append(inst)

    if rrule == "none":
        emit(start_dt)
    elif rrule == "daily":
        cur = max(start_dt, week_start)
        # snap to event's HH:MM
        cur = cur.replace(hour=start_dt.hour, minute=start_dt.minute, second=0, microsecond=0)
        if cur < start_dt:
            cur = start_dt
        while cur < week_end:
            emit(cur)
            cur += timedelta(days=1)
    elif rrule == "weekdays":
        cur = max(start_dt, week_start).replace(
            hour=start_dt.hour, minute=start_dt.minute, second=0, microsecond=0)
        if cur < start_dt: cur = start_dt
        while cur < week_end:
            if cur.weekday() < 5:
                emit(cur)
            cur += timedelta(days=1)
    elif rrule == "weekly":
        # same weekday each week
        wd = start_dt.weekday()
        cur = week_start + timedelta(days=wd)
        cur = cur.replace(hour=start_dt.hour, minute=start_dt.minute, second=0, microsecond=0)
        if cur < start_dt:
            cur += timedelta(days=7)
        while cur < week_end:
            emit(cur)
            cur += timedelta(days=7)

    return instances


def _expand_for_month(event: dict, month_start: date, month_end: date) -> list[dict]:
    """Expand a single event across a month-view date range."""
    week_start_dt = datetime.combine(month_start, datetime.min.time())
    week_end_dt = datetime.combine(month_end + timedelta(days=1), datetime.min.time())
    return _expand_recurring(event, week_start_dt, week_end_dt)


# ---------- main builder ----------

def build(app):
    paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
    paned.set_wide_handle(True)
    paned.set_resize_start_child(True)
    paned.add_css_class("page")
    paned.set_position(820)

    state = {
        "view": "week",                              # 'week' | 'month'
        "week_start": _start_of_week(date.today()),
        "month_anchor": date.today().replace(day=1),
        "editing": False,
        "selection": None,
        "drag_state": None,
    }

    # ---- Right pane: tasks ----
    tasks_box = _build_tasks_pane(app)

    # ---- Left pane: calendar with header ----
    left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    left.set_margin_top(28); left.set_margin_bottom(20)
    left.set_margin_start(28); left.set_margin_end(14)

    # Header: title + nav + view toggle + new event
    head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    title = Gtk.Label(label="Calendar", xalign=0)
    title.add_css_class("page-title")
    title.set_hexpand(True)
    head.append(title)

    # view toggle
    toggle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    toggle_box.add_css_class("linked")
    btn_week = Gtk.Button(label="Week"); btn_week.add_css_class("chip"); btn_week.add_css_class("active")
    btn_month = Gtk.Button(label="Month"); btn_month.add_css_class("chip")
    toggle_box.append(btn_week); toggle_box.append(btn_month)
    head.append(toggle_box)

    # nav
    btn_prev = Gtk.Button(label="‹")
    btn_today = Gtk.Button(label="Today")
    btn_next = Gtk.Button(label="›")
    for b in (btn_prev, btn_today, btn_next):
        b.add_css_class("flat")
    head.append(btn_prev); head.append(btn_today); head.append(btn_next)

    btn_new = Gtk.Button(label="+ New Event")
    btn_new.add_css_class("suggested-action")
    head.append(btn_new)

    range_lbl = Gtk.Label(xalign=0)
    range_lbl.add_css_class("page-subtitle")

    left.append(head)
    left.append(range_lbl)

    # bedtime row
    bedtime_section = _build_bedtime_section(app, on_change=lambda: refresh())
    left.append(bedtime_section)

    # Stack for week/month
    view_stack = Gtk.Stack()
    view_stack.set_vexpand(True)
    view_stack.set_hexpand(True)
    view_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
    view_stack.set_transition_duration(150)
    left.append(view_stack)

    # Week view: scrolled grid
    week_scroll = Gtk.ScrolledWindow()
    week_scroll.set_vexpand(True)
    week_grid = Gtk.Grid()
    week_grid.set_column_homogeneous(False)
    week_grid.add_css_class("week-grid")
    week_scroll.set_child(week_grid)
    view_stack.add_named(week_scroll, "week")

    # Month view
    month_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    view_stack.add_named(month_box, "month")

    paned.set_start_child(left)
    paned.set_end_child(tasks_box)

    # ---------- rendering ----------
    def render_week():
        # Clear grid
        _clear_grid(week_grid)
        ws = state["week_start"]
        we = ws + timedelta(days=7)
        range_lbl.set_label(
            f"{ws.strftime('%b %d')} – {(we - timedelta(days=1)).strftime('%b %d, %Y')}"
        )

        # Column widths (col 0 is time labels)
        # Time column header
        empty = Gtk.Label()
        empty.set_size_request(48, -1)
        week_grid.attach(empty, 0, HEADER_ROW, 1, 1)

        # Day headers (cols 1..7)
        today = date.today()
        for i in range(7):
            d = (ws + timedelta(days=i)).date()
            lbl = Gtk.Label(xalign=0.5)
            day_str = d.strftime("%a")
            num_str = d.strftime("%d")
            lbl.set_use_markup(False)
            lbl.set_label(f"{day_str}  {num_str}")
            lbl.add_css_class("calendar-day-header")
            if d == today:
                lbl.add_css_class("today")
            week_grid.attach(lbl, i + 1, HEADER_ROW, 1, 1)

        # Time labels (col 0)
        for h in range(24):
            ampm = "AM" if h < 12 else "PM"
            h12 = h % 12 or 12
            lbl = Gtk.Label(label=f"{h12} {ampm}")
            lbl.add_css_class("calendar-time-label")
            lbl.set_valign(Gtk.Align.START)
            lbl.set_halign(Gtk.Align.END)
            week_grid.attach(lbl, 0, FIRST_SLOT_ROW + h * SLOTS_PER_HOUR, 1, 1)

        # Slot background frames (per hour, not per 15-min, for perf)
        for d_i in range(7):
            for h in range(24):
                slot = Gtk.Box()
                slot.add_css_class("calendar-slot")
                slot.add_css_class("hour-start")
                slot.set_size_request(110, 28)  # 4 slots * 7px? Tweak below
                week_grid.attach(slot, d_i + 1, FIRST_SLOT_ROW + h * SLOTS_PER_HOUR, 1, SLOTS_PER_HOUR)

        # Sleep overlay
        bedtime = model.bedtime(app.settings)
        try:
            sh = int(bedtime.get("start", "23:00").split(":")[0])
            eh = int(bedtime.get("end", "05:00").split(":")[0])
        except ValueError:
            sh, eh = 23, 5
        s_row = FIRST_SLOT_ROW + sh * SLOTS_PER_HOUR
        e_row = FIRST_SLOT_ROW + eh * SLOTS_PER_HOUR

        for d_i in range(7):
            if s_row > e_row:
                top = Gtk.Box(); top.add_css_class("sleep-slot")
                week_grid.attach(top, d_i + 1, s_row, 1, FIRST_SLOT_ROW + TOTAL_SLOTS - s_row)
                bot = Gtk.Box(); bot.add_css_class("sleep-slot")
                week_grid.attach(bot, d_i + 1, FIRST_SLOT_ROW, 1, e_row - FIRST_SLOT_ROW)
            elif e_row > s_row:
                m = Gtk.Box(); m.add_css_class("sleep-slot")
                week_grid.attach(m, d_i + 1, s_row, 1, e_row - s_row)

        # Now line (only on today's column)
        now = datetime.now()
        if ws <= now < we:
            day_i = (now.date() - ws.date()).days
            row = _row_for_dt(now)
            line = Gtk.Box()
            line.add_css_class("now-line")
            week_grid.attach(line, day_i + 1, row, 1, 1)

        # Events
        all_events = model.calendar_events(app.settings)
        instances: list[dict] = []
        for e in all_events:
            instances.extend(_expand_recurring(e, ws, we))

        for inst in instances:
            _attach_event_widget(app, state, week_grid, inst, ws, refresh)

        # Drag-to-create overlay handler on the grid
        _attach_drag_create(app, state, week_grid, ws, refresh)

        # Selection overlay
        sel_ind = Gtk.Box()
        sel_ind.add_css_class("selection")
        sel_ind.set_visible(False)
        state["selection_widget"] = sel_ind
        # attached temporarily during drag

    def render_month():
        # Clear
        c = month_box.get_first_child()
        while c:
            n = c.get_next_sibling()
            month_box.remove(c)
            c = n

        anchor = state["month_anchor"]
        range_lbl.set_label(anchor.strftime("%B %Y"))

        # Day-of-week header
        dow_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4, homogeneous=True)
        for name in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"):
            l = Gtk.Label(label=name)
            l.add_css_class("calendar-day-header")
            dow_row.append(l)
        month_box.append(dow_row)

        # Compute grid: Monday start, 6 rows max
        first = date(anchor.year, anchor.month, 1)
        start_grid = first - timedelta(days=first.weekday())
        # 42-day window (6 weeks)
        all_events = model.calendar_events(app.settings)
        instances = []
        grid_end = start_grid + timedelta(days=42)
        for e in all_events:
            instances.extend(_expand_for_month(e, start_grid, grid_end - timedelta(days=1)))

        # Group by date
        per_day: dict[date, list[dict]] = {}
        for inst in instances:
            d_inst = datetime.fromisoformat(inst["start"]).date()
            per_day.setdefault(d_inst, []).append(inst)

        today = date.today()

        for row in range(6):
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4, homogeneous=True)
            for col in range(7):
                d = start_grid + timedelta(days=row * 7 + col)
                cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                cell.add_css_class("month-day")
                if d.month != anchor.month:
                    cell.add_css_class("other")
                if d == today:
                    cell.add_css_class("today")

                day_head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                num = Gtk.Label(label=str(d.day), xalign=0)
                num.add_css_class("day-num")
                day_head.append(num)
                cell.append(day_head)

                for ev in sorted(per_day.get(d, []), key=lambda x: x["start"])[:4]:
                    ev_lbl = Gtk.Label(
                        label=f"{datetime.fromisoformat(ev['start']).strftime('%H:%M')}  {ev.get('goal','')[:14]}",
                        xalign=0,
                    )
                    ev_lbl.add_css_class("month-event")
                    ev_lbl.set_ellipsize(3)
                    cell.append(ev_lbl)
                more = len(per_day.get(d, [])) - 4
                if more > 0:
                    extra = Gtk.Label(label=f"+{more} more", xalign=0)
                    extra.add_css_class("dim-label")
                    cell.append(extra)

                # Click → jump to week view on that day
                gesture = Gtk.GestureClick()
                gesture.set_button(1)

                def on_click(_g, _n, _x, _y, dd=d):
                    state["week_start"] = _start_of_week(dd)
                    state["view"] = "week"
                    btn_week.add_css_class("active")
                    btn_month.remove_css_class("active")
                    view_stack.set_visible_child_name("week")
                    refresh()

                gesture.connect("released", on_click)
                cell.add_controller(gesture)

                row_box.append(cell)
            month_box.append(row_box)

    def refresh():
        if state["view"] == "week":
            render_week()
        else:
            render_month()

    # ---- nav wires ----
    def on_prev(_b):
        if state["view"] == "week":
            state["week_start"] -= timedelta(days=7)
        else:
            anchor = state["month_anchor"]
            if anchor.month == 1:
                state["month_anchor"] = date(anchor.year - 1, 12, 1)
            else:
                state["month_anchor"] = date(anchor.year, anchor.month - 1, 1)
        refresh()

    def on_next(_b):
        if state["view"] == "week":
            state["week_start"] += timedelta(days=7)
        else:
            anchor = state["month_anchor"]
            if anchor.month == 12:
                state["month_anchor"] = date(anchor.year + 1, 1, 1)
            else:
                state["month_anchor"] = date(anchor.year, anchor.month + 1, 1)
        refresh()

    def on_today(_b):
        state["week_start"] = _start_of_week(date.today())
        state["month_anchor"] = date.today().replace(day=1)
        refresh()

    def on_week_view(_b):
        state["view"] = "week"
        btn_week.add_css_class("active"); btn_month.remove_css_class("active")
        view_stack.set_visible_child_name("week")
        refresh()

    def on_month_view(_b):
        state["view"] = "month"
        btn_month.add_css_class("active"); btn_week.remove_css_class("active")
        view_stack.set_visible_child_name("month")
        refresh()

    def on_new(_b):
        # Open create dialog with current week's today (or its first day) at 09:00
        anchor = max(date.today(), state["week_start"].date())
        if anchor >= (state["week_start"].date() + timedelta(days=7)):
            anchor = state["week_start"].date()
        _show_event_dialog(app, paned, None,
                           default_date=anchor, default_start_min=9 * 60,
                           default_duration=60, on_saved=refresh)

    btn_prev.connect("clicked", on_prev)
    btn_next.connect("clicked", on_next)
    btn_today.connect("clicked", on_today)
    btn_week.connect("clicked", on_week_view)
    btn_month.connect("clicked", on_month_view)
    btn_new.connect("clicked", on_new)

    # initial paint
    refresh()
    paned.on_show = refresh
    paned.on_theme_changed = refresh
    return paned


# ---------- tasks pane ----------

def _build_tasks_pane(app) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.set_margin_top(28); box.set_margin_bottom(20)
    box.set_margin_start(14); box.set_margin_end(28)
    box.set_size_request(280, -1)

    title = Gtk.Label(label="Tasks", xalign=0)
    title.add_css_class("page-title")
    box.append(title)

    sub = Gtk.Label(label="Drag a task onto the calendar to schedule it.", xalign=0, wrap=True)
    sub.add_css_class("page-subtitle")
    box.append(sub)

    # Goal filter chips
    chips_holder = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    chips_scroll = Gtk.ScrolledWindow()
    chips_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
    chips_scroll.set_child(chips_holder)
    box.append(chips_scroll)

    # Add input
    add_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    entry = Gtk.Entry(placeholder_text="Add a task…")
    entry.set_hexpand(True)
    add_btn = Gtk.Button(label="Add"); add_btn.add_css_class("suggested-action")
    add_row.append(entry); add_row.append(add_btn)
    box.append(add_row)

    # List
    scroll = Gtk.ScrolledWindow()
    scroll.set_vexpand(True)
    list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    scroll.set_child(list_box)
    box.append(scroll)

    state = {"goal": None}

    def render():
        tasks = app.settings.setdefault("schedule", {}).setdefault("tasks", [])
        # chips
        c = chips_holder.get_first_child()
        while c:
            n = c.get_next_sibling()
            chips_holder.remove(c); c = n
        goals = ["All", *model.goals(app.settings)]
        if state["goal"] not in goals: state["goal"] = "All"
        for g in goals:
            b = Gtk.Button(label=g); b.add_css_class("chip")
            if g == state["goal"]: b.add_css_class("active")
            def on_click(_b, gg=g):
                state["goal"] = gg
                render()
            b.connect("clicked", on_click)
            chips_holder.append(b)

        # list
        c = list_box.get_first_child()
        while c:
            n = c.get_next_sibling()
            list_box.remove(c); c = n

        visible = tasks
        if state["goal"] not in (None, "All"):
            visible = [t for t in tasks if t.get("goal") == state["goal"]]

        if not visible:
            empty = Gtk.Label(label="No tasks.", xalign=0)
            empty.add_css_class("dim-label")
            list_box.append(empty)
            return

        for task in visible:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.add_css_class("action-row")
            chk = Gtk.CheckButton()
            chk.set_active(task.get("done", False))

            def on_toggle(c_, t=task):
                t["done"] = c_.get_active()
                app.save()
                render()

            chk.connect("toggled", on_toggle)
            row.append(chk)

            lbl = Gtk.Label(label=task.get("title", ""), xalign=0, wrap=True)
            lbl.set_hexpand(True)
            if task.get("done"):
                lbl.add_css_class("dim-label")
            row.append(lbl)

            if task.get("goal"):
                g_badge = Gtk.Label(label=task["goal"], xalign=1)
                g_badge.add_css_class("dim-label")
                g_badge.set_ellipsize(3)
                g_badge.set_max_width_chars(14)
                row.append(g_badge)

            del_btn = Gtk.Button(label="✕"); del_btn.add_css_class("flat")

            def on_del(_b, t=task):
                if t in tasks:
                    tasks.remove(t)
                app.save(); render()

            del_btn.connect("clicked", on_del)
            row.append(del_btn)

            # Drag source
            src = Gtk.DragSource()
            src.set_actions(Gdk.DragAction.COPY)

            def on_prepare(_s, _x, _y, t=task):
                payload = f"TASK::{t.get('title','')}::{t.get('goal') or ''}"
                return Gdk.ContentProvider.new_for_value(payload)

            src.connect("prepare", on_prepare)
            row.add_controller(src)

            list_box.append(row)

    def commit_add():
        text = entry.get_text().strip()
        if not text:
            return
        tasks = app.settings.setdefault("schedule", {}).setdefault("tasks", [])
        goal = state["goal"] if state["goal"] not in (None, "All") else None
        tasks.append({"title": text, "done": False, "goal": goal})
        app.save()
        entry.set_text("")
        render()

    entry.connect("activate", lambda _e: commit_add())
    add_btn.connect("clicked", lambda _b: commit_add())

    render()
    box.on_show = render
    return box


# ---------- bedtime control ----------

def _build_bedtime_section(app, on_change) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    box.add_css_class("action-row")
    lbl = Gtk.Label(label="Bedtime block", xalign=0)
    lbl.add_css_class("heading")
    lbl.set_hexpand(True)
    box.append(lbl)

    b = model.bedtime(app.settings)
    start_h = int(b.get("start", "23:00").split(":")[0])
    end_h = int(b.get("end", "05:00").split(":")[0])

    spin_s = Gtk.SpinButton.new_with_range(0, 23, 1)
    spin_s.set_value(start_h)
    spin_e = Gtk.SpinButton.new_with_range(0, 23, 1)
    spin_e.set_value(end_h)

    def commit(_w=None):
        bd = app.settings.setdefault("schedule", {}).setdefault("bedtime", {})
        bd["start"] = f"{int(spin_s.get_value()):02d}:00"
        bd["end"] = f"{int(spin_e.get_value()):02d}:00"
        app.save()
        on_change()

    spin_s.connect("value-changed", commit)
    spin_e.connect("value-changed", commit)

    box.append(Gtk.Label(label="from"))
    box.append(spin_s)
    box.append(Gtk.Label(label="to"))
    box.append(spin_e)
    return box


# ---------- grid utilities ----------

def _clear_grid(grid: Gtk.Grid) -> None:
    c = grid.get_first_child()
    while c:
        n = c.get_next_sibling()
        grid.remove(c)
        c = n


def _attach_event_widget(app, state, grid: Gtk.Grid, inst: dict, week_start: datetime,
                         refresh) -> None:
    try:
        s = datetime.fromisoformat(inst["start"])
        e = datetime.fromisoformat(inst["end"])
    except (KeyError, ValueError):
        return
    day_i = (s.date() - week_start.date()).days
    if not (0 <= day_i < 7):
        return
    row = _row_for_dt(s)
    end_row = _row_for_dt(e) if e.date() == s.date() else FIRST_SLOT_ROW + TOTAL_SLOTS
    span = max(1, end_row - row)

    palette = app.palette()
    accent = palette["accent"]
    # goal color override
    goal_themes_ = model.goal_themes(app.settings)
    theme_name = goal_themes_.get(inst.get("goal", ""), "")
    if theme_name:
        try:
            p = theme_mod.load_palette(theme_name)
            accent = theme_mod.derive(p)["accent"]
        except Exception:
            pass

    # Container
    frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    frame.add_css_class("event")
    if (inst.get("rrule") or "none") != "none":
        frame.add_css_class("recurring")

    # Per-event accent color override
    css = f""".event-{inst.get('id','x')} {{ background-color: rgba({_hex_to_rgba_parts(accent)},0.22); border-left-color: {accent}; }}"""
    prov = Gtk.CssProvider()
    prov.load_from_data(css.encode("utf-8"))
    frame.get_style_context().add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    frame.add_css_class(f"event-{inst.get('id','x')}")

    # Top resize grip
    top_grip = Gtk.Box(); top_grip.set_size_request(-1, 5)
    top_grip.set_cursor(Gdk.Cursor.new_from_name("n-resize", None))
    frame.append(top_grip)

    body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
    body.set_vexpand(True)
    body.set_margin_start(4); body.set_margin_end(4)
    title_lbl = Gtk.Label(label=inst.get("goal", "—"), xalign=0)
    title_lbl.add_css_class("event-title")
    title_lbl.set_ellipsize(3)
    body.append(title_lbl)
    if inst.get("intention"):
        int_lbl = Gtk.Label(label=inst["intention"], xalign=0)
        int_lbl.add_css_class("event-intention")
        int_lbl.set_ellipsize(3)
        body.append(int_lbl)
    frame.append(body)

    bot_grip = Gtk.Box(); bot_grip.set_size_request(-1, 5)
    bot_grip.set_cursor(Gdk.Cursor.new_from_name("s-resize", None))
    frame.append(bot_grip)

    frame.set_tooltip_text(
        f"{inst.get('intention','')}\n"
        f"{s.strftime('%I:%M %p')} – {e.strftime('%I:%M %p')}\n"
        + ("(recurring — right-click to edit)" if (inst.get("rrule") or "none") != "none"
           else "Drag to move • drag edges to resize • right-click to edit")
    )

    # Right-click → edit
    right_click = Gtk.GestureClick()
    right_click.set_button(3)
    right_click.connect("released",
                       lambda _g, _n, _x, _y, ii=inst: _show_event_dialog(
                           app, frame.get_root(), ii, on_saved=refresh))
    body.add_controller(right_click)

    # Move/resize only for non-recurring or template origin
    rrule = (inst.get("rrule") or "none").lower()
    template = _find_event_by_id(app, inst.get("_template_id") or inst.get("id"))
    can_drag = (rrule == "none")

    if can_drag and template is not None:
        _wire_move(state, grid, frame, body, template, week_start, refresh, app)
        _wire_resize(state, grid, frame, top_grip, template, week_start, refresh, app, top=True)
        _wire_resize(state, grid, frame, bot_grip, template, week_start, refresh, app, top=False)
    else:
        # tap → edit
        click = Gtk.GestureClick(); click.set_button(1)
        click.connect("released", lambda _g, _n, _x, _y, ii=inst: _show_event_dialog(
            app, frame.get_root(), ii, on_saved=refresh))
        body.add_controller(click)

    grid.attach(frame, day_i + 1, row, 1, span)


def _hex_to_rgba_parts(hex_color: str) -> str:
    hx = hex_color.lstrip("#")
    return f"{int(hx[0:2],16)},{int(hx[2:4],16)},{int(hx[4:6],16)}"


def _find_event_by_id(app, eid):
    for e in model.calendar_events(app.settings):
        if str(e.get("id")) == str(eid):
            return e
    return None


# ---------- drag-create on empty grid ----------

def _attach_drag_create(app, state, grid: Gtk.Grid, week_start: datetime, refresh) -> None:
    gesture = Gtk.GestureDrag()
    drag_state = {"valid": False, "start_x": 0, "start_y": 0, "min_row": 0, "max_row": 0, "day_i": 0, "indicator": None}

    def on_begin(_g, x, y):
        if state.get("editing"):
            return
        # Determine column/row from x,y in grid widget coords
        col, row = _xy_to_cell(grid, x, y)
        if col < 1:
            return
        if _has_collision(app, row, row + 1, col - 1, week_start):
            return
        drag_state["valid"] = True
        drag_state["start_x"] = x
        drag_state["start_y"] = y
        drag_state["day_i"] = col - 1
        drag_state["min_row"] = drag_state["max_row"] = row

        ind = Gtk.Box(); ind.add_css_class("selection")
        grid.attach(ind, col, row, 1, 1)
        drag_state["indicator"] = ind

    def on_update(_g, ox, oy):
        if not drag_state["valid"]:
            return
        col_w, row_h, _ = _grid_metrics(grid)
        end_y = drag_state["start_y"] + oy
        end_row = max(FIRST_SLOT_ROW, min(FIRST_SLOT_ROW + TOTAL_SLOTS - 1,
                       int(end_y // row_h)))
        start_row = drag_state["min_row"]
        # snap into valid range and don't cross collisions
        a = min(start_row, end_row)
        b = max(start_row, end_row) + 1  # inclusive
        # grow up/down from start in safe direction
        safe_a = start_row
        safe_b = start_row + 1
        cur = start_row
        while cur - 1 >= FIRST_SLOT_ROW and cur - 1 >= a:
            if _has_collision(app, cur - 1, cur, drag_state["day_i"], week_start):
                break
            safe_a = cur - 1
            cur -= 1
        cur = start_row
        while cur + 1 < FIRST_SLOT_ROW + TOTAL_SLOTS and cur + 1 <= b - 1:
            if _has_collision(app, cur, cur + 1, drag_state["day_i"], week_start):
                break
            safe_b = cur + 1
            cur += 1

        drag_state["min_row"] = safe_a
        drag_state["max_row"] = safe_b - 1
        if drag_state["indicator"]:
            grid.remove(drag_state["indicator"])
        ind = Gtk.Box(); ind.add_css_class("selection")
        span = max(1, safe_b - safe_a)
        grid.attach(ind, drag_state["day_i"] + 1, safe_a, 1, span)
        drag_state["indicator"] = ind

    def on_end(_g, _ox, _oy):
        if not drag_state["valid"]:
            return
        if drag_state["indicator"]:
            grid.remove(drag_state["indicator"])
            drag_state["indicator"] = None
        drag_state["valid"] = False

        s_row = drag_state["min_row"]
        e_row = drag_state["max_row"] + 1
        if e_row - s_row < 1:
            return
        day_i = drag_state["day_i"]
        day = (week_start + timedelta(days=day_i)).date()
        sh, sm = _row_to_hm(s_row)
        eh, em = _row_to_hm(e_row)
        start_min = sh * 60 + sm
        end_min = eh * 60 + em
        if end_min - start_min < 15:
            end_min = start_min + 15
        _show_event_dialog(app, grid.get_root(), None,
                          default_date=day, default_start_min=start_min,
                          default_duration=end_min - start_min, on_saved=refresh)

    gesture.connect("drag-begin", on_begin)
    gesture.connect("drag-update", on_update)
    gesture.connect("drag-end", on_end)
    grid.add_controller(gesture)

    # Drop target for tasks
    drop = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.COPY)

    def on_drop(_t, value, x, y):
        col, row = _xy_to_cell(grid, x, y)
        if col < 1:
            return False
        day_i = col - 1
        if isinstance(value, str) and value.startswith("TASK::"):
            try:
                _, title, goal = value.split("::", 2)
            except ValueError:
                return False
            day = (week_start + timedelta(days=day_i)).date()
            sh, sm = _row_to_hm(row)
            start = datetime.combine(day, datetime.min.time()).replace(hour=sh, minute=sm)
            evt = {
                "id": str(uuid4()),
                "start": start.isoformat(),
                "end": (start + timedelta(minutes=30)).isoformat(),
                "goal": goal or (model.goals(app.settings)[0] if model.goals(app.settings) else "Work"),
                "intention": title,
                "rrule": "none",
            }
            app.settings.setdefault("schedule", {}).setdefault("calendar_events", []).append(evt)
            app.save()
            refresh()
            return True
        return False

    drop.connect("drop", on_drop)
    grid.add_controller(drop)


def _grid_metrics(grid: Gtk.Grid) -> tuple[float, float, int]:
    """Approximate column width / row height / header height."""
    w = grid.get_width() or 1
    h = grid.get_height() or 1
    # 1 time column + 7 days
    col_w = w / 8
    # header row + 96 slots
    row_h = h / (TOTAL_SLOTS + 1)
    return col_w, row_h, 0


def _xy_to_cell(grid: Gtk.Grid, x: float, y: float) -> tuple[int, int]:
    col_w, row_h, _ = _grid_metrics(grid)
    col = int(x // col_w)
    row = int(y // row_h)
    if col < 0: col = 0
    if col > 7: col = 7
    if row < FIRST_SLOT_ROW: row = FIRST_SLOT_ROW
    if row >= FIRST_SLOT_ROW + TOTAL_SLOTS:
        row = FIRST_SLOT_ROW + TOTAL_SLOTS - 1
    return col, row


# ---------- collision check ----------

def _has_collision(app, start_row: int, end_row: int, day_i: int,
                  week_start: datetime, exclude_id=None) -> bool:
    # Sleep
    b = model.bedtime(app.settings)
    try:
        sh = int(b.get("start", "23:00").split(":")[0])
        eh = int(b.get("end", "05:00").split(":")[0])
    except ValueError:
        sh, eh = 23, 5
    s_row = FIRST_SLOT_ROW + sh * SLOTS_PER_HOUR
    e_row = FIRST_SLOT_ROW + eh * SLOTS_PER_HOUR

    if s_row > e_row:
        if max(start_row, s_row) < min(end_row, FIRST_SLOT_ROW + TOTAL_SLOTS): return True
        if max(start_row, FIRST_SLOT_ROW) < min(end_row, e_row): return True
    else:
        if max(start_row, s_row) < min(end_row, e_row): return True

    # Events (expanded into the week)
    we = week_start + timedelta(days=7)
    for e in model.calendar_events(app.settings):
        for inst in _expand_recurring(e, week_start, we):
            if exclude_id is not None and str(inst.get("_template_id") or inst.get("id")) == str(exclude_id):
                continue
            try:
                est = datetime.fromisoformat(inst["start"])
                eend = datetime.fromisoformat(inst["end"])
            except (KeyError, ValueError):
                continue
            inst_day = (est.date() - week_start.date()).days
            if inst_day != day_i:
                continue
            esr = _row_for_dt(est)
            eer = _row_for_dt(eend) if eend.date() == est.date() else FIRST_SLOT_ROW + TOTAL_SLOTS
            if max(start_row, esr) < min(end_row, eer):
                return True
    return False


# ---------- move/resize ----------

def _wire_move(state, grid, frame, body, template, week_start, refresh, app):
    drag = Gtk.GestureDrag()
    dr = {"orig_row": 0, "span": 0, "day_i": 0, "ghost": None, "current_row": 0, "current_day": 0}

    def begin(_g, _x, _y):
        state["editing"] = True
        frame.set_opacity(0.0)
        s = datetime.fromisoformat(template["start"])
        e = datetime.fromisoformat(template["end"])
        dr["orig_row"] = _row_for_dt(s)
        end_row = _row_for_dt(e) if e.date() == s.date() else FIRST_SLOT_ROW + TOTAL_SLOTS
        dr["span"] = max(1, end_row - dr["orig_row"])
        dr["day_i"] = (s.date() - week_start.date()).days
        dr["current_row"] = dr["orig_row"]
        dr["current_day"] = dr["day_i"]

        ghost = Gtk.Box(); ghost.add_css_class("event-ghost")
        grid.attach(ghost, dr["day_i"] + 1, dr["orig_row"], 1, dr["span"])
        dr["ghost"] = ghost

    def update(_g, ox, oy):
        if dr["ghost"] is None:
            return
        col_w, row_h, _ = _grid_metrics(grid)
        d_delta = int(round(ox / col_w))
        new_day = max(0, min(6, dr["day_i"] + d_delta))
        r_delta = int(round(oy / row_h))
        new_row = max(FIRST_SLOT_ROW, min(FIRST_SLOT_ROW + TOTAL_SLOTS - dr["span"],
                                          dr["orig_row"] + r_delta))
        if _has_collision(app, new_row, new_row + dr["span"], new_day, week_start,
                          exclude_id=template.get("id")):
            return
        if new_row == dr["current_row"] and new_day == dr["current_day"]:
            return
        grid.remove(dr["ghost"])
        gh = Gtk.Box(); gh.add_css_class("event-ghost")
        grid.attach(gh, new_day + 1, new_row, 1, dr["span"])
        dr["ghost"] = gh
        dr["current_row"] = new_row
        dr["current_day"] = new_day

    def end(_g, _ox, _oy):
        if dr["ghost"] is not None:
            grid.remove(dr["ghost"])
            dr["ghost"] = None
        frame.set_opacity(1.0)
        state["editing"] = False

        s = datetime.fromisoformat(template["start"])
        e = datetime.fromisoformat(template["end"])
        dur = e - s
        new_day_date = (week_start + timedelta(days=dr["current_day"])).date()
        sh, sm = _row_to_hm(dr["current_row"])
        new_start = datetime.combine(new_day_date, datetime.min.time()).replace(hour=sh, minute=sm)
        template["start"] = new_start.isoformat()
        template["end"] = (new_start + dur).isoformat()
        app.save()
        refresh()

    drag.connect("drag-begin", begin)
    drag.connect("drag-update", update)
    drag.connect("drag-end", end)
    body.add_controller(drag)


def _wire_resize(state, grid, frame, grip, template, week_start, refresh, app, top: bool):
    drag = Gtk.GestureDrag()
    rs = {"orig_row": 0, "orig_span": 0, "day_i": 0, "ghost": None,
          "current_row": 0, "current_span": 0}

    def begin(_g, _x, _y):
        state["editing"] = True
        s = datetime.fromisoformat(template["start"])
        e = datetime.fromisoformat(template["end"])
        rs["orig_row"] = _row_for_dt(s)
        end_row = _row_for_dt(e) if e.date() == s.date() else FIRST_SLOT_ROW + TOTAL_SLOTS
        rs["orig_span"] = max(1, end_row - rs["orig_row"])
        rs["day_i"] = (s.date() - week_start.date()).days
        rs["current_row"] = rs["orig_row"]
        rs["current_span"] = rs["orig_span"]
        frame.set_opacity(0.3)

    def update(_g, _ox, oy):
        _col, row_h, _ = _grid_metrics(grid)
        r_delta = int(round(oy / row_h))
        if top:
            new_row = max(FIRST_SLOT_ROW, rs["orig_row"] + r_delta)
            end_fixed = rs["orig_row"] + rs["orig_span"]
            new_span = end_fixed - new_row
            if new_span < 1:
                new_row = end_fixed - 1
                new_span = 1
        else:
            new_row = rs["orig_row"]
            new_span = max(1, rs["orig_span"] + r_delta)
            if new_row + new_span > FIRST_SLOT_ROW + TOTAL_SLOTS:
                new_span = FIRST_SLOT_ROW + TOTAL_SLOTS - new_row
        if _has_collision(app, new_row, new_row + new_span, rs["day_i"], week_start,
                          exclude_id=template.get("id")):
            return
        if new_row == rs["current_row"] and new_span == rs["current_span"]:
            return
        rs["current_row"] = new_row
        rs["current_span"] = new_span

    def end(_g, _ox, _oy):
        frame.set_opacity(1.0)
        state["editing"] = False
        s = datetime.fromisoformat(template["start"])
        day = s.date()
        sh, sm = _row_to_hm(rs["current_row"])
        eh, em = _row_to_hm(rs["current_row"] + rs["current_span"])
        new_start = datetime.combine(day, datetime.min.time()).replace(hour=sh, minute=sm)
        if eh >= 24:
            new_end = datetime.combine(day, datetime.min.time()) + timedelta(hours=24)
        else:
            new_end = datetime.combine(day, datetime.min.time()).replace(hour=eh, minute=em)
        template["start"] = new_start.isoformat()
        template["end"] = new_end.isoformat()
        app.save()
        refresh()

    drag.connect("drag-begin", begin)
    drag.connect("drag-update", update)
    drag.connect("drag-end", end)
    grip.add_controller(drag)


# ---------- event dialog ----------

def _show_event_dialog(app, root, instance, default_date=None,
                       default_start_min=540, default_duration=60,
                       on_saved=lambda: None) -> None:
    is_new = instance is None
    template = instance if is_new else _find_event_by_id(app, instance.get("_template_id") or instance.get("id"))

    dialog = Gtk.Window(title="Event")
    dialog.set_transient_for(root)
    dialog.set_modal(True)
    dialog.set_default_size(460, 480)

    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
    outer.set_margin_top(20); outer.set_margin_bottom(20)
    outer.set_margin_start(20); outer.set_margin_end(20)
    outer.add_css_class("page")
    dialog.set_child(outer)

    title = Gtk.Label(label="New Event" if is_new else "Edit Event", xalign=0)
    title.add_css_class("section-title")
    outer.append(title)

    goals = model.goals(app.settings) or ["Work"]
    selected_goal = (instance or {}).get("goal") or goals[0]
    selected_goal_idx = goals.index(selected_goal) if selected_goal in goals else 0
    dd_goal = Gtk.DropDown.new_from_strings(goals)
    dd_goal.set_selected(selected_goal_idx)
    outer.append(_field("Goal", dd_goal))

    entry_intent = Gtk.Entry(placeholder_text="Intention…")
    if instance: entry_intent.set_text(instance.get("intention", ""))
    outer.append(_field("Intention", entry_intent))

    # Date / time
    if is_new:
        d = default_date or date.today()
        sh, sm = divmod(default_start_min, 60)
        eh, em = divmod(default_start_min + default_duration, 60)
    else:
        s = datetime.fromisoformat(instance["start"])
        e = datetime.fromisoformat(instance["end"])
        d = s.date()
        sh, sm = s.hour, s.minute
        eh, em = e.hour, e.minute

    date_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    date_entry = Gtk.Entry(text=d.isoformat())
    date_entry.set_size_request(120, -1)
    date_row.append(date_entry)
    outer.append(_field("Date (YYYY-MM-DD)", date_row))

    time_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    spin_sh = Gtk.SpinButton.new_with_range(0, 23, 1); spin_sh.set_value(sh)
    spin_sm = Gtk.SpinButton.new_with_range(0, 59, 5); spin_sm.set_value(sm)
    spin_eh = Gtk.SpinButton.new_with_range(0, 24, 1); spin_eh.set_value(eh)
    spin_em = Gtk.SpinButton.new_with_range(0, 59, 5); spin_em.set_value(em)
    time_row.append(spin_sh); time_row.append(Gtk.Label(label=":")); time_row.append(spin_sm)
    time_row.append(Gtk.Label(label="—"))
    time_row.append(spin_eh); time_row.append(Gtk.Label(label=":")); time_row.append(spin_em)
    outer.append(_field("Time", time_row))

    # Recurrence
    dd_rec = Gtk.DropDown.new_from_strings(list(RRULE_LABELS))
    cur_rule = (instance or {}).get("rrule", "none").lower()
    dd_rec.set_selected(RRULES.index(cur_rule) if cur_rule in RRULES else 0)
    outer.append(_field("Repeats", dd_rec))

    # Edit scope (for existing recurring instances only)
    scope_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    radio_series = Gtk.CheckButton(label="Edit series")
    radio_one = Gtk.CheckButton(label="This occurrence only")
    radio_one.set_group(radio_series)
    radio_series.set_active(True)
    scope_box.append(radio_series); scope_box.append(radio_one)
    has_scope = (not is_new) and cur_rule != "none"
    if has_scope:
        outer.append(_field("Apply changes to", scope_box))

    # Buttons
    button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    button_row.set_halign(Gtk.Align.END)
    btn_cancel = Gtk.Button(label="Cancel")
    btn_cancel.add_css_class("flat")
    btn_cancel.connect("clicked", lambda _b: dialog.close())
    button_row.append(btn_cancel)

    if not is_new:
        btn_del = Gtk.Button(label="Delete")
        btn_del.add_css_class("destructive-action")

        def on_delete(_b):
            events = app.settings.setdefault("schedule", {}).setdefault("calendar_events", [])
            if has_scope and radio_one.get_active():
                tmpl = template
                if tmpl is not None:
                    tmpl.setdefault("exdates", []).append(d.isoformat())
            else:
                tmpl = template
                if tmpl is not None and tmpl in events:
                    events.remove(tmpl)
            app.save(); on_saved(); dialog.close()

        btn_del.connect("clicked", on_delete)
        button_row.append(btn_del)

    btn_save = Gtk.Button(label="Save")
    btn_save.add_css_class("suggested-action")

    def on_save(_b):
        try:
            new_date = datetime.fromisoformat(date_entry.get_text().strip()).date()
        except (ValueError, AttributeError):
            return
        new_sh = int(spin_sh.get_value()); new_sm = int(spin_sm.get_value())
        new_eh = int(spin_eh.get_value()); new_em = int(spin_em.get_value())
        # snap minutes to MINS_PER_SLOT
        new_sm -= new_sm % MINS_PER_SLOT
        new_em -= new_em % MINS_PER_SLOT
        start_dt = datetime.combine(new_date, datetime.min.time()).replace(hour=new_sh, minute=new_sm)
        if new_eh >= 24:
            end_dt = datetime.combine(new_date, datetime.min.time()) + timedelta(hours=24)
        else:
            end_dt = datetime.combine(new_date, datetime.min.time()).replace(hour=new_eh, minute=new_em)
        if end_dt <= start_dt:
            end_dt = start_dt + timedelta(minutes=MINS_PER_SLOT)

        goal_idx = dd_goal.get_selected()
        new_goal = goals[goal_idx] if 0 <= goal_idx < len(goals) else (goals[0] if goals else "Work")
        new_intent = entry_intent.get_text().strip()
        new_rrule = RRULES[dd_rec.get_selected()]

        events = app.settings.setdefault("schedule", {}).setdefault("calendar_events", [])

        if is_new:
            events.append({
                "id": str(uuid4()),
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "goal": new_goal,
                "intention": new_intent,
                "rrule": new_rrule,
            })
        elif has_scope and radio_one.get_active():
            # Skip the original instance from the template and create a one-off.
            if template is not None:
                template.setdefault("exdates", []).append(d.isoformat())
            events.append({
                "id": str(uuid4()),
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "goal": new_goal,
                "intention": new_intent,
                "rrule": "none",
            })
        else:
            tmpl = template or instance
            tmpl["start"] = start_dt.isoformat()
            tmpl["end"] = end_dt.isoformat()
            tmpl["goal"] = new_goal
            tmpl["intention"] = new_intent
            tmpl["rrule"] = new_rrule
            if tmpl is not None and tmpl not in events and is_new is False:
                events.append(tmpl)

        app.save()
        on_saved()
        dialog.close()

    btn_save.connect("clicked", on_save)
    button_row.append(btn_save)
    outer.append(button_row)

    dialog.present()


def _field(label: str, widget: Gtk.Widget) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    l = Gtk.Label(label=label, xalign=0)
    l.add_css_class("dim-label")
    box.append(l); box.append(widget)
    return box
