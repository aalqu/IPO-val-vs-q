import re,json,os,sys,datetime
sys.path.insert(0,'tools/extraction')
from cn_extract import scan, norm
D='./data/cn/'
idx=json.load(open(D+'cninfo_docs.json'))
rows=[]; bad=[]
def unit_mult(u): return {'股':1,'万股':1e4,'亿股':1e8}[u]
# manual share totals (all classes, before any over-allotment) where the listing announcement does not state one in the standard form
MAN_SH={
 'ABC_A': ('hk', 317647059000, 'Total . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 317,647,059,000 100.00%'),
 'CSC_A': ('listing', [6385361476, 1261023762], '中 A 股 总 股 本 6,385,361,476股，H股总股本1,261,023,762股'),
 'SMIC_A': ('listing', 7136423226, '本次公开发行后的股份总数3：7,136,423,226 股（行使超额配售选择权之 前）'),
 'CM_A': ('listing', 21321182897, '行完成后公司已发行股份总数为 21,321,182,897 股，其中 A 股 845,700,000 股，港股 20,475,482,897 股'),
 'CNOOC_A': ('listing', 47247455984, '前，本次发行完成后公司已发行股份总数为 47,247,455,984 股'),
 'GTJA_A': ('prospectus', 7625000000, '发行后总股本： 76.25 亿股'),
 'NCI_A': ('listing', None, None),
}
# where several share figures appear, the one before any over-allotment option
PREF={'PSBC_A':'86,202,738,200股','HUADIAN_NE':'4,096,894.4214万股','JSBANK':'1,154,445万股','JINKO_A':'1,000,000万股'}
for id_,v in idx.items():
    lst=v.get('listing'); url=lst[1] if lst else None
    doc=f"CNINFO: {lst[0]}" if lst else ''
    if id_=='GTJA_A':
        s=norm(open(D+'GTJA_A_result.txt',errors='ignore').read()); q='发行价格为19.71元/股'
        assert q in s; rows.append(dict(id=id_,field='offer_price',value=19.71,unit='CNY per share',source_url=v['result_doc'][1],source_doc='CNINFO: '+v['result_doc'][0],quote=q,note=''))
        s=norm(open(D+'GTJA_A_prospectus.txt',errors='ignore').read()); q='发行后总股本： 76.25 亿股'
        assert q in s; rows.append(dict(id=id_,field='shares_after_offering_1',value=7625000000,unit='shares',source_url=v['prospectus_doc'][1],source_doc='CNINFO: '+v['prospectus_doc'][0],quote=q,note='76.25 亿股 (100 million shares)'))
        continue
    o,s=scan(id_)
    ps=sorted(set(h[1] for h in o['price']))
    if len(ps)!=1: bad.append((id_,'price',ps))
    else:
        q=next(h[0] for h in o['price'] if h[1]==ps[0])
        rows.append(dict(id=id_,field='offer_price',value=float(ps[0]),unit='CNY per share',source_url=url,source_doc=doc,quote=q,note=''))
    if id_ in MAN_SH and MAN_SH[id_][1] is not None:
        where,val,q=MAN_SH[id_]
        if where=='hk':
            hk=json.load(open('./data/hk/hkex_docs.json'))['ABC_H']
            d=[x for x in hk['docs'] if x['path'].endswith('E124.pdf')][0]
            t=norm(open('./'+d['path'][:-4]+'.txt',errors='ignore').read())
            if q not in t: bad.append((id_,'hk quote missing')); continue
            rows.append(dict(id=id_,field='shares_after_offering_1',value=val,unit='shares',source_url=d['url'],source_doc='HKEX prospectus (Share Capital), ABC H-share global offering',quote=q,note='A and H shares after both offerings, before over-allotment'))
        else:
            src=s if where=='listing' else None
            if q not in src: bad.append((id_,'quote missing',q[:30])); continue
            vals=val if isinstance(val,list) else [val]
            for i,x in enumerate(vals):
                rows.append(dict(id=id_,field=f'shares_after_offering_{i+1}',value=x,unit='shares',source_url=url,source_doc=doc,quote=q,note=''))
    else:
        sh=sorted(set(h[1] for h in o['shares']))
        if id_ in PREF: sh=[PREF[id_]]
        if len(sh)<1: bad.append((id_,'shares',sh)); 
        else:
            if len(sh)>1:
                # same number in different units (e.g. 万股 and 亿股) is fine
                vals={round(float(re.sub(r'[,，]','',re.match(r'[0-9,.]+',x).group(0)))*unit_mult(re.search(r'(万股|亿股|股)$',x).group(1))) for x in sh}
                if len(vals)>1: bad.append((id_,'shares multiple',sh)); continue
            x=sh[0]; num=float(re.sub(r'[,，]','',re.match(r'[0-9,.]+',x).group(0))); u=re.search(r'(万股|亿股|股)$',x).group(1)
            q=next(h[0] for h in o['shares'] if h[1]==x)
            rows.append(dict(id=id_,field='shares_after_offering_1',value=round(num*unit_mult(u)),unit='shares',source_url=url,source_doc=doc,quote=q,note=f'{x} as stated'))
    m=re.search(r'上市(?:时间|日期)\s*[:：]?\s*(20[0-9]{2})\s*年\s*([0-9]{1,2})\s*月\s*([0-9]{1,2})\s*日',s)
    if m: rows.append(dict(id=id_,field='listing_date',value=datetime.date(int(m.group(1)),int(m.group(2)),int(m.group(3))).isoformat(),unit='date',source_url=url,source_doc=doc,quote=m.group(0),note=''))
print(len(rows),'rows'); [print(' BAD',b) for b in bad]
json.dump(rows,open('tools/extraction/cn_rows.json','w'),ensure_ascii=False)
