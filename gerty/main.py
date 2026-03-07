"""Gerty main entry point: starts UI, optional voice loop, optional Telegram bot."""

import logging
import sys
import threading
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gerty.config import LOG_LEVEL, PROJECT_ROOT

# Configure logging early (GERTY_LOG_LEVEL=INFO for debugging)
_level = getattr(logging, LOG_LEVEL, logging.WARNING)
_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=_level, format=_fmt, datefmt="%H:%M:%S")
# When INFO or DEBUG, also write to gerty.log for tail -f during testing
if _level <= logging.INFO:
    _fh = logging.FileHandler(PROJECT_ROOT / "gerty.log", mode="a", encoding="utf-8")
    _fh.setFormatter(logging.Formatter(_fmt, datefmt="%H:%M:%S"))
    logging.getLogger().addHandler(_fh)
    logging.getLogger("httpx").setLevel(logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)

from gerty.config import (
    ALARM_POLL_INTERVAL,
    OLLAMA_BASE_URL,
    SERVER_HOST,
    TELEGRAM_BOT_TOKEN,
)
from gerty.llm.ollama_client import OllamaClient
from gerty.llm.router import Router
from gerty.notifications import notify
from gerty.pipeline import chat_pipeline_sync
from gerty.tools import (
    AlarmsTool,
    CalculatorTool,
    NotesTool,
    PomodoroTool,
    RandomTool,
    RagTool,
    SearchTool,
    StopwatchTool,
    TimersTool,
    TimeDateTool,
    TimezoneTool,
    ToolExecutor,
    UnitsTool,
    WeatherTool,
)
from gerty.tools.alarms import get_pending_alarms_for_trigger
from gerty.tools.timers import register_timer_callback
from gerty.tools.pomodoro import register_pomodoro_callback
from gerty.ui.server import create_app
from gerty.ui.bridge import create_bridge


def _run_server(app, port: int):
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=port, log_level="warning")


def _run_telegram_bot(router_callback):
    from gerty.telegram.bot import create_bot
    create_bot(router_callback)


def _alarm_trigger_loop():
    """Background loop: poll for due alarms, start sounding (TTS repeat + listen for cancel)."""
    import time
    from gerty.voice.alarm_state import set_sounding_alarm, get_sounding_alarm
    from gerty.voice.wake_word import request_ptt_recording

    while True:
        try:
            # Don't trigger if one is already sounding
            if get_sounding_alarm():
                time.sleep(ALARM_POLL_INTERVAL)
                continue
            due = get_pending_alarms_for_trigger()
            if due:
                alarm = due[0]
                time_str = alarm.get("time", "alarm")
                logger.info("Alarm triggering: %s – setting sounding, notifying, requesting PTT for voice cancel", time_str)
                set_sounding_alarm(alarm)
                msg = f"This is your {time_str} alarm, say cancel to stop"
                notify(msg, channels=["system", "tts", "telegram"])
                request_ptt_recording()
                logger.debug("Alarm: PTT requested – voice loop will open mic on next iteration")
        except Exception as e:
            logger.debug("Alarm loop: %s", e)
        time.sleep(ALARM_POLL_INTERVAL)


def _on_timer_done(label: str, duration_sec: int):
    """Called when a timer completes."""
    mins, secs = divmod(duration_sec, 60)
    if mins:
        msg = f"{label} finished ({mins}m)"
    else:
        msg = f"{label} finished ({duration_sec}s)"
    notify(msg, channels=["tts", "system", "telegram"])


def _on_pomodoro_done(phase: str, duration_sec: int):
    """Called when a pomodoro phase completes."""
    mins = duration_sec // 60
    msg = f"Pomodoro {phase} complete ({mins}m)"
    notify(msg, channels=["tts", "system", "telegram"])


def main():
    # Build tool executor and router
    # When adding a tool: also update gerty/tools/skills_registry.py, frontend/src/skills.ts, COMMANDS.md
    # See docs/ADDING_TOOLS.md
    ollama = OllamaClient()
    executor = ToolExecutor()
    executor.register(TimeDateTool(), ["time", "date"])
    executor.register(AlarmsTool())
    executor.register(TimersTool())
    executor.register(CalculatorTool())
    executor.register(UnitsTool())
    executor.register(RandomTool())
    executor.register(NotesTool())
    executor.register(StopwatchTool())
    executor.register(TimezoneTool())
    executor.register(WeatherTool())
    executor.register(RagTool(ollama=ollama))
    executor.register(SearchTool())
    executor.register(PomodoroTool())

    router = Router(tool_executor=executor.execute)

    # Check Ollama
    try:
        import httpx
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        if r.status_code != 200:
            logger.warning("Ollama not responding. Start with: ollama serve")
    except Exception as e:
        logger.warning("Ollama not running: %s. Start with: ollama serve", e)

    # Build FastAPI app
    app = create_app(router)
    port = 8765

    # Start server in background
    server_thread = threading.Thread(target=_run_server, args=(app, port), daemon=True)
    server_thread.start()

    # Start Telegram bot in background if configured
    if TELEGRAM_BOT_TOKEN:
        telegram_thread = threading.Thread(
            target=_run_telegram_bot,
            args=(lambda msg: chat_pipeline_sync(router, msg),),
            daemon=True,
        )
        telegram_thread.start()

    # Register timer and pomodoro callbacks; start alarm trigger loop
    register_timer_callback(_on_timer_done)
    register_pomodoro_callback(_on_pomodoro_done)
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
        f"http://{SERVER_HOST}:{port}",
        width=900,
        height=700,
        resizable=True,
        background_color="#0f0f0f",
        js_api=api,
    )

    def on_voice_exchange(user_msg: str, assistant_msg: str):
        """Push voice exchange to UI (legacy, when not streaming)."""
        import json
        try:
            window.evaluate_js(
                f"window.__gertyAddVoiceExchange?.({json.dumps(user_msg)}, {json.dumps(assistant_msg)})"
            )
        except Exception as e:
            logger.debug("Voice exchange push failed: %s", e)

    def on_voice_user_text(text: str):
        """Show user STT text immediately in chat."""
        import json
        try:
            window.evaluate_js(f"window.__gertyAddVoiceUserMessage?.({json.dumps(text)})")
        except Exception as e:
            logger.debug("Voice user text push failed: %s", e)

    def on_voice_assistant_content(content: str):
        """Update streaming assistant message in chat."""
        import json
        try:
            window.evaluate_js(f"window.__gertySetVoiceAssistantContent?.({json.dumps(content)})")
        except Exception as e:
            logger.debug("Voice assistant content push failed: %s", e)

    def on_voice_status(status: str):
        """Push voice status to UI."""
        import json
        try:
            window.evaluate_js(f"window.__gertySetVoiceStatus?.({json.dumps(status)})")
        except Exception as e:
            logger.debug("Voice status push failed: %s", e)

    try:
        import httpx

        from gerty.pipeline import chat_pipeline_stream
        from gerty.voice.loop import start_voice_loop_thread

        def _get_voice_history() -> list[dict]:
            """Fetch persisted chat history for voice context."""
            try:
                r = httpx.get(
                    f"http://{SERVER_HOST}:8765/api/chat/history",
                    timeout=2,
                )
                if r.status_code == 200:
                    msgs = r.json().get("messages", [])
                    return [
                        {"role": m.get("role", "user"), "content": m.get("content", "")}
                        for m in msgs
                    ]
            except Exception:
                pass
            return []

        def stream_cb(msg):
            history = _get_voice_history()
            return chat_pipeline_stream(
                router, msg, history=history, source="voice"
            )

        def sync_cb(msg):
            history = _get_voice_history()
            return chat_pipeline_sync(
                router, msg, history=history, source="voice"
            )

        def on_save_after_exchange():
            try:
                window.evaluate_js("window.__gertySaveHistory?.()")
            except Exception as e:
                logger.debug("Voice save after exchange failed: %s", e)
            try:
                window.evaluate_js("window.__gertyRefreshAlarmsTimers?.()")
            except Exception as e:
                logger.debug("Voice refresh alarms/timers failed: %s", e)

        start_voice_loop_thread(
            sync_cb,
            on_exchange=on_voice_exchange,
            on_status_change=on_voice_status,
            on_user_text=on_voice_user_text,
            on_assistant_content=on_voice_assistant_content,
            stream_router_callback=stream_cb,
            on_save_after_exchange=on_save_after_exchange,
        )
    except Exception as e:
        logger.warning("Voice loop failed to start: %s", e)

    icon_path = str(PROJECT_ROOT / "assets" / "gerty.png")

    # No on_closing handler - it blocked the window (evaluate_js + httpx can hang).
    # Chat is already saved after each message and on beforeunload.
    webview.start(debug=False, gui="qt", icon=icon_path)


if __name__ == "__main__":
    main()
