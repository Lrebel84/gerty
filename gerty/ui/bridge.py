"""PyWebView JS bridge for Gerty."""

from gerty.llm.router import Router


def create_bridge(router: Router):
    """Create API object for pywebview.expose()."""

    class GertyAPI:
        def __init__(self):
            self._router = router
            self._history: list[dict] = []

        def sendMessage(self, message: str) -> str:
            """Handle message from frontend. Returns reply."""
            reply = self._router.route(message, history=self._history, source="chat")
            self._history.append({"role": "user", "content": message})
            self._history.append({"role": "assistant", "content": reply})
            # Keep last 20 messages for context
            if len(self._history) > 20:
                self._history = self._history[-20:]
            return reply

        def getHistory(self) -> list[dict]:
            return self._history

    return GertyAPI()
