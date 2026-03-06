"""Audio capture and playback."""

import queue
import threading
from typing import Iterator

import numpy as np
import sounddevice as sd


SAMPLE_RATE = 16000  # Porcupine and Vosk use 16kHz
CHANNELS = 1
DTYPE = np.int16

# Sentinel objects for play queue
_PLAY_END = object()
_PLAY_STOP = object()

_play_queue: queue.Queue = queue.Queue()
_play_drained = threading.Event()
_play_thread: threading.Thread | None = None
_play_lock = threading.Lock()


def _playback_worker() -> None:
    """Daemon thread: consume queue and play audio. Stops on _PLAY_STOP."""
    global _play_thread
    while True:
        try:
            item = _play_queue.get()
            if item is _PLAY_STOP:
                _play_drained.set()
                break
            if item is _PLAY_END:
                _play_drained.set()
                continue
            data, sample_rate = item
            if data:
                arr = np.frombuffer(data, dtype=DTYPE)
                sd.play(arr, samplerate=sample_rate)
                sd.wait()
        except Exception:
            _play_drained.set()
            break
    with _play_lock:
        _play_thread = None


def _ensure_play_thread() -> None:
    """Start playback thread if not running."""
    global _play_thread
    with _play_lock:
        if _play_thread is None or not _play_thread.is_alive():
            _play_drained.clear()
            _play_thread = threading.Thread(target=_playback_worker, daemon=True)
            _play_thread.start()


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


def prepare_play_queue() -> None:
    """Prepare for a new voice response. Call before queueing audio. Clears drained state."""
    _ensure_play_thread()
    _play_drained.clear()


def play_queued(data: bytes, sample_rate: int = 22050) -> None:
    """Queue audio for playback. Returns immediately. Plays in order."""
    _ensure_play_thread()
    _play_queue.put((data, sample_rate))


def drain_play_queue() -> None:
    """Block until current response is fully played. Call after queueing all audio and END."""
    _play_drained.wait()


def stop_playback() -> None:
    """Immediately stop currently playing audio. Call on cancel."""
    sd.stop()
    while not _play_queue.empty():
        try:
            _play_queue.get_nowait()
        except queue.Empty:
            break
    _play_queue.put(_PLAY_STOP)
    _play_drained.set()


def put_play_end() -> None:
    """Signal end of current voice response. drain_play_queue waits for this."""
    _play_drained.clear()
    _play_queue.put(_PLAY_END)


class AudioPlayback:
    """Play audio from bytes (16-bit PCM)."""

    @staticmethod
    def play(data: bytes, sample_rate: int = 22050):
        """Play raw PCM audio. Blocks until done."""
        arr = np.frombuffer(data, dtype=DTYPE)
        sd.play(arr, samplerate=sample_rate)
        sd.wait()
