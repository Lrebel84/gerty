"""Shared state for sounding alarms: TTS repeat, voice loop integration."""

import logging
import threading
import time

logger = logging.getLogger(__name__)

# Currently sounding alarm: {"id", "time", "label", ...} or None
_sounding_alarm: dict | None = None
_lock = threading.Lock()
_stop_repeat = threading.Event()
_repeat_thread: threading.Thread | None = None

ALARM_REPEAT_INTERVAL_SEC = 30


def get_sounding_alarm() -> dict | None:
    """Return the currently sounding alarm, or None."""
    with _lock:
        return _sounding_alarm


def set_sounding_alarm(alarm: dict | None):
    """Set or clear the sounding alarm. Starts TTS repeat thread if alarm is set."""
    global _sounding_alarm, _repeat_thread
    with _lock:
        _stop_repeat.set()
        if _repeat_thread and _repeat_thread.is_alive():
            _repeat_thread.join(timeout=1.0)
        _sounding_alarm = alarm
        _stop_repeat.clear()
        if alarm:
            try:
                from gerty.voice.feedback import play_listening_ping
                play_listening_ping()
            except Exception as e:
                logger.debug("Alarm beep failed: %s", e)
            _repeat_thread = threading.Thread(target=_alarm_repeat_worker, args=(alarm,), daemon=True)
            _repeat_thread.start()


def stop_alarm_sounding():
    """Stop the sounding alarm. One-time: remove. Daily: reschedule to tomorrow."""
    from gerty.tools.alarms import cancel_alarm, reschedule_daily_alarm

    alarm = get_sounding_alarm()
    if alarm:
        aid = alarm.get("id") or alarm.get("datetime")
        if aid:
            if alarm.get("recurring") == "daily":
                reschedule_daily_alarm(aid)
            else:
                cancel_alarm(aid)
    set_sounding_alarm(None)


def _alarm_repeat_worker(alarm: dict):
    """Repeat TTS every 30s until stopped. Waits 30s before first repeat (notify speaks first)."""
    time_str = alarm.get("time", "alarm")
    msg = f"This is your {time_str} alarm, say cancel to stop"
    while not _stop_repeat.is_set():
        if _stop_repeat.wait(timeout=ALARM_REPEAT_INTERVAL_SEC):
            break
        try:
            from gerty.voice.tts import TextToSpeech
            from gerty.voice.audio import AudioPlayback

            tts = TextToSpeech()
            if tts.is_available():
                audio = tts.synthesize(msg)
                if audio:
                    AudioPlayback.play(audio, tts.get_sample_rate())
        except Exception as e:
            logger.debug("Alarm TTS failed: %s", e)
