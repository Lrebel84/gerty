"""RAG tool: query documents and memory when user asks to check/retrieve."""

import logging
from typing import TYPE_CHECKING

from gerty.config import OLLAMA_CHAT_MODEL, RAG_TOP_K
from gerty.rag import is_indexed as rag_is_indexed, query as rag_query
from gerty.settings import load as load_settings

from gerty.tools.base import Tool

if TYPE_CHECKING:
    from gerty.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


def _extract_query(message: str) -> str:
    """Extract search query from message. Falls back to full message."""
    lower = message.lower().strip()
    for phrase in [
        "check documentation",
        "check docs",
        "check my docs",
        "retrieve",
        "search my docs",
        "search documentation",
        "look in my docs",
        "look in documentation",
        "find in docs",
        "what do my documents say",
        "what does my documentation say",
    ]:
        if phrase in lower:
            idx = lower.find(phrase) + len(phrase)
            rest = message[idx:].strip().lstrip(":").strip().lstrip("for").strip()
            if rest:
                return rest
    return message.strip()


class RagTool(Tool):
    """Query RAG knowledge base and memory. Returns LLM answer with context."""

    def __init__(self, ollama: "OllamaClient"):
        self._ollama = ollama

    @property
    def name(self) -> str:
        return "rag"

    @property
    def description(self) -> str:
        return "Query documents and memory"

    def execute(self, intent: str, message: str) -> str:
        if not rag_is_indexed():
            return (
                "No documents are indexed yet. Drop PDF, Excel, Word, or text files into "
                "data/knowledge/, then open Settings → Knowledge base → Index now."
            )
        query_text = _extract_query(message)
        if not query_text:
            return "What would you like me to check in your documentation?"
        settings = load_settings()
        embed_model = settings.get("rag_embed_model", "nomic-embed-text")
        chunks = rag_query(query_text, top_k=RAG_TOP_K, embed_model=embed_model)
        if not chunks:
            return "I didn't find any relevant information in your documents or memory for that query."
        context = "\n\n".join(c[0] for c in chunks)
        rag_chat_model = settings.get("rag_chat_model") or "__use_chat__"
        model = rag_chat_model if rag_chat_model != "__use_chat__" else (settings.get("local_model") or OLLAMA_CHAT_MODEL)
        prompt = (
            "Using only the context below, answer the user's question. "
            "If the context doesn't contain the answer, say so.\n\n"
            "Context:\n---\n"
            f"{context}\n---\n\n"
            f"User question: {query_text}"
        )
        try:
            return self._ollama.chat(prompt, history=[], model=model, system_prompt="Be concise. Use the context provided.")
        except Exception as e:
            logger.debug("RAG tool LLM failed: %s", e)
            return f"Error querying documents: {e}. Is Ollama running?"
