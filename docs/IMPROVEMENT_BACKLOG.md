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
| **status** | open |
| **discovered_in** | System 3 (Agent Designer) implementation |
| **why_it_matters** | Designs stored only in `_last_design` (current tool instance). Disappear on Gerty restart, tool reload, or session reset. User may lose work; prevents long-running design workflows. |
| **recommended_timing** | System 3.1. Persist under `data/agent_designs/<agent_name>.json` with full spec, timestamp, model profile, design prompt, suggested tools. |

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
| **status** | open |
| **discovered_in** | System 4 planning stage |
| **why_it_matters** | Intent Orchestrator will generate plans, but no artifact system planned. Plans disappear; hard to debug reasoning. |
| **recommended_timing** | System 4.1. Store under `data/orchestration/<timestamp>-plan.json` with request, plan, chosen action, reasoning summary. |

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
| **status** | open |
| **discovered_in** | Intent Orchestration planning |
| **why_it_matters** | Orchestrator will need to understand system capabilities. Currently capability discovery is implicit. |
| **recommended_timing** | System 4.2. Add `config/capabilities.json` listing tools, agents, system modules. |

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
