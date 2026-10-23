"""The study: per-deal returns, traditional valuation screens and quant rules.

Every number in the report is produced by `run()`. Returns are buy-and-hold total
returns (dividends and splits via adjusted closes), measured month-end to month-end.
Excess return = deal return minus benchmark return over the same months.
"""
from __future__ import annotations

import statistics as st
from dataclasses import dataclass, field

from .data import Deal, load_benchmarks, load_deals, load_prices, month_index
from .metrics import bootstrap_ci, spearman, summarize

HORIZONS = (5, 6, 7, 12, 18, 24, 36)   # months after the IPO month
LATEST = month_index("2026-10")         # price snapshot date


@dataclass
class Config:
    min_mcap_usd_bn: float = 5.0
    regions: tuple[str, ...] | None = None    # None = every region in the universe
    universe: str = "core"                     # "core" (US + global, v1) or "asia" (Korea, India, HK, China A)
    exclude_cohorts: tuple[str, ...] = ()
    exclude_ids: tuple[str, ...] = ()
    from_year: int = 2010
    to_year: int = 2025
    verified_only: bool = False
    bootstrap: int = 0                  # draws for confidence intervals; 0 = off
    seed: int = 7


@dataclass
class DealResult:
    deal: Deal
    entry_prem: float                   # first month-end close / offer - 1
    r_after: dict = field(default_factory=dict)   # h -> return from first month-end
    r_offer: dict = field(default_factory=dict)   # h -> return from offer price
    bench: dict = field(default_factory=dict)     # h -> benchmark return
    since: dict | None = None           # return to latest price, for deals still listed

    def xs(self, kind: str, h: int) -> float | None:
        r = (self.r_after if kind == "after" else self.r_offer).get(h)
        b = self.bench.get(h)
        return None if r is None or b is None else r - b

    def fwd_xs(self, a: int, b: int) -> float | None:
        """Excess return from month a to month b after listing."""
        if self.r_after.get(a) is None or self.r_after.get(b) is None:
            return None
        rr = (1 + self.r_after[b]) / (1 + self.r_after[a]) - 1
        bb = (1 + self.bench[b]) / (1 + self.bench[a]) - 1
        return rr - bb


def select(deals: list[Deal], cfg: Config) -> list[Deal]:
    return [d for d in deals
            if d.mcap_usd_bn >= cfg.min_mcap_usd_bn and (cfg.regions is None or d.region in cfg.regions)
            and d.cohort not in cfg.exclude_cohorts and d.id not in cfg.exclude_ids
            and cfg.from_year <= d.year <= cfg.to_year
            and (d.verified or not cfg.verified_only)]


def deal_returns(deals, prices, benches) -> list[DealResult]:
    out = []
    for d in deals:
        px = prices.get(d.ticker, {})
        m0 = d.ipo_month
        if m0 not in px:
            raise ValueError(f"{d.id}: no price for IPO month")
        bench = benches[d.region]
        a0, c0 = px[m0]
        offer = d.offer_price / d.price_unit_divisor
        entry_close = d.entry_close_override if d.entry_close_override else c0
        entry_mult = entry_close / offer           # offer -> first month-end
        res = DealResult(d, entry_mult - 1)
        for h in HORIZONS:
            k = m0 + h
            if k in px and k in bench and k <= LATEST:
                ra = px[k][0] / a0 - 1
                res.r_after[h] = ra
                res.r_offer[h] = entry_mult * (1 + ra) - 1
                res.bench[h] = bench[k] / bench[m0] - 1
        last = max(px)
        if last > m0 + 12 and last >= LATEST - 2 and last in bench:
            yrs = (last - m0) / 12
            tot = entry_mult * px[last][0] / a0
            btot = bench[last] / bench[m0]
            res.since = {"years": yrs, "ret": tot - 1, "bench": btot - 1,
                         "cagr": tot ** (1 / yrs) - 1, "bench_cagr": btot ** (1 / yrs) - 1}
        out.append(res)
    return out


def _s(values, cfg: Config, stat="median"):
    s = summarize(values)
    if s and cfg.bootstrap:
        s["ci95_" + stat] = bootstrap_ci(values, stat, cfg.bootstrap, cfg.seed)
        s["ci95_hit"] = bootstrap_ci(values, "hit", cfg.bootstrap, cfg.seed)
    return s


def run(cfg: Config | None = None, deals=None, prices=None, benches=None) -> dict:
    cfg = cfg or Config()
    if deals is None or prices is None:
        from .data import load_universe
        u_deals, u_prices = load_universe(cfg.universe)
        deals = deals if deals is not None else u_deals
        prices = prices if prices is not None else u_prices
    deals = select(deals, cfg)
    res = deal_returns(deals, prices, benches or load_benchmarks())
    ipo = [r for r in res if r.deal.listing_type == "IPO"]   # priced deals (offer price exists)
    R: dict = {"config": cfg.__dict__.copy(), "n_deals": len(res), "n_priced_ipos": len(ipo)}

    # ---- what happened ------------------------------------------------------------
    if not res:
        return {"config": cfg.__dict__.copy(), "n_deals": 0, "n_priced_ipos": 0, "empty": True}
    R["entry_premium"] = _s([r.entry_prem for r in ipo], cfg)
    R["horizons"] = {h: {"from_offer": _s([r.xs("offer", h) for r in ipo], cfg),
                         "from_first_month_end": _s([r.xs("after", h) for r in res], cfg)}
                     for h in (6, 12, 36)}
    R["by_region"] = {g: {h: {"from_offer": summarize([r.xs("offer", h) for r in ipo if r.deal.region == g]),
                              "from_first_month_end": summarize([r.xs("after", h) for r in res if r.deal.region == g])}
                          for h in (6, 12, 36)} for g in sorted({r.deal.region for r in res})}
    R["entry_premium_by_region"] = {g: summarize([r.entry_prem for r in ipo if r.deal.region == g]) for g in sorted({r.deal.region for r in res})}
    R["by_cohort"] = {c: {h: summarize([r.xs("after", h) for r in res if r.deal.cohort == c]) for h in (6, 12, 36)}
                      for c in ("2010-14", "2015-19", "2020-21", "2022-25")}
    lt = [r for r in res if r.since and r.since["years"] >= 5]
    R["since_listing_5y_plus"] = {
        "excess_cagr": summarize([r.since["cagr"] - r.since["bench_cagr"] for r in lt]),
        "beat": sorted(r.deal.id for r in lt if r.since["cagr"] > r.since["bench_cagr"])}
    for h in (6, 12, 36):
        pairs = [r for r in ipo if r.xs("offer", h) is not None]
        R.setdefault("below_offer_share", {})[h] = (sum(r.r_offer[h] < 0 for r in pairs) / len(pairs)) if pairs else None

    # ---- traditional valuation screens (buy at offer) -------------------------------
    ps = [r.deal.ps for r in ipo if r.deal.ps is not None]
    ps_med = st.median(ps) if ps else None
    R["ps_median"] = ps_med

    def screen(pred):
        sel = [r for r in ipo if pred(r.deal)]
        return {"ids": [r.deal.id for r in sel],
                **{f"h{h}": _s([r.xs("offer", h) for r in sel], cfg) for h in (6, 12, 36)}}
    cheap = lambda d: d.ps is not None and d.ps <= ps_med
    rich = lambda d: d.ps is not None and d.ps > ps_med
    R["traditional"] = {
        "buy_every_ipo": screen(lambda d: True),
        "profitable": screen(lambda d: d.profitable is True),
        "loss_making": screen(lambda d: d.profitable is False),
        "cheap_ps": screen(cheap),
        "expensive_ps": screen(rich),
        "profitable_and_cheap": screen(lambda d: d.profitable is True and cheap(d)),
        "loss_making_and_expensive": screen(lambda d: d.profitable is False and rich(d)),
    }
    R["spearman_ps_vs_offer_excess"] = {h: spearman([r.deal.ps for r in ipo], [r.xs("offer", h) for r in ipo]) for h in (6, 12, 36)}
    R["after_by_profitability"] = {flag: {h: summarize([r.xs("after", h) for r in res if r.deal.profitable == (flag == "profitable")])
                                          for h in (6, 12, 36)} for flag in ("profitable", "loss_making")}

    # ---- quant rules ----------------------------------------------------------------
    Q: dict = {}
    Q["flip_allocation_first_month"] = R["entry_premium"]
    Q["short_basket"] = {f"h{h}": _s([-x if (x := r.xs("after", h)) is not None else None for r in res], cfg) for h in (6, 12, 36)}
    by_prem = sorted(ipo, key=lambda r: r.entry_prem)
    k = len(by_prem) // 3
    cold, hot = by_prem[:k], by_prem[-k:]
    R["heat_cutoffs"] = {"cold_max": cold[-1].entry_prem if cold else None, "hot_min": hot[0].entry_prem if hot else None,
                         "hot_ids": [r.deal.id for r in hot], "cold_ids": [r.deal.id for r in cold]}
    Q["hot_fade"] = {}
    for h in (6, 12, 36):
        c = [r.xs("after", h) for r in cold if r.xs("after", h) is not None]
        hh = [r.xs("after", h) for r in hot if r.xs("after", h) is not None]
        Q["hot_fade"][f"h{h}"] = {"long_cold": _s(c, cfg), "short_hot": _s([-x for x in hh], cfg),
                                  "spread": (st.mean(c) - st.mean(hh)) if c and hh else None}
    Q["short_lockup_window_m5_m7"] = _s([-x if (x := r.fwd_xs(5, 7)) is not None else None for r in res], cfg)
    pool = sorted([r for r in res if r.r_offer.get(6) is not None], key=lambda r: r.r_offer[6])
    k6 = len(pool) // 3
    losers, winners = pool[:k6], pool[-k6:]
    Q["post_lockup_momentum"] = {}
    for b in (12, 18):
        w = [x for r in winners if (x := r.fwd_xs(6, b)) is not None]
        l = [x for r in losers if (x := r.fwd_xs(6, b)) is not None]
        Q["post_lockup_momentum"][f"m6_to_m{b}"] = {"long_winners": _s(w, cfg), "short_losers": _s([-x for x in l], cfg),
                                                    "spread": (st.mean(w) - st.mean(l)) if w and l else None}
    Q["wait_for_lockup"] = {"buy_m6_hold_12m": _s([r.fwd_xs(6, 18) for r in res], cfg),
                            "buy_m0_hold_12m": _s([r.xs("after", 12) for r in res], cfg)}
    R["quant"] = Q
    R["_deal_results"] = res
    return R


def headline(R: dict) -> dict:
    """The handful of numbers quoted in the report's verdict; used by the regression test."""
    if R.get("empty"):
        return {"n_deals": 0}
    g = lambda s, k: None if s is None else s[k]
    return {
        "n_deals": R["n_deals"],
        "entry_premium_median": g(R["entry_premium"], "median"),
        "entry_premium_hit": g(R["entry_premium"], "hit"),
        "after_median_6m": g(R["horizons"][6]["from_first_month_end"], "median"),
        "after_median_12m": g(R["horizons"][12]["from_first_month_end"], "median"),
        "after_median_36m": g(R["horizons"][36]["from_first_month_end"], "median"),
        "after_hit_36m": g(R["horizons"][36]["from_first_month_end"], "hit"),
        "offer_median_36m": g(R["horizons"][36]["from_offer"], "median"),
        "since_5y_excess_cagr_median": g(R["since_listing_5y_plus"]["excess_cagr"], "median"),
        "since_5y_beat_share": g(R["since_listing_5y_plus"]["excess_cagr"], "hit"),
        "profitable_median_36m": g(R["traditional"]["profitable"]["h36"], "median"),
        "loss_making_median_36m": g(R["traditional"]["loss_making"]["h36"], "median"),
        "spearman_ps_36m": g(R["spearman_ps_vs_offer_excess"][36], "rho"),
        "short_hot_mean_36m": g(R["quant"]["hot_fade"]["h36"]["short_hot"], "mean"),
        "short_hot_hit_36m": g(R["quant"]["hot_fade"]["h36"]["short_hot"], "hit"),
        "short_basket_hit_36m": g(R["quant"]["short_basket"]["h36"], "hit"),
        "wait_lockup_mean_12m": g(R["quant"]["wait_for_lockup"]["buy_m6_hold_12m"], "mean"),
    }
