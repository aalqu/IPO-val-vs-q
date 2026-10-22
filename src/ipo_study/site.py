"""Build a single self-contained web page (site/index.html) from the study's results.
No external scripts, fonts or trackers: upload the `site/` folder to any web host."""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from .cli import ROBUSTNESS
from .study import Config, headline, run

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path(__file__).with_name("site_template.html")


def _r(v, nd=1):
    return None if v is None else round(v * 100, nd)


def _deal_rows(R, universe):
    hot = set(R["heat_cutoffs"]["hot_ids"])
    out = []
    for r in R["_deal_results"]:
        d = r.deal
        out.append({"id": d.id, "name": d.name, "region": d.region, "listed": d.ipo_date[:7], "cohort": d.cohort,
                    "type": d.listing_type, "sector": d.sector, "mcap": d.mcap_usd_bn, "u": universe,
                    "ah": (d.extra or {}).get("dual_ah", "") if universe == "asia" else "",
                    "ps": None if d.ps is None else round(d.ps, 1), "profitable": d.profitable, "hot": d.id in hot,
                    "prem": _r(r.entry_prem), "o12": _r(r.xs("offer", 12)), "o36": _r(r.xs("offer", 36)),
                    "a36": _r(r.xs("after", 36))})
    return out


def _rules(R):
    Q, T = R["quant"], R["traditional"]
    rules = [
        ("Flip allocation at first month-end", "Quant rule", "1 month", Q["flip_allocation_first_month"]),
        ("Short hottest third of deals", "Quant rule", "3 years", Q["hot_fade"]["h36"]["short_hot"]),
        ("Short the new-issue basket", "Quant rule", "3 years", Q["short_basket"]["h36"]),
        ("Short post-lock-up losers", "Quant rule", "6 months", Q["post_lockup_momentum"]["m6_to_m12"]["short_losers"]),
        ("Short across lock-up expiry", "Quant rule", "2 months", Q["short_lockup_window_m5_m7"]),
        ("Wait for lock-up, then buy", "Quant rule", "1 year", Q["wait_for_lockup"]["buy_m6_hold_12m"]),
        ("Profitable at IPO, buy at offer", "Traditional", "3 years", T["profitable"]["h36"]),
        ("Buy every IPO at offer", "Traditional", "3 years", T["buy_every_ipo"]["h36"]),
        ("Cheap on P/S, buy at offer", "Traditional", "3 years", T["cheap_ps"]["h36"]),
        ("Buy at first month-end", "Traditional", "3 years", R["horizons"][36]["from_first_month_end"]),
    ]
    return [{"rule": a, "family": b, "horizon": c, "n": s["n"], "mean": _r(s["mean"]), "median": _r(s["median"]),
             "hit": _r(s["hit"], 0)} for a, b, c, s in rules if s]


def _rob_row(name, cfg):
    hh = headline(run(cfg))
    return {"variant": name, "n": hh["n_deals"], "prem": _r(hh["entry_premium_median"], 0),
            "after12": _r(hh["after_median_12m"], 0), "after36": _r(hh["after_median_36m"], 0),
            "beat36": _r(hh["after_hit_36m"], 0), "offer36": _r(hh["offer_median_36m"], 0),
            "hot_mean": _r(hh["short_hot_mean_36m"], 0), "hot_hit": _r(hh["short_hot_hit_36m"], 0),
            "rho": None if hh["spearman_ps_36m"] is None else round(hh["spearman_ps_36m"], 2)}


ASIA_ROBUSTNESS = [
    ("All Asia ($5bn+, 2010-2025)", Config(universe="asia")),
    ("Korea", Config(universe="asia", regions=("Korea",))),
    ("India", Config(universe="asia", regions=("India",))),
    ("Hong Kong", Config(universe="asia", regions=("HK",))),
    ("China A-shares", Config(universe="asia", regions=("ChinaA",))),
    ("Very large only ($10bn+)", Config(universe="asia", min_mcap_usd_bn=10)),
    ("Excluding the 2020-21 boom", Config(universe="asia", exclude_cohorts=("2020-21",))),
    ("First half only: 2010-2018 listings", Config(universe="asia", to_year=2018)),
    ("Second half only: 2019-2025 listings", Config(universe="asia", from_year=2019)),
]


def _valuation(universe):
    try:
        from .valuation_study import TRADITIONAL_RULES, run_valuation
        V = run_valuation(Config(universe=universe))
        vdeals = []
        for x in V["_rows"]:
            v, m, I = x["val"], x["val"]["multiples"], x["ind"]
            vdeals.append({"id": x["id"], "name": x["name"], "industry": x["industry"], "region": x["result"].deal.region,
                           "ev_ebitda": m["ev_ebitda"], "ind_ev_ebitda": I.ev_ebitda, "ev_sales": m["ev_sales"], "ind_ev_sales": I.ev_sales,
                           "pe": m["pe"], "ind_pe": I.pe, "dy": m["div_yield"], "ind_dy": I.div_yield, "pbv": m["pbv"], "ind_pbv": I.pbv,
                           "comps_gap": v["comps_gap"], "dcf_gap": v["dcf_gap"],
                           "buys": [k for k, rule in TRADITIONAL_RULES.items() if rule(x)],
                           "xs36": x["result"].xs("offer", 36), "xs12": x["result"].xs("offer", 12)})
        sig = {k: {h: (t[h]["rank_corr_from_offer"] or {}).get("rho") for h in t} for k, t in V["signal_tests"].items()}
        return {"deals_valued": V["deals_valued"], "comparison": V["comparison"], "problems": V["problems"],
                "deals": vdeals, "signal": sig, "median_gap": V["median_gap"]}
    except Exception as e:      # missing industry/fundamental data: the page says the section is pending
        return {"deals_valued": 0, "comparison": [], "problems": [str(e)]}


def build(repo_url: str = "https://github.com/aalqu/IPO-val-vs-q") -> Path:
    R = run(Config())
    h = headline(R)
    deals = _deal_rows(R, "core")
    hz = []
    for k, lab in ((6, "6 months"), (12, "1 year"), (36, "3 years")):
        for key, entry in (("from_offer", "Bought at offer price"), ("from_first_month_end", "Bought at first month-end")):
            s = R["horizons"][k][key]
            hz.append({"horizon": lab, "entry": entry, "n": s["n"], "median": _r(s["median"], 2), "hit": _r(s["hit"], 0)})
    rules = _rules(R)
    rob = [_rob_row(name, cfg) for name, cfg in ROBUSTNESS if not cfg.verified_only]
    valuation = _valuation("core")
    asia = None
    if (ROOT / "data" / "deals_asia.csv").exists():
        RA = run(Config(universe="asia"))
        deals += _deal_rows(RA, "asia")
        asia = {"headline": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in headline(RA).items()},
                "rules": _rules(RA), "markets": [_rob_row(n, c) for n, c in ASIA_ROBUSTNESS],
                "valuation": _valuation("asia")}
    payload = {"valuation": valuation, "headline": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in h.items()},
               "deals": deals, "horizons": hz, "rules": rules, "robustness": rob, "asia": asia, "repo": repo_url,
               "version": __import__("ipo_study").__version__, "snapshot": "2026-10-19"}
    html = TEMPLATE.read_text().replace("/*__DATA__*/null", json.dumps(payload, separators=(",", ":")))
    html = html.replace("__REPO__", repo_url)
    out = ROOT / "site"
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html)
    for f in ("deals.csv", "prices.csv", "benchmarks.csv", "corrections.csv", "corporate_actions.csv",
              "deals_asia.csv", "prices_asia.csv", "benchmarks_asia.csv", "fundamentals.csv", "fundamentals_asia.csv"):
        if (ROOT / "data" / f).exists():
            shutil.copy(ROOT / "data" / f, out / "data" / f)
    for f in ("deal_returns.csv", "asia/deal_returns.csv"):
        if (ROOT / "results" / f).exists():
            shutil.copy(ROOT / "results" / f, out / "data" / f.replace("/", "_"))
    return out / "index.html"


def pdf(out_path: Path | None = None) -> Path:
    """Print the page to PDF with a headless browser (pip install playwright; playwright install chromium)."""
    from playwright.sync_api import sync_playwright
    html = build()
    out_path = out_path or ROOT / "reports" / "ipo-valuation-vs-quant.pdf"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page(viewport={"width": 1000, "height": 1400}, color_scheme="light")
        p.goto(html.resolve().as_uri())
        p.wait_for_timeout(300)
        p.emulate_media(media="print")
        p.evaluate("window.dispatchEvent(new Event('resize'))")
        p.wait_for_timeout(300)
        p.pdf(path=str(out_path), format="A4", print_background=True,
              margin={"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"},
              display_header_footer=True, header_template="<span></span>",
              footer_template="<div style='font-size:8px;width:100%;text-align:center;color:#777'>"
                              "Large-cap IPOs: valuation vs quant · page <span class='pageNumber'></span> of <span class='totalPages'></span></div>")
        b.close()
    return out_path
