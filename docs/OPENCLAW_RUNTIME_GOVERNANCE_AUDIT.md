# OpenClaw Runtime Governance Audit

**Date:** 2026-03-15  
**Scope:** Full audit of OpenClaw runtime environment to enforce strict governance.  
**Intent:** Identify why multiple models appear in OpenRouter logs, Grok-style responses, autonomous skills, and uncontrolled memory influence. Audit only — no modifications.

**Follow-up:** Lockdown v1 implemented 2026-03-15. See [OPENCLAW_LOCKDOWN_V1_REPORT.md](OPENCLAW_LOCKDOWN_V1_REPORT.md).

---

## 1. OpenClaw Runtime Architecture

### 1.1 Current Configuration

| Component | Location | Value |
|-----------|----------|-------|
| **OpenClaw config** | `~/.openclaw/openclaw.json` | agents.defaults.model.primary = openai/gpt-oss-120b |
| **OpenClaw models** | `~/.openclaw/openclaw.json` | openrouter/auto (removed); openai/gpt-oss-120b only |
| **Workspace** | `agents.defaults.workspace` | /home/liam/gerty |
| **Auth** | openrouter:default | API key from ~/.openclaw/.env |
| **Tools** | tools.profile | coding; alsoAllow: group:web, group:plugins, openclaw-shield, knostic_shield |
| **Subagents** | agents.defaults.subagents.maxConcurrent | 8 |

### 1.2 Gerty → OpenClaw Flow

1. Gerty router classifies intent → apply_policy → execution boundary
2. When OpenClaw path: Gerty calls `openclaw_execute(message, history, system_context)`
3. Gerty builds payload: `[System: context]` + `Previous conversation` + `message`
4. OpenClaw SDK sends to gateway; **Gerty does not specify model** — OpenClaw uses its own config
5. OpenClaw gateway injects bootstrap files (USER, SOUL, AGENTS, TOOLS, MEMORY, memory/*) from workspace
6. OpenClaw selects model per session/channel config; executes tools; returns response

### 1.3 Session Keys Observed

| Session key | Purpose |
|-------------|---------|
| agent:main:gerty | Gerty chat (SDK) |
| agent:main:main | Control UI / default |
| agent:main:cron:* | Proactive heartbeat (system cron) |

**Evidence:** `~/.openclaw/agents/main/sessions/b23af1bb-*.jsonl` contains `modelId: x-ai/grok-4.1-fast` — proactive cron session used Grok, not GPT-OSS-120B.

---

## 2. Model Usage Explanation

### 2.1 Why GPT-OSS-120B, Grok-4.1-fast, and Claude-3.5-Sonnet Were Called

| Model | Likely Source | Evidence |
|-------|---------------|----------|
| **GPT-OSS-120B** | OpenClaw primary (openai/gpt-oss-120b) | openclaw.json agents.defaults.model.primary; sessions.json model |
| **Grok-4.1-fast** | Proactive cron session; web search; or openrouter/auto | Session b23af1bb shows modelId: x-ai/grok-4.1-fast; proactive cron runs with different session |
| **Claude-3.5-Sonnet** | Gerty fallback (OPENROUTER_MODEL default); agent_runner planning_review; or openrouter/auto | config.py OPENROUTER_MODEL=anthropic/claude-3.5-sonnet; model_profiles.json planning_review: anthropic/claude |

### 2.2 All LLM Call Paths Identified

| Path | Component | Model Source | Notes |
|------|-----------|--------------|-------|
| **Gerty direct (native)** | router._execute_route | Ollama or OpenRouter | Gerty model routing; OPENROUTER_MODEL, OPENROUTER_REASONING_MODEL, etc. |
| **Gerty web intent fallback** | _classify_web_intent_fallback | openai/gpt-4o-mini (hardcoded) | When Ollama down; classifies web_lookup vs web_research |
| **Gerty OpenClaw path** | openclaw.client.execute | **OpenClaw** — Gerty does not control | OpenClaw uses agents.defaults.model.primary |
| **Proactive cron** | scripts/proactive-heartbeat.sh → openclaw agent --to | **OpenClaw** — may use different session/channel | Session transcript shows Grok; cron may have different model |
| **Gerty agent_runner** | agent_runner.run_agent | config/model_profiles.json | general_reasoning, coding_heavy, research_heavy, planning_review — each maps to different model |
| **OpenClaw tools** | web_search, web_fetch | OpenClaw internal | BRAVE_API_KEY or PERPLEXITY_API_KEY — may use external APIs; tool results returned to main model |
| **openrouter/auto** | OpenClaw models alias | OpenRouter auto-routing | Selects from curated set (GPT, Grok, Claude, etc.) per prompt complexity |
| **Self-improving-agent** | sessions_spawn, sub-agents | OpenClaw / skill | Can spawn sub-agents; model may inherit or differ |
| **Proactive-agent** | Spawn research agents | Skill instructions | Instructs agent to "Spawn research agents", "isolated agentTurn" |

### 2.3 openrouter/auto Risk

OpenClaw config has `agents.defaults.models.openrouter/auto` as alias. If any code path or tool uses `openrouter/auto`, OpenRouter's auto-router selects the "best" model from a curated set — **explaining multiple models in logs**.

---

## 3. Installed Skill Ecosystem Analysis

### 3.1 All Installed Skills

| Skill | Origin | Location | Description |
|-------|--------|----------|-------------|
| **proactive-agent** | ClawHub | skills/proactive-agent | Proactive, self-improving architecture; WAL Protocol, Working Buffer, Autonomous Crons |
| **self-improving-agent** | ClawHub | skills/self-improving-agent | Logs learnings, errors, corrections; sessions_spawn for sub-agents |
| **gog** | ClawHub | skills/gog | Google Workspace CLI (Gmail, Calendar, Drive, etc.) |
| **calendar** | Local | skills/calendar | Gerty calendar script via exec |
| **dcg-guard** | ClawHub | skills/dcg-guard | Blocks destructive commands |
| **openclaw-shield** | Local | skills/openclaw-shield | Plugin: audit mode; promptGuard/securityGate off |
| **playwright-scraper-skill** | ClawHub | skills/playwright-scraper-skill | Browser automation |

### 3.2 Skill Capabilities

| Skill | Spawns agents? | Retries? | Model override? | File access? | Memory? |
|-------|----------------|----------|-----------------|--------------|---------|
| **proactive-agent** | Yes — "Spawn research agents", "isolated agentTurn" | Yes — "Try 10 approaches" | No explicit | MEMORY.md, memory/*, notes/areas/* | Writes to MEMORY.md, memory/*.md |
| **self-improving-agent** | Yes — sessions_spawn, sessions_send | Via instructions | No explicit | .learnings/, SOUL.md, AGENTS.md, TOOLS.md | Promotes to workspace files |
| **gog** | No | No | No | No | No |
| **calendar** | No | No | No | Exec only | No |
| **dcg-guard** | No | No | No | No | No |
| **openclaw-shield** | No | No | No | No | No |
| **playwright-scraper-skill** | No | No | No | No | No |

### 3.3 Proactive-Agent Details

- **Autonomous vs Prompted Crons:** Uses `systemEvent` vs `isolated agentTurn` for background work
- **Instructs:** "Spawn research agents", "isolated agentTurn Spawns sub-agent that executes autonomously"
- **Writes:** MEMORY.md, memory/*.md, notes/areas/proactive-updates.md, notes/areas/proactive-ideas.md
- **Self-healing:** "Fix its own issues", "Try 10 approaches before asking for help
- **Relentless resourcefulness:** Spawn research agents, check GitHub issues

### 3.4 Self-Improving-Agent Details

- **sessions_spawn:** Spawn sub-agent for background work
- **sessions_send:** Send learning to another session
- **sessions_history:** Read another session's transcript
- **Hook:** agent:bootstrap — injects reminder to check .learnings/
- **Promotion:** Learnings → SOUL.md, AGENTS.md, TOOLS.md

---

## 4. Cron / Background Task Analysis

### 4.1 System Crontab

| Schedule | Script | Purpose |
|----------|--------|---------|
| `0 */4 * * *` | /home/liam/gerty/scripts/proactive-heartbeat.sh | Proactive heartbeat every 4 hours |

### 4.2 Proactive Heartbeat Script

```bash
MSG="HEARTBEAT: Read USER.md for search priorities. Read and run HEARTBEAT_PROACTIVE.md checklist. Use web_search for 1-2 items relevant to Liam's goals (Gerty, AI-run businesses, UK tech). Append findings to notes/areas/proactive-updates.md. Output a brief summary (3-5 lines) to stdout."
openclaw agent --to 5789425841 --message "$MSG" --deliver >> /home/liam/gerty/logs/proactive.log 2>&1
```

- **Schedule:** Every 4 hours (0, 4, 8, 12, 16, 20)
- **Uses:** OpenClaw agent with HEARTBEAT_PROACTIVE.md checklist
- **Web search:** Yes — 1–2 items
- **Writes:** notes/areas/proactive-updates.md
- **Model:** OpenClaw session; session b23af1bb used **Grok-4.1-fast**
- **Session:** `--to 5789425841` (Telegram channel) — may use different session model config

### 4.3 OpenClaw Built-in Cron

```json
~/.openclaw/cron/jobs.json: { "version": 1, "jobs": [] }
```

**Empty** — no OpenClaw cron jobs. Proactive heartbeat is system cron only.

### 4.4 Files Written by Background Tasks

| File | Written by | Purpose |
|------|------------|---------|
| notes/areas/proactive-updates.md | Proactive agent | Research findings |
| notes/areas/proactive-ideas.md | Proactive agent |
| MEMORY.md | Proactive agent (per HEARTBEAT_PROACTIVE) | Distilled insights |
| memory/YYYY-MM-DD.md | Proactive agent |
| logs/proactive.log | proactive-heartbeat.sh | Stdout/stderr |

---

## 5. Memory Influence Analysis

### 5.1 Memory Sources Influencing Responses

| Source | Injected when? | Controlled by | Persists across sessions? |
|--------|----------------|---------------|---------------------------|
| **USER.md** | Every OpenClaw request | Gerty (workspace) | Yes |
| **SOUL.md** | Every OpenClaw request | Gerty | Yes |
| **AGENTS.md** | Every OpenClaw request | Gerty | Yes |
| **TOOLS.md** | Every OpenClaw request | Gerty | Yes |
| **MEMORY.md** | Every OpenClaw request (if present) | Proactive agent writes | Yes |
| **memory/*.md** | Possibly every request | Proactive agent writes | Yes |
| **notes/areas/proactive-updates.md** | Not in bootstrap | Proactive agent | Yes |
| **OpenClaw session transcript** | Merged with payload? | OpenClaw | Until clear_session |
| **OpenClaw memory DB** | main.sqlite; memory tool | OpenClaw | Until full reset |
| **.learnings/** | Self-improving-agent | Skill | Yes |

### 5.2 Proactive → Normal Chat Flow

1. Cron runs proactive-heartbeat.sh every 4h
2. Proactive agent uses web_search, writes to notes/areas/proactive-updates.md
3. HEARTBEAT_PROACTIVE instructs: "Update MEMORY.md with distilled insights", "Write them to memory/YYYY-MM-DD.md"
4. OpenClaw bootstrap injects MEMORY.md and memory/*.md on **every** request
5. **Result:** Proactive research enters normal Gerty chat responses without explicit user awareness

**Evidence:** notes/areas/proactive-updates.md contains "2026-03-14: UK AI grant funding...", "Innovate UK Business Connect...". MEMORY.md and memory/*.md are in bootstrap.

---

## 6. Autonomous Agent Behavior Analysis

### 6.1 Behaviors Detected

| Behavior | Present? | Where | How |
|----------|----------|-------|-----|
| **Self-improving agents** | Yes | self-improving-agent skill | sessions_spawn, promote learnings |
| **Retry agents** | Possible | Proactive agent instructions | "Try 10 approaches", "Spawn research agents" |
| **Planning agents** | Possible | Proactive agent | "isolated agentTurn" for background work |
| **Research agents** | Yes | Proactive agent instructions | "Spawn research agents", web_search |
| **Recursive agents** | Possible | sessions_spawn | Sub-agent could spawn |
| **Tool retry loops** | Unknown | OpenClaw internal | Not documented |

### 6.2 Subagent Configuration

```json
agents.defaults.subagents: { "maxConcurrent": 8 }
```

OpenClaw allows up to 8 concurrent subagents. Skills can spawn them.

### 6.3 Gerty-Side vs OpenClaw-Side

| Component | Autonomous? | Notes |
|-----------|-------------|-------|
| **Gerty agent_runner** | No | Single-shot, no recursive spawn; "Execute only this task. Do not spawn other agents" |
| **Gerty subagent_roles** | Opt-in | Observer, Diagnoser, Planner, Validator — used in self-improvement pipeline only |
| **OpenClaw** | Yes | Skills can spawn; proactive agent instructs spawning |
| **Proactive-agent skill** | Yes | Autonomous crons, spawn research agents |
| **Self-improving-agent** | Yes | sessions_spawn, sessions_send |

---

## 7. Prompt Injection Sources

### 7.1 Injected Files (OpenClaw Bootstrap)

| File | Injected when | Content |
|------|---------------|---------|
| USER.md | Every request | Liam's context, goals, preferences, proactive search focus |
| SOUL.md | Every request | Gerty identity, principles, personality |
| AGENTS.md | Every request | Safety, planning protocol |
| TOOLS.md | Every request | Tool config |
| MEMORY.md | If present | Long-term memory |
| memory/*.md | Possibly | Daily notes |
| HEARTBEAT.md | If present | Removed in Gerty; marker if missing |

### 7.2 Additional Injection Paths

| Source | When | Notes |
|--------|------|-------|
| **Gerty system_context** | OPENCLAW_TOOL_INSTRUCTIONS | Appended to every OpenClaw payload |
| **Gerty planning/inspection** | When triggered | Grounded planning or inspection-first context prepended |
| **Self-improving-agent hook** | agent:bootstrap | Injects reminder to check .learnings/ |
| **Skill SKILL.md** | On demand | Model reads via `read` tool when instructed |
| **HEARTBEAT_PROACTIVE.md** | Proactive cron only | Explicitly in message |

### 7.3 OpenClaw Hidden Instructions

- OpenClaw builds system prompt from: workspace files, tool schemas, session context
- **Not documented:** Whether OpenClaw adds internal instructions beyond bootstrap
- **openrouter/auto:** If used, could add routing metadata

---

## 8. Governance Risks

### 8.1 Model Usage Risks

| Risk | Severity | Description |
|------|----------|-------------|
| **Multiple models** | High | GPT-OSS, Grok, Claude observed; no single-model lock |
| **openrouter/auto** | High | Alias in config; auto-routes to "best" model |
| **Per-session model** | High | Proactive cron session used Grok; session/channel may override |
| **Agent runner profiles** | Medium | model_profiles.json: Claude, Kimi, DeepSeek; agent_runner uses these |
| **Gerty fallback** | Medium | OPENROUTER_MODEL=anthropic/claude-3.5-sonnet; web fallback uses gpt-4o-mini |

### 8.2 Autonomous Behavior Risks

| Risk | Severity | Description |
|------|----------|-------------|
| **Proactive cron** | High | Runs every 4h; writes to memory; influences normal chat |
| **Skill spawning** | High | Proactive-agent, self-improving-agent instruct spawn |
| **Subagent concurrency** | Medium | maxConcurrent: 8; skills can spawn |
| **Self-improving promotion** | Medium | Writes to SOUL.md, AGENTS.md, TOOLS.md |

### 8.3 Memory Influence Risks

| Risk | Severity | Description |
|------|----------|-------------|
| **Proactive → bootstrap** | High | Proactive writes MEMORY.md, memory/*; bootstrap injects on every request |
| **Session transcript** | Medium | Unknown if merged with payload; may add prior context |
| **Memory DB** | Medium | main.sqlite; not cleared by New chat |
| **.learnings/** | Low | Self-improving-agent; not in bootstrap |

### 8.4 Personality Risks

| Risk | Severity | Description |
|------|----------|-------------|
| **Grok personality** | High | When Grok used, responses may have Grok tone |
| **SOUL.md** | Medium | Defines "Gerty" personality; may conflict with model personality |
| **Proactive instructions** | Medium | HEARTBEAT_PROACTIVE has personality cues |

---

## 9. Recommended Remediation Plan

### 9.1 Model Lock (GPT-OSS-120B Only)

| Action | Location | Change |
|--------|----------|--------|
| **Remove openrouter/auto** | ~/.openclaw/openclaw.json | Delete from agents.defaults.models |
| **Lock primary** | ~/.openclaw/openclaw.json | Ensure agents.defaults.model.primary = openai/gpt-oss-120b |
| **Per-session override** | Check sessions | Ensure no session/channel overrides to Grok/Claude |
| **Gerty OPENROUTER_MODEL** | .env | Set to openai/gpt-oss-120b for consistency |
| **model_profiles.json** | config/model_profiles.json | Set all profiles to openai/gpt-oss-120b |
| **Web intent fallback** | router.py | Change gpt-4o-mini to gpt-oss-120b or remove |

### 9.2 Skills to Disable or Remove

| Skill | Recommendation | Reason |
|-------|----------------|-------|
| **proactive-agent** | **Disable or remove** | Spawns agents, writes to memory, runs every 4h, autonomous |
| **self-improving-agent** | **Disable or remove** | sessions_spawn, promotes to workspace |

**Keep:** gog, calendar, dcg-guard, openclaw-shield (audit mode). playwright-scraper-skill — evaluate per use case.

### 9.3 Cron/Background Tasks

| Action | Recommendation |
|--------|----------------|
| **Proactive cron** | Remove from crontab or disable script |
| **OpenClaw cron** | Already empty |

### 9.4 Memory Governance

| Action | Recommendation |
|--------|----------------|
| **Proactive → MEMORY.md** | Stop proactive agent; or exclude MEMORY.md, memory/* from bootstrap when source=chat |
| **Bootstrap** | skipBootstrap already true; no new files from OpenClaw |

### 9.5 Autonomous Behavior

| Action | Recommendation |
|--------|----------------|
| **subagents.maxConcurrent** | Set to 0 to disable subagent spawning |
| **Skill removal** | Remove proactive-agent, self-improving-agent |

---

## 10. How to Enforce Single-Model Usage

### 10.1 OpenClaw Configuration

```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "openai/gpt-oss-120b"
      },
      "models": {
        "openai/gpt-oss-120b": {}
      },
      "subagents": {
        "maxConcurrent": 0
      }
    }
  }
}
```

- Remove `openrouter/auto` from models
- Set subagents.maxConcurrent to 0
- Verify no per-channel or per-session model overrides

### 10.2 Gerty Configuration

- `.env`: OPENROUTER_MODEL=openai/gpt-oss-120b
- `config/model_profiles.json`: All profiles → openai/gpt-oss-120b
- `config.py`: OPENROUTER_MODEL default = openai/gpt-oss-120b

### 10.3 Verification

- Run OpenClaw; inspect session logs for modelId
- Check OpenRouter usage dashboard for model distribution
- Remove proactive cron; verify no Grok/Claude calls

---

## 11. Remaining Risks

| Risk | Mitigation |
|------|-------------|
| **OpenClaw internal model selection** | Unknown if OpenClaw uses model for tool calls (e.g. web_search) |
| **Skill reinstall** | clawhub install could re-add proactive-agent |
| **Session config drift** | Sessions may have cached model overrides |
| **OpenRouter auto** | If used elsewhere, could still route |
| **Telegram channel** | --to 5789425841 may have different model config |

---

## 12. Files Inspected

- ~/.openclaw/openclaw.json
- ~/.openclaw/cron/jobs.json
- ~/.openclaw/agents/main/sessions/sessions.json
- ~/.openclaw/agents/main/sessions/b23af1bb-*.jsonl (excerpt)
- gerty/gerty/config.py
- gerty/gerty/llm/router.py
- gerty/gerty/model_routing.py
- gerty/gerty/openclaw/client.py
- gerty/gerty/agent_runner.py
- gerty/config/model_profiles.json
- gerty/scripts/proactive-heartbeat.sh
- gerty/HEARTBEAT_PROACTIVE.md
- gerty/USER.md, SOUL.md, AGENTS.md
- gerty/notes/areas/proactive-updates.md
- gerty/skills/proactive-agent/SKILL.md
- gerty/skills/self-improving-agent/SKILL.md
- gerty/skills/self-improving-agent/hooks/openclaw/HOOK.md
- gerty/skills/gog/SKILL.md
- gerty/skills/calendar/SKILL.md
- gerty/docs/OPENCLAW_PERSISTENCE_AUDIT.md
- gerty/docs/OPENCLAW_BOOTSTRAP.md
- gerty/docs/OPENCLAW_INTEGRATION.md
- crontab -l

---

## 13. Summary

| Aspect | Current State | Governance Target |
|--------|---------------|-------------------|
| **Model** | GPT-OSS, Grok, Claude observed | GPT-OSS-120B only |
| **OpenClaw** | Autonomous agent platform | Controlled execution layer |
| **Skills** | proactive-agent, self-improving-agent spawn | Remove or disable |
| **Cron** | Proactive every 4h | Disable |
| **Memory** | Proactive writes influence chat | Stop proactive; or isolate |
| **Subagents** | maxConcurrent: 8 | 0 |

**Verdict:** OpenClaw currently behaves as an **autonomous agent platform** (B), not a controlled execution layer (A). Multiple models, proactive cron, skill spawning, and memory influence from background tasks all conflict with Gerty's governance goals.
