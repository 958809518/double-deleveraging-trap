# -*- coding: utf-8 -*-
"""把论文 Markdown 转为可离线阅读的 HTML（含表格、公式）"""
import os
import re
import html

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, '论文_双重去杠杆陷阱.md')
DST = os.path.join(BASE, '论文_双重去杠杆陷阱.html')


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
    s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)
    return s


lines = open(SRC, encoding='utf-8').read().split('\n')
out = []
i = 0
in_quote = False
while i < len(lines):
    ln = lines[i].rstrip()

    # 块级公式
    if ln.strip().startswith('$$'):
        buf = []
        while i < len(lines) and not lines[i].strip().endswith('$$'):
            buf.append(lines[i]); i += 1
        if i < len(lines):
            buf.append(lines[i])
        body = '\n'.join(buf).strip().strip('$').strip()
        out.append(f'<div class="eq">\\({body}\\)</div>')
        i += 1
        continue

    # 配图（内嵌 SVG，保证单文件离线可读）
    if ln.startswith('@@FIG'):
        rel = ln[5:].strip()
        fp = os.path.join(BASE, rel)
        try:
            svg = open(fp, encoding='utf-8').read()
            out.append(f'<figure class="fig">{svg}</figure>')
        except Exception:
            out.append(f'<p>[缺少配图：{rel}]</p>')
        i += 1
        continue

    # 表格
    if ln.strip().startswith('|') and i + 1 < len(lines) and re.match(r'^\s*\|[\s:\-|]+\|\s*$', lines[i + 1]):
        header = [c.strip() for c in ln.strip().strip('|').split('|')]
        i += 2
        rows = []
        while i < len(lines) and lines[i].strip().startswith('|'):
            rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
            i += 1
        out.append('<div class="tw"><table><thead><tr>')
        out.append(''.join(f'<th>{inline(h)}</th>' for h in header))
        out.append('</tr></thead><tbody>')
        for r in rows:
            out.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>')
        out.append('</tbody></table></div>')
        continue

    # 标题
    if ln.startswith('### '):
        out.append(f'<h3>{inline(ln[4:])}</h3>')
    elif ln.startswith('## '):
        out.append(f'<h2>{inline(ln[3:])}</h2>')
    elif ln.startswith('# '):
        out.append(f'<h1>{inline(ln[2:])}</h1>')
    elif ln.strip() == '---':
        out.append('<hr>')
    elif ln.startswith('>'):
        out.append(f'<blockquote>{inline(ln.lstrip("> ").strip())}</blockquote>')
    elif re.match(r'^\s*[-*]\s+', ln):
        out.append(f'<li>{inline(re.sub(r"^\s*[-*]\s+", "", ln))}</li>')
    elif re.match(r'^\s*\d+\.\s+', ln):
        out.append(f'<li class="num">{inline(re.sub(r"^\s*\d+\.\s+", "", ln))}</li>')
    elif ln.strip() == '':
        out.append('')
    else:
        out.append(f'<p>{inline(ln)}</p>')
    i += 1

body = '\n'.join(out)

HTML = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>双重去杠杆陷阱：波动率目标与回撤控制的交互效应</title>
<script>
window.MathJax = {{tex: {{inlineMath: [['\\\\(','\\\\)']], displayMath: [['\\\\[','\\\\]']]}}}};
</script>
<script id="MathJax-script" async src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-mml-chtml.js"></script>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#f5f6f7;color:#1f2328;
 font-family:"Songti SC","SimSun",Georgia,system-ui,sans-serif;line-height:1.85;font-size:16px}}
.wrap{{max-width:940px;margin:0 auto;background:#fff;padding:56px 62px 80px;
 box-shadow:0 1px 6px rgba(0,0,0,.07)}}
h1{{font-size:25px;text-align:center;line-height:1.5;margin:0 0 6px;font-weight:700;
 font-family:"Heiti SC","Microsoft YaHei",sans-serif}}
h2{{font-size:20px;margin:40px 0 16px;padding-bottom:8px;border-bottom:2px solid #1a4d7c;
 color:#17324a;font-family:"Heiti SC","Microsoft YaHei",sans-serif}}
h3{{font-size:17px;margin:26px 0 10px;color:#24405c;
 font-family:"Heiti SC","Microsoft YaHei",sans-serif}}
p{{margin:11px 0;text-align:justify;text-indent:0}}
blockquote{{background:#f7f9fb;border-left:3px solid #1a4d7c;margin:16px 0;
 padding:10px 16px;color:#4a5568;font-size:14.5px}}
blockquote p{{margin:2px 0}}
.tw{{overflow-x:auto;margin:18px 0}}
table{{border-collapse:collapse;width:100%;font-size:14px;
 font-family:"Microsoft YaHei",system-ui,sans-serif}}
th{{background:#eef2f6;color:#24405c;font-weight:600;text-align:left;
 padding:9px 11px;border:1px solid #d8e0e8;white-space:nowrap}}
td{{padding:8px 11px;border:1px solid #e6ebf0}}
tbody tr:nth-child(even) td{{background:#fafbfc}}
tbody tr:hover td{{background:#f2f7fb}}
li{{margin:6px 0 6px 22px}}
li.num{{list-style:decimal}}
ul,ol{{padding-left:0;margin:10px 0}}
.eq{{background:#f8fafc;border:1px solid #e3e9ef;border-radius:6px;
 padding:14px 18px;margin:16px 0;text-align:center;overflow-x:auto;font-size:16px}}
figure.fig{{margin:24px 0;padding:12px 10px;background:#fff;border:1px solid #e6ebf0;
 border-radius:6px;text-align:center;overflow-x:auto}}
figure.fig svg{{max-width:100%;height:auto;display:block;margin:0 auto}}
hr{{border:0;border-top:1px solid #e3e9ef;margin:32px 0}}
code{{background:#f0f3f6;padding:1px 5px;border-radius:3px;font-size:14px}}
strong{{color:#0f2b45}}
.toc{{background:#f8fafc;border:1px solid #e3e9ef;border-radius:8px;padding:16px 22px;margin:26px 0;
 font-family:"Microsoft YaHei",sans-serif;font-size:14px}}
.toc a{{color:#1a4d7c;text-decoration:none;display:inline-block;margin:3px 14px 3px 0}}
.toc a:hover{{text-decoration:underline}}
.foot{{margin-top:40px;padding-top:16px;border-top:1px solid #e3e9ef;
 font-size:13px;color:#6b7785;text-align:center}}
@media print{{body{{background:#fff}}.wrap{{box-shadow:none;padding:0}}}}
</style>
</head>
<body>
<div class="wrap">
<div class="toc">
<b>目　录</b><br>
<a href="#s0">摘要</a><a href="#s1">一、引言</a><a href="#s2">二、文献综述与理论模型</a>
<a href="#s3">三、研究设计</a><a href="#s4">四、实证结果</a><a href="#s5">五、机制检验与数值模拟</a>
<a href="#s6">六、稳健性检验</a><a href="#s65">七、扩展讨论：约束成本的量化</a>
<a href="#s7">八、结论与启示</a><a href="#s8">参考文献</a>
</div>
{body}
<div class="foot">中文 A 类期刊体例 ｜ 数据区间 2013-08-01 至 2026-10-20 ｜ 本报告仅供研究参考，不构成个人投资建议</div>
</div>
<script>
document.querySelectorAll('h2').forEach(function(h){{
  var t=h.textContent.trim();
  var map={{'摘要':'s0','一、引言':'s1','二、文献综述与理论模型':'s2','三、研究设计':'s3',
    '四、实证结果':'s4','五、机制检验与数值模拟':'s5','六、稳健性检验':'s6',
    '七、扩展讨论：约束成本的量化':'s65','八、结论与启示':'s7','参考文献':'s8'}};
  if(map[t]) h.id=map[t];
}});
</script>
</body>
</html>
'''

open(DST, 'w', encoding='utf-8').write(HTML)
print('生成:', DST, len(HTML), 'chars')
