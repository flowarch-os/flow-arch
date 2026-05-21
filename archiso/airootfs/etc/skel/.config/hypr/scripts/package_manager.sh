#!/bin/bash
# Toggle launcher for the GTK4 package manager.

if pgrep -f "package_manager.py" >/dev/null; then
    pkill -f "package_manager.py"
    exit 0
fi

exec python3 "$HOME/.config/hypr/scripts/package_manager.py"
