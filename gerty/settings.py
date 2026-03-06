"""Persistent user settings for Gerty."""

import json
import logging
from pathlib import Path

from gerty.config import (
    DATA_DIR,
    OLLAMA_CHAT_MODEL,
    OPENROUTER_MODEL,
    PIPER_VOICE_PATH,
    RAG_CHAT_MODEL,
    RAG_EMBED_MODEL,
)

SETTINGS_FILE = DATA_DIR / "settings.json"
logger = logging.getLogger(__name__)

# Default piper voice: use last part of path (e.g. en_US-amy-medium)
_piper_name = getattr(PIPER_VOICE_PATH, "name", None) or str(PIPER_VOICE_PATH).split("/")[-1]
_DEFAULT_PIPER_VOICE = _piper_name.replace(".onnx", "") if _piper_name else "en_US-amy-medium"

DEFAULTS = {
    "local_model": OLLAMA_CHAT_MODEL,
    "openrouter_model": OPENROUTER_MODEL,
    "custom_prompt": "You are Gerty, a helpful AI assistant. Always identify as Gerty. Format replies in Markdown: use **bold**, headings (##), bullet lists, numbered lists, and code blocks (```language) when helpful. Use emojis sparingly for clarity.",
    "provider": "local",  # "local" | "openrouter"
    "rag_enabled": False,  # RAG off by default; use "check documentation" or enable in Settings
    "rag_chat_model": RAG_CHAT_MODEL,  # "__use_chat__" = use local_model; or command-r7b etc for RAG-optimized
    "rag_embed_model": RAG_EMBED_MODEL,
    "memory_enabled": True,
    "piper_voice": _DEFAULT_PIPER_VOICE,
    "tts_backend": "piper",  # piper | kokoro (Kokoro-82M, ElevenLabs-like)
    "kokoro_voice": "af_sarah",  # Kokoro voice (af_sarah, af_bella, am_liam, etc.)
    "stt_backend": "faster_whisper",  # faster_whisper | moonshine | vosk | groq | auto
    "faster_whisper_model": "base",  # tiny | base | small | medium | large-v3
    "moonshine_model": "base",  # tiny (27M) | base (61M) – variable-length, ~5x faster than Whisper on short commands
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
    if key == "stt_backend":
        return value in ("vosk", "faster_whisper", "moonshine", "groq", "auto")
    if key == "tts_backend":
        return value in ("piper", "kokoro")
    if key in ("memory_enabled", "rag_enabled"):
        return isinstance(value, bool)
    if key in ("local_model", "openrouter_model", "rag_chat_model", "rag_embed_model", "piper_voice", "faster_whisper_model", "moonshine_model", "tts_backend", "kokoro_voice"):
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
