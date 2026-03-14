"""Model router: intent classification, tool dispatch, Ollama/OpenRouter selection."""

import logging
import re
from dataclasses import dataclass
from typing import Callable, Iterator

from gerty.config import (
    GERTY_BROWSE_ENABLED,
    GERTY_OPENCLAW_ENABLED,
    GERTY_WEB_INTENT_FALLBACK,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OLLAMA_CHAT_MODEL,
    OLLAMA_REASONING_MODEL,
)
from gerty.llm.ollama_client import OllamaClient
from gerty.llm.openrouter_client import OpenRouterClient
from gerty.openclaw.client import OPENCLAW_UNAVAILABLE_MSG
from gerty.utils.math_extract import extract_math

logger = logging.getLogger(__name__)

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
    """
    intent: str
    provider: str = PROVIDER_CHAT
    tool_intent: str | None = None
    run_web_fallback: bool = False
    use_reasoning: bool = False
    openclaw_fallback_calendar: bool = False
    show_app_unavailable: bool = False


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
)

# Fast path: instant Gerty tools—skip OpenClaw classifier
# Calendar routes to OpenClaw (has gerty-calendar skill); CalendarTool used only when OpenClaw is down
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
NOTES_KEYWORDS = ["note:", "note ", "notes", "remember", "add note", "remind me", "make a note", "make note"]
STOPWATCH_KEYWORDS = ["stopwatch", "how long has", "elapsed"]
TIMEZONE_KEYWORDS = ["time in", "timezone", "time zone", "what time in"]
WEATHER_KEYWORDS = ["weather", "forecast", "temperature"]
CALENDAR_KEYWORDS = [
    "calendar", "my calendar", "check my calendar", "what's on my calendar",
    "my schedule", "calendar for", "check calendar", "what have i got on",
    "what do i have on", "what's on", "schedule for",
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


def classify_to_decision(text: str) -> RoutingDecision:
    """Classify intent and return a RoutingDecision (intent only). Use apply_policy for full decision."""
    return _classify_intent_impl(text, browse_enabled=GERTY_BROWSE_ENABLED)


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

    if openclaw_enabled and intent not in FAST_PATH_INTENTS:
        return RoutingDecision(
            intent=intent,
            provider=PROVIDER_OPENCLAW,
            openclaw_fallback_calendar=(intent == INTENT_CALENDAR and tool_executor_present),
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
                model="openai/gpt-4o-mini",
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


OPENCLAW_APP_UNAVAILABLE_MSG = (
    "I'd love to check your calendar/emails/drive/tasks, but OpenClaw isn't set up. "
    "Add **GERTY_OPENCLAW_ENABLED=1** to your `.env`, install OpenClaw (`npm install -g openclaw`), "
    "run `openclaw daemon start`, and configure your integrations. See docs/OPENCLAW_INTEGRATION.md."
)

# Tool-use instructions appended to OpenClaw system context to reduce hallucination
OPENCLAW_TOOL_INSTRUCTIONS = (
    " When performing actions (calendar, skills, exec, web search), you MUST use the available tools. "
    "Never invent or guess results. If you need to run a command, use exec. "
    "Do NOT pass security or ask params to exec—use the configured defaults (full access). "
    "If you need to check the calendar, run the gerty calendar script via exec. "
    "If you need to install a skill, use `clawhub install <slug>` via exec—never use `openclaw skills install` (that command does not exist). "
    "ClawHub slug format: use the skill name only (e.g. `gog`), not owner/name. For URL https://clawhub.ai/steipete/gog use `clawhub install gog`. If `clawhub install owner/name` fails with Invalid slug, retry with `clawhub install <skill-name>` (the last path segment). Use `clawhub inspect <slug>` to verify the slug exists first."
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
            return self._tool_executor(decision.tool_intent, message)

        if decision.provider == PROVIDER_OPENCLAW:
            _gw = intent == INTENT_CALENDAR or any(kw in message.lower() for kw in APP_INTEGRATION_KEYWORDS)
            if _gw:
                logger.info("OpenClaw: Google Workspace request intent=%r msg=%r", intent, message[:80])
            from gerty.openclaw.client import execute as openclaw_execute
            openclaw_prompt = (custom_prompt or "") + OPENCLAW_TOOL_INSTRUCTIONS
            response = openclaw_execute(message, history=history, system_context=openclaw_prompt)
            if response != OPENCLAW_UNAVAILABLE_MSG:
                return response
            if decision.openclaw_fallback_calendar and self._tool_executor:
                return self._tool_executor(INTENT_CALENDAR, message)

        if decision.provider == PROVIDER_CHAT and decision.run_web_fallback:
            fallback = _classify_web_intent_fallback(message, self.ollama, self.openrouter)
            if fallback == "web_lookup" and self._tool_executor:
                return self._tool_executor(INTENT_SEARCH, message)
            if fallback == "web_research" and self._tool_executor:
                return self._tool_executor(INTENT_RESEARCH, message)

        if decision.provider == PROVIDER_APP_UNAVAILABLE and decision.show_app_unavailable:
            return OPENCLAW_APP_UNAVAILABLE_MSG

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

        # Default: Ollama (chat model for general conversation)
        if self.ollama.is_available():
            try:
                model = OLLAMA_CHAT_MODEL
                return self.ollama.chat(message, history, model=model)
            except Exception as e:
                return f"Ollama error: {e}. Is Ollama running? Try: ollama serve"
        if OPENROUTER_API_KEY and self.openrouter.is_available():
            try:
                return self.openrouter.chat(message, history)
            except Exception as e:
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
    ) -> Iterator[str]:
        """Route message and stream response chunks. Flow: classify -> apply_policy -> execute."""
        decision = classify_to_decision(message)
        decision = apply_policy(
            decision,
            message=message,
            openclaw_enabled=GERTY_OPENCLAW_ENABLED,
            tool_executor_present=bool(self._tool_executor),
            web_fallback_enabled=GERTY_WEB_INTENT_FALLBACK,
        )
        yield from self._execute_route_stream(
            decision, message, history, custom_prompt,
            provider=provider,
            local_model=local_model,
            openrouter_model=openrouter_model,
            rag_model=rag_model,
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
    ) -> Iterator[str]:
        """Execution layer for streaming. Consumes RoutingDecision."""
        intent = decision.intent

        if decision.provider == PROVIDER_TOOL and decision.tool_intent and self._tool_executor:
            if decision.tool_intent == INTENT_BROWSE:
                yield "Browsing..."
            result = self._tool_executor(decision.tool_intent, message)
            yield result
            return

        if decision.provider == PROVIDER_OPENCLAW:
            _gw = intent == INTENT_CALENDAR or any(kw in message.lower() for kw in APP_INTEGRATION_KEYWORDS)
            if _gw:
                logger.info("OpenClaw: Google Workspace request intent=%r msg=%r", intent, message[:80])
            from gerty.openclaw.client import execute as openclaw_execute
            yield "Working on it..."
            openclaw_prompt = (custom_prompt or "") + OPENCLAW_TOOL_INSTRUCTIONS
            response = openclaw_execute(message, history=history, system_context=openclaw_prompt)
            if response != OPENCLAW_UNAVAILABLE_MSG:
                yield response
                return
            if decision.openclaw_fallback_calendar and self._tool_executor:
                result = self._tool_executor(INTENT_CALENDAR, message)
                yield result
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
            yield OPENCLAW_APP_UNAVAILABLE_MSG
            return

        use_local = (provider or "local").lower() == "local"
        local_m = rag_model or local_model or OLLAMA_CHAT_MODEL
        openrouter_m = openrouter_model or OPENROUTER_MODEL

        if use_local and self.ollama.is_available():
            try:
                model = rag_model or (local_m if intent != INTENT_COMPLEX else (local_model or OLLAMA_REASONING_MODEL))
                for chunk in self.ollama.chat_stream(
                    message, history, model=model, system_prompt=custom_prompt
                ):
                    yield chunk
                return
            except Exception as e:
                yield f"Ollama error: {e}. Is Ollama running? Try: ollama serve"
                return

        if OPENROUTER_API_KEY and self.openrouter.is_available():
            try:
                for chunk in self.openrouter.chat_stream(
                    message, history, model=openrouter_m, system_prompt=custom_prompt
                ):
                    yield chunk
                return
            except Exception as e:
                yield f"OpenRouter error: {e}"
                return

        yield "No LLM available. Start Ollama with: ollama serve"
