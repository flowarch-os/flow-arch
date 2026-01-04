import os
from pathlib import Path

THEMES_DIR = Path.home() / ".config/hypr/themes"

def regenerate_css(theme_dir):
    colors_file = theme_dir / "colors"
    if not colors_file.exists():
        print(f"Skipping {theme_dir.name} (no colors file)")
        return

    # Parse shell variable file
    bg = ""
    fg = ""
    with open(colors_file, "r") as f:
        for line in f:
            if "bg_color=" in line:
                bg = line.split("'")[1]
            if "fg_color=" in line:
                fg = line.split("'")[1]
    
    if not bg or not fg:
        return

    # Generate CSS
    # Note: double curly braces {{ }} for literal braces in f-string
    css = f"""
* {{
    border: none;
    border-radius: 0;
    font-family: "JetBrainsMono Nerd Font", "FontAwesome", monospace;
    font-size: 14px;
    min-height: 0;
}}

window#waybar {{
    background: rgba({int(bg[:2],16)}, {int(bg[2:4],16)}, {int(bg[4:],16)}, 0.8);
    color: #{fg};
    border-bottom: 2px solid #{fg};
}}

#workspaces button {{
    padding: 0 5px;
    color: #ffffff;
    background: transparent;
}}

#workspaces button.active {{
    color: #{fg};
    border-bottom: 2px solid #{fg};
}}

#workspaces button:hover {{
    background: rgba(255, 255, 255, 0.1);
}}

#clock,
#custom-clock,
#battery,
#cpu,
#memory,
#network,
#pulseaudio,
#mpris,
#tray {{
    padding: 0 10px;
    background-color: transparent;
    color: #ffffff;
}}

#clock {{
    color: #{fg};
    font-weight: bold;
    margin-right: 20px;
}}

#battery.charging {{
    color: #00ff00;
}}

#battery.warning:not(.charging) {{
    color: #ffaa00;
}}

#battery.critical:not(.charging) {{
    color: #ff0000;
    animation-name: blink;
    animation-duration: 0.5s;
    animation-timing-function: linear;
    animation-iteration-count: infinite;
    animation-direction: alternate;
}}

@keyframes blink {{
    to {{
        color: #000000;
        background-color: #ff0000; 
    }}
}}
"""
    with open(theme_dir / "waybar.css", "w") as f:
        f.write(css)
    print(f"Regenerated CSS for {theme_dir.name}")

for theme_dir in THEMES_DIR.iterdir():
    if theme_dir.is_dir():
        regenerate_css(theme_dir)

print("All Waybar CSS files regenerated.")
