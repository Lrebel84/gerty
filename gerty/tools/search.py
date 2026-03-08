"""Web search tool: DuckDuckGo (no API key)."""

import logging

from gerty.tools.base import Tool

logger = logging.getLogger(__name__)


def _extract_query(message: str) -> str | None:
    """Extract search query from message. Handles explicit and implicit search phrasings."""
    lower = message.lower()
    # Explicit search phrases (longer phrases first to avoid "find " matching "find me ")
    for phrase in ["search for", "search ", "look up", "look up the ", "google ", "find me ", "find "]:
        if phrase in lower:
            idx = lower.find(phrase) + len(phrase)
            rest = message[idx:].strip().lstrip(":").strip()
            if rest:
                return rest
    # Implicit web lookup: "get me X", "can you get me X", "can you find me X" (find me in explicit above)
    for phrase in ["can you get me ", "can you find me ", "get me "]:
        if phrase in lower:
            idx = lower.find(phrase) + len(phrase)
            rest = message[idx:].strip().lstrip(":").strip()
            if rest:
                return rest
    # "when is X" - e.g. "when is the next showtimes of Dune at VUE Sheffield"
    if "when is" in lower:
        idx = lower.find("when is") + len("when is")
        rest = message[idx:].strip().lstrip(":").strip()
        if rest:
            return rest
    # "contact details for X", "contact info for X" - extract the entity
    for phrase in ["contact details for ", "contact info for ", "phone number for ", "address of "]:
        if phrase in lower:
            idx = lower.find(phrase) + len(phrase)
            rest = message[idx:].strip().lstrip(":").strip()
            if rest:
                return rest
    # "who owns X", "where can i find X"
    for phrase in ["who owns ", "where can i find ", "where can i get "]:
        if phrase in lower:
            idx = lower.find(phrase) + len(phrase)
            rest = message[idx:].strip().lstrip(":").strip()
            if rest:
                return rest
    # Fallback: if message looks like a request for info, use whole message as query
    # (e.g. "who owns xyz business" -> "who owns xyz business")
    if any(kw in lower for kw in ["contact", "showtimes", "opening hours", "phone", "address", "where can i find"]):
        return message.strip()
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
