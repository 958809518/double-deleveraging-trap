# -*- coding: utf-8 -*-
"""结构变体测试: A) 2014年起 B) 固定红利底仓+择时进攻 C) 进攻仓动量增强"""
import pandas as pd
import numpy as np
import json
import backtest_v2 as bt

df = bt.build_signals()

def run_variant(df, cfg, start, fixed_ballast=0.0, mom_boost=False):
    """fixed_ballast: 固定红利底仓比例; mom_boost: 动量增强"""
    d = df[df.index >= start].dropna(subset=['r_tr_hong', 'r_tr_cun', 'r_tr_bond']).copy()
    wh, wc, wb, wy = fixed_ballast, 0.0, 0.85 - fixed_ballast, 0.15
    nav = [1.0]; dates = []
    cur_m = None; prev_mdd = 0.0; month_mdd = 0.0; month_start = 1.0
    turn = 0.0
    for i in range(1, len(d)):
        date, row = d.index[i], d.iloc[i]
        if cur_m != (date.year, date.month):
            if cur_m is not None:
                prev_mdd = month_mdd
            cur_m = (date.year, date.month)
            month_mdd = 0.0; month_start = nav[-1]
            sig = d.iloc[i - 1]
            pct, trend, mom, volr, m1m2 = sig['price_pct'], sig['trend_ok'], sig['mom20'], sig['vol_ratio'], sig['m1m2']
            cap = cfg['eq_cap']
            if pd.isna(pct):
                h, c = fixed_ballast, 0.0
            else:
                # —— 进攻仓(c)择时; 红利底仓=固定ballast+择时部分 ——
                if pct < 0.30 and trend:
                    h_extra, c = (cap - fixed_ballast) * 0.6, (cap - fixed_ballast) * 0.4
                elif pct < 0.30:
                    h_extra, c = (cap - fixed_ballast) * 0.5, 0.0
                elif pct > 0.80:
                    h_extra, c = 0.0, 0.0
                elif not trend:
                    h_extra, c = -0.05, 0.0     # 趋势不在: 连底仓都略降
                else:
                    h_extra, c = (cap - fixed_ballast) * 0.665, (cap - fixed_ballast) * 0.335
                if mom_boost and c > 0 and mom > 0.02:
                    c = min(c * 1.3, cap - fixed_ballast)
                if mom < -0.10:
                    h_extra, c = h_extra * 0.6, c * 0.4
                liq_bad = (m1m2 < cfg['m1m2_floor']) or (volr < cfg['vol_floor'])
                if liq_bad: c = 0.0
                h = fixed_ballast + max(h_extra, 0)
            # 熔断
            if prev_mdd <= cfg['dd3']:
                h, c = min(h, 0.05), 0.0
            elif prev_mdd <= cfg['dd2']:
                h, c = h * 0.5, 0.0
            elif prev_mdd <= cfg['dd1']:
                h, c = h * 0.8, c * 0.5
            if h + c > cap:
                h = cap - c
            b = max(1 - h - c - 0.05, 0); y = 0.05
            turn += abs(h - wh) + abs(c - wc) + abs(b - wb) + abs(y - wy)
            wh, wc, wb, wy = h, c, b, y
        pr = wh * row['r_tr_hong'] + wc * row['r_tr_cun'] + wb * row['r_tr_bond'] + wy * row['r_cash']
        nn = nav[-1] * (1 + pr)
        month_mdd = min(month_mdd, nn / max(month_start, max(nav[-30:]) if nav else nn) - 1)
        nav.append(nn); dates.append(date)
    return pd.Series(nav[1:], index=dates), turn / 2 / len(d)

cfg = dict(bt.BASE_CFG)

print('== A: 起始期对比 (base规则) ==')
for start in ['2013-04-01', '2014-01-01']:
    for cap in [0.35, 0.45]:
        c2 = dict(cfg); c2['eq_cap'] = cap
        nav, t = run_variant(df, c2, start)
        print(json.dumps(bt.metrics(nav, f'{start[:7]} cap={cap}'), ensure_ascii=False))

print('\n== B: 固定红利底仓 + 择时进攻 ==')
for ball in [0.20, 0.30]:
    for cap in [0.40, 0.50]:
        c2 = dict(cfg); c2['eq_cap'] = cap
        nav, t = run_variant(df, c2, '2014-01-01', fixed_ballast=ball)
        print(json.dumps(bt.metrics(nav, f'ballast={ball} cap={cap}'), ensure_ascii=False))

print('\n== C: 动量增强进攻仓 ==')
for cap in [0.40, 0.50, 0.60]:
    c2 = dict(cfg); c2['eq_cap'] = cap
    nav, t = run_variant(df, c2, '2014-01-01', fixed_ballast=0.25, mom_boost=True)
    print(json.dumps(bt.metrics(nav, f'mom_boost cap={cap}'), ensure_ascii=False))
