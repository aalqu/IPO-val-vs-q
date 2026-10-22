# Known data issues

Open items a reviewer should check. Each one is listed with its effect on the results.

1. **Valuation pilot (19 deals) is sourced; the other 77 deals are not.** Pilot inputs are in
   `data/fundamentals.csv` with prospectus links; `data/fundamentals_sec_extract.csv` holds the
   matching SEC XBRL values for cross-checking. Porsche is excluded: its accounts are on
   porsche.com, which this build could not reach.
1b. **Offer prices, market value at offer, revenue and profitability for the full 96 are not yet sourced.**
   `deals.csv` columns `offer_price_source` and `valuation_inputs_source` are blank and
   `verified` is `no` for every deal. Values are approximate prospectus-era figures.
   Effect: offer prices drive every "bought at offer" result; valuation inputs drive the
   traditional screens. `pytest tests/test_data.py -k provenance` reports coverage.
2. **Single price source.** Month-end closes come from one aggregator (digrin.com).
   `ipo-study fetch` rebuilds them from Yahoo Finance so anyone can cross-check;
   `ipo-study crosscheck` compares the two.
3. **Lineage (LINE)** uses approximate month-end prices (midpoint of each month's range).
4. **Five deals excluded** for lack of monthly history (`excluded.csv`).
5. **Global deals** are measured in local currency against MSCI ACWI in USD.
6. **Entry B** is the IPO month's last close, not the first-day close.
7. **Valuation pilot conventions** that a reviewer may want changed: trailing (not forward)
   multiples; basic post-IPO shares; industry classification in `data/industry_map.csv`
   (judgement calls, with an alternative listed); the standard DCF rules in `valuation.py`.
8. **Asian deal list is approximate.** Offer prices, $bn value at offer and revenues in
   `deals_asia.csv` are not yet tied to prospectuses (`verified = no`). The P/S screen in
   Asia uses these approximate revenues, so its result (cheap-on-P/S deals did better) is the
   least reliable Asian figure.
9. **Asian survivorship.** Sinovel (China A, delisted 2020) has no price history and is
   excluded; including it would make China A results worse. Haitong International (merged)
   and ESR (taken private) are also excluded.
10. **Second price source is not independent.** For the 10 deals in both studies, Yahoo and
    Digrin returns are identical, so Digrin appears to resell Yahoo-type data; the
    cross-check confirms transcription, not the underlying prices.
11. **Asian pilot conventions** differ from the US pilot (pre-IPO balance sheet plus
    proceeds; proceeds scaled from the mid-point price for three HK deals; Nongfu's pre-IPO
    dividend as debt; Xiaomi profit excluding fair-value items; minority interests as debt;
    India's EBIT excluding other income); see METHODOLOGY.md. Meituan's prospectus could not be
    retrieved. **Korea is not valued:** DART's search pages answer automated requests with a
    bot challenge and KIND returns 403, so the Korean pilot needs an OpenDART API key
    (free, opendart.fss.or.kr) to download filings through the official API.
11b. **Standard DCF rules misfire on some Asian deals.** Industry sales-to-capital ratios
    make fast-growing, asset-light Foxconn Industrial Internet worth less than nothing; India's
    listed online retailers were loss-making in January 2021, so the DCF converges Zomato and
    Nykaa to losses; CNNP's leverage leaves little equity. These are the rules applied
    uniformly, not judgement calls; the comps values are less extreme.
11c. **CATL dominates the means.** It beat the CSI 300 by about 20 times its offer price over
    three years, so any rule that bought it shows a huge mean; medians and hit rates are the
    figures to read.
12. **Xiaomi's list value ($54bn)** is fully diluted; the pilot's basic share count gives about $49bn.
