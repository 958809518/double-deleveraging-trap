# -*- coding: utf-8 -*-
"""最终配置 v5(严格|tv=5.5%) 的完整回测输出 + 稳健性 + 前沿, 导出 JSON 供报告使用"""
import json
import os
import numpy as np
import pandas as pd
import multi_strategy as ms
from multi_v5 import run_v5, ALL_RISKY, CFG5

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'report_data')
os.makedirs(OUT, exist_ok=True)

STRICT = dict(dc1=-0.015, dc2=-0.025, dc3=-0.035, x1=-0.005, x2=-0.010, x3=-0.018,
              s1=0.70, s2=0.40, s3=0.15)
FINAL = dict(CFG5); FINAL.update(STRICT); FINAL['target_vol'] = 0.055; FINAL['dc_on'] = True

panel, sig_df = ms.build_panel()
START = '2013-08-01'

res = {}

# ---------- 1. 主策略 ----------
nav, log, turn = run_v5(panel, sig_df, FINAL, ALL_RISKY, start=START)
m = ms.metrics(nav, '朱格一号v5')
print('== 最终配置 =='); print(json.dumps(m, ensure_ascii=False))
res['main'] = m
res['main']['换手/年'] = round(turn * 252, 2)

# 年度收益
nav_y = nav.resample('YE').last()
ys = pd.concat([pd.Series([nav.iloc[0]], index=[pd.Timestamp('2012-12-31')]), nav_y])
yret = ys.pct_change().dropna()
annual = [{'年份': int(d.year), '收益%': round(v * 100, 2)} for d, v in yret.items()]
res['annual'] = annual
print('\n== 年度收益 =='); print(pd.DataFrame(annual).to_string(index=False))

# 最大回撤区间
cm = nav.cummax()
dd = nav / cm - 1
trough = dd.idxmin()
peak_d = nav.loc[:trough].idxmax()
rec = nav.loc[trough:]
rec_d = rec[rec >= nav.loc[peak_d]]
res['mdd_window'] = {'peak': str(peak_d.date()), 'trough': str(trough.date()),
                     'depth%': round(float(dd.min()) * 100, 2),
                     'recover': str(rec_d.index[0].date()) if len(rec_d) else '未修复',
                     'days': int((pd.Timestamp(rec_d.index[0]) - peak_d).days) if len(rec_d) else None}
print('\n最大回撤:', res['mdd_window'])

# ---------- 2. 基准 ----------
bench = {}
p = panel[panel.index >= START]
for nm, col in [('满仓红利ETF', '红利'), ('满仓沪深300ETF', '沪深300'), ('满仓国债ETF', '国债'),
                ('满仓纳指ETF', '纳指'), ('满仓黄金ETF', '黄金')]:
    s = p[col].dropna()
    if len(s) > 100:
        bench[nm] = ms.metrics(s / s.iloc[0], nm)
# 60/40
r40 = p[['国债', '沪深300']].pct_change().dropna()
n40 = (1 + (r40 * np.array([0.6, 0.4])).sum(axis=1)).cumprod()
bench['60债/40沪深300'] = ms.metrics(n40, '60债/40沪深300')
print('\n== 基准 =='); print(pd.DataFrame(bench).T.to_string())
res['bench'] = bench

# ---------- 3. 前沿 ----------
front = []
for tv in [0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.07, 0.08, 0.09, 0.12]:
    c = dict(CFG5); c.update(STRICT); c['target_vol'] = tv; c['dc_on'] = True
    nv, _, _ = run_v5(panel, sig_df, c, ALL_RISKY, start=START)
    mm = ms.metrics(nv, f'{tv:.1%}')
    front.append({'tv': tv, '年化': mm['年化%'], '回撤': mm['最大回撤%'],
                  '波动': mm['波动%'], '夏普': mm['夏普'], '卡玛': mm['卡玛']})
print('\n== 前沿(tv -> 年化/回撤) =='); print(pd.DataFrame(front).to_string(index=False))
res['frontier'] = front

# 前沿外推: 年化10% 需要多大回撤
f = pd.DataFrame(front)
k = np.polyfit(f['年化'], f['回撤'].abs(), 1)
res['fit'] = {'slope': round(float(k[0]), 3), 'intercept': round(float(k[1]), 3),
              'pred_dd_at_10pct': round(float(np.polyval(k, 10.0)), 2)}
print('前沿线性拟合: |回撤| = %.3f * 年化 + %.3f  => 年化10%% 对应回撤 %.1f%%'
      % (k[0], k[1], np.polyval(k, 10.0)))

# ---------- 4. 稳健性 ----------
rob = []
for drop in [[], ['纳指'], ['黄金'], ['恒生'], ['纳指', '恒生'], ['中证500']]:
    rk = [c for c in ALL_RISKY if c not in drop]
    nv, _, _ = run_v5(panel, sig_df, FINAL, rk, start=START)
    mm = ms.metrics(nv, '剔除' + (','.join(drop) or '无'))
    rob.append({'场景': '剔除' + (','.join(drop) or '无'), '年化%': mm['年化%'],
                '最大回撤%': mm['最大回撤%'], '夏普': mm['夏普'], '卡玛': mm['卡玛']})
res['robust_drop'] = rob
print('\n== 稳健性: 剔除资产 =='); print(pd.DataFrame(rob).to_string(index=False))

# 子样本
sub = []
for s0, s1 in [('2013-08-01', '2019-12-31'), ('2020-01-01', '2026-10-20'),
               ('2013-08-01', '2017-12-31'), ('2018-01-01', '2022-12-31')]:
    nv = nav[(nav.index >= s0) & (nav.index <= s1)]
    mm = ms.metrics(nv, f'{s0[:7]}~{s1[:7]}')
    sub.append({'区间': f'{s0[:7]}~{s1[:7]}', '年化%': mm['年化%'], '最大回撤%': mm['最大回撤%'],
                '夏普': mm['夏普'], '卡玛': mm['卡玛']})
res['robust_sub'] = sub
print('\n== 稳健性: 子样本 =='); print(pd.DataFrame(sub).to_string(index=False))

# 参数敏感性(附近参数)
sens = []
for tv in [0.045, 0.05, 0.055, 0.06, 0.065]:
    for ma in [160, 200, 240]:
        c = dict(FINAL); c['target_vol'] = tv; c['ma'] = ma
        nv, _, _ = run_v5(panel, sig_df, c, ALL_RISKY, start=START)
        mm = ms.metrics(nv, f'tv={tv:.1%},MA{ma}')
        sens.append({'参数': f'tv={tv:.1%}|MA{ma}', '年化%': mm['年化%'],
                     '最大回撤%': mm['最大回撤%'], '夏普': mm['夏普'], '卡玛': mm['卡玛']})
res['sens'] = sens
print('\n== 参数敏感性 =='); print(pd.DataFrame(sens).to_string(index=False))

# ---------- 5. 当前持仓建议 ----------
last = log.iloc[-1] if len(log) else None
cur_assets = {}
for c in ALL_RISKY:
    s = panel[c].dropna()
    ma200 = s.rolling(200).mean()
    cur_assets[c] = {'在年线上': bool(s.iloc[-1] > ma200.iloc[-1]),
                     '现价': round(float(s.iloc[-1]), 3),
                     'MA200': round(float(ma200.iloc[-1]), 3)}
res['current'] = {'asof': str(panel.index[-1].date()), 'assets': cur_assets,
                  '上月权益仓E': float(log.iloc[-1]['E']) if len(log) else None}
print('\n== 当前状态 ==', res['current'])

# ---------- 导出 ----------
nav.to_csv(os.path.join(OUT, 'nav_final.csv'), encoding='utf-8-sig')
# 月度采样用于作图
nm = nav.resample('ME').last()
nm.to_csv(os.path.join(OUT, 'nav_monthly.csv'), encoding='utf-8-sig')
with open(os.path.join(OUT, 'report_data.json'), 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1, default=str)
print('\n导出:', OUT)

# 基准净值(月度)一并导出
bench_nav = {}
for nm2, col in [('满仓红利ETF', '红利'), ('满仓沪深300ETF', '沪深300'), ('满仓国债ETF', '国债')]:
    bench_nav[nm2] = (p[col].dropna() / p[col].dropna().iloc[0])
pd.DataFrame(bench_nav).resample('ME').last().to_csv(
    os.path.join(OUT, 'bench_monthly.csv'), encoding='utf-8-sig')
print('基准净值已导出')
