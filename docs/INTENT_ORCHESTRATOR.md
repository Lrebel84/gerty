# Intent Orchestrator (System 4)

> **Purpose:** Interpret natural-language outcome requests and choose the best internal path so Liam does not need to remember commands, agent names, folder paths, or system mechanics.

---

## What It Is

The Intent Orchestrator is a planner/orchestrator layer that sits between high-level user requests and Gerty's internal capabilities. When you say things like:

- "Help me explore tattoo-related AI business ideas"
- "I want to turn this into a real project"
- "Build whatever agent we need for researching this"
- "If we do not have the right tool, propose one"
- "What is the best next step for this goal?"

…the orchestrator interprets the request, decides the best path, and either:

1. **Returns a plan/recommendation** (default for broad or ambiguous requests)
2. **Invokes the chosen path directly** (when the request is simple and safe)

---

## Action Paths

The orchestrator can recommend one of these internal paths:

| Path | Description |
|------|--------------|
| `direct_answer` | Answer directly (factual, opinion, explanation) |
| `use_tool` | Use an existing Gerty tool (time, notes, search, rag, calendar, etc.) |
| `run_agent` | Invoke an existing agent by name for a bounded task |
| `design_agent` | Design or suggest a new agent via the Agent Designer |
| `create_project_structure` | Set up project/task structure (notes, areas, ideas) |
| `recommend_new_tool` | Propose a new tool/capability we don't have |
| `escalate_to_maintenance` | Log as maintenance task for later |

---

## Output Structure

The orchestrator returns a structured result:

```json
{
  "request_type": "simple|broad|ambiguous|specific",
  "recommended_action": "direct_answer|use_tool|run_agent|...",
  "reasoning_summary": "1-2 sentence explanation",
  "tool_name": null,
  "agent_name": null,
  "needs_new_agent": false,
  "needs_new_tool": false,
  "suggested_next_step": "What to do next",
  "safe_to_execute_now": true
}
```

---

## What It Does in v1

- **Analyzes** high-level outcome requests via keyword classification + LLM
- **Classifies** request type (simple, broad, ambiguous, specific)
- **Chooses** the best action path from available tools and agents
- **Builds** an execution plan (steps, summary)
- **Suggests** missing capabilities when the user asks for something we don't have
- **Optionally invokes** when `safe_to_execute_now` and we have a clear tool/agent match
- **Preserves** existing direct command behavior (list agents, my goals, ask agent X: task, etc.)

---

## What It Explicitly Does NOT Do (v1)

- **No background autonomy** — does not run loops or scheduled tasks
- **No recursive multi-agent chains** — does not spawn agents that spawn agents
- **No shell/code execution** — never runs arbitrary commands
- **No arbitrary file writes** — only uses safe paths (notes, maintenance, agent factory)
- **No automatic system modification** — does not change config or install things without approval
- **No silent creation** — does not create multiple agents/tools without clear user intent
- **No OpenClaw routing changes** — OpenClaw flow is unchanged

---

## Routing

The orchestrator is triggered by **keywords** that indicate high-level outcome requests:

- `help me explore`
- `help me organize`
- `turn this into`
- `build whatever agent`
- `if we don't have the right tool` / `if we do not have the right tool`
- `propose one`
- `best next step`
- `what's the best way to`
- `what is the best next step`
- `organize this`
- `what should i do`
- `how do i get started`
- `i want to turn this into`

**Precedence:** Direct commands still win. The orchestrator is checked *after* agent designer, agent runner, and agent factory. So:

- "list agents" → agent_factory (unchanged)
- "ask agent X: task" → agent_runner (unchanged)
- "design agent: name - role" → agent_designer (unchanged)
- "help me explore tattoo AI ideas" → intent_orchestrator

---

## Example Flows

### Example 1: "Help me explore tattoo-related AI business ideas"

1. Router matches `help me explore` → `intent_orchestrator`
2. Orchestrator analyzes → may recommend `run_agent` (market_researcher) or `design_agent`
3. If `market_researcher` exists and `safe_to_execute_now`: invokes agent
4. Otherwise: returns plan with "suggest agent for: tattoo-related AI business ideas"

### Example 2: "I want to turn this into a real project"

1. Router matches `turn this into` → `intent_orchestrator`
2. Orchestrator recommends `create_project_structure` or `design_agent`
3. Returns plan: "Add project: <name> or add idea: <description>"

### Example 3: "If we do not have the right tool, propose one"

1. Router matches `if we do not have the right tool` → `intent_orchestrator`
2. Orchestrator recommends `recommend_new_tool`
3. Calls `suggest_missing_capability` → returns suggested tool + rationale

### Example 4: "What is the best next step for this goal?"

1. Router matches `best next step` → `intent_orchestrator`
2. Orchestrator analyzes context, recommends path
3. Returns plan with suggested next step

---

## Modules

| Module | Responsibility |
|--------|----------------|
| `gerty/intent_orchestrator.py` | `analyze_request`, `classify_outcome_request`, `choose_action_path`, `build_execution_plan`, `suggest_missing_capability` |
| `gerty/tools/intent_orchestrator_tool.py` | Tool that receives orchestrator intents, calls orchestrator, optionally invokes chosen path |

---

## Assumptions and Limitations

- **LLM-dependent:** Classification and path selection use Ollama or OpenRouter. Offline/LLM-unavailable: falls back to safe defaults.
- **No persistence:** Orchestration plans are not persisted across sessions (see IB-013 in Improvement Backlog).
- **No capability registry:** Tools/agents are discovered at runtime from router and agent_registry; no central capability registry yet (see IB-023).
- **Conservative invocation:** v1 only invokes when `safe_to_execute_now` and we have a clear tool/agent; broad requests get plans only.

---

## Related

- [AGENT_DESIGNER.md](AGENT_DESIGNER.md) — System 3, agent design/improvement
- [AGENT_FACTORY.md](AGENT_FACTORY.md) — System 2, agent creation
- [IMPROVEMENT_BACKLOG.md](IMPROVEMENT_BACKLOG.md) — IB-013 (persist plans), IB-023 (capability registry)
