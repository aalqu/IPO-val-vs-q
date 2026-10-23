"""Download the source documents cited in data/deal_facts.csv (listed in data/sources.csv) and
save their text where tests/test_provenance.py looks for it. The repository ships only the small
files (prices, FX series, Yahoo responses); prospectuses and exchange announcements are fetched
from the issuer, regulator or exchange URL.

    python tools/fetch_sources.py            # everything missing
    python tools/fetch_sources.py HCA XIAOMI # only documents cited for these deals

Needs `pdftotext` (poppler) and `beautifulsoup4` + `lxml`. A few hosts refuse automated
downloads (they are listed as 'remote only' in data/sources.csv); open those URLs in a browser."""
import csv
import html
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
UA = {"User-Agent": "ipo-valuation-vs-quant replication (see README)",
      "Accept": "text/html,application/pdf,*/*"}


def get(url):
    for i in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180).read()
        except Exception as e:      # noqa: BLE001 - report and retry
            err = e
            time.sleep(2 + 3 * i)
    raise err


def to_text(raw: bytes, url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if raw[:5] == b"%PDF-":
        pdf = dest.with_suffix(".pdf")
        pdf.write_bytes(raw)
        subprocess.run(["pdftotext", "-layout", str(pdf), str(dest)], check=False)
    elif "sec.gov/Archives" in url:
        from bs4 import BeautifulSoup
        t = BeautifulSoup(raw, "lxml").get_text("\n")
        t = re.sub(r"[ \t\xa0]+", " ", t)
        dest.write_text(re.sub(r"\n\s*\n+", "\n", t), encoding="utf-8")
    else:
        t = raw.decode("utf-8", "ignore")
        t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
        t = html.unescape(re.sub(r"<[^>]+>", " ", t))
        dest.write_text(re.sub(r"\s+", " ", t), encoding="utf-8")


def main(ids):
    facts = list(csv.DictReader(open(D / "deal_facts.csv", newline="", encoding="utf-8")))
    wanted = {r["source_url"] for r in facts if not ids or r["id"] in ids}
    rows = [r for r in csv.DictReader(open(D / "sources.csv", newline="", encoding="utf-8")) if r["source_url"] in wanted]
    done = failed = 0
    for r in rows:
        if r["kind"] != "document text" or not r["local_text"]:
            continue
        dest = ROOT / r["local_text"]
        if dest.exists():
            continue
        try:
            to_text(get(r["source_url"]), r["source_url"], dest)
            done += 1
        except Exception as e:      # noqa: BLE001
            failed += 1
            print("failed:", r["source_url"], e, file=sys.stderr)
        time.sleep(0.3)
    print(f"downloaded {done}, failed {failed}")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
