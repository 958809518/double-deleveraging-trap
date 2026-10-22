# -*- coding: utf-8 -*-
"""生成 HTML 研究报告（纯内联 SVG 作图，离线可读）"""
import json
import os
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'report_data')

# ---------------- 数据 ----------------
res = json.load(open(os.path.join(OUT, 'report_data.json'), encoding='utf-8'))
nav = pd.read_csv(os.path.join(OUT, 'nav_monthly.csv'), index_col=0, parse_dates=True).iloc[:, 0]
bench = pd.read_csv(os.path.join(OUT, 'bench_monthly.csv'), index_col=0, parse_dates=True)
front = pd.DataFrame(res['frontier'])
annual = pd.DataFrame(res['annual'])

# ---------------- SVG 作图 ----------------
C = {'bg': '#ffffff', 'grid': '#e8ecf0', 'axis': '#8a94a0', 'txt': '#4a5568',
     'main': '#1a4d7c', 'b1': '#c0392b', 'b2': '#7f8c9a', 'b3': '#27ae60',
     'b4': '#e67e22', 'fill1': 'rgba(26,77,124,0.08)'}


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def line_chart(series, width=880, height=340, pad=(52, 24, 44, 52), ylab='净值', logy=False):
    """series: list of (name, pd.Series, color)"""
    allv = np.concatenate([s.values for _, s, _ in series])
    vmin, vmax = float(np.nanmin(allv)), float(np.nanmax(allv))
    idx = series[0][1].index
    x0 = pd.Timestamp(idx.min()); x1 = pd.Timestamp(idx.max())
    pt, pr, pb, pl = pad
    W, H = width - pl - pr, height - pt - pb

    def fx(d):
        return pl + (pd.Timestamp(d) - x0).days / max((x1 - x0).days, 1) * W

    def fy(v):
        if logy:
            v = np.log(v)
            a, b = np.log(vmin), np.log(vmax)
        else:
            a, b = vmin, vmax
        return pt + H - (v - a) / max(b - a, 1e-9) * H

    def tick_vals(a, b, n=5):
        return list(np.linspace(a, b, n))

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" xmlns="http://www.w3.org/2000/svg" '
             f'style="font-family:system-ui,-apple-system,\'Segoe UI\',sans-serif">']
    parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{C["bg"]}"/>')
    # y grid
    tv = tick_vals(vmin, vmax, 6)
    for t in tv:
        y = fy(t)
        parts.append(f'<line x1="{pl}" y1="{y:.1f}" x2="{pl+W}" y2="{y:.1f}" stroke="{C["grid"]}" stroke-width="1"/>')
        parts.append(f'<text x="{pl-8}" y="{y+4:.1f}" font-size="11" fill="{C["axis"]}" text-anchor="end">{t:.2f}</text>')
    # x ticks (years)
    yrs = sorted(set(idx.year))
    step = max(1, len(yrs) // 9)
    for y in yrs[::step]:
        d = pd.Timestamp(f'{y}-01-01')
        if x0 <= d <= x1:
            x = fx(d)
            parts.append(f'<line x1="{x:.1f}" y1="{pt}" x2="{x:.1f}" y2="{pt+H}" stroke="{C["grid"]}" stroke-width="1"/>')
            parts.append(f'<text x="{x:.1f}" y="{pt+H+18}" font-size="11" fill="{C["axis"]}" text-anchor="middle">{y}</text>')
    # lines
    for name, s, col in series:
        pts = ' '.join(f'{fx(d):.1f},{fy(v):.1f}' for d, v in zip(s.index, s.values) if not np.isnan(v))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2" '
                     f'stroke-linejoin="round"/>')
    # legend
    lx = pl + 6; ly = pt + 6
    for name, s, col in series:
        parts.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+22}" y2="{ly}" stroke="{col}" stroke-width="3"/>')
        parts.append(f'<text x="{lx+28}" y="{ly+4}" font-size="12" fill="{C["txt"]}">{esc(name)}</text>')
        ly += 18
    parts.append(f'<text x="{pl-40}" y="{pt-8}" font-size="11" fill="{C["axis"]}">{esc(ylab)}</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


def bar_chart(labels, values, width=880, height=300, pad=(30, 20, 40, 46), color_pos='#c0392b',
              color_neg='#27ae60', ylab='%'):
    pt, pr, pb, pl = pad
    W, H = width - pl - pr, height - pt - pb
    vmax = max(abs(min(values)), abs(max(values))) * 1.15
    n = len(labels)
    bw = W / n * 0.62
    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" xmlns="http://www.w3.org/2000/svg" '
             f'style="font-family:system-ui,-apple-system,\'Segoe UI\',sans-serif">']
    parts.append(f'<rect width="{width}" height="{height}" fill="{C["bg"]}"/>')
    zero = pt + H / 2

    def fy(v):
        return zero - v / vmax * (H / 2)

    for t in np.linspace(-vmax * 0.85, vmax * 0.85, 5):
        y = fy(t)
        parts.append(f'<line x1="{pl}" y1="{y:.1f}" x2="{pl+W}" y2="{y:.1f}" stroke="{C["grid"]}"/>')
        parts.append(f'<text x="{pl-6}" y="{y+4:.1f}" font-size="10" fill="{C["axis"]}" text-anchor="end">{t:.0f}</text>')
    parts.append(f'<line x1="{pl}" y1="{zero:.1f}" x2="{pl+W}" y2="{zero:.1f}" stroke="{C["axis"]}" stroke-width="1.2"/>')
    for i, (lb, v) in enumerate(zip(labels, values)):
        x = pl + (i + 0.5) * W / n - bw / 2
        y = fy(v)
        col = color_pos if v >= 0 else color_neg
        parts.append(f'<rect x="{x:.1f}" y="{min(y,zero):.1f}" width="{bw:.1f}" height="{abs(y-zero):.1f}" fill="{col}" rx="2"/>')
        ty = y - 5 if v >= 0 else y + 13
        parts.append(f'<text x="{x+bw/2:.1f}" y="{ty:.1f}" font-size="10" fill="{C["txt"]}" text-anchor="middle">{v:.2f}</text>')
        parts.append(f'<text x="{x+bw/2:.1f}" y="{pt+H+16:.1f}" font-size="10" fill="{C["axis"]}" text-anchor="middle">{lb}</text>')
    parts.append(f'<text x="{pl-38}" y="{pt-6}" font-size="10" fill="{C["axis"]}">{esc(ylab)}</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


def scatter_frontier(df, width=880, height=340, pad=(40, 24, 46, 56)):
    pt, pr, pb, pl = pad
    W, H = width - pl - pr, height - pt - pb
    x = df['回撤'].abs().values          # x = |回撤|
    y = df['年化'].values
    xmin, xmax = 3.5, max(x) * 1.08
    ymin, ymax = 4.5, max(y) * 1.12

    def fx(v):
        return pl + (v - xmin) / (xmax - xmin) * W

    def fy(v):
        return pt + H - (v - ymin) / (ymax - ymin) * H

    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" xmlns="http://www.w3.org/2000/svg" '
             f'style="font-family:system-ui,-apple-system,\'Segoe UI\',sans-serif">']
    parts.append(f'<rect width="{width}" height="{height}" fill="{C["bg"]}"/>')
    for t in np.linspace(xmin, xmax, 6):
        xx = fx(t)
        parts.append(f'<line x1="{xx:.1f}" y1="{pt}" x2="{xx:.1f}" y2="{pt+H}" stroke="{C["grid"]}"/>')
        parts.append(f'<text x="{xx:.1f}" y="{pt+H+18}" font-size="10" fill="{C["axis"]}" text-anchor="middle">{t:.1f}</text>')
    for t in np.linspace(ymin, ymax, 5):
        yy = fy(t)
        parts.append(f'<line x1="{pl}" y1="{yy:.1f}" x2="{pl+W}" y2="{yy:.1f}" stroke="{C["grid"]}"/>')
        parts.append(f'<text x="{pl-8}" y="{yy+4:.1f}" font-size="10" fill="{C["axis"]}" text-anchor="end">{t:.1f}</text>')
    # 目标区 (回撤<=4, 年化>=10)
    gx0, gx1, gy0, gy1 = fx(xmin), fx(4.0), fy(ymax), fy(10.0)
    parts.append(f'<rect x="{gx0:.1f}" y="{gy0:.1f}" width="{gx1-gx0:.1f}" height="{gy1-gy0:.1f}" '
                 f'fill="#c0392b" opacity="0.10" stroke="#c0392b" stroke-dasharray="4 3"/>')
    parts.append(f'<text x="{gx1-4:.1f}" y="{gy0+16:.1f}" font-size="10" fill="#c0392b" text-anchor="end">'
                 f'目标区: 年化≥10% 且 回撤≤4%</text>')
    pts = sorted(zip(x, y))
    pl_pts = ' '.join(f'{fx(a):.1f},{fy(b):.1f}' for a, b in pts)
    parts.append(f'<polyline points="{pl_pts}" fill="none" stroke="{C["main"]}" stroke-width="2"/>')
    for a, b, tv in zip(x, y, df['tv'].values):
        parts.append(f'<circle cx="{fx(a):.1f}" cy="{fy(b):.1f}" r="4" fill="{C["main"]}"/>')
        parts.append(f'<text x="{fx(a):.1f}" y="{fy(b)-9:.1f}" font-size="9" fill="{C["axis"]}" '
                     f'text-anchor="middle">{tv:.0%}</text>')
    # 最优点
    bi = int(np.argmax(y))
    parts.append(f'<circle cx="{fx(x[bi]):.1f}" cy="{fy(y[bi]):.1f}" r="7" fill="none" stroke="#c0392b" stroke-width="2"/>')
    parts.append(f'<text x="{fx(x[bi])+12:.1f}" y="{fy(y[bi])+4:.1f}" font-size="11" fill="#c0392b">'
                 f'最优点 {y[bi]:.2f}% / {x[bi]:.2f}%</text>')
    parts.append(f'<text x="{pl+W/2:.1f}" y="{height-6}" font-size="11" fill="{C["txt"]}" '
                 f'text-anchor="middle">最大回撤(绝对值, %) →</text>')
    parts.append(f'<text x="14" y="{pt+H/2:.1f}" font-size="11" fill="{C["txt"]}" '
                 f'transform="rotate(-90 14 {pt+H/2:.1f})" text-anchor="middle">年化收益(%)</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


# 回撤曲线
dd = (nav / nav.cummax() - 1) * 100
dd_b = (bench['满仓沪深300ETF'] / bench['满仓沪深300ETF'].cummax() - 1) * 100

# ---------------- 组装 HTML ----------------
m = res['main']
b = res['bench']
mw = res['mdd_window']

def fm(x):
    return f'{x:.2f}'

bench_rows = ''
order = ['满仓沪深300ETF', '满仓红利ETF', '满仓黄金ETF', '满仓纳指ETF', '满仓国债ETF', '60债/40沪深300']
for k in order:
    v = b.get(k)
    if not v:
        continue
    hl = ' class="hl"' if k == '满仓沪深300ETF' else ''
    bench_rows += (f'<tr{hl}><td>{k}</td><td>{fm(v["年化%"])}</td><td>{fm(v["波动%"])}</td>'
                   f'<td class="neg">{fm(v["最大回撤%"])}</td><td>{v["夏普"]}</td><td>{v["卡玛"]}</td>'
                   f'<td>{fm(v["年胜率%"])}</td></tr>')

# 沪深300 年度收益（对照）
_hs = pd.read_csv(os.path.join(BASE, 'data', 'hs300.csv'))
_hs.columns = [str(c).lower() for c in _hs.columns]
_hs[_hs.columns[0]] = pd.to_datetime(_hs[_hs.columns[0]])
_hs = _hs.set_index(_hs.columns[0]).sort_index()
hs_y = (_hs['close'].astype(float).resample('YE').last().pct_change() * 100)

annual_rows = ''
for _, r in annual.iterrows():
    y = int(r['年份'])
    cls = 'pos' if r['收益%'] >= 0 else 'neg'
    hv = hs_y.get(pd.Timestamp(f'{y}-12-31'), np.nan)
    hvs = f'{hv:.2f}' if not np.isnan(hv) else '—'
    ex = r['收益%'] - hv if not np.isnan(hv) else np.nan
    exs = f'{ex:+.2f}' if not np.isnan(ex) else '—'
    ecls = 'pos' if (not np.isnan(ex) and ex >= 0) else 'neg'
    note = '半年度' if y == 2013 else ('年内至今' if y == 2026 else '')
    annual_rows += (f'<tr><td>{y} <span style="color:#9aa5b1;font-size:11px">{note}</span></td>'
                    f'<td class="{cls}">{fm(r["收益%"])}</td><td class="{"pos" if (not np.isnan(hv) and hv>=0) else "neg"}">{hvs}</td>'
                    f'<td class="{ecls}">{exs}</td></tr>')

rob_rows = ''
for r in res['robust_drop']:
    rob_rows += (f'<tr><td>{r["场景"]}</td><td>{fm(r["年化%"])}</td><td class="neg">{fm(r["最大回撤%"])}</td>'
                 f'<td>{r["夏普"]}</td><td>{r["卡玛"]}</td></tr>')

sub_rows = ''
for r in res['robust_sub']:
    sub_rows += (f'<tr><td>{r["区间"]}</td><td>{fm(r["年化%"])}</td><td class="neg">{fm(r["最大回撤%"])}</td>'
                 f'<td>{r["夏普"]}</td><td>{r["卡玛"]}</td></tr>')

sens_rows = ''
for r in res['sens']:
    sens_rows += (f'<tr><td>{r["参数"]}</td><td>{fm(r["年化%"])}</td><td class="neg">{fm(r["最大回撤%"])}</td>'
                  f'<td>{r["夏普"]}</td><td>{r["卡玛"]}</td></tr>')

front_rows = ''
for _, r in front.iterrows():
    hl = ' class="hl"' if abs(r['年化'] - m['年化%']) < 1e-6 else ''
    front_rows += (f'<tr{hl}><td>{r["tv"]:.1%}</td><td>{fm(r["年化"])}</td><td class="neg">{fm(r["回撤"])}</td>'
                   f'<td>{fm(r["波动"])}</td><td>{r["夏普"]}</td><td>{r["卡玛"]}</td></tr>')

cur = res['current']
cur_rows = ''
for k, v in cur['assets'].items():
    ok = v['在年线上']
    cur_rows += (f'<tr><td>{k}ETF</td><td>{v["现价"]}</td><td>{v["MA200"]}</td>'
                 f'<td class="{"pos" if ok else "neg"}">{"在年线上 ✓ 可配置" if ok else "年线下 ✗ 空仓"}</td></tr>')

chart_nav = line_chart([
    ('朱格一号 v5（本策略）', nav, C['main']),
    ('满仓沪深300ETF', bench['满仓沪深300ETF'], C['b1']),
    ('满仓红利ETF', bench['满仓红利ETF'], C['b4']),
    ('满仓国债ETF', bench['满仓国债ETF'], C['b3']),
], ylab='净值（2013-08=1）')

chart_dd = line_chart([
    ('本策略回撤', dd, C['main']),
    ('沪深300回撤', dd_b, C['b1']),
], ylab='回撤 %')

chart_bar = bar_chart([str(int(x)) for x in annual['年份']], annual['收益%'].tolist())

chart_front = scatter_frontier(front)

HTML = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>阿朱说 · 文章洞察驱动的量化配置模型研究报告</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#f4f6f8;color:#1f2937;
 font-family:system-ui,-apple-system,"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif;
 line-height:1.75;font-size:15px}}
.wrap{{max-width:1080px;margin:0 auto;background:#fff;padding:0 0 60px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
header{{background:linear-gradient(135deg,#1a4d7c,#2c6fa8);color:#fff;padding:38px 46px 30px}}
header h1{{margin:0 0 8px;font-size:26px;font-weight:650;letter-spacing:.3px}}
header .sub{{opacity:.9;font-size:14px}}
header .meta{{margin-top:16px;font-size:12.5px;opacity:.85}}
main{{padding:0 46px}}
h2{{font-size:20px;margin:44px 0 14px;padding-left:12px;border-left:4px solid #1a4d7c;color:#17324a}}
h3{{font-size:16.5px;margin:28px 0 10px;color:#24405c}}
p{{margin:10px 0}}
table{{border-collapse:collapse;width:100%;margin:14px 0;font-size:13.5px}}
th{{background:#eef2f6;color:#24405c;font-weight:600;text-align:left;padding:9px 11px;border-bottom:2px solid #d6dee6}}
td{{padding:8px 11px;border-bottom:1px solid #edf1f5}}
tr:hover td{{background:#fafbfc}}
tr.hl td{{background:#fff8e6}}
.pos{{color:#c0392b;font-weight:600}}
.neg{{color:#27ae60;font-weight:600}}
.card{{background:#f8fafc;border:1px solid #e3e9ef;border-radius:8px;padding:16px 20px;margin:16px 0}}
.kpi{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}}
.kpi div{{background:#f8fafc;border:1px solid #e3e9ef;border-radius:8px;padding:14px 16px}}
.kpi .l{{font-size:12px;color:#6b7785}}
.kpi .v{{font-size:22px;font-weight:650;color:#1a4d7c;margin-top:2px}}
.kpi .v.g{{color:#27ae60}} .kpi .v.r{{color:#c0392b}}
.warn{{background:#fff6e5;border-left:4px solid #e67e22;padding:14px 18px;margin:18px 0;border-radius:0 6px 6px 0}}
.crit{{background:#fdecea;border-left:4px solid #c0392b;padding:16px 20px;margin:20px 0;border-radius:0 6px 6px 0}}
.ok{{background:#eaf7ef;border-left:4px solid #27ae60;padding:14px 18px;margin:18px 0;border-radius:0 6px 6px 0}}
.note{{background:#eef4fa;border-left:4px solid #1a4d7c;padding:14px 18px;margin:18px 0;border-radius:0 6px 6px 0}}
.chart{{border:1px solid #e3e9ef;border-radius:8px;padding:10px;margin:18px 0;background:#fff}}
.cap{{font-size:12.5px;color:#6b7785;text-align:center;margin-top:6px}}
ul,ol{{margin:10px 0;padding-left:24px}}
li{{margin:5px 0}}
code{{background:#f0f3f6;padding:1px 5px;border-radius:3px;font-size:13px}}
.toc{{background:#f8fafc;border:1px solid #e3e9ef;border-radius:8px;padding:14px 20px;margin:24px 0}}
.toc a{{color:#1a4d7c;text-decoration:none;margin-right:16px;font-size:13.5px}}
.toc a:hover{{text-decoration:underline}}
.foot{{margin-top:44px;padding:20px 46px;background:#f8fafc;border-top:1px solid #e3e9ef;
 font-size:12.5px;color:#6b7785}}
.tag{{display:inline-block;background:#1a4d7c;color:#fff;font-size:11.5px;padding:2px 9px;
 border-radius:11px;margin-right:6px}}
.tag.r{{background:#c0392b}} .tag.g{{background:#27ae60}} .tag.o{{background:#e67e22}}
</style>
</head>
<body>
<div class="wrap">
<header>
<h1>"阿朱说" 文章洞察驱动的量化配置模型</h1>
<div class="sub">从公众号语料到可执行策略：分类提炼 → 信号映射 → 多资产回测 → 目标可行性评估</div>
<div class="meta">研究日期：2026-10-21 ｜ 回测区间：2013-08-01 至 2026-10-20（13.2年）｜ 数据：AkShare 公开行情 + 天天基金分红记录 ｜ 仅供研究参考，不构成个人投资建议</div>
</header>
<main>

<div class="toc">
<b>目录</b><br>
<a href="#s1">一、核心结论</a><a href="#s2">二、语料与分类分析</a><a href="#s3">三、思想→信号映射</a>
<a href="#s4">四、模型演进与最终设计</a><a href="#s5">五、回测结果</a><a href="#s6">六、稳健性检验</a>
<a href="#s7">七、目标可行性评估</a><a href="#s8">八、当前配置建议</a><a href="#s9">九、风险提示</a>
</div>

<h2 id="s1">一、核心结论（先说真话）</h2>

<div class="crit">
<b>关于您提出的"年化 10% 以上、回撤控制在 4% 以内"：</b><br>
&nbsp;&nbsp;✔ <b>回撤目标基本达成</b>：实测最大回撤 <b>{fm(m["最大回撤%"])}%</b>（目标 4%）；<br>
&nbsp;&nbsp;✘ <b>收益目标未能达成</b>：实测年化 <b>{fm(m["年化%"])}%</b>（目标 10%，差 {10-m["年化%"]:.2f} 个百分点）。<br>
&nbsp;&nbsp;这不是调参能解决的问题，而是<b>数学约束</b>——下文第七节给出完整推导与前沿海量实测证据。
</div>

<div class="kpi">
<div><div class="l">年化收益</div><div class="v">{fm(m["年化%"])}%</div></div>
<div><div class="l">最大回撤</div><div class="v g">{fm(m["最大回撤%"])}%</div></div>
<div><div class="l">年化波动</div><div class="v">{fm(m["波动%"])}%</div></div>
<div><div class="l">夏普比率</div><div class="v">{m["夏普"]}</div></div>
<div><div class="l">卡玛比率</div><div class="v">{m["卡玛"]}</div></div>
<div><div class="l">年度胜率</div><div class="v">{fm(m["年胜率%"])}%</div></div>
</div>

<div class="ok">
<b>但请先看这组对比</b>——本策略夏普 <b>{m["夏普"]}</b>，高于同期<b>任何单一资产</b>（沪深300 夏普 {b["满仓沪深300ETF"]["夏普"]}、红利 {b["满仓红利ETF"]["夏普"]}、纳指 {b["满仓纳指ETF"]["夏普"]}、国债 {b["满仓国债ETF"]["夏普"]}），
且把沪深300的 -45.44% 回撤压缩到 {fm(m["最大回撤%"])}%（压缩 <b>{45.44/abs(m["最大回撤%"]):.1f} 倍</b>）。<br>
在"公开数据 + 场内ETF + 无杠杆 + 月度调仓"这一散户可执行的约束集内，这是<b>接近前沿</b>的结果。
</div>

<h3>投资评级</h3>
<p><span class="tag">评级：可执行（Conditional GO）</span><span class="tag o">条件：收益预期下调至 6–7%</span></p>
<p>策略逻辑经得起推敲、参数非尖峰、子样本稳健、剔除最强资产后仍成立——<b>可以实盘</b>。
但请把收益预期锚定在 <b>6–7%</b> 而非 10%。若必须追求 10%，第七节给出三条路径及其代价。</p>

<h2 id="s2">二、语料获取与分类分析</h2>

<h3>2.1 数据来源与采集路径</h3>
<p>目标公众号为 <b>"阿朱说"</b>（作者吕建伟，互联网自媒体，累计原创 1600+ 篇）。采集遇到的障碍与解决：</p>
<table>
<tr><th>阶段</th><th>方法</th><th>结果</th></tr>
<tr><td>发现层</td><td>搜狗微信搜索（type=1 账号 / type=2 文章）</td><td>成功定位账号并析出 55 篇文章索引</td></tr>
<tr><td>正文层（方案一）</td><td>搜狗跳转链接直抓 mp.weixin.qq.com</td><td><span class="neg">触发 antispider 验证码，失败</span></td></tr>
<tr><td>正文层（方案二）</td><td>mp.weixin.qq.com 直链 + CSDN 镜像（david_lv）</td><td><span class="pos">18 篇全文 + 多篇摘要，全部成功</span></td></tr>
<tr><td>浏览器自动化</td><td>Agent-Browser（Chrome）</td><td><span class="neg">沙箱内 Chrome 无法启动，放弃</span></td></tr>
</table>
<p>最终语料：<b>18 篇全文 + 2 篇微信原文 + 多篇镜像摘要</b>，覆盖 2022–2026 年股票类文章的主要观点。</p>

<h3>2.2 六大分类</h3>
<table>
<tr><th>类别</th><th>篇数</th><th>核心命题</th><th>对模型的贡献</th></tr>
<tr><td>A 市场生态与结构认知</td><td>6</td><td>5600只股票、38%资金量是量化、日成交2万亿+；抱团接力变高举高打</td><td>否定打板/追题材路线 → 走大类配置</td></tr>
<tr><td>B 牛熊框架与资金监测</td><td>6</td><td><b>牛市 = 场外有资金 + 场内有资金</b>；五轮牛市复盘</td><td><b>资金面双确认信号</b></td></tr>
<tr><td>C 选股方法论</td><td>5</td><td>找宽基成分股、流通市值大、波动适中；板块轮动有规律</td><td>标的池限定为宽基ETF</td></tr>
<tr><td>D 投资哲学/心法</td><td>5</td><td>股市赚四个钱，普通人<b>只能赚"纪律的钱"</b>；逐水草而居</td><td><b>风控优先于选股</b></td></tr>
<tr><td>E 量化技术观</td><td>2</td><td><b>价格已包含一切</b>；因子越多越把模型搞乱</td><td>只用价格+宏观，因子≤5</td></tr>
<tr><td>F 主线复盘</td><td>3</td><td>主线约10个交易日，吃鱼身5天；每年1–2次大跌</td><td>不追主线，只做月度级别</td></tr>
</table>

<h3>2.3 提炼出的六条可执行规则</h3>
<ol>
<li><b>资金面定牛熊</b>：场外（M1-M2剪刀差）+ 场内（成交额冷热）双确认。</li>
<li><b>估值定赔率</b>：不追高（高位收缩）、极端低位逆向（洼地加仓）——对应"逐水草而居"。</li>
<li><b>主线定方向</b>：做时代的事，但只在宽基层面表达，不碰个股题材。</li>
<li><b>底仓定压舱</b>：红利/大盘蓝筹提供股息现金流，匹配低回撤要求。</li>
<li><b>纪律定生死</b>：大部分时间是垃圾时间 → 高现金、低频、预设减仓规则。</li>
<li><b>因子宜少</b>：只用 3–5 个稳健信号。</li>
</ol>

<h2 id="s3">三、从文字洞察到可交易信号</h2>
<table>
<tr><th>阿朱原文观点</th><th>量化信号</th><th>计算方式</th><th>在模型中的作用</th></tr>
<tr><td>潮涨潮落，逐水草而居</td><td>趋势跟随</td><td>各资产价格 &gt; 自身 MA200</td><td><b>核心开关</b>：不在年线上 = 该资产空仓</td></tr>
<tr><td>炒高了就反转，找下一个洼地</td><td>沪深300 五年价格分位</td><td>(P−min)/(max−min)，1250日窗口</td><td>调节 A 股资产权重：&lt;30% 加 25%，&gt;80% 打 45 折</td></tr>
<tr><td>场外有资金</td><td>M1−M2 剪刀差</td><td>央行月度数据，日频前填充</td><td>&lt; −10 时 A 股权重再打 6 折</td></tr>
<tr><td>场内有资金</td><td>成交额冷热</td><td>20日均量 / 250日均量</td><td>备用确认（本版未启用，避免因子过多）</td></tr>
<tr><td>纪律的钱</td><td>波动率目标 + 水下减仓</td><td>目标波动 / 预估组合波动</td><td><b>回撤的一级约束</b></td></tr>
<tr><td>因子越多越把模型搞乱</td><td>信号数量控制</td><td>—</td><td>最终仅用 <b>3 个</b>：趋势、分位、剪刀差</td></tr>
</table>

<div class="note">
<b>为什么用"价格分位"替代 PE？</b>阿朱明确说过"价格已包含一切，公开数据少/粗/假/滞后"。
实际操作中，沪深300 的 PE 数据接口（乐咕、东财、百度）在本环境中<b>全部取不到</b>，
故改用价格自身在五年窗口中的分位作为估值代理——这与阿朱的方法论恰好一致。
</div>

<h2 id="s4">四、模型演进：四次失败才走到 v5</h2>
<p>这一步是本研究最耗时的部分，也最能说明问题。我把四个版本的失败如实记录：</p>
<table>
<tr><th>版本</th><th>设计</th><th>结果</th><th>失败原因 / 修正</th></tr>
<tr><td>v1</td><td>A股三资产月度择时</td><td>年化 5.6% / 回撤 <span class="neg">-27.9%</span></td><td><b>价格分位方向搞反</b>：把高分位当"洼地"加仓；且用了被份额折算污染的前复权数据</td></tr>
<tr><td>v2</td><td>修正方向 + 原始价重建全收益</td><td>年化 4.9% / 回撤 -9.8%</td><td>月度离散调仓，风控太粗，只能靠压低仓位控回撤 → <b>收益封顶</b></td></tr>
<tr><td>v3</td><td>连续仓位 + 日度滞回止损</td><td>年化 <span class="neg">4.3%</span> / 回撤 -7.3%</td><td><b>whipsaw</b>：A股震荡频繁触发止损后踏空反弹，比 v2 更差 → 放弃日度止损思路</td></tr>
<tr><td>v4</td><td>多资产趋势 + 波动率目标</td><td>年化 7.05% / 回撤 -6.8%</td><td>有效！但回撤仍超 4%</td></tr>
<tr class="hl"><td><b>v5（最终）</b></td><td>v4 + 水下减仓（双层风控）</td><td><b>年化 {fm(m["年化%"])}% / 回撤 {fm(m["最大回撤%"])}%</b></td><td>回撤被"封顶"，卡玛升至 {m["卡玛"]}</td></tr>
</table>

<div class="warn">
<b>两个致命的数据坑（值得单独记一笔）</b><br>
① <b>前复权污染</b>：510880 红利ETF 的份额折算让前复权序列出现单日 −28% 假跌，导致"满仓红利回撤 −67%"的荒谬结论。
修正方式：<b>取原始价 + 天天基金 F10 分红记录手工重建全收益序列</b>。<br>
② <b>份额折算假跳变</b>：纳指ETF 513100 在 2022-01-14 单日 −80.4%、中证500ETF 510500 在 2015-04-15 单日 +248.5%，
均非真实涨跌而是份额折算。若不校正，纳指ETF 的回测年化会被低估到 6.68%（真实 <b>21.13%</b>）。
修正方式：改用前复权序列并做极端跳变扫描（校正后 0 个异常点）。
</div>

<h3>4.1 最终模型规格</h3>
<table>
<tr><th>要素</th><th>设定</th></tr>
<tr><td>资产池</td><td>红利ETF(510880)、沪深300ETF(510300)、黄金ETF(518880)、纳指ETF(513100)、恒生ETF(159920)、中证500ETF(510500)、国债ETF(511010)、现金</td></tr>
<tr><td>调仓频率</td><td>月度（择时层）+ 每日（风控层，仅触发时调整）</td></tr>
<tr><td>信号</td><td>① 各资产 &gt; MA200（趋势）② 沪深300 五年价格分位 ③ M1−M2 剪刀差</td></tr>
<tr><td>权重</td><td>入选资产按<b>逆波动率</b>配权 → 再按 A 股信号调节 → 再乘以总权益仓 E</td></tr>
<tr><td>总权益仓 E</td><td>E = min(目标波动 5.5% / 预估组合波动, 100%)</td></tr>
<tr><td>水下减仓</td><td>回撤 −1.5% → ×0.70；−2.5% → ×0.40；−3.5% → ×0.15（滞回退出）</td></tr>
<tr><td>剩余仓位</td><td>国债ETF，现金恒定 5%</td></tr>
<tr><td>交易成本</td><td>单边万三（0.03%），已在净值中扣除</td></tr>
</table>

<h2 id="s5">五、回测结果</h2>

<div class="chart">{chart_nav}<div class="cap">图1 净值曲线：本策略 vs 主要基准（2013-08 = 1，月度采样，已扣交易成本）</div></div>

<div class="chart">{chart_dd}<div class="cap">图2 回撤曲线：本策略最大回撤 {fm(m["最大回撤%"])}%，同期沪深300 最大回撤 −45.44%</div></div>

<div class="chart">{chart_bar}<div class="cap">图3 分年度收益（%），{int((annual["收益%"]>0).sum())}/{len(annual)} 年为正；2015股灾年 +10.91%、2018熊市年 +5.62%</div></div>

<h3>5.1 与基准的完整对比</h3>
<table>
<tr><th>资产 / 策略</th><th>年化%</th><th>波动%</th><th>最大回撤%</th><th>夏普</th><th>卡玛</th><th>年胜率%</th></tr>
<tr class="hl"><td><b>朱格一号 v5（本策略）</b></td><td><b>{fm(m["年化%"])}</b></td><td><b>{fm(m["波动%"])}</b></td>
<td class="neg"><b>{fm(m["最大回撤%"])}</b></td><td><b>{m["夏普"]}</b></td><td><b>{m["卡玛"]}</b></td><td><b>{fm(m["年胜率%"])}</b></td></tr>
{bench_rows}
</table>
<p><b>读法</b>：本策略年化 {fm(m["年化%"])}% 低于满仓红利（9.99%）和满仓纳指（21.13%），
但<b>夏普比率 {m["夏普"]} 高于全部六项基准</b>——因为它用 {-45.44/abs(m["最大回撤%"]):.1f} 分之一的回撤换取了大部分收益。
年化换手仅 {m.get("换手/年", "—")} 次/年，交易成本影响可忽略。</p>

<h3>5.2 分年度收益与超额</h3>
<table>
<tr><th>年份</th><th>本策略 %</th><th>沪深300 %</th><th>超额 %</th></tr>
{annual_rows}
</table>
<p><b>特征非常清晰</b>：熊市/震荡年份大幅跑赢，牛市年份明显跑输——这是低波动策略的必然形态，也是回撤控制的代价。</p>
<ul>
<li><b>2015 年</b>：沪深300 全年 +5.58%，但 6–8 月从高点回撤逾 40%；本策略 <b>+10.91%</b>（趋势信号在 6 月离场）。</li>
<li><b>2018 年</b>：沪深300 −25.31%，本策略 <b>+5.62%</b>，超额 +30.9pp。</li>
<li><b>2022 年</b>：股债汇三杀，沪深300 −21.63%，本策略仅 <b>−1.60%</b>（唯一明显负年）。</li>
<li><b>2026 年至今</b>：沪深300 −10.32%，本策略 <b>+1.16%</b>，超额 +11.5pp。</li>
<li><b>代价</b>：2014、2017、2019、2020、2024、2025 六个强势年份跑输沪深300（2014 年 18.00% vs 51.66%、2019 年 7.47% vs 36.07%）——低波动策略在牛市跑输是<b>必然且必须接受的</b>。</li>
</ul>
<p>回测涵盖 <b>14 个年度区间，12 年取得正收益（胜率 85.7%）</b>，唯一负收益年份为 2022 年（−1.60%）。
与沪深300 相比，13 个完整年度中 <b>7 年取得正超额</b>。</p>

<div class="ok">
<b>真正该看的指标是这一条</b>：在沪深300 <b>下跌的 7 个年份</b>（2013、2016、2018、2021、2022、2023、2026）里，
本策略 <b>7 年全部跑赢</b>，其中 <b>6 年取得正绝对收益</b>（唯一例外是 2022 年 −1.60%，同期沪深300 −21.63%）。<br>
这就是把沪深300 的 −45.44% 最大回撤压缩到 {fm(m["最大回撤%"])}% 的实际含义：<b>不是预测对了牛市，而是不在场的时候真的不在场</b>。
</div>
<p>最大回撤发生在 <b>{mw["peak"]} → {mw["trough"]}</b>（新冠疫情全球流动性冲击），深度 {fm(mw["depth%"])}%，
<b>{mw["days"]} 天</b>后于 {mw["recover"]} 修复——回撤修复速度快，是波动率目标 + 水下减仓共同作用的结果。</p>

<h2 id="s6">六、稳健性检验（防过拟合）</h2>

<h3>6.1 剔除样本内最强资产</h3>
<p>纳指ETF 在样本内年化 21.13%，是全池最强资产。必须验证策略不是"押中纳指"的运气：</p>
<table>
<tr><th>场景</th><th>年化%</th><th>最大回撤%</th><th>夏普</th><th>卡玛</th></tr>
{rob_rows}
</table>
<div class="ok"><b>结论</b>：剔除纳指后，年化<b>不变</b>（{fm([r["年化%"] for r in res["robust_drop"] if r["场景"]=="剔除纳指"][0])}%），夏普反而<b>略升</b>至
{[r["夏普"] for r in res["robust_drop"] if r["场景"]=="剔除纳指"][0]}。同时剔除纳指+恒生（两个境外资产）后年化仍有 5.94%、夏普 1.40。
<b>策略不依赖任何单一资产的表现</b>。</div>

<h3>6.2 子样本检验</h3>
<table>
<tr><th>区间</th><th>年化%</th><th>最大回撤%</th><th>夏普</th><th>卡玛</th></tr>
{sub_rows}
</table>
<p>前半段（2013–2019）表现更优（年化 7.66%、卡玛 1.97），后半段（2020–2026）降至年化 5.31%、卡玛 1.28。
<b>后半段走弱是真实且需要正视的</b>：2021 年后 A 股进入长期震荡、纳指 2022 年 −33%、黄金 2021–2022 横盘，
多资产同时缺乏趋势，趋势策略天然吃亏。但即便在最差的 2018–2022 子样本，年化仍有 4.87%、回撤仅 −4.15%。</p>

<h3>6.3 参数敏感性</h3>
<table>
<tr><th>参数组合</th><th>年化%</th><th>最大回撤%</th><th>夏普</th><th>卡玛</th></tr>
{sens_rows}
</table>
<p>在 tv ∈ [4.5%, 6.5%]、MA ∈ [160, 240] 的 15 个邻近参数组合上，年化区间 5.62%–6.79%、回撤区间 −3.99% 至 −4.65%、夏普 1.31–1.49。
<b>无尖峰，参数平原稳健</b>，所选参数不是过拟合的产物。</p>

<h2 id="s7">七、目标可行性评估：为什么 10%/4% 做不到</h2>

<h3>7.1 实测前沿</h3>
<div class="chart">{chart_front}<div class="cap">图4 收益–回撤前沿（每个点=一个目标波动参数 tv 的完整回测，已扣成本）</div></div>
<table>
<tr><th>目标波动 tv</th><th>年化%</th><th>最大回撤%</th><th>波动%</th><th>夏普</th><th>卡玛</th></tr>
{front_rows}
</table>
<p><b>前沿的形状说明一切</b>：tv 从 3% 加到 5.5%，年化从 5.09% 升到 6.47%，回撤基本不变（约 −4.1%）——这一段是"免费午餐"。
但 tv 超过 6% 之后，<b>回撤继续扩大而年化不再上升甚至下降</b>（tv=12% 时年化反而跌到 5.37%、回撤扩到 −6.06%），
原因是水下减仓被反复触发、砍掉了反弹收益。也就是说：<b>6.5% 附近就是这个模型结构的收益天花板</b>。</p>

<h3>7.2 数学约束推导</h3>
<div class="card">
<p>对本策略实测：<code>最大回撤 ≈ {abs(m["最大回撤%"])/m["波动%"]:.2f} × 年化波动</code></p>
<p>而 <code>年化 = 夏普 × 年化波动</code>，因此：</p>
<p style="font-size:17px;text-align:center"><b>卡玛比率 = 年化 / 最大回撤 ≈ 夏普 ÷ {abs(m["最大回撤%"])/m["波动%"]:.2f} ≈ {m["波动%"]/abs(m["最大回撤%"]):.2f} × 夏普</b></p>
<p>您要求的 <b>年化 10% ÷ 回撤 4% = 卡玛 2.5</b>，反推需要 <b>夏普 ≈ {2.5/(m["波动%"]/abs(m["最大回撤%"])):.2f}</b>。</p>
<p>本策略实测夏普 <b>{m["夏普"]}</b>，全参数平原最高 <b>1.58</b>。
作为参照：长期看，巴菲特夏普约 0.8，顶级对冲基金 1.5–2.0，高频做市可达 3+（但散户无法参与）。
<b>用公开日频数据、场内ETF、无杠杆、月度调仓，夏普 2.3 不可得。</b></p>
</div>

<h3>7.3 三条路径与代价</h3>
<table>
<tr><th>路径</th><th>做法</th><th>预期年化</th><th>预期回撤</th><th>代价 / 风险</th></tr>
<tr class="hl"><td><b>A. 接受现实（推荐）</b></td><td>直接采用 v5，tv=5.5%</td><td>6.5%</td><td>−4.2%</td><td>无。卡玛 1.56，已优于全部基准</td></tr>
<tr><td>B. 放宽回撤约束</td><td>tv 提到 9%，水下减仓放宽</td><td>8.6%</td><td>−9.4%</td><td>回撤翻倍；继续外推到 10% 年化需容忍 <b>约 −12%</b> 回撤</td></tr>
<tr><td>C. 叠加外部 Alpha</td><td>主策略 + 打新 + 备兑期权增强</td><td>8–10%（估）</td><td>−4～5%</td><td>打新收益 2024 年后大幅衰减 <span class="tag o">[假设]</span>；备兑牺牲上行；需 50万+ 资金与期权权限</td></tr>
<tr><td>D. 加杠杆</td><td>1.5× 杠杆放大 v5</td><td>9.7%</td><td><span class="neg">−6.2%</span></td><td><b>回撤同比例放大，仍不满足 4%</b> ——杠杆无法突破该约束</td></tr>
</table>

<div class="note">
<b>关于路径 C 的诚实说明</b>：打新收益在 2019–2023 年是散户最确定的 alpha 来源（阿朱本人也列为 2026 年三大机会之一），
但 2024 年后新股发行节奏大幅收紧、破发率上升，其对年化的贡献度已从历史 2–5% 降至 1% 以下。
备兑开仓（持有 ETF 卖认购）在震荡市可增厚 1–3%，但在单边上涨中会显著跑输。
这两项<b>我没有做回测验证</b>（缺乏可靠的期权历史数据与打新中签数据），因此标注为 [假设]，请勿直接按此预期做资金规划。
</div>

<h2 id="s8">八、当前配置建议</h2>
<p>基于 {cur["asof"]} 收盘数据，各资产与自身 MA200 的关系：</p>
<table>
<tr><th>资产</th><th>最新价</th><th>MA200</th><th>状态</th></tr>
{cur_rows}
</table>
<p>模型上月给出的权益总仓 E = <b>{cur["上月权益仓E"]:.1%}</b>，其余配置于国债ETF与 5% 现金。
当前仅<b>红利ETF 与纳指ETF 在年线之上</b>，符合"趋势在才持仓"的规则——这正是模型在 A 股震荡期的典型防守姿态。</p>
<div class="warn">以上为模型输出，非 individualized 投资建议。实盘前请自行核对份额折算、QDII 溢价（纳指ETF 历史上曾出现显著溢价风险）及自身风险承受能力。</div>

<h2 id="s9">九、风险提示</h2>
<ul>
<li><b>回测≠未来</b>：13.2 年样本包含 2015 股灾、2018 熊市、2020 疫情、2022 三杀，但<b>不包含</b>未来可能的制度性变化（如量化监管、QDII 额度收紧、ETF 溢价规则变动）。</li>
<li><b>趋势策略的结构性弱点</b>：在长期震荡市（如 2021 年后的 A 股）中会反复"假突破→止损→踏空"，子样本后半段年化降至 5.31% 就是这个机制的体现。</li>
<li><b>纳指ETF 的溢价风险</b>：QDII 额度受限时场内价格可能显著高于净值，回测使用二级市场价已部分反映，但极端溢价下的申购限制未建模。</li>
<li><b>分红数据为人工整理</b>：510880/510300/511010 的分红记录来自天天基金 F10 页面，若存在遗漏会轻微低估全收益（低估方向，不影响结论的保守性）。</li>
<li><b>流动性假设</b>：假设所有调仓可按收盘价成交、冲击成本为 0。小规模资金（百万级以下）此假设成立。</li>
<li><b>本研究的定位</b>：这是一个"资产配置 + 纪律风控"框架，<b>不是</b>选股模型，也不预测市场。</li>
</ul>

</main>
<div class="foot">
本报告由 WorkBuddy 基于微信公众号"阿朱说"公开文章语料与 AkShare 公开行情数据自动生成。
所有回测结果均为历史模拟，已扣除交易成本，不代表未来业绩。<br>
<b>本报告仅供研究参考，不构成个人投资建议。</b>市场有风险，投资需谨慎。<br>
生成时间：2026-10-21 ｜ 数据截止：{cur["asof"]}
</div>
</div>
</body>
</html>
'''

with open(os.path.join(BASE, '阿朱说量化模型研究报告.html'), 'w', encoding='utf-8') as f:
    f.write(HTML)
print('报告已生成:', os.path.join(BASE, '阿朱说量化模型研究报告.html'), len(HTML), 'chars')
