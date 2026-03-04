# Changelog

All notable changes to the Gerty project are documented in this file.

## [0.1.0] - 2025-03-04

Initial implementation of Gerty, a local Jarvis/Alexa-style voice assistant.

### Added

#### Core Infrastructure
- **Config** (`gerty/config.py`) – Environment-based configuration for Ollama, OpenRouter, Telegram, Porcupine, and model paths
- **Ollama client** (`gerty/llm/ollama_client.py`) – Local LLM chat via Ollama API
- **OpenRouter client** (`gerty/llm/openrouter_client.py`) – Cloud LLM access (Claude, GPT, etc.) via OpenAI-compatible API
- **Model router** (`gerty/llm/router.py`) – Intent classification, tool dispatch, and routing between Ollama and OpenRouter

#### Voice Pipeline
- **Audio capture/playback** (`gerty/voice/audio.py`) – Microphone input and speaker output via sounddevice
- **Wake word detection** (`gerty/voice/wake_word.py`) – Porcupine-based detection for "computer"
- **Speech-to-text** (`gerty/voice/stt.py`) – Vosk streaming recognition (offline)
- **Text-to-speech** (`gerty/voice/tts.py`) – Piper synthesis (offline)
- **Voice loop** (`gerty/voice/loop.py`) – End-to-end flow: wake word → record → STT → router → TTS → play

#### Toolkit
- **Time/date tool** (`gerty/tools/time_date.py`) – Current time and date
- **Alarms tool** (`gerty/tools/alarms.py`) – Set, list, and cancel alarms (JSON storage)
- **Timers tool** (`gerty/tools/timers.py`) – Countdown timers with in-memory storage and callbacks
- **Tool executor** (`gerty/tools/base.py`) – Base interface and dispatcher for tools

#### Desktop UI
- **React frontend** (`frontend/`) – Chat interface with dark theme, Tailwind CSS v4, Vite
- **Chat window** – Main chat view with message history
- **Sidebar** – Extensible panel for future tools
- **FastAPI server** (`gerty/ui/server.py`) – Serves static frontend and `/api/chat` endpoint
- **PyWebView bridge** (`gerty/ui/bridge.py`) – JS API for desktop integration
- **Main entry** (`gerty/main.py`) – Launches server, Telegram bot, voice loop, and PyWebView window

#### Mobile Control
- **Telegram bot** (`gerty/telegram/bot.py`) – Commands: `/start`, `/chat`, `/time`, `/alarm`, `/timer`; plain text chat; authorized users only via `TELEGRAM_CHAT_IDS`

#### Desktop Integration
- **Desktop launcher** (`gerty.desktop`) – Pop!_OS/Ubuntu launcher with `StartupWMClass` for dock pinning
- **Icon** (`assets/gerty.svg`) – Microphone-style app icon
- **Install script** (`scripts/install_desktop.sh`) – Installs `.desktop` file to `~/.local/share/applications/`
- **Model download script** (`scripts/download_models.sh`) – Downloads Vosk and Piper models

#### Configuration
- **Extended `.env.example`** – Variables for Ollama, OpenRouter, Telegram, Porcupine, and model paths
- **`requirements.txt`** – Dependencies including pywebview[qt6], vosk, piper-tts, pvporcupine, ollama, openai, python-telegram-bot, fastapi, uvicorn

#### Documentation
- **README.md** – Setup, usage, project structure, and system dependencies
- **CHANGELOG.md** – This file

### Changed (post-0.1.0)
- **PyWebView**: Force Qt backend (`gui="qt"`) to skip GTK and avoid load failures
- **Chat UI**: Make message text selectable for copy/paste (`select-text`)
- **Multi-model routing**: Optional per-intent Ollama models (chat, reasoning) for AMD Ryzen 9 / 27GB RAM setups
- **Config**: `OLLAMA_CHAT_MODEL`, `OLLAMA_TOOL_MODEL`, `OLLAMA_REASONING_MODEL` with fallback to `OLLAMA_MODEL`
- **README**: Model recommendations for high-end APU hardware

### Technical Notes
- PyWebView uses Qt6 backend (`pywebview[qt6]`) for Linux; requires `libxcb-cursor0` and `libxcb-xinerama0`
- Voice features require: PICOVOICE_ACCESS_KEY, Vosk model, Piper voice model
- Ollama must be running for local LLM; OpenRouter is optional for complex queries
