"""
main.py
The core of the Prop Firm Management Bot.
  - Listens to signal channel (switchable on the fly)
  - Executes trades on ALL slave accounts simultaneously
  - Accepts commands from personal channel to control everything
  - Notifies personal channel with full execution report per signal
"""

import asyncio
import logging
import sys
from datetime import datetime

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

from config import (
    TELEGRAM_API_ID, TELEGRAM_API_HASH,
    TELEGRAM_PHONE, TELEGRAM_SESSION_NAME,
    SOURCE_CHANNEL, PERSONAL_CHANNEL,
    LOG_FILE
)
from signal_parser import parse_signal, format_signal_summary
from account_manager import execute_on_all_accounts, format_execution_report
from command_handler import handle_command, get_active_channel

# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# TELEGRAM CLIENT
# ─────────────────────────────────────────────────────────────
client = TelegramClient(TELEGRAM_SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH)


async def send_notification(text: str):
    """Send a message to the personal Telegram channel."""
    try:
        await client.send_message(PERSONAL_CHANNEL, text)
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds)
    except Exception as e:
        logger.error(f"Notification failed: {e}")


# ─────────────────────────────────────────────────────────────
# PERSONAL CHANNEL — COMMAND LISTENER
# ─────────────────────────────────────────────────────────────
@client.on(events.NewMessage(chats=PERSONAL_CHANNEL, outgoing=True))
async def handle_personal_channel(event):
    """
    Listen to messages the client sends in his own personal channel.
    If it's a command (/help, /pause, /setchannel etc.) — handle it.
    """
    text = event.message.message
    if not text:
        return
    await handle_command(text, client, PERSONAL_CHANNEL, SOURCE_CHANNEL)


# ─────────────────────────────────────────────────────────────
# SIGNAL CHANNEL — MAIN TRADING LISTENER
# ─────────────────────────────────────────────────────────────
@client.on(events.NewMessage())
async def handle_new_message(event):
    """
    Listens to ALL incoming messages and filters for the active signal channel.
    Dynamic channel matching so /setchannel works without restarting.
    """
    active_channel = get_active_channel(SOURCE_CHANNEL)

    try:
        chat = await event.get_chat()
        chat_username = getattr(chat, "username", None)
        chat_id       = getattr(chat, "id", None)
        chat_invite   = getattr(chat, "invite_link", None)
    except Exception:
        return

    channel_match = (
        (chat_username and chat_username.lower() in active_channel.lower()) or
        (str(chat_id) in active_channel) or
        (chat_invite and active_channel in chat_invite)
    )

    if not channel_match:
        return

    message_text = event.message.message
    if not message_text:
        return

    logger.info(f"📨 Signal channel message:\n{message_text}\n{'─'*50}")

    # ── Parse ──
    signal = parse_signal(message_text)
    if signal is None:
        logger.info("⏭️  Skipped — not a valid signal.")
        return

    # ── Notify signal detected ──
    summary = format_signal_summary(signal)
    await send_notification(f"🔍 Signal Detected — Executing on all accounts...\n\n{summary}")

    # ── Execute on ALL slave accounts in parallel ──
    results = await execute_on_all_accounts(signal)

    # ── Send full execution report ──
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = format_execution_report(results)
    await send_notification(f"{report}\n\n🕐 {timestamp}")


# ─────────────────────────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────────────────────────
async def startup():
    logger.info("=" * 60)
    logger.info("  PROP FIRM MANAGEMENT BOT  |  Starting up...")
    logger.info("=" * 60)

    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH or not TELEGRAM_PHONE:
        logger.error("❌ Telegram credentials missing in config.py")
        sys.exit(1)

    active_channel = get_active_channel(SOURCE_CHANNEL)
    logger.info(f"📡 Listening to: {active_channel}")
    logger.info(f"📲 Commands & notifications → {PERSONAL_CHANNEL}")
    logger.info("✅ Bot is live!\n")

    await send_notification(
        "🤖 *Prop Firm Management Bot is LIVE!*\n\n"
        f"📡 Signal Channel: {active_channel}\n"
        "✅ All systems ready.\n\n"
        "Type /help to see all available commands."
    )


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────
async def main():
    await client.start(phone=TELEGRAM_PHONE)
    await startup()
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())