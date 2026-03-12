# MCP (Rube/Composio) Integration – Status and Failure Report

**Archived – MCP removed; OpenClaw handles app integrations.** See [docs/OPENCLAW_INTEGRATION.md](../OPENCLAW_INTEGRATION.md).

**Last updated:** 2025-03-08

**Bottom line:** MCP routing fixed. Calendar/Gmail/Drive queries now reach MCP. MCP tool calls use **OpenRouter Grok 4.1 Fast** (`OPENROUTER_MCP_MODEL`) – local LLMs are unreliable for tool orchestration.

**OpenClaw bypass:** When `GERTY_OPENCLAW_ENABLED=1`, MCP is bypassed. Calendar, Gmail, Drive, Tasks requests go to OpenClaw instead. OpenClaw handles app integrations better and is less temperamental. See [docs/OPENCLAW_INTEGRATION.md](OPENCLAW_INTEGRATION.md).

**⚠️ Performance:** Enabling MCP has slowed regular voice chat significantly (from a few seconds to 10–15s per reply). Likely causes: MCP tools loaded on every request, schema checks, or routing overhead. Consider `GERTY_MCP_ENABLED=0` or `GERTY_OPENCLAW_ENABLED=1` if voice latency is critical.

---

## How MCP Is Set Up

### Architecture (Current)

```
User: "What's in my Google Calendar for tomorrow?" / "Check my latest three emails"
    │
    ▼
Router (gerty/llm/router.py)
    │
    ├─ classify_intent() → "chat" (MCP_APP_KEYWORDS: calendar, emails, gmail, drive, tasks)
    │
    ├─ GERTY_WEB_INTENT_FALLBACK: SKIPPED when MCP_APP_KEYWORDS match
    │
    ├─ MCP tools loaded, batch executor wrapped with calendar-args fix
    │
    └─ OpenRouter (Grok 4.1 Fast) + MCP tool loop
        └─ RUBE_SEARCH_TOOLS → RUBE_MULTI_EXECUTE_TOOL
        └─ Wrapper injects time_min/time_max when LLM passes empty args
        └─ Summarize for user
```

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| MCP Client | `gerty/mcp/client.py` | Connects to Rube at `https://rube.app/mcp`, lists tools, calls tools |
| Router | `gerty/llm/router.py` | Classifies intent, routes to tools or LLM |
| MCP Keywords | `MCP_APP_KEYWORDS` in router.py | "google calendar", "my calendar", "emails", "check emails", "gmail", "drive", "tasks" – route to chat with MCP |
| Config | `gerty/config.py` | `COMPOSIO_API_KEY`, `GERTY_MCP_ENABLED`, `RUBE_MCP_URL`, etc. |

### Config Required

- `COMPOSIO_API_KEY` – Signed token from [rube.app/settings/api-keys](https://rube.app/settings/api-keys)
- `OPENROUTER_API_KEY` – Required for MCP tool loop (Grok 4.1 Fast)
- `OPENROUTER_MCP_MODEL` – Default `x-ai/grok-4.1-fast`; local LLMs often fail at tool calling
- Apps connected in Rube (Google Calendar, Gmail, etc.)

---

## What Was Attempted

### Attempt 1: Original Implementation (CHANGELOG 0.8.29)

- MCP client with streamable HTTP
- `MCP_APP_KEYWORDS` routing
- Groq Remote MCP (server-side)
- Local tool loop via OpenRouter/Ollama

**Result:** Unusably slow. Each `call_tool` = new connection (~15–20s). Groq Remote MCP hit token limits (413). User saw "Using tools" loop for minutes.

### Attempt 2: Groq Disabled for MCP

- Set `GERTY_MCP_GROQ_FIRST=0` in `.env`
- Intended to skip Groq and use OpenRouter directly

**Result:** No change. MCP still not reached.

### Attempt 3: Batch Tool Execution

- Added `call_tools_batch()` – one MCP connection per round instead of per tool
- Added `batch_tool_executor` to OpenRouter and Ollama clients
- Reduced `GERTY_MCP_MAX_TOOL_ROUNDS` from 10 to 5
- Added round progress: "Using tools (round 1/5)..."

**Result:** No change. MCP still not reached. Batch optimization never runs because MCP path is never taken.

---

## Root Cause: Why MCP Is Never Called

### The Bug

**`GERTY_WEB_INTENT_FALLBACK`** (default: 1) runs when `classify_intent()` returns `"chat"`. It asks an LLM: "Does this need web lookup, web research, or no_web?"

For **"What's in my Google Calendar for tomorrow?"**:

1. `classify_intent()` correctly returns `"chat"` (matches `MCP_APP_KEYWORDS`: "google calendar")
2. Web intent fallback runs
3. The LLM sees "what's in" + "for tomorrow" and classifies as `web_lookup`
4. Intent is overwritten to `"search"`
5. Router goes to search block → `quick_search()` → "Searching..."
6. **MCP block is never reached**

### Code Path (router.py)

```python
# Line 326-335 (route) and 422-431 (route_stream)
intent = classify_intent(message)

if intent == "chat" and GERTY_WEB_INTENT_FALLBACK:
    fallback = _classify_web_intent_fallback(message, ...)
    if fallback == "web_lookup":
        intent = "search"   # ← MCP calendar query gets hijacked here
    elif fallback == "web_research":
        intent = "research"

# ... later ...
if intent == "search":
    yield "Searching..."
    # MCP never reached
```

### Why This Wasn't Caught

- MCP_APP_KEYWORDS correctly match "google calendar"
- The bug is in the *fallback* that runs *after* keyword classification
- Fallback was added for "ambiguous" chat queries (e.g. "what's the latest news about AI?")
- No exclusion for MCP app queries – calendar/Gmail/Drive get misclassified as web lookup

---

## Fixes Applied (2025-03-08)

### 1. Web intent fallback

**Skip the web intent fallback when the message matches MCP_APP_KEYWORDS.**

Calendar, Gmail, Drive, and Tasks queries are no longer reclassified as search. They now go to the MCP path.

Change in `router.py` (route and route_stream): wrap the fallback in `if not any(kw in message.lower() for kw in MCP_APP_KEYWORDS)` so MCP app queries never reach the web intent classifier.

### 2. OpenRouter Grok 4.1 Fast for MCP

**MCP tool calls always use OpenRouter with `OPENROUTER_MCP_MODEL` (default: `x-ai/grok-4.1-fast`).**

Local LLMs (Ollama) are unreliable for tool orchestration – they often fail to call tools correctly or loop indefinitely. The router now:

- Tries OpenRouter + Grok 4.1 Fast first for MCP
- Falls back to Ollama only if OpenRouter fails
- Never uses the user's selected model for MCP (always the dedicated MCP model)

### 3. Root cause: GOOGLECALENDAR_EVENTS_LIST_ALL_CALENDARS requires time_min/time_max

**Debug finding (2025-03-08):** Grok was calling the calendar list tool with empty arguments. The Rube/Composio tool returns:

```
"Invalid request data provided - Following fields are missing: {'time_max', 'time_min'}"
```

Grok put the values in the "thought" field instead of in `tools[].arguments`, so Rube never received them. Fixes applied:

- **Rube schema injection:** We pre-fetch Rube's tool schemas via `RUBE_SEARCH_TOOLS` and inject them into the MCP system prompt. The LLM now sees exactly what Rube expects (required params, descriptions, examples).
- **Calendar args fix wrapper:** The LLM often puts `time_min`/`time_max` in the "thought" field instead of `tools[].arguments`. We wrap the MCP batch executor to intercept calls to `GOOGLECALENDAR_EVENTS_LIST_ALL_CALENDARS` with empty arguments, infer the time range from the user message (and optionally the LLM's thought), and inject the correct params. This lets the LLM handle arbitrary queries—"tomorrow", "this week", "next Tuesday", etc.—without hardcoding each one.
- **Fallback when max rounds hit:** If the tool loop exits with no final text, we make one more request without tools asking the model to summarize what happened.

### 4. Email routing

**"Check my latest three emails"** was routing to browse (BROWSE_KEYWORDS "check my") instead of MCP. Added "emails", "check emails", "latest emails", "read my email", "read my emails" to `MCP_APP_KEYWORDS` so email queries reach MCP before browse.

### 5. "This week" on weekend

On Saturday or Sunday, "this week" now means the **upcoming week** (Mon–Sun starting next Monday), not the week ending today.

### 6. Calendar-only speedup

Skip schema pre-fetch for calendar-only queries (no Gmail/Drive/Tasks). Saves ~5–10s since the wrapper fixes args anyway.

---

## Summary

| Component | Status |
|-----------|--------|
| Routing | Fixed – MCP_APP_KEYWORDS, web fallback skip, email vs browse |
| Tool loop | OpenRouter Grok 4.1 Fast, batch executor |
| Calendar | Args wrapper injects time_min/time_max from user message |
| Gmail/Drive/Tasks | Schema hints, routing; may need similar wrappers if param issues arise |
