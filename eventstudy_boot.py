# -*- coding: utf-8 -*-
"""
事件研究的统计检验(回应审稿意见 F7-2/F7-3):
  1) 状态控制: 用"未施加风控的参照组合"前瞻收益替代策略净值前瞻收益,
     检验"深跌后市场是否真的更好", 剔除"低仓位机械抬高前瞻收益"的成分。
  2) block bootstrap: 250日窗口严重重叠, 均值差必须给置信区间。
     做法: 对策略日收益做 block bootstrap -> 重建净值 -> 按滞回规则重算档位
     -> 重算分组前瞻收益差, 保留路径依赖。
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
rng = np.random.default_rng(20241022)

cfg = dict(CFG5); cfg.update(STRICT)
cfg['target_vol'] = 0.055; cfg['dc_on'] = True; cfg['eq_cap'] = 1.0

panel, sig_df = ms.build_panel()
dg = run_diag(panel, sig_df, cfg, ALL_RISKY)
nav = dg['nav']
r = nav.pct_change().dropna()
state = dg['state'].reindex(r.index).fillna(0).astype(int).values

# 参照组合(未施加任何风控): 逆波动加权的风险资产组合, 满仓
p = panel[panel.index >= START]
rr = p[ALL_RISKY].pct_change()
iv = 1.0 / (rr.rolling(60, min_periods=20).std() * np.sqrt(252))
wref = iv.div(iv.sum(axis=1), axis=0)
r_ref = (wref * rr).sum(axis=1).reindex(r.index).fillna(0.0)
nav_ref = (1 + r_ref).cumprod()

print('=== 表8(重算): 策略净值前瞻收益 与 参照组合前瞻收益(状态控制) ===')
rows = []
for h in [20, 40, 60, 120, 250]:
    fwd_s = (nav.shift(-h) / nav - 1).reindex(r.index)
    fwd_b = (nav_ref.shift(-h) / nav_ref - 1).reindex(r.index)
    row = {'持有期(日)': h}
    for g, lab in [(0, '无减仓'), (1, '轻×0.70'), (2, '中×0.40'), (3, '重×0.15')]:
        m = state == g
        row[f'{lab}_策略%'] = round(float(fwd_s[m].mean()) * 100, 3)
        row[f'{lab}_参照%'] = round(float(fwd_b[m].mean()) * 100, 3)
        row[f'{lab}_N'] = int(m.sum())
    row['重-无(策略)pp'] = round(row['重×0.15_策略%'] - row['无减仓_策略%'], 3)
    row['重-无(参照)pp'] = round(row['重×0.15_参照%'] - row['无减仓_参照%'], 3)
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False))
pd.DataFrame(rows).to_csv(os.path.join(OUT, 'J2_event_control.csv'),
                          index=False, encoding='utf-8-sig')


# ---------- block bootstrap ----------
def states_from_returns(rv, c):
    """给定日收益序列 -> 重建净值 -> 滞回档位序列"""
    nv = np.cumprod(1.0 + rv)
    peak = np.maximum.accumulate(nv)
    dd = nv / peak - 1.0
    st = 0
    out = np.empty(len(rv), dtype=np.int8)
    d1, d2, d3 = c['dc1'], c['dc2'], c['dc3']
    x1, x2, x3 = c['x1'], c['x2'], c['x3']
    for i in range(len(rv)):
        d = dd[i]
        if d <= d3:
            st = 3
        elif d <= d2:
            st = max(st, 2)
        elif d <= d1:
            st = max(st, 1)
        if st == 3 and d > x3:
            st = 2
        elif st == 2 and d > x2:
            st = 1
        elif st == 1 and d > x1:
            st = 0
        out[i] = st
    return nv, out


def block_sample(rv, L, gen):
    n = len(rv)
    nb = int(np.ceil(n / L))
    starts = gen.integers(0, n - L + 1, size=nb)
    return np.concatenate([rv[s:s + L] for s in starts])[:n]


print('\n=== block bootstrap (block=21日, 1000次): 重度减仓 vs 无减仓 前瞻收益差 ===')
rv = r.values.astype(float)
L = 21
B = 1000
res = {}
for h in [60, 120, 250]:
    diffs = np.empty(B)
    for b in range(B):
        rb = block_sample(rv, L, rng)
        nvb, sb = states_from_returns(rb, cfg)
        nxt = np.empty(len(rb)); nxt[:] = np.nan
        nxt[:len(rb) - h] = nvb[h:] / nvb[:len(rb) - h] - 1.0
        m0 = sb == 0; m3 = sb == 3
        if m3.sum() < 20 or m0.sum() < 20:
            diffs[b] = np.nan
        else:
            diffs[b] = np.nanmean(nxt[m3]) - np.nanmean(nxt[m0])
    d = diffs[~np.isnan(diffs)]
    lo, hi = np.percentile(d, [2.5, 97.5])
    pval = 2 * min((d > 0).mean(), (d < 0).mean())
    res[h] = dict(持有期=h, 均值差pp=round(float(d.mean()) * 100, 3),
                  CI_lo=round(float(lo) * 100, 3), CI_hi=round(float(hi) * 100, 3),
                  p值=round(float(pval), 3), 有效次数=int(len(d)))
    print(json.dumps(res[h], ensure_ascii=False))

with open(os.path.join(OUT, 'J_bootstrap.json'), 'w', encoding='utf-8') as f:
    json.dump({'control': rows, 'bootstrap': res}, f, ensure_ascii=False, indent=1)
print('\n完成 ->', OUT)
