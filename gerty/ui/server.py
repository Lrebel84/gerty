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
    GERTY_OPENCLAW_ENABLED,
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
from gerty.tools.alarms import get_pending_alarms, cancel_all_alarms, cancel_alarm, add_alarm, toggle_alarm_recurring
from gerty.tools.notes import get_notes, add_note, clear_notes, delete_note
from gerty.tools.skills_registry import get_skills
from gerty.voice.alarm_state import get_sounding_alarm, stop_alarm_sounding
from gerty.tools.timers import get_active_timers, cancel_all_timers, cancel_timer, add_timer
from gerty.voice.wake_word import request_ptt_recording, request_voice_cancel, stop_ptt_recording

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
        settings = load_settings()
        history = body.get("history", [])
        provider = body.get("provider", settings.get("provider", "local"))
        local_model = body.get("local_model", settings.get("local_model"))
        openrouter_model = body.get("openrouter_model", settings.get("openrouter_model"))
        custom_prompt = (body.get("custom_prompt") or settings.get("custom_prompt") or "").strip()
        if not custom_prompt:
            custom_prompt = DEFAULT_SYSTEM_PROMPT
        try:
            reply = "".join(
                chat_pipeline_stream(
                    router,
                    message,
                    history,
                    provider=provider,
                    local_model=local_model,
                    openrouter_model=openrouter_model,
                    custom_prompt=custom_prompt,
                )
            )
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

    @app.get("/api/skills")
    async def get_skills_api():
        """Return skills and tools with example commands. Update gerty/tools/skills_registry.py when adding tools."""
        return {"skills": get_skills()}

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
        """Clear persisted chat history (new chat). Also clears OpenClaw session when enabled."""
        try:
            if CHAT_HISTORY_FILE.exists():
                CHAT_HISTORY_FILE.unlink()
            if GERTY_OPENCLAW_ENABLED:
                from gerty.openclaw.client import clear_session
                clear_session()
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
        logger.info("Chat stream request: message=%r len=%d", message, len(message) if message else 0)
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
                yield "\u200b"  # Zero-width space: immediate byte so client gets response (avoids WebEngine timeout)
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
        logger.info("Voice: start received")
        request_ptt_recording()
        return {"ok": True}

    @app.post("/api/voice/stop")
    async def voice_stop():
        """Stop voice recording (HTTP fallback when pywebview bridge unavailable)."""
        logger.info("Voice: stop received")
        stop_ptt_recording()
        return {"ok": True}

    @app.post("/api/voice/cancel")
    async def voice_cancel():
        """Cancel current voice processing (STT/LLM/TTS). Unsticks 'Processing' state."""
        request_voice_cancel()
        return {"ok": True}

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/alarms")
    async def list_alarms():
        """Return alarms: future + currently sounding. Triggered alarm stays until user cancels."""
        sounding = get_sounding_alarm()
        sounding_id = (sounding.get("id") or sounding.get("datetime")) if sounding else None
        alarms = get_pending_alarms(include_sounding_id=sounding_id)
        return {"alarms": alarms, "sounding": sounding}

    @app.post("/api/alarms/dismiss")
    async def dismiss_alarm():
        """Stop the currently sounding alarm (manual stop from UI)."""
        stop_alarm_sounding()
        return {"ok": True}

    @app.post("/api/alarms")
    async def post_alarm(body: dict = Body(default_factory=dict)):
        """Add an alarm. Body: { time: string, label?: string, recurring?: 'daily' }."""
        time_str = body.get("time", "").strip()
        if not time_str:
            return {"added": False, "error": "time required"}
        label = (body.get("label") or "Alarm").strip()[:50] or "Alarm"
        recurring = "daily" if body.get("recurring") in (True, "daily", "true") else None
        try:
            alarm = add_alarm(time_str, label, recurring=recurring)
            return {"added": True, "alarm": alarm}
        except ValueError as e:
            return {"added": False, "error": str(e)}

    @app.post("/api/alarms/toggle-recurring")
    async def toggle_alarm_recurring_api(body: dict = Body(default_factory=dict)):
        """Toggle an alarm between daily and one-time. Body: { id: string }."""
        alarm_id = body.get("id")
        if not alarm_id:
            return {"ok": False, "error": "id required"}
        result = toggle_alarm_recurring(alarm_id)
        if result is None:
            return {"ok": False, "error": "alarm not found"}
        return {"ok": True, "recurring": result}

    @app.post("/api/alarms/cancel")
    async def cancel_alarms(body: dict = Body(default_factory=dict)):
        alarm_id = body.get("id")
        if alarm_id:
            ok = cancel_alarm(alarm_id)
            return {"cancelled": 1 if ok else 0}
        count = cancel_all_alarms()
        return {"cancelled": count}

    @app.get("/api/timers")
    async def list_timers():
        return {"timers": get_active_timers()}

    @app.post("/api/timers")
    async def post_timer(body: dict = Body(default_factory=dict)):
        """Add a timer. Body: { duration_sec: number, label?: string }."""
        duration_sec = body.get("duration_sec")
        if duration_sec is None:
            return {"added": False, "error": "duration_sec required"}
        try:
            duration_sec = int(duration_sec)
        except (TypeError, ValueError):
            return {"added": False, "error": "duration_sec must be a positive integer"}
        if duration_sec <= 0:
            return {"added": False, "error": "duration_sec must be positive"}
        label = (body.get("label") or "Timer").strip()[:50] or "Timer"
        try:
            result = add_timer(duration_sec, label)
            return {"added": True, **result}
        except ValueError as e:
            return {"added": False, "error": str(e)}

    @app.get("/api/notes")
    async def list_notes():
        return {"notes": get_notes()}

    @app.post("/api/notes")
    async def post_note(body: dict = Body(default_factory=dict)):
        text = body.get("text", "").strip()
        if not text:
            return {"added": False}
        add_note(text)
        return {"added": True}

    @app.delete("/api/notes/{index:int}")
    async def delete_note_at(index: int):
        ok = delete_note(index)
        return {"deleted": 1 if ok else 0}

    @app.delete("/api/notes")
    async def delete_all_notes():
        count = clear_notes()
        return {"cleared": count}

    @app.post("/api/timers/cancel")
    async def cancel_timers(body: dict = Body(default_factory=dict)):
        """Cancel timers. Body: { id?: string } - if id present, cancel that timer; else cancel all."""
        timer_id = body.get("id")
        if timer_id:
            ok = cancel_timer(timer_id)
            return {"cancelled": 1 if ok else 0}
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
