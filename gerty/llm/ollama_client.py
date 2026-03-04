"""Ollama API client for local LLM."""

import httpx

from gerty.config import OLLAMA_BASE_URL, OLLAMA_MODEL


class OllamaClient:
    """Client for Ollama chat API."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = OLLAMA_MODEL,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, message: str, history: list[dict] | None = None, model: str | None = None) -> str:
        """Send a message and get a response. Optional model override."""
        messages = list(history or [])
        messages.append({"role": "user", "content": message})
        model = model or self.model

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")

    def is_available(self) -> bool:
        """Check if Ollama is running and reachable."""
        try:
            with httpx.Client(timeout=2.0) as client:
                r = client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False
