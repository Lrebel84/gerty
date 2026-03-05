"""Speech-to-text: Vosk, faster-whisper, or Groq."""

import io
import json
import logging
import tempfile
from pathlib import Path

from gerty.config import (
    FASTER_WHISPER_DEVICE,
    FASTER_WHISPER_MODEL,
    GROQ_API_KEY,
    STT_BACKEND,
    VOSK_MODEL_PATH,
)

logger = logging.getLogger(__name__)


def _pcm_to_wav_bytes(pcm: bytes, sample_rate: int = 16000) -> bytes:
    """Wrap 16-bit mono PCM in a minimal WAV header."""
    import struct

    n = len(pcm)
    wav = (
        b"RIFF"
        + struct.pack("<I", 36 + n)
        + b"WAVE"
        + b"fmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
        + b"data"
        + struct.pack("<I", n)
        + pcm
    )
    return wav


class VoskSTT:
    """Vosk-based speech recognition (legacy)."""

    def __init__(self, model_path: Path | str = VOSK_MODEL_PATH):
        self.model_path = Path(model_path)
        self._model = None

    def _ensure_loaded(self):
        if self._model is not None:
            return
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Vosk model not found at {self.model_path}. "
                "Download from https://alphacephei.com/vosk/models"
            )
        from vosk import Model

        self._model = Model(str(self.model_path))

    def transcribe_stream(
        self, audio_chunks: list[bytes], sample_rate: int = 16000
    ) -> str:
        """Transcribe a stream of audio chunks. Returns final text."""
        from vosk import KaldiRecognizer

        self._ensure_loaded()
        rec = KaldiRecognizer(self._model, sample_rate)
        for chunk in audio_chunks:
            if rec.AcceptWaveform(chunk):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()
                if text:
                    return text
        result = json.loads(rec.FinalResult())
        return result.get("text", "").strip()

    def is_available(self) -> bool:
        return self.model_path.exists()


class FasterWhisperSTT:
    """faster-whisper speech recognition (CTranslate2, 4x faster than OpenAI Whisper)."""

    def __init__(
        self,
        model_size: str = FASTER_WHISPER_MODEL,
        device: str = FASTER_WHISPER_DEVICE,
        compute_type: str = "int8",
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _ensure_loaded(self):
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        except ImportError as e:
            raise ImportError(
                "faster-whisper not installed. Run: pip install faster-whisper"
            ) from e

    def transcribe_stream(
        self, audio_chunks: list[bytes], sample_rate: int = 16000
    ) -> str:
        """Transcribe audio chunks. Returns final text."""
        self._ensure_loaded()
        if not audio_chunks:
            return ""
        pcm = b"".join(audio_chunks)
        wav = _pcm_to_wav_bytes(pcm, sample_rate)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav)
            path = f.name
        try:
            segments, _ = self._model.transcribe(
                path,
                language="en",
                beam_size=1,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300),
            )
            text = " ".join(seg.text.strip() for seg in segments if seg.text).strip()
            return text
        finally:
            Path(path).unlink(missing_ok=True)

    def is_available(self) -> bool:
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False


class GroqSTT:
    """Groq Whisper API (cloud, 216x real-time)."""

    def __init__(self, api_key: str = GROQ_API_KEY):
        self.api_key = api_key or GROQ_API_KEY

    def transcribe_stream(
        self, audio_chunks: list[bytes], sample_rate: int = 16000
    ) -> str:
        """Transcribe via Groq API. Returns final text."""
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY not set")
        if not audio_chunks:
            return ""
        pcm = b"".join(audio_chunks)
        wav = _pcm_to_wav_bytes(pcm, sample_rate)
        import httpx

        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": ("audio.wav", io.BytesIO(wav), "audio/wav")},
                data={"model": "whisper-large-v3-turbo"},
            )
            r.raise_for_status()
            data = r.json()
            return data.get("text", "").strip()

    def is_available(self) -> bool:
        return bool(self.api_key)


def _create_stt_backend(
    backend: str | None = None,
    faster_whisper_model: str | None = None,
):
    """Create STT backend based on config or overrides from settings.
    Tries preferred backend first, then fallbacks (vosk, groq) if it fails."""
    backend = (backend or STT_BACKEND or "").strip().lower()
    model = (faster_whisper_model or FASTER_WHISPER_MODEL or "base").strip()
    order = [backend] if backend else []
    # Add fallbacks: prefer vosk (offline, model exists) then groq
    if "vosk" not in order and VOSK_MODEL_PATH.exists():
        order.append("vosk")
    if "groq" not in order and GROQ_API_KEY:
        order.append("groq")
    for b in order:
        if b == "groq" and GROQ_API_KEY:
            try:
                return GroqSTT()
            except Exception as e:
                logger.debug("Groq STT failed: %s", e)
        elif b == "faster_whisper":
            try:
                stt = FasterWhisperSTT(model_size=model)
                if stt.is_available():
                    return stt
            except Exception as e:
                logger.debug("faster-whisper not available: %s", e)
        elif b == "vosk":
            try:
                return VoskSTT()
            except Exception as e:
                logger.debug("Vosk STT failed: %s", e)
    raise RuntimeError(
        "No STT backend available. Set STT_BACKEND=faster_whisper (pip install faster-whisper) "
        "or STT_BACKEND=vosk with VOSK_MODEL_PATH, or STT_BACKEND=groq with GROQ_API_KEY."
    )


class SpeechToText:
    """
    Facade that selects STT backend from config or settings.
    Supports: vosk, faster_whisper, groq.
    """

    def __init__(
        self,
        backend: str | None = None,
        faster_whisper_model: str | None = None,
    ):
        self._backend = None
        self._backend_override = backend
        self._model_override = faster_whisper_model

    def _get_backend(self):
        if self._backend is None:
            self._backend = _create_stt_backend(
                backend=self._backend_override,
                faster_whisper_model=self._model_override,
            )
        return self._backend

    def transcribe_stream(
        self, audio_chunks: list[bytes], sample_rate: int = 16000
    ) -> str:
        """Transcribe a stream of audio chunks. Returns final text."""
        return self._get_backend().transcribe_stream(audio_chunks, sample_rate)

    def transcribe_file(self, path: str | Path, sample_rate: int = 16000) -> str:
        """Transcribe an audio file."""
        path = Path(path)
        with open(path, "rb") as f:
            data = f.read()
        # Assume WAV; extract PCM if needed, or pass through for faster-whisper
        backend = self._get_backend()
        if isinstance(backend, VoskSTT):
            import wave

            with wave.open(str(path), "rb") as wf:
                if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                    raise ValueError("Audio must be 16-bit mono")
                rate = wf.getframerate()
                chunks = []
                while True:
                    d = wf.readframes(4000)
                    if not d:
                        break
                    chunks.append(d)
                return backend.transcribe_stream(chunks, rate)
        # faster-whisper and Groq accept file path
        if isinstance(backend, FasterWhisperSTT):
            backend._ensure_loaded()
            segments, _ = backend._model.transcribe(str(path), language="en", beam_size=1)
            return " ".join(seg.text.strip() for seg in segments if seg.text).strip()
        if isinstance(backend, GroqSTT):
            import httpx

            with open(path, "rb") as f:
                data = f.read()
            with httpx.Client(timeout=30.0) as client:
                r = client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                    files={"file": (path.name, io.BytesIO(data), "audio/wav")},
                    data={"model": "whisper-large-v3-turbo"},
                )
                r.raise_for_status()
                return r.json().get("text", "").strip()
        return ""

    def is_available(self) -> bool:
        try:
            return self._get_backend().is_available()
        except Exception:
            return False
