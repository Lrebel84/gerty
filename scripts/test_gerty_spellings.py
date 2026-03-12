#!/usr/bin/env python3
"""Test British Piper voices + phonetic spellings for Yorkshire-style "Gerty".

Downloads en_GB voices, generates 1 file per Voice + Spelling combination,
saves to models/wakeword/spelling_test/. Listen to find the best match.

Usage:
    python3 scripts/test_gerty_spellings.py
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PIPER_DIR = PROJECT_ROOT / "models" / "piper"
OUTPUT_DIR = PROJECT_ROOT / "models" / "wakeword" / "spelling_test"
TARGET_SR = 16000

# British voices to download and test
VOICES = [
    "en_GB-northern_english_male-medium",
    "en_GB-alan-medium",
    "en_GB-alba-medium",
    "en_GB-jenny_dioco-medium",
]

# Phonetic spellings (Yorkshire glottal stop style)
SPELLINGS = [
    "Gerty",
    "Gertie",
    "Ger-eh",
    "Gerr-eh",
    "Geh-eh",
]

# Hugging Face base URL for rhasspy/piper-voices
HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB"


def _voice_to_path(voice_id: str) -> str:
    """Voice ID -> path (e.g. en_GB-alan-medium -> alan/medium)."""
    # en_GB-<name>-medium -> name/medium
    if not voice_id.startswith("en_GB-") or not voice_id.endswith("-medium"):
        return ""
    name = voice_id[6:-7]  # strip "en_GB-" and "-medium"
    return f"{name}/medium"


def _download_voice(voice_id: str) -> bool:
    """Download Piper voice from Hugging Face if not present."""
    onnx_path = PIPER_DIR / f"{voice_id}.onnx"
    json_path = PIPER_DIR / f"{voice_id}.onnx.json"
    if onnx_path.exists():
        return True
    path_component = _voice_to_path(voice_id)
    if not path_component:
        return False
    url_onnx = f"{HF_BASE}/{path_component}/{voice_id}.onnx"
    url_json = f"{HF_BASE}/{path_component}/{voice_id}.onnx.json"
    try:
        import urllib.request
        PIPER_DIR.mkdir(parents=True, exist_ok=True)
        print(f"  Downloading {voice_id}...")
        urllib.request.urlretrieve(url_onnx, onnx_path)
        try:
            urllib.request.urlretrieve(url_json, json_path)
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"  Failed to download {voice_id}: {e}")
        return False


def _spelling_to_filename(spelling: str) -> str:
    """Convert spelling to filename-safe string (e.g. 'Gerr-eh' -> 'gerr_eh')."""
    s = spelling.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s or "unknown"


def _voice_to_filename(voice_id: str) -> str:
    """Convert voice ID to short filename (e.g. en_GB-alan-medium -> alan)."""
    parts = voice_id.replace("en_GB-", "").replace("-medium", "").split("-")
    return "_".join(parts) if parts else voice_id


def main():
    sys.path.insert(0, str(PROJECT_ROOT))

    try:
        import numpy as np
        import scipy.io.wavfile
    except ImportError:
        print("Error: pip install scipy")
        sys.exit(1)

    from gerty.voice.tts import PiperTTS

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PIPER_DIR.mkdir(parents=True, exist_ok=True)

    print("Downloading British Piper voices...")
    for voice_id in VOICES:
        if not _download_voice(voice_id):
            print(f"  Skipping {voice_id} (download failed)")

    print("\nGenerating test files (Voice × Spelling)...")
    generated = []
    for voice_id in VOICES:
        onnx_path = PIPER_DIR / f"{voice_id}.onnx"
        if not onnx_path.exists():
            print(f"  Skip {voice_id}: not found")
            continue
        try:
            tts = PiperTTS(voice_path=onnx_path)
        except Exception as e:
            print(f"  Skip {voice_id}: {e}")
            continue
        voice_short = _voice_to_filename(voice_id)
        for spelling in SPELLINGS:
            spelling_safe = _spelling_to_filename(spelling)
            filename = f"{voice_short}_{spelling_safe}.wav"
            out_path = OUTPUT_DIR / filename
            try:
                audio_bytes = tts.synthesize(spelling)
                sr = tts.get_sample_rate()
                arr = np.frombuffer(audio_bytes, dtype=np.int16)
                if arr.ndim > 1:
                    arr = arr.mean(axis=1).astype(np.int16)
                if sr != TARGET_SR:
                    from scipy import signal
                    num = int(len(arr) * TARGET_SR / sr)
                    arr = signal.resample(arr.astype(np.float64), num).astype(np.int16)
                scipy.io.wavfile.write(str(out_path), TARGET_SR, arr)
                generated.append(out_path.name)
            except Exception as e:
                print(f"  Failed {voice_short} + {spelling!r}: {e}")

    print(f"\nDone. {len(generated)} files in {OUTPUT_DIR}")
    print("\nListen to find the best Voice + Spelling for your Yorkshire accent:")
    print("  e.g. aplay models/wakeword/spelling_test/northern_english_male_gerr_eh.wav")
    print("  or open the folder in your file manager and play with your media player.")


if __name__ == "__main__":
    main()
