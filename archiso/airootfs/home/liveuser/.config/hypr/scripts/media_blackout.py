#!/usr/bin/env python3
import os
import json
import glob
import subprocess

def close_browsers():
    print("Closing browsers to ensure settings save...")
    subprocess.run(["killall", "-q", "google-chrome", "chromium", "firefox", "brave", "vivaldi"])
    import time
    time.sleep(1) # Give time to release file locks

def set_chrome_images(enable_blackout, allowed_domains):
    # 1 = Allow, 2 = Block
    val = 2 if enable_blackout else 1
    
    paths = [
        "~/.config/google-chrome", 
        "~/.config/chromium", 
        "~/.config/brave-flags",
        "~/.config/BraveSoftware/Brave-Browser",
        "~/.config/microsoft-edge",
        "~/.config/vivaldi",
        "~/.config/opera",
        # Flatpaks
        "~/.var/app/com.google.Chrome/config/google-chrome",
        "~/.var/app/org.chromium.Chromium/config/chromium",
        "~/.var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser",
        "~/.var/app/com.microsoft.Edge/config/microsoft-edge"
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
                
                if "profile" not in data: data["profile"] = {}
                if "default_content_setting_values" not in data["profile"]:
                    data["profile"]["default_content_setting_values"] = {}
                
                data["profile"]["default_content_setting_values"]["images"] = val
                
                # Exceptions
                if "content_settings" not in data["profile"]: data["profile"]["content_settings"] = {}
                if "exceptions" not in data["profile"]["content_settings"]: data["profile"]["content_settings"]["exceptions"] = {}
                
                if enable_blackout:
                    data["profile"]["content_settings"]["exceptions"]["images"] = {}
                    for d in allowed_domains:
                        clean_d = d.replace("www.", "")
                        key = f"https://[*.]" + clean_d + ":443,*"
                        key_http = f"http://[*.]" + clean_d + ":80,*"
                        
                        entry = {"last_modified": "1324567890000000", "setting": 1} # 1 = Allow
                        data["profile"]["content_settings"]["exceptions"]["images"][key] = entry
                        data["profile"]["content_settings"]["exceptions"]["images"][key_http] = entry
                
                with open(pref_file, 'w') as f:
                    json.dump(data, f)
                print(f"Updated Chrome config: {prof}")
            except Exception as e:
                print(f"Error Chrome {prof}: {e}")

def set_firefox_blackout(enable_blackout, allowed_domains):
    base = os.path.expanduser("~/.mozilla/firefox")
    if not os.path.exists(base): return
    
    profiles = glob.glob(os.path.join(base, "*.default-release")) + glob.glob(os.path.join(base, "*.default"))
    
    # Logic:
    # If Allowlist exists, we MUST allow download (val=1) and block via CSS.
    # If Allowlist empty, we block via Engine (val=2) AND CSS.
    
    engine_val = 1
    if enable_blackout:
        if not allowed_domains:
            engine_val = 2 # Hard block
        else:
            engine_val = 1 # Soft block (CSS only)
    
    css_content = ""
    if enable_blackout:
        # Base Block
        css_content += """
/* HYPRFOCUS MEDIA BLOCK */
@-moz-document url-prefix(http) {
    img, video, figure, canvas, svg, [style*=\"background-image\"] { 
        display: none !important; 
        visibility: hidden !important; 
        opacity: 0 !important;
    }
}
"""
        # Exceptions
        if allowed_domains:
            domains_css = ", ".join([f'domain("{d}")' for d in allowed_domains])
            css_content += f"""
@-moz-document {domains_css} {{
    img, video, figure, canvas, svg, [style*=\"background-image\"] {{
        display: block !important; 
        visibility: visible !important; 
        opacity: 1 !important;
    }}
}} """

    for prof in profiles:
        user_js = os.path.join(prof, "user.js")
        
        lines = []
        if os.path.exists(user_js):
            with open(user_js, 'r') as f: lines = f.readlines()
            
        keys = ["permissions.default.image", "toolkit.legacyUserProfileCustomizations.stylesheets"]
        lines = [l for l in lines if not any(k in l for k in keys)]
        
        lines.append('user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);\n')
        lines.append(f'user_pref("permissions.default.image", {engine_val});\n')
        
        try:
            with open(user_js, 'w') as f: f.writelines(lines)
            print(f"Updated Firefox user.js: {prof}")
        except: pass
        
        chrome_dir = os.path.join(prof, "chrome")
        os.makedirs(chrome_dir, exist_ok=True)
        css_file = os.path.join(chrome_dir, "userContent.css")
        
        existing_css = ""
        if os.path.exists(css_file):
            with open(css_file, 'r') as f: existing_css = f.read()
            
        import re
        existing_css = re.sub(r'/\* HYPRFOCUS MEDIA BLOCK \*/.*', '', existing_css, flags=re.DOTALL)
            
        final_css = existing_css.strip() + "\n" + css_content
            
        with open(css_file, 'w') as f: f.write(final_css)

def set_chrome_policies(enable_blackout, allowed_domains):
    # Enterprise Policy path
    policy_dir = os.path.expanduser("~/.config/google-chrome/Policies/managed")
    os.makedirs(policy_dir, exist_ok=True)
    policy_file = os.path.join(policy_dir, "focus_policy.json")
    
    if not enable_blackout:
        if os.path.exists(policy_file): os.remove(policy_file)
        return

    # 1 = Allow, 2 = Block, 3 = Ask
    policy = {
        "DefaultImagesSetting": 2,
        "ImagesAllowedForUrls": [f"https://{d}" for d in allowed_domains] + [f"http://{d}" for d in allowed_domains]
    }
    
    try:
        with open(policy_file, 'w') as f:
            json.dump(policy, f, indent=4)
        print("Chrome Enterprise Policy Applied (Hard Lock)")
    except Exception as e:
        print(f"Policy Error: {e}")

def set_firefox_policies(enable_blackout, allowed_domains):
    # Firefox looks for distribution/policies.json relative to the binary or in profile?
    # Actually, the most reliable per-user way on Linux is inside the profile or distribution folder.
    # We'll try common profile distribution folders.
    base = os.path.expanduser("~/.mozilla/firefox")
    if not os.path.exists(base): return
    
    profiles = glob.glob(os.path.join(base, "*.default-release")) + glob.glob(os.path.join(base, "*.default"))
    
    policy = {
        "policies": {
            "Permissions": {
                "Camera": {"BlockNewRequests": True},
                "Microphone": {"BlockNewRequests": True}
            }
        }
    }
    
    if enable_blackout:
        policy["policies"]["DefaultRenderProcessLimit"] = 1 # unrelated but safe
        # Hard block images via policy
        policy["policies"]["Permissions"]["Image"] = {
            "Block": ["<all_urls>"],
            "Allow": [f"https://{d}/*" for d in allowed_domains]
        }
    else:
        # Clear or set to allow
        policy["policies"]["Permissions"]["Image"] = {"Default": "allow"}

    for prof in profiles:
        dist_dir = os.path.join(prof, "distribution")
        os.makedirs(dist_dir, exist_ok=True)
        policy_file = os.path.join(dist_dir, "policies.json")
        try:
            with open(policy_file, 'w') as f:
                json.dump(policy, f, indent=4)
            print(f"Firefox Policy Applied: {prof}")
        except: pass

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2: sys.exit(1)
    
    close_browsers()
    
    on = sys.argv[1] == "on"
    allowed_str = sys.argv[2] if len(sys.argv) > 2 else ""
    allowed = [d.strip() for d in allowed_str.split(',') if d.strip()]
    
    # Apply standard Preferences (Secondary layer)
    set_chrome_images(on, allowed)
    set_firefox_blackout(on, allowed)
    
    # Apply Enterprise Policies (Hard Lock layer)
    set_chrome_policies(on, allowed)
    set_firefox_policies(on, allowed)
    
    subprocess.run(["notify-send", "Nuclear Media Block Active", "Browsers are now hard-locked to Text-Only mode."])