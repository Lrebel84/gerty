"""Wake word detection: Porcupine (cloud key) or OpenWakeWord (fully local)."""

import struct
import threading
from typing import Callable, Optional

from gerty.config import PICOVOICE_ACCESS_KEY

# Thread-safe flags for push-to-talk (when no wake word available)
_ptt_requested = threading.Event()
_ptt_stop_requested = threading.Event()


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


class WakeWordDetector:
    """Listens for wake word using Porcupine (requires API key)."""

    def __init__(
        self,
        callback: Optional[Callable[[], None]] = None,
        access_key: str = PICOVOICE_ACCESS_KEY,
        keyword: str = "computer",
    ):
        self.callback = callback if callback is not None else lambda: None
        self.access_key = access_key
        self.keyword = keyword
        self._porcupine = None
        self._running = False

    def _init_porcupine(self):
        if self._porcupine is not None:
            return
        if not self.access_key:
            raise RuntimeError(
                "PICOVOICE_ACCESS_KEY not set. Get a free key at console.picovoice.ai"
            )
        import pvporcupine

        self._porcupine = pvporcupine.create(
            access_key=self.access_key,
            keywords=[self.keyword],
            sensitivities=[0.5],
        )

    def _cleanup(self):
        if self._porcupine:
            self._porcupine.delete()
            self._porcupine = None

    @property
    def frame_length(self) -> int:
        """Samples per frame (for audio capture)."""
        self._init_porcupine()
        return self._porcupine.frame_length

    @property
    def sample_rate(self) -> int:
        """Required sample rate."""
        self._init_porcupine()
        return self._porcupine.sample_rate

    def process_frame(self, pcm: bytes) -> bool:
        """
        Process one frame of audio. Returns True if wake word detected.
        pcm: 16-bit mono audio, length = frame_length * 2 bytes
        """
        self._init_porcupine()
        samples = struct.unpack_from(
            "h" * self._porcupine.frame_length, pcm
        )
        result = self._porcupine.process(samples)
        return result >= 0

    def is_available(self) -> bool:
        """Check if Porcupine is configured."""
        return bool(self.access_key)


class OpenWakeWordDetector:
    """Fully local wake word detection using OpenWakeWord (no API key)."""

    SAMPLE_RATE = 16000
    FRAME_LENGTH = 1280  # 80ms at 16kHz

    def __init__(self, keyword: str = "hey jarvis"):
        self.keyword = keyword
        self._model = None
        self._threshold = 0.5

    def _ensure_loaded(self):
        if self._model is not None:
            return
        try:
            from openwakeword.model import Model
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
            arr = arr[:self.FRAME_LENGTH]
        pred = self._model.predict(arr)
        for scores in pred.values():
            score = scores[-1] if isinstance(scores, (list, tuple)) and scores else scores
            if isinstance(score, (int, float)) and score > self._threshold:
                return True
        return False

    def is_available(self) -> bool:
        """Check if OpenWakeWord can be loaded."""
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False


def create_wake_detector():
    """
    Create the best available wake detector.
    Priority: Porcupine (if key) > OpenWakeWord > None (push-to-talk only).
    """
    if PICOVOICE_ACCESS_KEY:
        try:
            det = WakeWordDetector(keyword="computer")
            _ = det.frame_length  # Trigger init to verify it works
            return det, "porcupine"
        except Exception:
            pass
    try:
        det = OpenWakeWordDetector(keyword="hey jarvis")
        if det.is_available():
            return det, "openwakeword"
    except Exception:
        pass
    return None, "ptt"
