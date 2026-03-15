"""Model router: intent classification, tool dispatch, Ollama/OpenRouter selection."""

import logging
import re
import time
import uuid
from dataclasses import dataclass
from typing import Callable, Iterator

from gerty.observability import log_event, log_friction, log_routing_trace, maybe_log_user_friction
from gerty.prompt_metrics import (
    approx_tokens,
    build_openrouter_messages,
    log_prompt_metrics,
)

from gerty.config import (
    GERTY_BROWSE_ENABLED,
    GERTY_EXECUTION_BOUNDARY_ENABLED,
    GERTY_GOOGLE_NATIVE_ENABLED,
    GERTY_OPENCLAW_ENABLED,
    GERTY_WEB_INTENT_FALLBACK,
    LOCKED_OPENROUTER_MODEL,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OLLAMA_CHAT_MODEL,
    OLLAMA_REASONING_MODEL,
)
from gerty.llm.ollama_client import OllamaClient
from gerty.llm.openrouter_client import OpenRouterClient
from gerty.grounded_planning import (
    build_planning_injection,
    get_planning_block_for_message,
)
from gerty.inspection_first import (
    build_inspection_first_injection,
    get_inspection_block_for_message,
)
from gerty.execution_boundary import select_execution_path
from gerty.intent_taxonomy import (
    PRIMARY_INTENT_CALENDAR_CREATE,
    PRIMARY_INTENT_CALENDAR_UPDATE,
    PRIMARY_INTENT_EMAIL_REPLY,
    PRIMARY_INTENT_EMAIL_SEND,
    resolve_taxonomy,
)
from gerty.model_routing import select_model_for_request
from gerty.openclaw.client import OPENCLAW_UNAVAILABLE_MSG
from gerty.utils.math_extract import extract_math

logger = logging.getLogger(__name__)


def _get_planning_or_inspection_context(message: str) -> tuple[str, dict, bool]:
    """
    Get injection and metrics for planning/inspection context.
    Inspection-first takes precedence over grounded planning when both could apply.
    Returns (injection, metrics_dict, is_inspection_first).
    is_inspection_first: True when inspection-first triggered (injection used on all paths).
    """
    inspection_result = get_inspection_block_for_message(message)
    if inspection_result:
        injection = build_inspection_first_injection(inspection_result)
        # v3: Check if grounded planning would also have matched (inspection won precedence)
        planning_would_trigger = False
        try:
            from gerty.grounded_planning import should_use_grounded_planning_mode
            planning_would_trigger, _ = should_use_grounded_planning_mode(message)
        except Exception:
            pass
        metrics = {
            "inspection_first_mode_triggered": True,
            "inspection_reason": inspection_result.trigger_reason,
            "inspection_detection_reason": inspection_result.trigger_reason,
            "inspected_sources": inspection_result.sources_used,
            "extracted_sections": [
                f"{s}:{h}" for s, h in (inspection_result.extracted_headings or [])
            ][:10],
            "factual_summary_chars": len(inspection_result.factual_summary),
            "capability_registry_used": inspection_result.capability_registry_used,
            "planning_mode_triggered": False,
            "summary_signals_used": list(getattr(inspection_result, "summary_signals_used", ())),
            "recommendation_basis": getattr(inspection_result, "recommendation_basis", ""),
            "backlog_signals_influenced": getattr(inspection_result, "backlog_signals_influenced", False),
            "live_validation_signals_influenced": getattr(inspection_result, "live_validation_signals_influenced", False),
            "inspection_won_over_planning": planning_would_trigger,
        }
        log_event(
            "inspection_first_mode_triggered",
            reason=inspection_result.trigger_reason,
            sources=inspection_result.sources_used,
            capability_registry_used=inspection_result.capability_registry_used,
            summary_signals=getattr(inspection_result, "summary_signals_used", ()),
            backlog_influenced=getattr(inspection_result, "backlog_signals_influenced", False),
            live_validation_influenced=getattr(inspection_result, "live_validation_signals_influenced", False),
            inspection_won_over_planning=planning_would_trigger,
        )
        return injection, metrics, True

    planning_result = get_planning_block_for_message(message)
    if planning_result:
        injection = build_planning_injection(planning_result)
        metrics = {
            "planning_mode_triggered": True,
            "planning_sources_used": planning_result.sources_used,
            "planning_context_chars": planning_result.total_chars,
            "planning_route_reason": planning_result.trigger_reason,
            "planning_detection_reason": planning_result.trigger_reason,
            "planning_sources_considered": list(getattr(planning_result, "sources_considered", []) or []),
            "planning_extracted_headings": [
                f"{s}:{h}" for s, h in (getattr(planning_result, "extracted_headings", ()) or ())
            ][:10],
            "inspection_first_mode_triggered": False,
        }
        log_event("grounded_planning_triggered", reason=planning_result.trigger_reason, sources=planning_result.sources_used)
        return injection, metrics, False

    return "", {}, False

# Intent labels (Sprint 2a) — explicit constants for classification
INTENT_APP_LAUNCH = "app_launch"
INTENT_SCREEN_VISION = "screen_vision"
INTENT_SYS_MONITOR = "sys_monitor"
INTENT_MEDIA_CONTROL = "media_control"
INTENT_SYSTEM_COMMAND = "system_command"
INTENT_TIMER = "timer"
INTENT_TIMEZONE = "timezone"
INTENT_WEATHER = "weather"
INTENT_CALENDAR = "calendar"
INTENT_EMAIL = "email"
INTENT_DRIVE = "drive"
INTENT_RAG = "rag"
INTENT_RESEARCH = "research"
INTENT_OPENCLAW_DIRECT = "openclaw_direct"
INTENT_SEARCH = "search"
INTENT_POMODORO = "pomodoro"
INTENT_STOPWATCH = "stopwatch"
INTENT_TIME = "time"
INTENT_DATE = "date"
INTENT_CALCULATOR = "calculator"
INTENT_UNITS = "units"
INTENT_RANDOM = "random"
INTENT_NOTES = "notes"
INTENT_ALARM = "alarm"
INTENT_COMPLEX = "complex"
INTENT_BROWSE = "browse"
INTENT_MAINTENANCE = "maintenance"
INTENT_PERSONAL_CONTEXT = "personal_context"
INTENT_AGENT_FACTORY = "agent_factory"
INTENT_AGENT_RUNNER = "agent_runner"
INTENT_AGENT_DESIGNER = "agent_designer"
INTENT_ORCHESTRATOR = "intent_orchestrator"
INTENT_PROJECT_GRAPH = "project_graph"
INTENT_OPPORTUNITY_SCANNER = "opportunity_scanner"
INTENT_CAPABILITY_REGISTRY = "capability_registry"
INTENT_CHAT = "chat"

ALL_INTENTS = (
    INTENT_APP_LAUNCH,
    INTENT_SCREEN_VISION,
    INTENT_SYS_MONITOR,
    INTENT_MEDIA_CONTROL,
    INTENT_SYSTEM_COMMAND,
    INTENT_TIMER,
    INTENT_TIMEZONE,
    INTENT_WEATHER,
    INTENT_CALENDAR,
    INTENT_EMAIL,
    INTENT_DRIVE,
    INTENT_RAG,
    INTENT_RESEARCH,
    INTENT_OPENCLAW_DIRECT,
    INTENT_SEARCH,
    INTENT_POMODORO,
    INTENT_STOPWATCH,
    INTENT_TIME,
    INTENT_DATE,
    INTENT_CALCULATOR,
    INTENT_UNITS,
    INTENT_RANDOM,
    INTENT_NOTES,
    INTENT_ALARM,
    INTENT_COMPLEX,
    INTENT_BROWSE,
    INTENT_MAINTENANCE,
    INTENT_PERSONAL_CONTEXT,
    INTENT_AGENT_FACTORY,
    INTENT_AGENT_RUNNER,
    INTENT_AGENT_DESIGNER,
    INTENT_ORCHESTRATOR,
    INTENT_PROJECT_GRAPH,
    INTENT_OPPORTUNITY_SCANNER,
    INTENT_CAPABILITY_REGISTRY,
    INTENT_CHAT,
)


# Provider / action labels for policy layer
PROVIDER_TOOL = "tool"
PROVIDER_OPENCLAW = "openclaw"
PROVIDER_CHAT = "chat"
PROVIDER_APP_UNAVAILABLE = "app_unavailable"
PROVIDER_COMPLEX = "complex"


@dataclass(frozen=True)
class RoutingDecision:
    """
    Result of classification + policy. Execution layer consumes this.
    Phase 3.1 (FAR-002): Extended with primary_intent, requires_tool, capability_owner, etc.
    """
    intent: str
    provider: str = PROVIDER_CHAT
    tool_intent: str | None = None
    run_web_fallback: bool = False
    use_reasoning: bool = False
    show_app_unavailable: bool = False
    unavailable_msg_override: str | None = None  # Override when provider is app_unavailable
    execution_path: str = "native"  # native | openclaw (Execution Boundary v1)
    execution_path_reason: str = ""
    # Phase 3.1 (FAR-002, FAR-003, FAR-004)
    primary_intent: str | None = None
    secondary_intent: str | None = None
    intent_confidence: float = 0.0
    requires_tool: bool = False
    requires_confirmation: bool = False
    capability_owner: str | None = None
    tool_family: str | None = None
    safety_level: str = "read_only"


# Tool intents: use tool executor (Gerty tools)
TOOL_INTENTS = (
    INTENT_TIME,
    INTENT_DATE,
    INTENT_ALARM,
    INTENT_TIMER,
    INTENT_CALCULATOR,
    INTENT_UNITS,
    INTENT_RANDOM,
    INTENT_NOTES,
    INTENT_STOPWATCH,
    INTENT_TIMEZONE,
    INTENT_WEATHER,
    INTENT_RAG,
    INTENT_SEARCH,
    INTENT_BROWSE,
    INTENT_POMODORO,
    INTENT_APP_LAUNCH,
    INTENT_MEDIA_CONTROL,
    INTENT_SYSTEM_COMMAND,
    INTENT_SYS_MONITOR,
    INTENT_SCREEN_VISION,
    INTENT_MAINTENANCE,
    INTENT_PERSONAL_CONTEXT,
    INTENT_AGENT_FACTORY,
    INTENT_AGENT_RUNNER,
    INTENT_AGENT_DESIGNER,
    INTENT_ORCHESTRATOR,
    INTENT_PROJECT_GRAPH,
    INTENT_OPPORTUNITY_SCANNER,
    INTENT_CAPABILITY_REGISTRY,
)

# Fast path: instant Gerty tools—skip OpenClaw classifier
# Calendar routes to OpenClaw (gog skill); NOT in FAST_PATH
# Maintenance: NOT in FAST_PATH; policy routes local commands to tool, broader to chat (Sprint 5a)
FAST_PATH_INTENTS = (
    INTENT_TIME,
    INTENT_DATE,
    INTENT_ALARM,
    INTENT_TIMER,
    INTENT_CALCULATOR,
    INTENT_UNITS,
    INTENT_NOTES,
    INTENT_STOPWATCH,
    INTENT_TIMEZONE,
    INTENT_WEATHER,
    INTENT_RANDOM,
    INTENT_RAG,
    INTENT_PERSONAL_CONTEXT,
    INTENT_AGENT_FACTORY,
    INTENT_AGENT_RUNNER,
    INTENT_AGENT_DESIGNER,
    INTENT_ORCHESTRATOR,
    INTENT_PROJECT_GRAPH,
    INTENT_OPPORTUNITY_SCANNER,
)

# Keywords for intent classification
# Explicit time queries only—bare "time" was too broad ("do we have time", "it's time to set up")
TIME_KEYWORDS = ["what time", "current time", "what's the time", "what time is it", "tell me the time"]
DATE_KEYWORDS = ["date", "what date", "today's date", "what day", "what's the date"]
ALARM_KEYWORDS = [
    "alarm", "set alarm", "wake me", "remind me at",
    "alarm for", "wake up", "set an alarm",
    "wake me up", "remind me", "alarm at",
]
TIMER_KEYWORDS = [
    "timer", "set timer", "countdown", "timer for",
    "minute timer", "minute", "second timer",
    "start a timer", "countdown for",
]
CALC_KEYWORDS = ["calculate", "calculator", "what is", "what's", "compute", "+", "*", "% of"]
UNIT_KEYWORDS = ["convert", "kilograms to", "miles to", "fahrenheit to", "celsius to"]
RANDOM_KEYWORDS = ["flip", "coin", "roll", "dice", "random", "pick", "choose"]
NOTES_KEYWORDS = [
    "note:", "note ", "notes", "remember", "add note", "remind me", "make a note", "make note",
    # FAR-005 paraphrase coverage
    "add this idea", "save this to", "save this under", "save this note", "note this down",
    "record this", "take a note", "store this in notes", "add to notes", "add a note",
]
STOPWATCH_KEYWORDS = ["stopwatch", "how long has", "elapsed"]
TIMEZONE_KEYWORDS = ["time in", "timezone", "time zone", "what time in"]
WEATHER_KEYWORDS = ["weather", "forecast", "temperature"]
CALENDAR_KEYWORDS = [
    "calendar", "my calendar", "check my calendar", "what's on my calendar",
    "my schedule", "calendar for", "check calendar", "what have i got on",
    "what ive got on", "what i've got on",  # contractions (Phase 3.0B)
    "what do i have on", "what's on", "schedule for", "schedule",
    # FAR-005 paraphrase coverage
    "am i busy", "am i free", "do i have anything on", "what's my next",
    "what's coming up", "diary", "next event", "anything on",
    # Natural paraphrases (Phase 3.0B)
    "what have i got coming up", "what am i doing",
    "put a ", "appointment", "add a meeting", "add meeting", "block ",
    "move that", "move meeting", "reschedule", "meeting to",
]
# Phase 3.1: Email and Drive as first-class intents (FAR-001)
EMAIL_KEYWORDS = [
    "email", "emails", "gmail", "inbox", "check my email", "check my gmail",
    "my emails", "my inbox", "read my email", "read my emails", "check emails",
    "latest emails", "emailed me", "emailed", "email from", "reply and say",
    "send an email", "send email", "summarise my unread", "summarize my unread",
    "unread emails", "find the last email", "find the email from", "check if tom",
    "tom emailed", "summarise my email", "summarize my email",
    # FAR-005 paraphrase coverage
    "any emails from", "did tom email", "search my inbox", "look for emails",
    "find emails from", "look up emails", "check if i have mail",
    "summarize unread", "summarise unread",
    "have unread", "what do i have unread",
]
DRIVE_KEYWORDS = [
    "drive", "google drive", "my drive", "my documents", "check my drive",
    "find my latest", "find my ", "latest invoice", "open the file",
    "file i worked on", "file i was using", "look for the ", "gerty notes",
    "gerty planning", "summarise the latest", "summarize the latest",
    "planning doc", "strategy document", "in drive",
    # FAR-005 paraphrase coverage
    "search for my invoice", "where's my latest", "search drive", "locate the",
    "find that planning", "where is the", "newest invoice", "find the newest",
]
RAG_KEYWORDS = [
    "check documentation", "check docs", "check my docs",
    "retrieve", "search my docs", "search documentation",
    "look in my docs", "look in documentation", "find in docs",
    "what do my documents say", "what does my documentation say",
    "search my files", "what do my files say", "look in my files",
    "check my files", "check files for",
]
SEARCH_KEYWORDS = ["search for", "search ", "look up", "google"]
# Web lookup: queries needing current info but without explicit "search" keywords
WEB_LOOKUP_KEYWORDS = [
    "contact details", "contact info", "get me", "find me",
    "when is", "showtimes", "opening hours", "phone number",
    "address of", "where can i find", "who owns", "can you find",
    "can you get me", "look up the", "what's the phone", "what's the address",
]
POMODORO_KEYWORDS = ["pomodoro"]
MAINTENANCE_KEYWORDS = [
    "maintenance",
    "create incident",
    "log incident",
    "create proposal",
    "maintenance task",
    "maintenance status",
    "maintenance summary",
    "list incidents",
    "list proposals",
    "list tasks",
    "list releases",
    "run diagnostics",
    "gerty diagnostics",
    "collect logs",
    "recent logs",
    "gerty health",
    "check gerty",
    "system health",
    "show me gerty",
    # FAR-005 paraphrase coverage
    "health check",
    "gerty status",
    "gerty ok",
    "how's gerty",
    "gerty healthy",
    "verify gerty",
    "gerty is working",
    "check if gerty",
]
# Local maintenance: explicit commands that route to tool. Broader maintenance (planning, analysis) goes to chat.
PERSONAL_CONTEXT_KEYWORDS = [
    "who am i",
    "who is liam",
    "about me",
    "my goals",
    "my projects",
    "personal context",
    "what are my goals",
    "what are my projects",
    "context summary",
    "remind me about liam",
    "remind me about my goals",
    "remind me about my projects",
    "add idea",
    "add goal",
    "add project",
    "update project status",
    "update goal status",
    "add preference note",
    "add business idea",
    "add business concept",
    "my schedule",
    "work schedule",
    # FAR-005 paraphrase coverage
    "focus on today",
    "what should i focus on",
]
# Agent designer: design/improve/suggest — check BEFORE agent_runner and agent_factory
AGENT_DESIGNER_KEYWORDS = [
    "design agent",
    "improve agent",
    "suggest agent",
    "show agent design",
    "show agent design artifact",
    "list agent designs",
    "create from design",
]
# Agent invocation: ask/run/use agent X — check BEFORE agent_factory
AGENT_RUNNER_KEYWORDS = [
    "ask agent",
    "run agent",
    "use agent",
]
AGENT_FACTORY_KEYWORDS = [
    "create agent",
    "new agent",
    "build agent",
    "list agents",
    "show agent",
]
# Project graph: create/list/show projects, add/update tasks, run tasks (check before personal_context)
PROJECT_GRAPH_KEYWORDS = [
    "create project",
    "list projects",
    "show project",
    "add task",
    "update task",
    "assign agent",
    "run next task",
    "run task",
    "project summary",
    "next task",
]
# Opportunity scanner: discover, record, summarize opportunities
# "to opportunity" matches "assign agent X to opportunity Y" (before project graph's "assign agent")
OPPORTUNITY_SCANNER_KEYWORDS = [
    "to opportunity",
    "create opportunity",
    "list opportunities",
    "show opportunity",
    "opportunity summary",
    "opportunity research summary",
    "score opportunity",
    "research opportunity",
    "suggest opportunity status",
    "next step for opportunity",
    "create project from opportunity",
]
# Capability registry: list/show capabilities (check before orchestrator so "list capabilities" wins)
CAPABILITY_REGISTRY_KEYWORDS = [
    "list capabilities",
    "show capability",
    "what capabilities do you already have",
    "what capabilities do you have",
    "what can you do for this",
    "what can you do for",
]
# Intent orchestrator: high-level outcome requests (check after agent_* so direct commands win)
ORCHESTRATOR_KEYWORDS = [
    "help me explore",
    "help me organize",
    "turn this into",
    "build whatever agent",
    "if we don't have the right tool",
    "if we do not have the right tool",
    "propose one",
    "best next step",
    "what's the best way to",
    "what is the best next step",
    "organize this",
    "what should i do",
    "how do i get started",
    "i want to turn this into",
    "list orchestration plans",
    "show orchestration plan",
    "what is the best internal path for this",
    "what is the best internal path for",
]
LOCAL_MAINTENANCE_PATTERNS = (
    "create incident",
    "log incident",
    "gerty diagnostics",
    "create proposal",
    "create task",
    "create release",
    "list incidents",
    "list proposals",
    "list tasks",
    "list releases",
    "maintenance summary",
    "maintenance status",
    "collect logs",
    "recent logs",
    "run diagnostics",
)
# System tools - check before generic chat
APP_LAUNCH_PREFIXES = ["open ", "launch ", "start ", "run "]
MEDIA_KEYWORDS = ["play", "pause", "skip", "next track", "previous", "mute", "unmute", "volume up", "volume down"]
SYSTEM_CMD_KEYWORDS = ["lock screen", "lock my screen", "lock the screen", "suspend", "reboot", "shut down", "power off"]
SYS_MONITOR_KEYWORDS = ["why are my fans", "cpu usage", "memory usage", "what's using", "system status", "diagnose"]
# Use lowercase: we match with "kw in lower" (lowercased message)
SCREEN_VISION_KEYWORDS = [
    "what am i looking at",
    "what am i looking",  # STT often drops "at"
    "what's on screen",
    "describe my screen",
    "extract code",
    "what do you see",
    "what do i see",  # voice variation
    "screenshot",
    "look at my screen",
    "what's on my screen",
    "describe the screen",
    "extract the code",
    "code from this",
    "what is on screen",
    "what can i see",  # "what can I see?"
]
RESEARCH_KEYWORDS = [
    "research", "compare and summarize", "create a spreadsheet",
    "find the best", "find me the best", "compare the top", "analyze and report",
    "gather information about", "complete overview", "thoroughly research",
]
# Direct OpenClaw test: bypass classifier for connection verification
OPENCLAW_DIRECT_KEYWORDS = ["list my skills", "list skills", "openclaw skills", "what can openclaw do"]
# App integration queries: calendar, gmail, drive, tasks - route to OpenClaw classifier
# Include "emails"/"email" so "check my latest three emails" routes correctly (not browse/search)
APP_INTEGRATION_KEYWORDS = [
    "google calendar", "my calendar", "check my calendar", "what's on my calendar",
    "my schedule", "calendar for", "check calendar",
    "check my gmail", "my emails", "my inbox", "check my email", "my gmail",
    "emails", "check emails", "latest emails", "read my email", "read my emails",
    "google drive", "my drive", "my documents", "check my drive",
    "google tasks", "my tasks", "check my tasks",
]
BROWSE_KEYWORDS = [
    "browse", "go to", "navigate to", "open the page", "check my",
    "log into", "login to", "visit", "open the website",
]
COMPLEX_KEYWORDS = [
    "explain", "write code", "program", "analyze", "compare",
    "summarize", "translate", "complex", "detailed",
]


def classify_intent(text: str) -> str:
    """Classify user intent from message text. Check specific intents before generic."""
    return _classify_intent_impl(text, browse_enabled=GERTY_BROWSE_ENABLED).intent


def _is_local_maintenance_command(message: str) -> bool:
    """
    True if message is an explicit local maintenance command (create, list, summary, logs, diagnostics).
    Broader maintenance (planning, analysis, "what should I fix") returns False → routes to chat.
    """
    lower = message.lower().strip()
    if any(pat in lower for pat in LOCAL_MAINTENANCE_PATTERNS):
        return True
    # Standalone "maintenance" → tool (preserve Sprint 5 behavior)
    if lower in ("maintenance", "maintenance help", "maintenance?"):
        return True
    if len(lower) <= 25 and "maintenance" in lower:
        # Short maintenance-only; avoid "what maintenance do I need" etc.
        if not any(q in lower for q in ("what", "how", "why", "analyze", "suggest", "recommend", "should", "need")):
            return True
    return False


def classify_to_decision(text: str) -> RoutingDecision:
    """Classify intent and return a RoutingDecision (intent only). Use apply_policy for full decision."""
    return _classify_intent_impl(text, browse_enabled=GERTY_BROWSE_ENABLED)


def enrich_decision_with_taxonomy(decision: RoutingDecision, message: str) -> RoutingDecision:
    """
    Phase 3.1 (FAR-002, FAR-003, FAR-004): Enrich RoutingDecision with taxonomy fields.
    Call after apply_policy to add primary_intent, requires_tool, capability_owner, etc.
    """
    taxonomy = resolve_taxonomy(decision.intent, message)
    return RoutingDecision(
        intent=decision.intent,
        provider=decision.provider,
        tool_intent=decision.tool_intent,
        run_web_fallback=decision.run_web_fallback,
        use_reasoning=decision.use_reasoning,
        show_app_unavailable=decision.show_app_unavailable,
        unavailable_msg_override=decision.unavailable_msg_override,
        execution_path=decision.execution_path,
        execution_path_reason=decision.execution_path_reason,
        primary_intent=taxonomy.primary_intent,
        secondary_intent=taxonomy.secondary_intent,
        intent_confidence=taxonomy.intent_confidence,
        requires_tool=taxonomy.requires_tool,
        requires_confirmation=taxonomy.requires_confirmation,
        capability_owner=taxonomy.capability_owner,
        tool_family=taxonomy.tool_family,
        safety_level=taxonomy.safety_level,
    )


def apply_policy(
    decision: RoutingDecision,
    *,
    message: str,
    openclaw_enabled: bool,
    tool_executor_present: bool,
    web_fallback_enabled: bool,
) -> RoutingDecision:
    """
    Policy layer: decide routing without executing.
    Returns a new RoutingDecision with provider and policy fields set.
    Order matches current route() logic (first match wins).
    """
    intent = decision.intent
    has_app_keywords = any(kw in message.lower() for kw in APP_INTEGRATION_KEYWORDS)

    if intent in FAST_PATH_INTENTS and tool_executor_present:
        return RoutingDecision(
            intent=intent,
            provider=PROVIDER_TOOL,
            tool_intent=intent,
        )

    # Phase 3.0A: Google Workspace — routing invariant: never route write to read-only native
    # Resolve taxonomy for calendar/email/drive to distinguish read vs write
    if intent in (INTENT_CALENDAR, INTENT_EMAIL, INTENT_DRIVE) and tool_executor_present:
        taxonomy = resolve_taxonomy(intent, message)
        primary = taxonomy.primary_intent
        write_intents = {
            PRIMARY_INTENT_CALENDAR_CREATE,
            PRIMARY_INTENT_CALENDAR_UPDATE,
            PRIMARY_INTENT_EMAIL_REPLY,
            PRIMARY_INTENT_EMAIL_SEND,
        }
        if primary in write_intents:
            # Write intent: OpenClaw/gog only; never silently downgrade to native
            if openclaw_enabled:
                return RoutingDecision(
                    intent=intent,
                    provider=PROVIDER_OPENCLAW,
                    execution_path="openclaw:gog",
                    execution_path_reason="write_intent_requires_gog",
                )
            return RoutingDecision(
                intent=intent,
                provider=PROVIDER_APP_UNAVAILABLE,
                show_app_unavailable=True,
                unavailable_msg_override=GOOGLE_WRITE_UNAVAILABLE_MSG,
            )
        # Read-only: single-backend (stabilization) -> OpenClaw/gog for all; native only when explicitly enabled
        if not GERTY_GOOGLE_NATIVE_ENABLED and openclaw_enabled:
            return RoutingDecision(
                intent=intent,
                provider=PROVIDER_OPENCLAW,
                execution_path="openclaw:gog",
                execution_path_reason="single_backend_mode",
            )
        if GERTY_GOOGLE_NATIVE_ENABLED:
            return RoutingDecision(
                intent=intent,
                provider=PROVIDER_TOOL,
                tool_intent=intent,
            )
        # Single-backend mode, OpenClaw disabled -> app_unavailable
        return RoutingDecision(
            intent=intent,
            provider=PROVIDER_APP_UNAVAILABLE,
            show_app_unavailable=True,
            unavailable_msg_override=GOOGLE_WRITE_UNAVAILABLE_MSG,
        )

    # Maintenance: local commands → tool; broader (planning, analysis) → chat (room for future workflows)
    if intent == INTENT_MAINTENANCE:
        if _is_local_maintenance_command(message) and tool_executor_present:
            return RoutingDecision(
                intent=intent,
                provider=PROVIDER_TOOL,
                tool_intent=intent,
            )
        return RoutingDecision(intent=intent, provider=PROVIDER_CHAT)

    if openclaw_enabled and intent not in FAST_PATH_INTENTS:
        # Execution Boundary v1: prefer native for reasoning/planning when boundary enabled
        if GERTY_EXECUTION_BOUNDARY_ENABLED:
            planning_result = get_planning_block_for_message(message)
            inspection_result = get_inspection_block_for_message(message)
            planning_triggered = planning_result is not None or inspection_result is not None
            boundary = select_execution_path(
                message=message,
                intent=intent,
                planning_triggered=planning_triggered,
                openclaw_available=True,
            )
            if not boundary.use_openclaw:
                run_web = (
                    intent == INTENT_CHAT
                    and web_fallback_enabled
                    and not has_app_keywords
                )
                return RoutingDecision(
                    intent=intent,
                    provider=PROVIDER_CHAT,
                    run_web_fallback=run_web,
                    execution_path=boundary.execution_path,
                    execution_path_reason=boundary.execution_path_reason,
                )
            return RoutingDecision(
                intent=intent,
                provider=PROVIDER_OPENCLAW,
                execution_path=boundary.execution_path,
                execution_path_reason=boundary.execution_path_reason,
            )
        return RoutingDecision(
            intent=intent,
            provider=PROVIDER_OPENCLAW,
            execution_path="openclaw",
            execution_path_reason="legacy_no_boundary",
        )

    if (
        intent == INTENT_CHAT
        and not openclaw_enabled
        and web_fallback_enabled
        and not has_app_keywords
    ):
        return RoutingDecision(
            intent=intent,
            provider=PROVIDER_CHAT,
            run_web_fallback=True,
        )

    if intent in TOOL_INTENTS and tool_executor_present:
        return RoutingDecision(
            intent=intent,
            provider=PROVIDER_TOOL,
            tool_intent=intent,
        )

    if intent == INTENT_CHAT and not openclaw_enabled and has_app_keywords:
        return RoutingDecision(
            intent=intent,
            provider=PROVIDER_APP_UNAVAILABLE,
            show_app_unavailable=True,
        )

    if intent == INTENT_COMPLEX:
        return RoutingDecision(
            intent=intent,
            provider=PROVIDER_COMPLEX,
            use_reasoning=True,
        )

    return RoutingDecision(intent=intent, provider=PROVIDER_CHAT)


def _classify_intent_impl(text: str, *, browse_enabled: bool) -> RoutingDecision:
    """Pure classification logic. browse_enabled allows tests without patching config."""
    lower = text.lower().strip()
    if not lower:
        return RoutingDecision(intent=INTENT_CHAT)

    # Maintenance: check before app_launch so "run diagnostics" doesn't match "run "
    for kw in MAINTENANCE_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_MAINTENANCE)

    # Opportunity scanner: "create project from opportunity" must match before "create project"
    for kw in OPPORTUNITY_SCANNER_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_OPPORTUNITY_SCANNER)

    # Project graph: create project, add task, etc. (before personal_context)
    for kw in PROJECT_GRAPH_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_PROJECT_GRAPH)

    # Calendar: "schedule for" and "my schedule" + time before personal_context (FAR-005, Phase 3.0B)
    if "schedule for" in lower:
        return RoutingDecision(intent=INTENT_CALENDAR)
    if "my schedule" in lower and any(
        t in lower for t in ("next week", "tomorrow", "today", "next month", "this week", "coming up")
    ):
        return RoutingDecision(intent=INTENT_CALENDAR)

    # Personal context: who am I, goals, projects (read-only)
    for kw in PERSONAL_CONTEXT_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_PERSONAL_CONTEXT)

    # Agent designer: design/improve/suggest (before agent_runner and agent_factory)
    for kw in AGENT_DESIGNER_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_AGENT_DESIGNER)

    # Agent invocation: ask/run/use agent (before agent_factory)
    for kw in AGENT_RUNNER_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_AGENT_RUNNER)

    # Agent factory: create/list/show agents
    for kw in AGENT_FACTORY_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_AGENT_FACTORY)

    # Capability registry: list/show capabilities (before orchestrator)
    for kw in CAPABILITY_REGISTRY_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_CAPABILITY_REGISTRY)

    # Intent orchestrator: high-level outcome requests (after direct agent commands)
    for kw in ORCHESTRATOR_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_ORCHESTRATOR)

    # Drive: "open the file" (file in drive) before app_launch
    if any(kw in lower for kw in ("open the file", "file i was using", "file i worked on")):
        return RoutingDecision(intent=INTENT_DRIVE)

    # App launch: "open firefox", "launch vs code" - check before media (open/start could overlap)
    for prefix in APP_LAUNCH_PREFIXES:
        if lower.startswith(prefix) and len(lower) > len(prefix) + 1:
            return RoutingDecision(intent=INTENT_APP_LAUNCH)
    for kw in SCREEN_VISION_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_SCREEN_VISION)
    for kw in SYS_MONITOR_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_SYS_MONITOR)
    for kw in MEDIA_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_MEDIA_CONTROL)
    for kw in SYSTEM_CMD_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_SYSTEM_COMMAND)
    # Check timer before time (timer contains "time")
    for kw in TIMER_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_TIMER)
    for kw in TIMEZONE_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_TIMEZONE)
    for kw in WEATHER_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_WEATHER)
    for kw in CALENDAR_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_CALENDAR)
    # Phase 3.1: Email and Drive before APP_INTEGRATION (FAR-001)
    for kw in EMAIL_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_EMAIL)
    for kw in DRIVE_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_DRIVE)
    for kw in RAG_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_RAG)
    # Research before search: "research" contains "search", so check research first
    for kw in RESEARCH_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_RESEARCH)
    # Direct OpenClaw: "list my skills" etc — bypass classifier for connection test
    for kw in OPENCLAW_DIRECT_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_OPENCLAW_DIRECT)
    # App integration queries (calendar, gmail, drive, tasks) before browse
    for kw in APP_INTEGRATION_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_CHAT)
    for kw in BROWSE_KEYWORDS:
        if kw in lower and browse_enabled:
            return RoutingDecision(intent=INTENT_BROWSE)
    for kw in SEARCH_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_SEARCH)
    for kw in WEB_LOOKUP_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_SEARCH)
    for kw in POMODORO_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_POMODORO)
    for kw in STOPWATCH_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_STOPWATCH)
    for kw in TIME_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_TIME)
    for kw in DATE_KEYWORDS:
        if kw == "date":
            # Whole word only: avoid "dated", "outdated", "update" etc.
            if re.search(r"\bdate\b", lower):
                return RoutingDecision(intent=INTENT_DATE)
        elif kw in lower:
            return RoutingDecision(intent=INTENT_DATE)
    for kw in CALC_KEYWORDS:
        if kw in lower or (kw in ("+", "*") and kw in text):
            # Only route to calculator if we can actually extract a math expression.
            # Avoids false positives like "what's the most controversial episode?"
            if extract_math(text) is not None:
                return RoutingDecision(intent=INTENT_CALCULATOR)
            break  # matched a calc keyword but no math found -> fall through to chat
    for kw in UNIT_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_UNITS)
    for kw in RANDOM_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_RANDOM)
    for kw in NOTES_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_NOTES)
    for kw in ALARM_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_ALARM)
    for kw in COMPLEX_KEYWORDS:
        if kw in lower:
            return RoutingDecision(intent=INTENT_COMPLEX)

    return RoutingDecision(intent=INTENT_CHAT)


def parse_timer_duration(text: str) -> int | None:
    """Parse timer duration in seconds from natural language."""
    text = text.lower()
    total_seconds = 0

    # Match "X hours" or "X hour"
    for m in re.finditer(r"(\d+)\s*h(?:our)?s?", text):
        total_seconds += int(m.group(1)) * 3600
    # Match "X minutes" or "X mins" or "X minute"
    for m in re.finditer(r"(\d+)\s*m(?:in(?:ute)?s?)?", text):
        total_seconds += int(m.group(1)) * 60
    # Match "X seconds" or "X secs"
    for m in re.finditer(r"(\d+)\s*s(?:ec(?:ond)?s?)?", text):
        total_seconds += int(m.group(1))

    # Bare number: assume minutes (e.g. "timer 5" = 5 minutes)
    if total_seconds == 0:
        nums = re.findall(r"\b(\d+)\b", text)
        if nums:
            total_seconds = int(nums[0]) * 60

    return total_seconds if total_seconds > 0 else None


def _classify_web_intent_fallback(
    message: str,
    ollama: OllamaClient,
    openrouter: OpenRouterClient,
) -> str:
    """
    When keyword classification returns chat, check if query needs web search.
    Returns: web_lookup | web_research | no_web
    """
    prompt = (
        "Does this query require current/live information from the web to answer accurately?\n"
        "Categories:\n"
        "- web_lookup: quick fact (contact details, showtimes, opening hours, phone number, address)\n"
        "- web_research: compare, analyze, multi-step research, spreadsheets\n"
        "- no_web: general knowledge, opinion, coding, no web needed\n"
        "Reply with exactly one word: web_lookup | web_research | no_web\n\n"
        f"Query: {message}"
    )
    try:
        if ollama.is_available():
            out = ollama.chat(
                prompt,
                history=[],
                model=OLLAMA_CHAT_MODEL,
                system_prompt="Reply with exactly one word: web_lookup, web_research, or no_web.",
            )
        elif OPENROUTER_API_KEY and openrouter.is_available():
            out = openrouter.chat(
                prompt,
                history=[],
                model="openai/gpt-oss-120b",
                system_prompt="Reply with exactly one word: web_lookup, web_research, or no_web.",
            )
        else:
            return "no_web"
        out = out.strip().lower()
        if "web_lookup" in out:
            return "web_lookup"
        if "web_research" in out:
            return "web_research"
    except Exception as e:
        logger.debug("Web intent fallback failed: %s", e)
    return "no_web"


def _log_routing_trace(decision: RoutingDecision, message: str) -> None:
    """Phase 3.1 FAR-030: Log routing trace for each routed request."""
    request_id = str(uuid.uuid4())
    tool_name = decision.tool_intent or decision.intent
    log_routing_trace(
        request_id=request_id,
        normalized_request=(message or "").lower().strip(),
        primary_intent=decision.primary_intent,
        secondary_intent=decision.secondary_intent,
        intent_confidence=decision.intent_confidence,
        requires_tool=decision.requires_tool,
        chosen_capability=decision.capability_owner,
        chosen_execution_path=decision.execution_path,
        tool_invoked=decision.provider,
        tool_name=tool_name,
        confirmation_required=decision.requires_confirmation,
    )


OPENCLAW_APP_UNAVAILABLE_MSG = (
    "I'd love to check your calendar/emails/drive/tasks, but OpenClaw isn't set up. "
    "Add **GERTY_OPENCLAW_ENABLED=1** to your `.env`, install OpenClaw (`npm install -g openclaw`), "
    "run `openclaw daemon start`, and configure your integrations. See docs/OPENCLAW_INTEGRATION.md."
)

# Phase 3.0A: Write intents (calendar create, email reply) require gog via OpenClaw
GOOGLE_WRITE_UNAVAILABLE_MSG = (
    "Creating calendar events or sending emails requires the gog skill via OpenClaw. "
    "Set GERTY_OPENCLAW_ENABLED=1, run `openclaw daemon start`, and configure gog. "
    "See docs/GOOGLE_WORKSPACE_STATUS.md."
)

# Tool-use instructions appended to OpenClaw system context to reduce hallucination
OPENCLAW_TOOL_INSTRUCTIONS = (
    " When performing actions (skills, exec, web search), you MUST use the available tools. "
    "Never invent or guess results. If you need to run a command, use exec. "
    "Do NOT pass security or ask params to exec—use the configured defaults (full access). "
    "Calendar/Gmail/Drive (read and write) go via OpenClaw/gog when single-backend. "
    "If you need to install a skill, use `clawhub install <slug>` via exec—never use `openclaw skills install` (that command does not exist). "
    "ClawHub slug format: use the skill name only (e.g. `gog`), not owner/name. For URL https://clawhub.ai/steipete/gog use `clawhub install gog`. If `clawhub install owner/name` fails with Invalid slug, retry with `clawhub install <skill-name>` (the last path segment). Use `clawhub inspect <slug>` to verify the slug exists first. "
    "For improvement/planning advice: consider Gerty's capabilities first—create agents (design agent, create agent), run research agents (run agent, ask agent), create projects (create project, add task), manage opportunities (create opportunity, research opportunity), execute tasks (run next task). Use these when they fit; avoid generic advice when a capability applies."
)


class Router:
    """Routes messages to tools or LLM backends."""

    def __init__(
        self,
        tool_executor: Callable[[str, str], str] | None = None,
    ):
        self.ollama = OllamaClient()
        self.openrouter = OpenRouterClient()
        self._tool_executor = tool_executor

    def route(
        self,
        message: str,
        history: list[dict] | None = None,
        source: str = "chat",
        custom_prompt: str | None = None,
    ) -> str:
        """
        Route message to appropriate handler.
        Flow: classify_intent -> apply_policy -> execute.
        Returns response text.
        """
        decision = classify_to_decision(message)
        decision = apply_policy(
            decision,
            message=message,
            openclaw_enabled=GERTY_OPENCLAW_ENABLED,
            tool_executor_present=bool(self._tool_executor),
            web_fallback_enabled=GERTY_WEB_INTENT_FALLBACK,
        )
        decision = enrich_decision_with_taxonomy(decision, message)
        maybe_log_user_friction(message, source=source)
        log_event(
            "route_decision",
            intent=decision.intent,
            provider=decision.provider,
            execution_path=getattr(decision, "execution_path", "native"),
            execution_path_reason=getattr(decision, "execution_path_reason", ""),
            source=source,
            msg_len=len(message),
            primary_intent=decision.primary_intent,
            requires_tool=decision.requires_tool,
            capability_owner=decision.capability_owner,
        )
        _log_routing_trace(decision, message)
        return self._execute_route(decision, message, history, custom_prompt)

    def _execute_route(
        self,
        decision: RoutingDecision,
        message: str,
        history: list[dict] | None,
        custom_prompt: str | None,
    ) -> str:
        """
        Execution layer: consume RoutingDecision and perform the action.
        Single responsibility per branch.
        """
        intent = decision.intent

        if decision.provider == PROVIDER_TOOL and decision.tool_intent and self._tool_executor:
            t0 = time.perf_counter()
            out = self._tool_executor(decision.tool_intent, message)
            log_event(
                "tool_call",
                intent=decision.tool_intent,
                provider=PROVIDER_TOOL,
                elapsed_ms=round((time.perf_counter() - t0) * 1000),
            )
            return out

        if decision.provider == PROVIDER_OPENCLAW:
            _gw = intent in (INTENT_CALENDAR, INTENT_EMAIL, INTENT_DRIVE) or any(kw in message.lower() for kw in APP_INTEGRATION_KEYWORDS)
            if _gw:
                logger.info(
                    "OpenClaw: Google intent=%r primary=%r exec_path=%r msg=%r",
                    intent, getattr(decision, "primary_intent", None),
                    getattr(decision, "execution_path", None), message[:80],
                )
            from gerty.openclaw.client import execute as openclaw_execute
            from gerty.openclaw.context_inspect import inspect_openclaw_context
            from gerty.openclaw.transparency import compute_memory_influence_metadata, set_last_reply_metadata
            from gerty.openclaw.validation import verify_write_response
            ctx = inspect_openclaw_context()
            meta = compute_memory_influence_metadata(ctx, history_included=bool(history))
            set_last_reply_metadata(meta)
            openclaw_prompt = (custom_prompt or "") + OPENCLAW_TOOL_INSTRUCTIONS
            injection, context_metrics, _ = _get_planning_or_inspection_context(message)
            effective_message = (injection + message) if injection else message
            t0 = time.perf_counter()
            response = openclaw_execute(effective_message, history=history, system_context=openclaw_prompt)
            response = verify_write_response(response, getattr(decision, "primary_intent", None))
            elapsed_ms = round((time.perf_counter() - t0) * 1000)
            if response != OPENCLAW_UNAVAILABLE_MSG:
                log_event("openclaw_result", intent=intent, success=True, elapsed_ms=elapsed_ms)
                return response
            log_event(
                "openclaw_result",
                intent=intent,
                success=False,
                unavailable=True,
                elapsed_ms=elapsed_ms,
            )
            return response

        if decision.provider == PROVIDER_CHAT and decision.run_web_fallback:
            fallback = _classify_web_intent_fallback(message, self.ollama, self.openrouter)
            if fallback == "web_lookup" and self._tool_executor:
                log_event("web_fallback", from_intent="chat", to=INTENT_SEARCH, reason=fallback)
                t0 = time.perf_counter()
                out = self._tool_executor(INTENT_SEARCH, message)
                log_event("tool_call", intent=INTENT_SEARCH, provider="web_fallback", elapsed_ms=round((time.perf_counter() - t0) * 1000))
                return out
            if fallback == "web_research" and self._tool_executor:
                log_event("web_fallback", from_intent="chat", to=INTENT_RESEARCH, reason=fallback)
                t0 = time.perf_counter()
                out = self._tool_executor(INTENT_RESEARCH, message)
                log_event("tool_call", intent=INTENT_RESEARCH, provider="web_fallback", elapsed_ms=round((time.perf_counter() - t0) * 1000))
                return out

        if decision.provider == PROVIDER_APP_UNAVAILABLE and decision.show_app_unavailable:
            log_event("app_unavailable", intent=intent)
            msg = decision.unavailable_msg_override or OPENCLAW_APP_UNAVAILABLE_MSG
            return msg

        if decision.provider == PROVIDER_COMPLEX and decision.use_reasoning:
            if OPENROUTER_API_KEY and self.openrouter.is_available():
                try:
                    return self.openrouter.chat(message, history)
                except Exception as e:
                    logger.debug("OpenRouter fallback: %s", e)
            if self.ollama.is_available():
                try:
                    return self.ollama.chat(message, history, model=OLLAMA_REASONING_MODEL)
                except Exception as e:
                    logger.debug("Ollama reasoning fallback: %s", e)

        # Default: model routing v1 (sync path loads settings for provider/model)
        # Model lock: always use LOCKED_OPENROUTER_MODEL for OpenRouter (overrides settings)
        from gerty.settings import load as load_settings
        settings = load_settings()
        prov = settings.get("provider", "local")
        loc_m = settings.get("local_model") or OLLAMA_CHAT_MODEL
        or_m = LOCKED_OPENROUTER_MODEL
        injection, _, is_inspection_first = _get_planning_or_inspection_context(message)
        # Preserve runtime behavior: only inject on direct path for inspection-first.
        # Grounded planning injection is OpenClaw-only (legacy behavior).
        effective_message = (injection + message) if (injection and is_inspection_first) else message
        planning_triggered = bool(injection)
        route_result = select_model_for_request(
            message=message,
            planning_triggered=planning_triggered,
            intent=intent,
            provider=prov,
            local_model=loc_m,
            openrouter_model=or_m,
            ollama_available=self.ollama.is_available(),
            openrouter_available=bool(OPENROUTER_API_KEY and self.openrouter.is_available()),
        )

        if self.ollama.is_available() and (prov or "local").lower() == "local":
            try:
                return self.ollama.chat(effective_message, history, model=route_result.selected_model)
            except Exception as e:
                logger.debug("Ollama preferred model failed: %s", e)
                fallback_model = OLLAMA_CHAT_MODEL or loc_m
                if fallback_model != route_result.selected_model:
                    try:
                        log_event("model_fallback", from_model=route_result.selected_model, to_model=fallback_model, reason=str(e)[:100])
                        return self.ollama.chat(effective_message, history, model=fallback_model)
                    except Exception as e2:
                        logger.debug("Ollama fallback also failed: %s", e2)
                return f"Ollama error: {e}. Is Ollama running? Try: ollama serve"
        if OPENROUTER_API_KEY and self.openrouter.is_available():
            try:
                return self.openrouter.chat(effective_message, history, model=route_result.selected_model)
            except Exception as e:
                logger.debug("OpenRouter failed: %s", e)
                if self.ollama.is_available():
                    try:
                        log_event("model_fallback", from_provider="openrouter", to_provider="ollama", to_model=OLLAMA_CHAT_MODEL or loc_m, reason=str(e)[:100])
                        return self.ollama.chat(effective_message, history, model=OLLAMA_CHAT_MODEL or loc_m)
                    except Exception as e2:
                        logger.debug("Ollama fallback also failed: %s", e2)
                return f"OpenRouter error: {e}"
        return "No LLM available. Start Ollama with: ollama serve"

    def route_stream(
        self,
        message: str,
        history: list[dict] | None = None,
        *,
        provider: str | None = None,
        local_model: str | None = None,
        openrouter_model: str | None = None,
        custom_prompt: str | None = None,
        rag_model: str | None = None,
        source: str | None = None,
        metrics_source: str | None = None,
    ) -> Iterator[str]:
        """Route message and stream response chunks. Flow: classify -> apply_policy -> enrich -> execute."""
        decision = classify_to_decision(message)
        decision = apply_policy(
            decision,
            message=message,
            openclaw_enabled=GERTY_OPENCLAW_ENABLED,
            tool_executor_present=bool(self._tool_executor),
            web_fallback_enabled=GERTY_WEB_INTENT_FALLBACK,
        )
        decision = enrich_decision_with_taxonomy(decision, message)
        maybe_log_user_friction(message, source=source or "stream")
        log_event(
            "route_decision",
            intent=decision.intent,
            provider=decision.provider,
            execution_path=getattr(decision, "execution_path", "native"),
            execution_path_reason=getattr(decision, "execution_path_reason", ""),
            source=source or "stream",
            msg_len=len(message),
            primary_intent=decision.primary_intent,
            requires_tool=decision.requires_tool,
            capability_owner=decision.capability_owner,
        )
        _log_routing_trace(decision, message)
        yield from self._execute_route_stream(
            decision, message, history, custom_prompt,
            provider=provider,
            local_model=local_model,
            openrouter_model=openrouter_model,
            rag_model=rag_model,
            metrics_source=metrics_source,
        )

    def _execute_route_stream(
        self,
        decision: RoutingDecision,
        message: str,
        history: list[dict] | None,
        custom_prompt: str | None,
        *,
        provider: str | None = None,
        local_model: str | None = None,
        openrouter_model: str | None = None,
        rag_model: str | None = None,
        metrics_source: str | None = None,
    ) -> Iterator[str]:
        """Execution layer for streaming. Consumes RoutingDecision."""
        intent = decision.intent

        if decision.provider == PROVIDER_TOOL and decision.tool_intent and self._tool_executor:
            if decision.tool_intent == INTENT_BROWSE:
                yield "Browsing..."
            t0 = time.perf_counter()
            result = self._tool_executor(decision.tool_intent, message)
            log_event(
                "tool_call",
                intent=decision.tool_intent,
                provider=PROVIDER_TOOL,
                elapsed_ms=round((time.perf_counter() - t0) * 1000),
            )
            yield result
            return

        if decision.provider == PROVIDER_OPENCLAW:
            _gw = intent in (INTENT_CALENDAR, INTENT_EMAIL, INTENT_DRIVE) or any(kw in message.lower() for kw in APP_INTEGRATION_KEYWORDS)
            if _gw:
                logger.info(
                    "OpenClaw: Google intent=%r primary=%r exec_path=%r msg=%r",
                    intent, getattr(decision, "primary_intent", None),
                    getattr(decision, "execution_path", None), message[:80],
                )
            from gerty.openclaw.client import build_openclaw_payload, execute as openclaw_execute
            from gerty.openclaw.context_inspect import inspect_openclaw_context
            from gerty.openclaw.transparency import compute_memory_influence_metadata, set_last_reply_metadata
            from gerty.openclaw.validation import verify_write_response
            ctx = inspect_openclaw_context()
            meta = compute_memory_influence_metadata(ctx, history_included=bool(history))
            set_last_reply_metadata(meta)
            yield "Working on it..."
            openclaw_prompt = (custom_prompt or "") + OPENCLAW_TOOL_INSTRUCTIONS
            injection, context_metrics, _ = _get_planning_or_inspection_context(message)
            effective_message = (injection + message) if injection else message
            payload = build_openclaw_payload(effective_message, history=history, system_context=openclaw_prompt)
            log_prompt_metrics({
                "route": "openclaw",
                "provider": provider or "openrouter",
                "model": openrouter_model or OPENROUTER_MODEL,
                "user_message_preview": (message or "")[:80],
                "message_count": 1 + len(history or []),
                "history_message_count": len(history or []),
                "history_included": bool(history),
                "summary_included": "Conversation summary:" in (custom_prompt or ""),
                "custom_prompt_included": bool(custom_prompt),
                "approx_chars_sent_by_gerty": len(payload),
                "approx_tokens_sent_by_gerty": approx_tokens(len(payload)),
                "openclaw_payload_chars": len(payload),
                "execution_path": getattr(decision, "execution_path", "openclaw"),
                "execution_path_reason": getattr(decision, "execution_path_reason", ""),
                "openclaw_used": True,
                "openclaw_expanded_note": "OpenClaw adds bootstrap files (USER.md, SOUL.md, etc.) and tool schemas before sending to OpenRouter. Gerty cannot measure expanded size.",
                "fresh_session_hint": len(history or []) == 0,
                "source": metrics_source or "stream",
                **context_metrics,
            })
            t0 = time.perf_counter()
            response = openclaw_execute(effective_message, history=history, system_context=openclaw_prompt)
            response = verify_write_response(response, getattr(decision, "primary_intent", None))
            elapsed_ms = round((time.perf_counter() - t0) * 1000)
            if response != OPENCLAW_UNAVAILABLE_MSG:
                log_event("openclaw_result", intent=intent, success=True, elapsed_ms=elapsed_ms)
                yield response
                return
            log_event(
                "openclaw_result",
                intent=intent,
                success=False,
                unavailable=True,
                elapsed_ms=elapsed_ms,
            )
            yield response
            return

        if decision.provider == PROVIDER_CHAT and decision.run_web_fallback:
            fallback = _classify_web_intent_fallback(message, self.ollama, self.openrouter)
            if fallback == "web_lookup":
                intent = INTENT_SEARCH
            elif fallback == "web_research":
                intent = INTENT_RESEARCH

        if intent in (INTENT_RESEARCH, INTENT_SEARCH, INTENT_BROWSE):
            logger.info("Router: intent=%r message=%r", intent, message[:80] + "..." if len(message) > 80 else message)

        if intent == INTENT_SEARCH:
            use_openrouter = (provider or "local").lower() == "openrouter"
            if use_openrouter and OPENROUTER_API_KEY and self.openrouter.is_available():
                try:
                    yield "Searching..."
                    msgs = build_openrouter_messages(message, history, custom_prompt)
                    chars = sum(len(m.get("content", "")) for m in msgs if isinstance(m.get("content"), str))
                    log_prompt_metrics({
                        "route": "openrouter_search",
                        "provider": "openrouter",
                        "user_message_preview": (message or "")[:80],
                        "message_count": len(msgs),
                        "history_message_count": len(history or []),
                        "history_included": bool(history),
                        "summary_included": "Conversation summary:" in (custom_prompt or ""),
                        "custom_prompt_included": bool(custom_prompt),
                        "approx_chars_sent_by_gerty": chars,
                        "approx_tokens_sent_by_gerty": approx_tokens(chars),
                        "fresh_session_hint": len(history or []) == 0,
                        "source": metrics_source or "stream",
                    })
                    response = self.openrouter.quick_search(
                        message, history, system_prompt=custom_prompt
                    )
                    yield response
                    return
                except Exception as e:
                    logger.debug("OpenRouter search fallback: %s", e)

        if intent in TOOL_INTENTS and self._tool_executor:
            if intent == INTENT_BROWSE:
                yield "Browsing..."
            result = self._tool_executor(intent, message)
            yield result
            return

        if intent == INTENT_RESEARCH:
            use_openrouter = (provider or "local").lower() == "openrouter"
            if use_openrouter and OPENROUTER_API_KEY and self.openrouter.is_available():
                try:
                    yield "Researching..."
                    msgs = build_openrouter_messages(message, history, custom_prompt)
                    chars = sum(len(m.get("content", "")) for m in msgs if isinstance(m.get("content"), str))
                    log_prompt_metrics({
                        "route": "openrouter_research",
                        "provider": "openrouter",
                        "user_message_preview": (message or "")[:80],
                        "message_count": len(msgs),
                        "history_message_count": len(history or []),
                        "history_included": bool(history),
                        "summary_included": "Conversation summary:" in (custom_prompt or ""),
                        "custom_prompt_included": bool(custom_prompt),
                        "approx_chars_sent_by_gerty": chars,
                        "approx_tokens_sent_by_gerty": approx_tokens(chars),
                        "fresh_session_hint": len(history or []) == 0,
                        "source": metrics_source or "stream",
                    })
                    response = self.openrouter.research(message, history, system_prompt=custom_prompt)
                    from gerty.research.output import parse_and_save_tables

                    saved_path = parse_and_save_tables(response)
                    if saved_path:
                        response = response + f"\n\n*Saved spreadsheet to `{saved_path}`*"
                    yield response
                    return
                except Exception as e:
                    logger.debug("Research fallback: %s", e)
                    yield f"Research failed: {e}. Try again or use a simpler search."
                    return
            yield (
                "Deep research requires OpenRouter. Switch to OpenRouter in Settings to use "
                "web search, multi-step research, and spreadsheet output."
            )
            return

        if decision.provider == PROVIDER_APP_UNAVAILABLE and decision.show_app_unavailable:
            log_event("app_unavailable", intent=intent)
            msg = decision.unavailable_msg_override or OPENCLAW_APP_UNAVAILABLE_MSG
            yield msg
            return

        use_local = (provider or "local").lower() == "local"
        local_m = rag_model or local_model or OLLAMA_CHAT_MODEL
        # Model lock: always use LOCKED_OPENROUTER_MODEL (overrides settings/body)
        openrouter_m = LOCKED_OPENROUTER_MODEL

        # Model routing v1: select model by task type when not overridden by RAG
        injection, context_metrics, is_inspection_first = _get_planning_or_inspection_context(message)
        effective_message = (injection + message) if (injection and is_inspection_first) else message
        planning_triggered = bool(injection)
        route_result = select_model_for_request(
            message=message,
            planning_triggered=planning_triggered,
            intent=intent,
            provider=provider or "local",
            local_model=local_m,
            openrouter_model=openrouter_m,
            ollama_available=self.ollama.is_available(),
            openrouter_available=bool(OPENROUTER_API_KEY and self.openrouter.is_available()),
        )
        model_routing_metrics = {
            "task_type": route_result.task_type,
            "selected_model_profile": route_result.selected_model_profile,
            "model_route_reason": route_result.model_route_reason,
            "fallback_used": route_result.fallback_used,
            "execution_path": getattr(decision, "execution_path", "native"),
            "execution_path_reason": getattr(decision, "execution_path_reason", ""),
            "openclaw_used": False,
            **context_metrics,
        }

        if use_local and self.ollama.is_available():
            model = rag_model or route_result.selected_model
            fallback_model = OLLAMA_CHAT_MODEL or local_m
            for attempt_model in ([model] + ([fallback_model] if fallback_model != model else [])):
                try:
                    msgs = build_openrouter_messages(effective_message, history, custom_prompt)
                    chars = sum(len(m.get("content", "")) for m in msgs if isinstance(m.get("content"), str))
                    log_prompt_metrics({
                        "route": "local",
                        "provider": "local",
                        "model": attempt_model,
                        "user_message_preview": (message or "")[:80],
                        "message_count": len(msgs),
                        "history_message_count": len(history or []),
                        "history_included": bool(history),
                        "summary_included": "Conversation summary:" in (custom_prompt or ""),
                        "custom_prompt_included": bool(custom_prompt),
                        "approx_chars_sent_by_gerty": chars,
                        "approx_tokens_sent_by_gerty": approx_tokens(chars),
                        "fresh_session_hint": len(history or []) == 0,
                        "source": metrics_source or "stream",
                        "fallback_used": attempt_model != model,
                        **model_routing_metrics,
                    })
                    for chunk in self.ollama.chat_stream(
                        effective_message, history, model=attempt_model, system_prompt=custom_prompt
                    ):
                        yield chunk
                    return
                except Exception as e:
                    if attempt_model == model:
                        logger.debug("Ollama stream preferred model failed: %s", e)
                        if fallback_model != model:
                            log_event("model_fallback", from_model=model, to_model=fallback_model, reason=str(e)[:100], stream=True)
                    else:
                        yield f"Ollama error: {e}. Is Ollama running? Try: ollama serve"
                        return
            yield "Ollama error. Is Ollama running? Try: ollama serve"
            return

        if OPENROUTER_API_KEY and self.openrouter.is_available():
            model = route_result.selected_model
            try:
                msgs = build_openrouter_messages(effective_message, history, custom_prompt)
                chars = sum(len(m.get("content", "")) for m in msgs if isinstance(m.get("content"), str))
                log_prompt_metrics({
                    "route": "openrouter_direct",
                    "provider": "openrouter",
                    "model": model,
                    "user_message_preview": (message or "")[:80],
                    "message_count": len(msgs),
                    "history_message_count": len(history or []),
                    "history_included": bool(history),
                    "summary_included": "Conversation summary:" in (custom_prompt or ""),
                    "custom_prompt_included": bool(custom_prompt),
                    "approx_chars_sent_by_gerty": chars,
                    "approx_tokens_sent_by_gerty": approx_tokens(chars),
                    "fresh_session_hint": len(history or []) == 0,
                    "source": metrics_source or "stream",
                    **model_routing_metrics,
                })
                for chunk in self.openrouter.chat_stream(
                    effective_message, history, model=model, system_prompt=custom_prompt
                ):
                    yield chunk
                return
            except Exception as e:
                logger.debug("OpenRouter stream failed: %s", e)
                if self.ollama.is_available():
                    try:
                        log_event("model_fallback", from_provider="openrouter", to_provider="ollama", to_model=OLLAMA_CHAT_MODEL or local_m, reason=str(e)[:100], stream=True)
                        for chunk in self.ollama.chat_stream(
                            effective_message, history, model=OLLAMA_CHAT_MODEL or local_m, system_prompt=custom_prompt
                        ):
                            yield chunk
                        return
                    except Exception as e2:
                        logger.debug("Ollama fallback stream also failed: %s", e2)
                yield f"OpenRouter error: {e}"
                return

        yield "No LLM available. Start Ollama with: ollama serve"
