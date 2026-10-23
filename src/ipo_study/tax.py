"""Statutory corporate income tax rates by country and year, from the Tax Foundation's
published data (data/raw/taxfoundation/, see SOURCE.md). Used as the DCF's marginal tax rate."""
from __future__ import annotations

import csv
from functools import lru_cache

from .data import DATA_DIR

RAW = DATA_DIR / "raw" / "taxfoundation"


@lru_cache(maxsize=1)
def table() -> dict[tuple[str, int], float]:
    out: dict[tuple[str, int], float] = {}
    for r in csv.DictReader(open(RAW / "data_rates_1980_2022.csv", newline="", encoding="utf-8")):
        for k, v in r.items():
            if k and k.isdigit() and v not in ("", "NA"):
                out[(r["iso_3"], int(k))] = float(v) / 100
    for r in csv.DictReader(open(RAW / "final_data_2023.csv", newline="", encoding="utf-8")):
        if r["rate"] not in ("", "NA"):
            out[(r["iso_3"], int(r["year"]))] = float(r["rate"]) / 100
    return out


def statutory_rate(iso3: str, year: int) -> float:
    """Rate in force in `year` for country `iso3`. Raises KeyError when the source has no value."""
    return table()[(iso3, year)]
