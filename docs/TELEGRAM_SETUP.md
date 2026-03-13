# Telegram Setup

Control Gerty and OpenClaw from your phone via Telegram. All messages go through Gerty—no separate OpenClaw channel.

## Architecture

- **Single entry point:** Telegram → Gerty → Router → fast-path tools or OpenClaw
- **Replies:** Gerty sends responses back to Telegram
- **Notifications:** Alarms, timers, and pomodoro phases are sent to Telegram when configured

## Setup

### 1. Create the bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Enter a display name (e.g. `Gerty`)
4. Enter a username ending in `bot` (e.g. `gerty_assistant_bot`)
5. Copy the token (e.g. `7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

### 2. Get your chat ID

1. Search for **@userinfobot** in Telegram
2. Start a chat and send any message
3. It will reply with your numeric ID (e.g. `8734062810`)
4. Copy that number

### 3. Configure Gerty

Edit your `.env` in the Gerty project root:

```
TELEGRAM_BOT_TOKEN=7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_IDS=8734062810
```

- Replace with your actual token and chat ID
- For multiple users, use comma-separated IDs: `TELEGRAM_CHAT_IDS=123456,789012`

### 4. Start a chat with your bot

1. Search for your bot by its username (e.g. `@gerty_assistant_bot`)
2. Tap **Start** or send `/start`
3. You should see Gerty's intro and command list

### 5. Restart Gerty

Restart Gerty so it loads the new env vars and starts the Telegram bot.

### 6. Test

Send a message to your bot, for example:

- `what time is it`
- `list my skills` (verifies OpenClaw when enabled)
- `check my calendar`

You should get replies from Gerty.

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Intro and help |
| `/chat <message>` | Send a chat message |
| `/time` | Current time |
| `/alarm <time>` or `list` | Set alarm or list alarms |
| `/timer <duration>` or `list` | Set timer or list timers |

Plain text messages (e.g. "flip a coin", "list my skills") also work—they're routed to the same tools.

## Security

- Only chat IDs in `TELEGRAM_CHAT_IDS` can use the bot
- Anyone else gets "Unauthorized"
- Keep the bot token secret; don't commit it to git

## Troubleshooting

**No response when messaging the bot**

- Ensure Gerty is running (desktop or terminal)
- Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_IDS` are set in `.env`
- Verify your chat ID matches (use @userinfobot)
- Run with `GERTY_LOG_LEVEL=INFO` and check for "Telegram bot starting" in the log

**"Unauthorized"**

- Your chat ID is not in `TELEGRAM_CHAT_IDS`. Add it to `.env` and restart.
