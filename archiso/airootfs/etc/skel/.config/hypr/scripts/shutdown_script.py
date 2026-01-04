#!/usr/bin/env python3
import os
import json
import subprocess
import sys
import time
from datetime import datetime

SETTINGS_FILE = os.path.expanduser("~/.config/hypr/settings.json")
LOG_FILE = os.path.expanduser("~/session_logs.jsonl")
SESSION_FILE = "/tmp/sddm_session.json"
QML_PATH = os.path.expanduser("~/.config/hypr/scripts/SessionFeedback.qml")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def get_current_session():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"goal": "Unknown", "intention": "Unknown"}

def log_feedback(rating, comment, session_data):
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "feedback",
        "goal": session_data.get("goal"),
        "intention": session_data.get("intention"),
        "rating": rating,
        "comment": comment
    }
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Failed to log: {e}")

def run_feedback_gui(goal, intention):
    script_path = os.path.expanduser("~/.config/hypr/scripts/session_feedback.py")
    cmd = [script_path, "--goal", goal, "--intention", intention]
    
    try:
        # Run the python GTK script
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        
        rating = None
        comment = ""
        
        for line in output.splitlines():
            if "RATING:" in line:
                try:
                    rating = int(line.split("RATING:", 1)[1].strip())
                except:
                    pass
            if "COMMENT:" in line:
                comment = line.split("COMMENT:", 1)[1].strip()
            if "SKIP" in line:
                return None, None
                
        return rating, comment
    except Exception as e:
        print(f"Error running GUI: {e}")
        return None, None

def main():
    settings = load_settings()
    
    # Check if shutdown feedback is enabled (default True)
    if settings.get("shutdown_feedback", True):
        session = get_current_session()
        
        # Only prompt if we have a valid session context
        if session.get("goal") and session.get("goal") != "Default":
            print("Launching Feedback...")
            rating, comment = run_feedback_gui(session.get("goal"), session.get("intention"))
            
            if rating is not None:
                log_feedback(rating, comment, session)
                time.sleep(0.5) # Ensure write completion

    # Proceed to shutdown
    print("Shutting down...")
    subprocess.run(["systemctl", "poweroff"])

if __name__ == "__main__":
    main()
