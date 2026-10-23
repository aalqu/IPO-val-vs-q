import json, csv, re, time, urllib.request, urllib.parse, datetime, sys, os
UA={"User-Agent":"Mozilla/5.0"}
B='https://www1.hkexnews.hk'
def get(url, tries=5):
    for i in range(tries):
        try: return urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60).read()
        except Exception as e: err=e; time.sleep(2+i*2)
    raise err
def stock_id(code):
    t=get(f'{B}/search/prefix.do?&callback=callback&lang=EN&type=A&name={code}&market=SEHK').decode()
    d=json.loads(t[t.index('(')+1:t.rindex(')')])
    for s in d['stockInfo']:
        if s['code']==code: return s['stockId'], s['name']
    # delisted stocks: type=I
    t=get(f'{B}/search/prefix.do?&callback=callback&lang=EN&type=I&name={code}&market=SEHK').decode()
    d=json.loads(t[t.index('(')+1:t.rindex(')')])
    for s in d['stockInfo']:
        if s['code']==code: return s['stockId'], s['name']
    return None, None
def search(sid, d0, d1):
    u=(f'{B}/search/titleSearchServlet.do?sortDir=0&sortByOptions=DateTime&category=0&market=SEHK&stockId={sid}&documentType=-1'
       f'&fromDate={d0}&toDate={d1}&title=&searchType=0&t1code=-2&t2Gcode=-2&t2code=-2&rowRange=300&lang=E')
    d=json.loads(get(u)); return json.loads(d['result'])
if __name__=='__main__':
    R='./'
    deals=[r for r in csv.DictReader(open(R+'data/deals_asia.csv')) if r['region']=='HK']
    out={}
    for r in deals:
        code=r['ticker'].split('.')[0].zfill(5)
        sid,name=stock_id(code); time.sleep(0.3)
        ipo=datetime.date.fromisoformat(r['ipo_date'])
        if not sid: out[r['id']]={'error':'no stockId'}; print(r['id'],'NO SID'); continue
        res=search(sid,(ipo-datetime.timedelta(days=40)).strftime('%Y%m%d'),(ipo+datetime.timedelta(days=12)).strftime('%Y%m%d')); time.sleep(0.3)
        allot=[x for x in res if re.search(r'ALLOTMENT RESULTS|OFFER PRICE AND ALLOTMENT|ALLOCATION RESULTS|FINAL OFFER PRICE',x['TITLE'],re.I)]
        prosp=[x for x in res if re.search(r'GLOBAL OFFERING|PROSPECTUS|LISTING BY WAY OF INTRODUCTION',x['TITLE'],re.I) and 'Application Form' not in x['TITLE']]
        out[r['id']]={'code':code,'stockId':sid,'name':name,'allot':[(x['DATE_TIME'],x['TITLE'],x['FILE_LINK']) for x in allot],
                      'prospectus':[(x['DATE_TIME'],x['TITLE'],x['FILE_LINK'],x.get('FILE_INFO')) for x in prosp]}
        print(r['id'], code, name, len(allot), len(prosp), allot[0][1][:60] if allot else '-' , '|', allot[0][2] if allot else '')
    json.dump(out,open(R+'data/hk/hkex_index.json','w'),indent=1)
