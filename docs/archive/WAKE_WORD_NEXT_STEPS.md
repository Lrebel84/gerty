# Gerty Wake Word: Your Next Steps

You have 500 synthetic samples ready. Follow these steps to train and install your model.

---

## Step 1: Prepare the upload package (run locally)

```bash
cd /home/liam/gerty && source .venv/bin/activate && python3 scripts/prepare_training_upload.py
```

This creates `models/wakeword/training_data/gerty_synthetic.tar.gz` for Colab upload. It may also download the negative data zips (fma_sample, fsd50k_sample).

---

## Step 2: Open the training notebook in Colab

1. Go to: **https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/training_models.ipynb**
2. **File → Save a copy in Drive** (so you can edit)
3. **Runtime → Change runtime type → T4 GPU** (optional; speeds up training)

---

## Step 3: Install dependencies (first code cell)

In the first code cell, **uncomment** the pip line and run it:

```python
!pip install openwakeword speechbrain datasets scipy matplotlib
```

Run the cell (Shift+Enter). Wait for it to finish.

---

## Step 4: Upload your gerty_synthetic to Colab

1. In Colab’s left sidebar, click the **Files** icon (folder)
2. Click **Upload**
3. Upload `gerty_synthetic.tar.gz` from `models/wakeword/training_data/`
4. In a **new cell**, run:

```python
!tar -xzf gerty_synthetic.tar.gz
```

This extracts the `gerty_synthetic/` folder into Colab’s workspace.

---

## Step 5: Download negative data in Colab

Add and run this cell **before** the “Negative Clips” section:

```python
# Download negative data (music, noise)
!wget -q https://f002.backblazeb2.com/file/openwakeword-resources/data/fma_sample.zip -O fma_sample.zip
!wget -q https://f002.backblazeb2.com/file/openwakeword-resources/data/fsd50k_sample.zip -O fsd50k_sample.zip
!unzip -o fma_sample.zip
!unzip -o fsd50k_sample.zip
```

---

## Step 6: Edit the notebook for Gerty

Before running the positive-clips cells, change these strings:

| Find | Replace with |
|------|--------------|
| `"turn_on_the_office_lights"` | `"gerty_synthetic"` |
| `"turn_on_the_office_lights_features.npy"` | `"gerty_features.npy"` |
| `"turn_on_the_office_lights.onnx"` | `"gerty.onnx"` |
| `wakeword_model_paths=["turn_on_the_office_lights.onnx"]` | `wakeword_model_paths=["gerty.onnx"]` |

Use **Edit → Find and replace** (Ctrl+H) for each.

---

## Step 7: Run all cells in order

Run each cell from top to bottom. The Common Voice download may take a few minutes. Training usually takes 5–15 minutes.

---

## Step 8: Download your model

1. When training finishes, find `gerty.onnx` in the Colab file browser
2. Right-click → **Download**
3. Save it to: `/home/liam/gerty/models/wakeword/gerty.onnx` (replace the existing file)

---

## Step 9: Test in Gerty

```bash
cd /home/liam/gerty && source .venv/bin/activate && python3 scripts/test_wake_score.py
```

Say “Gerty” or “Gertie” and check that the score rises above the threshold. Then start Gerty and try the wake word in the app.

---

## Quick reference

| Step | Command / action |
|------|------------------|
| 1. Prepare | `python3 scripts/prepare_training_upload.py` |
| 2. Open | https://colab.research.google.com/github/dscripka/openWakeWord/blob/main/notebooks/training_models.ipynb |
| 3. Install | Uncomment `!pip install ...` and run |
| 4. Upload | Upload `gerty_synthetic.tar.gz`, run `!tar -xzf gerty_synthetic.tar.gz` |
| 5. Negatives | Run the wget/unzip cell |
| 6. Edit | Replace `turn_on_the_office_lights` → `gerty_synthetic`, etc. |
| 7. Run | Execute all cells |
| 8. Download | Save `gerty.onnx` to `models/wakeword/` |
| 9. Test | `python3 scripts/test_wake_score.py` |
