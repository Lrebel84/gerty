# Gerty Wake Word: Official Synthetic Training Guide

We use the **official openWakeWord synthetic training pipeline** instead of manual few-shot recording. Synthetic training trains against thousands of hours of *other* human speech, music, and noise, so the model learns to detect "Gerty" specifically—not just "any human voice."

---

## Official Resources

| Resource | Link |
|----------|------|
| **Training notebook** | https://github.com/dscripka/openWakeWord/blob/main/notebooks/training_models.ipynb |
| **Open in Colab** | https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/training_models.ipynb |
| **Synthetic TTS repo** | https://github.com/dscripka/synthetic_speech_dataset_generation |
| **Pre-trained model docs** | https://github.com/dscripka/openWakeWord/tree/main/docs/models |

---

## Quick start (you have samples ready)

If you already ran `generate_synthetic_gerty.py` and have 500 samples, see **[WAKE_WORD_NEXT_STEPS.md](WAKE_WORD_NEXT_STEPS.md)** for the exact Colab steps.

---

## Step-by-Step: Generate a "Gerty" Model

### Step 1: Generate Synthetic "Gerty" Audio (Positives)

You need **thousands** of synthetic "gerty" clips (the notebook example uses ~3,400). Options:

#### Option A: Piper TTS (local, Gerty already has Piper)

```bash
# Generate 500 "gerty" samples with Piper (run from project root)
python3 scripts/generate_synthetic_gerty.py --count 500 --output models/wakeword/gerty_synthetic
```

Then repeat with different voices or settings to reach 3,000+ samples. See `scripts/generate_synthetic_gerty.py` for usage.

#### Option B: Coqui TTS / other TTS

Use [Coqui TTS](https://github.com/coqui-ai/TTS) or similar to generate "gerty" with multiple voices. Save as 16 kHz, 16-bit mono WAV in a folder (e.g. `gerty_synthetic/`).

#### Option C: synthetic_speech_dataset_generation repo

Clone https://github.com/dscripka/synthetic_speech_dataset_generation and follow its README to generate "gerty" with their TTS pipeline.

**Requirements for positive clips:**
- 16 kHz, 16-bit, mono WAV
- Duration: 1.0–2.0 seconds per clip
- Phrase: just "gerty" (or "Gerty")

---

### Step 2: Download Negative Data

The notebook uses three negative sources (music, noise, other speech):

| Dataset | Download | Extract to |
|---------|----------|------------|
| **FMA (music)** | https://f002.backblazeb2.com/file/openwakeword-resources/data/fma_sample.zip | `fma_sample/` |
| **FSD50k (noise)** | https://f002.backblazeb2.com/file/openwakeword-resources/data/fsd50k_sample.zip | `fsd50k_sample/` |
| **Common Voice 11 (speech)** | HuggingFace (notebook downloads automatically) | `cv11_test_clips/` |

Download and extract `fma_sample.zip` and `fsd50k_sample.zip` into your Colab working directory. The notebook will download Common Voice 11.

---

### Step 3: Open the Notebook in Colab

1. Go to: **https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/training_models.ipynb**
2. File → Save a copy in Drive (so you can edit)
3. Runtime → Change runtime type → GPU (optional, speeds up training)

---

### Step 4: Edit the Notebook for "Gerty"

Find and replace these values:

| What to change | Find | Replace with |
|----------------|------|--------------|
| Positive data folder | `"turn_on_the_office_lights"` | `"gerty_synthetic"` (or your folder name) |
| Positive filter max length | `max_length_secs = 2.0` | Keep 2.0 (clips 1–2 s) |
| Output feature file | `"turn_on_the_office_lights_features.npy"` | `"gerty_features.npy"` |
| Model output | `"turn_on_the_office_lights.onnx"` | `"gerty.onnx"` |
| openWakeWord model path | `wakeword_model_paths=["turn_on_the_office_lights.onnx"]` | `wakeword_model_paths=["gerty.onnx"]` |

**Upload your `gerty_synthetic/` folder** (or `gerty_synthetic.tar.gz`) to Colab before running the positive-data cells.

---

### Step 5: Run the Notebook

Execute cells in order:

1. **Install** – Uncomment and run the pip install cell
2. **Imports** – Run imports
3. **Download CV11** – Downloads Common Voice 11 (takes a few minutes)
4. **Negative clips** – Filter and compute negative embeddings
5. **Positive clips** – Point to `gerty_synthetic`, mix with background, compute features
6. **Train** – Train the classifier
7. **Export ONNX** – Export `gerty.onnx`
8. **Test** – Validate on a sample clip

---

### Step 6: Download and Install Your Model

1. From Colab: right-click `gerty.onnx` → Download
2. Save to: `gerty/models/wakeword/gerty.onnx`
3. Restart Gerty; it will use the new model

---

## Data Volume (Important)

The notebook uses **small samples** for a quick demo. For a robust model:

- **Positives:** 10,000+ synthetic "gerty" clips (multiple TTS voices, speeds, noise levels)
- **Negatives:** 30,000+ hours (music, noise, speech) – the pre-trained openWakeWord models use this scale

Start with the notebook’s smaller setup to verify the pipeline, then scale up for production.

---

## Verifier Model (Optional)

To reduce false accepts, the notebook shows how to train a **custom verifier** using a few reference clips of *your* voice saying "gerty" and *your* voice saying something else. This makes the system more user-specific. See the "Custom Verifier" section in the notebook.
