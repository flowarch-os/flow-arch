#!/bin/bash
# script to change timezone via wofi

# get list of timezones
timezones=$(timedatectl list-timezones)

# show wofi menu
selected=$(echo "$timezones" | wofi --show dmenu --prompt "Select Timezone")

if [ -z "$selected" ]; then
    exit 0
fi

# Try pkexec first (graphical)
if pkexec timedatectl set-timezone "$selected" 2>/dev/null; then
    notify-send "Timezone Changed" "New timezone: $selected"
    exit 0
fi

# Fallback: Open a terminal to ask for password
if command -v kitty >/dev/null; then
     # Use bash -c to wrap the command properly
     kitty -e bash -c "sudo timedatectl set-timezone '$selected'; echo 'Timezone updated. Press Enter to close.'; read"
elif command -v gnome-terminal >/dev/null; then
     gnome-terminal -- bash -c "sudo timedatectl set-timezone '$selected'; echo 'Timezone updated. Press Enter to close.'; read"
else
     notify-send "Error" "Could not find a supported terminal (kitty/gnome-terminal) for password prompt."
fi
