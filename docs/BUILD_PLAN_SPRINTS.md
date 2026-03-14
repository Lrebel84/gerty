# Gerty Build Plan — Sprint Breakdown

> Phased implementation of the external review build plan. Each sprint is sized for high-quality delivery. **Stabilize → Formalize → Automate → Self-improve.**

**Progress:** See `docs/BUILD_PLAN_PROGRESS.md` for current status and how to pick up.

---

## Do Not Break (validate every sprint, in order)

1. Local chat must still function
2. Voice must still function
3. Fast-path tools must still function
4. Chat UI must still function
5. OpenClaw disabled mode must still function
6. OpenClaw enabled but unavailable mode must still function
7. OpenClaw enabled and reachable mode must still function

---

## Sprint Overview

| Sprint | Focus | Est. effort | Depends on | Status |
|--------|-------|-------------|------------|--------|
| **0** | Safety freeze & baseline | 0.5–1 day | — | ✅ |
| **1a** | Secrets & path hardening | 0.5–1 day | 0 | ✅ |
| **1b** | Config boundary & startup validation | 0.5–1 day | 1a | ✅ |
| **1c** | Google Workspace diagnostics & stabilization | 0.5–1 day | 1b | ✅ |
| **1d** | Google Workspace normalization & portability | 0.5–1 day | 1c | ✅ |
| **2a** | Intent classification (router split) | 1–2 days | 1d | ✅ |
| **2b** | Policy & execution layers | 1–2 days | 2a | ✅ |
| **2c** | Result validation & OpenClaw payload | 0.5–1 day | 2b | ✅ |
| **3** | OpenClaw workspace formalization | 1–2 days | 2c | ⏳ Next |
| **4** | Observability (events, health, friction) | 1–2 days | 3 | — |
| **5** | Maintenance subsystem | 1–2 days | 4 | — |
| **6** | Autonomy policy | 0.5–1 day | 5 | — |
| **7** | Self-improvement pipeline | 2–3 days | 6 | — |
| **8** | Subagent roles | 1–2 days | 7 | — |
| **9** | Heartbeat & cron | 1 day | 8 | — |
| **10** | Security tightening | 1–2 days | 9 | — |

---

# Sprint 0 — Safety Freeze & Baseline Capture

**Goal:** Capture current behavior and create a rollback point. No behavior changes.

**Branch:** `stabilize/openclaw-foundation`

## Tasks

1. Create branch `stabilize/openclaw-foundation`
2. Create `docs/BASELINE_BEHAVIOR.md` documenting:
   - Current routing rules (Option A: fast-path vs OpenClaw vs fallback)
   - Fast-path intents (time, alarm, timer, calculator, notes, weather, RAG, etc.)
   - OpenClaw-enabled behavior
   - Fallback when OpenClaw unavailable
   - Current settings fields
   - Known brittle areas (hardcoded paths, message packing, etc.)
3. Create `docs/ARCHITECTURE_CURRENT.md`:
   - Request flow diagram (text/mermaid)
   - Key modules and responsibilities
   - Integration points (Ollama, OpenRouter, OpenClaw, voice, UI)
4. Add "do not break" checklist to both docs

## Acceptance

- [ ] Branch exists and is pushed
- [ ] BASELINE_BEHAVIOR.md is complete and accurate
- [ ] ARCHITECTURE_CURRENT.md reflects current state
- [ ] No code changes; behavior identical

---

# Sprint 1a — Secrets & Path Hardening

**Goal:** Remove sensitive and machine-specific coupling. No secrets in repo.

**Depends on:** Sprint 0

## Tasks

1. **Remove tracked secrets**
   - Remove `openclaw/google_client.json` from source control (if present)
   - Add to `.gitignore`: `google_client.json`, `*-token.json`, `credentials/`
   - Create `openclaw/google_client.json.example` or document external path in `.env.example`

2. **Refactor `openclaw/google_auth.py`**
   - Replace hardcoded `/home/liam/.openclaw/credentials/google-token.json` with config-driven path
   - Use env var (e.g. `OPENCLAW_GOOGLE_TOKEN_PATH`) or `~/.openclaw/credentials/google-token.json` with `os.path.expanduser`
   - Document in `.env.example`

3. **Audit for other hardcoded paths**
   - Grep for `/home/liam`, absolute paths in `openclaw/`, `config.py`
   - Replace with config/env or `expanduser` where appropriate

## Acceptance

- [ ] No credential files in tracked code
- [ ] `.gitignore` blocks credential patterns
- [ ] `google_auth.py` uses config/env for token path
- [ ] Do-not-break checklist passes

---

# Sprint 1b — Config Boundary & Startup Validation

**Goal:** Proper secrets/config boundary and clear startup diagnostics.

**Depends on:** Sprint 1a

## Tasks

1. **Config layer for paths**
   - Add to `config.py` or new `gerty/paths.py`:
     - `OPENCLAW_WORKSPACE_PATH`
     - `OPENCLAW_LOGS_PATH`
     - `OPENCLAW_CREDENTIALS_PATH` (or similar)
   - Resolve via env vars with sensible defaults (`~/.openclaw/...`)

2. **Environment validation**
   - On startup, validate required env vars
   - Log missing/optional config clearly

3. **Startup diagnostics**
   - On app start, check and log:
     - Ollama reachable (or not)
     - OpenClaw reachable (or not)
     - Required external files exist
     - Required directories present
     - Dangerous config combinations (if any)
   - Output to console/log; consider `--diagnose` flag for one-off check

4. **Explicit degraded mode**
   - Document and enforce: when OpenClaw unavailable:
     - Fast-path tools work
     - Local/OpenRouter chat works
     - Integrations return clean, consistent message (no silent half-failure)

## Acceptance

- [ ] Credential and workspace paths configurable
- [ ] Startup logs clearly show what is healthy/unhealthy
- [ ] Degraded behavior is intentional and documented
- [ ] Do-not-break checklist passes

---

# Sprint 1c — Google Workspace Diagnostics & Stabilization

**Goal:** Diagnose and stabilize calendar/Gmail/Drive/Sheets/Docs through OpenClaw. No routing refactor.

**Depends on:** Sprint 1b

## Tasks

1. Trace request path for Google Workspace requests
2. Add logging for calendar/gmail/drive/docs/sheets intents
3. Improve empty-response handling ("OpenClaw ran but returned no output")
4. Add `scripts/check_google_workspace.sh` diagnostic
5. Document true state in `docs/GOOGLE_WORKSPACE_STATUS.md`
6. Add validation checklist in `docs/SPRINT_1C_VALIDATION.md`

## Acceptance

- [ ] Google Workspace requests logged at INFO
- [ ] Empty output returns user-friendly hint (not "Done.")
- [ ] Diagnostic script runs and reports pass/fail
- [ ] Status doc reflects actual behavior
- [ ] Validation checklist covers calendar, gmail, drive, docs, sheets

---

# Sprint 1d — Google Workspace Normalization & Portability

**Goal:** Remove hardcoded paths, normalize integration paths, add single E2E verify, mark status truthfully.

**Depends on:** Sprint 1c

## Tasks

1. Remove hardcoded /home/liam/gerty from skills/calendar and related docs
2. Normalize paths: GERTY_WORKSPACE in ~/.openclaw/.env
3. Improve empty-output logging (google_workspace flag)
4. Add scripts/verify_calendar_openclaw.sh (single E2E command)
5. Update docs: working / flaky / unsupported per service

## Acceptance

- [ ] No hardcoded /home/liam in skills or integration docs
- [ ] Primary path documented for calendar and gmail/drive/docs/sheets
- [ ] verify_calendar_openclaw.sh runs and has clear pass/fail
- [ ] GOOGLE_WORKSPACE_STATUS marks each service as working, flaky, or unsupported

---

# Sprint 2a — Intent Classification (Router Split)

**Goal:** Split intent classification from execution. Pure classification only.

**Depends on:** Sprint 1b

## Tasks

1. **Define intent enum/constants**
   - `fast_path`, `local_chat`, `openrouter_chat`, `openclaw_action`, `web_lookup`, `research`, `screen_vision`, `browse`, `maintenance`, `unsupported`

2. **Extract `classify_intent()`**
   - Move classification logic out of router into a pure function
   - Input: message (and optionally context)
   - Output: intent label
   - No side effects, no execution

3. **Introduce `RoutingDecision` dataclass**
   - Fields: `intent`, `provider`, `fallback_allowed`, `requires_confirmation`, etc.
   - Policy will populate this; execution will consume it

4. **Preserve current behavior**
   - Classifier should produce same effective routing as today
   - Add unit tests for classifier edge cases

## Acceptance

- [x] `classify_intent()` is pure and testable
- [x] `RoutingDecision` exists and is used
- [x] Current routing behavior preserved
- [x] Tests for classifier
- [x] Do-not-break checklist passes

## Completed (2026-03-13)

- **Intent constants:** `INTENT_*` in `gerty/llm/router.py` (time, date, calendar, chat, etc.)
- **Pure classifier:** `_classify_intent_impl(text, browse_enabled)` — no config import in impl
- **RoutingDecision:** `@dataclass(frozen=True) RoutingDecision(intent: str)`
- **classify_to_decision():** Returns `RoutingDecision`; `classify_intent()` returns `.intent` (unchanged API)
- **Tests:** 44 passing; edge cases: date whole-word, calendar vs app-integration, browse_enabled, openclaw_direct, pomodoro/stopwatch
- **Routing unchanged:** Router still uses `classify_intent()` → same outcomes

---

# Sprint 2b — Policy & Execution Layers

**Goal:** Separate policy (what is allowed) from execution (what happens).

**Depends on:** Sprint 2a

## Tasks

1. **Policy layer**
   - `apply_policy(intent, context) -> RoutingDecision`
   - Decides: OpenClaw allowed? Local model? Fallback? Destructive? Confirmation?
   - No execution, only decision

2. **Execution layer**
   - `execute(decision, message, context) -> result`
   - Dispatches to: local tool, Ollama, OpenRouter, OpenClaw, fallback
   - Single responsibility per branch

3. **Refactor `llm/router.py`**
   - Flow: `classify_intent` → `apply_policy` → `execute`
   - Keep existing behavior; structure only

4. **Structured route logging**
   - Log: source, intent, provider, fallback used, elapsed time, success/failure
   - Machine-readable format (e.g. JSON lines) for later observability

## Acceptance

- [x] Policy and execution are separate
- [x] One message traceable: classification → policy → execution
- [ ] Route decisions logged (deferred to observability sprint)
- [x] Do-not-break checklist passes

## Completed (2026-03-13)

- **Policy layer:** `apply_policy(decision, message, openclaw_enabled, tool_executor_present, web_fallback_enabled) -> RoutingDecision`
- **RoutingDecision extended:** provider, tool_intent, run_web_fallback, use_reasoning, openclaw_fallback_calendar, show_app_unavailable
- **Execution layer:** `_execute_route()` and `_execute_route_stream()` consume decision
- **Flow:** `route()` and `route_stream()` use classify_to_decision → apply_policy → execute
- **Tests:** 7 policy tests added; 51 total passing

---

# Sprint 2c — Result Validation & OpenClaw Payload

**Goal:** Normalize OpenClaw responses and improve payload construction.

**Depends on:** Sprint 2b

## Tasks

1. **Result validation layer**
   - For OpenClaw responses: detect empty output, fabricated success, tool failure phrasing
   - Normalize user-facing messages
   - Return consistent structure

2. **Centralize OpenClaw payload construction**
   - Document exactly what goes in
   - Separate user content from operating context (as SDK allows)
   - Explicit history trimming/summarization policy
   - Reduce instruction-boundary blur (security)

3. **Generalize fallback pattern**
   - "Trusted direct integration" vs "OpenClaw integration" vs "degraded fallback"
   - Apply pattern beyond calendar (e.g. for future integrations)

## Acceptance

- [x] OpenClaw responses validated and normalized
- [x] Payload construction centralized and documented
- [x] Fallback pattern generalized
- [x] Do-not-break checklist passes

## Completed (2026-03-13)

- **Validation:** `gerty/openclaw/validation.py` — `validate_openclaw_response()` detects empty, tool failure phrasing, fabricated success; returns context-aware hints
- **Payload:** `build_openclaw_payload()` in client; structure documented in OPENCLAW_INTEGRATION.md; history policy explicit
- **Fallback pattern:** Three tiers (trusted direct → OpenClaw → degraded) documented in OPENCLAW_INTEGRATION.md
- **Tests:** 13 in `tests/test_openclaw.py` (validation + payload)

---

# Sprint 3 — OpenClaw Workspace Formalization

**Goal:** Gerty-specific OpenClaw workspace with durable identity and rules.

**Depends on:** Sprint 2c

## Tasks

1. **Create `docs/OPENCLAW_WORKSPACE_PLAN.md`**
   - Document workspace structure
   - Explain purpose of each file

2. **Generate workspace templates**
   - `workspace/USER.md` — Liam, goals, preferences
   - `workspace/SOUL.md` — Gerty identity, principles
   - `workspace/AGENTS.md` — Operating rules (observe, patch small, verify)
   - `workspace/TOOLS.md` — Repo path, build/run/test commands, log paths
   - `workspace/HEARTBEAT.md` — Tiny health checklist
   - `workspace/MEMORY.md` — Long-term memory
   - `workspace/notes/backlog.md`
   - `workspace/notes/incidents/`, `proposals/`, `releases/`, `decisions/`

3. **Populate from existing SOUL.md, USER.md, AGENTS.md**
   - Sync or copy content; avoid duplication where it causes drift
   - Document which files are source of truth

## Acceptance

- [ ] Workspace plan documented
- [ ] All template files created and populated
- [ ] OpenClaw uses Gerty-specific identity
- [ ] Do-not-break checklist passes

---

# Sprint 4 — Observability

**Goal:** Gerty can notice what is wrong before fixing anything.

**Depends on:** Sprint 3

## Tasks

1. **Structured event log** — `data/logs/events.jsonl`
   - Route decisions, tool calls, OpenClaw attempts, failures, latencies, fallback reasons

2. **Health log** — `data/logs/health.jsonl`
   - App startup, OpenClaw reachability, voice/STT/TTS/screen/calendar failures, repeated empty OpenClaw outputs

3. **Friction log** — `data/logs/friction.jsonl`
   - Repeated rephrases, "that didn't work" messages, retries, failed action sequences

4. **Daily summary writer (optional, minimal)**
   - Top failures, common route path, most-used features
   - Can be manual script at first

## Acceptance

- [ ] Events, health, friction logs exist and are written
- [ ] Log format is machine-readable (JSONL)
- [ ] Do-not-break checklist passes

---

# Sprint 5 — Maintenance Subsystem

**Goal:** Gerty can manage work about itself, but not patch live code automatically.

**Depends on:** Sprint 4

## Tasks

1. **Folder structure**
   - `data/maintenance/incidents/`
   - `data/maintenance/proposals/`
   - `data/maintenance/tasks/`
   - `data/maintenance/releases/`

2. **Task types**
   - `incident`, `proposal`, `maintenance`, `experiment`, `release`

3. **Maintenance workflow (documented)**
   - Detect → incident note → propose fix → classify risk → prepare patch/review task → validate → record → update

4. **Allowed actions at this phase**
   - Inspect, summarize, prepare patch plans, prepare branch/work items, collect logs, run diagnostics
   - **Not allowed:** Direct patch of live code, merge, overwrite baseline

## Acceptance

- [ ] Maintenance folders and task types exist
- [ ] Workflow documented
- [ ] Gerty can create incidents/proposals/tasks
- [ ] No automatic code patching
- [ ] Do-not-break checklist passes

---

# Sprint 6 — Autonomy Policy

**Goal:** Configurable autonomy levels. Risky capabilities explicit.

**Depends on:** Sprint 5

## Tasks

1. **Create `gerty/autonomy.py` or `data/config/autonomy.json`**

2. **Define levels**
   - **Level 0:** Observe only (inspect, summarize, log, propose)
   - **Level 1:** Non-destructive updates (memory, notes, backlog, reports, staging)
   - **Level 2:** Controlled code work (branch, patch, test, build, summary)
   - **Level 3:** Operational (restart services, rotate state, refresh indexes) — explicit opt-in

3. **Policy gates**
   - Filesystem writes, service restarts, dependency changes, git ops, external integrations, dangerous shell commands

## Acceptance

- [ ] Autonomy levels defined and configurable
- [ ] Policy gates documented and enforced
- [ ] Do-not-break checklist passes

---

# Sprint 7 — Self-Improvement Pipeline

**Goal:** Gerty can prepare and test fixes under guardrails. No direct merge.

**Depends on:** Sprint 6

## Tasks

1. **Pipeline stages**
   - Observe (read logs, incidents)
   - Diagnose (root cause, affected files, suggested change, risk, rollback plan)
   - Prepare patch (branch name, file list, test plan, acceptance checklist)
   - Patch in isolation (branch or staging only)
   - Validate (import, startup, smoke tests, route checks, voice-disabled, OpenClaw-disabled/enabled)
   - Summarize (what changed, passed, failed, promotion safety)

2. **Critical rule**
   - No direct merge or overwrite of baseline branch

3. **Integration with maintenance subsystem**
   - Incidents feed into pipeline; proposals become patch tasks

## Acceptance

- [ ] Pipeline stages implemented
- [ ] Gerty can prepare fixes with evidence
- [ ] Gerty can test on branch
- [ ] Promotion remains human-controlled
- [ ] Do-not-break checklist passes

---

# Sprint 8 — Subagent Roles

**Goal:** Separate responsibilities inside OpenClaw model.

**Depends on:** Sprint 7

## Tasks

1. **Define roles**
   - Operator (daily assistant)
   - Watcher (logs, incidents, failures)
   - Maintainer (code/config investigation)
   - Researcher (web/docs-heavy)
   - Release manager (build/test/promote summaries)

2. **Role prompts or workspace guidance**
   - Purpose, allowed actions, success criteria, escalation rules per role

3. **Integration**
   - Route maintenance/research/release tasks to appropriate role context

## Acceptance

- [ ] Roles defined with clear boundaries
- [ ] One context does not do every job
- [ ] Do-not-break checklist passes

---

# Sprint 9 — Heartbeat & Cron

**Goal:** Automatic monitoring without spam.

**Depends on:** Sprint 8

## Tasks

1. **Heartbeat (30–60 min)**
   - App healthy? Gateway healthy? Recent errors? Failed jobs? Critical incidents?
   - If yes → write note
   - If no → no noise

2. **Cron jobs**
   - Morning status brief
   - Nightly maintenance report
   - Weekly self-improvement review
   - Stale-incident cleanup

3. **Separation**
   - Heartbeat = regular health rotation
   - Cron = precise scheduled tasks

## Acceptance

- [ ] Heartbeat runs and produces useful artifacts
- [ ] Cron jobs documented and configured
- [ ] No spam
- [ ] Do-not-break checklist passes

---

# Sprint 10 — Security Tightening

**Goal:** Shrink risk surface before wider autonomy.

**Depends on:** Sprint 9

## Tasks

1. **Prefer built-in tools** over third-party skills
2. **Explicit skill allowlist** — small, documented
3. **Forbidden command categories** — list and enforce
4. **Separate** inspect / safe edit / risky operational commands
5. **Protection around** home dir secrets, SSH keys, credential stores, dotfiles, shell init, package manager, destructive git

## Acceptance

- [ ] Skill allowlist exists
- [ ] Forbidden commands documented
- [ ] Sensitive paths protected
- [ ] Do-not-break checklist passes

---

# Implementation Order (Concrete)

## First batch (Sprints 0, 1a, 1b)
- `docs/BASELINE_BEHAVIOR.md`
- `docs/ARCHITECTURE_CURRENT.md`
- Remove tracked secrets
- Refactor `google_auth.py`
- Startup diagnostics
- Structured route logging

## Second batch (Sprints 2a, 2b, 2c)
- Split `llm/router.py`: classification, policy, execution, result normalization

## Third batch (Sprints 3, 4)
- OpenClaw workspace templates
- Heartbeat/maintenance docs
- Observability logs

## Fourth batch (Sprints 5, 6, 7, 8, 9, 10)
- Maintenance task system
- Autonomy policy
- Self-improvement pipeline
- Subagent roles
- Heartbeat & cron
- Security tightening

---

# Notes

- **Sprint 0 is mandatory** — do not skip. It is the rollback point.
- **Sprints 1a and 1b** address the immediate security/path issues from the review.
- **Sprints 2a–2c** are the largest refactor; allow time for testing.
- **Sprints 5–7** are where "Gerty maintains Gerty" becomes real; keep guardrails strict.
- **Sprint 10** should be revisited as autonomy grows.

---

*Target: "Gerty can maintain Gerty safely without Liam living in Cursor."*
