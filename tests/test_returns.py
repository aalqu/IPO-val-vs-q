"""Return arithmetic on a hand-built deal, so every formula is checked against numbers you can do on paper."""
import math

from ipo_study.data import Deal, month_index
from ipo_study.study import Config, deal_returns, run, select


def make_deal(**kw):
    base = dict(id="X", name="Test Co", ticker="X", region="US", ipo_date="2015-01-15", listing_type="IPO",
                offer_price=10.0, mcap_usd_bn=20.0, revenue_usd_bn=2.0, profitable=True, sector="Test",
                financial=False, price_unit_divisor=1.0, entry_close_override=None, verified=True)
    base.update(kw)
    return Deal(**base)


def prices_for(ticker, m0, path):
    """path: {months_after: adjusted close}; unadjusted close = adjusted (no dividends)."""
    return {ticker: {m0 + h: (v, v) for h, v in path.items()}}


M0 = month_index("2015-01")
BENCH = {"US": {M0 + h: 100 * (1.01 ** h) for h in range(0, 40)}, "Global": {}}


def test_entry_premium_and_offer_returns():
    d = make_deal()
    px = prices_for("X", M0, {0: 12.0, 6: 9.0, 12: 15.0, 36: 6.0})
    (r,) = deal_returns([d], px, BENCH)
    assert math.isclose(r.entry_prem, 0.2)            # 12 / 10 - 1
    assert math.isclose(r.r_after[6], 9 / 12 - 1)     # from first month-end
    assert math.isclose(r.r_offer[6], 9 / 10 - 1)     # from the offer
    assert math.isclose(r.r_offer[12], 0.5)
    assert math.isclose(r.bench[12], 1.01 ** 12 - 1)
    assert math.isclose(r.xs("offer", 12), 0.5 - (1.01 ** 12 - 1))


def test_forward_excess_between_months():
    d = make_deal()
    px = prices_for("X", M0, {0: 10.0, 6: 8.0, 18: 12.0})
    (r,) = deal_returns([d], px, BENCH)
    expected = (12 / 8 - 1) - (1.01 ** 18 / 1.01 ** 6 - 1)
    assert math.isclose(r.fwd_xs(6, 18), expected)


def test_entry_override_and_unit_divisor():
    d = make_deal(offer_price=530.0, price_unit_divisor=1.0, entry_close_override=None)  # pence in, pence out
    px = prices_for("X", M0, {0: 530.0})
    assert math.isclose(deal_returns([d], px, BENCH)[0].entry_prem, 0.0)
    d2 = make_deal(entry_close_override=11.0)
    assert math.isclose(deal_returns([d2], prices_for("X", M0, {0: 99.0}), BENCH)[0].entry_prem, 0.1)


def test_missing_horizon_is_none_not_zero():
    d = make_deal()
    (r,) = deal_returns([d], prices_for("X", M0, {0: 10.0, 6: 11.0}), BENCH)
    assert r.xs("after", 36) is None


def test_selection_filters():
    deals = [make_deal(id="A", mcap_usd_bn=6), make_deal(id="B", mcap_usd_bn=12),
             make_deal(id="C", region="Global"), make_deal(id="D", ipo_date="2021-03-01")]
    ids = lambda cfg: [d.id for d in select(deals, cfg)]
    assert ids(Config(min_mcap_usd_bn=10)) == ["B", "C", "D"]
    assert ids(Config(regions=("US",))) == ["A", "B", "D"]
    assert ids(Config(exclude_cohorts=("2020-21",))) == ["A", "B", "C"]


def test_hot_and_cold_terciles_on_synthetic_set():
    deals, px = [], {}
    for i, prem in enumerate([0.0, 0.1, 0.2, 0.5, 0.8, 1.0]):
        t = f"T{i}"
        deals.append(make_deal(id=t, ticker=t))
        px[t] = {M0 + h: (10 * (1 + prem), 10 * (1 + prem)) for h in (0, 6, 12, 36)}
    R = run(Config(), deals=deals, prices=px, benches=BENCH)
    assert R["heat_cutoffs"]["hot_ids"] == ["T4", "T5"]
    assert R["heat_cutoffs"]["cold_ids"] == ["T0", "T1"]
