---
name: gerty-calendar
description: Check the user's Google Calendar for a specific date. Use exec to run the Gerty calendar script. NEVER invent or guess events—only report the exact script output.
metadata:
  {"openclaw": {"requires": {"config": ["tools.exec.host"]}, "always": true}}
---

# Gerty Calendar Skill

## When to use

When the user asks about their calendar, schedule, or what they have on a specific date. Examples:
- "What's on my calendar today?"
- "Check my calendar for 18th March"
- "What have I got on tomorrow?"
- "What do I have on Friday?"

## How to use (required)

1. **Parse the date** from the user's message:
   - "today" → today's date (YYYY-MM-DD)
   - "tomorrow" → tomorrow's date
   - "18th March", "March 18", "18 March" → 2026-03-18 (or current year)
   - "next Friday" → the next Friday's date
   - If no date given, default to tomorrow

2. **Run the script** via exec. Use the exact command:
   ```
   cd /home/liam/gerty && /home/liam/gerty/.venv/bin/python scripts/check_google_calendar.py YYYY-MM-DD
   ```
   Replace YYYY-MM-DD with the parsed date.

3. **Report the output** exactly as the script prints it. Do NOT summarize, invent, or guess events. If the script says "Full Day Sitting for Miles Emmett", say that. If it says "No events.", say that.

## Critical rules

- **NEVER invent calendar events.** Only report what the script outputs.
- **ALWAYS use exec** to run the script—do not guess or hallucinate.
- **Use absolute paths**—the script and venv are at /home/liam/gerty.
- The OAuth token is at /home/liam/.openclaw/credentials/google-token.json (script reads it automatically).

## Example

User: "What have I got on 18th March?"

1. Parse: 2026-03-18
2. Exec: `cd /home/liam/gerty && /home/liam/gerty/.venv/bin/python scripts/check_google_calendar.py 2026-03-18`
3. Report the script's stdout verbatim to the user.
