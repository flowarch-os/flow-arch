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
HOSTS_MANAGER_SCRIPT = os.path.expanduser("~/.config/hypr/scripts/hosts_manager.py")
REDIRECT_SERVER_SCRIPT = os.path.expanduser("~/.config/hypr/scripts/redirect_server.py")
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
    """Return raw settings dict, then wrap with _normalize() to expose v2 layout
    with v1-fallback so existing key access patterns keep working."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return _normalize(json.load(f))
        except:
            pass
    return _normalize({})


def _normalize(raw):
    """Make a settings dict look v1-flat regardless of whether it's actually v1
    or v2. Lets the rest of session_manager keep using settings.get('goals') etc.

    v2 keys are read first; v1 keys are used as fallback. The returned dict
    contains BOTH the original namespaced structure AND a flat overlay.
    """
    if not isinstance(raw, dict):
        raw = {}
    focus = raw.get("focus", {}) if isinstance(raw.get("focus"), dict) else {}
    filters_ns = raw.get("filters", {}) if isinstance(raw.get("filters"), dict) else {}
    schedule = raw.get("schedule", {}) if isinstance(raw.get("schedule"), dict) else {}
    system_ns = raw.get("system", {}) if isinstance(raw.get("system"), dict) else {}
    vg = filters_ns.get("visual_guard", {}) if isinstance(filters_ns.get("visual_guard"), dict) else {}
    mb = filters_ns.get("media_blackout", {}) if isinstance(filters_ns.get("media_blackout"), dict) else {}
    bedtime = schedule.get("bedtime", {}) if isinstance(schedule.get("bedtime"), dict) else {}

    flat = {
        "goals":              focus.get("goals", raw.get("goals", [])),
        "goal_themes":        focus.get("goal_themes", raw.get("goal_themes", {})),
        "pomodoro":           focus.get("pomodoro", raw.get("pomodoro", {})),
        "shutdown_feedback":  focus.get("shutdown_feedback", raw.get("shutdown_feedback", True)),
        "ad_blocking":        filters_ns.get("ad_blocking", raw.get("ad_blocking", False)),
        "global_blacklist":   filters_ns.get("global_blacklist", raw.get("global_blacklist", [])),
        "keyword_blacklist":  filters_ns.get("keyword_blacklist", raw.get("keyword_blacklist", [])),
        "filters":            filters_ns.get("goal_filters", raw.get("filters", {})),
        "visual_guard":       vg.get("enabled", raw.get("visual_guard", False)),
        "visual_sensitivity": vg.get("sensitivity", raw.get("visual_sensitivity", 50)),
        "media_blackout":     mb.get("enabled", raw.get("media_blackout", False)),
        "media_allowlist":    mb.get("allowlist", raw.get("media_allowlist", [])),
        "calendar_events":    schedule.get("calendar_events", raw.get("calendar_events", [])),
        "tasks":              schedule.get("tasks", raw.get("tasks", [])),
        "bedtime_start":      bedtime.get("start", raw.get("bedtime_start", "23:00")),
        "bedtime_end":        bedtime.get("end", raw.get("bedtime_end", "05:00")),
    }
    # Preserve namespaces alongside the flat view.
    flat["focus"] = focus
    flat["_filters_ns"] = filters_ns
    flat["schedule"] = schedule
    flat["system"] = system_ns
    return flat

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

import threading
import socket

def hyprctl_fast(cmd, json_output=False):
    hypr_sig = os.getenv("HYPRLAND_INSTANCE_SIGNATURE")
    if not hypr_sig: return None
    sock_path = f"/tmp/hypr/{hypr_sig}/.socket.sock"
    
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(sock_path)
        
        full_cmd = f"j/{cmd}" if json_output else f"/{cmd}"
        # Hyprland socket commands are simple strings. 
        # Actually dispatch syntax is usually just "dispatch arg..." or just "arg..." depending on socket.
        # Command socket accepts raw args like "activewindow" or "dispatch ..."
        # To get JSON, use "j/activewindow"
        
        if not json_output and cmd.startswith("dispatch"):
            # dispatch commands via socket are just the command string usually
            # e.g. "dispatch closewindow ..."
            pass
            
        s.sendall(full_cmd.encode('utf-8'))
        
        # Read response
        response = b""
        while True:
            chunk = s.recv(4096)
            if not chunk: break
            response += chunk
            
        s.close()
        res_str = response.decode('utf-8')
        
        if json_output:
            return json.loads(res_str)
        return res_str
    except Exception as e:
        # Fallback if direct socket fails (unlikely)
        # print(f"Socket error: {e}")
        return None

def check_active_window_fast(keywords):
    if not keywords: return
    try:
        # Zero-latency socket query
        client = hyprctl_fast("activewindow", json_output=True)
        if not client: return
        
        title = client.get("title", "").lower()
        # Space stripping for robustness
        stripped_title = title.replace(" ", "")
        address = client.get("address")
        
        for kw in keywords:
            stripped_kw = kw.lower().replace(" ", "")
            if stripped_kw and stripped_kw in stripped_title:
                print(f"FAST BLOCK: {title}")
                hyprctl_fast(f"dispatch sendshortcut CTRL,W,address:{address}")
                notify("Focus Guard", f"Fast Block: {title}", "critical")
                return
    except:
        pass

def listen_hyprland_events(keywords):
    if not keywords: return
    
    hypr_sig = os.getenv("HYPRLAND_INSTANCE_SIGNATURE")
    if not hypr_sig: return
    
    sock_path = f"/tmp/hypr/{hypr_sig}/.socket2.sock"
    
    def worker():
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(sock_path)
            f = s.makefile('r')
            
            for line in f:
                if ">>" not in line: continue
                event, data = line.strip().split(">>", 1)
                
                if event == "activewindow" or event == "windowtitle":
                    # Instant check on the active window
                    check_active_window_fast(keywords)
                    
        except Exception as e:
            print(f"Socket listener error: {e}")

    t = threading.Thread(target=worker, daemon=True)
    t.start()

def check_window_titles(keywords):
    if not keywords: return
    
    # Static cache to prevent spamming the same window
    if not hasattr(check_window_titles, "last_trigger"):
        check_window_titles.last_trigger = {}
        
    try:
        result = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True, text=True)
        clients = json.loads(result.stdout)
        
        current_time = time.time()
        
        for client in clients:
            title = client.get("title", "").lower()
            # Remove all spaces for robust matching (catches "n u d e")
            stripped_title = title.replace(" ", "")
            address = client.get("address")
            
            # Skip if we acted on this window recently (5s cooldown)
            if current_time - check_window_titles.last_trigger.get(address, 0) < 5:
                continue
            
            for kw in keywords:
                # Also strip spaces from the keyword itself
                stripped_kw = kw.lower().replace(" ", "")
                if stripped_kw and stripped_kw in stripped_title:
                    print(f"Blocking content in: {title} (Matches '{kw}')")
                    
                    # Close the TAB (Ctrl+W) instead of the whole window
                    subprocess.run(["hyprctl", "dispatch", "sendshortcut", f"CTRL,W,address:{address}"])
                    
                    notify("Focus Guard", f"Closed Tab: {title} (Keyword: {kw})", "critical")
                    
                    # Mark processed
                    check_window_titles.last_trigger[address] = current_time
                    return
    except Exception as e:
        print(f"Error checking windows: {e}")

def check_visual_content(sensitivity=50):
    try:
        from PIL import Image
    except ImportError:
        return

    screenshot_path = "/tmp/visual_guard.png"
    
    try:
        # Get Active Workspace
        res_ws = subprocess.run(["hyprctl", "activeworkspace", "-j"], capture_output=True, text=True)
        if not res_ws.stdout.strip(): return
        active_ws_id = json.loads(res_ws.stdout).get("id")
        
        # Get Clients on Active Workspace
        res_clients = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True, text=True)
        if not res_clients.stdout.strip(): return
        all_clients = json.loads(res_clients.stdout)
        
        target_clients = [c for c in all_clients if c.get("workspace", {}).get("id") == active_ws_id]
        
        # Limit to checking 3 windows max per cycle to save CPU (prioritize last focused? or just list order)
        # List order usually Z-order or creation.
        # Let's check ALL but stop on first detection.
        
        for win in target_clients:
            x, y = win.get("at", [0, 0])
            w, h = win.get("size", [0, 0])
            addr = win.get("address")
            title = win.get("title", "Unknown")
            
            # Skip tiny windows (e.g. picture in picture or tooltips)
            if w < 100 or h < 100: continue
            
            # Capture specific window
            geometry = f"{x},{y} {w}x{h}"
            subprocess.run(["grim", "-g", geometry, screenshot_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(screenshot_path): continue
            
            img = Image.open(screenshot_path)
            img = img.resize((100, 100))
            img = img.convert("RGB")
            
            total_pixels = 100 * 100
            global_skin_pixels = 0
            
            # Grid settings
            grid_size = 5
            block_size = 20
            grid_counts = [[0 for _ in range(grid_size)] for _ in range(grid_size)]
            
            for px in range(100):
                for py in range(100):
                    r, g, b = img.getpixel((px, py))
                    if (r > 95 and g > 40 and b > 20 and
                        max(r, g, b) - min(r, g, b) > 15 and
                        abs(r - g) > 15 and
                        r > g and r > b):
                        
                        global_skin_pixels += 1
                        
                        gx = px // block_size
                        gy = py // block_size
                        if gx < grid_size and gy < grid_size:
                            grid_counts[gy][gx] += 1
            
            # Checks
            global_pct = (global_skin_pixels / total_pixels) * 100
            
            max_sector_pct = 0
            for r in range(grid_size):
                for c in range(grid_size):
                    pct = (grid_counts[r][c] / (block_size * block_size)) * 100
                    if pct > max_sector_pct: max_sector_pct = pct
            
            trigger = False
            reason = ""
            
            thresh_global = float(sensitivity)
            thresh_sector = float(sensitivity) + 15
            
            if global_pct > thresh_global:
                trigger = True
                reason = f"Global {global_pct:.0f}%"
            elif max_sector_pct > thresh_sector:
                trigger = True
                reason = f"Sector {max_sector_pct:.0f}%"
                
            if trigger: 
                print(f"Visual Guard Triggered on '{title}': {reason}")
                if addr:
                    subprocess.run(["hyprctl", "dispatch", "sendshortcut", f"CTRL,W,address:{addr}"])
                    notify("Visual Guard", f"Blocked Content in {title[:15]}... ({reason})", "critical")
                    return # Stop scanning others if one is killed (avoids race/confusion)
                    
    except Exception as e:
        print(f"Visual check error: {e}")

def run_pomodoro(data, settings):
    pomo_settings = settings.get("pomodoro", {})
    work_duration = int(pomo_settings.get("work_duration", 25)) * 60
    short_break = int(pomo_settings.get("short_break", 5)) * 60
    long_break = int(pomo_settings.get("long_break", 20)) * 60
    show_popup = pomo_settings.get("intention_popup", True)
    
    current_intention = data.get("intention", "Focus")
    goal = data.get("goal", "Work")
    keywords = settings.get("keyword_blacklist", [])
    visual_guard = settings.get("visual_guard", False)
    visual_sensitivity = settings.get("visual_sensitivity", 50)
    
    # Initialize intention file
    try:
        with open(INTENTION_FILE, 'w') as f:
            f.write(current_intention)
    except:
        pass
        
    pomodoros_completed = 0
    listen_hyprland_events(keywords)
    
    while True:
        # --- WORK PHASE ---
        notify("Pomodoro Started", f"Focus: {current_intention}")
        start_time = time.time()
        end_time = start_time + work_duration
        
        tick = 0
        while time.time() < end_time:
            # Reload settings dynamically
            if tick % 2 == 0: # Every 4s
                current_settings = load_settings()
                visual_guard = current_settings.get("visual_guard", False)
                visual_sensitivity = current_settings.get("visual_sensitivity", 50)
                # Note: keywords update requires restarting listener? 
                # For now just Visual Guard dynamic update is requested.
            
            check_window_titles(keywords)
            if visual_guard and tick % 3 == 0: # Every 6s
                check_visual_content(visual_sensitivity)
                
            remaining = end_time - time.time()
            mins, secs = divmod(int(remaining), 60)
            write_file(TIMER_FILE, f"{mins:02d}:{secs:02d} [WORK]")
            time.sleep(2)
            tick += 1
            
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

def run_standard_timer(data, settings):
    try:
        duration_mins = int(data.get("duration", 60))
    except:
        duration_mins = 60
        
    keywords = settings.get("keyword_blacklist", [])
    visual_guard = settings.get("visual_guard", False)
    visual_sensitivity = settings.get("visual_sensitivity", 50)
    end_time = time.time() + (duration_mins * 60)
    warning_sent = False
    
    # Start Event Listener for instant blocking
    listen_hyprland_events(keywords)

    tick = 0
    while True:
        # Reload settings dynamically
        if tick % 2 == 0:
            current_settings = load_settings()
            visual_guard = current_settings.get("visual_guard", False)
            visual_sensitivity = current_settings.get("visual_sensitivity", 50)

        check_window_titles(keywords)
        if visual_guard and tick % 3 == 0:
            check_visual_content(visual_sensitivity)
        
        remaining = end_time - time.time()
        if remaining <= 0:
            break
            
        if remaining <= 60 and not warning_sent:
            notify("System Shutdown", "Session ending in 1 minute!", "critical")
            warning_sent = True
            
        mins = int(max(0, remaining) // 60)
        secs = int(max(0, remaining) % 60)
        write_file(TIMER_FILE, f"{mins:02d}:{secs:02d}")
        time.sleep(2) # Reduced polling frequency
        tick += 1

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

MEDIA_DOMAINS = [
    "googlevideo.com", "ytimg.com", "vimeo.com", "dailymotion.com",
    "fbcdn.net", "twimg.com", "twitpic.com", "imgur.com", "giphy.com",
    "tenor.com", "gfycat.com", "photobucket.com", "flickr.com",
    "images-amazon.com", "media-amazon.com", "m.media-amazon.com",
    "static.flickr.com", "cdninstagram.com", "tiktokv.com", "byteoversea.com",
    "ibyteimg.com", "p16-tiktokcdn-com.akamaized.net", "vimeocdn.com",
    "pinterest.com", "pinimg.com", "redditmedia.com", "thumbs.redditmedia.com"
]

def apply_blocks(goal, settings):
    log_debug(f"Applying blocks for {goal}")
    filters = settings.get("filters", {}).get(goal, [])
    global_blacklist = settings.get("global_blacklist", [])
    
    # Combine and unique
    all_blocks = list(set(filters + global_blacklist))
    
    # System-wide Media Blackout (Nuclear Source-level block)
    if settings.get("media_blackout", False):
        all_blocks = list(set(all_blocks + MEDIA_DOMAINS))
    
    if all_blocks:
        print(f"Applying blocklist for {goal} (including global/media): {len(all_blocks)} domains")
        domains_str = ",".join(all_blocks)
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

    # Check for Normal Mode (Duration 0)
    try:
        duration = int(data.get("duration", 60))
    except (ValueError, TypeError):
        duration = 60

    if duration == 0:
        log_debug("Normal Mode: Duration is 0. Applying theme only.")
        clean_blocks()
        current_goal = data.get("goal")
        if current_goal:
            apply_theme(current_goal, settings)
        return

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
            run_standard_timer(data, settings)
    except KeyboardInterrupt:
        clean_blocks()
    finally:
        clean_blocks()

if __name__ == "__main__":
    main()
