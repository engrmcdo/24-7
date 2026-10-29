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
        "catalysts":
