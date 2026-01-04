#!/usr/bin/env python3
import sys
import os
import json
import time
import gi
from datetime import datetime, timedelta

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, Gdk, GObject

SETTINGS_FILE = os.path.expanduser("~/.config/hypr/settings.json")
KEYBINDINGS_FILE = os.path.expanduser("~/.config/hypr/keybindings.conf")
THEMES_DIR = os.path.expanduser("~/.config/hypr/themes")
LOG_FILE = os.path.expanduser("~/session_logs.jsonl")

class SettingsApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.malek.hyprsettings",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.settings_data = self.load_settings()
        self.is_editing_event = False

    def do_activate(self):
        self.apply_theme()
        
        window = Gtk.ApplicationWindow(application=self, title="OS Settings")
        window.set_default_size(950, 700)

        # Main Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        window.set_child(main_box)

        # Sidebar (Stack Switcher)
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sidebar.set_size_request(200, -1)
        sidebar.set_margin_top(20)
        sidebar.set_margin_bottom(20)
        sidebar.set_margin_start(10)
        sidebar.set_margin_end(10)
        
        stack = Gtk.Stack()
        
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(stack)
        stack_switcher.set_orientation(Gtk.Orientation.VERTICAL)
        
        sidebar.append(stack_switcher)
        main_box.append(sidebar)
        
        # Separator
        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Data Loading
        self.logs = self.load_logs()

        # Pages
        stack.add_titled(self.create_dashboard_page(), "dashboard", "Dashboard")
        stack.add_titled(self.create_journal_page(), "journal", "Journal")
        stack.add_titled(self.create_calendar_page(), "calendar", "Calendar")
        stack.add_titled(self.create_goals_page(), "goals", "Goals & Themes")
        stack.add_titled(self.create_filters_page(), "filters", "Web Filters")
        stack.add_titled(self.create_pomodoro_page(), "pomodoro", "Pomodoro")
        stack.add_titled(self.create_shortcuts_page(), "shortcuts", "Shortcuts")
        
        main_box.append(stack)

        # Monitor for theme changes
        try:
            config_file = Gio.File.new_for_path(os.path.expanduser("~/.config/gtk-4.0/settings.ini"))
            self.monitor = config_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
            self.monitor.connect("changed", self.on_config_changed)
        except Exception as e:
            print(f"Failed to monitor settings: {e}")

        window.present()

    def on_config_changed(self, monitor, file, other_file, event_type):
        if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT or event_type == Gio.FileMonitorEvent.CHANGED:
            self.apply_theme()

    def apply_theme(self):
        try:
            theme_name = "Adwaita"
            icon_theme = "Adwaita"
            config_path = os.path.expanduser("~/.config/gtk-4.0/settings.ini")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    for line in f:
                        if "gtk-theme-name" in line:
                            theme_name = line.split("=")[1].strip()
                        if "gtk-icon-theme-name" in line:
                            icon_theme = line.split("=")[1].strip()
            
            settings = Gtk.Settings.get_default()
            settings.props.gtk_icon_theme_name = icon_theme
            settings.props.gtk_application_prefer_dark_theme = True
            
            css_path = os.path.expanduser(f"~/.themes/{theme_name}/gtk-4.0/gtk.css")
            if os.path.exists(css_path):
                provider = Gtk.CssProvider()
                provider.load_from_path(css_path)
                Gtk.StyleContext.add_provider_for_display(
                    Gdk.Display.get_default(),
                    provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_USER
                )
            
            fix_provider = Gtk.CssProvider()
            fix_css = """
            .title-1 { font-size: 24pt; font-weight: 800; margin-bottom: 20px; }
            .title-2 { font-size: 16pt; font-weight: 600; margin-top: 10px; }
            .heading { font-weight: 700; opacity: 0.8; }
            .dim-label { opacity: 0.5; font-size: 0.9em; }
            
            .boxed-list {
                background-color: alpha(@theme_fg_color, 0.05);
                border-radius: 12px;
                border: 1px solid alpha(@theme_fg_color, 0.1);
            }
            
            frame {
                border-radius: 12px;
                border: 1px solid alpha(@theme_fg_color, 0.1);
            }
            
            button.destructive-action { color: #ff5555; }
            .success { color: #a6e3a1; }
            .error { color: #f38ba8; }
            
            .calendar-slot {
                border: 1px solid alpha(@theme_fg_color, 0.05);
                background-color: transparent;
                border-radius: 0px;
            }
            
            .selection {
                background-color: alpha(@theme_selected_bg_color, 0.3);
                border: 1px solid @theme_selected_bg_color;
                border-radius: 4px;
            }
            
            .sleep-slot {
                background-color: alpha(@theme_fg_color, 0.08);
                border: none;
            }
            """
            fix_provider.load_from_data(fix_css.encode())
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                fix_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
                
        except Exception as e:
            print(f"Failed to apply theme: {e}")

    def load_settings(self):
        defaults = {
            "goals": ["Work", "Study"],
            "goal_themes": {},
            "filters": {},
            "pomodoro": {"work_duration": 25, "short_break": 5, "long_break": 20, "intention_popup": True},
            "shutdown_feedback": True,
            "calendar_events": [],
            "tasks": [],
            "bedtime_start": "23:00",
            "bedtime_end": "05:00"
        }
        
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    for k, v in defaults.items():
                        if k not in data:
                            data[k] = v
                    return data
            except:
                pass
        return defaults

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings_data, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def load_logs(self):
        logs = []
        if not os.path.exists(LOG_FILE):
            return logs
        try:
            with open(LOG_FILE, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        timestamp = data.get("timestamp") or data.get("date")
                        if timestamp:
                            data["dt"] = datetime.fromisoformat(timestamp)
                            logs.append(data)
                    except:
                        continue
        except Exception as e:
            print(f"Error loading logs: {e}")
        logs.sort(key=lambda x: x["dt"], reverse=True)
        return logs

    def get_themes(self):
        themes = []
        if os.path.exists(THEMES_DIR):
            for item in os.listdir(THEMES_DIR):
                if os.path.isdir(os.path.join(THEMES_DIR, item)):
                    themes.append(item)
        return sorted(themes)

    # --- CALENDAR & TASKS ---

    def create_calendar_page(self):
        self.current_week_start = self.get_this_week_start()
        
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(600)
        paned.set_margin_start(10)
        paned.set_margin_end(10)
        paned.set_margin_top(10)
        paned.set_margin_bottom(10)

        # Left: Calendar
        cal_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_prev = Gtk.Button(icon_name="go-previous-symbolic")
        btn_prev.connect("clicked", self.on_week_nav, -1)
        btn_next = Gtk.Button(icon_name="go-next-symbolic")
        btn_next.connect("clicked", self.on_week_nav, 1)
        btn_today = Gtk.Button(label="Today")
        btn_today.connect("clicked", self.on_week_nav, 0)
        
        self.lbl_week_range = Gtk.Label()
        self.lbl_week_range.add_css_class("title-2")
        
        header_box.append(btn_prev)
        header_box.append(btn_today)
        header_box.append(btn_next)
        header_box.append(self.lbl_week_range)
        cal_box.append(header_box)

        # Sleep Schedule Expander
        expander = Gtk.Expander(label="Sleep Schedule Settings")
        sleep_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sleep_box.set_margin_top(10)
        sleep_box.set_margin_bottom(10)
        sleep_box.set_margin_start(10)
        sleep_box.set_margin_end(10)
        
        sleep_lbl = Gtk.Label(label="System lockout hours (Strict):", xalign=0)
        sleep_lbl.add_css_class("dim-label")
        sleep_box.append(sleep_lbl)
        
        time_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        start_h = int(self.settings_data.get("bedtime_start", "23:00").split(":")[0])
        end_h = int(self.settings_data.get("bedtime_end", "05:00").split(":")[0])
        
        spin_start = Gtk.SpinButton.new_with_range(0, 23, 1)
        spin_start.set_value(start_h)
        spin_end = Gtk.SpinButton.new_with_range(0, 23, 1)
        spin_end.set_value(end_h)
        
        def on_time_change(w):
            s = int(spin_start.get_value())
            e = int(spin_end.get_value())
            self.settings_data["bedtime_start"] = f"{s:02d}:00"
            self.settings_data["bedtime_end"] = f"{e:02d}:00"
            self.save_settings()
            
        spin_start.connect("value-changed", on_time_change)
        spin_end.connect("value-changed", on_time_change)
        
        time_row.append(Gtk.Label(label="Bedtime:"))
        time_row.append(spin_start)
        time_row.append(Gtk.Label(label="Wake Up:"))
        time_row.append(spin_end)
        
        sleep_box.append(time_row)
        expander.set_child(sleep_box)
        cal_box.append(expander)

        # Scrollable Grid
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.cal_grid = Gtk.Grid()
        self.cal_grid.set_column_homogeneous(True)
        self.cal_grid.set_row_homogeneous(True) # Key for slots
        scrolled.set_child(self.cal_grid)
        cal_box.append(scrolled)

        # Right: Tasks
        task_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        task_box.set_size_request(250, -1)
        
        lbl_tasks = Gtk.Label(label="Tasks")
        lbl_tasks.add_css_class("title-2")
        task_box.append(lbl_tasks)
        
        # Goal Selector for Tasks
        goals = self.settings_data.get("goals", [])
        goals_list = ["All Goals"] + goals
        self.task_goal_combo = Gtk.DropDown.new_from_strings(goals_list)
        self.task_goal_combo.set_selected(0)
        self.task_goal_combo.connect("notify::selected-item", self.refresh_task_list_wrapper)
        task_box.append(self.task_goal_combo)
        
        # Add Task
        add_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.entry_task = Gtk.Entry(placeholder_text="Add a task...")
        self.entry_task.set_hexpand(True)
        self.entry_task.connect("activate", self.on_add_task)
        btn_add_task = Gtk.Button(icon_name="list-add-symbolic")
        btn_add_task.connect("clicked", self.on_add_task)
        add_row.append(self.entry_task)
        add_row.append(btn_add_task)
        task_box.append(add_row)
        
        # Task List
        task_scroll = Gtk.ScrolledWindow()
        task_scroll.set_vexpand(True)
        self.task_listbox = Gtk.ListBox()
        self.task_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.task_listbox.add_css_class("boxed-list")
        task_scroll.set_child(self.task_listbox)
        task_box.append(task_scroll)

        paned.set_start_child(cal_box)
        paned.set_end_child(task_box)
        
        self.refresh_calendar_view()
        self.refresh_task_list()
        
        return paned
        
    def refresh_task_list_wrapper(self, *args):
        self.refresh_task_list()

    def get_this_week_start(self):
        today = datetime.now()
        start = today - timedelta(days=today.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)

    def on_week_nav(self, btn, direction):
        if direction == 0:
            self.current_week_start = self.get_this_week_start()
        else:
            self.current_week_start += timedelta(weeks=direction)
        self.refresh_calendar_view()

    def get_sleep_rows(self):
        s_str = self.settings_data.get("bedtime_start", "23:00")
        e_str = self.settings_data.get("bedtime_end", "05:00")
        sh = int(s_str.split(":")[0])
        eh = int(e_str.split(":")[0])
        
        # Convert to Rows (15 min slots)
        # Row 1 is 00:00.
        # sh*4 + 1
        return (sh * 4 + 1), (eh * 4 + 1)

    def check_collision(self, start_row, end_row, day_idx, exclude_event_id=None):
        # 1. Sleep Collision
        s_row, e_row = self.get_sleep_rows()
        # Sleep is usually overnight. e.g. 23:00 (93) to 05:00 (21).
        # range 93..96+1 AND 1..21.
        
        # Check normalization
        if s_row > e_row: # Crosses midnight
            # Collision if range touches [s_row, 97) OR [1, e_row)
            if max(start_row, s_row) < min(end_row, 97): return True
            if max(start_row, 1) < min(end_row, e_row): return True
        else:
            if max(start_row, s_row) < min(end_row, e_row): return True
            
        # 2. Event Collision
        for evt in self.settings_data.get("calendar_events", []):
            if str(evt.get("id")) == str(exclude_event_id): continue
            
            try:
                # Need to parse event to rows
                # This is expensive inside a loop, but list is short.
                est = datetime.fromisoformat(evt["start"])
                eend = datetime.fromisoformat(evt["end"])
                
                # Check Day
                evt_day = (est.date() - self.current_week_start.date()).days
                if evt_day != day_idx: continue
                
                esm = est.hour * 60 + est.minute
                eem = eend.hour * 60 + eend.minute
                if eend.date() > est.date(): eem = 24*60
                
                esr = 1 + (esm // 15)
                eer = 1 + (eem // 15)
                
                # Overlap logic
                if max(start_row, esr) < min(end_row, eer):
                    return True
            except: continue
            
        return False

    def refresh_calendar_view(self):
        # Clear Grid
        child = self.cal_grid.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.cal_grid.remove(child)
            child = next_child
            
        # Clear Controllers (Fix multiple popups)
        # Note: In GTK4 Python, removing specific controllers can be tricky if not stored.
        # But we can iterate. Or simpler: Store them in self.
        if hasattr(self, 'cal_drop_target'): self.cal_grid.remove_controller(self.cal_drop_target)
        if hasattr(self, 'cal_drag_create'): self.cal_grid.remove_controller(self.cal_drag_create)

        # 15-minute slots: 24 * 4 = 96 rows
        SLOTS_PER_HOUR = 4
        MINS_PER_SLOT = 15
        
        # Add a strut to force minimum height for the grid
        # 5px * 96 = 480px tall (Super Compact)
        strut = Gtk.Label(label="")
        strut.set_size_request(1, 480)
        self.cal_grid.attach(strut, 0, 1, 1, 96)
        
        # Headers
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        week_end = self.current_week_start + timedelta(days=6)
        self.lbl_week_range.set_label(f"{self.current_week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}")

        # Add Headers Row
        for i, day in enumerate(days):
            d_date = self.current_week_start + timedelta(days=i)
            lbl = Gtk.Label(label=f"{day} {d_date.day}")
            lbl.add_css_class("heading")
            if d_date.date() == datetime.now().date():
                lbl.add_css_class("success")
            self.cal_grid.attach(lbl, i + 1, 0, 1, 1) # Row 0 is headers
            
        ROW_OFFSET = 1 # Time starts at row 1

        # Time Labels & Grid Lines
        for h in range(24):
            # Label
            ampm = "AM" if h < 12 else "PM"
            h12 = h % 12
            if h12 == 0: h12 = 12
            lbl = Gtk.Label(label=f"{h12}{ampm}")
            lbl.add_css_class("dim-label")
            lbl.set_valign(Gtk.Align.START)
            lbl.set_margin_end(5)
            # Attach at start of hour
            row_idx = ROW_OFFSET + (h * SLOTS_PER_HOUR)
            self.cal_grid.attach(lbl, 0, row_idx, 1, 1)

        # Background Grid (Visual Hour Blocks)
        for d in range(7):
            for h in range(24):
                frame = Gtk.Frame()
                frame.add_css_class("calendar-slot")
                self.cal_grid.attach(frame, d + 1, ROW_OFFSET + (h * 4), 1, 4)
                
        # Sleep Blocks
        s_row, e_row = self.get_sleep_rows()
        for d in range(7):
            if s_row > e_row:
                # Evening part
                f1 = Gtk.Frame(); f1.add_css_class("sleep-slot")
                self.cal_grid.attach(f1, d + 1, s_row, 1, 97 - s_row)
                # Morning part
                f2 = Gtk.Frame(); f2.add_css_class("sleep-slot")
                self.cal_grid.attach(f2, d + 1, 1, 1, e_row - 1)
            else:
                f = Gtk.Frame(); f.add_css_class("sleep-slot")
                self.cal_grid.attach(f, d + 1, s_row, 1, e_row - s_row)
        
        # Selection Indicator (Hidden by default)
        self.selection_indicator = Gtk.Frame()
        self.selection_indicator.add_css_class("selection")
        self.selection_indicator.set_visible(False)
        self.cal_grid.attach(self.selection_indicator, 1, ROW_OFFSET, 1, 1)

        # Drop Target on Grid (For Tasks Only)
        target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.COPY)
        target.connect("drop", self.on_cal_drop)
        self.cal_grid.add_controller(target)
        
        # Drag to Create Controller
        self.cal_drag_create = Gtk.GestureDrag()
        self.cal_drag_create.connect("drag-begin", self.on_create_drag_begin)
        self.cal_drag_create.connect("drag-update", self.on_create_drag_update)
        self.cal_drag_create.connect("drag-end", self.on_create_drag_end)
        self.cal_grid.add_controller(self.cal_drag_create)

        # Events
        for event in self.settings_data.get("calendar_events", []):
            try:
                start_dt = datetime.fromisoformat(event["start"])
                end_dt = datetime.fromisoformat(event["end"])
                
                week_end_dt = self.current_week_start + timedelta(days=7)
                if start_dt < self.current_week_start or start_dt >= week_end_dt:
                    continue
                    
                day_idx = (start_dt.date() - self.current_week_start.date()).days
                
                start_min = start_dt.hour * 60 + start_dt.minute
                end_min = end_dt.hour * 60 + end_dt.minute
                if end_dt.date() > start_dt.date(): end_min = 24 * 60
                
                start_row = ROW_OFFSET + (start_min // MINS_PER_SLOT)
                duration_mins = end_min - start_min
                span = max(1, duration_mins // MINS_PER_SLOT)
                
                # Event Widget
                frame = Gtk.Frame()
                frame.add_css_class("boxed-list")
                
                main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                frame.set_child(main_vbox)
                
                # Top Grip
                top_grip = Gtk.Box()
                top_grip.set_size_request(-1, 5)
                top_grip.set_cursor(Gdk.Cursor.new_from_name("n-resize", None))
                drag_top = Gtk.GestureDrag()
                drag_top.connect("drag-begin", self.on_resize_top_begin, event, frame)
                drag_top.connect("drag-update", self.on_resize_top_update, event, frame)
                drag_top.connect("drag-end", self.on_resize_top_end, event, frame)
                top_grip.add_controller(drag_top)
                main_vbox.append(top_grip)
                
                # Content (Move/Edit area)
                content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                content_box.set_vexpand(True)
                lbl_g = Gtk.Label(label=event.get("goal", "?"))
                lbl_g.add_css_class("heading")
                lbl_g.set_ellipsize(3)
                lbl_g.set_halign(Gtk.Align.START)
                content_box.append(lbl_g)
                main_vbox.append(content_box)
                
                # Tooltip
                time_range = f"{start_dt.strftime('%I:%M %p')} - {end_dt.strftime('%I:%M %p')}"
                frame.set_tooltip_text(f"{event.get('intention')}\n{time_range}\n(Drag to Move, Right Click to Edit)")
                
                # Gesture Drag (Live Move) - Attached to CONTENT only
                move_drag = Gtk.GestureDrag()
                move_drag.connect("drag-begin", self.on_event_move_begin, event, frame)
                move_drag.connect("drag-update", self.on_event_move_update, event, frame)
                move_drag.connect("drag-end", self.on_event_move_end, event, frame)
                content_box.add_controller(move_drag)
                
                click = Gtk.GestureClick()
                click.set_button(3) # Right Click
                click.connect("pressed", lambda g, n, x, y, e=event: self.show_edit_event_dialog(e))
                content_box.add_controller(click)
                
                # Bottom Grip
                bot_grip = Gtk.Box()
                bot_grip.set_size_request(-1, 5)
                bot_grip.set_cursor(Gdk.Cursor.new_from_name("s-resize", None))
                drag_bot = Gtk.GestureDrag()
                drag_bot.connect("drag-begin", self.on_resize_bot_begin, event, frame)
                drag_bot.connect("drag-update", self.on_resize_bot_update, event, frame)
                drag_bot.connect("drag-end", self.on_resize_bot_end, event, frame)
                bot_grip.add_controller(drag_bot)
                main_vbox.append(bot_grip)
                
                self.cal_grid.attach(frame, day_idx + 1, start_row, 1, span)
                
            except Exception as e:
                print(f"Error render event: {e}")

    # --- RESIZE HANDLERS ---

    def on_resize_top_begin(self, gesture, x, y, event, widget):
        self.is_editing_event = True
        widget.set_opacity(0.0)
        self.move_ghost = self.create_event_ghost(event)
        
        start_dt = datetime.fromisoformat(event["start"])
        end_dt = datetime.fromisoformat(event["end"])
        start_min = start_dt.hour * 60 + start_dt.minute
        row = 1 + (start_min // 15)
        dur = (end_dt - start_dt).total_seconds() / 60
        span = max(1, int(dur // 15))
        day_idx = (start_dt.date() - self.current_week_start.date()).days
        
        self.cal_grid.attach(self.move_ghost, day_idx + 1, row, 1, span)
        self.resize_orig_row = row
        self.resize_orig_span = span
        self.current_resize_target_row = row
        self.current_resize_target_span = span

    def on_resize_top_update(self, gesture, offset_x, offset_y, event, widget):
        if not hasattr(self, 'move_ghost'): return
        
        height = self.cal_grid.get_height()
        row_h = height / 97
        
        row_delta = int(offset_y / row_h)
        new_row = self.resize_orig_row + row_delta
        
        # Calculate new span (growing up increases span, moving down decreases)
        # End row is fixed: orig_row + orig_span
        end_row = self.resize_orig_row + self.resize_orig_span
        new_span = end_row - new_row
        
        new_row = max(1, min(end_row - 1, new_row)) # Min duration 15m (1 slot)
        new_span = max(1, new_span)
        
        day_idx = (datetime.fromisoformat(event["start"]).date() - self.current_week_start.date()).days
        
        if not self.check_collision(new_row, new_row + new_span, day_idx, exclude_event_id=event.get("id")):
            if new_row != self.current_resize_target_row:
                self.cal_grid.remove(self.move_ghost)
                self.cal_grid.attach(self.move_ghost, day_idx + 1, new_row, 1, new_span)
                self.current_resize_target_row = new_row
                self.current_resize_target_span = new_span

    def on_resize_top_end(self, gesture, offset_x, offset_y, event, widget):
        self.finish_resize(event, widget, True)
        self.is_editing_event = False

    def on_resize_bot_begin(self, gesture, x, y, event, widget):
        self.is_editing_event = True
        widget.set_opacity(0.0)
        self.move_ghost = self.create_event_ghost(event)
        
        start_dt = datetime.fromisoformat(event["start"])
        end_dt = datetime.fromisoformat(event["end"])
        start_min = start_dt.hour * 60 + start_dt.minute
        row = 1 + (start_min // 15)
        dur = (end_dt - start_dt).total_seconds() / 60
        span = max(1, int(dur // 15))
        day_idx = (start_dt.date() - self.current_week_start.date()).days
        
        self.cal_grid.attach(self.move_ghost, day_idx + 1, row, 1, span)
        self.resize_orig_row = row
        self.resize_orig_span = span
        self.current_resize_target_span = span

    def on_resize_bot_update(self, gesture, offset_x, offset_y, event, widget):
        if not hasattr(self, 'move_ghost'): return
        
        height = self.cal_grid.get_height()
        row_h = height / 97
        
        row_delta = int(offset_y / row_h)
        new_span = self.resize_orig_span + row_delta
        new_span = max(1, new_span)
        
        day_idx = (datetime.fromisoformat(event["start"]).date() - self.current_week_start.date()).days
        row = self.resize_orig_row
        
        if not self.check_collision(row, row + new_span, day_idx, exclude_event_id=event.get("id")):
            if new_span != self.current_resize_target_span:
                self.cal_grid.remove(self.move_ghost)
                self.cal_grid.attach(self.move_ghost, day_idx + 1, row, 1, new_span)
                self.current_resize_target_span = new_span

    def on_resize_bot_end(self, gesture, offset_x, offset_y, event, widget):
        self.finish_resize(event, widget, False)
        self.is_editing_event = False

    def finish_resize(self, event, widget, is_top):
        widget.set_opacity(1.0)
        if hasattr(self, 'move_ghost'):
            self.cal_grid.remove(self.move_ghost)
            del self.move_ghost
            
        day_idx = (datetime.fromisoformat(event["start"]).date() - self.current_week_start.date()).days
        new_dt = self.current_week_start + timedelta(days=day_idx)
        
        if is_top:
            row = getattr(self, 'current_resize_target_row', self.resize_orig_row)
            span = getattr(self, 'current_resize_target_span', self.resize_orig_span)
        else:
            row = self.resize_orig_row
            span = getattr(self, 'current_resize_target_span', self.resize_orig_span)
            
        start_mins = (row - 1) * 15
        end_mins = start_mins + (span * 15)
        
        sh, sm = divmod(start_mins, 60)
        eh, em = divmod(end_mins, 60)
        
        event["start"] = new_dt.replace(hour=sh, minute=sm, second=0).isoformat()
        event["end"] = new_dt.replace(hour=eh, minute=em, second=0).isoformat()
        
        self.save_settings()
        self.refresh_calendar_view()

    def create_event_ghost(self, event):
        frame = Gtk.Frame()
        frame.add_css_class("boxed-list")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        lbl_g = Gtk.Label(label=event.get("goal", "?"))
        lbl_g.add_css_class("heading")
        lbl_g.set_ellipsize(3)
        lbl_g.set_halign(Gtk.Align.START)
        box.append(lbl_g)
        frame.set_child(box)
        return frame

    def on_event_move_begin(self, gesture, x, y, event, widget):
        self.is_editing_event = True
        self.move_start_y = y
        self.move_start_x = x
        widget.set_opacity(0.0)
        
        # Create Ghost
        self.move_ghost = self.create_event_ghost(event)
        
        # Find current position (approx via event data)
        start_dt = datetime.fromisoformat(event["start"])
        end_dt = datetime.fromisoformat(event["end"])
        start_min = start_dt.hour * 60 + start_dt.minute
        row = 1 + (start_min // 15)
        dur = (end_dt - start_dt).total_seconds() / 60
        span = max(1, int(dur // 15))
        day_idx = (start_dt.date() - self.current_week_start.date()).days
        
        self.cal_grid.attach(self.move_ghost, day_idx + 1, row, 1, span)
        self.current_move_target = row

    def on_event_move_update(self, gesture, offset_x, offset_y, event, widget):
        if not hasattr(self, 'move_ghost'): return
        
        height = self.cal_grid.get_height()
        row_h = height / 97
        
        start_dt = datetime.fromisoformat(event["start"])
        start_min = start_dt.hour * 60 + start_dt.minute
        orig_row = 1 + (start_min // 15)
        
        row_delta = int(offset_y / row_h)
        target_row = orig_row + row_delta
        target_row = max(1, min(96, target_row))
        
        end_dt = datetime.fromisoformat(event["end"])
        dur = (end_dt - start_dt).total_seconds() / 60
        span = max(1, int(dur // 15))
        
        if target_row + span > 97: target_row = 97 - span
        
        day_idx = (start_dt.date() - self.current_week_start.date()).days
        
        if not self.check_collision(target_row, target_row + span, day_idx, exclude_event_id=event.get("id")):
            if target_row != self.current_move_target:
                self.cal_grid.remove(self.move_ghost)
                self.cal_grid.attach(self.move_ghost, day_idx + 1, target_row, 1, span)
                self.current_move_target = target_row

    def on_event_move_end(self, gesture, offset_x, offset_y, event, widget):
        self.is_editing_event = False
        widget.set_opacity(1.0)
        if hasattr(self, 'move_ghost'):
            self.cal_grid.remove(self.move_ghost)
            del self.move_ghost
            
        if hasattr(self, 'current_move_target'):
            new_row = self.current_move_target
            # ... (Save logic same as before)
            day_idx = (datetime.fromisoformat(event["start"]).date() - self.current_week_start.date()).days
            new_dt = self.current_week_start + timedelta(days=day_idx)
            mins = (new_row - 1) * 15
            h, m = divmod(mins, 60)
            new_start = new_dt.replace(hour=h, minute=m, second=0)
            
            old_start = datetime.fromisoformat(event["start"])
            old_end = datetime.fromisoformat(event["end"])
            dur = old_end - old_start
            
            event["start"] = new_start.isoformat()
            event["end"] = (new_start + dur).isoformat()
            self.save_settings()
            del self.current_move_target
            self.refresh_calendar_view()

    def on_event_click(self, n_press, event):
        if n_press == 2:
            self.show_edit_event_dialog(event)

    def on_task_drag_prepare(self, source, x, y, task):
        # Payload: "TASK:Title|Goal"
        title = task.get("title", "")
        goal = task.get("goal") or "Default"
        return Gdk.ContentProvider.new_for_value(f"TASK:{title}|{goal}")

    def on_cal_drop(self, target, value, x, y):
        # Calculate Time from Drop Y
        height = self.cal_grid.get_height()
        width = self.cal_grid.get_width()
        col_width = width / 8 # 0 + 7 cols
        
        row_h = height / 97 # 96 slots + 1 header
        row = int(y / row_h) - 1
        if row < 0: row = 0
        
        col = int(x / col_width)
        if col < 1: col = 1
        if col > 7: col = 7
        
        day_idx = col - 1
        mins = row * 15
        hour = mins // 60
        minute = mins % 60
        
        drop_date = self.current_week_start + timedelta(days=day_idx)
        new_start = drop_date.replace(hour=hour, minute=minute, second=0)
        
        if isinstance(value, str):
            if value.startswith("MOVE:"):
                evt_id = value.split(":", 1)[1]
                # Find Event
                for evt in self.settings_data["calendar_events"]:
                    if str(evt.get("id")) == str(evt_id):
                        try:
                            old_start = datetime.fromisoformat(evt["start"])
                            old_end = datetime.fromisoformat(evt["end"])
                            duration = old_end - old_start
                            
                            evt["start"] = new_start.isoformat()
                            evt["end"] = (new_start + duration).isoformat()
                            self.save_settings()
                            self.refresh_calendar_view()
                        except Exception as e:
                            print(f"Move Error: {e}")
                        break
            elif value.startswith("TASK:"):
                try:
                    _, content = value.split(":", 1)
                    title, goal = content.split("|", 1)
                    
                    event = {
                        "id": str(time.time()),
                        "start": new_start.isoformat(),
                        "end": (new_start + timedelta(minutes=30)).isoformat(),
                        "goal": goal,
                        "intention": title
                    }
                    self.settings_data["calendar_events"].append(event)
                    self.save_settings()
                    self.refresh_calendar_view()
                except Exception as e:
                    print(f"Task Drop Error: {e}")
                
        return True

    def on_create_drag_begin(self, gesture, x, y):
        self.drag_valid = False
        if self.is_editing_event: return # Block creation if interacting
        
        height = self.cal_grid.get_height()
        width = self.cal_grid.get_width()
        col_width = width / 8
        row_h = height / 97
        
        col = int(x / col_width)
        if col < 1: col = 1
        if col > 7: col = 7
        day_idx = col - 1
        
        row = int(y / row_h) - 1
        row = max(1, min(96, row))
        
        if self.check_collision(row, row + 1, day_idx):
            return
            
        self.drag_valid = True
        self.drag_start_x = x
        self.drag_start_y = y
        self.selection_indicator.set_visible(True)

    def on_create_drag_update(self, gesture, offset_x, offset_y):
        if not hasattr(self, 'drag_valid') or not self.drag_valid: return
        
        start_x = self.drag_start_x
        start_y = self.drag_start_y
        
        height = self.cal_grid.get_height()
        width = self.cal_grid.get_width()
        col_width = width / 8
        row_h = height / 97
        
        col = int(start_x / col_width)
        if col < 1: col = 1
        if col > 7: col = 7
        day_idx = col - 1
        
        r1 = int(start_y / row_h) - 1
        r2 = int((start_y + offset_y) / row_h) - 1
        
        min_row = max(1, min(r1, r2))
        max_row = max(1, max(r1, r2))
        
        # Grow check
        safe_max = min_row
        for r in range(min_row, max_row + 1):
            if self.check_collision(r, r + 1, day_idx):
                break
            safe_max = r
            
        max_row = safe_max
        if max_row < min_row: max_row = min_row
        
        # Min duration visual
        if max_row - min_row < 1:
            if not self.check_collision(min_row, min_row + 2, day_idx):
                max_row = min_row + 2
            
        # Move Indicator
        self.cal_grid.remove(self.selection_indicator)
        self.cal_grid.attach(self.selection_indicator, col, min_row + 1, 1, max_row - min_row)
        
        self.drag_final_min = min_row
        self.drag_final_max = max_row

    def on_create_drag_end(self, gesture, offset_x, offset_y):
        self.selection_indicator.set_visible(False)
        if not hasattr(self, 'drag_valid') or not self.drag_valid: return
        if not hasattr(self, 'drag_final_min'): return
        
        start_mins = self.drag_final_min * 15
        end_mins = self.drag_final_max * 15
        
        col = int(self.drag_start_x / (self.cal_grid.get_width() / 8))
        if col < 1: col = 1
        if col > 7: col = 7
        day_idx = col - 1
        
        date_obj = self.current_week_start + timedelta(days=day_idx)
        self.show_add_event_dialog_range(date_obj, start_mins, end_mins)
        
        if hasattr(self, 'drag_final_min'): del self.drag_final_min
        if hasattr(self, 'drag_final_max'): del self.drag_final_max

    def show_add_event_dialog_range(self, date_obj, start_mins, end_mins):
        dialog = Gtk.Window(title="New Time Block")
        dialog.set_transient_for(self.get_active_window())
        dialog.set_modal(True)
        dialog.set_default_size(400, 300)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        dialog.set_child(box)
        
        # Goal
        goals = self.settings_data.get("goals", [])
        if not goals:
            box.append(Gtk.Label(label="Please define Goals first."))
            return
            
        combo_goal = Gtk.DropDown.new_from_strings(goals)
        box.append(Gtk.Label(label="Goal", xalign=0))
        box.append(combo_goal)
        
        # Intention
        box.append(Gtk.Label(label="Intention", xalign=0))
        entry_int = Gtk.Entry(placeholder_text="Specific task...")
        box.append(entry_int)
        
        # Time
        s_h, s_m = divmod(start_mins, 60)
        e_h, e_m = divmod(end_mins, 60)
        
        def format_ampm(h, m):
            ap = "AM" if h < 12 else "PM"
            h12 = h % 12
            if h12 == 0: h12 = 12
            return f"{h12}:{m:02d} {ap}"
            
        time_str = f"{format_ampm(s_h, s_m)} - {format_ampm(e_h, e_m)}"
        box.append(Gtk.Label(label=f"{date_obj.strftime('%A')}: {time_str}", xalign=0))
        
        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_halign(Gtk.Align.END)
        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda b: dialog.close())
        btn_save = Gtk.Button(label="Save Block")
        btn_save.add_css_class("suggested-action")
        
        def on_save(btn):
            g_idx = combo_goal.get_selected()
            goal = goals[g_idx]
            intention = entry_int.get_text()
            
            start_dt = date_obj.replace(hour=s_h, minute=s_m, second=0)
            end_dt = date_obj.replace(hour=e_h, minute=e_m, second=0)
            
            event = {
                "id": str(time.time()),
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "goal": goal,
                "intention": intention
            }
            self.settings_data["calendar_events"].append(event)
            self.save_settings()
            self.refresh_calendar_view()
            dialog.close()
            
        btn_save.connect("clicked", on_save)
        btn_box.append(btn_cancel)
        btn_box.append(btn_save)
        box.append(btn_box)
        
        dialog.present()

    def show_edit_event_dialog(self, event):
        dialog = Gtk.Window(title="Edit Time Block")
        dialog.set_transient_for(self.get_active_window())
        dialog.set_modal(True)
        dialog.set_default_size(400, 300)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        dialog.set_child(box)
        
        # Goal
        goals = self.settings_data.get("goals", [])
        if not goals: goals = ["Default"]
        
        combo_goal = Gtk.DropDown.new_from_strings(goals)
        try:
            combo_goal.set_selected(goals.index(event.get("goal")))
        except:
            combo_goal.set_selected(0)
            
        box.append(Gtk.Label(label="Goal", xalign=0))
        box.append(combo_goal)
        
        # Intention
        box.append(Gtk.Label(label="Intention", xalign=0))
        entry_int = Gtk.Entry(text=event.get("intention", ""))
        box.append(entry_int)
        
        # Time Info (Read-only)
        start = datetime.fromisoformat(event['start'])
        end = datetime.fromisoformat(event['end'])
        time_range = f"{start.strftime('%I:%M %p')} - {end.strftime('%I:%M %p')}"
        box.append(Gtk.Label(label=f"Time: {time_range}", xalign=0, css_classes=["dim-label"]))
        
        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_halign(Gtk.Align.END)
        
        btn_del = Gtk.Button(label="Delete")
        btn_del.add_css_class("destructive-action")
        
        btn_save = Gtk.Button(label="Save")
        btn_save.add_css_class("suggested-action")
        
        def on_del(btn):
            if event in self.settings_data["calendar_events"]:
                self.settings_data["calendar_events"].remove(event)
                self.save_settings()
                self.refresh_calendar_view()
            dialog.close()
            
        def on_save(btn):
            g_idx = combo_goal.get_selected()
            event["goal"] = goals[g_idx]
            event["intention"] = entry_int.get_text()
            self.save_settings()
            self.refresh_calendar_view()
            dialog.close()
            
        btn_del.connect("clicked", on_del)
        btn_save.connect("clicked", on_save)
        
        btn_box.append(btn_del)
        btn_box.append(btn_save)
        box.append(btn_box)
        
        dialog.present()
    
    def refresh_task_list(self):
        child = self.task_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.task_listbox.remove(child)
            child = next_child
            
        selected_goal_idx = self.task_goal_combo.get_selected()
        goals = ["All Goals"] + self.settings_data.get("goals", [])
        selected_goal = goals[selected_goal_idx]
            
        for task in self.settings_data.get("tasks", []):
            if selected_goal != "All Goals" and task.get("goal") != selected_goal:
                continue
                
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.set_margin_top(5)
            row.set_margin_bottom(5)
            row.set_margin_start(5)
            
            # Allow Drag and Drop
            drag_source = Gtk.DragSource()
            drag_source.set_actions(Gdk.DragAction.COPY)
            drag_source.connect("prepare", self.on_task_drag_prepare, task)
            row.add_controller(drag_source)
            
            chk = Gtk.CheckButton()
            chk.set_active(task.get("done", False))
            chk.connect("toggled", self.on_toggle_task, task)
            
            lbl = Gtk.Label(label=task["title"])
            if task.get("done"):
                lbl.add_css_class("dim-label")
            lbl.set_hexpand(True)
            lbl.set_xalign(0)
            
            # Goal badge if All Goals
            if selected_goal == "All Goals" and task.get("goal"):
                lbl_g = Gtk.Label(label=task.get("goal"))
                lbl_g.add_css_class("dim-label")
                lbl_g.set_margin_end(5)
                row.append(lbl_g)
            
            btn_del = Gtk.Button(icon_name="user-trash-symbolic")
            btn_del.add_css_class("flat")
            btn_del.connect("clicked", self.on_delete_task, task)
            
            row.append(chk)
            row.append(lbl)
            row.append(btn_del)
            self.task_listbox.append(row)
    
    def on_add_task(self, widget):
        text = self.entry_task.get_text().strip()
        if text:
            selected_goal_idx = self.task_goal_combo.get_selected()
            goals = ["All Goals"] + self.settings_data.get("goals", [])
            goal = goals[selected_goal_idx]
            if goal == "All Goals": goal = None # Or default?
            
            self.settings_data["tasks"].append({"title": text, "done": False, "goal": goal})
            self.save_settings()
            self.entry_task.set_text("")
            self.refresh_task_list()
    
    def on_toggle_task(self, chk, task):
        task["done"] = chk.get_active()
        self.save_settings()
        self.refresh_task_list()
    
    def on_delete_task(self, btn, task):
        if task in self.settings_data["tasks"]:
            self.settings_data["tasks"].remove(task)
            self.save_settings()
            self.refresh_task_list()
    
    # --- PAGES ---

    def calculate_stats(self):
        stats = {
            "today_hours": 0, 
            "session_count": 0, 
            "recent_activity": [], 
            "avg_rating": 0.0,
            "history": { (datetime.now().date() - timedelta(days=i)).strftime("%Y-%m-%d"): 0 for i in range(7) }
        }
        
        # Sort logs ascending to track flow
        sorted_logs = sorted(self.logs, key=lambda x: x["dt"])
        
        active_session_start = None
        rating_sum = 0
        total_ratings = 0
        
        for i, data in enumerate(sorted_logs):
            d_date = data["dt"].date()
            date_str = d_date.strftime("%Y-%m-%d")
            
            if data.get("type") == "login":
                active_session_start = data["dt"]
                if date_str == datetime.now().strftime("%Y-%m-%d"):
                    stats["session_count"] += 1
                    
            elif data.get("type") == "feedback":
                if active_session_start:
                    # Calculate actual duration
                    delta = (data["dt"] - active_session_start).total_seconds() / 3600
                    if delta > 0 and delta < 24: # Sanity check
                        if date_str in stats["history"]:
                            stats["history"][date_str] += delta
                        
                        if date_str == datetime.now().strftime("%Y-%m-%d"):
                            stats["today_hours"] += delta
                    
                    active_session_start = None
                
                r = data.get("rating")
                if isinstance(r, (int, float)):
                    rating_sum += r
                    total_ratings += 1

        if total_ratings > 0:
            stats["avg_rating"] = rating_sum / total_ratings
            
        # Recent activity from raw reverse logs
        for item in self.logs[:10]:
             if item.get("type") in ["login", "feedback", "pomodoro_segment"]:
                stats["recent_activity"].append({
                    "time": item["dt"].strftime("%H:%M"),
                    "goal": item.get("goal", "Unknown"),
                    "intention": item.get("intention", "")
                })
                
        return stats

    def create_stat_card(self, title, value, icon_name):
        frame = Gtk.Frame()
        frame.add_css_class("boxed-list") # clean look
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, margin_top=15, margin_bottom=15, margin_start=15, margin_end=15)
        
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(24)
        icon.set_opacity(0.5)
        icon.set_halign(Gtk.Align.START)
        
        lbl_val = Gtk.Label(label=value, css_classes=["title-1"], xalign=0)
        lbl_title = Gtk.Label(label=title, css_classes=["dim-label"], xalign=0)
        
        box.append(icon)
        box.append(lbl_val)
        box.append(lbl_title)
        frame.set_child(box)
        return frame

    def draw_chart(self, area, ctx, w, h, data):
        # Data prep
        days = sorted(data.keys())
        values = [data[d] for d in days]
        max_val = max(values) if values and max(values) > 0 else 1
        
        bar_width = (w / len(values)) * 0.6
        spacing = (w / len(values)) * 0.4
        
        # Draw Bars
        for i, val in enumerate(values):
            x = i * (bar_width + spacing) + (spacing / 2)
            bar_h = (val / max_val) * (h - 30)
            y = h - bar_h - 20
            
            # Bar
            ctx.rectangle(x, y, bar_width, bar_h)
            ctx.set_source_rgb(0.2, 0.6, 1.0) # Blue
            ctx.fill()
            
            # Label (Day)
            ctx.set_source_rgb(0.6, 0.6, 0.6)
            ctx.set_font_size(10)
            day_lbl = days[i][5:] # MM-DD
            ext = ctx.text_extents(day_lbl)
            ctx.move_to(x + (bar_width - ext.width)/2, h - 5)
            ctx.show_text(day_lbl)
            
            # Value
            if val > 0:
                val_lbl = f"{val:.1f}"
                ext = ctx.text_extents(val_lbl)
                ctx.move_to(x + (bar_width - ext.width)/2, y - 5)
                ctx.show_text(val_lbl)

    def create_dashboard_page(self):
        scrolled = Gtk.ScrolledWindow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(30); box.set_margin_bottom(30); box.set_margin_start(30); box.set_margin_end(30)
        scrolled.set_child(box)

        stats = self.calculate_stats()

        # Header
        h_box = Gtk.Box(spacing=10)
        title = Gtk.Label(label="Overview", xalign=0); title.add_css_class("title-1")
        h_box.append(title)
        box.append(h_box)

        # Stats Grid
        grid = Gtk.Grid(column_spacing=20, row_spacing=20, halign=Gtk.Align.FILL, hexpand=True)
        # 3 columns, equal width
        grid.set_column_homogeneous(True)
        
        grid.attach(self.create_stat_card("Today's Actual Focus", f"{stats['today_hours']:.1f} hrs", "weather-clear-symbolic"), 0, 0, 1, 1)
        grid.attach(self.create_stat_card("Sessions Started", str(stats['session_count']), "media-playback-start-symbolic"), 1, 0, 1, 1)
        grid.attach(self.create_stat_card("Performance Rating", f"{stats['avg_rating']:.1f}/10", "starred-symbolic"), 2, 0, 1, 1)
        box.append(grid)

        # Chart Section
        chart_frame = Gtk.Frame()
        chart_frame.add_css_class("boxed-list")
        chart_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=20, margin_bottom=20, margin_start=20, margin_end=20)
        chart_box.append(Gtk.Label(label="Last 7 Days (Hours)", xalign=0, css_classes=["heading"]))
        
        drawing = Gtk.DrawingArea()
        drawing.set_content_width(600)
        drawing.set_content_height(200)
        drawing.set_draw_func(self.draw_chart, stats["history"])
        chart_box.append(drawing)
        
        chart_frame.set_child(chart_box)
        box.append(chart_frame)
        
        # Recent Activity
        box.append(Gtk.Label(label="Recent Activity", halign=Gtk.Align.START, margin_top=10, css_classes=["title-2"]))
        list_box = Gtk.ListBox(); list_box.add_css_class("boxed-list")
        for item in stats['recent_activity']:
            row = Gtk.Box(spacing=15, margin_top=12, margin_bottom=12, margin_start=15, margin_end=15)
            lbl_time = Gtk.Label(label=item['time'], css_classes=["dim-label"])
            lbl_goal = Gtk.Label(label=item['goal'], css_classes=["heading"], hexpand=True, xalign=0)
            lbl_int = Gtk.Label(label=item['intention'], css_classes=["dim-label"], ellipsize=3, xalign=1)
            row.append(lbl_time); row.append(lbl_goal); row.append(lbl_int)
            list_box.append(row)
        box.append(list_box)
        
        return scrolled

    def create_journal_page(self):
        scrolled = Gtk.ScrolledWindow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(30); box.set_margin_bottom(30); box.set_margin_start(30); box.set_margin_end(30)
        scrolled.set_child(box)

        header_box = Gtk.Box(spacing=10)
        title = Gtk.Label(label="Progress Diary"); title.add_css_class("title-1")
        header_box.append(title)
        box.append(header_box)
        
        # Shutdown Prompt Toggle
        toggle_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        toggle_row.set_halign(Gtk.Align.END) # Right align the whole block? Or keep split?
        # Let's keep it split: Label left, Switch right
        toggle_row.set_halign(Gtk.Align.FILL)
        
        lbl_sys = Gtk.Label(label="Prompt for Feedback on Shutdown", hexpand=True, xalign=1)
        lbl_sys.add_css_class("dim-label")
        switch_sys = Gtk.Switch()
        switch_sys.set_valign(Gtk.Align.CENTER)
        switch_sys.set_active(self.settings_data.get("shutdown_feedback", True))
        switch_sys.connect("state-set", self.on_system_bool_change, "shutdown_feedback")
        
        toggle_row.append(lbl_sys)
        toggle_row.append(switch_sys)
        box.append(toggle_row)

        # Group logs by date
        from itertools import groupby
        def get_date(item): return item["dt"].date()
        
        # Only feedback items matter for journal
        journal_logs = [l for l in self.logs if l.get("type") == "feedback"]
        
        if not journal_logs:
            box.append(Gtk.Label(label="No entries yet. Complete a session to see your history!"))
            return scrolled

        for date, group in groupby(journal_logs, key=get_date):
            day_frame = Gtk.Frame()
            day_frame.add_css_class("boxed-list")
            day_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            
            # Date Header
            date_lbl = Gtk.Label(label=date.strftime("%A, %B %d"), xalign=0)
            date_lbl.add_css_class("heading")
            date_lbl.set_margin_top(15); date_lbl.set_margin_start(15); date_lbl.set_margin_bottom(10)
            day_box.append(date_lbl)
            
            for i, entry in enumerate(group):
                if i > 0: day_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
                
                row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                row.set_margin_top(15); row.set_margin_bottom(15); row.set_margin_start(15); row.set_margin_end(15)
                
                # Top: Time + Goal + Rating
                top = Gtk.Box(spacing=15)
                time_lbl = Gtk.Label(label=entry["dt"].strftime("%I:%M %p"), css_classes=["dim-label"])
                goal_lbl = Gtk.Label(label=entry.get("goal", "Unknown"), css_classes=["heading"], hexpand=True, xalign=0)
                
                top.append(time_lbl)
                top.append(goal_lbl)
                
                r = entry.get("rating", 0)
                if isinstance(r, (int, float)):
                    lvl = Gtk.LevelBar()
                    lvl.set_min_value(0); lvl.set_max_value(10); lvl.set_value(r)
                    lvl.set_size_request(50, 5)
                    top.append(lvl)
                    top.append(Gtk.Label(label=f"{r}"))

                row.append(top)
                
                # Intention arrow
                int_box = Gtk.Box(spacing=5)
                int_box.append(Gtk.Label(label="↳", css_classes=["dim-label"]))
                int_box.append(Gtk.Label(label=entry.get("intention", ""), wrap=True, xalign=0))
                row.append(int_box)
                
                # Comment
                if entry.get("comment"):
                    comm = Gtk.Label(label=entry["comment"], wrap=True, xalign=0)
                    comm.add_css_class("dim-label")
                    comm.set_margin_start(20) # Indent
                    row.append(comm)
                
                day_box.append(row)
            
            day_frame.set_child(day_box)
            box.append(day_frame)
            
        return scrolled

    def create_goals_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(30)
        box.set_margin_bottom(30)
        box.set_margin_start(30)
        box.set_margin_end(30)

        add_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.entry_new_goal = Gtk.Entry(placeholder_text="New Goal Name")
        self.entry_new_goal.set_hexpand(True)
        btn_add = Gtk.Button(label="Add Goal")
        btn_add.connect("clicked", self.on_add_goal)
        add_box.append(self.entry_new_goal)
        add_box.append(btn_add)
        box.append(add_box)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self.goals_listbox = Gtk.ListBox()
        self.goals_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.goals_listbox.add_css_class("boxed-list")
        scroll.set_child(self.goals_listbox)
        box.append(scroll)
        self.refresh_goals_list()
        return box

    def refresh_goals_list(self):
        child = self.goals_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.goals_listbox.remove(child)
            child = next_child

        available_themes = self.get_themes()
        available_themes.insert(0, "Default")

        for goal in self.settings_data.get("goals", []):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.set_margin_top(10)
            row.set_margin_bottom(10)
            row.set_margin_start(10)
            row.set_margin_end(10)
            
            lbl = Gtk.Label(label=goal, xalign=0)
            lbl.set_hexpand(True)
            
            theme_combo = Gtk.DropDown.new_from_strings(available_themes)
            current_theme = self.settings_data.get("goal_themes", {}).get(goal, "Default")
            try:
                theme_combo.set_selected(available_themes.index(current_theme))
            except:
                theme_combo.set_selected(0)
            theme_combo.connect("notify::selected-item", self.on_theme_changed, goal, available_themes)
            
            btn_del = Gtk.Button(icon_name="user-trash-symbolic")
            btn_del.add_css_class("destructive-action")
            btn_del.connect("clicked", self.on_delete_goal, goal)
            row.append(lbl)
            row.append(Gtk.Label(label="Theme:"))
            row.append(theme_combo)
            row.append(btn_del)
            self.goals_listbox.append(row)

    def on_add_goal(self, btn):
        text = self.entry_new_goal.get_text().strip()
        if text and text not in self.settings_data["goals"]:
            self.settings_data["goals"].append(text)
            self.save_settings()
            self.refresh_goals_list()
            self.entry_new_goal.set_text("")

    def on_delete_goal(self, btn, goal):
        if goal in self.settings_data["goals"]:
            self.settings_data["goals"].remove(goal)
            if goal in self.settings_data.get("goal_themes", {}):
                del self.settings_data["goal_themes"][goal]
            self.save_settings()
            self.refresh_goals_list()

    def on_theme_changed(self, combo, param, goal, themes):
        idx = combo.get_selected()
        theme = themes[idx]
        if "goal_themes" not in self.settings_data:
            self.settings_data["goal_themes"] = {}
        if theme == "Default":
            if goal in self.settings_data["goal_themes"]:
                del self.settings_data["goal_themes"][goal]
        else:
            self.settings_data["goal_themes"][goal] = theme
        self.save_settings()
    
    def create_filters_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(30)
        box.set_margin_bottom(30)
        box.set_margin_start(30)
        box.set_margin_end(30)
        
        # --- Ad Blocking Section ---
        ad_frame = Gtk.Frame(label="Global Ad Blocking")
        ad_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        ad_box.set_margin_top(15)
        ad_box.set_margin_bottom(15)
        ad_box.set_margin_start(15)
        ad_box.set_margin_end(15)
        
        row_ad = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl_ad = Gtk.Label(label="Enable Ad Blocking (Blocks known ad domains system-wide)", xalign=0)
        lbl_ad.set_hexpand(True)
        switch_ad = Gtk.Switch()
        switch_ad.set_active(self.settings_data.get("ad_blocking", False))
        switch_ad.connect("state-set", self.on_adblock_change)
        
        row_ad.append(lbl_ad)
        row_ad.append(switch_ad)
        ad_box.append(row_ad)
        
        ad_frame.set_child(ad_box)
        box.append(ad_frame)

        # Header
        lbl_info = Gtk.Label(label="Manage blocklists for each goal. Sites added here will be blocked at the OS level during a session.")
        lbl_info.set_wrap(True)
        lbl_info.set_xalign(0)
        box.append(lbl_info)

        # Goal Selector
        row_sel = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row_sel.append(Gtk.Label(label="Select Goal:"))
        
        goals = self.settings_data.get("goals", [])
        if not goals:
            box.append(Gtk.Label(label="Please add Goals first."))
            return box
            
        self.filter_goal_combo = Gtk.DropDown.new_from_strings(goals)
        self.filter_goal_combo.set_selected(0)
        self.filter_goal_combo.connect("notify::selected-item", self.refresh_filter_list)
        row_sel.append(self.filter_goal_combo)
        box.append(row_sel)

        # Add Domain Input
        add_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.entry_new_domain = Gtk.Entry(placeholder_text="example.com")
        self.entry_new_domain.set_hexpand(True)
        btn_add = Gtk.Button(label="Block Site")
        btn_add.connect("clicked", self.on_add_domain)
        add_box.append(self.entry_new_domain)
        add_box.append(btn_add)
        box.append(add_box)

        # Filter List
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self.filter_listbox = Gtk.ListBox()
        self.filter_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.filter_listbox.add_css_class("boxed-list")
        scroll.set_child(self.filter_listbox)
        box.append(scroll)
        
        self.refresh_filter_list(None, None)
        return box

    def on_adblock_change(self, switch, state):
        self.settings_data["ad_blocking"] = state
        self.save_settings()
        # Apply immediately
        import subprocess
        cmd = "on" if state else "off"
        script = os.path.expanduser("~/.config/hypr/scripts/hosts_manager.py")
        subprocess.Popen(["sudo", script, "ads", cmd])

    def on_update_ads(self, btn):
        import subprocess
        script = os.path.expanduser("~/.config/hypr/scripts/hosts_manager.py")
        subprocess.Popen(["sudo", script, "ads", "update"])

    def refresh_filter_list(self, *args):
        # Clear
        child = self.filter_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.filter_listbox.remove(child)
            child = next_child
            
        goals = self.settings_data.get("goals", [])
        if not goals: return
        
        idx = self.filter_goal_combo.get_selected()
        goal = goals[idx]
        
        filters = self.settings_data.get("filters", {}).get(goal, [])
        
        for domain in filters:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.set_margin_top(10)
            row.set_margin_bottom(10)
            row.set_margin_start(10)
            row.set_margin_end(10)
            
            lbl = Gtk.Label(label=domain, xalign=0)
            lbl.set_hexpand(True)
            
            btn_del = Gtk.Button(icon_name="user-trash-symbolic")
            btn_del.add_css_class("destructive-action")
            btn_del.connect("clicked", self.on_delete_domain, goal, domain)
            
            row.append(lbl)
            row.append(btn_del)
            self.filter_listbox.append(row)

    def on_add_domain(self, btn):
        domain = self.entry_new_domain.get_text().strip()
        if not domain: return
        
        goals = self.settings_data.get("goals", [])
        idx = self.filter_goal_combo.get_selected()
        goal = goals[idx]
        
        if "filters" not in self.settings_data:
            self.settings_data["filters"] = {}
        if goal not in self.settings_data["filters"]:
            self.settings_data["filters"][goal] = []
            
        if domain not in self.settings_data["filters"][goal]:
            self.settings_data["filters"][goal].append(domain)
            self.save_settings()
            self.refresh_filter_list()
            self.entry_new_domain.set_text("")

    def on_delete_domain(self, btn, goal, domain):
        if goal in self.settings_data.get("filters", {}):
            if domain in self.settings_data["filters"][goal]:
                self.settings_data["filters"][goal].remove(domain)
                self.save_settings()
                self.refresh_filter_list()

    def create_pomodoro_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(30)
        box.set_margin_start(30)
        box.set_margin_end(30)
        pomo_settings = self.settings_data.get("pomodoro", {})
        box.append(self.create_spin_row("Work Duration (min)", "work_duration", pomo_settings))
        box.append(self.create_spin_row("Short Break (min)", "short_break", pomo_settings))
        box.append(self.create_spin_row("Long Break (min)", "long_break", pomo_settings))
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl = Gtk.Label(label="Show Intention Popup", xalign=0)
        lbl.set_hexpand(True)
        switch = Gtk.Switch()
        switch.set_active(pomo_settings.get("intention_popup", True))
        switch.connect("state-set", self.on_pomo_bool_change, "intention_popup")
        row.append(lbl)
        row.append(switch)
        box.append(row)
        return box
    
    def create_spin_row(self, label_text, key, settings_dict):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl = Gtk.Label(label=label_text, xalign=0)
        lbl.set_hexpand(True)
        adj = Gtk.Adjustment(value=settings_dict.get(key, 25), lower=1, upper=120, step_increment=1, page_increment=5)
        spin = Gtk.SpinButton(adjustment=adj)
        spin.connect("value-changed", self.on_pomo_val_change, key)
        row.append(lbl)
        row.append(spin)
        return row

    def on_pomo_val_change(self, spin, key):
        if "pomodoro" not in self.settings_data:
            self.settings_data["pomodoro"] = {}
        self.settings_data["pomodoro"][key] = int(spin.get_value())
        self.save_settings()

    def on_pomo_bool_change(self, switch, state, key):
        if "pomodoro" not in self.settings_data:
            self.settings_data["pomodoro"] = {}
        self.settings_data["pomodoro"][key] = state
        self.save_settings()
        
    def on_system_bool_change(self, switch, state, key):
        self.settings_data[key] = state
        self.save_settings()
    def create_shortcuts_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(30)
        box.set_margin_bottom(30)
        box.set_margin_start(30)
        box.set_margin_end(30)

        # Header
        box.append(Gtk.Label(label="Keyboard Shortcuts", css_classes=["title-1"], xalign=0))
        box.append(Gtk.Label(label="Edit keybindings for Hyprland. Changes apply immediately upon saving.", css_classes=["dim-label"], xalign=0))

        # List
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        self.shortcuts_listbox = Gtk.ListBox()
        self.shortcuts_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.shortcuts_listbox.add_css_class("boxed-list")
        scroll.set_child(self.shortcuts_listbox)
        box.append(scroll)
        
        # Bottom Bar
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_halign(Gtk.Align.END)
        btn_reload = Gtk.Button(label="Reload Config")
        btn_reload.connect("clicked", lambda b: self.refresh_shortcuts_list())
        
        btn_save = Gtk.Button(label="Save Changes")
        btn_save.add_css_class("suggested-action")
        btn_save.connect("clicked", self.on_save_shortcuts)
        
        btn_box.append(btn_reload)
        btn_box.append(btn_save)
        box.append(btn_box)

        self.current_bindings = []
        self.refresh_shortcuts_list()
        return box

    def load_keybindings(self):
        bindings = []
        current_section = "General"
        if not os.path.exists(KEYBINDINGS_FILE): return []
        
        try:
            with open(KEYBINDINGS_FILE, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    if line.startswith("# --"):
                        current_section = line.strip("# -").strip()
                    elif line.startswith("bind") and "=" in line:
                        try:
                            # Split by first =
                            _, content = line.split("=", 1)
                            parts = [p.strip() for p in content.split(",")]
                            if len(parts) >= 3:
                                mods = parts[0]
                                key = parts[1]
                                action = parts[2]
                                args = ",".join(parts[3:]) if len(parts) > 3 else ""
                                
                                bindings.append({
                                    "section": current_section,
                                    "mods": mods,
                                    "key": key,
                                    "action": action,
                                    "args": args,
                                    "original_line": line
                                })
                        except: pass
        except Exception as e:
            print(f"Error loading bindings: {e}")
            
        return bindings

    def refresh_shortcuts_list(self):
        self.current_bindings = self.load_keybindings()
        
        child = self.shortcuts_listbox.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.shortcuts_listbox.remove(child)
            child = next_child
            
        last_section = None
        
        for i, b in enumerate(self.current_bindings):
            if b["section"] != last_section:
                # Header
                h_row = Gtk.Box(margin_top=20, margin_bottom=5, margin_start=10)
                h_lbl = Gtk.Label(label=b["section"], css_classes=["heading"])
                h_row.append(h_lbl)
                self.shortcuts_listbox.append(h_row)
                last_section = b["section"]
                
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.set_margin_top(5); row.set_margin_bottom(5)
            row.set_margin_start(10); row.set_margin_end(10)
            
            # Action Desc
            desc = f"{b['action']} {b['args']}"
            if b['action'] == "exec": desc = f"Run: {b['args']}"
            elif b['action'] == "workspace": desc = f"Workspace {b['args']}"
            elif b['action'] == "movetoworkspace": desc = f"Move to {b['args']}"
            
            lbl_desc = Gtk.Label(label=desc, xalign=0, hexpand=True)
            lbl_desc.set_ellipsize(3) # Ellipsize end
            
            # Editors
            entry_mods = Gtk.Entry(text=b['mods'])
            entry_mods.set_width_chars(15)
            entry_mods.set_placeholder_text("SUPER SHIFT...")
            
            entry_key = Gtk.Entry(text=b['key'])
            entry_key.set_width_chars(10)
            entry_key.set_placeholder_text("Q, 1, left...")
            
            # Connect updates
            entry_mods.connect("changed", self.on_binding_change, i, "mods")
            entry_key.connect("changed", self.on_binding_change, i, "key")
            
            row.append(lbl_desc)
            row.append(entry_mods)
            row.append(entry_key)
            self.shortcuts_listbox.append(row)

    def on_binding_change(self, entry, idx, field):
        self.current_bindings[idx][field] = entry.get_text()

    def on_save_shortcuts(self, btn):
        # Reconstruct file
        sections = {}
        for b in self.current_bindings:
            if b["section"] not in sections: sections[b["section"]] = []
            sections[b["section"]].append(b)
            
        try:
            with open(KEYBINDINGS_FILE, 'w') as f:
                f.write("$mainMod = SUPER\n\n")
                for sec, binds in sections.items():
                    f.write(f"# -- {sec} --\n")
                    for b in binds:
                        # Infer prefix
                        prefix = "bind"
                        if "bindm" in b.get("original_line", ""): prefix = "bindm"
                        if "bindel" in b.get("original_line", ""): prefix = "bindel"
                        
                        line = f"{prefix} = {b['mods']}, {b['key']}, {b['action']}"
                        if b['args']: line += f", {b['args']}"
                        f.write(f"{line}\n")
                    f.write("\n")
            
            # Reload Hyprland
            os.system("hyprctl reload")
            
        except Exception as e:
            print(f"Error saving: {e}")

if __name__ == "__main__":
    app = SettingsApp()
    app.run(sys.argv)
