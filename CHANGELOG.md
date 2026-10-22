# Changelog

## 1.3.0 — 2026-10-22
- Asian comps/DCF pilot extended from 5 Hong Kong deals to 15: five China A-share IPOs from
  CNINFO prospectuses and five Indian IPOs from prospectuses filed with SEBI.
- Industry benchmarks: Damodaran India files; same industry in the Emerging-markets file
  is now preferred to the alternative industry when a country file is thin; pre-2010 Damodaran
  headers ("Value/EBITDA", "Value/Sales") are read.
- Korea pilot pending: needs an OpenDART API key (DART's search blocks automated access).
- Core (US + global) results unchanged.

## 1.2.0 — 2026-10-20
- Asia extension: 131 listings worth $5bn+ in Korea, India, Hong Kong and China A-shares,
  with Yahoo Finance monthly prices (raw responses kept) and local index benchmarks.
  `ipo-study run --universe asia`.
- Hong Kong comps/DCF pilot (5 HKEX prospectuses) against Damodaran's China file, with an
  Emerging-markets fallback for industries with fewer than 10 Chinese firms.
  `ipo-study valuation --universe asia`.
- Site and PDF gain an Asia section; `tests/test_asia.py` locks the Asian headline numbers.
- `industry_benchmarks.csv` gains an `n_firms` column. Core (US + global) results unchanged.

## 1.1.0 — 2026-10-20
- Traditional valuation layer: comps (EV/EBITDA, EV/Sales, P/E, dividend yield, P/B) against
  Damodaran industry multiples, and a standard-rules DCF, for a pilot of 19 deals sourced from
  their final prospectuses and SEC XBRL data.
- Traditional valuation as buy rules, compared head-to-head with the quant rules on the same deals.
- `make industry`, `make valuation`, `make pdf` (shareable PDF report).

## 1.0.0 — 2026-10-20
- First public version: 96 deals, prices to 19 October 2026.
- Since the first write-up: 1-year median excess after listing is −28.5% (previously shown
  as −29% after rounding up; the exact value is −28.47%).
- Latest prices for LIC (Aug 2026) and Budweiser APAC (Sep 2026) are dated to the month
  the source actually showed.
- Added robustness battery: the hot-deal short does not survive excluding 2020–21.
