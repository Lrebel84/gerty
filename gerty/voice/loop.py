"""Voice loop: wake word -> record -> STT -> router -> TTS -> play."""

import threading
import time

from gerty.config import PICOVOICE_ACCESS_KEY, VOSK_MODEL_PATH, PIPER_VOICE_PATH


def run_voice_loop(
    router_callback,
    on_exchange=None,
    on_status_change=None,
):
    """
    Run voice loop in current thread. Blocks.
    on_exchange(user_msg, assistant_msg) called when we have a full exchange.
    on_status_change("idle"|"listening"|"processing") called for UI updates.
    """
    if not PICOVOICE_ACCESS_KEY:
        return
    try:
        from gerty.voice.wake_word import WakeWordDetector
        from gerty.voice.audio import AudioCapture, AudioPlayback
        from gerty.voice.stt import SpeechToText
        from gerty.voice.tts import TextToSpeech
    except ImportError as e:
        return

    if not VOSK_MODEL_PATH.exists():
        return
    onnx = PIPER_VOICE_PATH if PIPER_VOICE_PATH.suffix == ".onnx" else PIPER_VOICE_PATH.with_suffix(".onnx")
    if not onnx.exists() and not any(PIPER_VOICE_PATH.parent.glob("*.onnx")):
        return

    wake = WakeWordDetector(keyword="computer")
    stt = SpeechToText()
    tts = TextToSpeech()
    capture = AudioCapture(sample_rate=wake.sample_rate, block_size=wake.frame_length)

    silence_frames = 0
    SILENCE_THRESHOLD = 30  # frames of silence to stop recording
    recording = False
    audio_chunks = []
    capture.start()

    def _status(s: str):
        if on_status_change:
            try:
                on_status_change(s)
            except Exception:
                pass

    def on_wake():
        nonlocal recording, audio_chunks, silence_frames
        recording = True
        audio_chunks = []
        silence_frames = 0
        _status("listening")

    while True:
        try:
            pcm = capture.read()
            if wake.process_frame(pcm):
                on_wake()
            elif recording:
                audio_chunks.append(pcm)
                # Simple silence detection: check if frame is mostly quiet
                import numpy as np
                arr = np.frombuffer(pcm, dtype=np.int16)
                if np.abs(arr).mean() < 500:
                    silence_frames += 1
                else:
                    silence_frames = 0
                if silence_frames >= SILENCE_THRESHOLD and len(audio_chunks) > 10:
                    recording = False
                    _status("processing")
                    # Vosk transcribe_stream expects raw PCM chunks
                    text = stt.transcribe_stream(audio_chunks, wake.sample_rate)
                    if text:
                        reply = router_callback(text)
                        if on_exchange:
                            on_exchange(text, reply)
                        # TTS
                        try:
                            audio = tts.synthesize(reply)
                            AudioPlayback.play(audio, tts.get_sample_rate())
                        except Exception:
                            pass
                    _status("idle")
        except Exception:
            if recording:
                recording = False
                _status("idle")
            time.sleep(0.01)


def start_voice_loop_thread(router_callback, on_exchange=None, on_status_change=None):
    """Start voice loop in a daemon thread."""
    t = threading.Thread(
        target=run_voice_loop,
        args=(router_callback, on_exchange, on_status_change),
        daemon=True,
    )
    t.start()
    return t
