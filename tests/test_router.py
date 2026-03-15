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
    enrich_decision_with_taxonomy,
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

    def test_project_graph_before_personal_context(self):
        """Project graph (create project, add task, run task) routes to project_graph."""
        assert classify_intent("create project: AI Tattoo SaaS - explore digital product") == "project_graph"
        assert classify_intent("list projects") == "project_graph"
        assert classify_intent("show project ai_tattoo_saas") == "project_graph"
        assert classify_intent("add task to ai_tattoo_saas: research market") == "project_graph"
        assert classify_intent("update task task_001 in ai_tattoo_saas to in_progress") == "project_graph"
        assert classify_intent("assign agent market_researcher to task task_001 in ai_tattoo_saas") == "project_graph"
        assert classify_intent("run task task_001 in ai_tattoo_saas") == "project_graph"
        assert classify_intent("run next task for ai_tattoo_saas") == "project_graph"
        assert classify_intent("project summary ai_tattoo_saas") == "project_graph"
        assert classify_intent("next task for ai_tattoo_saas") == "project_graph"

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

    def test_capability_registry_before_orchestrator(self):
        """Capability registry commands route to capability_registry; checked before orchestrator."""
        assert classify_intent("list capabilities") == "capability_registry"
        assert classify_intent("show capability project_graph") == "capability_registry"
        assert classify_intent("what capabilities do you already have") == "capability_registry"
        assert classify_intent("what can you do for this: research AI ideas") == "capability_registry"

    def test_intent_orchestrator_after_agent_commands(self):
        """Orchestrator keywords route to intent_orchestrator; direct commands still win."""
        assert classify_intent("help me explore tattoo AI business ideas") == "intent_orchestrator"
        assert classify_intent("help me organize this business idea properly") == "intent_orchestrator"
        assert classify_intent("I want to turn this into a real project") == "intent_orchestrator"
        assert classify_intent("build whatever agent we need for researching this") == "intent_orchestrator"
        assert classify_intent("if we do not have the right tool, propose one") == "intent_orchestrator"
        assert classify_intent("what is the best next step for this goal") == "intent_orchestrator"
        assert classify_intent("what is the best internal path for this") == "intent_orchestrator"
        assert classify_intent("list orchestration plans") == "intent_orchestrator"
        assert classify_intent("show orchestration plan 20250313-123456-plan") == "intent_orchestrator"
        # Direct commands still win
        assert classify_intent("list agents") == "agent_factory"
        assert classify_intent("ask agent X: task") == "agent_runner"
        assert classify_intent("design agent: x - y") == "agent_designer"

    def test_agent_designer_list_show_artifact_commands(self):
        """list agent designs and show agent design artifact route to agent_designer."""
        assert classify_intent("list agent designs") == "agent_designer"
        assert classify_intent("show agent design artifact 20250313-123456-niche_finder") == "agent_designer"

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
        """Phase 3.1: Gmail/Drive route to email/drive intents; Tasks (no dedicated intent) still chat."""
        assert classify_intent("check my gmail") == "email"
        assert classify_intent("show my emails") == "email"
        assert classify_intent("what's in my Google Drive") == "drive"
        # Google Tasks has no dedicated intent yet -> chat via APP_INTEGRATION_KEYWORDS
        assert classify_intent("check my tasks") == "chat"

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

    def test_email_intent_phase_31(self):
        """Phase 3.1: Email as first-class intent."""
        assert classify_intent("check if Tom emailed me") == "email"
        assert classify_intent("summarise my unread emails") == "email"
        assert classify_intent("reply and say I can do Thursday") == "email"

    def test_drive_intent_phase_31(self):
        """Phase 3.1: Drive as first-class intent."""
        assert classify_intent("find my latest invoice") == "drive"
        assert classify_intent("look for the Gerty planning doc") == "drive"

    def test_gerty_health_maintenance(self):
        """Phase 3.1: Gerty health routes to maintenance."""
        assert classify_intent("check Gerty health") == "maintenance"
        assert classify_intent("show me Gerty health") == "maintenance"
        assert classify_intent("run Gerty diagnostics") == "maintenance"

    def test_calendar_vs_gmail_ordering(self):
        """Calendar keywords checked before email/drive; gmail/drive route to email/drive (Phase 3.1)."""
        # "what's on my calendar" in CALENDAR_KEYWORDS -> calendar
        assert classify_intent("what's on my calendar") == INTENT_CALENDAR
        # "check my gmail" in EMAIL_KEYWORDS -> email (Phase 3.1 first-class intent)
        assert classify_intent("check my gmail") == "email"

    def test_can_you_check_what_ive_got_on_routes_to_calendar(self):
        """Phase 3.0B regression: natural paraphrase must route to calendar read, not chat.
        Stabilization: single-backend mode routes calendar to OpenClaw/gog."""
        msg = "can you check what ive got on next week"
        assert classify_intent(msg) == INTENT_CALENDAR
        dec = classify_to_decision(msg)
        out = apply_policy(
            dec,
            message=msg,
            openclaw_enabled=True,
            tool_executor_present=True,
            web_fallback_enabled=True,
        )
        assert out.provider == PROVIDER_OPENCLAW
        assert out.execution_path == "openclaw:gog"

    def test_six_calendar_read_phrasings_resolve_to_calendar(self):
        """Stabilization Reset §2.3: exact phrase dependence is a bug. All must resolve to calendar."""
        phrasings = [
            "what have I got on next week",
            "what's on next week",
            "what am I doing next week",
            "check my calendar for next week",
            "can you check what ive got on next week",
            "my schedule next week",
        ]
        for msg in phrasings:
            assert classify_intent(msg) == INTENT_CALENDAR, f"Failed for: {msg!r}"


class TestEnrichDecisionWithTaxonomy:
    """Phase 3.1: enrich_decision_with_taxonomy adds taxonomy fields."""

    def test_enrich_adds_primary_intent_and_requires_tool(self):
        dec = RoutingDecision(intent="calendar")
        enriched = enrich_decision_with_taxonomy(dec, "what have I got on tomorrow?")
        assert enriched.primary_intent == "calendar_check"
        assert enriched.requires_tool is True
        assert enriched.capability_owner == "google_workspace_calendar"

    def test_enrich_email_reply_requires_confirmation(self):
        dec = RoutingDecision(intent="email")
        enriched = enrich_decision_with_taxonomy(dec, "reply and say I can do Thursday")
        assert enriched.primary_intent == "email_reply"
        assert enriched.requires_confirmation is True
        assert enriched.safety_level == "write_external"


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

    def test_calendar_routes_to_openclaw_single_backend(self):
        """Stabilization: calendar read -> OpenClaw/gog when single-backend (GERTY_GOOGLE_NATIVE_ENABLED=0)."""
        dec = RoutingDecision(intent="calendar")
        out = apply_policy(
            dec,
            message="what's on my calendar",
            openclaw_enabled=True,
            tool_executor_present=True,
            web_fallback_enabled=False,
        )
        assert out.provider == PROVIDER_OPENCLAW
        assert "gog" in (out.execution_path or "")

    @patch("gerty.llm.router.GERTY_GOOGLE_NATIVE_ENABLED", True)
    def test_calendar_routes_to_native_when_explicitly_enabled(self):
        """Calendar read -> native tool when GERTY_GOOGLE_NATIVE_ENABLED=1."""
        dec = RoutingDecision(intent="calendar")
        out = apply_policy(
            dec,
            message="what's on my calendar",
            openclaw_enabled=True,
            tool_executor_present=True,
            web_fallback_enabled=False,
        )
        assert out.provider == PROVIDER_TOOL

    def test_email_routes_to_openclaw_single_backend(self):
        """Stabilization: email read -> OpenClaw/gog when single-backend."""
        dec = RoutingDecision(intent="email")
        out = apply_policy(
            dec,
            message="check if Tom emailed me",
            openclaw_enabled=True,
            tool_executor_present=True,
            web_fallback_enabled=False,
        )
        assert out.provider == PROVIDER_OPENCLAW

    def test_drive_routes_to_openclaw_single_backend(self):
        """Stabilization: drive read -> OpenClaw/gog when single-backend."""
        dec = RoutingDecision(intent="drive")
        out = apply_policy(
            dec,
            message="find my latest invoice",
            openclaw_enabled=True,
            tool_executor_present=True,
            web_fallback_enabled=False,
        )
        assert out.provider == PROVIDER_OPENCLAW

    def test_calendar_create_routes_to_openclaw(self):
        """Phase 3.0A: Write intent (calendar create) -> OpenClaw/gog, never native."""
        dec = RoutingDecision(intent="calendar")
        out = apply_policy(
            dec,
            message="add a meeting for Wednesday at 3pm",
            openclaw_enabled=True,
            tool_executor_present=True,
            web_fallback_enabled=False,
        )
        assert out.provider == PROVIDER_OPENCLAW
        assert "gog" in (out.execution_path_reason or "")

    def test_email_reply_routes_to_openclaw(self):
        """Phase 3.0A: Write intent (email reply) -> OpenClaw/gog, never native."""
        dec = RoutingDecision(intent="email")
        out = apply_policy(
            dec,
            message="reply to that email and say I can do Thursday",
            openclaw_enabled=True,
            tool_executor_present=True,
            web_fallback_enabled=False,
        )
        assert out.provider == PROVIDER_OPENCLAW

    def test_write_intent_fails_clearly_when_openclaw_disabled(self):
        """Phase 3.0A: Write intent + OpenClaw disabled -> fail clearly, not native."""
        dec = RoutingDecision(intent="calendar")
        out = apply_policy(
            dec,
            message="add a meeting for tomorrow",
            openclaw_enabled=False,
            tool_executor_present=True,
            web_fallback_enabled=False,
        )
        assert out.provider == PROVIDER_APP_UNAVAILABLE
        assert out.show_app_unavailable is True
        assert out.unavailable_msg_override is not None
        assert "gog" in (out.unavailable_msg_override or "").lower()

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
        """OpenClaw execute receives history and custom_prompt for search (OpenClaw path)."""
        from gerty.llm.router import OPENCLAW_TOOL_INSTRUCTIONS

        with patch("gerty.openclaw.client.execute") as mock_execute:
            mock_execute.return_value = "Chat response"
            router = Router(tool_executor=MagicMock())
            history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
            result = router.route("search for python", history=history, custom_prompt="You are Gerty.")
            assert result == "Chat response"
            mock_execute.assert_called_once_with(
                "search for python",
                history=history,
                system_context="You are Gerty." + OPENCLAW_TOOL_INSTRUCTIONS,
            )

    @patch("gerty.llm.router.GERTY_OPENCLAW_ENABLED", True)
    @patch("gerty.llm.router.GERTY_GOOGLE_NATIVE_ENABLED", True)
    def test_calendar_routes_to_native_tool(self):
        """Calendar routes to native GoogleWorkspaceTool when GERTY_GOOGLE_NATIVE_ENABLED=1."""
        tool_executor = MagicMock(return_value="You have 2 events today.")
        router = Router(tool_executor=tool_executor)
        result = router.route("check my calendar", history=[])
        assert result == "You have 2 events today."
        tool_executor.assert_called_once()
        assert tool_executor.call_args[0][0] == "calendar"

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
        mock_response = "I can help with maintenance planning."
        with patch("gerty.llm.router.GERTY_OPENCLAW_ENABLED", False):
            with patch("gerty.settings.load") as mock_settings:
                mock_settings.return_value = {"provider": "local", "local_model": "llama3.2"}
                router = Router(tool_executor=tool_executor)
                router.ollama = MagicMock()
                router.ollama.is_available.return_value = True
                router.ollama.chat.return_value = mock_response
                # "what maintenance do I need" → maintenance intent but not local command → chat
                assert _is_local_maintenance_command("what maintenance do I need to fix") is False
                result = router.route("what maintenance do I need to fix", history=[])
                tool_executor.assert_not_called()
                assert result == mock_response


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
