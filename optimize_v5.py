# -*- coding: utf-8 -*-
"""v5 前沿寻优: 水下减仓档位 × 目标波动, 并在两个子样本上复核(防过拟合)"""
import json
import numpy as np
import pandas as pd
import multi_strategy as ms
from multi_v5 import run_v5, ALL_RISKY, CFG5

panel, sig_df = ms.build_panel()

DC_SETS = {
    '严格': dict(dc1=-0.015, dc2=-0.025, dc3=-0.035, x1=-0.005, x2=-0.010, x3=-0.018,
               s1=0.70, s2=0.40, s3=0.15),
    '中等': dict(dc1=-0.020, dc2=-0.030, dc3=-0.045, x1=-0.006, x2=-0.012, x3=-0.022,
               s1=0.75, s2=0.50, s3=0.25),
    '宽松': dict(dc1=-0.025, dc2=-0.040, dc3=-0.060, x1=-0.008, x2=-0.015, x3=-0.030,
               s1=0.80, s2=0.60, s3=0.30),
    '超宽': dict(dc1=-0.030, dc2=-0.050, dc3=-0.075, x1=-0.010, x2=-0.020, x3=-0.038,
               s1=0.85, s2=0.65, s3=0.35),
}

rows = []
for dcname, dcp in DC_SETS.items():
    for tv in [0.05, 0.07, 0.09, 0.12]:
        c = dict(CFG5); c.update(dcp); c['target_vol'] = tv; c['dc_on'] = True
        nav, log, turn = run_v5(panel, sig_df, c, ALL_RISKY)
        m = ms.metrics(nav, f'{dcname}|tv={tv:.0%}')
        # 子样本复核
        n1 = nav[nav.index <= '2019-12-31']
        n2 = nav[nav.index >= '2020-01-01']
        m['前半夏普'] = ms.metrics(n1, 'a')['夏普']
        m['后半夏普'] = ms.metrics(n2, 'b')['夏普']
        m['前半年化%'] = ms.metrics(n1, 'a')['年化%']
        m['后半年化%'] = ms.metrics(n2, 'b')['年化%']
        rows.append(m)
        print(json.dumps(m, ensure_ascii=False))

r = pd.DataFrame(rows)
print('\n== 全表 ==')
print(r.to_string(index=False))
print('\n== 满足 MDD<=5% 中 年化最高 top6 ==')
print(r[r['最大回撤%'] >= -5.0].sort_values('年化%', ascending=False).head(6).to_string(index=False))
print('\n== 卡玛 top6 ==')
print(r.sort_values('卡玛', ascending=False).head(6).to_string(index=False))
r.to_csv('data/frontier_v5.csv', index=False, encoding='utf-8-sig')
