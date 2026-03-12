"""MCP client for connecting to Rube (Composio) MCP server.

Note: Each list_tools and call_tool creates a new connection (connect → initialize → call → close).
This adds ~15-20s per tool round. For faster MCP, use Groq Remote MCP (GROQ_API_KEY + COMPOSIO_API_KEY)
which connects server-side with no local round-trips.
"""

import asyncio
import logging
import time
from typing import Any

import httpx

from gerty.config import COMPOSIO_API_KEY, RUBE_MCP_URL

logger = logging.getLogger(__name__)


def _mcp_tool_to_openai(tool: Any) -> dict:
    """Convert MCP Tool to OpenAI function format."""
    name = getattr(tool, "name", str(tool))
    description = getattr(tool, "description", None) or ""
    schema = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": schema,
        },
    }


def _extract_text_from_result(result: Any) -> str:
    """Extract text content from MCP CallToolResult."""
    content = getattr(result, "content", None) or []
    parts = []
    for item in content:
        if hasattr(item, "type") and item.type == "text":
            text = getattr(item, "text", "")
            if text:
                parts.append(text)
        elif isinstance(item, dict):
            if item.get("type") == "text":
                parts.append(item.get("text", ""))
    return "\n".join(parts) if parts else str(result)


async def _async_list_tools(url: str, api_key: str) -> list[dict]:
    """Async: connect to MCP server and list tools in OpenAI format."""
    headers: dict[str, str] = {}
    if api_key:
        # Rube uses Authorization: Bearer <token> (signed token from rube.app/settings/api-keys)
        headers["Authorization"] = f"Bearer {api_key}"

    from mcp import ClientSession
    from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

    client = create_mcp_http_client(
        headers=headers,
        timeout=httpx.Timeout(60.0, read=120.0),
    )
    async with client:
        async with streamable_http_client(
            url,
            http_client=client,
            terminate_on_close=True,
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                tools = getattr(result, "tools", []) or []
                return [_mcp_tool_to_openai(t) for t in tools]


async def _async_call_tool(url: str, api_key: str, name: str, arguments: dict[str, Any]) -> str:
    """Async: connect to MCP server and call a tool."""
    results = await _async_call_tools_batch(url, api_key, [(name, arguments or {})])
    return results[0] if results else ""


async def _async_call_tools_batch(
    url: str, api_key: str, calls: list[tuple[str, dict[str, Any]]]
) -> list[str]:
    """Async: one connection, execute all tool calls. Much faster than N separate connections."""
    if not calls:
        return []
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    from mcp import ClientSession
    from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

    client = create_mcp_http_client(
        headers=headers,
        timeout=httpx.Timeout(60.0, read=120.0),
    )
    async with client:
        async with streamable_http_client(
            url,
            http_client=client,
            terminate_on_close=True,
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                results = []
                for name, arguments in calls:
                    result = await session.call_tool(name, arguments or {})
                    results.append(_extract_text_from_result(result))
                return results


def get_tool_schema_hints(client, query: str) -> str:
    """
    Fetch Rube's tool schemas for a query and return prompt-ready hints.
    Rube's SEARCH_TOOLS returns exact param requirements (e.g. time_min, time_max).
    We inject these so the LLM knows exactly what Rube expects.
    """
    try:
        raw = client.call_tool("RUBE_SEARCH_TOOLS", {"query": query})
        import json
        data = json.loads(raw)
        schemas = data.get("data", {}).get("data", {}).get("tool_schemas", {})
        if not schemas:
            return ""
        lines = [
            "\nRube tool schemas – you MUST pass these exact params when calling RUBE_MULTI_EXECUTE_TOOL:",
            "Do NOT call these tools with empty arguments. Extract/compute required values first.",
        ]
        for slug, info in schemas.items():
            if not isinstance(info, dict):
                continue
            inp = info.get("input_schema") or {}
            required = inp.get("required") or []
            props = inp.get("properties") or {}
            if not required:
                continue
            lines.append(f"- {slug}: REQUIRED params: {required}")
            for r in required:
                p = props.get(r, {})
                d = p.get("description", "")
                if d:
                    lines.append(f"  - {r}: {d[:150]}")
            # Add concrete example for calendar tools – params go in tools[].arguments, NOT in thought
            if "time_min" in required and "time_max" in required:
                lines.append(
                    "  CRITICAL: Put time_min and time_max INSIDE the arguments object for that tool. "
                    "Example: {\"tool_slug\": \"GOOGLECALENDAR_EVENTS_LIST_ALL_CALENDARS\", \"arguments\": {\"time_min\": \"2026-03-09T00:00:00Z\", \"time_max\": \"2026-03-09T23:59:59Z\"}}. "
                    "Call GOOGLECALENDAR_GET_CURRENT_DATE_TIME first, then compute tomorrow's bounds and pass them in arguments."
                )
        return "\n".join(lines) if len(lines) > 2 else ""
    except Exception as e:
        logger.debug("get_tool_schema_hints failed: %s", e)
        return ""


class MCPClient:
    """Client for Rube (Composio) MCP server. Sync interface over async MCP SDK."""

    def __init__(
        self,
        url: str = RUBE_MCP_URL,
        api_key: str | None = None,
    ):
        self.url = url.rstrip("/")
        self.api_key = api_key or COMPOSIO_API_KEY
        self._tools_cache: list[dict] | None = None
        self._tools_cache_ttl_sec = 300  # 5 min
        self._schema_hints_cache: dict[str, str] = {}
        self._schema_hints_cache_ttl_sec = 300

    def fetch_calendar_direct(self, range_type: str) -> str | None:
        """
        Direct fetch of calendar events using correct Rube params.
        Bypasses LLM tool-calling so we pass time_min/time_max correctly.
        range_type: "today", "tomorrow", "this_week", "next_week", "this_month"
        Returns event data JSON string or None on failure.
        """
        import json
        from datetime import datetime, timedelta, timezone

        def _bounds(now: datetime, r: str) -> tuple[str, str]:
            d = now.date()
            if r == "today":
                start, end = d, d
            elif r == "tomorrow":
                start = end = d + timedelta(days=1)
            elif r == "this_week":
                # Mon–Sun; if today is Wed, start = Mon of this week
                start = d - timedelta(days=d.weekday())
                end = start + timedelta(days=6)
            elif r == "next_week":
                start = d - timedelta(days=d.weekday()) + timedelta(days=7)
                end = start + timedelta(days=6)
            elif r == "this_month":
                start = d.replace(day=1)
                # Last day of month
                next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
                end = next_month - timedelta(days=1)
            else:
                start = end = d
            time_min = f"{start.isoformat()}T00:00:00Z"
            time_max = f"{end.isoformat()}T23:59:59Z"
            return time_min, time_max

        try:
            raw = self.call_tool("RUBE_SEARCH_TOOLS", {"query": "google calendar list events"})
            data = json.loads(raw)
            inner = data.get("data", {}).get("data", {})
            session = inner.get("session") or {}
            session_id = session.get("id") or "direct"

            r1 = self.call_tools_batch([("RUBE_MULTI_EXECUTE_TOOL", {
                "tools": [{"tool_slug": "GOOGLECALENDAR_GET_CURRENT_DATE_TIME", "arguments": {}}],
                "sync_response_to_workbench": False,
                "memory": {},
                "session_id": session_id,
            })])
            if not r1:
                return None
            d1 = json.loads(r1[0])
            dt_str = (d1.get("data", {}).get("data", {}).get("results", [{}])[0].get("response", {}).get("data", {}).get("current_datetime")) or ""
            if not dt_str:
                return None
            try:
                now = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except ValueError:
                now = datetime.now(timezone.utc)

            time_min, time_max = _bounds(now, range_type)

            r2 = self.call_tools_batch([("RUBE_MULTI_EXECUTE_TOOL", {
                "tools": [{
                    "tool_slug": "GOOGLECALENDAR_EVENTS_LIST_ALL_CALENDARS",
                    "arguments": {"time_min": time_min, "time_max": time_max},
                }],
                "sync_response_to_workbench": False,
                "memory": {},
                "session_id": session_id,
            })])
            if not r2:
                return None
            return r2[0]
        except Exception as e:
            logger.debug("fetch_calendar_direct failed: %s", e)
            return None

    @staticmethod
    def calendar_range_from_message(message: str) -> str | None:
        """Return range_type for direct fetch if message asks about a supported range, else None."""
        m = message.lower()
        if any(k in m for k in ("tomorrow",)):
            return "tomorrow"
        if any(k in m for k in ("today", "right now", "now")):
            return "today"
        if any(k in m for k in ("this week", "the week", "week ahead")):
            return "this_week"
        if any(k in m for k in ("next week",)):
            return "next_week"
        if any(k in m for k in ("this month", "the month", "month ahead")):
            return "this_month"
        return None

    @staticmethod
    def infer_calendar_time_bounds(message: str, thought: str = "") -> tuple[str, str] | None:
        """
        Infer time_min/time_max (RFC3339) from user message and optionally LLM thought.
        Used when the LLM calls calendar tools with empty arguments - we fix it here
        so the LLM can handle arbitrary queries without hardcoding.
        """
        import re
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        d = now.date()
        m = (message + " " + thought).lower()

        # Try to extract RFC3339 from thought (LLM sometimes puts it there)
        for pattern in [
            r"time_min['\"]?\s*[:=]\s*['\"]?([\dT:\-+Z]+)",
            r"time_max['\"]?\s*[:=]\s*['\"]?([\dT:\-+Z]+)",
            r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[Z\d:+\-]*)",
        ]:
            matches = re.findall(pattern, m, re.I)
            if len(matches) >= 2:
                try:
                    t1 = datetime.fromisoformat(matches[0].replace("Z", "+00:00"))
                    t2 = datetime.fromisoformat(matches[1].replace("Z", "+00:00"))
                    if t1 < t2:
                        return t1.strftime("%Y-%m-%dT%H:%M:%SZ"), t2.strftime("%Y-%m-%dT%H:%M:%SZ")
                    return t2.strftime("%Y-%m-%dT%H:%M:%SZ"), t1.strftime("%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    pass

        def bounds(start, end):
            return f"{start.isoformat()}T00:00:00Z", f"{end.isoformat()}T23:59:59Z"

        # Explicit ranges
        if any(k in m for k in ("tomorrow",)):
            t = d + timedelta(days=1)
            return bounds(t, t)
        if any(k in m for k in ("today", "right now", "now")):
            return bounds(d, d)
        if any(k in m for k in ("this week", "the week", "week ahead", "this week's")):
            # On Sat/Sun, "this week" usually means the upcoming week (not the one ending today)
            if d.weekday() >= 5:  # Saturday=5, Sunday=6
                start = d - timedelta(days=d.weekday()) + timedelta(days=7)
            else:
                start = d - timedelta(days=d.weekday())
            return bounds(start, start + timedelta(days=6))
        if any(k in m for k in ("next week",)):
            start = d - timedelta(days=d.weekday()) + timedelta(days=7)
            return bounds(start, start + timedelta(days=6))
        if any(k in m for k in ("week after next", "in two weeks")):
            start = d - timedelta(days=d.weekday()) + timedelta(days=14)
            return bounds(start, start + timedelta(days=6))
        if any(k in m for k in ("this month", "the month", "month ahead")):
            start = d.replace(day=1)
            next_m = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            return bounds(start, next_m - timedelta(days=1))
        if any(k in m for k in ("next month",)):
            first = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
            next_m = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
            return bounds(first, next_m - timedelta(days=1))
        # Weekdays: "next Monday", "on Tuesday"
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, wd in enumerate(weekdays):
            if wd in m:
                target = (i - d.weekday()) % 7
                if target == 0 and "next" in m:
                    target = 7
                elif target == 0 and "this" not in m:
                    target = 7
                day = d + timedelta(days=target)
                return bounds(day, day)
        return None

    def make_batch_executor_with_calendar_fix(self, user_message: str):
        """
        Return a batch executor that fixes empty calendar arguments.
        When the LLM calls GOOGLECALENDAR_EVENTS_LIST_ALL_CALENDARS with empty arguments,
        we infer time_min/time_max from the user message and inject them.
        This lets the LLM handle arbitrary queries without hardcoding.
        """

        def batch_executor(calls: list[tuple[str, dict]]) -> list[str]:
            fixed = []
            for name, args in calls:
                if name == "RUBE_MULTI_EXECUTE_TOOL" and isinstance(args, dict):
                    tools = list(args.get("tools") or [])
                    thought = args.get("thought") or ""
                    for t in tools:
                        if t.get("tool_slug") == "GOOGLECALENDAR_EVENTS_LIST_ALL_CALENDARS":
                            t_args = dict(t.get("arguments") or {})
                            if not t_args.get("time_min") or not t_args.get("time_max"):
                                bounds = self.infer_calendar_time_bounds(user_message, thought)
                                if bounds:
                                    t_args["time_min"], t_args["time_max"] = bounds
                                    t["arguments"] = t_args
                                    logger.info("MCP: inferred time_min/time_max from user message")
                fixed.append((name, args))
            return self.call_tools_batch(fixed)

        return batch_executor

    def get_schema_hints_for_message(self, message: str) -> str:
        """Return Rube schema hints for the message context. Cached per query type."""
        msg_lower = message.lower()
        if any(k in msg_lower for k in ("calendar", "events", "tomorrow", "today", "schedule")):
            key = "calendar"
        elif any(k in msg_lower for k in ("gmail", "email", "inbox")):
            key = "gmail"
        elif any(k in msg_lower for k in ("drive", "google drive", "file")):
            key = "drive"
        elif any(k in msg_lower for k in ("tasks", "todo")):
            key = "tasks"
        else:
            return ""
        if key in self._schema_hints_cache:
            return self._schema_hints_cache[key]
        queries = {
            "calendar": "google calendar list events for date range",
            "gmail": "gmail list emails",
            "drive": "google drive list files",
            "tasks": "google tasks list",
        }
        hints = get_tool_schema_hints(self, queries[key])
        if hints:
            self._schema_hints_cache[key] = hints
        return hints

    def list_tools(self) -> list[dict]:
        """List tools from MCP server in OpenAI format. Uses cache."""
        try:
            start = time.perf_counter()
            tools = asyncio.run(_async_list_tools(self.url, self.api_key))
            elapsed = time.perf_counter() - start
            logger.info("MCP list_tools: %d tools in %.1fs", len(tools), elapsed)
            self._tools_cache = tools
            return tools
        except Exception as e:
            logger.warning("MCP list_tools failed: %s", e)
            if self._tools_cache:
                return self._tools_cache
            raise

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        """Call a tool on the MCP server. Returns result text."""
        results = self.call_tools_batch([(name, arguments or {})])
        return results[0] if results else ""

    def call_tools_batch(
        self, calls: list[tuple[str, dict[str, Any]]]
    ) -> list[str]:
        """Execute multiple tool calls in one MCP connection. Much faster than N separate calls."""
        if not calls:
            return []
        try:
            start = time.perf_counter()
            results = asyncio.run(
                _async_call_tools_batch(self.url, self.api_key, calls)
            )
            elapsed = time.perf_counter() - start
            names = ", ".join(n for n, _ in calls)
            logger.info("MCP call_tools_batch [%s]: %d calls in %.1fs", names, len(calls), elapsed)
            return results
        except Exception as e:
            logger.warning("MCP call_tools_batch failed: %s", e)
            return [f"Tool call failed: {e}"] * len(calls)
