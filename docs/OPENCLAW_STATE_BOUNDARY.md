# OpenClaw State Boundary

> Explicit boundary between Gerty-managed state, OpenClaw-managed state, and shared workspace files.
> See [OPENCLAW_PERSISTENCE_AUDIT.md](OPENCLAW_PERSISTENCE_AUDIT.md) for the full audit.
> For memory influence transparency, see [OPENCLAW_MEMORY_TRANSPARENCY.md](OPENCLAW_MEMORY_TRANSPARENCY.md).

## Quick Reference

| Owner | Location | Cleared by New chat? |
|-------|----------|---------------------|
| **Gerty** | `data/chat_history.json` | Yes |
| **Gerty** | OpenClaw session transcript (`agent:main:gerty`) | Yes |
| **OpenClaw** | `~/.openclaw/memory/main.sqlite` | No |
| **Shared** | `MEMORY.md`, `memory/*.md` (workspace) | No |

## Reset Semantics

### New chat (default)

**What it does:**
- Clears `data/chat_history.json` (Gerty chat history)
- Calls `sessions_reset(agent:main:gerty)` (OpenClaw session transcript)

**What it does NOT do:**
- Does not clear OpenClaw memory DB (`~/.openclaw/memory/main.sqlite`)
- Does not modify `MEMORY.md` or `memory/*.md`
- Does not clear proactive-agent outputs

**Trigger:** User clicks "New chat" in UI → `DELETE /api/chat/history`

### Full reset

**What it does:**
- Everything from New chat, plus:
- Deletes OpenClaw memory DB (if it exists)

**What it does NOT do:**
- Does not modify `MEMORY.md` or `memory/*.md` (those live in workspace; user must edit manually)

**Trigger:** `DELETE /api/chat/history?full=true` (user must explicitly request)

## Bootstrap Memory Influence

OpenClaw injects these files from the workspace on **every** request (including normal Gerty chat):

- `MEMORY.md` — long-term memory template
- `memory/*.md` — daily notes (possibly; see audit)

**Critical:** Gerty does not send these files. OpenClaw reads them from disk. Any process that writes to these files influences subsequent chat.

**Lockdown v1 (2026-03-15):** Proactive cron and proactive-agent skill are disabled. No automatic writes to MEMORY.md or memory/*.md from proactive flows. See [OPENCLAW_LOCKDOWN_V1_REPORT.md](OPENCLAW_LOCKDOWN_V1_REPORT.md).

### Proactive → memory → normal chat flow (legacy; now disabled)

1. ~~Cron runs `scripts/proactive-heartbeat.sh` → OpenClaw proactive agent~~
2. ~~Proactive agent (per HEARTBEAT_PROACTIVE.md) may update MEMORY.md, memory/*.md, notes/areas/proactive-updates.md~~
3. `MEMORY.md` and `memory/*.md` are in the bootstrap set
4. Next normal Gerty chat gets them injected by OpenClaw
5. **Result (when proactive was active):** Proactive agent's writes could make Gerty appear to "remember" things from a prior cron run. **Lockdown v1:** Proactive disabled; no automatic writes.

**Visibility:** Run `python -m gerty --inspect-openclaw-context` to see:
- Whether MEMORY.md / memory/*.md exist and when they were last modified
- Whether proactive-related files were recently updated

## Inspect Command

```bash
python -m gerty --inspect-openclaw-context
```

Reports:
- Session transcript presence and size
- Memory DB existence and size
- Bootstrap memory files (MEMORY.md, memory/*.md) and modification times
- Proactive-related files recently modified (24h)
- Boundary classification (Gerty-owned vs OpenClaw-owned vs shared)

## API

### DELETE /api/chat/history

- `?full=false` (default): New chat — Gerty history + OpenClaw session
- `?full=true`: Full reset — also clears OpenClaw memory DB

Response includes `reset_report` with `cleared` and `not_cleared` lists when OpenClaw is enabled.

### GET /api/chat/history/state?include_openclaw=true

Returns OpenClaw context summary:
- `proactive_recently_modified`: Files modified in last 24h
- `memory_db_exists`: Whether OpenClaw memory DB exists
- `notes`: Boundary notes

## Limits of "New chat"

- User may expect "New chat" to reset all context. It does not.
- OpenClaw memory DB, MEMORY.md, and memory/*.md persist.
- Document this in UI tooltips or help if possible.

## Shared Memory Is Intentional

Shared memory (bootstrap, proactive, session) may influence ordinary chat. This is by design. The system reports likely memory influence for transparency. Run `python -m gerty --inspect-openclaw-transparency` or see [OPENCLAW_MEMORY_TRANSPARENCY.md](OPENCLAW_MEMORY_TRANSPARENCY.md).
