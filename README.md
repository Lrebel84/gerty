# Gerty

Local AI/LLM voice assistant (Jarvis/Alexa-style). Fully private, runs on your machine.

**See [docs/GERTY_OVERVIEW.md](docs/GERTY_OVERVIEW.md)** for developer onboarding: architecture, request flow, Gerty vs OpenClaw, and how to extend. **Security:** [docs/SECURITY_POLICY.md](docs/SECURITY_POLICY.md).

## Features

- **Chat UI**: Modern dark-themed desktop app with chat window and extensible sidebar
- **Voice** (optional): Wake word **"our Gurt"** (Picovoice; say "our Gurt" not "Gerty"), speech-to-text (faster-whisper, Vosk, or Groq), text-to-speech (Piper). Single-click mic with auto stop. Say **"bye"**, **"thanks"**, **"stop"** to end the conversation; say the wake word during auto-listen to stop listening.
- **Mobile control**: Telegram bot for commands from your phone
- **Model router**: Uses Ollama for local inference, OpenRouter for complex tasks
- **Toolkit**: Time, date, alarms, timers, calculator, units, notes, stopwatch, timezone, random, weather, web search, **deep research** (OpenRouter), pomodoro, system commands, media/audio, app launching, system monitoring, **screen vision**, **OpenClaw** (action execution: files, browser, calendar, email when enabled)
- **RAG Knowledge Base**: Drop PDF, Excel, Word, or text files into `data/knowledge/`; enable in Settings, then say "check my docs for X" to search. Long-term memory extracts facts from chat (Settings toggle). On-demand only (no automatic injection) for fast chat. See [docs/RAG_MEMORY.md](docs/RAG_MEMORY.md).
- **Web search** (optional): `pip install duckduckgo-search`. Routes by intent: "search for X", "get me contact details for Y", "when is showtimes of Z", etc. OpenRouter uses quick search for simple lookups.
- **Deep research** (OpenRouter): Multi-step web research, comparisons, spreadsheets. Requires OpenRouter in Settings. When OpenClaw is enabled, everything except fast-path (time, alarm, etc.) goes to OpenClaw; when the daemon is down, Gerty falls back to Ollama/OpenRouter chat. See COMMANDS.md.
- **Interactive browsing** (OpenRouter, opt-in): Navigate, click, fill forms. Requires Python 3.11+, `GERTY_BROWSE_ENABLED=1`, and `pip install browser-use playwright` + `python -m playwright install chromium`. See COMMANDS.md.

## Setup

### System dependencies (Linux/Pop!_OS)

For the desktop UI, pywebview uses Qt6. Install XCB platform plugin:

```bash
sudo apt install libxcb-cursor0 libxcb-xinerama0
```

For system tools (media, app launch): `playerctl` (media control), `wpctl` (PipeWire, usually preinstalled) or `pamixer` (PulseAudio), and `gtk-launch` (libgtk-3-0):

```bash
sudo apt install playerctl libgtk-3-0
```

### Python setup

```bash
cd gerty
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 1. Build frontend

```bash
cd frontend && npm install && npm run build && cd ..
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your keys (optional):
# - OPENROUTER_API_KEY for cloud LLM
# - TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS for mobile
# - PICOVOICE_ACCESS_KEY for wake word (free at console.picovoice.ai)
# - GERTY_SYSTEM_TOOLS=1 for system commands and app launching (lock, suspend, open apps)
# - GERTY_BROWSE_ENABLED=1 for interactive browsing (requires Python 3.11+, browser-use, playwright)
# - GERTY_OPENCLAW_ENABLED=1 for OpenClaw (files, browser, calendar, email; see docs/OPENCLAW_INTEGRATION.md). Note: OpenClaw may return invented responses; see docs/OPENCLAW_DIAGNOSIS.md.
```

### 3. Start Ollama (for local LLM)

```bash
ollama serve
ollama pull llama3.2
ollama pull llama3.1:8b
```

**Model recommendations (CPU-only, 32GB RAM):** For voice latency and fewer hallucinations:

```
OLLAMA_CHAT_MODEL=llama3.1:8b    # Good balance, fewer hallucinations
OLLAMA_VOICE_MODEL=llama3.2      # Fast 3B model for low-latency voice
OLLAMA_TEMPERATURE=0.1           # Factual responses (reduces hallucinations)
```

For complex tasks: `OLLAMA_REASONING_MODEL=deepseek-r1:7b`. Check `ollama list` for available models.

**Screen vision (optional):** For "what am I looking at?" and screen analysis:

```bash
ollama pull moondream
```

Set `OLLAMA_VISION_MODEL=moondream` in `.env` (default). For better quality: `ollama pull qwen2.5vl:7b` and `OLLAMA_VISION_MODEL=qwen2.5vl:7b`. Hotkey: `Ctrl+Shift+S`.

### 4. RAG Knowledge Base (optional)

To use the knowledge base, pull the embedding and RAG chat models:

```bash
ollama pull nomic-embed-text
ollama pull command-r7b
```

Drop PDF, Excel, Word, or text files into `data/knowledge/`, then open Settings → Knowledge base → "Index now". Test from terminal: `python3 -m gerty.rag`.

### 5. Download voice models (optional, for STT/TTS)

```bash
./scripts/download_models.sh
```

Voice is **fully local** by default – no API keys required:
- **Single-click mic**: Click once to speak; auto-stops when you finish (or click again to stop early). Uses Silero VAD for end-of-speech detection.
- **STT (speech-to-text)**: faster-whisper (default), **Moonshine** (variable-length, ~5x faster on short commands), Vosk (legacy), Groq (cloud, 216x real-time), or Auto. Moonshine: `pip install "transformers[torch]"`, then Settings → Voice – Speech recognition → Moonshine. For CPU: use `tiny` or Groq.
- **Vosk fallback**: If faster-whisper hangs (e.g. under PyWebView), voice automatically falls back to Vosk.
- **TTS (text-to-speech)**: Piper (fast) or Kokoro-82M (ElevenLabs-like) – Settings → Voice – Text-to-speech. Choose a voice and click **Save** to set it as default.
- **Wake word** (optional): Say **"our Gurt"** (not "Gerty") to activate – Picovoice custom model. Set `PICOVOICE_ACCESS_KEY` in `.env` (free at console.picovoice.ai). During auto-listen (after a response), say the wake word again to stop listening.
- **Settings → Voice – Speech recognition (STT)**: Choose STT backend and faster-whisper model (tiny, base, small, medium, large-v3). Restart app after changing.
- **Voice + OpenRouter + Groq**: Select **OpenRouter** in the chat header (Local/OpenRouter toggle) for voice to use cloud LLM. For Groq STT: Settings → Voice → Speech recognition → **Groq** or **Auto** (Auto uses Groq when `GROQ_API_KEY` and network available). Add both keys to `.env`. Restart after changing STT.

**TTS note:** Piper is fast and CPU-friendly. **Kokoro-82M** (~80MB) offers ElevenLabs-like quality on CPU—set `TTS_BACKEND=kokoro` in `.env` or choose in Settings. If using the desktop launcher, Kokoro runs from the project venv: ensure `kokoro-onnx` is installed there (`pip install -r requirements.txt` or `./.venv/bin/pip install kokoro-onnx`). For voice cloning, consider [Coqui XTTS](https://github.com/coqui-ai/TTS) or [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) (GPU recommended).

### 6. Install desktop launcher (Pop!_OS / Ubuntu)

```bash
./scripts/install_desktop.sh
```

This installs a `.desktop` file so you can:
- **Launch** Gerty from the app launcher (Super key → search "Gerty")
- **Pin to dock** – Launch Gerty, then right-click its dock icon → "Pin to dock"
- **Close cleanly** – Clicking the window X button fully exits the app (no lingering process)
- **OpenClaw auto-start** – When `GERTY_OPENCLAW_ENABLED=1`, the OpenClaw daemon starts automatically in the background when you launch Gerty from the app launcher

### 7. Telegram (optional – mobile control)

Control Gerty from your phone. All messages go through Gerty (fast-path tools + OpenClaw when enabled). See [docs/TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md) for full instructions.

1. Create a bot via [@BotFather](https://t.me/BotFather) (`/newbot`), copy the token
2. Get your chat ID (e.g. message [@userinfobot](https://t.me/userinfobot))
3. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_CHAT_IDS=your_chat_id
   ```
4. Restart Gerty, then message your bot (e.g. "what time is it", "list my skills")

### 8. OpenClaw (optional – action execution)

When enabled, Gerty uses **Option A** routing: everything except fast-path (time, alarm, timer, etc.) goes to OpenClaw. Gerty passes full chat history and your custom prompt. When the daemon is down, Gerty falls back to Ollama/OpenRouter chat. See [docs/OPENCLAW_INTEGRATION.md](docs/OPENCLAW_INTEGRATION.md).

```bash
# Install OpenClaw (Node.js 22+)
npm install -g openclaw@latest

# Set in Gerty's .env
GERTY_OPENCLAW_ENABLED=1
```

**OpenClaw config:** OpenClaw uses its own config and keys in `~/.openclaw/`. Create `~/.openclaw/.env` with a dedicated `OPENROUTER_API_KEY` (separate from Gerty). Add `BRAVE_API_KEY` or `PERPLEXITY_API_KEY` for web search. Run `openclaw onboard` or `openclaw configure --section web` to set up. To use Grok 4.1 fast, set `agents.defaults.model.primary` to `openrouter/x-ai/grok-4.1-fast` in `~/.openclaw/openclaw.json`.

**Exec approvals (critical):** Gerty is headless—no one approves exec commands. **Recommended:** Set `security: "full"` and `ask: "off"` in `~/.openclaw/exec-approvals.json` and `~/.openclaw/openclaw.json`, then install **dcg-guard** (`clawhub install dcg-guard`, `bash install.sh` in skill dir) to block destructive commands. Alternative: use allowlist mode. See [docs/OPENCLAW_INTEGRATION.md](docs/OPENCLAW_INTEGRATION.md).

**gog (Google Workspace):** For Gmail/Calendar/Drive/Sheets/Docs via the gog skill, run `./scripts/install_gog.sh` on Linux, then `gog auth credentials <path>` and `gog auth add <email> --services ...`. See [docs/GOOGLE_OAUTH_SETUP.md](docs/GOOGLE_OAUTH_SETUP.md).

When using the desktop launcher, the daemon starts automatically. Otherwise run `openclaw daemon start` before using Gerty. If gateway shows unreachable despite systemd "running", try `systemctl --user restart openclaw-gateway`.

### 9. Proactive agent (optional – background checks)

The **proactive-agent** skill (ClawHub) runs periodic heartbeats: web search, calendar/email checks, and logs findings. Uses system cron (OpenClaw's built-in cron has issues with isolated sessions + tools). **Not the same as Gerty's built-in heartbeat** (`python -m gerty --heartbeat` — health rotation checks). See [docs/GERTY_OVERVIEW.md](docs/GERTY_OVERVIEW.md) § Heartbeat vs Proactive-Agent.

```bash
# Add crontab (every 4 hours)
./scripts/setup-proactive-cron.sh
# Or manually: crontab -e, add:
# 0 */4 * * * /home/you/gerty/scripts/proactive-heartbeat.sh
```

**Prerequisites:** Complete onboarding (USER.md, SOUL.md). Gateway running when cron fires. Test: `./scripts/proactive-heartbeat.sh`. Findings: `notes/areas/proactive-updates.md`; log: `tail logs/proactive.log`.

## Usage

```bash
python -m gerty
```

Or launch from your application launcher after running `./scripts/install_desktop.sh`.

**CLI modes:**
- `python -m gerty --heartbeat` — Health rotation (diagnostics, friction, incidents); writes to `data/maintenance/heartbeat/` when noteworthy. See [docs/HEARTBEAT_AND_CRON.md](docs/HEARTBEAT_AND_CRON.md).
- `python -m gerty --validate` — Run do-not-break checks (pytest, etc.).
- `python -m gerty --diagnose` — One-off diagnostics (Ollama, OpenClaw, OpenRouter, paths).

**See [COMMANDS.md](COMMANDS.md) for the full commands reference** – all tools with example phrases for chat, voice, and Telegram. **See [docs/OPENCLAW_INTEGRATION.md](docs/OPENCLAW_INTEGRATION.md)** for OpenClaw setup.

**See [PERFORMANCE.md](PERFORMANCE.md)** – Benchmarks and tips (e.g. Qwen &lt;1s vs Gemma ~6s first response; RAG toggle for speed).

### Reverting to a past working version

To restore a known-good state (e.g. after a bad update):

```bash
git reset --hard baseline-working
cd frontend && npm run build && cd ..
```

**You must rebuild the frontend.** The `frontend/dist/` folder is not in git. Reverting restores source files only; the app serves built JS from `dist/`. Without `npm run build`, you may still run old or broken code even after reverting.

## Project structure

```
gerty/
├── PERFORMANCE.md       # Benchmarks, first-response times, tips
├── docs/                # ALARM.md, RAG_MEMORY.md, SECURITY_POLICY.md; archive/ for old docs
├── gerty/
│   ├── main.py          # Entry point
│   ├── config.py        # Environment config
│   ├── heartbeat.py     # Health rotation (--heartbeat)
│   ├── security.py      # Trusted tools, forbidden patterns, OpenClaw screening
│   ├── maintenance.py   # Incidents, proposals, tasks
│   ├── observability.py # Friction log, health log
│   ├── self_improvement.py  # validate(), format_validation_report (--validate)
│   ├── llm/             # Ollama, OpenRouter, router
│   ├── rag/             # RAG knowledge base (ChromaDB, parsers, embedder)
│   ├── voice/           # Wake word, STT, TTS
│   ├── openclaw/        # OpenClaw client (action execution when enabled)
│   ├── research/        # Deep research: OpenRouter :online, table parsing, CSV output
│   ├── tools/           # Time, alarms, timers, calculator, units, notes, weather, search, browse, pomodoro, system, media, app_launch, sys_monitor, screen_vision, maintenance
│   ├── telegram/        # Telegram bot
│   └── ui/              # FastAPI server, PyWebView
├── data/
│   ├── knowledge/       # Drop files here for RAG indexing
│   ├── rag/             # ChromaDB + index metadata
│   └── maintenance/     # Incidents, heartbeat artifacts
├── frontend/            # React SPA
├── models/              # Vosk, Piper models
└── scripts/             # Install helpers, launch_gerty.sh (desktop launcher wrapper)
```

## Development / Git

Use SSH for push/pull so you don't need to enter tokens. Cursor and OpenClaw (when exec runs with your SSH agent) can push without prompts.

1. **Create the repo** (if needed): [github.com/new](https://github.com/new) → name it `gerty` → **don't** add README/license (you're pushing existing code)
2. **Add your SSH key to GitHub**: [Settings → SSH and GPG keys](https://github.com/settings/keys) → New SSH key → paste `cat ~/.ssh/id_ed25519.pub`
3. **Set remote**: `git remote set-url origin git@github.com:YOUR_USERNAME/gerty.git`
4. **Push**: `git push -u origin master`

**Stable branch:** `stable` is a known-good checkpoint. Work on `master`; when happy with a milestone, update stable: `git checkout stable && git merge master && git push && git checkout master`. To revert: `git reset --hard stable`.
