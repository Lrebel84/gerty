"""Timer tool: countdown timers."""

import re
import threading
import time
from typing import Callable

from gerty.llm.router import parse_timer_duration
from gerty.tools.base import Tool

# In-memory active timers: label -> (Timer, duration_sec, start_time)
_active_timers: dict[str, tuple[threading.Timer, int, float]] = {}
_timer_callbacks: list[Callable[[str, int], None]] = []  # (label, duration_sec)


def _notify_timer_done(label: str, duration_sec: int):
    for cb in _timer_callbacks:
        try:
            cb(label, duration_sec)
        except Exception:
            pass


def register_timer_callback(cb: Callable[[str, int], None]):
    """Register callback for when a timer completes."""
    _timer_callbacks.append(cb)


def get_active_timers() -> list[dict]:
    """Return active timers with label and remaining seconds."""
    now = time.time()
    result = []
    for label, (_, duration_sec, start_time) in _active_timers.items():
        remaining = max(0, int(duration_sec - (now - start_time)))
        result.append({"label": label, "remaining_sec": remaining, "duration_sec": duration_sec})
    return result


def cancel_all_timers() -> int:
    """Cancel all timers. Returns count cancelled."""
    count = len(_active_timers)
    for t, _, _ in _active_timers.values():
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
        global _active_timers

        lower = message.lower()

        # List timers
        if "list" in lower or "show" in lower or "what" in lower and "timer" in lower:
            if not _active_timers:
                return "No timers running."
            lines = [f"• {label}: {dur}s" for label, (_, dur, _) in _active_timers.items()]
            return "Active timers:\n" + "\n".join(lines)

        # Cancel timers
        if "cancel" in lower or "stop" in lower:
            if not _active_timers:
                return "No timers to cancel."
            for t, _, _ in _active_timers.values():
                t.cancel()
            _active_timers.clear()
            return "All timers cancelled."

        # Set timer
        duration = parse_timer_duration(message)
        if duration and duration > 0:
            label = _parse_timer_label(message)
            if label in _active_timers:
                _active_timers[label][0].cancel()

            start_time = time.time()

            def timer_done():
                _active_timers.pop(label, None)
                _notify_timer_done(label, duration)

            t = threading.Timer(duration, timer_done)
            t.daemon = True
            t.start()
            _active_timers[label] = (t, duration, start_time)

            mins, secs = divmod(duration, 60)
            if mins:
                return f"Timer set for {mins} minute{'s' if mins != 1 else ''}."
            return f"Timer set for {secs} seconds."
        return "I couldn't understand the duration. Try: timer 5 minutes"
