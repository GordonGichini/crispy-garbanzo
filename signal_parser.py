"""
signal_parser.py
Parses and validates trading signals from Telegram messages.
Only accepts signals with a clearly defined entry range, at least one TP, and an SL.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from config import SYMBOL_MAP

logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    symbol: str           # MT5 symbol e.g. "XAUUSD"
    direction: str        # "BUY" or "SELL"
    entry_low: float      # Lower bound of entry range
    entry_high: float     # Upper bound of entry range
    tps: list             # List of take profit levels [TP1, TP2, TP3, TP4]
    sl: float             # Stop loss
    raw_message: str      # Original message for logging


def parse_signal(message: str) -> Optional[TradeSignal]:
    """
    Parse a Telegram message and return a TradeSignal if valid.
    Returns None if the signal is incomplete or not a trading signal.
    """
    text = message.strip().upper()

    # --- Step 1: Detect direction (BUY or SELL) ---
    direction_match = re.search(r'\b(BUY|SELL)\b', text)
    if not direction_match:
        logger.debug("No BUY/SELL found — skipping message.")
        return None
    direction = direction_match.group(1)

    # --- Step 2: Detect symbol ---
    symbol = None
    for keyword, mt5_symbol in SYMBOL_MAP.items():
        if keyword in text:
            symbol = mt5_symbol
            break
    if not symbol:
        logger.debug("No recognized symbol found — skipping.")
        return None

    # --- Step 3: Detect entry range (e.g. 4994/4998 or 4994_4998 or 4994-4998) ---
    entry_match = re.search(
        r'\b(\d{3,6}(?:\.\d+)?)[\/\-_](\d{3,6}(?:\.\d+)?)\b', text
    )
    if not entry_match:
        logger.debug("No valid entry range found — skipping.")
        return None

    entry_low  = float(entry_match.group(1))
    entry_high = float(entry_match.group(2))

    # Ensure low ≤ high
    if entry_low > entry_high:
        entry_low, entry_high = entry_high, entry_low

    # --- Step 4: Detect Take Profits ---
    tp_matches = re.findall(
        r'TP\s*(?:OPEN\s*)?\.?\s*(\d{3,6}(?:\.\d+)?)', text
    )
    if not tp_matches:
        logger.debug("No TP levels found — skipping (vague signal).")
        return None
    tps = [float(tp) for tp in tp_matches]

    # --- Step 5: Detect Stop Loss ---
    sl_match = re.search(r'SL\.?\s*(\d{3,6}(?:\.\d+)?)', text)
    if not sl_match:
        logger.debug("No SL found — skipping (vague signal).")
        return None
    sl = float(sl_match.group(1))

    signal = TradeSignal(
        symbol=symbol,
        direction=direction,
        entry_low=entry_low,
        entry_high=entry_high,
        tps=tps,
        sl=sl,
        raw_message=message
    )

    logger.info(
        f"✅ Valid signal parsed: {signal.direction} {signal.symbol} | "
        f"Entry: {signal.entry_low}/{signal.entry_high} | "
        f"TPs: {signal.tps} | SL: {signal.sl}"
    )
    return signal


def format_signal_summary(signal: TradeSignal) -> str:
    """Returns a human-readable summary of the parsed signal."""
    tp_lines = "\n".join(
        [f"  TP{i+1}: {tp}" for i, tp in enumerate(signal.tps)]
    )
    return (
        f"📊 Signal Detected:\n"
        f"  {signal.direction} {signal.symbol}\n"
        f"  Entry Range: {signal.entry_low} – {signal.entry_high}\n"
        f"{tp_lines}\n"
        f"  SL: {signal.sl}"
    )
