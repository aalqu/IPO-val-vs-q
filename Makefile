PY ?= python3
RUN = PYTHONPATH=src $(PY) -m ipo_study

.PHONY: test results robustness site fetch crosscheck golden checksums all industry valuation pdf sec facts sources audit

all: test results robustness site

test:            ## unit, data-integrity and regression tests
	PYTHONPATH=src $(PY) -m pytest -q

results:         ## rebuild results/ and results/asia/ (with 95% bootstrap intervals)
	$(RUN) run --bootstrap 2000
	$(RUN) run --universe asia --bootstrap 2000

robustness:      ## alternative specifications -> results/robustness.md
	$(RUN) robustness

site: results    ## rebuild site/index.html
	$(RUN) site

fetch:           ## re-download prices from Yahoo Finance (pip install yfinance)
	$(RUN) fetch

crosscheck: fetch ## compare snapshot returns with the Yahoo download
	$(RUN) crosscheck

checksums:       ## after a deliberate data change
	cd data && sha256sum candidates.csv candidates_asia.csv deal_facts.csv sources.csv deals.csv deals_asia.csv prices.csv prices_asia.csv benchmarks.csv benchmarks_asia.csv corporate_actions.csv corrections.csv excluded.csv excluded_asia.csv excluded_manual.csv excluded_manual_asia.csv raw/digrin_monthly_snapshot_2026-10-19.txt raw/fred/DEXHKUS.csv raw/fred/DEXCHUS.csv raw/fred/DEXINUS.csv raw/fred/DEXJPUS.csv raw/fred/DEXUSEU.csv raw/fred/DEXUSUK.csv fundamentals.csv fundamentals_asia.csv fundamentals_derivations.csv industry_benchmarks.csv industry_map.csv industry_map_asia.csv riskfree.csv > SHA256SUMS

facts:           ## rebuild data/deals*.csv and data/excluded*.csv from data/deal_facts.csv
	PYTHONPATH=src $(PY) -c "from ipo_study import facts; print(facts.write_tables())"

sources:         ## download the source documents cited in data/deal_facts.csv (large; not in git)
	$(PY) tools/fetch_sources.py

audit:           ## check every valuation input against its source document (needs make sources)
	$(PY) tools/check_fundamentals.py > data/fundamentals_check.tsv

golden:          ## after a reviewed change to data or code: accept the new headline numbers
	PYTHONPATH=src $(PY) -c "import json; from ipo_study.study import run, headline; json.dump(headline(run()), open('tests/expected_headline.json','w'), indent=1)"
	PYTHONPATH=src $(PY) -c "import json; from ipo_study.study import run, headline, Config; json.dump(headline(run(Config(universe='asia'))), open('tests/expected_headline_asia.json','w'), indent=1)"

industry:        ## download Damodaran industry multiples, margins, WACC (pip install xlrd openpyxl)
	$(RUN) industry

valuation:       ## comps + DCF value for each deal with fundamentals; tests vs returns -> results/valuation*.json
	$(RUN) valuation
	$(RUN) valuation --universe asia

pdf: results     ## shareable PDF -> reports/ipo-valuation-vs-quant.pdf (pip install playwright)
	$(RUN) pdf

sec:             ## re-download SEC XBRL facts for the pilot and rebuild the cross-check extract
	$(RUN) sec
