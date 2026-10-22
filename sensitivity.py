# -*- coding: utf-8 -*-
"""敏感性分析: 权益仓位上限 vs 收益/回撤前沿"""
import pandas as pd
import numpy as np
import json, os
import backtest_v2 as bt

df = bt.build_signals()

print('== 敏感性: 权益总仓上限 ==')
rows = []
for cap in [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
    cfg = dict(bt.BASE_CFG); cfg['eq_cap'] = cap
    nav, allocs, grid, turn = bt.run_backtest(df, cfg)
    m = bt.metrics(nav, f'cap={cap}')
    m['年换手'] = round(turn * 252, 2)
    rows.append(m)
    print(json.dumps(m, ensure_ascii=False))

print('\n== 敏感性: 回撤熔断严格度 (cap=0.45) ==')
for dd1, dd2, dd3 in [(-0.015, -0.025, -0.04), (-0.02, -0.03, -0.045), (-0.03, -0.04, -0.06)]:
    cfg = dict(bt.BASE_CFG); cfg['eq_cap'] = 0.45; cfg['dd1'], cfg['dd2'], cfg['dd3'] = dd1, dd2, dd3
    nav, allocs, grid, turn = bt.run_backtest(df, cfg)
    m = bt.metrics(nav, f'dd=({dd1},{dd2},{dd3})')
    rows.append(m)
    print(json.dumps(m, ensure_ascii=False))

print('\n== 敏感性: 分位窗口(以3年窗口替换5年) ==')
df3 = df.copy()
hs = df3['hs300']
df3['price_pct'] = (hs - hs.rolling(750, min_periods=180).min()) / (hs.rolling(750, min_periods=180).max() - hs.rolling(750, min_periods=180).min() + 1e-9)
for cap in [0.35, 0.45, 0.55]:
    cfg = dict(bt.BASE_CFG); cfg['eq_cap'] = cap
    nav, allocs, grid, turn = bt.run_backtest(df3, cfg)
    m = bt.metrics(nav, f'3y窗 cap={cap}')
    print(json.dumps(m, ensure_ascii=False))
