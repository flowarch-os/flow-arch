#!/usr/bin/env python3
import os
import json
import time
import subprocess
import sys
from datetime import datetime

SESSION_FILE = "/tmp/sddm_session.json"
TIMER_FILE = "/tmp/session_timer"
BREAK_COUNTDOWN_FILE = "/tmp/pomodoro_break_countdown"
INTENTION_FILE = "/tmp/pomodoro_intention"
LOG_FILE = os.path.expanduser("~/session_logs.jsonl")
STATUS_TEXT_FILE = "/tmp/pomodoro_status_text"
HYPRLOCK_UNIFIED = os.path.expanduser("~/.config/hypr/hyprlock_unified.conf")
SETTINGS_FILE = os.path.expanduser("~/.config/hypr/settings.json")
SWITCH_THEME_SCRIPT = os.path.expanduser("~/.config/hypr/scripts/switch_theme.sh")
HOSTS_MANAGER_SCRIPT = "/usr/local/bin/hosts_manager.py"
REDIRECT_SERVER_SCRIPT = "/usr/local/bin/redirect_server.py"
CA_MANAGER_SCRIPT = os.path.expanduser("~/.config/hypr/scripts/ca_manager.py")

def notify(summary, body, urgency="normal"):
    subprocess.run(["notify-send", "-u", urgency, summary, body])

def write_file(path, content):
    try:
        with open(path, "w") as f:
            f.write(content)
    except:
        pass

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def get_session_data(timeout=10):
    start_wait = time.time()
    while time.time() - start_wait < timeout:
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r') as f:
                    data = json.load(f)
                return data
            except (json.JSONDecodeError, IOError):
                time.sleep(0.5)
                continue
        time.sleep(0.5)
    return None

def log_session(data, session_type="start"):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": session_type,
        "goal": data.get("goal"),
        "intention": data.get("intention"),
        "duration": data.get("duration"),
        "pomodoro": data.get("pomodoro")
    }
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Failed to log: {e}")

def get_new_intention(current_goal):
    qml_path = os.path.expanduser("~/.config/hypr/scripts/CheckIn.qml")
    
    # Launch qmlscene and capture output
    # We pass the main goal via a property override
    cmd = ["qmlscene", "--path", os.path.dirname(qml_path), "-p", f"mainGoal={current_goal}", qml_path]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        
        for line in output.splitlines():
            if "NEW:" in line:
                return line.split("NEW:", 1)[1].strip()
            if "CONTINUE" in line:
                try:
                    with open(INTENTION_FILE, 'r') as f:
                        return f.read().strip()
                except:
                    return "Focus"
                    
        return "Focus"
    except Exception as e:
        print(f"Error: {e}")
        return "Focus"

def run_pomodoro(data, settings):
    pomo_settings = settings.get("pomodoro", {})
    work_duration = int(pomo_settings.get("work_duration", 25)) * 60
    short_break = int(pomo_settings.get("short_break", 5)) * 60
    long_break = int(pomo_settings.get("long_break", 20)) * 60
    show_popup = pomo_settings.get("intention_popup", True)
    
    current_intention = data.get("intention", "Focus")
    goal = data.get("goal", "Work")
    
    # Initialize intention file
    try:
        with open(INTENTION_FILE, 'w') as f:
            f.write(current_intention)
    except:
        pass
        
    pomodoros_completed = 0
    
    while True:
        # --- WORK PHASE ---
        notify("Pomodoro Started", f"Focus: {current_intention}")
        start_time = time.time()
        end_time = start_time + work_duration
        
        while time.time() < end_time:
            remaining = end_time - time.time()
            mins, secs = divmod(int(remaining), 60)
            write_file(TIMER_FILE, f"{mins:02d}:{secs:02d} [WORK]")
            time.sleep(1)
            
        pomodoros_completed += 1
        
        # Determine Break Length
        if pomodoros_completed % 4 == 0:
            break_duration = long_break
            notify("Long Break!", f"Great job! Enjoy a {break_duration//60} minute break.", "critical")
        else:
            break_duration = short_break
            notify("Time's Up!", f"Locking screen for {break_duration//60} minute break.", "critical")

        time.sleep(2)
        
        break_end = time.time() + break_duration
        write_file(STATUS_TEXT_FILE, "POMODORO BREAK")
        
        # --- LOCK LOOP ---
        while True:
            remaining = break_end - time.time()
            mins, secs = divmod(int(max(0, remaining)), 60)
            write_file(BREAK_COUNTDOWN_FILE, f"{mins:02d}:{secs:02d}")
            write_file(TIMER_FILE, "BREAK")
            
            # Start Hyprlock (Unified - Password Only)
            lock_proc = subprocess.Popen(["hyprlock", "--config", HYPRLOCK_UNIFIED])
            
            while lock_proc.poll() is None:
                remaining = break_end - time.time()
                mins, secs = divmod(int(max(0, remaining)), 60)
                write_file(BREAK_COUNTDOWN_FILE, f"{mins:02d}:{secs:02d}")
                
                if remaining <= 0:
                    write_file(STATUS_TEXT_FILE, "BREAK COMPLETE")
                    write_file(BREAK_COUNTDOWN_FILE, "Unlock Now")
                
                time.sleep(0.5)
            
            if time.time() >= break_end:
                break # Valid unlock
            else:
                notify("Break Not Over", "Screen re-locking...", "critical")
                time.sleep(1)
                continue
        
        # --- CHECK-IN PHASE ---
        if show_popup:
            # Floating popup with 10s timeout
            new_int = get_new_intention(goal)
            if new_int:
                current_intention = new_int
            
        log_session({"goal": goal, "intention": current_intention}, session_type="pomodoro_segment")

def run_standard_timer(data):
    try:
        duration_mins = int(data.get("duration", 60))
    except:
        duration_mins = 60
        
    end_time = time.time() + (duration_mins * 60)
    warning_sent = False

    while True:
        remaining = end_time - time.time()
        if remaining <= 0:
            break
            
        if remaining <= 60 and not warning_sent:
            notify("System Shutdown", "Session ending in 1 minute!", "critical")
            warning_sent = True
            
        mins = int(max(0, remaining) // 60)
        secs = int(max(0, remaining) % 60)
        write_file(TIMER_FILE, f"{mins:02d}:{secs:02d}")
        time.sleep(1)

    # Clean up blocks before exit
    clean_blocks()

    notify("Session Ended", "Initiating shutdown sequence...", "critical")
    time.sleep(2)
    # Delegate to shutdown script which handles feedback
    shutdown_script = os.path.expanduser("~/.config/hypr/scripts/shutdown_script.py")
    subprocess.run([shutdown_script])

def log_debug(msg):
    try:
        with open("/tmp/session_debug.log", "a") as f:
            f.write(f"{datetime.now().isoformat()} - {msg}\n")
    except: pass

def start_redirect_server():
    log_debug("Checking redirect server...")
    # Check if running
    try:
        # Check if port 80 is used
        subprocess.check_output(["lsof", "-i", ":80"])
        log_debug("Redirect server already running.")
    except:
        # Not running, start it
        log_debug("Starting Redirect Server...")
        subprocess.Popen(["sudo", REDIRECT_SERVER_SCRIPT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def apply_blocks(goal, settings):
    log_debug(f"Applying blocks for {goal}")
    filters = settings.get("filters", {}).get(goal, [])
    if filters:
        print(f"Applying blocklist for {goal}: {filters}")
        domains_str = ",".join(filters)
        subprocess.run(["sudo", HOSTS_MANAGER_SCRIPT, domains_str])
    else:
        print(f"No blocklist for {goal}, clearing blocks.")
        clean_blocks()
    log_debug("Blocks applied.")

def apply_adblock(settings):
    log_debug("Checking Adblock settings...")
    if settings.get("ad_blocking", False):
        log_debug("Enabling Adblock")
        subprocess.run(["sudo", HOSTS_MANAGER_SCRIPT, "ads", "on"])
    else:
        log_debug("Disabling Adblock")
        subprocess.run(["sudo", HOSTS_MANAGER_SCRIPT, "ads", "off"])

def clean_blocks():
    log_debug("Cleaning blocks...")
    subprocess.run(["sudo", HOSTS_MANAGER_SCRIPT, "clear"])

def apply_theme(goal, settings):
    log_debug(f"Applying theme for {goal}")
    themes = settings.get("goal_themes", {})
    theme = themes.get(goal)
    if theme:
        print(f"Applying theme {theme} for goal {goal}")
        subprocess.run([SWITCH_THEME_SCRIPT, theme])
    log_debug("Theme applied.")

def main():
    log_debug("Session Manager Started")
    settings = load_settings()
    data = get_session_data()
    
    if not data:
        data = {"goal": "Default", "intention": "No intention provided", "duration": 60, "pomodoro": False}
    
    if os.path.exists(SESSION_FILE):
        try: os.remove(SESSION_FILE)
        except: pass

    # Start Services
    start_redirect_server()
    
    # Apply Goal Settings
    current_goal = data.get("goal")
    if current_goal:
        apply_theme(current_goal, settings)
        apply_blocks(current_goal, settings)
    
    # Apply Adblock
    apply_adblock(settings)

    log_session(data, "login")
    log_debug("Entering main loop")
    
    is_pomodoro = data.get("pomodoro", False)
    if isinstance(is_pomodoro, str):
        is_pomodoro = is_pomodoro.lower() == "true"
        
    try:
        if is_pomodoro:
            run_pomodoro(data, settings)
        else:
            run_standard_timer(data)
    except KeyboardInterrupt:
        clean_blocks()
    finally:
        clean_blocks()

if __name__ == "__main__":
    main()
