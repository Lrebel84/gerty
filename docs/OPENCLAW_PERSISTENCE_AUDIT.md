# OpenClaw Persistence and Hidden State Audit

**Date:** 2026-03-14  
**Scope:** OpenClaw daemon, Gerty integration, skills, proactive-agent, workspace files.  
**Intent:** Map the boundary between Gerty-managed state and OpenClaw-managed state; identify hidden or indirect memory paths.

---

## 1. Confirmed Persistent State Locations

### OpenClaw daemon (gateway host)

| Location | Type | Purpose |
|----------|------|---------|
| `~/.openclaw/agents/main/sessions/sessions.json` | JSON | Session metadata (sessionId, updatedAt, systemSent). Keys: `agent:main:gerty`, `agent:main:main`, `agent:main:cron:*`. |
| `~/.openclaw/agents/main/sessions/*.jsonl` | JSONL | Per-session conversation transcripts. Example: `b23af1bb-*.jsonl` (674KB), `9f46fd37-*.jsonl` (65KB). |
| `~/.openclaw/memory/main.sqlite` | SQLite | Memory tool storage: `chunks`, `meta`, `files`, `embedding_cache`, FTS tables. 69KB; 1 meta row, 0 chunks at audit time. |
| `~/.openclaw/cron/jobs.json` | JSON | Cron job definitions. |
| `~/.openclaw/cron/runs/*.jsonl` | JSONL | Cron run outputs (e.g. proactive heartbeat runs). |
| `~/.openclaw/openclaw.json` | JSON | Config: workspace, tools, session.dmScope, etc. |
| `~/.openclaw/credentials/google-token.json` | JSON | Google OAuth token (used by gog skill). |
| `~/.openclaw/identity/device-auth.json` | JSON | Device auth for gateway. |
| `~/.openclaw/exec-approvals.json` | JSON | Exec allowlist. |

**Session keys observed:** `agent:main:gerty` (Gerty SDK), `agent:main:main` (Control UI / default), `agent:main:cron:*` (proactive heartbeat).

### Gerty project (workspace root)

| Location | Type | Purpose |
|----------|------|---------|
| `data/chat_history.json` | JSON | Gerty-managed chat history. Cleared on "New chat". |
| `MEMORY.md` | Markdown | Long-term memory. **Injected by OpenClaw bootstrap** on every request. |
| `memory/*.md` | Markdown | Daily notes. **Possibly injected** — docs reference it; not in sessions.json bootstrap list. HEARTBEAT_PROACTIVE instructs writing here. |
| `notes/areas/proactive-updates.md` | Markdown | Proactive-agent findings. **Written by OpenClaw** (proactive cron). Not in bootstrap list. |
| `notes/areas/proactive-ideas.md` | Markdown | Proactive-agent ideas (HEARTBEAT_PROACTIVE instructs). |
| `logs/proactive.log` | Text | Proactive heartbeat stdout/stderr. |

**Critical:** OpenClaw bootstrap injects `MEMORY.md` from workspace (`agents.defaults.workspace` = `/home/liam/gerty`). Confirmed in `~/.openclaw/agents/main/sessions/sessions.json` injectedWorkspaceFiles. `memory/*.md` may be included per docs; not visible in that list. Gerty does not control this injection.

---

## 2. Transient-Only State Locations

| Location | Purpose |
|----------|---------|
| Gerty `build_openclaw_payload()` output | Per-request payload: [System] + Previous conversation + message. Not persisted by Gerty. |
| OpenClaw tool execution results | Returned to Gerty; not stored by Gerty. |

**Note:** OpenClaw persists session transcripts and may use the memory tool (main.sqlite). Those are OpenClaw-side, not Gerty-side.

---

## 3. Hidden or Indirect Memory Risks

### 3.1 Proactive agent writes → bootstrap injection

**Flow:**
1. Cron runs `scripts/proactive-heartbeat.sh` → `openclaw agent --to <telegram-id> --message "HEARTBEAT: ... Append findings to notes/areas/proactive-updates.md"`.
2. Proactive agent (OpenClaw) appends to `notes/areas/proactive-updates.md`.
3. HEARTBEAT_PROACTIVE.md instructs: "Update MEMORY.md with distilled insights" and "Write them to `memory/YYYY-MM-DD.md`".
4. OpenClaw bootstrap injects `MEMORY.md` and `memory/*.md` on **every** subsequent request (including normal Gerty chat).
5. **Result:** Proactive agent's writes to MEMORY.md and memory/*.md influence normal Gerty responses without explicit user awareness. The user may see "remembered" content that came from a cron job, not from the current conversation.

**Evidence:** `notes/areas/proactive-updates.md` contains entries like "2026-03-14: UK AI grant funding...". HEARTBEAT_PROACTIVE.md lines 93–94, 101–102.

### 3.2 OpenClaw session persistence vs Gerty history

**Flow:**
1. Gerty sends full history in payload (`build_openclaw_payload(message, history=...)`).
2. OpenClaw gateway stores session transcript in `~/.openclaw/agents/main/sessions/<sessionId>.jsonl`.
3. Session key for Gerty: `agent:main:gerty`.
4. When user clicks "New chat", Gerty calls `clear_session()` → `sessions_reset(agent:main:gerty)`.
5. **Unclear:** Does the gateway use only Gerty's payload for context, or does it merge with stored session transcript? OpenClaw docs state "Gateway is the source of truth" and sessions persist until reset. If the gateway prepends stored transcript to the payload, context could include prior turns even when Gerty sends "fresh" history. If the gateway replaces session with payload, behavior is aligned.

**Risk:** If session transcript is merged, OpenClaw could have more context than Gerty intends. If `clear_session()` fails (e.g. gateway unreachable), the session persists and may influence future turns.

### 3.3 OpenClaw memory tool (main.sqlite)

**Flow:**
1. OpenClaw has a `group:memory` tool (per OPENCLAW_INTEGRATION.md: "files, exec, sessions, memory, image").
2. `~/.openclaw/memory/main.sqlite` contains `chunks`, `meta`, `files`, `embedding_cache`.
3. **Not cleared by `clear_session()`:** `sessions_reset` affects the session store, not the memory DB.
4. **Result:** If OpenClaw's memory tool is used during a session, that data persists across "New chat" and can influence future responses. Gerty has no API to clear OpenClaw's memory DB.

### 3.4 notes/areas/* not in bootstrap

`notes/areas/proactive-updates.md` is written by the proactive agent but is **not** in the OpenClaw bootstrap file list (USER, SOUL, AGENTS, TOOLS, MEMORY, memory/*). So it is not auto-injected. The agent could read it via the `read` or `files` tool if instructed, but it is not part of the default context. Lower risk than MEMORY.md / memory/*.

### 3.5 ~/.openclaw/workspace vs agents.defaults.workspace

`~/.openclaw/workspace/` exists and contains copies of USER.md, SOUL.md, etc. The config `agents.defaults.workspace` is `/home/liam/gerty`. OpenClaw reads from the workspace path in config (Gerty project root), not necessarily from `~/.openclaw/workspace`. The `~/.openclaw/workspace` directory may be legacy or used for a different purpose. Confirm which path OpenClaw actually uses for bootstrap.

---

## 4. Can OpenClaw Influence Gerty Outside the Explicit Request Payload?

**Yes.**

| Path | Mechanism |
|------|------------|
| **Bootstrap files** | OpenClaw injects MEMORY.md, memory/*.md from workspace on every request. Gerty does not send these; OpenClaw reads them from disk. |
| **Session transcript** | If the gateway merges stored session with payload, prior turns in the session affect the response. |
| **Memory tool** | If the memory tool is used, main.sqlite persists facts. These can be retrieved in future turns. |
| **Proactive writes** | Proactive agent writes to MEMORY.md and memory/*.md. Those files are in the bootstrap set. Next normal chat gets them. |

**Gerty sends:** `[System: context]` + `Previous conversation: {history}` + `{message}`.  
**OpenClaw adds:** Bootstrap files (USER, SOUL, AGENTS, TOOLS, MEMORY, memory/*) + session transcript (if merged) + memory tool retrieval.

---

## 5. Recommended Fixes or Observability Additions

### 5.1 Document the boundary

- Add `docs/OPENCLAW_STATE_BOUNDARY.md` describing:
  - What Gerty controls: `data/chat_history.json`, `clear_session()` for `agent:main:gerty`.
  - What OpenClaw controls: `~/.openclaw/agents/main/sessions/*`, `~/.openclaw/memory/main.sqlite`, bootstrap injection.
  - Shared workspace files: MEMORY.md, memory/*.md — written by proactive agent, read by OpenClaw bootstrap.

### 5.2 Proactive → memory flow

- **Option A:** Exclude MEMORY.md and memory/* from bootstrap when the request originates from Gerty chat (requires OpenClaw feature).
- **Option B:** Document that proactive agent writes to MEMORY.md and memory/* influence normal chat. Add a note in HEARTBEAT_PROACTIVE.md and OPENCLAW_INTEGRATION.md.
- **Option C:** Use a separate file for proactive findings (e.g. `memory/proactive-YYYY-MM-DD.md`) and exclude it from bootstrap via naming or config, if OpenClaw supports it.

### 5.3 clear_session and memory DB

- **Check:** Does `sessions_reset` clear only session transcript, or also memory tool data? If memory persists, consider adding a Gerty command or script to clear OpenClaw memory when the user wants a full reset.
- **Document:** "New chat" clears Gerty history and OpenClaw session transcript; it does not clear OpenClaw memory DB.

### 5.4 Observability

- Log when OpenClaw bootstrap files (MEMORY.md, memory/*) are present and their approximate size. Add to `--inspect-prompt` or a new `--inspect-openclaw-context` command.
- Add a test: when `clear_session()` is called, verify `agent:main:gerty` is removed from sessions.json (or session transcript is cleared). Requires gateway access in test env.

### 5.5 Validation

- Add `python -m gerty --validate` check: if MEMORY.md or memory/*.md were modified in the last N hours and differ from a baseline, warn that proactive/cron may have written to them.

---

## 6. Verdict

**Unclear boundary.**

| Aspect | Status |
|--------|--------|
| **Session transcript** | OpenClaw persists; Gerty clears via `clear_session()`. Boundary is explicit for session. |
| **Bootstrap files** | OpenClaw injects MEMORY.md, memory/* on every request. Gerty does not control this. Shared, not Gerty-owned. |
| **Proactive → memory** | Proactive agent writes to MEMORY.md and memory/* per HEARTBEAT_PROACTIVE. Those files are in bootstrap. **Hidden path:** cron output influences normal chat. |
| **Memory tool (main.sqlite)** | Persists across sessions. Not cleared by `clear_session()`. Gerty has no API to clear it. |
| **notes/areas/proactive-updates.md** | Written by proactive; not in bootstrap. Lower risk. |

**Risks:**
1. User may believe "New chat" resets all context; OpenClaw memory DB and bootstrap files (MEMORY.md, memory/*) are not reset.
2. Proactive agent writes can make Gerty appear to "remember" things from a prior cron run.
3. Session merge behavior (payload vs stored transcript) is not fully documented; could lead to context duplication or unexpected retention.

**Recommendation:** Implement documentation (5.1, 5.2) and observability (5.4) first. Consider backlog items for: (a) documenting proactive→memory flow, (b) optional memory DB clear when user requests full reset, (c) validation check for recent MEMORY.md/memory/* changes.
