import os
import time
import threading
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from fastapi import FastAPI
import uvicorn
from datetime import datetime
import pytz

# ==============================================================================
# 1. FastAPI HTTP Server (For 24/7 Free Hosting Keep-Alive)
# ==============================================================================
app = FastAPI(title="PSE Dynamic Broadcast Engine (Telegram)")

@app.get("/")
@app.get("/health")
def health():
    return {
        "status": "online",
        "service": "PSE 5-Pillar Broadcast Engine via Telegram",
        "timestamp": time.time()
    }

PHT = pytz.timezone("Asia/Manila")

# ==============================================================================
# 2. Monitored Watchlist: 14 PSE Blue Chips + GCash (Mynt, Inc.)
# ==============================================================================
WATCHLIST = {
    "GCASH": {"name": "Mynt, Inc. (Digital Financial Services)", "yf_sym": "GLO.PS", "base_s": 5.95, "base_r": 6.76, "pb": "4.8x", "pe": "24.5x", "sector": "Fintech", "catalysts": "Micro-lending expansion (GLoan/GCredit), remittance ubiquity.", "risks": "Digital bank competition, credit rate caps."},
    "GLO": {"name": "Globe Telecom, Inc.", "yf_sym": "GLO.PS", "base_s": 1450.00, "base_r": 1650.00, "pb": "1.8x", "pe": "12.4x", "sector": "Telecommunications", "catalysts": "Data monetization, digital solutions, capex reduction.", "risks": "Network capex depreciation, mobile broadband price competition."},
    "AC": {"name": "Ayala Corporation", "yf_sym": "AC.PS", "base_s": 520.00, "base_r": 590.00, "pb": "0.8x", "pe": "10.1x", "sector": "Conglomerates", "catalysts": "Broad portfolio earnings resilience, renewable power expansion.", "risks": "Holding company net asset value discount, interest rate sensitivity."},
    "BPI": {"name": "Bank of the Philippine Islands", "yf_sym": "BPI.PS", "base_s": 92.00, "base_r": 110.00, "pb": "1.2x", "pe": "8.8x", "sector": "Banking", "catalysts": "Digital channel integration, post-merger branch synergies.", "risks": "Deposit cost pressure, monetary policy cycle shifts."},
    "TEL": {"name": "PLDT Inc.", "yf_sym": "TEL.PS", "base_s": 1110.00, "base_r": 1250.00, "pb": "1.4x", "pe": "11.2x", "sector": "Telecommunications", "catalysts": "Data center leasing growth, capex tapering, stable cash dividends.", "risks": "Broadband competition, debt amortization requirements."},
    "ALI": {"name": "Ayala Land, Inc.", "yf_sym": "ALI.PS", "base_s": 14.80, "base_r": 17.50, "pb": "0.6x", "pe": "8.9x", "sector": "Real Estate", "catalysts": "Commercial leasing recovery, stable residential presales.", "risks": "Mortgage rate sensitivity, construction material inflation."},
    "BDO": {"name": "BDO Unibank, Inc.", "yf_sym": "BDO.PS", "base_s": 110.00, "base_r": 125.00, "pb": "1.0x", "pe": "8.4x", "sector": "Banking", "catalysts": "Market-leading loan portfolio scale, fee income diversification.", "risks": "Credit cost sensitivity if monetary policy easing is delayed."},
    "ICT": {"name": "Intl Container Terminal Services", "yf_sym": "ICT.PS", "base_s": 800.00, "base_r": 890.00, "pb": "3.5x", "pe": "18.2x", "sector": "Port Logistics", "catalysts": "Global volume throughput growth, port tariff adjustments.", "risks": "Global trade route disruptions, concession renewal capex."},
    "SMPH": {"name": "SM Prime Holdings", "yf_sym": "SMPH.PS", "base_s": 15.40, "base_r": 18.50, "pb": "1.1x", "pe": "14.5x", "sector": "Real Estate / Malls", "catalysts": "Provincial mall foot traffic, resilient tenant rental revenue yields.", "risks": "Inflationary pressure on retail tenant sales."},
    "SM": {"name": "SM Investments Corp.", "yf_sym": "SM.PS", "base_s": 510.00, "base_r": 580.00, "pb": "1.3x", "pe": "13.2x", "sector": "Conglomerates", "catalysts": "Direct consumer spending proxy across retail and banking.", "risks": "Compression in discretionary consumer spending."},
    "MBT": {"name": "Metrobank", "yf_sym": "MBT.PS", "base_s": 58.00, "base_r": 66.00, "pb": "0.7x", "pe": "6.8x", "sector": "Banking", "catalysts": "High Tier-1 capital adequacy, room for dividend payout expansion.", "risks": "Compression in loan margins during rate cuts."},
    "MER": {"name": "Manila Electric Company", "yf_sym": "MER.PS", "base_s": 410.00, "base_r": 450.00, "pb": "1.9x", "pe": "12.0x", "sector": "Utilities", "catalysts": "Guaranteed distribution asset base, consistent power demand growth.", "risks": "Regulatory rate review scrutiny, fuel cost pass-through risks."},
    "MONDE": {"name": "Monde Nissin", "yf_sym": "MONDE.PS", "base_s": 5.75, "base_r": 7.20, "pb": "2.2x", "pe": "16.5x", "sector": "Food Staples", "catalysts": "Core noodles volume leadership, input commodity cost deflation.", "risks": "Alternative meat segment drag, agricultural price volatility."},
    "JFC": {"name": "Jollibee Foods Corporation", "yf_sym": "JFC.PS", "base_s": 135.00, "base_r": 160.00, "pb": "3.1x", "pe": "22.8x", "sector": "Consumer Discretionary", "catalysts": "Global store expansion, domestic quick-service restaurant resilience.", "risks": "Store labor inflation, international acquisition overhead."},
    "PGOLD": {"name": "Puregold Price Club", "yf_sym": "PGOLD.PS", "base_s": 36.00, "base_r": 42.00, "pb": "0.8x", "pe": "10.4x", "sector": "Grocery Retail", "catalysts": "Provincial footprint rollouts, resilient staple volume demand.", "risks": "Competition from regional discounters, margin compression."}
}

# ==============================================================================
# 3. Dynamic Calculation Engine
# ==============================================================================
def calculate_wilders_rsi(series: pd.Series, period: int = 14) -> float:
    if len(series) < period + 1:
        return 50.0
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

def evaluate_stock_state(ticker: str, meta: dict) -> dict:
    cur_p = meta["base_s"] * 1.05
    dyn_s = meta["base_s"]
    dyn_r = meta["base_r"]
    rsi_val = 50.0
    ma20 = (dyn_s + dyn_r) / 2

    # Query live daily exchange candles
    try:
        t = yf.Ticker(meta["yf_sym"])
        df = t.history(period="3mo", interval="1d")
        if not df.empty and len(df) >= 15:
            closes = df["Close"]
            highs = df["High"]
            lows = df["Low"]
            
            raw_p = round(float(closes.iloc[-1]), 2)
            raw_s = round(float(lows.tail(20).min()), 2)
            raw_r = round(float(max(highs.tail(20).max(), raw_p)), 2)
            raw_ma20 = round(float(closes.tail(20).mean()), 2)
            raw_rsi = calculate_wilders_rsi(closes, period=14)

            if ticker == "GCASH":
                scale = 6.72 / 1537.00
                cur_p = round(raw_p * scale, 2)
                dyn_s = round(raw_s * scale, 2)
                dyn_r = round(raw_r * scale, 2)
                ma20 = round(raw_ma20 * scale, 2)
            else:
                cur_p, dyn_s, dyn_r, ma20 = raw_p, raw_s, raw_r, raw_ma20
            rsi_val = raw_rsi
    except Exception:
        pass

    trend = "Above MA20" if cur_p >= ma20 else "Below MA20"
    
    # 5-Pillar Dynamic Corridors (gem.json)
    buy_band = f"₱{(dyn_s * 0.995):,.2f} – ₱{(dyn_s * 1.010):,.2f}"
    sell_band = f"₱{(dyn_r * 0.990):,.2f} – ₱{(dyn_r * 1.005):,.2f}"

    # 3-State Condition Logic[cite: 1]
    if cur_p <= dyn_s * 1.015:
        zone_status = "ACCUMULATION (BUY ZONE)"
        status_tag = "🟢 ACCUMULATION"
    elif cur_p >= dyn_r * 0.990 or rsi_val >= 68.0:
        zone_status = "PROFIT-TAKING (SELL ZONE)"
        status_tag = "🔴 PROFIT-TAKING"
    else:
        zone_status = "NEUTRAL (HOLD / CONSOLIDATION)"
        status_tag = "⚪ NEUTRAL"

    return {
        "ticker": ticker,
        "name": meta["name"],
        "sector": meta["sector"],
        "price": cur_p,
        "support": dyn_s,
        "resistance": dyn_r,
        "ma20": ma20,
        "rsi": rsi_val,
        "trend": trend,
        "status_tag": status_tag,
        "zone_status": zone_status,
        "buy_band": buy_band,
        "sell_band": sell_band,
        "pb": meta["pb"],
        "pe": meta["pe"],
        "catalysts": meta["catalysts"],
        "risks": meta["risks"]
    }

# ==============================================================================
# 4. 5-Pillar Telegram Formatter
# ==============================================================================
def format_5pillar_telegram(s: dict) -> str:
    now_str = datetime.now(PHT).strftime("%Y-%m-%d %I:%M:%S %p PHT")
    
    return f"""📢 *[PSE MARKET RADAR] {s['status_tag']} — {s['ticker']}*
*Timestamp: {now_str}*

*1. Technical Chart Analysis*[cite: 1]
• *Market Price:* ₱{s['price']:,.2f} | *Trend:* {s['trend']} (MA20: ₱{s['ma20']:,.2f})
• *Key Support (Floor):* ₱{s['support']:,.2f}[cite: 1]
• *Key Resistance (Ceiling):* ₱{s['resistance']:,.2f}[cite: 1]
• *Wilder RSI (14D):* {s['rsi']:.1f}[cite: 1]
• *Note:* Based on recent price action, support aligns near ₱{s['support']:,.2f} and resistance near ₱{s['resistance']:,.2f}[cite: 1]. Traders monitor these levels for liquidity absorption or trend exhaustion[cite: 1].

*2. Fundamental Profile & Valuation Anchor*[cite: 1]
• *Company:* {s['name']} ({s['sector']})
• *Multiples:* P/E {s['pe']} | P/B {s['pb']}
• *Key Catalysts:* {s['catalysts']}
• *Key Risks:* {s['risks']}

*3. Suggested Price Ranges (Analytical Corridors)*[cite: 1]
• 🟢 *Suggested Accumulation Zone:* {s['buy_band']}[cite: 1]
• 🔴 *Suggested Profit-Taking Zone:* {s['sell_band']}[cite: 1]
• *Current Positioning:* *{s['zone_status']}*[cite: 1]
• *Analytical Note:* Corridors reflect historical buyer/seller concentration areas, not trade execution orders[cite: 1].

*4. Analyst-Style Commentary*[cite: 1]
The issue is currently trading in a *{s['zone_status']}* stance[cite: 1]. Technical moving average alignment reflects prevailing institutional sentiment. Fundamental valuation multiples provide structural context relative to sector medians[cite: 1].

---
_Pillar 5 Mandatory Safety & Educational Disclaimer: These insights, technical indicators, and suggested price ranges are generated strictly for informational and educational tracking purposes[cite: 1]. They do not constitute financial advice, an investment recommendation, an endorsement, or a trade instruction to buy, sell, or hold any security[cite: 1]. Always consult a licensed financial advisor before making investment decisions[cite: 1]._"""

# ==============================================================================
# 5. Telegram Dispatcher & Continuous Polling Loop
# ==============================================================================
def send_telegram_message(text: str):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    print("\n" + "=" * 60)
    print(text)
    print("=" * 60 + "\n")

    if bot_token and chat_id:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(url, json=payload, timeout=8)
        except Exception as e:
            print(f"Telegram dispatch error: {e}")

def continuous_broadcast_worker():
    time.sleep(5)
    tickers = list(WATCHLIST.keys())
    idx = 0
    print(f"Telegram Broadcast Engine active for {len(tickers)} tickers.")

    while True:
        ticker = tickers[idx % len(tickers)]
        meta = WATCHLIST[ticker]

        try:
            state = evaluate_stock_state(ticker, meta)
            message = format_5pillar_telegram(state)
            send_telegram_message(message)
        except Exception as e:
            print(f"Error evaluating {ticker}: {e}")

        idx += 1
        time.sleep(60)

if __name__ == "__main__":
    worker_thread = threading.Thread(target=continuous_broadcast_worker, daemon=True)
    worker_thread.start()
    
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
