"""Audio feedback: ping tones for listening/processing state."""

import numpy as np

from gerty.config import PING_LISTENING_ENABLED, PING_PROCESSING_ENABLED
from gerty.voice.audio import play_queued

PING_SAMPLE_RATE = 22050
PING_DURATION_MS = 120
PING_FREQ_LISTENING = 660  # Hz - lower tone for "listening"
PING_FREQ_PROCESSING = 880  # Hz - higher tone for "processing"


def _create_ping(freq_hz: float, duration_ms: int = PING_DURATION_MS) -> bytes:
    """Generate a short sine-wave ping as 16-bit PCM."""
    num_samples = int(PING_SAMPLE_RATE * duration_ms / 1000)
    t = np.linspace(0, duration_ms / 1000, num_samples, dtype=np.float32)
    sine = np.sin(2 * np.pi * freq_hz * t)
    # Apply envelope to avoid click: short fade in/out
    envelope = np.ones_like(sine)
    fade = int(num_samples * 0.1)  # 10% fade
    envelope[:fade] = np.linspace(0, 1, fade)
    envelope[-fade:] = np.linspace(1, 0, fade)
    sine = sine * envelope * 0.3  # 30% volume
    pcm = (sine * 32767).astype(np.int16)
    return pcm.tobytes()


def play_listening_ping() -> None:
    """Play ping when system starts listening (after wake word)."""
    if not PING_LISTENING_ENABLED:
        return
    data = _create_ping(PING_FREQ_LISTENING)
    play_queued(data, PING_SAMPLE_RATE)


def play_processing_ping() -> None:
    """Play ping when recording stops and processing begins."""
    if not PING_PROCESSING_ENABLED:
        return
    data = _create_ping(PING_FREQ_PROCESSING)
    play_queued(data, PING_SAMPLE_RATE)
