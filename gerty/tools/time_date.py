"""Time and date tool."""

from datetime import datetime

from gerty.tools.base import Tool


class TimeDateTool(Tool):
    """Returns current time and date."""

    @property
    def name(self) -> str:
        return "time_date"

    @property
    def description(self) -> str:
        return "Current time and date"

    def execute(self, intent: str, message: str) -> str:
        now = datetime.now()
        if intent == "time":
            return f"The time is {now.strftime('%I:%M %p')}."
        if intent == "date":
            return f"Today is {now.strftime('%A, %B %d, %Y')}."
        return f"Today is {now.strftime('%A, %B %d, %Y')}. The time is {now.strftime('%I:%M %p')}."
