"""Parse ~/session_logs.jsonl and compute stats used by Dashboard/Journal."""

import json
from datetime import datetime, timedelta
from pathlib import Path

LOG_FILE = Path.home() / "session_logs.jsonl"


def load_logs() -> list[dict]:
    """Return all log entries with a parsed `dt` field, newest first."""
    out = []
    if not LOG_FILE.exists():
        return out
    try:
        for line in LOG_FILE.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = data.get("timestamp") or data.get("date")
            if not ts:
                continue
            try:
                data["dt"] = datetime.fromisoformat(ts)
            except ValueError:
                continue
            out.append(data)
    except OSError as e:
        print(f"[logs] read error: {e}")
    out.sort(key=lambda x: x["dt"], reverse=True)
    return out


def compute_stats(logs: list[dict]) -> dict:
    """Today/week summary used by the Dashboard page."""
    today = datetime.now().date()
    history = {(today - timedelta(days=i)).strftime("%Y-%m-%d"): 0.0 for i in range(7)}

    today_hours = 0.0
    session_count = 0
    rating_sum = 0.0
    total_ratings = 0
    streak = 0

    sorted_logs = sorted(logs, key=lambda x: x["dt"])
    active_start = None

    for data in sorted_logs:
        d_str = data["dt"].strftime("%Y-%m-%d")
        t = data.get("type")
        if t == "login":
            active_start = data["dt"]
            if data["dt"].date() == today:
                session_count += 1
        elif t == "feedback":
            if active_start:
                hrs = (data["dt"] - active_start).total_seconds() / 3600
                if 0 < hrs < 24:
                    if d_str in history:
                        history[d_str] += hrs
                    if data["dt"].date() == today:
                        today_hours += hrs
                active_start = None
            r = data.get("rating")
            if isinstance(r, (int, float)):
                rating_sum += float(r)
                total_ratings += 1

    # streak: consecutive days back from yesterday with at least one feedback.
    feedback_days = {l["dt"].date() for l in logs if l.get("type") == "feedback"}
    cursor = today
    while cursor in feedback_days:
        streak += 1
        cursor -= timedelta(days=1)

    recent = []
    for item in logs[:12]:
        if item.get("type") in ("login", "feedback", "pomodoro_segment"):
            recent.append({
                "dt": item["dt"],
                "type": item.get("type"),
                "goal": item.get("goal", "—"),
                "intention": item.get("intention", ""),
                "rating": item.get("rating"),
            })

    return {
        "today_hours":   today_hours,
        "session_count": session_count,
        "avg_rating":    (rating_sum / total_ratings) if total_ratings else 0.0,
        "history":       history,
        "streak":        streak,
        "recent":        recent,
        "total_sessions": sum(1 for l in logs if l.get("type") == "login"),
    }


def feedback_only(logs: list[dict]) -> list[dict]:
    return [l for l in logs if l.get("type") == "feedback"]
