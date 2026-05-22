#!/bin/bash

# Wait for Hyprland to fully initialize
sleep 1

# Kill potentially conflicting instances
pkill -x hyprpolkitagent
pkill -x hyprpaper
pkill wl-paste
pkill cliphist
# Ensure audio services are running (restart to be safe)
systemctl --user restart pipewire wireplumber

# Start Power Key Inhibitor (Prevents immediate shutdown on power button press)
~/.config/hypr/scripts/inhibit_power.sh &

# Start Polkit Agent (Critical for sudo/pkexec GUI prompts)
/usr/lib/hyprpolkitagent/hyprpolkitagent &

# Start Wallpaper Engine (reads active theme's wallpaper.conf manifest and
# launches swww / mpvpaper / hyprpaper as appropriate; falls back to static
# hyprpaper if dispatcher fails).
{
    active_theme=$(basename "$(dirname "$(readlink -f ~/.config/hypr/theme.conf)")" 2>/dev/null)
    if [ -n "$active_theme" ] && [ -x ~/.config/hypr/scripts/wallpaper_engine.sh ]; then
        ~/.config/hypr/scripts/wallpaper_engine.sh "$active_theme" || hyprpaper &
    else
        hyprpaper &
    fi
} &

# Start Idle Daemon
hypridle &

# Start Clipboard Manager
wl-paste --type text --watch cliphist store &
wl-paste --type image --watch cliphist store &

# Start Thunar Daemon
thunar --daemon &

# Start Waybar (using wrapper for locale fix)
~/.config/hypr/scripts/waybar_wrapper.sh &

# Start System Tray Applets
nm-applet --indicator &
blueman-applet &

# Start Session Manager (Delayed to ensure services are ready)
(sleep 1 && ~/.config/hypr/scripts/session_manager.py) &
