import re, json, csv, sys, os, datetime
sys.path.insert(0, 'tools/extraction')
from us_offer_facts import F, DL, DATES_EXTRA, FX, MANUAL_FIN
R='./'
D=R+'data/sec/prospectus/'
idx=json.load(open(D+'index_us.json'))
dates=json.load(open('tools/extraction/us_dates.json'))
xb=json.load(open(R+'data/sec/xbrl_us_lastfy.json'))
deals={r['id']:r for r in csv.DictReader(open(R+'data/candidates.csv'))}
rows=[]; bad=[]
def fmt(v):
    return [f"{v:,.0f}", f"{v:.2f}", f"{v:,.2f}", f"{v:g}", f"{v:.4f}", f"{v:.1f}"]
def flat_of(id_): return re.sub(r'\s+',' ',open(D+f'{id_}.txt').read())
def row(id_,field,value,unit,url,doc,quote,note=''):
    rows.append(dict(id=id_,field=field,value=value,unit=unit,source_url=url,source_doc=doc,quote=quote,note=note))
for id_ in idx:
    m=idx[id_]; flat=flat_of(id_)
    doc=f"SEC {m['form']} filed {m['filed']} (accession {m['accession']})"
    def q(field,value,quote,unit,check=True,note=''):
        if quote not in flat: bad.append((id_,field,'quote missing')); return
        if check and not any(s in quote for s in fmt(float(value))): bad.append((id_,field,'value not in quote',value)); return
        row(id_,field,value,unit,m['url'],doc,quote,note)
    price,pq,shares,ads,aq = F[id_]
    if price is not None: q('offer_price',price,pq,'USD per ADS' if ads else 'USD per share')
    else:
        p,url,quote=DL[id_]; row(id_,'reference_price',p,'USD per share',url,'web page (exchange reference price for the direct listing)',quote)
    for i,(v,qq) in enumerate(shares): q(f'shares_after_offering_{i+1}',v,qq,'shares')
    if ads is not None: q('ordinary_shares_per_ads',ads,aq,'shares per ADS',check=False)
    d=dates.get(id_) or DATES_EXTRA.get(id_)
    if id_ in DATES_EXTRA: d=DATES_EXTRA[id_]
    if d:
        val=datetime.datetime.strptime(d[0].replace('  ',' '),'%B %d, %Y').date().isoformat() if ',' in d[0] else d[0]
        q('prospectus_date',val,d[1],'date',check=False, note='trading start date' if id_=='WORK' else '')
    t=deals[id_]['ticker']; yp=R+f'data/raw/yahoo/{t}.json'
    if os.path.exists(yp):
        meta=json.load(open(yp))['chart']['result'][0]['meta']; ft=meta.get('firstTradeDate')
        if ft:
            fd=datetime.datetime.fromtimestamp(ft,datetime.timezone.utc).date().isoformat()
            row(id_,'yahoo_first_trade_date',fd,'date',f'data/raw/yahoo/{t}.json','Yahoo Finance chart API, meta.firstTradeDate',f'"firstTradeDate": {ft}')
    if id_ in FX:
        v,ccy,quote=FX[id_]; q('fx_reporting_per_usd',v,quote,f'{ccy} per USD',check=False)
    x=xb.get(id_,{})
    cik=m['cik']; cf=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json'
    for k in ('revenue','revenue_prior','operating_income'):
        v=x.get(k)
        if v:
            fld={'revenue':'revenue_last_fy','revenue_prior':'revenue_prior_fy','operating_income':'profit_last_fy'}[k]
            row(id_,fld,v['value'],v['unit'],cf,f"SEC XBRL {v['tag']}, {v['form']} filed {v['filed']} (accession {v['accn']})",f"period {v['start']} to {v['end']}", note=v['tag'])
    if id_ in MANUAL_FIN:
        for k,(v,ccy,per,quote) in MANUAL_FIN[id_].items():
            fld={'revenue':'revenue_last_fy','operating_income':'profit_last_fy'}[k]
            q(fld,v/1e6,quote,f'{ccy} million',note=f'{per}; operating income (EBIT) as reported in the prospectus')
    # classification
    pp=R+f'data/raw/yahoo_profile/{t}.json'
    if os.path.exists(pp):
        qo=json.load(open(pp))
        row(id_,'sector',qo['quote'].get('sector'),'Yahoo Finance sector',qo['query_url'],'Yahoo Finance search API (retrieved 22 Oct 2026)',f"industry: {qo['quote'].get('industry')}")
    else:
        sub=json.load(open(R+f'data/sec/submissions/CIK{cik:010d}.json'))
        row(id_,'sic',sub.get('sic'),'SEC SIC code',f'https://data.sec.gov/submissions/CIK{cik:010d}.json','SEC EDGAR submissions',sub.get('sicDescription'))
print(len(rows),'rows'); print('problems',bad)
json.dump(rows,open('tools/extraction/us_fact_rows.json','w'))
