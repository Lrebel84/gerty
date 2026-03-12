# Gerty Wake Word (openWakeWord - Your Voice)

Train a custom "Gerty" wake word on your own voice. Fully local, no API.

## 1. Record samples

```bash
python scripts/record_gerty_samples.py --count 80
```

Say "Gerty" clearly in each recording. Aim for 50-100+ samples. Vary conditions:
- Quiet room
- With background (music, TV low)
- Different distances from mic
- Different emphasis

Output: `models/wakeword/gerty_samples/gerty_0001.wav`, etc.

## 2. Train model

```bash
pip install openwakeword scipy torch tqdm onnxscript  # if not already installed
python3 scripts/train_gerty_wakeword.py
```

The script uses the start of your recordings (before you say "Gerty") as negative examples—no external datasets needed.

Output: `models/wakeword/gerty.onnx`

## 3. Use it

Restart Gerty. The voice loop will automatically use your custom model.

## Tips

- **More samples = better**: 80+ is good, 150+ is better
- **Variety**: Record in different rooms, with/without noise
- **Clarity**: Speak naturally; don't over-enunciate
- If the model has many false activations, record more samples and retrain with more negative data
