# =============================================================
#         TELEGRAM → MT5 SIGNAL BOT — CONFIGURATION
# =============================================================
# Fill in your details below before running the bot.

# --- TELEGRAM API CREDENTIALS ---
# Get these from https://my.telegram.org (takes 2 minutes)
TELEGRAM_API_ID = 39934049              # e.g. 12345678
TELEGRAM_API_HASH = "7b6c7f757db618ccdd10156678bfb94d"           # e.g. "abc123def456..."
TELEGRAM_PHONE = "+242064618210"              # e.g. "+33612345678"
TELEGRAM_SESSION_NAME = "signal_bot"

# --- CHANNEL SETTINGS ---
# The private channel you receive signals from
SOURCE_CHANNEL = "https://t.me/+OVM9Z-_JoqI4ZDFk"              # e.g. "EZzaProManager" or channel numeric ID e.g. -1001234567890

# Your personal channel where confirmations are sent
PERSONAL_CHANNEL = "https://t.me/+Mn6fwlAnbXU0MWU0"            # e.g. "mytradeslog" or numeric ID

# --- MT5 SETTINGS ---
MT5_LOGIN = 435035534                   # Your MT5 account number
MT5_PASSWORD = "#Chadane2002"                # Your MT5 password
MT5_SERVER = "Exness-MT5Trial9"                  # e.g. "ICMarkets-Demo"
MT5_PATH = ""                    # Optional: path to MT5 terminal .exe
                                 # e.g. "C:/Program Files/MetaTrader 5/terminal64.exe"

# --- RISK MANAGEMENT ---
RISK_PERCENT = 2.0               # % of balance to risk per trade (e.g. 2.0 = 2%)
                                 # 1.0 = Conservative | 2.0 = Moderate | 3-5 = Aggressive

# --- TRADE SETTINGS ---
TP_MODE = "final"                # "final" = only last TP | "all" = split across all TPs
MAGIC_NUMBER = 20250101          # Unique ID to identify this bot's trades in MT5
MAX_SLIPPAGE = 10                # Max allowed slippage in points

# --- SYMBOL MAPPING ---
# Maps signal keywords → MT5 exact symbol names (check your broker's Market Watch)
SYMBOL_MAP = {
    "GOLD":   "XAUUSDm",
    "XAUUSD": "XAUUSDm",
    "SILVER": "XAGUSDm",
    "XAGUSD": "XAGUSDm",
    "OIL":    "USOILm",
    "USOIL":  "USOILm",
    "UKOIL":  "UKOILm",
    "EURUSD": "EURUSDm",
    "GBPUSD": "GBPUSDm",
    "USDJPY": "USDJPYm",
    "BTCUSD": "BTCUSDm",
}

# --- LOGGING ---
LOG_FILE = "bot_activity.log"
