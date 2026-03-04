"""Speech-to-text using Vosk."""

import json
from pathlib import Path

from gerty.config import VOSK_MODEL_PATH


class SpeechToText:
    """Vosk-based speech recognition."""

    def __init__(self, model_path: Path | str = VOSK_MODEL_PATH):
        self.model_path = Path(model_path)
        self._model = None
        self._recognizer = None

    def _ensure_loaded(self):
        if self._model is not None:
            return
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Vosk model not found at {self.model_path}. "
                "Download from https://alphacephei.com/vosk/models"
            )
        from vosk import Model, KaldiRecognizer

        self._model = Model(str(self.model_path))

    def create_recognizer(self, sample_rate: int = 16000):
        """Create a recognizer for streaming. Call _ensure_loaded first."""
        self._ensure_loaded()
        from vosk import KaldiRecognizer

        return KaldiRecognizer(self._model, sample_rate)

    def transcribe_stream(
        self, audio_chunks: list[bytes], sample_rate: int = 16000
    ) -> str:
        """Transcribe a stream of audio chunks. Returns final text."""
        rec = self.create_recognizer(sample_rate)
        for chunk in audio_chunks:
            if rec.AcceptWaveform(chunk):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()
                if text:
                    return text
        # Final partial result
        result = json.loads(rec.FinalResult())
        return result.get("text", "").strip()

    def transcribe_file(self, path: str | Path, sample_rate: int = 16000) -> str:
        """Transcribe an audio file."""
        import wave

        self._ensure_loaded()
        with wave.open(str(path), "rb") as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                raise ValueError("Audio must be 16-bit mono")
            rate = wf.getframerate()
            rec = self.create_recognizer(rate)
            text_parts = []
            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    t = result.get("text", "").strip()
                    if t:
                        text_parts.append(t)
            result = json.loads(rec.FinalResult())
            t = result.get("text", "").strip()
            if t:
                text_parts.append(t)
            return " ".join(text_parts)

    def is_available(self) -> bool:
        """Check if model exists."""
        return self.model_path.exists()
