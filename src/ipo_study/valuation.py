"""Traditional valuation of each IPO at its offer price.

Two methods, each with fixed rules applied identically to every deal, so anyone can
reproduce and challenge them:

1. Comparable multiples. The deal's own multiples at the offer (EV/EBITDA, EV/Sales, P/E,
   dividend yield; P/B for financials) are compared with the industry median for the IPO
   year and region (Damodaran's January industry datasets). Each multiple gives an implied
   equity value; the comps value is the median of those available.
2. Standardised DCF (free cash flow to the firm, 10 years + terminal value), with growth,
   margins, reinvestment and cost of capital all set by the rules in `DCFRules`.

Output per deal: fair equity value and the *valuation gap* = fair value / offer equity
value - 1. A positive gap means the IPO was priced below fair value ("cheap").

All money amounts are in millions of the deal's reporting currency. The offer equity value
is converted into that currency with `fx_listing_to_reporting`.
"""
from __future__ import annotations

import csv
import statistics as st
from dataclasses import dataclass, field
from pathlib import Path

from .data import DATA_DIR


# ----------------------------------------------------------------------------------------
# Inputs
# ----------------------------------------------------------------------------------------
@dataclass
class Fundamentals:
    """Last full fiscal year before the IPO, plus the post-IPO share count."""
    id: str
    revenue: float
    revenue_prior: float | None          # year before, for trailing growth
    ebitda: float | None
    ebit: float | None                   # operating income
    net_income: float | None
    dividends: float | None              # annual cash dividends (or stated payout policy x net income)
    cash: float                          # at the fiscal year end (pre-IPO)
    debt: float                          # total financial debt incl. leases if reported as debt
    primary_proceeds: float              # net IPO cash raised by the company (0 for a pure secondary sale)
    shares_post_ipo: float               # millions of shares outstanding after the offering
    fx_listing_to_reporting: float = 1.0 # units of reporting currency per unit of listing currency
    ads_ratio: float = 1.0               # ordinary shares per traded share/ADS
    marginal_tax: float = 0.25
    book_equity: float | None = None     # for financials (P/B)
    financial: bool = False
    source: str = ""

    @property
    def net_debt_post(self) -> float:
        return self.debt - self.cash - self.primary_proceeds


@dataclass
class Industry:
    """Industry medians for one industry, region and year."""
    name: str
    ev_ebitda: float | None = None
    ev_sales: float | None = None
    pe: float | None = None
    div_yield: float | None = None
    pbv: float | None = None
    wacc: float = 0.08
    op_margin: float = 0.10              # pre-tax operating margin
    sales_to_capital: float = 1.5
    market_wacc: float = 0.08            # "Total market" row: terminal cost of capital
    riskfree: float = 0.03               # long government bond yield at the start of the year


def _f(x):
    x = (x or "").strip()
    return float(x) if x not in ("", "NA", "na") else None


def load_fundamentals(path: Path | None = None) -> dict[str, Fundamentals]:
    path = path or DATA_DIR / "fundamentals.csv"
    out = {}
    if not path.exists():
        return out
    for r in csv.DictReader(open(path, newline="", encoding="utf-8")):
        if not (r.get("revenue") or "").strip():
            continue                     # template row not filled yet
        out[r["id"]] = Fundamentals(
            id=r["id"], revenue=float(r["revenue"]), revenue_prior=_f(r["revenue_prior"]), ebitda=_f(r["ebitda"]),
            ebit=_f(r["ebit"]), net_income=_f(r["net_income"]), dividends=_f(r["dividends"]), cash=_f(r["cash"]) or 0.0,
            debt=_f(r["debt"]) or 0.0, primary_proceeds=_f(r["primary_proceeds"]) or 0.0,
            shares_post_ipo=float(r["shares_post_ipo_m"]), fx_listing_to_reporting=_f(r["fx_listing_to_reporting"]) or 1.0,
            ads_ratio=_f(r["ads_ratio"]) or 1.0, marginal_tax=_f(r["marginal_tax"]) or 0.25,
            book_equity=_f(r["book_equity"]), financial=r.get("financial", "0") == "1", source=r.get("source_url", ""))
    return out


# ----------------------------------------------------------------------------------------
# Offer-price multiples and comps
# ----------------------------------------------------------------------------------------
def offer_equity_value(f: Fundamentals, offer_price: float) -> float:
    """Market value of equity at the offer, in millions of reporting currency."""
    return offer_price * f.shares_post_ipo / f.ads_ratio * f.fx_listing_to_reporting


def offer_multiples(f: Fundamentals, offer_price: float) -> dict:
    eq = offer_equity_value(f, offer_price)
    ev = eq + f.net_debt_post
    pos = lambda x: x is not None and x > 0
    return {
        "equity_value": eq, "enterprise_value": ev,
        "ev_ebitda": ev / f.ebitda if pos(f.ebitda) else None,
        "ev_sales": ev / f.revenue if pos(f.revenue) else None,
        "pe": eq / f.net_income if pos(f.net_income) else None,
        "div_yield": (f.dividends / eq) if pos(f.dividends) else None,
        "pbv": eq / f.book_equity if pos(f.book_equity) else None,
    }


def comps_value(f: Fundamentals, ind: Industry) -> dict:
    """Equity value implied by each industry multiple, and their median.

    Non-financials: EV/EBITDA and EV/Sales (minus net debt), P/E, and dividend yield.
    Financials: P/E, P/B and dividend yield (EV multiples are not meaningful for banks).
    A multiple is used only when the company's own metric is positive.
    """
    implied = {}
    pos = lambda x: x is not None and x > 0
    if not f.financial:
        if pos(f.ebitda) and pos(ind.ev_ebitda):
            implied["ev_ebitda"] = ind.ev_ebitda * f.ebitda - f.net_debt_post
        if pos(f.revenue) and pos(ind.ev_sales):
            implied["ev_sales"] = ind.ev_sales * f.revenue - f.net_debt_post
    elif pos(f.book_equity) and pos(ind.pbv):
        implied["pbv"] = ind.pbv * (f.book_equity + f.primary_proceeds)
    if pos(f.net_income) and pos(ind.pe):
        implied["pe"] = ind.pe * f.net_income
    if pos(f.dividends) and pos(ind.div_yield):
        implied["div_yield"] = f.dividends / ind.div_yield
    vals = [v for v in implied.values() if v > 0]
    return {"implied": implied, "value": st.median(vals) if vals else None, "methods": len(vals)}


# ----------------------------------------------------------------------------------------
# Standardised DCF
# ----------------------------------------------------------------------------------------
@dataclass
class DCFRules:
    years: int = 10
    high_growth_years: int = 5
    growth_cap: float = 0.40             # trailing growth above this is capped
    growth_floor: float = 0.0
    margin_rule: str = "midpoint"        # 'industry' | 'midpoint' | 'hold' (target for profitable firms)
    terminal_growth_cap: float = 0.04    # terminal growth = min(riskfree, cap)
    wacc_shift: float = 0.0              # for sensitivity runs
    growth_shift: float = 0.0


def dcf_value(f: Fundamentals, ind: Industry, rules: DCFRules | None = None) -> dict:
    """FCFF DCF. Returns enterprise value, equity value and the year-by-year path.

    Rules (identical for every deal):
      revenue growth: trailing growth (capped) for years 1-5, fading linearly to terminal growth by year 10;
      operating margin: moves linearly from the current margin to a target margin by year 10;
        target = industry margin for loss-makers; for profitable firms per `margin_rule`;
      taxes: marginal rate on positive EBIT after using accumulated losses;
      reinvestment: change in revenue / industry sales-to-capital;
      cost of capital: industry WACC for years 1-5, fading to the market WACC by year 10;
      terminal value: growth g = min(riskfree, cap); reinvestment rate g / ROIC with ROIC = terminal WACC.
    """
    R = rules or DCFRules()
    g_term = min(ind.riskfree, R.terminal_growth_cap) + R.growth_shift
    if f.revenue_prior and f.revenue_prior > 0:
        g0 = f.revenue / f.revenue_prior - 1
    else:
        g0 = g_term
    g0 = max(R.growth_floor, min(R.growth_cap, g0)) + R.growth_shift
    m0 = (f.ebit or 0.0) / f.revenue
    if m0 <= 0 or R.margin_rule == "industry":
        target = ind.op_margin
    elif R.margin_rule == "hold":
        target = m0
    else:
        target = (m0 + ind.op_margin) / 2
    rev, nol, pv, disc = f.revenue, 0.0, 0.0, 1.0
    path = []
    for t in range(1, R.years + 1):
        if t <= R.high_growth_years:
            g = g0
        else:
            k = (t - R.high_growth_years) / (R.years - R.high_growth_years)
            g = g0 + (g_term - g0) * k
        new_rev = rev * (1 + g)
        margin = m0 + (target - m0) * t / R.years
        ebit = new_rev * margin
        if ebit < 0:
            nol += -ebit
            tax = 0.0
        else:
            used = min(nol, ebit)
            nol -= used
            tax = (ebit - used) * f.marginal_tax
        reinvest = (new_rev - rev) / ind.sales_to_capital
        fcff = ebit - tax - reinvest
        if t <= R.high_growth_years:
            w = ind.wacc
        else:
            w = ind.wacc + (ind.market_wacc - ind.wacc) * (t - R.high_growth_years) / (R.years - R.high_growth_years)
        w += R.wacc_shift
        disc /= (1 + w)
        pv += fcff * disc
        path.append({"year": t, "revenue": new_rev, "growth": g, "margin": margin, "ebit": ebit, "tax": tax,
                     "reinvestment": reinvest, "fcff": fcff, "wacc": w})
        rev = new_rev
    w_t = ind.market_wacc + R.wacc_shift
    if w_t <= g_term:
        raise ValueError("terminal cost of capital must exceed terminal growth")
    ebit_t = rev * (1 + g_term) * target
    nopat_t = ebit_t * (1 - f.marginal_tax)
    fcff_t = nopat_t * (1 - g_term / w_t)
    tv = fcff_t / (w_t - g_term)
    pv_tv = tv * disc
    ev = pv + pv_tv
    equity = ev - f.net_debt_post
    return {"enterprise_value": ev, "equity_value": equity, "pv_explicit": pv, "pv_terminal": pv_tv,
            "terminal_share": pv_tv / ev if ev else None, "g0": g0, "g_terminal": g_term,
            "margin_now": m0, "margin_target": target, "path": path}


def value_deal(f: Fundamentals, ind: Industry, offer_price: float, rules: DCFRules | None = None) -> dict:
    eq = offer_equity_value(f, offer_price)
    c = comps_value(f, ind)
    out = {"offer_equity_value": eq, "multiples": offer_multiples(f, offer_price), "comps": c,
           "comps_gap": (c["value"] / eq - 1) if c["value"] else None}
    if f.financial or f.revenue <= 0:
        out["dcf"], out["dcf_gap"] = None, None   # FCFF not meaningful for financials or pre-revenue firms
    else:
        d = dcf_value(f, ind, rules)
        out["dcf"] = d
        out["dcf_gap"] = d["equity_value"] / eq - 1
        sens = {}
        for name, r in (("wacc_+1pt", DCFRules(wacc_shift=0.01)), ("wacc_-1pt", DCFRules(wacc_shift=-0.01)),
                        ("margin_industry", DCFRules(margin_rule="industry")), ("margin_hold", DCFRules(margin_rule="hold"))):
            sens[name] = dcf_value(f, ind, r)["equity_value"] / eq - 1
        out["dcf_gap_sensitivity"] = sens
    gaps = [g for g in (out["comps_gap"], out["dcf_gap"]) if g is not None]
    out["blended_gap"] = st.mean(gaps) if gaps else None
    return out
