#!/usr/bin/env python3
import sys
import os
import urllib.request

HOSTS_PATH = "/etc/hosts"
REDIRECT_IP = "127.0.0.1"
BLOCK_IP = "0.0.0.0"

# Markers for Goal Blocking
START_MARKER = "# --- HYPRFOCUS BLOCK START ---"
END_MARKER = "# --- HYPRFOCUS BLOCK END ---"

# Markers for Ad Blocking
ADS_START_MARKER = "# --- HYPRFOCUS ADS START ---"
ADS_END_MARKER = "# --- HYPRFOCUS ADS END ---"

# Determine Home Directory (Sudo-aware)
real_user = os.getenv("SUDO_USER") or os.getenv("USER")
if os.getuid() == 0 and os.getenv("SUDO_USER"):
    home_dir = os.path.expanduser(f"~{os.getenv('SUDO_USER')}")
else:
    home_dir = os.path.expanduser("~")

AD_CACHE_FILE = os.path.join(home_dir, ".config/hypr/adblock_list.txt")
AD_SOURCE_URL = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"

def clean_hosts(lines):
    new_lines = []
    skip_goal = False
    skip_ads = False
    
    for line in lines:
        # Goal Section
        if START_MARKER in line:
            skip_goal = True
            continue
        if END_MARKER in line:
            skip_goal = False
            continue
            
        # Ads Section
        if ADS_START_MARKER in line:
            skip_ads = True
            continue
        if ADS_END_MARKER in line:
            skip_ads = False
            continue
            
        if not skip_goal and not skip_ads:
            new_lines.append(line)
    return new_lines

def get_current_blocks(marker_start, marker_end):
    # Reads the existing block from file to preserve it when modifying the other section
    blocks = []
    try:
        with open(HOSTS_PATH, 'r') as f:
            lines = f.readlines()
        
        in_block = False
        for line in lines:
            if marker_start in line:
                in_block = True
                blocks.append(line)
                continue
            if marker_end in line:
                in_block = False
                blocks.append(line)
                break
            if in_block:
                blocks.append(line)
    except:
        pass
    return blocks

def write_hosts(clean_lines, goal_lines, ad_lines):
    # Ensure newline consistency
    if clean_lines and not clean_lines[-1].endswith('\n'):
        clean_lines[-1] += '\n'
        
    final_lines = clean_lines + goal_lines + ad_lines
    
    try:
        with open(HOSTS_PATH, 'w') as f:
            f.writelines(final_lines)
    except Exception as e:
        print(f"Error writing hosts: {e}")
        sys.exit(1)

def apply_goal_blocks(domains):
    try:
        with open(HOSTS_PATH, 'r') as f:
            lines = f.readlines()
        
        clean_lines = clean_hosts(lines)
        ad_lines = get_current_blocks(ADS_START_MARKER, ADS_END_MARKER)
        
        goal_lines = [START_MARKER + "\n"]
        for domain in domains:
            domain = domain.strip()
            if domain:
                if domain.startswith("www."):
                    clean_domain = domain[4:]
                    goal_lines.append(f"{REDIRECT_IP} {clean_domain}\n")
                    goal_lines.append(f"{REDIRECT_IP} {domain}\n")
                else:
                    goal_lines.append(f"{REDIRECT_IP} {domain}\n")
                    goal_lines.append(f"{REDIRECT_IP} www.{domain}\n")
        goal_lines.append(END_MARKER + "\n")
        
        write_hosts(clean_lines, goal_lines, ad_lines)
        print(f"Blocked {len(domains)} goal domains.")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def update_ad_cache():
    print("Downloading ad blocklist...")
    try:
        with urllib.request.urlopen(AD_SOURCE_URL) as response:
            data = response.read().decode('utf-8')
        
        # Process lines: extract only 0.0.0.0 entries, ignore localhost
        valid_lines = []
        for line in data.splitlines():
            line = line.strip()
            if line.startswith("0.0.0.0") and not line.startswith("0.0.0.0 0.0.0.0"):
                valid_lines.append(line + "\n")
                
        with open(AD_CACHE_FILE, 'w') as f:
            f.writelines(valid_lines)
        print(f"Adlist updated. {len(valid_lines)} rules saved.")
    except Exception as e:
        print(f"Failed to update adlist: {e}")

def apply_ads(enable):
    try:
        with open(HOSTS_PATH, 'r') as f:
            lines = f.readlines()
        
        clean_lines = clean_hosts(lines)
        goal_lines = get_current_blocks(START_MARKER, END_MARKER)
        
        ad_lines = []
        if enable:
            if not os.path.exists(AD_CACHE_FILE):
                print("Ad cache not found. Updating...")
                update_ad_cache()
            
            ad_lines.append(ADS_START_MARKER + "\n")
            try:
                with open(AD_CACHE_FILE, 'r') as f:
                    ad_lines.extend(f.readlines())
            except:
                print("Error reading ad cache")
            ad_lines.append(ADS_END_MARKER + "\n")
            print("Ad blocking ENABLED.")
        else:
            print("Ad blocking DISABLED.")
            
        write_hosts(clean_lines, goal_lines, ad_lines)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: hosts_manager.py [clear|ads on|ads off|ads update|domain1,domain2...]")
        sys.exit(1)
        
    arg = sys.argv[1]
    
    if arg == "clear":
        apply_goal_blocks([])
    elif arg == "ads":
        if len(sys.argv) < 3:
            print("Usage: ads [on|off|update]")
        else:
            sub = sys.argv[2]
            if sub == "on": apply_ads(True)
            elif sub == "off": apply_ads(False)
            elif sub == "update": update_ad_cache()
    else:
        domains = arg.split(',')
        apply_goal_blocks(domains)
