"""Alarm tool: set, list, cancel alarms."""

import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from gerty.config import ALARMS_FILE, DATA_DIR
from gerty.tools.base import Tool
from gerty.tools.number_words import normalize_time_words


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
    """Parse time from natural language (e.g. '7:30 am', '7.32pm', '7 30', '7am', 'eleven oh five')."""
    text = normalize_time_words(text).lower().strip()
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

    # Match "6.32pm" or "7.30 am" (dot as separator, common in speech/STT)
    m = re.search(r"(\d{1,2})\.(\d{2})\s*(am|pm)?", text)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= mi <= 59:
            if m.group(3) == "pm" and h < 12:
                h += 12
            elif m.group(3) == "am" and h == 12:
                h = 0
            return now.replace(hour=h, minute=mi, second=0, microsecond=0)

    # Match "7 am" or "7am" or "7 pm" (hour must be 1-12; avoid matching "30 am" in "7 30 am")
    m = re.search(r"(\d{1,2})\s*(am|pm)\b", text)
    if m:
        h = int(m.group(1))
        if 1 <= h <= 12:  # Valid hour for am/pm
            if m.group(2) == "pm" and h < 12:
                h += 12
            elif m.group(2) == "am" and h == 12:
                h = 0
            return now.replace(hour=h, minute=0, second=0, microsecond=0)

    # Match "7 30" or "7 30 pm" (hour minute, with optional am/pm)
    nums = re.findall(r"\b(\d{1,2})\b", text)
    has_pm = "pm" in text
    has_am = "am" in text
    if len(nums) >= 2:
        h, mi = int(nums[0]), int(nums[1])
        if 0 <= h <= 23 and 0 <= mi <= 59:
            if has_pm and h < 12:
                h += 12
            elif has_am and h == 12:
                h = 0
            return now.replace(hour=h, minute=mi, second=0, microsecond=0)
    if len(nums) == 1:
        h = int(nums[0])
        if 0 <= h <= 23:
            if has_pm and h < 12:
                h += 12
            elif has_am and h == 12:
                h = 0
            return now.replace(hour=h, minute=0, second=0, microsecond=0)

    return None


def _parse_alarm_label(message: str) -> str:
    """Extract optional alarm label (e.g. 'set alarm for 7am for workout' -> 'workout')."""
    m = re.search(r"for\s+([a-zA-Z][\w\s]*?)(?:\s+please|\s*)$", message, re.I)
    if m:
        return m.group(1).strip()[:50]
    return "Alarm"


def _parse_recurring(message: str) -> str | None:
    """Extract recurring mode: 'daily' if user said daily/repeat/repeating, else None."""
    lower = message.lower()
    if any(w in lower for w in ("daily", "every day", "repeat", "repeating", "recurring")):
        return "daily"
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
        if "list" in lower or "show" in lower or ("what" in lower and "alarm" in lower):
            alarms = self._get_pending_alarms()
            if not alarms:
                return "You have no alarms set."
            lines = []
            for a in alarms:
                daily = " (daily)" if a.get("recurring") == "daily" else ""
                lines.append(f"• {a['time']} - {a.get('label', 'Alarm')}{daily}")
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
            label = _parse_alarm_label(message)
            recurring = _parse_recurring(message)
            alarms = _load_alarms()
            alarms.append({
                "id": str(uuid.uuid4()),
                "datetime": alarm_time.isoformat(),
                "time": alarm_time.strftime("%I:%M %p"),
                "label": label,
                "recurring": recurring,
            })
            _save_alarms(alarms)
            label_part = f" ({label})" if label != "Alarm" else ""
            recurring_part = " daily" if recurring else ""
            return f"Alarm set for {alarm_time.strftime('%I:%M %p')}{recurring_part}{label_part}."
        return "I couldn't understand the time. Try: set alarm for 7:30 am"

    def _get_pending_alarms(self) -> list[dict]:
        alarms = _load_alarms()
        now = datetime.now()
        return [
            {**a, "time": datetime.fromisoformat(a["datetime"]).strftime("%I:%M %p")}
            for a in alarms
            if datetime.fromisoformat(a["datetime"]) > now
        ]


def add_alarm(time_str: str, label: str = "Alarm", recurring: str | None = None) -> dict:
    """Add an alarm programmatically. time_str: '7:30', '7:30 am', '19:30'.
    recurring: 'daily' for repeat every day, None for one-time. Returns created alarm dict."""
    alarm_time = _parse_alarm_time(time_str.strip())
    if not alarm_time:
        raise ValueError("Could not parse time. Use format like 7:30, 7:30 am, or 19:30")
    if alarm_time <= datetime.now():
        alarm_time = alarm_time + timedelta(days=1)
    alarms = _load_alarms()
    alarm = {
        "id": str(uuid.uuid4()),
        "datetime": alarm_time.isoformat(),
        "time": alarm_time.strftime("%I:%M %p"),
        "label": (label or "Alarm").strip()[:50] or "Alarm",
        "recurring": "daily" if recurring == "daily" else None,
    }
    alarms.append(alarm)
    _save_alarms(alarms)
    return alarm


def cancel_all_alarms() -> int:
    """Cancel all alarms. Returns count removed."""
    alarms = _load_alarms()
    count = len(alarms)
    _save_alarms([])
    return count


def cancel_alarm(alarm_id: str) -> bool:
    """Cancel a single alarm by id (or datetime for legacy alarms). Returns True if removed."""
    alarms = _load_alarms()
    for i, a in enumerate(alarms):
        if a.get("id") == alarm_id or a.get("datetime") == alarm_id:
            alarms.pop(i)
            _save_alarms(alarms)
            return True
    return False


def reschedule_daily_alarm(alarm_id: str) -> bool:
    """Reschedule a daily alarm to tomorrow at the same time. Returns True if updated."""
    alarms = _load_alarms()
    for a in alarms:
        if a.get("id") == alarm_id or a.get("datetime") == alarm_id:
            dt = datetime.fromisoformat(a["datetime"])
            next_dt = dt + timedelta(days=1)
            a["datetime"] = next_dt.isoformat()
            a["time"] = next_dt.strftime("%I:%M %p")
            _save_alarms(alarms)
            return True
    return False


def toggle_alarm_recurring(alarm_id: str) -> bool | None:
    """Toggle alarm between daily and one-time. Returns new state: 'daily' or None, or None if not found."""
    alarms = _load_alarms()
    for a in alarms:
        if a.get("id") == alarm_id or a.get("datetime") == alarm_id:
            current = a.get("recurring")
            new_val = None if current == "daily" else "daily"
            a["recurring"] = new_val
            _save_alarms(alarms)
            return new_val
    return None


def get_pending_alarms(include_sounding_id: str | None = None) -> list[dict]:
    """Return alarms for display: future alarms + currently sounding (even if past).
    include_sounding_id: if set, include this alarm in the list with sounding=True even when past.
    Alarm stays in list until user cancels (voice or UI)."""
    alarms = _load_alarms()
    now = datetime.now()
    result = []
    for a in alarms:
        dt = datetime.fromisoformat(a["datetime"])
        aid = a.get("id") or a["datetime"]
        is_future = dt > now
        is_sounding = bool(include_sounding_id and aid == include_sounding_id)
        if is_future or is_sounding:
            result.append({
                **a,
                "id": aid,
                "time": dt.strftime("%I:%M %p"),
                "sounding": is_sounding,
            })
    return result


def get_pending_alarms_for_trigger() -> list[dict]:
    """Return alarms that are due (for background trigger loop). Does NOT remove them."""
    alarms = _load_alarms()
    now = datetime.now()
    due = [a for a in alarms if datetime.fromisoformat(a["datetime"]) <= now]
    return due
