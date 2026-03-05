"""Voice loop: wake word or push-to-talk -> record -> STT -> router -> TTS -> play."""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from gerty.config import (
    GROQ_API_KEY,
    PIPER_VOICE_PATH,
    STT_BACKEND,
    VAD_MIN_SILENCE_MS,
    VOSK_MODEL_PATH,
    VOICE_RESPONSE_TIMEOUT,
)
from gerty.settings import load as load_settings
from gerty.voice.wake_word import (
    create_wake_detector,
    consume_ptt_request,
    is_ptt_stop_requested,
    clear_ptt_stop,
)

logger = logging.getLogger(__name__)

# Silero VAD: 512 samples at 16kHz (32ms chunks)
PTT_FRAME_LENGTH = 512
PTT_SAMPLE_RATE = 16000

# Minimum chunks before VAD end is considered (avoid false triggers on brief noise)
# ~0.5s of speech = 512 * 16 = 8192 samples = 16 chunks at 512
MIN_SPEECH_CHUNKS = 16
# Minimum chunks before processing (ensure enough audio for useful transcription)
# ~1s = 32 chunks
MIN_RECORDING_CHUNKS = 32
# STT timeout (faster-whisper can hang in PyWebView; fallback to Vosk on timeout)
STT_TIMEOUT_SEC = 20
# Read timeout: must exceed block duration (1280 samples @ 16kHz = 80ms) to get audio
CAPTURE_READ_TIMEOUT_SEC = 0.15


def _stt_available() -> bool:
    """Check if any STT backend is available (Vosk, faster-whisper, or Groq)."""
    if VOSK_MODEL_PATH.exists():
        return True
    if GROQ_API_KEY:
        return True
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        pass
    return False


def run_voice_loop(
    router_callback,
    on_exchange=None,
    on_status_change=None,
):
    """
    Run voice loop in current thread. Blocks.
    Works with: Porcupine (if PICOVOICE_ACCESS_KEY), OpenWakeWord (local), or push-to-talk only.
    Single-click: VAD auto-detects end of speech; manual click optional to stop early.
    on_exchange(user_msg, assistant_msg) called when we have a full exchange.
    on_status_change("idle"|"listening"|"processing") called for UI updates.
    """
    try:
        from gerty.voice.audio import AudioCapture, AudioPlayback
        from gerty.voice.stt import SpeechToText
        from gerty.voice.tts import TextToSpeech
        from gerty.voice.vad import VADDetector
    except ImportError as e:
        logger.debug("Voice imports failed: %s", e)
        return

    if not _stt_available():
        logger.debug("No STT backend available (Vosk, faster-whisper, or Groq)")
        return
    onnx = PIPER_VOICE_PATH if PIPER_VOICE_PATH.suffix == ".onnx" else PIPER_VOICE_PATH.with_suffix(".onnx")
    if not onnx.exists() and not any(PIPER_VOICE_PATH.parent.glob("*.onnx")):
        logger.debug("Piper voice not found at %s", PIPER_VOICE_PATH)
        return

    wake, mode = create_wake_detector()
    if wake:
        sample_rate = wake.sample_rate
        frame_length = wake.frame_length
        logger.info("Voice: using %s wake word", mode)
    else:
        sample_rate = PTT_SAMPLE_RATE
        frame_length = PTT_FRAME_LENGTH
        logger.info("Voice: push-to-talk (click mic once—I detect when you stop)")

    settings = load_settings()
    backend = settings.get("stt_backend") or STT_BACKEND or "faster_whisper"
    faster_whisper_model = settings.get("faster_whisper_model")
    stt = SpeechToText(backend=backend, faster_whisper_model=faster_whisper_model)
    logger.info(
        "Voice: STT=%s, faster_whisper_model=%s, local_model=%s",
        backend,
        faster_whisper_model or "default",
        settings.get("local_model") or "(default)",
    )
    tts = TextToSpeech()
    capture = AudioCapture(sample_rate=sample_rate, block_size=frame_length)

    vad = None
    try:
        vad = VADDetector(min_silence_duration_ms=VAD_MIN_SILENCE_MS)
        vad._ensure_loaded()
    except Exception as e:
        vad = None  # Must set None so on_wake() doesn't call vad.reset() and re-raise
        logger.debug("Silero VAD not available, using energy-based fallback: %s", e)

    recording = False
    audio_chunks = []
    capture.start()

    def _status(s: str):
        if on_status_change:
            try:
                on_status_change(s)
            except Exception as e:
                logger.debug("Voice status callback failed: %s", e)

    def on_wake():
        nonlocal recording, audio_chunks
        recording = True
        audio_chunks = []
        _status("listening")
        if vad:
            vad.reset()

    def process_recording():
        nonlocal recording, audio_chunks
        if not audio_chunks or len(audio_chunks) < MIN_RECORDING_CHUNKS:
            _status("idle")
            recording = False
            audio_chunks = []
            return
        _status("processing")
        try:
            t0 = time.perf_counter()
            text = ""
            stt_to_use = stt
            for attempt in range(2):
                def _transcribe():
                    return stt_to_use.transcribe_stream(audio_chunks, sample_rate)

                with ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(_transcribe)
                    try:
                        text = future.result(timeout=STT_TIMEOUT_SEC)
                        break
                    except FuturesTimeoutError:
                        logger.warning("STT timed out after %ds (backend=%s)", STT_TIMEOUT_SEC, type(stt_to_use).__name__)
                        if attempt == 1 or not VOSK_MODEL_PATH.exists():
                            text = ""
                            break
                        logger.info("Voice: falling back to Vosk")
                        stt_to_use = SpeechToText(backend="vosk")
                    except Exception as e:
                        logger.warning("STT failed: %s", e)
                        if attempt == 1 or not VOSK_MODEL_PATH.exists():
                            break
                        logger.info("Voice: falling back to Vosk")
                        stt_to_use = SpeechToText(backend="vosk")
            t_stt = time.perf_counter() - t0
            logger.info("Voice: STT %.2fs | %r", t_stt, (text[:60] + "..." if text and len(text) > 60 else text))
            if text:
                t1 = time.perf_counter()
                with ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(router_callback, text)
                    try:
                        reply = future.result(timeout=VOICE_RESPONSE_TIMEOUT)
                    except FuturesTimeoutError:
                        reply = "That took too long. Please try again or ask something simpler."
                        logger.warning("Voice response timed out after %ds", VOICE_RESPONSE_TIMEOUT)
                t_llm = time.perf_counter() - t1
                logger.info("Voice: LLM %.2fs | reply %d chars", t_llm, len(reply))
                if on_exchange:
                    on_exchange(text, reply)
                try:
                    t2 = time.perf_counter()
                    audio = tts.synthesize(reply)
                    AudioPlayback.play(audio, tts.get_sample_rate())
                    t_tts = time.perf_counter() - t2
                    logger.info("Voice: TTS %.2fs | total %.2fs", t_tts, time.perf_counter() - t0)
                except Exception as e:
                    logger.debug("TTS playback failed: %s", e)
            else:
                # Empty transcription - give user feedback
                fallback = "I didn't catch that. Try speaking again."
                if on_exchange:
                    on_exchange("", fallback)
                try:
                    audio = tts.synthesize(fallback)
                    AudioPlayback.play(audio, tts.get_sample_rate())
                except Exception as e:
                    logger.debug("TTS playback failed: %s", e)
        except Exception as e:
            logger.warning("Voice processing failed: %s", e)
        finally:
            _status("idle")
            recording = False
            audio_chunks = []

    def check_energy_fallback() -> bool:
        """Energy-based fallback when Silero VAD unavailable."""
        import numpy as np

        if len(audio_chunks) < MIN_SPEECH_CHUNKS:
            return False
        # Use VAD_MIN_SILENCE_MS; chunk duration = frame_length/sample_rate
        ms_per_chunk = 1000 * frame_length / sample_rate
        SILENCE_THRESHOLD = max(20, int(VAD_MIN_SILENCE_MS / ms_per_chunk))
        # 1200 tolerates ambient room noise (was 800; higher = stop sooner with background sound)
        SILENCE_ENERGY = 1200
        silence_frames = 0
        for chunk in audio_chunks[-SILENCE_THRESHOLD:]:
            arr = np.frombuffer(chunk, dtype=np.int16)
            if np.abs(arr).mean() < SILENCE_ENERGY:
                silence_frames += 1
            else:
                silence_frames = 0
        return silence_frames >= SILENCE_THRESHOLD

    while True:
        try:
            # Use timeout so we can check stop request when mic blocks (PyWebView/Qt can block sounddevice)
            pcm = None
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(capture.read)
                try:
                    pcm = future.result(timeout=CAPTURE_READ_TIMEOUT_SEC)
                except FuturesTimeoutError:
                    if recording and is_ptt_stop_requested():
                        clear_ptt_stop()
                        process_recording()
                    elif consume_ptt_request():
                        on_wake()
                    continue
            wake_detected = bool(wake and wake.process_frame(pcm))
            ptt_start = consume_ptt_request()

            if wake_detected or ptt_start:
                on_wake()
            elif recording:
                if is_ptt_stop_requested():
                    clear_ptt_stop()
                    process_recording()
                    continue
                audio_chunks.append(pcm)
                end_detected = False
                if vad:
                    try:
                        # Silero VAD: feed each 512-sample chunk (1024 bytes) in sequence
                        chunk_bytes = 512 * 2  # 512 samples, 16-bit
                        for i in range(0, len(pcm), chunk_bytes):
                            part = pcm[i : i + chunk_bytes]
                            if len(part) == chunk_bytes and vad.process_chunk(part):
                                end_detected = True
                                break
                    except Exception as vad_err:
                        logger.debug("VAD chunk failed: %s", vad_err)
                if not end_detected:
                    end_detected = check_energy_fallback()
                if end_detected and len(audio_chunks) >= max(MIN_SPEECH_CHUNKS, MIN_RECORDING_CHUNKS):
                    process_recording()
        except Exception as e:
            logger.debug("Voice loop iteration: %s", e)
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
