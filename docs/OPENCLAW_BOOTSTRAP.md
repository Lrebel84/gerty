# OpenClaw Bootstrap

> What OpenClaw injects into the system prompt. See [docs/CONTEXT_BUDGET_DESIGN.md](CONTEXT_BUDGET_DESIGN.md) for audit and design.

## Gerty Owns Workspace Bootstrap Files

Gerty manages workspace bootstrap files (USER.md, SOUL.md, AGENTS.md, TOOLS.md, MEMORY.md) at project root. OpenClaw bootstrap **seeding** (creating missing files) is intentionally disabled via `agents.defaults.skipBootstrap: true` in `~/.openclaw/openclaw.json`. This prevents OpenClaw from recreating HEARTBEAT.md or other default templates when running `openclaw onboard`, `openclaw configure`, or `openclaw setup`. OpenClaw still **injects** existing workspace files into the prompt; it just does not create them.

## Bootstrap Files (OpenClaw-Injected)

OpenClaw reads from the workspace root (`agents.defaults.workspace` in `~/.openclaw/openclaw.json`) and injects these files under "Project Context":

| File | Status | Purpose |
|------|--------|---------|
| USER.md | **Always** | Human context, goals, preferences |
| SOUL.md | **Always** | Agent identity, principles, boundaries |
| AGENTS.md | **Always** | Core operating rules (slim for OpenClaw) |
| TOOLS.md | **Always** | Tool config, credentials location |
| IDENTITY.md | Optional | Not used by Gerty; missing-file marker if absent |
| HEARTBEAT.md | **Removed** | Renamed to HEARTBEAT_PROACTIVE.md; file removed from root. Proactive script reads HEARTBEAT_PROACTIVE.md on demand. |
| MEMORY.md | If present | Long-term memory template |
| BOOTSTRAP.md | Brand-new only | One-time setup; deleted after use |

**Order (per OpenClaw):** HEARTBEAT.md, USER.md, IDENTITY.md, TOOLS.md, SOUL.md, AGENTS.md. Missing files inject a short marker.

## Gerty Bootstrap Cleanup (v1)

- **HEARTBEAT.md → HEARTBEAT_PROACTIVE.md** — Excluded from always-on bootstrap. Proactive script (`scripts/proactive-heartbeat.sh`) instructs agent to read HEARTBEAT_PROACTIVE.md when heartbeat runs. Saves ~820 tokens per normal chat turn.
- **AGENTS.md slimmed** — Full content in AGENTS_FULL.md. AGENTS.md now ~828 chars (core safety, external vs internal, blockers, verify-before-narrate). Saves ~1,000 tokens per turn.

## Prompt Architecture v2

- **Planning Protocol** (AGENTS.md) — For architecture/improvement requests: consider system state, identify biggest bottleneck, recommend ONE prioritized improvement with rationale, avoid generic checklists.
- **Tool awareness** (OPENCLAW_TOOL_INSTRUCTIONS) — Before generic advice, consider Gerty capabilities: create agents, run research agents, create projects, manage opportunities, execute tasks.
- **Grounded Planning Mode v2** (Gerty-side) — For strategic/planning requests, Gerty extracts relevant sections from BUILD_PLAN_PROGRESS, IMPROVEMENT_BACKLOG, GERTY_OVERVIEW, GERTY_VISION and injects planning context before sending to OpenClaw. See [GROUNDED_PLANNING_MODE.md](GROUNDED_PLANNING_MODE.md).
- **Inspection-First Mode v1** (Gerty-side) — For review/audit/inspect requests, Gerty inspects extended docs + capability registry before answering. Stricter than grounded planning; takes precedence when triggered. See [INSPECTION_FIRST_MODE.md](INSPECTION_FIRST_MODE.md).
- **Capability Registry v1** — Canonical map of native vs OpenClaw capabilities; Google Workspace (calendar, Gmail, Drive) → gog skill. See [CAPABILITY_REGISTRY.md](CAPABILITY_REGISTRY.md).
- **No template duplication** — Only one active version per file. OpenClaw injects: USER.md, SOUL.md, AGENTS.md, TOOLS.md, MEMORY.md. No *_TEMPLATE.md in workspace root.

## Configuration

### skipBootstrap (Gerty setup)

```json
{
  "agents": {
    "defaults": {
      "skipBootstrap": true
    }
  }
}
```

Disables OpenClaw’s bootstrap file seeding. Gerty owns workspace files; OpenClaw must not recreate HEARTBEAT.md or other defaults. See [HEARTBEAT_MD_RECREATION_TRACE.md](HEARTBEAT_MD_RECREATION_TRACE.md).

### bootstrapMaxChars

Cap per-file size. In `~/.openclaw/openclaw.json`:

```json
{
  "agents": {
    "defaults": {
      "bootstrapMaxChars": 8000
    }
  }
}
```

Default: 20000. Lower values truncate large files earlier.

### bootstrapTotalMaxChars

Total bootstrap context limit (if supported by your OpenClaw version).

## Conditional Loading

OpenClaw does **not** support conditional bootstrap by mode. Files are hardcoded. Workarounds:

- **Exclude file:** Rename so OpenClaw doesn't find it (e.g. HEARTBEAT.md → HEARTBEAT_PROACTIVE.md). Agent reads on demand when instructed.
- **Shrink file:** Replace with minimal content; full content elsewhere.

## Tool Schemas

OpenClaw always injects tool schemas (exec, read, write, files, web_search, etc.). Gerty cannot change this. Tool schema scope is controlled by OpenClaw config (`tools.allow`, `tools.alsoAllow`).

## Audit

Run `python scripts/audit_bootstrap_sizes.py` to measure current bootstrap file sizes.

## Heartbeat Flow

1. Cron runs `scripts/proactive-heartbeat.sh`
2. Script sends: "Read USER.md. Read and run HEARTBEAT_PROACTIVE.md checklist. Use web_search..."
3. Agent reads HEARTBEAT_PROACTIVE.md (not in bootstrap) and runs checklist
4. Findings appended to `notes/areas/proactive-updates.md`

## Bootstrap Memory Influence (State Boundary)

**MEMORY.md** and possibly **memory/*.md** are injected by OpenClaw on every request. This is not equivalent to Gerty-native memory only:

- OpenClaw reads these files from the workspace; Gerty does not send them.
- The proactive agent (HEARTBEAT_PROACTIVE.md) instructs: "Update MEMORY.md with distilled insights" and "Write them to memory/YYYY-MM-DD.md".
- Proactive agent writes to MEMORY.md and memory/*.md influence **later normal Gerty chat** without explicit user awareness.
- "New chat" does not clear these files; they persist in the workspace.

**Visibility:** Run `python -m gerty --inspect-openclaw-context` to see modification times and proactive influence.

See [OPENCLAW_STATE_BOUNDARY.md](OPENCLAW_STATE_BOUNDARY.md) for full boundary documentation.
