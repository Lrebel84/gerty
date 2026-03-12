#!/usr/bin/env python3
"""Prepare files for openWakeWord Colab training.

Creates gerty_synthetic.tar.gz for upload and downloads negative data (fma, fsd50k).
You will upload gerty_synthetic.tar.gz to Colab and extract it there.

Usage:
    python3 scripts/prepare_training_upload.py
"""

import sys
import tarfile
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GERTY_SYNTHETIC = PROJECT_ROOT / "models" / "wakeword" / "gerty_synthetic"
OUTPUT_DIR = PROJECT_ROOT / "models" / "wakeword" / "training_data"

FMA_URL = "https://f002.backblazeb2.com/file/openwakeword-resources/data/fma_sample.zip"
FSD50K_URL = "https://f002.backblazeb2.com/file/openwakeword-resources/data/fsd50k_sample.zip"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Create tarball of gerty_synthetic for Colab upload
    if not GERTY_SYNTHETIC.exists():
        print(f"Error: {GERTY_SYNTHETIC} not found.")
        print("Run: python3 scripts/generate_synthetic_gerty.py --count 500")
        sys.exit(1)

    tar_path = OUTPUT_DIR / "gerty_synthetic.tar.gz"
    print(f"Creating {tar_path}...")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(GERTY_SYNTHETIC, arcname="gerty_synthetic")
    print(f"  Done. Upload this file to Colab: {tar_path}")

    # 2. Download negative data (optional - Colab can download too)
    for name, url in [("fma_sample.zip", FMA_URL), ("fsd50k_sample.zip", FSD50K_URL)]:
        dest = OUTPUT_DIR / name
        if dest.exists():
            print(f"  {name} already exists")
            continue
        print(f"Downloading {name}...")
        try:
            urllib.request.urlretrieve(url, dest)
            print(f"  Saved to {dest}")
        except Exception as e:
            print(f"  Failed: {e}. You can download in Colab instead.")

    print("\nNext: see docs/archive/WAKE_WORD_SYNTHETIC_TRAINING.md for Colab steps (archived; Picovoice is now the supported wake word).")


if __name__ == "__main__":
    main()
