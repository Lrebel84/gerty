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

## Gerty vs OpenClaw (single source of truth)

| | Gerty | OpenClaw |
|---|-------|----------|
| **What** | Local assistant: router, tools, voice, UI | Optional action layer: calendar, email, exec, files, browser, ClawHub skills |
| **Where** | `gerty/` package, runs on your machine | Separate daemon (`openclaw daemon start`), Node.js 22+ |
| **When** | Always running when you use Gerty | Only when `GERTY_OPENCLAW_ENABLED=1` |
| **Routing** | Fast-path (time, alarm, etc.) → Gerty tools; everything else → OpenClaw when enabled | Receives non-fast-path requests from Gerty |
| **Security** | **Pre-send screening** (Sprint 10a): blocks risky messages before sending to OpenClaw | dcg-guard, exec-approvals allowlist on OpenClaw side |

**Flow:** User → Gerty (chat/voice/Telegram) → Router → Fast-path tools OR OpenClaw. Before sending to OpenClaw, Gerty runs `screen_openclaw_message()`—blocked requests never reach OpenClaw. See [docs/SECURITY_POLICY.md](SECURITY_POLICY.md).

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
│  classify_intent() → Fast path | OpenClaw (Option A) | Gerty tools / Chat   │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
          ┌─────────────────────────────┼─────────────────────────────┐
          ▼                             ▼                             ▼
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│  Fast path       │         │  OpenClaw        │         │  Gerty tools /   │
│  time, alarm,    │         │  (when enabled)  │         │  Chat            │
│  timer, calc,    │         │  Everything else │         │  (fallback when  │
│  notes, weather, │         │  except fast path│         │  OpenClaw down)  │
│  rag             │         │  Fallback: chat  │         │                  │
└────────┬─────────┘         └────────┬─────────┘         └────────┬─────────┘
         │                            │                            │
         ▼                            ▼                            ▼
┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│  ToolExecutor    │         │  screen_openclaw │         │  SearchTool /    │
│  (instant)       │         │  _message() then │         │  LLM             │
│                  │         │  openclaw-sdk   │         │                  │
└──────────────────┘         └──────────────────┘         └──────────────────┘
         │                            │                            │
         │                   (fallback when OpenClaw down          │
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
| **Router** | `gerty/llm/router.py` | Intent classification (keywords), routing to tools or LLM; Option A: OpenClaw for non-fast-path when enabled |
| **Pipeline** | `gerty/pipeline.py` | Chat pipeline: prompt, history summarization, voice tweaks; calls `router.route_stream()` |
| **ToolExecutor** | `gerty/tools/base.py` | Registers tools by intent; `execute(intent, message)` dispatches to matching tool |
| **Tools** | `gerty/tools/*.py` | TimeDateTool, AlarmsTool, TimersTool, CalculatorTool, SearchTool, RagTool, ScreenVisionTool, MaintenanceTool, PersonalContextTool, AgentFactoryTool, AgentRunnerTool, AgentDesignerTool, IntentOrchestratorTool, etc. |
| **Voice** | `gerty/voice/` | Wake word (Picovoice/openWakeWord), STT (faster-whisper, Moonshine, Vosk, Groq), TTS (Piper, Kokoro), VAD |
| **RAG** | `gerty/rag/` | ChromaDB, embedder (nomic-embed-text), parsers (PDF, Excel, Word); on-demand via RagTool |
| **Personal Context** | `gerty/personal_context.py`, `gerty/tools/personal_context_tool.py` | System 1: goals, projects, routines, controlled updates; see [PERSONAL_CONTEXT_ENGINE.md](PERSONAL_CONTEXT_ENGINE.md) |
| **Agent Factory** | `gerty/agent_factory.py`, `gerty/agent_registry.py`, `gerty/tools/agent_factory_tool.py` | System 2: create/list agents from templates; see [AGENT_FACTORY.md](AGENT_FACTORY.md) |
| **Agent Designer** | `gerty/agent_designer.py`, `gerty/tools/agent_designer_tool.py` | System 3: design/improve agents; see [AGENT_DESIGNER.md](AGENT_DESIGNER.md) |
| **Intent Orchestrator** | `gerty/intent_orchestrator.py`, `gerty/tools/intent_orchestrator_tool.py` | System 4: interpret high-level outcome requests, recommend or invoke best path; see [INTENT_ORCHESTRATOR.md](INTENT_ORCHESTRATOR.md) |
| **UI** | `gerty/ui/` | FastAPI server, PyWebView bridge; frontend in `frontend/` (React, Vite) |
| **Security** | `gerty/security.py` | Trusted tools, forbidden patterns, sensitive paths; `screen_openclaw_message()` before OpenClaw |
| **Heartbeat** | `gerty/heartbeat.py` | Health rotation: diagnostics, friction tail, health tail, incidents; `python -m gerty --heartbeat` |
| **Maintenance** | `gerty/maintenance.py` | Incidents, proposals, tasks; path checks before writes |
| **Observability** | `gerty/observability.py` | Friction log, health log, structured logging |

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
| time | "what time", "what's the time", "current time", "tell me the time" |
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
| personal_context | "my goals", "add goal", "update project", "my routines" |
| agent_factory | "create agent", "list agents" |
| agent_runner | "ask agent X: task", "run agent X: task" |
| agent_designer | "design agent", "improve agent", "suggest agent for" |
| intent_orchestrator | "help me explore", "best next step", "turn this into", "organize this" |
| chat / complex | Fallback; may trigger web intent fallback |

**OpenClaw (when enabled):** Option A—everything except fast-path goes to OpenClaw. Gerty passes full chat history and custom prompt. When the daemon is unreachable, Gerty falls back to Ollama/OpenRouter chat. **Headless:** Use `security: "full"` + `ask: "off"` with **dcg-guard** (blocks rm -rf, destructive git, etc.), or allowlist commands. **Caveat:** OpenClaw/Grok sometimes returns invented responses instead of using tools; behaviour is inconsistent. See [docs/OPENCLAW_INTEGRATION.md](OPENCLAW_INTEGRATION.md) and [docs/OPENCLAW_DIAGNOSIS.md](OPENCLAW_DIAGNOSIS.md).

---

## Configuration

Key environment variables (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_VOICE_MODEL` | Local LLM |
| `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | Cloud LLM |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_IDS` | Telegram bot |
| `PICOVOICE_ACCESS_KEY` | Wake word |
| `GERTY_OPENCLAW_ENABLED` | OpenClaw integration (files, browser, calendar, email, exec on host, ClawHub skills). OpenClaw uses `~/.openclaw/.env` for its own keys. See [docs/OPENCLAW_INTEGRATION.md](OPENCLAW_INTEGRATION.md) for self-improvement setup. Proactive-agent (ClawHub) runs via system cron; see §8. |
| `GERTY_BROWSE_ENABLED` | Interactive browsing |
| `GERTY_SYSTEM_TOOLS` | System commands, app launch |

---

## Heartbeat vs Proactive-Agent (avoid confusion)

| Term | What | Where |
|------|------|-------|
| **Gerty heartbeat** | Built-in health rotation: diagnostics, friction logs, incidents. Writes to `data/maintenance/heartbeat/` when noteworthy. | `python -m gerty --heartbeat`; see [docs/HEARTBEAT_AND_CRON.md](HEARTBEAT_AND_CRON.md) |
| **Proactive-agent heartbeats** | ClawHub skill: system cron runs `scripts/proactive-heartbeat.sh` every 4h — runs OpenClaw agent with HEARTBEAT.md checklist, web search, calendar/email checks. | `skills/proactive-agent/`; `notes/areas/proactive-updates.md`; see [docs/OPENCLAW_INTEGRATION.md](OPENCLAW_INTEGRATION.md) §8 |

AGENTS.md "heartbeat poll" = when the proactive-agent skill runs (via cron), it sends a message to the agent; that is the poll. Not the same as `python -m gerty --heartbeat`.

---

## How to Extend

**Adding a new tool:** See [docs/ADDING_TOOLS.md](ADDING_TOOLS.md). Update:

1. `gerty/main.py` – `executor.register(YourTool())`
2. `gerty/llm/router.py` – Intent keywords and routing
3. `gerty/tools/skills_registry.py` – Add to SKILLS
4. `frontend/src/skills.ts` – Mirror entry
5. `COMMANDS.md` – Examples

**OpenClaw integration:** See [docs/OPENCLAW_INTEGRATION.md](OPENCLAW_INTEGRATION.md).

**Discovered a weakness or limitation?** Log it in [docs/IMPROVEMENT_BACKLOG.md](IMPROVEMENT_BACKLOG.md). Critical → fix now. Non-blocking → add to backlog so it is not lost.

---

## Project Structure

```
gerty/
├── main.py              # Entry point
├── config.py            # Environment config
├── pipeline.py          # Chat pipeline
├── gerty/
│   ├── llm/             # Router, Ollama, OpenRouter
│   ├── tools/           # Built-in tools (incl. personal_context, agent_factory)
│   ├── personal_context.py  # System 1: goals, projects, routines
│   ├── agent_factory.py     # System 2: create agents
│   ├── agent_registry.py   # System 2: list/get agents
│   ├── agent_designer.py   # System 3: design/improve agents
│   ├── intent_orchestrator.py  # System 4: interpret outcome requests
│   ├── openclaw/        # OpenClaw client (action execution)
│   ├── rag/             # RAG (ChromaDB, parsers, embedder)
│   ├── voice/           # Wake word, STT, TTS
│   ├── research/        # Deep research
│   ├── telegram/        # Telegram bot
│   ├── ui/              # FastAPI server, PyWebView bridge
│   ├── heartbeat.py     # Health rotation (--heartbeat)
│   ├── security.py      # Trusted tools, forbidden patterns, OpenClaw screening
│   ├── maintenance.py   # Incidents, proposals, tasks
│   ├── observability.py # Friction log, health log
│   └── self_improvement.py  # validate(), format_validation_report (--validate)
├── frontend/            # React SPA
├── templates/           # Agent Factory: base_agent template
├── config/              # model_profiles.json
├── data/knowledge/      # RAG documents
├── data/maintenance/    # Incidents, heartbeat artifacts
├── data/personal_context/  # System 1: profile, goals, projects, routines
├── data/agents/         # System 2: created agents
└── docs/                # Documentation
```

## Systems (beyond build plan)

| System | Purpose | Docs |
|--------|---------|------|
| **System 1: Personal Context** | Goals, projects, routines, preferences; controlled updates | [PERSONAL_CONTEXT_ENGINE.md](PERSONAL_CONTEXT_ENGINE.md) |
| **System 2: Agent Factory** | Create and list agents from templates; invoke agents | [AGENT_FACTORY.md](AGENT_FACTORY.md) |
| **System 3: Agent Designer** | Design/improve agents with high-quality specs; draft-first | [AGENT_DESIGNER.md](AGENT_DESIGNER.md) |
| **System 4: Intent Orchestrator** | Interpret high-level outcome requests; recommend or invoke best path | [INTENT_ORCHESTRATOR.md](INTENT_ORCHESTRATOR.md) |
