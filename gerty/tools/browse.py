"""Interactive browser tool: navigate, click, forms. Uses BrowserUse + OpenRouter."""

import asyncio
import logging
from gerty.config import (
    BROWSE_HEADED,
    GERTY_BROWSE_ENABLED,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
    OPENROUTER_RESEARCH_MODEL,
)
from gerty.tools.base import Tool
from gerty.tools.browse_auth import get_storage_state_for_message

logger = logging.getLogger(__name__)


def _run_browse(task: str, storage_state_path: str | None = None) -> str:
    """Run BrowserUse agent. Blocks until done."""
    if not OPENROUTER_API_KEY:
        return (
            "Interactive browsing requires OpenRouter. Add OPENROUTER_API_KEY and switch "
            "provider to OpenRouter in Settings."
        )
    try:
        from browser_use import Agent, Browser, ChatOpenAI
    except ImportError as e:
        logger.debug("browser-use import failed: %s", e)
        return (
            "Interactive browsing requires browser-use (Python 3.11+). Run: pip install browser-use playwright "
            "&& python -m playwright install chromium"
        )

    llm = ChatOpenAI(
        model=OPENROUTER_MODEL or OPENROUTER_RESEARCH_MODEL,
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    browser_kwargs: dict = {
        "headless": not BROWSE_HEADED,
    }
    if storage_state_path:
        browser_kwargs["storage_state"] = storage_state_path
    browser = Browser(**browser_kwargs)
    agent = Agent(
        task=task,
        llm=llm,
        browser=browser,
        use_vision=False,
    )

    async def _run():
        result = await agent.run(max_steps=15)
        # AgentHistoryList: final result may be in result.final_result() or last history item
        if result is None:
            return "Browsing completed but no result was extracted."
        if hasattr(result, "final_result") and callable(result.final_result):
            try:
                fr = result.final_result()
                if fr:
                    return str(fr)
            except Exception:
                pass
        if hasattr(result, "result") and result.result:
            return str(result.result)
        if hasattr(result, "history") and result.history:
            for h in reversed(result.history):
                if hasattr(h, "result") and h.result:
                    return str(h.result)
        return "Browsing completed but no result was extracted."

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.debug("Browse failed: %s", e)
        return f"Browsing failed: {e}"


class BrowseTool(Tool):
    """Interactive web browsing via BrowserUse (click, navigate, forms). OpenRouter only."""

    @property
    def name(self) -> str:
        return "browse"

    @property
    def description(self) -> str:
        return "Browse the web interactively (navigate, click, fill forms). Requires OpenRouter."

    def execute(self, intent: str, message: str) -> str:
        if not GERTY_BROWSE_ENABLED:
            return (
                "Interactive browsing is disabled. Set GERTY_BROWSE_ENABLED=1 in .env to enable. "
                "Browsing can access sensitive sites."
            )
        storage_state = get_storage_state_for_message(message)
        return _run_browse(message, storage_state)
