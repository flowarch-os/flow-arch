#!/bin/bash
INTENTION_FILE="/tmp/pomodoro_intention"

# Colors (Matching hyprlock theme)
BG="\033[48;2;25;20;20m"    # #191414
FG="\033[38;2;200;200;200m" # #c8c8c8
ACCENT="\033[38;2;100;255;100m" # Green
RESET="\033[0m"

# Setup Terminal
echo -ne "${BG}"
clear
tput civis # Hide cursor

# Dimensions
ROWS=$(tput lines)
COLS=$(tput cols)
CENTER_ROW=$((ROWS / 2))

# Draw Background
for ((i=0; i<ROWS; i++)); do
    printf "%*s\n" "$COLS" " "
done
tput cup 0 0

# UI Drawing Helper
draw_center() {
    local r=$1
    local text="$2"
    local len=${#text}
    # Strip escape codes for length calc? Rough approx ok.
    local col=$(( (COLS - len) / 2 ))
    tput cup $r $col
    echo -ne "$text"
}

# Draw UI
draw_center $((CENTER_ROW - 4)) "${ACCENT}SESSION START${FG}"
draw_center $((CENTER_ROW - 1)) "Enter your intention for the next session:"

# Draw Input Box
BOX_WIDTH=40
BOX_START=$(( (COLS - BOX_WIDTH) / 2 ))
tput cup $((CENTER_ROW + 2)) $BOX_START
echo -ne "\033[48;2;50;50;50m" # Lighter grey input bg
printf "%${BOX_WIDTH}s" " "
echo -ne "${BG}"

# Input Logic
tput cup $((CENTER_ROW + 2)) $((BOX_START + 2))
tput cnorm # Show cursor
echo -ne "${FG}"
read -r intention

# Save
echo "$intention" > "$INTENTION_FILE"

# Fade out / Clear
tput civis
echo -ne "${RESET}"
clear