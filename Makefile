PY ?= python3
RUN = PYTHONPATH=src $(PY) -m ipo_study

.PHONY: test results robustness site fetch crosscheck golden checksums all industry valuation pdf sec

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
	cd data && sha256sum deals.csv prices.csv benchmarks.csv corporate_actions.csv corrections.csv excluded.csv raw/digrin_monthly_snapshot_2026-10-19.txt fundamentals.csv industry_benchmarks.csv industry_map.csv riskfree.csv deals_asia.csv prices_asia.csv benchmarks_asia.csv excluded_asia.csv fundamentals_asia.csv industry_map_asia.csv > SHA256SUMS

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
