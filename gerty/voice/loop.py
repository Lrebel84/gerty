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
    VOICE_TTS_PARALLEL,
    VOICE_WAKE_GRACE_SEC,
)
from gerty.settings import load as load_settings
from gerty.voice.feedback import play_listening_ping, play_processing_ping
from gerty.voice.wake_word import (
    create_wake_detector,
    consume_ptt_request,
    consume_voice_cancel,
    clear_ptt_stop,
    clear_voice_cancel,
    is_ptt_stop_requested,
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
# STT timeout (faster-whisper can hang in PyWebView; fallback to Vosk on timeout; 25s = fail faster)
STT_TIMEOUT_SEC = 25
# Read timeout: must exceed block duration (1280 samples @ 16kHz = 80ms) to get audio
CAPTURE_READ_TIMEOUT_SEC = 0.15
# Max recording: force process after this many seconds (prevents infinite recording if VAD never triggers)
MAX_RECORDING_SEC = 30


def _stt_available() -> bool:
    """Check if any STT backend is available (Vosk, faster-whisper, Moonshine, or Groq)."""
    if VOSK_MODEL_PATH.exists():
        return True
    if GROQ_API_KEY:
        return True
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        import transformers  # noqa: F401
        return True
    except ImportError:
        pass
    return False


def run_voice_loop(
    router_callback,
    on_exchange=None,
    on_status_change=None,
    *,
    on_user_text=None,
    on_assistant_content=None,
    stream_router_callback=None,
):
    """
    Run voice loop in current thread. Blocks.
    Works with: Porcupine (if PICOVOICE_ACCESS_KEY), OpenWakeWord (local), or push-to-talk only.
    Single-click: VAD auto-detects end of speech; manual click optional to stop early.
    on_exchange(user_msg, assistant_msg) called when we have a full exchange (legacy).
    on_user_text(text) called when STT completes – show user message immediately.
    on_assistant_content(content) called as LLM streams – update assistant message.
    stream_router_callback(msg) yields chunks; if provided, enables streaming TTS (sentence-by-sentence).
    on_status_change("idle"|"listening"|"processing") called for UI updates.
    """
    try:
        from gerty.voice.audio import (
    AudioCapture,
    AudioPlayback,
    drain_play_queue,
    play_queued,
    prepare_play_queue,
    put_play_end,
    stop_playback,
)
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
    moonshine_model = settings.get("moonshine_model")
    stt = SpeechToText(
        backend=backend,
        faster_whisper_model=faster_whisper_model,
        moonshine_model=moonshine_model,
    )
    logger.info(
        "Voice: STT=%s, model=%s, provider=%s",
        backend,
        (moonshine_model if backend == "moonshine" else faster_whisper_model) or "default",
        settings.get("provider", "local"),
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
    recording_started_at: float | None = None
    capture.start()

    # Signal that voice is active and listening for wake word (or PTT)
    def _status(s: str):
        if on_status_change:
            try:
                on_status_change(s)
            except Exception as e:
                logger.debug("Voice status callback failed: %s", e)

    _status("idle")  # Voice ready, listening for wake word (or PTT)

    def on_wake():
        nonlocal recording, audio_chunks, recording_started_at
        clear_voice_cancel()  # Clear any stale cancel from previous run
        recording = True
        audio_chunks = []
        recording_started_at = time.perf_counter()
        _status("listening")
        play_listening_ping()
        if vad:
            vad.reset()

    def process_recording():
        nonlocal recording, audio_chunks, recording_started_at
        if not audio_chunks or len(audio_chunks) < MIN_RECORDING_CHUNKS:
            _status("idle")
            recording = False
            audio_chunks = []
            recording_started_at = None
            return
        _status("processing")
        play_processing_ping()
        if consume_voice_cancel():
            return
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
            if consume_voice_cancel():
                logger.info("Voice: cancelled after STT")
                return
            if text:
                if on_user_text:
                    try:
                        on_user_text(text)
                    except Exception as e:
                        logger.debug("on_user_text failed: %s", e)
                t1 = time.perf_counter()
                reply = ""
                if stream_router_callback and on_assistant_content:
                    import re
                    full_reply = ""
                    played_up_to = 0
                    sentence_end = re.compile(r"([^.!?\n]+[.!?\n]+)")
                    try:
                        if VOICE_TTS_PARALLEL:
                            prepare_play_queue()
                            def _producer():
                                nonlocal full_reply, reply
                                fp = ""
                                pp = 0
                                try:
                                    for chunk in stream_router_callback(text):
                                        if consume_voice_cancel():
                                            stop_playback()
                                            return
                                        fp += chunk
                                        on_assistant_content(fp)
                                        remainder = fp[pp:]
                                        while True:
                                            m = sentence_end.search(remainder)
                                            if not m:
                                                break
                                            sentence = m.group(1)
                                            pp += m.end()
                                            try:
                                                audio = tts.synthesize(sentence)
                                                if audio:
                                                    play_queued(audio, tts.get_sample_rate())
                                            except Exception as e:
                                                logger.debug("TTS chunk failed: %s", e)
                                            remainder = fp[pp:]
                                    remainder = fp[pp:]
                                    if remainder.strip():
                                        try:
                                            audio = tts.synthesize(remainder)
                                            if audio:
                                                play_queued(audio, tts.get_sample_rate())
                                        except Exception as e:
                                            logger.debug("TTS final chunk failed: %s", e)
                                    full_reply = fp
                                    reply = fp
                                except Exception as e:
                                    logger.warning("Streaming voice failed: %s", e)
                                    reply = ""
                                finally:
                                    put_play_end()

                            prod = threading.Thread(target=_producer)
                            prod.start()
                            drain_thread = threading.Thread(target=drain_play_queue)
                            drain_thread.start()
                            while drain_thread.is_alive():
                                if consume_voice_cancel():
                                    stop_playback()
                                    break
                                drain_thread.join(timeout=0.1)
                            drain_thread.join(timeout=1.0)
                            prod.join(timeout=2.0)
                        else:
                            for chunk in stream_router_callback(text):
                                if consume_voice_cancel():
                                    break
                                full_reply += chunk
                                on_assistant_content(full_reply)
                                remainder = full_reply[played_up_to:]
                                while True:
                                    m = sentence_end.search(remainder)
                                    if not m:
                                        break
                                    sentence = m.group(1)
                                    played_up_to += m.end()
                                    try:
                                        audio = tts.synthesize(sentence)
                                        if audio:
                                            AudioPlayback.play(audio, tts.get_sample_rate())
                                    except Exception as e:
                                        logger.debug("TTS chunk failed: %s", e)
                                    remainder = full_reply[played_up_to:]
                            remainder = full_reply[played_up_to:]
                            if remainder.strip():
                                try:
                                    audio = tts.synthesize(remainder)
                                    if audio:
                                        AudioPlayback.play(audio, tts.get_sample_rate())
                                except Exception as e:
                                    logger.debug("TTS final chunk failed: %s", e)
                            reply = full_reply
                    except Exception as e:
                        logger.warning("Streaming voice failed: %s", e)
                        reply = ""
                if not reply:
                    with ThreadPoolExecutor(max_workers=1) as ex:
                        future = ex.submit(router_callback, text)
                        try:
                            reply = future.result(timeout=VOICE_RESPONSE_TIMEOUT)
                        except FuturesTimeoutError:
                            reply = "That took too long. Please try again or ask something simpler."
                            logger.warning("Voice response timed out after %ds", VOICE_RESPONSE_TIMEOUT)
                    if on_assistant_content:
                        on_assistant_content(reply)
                    try:
                        audio = tts.synthesize(reply)
                        AudioPlayback.play(audio, tts.get_sample_rate())
                    except Exception as e:
                        logger.debug("TTS playback failed: %s", e)
                t_llm = time.perf_counter() - t1
                logger.info("Voice: LLM %.2fs | reply %d chars", t_llm, len(reply))
                if on_exchange and not (stream_router_callback and on_assistant_content):
                    on_exchange(text, reply)
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
            recording_started_at = None

    def check_energy_fallback() -> bool:
        """Energy-based fallback when Silero VAD unavailable."""
        import numpy as np

        if len(audio_chunks) < MIN_SPEECH_CHUNKS:
            return False
        # Use VAD_MIN_SILENCE_MS; chunk duration = frame_length/sample_rate
        # max(5,...) = min 5 chunks to avoid false triggers; was max(20,...) which forced ~1.6s with OpenWakeWord
        ms_per_chunk = 1000 * frame_length / sample_rate
        SILENCE_THRESHOLD = max(5, int(VAD_MIN_SILENCE_MS / ms_per_chunk))
        # 800 = more sensitive; 1200 was too high for some environments (never stopped)
        SILENCE_ENERGY = 800
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
                # Grace period: ignore end-of-speech for first N seconds after wake (gives time to start talking)
                elapsed = (time.perf_counter() - recording_started_at) if recording_started_at else 0
                if end_detected and elapsed < VOICE_WAKE_GRACE_SEC:
                    end_detected = False
                # Force process after MAX_RECORDING_SEC (VAD may never trigger in noisy environments)
                if recording_started_at and elapsed >= MAX_RECORDING_SEC:
                    end_detected = True
                    logger.info("Voice: max recording duration reached, forcing process")
                if end_detected and len(audio_chunks) >= max(MIN_SPEECH_CHUNKS, MIN_RECORDING_CHUNKS):
                    process_recording()
        except Exception as e:
            logger.debug("Voice loop iteration: %s", e)
            if recording:
                recording = False
                _status("idle")
            time.sleep(0.01)


def start_voice_loop_thread(
    router_callback,
    on_exchange=None,
    on_status_change=None,
    *,
    on_user_text=None,
    on_assistant_content=None,
    stream_router_callback=None,
):
    """Start voice loop in a daemon thread."""
    t = threading.Thread(
        target=run_voice_loop,
        args=(router_callback, on_exchange, on_status_change),
        kwargs={
            "on_user_text": on_user_text,
            "on_assistant_content": on_assistant_content,
            "stream_router_callback": stream_router_callback,
        },
        daemon=True,
    )
    t.start()
    return t
