"""PyWebView JS bridge for Gerty."""

from gerty.llm.router import Router
from gerty.pipeline import chat_pipeline_sync
from gerty.tools.notes import get_notes, delete_note as delete_note_by_index
from gerty.voice.wake_word import request_ptt_recording, stop_ptt_recording


def create_bridge(router: Router):
    """Create API object for pywebview.expose()."""

    class GertyAPI:
        def __init__(self):
            self._router = router
            self._history: list[dict] = []

        def sendMessage(self, message: str) -> str:
            """Handle message from frontend. Returns reply."""
            reply = chat_pipeline_sync(self._router, message, history=self._history)
            self._history.append({"role": "user", "content": message})
            self._history.append({"role": "assistant", "content": reply})
            # Keep last 50 messages for context (was 20; caused OpenClaw empty response at ~20)
            if len(self._history) > 50:
                self._history = self._history[-50:]
            return reply

        def getHistory(self) -> list[dict]:
            return self._history

        def startVoiceRecording(self) -> None:
            """Start push-to-talk recording (hold mic button)."""
            request_ptt_recording()

        def stopVoiceRecording(self) -> None:
            """Stop push-to-talk recording (release mic button)."""
            stop_ptt_recording()

        def getNotes(self) -> list[str]:
            """Return notes list. Bridge fallback when fetch blocks in Qt WebEngine."""
            return get_notes()

        def deleteNote(self, index: int) -> bool:
            """Delete note at 0-based index. Bridge fallback when fetch blocks."""
            return delete_note_by_index(index)

    return GertyAPI()
