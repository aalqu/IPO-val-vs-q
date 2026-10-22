"""Load the study's input files. Standard library only."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def month_index(ym: str) -> int:
    """'2019-06' -> integer month count, so month arithmetic is plain addition."""
    y, m = ym.split("-")[:2]
    return int(y) * 12 + int(m) - 1


def month_label(i: int) -> str:
    return f"{i // 12}-{i % 12 + 1:02d}"


@dataclass
class Deal:
    id: str
    name: str
    ticker: str
    region: str            # "US" or "Global"
    ipo_date: str          # YYYY-MM-DD
    listing_type: str      # "IPO" or "Direct"
    offer_price: float
    mcap_usd_bn: float
    ltm_revenue_usd_bn: float | None
    profitable: bool
    sector: str
    financial: bool
    price_unit_divisor: float
    entry_close_override: float | None
    verified: bool
    extra: dict = field(default_factory=dict)

    @property
    def ipo_month(self) -> int:
        """Entry month: the IPO month, unless the price source starts later (logged in corrections.csv)."""
        em = (self.extra or {}).get("entry_month", "").strip() if self.extra else ""
        return month_index(em or self.ipo_date)

    @property
    def year(self) -> int:
        return int(self.ipo_date[:4])

    @property
    def cohort(self) -> str:
        y = self.year
        if y <= 2014:
            return "2010-14"
        if y <= 2019:
            return "2015-19"
        if y <= 2021:
            return "2020-21"
        return "2022-25"

    @property
    def ps(self) -> float | None:
        """Price-to-sales at the offer; not defined for financials."""
        if self.financial or not self.ltm_revenue_usd_bn:
            return None
        return self.mcap_usd_bn / self.ltm_revenue_usd_bn


def _f(x: str) -> float | None:
    x = (x or "").strip()
    return float(x) if x else None


def load_deals(path: Path | None = None) -> list[Deal]:
    path = path or DATA_DIR / "deals.csv"
    out = []
    for r in csv.DictReader(open(path, newline="", encoding="utf-8")):
        out.append(Deal(
            id=r["id"], name=r["name"], ticker=r["ticker"], region=r["region"],
            ipo_date=r["ipo_date"], listing_type=r["listing_type"],
            offer_price=float(r["offer_price"]), mcap_usd_bn=float(r["mcap_usd_bn_at_offer"]),
            ltm_revenue_usd_bn=_f(r["ltm_revenue_usd_bn"]),
            profitable=r["operating_profit_positive"] == "1", sector=r["sector"],
            financial=r["financial"] == "1", price_unit_divisor=float(r["price_unit_divisor"] or 1),
            entry_close_override=_f(r["entry_close_override"]),
            verified=r["verified"].strip().lower() in ("yes", "true", "1"), extra=r,
        ))
    return out


def load_prices(path: Path | None = None) -> dict[str, dict[int, tuple[float, float]]]:
    """ticker -> {month_index: (adjusted_close, unadjusted_close)}"""
    path = path or DATA_DIR / "prices.csv"
    out: dict[str, dict[int, tuple[float, float]]] = {}
    for r in csv.DictReader(open(path, newline="", encoding="utf-8")):
        out.setdefault(r["ticker"], {})[month_index(r["month"])] = (float(r["adj_close"]), float(r["close"]))
    return out


def load_benchmarks(path: Path | None = None) -> dict[str, dict[int, float]]:
    """{'US': {month: level}, 'Global': {month: level}} - total-return index levels."""
    path = path or DATA_DIR / "benchmarks.csv"
    us, gl = {}, {}
    for r in csv.DictReader(open(path, newline="", encoding="utf-8")):
        m = month_index(r["month"])
        if r["spy_adj_close"]:
            us[m] = float(r["spy_adj_close"])
        if r["acwi_adj_close"]:
            gl[m] = float(r["acwi_adj_close"])
    out = {"US": us, "Global": gl}
    asia = DATA_DIR / "benchmarks_asia.csv"
    if path == DATA_DIR / "benchmarks.csv" and asia.exists():
        cols = {"Korea": "korea_adj_close", "India": "india_adj_close", "HK": "hk_adj_close", "ChinaA": "chinaa_adj_close"}
        for k in cols:
            out[k] = {}
        for r in csv.DictReader(open(asia, newline="", encoding="utf-8")):
            m = month_index(r["month"])
            for k, c in cols.items():
                if r[c]:
                    out[k][m] = float(r[c])
    return out


UNIVERSES = {"core": ("deals.csv", "prices.csv"), "asia": ("deals_asia.csv", "prices_asia.csv")}
# per universe: (fundamentals file, industry map file) for the comps/DCF pilot
VALUATION_FILES = {"core": ("fundamentals.csv", "industry_map.csv"), "asia": ("fundamentals_asia.csv", "industry_map_asia.csv")}


def load_universe(name: str = "core"):
    d, p = UNIVERSES[name]
    return load_deals(DATA_DIR / d), load_prices(DATA_DIR / p)
