"""Gerty configuration from environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_ollama_default = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_MODEL = _ollama_default

# Multi-model strategy (optional - for AMD Ryzen 9 / 27GB RAM setups)
# Brain: chat/personality. Hand: tools. Specialist: deep reasoning/coding.
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "") or _ollama_default
OLLAMA_TOOL_MODEL = os.getenv("OLLAMA_TOOL_MODEL", "") or _ollama_default
OLLAMA_REASONING_MODEL = os.getenv("OLLAMA_REASONING_MODEL", "") or _ollama_default

# OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_IDS = [
    int(x.strip())
    for x in os.getenv("TELEGRAM_CHAT_IDS", "").split(",")
    if x.strip().isdigit()
]

# Porcupine wake word
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY", "")

# Model paths (resolved from project root)
_vosk_path = os.getenv("VOSK_MODEL_PATH", "models/vosk/vosk-model-small-en-us-0.22")
_piper_path = os.getenv("PIPER_VOICE_PATH", "models/piper/en_US-amy-medium")
VOSK_MODEL_PATH = PROJECT_ROOT / _vosk_path if not Path(_vosk_path).is_absolute() else Path(_vosk_path)
PIPER_VOICE_PATH = PROJECT_ROOT / _piper_path if not Path(_piper_path).is_absolute() else Path(_piper_path)

# Data directory for alarms etc.
DATA_DIR = PROJECT_ROOT / "data"
ALARMS_FILE = DATA_DIR / "alarms.json"
