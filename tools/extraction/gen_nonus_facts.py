"""Non-US deal facts: China A extras, India (final prospectuses), global deals, FX and sector.
Every value is printed in its quote; quotes are exact substrings of the whitespace-normalised source text."""
import json, re, os, sys, csv, datetime
SP = 'tools/extraction/'
sys.path.insert(0, SP + 'bin')
import fred
R = './'
rows, problems = [], []
deals = {}
for f in ('deals.csv', 'deals_asia.csv'):
    for r in csv.DictReader(open(R + 'data/' + f)):
        deals.setdefault(r['id'], r)

def norm_file(p):
    return re.sub(r'\s+', ' ', open(R + p, errors='ignore').read())

def add(id_, field, value, unit, url, doc, quote, note='', local=None):
    if local:
        t = norm_file(local)
        if quote not in t:
            problems.append((id_, field, 'quote not in source')); return
    rows.append(dict(id=id_, field=field, value=value, unit=unit, source_url=url, source_doc=doc, quote=quote, note=note))

def find(local, pat, group=1):
    t = norm_file(local); m = re.search(pat, t)
    return (m.group(0), m.group(group)) if m else (None, None)

def yahoo_first(id_):
    t = deals[id_]['ticker']; p = R + f'data/raw/yahoo/{t}.json'
    if not os.path.exists(p): return None
    ft = json.load(open(p))['chart']['result'][0]['meta'].get('firstTradeDate')
    if not ft: return None
    d = datetime.datetime.fromtimestamp(ft, datetime.timezone.utc).date().isoformat()
    add(id_, 'yahoo_first_trade_date', d, 'date', f'data/raw/yahoo/{t}.json', 'Yahoo Finance chart API, meta.firstTradeDate', f'"firstTradeDate": {ft}')
    return d

def iso(s, fmts=('%B %d, %Y', '%d %B %Y')):
    s = s.replace('  ', ' ').strip()
    for f in fmts:
        try: return datetime.datetime.strptime(s.title() if s.isupper() else s, f).date().isoformat()
        except ValueError: pass
    raise ValueError(s)

def listing_from(id_):
    """Same rule as facts.listing_date."""
    f = {r['field']: r['value'] for r in rows if r['id'] == id_}
    if 'listing_date' in f: return f['listing_date']
    yd, pd = f.get('yahoo_first_trade_date'), f.get('prospectus_date')
    if yd and pd and 0 <= (datetime.date.fromisoformat(yd) - datetime.date.fromisoformat(pd)).days <= 10:
        return yd
    if f.get('scheduled_listing_date'): return f['scheduled_listing_date']
    return pd or yd

# ---------------- China A: rows already built from CNINFO documents, plus gaps ----------------
cn = json.load(open(SP + 'cn_rows.json'))
for r in cn:
    rows.append({**r, 'value': r['value']})
cn_docs = json.load(open(R + 'data/cn/cninfo_docs.json')) if os.path.exists(R + 'data/cn/cninfo_docs.json') else {}
q = '上市时间为 2022 年 1 月 26 日'
src = next(r for r in cn if r['id'] == 'JINKO_A')
add('JINKO_A', 'listing_date', '2022-01-26', 'date', src['source_url'], src['source_doc'], q, local='data/cn/JINKO_A_listing.txt')
gp = next(r for r in cn if r['id'] == 'GTJA_A' and r['field'] == 'shares_after_offering_1')
add('GTJA_A', 'prospectus_date', '2015-06-18', 'date', gp['source_url'], gp['source_doc'], '发行日期： 2015 年 6 月 18 日', note='Offering date on the prospectus cover', local='data/cn/GTJA_A_prospectus.txt')
yahoo_first('GTJA_A')

# ---------------- India: final prospectuses ----------------
IN_SRC = {
 'COALINDIA': 'https://www.citigroup.com/rcs/citigpa/storage/public/India/regulatory-disclosures/coal-india-limited-prospectus.pdf',
 'SBILIFE': 'https://www.citigroup.com/rcs/citigpa/storage/public/India/regulatory-disclosures/SBI-Life-Insurance-Prospectus.pdf',
 'GICRE': 'https://www.citigroup.com/rcs/citigpa/storage/public/India/regulatory-disclosures/Suraksha-Prospectus.pdf',
 'NIACL': 'https://www.nomuranow.com/portal/site/nnextranet/resources/assets/files/NIA_Prospectus.pdf',
 'HDFCLIFE': 'https://www.nomuranow.com/portal/site/nnextranet/resources/assets/files/hdfcslip.pdf',
 'BANDHAN': 'https://www.goldmansachs.com/worldwide/india/ipo/bandhan-bank-limited/bandhan-bank-prospectus.pdf',
 'HAL': 'https://www.sbicaps.com/wp-content/uploads/2021/10/Hindustan_Aeronautics_Limited_Prospectus.pdf',
 'SBICARD': 'https://business.bofa.com/content/dam/flagship/in/en/investment-banking/SBI-Cards-and-Payment-Services-Limited-Prospectus.pdf',
 'POLICYBZR': 'https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/discover-products/wholesale-banking/investment-banking/offer-documents/pb-fintech-limited-prospectus.pdf',
 'STARHEALTH': 'https://business.bofa.com/content/dam/flagship/in/en/investment-banking/Star-Health-and-Allied-Insurance-Company-Limited-Prospectus.pdf',
 'LIC': 'https://www.bseindia.com/corporates/download/318111/IPO%20BasisOfAllotment/Life%20Insurance%20Corporation%20of%20India%20-%20Prospectus%20(May%2012,%202022)_20220512195642.pdf',
 'MANKIND': 'https://www.jefferies.com/wp-content/uploads/sites/4/2023/10/050323-mankind-pharma-limited-prospectus-1.pdf',
 'BAJAJHFL': 'https://business.bofa.com/content/dam/flagship/in/en/investment-banking/Bajaj-Housing-Finance-Limited-IPO-Prospectus.pdf',
 'HYUNDAIIN': 'https://www.hyundai.com/content/dam/hyundai/in/en/data/investor-relations/material-documents/prospectus.pdf',
 'WAAREE': 'https://nsearchives.nseindia.com/corporate/FP_INE377N01017_24OCT2024.pdf',
 'SWIGGY': 'https://business.bofa.com/content/dam/flagship/in/en/investment-banking/Swiggy-Limited-IPO-Prospectus.pdf',
 'NTPCGREEN': 'https://www.sebi.gov.in/sebi_data/attachdocs/nov-2024/1732529788335.pdf',
 'HDBFS': 'https://www.morganstanley.com/content/dam/msdotcom/en/indiaofferdocuments/pdfs/HDB_Financial_Services_Limited_Prospectus.pdf',
 'TATACAP': 'https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/discover-products/wholesale-banking/investment-banking/Tata-Capital-Limited-Prospectus.pdf',
 'LGEIND': 'https://www.morganstanley.com/content/dam/msdotcom/en/indiaofferdocuments/pdfs/LG_Electronics_India_Limited_Prospectus.pdf',
 'LENSKART': 'https://www.morganstanley.com/content/dam/msdotcom/en/indiaofferdocuments/pdfs/Lenskart_Solution_Limited_Prospectus.pdf',
 'GROWW': 'https://resources.groww.in/web-assets/media-library/2025/11/Prospectus.pdf',
 'MEESHO': 'https://www.morganstanley.com/content/dam/msdotcom/en/indiaofferdocuments/pdfs/Meesho_Limited_Prospectus.pdf',
 'ZOMATO': 'https://www.morganstanley.com/content/dam/msdotcom/en/indiaofferdocuments/pdfs/Zomato_Limited_Prospectus.pdf',
 'NYKAA': 'https://nsearchives.nseindia.com/corporate/FP_INE388Y01029_08NOV2021.pdf',
 'PAYTM': 'https://nsearchives.nseindia.com/corporate/FP_INE982J01020_16NOV2021.pdf',
 'ICICIAMC': 'https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/pdf/ICICI-Prudential-Asset-Management-Company-Limited-Prospectus.pdf',
}
PRICE_P = [r'OFFER PRICE IS (?:₹|Rs\.?|`) ?([0-9][0-9,.]*[0-9])', r'ISSUE PRICE IS (?:₹|Rs\.?|`) ?([0-9][0-9,.]*[0-9])',
           r'(?:Offer|Issue) Price[”"]? (?:₹|`|Rs\.?) ?([0-9][0-9,.]*[0-9]) per Equity Share',
           r'Offer Price, (?:that is|price being|being),? ?(?:₹|`) ?([0-9][0-9,.]*[0-9]) per Equity Share',
           r'Offer Price:? The final price (?:being |of )(?:₹|`) ?([0-9][0-9,.]*[0-9])', r'OFFER PRICE: (?:₹|`) ?([0-9][0-9,.]*[0-9]) PER EQUITY SHARE',
           r'(?:Offer|Issue) Price (?:is|of) (?:₹|`|Rs\.?) ?([0-9][0-9,.]*[0-9])(?: per Equity Share|\.00 per Equity Share| has been determined)']
SH_P = [r'Equity Shares outstanding (?:after|post) the (?:Offer|Issue):? ([0-9][0-9,]*[0-9])\*?\^? Equity Shares',
        r'PAID[- ]UP (?:EQUITY )?(?:SHARE )?CAPITAL AFTER THE (?:OFFER|ISSUE)\*? ?\*? ?([0-9][0-9,]*[0-9])\*?\^?\*? (?:fully paid[- ]up )?(?:Equity|equity) [Ss]hares']
DATE_P = r'PROSPECTUS (?:Dated:? |Delivered[^.]{0,120}?Dated )?([A-Z][a-z]+ \d{1,2}, \d{4}|[A-Z]+ \d{1,2}, \d{4})'
for k, url in IN_SRC.items():
    local = f'data/in/pros/{k}.txt'
    doc = 'Final prospectus filed with the Registrar of Companies'
    q, v = None, None
    for p in PRICE_P:
        q, v = find(local, p)
        if q: break
    if q: add(k, 'offer_price', v.replace(',', ''), 'INR per share', url, doc, q, local=local)
    else: problems.append((k, 'price'))
    q = None
    for p in SH_P:
        q, v = find(local, p)
        if q: break
    if q: add(k, 'shares_after_offering_1', v.replace(',', ''), 'shares', url, doc, q, note='Equity shares outstanding after the offer, as stated in the prospectus', local=local)
    else: problems.append((k, 'shares'))
    t = norm_file(local)[:4000]
    m = re.search(DATE_P, t)
    if m: add(k, 'prospectus_date', iso(m.group(1)), 'date', url, doc, m.group(0), local=local)
    else: problems.append((k, 'date'))
    m = re.search(r'Commencement of trading[^.]{0,60}?(?:On or about|on or about)?,? ?(?:\w+day,? )?([A-Z][a-z]+ \d{1,2}, \d{4})', norm_file(local))
    if m: add(k, 'scheduled_listing_date', iso(m.group(1)), 'date', url, doc, m.group(0), note='Scheduled commencement of trading stated in the prospectus', local=local)
    yd = yahoo_first(k)
    ld = listing_from(k)
    if m and yd and yd != iso(m.group(1)): print('LISTING DATE CHECK', k, 'scheduled', iso(m.group(1)), 'yahoo', yd, '-> used', ld)
    if ld: rows.append(fred.row(k, 'DEXINUS', ld))

add('MANKIND', 'listing_date', '2023-05-09', 'date', 'https://indiaipo.jpmorgan.com/content/dam/jpm/india-private-limited/documents/mankind-basis-allotment.pdf',
    'Mankind Pharma basis of allotment advertisement (May 2023)', 'the trading will commence on May 9, 2023', local='data/in/pros/MANKIND_boa.txt')
rows[:] = [r for r in rows if not (r['id'] == 'MANKIND' and r['field'] in ('fx_listing_per_usd',))]
rows.append(fred.row('MANKIND', 'DEXINUS', listing_from('MANKIND')))

# ---------------- Global deals ----------------
G = 'data/global/'
# Siemens Healthineers: Deutsche Boerse release on the listing day
u = 'https://deutsche-boerse.com/dbg-en/media/news-stories/press-releases/Siemens-Healthineers-AG-listed-on-the-Frankfurt-Stock-Exchange-today-146750'
d = 'Deutsche Börse press release, 16 March 2018'
add('SHL', 'offer_price', '28.00', 'EUR per share', u, d, 'The Siemens Healthineers AG shares opened trading at €29.10, following an issue price of €28.00', local=G + 'SHL_dbg.txt')
add('SHL', 'shares_after_offering_1', '1000000000', 'shares', u, d, 'Placement volume amounted to 150 million shares, with a total of one billion shares admitted for trading', local=G + 'SHL_dbg.txt')
add('SHL', 'listing_date', '2018-03-16', 'date', u, d, 'Release date: Mar 16, 2018 | Deutsche Börse Medical technology company lists in Prime Standard / Initial price €29.10 Siemens Healthineers AG (ISIN: DE000SHL1006) today completed one of the largest German IPOs in recent years and is now listed', local=G + 'SHL_dbg.txt')
# Porsche
u = 'https://newsroom.porsche.com/en/2022/company/porsche-ag-initial-public-offering-p911-frankfurt-stock-exchange-29830.html'
d = 'Porsche AG press release, 29 September 2022'
add('PORSCHE', 'offer_price', '82.50', 'EUR per share', u, d, 'Offer price set at 82.50 euros per Preferred Share offered', local=G + 'PORSCHE_pr.txt')
add('PORSCHE', 'listing_date', '2022-09-29', 'date', u, d, '29/09/2022 Dr. Ing. h.c. F. Porsche AG ("Porsche AG" and, together with its consolidated subsidiaries, the "Porsche Group" or "Porsche") has successfu', note='Release dated 29/09/2022 announcing the preferred shares are listed', local=G + 'PORSCHE_pr.txt')
u = 'https://moneybase.com/wp-content/uploads/2022/09/prospectus_porsche.pdf'
d = 'Porsche AG prospectus dated September 19, 2022'
add('PORSCHE', 'shares_after_offering_1', '455500000', 'shares', u, d, 'the share capital of the Company amounts to EUR 911,000,000 and is divided into 455,500,000 Preferred Shares and 455,500,000 Ordinary Shares', note='Preferred shares', local=G + 'PORSCHE_prospectus.txt')
add('PORSCHE', 'shares_after_offering_2', '455500000', 'shares', u, d, 'the share capital of the Company amounts to EUR 911,000,000 and is divided into 455,500,000 Preferred Shares and 455,500,000 Ordinary Shares', note='Ordinary shares (unlisted, valued at the offer price like the preferred shares)', local=G + 'PORSCHE_prospectus.txt')
# Saudi Aramco
u = 'https://cma.gov.sa/en/Market/Prospectuses/Documents/Saudi_Aramco_Prospectus.pdf'
d = 'Saudi Aramco prospectus (Capital Market Authority)'
add('ARAMCO', 'shares_after_offering_1', '200000000000', 'shares', u, d, 'The current share capital of Saudi Aramco is sixty billion Saudi Riyals (SAR 60,000,000,000), consisting of two hundred billion (200,000,000,000) ordinary shares with no par value', note='All offered shares were existing shares sold by the Government', local=G + 'ARAMCO_prospectus.txt')
add('ARAMCO', 'fx_listing_per_usd', '3.75', 'SAR per USD', u, d, 'the Saudi Riyal has been pegged to the U.S. Dollar at a fixed exchange rate of SAR 3.75 = U.S.$1.00', local=G + 'ARAMCO_prospectus.txt')
u = 'https://www.aramco.com/-/media/images/investors/saudi-aramco-final-price-announcement-en.pdf'
d = 'Saudi Aramco final price announcement, 5 December 2019 (read with a web fetch; the host refuses automated downloads, so no local copy)'
add('ARAMCO', 'offer_price', '32', 'SAR per share', u, d, 'the setting of the final offer price (the "Final Offer Price") for the Offering at SAR 32.')
add('ARAMCO', 'prospectus_date', '2019-12-05', 'date', u, d, '5 December 2019', note='Date of the final price announcement, used to check the Yahoo first trade date')
yahoo_first('ARAMCO')
# DEWA
u = 'https://fnn.prod.fs.tomcat2.gfm.support/File.Mix_Announcement_File/5C028E95-3008-4517-B65F-01A3FB38F425.pdf'
d = 'Dubai Financial Market: prospectus announcement concerning listing the shares of DEWA'
add('DEWA', 'shares_after_offering_1', '50000000000', 'shares', u, d, 'The share capital of the Company as at the date of the listing has been set at AED 500,000,000 (five hundred million UAE dirhams) divided into 50,000,000,000 (fifty billion) shares', local=G + 'DEWA_dfm.txt')
u = 'https://ipo.emiratesnbd.com/-/media/enbd/files/ipo/prospectus-en.pdf'
add('DEWA', 'fx_listing_per_usd', '3.6725', 'AED per USD', u, 'DEWA prospectus', 'The value of UAE dirhams has been pegged to US dollar at a rate of AED 3.6725 per USD 1 since 1997', local=G + 'DEWA_prospectus.txt')
u = 'https://www.dewa.gov.ae/~/media/Files/IPO/FinalPriceAnnouncement_EN.ashx'
d = 'DEWA final price announcement, 6 April 2022 (read with a web fetch; the host refuses automated downloads, so no local copy)'
add('DEWA', 'offer_price', '2.48', 'AED per share', u, d, 'it has set the final offer price for its IPO at AED 2.48 per share.')
add('DEWA', 'listing_date', '2022-04-12', 'date', u, d, 'DEWA is expected to commence trading on the Dubai Financial Market (“DFM”) on 12 April 2022')
# SoftBank Corp
u = 'https://www.softbank.jp/corp/news/press/sbkk/2018/20181210_01/'
d = 'SoftBank Corp. notice on determination of the offer price, 10 December 2018'
open(R + G + 'SBK_price.txt', 'w').write(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>|<style.*?</style>', '', open(R + G + 'SBK_price.html', errors='ignore').read(), flags=re.S))))
add('SBK', 'offer_price', '1500', 'JPY per share', u, d, '売出価格 1株につき 金 1,500円', local=G + 'SBK_price.txt')
add('SBK', 'prospectus_date', '2018-12-10', 'date', u, d, '2018年12月10日 ソフトバンク株式会社 当社普通株式の売出価格', note='Date of the pricing notice, used to check the Yahoo first trade date', local=G + 'SBK_price.txt')
u = 'https://disclosure2dl.edinet-fsa.go.jp/searchdocument/pdf/S100EJ15.pdf'
d = 'SoftBank Corp. securities registration statement (有価証券届出書) filed 12 November 2018 on EDINET (image PDF; read with a web fetch)'
add('SBK', 'shares_after_offering_1', '4787145170', 'shares', u, d, '本書提出日現在の発行済株式総数は4,787,145,170株となっています', note='The offering was a sale of existing shares by SoftBank Group; issued shares as of the filing date')
yahoo_first('SBK')
# Japan Post Holdings
u = 'https://search.sbisec.co.jp/v2/popwin/info/connect/ipo/201509102103.pdf'
d = 'Japan Post Holdings prospectus amendment (株式売出届出目論見書の訂正事項分, 第3回訂正分, October 2015)'
add('JPH', 'offer_price', '1400', 'JPY per share', u, d, '平成27年10月26日に決定された売出価格(1,400円)', local=G + 'JPH_amend3.txt')
add('JPH', 'shares_after_offering_1', '4500000000', 'shares', u, d, '所有株式数 (株) 財務大臣 東京都千代田区 4,500,000,000', note='The Minister of Finance held all 4,500,000,000 shares (100.00%) before the offering, which was a sale of existing shares', local=G + 'JPH_amend3.txt')
add('JPH', 'prospectus_date', '2015-10-26', 'date', u, d, '平成27年10月26日に決定された売出価格', note='Pricing date, used to check the Yahoo first trade date', local=G + 'JPH_amend3.txt')
yahoo_first('JPH')
for k, ser in [('SHL', 'DEXUSEU'), ('PORSCHE', 'DEXUSEU'), ('SBK', 'DEXJPUS'), ('JPH', 'DEXJPUS')]:
    rows.append(fred.row(k, ser, listing_from(k)))

# China A FX on the listing date
for k in sorted({r['id'] for r in cn}):
    ld = listing_from(k)
    if ld: rows.append(fred.row(k, 'DEXCHUS', ld))
    else: problems.append((k, 'cn listing date'))

# Sector (Yahoo Finance search API) for every non-US deal handled here or in the HK file
hk = json.load(open(SP + 'hk_rows.json'))
ids = sorted({r['id'] for r in rows} | {r['id'] for r in hk})
for k in ids:
    t = deals[k]['ticker']; p = R + f'data/raw/yahoo_profile/{t}.json'
    qo = json.load(open(p))
    rows.append(dict(id=k, field='sector', value=qo['quote'].get('sector'), unit='Yahoo Finance sector', source_url=qo['query_url'],
                     source_doc='Yahoo Finance search API (retrieved 22 Oct 2026)', quote=f"industry: {qo['quote'].get('industry')}", note=''))
json.dump(rows, open(SP + 'nonus_rows.json', 'w'), ensure_ascii=False, indent=0)
print(len(rows), 'rows'); print('problems', problems)
