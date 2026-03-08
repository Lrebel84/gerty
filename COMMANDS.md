# Gerty Commands Reference

A quick reference for tools and skills you can use with Gerty. Just type or say these phrases in chat, via voice, or in the Telegram bot.

| Section | Tools |
|---------|-------|
| Time | Time, date, timezone, stopwatch |
| Scheduling | Alarms, timers, pomodoro |
| Utilities | Calculator, unit conversion, random, notes |
| Info | Weather, web search |
| Knowledge | RAG (documents + memory in `data/knowledge/`, `data/rag/`) |
| System | System commands, media & audio, app launching, system monitoring |

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
| Search | "search for Python tutorial" / "look up current events" |

*Uses DuckDuckGo. Requires: `pip install duckduckgo-search`*

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

When using Gerty via Telegram:

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
