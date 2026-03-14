# HEARTBEAT.md Recreation Trace Audit

**Date:** 2026-03-14  
**Scope:** Strict trace audit for what recreates HEARTBEAT.md at project root.

---

## 1. Exact Source of Recreation

**Primary source: OpenClaw CLI**

When you run any of:

- `openclaw onboard`
- `openclaw configure`
- `openclaw setup`

OpenClaw creates the workspace and seeds bootstrap files **if they are missing**. HEARTBEAT.md is one of those bootstrap files.

From [docs.openclaw.ai/concepts/agent-workspace](https://docs.openclaw.ai/concepts/agent-workspace):

> `openclaw onboard`, `openclaw configure`, or `openclaw setup` will create the workspace and seed the bootstrap files if they are missing.
>
> `openclaw setup` can recreate missing defaults without overwriting existing files.

The stub content matches the OpenClaw default template:

```
# HEARTBEAT.md
# Keep this file empty (or with only comments) to skip heartbeat API calls.
# Add tasks below when you want the agent to check something periodically.
```

From [open-claw.bot/docs/cli/reference/templates/heartbeat](https://open-claw.bot/docs/cli/reference/templates/heartbeat/).

---

## 2. File / Path / Function / Script Responsible

| Component | Location | Role |
|-----------|----------|------|
| **OpenClaw CLI** | `openclaw` (npm package) | Seeds bootstrap files when workspace/bootstrap files are missing |
| **Commands** | `openclaw onboard`, `openclaw configure`, `openclaw setup` | Trigger bootstrap file creation |
| **Workspace** | `agents.defaults.workspace` in `~/.openclaw/openclaw.json` | Target path for seeded files (Gerty project root) |
| **Secondary** | `skills/proactive-agent/SKILL.md` line 86 | Instructs: `cp assets/*.md ./` — copies HEARTBEAT.md from assets (full checklist, not stub) |

**Note:** The proactive-agent `cp assets/*.md ./` would produce a different file (full checklist). The recurring stub is from OpenClaw CLI.

---

## 3. Gerty-Side vs OpenClaw-Side

| Side | Responsible? | Details |
|------|---------------|---------|
| **OpenClaw** | **Yes** | CLI seeds HEARTBEAT.md when bootstrap files are missing |
| **Gerty** | No | No Gerty code writes or copies HEARTBEAT.md |
| **Proactive-agent skill** | Partial | SKILL.md instructs manual `cp assets/*.md ./`; that would copy the full checklist, not the stub |

---

## 4. Whether Removal Is Safe Permanently

**Yes, removal is safe** from Gerty’s perspective:

- Gerty does not depend on HEARTBEAT.md.
- Proactive flow uses HEARTBEAT_PROACTIVE.md only.
- OpenClaw injects a “missing file” marker in the prompt when HEARTBEAT.md is absent; it does not fail.

**But:** Any future run of `openclaw onboard`, `openclaw configure`, or `openclaw setup` will recreate HEARTBEAT.md if it is missing.

---

## 5. Recommended Permanent Fix

### Option A: Disable OpenClaw Bootstrap Seeding (Recommended)

Add to `~/.openclaw/openclaw.json`:

```json5
{
  "agents": {
    "defaults": {
      "skipBootstrap": true
    }
  }
}
```

From [docs.openclaw.ai/concepts/agent-workspace](https://docs.openclaw.ai/concepts/agent-workspace):

> If you already manage the workspace files yourself, you can disable bootstrap file creation:
> `{ agent: { skipBootstrap: true } }`

Gerty manages its own workspace files (USER.md, SOUL.md, AGENTS.md, etc.), so disabling OpenClaw bootstrap seeding is appropriate.

### Option B: Post-Setup Cleanup Script

If you must run `openclaw onboard`/`configure`/`setup` occasionally, add a cleanup step:

```bash
# After openclaw onboard/configure/setup
rm -f /home/liam/gerty/HEARTBEAT.md
```

### Option C: Update Proactive-Agent SKILL.md (Optional)

The proactive-agent Quick Start says `cp assets/*.md ./`, which would copy HEARTBEAT.md. To avoid that:

- Exclude HEARTBEAT.md from the copy, or
- Document that Gerty uses HEARTBEAT_PROACTIVE.md and HEARTBEAT.md should not be copied.

This only affects manual setup; it does not stop OpenClaw CLI from recreating the stub.

---

## Summary

| Question | Answer |
|----------|--------|
| **Exact source** | OpenClaw CLI (`openclaw onboard`, `openclaw configure`, `openclaw setup`) |
| **File/script** | OpenClaw npm package bootstrap seeding logic |
| **Gerty vs OpenClaw** | OpenClaw-side |
| **Removal safe?** | Yes; OpenClaw will recreate it on next onboard/configure/setup |
| **Permanent fix** | Set `agents.defaults.skipBootstrap: true` in `~/.openclaw/openclaw.json` |

---

## Other Bootstrap Files That Could Be Recreated (Without skipBootstrap)

If `skipBootstrap` were not set, OpenClaw would seed these when missing:

| File | Gerty status | Risk |
|------|--------------|------|
| HEARTBEAT.md | Removed; use HEARTBEAT_PROACTIVE.md | **High** — Recreated by onboard/configure/setup; conflicts with bootstrap cleanup |
| IDENTITY.md | Not used (Gerty uses SOUL.md) | Low — Would add redundant file |
| BOOTSTRAP.md | Brand-new only; deleted after use | Low — One-time; Gerty workspace is not brand-new |
| BOOT.md | Optional startup checklist | Low — Unlikely to be created |
| USER.md, SOUL.md, AGENTS.md, TOOLS.md, MEMORY.md | Gerty-owned; already exist | None — OpenClaw would not overwrite existing |

With `skipBootstrap: true`, none of these are created.

---

## Config Safety Confirmation

`skipBootstrap: true` disables **only** bootstrap file seeding (creating missing files when running onboard/configure/setup). It does **not** affect:

- Bootstrap **injection** — OpenClaw still reads and injects existing workspace files (USER.md, SOUL.md, AGENTS.md, TOOLS.md, MEMORY.md) into the prompt
- Session handling, tool execution, or other OpenClaw behavior
- Gerty’s routing or OpenClaw integration

Gerty owns and maintains these files at project root; OpenClaw should not create or overwrite them. Safe for this setup.

---

## Applied (2026-03-14)

- **Config:** `agents.defaults.skipBootstrap: true` added to `~/.openclaw/openclaw.json`
- **HEARTBEAT.md:** Removed from project root
- **Docs:** OPENCLAW_BOOTSTRAP.md, OPENCLAW_INTEGRATION.md updated to state Gerty owns workspace bootstrap files and OpenClaw seeding is disabled
