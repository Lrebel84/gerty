#!/usr/bin/env python3
"""Train a custom 'Gerty' wake word model on your recorded voice samples.

Requires: pip install openwakeword scipy torch tqdm onnxscript

Usage:
    1. Record Gerty: python3 scripts/record_gerty_samples.py --count 80
    2. Record background: python3 scripts/record_background.py  (stay silent!)
    3. Train: python3 scripts/train_gerty_wakeword.py
    4. Model saved to models/wakeword/gerty.onnx
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from tqdm import tqdm


def _load_wav(path: str, sr: int = 16000):
    """Load WAV as int16 array, resample if needed."""
    import scipy.io.wavfile
    file_sr, dat = scipy.io.wavfile.read(path)
    if dat.dtype != np.int16:
        dat = (dat.astype(np.float32) * 32767).astype(np.int16)
    if len(dat.shape) > 1:
        dat = dat.mean(axis=1).astype(np.int16)
    if file_sr != sr:
        from scipy import signal
        num = int(len(dat) * sr / file_sr)
        dat = signal.resample(dat.astype(np.float32), num).astype(np.int16)
    return dat


def _filter_clips(paths: list, min_sec: float, max_sec: float, sr: int = 16000):
    """Return (path, duration_sec) for clips within length bounds."""
    import scipy.io.wavfile
    result = []
    for p in paths:
        try:
            sr_file, dat = scipy.io.wavfile.read(p)
            n = len(dat) if dat.ndim == 1 else len(dat) // dat.shape[1]
            dur = n / (sr_file if sr_file else sr)
            if min_sec <= dur <= max_sec:
                result.append((str(p), dur))
        except Exception:
            pass
    return result


def _stack_clips(arrays: list, clip_samples: int) -> np.ndarray:
    """Stack/clip arrays to fixed length. Returns (N, clip_samples) int16."""
    out = []
    for arr in arrays:
        arr = np.asarray(arr, dtype=np.int16)
        if arr.ndim > 1:
            arr = arr.mean(axis=1).astype(np.int16)
        if len(arr) >= clip_samples:
            # Take from end (wake word typically at end)
            out.append(arr[-clip_samples:])
        else:
            out.append(np.pad(arr, (0, clip_samples - len(arr))))
    return np.stack(out, axis=0)


def _mix_foreground_background(fg: np.ndarray, bg: np.ndarray, snr_db: float) -> np.ndarray:
    """Mix foreground (wake word) with background at given SNR. fg and bg are int16."""
    # Scale fg so its RMS is snr_db above bg's RMS
    rms_bg = np.sqrt(np.mean(bg.astype(np.float64) ** 2)) + 1e-8
    rms_fg = np.sqrt(np.mean(fg.astype(np.float64) ** 2)) + 1e-8
    scale = rms_bg / rms_fg * (10 ** (snr_db / 20))
    mixed = fg.astype(np.float64) * scale + bg.astype(np.float64)
    mixed = np.clip(mixed, -32768, 32767).astype(np.int16)
    return mixed


def main():
    positive_dir = PROJECT_ROOT / "models" / "wakeword" / "gerty_samples"
    if not positive_dir.exists():
        print(f"Error: {positive_dir} not found.")
        print("Run: python scripts/record_gerty_samples.py --count 50")
        sys.exit(1)

    positive_files = sorted(positive_dir.glob("*.wav"))
    if len(positive_files) < 20:
        print(f"Error: Need at least 20 samples, found {len(positive_files)}")
        print("Record more: python scripts/record_gerty_samples.py --count 50")
        sys.exit(1)

    try:
        import openwakeword.utils
        import scipy.io.wavfile
        import torch
        from torch import nn
    except ImportError as e:
        print("Error: Install training deps:")
        print("  pip install openwakeword scipy torch tqdm")
        print(f"  ({e})")
        sys.exit(1)

    sr = 16000
    clip_size = 3  # seconds
    total_length = int(sr * clip_size)

    print("Creating audio feature extractor...")
    F = openwakeword.utils.AudioFeatures()
    n_feature_cols = F.get_embedding_shape(clip_size)

    # Filter positive clips
    pos_filtered = _filter_clips(
        [str(p) for p in positive_files],
        min_sec=0.4,
        max_sec=2.0,
        sr=sr,
    )
    if len(pos_filtered) < 20:
        print(f"Error: Only {len(pos_filtered)} clips passed filter (need 20+)")
        print("Ensure WAV files are 16kHz, 16-bit. Record longer samples.")
        sys.exit(1)
    print(f"Positive clips: {len(pos_filtered)}")

    # Negative clips: YOUR room background (critical!), pre-Gerty, silence, noise
    print("Preparing negative examples...")
    neg_arrays = []
    # 1. YOUR recorded background - matches your mic + room (run record_background.py)
    bg_dir = PROJECT_ROOT / "models" / "wakeword" / "background_samples"
    if bg_dir.exists():
        for bg_file in sorted(bg_dir.glob("*.wav")):
            dat = _load_wav(str(bg_file), sr)
            # Slice into 3s chunks (with overlap for more samples)
            step = total_length // 2  # 50% overlap
            for start in range(0, max(1, len(dat) - total_length), step):
                chunk = dat[start : start + total_length]
                if len(chunk) == total_length:
                    neg_arrays.append(chunk)
        if neg_arrays:
            print(f"  Loaded {len(neg_arrays)} background chunks from {bg_dir}")
    else:
        print("  No background_samples/ - run: python3 scripts/record_background.py")
    # 2. Pre-Gerty (start of recordings - breath, silence before saying Gerty)
    for p, _ in pos_filtered[: min(100, len(pos_filtered))]:
        dat = _load_wav(p, sr)
        if len(dat) > 12000:  # 0.75s
            neg_arrays.append(dat[:12000])
    # 3. Pure silence
    n_silence = max(80, len(pos_filtered) * 2)
    for _ in range(n_silence):
        neg_arrays.append(np.zeros(total_length, dtype=np.int16))
    # 4. Random noise
    np.random.seed(42)
    for _ in range(n_silence):
        noise = np.random.randint(-500, 500, total_length).astype(np.int16)
        neg_arrays.append(noise)
    # 5. Pad with more segments if needed
    n_neg = max(500, len(pos_filtered) * 10)
    while len(neg_arrays) < n_neg:
        if neg_arrays:
            arr = neg_arrays[np.random.randint(0, len(neg_arrays))]
            if len(arr) > total_length:
                start = np.random.randint(0, len(arr) - total_length)
                neg_arrays.append(arr[start : start + total_length])
            elif len(arr) < total_length:
                neg_arrays.append(np.pad(arr, (0, total_length - len(arr))))
            else:
                neg_arrays.append(arr.copy())
        else:
            neg_arrays.append(np.zeros(total_length, dtype=np.int16))
    print(f"Negative segments: {len(neg_arrays)} (incl. silence + noise)")

    # Compute negative features
    print("Computing negative features...")
    neg_clips = _stack_clips(neg_arrays[: n_neg], total_length)
    negative_features = F.embed_clips(neg_clips, batch_size=256)
    negative_features = np.asarray(negative_features, dtype=np.float32)

    # Compute positive features (optionally mix with noise)
    print("Computing positive features...")
    pos_features_list = []
    for path, dur in tqdm(pos_filtered, desc="Positive"):
        fg = _load_wav(path, sr)
        if len(fg) < total_length:
            fg = np.pad(fg, (0, total_length - len(fg)))
        else:
            fg = fg[-total_length:]  # Wake word at end
        # Optionally mix with random negative for robustness
        if len(neg_arrays) > 0 and np.random.random() < 0.7:
            bg = neg_arrays[np.random.randint(0, len(neg_arrays))]
            if len(bg) > total_length:
                start = np.random.randint(0, len(bg) - total_length)
                bg = bg[start : start + total_length]
            elif len(bg) < total_length:
                bg = np.pad(bg, (0, total_length - len(bg)))
            # else len(bg)==total_length, use as is
            snr = np.random.uniform(5, 15)
            fg = _mix_foreground_background(fg, bg, snr)
        feats = F.embed_clips(fg[None, :], batch_size=1)
        pos_features_list.append(feats[0])
    positive_features = np.stack(pos_features_list, axis=0).astype(np.float32)

    # Train
    print("Training model...")
    X = np.vstack((negative_features, positive_features))
    y = np.array(
        [0.0] * len(negative_features) + [1.0] * len(positive_features),
        dtype=np.float32,
    )[..., None]

    n_pos = len(positive_features)
    n_neg = len(negative_features)
    pos_weight_val = n_neg / max(n_pos, 1)
    print(f"  Class balance: {n_neg} neg, {n_pos} pos (pos_weight={pos_weight_val:.1f})")

    batch_size = 256
    train_loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(
            torch.from_numpy(X),
            torch.from_numpy(y),
        ),
        batch_size=batch_size,
        shuffle=True,
    )

    layer_dim = 32
    fcn = nn.Sequential(
        nn.Flatten(),
        nn.Linear(int(np.prod(X.shape[1:])), layer_dim),
        nn.LayerNorm(layer_dim),
        nn.ReLU(),
        nn.Linear(layer_dim, layer_dim),
        nn.LayerNorm(layer_dim),
        nn.ReLU(),
        nn.Linear(layer_dim, 1),
        nn.Sigmoid(),
    )
    optimizer = torch.optim.Adam(fcn.parameters(), lr=0.001)

    n_epochs = 15
    X_t = torch.from_numpy(X.astype(np.float32))
    y_t = torch.from_numpy(y)
    for epoch in range(n_epochs):
        for x_b, y_b in train_loader:
            weights = torch.ones(y_b.shape[0])
            weights[y_b.flatten() == 1] = pos_weight_val
            weights = weights / weights.mean()
            optimizer.zero_grad()
            pred = fcn(x_b)
            loss = torch.nn.functional.binary_cross_entropy(
                pred, y_b, weight=weights[..., None]
            )
            loss.backward()
            optimizer.step()

        # Epoch diagnostics: accuracy on full dataset
        fcn.eval()
        with torch.no_grad():
            pred_all = fcn(X_t)
            pred_np = pred_all.numpy().flatten()
            y_np = y_t.numpy().flatten()
            pos_mask = y_np == 1
            neg_mask = y_np == 0
            pos_acc = (pred_np[pos_mask] > 0.5).mean() if pos_mask.any() else 0.0
            neg_acc = (pred_np[neg_mask] < 0.5).mean() if neg_mask.any() else 0.0
            pos_mean = pred_np[pos_mask].mean() if pos_mask.any() else 0.0
            neg_mean = pred_np[neg_mask].mean() if neg_mask.any() else 0.0
        fcn.train()
        print(
            f"  Epoch {epoch+1}/{n_epochs} loss={loss.item():.4f} "
            f"pos_acc={pos_acc:.2%} neg_acc={neg_acc:.2%} "
            f"pos_mean={pos_mean:.3f} neg_mean={neg_mean:.3f}"
        )

    # Export ONNX
    out_path = PROJECT_ROOT / "models" / "wakeword" / "gerty.onnx"
    fcn.eval()
    dummy = torch.from_numpy(X[:1].astype(np.float32))
    torch.onnx.export(
        fcn,
        dummy,
        str(out_path),
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
    )
    print(f"\nModel saved to {out_path}")
    print("Restart Gerty to use your custom 'Gerty' wake word.")


if __name__ == "__main__":
    main()
