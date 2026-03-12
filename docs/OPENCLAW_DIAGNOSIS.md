# OpenClaw Diagnosis: Hallucination and Tool Use

## TL;DR

**OpenClaw/Grok sometimes returns plausible but invented responses** instead of using tools. On some setups, `openclaw agent --agent main --message 'Run: echo HELLO_VERIFY'` *does* execute and return real output—so tools can work. The problem is **inconsistent**: Grok sometimes uses tools, sometimes invents. There is also a known OpenClaw bug (#39971) where the main agent outputs tool-call text instead of executing; fix PR #43365 is open.

---

## What's Actually Happening

### The Flow (Correct Design)

1. **Gerty** → sends your message to OpenClaw via SDK (`agent.execute(message)`)
2. **OpenClaw Gateway** → receives it, runs the `main` agent
3. **Agent (Grok via OpenRouter)** → should: call tools (exec, web_search, etc.) → get real results → summarize for you
4. **Gerty** → displays the agent's response

### Observed Behaviour (Not Working as Expected)

In some cases, OpenClaw/Grok returns **invented** responses:

- Claims to have run commands that were never executed
- Invents skill names, URLs, and install success (e.g. "google-workspace-tools", "gmail-fetcher") that don't exist on ClawHub
- Uses non-existent commands (e.g. `openclaw skills install`—real command is `clawhub install`)

**Verification:** Running `openclaw agent --agent main --message 'Run: echo HELLO_VERIFY'` directly *can* return real `HELLO_VERIFY` output—so exec *does* work on some setups. The inconsistency suggests **Grok sometimes chooses not to use tools** and invents instead (model behaviour), rather than a universal tool-execution failure.

---

## Evidence

| What OpenClaw/Grok said | Reality |
|-------------------------|---------|
| `openclaw skills install https://clawhub.ai/...` | **No such command.** `openclaw skills` has `list`, `info`, `check` only. Real install: `clawhub install <name>` |
| Installed to `~/.openclaw/skills/google-workspace-tools` | **Directory doesn't exist.** No `~/.openclaw/skills/` at all |
| "google-workspace-tools" on ClawHub | **Not in search results.** Real hits: `google-workspace-mcp`, `gog`, `gws-workspace` |

---

## Possible Causes

### 1. Model behaviour (Grok not using tools)

Grok may sometimes skip tool calls and invent plausible answers. Direct `openclaw agent` tests that *do* return real exec output suggest tools can work—so the issue may be Grok's choice of when to use them.

### 2. OpenClaw bug #39971 (tool-call text instead of execution)

- **Issue:** [openclaw/openclaw#39971](https://github.com/openclaw/openclaw/issues/39971) — "main agent outputs tool call text instead of executing tools"
- **Fix PR:** [#43365](https://github.com/openclaw/openclaw/pull/43365) — "resolve main agent config when no sessionKey is provided"
- **Status:** Fix is **open**, not merged.

When affected: tool-policy resolution skips the main agent's config, so the agent emits tool-call text instead of invoking tools. If `openclaw agent --agent main --message 'Run: echo X'` returns `exec(command: "echo X")` as plain text (not real output), you're likely hitting this.

---

## Root Cause: tools.allow vs tools.alsoAllow

**If `tools.allow: ["group:web"]` is set:** This *restricts* tools to only web_search and web_fetch. Exec, read, write, and other coding tools are filtered out. The model receives zero tools and outputs tool-call text instead of executing.

**Fix:** Use `tools.alsoAllow: ["group:web"]` instead. This *adds* web tools to the coding profile without removing exec, read, write, etc.

## What Is NOT Wrong

- **Gerty routing:** Correct. Non–fast-path intents go to OpenClaw when enabled.
- **OpenClaw config:** `exec` host=gateway, Python allowlisted, web search enabled.
- **Band-aids:** The gerty-calendar skill and CalendarTool fallback don't cause this.

---

## How to Verify Tool Execution

Run this directly (bypass Gerty):

```bash
openclaw agent --agent main --message 'Run: ls -la /home/liam/.openclaw' --json
```

- **If tools work:** You'll see real `ls` output in the response.
- **If bug is present:** You'll see something like `exec(command: "ls -la ...")` as plain text, or made-up output.

---

## "OpenClaw completed but returned no output" / Empty Responses

### Primary cause (headless Gerty): Exec approval timeout

**Gerty is headless**—no one is at the OpenClaw Control UI to approve exec commands. With `ask: "on-miss"` in `~/.openclaw/exec-approvals.json`, any command not in the allowlist waits for approval and times out (~2 min). The agent then returns empty or incomplete.

**Fix:** Set `ask: "off"` for the main agent and allowlist all commands the agent needs: `find`, `which`, `grep`, `cat`, `xargs`, `basename`, `dirname`, `gog`, `python`, `clawhub`, etc. See [OPENCLAW_INTEGRATION.md](OPENCLAW_INTEGRATION.md) § Exec approvals.

### Other causes (per [OpenClaw help](https://www.getopenclaw.ai/help/model-not-responding-no-output))

1. **Gateway unreachable** — systemd may show "running" but port 18789 not listening. Restart: `systemctl --user restart openclaw-gateway`.
2. **Auth (HTTP 401)** — Invalid or missing `OPENROUTER_API_KEY` in `~/.openclaw/.env`. OpenClaw uses its own env, not Gerty's.
3. **Model not configured** — No default in `~/.openclaw/openclaw.json` or model inaccessible.
4. **API key not loading** — Daemon doesn't inherit shell env. Put keys in `~/.openclaw/.env`, restart: `openclaw daemon start`.
5. **Grok returning empty** — Model sometimes returns no text for certain prompts.

**Quick triage:**
```bash
openclaw status
openclaw models status
openclaw gateway logs --follow
openclaw doctor --fix
```

---

## Options Until the Fix Ships

1. **Wait for upstream fix** — Watch [#43365](https://github.com/openclaw/openclaw/pull/43365); upgrade when it's merged and released.

2. **Try a different agent** — Issue #39971 reports that `dossiers_agent` executes tools correctly. You could add an agent and point Gerty at it (would require Gerty changes to support `OPENCLAW_AGENT_ID`).

3. **Use Gerty tools for critical paths** — Calendar, search, etc. can stay on Gerty's fast path until OpenClaw is fixed. That's a workaround, not a fix.

4. **Try the fix commit** (advanced): The fix branch may be deleted; use the PR's commit hash:
   ```bash
   npm install -g "openclaw@github:openclaw/openclaw#e4e6848ff95be7664b4f4de578836920d6a85fea"
   ```
   Then restart the daemon: `openclaw daemon start`. Not recommended for production.

---

## Summary

| Question | Answer |
|----------|--------|
| Is Gerty sending to OpenClaw? | Yes |
| Is OpenClaw receiving it? | Yes |
| Does the agent have tools? | Yes (exec, web_search, etc.) |
| Do tools ever run? | **Sometimes** — direct `openclaw agent` tests can succeed |
| Why invented responses? | Grok may skip tools and hallucinate; or bug #39971 (tool text vs execution) |
| Is this a Gerty setup issue? | No — routing and config are correct |
