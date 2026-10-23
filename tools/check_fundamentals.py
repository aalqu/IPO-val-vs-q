"""For every number in data/fundamentals*.csv, look for it in the saved text of the source
document (prospectus, listing document or annual report). A value that is printed in the source
is 'found'; a value derived from printed components (for example EBIT = pre-tax income + interest)
must have every component listed in `notes` found instead. Prints one line per value."""
import csv, glob, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
FIELDS = ["revenue", "revenue_prior", "ebitda", "ebit", "net_income", "dividends", "cash", "debt", "primary_proceeds", "shares_post_ipo_m", "book_equity"]


def texts_for(row):
    id_ = row["id"]
    pats = [f"sec/prospectus/{id_}.txt", f"hk/ann/{id_}_*.txt", f"hk/{id_}.txt", f"hk/{id_}_*.txt", f"cn/{id_}.txt", f"cn/{id_}_*.txt",
            f"in/{id_}.txt", f"in/pros/{id_}.txt", f"global/{id_}_*.txt"]
    paths = [Path(p) for pat in pats for p in sorted(glob.glob(str(D / pat)))]
    out = " ".join(re.sub(r"\s+", " ", open(p, errors="ignore").read()) for p in paths)
    return out, [str(p.relative_to(ROOT)) for p in paths]


NUM = re.compile(r"(?<![0-9.,])\(?-?(?:[0-9]{1,3}(?:,[0-9]{2,3})+(?:\.[0-9]+)?|[0-9]{4,}(?:\.[0-9]+)?|[0-9]{1,3}\.[0-9]+)\)?(?![0-9])")
SCALES = {"millions": 1, "thousands": 1e-3, "units": 1e-6, "RMB 10,000s": 1e-2, "crore": 10, "lakh": 0.1}


def tokens(text):
    """Every printed number with at least four significant digits, as (value, printed form, position)."""
    out = []
    for m in NUM.finditer(text):
        raw = m.group(0)
        digits = re.sub(r"[^0-9]", "", raw).lstrip("0")
        if len(digits) < 4:
            continue
        v = float(raw.strip("()").replace(",", ""))
        out.append((abs(v), raw, m.start()))
    return out


LABELS = {
    "revenue": r"revenue|sales|收入",
    "revenue_prior": r"revenue|sales|收入",
    "ebit": r"operat|EBIT|before tax|利润",
    "ebitda": r"EBITDA|息税折旧",
    "net_income": r"net (?:income|profit|loss)|profit for|loss for|净利润|attributable",
    "cash": r"cash|货币资金|bank balances",
    "debt": r"debt|borrowings|loans|借款|notes",
    "dividends": r"dividend|股利|分红",
    "primary_proceeds": r"proceeds|募集",
    "shares_post_ipo_m": r"shares|股",
    "book_equity": r"equity|权益",
}


def match(stored: str, toks, text, field=None):
    """A printed number that, read in one of the usual units, rounds to the stored value. The row
    label must name the item (e.g. 'Revenue' for revenue) within the preceding 200 characters,
    unless the printed number has at least seven significant digits."""
    v = abs(float(stored))
    d = len(stored.split(".")[1]) if "." in stored else 0
    lab = re.compile(LABELS.get(field, "."), re.I)
    for name, sc in SCALES.items():
        for x, raw, pos in toks:
            if round(x * sc, d) == round(v, d) and abs(x * sc - v) <= max(0.5 * 10 ** -d, 1e-9) + 1e-9:
                sig = len(re.sub(r"[^0-9]", "", raw).lstrip("0"))
                if sig >= 7 or lab.search(text[max(0, pos - 200):pos]):
                    return f"{raw} ({name}) | " + text[max(0, pos - 70):pos + len(raw) + 15]
    return None


def xbrl_values():
    out = {}
    p = D / "fundamentals_sec_extract.csv"
    if p.exists():
        for r in csv.DictReader(open(p, newline="", encoding="utf-8")):
            if r["value"]:
                out.setdefault(r["id"], {})[r["field"]] = (float(r["value"]) / 1e6, r["xbrl_tag"], r["accession"])
    return out


def close(a, b, stored):
    d = len(stored.split(".")[1]) if "." in stored else 0
    return abs(a - b) <= 0.5 * 10 ** -d + 1e-6


def derivations():
    """data/fundamentals_derivations.csv: id, field, expression (printed numbers joined by + and -), scale (to millions), note."""
    out = {}
    p = D / "fundamentals_derivations.csv"
    if p.exists():
        for r in csv.DictReader(open(p, newline="", encoding="utf-8")):
            out[(r["id"], r["field"])] = r
    return out


def main():
    bad = 0
    X, DER = xbrl_values(), derivations()
    for f in ("fundamentals.csv", "fundamentals_asia.csv"):
        for r in csv.DictReader(open(D / f, newline="", encoding="utf-8")):
            if not (r.get("revenue") or "").strip():
                continue
            text, used = texts_for(r)
            toks = tokens(text)
            for k in FIELDS:
                v = (r.get(k) or "").strip()
                if not v or float(v) == 0:
                    continue
                hit = None
                x = X.get(r["id"], {})
                if (r["id"], k) in DER:
                    e = DER[(r["id"], k)]
                    expr = e["expression"]
                    lits = re.findall(r"[0-9][0-9,]*(?:\.[0-9]+)?", expr)
                    lits = [n for n in lits if not re.fullmatch(r"10*", n)]          # 100, 1000, 1000000: unit conversions
                    missing = [n for n in lits if not re.search(r"(?<![0-9.,])" + re.escape(n) + r"(?![0-9]|[.,][0-9])", text)]
                    total = eval(re.sub(r"(?<=[0-9]),(?=[0-9]{2,3})", "", expr), {"__builtins__": {}}) * float(e.get("scale") or 1)
                    if close(total, float(v), v) and not missing:
                        hit = f"derived: {e['expression']} ({e['note']})"
                    else:
                        print(f"# derivation check failed for {r['id']} {k}: total {total} vs {v}; not printed: {missing}", file=sys.stderr)
                elif k in x and close(x[k][0], float(v), v):
                    hit = f"SEC XBRL {x[k][1]} ({x[k][2]})"
                elif k == "ebitda" and "ebit" in x and "da" in x and close(x["ebit"][0] + x["da"][0], float(v), v):
                    hit = f"EBIT + D&A from SEC XBRL ({x['ebit'][1]} + {x['da'][1]})"
                else:
                    hit = match(v, toks, text, k)
                status = "found" if hit else "NOT FOUND"
                bad += hit is None
                print(f"{f}\t{r['id']}\t{k}\t{v}\t{status}\t{hit or ''}\t{';'.join(used) if not hit else ''}")
    print("not found:", bad, file=sys.stderr)


if __name__ == "__main__":
    main()
