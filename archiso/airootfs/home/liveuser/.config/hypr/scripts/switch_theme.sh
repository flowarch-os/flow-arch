#!/bin/bash
# switches the current theme by updating symlinks and reloading apps

theme=$1

if [ -z "$theme" ]; then
    echo "usage: $0 <theme_name>"
    exit 1
fi

# paths
config_dir="$HOME/.config"
hypr_dir="$config_dir/hypr"
themes_dir="$hypr_dir/themes"
waybar_dir="$config_dir/waybar"
wofi_dir="$config_dir/wofi"

# check if theme exists
if [ ! -d "$themes_dir/$theme" ]; then
    echo "error: theme '$theme' not found in $themes_dir"
    exit 1
fi

echo "switching to theme: $theme..."

# load theme colors
if [ -f "$themes_dir/$theme/colors" ]; then
    source "$themes_dir/$theme/colors"
    # apply to system apps (gtk, vscode)
    python3 "$HOME/.config/hypr/scripts/apply_app_theme.py" "$bg_color" "$fg_color"
else
    echo "warning: no colors file found for theme $theme"
fi

# 1. link hyprland colors
ln -sf "$themes_dir/$theme/hypr.conf" "$hypr_dir/theme.conf"

# 2. link waybar style
ln -sf "$themes_dir/$theme/waybar.css" "$waybar_dir/style.css"
# restart waybar via wrapper to ensure locale is correct
"$HOME/.config/hypr/scripts/waybar_wrapper.sh" > /dev/null 2>&1

# 3. link wofi style
ln -sf "$themes_dir/$theme/wofi.css" "$wofi_dir/style.css"

# 4. update wallpaper
wallpaper="$themes_dir/$theme/wallpaper.png"

# check for wallpaper daemon
if pgrep -x "swww-daemon" > /dev/null; then
    # swww: simple fade, very fast
    swww img "$wallpaper" --transition-type simple --transition-step 200
elif pgrep -x "hyprpaper" > /dev/null; then
    # hyprpaper: use ipc for instant switch
    hyprctl hyprpaper preload "$wallpaper"
    hyprctl hyprpaper wallpaper ",$wallpaper"
    # optional: unload unused wallpapers to save ram
    hyprctl hyprpaper unload all
elif command -v hyprpaper > /dev/null; then
    # hyprpaper not running, start it
    echo "preload = $wallpaper" > "$hypr_dir/hyprpaper.conf"
    echo "wallpaper = ,$wallpaper" >> "$hypr_dir/hyprpaper.conf"
    hyprpaper & > /dev/null 2>&1
else
    echo "warning: no wallpaper daemon found"
fi

# 5. reload hyprland to apply new colors
hyprctl reload

echo "done!"
