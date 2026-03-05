"""Stopwatch tool: start, elapsed, stop."""

import time
from datetime import timedelta

from gerty.tools.base import Tool

# In-memory: (start_time, label) or None
_stopwatch: tuple[float, str] | None = None


def _format_duration(secs: float) -> str:
    d = timedelta(seconds=int(secs))
    parts = str(d).split(":")
    if len(parts) == 3:
        h, m, s = parts
        if int(h) > 0:
            return f"{int(h)}h {int(m)}m {int(s)}s"
        if int(m) > 0:
            return f"{int(m)}m {int(s)}s"
        return f"{int(s)}s"
    return f"{int(secs)}s"


class StopwatchTool(Tool):
    """Stopwatch: start, how long, stop."""

    @property
    def name(self) -> str:
        return "stopwatch"

    @property
    def description(self) -> str:
        return "Start stopwatch, check elapsed time, or stop"

    def execute(self, intent: str, message: str) -> str:
        global _stopwatch
        lower = message.lower()

        # Stop / reset
        if "stop" in lower or "reset" in lower:
            if _stopwatch:
                elapsed = time.time() - _stopwatch[0]
                _stopwatch = None
                return f"Stopwatch stopped at **{_format_duration(elapsed)}**."
            return "No stopwatch running."

        # How long / elapsed
        if "how long" in lower or "elapsed" in lower or "been" in lower or "running" in lower:
            if _stopwatch:
                elapsed = time.time() - _stopwatch[0]
                return f"Stopwatch: **{_format_duration(elapsed)}**."
            return "No stopwatch running. Say 'start stopwatch' first."

        # Start
        if "start" in lower or "begin" in lower:
            _stopwatch = (time.time(), "stopwatch")
            return "Stopwatch started."

        # Default: show elapsed if running
        if _stopwatch:
            elapsed = time.time() - _stopwatch[0]
            return f"Stopwatch: **{_format_duration(elapsed)}**."
        return "No stopwatch running. Say 'start stopwatch' to begin."
