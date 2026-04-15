"""
find_symbols.py
Connects to MT5 and lists ALL available symbols containing
common keywords — so we know the EXACT name Exness uses.
Run this once to fix the symbol map in config.py.
"""

import MetaTrader5 as mt5
from trade_executor import connect_mt5, disconnect_mt5

KEYWORDS = ["XAU", "GOLD", "XAG", "SILVER", "OIL", "BTC", "EUR", "GBP", "USD"]

if connect_mt5():
    print("\n📋 Searching for symbols on your broker...\n")
    all_symbols = mt5.symbols_get()

    for keyword in KEYWORDS:
        matches = [s.name for s in all_symbols if keyword.upper() in s.name.upper()]
        if matches:
            print(f"  {keyword}: {matches}")

    disconnect_mt5()