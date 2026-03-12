"""Tests for LLM router intent classification and parsing."""

from unittest.mock import MagicMock

import pytest

from gerty.llm.router import (
    _classify_web_intent_fallback,
    classify_intent,
    parse_timer_duration,
)
from gerty.tools.number_words import normalize_time_words


class TestClassifyIntent:
    def test_time(self):
        assert classify_intent("what time is it") == "time"
        assert classify_intent("current time") == "time"

    def test_date(self):
        assert classify_intent("what's the date") == "date"
        assert classify_intent("today's date") == "date"

    def test_timer_before_time(self):
        assert classify_intent("set a 5 minute timer") == "timer"
        assert classify_intent("timer for 10 minutes") == "timer"

    def test_alarm(self):
        assert classify_intent("set alarm for 7am") == "alarm"
        assert classify_intent("wake me at 6") == "alarm"

    def test_research(self):
        assert classify_intent("research best 3D printers under 500") == "research"
        assert classify_intent("compare and summarize top project management tools") == "research"
        assert classify_intent("find the best laptops") == "research"
        assert classify_intent("gather information about electric cars") == "research"
        assert classify_intent("thoroughly research this business xyz") == "research"
        assert classify_intent("complete overview of the market") == "research"
        assert classify_intent("can you find me the best budget PCs for local LLM") == "research"

    def test_web_lookup_keywords(self):
        """Queries needing web search without explicit 'search for' keywords."""
        assert classify_intent("can you get me the contact details for xyz business") == "search"
        assert classify_intent("when is the next showtimes of Dune at VUE in Sheffield") == "search"
        assert classify_intent("what's the phone number for Acme Corp") == "search"
        assert classify_intent("opening hours of the library") == "search"
        assert classify_intent("where can i find the address of city hall") == "search"
        assert classify_intent("can you find me a good plumber") == "search"

    def test_complex(self):
        assert classify_intent("explain quantum physics") == "complex"
        assert classify_intent("write code for a REST API") == "complex"

    def test_rag(self):
        assert classify_intent("check documentation") == "rag"
        assert classify_intent("retrieve the setup guide") == "rag"
        assert classify_intent("search my docs for API") == "rag"
        assert classify_intent("search my files for config") == "rag"
        assert classify_intent("what do my files say about X") == "rag"
        assert classify_intent("check my files for the report") == "rag"

    def test_chat_default(self):
        assert classify_intent("hello") == "chat"
        assert classify_intent("tell me a joke") == "chat"

    def test_calculator_genuine_math(self):
        assert classify_intent("what is 15% of 80") == "calculator"
        assert classify_intent("calculate 2 + 2") == "calculator"
        assert classify_intent("what's 10 times 5") == "calculator"
        assert classify_intent("2 + 2") == "calculator"

    def test_calculator_not_conversational_questions(self):
        """Questions starting with 'what's' or 'what is' but with no math go to chat."""
        assert classify_intent("what's the most controversial episode of South Park?") == "chat"
        assert classify_intent("What's better, the book or the film?") == "chat"
        assert classify_intent("what is the capital of France") == "chat"

    def test_empty(self):
        assert classify_intent("") == "chat"
        assert classify_intent("   ") == "chat"

    def test_app_launch(self):
        assert classify_intent("open firefox") == "app_launch"
        assert classify_intent("launch VS Code") == "app_launch"
        assert classify_intent("start terminal") == "app_launch"

    def test_media_control(self):
        assert classify_intent("play music") == "media_control"
        assert classify_intent("pause") == "media_control"
        assert classify_intent("mute") == "media_control"
        assert classify_intent("volume up") == "media_control"

    def test_system_command(self):
        assert classify_intent("lock my screen") == "system_command"
        assert classify_intent("suspend") == "system_command"
        assert classify_intent("reboot") == "system_command"
        assert classify_intent("shut down") == "system_command"

    def test_sys_monitor(self):
        assert classify_intent("why are my fans spinning") == "sys_monitor"
        assert classify_intent("what's using CPU") == "sys_monitor"
        assert classify_intent("system status") == "sys_monitor"

    def test_notes_phrasings(self):
        assert classify_intent("remind me to call mom") == "notes"
        assert classify_intent("remember to buy milk") == "notes"
        assert classify_intent("make a note get groceries") == "notes"
        assert classify_intent("note: buy eggs") == "notes"

    def test_mcp_app_keywords_route_to_chat(self):
        """Calendar, Gmail, Drive, Tasks queries use MCP tools, not browse."""
        assert classify_intent("check my Google Calendar for what I've got on this week") == "chat"
        assert classify_intent("what's on my calendar") == "chat"
        assert classify_intent("check my gmail") == "chat"
        assert classify_intent("show my emails") == "chat"  # "my emails" matches
        assert classify_intent("what's in my Google Drive") == "chat"

    def test_browse_disabled_falls_through(self):
        """When GERTY_BROWSE_ENABLED is False (default), browse keywords fall through to chat."""
        from unittest.mock import patch
        with patch("gerty.llm.router.GERTY_BROWSE_ENABLED", False):
            # "go to" matches BROWSE_KEYWORDS but we only return "browse" when enabled
            assert classify_intent("go to example.com") == "chat"

    def test_browse_when_enabled(self):
        """When GERTY_BROWSE_ENABLED is True, browse keywords return browse."""
        from unittest.mock import patch
        with patch("gerty.llm.router.GERTY_BROWSE_ENABLED", True):
            assert classify_intent("go to example.com") == "browse"
            assert classify_intent("check my GitHub notifications") == "browse"
            assert classify_intent("visit python.org") == "browse"


class TestClassifyWebIntentFallback:
    """Tests for LLM-based web intent fallback (chat -> web_lookup/web_research)."""

    def test_returns_web_lookup_when_ollama_says_so(self):
        ollama = MagicMock()
        ollama.is_available.return_value = True
        ollama.chat.return_value = "web_lookup"
        openrouter = MagicMock()
        assert _classify_web_intent_fallback("get me contact details for Acme", ollama, openrouter) == "web_lookup"

    def test_returns_web_research_when_ollama_says_so(self):
        ollama = MagicMock()
        ollama.is_available.return_value = True
        ollama.chat.return_value = "web_research"
        openrouter = MagicMock()
        assert _classify_web_intent_fallback("compare top CRM tools", ollama, openrouter) == "web_research"

    def test_returns_no_web_when_ollama_says_so(self):
        ollama = MagicMock()
        ollama.is_available.return_value = True
        ollama.chat.return_value = "no_web"
        openrouter = MagicMock()
        assert _classify_web_intent_fallback("tell me a joke", ollama, openrouter) == "no_web"

    def test_returns_no_web_when_ollama_unavailable(self):
        ollama = MagicMock()
        ollama.is_available.return_value = False
        openrouter = MagicMock()
        openrouter.is_available.return_value = False
        assert _classify_web_intent_fallback("any query", ollama, openrouter) == "no_web"

    def test_returns_no_web_on_exception(self):
        ollama = MagicMock()
        ollama.is_available.return_value = True
        ollama.chat.side_effect = Exception("timeout")
        openrouter = MagicMock()
        assert _classify_web_intent_fallback("any query", ollama, openrouter) == "no_web"


class TestParseTimerDuration:
    def test_minutes(self):
        assert parse_timer_duration("5 minutes") == 300
        assert parse_timer_duration("1 minute") == 60

    def test_hours(self):
        assert parse_timer_duration("2 hours") == 7200
        assert parse_timer_duration("1 hour") == 3600

    def test_seconds(self):
        assert parse_timer_duration("30 seconds") == 30

    def test_combined(self):
        assert parse_timer_duration("1 hour 30 minutes") == 5400

    def test_bare_number_assumes_minutes(self):
        assert parse_timer_duration("timer 5") == 300

    def test_number_words_stt(self):
        """STT may say 'five minutes' instead of '5 minutes'."""
        assert parse_timer_duration(normalize_time_words("five minutes")) == 300
        assert parse_timer_duration(normalize_time_words("twenty minutes")) == 1200
        assert parse_timer_duration(normalize_time_words("timer for ten minutes")) == 600

    def test_none_for_invalid(self):
        assert parse_timer_duration("no numbers") is None
        assert parse_timer_duration("") is None
