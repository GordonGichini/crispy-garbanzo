"""
lot_calculator.py
Calculates the correct lot size based on:
  - Account balance
  - Risk percentage per trade
  - Stop loss distance in pips/points
Works correctly for XAUUSD (Gold) and other instruments on MT5.
"""

import logging
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

# Minimum and maximum lot sizes (broker-standard)
MIN_LOT = 0.01
MAX_LOT = 100.0


def get_pip_value(symbol: str, lot: float = 1.0) -> float:
    """
    Returns the monetary value of 1 pip for 1 lot on the given symbol.
    MT5 calculates this precisely via tick value.
    """
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"Symbol '{symbol}' not found in MT5 Market Watch.")

    # tick_value = profit for 1 tick move on 1 lot
    # We normalize to 1 pip (= 10 ticks for 5-digit brokers, or 1 tick for others)
    tick_value = info.trade_tick_value
    tick_size  = info.trade_tick_size
    point      = info.point

    # 1 pip = 1 point for most metals/indices
    pip_value_per_lot = (point / tick_size) * tick_value
    return pip_value_per_lot


def calculate_lot(
    symbol: str,
    sl_price: float,
    entry_price: float,
    balance: float,
    risk_percent: float
) -> float:
    """
    Calculate lot size using:
      Lot = (Balance × Risk%) / (SL distance in points × pip value per lot)

    Args:
        symbol:       MT5 symbol string e.g. "XAUUSD"
        sl_price:     Stop loss price level
        entry_price:  Actual entry price used
        balance:      Account balance in deposit currency
        risk_percent: Risk as a percentage (e.g. 2.0 for 2%)

    Returns:
        Calculated and broker-validated lot size (float)
    """
    info = mt5.symbol_info(symbol)
    if info is None:
        raise ValueError(f"Cannot get symbol info for '{symbol}'")

    point         = info.point
    lot_step      = info.volume_step
    lot_min       = max(info.volume_min, MIN_LOT)
    lot_max       = min(info.volume_max, MAX_LOT)

    # SL distance in points
    sl_distance_points = abs(entry_price - sl_price) / point
    if sl_distance_points == 0:
        raise ValueError("SL distance is zero — cannot calculate lot size.")

    # Money at risk
    risk_amount = balance * (risk_percent / 100)

    # Pip value for 1 lot
    pip_value = get_pip_value(symbol, lot=1.0)

    # Raw lot calculation
    raw_lot = risk_amount / (sl_distance_points * pip_value)

    # Round DOWN to nearest lot step (never round up — protect account)
    lot = round(int(raw_lot / lot_step) * lot_step, 8)

    # Clamp within broker limits
    lot = max(lot_min, min(lot, lot_max))

    logger.info(
        f"💰 Lot Calculation → Balance: ${balance:.2f} | "
        f"Risk: {risk_percent}% (${risk_amount:.2f}) | "
        f"SL Distance: {sl_distance_points:.1f} pts | "
        f"Pip Value: {pip_value:.4f} | "
        f"Lot Size: {lot}"
    )
    return lot
