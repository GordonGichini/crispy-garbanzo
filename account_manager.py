"""
account_manager.py
Manages all slave MT5 accounts.
  - Loads accounts from accounts.json
  - Executes trades on ALL enabled accounts in parallel
  - Handles per-account lot sizing based on individual balance & risk %
  - Supports enabling/disabling accounts on the fly
  - Supports multiple brokers
"""

import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import MetaTrader5 as mt5

from signal_parser import TradeSignal
from lot_calculator import calculate_lot
from config import MAGIC_NUMBER, MAX_SLIPPAGE, TP_MODE

logger = logging.getLogger(__name__)

ACCOUNTS_FILE = Path(__file__).parent / "accounts.json"


# ─────────────────────────────────────────────────────────────
# ACCOUNT DATA MODEL
# ─────────────────────────────────────────────────────────────
class SlaveAccount:
    def __init__(self, data: dict):
        self.id           = data["id"]
        self.name         = data["name"]
        self.login        = data["login"]
        self.password     = data["password"]
        self.server       = data["server"]
        self.risk_percent = data.get("risk_percent", 2.0)
        self.enabled      = data.get("enabled", True)
        self.notes        = data.get("notes", "")

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "name":         self.name,
            "login":        self.login,
            "password":     self.password,
            "server":       self.server,
            "risk_percent": self.risk_percent,
            "enabled":      self.enabled,
            "notes":        self.notes,
        }

    def __repr__(self):
        status = "✅" if self.enabled else "⏸️"
        return f"{status} [{self.id}] {self.name} | Login: {self.login} | Risk: {self.risk_percent}%"


# ─────────────────────────────────────────────────────────────
# LOAD / SAVE ACCOUNTS
# ─────────────────────────────────────────────────────────────
def load_accounts() -> list[SlaveAccount]:
    """Load all accounts from accounts.json."""
    if not ACCOUNTS_FILE.exists():
        logger.warning("accounts.json not found — no accounts loaded.")
        return []
    with open(ACCOUNTS_FILE, "r") as f:
        data = json.load(f)
    accounts = [SlaveAccount(a) for a in data.get("accounts", [])]
    logger.info(f"Loaded {len(accounts)} account(s) from accounts.json.")
    return accounts


def save_accounts(accounts: list[SlaveAccount]):
    """Persist accounts list back to accounts.json."""
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump({"accounts": [a.to_dict() for a in accounts]}, f, indent=2)
    logger.info("accounts.json saved.")


def get_next_id(accounts: list[SlaveAccount]) -> int:
    return max((a.id for a in accounts), default=0) + 1


# ─────────────────────────────────────────────────────────────
# ADD / REMOVE / TOGGLE ACCOUNTS
# ─────────────────────────────────────────────────────────────
def add_account(login: int, password: str, server: str,
                name: str, risk_percent: float = 2.0, notes: str = "") -> tuple[bool, str]:
    """Add a new slave account."""
    accounts = load_accounts()

    # Check for duplicate login
    if any(a.login == login for a in accounts):
        return False, f"Account {login} already exists."

    new_account = SlaveAccount({
        "id":           get_next_id(accounts),
        "name":         name,
        "login":        login,
        "password":     password,
        "server":       server,
        "risk_percent": risk_percent,
        "enabled":      True,
        "notes":        notes,
    })

    # Verify credentials work before saving
    ok, msg = verify_account_credentials(new_account)
    if not ok:
        return False, f"Could not connect to MT5 account {login}: {msg}"

    accounts.append(new_account)
    save_accounts(accounts)
    return True, f"✅ Account [{new_account.id}] {name} added successfully."


def remove_account(account_id: int) -> tuple[bool, str]:
    """Remove an account by ID."""
    accounts = load_accounts()
    match = next((a for a in accounts if a.id == account_id), None)
    if not match:
        return False, f"No account found with ID {account_id}."
    accounts.remove(match)
    save_accounts(accounts)
    return True, f"🗑️ Account [{account_id}] {match.name} removed."


def toggle_account(account_id: int, enabled: bool) -> tuple[bool, str]:
    """Enable or disable a specific account."""
    accounts = load_accounts()
    match = next((a for a in accounts if a.id == account_id), None)
    if not match:
        return False, f"No account found with ID {account_id}."
    match.enabled = enabled
    save_accounts(accounts)
    status = "▶️ Resumed" if enabled else "⏸️ Paused"
    return True, f"{status} account [{account_id}] {match.name}."


def update_risk(account_id: int, risk_percent: float) -> tuple[bool, str]:
    """Update risk % for a specific account."""
    accounts = load_accounts()
    match = next((a for a in accounts if a.id == account_id), None)
    if not match:
        return False, f"No account found with ID {account_id}."
    match.risk_percent = risk_percent
    save_accounts(accounts)
    return True, f"📊 Account [{account_id}] {match.name} risk updated to {risk_percent}%."


def list_accounts_summary() -> str:
    """Returns a formatted summary of all accounts."""
    accounts = load_accounts()
    if not accounts:
        return "No accounts configured yet.\nUse /addaccount to add one."
    lines = ["📋 *Slave Accounts:*\n"]
    for a in accounts:
        status = "✅ Active" if a.enabled else "⏸️ Paused"
        lines.append(
            f"{status} | [{a.id}] {a.name}\n"
            f"   Login: {a.login} | Server: {a.server}\n"
            f"   Risk: {a.risk_percent}%\n"
        )
    active = sum(1 for a in accounts if a.enabled)
    lines.append(f"Total: {len(accounts)} accounts | {active} active")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# CREDENTIAL VERIFICATION
# ─────────────────────────────────────────────────────────────
def verify_account_credentials(account: SlaveAccount) -> tuple[bool, str]:
    """Test login for a single account. Returns (success, message)."""
    if not mt5.initialize():
        return False, "MT5 failed to initialize."
    if not mt5.login(account.login, password=account.password, server=account.server):
        error = mt5.last_error()
        mt5.shutdown()
        return False, str(error)
    mt5.shutdown()
    return True, "OK"


# ─────────────────────────────────────────────────────────────
# SINGLE ACCOUNT TRADE EXECUTION
# ─────────────────────────────────────────────────────────────
def execute_on_account(account: SlaveAccount, signal: TradeSignal) -> dict:
    """
    Execute a trade on one slave account.
    Each account gets its own MT5 session (thread-safe).
    Returns result dict.
    """
    result_base = {"account_id": account.id, "account_name": account.name}

    try:
        # Initialize fresh MT5 connection for this account
        if not mt5.initialize():
            return {**result_base, "success": False,
                    "message": f"MT5 init failed for {account.name}"}

        if not mt5.login(account.login, password=account.password, server=account.server):
            mt5.shutdown()
            return {**result_base, "success": False,
                    "message": f"Login failed: {mt5.last_error()}"}

        # Ensure symbol is visible
        if not mt5.symbol_select(signal.symbol, True):
            mt5.shutdown()
            return {**result_base, "success": False,
                    "message": f"Symbol {signal.symbol} not found on {account.server}"}

        # Get current price
        tick = mt5.symbol_info_tick(signal.symbol)
        if tick is None:
            mt5.shutdown()
            return {**result_base, "success": False, "message": "Cannot get tick price"}

        current_price = tick.bid if signal.direction == "SELL" else tick.ask

        # Range check
        if not (signal.entry_low <= current_price <= signal.entry_high):
            mt5.shutdown()
            return {**result_base, "success": False,
                    "message": (f"⚠️ Price out of range "
                                f"({current_price} not in {signal.entry_low}–{signal.entry_high})")}

        # Get account balance
        account_info = mt5.account_info()
        balance = account_info.balance

        # Calculate lot per this account's balance + risk
        lot = calculate_lot(
            symbol=signal.symbol,
            sl_price=signal.sl,
            entry_price=current_price,
            balance=balance,
            risk_percent=account.risk_percent
        )

        # Select TP
        tp = signal.tps[-1] if TP_MODE == "final" else signal.tps[0]

        # Build order
        order_type = mt5.ORDER_TYPE_SELL if signal.direction == "SELL" else mt5.ORDER_TYPE_BUY
        request = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       signal.symbol,
            "volume":       lot,
            "type":         order_type,
            "price":        current_price,
            "sl":           signal.sl,
            "tp":           tp,
            "deviation":    MAX_SLIPPAGE,
            "magic":        MAGIC_NUMBER,
            "comment":      f"TG_Bot_Slave_{account.id}",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        mt5.shutdown()

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return {**result_base, "success": False,
                    "message": f"Order failed. Retcode: {result.retcode if result else 'None'}"}

        return {
            **result_base,
            "success": True,
            "message": (
                f"✅ [{account.name}] {signal.direction} {signal.symbol}\n"
                f"   Entry: {current_price} | Lot: {lot} | "
                f"TP: {tp} | SL: {signal.sl} | Ticket: #{result.order}"
            ),
            "ticket": result.order,
            "lot":    lot,
            "entry":  current_price,
        }

    except Exception as e:
        try:
            mt5.shutdown()
        except Exception:
            pass
        return {**result_base, "success": False, "message": f"Exception: {str(e)}"}


# ─────────────────────────────────────────────────────────────
# PARALLEL EXECUTION ACROSS ALL ACCOUNTS
# ─────────────────────────────────────────────────────────────
async def execute_on_all_accounts(signal: TradeSignal) -> list[dict]:
    """
    Fire the signal across ALL enabled accounts simultaneously.
    Uses a thread pool so MT5 calls don't block the async event loop.
    """
    accounts = load_accounts()
    enabled  = [a for a in accounts if a.enabled]

    if not enabled:
        return [{"account_id": 0, "account_name": "N/A",
                 "success": False, "message": "No active accounts configured."}]

    logger.info(f"⚡ Firing signal on {len(enabled)} account(s) in parallel...")

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=len(enabled)) as executor:
        futures = [
            loop.run_in_executor(executor, execute_on_account, account, signal)
            for account in enabled
        ]
        results = await asyncio.gather(*futures)

    # Log summary
    success_count = sum(1 for r in results if r["success"])
    logger.info(f"Execution complete: {success_count}/{len(enabled)} accounts filled.")
    return list(results)


def format_execution_report(results: list[dict]) -> str:
    """Format all execution results into one clean Telegram notification."""
    success = [r for r in results if r["success"]]
    failed  = [r for r in results if not r["success"]]

    lines = [f"📊 *Execution Report* ({len(success)}/{len(results)} filled)\n"]

    for r in success:
        lines.append(r["message"])

    if failed:
        lines.append("\n⚠️ *Failed:*")
        for r in failed:
            lines.append(f"❌ [{r['account_name']}]: {r['message']}")

    return "\n".join(lines)