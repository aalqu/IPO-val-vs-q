"""Build HK deal facts (offer price, shares after the offering, listing date, HK$ per US$)
from HKEXnews documents saved under data/hk. Every value is the number printed in the quote."""
import json, re, os, sys, datetime
sys.path.insert(0, 'tools/extraction')
import fred
R = './'
SP = 'tools/extraction/'
idx = json.load(open(R + 'data/hk/hkex_docs.json'))
EXTRA = {  # documents fetched outside the offering window (monthly returns)
    'BUDAPAC_mr201909': {'date': '08/10/2019 20:00', 'title': 'Monthly Return of Equity Issuer on Movements in Securities for the month ended 30 September 2019',
                         'url': 'https://www1.hkexnews.hk/listedco/listconews/sehk/2019/1008/ltn20191008751.pdf', 'path': 'data/hk/ann_extra/BUDAPAC_mr201909.pdf'},
}
_cache = {}
def norm(p):
    if p not in _cache:
        t = re.sub(r'\.pdf$', '.txt', R + p, flags=re.I)
        _cache[p] = re.sub(r'\s+', ' ', open(t, errors='ignore').read()) if os.path.exists(t) else ''
    return _cache[p]

def docs(k):
    return idx[k]['docs'] + ([EXTRA[x] for x in EXTRA if x.startswith(k + '_')])

def srcdoc(d):
    return f"HKEXnews: {d['title'].strip()} ({d['date'][:10]})"

def find(k, anchor, num, maxlen=2200, prefer=None):
    """Quote from the anchor through the first occurrence of `num` after it."""
    ds = docs(k)
    if prefer: ds = sorted(ds, key=lambda d: prefer not in d['url'])
    for d in ds:
        t = norm(d['path'])
        for m in re.finditer(anchor, t):
            j = t.find(num, m.start())
            if 0 <= j - m.start() <= maxlen:
                end = j + len(num)
                # extend to end of sentence / table row (up to 160 chars)
                tail = t[end:end + 400]
                m100 = re.match(r'\s*100(?:\.0+)?%?', tail)
                e2 = m100 or re.search(r'\.\s|\)\.|;\s', tail)
                if e2 and e2.end() <= 400: end += e2.end()
                else: end += len(tail[:45].rsplit(' ', 1)[0])
                return d, t[m.start():end].strip()
    return None, None

SH = {  # id: [(field, anchor regex, number as printed, note)]
 'ABC_H': [('shares_after_offering_1', r'Immediately following the completion of the A Share Offering and the Global Offering, assuming that neither of the over-allotment options', '317,647,059,000', 'Total A and H shares (registered capital in RMB at RMB1.00 per share) after the concurrent A Share Offering and Global Offering')],
 'NCI_H': [('shares_after_offering_1', r'Immediately following completion of the A Share Offering and the Global Offering \(assuming the H Share Over-Allotment Option is not exercised\)', '3,116,960,000', 'Total A and H shares after the concurrent A Share Offering and Global Offering')],
 'PICC': [('shares_after_offering_1', r'Immediately following the completion of the Global Offering, assuming that the H-Share Over-allotment Option is not exercised', '41,389,259,583', 'H plus Domestic Shares; the A Share Offering described in the prospectus was not part of this listing')],
 'CINDA': [('shares_after_offering_1', r'Immediately following the completion of the Global Offering, assuming that the Over- ?allotment Option is not exercised', '35,458,864,035', 'H plus Domestic Shares')],
 'CEB_H': [('shares_after_offering_1', r'Immediately following the completion of the Global Offering and assuming exercise in full of either the Offer Size Adjustment Option or the Over-allotment Option', '46,276,790,000', 'A plus H shares; the Offer Size Adjustment Option was exercised in full (see offer_size_adjustment) and the over-allotment is excluded')],
 'MGMCHINA': [('shares_after_offering_1', r'market capitali[sz]ation of our Shares is based on the assumption that', '3,800,000,001', '')],
 'XIAOMI': [('shares_after_offering_1', r'market capitalization is based on 22,376,130,830', '22,376,130,830', 'All classes (Class A and Class B)')],
 'AIA': [('shares_after_offering_1', r'market capitalisation is based on 12,044,000,001', '12,044,000,001', 'All Offer Shares were sold by the Selling Shareholder, so the Offer Size Adjustment Option did not change the share count')],
 'PRADA': [('shares_after_offering_1', r'market capitalization is based on 2,558,824,000', '2,558,824,000', '')],
 'SUNART': [('shares_after_offering_1', r'market capitalisation of the Shares is based on the assumption that 9,368,127,700', '9,368,127,700', '')],
 'WHGROUP': [('shares_after_offering_1', r'market capitalization is based on 14,263,311,111', '14,263,311,111', '')],
 'CGN_H': [('shares_after_offering_1', r'market capitalization is based on 8,825,000,000 H Shares', '44,125,000,000', 'Total shares (H plus Domestic)')],
 'BAIC': [('shares_after_offering_1', r'Assuming the Over-allotment Option is not exercised, the share capital of our Company immediately after the Global Offering will be as follows', '7,508,018,182', 'Total share capital (Domestic plus H)')],
 'FUYAO_H': [('shares_after_offering_1', r'Immediately following completion of the Global Offering, assuming that the Over- ?allotment Option is not exercised, our registered and issued share capital', '2,442,665,932', 'A plus H shares')],
 'GFSEC_H': [('shares_after_offering_1', r'Immediately following completion of the Global Offering, assuming that the Over-allotment Option is not exercised, our share capital is as follows', '7,399,114,264', 'A plus H shares')],
 'HUATAI_H': [('shares_after_offering_1', r'Immediately following completion of the Global Offering, assuming that the Over-allotment Option is not exercised, the entire share capital', '7,000,000,000', 'A plus H shares')],
 'LEGEND': [('shares_after_offering_1', r'Immediately following the completion of the Global Offering, assuming the Over- ?allotment Option is not exercised, the registered capital', '2,352,944,000', 'H plus Domestic Shares (RMB1.00 per share)')],
 'CHINARE': [('shares_after_offering_1', r'Immediately following completion of the Global Offering, assuming that the Over-allotment Option is not exercised, the registered capital', '42,177,501,085', 'H plus Domestic Shares (RMB1.00 per share)')],
 'HUARONG': [('shares_after_offering_1', r'based on the 38,465,750,462 Shares', '38,465,750,462', '')],
 'CZB_H': [('shares_after_offering_1', r'Immediately after completion of the Global Offering, but without taking into account the exercise of the Over-allotment Option, our total share capital', '17,509,696,778', 'Domestic plus H shares')],
 'EBSEC_H': [('shares_after_offering_1', r'Immediately following completion of the Global Offering, assuming that the Over-allotment Option is not exercised, our share capital is as follows', '4,586,698,839', 'A plus H shares')],
 'PSBC_H': [('shares_after_offering_1', r'Immediately following completion of the Global Offering, conversion of the unlisted Foreign Shares as well as the Domestic Shares for transfer to NSSF into H Shares, and assuming that the Over-allotment Option is not exercised', '80,710,588,000', 'Domestic plus H shares')],
 'GTJA_H': [('shares_after_offering_1', r'Immediately after the Global Offering, assuming that the Over-allotment Option is not exercised and none of the Convertible Bonds is converted', '8,665,000,000', 'A plus H shares')],
 'ZHONGAN': [('shares_after_offering_1', r'market capitalisation is based on 1,439,918,900', '1,439,918,900', '')],
 'CHINALIT': [('shares_after_offering_1', r'market capitalization is based on 906,417,239', '906,417,239', '')],
 'YIXIN': [('shares_after_offering_1', r'market capitalization is based on 6,276,322,474', '6,276,322,474', '')],
 'PAGD': [('shares_after_offering_1', r'on the basis that 1,067,294,200 Shares', '1,067,294,200', '')],
 'CHINATOWER': [('shares_after_offering_1', r'Immediately after the Global Offering and assuming that the Over-allotment Option is not exercised, the share capital of the Company will be as follows', '172,459,415,024', 'Domestic plus H shares')],
 'MEITUAN': [('shares_after_offering_1', r'market capitalization is based on 5,491,255,065', '5,491,255,065', 'All classes')],
 'HAIDILAO': [('shares_after_offering_1', r'market capitalization is based on 5,300,000,000', '5,300,000,000', '')],
 'SWHY_H': [('shares_after_offering_1', r'Immediately following completion of the Global Offering, assuming that the Over-allotment Option is not exercised, our share capital is as follows', '25,039,944,560', 'A plus H shares')],
 'HANSOH': [('shares_after_offering_1', r'market capitalization is based on 5,705,919,200', '5,705,919,200', '')],
 'BUDAPAC': [('shares_after_offering_1', r'Balance upon listing on 30/09/2019', '13,025,642,000', 'Issued shares on the listing date per the first monthly return; the Offer Size Adjustment Option was partially exercised, so the prospectus totals do not apply')],
 'FEIHE': [('shares_after_offering_1', r'based on the total number of 8,933,340,000', '8,933,340,000', '')],
 'SMOORE': [('shares_after_offering_1', r'market capitalization is based on 5,743,512,720', '5,743,512,720', '')],
 'BOHAI': [('shares_after_offering_1', r'Immediately following completion of the Global Offering and conversion of the unlisted Foreign Shares, and assuming the Over-allotment Option is not exercised, the total issued share capital', '17,330,000,000', 'Domestic plus H shares')],
 'TIGERMED_H': [('shares_after_offering_1', r'Immediately following completion of the Global Offering, assuming that the Over- ?allotment Option is not exercised, the share capital of our Company would be as follows', '856,520,650', 'A plus H shares')],
 'NONGFU': [('shares_after_offering_1', r'Immediately after the Global Offering and Conversion of Domestic Shares into H Shares \(assuming that the Over-allotment Option is not exercised\)', '11,188,231,800', 'Domestic plus H shares')],
 'JDH': [('shares_after_offering_1', r'market capitalization is based on 3,127,082,111', '3,127,082,111', '')],
 'MIXC': [('shares_after_offering_1', r'market capitalization is based on 2,200,000,000', '2,200,000,000', '')],
 'POPMART': [('shares_after_offering_1', r'market capitalization is based on 1,381,580,350', '1,381,580,350', '')],
 'KUAISHOU': [('shares_after_offering_1', r'market capitalization is based on 4,108,194,737', '4,108,194,737', 'All classes')],
 'JDLOG': [('shares_after_offering_1', r'market capitalization is based on 6,091,607,672', '6,091,607,672', '')],
 'SENSETIME': [('shares_after_offering_1', r'market capitalization is based on 7,528,760,000 Class A Shares', '7,528,760,000', 'Class A shares'),
               ('shares_after_offering_2', r'market capitalization is based on 7,528,760,000 Class A Shares', '25,753,640,000', 'Class B shares')],
 'TIANQI_H': [('shares_after_offering_1', r'Immediately following completion of the Global Offering, assuming that the Over-allotment Option is not exercised, our registered and issued share capital', '1,641,221,583', 'A plus H shares')],
 'LEAPMOTOR': [('shares_after_offering_1', r'assuming the Offer Size Adjustment Option and the Over-allotment Option are not exercised, the share capital of our Company will', '1,142,706,059', 'All shares; the Offer Size Adjustment Option lapsed (see offer_size_adjustment)')],
 'CALB': [('shares_after_offering_1', r'market capitalization is based on 1,772,301,858', '1,772,301,858', 'Domestic, unlisted and H shares')],
 'ZJLD': [('shares_after_offering_1', r'market capitalization is based on 3,271,331,050', '3,271,331,050', '')],
 'MIDEA_H': [('shares_after_offering_1', r'total issued share capital of the Company upon Listing', '7,559,086,151', 'A plus H shares, after the Offer Size Adjustment Option')],
 'HORIZON': [('shares_after_offering_1', r'Number of issued Shares upon Listing', '13,029,866,082', 'Class A plus Class B shares')],
 'SF_H': [('shares_after_offering_1', r'Number of issued shares upon Listing', '4,986,186,983', 'A plus H shares')],
 'MIXUE': [('shares_after_offering_1', r'Number of issued Shares upon Listing', '377,059,900', '')],
 'CATL_H': [('shares_after_offering_1', r'total issued share capital of the Company upon Listing', '4,538,973,511', 'A plus H shares, after the Offer Size Adjustment Option')],
 'HENGRUI_H': [('shares_after_offering_1', r'Number of issued shares upon Listing', '6,603,522,074', 'A plus H shares')],
 'HAITIAN_H': [('shares_after_offering_1', r'total issued share capital of the Company upon Listing', '5,839,632,244', 'A plus H shares, after the Offer Size Adjustment Option')],
 'SANHUA_H': [('shares_after_offering_1', r'total issued share capital of the Company upon Listing', '4,146,769,035', 'A plus H shares, after the Offer Size Adjustment Option')],
 'CHERY': [('shares_after_offering_1', r'Number of issued Shares upon Listing', '5,767,228,633', '')],
 'ZIJINGOLD': [('shares_after_offering_1', r'Number of issued shares upon Listing', '2,623,990,700', '')],
 'SANY_H': [('shares_after_offering_1', r'total issued share capital of the Company upon Listing', '9,105,988,837', 'A plus H shares, after the partial exercise of the Offer Size Adjustment Option')],
 'SERES_H': [('shares_after_offering_1', r'total issued share capital of the Company upon Listing', '1,741,985,086', 'A plus H shares, after the partial exercise of the Offer Size Adjustment Option')],
}
OSA = {  # supporting facts on the offer size adjustment option
 'CEB_H': r'Offer Size Adjustment Option granted to the Underwriters has been exercised in full',
 'LEAPMOTOR': r'The Company did not exercise the Offer Size Adjustment Option on or before the Price Determination Date',
 'BUDAPAC': r'Offer Size Adjustment Option was partially exercised by the Company',
}
PRICE_FIX = {'ABC_H': r'the offer price for the Global Offering has been determined at HK\$3\.20 per H share',
             'NCI_H': r'The Offer Price for the Global Offering has been determined at HK\$28\.50 per H Share'}
DEAL = r'[Dd]ealings in (?:the )?(?:our )?(?:H |Class B |Class B Ordinary )?[Ss]hares (?:on (?:the Main Board of )?(?:the )?(?:Hong Kong )?Stock Exchange |on the Main Board )?(?:are expected to|is expected to|will) commence (?:at [0-9:]+ a\.m\. (?:\(Hong Kong time\) )?)?on (?:\w+day,? )?(\d{1,2} \w+,? \d{4}|\w+ \d{1,2},? \d{4})'
FXP = [r'HK\$ ?(7\.[0-9]{2,5}) ?(?:to|=|:|for|per) ?US\$ ?1(?:\.0+)?\b', r'US\$ ?1(?:\.0+)? ?(?:to|=|:) ?HK\$ ?(7\.[0-9]{2,5})']

def num(s): return s.replace(',', '')

def to_iso(s):
    s = s.replace(',', '')
    for f in ('%d %B %Y', '%B %d %Y'):
        try: return datetime.datetime.strptime(s, f).date().isoformat()
        except ValueError: pass
    return None

rows, problems = [], []
price = json.load(open(SP + 'hk_price.json'))
for k in idx:
    # offer price
    if k in PRICE_FIX:
        d, q = find(k, PRICE_FIX[k], PRICE_FIX[k].split('HK\\$')[1].split(' ')[0].replace('\\', ''))
        if d: rows.append(dict(id=k, field='offer_price', value=re.search(r'HK\$ ?([0-9.]+)', q).group(1), unit='HKD per share', source_url=d['url'], source_doc=srcdoc(d), quote=q, note=''))
        else: problems.append((k, 'price'))
    elif price.get(k):
        q, url, _, dt = price[k]
        d = next(x for x in docs(k) if x['url'] == url)
        m = re.search(r'HK\$ ?([0-9]+(?:\.[0-9]+)?)', q)
        rows.append(dict(id=k, field='offer_price', value=m.group(1), unit='HKD per share', source_url=url, source_doc=srcdoc(d), quote=q.strip(), note=''))
    else: problems.append((k, 'price'))
    # shares
    for field, anc, n, note in SH.get(k, []):
        d, q = find(k, anc, n)
        if not d: problems.append((k, field)); continue
        rows.append(dict(id=k, field=field, value=num(n), unit='shares', source_url=d['url'], source_doc=srcdoc(d), quote=q, note=note))
    if k not in SH: problems.append((k, 'shares: no spec'))
    if k in OSA:
        d, q = find(k, OSA[k], 'Offer Size Adjustment Option', maxlen=400)
        m = re.search(OSA[k], norm(d['path']))
        rows.append(dict(id=k, field='offer_size_adjustment', value='see quote', unit='text', source_url=d['url'], source_doc=srcdoc(d), quote=norm(d['path'])[m.start():m.start()+260].rsplit(' ',1)[0], note=''))
    # listing date: first allotment/price doc that states it
    got = None
    for d in docs(k):
        m = re.search(DEAL, norm(d['path']))
        if m and to_iso(m.group(1)):
            got = (d, m); break
    if got:
        d, m = got
        rows.append(dict(id=k, field='listing_date', value=to_iso(m.group(1)), unit='date', source_url=d['url'], source_doc=srcdoc(d), quote=m.group(0), note='Scheduled first day of dealings'))
    else: problems.append((k, 'listing_date'))
    # HK$ per US$: Federal Reserve H.10 (FRED DEXHKUS) on the listing date
    ld = next((r['value'] for r in rows if r['id'] == k and r['field'] == 'listing_date'), None)
    if ld: rows.append(fred.row(k, 'DEXHKUS', ld))
    else: problems.append((k, 'fx'))
json.dump(rows, open(SP + 'hk_rows.json', 'w'), indent=0, ensure_ascii=False)
print(len(rows), 'rows'); print('problems', problems)
