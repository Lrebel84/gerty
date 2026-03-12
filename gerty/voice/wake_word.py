"""Wake word detection: Picovoice Porcupine (custom "our Gurt") or openWakeWord."""

import threading
from pathlib import Path
from typing import Optional

from gerty.config import (
    PICOVOICE_ACCESS_KEY,
    PICOVOICE_KEYWORD_PATH,
    WAKE_WORD_MODEL_PATH,
    WAKE_WORD_THRESHOLD,
)

# Thread-safe flags for push-to-talk (when no wake word available)
_ptt_requested = threading.Event()
_ptt_stop_requested = threading.Event()
_voice_cancel_requested = threading.Event()


def request_ptt_recording():
    """Signal voice loop to start recording (push-to-talk)."""
    _ptt_stop_requested.clear()
    _ptt_requested.set()


def stop_ptt_recording():
    """Signal voice loop to stop recording (push-to-talk)."""
    _ptt_stop_requested.set()
    _ptt_requested.clear()


def consume_ptt_request() -> bool:
    """Check and consume a PTT start request. Returns True if user requested recording."""
    if _ptt_requested.is_set():
        _ptt_requested.clear()
        return True
    return False


def is_ptt_stop_requested() -> bool:
    """Check if user requested to stop recording."""
    return _ptt_stop_requested.is_set()


def clear_ptt_stop():
    """Clear the stop flag after processing."""
    _ptt_stop_requested.clear()


def request_voice_cancel():
    """Signal voice loop to cancel current processing (STT/LLM/TTS)."""
    _voice_cancel_requested.set()


def consume_voice_cancel() -> bool:
    """Check and consume a voice cancel request. Returns True if cancel was requested."""
    if _voice_cancel_requested.is_set():
        _voice_cancel_requested.clear()
        return True
    return False


def clear_voice_cancel():
    """Clear cancel flag (e.g. when starting new recording)."""
    _voice_cancel_requested.clear()


class PorcupineDetector:
    """Picovoice Porcupine wake word detection (custom model, e.g. "our Gurt")."""

    SAMPLE_RATE = 16000

    def __init__(self, access_key: str, keyword_path: Path):
        self._access_key = access_key
        self._keyword_path = Path(keyword_path)
        self._handle = None
        self.last_score = 0.0

    def _ensure_loaded(self):
        if self._handle is not None:
            return
        import pvporcupine
        self._handle = pvporcupine.create(
            access_key=self._access_key,
            keyword_paths=[str(self._keyword_path)],
        )

    @property
    def frame_length(self) -> int:
        self._ensure_loaded()
        return self._handle.frame_length

    @property
    def sample_rate(self) -> int:
        return self.SAMPLE_RATE

    def process_frame(self, pcm: bytes) -> bool:
        """Process one frame. Returns True if wake word detected."""
        self._ensure_loaded()
        import numpy as np
        arr = np.frombuffer(pcm, dtype=np.int16)
        if len(arr) < self._handle.frame_length:
            return False
        if len(arr) > self._handle.frame_length:
            arr = arr[: self._handle.frame_length]
        idx = self._handle.process(arr)
        self.last_score = 1.0 if idx >= 0 else 0.0
        return idx >= 0

    def is_available(self) -> bool:
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False


class OpenWakeWordDetector:
    """Fully local wake word detection using openWakeWord (no API key).

    Loads standard .onnx models from the official openWakeWord synthetic training
    pipeline. Archived: docs/archive/WAKE_WORD_SYNTHETIC_TRAINING.md.
    """

    SAMPLE_RATE = 16000
    FRAME_LENGTH = 1280  # 80ms at 16kHz

    def __init__(
        self,
        keyword: str = "hey jarvis",
        model_path: Optional[Path] = None,
        threshold: float = 0.5,
    ):
        self.keyword = keyword
        self.model_path = Path(model_path) if model_path else None
        self._threshold = threshold
        self._model = None
        self.last_score = 0.0

    def _ensure_loaded(self):
        if self._model is not None:
            return
        try:
            from openwakeword.model import Model

            if self.model_path and self.model_path.is_file():
                self._model = Model(
                    wakeword_models=[str(self.model_path)],
                    inference_framework="onnx",
                )
            else:
                import openwakeword
                openwakeword.utils.download_models()
                self._model = Model(inference_framework="onnx")
        except ImportError as e:
            raise ImportError(
                "openwakeword not installed. Run: pip install openwakeword"
            ) from e

    @property
    def frame_length(self) -> int:
        return self.FRAME_LENGTH

    @property
    def sample_rate(self) -> int:
        return self.SAMPLE_RATE

    def process_frame(self, pcm: bytes) -> bool:
        """Process one frame. Returns True if wake word detected."""
        self._ensure_loaded()
        import numpy as np
        arr = np.frombuffer(pcm, dtype=np.int16)
        if len(arr) < self.FRAME_LENGTH:
            return False
        if len(arr) > self.FRAME_LENGTH:
            arr = arr[: self.FRAME_LENGTH]
        pred = self._model.predict(arr)
        for scores in pred.values():
            score = scores[-1] if isinstance(scores, (list, tuple)) and scores else scores
            try:
                s = float(score)
                self.last_score = s
                if s > self._threshold:
                    return True
            except (TypeError, ValueError):
                pass
        return False

    def is_available(self) -> bool:
        """Check if openWakeWord can be loaded."""
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False


def create_wake_detector():
    """
    Create the best available wake detector.
    Priority: Picovoice (our Gurt) > openWakeWord > PTT only.
    """
    try:
        if PICOVOICE_ACCESS_KEY and PICOVOICE_KEYWORD_PATH.is_file():
            det = PorcupineDetector(PICOVOICE_ACCESS_KEY, PICOVOICE_KEYWORD_PATH)
            if det.is_available():
                return det, "picovoice (our Gurt)"
    except Exception:
        pass
    try:
        if WAKE_WORD_MODEL_PATH.is_file():
            det = OpenWakeWordDetector(
                keyword="Gerty",
                model_path=WAKE_WORD_MODEL_PATH,
                threshold=WAKE_WORD_THRESHOLD,
            )
            if det.is_available():
                return det, "gerty (openwakeword)"
        det = OpenWakeWordDetector(keyword="hey jarvis")
        if det.is_available():
            return det, "openwakeword"
    except Exception:
        pass
    return None, "ptt"
