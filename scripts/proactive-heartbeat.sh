#!/bin/bash
# Proactive agent heartbeat - runs every 4h via cron.
# The message must be explicit: "Proactive heartbeat" alone gets a lazy HEARTBEAT_OK.
# This tells the agent to actually run the checklist, use web tools, and log findings.

export PATH=/usr/local/bin:/usr/bin:/bin
MSG="HEARTBEAT: Read USER.md for search priorities. Run HEARTBEAT.md checklist. Use web_search for 1-2 items relevant to Liam's goals (Gerty, AI-run businesses, UK tech). Append findings to notes/areas/proactive-updates.md. Output a brief summary (3-5 lines) to stdout."

/home/liam/.npm-global/bin/openclaw agent --to 5789425841 --message "$MSG" --deliver >> /home/liam/gerty/logs/proactive.log 2>&1
