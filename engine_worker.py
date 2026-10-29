import os
import time
import threading
import requests
import pandas as pd
import yfinance as yf
from fastapi import FastAPI
import uvicorn
from google import genai

# ==============================================================================
# 1. FastAPI HTTP Server (Qualifies for Render $0 Free Web Service)
# ==============================================================================
app = FastAPI(title="PSE Stock Engine Health Check")

@app.get("/")
@app.get("/health")
def health_check():
    return {
        "status": "online",
        "service": "PSE Stock Analyst & Insight Engine",
        "timestamp": time.time()
    }

# ==============================================================================
# 2. 5-Pillar Analytical Guidance (gem.json Architecture)
# ==============================================================================
SYSTEM_PROMPT = """
You are the Stock Analysis & Insight Engine. Your purpose is to analyze stocks using both 
technical indicators and fundamental data to help users understand market behavior, 
identify potential buy/sell corridors, and review analyst-style background information. 
You do not give financial advice or tell users what to buy or sell.

Follow this 5-Pillar Analytical Structure rigorously for every evaluation:

1. Technical Chart Analysis
- Identify key dynamic support and resistance price floors and ceilings.
- Analyze moving average trend alignment (20-day, 50-day, 200-day).
- Evaluate momentum and volatility: 14-period Wilder RSI, MACD signal crosses, volume trends, and Bollinger Bands / ATR.
- State explicitly that levels are analytical reference points, not purchase or sell instructions.

2. Fundamental Profile & Valuation Anchor
- Provide a concise analyst-style operational background: core business model and primary operating segments.
- Summarize revenue trajectory, operating margins, leverage profile (debt-to-equity), and cash flow sustainability.
- Evaluate valuation multiples (P/E, P/B, EV/EBITDA, PEG) relative to industry peers and historical medians.
- Highlight recent operational catalysts and key macroeconomic or competitive risks.

3. Suggested Price Ranges (Analytical Corridors)
- Suggest data-based price bands:
  * Suggested Accumulation Zone (Buy Band): Formulated near historical support floors or valuation troughs.
  * Suggested Profit-Taking Zone (Sell Band): Formulated near key overhead resistance ceilings or valuation extensions.
- Always frame these as data-driven quantitative insights, never execution directives.

4. Analyst-Style Commentary
- Emulate the synthesis of an equity research analyst:
  * Assess prevailing institutional market sentiment.
  * Integrate macroeconomic factors (e.g., central bank policy, domestic inflation, consumer spending).
  * Compare relative performance against sector peers.
  * Highlight upcoming earnings or regulatory catalysts alongside structural risks.

5. Safety & Mandatory Educational Disclaimer
- Strictly avoid telling users to buy, sell, or hold specific securities.
- Avoid predicting guaranteed returns or absolute price targets.
- Include the mandatory educational statement reminding users that insights are for analytical tracking and that they should consult a licensed financial advisor.
"""

# ==============================================================================
# 3. Monitored Watchlist: 14 PSE Blue Chips + GCash
# ==============================================================================
WATCHLIST = {
    "GCASH": {
        "name": "Mynt, Inc. (Digital Financial Services)",
        "yf_sym": "GLO.PS",
        "current_price": 6.72,
        "support": 5.95,
        "resistance": 6.76,
        "rsi": 54.2,
        "pb": "4.8x",
        "pe": "24.5x",
        "sector": "Fintech / Digital Financial Services",
        "catalysts": "Micro-lending expansion (GLoan, GCredit), remittance ubiquity, non-collateralized loan margins.",
        "risks": "Deposit competition from digital-only banks, regulatory caps on credit spreads, cybersecurity overhead."
    },
    "GLO": {
        "name": "Globe Telecom, Inc.",
        "yf_sym": "GLO.PS",
        "current_price": 1537.00,
        "support": 1450.00,
        "resistance": 1650.00,
        "rsi": 46.8,
        "pb": "1.8x",
        "pe": "12.4x",
        "sector": "Telecommunications",
        "catalysts": "Data monetization, digital solutions expansion, capex tapering, recurring dividend yield.",
        "risks": "Network capex depreciation, mobile broadband price competition, debt servicing requirements."
    },
    "AC": {
        "name": "Ayala Corporation",
        "yf_sym": "AC.PS",
        "current_price": 540.00,
        "support": 520.00,
        "resistance": 590.00,
        "rsi": 51.8,
        "pb": "0.8x",
        "pe": "10.1x",
        "sector": "Conglomerates / Holding Firms",
        "catalysts": "Broad portfolio earnings resilience, renewable power capacity additions, banking fee growth.",
        "risks": "Holding company net asset value discount, macroeconomic interest rate sensitivity."
    },
    "BPI": {
        "name": "Bank of the Philippine Islands",
        "yf_sym": "BPI.PS",
        "current_price": 94.00,
        "support": 92.00,
        "resistance": 110.00,
        "rsi": 46.9,
        "pb": "1.2x",
        "pe": "8.8x",
        "sector": "Banking / Financial Services",
        "catalysts": "Digital channel integration, post-merger branch synergies, commercial credit expansion.",
        "risks": "Deposit funding cost pressure, credit cost fluctuations upon rate-cycle shifts."
    },
    "TEL": {
        "name": "PLDT Inc.",
        "yf_sym": "TEL.PS",
        "current_price": 1126.00,
        "support": 1110.00,
        "resistance": 1250.00,
        "rsi": 48.2,
        "pb": "1.4x",
        "pe": "11.2x",
        "sector": "Telecommunications",
        "catalysts": "Enterprise data center colocation leasing, capex tapering, consistent dividend yields.",
        "risks": "Broadband market competition, legacy debt amortization."
    },
    "ALI": {
        "name": "Ayala Land, Inc.",
        "yf_sym": "ALI.PS",
        "current_price": 15.20,
        "support": 14.80,
        "resistance": 17.50,
        "rsi": 53.4,
        "pb": "0.6x",
        "pe": "8.9x",
        "sector": "Real Estate",
        "catalysts": "Commercial leasing recovery, stable residential presales volume, provincial estate landbanking.",
        "risks": "Mortgage rate sensitivity, construction material inflation."
    },
    "BDO": {
        "name": "BDO Unibank, Inc.",
        "yf_sym": "BDO.PS",
        "current_price": 117.10,
        "support": 110.00,
        "resistance": 125.00,
        "rsi": 57.2,
        "pb": "1.0x",
        "pe": "8.4x",
        "sector": "Banking",
        "catalysts": "Market-leading loan portfolio scale, fee income diversification, resilient net interest margins.",
        "risks": "Credit cost sensitivity if monetary policy easing is delayed."
    },
    "ICT": {
        "name": "Intl Container Terminal Services",
        "yf_sym": "ICT.PS",
        "current_price": 820.00,
        "support": 800.00,
        "resistance": 890.00,
        "rsi": 45.9,
        "pb": "3.5x",
        "pe": "18.2x",
        "sector": "Port Logistics",
        "catalysts": "Global volume throughput growth, port tariff adjustments, natural USD revenue hedge.",
        "risks": "Global trade route disruptions, concession renewal capex."
    },
    "SMPH": {
        "name": "SM Prime Holdings",
        "yf_sym": "SMPH.PS",
        "current_price": 17.54,
        "support": 15.40,
        "resistance": 18.50,
        "rsi": 55.1,
        "pb": "1.1x",
        "pe": "14.5x",
        "sector": "Real Estate / Commercial Malls",
        "catalysts": "Provincial mall foot traffic, resilient tenant rental revenue yields, residential pipeline expansion.",
        "risks": "Inflationary pressure on retail tenant sales."
    },
    "SM": {
        "name": "SM Investments Corp.",
        "yf_sym": "SM.PS",
        "current_price": 534.00,
        "support": 510.00,
        "resistance": 580.00,
        "rsi": 50.7,
        "pb": "1.3x",
        "pe": "13.2x",
        "sector": "Conglomerates",
        "catalysts": "Direct consumer spending proxy across retail, universal banking, and prime commercial property.",
        "risks": "Compression in discretionary consumer spending."
    },
    "MBT": {
        "name": "Metrobank",
        "yf_sym": "MBT.PS",
        "current_price": 60.75,
        "support": 58.00,
        "resistance": 66.00,
        "rsi": 45.1,
        "pb": "0.7x",
        "pe": "6.8x",
        "sector": "Banking",
        "catalysts": "High Tier-1 capital adequacy, room for dividend payout expansion, corporate credit demand.",
        "risks": "Compression in loan margins during rate cuts."
    },
    "MER": {
        "name": "Manila Electric Company",
        "yf_sym": "MER.PS",
        "current_price": 429.80,
        "support": 410.00,
        "resistance": 450.00,
        "rsi": 44.8,
        "pb": "1.9x",
        "pe": "12.0x",
        "sector": "Utilities / Power Distribution",
        "catalysts": "Guaranteed distribution asset base, consistent power demand growth, stable cash return.",
        "risks": "Regulatory rate review scrutiny, fuel input cost pass-through risks."
    },
    "MONDE": {
        "name": "Monde Nissin",
        "yf_sym": "MONDE.PS",
        "current_price": 5.90,
        "support": 5.75,
        "resistance": 7.20,
        "rsi": 37.2,
        "pb": "2.2x",
        "pe": "16.5x",
        "sector": "Consumer Staples / Food",
        "catalysts": "Core noodles volume leadership, input commodity cost deflation (wheat, palm oil).",
        "risks": "Alternative meat segment drag, agricultural commodity volatility."
    },
    "JFC": {
        "name": "Jollibee Foods Corporation",
        "yf_sym": "JFC.PS",
        "current_price": 144.00,
        "support": 135.00,
        "resistance": 160.00,
        "rsi": 51.4,
        "pb": "3.1x",
        "pe": "22.8x",
        "sector": "Consumer Discretionary / QSR",
        "catalysts": "Global network expansion, domestic quick-service restaurant resilience, franchising revenue.",
        "risks": "Store labor inflation, international acquisition overhead."
    },
    "PGOLD": {
        "name": "Puregold Price Club",
        "yf_sym": "PGOLD.PS",
        "current_price": 40.00,
        "support": 36.00,
        "resistance": 42.00,
        "rsi": 50.9,
        "pb": "0.8x",
        "pe": "10.4x",
        "sector": "Consumer Staples / Grocery Retail",
        "catalysts": "Provincial footprint rollouts, resilient staple volume demand, wholesale store growth.",
        "risks": "Competition from regional discounters, margin compression."
    }
}

# ==============================================================================
# 4. Engine Worker Core
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

def fetch_stock_snapshot(ticker: str, meta: dict) -> dict:
    base_p = meta["current_price"]
    dyn_s = meta["support"]
    dyn_r = meta["resistance"]
    rsi_val = meta["rsi"]
    ma20 = (dyn_s + dyn_r) / 2
    ma50 = dyn_s * 1.02

    if ticker != "GCASH":
        try:
            t = yf.Ticker(meta["yf_sym"])
            df = t.history(period="3mo", interval="1d")
            if not df.empty and len(df) >= 15:
                closes = df["Close"]
                highs = df["High"]
                lows = df["Low"]
                base_p = round(float(closes.iloc[-1]), 2)
                dyn_s = round(float(lows.tail(20).min()), 2)
                dyn_r = round(float(max(highs.tail(20).max(), base_p)), 2)
                rsi_val = calculate_wilders_rsi(closes, period=14)
                ma20 = round(float(closes.tail(20).mean()), 2)
                if len(closes) >= 50:
                    ma50 = round(float(closes.tail(50).mean()), 2)
        except Exception:
            pass

    trend = "Above MA20" if base_p >= ma20 else "Below MA20"
    buy_band = f"₱{(dyn_s * 0.995):,.2f} – ₱{(dyn_s * 1.010):,.2f}"
    sell_band = f"₱{(dyn_r * 0.990):,.2f} – ₱{(dyn_r * 1.005):,.2f}"

    if base_p <= dyn_s * 1.015:
        zone_status = "ACCUMULATION"
    elif base_p >= dyn_r * 0.990:
        zone_status = "PROFIT_TAKING"
    else:
        zone_status = "NEUTRAL"

    return {
        "ticker": ticker,
        "name": meta["name"],
        "sector": meta["sector"],
        "price": base_p,
        "support": dyn_s,
        "resistance": dyn_r,
        "rsi": rsi_val,
        "ma20": ma20,
        "ma50": ma50,
        "trend": trend,
        "zone_status": zone_status,
        "buy_band": buy_band,
        "sell_band": sell_band,
        "pe": meta["pe"],
        "pb": meta["pb"],
        "catalysts": meta["catalysts"],
        "risks": meta["risks"]
    }

def generate_gemini_5pillar_brief(client: genai.Client, snapshot: dict) -> str:
    prompt = f"""
    Perform a complete 5-pillar stock analysis based on the following verified data snapshot:

    Ticker: {snapshot['ticker']} ({snapshot['name']})
    Sector: {snapshot['sector']}
    Current Market Price: ₱{snapshot['price']:,.2f}
    Dynamic Support Floor (S): ₱{snapshot['support']:,.2f}
    Dynamic Resistance Ceiling (R): ₱{snapshot['resistance']:,.2f}
    Wilder RSI (14D): {snapshot['rsi']}
    20-Day Moving Average: ₱{snapshot['ma20']:,.2f} ({snapshot['trend']})
    50-Day Moving Average: ₱{snapshot['ma50']:,.2f}
    Zone Status: {snapshot['zone_status']}
    Suggested Accumulation Zone: {snapshot['buy_band']}
    Suggested Profit-Taking Zone: {snapshot['sell_band']}
    Valuation Multiples: P/E {snapshot['pe']}, P/B {snapshot['pb']}
    Key Catalysts: {snapshot['catalysts']}
    Operational & Macro Risks: {snapshot['risks']}

    Generate a structured, professional analyst update covering:
    1. Technical Chart Analysis (Support, resistance, MA positioning, RSI momentum)
    2. Fundamental Profile & Valuation Anchor (Business segments, multiples, catalysts, risks)
    3. Suggested Price Ranges (Explicitly state Accumulation and Profit-Taking zones as analytical corridors)
    4. Analyst-Style Commentary (Institutional market context and reasoning)
    5. Safety & Educational Disclaimer (Explicit non-recommendation statement)
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"system_instruction": SYSTEM_PROMPT}
    )
    return response.text

def dispatch_notification(webhook_url: str, text: str):
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80 + "\n")

    if webhook_url:
        chunks = [text[i:i+1900] for i in range(0, len(text), 1900)]
        for chunk in chunks:
            try:
                requests.post(webhook_url, json={"content": chunk}, timeout=5)
            except Exception as e:
                print(f"Failed to post to webhook: {e}")

# ==============================================================================
# 5. Background Thread Execution Loop
# ==============================================================================
def background_scanner_loop():
    time.sleep(5)  # Wait for web server to bind
    api_key = os.environ.get("GEMINI_API_KEY")
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not api_key:
        print("[WARNING] GEMINI_API_KEY is not set. Worker thread paused.")
        return

    client = genai.Client(api_key=api_key)
    tickers = list(WATCHLIST.keys())
    idx = 0
    print(f"Background Stock Scanner started across {len(tickers)} stocks.")

    while True:
        target_ticker = tickers[idx % len(tickers)]
        meta = WATCHLIST[target_ticker]

        try:
            snapshot = fetch_stock_snapshot(target_ticker, meta)
            analysis = generate_gemini_5pillar_brief(client, snapshot)
            dispatch_notification(webhook_url, analysis)
        except Exception as e:
            print(f"Error evaluating {target_ticker}: {e}")

        idx += 1
        time.sleep(60)  # Evaluate one stock per minute

# ==============================================================================
# 6. Entrypoint: Start Scanner Thread & Run HTTP Server
# ==============================================================================
if __name__ == "__main__":
    # Launch stock scanner in a background daemon thread
    scanner_thread = threading.Thread(target=background_scanner_loop, daemon=True)
    scanner_thread.start()

    # Bind HTTP server to the port provided by Render (defaults to 8080)
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
