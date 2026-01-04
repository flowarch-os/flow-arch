#!/bin/bash

# Define options
options="3000K (Very Warm)\n3500K (Warm/Default)\n4500K (Balanced)\n5500K (Light)\n6500K (Daylight/Off)"

# Show menu
selected=$(echo -e "$options" | wofi --dmenu --prompt "Select Screen Temp")

# Exit if cancelled
if [ -z "$selected" ]; then
    exit 0
fi

# Extract temperature value (first word)
temp=${selected%%K*}

# Call the main control script
~/.config/hypr/scripts/blue_light_control.sh set_temp "$temp"
