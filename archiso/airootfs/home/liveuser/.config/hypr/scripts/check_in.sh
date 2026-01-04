#!/bin/bash
GOAL="$1"
INTENTION_FILE="/tmp/pomodoro_intention"
CURRENT_INTENTION=$(cat "$INTENTION_FILE" 2>/dev/null || echo "Focus")

# Colors
BG="\033[48;2;25;20;20m"
FG="\033[38;2;200;200;200m"
ACCENT="\033[38;2;100;255;100m"
WARN="\033[38;2;255;100;100m"
RESET="\033[0m"

echo -ne "${BG}"
clear
tput civis

ROWS=$(tput lines)
COLS=$(tput cols)
CENTER_ROW=$((ROWS / 2))

draw_center() {
    local r=$1
    local text="$2"
    local len=${#text}
    local col=$(( (COLS - len) / 2 ))
    tput cup $r $col
    echo -ne "$text"
}

# Display
draw_center $((CENTER_ROW - 4)) "${ACCENT}SESSION CHECK-IN${FG}"
draw_center $((CENTER_ROW - 2)) "Main Goal: ${GOAL}"
draw_center $((CENTER_ROW - 1)) "Last Task: ${CURRENT_INTENTION}"
draw_center $((CENTER_ROW + 1)) "Type new sub-task or wait to continue..."

# Timer & Input Loop
tput cup $((CENTER_ROW + 3)) 0
echo -ne "${WARN}"

# We use read with timeout. 
# Visual countdown is hard with blocking read in bash without losing chars.
# Simpler approach: 10s timeout on read.
draw_center $((CENTER_ROW + 3)) "Auto-continuing in 10s..."
tput cup $((CENTER_ROW + 5)) $(( (COLS - 40) / 2 ))
echo -ne "${FG}> "
tput cnorm

if read -t 10 -r new_input; then
    if [ -z "$new_input" ]; then
        # Empty enter -> Continue
        echo "$CURRENT_INTENTION" > "$INTENTION_FILE"
    else
        # New input
        echo "$new_input" > "$INTENTION_FILE"
    fi
else
    # Timeout -> Continue
    echo "$CURRENT_INTENTION" > "$INTENTION_FILE"
fi

tput civis
echo -ne "${BG}"
clear
