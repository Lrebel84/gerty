"""Model router: intent classification, tool dispatch, Ollama/OpenRouter selection."""

import logging
import re
from typing import Callable, Iterator

from gerty.config import (
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
NOTES_KEYWORDS = ["note:", "note ", "notes", "remember", "add note"]
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
POMODORO_KEYWORDS = ["pomodoro"]
COMPLEX_KEYWORDS = [
    "explain", "write code", "program", "analyze", "compare",
    "summarize", "translate", "complex", "detailed",
]


def classify_intent(text: str) -> str:
    """Classify user intent from message text. Check specific intents before generic."""
    lower = text.lower().strip()
    if not lower:
        return "chat"

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
    for kw in SEARCH_KEYWORDS:
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

        # Tool intents: delegate to tool executor
        tool_intents = ("time", "date", "alarm", "timer", "calculator", "units", "random", "notes", "stopwatch", "timezone", "weather", "rag", "search", "pomodoro")
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

        tool_intents = ("time", "date", "alarm", "timer", "calculator", "units", "random", "notes", "stopwatch", "timezone", "weather", "rag", "search", "pomodoro")
        if intent in tool_intents and self._tool_executor:
            result = self._tool_executor(intent, message)
            yield result
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
