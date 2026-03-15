"""Tests for OpenClaw client: validation, payload construction (Sprint 2c), state boundary."""

from unittest.mock import patch

import pytest

from gerty.openclaw.client import (
    OPENCLAW_SECURITY_BLOCKED_MSG,
    OPENCLAW_UNAVAILABLE_MSG,
    build_openclaw_payload,
    execute,
)
from gerty.openclaw.validation import (
    ValidationResult,
    WRITE_VERIFICATION_FAILED_MSG,
    validate_openclaw_response,
    verify_write_response,
)


class TestValidateOpenclawResponse:
    """Result validation layer."""

    def test_empty_output_returns_hint(self):
        """Empty content -> replaced with OpenClaw/gog-aware hint (stabilization path)."""
        result = validate_openclaw_response("", "check my calendar", success=True)
        assert result.is_empty
        assert result.replaced_with_hint
        assert "OpenClaw" in result.normalized_content
        assert "gog" in result.normalized_content or "verify_gog" in result.normalized_content

    def test_empty_output_generic_hint_for_non_google(self):
        """Empty content for non-Google query -> generic hint (mentions exec, not Google-specific)."""
        result = validate_openclaw_response("", "run ls", success=True)
        assert result.is_empty
        assert "exec-approvals" in result.normalized_content or "exec" in result.normalized_content
        # Generic hint is longer; Google-specific hint starts with "I tried to fetch your Google data"
        assert "I tried to fetch your Google data" not in result.normalized_content

    def test_tool_failure_phrasing_replaced(self):
        """Content with exec failed / permission denied -> replaced with OpenClaw hint."""
        result = validate_openclaw_response(
            "exec failed: permission denied",
            "check my calendar",
            success=False,
        )
        assert result.is_tool_failure
        assert result.replaced_with_hint
        assert "OpenClaw" in result.normalized_content

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
        """'Here are your events' with <80 chars and no real data -> replaced with OpenClaw hint."""
        content = "Here are your calendar events for today."
        result = validate_openclaw_response(content, "what's on my calendar", success=True)
        assert result.is_likely_fabricated
        assert result.replaced_with_hint
        assert "OpenClaw" in result.normalized_content

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


class TestVerifyWriteResponse:
    """Stabilization Reset §4: require backend confirmation before success."""

    def test_calendar_create_with_event_id_passthrough(self):
        """Response with event id -> passthrough."""
        out = verify_write_response(
            "Event created. event_id: 4jc652rto5d4tcgpajhv0d77e0",
            "calendar_create",
        )
        assert "4jc652rto5d4tcgpajhv0d77e0" in out

    def test_calendar_create_without_event_id_fails(self):
        """Response without event id -> failure message."""
        out = verify_write_response(
            "I've added the meeting to your calendar.",
            "calendar_create",
        )
        assert out == WRITE_VERIFICATION_FAILED_MSG

    def test_email_send_with_message_id_passthrough(self):
        """Response with message_id -> passthrough."""
        out = verify_write_response(
            "Email sent. message_id: 19cf34881788ef4a",
            "email_send",
        )
        assert "19cf34881788ef4a" in out

    def test_email_send_without_message_id_fails(self):
        """Response without message_id -> failure message."""
        out = verify_write_response(
            "I've sent the email.",
            "email_send",
        )
        assert out == WRITE_VERIFICATION_FAILED_MSG

    def test_read_intent_passthrough(self):
        """Read intents -> always passthrough (no verification)."""
        out = verify_write_response("Here are your events...", "calendar_check")
        assert out == "Here are your events..."

    def test_none_primary_intent_passthrough(self):
        """None primary_intent -> passthrough."""
        out = verify_write_response("Some response", None)
        assert out == "Some response"


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


class TestOpenclawSecurityGuard:
    """Sprint 10a: Security screening before OpenClaw execution."""

    def test_execute_blocks_risky_message(self):
        """execute returns security blocked message for risky requests."""
        with patch("gerty.openclaw.client._gateway_port_reachable", return_value=True):
            out = execute("run rm -rf /tmp/foo")
        assert OPENCLAW_SECURITY_BLOCKED_MSG in out
        assert "Blocked:" in out

    def test_execute_allows_safe_message(self):
        """Safe messages pass screen (tested via screen_openclaw_message in test_security)."""
        # screen_openclaw_message("what's on my calendar?") returns (False, "")
        # execute() would proceed to OpenClaw. We rely on test_security for screen coverage.
        from gerty.security import screen_openclaw_message
        blocked, _ = screen_openclaw_message("what's on my calendar tomorrow?")
        assert blocked is False


class TestOpenclawStateBoundary:
    """State boundary hardening: inspect, reset semantics."""

    def test_inspect_openclaw_context_returns_expected_keys(self):
        """inspect_openclaw_context returns dict with boundary, session, memory_db, etc."""
        from gerty.openclaw.context_inspect import inspect_openclaw_context

        report = inspect_openclaw_context()
        assert "boundary" in report
        assert "session" in report
        assert "memory_db" in report
        assert "bootstrap_memory" in report
        assert "proactive_influence" in report
        assert "notes" in report

    def test_inspect_boundary_classification(self):
        """Boundary has gerty_owned, openclaw_owned, shared."""
        from gerty.openclaw.context_inspect import inspect_openclaw_context

        report = inspect_openclaw_context()
        assert "gerty_owned" in report["boundary"]
        assert "openclaw_owned" in report["boundary"]
        assert "shared" in report["boundary"]
        assert any(
            "chat" in str(x).lower() or "session" in str(x).lower()
            for x in report["boundary"]["gerty_owned"]
        )
        assert "MEMORY.md" in str(report["boundary"]["shared"])

    def test_format_inspect_report_produces_string(self):
        """format_inspect_report produces readable string with sections."""
        from gerty.openclaw.context_inspect import inspect_openclaw_context, format_inspect_report

        report = inspect_openclaw_context()
        out = format_inspect_report(report)
        assert "OpenClaw Context Inspection" in out
        assert "Boundary Classification" in out
        assert "Session" in out
        assert "Memory DB" in out
        assert "Bootstrap Memory" in out
        assert "Proactive Influence" in out

    def test_clear_full_reset_without_memory_db(self):
        """clear_full_reset(include_openclaw_memory_db=False) does not clear memory DB."""
        from gerty.openclaw.client import clear_full_reset

        report = clear_full_reset(
            include_gerty_history=False,
            include_openclaw_session=False,
            include_openclaw_memory_db=False,
        )
        assert "cleared" in report
        assert "not_cleared" in report
        assert any("memory_db" in str(x) for x in report["not_cleared"])

    def test_clear_full_reset_report_structure(self):
        """clear_full_reset returns report with cleared, not_cleared, errors."""
        from gerty.openclaw.client import clear_full_reset

        report = clear_full_reset(
            include_gerty_history=False,
            include_openclaw_session=False,
            include_openclaw_memory_db=False,
        )
        assert isinstance(report["cleared"], list)
        assert isinstance(report["not_cleared"], list)
        assert isinstance(report["errors"], list)


class TestOpenclawMemoryTransparency:
    """Memory transparency v2: metadata, transparency report, proactive visibility."""

    def test_compute_memory_influence_metadata_structure(self):
        """compute_memory_influence_metadata returns expected keys."""
        from gerty.openclaw.context_inspect import inspect_openclaw_context
        from gerty.openclaw.transparency import compute_memory_influence_metadata

        ctx = inspect_openclaw_context()
        meta = compute_memory_influence_metadata(ctx, history_included=True)
        assert "memory_influence_detected" in meta
        assert "memory_sources_used" in meta
        assert "bootstrap_memory_used" in meta
        assert "proactive_memory_used" in meta
        assert "openclaw_session_used" in meta
        assert "openclaw_memory_db_present" in meta
        assert "recent_memory_file_updates" in meta
        assert "transparency_notes" in meta

    def test_memory_sources_include_current_chat(self):
        """memory_sources_used always includes current_chat."""
        from gerty.openclaw.context_inspect import inspect_openclaw_context
        from gerty.openclaw.transparency import compute_memory_influence_metadata

        ctx = inspect_openclaw_context()
        meta = compute_memory_influence_metadata(ctx, history_included=False)
        assert "current_chat" in meta["memory_sources_used"]

    def test_history_included_adds_gerty_chat_history(self):
        """history_included=True adds gerty_chat_history to sources."""
        from gerty.openclaw.context_inspect import inspect_openclaw_context
        from gerty.openclaw.transparency import compute_memory_influence_metadata

        ctx = inspect_openclaw_context()
        meta = compute_memory_influence_metadata(ctx, history_included=True)
        assert "gerty_chat_history" in meta["memory_sources_used"]

    def test_build_transparency_report_sections(self):
        """build_transparency_report has required sections."""
        from gerty.openclaw.context_inspect import build_transparency_report

        report = build_transparency_report(history_included=False)
        assert "current_chat_context" in report
        assert "persistent_memory_sources" in report
        assert "recently_updated_memory_sources" in report
        assert "likely_reply_influence" in report
        assert "unknowns_and_limitations" in report

    def test_format_transparency_report_produces_string(self):
        """format_transparency_report produces readable output."""
        from gerty.openclaw.context_inspect import build_transparency_report, format_transparency_report

        report = build_transparency_report(history_included=False)
        out = format_transparency_report(report)
        assert "OpenClaw Memory Transparency Report" in out
        assert "Likely Reply Influence" in out
        assert "Unknowns" in out

    def test_set_last_reply_metadata_roundtrip(self):
        """set_last_reply_metadata and get_last_reply_metadata roundtrip."""
        from gerty.openclaw.transparency import (
            set_last_reply_metadata,
            get_last_reply_metadata,
            clear_last_reply_metadata,
        )

        clear_last_reply_metadata()
        assert get_last_reply_metadata() is None
        meta = {"memory_influence_detected": True, "memory_sources_used": ["current_chat"]}
        set_last_reply_metadata(meta)
        got = get_last_reply_metadata()
        assert got is not None
        assert got["memory_influence_detected"] is True
        assert "current_chat" in got["memory_sources_used"]
        clear_last_reply_metadata()
        assert get_last_reply_metadata() is None

    def test_unknowns_handled_cleanly(self):
        """Transparency report includes unknowns/limitations."""
        from gerty.openclaw.context_inspect import build_transparency_report

        report = build_transparency_report(history_included=False)
        unknowns = report["unknowns_and_limitations"]
        assert isinstance(unknowns, list)
        assert len(unknowns) > 0
