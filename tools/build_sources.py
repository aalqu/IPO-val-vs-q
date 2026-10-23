"""Map every source document cited in data/deal_facts.csv to its saved local copy and write
data/sources.csv (source_url, local_text, kind). The local copies (PDF text, HTML text, JSON, CSV)
are what tests/test_provenance.py searches for each quote. Run after adding facts."""
import csv, glob, json, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"


def norm(p):
    return re.sub(r"\s+", " ", open(p, errors="ignore").read())


def candidates(id_):
    pats = [f"sec/prospectus/{id_}.txt", f"hk/ann/{id_}_*.txt", f"cn/{id_}*.txt", f"in/pros/{id_}*.txt", f"in/{id_}*.txt", f"global/{id_}_*.txt", f"web/{id_}_*.txt"]
    return [Path(p) for pat in pats for p in sorted(glob.glob(str(D / pat)))]


def main():
    facts = list(csv.DictReader(open(D / "deal_facts.csv", newline="", encoding="utf-8")))
    by_url = defaultdict(set)
    hk = json.load(open(D / "hk/hkex_docs.json"))
    hk_url = {d["url"]: re.sub(r"\.pdf$", ".txt", d["path"], flags=re.I) for v in hk.values() for d in v["docs"]}
    hk_url["https://www1.hkexnews.hk/listedco/listconews/sehk/2019/1008/ltn20191008751.pdf"] = "data/hk/ann_extra/BUDAPAC_mr201909.txt"
    rows, cache = {}, {}
    for r in facts:
        u = r["source_url"]
        if u in rows:
            continue
        if u.startswith("data/raw/"):
            rows[u] = (u, "raw json")
        elif "fred.stlouisfed.org/series/" in u:
            rows[u] = (f"data/raw/fred/{u.rsplit('/', 1)[1]}.csv", "fred csv")
        elif "data.sec.gov/api/xbrl/companyfacts" in u:
            rows[u] = ("data/sec/companyfacts/" + u.rsplit("/", 1)[1], "xbrl json")
        elif "finance.yahoo.com/v1/finance/search" in u:
            t = re.search(r"q=([^&]+)", u).group(1)
            rows[u] = (f"data/raw/yahoo_profile/{t}.json", "yahoo profile json")
        elif "data.sec.gov/submissions/" in u:
            rows[u] = ("data/sec/submissions/" + u.rsplit("/", 1)[1], "sec submissions json")
        elif u in hk_url:
            rows[u] = (hk_url[u], "document text")
    # remaining URLs: find the local text that contains the quotes cited from that URL
    pending = defaultdict(list)
    for r in facts:
        if r["source_url"] not in rows:
            pending[r["source_url"]].append(r)
    for u, rs in pending.items():
        found = None
        for p in candidates(rs[0]["id"]):
            if p not in cache:
                cache[p] = norm(p)
            if all(x["quote"] in cache[p] for x in rs if x["quote"]):
                found = p
                break
        rows[u] = (str(found.relative_to(ROOT)) if found else "", "document text" if found else "remote only (no local copy)")
    with open(D / "sources.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source_url", "local_text", "kind"])
        for u, (p, k) in sorted(rows.items()):
            w.writerow([u, p, k])
    print(len(rows), "sources;", sum(1 for p, k in rows.values() if not p), "without a local copy")


if __name__ == "__main__":
    main()
