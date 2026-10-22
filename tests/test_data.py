"""Integrity checks on the published data. A reviewer's first line of defence."""
import csv
import hashlib
from pathlib import Path

import pytest

from ipo_study.data import DATA_DIR, load_benchmarks, load_deals, load_prices, month_index

DEALS = load_deals()
PRICES = load_prices()
BENCH = load_benchmarks()


def test_deal_ids_unique():
    ids = [d.id for d in DEALS]
    assert len(ids) == len(set(ids))


def test_every_deal_has_ipo_month_price_and_benchmark():
    for d in DEALS:
        assert d.ipo_month in PRICES.get(d.ticker, {}), d.id
        assert d.ipo_month in BENCH[d.region], d.id


def test_universe_definition():
    for d in DEALS:
        assert d.mcap_usd_bn >= 5, d.id
        assert 2010 <= d.year <= 2025, d.id
        assert d.region in ("US", "Global")
        assert d.listing_type in ("IPO", "Direct")
        assert d.offer_price > 0


def test_excluded_deals_are_not_in_universe():
    excluded = {r["id"] for r in csv.DictReader(open(DATA_DIR / "excluded.csv"))}
    assert excluded.isdisjoint({d.id for d in DEALS})


def test_prices_positive_and_months_valid():
    for t, rows in PRICES.items():
        for m, (adj, close) in rows.items():
            assert adj > 0 and close > 0, (t, m)
            assert month_index("2010-01") <= m <= month_index("2026-10"), (t, m)


def test_benchmarks_have_no_gaps():
    for region, series in BENCH.items():
        ms = sorted(series)
        assert ms == list(range(ms[0], ms[-1] + 1)), region


def test_adjustment_factors_are_explained():
    """close/adj_close moves only with splits and dividends. Large factors must be documented."""
    documented = {r["ticker"] for r in csv.DictReader(open(DATA_DIR / "corporate_actions.csv"))}
    undocumented = []
    for t, rows in PRICES.items():
        f = [c / a for a, c in rows.values()]
        if (max(f) > 1.6 or min(f) < 0.6 or max(f) / min(f) > 1.6) and t not in documented:
            undocumented.append(t)
    assert not undocumented, f"unexplained price adjustment for {undocumented}; add to corporate_actions.csv"


def test_checksums_match():
    sums = (DATA_DIR / "SHA256SUMS").read_text().split("\n")
    for line in filter(None, sums):
        digest, name = line.split(maxsplit=1)
        assert hashlib.sha256((DATA_DIR / name.strip()).read_bytes()).hexdigest() == digest, name


@pytest.mark.xfail(reason="Offer prices and valuation inputs are not yet sourced; see data/known_issues.md", strict=False)
def test_provenance_complete():
    missing = [d.id for d in DEALS if not d.extra["offer_price_source"] or not d.extra["valuation_inputs_source"]]
    assert not missing, f"{len(missing)} of {len(DEALS)} deals lack sources"


def test_valuation_inputs_match_offer_size():
    """Offer price x post-IPO shares (converted) should be close to the deal's reported size.
    Basic share counts exclude options/RSUs, so a few tech deals sit lower; anything else is a data error."""
    from ipo_study.valuation import load_fundamentals, offer_equity_value
    usd = {"CNY": 1 / 6.1344, "EUR": 1.1360, "SAR": 1 / 3.75}
    diluted_gap_ok = {"META", "SNAP", "UBER", "ABNB"}
    deals = {d.id: d for d in DEALS}
    funds = load_fundamentals()
    for i, f in funds.items():
        d = deals[i]
        ccy = d.extra and next(r for r in csv.DictReader(open(DATA_DIR / "fundamentals.csv")) if r["id"] == i)["reporting_ccy"]
        val = offer_equity_value(f, d.offer_price / d.price_unit_divisor) * usd.get(ccy, 1) / 1000
        lo = 0.75 if i in diluted_gap_ok else 0.90   # deals.csv sizes are approximate press figures (e.g. Kenvue 41 vs 37.8)
        assert lo <= val / d.mcap_usd_bn <= 1.05, (i, round(val, 1), d.mcap_usd_bn)


def test_valuation_inputs_agree_with_sec_xbrl():
    """Where the SEC XBRL extract has the same figure, the hand-entered value must agree within 1%,
    unless the deviation is documented in that row's notes."""
    ext = {}
    for r in csv.DictReader(open(DATA_DIR / "fundamentals_sec_extract.csv")):
        if r["value"]:
            ext[(r["id"], r["field"])] = float(r["value"]) / 1e6
    for r in csv.DictReader(open(DATA_DIR / "fundamentals.csv")):
        for fld in ("revenue", "revenue_prior", "net_income"):
            x = ext.get((r["id"], fld))
            if x is None or not r[fld] or float(r[fld]) == 0:
                continue
            v = float(r[fld])
            if abs(v - x) > 0.01 * max(abs(x), 1) and "pro forma" not in r["notes"] and "originally reported" not in r["notes"]:
                raise AssertionError(f"{r['id']} {fld}: file {v} vs XBRL {x}")
