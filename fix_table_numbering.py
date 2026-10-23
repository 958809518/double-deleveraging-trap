# -*- coding: utf-8 -*-
"""修复资产池表无题注漏转问题：
1) md：全文 表N → 表N+1（一次性正则，不会二次顺移），再在资产池表前插入"表1"题注
2) md2docx.py：FIGCAP 中图4题注的 表10/表19 同步顺移
3) README.md：24 表 → 25 表
4) verify_docx.py：表格期望数 24 → 25
"""
import re, io

ROOT = 'E:/金融/阿朱说量化研究/'


def rw(path, fn):
    with io.open(path, encoding='utf-8') as f:
        s = f.read()
    s2 = fn(s)
    if s2 != s:
        with io.open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(s2)
        print('已更新:', path)
    else:
        print('无变化:', path)


def fix_md(s):
    # 1. 一次性顺移所有 表N（含题注与正文引用）
    s = re.sub(r'表(\d+)(?!\d)', lambda m: '表%d' % (int(m.group(1)) + 1), s)
    # 2. 在资产池表前插入表1题注
    anchor = '| 资产 | 代码 | 起始日 | 年化% | 波动% | 夏普 | 最大回撤% |'
    assert anchor in s, 'anchor not found'
    cap = '**表1　资产池构成与描述性统计（2013-08 至 2026-10，全收益口径）**\n\n'
    assert cap not in s
    s = s.replace(anchor, cap + anchor, 1)
    return s


def fix_md2docx(s):
    # 只动图4题注一行
    old = "'fig4_boundary.svg': '图4　回撤控制成本的分离与条件性（A：表10；B：表19）',"
    new = "'fig4_boundary.svg': '图4　回撤控制成本的分离与条件性（A：表11；B：表20）',"
    assert old in s, 'fig4 caption not found'
    return s.replace(old, new, 1)


def fix_readme(s):
    return s.replace('24 表 / 4 图 / 12 公式', '25 表 / 4 图 / 12 公式', 1)


def fix_verify(s):
    return s.replace("'  (期望 24)'", "'  (期望 25)'", 1)


rw(ROOT + '论文_双重去杠杆陷阱.md', fix_md)
rw(ROOT + 'md2docx.py', fix_md2docx)
rw(ROOT + 'README.md', fix_readme)
rw(ROOT + 'verify_docx.py', fix_verify)

# 复核 md
with io.open(ROOT + '论文_双重去杠杆陷阱.md', encoding='utf-8') as f:
    md = f.read()
caps = re.findall(r'^\*\*表(\d+)　', md, re.M)
print('md 题注序列:', caps)
refs = sorted(set(int(x) for x in re.findall(r'表(\d+)(?!\d)', md)))
print('md 全部表号:', refs)
