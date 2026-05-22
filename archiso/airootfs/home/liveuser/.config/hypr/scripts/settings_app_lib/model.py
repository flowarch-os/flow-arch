"""settings.json model + v1→v2 migration.

v2 shape:
  {
    "version": 2,
    "focus":    { goals, goal_themes, pomodoro, shutdown_feedback },
    "filters":  { ad_blocking, global_blacklist, keyword_blacklist,
                  goal_filters, visual_guard{enabled,sensitivity},
                  media_blackout{enabled,allowlist} },
    "schedule": { calendar_events, tasks, bedtime{start,end} },
    "system":   { blue_light{enabled,day_temp,night_temp,brightness},
                  active_theme }
  }
"""

import json
import os
import shutil
from pathlib import Path
from typing import Any

SETTINGS_FILE = Path.home() / ".config/hypr/settings.json"
BACKUP_FILE = SETTINGS_FILE.with_suffix(".json.v1.bak")
SCHEMA_VERSION = 2


def _defaults() -> dict:
    return {
        "version": SCHEMA_VERSION,
        "focus": {
            "goals": ["Work", "Study"],
            "goal_themes": {},
            "pomodoro": {
                "work_duration": 25,
                "short_break": 5,
                "long_break": 20,
                "intention_popup": True,
            },
            "shutdown_feedback": True,
        },
        "filters": {
            "ad_blocking": False,
            "global_blacklist": [],
            "keyword_blacklist": [],
            "goal_filters": {},
            "visual_guard": {"enabled": False, "sensitivity": 50},
            "media_blackout": {
                "enabled": False,
                "allowlist": ["google.com", "drive.google.com", "classroom.google.com"],
            },
        },
        "schedule": {
            "calendar_events": [],
            "tasks": [],
            "bedtime": {"start": "23:00", "end": "05:00"},
        },
        "system": {
            "blue_light": {
                "enabled": False,
                "day_temp": 6500,
                "night_temp": 3500,
                "brightness": 1.0,
            },
            "active_theme": "blue",
        },
    }


def _migrate_v1(old: dict) -> dict:
    """Reshape flat v1 settings into v2 namespaces. Preserves all data."""
    new = _defaults()

    if "goals" in old:           new["focus"]["goals"] = old["goals"]
    if "goal_themes" in old:     new["focus"]["goal_themes"] = old["goal_themes"]
    if "pomodoro" in old and isinstance(old["pomodoro"], dict):
        new["focus"]["pomodoro"].update(old["pomodoro"])
    if "shutdown_feedback" in old:
        new["focus"]["shutdown_feedback"] = bool(old["shutdown_feedback"])

    if "ad_blocking" in old:        new["filters"]["ad_blocking"] = bool(old["ad_blocking"])
    if "global_blacklist" in old:   new["filters"]["global_blacklist"] = list(old["global_blacklist"])
    if "keyword_blacklist" in old:  new["filters"]["keyword_blacklist"] = list(old["keyword_blacklist"])
    if "filters" in old and isinstance(old["filters"], dict):
        new["filters"]["goal_filters"] = old["filters"]
    new["filters"]["visual_guard"] = {
        "enabled": bool(old.get("visual_guard", False)),
        "sensitivity": int(old.get("visual_sensitivity", 50)),
    }
    new["filters"]["media_blackout"] = {
        "enabled": bool(old.get("media_blackout", False)),
        "allowlist": list(old.get("media_allowlist",
            ["google.com", "drive.google.com", "classroom.google.com"])),
    }

    if "calendar_events" in old: new["schedule"]["calendar_events"] = old["calendar_events"]
    if "tasks" in old:           new["schedule"]["tasks"] = old["tasks"]
    new["schedule"]["bedtime"] = {
        "start": old.get("bedtime_start", "23:00"),
        "end":   old.get("bedtime_end",   "05:00"),
    }

    return new


def _deep_merge_defaults(data: dict, defaults: dict) -> dict:
    """Fill missing keys from defaults without overwriting existing ones."""
    for k, dv in defaults.items():
        if k not in data:
            data[k] = dv
        elif isinstance(dv, dict) and isinstance(data[k], dict):
            _deep_merge_defaults(data[k], dv)
    return data


def load() -> dict:
    """Load settings, migrating v1→v2 once and writing the result back."""
    if not SETTINGS_FILE.exists():
        return _defaults()

    try:
        raw = json.loads(SETTINGS_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"[settings] could not read {SETTINGS_FILE}: {e}; using defaults")
        return _defaults()

    if not isinstance(raw, dict):
        return _defaults()

    if raw.get("version") == SCHEMA_VERSION:
        return _deep_merge_defaults(raw, _defaults())

    # v1 (or unversioned) — migrate.
    try:
        if not BACKUP_FILE.exists():
            shutil.copy2(SETTINGS_FILE, BACKUP_FILE)
    except OSError:
        pass

    migrated = _migrate_v1(raw)
    save(migrated)
    return migrated


def save(data: dict) -> None:
    """Write atomically (tmp + rename)."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, SETTINGS_FILE)


# --------- typed accessors (used by app + consumer scripts) ---------

def goals(s: dict) -> list[str]:               return s.get("focus", {}).get("goals", [])
def goal_themes(s: dict) -> dict:              return s.get("focus", {}).get("goal_themes", {})
def pomodoro(s: dict) -> dict:                 return s.get("focus", {}).get("pomodoro", {})
def shutdown_feedback(s: dict) -> bool:        return s.get("focus", {}).get("shutdown_feedback", True)

def ad_blocking(s: dict) -> bool:              return s.get("filters", {}).get("ad_blocking", False)
def global_blacklist(s: dict) -> list[str]:    return s.get("filters", {}).get("global_blacklist", [])
def keyword_blacklist(s: dict) -> list[str]:   return s.get("filters", {}).get("keyword_blacklist", [])
def goal_filters(s: dict, goal: str | None = None) -> Any:
    f = s.get("filters", {}).get("goal_filters", {})
    return f.get(goal, []) if goal else f
def visual_guard(s: dict) -> dict:             return s.get("filters", {}).get("visual_guard", {"enabled": False, "sensitivity": 50})
def media_blackout(s: dict) -> dict:           return s.get("filters", {}).get("media_blackout", {"enabled": False, "allowlist": []})

def calendar_events(s: dict) -> list[dict]:    return s.get("schedule", {}).get("calendar_events", [])
def tasks(s: dict) -> list[dict]:              return s.get("schedule", {}).get("tasks", [])
def bedtime(s: dict) -> dict:                  return s.get("schedule", {}).get("bedtime", {"start": "23:00", "end": "05:00"})

def blue_light(s: dict) -> dict:               return s.get("system", {}).get("blue_light", {})
def active_theme(s: dict) -> str:              return s.get("system", {}).get("active_theme", "blue")


def clean_and_extract_domains(text: str) -> list[str]:
    """Parse a comma-separated user input into a list of bare domain strings."""
    out = []
    for raw in text.split(","):
        d = raw.strip()
        if not d:
            continue
        if "://" in d:
            d = d.split("://", 1)[1]
        if "/" in d:
            d = d.split("/", 1)[0]
        if d.startswith("www."):
            d = d[4:]
        if ":" in d:
            d = d.split(":", 1)[0]
        if d:
            out.append(d)
    return out
