"""Gerty configuration from environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Logging: WARNING default, INFO for debugging (e.g. GERTY_LOG_LEVEL=INFO)
LOG_LEVEL = os.getenv("GERTY_LOG_LEVEL", "WARNING").upper()

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_ollama_default = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_MODEL = _ollama_default

# Multi-model strategy (optional - for AMD Ryzen 9 / 27GB RAM setups)
# Brain: chat/personality. Hand: tools. Specialist: deep reasoning/coding.
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "") or _ollama_default
OLLAMA_TOOL_MODEL = os.getenv("OLLAMA_TOOL_MODEL", "") or _ollama_default
OLLAMA_REASONING_MODEL = os.getenv("OLLAMA_REASONING_MODEL", "") or _ollama_default
# Voice: faster model for low-latency voice replies (e.g. llama3.2). Empty = use chat model.
OLLAMA_VOICE_MODEL = os.getenv("OLLAMA_VOICE_MODEL", "") or None
# Temperature: 0.0-0.1 for factual/control assistant; higher for creative. Reduces hallucinations.
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.1"))

# OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def _parse_telegram_chat_ids() -> list[int]:
    """Parse TELEGRAM_CHAT_IDS, skipping invalid entries."""
    result: list[int] = []
    raw = os.getenv("TELEGRAM_CHAT_IDS", "")
    for x in raw.split(","):
        s = x.strip()
        if not s or not s.isdigit():
            continue
        try:
            result.append(int(s))
        except (ValueError, OverflowError):
            continue
    return result


TELEGRAM_CHAT_IDS = _parse_telegram_chat_ids()

# Porcupine wake word
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY", "")

# Speech-to-text backend: faster_whisper, vosk, groq, or auto (Groq when WiFi, else local)
STT_BACKEND = os.getenv("STT_BACKEND", "faster_whisper")
# tiny=fastest for voice on CPU; base=balanced; small/medium/large-v3=better accuracy, slower
FASTER_WHISPER_MODEL = os.getenv("FASTER_WHISPER_MODEL", "base")
FASTER_WHISPER_DEVICE = os.getenv("FASTER_WHISPER_DEVICE", "cpu")  # cpu or cuda
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# VAD (Silero) / energy fallback: min silence before end-of-speech (ms)
# 700=fastest, 1200=balanced, 2000=noisy environments
VAD_MIN_SILENCE_MS = int(os.getenv("VAD_MIN_SILENCE_MS", "700"))

# Model paths (resolved from project root)
_vosk_path = os.getenv("VOSK_MODEL_PATH", "models/vosk/vosk-model-small-en-us-0.15")
_piper_path = os.getenv("PIPER_VOICE_PATH", "models/piper/en_US-amy-medium")
VOSK_MODEL_PATH = PROJECT_ROOT / _vosk_path if not Path(_vosk_path).is_absolute() else Path(_vosk_path)
PIPER_VOICE_PATH = PROJECT_ROOT / _piper_path if not Path(_piper_path).is_absolute() else Path(_piper_path)

# TTS backend: piper (default) or kokoro (Kokoro-82M, ElevenLabs-like quality)
TTS_BACKEND = os.getenv("TTS_BACKEND", "piper").lower()
_kokoro_dir = os.getenv("KOKORO_MODEL_DIR", "models/kokoro")
KOKORO_DIR = PROJECT_ROOT / _kokoro_dir if not Path(_kokoro_dir).is_absolute() else Path(_kokoro_dir)
KOKORO_MODEL_PATH = KOKORO_DIR / "kokoro-v1.0.onnx"
KOKORO_VOICES_PATH = KOKORO_DIR / "voices-v1.0.bin"

# Data directory for alarms etc.
DATA_DIR = PROJECT_ROOT / "data"
ALARMS_FILE = DATA_DIR / "alarms.json"
CHAT_HISTORY_FILE = DATA_DIR / "chat_history.json"

# RAG knowledge base
KNOWLEDGE_DIR = DATA_DIR / "knowledge"
RAG_DIR = DATA_DIR / "rag"
RAG_EMBED_MODEL = os.getenv("RAG_EMBED_MODEL", "nomic-embed-text")
RAG_CHAT_MODEL = os.getenv("RAG_CHAT_MODEL", "__use_chat__")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_MIN_MSG_LEN = int(os.getenv("RAG_MIN_MSG_LEN", "15"))
RAG_SUMMARIZE_THRESHOLD = int(os.getenv("RAG_SUMMARIZE_THRESHOLD", "15"))
# Max distance for relevance (Chroma uses cosine distance; lower = better; typical keep < 0.8)
RAG_RELEVANCE_THRESHOLD = float(os.getenv("RAG_RELEVANCE_THRESHOLD", "0.9"))

# Server
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
ALARM_POLL_INTERVAL = int(os.getenv("ALARM_POLL_INTERVAL", "5"))

# HTTP timeouts (seconds)
HTTP_TIMEOUT_OLLAMA = float(os.getenv("HTTP_TIMEOUT_OLLAMA", "5"))
VOICE_RESPONSE_TIMEOUT = float(os.getenv("VOICE_RESPONSE_TIMEOUT", "30"))
HTTP_TIMEOUT_OPENROUTER = float(os.getenv("HTTP_TIMEOUT_OPENROUTER", "15"))
OLLAMA_CHAT_TIMEOUT = float(os.getenv("OLLAMA_CHAT_TIMEOUT", "180"))
OLLAMA_HEALTH_TIMEOUT = float(os.getenv("OLLAMA_HEALTH_TIMEOUT", "2"))
