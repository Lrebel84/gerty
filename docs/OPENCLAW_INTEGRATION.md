# OpenClaw Integration

Gerty can route action requests to [OpenClaw](https://github.com/openclaw/openclaw), an autonomous AI that executes tasks (files, browser, calendar, email, etc.). Gerty remains your voice and interface; OpenClaw is the execution backend.

## How It Works

1. **Fast path:** Obvious Gerty tools (time, alarm, timer, calculator, notes, weather, RAG) skip the classifier—instant response.
2. **Classifier:** For everything else, an LLM decides: Gerty (chat, Q&A, search) or OpenClaw (action to execute). The classifier runs *before* any web-intent fallback, so simple questions (e.g. "tell me about The Sopranos") go straight to chat—no extra LLM call or misrouting to research.
3. **OpenClaw:** When the classifier routes to OpenClaw, Gerty reformulates the task and passes it to OpenClaw. Gerty reports the result back to you.

OpenClaw handles calendar, Gmail, Drive, Tasks, files, browser, and more.

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
OPENCLAW_CLASSIFIER_MODEL=openai/gpt-4o-mini
OLLAMA_CLASSIFIER_MODEL=llama3.2
```

### 4. Configure OpenClaw

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

## Config Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `GERTY_OPENCLAW_ENABLED` | `0` | Enable OpenClaw routing |
| `OPENCLAW_GATEWAY_WS_URL` | `ws://127.0.0.1:18789/gateway` | OpenClaw WebSocket gateway |
| `OPENCLAW_AGENT_ID` | `main` | OpenClaw agent to use |
| `OPENCLAW_TIMEOUT` | `120` | Execution timeout (seconds) |
| `OPENCLAW_CLASSIFIER_MODEL` | `openai/gpt-4o-mini` | Model for routing (OpenRouter) |
| `OLLAMA_CLASSIFIER_MODEL` | `llama3.2` | Fallback classifier when offline |

## Troubleshooting

**"I know what you want, but my action system isn't running right now"**

OpenClaw daemon is not reachable. Start it with:

```bash
openclaw daemon start
```

**Classifier always routes to Gerty**

Ensure you have `OPENROUTER_API_KEY` (or Ollama running) for the classifier. The classifier uses OpenRouter first, Ollama as fallback.

**OpenClaw executes but returns nothing useful**

Configure OpenClaw with the required skills (calendar, Gmail, etc.). Gerty only passes the request; OpenClaw must have the integrations set up.
