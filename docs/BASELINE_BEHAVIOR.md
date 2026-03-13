# Baseline Behavior — Gerty (Sprint 0)

> Captured 2026-03-13. Do not change runtime behavior until baseline is validated.

## Do Not Break Checklist

Validate these in order after any change:

1. [ ] Local chat must still function
2. [ ] Voice must still function
3. [ ] Fast-path tools must still function
4. [ ] Chat UI must still function
5. [ ] OpenClaw disabled mode must still function
6. [ ] OpenClaw enabled but unavailable mode must still function
7. [ ] OpenClaw enabled and reachable mode must still function

---

## Routing Rules (Option A)

Gerty uses **Option A** routing: nearly everything except fast-path goes to OpenClaw when enabled.

### Fast-path intents (instant Gerty tools)

These bypass OpenClaw and go directly to `ToolExecutor`:

| Intent | Keywords (examples) |
|--------|---------------------|
| `time` | "what time", "current time", "what's the time" |
| `date` | "date", "what date", "today's date", "what day" |
| `alarm` | "alarm", "set alarm", "wake me", "remind me at" |
| `timer` | "timer", "set timer", "countdown", "timer for" |
| `calculator` | "calculate", "what is", "compute", "+", "*" (with extractable math) |
| `units` | "convert", "kilograms to", "miles to", "fahrenheit to" |
| `notes` | "note:", "notes", "remember", "add note", "make a note" |
| `stopwatch` | "stopwatch", "how long has", "elapsed" |
| `timezone` | "time in", "timezone", "time zone" |
| `weather` | "weather", "forecast", "temperature" |
| `random` | "flip", "coin", "roll", "dice", "random", "pick" |
| `rag` | "check documentation", "check docs", "search my docs", "look in my files" |

**Note:** Calendar is *not* in fast-path. It routes to OpenClaw when enabled; CalendarTool is used only when OpenClaw is down.

### Intent classification order (first match wins)

1. `app_launch` — "open X", "launch X", "start X", "run X"
2. `screen_vision` — "what am i looking at", "what's on screen", "screenshot"
3. `sys_monitor` — "cpu usage", "memory usage", "system status"
4. `media_control` — "play", "pause", "skip", "mute"
5. `system_command` — "lock screen", "suspend", "reboot"
6. `timer` (before time)
7. `timezone`
8. `weather`
9. `calendar`
10. `rag`
11. `research`
12. `openclaw_direct` — "list my skills", "list skills"
13. `search` — "search for", "look up", "google"
14. `web_lookup` — "contact details", "when is", "opening hours"
15. `pomodoro`
16. `stopwatch`
17. `time`
18. `date`
19. `calculator` (only if `extract_math()` returns non-None)
20. `units`
21. `random`
22. `notes`
23. `alarm`
24. `complex` — "explain", "write code", "analyze", "summarize"
25. `browse` — only if `GERTY_BROWSE_ENABLED`; "browse", "go to", "visit"
26. `chat` — default

**Special:** `APP_INTEGRATION_KEYWORDS` (calendar, gmail, drive, tasks) return `chat` when matched, but `CALENDAR_KEYWORDS` are checked earlier, so calendar queries get `calendar` intent.

### OpenClaw-enabled behavior

When `GERTY_OPENCLAW_ENABLED=1` and intent is **not** in `FAST_PATH_INTENTS`:

1. Call `openclaw.client.execute()` (or `execute_stream` for voice/streaming)
2. Pass: message, history, system_context = custom_prompt + OPENCLAW_TOOL_INSTRUCTIONS
3. If response ≠ `OPENCLAW_UNAVAILABLE_MSG` → return response
4. **Calendar fallback:** If intent is `calendar` and OpenClaw unavailable → use `CalendarTool`

### Fallback when OpenClaw unavailable

- **Gateway check:** `_gateway_port_reachable()` — port 18789 on 127.0.0.1, 2s timeout
- **Unavailable message:** "I know what you want, but my action system isn't running right now. Try starting OpenClaw with: openclaw daemon start"
- **Calendar:** Falls back to `CalendarTool` (runs `scripts/check_google_calendar.py`)
- **All other intents:** Continue to Gerty chat (Ollama or OpenRouter)

### Web intent fallback (OpenClaw disabled only)

When `GERTY_OPENCLAW_ENABLED=0` and `GERTY_WEB_INTENT_FALLBACK=1` and intent is `chat`:

- Use Ollama or OpenRouter to classify: `web_lookup` | `web_research` | `no_web`
- If `web_lookup` → treat as `search`
- If `web_research` → treat as `research`
- Adds ~5–15s; can misroute chat to research

### Tool intents (non-fast-path)

When not routed to OpenClaw (or after OpenClaw fallback), these go to `ToolExecutor`:

`time`, `date`, `alarm`, `timer`, `calculator`, `units`, `random`, `notes`, `stopwatch`, `timezone`, `weather`, `rag`, `search`, `browse`, `pomodoro`, `app_launch`, `media_control`, `system_command`, `sys_monitor`, `screen_vision`

### App integration query, OpenClaw disabled

If intent is `chat` and message matches `APP_INTEGRATION_KEYWORDS` (calendar, gmail, drive, tasks) and OpenClaw is disabled:

- Return: "I'd love to check your calendar/emails/drive/tasks, but OpenClaw isn't set up. Add GERTY_OPENCLAW_ENABLED=1..."

### Complex intent

- Prefer OpenRouter if available
- Else Ollama with `OLLAMA_REASONING_MODEL`

### Default chat

- Ollama (chat model) if available
- Else OpenRouter if `OPENROUTER_API_KEY` set
- Else "No LLM available. Start Ollama with: ollama serve"

---

## Current Settings Fields

From `gerty/settings.py` (persisted in `data/settings.json`):

| Key | Default | Description |
|-----|---------|-------------|
| `local_model` | OLLAMA_CHAT_MODEL | Ollama model for chat |
| `openrouter_model` | OPENROUTER_MODEL | OpenRouter model |
| `custom_prompt` | "" | Overrides DEFAULT_SYSTEM_PROMPT when non-empty |
| `provider` | "local" | "local" \| "openrouter" |
| `rag_enabled` | False | RAG on-demand via RagTool |
| `rag_chat_model` | RAG_CHAT_MODEL | "__use_chat__" or specific model |
| `rag_embed_model` | RAG_EMBED_MODEL | Embedding model |
| `memory_enabled` | True | Extract facts from chat |
| `piper_voice` | from path | TTS voice |
| `tts_backend` | "piper" | piper \| kokoro |
| `kokoro_voice` | "af_sarah" | Kokoro voice |
| `stt_backend` | "faster_whisper" | faster_whisper \| moonshine \| vosk \| groq \| auto |
| `faster_whisper_model` | "base" | tiny \| base \| small \| medium \| large-v3 |
| `moonshine_model` | "base" | tiny \| base |

---

## Known Brittle Areas

1. **OpenClaw payload:** System context and full history flattened into one formatted message string (`_format_message`). Instruction boundaries can blur; history trimming/summarization not explicit.

2. ~~**Hardcoded path in `openclaw/google_auth.py`**~~ **Fixed (Sprint 1a):** Default is now `~/.openclaw/credentials/google-token.json` via `Path.home()`. Override with `GOOGLE_TOKEN_PATH` env var.

3. **Routing by keyword blocks:** Order-dependent; adding new intents can cause regressions. No formal policy layer.

4. **Calendar fallback as one-off:** Pattern (trusted direct vs OpenClaw vs degraded) is not generalized for other integrations.

5. **`GERTY_OPENCLAW_WEB_ENABLED`:** Defined in config but not used in router. Purpose unclear from codebase.

6. **Bridge history cap:** `ui/bridge.py` keeps last 50 messages; was 20, increased due to OpenClaw empty response at ~20.

---

## Assumptions

- `.env` is loaded from project root
- Ollama default URL: http://localhost:11434
- OpenClaw gateway: ws://127.0.0.1:18789/gateway
- Chat history: `data/chat_history.json`
- Frontend served from `frontend/dist` when present

---

## Files Inspected

- `gerty/llm/router.py`
- `gerty/openclaw/client.py`
- `gerty/config.py`
- `gerty/main.py`
- `gerty/pipeline.py`
- `gerty/settings.py`
- `gerty/ui/server.py`
- `gerty/ui/bridge.py`
- `gerty/openclaw/google_auth.py`
- `gerty/tools/__init__.py`
- `gerty/tools/calendar_tool.py`
- `.env.example`

---

## Uncertain / Not Yet Verified

- Whether `GERTY_OPENCLAW_WEB_ENABLED` was intended to route web search/research to OpenClaw when enabled (currently router does not check it)
- Exact behavior when OpenClaw returns `success=True` but `content` empty (currently returns "OpenClaw ran but returned no output...")
- Voice pipeline behavior when OpenClaw times out (streaming path)
- Telegram bot: uses `chat_pipeline_sync`; same routing as chat UI
