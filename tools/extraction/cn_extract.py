import re,json,os,sys
D='./data/cn/'
def norm(s):
    s=re.sub(r'[ \t　]+',' ',s); s=re.sub(r'\s*\n\s*',' ',s); return s
PRICE=[r'发行价格\s*[:：]\s*(?:人民币)?\s*([0-9]+\.[0-9]+)\s*元', r'发行价格为\s*(?:人民币)?\s*([0-9]+\.[0-9]+)\s*元', r'发行价格\s*(?:人民币)?\s*([0-9]+\.[0-9]+)\s*元/股',
       r'每股发行价格\s*[:：]?\s*(?:人民币)?\s*([0-9]+\.[0-9]+)', r'发行价\s*[:：]?\s*(?:人民币)?\s*([0-9]+\.[0-9]+)\s*元/股']
SH=[r'(?:本次)?(?:公开)?发行后的?总股本\s*(?:为|[:：])\s*([0-9][0-9,.]*)\s*(万股|股|亿股)', r'(?:首次公开)?发行(?:完成)?后(?:公司)?总股本\s*(?:为|[:：])\s*([0-9][0-9,.]*)\s*(万股|股|亿股)', r'发行完成后(?:本行|本公司|公司)?总股本为\s*([0-9][0-9,.]*)\s*(万股|股|亿股)']
MV=[r'上市时市值约为\s*([0-9][0-9,.]*)\s*亿元']
def scan(id_):
    s=norm(open(D+f'{id_}_listing.txt',errors='ignore').read())
    o={}
    for k,ps in (('price',PRICE),('shares',SH),('mv',MV)):
        hits=[]
        for p in ps:
            for m in re.finditer(p,s): hits.append((m.group(0), m.group(1)+(m.group(2) if m.lastindex==2 else '')))
        o[k]=hits
    return o,s
if __name__=='__main__':
    for id_ in sys.argv[1:]:
        o,s=scan(id_)
        print(id_.ljust(10),'P',sorted(set(h[1] for h in o['price']))[:4],'S',sorted(set(h[1] for h in o['shares']))[:4],'MV',sorted(set(h[1] for h in o['mv'])))
