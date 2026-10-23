"""Rebuild data/prices.csv and data/benchmarks.csv for the US + global study from the saved
Yahoo Finance responses in data/raw/yahoo/. Tickers Yahoo no longer serves (delisted or
acquired companies) keep their rows from the digrin.com snapshot (data/raw/digrin_*.txt),
marked source=digrin.com. Bars dated before the listing month are dropped (Yahoo shows
pre-listing bars for a few issuers, e.g. ALLY). No value is estimated: a month missing from both
sources is simply absent."""
from __future__ import annotations

import csv

from .data import DATA_DIR, load_deals, month_index, month_label
from .yahoo import RAW, monthly

LATEST = "2026-10"


def build() -> list[str]:
    deals = load_deals(DATA_DIR / "deals.csv")
    old = list(csv.DictReader(open(DATA_DIR / "prices.csv", newline="", encoding="utf-8")))
    rows, log = [], []
    first = {}
    for d in deals:
        first[d.ticker] = min(first.get(d.ticker, 10**6), month_index(d.ipo_date))
    for t in sorted({d.ticker for d in deals}):
        if (RAW / f"{t}.json").exists():
            for m, (adj, close) in sorted(monthly(t)["prices"].items()):
                if first[t] <= m <= month_index(LATEST):     # bars before the listing month are not trading prices
                    rows.append({"ticker": t, "month": month_label(m), "adj_close": f"{adj:.6g}", "close": f"{close:.6g}",
                                 "source": "yahoo", "note": ""})
        else:
            kept = [r for r in old if r["ticker"] == t and r["source"].startswith("digrin")]
            rows += kept
            log.append(f"{t}: not served by Yahoo; {len(kept)} digrin.com rows kept")
    with open(DATA_DIR / "prices.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "month", "adj_close", "close", "source", "note"])
        w.writeheader()
        w.writerows(rows)
    spy, acwi = monthly("SPY")["prices"], monthly("ACWI")["prices"]
    with open(DATA_DIR / "benchmarks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["month", "spy_adj_close", "acwi_adj_close", "source"])
        for m in range(month_index("2010-01"), month_index(LATEST) + 1):
            w.writerow([month_label(m), f"{spy[m][0]:.6g}" if m in spy else "", f"{acwi[m][0]:.6g}" if m in acwi else "",
                        "yahoo (SPY, ACWI adjusted close)"])
    return log
