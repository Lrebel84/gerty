# Build Plan Progress

> **Purpose:** Record progress through the Gerty Build Plan. **Build plan complete.** Read this for artifact summary and status.

**Last updated:** 2026-03-14  
**Branch:** `stabilize/openclaw-foundation`  
**Status:** ✅ **Build plan complete** (Sprints 0–10a)

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
| 3 | ✅ Done | OpenClaw workspace formalization |
| 3a | ✅ Done | Source-of-truth cleanup (root canonical) |
| 4 | ✅ Done | Observability (events, health, friction logs) |
| 5 | ✅ Done | Maintenance subsystem |
| 5a | ✅ Done | Maintenance routing design (local vs broader) |
| 6 | ✅ Done | Autonomy policy layer |
| 6a | ✅ Done | Autonomy denial clarity |
| 7 | ✅ Done | Self-improvement pipeline |
| 7a | ✅ Done | Pipeline validation & evidence |
| 7b | ✅ Done | Patch proposal & staging refinement |
| 8 | ✅ Done | Subagent roles (Observer, Diagnoser, Planner, Validator) |
| 8a | ✅ Done | Role usage opt-in (GERTY_PIPELINE_USE_ROLES, legacy default) |
| 9 | ✅ Done | Heartbeat & cron |
| 9a | ✅ Done | `--validate`, cron install docs |
| 10 | ✅ Done | Security tightening (trusted tools, forbidden patterns, sensitive paths) |
| 10a | ✅ Done | OpenClaw pre-send screening (`screen_openclaw_message`) |

---

## How to pick up

1. **Read** `docs/BUILD_PLAN_SPRINTS.md` — full sprint breakdown
2. **Read** `docs/BUILD_PLAN_PROGRESS.md` (this file) — summary and artifacts
3. **Read** `memory/YYYY-MM-DD.md` and `MEMORY.md` — recent context
4. **Validate:** `python -m gerty --validate` — run do-not-break checklist

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

### Sprint 3 (this session)

- `docs/OPENCLAW_WORKSPACE_PLAN.md` — structure, source of truth, file purposes
- `workspace/` — notes only (backlog, incidents, proposals, releases, decisions)

### Sprint 3a (this session)

- **Canonical:** Root only. Removed workspace/ duplicates (USER.md, SOUL.md, AGENTS.md, TOOLS.md, HEARTBEAT.md, MEMORY.md).
- **Symlinks:** Not used; root-only is simpler.

### Sprint 4 (this session)

- **Observability:** `gerty/observability.py` — `log_event`, `log_health`, `log_friction`, `maybe_log_user_friction`
- **Logs:** `data/logs/events.jsonl`, `health.jsonl`, `friction.jsonl` (JSONL, machine-readable)
- **Events:** route_decision, tool_call, openclaw_result, openclaw_timeout/error, web_fallback, app_unavailable
- **Health:** startup, openclaw_unreachable, openclaw_validation_replaced, voice_stt/stream/sync/processing_fail, screen_fail, calendar_fail
- **Friction:** openclaw_fallback_calendar, openclaw_failed, openclaw_replaced, user_friction_phrase
- **Docs:** `docs/OBSERVABILITY.md`
- **Tests:** `tests/test_observability.py` (6 tests)

### Sprint 5 (this session)

- **Maintenance:** `data/maintenance/{incidents,proposals,tasks,releases}/`
- **Module:** `gerty/maintenance.py` — create/list/summarize/collect/diagnostics
- **Tool:** MaintenanceTool — create incident/proposal/task/release, list, summarize, collect logs, run diagnostics
- **Workflow:** `docs/MAINTENANCE_WORKFLOW.md`
- **Tests:** `tests/test_maintenance.py` (10 tests)

### Sprint 5a (this session)

- **Routing design:** Local maintenance → tool; broader maintenance → chat (avoids dead end)
- **LOCAL_MAINTENANCE_PATTERNS**, `_is_local_maintenance_command()`
- Removed INTENT_MAINTENANCE from FAST_PATH; policy-based routing in `apply_policy`
- **Tests:** `test_maintenance_local_vs_broader`, `test_maintenance_broader_routes_to_chat`, `test_maintenance_standalone_routes_to_tool`

### Sprint 6 (this session)

- **Autonomy:** `gerty/autonomy.py` — levels 0–3, GATES, check(), get_policy_summary()
- **Gates:** filesystem_writes, maintenance_writes, shell_commands, external_integrations, service_restart, code_change_prep
- **Integration:** MaintenanceTool, NotesTool (add/clear/delete), SystemCommandTool
- **Config:** GERTY_AUTONOMY_LEVEL env, data/config/autonomy.json (optional)
- **Docs:** `docs/AUTONOMY_POLICY.md`
- **Tests:** `tests/test_autonomy.py`, `tests/test_autonomy_integration.py`

### Sprint 6a (this session)

- **Notes API:** `{"added": false, "error": "Autonomy level 0..."}` when blocked
- **Notes functions:** `add_note`, `clear_notes`, `delete_note` return `(result, error_message)`
- **Observability:** `autonomy.check()` logs `autonomy_denied` to friction.jsonl when denied
- **Docs:** Enforced vs defined-only gates clarified in AUTONOMY_POLICY.md

### Sprint 7 (Self-Improvement Pipeline)

- **Module:** `gerty/self_improvement.py` — observe, diagnose, prepare_patch_plan, write_patch_staging, validate, summarize, run_pipeline
- **Staging:** `data/maintenance/staging/`, `data/maintenance/pipeline_runs/`
- **Tool:** MaintenanceTool — "run pipeline", "diagnose incident"
- **Docs:** `docs/SELF_IMPROVEMENT_PIPELINE.md`

### Sprint 7a (Pipeline Validation & Evidence)

- **Validation:** Structured checks aligned with do-not-break (import, voice, chat UI, OpenClaw modes, pytest)
- **Evidence:** maintenance_tasks, experiment_tasks (clear record types)
- **Summary:** Checks Executed / Skipped / Unavailable sections

### Sprint 7b (Patch Proposal & Staging Refinement)

- **Artifacts:** 01_issue_summary.md, 02_evidence.json, 03_diagnosis.json, 04_change_plan.json, 05_patch_content.md, 06_validation.json, 07_rollback_safety.md, manifest.json
- **Traceability:** manifest.json links incident_paths, proposal_paths to pipeline run
- **Tool:** "list staging runs", "list staging for incident X"
- **prepare_patch_plan:** patch_outline, risk

### Sprint 8 (Subagent Roles)

- **Module:** `gerty/subagent_roles.py` — Observer, Diagnoser, Planner, Validator
- **Integration:** run_pipeline(use_roles=None), summarize(role_contributions)
- **Docs:** `docs/SUBAGENT_ROLES.md`
- **Tests:** `tests/test_subagent_roles.py`

### Sprint 8a (Subagent Role Safe Rollout)

- **Default:** Legacy non-role pipeline (use_roles=False)
- **Opt-in:** GERTY_PIPELINE_USE_ROLES=1 or run_pipeline(use_roles=True)
- **Config:** `gerty/config.py` — GERTY_PIPELINE_USE_ROLES
- **Tests:** test_run_pipeline_default_legacy, test_run_pipeline_roles_via_config

### Sprint 9 (Heartbeat & Cron)

- **Module:** `gerty/heartbeat.py` — run_heartbeat(), get_heartbeat_summary()
- **Checks:** import, diagnostics, friction tail, health tail, open incidents
- **Artifacts:** `data/maintenance/heartbeat/heartbeat-YYYYMMDD-HHMMSS.json` (when noteworthy)
- **CLI:** `python -m gerty --heartbeat`
- **Docs:** `docs/HEARTBEAT_AND_CRON.md`
- **Scripts:** morning-brief.sh, nightly-report.sh, weekly-review.sh, stale-incidents.sh
- **Tests:** `tests/test_heartbeat.py` (11 tests)

### Sprint 9a (Heartbeat & Cron Acceptance Gaps)

- **CLI:** `python -m gerty --validate` / `--do-not-break`
- **Module:** `gerty/self_improvement.py` — format_validation_report(), pytest unavailable handling
- **Docs:** `docs/CRON_INSTALL.md`, `scripts/crontab.example`
- **Tests:** format_validation_report, validate with pytest unavailable

### Sprint 10 (Security Tightening)

- **Module:** `gerty/security.py` — TRUSTED_TOOLS, forbidden patterns, sensitive paths, is_command_blocked, check_path_safe_for_write
- **Docs:** `docs/SECURITY_POLICY.md`
- **Integration:** maintenance.py path checks before create_incident/proposal/task/release
- **Tests:** `tests/test_security.py` (16 tests)

### Sprint 10a (OpenClaw Security Guard)

- **Screening:** `gerty/security.py` — screen_openclaw_message()
- **Integration:** `gerty/openclaw/client.py` — guard in execute() and execute_stream()
- **Logging:** openclaw_security_blocked in friction.jsonl; heartbeat includes in noteworthy
- **Docs:** SECURITY_POLICY.md OpenClaw-bound screening section
- **Tests:** screen_openclaw_message, TestOpenclawSecurityGuard

---

## Commits (build plan work)

```
af07eff Sprint 2a: Intent classification (router split)
8a53c85 Sprint 1a: path hardening and secret handling
41d26fa Sprint 2b, 2c
38967a6 docs: clarify Gerty vs OpenClaw, heartbeat terminology, security screening
```

Sprints 3–10a implemented on `stabilize/openclaw-foundation`.

---

## Post–Build Plan: Systems

Beyond the original build plan sprints, two systems have been implemented:

### System 1: Personal Context Engine

- **Module:** `gerty/personal_context.py`, `gerty/tools/personal_context_tool.py`
- **Data:** `data/personal_context/` — profile, goals, projects, ideas, preferences, businesses; `routines.json` (work schedule, best times)
- **Features:** Read goals/projects/routines; controlled updates (add idea/goal/project, update status, add preference note, add business concept)
- **Docs:** [docs/PERSONAL_CONTEXT_ENGINE.md](PERSONAL_CONTEXT_ENGINE.md)

### System 2: Agent Factory

- **Modules:** `gerty/agent_factory.py`, `gerty/agent_registry.py`, `gerty/agent_runner.py`, `gerty/tools/agent_factory_tool.py`, `gerty/tools/agent_runner_tool.py`
- **Data:** `data/agents/` (created agents), `templates/agents/base_agent/`, `config/model_profiles.json`
- **Features:** Create agents from templates, list agents, invoke agents (ask/run/use), model profiles
- **Docs:** [docs/AGENT_FACTORY.md](AGENT_FACTORY.md)

### System 3: Agent Designer

- **Modules:** `gerty/agent_designer.py`, `gerty/tools/agent_designer_tool.py`
- **Features:** Design new agents from natural language, improve existing agents, suggest agents for tasks; draft-first, inspectable before create/apply
- **Docs:** [docs/AGENT_DESIGNER.md](AGENT_DESIGNER.md)

### System 4: Intent Orchestrator

- **Modules:** `gerty/intent_orchestrator.py`, `gerty/tools/intent_orchestrator_tool.py`
- **Features:** Interpret high-level outcome requests (help me explore, best next step, organize this, build whatever agent we need); choose best path (direct_answer, use_tool, run_agent, design_agent, create_project_structure, recommend_new_tool, escalate_to_maintenance); optionally invoke when simple and safe
- **Routing:** ORCHESTRATOR_KEYWORDS after agent_* so direct commands still win
- **Docs:** [docs/INTENT_ORCHESTRATOR.md](INTENT_ORCHESTRATOR.md)

### System 5: Project / Task Graph

- **Modules:** `gerty/project_graph.py`, `gerty/tools/project_graph_tool.py`
- **Data:** `data/projects/<project_slug>/` — project.json, tasks.json, README.md, notes/, outputs/
- **Features:** Create projects, add tasks (with dependencies, assigned_agent), update task status, summarize, suggest next task; validate_project_graph
- **Routing:** PROJECT_GRAPH_KEYWORDS before personal_context (create project, add task, etc.)
- **Docs:** [docs/PROJECT_TASK_GRAPH.md](PROJECT_TASK_GRAPH.md)

### System 5.1: Project Execution Layer

- **Module:** `gerty/project_execution.py`
- **Features:** assign_agent_to_task, run_task, run_next_task, can_run_task; write_project_output, update_task_after_run
- **Commands:** assign agent, run task, run next task
- **Outputs:** `outputs/<task_id>-<timestamp>.md`
- **Task fields:** last_run_at, last_result_summary, output_artifact

### System 6: Opportunity Scanner

- **Modules:** `gerty/opportunity_scanner.py`, `gerty/tools/opportunity_scanner_tool.py`
- **Data:** `data/opportunities/<timestamp>-<slug>.json`
- **Features:** create, list, get, summarize, score, suggest_next_step, create_project_from_opportunity
- **Categories:** business, product, automation, niche, content, other

---

## Do-not-break checklist (validate after changes)

1. Local chat must still function
2. Voice must still function
3. Fast-path tools must still function
4. Chat UI must still function
5. OpenClaw disabled mode must still function
6. OpenClaw enabled but unavailable mode must still function
7. OpenClaw enabled and reachable mode must still function
