import json, re, os, subprocess, sys
R='./'
idx=json.load(open(R+'data/hk/hkex_docs.json'))
def text(p):
    p=R+p; t=re.sub(r'\.pdf$','.txt',p,flags=re.I)
    if not os.path.exists(t): subprocess.run(['pdftotext','-layout',p,t],capture_output=True)
    s=open(t,errors='ignore').read() if os.path.exists(t) else ''
    return re.sub(r'\s+',' ',s)
PRICE=[r'(?:final )?Offer Price (?:has been|was|had been|is) (?:determined|fixed|set) (?:at|as) HK\$ ?([0-9]+\.[0-9]+)',
       r'Offer Price (?:has been|was|is) (?:determined |fixed )?at HK\$ ?([0-9]+\.[0-9]+)',
       r'(?:final )?Offer Price[^.]{0,40}?(?:is|of|at|:) ?HK\$ ?([0-9]+\.[0-9]+) per (?:H |Offer )?Share',
       r'Offer Price: HK\$ ?([0-9]+\.[0-9]+)']
SH=[r'([0-9][0-9,]{6,}) (?:H |ordinary |Class [AB] )?Shares (?:(?:are )?(?:expected|anticipated) to be |will be |to be )?(?:in issue|issued)(?: and outstanding)?,? (?:immediately )?(?:following|upon|after|on) (?:the )?(?:completion of )?the (?:Global Offering|Capitali[sz]ation Issue|Share Subdivision)',
    r'based on ([0-9][0-9,]{6,}) (?:H |ordinary )?Shares',
    r'([0-9][0-9,]{6,}) Shares (?:were |are )?in issue immediately (?:following|upon|after) (?:the )?(?:completion of the )?(?:Global Offering|Listing)']
def is_allot(d,t):
    return bool(re.search(r'OFFER PRICE|ALLOTMENT|ALLOCATION|RESULTS',d['title'],re.I)) or bool(re.search(r'allotment results|Basis of Allo|BASIS OF ALLOTMENT|Results of Allocations',t[:20000],re.I))
out={}
for id_,v in idx.items():
    pr=[];sh=[]
    for d in v['docs']:
        t=text(d['path'])
        if is_allot(d,t):
            for p in PRICE:
                for m in re.finditer(p,t,re.I): pr.append((m.group(1),d['url'],m.group(0)))
        for p in SH:
            for m in re.finditer(p,t,re.I): sh.append((m.group(1),d['url'],t[max(0,m.start()-80):m.end()+30]))
    out[id_]={'price':pr,'shares':sh}
    print(id_.ljust(11),'P',sorted(set(x[0] for x in pr))[:5],'S',sorted(set(x[0] for x in sh))[:4])
json.dump(out,open('tools/extraction/hk_cands.json','w'))
