"""Convert number words to digits for STT compatibility (e.g. 'eleven oh five' -> 11:05)."""

# Word -> digit for 0-19
_WORDS_0_19 = {
    "zero": 0, "oh": 0, "o": 0,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19,
}

# Tens: twenty -> 20, thirty -> 30, etc.
_WORDS_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

# Special times
_SPECIAL_TIMES = {"noon": 12, "midnight": 0}


def _word_to_digit(word: str) -> int | None:
    """Convert a single word to digit, or None if not a number word."""
    w = word.lower().rstrip(".,")
    if w in _WORDS_0_19:
        return _WORDS_0_19[w]
    if w in _WORDS_TENS:
        return _WORDS_TENS[w]
    if w in _SPECIAL_TIMES:
        return _SPECIAL_TIMES[w]
    return None


def words_to_number_sequence(text: str) -> list[int]:
    """
    Convert a sequence of number words to digits.
    E.g. "eleven oh five" -> [11, 0, 5], "twenty five" -> [25] or [20, 5].
    """
    words = text.lower().split()
    result: list[int] = []
    i = 0
    while i < len(words):
        w = words[i].rstrip(".,")
        # Check for "twenty five" (20 + 5), "thirty two" (30 + 2), etc.
        if w in _WORDS_TENS and i + 1 < len(words):
            next_w = words[i + 1].lower().rstrip(".,")
            if next_w in _WORDS_0_19 and _WORDS_0_19[next_w] < 10:
                result.append(_WORDS_TENS[w] + _WORDS_0_19[next_w])
                i += 2
                continue
        d = _word_to_digit(words[i])
        if d is not None:
            result.append(d)
        i += 1
    return result


def normalize_time_words(text: str) -> str:
    """
    Replace number words with digits in text for time parsing.
    E.g. "eleven oh five" -> "11 5" (11:05), "seven thirty" -> "7 30".
    """
    words = text.lower().split()
    result: list[str] = []
    i = 0
    while i < len(words):
        w = words[i].rstrip(".,")
        # "oh five" / "o five" -> "5" (for 11:05)
        if w in ("oh", "o") and i + 1 < len(words):
            next_d = _word_to_digit(words[i + 1])
            if next_d is not None and 0 <= next_d <= 9:
                result.append(str(next_d))
                i += 2
                continue
        # "twenty five" -> "25"
        if w in _WORDS_TENS and i + 1 < len(words):
            next_w = words[i + 1].lower().rstrip(".,")
            if next_w in _WORDS_0_19 and _WORDS_0_19[next_w] < 10:
                result.append(str(_WORDS_TENS[w] + _WORDS_0_19[next_w]))
                i += 2
                continue
        d = _word_to_digit(words[i])
        if d is not None:
            result.append(str(d))
        else:
            result.append(words[i])
        i += 1
    return " ".join(result)


