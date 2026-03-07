"""Math expression extraction for calculator intent. No dependencies on router or tools."""

import re


def extract_math(message: str) -> str | None:
    """Extract a math expression from natural language. Returns None if no math found."""
    lower = message.lower()
    # "15% of 80" -> 0.15 * 80
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:of|off)\s*(\d+(?:\.\d+)?)", lower)
    if m:
        pct, val = float(m.group(1)), float(m.group(2))
        return f"{pct / 100} * {val}"

    # "what is X" or "calculate X" or "X plus Y"
    for prefix in ("what is", "what's", "calculate", "compute", "evaluate", "="):
        if prefix in lower:
            idx = lower.rfind(prefix) + len(prefix)
            rest = message[idx:].strip()
            # Replace words with operators
            rest = re.sub(r"\bplus\b", "+", rest, flags=re.I)
            rest = re.sub(r"\bminus\b", "-", rest, flags=re.I)
            rest = re.sub(r"\btimes\b", "*", rest, flags=re.I)
            rest = re.sub(r"\bdivided by\b", "/", rest, flags=re.I)
            rest = re.sub(r"\bpercent\b", "/ 100", rest, flags=re.I)
            rest = re.sub(r"\bsquared\b", "** 2", rest, flags=re.I)
            rest = re.sub(r"\bcubed\b", "** 3", rest, flags=re.I)
            # Only allow safe chars
            if re.match(r"^[\d\s\+\-\*\/\.\*\*\(\)\%]+$", rest.replace(" ", "")):
                return rest

    # Bare expression: "2 + 2" – must be only digits, operators, spaces
    nums = re.findall(r"[\d\.]+", message)
    ops = re.findall(r"[+\-*/]", message)
    stripped = message.strip().replace(" ", "")
    if nums and (ops or len(nums) == 1) and re.match(r"^[\d\.\+\-\*\/\*\*\(\)\%]+$", stripped):
        return message.strip()

    return None
