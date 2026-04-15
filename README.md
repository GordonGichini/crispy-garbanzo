# 📡 Telegram → MT5 Signal Bot

Automatically reads trading signals from a private Telegram channel and executes them on your MT5 account.

---

## ⚙️ Setup (Step-by-Step)

### 1. Install Python
Download and install Python 3.10+ from https://python.org
> ✅ During install, check **"Add Python to PATH"**

### 2. Install dependencies
Open a terminal / command prompt in this folder and run:
```bash
pip install -r requirements.txt
```

### 3. Get your Telegram API credentials (2 minutes)
1. Go to https://my.telegram.org
2. Log in with your phone number
3. Click **"API development tools"**
4. Create a new app (name doesn't matter)
5. Copy your **api_id** and **api_hash**

### 4. Configure the bot
Open `config.py` and fill in:

| Setting | What to put |
|---|---|
| `TELEGRAM_API_ID` | Your api_id from step 3 |
| `TELEGRAM_API_HASH` | Your api_hash from step 3 |
| `TELEGRAM_PHONE` | Your phone number e.g. `"+33612345678"` |
| `SOURCE_CHANNEL` | Username or ID of the signal channel |
| `PERSONAL_CHANNEL` | Your personal channel username or ID |
| `MT5_LOGIN` | Your MT5 account number |
| `MT5_PASSWORD` | Your MT5 password |
| `MT5_SERVER` | Your broker's server name |
| `RISK_PERCENT` | % of balance to risk per trade (e.g. `2.0`) |

### 5. Run the bot
```bash
python main.py
```

On first run, Telegram will ask you to confirm your phone number (one-time only).

---

## 🔁 How It Works

```
Private Signal Channel
        ↓
  Bot reads every new message
        ↓
  Signal validated? (has TP + SL?)
        ↓ NO → Skipped silently
        ↓ YES
  Price in entry range?
        ↓ NO → Cancelled, notification sent
        ↓ YES
  Lot size calculated (balance × risk%)
        ↓
  Market order placed on MT5
        ↓
  Result sent to your personal channel
```

---

## 📲 Notifications You Will Receive

- 🔍 Signal detected (with full details)
- ✅ Trade executed (entry, lot, TP, SL, ticket number)
- ⚠️ Trade cancelled (price moved out of range)
- ❌ Trade failed (with error reason)

---

## ⚙️ Settings Reference

| Setting | Options | Description |
|---|---|---|
| `RISK_PERCENT` | `1.0` / `2.0` / `3.0` | Risk per trade as % of balance |
| `TP_MODE` | `"final"` / `"all"` | Use last TP only, or split across all TPs |
| `MAX_SLIPPAGE` | `10` (default) | Max allowed price slippage in points |

---

## ⚠️ Important Notes

- The bot must run on a **Windows PC** (MT5 Python library is Windows-only)
- MT5 terminal must be **installed and running** when the bot starts
- Keep the terminal/CMD window open while the bot is running
- For 24/7 operation, run on a **Windows VPS**
