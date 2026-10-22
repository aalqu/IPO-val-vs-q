"""Does the traditional valuation at the offer predict what happened next?

For each deal with filled-in fundamentals: value it with comps and the standard DCF
(`valuation.py`), then test whether IPOs priced below fair value ("cheap") beat those priced
above it, and set that against the quant rules on the same deals.
"""
from __future__ import annotations

import csv
import statistics as st

from .data import DATA_DIR, VALUATION_FILES
from .metrics import spearman, summarize
from .study import Config, run
from .valuation import DCFRules, Industry, load_fundamentals, value_deal


def load_benchmarks_table():
    path = DATA_DIR / "industry_benchmarks.csv"
    if not path.exists():
        return {}
    out = {}
    for r in csv.DictReader(open(path, newline="")):
        out[(r["region"], int(r["file_year"]), r["industry"].strip().lower())] = r
    return out


def load_riskfree():
    path = DATA_DIR / "riskfree.csv"
    if not path.exists():
        return {}
    return {int(r["year"]): float(r["riskfree"]) for r in csv.DictReader(open(path, newline=""))}


def _num(r, k):
    v = (r.get(k) or "").strip()
    return float(v) if v else None


MAX_INDUSTRY_PE = 500     # an aggregate P/E above this means industry earnings are near zero: not usable


def _pe(v):
    return v if v is not None and 0 < v <= MAX_INDUSTRY_PE else None


def industry_for(deal_id, imap, table, rf):
    """Industry benchmarks for a deal: the mapped industry in the mapped region and year.

    For single-country regions (China, India) an industry with fewer than MIN_FIRMS firms in
    that country's file is taken from the Emerging-markets file instead, because a handful of
    firms gives meaningless aggregates (e.g. 2 soft-drink makers in China's 2019 file).
    """
    from .industry import FALLBACK_REGION, MIN_FIRMS
    m = imap[deal_id]
    region, year = m["benchmark_region"], int(m["benchmark_file_year"])
    names = [n for n in (m["industry"], m["alternative_industry"]) if n]
    tries = [(region, n) for n in names]
    if region in FALLBACK_REGION:
        # industry first, then region: the mapped industry in the country file (if it has enough
        # firms), else the same industry in the wider file; only then the alternative industry
        thin = lambda r: r is None or (_num(r, "n_firms") or 0) < MIN_FIRMS
        tries = []
        for n in names:
            if not thin(table.get((region, year, n.strip().lower()))):
                tries.append((region, n))
            tries.append((FALLBACK_REGION[region], n))
    for reg, name in tries:
        row = table.get((reg, year, name.strip().lower()))
        if row:
            mkt = table.get((reg, year, "total market")) or {}
            pct = lambda v: None if v is None else (v / 100 if v > 1.5 else v)    # some files store percents
            used = name if reg == region else f"{name} ({reg} file: under {MIN_FIRMS} {region} firms)"
            return Industry(name=row["industry"], ev_ebitda=_num(row, "ev_ebitda"), ev_sales=_num(row, "ev_sales"),
                            pe=_pe(_num(row, "pe")), pbv=_num(row, "pbv"), div_yield=pct(_num(row, "div_yield")),
                            wacc=pct(_num(row, "wacc")) or 0.08, op_margin=pct(_num(row, "op_margin")) or 0.10,
                            sales_to_capital=_num(row, "sales_to_capital") or 1.5,
                            market_wacc=pct(_num(mkt, "wacc")) or pct(_num(row, "wacc")) or 0.08,
                            riskfree=rf.get(year + 1, 0.03)), used
    raise KeyError(f"{deal_id}: no benchmark row for {region} {year} {m['industry']!r}")


def run_valuation(cfg: Config | None = None, rules: DCFRules | None = None) -> dict:
    cfg = cfg or Config()
    R = run(cfg)
    fund_file, map_file = VALUATION_FILES[cfg.universe]
    funds = load_fundamentals(DATA_DIR / fund_file)
    table = load_benchmarks_table()
    rf = load_riskfree()
    imap = {r["id"]: r for r in csv.DictReader(open(DATA_DIR / map_file, newline=""))}
    rows, problems = [], []
    for r in R["_deal_results"]:
        d = r.deal
        if d.id not in funds or d.id not in imap or d.listing_type != "IPO":
            continue
        try:
            ind, used = industry_for(d.id, imap, table, rf)
            v = value_deal(funds[d.id], ind, d.offer_price / d.price_unit_divisor, rules)
        except Exception as e:  # missing benchmark or bad inputs: reported, not hidden
            problems.append(f"{d.id}: {e}")
            continue
        rows.append({"id": d.id, "name": d.name, "industry": used, "ind": ind, "result": r, "val": v,
                     "financial": funds[d.id].financial})
    hot = set(R["heat_cutoffs"]["hot_ids"])
    return {"deals_valued": len(rows), "problems": problems, "_rows": rows,
            "comparison": compare_strategies(rows, hot),
            "signal_tests": {k: signal_test(rows, k) for k in ("comps_gap", "dcf_gap", "blended_gap")},
            "median_gap": {k: (st.median([x["val"][k] for x in rows if x["val"][k] is not None]) if rows else None)
                           for k in ("comps_gap", "dcf_gap", "blended_gap")}}


# ----------------------------------------------------------------------------------------
# Traditional valuation as investment rules, and the quant rules on the same deals
# ----------------------------------------------------------------------------------------
def _lt(a, b):
    return a is not None and b is not None and a < b


def _gt(a, b):
    return a is not None and b is not None and a > b


# Each traditional rule says "buy this IPO" when the valuation looks attractive at the offer.
TRADITIONAL_RULES = {
    "Dividend yield above industry": lambda x: _gt(x["val"]["multiples"]["div_yield"], x["ind"].div_yield),
    "P/E below industry": lambda x: _lt(x["val"]["multiples"]["pe"], x["ind"].pe),
    "EV/EBITDA below industry": lambda x: not x["financial"] and _lt(x["val"]["multiples"]["ev_ebitda"], x["ind"].ev_ebitda),
    "EV/Sales below industry": lambda x: not x["financial"] and _lt(x["val"]["multiples"]["ev_sales"], x["ind"].ev_sales),
    "P/B below industry (financials)": lambda x: x["financial"] and _lt(x["val"]["multiples"]["pbv"], x["ind"].pbv),
    "Comps value above offer": lambda x: _gt(x["val"]["comps_gap"], 0),
    "DCF value above offer": lambda x: _gt(x["val"]["dcf_gap"], 0),
    "Comps and DCF both above offer": lambda x: _gt(x["val"]["comps_gap"], 0) and _gt(x["val"]["dcf_gap"], 0),
}


def _perf(xs, kind, h, sign=1):
    return summarize([sign * v for x in xs if (v := (x["result"].xs(kind, h) if kind != "flip" else None)) is not None])


def compare_strategies(rows, hot_ids) -> list[dict]:
    """One row per (strategy, entry, horizon): trades, mean, median and hit rate of excess return.

    Traditional rules go long the IPOs they rate attractive, entering at the offer price
    (an allocation) or at the first month-end (an investor who buys on the market).
    Quant rules are run on exactly the same deals.
    """
    out = []

    def add(family, name, entry, h, s, note=""):
        if s:
            out.append({"family": family, "strategy": name, "entry": entry, "horizon_m": h, "trades": s["n"],
                        "mean": s["mean"], "median": s["median"], "hit": s["hit"], "t": s["t"], "note": note})

    for name, rule in TRADITIONAL_RULES.items():
        picked = [x for x in rows if rule(x)]
        for h in (6, 12, 36):
            add("Traditional", name, "offer", h, _perf(picked, "offer", h))
            add("Traditional", name, "first month-end", h, _perf(picked, "after", h))
    for h in (6, 12, 36):
        add("Benchmark", "Buy every IPO", "offer", h, _perf(rows, "offer", h))
        add("Benchmark", "Buy every IPO", "first month-end", h, _perf(rows, "after", h))
        hot = [x for x in rows if x["id"] in hot_ids]
        add("Quant", "Short hottest third", "first month-end", h, _perf(hot, "after", h, -1), "short")
        add("Quant", "Short new-issue basket", "first month-end", h, _perf(rows, "after", h, -1), "short")
    flips = summarize([x["result"].entry_prem for x in rows])
    add("Quant", "Flip allocation", "offer", 1, flips, "raw return, sold at first month-end")
    wait = summarize([x["result"].fwd_xs(6, 18) for x in rows])
    add("Quant", "Wait for lock-up, then buy", "month 6", 12, wait)
    return out


def signal_test(rows, gap_key) -> dict:
    """Does a bigger valuation gap (cheaper at the offer) go with better later returns?"""
    g = [x["val"][gap_key] for x in rows]
    return {f"h{h}": {"rank_corr_from_offer": spearman(g, [x["result"].xs("offer", h) for x in rows]),
                      "rank_corr_after_listing": spearman(g, [x["result"].xs("after", h) for x in rows])}
            for h in (6, 12, 36)}
