import json, csv, re, time, datetime, os, subprocess, sys, urllib.request, urllib.parse
sys.path.insert(0,'tools/extraction')
import cninfo
R='./'
OUT=R+'data/cn/'
def orgid(code):
    d=cninfo.post('https://www.cninfo.com.cn/new/information/topSearch/query',{'keyWord':code,'maxNum':5})
    for x in d:
        if x['code']==code: return x['orgId']
idx=json.load(open(OUT+'cninfo_docs.json')) if os.path.exists(OUT+'cninfo_docs.json') else {}
deals=[r for r in csv.DictReader(open(R+'data/deals_asia.csv')) if r['region']=='ChinaA']
for r in deals:
    if r['id'] in idx and idx[r['id']].get('prospectus'): continue
    code=r['ticker'].split('.')[0]; col='szse' if r['ticker'].endswith('.SZ') else 'sse'
    try:
        org=orgid(code)
    except Exception as e:
        print(r['id'],'orgid fail',e); continue
    ipo=datetime.date.fromisoformat(r['ipo_date'])
    rng=f"{(ipo-datetime.timedelta(days=60)).isoformat()}~{(ipo+datetime.timedelta(days=10)).isoformat()}"
    try:
        hits=cninfo.search(code,org,col,rng)
    except Exception as e:
        print(r['id'],'search fail',e); continue
    def clean(t): return re.sub('<[^>]+>','',t)
    pro=[h for h in hits if '招股' in clean(h[0]) and not re.search('摘要|附录|提示|意见|确认|更正|补充|发行安排|英文',clean(h[0]))]
    res=[h for h in hits if re.search('发行结果|上市公告书',clean(h[0])) and not re.search('提示',clean(h[0]))]
    idx[r['id']]={'code':code,'orgId':org,'column':col,'prospectus':[(clean(h[0]),h[1],h[2]) for h in pro],'results':[(clean(h[0]),h[1],h[2]) for h in res]}
    print(r['id'],code,len(hits),[clean(h[0])[:24] for h in pro],[clean(h[0])[:16] for h in res])
    json.dump(idx,open(OUT+'cninfo_docs.json','w'),indent=1,ensure_ascii=False)
    time.sleep(0.5)
