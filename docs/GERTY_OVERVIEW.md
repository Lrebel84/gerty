# Gerty Overview

**Hand this document to a developer or AI to understand what Gerty is and how it works.**

---

## What is Gerty?

Gerty is a **local AI voice assistant** (Jarvis/Alexa-style) that runs entirely on your machine. It is designed to be **private by default**—your data stays local. You interact via:

- **Desktop app** – Chat UI with sidebar
- **Voice** – Wake word ("our Gurt"), speech-to-text, text-to-speech, single-click mic
- **Telegram** – Commands from your phone

Gerty routes your messages to built-in tools (time, alarms, search, etc.) or to an LLM (Ollama locally, OpenRouter in the cloud). It can also use **OpenClaw** for action execution (files, browser, calendar, email) when enabled, and **RAG** for searching your documents.

---

## Request Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  INGRESS                                                                     │
│  • Chat UI (React SPA)  • Voice (wake word / PTT)  • Telegram bot            │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  FastAPI Server (port 8765)                                                  │
│  POST /api/chat  |  POST /api/chat/stream  |  Voice/Telegram → sync pipeline  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Chat Pipeline (gerty/pipeline.py)                                           │
│  • Custom prompt, history summarization (chat only)                          │
│  • Voice: minimal history, TTS-friendly output                               │
│  • Routes to Router.route_stream() or route()                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Router (gerty/llm/router.py)                                               │
│  classify_intent() → Fast path (instant) or LLM classifier (when OpenClaw)  │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
          ┌─────────────────────────────┼─────────────────────────────┐
          ▼                             ▼                             ▼
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│  Fast path       │         │  OpenClaw        │         │  Gerty tools /   │
│  time, alarm,    │         │  (when enabled)  │         │  Search,         │
│  timer, calc,    │         │  LLM classifier  │         │  Research,       │
│  notes, weather, │         │  → action exec   │         │  Browse, Chat    │
│  rag             │         │                  │         │                  │
└────────┬─────────┘         └────────┬─────────┘         └────────┬─────────┘
         │                            │                            │
         ▼                            ▼                            ▼
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│  ToolExecutor    │         │  openclaw-sdk    │         │  SearchTool /    │
│  (instant)       │         │  agent.execute  │         │  LLM             │
└──────────────────┘         └──────────────────┘         └──────────────────┘
         │                            │                            │
         │                   (or plain chat/complex                │
         │                    → Ollama / OpenRouter)               │
         │                            │                            │
         └────────────────────────────┼────────────────────────────┘
                                      ▼
                              Response to user
```

---

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **main.py** | `gerty/main.py` | Entry point: builds ToolExecutor, Router, FastAPI app; starts server, Telegram bot, alarm loop; opens PyWebView window |
| **Router** | `gerty/llm/router.py` | Intent classification (keywords), routing to tools or LLM; OpenClaw classifier when enabled |
| **Pipeline** | `gerty/pipeline.py` | Chat pipeline: prompt, history summarization, voice tweaks; calls `router.route_stream()` |
| **ToolExecutor** | `gerty/tools/base.py` | Registers tools by intent; `execute(intent, message)` dispatches to matching tool |
| **Tools** | `gerty/tools/*.py` | TimeDateTool, AlarmsTool, TimersTool, CalculatorTool, SearchTool, RagTool, ScreenVisionTool, etc. |
| **Voice** | `gerty/voice/` | Wake word (Picovoice/openWakeWord), STT (faster-whisper, Moonshine, Vosk, Groq), TTS (Piper, Kokoro), VAD |
| **RAG** | `gerty/rag/` | ChromaDB, embedder (nomic-embed-text), parsers (PDF, Excel, Word); on-demand via RagTool |
| **UI** | `gerty/ui/` | FastAPI server, PyWebView bridge; frontend in `frontend/` (React, Vite) |

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/chat` | Non-streaming chat |
| POST | `/api/chat/stream` | Streaming chat (main UI) |
| GET/PUT/DELETE | `/api/chat/history` | Chat history |
| GET/POST | `/api/settings` | User settings |
| GET | `/api/skills` | Skills/tools list |
| GET | `/api/ollama/models` | Ollama model list |
| GET | `/api/openrouter/models` | OpenRouter model list |
| GET/POST | `/api/alarms` | Alarms CRUD |
| GET/POST | `/api/timers` | Timers |
| GET/POST/DELETE | `/api/notes` | Notes |
| GET | `/api/rag/status` | RAG status |
| POST | `/api/rag/index` | Index knowledge folder |
| POST | `/api/voice/start`, `stop`, `cancel` | Voice control |
| GET | `/api/voice/list` | TTS voices |
| GET | `/api/health` | Health check |

---

## Intent Model

The router uses **keyword-based** intent classification. Order matters: specific intents are checked before generic ones.

| Intent | Example keywords |
|--------|------------------|
| time | "time", "what time", "current time" |
| date | "date", "today's date" |
| alarm | "alarm", "set alarm", "wake me" |
| timer | "timer", "countdown" |
| calculator | "calculate", "what is 15 + 27" |
| units | "convert", "miles to" |
| notes | "note", "remember", "add note" |
| weather | "weather", "forecast" |
| rag | "check my docs", "search documentation" |
| search | "search for", "look up", "google" |
| research | "research", "compare and summarize" |
| browse | "browse", "go to", "navigate to" |
| screen_vision | "what am I looking at", "describe my screen" |
| app_launch | "open firefox", "launch vs code" |
| media_control | "play", "pause", "skip" |
| system_command | "lock screen", "suspend" |
| sys_monitor | "cpu usage", "memory usage" |
| chat / complex | Fallback; may trigger web intent fallback |

**OpenClaw (when enabled):** Non-fast-path messages go through an LLM classifier that routes to Gerty or OpenClaw. Calendar, Gmail, Drive, Tasks go to OpenClaw. See [docs/OPENCLAW_INTEGRATION.md](OPENCLAW_INTEGRATION.md).

---

## Configuration

Key environment variables (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_VOICE_MODEL` | Local LLM |
| `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | Cloud LLM |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_IDS` | Telegram bot |
| `PICOVOICE_ACCESS_KEY` | Wake word |
| `GERTY_OPENCLAW_ENABLED` | OpenClaw integration (files, browser, calendar, email). OpenClaw uses `~/.openclaw/.env` for its own keys. |
| `GERTY_BROWSE_ENABLED` | Interactive browsing |
| `GERTY_SYSTEM_TOOLS` | System commands, app launch |

---

## How to Extend

**Adding a new tool:** See [docs/ADDING_TOOLS.md](ADDING_TOOLS.md). Update:

1. `gerty/main.py` – `executor.register(YourTool())`
2. `gerty/llm/router.py` – Intent keywords and routing
3. `gerty/tools/skills_registry.py` – Add to SKILLS
4. `frontend/src/skills.ts` – Mirror entry
5. `COMMANDS.md` – Examples

**OpenClaw integration:** See [docs/OPENCLAW_INTEGRATION.md](OPENCLAW_INTEGRATION.md).


---

## Project Structure

```
gerty/
├── main.py              # Entry point
├── config.py            # Environment config
├── pipeline.py          # Chat pipeline
├── gerty/
│   ├── llm/             # Router, Ollama, OpenRouter
│   ├── tools/           # Built-in tools
│   ├── openclaw/        # OpenClaw client (action execution)
│   ├── rag/             # RAG (ChromaDB, parsers, embedder)
│   ├── voice/           # Wake word, STT, TTS
│   ├── research/        # Deep research
│   ├── telegram/        # Telegram bot
│   └── ui/              # FastAPI server, PyWebView bridge
├── frontend/            # React SPA
├── data/knowledge/      # RAG documents
└── docs/                # Documentation
```
