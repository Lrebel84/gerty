"""Persistent user settings for Gerty."""

import json
import logging
from pathlib import Path

from gerty.config import (
    DATA_DIR,
    OLLAMA_CHAT_MODEL,
    OPENROUTER_MODEL,
    RAG_CHAT_MODEL,
    RAG_EMBED_MODEL,
)

SETTINGS_FILE = DATA_DIR / "settings.json"
logger = logging.getLogger(__name__)

DEFAULTS = {
    "local_model": OLLAMA_CHAT_MODEL,
    "openrouter_model": OPENROUTER_MODEL,
    "custom_prompt": "You are Gerty, a helpful AI assistant. Always identify as Gerty. Format replies in Markdown: use **bold**, headings (##), bullet lists, numbered lists, and code blocks (```language) when helpful. Use emojis sparingly for clarity.",
    "provider": "local",  # "local" | "openrouter"
    "rag_chat_model": RAG_CHAT_MODEL,  # "__use_chat__" = use local_model; or command-r7b etc for RAG-optimized
    "rag_embed_model": RAG_EMBED_MODEL,
    "memory_enabled": True,
}


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    """Load settings from disk. Returns defaults for missing keys."""
    result = dict(DEFAULTS)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                result.update({k: v for k, v in data.items() if k in DEFAULTS})
        except (json.JSONDecodeError, OSError) as e:
            logger.debug("Settings load failed: %s", e)
    return result


def _validate_value(key: str, value) -> bool:
    """Validate a setting value. Returns True if valid."""
    if key == "provider":
        return value in ("local", "openrouter")
    if key == "memory_enabled":
        return isinstance(value, bool)
    if key in ("local_model", "openrouter_model", "rag_chat_model", "rag_embed_model"):
        return isinstance(value, str)
    if key == "custom_prompt":
        return isinstance(value, str)
    return True


def save(updates: dict) -> dict:
    """Save settings. Only updates provided keys. Returns full settings."""
    _ensure_data_dir()
    current = load()
    for k, v in updates.items():
        if k in DEFAULTS and _validate_value(k, v):
            current[k] = v
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(current, f, indent=2)
    except OSError as e:
        logger.warning("Settings save failed: %s", e)
        raise
    return current
