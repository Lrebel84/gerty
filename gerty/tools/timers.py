"""Timer tool: countdown timers."""

import logging
import re
import threading
import time
import uuid
from typing import Callable

from gerty.llm.router import parse_timer_duration
from gerty.tools.number_words import normalize_time_words

logger = logging.getLogger(__name__)
from gerty.tools.base import Tool

# In-memory active timers: id -> (Timer, duration_sec, start_time, label)
_active_timers: dict[str, tuple[threading.Timer, int, float, str]] = {}
_timer_callbacks: list[Callable[[str, int], None]] = []  # (label, duration_sec)


def _notify_timer_done(label: str, duration_sec: int):
    for cb in _timer_callbacks:
        try:
            cb(label, duration_sec)
        except Exception as e:
            logger.debug("Timer callback failed: %s", e)


def register_timer_callback(cb: Callable[[str, int], None]):
    """Register callback for when a timer completes."""
    _timer_callbacks.append(cb)


def get_active_timers() -> list[dict]:
    """Return active timers with id, label, remaining seconds."""
    now = time.time()
    result = []
    for timer_id, (_, duration_sec, start_time, label) in _active_timers.items():
        remaining = max(0, int(duration_sec - (now - start_time)))
        result.append({
            "id": timer_id,
            "label": label,
            "remaining_sec": remaining,
            "duration_sec": duration_sec,
        })
    return result


def add_timer(duration_sec: int, label: str = "Timer") -> dict:
    """Add a timer programmatically. Returns {id, label, duration_sec}."""
    if duration_sec <= 0:
        raise ValueError("duration_sec must be positive")
    timer_id = str(uuid.uuid4())
    start_time = time.time()

    def timer_done():
        entry = _active_timers.pop(timer_id, None)
        if entry:
            _, dur, _, lbl = entry
            _notify_timer_done(lbl, dur)

    t = threading.Timer(duration_sec, timer_done)
    t.daemon = True
    t.start()
    _active_timers[timer_id] = (t, duration_sec, start_time, label)
    return {"id": timer_id, "label": label, "duration_sec": duration_sec}


def cancel_timer(timer_id: str) -> bool:
    """Cancel a single timer by id. Returns True if removed."""
    entry = _active_timers.pop(timer_id, None)
    if entry:
        entry[0].cancel()
        return True
    return False


def cancel_all_timers() -> int:
    """Cancel all timers. Returns count cancelled."""
    count = len(_active_timers)
    for t, _, _, _ in _active_timers.values():
        t.cancel()
    _active_timers.clear()
    return count


def _parse_timer_label(message: str) -> str:
    """Extract optional timer label (e.g. 'timer 5 minutes for eggs' -> 'eggs')."""
    # "timer X for Y" or "X minute timer for Y"
    m = re.search(r"(?:for|called)\s+(.+?)(?:\s+please|\s*$)", message, re.I)
    if m:
        return m.group(1).strip()[:50]
    return "Timer"


class TimersTool(Tool):
    """Set and list countdown timers."""

    @property
    def name(self) -> str:
        return "timer"

    @property
    def description(self) -> str:
        return "Set, list, or cancel countdown timers"

    def execute(self, intent: str, message: str) -> str:
        lower = message.lower()

        # List timers
        if "list" in lower or "show" in lower or ("what" in lower and "timer" in lower):
            timers = get_active_timers()
            if not timers:
                return "No timers running."
            lines = [f"• {t['label']}: {t['remaining_sec']}s left" for t in timers]
            return "Active timers:\n" + "\n".join(lines)

        # Cancel timers
        if "cancel" in lower or "stop" in lower:
            count = cancel_all_timers()
            if count == 0:
                return "No timers to cancel."
            return f"All {count} timer(s) cancelled."

        # Set timer (normalize number words for STT: "five minutes" -> "5 minutes")
        duration = parse_timer_duration(normalize_time_words(message))
        if duration and duration > 0:
            label = _parse_timer_label(message)
            add_timer(duration, label)
            mins, secs = divmod(duration, 60)
            if mins:
                return f"Timer set for {mins} minute{'s' if mins != 1 else ''}."
            return f"Timer set for {secs} seconds."
        return "I couldn't understand the duration. Try: timer 5 minutes"
