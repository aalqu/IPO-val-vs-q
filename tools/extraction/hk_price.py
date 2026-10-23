import json,re,sys,datetime
sys.path.insert(0,'tools/extraction')
from hk_extract2 import text, idx
P=[r'(?:The )?(?:final )?Offer Price (?:has been|was|had been|is) (?:determined|fixed|set) (?:at|as) HK\$ ?[0-9]+\.[0-9]+[^.]{0,80}',
   r'(?:The )?(?:final )?Offer Price (?:has been|was|is) (?:determined |fixed )?at HK\$ ?[0-9]+\.[0-9]+[^.]{0,80}',
   r'Offer Price[^.]{0,30}?:? ?HK\$ ?[0-9]+\.[0-9]+ per (?:H |Offer )?Share[^.]{0,40}',
   r'Final Offer Price[^.]{0,30}HK\$ ?[0-9]+\.[0-9]+']
res={}
for id_,v in idx.items():
    docs=sorted(v['docs'],key=lambda d:datetime.datetime.strptime(d['date'],'%d/%m/%Y %H:%M'),reverse=True)
    al=[d for d in docs if re.search(r'OFFER PRICE|ALLOTMENT|ALLOCATION|RESULTS',d['title'],re.I)] or docs[:1]
    hit=None
    for d in al:
        t=text(d['path'])
        for p in P:
            m=re.search(p,t,re.I)
            if m: hit=(m.group(0),d['url'],d['title'],d['date']); break
        if hit: break
    res[id_]=hit
    print(id_.ljust(11), (hit[3][:10]+' | '+hit[2][:28]+' | '+hit[0][:150]) if hit else 'NONE')
json.dump(res,open('tools/extraction/hk_price.json','w'))
