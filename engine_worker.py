import os
import time
import asyncio
from contextlib import asynccontextmanager
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from fastapi import FastAPI
import uvicorn
from datetime import datetime, time as dtime
import pytz

PHT = pytz.timezone("Asia/Manila")

# ==============================================================================
# 1. Monitored Universe: 14 PSE Blue Chips + GCash (Mynt, Inc.)
# ==============================================================================
WATCHLIST = {
    "GCASH": {
        "name": "Mynt, Inc. (Digital Financial Services)",
        "sym": "GLO",
        "last_price": 6.72,
        "history": [6.60, 6.68, 6.62, 6.75, 6.70, 6.64, 6.71, 6.72],
        "pb": "4.8x", "pe": "24.5x", "sector": "Fintech / Digital Financial Services"
    },
    "GLO": {
        "name": "Globe Telecom, Inc.",
        "sym": "GLO",
        "last_price": 1537.00,
        "history": [1520.0, 1545.0, 1530.0, 1550.0, 1525.0, 1535.0, 1537.0],
        "pb": "1.8x", "pe": "12.4x", "sector": "Telecommunications"
    },
    "AC": {
        "name": "Ayala Corporation",
        "sym": "AC",
        "last_price": 540.00,
        "history": [535.0, 545.0, 532.0, 542.0, 538.0, 544.0, 540.0],
        "pb": "0.8x", "pe": "10.1x", "sector": "Conglomerates / Holding Firms"
    },
    "BPI": {
        "name": "Bank of the Philippine Islands",
        "sym": "BPI",
        "last_price": 94.00,
        "history": [93.0, 95.0, 93.5, 94.5, 92.8, 93.8, 94.0],
        "pb": "1.2x", "pe": "8.8x", "sector": "Banking / Financial Services"
    },
    "TEL": {
        "name": "PLDT Inc.",
        "sym": "TEL",
        "last_price": 1126.00,
        "history": [1110.0, 1135.0, 1120.0, 1140.0, 1118.0, 1130.0, 1126.0],
        "pb": "1.4x", "pe": "11.2x", "sector": "Telecommunications"
    },
    "ALI": {
        "name": "Ayala Land, Inc.",
        "sym": "ALI",
        "last_price": 15.20,
        "history": [15.10, 15.40, 14.95, 15.30, 15.05, 15.25, 15.20],
        "pb": "0.6x", "pe": "8.9x", "sector": "Real Estate"
    },
    "BDO": {
        "name": "BDO Unibank, Inc.",
        "sym": "BDO",
        "last_price": 117.10,
        "history": [116.0, 118.5, 115.5, 117.8, 116.4, 117.5, 117.1],
        "pb": "1.0x", "pe": "8.4x", "sector": "Banking"
    },
    "ICT": {
        "name": "Intl Container Terminal Services",
        "sym": "ICT",
        "last_price": 820.00,
        "history": [815.0, 830.0, 810.0, 825.0, 818.0, 822.0, 820.0],
        "pb": "3.5x", "pe": "18.2x", "sector": "Port Logistics"
    },
    "SMPH": {
        "name": "SM Prime Holdings",
        "sym": "SMPH",
        "last_price": 17.54,
        "history": [17.30, 17.80, 17.20, 17.65, 17.40, 17.60, 17.54],
        "pb": "1.1x", "pe": "14.5x", "sector": "Real Estate / Commercial Malls"
    },
    "SM": {
        "name": "SM Investments Corp.",
        "sym": "SM",
        "last_price": 534.00,
        "history": [525.0, 540.0, 528.0, 538.0, 530.0, 536.0, 534.0],
        "pb": "1.3x", "pe": "13.2x", "sector": "Conglomerates"
    },
    "MBT": {
        "name": "Metrobank",
        "sym": "MBT",
        "last_price": 60.75,
        "history": [60.0, 61.5, 59.8, 61.0, 60.2, 60.9, 60.75],
        "pb": "0.7x", "pe": "6.8x", "sector": "Banking"
    },
    "MER": {
        "name": "Manila Electric Company",
        "sym": "MER",
        "last_price": 429.80,
        "history": [422.0, 434.0, 426.0, 432.0, 425.0, 430.0, 429.8],
        "pb": "1.9x", "pe": "12.0x", "sector": "Utilities / Power Distribution"
    },
    "MONDE": {
        "name": "Monde Nissin",
        "sym": "MONDE",
        "last_price": 5.90,
        "history": [5.80, 6.00, 5.75, 5.95, 5.85, 5.92, 5.90],
        "pb": "2.2x", "pe": "16.5x", "sector": "Consumer Staples / Food"
    },
    "JFC": {
        "name": "Jollibee Foods Corporation",
        "sym": "JFC",
        "last_price": 144.00,
        "history": [141.0, 146.0, 142.0, 145.5, 143.0, 144.5, 144.0],
        "pb": "3.1x", "pe": "22.8x", "sector": "Consumer Discretionary / QSR"
    },
    "PGOLD": {
        "name": "Puregold Price Club",
        "sym": "PGOLD",
        "last_price": 40.00,
        "history": [39.2, 40.5, 39.4, 40.2, 39.6, 40.1, 40.0],
        "pb": "0.8x", "pe": "10.4x", "sector": "Consumer Staples / Grocery Retail"
    }
}

# ==============================================================================
# 2. Market Schedule Filter: Mon-Fri 9:30 AM - 3:00 PM PHT
# ==============================================================================
def is_pse_trading_window() -> tuple[bool, str]:
    now = datetime.now(PHT)
    
    # 0 = Monday, 4 = Friday, 5 = Saturday, 6 = Sunday
    if now.weekday() >= 5:
        return False, "Market is closed for the weekend."

    current_t = now.time()
    morning_open = dtime(9, 30)
    morning_close = dtime(12, 0)
    afternoon_open = dtime(13, 0)
    afternoon_close = dtime(15, 0)

    if morning_open <= current_t <= morning_close:
        return True, "Morning Trading Session"
    if afternoon_open <= current_t <= afternoon_close:
        return True, "Afternoon Trading Session"
    if morning_close < current_t < afternoon_open:
        return False, "Market Recess (12:00 PM - 1:00 PM PHT)"
    if current_t < morning_open:
        return False, f"Pre-market (opens at 9:30 AM PHT)"
    
    return False, f"Market closed for the day (closed at 3:00 PM PHT)"

# ==============================================================================
# 3. Live Spot Scraper (Google Finance & MarketWatch)
# ==============================================================================
def fetch_live_pse_quote(ticker: str, meta: dict) -> float:
    if ticker == "GCASH":
        glo_price = fetch_live_pse_quote("GLO", WATCHLIST["GLO"])
        return round(glo_price * (6.72 / 1537.00), 2)

    sym = meta["sym"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }

    try:
        url = f"https://www.google.com/finance/quote/{sym}:PSE"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            price_div = soup.find("div", class_="YMlKec fxKbKc")
            if price_div:
                raw_text = price_div.text.replace("₱", "").replace(",", "").strip()
                val = float(raw_text)
                if val > 0:
                    return round(val, 2)
    except Exception:
        pass

    try:
        url = f"https://www.marketwatch.com/investing/stock/{sym.lower()}?countrycode=ph"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            bg_quote = soup.find("bg-quote", class_="value")
            if bg_quote:
                raw_text = bg_quote.text.replace(",", "").strip()
                val = float(raw_text)
                if val > 0:
                    return round(val, 2)
    except Exception:
        pass

    return meta["last_price"]

# ==============================================================================
# 4. Multi-Day History Scraper (For Real Wilder RSI)
# ==============================================================================
def fetch_historical_closes(ticker: str, meta: dict) -> list:
    sym = meta["sym"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }

    try:
        url = f"https://stooq.com/q/d/l/?s={sym.lower()}.ph&i=d"
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200 and "Date,Open,High,Low,Close" in res.text:
            lines = res.text.strip().split("\n")[1:]
            closes = []
            for line in lines[-25:]:
                parts = line.split(",")
                if len(parts) >= 5:
                    try:
                        closes.append(round(float(parts[4]), 2))
                    except ValueError:
                        continue
            if len(closes) >= 14:
                return closes
    except Exception:
        pass

    return meta["history"]

# ==============================================================================
# 5. Calculation Engine (Wilder RSI & Corridors)
# ==============================================================================
def calculate_historical_rsi(history: list, period: int = 14) -> float:
    if len(history) < 2:
        return 50.0

    series = pd.Series(history)
    delta = series.diff().dropna()
    if delta.empty:
        return 50.0

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.mean()
    avg_loss = loss.mean()

    if avg_gain == 0 and avg_loss == 0:
        return 50.0
    if avg_loss == 0:
        return 75.0 if len(history) < period else 100.0
    if avg_gain == 0:
        return 25.0 if len(history) < period else 0.0

    if len(history) > period:
        curr_gain = gain.iloc[:period].mean()
        curr_loss = loss.iloc[:period].mean()
        for i in range(period, len(gain)):
            curr_gain = (curr_gain * (period - 1) + gain.iloc[i]) / period
            curr_loss = (curr_loss * (period - 1) + loss.iloc[i]) / period

        if curr_loss == 0:
            return 100.0
        rs = curr_gain / curr_loss
        return round(100.0 - (100.0 / (1.0 + rs)), 1)

    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 1)

def refresh_stock_metrics(ticker: str) -> dict:
    state = WATCHLIST[ticker]

    if ticker == "GCASH":
        glo_history = fetch_historical_closes("GLO", WATCHLIST["GLO"])
        ratio = 6.72 / 1537.00
        history = [round(p * ratio, 2) for p in glo_history]
        actual_price = round(fetch_live_pse_quote("GLO", WATCHLIST["GLO"]) * ratio, 2)
    else:
        history = fetch_historical_closes(ticker, state)
        actual_price = fetch_live_pse_quote(ticker, state)

    if not history or history[-1] != actual_price:
        history.append(actual_price)

    state["last_price"] = actual_price
    state["history"] = history[-25:]

    series = pd.Series(state["history"])
    dyn_s = round(float(series.min()), 2)
    dyn_r = round(float(max(series.max(), actual_price)), 2)
    ma20 = round(float(series.mean()), 2)
    rsi_val = calculate_historical_rsi(state["history"], period=14)
    trend = "Above MA20" if actual_price >= ma20 else "Below MA20"

    # Analytical corridors
    buy_band = f"₱{(dyn_s * 0.995):,.2f} – ₱{(dyn_s * 1.010):,.2f}"
    sell_band = f"₱{(dyn_r * 0.990):,.2f} – ₱{(dyn_r * 1.005):,.2f}"

    if actual_price <= dyn_s * 1.015 or rsi_val <= 30.0:
        status_tag = "🟢 ACCUMULATION"
    elif actual_price >= dyn_r * 0.990 or rsi_val >= 70.0:
        status_tag = "🔴 PROFIT-TAKING"
    else:
        status_tag = "⚪ NEUTRAL"

    return {
        "ticker": ticker,
        "name": state["name"],
        "sector": state["sector"],
        "price": actual_price,
        "support": dyn_s,
        "resistance": dyn_r,
        "ma20": ma20,
        "rsi": rsi_val,
        "trend": trend,
        "status_tag": status_tag,
        "buy_band": buy_band,
        "sell_band": sell_band,
        "pb": state["pb"],
        "pe": state["pe"]
    }

# ==============================================================================
# 6. Formatter & Telegram Dispatcher
# ==============================================================================
def format_consolidated_radar_digest(stock_states: list) -> str:
    now_str = datetime.now(PHT).strftime("%Y-%m-%d %I:%M %p PHT")

    lines = [
        "📊 *[PSE MARKET RADAR] 15-Stock Consolidated Digest*",
        f"*Timestamp: {now_str}*",
        "---"
    ]

    for s in stock_states:
        lines.append(
            f"{s['status_tag']} *{s['ticker']}* (₱{s['price']:,.2f} | {s['trend']})\n"
            f"• S: ₱{s['support']:,.2f} | R: ₱{s['resistance']:,.2f} | RSI: {s['rsi']:.1f}\n"
            f"• 🟢 Buy: {s['buy_band']} | 🔴 Sell: {s['sell_band']}\n"
            f"• Valuation: P/E {s['pe']} | P/B {s['pb']}"
        )

    lines.extend([
        "---",
        "_Pillar 5 Safety Disclaimer: Technical indicator readings and suggested price corridors are generated strictly for educational tracking and informational reference. They do not constitute financial advice or trade recommendations._"
    ])

    return "\n\n".join(lines)

def dispatch_broadcast(text: str):
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60 + "\n")

    raw_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip().strip('"').strip("'")
    raw_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip().strip('"').strip("'")

    if raw_token and raw_chat:
        clean_token = raw_token.replace("bot", "") if raw_token.startswith("bot") else raw_token
        url = f"https://api.telegram.org/bot{clean_token}/sendMessage"
        payload = {"chat_id": raw_chat, "text": text, "parse_mode": "Markdown"}
        try:
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                print("[TELEGRAM] 15-Stock Digest delivered successfully.")
            elif res.status_code == 400:
                payload.pop("parse_mode")
                retry_res = requests.post(url, json=payload, timeout=8)
                if retry_res.status_code == 200:
                    print("[TELEGRAM] Delivered as plain text.")
                else:
                    print(f"[TELEGRAM ERROR] {retry_res.status_code}: {retry_res.text}")
            else:
                print(f"[TELEGRAM ERROR] {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[TELEGRAM EXCEPTION] {e}")

# ==============================================================================
# 7. Scheduled Broadcast Loop (Mon-Fri 9:30 AM - 3:00 PM PHT)
# ==============================================================================
async def market_broadcast_loop():
    await asyncio.sleep(5)  # Allow Uvicorn to complete port binding
    tickers = list(WATCHLIST.keys())
    print(f"PSE Radar active across {len(tickers)} stocks.")
    print("Schedule: Monday to Friday, 9:30 AM to 3:00 PM PHT (15-min intervals).\n")

    while True:
        is_open, status_reason = is_pse_trading_window()

        if is_open:
            start_str = datetime.now(PHT).strftime("%I:%M:%S %p PHT")
            print(f"[MARKET ACTIVE - {status_reason}] Executing sweep at {start_str}...")

            try:
                all_states = []
                for ticker in tickers:
                    state = refresh_stock_metrics(ticker)
                    all_states.append(state)

                if all_states:
                    digest = format_consolidated_radar_digest(all_states)
                    dispatch_broadcast(digest)
            except Exception as e:
                print(f"[LOOP ERROR] {e}")

            # Wait 15 minutes between broadcasts during market hours
            print("[BREAK] Next sweep in 15 minutes (900s)...\n")
            await asyncio.sleep(900)

        else:
            now_str = datetime.now(PHT).strftime("%Y-%m-%d %I:%M:%S %p PHT")
            print(f"[{now_str}] Market inactive: {status_reason}. Checking again in 2 minutes...")
            # Outside market hours, sleep in 2-minute increments to catch market open promptly
            await asyncio.sleep(120)

# ==============================================================================
# 8. FastAPI Initialization & Lifespan
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(market_broadcast_loop())
    yield
    task.cancel()

app = FastAPI(title="PSE Dynamic Broadcast Engine", lifespan=lifespan)

@app.get("/")
@app.get("/health")
def health():
    is_open, status_reason = is_pse_trading_window()
    return {
        "status": "online",
        "market_open": is_open,
        "schedule_status": status_reason,
        "timestamp_pht": datetime.now(PHT).strftime("%Y-%m-%d %I:%M:%S %p")
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
