"""Model router: intent classification, tool dispatch, Ollama/OpenRouter selection."""

import logging
import re
from typing import Callable, Iterator

from gerty.config import (
    GERTY_BROWSE_ENABLED,
    GERTY_WEB_INTENT_FALLBACK,
    OPENROUTER_API_KEY,
    OLLAMA_CHAT_MODEL,
    OLLAMA_REASONING_MODEL,
)
from gerty.llm.ollama_client import OllamaClient
from gerty.llm.openrouter_client import OpenRouterClient
from gerty.utils.math_extract import extract_math

logger = logging.getLogger(__name__)

# Keywords for intent classification
TIME_KEYWORDS = ["time", "what time", "current time", "what's the time"]
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
    lower = text.lower().strip()
    if not lower:
        return "chat"

    # App launch: "open firefox", "launch vs code" - check before media (open/start could overlap)
    for prefix in APP_LAUNCH_PREFIXES:
        if lower.startswith(prefix) and len(lower) > len(prefix) + 1:
            return "app_launch"
    for kw in SCREEN_VISION_KEYWORDS:
        if kw in lower:
            return "screen_vision"
    for kw in SYS_MONITOR_KEYWORDS:
        if kw in lower:
            return "sys_monitor"
    for kw in MEDIA_KEYWORDS:
        if kw in lower:
            return "media_control"
    for kw in SYSTEM_CMD_KEYWORDS:
        if kw in lower:
            return "system_command"
    # Check timer before time (timer contains "time")
    for kw in TIMER_KEYWORDS:
        if kw in lower:
            return "timer"
    for kw in TIMEZONE_KEYWORDS:
        if kw in lower:
            return "timezone"
    for kw in WEATHER_KEYWORDS:
        if kw in lower:
            return "weather"
    for kw in RAG_KEYWORDS:
        if kw in lower:
            return "rag"
    # Research before search: "research" contains "search", so check research first
    for kw in RESEARCH_KEYWORDS:
        if kw in lower:
            return "research"
    for kw in BROWSE_KEYWORDS:
        if kw in lower and GERTY_BROWSE_ENABLED:
            return "browse"
    for kw in SEARCH_KEYWORDS:
        if kw in lower:
            return "search"
    for kw in WEB_LOOKUP_KEYWORDS:
        if kw in lower:
            return "search"
    for kw in POMODORO_KEYWORDS:
        if kw in lower:
            return "pomodoro"
    for kw in STOPWATCH_KEYWORDS:
        if kw in lower:
            return "stopwatch"
    for kw in TIME_KEYWORDS:
        if kw == "time":
            if re.search(r"\btime\b", lower):
                return "time"
        elif kw in lower:
            return "time"
    for kw in DATE_KEYWORDS:
        if kw == "date":
            # Whole word only: avoid "dated", "outdated", "update" etc.
            if re.search(r"\bdate\b", lower):
                return "date"
        elif kw in lower:
            return "date"
    for kw in CALC_KEYWORDS:
        if kw in lower or (kw in ("+", "*") and kw in text):
            # Only route to calculator if we can actually extract a math expression.
            # Avoids false positives like "what's the most controversial episode?"
            if extract_math(text) is not None:
                return "calculator"
            break  # matched a calc keyword but no math found -> fall through to chat
    for kw in UNIT_KEYWORDS:
        if kw in lower:
            return "units"
    for kw in RANDOM_KEYWORDS:
        if kw in lower:
            return "random"
    for kw in NOTES_KEYWORDS:
        if kw in lower:
            return "notes"
    for kw in ALARM_KEYWORDS:
        if kw in lower:
            return "alarm"
    for kw in COMPLEX_KEYWORDS:
        if kw in lower:
            return "complex"

    return "chat"


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
    ) -> str:
        """
        Route message to appropriate handler.
        Returns response text.
        """
        intent = classify_intent(message)

        # LLM-based fallback: when chat, check if query needs web search
        if intent == "chat" and GERTY_WEB_INTENT_FALLBACK:
            fallback = _classify_web_intent_fallback(message, self.ollama, self.openrouter)
            if fallback == "web_lookup":
                intent = "search"
            elif fallback == "web_research":
                intent = "research"

        # Tool intents: delegate to tool executor
        tool_intents = ("time", "date", "alarm", "timer", "calculator", "units", "random", "notes", "stopwatch", "timezone", "weather", "rag", "search", "browse", "pomodoro", "app_launch", "media_control", "system_command", "sys_monitor", "screen_vision")
        if intent in tool_intents and self._tool_executor:
            return self._tool_executor(intent, message)

        # Complex intent: use reasoning model or OpenRouter
        if intent == "complex":
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
        """Route message and stream response chunks. Tools return full text at once."""
        intent = classify_intent(message)

        # LLM-based fallback: when chat, check if query needs web search
        if intent == "chat" and GERTY_WEB_INTENT_FALLBACK:
            fallback = _classify_web_intent_fallback(message, self.ollama, self.openrouter)
            if fallback == "web_lookup":
                intent = "search"
            elif fallback == "web_research":
                intent = "research"

        if intent in ("research", "search", "browse"):
            logger.info("Router: intent=%r message=%r", intent, message[:80] + "..." if len(message) > 80 else message)

        # Search with OpenRouter :online when provider is OpenRouter
        # Use quick_search (fewer results, faster) for simple lookups vs full research
        if intent == "search":
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

        tool_intents = ("time", "date", "alarm", "timer", "calculator", "units", "random", "notes", "stopwatch", "timezone", "weather", "rag", "search", "browse", "pomodoro", "app_launch", "media_control", "system_command", "sys_monitor", "screen_vision")
        if intent in tool_intents and self._tool_executor:
            if intent == "browse":
                yield "Browsing..."
            result = self._tool_executor(intent, message)
            yield result
            return

        # Research intent: OpenRouter only (uses :online model for web search)
        if intent == "research":
            use_openrouter = (provider or "local").lower() == "openrouter"
            if use_openrouter and OPENROUTER_API_KEY and self.openrouter.is_available():
                try:
                    # Yield immediate feedback for voice/streaming (research can take 30-60s)
                    yield "Researching..."
                    # Full response needed to parse tables; use sync research()
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
            # Local provider: fallback message
            yield (
                "Deep research requires OpenRouter. Switch to OpenRouter in Settings to use "
                "web search, multi-step research, and spreadsheet output."
            )
            return

        use_local = (provider or "local").lower() == "local"
        local_m = rag_model or local_model or OLLAMA_CHAT_MODEL
        openrouter_m = openrouter_model or OLLAMA_REASONING_MODEL

        if use_local and self.ollama.is_available():
            try:
                model = rag_model or (local_m if intent != "complex" else (local_model or OLLAMA_REASONING_MODEL))
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
