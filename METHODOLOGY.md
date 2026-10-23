# Methodology

All definitions below are implemented in `src/ipo_study/study.py`; where this file and the
code disagree, the code is what produced the numbers, and that is a bug to report.

## Universe and sourcing

- Listings from 1 January 2010 to 31 December 2025 with market value of at least
  **$5bn at the offer price** (`mcap_usd_bn_at_offer`).
- **Candidates** (`data/candidates*.csv`) hold identifiers only: id, name, ticker, region,
  listing currency, listing type, A+H flag. Every number comes from `data/deal_facts.csv`.
- **Sourced facts** (`data/deal_facts.csv`, one row per value): the value, its unit, the
  document URL, the document name and the exact words in it.
  - Offer price: final prospectus (SEC 424B4/424B1), exchange allotment-results or offer-price
    announcement (HKEXnews), A-share listing announcement (CNINFO), final Indian prospectus, or
    the issuer's or exchange's pricing announcement. Direct listings: the exchange reference
    price as reported (news reports; marked in the source column).
  - Shares outstanding after the offering, before over-allotment, all share classes (A+H
    companies: A plus H; ADS deals divide by the ADS ratio). Where an offer-size adjustment
    option was exercised, the total after it.
  - Listing date, in order of preference: a first-dealing date stated by the exchange or the
    issuer; Yahoo Finance's first trade date when it is 0–10 days after the final prospectus
    or pricing date; the commencement of trading scheduled in the final prospectus; the final
    prospectus date.
  - Exchange rate: Federal Reserve H.10 noon buying rate (FRED) on the listing date, or the
    last rate published before it; the prospectus peg for SAR and AED.
  - Revenue and operating profit, last full fiscal year before the listing: SEC XBRL company
    facts (earliest filing reporting that year). Not yet extracted for non-US deals (blank).
  - Sector: Yahoo Finance; financial = Yahoo sector "Financial Services" (SEC SIC 6000–6411
    when Yahoo has no profile).
- `facts.build` turns facts into `data/deals*.csv`. A deal whose market value cannot be
  computed from facts, or is under $5bn, goes to `data/excluded*.csv` with the reason.
- **US:** NYSE and Nasdaq, including five direct listings (Spotify, Slack, Palantir, Roblox,
  Coinbase), which use the reference price in place of an offer price and are excluded from
  every "bought at offer" statistic.
- **Global:** 15 mega-listings in Hong Kong, Tokyo, Frankfurt, Riyadh, Dubai and Mumbai.

## Prices and returns

- Month-end closes. **Adjusted** closes (splits and dividends) drive all returns;
  **unadjusted** closes are used once, for the first month-end price compared with the offer.
- `m0` = the IPO month. Horizon `h` = the month-end `h` months later.
- **From first month-end:** `R_after(h) = adj(m0+h) / adj(m0) − 1`.
- **From offer:** `R_offer(h) = (close(m0) / offer) × (1 + R_after(h)) − 1`.
- **Benchmark:** S&P 500 (SPY, total return) for US deals, MSCI ACWI (total return, USD) for
  global deals, over the same months. `Excess = R − R_benchmark` (buy-and-hold, as in
  Ritter's long-run IPO studies). Global deals are measured in local currency.
- **Since listing:** for deals still trading at the snapshot and listed 5+ years ago, the
  annualised deal return minus the annualised benchmark return.

## Traditional valuation screens (buy at the offer)

- **Profitable / loss-making:** operating profit positive in the last fiscal year before IPO.
- **Price-to-sales (P/S):** market value at offer ÷ last full fiscal year's revenue (SEC XBRL).
  Not defined for financials (`financial = 1`) or where revenue is not sourced.
- Deals without sourced revenue or operating profit are left out of these screens (not
  counted as loss-making).
- **Cheap / expensive:** P/S at or below / above the sample median.
- **Signal test:** Spearman rank correlation of P/S with later excess return.

## Quant rules

Reconstructed from published research; not any fund's actual strategy. Short-side payoffs
are `−excess`. No trading or borrowing costs.

| Rule | Definition |
| --- | --- |
| Flip allocation | Buy at offer, sell at first month-end (raw return, not excess) |
| Short new-issue basket | Short every deal at first month-end against the index; hold 6/12/36 months |
| Hot-deal fade | Rank priced IPOs on offer → first month-end gain; terciles. Short the top third, long the bottom third |
| Lock-up window | Short at month 5, cover at month 7 (lock-ups usually expire near day 180) |
| Post-lock-up momentum | At month 6, rank on return since offer; long top third, short bottom third, hold to month 12 or 18 |
| Wait for lock-up | Buy at month 6, hold 12 months; compare with buying at month 0 |

## Statistics

Equal-weighted means and medians; hit rate = share of deals with positive excess;
t-statistic of the mean; percentile bootstrap (2,000 draws, seed 7) for 95% intervals of the
median and hit rate. Deals are not independent (listings cluster in hot markets), so
intervals are optimistic.

## Known limitations

In-sample; small groups (26–32 deals per tercile); 2020–21 dominates; month-end rather than
first-day prices; one price source; revenue and profitability not yet sourced for non-US deals.
See `data/known_issues.md`.

## Traditional valuation at the offer (v1.1, pilot of 19 deals)

Implemented in `src/ipo_study/valuation.py`. Each rule is applied the same way to every
deal; `tests/test_valuation.py` checks each formula on hand-worked numbers.

**Inputs** (`data/fundamentals.csv`, one row per deal, millions of reporting currency):
last fiscal year before the IPO — revenue (and the year before), EBITDA, operating income,
net income, dividends, cash, debt; net primary proceeds; post-IPO shares; ADS ratio and FX
where the listing currency differs. Every row cites its prospectus. Every non-zero input is
printed in the source document, reported in SEC XBRL, or derived from printed numbers listed in
`data/fundamentals_derivations.csv`; `make audit` (tools/check_fundamentals.py) checks each one
and writes the evidence to `data/fundamentals_check.tsv`. Post-IPO shares equal the sourced
share count in `data/deal_facts.csv` (tested).

**Offer value:** equity = offer price × post-IPO shares; EV = equity + debt − cash − primary proceeds.

**Comparable multiples:** the industry multiple for the IPO year and region, from Damodaran's
January dataset of that year (aggregate ratios, e.g. total EV / total EBITDA; P/E = aggregate
market cap / aggregate net income, not the outlier-prone simple average) (`data/industry_benchmarks.csv`, built from the raw files in
`data/industry/raw/`). Implied equity value:

| Multiple | Implied equity value | Used when |
| --- | --- | --- |
| EV/EBITDA | industry EV/EBITDA × EBITDA − net debt | EBITDA > 0, non-financials |
| EV/Sales | industry EV/Sales × revenue − net debt | non-financials |
| P/E | industry P/E × net income | net income > 0 |
| Dividend yield | dividends ÷ industry yield | dividends > 0 |
| P/B | industry P/B × (book equity + proceeds) | financials only |

Comps value = median of the available implied values.

**Standard DCF (FCFF, 10 years + terminal):**
- Revenue growth: trailing growth (capped at 40%, floored at 0) for years 1–5, fading
  linearly to terminal growth by year 10. Terminal growth = min(US 10-year yield, 4%).
- Operating margin: moves linearly from today's margin to a target by year 10. Target =
  industry margin for loss-makers; for profitable firms, halfway between own and industry
  margin (sensitivities: all the way to industry, or held).
- Tax: marginal rate on positive operating income after using accumulated losses.
- Reinvestment: change in revenue ÷ industry sales-to-capital.
- Discount rate: industry cost of capital for years 1–5, fading to the market average by
  year 10. Terminal reinvestment = g ÷ ROIC, ROIC = terminal cost of capital.
- Financials are valued by comps only.

**Valuation gap** = fair equity value ÷ offer equity value − 1 (positive = priced cheap).
Reported for comps, DCF and their average.

**Test:** rank correlation of each gap with later excess return (6, 12, 36 months; from the
offer and from the first month-end), and cheap-vs-rich medians. The quant rules are rerun on
the same deals so both sides are judged on identical samples.

**Traditional rules (buy when the valuation looks attractive at the offer):** dividend yield
above industry; P/E, EV/EBITDA, EV/Sales (or P/B for financials) below industry; comps value
above the offer value; DCF value above the offer value; both. Each is tested buying at the offer
and at the first month-end, held 6, 12 and 36 months.

**Input conventions:** last full fiscal year before the IPO, as first reported; cash and debt
from the prospectus capitalization table "as adjusted" for the offering (so primary proceeds are
already included); post-IPO shares from "The Offering" section (basic, excluding options and
RSUs); dividends = a per-share amount stated in the prospectus × 4 quarters × post-IPO shares
(blank when the prospectus states only a payout ratio, which would need a profit forecast);
currency rates as stated in the prospectus. Marginal tax: the statutory corporate income tax rate for the company's country and the IPO year
(Tax Foundation, combined central and sub-national rate; `data/raw/taxfoundation/`).

## Asia extension

Run with `ipo-study run --universe asia` (`Config(universe="asia")`); every definition above
applies unchanged. Implemented through `data/candidates_asia.csv` → `data/deals_asia.csv`,
`data/prices_asia.csv` and `data/benchmarks_asia.csv`.

- **Universe:** 119 listings worth **$5bn+ at the offer**, 2010–2025: India (NSE/BSE, 27),
  Hong Kong (59, including H-shares of mainland companies) and mainland China A-shares
  (Shanghai/Shenzhen, 33). `dual_ah` tags companies that list both A- and H-shares. Korean
  listings were removed on 22 Oct 2026. Exclusions with reasons: `data/excluded_asia.csv`.
- **Sources:** Hong Kong offer prices from the allotment-results or offer-price announcement
  and share counts from the prospectus (market-capitalisation note or share-capital table) or,
  since 2023, the allotment announcement's "number of issued shares upon listing"; China A
  offer prices, share counts and listing dates from the CNINFO listing announcement (上市公告书);
  India from the final prospectus filed with the Registrar of Companies.
- **Prices:** Yahoo Finance monthly bars (raw responses saved in `data/raw/yahoo/`).
  Yahoo's monthly close is split-adjusted, so the unadjusted close is rebuilt by undoing
  later splits and bonus issues; a test rebuilds every row of `prices_asia.csv` from the raw files.
- **Benchmarks (total return, local currency):** India — Nippon Nifty BeES (Nifty 50);
  Hong Kong — Tracker Fund of Hong Kong (Hang Seng); China A — Huatai-PineBridge CSI 300 ETF
  from May 2012, chained to the CSI 300 price index before that. ETF returns are after their
  small fees.
- **Late first bars:** where Yahoo's history starts the month after listing (HAL, Midea H),
  the entry month is the first available month (`entry_month`, logged in `corrections.csv`).
- **Market splits:** per-market rows re-rank the "hottest third" within that market.
- **Not yet sourced:** revenue and operating profit, so the price-to-sales and profitability
  screens are not run for Asia.

### Asian valuation pilot (15 deals)

Same comps and DCF rules as the US pilot, applied to five deals in each of Hong Kong (Xiaomi,
China Tower, Haidilao, Smoore, Nongfu Spring; HKEX prospectuses and allotment announcements),
China A (CNNP, Foxconn Industrial Internet, CATL, Mindray, Beijing–Shanghai High-Speed Railway;
CNINFO prospectuses) and India (Coal India, HAL, Zomato, Nykaa, Paytm; final prospectuses)
(`data/fundamentals_asia.csv`, `data/industry_map_asia.csv`). Figures are as reported, with no
analyst adjustments. Differences from the US convention, forced by what these prospectuses report:

- Cash and debt are the latest **pre-IPO** balance (indebtedness statement), so net primary
  proceeds are added: the net proceeds at the final offer price stated in the allotment-results
  announcement (Hong Kong) or listing announcement (China A), translated at the prospectus rate.
- Pre-IPO special dividends declared before listing are counted as debt (Nongfu).
- **EBIT** = profit before tax + interest expense (China A, Hong Kong), or profit before tax −
  other income + finance costs (India, where other income is mostly interest on cash).
  **EBITDA** = the prospectus's own figure where stated (China A prospectuses report
  息税折旧摊销前利润; China Tower), else EBIT + depreciation and amortisation.
- **Minority interests** are added to debt (material for CNNP and CATL), because EBITDA
  and EV/Sales cover the whole group while the offer value is the parent's equity.
- **India:** cash includes bank deposits and liquid investments; debt is borrowings
  (lease liabilities excluded). Coal India and HAL were all-secondary government sales, so
  no proceeds are added.
- **Dividends:** none of these prospectuses states a dividend amount (only payout ratios), so
  the dividend-yield comparison is not computed for the Asian pilot.
- Mindray's prospectus PDF is a scanned image, so its FY2017 figures come from the
  comparatives in its 2018 annual report.
- Industry benchmarks come from Damodaran's **China** and **India** files; where China has fewer than
  10 firms in the industry, the **Emerging-markets** file for that industry is used
  (`industry.MIN_FIRMS`, `FALLBACK_REGION`); the same industry in the wider file is tried
  before the alternative industry. CNNP uses the 2014 Emerging-markets file (no China file
  that year); Coal India uses the US January 2010 file (no India or Emerging-markets file
  before the 2011 edition, which post-dates the IPO). Discount rates are Damodaran's (US-dollar based)
  and the terminal growth rate is the US 10-year yield, applied to RMB cash flows; a
  reviewer may prefer an RMB risk-free rate.
