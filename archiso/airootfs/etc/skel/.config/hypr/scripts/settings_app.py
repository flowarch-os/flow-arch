#!/usr/bin/env python3
"""Entry-point for the Hyprland settings app. The real code lives in
settings_app_lib/. This shim keeps the existing waybar / launcher paths working.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from settings_app_lib.app import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run())
