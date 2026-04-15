"""
main.py
The core of the bot.
  - Connects to Telegram as a userbot using Telethon
  - Listens to the private source channel
  - Parses every new message for valid signals
  - Executes trades on MT5
  - Sends confirmation/failure notifications to the personal channel
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
from trade_executor import connect_mt5, disconnect_mt5, execute_trade

# =============================================================
#  LOGGING SETUP
# =============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)

# =============================================================
#  TELEGRAM CLIENT
# =============================================================
client = TelegramClient(TELEGRAM_SESSION_NAME, TELEGRAM_API_ID, TELEGRAM_API_HASH)


async def send_notification(text: str):
    """Send a message to the personal Telegram channel."""
    try:
        await client.send_message(PERSONAL_CHANNEL, text)
    except FloodWaitError as e:
        logger.warning(f"Flood wait — sleeping {e.seconds}s")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


# =============================================================
#  MAIN SIGNAL HANDLER
# =============================================================
@client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def handle_new_message(event):
    """
    Triggered on every new message in the source channel.
    Full pipeline: receive → parse → validate → execute → notify.
    """
    message_text = event.message.message
    if not message_text:
        return  # Ignore media-only messages with no text

    logger.info(f"📨 New message received:\n{message_text}\n{'─'*50}")

    # --- STEP 1: Parse the signal ---
    signal = parse_signal(message_text)

    if signal is None:
        logger.info("⏭️  Message skipped — not a valid signal.")
        return

    # --- STEP 2: Log & notify signal was detected ---
    summary = format_signal_summary(signal)
    logger.info(summary)
    await send_notification(f"🔍 Signal Detected — Attempting execution...\n\n{summary}")

    # --- STEP 3: Execute the trade on MT5 ---
    result = execute_trade(signal)

    # --- STEP 4: Notify result ---
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    notification = f"{result['message']}\n\n🕐 {timestamp}"
    await send_notification(notification)


# =============================================================
#  STARTUP & SHUTDOWN
# =============================================================
async def startup():
    """Run startup checks before listening."""
    logger.info("=" * 60)
    logger.info("  TELEGRAM → MT5 SIGNAL BOT  |  Starting up...")
    logger.info("=" * 60)

    # Check config is filled
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH or not TELEGRAM_PHONE:
        logger.error("❌ Telegram credentials missing in config.py — aborting.")
        sys.exit(1)

    if not SOURCE_CHANNEL or not PERSONAL_CHANNEL:
        logger.error("❌ SOURCE_CHANNEL or PERSONAL_CHANNEL not set in config.py — aborting.")
        sys.exit(1)

    # Connect to MT5
    if not connect_mt5():
        logger.error("❌ Could not connect to MT5 — aborting.")
        sys.exit(1)

    logger.info(f"👂 Listening to channel: {SOURCE_CHANNEL}")
    logger.info(f"📲 Notifications → {PERSONAL_CHANNEL}")
    logger.info("✅ Bot is live and waiting for signals...\n")

    await send_notification(
        "🤖 Signal Bot is LIVE!\n"
        f"📡 Monitoring: {SOURCE_CHANNEL}\n"
        "✅ MT5 connected and ready to trade."
    )


async def main():
    """Entry point."""
    await client.start(phone=TELEGRAM_PHONE)
    await startup()

    try:
        await client.run_until_disconnected()
    finally:
        disconnect_mt5()
        logger.info("Bot stopped. MT5 disconnected.")


# =============================================================
#  RUN
# =============================================================
if __name__ == "__main__":
    asyncio.run(main())
