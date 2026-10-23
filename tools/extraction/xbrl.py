import json, os, time, urllib.request, datetime, sys
UA={"User-Agent":"ipo-valuation-vs-quant research contact@example.com"}
D='./data/sec/'
idx=json.load(open(D+'prospectus/index_us.json'))
REV=['us-gaap:Revenues','us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax','us-gaap:SalesRevenueNet','us-gaap:SalesRevenueGoodsNet','us-gaap:SalesRevenueServicesNet',
     'us-gaap:RevenuesNetOfInterestExpense','us-gaap:HealthCareOrganizationRevenue','us-gaap:RevenueFromContractWithCustomerIncludingAssessedTax','ifrs-full:Revenue','ifrs-full:RevenueFromContractsWithCustomers']
OPI=['us-gaap:OperatingIncomeLoss','ifrs-full:ProfitLossFromOperatingActivities','us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest','us-gaap:IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments','ifrs-full:ProfitLossBeforeTax','us-gaap:ProfitLoss','us-gaap:NetIncomeLoss','ifrs-full:ProfitLoss']
NI=['us-gaap:NetIncomeLoss','us-gaap:ProfitLoss','ifrs-full:ProfitLossAttributableToOwnersOfParent','ifrs-full:ProfitLoss']
def get(cik):
    p=D+f'companyfacts/CIK{cik:010d}.json'
    if not os.path.exists(p):
        for i in range(5):
            try:
                b=urllib.request.urlopen(urllib.request.Request(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json',headers=UA),timeout=120).read(); open(p,'wb').write(b); break
            except Exception as e: err=e; time.sleep(2+i)
        time.sleep(0.15)
    return json.load(open(p)) if os.path.exists(p) else None
def series(facts,tag):
    tx,name=tag.split(':'); node=facts.get('facts',{}).get(tx,{}).get(name)
    if not node: return []
    out=[]
    for unit,vals in node['units'].items():
        for v in vals:
            if 'start' not in v: continue
            s=datetime.date.fromisoformat(v['start']); e=datetime.date.fromisoformat(v['end'])
            if 340<=(e-s).days<=380: out.append(dict(v,unit=unit,tag=tag))
    return out
def pick(facts,tags,ipo):
    # last annual period ending before the IPO; earliest filing that reports it; first tag with data
    for tag in tags:
        s=[v for v in series(facts,tag) if datetime.date.fromisoformat(v['end'])<ipo]
        if not s: continue
        last=max(v['end'] for v in s)
        cands=sorted([v for v in s if v['end']==last], key=lambda v:(v['filed'], v['accn']))
        return cands[0], [v for v in s]
    return None, []
res={}
for id_,m in idx.items():
    cik=m['cik']; f=get(cik)
    if not f: res[id_]={'error':'no companyfacts'}; continue
    ipo=datetime.date.fromisoformat(m['filed'])
    r={}
    for k,tags in (('revenue',REV),('operating_income',OPI),('net_income',NI)):
        v,allv=pick(f,tags,ipo)
        if v:
            r[k]=dict(value=v['val'],unit=v['unit'],start=v['start'],end=v['end'],tag=v['tag'],accn=v['accn'],form=v['form'],filed=v['filed'])
            # prior year for growth
            prev=[x for x in allv if x['end']<v['start'] and datetime.date.fromisoformat(v['start'])-datetime.date.fromisoformat(x['end'])<datetime.timedelta(days=10)]
            if k=='revenue' and prev:
                pv=sorted(prev,key=lambda x:(x['filed'],x['accn']))[0]; r['revenue_prior']=dict(value=pv['val'],unit=pv['unit'],start=pv['start'],end=pv['end'],tag=pv['tag'],accn=pv['accn'],form=pv['form'],filed=pv['filed'])
    res[id_]=r
    rv=r.get('revenue',{}); op=r.get('operating_income',{})
    print(id_.ljust(6), rv.get('end'), rv.get('unit'), rv.get('value'), rv.get('form'), rv.get('filed'), '| opi', op.get('value'), op.get('end'))
json.dump(res,open(D+'xbrl_us_lastfy.json','w'),indent=1)
