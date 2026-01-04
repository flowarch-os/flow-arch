#!/bin/bash
# Get the default browser desktop file (e.g., google-chrome.desktop)
BROWSER_DESKTOP=$(xdg-settings get default-web-browser)

if [ -n "$BROWSER_DESKTOP" ]; then
    # gtk-launch takes the desktop file name (with or without .desktop)
    # It launches the application as if clicked in a menu
    gtk-launch "$BROWSER_DESKTOP"
else
    # Fallback if xdg-settings fails
    xdg-open https://www.google.com
fi
