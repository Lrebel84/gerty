# Runtime Stabilization & Governance Lockdown — Milestone Recap

**Date:** 2026-03-15  
**Status:** Complete  
**Scope:** OpenClaw runtime governance, model lock, memory reset, last-mile model leak fix.

---

## Summary

A major stabilization and governance effort was completed across the Gerty system and OpenClaw runtime. OpenClaw now operates as a controlled execution layer under Gerty governance. All runtime paths use a single model (GPT-OSS-120B). Legacy autonomous behavior has been disabled or removed.

---

## Governance Changes

### OpenClaw Runtime Governance

| Change | Description |
|--------|-------------|
| **Autonomous agents disabled** | proactive-agent, self-improving-agent skills renamed to .disabled |
| **Proactive cron removed** | System crontab no longer runs proactive-heartbeat every 4h |
| **Subagent spawning disabled** | agents.defaults.subagents.maxConcurrent = 0 |
| **openrouter/auto removed** | OpenClaw models restricted to openai/gpt-oss-120b only |
| **Memory DB cleared** | Legacy OpenClaw memory DB archived and reset |
| **Session transcripts cleared** | OpenClaw sessions archived; new sessions start clean |
| **Proactive memory archived** | MEMORY.md, memory/*.md, proactive-updates.md archived |

### Model Lock

**Target model:** `openai/gpt-oss-120b` (OpenRouter format: provider/model)

All runtime paths now use this model. Sources aligned:

| Source | Fix |
|--------|-----|
| openrouter/auto | Removed from OpenClaw config |
| model_profiles.json | All profiles → openai/gpt-oss-120b |
| Router fallback | Web intent fallback aligned |
| OpenClaw config | primary + models locked |
| UI persisted setting | Overridden at load; save validation rejects non-OSS |
| .env | OPENROUTER_MODEL aligned |

---

## Model Leak Root Cause and Fix

### Root Cause

**Source:** `data/settings.json` → `openrouter_model: "x-ai/grok-4.1-fast"`

The UI persists the user's model selection. When provider is "openrouter", the router used `settings.get("openrouter_model") or OPENROUTER_MODEL`. The persisted value overrode config defaults, causing Grok to be used for all OpenRouter chat.

### Fix Implemented

1. **LOCKED_OPENROUTER_MODEL** — Constant in config; router always uses it for OpenRouter paths
2. **Settings load override** — `load()` always returns LOCKED_OPENROUTER_MODEL for openrouter_model
3. **Settings save validation** — Never persist non-OSS openrouter_model
4. **Router enforcement** — Ignores mutable UI settings; uses LOCKED_OPENROUTER_MODEL

### Model ID Correction

OpenRouter uses `openai/gpt-oss-120b` (not `openrouter/openai/gpt-oss-120b`). Corrected 2026-03-15.

---

## Memory Reset Process

1. **Session state** — Archived to `docs/archive/openclaw_sessions_pre_lockdown/`; cleared
2. **Memory DB** — Archived to `docs/archive/openclaw_memory_db_pre_lockdown/`; removed
3. **Workspace memory** — MEMORY.md, memory/*.md archived; fresh versions created
4. **Proactive output** — proactive-updates.md archived to `docs/archive/proactive_agent_history/`

See [OPENCLAW_POST_LOCKDOWN_RESET.md](OPENCLAW_POST_LOCKDOWN_RESET.md).

---

## Architecture State Snapshot

### Gerty Core

- **Model Routing v1** — Task-type-based model selection
- **Execution Boundary v1** — Planning/reasoning → native; action-heavy → OpenClaw when enabled
- **Capability Registry** — Canonical capability map, native vs OpenClaw ownership
- **Grounded Planning Mode** — Strategic requests get project-state context
- **Inspection-First Planning Mode** — Review/audit requests inspect docs before answering
- **Diagnostics and governance checks** — `--diagnose`, `--governance`, `--validate`

### OpenClaw Integration

OpenClaw now acts strictly as:

- **Bounded tool execution layer**
- **Responsibilities:** tool execution, external integrations, controlled reasoning paths

**Not allowed:**

- Autonomous agents
- Background research
- Persistent uncontrolled memory
- Model auto-selection

---

## Current System Health

- Build plan complete through Sprint 11 (Lockdown v1)
- 566+ tests passing
- Runtime governance checks passing
- Model lock verified (openai/gpt-oss-120b)
- OpenClaw runtime stable
- No multi-model leakage detected (OpenRouter logs confirm)

---

## Lessons Learned

### 1. Model governance must override UI settings

Persisted UI configuration can override runtime model locks if not explicitly controlled. Settings load/save must enforce the locked model.

### 2. Autonomous agent platforms require strict governance

OpenClaw defaults favor autonomy (agents, cron, research). For Gerty's architecture, OpenClaw must remain a controlled execution layer.

### 3. Runtime transparency is essential

The ability to inspect OpenClaw context, memory influence, and session metadata proved critical for diagnosing system behavior.

### 4. Logs are the source of truth

Model self-reporting is unreliable. OpenRouter logs were required to verify runtime model usage.

---

## Next Development Phase: Response Quality Hardening

Now that runtime governance is stable, the next work should focus on assistant quality improvements.

**Primary goals:**

- Improve factual precision in architecture explanations
- Reduce mechanical repetition of backlog items
- Improve contextual adaptation in assistant responses
- Strengthen distinction between documented facts and inferred recommendations
- Remove outdated terminology (e.g. references to Grok modules)
- Improve system-introspection responses (model, memory, architecture questions)

**Important:** Do not change runtime architecture during this phase. Focus only on improving assistant reasoning quality and contextual awareness.

---

## Related Documents

- [OPENCLAW_RUNTIME_GOVERNANCE_AUDIT.md](OPENCLAW_RUNTIME_GOVERNANCE_AUDIT.md) — Audit findings
- [OPENCLAW_LOCKDOWN_V1_REPORT.md](OPENCLAW_LOCKDOWN_V1_REPORT.md) — Lockdown implementation
- [OPENCLAW_POST_LOCKDOWN_RESET.md](OPENCLAW_POST_LOCKDOWN_RESET.md) — Memory reset
- [LAST_MILE_MODEL_LEAK_AUDIT.md](LAST_MILE_MODEL_LEAK_AUDIT.md) — Model leak fix
