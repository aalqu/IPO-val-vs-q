"""Every deal-level number used by the study comes from data/deal_facts.csv, one row per
sourced value: the value, its unit, the document it came from (URL plus filing/accession) and
the exact words in that document (`quote`) or the XBRL tag and period. `build()` turns those
facts into the deal tables (data/deals.csv, data/deals_asia.csv). Nothing is estimated: a
value that cannot be computed from facts is left blank, and a deal whose market value at the
offer cannot be computed, or is under $5bn, is moved to the excluded list."""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date

from .data import DATA_DIR

FACTS = DATA_DIR / "deal_facts.csv"
MIN_MCAP_USD_BN = 5.0
FIN_SECTORS = {"Financial Services"}            # Yahoo Finance sector classification
FIN_SIC = range(6000, 6412)                     # SEC SIC: banks, credit, brokers, insurance (6000-6411)


def load_facts(path=FACTS) -> dict[str, dict[str, list[dict]]]:
    out: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in csv.DictReader(open(path, newline="", encoding="utf-8")):
        out[r["id"]][r["field"]].append(r)
    return out


def _one(f, field):
    v = f.get(field)
    return v[0]["value"] if v else None


def _num(x):
    return None if x in (None, "") else float(x)


def listing_date(f) -> str | None:
    """First trading day, in this order of preference:
    1. a first-dealing date stated by the exchange or the issuer (`listing_date`);
    2. Yahoo's first trade date, when it falls 0-10 days after the final prospectus or pricing date;
    3. the commencement of trading scheduled in the final prospectus (`scheduled_listing_date`);
    4. the final prospectus or pricing date (trading starts within days, in the same month for
       every such deal in the sample)."""
    if _one(f, "listing_date"):
        return _one(f, "listing_date")
    yd, pd = _one(f, "yahoo_first_trade_date"), _one(f, "prospectus_date")
    if yd and pd and 0 <= (date.fromisoformat(yd) - date.fromisoformat(pd)).days <= 10:
        return yd
    return _one(f, "scheduled_listing_date") or pd or yd


def derive(f) -> dict:
    price = _num(_one(f, "offer_price")) or _num(_one(f, "reference_price"))
    shares = sum(float(r["value"]) for k, rows in f.items() if k.startswith("shares_after_offering_") for r in rows) or None
    ads = _num(_one(f, "ordinary_shares_per_ads")) or 1.0
    usd_per = _num(_one(f, "fx_usd_per_listing"))                         # H.10 quotes GBP and EUR as US$ per unit
    fx_listing_usd = (1 / usd_per) if usd_per else (_num(_one(f, "fx_listing_per_usd")) or 1.0)  # listing ccy per US$
    mcap_local = price * shares / ads if price and shares else None
    mcap_usd_bn = mcap_local / fx_listing_usd / 1e9 if mcap_local else None
    rev = _num(_one(f, "revenue_last_fy"))
    rev_unit = (f.get("revenue_last_fy") or [{}])[0].get("unit", "")
    scale = 1e6 if "million" in rev_unit else 1.0
    fx_rep = _num(_one(f, "fx_reporting_per_usd"))
    rev_ccy = rev_unit.split()[0] if rev_unit else ""
    if rev is not None and rev_ccy != "USD" and fx_rep is None:
        rev_usd_bn = None                                                  # no sourced rate: no USD revenue
    else:
        rev_usd_bn = None if rev is None else rev * scale / (fx_rep or 1.0) / 1e9
    profit = _num(_one(f, "profit_last_fy"))
    sector = _one(f, "sector")
    sic = _one(f, "sic")
    financial = (sector in FIN_SECTORS) if sector else (int(sic) in FIN_SIC if sic else None)
    if (f.get("offer_price") or f.get("reference_price")) and not f.get("fx_listing_per_usd") and not f.get("fx_usd_per_listing"):
        unit = (f.get("offer_price") or f.get("reference_price"))[0]["unit"]
        if not unit.startswith("USD"):
            mcap_usd_bn = None                                             # non-US$ price with no sourced rate
    return {"listing_date": listing_date(f), "offer_price": price, "shares_after": shares, "mcap_usd_bn": mcap_usd_bn,
            "revenue_usd_bn": rev_usd_bn, "profitable": None if profit is None else profit > 0,
            "financial": financial, "sector": sector or (f.get("sic") or [{}])[0].get("quote")}


DEAL_COLUMNS = ["id", "name", "ticker", "region", "exchange_ccy", "ipo_date", "entry_month", "listing_type", "offer_price",
                "offer_price_unit", "mcap_usd_bn_at_offer", "revenue_last_fy_usd_bn", "operating_profit_positive", "sector",
                "financial", "price_unit_divisor", "entry_close_override", "offer_price_source", "verified"]


def _entry_months() -> dict[str, str]:
    """Entry-month overrides logged in corrections.csv (price source starts after the listing month)."""
    out = {}
    p = DATA_DIR / "corrections.csv"
    if p.exists():
        for r in csv.DictReader(open(p, newline="", encoding="utf-8")):
            if r["field"].strip() == "entry month":
                for t in r["ticker"].split():
                    out[t] = r["used_value"].strip()
    return out


def build(candidates: list[dict], facts=None) -> tuple[list[dict], list[dict]]:
    """Turn sourced facts into deal rows. `candidates` supplies identifiers only (id, name, ticker,
    region, currency, listing type, A+H flag); every number comes from the facts. Returns
    (deals, excluded)."""
    facts = facts if facts is not None else load_facts()
    em = _entry_months()
    deals, excluded = [], []
    for c in candidates:
        f = facts.get(c["id"])
        if not f:
            excluded.append({"id": c["id"], "name": c["name"], "reason": "offering documents not retrieved, so the offer price and share count are unsourced"})
            continue
        d = derive(f)
        if d["mcap_usd_bn"] is None:
            miss = [k for k in ("offer_price", "shares_after", "listing_date") if not d.get(k)]
            excluded.append({"id": c["id"], "name": c["name"], "reason": "market value at the offer not computable from sourced facts (missing: " + (", ".join(miss) or "exchange rate") + ")"})
            continue
        if d["mcap_usd_bn"] < MIN_MCAP_USD_BN:
            excluded.append({"id": c["id"], "name": c["name"], "reason": f"market value at the offer US${d['mcap_usd_bn']:.2f}bn, under the US$5bn threshold"})
            continue
        pf = (f.get("offer_price") or f.get("reference_price"))[0]
        deals.append({
            "id": c["id"], "name": c["name"], "ticker": c["ticker"], "region": c["region"], "exchange_ccy": c.get("exchange_ccy", ""),
            "ipo_date": d["listing_date"], "entry_month": em.get(c["ticker"], ""), "listing_type": c["listing_type"],
            "offer_price": f"{d['offer_price']:g}", "offer_price_unit": pf["unit"],
            "mcap_usd_bn_at_offer": f"{d['mcap_usd_bn']:.3f}",
            "revenue_last_fy_usd_bn": "" if d["revenue_usd_bn"] is None else f"{d['revenue_usd_bn']:.3f}",
            "operating_profit_positive": "" if d["profitable"] is None else str(int(d["profitable"])),
            "sector": d["sector"] or "", "financial": "" if d["financial"] is None else str(int(d["financial"])),
            "price_unit_divisor": c.get("price_unit_divisor") or "1", "entry_close_override": "",
            "offer_price_source": pf["source_url"], "verified": "yes",
            **({"dual_ah": c["dual_ah"]} if "dual_ah" in c else {}),
        })
    return deals, excluded


UNIVERSE_FILES = {"core": ("candidates.csv", "deals.csv", "excluded_manual.csv", "excluded.csv"),
                  "asia": ("candidates_asia.csv", "deals_asia.csv", "excluded_manual_asia.csv", "excluded_asia.csv")}


def write_tables() -> dict[str, tuple[int, int]]:
    """Rebuild data/deals*.csv and data/excluded*.csv from data/candidates*.csv and the facts."""
    facts, out = load_facts(), {}
    for name, (cand, deals_f, manual, excl) in UNIVERSE_FILES.items():
        c = list(csv.DictReader(open(DATA_DIR / cand, newline="", encoding="utf-8")))
        deals, excluded = build(c, facts)
        cols = DEAL_COLUMNS + (["dual_ah"] if "dual_ah" in c[0] else [])
        with open(DATA_DIR / deals_f, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(deals)
        man = list(csv.DictReader(open(DATA_DIR / manual, newline="", encoding="utf-8")))
        with open(DATA_DIR / excl, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["id", "name", "reason"])
            w.writeheader()
            w.writerows(man + excluded)
        out[name] = (len(deals), len(man) + len(excluded))
    return out
