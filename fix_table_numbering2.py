# -*- coding: utf-8 -*-
"""第二轮表号修复：档位表补"表2"题注，现有表2-25顺移为表3-26。"""
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
    # 1. 现有 表N(N>=2) → 表N+1
    s = re.sub(r'表(\d+)(?!\d)',
               lambda m: '表%d' % (int(m.group(1)) + 1) if int(m.group(1)) >= 2 else m.group(0),
               s)
    # 2. 插入表2题注
    anchor = '| 档位 | 触发（D_t ≤） | 退出（D_t >） | 仓位乘子 φ |'
    assert anchor in s, 'anchor not found'
    cap = '**表2　回撤控制的滞回档位设定（基准组）**\n\n'
    assert cap not in s
    s = s.replace(anchor, cap + anchor, 1)
    # 3. 正文补表1/表2指引
    s = s.replace('**资产池**包括六类风险资产与两类安全资产：',
                  '**资产池**包括六类风险资产与两类安全资产（表1）：', 1)
    s = s.replace('按滞回（hysteresis）规则确定档位：',
                  '按滞回（hysteresis）规则确定档位（表2）：', 1)
    return s


def fix_md2docx(s):
    old = "'fig4_boundary.svg': '图4　回撤控制成本的分离与条件性（A：表11；B：表20）',"
    new = "'fig4_boundary.svg': '图4　回撤控制成本的分离与条件性（A：表12；B：表21）',"
    assert old in s, 'fig4 caption not found'
    return s.replace(old, new, 1)


def fix_readme(s):
    return s.replace('25 表 / 4 图 / 12 公式', '26 表 / 4 图 / 12 公式', 1)


def fix_verify(s):
    return s.replace("'  (期望 25)'", "'  (期望 26)'", 1)


rw(ROOT + '论文_双重去杠杆陷阱.md', fix_md)
rw(ROOT + 'md2docx.py', fix_md2docx)
rw(ROOT + 'README.md', fix_readme)
rw(ROOT + 'verify_docx.py', fix_verify)

with io.open(ROOT + '论文_双重去杠杆陷阱.md', encoding='utf-8') as f:
    md = f.read()
caps = re.findall(r'^\*\*表(\d+)　', md, re.M)
print('md 题注序列:', caps)
refs = sorted(set(int(x) for x in re.findall(r'表(\d+)(?!\d)', md)))
print('md 全部表号:', refs)
