import csv
R='./'
_c={}
def rate(series, iso):
    """FRED/H.10 rate on the listing date, or the last published rate before it (H.10 has no
    rate on US holidays). Returns (date, value_str, csv_line)."""
    if series not in _c:
        _c[series]=[(r[0],r[1]) for r in csv.reader(open(R+f'data/raw/fred/{series}.csv')) if r[0][:1].isdigit() and r[1] not in ('','.')]
    best=None
    for d,v in _c[series]:
        if d<=iso: best=(d,v)
        else: break
    return best[0],best[1],f'{best[0]},{best[1]}'
def row(id_,series,iso):
    d,v,line=rate(series,iso)
    inv=series in ('DEXUSUK','DEXUSEU')
    return dict(id=id_,field='fx_usd_per_listing' if inv else 'fx_listing_per_usd',value=v,
        unit={'DEXHKUS':'HKD per USD','DEXCHUS':'CNY per USD','DEXINUS':'INR per USD','DEXJPUS':'JPY per USD','DEXUSUK':'USD per GBP','DEXUSEU':'USD per EUR'}[series],
        source_url=f'https://fred.stlouisfed.org/series/{series}',source_doc=f'Federal Reserve H.10 noon buying rate via FRED, series {series} (file data/raw/fred/{series}.csv)',
        quote=line,note='Rate on the listing date' if d==iso else f'Last published rate before the listing date ({iso})')
