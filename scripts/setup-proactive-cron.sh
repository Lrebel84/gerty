#!/bin/bash
# Add the proactive-agent system cron job.
# OpenClaw's built-in cron has issues with isolated sessions + tools; system cron works.

set -e

echo "Adding proactive-heartbeat to system crontab..."
(crontab -l 2>/dev/null | grep -v "proactive-heartbeat"; echo '0 */4 * * * /home/liam/gerty/scripts/proactive-heartbeat.sh') | crontab -

echo ""
echo "Done. Verify with: crontab -l"
echo "Test: ./scripts/proactive-heartbeat.sh"
echo "Log: tail logs/proactive.log"
echo "Findings: notes/areas/proactive-updates.md"
