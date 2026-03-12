#!/usr/bin/env python3
"""Record your room's background/ambient noise for wake word training.

Your mic + room produces different audio than synthetic silence. Recording
real background helps the model learn to stay LOW when you're not saying "Gerty".

Usage:
    python3 scripts/record_background.py
    # Stay SILENT - let it capture room tone, fan, AC, etc.
    # Then run: python3 scripts/train_gerty_wakeword.py
"""

import sys
from pathlib import Path

import numpy as np
import sounddevice as sd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = np.int16


def record_seconds(seconds: float) -> np.ndarray:
    """Record from microphone. Returns int16 array."""
    samples = int(SAMPLE_RATE * seconds)
    print(f"Recording {seconds}s... ", end="", flush=True)
    result = sd.rec(
        samples,
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype=DTYPE,
    )
    sd.wait()
    data = result[0] if isinstance(result, tuple) else result
    arr = data.flatten() if data.ndim > 1 else data
    print("done.")
    return np.asarray(arr, dtype=np.int16)


def save_wav(arr: np.ndarray, path: Path) -> None:
    import struct
    pcm = arr.tobytes()
    n = len(pcm)
    wav = (
        b"RIFF"
        + struct.pack("<I", 36 + n)
        + b"WAVE"
        + b"fmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, SAMPLE_RATE, SAMPLE_RATE * 2, 2, 16)
        + b"data"
        + struct.pack("<I", n)
        + pcm
    )
    path.write_bytes(wav)


def main():
    out_dir = PROJECT_ROOT / "models" / "wakeword" / "background_samples"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\nRecord your room's background (stay SILENT).")
    print("Let it capture: room tone, fan, AC, computer hum, etc.")
    print(f"Output: {out_dir}\n")
    input("Press Enter when ready (don't say anything)...")

    # Record 20 seconds - we'll slice into 3s chunks for training
    arr = record_seconds(20.0)
    out_path = out_dir / "background_001.wav"
    save_wav(arr, out_path)
    print(f"Saved: {out_path}")

    print("\nDone! Run: python3 scripts/train_gerty_wakeword.py")


if __name__ == "__main__":
    main()
