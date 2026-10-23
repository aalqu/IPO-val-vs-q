"""Every number the study uses traces to a document.

* data/deal_facts.csv: one row per sourced value with the document URL, the document name and
  the exact words in it (`quote`). The deal tables (data/deals*.csv) must equal what
  `facts.build` computes from these facts and the identifier-only candidate lists.
* data/sources.csv maps each document to its saved text. Where that text is present locally
  (the large documents are not shipped in the repository; tools/fetch_sources.py downloads
  them), every quote must appear in it word for word.
* data/fundamentals*.csv (valuation pilot): every non-zero input is printed in the source,
  reported in SEC XBRL, or derived from printed numbers listed in
  data/fundamentals_derivations.csv (tools/check_fundamentals.py).
"""
import csv
import json
import re

import pytest

from ipo_study import facts
from ipo_study.data import DATA_DIR

ROOT = DATA_DIR.parent
FACTS = list(csv.DictReader(open(DATA_DIR / "deal_facts.csv", newline="", encoding="utf-8")))
SOURCES = {r["source_url"]: r for r in csv.DictReader(open(DATA_DIR / "sources.csv", newline="", encoding="utf-8"))}
_cache = {}


def _text(rel):
    if rel not in _cache:
        p = ROOT / rel
        _cache[rel] = re.sub(r"\s+", " ", p.read_text(encoding="utf-8", errors="ignore")) if rel and p.exists() else None
    return _cache[rel]


def test_every_fact_names_document_and_words():
    for r in FACTS:
        assert r["source_url"] and r["source_doc"] and r["quote"] and r["value"] != "", r


def test_every_document_is_mapped():
    assert {r["source_url"] for r in FACTS} <= set(SOURCES)


def test_quotes_appear_in_saved_documents():
    checked, absent, bad = 0, set(), []
    for r in FACTS:
        s = SOURCES[r["source_url"]]
        if s["kind"] in ("document text", "raw json", "fred csv"):
            t = _text(s["local_text"])
            if t is None:
                absent.add(s["local_text"])
                continue
            checked += 1
            if r["quote"] not in t:
                bad.append((r["id"], r["field"], r["quote"][:80], s["local_text"]))
    assert not bad, bad[:10]
    if absent and not checked:
        pytest.skip(f"source documents not downloaded ({len(absent)} files); run tools/fetch_sources.py")


def test_xbrl_and_profile_facts_match_saved_json():
    for r in FACTS:
        s = SOURCES[r["source_url"]]
        p = ROOT / s["local_text"] if s["local_text"] else None
        if not p or not p.exists():
            continue
        if s["kind"] == "xbrl json":
            tag = r["note"] or r["source_doc"].split("SEC XBRL ")[1].split(",")[0]
            tx, name = tag.split(":")
            start, end = re.search(r"period (\S+) to (\S+)", r["quote"]).groups()
            units = json.load(open(p))["facts"][tx][name]["units"]
            vals = {v["val"] for u in units.values() for v in u if v.get("start") == start and v["end"] == end}
            assert float(r["value"]) in {float(v) for v in vals}, (r["id"], r["field"])
        elif s["kind"] == "yahoo profile json":
            q = json.load(open(p))["quote"]
            assert r["value"] == q.get("sector") and r["quote"] == f"industry: {q.get('industry')}", r["id"]


def test_numbers_are_printed_in_their_quotes():
    """Offer prices and share counts appear in the quoted words (CN quotes in 万股/亿股 are
    checked in those units)."""
    for r in FACTS:
        if r["field"] not in ("offer_price", "reference_price") and not r["field"].startswith("shares_after_offering"):
            continue
        q, v = r["quote"].replace(",", ""), float(r["value"])
        forms = {f"{v:g}", f"{v:.2f}", f"{v:.1f}", f"{v:.0f}"}
        for unit in (1e4, 1e8):                                            # 万股, 亿股
            forms |= {f"{v / unit:.{d}f}".rstrip("0").rstrip(".") for d in range(5)}
        assert any(f in q for f in forms), (r["id"], r["field"], r["value"], r["quote"][:100])


def test_deal_tables_equal_what_the_facts_give():
    F = facts.load_facts()
    for cand, deals_file in (("candidates.csv", "deals.csv"), ("candidates_asia.csv", "deals_asia.csv")):
        c = list(csv.DictReader(open(DATA_DIR / cand, newline="", encoding="utf-8")))
        built, _ = facts.build(c, F)
        saved = list(csv.DictReader(open(DATA_DIR / deals_file, newline="", encoding="utf-8")))
        assert [dict(b) for b in built] == [dict(s) for s in saved], deals_file


def test_every_deal_is_5bn_or_more_on_sourced_numbers():
    for f in ("deals.csv", "deals_asia.csv"):
        for r in csv.DictReader(open(DATA_DIR / f, newline="", encoding="utf-8")):
            assert float(r["mcap_usd_bn_at_offer"]) >= facts.MIN_MCAP_USD_BN, r["id"]


def test_valuation_shares_equal_the_facts():
    F = facts.load_facts()
    for f in ("fundamentals.csv", "fundamentals_asia.csv"):
        for r in csv.DictReader(open(DATA_DIR / f, newline="", encoding="utf-8")):
            if r["revenue"]:
                assert abs(float(r["shares_post_ipo_m"]) - facts.derive(F[r["id"]])["shares_after"] / 1e6) < 1e-6, r["id"]


def test_fundamentals_are_traced():
    import subprocess, sys
    if not (DATA_DIR / "sec/prospectus/HCA.txt").exists():
        pytest.skip("source documents not downloaded; run tools/fetch_sources.py")
    out = subprocess.run([sys.executable, str(ROOT / "tools/check_fundamentals.py")], capture_output=True, text=True)
    assert "not found: 0" in out.stderr, out.stderr[-2000:]
