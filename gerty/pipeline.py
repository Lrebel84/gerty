"""Shared chat pipeline: RAG, memory, custom prompt, then route. Used by UI, voice, and Telegram."""

import logging
from typing import Iterator

from gerty.config import (
    OLLAMA_CHAT_MODEL,
    OLLAMA_VOICE_MODEL,
    RAG_MIN_MSG_LEN,
    RAG_SUMMARIZE_THRESHOLD,
    RAG_TOP_K,
)
from gerty.rag import is_indexed as rag_is_indexed, query as rag_query
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
    Full chat pipeline: RAG context, summarization, custom prompt, then route.
    Yields response chunks. Used by HTTP stream; voice/Telegram collect and join.
    """
    settings = load_settings()
    provider = provider or settings.get("provider", "local")
    local_model = local_model or settings.get("local_model")
    if source == "voice" and OLLAMA_VOICE_MODEL:
        local_model = OLLAMA_VOICE_MODEL
        logger.info("Voice: using OLLAMA_VOICE_MODEL=%s", OLLAMA_VOICE_MODEL)
    openrouter_model = openrouter_model or settings.get("openrouter_model")
    custom_prompt = (
        (custom_prompt or settings.get("custom_prompt") or "").strip()
        or DEFAULT_SYSTEM_PROMPT
    )

    effective_history = list(history or [])
    effective_prompt = custom_prompt
    rag_model_override = None
    rag_embed_model = settings.get("rag_embed_model", "nomic-embed-text")
    rag_chat_model = settings.get("rag_chat_model") or "__use_chat__"
    use_rag_model = rag_chat_model and rag_chat_model != "__use_chat__"

    chunks: list[tuple[str, dict]] = []
    rag_enabled = settings.get("rag_enabled", False)
    if rag_enabled and rag_is_indexed() and len(message.strip()) >= RAG_MIN_MSG_LEN:
        chunks = rag_query(message, top_k=RAG_TOP_K, embed_model=rag_embed_model)
    if chunks:
        context = "\n\n".join(c[0] for c in chunks)
        if use_rag_model:
            effective_prompt = (
                custom_prompt
                + "\n\nRelevant context from your documents and memory:\n---\n"
                + context
                + "\n---\nUse this context to answer the user's question."
            )
            rag_model_override = rag_chat_model
        else:
            effective_prompt = (
                custom_prompt
                + "\n\nWhen relevant, you may use this context about the user. "
                "Keep your usual personality and style.\n---\n"
                + context
                + "\n---\n"
            )
    else:
        # No RAG context: add grounding note for external-topic questions
        effective_prompt = custom_prompt + GROUNDING_NOTE

    if (
        len(effective_history) >= RAG_SUMMARIZE_THRESHOLD
        and not chunks
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
        provider="local" if rag_model_override else provider,
        local_model=rag_model_override or local_model,
        openrouter_model=openrouter_model,
        custom_prompt=effective_prompt,
        rag_model=rag_model_override,
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
