"""OpenClaw client: execute actions via openclaw-sdk."""

import asyncio
import logging
import queue
import socket
import threading
from typing import AsyncIterator, Iterator, Optional

from gerty.config import (
    OPENCLAW_AGENT_ID,
    OPENCLAW_GATEWAY_WS_URL,
    OPENCLAW_TIMEOUT,
)
from gerty.openclaw.validation import validate_openclaw_response

logger = logging.getLogger(__name__)

# Natural message when OpenClaw is unreachable
OPENCLAW_UNAVAILABLE_MSG = (
    "I know what you want, but my action system isn't running right now. "
    "Try starting OpenClaw with: openclaw daemon start"
)

# Tool names -> brief feedback for streaming
_TOOL_FEEDBACK = {
    "web_search": "Searching...",
    "web_fetch": "Fetching...",
    "exec": "Running...",
    "files": "Working with files...",
    "process": "Running...",
}

def build_openclaw_payload(
    message: str,
    history: list[dict] | None = None,
    system_context: str | None = None,
) -> str:
    """
    Build the OpenClaw execution payload (Sprint 2c).

    Structure (in order):
    1. [System: {system_context}] — operating context, tool instructions, persona
    2. Previous conversation: — full history as "Role: content" lines (no trimming here)
    3. {message} — current user message

    History policy: Full history as provided. No trimming or summarization in this layer.
    The pipeline may trim (voice) or summarize (chat, local) before passing history.
    """
    parts = []
    context = (system_context or "").strip()
    if context:
        parts.append(f"[System: {context}]\n\n")
    if history:
        lines = []
        for m in history:
            role = m.get("role", "user")
            content = m.get("content", "")
            if content:
                lines.append(f"{role.capitalize()}: {content}")
        if lines:
            parts.append("Previous conversation:\n" + "\n".join(lines) + "\n\n")
    parts.append(message)
    return "".join(parts)


def _gateway_port_reachable() -> bool:
    """Quick check: is gateway port 18789 listening? Fails fast if daemon not running."""
    try:
        with socket.create_connection(("127.0.0.1", 18789), timeout=2):
            return True
    except (OSError, socket.timeout):
        return False


# Max wait for OpenClaw — use OPENCLAW_TIMEOUT from config (default 120 for long tasks)
def _get_execute_timeout() -> int:
    return OPENCLAW_TIMEOUT


def execute(
    message: str,
    history: list[dict] | None = None,
    system_context: str | None = None,
) -> str:
    """
    Execute a task via OpenClaw. Sync wrapper around async openclaw-sdk.
    Returns validated, normalized result or a natural error message if unreachable.
    """
    if not _gateway_port_reachable():
        return OPENCLAW_UNAVAILABLE_MSG
    payload = build_openclaw_payload(message, history=history, system_context=system_context)
    timeout = _get_execute_timeout()
    try:
        return asyncio.run(asyncio.wait_for(_execute_async(payload, original_message=message), timeout=timeout))
    except asyncio.TimeoutError:
        logger.warning("OpenClaw execute timed out after %ds", timeout)
        return OPENCLAW_UNAVAILABLE_MSG


async def _execute_async(payload: str, *, original_message: str = "") -> str:
    try:
        from openclaw_sdk import OpenClawClient
        from openclaw_sdk.core.config import ClientConfig, ExecutionOptions
    except ImportError:
        logger.warning("openclaw-sdk not installed. Run: pip install openclaw-sdk")
        return (
            "OpenClaw isn't set up yet. Install it with: pip install openclaw-sdk, "
            "then start the daemon: openclaw daemon start"
        )

    config = ClientConfig(
        gateway_ws_url=OPENCLAW_GATEWAY_WS_URL,
        timeout=OPENCLAW_TIMEOUT,
    )
    try:
        async with await OpenClawClient.connect(**config.model_dump()) as client:
            agent = client.get_agent(OPENCLAW_AGENT_ID, session_name="gerty")
            options = ExecutionOptions(deliver=False)
            result = await agent.execute(payload, options=options)
            content = (result.content or "").strip()
            validated = validate_openclaw_response(
                content, original_message=original_message or payload, success=result.success
            )
            if validated.replaced_with_hint:
                logger.warning(
                    "OpenClaw: validated replacement. empty=%s tool_fail=%s fabricated=%s msg=%r",
                    validated.is_empty, validated.is_tool_failure, validated.is_likely_fabricated,
                    (original_message or payload)[:100],
                )
            return validated.normalized_content
    except Exception as e:
        logger.warning("OpenClaw execute failed: %s", e)
        return OPENCLAW_UNAVAILABLE_MSG


async def _execute_stream_async(
    message: str,
    history: list[dict] | None = None,
    system_context: str | None = None,
) -> AsyncIterator[str]:
    """Async generator: yield content chunks and tool feedback from OpenClaw stream."""
    try:
        from openclaw_sdk import OpenClawClient
        from openclaw_sdk.core.config import ClientConfig, ExecutionOptions
        from openclaw_sdk.core.types import ContentEvent, DoneEvent, ErrorEvent, ToolCallEvent
    except ImportError:
        logger.warning("openclaw-sdk not installed. Run: pip install openclaw-sdk")
        yield (
            "OpenClaw isn't set up yet. Install it with: pip install openclaw-sdk, "
            "then start the daemon: openclaw daemon start"
        )
        return

    config = ClientConfig(
        gateway_ws_url=OPENCLAW_GATEWAY_WS_URL,
        timeout=OPENCLAW_TIMEOUT,
    )
    try:
        async with await OpenClawClient.connect(**config.model_dump()) as client:
            agent = client.get_agent(OPENCLAW_AGENT_ID, session_name="gerty")
            payload = build_openclaw_payload(message, history=history, system_context=system_context)
            seen_tool_feedback = set()

            try:
                options = ExecutionOptions(deliver=False)
                async for event in agent.execute_stream_typed(payload, options=options):
                    if isinstance(event, ContentEvent) and event.text:
                        yield event.text
                    elif isinstance(event, ToolCallEvent) and event.tool:
                        # Yield brief feedback once per tool (avoid spam)
                        feedback = _TOOL_FEEDBACK.get(
                            event.tool, f"Using {event.tool}..."
                        )
                        if event.tool not in seen_tool_feedback:
                            seen_tool_feedback.add(event.tool)
                            yield feedback
                    elif isinstance(event, ErrorEvent):
                        yield event.message or "OpenClaw encountered an error."
                        return
                    elif isinstance(event, DoneEvent):
                        break
            except NotImplementedError:
                # Gateway doesn't support streaming; fall back to execute
                logger.debug("OpenClaw streaming not supported, using execute")
                options = ExecutionOptions(deliver=False)
                result = await agent.execute(payload, options=options)
                content = (result.content or "").strip()
                validated = validate_openclaw_response(
                    content, original_message=message, success=result.success
                )
                yield validated.normalized_content
    except asyncio.TimeoutError:
        logger.warning("OpenClaw stream timed out after %ds", _get_execute_timeout())
        yield OPENCLAW_UNAVAILABLE_MSG
    except Exception as e:
        logger.warning("OpenClaw stream failed: %s", e)
        yield OPENCLAW_UNAVAILABLE_MSG


def execute_stream(
    message: str,
    history: list[dict] | None = None,
    system_context: str | None = None,
) -> Iterator[str]:
    """
    Execute via OpenClaw and stream response chunks. Yields content as it arrives,
    plus brief feedback for tool calls (e.g. "Searching...", "Running...").
    Falls back to non-streaming execute if gateway doesn't support streaming.
    """
    if not _gateway_port_reachable():
        yield OPENCLAW_UNAVAILABLE_MSG
        return

    out_queue: queue.Queue[str | None] = queue.Queue()

    def run_stream():
        async def consume():
            try:
                async for chunk in _execute_stream_async(
                    message, history=history, system_context=system_context
                ):
                    out_queue.put(chunk)
            except asyncio.TimeoutError:
                logger.warning("OpenClaw stream timed out")
                out_queue.put(OPENCLAW_UNAVAILABLE_MSG)
            except Exception as e:
                logger.warning("OpenClaw stream consume failed: %s", e)
                out_queue.put(OPENCLAW_UNAVAILABLE_MSG)
            finally:
                out_queue.put(None)

        try:
            asyncio.run(asyncio.wait_for(consume(), timeout=_get_execute_timeout()))
        except asyncio.TimeoutError:
            out_queue.put(OPENCLAW_UNAVAILABLE_MSG)
            out_queue.put(None)

    thread = threading.Thread(target=run_stream, daemon=True)
    thread.start()

    while True:
        try:
            chunk = out_queue.get(timeout=0.1)
        except queue.Empty:
            if not thread.is_alive():
                break
            continue
        if chunk is None:
            break
        yield chunk


def clear_session() -> bool:
    """
    Clear the OpenClaw session (conversation history).
    Called when user clicks "New chat". Returns True on success, False if unreachable.
    """
    try:
        return asyncio.run(_clear_session_async())
    except Exception:
        return False


async def _clear_session_async() -> bool:
    """Clear OpenClaw session. Returns True on success."""
    try:
        from openclaw_sdk import OpenClawClient
        from openclaw_sdk.core.config import ClientConfig
    except ImportError:
        return False
    if not _gateway_port_reachable():
        return False
    try:
        config = ClientConfig(
            gateway_ws_url=OPENCLAW_GATEWAY_WS_URL,
            timeout=5,
        )
        async with await OpenClawClient.connect(**config.model_dump()) as client:
            agent = client.get_agent(OPENCLAW_AGENT_ID, session_name="gerty")
            session_key = f"agent:{OPENCLAW_AGENT_ID}:gerty"
            await client.gateway.sessions_reset(session_key)
            return True
    except Exception as e:
        logger.debug("OpenClaw clear_session failed: %s", e)
        return False


def is_reachable() -> bool:
    """Check if OpenClaw gateway is reachable."""
    try:
        from openclaw_sdk import OpenClawClient
        from openclaw_sdk.core.config import ClientConfig
    except ImportError:
        return False

    async def _check():
        try:
            config = ClientConfig(
                gateway_ws_url=OPENCLAW_GATEWAY_WS_URL,
                timeout=5,
            )
            async with await OpenClawClient.connect(**config.model_dump()) as client:
                return True
        except Exception:
            return False

    try:
        return asyncio.run(_check())
    except Exception:
        return False
