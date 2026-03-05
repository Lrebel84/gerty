"""Notification service: TTS, system notify, Telegram."""

import logging
import subprocess
from typing import Literal

from gerty.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS

logger = logging.getLogger(__name__)

Channel = Literal["tts", "system", "telegram"]


def notify(message: str, channels: list[Channel] | None = None):
    """Send notification via specified channels. Default: system + tts."""
    channels = channels or ["system", "tts"]

    if "system" in channels:
        _system_notify(message)
    if "tts" in channels:
        _tts_speak(message)
    if "telegram" in channels and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_IDS:
        _telegram_send(message)


def _system_notify(message: str):
    """Send Linux desktop notification via notify-send."""
    try:
        subprocess.run(
            ["notify-send", "-a", "Gerty", message],
            capture_output=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.debug("System notify failed: %s", e)


def _tts_speak(message: str):
    """Speak message via Piper TTS."""
    try:
        from gerty.voice.tts import TextToSpeech
        from gerty.voice.audio import AudioPlayback

        tts = TextToSpeech()
        if tts.is_available():
            audio = tts.synthesize(message)
            AudioPlayback.play(audio, tts.get_sample_rate())
    except Exception as e:
        logger.debug("TTS failed: %s", e)


def _telegram_send(message: str):
    """Send message to authorized Telegram chats."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        return
    try:
        import httpx
        for chat_id in TELEGRAM_CHAT_IDS:
            httpx.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": chat_id, "text": f"Gerty: {message}"},
                timeout=10,
            )
    except Exception as e:
        logger.debug("Telegram send failed: %s", e)
