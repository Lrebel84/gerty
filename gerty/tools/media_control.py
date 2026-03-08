"""Media and audio control: playerctl for playback, wpctl/pamixer for volume/mute."""

import logging
import shutil
import subprocess

from gerty.tools.base import Tool

logger = logging.getLogger(__name__)

_TIMEOUT = 2

# Audio backend: "wpctl" (PipeWire) or "pamixer" (PulseAudio)
_audio_backend: str | None = None


def _get_audio_backend() -> str | None:
    """Detect wpctl (PipeWire) or pamixer (PulseAudio)."""
    global _audio_backend
    if _audio_backend is not None:
        return _audio_backend
    if shutil.which("wpctl"):
        _audio_backend = "wpctl"
    elif shutil.which("pamixer"):
        _audio_backend = "pamixer"
    else:
        _audio_backend = ""
    return _audio_backend if _audio_backend else None


def _playerctl(cmd: str) -> tuple[bool, str]:
    """Run playerctl command. Returns (success, message)."""
    if not shutil.which("playerctl"):
        return False, "playerctl not found. Install with: sudo apt install playerctl"
    try:
        result = subprocess.run(
            ["playerctl", cmd],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            shell=False,
        )
        if result.returncode == 0:
            return True, ""
        # No player running is common
        err = (result.stderr or "").strip()
        if "No players found" in err or "No player could handle" in err:
            return False, "No media player is running."
        return False, err or "Media command failed."
    except subprocess.TimeoutExpired:
        return False, "Media command timed out."
    except Exception as e:
        logger.debug("playerctl failed: %s", e)
        return False, str(e)


def _audio_mute_toggle() -> tuple[bool, str]:
    """Toggle mute using wpctl or pamixer."""
    backend = _get_audio_backend()
    if not backend:
        return False, "No audio control found. Install wpctl (PipeWire) or pamixer (PulseAudio)."
    try:
        if backend == "wpctl":
            result = subprocess.run(
                ["wpctl", "set-mute", "@DEFAULT_SINK@", "toggle"],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
                shell=False,
            )
        else:
            result = subprocess.run(
                ["pamixer", "-t"],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
                shell=False,
            )
        if result.returncode == 0:
            return True, ""
        return False, (result.stderr or "").strip() or "Audio command failed."
    except Exception as e:
        logger.debug("Audio mute failed: %s", e)
        return False, str(e)


def _audio_mute() -> tuple[bool, str]:
    """Mute audio."""
    backend = _get_audio_backend()
    if not backend:
        return False, "No audio control found."
    try:
        if backend == "wpctl":
            result = subprocess.run(
                ["wpctl", "set-mute", "@DEFAULT_SINK@", "1"],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
                shell=False,
            )
        else:
            result = subprocess.run(
                ["pamixer", "-m"],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
                shell=False,
            )
        return result.returncode == 0, (result.stderr or "").strip() or ""
    except Exception as e:
        return False, str(e)


def _audio_unmute() -> tuple[bool, str]:
    """Unmute audio."""
    backend = _get_audio_backend()
    if not backend:
        return False, "No audio control found."
    try:
        if backend == "wpctl":
            result = subprocess.run(
                ["wpctl", "set-mute", "@DEFAULT_SINK@", "0"],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
                shell=False,
            )
        else:
            result = subprocess.run(
                ["pamixer", "-u"],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
                shell=False,
            )
        return result.returncode == 0, (result.stderr or "").strip() or ""
    except Exception as e:
        return False, str(e)


def _audio_volume_up() -> tuple[bool, str]:
    """Increase volume by 10%."""
    backend = _get_audio_backend()
    if not backend:
        return False, "No audio control found."
    try:
        if backend == "wpctl":
            result = subprocess.run(
                ["wpctl", "set-volume", "@DEFAULT_SINK@", "10%+"],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
                shell=False,
            )
        else:
            result = subprocess.run(
                ["pamixer", "-i", "10"],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
                shell=False,
            )
        return result.returncode == 0, (result.stderr or "").strip() or ""
    except Exception as e:
        return False, str(e)


def _audio_volume_down() -> tuple[bool, str]:
    """Decrease volume by 10%."""
    backend = _get_audio_backend()
    if not backend:
        return False, "No audio control found."
    try:
        if backend == "wpctl":
            result = subprocess.run(
                ["wpctl", "set-volume", "@DEFAULT_SINK@", "10%-"],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
                shell=False,
            )
        else:
            result = subprocess.run(
                ["pamixer", "-d", "10"],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
                shell=False,
            )
        return result.returncode == 0, (result.stderr or "").strip() or ""
    except Exception as e:
        return False, str(e)


def _classify_media_intent(message: str) -> str | None:
    """Map message to media/audio sub-intent."""
    lower = message.lower().strip()
    # Audio
    if any(kw in lower for kw in ["mute", "unmute audio", "turn off sound"]):
        if "unmute" in lower or "un mute" in lower:
            return "audio_unmute"
        return "audio_mute"
    if any(kw in lower for kw in ["volume up", "turn up", "louder", "increase volume"]):
        return "audio_volume_up"
    if any(kw in lower for kw in ["volume down", "turn down", "quieter", "decrease volume"]):
        return "audio_volume_down"
    # Media
    if any(kw in lower for kw in ["next track", "next song", "skip", "skip track"]):
        return "media_next"
    if any(kw in lower for kw in ["previous track", "previous song", "last song", "go back"]):
        return "media_prev"
    if any(kw in lower for kw in ["pause", "pause music", "pause playback"]):
        return "media_pause"
    if any(kw in lower for kw in ["play", "play music", "resume"]):
        return "media_play"
    if "play" in lower or "pause" in lower:
        return "media_play_pause"
    if "stop" in lower and ("music" in lower or "playback" in lower):
        return "media_stop"
    return None


class MediaControlTool(Tool):
    """Control media playback (playerctl) and system audio (wpctl/pamixer)."""

    @property
    def name(self) -> str:
        return "media_control"

    @property
    def description(self) -> str:
        return "Play, pause, skip, mute, volume"

    def execute(self, intent: str, message: str) -> str:
        resolved = _classify_media_intent(message)
        if not resolved:
            return "I can play, pause, skip tracks, mute, or adjust volume. What would you like?"

        if resolved == "media_play":
            ok, err = _playerctl("play")
        elif resolved == "media_pause":
            ok, err = _playerctl("pause")
        elif resolved == "media_play_pause":
            ok, err = _playerctl("play-pause")
        elif resolved == "media_next":
            ok, err = _playerctl("next")
        elif resolved == "media_prev":
            ok, err = _playerctl("previous")
        elif resolved == "media_stop":
            ok, err = _playerctl("stop")
        elif resolved == "audio_mute":
            ok, err = _audio_mute()
        elif resolved == "audio_unmute":
            ok, err = _audio_unmute()
        elif resolved == "audio_volume_up":
            ok, err = _audio_volume_up()
        elif resolved == "audio_volume_down":
            ok, err = _audio_volume_down()
        else:
            return "I can play, pause, skip tracks, mute, or adjust volume. What would you like?"

        if ok:
            labels = {
                "media_play": "Playing.",
                "media_pause": "Paused.",
                "media_play_pause": "Toggled play/pause.",
                "media_next": "Next track.",
                "media_prev": "Previous track.",
                "media_stop": "Stopped.",
                "audio_mute": "Muted.",
                "audio_unmute": "Unmuted.",
                "audio_volume_up": "Volume up.",
                "audio_volume_down": "Volume down.",
            }
            return labels.get(resolved, "Done.")
        return f"Could not complete: {err}"
