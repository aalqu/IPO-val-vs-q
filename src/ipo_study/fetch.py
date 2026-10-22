"""Independent rebuild of the price data from Yahoo Finance, and a cross-check
against the published snapshot. Needs `pip install yfinance` and internet access.

Yahoo's 'Adj Close' is adjusted for splits and dividends, like the snapshot's
adjusted column, so returns (ratios of adjusted closes) are compared, not levels.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .data import DATA_DIR, load_deals, load_prices, month_index, month_label

# Snapshot ticker -> Yahoo symbol, where they differ. Acquired/delisted names are
# often missing on Yahoo; they are reported, not guessed.
YAHOO = {"META": "META", "DEWA.AE": "DEWA.AE", "TWTR": None, "WORK": None, "XM": None,
         "DIDI": "DIDIY", "HCP": None, "NLSN": None, "ZNGA": None, "SC": None}
BENCH = {"spy_adj_close": "SPY", "acwi_adj_close": "ACWI"}


def fetch(out_dir: Path) -> Path:
    import yfinance as yf  # optional dependency

    out_dir.mkdir(parents=True, exist_ok=True)
    rows, missing = [], []
    tickers = sorted({d.ticker for d in load_deals()})
    for t in tickers:
        sym = YAHOO.get(t, t)
        if sym is None:
            missing.append(t)
            continue
        df = yf.download(sym, start="2010-01-01", interval="1mo", auto_adjust=False, progress=False)
        if df is None or df.empty:
            missing.append(t)
            continue
        for ts, r in df.iterrows():
            adj = float(r["Adj Close"].iloc[0] if hasattr(r["Adj Close"], "iloc") else r["Adj Close"])
            cl = float(r["Close"].iloc[0] if hasattr(r["Close"], "iloc") else r["Close"])
            rows.append({"ticker": t, "month": ts.strftime("%Y-%m"), "adj_close": adj, "close": cl, "source": f"yahoo:{sym}"})
    path = out_dir / "prices_yahoo.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticker", "month", "adj_close", "close", "source"])
        w.writeheader()
        w.writerows(rows)
    bench = {}
    for col, sym in BENCH.items():
        df = yf.download(sym, start="2010-01-01", interval="1mo", auto_adjust=False, progress=False)
        for ts, r in df.iterrows():
            v = r["Adj Close"]
            bench.setdefault(ts.strftime("%Y-%m"), {})[col] = float(v.iloc[0] if hasattr(v, "iloc") else v)
    with open(out_dir / "benchmarks_yahoo.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "spy_adj_close", "acwi_adj_close", "source"])
        for m in sorted(bench):
            w.writerow([m, bench[m].get("spy_adj_close", ""), bench[m].get("acwi_adj_close", ""), "yahoo"])
    (out_dir / "missing_on_yahoo.txt").write_text("\n".join(missing) + "\n")
    return path


def crosscheck(yahoo_prices: Path, tolerance: float = 0.03) -> list[dict]:
    """Compare each deal's 6/12/36-month adjusted return between the snapshot and Yahoo."""
    snap = load_prices()
    alt = load_prices(yahoo_prices)
    report = []
    for d in load_deals():
        a, b = snap.get(d.ticker, {}), alt.get(d.ticker, {})
        m0 = d.ipo_month
        for h in (6, 12, 36):
            k = m0 + h
            if m0 in a and k in a and m0 in b and k in b:
                ra = a[k][0] / a[m0][0] - 1
                rb = b[k][0] / b[m0][0] - 1
                report.append({"id": d.id, "horizon_m": h, "from": month_label(m0), "to": month_label(k),
                               "snapshot": ra, "yahoo": rb, "diff": ra - rb, "flag": abs(ra - rb) > tolerance})
    return report
