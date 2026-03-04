"""Audio capture and playback."""

import queue
import threading
from typing import Iterator

import numpy as np
import sounddevice as sd


SAMPLE_RATE = 16000  # Porcupine and Vosk use 16kHz
CHANNELS = 1
DTYPE = np.int16


class AudioCapture:
    """Microphone capture with configurable sample rate."""

    def __init__(self, sample_rate: int = SAMPLE_RATE, block_size: int = 512):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self._stream: sd.InputStream | None = None

    def start(self):
        """Start capturing audio."""
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=self.block_size,
        )
        self._stream.start()

    def stop(self):
        """Stop capturing."""
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def read(self) -> bytes:
        """Read one block of audio. Call start() first."""
        if not self._stream:
            raise RuntimeError("AudioCapture not started")
        data, _ = self._stream.read(self.block_size)
        return data.tobytes()

    def stream_blocks(self) -> Iterator[bytes]:
        """Generator yielding audio blocks until stopped."""
        self.start()
        try:
            while True:
                yield self.read()
        finally:
            self.stop()


class AudioPlayback:
    """Play audio from bytes (16-bit PCM)."""

    @staticmethod
    def play(data: bytes, sample_rate: int = 22050):
        """Play raw PCM audio. Blocks until done."""
        arr = np.frombuffer(data, dtype=DTYPE)
        sd.play(arr, samplerate=sample_rate)
        sd.wait()
