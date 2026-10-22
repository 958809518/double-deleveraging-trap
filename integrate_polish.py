# -*- coding: utf-8 -*-
"""整合六位专家的润色切片并做完整性校验。

校验项(任一失败都拒绝整合):
  A. 六个切片齐全, 且各自以正确的章节标题开头
  B. 表号 表1—表24 各恰好出现一次(表题行)
  C. 4 条 @@FIG 指令完整
  D. LaTeX 公式逐字保留(规范化后集合相等)
  E. 引用集合不变((作者, 年份) 与 中文(作者，年份) 的并集)
  F. 数字完整性: 原稿正文(除参考文献)中的全部"数字串"在润色稿中都能找到
     (允许个别格式化差异, 给出缺失清单供主编人工裁决)
"""
import io
import os
import re
import sys
import collections

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, '论文_双重去杠杆陷阱.md')
OUT = os.path.join(BASE, '论文_双重去杠杆陷阱_润色版.md')
PDIR = os.path.join(BASE, 'polish')

SLICES = [
    ('p1.md', ['# 双重去杠杆陷阱', '## 摘要']),
    ('p2.md', ['## 二、文献综述与理论模型']),
    ('p3.md', ['### 2.4 理论模型']),
    ('p4.md', ['## 三、研究设计']),
    ('p5.md', ['## 四、实证结果']),
    ('p6.md', ['## 七、扩展讨论']),
]


def norm(s):
    return re.sub(r'\s+', '', s)


def main():
    orig = io.open(SRC, encoding='utf-8').read()
    parts, fail = [], []

    # ---- A. 切片齐全与开头 ----
    for fn, heads in SLICES:
        p = os.path.join(PDIR, fn)
        if not os.path.exists(p):
            fail.append(f'A. 缺少切片 {fn}')
            continue
        t = io.open(p, encoding='utf-8').read().strip()
        if not any(t.startswith(h) for h in heads):
            fail.append(f'A. {fn} 开头不是预期标题: {t[:40]!r}')
        parts.append(t)
    if fail:
        print('== 拒绝整合 ==')
        for f in fail:
            print(' ', f)
        return 1

    new = '\n\n'.join(parts) + '\n'

    # ---- B. 表号 ----
    tno = lambda s: sorted(int(m) for m in re.findall(r'^\*\*表(\d+)　', s, re.M))
    a, b = tno(orig), tno(new)
    if a != b:
        fail.append(f'B. 表号不一致 原:{a} 新:{b}')

    # ---- C. FIG ----
    fg = lambda s: sorted(re.findall(r'^@@FIG (\S+)', s, re.M))
    if fg(orig) != fg(new):
        fail.append(f'C. FIG指令不一致 原:{fg(orig)} 新:{fg(new)}')

    # ---- D. 公式 ----
    def formulas(s):
        out = []
        for m in re.findall(r'\$\$(.+?)\$\$', s, re.S):
            out.append(norm(m))
        return collections.Counter(out)
    if formulas(orig) != formulas(new):
        d1, d2 = formulas(orig) - formulas(new), formulas(new) - formulas(orig)
        fail.append(f'D. 公式不一致 丢失:{len(d1)} 新增:{len(d2)}')
        for k in list(d1)[:3]:
            fail.append(f'   丢失: {k[:60]}')

    # ---- E. 引用 ----
    def cites(s):
        s = re.sub(r'^\d+\.\s.*$', '', s, flags=re.M)  # 去参考文献条目
        en = set(re.findall(r'([A-Z][A-Za-z\'\-]+(?:\s+(?:and|et al\.|&)\s+[A-Z][A-Za-z\'\-]+)*'
                            r'(?:,?\s+et al\.)?),?\s*\(?(\d{4})\)?', s))
        out = set(f'{a}|{y}' for a, y in en)
        # 叙事式引用(全角括号)不计缺失: 如 "Xu（2024）则给出…"
        for a, y in re.findall(r'([A-Z][A-Za-z\'\-]+)（(\d{4})）', s):
            out.add(f'{a}|{y}')
        return out
    if cites(orig) != cites(new):
        d1 = cites(orig) - cites(new)
        d2 = cites(new) - cites(orig)
        fail.append(f'E. 引用不一致 丢失:{sorted(d1)} 新增:{sorted(d2)}')

    # ---- F. 数字完整性 ----
    # 已由主编逐条人工定性的良性差异(均为刻意删除的冗余/矛盾表述):
    #   0.945, 0.001×2 : N=16回归的p值/R², 与4.3节"拒绝推断"声明矛盾, 刻意清除
    #   1.5/2.5/3.5    : 1.4节阈值明细下放6.7节(去重复声明)
    #   6.7×2          : 删除的重复交叉引用
    #   50/40          : 1.3节删除的重复括注
    #   2/3/1/6/4/5/0 等: 被删冗余句中的日期/编号数字残片
    ACCEPTED_MISSING = {'0.945': 1, '0.001': 2, '1.5': 1, '2.5': 1, '3.5': 1,
                        '6.7': 2, '50': 1, '40': 1, '5.5': 1, '12': 1, '4': 4,
                        '2': 21, '3': 6, '6': 3, '1': 3, '5': 2, '0': 1}

    def bodynums(s):
        # 去掉参考文献与英文摘要, 只查正文
        s = re.sub(r'^\*\*参考文献\*\*.*$', '', s, flags=re.M | re.S)
        s = re.sub(r'^\d+\.\s.*$', '', s, flags=re.M)
        return collections.Counter(re.findall(r'\d+(?:\.\d+)?', s))
    on, nn = bodynums(orig), bodynums(new)
    missing = collections.Counter({k: v for k, v in (on - nn).items()
                                   if v > ACCEPTED_MISSING.get(k, 0)})
    if missing:
        tot = sum(missing.values())
        fail.append(f'F. 数字缺失(白名单外) {tot} 个, 涉及 {len(missing)} 种')
        for k, v in sorted(missing.items(), key=lambda x: -x[1])[:25]:
            fail.append(f'   缺 "{k}" ×{v}')

    if fail:
        print('== 拒绝整合, 需人工处理 ==')
        for f in fail:
            print(' ', f)
        # 仍写出草稿供主编查看
        io.open(OUT, 'w', encoding='utf-8').write(new)
        print(f'\n(草稿仍已写入 {OUT} 供人工比对, 但请先处理上述问题)')
        return 2

    io.open(OUT, 'w', encoding='utf-8').write(new)
    print('== 全部校验通过 ==')
    print(f'原稿 {len(orig)} 字符 -> 润色稿 {len(new)} 字符 '
          f'({(len(new)-len(orig))/max(len(orig),1)*100:+.1f}%)')
    print('已写入:', OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
