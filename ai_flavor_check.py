# -*- coding: utf-8 -*-
"""AI 味体检: 把"读起来像 AI"拆成可计量的指标。

用法: python ai_flavor_check.py <markdown文件> [标签]
输出七类指标, 供润色前后对比。
"""
import io
import os
import re
import sys
import statistics as st

# ---------- 1. 套话词表 ----------
CLICHE = [
    '值得注意的是', '值得强调的是', '需要指出的是', '需要强调的是', '不难看出',
    '不难发现', '不难理解', '总而言之', '综上所述', '由此可见', '总而言之',
    '进一步说明', '这也印证', '这印证了', '这充分说明', '这提示我们', '这提示',
    '这提醒我们', '这一点值得', '具有重要的', '具有较强说服力', '具有说服力',
    '本文首次', '首次系统', '系统考察', '系统地考察', '全面考察',
    '这一结果并不令人意外', '并不令人意外', '与直觉一致', '反直觉',
    '颇具讽刺意味', '令人深思', '值得深思', '不难想见', '显而易见',
    '综上所述', '总的来说', '总的来说', '归根结底', '从某种意义上说',
    '在某种程度上', '某种程度上', '某种意义上', '值得一提的是',
    '我们不难', '可以看到', '可以看出', '需要注意的是', '应当指出',
]
# 真正恶劣的标志词(出现即 AI 概率高)
HARD = ['值得注意的是', '值得强调的是', '需要指出的是', '不难看出', '不难发现',
        '总而言之', '综上所述', '由此可见', '这提示我们', '这提醒我们',
        '具有较强说服力', '反直觉', '并不令人意外', '与直觉一致']


def split_blocks(md):
    """返回 (标题行, 正文块列表)"""
    lines = md.split('\n')
    blocks, cur, cur_head = [], [], '(文首)'
    for ln in lines:
        if re.match(r'^#{1,4}\s', ln):
            if cur:
                blocks.append((cur_head, '\n'.join(cur)))
            cur, cur_head = [], ln.strip()
        else:
            cur.append(ln)
    if cur:
        blocks.append((cur_head, '\n'.join(cur)))
    return blocks


def paras(text):
    out = []
    for p in text.split('\n'):
        p = p.strip()
        if not p:
            continue
        if p.startswith('|') or p.startswith('@@') or p.startswith('$$'):
            continue
        if re.match(r'^\*\*表', p) or re.match(r'^\*\*图', p):
            continue
        if p.startswith('>') or p.startswith('---'):
            continue
        # 参考文献条目(编号列表)与英文摘要不计入正文节奏统计
        if re.match(r'^\d+\.\s', p):
            continue
        if re.match(r'^(Abstract|Keywords|JEL)', p):
            continue
        out.append(p)
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else '论文_双重去杠杆陷阱.md'
    tag = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(path)
    md = io.open(path, encoding='utf-8').read()

    blocks = split_blocks(md)
    allp = []
    for h, b in blocks:
        allp.extend(paras(b))
    body = '\n'.join(allp)

    print(f'===== AI 味体检: {tag} =====')
    print(f'总字符(含符号) : {len(md)}')
    print(f'正文段落数     : {len(allp)}')

    # --- 指标1: 恶性套话 ---
    hard_hits = []
    for w in HARD:
        n = body.count(w)
        if n:
            hard_hits.append((w, n))
    hard_hits.sort(key=lambda x: -x[1])
    print('\n[1] 恶性套话(出现即为AI强信号)  合计 %d 次' % sum(n for _, n in hard_hits))
    for w, n in hard_hits:
        print(f'      {w:<12} {n}')

    soft_hits = []
    for w in CLICHE:
        if w in HARD:
            continue
        n = body.count(w)
        if n:
            soft_hits.append((w, n))
    soft_hits.sort(key=lambda x: -x[1])
    print('[2] 软性套话/陈词  合计 %d 次' % sum(n for _, n in soft_hits))
    for w, n in soft_hits[:18]:
        print(f'      {w:<16} {n}')

    # --- 指标3: 加粗密度 ---
    bolds = re.findall(r'\*\*(.+?)\*\*', body)
    print('\n[3] 加粗标记      %d 处; 每千字 %.2f 处'
          % (len(bolds), len(bolds) / max(len(body), 1) * 1000))

    # --- 指标4: "N个X"编号模板 ---
    pats = [
        (r'第[一二三四五六七八九十]+[，、]', '第一/第二…编号'),
        (r'其[一二三四五六七八九十]+[，、：]', '其一/其二…编号'),
        (r'\*\*第[一二三四五六七八九十]+[，、]', '加粗的第一/第二'),
        (r'\*\*其[一二三四五六七八九十]+[，、：]', '加粗的其一/其二'),
        (r'[一二三四五六七八九十]+个(观察|结论|读数|数字|发现|方面|层次|提醒)', 'N个X模板'),
        (r'[一二三四五六七八九十]+点(提醒|含义|观察)', 'N点X模板'),
        (r'^\s*[-*]?\s*\*\*[（(]\d+[)）]', '（1）（2）编号段'),
    ]
    print('[4] 编号/条列模板:')
    tot_tpl = 0
    for p, lab in pats:
        n = len(re.findall(p, body, flags=re.M))
        tot_tpl += n
        print(f'      {lab:<18} {n}')
    print(f'      {"合计":<18} {tot_tpl}')

    # --- 指标5: 段末总结句模板 ---
    tail = re.findall(r'(这(?:一?)(?:进一步|也|充分|直接)?(?:说明|印证|提示|表明|解释|意味)[^。]{0,30}。)', body)
    print('\n[5] 段末"这说明/这提示…"总结句  %d 处' % len(tail))

    # --- 指标6: 句长与段长结构 ---
    sents = [s for s in re.split(r'[。！？；]', body) if len(s.strip()) > 2]
    slen = [len(s.strip()) for s in sents]
    plen = [len(p) for p in allp]
    if slen:
        print('\n[6] 句长  均值 %.1f  标准差 %.1f  最长 %d  最短 %d'
              % (st.mean(slen), st.pstdev(slen), max(slen), min(slen)))
        # 中长句(30-55字)占比 —— 过高说明节奏单调
        mid = sum(1 for x in slen if 30 <= x <= 55) / len(slen)
        print('     30—55字中长句占比 %.1f%%  (>55%% 提示节奏单调)' % (mid * 100))
    if plen:
        print('[6b] 段长  均值 %.1f  标准差 %.1f  (标准差过小=段落同构)'
              % (st.mean(plen), st.pstdev(plen)))

    # --- 指标7: 破折号与括号 ---
    dash = body.count('——')
    # 只统计"补充说明型"长括号: 排除文献引用(含年份或拉丁字母)
    paren = 0
    for m in re.findall(r'（([^）]{4,})）', body):
        if re.search(r'[A-Za-z]', m) or re.search(r'(19|20)\d{2}', m):
            continue
        paren += 1
    print('\n[7] 破折号 %d 处; 长括号补充说明 %d 处; 每千字 %.1f / %.1f'
          % (dash, paren, dash / max(len(body), 1) * 1000,
             paren / max(len(body), 1) * 1000))

    # --- 综合评分 ---
    score = 0
    score += sum(n for _, n in hard_hits) * 3
    score += sum(n for _, n in soft_hits) * 1
    score += max(0, (len(bolds) / max(len(body), 1) * 1000 - 8)) * 2
    score += tot_tpl * 0.8
    score += len(tail) * 1.5
    score += dash / max(len(body), 1) * 1000 * 1.5
    print('\n===== 综合 AI 味评分 (越低越好, 0—30 为干净区) : %.1f =====' % score)


if __name__ == '__main__':
    main()
