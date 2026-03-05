"""Alarm tool: set, list, cancel alarms."""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from gerty.config import ALARMS_FILE, DATA_DIR
from gerty.tools.base import Tool


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_alarms() -> list[dict]:
    _ensure_data_dir()
    if not ALARMS_FILE.exists():
        return []
    with open(ALARMS_FILE) as f:
        return json.load(f)


def _save_alarms(alarms: list[dict]):
    _ensure_data_dir()
    with open(ALARMS_FILE, "w") as f:
        json.dump(alarms, f, indent=2)


def _parse_alarm_time(text: str) -> datetime | None:
    """Parse time from natural language (e.g. '7:30 am', '7 30', '7am')."""
    text = text.lower().strip()
    now = datetime.now()

    # Match "7:30" or "7:30 am" or "7:30pm"
    m = re.search(r"(\d{1,2}):(\d{2})\s*(am|pm)?", text)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if m.group(3) == "pm" and h < 12:
            h += 12
        elif m.group(3) == "am" and h == 12:
            h = 0
        return now.replace(hour=h, minute=mi, second=0, microsecond=0)

    # Match "7 am" or "7am" or "7 pm"
    m = re.search(r"(\d{1,2})\s*(am|pm)\b", text)
    if m:
        h = int(m.group(1))
        if m.group(2) == "pm" and h < 12:
            h += 12
        elif m.group(2) == "am" and h == 12:
            h = 0
        return now.replace(hour=h, minute=0, second=0, microsecond=0)

    # Match "7 30" (hour minute)
    nums = re.findall(r"\b(\d{1,2})\b", text)
    if len(nums) >= 2:
        h, mi = int(nums[0]), int(nums[1])
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return now.replace(hour=h, minute=mi, second=0, microsecond=0)
    if len(nums) == 1:
        h = int(nums[0])
        if 0 <= h <= 23:
            return now.replace(hour=h, minute=0, second=0, microsecond=0)

    return None


class AlarmsTool(Tool):
    """Set, list, and cancel alarms."""

    @property
    def name(self) -> str:
        return "alarm"

    @property
    def description(self) -> str:
        return "Set, list, or cancel alarms"

    def execute(self, intent: str, message: str) -> str:
        lower = message.lower()

        # List alarms
        if "list" in lower or "show" in lower or "what" in lower and "alarm" in lower:
            alarms = self._get_pending_alarms()
            if not alarms:
                return "You have no alarms set."
            lines = [f"• {a['time']} - {a.get('label', 'Alarm')}" for a in alarms]
            return "Your alarms:\n" + "\n".join(lines)

        # Cancel alarms - clear all future alarms
        if "cancel" in lower or "remove" in lower or "delete" in lower or "stop" in lower:
            alarms = _load_alarms()
            count = len(alarms)
            _save_alarms([])
            if count:
                return f"Removed {count} alarm(s)."
            return "No alarms to remove."

        # Set alarm
        alarm_time = _parse_alarm_time(message)
        if alarm_time:
            if alarm_time <= datetime.now():
                alarm_time = alarm_time + timedelta(days=1)
            alarms = _load_alarms()
            alarms.append({
                "datetime": alarm_time.isoformat(),
                "time": alarm_time.strftime("%I:%M %p"),
                "label": "Alarm",
            })
            _save_alarms(alarms)
            return f"Alarm set for {alarm_time.strftime('%I:%M %p')}."
        return "I couldn't understand the time. Try: set alarm for 7:30 am"

    def _get_pending_alarms(self) -> list[dict]:
        alarms = _load_alarms()
        now = datetime.now()
        return [
            {**a, "time": datetime.fromisoformat(a["datetime"]).strftime("%I:%M %p")}
            for a in alarms
            if datetime.fromisoformat(a["datetime"]) > now
        ]


def cancel_all_alarms() -> int:
    """Cancel all alarms. Returns count removed."""
    alarms = _load_alarms()
    count = len(alarms)
    _save_alarms([])
    return count


def get_pending_alarms() -> list[dict]:
    """Return all pending (future) alarms for display."""
    alarms = _load_alarms()
    now = datetime.now()
    return [
        {**a, "time": datetime.fromisoformat(a["datetime"]).strftime("%I:%M %p")}
        for a in alarms
        if datetime.fromisoformat(a["datetime"]) > now
    ]


def get_pending_alarms_for_trigger() -> list[dict]:
    """Return alarms that are due (for background trigger loop)."""
    alarms = _load_alarms()
    now = datetime.now()
    due = []
    remaining = []
    for a in alarms:
        dt = datetime.fromisoformat(a["datetime"])
        if dt <= now:
            due.append(a)
        else:
            remaining.append(a)
    if due:
        _save_alarms(remaining)
    return due
