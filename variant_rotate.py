# -*- coding: utf-8 -*-
"""变体D: 进攻仓三资产动量轮动 (红利/沪深300/中证1000) — 阿朱"板块轮动逐水草而居" """
import pandas as pd
import numpy as np
import json, os
import backtest_v2 as bt

df = bt.build_signals()

# 中证1000 指数(动量比较用)
z = pd.read_csv('data/zz1000.csv')
z.columns = [c.lower() for c in z.columns]
z[z.columns[0]] = pd.to_datetime(z.columns[0] and z[z.columns[0]])
z = z.set_index(z.columns[0]).sort_index()
df['tr_1000'] = z['close'].astype(float).reindex(df.index, method='ffill')
df.loc[df.index < z.index.min(), 'tr_1000'] = float(z['close'].iloc[0])
df['r_tr_1000'] = df['tr_1000'].pct_change()

def run_rotate(df, cfg, start='2014-01-01', ballast=0.25):
    d = df[df.index >= start].dropna(subset=['r_tr_hong', 'r_tr_cun', 'r_tr_bond']).copy()
    for col in ['tr_hong', 'tr_cun', 'tr_1000']:
        d[f'mom63_{col}'] = d[col].pct_change(63)
    wh, wc0, wc1, wb, wy = ballast, 0.0, 0.0, 0.75, 0.0
    nav = [1.0]; dates = []; cur_m = None; prev_mdd = 0.0; month_mdd = 0.0; month_start = 1.0
    turn = 0.0
    for i in range(1, len(d)):
        date, row = d.index[i], d.iloc[i]
        if cur_m != (date.year, date.month):
            if cur_m is not None:
                prev_mdd = month_mdd
            cur_m = (date.year, date.month)
            month_mdd = 0.0; month_start = nav[-1]
            sig = d.iloc[i - 1]
            pct, trend, volr, m1m2 = sig['price_pct'], sig['trend_ok'], sig['vol_ratio'], sig['m1m2']
            cap = cfg['eq_cap']
            if pd.isna(pct):
                h, c0, c1 = ballast, 0.0, 0.0
            else:
                # 进攻额度
                off = max(cap - ballast, 0)
                if pct > 0.80:
                    h, c0, c1 = ballast, 0.0, 0.0        # 炒高收缩
                elif not trend:
                    h, c0, c1 = ballast * 0.7, 0.0, 0.0   # 趋势不在收缩
                else:
                    # 轮动: 动量最高者得进攻仓(洼地时放大)
                    moms = {'c0': sig['mom63_tr_cun'], 'h': sig['mom63_tr_hong'], 'c1': sig['mom63_tr_1000']}
                    best = max(moms, key=lambda k: -1e9 if pd.isna(moms[k]) else moms[k])
                    if moms[best] < 0:
                        h, c0, c1 = ballast, 0.0, 0.0     # 全弱者不加仓
                    elif pct < 0.30:
                        mult = 1.0                          # 洼地满额进攻
                    else:
                        mult = 0.65                         # 中枢六成
                    alloc_off = off * mult
                    h, c0, c1 = ballast, 0.0, 0.0
                    if best == 'c0': c0 = alloc_off
                    elif best == 'h': h = ballast + alloc_off
                    else: c1 = alloc_off
                liq_bad = (m1m2 < cfg['m1m2_floor']) or (volr < cfg['vol_floor'])
                if liq_bad: c0, c1 = 0.0, 0.0
            # 熔断
            if prev_mdd <= cfg['dd3']:
                h, c0, c1 = min(h, 0.05), 0.0, 0.0
            elif prev_mdd <= cfg['dd2']:
                h, c0, c1 = h * 0.5, 0.0, 0.0
            elif prev_mdd <= cfg['dd1']:
                h, c0, c1 = h * 0.8, c0 * 0.5, c1 * 0.5
            tot = h + c0 + c1
            if tot > cap:
                sc = cap / tot; h *= sc; c0 *= sc; c1 *= sc
            wb = max(1 - h - c0 - c1 - 0.05, 0); wy = 0.05
            turn += abs(h - wh) + abs(c0 - wc0) + abs(c1 - wc1) + abs(wb - wb)
            wh, wc0, wc1 = h, c0, c1
        pr = (wh * row['r_tr_hong'] + wc0 * row['r_tr_cun'] + wc1 * row['r_tr_1000']
              + wb * row['r_tr_bond'] + wy * row['r_cash'])
        nn = nav[-1] * (1 + pr)
        month_mdd = min(month_mdd, nn / max(month_start, max(nav[-30:])) - 1)
        nav.append(nn); dates.append(date)
    return pd.Series(nav[1:], index=dates), turn / 2 / len(d)

cfg = dict(bt.BASE_CFG)
print('== 变体D: 动量轮动进攻 ==')
for ball in [0.20, 0.25, 0.30]:
    for cap in [0.40, 0.45, 0.50]:
        c2 = dict(cfg); c2['eq_cap'] = cap
        nav, t = run_rotate(df, c2, '2014-01-01', ballast=ball)
        print(json.dumps(bt.metrics(nav, f'ballast={ball} cap={cap}'), ensure_ascii=False))
