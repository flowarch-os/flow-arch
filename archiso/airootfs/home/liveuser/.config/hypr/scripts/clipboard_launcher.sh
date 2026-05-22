#!/bin/bash
# Toggle the custom clipboard manager. Computes a cursor-anchored monitor-local
# position and hands it to clipboard_manager.py (PySide6+QML on top of cliphist).

WIDTH=540
HEIGHT=660
APP="$HOME/.config/hypr/scripts/clipboard_manager.py"

# 1. Single-instance toggle
if pgrep -f "clipboard_manager.py" >/dev/null; then
    pkill -f "clipboard_manager.py"
    exit 0
fi

# 2. Compute monitor-relative window position centered on cursor
CALC_RESULT=$(python3 - "$WIDTH" "$HEIGHT" <<'PY'
import subprocess, json, sys

w, h = int(sys.argv[1]), int(sys.argv[2])

try:
    monitors = json.loads(subprocess.check_output(["hyprctl", "monitors", "-j"]).decode())
    gx, gy = map(int, subprocess.check_output(["hyprctl", "cursorpos"]).decode().strip().split(","))
except Exception:
    sys.exit(1)

target = None
for m in monitors:
    mx, my, scale = m["x"], m["y"], m["scale"]
    mw, mh = m["width"] / scale, m["height"] / scale
    if mx <= gx < mx + mw and my <= gy < my + mh:
        target = m; break
if not target:
    for m in monitors:
        if m["focused"]:
            target = m; break

if not target:
    print("0 0"); sys.exit(0)

mx, my, scale = target["x"], target["y"], target["scale"]
mw, mh = target["width"] / scale, target["height"] / scale

# Anchor: center the window on the cursor, then clamp inside the monitor with a
# small margin so it doesn't kiss the screen edge.
margin = 8
fx = (gx - mx) - w / 2
fy = (gy - my) - h / 2
fx = max(margin, min(fx, mw - w - margin))
fy = max(margin, min(fy, mh - h - margin))

# Hyprland windows want absolute (global) coords for floating placement.
print(f"{int(mx + fx)} {int(my + fy)}")
PY
)

read -r GX GY <<< "$CALC_RESULT"
[ -z "$GX" ] && GX=100
[ -z "$GY" ] && GY=100

# 3. Launch the app
exec python3 "$APP" --pos "$GX,$GY"
