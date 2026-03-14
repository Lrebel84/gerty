# Build Plan Progress

> **Purpose:** Record progress through the Gerty Build Plan so work can be paused and resumed. Read this first when picking up.

**Last updated:** 2026-03-13  
**Branch:** `stabilize/openclaw-foundation`  
**Next sprint:** 3 (OpenClaw Workspace Formalization)

---

## Quick status

| Sprint | Status | Notes |
|--------|--------|------|
| 0 | ✅ Done | Baseline docs, branch |
| 1a | ✅ Done | Path hardening, secrets |
| 1b | ✅ Done | Config, diagnostics, `--diagnose` |
| 1c | ✅ Done | Google Workspace diagnostics, empty-output handling |
| 1d | ✅ Done | GERTY_WORKSPACE, portable calendar path, verify script |
| 2a | ✅ Done | Intent constants, RoutingDecision, pure classifier |
| 2b | ✅ Done | Policy layer, execution layer, classify→policy→execute |
| 2c | ✅ Done | Result validation, payload construction, fallback pattern |
| 3 | ⏳ Next | OpenClaw workspace formalization |
| 4–10 | Pending | — |

---

## How to pick up

1. **Read** `docs/BUILD_PLAN_SPRINTS.md` — full sprint breakdown
2. **Read** `docs/BUILD_PLAN_PROGRESS.md` (this file) — current status
3. **Read** `memory/YYYY-MM-DD.md` and `MEMORY.md` — recent context
4. **Run** `pytest tests/test_router.py tests/test_openclaw.py -q` — verify 2a/2b/2c
5. **Start** Sprint 3 tasks (see BUILD_PLAN_SPRINTS.md § Sprint 3)

---

## Completed work (summary)

### Sprints 0–1d (prior sessions)

- Branch `stabilize/openclaw-foundation`
- `docs/BASELINE_BEHAVIOR.md`, `docs/ARCHITECTURE_CURRENT.md`
- Path hardening, `GOOGLE_TOKEN_PATH`, config boundary
- `--diagnose`, `scripts/check_google_workspace.sh`, `scripts/verify_calendar_openclaw.sh`
- `GERTY_WORKSPACE`, portable skills, empty-output hints

### Sprint 2a (committed: af07eff)

- `INTENT_*` constants, `RoutingDecision`, `_classify_intent_impl`, `classify_to_decision`
- 44 tests; calendar vs app-integration fixed

### Sprint 2b (this session)

- `apply_policy()`, `_execute_route()`, `_execute_route_stream()`
- Flow: classify → apply_policy → execute
- 7 policy tests; 51 router tests total

### Sprint 2c (this session)

- `gerty/openclaw/validation.py` — `validate_openclaw_response()`
- `build_openclaw_payload()`, fallback pattern doc
- 13 OpenClaw tests; 64 total

---

## Commits (build plan work)

```
af07eff Sprint 2a: Intent classification (router split)
8a53c85 Sprint 1a: path hardening and secret handling
```

Sprint 2b and 2c changes are not yet committed.

---

## Do-not-break checklist (validate after changes)

1. Local chat must still function
2. Voice must still function
3. Fast-path tools must still function
4. Chat UI must still function
5. OpenClaw disabled mode must still function
6. OpenClaw enabled but unavailable mode must still function
7. OpenClaw enabled and reachable mode must still function
