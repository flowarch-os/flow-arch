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

# 4. swap kitty palette + live-reload running kitty windows
if [ -f "$themes_dir/$theme/kitty.conf" ]; then
    ln -sf "$themes_dir/$theme/kitty.conf" "$HOME/.config/kitty/colors.conf"
    # SIGUSR1 tells kitty to re-read its config (palette is via `include colors.conf`)
    pkill -SIGUSR1 -x kitty 2>/dev/null || true
fi

# 5. render hyprlock from the theme template (colors + a wallpaper image)
if [ -x "$hypr_dir/scripts/render_hyprlock.sh" ]; then
    "$hypr_dir/scripts/render_hyprlock.sh" "$theme" >/dev/null
fi

# 6. cursor theme
if [ -f "$themes_dir/$theme/cursor" ]; then
    cursor_theme=$(cat "$themes_dir/$theme/cursor")
    # Apply via gsettings (covers GTK + many GUI apps)
    gsettings set org.gnome.desktop.interface cursor-theme "$cursor_theme" 2>/dev/null || true
    # Persist via xsettingsd for X11/legacy apps; SIGHUP to reload
    xsettings_conf="$HOME/.config/xsettingsd/xsettingsd.conf"
    if [ -f "$xsettings_conf" ]; then
        sed -i "s|^Gtk/CursorThemeName .*|Gtk/CursorThemeName \"$cursor_theme\"|" "$xsettings_conf"
        pkill -HUP -x xsettingsd 2>/dev/null || true
    fi
    # Tell Hyprland to pick up the new cursor for newly-spawned clients
    hyprctl setcursor "$cursor_theme" 32 >/dev/null 2>&1 || true
fi

# 7. update wallpaper (dispatcher reads theme manifest and picks engine)
"$hypr_dir/scripts/wallpaper_engine.sh" "$theme"

# 8. reload hyprland to apply new colors + decoration vars
hyprctl reload

echo "done!"
