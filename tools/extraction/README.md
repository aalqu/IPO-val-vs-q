# Extraction scripts (as run)

The scripts that built `data/deal_facts.csv` from the source documents, kept for transparency.
They were run from the repository root in October 2026; each reads the downloaded documents
under `data/` and writes intermediate JSON that was merged into `data/deal_facts.csv`.

| Script | What it extracted |
| --- | --- |
| `sec_find.py`, `sec_dl.py` | Locate and download each US deal's final prospectus (424B4/424B1) |
| `us_offer_facts.py` | Hand-located quotes for US offer prices, share counts and ADS ratios (each checked to appear in the prospectus text) |
| `xbrl.py` | Last fiscal-year revenue and operating profit from SEC XBRL company facts |
| `gen_us_facts.py` | US fact rows |
| `hkex.py`, `hk_docs.py`, `hk_price.py`, `hk_extract2.py` | HKEXnews search and download; final offer prices |
| `gen_hk_facts.py` | Hong Kong fact rows (offer price, shares after the offering, listing date, H.10 rate) |
| `cninfo.py`, `cn_docs.py`, `cn_extract.py`, `gen_cn_facts.py`, `cn_rows.json` | CNINFO listing announcements; China A fact rows |
| `sebi.py`, `gen_nonus_facts.py` | Indian final prospectuses, global deals, exchange rates, sectors |
| `fred.py` | Federal Reserve H.10 rate on (or last before) a date |

The checks that matter are not these scripts but the tests: `tests/test_provenance.py`
confirms every quote is in its document and every number is in its quote, whatever produced it.
