"""Tests for OpenClaw client: validation, payload construction (Sprint 2c)."""

import pytest

from gerty.openclaw.client import OPENCLAW_UNAVAILABLE_MSG, build_openclaw_payload
from gerty.openclaw.validation import (
    ValidationResult,
    validate_openclaw_response,
)


class TestValidateOpenclawResponse:
    """Result validation layer."""

    def test_empty_output_returns_hint(self):
        """Empty content -> replaced with context-aware hint."""
        result = validate_openclaw_response("", "check my calendar", success=True)
        assert result.is_empty
        assert result.replaced_with_hint
        assert "check_google_workspace" in result.normalized_content
        assert "Google" in result.normalized_content

    def test_empty_output_generic_hint_for_non_google(self):
        """Empty content for non-Google query -> generic hint (mentions exec, not Google-specific)."""
        result = validate_openclaw_response("", "run ls", success=True)
        assert result.is_empty
        assert "exec-approvals" in result.normalized_content or "exec" in result.normalized_content
        # Generic hint is longer; Google-specific hint starts with "I tried to fetch your Google data"
        assert "I tried to fetch your Google data" not in result.normalized_content

    def test_tool_failure_phrasing_replaced(self):
        """Content with exec failed / permission denied -> replaced with hint."""
        result = validate_openclaw_response(
            "exec failed: permission denied",
            "check my calendar",
            success=False,
        )
        assert result.is_tool_failure
        assert result.replaced_with_hint
        assert "check_google_workspace" in result.normalized_content

    def test_tool_failure_error_keyword(self):
        """Content with 'Error:' -> tool failure."""
        result = validate_openclaw_response(
            "Error: EACCES when running script",
            "what's on my calendar",
            success=False,
        )
        assert result.is_tool_failure
        assert result.replaced_with_hint

    def test_valid_content_passthrough(self):
        """Real content -> passthrough unchanged."""
        content = "Here are your events:\n- 2pm Meeting with Bob\n- 4pm Dentist"
        result = validate_openclaw_response(content, "check my calendar", success=True)
        assert not result.replaced_with_hint
        assert result.normalized_content == content.strip()
        assert not result.is_empty
        assert not result.is_tool_failure
        assert not result.is_likely_fabricated

    def test_likely_fabricated_short_intro(self):
        """'Here are your events' with <80 chars and no real data -> replaced."""
        content = "Here are your calendar events for today."
        result = validate_openclaw_response(content, "what's on my calendar", success=True)
        assert result.is_likely_fabricated
        assert result.replaced_with_hint
        assert "check_google_workspace" in result.normalized_content

    def test_likely_fabricated_retrieved_intro(self):
        """'I've retrieved your' with very short content -> replaced."""
        content = "I've retrieved your emails. You have 3 new messages."
        result = validate_openclaw_response(content, "check my gmail", success=True)
        # 47 chars - below threshold, has intro pattern
        assert result.is_likely_fabricated
        assert result.replaced_with_hint

    def test_legitimate_short_response_passthrough(self):
        """Short but legitimate response (e.g. 'No events today') -> passthrough."""
        content = "No events on your calendar for today."
        result = validate_openclaw_response(content, "what's on my calendar", success=True)
        # "No events" is not in FABRICATED_INTRO_PATTERNS - we removed it
        assert not result.is_likely_fabricated
        assert not result.replaced_with_hint
        assert result.normalized_content == content

    def test_success_false_empty_content(self):
        """success=False, empty content -> empty hint."""
        result = validate_openclaw_response("", "run something", success=False)
        assert result.is_empty
        assert result.replaced_with_hint


class TestBuildOpenclawPayload:
    """Payload construction."""

    def test_message_only(self):
        """Message only -> no system, no history."""
        out = build_openclaw_payload("hello")
        assert out == "hello"

    def test_system_context_prepended(self):
        """System context -> [System: ...] prepended."""
        out = build_openclaw_payload("hi", system_context="You are Gerty.")
        assert out.startswith("[System: You are Gerty.]")
        assert "hi" in out

    def test_history_included(self):
        """History -> Previous conversation section."""
        history = [
            {"role": "user", "content": "what time is it"},
            {"role": "assistant", "content": "2pm"},
        ]
        out = build_openclaw_payload("and tomorrow?", history=history)
        assert "Previous conversation:" in out
        assert "User: what time is it" in out
        assert "Assistant: 2pm" in out
        assert "and tomorrow?" in out

    def test_full_structure(self):
        """All parts in correct order."""
        history = [{"role": "user", "content": "hi"}]
        out = build_openclaw_payload(
            "bye",
            history=history,
            system_context="Be helpful.",
        )
        assert out.index("[System:") < out.index("Previous conversation:")
        assert out.index("Previous conversation:") < out.index("bye")
        assert out.endswith("bye")
