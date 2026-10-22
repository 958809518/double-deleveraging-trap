# -*- coding: utf-8 -*-
"""v4 参数寻优: 趋势窗口 / 动量加权 / 债券择时 / A股信号开关"""
import itertools
import json
import numpy as np
import pandas as pd
import multi_strategy as ms
import backtest_v2 as bt

panel, sig_df = ms.build_panel()
print('面板', panel.shape)

base = dict(ms.CFG4)
rows = []

# 1) 趋势窗口 × 目标波动
print('== 1) MA窗口 ==')
for maw in [80, 120, 160, 200, 250]:
    ms.MA_WIN = maw
    for tv in [0.03, 0.04, 0.05]:
        c = dict(base); c['target_vol'] = tv
        nav, log, turn = ms.run_multi(panel, sig_df, c)
        m = ms.metrics(nav, f'MA{maw}|tv={tv:.0%}')
        rows.append(m)
        print(json.dumps(m, ensure_ascii=False))
ms.MA_WIN = 200

r = pd.DataFrame(rows)
print('\n夏普 top5:')
print(r.sort_values('夏普', ascending=False).head(5).to_string(index=False))
