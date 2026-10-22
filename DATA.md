# Data: sources, provenance and licensing

| File | What it holds | Source |
| --- | --- | --- |
| `data/deals.csv` | 96 deals: offer price, market value, revenue, profitability, sector | Compiled by the author; **sources not yet filled** (`offer_price_source`, `valuation_inputs_source`) |
| `data/prices.csv` | Month-end adjusted and unadjusted closes at the months the study uses | digrin.com price-history pages, fetched 19 Oct 2026; Lineage from stockscan.io (approximate) |
| `data/benchmarks.csv` | SPY and ACWI adjusted closes, every month 2010-09 to 2026-10 | digrin.com |
| `data/raw/…snapshot…txt` | The prices exactly as read from the source pages | as above |
| `data/corrections.csv` | Every hand correction, with the reason | author |
| `data/corporate_actions.csv` | Splits and bonus issues that explain price adjustments | linked press releases and news |
| `data/excluded.csv` | Deals dropped and why | author |
| `data/deals_asia.csv` | 131 Asian deals (Korea, India, Hong Kong, China A), same columns plus `entry_month`, `dual_ah` | Compiled by the author; approximate, **sources not yet filled** |
| `data/prices_asia.csv` | Full monthly adjusted and unadjusted closes for the Asian deals | Yahoo Finance chart API, fetched Oct 2026; raw responses in `data/raw/yahoo/` |
| `data/benchmarks_asia.csv` | KODEX 200, Nifty BeES, Tracker Fund (2800.HK), CSI 300 ETF/index, monthly 2010–2026 | Yahoo Finance |
| `data/excluded_asia.csv` | Asian deals dropped and why | author |
| `data/fundamentals.csv`, `data/fundamentals_asia.csv` | Valuation pilot inputs, one row per deal with its prospectus link | SEC 424B4 / HKEX prospectuses |
| `data/industry_benchmarks.csv`, `data/riskfree.csv` | Industry multiples, margins, WACC by region and year; US 10-year yield | Damodaran (NYU Stern) January archives |
| `data/SHA256SUMS` | Checksums of all of the above | generated |

`prices.csv` holds only the month-ends the study needs (IPO month and months 5, 6, 7, 12,
18, 24 and 36 after it, plus the latest), not full histories. `ipo-study fetch` downloads
full monthly histories from Yahoo Finance into `data/independent/`.

## Licensing

The code and the derived results are open (see LICENSE). **The raw price data belongs to
its providers.** Before you publish this repository, check the terms of use of the price
source. If redistribution is not allowed, delete `data/prices.csv`,
`data/benchmarks.csv` and `data/raw/`, keep `data/SHA256SUMS` so others can confirm they
rebuilt the same files, and point readers to `make fetch`.

## Filling in provenance (the main open task)

For each row of `deals.csv`:

1. `offer_price_source`: the final prospectus (SEC 424B4 for US deals) or exchange
   announcement giving the offer price.
2. `valuation_inputs_source`: the prospectus pages giving shares outstanding (for market
   value), last-twelve-month revenue and operating income.
3. Correct any value that differs, log it in `corrections.csv`, set `verified = yes`.
4. Run `make test`; if headline numbers change, review the change and run `make golden`.

`ipo-study run --verified-only` runs the study on verified deals only, so the result can
be re-confirmed as provenance is filled in.
