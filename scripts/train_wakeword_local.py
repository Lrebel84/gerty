#!/usr/bin/env python3
"""Train Gerty wake word model locally (no Colab).

Combines 500 synthetic samples + 80 original user recordings into positives,
downloads negatives (FMA, FSD50k, Common Voice 11), and trains the openWakeWord
model. Output: models/wakeword/gerty.onnx.

Uses the ORIGINAL batch of user recordings (gerty_0001–gerty_0080) only,
excluding the later Gertrude test batch.

Usage:
    python3 scripts/train_wakeword_local.py

Requires: pip install openwakeword speechbrain datasets scipy matplotlib torch mutagen acoustics torchcodec
"""

import collections
import os
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
from numpy.lib.format import open_memmap
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

WAKEWORD_DIR = PROJECT_ROOT / "models" / "wakeword"
GERTY_SYNTHETIC = WAKEWORD_DIR / "gerty_synthetic"
GERTY_SAMPLES = WAKEWORD_DIR / "gerty_samples"
TRAINING_DATA = WAKEWORD_DIR / "training_data"
OUTPUT_ONNX = WAKEWORD_DIR / "gerty.onnx"

# Use first 80 user samples only (original batch; exclude Gertrude test batch)
MAX_USER_SAMPLES = 80

FMA_URL = "https://f002.backblazeb2.com/file/openwakeword-resources/data/fma_sample.zip"
FSD50K_URL = "https://f002.backblazeb2.com/file/openwakeword-resources/data/fsd50k_sample.zip"

CLIP_SIZE_SEC = 3
CV11_LIMIT = 5000  # Limit Common Voice clips for faster training


def _ensure_deps():
    """Ensure required packages are installed."""
    # Workaround: torchaudio 2.9+ removed list_audio_backends; speechbrain expects it
    try:
        import torchaudio
        if not hasattr(torchaudio, "list_audio_backends"):
            torchaudio.list_audio_backends = lambda: ["soundfile"]
    except ImportError:
        pass
    # Workaround: torchaudio.info removed in 2.9+; patch openwakeword to use scipy for WAV duration
    def _patch_get_clip_duration():
        import openwakeword.data as _data
        def _wav_duration(clip):
            try:
                import scipy.io.wavfile
                sr, data = scipy.io.wavfile.read(clip)
                if hasattr(data, "shape") and len(data.shape) > 1:
                    n = data.shape[0]
                else:
                    n = len(data)
                return n / sr
            except Exception:
                return 0
        _data.get_clip_duration = _wav_duration
    try:
        import openwakeword.data
        _patch_get_clip_duration()
    except ImportError:
        pass
    try:
        import openwakeword  # noqa: F401
        import openwakeword.data
        import openwakeword.utils
        import datasets
        import scipy
        import torch
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Install: pip install openwakeword speechbrain datasets scipy matplotlib torch mutagen")
        sys.exit(1)


def _get_original_user_samples(limit: int = MAX_USER_SAMPLES) -> list[Path]:
    """Get paths to original user recordings (gerty_NNNN.wav), first N only."""
    if not GERTY_SAMPLES.exists():
        return []
    pattern = re.compile(r"^gerty_(\d+)\.wav$")
    matches = []
    for f in GERTY_SAMPLES.iterdir():
        if f.suffix.lower() != ".wav":
            continue
        m = pattern.match(f.name)
        if m:
            matches.append((int(m.group(1)), f))
    matches.sort(key=lambda x: x[0])
    return [p for _, p in matches[:limit]]


def _get_positive_clips() -> tuple[list[str], list[float]]:
    """Combine synthetic + original user samples into positive clips."""
    import openwakeword.data

    # Synthetic: filter by duration 1.0-2.0 s
    synthetic_clips, synthetic_durations = [], []
    if GERTY_SYNTHETIC.exists():
        synthetic_clips, synthetic_durations = openwakeword.data.filter_audio_paths(
            [str(GERTY_SYNTHETIC)],
            min_length_secs=1.0,
            max_length_secs=2.0,
            duration_method="header",
        )

    # User: first 80 original (gerty_0001-gerty_0080), filter by duration
    user_paths = _get_original_user_samples()
    user_clips, user_durations = [], []
    for p in user_paths:
        d = openwakeword.data.get_clip_duration(str(p))
        if 1.0 <= d <= 2.0:
            user_clips.append(str(p))
            user_durations.append(d)

    positive_clips = synthetic_clips + user_clips
    positive_durations = synthetic_durations + user_durations

    if not positive_clips:
        print("Error: No positive clips found (after duration filter 1.0-2.0 s).")
        print(f"  Synthetic: {GERTY_SYNTHETIC} ({len(synthetic_clips)} passed)")
        print(f"  User: {GERTY_SAMPLES} ({len(user_clips)} passed, max {MAX_USER_SAMPLES})")
        sys.exit(1)

    print(f"Positive clips: {len(synthetic_clips)} synthetic + {len(user_clips)} user = {len(positive_clips)}")
    return positive_clips, positive_durations


def _download_negatives():
    """Download FMA and FSD50k samples; prepare Common Voice 11."""
    TRAINING_DATA.mkdir(parents=True, exist_ok=True)
    os.chdir(TRAINING_DATA)

    for name, url in [("fma_sample.zip", FMA_URL), ("fsd50k_sample.zip", FSD50K_URL)]:
        dest = TRAINING_DATA / name
        if dest.exists():
            print(f"  {name} already exists")
        else:
            print(f"Downloading {name}...")
            try:
                urllib.request.urlretrieve(url, dest)
            except Exception as e:
                print(f"  Failed: {e}")
                sys.exit(1)
        # Extract
        outdir = TRAINING_DATA / name.replace(".zip", "")
        if not outdir.exists():
            print(f"  Extracting {name}...")
            with zipfile.ZipFile(dest, "r") as z:
                z.extractall(TRAINING_DATA)

    # Common Voice 11
    cv_dir = TRAINING_DATA / "cv11_test_clips"
    if cv_dir.exists() and len(list(cv_dir.rglob("*.wav"))) >= CV11_LIMIT:
        print(f"  cv11_test_clips already has enough clips")
    else:
        print("Downloading Common Voice 11 (test split, English)...")
        cv_dir.mkdir(parents=True, exist_ok=True)
        import datasets
        import scipy.io.wavfile

        # Try common_voice_12_0 or 13_0 (11_0 deprecated)
        cv_11 = None
        for ds_name in ["mozilla-foundation/common_voice_12_0", "mozilla-foundation/common_voice_13_0"]:
            try:
                cv_11 = datasets.load_dataset(ds_name, "en", split="test")
                print(f"  Using {ds_name}")
                break
            except Exception as e:
                print(f"  {ds_name}: {e}")
        if cv_11 is not None:
            cv_11 = cv_11.cast_column("audio", datasets.Audio(sampling_rate=16000, mono=True))
            for i in tqdm(range(min(CV11_LIMIT, len(cv_11))), desc="Converting CV11"):
                example = cv_11[i]
                path = example.get("path") or (example.get("audio") or {}).get("path")
                if path:
                    base = Path(path).stem
                else:
                    base = f"cv11_{i:05d}"
                output = cv_dir / f"{base}.wav"
                if output.exists():
                    continue
                arr = example["audio"]["array"]
                wav_data = (arr * 32767).astype(np.int16)
                scipy.io.wavfile.write(str(output), 16000, wav_data)
        else:
            print("  Skipping Common Voice (using FMA+FSD50k only)")


def _compute_negative_features():
    """Compute negative embeddings and save to negative_features.npy."""
    import openwakeword.data
    import openwakeword.utils

    os.chdir(TRAINING_DATA)
    F = openwakeword.utils.AudioFeatures()

    neg_dirs = [
        str(TRAINING_DATA / "fma_sample"),
        str(TRAINING_DATA / "fsd50k_sample"),
        str(TRAINING_DATA / "cv11_test_clips"),
    ]
    negative_clips, negative_durations = openwakeword.data.filter_audio_paths(
        neg_dirs,
        min_length_secs=1.0,
        max_length_secs=60 * 30,
        duration_method="header",
    )
    print(f"{len(negative_clips)} negative clips (~{sum(negative_durations) // 3600} hours)")

    def _load_wav(path, target_sr=16000):
        import scipy.io.wavfile
        import scipy.signal
        sr, data = scipy.io.wavfile.read(path)
        if hasattr(data, "shape") and len(data.shape) > 1:
            data = data.mean(axis=1)
        if data.dtype != np.int16:
            data = (data.astype(np.float32) / np.iinfo(data.dtype).max * 32767).astype(np.int16)
        if sr != target_sr:
            num = int(len(data) * target_sr / sr)
            data = scipy.signal.resample(data.astype(np.float64), num).astype(np.int16)
        return data

    batch_size = 64
    n_feature_cols = F.get_embedding_shape(CLIP_SIZE_SEC)
    N_total = int(sum(negative_durations) // CLIP_SIZE_SEC)
    output_array_shape = (N_total, n_feature_cols[0], n_feature_cols[1])
    output_file = "negative_features.npy"
    fp = open_memmap(output_file, mode="w+", dtype=np.float32, shape=output_array_shape)

    row_counter = 0
    for i in tqdm(range(0, len(negative_clips), batch_size), desc="Negative features"):
        batch_paths = negative_clips[i : i + batch_size]
        wav_data = []
        for p in batch_paths:
            try:
                arr = _load_wav(p)
                wav_data.append(arr)
            except Exception:
                continue
        if not wav_data:
            continue
        wav_data = openwakeword.data.stack_clips(
            wav_data, clip_size=16000 * CLIP_SIZE_SEC
        ).astype(np.int16)
        features = F.embed_clips(x=wav_data, batch_size=1024, ncpu=8)
        if row_counter + features.shape[0] > N_total:
            n_write = N_total - row_counter
            fp[row_counter:N_total, :, :] = features[:n_write, :, :]
            row_counter = N_total
            fp.flush()
            break
        fp[row_counter : row_counter + features.shape[0], :, :] = features
        row_counter += features.shape[0]
        fp.flush()

    openwakeword.data.trim_mmap(output_file)
    print(f"  Saved {output_file}")


def _mix_clip_numpy(fg: np.ndarray, bg: np.ndarray, snr_db: float, start: int) -> np.ndarray:
    """Mix foreground into background at given SNR (numpy, no torch)."""
    fg = fg.astype(np.float64) / 32768
    bg = bg.astype(np.float64).copy() / 32768
    fg_rms = np.sqrt(np.mean(fg**2)) + 1e-8
    bg_rms = np.sqrt(np.mean(bg**2)) + 1e-8
    snr_lin = 10 ** (snr_db / 20)
    scale = snr_lin * bg_rms / fg_rms
    end = min(start + len(fg), len(bg))
    fg_len = end - start
    bg[start:end] = bg[start:end] + scale * fg[:fg_len]
    return (bg / 2 * 32767).astype(np.int16)


def _compute_positive_features(positive_clips: list[str], positive_durations: list[float]):
    """Compute positive embeddings (mixed with background) and save."""
    import openwakeword.data
    import openwakeword.utils

    os.chdir(TRAINING_DATA)
    F = openwakeword.utils.AudioFeatures()

    neg_dirs = [
        str(TRAINING_DATA / "fma_sample"),
        str(TRAINING_DATA / "fsd50k_sample"),
        str(TRAINING_DATA / "cv11_test_clips"),
    ]
    negative_clips, _ = openwakeword.data.filter_audio_paths(
        neg_dirs,
        min_length_secs=1.0,
        max_length_secs=60 * 30,
        duration_method="header",
    )

    sr = 16000
    total_length = int(sr * CLIP_SIZE_SEC)
    jitters = (np.random.uniform(0, 0.2, len(positive_clips)) * sr).astype(np.int32)
    starts = [
        total_length - (int(np.ceil(d * sr)) + int(j))
        for d, j in zip(positive_durations, jitters)
    ]

    def _load_wav(path, target_sr=16000):
        import scipy.io.wavfile
        import scipy.signal
        s, data = scipy.io.wavfile.read(path)
        if hasattr(data, "shape") and len(data.shape) > 1:
            data = data.mean(axis=1)
        if data.dtype != np.int16:
            data = (data.astype(np.float32) / np.iinfo(data.dtype).max * 32767).astype(np.int16)
        if s != target_sr:
            num = int(len(data) * target_sr / s)
            data = scipy.signal.resample(data.astype(np.float64), num).astype(np.int16)
        return data

    N_total = len(positive_clips)
    n_feature_cols = F.get_embedding_shape(CLIP_SIZE_SEC)
    output_file = "gerty_features.npy"
    output_array_shape = (N_total, n_feature_cols[0], n_feature_cols[1])
    fp = open_memmap(output_file, mode="w+", dtype=np.float32, shape=output_array_shape)

    batch_size = 8
    row_counter = 0
    for batch_start in tqdm(range(0, N_total, batch_size), desc="Positive features"):
        batch_clips = []
        for idx in range(batch_start, min(batch_start + batch_size, N_total)):
            try:
                fg = _load_wav(positive_clips[idx])
                bg_path = negative_clips[np.random.randint(len(negative_clips))]
                bg = _load_wav(bg_path)
                start = max(0, min(starts[idx], len(bg) - len(fg)))
                if len(bg) < total_length:
                    bg = np.tile(bg, (total_length // len(bg) + 1))[:total_length]
                else:
                    r = np.random.randint(0, max(1, len(bg) - total_length))
                    bg = bg[r : r + total_length]
                snr = np.random.uniform(5, 15)
                mixed = _mix_clip_numpy(fg, bg, snr, start)
                if len(mixed) < total_length:
                    mixed = np.pad(mixed, (0, total_length - len(mixed)))
                else:
                    mixed = mixed[:total_length]
                vol = np.random.uniform(0.02, 1.0)
                mixed = (mixed.astype(np.float64) * vol / (np.abs(mixed).max() + 1e-8) * 32767).astype(np.int16)
                batch_clips.append(mixed)
            except Exception:
                continue
        if not batch_clips:
            continue
        batch_arr = np.stack(batch_clips)
        features = F.embed_clips(batch_arr, batch_size=256)
        n = features.shape[0]
        fp[row_counter : row_counter + n, :, :] = features
        row_counter += n
        fp.flush()
        if row_counter >= N_total:
            break

    openwakeword.data.trim_mmap(output_file)
    print(f"  Saved {output_file}")


def _train_and_export():
    """Train classifier and export to ONNX."""
    import torch
    from torch import nn

    os.chdir(TRAINING_DATA)

    negative_features = np.load("negative_features.npy")
    positive_features = np.load("gerty_features.npy")

    X = np.vstack((negative_features, positive_features))
    y = np.array([0] * len(negative_features) + [1] * len(positive_features)).astype(
        np.float32
    )[..., None]

    batch_size = 512
    training_data = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(torch.from_numpy(X), torch.from_numpy(y)),
        batch_size=batch_size,
        shuffle=True,
    )

    layer_dim = 32
    fcn = nn.Sequential(
        nn.Flatten(),
        nn.Linear(X.shape[1] * X.shape[2], layer_dim),
        nn.LayerNorm(layer_dim),
        nn.ReLU(),
        nn.Linear(layer_dim, layer_dim),
        nn.LayerNorm(layer_dim),
        nn.ReLU(),
        nn.Linear(layer_dim, 1),
        nn.Sigmoid(),
    )

    loss_fn = torch.nn.functional.binary_cross_entropy
    optimizer = torch.optim.Adam(fcn.parameters(), lr=0.001)

    n_epochs = 10
    history = collections.defaultdict(list)
    for i in tqdm(range(n_epochs), desc="Training"):
        for batch in training_data:
            x, y_b = batch[0], batch[1]
            weights = torch.ones(y_b.shape[0])
            weights[y_b.flatten() == 1] = 0.1
            optimizer.zero_grad()
            predictions = fcn(x)
            loss = loss_fn(predictions, y_b, weights[..., None])
            loss.backward()
            optimizer.step()
            history["loss"].append(float(loss.detach().numpy()))
            tp = (predictions.flatten()[y_b.flatten() == 1] >= 0.5).sum()
            fn = (predictions.flatten()[y_b.flatten() == 1] < 0.5).sum()
            denom = tp + fn
            if denom > 0:
                history["recall"].append(float((tp / denom).detach().numpy()))

    # Export
    torch.onnx.export(
        fcn,
        torch.zeros((1, X.shape[1], X.shape[2])),
        str(TRAINING_DATA / "gerty.onnx"),
    )
    # Copy to final location
    import shutil
    shutil.copy(TRAINING_DATA / "gerty.onnx", OUTPUT_ONNX)
    print(f"\nModel saved to {OUTPUT_ONNX}")


def main():
    _ensure_deps()
    print("Gerty wake word local training")
    print("=" * 50)

    if not GERTY_SYNTHETIC.exists():
        print(f"Error: {GERTY_SYNTHETIC} not found.")
        print("Run: python3 scripts/generate_synthetic_gerty.py --count 500")
        sys.exit(1)

    # 1. Get positive clips (synthetic + first 80 user)
    print("\n1. Preparing positive clips...")
    positive_clips, positive_durations = _get_positive_clips()

    # 2. Download negatives
    print("\n2. Downloading negative data...")
    _download_negatives()

    # 3. Compute negative features
    print("\n3. Computing negative features...")
    _compute_negative_features()

    # 4. Compute positive features
    print("\n4. Computing positive features...")
    _compute_positive_features(positive_clips, positive_durations)

    # 5. Train and export
    print("\n5. Training and exporting...")
    _train_and_export()

    print("\nDone. Test with: python3 scripts/test_wake_score.py")


if __name__ == "__main__":
    main()
