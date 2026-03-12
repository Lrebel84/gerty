# Gerty Wake Word Status

> **Update:** We have pivoted to the official openWakeWord **synthetic training** approach. See `docs/WAKE_WORD_SYNTHETIC_TRAINING.md` for the new workflow. The manual few-shot scripts are archived in `scripts/archive/`.

## What We're Trying To Do

Implement a **local, always-listening wake word** for the Gerty voice assistant:

- **Wake word:** "Gerty" – user says it to activate the mic without clicking
- **Fully local** – no cloud API, no API keys for wake detection
- **Custom-trained** – model trained on the user's own voice samples for accent/voice compatibility
- **Audio feedback** – ping when listening starts, ping when processing starts
- **Future:** voice-based security (recognise authorised user)

The system should:
1. Stay idle (low score) when there's background noise, silence, or other speech
2. Trigger (high score) only when the user says "Gerty"
3. Work with OpenRouter/Groq and other backends

---

## What Has Been Done

### 1. Picovoice (removed)
- Added Picovoice Porcupine for "Gerty" wake word
- **Problem:** Did not recognise user's voice/accent
- **Removed:** Switched to custom training approach

### 2. openWakeWord + Custom Training
- **Recording:** `scripts/record_gerty_samples.py` – records 16 kHz 16-bit WAV samples of user saying "Gerty"
- **Training:** `scripts/train_gerty_wakeword.py` – trains a small neural net on:
  - Positives: user's "Gerty" samples (80+)
  - Negatives: pre-Gerty audio, pure silence, random noise, user's recorded background
- **Model:** `models/wakeword/gerty.onnx` – binary classifier (Gerty vs not-Gerty)
- **Pipeline:** Uses openWakeWord's `AudioFeatures.embed_clips()` – Google speech embedding → 28×96 feature frames per 3s clip

### 3. Inference Approaches Tried

| Approach | Description | Result |
|---------|-------------|--------|
| **openWakeWord Model.predict()** | Streaming 80ms frames through openWakeWord's pipeline | Score stuck ~0.13 for everything, or jumped 0.13–0.95 randomly |
| **Inverse-frequency weighting** | Fixed class imbalance (positives up-weighted) | Model learned but streaming mismatch remained |
| **Silence + noise negatives** | Added pure silence and random noise to training | Helped offline; streaming still unstable |
| **User background recording** | `scripts/record_background.py` – record room tone as negative | Added to training; user reports no improvement |
| **GertyDetector (custom)** | 3s buffer + `embed_clips` + ONNX (matches training exactly) | Designed to fix streaming mismatch; user reports no change |

### 4. Current Implementation
- **`GertyDetector`** in `gerty/voice/wake_word.py`:
  - 3-second PCM ring buffer
  - Every 80ms: add frame, take last 3s, run `embed_clips`, run ONNX
  - Score smoothing (EMA α=0.3)
  - Confirm frames (3 consecutive above threshold to trigger)
- **Config:** `WAKE_WORD_THRESHOLD` (default 0.5), `WAKE_WORD_CONFIRM_FRAMES` (default 3)
- **Test script:** `scripts/test_wake_score.py` – live score monitor

### 5. Training Fixes Applied
- Inverse-frequency class weighting (positives up-weighted)
- Pure silence and random noise as negatives
- User's recorded background (`models/wakeword/background_samples/`) as negatives
- Training diagnostics (pos_acc, neg_acc, pos_mean, neg_mean per epoch)

---

## What The User Is Seeing (Not Working)

**Symptom:** The wake word score bar hovers between **0.3 and 0.95** with only subtle background noise. Saying "Gerty" has no discernible impact – the score does not reliably rise when the user speaks the wake word.

**Implications:**
- The model appears to output high scores for background/ambient audio
- The model does not appear to discriminate "Gerty" from non-Gerty
- Threshold tuning (0.2, 0.35, 0.5) does not help – background alone crosses threshold
- Wake word detection is effectively unusable

**Possible causes (hypotheses):**
1. **Environment mismatch** – User's mic/room produces embeddings very different from training data; model has not generalised
2. **Model capacity/architecture** – Simple 2-layer MLP may be insufficient for the task
3. **Embedding sensitivity** – Google speech embedding may be sensitive to room tone, fan, AC in ways that look "speech-like"
4. **Training data quality** – Positives or negatives may be mislabelled or insufficiently diverse
5. **Hardware/driver** – Mic gain, sample rate, or driver behaviour could alter the signal

---

## Key Files

| File | Purpose |
|------|---------|
| `scripts/record_gerty_samples.py` | Record "Gerty" samples |
| `scripts/record_background.py` | Record room background (stay silent) |
| `scripts/train_gerty_wakeword.py` | Train custom model |
| `scripts/test_wake_score.py` | Live score monitor |
| `gerty/voice/wake_word.py` | GertyDetector, OpenWakeWordDetector |
| `models/wakeword/gerty.onnx` | Trained model |
| `models/wakeword/gerty_samples/` | User's "Gerty" recordings |
| `models/wakeword/background_samples/` | User's room background |

---

## Next Steps (To Investigate)

1. **Verify training quality** – Run offline eval: feed Gerty samples vs background through `embed_clips` + ONNX; check if model separates them
2. **Compare environments** – Record a 3s clip of "idle" and a 3s clip of "Gerty" on user's machine; run both through the pipeline offline
3. **Alternative architectures** – Try larger model, different features, or different wake word framework
4. **Fallback** – Consider push-to-talk as primary until wake word is reliable
