"""Telegram bot: receive commands and chat from mobile."""

import asyncio
import logging
from typing import Callable

from gerty.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS

logger = logging.getLogger(__name__)


def create_bot(router_callback: Callable[[str], str]):
    """Create and run Telegram bot. Blocks until stopped."""

    if not TELEGRAM_BOT_TOKEN:
        logger.info("TELEGRAM_BOT_TOKEN not set, skipping Telegram bot")
        return

    if not TELEGRAM_CHAT_IDS:
        logger.info("TELEGRAM_CHAT_IDS not set, skipping Telegram bot")
        return

    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        filters,
        ContextTypes,
    )

    def is_authorized(chat_id: int) -> bool:
        return chat_id in TELEGRAM_CHAT_IDS

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        await update.message.reply_text(
            "Hi! I'm Gerty. Send me a message or use:\n"
            "/chat <message> - Chat with me\n"
            "/time - Current time\n"
            "/alarm <time> - Set alarm\n"
            "/timer <duration> - Set timer"
        )

    async def handle_chat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not is_authorized(update.effective_chat.id):
            return
        text = " ".join(context.args) if context.args else ""
        if not text:
            await update.message.reply_text("Usage: /chat <message>")
            return
        try:
            reply = router_callback(text)
            await update.message.reply_text(reply)
        except Exception as e:
            logger.exception("Chat command error")
            await update.message.reply_text("Something went wrong. Please try again.")

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return
        if not is_authorized(update.effective_chat.id):
            await update.message.reply_text("Unauthorized.")
            return
        text = update.message.text.strip()
        if text.startswith("/"):
            return  # Commands handled by CommandHandlers
        try:
            reply = router_callback(text)
            await update.message.reply_text(reply)
        except Exception as e:
            logger.exception("Message handler error")
            await update.message.reply_text("Something went wrong. Please try again.")

    async def cmd_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update.effective_chat.id):
            return
        try:
            reply = router_callback("what time is it")
            await update.message.reply_text(reply)
        except Exception:
            logger.exception("Time command error")
            await update.message.reply_text("Something went wrong. Please try again.")

    async def cmd_alarm(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update.effective_chat.id):
            return
        text = update.message.text or ""
        msg = text.replace("/alarm", "").strip() or "list"
        try:
            if msg == "list":
                reply = router_callback("list my alarms")
            else:
                reply = router_callback(f"set alarm for {msg}")
            await update.message.reply_text(reply)
        except Exception:
            logger.exception("Alarm command error")
            await update.message.reply_text("Something went wrong. Please try again.")

    async def cmd_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update.effective_chat.id):
            return
        text = update.message.text or ""
        msg = text.replace("/timer", "").strip() or "list"
        try:
            if msg == "list":
                reply = router_callback("list timers")
            else:
                reply = router_callback(f"timer {msg}")
            await update.message.reply_text(reply)
        except Exception:
            logger.exception("Timer command error")
            await update.message.reply_text("Something went wrong. Please try again.")

    def run():
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("chat", handle_chat_cmd))
        app.add_handler(CommandHandler("time", cmd_time))
        app.add_handler(CommandHandler("alarm", cmd_alarm))
        app.add_handler(CommandHandler("timer", cmd_timer))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.run_polling(allowed_updates=Update.ALL_TYPES)

    run()
