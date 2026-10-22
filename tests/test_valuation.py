"""Valuation formulas checked against numbers you can work out by hand."""
import math

import pytest

from ipo_study.valuation import (DCFRules, Fundamentals, Industry, comps_value, dcf_value, offer_equity_value,
                                 offer_multiples, value_deal)


def co(**kw):
    base = dict(id="X", revenue=1000.0, revenue_prior=1000.0, ebitda=200.0, ebit=150.0, net_income=100.0,
                dividends=40.0, cash=50.0, debt=250.0, primary_proceeds=0.0, shares_post_ipo=100.0)
    base.update(kw)
    return Fundamentals(**base)


IND = Industry(name="Test", ev_ebitda=10.0, ev_sales=2.0, pe=15.0, div_yield=0.02, pbv=1.5,
               wacc=0.08, op_margin=0.15, sales_to_capital=2.0, market_wacc=0.08, riskfree=0.02)


def test_offer_equity_value_with_ads_and_fx():
    f = co(shares_post_ipo=800.0, ads_ratio=8.0, fx_listing_to_reporting=6.5)
    assert math.isclose(offer_equity_value(f, 10.0), 10 * 100 * 6.5)   # 100m ADS x $10 x 6.5


def test_offer_multiples():
    m = offer_multiples(co(), 20.0)                 # equity 2,000; net debt 200; EV 2,200
    assert math.isclose(m["enterprise_value"], 2200)
    assert math.isclose(m["ev_ebitda"], 11.0)
    assert math.isclose(m["ev_sales"], 2.2)
    assert math.isclose(m["pe"], 20.0)
    assert math.isclose(m["div_yield"], 0.02)


def test_comps_implied_values_and_median():
    c = comps_value(co(), IND)
    assert math.isclose(c["implied"]["ev_ebitda"], 10 * 200 - 200)   # 1,800
    assert math.isclose(c["implied"]["ev_sales"], 2 * 1000 - 200)    # 1,800
    assert math.isclose(c["implied"]["pe"], 15 * 100)                # 1,500
    assert math.isclose(c["implied"]["div_yield"], 40 / 0.02)        # 2,000
    assert math.isclose(c["value"], 1800)


def test_comps_loss_maker_uses_sales_only():
    c = comps_value(co(ebitda=-50.0, ebit=-80.0, net_income=-90.0, dividends=None), IND)
    assert set(c["implied"]) == {"ev_sales"}


def test_comps_financial_uses_pe_pbv_dividends():
    c = comps_value(co(financial=True, book_equity=1000.0), IND)
    assert set(c["implied"]) == {"pbv", "pe", "div_yield"}
    assert math.isclose(c["implied"]["pbv"], 1500)


def test_dcf_no_growth_perpetuity():
    """Zero growth, margin already at target, no reinvestment: EV = EBIT(1-t) / WACC."""
    f = co(revenue_prior=1000.0, ebit=150.0, marginal_tax=0.25)
    ind = Industry(name="flat", op_margin=0.15, wacc=0.10, market_wacc=0.10, riskfree=0.0, sales_to_capital=2.0)
    d = dcf_value(f, ind, DCFRules(margin_rule="hold"))
    assert math.isclose(d["enterprise_value"], 150 * 0.75 / 0.10, rel_tol=1e-9)
    assert math.isclose(d["equity_value"], d["enterprise_value"] - 200, rel_tol=1e-9)


def test_dcf_margin_rules_order():
    f = co(ebit=300.0)          # 30% margin vs 15% industry
    hold = dcf_value(f, IND, DCFRules(margin_rule="hold"))["enterprise_value"]
    mid = dcf_value(f, IND, DCFRules(margin_rule="midpoint"))["enterprise_value"]
    ind_ = dcf_value(f, IND, DCFRules(margin_rule="industry"))["enterprise_value"]
    assert hold > mid > ind_


def test_dcf_loss_maker_converges_to_industry_margin_and_uses_losses():
    f = co(revenue=500.0, revenue_prior=250.0, ebitda=-40.0, ebit=-100.0, net_income=-110.0)
    d = dcf_value(f, IND)
    assert math.isclose(d["g0"], 0.40)                       # 100% trailing growth capped at 40%
    assert math.isclose(d["margin_target"], 0.15)
    assert d["path"][0]["tax"] == 0.0                         # losses are not taxed
    assert math.isclose(d["path"][-1]["margin"], 0.15)


def test_higher_wacc_lowers_value():
    lo = dcf_value(co(), IND, DCFRules(wacc_shift=-0.01))["equity_value"]
    hi = dcf_value(co(), IND, DCFRules(wacc_shift=0.01))["equity_value"]
    assert lo > hi


def test_terminal_growth_must_be_below_wacc():
    with pytest.raises(ValueError):
        dcf_value(co(), Industry(name="bad", market_wacc=0.02, wacc=0.02, riskfree=0.03))


def test_value_deal_gaps():
    v = value_deal(co(), IND, 20.0)               # offer equity 2,000; comps 1,800
    assert math.isclose(v["comps_gap"], 1800 / 2000 - 1)
    assert v["dcf_gap"] is not None and "wacc_+1pt" in v["dcf_gap_sensitivity"]
    assert math.isclose(v["blended_gap"], (v["comps_gap"] + v["dcf_gap"]) / 2)


def test_damodaran_parser_reads_header_and_percent(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from ipo_study.industry import parse
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Date updated:", "05-Jan-24"])
    ws.append([])
    ws.append(["Industry Name", "Number of firms", "EV/EBITDA", "EV/Sales", "Cost of Capital"])
    ws.append(["Software (Internet)", 33, 25.1, 4.2, "9.50%"])
    ws.append(["Total Market", 5000, 14.0, 2.1, 0.081])
    p = tmp_path / "test.xlsx"
    wb.save(p)
    out = parse(p, {"ev_ebitda": ["ev/ebitda"], "wacc": ["cost of capital"]})
    assert out["Software (Internet)"]["ev_ebitda"] == 25.1
    assert abs(out["Software (Internet)"]["wacc"] - 0.095) < 1e-12
    assert out["Total Market"]["wacc"] == 0.081


def test_every_pilot_deal_is_in_the_universe_and_has_a_template_row():
    import csv
    from ipo_study.data import DATA_DIR, load_deals
    ids = {d.id for d in load_deals()}
    imap = {r["id"] for r in csv.DictReader(open(DATA_DIR / "industry_map.csv"))}
    fund = {r["id"] for r in csv.DictReader(open(DATA_DIR / "fundamentals.csv"))}
    assert imap <= ids and imap == fund


def test_traditional_rules_pick_the_attractive_ipos():
    from types import SimpleNamespace
    from ipo_study.valuation_study import TRADITIONAL_RULES, compare_strategies

    class Res:
        def __init__(self, x6):
            self.x6, self.entry_prem = x6, 0.1
        def xs(self, kind, h):
            return self.x6
        def fwd_xs(self, a, b):
            return 0.0
    def row(i, dy, pe, gap, x6):
        mult = {"div_yield": dy, "pe": pe, "ev_ebitda": None, "ev_sales": None, "pbv": None}
        return {"id": i, "financial": False, "ind": IND, "result": Res(x6),
                "val": {"multiples": mult, "comps_gap": gap, "dcf_gap": gap}}
    rows = [row("A", 0.04, 10.0, 0.2, 0.30), row("B", 0.01, 30.0, -0.3, -0.10), row("C", None, None, 0.1, 0.05)]
    pick = lambda name: [x["id"] for x in rows if TRADITIONAL_RULES[name](x)]
    assert pick("Dividend yield above industry") == ["A"]          # 4% vs 2% industry
    assert pick("P/E below industry") == ["A"]                     # 10x vs 15x
    assert pick("Comps value above offer") == ["A", "C"]
    cmp = compare_strategies(rows, hot_ids={"B"})
    dy = next(r for r in cmp if r["strategy"] == "Dividend yield above industry" and r["horizon_m"] == 6 and r["entry"] == "offer")
    assert dy["trades"] == 1 and abs(dy["mean"] - 0.30) < 1e-12
    short_hot = next(r for r in cmp if r["strategy"] == "Short hottest third" and r["horizon_m"] == 6)
    assert abs(short_hot["mean"] - 0.10) < 1e-12                  # short B, which lagged by 10%
