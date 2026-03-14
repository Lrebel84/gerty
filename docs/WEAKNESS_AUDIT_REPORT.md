# Gerty Weakness Audit Report

**Date:** 2026-03-14  
**Scope:** Bounded audit of routing, prompts, grounding, capability layer, Google Workspace ownership, tests, safety, and maintainability.  
**Intent:** Identify weaknesses, drift, and hardening priorities. No major refactors.

---

## Fixes Applied (Hardening Sprint v1 + Inspection-First v2)

| ID | Status |
|----|--------|
| H-001 (IB-042) | ✅ Done — 8 tests updated for Execution Boundary; OpenClaw-required messages used when asserting OpenClaw path |
| H-002 (IB-043) | ✅ Done — HEARTBEAT.md removed; regression fix 2026-03-14 (file reappeared, removed again) |
| M-001 | Partial — `test_intent_capability_mapping_coverage` added; mapping still incomplete for 27+ intents |
| M-002 (IB-045) | ✅ Done — Extracted to gerty/utils/markdown_sections.py (Maintenance Audit Sprint 2026-03-14) |
| M-003 (IB-044) | ✅ Done — inspection-first included in `planning_triggered` via `inspection_result` |
| M-004 (IB-046) | ✅ Done — maintenance test decoupled from exact LLM output |
| IB-047 | Partial — Inspection-First v2 broadened detection; some paraphrased requests may still miss |

**Tests:** 566 passed. See [HARDENING_SPRINT_V1_REPORT.md](HARDENING_SPRINT_V1_REPORT.md), [INSPECTION_FIRST_V2_REPORT.md](INSPECTION_FIRST_V2_REPORT.md), [MAINTENANCE_AUDIT_SPRINT_REPORT.md](MAINTENANCE_AUDIT_SPRINT_REPORT.md).

---

## 1. Executive Summary

### Overall Health Assessment

The Gerty codebase is **coherent but fragmented at the edges**. Core routing (classify → policy → execute), execution boundary, model routing, and capability registry are well-structured. Several areas show **architectural drift** from recent upgrades: tests assume pre–Execution Boundary behavior, bootstrap cleanup left a stale file, and intent-to-capability mapping is incomplete.

### Biggest Risks

1. **Stale tests masking behavior changes** — 8 failing tests; most reflect Execution Boundary v1 routing planning/chat to native instead of OpenClaw. Tests were not updated when the boundary was introduced.
2. **HEARTBEAT.md still present** — Bootstrap cleanup (IB-033) renamed to HEARTBEAT_PROACTIVE.md but HEARTBEAT.md was not removed; test expects it absent.
3. **Inspection-first can still miss paraphrased requests** — Deterministic phrase matching; "analyze our setup" or "what should we fix first" may not trigger inspection-first, yielding generic advice.
4. **Intent–capability drift** — Router has 30+ intents; `get_capability_for_intent` maps only 3 explicitly (calendar, search, research). Others rely on name match; new intents can return None.

### Immediate Priorities

1. Fix or update the 8 failing tests so CI reflects actual behavior.
2. Remove HEARTBEAT.md (or document why it remains) to satisfy bootstrap cleanup.
3. Update inspect-prompt and prompt-metrics tests for Execution Boundary routing.
4. Add validation or sync between router intents and capability registry.

---

## 2. Findings by Severity

### Critical

*None identified.* No security exploits, data loss paths, or blocking correctness bugs.

---

### High

#### H-001: Stale tests assume pre–Execution Boundary routing

| Field | Value |
|-------|-------|
| **ID** | H-001 |
| **Title** | Tests expect OpenClaw for chat/planning; Execution Boundary routes to native |
| **Severity** | high |
| **Area** | Testing, Routing |
| **Evidence** | `tests/test_prompt_metrics.py` (test_inspect_test_message_openclaw, test_inspect_planning_message_triggers_planning_mode, test_openclaw_path_logs_metrics, test_openclaw_path_writes_to_file); `tests/test_router.py` (test_openclaw_receives_history_and_system_context, test_fallback_to_gerty_when_openclaw_unavailable, test_maintenance_broader_routes_to_chat) |
| **Why it matters** | Tests assert `route == "openclaw"` for "test" and planning messages. With Execution Boundary v1, planning/chat goes to native. Tests fail; CI is red; behavior is correct but tests are wrong. |
| **Recommended fix** | Update tests to reflect Execution Boundary: when planning triggers or intent is chat, expect `route in ("local", "openrouter_direct")` unless intent requires OpenClaw. Mock execution path selection or use messages that explicitly route to OpenClaw (e.g. "check my calendar"). |
| **Fix now or later** | Now — unblocks CI and prevents false confidence. |

---

#### H-002: HEARTBEAT.md still exists; bootstrap test fails

| Field | Value |
|-------|-------|
| **ID** | H-002 |
| **Title** | HEARTBEAT.md present at root; bootstrap cleanup incomplete |
| **Severity** | high |
| **Area** | Bootstrap, Maintainability |
| **Evidence** | `ls -la /home/liam/gerty/HEARTBEAT*.md` shows both HEARTBEAT.md and HEARTBEAT_PROACTIVE.md. HEARTBEAT.md contains "Keep this file empty (or with only comments) to skip heartbeat API calls." `tests/test_bootstrap_cleanup.py::test_heartbeat_excluded_from_bootstrap` asserts `not (PROJECT_ROOT / "HEARTBEAT.md").exists()`. IB-033 marked done: "Renamed HEARTBEAT.md → HEARTBEAT_PROACTIVE.md" but HEARTBEAT.md was not removed. If HEARTBEAT.md is intentional (to skip OpenClaw heartbeat API calls), update the test instead of removing the file. |
| **Why it matters** | OpenClaw may still inject HEARTBEAT.md on every turn if it looks for that filename. Bootstrap bloat; test fails. |
| **Recommended fix** | Remove HEARTBEAT.md if it is a duplicate or stub. If it serves a different purpose, document and update the test. |
| **Fix now or later** | Now — trivial fix. |

---

### Medium

#### M-001: Intent-to-capability mapping incomplete; drift risk

| Field | Value |
|-------|-------|
| **ID** | M-001 |
| **Title** | get_capability_for_intent maps only 3 intents; 27+ rely on name match |
| **Severity** | medium |
| **Area** | Capability Registry, Design |
| **Evidence** | `gerty/capability_registry.py` lines 134–141: `intent_to_cap = {"calendar": "google_workspace_calendar", "search": "web_search", "research": "web_search"}`. Router has 30 intents. Capabilities use `capability_id` like `agent_designer`, `project_graph`; intents use `INTENT_AGENT_DESIGNER` = "agent_designer" — name match works for many. But `INTENT_CALENDAR` → "google_workspace_calendar" requires explicit map. New intents (e.g. future `INTENT_GOOGLE_TASKS`) would need manual config. |
| **Why it matters** | Orchestrator and inspect-prompt use capability_for_intent. Drift causes None returns; planning/inspection may miss capabilities. |
| **Recommended fix** | Add validation script or test: for each INTENT_* in router, verify `get_capability_for_intent(intent)` returns a capability when one exists. Document intent→capability_id mapping in capabilities.json or a single source. |
| **Fix now or later** | Later — add validation in next maintenance window. |

---

#### M-002: Inspection-first and grounded planning use duplicate _parse_markdown_sections

| Field | Value |
|-------|-------|
| **ID** | M-002 |
| **Title** | Duplicate markdown parsing in grounded_planning.py and inspection_first.py |
| **Severity** | medium |
| **Area** | Maintainability, Design |
| **Evidence** | `grounded_planning.py` lines 140–161 and `inspection_first.py` lines 105–125 both define `_parse_markdown_sections` and `_section_relevance_score` with nearly identical logic. |
| **Why it matters** | Bug fixes or improvements must be applied in two places. Risk of divergence. |
| **Recommended fix** | Extract to `gerty/utils/markdown_sections.py` or similar; both modules import. |
| **Fix now or later** | Later — low risk, refactor when touching these modules. |

---

#### M-003: Router apply_policy does not check inspection-first before boundary

| Field | Value |
|-------|-------|
| **ID** | M-003 |
| **Title** | Execution boundary uses planning_result only; inspection-first not passed |
| **Severity** | medium |
| **Area** | Routing, Execution Boundary |
| **Evidence** | `router.py` apply_policy lines 420–428: `planning_result = get_planning_block_for_message(message)` then `boundary = select_execution_path(..., planning_triggered=planning_result is not None, ...)`. Inspection-first is checked in `_get_planning_or_inspection_context` but that runs later in execution. When inspection-first triggers, it also implies "reasoning/planning" and should route to native — but `planning_triggered` in apply_policy is derived only from grounded planning, not inspection-first. |
| **Why it matters** | If inspection-first triggers, the boundary decision may still route to OpenClaw for some intents (e.g. search) when it should prefer native for inspection-style reasoning. |
| **Recommended fix** | In apply_policy, also call `get_inspection_block_for_message(message)` and set `planning_triggered = planning_result is not None or inspection_result is not None`. |
| **Fix now or later** | Now if simple; verify behavior. |

---

#### M-004: test_maintenance_broader_routes_to_chat depends on LLM output

| Field | Value |
|-------|-------|
| **ID** | M-004 |
| **Title** | Maintenance broader test asserts exact LLM response string |
| **Severity** | medium |
| **Area** | Testing |
| **Evidence** | `test_maintenance_broader_routes_to_chat` mocks `router.ollama.chat.return_value = "I can help with maintenance planning."` but the router may use OpenRouter when Ollama fails or provider is openrouter. Actual response: "I cannot determine what specific maintenance you need to fix without more information...". Test fails because it asserts exact string match. |
| **Why it matters** | Flaky test; depends on which provider/model is used. Over-mocked for routing test. |
| **Recommended fix** | Test routing only: assert `tool_executor.assert_not_called()` and `decision.provider == PROVIDER_CHAT`. Do not assert response content. Or mock both Ollama and OpenRouter and force provider=local. |
| **Fix now or later** | Now — test is currently failing. |

---

### Low

#### L-001: OPENCLAW_ACTION_PHRASES includes "read file" — may over-trigger OpenClaw

| Field | Value |
|-------|-------|
| **ID** | L-001 |
| **Title** | "read file" in execution boundary action phrases |
| **Severity** | low |
| **Area** | Execution Boundary |
| **Evidence** | `execution_boundary.py` line 81: `OPENCLAW_ACTION_PHRASES` includes "read file". "How do I read a file in Python" could match and route to OpenClaw when user wants coding advice. |
| **Why it matters** | Edge case; "read file" is ambiguous (advice vs action). |
| **Recommended fix** | Consider removing "read file" or requiring stronger context (e.g. "read file X" with path). Document as known edge case (IB-039). |
| **Fix now or later** | Later. |

---

#### L-002: capabilities.json has no entry for several router intents

| Field | Value |
|-------|-------|
| **ID** | L-002 |
| **Title** | capability_id for notes, time, alarm, etc. not in capabilities.json |
| **Severity** | low |
| **Area** | Capability Registry |
| **Evidence** | capabilities.json lists 18 capabilities. Router has intents: notes, time, alarm, timer, calculator, units, etc. Many match by name (e.g. "notes" → no capability_id "notes"). `get_capability(intent)` returns None for those. |
| **Why it matters** | Orchestrator "what can you do for this" may under-report. Low impact for now. |
| **Recommended fix** | Add capabilities for core tools (notes, time, alarm, timer, calculator, units) or accept that capability registry is partial. |
| **Fix now or later** | Later. |

---

#### L-003: screen_openclaw_message checks is_command_blocked with args=[text]

| Field | Value |
|-------|-------|
| **ID** | L-003 |
| **Title** | Security screening passes full message as single "arg" |
| **Severity** | low |
| **Area** | Security |
| **Evidence** | `security.py` line 233: `blocked, reason = is_command_blocked("", args=[text])`. This concatenates args and checks against forbidden patterns. User message "run rm -rf /" would be blocked. Good. But `args=[text]` means the whole message is one arg; patterns like `r"\brm\s+-[rf]"` may not match "please run rm -rf" depending on regex. |
| **Why it matters** | Prompt injection to trigger destructive commands could bypass if phrased unusually. |
| **Recommended fix** | Verify patterns against common injection phrases. Consider also checking `cmd=text` when message starts with action words. |
| **Fix now or later** | Later — current coverage is reasonable. |

---

## 3. Existing Test Failures

| Test | Failure | Truly Unrelated? | Block Feature Work? |
|------|---------|------------------|---------------------|
| test_heartbeat_excluded_from_bootstrap | HEARTBEAT.md exists | No — bootstrap cleanup incomplete | Yes — easy fix |
| test_inspect_test_message_openclaw | route=openrouter_direct not openclaw | No — Execution Boundary routes "test" to native | Yes — update test |
| test_inspect_planning_message_triggers_planning_mode | route=openrouter_direct not openclaw | No — planning triggers native path | Yes — update test |
| test_openclaw_path_logs_metrics | Got Ollama error, not "Got it!" | No — path is native, OpenClaw mock not used | Yes — update test |
| test_openclaw_path_writes_to_file | route=local not openclaw | No — same as above | Yes — update test |
| test_openclaw_receives_history_and_system_context | Response from LLM not mock | No — native path used, mock bypassed | Yes — update test |
| test_fallback_to_gerty_when_openclaw_unavailable | Different LLM response | Partial — mock may not be applied if path is native first | Yes — update test |
| test_maintenance_broader_routes_to_chat | LLM returned different content | No — test asserts exact string; routing may be correct | Yes — fix assertion |

**Conclusion:** All 8 failures are **not** truly unrelated. They reflect (a) incomplete bootstrap cleanup, and (b) tests written for pre–Execution Boundary behavior. They **should not** be ignored; they should be fixed so CI is green and reflects actual behavior.

---

## 4. Top 5 Hardening Priorities

1. **Fix the 8 failing tests** — Update for Execution Boundary routing and bootstrap state. Unblock CI.
2. **Remove or reconcile HEARTBEAT.md** — Complete bootstrap cleanup (IB-033). One-line fix or doc update.
3. **Include inspection-first in apply_policy planning_triggered** — Ensure boundary routes inspection-first requests to native (M-003).
4. **Add intent–capability validation** — Script or test that ensures each router intent maps to a capability when appropriate (M-001).
5. **Decouple test_maintenance_broader from LLM output** — Assert routing only, not response text (M-004).

---

## 5. Optional Quick Wins

- Extract `_parse_markdown_sections` to shared util (M-002).
- Add `capability_registry` to TRUSTED_TOOLS if used by OpenClaw (verify).
- Document in BUILD_PLAN_PROGRESS that Execution Boundary changes routing; tests must reflect it.

---

## Audit Questions Answered

| Question | Answer |
|----------|--------|
| **Is Gerty's architecture currently coherent, or fragmented?** | Coherent at the core (router, policy, execution). Fragmented at edges: tests vs behavior, bootstrap files, intent–capability sync. |
| **Are native vs OpenClaw responsibilities clear in code?** | Yes. `execution_boundary.py`, `OPENCLAW_TOOL_INSTRUCTIONS`, `capability_registry` (execution_layer, owner) document it. Calendar fallback to CalendarTool when OpenClaw down is clear. |
| **Can the system still produce generic guessed answers after inspection-first?** | Yes. Inspection-first uses strict phrase matching. "Analyze our setup", "what should we fix first" may not trigger; user gets generic advice. (IB-041) |
| **Is capability ownership truly canonical?** | Partially. capabilities.json is source of truth for execution_layer/owner. Router intents and capability_id are maintained separately; drift risk (IB-040, M-001). |
| **Are there legacy paths that reintroduce old behavior?** | HEARTBEAT.md at root could be picked up by OpenClaw if it still looks for it. CalendarTool runs `check_google_calendar.py` — native path when OpenClaw down; this is intentional fallback, not legacy. |
| **Are the failing tests safe to ignore?** | No. They indicate real drift between tests and behavior. Fix them. |
| **Single most important hardening step next?** | Fix the 8 failing tests and remove HEARTBEAT.md. Restores CI and completes bootstrap cleanup. |

---

## Files Inspected

- `gerty/llm/router.py` — routing, policy, execution
- `gerty/execution_boundary.py` — native vs OpenClaw path selection
- `gerty/model_routing.py` — task type, model selection
- `gerty/grounded_planning.py` — planning context injection
- `gerty/inspection_first.py` — inspection-first mode
- `gerty/capability_registry.py` — capability lookup
- `gerty/prompt_metrics.py` — observability
- `gerty/inspect_prompt.py` — payload inspection
- `config/capabilities.json` — capability definitions
- `gerty/security.py` — screening, forbidden patterns
- `gerty/openclaw/client.py` — execute, stream, screening
- `gerty/openclaw/validation.py` — response validation
- `gerty/tools/calendar_tool.py` — fallback calendar
- `docs/BUILD_PLAN_PROGRESS.md`, `docs/IMPROVEMENT_BACKLOG.md`
- `tests/test_prompt_metrics.py`, `tests/test_router.py`, `tests/test_bootstrap_cleanup.py`
- `AGENTS.md`, `USER.md`, `SOUL.md` (referenced)

---

## Runtime Behavior Changed?

**No.** This audit did not modify runtime behavior. Only documentation and backlog updates.
