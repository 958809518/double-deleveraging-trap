# -*- coding: utf-8 -*-
"""
稳健性检验 6.6: 关闭全部战术信号(趋势MA / 价格分位 / M1-M2剪刀差),
只保留"纯风险overlay" = 逆波动率加权 + 波动率目标 (+ 回撤控制)

目的: 回答审稿人必问的问题——前沿分岔是否只是本文特定战术信号的副产品?
若关闭信号后分岔依然存在, 则证明该现象源自两层风控的交互本身。
"""
import os
import json
import numpy as np
import pandas as pd
import multi_strategy as ms
from multi_v5 import CFG5, ALL_RISKY, COST

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'paper_data')
os.makedirs(OUT, exist_ok=True)

START = '2013-08-01'
STRICT = dict(dc1=-0.015, dc2=-0.025, dc3=-0.035, x1=-0.005, x2=-0.010, x3=-0.018,
              s1=0.70, s2=0.40, s3=0.15)


def run_pure(panel, cfg, risky, start=START, borrow=0.0):
    """纯风险overlay: 无趋势过滤、无价格分位、无宏观信号"""
    ms.RISKY = risky
    p = panel[panel.index >= pd.Timestamp(start)].copy()
    p = p.dropna(subset=['红利', '沪深300', '国债'])
    for c in risky:
        s = p[c]
        fv = s.first_valid_index()
        if fv is not None:
            p.loc[p.index < fv, c] = float(s.loc[fv])
    r = p.pct_change()
    vol = r[risky].rolling(60, min_periods=20).std() * np.sqrt(252)

    nav = [1.0]
    dates = []
    w_prev = pd.Series(0.0, index=risky)
    wb_prev = 1.0
    turn = 0.0
    cur_m = None
    peak = 1.0
    state = 0

    for i in range(1, len(p)):
        date = p.index[i]
        if cur_m != (date.year, date.month):
            cur_m = (date.year, date.month)
            j = i - 1
            v = vol.iloc[j]
            sel = [c for c in risky if not np.isnan(v[c]) and v[c] > 0]
            w = pd.Series(0.0, index=risky)
            if sel:
                iv = 1.0 / v[sel]
                w[sel] = iv / iv.sum()
                sub = r[risky].iloc[max(0, j - 250):j].dropna()
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
            turn += float(np.abs(w - w_prev).sum() + abs(wb - wb_prev))
            cost = float(np.abs(w - w_prev).sum() + abs(wb - wb_prev)) * COST
            w_prev, wb_prev = w, wb
        else:
            cost = 0.0

        dd = nav[-1] / peak - 1
        if cfg['dc_on']:
            d1, d2, d3 = cfg['dc1'], cfg['dc2'], cfg['dc3']
            if dd <= d3:
                state = 3
            elif dd <= d2:
                state = max(state, 2)
            elif dd <= d1:
                state = max(state, 1)
            if state == 3 and dd > cfg['x3']:
                state = 2
            elif state == 2 and dd > cfg['x2']:
                state = 1
            elif state == 1 and dd > cfg['x1']:
                state = 0
            sc = [1.0, cfg['s1'], cfg['s2'], cfg['s3']][state]
        else:
            sc = 1.0
        w_eff = w_prev * sc
        extra = float(w_prev.sum() * (1 - sc))
        wb_eff = wb_prev + extra

        pr = float((w_eff * r.iloc[i][risky]).sum() + wb_eff * r.iloc[i]['国债']
                   + cfg['cash'] * ((1 + 0.02) ** (1 / 252) - 1))
        lev = max(float(w_eff.sum()) + wb_eff + cfg['cash'] - 1.0, 0.0)
        pr -= lev * borrow / 252.0
        nn = nav[-1] * (1 + pr)
        nn *= (1 - cost)
        nav.append(nn)
        dates.append(date)
        peak = max(peak, nn)

    return pd.Series(nav[1:], index=dates), turn / 2 / len(p)


if __name__ == '__main__':
    panel, sig_df = ms.build_panel()
    TVS = [0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.065, 0.07, 0.08, 0.09,
           0.10, 0.12, 0.15]
    rows = []
    print('=== 纯风险overlay(无战术信号) 前沿扫描 ===')
    for cap in [1.0, 2.0]:
        for dc in [False, True]:
            for tv in TVS:
                c = dict(CFG5)
                c.update(STRICT)
                c['target_vol'] = tv
                c['dc_on'] = dc
                c['eq_cap'] = cap
                nav, turn = run_pure(panel, c, ALL_RISKY, borrow=0.03 if cap > 1 else 0.0)
                m = ms.metrics(nav, f'pure|{tv}|{dc}|{cap}')
                rec = {'tv': tv, 'DC': dc, 'cap': cap, 'ann': m['年化%'], 'vol': m['波动%'],
                       'mdd': m['最大回撤%'], 'sharpe': m['夏普'], 'calmar': m['卡玛'],
                       'turn': round(turn * 252, 2)}
                rows.append(rec)
                print(json.dumps(rec, ensure_ascii=False))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, 'C6_nosignal.csv'), index=False, encoding='utf-8-sig')

    print('\n=== 内点最优与末端衰减(无信号) ===')
    pk = []
    for cap in [1.0, 2.0]:
        for dc in [False, True]:
            sub = df[(df['cap'] == cap) & (df['DC'] == dc)].sort_values('tv')
            i = sub['ann'].idxmax()
            tail = sub[sub['tv'] >= 0.10]['ann'].mean()
            peak_tv = float(sub.loc[i, 'tv'])
            peak_ann = float(sub.loc[i, 'ann'])
            end_ann = float(sub.iloc[-1]['ann'])
            pk.append({'cap': cap, 'DC': dc, '峰值σ*': peak_tv, '峰值年化%': peak_ann,
                       '末端年化%': end_ann,
                       '末端衰减pp': round(peak_ann - end_ann, 3),
                       '高tv区均值%': round(float(tail), 3)})
            print(json.dumps(pk[-1], ensure_ascii=False))
    pd.DataFrame(pk).to_csv(os.path.join(OUT, 'C6_peak.csv'), index=False,
                            encoding='utf-8-sig')
    print('\n完成 ->', OUT)
