"""Ollama embeddings for RAG."""

import logging

import httpx

from gerty.config import OLLAMA_BASE_URL

logger = logging.getLogger(__name__)
DEFAULT_EMBED_MODEL = "nomic-embed-text"


def check_embed_ready(model: str = DEFAULT_EMBED_MODEL, base_url: str = OLLAMA_BASE_URL) -> tuple[bool, str]:
    """Verify Ollama is reachable and the embed model exists. Returns (ok, error_message)."""
    base_url = base_url.rstrip("/")
    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(
                f"{base_url}/api/embed",
                json={"model": model, "input": ["test"]},
            )
            if r.status_code == 200:
                return True, ""
            if r.status_code == 404:
                return False, f"Embedding model '{model}' not found. Run: ollama pull {model}"
            return False, f"Ollama error {r.status_code}: {r.text[:150]}"
    except httpx.ConnectError as e:
        logger.debug("Embed check connect failed: %s", e)
        return False, "Cannot connect to Ollama. Is it running? Start with: ollama serve"
    except httpx.TimeoutException as e:
        logger.debug("Embed check timeout: %s", e)
        return False, "Ollama timed out. Try: ollama serve"
    except Exception as e:
        logger.warning("Embed check failed: %s", e)
        return False, str(e)


def embed(texts: list[str], model: str = DEFAULT_EMBED_MODEL, base_url: str = OLLAMA_BASE_URL) -> list[list[float]]:
    """Generate embeddings for a list of texts via Ollama."""
    if not texts:
        return []
    base_url = base_url.rstrip("/")
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{base_url}/api/embed",
            json={"model": model, "input": texts, "keep_alive": "5m"},
        )
        if response.status_code != 200:
            raise RuntimeError(f"Ollama embed failed: {response.status_code} {response.text[:200]}")
        data = response.json()
        return data.get("embeddings", [])
