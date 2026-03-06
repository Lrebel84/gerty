#!/bin/bash
# Download Vosk and Piper models for Gerty
# faster-whisper models download on first use (Hugging Face)
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODELS_DIR="$PROJECT_ROOT/models"
VOSK_DIR="$MODELS_DIR/vosk"
PIPER_DIR="$MODELS_DIR/piper"
KOKORO_DIR="$MODELS_DIR/kokoro"

mkdir -p "$VOSK_DIR" "$PIPER_DIR" "$KOKORO_DIR"

# Vosk small English model (0.22 doesn't exist; 0.15 is the available small model)
VOSK_MODEL="vosk-model-small-en-us-0.15"
if [ ! -d "$VOSK_DIR/$VOSK_MODEL" ]; then
  echo "Downloading Vosk model (~40MB)..."
  if ! curl -L "https://alphacephei.com/vosk/models/$VOSK_MODEL.zip" -o /tmp/vosk.zip; then
    echo "Error: curl failed to download Vosk model"
    exit 1
  fi
  if ! unzip -t /tmp/vosk.zip >/dev/null 2>&1; then
    echo "Error: Downloaded file is not a valid zip. The model URL may have changed."
    echo "Check https://alphacephei.com/vosk/models for current links."
    rm -f /tmp/vosk.zip
    exit 1
  fi
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

# Kokoro-82M TTS (optional; ElevenLabs-like quality, ~80MB quantized)
if [ ! -f "$KOKORO_DIR/kokoro-v1.0.onnx" ]; then
  echo "Downloading Kokoro-82M TTS model..."
  if curl -L "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx" -o "$KOKORO_DIR/kokoro-v1.0.onnx" 2>/dev/null; then
    curl -L "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin" -o "$KOKORO_DIR/voices-v1.0.bin" 2>/dev/null || true
    echo "Kokoro TTS installed. Set TTS_BACKEND=kokoro in .env to use."
  else
    echo "Skip Kokoro (optional). pip install kokoro-onnx when ready."
  fi
else
  echo "Kokoro model already exists."
fi

# Optional: pull common Ollama models (requires ollama running)
if command -v ollama &>/dev/null; then
  echo "Pulling Ollama models (llama3.2, llama3.1:8b)..."
  ollama pull llama3.2 2>/dev/null || true
  ollama pull llama3.1:8b 2>/dev/null || true
  echo "Ollama models ready. Run 'ollama list' to see installed models."
fi

# Pre-download faster-whisper models: tiny for voice (fastest), base for balanced
if command -v python3 &>/dev/null; then
  echo "Pre-downloading faster-whisper models (tiny for voice, base for accuracy)..."
  if python3 -c "
from faster_whisper import WhisperModel
WhisperModel('tiny', device='cpu', compute_type='int8')
print('faster-whisper tiny ready.')
" 2>/dev/null; then
    python3 -c "
from faster_whisper import WhisperModel
WhisperModel('base', device='cpu', compute_type='int8')
print('faster-whisper base ready.')
" 2>/dev/null || true
  else
    echo "Skip faster-whisper (pip install faster-whisper to enable)"
  fi
fi

echo "Models ready."
