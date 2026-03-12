# Alarms

## Current Behavior

When you set an alarm, Gerty stores it in `data/alarms.json`. When the alarm time is reached:

1. **Notifications** – Gerty sends the alarm message via TTS (speaks it), system notification, and Telegram (if configured).
2. **Message** – "This is your [time] alarm, say cancel to stop"
3. **TTS repeat** – The message repeats every 30 seconds until you stop it.

## How to Stop an Alarm

- **Voice:** Say "cancel alarms" or "remove alarms" – this clears all alarms.
- **Chat:** Type "cancel alarms" or "remove alarms".
- **Telegram:** Send "cancel alarms" or use `/alarm list` then manage as needed.

## Setting Alarms

- **Chat/Voice:** "set alarm for 7am", "wake me at 7:30", "alarm for 6pm"
- **Formats:** 7am, 7:30 pm, 7 30, 19:00. Voice: "eleven oh five", "seven thirty am"
- **Telegram:** `/alarm 7:30` or `/alarm list`

## Note on Voice Cancel

A "say cancel to stop" flow (mic opens automatically, listens for "cancel"/"stop"/wake word) was attempted multiple times but did not work reliably. The alarm still works with notifications and manual cancel. See `docs/archive/ALARM_STATUS.md` for implementation history.
