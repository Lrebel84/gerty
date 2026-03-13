"""Calendar tool: runs check_google_calendar.py directly for accurate data (bypasses OpenClaw)."""

import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from gerty.tools.base import Tool

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = PROJECT_ROOT / "scripts" / "check_google_calendar.py"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def _parse_date_from_message(message: str) -> str:
    """Extract date from message, return YYYY-MM-DD. Defaults to tomorrow."""
    lower = message.lower().strip()
    now = datetime.now()
    year = now.year

    if "today" in lower:
        return now.strftime("%Y-%m-%d")
    if "tomorrow" in lower:
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")

    # Match "18th March", "March 18th", "18 March", "March 18", "18th of March"
    for month_name, month_num in MONTHS.items():
        if month_name not in lower:
            continue
        # Day before month: "18th March", "18 March"
        m = re.search(rf"(\d{{1,2}})(?:st|nd|rd|th)?\s*(?:of\s*)?{month_name}", lower)
        if m:
            day = int(m.group(1))
            if 1 <= day <= 31:
                return f"{year}-{month_num:02d}-{day:02d}"
        # Month before day: "March 18th", "March 18"
        m = re.search(rf"{month_name}\s*(\d{{1,2}})(?:st|nd|rd|th)?", lower)
        if m:
            day = int(m.group(1))
            if 1 <= day <= 31:
                return f"{year}-{month_num:02d}-{day:02d}"

    # YYYY-MM-DD already in message
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", message)
    if m:
        return m.group(0)

    # Default: tomorrow
    return (now + timedelta(days=1)).strftime("%Y-%m-%d")


class CalendarTool(Tool):
    """Runs check_google_calendar.py for real calendar data. Bypasses OpenClaw to avoid hallucination."""

    @property
    def name(self) -> str:
        return "calendar"

    @property
    def description(self) -> str:
        return "Google Calendar events for a date"

    def execute(self, intent: str, message: str) -> str:
        if not SCRIPT.exists():
            return "Calendar script not found. Run the OAuth flow first (see docs/GOOGLE_OAUTH_SETUP.md)."
        if not VENV_PYTHON.exists():
            return "Python venv not found."

        date_str = _parse_date_from_message(message)
        try:
            result = subprocess.run(
                [str(VENV_PYTHON), str(SCRIPT), date_str],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(PROJECT_ROOT),
            )
            if result.returncode != 0:
                return result.stderr or f"Calendar script failed (exit {result.returncode})."
            return result.stdout.strip() or "No events."
        except subprocess.TimeoutExpired:
            return "Calendar request timed out."
        except Exception as e:
            return f"Calendar error: {e}"
