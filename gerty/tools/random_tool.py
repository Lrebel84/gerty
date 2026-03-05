"""Random tool: coin flip, dice roll, pick number."""

import random
import re

from gerty.tools.base import Tool


def _parse_dice(text: str) -> tuple[int, int] | None:
    """Parse NdM format (e.g. 2d6 = two six-sided dice). Returns (count, sides)."""
    m = re.search(r"(\d+)\s*d\s*(\d+)", text.lower())
    if m:
        return (int(m.group(1)), int(m.group(2)))
    # "roll 6" or "roll a 6" = 1d6
    m = re.search(r"roll\s*(?:a\s*)?(\d+)", text.lower())
    if m:
        return (1, int(m.group(1)))
    return None


def _parse_range(text: str) -> tuple[int, int] | None:
    """Parse 'number between 1 and 10' or 'pick 1-10'."""
    m = re.search(r"(?:between\s+)?(\d+)\s*(?:and|to|-)\s*(\d+)", text.lower())
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo <= hi:
            return (lo, hi)
    m = re.search(r"(\d+)\s*-\s*(\d+)", text)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo <= hi:
            return (lo, hi)
    return None


def _parse_choices(text: str) -> list[str] | None:
    """Parse 'choose A, B, or C' or 'pick from A B C'."""
    for sep in [",", " or ", " and ", " / "]:
        if sep in text:
            parts = [p.strip() for p in re.split(rf"\s*{re.escape(sep)}\s*", text)]
            if len(parts) >= 2 and all(len(p) < 50 for p in parts):
                return parts
    return None


class RandomTool(Tool):
    """Coin flip, dice roll, random number, pick from choices."""

    @property
    def name(self) -> str:
        return "random"

    @property
    def description(self) -> str:
        return "Coin flip, dice roll, random number, pick from options"

    def execute(self, intent: str, message: str) -> str:
        lower = message.lower()

        # Coin flip
        if "coin" in lower or "flip" in lower and "dice" not in lower:
            result = random.choice(["Heads", "Tails"])
            return f"Flipped a coin: **{result}**."

        # Dice
        dice = _parse_dice(message)
        if dice:
            count, sides = dice
            if count > 20 or sides > 1000:
                return "Keep it reasonable: max 20 dice, 1000 sides."
            rolls = [random.randint(1, sides) for _ in range(count)]
            total = sum(rolls)
            if count == 1:
                return f"Rolled d{sides}: **{rolls[0]}**."
            return f"Rolled {count}d{sides}: {rolls} = **{total}**."

        # Random number in range
        rng = _parse_range(message)
        if rng:
            lo, hi = rng
            n = random.randint(lo, hi)
            return f"Picked a number between {lo} and {hi}: **{n}**."

        # Pick from choices
        for phrase in ["choose", "pick", "select", "between"]:
            if phrase in lower:
                idx = lower.find(phrase)
                rest = message[idx + len(phrase) :].strip()
                choices = _parse_choices(rest)
                if choices:
                    return f"Picked: **{random.choice(choices)}**."

        # Default: coin flip
        result = random.choice(["Heads", "Tails"])
        return f"Flipped a coin: **{result}**."
