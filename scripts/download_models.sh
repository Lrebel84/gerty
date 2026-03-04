#!/bin/bash
# Download Vosk and Piper models for Gerty
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODELS_DIR="$PROJECT_ROOT/models"
VOSK_DIR="$MODELS_DIR/vosk"
PIPER_DIR="$MODELS_DIR/piper"

mkdir -p "$VOSK_DIR" "$PIPER_DIR"

# Vosk small English model
VOSK_MODEL="vosk-model-small-en-us-0.22"
if [ ! -d "$VOSK_DIR/$VOSK_MODEL" ]; then
  echo "Downloading Vosk model..."
  curl -L "https://alphacephei.com/vosk/models/$VOSK_MODEL.zip" -o /tmp/vosk.zip
  unzip -o /tmp/vosk.zip -d "$VOSK_DIR"
  rm /tmp/vosk.zip
  echo "Vosk model installed."
else
  echo "Vosk model already exists."
fi

# Piper voice (en_US-amy-medium)
PIPER_VOICE="en_US-amy-medium"
if [ ! -f "$PIPER_DIR/$PIPER_VOICE.onnx" ]; then
  echo "Downloading Piper voice..."
  curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/$PIPER_VOICE.onnx" -o "$PIPER_DIR/$PIPER_VOICE.onnx"
  curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/$PIPER_VOICE.onnx.json" -o "$PIPER_DIR/$PIPER_VOICE.onnx.json"
  echo "Piper voice installed."
else
  echo "Piper voice already exists."
fi

echo "Models ready."
