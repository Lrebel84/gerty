#!/usr/bin/env python3
"""Generate synthetic "gerty" audio for openWakeWord training using Piper TTS.

Uses all en_GB voices + spellings "Gerty" and "Gertie" evenly. Run
scripts/test_gerty_spellings.py first to download British voices.

Output: 16 kHz, 16-bit, mono WAV files (1.0–2.0 s) for use in the official
openWakeWord training notebook.

Usage:
    python3 scripts/generate_synthetic_gerty.py --count 500 --output models/wakeword/gerty_synthetic
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TARGET_SR = 16000

# British voices (run test_gerty_spellings.py first to download)
DEFAULT_VOICES = [
    "en_GB-northern_english_male-medium",
    "en_GB-alan-medium",
    "en_GB-alba-medium",
    "en_GB-jenny_dioco-medium",
]

# Spellings to use evenly
SPELLINGS = ["Gerty", "Gertie"]


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic 'gerty' WAV files for wake word training"
    )
    parser.add_argument("--count", type=int, default=500, help="Number of samples")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "models" / "wakeword" / "gerty_synthetic",
        help="Output directory",
    )
    parser.add_argument(
        "--voices",
        nargs="+",
        default=None,
        help="Piper voice IDs. Default: all en_GB voices.",
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    try:
        import numpy as np
        import scipy.io.wavfile
    except ImportError as e:
        print(f"Error: {e}")
        print("Install: pip install piper-tts scipy")
        sys.exit(1)

    from gerty.voice.tts import PiperTTS

    voices = args.voices or DEFAULT_VOICES
    piper_dir = PROJECT_ROOT / "models" / "piper"

    # Filter to only voices that exist
    available = [v for v in voices if (piper_dir / f"{v}.onnx").exists()]
    if not available:
        print("Error: No British voices found. Run: python3 scripts/test_gerty_spellings.py")
        sys.exit(1)
    voices = available

    print(f"Generating {args.count} samples to {args.output}")
    print(f"Voices: {voices} ({len(voices)} voices)")
    print(f"Spellings: {SPELLINGS} (evenly distributed)")

    for i in range(args.count):
        voice_id = voices[i % len(voices)]
        spelling = SPELLINGS[i % len(SPELLINGS)]
        path = piper_dir / f"{voice_id}.onnx"
        tts = PiperTTS(voice_path=path)
        if not tts.is_available():
            print(f"Error: Voice {voice_id} not found")
            sys.exit(1)
        audio_bytes = tts.synthesize(spelling)
        sr = tts.get_sample_rate()

        arr = np.frombuffer(audio_bytes, dtype=np.int16)
        if arr.ndim > 1:
            arr = arr.mean(axis=1).astype(np.int16)

        # Resample to 16 kHz if needed
        if sr != TARGET_SR:
            from scipy import signal
            num = int(len(arr) * TARGET_SR / sr)
            arr = signal.resample(arr.astype(np.float64), num).astype(np.int16)

        # Trim/pad to 1.0–1.5 s (openWakeWord wants 1–2 s)
        target_len = int(TARGET_SR * (1.0 + (i % 6) * 0.1))  # 1.0–1.5 s
        if len(arr) > target_len:
            arr = arr[:target_len]
        else:
            arr = np.pad(arr, (0, target_len - len(arr)))

        out_path = args.output / f"gerty_{i+1:05d}.wav"
        scipy.io.wavfile.write(str(out_path), TARGET_SR, arr)

        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{args.count}")

    print(f"Done. {args.count} files in {args.output}")
    print("Next: use in openWakeWord training notebook (see docs/archive/WAKE_WORD_SYNTHETIC_TRAINING.md)")


if __name__ == "__main__":
    main()
