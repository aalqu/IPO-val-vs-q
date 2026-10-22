"""Unit tests for the statistics helpers."""
import math

from ipo_study.metrics import _ranks, bootstrap_ci, spearman, summarize


def test_summarize_basic():
    s = summarize([1.0, -1.0, 2.0, None])
    assert s["n"] == 3
    assert math.isclose(s["mean"], 2 / 3)
    assert s["median"] == 1.0
    assert math.isclose(s["hit"], 2 / 3)


def test_summarize_empty():
    assert summarize([None, None]) is None


def test_ranks_ties_share_mean_rank():
    assert _ranks([10, 20, 20, 30]) == [0, 1.5, 1.5, 3]


def test_spearman_perfect_and_inverse():
    x = [1, 2, 3, 4, 5, 6]
    assert math.isclose(spearman(x, [10, 20, 30, 40, 50, 60])["rho"], 1.0)
    assert math.isclose(spearman(x, [6, 5, 4, 3, 2, 1])["rho"], -1.0)


def test_spearman_needs_five_pairs():
    assert spearman([1, 2, 3], [1, 2, 3]) is None


def test_bootstrap_deterministic_and_brackets_median():
    v = [0.1 * i for i in range(-10, 11)]
    a = bootstrap_ci(v, "median", 500, seed=1)
    b = bootstrap_ci(v, "median", 500, seed=1)
    assert a == b
    assert a[0] <= 0.0 <= a[1]
