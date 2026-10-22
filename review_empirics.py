# -*- coding: utf-8 -*-
"""
回应《金融研究》审稿意见的补充实证
  A 固定敞口 × 回撤控制   —— 干净分离回撤控制的单独作用(不依赖波动率目标)
  B 回撤控制参数敏感性     —— 证明"单峰"不是特定阈值的产物
  C 交易成本敏感性         —— 检验成本假设是否驱动结论
  D 扩展基准对比           —— 1/N、60/40、CPPI、风险平价式满仓
"""
import os
import json
import numpy as np
import pandas as pd
import multi_strategy as ms
import multi_v5
from multi_v5 import CFG5, ALL_RISKY, run_v5, COST as COST0

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'paper_data')
START = '2013-08-01'
STRICT = dict(dc1=-0.015, dc2=-0.025, dc3=-0.035, x1=-0.005, x2=-0.010, x3=-0.018,
              s1=0.70, s2=0.40, s3=0.15)
panel, sig_df = ms.build_panel()
TVS6 = [0.03, 0.045, 0.055, 0.07, 0.09, 0.12]


def run(tv, dc, cap=1.0, strict=None, borrow=0.0, **kw):
    c = dict(CFG5)
    c.update(strict or STRICT)
    c['target_vol'] = tv
    c['dc_on'] = dc
    c['eq_cap'] = cap
    c.update(kw)
    nav, log, turn = run_v5(panel, sig_df, c, ALL_RISKY, start=START, borrow=borrow)
    m = ms.metrics(nav, '')
    return {'ann': m['年化%'], 'vol': m['波动%'], 'mdd': m['最大回撤%'],
            'sharpe': m['夏普'], 'calmar': m['卡玛'], 'turn': round(turn * 252, 2)}


def shape(series):
    """判断前沿形状: 返回 峰值tv / 峰值年化 / 末端年化 / 末端衰减 / 是否内点"""
    s = sorted(series, key=lambda x: x[0])
    vals = [v for _, v in s]
    k = int(np.argmax(vals))
    peak_tv, peak_v = s[k]
    end_v = s[-1][1]
    return (peak_tv, peak_v, end_v, round(peak_v - end_v, 3), k < len(s) - 1)


res = {}

# ---------- A 固定敞口 × 回撤控制 ----------
print('=== A. 固定敞口(无波动率目标)下的回撤控制成本 ===')
rowsA = []
for Efix in [0.25, 0.44, 0.70, 0.85, 1.00]:
    r_off = run(1.0, False, cap=Efix)
    r_on = run(1.0, True, cap=Efix)
    row = {'固定敞口E': Efix, 'DC关年化%': r_off['ann'], 'DC开年化%': r_on['ann'],
           'DC成本pp': round(r_off['ann'] - r_on['ann'], 3),
           'DC关回撤%': r_off['mdd'], 'DC开回撤%': r_on['mdd'],
           '回撤改善pp': round(r_on['mdd'] - r_off['mdd'], 3),
           'DC关夏普': r_off['sharpe'], 'DC开夏普': r_on['sharpe']}
    rowsA.append(row)
    print(json.dumps(row, ensure_ascii=False))
pd.DataFrame(rowsA).to_csv(os.path.join(OUT, 'R_A_fixedE.csv'), index=False,
                           encoding='utf-8-sig')
res['A'] = rowsA

# ---------- B 回撤控制参数敏感性 ----------
print('\n=== B. 回撤控制参数敏感性(前沿形状是否依赖阈值) ===')
GRIDS = {
    '基准(-1.5/-2.5/-3.5; .70/.40/.15)': STRICT,
    '宽松(-2/-4/-6; .80/.50/.25)': dict(dc1=-0.02, dc2=-0.04, dc3=-0.06,
                                        x1=-0.008, x2=-0.015, x3=-0.03,
                                        s1=0.80, s2=0.50, s3=0.25),
    '严格(-1/-2/-3; .60/.30/.10)': dict(dc1=-0.01, dc2=-0.02, dc3=-0.03,
                                        x1=-0.003, x2=-0.008, x3=-0.015,
                                        s1=0.60, s2=0.30, s3=0.10),
    '极宽(-3/-5/-8; .85/.60/.35)': dict(dc1=-0.03, dc2=-0.05, dc3=-0.08,
                                        x1=-0.012, x2=-0.025, x3=-0.045,
                                        s1=0.85, s2=0.60, s3=0.35),
}
rowsB = []
for name, st in GRIDS.items():
    on, off = [], []
    for tv in TVS6:
        on.append((tv, run(tv, True, strict=st)['ann']))
        off.append((tv, run(tv, False, strict=st)['ann']))
    p_tv, p_v, e_v, decay, interior = shape(on)
    _, _, _, _, interior_off = shape(off)
    row = {'参数组': name, 'DC开_峰值σ*': p_tv, 'DC开_峰值年化%': p_v,
           'DC开_末端年化%': e_v, 'DC开_末端衰减pp': decay,
           'DC开_内点最优': bool(interior), 'DC关_内点最优': bool(interior_off),
           'DC开序列': [round(v, 2) for _, v in on]}
    rowsB.append(row)
    print(json.dumps(row, ensure_ascii=False))
pd.DataFrame(rowsB).to_csv(os.path.join(OUT, 'R_B_dcparam.csv'), index=False,
                           encoding='utf-8-sig')
res['B'] = rowsB

# ---------- C 交易成本敏感性 ----------
print('\n=== C. 交易成本敏感性 ===')
rowsC = []
for mult, lab in [(1.0, '万三(基准)'), (2.0, '万六'), (4.0, '万十二')]:
    multi_v5.COST = COST0 * mult
    on, off = [], []
    for tv in TVS6:
        on.append((tv, run(tv, True)['ann']))
        off.append((tv, run(tv, False)['ann']))
    p_tv, p_v, e_v, decay, interior = shape(on)
    row = {'成本': lab, '峰值σ*': p_tv, '峰值年化%': p_v, '末端年化%': e_v,
           '末端衰减pp': decay, '内点最优': bool(interior),
           'DC开序列': [round(v, 2) for _, v in on]}
    rowsC.append(row)
    print(json.dumps(row, ensure_ascii=False))
multi_v5.COST = COST0
pd.DataFrame(rowsC).to_csv(os.path.join(OUT, 'R_C_cost.csv'), index=False,
                           encoding='utf-8-sig')
res['C'] = rowsC

# ---------- D 扩展基准 ----------
print('\n=== D. 扩展基准 ===')


def bench(weights_fn, name, rebal='M'):
    p = panel[panel.index >= pd.Timestamp(START)].copy()
    p = p.dropna(subset=['红利', '沪深300', '国债'])
    for c in ALL_RISKY:
        s = p[c]
        fv = s.first_valid_index()
        if fv is not None:
            p.loc[p.index < fv, c] = float(s.loc[fv])
    r = p.pct_change()
    nav = [1.0]
    dates = []
    cur = None
    w = None
    for i in range(1, len(p)):
        d = p.index[i]
        m = (d.year, d.month)
        if cur != m or w is None:
            cur = m
            w = weights_fn(p, r, i - 1)
            nav[-1] *= (1 - float(np.abs(w).sum()) * COST0 * 0.0)
        pr = float((w * r.iloc[i][ALL_RISKY]).sum()
                   + max(1 - float(w.sum()), 0.0) * r.iloc[i]['国债'])
        nav.append(nav[-1] * (1 + pr))
        dates.append(d)
    s = pd.Series(nav[1:], index=dates)
    mm = ms.metrics(s, name)
    return {'基准': name, '年化%': mm['年化%'], '波动%': mm['波动%'],
            '最大回撤%': mm['最大回撤%'], '夏普': mm['夏普'], '卡玛': mm['卡玛']}


rowsD = []


def w_equal(p, r, j):
    return pd.Series(1.0 / len(ALL_RISKY), index=ALL_RISKY)


rowsD.append(bench(w_equal, '等权6资产(月度再平衡)'))


def w_invvol(p, r, j):
    v = r[ALL_RISKY].iloc[max(0, j - 250):j].std() * np.sqrt(252)
    iv = 1.0 / v.replace(0, np.nan)
    w = iv / iv.sum()
    return w.fillna(0)


rowsD.append(bench(w_invvol, '逆波动加权满仓(风险平价近似)'))


def w_6040(p, r, j):
    w = pd.Series(0.0, index=ALL_RISKY)
    w['沪深300'] = 0.40
    return w


rowsD.append(bench(w_6040, '60国债/40沪深300(月平衡)'))

# CPPI: 风险资产=沪深300, 乘数3, 底线=0.9*历史高水位
p = panel[panel.index >= pd.Timestamp(START)].copy()
p = p.dropna(subset=['红利', '沪深300', '国债'])
r = p.pct_change()
nav = [1.0]
dates = []
floor = 0.90
peak_v = 1.0
exp = 0.0
for i in range(1, len(p)):
    d = p.index[i]
    if (d.year, d.month) != (p.index[i - 1].year, p.index[i - 1].month):
        cushion = max(nav[-1] - floor * peak_v, 0.0)
        exp = float(np.clip(3.0 * cushion / max(nav[-1], 1e-9), 0, 1))
    pr = exp * r.iloc[i]['沪深300'] + (1 - exp) * r.iloc[i]['国债']
    nn = nav[-1] * (1 + pr)
    nav.append(nn)
    dates.append(d)
    peak_v = max(peak_v, nn)
mm = ms.metrics(pd.Series(nav[1:], index=dates), 'CPPI')
rowsD.append({'基准': 'CPPI(m=3,底线90%)', '年化%': mm['年化%'],
              '波动%': mm['波动%'], '最大回撤%': mm['最大回撤%'],
              '夏普': mm['夏普'], '卡玛': mm['卡玛']})

for row in rowsD:
    print(json.dumps(row, ensure_ascii=False))
pd.DataFrame(rowsD).to_csv(os.path.join(OUT, 'R_D_bench.csv'), index=False,
                           encoding='utf-8-sig')
res['D'] = rowsD

with open(os.path.join(OUT, 'review_empirics.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1, default=str)
print('\n完成 ->', OUT)
