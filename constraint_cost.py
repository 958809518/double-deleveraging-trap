# -*- coding: utf-8 -*-
"""
论文第7节"扩展讨论: 约束成本的量化" 的实证支撑
度量: 无杠杆约束(Ē=1, 零售) vs 可杠杆(Ē=2, 机构) 之间的福利差距

三种度量口径:
  C1 效用口径   : U = R − (γ/2)σ², 取不同风险厌恶系数 γ 下的最大效用差
  C2 收益口径   : 在回撤不超过 Dmax 的约束下, 两种约束集能达到的最大年化收益之差
  C3 风险口径   : 要达到给定收益目标 R*, 两种约束集所需承担的最小回撤之差
另输出:
  有效前沿(收益-回撤平面)的四条曲线, 供作图
"""
import os
import json
import numpy as np
import pandas as pd
import multi_strategy as ms
from multi_v5 import CFG5, ALL_RISKY

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'paper_data')
os.makedirs(OUT, exist_ok=True)

STRICT = dict(dc1=-0.015, dc2=-0.025, dc3=-0.035, x1=-0.005, x2=-0.010, x3=-0.018,
              s1=0.70, s2=0.40, s3=0.15)
START = '2013-08-01'
BORROW = 0.03
panel, sig_df = ms.build_panel()
TVS = [0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.065, 0.07, 0.08, 0.09, 0.10, 0.12, 0.15]

res = {}


def run(tv, dc, cap):
    c = dict(CFG5); c.update(STRICT)
    c['target_vol'] = tv; c['dc_on'] = dc; c['eq_cap'] = cap
    from multi_v5 import run_v5
    nav, log, turn = run_v5(panel, sig_df, c, ALL_RISKY, start=START,
                            borrow=BORROW if cap > 1 else 0.0)
    m = ms.metrics(nav, f'{tv}|{dc}|{cap}')
    return {'tv': tv, 'DC': dc, 'cap': cap, 'ann': m['年化%'], 'vol': m['波动%'],
            'mdd': m['最大回撤%'], 'sharpe': m['夏普'], 'calmar': m['卡玛'],
            'turn': round(turn * 252, 2)}


print('=== 扫描四组配置 ===')
rows = []
for cap in [1.0, 2.0]:
    for dc in [False, True]:
        for tv in TVS:
            r = run(tv, dc, cap); rows.append(r)
            print(json.dumps(r, ensure_ascii=False))
df = pd.DataFrame(rows)
df.to_csv(os.path.join(OUT, 'C1_grid.csv'), index=False, encoding='utf-8-sig')


# ---------- C1 效用口径 ----------
print('\n=== C1: 效用口径的约束成本 ===')
u_rows = []
for gamma in [0.5, 1.0, 2.0, 4.0, 8.0]:
    row = {'γ': gamma}
    for cap, lab in [(1.0, '零售Ē=1'), (2.0, '机构Ē=2')]:
        for dc, dcl in [(False, '无DC'), (True, '有DC')]:
            sub = df[(df['cap'] == cap) & (df['DC'] == dc)].copy()
            sub['U'] = sub['ann'] - 0.5 * gamma * (sub['vol'] / 100) ** 2 * 100
            b = sub.loc[sub['U'].idxmax()]
            row[f'{lab}|{dcl}|U*'] = round(float(b['U']), 3)
            row[f'{lab}|{dcl}|年化'] = float(b['ann'])
            row[f'{lab}|{dcl}|回撤'] = float(b['mdd'])
            row[f'{lab}|{dcl}|σ*'] = float(b['tv'])
    # 约束成本(收益当量) = 机构最优效用 − 零售最优效用
    for dcl in ['无DC', '有DC']:
        row[f'约束成本(收益当量%{dcl})'] = round(
            row[f'机构Ē=2|{dcl}|U*'] - row[f'零售Ē=1|{dcl}|U*'], 3)
    u_rows.append(row)
    print(json.dumps(row, ensure_ascii=False))
dfU = pd.DataFrame(u_rows)
dfU.to_csv(os.path.join(OUT, 'C1_utility.csv'), index=False, encoding='utf-8-sig')
res['C1'] = u_rows

# ---------- C2 收益口径 ----------
print('\n=== C2: 给定回撤上限下的最大收益 ===')
c2 = []
for dmax in [3.0, 4.0, 5.0, 6.0, 8.0]:
    row = {'回撤上限%': dmax}
    for cap, lab in [(1.0, '零售Ē=1'), (2.0, '机构Ē=2')]:
        sub = df[(df['cap'] == cap) & (df['mdd'] >= -dmax)]
        if len(sub):
            b = sub.loc[sub['ann'].idxmax()]
            row[f'{lab}最大年化%'] = float(b['ann'])
            row[f'{lab}对应σ*'] = float(b['tv'])
            row[f'{lab}对应DC'] = bool(b['DC'])
        else:
            row[f'{lab}最大年化%'] = np.nan; row[f'{lab}对应σ*'] = np.nan
    if not np.isnan(row.get('机构Ē=2最大年化%', np.nan)):
        row['约束成本pp'] = round(row['机构Ē=2最大年化%'] - row['零售Ē=1最大年化%'], 3)
    c2.append(row)
    print(json.dumps(row, ensure_ascii=False, default=str))
dfC2 = pd.DataFrame(c2)
dfC2.to_csv(os.path.join(OUT, 'C2_return.csv'), index=False, encoding='utf-8-sig')
res['C2'] = c2

# ---------- C3 风险口径 ----------
print('\n=== C3: 给定收益目标下的最小回撤 ===')
c3 = []
for target in [5.0, 6.0, 7.0, 8.0, 9.0, 10.0]:
    row = {'收益目标%': target}
    for cap, lab in [(1.0, '零售Ē=1'), (2.0, '机构Ē=2')]:
        sub = df[(df['cap'] == cap) & (df['ann'] >= target)]
        if len(sub):
            b = sub.loc[sub['mdd'].idxmax()]     # mdd 最大(最接近0) = 回撤最小
            row[f'{lab}最小回撤%'] = float(b['mdd'])
            row[f'{lab}对应σ*'] = float(b['tv'])
            row[f'{lab}对应DC'] = bool(b['DC'])
        else:
            row[f'{lab}最小回撤%'] = None; row[f'{lab}对应σ*'] = None
    c3.append(row)
    print(json.dumps(row, ensure_ascii=False, default=str))
dfC3 = pd.DataFrame(c3)
dfC3.to_csv(os.path.join(OUT, 'C3_risk.csv'), index=False, encoding='utf-8-sig')
res['C3'] = c3

# ---------- 前沿作图数据 ----------
print('\n=== 前沿(收益-回撤平面) ===')
fr = df[['tv', 'DC', 'cap', 'ann', 'mdd']].copy()
fr.to_csv(os.path.join(OUT, 'C4_frontier_plot.csv'), index=False, encoding='utf-8-sig')

# ---------- 关键拐点: 内点最优位置 ----------
print('\n=== 内点最优与末端衰减(按 cap/DC) ===')
pk = []
for cap in [1.0, 2.0]:
    for dc in [False, True]:
        sub = df[(df['cap'] == cap) & (df['DC'] == dc)].sort_values('tv')
        i = sub['ann'].idxmax()
        tail = sub[sub['tv'] >= 0.10]['ann'].mean()
        peak_tv = float(sub.loc[i, 'tv']); peak_ann = float(sub.loc[i, 'ann'])
        end_ann = float(sub.iloc[-1]['ann'])
        pk.append({'cap': cap, 'DC': dc, '峰值σ*': peak_tv, '峰值年化%': peak_ann,
                   '末端年化%': end_ann, '末端衰减pp': round(peak_ann - end_ann, 3),
                   '高tv区均值%': round(float(tail), 3)})
        print(json.dumps(pk[-1], ensure_ascii=False))
dfPk = pd.DataFrame(pk)
dfPk.to_csv(os.path.join(OUT, 'C5_peak.csv'), index=False, encoding='utf-8-sig')
res['peak'] = pk

with open(os.path.join(OUT, 'constraint_cost.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1, default=str)
print('\n完成 ->', OUT)
