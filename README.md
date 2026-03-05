# Gerty

Local AI/LLM voice assistant (Jarvis/Alexa-style). Fully private, runs on your machine.

## Features

- **Chat UI**: Modern dark-themed desktop app with chat window and extensible sidebar
- **Voice** (optional): Wake word ("computer"), speech-to-text (faster-whisper, Vosk, or Groq), text-to-speech (Piper). Single-click mic with auto stop.
- **Mobile control**: Telegram bot for commands from your phone
- **Model router**: Uses Ollama for local inference, OpenRouter for complex tasks
- **Toolkit**: Time, date, alarms, timers, calculator, units, notes, stopwatch, timezone, random, weather, web search, pomodoro
- **RAG Knowledge Base**: Drop PDF, Excel, Word, or text files into `data/knowledge/`; index and query your documents in chat (toggle on/off in Settings for faster chat)
- **Web search** (optional): `pip install duckduckgo-search` for the search tool

## Setup

### System dependencies (Linux/Pop!_OS)

For the desktop UI, pywebview uses Qt6. Install XCB platform plugin:

```bash
sudo apt install libxcb-cursor0 libxcb-xinerama0
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
```

### 3. Start Ollama (for local LLM)

```bash
ollama serve
ollama pull llama3.2
ollama pull llama3.1:8b
```

**Model recommendations (AMD Ryzen 9 / 27GB RAM):** For best results on high-end APUs, use a multi-model setup. Add to `.env`:

```
OLLAMA_CHAT_MODEL=llama3.1:8b     # Good balance of speed and quality
OLLAMA_REASONING_MODEL=deepseek-r1:7b  # Specialist: coding, math
```

Or: `ollama pull gemma3:12b` and `ollama pull deepseek-r1:7b`. Check `ollama list` for available model names.

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
- **STT (speech-to-text)**: faster-whisper (default), Vosk (legacy), Groq (cloud, 216x real-time), or Auto (Groq when WiFi, else local). Settings → Voice – Speech recognition.
- **Vosk fallback**: If faster-whisper hangs (e.g. under PyWebView), voice automatically falls back to Vosk.
- **TTS (text-to-speech)**: Piper voices – Settings → Voice – Text-to-speech
- **Wake word** (optional): Install `pip install openwakeword` for "hey jarvis", or set `PICOVOICE_ACCESS_KEY` for "computer"
- **Settings → Voice – Speech recognition (STT)**: Choose STT backend and faster-whisper model (tiny, base, small, medium, large-v3). Restart app after changing.

**TTS note:** Piper is fast and CPU-friendly. For more human-like quality (voice cloning, higher naturalness), consider [Coqui XTTS](https://github.com/coqui-ai/TTS) or [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS) – they require more resources (GPU recommended).

### 6. Install desktop launcher (Pop!_OS / Ubuntu)

```bash
./scripts/install_desktop.sh
```

This installs a `.desktop` file so you can:
- **Launch** Gerty from the app launcher (Super key → search "Gerty")
- **Pin to dock** – Launch Gerty, then right-click its dock icon → "Pin to dock"

## Usage

```bash
python -m gerty
```

Or launch from your application launcher after running `./scripts/install_desktop.sh`.

**See [COMMANDS.md](COMMANDS.md) for the full commands reference** – all tools with example phrases for chat, voice, and Telegram.

**See [PERFORMANCE.md](PERFORMANCE.md)** – Benchmarks and tips (e.g. Qwen &lt;1s vs Gemma ~6s first response; RAG toggle for speed).

## Project structure

```
gerty/
├── PERFORMANCE.md       # Benchmarks, first-response times, tips
├── gerty/
│   ├── main.py          # Entry point
│   ├── config.py        # Environment config
│   ├── llm/             # Ollama, OpenRouter, router
│   ├── rag/              # RAG knowledge base (ChromaDB, parsers, embedder)
│   ├── voice/           # Wake word, STT, TTS
│   ├── tools/           # Time, alarms, timers, calculator, units, notes, weather, search, pomodoro
│   ├── telegram/        # Telegram bot
│   └── ui/              # FastAPI server, PyWebView
├── data/
│   ├── knowledge/       # Drop files here for RAG indexing
│   └── rag/             # ChromaDB + index metadata
├── frontend/            # React SPA
├── models/              # Vosk, Piper models
└── scripts/             # Install helpers
```
