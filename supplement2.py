# -*- coding: utf-8 -*-
"""
机制检验(修正版):
  G 敞口实现率       —— 双重去杠杆的直接度量: 实际波动 / 目标波动
  H 两层削减的相关性  —— corr(cut_V, cut_D) > 0 证明同向叠加
  I 收益归因分解     —— 拆为"敞口效应"与"择时效应"
  J 事件研究(扩展)   —— 更长持有期 + 按减仓强度分组
"""
import os
import json
import numpy as np
import pandas as pd
import multi_strategy as ms
from multi_v5 import CFG5, ALL_RISKY
from diagnostics import run_diag

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'paper_data')
os.makedirs(OUT, exist_ok=True)

STRICT = dict(dc1=-0.015, dc2=-0.025, dc3=-0.035, x1=-0.005, x2=-0.010, x3=-0.018,
              s1=0.70, s2=0.40, s3=0.15)
START = '2013-08-01'
panel, sig_df = ms.build_panel()

res = {}


def cfg_of(tv, dc, cap=1.0):
    c = dict(CFG5); c.update(STRICT); c['target_vol'] = tv; c['dc_on'] = dc; c['eq_cap'] = cap
    return c


# ---------- G. 敞口实现率 ----------
print('=== G. 敞口实现率 (双重去杠杆的直接度量) ===')
rows = []
for tv in [0.03, 0.04, 0.05, 0.055, 0.06, 0.07, 0.09, 0.12]:
    for dc in [False, True]:
        dg = run_diag(panel, sig_df, cfg_of(tv, dc), ALL_RISKY)
        r = dg['nav'].pct_change().dropna()
        vol = r.std() * np.sqrt(252)
        nav = dg['nav']
        ann = (nav.iloc[-1] / nav.iloc[0]) ** (252 / len(nav)) - 1
        mdd = (nav / nav.cummax() - 1).min()
        rows.append({'目标波动σ*': f'{tv:.1%}', '回撤控制': '开' if dc else '关',
                     '实现波动%': round(vol * 100, 2),
                     '实现率': round(vol / tv, 3),
                     '平均目标敞口': round(float(dg['tgt'].mean()), 3),
                     '平均有效敞口': round(float(dg['eff'].mean()), 3),
                     '敞口削减%': round((1 - dg['eff'].mean() / max(dg['tgt'].mean(), 1e-9)) * 100, 1),
                     '年化%': round(ann * 100, 2), '最大回撤%': round(mdd * 100, 2)})
        print(json.dumps(rows[-1], ensure_ascii=False))
dfG = pd.DataFrame(rows)
dfG.to_csv(os.path.join(OUT, 'G_realization.csv'), index=False, encoding='utf-8-sig')
res['G'] = rows

# ---------- H. 两层削减的相关性 ----------
print('\n=== H. 两层削减的相关性 corr(cut_V, cut_D) ===')
rowsH = []
for tv in [0.03, 0.055, 0.09, 0.12]:
    dg = run_diag(panel, sig_df, cfg_of(tv, True), ALL_RISKY)
    # 波动率目标层的削减程度: 相对理论满仓(1.0)的削减
    cut_v = 1.0 - np.clip(dg['tgt'], 0, 1)
    # 回撤控制层的削减程度
    cut_d = 1.0 - dg['scale']
    cc = pd.concat([cut_v.rename('cv'), cut_d.rename('cd')], axis=1).dropna()
    rho = float(cc['cv'].corr(cc['cd']))
    # 双重削减同时发生的天数占比
    both = float(((cc['cv'] > cc['cv'].median()) & (cc['cd'] > 0)).mean())
    rowsH.append({'σ*': f'{tv:.1%}', 'corr(cut_V,cut_D)': round(rho, 3),
                  '双重减仓占比': round(both, 3),
                  '平均有效敞口': round(float(dg['eff'].mean()), 3)})
    print(json.dumps(rowsH[-1], ensure_ascii=False))
dfH = pd.DataFrame(rowsH)
dfH.to_csv(os.path.join(OUT, 'H_cutcorr.csv'), index=False, encoding='utf-8-sig')
res['H'] = rowsH

# ---------- I. 收益归因分解 ----------
print('\n=== I. 收益归因分解 (敞口效应 vs 择时效应) ===')
rowsI = []
for tv in [0.055, 0.09, 0.12]:
    for dc in [False, True]:
        dg = run_diag(panel, sig_df, cfg_of(tv, dc), ALL_RISKY)
        # 组合的"未加风控"参照: 用风险资产等权逆波动组合的收益
        p = panel[panel.index >= START]
        rr = p[ALL_RISKY].pct_change()
        iv = 1.0 / (rr.rolling(60, min_periods=20).std() * np.sqrt(252))
        wref = (iv.div(iv.sum(axis=1), axis=0)).reindex(dg.index).fillna(0)
        r_ref = float((wref * rr.reindex(dg.index).fillna(0)).sum(axis=1).mean())
        ebar = float(dg['eff'].mean())
        nav = dg['nav']
        ann = (nav.iloc[-1] / nav.iloc[0]) ** (252 / len(nav)) - 1
        # 分解: R = ē·R_ref + Σ(e-ē)·r
        exposure_eff = ebar * r_ref * 252
        timing_eff = ann - exposure_eff
        rowsI.append({'σ*': f'{tv:.1%}', '回撤控制': '开' if dc else '关',
                      '平均敞口ē': round(ebar, 3),
                      '年化%': round(ann * 100, 2),
                      '敞口效应%': round(exposure_eff * 100, 2),
                      '择时效应%': round(timing_eff * 100, 2)})
        print(json.dumps(rowsI[-1], ensure_ascii=False))
dfI = pd.DataFrame(rowsI)
dfI.to_csv(os.path.join(OUT, 'I_attribution.csv'), index=False, encoding='utf-8-sig')
res['I'] = rowsI

# ---------- J. 事件研究(扩展) ----------
print('\n=== J. 扩展事件研究: 按减仓强度分组的后续收益 ===')
dg = run_diag(panel, sig_df, cfg_of(0.055, True), ALL_RISKY)
dg['grp'] = np.where(dg['state'] == 0, '无回撤减仓',
             np.where(dg['state'] == 1, '轻度减仓(×0.70)',
              np.where(dg['state'] == 2, '中度减仓(×0.40)', '重度减仓(×0.15)')))
rowsJ = []
for h in [20, 40, 60, 120, 250]:
    fwd = dg['nav'].shift(-h) / dg['nav'] - 1
    row = {'持有期(日)': h}
    for g in ['无回撤减仓', '轻度减仓(×0.70)', '中度减仓(×0.40)', '重度减仓(×0.15)']:
        v = fwd[dg['grp'] == g].dropna()
        row[f'{g}%'] = round(v.mean() * 100, 3) if len(v) else np.nan
        row[f'{g}N'] = int(len(v))
    rowsJ.append(row)
    print(json.dumps(row, ensure_ascii=False))
dfJ = pd.DataFrame(rowsJ)
dfJ.to_csv(os.path.join(OUT, 'J_eventstudy_ext.csv'), index=False, encoding='utf-8-sig')
res['J'] = rowsJ

with open(os.path.join(OUT, 'supplement2.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1, default=str)
print('\n完成 ->', OUT)
