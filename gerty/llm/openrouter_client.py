"""OpenRouter API client for cloud LLM access."""

from openai import OpenAI

from gerty.config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    OPENROUTER_RESEARCH_MODEL,
    OPENROUTER_SEARCH_CONTEXT,
    OPENROUTER_WEB_MAX_RESULTS,
)


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

    def is_available(self) -> bool:
        """Check if OpenRouter is configured and reachable."""
        return bool(self.client.api_key)
