"""Ollama API client for local LLM."""

import json

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

        with httpx.Client(timeout=180.0) as client:
            response = client.post(
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            if response.status_code == 404:
                return (
                    f"Model '{model}' not found. Run: ollama pull {model}\n"
                    "Or check available models: ollama list"
                )
            if response.status_code == 500:
                try:
                    err = response.json()
                    detail = err.get("error", str(err))
                except Exception:
                    detail = response.text[:200] if response.text else "Unknown"
                return (
                    f"Ollama server error (500) with model '{model}'. "
                    "Try: ollama run gemma3:12b (in terminal) to test. "
                    "If OOM, try a smaller model: ollama pull llama3.2\n"
                    f"Details: {detail}"
                )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")

    def chat_stream(self, message: str, history: list[dict] | None = None, model: str | None = None):
        """Stream chat response. Yields content chunks."""
        messages = list(history or [])
        messages.append({"role": "user", "content": message})
        model = model or self.model

        with httpx.Client(timeout=180.0) as client:
            with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": True},
            ) as response:
                if response.status_code == 404:
                    yield f"Model '{model}' not found. Run: ollama pull {model}"
                    return
                if response.status_code == 500:
                    yield f"Ollama server error (500). Try: ollama run {model}"
                    return
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        chunk = data.get("message", {}).get("content", "")
                        if chunk:
                            yield chunk
                    except json.JSONDecodeError:
                        continue

    def is_available(self) -> bool:
        """Check if Ollama is running and reachable."""
        try:
            with httpx.Client(timeout=2.0) as client:
                r = client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False
