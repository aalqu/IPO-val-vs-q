import subprocess,re,urllib.parse,time,sys
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36'
def get(url,out=None,timeout=120):
    cmd=['curl','-s','-L','--max-time',str(timeout),'-A',UA,url]
    if out: cmd+=['-o',out]
    r=subprocess.run(cmd,capture_output=True)
    return r.stdout
def search(q):
    h=get('https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=3&ssid=15&smid=11&search='+urllib.parse.quote(q)).decode('utf-8','ignore')
    rows=re.findall(r'<td>([A-Za-z]{3} \d{1,2}, \d{4})</td>\s*<td[^>]*>\s*<a href="(https://www\.sebi\.gov\.in/filings/public-issues/[^"]+)"[^>]*title="([^"]*)"',h)
    if not rows:
        rows=[('',u,'') for u in sorted(set(re.findall(r'https://www\.sebi\.gov\.in/filings/public-issues/[^"]+\.html',h)))]
    return rows
def pdf_of(page):
    h=get(page).decode('utf-8','ignore')
    m=re.findall(r"(?:file=|src=['\"])(https?://www\.sebi\.gov\.in/sebi_data/attachdocs/[^'\"&]+\.pdf)",h)
    return m[0] if m else None
if __name__=='__main__':
    for q in sys.argv[1:]:
        for r in search(q): print(q,'|',r)
        time.sleep(1)
