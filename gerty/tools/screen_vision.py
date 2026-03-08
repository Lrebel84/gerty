"""Screen vision: capture screenshot and send to vision model (Ollama or OpenRouter)."""

import base64
import io
import logging
from typing import TYPE_CHECKING

from gerty.config import OLLAMA_VISION_MODEL
from gerty.settings import load as load_settings
from gerty.tools.base import Tool

if TYPE_CHECKING:
    from gerty.llm.router import Router

logger = logging.getLogger(__name__)

# Max dimension for downscaling (vision models have context limits)
MAX_DIMENSION = 1280


def _capture_screenshot() -> tuple[bytes | None, str | None]:
    """Capture full screen as PNG bytes. Returns (png_bytes, error_msg)."""
    try:
        import mss
        import mss.tools
    except ImportError:
        return None, "mss not installed. Run: pip install mss"

    try:
        with mss.mss() as sct:
            monitor = sct.monitors[0]  # All monitors combined
            sct_img = sct.grab(monitor)
            png_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)

            # Optional downscaling if too large
            if sct_img.width > MAX_DIMENSION or sct_img.height > MAX_DIMENSION:
                try:
                    from PIL import Image

                    img = Image.open(io.BytesIO(png_bytes))
                    img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    png_bytes = buf.getvalue()
                except ImportError:
                    pass  # No PIL, use full size

            return png_bytes, None
    except Exception as e:
        logger.debug("Screenshot capture failed: %s", e)
        err = str(e)
        if "wayland" in err.lower() or "permission" in err.lower():
            return None, "Screen capture failed (possibly Wayland). Try running under X11 or use grim/slurp."
        return None, f"Screen capture failed: {err}"


def _default_prompt(message: str) -> str:
    """Use message if substantive, else default prompt."""
    lower = message.lower().strip()
    generic = [
        "what am I looking at",
        "what's on screen",
        "what do you see",
        "what is on screen",
        "what's on my screen",
        "describe my screen",
        "describe the screen",
        "screenshot",
        "look at my screen",
    ]
    if any(lower == g or lower.startswith(g + " ") for g in generic):
        return "Describe what is visible on this screen in detail."
    return message


class ScreenVisionTool(Tool):
    """Capture screen and send to vision model (Ollama or OpenRouter)."""

    def __init__(self, router: "Router"):
        self._router = router

    @property
    def name(self) -> str:
        return "screen_vision"

    @property
    def description(self) -> str:
        return "Describe or analyze screen content"

    def execute(self, intent: str, message: str) -> str:
        png_bytes, err = _capture_screenshot()
        if err:
            return f"Could not capture screen: {err}"

        b64_str = base64.b64encode(png_bytes).decode("utf-8")
        prompt = _default_prompt(message)

        settings = load_settings()
        provider = settings.get("provider", "local")

        if provider == "openrouter":
            if not self._router.openrouter.is_available():
                return "OpenRouter is not configured. Add OPENROUTER_API_KEY to .env"
            try:
                model = settings.get("openrouter_model")
                return self._router.openrouter.chat_with_images(
                    prompt,
                    images=[b64_str],
                    model=model,
                    system_prompt="Format replies in Markdown. Use code blocks for code.",
                )
            except Exception as e:
                logger.debug("OpenRouter vision failed: %s", e)
                return f"Vision request failed: {e}"

        # Local Ollama
        if not self._router.ollama.is_available():
            return "Ollama is not running. Start with: ollama serve"
        try:
            return self._router.ollama.chat_with_images(
                prompt,
                images=[png_bytes],
                model=OLLAMA_VISION_MODEL,
                system_prompt="Format replies in Markdown. Use code blocks for code.",
            )
        except Exception as e:
            logger.debug("Ollama vision failed: %s", e)
            return f"Vision request failed: {e}"
