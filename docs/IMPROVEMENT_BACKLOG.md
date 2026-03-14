# Improvement Backlog

> **Purpose:** Capture discovered weaknesses, limitations, design smells, and deferred fixes so nothing is lost across sessions.

---

## How to Use This Backlog

**Critical issues** — Fix immediately. Security, data loss, or blocking bugs belong here but should not linger.

**Non-blocking issues** — Can be deferred, but **must be logged**. Do not rely on memory or mental notes. When you discover a limitation, weakness, or design smell, add an item to this backlog.

**Workflow:** When working on a system, check this backlog for related items. When you discover something worth fixing later, add it. When you fix an item, update its status to `done` and add a brief note.

---

## Item Format

Each backlog item uses:

| Field | Description |
|-------|-------------|
| **ID** | Short unique identifier (e.g. `IB-001`) |
| **title** | One-line summary |
| **category** | `security` \| `reliability` \| `ux` \| `design` \| `performance` \| `docs` \| `tech-debt` \| `observability` \| `intelligence` \| `scalability` \| `stability` \| `developer-experience` |
| **severity** | `critical` \| `high` \| `medium` \| `low` |
| **status** | `open` \| `in-progress` \| `deferred` \| `done` |
| **discovered_in** | Where it was found (system, doc, session) |
| **why_it_matters** | Impact if left unfixed |
| **recommended_timing** | When to address (e.g. "next maintenance window", "before v2") |

---

## Backlog Items

### IB-001

| Field | Value |
|-------|-------|
| **title** | OpenClaw/Grok sometimes invents responses instead of using tools |
| **category** | reliability |
| **severity** | high |
| **status** | open |
| **discovered_in** | OpenClaw integration, CHANGELOG Known Issues |
| **why_it_matters** | User may receive plausible but fake answers (e.g. claimed skill installs that never happened). Erodes trust. |
| **recommended_timing** | Track OpenClaw bug #39971; consider model swap or validation layer |

---

### IB-002

| Field | Value |
|-------|-------|
| **title** | OpenClaw built-in cron with `--session isolated` — tools don't execute |
| **category** | reliability |
| **severity** | high |
| **status** | deferred |
| **discovered_in** | docs/OPENCLAW_INTEGRATION.md §8 |
| **why_it_matters** | Proactive-agent and similar cron jobs fail silently when using isolated sessions. |
| **recommended_timing** | Workaround in place (system cron). Revisit when OpenClaw fixes isolated session tool execution. |

---

### IB-003

| Field | Value |
|-------|-------|
| **title** | Agent Designer: design drafts not persisted across sessions |
| **category** | reliability |
| **severity** | medium |
| **status** | done |
| **discovered_in** | System 3 (Agent Designer) implementation |
| **why_it_matters** | Designs stored only in `_last_design` (current tool instance). Disappear on Gerty restart, tool reload, or session reset. User may lose work; prevents long-running design workflows. |
| **recommended_timing** | System 3.1. Persist under `data/agent_designs/<agent_name>.json` with full spec, timestamp, model profile, design prompt, suggested tools. |
| **resolved** | System 4.1 implemented. Designs saved to `data/agent_designs/<timestamp>-<agent_name>.json`. Commands: `list agent designs`, `show agent design artifact <id>`. |

---

### IB-004

| Field | Value |
|-------|-------|
| **title** | Agent Designer: LLM may return non-JSON; fallback parsing is brittle |
| **category** | reliability |
| **severity** | medium |
| **status** | open |
| **discovered_in** | System 3 (Agent Designer) implementation |
| **why_it_matters** | Some models return prose or malformed JSON; `_parse_spec_from_response` may produce incomplete specs. Malformed designs could slip through. |
| **recommended_timing** | System 3.1. Add schema validation before creation; consider structured output (JSON mode) or stricter prompt. |

---

### IB-005

| Field | Value |
|-------|-------|
| **title** | Personal Context: extend to semantic search (future capability) |
| **category** | intelligence |
| **severity** | low |
| **status** | open |
| **discovered_in** | docs/PERSONAL_CONTEXT_ENGINE.md Assumptions & Limitations |
| **why_it_matters** | Current design uses keyword matching for lightweight deps. Semantic search (embedding + vector store) would improve relevance when available. |
| **recommended_timing** | Intelligence phase. Replace with embedding search when RAG/embedding infra is mature. |

---

### IB-006

| Field | Value |
|-------|-------|
| **title** | Personal Context: data/ gitignored; no versioned default templates |
| **category** | reliability |
| **severity** | low |
| **status** | open |
| **discovered_in** | docs/PERSONAL_CONTEXT_ENGINE.md, Personal Context Engine review |
| **why_it_matters** | `data/personal_context/` lives under gitignored `data/`. New installs lack default templates; system relies on manual creation. |
| **recommended_timing** | System 1.2. Add versioned templates under `templates/personal_context/` and bootstrap on first run. |

---

### IB-007

| Field | Value |
|-------|-------|
| **title** | STT backend/model changes require app restart |
| **category** | ux |
| **severity** | medium |
| **status** | open |
| **discovered_in** | CHANGELOG Known Issues |
| **why_it_matters** | User changes Settings → Voice → STT but must restart to apply. Poor UX. |
| **recommended_timing** | Next voice/UI maintenance pass |

---

### IB-008

| Field | Value |
|-------|-------|
| **title** | Hallucination on non-RAG topics — known LLM limitation |
| **category** | reliability |
| **severity** | medium |
| **status** | open |
| **discovered_in** | CHANGELOG Known Issues |
| **why_it_matters** | Models may invent facts when asked about things not in memory/docs. Expected LLM behaviour; not a bug. |
| **recommended_timing** | Consider grounding external queries; document for users |

---

### IB-009

| Field | Value |
|-------|-------|
| **title** | frontend/src/skills.ts can drift from gerty/tools/skills_registry.py |
| **category** | tech-debt |
| **severity** | medium |
| **status** | open |
| **discovered_in** | docs/ADDING_TOOLS.md |
| **why_it_matters** | Two sources of truth for skills. Easy to forget one when adding tools. |
| **recommended_timing** | Generate skills.ts from skills_registry.py, or single source (API) for UI |

---

### IB-010

| Field | Value |
|-------|-------|
| **title** | Agent Runner: extend to tool dispatch (future capability) |
| **category** | design |
| **severity** | low |
| **status** | open |
| **discovered_in** | System 2 v1.1 (Agent Invocation) implementation |
| **why_it_matters** | v1.1 scope is single LLM call only by design. Future v1.2 could allow agents to call Gerty tools (search, RAG, etc.) via controlled dispatch. |
| **recommended_timing** | Agent Runner v1.2; requires controlled tool dispatch design |

---

### IB-011

| Field | Value |
|-------|-------|
| **title** | Route decisions not logged for observability |
| **category** | observability |
| **severity** | low |
| **status** | done |
| **discovered_in** | docs/BUILD_PLAN_SPRINTS.md Sprint 4 |
| **why_it_matters** | Harder to debug routing; no audit trail of classify → policy → execute. |
| **recommended_timing** | — |
| **resolved** | Implemented in Sprint 4. Router logs `route_decision` to `data/logs/events.jsonl` (intent, provider, source, msg_len). See docs/OBSERVABILITY.md. |

---

### IB-012

| Field | Value |
|-------|-------|
| **title** | Agent Designer: "create from design" overwrites without confirmation for existing agents |
| **category** | ux |
| **severity** | low |
| **status** | open |
| **discovered_in** | System 3 (Agent Designer) implementation |
| **why_it_matters** | Applying improved design to existing agent overwrites ROLE.md, TOOLS.json. No undo. |
| **recommended_timing** | Add confirmation or backup-before-overwrite when improving agents |

---

### IB-013

| Field | Value |
|-------|-------|
| **title** | Persist orchestration plans |
| **category** | observability |
| **severity** | medium |
| **status** | done |
| **discovered_in** | System 4 planning stage |
| **why_it_matters** | Intent Orchestrator will generate plans, but no artifact system planned. Plans disappear; hard to debug reasoning. |
| **recommended_timing** | System 4.1. Store under `data/orchestration/<timestamp>-plan.json` with request, plan, chosen action, reasoning summary. |
| **resolved** | System 4.1 implemented. Plans saved to `data/orchestration/<timestamp>-plan.json`. Commands: `list orchestration plans`, `show orchestration plan <id>`. |

---

### IB-014

| Field | Value |
|-------|-------|
| **title** | Version example agents |
| **category** | developer-experience |
| **severity** | low |
| **status** | open |
| **discovered_in** | Agent Factory review |
| **why_it_matters** | All agents live under `data/agents/` (not versioned). No canonical example agents; harder onboarding. |
| **recommended_timing** | System 2.2. Add `templates/agents/examples/` (e.g. market_researcher, builder, operations_manager). |

---

### IB-015

| Field | Value |
|-------|-------|
| **title** | Agent memory growth management |
| **category** | scalability |
| **severity** | medium |
| **status** | open |
| **discovered_in** | Agent system review |
| **why_it_matters** | Agents append indefinitely to MEMORY.md. Will grow too large over time. |
| **recommended_timing** | System 2.3. Add periodic summarization, archive old memory, keep short working memory. Structure: MEMORY.md, memory_archive/, memory_summary.md. |

---

### IB-016

| Field | Value |
|-------|-------|
| **title** | Agent tool capability enforcement (when tool dispatch enabled) |
| **category** | security |
| **severity** | medium |
| **status** | open |
| **discovered_in** | Agent Factory review |
| **why_it_matters** | When agents gain tool dispatch (v1.2+), TOOLS.json must be enforced. Currently agents have no tool use; this is a prerequisite for safe tool dispatch. |
| **recommended_timing** | System 2.2. Add validation before agent execution when tool dispatch is implemented. |

---

### IB-017

| Field | Value |
|-------|-------|
| **title** | Agent execution history index |
| **category** | observability |
| **severity** | low |
| **status** | open |
| **discovered_in** | Agent system review |
| **why_it_matters** | Tasks and outputs stored as files; no index. Hard to query which agent did what, recent runs, failure patterns. |
| **recommended_timing** | System 2.3. Add `data/agent_runs/index.jsonl` with agent, task, timestamp, result summary. |

---

### IB-018

| Field | Value |
|-------|-------|
| **title** | Model profile validation |
| **category** | reliability |
| **severity** | medium |
| **status** | open |
| **discovered_in** | Model strategy review |
| **why_it_matters** | Agent Designer selects model profiles, but system assumes profile exists. Misconfigured profile could break execution. |
| **recommended_timing** | System 2.2. Validate model profiles during agent design, creation, and invocation. |

---

### IB-019

| Field | Value |
|-------|-------|
| **title** | Model usage logging |
| **category** | observability |
| **severity** | low |
| **status** | open |
| **discovered_in** | Model strategy review |
| **why_it_matters** | System does not track which model handled each request globally. |
| **recommended_timing** | Observability expansion. Log to `data/logs/model_usage.jsonl` with model, profile, request_type, latency. |

---

### IB-020

| Field | Value |
|-------|-------|
| **title** | Personal Context: controlled deletion API |
| **category** | ux |
| **severity** | low |
| **status** | open |
| **discovered_in** | Personal Context Engine review |
| **why_it_matters** | Personal context supports add/update but not delete. Users cannot clean up outdated entries. |
| **recommended_timing** | System 1.3. Add safe deletion commands. |

---

### IB-021

| Field | Value |
|-------|-------|
| **title** | Log rotation |
| **category** | stability |
| **severity** | medium |
| **status** | open |
| **discovered_in** | Observability review |
| **why_it_matters** | Logs append indefinitely. Disk growth over long periods. |
| **recommended_timing** | Observability expansion. Add log rotation. |

---

### IB-022

| Field | Value |
|-------|-------|
| **title** | Agent Designer: schema validation before creation |
| **category** | reliability |
| **severity** | medium |
| **status** | open |
| **discovered_in** | Agent Designer review |
| **why_it_matters** | Designer outputs depend on LLM formatting. Malformed designs could slip through without validation. |
| **recommended_timing** | System 3.1. Add schema validation before create/apply. |

---

### IB-023

| Field | Value |
|-------|-------|
| **title** | Capability registry for Intent Orchestrator |
| **category** | intelligence |
| **severity** | medium |
| **status** | done |
| **discovered_in** | Intent Orchestration planning |
| **why_it_matters** | Orchestrator will need to understand system capabilities. Currently capability discovery is implicit. |
| **recommended_timing** | System 4.2. Add `config/capabilities.json` listing tools, agents, system modules. |
| **resolved** | System 4.2 implemented. `config/capabilities.json`, `gerty/capability_registry.py`, `gerty/tools/capability_registry_tool.py`. Orchestrator uses registry in choose_action_path and suggest_missing_capability. |

---

### IB-024

| Field | Value |
|-------|-------|
| **title** | Intent Orchestrator: LLM-offline fallback is minimal |
| **category** | reliability |
| **severity** | low |
| **status** | open |
| **discovered_in** | System 4 (Intent Orchestrator) implementation |
| **why_it_matters** | When Ollama/OpenRouter unavailable, orchestrator returns generic "Rephrase your request" instead of keyword-based path selection. User gets no useful guidance. |
| **recommended_timing** | System 4.1. Add keyword-based fallback: when LLM fails, use classify_outcome_request + simple heuristics to suggest path. |

---

### IB-025

| Field | Value |
|-------|-------|
| **title** | Project Graph: no project status update command |
| **category** | ux |
| **severity** | low |
| **status** | open |
| **discovered_in** | System 5 (Project / Task Graph) v1 implementation |
| **why_it_matters** | Users can create projects and update task status, but cannot change project status (idea → planned → active → paused → completed → archived) via command. |
| **recommended_timing** | System 5.1. Add *update project &lt;slug&gt; to &lt;status&gt;* command. |

---

### IB-026

| Field | Value |
|-------|-------|
| **title** | Project Graph: no dependency cycle detection |
| **category** | reliability |
| **severity** | low |
| **status** | open |
| **discovered_in** | System 5 (Project / Task Graph) v1 implementation |
| **why_it_matters** | validate_project_graph checks that dependency references exist but does not detect cycles (task_001 → task_002 → task_001). Cycles would make suggest_next_task never return some tasks. |
| **recommended_timing** | System 5.1. Add cycle detection via DFS/topological sort in validate_project_graph. |

---

### IB-027

| Field | Value |
|-------|-------|
| **title** | Project Execution: no retry/rerun of failed tasks |
| **category** | ux |
| **severity** | low |
| **status** | open |
| **discovered_in** | System 5.1 (Project Execution Layer) v1 implementation |
| **why_it_matters** | Failed tasks are marked `blocked`. User must manually update status to `todo` before retrying. No "retry task" command. |
| **recommended_timing** | System 5.2. Add *retry task &lt;task_id&gt; in &lt;project&gt;* to reset blocked→todo and run again. |

---

### IB-028

| Field | Value |
|-------|-------|
| **title** | Opportunity Scanner: no status update command |
| **category** | ux |
| **severity** | low |
| **status** | open |
| **discovered_in** | System 6 (Opportunity Scanner) v1 implementation |
| **why_it_matters** | Users cannot change opportunity status (open → researching → shortlisted) via command. Must edit JSON manually. |
| **recommended_timing** | System 6.1. Add *update opportunity &lt;id&gt; to &lt;status&gt;* command. |

---

### IB-029

| Field | Value |
|-------|-------|
| **title** | Opportunity Scanner: no duplicate detection |
| **category** | reliability |
| **severity** | low |
| **status** | open |
| **discovered_in** | System 6 (Opportunity Scanner) v1 implementation |
| **why_it_matters** | Same title can create multiple opportunities with different timestamps. No warning for similar existing opportunities. |
| **recommended_timing** | System 6.1. Add similarity check (e.g. slug match) before create; optionally warn. |

---

## Adding New Items

Use this template:

```markdown
### IB-XXX

| Field | Value |
|-------|-------|
| **title** | One-line summary |
| **category** | security \| reliability \| ux \| design \| performance \| docs \| tech-debt \| observability \| intelligence \| scalability \| stability \| developer-experience |
| **severity** | critical \| high \| medium \| low |
| **status** | open \| in-progress \| deferred \| done |
| **discovered_in** | Where found |
| **why_it_matters** | Impact |
| **recommended_timing** | When to fix |
```

Assign the next sequential ID. When done, set status to `done` and add: `**resolved:** Brief note.`

---

### IB-030

| Field | Value |
|-------|-------|
| **title** | Capability Registry: keyword-based matching only |
| **category** | intelligence |
| **severity** | low |
| **status** | open |
| **discovered_in** | System 4.2 (Capability Registry) implementation |
| **why_it_matters** | `find_capabilities_for_request` uses substring/word overlap. No semantic embedding. May miss relevant capabilities for paraphrased requests. |
| **recommended_timing** | Consider embedding-based matching if keyword recall is insufficient. |

---

### IB-031

| Field | Value |
|-------|-------|
| **title** | Opportunity Scanner: no status update command |
| **category** | ux |
| **severity** | low |
| **status** | open |
| **discovered_in** | System 6.1 (Opportunity Research Execution) implementation |
| **why_it_matters** | `suggest_opportunity_status` recommends "update opportunity X to shortlisted" but that command does not exist. User cannot shortlist/reject via command. |
| **recommended_timing** | Add *update opportunity &lt;id&gt; to &lt;status&gt;* command. |

---

### IB-032

| Field | Value |
|-------|-------|
| **title** | OpenClaw bootstrap/tool context dominates first-turn token count (~10k) |
| **category** | performance |
| **severity** | low |
| **status** | done |
| **discovered_in** | Prompt bloat investigation (2026-03-14) |
| **why_it_matters** | Fresh "test" message: Gerty sends ~230 tokens; OpenClaw adds bootstrap files (USER.md, SOUL.md, etc.) and tool schemas before OpenRouter. Final input ~10k tokens. Expected OpenClaw design, not Gerty bug. |
| **recommended_timing** | Bootstrap cleanup sprint first. See docs/CONTEXT_BUDGET_DESIGN.md. |
| **resolved** | Bootstrap cleanup v1: HEARTBEAT excluded, AGENTS slimmed. Bootstrap files ~7k chars (~1.7k tokens) vs ~16k before. See docs/OPENCLAW_BOOTSTRAP.md. |

---

### IB-033

| Field | Value |
|-------|-------|
| **title** | OpenClaw HEARTBEAT.md injected on every turn |
| **category** | performance |
| **severity** | low |
| **status** | done |
| **discovered_in** | Context budget audit (2026-03-14) |
| **why_it_matters** | HEARTBEAT.md (~820 tokens) is for proactive-agent cron polls. Injected on every chat turn. Wasteful for ad-hoc "test" messages. |
| **recommended_timing** | Bootstrap cleanup. Check if OpenClaw supports conditional bootstrap (e.g. promptMode, source) to exclude HEARTBEAT.md for non-heartbeat turns. |
| **resolved** | Renamed HEARTBEAT.md → HEARTBEAT_PROACTIVE.md. OpenClaw no longer finds HEARTBEAT.md; proactive script instructs agent to read HEARTBEAT_PROACTIVE.md on demand. |

---

### IB-034

| Field | Value |
|-------|-------|
| **title** | AGENTS.md is Cursor-oriented, verbose for OpenClaw chat |
| **category** | design |
| **severity** | low |
| **status** | done |
| **discovered_in** | Context budget audit (2026-03-14) |
| **why_it_matters** | AGENTS.md (~1,235 tokens) includes "Every Session: Read SOUL.md", Heartbeats, Proactive Work—targeted at Cursor agents. OpenClaw chat gets full file every turn. |
| **recommended_timing** | Create AGENTS_CORE.md (~1k chars) with safety + identity refs; use for OpenClaw bootstrap. Keep full AGENTS.md for Cursor. |
| **resolved** | AGENTS.md slimmed (~828 chars). Full content in AGENTS_FULL.md. Cursor/agents read AGENTS_FULL.md per AGENTS.md pointer. |

---

### IB-035

| Field | Value |
|-------|-------|
| **title** | Context Budget Manager for long conversations |
| **category** | design |
| **severity** | medium |
| **status** | open |
| **discovered_in** | Context budget design (2026-03-14) |
| **why_it_matters** | As chats grow, context can approach model limits. No summarization or budget awareness. Risk of truncation, degraded replies. |
| **recommended_timing** | After bootstrap cleanup. Implement v1: token estimation, budget metrics, headroom reserve, over-threshold warning. See docs/CONTEXT_BUDGET_DESIGN.md. |

---

### IB-036

| Field | Value |
|-------|-------|
| **title** | Grounded Planning Mode: keyword-only detection, no memory integration |
| **category** | intelligence |
| **severity** | low |
| **status** | open |
| **discovered_in** | Grounded Planning Mode v1 implementation (2026-03-14) |
| **why_it_matters** | Planning mode uses phrase matching; may miss paraphrased requests. Recent memory (memory/*.md) not included in context. |
| **recommended_timing** | v1.1. Consider LLM-based planning intent classification; add memory/*.md to sources when relevant. |

---

### IB-037

| Field | Value |
|-------|-------|
| **title** | Grounded Planning v2: section-based extraction may miss unstructured content |
| **category** | intelligence |
| **severity** | low |
| **status** | open |
| **discovered_in** | Grounded Planning Mode v2 implementation (2026-03-14) |
| **why_it_matters** | Extraction relies on ##/### markdown headings. Content without clear headings may be omitted. |
| **recommended_timing** | v2.1. Consider fallback to first-N for files with weak heading structure. |

---

### IB-038

| Field | Value |
|-------|-------|
| **title** | Model Routing v1: no fallback when preferred model fails at runtime |
| **category** | reliability |
| **severity** | low |
| **status** | open |
| **discovered_in** | Model Routing v1 implementation (2026-03-14) |
| **why_it_matters** | If the selected model (e.g. OLLAMA_REASONING_MODEL) is not pulled or fails, the router returns an error. No automatic retry with fallback model. |
| **recommended_timing** | v1.1. Add try-preferred-then-fallback when model call fails. |

---

### IB-039

| Field | Value |
|-------|-------|
| **title** | Execution Boundary v1: deterministic keyword detection may misclassify edge cases |
| **category** | intelligence |
| **severity** | low |
| **status** | open |
| **discovered_in** | Execution Boundary v1 implementation (2026-03-14) |
| **why_it_matters** | "Edit the README" vs "how do I edit the README" — first implies action, second is advice. Phrase-based detection may misclassify. |
| **recommended_timing** | v1.1. Consider intent+context refinement or LLM-based boundary when uncertain. |

---

### IB-040

| Field | Value |
|-------|-------|
| **title** | Capability Registry v1: no intent-to-capability sync; manual config drift risk |
| **category** | design |
| **severity** | low |
| **status** | open |
| **discovered_in** | Capability Registry v1 implementation (2026-03-14) |
| **why_it_matters** | Router intents (INTENT_*) and capability registry are maintained separately. New intents require manual config/capabilities.json update. Drift can cause capability_for_intent to return None. |
| **recommended_timing** | v1.1. Consider intent constants as source for capability_id mapping, or validation script that checks intent coverage. |

---

### IB-041

| Field | Value |
|-------|-------|
| **title** | Inspection-First v1: deterministic detection may miss paraphrased requests |
| **category** | intelligence |
| **severity** | low |
| **status** | open |
| **discovered_in** | Inspection-First Mode v1 implementation (2026-03-14) |
| **why_it_matters** | "Analyze our setup" or "what should we fix first" may not trigger inspection-first. User gets generic advice instead of inspected-state response. |
| **recommended_timing** | v1.1. Expand phrase list or add keyword scoring similar to grounded planning. |
| **resolved** | v2 implemented: broader phrases, keyword scoring. Some paraphrases (e.g. "give me a health check") may still miss. |

---

### IB-047

| Field | Value |
|-------|-------|
| **title** | Inspection-First: some paraphrased requests may still miss |
| **category** | intelligence |
| **severity** | low |
| **status** | open |
| **discovered_in** | Inspection-First v2 implementation |
| **why_it_matters** | Requests like "what needs attention" may not trigger inspection-first. |
| **recommended_timing** | v3.2. Expand keyword set if user feedback indicates misses. |
| **note** | v3.1 added health check, system health, sanity check, system audit, architecture review. |

---

### IB-048

| Field | Value |
|-------|-------|
| **title** | Inspection-First v3.1: instruction-only; model may still invent metrics or wrong IB |
| **category** | reliability |
| **severity** | low |
| **status** | open |
| **discovered_in** | Inspection-First v3.1 implementation |
| **why_it_matters** | IB reference card and "Do NOT invent" are instruction-only. No post-processing. Model may occasionally still output 8/10, wrong IB-015/016 attribution. |
| **recommended_timing** | v3.2. Consider lightweight output validation (regex for IB-xxx, scores) or structured output if live validation shows regression. |

---

### IB-042

| Field | Value |
|-------|-------|
| **title** | Stale tests assume pre–Execution Boundary routing (OpenClaw for chat/planning) |
| **category** | tech-debt |
| **severity** | high |
| **status** | done |
| **discovered_in** | Weakness audit 2026-03-14 |
| **why_it_matters** | 8 failing tests; Execution Boundary v1 routes planning/chat to native. Tests assert route=openclaw. CI red; tests need update to reflect actual behavior. |
| **recommended_timing** | Now. Update test_prompt_metrics, test_router, test_bootstrap_cleanup. |
| **resolved** | Hardening Sprint v1. Tests updated to use OpenClaw-required messages (calendar) when asserting OpenClaw path; planning/inspection assert native route. |

---

### IB-043

| Field | Value |
|-------|-------|
| **title** | HEARTBEAT.md still present at root; bootstrap cleanup incomplete |
| **category** | tech-debt |
| **severity** | high |
| **status** | done |
| **discovered_in** | Weakness audit 2026-03-14 |
| **why_it_matters** | IB-033 marked done but HEARTBEAT.md was not removed. Current HEARTBEAT.md says "Keep this file empty to skip heartbeat API calls" — may be intentional. test_heartbeat_excluded_from_bootstrap fails. |
| **recommended_timing** | Resolve: either remove HEARTBEAT.md (if OpenClaw should not find it) or update test to allow HEARTBEAT.md when it serves a purpose. |
| **resolved** | Hardening Sprint v1. HEARTBEAT.md removed. Proactive flow uses HEARTBEAT_PROACTIVE.md only. Regression fix 2026-03-14: file reappeared; removed again. Permanent fix 2026-03-14: trace audit found OpenClaw CLI recreates it; set `skipBootstrap: true` in ~/.openclaw/openclaw.json. See docs/HEARTBEAT_MD_RECREATION_TRACE.md. |

---

### IB-044

| Field | Value |
|-------|-------|
| **title** | apply_policy does not pass inspection-first to execution boundary |
| **category** | design |
| **severity** | medium |
| **status** | done |
| **discovered_in** | Weakness audit 2026-03-14 |
| **why_it_matters** | planning_triggered in apply_policy uses only grounded planning. When inspection-first triggers, boundary may still route to OpenClaw for some intents. |
| **recommended_timing** | Include get_inspection_block_for_message in planning_triggered check. |
| **resolved** | Hardening Sprint v1. apply_policy now sets planning_triggered = planning_result or inspection_result. |

---

### IB-045

| Field | Value |
|-------|-------|
| **title** | Duplicate _parse_markdown_sections in grounded_planning and inspection_first |
| **category** | tech-debt |
| **severity** | medium |
| **status** | done |
| **discovered_in** | Weakness audit 2026-03-14 |
| **why_it_matters** | Same logic in two modules; risk of divergence, double maintenance. |
| **recommended_timing** | Extract to gerty/utils/markdown_sections.py when touching these modules. |
| **resolved** | Maintenance Audit Sprint 2026-03-14. Extracted to gerty/utils/markdown_sections.py; both modules now import parse_markdown_sections and section_relevance_score. |

---

### IB-046

| Field | Value |
|-------|-------|
| **title** | test_maintenance_broader asserts exact LLM response; flaky |
| **category** | tech-debt |
| **severity** | medium |
| **status** | done |
| **discovered_in** | Weakness audit 2026-03-14 |
| **why_it_matters** | Test fails when provider/model returns different content. Should assert routing only (tool_executor not called, provider=chat). |
| **recommended_timing** | Decouple from LLM output; assert routing behavior only. |
| **resolved** | Hardening Sprint v1. Patched gerty.settings.load to force provider=local; asserts tool_executor not called and mocked response. |
