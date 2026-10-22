"""Summary statistics. Standard library only."""
from __future__ import annotations

import math
import random
import statistics as st
from typing import Iterable, Sequence


def clean(values: Iterable[float | None]) -> list[float]:
    return [v for v in values if v is not None]


def summarize(values: Iterable[float | None]) -> dict | None:
    """n, mean, median, hit rate (share > 0) and t-stat of the mean."""
    v = clean(values)
    if not v:
        return None
    n = len(v)
    mean = st.mean(v)
    sd = st.stdev(v) if n > 1 else 0.0
    t = mean / (sd / math.sqrt(n)) if sd > 0 else None
    return {"n": n, "mean": mean, "median": st.median(v), "hit": sum(x > 0 for x in v) / n, "t": t}


def _ranks(v: Sequence[float]) -> list[float]:
    """Average ranks (ties share the mean rank)."""
    order = sorted(range(len(v)), key=lambda i: v[i])
    ranks = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2
        i = j + 1
    return ranks


def spearman(x: Sequence[float | None], y: Sequence[float | None]) -> dict | None:
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pairs) < 5:
        return None
    rx, ry = _ranks([p[0] for p in pairs]), _ranks([p[1] for p in pairs])
    mx, my = st.mean(rx), st.mean(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return {"rho": cov / den if den else None, "n": len(pairs)}


def bootstrap_ci(values: Iterable[float | None], stat: str = "median", n_boot: int = 2000,
                 seed: int = 7, level: float = 0.95) -> tuple[float, float] | None:
    """Percentile bootstrap interval for the mean, median or hit rate."""
    v = clean(values)
    if len(v) < 5 or n_boot <= 0:
        return None
    rng = random.Random(seed)
    f = {"mean": st.mean, "median": st.median, "hit": lambda s: sum(x > 0 for x in s) / len(s)}[stat]
    draws = sorted(f([rng.choice(v) for _ in v]) for _ in range(n_boot))
    lo = draws[int((1 - level) / 2 * n_boot)]
    hi = draws[min(n_boot - 1, int((1 + level) / 2 * n_boot))]
    return (lo, hi)
