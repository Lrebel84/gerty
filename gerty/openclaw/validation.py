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


def _empty_output_message(original_message: str, *, from_openclaw: bool = True) -> str:
    """User-facing message when OpenClaw returns empty. Context-aware hints.
    from_openclaw=True: path was OpenClaw/gog (use gog/exec hints). False: legacy native path."""
    lower = (original_message or "").lower()
    if any(kw in lower for kw in _GOOGLE_WORKSPACE_KEYWORDS):
        if from_openclaw:
            return (
                "OpenClaw returned no output for your calendar/email/drive request. "
                "Check: (1) openclaw daemon running: openclaw daemon start, "
                "(2) gog skill installed: clawhub install gog, "
                "(3) ~/.openclaw/exec-approvals.json has your Python path, ask=off, "
                "(4) tools.exec.host is 'gateway' in openclaw.json for gog keyring. "
                "Run ./scripts/verify_gog_setup.sh to diagnose."
            )
        return (
            "I tried to fetch your Google data but got no output. "
            "If token missing: run `./.venv/bin/python scripts/google_oauth_flow.py` (opens browser). "
            "Otherwise run `./scripts/check_google_workspace.sh` to verify OAuth, exec config, and scripts. "
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
    *,
    from_openclaw: bool = True,
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
            normalized_content=_empty_output_message(original_message, from_openclaw=from_openclaw),
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
        hint = _empty_output_message(original_message, from_openclaw=from_openclaw)
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
                    hint = _empty_output_message(original_message, from_openclaw=from_openclaw)
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


# Write verification (Stabilization Reset §4): require backend confirmation before success
_WRITE_INTENTS_REQUIRING_VERIFICATION = (
    "calendar_create",
    "calendar_update",
    "email_send",
    "email_reply",
)
# gog returns: event id (e.g. 4jc652rto5d4tcgpajhv0d77e0), message_id (e.g. 19cf34881788ef4a)
_EVENT_ID_PATTERN = re.compile(
    r"(?:event[_\s]?id|eventId|event\s+id)\s*[=:]?\s*[a-z0-9]{15,}|"
    r"calendar\.google\.com|"
    r"(?:created|added).*[a-z0-9]{15,}",
    re.IGNORECASE | re.DOTALL,
)
_MESSAGE_ID_PATTERN = re.compile(
    r"(?:message[_\s]?id|message_id)\s*[=:]?\s*[a-z0-9]{15,}",
    re.IGNORECASE,
)

WRITE_VERIFICATION_FAILED_MSG = (
    "I wasn't able to complete that. The action didn't return a confirmation. "
    "Check your calendar or email to verify."
)


def verify_write_response(
    response: str,
    primary_intent: str | None,
) -> str:
    """
    For write intents, require response to contain backend confirmation (event id, message_id).
    Do not report success without verification.
    """
    if not primary_intent or primary_intent not in _WRITE_INTENTS_REQUIRING_VERIFICATION:
        return response
    text = (response or "").strip()
    if not text:
        return WRITE_VERIFICATION_FAILED_MSG
    lower = text.lower()
    if any(phrase in lower for phrase in ("exec failed", "error", "could not", "permission denied")):
        return WRITE_VERIFICATION_FAILED_MSG
    if primary_intent in ("calendar_create", "calendar_update"):
        if _EVENT_ID_PATTERN.search(text):
            return response
        return WRITE_VERIFICATION_FAILED_MSG
    if primary_intent in ("email_send", "email_reply"):
        if _MESSAGE_ID_PATTERN.search(text):
            return response
        return WRITE_VERIFICATION_FAILED_MSG
    return response
