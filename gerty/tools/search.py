"""Web search tool: DuckDuckGo (no API key)."""

import logging

from gerty.tools.base import Tool

logger = logging.getLogger(__name__)


def _extract_query(message: str) -> str | None:
    """Extract search query from message."""
    lower = message.lower()
    for phrase in ["search for", "search ", "look up", "find ", "google "]:
        if phrase in lower:
            idx = lower.find(phrase) + len(phrase)
            rest = message[idx:].strip().lstrip(":").strip()
            if rest:
                return rest
    return None


def _duckduckgo_search(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo. Returns list of {title, url, snippet}."""
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("url", "")),
                    "snippet": r.get("body", r.get("snippet", "")),
                })
        return results
    except ImportError:
        logger.debug("duckduckgo_search not installed")
        return []
    except Exception as e:
        logger.debug("DuckDuckGo search failed: %s", e)
        return []


class SearchTool(Tool):
    """Web search via DuckDuckGo."""

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search the web"

    def execute(self, intent: str, message: str) -> str:
        query = _extract_query(message)
        if not query:
            return "Try: search for Python tutorial, or look up current events"
        results = _duckduckgo_search(query)
        if not results:
            return "Search failed or no results. Try again later, or install: pip install duckduckgo-search"
        lines = []
        for i, r in enumerate(results[:5], 1):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            snippet = (r.get("snippet", "") or "")[:150]
            lines.append(f"{i}. **{title}**\n   {url}\n   {snippet}...")
        return "\n\n".join(lines)
