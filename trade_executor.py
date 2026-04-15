"""
trade_executor.py
Handles all MT5 operations:
  - Connecting / disconnecting
  - Range validation (is price still in entry range?)
  - Placing market orders with TP and SL
  - Returning results for Telegram notifications
"""

import logging
import MetaTrader5 as mt5
from signal_parser import TradeSignal
from lot_calculator import calculate_lot
from config import (
    MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH,
    RISK_PERCENT, TP_MODE, MAGIC_NUMBER, MAX_SLIPPAGE
)

logger = logging.getLogger(__name__)


def connect_mt5() -> bool:
    """Initialize and log in to MT5 terminal."""
    kwargs = {}
    if MT5_PATH:
        kwargs["path"] = MT5_PATH

    if not mt5.initialize(**kwargs):
        logger.error(f"MT5 initialize failed: {mt5.last_error()}")
        return False

    if not mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        logger.error(f"MT5 login failed: {mt5.last_error()}")
        mt5.shutdown()
        return False

    account = mt5.account_info()
    logger.info(
        f"✅ MT5 Connected | Account: {account.login} | "
        f"Balance: ${account.balance:.2f} | Server: {account.server}"
    )
    return True


def disconnect_mt5():
    """Safely disconnect from MT5."""
    mt5.shutdown()
    logger.info("MT5 disconnected.")


def get_current_price(symbol: str, direction: str) -> float:
    """
    Returns the relevant current price:
    - SELL trades use the BID price (what market pays you)
    - BUY  trades use the ASK price (what you pay market)
    """
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise ValueError(f"Cannot get tick for {symbol}")
    return tick.bid if direction == "SELL" else tick.ask


def is_price_in_range(current_price: float, entry_low: float, entry_high: float) -> bool:
    """Returns True if current price is within the signal's entry range."""
    return entry_low <= current_price <= entry_high


def execute_trade(signal: TradeSignal) -> dict:
    """
    Main execution function.
    1. Checks if price is still within the entry range.
    2. Calculates lot size.
    3. Selects TP based on TP_MODE.
    4. Places the market order.
    5. Returns a result dict for notification.

    Returns:
        dict with keys: success (bool), message (str), order (dict or None)
    """
    symbol    = signal.symbol
    direction = signal.direction

    # --- 1. Ensure symbol is available in Market Watch ---
    if not mt5.symbol_select(symbol, True):
        return {
            "success": False,
            "message": f"⚠️ Symbol {symbol} not found in MT5 Market Watch.",
            "order": None
        }

    # --- 2. Get current price ---
    try:
        current_price = get_current_price(symbol, direction)
    except ValueError as e:
        return {"success": False, "message": str(e), "order": None}

    # --- 3. Range check — CANCEL if price has moved out of range ---
    if not is_price_in_range(current_price, signal.entry_low, signal.entry_high):
        msg = (
            f"⚠️ Signal CANCELLED — Price out of range.\n"
            f"  Signal Range: {signal.entry_low} – {signal.entry_high}\n"
            f"  Current Price: {current_price}"
        )
        logger.warning(msg)
        return {"success": False, "message": msg, "order": None}

    # --- 4. Get account balance ---
    account_info = mt5.account_info()
    if account_info is None:
        return {"success": False, "message": "Cannot retrieve account info from MT5.", "order": None}
    balance = account_info.balance

    # --- 5. Calculate lot size ---
    try:
        lot = calculate_lot(
            symbol=symbol,
            sl_price=signal.sl,
            entry_price=current_price,
            balance=balance,
            risk_percent=RISK_PERCENT
        )
    except ValueError as e:
        return {"success": False, "message": f"Lot calc error: {e}", "order": None}

    # --- 6. Select Take Profit ---
    if TP_MODE == "final":
        tp = signal.tps[-1]   # Last TP in the list
    else:
        tp = signal.tps[0]    # First TP (future: will split across all)

    # --- 7. Build MT5 order request ---
    order_type = mt5.ORDER_TYPE_SELL if direction == "SELL" else mt5.ORDER_TYPE_BUY

    request = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       symbol,
        "volume":       lot,
        "type":         order_type,
        "price":        current_price,
        "sl":           signal.sl,
        "tp":           tp,
        "deviation":    MAX_SLIPPAGE,
        "magic":        MAGIC_NUMBER,
        "comment":      "TG_Signal_Bot",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # --- 8. Send order ---
    result = mt5.order_send(request)

    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        error_msg = f"❌ Order failed. Retcode: {result.retcode if result else 'None'} | {mt5.last_error()}"
        logger.error(error_msg)
        return {"success": False, "message": error_msg, "order": None}

    success_msg = (
        f"✅ Trade Executed!\n"
        f"  {direction} {symbol}\n"
        f"  Entry: {current_price}\n"
        f"  Lot: {lot}\n"
        f"  TP: {tp}\n"
        f"  SL: {signal.sl}\n"
        f"  Ticket: #{result.order}"
    )
    logger.info(success_msg)
    return {
        "success": True,
        "message": success_msg,
        "order": {
            "ticket":    result.order,
            "symbol":    symbol,
            "direction": direction,
            "entry":     current_price,
            "lot":       lot,
            "tp":        tp,
            "sl":        signal.sl,
        }
    }
