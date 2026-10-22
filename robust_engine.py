# -*- coding: utf-8 -*-
"""
回应审稿意见 M2/M3/M4 的稳健性补跑(独立于主引擎, 不改动 multi_v5):
  M2 波动率估计窗口: 资产层 60/120 日, 组合协方差 250/125 日
  M3 调仓频率:       月度 / 双周 / 季度
  M4 回撤控制形式:   三档滞回(基准) / 连续线性 ramp
每个变体重跑前沿扫描(σ* 六档 × DC 开关), 报告内点最优是否成立。
"""
import os
import json
import numpy as np
import pandas as pd
import multi_strategy as ms
from multi_v5 import CFG5, ALL_RISKY, COST

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'paper_data')
START = '2013-08-01'
STRICT = dict(dc1=-0.015, dc2=-0.025, dc3=-0.035, x1=-0.005, x2=-0.010, x3=-0.018,
              s1=0.70, s2=0.40, s3=0.15)
TVS = [0.03, 0.045, 0.055, 0.07, 0.09, 0.12]


def key_of(date, freq):
    if freq == 'M':
        return (date.year, date.month)
    if freq == '2W':
        return (date.year, date.isocalendar()[1] // 2)
    return (date.year, (date.month - 1) // 3)


def run(panel, sig_df, cfg, risky, freq='M', vwin=60, cwin=250,
        dc_form='hyst', start=START):
    ms.RISKY = risky
    p = panel[panel.index >= pd.Timestamp(start)].copy()
    p = p.dropna(subset=['红利', '沪深300', '国债'])
    for c in risky:
        s = p[c]; fv = s.first_valid_index()
        if fv is not None:
            p.loc[p.index < fv, c] = float(s.loc[fv])
    r = p.pct_change()
    ma = p[risky].rolling(cfg['ma'], min_periods=min(100, cfg['ma'])).mean()
    trend = p[risky] > ma
    vol = r[risky].rolling(vwin, min_periods=min(20, vwin)).std() * np.sqrt(252)

    nav = [1.0]; dates = []
    w_prev = pd.Series(0.0, index=risky); wb_prev = 1.0
    cur_k = None; peak = 1.0; state = 0
    for i in range(1, len(p)):
        date = p.index[i]
        cost = 0.0
        k = key_of(date, freq)
        if cur_k != k:
            cur_k = k
            j = i - 1
            t, v = trend.iloc[j], vol.iloc[j]
            sel = [c for c in risky if bool(t[c]) and not np.isnan(v[c]) and v[c] > 0]
            w = pd.Series(0.0, index=risky)
            if sel:
                iv = 1.0 / v[sel]; w[sel] = iv / iv.sum()
                try:
                    sr = sig_df.loc[p.index[j]]
                    pct, m1m2 = sr['price_pct'], sr['m1m2']
                    mu = 1.0
                    if not np.isnan(pct):
                        mu = cfg['a_mult_low'] if pct < 0.30 else (
                            cfg['a_mult_high'] if pct > 0.80 else 1.0)
                    if not np.isnan(m1m2) and m1m2 < cfg['m1m2_floor']:
                        mu *= 0.6
                except Exception:
                    mu = 1.0
                for c in risky:
                    if c in ['红利', '沪深300', '中证500']:
                        w[c] *= mu
                    elif c == '恒生':
                        w[c] *= (1 + (mu - 1) * 0.5)
                if w.sum() > 0:
                    w = w / w.sum()
                sub = r[risky].iloc[max(0, j - cwin):j].dropna()
                if len(sub) > 60:
                    cov = sub.cov() * 252
                    pv = float(np.sqrt(max(w.values @ cov.values @ w.values, 1e-8)))
                else:
                    pv = 0.15
                E = float(np.clip(cfg['target_vol'] / pv, 0, cfg['eq_cap']))
            else:
                E = 0.0
            w = w * E
            wb = max(1 - w.sum() - cfg['cash'], 0.0)
            cost = float(np.abs(w - w_prev).sum() + abs(wb - wb_prev)) * COST
            w_prev, wb_prev = w, wb

        dd = nav[-1] / peak - 1
        if cfg['dc_on']:
            if dc_form == 'hyst':
                if dd <= cfg['dc3']:
                    state = 3
                elif dd <= cfg['dc2']:
                    state = max(state, 2)
                elif dd <= cfg['dc1']:
                    state = max(state, 1)
                if state == 3 and dd > cfg['x3']:
                    state = 2
                elif state == 2 and dd > cfg['x2']:
                    state = 1
                elif state == 1 and dd > cfg['x1']:
                    state = 0
                sc = [1.0, cfg['s1'], cfg['s2'], cfg['s3']][state]
            else:  # 连续线性 ramp: D=-3.5% 时 φ=0.15
                kk = (1 - cfg['s3']) / abs(cfg['dc3'])
                sc = float(np.clip(1 + kk * dd, cfg['s3'], 1.0))
        else:
            sc = 1.0
        w_eff = w_prev * sc
        wb_eff = wb_prev + float(w_prev.sum() * (1 - sc))
        pr = float((w_eff * r.iloc[i][risky]).sum() + wb_eff * r.iloc[i]['国债']
                   + cfg['cash'] * ((1 + 0.02) ** (1 / 252) - 1))
        nn = nav[-1] * (1 + pr) * (1 - cost)
        nav.append(nn); dates.append(date)
        peak = max(peak, nn)
    return pd.Series(nav[1:], index=dates)


def shape(pairs):
    s = sorted(pairs, key=lambda x: x[0])
    vals = [v for _, v in s]
    k = int(np.argmax(vals))
    return dict(峰值σ=f'{s[k][0]:.1%}', 峰值年化=round(s[k][1], 2),
                末端年化=round(s[-1][1], 2), 末端衰减pp=round(s[k][1] - s[-1][1], 3),
                内点最优=bool(k < len(s) - 1))


panel, sig_df = ms.build_panel()
rows = []
VAR = [('基准（月度 / 60日 / 250日 / 三档滞回）', 'M', 60, 250, 'hyst'),
       ('M2 资产波动窗120日', 'M', 120, 250, 'hyst'),
       ('M2 组合协方差窗125日', 'M', 60, 125, 'hyst'),
       ('M3 双周调仓', '2W', 60, 250, 'hyst'),
       ('M3 季度调仓', 'Q', 60, 250, 'hyst'),
       ('M4 连续线性 ramp', 'M', 60, 250, 'ramp')]

print('=== 稳健性变体：前沿形状是否保持内点最优 ===')
for lab, freq, vw, cw, form in VAR:
    for dc in [False, True]:
        c = dict(CFG5); c.update(STRICT); c['dc_on'] = dc
        ser = []
        for tv in TVS:
            c['target_vol'] = tv
            nv = run(panel, sig_df, c, ALL_RISKY, freq=freq, vwin=vw, cwin=cw,
                     dc_form=form)
            ann = (nv.iloc[-1] / nv.iloc[0]) ** (252 / len(nv)) - 1
            ser.append((tv, ann * 100))
        sh = shape(ser)
        r = dict(变体=lab, 回撤控制='开' if dc else '关', **sh,
                 序列=[round(v, 2) for _, v in ser])
        rows.append(r)
        print(json.dumps(r, ensure_ascii=False))

pd.DataFrame(rows).to_csv(os.path.join(OUT, 'R_robust_variants.csv'),
                          index=False, encoding='utf-8-sig')
print('\n完成 ->', OUT)
