# OpenClaw Memory Transparency

> Shared memory across Gerty and OpenClaw is intentional. This doc explains how memory influence is made transparent and inspectable.

## Intent

Gerty supports shared memory across the system, including OpenClaw-side memory and proactive memory. This memory **may influence ordinary chat**. The system is designed so that:

- Shared memory influence is **visible**
- Memory sources are **attributable**
- Chat context is **distinguished** from persistent/shared memory context
- Proactive-memory influence is **explicit**
- Trust and debuggability are improved without changing core assistant behavior

## Memory Source Categories

| Category | Description |
|----------|-------------|
| `current_chat` | The current user message / current turn |
| `gerty_chat_history` | Gerty-managed conversation history (passed in payload) |
| `openclaw_session` | OpenClaw session transcript state |
| `bootstrap_memory` | Bootstrap-injected files (MEMORY.md, memory/*.md) |
| `proactive_memory` | Memory content recently modified by proactive/cron flows (Lockdown v1: proactive disabled) |
| `openclaw_memory_db` | Persistent OpenClaw memory tool state |
| `unknown_or_unverified` | Memory influence suspected but not confirmed |

## What Can Be Confirmed vs Inferred

### Confirmed (state present)

- **Session transcript exists** — We can check `~/.openclaw/agents/main/sessions/*.jsonl`
- **Memory DB exists** — We can check `~/.openclaw/memory/main.sqlite`
- **MEMORY.md exists** — We can check workspace file
- **memory/*.md files exist** — We can list the directory
- **Proactive files recently modified** — We can check mtime within 24h

### Inferred (likely influence)

- **Bootstrap memory used** — OpenClaw injects these files on every request; we infer use when they exist
- **Proactive memory used** — When bootstrap memory files were recently modified, proactive agent may have written
- **OpenClaw session used** — When transcript exists, gateway may merge it with payload (behavior not verified)
- **OpenClaw memory DB used** — When it exists, the memory tool may have been queried (not observable)

### Not verifiable

- Actual model attention to bootstrap content
- Whether memory tool was invoked in a given turn
- Gateway session merge behavior (payload vs stored transcript)

## How to Inspect Memory Influence

### CLI

```bash
# Context inspection (boundary, session, memory DB, bootstrap, proactive)
python -m gerty --inspect-openclaw-context

# Transparency report (likely influence, unknowns)
python -m gerty --inspect-openclaw-transparency
```

### API

**GET /api/chat/history/state?include_openclaw=true**

Returns `openclaw_context.transparency` with:
- `memory_influence_detected`
- `memory_sources_used`
- `bootstrap_memory_used`
- `proactive_memory_used`
- `recent_memory_file_updates`
- `state_present`
- `unknowns`

**GET /api/chat/last-reply-metadata**

Returns memory influence metadata for the last OpenClaw-routed reply. Developer/diagnostics only. Includes:
- `memory_influence_detected`
- `memory_sources_used`
- `bootstrap_memory_used`
- `proactive_memory_used`
- `openclaw_session_used`
- `openclaw_memory_db_present`
- `recent_memory_file_updates`
- `transparency_notes`

### Programmatic

```python
from gerty.openclaw.context_inspect import inspect_openclaw_context, build_transparency_report
from gerty.openclaw.transparency import compute_memory_influence_metadata, get_last_reply_metadata

ctx = inspect_openclaw_context()
report = build_transparency_report(ctx, history_included=True)
meta = compute_memory_influence_metadata(ctx, history_included=True)
last_meta = get_last_reply_metadata()
```

## Proactive Memory Visibility

When MEMORY.md or memory/*.md were updated within the last 24 hours, the system reports:

- `proactive_memory_used: true`
- `recent_memory_file_updates` with file names and dates
- A transparency note: "Proactive/cron may have recently updated bootstrap memory files."

This makes it clear that bootstrap memory may include content written by the proactive agent (cron/heartbeat), which can influence normal chat.

## Limitations

1. **Attribution is inferred** — We infer from context state; actual model usage is not observable.
2. **No semantic attribution** — We cannot say which specific fact in a reply came from which source.
3. **Last-reply metadata is process-scoped** — Cleared on restart; not persisted.
4. **Gateway behavior** — OpenClaw gateway session merge is not verified.

## Post-Lockdown Memory State (2026-03-15)

After the Runtime Stabilization Milestone, memory state was reset to a known baseline:

| Component | State |
|-----------|-------|
| OpenClaw session transcripts | Cleared (archived to `~/.openclaw/agents/main/sessions/archive/`) |
| OpenClaw memory DB | Cleared (`main.sqlite` reset) |
| Workspace memory (MEMORY.md, memory/*.md) | Proactive artifacts archived; baseline retained |
| Proactive output | Archived to `memory/proactive-archive/` |

Inspection tools (`--inspect-openclaw-context`, `--inspect-openclaw-transparency`) reflect this cleared state. Proactive/cron flows remain disabled, so `proactive_memory_used` will not be set by new writes until proactive is re-enabled.

See [RUNTIME_STABILIZATION_MILESTONE.md](RUNTIME_STABILIZATION_MILESTONE.md) for full governance and reset details.

## Related Docs

- [OPENCLAW_STATE_BOUNDARY.md](OPENCLAW_STATE_BOUNDARY.md) — Reset semantics, boundary classification
- [OPENCLAW_PERSISTENCE_AUDIT.md](OPENCLAW_PERSISTENCE_AUDIT.md) — Full audit of persistent state
- [OPENCLAW_BOOTSTRAP.md](OPENCLAW_BOOTSTRAP.md) — Bootstrap memory influence
- [RUNTIME_STABILIZATION_MILESTONE.md](RUNTIME_STABILIZATION_MILESTONE.md) — Post-lockdown governance and memory reset
