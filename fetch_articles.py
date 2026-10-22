# -*- coding: utf-8 -*-
"""抓取阿朱说股票类文章正文（通过搜狗 redirect 链接）"""
import json, os, re, time, random, urllib.request, urllib.parse, http.cookiejar

BASE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(BASE, "articles")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
opener.addheaders = [("User-Agent", UA),
                     ("Accept-Language", "zh-CN,zh;q=0.9"),
                     ("Referer", "https://weixin.sogou.com/")]

STOCK_KW = ["股市", "股票", "A股", "大A", "炒股", "上证", "证券", "保股市"]

def main():
    items = json.load(open(os.path.join(ART, "index2.json"), encoding="utf-8"))
    # 去重取阿朱说账号
    seen, cands = set(), []
    for a in items:
        if a["account"] != "阿朱说":
            continue
        if not a["url"].startswith("/link"):
            continue
        key = (a["title"], a["date"])
        if key in seen:
            continue
        seen.add(key)
        if any(k in a["title"] for k in STOCK_KW) or a["date"] and int(a["date"]) > 1654000000:
            cands.append(a)
    print(f"候选文章: {len(cands)}")

    out = []
    for i, a in enumerate(cands, 1):
        url = "https://weixin.sogou.com" + a["url"].replace("&amp;", "&")
        url = urllib.parse.quote(url, safe=":/?&=%.-_~")
        fname = os.path.join(ART, f"art_{i:02d}.html")
        ok = False
        for attempt in range(3):
            try:
                req = urllib.request.Request(url)
                with opener.open(req, timeout=30) as r:
                    html = r.read().decode("utf-8", "ignore")
                    final = r.geturl()
                if "js_content" in html or "rich_media" in html or len(html) > 20000:
                    with open(fname, "w", encoding="utf-8") as f:
                        f.write(html)
                    a2 = dict(a); a2["final_url"] = final; a2["file"] = f"art_{i:02d}.html"
                    a2["url"] = final
                    out.append(a2)
                    ok = True
                    print(f"[{i:2d}] OK {len(html)//1024}KB {a['title'][:40]}")
                    break
                else:
                    print(f"[{i:2d}] small resp {len(html)}B, retry {attempt}")
                    time.sleep(3)
            except Exception as e:
                print(f"[{i:2d}] ERR {e} retry {attempt}")
                time.sleep(4)
        if not ok:
            print(f"[{i:2d}] FAILED {a['title'][:40]}")
        time.sleep(1.5 + random.random() * 2)

    json.dump(out, open(os.path.join(ART, "stock_articles.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n成功抓取正文: {len(out)}")

if __name__ == "__main__":
    main()
