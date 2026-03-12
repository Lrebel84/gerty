#!/usr/bin/env python3
"""Record your own voice saying 'Gerty' for wake word training.

Records 16kHz 16-bit mono WAV files. Aim for 50-100+ samples in varied
conditions (quiet, with background noise, different volumes).

Usage:
    python scripts/record_gerty_samples.py [--count 50] [--duration 2]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import sounddevice as sd

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = np.int16


def record_seconds(seconds: float) -> bytes:
    """Record from microphone for given seconds. Returns 16-bit PCM bytes."""
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
    print("done.")
    return data.tobytes()


def save_wav(pcm: bytes, path: Path) -> None:
    """Save PCM as WAV file."""
    import struct
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
    parser = argparse.ArgumentParser(
        description="Record 'Gerty' samples for wake word training"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=50,
        help="Number of samples to record (default: 50)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=1.5,
        help="Recording duration per sample in seconds (default: 1.5)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "models" / "wakeword" / "gerty_samples",
        help="Output directory for WAV files",
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    existing = list(args.output.glob("gerty_*.wav"))
    start_idx = max((int(f.stem.split("_")[1]) for f in existing), default=0)

    print(f"\nRecord {args.count} samples of you saying 'Gerty'.")
    print(f"Output: {args.output}")
    print(f"Each sample: {args.duration}s at 16kHz mono\n")
    input("Press Enter when ready to start...")

    for i in range(args.count):
        idx = start_idx + i + 1
        out_path = args.output / f"gerty_{idx:04d}.wav"
        print(f"\n[{i+1}/{args.count}] Say 'Gerty' clearly...")
        pcm = record_seconds(args.duration)
        save_wav(pcm, out_path)
        print(f"  Saved: {out_path.name}")

    print(f"\nDone! {args.count} samples saved to {args.output}")
    print("Run: python scripts/train_gerty_wakeword.py")


if __name__ == "__main__":
    main()
