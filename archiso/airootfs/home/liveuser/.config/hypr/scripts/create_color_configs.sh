#!/bin/bash

# Function to write colors file
write_colors() {
    theme=$1
    bg=$2
    fg=$3
    # Approximating border colors from previous logic if not strictly known, 
    # but I'll use the FG as active and a dimmed version for inactive
    
    echo "bg_color='$bg'" > ~/.config/hypr/themes/$theme/colors
    echo "fg_color='$fg'" >> ~/.config/hypr/themes/$theme/colors
    # reusing logic from before: active is usually FG, inactive is mixed
    echo "active_border='$fg'" >> ~/.config/hypr/themes/$theme/colors
    echo "inactive_border='$bg'" >> ~/.config/hypr/themes/$theme/colors
}

write_colors "blue" "000030" "00aaff"
write_colors "gold" "222200" "ffd700"
write_colors "green" "001100" "00ffaa"
write_colors "purple" "110011" "aa00ff"
write_colors "red" "330000" "ff0000"
write_colors "orange" "331a00" "ff8800"
write_colors "cyan" "003333" "00ffff"
write_colors "magenta" "330033" "ff00ff"
write_colors "teal" "003322" "00ffaa"
