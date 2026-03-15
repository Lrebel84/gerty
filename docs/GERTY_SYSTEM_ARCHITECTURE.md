# GERTY SYSTEM ARCHITECTURE

## Unified System Overview and Current Development State

This document is the consolidated reference for the current Gerty system. It combines prior development-session summaries into one up-to-date overview and reflects the latest architectural understanding from the codebase.

Gerty should be understood as **one unified system**. OpenClaw is not a separate assistant sitting beside Gerty; it is part of Gerty's execution layer and must be designed, upgraded, and governed as part of the same architecture.

This document covers:

* system philosophy
* core architecture
* subsystem layout
* request flow
* OpenClaw's role inside the system
* major upgrades completed
* runtime governance and stabilization
* current health
* known weaknesses
* next development priorities

---

# 1. Core Philosophy

Gerty is being developed as a **structured personal AI operating system**, not just a conversational chatbot.

The emphasis is on the architecture around the model so the system becomes:

* reliable
* inspectable
* governable
* safe to extend
* maintainable over time

The core principles are:

## 1.1 Artifact-First Design

Important actions produce persistent artifacts.

Examples include:

```text
data/projects/
data/agents/
data/opportunities/
data/orchestration/
data/logs/
```

This gives:

* inspectability
* recoverability
* debuggability
* transparency

## 1.2 Controlled Autonomy

Gerty avoids uncontrolled background behaviour.

The system does not rely on:

* background autonomous loops
* recursive uncontrolled agent spawning
* silent system mutation
* unbounded execution

Autonomy must be explicit, bounded, and observable.

## 1.3 Explicit Orchestration

Requests are routed deliberately through a structured decision process rather than letting the model improvise capabilities.

## 1.4 Capability Awareness

Gerty should know what it can already do before suggesting new tools, new agents, or unsupported actions.

This is grounded in:

```text
config/capabilities.json
```

## 1.5 Continuous Improvement

Weaknesses are tracked explicitly in:

```text
docs/IMPROVEMENT_BACKLOG.md
```

This keeps the system evolving through controlled iteration instead of drift.

---

# 2. Unified System Architecture

Gerty is a **single integrated system** with multiple coordinated layers.

OpenClaw is part of the execution path, not a separate product or assistant.

## 2.1 High-Level Structure

```text
User Interfaces
(Chat UI, Voice, Telegram)
        ↓
Pipeline
        ↓
Router
(classify → policy → execute)
        ↓
Execution Path
   ├─ Native / fast reasoning path
   ├─ OpenClaw execution path
   └─ Tool / chat handling
        ↓
Artifacts, logs, and state
```

This is the top-level operational flow.

## 2.2 Architectural Split

### Gerty core is responsible for:

* reasoning
* planning
* routing
* governance
* system awareness
* memory control
* deciding when tools should be used

### OpenClaw is responsible for:

* tool execution
* integration access
* external actions
* bounded tool-oriented reasoning

The key rule is:

**Gerty and OpenClaw must be treated as one unified architecture.**

---

# 3. Core Subsystems

## System 1 — Personal Context Engine

Location:

```text
data/personal_context/
```

Purpose:

Stores Liam's:

* goals
* ideas
* projects
* routines
* preferences
* business concepts

The Personal Context Engine supports structured updates rather than opaque memory blobs.

---

## System 2 — Agent Factory

Location:

```text
data/agents/
```

Purpose:

Creates structured agent definitions.

Typical structure:

```text
data/agents/<agent_name>/

agent.json
ROLE.md
TOOLS.json
MEMORY.md
tasks/
outputs/
```

Agents define:

* purpose
* responsibilities
* inputs
* outputs
* constraints
* success criteria

---

## System 2.1 — Agent Invocation

Agents can be run through commands such as:

```text
ask agent <name>: <task>
run agent <name>: <task>
```

Execution flow:

```text
load agent context
resolve model profile
build prompt
invoke model
write output artifacts
```

Outputs are written into the agent artifact structure.

---

## System 3 — Agent Designer

Purpose:

Create and refine high-quality agent specifications with LLM assistance.

Artifacts are stored under:

```text
data/agent_designs/
```

This system helps formalize agents before they are created or run.

---

## System 4 — Intent Orchestrator

Purpose:

Interpret some natural-language requests and recommend an internal action path.

Important clarification:

The Intent Orchestrator is **not** the top-level router for the whole product. It is a **tool/path** triggered for certain orchestration-style prompts, typically via orchestrator keywords.

It may recommend actions such as:

* direct answer
* run agent
* design agent
* create project structure
* recommend tool
* escalate maintenance

---

## System 4.2 — Capability Registry

Location:

```text
config/capabilities.json
```

Purpose:

Provides a canonical map of what the system can do and which execution path owns each capability.

Examples include:

```text
calendar → native (GoogleWorkspaceTool, read-only)
gmail → native (GoogleWorkspaceTool, read-only)
drive → native (GoogleWorkspaceTool, read-only)
```

This registry helps prevent:

* tool hallucination
* duplicate capability invention
* unclear ownership

Current limitation:

Capability matching is still primarily keyword-based rather than semantic.

---

## System 5 — Project / Task Graph

Location:

```text
data/projects/
```

Structure:

```text
data/projects/<project_slug>/

project.json
tasks.json
README.md
notes/
outputs/
```

This supports structured project management inside Gerty.

---

## System 5.1 — Project Execution Layer

Allows project tasks to be executed through assigned agents.

Typical flow:

```text
validate dependencies
invoke assigned agent
write artifact output
update task metadata
```

Safety constraints include:

* one task at a time
* no recursive uncontrolled execution
* no background loops

---

## System 6 — Opportunity Scanner

Location:

```text
data/opportunities/
```

Purpose:

Track and evaluate product or business opportunities.

Opportunity records include fields such as:

* title
* description
* category
* status
* score
* suggested next step

---

## System 6.1 — Opportunity Research Execution

Allows opportunities to be researched through agents and written back as artifacts.

This keeps business exploration structured and inspectable.

---

# 4. Request Flow

The current main operational flow is:

```text
User
  ↓
Pipeline
  ↓
Router
  ↓
Path selection:
  - native/fast reasoning
  - OpenClaw execution
  - tools/chat handling
```

This is the core production path.

The Intent Orchestrator sits inside this broader architecture as a specialized orchestration mechanism for certain request types, rather than acting as the primary entrypoint for everything.

---

# 5. OpenClaw's Role Inside Gerty

OpenClaw should be treated as Gerty's controlled execution environment.

**OpenClaw is the default execution owner for:**

* dynamic capability execution
* Google Workspace writes (gog: create event, send email, Sheets/Docs)
* web search and browse
* app launch and browser control
* file editing
* skill install/create

**Gerty owns:**

* Personal context, memory shaping, intent understanding
* Safety policy (screen_openclaw_message, autonomy gates)
* Routing and orchestration (when to use native vs OpenClaw)
* Read-only native tools (calendar list, email list, drive list) for speed
* Governance (model lock, bootstrap ownership, diagnostics)

**Principle:** Build on top of OpenClaw, not around it. Do not create inferior native replacements for capabilities OpenClaw already provides well.

The most recent architectural lesson is:

**Gerty must be upgraded as one unified system, not "Gerty + OpenClaw."**

Any change to OpenClaw changes Gerty's behaviour and governance envelope, so integration decisions must always be evaluated at system level.

---

# 6. Major Architectural Upgrades Completed

## 6.1 Prompt Architecture v2

Prompt structure was simplified and cleaned up to reduce duplication and prompt-layer confusion.

## 6.2 Grounded Planning Mode

Planning prompts now pull from project documentation, including sources such as:

```text
BUILD_PLAN_PROGRESS
IMPROVEMENT_BACKLOG
GERTY_OVERVIEW
GERTY_VISION
```

This improved the grounding of planning responses.

## 6.3 Inspection-First Mode

System-analysis prompts can trigger an inspection path that reads documentation and capability context before answering.

This reduces unsupported guessing and increases system-specific reasoning.

## 6.4 Execution Boundary

A dedicated execution-boundary layer now helps determine whether a request should stay in native reasoning or go to OpenClaw/tool execution.

## 6.5 Capability Registry v1

A canonical registry was established to define capability ownership and route selection.

## 6.6 Google Workspace Routing (Phase 3.0A, Stabilization Reset)

**Stabilization mode (default):** Single-backend. All calendar/email/drive → OpenClaw/gog. `GERTY_GOOGLE_NATIVE_ENABLED=0`. See docs/STABILIZATION_RESET_PLAN.md.

**Legacy dual-path:** Set `GERTY_GOOGLE_NATIVE_ENABLED=1` for read → native GoogleWorkspaceTool; write → OpenClaw/gog. Routing invariant: never route a write request to the read-only native provider. See docs/GOOGLE_WORKSPACE_STATUS.md.

**Desktop runtime integrity:** Empty-output hints now use OpenClaw/gog remediation (not native OAuth). Runtime report at `/api/runtime-integrity`. See docs/DESKTOP_RUNTIME_INTEGRITY.md.

## 6.7 Phase 3.0A — OpenClaw Capability Audit and Recovery

Empirical audit of OpenClaw capabilities; write-intent routing regression fixed; gog restored as first-class path for writes; OpenClaw-First Policy (docs/OPENCLAW_FIRST_POLICY.md) to prevent inferior native replacements. See docs/OPENCLAW_CAPABILITY_AUDIT.md, docs/OPENCLAW_WOW_FACTOR_TASKS.md.

## 6.8 Bootstrap Cleanup

Bootstrap prompt load was reduced significantly by cleaning up bootstrap files and reducing excess context.

---

# 7. Runtime Stabilization and Governance Work

A major stabilization effort was completed after discovering that the architecture was sound but runtime behaviour was not yet controlled tightly enough.

## 7.1 Problems Found

The system previously suffered from:

* multiple model usage
* autonomous OpenClaw behaviours
* opaque memory influence
* persistent historical contamination in OpenClaw sessions
* model selection drift caused by persisted settings
* behavioural inconsistency across runs

## 7.2 OpenClaw Governance Lockdown

Autonomous and experimental behaviours were disabled or constrained.

Disabled items included:

* proactive-agent
* self-improving-agent
* autonomous research loops
* proactive cron-driven behaviour

Important correction:

`subagents.maxConcurrent` was **not** reduced to 0 in the final working state.
The current configuration uses:

```text
subagents.maxConcurrent = 1
```

because gog requires it to be greater than 0.

That means OpenClaw has been constrained, but not in a way that breaks required integration behaviour.

## 7.3 Model Governance Lockdown

A key issue was uncontrolled model usage.

The final enforced Gerty-side constant is:

```text
LOCKED_OPENROUTER_MODEL = "openai/gpt-oss-120b"
```

Important distinction:

* **Gerty router / OpenRouter API format:** `openai/gpt-oss-120b`
* **OpenClaw config/catalog context:** `openrouter/openai/gpt-oss-120b`

This distinction matters and should not be blurred.

The result is that model governance is now enforced correctly at the routing/configuration level rather than being left to UI state.

## 7.4 OpenClaw Memory Reset

Legacy OpenClaw memory, transcripts, and related state were archived under:

```text
docs/archive/
```

This removed historical contamination from the active runtime context.

## 7.5 Bootstrap Ownership

OpenClaw's tendency to recreate bootstrap files such as `HEARTBEAT.md` was addressed through:

```text
skipBootstrap: true
```

in the OpenClaw config.

This means workspace bootstrap ownership remains with Gerty rather than being silently regenerated by OpenClaw.

## 7.6 Maintenance Audit

A maintenance pass removed technical drift, fixed regressions, aligned docs, and strengthened validation.

---

# 8. Current System Health

Current repo-verified status is:

## Runtime

Stable.

## Model governance

Single governed model path enforced.

## OpenClaw role

Controlled execution layer inside the Gerty system.

## Tests

* **574 tests collected**
* **575 passed** (per BUILD_PLAN_PROGRESS documentation)

Run `python3 -m pytest --co -q` and `python3 -m gerty --validate` to verify current counts.

## Diagnostics

These are present and implemented:

```text
--validate
--diagnose
--governance
```

---

# 9. Known Weaknesses

The main remaining issues are quality and capability maturity issues, not foundational architecture failures.

## 9.1 Assistant Response Quality

Sometimes the assistant still:

* overstates architecture details
* gives generic recommendations instead of Gerty-specific reasoning
* repeats backlog themes too mechanically
* includes outdated framing

This is a reasoning-quality problem.

## 9.2 Tool Dispatch Reliability

Backlog item:

```text
IB-001
```

This is the issue about the system inventing responses instead of using tools when tools should be used.

This remains open.

## 9.3 Memory Growth / Context Bloat

Backlog item:

```text
IB-015
```

Long-session context growth still needs a proper management strategy.

## 9.4 Semantic Capability Matching

Backlog item:

```text
IB-030
```

Capability matching is still keyword-driven and would benefit from semantic retrieval.

---

# 10. Important Corrections to Earlier Framing

## 10.1 IB-009 is no longer open

Skills registry drift is **not** an open weakness anymore.

IB-009 is done, with sync enforcement covered by tests such as:

```text
tests/test_skills_sync.py
```

So this should be treated as completed, not as roadmap work.

## 10.2 IB-016 is not the fix for IB-001

These are different backlog items.

* **IB-001** = tool invention / answering instead of using tools
* **IB-016** = future enforcement of agent `TOOLS.json` when agents gain tool dispatch

IB-016 should not be described as the direct fix for IB-001.

---

# 11. Development Priorities Going Forward

The system has moved out of architecture stabilization and into refinement.

**Current build plan:** [docs/PHASE_3_1_BUILD_PLAN.md](PHASE_3_1_BUILD_PLAN.md) — Phase 3.1 Foundational Assistant Reliability. Work through in sprints; update the plan with completion status as we progress.

Best next priorities are:

## Near-term (Phase 3.1)

* intent taxonomy and routing reliability
* deterministic intent-to-capability mapping
* Gmail / Calendar / Drive / local PC task coverage
* tool-grounded response behavior and anti-speculation
* golden prompt evaluation suite and friction logging

## Medium-term

* context budget / memory growth management
* semantic capability matching
* stronger tool-dispatch enforcement
* continued quality improvements in inspection and planning behaviour

---

# 12. Key Lessons Learned

## 12.1 Runtime governance matters as much as architecture

A good architecture can still behave badly if runtime controls are weak.

## 12.2 Router-level enforcement matters

UI settings and persisted config can override intended behaviour unless model and policy decisions are locked at the correct layer.

## 12.3 Transparency tools are essential

Inspection and diagnostic tools were critical for exposing model leaks, memory influence, and runtime drift.

## 12.4 Logs are more trustworthy than model self-reporting

Observed runtime behaviour must be validated from logs and code paths, not from what the model says about itself.

## 12.5 OpenClaw must be evaluated as part of Gerty, not beside it

This is the most important current architectural conclusion. OpenClaw changes system behaviour, governance, and execution quality, so it must be treated as part of the whole Gerty architecture.

---

# 13. Current Development Phase

The project has transitioned from:

```text
architecture stabilization
```

to:

```text
assistant quality improvement
```

The foundation is now strong enough that the next gains come from improving:

* response accuracy
* system-aware reasoning
* tool-use correctness
* context discipline
* execution reliability

---

# Conclusion

Gerty is no longer just an experimental assistant prototype.

It is now a structured AI operating system with:

* artifact persistence
* capability awareness
* orchestration layers
* governed execution
* integrated OpenClaw tooling
* explicit improvement tracking

The core architectural direction is now stable.

The next phase is about making the system **more intelligent, more grounded, and more reliable in how it uses the architecture that is already in place**.
