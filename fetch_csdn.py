# -*- coding: utf-8 -*-
"""解析 CSDN 镜像博客列表，筛选股票类文章并抓取全文"""
import urllib.request, re, html as H, time, json, os

BASE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.join(BASE, "articles")
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36'}

def get(url, retry=2):
    for i in range(retry + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            return urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')
        except Exception as e:
            if i == retry:
                raise
            time.sleep(3 + i * 3)

STOCK_KW = ['股', 'A股', '大A', '牛市', '熊市', '炒股', '量化', '资本', '基金', '涨停', '炒',
            '上证', '深证', '打板', '游资', '主力', '板块', '经济', '金融', '市值', '估值']

def parse_list(html):
    items = []
    for m in re.finditer(r'<div class="article-item-box[^"]*" data-articleid="(\d+)">(.*?)(?=<div class="article-item-box|$)', html, re.S):
        aid, block = m.group(1), m.group(2)
        tm = re.search(r'<h4 class="">\s*<a href="([^"]+)"[^>]*>\s*(?:<span[^>]*>[^<]*</span>\s*)?(.*?)</a>', block, re.S)
        if not tm:
            continue
        url, title = tm.group(1), H.unescape(re.sub(r'\s+', ' ', tm.group(2))).strip()
        sm = re.search(r'<p class="content">(.*?)</p>', block, re.S)
        summ = H.unescape(re.sub(r'<[^>]+>', '', sm.group(1))).strip() if sm else ''
        dm = re.search(r'<span class="date">([^<]+)</span>', block)
        date = dm.group(1)[:10] if dm else ''
        items.append({'id': aid, 'title': title, 'url': url, 'summary': summ, 'date': date})
    return items

def extract_detail(html):
    m = re.search(r'<div[^>]*id="content_views"[^>]*>(.*?)</div>\s*<div', html, re.S)
    if not m:
        m = re.search(r'<article[^>]*>(.*?)</article>', html, re.S)
    body = m.group(1) if m else ''
    body = re.sub(r'<br[^>]*>', '\n', body)
    body = re.sub(r'</p>', '\n', body)
    body = re.sub(r'<[^>]+>', '', body)
    body = H.unescape(body)
    body = re.sub(r'[ \t]+', ' ', body)
    body = re.sub(r'\n\s*\n+', '\n\n', body).strip()
    return body

def main():
    all_items = []
    for page_url in ['https://blog.csdn.net/david_lv/article/list']:
        try:
            html = get(page_url)
            items = parse_list(html)
            print(f'{page_url}: {len(items)} items')
            all_items.extend(items)
        except Exception as e:
            print(f'{page_url} ERR: {e}')
        time.sleep(2)

    # 去重
    seen, uniq = set(), []
    for it in all_items:
        if it['id'] not in seen:
            seen.add(it['id'])
            uniq.append(it)

    stock = [it for it in uniq if any(k in it['title'] + it['summary'] for k in STOCK_KW)]
    print(f'\n全部 {len(uniq)} 篇，股票相关 {len(stock)} 篇:')
    for it in stock:
        print(f"  [{it['date']}] {it['title']}")

    # 抓全文
    results = []
    for i, it in enumerate(stock, 1):
        fname = os.path.join(ART, f"csdn_{it['id']}.txt")
        try:
            html = get(it['url'])
            txt = extract_detail(html)
            if len(txt) > 300:
                with open(fname, 'w', encoding='utf-8') as f:
                    f.write(f"标题: {it['title']}\n日期: {it['date']}\n链接: {it['url']}\n\n{txt}")
                it2 = dict(it); it2['len'] = len(txt); it2['file'] = fname
                results.append(it2)
                print(f"[{i}/{len(stock)}] OK {len(txt)}chars {it['title']}")
            else:
                print(f"[{i}/{len(stock)}] 内容过短 {len(txt)} {it['title']}")
                # 摘要保底
                it2 = dict(it); it2['len'] = 0; it2['file'] = ''
                results.append(it2)
        except Exception as e:
            print(f"[{i}/{len(stock)}] ERR {e} {it['title']}")
            it2 = dict(it); it2['len'] = -1; it2['file'] = ''
            results.append(it2)
        time.sleep(1.5)

    json.dump(results, open(os.path.join(ART, 'csdn_stock.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    ok = sum(1 for r in results if r['len'] > 300)
    print(f'\n全文抓取成功 {ok}/{len(results)}')

if __name__ == '__main__':
    main()
