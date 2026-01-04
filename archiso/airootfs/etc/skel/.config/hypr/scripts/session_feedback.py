#!/usr/bin/env python3
import sys
import os
import gi
import argparse

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, Gio

class SessionFeedbackApp(Gtk.Application):
    def __init__(self, goal, intention):
        super().__init__(application_id="com.malek.sessionfeedback",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.goal = goal
        self.intention = intention
        self.rating = 5

    def do_activate(self):
        self.apply_theme()
        
        window = Gtk.ApplicationWindow(application=self, title="Session Feedback")
        window.set_default_size(500, 450)
        window.set_decorated(False)
        window.set_resizable(False)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        main_box.set_margin_top(30)
        main_box.set_margin_bottom(30)
        main_box.set_margin_start(30)
        main_box.set_margin_end(30)
        main_box.add_css_class("window-content")
        window.set_child(main_box)

        lbl_title = Gtk.Label(label="Session Complete")
        lbl_title.add_css_class("title-1")
        main_box.append(lbl_title)
        
        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        lbl_goal = Gtk.Label(label=f"GOAL: {self.goal}")
        lbl_goal.add_css_class("heading")
        info_box.append(lbl_goal)
        lbl_int = Gtk.Label(label=f"INTENTION: {self.intention}")
        lbl_int.add_css_class("dim-label")
        info_box.append(lbl_int)
        main_box.append(info_box)

        rating_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        row_r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        row_r.append(Gtk.Label(label="Productivity Rating", css_classes=["heading"]))
        self.lbl_val = Gtk.Label(label="5/10", css_classes=["title-2", "success"])
        self.lbl_val.set_hexpand(True)
        self.lbl_val.set_halign(Gtk.Align.END)
        row_r.append(self.lbl_val)
        rating_box.append(row_r)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 10, 1)
        scale.set_value(5)
        scale.set_draw_value(False)
        scale.connect("value-changed", self.on_rating_change)
        rating_box.append(scale)
        main_box.append(rating_box)

        comment_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        comment_box.append(Gtk.Label(label="Comments / Retrospective", css_classes=["heading"], xalign=0))
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(80)
        scrolled.set_vexpand(True)
        self.txt_comment = Gtk.TextView()
        self.txt_comment.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scrolled.set_child(self.txt_comment)
        frame = Gtk.Frame()
        frame.set_child(scrolled)
        comment_box.append(frame)
        main_box.append(comment_box)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_margin_top(10)
        btn_skip = Gtk.Button(label="Skip")
        btn_skip.add_css_class("flat")
        btn_skip.set_size_request(100, -1)
        btn_skip.connect("clicked", lambda x: self.quit_app(skip=True))
        
        btn_submit = Gtk.Button(label="Submit & Close")
        btn_submit.set_hexpand(True)
        btn_submit.connect("clicked", lambda x: self.quit_app())
        
        btn_box.append(btn_skip)
        btn_box.append(btn_submit)
        main_box.append(btn_box)

        window.present()

    def on_rating_change(self, scale):
        val = int(scale.get_value())
        self.rating = val
        self.lbl_val.set_label(f"{val}/10")

    def quit_app(self, skip=False):
        if skip: print("SKIP")
        else:
            buffer = self.txt_comment.get_buffer()
            start, end = buffer.get_bounds()
            text = buffer.get_text(start, end, True).replace("\n", " ")
            print(f"RATING:{self.rating}")
            print(f"COMMENT:{text}")
        self.quit()

    def apply_theme(self):
        try:
            theme_name = "Adwaita"
            config_path = os.path.expanduser("~/.config/gtk-4.0/settings.ini")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    for line in f:
                        if "gtk-theme-name" in line:
                            theme_name = line.split("=")[1].strip()
            
            settings = Gtk.Settings.get_default()
            settings.props.gtk_application_prefer_dark_theme = True
            
            # Check multiple common theme locations
            paths = [
                os.path.expanduser(f"~/.themes/{theme_name}/gtk-4.0/gtk.css"),
                os.path.expanduser(f"~/.local/share/themes/{theme_name}/gtk-4.0/gtk.css"),
                f"/usr/share/themes/{theme_name}/gtk-4.0/gtk.css"
            ]
            
            for css_path in paths:
                if os.path.exists(css_path):
                    print(f"Loading theme from: {css_path}")
                    provider = Gtk.CssProvider()
                    provider.load_from_path(css_path)
                    Gtk.StyleContext.add_provider_for_display(
                        Gdk.Display.get_default(),
                        provider,
                        Gtk.STYLE_PROVIDER_PRIORITY_USER
                    )
                    break
            
            # Semantic overrides
            fix_provider = Gtk.CssProvider()
            fix_css = """
            .title-1 { font-size: 20pt; font-weight: 800; }
            .title-2 { font-size: 16pt; font-weight: 600; }
            .heading { font-weight: 700; opacity: 0.9; }
            .dim-label { opacity: 0.6; }
            .success { color: #a6e3a1; }
            
            /* Fix window background and outline */
            window {
                background-color: @theme_bg_color;
                color: @theme_fg_color;
            }
            
            .window-content {
                background-color: @theme_bg_color;
                color: @theme_fg_color;
            }
            """
            fix_provider.load_from_data(fix_css.encode())
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                fix_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            print(f"Failed to apply theme: {e}", file=sys.stderr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal", default="Work")
    parser.add_argument("--intention", default="Focus")
    args = parser.parse_args()
    app = SessionFeedbackApp(args.goal, args.intention)
    app.run(None)