#!/bin/bash
# force C locale as a fallback to ensure clock loads
export LANG=C
export LC_ALL=C

# Kill existing waybar instances (exact match to avoid killing this script)
pkill -x waybar

# Wait for waybar to exit
while pgrep -x waybar >/dev/null; do sleep 0.1; done

waybar &
