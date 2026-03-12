"""OpenRouter API client for cloud LLM access."""

import json
from typing import Any, Callable, Iterator

from openai import OpenAI

from gerty.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    OPENROUTER_QUICK_SEARCH_MAX_RESULTS,
    OPENROUTER_RESEARCH_MODEL,
    OPENROUTER_SEARCH_CONTEXT,
    OPENROUTER_WEB_MAX_RESULTS,
)

# Tool executor: (name, arguments) -> result text
ToolExecutor = Callable[[str, dict[str, Any]], str]
# Batch: list of (name, args) -> list of result strings (same order)
BatchToolExecutor = Callable[[list[tuple[str, dict[str, Any]]]], list[str]]


class OpenRouterClient:
    """Client for OpenRouter API (OpenAI-compatible)."""

    def __init__(
        self,
        api_key: str = OPENROUTER_API_KEY,
        base_url: str = OPENROUTER_BASE_URL,
        model: str = OPENROUTER_MODEL,
    ):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model

    def chat(
        self,
        message: str,
        history: list[dict] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Send a message and get a response."""
        messages = list(history or [])
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        response = self.client.chat.completions.create(
            model=model or self.model,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    def chat_stream(
        self,
        message: str,
        history: list[dict] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
    ):
        """Stream chat response. Yields content chunks."""
        messages = list(history or [])
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        stream = self.client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def chat_with_images(
        self,
        message: str,
        images: list[str],
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """Send a message with images to a vision model. Images as base64 strings."""
        content: list[dict] = [{"type": "text", "text": message}]
        for b64 in images:
            url = f"data:image/png;base64,{b64}" if not b64.startswith("data:") else b64
            content.append({"type": "image_url", "image_url": {"url": url}})

        messages = [{"role": "user", "content": content}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        response = self.client.chat.completions.create(
            model=model or self.model,
            messages=messages,
        )
        return response.choices[0].message.content or ""

    def _research_request(
        self,
        message: str,
        history: list[dict] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        stream: bool = False,
    ):
        """Build research request with web plugin options."""
        model = model or OPENROUTER_RESEARCH_MODEL
        research_prompt = (
            "You are a thorough research assistant. Use web search to gather current, accurate information. "
            "When the user asks for a spreadsheet or table, include a markdown table in your response "
            "(format: | col1 | col2 | col3 |\\n|---|---|---|\\n| a | b | c |). "
            "Be comprehensive and cite sources when relevant."
        )
        effective_system = (system_prompt or "") + "\n\n" + research_prompt if system_prompt else research_prompt
        messages = list(history or [])
        messages.insert(0, {"role": "system", "content": effective_system})
        messages.append({"role": "user", "content": message})
        # OpenRouter-specific params go in extra_body (OpenAI client rejects them as direct kwargs)
        extra_body = {
            "plugins": [{"id": "web", "max_results": OPENROUTER_WEB_MAX_RESULTS}],
            "web_search_options": {"search_context_size": OPENROUTER_SEARCH_CONTEXT},
        }
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream,
            extra_body=extra_body,
        )

    def research(
        self,
        message: str,
        history: list[dict] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """
        Deep research via OpenRouter with :online model (native web search).
        Uses OPENROUTER_RESEARCH_MODEL by default (e.g. x-ai/grok-4.1-fast:online).
        """
        response = self._research_request(
            message, history, model, system_prompt, stream=False
        )
        return response.choices[0].message.content or ""

    def quick_search(
        self,
        message: str,
        history: list[dict] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
    ) -> str:
        """
        Quick web lookup via OpenRouter :online model. Fewer results, lighter prompt.
        For contact details, showtimes, simple facts. Faster than full research().
        """
        model = model or OPENROUTER_RESEARCH_MODEL
        quick_prompt = (
            "Use web search to find current, accurate information. "
            "Be concise. Cite sources when relevant."
        )
        effective_system = (system_prompt or "") + "\n\n" + quick_prompt if system_prompt else quick_prompt
        messages = list(history or [])
        messages.insert(0, {"role": "system", "content": effective_system})
        messages.append({"role": "user", "content": message})
        extra_body = {
            "plugins": [{"id": "web", "max_results": OPENROUTER_QUICK_SEARCH_MAX_RESULTS}],
            "web_search_options": {"search_context_size": "medium"},
        }
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=False,
            extra_body=extra_body,
        )
        return response.choices[0].message.content or ""

    def research_stream(
        self,
        message: str,
        history: list[dict] | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
    ):
        """Stream deep research response. Uses :online model for web search."""
        stream = self._research_request(
            message, history, model, system_prompt, stream=True
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def chat_with_tools(
        self,
        message: str,
        history: list[dict] | None = None,
        tools: list[dict] | None = None,
        tool_executor: ToolExecutor | None = None,
        batch_tool_executor: BatchToolExecutor | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        max_tool_rounds: int = 5,
    ) -> str:
        """Chat with tool-calling support. Loops until no tool_calls or max_tool_rounds."""
        messages = list(history or [])
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        tools = tools or []
        tool_executor = tool_executor or (lambda _n, _a: "")

        for _round in range(max_tool_rounds):
            kwargs: dict = {
                "model": model or self.model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            response = self.client.chat.completions.create(**kwargs)
            msg = response.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None) or []
            content = msg.content or ""

            if not tool_calls:
                return content

            messages.append(
                {"role": "assistant", "content": content, "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in tool_calls]}
            )

            if batch_tool_executor:
                calls = []
                for tc in tool_calls:
                    args_raw = tc.function.arguments or "{}"
                    try:
                        args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    except json.JSONDecodeError:
                        args = {}
                    calls.append((tc.function.name, args))
                results = batch_tool_executor(calls)
                for tc, result in zip(tool_calls, results):
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
            else:
                for tc in tool_calls:
                    name = tc.function.name
                    args_raw = tc.function.arguments or "{}"
                    try:
                        args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    except json.JSONDecodeError:
                        args = {}
                    result = tool_executor(name, args)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})

        return content

    def chat_with_tools_stream(
        self,
        message: str,
        history: list[dict] | None = None,
        tools: list[dict] | None = None,
        tool_executor: ToolExecutor | None = None,
        batch_tool_executor: BatchToolExecutor | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        max_tool_rounds: int = 5,
    ) -> Iterator[str]:
        """Stream chat with tool-calling. Runs tool loop sync, then streams final response."""
        messages = list(history or [])
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        tools = tools or []
        tool_executor = tool_executor or (lambda _n, _a: "")
        content = ""

        for round_num in range(max_tool_rounds):
            kwargs: dict = {
                "model": model or self.model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools

            response = self.client.chat.completions.create(**kwargs)
            msg = response.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None) or []
            content = msg.content or ""

            if not tool_calls:
                for ch in content:
                    yield ch
                return

            yield f"Using tools (round {round_num + 1}/{max_tool_rounds})... "
            messages.append(
                {"role": "assistant", "content": content, "tool_calls": [{"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in tool_calls]}
            )

            if batch_tool_executor:
                calls = []
                for tc in tool_calls:
                    args_raw = tc.function.arguments or "{}"
                    try:
                        args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    except json.JSONDecodeError:
                        args = {}
                    calls.append((tc.function.name, args))
                results = batch_tool_executor(calls)
                for tc, result in zip(tool_calls, results):
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
            else:
                for tc in tool_calls:
                    name = tc.function.name
                    args_raw = tc.function.arguments or "{}"
                    try:
                        args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    except json.JSONDecodeError:
                        args = {}
                    result = tool_executor(name, args)
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})

        # Hit max rounds with no usable final text: force one more call without tools to get a summary
        if len(content.strip()) < 50:
            try:
                # Add explicit prompt so model knows to summarize (conversation ends with tool result)
                summary_messages = messages + [
                    {"role": "user", "content": "Based on the tool results above, provide a clear summary for the user. If there were errors, explain what went wrong. Keep it brief."},
                ]
                response = self.client.chat.completions.create(
                    model=model or self.model,
                    messages=summary_messages,
                )
                content = response.choices[0].message.content or ""
            except Exception as e:
                content = f"I ran into limits while fetching your calendar: {e}. Please try again."
        for ch in content:
            yield ch

    def is_available(self) -> bool:
        """Check if OpenRouter is configured and reachable."""
        return bool(self.client.api_key)
