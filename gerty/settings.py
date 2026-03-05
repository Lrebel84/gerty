"""Persistent user settings for Gerty."""

import json
from pathlib import Path

from gerty.config import (
    DATA_DIR,
    OLLAMA_CHAT_MODEL,
    OPENROUTER_MODEL,
    RAG_CHAT_MODEL,
    RAG_EMBED_MODEL,
)

SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULTS = {
    "local_model": OLLAMA_CHAT_MODEL,
    "openrouter_model": OPENROUTER_MODEL,
    "custom_prompt": "Format replies in Markdown: use **bold**, headings (##), bullet lists, numbered lists, and code blocks (```language) when helpful. Use emojis sparingly for clarity.",
    "provider": "local",  # "local" | "openrouter"
    "rag_chat_model": RAG_CHAT_MODEL,
    "rag_embed_model": RAG_EMBED_MODEL,
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
        except (json.JSONDecodeError, OSError):
            pass
    return result


def save(updates: dict) -> dict:
    """Save settings. Only updates provided keys. Returns full settings."""
    _ensure_data_dir()
    current = load()
    for k, v in updates.items():
        if k in DEFAULTS:
            current[k] = v
    with open(SETTINGS_FILE, "w") as f:
        json.dump(current, f, indent=2)
    return current
