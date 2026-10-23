"""The published numbers. If data or code changes any headline figure, this fails until
the change is reviewed and tests/expected_headline.json is regenerated on purpose
(`make golden`)."""
import json
import math
from pathlib import Path

from ipo_study.study import headline, run

EXPECTED = json.loads((Path(__file__).parent / "expected_headline.json").read_text())


def test_headline_numbers_unchanged():
    got = headline(run())
    assert set(got) == set(EXPECTED)
    for k, v in EXPECTED.items():
        if isinstance(v, float):
            assert math.isclose(got[k], v, rel_tol=1e-9, abs_tol=1e-12), k
        else:
            assert got[k] == v, k


def test_report_figures():
    """The rounded figures as printed in the report."""
    h = headline(run())
    assert h["n_deals"] == 96
    assert round(h["entry_premium_median"] * 100) == 14
    assert round(h["after_median_6m"] * 100) == -21
    assert round(h["after_median_12m"] * 100) == -30
    assert round(h["after_median_36m"] * 100) == -49
    assert round(h["short_hot_hit_36m"] * 100) == 88
