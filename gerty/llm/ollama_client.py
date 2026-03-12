"""Ollama API client for local LLM."""

import base64
import json
import logging
from typing import Any, Callable, Iterator

import httpx

from gerty.config import (
    OLLAMA_BASE_URL,
    OLLAMA_CHAT_TIMEOUT,
    OLLAMA_HEALTH_TIMEOUT,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
    OLLAMA_VISION_MODEL,
)

logger = logging.getLogger(__name__)

# Tool executor: (name, arguments) -> result text
ToolExecutor = Callable[[str, dict[str, Any]], str]
# Batch: list of (name, args) -> list of result strings (same order)
BatchToolExecutor = Callable[[list[tuple[str, dict[str, Any]]]], list[str]]


class OllamaClient:
    """Client for Ollama chat API."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(
        self,
        message: str,
        history: list[dict] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """Send a message and get a response. Optional model and system prompt override."""
        default_prompt = "Format replies in Markdown: use **bold**, headings (##), bullet lists, numbered lists, and code blocks (```language) when helpful. Use emojis sparingly for clarity."
        system = {"role": "system", "content": system_prompt or default_prompt}
        messages = [system] + list(history or [])
        messages.append({"role": "user", "content": message})
        model = model or self.model
        temp = temperature if temperature is not None else OLLAMA_TEMPERATURE

        with httpx.Client(timeout=OLLAMA_CHAT_TIMEOUT) as client:
            response = client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "keep_alive": "5m",
                    "options": {"temperature": temp},
                },
            )
            if response.status_code == 404:
                return (
                    f"Model '{model}' not found. Run: ollama pull {model}\n"
                    "Or check available models: ollama list"
                )
            if response.status_code == 500:
                try:
                    err = response.json()
                    detail = err.get("error", str(err))
                except Exception as e:
                    logger.debug("Ollama 500 response parse: %s", e)
                    detail = response.text[:200] if response.text else "Unknown"
                return (
                    f"Ollama server error (500) with model '{model}'. "
                    "Try: ollama run gemma3:12b (in terminal) to test. "
                    "If OOM, try a smaller model: ollama pull llama3.2\n"
                    f"Details: {detail}"
                )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")

    def chat_stream(
        self,
        message: str,
        history: list[dict] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ):
        """Stream chat response. Yields content chunks."""
        default_prompt = "Format replies in Markdown: use **bold**, headings (##), bullet lists, numbered lists, and code blocks (```language) when helpful. Use emojis sparingly for clarity."
        system = {"role": "system", "content": system_prompt or default_prompt}
        messages = [system] + list(history or [])
        messages.append({"role": "user", "content": message})
        model = model or self.model
        temp = temperature if temperature is not None else OLLAMA_TEMPERATURE

        with httpx.Client(timeout=OLLAMA_CHAT_TIMEOUT) as client:
            with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "keep_alive": "5m",
                    "options": {"temperature": temp},
                },
            ) as response:
                if response.status_code == 404:
                    yield f"Model '{model}' not found. Run: ollama pull {model}"
                    return
                if response.status_code == 500:
                    yield f"Ollama server error (500). Try: ollama run {model}"
                    return
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            yield chunk
                    except json.JSONDecodeError as e:
                        logger.debug("Ollama stream JSON parse: %s", e)
                        continue

    def chat_with_images(
        self,
        message: str,
        images: list[bytes] | list[str],
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """Send a message with images to a vision model. Images as base64 strings or raw bytes."""
        default_prompt = "Format replies in Markdown: use **bold**, headings (##), bullet lists, numbered lists, and code blocks (```language) when helpful. Use emojis sparingly for clarity."
        system = {"role": "system", "content": system_prompt or default_prompt}
        model = model or OLLAMA_VISION_MODEL
        temp = temperature if temperature is not None else OLLAMA_TEMPERATURE

        # Convert images to base64 strings
        b64_images: list[str] = []
        for img in images:
            if isinstance(img, bytes):
                b64_images.append(base64.b64encode(img).decode("utf-8"))
            else:
                b64_images.append(img)

        user_msg = {"role": "user", "content": message, "images": b64_images}
        messages = [system, user_msg]

        with httpx.Client(timeout=OLLAMA_CHAT_TIMEOUT) as client:
            response = client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "keep_alive": "5m",
                    "options": {"temperature": temp},
                },
            )
            if response.status_code == 404:
                return (
                    f"Vision model '{model}' not found. Run: ollama pull {model}\n"
                    "Or check available models: ollama list"
                )
            if response.status_code == 500:
                try:
                    err = response.json()
                    detail = err.get("error", str(err))
                except Exception as e:
                    logger.debug("Ollama 500 response parse: %s", e)
                    detail = response.text[:200] if response.text else "Unknown"
                return (
                    f"Ollama server error (500) with model '{model}'. "
                    f"Details: {detail}"
                )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")

    def chat_with_tools(
        self,
        message: str,
        history: list[dict] | None = None,
        tools: list[dict] | None = None,
        tool_executor: ToolExecutor | None = None,
        batch_tool_executor: BatchToolExecutor | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tool_rounds: int = 5,
    ) -> str:
        """Chat with tool-calling support. Loops until no tool_calls or max_tool_rounds."""
        default_prompt = "Format replies in Markdown: use **bold**, headings (##), bullet lists, numbered lists, and code blocks (```language) when helpful. Use emojis sparingly for clarity."
        system = {"role": "system", "content": system_prompt or default_prompt}
        messages: list[dict] = [system] + list(history or [])
        messages.append({"role": "user", "content": message})
        model = model or self.model
        temp = temperature if temperature is not None else OLLAMA_TEMPERATURE
        tools = tools or []
        tool_executor = tool_executor or (lambda _n, _a: "")

        for _round in range(max_tool_rounds):
            with httpx.Client(timeout=OLLAMA_CHAT_TIMEOUT) as client:
                payload: dict = {
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "keep_alive": "5m",
                    "options": {"temperature": temp},
                }
                if tools:
                    payload["tools"] = tools

                response = client.post(f"{self.base_url}/api/chat", json=payload)
                if response.status_code == 404:
                    return f"Model '{model}' not found. Run: ollama pull {model}"
                if response.status_code == 500:
                    return f"Ollama server error (500). Try: ollama run {model}"
                response.raise_for_status()
                data = response.json()

            msg = data.get("message", {})
            tool_calls = msg.get("tool_calls") or []
            content = msg.get("content", "")

            if not tool_calls:
                return content or ""

            messages.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})

            calls = []
            for tc in tool_calls:
                fn = tc.get("function", tc) if isinstance(tc, dict) else getattr(tc, "function", tc)
                if isinstance(fn, dict):
                    name = fn.get("name", "")
                    args_raw = fn.get("arguments", {})
                else:
                    name = getattr(fn, "name", "")
                    args_raw = getattr(fn, "arguments", {})
                if isinstance(args_raw, str):
                    try:
                        args = json.loads(args_raw) if args_raw else {}
                    except json.JSONDecodeError:
                        args = {}
                else:
                    args = args_raw or {}
                calls.append((name, args))

            if batch_tool_executor:
                results = batch_tool_executor(calls)
                for (name, _), result in zip(calls, results):
                    messages.append({"role": "tool", "tool_name": name, "content": str(result)})
            else:
                for name, args in calls:
                    result = tool_executor(name, args)
                    messages.append({"role": "tool", "tool_name": name, "content": str(result)})

        return content or ""

    def chat_with_tools_stream(
        self,
        message: str,
        history: list[dict] | None = None,
        tools: list[dict] | None = None,
        tool_executor: ToolExecutor | None = None,
        batch_tool_executor: BatchToolExecutor | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tool_rounds: int = 5,
    ) -> Iterator[str]:
        """Stream chat with tool-calling. Runs tool loop sync, then streams final response."""
        default_prompt = "Format replies in Markdown: use **bold**, headings (##), bullet lists, numbered lists, and code blocks (```language) when helpful. Use emojis sparingly for clarity."
        system = {"role": "system", "content": system_prompt or default_prompt}
        messages: list[dict] = [system] + list(history or [])
        messages.append({"role": "user", "content": message})
        model = model or self.model
        temp = temperature if temperature is not None else OLLAMA_TEMPERATURE
        tools = tools or []
        tool_executor = tool_executor or (lambda _n, _a: "")

        def _progress_msg(name: str, round_num: int) -> str:
            n = (name or "").upper()
            prefix = f"Using tools (round {round_num + 1}/{max_tool_rounds})... "
            if "SEARCH" in n:
                return prefix + "Finding relevant tools... "
            if "MULTI_EXECUTE" in n or "EXECUTE" in n:
                return prefix + "Fetching data... "
            if "RECIPE" in n:
                return prefix + "Running recipe... "
            return prefix

        for round_num in range(max_tool_rounds):
            with httpx.Client(timeout=OLLAMA_CHAT_TIMEOUT) as client:
                payload: dict = {
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "keep_alive": "5m",
                    "options": {"temperature": temp},
                }
                if tools:
                    payload["tools"] = tools

                response = client.post(f"{self.base_url}/api/chat", json=payload)
                if response.status_code == 404:
                    yield f"Model '{model}' not found. Run: ollama pull {model}"
                    return
                if response.status_code == 500:
                    yield "Ollama server error (500). Try: ollama run " + model
                    return
                response.raise_for_status()
                data = response.json()

            msg = data.get("message", {})
            tool_calls = msg.get("tool_calls") or []
            content = msg.get("content", "")

            if not tool_calls:
                for ch in (content or ""):
                    yield ch
                return

            first_name = ""
            calls = []
            for tc in tool_calls:
                fn = tc.get("function", tc) if isinstance(tc, dict) else getattr(tc, "function", tc)
                if isinstance(fn, dict):
                    name = fn.get("name", "")
                    args_raw = fn.get("arguments", {})
                else:
                    name = getattr(fn, "name", "")
                    args_raw = getattr(fn, "arguments", {})
                if not first_name:
                    first_name = name
                if isinstance(args_raw, str):
                    try:
                        args = json.loads(args_raw) if args_raw else {}
                    except json.JSONDecodeError:
                        args = {}
                else:
                    args = args_raw or {}
                calls.append((name, args))
            yield _progress_msg(first_name, round_num)
            messages.append({"role": "assistant", "content": content or "", "tool_calls": tool_calls})

            if batch_tool_executor:
                results = batch_tool_executor(calls)
                for (name, _), result in zip(calls, results):
                    messages.append({"role": "tool", "tool_name": name, "content": str(result)})
            else:
                for name, args in calls:
                    result = tool_executor(name, args)
                    messages.append({"role": "tool", "tool_name": name, "content": str(result)})

        for ch in (content or ""):
            yield ch

    def is_available(self) -> bool:
        """Check if Ollama is running and reachable."""
        try:
            with httpx.Client(timeout=OLLAMA_HEALTH_TIMEOUT) as client:
                r = client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception as e:
            logger.debug("Ollama availability check failed: %s", e)
            return False
