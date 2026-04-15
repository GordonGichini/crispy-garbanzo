"""
command_handler.py
Handles all Telegram commands sent to the bot's personal channel.
The client controls everything from his phone — no code edits needed.

Available commands:
  /status               → Current channel + active accounts summary
  /accounts             → List all slave accounts
  /addaccount           → Add a new slave account
  /removeaccount <id>   → Remove an account
  /pause <id>           → Pause a specific account
  /resume <id>          → Resume a specific account
  /setrisk <id> <%>     → Update risk % for an account
  /setchannel <link>    → Switch the signal source channel
  /currentchannel       → Show active signal channel
  /help                 → Show all commands
"""

import logging
import json
from pathlib import Path
from account_manager import (
    add_account, remove_account, toggle_account,
    update_risk, list_accounts_summary
)

logger = logging.getLogger(__name__)
RUNTIME_FILE = Path(__file__).parent / "runtime.json"


# ─────────────────────────────────────────────────────────────
# RUNTIME STATE (channel switching + any live settings)
# ─────────────────────────────────────────────────────────────
def load_runtime() -> dict:
    if RUNTIME_FILE.exists():
        with open(RUNTIME_FILE) as f:
            return json.load(f)
    return {}


def save_runtime(data: dict):
    with open(RUNTIME_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_active_channel(default_channel: str) -> str:
    """Returns the currently active signal channel (runtime override or config default)."""
    runtime = load_runtime()
    return runtime.get("source_channel", default_channel)


def set_active_channel(channel: str):
    runtime = load_runtime()
    runtime["source_channel"] = channel
    save_runtime(runtime)


# ─────────────────────────────────────────────────────────────
# COMMAND ROUTER
# ─────────────────────────────────────────────────────────────
async def handle_command(text: str, bot_client, personal_channel: str, default_channel: str) -> bool:
    """
    Parse and handle a command message.
    Returns True if it was a command, False if it was a regular message.
    """
    text = text.strip()
    if not text.startswith("/"):
        return False

    parts = text.split()
    cmd   = parts[0].lower()

    # ── /help ──
    if cmd == "/help":
        reply = (
            "🤖 *Signal Bot Commands*\n\n"
            "*Signal Channel:*\n"
            "`/setchannel <link>` — Switch signal provider\n"
            "`/currentchannel` — Show active channel\n\n"
            "*Account Management:*\n"
            "`/accounts` — List all accounts\n"
            "`/addaccount <login> <password> <server> <name> <risk%>`\n"
            "`/removeaccount <id>` — Remove account\n"
            "`/pause <id>` — Pause an account\n"
            "`/resume <id>` — Resume an account\n"
            "`/setrisk <id> <risk%>` — Update risk %\n\n"
            "*General:*\n"
            "`/status` — Full system status\n"
            "`/help` — Show this message"
        )

    # ── /status ──
    elif cmd == "/status":
        channel = get_active_channel(default_channel)
        accounts_summary = list_accounts_summary()
        reply = (
            f"📡 *Bot Status*\n\n"
            f"*Signal Channel:*\n{channel}\n\n"
            f"{accounts_summary}"
        )

    # ── /accounts ──
    elif cmd == "/accounts":
        reply = list_accounts_summary()

    # ── /setchannel <link> ──
    elif cmd == "/setchannel":
        if len(parts) < 2:
            reply = "Usage: `/setchannel <channel_link_or_username>`"
        else:
            new_channel = parts[1]
            set_active_channel(new_channel)
            logger.info(f"Signal channel switched to: {new_channel}")
            reply = (
                f"✅ Signal channel updated!\n"
                f"Now listening to:\n{new_channel}\n\n"
                f"⚠️ Restart the bot for the new channel to take effect."
            )

    # ── /currentchannel ──
    elif cmd == "/currentchannel":
        channel = get_active_channel(default_channel)
        reply = f"📡 Active signal channel:\n{channel}"

    # ── /addaccount <login> <password> <server> <name> <risk%> ──
    elif cmd == "/addaccount":
        if len(parts) < 6:
            reply = (
                "Usage:\n"
                "`/addaccount <login> <password> <server> <name> <risk%>`\n\n"
                "Example:\n"
                "`/addaccount 123456789 mypassword Exness-MT5Trial9 ClientA 2.0`"
            )
        else:
            try:
                login       = int(parts[1])
                password    = parts[2]
                server      = parts[3]
                name        = parts[4]
                risk        = float(parts[5])
                ok, msg     = add_account(login, password, server, name, risk)
                reply       = msg
            except ValueError:
                reply = "❌ Invalid format. Login must be a number, risk must be a decimal (e.g. 2.0)."

    # ── /removeaccount <id> ──
    elif cmd == "/removeaccount":
        if len(parts) < 2:
            reply = "Usage: `/removeaccount <id>`"
        else:
            try:
                account_id  = int(parts[1])
                ok, msg     = remove_account(account_id)
                reply       = msg
            except ValueError:
                reply = "❌ Invalid ID. Must be a number."

    # ── /pause <id> ──
    elif cmd == "/pause":
        if len(parts) < 2:
            reply = "Usage: `/pause <account_id>`"
        else:
            try:
                ok, msg = toggle_account(int(parts[1]), enabled=False)
                reply   = msg
            except ValueError:
                reply = "❌ Invalid ID."

    # ── /resume <id> ──
    elif cmd == "/resume":
        if len(parts) < 2:
            reply = "Usage: `/resume <account_id>`"
        else:
            try:
                ok, msg = toggle_account(int(parts[1]), enabled=True)
                reply   = msg
            except ValueError:
                reply = "❌ Invalid ID."

    # ── /setrisk <id> <risk%> ──
    elif cmd == "/setrisk":
        if len(parts) < 3:
            reply = "Usage: `/setrisk <account_id> <risk_percent>`\nExample: `/setrisk 2 1.5`"
        else:
            try:
                ok, msg = update_risk(int(parts[1]), float(parts[2]))
                reply   = msg
            except ValueError:
                reply = "❌ Invalid format."

    else:
        reply = f"❓ Unknown command: `{cmd}`\nType `/help` to see all commands."

    await bot_client.send_message(personal_channel, reply)
    return True