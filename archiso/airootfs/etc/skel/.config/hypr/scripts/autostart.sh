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

# Start Wallpaper Daemon
hyprpaper &

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

# Launch Calamares Installer automatically (ONLY for liveuser)
if [ "$USER" = "liveuser" ]; then
    (sleep 3 && /usr/local/bin/calamares-wayland) &
fi
