"""Pomodoro tool: 25 min work, 5 min break cycles."""

import logging
import threading
import time
from typing import Callable

from gerty.tools.base import Tool

logger = logging.getLogger(__name__)

WORK_MIN = 25
BREAK_MIN = 5
_pomodoro: dict | None = None  # {phase, remaining_sec, timer, start_time}
_pomodoro_callbacks: list[Callable[[str, int], None]] = []


def register_pomodoro_callback(cb: Callable[[str, int], None]):
    """Register callback when a phase ends. (phase_name, duration_sec)."""
    _pomodoro_callbacks.append(cb)


def _notify_pomodoro(phase: str, duration_sec: int):
    for cb in _pomodoro_callbacks:
        try:
            cb(phase, duration_sec)
        except Exception as e:
            logger.debug("Pomodoro callback failed: %s", e)


def get_pomodoro_status() -> dict | None:
    """Return current pomodoro state or None."""
    global _pomodoro
    if not _pomodoro:
        return None
    elapsed = time.time() - _pomodoro["start_time"]
    remaining = max(0, _pomodoro["duration_sec"] - int(elapsed))
    return {
        "phase": _pomodoro["phase"],
        "remaining_sec": remaining,
        "duration_sec": _pomodoro["duration_sec"],
    }


def cancel_pomodoro() -> bool:
    """Cancel active pomodoro. Returns True if one was running."""
    global _pomodoro
    if _pomodoro and _pomodoro.get("timer"):
        _pomodoro["timer"].cancel()
    had = _pomodoro is not None
    _pomodoro = None
    return had


def _format_remaining(secs: int) -> str:
    m, s = divmod(secs, 60)
    return f"{m}m {s}s"


class PomodoroTool(Tool):
    """Pomodoro: 25 min work, 5 min break."""

    @property
    def name(self) -> str:
        return "pomodoro"

    @property
    def description(self) -> str:
        return "Pomodoro timer: 25 min work, 5 min break"

    def execute(self, intent: str, message: str) -> str:
        global _pomodoro
        lower = message.lower()

        # Status
        if "status" in lower or "how long" in lower or "remaining" in lower:
            status = get_pomodoro_status()
            if not status:
                return "No pomodoro running. Say 'start pomodoro' to begin."
            phase = status["phase"]
            rem = _format_remaining(status["remaining_sec"])
            return f"**{phase}** phase: **{rem}** remaining."

        # Stop / cancel
        if "stop" in lower or "cancel" in lower:
            if cancel_pomodoro():
                return "Pomodoro stopped."
            return "No pomodoro running."

        # Start
        if "start" in lower or "begin" in lower:
            if _pomodoro:
                return "A pomodoro is already running. Say 'stop pomodoro' first."
            _start_work()
            return f"Pomodoro started: **25 min work** phase. I'll notify you when it's break time."

        return "Say 'start pomodoro' to begin a 25 min work session."


def _start_work():
    global _pomodoro
    duration = WORK_MIN * 60

    def on_done():
        global _pomodoro
        _notify_pomodoro("Work", duration)
        _pomodoro = None
        _start_break()

    t = threading.Timer(duration, on_done)
    t.daemon = True
    t.start()
    _pomodoro = {
        "phase": "Work",
        "duration_sec": duration,
        "timer": t,
        "start_time": time.time(),
    }


def _start_break():
    global _pomodoro
    duration = BREAK_MIN * 60

    def on_done():
        global _pomodoro
        _notify_pomodoro("Break", duration)
        _pomodoro = None

    t = threading.Timer(duration, on_done)
    t.daemon = True
    t.start()
    _pomodoro = {
        "phase": "Break",
        "duration_sec": duration,
        "timer": t,
        "start_time": time.time(),
    }
