"""
Result validation for OpenClaw responses (Sprint 2c).

Detects and normalizes:
- Empty output
- Likely fabricated success (model claims success with no real data)
- Tool failure phrasing (exec failed, permission denied, etc.)
"""

import re
from dataclasses import dataclass

# Keywords that suggest Google Workspace context (for tailored empty-msg)
_GOOGLE_WORKSPACE_KEYWORDS = ("calendar", "gmail", "drive", "docs", "sheets", "email")

# Phrases that suggest tool/exec failure (normalize to helpful message)
_TOOL_FAILURE_PHRASES = (
    "exec failed",
    "execution failed",
    "permission denied",
    "eacces",
    "enoent",
    "command not found",
    "could not connect",
    "connection refused",
    "timeout",
    "timed out",
    "error:",
    "exception:",
    "traceback",
    "failed to run",
    "tool returned error",
)

# Fabricated success: model says "here are your X" but content has no real data
# (no dates, no list items, very short). "Your calendar is empty" is legitimate—excluded.
_FABRICATED_INTRO_PATTERNS = (
    r"here (?:are|is) your (?:calendar |events?|emails?|drive|documents?)",
    r"i(?:'ve| have) (?:retrieved|fetched|checked) your",
)
_FABRICATED_MIN_CONTENT_LEN = 80  # Below this, "here are your events" with nothing else = suspect


@dataclass
class ValidationResult:
    """Result of validating an OpenClaw response."""

    normalized_content: str
    is_empty: bool
    is_tool_failure: bool
    is_likely_fabricated: bool
    replaced_with_hint: bool


def _empty_output_message(original_message: str) -> str:
    """User-facing message when OpenClaw returns empty. Context-aware hints."""
    lower = (original_message or "").lower()
    if any(kw in lower for kw in _GOOGLE_WORKSPACE_KEYWORDS):
        return (
            "I tried to fetch your Google data but got no output. "
            "Run `./scripts/check_google_workspace.sh` to verify OAuth, exec config, and scripts. "
            "See docs/GOOGLE_WORKSPACE_STATUS.md for the full checklist."
        )
    return (
        "OpenClaw ran but returned no output. This often means: "
        "(1) exec needs approval—check ~/.openclaw/exec-approvals.json has your Python path and ask is off, "
        "(2) tools.exec.host must be 'gateway' (not sandbox) for Google token access, "
        "(3) the model may have skipped tool use. Run: ./scripts/check_google_workspace.sh to diagnose."
    )


def validate_openclaw_response(
    content: str,
    original_message: str,
    success: bool,
) -> ValidationResult:
    """
    Validate and normalize an OpenClaw response.

    Returns ValidationResult with normalized_content suitable for user display.
    """
    text = (content or "").strip()
    lower = text.lower()
    msg_lower = (original_message or "").lower()

    is_empty = len(text) == 0
    is_tool_failure = False
    is_likely_fabricated = False
    replaced_with_hint = False

    # 1. Empty output
    if is_empty:
        return ValidationResult(
            normalized_content=_empty_output_message(original_message),
            is_empty=True,
            is_tool_failure=False,
            is_likely_fabricated=False,
            replaced_with_hint=True,
        )

    # 2. Tool failure phrasing: content looks like an error, not a helpful reply
    for phrase in _TOOL_FAILURE_PHRASES:
        if phrase in lower:
            is_tool_failure = True
            break

    if is_tool_failure:
        hint = _empty_output_message(original_message)
        return ValidationResult(
            normalized_content=hint,
            is_empty=False,
            is_tool_failure=True,
            is_likely_fabricated=False,
            replaced_with_hint=True,
        )

    # 3. Likely fabricated success: "Here are your events" with no actual data
    # Skip if content has list-like data (bullets, times) — likely real
    has_list_like_data = bool(
        re.search(r"[-•]\s|\d{1,2}:\d{2}|\d{1,2}\s*(?:am|pm)\b", text)
    )
    if success and len(text) < _FABRICATED_MIN_CONTENT_LEN and not has_list_like_data:
        for pat in _FABRICATED_INTRO_PATTERNS:
            if re.search(pat, lower):
                if any(kw in msg_lower for kw in _GOOGLE_WORKSPACE_KEYWORDS):
                    is_likely_fabricated = True
                    hint = _empty_output_message(original_message)
                    return ValidationResult(
                        normalized_content=hint,
                        is_empty=False,
                        is_tool_failure=False,
                        is_likely_fabricated=True,
                        replaced_with_hint=True,
                    )
                break

    return ValidationResult(
        normalized_content=text,
        is_empty=False,
        is_tool_failure=False,
        is_likely_fabricated=False,
        replaced_with_hint=False,
    )
