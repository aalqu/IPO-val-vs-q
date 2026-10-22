"""Industry benchmarks from Aswath Damodaran's public datasets (NYU Stern).

`fetch()` downloads the January industry files for each (region, year) the deals need
into data/industry/raw/, and `build()` extracts one tidy table,
data/industry_benchmarks.csv, with the medians the valuation uses. Raw files are kept and
checksummed so anyone can confirm the numbers came from the published spreadsheets.

Needs: pip install xlrd openpyxl, and network access to pages.stern.nyu.edu.
"""
from __future__ import annotations

import csv
import hashlib
import re
import urllib.request
from pathlib import Path

from .data import DATA_DIR

BASE = "https://pages.stern.nyu.edu/~adamodar/pc/archives/"
REGION_TAG = {"US": "", "Europe": "Europe", "Japan": "Japan", "Emerging": "emerg", "Global": "Global",
              "China": "China", "India": "India"}
# dataset stem -> the columns we take from it (header text to match, lower-case, first match wins)
DATASETS = {
    "vebitda": {"ev_ebitda": ["ev/ebitda", "value/ebitda"], "n_firms": ["number of firms"]},   # pre-2010 files say "Value/..."
    "psdata": {"ev_sales": ["ev/sales", "value/sales"]},
    "pedata": {"pe": ["aggregate market cap/ aggregate net income", "aggregate mkt cap/ net income"]},   # aggregate P/E, not the simple average ("Current PE")
    "pbvdata": {"pbv": ["pbv", "price/bv", "price/book"]},
    "divfund": {"div_yield": ["dividend yield"]},
    "margin": {"op_margin": ["pre-tax unadjusted operating margin", "ebit/sales"]},
    "capex": {"sales_to_capital": ["sales/ invested capital", "sales/invested capital", "sales/capital"]},
    "wacc": {"wacc": ["cost of capital"]},
}
RAW = DATA_DIR / "industry" / "raw"
UA = "ipo-valuation-vs-quant research script (open-source replication)"


MAP_FILES = ("industry_map.csv", "industry_map_asia.csv")


def needed() -> list[tuple[str, int]]:
    out = set()
    for fn in MAP_FILES:
        if (DATA_DIR / fn).exists():
            out |= {(r["benchmark_region"], int(r["benchmark_file_year"])) for r in csv.DictReader(open(DATA_DIR / fn, newline=""))}
    out |= {(FALLBACK_REGION[reg], y) for reg, y in out if reg in FALLBACK_REGION}
    return sorted(out)


# Single-country files can have very few firms in an industry; below MIN_FIRMS the valuation
# uses the same industry from the wider region's file (see valuation_study.industry_for).
FALLBACK_REGION = {"China": "Emerging", "India": "Emerging"}
MIN_FIRMS = 10


# regional files drop the "data" suffix for these three
ALT_STEM = {"pedata": "pe", "psdata": "ps", "pbvdata": "pbv"}
HEADER_NAMES = ("industry name", "industry", "induistry name")   # the last is a typo in some files


def _name(stem: str, region: str, year: int, ext: str) -> str:
    if region != "US":
        stem = ALT_STEM.get(stem, stem)
    return f"{stem}{REGION_TAG[region]}{year % 100:02d}.{ext}"


def fetch() -> list[str]:
    RAW.mkdir(parents=True, exist_ok=True)
    log = []
    for region, year in needed():
        for stem in DATASETS:
            got = False
            for ext in ("xls", "xlsx"):
                fn = _name(stem, region, year, ext)
                dest = RAW / fn
                if dest.exists():
                    got = True
                    break
                try:
                    req = urllib.request.Request(BASE + fn, headers={"User-Agent": UA})
                    data = urllib.request.urlopen(req, timeout=30).read()
                    if data[:4] in (b"\xd0\xcf\x11\xe0", b"PK\x03\x04"):   # real xls / xlsx
                        dest.write_bytes(data)
                        got = True
                        break
                except Exception:
                    continue
            log.append(f"{region} {year} {stem}: {'ok' if got else 'MISSING'}")
    (RAW / "SHA256SUMS").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
                                            for p in sorted(RAW.glob('*.xls*'))))
    return log


def _rows(path: Path) -> list[list]:
    if path.suffix == ".xls":
        import xlrd
        book = xlrd.open_workbook(path)
        sheets = [book.sheet_by_index(i) for i in range(book.nsheets)]
        tables = [[[s.cell_value(r, c) for c in range(s.ncols)] for r in range(s.nrows)] for s in sheets]
        return max(tables, key=len)          # the industry table is the longest sheet
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    return max(([list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets), key=len)


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def parse(path: Path, wanted: dict[str, list[str]]) -> dict[str, dict[str, float]]:
    """industry name -> {field: value}. Locates the header row containing 'Industry Name'."""
    rows = _rows(path)
    hi = next(i for i, r in enumerate(rows) if r and _norm(r[0]) in HEADER_NAMES)
    header = [_norm(c) for c in rows[hi]]
    name_col = 0
    cols = {}
    for fld, cands in wanted.items():
        for cand in cands:
            idx = [i for i, h in enumerate(header) if h == cand] or \
                  ([i for i, h in enumerate(header) if h.startswith(cand)] if len(cand) > 8 else [])
            if idx:
                cols[fld] = idx[0]
                break
    out = {}
    for r in rows[hi + 1:]:
        name = str(r[name_col] or "").strip()
        if not name:
            continue
        vals = {}
        for fld, i in cols.items():
            v = r[i] if i < len(r) else None
            if isinstance(v, str):
                v = v.strip().rstrip("%")
                try:
                    v = float(v) / (100 if "%" in str(r[i]) else 1)
                except ValueError:
                    v = None
            vals[fld] = float(v) if isinstance(v, (int, float)) else None
        out[name] = vals
    return out


def build() -> Path:
    """Write data/industry_benchmarks.csv: one row per (region, file year, industry)."""
    table: dict[tuple, dict] = {}
    for region, year in needed():
        for stem, wanted in DATASETS.items():
            files = [RAW / _name(stem, region, year, e) for e in ("xls", "xlsx")]
            f = next((p for p in files if p.exists()), None)
            if not f:
                continue
            for ind, vals in parse(f, wanted).items():
                row = table.setdefault((region, year, ind), {"region": region, "file_year": year, "industry": ind})
                row.update({k: v for k, v in vals.items() if v is not None})
                row.setdefault("source_files", set()).add(f.name)
    out = DATA_DIR / "industry_benchmarks.csv"
    fields = ["region", "file_year", "industry", "n_firms", "ev_ebitda", "ev_sales", "pe", "pbv", "div_yield", "op_margin",
              "sales_to_capital", "wacc", "source_files"]
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for k in sorted(table):
            r = dict(table[k])
            r["source_files"] = " ".join(sorted(r["source_files"]))
            w.writerow({f: r.get(f, "") for f in fields})
    return out


def fetch_riskfree() -> Path:
    """US 10-year Treasury yield at the start of each year, from Damodaran's implied-ERP history
    (histimpl.xls). Written to data/riskfree.csv as year,riskfree."""
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / "histimpl.xls"
    if not dest.exists():
        req = urllib.request.Request("https://pages.stern.nyu.edu/~adamodar/pc/datasets/histimpl.xls", headers={"User-Agent": UA})
        dest.write_bytes(urllib.request.urlopen(req, timeout=30).read())
    rows = _rows(dest)
    hi = next(i for i, r in enumerate(rows) if any(_norm(c) == "year" for c in r))
    header = [_norm(c) for c in rows[hi]]
    yc = header.index("year")
    tc = next(i for i, h in enumerate(header) if h.startswith("t-bond rate") or h.startswith("t.bond rate"))
    out = DATA_DIR / "riskfree.csv"
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "riskfree", "source"])
        for r in rows[hi + 1:]:
            try:
                y, v = int(float(r[yc])), float(r[tc])
            except (TypeError, ValueError):
                continue
            # the file's year Y row holds the rate at the END of Y, i.e. the start of Y+1
            w.writerow([y + 1, v if v < 1 else v / 100, "Damodaran histimpl.xls, T-bond rate at end of prior year"])
    return out
