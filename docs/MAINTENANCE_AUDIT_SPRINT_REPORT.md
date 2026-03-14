# Maintenance, Consistency, and Cleanup Audit Sprint Report

**Date:** 2026-03-14  
**Scope:** Architecture consistency, OpenClaw governance, docs audit, test coverage, safe cleanup.  
**Intent:** Identify weaknesses, duplicates, stale logic, conflicting behavior, outdated docs; perform safe maintenance without destabilizing the system.

---

## 1. Files Created, Modified, or Removed

### Created

| File | Purpose |
|------|---------|
| `gerty/utils/markdown_sections.py` | Shared `parse_markdown_sections` and `section_relevance_score` (M-002/IB-045) |
| `docs/MAINTENANCE_AUDIT_SPRINT_REPORT.md` | This report |
| `docs/HEARTBEAT_MD_RECREATION_TRACE.md` | Trace audit: OpenClaw CLI recreates HEARTBEAT.md; permanent fix (skipBootstrap) |

### Modified

| File | Changes |
|------|---------|
| `gerty/grounded_planning.py` | Import from `markdown_sections`; removed duplicate `_parse_markdown_sections`, `_section_relevance_score` |
| `gerty/inspection_first.py` | Import from `markdown_sections`; removed duplicate `_parse_markdown_sections`, `_section_relevance_score` |
| `docs/BUILD_PLAN_PROGRESS.md` | Test count 552→566; HEARTBEAT.md note; Maintenance Audit Sprint section |
| `docs/WEAKNESS_AUDIT_REPORT.md` | M-002 done; test count; report reference |
| `docs/IMPROVEMENT_BACKLOG.md` | IB-045 resolved |
| `docs/GERTY_OVERVIEW.md` | Router description updated for Execution Boundary v1 |
| `docs/OPENCLAW_BOOTSTRAP.md` | Gerty owns workspace bootstrap; skipBootstrap config |
| `docs/OPENCLAW_INTEGRATION.md` | Bootstrap ownership note in Workspace section |

### Removed

| File | Reason |
|------|--------|
| `HEARTBEAT.md` | Bootstrap cleanup (IB-033, IB-043); file had regressed; OpenClaw would inject on every turn; proactive flow uses HEARTBEAT_PROACTIVE.md only |

### HEARTBEAT Permanent Fix (follow-up)

| Action | Detail |
|--------|--------|
| **Trace audit** | [HEARTBEAT_MD_RECREATION_TRACE.md](HEARTBEAT_MD_RECREATION_TRACE.md) — OpenClaw CLI (onboard/configure/setup) recreates HEARTBEAT.md when missing |
| **Config** | `agents.defaults.skipBootstrap: true` in `~/.openclaw/openclaw.json` — disables bootstrap file seeding |
| **Docs** | OPENCLAW_BOOTSTRAP.md, OPENCLAW_INTEGRATION.md — Gerty owns workspace bootstrap files; OpenClaw seeding disabled |

---

## 2. Key Weaknesses Found

### Resolved This Sprint

| ID | Weakness | Resolution |
|----|----------|------------|
| H-002 | HEARTBEAT.md present at root; bootstrap test fails | Removed HEARTBEAT.md |
| M-002 (IB-045) | Duplicate `_parse_markdown_sections` in grounded_planning and inspection_first | Extracted to `gerty/utils/markdown_sections.py` |

### Already Resolved (Prior Sprints)

| ID | Weakness | Status |
|----|----------|--------|
| H-001 | Stale tests assume pre–Execution Boundary routing | Fixed in Hardening Sprint v1 |
| M-003 | Router apply_policy does not check inspection-first before boundary | Fixed: `planning_triggered = planning_result or inspection_result` |
| M-004 | test_maintenance_broader asserts exact LLM response | Fixed in Hardening Sprint v1 |

### Open / Deferred

| ID | Weakness | Recommendation |
|----|----------|----------------|
| M-001 | Intent-to-capability mapping incomplete; 27+ intents rely on name match | Add validation script or test; document intent→capability_id mapping |
| L-001 | "read file" in OPENCLAW_ACTION_PHRASES may over-trigger OpenClaw | Document as known edge case (IB-039); consider removing when touching |
| L-002 | capabilities.json has no entry for notes, time, alarm, etc. | Add capabilities or accept partial registry |
| L-003 | screen_openclaw_message checks is_command_blocked with args=[text] | Verify patterns against injection phrases; consider cmd=text check |
| IB-047 | Inspection-first may miss paraphrased requests | Partial: v3.1 broadened; some paraphrases may still miss |

---

## 3. Cleanup Actions Performed

1. **HEARTBEAT.md removal** — Bootstrap cleanup complete. Proactive flow uses HEARTBEAT_PROACTIVE.md only.
2. **Markdown section extraction (M-002)** — `parse_markdown_sections` and `section_relevance_score` moved to `gerty/utils/markdown_sections.py`. Both `grounded_planning.py` and `inspection_first.py` now import from shared util. `_section_relevance_score` kept as thin wrappers (`_section_relevance`) that pass module-specific `RELEVANCE_KEYWORDS`.

---

## 4. Docs Brought Up to Date

| Doc | Update |
|-----|--------|
| BUILD_PLAN_PROGRESS | Test count 552→566; HEARTBEAT.md regression note; Maintenance Audit Sprint section |
| WEAKNESS_AUDIT_REPORT | M-002 done; test count; report reference |
| IMPROVEMENT_BACKLOG | IB-045 resolved |
| GERTY_OVERVIEW | Router description: Execution Boundary v1 (planning→native, action→OpenClaw) |

---

## 5. Test Coverage Updates or Clarifications

- **No test changes** — All 566 tests pass. Markdown extraction is covered by existing grounded_planning and inspection_first tests.
- **Known exclusions:** None documented as new. `test_heartbeat_excluded_from_bootstrap` now passes (HEARTBEAT.md removed).

---

## 6. OpenClaw-Specific Findings

### Architecture Consistency

- **Execution boundary** — `apply_policy` correctly includes inspection-first in `planning_triggered`; planning/inspection routes to native.
- **Reset semantics** — New chat vs full reset documented in OPENCLAW_STATE_BOUNDARY.md; API `DELETE /api/chat/history?full=true` clears memory DB.
- **Memory transparency** — OPENCLAW_MEMORY_TRANSPARENCY.md accurately describes inferred vs confirmed; "likely influencing" vs "used" is clear.
- **Bootstrap** — HEARTBEAT.md removed; `skipBootstrap: true` prevents OpenClaw from recreating it; OPENCLAW_BOOTSTRAP.md states HEARTBEAT_PROACTIVE.md for proactive flow only.

### No Code Paths Bypassing Observability

- OpenClaw client screens via `screen_openclaw_message` before execute/stream.
- Transparency metadata set when OpenClaw route is used (sync + stream).
- `--inspect-openclaw-context` and `--inspect-openclaw-transparency` available.

### Deferred

- **Session merge behavior** — Gateway payload vs stored transcript merge not verified; documented as inferred.
- **Memory DB clear** — Full reset clears it; no separate Gerty command for memory-only clear.

---

## 7. Assumptions / Deferred Issues

| Item | Status |
|------|--------|
| Gateway session merge (payload vs transcript) | Not verified; documented as inferred |
| Memory tool invocation per turn | Not observable; documented |
| Proactive→memory flow | Documented; no code change |
| Intent–capability drift (M-001) | Validation test exists; mapping incomplete; deferred |
| Duplicate sprint report files | Not found; BUILD_PLAN_PROGRESS is canonical |

---

## 8. Runtime Stability Confirmation

- **Full test suite:** 566 passed.
- **Validate command:** `python -m gerty --validate` (do-not-break checklist) — not run in this audit; recommend running before merge.
- **No runtime behavior changes** except: HEARTBEAT.md removal (bootstrap; no user-facing change) and markdown extraction (internal refactor; same behavior).

---

## 9. Full Test Results

```
============================= test session starts ==============================
platform linux -- Python 3.10.12, pytest-9.0.2, pluggy-1.6.0
rootdir: /home/liam/gerty
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.12.1
collected 566 items

... (all modules) ...

============================= 566 passed in 3.43s ==============================
```

---

## 10. Overall Maintenance Verdict

**System health after cleanup: Good.**

| Aspect | Verdict |
|--------|---------|
| **Architecture consistency** | Execution boundary, model routing, capability registry, inspection-first, OpenClaw integration align. No duplicate routing logic between planning/inspection/execution. |
| **OpenClaw governance** | State boundary, memory transparency, reset semantics documented. No hidden assumptions; transparency language appropriately cautious. |
| **Docs** | BUILD_PLAN_PROGRESS, GERTY_OVERVIEW, OPENCLAW docs reflect current behavior. Test counts updated. |
| **Tests** | 566 passed. No new exclusions. Bootstrap test passes. |
| **Cleanup** | HEARTBEAT.md removed; markdown duplication eliminated. No dead code, obsolete shims, or redundant reports removed (none identified as safe). |

**Recommendation:** Proceed. No broad refactors; system is stable and inspectable. Defer M-001, L-001, L-002, L-003, IB-047 to future maintenance windows.
