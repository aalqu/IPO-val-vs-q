"""cninfo helper: search announcements and download, with retries."""
import json, sys, time, urllib.request, urllib.parse
UA = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/x-www-form-urlencoded"}
def post(url, data, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), headers=UA)
            return json.loads(urllib.request.urlopen(req, timeout=40).read())
        except Exception as e:
            err = e; time.sleep(2 + i * 2)
    raise err
def search(code, org, col, dates, key=""):
    d = post("https://www.cninfo.com.cn/new/hisAnnouncement/query",
             {"pageNum": 1, "pageSize": 50, "column": col, "tabName": "fulltext", "plate": "", "stock": f"{code},{org}",
              "searchkey": key, "secid": "", "category": "", "trade": "", "seDate": dates, "sortName": "", "sortType": "", "isHLtitle": "true"})
    return [(a["announcementTitle"], a["adjunctUrl"], a["adjunctSize"]) for a in (d.get("announcements") or [])]
def download(path, dest, tries=6):
    for i in range(tries):
        try:
            data = urllib.request.urlopen(urllib.request.Request("https://static.cninfo.com.cn/" + path, headers={"User-Agent": "Mozilla/5.0"}), timeout=180).read()
            if data[:4] == b"%PDF":
                open(dest, "wb").write(data); return len(data)
        except Exception as e:
            time.sleep(3 + i * 2)
    return 0
if __name__ == "__main__":
    if sys.argv[1] == "search":
        for t in search(*sys.argv[2:]): print(*t)
    else:
        print(download(sys.argv[2], sys.argv[3]))
