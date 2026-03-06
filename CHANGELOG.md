# Changelog

All notable changes to the Gerty project are documented in this file.

**Reverting to a past commit?** You must run `cd frontend && npm run build && cd ..` after reverting. The app serves built JS from `frontend/dist/`, which is not in git—reverting source alone leaves old/broken code in `dist/`.

---

## [0.8.9] - 2025-03-06

### Intent & Prompt Fixes

- **Intent classification**: "date" and "time" now use whole-word matching. Queries like "what is your info dated" or "why is your info outdated" no longer route to the date tool; they go to chat.
- **Grounding note**: GROUNDING_NOTE ("acknowledge you may not have up-to-date information") now applies only to local models. OpenRouter models (Grok, etc.) no longer get this instruction, so they stop adding "my info's a bit dated" disclaimers.

---

## [0.8.8] - 2025-03-06

### Voice + OpenRouter + Groq STT

Voice chat now works with OpenRouter (cloud LLM) and Groq STT. No changes to mic button logic.

- **OpenRouter for voice**: Select OpenRouter in the chat header; voice uses it. Pipeline only overrides local_model with OLLAMA_VOICE_MODEL when provider is local.
- **Groq STT**: Set `stt_backend` to `groq` or `auto` in Settings → Voice. Restart after changing.
- **Logging**: Voice logs provider and OpenRouter model to `gerty.log` for verification.

---

## [0.8.7] - 2025-03-06

### Mic Button & Voice Processing Fixes

#### Mic doesn't auto-stop
- **Energy fallback**: Reduced `SILENCE_THRESHOLD` from `max(20, ...)` to `max(5, ...)` so VAD_MIN_SILENCE_MS (700ms) is respected. Previously forced ~1.6s of silence with OpenWakeWord frame size.

#### Stuck on "Processing"
- **Voice cancel**: Added `POST /api/voice/cancel` and Cancel button now signals backend to abort. `process_recording` checks for cancel after STT and during LLM streaming.
- **STT timeout**: Reduced from 60s to 25s for faster Vosk fallback when faster-whisper/Groq hangs.

#### Reliability
- **Voice API retries**: `start`, `stop`, and `cancel` now retry up to 3 times with 100ms delay if fetch fails (Qt WebEngine can drop requests).

---

## [0.8.6] - 2025-03-06

### Chat Restored (Network Error Fix)

Text chat was broken with "Error: network error" after attempted OpenRouter/Groq STT changes. This release restores working chat.

#### Changes

- **Non-streaming fallback** – When `POST /api/chat/stream` fails (e.g. Qt WebEngine fetch restriction), the frontend automatically falls back to `POST /api/chat` and displays the full reply.
- **Immediate first-byte** – The stream endpoint now yields a zero-width space before the first LLM token so the client receives a response immediately, avoiding WebEngine timeout.
- **Request logging** – `chat_stream` logs each request to `gerty.log` for debugging.
- **PyWebView debug mode** – DevTools enabled (`debug=True`) to inspect Network tab when issues occur.

#### Revert to This Working Version

A baseline tag was created for easy rollback:

```bash
# Reset to working baseline (discards any later changes)
git reset --hard baseline-working

# IMPORTANT: You MUST rebuild the frontend after reverting
cd frontend && npm run build && cd ..
```

**Why the rebuild is required:** `frontend/dist/` is not in git (it's in `.gitignore`). The app serves the built JavaScript from `dist/`, not the source. Reverting restores source files but leaves `dist/` unchanged—so you can end up with reverted source and old/broken built code. Without rebuilding, reverting may appear to do nothing.

---

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

## [0.5.0] - 2025-03-05

### Long-term Memory & Chat Persistence

#### Added
- **Long-term memory** – Extracts user-stated facts (family, likes, work, etc.) when saving chat; stores in `gerty_memory` ChromaDB collection; merged with docs in RAG queries
- **Fact extraction** – LLM extracts facts from user messages when saving (2+ user messages); only user-stated facts, excludes questions/requests; deduplication via content hash
- **Chat persistence** – `GET/PUT/DELETE /api/chat/history`; history saved after each message and on beforeunload; resume on startup
- **Settings** – `memory_enabled` toggle; "New chat" button clears history
- **Data** – `data/chat_history.json`; `data/rag/chroma_db/` now has `gerty_memory` collection

#### Performance
- **Single embedding per RAG query** – Embed query once, use for both knowledge and memory collections (was 2x Ollama calls)
- **Summarization** – Only when 15+ messages AND no RAG context; skip when RAG provides focus
- **RAG chat model default** – `__use_chat__` so Qwen (or selected local model) used by default; RAG model is optional override
- **RAG latency** – Skip RAG for very short messages (< 15 chars); `keep_alive: "5m"` on embed and chat to keep models loaded; warmup on startup when RAG indexed (preload embed + chat models)

#### Model & Prompt
- **Explicit model passing** – Frontend sends `local_model` and `openrouter_model` with every chat request
- **Model display** – Active local model shown in chat header when using Local provider
- **RAG prompt** – When "Use chat model": softer context ("When relevant, you may use... Keep your usual personality"); when RAG model: focused context ("Use this context to answer")

#### Bug Fixes
- **Close handler removed** – `on_closing` (evaluate_js + httpx) blocked window close; rely on beforeunload and per-message save
- **Save on close** – `skip_extract=true` for quick save; extraction only on normal message saves

## [0.6.0] - 2025-03-05

### Security & Robustness (Build Review)

#### Security
- **Path traversal fix** – SPA static file serving now resolves paths and enforces they stay under `FRONTEND_DIST`
- **Error sanitization** – Chat, stream, RAG index, and Telegram errors return generic user-facing messages; full exceptions logged server-side
- **TELEGRAM_CHAT_IDS** – Safer parsing with validation for invalid/malformed input

#### Observability
- **Logging** – Added structured logging across server, RAG, LLM, voice, settings, and tools; replaced silent `except Exception: pass` with `logger.debug`/`logger.warning`/`logger.exception`
- **Print removed** – Ollama availability warnings now use `logger.warning`

#### Feature Parity
- **Chat pipeline** (`gerty/pipeline.py`) – Shared pipeline applies RAG, memory, custom prompt before routing; Voice and Telegram now get RAG, memory, and custom prompt (previously bypassed)

#### Robustness
- **Settings validation** – `provider`, `memory_enabled`, and string fields validated before save
- **Configurable values** – New env vars: `SERVER_HOST`, `ALARM_POLL_INTERVAL`, `HTTP_TIMEOUT_*`, `OLLAMA_*_TIMEOUT`, `RAG_TOP_K`, `RAG_MIN_MSG_LEN`, `RAG_SUMMARIZE_THRESHOLD`, `RAG_RELEVANCE_THRESHOLD`
- **RAG store** – Uses `RAG_EMBED_MODEL` from config consistently

#### RAG Polish
- **Relevance threshold** – `RAG_RELEVANCE_THRESHOLD` filters out chunks with distance above threshold (default 0.9)
- **Grounding note** – When no RAG context, prompt includes a note to acknowledge uncertainty on external topics (movies, current events)

#### Quality
- **Tests** – Added `tests/` with pytest: router intent/parse_timer_duration, settings load/save/validation, app creation (19 tests)
- **pyproject.toml** – Pytest config, ruff lint/format settings

### New Tools (Tier 1 & 2)

#### Tier 1 – Zero deps
- **Calculator** – Arithmetic and percentages ("what is 15% of 80")
- **Unit conversion** – Temperature, length, weight ("convert 5 miles to km")
- **Random** – Coin flip, dice roll, pick number, choose from options
- **Quick notes** – Add, list, clear notes (`data/notes.txt`)
- **Stopwatch** – Start, elapsed, stop
- **Timezone** – Time in another city (London, Tokyo, NYC, etc.)

#### Tier 2 – Minimal deps
- **Weather** – Current conditions via Open-Meteo, no API key ("weather in London")
- **Web search** – DuckDuckGo via `duckduckgo-search` ("search for Python tutorial")
- **Pomodoro** – 25 min work, 5 min break; notifications when each phase ends

#### Dependencies
- Added `duckduckgo-search>=6.0.0` (optional, for search tool)

#### Documentation
- **COMMANDS.md** – User guide listing all tools and example commands
- **README** – Updated toolkit list and link to COMMANDS.md

---

## [0.7.0] - 2025-03-05

### Real-time Voice Overhaul

#### STT (Speech-to-Text)
- **faster-whisper** – Replaces Vosk as default; 4x faster, CTranslate2 backend. Models: tiny, base, small, medium, large-v3 (download on first use)
- **Groq Whisper** – Optional cloud backend (216x real-time); set `STT_BACKEND=groq` and `GROQ_API_KEY`
- **Vosk** – Still available as fallback (legacy)
- **Settings** – STT backend and faster-whisper model selectable in Settings → Voice – Speech recognition (STT)

#### VAD (Voice Activity Detection)
- **Silero VAD** – Replaces energy-based silence detection; accurate end-of-speech detection
- **Single-click flow** – Click mic once; auto-stops when you finish speaking (or click again to stop early)
- **Config** – `VAD_MIN_SILENCE_MS` (default 700ms) for tuning

#### Latency Improvements
- **Voice skips RAG** – Voice queries bypass RAG retrieval and history summarization for faster replies
- **OLLAMA_VOICE_MODEL** – Optional faster model for voice (e.g. `qwen2.5:3b`); unset = use chat model
- **VOICE_RESPONSE_TIMEOUT** – Reduced from 60s to 30s

#### Dependencies
- **silero-vad** – Voice activity detection
- **faster-whisper** – Local STT (replaces Vosk as default)

#### Download Script
- **faster-whisper** – Script pre-downloads base model; others (tiny, small, medium, large-v3) download on first use

#### Config & Docs
- **.env.example** – `STT_BACKEND`, `FASTER_WHISPER_MODEL`, `FASTER_WHISPER_DEVICE`, `GROQ_API_KEY`, `VAD_MIN_SILENCE_MS`, `OLLAMA_VOICE_MODEL`

---

## [0.7.1] - 2025-03-05

### Revert: Streaming Attempt & Voice Regression

#### What Was Done
- Attempted to add streaming for faster perceived response time (display tokens as they arrive instead of waiting for full response).
- Changes made: SSE format for stream, `skip_summarization` for HTTP chat, no-buffer headers, frontend SSE parsing.
- After issues, reverted to plain-text streaming; then fully reverted `gerty/pipeline.py`, `gerty/ui/server.py`, and `frontend/src/App.tsx` to last committed state.
- Restored voice loop to start without requiring `PICOVOICE_ACCESS_KEY` (push-to-talk).
- Added minimal sidebar width/resize props to `App.tsx` to match current `Sidebar` component.

#### Known Regression
- **Voice chat was working absolutely fine** (with only a slight delay waiting for the full response block) until streaming changes were attempted.
- **Voice has not worked since** and still is not working: it gets stuck on "Processing" with no response.
- Text chat works; the regression is specific to voice.

---

## [0.7.2] - 2025-03-05

### Voice Chat Fixes

#### Bug Fixes
- **VAD init**: Set `vad = None` when Silero VAD fails to load; previously `on_wake()` called `vad.reset()` and re-raised `ImportError`, crashing the recording loop.
- **Stop signal**: Added HTTP endpoints `POST /api/voice/start` and `POST /api/voice/stop`; frontend now uses HTTP instead of PyWebView bridge (bridge can fail to invoke in some contexts).
- **Mic blocking**: Added 50ms timeout on `capture.read()` so the loop can check stop request when sounddevice blocks (e.g. under PyWebView/Qt).
- **Auto-stop timing**: Increased `VAD_MIN_SILENCE_MS` default from 700ms to 2000ms; energy fallback now derives threshold from this (avoids stopping on brief pauses).
- **STT backend**: Voice loop always uses Vosk; added fallback logic in `_create_stt_backend` when preferred backend fails.

#### Changed
- **Config**: `VAD_MIN_SILENCE_MS` default is now 2000.
- **Energy fallback**: Uses `VAD_MIN_SILENCE_MS` and frame length for correct silence threshold across PTT and wake-word modes.

#### Note
- Ensure `VOSK_MODEL_PATH` in `.env` matches the installed model (e.g. `vosk-model-small-en-us-0.15`).

---

## [0.7.3] - 2025-03-05

### Voice Chat Restored

Voice chat is working again after fixes for mic button, STT hangs, and VAD sensitivity.

#### Added
- **STT backend choice** – Voice loop now respects Settings; choose faster-whisper, Vosk, Groq, or Auto (Groq when WiFi, else local)
- **OLLAMA_VOICE_MODEL** – Voice uses `OLLAMA_VOICE_MODEL` when set (e.g. `qwen2.5:3b`) for faster replies
- **Vosk fallback** – When faster-whisper times out or fails (e.g. under PyWebView), automatically falls back to Vosk
- **Auto mode** – STT backend "auto" uses Groq when `GROQ_API_KEY` and network available; else faster-whisper

#### Bug Fixes
- **Mic button** – PTT start now handled when `capture.read()` times out; previously only stop was checked
- **Capture timeout** – Increased from 50ms to 150ms for OpenWakeWord (1280 samples @ 16kHz = 80ms block duration)
- **VAD sensitivity** – Silero threshold 0.5→0.6; energy fallback 800→1200; ambient noise no longer keeps recording
- **VAD_MIN_SILENCE_MS** – Default reduced to 700ms for faster end-of-speech detection

#### Changed
- **STT timeout** – Reduced from 45s to 20s; fallback to Vosk on timeout
- **Config** – `STT_BACKEND` default `faster_whisper`; `VAD_MIN_SILENCE_MS` default 700

#### Logging
- **GERTY_LOG_LEVEL=INFO** – Logs voice timing (STT, LLM, TTS) and backend choice to `gerty.log` for debugging

---

## [0.7.4] - 2025-03-05

### RAG as Tool & Llama 3.1

#### Added
- **RAG tool** – Query documents on demand: "check documentation", "retrieve", "search my docs", etc. Routes to RAG tool like other tools.
- **Llama 3.1 8B** – Added to model recommendations, download script, and RAG chat model dropdown

#### Changed
- **RAG default off** – `rag_enabled` defaults to `False`; RAG runs only when you ask (tool) or enable in Settings
- **Pipeline** – RAG context injected only when `rag_enabled` is True in Settings
- **Settings** – "Enable RAG on all messages" clarifies: when off, use "check documentation" to query

#### Documentation
- **COMMANDS.md** – Updated Knowledge Base section with RAG tool phrases

---

## [0.8.0] - 2025-03-05

### Voice Speed & Reliability Upgrades

RAG and memory injection removed from pipeline; voice path optimized for low latency.

#### Changed
- **RAG on-demand only** – Automatic RAG/memory injection removed from pipeline. Enable in Settings, then say "check my docs for X", "search my files for Y", etc. No context-window bloat = faster chat and voice.
- **Voice path** – No RAG, no summarization, minimal history (last 2 exchanges). Optimized for sub-second response feel.
- **Temperature** – `OLLAMA_TEMPERATURE=0.1` (default) for factual responses; reduces hallucinations.
- **RagTool** – Respects `rag_enabled`; returns "RAG is disabled in Settings" when off. Expanded keywords: "search my files", "check my files", "what do my files say".

#### Added
- **OLLAMA_TEMPERATURE** – Configurable (default 0.1) for factual/control assistant use.
- **RAG keywords** – "search my files", "what do my files say", "look in my files", "check my files", "check files for".

#### Model recommendations
- **Voice**: `OLLAMA_VOICE_MODEL=llama3.2` (3B) for fast replies.
- **Chat**: `OLLAMA_CHAT_MODEL=llama3.1:8b` for balance and fewer hallucinations.
- **STT**: Groq or faster-whisper `tiny` for voice on CPU.

#### Documentation
- **PERFORMANCE.md** – Updated for RAG tool-only, voice optimizations, model table.
- **README** – Model recommendations, RAG on-demand description, STT tips.
- **download_models.sh** – Pre-downloads faster-whisper `tiny` in addition to `base`.

---

## [0.8.1] - 2025-03-05

### STT-Friendly Alarms, Timers & Weather

#### Added
- **Number words for alarms/timers** – Voice: "set alarm for eleven oh five", "seven thirty am", "timer for five minutes", "twenty minutes". STT may transcribe digits as words.
- **number_words module** – Converts "eleven oh five" → 11:05, "five minutes" → 5 minutes.

#### Fixed
- **Weather city extraction** – "forecast for" now checked before "weather for" (avoids matching "weather fore" in "forecast"). Handles STT "ecast for sheffield" when "weather for" is dropped. Strips time qualifiers ("this afternoon", "tomorrow") from location.
- **Alarm "7 30 am"** – No longer misparses "30 am" as hour; requires 1–12 for am/pm.

---

## [0.8.2] - 2025-03-05

### Kokoro-82M TTS

#### Added
- **Kokoro TTS** – Optional TTS backend with ElevenLabs-like quality. 82M params, ~80MB, CPU-friendly.
- **TTS backend selection** – Settings → Voice – Text-to-speech: Piper (fast) or Kokoro.
- **Kokoro voices** – 20 American English voices (af_sarah, af_bella, am_liam, etc.). British English and other languages available.
- **Download script** – `./scripts/download_models.sh` now fetches Kokoro model files.

#### Config
- `TTS_BACKEND=kokoro` in `.env` to use Kokoro
- `kokoro_voice` in Settings (default: af_sarah)

---

## [0.8.4] - 2025-03-05

### Moonshine STT (The "Kokoro of STT")

#### Added
- **Moonshine STT** – Optional STT backend from Useful Sensors. Variable-length processing: only computes the exact length of your audio (no 30s Whisper chunks). ~5x faster than Whisper on short voice commands.
- **Models** – `tiny` (27M params) or `base` (61M params). English accuracy beats Whisper's smaller models.
- **Settings** – STT backend dropdown: Moonshine; model selector (tiny/base).
- **Config** – `STT_BACKEND=moonshine`, `MOONSHINE_MODEL=base` in `.env`.

#### Dependencies
- `transformers[torch]>=5.3.0` – Required for Moonshine. Models download from Hugging Face on first use.

#### Documentation
- **README** – Moonshine STT option, install note.
- **.env.example** – Moonshine config comments.

---

## [0.8.3] - 2025-03-05

### Kokoro TTS Fixes & Docs

#### Fixed
- **Kokoro "not installed"** – Desktop launcher uses project `.venv`; `kokoro-onnx` must be installed there. Run `./.venv/bin/pip install kokoro-onnx` (or `pip install -r requirements.txt` in venv).

#### Documentation
- **README** – Voice selection: choose voice in Settings and click Save to set as default. Kokoro install note for venv/desktop launcher.
- **CHANGELOG** – This entry.

---

## [0.8.5] - 2025-03-05

### Voice UX: Immediate Feedback & Streaming TTS

#### Added
- **Immediate STT display** – Your transcribed speech appears in the chat as soon as STT completes, before the assistant replies. Confirms what was heard.
- **Streaming TTS** – Assistant starts speaking as soon as the first sentence is ready. No longer waits for the full reply block.
- **Streaming assistant text** – Assistant message updates in the chat as the LLM streams tokens.
- **New callbacks** – `on_user_text`, `on_assistant_content`, `stream_router_callback` for phased voice updates.

#### Changed
- **Voice loop** – Uses `chat_pipeline_stream` for voice; plays TTS sentence-by-sentence (on `.` `!` `?` `\n`).
- **Frontend** – `__gertyAddVoiceUserMessage`, `__gertySetVoiceAssistantContent` for immediate user display and streaming assistant.
- **Moonshine STT** – Switched to model-specific API with `max_length` to prevent hallucination loops; increased timeout to 60s.
- **Settings** – STT tip: faster-whisper (tiny/base) recommended for lowest latency.

#### Fixed
- **Moonshine hanging** – Model-specific `MoonshineForConditionalGeneration` + `AutoProcessor` with token limit prevents infinite generation.

---

## Known Issues

- **Restart required for STT changes** – Changing STT backend or model in Settings requires restarting the app.
- **Hallucination on non-RAG topics** – When asked about things not in memory/docs (e.g. movies), the model answers from training and may invent facts (e.g. wrong cast). RAG context is irrelevant in those cases. *Expected LLM behaviour; consider grounding external queries.*
