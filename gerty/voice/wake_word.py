"""Wake word detection using Porcupine."""

import struct
from typing import Callable, Optional

from gerty.config import PICOVOICE_ACCESS_KEY


class WakeWordDetector:
    """Listens for wake word using Porcupine."""

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
