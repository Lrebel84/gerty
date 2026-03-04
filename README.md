# Gerty

Local AI/LLM voice assistant (Jarvis/Alexa-style). Fully private, runs on your machine.

## Features

- **Chat UI**: Modern dark-themed desktop app with chat window and extensible sidebar
- **Voice** (optional): Wake word ("computer"), speech-to-text (Vosk), text-to-speech (Piper)
- **Mobile control**: Telegram bot for commands from your phone
- **Model router**: Uses Ollama for local inference, OpenRouter for complex tasks
- **Toolkit**: Time, date, alarms, timers

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
```

**Model recommendations (AMD Ryzen 9 / 27GB RAM):** For best results on high-end APUs, use a multi-model setup. Add to `.env`:

```
OLLAMA_CHAT_MODEL=gemma3:12b      # Brain: best personality
OLLAMA_REASONING_MODEL=deepseek-r1:7b  # Specialist: coding, math
```

Pull the models: `ollama pull gemma3:12b` and `ollama pull deepseek-r1:7b`. Check `ollama list` for available model names.

### 4. Download voice models (optional, for STT/TTS)

```bash
./scripts/download_models.sh
```

### 5. Install desktop launcher (Pop!_OS)

```bash
./scripts/install_desktop.sh
```

## Usage

```bash
python -m gerty.main
```

Or launch from your application menu after installing the desktop file.

## Project structure

```
gerty/
├── gerty/
│   ├── main.py          # Entry point
│   ├── config.py        # Environment config
│   ├── llm/             # Ollama, OpenRouter, router
│   ├── voice/           # Wake word, STT, TTS
│   ├── tools/           # Time, alarms, timers
│   ├── telegram/        # Telegram bot
│   └── ui/              # FastAPI server, PyWebView
├── frontend/            # React SPA
├── models/              # Vosk, Piper models
└── scripts/             # Install helpers
```
