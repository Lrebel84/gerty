#!/usr/bin/env python3
"""Check your recorded 'Gerty' samples: play them, verify format, show stats.

Usage:
    python3 scripts/check_gerty_samples.py              # List all + play first 5
    python3 scripts/check_gerty_samples.py --play 3     # Play sample #3
    python3 scripts/check_gerty_samples.py --play all  # Play all (space to skip)
"""

import argparse
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = PROJECT_ROOT / "models" / "wakeword" / "gerty_samples"


def main():
    parser = argparse.ArgumentParser(description="Check Gerty wake word samples")
    parser.add_argument("--play", type=str, default="5", help="Play N samples, 'all', or single number (e.g. 3)")
    args = parser.parse_args()

    if not SAMPLES_DIR.exists():
        print(f"Error: {SAMPLES_DIR} not found")
        print("Run: python3 scripts/record_gerty_samples.py --count 50")
        sys.exit(1)

    try:
        import scipy.io.wavfile
        import sounddevice as sd
    except ImportError:
        print("Install: pip install scipy sounddevice")
        sys.exit(1)

    files = sorted(SAMPLES_DIR.glob("*.wav"))
    if not files:
        print(f"No WAV files in {SAMPLES_DIR}")
        sys.exit(1)

    print(f"Found {len(files)} samples\n")
    print(f"{'#':<4} {'File':<20} {'Rate':<8} {'Duration':<10} {'Samples':<10}")
    print("-" * 55)

    for i, f in enumerate(files, 1):
        try:
            sr, data = scipy.io.wavfile.read(str(f))
            dur = len(data) / sr if sr else 0
            n = len(data) if data.ndim == 1 else len(data) * data.shape[1]
            print(f"{i:<4} {f.name:<20} {sr:<8} {dur:.2f}s      {n}")
        except Exception as e:
            print(f"{i:<4} {f.name:<20} ERROR: {e}")

    # Play samples
    play_count = 0
    if args.play.lower() == "all":
        play_count = len(files)
    else:
        try:
            play_count = int(args.play)
        except ValueError:
            # Maybe they want to play a specific one by number
            try:
                idx = int(args.play)
                if 1 <= idx <= len(files):
                    play_count = 1
                    files = [files[idx - 1]]
                else:
                    play_count = 0
            except ValueError:
                play_count = 0

    if play_count > 0:
        print(f"\nPlaying first {min(play_count, len(files))} samples (say 'Gerty' like you did when recording)...\n")
        for i, f in enumerate(files[:play_count]):
            try:
                sr, data = scipy.io.wavfile.read(str(f))
                if data.dtype != np.int16:
                    data = (data.astype(float) / np.max(np.abs(data)) * 32767).astype(np.int16)
                if data.ndim > 1:
                    data = data.mean(axis=1).astype(np.int16)
                print(f"  [{i+1}] {f.name} ({len(data)/sr:.1f}s)")
                sd.play(data, samplerate=sr)
                sd.wait()
            except Exception as e:
                print(f"  [{i+1}] {f.name} - Error: {e}")
            except KeyboardInterrupt:
                sd.stop()
                print("\nStopped.")
                break

    print("\nExpected: 16kHz, 16-bit mono, 0.5-2s duration")
    print("If any look wrong, re-record with: python3 scripts/record_gerty_samples.py --count 80")


if __name__ == "__main__":
    main()
