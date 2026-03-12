"""OpenClaw client: execute actions via openclaw-sdk."""

import asyncio
import logging
import socket
from typing import Optional

from gerty.config import (
    OPENCLAW_AGENT_ID,
    OPENCLAW_GATEWAY_WS_URL,
    OPENCLAW_HISTORY_MAX_MESSAGES,
    OPENCLAW_TIMEOUT,
)

logger = logging.getLogger(__name__)

# Natural message when OpenClaw is unreachable
OPENCLAW_UNAVAILABLE_MSG = (
    "I know what you want, but my action system isn't running right now. "
    "Try starting OpenClaw with: openclaw daemon start"
)

def _format_message(
    message: str,
    history: list[dict] | None = None,
    system_context: str | None = None,
) -> str:
    """Build the payload: system context + history + current message."""
    parts = []
    if system_context and system_context.strip():
        parts.append(f"[System: {system_context.strip()}]\n\n")
    if history:
        keep = history[-OPENCLAW_HISTORY_MAX_MESSAGES:]
        lines = []
        for m in keep:
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
    Returns result content or a natural error message if OpenClaw is unreachable.
    """
    if not _gateway_port_reachable():
        return OPENCLAW_UNAVAILABLE_MSG
    payload = _format_message(message, history=history, system_context=system_context)
    timeout = _get_execute_timeout()
    try:
        return asyncio.run(asyncio.wait_for(_execute_async(payload), timeout=timeout))
    except asyncio.TimeoutError:
        logger.warning("OpenClaw execute timed out after %ds", timeout)
        return OPENCLAW_UNAVAILABLE_MSG


async def _execute_async(message: str) -> str:
    try:
        from openclaw_sdk import OpenClawClient
        from openclaw_sdk.core.config import ClientConfig
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
            agent = client.get_agent(OPENCLAW_AGENT_ID)
            result = await agent.execute(message)
            if result.success:
                return result.content or "Done."
            return result.content or "OpenClaw completed but returned no output."
    except Exception as e:
        logger.warning("OpenClaw execute failed: %s", e)
        return OPENCLAW_UNAVAILABLE_MSG


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
            agent = client.get_agent(OPENCLAW_AGENT_ID)
            session_key = f"agent:{OPENCLAW_AGENT_ID}:main"
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
