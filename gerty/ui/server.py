"""FastAPI server for Gerty UI."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response, StreamingResponse

from gerty.config import (
    CHAT_HISTORY_FILE,
    HTTP_TIMEOUT_OLLAMA,
    HTTP_TIMEOUT_OPENROUTER,
    KNOWLEDGE_DIR,
    OLLAMA_BASE_URL,
    OLLAMA_CHAT_MODEL,
    OPENROUTER_API_KEY,
    PROJECT_ROOT,
    RAG_DIR,
)
from gerty.voice.tts import KOKORO_VOICES, TextToSpeech
from gerty.pipeline import DEFAULT_SYSTEM_PROMPT, chat_pipeline_stream
from gerty.rag import (
    add_memory_facts as rag_add_memory_facts,
    get_status as rag_get_status,
    index_folder as rag_index_folder,
    is_indexed as rag_is_indexed,
    query as rag_query,
)
from gerty.settings import load as load_settings, save as save_settings
from gerty.tools.alarms import get_pending_alarms, cancel_all_alarms
from gerty.tools.timers import get_active_timers, cancel_all_timers
from gerty.voice.wake_word import request_ptt_recording, stop_ptt_recording

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"

logger = logging.getLogger(__name__)

# Generic user-facing error message (avoid leaking internal details)
CHAT_ERROR_MSG = "Something went wrong. Please try again."


def _extract_user_facts(ollama, user_messages: list[str], model: str) -> list[str]:
    """Extract facts the user stated about themselves. Returns list of fact strings."""
    if not user_messages:
        return []
    text = "\n\n".join(user_messages)
    prompt = (
        "Extract ONLY facts the user has stated as true about themselves "
        "(family, friends, likes, dislikes, hopes, work, preferences, etc.). "
        "Do NOT include: questions the user asked, requests for information, "
        "things the user is asking about, hypotheticals, or anything the user did not assert as fact. "
        "Output as a JSON array of strings, one fact per item. "
        'Example: ["User\'s name is Liam", "User is a tattoo artist", "User\'s wife is Jen"]. '
        "If none, output []."
    )
    full_prompt = f"{prompt}\n\nUser messages:\n{text}"
    try:
        out = ollama.chat(full_prompt, history=[], model=model, system_prompt="Output only valid JSON.")
        import json
        import re
        # Handle markdown code blocks if present
        raw = out.strip()
        if "```" in raw:
            m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
            if m:
                raw = m.group(1).strip()
        arr = json.loads(raw)
        if isinstance(arr, list):
            return [str(x).strip() for x in arr if x and str(x).strip()]
    except Exception as e:
        logger.debug("Fact extraction failed: %s", e)
    return []


def create_app(router):
    """Create FastAPI app with chat endpoint. router is Router instance."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        RAG_DIR.mkdir(parents=True, exist_ok=True)

        # Warmup: preload embed + chat models when RAG is indexed (avoids 5–15s delay on first message)
        if rag_is_indexed() and router.ollama.is_available():
            def _warmup_sync():
                try:
                    settings = load_settings()
                    embed_model = settings.get("rag_embed_model", "nomic-embed-text")
                    chat_model = settings.get("local_model") or OLLAMA_CHAT_MODEL
                    from gerty.rag.embedder import embed
                    embed(["warmup"], model=embed_model)
                    router.ollama.chat("hi", history=[], model=chat_model)
                except Exception as e:
                    logger.debug("RAG warmup failed: %s", e)

            async def _warmup():
                await asyncio.sleep(2)
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, _warmup_sync)

            asyncio.create_task(_warmup())

        yield
        # Cleanup if needed

    app = FastAPI(title="Gerty", lifespan=lifespan)

    @app.post("/api/chat")
    async def chat(body: dict = Body(default_factory=dict)):
        message = body.get("message", "")
        if not message:
            return {"reply": "", "error": "Empty message"}
        try:
            reply = "".join(chat_pipeline_stream(router, message))
            return {"reply": reply}
        except Exception as e:
            logger.exception("Chat error")
            return {"reply": "", "error": CHAT_ERROR_MSG}

    @app.get("/api/settings")
    async def get_settings():
        return load_settings()

    @app.post("/api/settings")
    async def post_settings(body: dict = Body(default_factory=dict)):
        return save_settings(body)

    def _pcm_to_wav(pcm: bytes, sample_rate: int) -> bytes:
        """Wrap 16-bit mono PCM in WAV header."""
        import struct
        n = len(pcm)
        return (
            b"RIFF"
            + struct.pack("<I", 36 + n)
            + b"WAVE"
            + b"fmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
            + b"data"
            + struct.pack("<I", n)
            + pcm
        )

    @app.get("/api/voice/list")
    async def voice_list():
        """Return available TTS voices for Piper and Kokoro."""
        piper_voices = []
        piper_dir = PROJECT_ROOT / "models" / "piper"
        if piper_dir.exists():
            for p in piper_dir.rglob("*.onnx"):
                if p.is_file():
                    name = p.stem
                    if name not in piper_voices:
                        piper_voices.append(name)
        piper_voices.sort()
        return {"piper_voices": piper_voices, "kokoro_voices": KOKORO_VOICES}

    def _generate_voice_sample(tts_backend: str, voice: str) -> tuple[bytes, int] | str:
        """Generate TTS sample. Returns (pcm_bytes, sample_rate) or error string."""
        try:
            tts = TextToSpeech(backend=tts_backend, voice=voice)
            pcm = tts.synthesize("Hello, this is a sample of my voice.")
            return (pcm, tts.get_sample_rate())
        except Exception as e:
            logger.exception("Voice sample failed: %s", e)
            return str(e)

    @app.post("/api/voice/sample")
    async def voice_sample(body: dict = Body(default_factory=dict)):
        """Generate TTS sample. Returns WAV audio."""
        tts_backend = body.get("tts_backend", "piper")
        voice = body.get("voice", "")
        if not voice:
            return {"error": "No voice specified"}
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _generate_voice_sample(tts_backend, voice),
        )
        if isinstance(result, str):
            return Response(
                content=json.dumps({"error": result}).encode(),
                status_code=500,
                media_type="application/json",
            )
        pcm, sample_rate = result
        wav = _pcm_to_wav(pcm, sample_rate)
        return Response(content=wav, media_type="audio/wav")

    @app.get("/api/ollama/models")
    async def ollama_models():
        try:
            with httpx.Client(timeout=HTTP_TIMEOUT_OLLAMA) as client:
                r = client.get(f"{OLLAMA_BASE_URL}/api/tags")
                if r.status_code != 200:
                    return {"models": []}
                data = r.json()
                return {"models": [m.get("name", m.get("model", "")) for m in data.get("models", [])]}
        except Exception as e:
            logger.debug("Ollama models fetch failed: %s", e)
            return {"models": []}

    @app.get("/api/openrouter/models")
    async def openrouter_models():
        if not OPENROUTER_API_KEY:
            return {"models": []}
        try:
            with httpx.Client(timeout=HTTP_TIMEOUT_OPENROUTER) as client:
                r = client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                )
                if r.status_code != 200:
                    return {"models": []}
                data = r.json()
                ids = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                ids.sort(key=str.lower)
                return {"models": ids}
        except Exception as e:
            logger.debug("OpenRouter models fetch failed: %s", e)
            return {"models": []}

    @app.get("/api/chat/history")
    async def get_chat_history():
        """Return persisted chat history for resume on startup."""
        if not CHAT_HISTORY_FILE.exists():
            return {"messages": []}
        try:
            import json

            with open(CHAT_HISTORY_FILE) as f:
                data = json.load(f)
            return {"messages": data.get("messages", [])}
        except (json.JSONDecodeError, OSError):
            return {"messages": []}

    @app.delete("/api/chat/history")
    async def delete_chat_history():
        """Clear persisted chat history (new chat)."""
        try:
            if CHAT_HISTORY_FILE.exists():
                CHAT_HISTORY_FILE.unlink()
            return {"cleared": True}
        except OSError:
            return {"cleared": False}

    @app.put("/api/chat/history")
    async def put_chat_history(body: dict = Body(default_factory=dict), skip_extract: bool = False):
        """Save chat history. Extract facts if 2+ user messages (unless skip_extract=True for quick save on close)."""
        messages = body.get("messages", [])
        if not isinstance(messages, list):
            return {"saved": False}
        # Normalise for storage: {id, role, content, timestamp}
        stored = []
        for m in messages:
            if isinstance(m, dict) and m.get("content"):
                stored.append({
                    "id": m.get("id", ""),
                    "role": m.get("role", "user"),
                    "content": str(m.get("content", "")),
                    "timestamp": m.get("timestamp"),
                })
        try:
            import hashlib
            import json

            CHAT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            user_msgs = [m["content"] for m in stored if m.get("role") == "user"]
            content_hash = hashlib.sha256("|".join(user_msgs).encode()).hexdigest() if user_msgs else ""
            last_extracted = None
            if CHAT_HISTORY_FILE.exists():
                try:
                    with open(CHAT_HISTORY_FILE) as f:
                        old = json.load(f)
                        last_extracted = old.get("last_extracted_hash")
                except (json.JSONDecodeError, OSError):
                    pass
            with open(CHAT_HISTORY_FILE, "w") as f:
                json.dump({"messages": stored, "last_extracted_hash": last_extracted}, f, indent=2)
        except OSError:
            return {"saved": False}
        # Extract facts when 2+ user messages, only if session changed since last extract (skip on close - too slow)
        settings = load_settings()
        if (
            not skip_extract
            and settings.get("memory_enabled", True)
            and router.ollama.is_available()
            and len(user_msgs) >= 2
            and content_hash != last_extracted
        ):
            facts = _extract_user_facts(
                router.ollama, user_msgs, settings.get("local_model") or OLLAMA_CHAT_MODEL
            )
            if facts:
                rag_add_memory_facts(
                    facts, embed_model=settings.get("rag_embed_model", "nomic-embed-text")
                )
                try:
                    with open(CHAT_HISTORY_FILE) as f:
                        d = json.load(f)
                    d["last_extracted_hash"] = content_hash
                    with open(CHAT_HISTORY_FILE, "w") as f:
                        json.dump(d, f, indent=2)
                except (json.JSONDecodeError, OSError):
                    pass
        return {"saved": True}

    @app.post("/api/chat/stream")
    async def chat_stream(body: dict = Body(default_factory=dict)):
        message = body.get("message", "")
        history = body.get("history", [])
        if not message:
            return {"error": "Empty message"}
        settings = load_settings()
        provider = body.get("provider", settings.get("provider", "local"))
        local_model = body.get("local_model", settings.get("local_model"))
        openrouter_model = body.get("openrouter_model", settings.get("openrouter_model"))
        custom_prompt = (body.get("custom_prompt") or settings.get("custom_prompt") or "").strip()
        if not custom_prompt:
            custom_prompt = DEFAULT_SYSTEM_PROMPT

        try:
            queue: asyncio.Queue[str | None] = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def produce():
                try:
                    for chunk in chat_pipeline_stream(
                        router,
                        message,
                        history,
                        provider=provider,
                        local_model=local_model,
                        openrouter_model=openrouter_model,
                        custom_prompt=custom_prompt,
                    ):
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
                except Exception as e:
                    logger.exception("Chat stream error")
                    loop.call_soon_threadsafe(queue.put_nowait, f"Error: {CHAT_ERROR_MSG}")
                loop.call_soon_threadsafe(queue.put_nowait, None)

            async def stream():
                loop.run_in_executor(None, produce)
                while True:
                    chunk = await queue.get()
                    if chunk is None:
                        break
                    yield chunk

            return StreamingResponse(
                stream(),
                media_type="text/plain; charset=utf-8",
            )
        except Exception as e:
            logger.exception("Chat stream setup error")
            return StreamingResponse(
                iter([f"Error: {CHAT_ERROR_MSG}"]),
                media_type="text/plain; charset=utf-8",
            )

    @app.post("/api/voice/start")
    async def voice_start():
        """Start voice recording (HTTP fallback when pywebview bridge unavailable)."""
        request_ptt_recording()
        return {"ok": True}

    @app.post("/api/voice/stop")
    async def voice_stop():
        """Stop voice recording (HTTP fallback when pywebview bridge unavailable)."""
        stop_ptt_recording()
        return {"ok": True}

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/alarms")
    async def list_alarms():
        return {"alarms": get_pending_alarms()}

    @app.post("/api/alarms/cancel")
    async def cancel_alarms():
        count = cancel_all_alarms()
        return {"cancelled": count}

    @app.get("/api/timers")
    async def list_timers():
        return {"timers": get_active_timers()}

    @app.post("/api/timers/cancel")
    async def cancel_timers():
        count = cancel_all_timers()
        return {"cancelled": count}

    @app.get("/api/rag/status")
    async def rag_status():
        return rag_get_status()

    @app.post("/api/rag/index")
    async def rag_index(body: dict = Body(default_factory=dict)):
        settings = load_settings()
        embed_model = body.get("embed_model") or settings.get("rag_embed_model", "nomic-embed-text")
        try:
            result = rag_index_folder(embed_model=embed_model)
            return result
        except Exception as e:
            logger.exception("RAG index error")
            return {"indexed": False, "error": CHAT_ERROR_MSG}

    @app.get("/api/rag/files")
    async def rag_files():
        if not KNOWLEDGE_DIR.exists():
            return {"files": []}
        exts = {".pdf", ".xlsx", ".xls", ".csv", ".docx", ".txt", ".md", ""}
        files = [p.name for p in KNOWLEDGE_DIR.iterdir() if p.is_file() and p.suffix.lower() in exts]
        return {"files": sorted(files)}

    # Serve static frontend
    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

        @app.get("/{path:path}")
        async def serve_spa(path: str):
            if path and not path.startswith("api"):
                resolved = (FRONTEND_DIST / path).resolve()
                if (
                    str(resolved).startswith(str(FRONTEND_DIST.resolve()))
                    and resolved.exists()
                    and resolved.is_file()
                ):
                    return FileResponse(resolved)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app
