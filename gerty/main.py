"""Gerty main entry point: starts UI, optional voice loop, optional Telegram bot."""

import logging
import sys
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gerty.config import OLLAMA_BASE_URL, TELEGRAM_BOT_TOKEN, PICOVOICE_ACCESS_KEY
from gerty.llm.router import Router
from gerty.notifications import notify
from gerty.tools import ToolExecutor, TimeDateTool, AlarmsTool, TimersTool
from gerty.tools.alarms import get_pending_alarms_for_trigger
from gerty.tools.timers import register_timer_callback
from gerty.ui.server import create_app
from gerty.ui.bridge import create_bridge


def _run_server(app, port: int):
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def _run_telegram_bot(router_callback):
    from gerty.telegram.bot import create_bot
    create_bot(router_callback)


def _alarm_trigger_loop():
    """Background loop: poll for due alarms and notify."""
    import time
    while True:
        try:
            due = get_pending_alarms_for_trigger()
            for alarm in due:
                msg = alarm.get("label", "Alarm") + " at " + alarm.get("time", "")
                notify(f"Alarm: {msg}", channels=["tts", "system", "telegram"])
        except Exception as e:
            logger.debug("Alarm loop: %s", e)
        time.sleep(5)


def _on_timer_done(label: str, duration_sec: int):
    """Called when a timer completes."""
    mins, secs = divmod(duration_sec, 60)
    if mins:
        msg = f"{label} finished ({mins}m)"
    else:
        msg = f"{label} finished ({duration_sec}s)"
    notify(msg, channels=["tts", "system", "telegram"])


def main():
    # Build tool executor and router
    executor = ToolExecutor()
    executor.register(TimeDateTool(), ["time", "date"])
    executor.register(AlarmsTool())
    executor.register(TimersTool())

    router = Router(tool_executor=executor.execute)

    # Check Ollama
    try:
        import httpx
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        if r.status_code != 200:
            print("Warning: Ollama not responding. Start with: ollama serve")
    except Exception:
        print("Warning: Ollama not running. Start with: ollama serve")

    # Build FastAPI app
    app = create_app(router)
    port = 8765

    # Start server in background
    server_thread = threading.Thread(target=_run_server, args=(app, port), daemon=True)
    server_thread.start()

    # Start Telegram bot in background if configured
    if TELEGRAM_BOT_TOKEN:
        telegram_thread = threading.Thread(
            target=_run_telegram_bot, args=(router.route,), daemon=True
        )
        telegram_thread.start()

    # Register timer callback and start alarm trigger loop
    register_timer_callback(_on_timer_done)
    alarm_thread = threading.Thread(target=_alarm_trigger_loop, daemon=True)
    alarm_thread.start()

    # Give server time to start
    import time
    time.sleep(0.5)

    # PyWebView window
    import webview

    api = create_bridge(router)
    window = webview.create_window(
        "Gerty",
        f"http://127.0.0.1:{port}",
        width=900,
        height=700,
        resizable=True,
        background_color="#0f0f0f",
        js_api=api,
    )

    def on_voice_exchange(user_msg: str, assistant_msg: str):
        """Push voice exchange to UI."""
        import json
        try:
            window.evaluate_js(
                f"window.__gertyAddVoiceExchange?.({json.dumps(user_msg)}, {json.dumps(assistant_msg)})"
            )
        except Exception:
            pass

    def on_voice_status(status: str):
        """Push voice status to UI."""
        import json
        try:
            window.evaluate_js(f"window.__gertySetVoiceStatus?.({json.dumps(status)})")
        except Exception:
            pass

    if PICOVOICE_ACCESS_KEY:
        try:
            from gerty.voice.loop import start_voice_loop_thread
            start_voice_loop_thread(
                router.route,
                on_exchange=on_voice_exchange,
                on_status_change=on_voice_status,
            )
        except Exception as e:
            logger.warning("Voice loop failed to start: %s", e)

    webview.start(debug=False, gui="qt")


if __name__ == "__main__":
    main()
