#!/bin/bash
# Inhibits systemd-logind from handling the power key
# This allows Hyprland to handle the XF86PowerOff key event instead.

echo "Starting Power Key Inhibitor..."
systemd-inhibit \
    --what=handle-power-key \
    --who="Hyprland Session" \
    --why="Allow custom shutdown script via Hyprland keybind" \
    --mode=block \
    sleep infinity
