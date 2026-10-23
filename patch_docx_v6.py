# -*- coding: utf-8 -*-
"""v5 → v6：修复两张无题注表的漏转问题（资产池表 + 回撤档位表）。
1. 全文段落 表N → 表N+2（两张新表均位于原表1之前，故统一 +2）
2. 删除 15 段 Markdown 管道原文
3. 插入"表1 资产池表"（7列×9行，位于"相关性矩阵显示"前）
   与"表2 档位表"（4列×4行，位于"进/出阈值取不同的值"前）
4. 正文补（表1）（表2）指引
样式复刻 md2docx 的三线表规范。
"""
import re
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

SRC = '双重去杠杆陷阱_投稿稿_v5.docx'
DST = '双重去杠杆陷阱_投稿稿_v6.docx'
BODY_CN, BODY_EN, HEAD_CN = '宋体', 'Times New Roman', '黑体'

T1_CAP = '表1　资产池构成与描述性统计（2013-08 至 2026-10，全收益口径）'
T1_HEAD = ['资产', '代码', '起始日', '年化%', '波动%', '夏普', '最大回撤%']
T1_ROWS = [
    ['红利ETF', '510880', '2013-08', '9.99', '20.15', '0.50', '−46.54'],
    ['沪深300ETF', '510300', '2013-08', '6.73', '22.16', '0.30', '−45.44'],
    ['中证500ETF', '510500', '2013-08', '7.62', '28.07', '0.27', '−65.77'],
    ['黄金ETF', '518880', '2013-08', '9.56', '15.22', '0.63', '−30.52'],
    ['纳指ETF', '513100', '2013-08', '21.13', '21.58', '0.98', '−28.49'],
    ['恒生ETF', '159920', '2013-08', '3.29', '21.02', '0.16', '−47.31'],
    ['国债ETF', '511010', '2013-08', '3.10', '2.39', '1.30', '−4.92'],
    ['现金', '—', '—', '2.00', '0.00', '—', '0.00'],
]
T1_ANCHOR = '相关性矩阵显示'

T2_CAP = '表2　回撤控制的滞回档位设定（基准组）'
T2_HEAD = ['档位', '触发（D_t ≤）', '退出（D_t >）', '仓位乘子 φ']
T2_ROWS = [
    ['1', '−1.5%', '−0.5%', '0.70'],
    ['2', '−2.5%', '−1.0%', '0.40'],
    ['3', '−3.5%', '−1.8%', '0.15'],
]
T2_ANCHOR = '进/出阈值取不同的值'


def set_run(r, cn=BODY_CN, en=BODY_EN, size=12, bold=False):
    r.font.size = Pt(size)
    r.bold = bold
    rPr = r._element.get_or_add_rPr()
    rf = rPr.get_or_add_rFonts()
    rf.set(qn('w:ascii'), en)
    rf.set(qn('w:hAnsi'), en)
    rf.set(qn('w:eastAsia'), cn)


def cell_border(cell, **edges):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.find(qn('w:tcBorders'))
    if borders is None:
        borders = OxmlElement('w:tcBorders')
        tcPr.append(borders)
    for edge in ('top', 'left', 'bottom', 'right'):
        if edge not in edges:
            continue
        el = borders.find(qn('w:' + edge))
        if el is None:
            el = OxmlElement('w:' + edge)
            borders.append(el)
        for k, v in edges[edge].items():
            el.set(qn('w:' + k), str(v))


def no_border(cell):
    for e in ('top', 'left', 'bottom', 'right'):
        cell_border(cell, **{e: {'val': 'nil'}})


def fill_cell(c, text, size, bold, align):
    c.text = ''
    cp = c.paragraphs[0]
    cp.alignment = align
    cp.paragraph_format.line_spacing = 1.0
    cp.paragraph_format.space_before = Pt(1.5)
    cp.paragraph_format.space_after = Pt(1.5)
    set_run(cp.add_run(text), size=size, bold=bold)


def ptext(p):
    return ''.join(r.text for r in p.runs)


def insert_table_block(doc, anchor_p, caption, header, rows):
    ncol = len(header)
    fsize = 8.5 if ncol >= 7 else (9.5 if ncol >= 5 else 10.5)
    cap = anchor_p.insert_paragraph_before()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(10)
    cap.paragraph_format.space_after = Pt(3)
    cap.paragraph_format.line_spacing = 1.15
    set_run(cap.add_run(caption), cn=HEAD_CN, size=10.5, bold=True)

    tbl = doc.add_table(rows=1 + len(rows), cols=ncol)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = True
    tblW = OxmlElement('w:tblW')
    tblW.set(qn('w:w'), '5000')
    tblW.set(qn('w:type'), 'pct')
    tbl._tbl.tblPr.append(tblW)
    for j, h in enumerate(header):
        c = tbl.cell(0, j)
        fill_cell(c, h, fsize, True, WD_ALIGN_PARAGRAPH.CENTER)
        no_border(c)
        cell_border(c, top={'val': 'single', 'sz': 8, 'color': '000000'},
                    bottom={'val': 'single', 'sz': 4, 'color': '000000'})
    for ri, row in enumerate(rows):
        for j in range(ncol):
            c = tbl.cell(ri + 1, j)
            al = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            fill_cell(c, row[j], fsize, False, al)
            no_border(c)
            if ri == len(rows) - 1:
                cell_border(c, bottom={'val': 'single', 'sz': 8, 'color': '000000'})
    anchor_p._p.addprevious(tbl._tbl)


def main():
    doc = Document(SRC)

    # 1. 全文表号统一 +2
    pat = re.compile(r'表(\d+)(?!\d)')
    n = 0
    for p in doc.paragraphs:
        full = ptext(p)
        new = pat.sub(lambda m: '表%d' % (int(m.group(1)) + 2), full)
        if new != full and p.runs:
            p.runs[0].text = new
            for r in p.runs[1:]:
                r.text = ''
            n += 1
    print('顺移段落数:', n)

    # 2. 删除管道原文段
    raw = [p for p in doc.paragraphs if ptext(p).strip().startswith('|')]
    print('管道原文段数:', len(raw))
    assert len(raw) == 15, '管道段数应为 15'
    for p in raw:
        p._element.getparent().remove(p._element)

    # 3. 插入两张表
    a1 = next(p for p in doc.paragraphs if ptext(p).startswith(T1_ANCHOR))
    insert_table_block(doc, a1, T1_CAP, T1_HEAD, T1_ROWS)
    a2 = next(p for p in doc.paragraphs if ptext(p).startswith(T2_ANCHOR))
    insert_table_block(doc, a2, T2_CAP, T2_HEAD, T2_ROWS)

    # 4. 正文补指引
    for p in doc.paragraphs:
        full = ptext(p)
        if full == '资产池包括六类风险资产与两类安全资产：':
            p.runs[-1].text = p.runs[-1].text.replace('：', '（表1）：')
        elif '按滞回（hysteresis）规则确定档位：' in full:
            p.runs[0].text = full.replace('确定档位：', '确定档位（表2）：')
            for r in p.runs[1:]:
                r.text = ''

    doc.save(DST)

    # 复核
    chk = Document(DST)
    pipes = [p for p in chk.paragraphs if ptext(p).strip().startswith('|')]
    caps = sorted(set(int(x) for x in re.findall(
        r'表\s?(\d+)　', '\n'.join(ptext(p) for p in chk.paragraphs))))
    print('生成:', DST)
    print('  残留管道段:', len(pipes), '| 表格总数:', len(chk.tables),
          '| 题注序列:', caps)
    print('  表1首行:', ' | '.join(c.text for c in chk.tables[15].rows[0].cells))
    print('  表2内容:', [' | '.join(c.text for c in r.cells)
                         for r in chk.tables[16].rows])


if __name__ == '__main__':
    main()
