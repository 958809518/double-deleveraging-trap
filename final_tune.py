# -*- coding: utf-8 -*-
"""锁定最终配置: 在 MDD<=4% 约束下最大化年化; 并输出完整回测细节"""
import json
import numpy as np
import pandas as pd
import multi_strategy as ms
from multi_v5 import run_v5, ALL_RISKY, CFG5

panel, sig_df = ms.build_panel()

STRICT = dict(dc1=-0.015, dc2=-0.025, dc3=-0.035, x1=-0.005, x2=-0.010, x3=-0.018,
              s1=0.70, s2=0.40, s3=0.15)
MID = dict(dc1=-0.020, dc2=-0.030, dc3=-0.045, x1=-0.006, x2=-0.012, x3=-0.022,
           s1=0.75, s2=0.50, s3=0.25)

print('== 精细扫描: 严格档 tv 3%~8% ==')
rows = []
for tv in [0.030, 0.035, 0.040, 0.045, 0.050, 0.055, 0.060, 0.070, 0.080]:
    c = dict(CFG5); c.update(STRICT); c['target_vol'] = tv; c['dc_on'] = True
    nav, log, turn = run_v5(panel, sig_df, c, ALL_RISKY)
    m = ms.metrics(nav, f'严格|tv={tv:.1%}')
    m['换手/年'] = round(turn * 252, 1)
    n1 = nav[nav.index <= '2019-12-31']; n2 = nav[nav.index >= '2020-01-01']
    m['前半%'] = ms.metrics(n1, 'a')['年化%']; m['后半%'] = ms.metrics(n2, 'b')['年化%']
    rows.append(m); print(json.dumps(m, ensure_ascii=False))

r = pd.DataFrame(rows)
print('\n== MDD<=4.0% 中最高年化 ==')
ok = r[r['最大回撤%'] >= -4.0].sort_values('年化%', ascending=False)
print(ok.to_string(index=False))
print('\n== 全部 ==')
print(r.to_string(index=False))
