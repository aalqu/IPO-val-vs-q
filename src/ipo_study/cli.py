"""Command line: `ipo-study run | robustness | site | fetch | crosscheck`."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .study import Config, headline, run

ROOT = Path(__file__).resolve().parents[2]


def _jsonable(R: dict) -> dict:
    return {k: v for k, v in R.items() if not k.startswith("_")}


def write_results(R: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(_jsonable(R), indent=1, default=str))
    (out / "headline.json").write_text(json.dumps(headline(R), indent=1))
    hot = set(R["heat_cutoffs"]["hot_ids"])
    cold = set(R["heat_cutoffs"]["cold_ids"])
    with open(out / "deal_returns.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "region", "ipo_date", "cohort", "listing_type", "sector", "mcap_usd_bn", "ps_at_offer",
                    "profitable", "verified", "heat", "first_month_vs_offer",
                    *[f"xs_offer_{h}m" for h in (6, 12, 36)], *[f"xs_after_{h}m" for h in (6, 12, 36)],
                    "since_listing_years", "since_listing_excess_cagr"])
        for r in R["_deal_results"]:
            d = r.deal
            heat = "Hot" if d.id in hot else "Cold" if d.id in cold else ("Middle" if d.listing_type == "IPO" else "")
            fmt = lambda v: "" if v is None else f"{v:.4f}"
            w.writerow([d.id, d.name, d.region, d.ipo_date, d.cohort, d.listing_type, d.sector, d.mcap_usd_bn,
                        fmt(d.ps), "" if d.profitable is None else int(d.profitable), int(d.verified), heat, fmt(r.entry_prem),
                        *[fmt(r.xs("offer", h)) for h in (6, 12, 36)], *[fmt(r.xs("after", h)) for h in (6, 12, 36)],
                        fmt(r.since["years"]) if r.since else "",
                        fmt(r.since["cagr"] - r.since["bench_cagr"]) if r.since else ""])


ROBUSTNESS = [
    ("Base case ($5bn+, 2010-2025, US + global)", Config()),
    ("Very large only ($10bn+)", Config(min_mcap_usd_bn=10)),
    ("Mega only ($25bn+)", Config(min_mcap_usd_bn=25)),
    ("US only", Config(regions=("US",))),
    ("Global only", Config(regions=("Global",))),
    ("Excluding the 2020-21 boom", Config(exclude_cohorts=("2020-21",))),
    ("First half only: 2010-2018 listings", Config(to_year=2018)),
    ("Second half only: 2019-2025 listings", Config(from_year=2019)),
    ("Excluding the five best 3-year winners", Config(exclude_ids=("NIO", "ARM", "CRWD", "PDD", "LI"))),
]


def robustness(out: Path) -> str:
    def p(v):
        return "" if v is None else f"{v * 100:+.0f}%"

    def q(v):
        return "" if v is None else f"{v * 100:.0f}%"
    lines = ["| Variant | Deals | Median 3y excess after listing | Beat index 3y | Median 3y excess from offer | Short hottest third: mean 3y | Hit | P/S rank corr. 3y |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for name, cfg in ROBUSTNESS:
        try:
            R = run(cfg)
            h = headline(R)
        except Exception as e:  # e.g. no verified deals yet
            lines.append(f"| {name} | 0 | not enough deals ({type(e).__name__}) | | | | | |")
            continue
        if h["n_deals"] == 0:
            lines.append(f"| {name} | 0 | no deals marked verified yet | | | | | |")
            continue
        rho = h["spearman_ps_36m"]
        lines.append(f"| {name} | {h['n_deals']} | {p(h['after_median_36m'])} | {q(h['after_hit_36m'])} | {p(h['offer_median_36m'])} | "
                     f"{p(h['short_hot_mean_36m'])} | {q(h['short_hot_hit_36m'])} | {'' if rho is None else f'{rho:+.2f}'} |")
    md = "\n".join(lines) + "\n"
    out.mkdir(parents=True, exist_ok=True)
    (out / "robustness.md").write_text(md)
    return md


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="ipo-study", description="Large-cap IPOs: traditional valuation vs quant rules")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the study with optional filters")
    r.add_argument("--min-mcap", type=float, default=5.0, help="minimum market value at offer, $bn")
    r.add_argument("--universe", choices=["core", "asia"], default="core",
                   help="core = US + global (v1); asia = Korea, India, Hong Kong, China A (v1.2)")
    r.add_argument("--region", choices=["US", "Global", "Korea", "India", "HK", "ChinaA", "all"], default="all")
    r.add_argument("--exclude-cohort", action="append", default=[], help="e.g. 2020-21 (repeatable)")
    r.add_argument("--exclude", action="append", default=[], help="deal id to drop (repeatable)")
    r.add_argument("--from-year", type=int, default=2010)
    r.add_argument("--to-year", type=int, default=2025)
    r.add_argument("--verified-only", action="store_true")
    r.add_argument("--bootstrap", type=int, default=0, help="bootstrap draws for 95%% intervals")
    r.add_argument("--seed", type=int, default=7)
    r.add_argument("--out", type=Path, default=None, help="default results/ (core) or results/asia/")
    sub.add_parser("robustness", help="run the standard battery of alternative specifications")
    sub.add_parser("site", help="build site/index.html from results")
    sub.add_parser("pdf", help="print the report to reports/ipo-valuation-vs-quant.pdf (needs playwright)")
    sub.add_parser("fetch", help="re-download prices from Yahoo Finance into data/independent/")
    sub.add_parser("industry", help="download Damodaran industry files and build data/industry_benchmarks.csv")
    sub.add_parser("sec", help="download SEC XBRL facts for the pilot deals and write data/fundamentals_sec_extract.csv")
    v = sub.add_parser("valuation", help="value each deal with comps and DCF; test against returns")
    v.add_argument("--universe", choices=["core", "asia"], default="core")
    c = sub.add_parser("crosscheck", help="compare snapshot returns with the Yahoo download")
    c.add_argument("--tolerance", type=float, default=0.03)
    a = ap.parse_args(argv)

    if a.cmd == "run":
        cfg = Config(universe=a.universe, min_mcap_usd_bn=a.min_mcap, regions=None if a.region == "all" else (a.region,),
                     exclude_cohorts=tuple(a.exclude_cohort), exclude_ids=tuple(a.exclude), from_year=a.from_year,
                     to_year=a.to_year, verified_only=a.verified_only, bootstrap=a.bootstrap, seed=a.seed)
        R = run(cfg)
        write_results(R, a.out or (ROOT / "results" if a.universe == "core" else ROOT / "results" / a.universe))
        print(json.dumps(headline(R), indent=1))
    elif a.cmd == "robustness":
        print(robustness(ROOT / "results"))
    elif a.cmd == "site":
        from .site import build
        print(build())
    elif a.cmd == "pdf":
        from .site import pdf
        print(pdf())
    elif a.cmd == "fetch":
        from .fetch import fetch
        print(fetch(ROOT / "data" / "independent"))
    elif a.cmd == "industry":
        from .industry import build, fetch, fetch_riskfree
        for line in fetch():
            print(line)
        print(fetch_riskfree())
        print(build())
    elif a.cmd == "sec":
        from .sec import download, extract
        download()
        print(extract())
    elif a.cmd == "valuation":
        from .valuation_study import run_valuation
        sfx = "" if a.universe == "core" else f"_{a.universe}"
        V = run_valuation(Config(universe=a.universe))
        out = ROOT / "results" / f"valuation{sfx}.json"
        clean = {k: v for k, v in V.items() if not k.startswith("_")}
        clean["deals"] = [{"id": x["id"], "industry": x["industry"], "comps_gap": x["val"]["comps_gap"], "dcf_gap": x["val"]["dcf_gap"],
                           "blended_gap": x["val"]["blended_gap"], "multiples": x["val"]["multiples"],
                           "industry_multiples": {k: getattr(x["ind"], k) for k in ("ev_ebitda", "ev_sales", "pe", "div_yield", "pbv", "wacc", "op_margin")},
                           "comps_implied": x["val"]["comps"]["implied"], "dcf_sensitivity": x["val"].get("dcf_gap_sensitivity")}
                          for x in V["_rows"]]
        out.write_text(json.dumps(clean, indent=1, default=str))
        with open(ROOT / "results" / f"strategy_comparison{sfx}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["family", "strategy", "entry", "horizon_m", "trades", "mean", "median", "hit", "t", "note"])
            w.writeheader()
            w.writerows(V["comparison"])
        print(f"{V['deals_valued']} deals valued; problems: {V['problems'] or 'none'}; written to {out}")
    elif a.cmd == "crosscheck":
        from .fetch import crosscheck
        rep = crosscheck(ROOT / "data" / "independent" / "prices_yahoo.csv", a.tolerance)
        bad = [x for x in rep if x["flag"]]
        out = ROOT / "results" / "crosscheck.csv"
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rep[0].keys()) if rep else ["id"])
            w.writeheader()
            w.writerows(rep)
        print(f"{len(rep)} deal-horizon returns compared, {len(bad)} differ by more than {a.tolerance:.0%}; see {out}")
        for x in bad[:30]:
            print(f"  {x['id']:10s} {x['horizon_m']:>2}m  snapshot {x['snapshot']:+.1%}  yahoo {x['yahoo']:+.1%}")


if __name__ == "__main__":
    main()
