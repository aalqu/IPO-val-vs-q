"""Monthly prices from Yahoo Finance's chart API, saved raw in data/raw/yahoo/ and turned into the
study's price format. Yahoo's monthly 'close' is split-adjusted; the unadjusted close is rebuilt by
undoing later splits (Yahoo reports bonus issues as splits)."""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .data import DATA_DIR, month_index

RAW = DATA_DIR / "raw" / "yahoo"
UA = {"User-Agent": "Mozilla/5.0 (ipo-valuation-vs-quant replication)"}


def download(tickers, period1=1230768000, period2=1793000000) -> list[str]:
    RAW.mkdir(parents=True, exist_ok=True)
    failed = []
    for t in tickers:
        dest = RAW / f"{t}.json"
        if dest.exists():
            continue
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?interval=1mo"
               f"&period1={period1}&period2={period2}&events=div%2Csplit")
        try:
            d = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read())
            if d["chart"]["result"]:
                dest.write_text(json.dumps(d))
            else:
                failed.append(t)
        except Exception:
            failed.append(t)
        time.sleep(0.25)
    return failed


def monthly(t: str) -> dict:
    """{month_index: (adj_close, unadjusted_close)} plus meta, from the saved raw file."""
    d = json.loads((RAW / f"{t}.json").read_text())["chart"]["result"][0]
    ts = d.get("timestamp") or []
    q = d["indicators"]["quote"][0]
    adj = d["indicators"].get("adjclose", [{}])[0].get("adjclose") or q["close"]
    tz = d["meta"].get("gmtoffset", 0)
    splits = sorted(((int(s["date"]), s["numerator"] / s["denominator"])
                     for s in (d.get("events", {}).get("splits", {}) or {}).values()), key=lambda x: x[0])
    out = {}
    for i, t0 in enumerate(ts):
        c, a = q["close"][i], adj[i]
        if c is None or a is None:
            continue
        m = month_index(datetime.fromtimestamp(t0 + tz, tz=timezone.utc).strftime("%Y-%m"))
        later = 1.0
        for sd, f in splits:
            if month_index(datetime.fromtimestamp(sd, tz=timezone.utc).strftime("%Y-%m")) > m:
                later *= f
        out[m] = (float(a), float(c) * later)
    first = d["meta"].get("firstTradeDate")
    return {"prices": out, "first_trade": datetime.fromtimestamp(first, tz=timezone.utc).strftime("%Y-%m-%d") if first else None,
            "currency": d["meta"].get("currency")}
