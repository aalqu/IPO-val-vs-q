"""Pull pre-IPO financials from SEC XBRL company facts (data.sec.gov).

For each deal, the last full fiscal year completed before the IPO. Every value is written
with the XBRL tag and the filing (accession number) it came from, so anyone can open the
filing and check it. Values the XBRL data cannot give reliably (shares outstanding right
after the IPO, net primary proceeds, announced dividend policy) come from the prospectus and
are entered by hand in data/fundamentals_manual.csv, each with a link.
"""
from __future__ import annotations

import csv
import json
import time
import urllib.request
from datetime import date
from pathlib import Path

from .data import DATA_DIR

UA = "ipo-valuation-vs-quant research (open-source replication) contact@example.com"
SEC_DIR = DATA_DIR / "sec"

# deal id -> (CIK, last fiscal year end before the IPO)
PILOT = {
    "HCA": (860730, "2010-12-31"), "ZTS": (1555280, "2012-12-31"), "HLT": (1585689, "2012-12-31"),
    "META": (1326801, "2011-12-31"), "TWTR": (1418091, "2012-12-31"), "BABA": (1577552, "2014-03-31"),
    "SYF": (1601712, "2013-12-31"), "RACE": (1648416, "2014-12-31"), "SNAP": (1564408, "2016-12-31"),
    "ZM": (1585521, "2019-01-31"), "UBER": (1543151, "2018-12-31"), "WMG": (1319161, "2019-09-30"),
    "SNOW": (1640147, "2020-01-31"), "ABNB": (1559720, "2019-12-31"), "CPNG": (1834584, "2020-12-31"),
    "RIVN": (1874178, "2020-12-31"), "KVUE": (1944048, "2023-01-01"), "ARM": (1973239, "2023-03-31"),
}

# field -> XBRL tags in priority order (us-gaap first, then IFRS)
TAGS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
                "SalesRevenueServicesGross", "HealthCareOrganizationRevenue", "RevenuesNetOfInterestExpense", "ifrs:Revenue"],
    "ebit": ["OperatingIncomeLoss", "ifrs:ProfitLossFromOperatingActivities"],
    "da": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "DepreciationAmortizationAndAccretionNet",
           "ifrs:DepreciationAndAmortisationExpense",
           "ifrs:DepreciationAmortisationAndImpairmentLossReversalOfImpairmentLossRecognisedInProfitOrLoss"],
    "net_income": ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic", "ProfitLoss",
                   "ifrs:ProfitLossAttributableToOwnersOfParent", "ifrs:ProfitLoss"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
             "ifrs:CashAndCashEquivalents"],
    "debt_total": ["LongTermDebt", "DebtLongtermAndShorttermCombinedAmount", "LongTermDebtAndCapitalLeaseObligations",
                   "ifrs:Borrowings"],
    "debt_noncurrent": ["LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations",
                        "ifrs:NoncurrentPortionOfNoncurrentBorrowings", "ifrs:LongtermBorrowings"],
    "debt_current": ["LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings", "ifrs:CurrentBorrowings",
                     "ifrs:CurrentPortionOfNoncurrentBorrowings", "ifrs:ShorttermBorrowings"],
    "book_equity": ["StockholdersEquity", "ifrs:EquityAttributableToOwnersOfParent"],
    "dividends_paid": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock", "ifrs:DividendsPaidClassifiedAsFinancingActivities"],
}
FLOW = {"revenue", "ebit", "da", "net_income", "dividends_paid"}


def download(ids=None) -> None:
    SEC_DIR.mkdir(parents=True, exist_ok=True)
    for i, (cik, _) in PILOT.items():
        if ids and i not in ids:
            continue
        dest = SEC_DIR / f"{i}.json"
        if dest.exists():
            continue
        req = urllib.request.Request(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", headers={"User-Agent": UA})
        dest.write_bytes(urllib.request.urlopen(req, timeout=60).read())
        time.sleep(0.2)                       # SEC fair-access limit is 10 requests/second


def _facts(doc, tag):
    ns, t = ("ifrs-full", tag[5:]) if tag.startswith("ifrs:") else ("us-gaap", tag)
    node = doc["facts"].get(ns, {}).get(t)
    if not node:
        return []
    out = []
    for unit, rows in node["units"].items():
        for r in rows:
            out.append({**r, "unit": unit, "tag": tag})
    return out


def _pick(doc, field, fy_end):
    """The value for the fiscal year ending fy_end (flows: a ~12-month period), as first reported."""
    for tag in TAGS[field]:
        cands = []
        for r in _facts(doc, tag):
            if r.get("end") != fy_end:
                continue
            if field in FLOW:
                if not r.get("start"):
                    continue
                days = (date.fromisoformat(r["end"]) - date.fromisoformat(r["start"])).days
                if not 350 <= days <= 380:
                    continue
            elif r.get("start"):
                continue
            cands.append(r)
        if cands:
            cands.sort(key=lambda r: r.get("filed", ""))     # earliest filing = as originally reported
            r = cands[0]
            return r["val"], r["tag"], r["unit"], r.get("accn", ""), r.get("form", "")
    return None


PRETAX = ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
          "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"]


def _pick_tags(doc, tags, end):
    saved = TAGS.get("_tmp")
    TAGS["_tmp"] = tags
    FLOW.add("_tmp")
    try:
        return _pick(doc, "_tmp", end)
    finally:
        TAGS.pop("_tmp")
        if saved is not None:
            TAGS["_tmp"] = saved


def _prior_year_end(fy_end: str) -> str:
    y, m, d = map(int, fy_end.split("-"))
    try:
        return date(y - 1, m, d).isoformat()
    except ValueError:                        # 29 Feb
        return date(y - 1, m, 28).isoformat()


def extract() -> Path:
    """Write data/fundamentals_sec_extract.csv: one row per (deal, field) with tag and filing."""
    out = DATA_DIR / "fundamentals_sec_extract.csv"
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "field", "fiscal_year_end", "value", "unit", "xbrl_tag", "accession", "form", "filing_url"])
        for i, (cik, fy) in PILOT.items():
            doc = json.loads((SEC_DIR / f"{i}.json").read_text())
            for field in TAGS:
                for label, end in ((field, fy), (field + "_prior", _prior_year_end(fy))):
                    if label.endswith("_prior") and field != "revenue":
                        continue
                    got = _pick(doc, field, end)
                    if not got and field == "ebit":   # no operating-income line: pre-tax income + interest expense
                        pt = _pick_tags(doc, PRETAX, end)
                        ie = _pick_tags(doc, ["InterestExpense", "InterestExpenseDebt"], end)
                        if pt and ie:
                            got = (pt[0] + ie[0], f"{pt[1]} + {ie[1]}", pt[2], pt[3], pt[4])
                    if got:
                        val, tag, unit, accn, form = got
                        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn.replace('-', '')}/" if accn else ""
                        w.writerow([i, label, end, val, unit, tag, accn, form, url])
                    else:
                        w.writerow([i, label, end, "", "", "", "", "", ""])
    return out
