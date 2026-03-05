# Performance Notes

Benchmarks on Pop!_OS (AMD Ryzen 9 / 27GB RAM). First chat message, single turn.

## Local models (no RAG)

| Model | First response time |
|-------|---------------------|
| Qwen  | &lt;1 sec (instant) |
| Gemma | ~6 sec              |

## With RAG enabled

First chat with RAG context: no measurable change vs no-RAG. RAG embedding adds some latency before streaming begins; impact varies by hardware and embed model.

## Voice (STT/TTS)

Recommended for AMD Ryzen 9:

- **STT**: faster-whisper `base` or `small` (Settings → Voice – Speech recognition). `tiny` is fastest; `base` balances speed and accuracy. Falls back to Vosk if faster-whisper hangs.
- **Groq** (cloud): Set `STT_BACKEND=groq` or `auto` and `GROQ_API_KEY` for 216x real-time transcription.
- **OLLAMA_VOICE_MODEL**: Optional faster model for voice (e.g. `qwen2.5:3b`) in `.env`.
- **Debug**: `GERTY_LOG_LEVEL=INFO` logs STT/LLM/TTS timing to `gerty.log`.

## Tips for faster responses

- **RAG off**: Settings → Knowledge base → uncheck "Enable RAG" for quick chat without document retrieval.
- **Smaller models**: Qwen (e.g. qwen2.5:7b) tends to be faster than Gemma for first-token latency.
- **History summarization**: Uses OpenRouter when available (WiFi); falls back to local. Long history summarization adds delay before the main reply.
