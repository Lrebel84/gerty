# Performance Notes

Benchmarks on Pop!_OS (AMD Ryzen 9 / 27GB RAM). First chat message, single turn.

## Local models

| Model | First response time |
|-------|---------------------|
| Llama 3.2 (3B) | &lt;1 sec (instant) – ideal for voice |
| Llama 3.1 8B | ~1–2 sec – good balance, fewer hallucinations |
| Gemma 12B | ~6 sec |

## RAG (on-demand)

RAG is now tool-only: say "check my docs for X" or "search my files for Y" to query. No automatic injection = no context-window bloat. Enable in Settings → Knowledge base, then use the tool when needed.

## Voice (STT/TTS)

For lowest latency on CPU:

- **STT**: Groq (cloud, 216x real-time) or faster-whisper `tiny` (fastest local). `base` balances speed and accuracy. Falls back to Vosk if faster-whisper hangs.
- **Groq**: Set `STT_BACKEND=groq` or `auto` and `GROQ_API_KEY`.
- **OLLAMA_VOICE_MODEL**: Set to `llama3.2` (3B) for fast voice replies.
- **Debug**: `GERTY_LOG_LEVEL=INFO` logs STT/LLM/TTS timing to `gerty.log`.

## Tips for faster responses

- **Voice path**: No RAG, no summarization, minimal history – optimized for low latency.
- **Temperature**: `OLLAMA_TEMPERATURE=0.1` for factual responses (reduces hallucinations).
- **History summarization**: Chat only (not voice). Long history adds delay before reply.
