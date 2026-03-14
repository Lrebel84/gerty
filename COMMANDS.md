# Gerty Commands Reference

A quick reference for tools and skills you can use with Gerty. Just type or say these phrases in chat, via voice, or in the Telegram bot.

**OpenClaw:** When `GERTY_OPENCLAW_ENABLED=1`, everything except fast-path (time, alarm, timer, etc.) goes to OpenClaw. Gerty passes full chat history and your custom prompt. Say what you want in natural language—no exact phrases needed. When the daemon is down, Gerty falls back to Ollama/OpenRouter chat. **Security:** Gerty screens messages before sending to OpenClaw—risky requests (e.g. "run rm -rf", "cat .env") are blocked and never reach OpenClaw. See [docs/SECURITY_POLICY.md](docs/SECURITY_POLICY.md). **Note:** OpenClaw/Grok sometimes returns invented responses instead of using tools; verify critical actions. See [docs/OPENCLAW_DIAGNOSIS.md](docs/OPENCLAW_DIAGNOSIS.md).

| Section | Tools |
|---------|-------|
| Time | Time, date, timezone, stopwatch |
| Scheduling | Alarms, timers, pomodoro |
| Utilities | Calculator, unit conversion, random, notes |
| Info | Weather, web search, deep research (OpenClaw when enabled; else OpenRouter or DuckDuckGo), interactive browsing |
| Integrations | OpenClaw (web search, research, browse, files, browser, calendar, email when enabled) |
| Knowledge | RAG (documents + memory in `data/knowledge/`, `data/rag/`) |
| Vision | Screen vision |
| System | System commands, media & audio, app launching, system monitoring |
| Maintenance | Incidents, proposals, tasks, diagnostics |
| Projects | Project graph (create projects, add tasks, assign agents, run tasks), opportunity scanner (record and summarize opportunities) |

---

## Time and Date

| Command | Example |
|---------|---------|
| Current time | "what time is it" / "current time" |
| Today's date | "what's the date" / "today's date" |

---

## Alarms

| Action | Example |
|--------|---------|
| Set alarm | "set alarm for 7am" / "wake me at 7:30" / "alarm for 6pm" |
| Set daily alarm | "daily alarm for 7am" / "alarm for 7am every day" / "repeating alarm at 6pm" |
| Set named alarm | "alarm for 7am for workout" |
| List alarms | "list my alarms" / "show alarms" |
| Cancel all | "cancel alarms" / "remove alarms" |

*Supports: 7am, 7:30 pm, 7 30, 19:00. Voice: "eleven oh five", "seven thirty am"*

**Daily alarms** repeat every day at the same time. Dismissing one reschedules it for tomorrow. Use the "Daily" toggle in the overlay to convert existing alarms.

**Note:** To stop a sounding alarm, say "cancel" or "stop", or use the wake word. See [docs/ALARM.md](docs/ALARM.md).

---

## Timers

| Action | Example |
|--------|---------|
| Set timer | "timer 5 minutes" / "5 minute timer" / "timer for 30 seconds" |
| Set named timer | "timer 10 minutes for eggs" |
| List timers | "list timers" / "show timers" |
| Cancel all | "cancel timers" / "stop timers" |

*Supports: X hours, X minutes, X seconds, or bare number (e.g. "timer 5" = 5 minutes). Voice: "five minutes", "twenty minutes". You can also add timers from the Alarms & Timers overlay.*

---

## Stopwatch

| Action | Example |
|--------|---------|
| Start | "start stopwatch" |
| Check elapsed | "how long has it been" / "stopwatch" / "how long running" |
| Stop | "stop stopwatch" / "reset stopwatch" |

---

## Calculator

| Command | Example |
|---------|---------|
| Arithmetic | "what is 15 + 27" / "calculate 100 / 4" |
| Percentages | "what is 15% of 80" / "20% off 50" |
| Powers | "what is 2 ** 10" |

*Supports: + - * / ** %*

---

## Unit Conversion

| Command | Example |
|---------|---------|
| Temperature | "convert 32 fahrenheit to celsius" / "32F to C" |
| Length | "convert 5 miles to km" / "10 feet to meters" |
| Weight | "convert 150 lb to kg" / "5 kilograms to pounds" |

*Supported units: F/C/K, m/km/mi/ft/in/cm, kg/lb/oz*

---

## Random

| Command | Example |
|---------|---------|
| Coin flip | "flip a coin" |
| Dice roll | "roll 2d6" / "roll a 6" |
| Random number | "pick a number 1 to 10" / "number between 1 and 100" |
| Pick from options | "choose A, B, or C" / "pick from pizza or pasta" |

---

## Notes

| Action | Example |
|--------|---------|
| Add note | "note: buy milk" / "remember to call mom" / "remind me to X" / "make a note X" |
| List notes | "list notes" / "show notes" |
| Clear all | "clear notes" / "delete notes" |

*Voice: "remind me to call mom", "remember to buy milk", "make a note get groceries"*

*Notes are saved in `data/notes.txt`*

---

## Timezone

| Command | Example |
|---------|---------|
| Time elsewhere | "time in Tokyo" / "what time is it in London" |

*Supported cities: London, Paris, Berlin, Tokyo, Sydney, New York, NYC, LA, Chicago, Toronto, Vancouver, Mumbai, Delhi, Beijing, Shanghai, Hong Kong, Singapore, Dubai, Moscow, UTC, GMT*

---

## Weather

| Command | Example |
|---------|---------|
| Current weather | "weather in London" / "forecast for Tokyo" / "temperature in Paris" |

*Uses Open-Meteo (no API key). Supports city names.*

---

## Web Search

| Command | Example |
|---------|---------|
| Explicit search | "search for Python tutorial" / "look up current events" |
| Contact & info | "get me the contact details for Acme Corp" / "phone number for xyz business" |
| Showtimes & hours | "when is the next showtimes of Dune at VUE Sheffield" / "opening hours of the library" |
| Find/lookup | "find me a good plumber" / "where can i find the address of city hall" |

*Uses DuckDuckGo. Requires: `pip install duckduckgo-search`*

*When OpenClaw is enabled (`GERTY_OPENCLAW_ENABLED=1`), search goes to OpenClaw (agentic web_search + web_fetch). When OpenClaw is disabled or unreachable, OpenRouter uses quick web lookup (:online) or DuckDuckGo. Queries that don't match explicit keywords may still route to web search via intent fallback (GERTY_WEB_INTENT_FALLBACK=1) when OpenClaw is off.*

---

## Interactive Browsing (OpenRouter, opt-in)

*Requires `GERTY_BROWSE_ENABLED=1` in `.env` and OpenRouter*

| Command | Example |
|---------|---------|
| Navigate | "go to example.com and find the pricing page" / "visit python.org" |
| Browse | "browse to github.com and show my repos" |
| Authenticated | "check my GitHub notifications" / "log into Gmail and check unread" |

*Uses BrowserUse + Playwright. Requires Python 3.11+, then: `pip install browser-use playwright` and `python -m playwright install chromium`.*

**Authenticated sites:** Save login state with `playwright codegen --save-storage=data/auth/github.json`, then set `BROWSE_AUTH_SITES=github.com:github.json` in `.env`. The browse tool loads the stored session when the task mentions the domain.

---

## Deep Research

| Command | Example |
|---------|---------|
| Research & compare | "research best 3D printers under $500" / "compare and summarize top project management tools" |
| Find best / overview | "find me the best budget PCs for local LLM under £500" / "thoroughly research this business and provide a complete overview" |
| Create spreadsheet | "find the best laptops and create a spreadsheet" / "analyze and report on electric cars under $40k" |

*When OpenClaw is enabled, research goes directly to OpenClaw (agentic web_search + web_fetch). When OpenClaw is disabled, requires OpenRouter (Settings → Provider → OpenRouter) for multi-step research; tables saved to `data/research_*.csv`. Works for both typed chat and voice.*

---

## OpenClaw (action execution)

*Requires `GERTY_OPENCLAW_ENABLED=1` in `.env` and OpenClaw installed (`npm install -g openclaw`). See [docs/OPENCLAW_INTEGRATION.md](docs/OPENCLAW_INTEGRATION.md).*

| Command | Example |
|---------|---------|
| Calendar | "What's in my calendar for tomorrow?" / "What have I got this week?" |
| Gmail | "Check my latest three emails" / "Read my inbox" |
| Drive | "What's in my Google Drive?" / "Check my drive" |
| Tasks | "What's on my tasks?" / "Check my tasks" |
| File ops | "Create a file with my meeting notes" / "Organize my downloads folder" |
| Browser | "Open the site and fill out the form" / "Navigate to example.com" |
| Web search / research / browse | "search for X" / "research Y" / "go to example.com" |
| Automation | "Clear my inbox" / "Send a message to X" |
| Self-improvement | "Install the summarize skill from ClawHub" / "Run ls -la in my home directory" / "Open Firefox" / "Add a new skill to Gerty that does X" |

*Option A: everything except fast-path (time, alarm, timer, etc.) goes to OpenClaw. Gerty passes full chat history and your custom prompt. Say what you want in natural language—no exact phrases needed.*

*To verify the connection:* Say **"list my skills"** or **"list skills"**—this routes directly to OpenClaw and returns your installed skills. If you see the list, the daemon and auth are working.

*Setup:* Install OpenClaw (`npm install -g openclaw`), run `openclaw daemon start` (or use the desktop launcher—it starts automatically), add `GERTY_OPENCLAW_ENABLED=1` to Gerty's `.env`. Configure OpenClaw: create `~/.openclaw/.env` with a dedicated `OPENROUTER_API_KEY` (not Gerty's), add `BRAVE_API_KEY` or `PERPLEXITY_API_KEY` for web search, run `openclaw onboard` or `openclaw configure --section web`. For self-improvement (run commands, install skills from ClawHub, control apps): see [docs/OPENCLAW_INTEGRATION.md](docs/OPENCLAW_INTEGRATION.md) Self-improvement setup.

---

## Maintenance (incidents, proposals, diagnostics)

| Command | Example |
|---------|---------|
| Create incident | "create incident: RAG indexing fails on large PDFs" |
| List incidents | "list incidents" / "show open incidents" |
| Run diagnostics | "run diagnostics" / "diagnostics summary" |
| Maintenance summary | "maintenance summary" |

*Stored in `data/maintenance/`. See [docs/MAINTENANCE_WORKFLOW.md](docs/MAINTENANCE_WORKFLOW.md).*

---

## Personal context

| Command | Example |
|---------|---------|
| Who am I | "who am I" / "about me" |
| Goals | "what are my goals" / "my goals" |
| Projects | "what are my projects" / "my projects" |
| Schedule | "my schedule" / "work schedule" |
| Preferences | "my preferences" / "my values" |
| Add idea | "add idea: build a SaaS for X" |
| Add goal | "add goal: ship Gerty v2" |
| Add project | "add project: Website redesign" |
| Update project | "update project status Gerty to paused" |
| Update goal | "update goal status X to done" |
| Add preference note | "add preference note: prefer dark mode" |
| Add business concept | "add business concept: AI content agency" |

*Source: `data/personal_context/`. See [docs/PERSONAL_CONTEXT_ENGINE.md](docs/PERSONAL_CONTEXT_ENGINE.md).*

---

## Agent Factory (create agents)

| Command | Example |
|---------|---------|
| Create agent | "create agent: market_researcher - researches market opportunities and competition" |
| List agents | "list agents" |
| Show agent | "show agent market_researcher" |

*See [docs/AGENT_FACTORY.md](docs/AGENT_FACTORY.md).*

## Agent invocation (run agents)

| Command | Example |
|---------|---------|
| Ask agent | "ask agent market_researcher: summarize the top 3 competitors" |
| Run agent | "run agent builder: outline a landing page for a SaaS product" |
| Use agent | "use agent content_marketer: write a tagline for a tattoo studio" |

*Single-shot, synchronous. Creates task and output artifacts. See [docs/AGENT_FACTORY.md](docs/AGENT_FACTORY.md) § Agent Invocation.*

## Agent Designer (design/improve agents)

| Command | Example |
|---------|---------|
| Design agent | "design agent: niche_finder - finds unsaturated AI business opportunities for tattoo-related digital products" |
| Improve agent | "improve agent market_researcher" |
| Suggest agent | "suggest agent for: researching and validating SaaS ideas for tattoo artists" |
| Show agent design | "show agent design market_researcher" |
| Show agent design artifact | "show agent design artifact 20250313-123456-niche_finder" |
| List agent designs | "list agent designs" |
| Create from design | "create from design niche_finder" |

*Draft-first: inspect design before creating. Designs are persisted to `data/agent_designs/`. See [docs/AGENT_DESIGNER.md](docs/AGENT_DESIGNER.md).*

## Intent Orchestrator (high-level outcome requests)

| Command | Example |
|---------|---------|
| Help explore | "help me explore tattoo-related AI business ideas" |
| Organize | "help me organize this business idea properly" |
| Turn into project | "I want to turn this into a real project" |
| Build agent | "build whatever agent we need for researching this" |
| Propose tool | "if we do not have the right tool, propose one" |
| Best next step | "what is the best next step for this goal" |
| List orchestration plans | "list orchestration plans" |
| Show orchestration plan | "show orchestration plan 20250313-123456-plan" |

*Interprets natural-language outcome requests and recommends or invokes the right path (agent, tool, design, project structure). Plans are persisted to `data/orchestration/`. Direct commands (list agents, ask agent X: task) still work unchanged. See [docs/INTENT_ORCHESTRATOR.md](docs/INTENT_ORCHESTRATOR.md).*

---

## Project / Task Graph (System 5 + 5.1)

| Command | Example |
|---------|---------|
| Create project | "create project: AI Tattoo SaaS - explore digital product opportunities for tattoo artists" |
| List projects | "list projects" |
| Show project | "show project ai_tattoo_saas" |
| Add task | "add task to ai_tattoo_saas: research market" |
| Add task with description | "add task to ai_tattoo_saas: identify top competitors - focus on scheduling and design workflows" |
| Update task status | "update task task_001 in ai_tattoo_saas to in_progress" |
| Assign agent to task | "assign agent market_researcher to task task_001 in ai_tattoo_saas" |
| Run task | "run task task_001 in ai_tattoo_saas" |
| Run next task | "run next task for ai_tattoo_saas" |
| Project summary | "project summary ai_tattoo_saas" |
| Next task (suggest) | "next task for ai_tattoo_saas" |

*Stored in `data/projects/<project_slug>/`. Each project has project.json, tasks.json, README.md, notes/, outputs/. Task execution (System 5.1) invokes the assigned agent and saves results to outputs/. See [docs/PROJECT_TASK_GRAPH.md](docs/PROJECT_TASK_GRAPH.md).*

---

## Opportunity Scanner (System 6)

| Command | Example |
|---------|---------|
| Create opportunity | "create opportunity: AI Tattoo SaaS - tools for tattoo artists including scheduling and design workflows" |
| List opportunities | "list opportunities" |
| Show opportunity | "show opportunity 20260314-123000-ai_tattoo_saas" |
| Opportunity summary | "opportunity summary 20260314-123000-ai_tattoo_saas" |
| Score opportunity | "score opportunity 20260314-123000-ai_tattoo_saas" |
| Next step | "next step for opportunity 20260314-123000-ai_tattoo_saas" |
| Create project from opportunity | "create project from opportunity 20260314-123000-ai_tattoo_saas" |

*Stored in `data/opportunities/<timestamp>-<slug>.json`. Categories: business, product, automation, niche, content, other. See [docs/OPPORTUNITY_SCANNER.md](docs/OPPORTUNITY_SCANNER.md).*

---

## CLI modes (terminal)

| Command | Purpose |
|---------|---------|
| `python -m gerty` | Start Gerty (default) |
| `python -m gerty --heartbeat` | Health rotation: diagnostics, friction, incidents; writes artifact when noteworthy |
| `python -m gerty --validate` | Run do-not-break checks (pytest, etc.) |
| `python -m gerty --diagnose` | One-off diagnostics (Ollama, OpenClaw, OpenRouter, paths) |

*Gerty's `--heartbeat` is different from the proactive-agent skill's heartbeats (cron → OpenClaw). See [docs/GERTY_OVERVIEW.md](docs/GERTY_OVERVIEW.md) § Heartbeat vs Proactive-Agent.*

---

## Proactive agent (background heartbeats)

When the **proactive-agent** skill is installed and configured, a system cron runs every 4 hours. The agent:

- Runs the HEARTBEAT.md checklist
- Uses web search for items relevant to your goals (from USER.md)
- Appends findings to `notes/areas/proactive-updates.md`
- Logs output to `logs/proactive.log`

*Setup:* Complete onboarding (USER.md, SOUL.md). Run `./scripts/setup-proactive-cron.sh` to add the crontab. Test: `./scripts/proactive-heartbeat.sh`. See [docs/OPENCLAW_INTEGRATION.md](docs/OPENCLAW_INTEGRATION.md) §8. **Not the same as** `python -m gerty --heartbeat` (Gerty's built-in health rotation).

---

## Pomodoro

| Action | Example |
|--------|---------|
| Start | "start pomodoro" |
| Status | "pomodoro status" / "how long left" |
| Stop | "stop pomodoro" |

*25 min work, 5 min break. Notifications via TTS, system, and Telegram when each phase ends.*

---

## Knowledge Base (RAG)

| Action | Example |
|--------|---------|
| Query documents | "check documentation" / "retrieve the setup guide" / "search my docs for API" / "search my files for X" / "what do my files say about Y" |
| Index documents | Settings → Knowledge base → "Index now" |
| Enable RAG tool | Settings → Knowledge base → "Enable RAG" (required to use the tool) |

*Drop PDF, Excel, Word, or text files into `data/knowledge/`, then index. Enable RAG in Settings. Long-term memory (Settings toggle) extracts facts from chat. Say "check my docs for X" or "search my files for Y" to query documents and memory. On-demand only—no automatic injection. See [docs/RAG_MEMORY.md](docs/RAG_MEMORY.md).*

---

## Screen Vision

| Action | Example |
|--------|---------|
| Describe screen | "what am I looking at" / "what's on screen" / "describe my screen" |
| Extract code | "extract the code from this" / "extract code from this video tutorial" |
| Analyze content | "what do you see" / "look at my screen" |

*Captures the current screen and sends it to your selected vision model (Ollama or OpenRouter). Local: run `ollama pull llava` or `ollama pull llama3.2-vision` and set `OLLAMA_VISION_MODEL` in `.env` if needed. OpenRouter models (Claude, GPT-4V) support vision by default. On Wayland, screen capture may require X11 or grim/slurp.*

**Hotkey:** `Ctrl+Shift+S` (or `Meta+Shift+S` on Mac) to instantly ask "what am I looking at?"

---

## System Commands (opt-in)

*Requires `GERTY_SYSTEM_TOOLS=1` in `.env`*

| Action | Example |
|--------|---------|
| Lock screen | "lock my screen" / "lock screen" |
| Suspend | "suspend" / "sleep" / "put to sleep" |
| Reboot | "reboot" / "restart" |
| Shut down | "shut down" / "power off" |

---

## Media & Audio

| Action | Example |
|--------|---------|
| Play / Pause | "play" / "pause" / "play pause" |
| Skip | "skip" / "next track" |
| Previous | "previous track" |
| Mute / Unmute | "mute" / "unmute" |
| Volume | "volume up" / "volume down" |

*Requires: `playerctl` (media), `wpctl` (PipeWire) or `pamixer` (PulseAudio) for audio. Install: `sudo apt install playerctl`*

---

## App Launching (opt-in)

*Requires `GERTY_SYSTEM_TOOLS=1` in `.env`*

| Action | Example |
|--------|---------|
| Open app | "open Firefox" / "launch VS Code" / "start Terminal" |

*Parses `.desktop` files from `/usr/share/applications` and `~/.local/share/applications`. Requires `gtk-launch` or `gio`.*

---

## System Monitoring

| Action | Example |
|--------|---------|
| Diagnose | "why are my fans spinning" / "what's using CPU" / "system status" |

*Uses psutil. Install: `pip install psutil`*

---

## General Chat

Everything else is handled by the LLM. Ask questions, get explanations, write code, summarize, translate—Gerty will respond using the Local (Ollama) or OpenRouter model you've selected.

---

## Telegram Commands

Control Gerty from your phone. Setup: [docs/TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md). When using Gerty via Telegram:

| Command | Description |
|---------|-------------|
| `/start` | Intro and help |
| `/chat <message>` | Send a chat message |
| `/time` | Current time |
| `/alarm <time>` or `list` | Set alarm or list alarms |
| `/timer <duration>` or `list` | Set timer or list timers |

*Plain text messages (e.g. "flip a coin") also work—they're routed to the same tools.*

---

## Voice

Say **"our Gurt"** to wake Gerty (Picovoice; set `PICOVOICE_ACCESS_KEY` in `.env`), then speak your command. Or use the single-click mic. All tools above work via voice.
