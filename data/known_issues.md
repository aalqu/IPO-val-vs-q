# Known data issues

Open items a reviewer should check. Each one is listed with its effect on the results.

1. **Revenue and profitability are sourced for SEC filers only.** Last full-year revenue and
   operating profit come from SEC XBRL company facts. They are blank for the global and Asian
   deals (not yet extracted from their prospectuses), so the price-to-sales and profitable /
   loss-making screens use the 78 core deals with sourced revenue (80 with operating profit;
   P/S is not defined for financials, leaving 61 deals at 1 year and 51 at 3 years) and are
   not run for Asia.
   Blank means unknown: those deals are left out of the screens, not counted as loss-making.
2. **XBRL timing.** Revenue and operating profit for the last fiscal year before the IPO come
   from the earliest SEC filing that reports that year in XBRL. For most deals that is an
   annual report filed after the IPO (prospectuses are rarely tagged), so the figure is the one
   later reported for that year, not necessarily the prospectus figure.
3. **Listing dates.** The study uses only the listing month. Where no exchange or issuer
   document states the first dealing day, the date is Yahoo's first trade date (checked to be
   0–10 days after the final prospectus or pricing date) or, failing that, the date scheduled
   in the prospectus (HAL: scheduled 28 March 2018; Yahoo shows 2 April) or the prospectus
   date. Yahoo's first trade date can differ from the first session by a day; only the month
   is used.
4. **Direct-listing reference prices** come from news reports of the exchange's announcement
   (CNBC, Renaissance Capital), not from the exchange itself.
5. **Six cited documents have no local copy** (their hosts refuse automated downloads), so
   their quotes are not machine-checked: see `data/sources.csv` ("remote only").
6. **Single price source.** Monthly closes come from Yahoo Finance; nine delisted US tickers
   come from a digrin.com snapshot. Digrin's data matched Yahoo's exactly where both exist, so
   it is not an independent check.
7. **Excluded deals** (`data/excluded*.csv`): Glencore and ICICI Prudential Life (offering
   documents could not be retrieved), ZJLD (US$4.5bn at the offer on sourced numbers), six
   deals with no monthly prices at Yahoo Finance (First Data, Borouge, ADNOC Gas, Haitong
   Securities H, ESR, Sinovel; survivorship: a delisted loser is missing) and the Korean
   listings (scope decision).
8. **Candidate list.** The list of deals considered was compiled by hand. A large IPO missing
   from it is missing from the study; every listed deal's numbers are sourced.
9. **Global deals** are measured in local currency against MSCI ACWI in USD.
10. **Entry B** is the IPO month's last close, not the first-day close.
11. **Valuation pilot conventions** a reviewer may want changed: trailing (not forward)
    multiples; basic post-IPO shares; figures as reported (Xiaomi's 2017 loss includes the
    fair-value loss on its preferred shares, so its P/E is not defined); industry
    classification in `data/industry_map*.csv` (judgement calls, with an alternative listed);
    the standard DCF rules in `valuation.py`. Porsche is not valued (its accounts could not
    be retrieved in this build). Dividends enter only where the prospectus states an amount.
12. **Standard DCF rules misfire on some Asian deals.** Industry sales-to-capital ratios
    make fast-growing, asset-light Foxconn Industrial Internet worth less than nothing; India's
    listed online retailers were loss-making in January 2021, so the DCF converges Zomato and
    Nykaa to losses; CNNP's leverage leaves little equity. These are the rules applied
    uniformly, not judgement calls; the comps values are less extreme.
13. **CATL dominates the Asian means.** Any rule that bought it shows a huge mean; medians
    and hit rates are the figures to read.
