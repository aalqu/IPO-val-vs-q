import json, time, urllib.request, os, re
from bs4 import BeautifulSoup
UA={"User-Agent":"ipo-valuation-vs-quant research contact@example.com"}
D='./data/sec/'
pick={'ALLY':None}
out=json.load(open(D+'us_424b.json'))
idx={}
for id_,cik,name,near in out:
    if not near: print('NONE',id_); continue
    # prefer 424B4, else 424B1, else last 424B3
    pref=[f for f in near if f[0]=='424B4'] or [f for f in near if f[0]=='424B1'] or near
    f=pref[0]
    acc=f[2].replace('-','')
    url=f'https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{f[3]}'
    htm=D+f'prospectus/{id_}.htm'; txt=D+f'prospectus/{id_}.txt'
    if not os.path.exists(htm):
        for i in range(5):
            try:
                b=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=120).read(); open(htm,'wb').write(b); break
            except Exception as e: time.sleep(2+i)
        time.sleep(0.2)
    if not os.path.exists(txt):
        t=BeautifulSoup(open(htm,'rb').read(),'lxml').get_text('\n')
        t=re.sub(r'[ \t\xa0]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
        open(txt,'w').write(t)
    idx[id_]={'cik':cik,'name':name,'form':f[0],'filed':f[1],'accession':f[2],'url':url}
json.dump(idx,open(D+'prospectus/index_us.json','w'),indent=1)
print(len(idx))
