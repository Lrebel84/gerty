"""Unit conversion tool: temperature, length, weight."""

import re

from gerty.tools.base import Tool

# Length: metres base
LENGTH = {"m": 1, "meter": 1, "metre": 1, "meters": 1, "metres": 1, "km": 1000, "mile": 1609.34, "miles": 1609.34, "mi": 1609.34, "ft": 0.3048, "foot": 0.3048, "feet": 0.3048, "inch": 0.0254, "inches": 0.0254, "cm": 0.01, "mm": 0.001, "yd": 0.9144}
# Weight: kg base
WEIGHT = {"kg": 1, "kilogram": 1, "kilograms": 1, "g": 0.001, "lb": 0.453592, "lbs": 0.453592, "pound": 0.453592, "pounds": 0.453592, "oz": 0.0283495}
# Temp: special handling
TEMP_PATTERNS = ["fahrenheit", "celsius", "kelvin", "f", "c", "k", "°f", "°c"]


def _convert_temp(val: float, from_u: str, to_u: str) -> float:
    from_u = from_u.lower().replace("°", "").replace("fahrenheit", "f").replace("celsius", "c")
    to_u = to_u.lower().replace("°", "").replace("fahrenheit", "f").replace("celsius", "c")
    # To Celsius first
    if from_u == "f":
        c = (val - 32) * 5 / 9
    elif from_u == "k":
        c = val - 273.15
    else:
        c = val
    if to_u == "f":
        return c * 9 / 5 + 32
    if to_u == "k":
        return c + 273.15
    return c


def _norm_unit(u: str) -> str:
    u = u.lower().replace("°", "")
    if u in ("fahrenheit", "f"):
        return "f"
    if u in ("celsius", "c", "celcius"):
        return "c"
    if u in ("kelvin", "k"):
        return "k"
    if u in ("mile", "miles", "mi"):
        return "mile"
    if u in ("foot", "feet", "ft"):
        return "ft"
    if u in ("meter", "metre", "meters", "metres"):
        return "m"
    if u in ("inch", "inches"):
        return "inch"
    if u in ("pound", "pounds"):
        return "lb"
    return u


def _parse_conversion(message: str) -> tuple[float, str, str] | None:
    """Parse 'X unit to unit' or 'convert X unit to unit'. Returns (value, from_unit, to_unit)."""
    lower = message.lower()
    # Match number (including decimals)
    num_match = re.search(r"(\d+(?:\.\d+)?)\s*", lower)
    if not num_match:
        return None
    val = float(num_match.group(1))

    # Find "to" or "in"
    to_match = re.search(r"\b(?:to|in)\s+(\w+)", lower)
    if not to_match:
        return None
    to_raw = to_match.group(1).lower()
    to_unit = _norm_unit(to_raw)
    if to_unit == "fahrenheit":
        to_unit = "f"
    if to_unit == "celsius":
        to_unit = "c"
    if to_unit == "kelvin":
        to_unit = "k"
    if to_unit == "miles":
        to_unit = "mile"

    # From unit: between number and "to"
    between = lower[num_match.end() : to_match.start()].strip()
    from_unit = None
    for u in list(LENGTH.keys()) + list(WEIGHT.keys()):
        if re.search(rf"\b{re.escape(u)}\b", between):
            from_unit = u
            break
    if not from_unit:
        if re.search(r"\b(f|fahrenheit|°f)\b", between) or (val < 150 and "f" in between):
            from_unit = "f"
        elif re.search(r"\b(c|celsius|°c)\b", between):
            from_unit = "c"
        elif re.search(r"\b(k|kelvin)\b", between):
            from_unit = "k"

    if not from_unit:
        return None
    from_unit = _norm_unit(from_unit)
    if not from_unit:
        return None
    from_unit = _norm_unit(from_unit)
    to_unit = _norm_unit(to_raw)
    return (val, from_unit, to_unit)


def _do_convert(val: float, from_u: str, to_u: str) -> float | None:
    from_u = from_u.lower()
    to_u = to_u.lower()
    if from_u in LENGTH and to_u in LENGTH:
        return val * LENGTH[from_u] / LENGTH[to_u]
    if from_u in WEIGHT and to_u in WEIGHT:
        return val * WEIGHT[from_u] / WEIGHT[to_u]
    if from_u in ("f", "c", "k") and to_u in ("f", "c", "k"):
        return _convert_temp(val, from_u, to_u)
    return None


class UnitsTool(Tool):
    """Unit conversion: temperature, length, weight."""

    @property
    def name(self) -> str:
        return "units"

    @property
    def description(self) -> str:
        return "Convert temperature, length, and weight"

    def execute(self, intent: str, message: str) -> str:
        parsed = _parse_conversion(message)
        if not parsed:
            return "Try: convert 5 miles to km, or 32 fahrenheit to celsius"
        val, from_u, to_u = parsed
        result = _do_convert(val, from_u, to_u)
        if result is None:
            return f"I don't know how to convert {from_u} to {to_u}. I support: temp (F/C/K), length (m, km, mi, ft, in, cm), weight (kg, lb, oz)."
        if result == int(result) and abs(result) < 1e10:
            return f"{val} {from_u} = {int(result)} {to_u}"
        return f"{val} {from_u} = {result:.4g} {to_u}"
