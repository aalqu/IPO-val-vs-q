# Large-cap IPOs, 2010–2025: traditional valuation vs quant rules

An open, reproducible test of one question: **after a large company goes public, does a
fundamental read of its valuation tell you more about how it will perform than a simple
systematic rule does?**

The repository contains every input, every line of code that turns inputs into the
published numbers, and tests that fail if anything changes. You can rerun it in a minute,
change any assumption, or rebuild the price data from a second source.

## Every number has a source

Each deal's offer price, share count, listing date and exchange rate is a row in
`data/deal_facts.csv` with the document it comes from (prospectus, exchange allotment or
listing announcement, Federal Reserve H.10 rate) and the exact words in that document. The deal
tables are generated from those rows (`make facts`), and the test suite checks that every quote
appears word for word in the saved document, that each number is printed in its quote, and that
the tables equal what the facts give. Nothing is estimated, interpolated or carried over from
memory: a value that cannot be sourced is left blank, and a deal whose size at the offer cannot
be computed is excluded (`data/excluded*.csv`, with the reason). Market value at the offer =
offer price × all shares outstanding after the offering, before any over-allotment.

## Findings (US + global, prices to 19 October 2026)

96 listings worth $5bn or more at the offer price (81 US, 15 global). Excess return = deal
return minus the S&P 500 (US) or MSCI ACWI (global) over the same months. Ranges are 95%
bootstrap intervals for the median.

| Finding | Number | 95% interval |
| --- | --- | --- |
| Allocation buyers' median gain, offer to first month-end | +14% | +9% to +25% |
| Median excess return, bought at first month-end: 6 months | −21 pts | −27 to −10 |
| … 1 year | −30 pts | −42 to −17 |
| … 3 years | −49 pts | −73 to −32 |
| Share of deals beating the index over 3 years after listing | 24% | 16% to 34% |
| Rank correlation of price-to-sales at offer with 3-year excess (51 deals with SEC revenue) | −0.00 | (no signal) |
| Median 3-year excess from offer: profitable vs loss-making at IPO (SEC filers) | −16 vs −54 pts | |
| Shorting the hottest third of deals: mean 3-year excess / right | +61 pts / 88% | right 76% to 100% |

**What holds up** in every variant below: buying after listing lagged the index, and
price-to-sales at the offer carried no reliable signal.

**What does not:** the hot-deal short. It depends on the 2020–21 boom. Without those two
years it earned −4 pts and was right 60% of the time; for 2010–2018 listings, −9 pts and 50%.

| Variant | Deals | Median 3y excess after listing | Beat index 3y | Median 3y from offer | Short hottest third: mean 3y | Right | P/S rank corr. 3y |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Base case | 96 | −49% | 24% | −38% | +61% | 88% | −0.00 |
| $10bn+ only | 76 | −51% | 20% | −39% | +72% | 90% | −0.10 |
| $25bn+ only | 32 | −43% | 23% | −33% | +58% | 80% | +0.30 |
| US only | 81 | −57% | 24% | −41% | +61% | 90% | −0.00 |
| Global only | 15 | −21% | 29% | −12% | +39% | 60% | |
| Excluding 2020–21 | 64 | −27% | 31% | −19% | −4% | 60% | +0.04 |
| 2010–2018 listings | 31 | −10% | 35% | −0% | −9% | 50% | −0.22 |
| 2019–2025 listings | 65 | −79% | 18% | −45% | +64% | 88% | +0.21 |
| Without the 5 best winners | 91 | −52% | 19% | −40% | +76% | 96% | −0.18 |

Regenerate this table with `make robustness` (written to `results/robustness.md`).
Price-to-sales and profitability use last full-year revenue and operating profit as reported in
SEC XBRL filings, so they cover SEC filers only; the global deals are left out of those screens.

## Asia extension

119 listings worth $5bn+ in India (27), Hong Kong (59) and mainland China A-shares (33), each
against its local index (Nifty 50, Hang Seng, CSI 300). Offer prices, share counts and listing
dates come from HKEXnews announcements and prospectuses, CNINFO listing announcements and the
final Indian prospectuses. Korean listings were removed (22 Oct 2026).

| Finding | Number | 95% interval |
| --- | --- | --- |
| Allocation buyers' median gain, offer to first month-end | +15% | +5% to +25% |
| Median excess return, bought at first month-end: 1 year | −15 pts | −25 to −8 |
| … 3 years | −22 pts | −36 to −9 |
| Share of deals beating the index over 3 years after listing | 34% | 25% to 44% |
| Shorting the hottest third: median 3-year excess / right | +28 pts / 70% | right 53% to 87% |

| Market | Deals | 1st-month gain | 3y excess after listing | Beat index 3y | Short hottest third: mean 3y / right |
| --- | --- | --- | --- | --- | --- |
| India | 27 | +21% | −45 | 27% | +16 / 50% |
| Hong Kong | 59 | +4% | −21 | 34% | +35 / 86% |
| China A | 33 | +74% | −12 | 39% | −68 / 67% |

The same lag shows up in every market. The hot-deal short is usually right but its mean
across Asia is −17 pts, because a few China A deals kept soaring. Revenues and profitability
are not yet extracted for these deals, so the price-to-sales and profitability screens are not
run for Asia. A 15-deal comps/DCF pilot (Hong Kong, China A, India) rated most IPOs as priced
rich; unlike in the US pilot, the valuation gap pointed the right way (rank correlation with
3-year excess from the offer +0.30 for comps, +0.43 for DCF). Comps rated five deals cheap:
CATL, Mindray, China National Nuclear Power and Foxconn Industrial Internet (China A) and HAL.
Small sample, and CATL dominates the means.

```bash
ipo-study run --universe asia --bootstrap 2000   # results/asia/
ipo-study valuation --universe asia              # results/valuation_asia.json (15 deals)
```

## Reproduce it

Python 3.9+. The study uses only the standard library.

```bash
git clone https://github.com/aalqu/IPO-val-vs-q
cd IPO-val-vs-q
pip install -e ".[test]"
make test          # arithmetic, data integrity, published numbers (US + global and Asia)
make results       # results/results.json, results/headline.json, results/deal_returns.csv
make robustness    # results/robustness.md
make site          # site/index.html: the public page, rebuilt from the results
```

Change an assumption:

```bash
ipo-study run --min-mcap 10 --region US --exclude-cohort 2020-21 --bootstrap 2000
ipo-study run --from-year 2010 --to-year 2018 --exclude NIO --exclude ARM
```

Rebuild prices independently and compare (needs internet):

```bash
pip install -e ".[fetch]"
make crosscheck    # downloads from Yahoo Finance, writes results/crosscheck.csv
```

## How to verify or challenge it

1. **Inputs.** `data/deal_facts.csv` (every sourced number, with document and quote),
   `data/candidates*.csv` (identifiers only), the generated `data/deals*.csv`,
   `data/prices.csv` (month-end closes) and `data/benchmarks.csv`. Every file is pinned by
   `data/SHA256SUMS`, and a test fails if one changes.
   `make sources` downloads the cited documents (about 2 GB; not stored in git) so the quote
   checks run locally; `make audit` traces every valuation input to its document.
2. **Every adjustment is logged.** Hand corrections are in `data/corrections.csv`.
   Splits and bonus issues that explain price adjustments are in
   `data/corporate_actions.csv`, with sources. A test fails if a price adjustment is
   unexplained.
3. **Known gaps** are listed in `data/known_issues.md`. The biggest: revenue and profitability
   for non-US deals are not yet extracted, and prices come from one source (Yahoo Finance).
4. **Formulas** are tested on hand-built examples you can check on paper
   (`tests/test_returns.py`).
5. **Published numbers** are locked by `tests/expected_headline.json`. If a correction
   changes them, the test fails until the change is reviewed and accepted with
   `make golden`, so every change to a headline figure is visible in the git history.

Found an error? Open an issue with the deal, field, correct value and a source link.

## Layout

```
data/        facts, candidates, generated deal tables, prices, corrections, corporate actions, known issues, checksums
src/ipo_study/
  data.py    loaders
  study.py   returns, valuation screens, quant rules  (every number comes from run())
  metrics.py summaries, rank correlation, bootstrap
  cli.py     `ipo-study` command and the robustness battery
  fetch.py   independent Yahoo Finance rebuild and cross-check
  facts.py   builds the deal tables from the sourced facts
  site.py    builds the public page
tools/       document download, source map and valuation-input audit
tests/       unit, data-integrity and regression tests
results/     generated outputs (committed, so changes show in diffs)
site/        the public page: upload this folder to any web host
```

See [METHODOLOGY.md](METHODOLOGY.md) for definitions and [DATA.md](DATA.md) for sources and licensing.

## Online

- Results page: https://aalqu.github.io/IPO-val-vs-q/ (GitHub Pages, built from `site/`)
- Shareable PDF: [`reports/ipo-valuation-vs-quant.pdf`](reports/ipo-valuation-vs-quant.pdf)

## Licence and citation

Code: MIT. Text and results: CC BY 4.0. Third-party price data: see DATA.md.
Citation metadata: `CITATION.cff`. Not investment advice.
