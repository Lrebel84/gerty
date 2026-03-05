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

## [0.2.0] - 2025-03-05

### Phase 2 Upgrades

#### Bug Fixes
- **WakeWordDetector**: Made `callback` optional (default no-op) so voice loop no longer crashes
- **Alarm cancel**: Now clears all alarms instead of only removing expired ones
- **Voice loop**: Added `logging.warning` when voice fails to start

#### Notifications
- **Notification service** (`gerty/notifications.py`): TTS, system (`notify-send`), and Telegram
- **Alarm trigger loop**: Background thread polls for due alarms; notifies via TTS, system, Telegram
- **Timer callbacks**: Registered in main; timers announce completion via TTS, system, Telegram

#### Backend API
- `GET /api/alarms` – list pending alarms
- `POST /api/alarms/cancel` – cancel all alarms
- `GET /api/timers` – list active timers with remaining time
- `POST /api/timers/cancel` – cancel all timers

#### Sidebar
- Alarms section with list and "Cancel all" button
- Timers section with countdown and "Cancel all" button
- Polls API every 2 seconds

#### Voice Status
- Voice loop reports `listening`, `processing`, `idle` to UI
- Chat header shows real-time voice status

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

## [0.3.0] - 2025-03-06

### Streaming & Model Updates

#### Streaming
- **Ollama client**: Added `chat_stream()` for token-by-token streaming from Ollama API
- **Router**: Added `route_stream()` – streams LLM output; tools return full text at once
- **API**: New `POST /api/chat/stream` endpoint returns plain-text stream
- **Frontend**: Chat uses `fetch` + `ReadableStream` to display tokens as they arrive
- **UI**: Blinking cursor while assistant message is empty during stream

#### Model
- **Default model**: Switched to `qwen2.5:7b` for AMD Ryzen 9 / Radeon 680M / 27GB RAM (balance of speed and quality)
- **`.env`**: `OLLAMA_CHAT_MODEL` and `OLLAMA_REASONING_MODEL` now use `qwen2.5:7b`

#### Changed
- **Server**: `create_app()` now accepts `Router` instance (not just `route` callback) for streaming support
- **Chat**: Always uses HTTP streaming endpoint instead of PyWebView bridge for real-time display

## [0.4.0] - 2025-03-05

### RAG Knowledge Base

#### Added
- **RAG module** (`gerty/rag/`) – Document ingestion and retrieval-augmented generation
  - **Parsers** (`parsers.py`) – PDF (pypdf), Excel/CSV (openpyxl, csv), DOCX (python-docx), TXT/MD, and extensionless text files
  - **Chunker** (`chunker.py`) – ~2000 char chunks with 100 char overlap
  - **Embedder** (`embedder.py`) – Ollama embeddings via `POST /api/embed`; pre-flight check for model availability
  - **Store** (`store.py`) – ChromaDB persistent vector store, `index_folder()`, `query()`, `is_indexed()`, `get_status()`
- **Config** – `KNOWLEDGE_DIR`, `RAG_DIR`, `RAG_EMBED_MODEL`, `RAG_CHAT_MODEL`
- **Settings** – `rag_chat_model`, `rag_embed_model` persisted; RAG chat model dropdown (command-r7b, granite3.2:8b, command-r:35b, "Use chat model"); embedding model dropdown (nomic-embed-text, mxbai-embed-large, bge-m3)
- **Chat flow** – When RAG is indexed, retrieves top-5 chunks, injects into system prompt; optional dedicated RAG chat model (e.g. command-r7b)
- **API** – `GET /api/rag/status`, `POST /api/rag/index`, `GET /api/rag/files`
- **Frontend** – Knowledge base section in Settings: status, "Index now" button, confirmation messages, knowledge folder path, CLI test hint
- **CLI test** – `python3 -m gerty.rag` runs end-to-end RAG check (Ollama, index, query)
- **Dependencies** – chromadb, pypdf, openpyxl, python-docx

#### Bug Fixes
- **ChromaDB metadata** – Sanitize `None` values (ChromaDB rejects them); use `0` for page, `""` for other fields
- **Extensionless files** – Support plain text files with no extension (e.g. "About me and my family")

#### Data Layout
- `data/knowledge/` – User drops files here
- `data/rag/chroma_db/` – ChromaDB persistence
- `data/rag/index.json` – Index metadata; dirs created on app startup
