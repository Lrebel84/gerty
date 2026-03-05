"""FastAPI server for Gerty UI."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse

from gerty.tools.alarms import get_pending_alarms, cancel_all_alarms
from gerty.tools.timers import get_active_timers, cancel_all_timers

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


def create_app(router):
    """Create FastAPI app with chat endpoint. router is Router instance."""
    route = router.route
    route_stream = router.route_stream

    @asynccontextmanager
    async def lifespan(app: FastAPI):
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

    @app.post("/api/chat/stream")
    async def chat_stream(body: dict = Body(default_factory=dict)):
        message = body.get("message", "")
        history = body.get("history", [])
        if not message:
            return {"error": "Empty message"}
        try:
            queue: asyncio.Queue[str | None] = asyncio.Queue()

            def produce():
                try:
                    for chunk in route_stream(message, history):
                        asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, chunk)
                except Exception as e:
                    asyncio.get_event_loop().call_soon_threadsafe(
                        queue.put_nowait, f"Error: {e}"
                    )
                asyncio.get_event_loop().call_soon_threadsafe(queue.put_nowait, None)

            async def stream():
                loop = asyncio.get_event_loop()
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
