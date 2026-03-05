"""Voice Activity Detection using Silero VAD."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Silero expects 512 samples at 16kHz (32ms chunks)
VAD_CHUNK_SAMPLES = 512
VAD_SAMPLE_RATE = 16000


class VADDetector:
    """
    Silero VAD wrapper for end-of-speech detection.
    Accepts 16kHz mono PCM chunks (512 samples = 32ms).
    Returns is_end_of_speech when min_silence_duration_ms of silence follows speech.
    """

    def __init__(
        self,
        min_silence_duration_ms: int = 700,
        speech_pad_ms: int = 100,
        threshold: float = 0.6,  # 0.6 = less sensitive to ambient (was 0.5)
    ):
        self.min_silence_duration_ms = min_silence_duration_ms
        self.speech_pad_ms = speech_pad_ms
        self.threshold = threshold
        self._model = None
        self._iterator = None

    def _ensure_loaded(self):
        if self._model is not None:
            return
        try:
            from silero_vad import load_silero_vad, VADIterator

            self._model = load_silero_vad()
            self._iterator = VADIterator(
                self._model,
                threshold=self.threshold,
                sampling_rate=VAD_SAMPLE_RATE,
                min_silence_duration_ms=self.min_silence_duration_ms,
                speech_pad_ms=self.speech_pad_ms,
            )
        except ImportError as e:
            raise ImportError(
                "silero-vad not installed. Run: pip install silero-vad"
            ) from e

    def reset(self):
        """Reset VAD state. Call when starting a new recording."""
        self._ensure_loaded()
        self._iterator.reset_states()

    def process_chunk(self, pcm: bytes) -> bool:
        """
        Process one chunk of PCM audio (512 samples, 16-bit mono).
        Returns True if end-of-speech detected (silence after speech).
        """
        self._ensure_loaded()
        import numpy as np

        arr = np.frombuffer(pcm, dtype=np.int16)
        if len(arr) < VAD_CHUNK_SAMPLES:
            return False
        if len(arr) > VAD_CHUNK_SAMPLES:
            arr = arr[:VAD_CHUNK_SAMPLES]

        # Silero expects float32 normalized to [-1, 1]
        tensor = arr.astype(np.float32) / 32768.0

        try:
            import torch

            chunk_tensor = torch.from_numpy(tensor)
        except ImportError:
            # silero-vad uses torch; if we get here, something is wrong
            return False

        result = self._iterator(chunk_tensor, return_seconds=False)
        if result is not None and "end" in result:
            return True
        return False

    def process_chunk_from_larger_buffer(self, pcm: bytes) -> bool:
        """
        Process PCM that may be larger than 512 samples.
        Splits into 512-sample chunks and processes each.
        Returns True if any chunk triggers end-of-speech.
        """
        import numpy as np

        arr = np.frombuffer(pcm, dtype=np.int16)
        end_detected = False
        for i in range(0, len(arr), VAD_CHUNK_SAMPLES):
            chunk = arr[i : i + VAD_CHUNK_SAMPLES]
            if len(chunk) < VAD_CHUNK_SAMPLES:
                break
            if self.process_chunk(chunk.tobytes()):
                end_detected = True
                break
        return end_detected

    def is_available(self) -> bool:
        """Check if Silero VAD can be loaded."""
        try:
            self._ensure_loaded()
            return True
        except Exception:
            return False
