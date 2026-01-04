#!/bin/bash
# custom clock script with calendar tooltip
# Now supports dynamic theming from ~/.config/waybar/style.css -> theme/colors

read -r -d '' PYTHON_SCRIPT << 'EOF'
import json
import datetime
import calendar
import os
import re
from pathlib import Path

# 1. Determine current theme colors
bg_color = "#000000" # default
fg_color = "#ffffff" # default

try:
    # Resolve the symlink to find the actual theme directory
    waybar_style = Path(os.path.expanduser("~/.config/waybar/style.css"))
    
    # Check if it exists and is a symlink (or just a file if not symlinked but valid)
    if waybar_style.exists():
        # resolve() handles symlinks and absolute paths
        real_path = waybar_style.resolve()
        theme_dir = real_path.parent
        colors_file = theme_dir / "colors"
        
        if colors_file.exists():
            with open(colors_file, "r") as f:
                content = f.read()
                # Parse shell variables: var='value'
                bg_match = re.search(r"bg_color='([0-9a-fA-F]+)'", content)
                fg_match = re.search(r"fg_color='([0-9a-fA-F]+)'", content)
                
                if bg_match:
                    bg_color = f"#{bg_match.group(1)}"
                if fg_match:
                    fg_color = f"#{fg_match.group(1)}"

except Exception as e:
    # If anything goes wrong, we stick to defaults. 
    # Can debug by printing to stderr if needed: sys.stderr.write(str(e))
    pass

# 2. Generate Calendar
now = datetime.datetime.now()
cal = calendar.Calendar(firstweekday=6)

# Header
month_name = calendar.month_name[now.month]
header = f"<span color='{fg_color}'><b>{month_name} {now.year}</b></span>"

# Days header
days_header = "Su Mo Tu We Th Fr Sa"

body = ""
for week in cal.monthdayscalendar(now.year, now.month):
    week_str = ""
    for d in week:
        if d == 0:
            week_str += "   "
        else:
            d_str = f"{d:2d}"
            if d == now.day:
                # Highlight current day: Invert theme colors
                # Background = Theme Foreground (bright)
                # Text = Theme Background (dark)
                week_str += f"<span background='{fg_color}' color='{bg_color}'><b>{d_str}</b></span> "
            else:
                week_str += f"{d_str} "
    body += week_str.rstrip() + "\n"

tooltip = f"{header}\n{days_header}\n{body.rstrip()}"

output = {
    "text": now.strftime("%I:%M %p"),
    "tooltip": tooltip,
    "class": "custom-clock"
}
print(json.dumps(output))
EOF

python3 -c "$PYTHON_SCRIPT"
