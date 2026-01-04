#!/bin/bash

# Configuration
WIDTH=400
HEIGHT=500

# 1. Toggle Logic: If running, close it and exit (Single instance)
if pgrep -f "wofi.*cliphist"; then
    pkill -f "wofi.*cliphist"
    exit 0
fi

# 2. Calculate Monitor-Relative Coordinates
# We need to know:
# - Which monitor has the cursor?
# - What are the cursor's X,Y relative to THAT monitor's top-left?
# - Output format: "X_POS Y_POS MONITOR_NAME"
CALC_RESULT=$(python3 -c '
import subprocess, json, sys, math

w, h = int(sys.argv[1]), int(sys.argv[2])

try:
    # Get Monitor Info
    monitors = json.loads(subprocess.check_output(["hyprctl", "monitors", "-j"]).decode())
    
    # Get Global Cursor Position
    cursor_out = subprocess.check_output(["hyprctl", "cursorpos"]).decode().strip()
    gx, gy = map(int, cursor_out.split(","))
except:
    sys.exit(1)

target_mon = None

# Find the monitor containing the cursor
for m in monitors:
    # In Hyprland, x/y are logical position. 
    # width/height are physical pixels, so divide by scale for logical size.
    mx = m["x"]
    my = m["y"]
    scale = m["scale"]
    mw = m["width"] / scale
    mh = m["height"] / scale
    
    if mx <= gx < mx + mw and my <= gy < my + mh:
        target_mon = m
        break

# Fallback if cursor is somehow off-screen (use focused monitor)
if not target_mon:
    for m in monitors:
        if m["focused"]:
            target_mon = m
            break

if target_mon:
    # Monitor details
    mx = target_mon["x"]
    my = target_mon["y"]
    scale = target_mon["scale"]
    mw = target_mon["width"] / scale
    mh = target_mon["height"] / scale
    name = target_mon["name"] # Use name or ID for wofi --monitor

    # Calculate Relative Coordinates (Cursor Global - Monitor Origin)
    rel_x = gx - mx
    rel_y = gy - my

    # Center the window around the cursor (still relative to monitor)
    final_x = rel_x - (w / 2)
    final_y = rel_y - (h / 2)

    # Clamp to ensure window stays inside the monitor
    final_x = max(0, min(final_x, mw - w))
    final_y = max(0, min(final_y, mh - h))

    # Wofi expects integers
    print(f"{int(final_x)} {int(final_y)} {name}")
else:
    print("0 0")
' "$WIDTH" "$HEIGHT")

# Read the results
read -r X_POS Y_POS MONITOR_NAME <<< "$CALC_RESULT"

# 3. Launch Wofi
# --location 1: Top-Left anchor (Crucial! Otherwise X/Y are offsets from center)
# --monitor: Forces it to the correct screen
# --x, --y: The calculated relative coordinates
WOFI_ARGS="--dmenu --name cliphist --width $WIDTH --height $HEIGHT --location 1 --x $X_POS --y $Y_POS --monitor $MONITOR_NAME --cache-file /dev/null --hide-scroll"

# Define special actions
DEL_MODE="[   Delete Mode ]"
CLEAR_ALL="[   Clear History ]"

HISTORY=$(cliphist list)
SELECTION=$(echo -e "$HISTORY\n$DEL_MODE\n$CLEAR_ALL" | wofi $WOFI_ARGS --prompt "Clipboard")

if [ -n "$SELECTION" ]; then
    case "$SELECTION" in
        "$DEL_MODE")
            DEL_SELECTION=$(cliphist list | wofi $WOFI_ARGS --prompt "DELETE ENTRY")
            [ -n "$DEL_SELECTION" ] && echo "$DEL_SELECTION" | cliphist delete
            ;;
        "$CLEAR_ALL")
            CONFIRM=$(echo -e "No\nYes" | wofi $WOFI_ARGS --prompt "Clear ALL history?" --lines 2 --height 150)
            [ "$CONFIRM" == "Yes" ] && cliphist wipe
            ;;
        *)
            echo "$SELECTION" | cliphist decode | wl-copy
            ;; 
    esac
fi
