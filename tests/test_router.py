"""Tests for LLM router intent classification and parsing."""

from unittest.mock import MagicMock, patch

import pytest

from gerty.llm.router import (
    INTENT_CALENDAR,
    INTENT_CHAT,
    INTENT_MAINTENANCE,
    INTENT_SEARCH,
    PROVIDER_APP_UNAVAILABLE,
    PROVIDER_CHAT,
    PROVIDER_COMPLEX,
    PROVIDER_OPENCLAW,
    PROVIDER_TOOL,
    RoutingDecision,
    _classify_intent_impl,
    _classify_web_intent_fallback,
    _is_local_maintenance_command,
    apply_policy,
    classify_intent,
    classify_to_decision,
    parse_timer_duration,
    Router,
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

    def test_maintenance(self):
        assert classify_intent("maintenance summary") == "maintenance"
        assert classify_intent("create incident: OpenClaw timeout") == "maintenance"
        assert classify_intent("list incidents") == "maintenance"
        assert classify_intent("run diagnostics") == "maintenance"

    def test_personal_context(self):
        assert classify_intent("who am I") == "personal_context"
        assert classify_intent("what are my goals") == "personal_context"
        assert classify_intent("personal context") == "personal_context"
        assert classify_intent("my projects") == "personal_context"
        assert classify_intent("add idea: build a SaaS") == "personal_context"
        assert classify_intent("add goal: ship v2") == "personal_context"
        assert classify_intent("add project: Website") == "personal_context"
        assert classify_intent("update project status Gerty to paused") == "personal_context"
        assert classify_intent("my schedule") == "personal_context"

    def test_agent_designer_before_runner_and_factory(self):
        """Agent designer (design/improve/suggest) routes to agent_designer."""
        assert classify_intent("design agent: niche_finder - finds AI opportunities") == "agent_designer"
        assert classify_intent("improve agent market_researcher") == "agent_designer"
        assert classify_intent("suggest agent for: validating SaaS ideas") == "agent_designer"
        assert classify_intent("show agent design market_researcher") == "agent_designer"
        assert classify_intent("create from design niche_finder") == "agent_designer"

    def test_agent_runner_before_agent_factory(self):
        """Agent invocation (ask/run/use) routes to agent_runner; create/list/show to agent_factory."""
        assert classify_intent("ask agent market_researcher: summarize competitors") == "agent_runner"
        assert classify_intent("run agent builder: outline a landing page") == "agent_runner"
        assert classify_intent("use agent content_marketer: write a tagline") == "agent_runner"

    def test_agent_factory(self):
        assert classify_intent("create agent: market_researcher - researches markets") == "agent_factory"
        assert classify_intent("list agents") == "agent_factory"
        assert classify_intent("show agent builder") == "agent_factory"

    def test_intent_orchestrator_after_agent_commands(self):
        """Orchestrator keywords route to intent_orchestrator; direct commands still win."""
        assert classify_intent("help me explore tattoo AI business ideas") == "intent_orchestrator"
        assert classify_intent("help me organize this business idea properly") == "intent_orchestrator"
        assert classify_intent("I want to turn this into a real project") == "intent_orchestrator"
        assert classify_intent("build whatever agent we need for researching this") == "intent_orchestrator"
        assert classify_intent("if we do not have the right tool, propose one") == "intent_orchestrator"
        assert classify_intent("what is the best next step for this goal") == "intent_orchestrator"
        # Direct commands still win
        assert classify_intent("list agents") == "agent_factory"
        assert classify_intent("ask agent X: task") == "agent_runner"
        assert classify_intent("design agent: x - y") == "agent_designer"

    def test_maintenance_local_vs_broader(self):
        """Sprint 5a: local commands vs broader planning."""
        assert _is_local_maintenance_command("create incident: X") is True
        assert _is_local_maintenance_command("maintenance summary") is True
        assert _is_local_maintenance_command("maintenance") is True
        assert _is_local_maintenance_command("run diagnostics") is True
        assert _is_local_maintenance_command("what maintenance do I need to fix") is False
        assert _is_local_maintenance_command("how should I prioritize maintenance") is False

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

    def test_calendar_keywords_before_app_integration(self):
        """Calendar-specific phrases match CALENDAR_KEYWORDS first, return calendar intent."""
        assert classify_intent("what's on my calendar") == "calendar"
        assert classify_intent("check my calendar") == "calendar"
        assert classify_intent("check my Google Calendar for what I've got on this week") == "calendar"

    def test_app_integration_keywords_route_to_chat(self):
        """Gmail, Drive, Tasks (non-calendar) match APP_INTEGRATION_KEYWORDS, return chat."""
        assert classify_intent("check my gmail") == "chat"
        assert classify_intent("show my emails") == "chat"  # "my emails" matches
        assert classify_intent("what's in my Google Drive") == "chat"

    def test_browse_disabled_falls_through(self):
        """When browse_enabled is False, browse keywords fall through to chat."""
        dec = _classify_intent_impl("go to example.com", browse_enabled=False)
        assert dec.intent == "chat"

    def test_browse_when_enabled(self):
        """When browse_enabled is True, browse keywords return browse."""
        dec = _classify_intent_impl("go to example.com", browse_enabled=True)
        assert dec.intent == "browse"
        dec = _classify_intent_impl("check my GitHub notifications", browse_enabled=True)
        assert dec.intent == "browse"
        dec = _classify_intent_impl("visit python.org", browse_enabled=True)
        assert dec.intent == "browse"

    def test_date_whole_word_only(self):
        """'date' must be whole word; 'outdated', 'update' should not match date intent."""
        assert classify_intent("what's the date") == "date"
        assert classify_intent("outdated document") == "chat"
        assert classify_intent("update my system") == "chat"
        assert classify_intent("what date is the meeting") == "date"

    def test_classify_to_decision_returns_routing_decision(self):
        """classify_to_decision returns RoutingDecision with same intent as classify_intent."""
        dec = classify_to_decision("what time is it")
        assert isinstance(dec, RoutingDecision)
        assert dec.intent == "time"
        assert classify_intent("what time is it") == dec.intent

    def test_openclaw_direct(self):
        """Direct OpenClaw keywords bypass classifier for connection test."""
        assert classify_intent("list my skills") == "openclaw_direct"
        assert classify_intent("list skills") == "openclaw_direct"
        assert classify_intent("what can openclaw do") == "openclaw_direct"

    def test_pomodoro_stopwatch(self):
        """Pomodoro and stopwatch intents. Avoid timer ('minute') and app_launch prefixes."""
        assert classify_intent("pomodoro") == "pomodoro"
        assert classify_intent("pomodoro session") == "pomodoro"
        assert classify_intent("stopwatch") == "stopwatch"
        assert classify_intent("how long has it been") == "stopwatch"

    def test_units_random(self):
        """Units and random intents."""
        assert classify_intent("convert 5 miles to km") == "units"
        assert classify_intent("pick a random number") == "random"

    def test_calendar_vs_gmail_ordering(self):
        """Calendar keywords checked before app integration; gmail/drive go to chat."""
        # "what's on my calendar" in CALENDAR_KEYWORDS -> calendar
        assert classify_intent("what's on my calendar") == INTENT_CALENDAR
        # "check my gmail" in APP_INTEGRATION_KEYWORDS only -> chat
        assert classify_intent("check my gmail") == INTENT_CHAT


class TestApplyPolicy:
    """Tests for policy layer: apply_policy produces correct RoutingDecision."""

    def test_fast_path_tool(self):
        """Fast-path intents -> provider=tool when tool executor present."""
        dec = RoutingDecision(intent="time")
        out = apply_policy(
            dec,
            message="what time is it",
            openclaw_enabled=True,
            tool_executor_present=True,
            web_fallback_enabled=False,
        )
        assert out.provider == PROVIDER_TOOL
        assert out.tool_intent == "time"

    def test_openclaw_when_enabled(self):
        """Non-fast-path -> openclaw when enabled."""
        dec = RoutingDecision(intent="search")
        out = apply_policy(
            dec,
            message="search for python",
            openclaw_enabled=True,
            tool_executor_present=True,
            web_fallback_enabled=False,
        )
        assert out.provider == PROVIDER_OPENCLAW
        assert out.tool_intent is None

    def test_openclaw_calendar_fallback_flag(self):
        """Calendar intent with OpenClaw -> openclaw_fallback_calendar when tool present."""
        dec = RoutingDecision(intent="calendar")
        out = apply_policy(
            dec,
            message="what's on my calendar",
            openclaw_enabled=True,
            tool_executor_present=True,
            web_fallback_enabled=False,
        )
        assert out.provider == PROVIDER_OPENCLAW
        assert out.openclaw_fallback_calendar is True

    def test_chat_web_fallback_when_openclaw_disabled(self):
        """Chat + OpenClaw disabled + no app keywords -> run_web_fallback."""
        dec = RoutingDecision(intent="chat")
        out = apply_policy(
            dec,
            message="tell me a joke",
            openclaw_enabled=False,
            tool_executor_present=True,
            web_fallback_enabled=True,
        )
        assert out.provider == PROVIDER_CHAT
        assert out.run_web_fallback is True

    def test_app_unavailable_when_chat_and_app_keywords(self):
        """Chat + OpenClaw disabled + app keywords -> app_unavailable."""
        dec = RoutingDecision(intent="chat")
        out = apply_policy(
            dec,
            message="check my gmail",
            openclaw_enabled=False,
            tool_executor_present=True,
            web_fallback_enabled=True,
        )
        assert out.provider == PROVIDER_APP_UNAVAILABLE
        assert out.show_app_unavailable is True

    def test_complex_use_reasoning(self):
        """Complex intent -> provider=complex, use_reasoning."""
        dec = RoutingDecision(intent="complex")
        out = apply_policy(
            dec,
            message="explain quantum physics",
            openclaw_enabled=False,
            tool_executor_present=True,
            web_fallback_enabled=False,
        )
        assert out.provider == PROVIDER_COMPLEX
        assert out.use_reasoning is True

    def test_tool_intent_when_openclaw_disabled(self):
        """Search intent + OpenClaw disabled -> provider=tool."""
        dec = RoutingDecision(intent=INTENT_SEARCH)
        out = apply_policy(
            dec,
            message="search for python tutorial",
            openclaw_enabled=False,
            tool_executor_present=True,
            web_fallback_enabled=False,
        )
        assert out.provider == PROVIDER_TOOL
        assert out.tool_intent == INTENT_SEARCH


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


class TestRouterOpenClawOptionA:
    """Tests for Option A: everything to OpenClaw except fast-path; fallback to Gerty when unreachable."""

    @patch("gerty.llm.router.GERTY_OPENCLAW_ENABLED", True)
    def test_non_fast_path_routes_to_openclaw_when_enabled(self):
        """Search, research, browse, chat all go to OpenClaw when enabled."""
        with patch("gerty.openclaw.client.execute") as mock_execute:
            mock_execute.return_value = "Result from OpenClaw"
            tool_executor = MagicMock()
            router = Router(tool_executor=tool_executor)
            result = router.route("search for Python tutorial")
            assert result == "Result from OpenClaw"
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert call_args[0][0] == "search for Python tutorial"
            assert call_args[1].get("history") is None
            # system_context includes OPENCLAW_TOOL_INSTRUCTIONS (appended when custom_prompt is None)
            from gerty.llm.router import OPENCLAW_TOOL_INSTRUCTIONS
            assert call_args[1].get("system_context") == OPENCLAW_TOOL_INSTRUCTIONS

    @patch("gerty.llm.router.GERTY_OPENCLAW_ENABLED", True)
    def test_openclaw_receives_history_and_system_context(self):
        """OpenClaw execute receives history and custom_prompt with tool instructions."""
        from gerty.llm.router import OPENCLAW_TOOL_INSTRUCTIONS

        with patch("gerty.openclaw.client.execute") as mock_execute:
            mock_execute.return_value = "Chat response"
            router = Router(tool_executor=MagicMock())
            history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
            result = router.route("we're testing", history=history, custom_prompt="You are Gerty.")
            assert result == "Chat response"
            mock_execute.assert_called_once_with(
                "we're testing",
                history=history,
                system_context="You are Gerty." + OPENCLAW_TOOL_INSTRUCTIONS,
            )

    @patch("gerty.llm.router.GERTY_OPENCLAW_ENABLED", True)
    def test_fallback_to_gerty_when_openclaw_unavailable(self):
        """When OpenClaw returns unavailable msg, fall through to Gerty chat."""
        from gerty.openclaw.client import OPENCLAW_UNAVAILABLE_MSG

        with patch("gerty.openclaw.client.execute") as mock_execute:
            mock_execute.return_value = OPENCLAW_UNAVAILABLE_MSG
            router = Router(tool_executor=MagicMock())
            router.ollama = MagicMock()
            router.ollama.is_available.return_value = True
            router.ollama.chat.return_value = "Ollama chat response"
            result = router.route("hello", history=[])
            assert result == "Ollama chat response"
            mock_execute.assert_called_once()

    @patch("gerty.llm.router.GERTY_OPENCLAW_ENABLED", False)
    def test_search_falls_back_to_gerty_when_openclaw_disabled(self):
        """When OpenClaw disabled, search goes to tool executor or OpenRouter."""
        tool_executor = MagicMock(return_value="DuckDuckGo results")
        router = Router(tool_executor=tool_executor)
        with patch("gerty.llm.router.GERTY_WEB_INTENT_FALLBACK", False):
            result = router.route("search for Python tutorial")
        tool_executor.assert_called_with("search", "search for Python tutorial")
        assert result == "DuckDuckGo results"

    @patch("gerty.llm.router.GERTY_OPENCLAW_ENABLED", True)
    def test_fast_path_skips_openclaw(self):
        """Fast-path intents (time, alarm, etc.) go to tool executor, not OpenClaw."""
        with patch("gerty.openclaw.client.execute") as mock_execute:
            tool_executor = MagicMock(return_value="14:30")
            router = Router(tool_executor=tool_executor)
            result = router.route("what time is it")
            assert result == "14:30"
            mock_execute.assert_not_called()
            tool_executor.assert_called_with("time", "what time is it")

    def test_maintenance_routes_to_tool(self):
        """Local maintenance commands route to tool executor."""
        tool_executor = MagicMock(return_value="# Maintenance summary\n\n## Incidents: 0")
        router = Router(tool_executor=tool_executor)
        result = router.route("maintenance summary")
        tool_executor.assert_called_with("maintenance", "maintenance summary")
        assert "Maintenance" in result

    def test_maintenance_standalone_routes_to_tool(self):
        """Standalone 'maintenance' preserves Sprint 5 behavior (Sprint 5a)."""
        tool_executor = MagicMock(return_value="Maintenance tool. I can: ...")
        router = Router(tool_executor=tool_executor)
        result = router.route("maintenance")
        tool_executor.assert_called_with("maintenance", "maintenance")

    def test_maintenance_broader_routes_to_chat(self):
        """Broader maintenance (planning, analysis) routes to chat, not tool (Sprint 5a)."""
        tool_executor = MagicMock()
        with patch("gerty.llm.router.GERTY_OPENCLAW_ENABLED", False):
            router = Router(tool_executor=tool_executor)
            router.ollama = MagicMock()
            router.ollama.is_available.return_value = True
            router.ollama.chat.return_value = "I can help with maintenance planning."
            # "what maintenance do I need" → maintenance intent but not local command → chat
            assert _is_local_maintenance_command("what maintenance do I need to fix") is False
            result = router.route("what maintenance do I need to fix", history=[])
            tool_executor.assert_not_called()
            assert result == "I can help with maintenance planning."


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
