"""FastAPI server for Gerty UI."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse

from gerty.config import KNOWLEDGE_DIR, OLLAMA_BASE_URL, OLLAMA_CHAT_MODEL, OPENROUTER_API_KEY, RAG_DIR
from gerty.rag import (
    get_status as rag_get_status,
    index_folder as rag_index_folder,
    is_indexed as rag_is_indexed,
    query as rag_query,
)
from gerty.settings import load as load_settings, save as save_settings
from gerty.tools.alarms import get_pending_alarms, cancel_all_alarms
from gerty.tools.timers import get_active_timers, cancel_all_timers

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


DEFAULT_SYSTEM_PROMPT = "Format replies in Markdown: use **bold**, headings (##), bullet lists, numbered lists, and code blocks (```language) when helpful. Use emojis sparingly for clarity."


def _summarize_history(ollama, history: list, model: str) -> str:
    """Use local LLM to summarize conversation history."""
    if not history:
        return ""
    text = "\n".join(f"{m.get('role', '')}: {m.get('content', '')}" for m in history)
    prompt = (
        "Summarize this conversation concisely. Keep key facts, decisions, and context the assistant should remember. "
        "Output only the summary, no preamble.\n\n" + text
    )
    try:
        return ollama.chat(prompt, history=[], model=model, system_prompt="Be concise.")
    except Exception:
        return ""


def create_app(router):
    """Create FastAPI app with chat endpoint. router is Router instance."""
    route = router.route
    route_stream = router.route_stream

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        RAG_DIR.mkdir(parents=True, exist_ok=True)
        yield
        # Cleanup if needed

    app = FastAPI(title="Gerty", lifespan=lifespan)

    @app.post("/api/chat")
    async def chat(body: dict = Body(default_factory=dict)):
        message = body.get("message", "")
        if not message:
            return {"reply": "", "error": "Empty message"}
        try:
            reply = route(message)
            return {"reply": reply}
        except Exception as e:
            return {"reply": "", "error": str(e)}

    @app.get("/api/settings")
    async def get_settings():
        return load_settings()

    @app.post("/api/settings")
    async def post_settings(body: dict = Body(default_factory=dict)):
        return save_settings(body)

    @app.get("/api/ollama/models")
    async def ollama_models():
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{OLLAMA_BASE_URL}/api/tags")
                if r.status_code != 200:
                    return {"models": []}
                data = r.json()
                return {"models": [m.get("name", m.get("model", "")) for m in data.get("models", [])]}
        except Exception:
            return {"models": []}

    @app.get("/api/openrouter/models")
    async def openrouter_models():
        if not OPENROUTER_API_KEY:
            return {"models": []}
        try:
            with httpx.Client(timeout=15.0) as client:
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
        except Exception:
            return {"models": []}

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
                    effective_history = history
                    effective_prompt = custom_prompt
                    rag_model_override = None
                    rag_embed_model = settings.get("rag_embed_model", "nomic-embed-text")
                    rag_chat_model = settings.get("rag_chat_model", "command-r7b")

                    if rag_is_indexed():
                        chunks = rag_query(message, top_k=5, embed_model=rag_embed_model)
                        if chunks:
                            context = "\n\n".join(c[0] for c in chunks)
                            effective_prompt = (
                                custom_prompt
                                + "\n\nRelevant context from your documents:\n---\n"
                                + context
                                + "\n---\nUse this context to answer the user's question."
                            )
                            if rag_chat_model and rag_chat_model != "__use_chat__":
                                rag_model_override = rag_chat_model

                    if len(history) >= 10 and router.ollama.is_available():
                        summary = _summarize_history(router.ollama, history, local_model or OLLAMA_CHAT_MODEL)
                        if summary:
                            effective_prompt = effective_prompt + "\n\nConversation summary:\n" + summary
                            effective_history = []

                    for chunk in route_stream(
                        message,
                        effective_history,
                        provider="local" if rag_model_override else provider,
                        local_model=rag_model_override or local_model,
                        openrouter_model=openrouter_model,
                        custom_prompt=effective_prompt,
                        rag_model=rag_model_override,
                    ):
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
                except Exception as e:
                    loop.call_soon_threadsafe(queue.put_nowait, f"Error: {e}")
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
            return StreamingResponse(
                iter([f"Error: {e}"]),
                media_type="text/plain; charset=utf-8",
            )

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
            return {"indexed": False, "error": str(e)}

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
                file_path = FRONTEND_DIST / path
                if file_path.exists() and file_path.is_file():
                    return FileResponse(file_path)
            return FileResponse(FRONTEND_DIST / "index.html")

    return app
