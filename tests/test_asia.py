"""The Asia extension (v1.2): Korea, India, Hong Kong and China A-shares."""
import csv
import json
import math
from pathlib import Path

import pytest

from ipo_study.data import DATA_DIR, load_benchmarks, load_universe
from ipo_study.study import Config, headline, run

DEALS, PRICES = load_universe("asia")
BENCH = load_benchmarks()
EXPECTED = json.loads((Path(__file__).parent / "expected_headline_asia.json").read_text())


def test_universe_definition():
    ids = [d.id for d in DEALS]
    assert len(ids) == len(set(ids))
    for d in DEALS:
        assert d.region in ("Korea", "India", "HK", "ChinaA"), d.id
        assert d.mcap_usd_bn >= 5 and 2010 <= d.year <= 2025 and d.offer_price > 0, d.id


def test_every_deal_has_entry_price_and_local_benchmark():
    for d in DEALS:
        assert d.ipo_month in PRICES.get(d.ticker, {}), d.id
        assert d.ipo_month in BENCH[d.region], d.id


def test_late_entry_months_are_logged():
    """Deals whose first monthly bar is after the IPO month must be listed in corrections.csv."""
    logged = {r["ticker"] for r in csv.DictReader(open(DATA_DIR / "corrections.csv")) if r["field"] == "entry month"}
    for d in DEALS:
        if (d.extra.get("entry_month") or "").strip():
            assert d.ticker in logged, d.id


def test_excluded_are_not_in_universe():
    excluded = {r["id"] for r in csv.DictReader(open(DATA_DIR / "excluded_asia.csv"))}
    assert excluded.isdisjoint({d.id for d in DEALS})


def test_prices_rebuild_from_raw_yahoo_files():
    """Every row of prices_asia.csv can be regenerated from the saved Yahoo responses."""
    from ipo_study.yahoo import RAW, monthly
    if not RAW.exists():
        pytest.skip("raw Yahoo files not present")
    rows = list(csv.DictReader(open(DATA_DIR / "prices_asia.csv")))
    cache, bad = {}, []
    from ipo_study.data import month_index
    for r in rows:
        t = r["ticker"]
        if t not in cache:
            cache[t] = monthly(t)["prices"] if (RAW / f"{t}.json").exists() else None
        p = cache[t]
        assert p is not None, f"no raw file for {t}"
        a, c = p[month_index(r["month"])]
        if not (math.isclose(a, float(r["adj_close"]), rel_tol=1e-4) and math.isclose(c, float(r["close"]), rel_tol=1e-4)):
            bad.append((t, r["month"]))
    assert not bad, bad[:10]


def test_benchmarks_cover_2010_to_snapshot_without_gaps():
    for k in ("Korea", "India", "HK", "ChinaA"):
        ms = sorted(BENCH[k])
        assert ms == list(range(ms[0], ms[-1] + 1)), k
        assert ms[0] <= 2010 * 12 and ms[-1] >= 2026 * 12 + 8, k


def test_headline_numbers_unchanged():
    got = headline(run(Config(universe="asia")))
    assert set(got) == set(EXPECTED)
    for k, v in EXPECTED.items():
        if isinstance(v, float):
            assert math.isclose(got[k], v, rel_tol=1e-9, abs_tol=1e-12), k
        else:
            assert got[k] == v, k


def test_report_figures():
    h = headline(run(Config(universe="asia")))
    assert h["n_deals"] == 131
    assert round(h["entry_premium_median"] * 100) == 15
    assert round(h["after_median_36m"] * 100) == -25
    assert round(h["after_hit_36m"] * 100) == 32
    assert round(h["short_hot_hit_36m"] * 100) == 74


def test_core_study_is_untouched_by_the_asia_files():
    assert headline(run())["n_deals"] == 96


def test_pilot_rows_match_universe_and_cite_a_filing():
    ids = {d.id for d in DEALS}
    imap = {r["id"] for r in csv.DictReader(open(DATA_DIR / "industry_map_asia.csv"))}
    fund = list(csv.DictReader(open(DATA_DIR / "fundamentals_asia.csv")))
    assert imap <= ids and imap == {r["id"] for r in fund}
    for r in fund:
        assert r["source_url"].startswith("https://"), r["id"]
        assert r["notes"].strip(), r["id"]


# approximate local currency per US$ at the listing, only to sanity-check offer size
FX = {("HKD", None): 7.8, ("CNY", 2015): 6.2, ("CNY", 2018): 6.5, ("CNY", 2020): 7.0,
      ("INR", 2010): 44.5, ("INR", 2018): 65.0, ("INR", 2021): 74.5}


def test_pilot_offer_size_matches_deal_list():
    """Offer equity value from the prospectus inputs vs the deal list's $bn (Xiaomi's list value is fully diluted)."""
    from ipo_study.valuation import load_fundamentals, offer_equity_value
    F = load_fundamentals(DATA_DIR / "fundamentals_asia.csv")
    for d in DEALS:
        if d.id in F:
            f = F[d.id]
            ccy = d.extra["exchange_ccy"]
            fx = FX.get((ccy, None)) or FX[(ccy, d.year)]
            usd_bn = offer_equity_value(f, d.offer_price) / f.fx_listing_to_reporting / fx / 1000
            tol = 0.75 if d.id == "XIAOMI" else 0.85
            assert tol < usd_bn / d.mcap_usd_bn < 1 / tol, (d.id, usd_bn, d.mcap_usd_bn)


def test_thin_country_industry_falls_back_to_emerging_file():
    from ipo_study.valuation_study import industry_for
    table = {("China", 2019, "beverage (soft)"): {"industry": "Beverage (Soft)", "n_firms": "2", "pe": "4.3", "wacc": "0.035"},
             ("Emerging", 2019, "beverage (soft)"): {"industry": "Beverage (Soft)", "n_firms": "31", "pe": "32.6", "wacc": "0.043"}}
    imap = {"X": {"benchmark_region": "China", "benchmark_file_year": "2019", "industry": "Beverage (Soft)", "alternative_industry": ""}}
    ind, used = industry_for("X", imap, table, {})
    assert ind.pe == 32.6 and "Emerging" in used
    table[("China", 2019, "beverage (soft)")]["n_firms"] = "40"
    ind, used = industry_for("X", imap, table, {})
    assert ind.pe == 4.3 and used == "Beverage (Soft)"


def test_asian_pilot_valuation_runs_without_problems():
    from ipo_study.valuation_study import run_valuation
    V = run_valuation(Config(universe="asia"))
    assert V["deals_valued"] == 15 and not V["problems"]
    assert {x["result"].deal.region for x in V["_rows"]} == {"HK", "ChinaA", "India"}


def test_meaningless_industry_pe_is_dropped():
    from ipo_study.valuation_study import _pe
    assert _pe(35.9) == 35.9 and _pe(70015.0) is None and _pe(-12.0) is None and _pe(None) is None
