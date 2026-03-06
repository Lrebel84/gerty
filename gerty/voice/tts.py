"""Text-to-speech: Piper (default) or Kokoro-82M (ElevenLabs-like quality)."""

import logging
from pathlib import Path

import numpy as np

from gerty.config import (
    KOKORO_MODEL_PATH,
    KOKORO_VOICES_PATH,
    PIPER_VOICE_PATH,
    PROJECT_ROOT,
    TTS_BACKEND,
)
from gerty.settings import load as load_settings

logger = logging.getLogger(__name__)

# Kokoro American English voices (from VOICES.md)
KOKORO_VOICES = [
    "af_sarah",
    "af_bella",
    "af_nicole",
    "af_nova",
    "af_heart",
    "af_alloy",
    "af_aoede",
    "af_jessica",
    "af_kore",
    "af_river",
    "af_sky",
    "am_adam",
    "am_echo",
    "am_eric",
    "am_fenrir",
    "am_liam",
    "am_michael",
    "am_onyx",
    "am_puck",
    "am_santa",
]


def get_piper_voice_path(voice_id: str | None = None) -> Path:
    """Resolve Piper voice path. If voice_id is None, use settings or config default."""
    if voice_id and voice_id.strip():
        base = PROJECT_ROOT / "models" / "piper"
        vid = voice_id.replace(".onnx", "")
        if base.exists():
            for p in base.rglob(f"{vid}.onnx"):
                if p.is_file():
                    return p
            if (base / f"{vid}.onnx").exists():
                return base / f"{vid}.onnx"
    settings = load_settings()
    vid = (settings.get("piper_voice") or "").strip()
    if vid:
        return get_piper_voice_path(vid)
    return PIPER_VOICE_PATH


class PiperTTS:
    """Piper-based text-to-speech."""

    def __init__(self, voice_path: Path | str | None = None):
        self.voice_path = Path(voice_path) if voice_path else get_piper_voice_path()
        self._voice = None
        self.sample_rate = 22050  # Piper default

    def _ensure_loaded(self):
        if self._voice is not None:
            return
        onnx_path = self.voice_path
        if onnx_path.is_dir():
            onnx_files = list(onnx_path.glob("*.onnx"))
            if not onnx_files:
                raise FileNotFoundError(
                    f"No .onnx file in {onnx_path}. "
                    "Download Piper voices from https://huggingface.co/rhasspy/piper-voices"
                )
            onnx_path = onnx_files[0]
        elif onnx_path.suffix != ".onnx":
            onnx_path = onnx_path.with_suffix(".onnx")
        if not onnx_path.exists():
            raise FileNotFoundError(
                f"Piper voice not found at {self.voice_path}. "
                "Download from https://huggingface.co/rhasspy/piper-voices"
            )
        try:
            from piper import PiperVoice

            self._voice = PiperVoice.load(str(onnx_path))
        except ImportError:
            raise ImportError("piper-tts not installed. Run: pip install piper-tts")

    def synthesize(self, text: str) -> bytes:
        """Synthesize text to raw 16-bit PCM audio bytes."""
        self._ensure_loaded()
        chunks = []
        for chunk in self._voice.synthesize(text):
            chunks.append(chunk.audio_int16_bytes)
        return b"".join(chunks)

    def get_sample_rate(self) -> int:
        return self.sample_rate

    def is_available(self) -> bool:
        p = self.voice_path
        if p.is_dir():
            return bool(list(p.glob("*.onnx")))
        return (p.with_suffix(".onnx") if p.suffix != ".onnx" else p).exists()


class KokoroTTS:
    """Kokoro-82M text-to-speech (ElevenLabs-like quality, ~80MB, CPU-friendly)."""

    def __init__(self, voice: str | None = None):
        settings = load_settings()
        self.voice = voice or settings.get("kokoro_voice", "af_sarah")
        self._model = None
        self.sample_rate = 24000  # Kokoro default

    def _ensure_loaded(self):
        if self._model is not None:
            return
        if not KOKORO_MODEL_PATH.exists() or not KOKORO_VOICES_PATH.exists():
            raise FileNotFoundError(
                f"Kokoro model not found. Run ./scripts/download_models.sh or download from "
                "https://github.com/thewh1teagle/kokoro-onnx/releases "
                f"(kokoro-v1.0.onnx, voices-v1.0.bin -> {KOKORO_MODEL_PATH.parent})"
            )
        try:
            from kokoro_onnx import Kokoro

            self._model = Kokoro(str(KOKORO_MODEL_PATH), str(KOKORO_VOICES_PATH))
        except ImportError:
            raise ImportError(
                "kokoro-onnx not installed. Run: pip install kokoro-onnx"
            )

    def synthesize(self, text: str) -> bytes:
        """Synthesize text to raw 16-bit PCM audio bytes."""
        self._ensure_loaded()
        samples, sr = self._model.create(
            text,
            voice=self.voice,
            speed=1.0,
            lang="en-us",
        )
        self.sample_rate = sr
        # Kokoro returns float32 [-1, 1]; convert to int16
        if not isinstance(samples, np.ndarray):
            samples = np.array(samples, dtype=np.float32)
        arr = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
        return arr.tobytes()

    def get_sample_rate(self) -> int:
        return self.sample_rate

    def is_available(self) -> bool:
        return KOKORO_MODEL_PATH.exists() and KOKORO_VOICES_PATH.exists()


def _create_tts_backend():
    """Create TTS backend from settings or config."""
    settings = load_settings()
    backend = (settings.get("tts_backend") or TTS_BACKEND or "piper").strip().lower()
    if backend == "kokoro":
        try:
            tts = KokoroTTS()
            if tts.is_available():
                return tts
        except Exception as e:
            logger.debug("Kokoro TTS not available, falling back to Piper: %s", e)
    return PiperTTS()


class TextToSpeech:
    """Unified TTS: Piper or Kokoro based on settings."""

    def __init__(self, backend: str | None = None, voice: str | None = None):
        if backend == "kokoro":
            self._impl = KokoroTTS(voice=voice)
        elif backend == "piper":
            path = get_piper_voice_path(voice) if voice else None
            self._impl = PiperTTS(voice_path=path)
        else:
            self._impl = _create_tts_backend()
            if voice:
                if hasattr(self._impl, "voice"):
                    self._impl.voice = voice
                else:
                    self._impl.voice_path = get_piper_voice_path(voice)
                    self._impl._voice = None

    def synthesize(self, text: str) -> bytes:
        """Synthesize text to raw 16-bit PCM audio bytes."""
        return self._impl.synthesize(text)

    def get_sample_rate(self) -> int:
        return self._impl.get_sample_rate()

    def is_available(self) -> bool:
        return self._impl.is_available()
