# -*- coding: utf-8 -*-
"""
阿朱说 公众号文章爬虫 — 多源发现
源1: 搜狗微信文章搜索 type=2 (query=阿朱说)
源2: 搜狗微信账号搜索 type=1 (找到账号主页)
源3: 搜狗文章搜索 + 关键词 (股票/A股/投资/估值...) 分页
输出: articles/index.json + articles/raw_*.html
"""
import json, os, re, time, random, hashlib, urllib.parse
import urllib.request, http.cookiejar

BASE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(BASE, "articles")
os.makedirs(ART, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
opener.addheaders = [
    ("User-Agent", UA),
    ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
    ("Accept-Language", "zh-CN,zh;q=0.9"),
    ("Referer", "https://weixin.sogou.com/"),
]

def fetch(url, name, retry=2):
    for i in range(retry + 1):
        try:
            req = urllib.request.Request(url)
            with opener.open(req, timeout=25) as r:
                html = r.read().decode("utf-8", "ignore")
            path = os.path.join(ART, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            return html
        except Exception as e:
            print(f"  fetch fail {name} ({i}): {e}")
            time.sleep(2 + random.random() * 3)
    return None

def main():
    index = {"articles": [], "accounts": []}

    # ---------- 源1: 账号搜索 ----------
    q = urllib.parse.quote("阿朱说")
    html = fetch(f"https://weixin.sogou.com/weixin?type=1&query={q}", "raw_account_search.html")
    if html:
        # 账号列表: <a ... href="/websearch/art.jsp?..." 或 直接 account 链接
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*uigs="account_name_[^"]*"[^>]*>(.*?)</a>', html, re.S):
            href, name = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
            index["accounts"].append({"name": name, "href": href})
        # 备用: 从新闻列表中的 account 块
        for m in re.finditer(r'<p class="tit">\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
            href, name = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if name and not any(a["name"] == name for a in index["accounts"]):
                index["accounts"].append({"name": name, "href": href})
    print(f"accounts found: {len(index['accounts'])}")
    for a in index["accounts"]:
        print("  -", a["name"], a["href"][:80])

    # ---------- 源2: 文章搜索 "阿朱说" ----------
    for page in range(1, 4):
        url = f"https://weixin.sogou.com/weixin?type=2&query={q}&page={page}"
        html = fetch(url, f"raw_art_search_p{page}.html")
        if not html:
            continue
        items = parse_news_list(html)
        print(f"page {page}: {len(items)} items")
        index["articles"].extend(items)
        time.sleep(2 + random.random() * 2)
        if len(items) < 10:
            break

    # ---------- 源3: 关键词文章搜索 ----------
    for kw in ["阿朱说 股票", "阿朱说 A股", "阿朱说 投资"]:
        q2 = urllib.parse.quote(kw)
        html = fetch(f"https://weixin.sogou.com/weixin?type=2&query={q2}", f"raw_art_kw_{hashlib.md5(kw.encode()).hexdigest()[:6]}.html")
        if html:
            items = parse_news_list(html)
            print(f"kw [{kw}]: {len(items)} items")
            index["articles"].extend(items)
        time.sleep(2 + random.random() * 2)

    # 去重
    seen, uniq = set(), []
    for a in index["articles"]:
        if a["url"] and a["url"] not in seen:
            seen.add(a["url"])
            uniq.append(a)
    index["articles"] = uniq

    with open(os.path.join(ART, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"\nTOTAL unique articles: {len(uniq)}")

def parse_news_list(html):
    items = []
    for m in re.finditer(r'<li id="sogou_vr_11002601_box_\d+"[^>]*>(.*?)</li>', html, re.S):
        block = m.group(1)
        tm = re.search(r'<h3>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not tm:
            continue
        url, title = tm.group(1), re.sub(r"<[^>]+>", "", tm.group(2)).strip()
        sm = re.search(r'<p class="txt-info"[^>]*>(.*?)</p>', block, re.S)
        summary = re.sub(r"<[^>]+>", "", sm.group(1)).strip() if sm else ""
        am = re.search(r'<a[^>]*class="account"[^>]*>(.*?)</a>', block, re.S)
        account = re.sub(r"<[^>]+>", "", am.group(1)).strip() if am else ""
        dm = re.search(r'timeConvert\(\'?(\d{9,10})\'?\)', block)
        date = dm.group(1) if dm else ""
        if url.startswith("/"):
            url = "https://weixin.sogou.com" + url
        items.append({"title": title, "url": url, "summary": summary,
                      "account": account, "date": date})
    return items

if __name__ == "__main__":
    main()
