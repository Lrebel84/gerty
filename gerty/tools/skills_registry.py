"""Skills registry for API and reference.

When adding a new tool → update BOTH:
  - This file (SKILLS below)
  - frontend/src/skills.ts
  - COMMANDS.md
See docs/ADDING_TOOLS.md for full checklist.
"""

from typing import TypedDict


class SkillEntry(TypedDict):
    category: str
    name: str
    description: str
    examples: list[str]


SKILLS: list[SkillEntry] = [
    # Time
    {
        "category": "Time",
        "name": "Time & date",
        "description": "Current time and date",
        "examples": ["what time is it", "current time", "what's the date", "today's date"],
    },
    {
        "category": "Time",
        "name": "Timezone",
        "description": "Time in other cities",
        "examples": ["time in Tokyo", "what time is it in London"],
    },
    {
        "category": "Time",
        "name": "Stopwatch",
        "description": "Elapsed time",
        "examples": ["start stopwatch", "how long has it been", "stop stopwatch"],
    },
    # Scheduling
    {
        "category": "Scheduling",
        "name": "Alarms",
        "description": "Set, list, or cancel alarms (daily or one-time)",
        "examples": ["set alarm for 7am", "daily alarm for 7am", "alarm for 6pm every day", "list my alarms", "cancel alarms"],
    },
    {
        "category": "Scheduling",
        "name": "Timers",
        "description": "Countdown timers",
        "examples": ["timer 5 minutes", "timer 10 minutes for eggs", "20 minutes", "list timers", "cancel timers"],
    },
    {
        "category": "Scheduling",
        "name": "Pomodoro",
        "description": "25 min work, 5 min break",
        "examples": ["start pomodoro", "pomodoro status", "stop pomodoro"],
    },
    # Utilities
    {
        "category": "Utilities",
        "name": "Calculator",
        "description": "Arithmetic and percentages",
        "examples": ["what is 15 + 27", "15% of 80", "2 ** 10"],
    },
    {
        "category": "Utilities",
        "name": "Unit conversion",
        "description": "Temperature, length, weight",
        "examples": ["convert 32F to C", "5 miles to km", "150 lb to kg"],
    },
    {
        "category": "Utilities",
        "name": "Random",
        "description": "Coin flip, dice, pick from options",
        "examples": ["flip a coin", "roll 2d6", "pick a number 1 to 10", "choose pizza or pasta"],
    },
    {
        "category": "Utilities",
        "name": "Notes",
        "description": "Save and recall notes",
        "examples": ["note: buy milk", "remember to call mom", "list notes", "clear notes"],
    },
    # Info
    {
        "category": "Info",
        "name": "Weather",
        "description": "Current weather by city",
        "examples": ["weather in London", "forecast for Tokyo"],
    },
    {
        "category": "Info",
        "name": "Web search",
        "description": "Search the web (DuckDuckGo)",
        "examples": ["search for Python tutorial", "look up current events"],
    },
    # Knowledge
    {
        "category": "Knowledge",
        "name": "RAG (documents + memory)",
        "description": "Search your files and remembered facts",
        "examples": ["check my docs for X", "search my files for Y", "what do my files say about Z"],
    },
]


def get_skills() -> list[SkillEntry]:
    """Return the skills list. Add new tools here when extending Gerty."""
    return SKILLS.copy()
