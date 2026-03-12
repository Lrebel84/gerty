#!/usr/bin/env python3
"""Monitor wake word score in real time. Say 'Gerty' and watch the score.

Run this, then speak. You want the score to go above your threshold (default 0.35)
when you say "Gerty". If it stays low, try lowering WAKE_WORD_THRESHOLD or retrain.

Usage:
    python3 scripts/test_wake_score.py
    WAKE_WORD_THRESHOLD=0.25 python3 scripts/test_wake_score.py  # more sensitive
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import sounddevice as sd


def main():
    from gerty.config import WAKE_WORD_THRESHOLD
    from gerty.voice.wake_word import create_wake_detector

    det, mode = create_wake_detector()
    if not det:
        print("Error: No wake word detector available (pip install pvporcupine or openwakeword)")
        sys.exit(1)
    if hasattr(det, "_ensure_loaded"):
        det._ensure_loaded()

    SAMPLE_RATE = det.sample_rate
    FRAME_LENGTH = det.frame_length

    wake_word = "our Gurt" if mode == "picovoice (our Gurt)" else ("Hey Jarvis" if mode == "openwakeword" else "Gerty")
    threshold = 0.5 if "picovoice" in mode else WAKE_WORD_THRESHOLD
    print(f"Listening for '{wake_word}' (mode={mode})")
    print("Say the wake word and watch the score. Press Ctrl+C to quit.\n")

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype=np.int16, blocksize=FRAME_LENGTH) as stream:
            while True:
                data, _ = stream.read(FRAME_LENGTH)
                pcm = data.flatten().tobytes()
                arr = np.frombuffer(pcm, dtype=np.int16)
                if len(arr) < FRAME_LENGTH:
                    continue
                arr = arr[:FRAME_LENGTH]
                det.process_frame(pcm)
                score = det.last_score
                triggered = " <<< TRIGGER" if score > threshold else ""
                bar = "█" * int(score * 40) + "░" * (40 - int(score * 40))
                label = "hey_jarvis" if mode == "openwakeword" else "gerty"
                print(f"\r{label}: {score:.3f} [{bar}]{triggered}   ", end="", flush=True)
    except KeyboardInterrupt:
        print("\nDone.")


if __name__ == "__main__":
    main()
