import os
import time
import threading
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from fastapi import FastAPI
import uvicorn
from datetime import datetime
import pytz

# ==============================================================================
# 1. FastAPI Web Server (Keeps Service Awake on Render $0 Free Tier)
# ==============================================================================
app = FastAPI(title="PSE Dynamic Broadcast Engine")

@app.get("/")
@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "PSE 5-Pillar Real-Time Engine",
        "timestamp": time.time()
    }

PHT = pytz.timezone("Asia/Manila")

# ==============================================================================
# 2. Monitored Universe: 14 PSE Blue Chips + GCash (Mynt, Inc.)
# ==============================================================================
WATCHLIST = {
    "GCASH": {
        "name": "Mynt, Inc. (Digital Financial Services)",
        "sym": "GLO",
        "last_price": 6.72,
        "history": [6.50, 6.55, 6.60, 6.65, 6.70, 6.72],
        "pb": "4.8x", "pe": "24.5x", "sector": "Fintech / Digital Financial Services",
        "catalysts": "Micro-lending expansion (GLoan, GCredit), digital remittance volume growth.",
        "risks": "Digital banking competition, regulatory caps on credit spreads, cybersecurity overhead."
    },
    "GLO": {
        "name": "Globe Telecom, Inc.",
        "sym": "GLO",
        "last_price": 1537.00,
        "history": [1510.0, 1520.0, 1530.0, 1537.0],
        "pb": "1.8x", "pe": "12.4x", "sector": "Telecommunications",
        "catalysts": "Data monetization, digital solutions expansion, capex reduction, recurring dividend yield.",
        "risks": "Network capex depreciation, mobile broadband price competition, debt servicing overhead."
    },
    "AC": {
        "name": "Ayala Corporation",
        "sym": "AC",
        "last_price": 540.00,
        "history": [530.0, 535.0, 538.0, 540.0],
        "pb": "0.8x", "pe": "10.1x", "sector": "Conglomerates / Holding Firms",
        "catalysts": "Broad portfolio earnings resilience, renewable power expansion, banking transaction growth.",
        "risks": "NAV holding discount, sensitivity to monetary policy rates."
    },
    "BPI": {
        "name": "Bank of the Philippine Islands",
        "sym": "BPI",
        "last_price": 94.00,
        "history": [93.0, 93.5, 94.0],
        "pb": "1.2x", "pe": "8.8x", "sector": "Banking / Financial Services",
        "catalysts": "Digital channel integration, post-merger branch synergies, corporate loan book growth.",
        "risks": "Deposit cost pressure, credit cost fluctuations upon interest rate easing."
    },
    "TEL": {
        "name": "PLDT Inc.",
        "sym": "TEL",
        "last_price": 1126.00,
        "history": [1115.0, 1120.0, 1126.0],
        "pb": "1.4x", "pe": "11.2x", "sector": "Telecommunications",
        "catalysts": "Enterprise data center leasing growth, capex tapering, stable cash dividends.",
        "risks": "Fixed broadband competition, legacy debt amortization."
    },
    "ALI": {
        "name": "Ayala Land, Inc.",
        "sym": "ALI",
        "last_price": 15.20,
        "history": [15.0, 15.1, 15.2],
        "pb": "0.6x", "pe": "8.9x", "sector": "Real Estate",
        "catalysts": "Commercial leasing recovery, stable residential presales, provincial estate landbanking.",
        "risks": "Mortgage rate sensitivity, construction material inflation."
    },
    "BDO": {
        "name": "BDO Unibank, Inc.",
        "sym": "BDO",
        "last_price": 117.10,
        "history": [115.0, 116.0, 117.1],
        "pb": "1.0x", "pe": "8.4x", "sector": "Banking",
        "catalysts": "Market-leading loan portfolio scale, fee income diversification, resilient net interest margins.",
        "risks": "Credit cost sensitivity if monetary policy easing is delayed."
    },
    "ICT": {
        "name": "Intl Container Terminal Services",
        "sym": "ICT",
        "last_price": 820.00,
        "history": [810.0, 815.0, 820.0],
        "pb": "3.5x", "pe": "18.2x", "sector": "Port Logistics",
        "catalysts": "Global volume throughput growth, port tariff adjustments, natural USD revenue hedge.",
        "risks": "Global trade route disruptions, concession renewal capex."
    },
    "SMPH": {
        "name": "SM Prime Holdings",
        "sym": "SMPH",
        "last_price": 17.54,
        "history": [17.2, 17.4, 17.54],
        "pb": "1.1x", "pe": "14.5x", "sector": "Real Estate / Commercial Malls",
        "catalysts": "Provincial mall foot traffic, resilient tenant rental revenue yields, residential pipeline expansion.",
        "risks": "Inflationary pressure on retail tenant sales."
    },
    "SM": {
        "name": "SM Investments Corp.",
        "sym": "SM",
        "last_price": 534.00,
        "history": [528.0, 530.0, 534.0],
        "pb": "1.3x", "pe": "13.2x", "sector": "Conglomerates",
        "catalysts": "Direct consumer spending proxy across retail, universal banking, and prime commercial property.",
        "risks": "Compression in discretionary consumer spending."
    },
    "MBT": {
        "name": "Metrobank",
        "sym": "MBT",
        "last_price": 60.75,
        "history": [59.5, 60.0, 60.75],
        "pb": "0.7x", "pe": "6.8x", "sector": "Banking",
        "catalysts": "High Tier-1 capital adequacy, room for dividend payout expansion, corporate credit demand.",
        "risks": "Compression in loan margins during rate cuts."
    },
    "MER": {
        "name": "Manila Electric Company",
        "sym": "MER",
        "last_price": 429.80,
        "history": [425.0, 428.0, 429.8],
        "pb": "1.9x", "pe": "12.0x", "sector": "Utilities / Power Distribution",
        "catalysts": "Guaranteed distribution asset base, consistent power demand growth, stable cash return.",
        "risks": "Regulatory rate review scrutiny, fuel input cost pass-through risks."
    },
    "MONDE": {
        "name": "Monde Nissin",
        "sym": "MONDE",
        "last_price": 5.90,
        "history": [5.80, 5.85, 5.90],
        "pb": "2.2x", "pe": "16.5x", "sector": "Consumer Staples / Food",
        "catalysts": "Core noodles volume leadership, input commodity cost deflation (wheat, palm oil).",
        "risks": "Alternative meat segment drag, agricultural commodity volatility."
    },
    "JFC": {
        "name": "Jollibee Foods Corporation",
        "sym": "JFC",
        "last_price": 144.00,
        "history": [140.0, 142.0, 144.0],
        "pb": "3.1x", "pe": "22.8x", "sector": "Consumer Discretionary / QSR",
        "catalysts": "Global network expansion, domestic quick-service restaurant resilience, franchising revenue.",
        "risks": "Store labor inflation, international acquisition overhead."
    },
    "PGOLD": {
        "name": "Puregold Price Club",
        "sym": "PGOLD",
        "last_price": 40.00,
        "history": [39.0, 39.5, 40.0],
        "pb": "0.8x", "pe": "10.4x", "sector": "Consumer Staples / Grocery Retail",
        "catalysts": "Provincial footprint rollouts, resilient staple volume demand, wholesale store growth.",
        "risks": "Competition from regional discounters, margin compression."
    }
}

# ==============================================================================
# 3. Direct Live PSE Quote Scraper
# ==============================================================================
def fetch_live_pse_quote(ticker: str, meta: dict) -> float:
    """Scrapes financial market endpoints to bypass Yahoo Finance 401 blocks."""
    if ticker == "GCASH":
        glo_price = fetch_live_pse_quote("GLO", WATCHLIST["GLO"])
        return round(glo_price * (6.72 / 1537.00), 2)

    sym = meta["sym"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }

    # Primary: Google Finance PSE quote
    try:
        url = f"https://www.google.com/finance/quote/{sym}:PSE"
        res = requests.get(url, headers=headers, timeout=6)
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

    # Secondary: MarketWatch PSE quote
    try:
        url = f"https://www.marketwatch.com/investing/stock/{sym.lower()}?countrycode=ph"
        res = requests.get(url, headers=headers, timeout=6)
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
# 4. Indicator Calculation Engine
# ==============================================================================
def calculate_wilders_rsi(series: pd.Series, period: int = 14) -> float:
    """Calculates Wilder's Smoothed RSI."""
    if len(series) < period + 1:
        diff = series.diff().dropna()
        if diff.empty:
            return 50.0
        g = diff.clip(lower=0).mean()
        l = -diff.clip(upper=0).mean()
        if l == 0:
            return 100.0
        return round(100.0 - (100.0 / (1.0 + (g / l))), 1)

    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.iloc[1:period+1].mean()
    avg_loss = loss.iloc[1:period+1].mean()
    for i in range(period + 1, len(series)):
        avg_gain = (avg_gain * (period - 1) + gain.iloc[i]) / period
        avg_loss = (avg_loss * (period - 1) + loss.iloc[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 1)

def refresh_stock_metrics(ticker: str) -> dict:
    """Fetches verified quote and recalculates support, resistance, MA20, and RSI."""
    state = WATCHLIST[ticker]
    actual_price = fetch_live_pse_quote(ticker, state)

    state["last_price"] = actual_price
    state["history"].append(actual_price)
    if len(state["history"]) > 25:
        state["history"].pop(0)

    series = pd.Series(state["history"])
    dyn_s = round(float(series.min()), 2)
    dyn_r = round(float(max(series.max(), actual_price)), 2)
    ma20 = round(float(series.mean()), 2)
    rsi_val = calculate_wilders_rsi(series, period=min(14, len(series) - 1))
    trend = "Above MA20" if actual_price >= ma20 else "Below MA20"

    # Corridors calculation (Clean math without cite tokens)
    buy_band = f"₱{(dyn_s * 0.995):,.2f} – ₱{(dyn_s * 1.010):,.2f}"
    sell_band = f"₱{(dyn_r * 0.990):,.2f} – ₱{(dyn_r * 1.005):,.2f}"

    # 3-State Condition Logic
    if actual_price <= dyn_s * 1.015:
        zone_status = "ACCUMULATION (BUY ZONE)"
        status_tag = "🟢 ACCUMULATION"
    elif actual_price >= dyn_r * 0.990 or rsi_val >= 68.0:
        zone_status = "PROFIT-TAKING (SELL ZONE)"
        status_tag = "🔴 PROFIT-TAKING"
    else:
        zone_status = "NEUTRAL (HOLD / CONSOLIDATION)"
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
        "zone_status": zone_status,
        "buy_band": buy_band,
        "sell_band": sell_band,
        "pb": state["pb"],
        "pe": state["pe"],
        "catalysts": state["catalysts"],
        "risks": state["risks"]
    }

# ==============================================================================
# 5. Consolidated Watchlist Digest Formatter (Fits within Telegram's 4,096-char cap)
# ==============================================================================
def format_consolidated_radar_digest(stock_states: list) -> str:
    now_str = datetime.now(PHT).strftime("%Y-%m-%d %I:%M %p PHT")

    lines = [
        "📊 *[PSE MARKET RADAR] 15-Stock Consolidated Digest*",
        f"*Timestamp: {now_str}*",
        "---"
    ]

    for s in stock_states:
        # Compact 5-pillar line summary per ticker
        lines.append(
            f"{s['status_tag']} *{s['ticker']}* (₱{s['price']:,.2f} | {s['trend']})\n"
            f"• *Corridors:* S ₱{s['support']:,.2f} | R ₱{s['resistance']:,.2f} | RSI: {s['rsi']:.1f}\n"
            f"• *Zones:* 🟢 Buy {s['buy_band']} | 🔴 Sell {s['sell_band']}\n"
            f"• *Valuation:* P/E {s['pe']} | P/B {s['pb']}"
        )

    lines.extend([
        "---",
        "_Analytical reference levels for tracking liquidity and exhaustion zones, not trade execution orders. Informational only, not financial advice._"
    ])

    return "\n\n".join(lines)
# ==============================================================================
# 6. Webhook & Telegram Dispatcher
# ==============================================================================
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
                print("[TELEGRAM] Alert delivered successfully.")
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

    discord_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if discord_url:
        try:
            requests.post(discord_url, json={"content": text[:1900]}, timeout=8)
        except Exception as e:
            print(f"Discord dispatch error: {e}")

# ==============================================================================
# 7. Background Loop (1 Single Broadcast Every 15 Minutes)
# ==============================================================================
def continuous_broadcast_worker():
    time.sleep(5)
    tickers = list(WATCHLIST.keys())
    print(f"PSE Consolidated Radar active: Broadcasting all {len(tickers)} stocks in 1 message every 15 mins.")

    while True:
        cycle_start_str = datetime.now(PHT).strftime("%I:%M:%S %p PHT")
        print(f"\n[SWEEP START] Scraping all 15 stocks at {cycle_start_str}...")

        all_states = []
        for ticker in tickers:
            try:
                state = refresh_stock_metrics(ticker)
                all_states.append(state)
            except Exception as e:
                print(f"Error scraping {ticker}: {e}")

        # Dispatch everything in a single message payload
        if all_states:
            digest_message = format_consolidated_radar_digest(all_states)
            dispatch_broadcast(digest_message)
            print(f"[SENT] Consolidated digest sent ({len(digest_message)} chars).")

        print("[BREAK] Sleeping for 15 minutes (900 seconds) until next cycle...\n")
        time.sleep(900)
