"""Model router: intent classification, tool dispatch, Ollama/OpenRouter selection."""

import re
from typing import Callable, Iterator

from gerty.config import (
    OPENROUTER_API_KEY,
    OLLAMA_CHAT_MODEL,
    OLLAMA_TOOL_MODEL,
    OLLAMA_REASONING_MODEL,
)
from gerty.llm.ollama_client import OllamaClient
from gerty.llm.openrouter_client import OpenRouterClient


# Keywords for intent classification
TIME_KEYWORDS = ["time", "what time", "current time", "what's the time"]
DATE_KEYWORDS = ["date", "what date", "today's date", "what day", "what's the date"]
ALARM_KEYWORDS = [
    "alarm", "set alarm", "wake me", "remind me at",
    "alarm for", "wake up", "set an alarm",
]
TIMER_KEYWORDS = [
    "timer", "set timer", "countdown", "timer for",
    "minute timer", "minute", "second timer",
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

    # Check timer before time (timer contains "time")
    for kw in TIMER_KEYWORDS:
        if kw in lower:
            return "timer"
    for kw in ALARM_KEYWORDS:
        if kw in lower:
            return "alarm"
    for kw in TIME_KEYWORDS:
        if kw in lower:
            return "time"
    for kw in DATE_KEYWORDS:
        if kw in lower:
            return "date"
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
        if intent in ("time", "date", "alarm", "timer") and self._tool_executor:
            return self._tool_executor(intent, message)

        # Complex intent: use reasoning model or OpenRouter
        if intent == "complex":
            if OPENROUTER_API_KEY and self.openrouter.is_available():
                try:
                    return self.openrouter.chat(message, history)
                except Exception:
                    pass
            if self.ollama.is_available():
                try:
                    return self.ollama.chat(message, history, model=OLLAMA_REASONING_MODEL)
                except Exception:
                    pass

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
    ) -> Iterator[str]:
        """Route message and stream response chunks. Tools return full text at once."""
        intent = classify_intent(message)

        if intent in ("time", "date", "alarm", "timer") and self._tool_executor:
            result = self._tool_executor(intent, message)
            yield result
            return

        if intent == "complex" and OPENROUTER_API_KEY and self.openrouter.is_available():
            try:
                result = self.openrouter.chat(message, history)
                yield result
                return
            except Exception:
                pass

        if self.ollama.is_available():
            try:
                model = OLLAMA_CHAT_MODEL if intent != "complex" else OLLAMA_REASONING_MODEL
                for chunk in self.ollama.chat_stream(message, history, model=model):
                    yield chunk
                return
            except Exception as e:
                yield f"Ollama error: {e}. Is Ollama running? Try: ollama serve"
                return

        if OPENROUTER_API_KEY and self.openrouter.is_available():
            try:
                result = self.openrouter.chat(message, history)
                yield result
                return
            except Exception as e:
                yield f"OpenRouter error: {e}"
                return

        yield "No LLM available. Start Ollama with: ollama serve"
