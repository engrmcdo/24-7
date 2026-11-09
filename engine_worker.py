def fetch_live_pse_quote(ticker: str, meta: dict) -> tuple[float, str]:
    sym = meta["sym"]
    timestamp_str = datetime.now(PHT).strftime("%Y-%m-%d %I:%M:%S %p PHT")
    
    # Direct Yahoo Finance query
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}.PS?interval=1d&range=1d"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            if price and float(price) > 0:
                return round(float(price), 2), timestamp_str
    except Exception as e:
        print(f"[YF FAILED] {sym}: {e}")

    # Explicit alert that live price could not be fetched
    print(f"[WARNING] Using stale fallback for {sym}: {meta['last_price']}")
    return meta["last_price"], timestamp_str
