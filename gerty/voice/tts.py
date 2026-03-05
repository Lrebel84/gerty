"""Text-to-speech using Piper."""

import io
from pathlib import Path

from gerty.config import PROJECT_ROOT, PIPER_VOICE_PATH
from gerty.settings import load as load_settings


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


class TextToSpeech:
    """Piper-based text-to-speech."""

    def __init__(self, voice_path: Path | str | None = None):
        self.voice_path = Path(voice_path) if voice_path else get_piper_voice_path()
        self._voice = None
        self.sample_rate = 22050  # Piper default

    def _ensure_loaded(self):
        if self._voice is not None:
            return
        # Resolve path: could be dir (en_US-amy-medium) or .onnx file
        onnx_path = self.voice_path
        if onnx_path.is_dir():
            # Find .onnx in directory
            onnx_files = list(onnx_path.glob("*.onnx"))
            if not onnx_files:
                raise FileNotFoundError(
                    f"No .onnx file in {onnx_path}. "
                    "Download Piper voices from https://huggingface.co/rhasspy/piper-voices"
                )
            onnx_path = onnx_files[0]
        elif not onnx_path.suffix == ".onnx":
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
            raise ImportError(
                "piper-tts not installed. Run: pip install piper-tts"
            )

    def synthesize(self, text: str) -> bytes:
        """Synthesize text to raw 16-bit PCM audio bytes."""
        self._ensure_loaded()
        chunks = []
        for chunk in self._voice.synthesize(text):
            chunks.append(chunk.audio_int16_bytes)
        return b"".join(chunks)

    def get_sample_rate(self) -> int:
        """Get output sample rate (Piper typically 22050 Hz)."""
        return self.sample_rate

    def is_available(self) -> bool:
        """Check if voice model exists."""
        p = self.voice_path
        if p.is_dir():
            return bool(list(p.glob("*.onnx")))
        return (p.with_suffix(".onnx") if p.suffix != ".onnx" else p).exists()
