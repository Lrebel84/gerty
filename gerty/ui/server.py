"""FastAPI server for Gerty UI."""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


def create_app(router_callback):
    """Create FastAPI app with chat endpoint."""

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
            reply = router_callback(message)
            return {"reply": reply}
        except Exception as e:
            return {"reply": "", "error": str(e)}

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

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
