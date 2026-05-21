#!/usr/bin/env python3
import time
import os
import signal
import sys
import subprocess

# Reuse logic from media_blackout by importing or duplicating.
# Duplicating for standalone robustness.
import json
import glob

def enforce_chrome(allowed_domains):
    val = 2 # Block
    paths = [
        "~/.config/google-chrome", "~/.config/chromium", 
        "~/.config/BraveSoftware/Brave-Browser", "~/.config/microsoft-edge",
        "~/.var/app/com.google.Chrome/config/google-chrome",
        "~/.var/app/org.chromium.Chromium/config/chromium"
    ]
    for p in paths:
        base = os.path.expanduser(p)
        if not os.path.exists(base): continue
        profiles = glob.glob(os.path.join(base, "Default")) + glob.glob(os.path.join(base, "Profile *"))
        for prof in profiles:
            pref_file = os.path.join(prof, "Preferences")
            if not os.path.exists(pref_file): continue
            try:
                with open(pref_file, 'r') as f: data = json.load(f)
                
                # Check if already set to avoid IO spam
                curr = data.get("profile", {}).get("default_content_setting_values", {}).get("images", 1)
                if curr == 2:
                    # Check exceptions too? Maybe excessive.
                    pass
                else:
                    if "profile" not in data: data["profile"] = {}
                    if "default_content_setting_values" not in data["profile"]:
                        data["profile"]["default_content_setting_values"] = {}
                    data["profile"]["default_content_setting_values"]["images"] = 2
                    
                    # Exceptions logic (simplified for enforcer)
                    if "content_settings" not in data["profile"]: data["profile"]["content_settings"] = {}
                    if "exceptions" not in data["profile"]["content_settings"]: data["profile"]["content_settings"]["exceptions"] = {}
                    
                    data["profile"]["content_settings"]["exceptions"]["images"] = {}
                    for d in allowed_domains:
                        clean = d.replace("www.", "")
                        k = f"https://[*.]" + clean + ":443,*"
                        data["profile"]["content_settings"]["exceptions"]["images"][k] = {"setting": 1}

                    with open(pref_file, 'w') as f: json.dump(data, f)
                    # print(f"Enforced Chrome: {prof}")
            except: pass

def enforce_firefox(allowed_domains):
    # Firefox requires user.js. If it exists and has the wrong value, update it.
    base = os.path.expanduser("~/.mozilla/firefox")
    if not os.path.exists(base): return
    profiles = glob.glob(os.path.join(base, "*.default-release")) + glob.glob(os.path.join(base, "*.default"))
    
    expected_line = 'user_pref("permissions.default.image", 2);\n'
    
    for prof in profiles:
        user_js = os.path.join(prof, "user.js")
        needs_write = False
        lines = []
        
        if os.path.exists(user_js):
            with open(user_js, 'r') as f: lines = f.readlines()
            
        # Check if line exists
        if expected_line not in lines:
            # Remove old
            lines = [l for l in lines if "permissions.default.image" not in l]
            lines.append(expected_line)
            needs_write = True
            
        if needs_write:
            try:
                with open(user_js, 'w') as f: f.writelines(lines)
                # print(f"Enforced Firefox: {prof}")
            except: pass

def main(allowed_str):
    allowed = [d.strip() for d in allowed_str.split(',') if d.strip()]
    print(f"Media Guard Started. Enforcing block on all except: {allowed}")
    
    while True:
        try:
            enforce_chrome(allowed)
            enforce_firefox(allowed)
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(5)

if __name__ == "__main__":
    allowed = sys.argv[1] if len(sys.argv) > 1 else ""
    main(allowed)
