"""Speaker verification stub for future voice-based security.

To enable: implement verify(audio_chunks, sample_rate) to return True if the
speaker matches an enrolled voice, False otherwise. Integrate into
voice loop after recording ends, before STT.
"""


def verify(audio_chunks: list[bytes], sample_rate: int = 16000) -> bool:
    """Verify speaker identity. Stub: always allows (no verification yet)."""
    return True
