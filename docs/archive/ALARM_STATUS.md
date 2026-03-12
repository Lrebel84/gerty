# Alarm "Say Cancel to Stop" – Implementation Attempts (Failed)

## Intended Behavior

When an alarm triggers:
1. Gerty speaks: "This is your [time] alarm, say cancel to stop"
2. Message repeats every 30 seconds until stopped
3. Mic opens automatically and listens only for "cancel", "stop", or wake word
4. User hears a beep when the mic is listening
5. Alarm stays visible in the UI with a Stop button
6. User can stop via voice ("cancel"/"stop"/wake word) or by clicking Stop in the UI

## What Was Implemented

### Backend
- **`gerty/voice/alarm_state.py`** – New module:
  - `get_sounding_alarm()` / `set_sounding_alarm()` / `stop_alarm_sounding()`
  - TTS repeat thread: speaks message every 30s until stopped
  - Beep (`play_listening_ping`) when alarm starts
  - `stop_alarm_sounding()` removes alarm from file when dismissed

- **`gerty/main.py`** – Alarm trigger loop:
  - Calls `set_sounding_alarm(alarm)` before notify
  - `notify(msg, channels=["system", "tts", "telegram"])` with full message
  - `request_ptt_recording()` to open mic
  - Skips if alarm already sounding

- **`gerty/tools/alarms.py`** – `get_pending_alarms_for_trigger()` no longer removes alarms on trigger

- **`gerty/voice/loop.py`** – Voice integration:
  - When `get_sounding_alarm()`: if STT returns "cancel" or "stop", call `stop_alarm_sounding()`
  - When wake word detected and alarm sounding: stop alarm
  - Re-request PTT when user says something else (keep mic open)

- **`gerty/ui/server.py`** – API:
  - `GET /api/alarms` returns `sounding` in response
  - `POST /api/alarms/dismiss` calls `stop_alarm_sounding()`

### Frontend
- **ChatWindow** – Polls `/api/alarms` every 2s; shows amber banner with Stop button when `sounding` is set
- **Sidebar** – Alarms list includes sounding alarm with `sounding: true` and Stop button

## Result: Complete Failure

**Observed behavior:**
- Alarm still says "Alarm: alarm at [time]" (old message)
- Alarm vanishes from UI when it triggers
- No listening for "cancel" or "stop"
- No manual Stop button visible
- No beep when alarm starts

**Nothing worked as described.**

## Possible Causes (Not Investigated)

- Import/load order: `alarm_state` may not be loaded when alarm trigger runs
- Voice loop and alarm trigger run in different threads; state may not be shared correctly
- PTT request may be consumed or lost before voice loop processes it
- Frontend may not be receiving updated `sounding` from API
- TTS or playback may be failing silently
- Build or restart may not have been applied correctly

## Reverting

To restore the original alarm behavior (single notify, no voice cancel):

1. Remove or bypass `gerty/voice/alarm_state.py`
2. Restore `get_pending_alarms_for_trigger()` to remove alarms when due
3. Restore alarm trigger loop to use `notify(f"Alarm: {msg}", channels=["tts", "system", "telegram"])` only
4. Remove alarm-mode handling from voice loop
5. Remove alarm dismiss API and UI banner
6. Rebuild frontend
