# -*- coding: utf-8 -*-
"""定位 run_v5 与 run_diag 净值首次偏离的位置"""
import numpy as np
import pandas as pd
import multi_strategy as ms
from multi_v5 import run_v5, CFG5, ALL_RISKY
from diagnostics import run_diag

panel, sig_df = ms.build_panel()
STRICT = dict(dc1=-0.015, dc2=-0.025, dc3=-0.035, x1=-0.005, x2=-0.010, x3=-0.018,
              s1=0.70, s2=0.40, s3=0.15)

c = dict(CFG5)
c.update(STRICT)
c['target_vol'] = 0.055
c['dc_on'] = True
nav1, log1, _ = run_v5(panel, sig_df, c, ALL_RISKY)
dg = run_diag(panel, sig_df, c, ALL_RISKY)
nav2 = dg['nav']

d = nav1.values - nav2.values
idx = np.where(np.abs(d) > 1e-12)[0]
print('首次偏离 idx:', idx[:5])
for k in idx[:5]:
    print(f'  {nav1.index[k].date()}  v5={nav1.values[k]:.8f} diag={nav2.values[k]:.8f} '
          f'diff={d[k]:.8f}')
print('\n前5天:')
for k in range(5):
    print(f'  {nav1.index[k].date()} v5={nav1.values[k]:.8f} diag={nav2.values[k]:.8f}')
print('\ndiag 前几行 state/scale/tgt/eff:')
print(dg.head(5))
print('\nv5 log 前几行:', log1[:3] if len(log1) else log1.head(3).to_dict('records'))
