"""Timezone conversion tool."""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

from gerty.tools.base import Tool

# Common city/country -> IANA zone
CITIES = {
    "london": "Europe/London",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "tokyo": "Asia/Tokyo",
    "sydney": "Australia/Sydney",
    "new york": "America/New_York",
    "nyc": "America/New_York",
    "la": "America/Los_Angeles",
    "los angeles": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "toronto": "America/Toronto",
    "vancouver": "America/Vancouver",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "singapore": "Asia/Singapore",
    "dubai": "Asia/Dubai",
    "moscow": "Europe/Moscow",
    "utc": "UTC",
    "gmt": "Europe/London",
}


def _parse_timezone_query(message: str) -> str | None:
    """Extract target timezone from message. E.g. 'time in Tokyo' -> Tokyo."""
    lower = message.lower()
    for phrase in ["in ", "at ", "timezone ", "time zone "]:
        if phrase in lower:
            idx = lower.find(phrase) + len(phrase)
            rest = message[idx:].strip()
            # Take first word or phrase
            words = rest.split()
            for i in range(len(words), 0, -1):
                candidate = " ".join(words[:i]).lower().rstrip("?.,")
                if candidate in CITIES:
                    return candidate
            if words:
                return " ".join(words[:2]).lower().rstrip("?.,")
    return None


class TimezoneTool(Tool):
    """What time is it in another timezone."""

    @property
    def name(self) -> str:
        return "timezone"

    @property
    def description(self) -> str:
        return "Time in another city or timezone"

    def execute(self, intent: str, message: str) -> str:
        place = _parse_timezone_query(message)
        if not place or place not in CITIES:
            return "Try: what time is it in Tokyo? I support: " + ", ".join(sorted(CITIES.keys())[:12]) + "..."
        zone = CITIES[place]
        try:
            now = datetime.now(ZoneInfo(zone))
            city = place.title()
            return f"In {city} it's **{now.strftime('%I:%M %p')}** on **{now.strftime('%A, %B %d')}**."
        except Exception:
            return f"I don't have timezone data for {place}."
