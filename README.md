# Large-cap IPOs, 2010–2025: traditional valuation vs quant rules

An open, reproducible test of one question: **after a large company goes public, does a
fundamental read of its valuation tell you more about how it will perform than a simple
systematic rule does?**

The repository contains every input, every line of code that turns inputs into the
published numbers, and tests that fail if anything changes. You can rerun it in a minute,
change any assumption, or rebuild the price data from a second source.

## Findings (US + global, prices to 19 October 2026)

96 listings worth $5bn or more at the offer price (79 US, 17 global). Excess return = deal
return minus the S&P 500 (US) or MSCI ACWI (global) over the same months. Ranges are 95%
bootstrap intervals for the median.

| Finding | Number | 95% interval |
| --- | --- | --- |
| Allocation buyers' median gain, offer to first month-end | +14% | +10% to +26% |
| Median excess return, bought at first month-end: 6 months | −19 pts | −26 to −9 |
| … 1 year | −28 pts | −38 to −17 |
| … 3 years | −49 pts | −73 to −34 |
| Share of deals beating the index over 3 years after listing | 24% | 15% to 33% |
| Rank correlation of price-to-sales at offer with 3-year excess | +0.04 | (no signal) |
| Median 3-year excess from offer: profitable vs loss-making at IPO | −9 vs −60 pts | |
| Shorting the hottest third of deals: mean 3-year excess / right | +60 pts / 88% | right 73% to 100% |

**What holds up** in every variant below: buying after listing lagged the index, and
price-to-sales at the offer carried no reliable signal.

**What does not:** the hot-deal short. It depends on the 2020–21 boom. Without those two
years it earned +2 pts and was right 67% of the time; for 2010–2018 listings, −9 pts and 50%.

| Variant | Deals | Median 3y excess after listing | Beat index 3y | Median 3y from offer | Short hottest third: mean 3y | Right | P/S rank corr. 3y |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Base case | 96 | −49% | 24% | −38% | +60% | 88% | +0.04 |
| $10bn+ only | 77 | −50% | 21% | −39% | +68% | 90% | −0.04 |
| $25bn+ only | 35 | −47% | 21% | −33% | +69% | 90% | +0.18 |
| US only | 79 | −57% | 24% | −41% | +61% | 90% | +0.08 |
| Global only | 17 | −29% | 25% | −14% | +57% | 80% | +0.34 |
| Excluding 2020–21 | 64 | −34% | 30% | −19% | +2% | 67% | +0.19 |
| 2010–2018 listings | 32 | −10% | 34% | −2% | −9% | 50% | +0.15 |
| 2019–2025 listings | 64 | −76% | 17% | −41% | +63% | 88% | +0.11 |
| Without the 5 best winners | 91 | −52% | 19% | −40% | +75% | 96% | −0.12 |

Regenerate this table with `make robustness` (written to `results/robustness.md`).

## Asia extension (v1.2.0)

131 listings worth $5bn+ in Korea (10), India (28), Hong Kong (60) and mainland China
A-shares (33), each against its local index (KOSPI 200, Nifty 50, Hang Seng, CSI 300).

| Finding | Number | 95% interval |
| --- | --- | --- |
| Allocation buyers' median gain, offer to first month-end | +15% | +7% to +26% |
| Median excess return, bought at first month-end: 1 year | −15 pts | −25 to −7 |
| … 3 years | −25 pts | −36 to −12 |
| Share of deals beating the index over 3 years after listing | 32% | 24% to 42% |
| Shorting the hottest third: median 3-year excess / right | +35 pts / 74% | right 59% to 88% |

| Market | Deals | 1st-month gain | 3y excess after listing | Beat index 3y | Short hottest third: mean 3y / right |
| --- | --- | --- | --- | --- | --- |
| Korea | 10 | +27% | −35 | 10% | +76 / 100% |
| India | 28 | +18% | −40 | 31% | +16 / 50% |
| Hong Kong | 60 | +4% | −24 | 33% | +34 / 87% |
| China A | 33 | +47% | −12 | 39% | −71 / 67% |

The same lag shows up in every market. The hot-deal short is usually right but its mean
across Asia is −6 pts, because a few China A deals kept soaring. Unlike the US + global
study, IPOs that looked cheap on price-to-sales did better in Asia (based on approximate revenues).
A 15-deal comps/DCF pilot (Hong Kong, China A, India; Korea pending an OpenDART key) rated
most IPOs as priced rich. Unlike in the US pilot, the valuation gap pointed the right way (rank
correlation with 3-year excess from the offer +0.28 for comps, +0.47 for DCF). Comps rated four
deals cheap: CATL and Mindray (China A, where regulators held offer prices down) beat the index
many times over; HAL and Foxconn Industrial Internet lagged. Small sample, and CATL dominates.

```bash
ipo-study run --universe asia --bootstrap 2000   # results/asia/
ipo-study valuation --universe asia              # results/valuation_asia.json (15 deals)
```

## Reproduce it

Python 3.9+. The study uses only the standard library.

```bash
git clone https://github.com/YOUR-NAME/ipo-valuation-vs-quant
cd ipo-valuation-vs-quant
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

1. **Inputs.** `data/deals.csv` (the 96 deals), `data/prices.csv` (month-end closes),
   `data/benchmarks.csv`. Every file is pinned by `data/SHA256SUMS`, and a test fails if
   one changes.
2. **Every adjustment is logged.** Hand corrections are in `data/corrections.csv`.
   Splits and bonus issues that explain price adjustments are in
   `data/corporate_actions.csv`, with sources. A test fails if a price adjustment is
   unexplained.
3. **Known gaps** are listed in `data/known_issues.md`. The biggest: offer prices and
   valuation inputs are not yet linked to prospectus sources (`verified = no`).
4. **Formulas** are tested on hand-built examples you can check on paper
   (`tests/test_returns.py`).
5. **Published numbers** are locked by `tests/expected_headline.json`. If a correction
   changes them, the test fails until the change is reviewed and accepted with
   `make golden`, so every change to a headline figure is visible in the git history.

Found an error? Open an issue with the deal, field, correct value and a source link.

## Layout

```
data/        inputs, raw snapshot, corrections, corporate actions, known issues, checksums
src/ipo_study/
  data.py    loaders
  study.py   returns, valuation screens, quant rules  (every number comes from run())
  metrics.py summaries, rank correlation, bootstrap
  cli.py     `ipo-study` command and the robustness battery
  fetch.py   independent Yahoo Finance rebuild and cross-check
  site.py    builds the public page
tests/       unit, data-integrity and regression tests
results/     generated outputs (committed, so changes show in diffs)
site/        the public page: upload this folder to any web host
```

See [METHODOLOGY.md](METHODOLOGY.md) for definitions and [DATA.md](DATA.md) for sources and licensing.

## Licence and citation

Code: MIT. Text and results: CC BY 4.0. Third-party price data: see DATA.md.
Citation metadata: `CITATION.cff`. Not investment advice.
