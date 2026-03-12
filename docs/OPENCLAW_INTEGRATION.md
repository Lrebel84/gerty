# OpenClaw Integration

Gerty can route action requests to [OpenClaw](https://github.com/openclaw/openclaw), an autonomous AI that executes tasks (files, browser, calendar, email, etc.). Gerty remains your voice and interface; OpenClaw is the execution backend.

## How It Works (Option A)

1. **Fast path:** Obvious Gerty tools (time, alarm, timer, calculator, notes, weather, RAG) go to Gerty—instant response.
2. **OpenClaw:** Everything else goes to OpenClaw when enabled. Gerty passes your message plus full chat history and custom prompt (persona) to OpenClaw.
3. **Fallback:** When the OpenClaw daemon is unreachable, Gerty falls back to Ollama or OpenRouter chat.

OpenClaw handles web search, research, browse, calendar, Gmail, Drive, Tasks, files, browser, and more. No classifier—simple routing.

## Setup

### 1. Install OpenClaw

Requires Node.js 22+:

```bash
npm install -g openclaw@latest
# or
pnpm add -g openclaw@latest
```

### 2. Start the daemon

**Option A: Automatic (when using the desktop launcher)**  
If you launch Gerty from the app launcher (Super key → search "Gerty"), the OpenClaw daemon starts automatically in the background when `GERTY_OPENCLAW_ENABLED=1`. No manual step needed.

**Option B: Manual**
```bash
openclaw daemon start
```

Or run the onboarding wizard:

```bash
openclaw onboard --install-daemon
```

### 3. Configure Gerty

Add to your `.env`:

```
GERTY_OPENCLAW_ENABLED=1
```

Optional:

```
OPENCLAW_GATEWAY_WS_URL=ws://127.0.0.1:18789/gateway
OPENCLAW_AGENT_ID=main
OPENCLAW_TIMEOUT=120
OPENCLAW_MODEL=openrouter/x-ai/grok-4.1-fast
OPENCLAW_HISTORY_MAX_MESSAGES=20
```

### 4. Configure OpenClaw model (Grok 4.1 fast)

To use Grok 4.1 fast (same as Gerty's LLM), set the model in OpenClaw's config. Edit `~/.openclaw/openclaw.json`:

```json
"agents": {
  "defaults": {
    "model": {
      "primary": "openrouter/x-ai/grok-4.1-fast"
    },
    ...
  }
}
```

Or run `openclaw configure` and select the model. OpenClaw uses its own config; Gerty's `OPENCLAW_MODEL` env var is for documentation—the actual model is set in `~/.openclaw/openclaw.json`.

### 5. Configure OpenClaw integrations

Set up your Google/calendar/email integrations in OpenClaw (skills or channels). Gerty passes requests through; OpenClaw performs the actions.

#### OpenClaw-specific configuration

OpenClaw uses its own config and API keys, separate from Gerty. Key locations:

| Item | Location | Purpose |
|------|----------|---------|
| Env vars | `~/.openclaw/.env` | `OPENROUTER_API_KEY` (dedicated key for OpenClaw), `BRAVE_API_KEY` or `PERPLEXITY_API_KEY` for web search |
| Config | `~/.openclaw/openclaw.json` | Model, tools, gateway |
| Auth | `~/.openclaw/agents/main/agent/auth-profiles.json` | References `OPENROUTER_API_KEY` from env |

**API key:** Create `~/.openclaw/.env` with your OpenClaw-specific OpenRouter key. Do not reuse Gerty's key—use a separate key for OpenClaw so usage and limits are isolated.

**Web search:** Add `BRAVE_API_KEY` or `PERPLEXITY_API_KEY` to `~/.openclaw/.env`, or run `openclaw configure --section web`. The `group:web` tools (`web_search`, `web_fetch`) are enabled in the coding profile.

**Tools:** OpenClaw is configured with `profile: "coding"` plus `group:web` (files, exec, sessions, memory, image, web search, web fetch). See [OpenClaw tools docs](https://docs.openclaw.ai/tools/index) for more.

## Custom prompt and history

- **Custom prompt:** Gerty's Settings custom prompt (e.g. "You are Gerty, the helpful assistant to Liam") is passed to OpenClaw as system context with each message.
- **Chat history:** Gerty sends the full chat history (last N messages, configurable via `OPENCLAW_HISTORY_MAX_MESSAGES`) so OpenClaw has conversation context.
- **New chat:** When you click "New chat", Gerty clears both local history and the OpenClaw session.

## Self-improvement setup (PC/terminal, skills, commands)

To let Gerty/OpenClaw run commands on your PC, install skills from ClawHub, control apps, and improve itself from your instructions:

### 1. Workspace

Set `agents.defaults.workspace` in `~/.openclaw/openclaw.json` to your Gerty project root so OpenClaw can edit files and install skills there:

```json
"agents": { "defaults": { "workspace": "/home/you/gerty" } }
```

### 2. Exec on gateway (host)

By default, exec runs in a sandbox. For real PC/terminal access, set `tools.exec.host` to `gateway` in `~/.openclaw/openclaw.json`:

```json
"tools": {
  "exec": {
    "host": "gateway",
    "security": "allowlist",
    "ask": "on-miss"
  }
}
```

### 3. Exec approvals

Create or edit `~/.openclaw/exec-approvals.json` to allow binaries for gateway exec. Use `security: "allowlist"` (safer) or `security: "full"` (all commands). Example allowlist:

```json
{
  "version": 1,
  "defaults": { "security": "allowlist", "ask": "on-miss", "autoAllowSkills": true },
  "agents": {
    "main": {
      "security": "allowlist",
      "allowlist": [
        "/usr/bin/gtk-launch",
        "/usr/bin/gio",
        "/usr/bin/xdg-open",
        "/usr/local/bin/npm",
        "/usr/local/bin/node",
        "/usr/local/bin/clawhub",
        "/home/you/gerty/.venv/bin/python"
      ]
    }
  }
}
```

Resolve paths with `which clawhub`, `which npm`, etc. Edit via Control UI at `http://127.0.0.1:18789` → Nodes → Exec approvals.

### 4. Web search

Add `BRAVE_API_KEY` or `PERPLEXITY_API_KEY` to `~/.openclaw/.env` for `web_search` and `web_fetch`. See [Brave Search API](https://brave.com/search/api/) or [Perplexity API](https://docs.perplexity.ai/api-reference).

### 5. ClawHub (skill installation)

```bash
npm install -g clawhub
clawhub login
```

Set `CLAWHUB_WORKDIR` to your Gerty project so installs go to `./skills`:

```bash
export CLAWHUB_WORKDIR=/home/you/gerty
clawhub install <skill-name>
```

OpenClaw can run `clawhub install` via exec when its workspace matches.

### 6. Custom prompt for self-improvement

In Gerty Settings, add a prompt that tells OpenClaw it can improve Gerty:

> You are Gerty's action system. You can run commands on the host, install skills from ClawHub, edit files in the workspace, and use web search. The workspace is the Gerty project. When asked to add capabilities or improve Gerty, use exec to run clawhub install, edit files, and run tests as needed.

### 7. Timeout for long tasks

For skill installs and multi-step edits, increase `OPENCLAW_TIMEOUT` in Gerty's `.env` (e.g. 120 seconds).

### Verification

| Step | Check |
|------|-------|
| Connection | Say "list my skills" in Gerty |
| Web search | "Search for latest Python release" |
| Exec | "Run ls -la in my home directory" |
| ClawHub | "Install the summarize skill from ClawHub" |
| App launch | "Open Firefox" |
| Self-improvement | "Add a new skill to Gerty that does X" |

**Security:** Exec on gateway runs commands on your machine. Prefer allowlist over `security: "full"`. Review ClawHub skills before installing. Use a separate git branch when experimenting with self-improvement.

## Config Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `GERTY_OPENCLAW_ENABLED` | `0` | Enable OpenClaw routing |
| `OPENCLAW_GATEWAY_WS_URL` | `ws://127.0.0.1:18789/gateway` | OpenClaw WebSocket gateway |
| `OPENCLAW_AGENT_ID` | `main` | OpenClaw agent to use |
| `OPENCLAW_TIMEOUT` | `120` | Execution timeout (seconds) |
| `OPENCLAW_MODEL` | `openrouter/x-ai/grok-4.1-fast` | Documented model; set in `~/.openclaw/openclaw.json` |
| `OPENCLAW_HISTORY_MAX_MESSAGES` | `20` | Max messages to include in history context |

## Testing the Connection

Say **"list my skills"** (or "list skills") to verify OpenClaw is connected. This routes to OpenClaw and returns your installed skills. If you see the skills list, the daemon and auth are working.

## Routing Summary

| Intent | Handler | When |
|--------|---------|------|
| time, date, alarm, timer, calculator, units, notes, weather, random, RAG | Gerty (instant) | Always |
| Everything else | OpenClaw | When `GERTY_OPENCLAW_ENABLED=1` |
| Fallback | Ollama or OpenRouter | When OpenClaw daemon unreachable |

## Troubleshooting

**"I know what you want, but my action system isn't running right now"**

OpenClaw daemon is not reachable. Gerty will fall back to Ollama/OpenRouter chat. Start OpenClaw with:

```bash
openclaw daemon start
```

**OpenClaw executes but returns nothing useful**

Configure OpenClaw with the required skills (calendar, Gmail, etc.). Gerty only passes the request; OpenClaw must have the integrations set up.

**"My action system isn't running" – daemon not starting?**

OpenClaw requires **Node.js 22+**. If your system `node` is v20 (e.g. from `/usr/bin/node`), the daemon won't start. The launch script puts `/usr/local/bin` first in PATH so Node 22 (if installed there) is used. Install Node 22 via [NodeSource](https://github.com/nodesource/distributions) or ensure `node --version` shows v22+ when the desktop launcher runs.

Run the diagnostic: `./scripts/check_openclaw.sh`. It checks: `GERTY_OPENCLAW_ENABLED`, `openclaw` on PATH, daemon process, port 18789, and `~/.openclaw` config. If `openclaw` is not found, ensure it's in PATH when the desktop launcher runs—e.g. install to `~/.local/bin` and add that to your PATH (or use `~/.npm-global/bin`). The launch script adds `~/.npm-global/bin` and `~/.local/bin` automatically. If the daemon is still not starting, run `openclaw daemon start` manually in a terminal before launching Gerty.

**"gateway token mismatch" or "unauthorized"**

The SDK uses `~/.openclaw/identity/device-auth.json` for auth. Ensure `gateway.auth.token` in `~/.openclaw/openclaw.json` matches `tokens.operator.token` in device-auth.json. If they differ, either update the gateway token to match device-auth, or re-run `openclaw onboard` / `openclaw pair` to regenerate a matching pair.

**"missing scope: operator.write"**

The device token has only `operator.read`. Re-pair the device to get write scope: run `openclaw pair` in a terminal, complete the pairing flow, then restart the daemon. The new device-auth will include `operator.write`.
