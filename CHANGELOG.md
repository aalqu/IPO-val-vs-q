# Changelog

## 1.4.0 — 2026-10-23
Every number is now sourced; nothing is estimated or carried over from memory.
- New `data/deal_facts.csv`: 1,337 sourced values (offer price, shares after the offering,
  ADS ratio, dates, exchange rates, SEC revenue and operating profit, sector), each with the
  document URL, the document name and the exact words in it. `data/deals*.csv` are generated
  from these facts (`make facts`); `data/candidates*.csv` hold identifiers only.
- New tests (`tests/test_provenance.py`): every quote appears in its saved document, every
  offer price and share count is printed in its quote, the deal tables equal what the facts
  give, every deal is $5bn+ on sourced numbers, and every valuation input is printed in its
  source, reported in SEC XBRL or derived from printed numbers (`data/fundamentals_derivations.csv`,
  `tools/check_fundamentals.py`, evidence in `data/fundamentals_check.tsv`).
- `tools/fetch_sources.py` (`make sources`) downloads the ~670 cited documents;
  `tools/build_sources.py` maps each to its saved text (`data/sources.csv`).
- Market value at the offer = offer price × all shares after the offering (before
  over-allotment); exchange rates from the Federal Reserve H.10 (FRED) on the listing date.
- Corrections found by sourcing, among others: Facebook $81bn at the offer (was $104bn),
  Palantir, Coinbase, DoorDash and Airbnb smaller; SWS H-share price HK$3.63; Guosen A-share
  price RMB5.83; Galaxy A-share price RMB6.81; CGN A-share price RMB2.49.
- Universe: core 96 deals (Venture Global and SailPoint added, Glencore excluded: offering
  documents not retrieved); Asia 119 (Korea removed by scope decision; ICICI Prudential Life
  excluded, documents not retrieved; ZJLD excluded, US$4.5bn at the offer).
- Revenue and profitability come from SEC XBRL only; non-US deals are left out of the P/S and
  profitability screens instead of using approximate figures (none run for Asia).
- Valuation pilot: share counts equal the sourced facts (Kenvue 1,889m, HAL 334m); Hong Kong
  net proceeds are the amounts in the allotment-results announcements (no scaling from the
  mid-point price); Xiaomi as reported (no adjustments, no assumed tax); dividends only where
  the prospectus states an amount (payout-ratio policies no longer turned into forecasts);
  derived inputs recomputed exactly from printed numbers.
- Prices: pre-listing Yahoo bars dropped; SoftBank Corp price units fixed (Yahoo unadjusted
  close, divisor 1); the SoftBank 10-for-1 split documented.
- Headline changes (core): 6-month median excess −21 pts (was −19), 1-year −30 (was −28);
  3-year −49 unchanged. Asia: 3-year median −22 pts (was −25), 34% beat the index.

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
