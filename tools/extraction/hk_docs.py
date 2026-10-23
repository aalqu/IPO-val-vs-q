import json, csv, re, time, datetime, os, subprocess, sys
sys.path.insert(0,'tools/extraction')
import hkex
R='./'
OUT=R+'data/hk/ann/'
B='https://www1.hkexnews.hk'
def txt(pdf):
    t=pdf[:-4]+'.txt'
    if not os.path.exists(t): subprocess.run(['pdftotext','-layout',pdf,t],capture_output=True)
    return open(t,errors='ignore').read() if os.path.exists(t) else ''
def dl(url,dest):
    if not os.path.exists(dest):
        b=hkex.get(url); open(dest,'wb').write(b); time.sleep(0.25)
    return dest
def fetch_doc(id_,tag,link):
    url=B+link
    if link.lower().endswith('.pdf'):
        p=dl(url,OUT+f'{id_}_{tag}.pdf'); return [(url,p)]
    h=hkex.get(url).decode('utf-8','ignore'); time.sleep(0.2)
    links=re.findall(r'href="([^"]+\.pdf)"[^>]*>(.*?)</a>',h,re.S|re.I)
    base=url.rsplit('/',1)[0]+'/'
    out=[]
    for l,t in links:
        t=re.sub(r'\s+',' ',re.sub('<[^>]+>','',t)).strip()
        if re.search(r'^Summary|Expected Timetable|Share Capital|Structure of the Global Offering|^Announcement|Allotment|Offer Price',t,re.I) or len(links)<=3:
            u=base+l.lstrip('./'); p=dl(u,OUT+f"{id_}_{tag}_{l.rsplit('/',1)[-1]}"); out.append((u,p))
    return out
if __name__=='__main__':
    ids=sys.argv[1:]
    deals={r['id']:r for r in csv.DictReader(open(R+'data/deals_asia.csv')) if r['region']=='HK'}
    idx=json.load(open(R+'data/hk/hkex_docs.json')) if os.path.exists(R+'data/hk/hkex_docs.json') else {}
    for id_ in (ids or deals):
        r=deals[id_]; code=r['ticker'].split('.')[0].zfill(5)
        sid,name=hkex.stock_id(code); time.sleep(0.2)
        ipo=datetime.date.fromisoformat(r['ipo_date'])
        res=hkex.search(sid,(ipo-datetime.timedelta(days=40)).strftime('%Y%m%d'),(ipo+datetime.timedelta(days=7)).strftime('%Y%m%d')); time.sleep(0.2)
        cands=[x for x in res if re.search(r'GLOBAL OFFERING|OFFER PRICE|ALLOTMENT|ALLOCATION|PROSPECTUS',x['TITLE'],re.I) and not re.search(r'Form|Web Proof|PHIP|Application Proof|Reposted|Stabili|OVER-ALLOTMENT OPTION|Supplemental',x['TITLE'],re.I)]
        docs=[]
        for i,x in enumerate(cands):
            for u,p in fetch_doc(id_,f'd{i}',x['FILE_LINK']):
                docs.append({'date':x['DATE_TIME'],'title':x['TITLE'],'url':u,'path':p.replace(R,'')})
        idx[id_]={'code':code,'stockId':sid,'name':name,'docs':docs}
        print(id_,code,name,[(d['date'][:10],d['title'][:30],os.path.basename(d['path'])) for d in docs][:8])
        json.dump(idx,open(R+'data/hk/hkex_docs.json','w'),indent=1)
