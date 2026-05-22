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

    # RGB tuples for both colors so we can mix alphas in the template
    bg_r, bg_g, bg_b = int(bg[:2], 16), int(bg[2:4], 16), int(bg[4:], 16)
    fg_r, fg_g, fg_b = int(fg[:2], 16), int(fg[2:4], 16), int(fg[4:], 16)

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
    background: rgba({bg_r}, {bg_g}, {bg_b}, 0.8);
    color: #ffffff;
    border: 1px solid rgba({fg_r}, {fg_g}, {fg_b}, 0.35);
    border-radius: 12px;
    margin: 6px 10px 0 10px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
}}

#workspaces {{
    margin: 0 4px;
}}

#workspaces button {{
    padding: 0 9px;
    margin: 3px 2px;
    color: #ffffff;
    background: transparent;
    border-radius: 8px;
    transition: background 150ms ease, color 150ms ease;
}}

#workspaces button.active {{
    color: #{fg};
    background: rgba({fg_r}, {fg_g}, {fg_b}, 0.18);
}}

#workspaces button:hover {{
    background: rgba({fg_r}, {fg_g}, {fg_b}, 0.10);
    color: #ffffff;
}}

#clock,
#custom-clock,
#custom-timer,
#custom-gammastep,
#custom-caffeine,
#custom-settings,
#battery,
#cpu,
#memory,
#network,
#pulseaudio,
#power-profiles-daemon,
#mpris,
#tray {{
    padding: 0 8px;
    margin: 3px 2px;
    background-color: transparent;
    color: #ffffff;
    border-radius: 8px;
    transition: background 150ms ease;
}}

#clock,
#custom-clock {{
    color: #{fg};
    font-weight: bold;
    margin-right: 14px;
    margin-left: 6px;
}}

#tray {{
    padding: 0 6px;
}}

#custom-settings {{
    color: #{fg};
    margin-right: 4px;
}}

#battery.charging {{
    color: #00ff88;
}}

#battery.warning:not(.charging) {{
    color: #ffaa00;
}}

#battery.critical:not(.charging) {{
    color: #ff5555;
    animation-name: pulse;
    animation-duration: 1s;
    animation-timing-function: ease-in-out;
    animation-iteration-count: infinite;
    animation-direction: alternate;
}}

@keyframes pulse {{
    to {{
        opacity: 0.4;
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
