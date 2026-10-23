import json, csv, time, urllib.request, sys, datetime
UA={"User-Agent":"ipo-valuation-vs-quant research contact@example.com"}
D='./data/sec/'
def get(url):
    for i in range(5):
        try: return urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60).read()
        except Exception as e: err=e; time.sleep(1+i)
    raise err
T=json.load(open(D+'company_tickers.json'))
m={v['ticker']:v['cik_str'] for v in T.values()}
extra={'NLSN':1492633,'ZNGA':1439404,'TWTR':1418091,'SC':1580608,'ATUS':1702780,'WORK':1764925,'XM':1747748,'DIDI':1764757,'HCP':1720671}
m.update(extra)
out=[]
for r in csv.DictReader(open('./data/deals.csv')):
    if r['region']!='US': continue
    cik=m[r['ticker']]
    p=D+f'submissions/CIK{cik:010d}.json'
    try: s=json.load(open(p))
    except FileNotFoundError:
        s=json.loads(get(f'https://data.sec.gov/submissions/CIK{cik:010d}.json')); json.dump(s,open(p,'w')); time.sleep(0.15)
    filings=[]
    def add(rec):
        for f,dt,acc,doc in zip(rec['form'],rec['filingDate'],rec['accessionNumber'],rec['primaryDocument']): filings.append((f,dt,acc,doc))
    add(s['filings']['recent'])
    for extra_f in s['filings'].get('files',[]):
        fp=D+'submissions/'+extra_f['name']
        try: e=json.load(open(fp))
        except FileNotFoundError:
            e=json.loads(get('https://data.sec.gov/submissions/'+extra_f['name'])); json.dump(e,open(fp,'w')); time.sleep(0.15)
        add(e)
    ipo=datetime.date.fromisoformat(r['ipo_date'])
    near=[f for f in filings if f[0] in ('424B4','424B1','424B3') and abs((datetime.date.fromisoformat(f[1])-ipo).days)<=20]
    near.sort(key=lambda f:f[1])
    out.append((r['id'],cik,s['name'],near[:3]))
    print(r['id'],cik,s['name'],r['listing_type'],near[:2])
json.dump(out,open(D+'us_424b.json','w'))
