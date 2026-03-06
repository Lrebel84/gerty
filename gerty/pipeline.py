"""Shared chat pipeline: custom prompt, then route. RAG is on-demand via RagTool only."""

import logging
from typing import Iterator

from gerty.config import (
    OLLAMA_CHAT_MODEL,
    OLLAMA_VOICE_MODEL,
    RAG_SUMMARIZE_THRESHOLD,
)
from gerty.settings import load as load_settings

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are Gerty, a helpful AI assistant. Always identify as Gerty. "
    "Format replies in Markdown: use **bold**, headings (##), bullet lists, numbered lists, and code blocks (```language) when helpful. Use emojis sparingly for clarity."
)

GROUNDING_NOTE = (
    " When answering questions about external topics (movies, current events, facts, etc.), "
    "acknowledge you may not have up-to-date information and could be wrong. "
    "Prefer saying 'I'm not sure' over inventing details."
)

# Voice: instruct LLM to avoid markdown/emoji so TTS sounds natural
VOICE_OUTPUT_NOTE = (
    " Your reply will be read aloud. Speak naturally: no markdown, asterisks, dashes for bullets, "
    "emoji, or code blocks. Plain sentences only."
)

# Voice: keep only last N exchanges to minimize prompt size and latency
VOICE_HISTORY_MAX_EXCHANGES = 2


def _summarize_history(ollama, history: list, model: str) -> str:
    """Use local LLM to summarize conversation history."""
    if not history:
        return ""
    text = "\n".join(f"{m.get('role', '')}: {m.get('content', '')}" for m in history)
    prompt = (
        "Summarize this conversation concisely. Keep key facts, decisions, and context the assistant should remember. "
        "Output only the summary, no preamble.\n\n" + text
    )
    try:
        return ollama.chat(prompt, history=[], model=model, system_prompt="Be concise.")
    except Exception as e:
        logger.debug("History summarization failed: %s", e)
        return ""


def chat_pipeline_stream(
    router,
    message: str,
    history: list[dict] | None = None,
    *,
    provider: str | None = None,
    local_model: str | None = None,
    openrouter_model: str | None = None,
    custom_prompt: str | None = None,
    source: str | None = None,
) -> Iterator[str]:
    """
    Chat pipeline: custom prompt, optional summarization (chat only), then route.
    RAG is on-demand via RagTool when user asks to check docs/files.
    Voice: no RAG, no summarization, minimal history for low latency.
    """
    settings = load_settings()
    provider = provider or settings.get("provider", "local")
    local_model = local_model or settings.get("local_model")
    if source == "voice" and OLLAMA_VOICE_MODEL and provider == "local":
        local_model = OLLAMA_VOICE_MODEL
        logger.info("Voice: using OLLAMA_VOICE_MODEL=%s", OLLAMA_VOICE_MODEL)
    elif source == "voice" and provider == "openrouter":
        logger.info("Voice: using OpenRouter model=%s", settings.get("openrouter_model"))
    openrouter_model = openrouter_model or settings.get("openrouter_model")
    custom_prompt = (
        (custom_prompt or settings.get("custom_prompt") or "").strip()
        or DEFAULT_SYSTEM_PROMPT
    )

    effective_history = list(history or [])
    if source == "voice" and effective_history:
        # Voice: trim to last N exchanges to keep prompt small
        msgs_per_exchange = 2
        keep = VOICE_HISTORY_MAX_EXCHANGES * msgs_per_exchange
        effective_history = effective_history[-keep:]

    # Grounding note only for local models; OpenRouter models (Grok, etc.) have fresher training
    effective_prompt = custom_prompt + (GROUNDING_NOTE if provider == "local" else "")
    if source == "voice":
        effective_prompt = effective_prompt + VOICE_OUTPUT_NOTE

    # Summarization: chat only, not voice (avoids extra LLM call)
    if (
        source != "voice"
        and len(effective_history) >= RAG_SUMMARIZE_THRESHOLD
        and router.ollama.is_available()
    ):
        summary = _summarize_history(
            router.ollama, effective_history, local_model or OLLAMA_CHAT_MODEL
        )
        if summary:
            effective_prompt = effective_prompt + "\n\nConversation summary:\n" + summary
            effective_history = []

    yield from router.route_stream(
        message,
        effective_history,
        provider=provider,
        local_model=local_model,
        openrouter_model=openrouter_model,
        custom_prompt=effective_prompt,
        rag_model=None,
    )


def chat_pipeline_sync(
    router,
    message: str,
    history: list[dict] | None = None,
    *,
    provider: str | None = None,
    source: str | None = None,
) -> str:
    """
    Synchronous chat pipeline. Collects streamed response. Used by voice and Telegram.
    """
    return "".join(
        chat_pipeline_stream(
            router, message, history, provider=provider, source=source
        )
    )
