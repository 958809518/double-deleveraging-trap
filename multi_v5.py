# -*- coding: utf-8 -*-
"""
"朱格一号" v5 —— 多资产趋势择时 + 波动率目标 + 水下减仓(双层风控)
并支持: 资产子集(稳健性检验) / 子样本 / 全参数导出
"""
import os
import numpy as np
import pandas as pd
import json
import backtest_v2 as bt
import multi_strategy as ms

COST = 0.0003
ALL_RISKY = ['红利', '沪深300', '黄金', '纳指', '恒生', '中证500']


def run_v5(panel, sig_df, cfg, risky, start='2013-08-01', borrow=0.0):
    ms.RISKY = risky
    p = panel[panel.index >= pd.Timestamp(start)].copy()
    p = p.dropna(subset=['红利', '沪深300', '国债'])
    for c in risky:
        s = p[c]
        fv = s.first_valid_index()
        if fv is not None:
            p.loc[p.index < fv, c] = float(s.loc[fv])
    r = p.pct_change()
    ma = p[risky].rolling(cfg['ma'], min_periods=min(100, cfg['ma'])).mean()
    trend = p[risky] > ma
    vol = r[risky].rolling(60, min_periods=20).std() * np.sqrt(252)

    nav = [1.0]; dates = []
    w_prev = pd.Series(0.0, index=risky); wb_prev = 1.0
    turn = 0.0; cur_m = None; peak = 1.0; state = 0
    log = []

    for i in range(1, len(p)):
        date = p.index[i]
        if cur_m != (date.year, date.month):
            cur_m = (date.year, date.month)
            j = i - 1
            t, v = trend.iloc[j], vol.iloc[j]
            sel = [c for c in risky if bool(t[c]) and not np.isnan(v[c]) and v[c] > 0]
            w = pd.Series(0.0, index=risky)
            if sel:
                iv = 1.0 / v[sel]
                w[sel] = iv / iv.sum()
                try:
                    sr = sig_df.loc[p.index[j]]
                    pct, m1m2 = sr['price_pct'], sr['m1m2']
                    mult_a = 1.0
                    if not np.isnan(pct):
                        mult_a = cfg['a_mult_low'] if pct < 0.30 else (
                            cfg['a_mult_high'] if pct > 0.80 else 1.0)
                    if not np.isnan(m1m2) and m1m2 < cfg['m1m2_floor']:
                        mult_a *= 0.6
                except Exception:
                    mult_a = 1.0
                for c in risky:
                    if c in ['红利', '沪深300', '中证500']:
                        w[c] *= mult_a
                    elif c == '恒生':
                        w[c] *= (1 + (mult_a - 1) * 0.5)
                if w.sum() > 0:
                    w = w / w.sum()
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
            log.append({'date': str(date.date()), 'E': round(float(w.sum()), 3)})

        # ---- 日度水下减仓(滞回) ----
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
        if cur_m is not None and len(log) and log[-1]['date'] == str(date.date()):
            nn *= (1 - cost)
        nav.append(nn); dates.append(date)
        peak = max(peak, nn)

    return pd.Series(nav[1:], index=dates), pd.DataFrame(log), turn / 2 / len(p)


CFG5 = {'ma': 200, 'target_vol': 0.05, 'eq_cap': 1.0, 'cash': 0.05, 'm1m2_floor': -10,
        'a_mult_low': 1.25, 'a_mult_high': 0.45,
        'dc_on': False, 'dc1': -0.015, 'dc2': -0.025, 'dc3': -0.035,
        'x1': -0.005, 'x2': -0.010, 'x3': -0.018, 's1': 0.7, 's2': 0.4, 's3': 0.15}

if __name__ == '__main__':
    panel, sig_df = ms.build_panel()
    print('== A) 双层风控扫描 (tv × 水下减仓开关) ==')
    rows = []
    for tv in [0.03, 0.04, 0.05, 0.06, 0.07]:
        for dc in [False, True]:
            c = dict(CFG5); c['target_vol'] = tv; c['dc_on'] = dc
            nav, log, turn = run_v5(panel, sig_df, c, ALL_RISKY)
            m = ms.metrics(nav, f'tv={tv:.0%}|DC={"on" if dc else "off"}')
            rows.append(m); print(json.dumps(m, ensure_ascii=False))
    print('\n前沿对比:')
    print(pd.DataFrame(rows).to_string(index=False))

    print('\n== B) 稳健性: 剔除样本内最强资产(纳指) ==')
    for drop in [[], ['纳指'], ['黄金'], ['纳指', '恒生']]:
        rk = [c for c in ALL_RISKY if c not in drop]
        for tv in [0.04, 0.05]:
            c = dict(CFG5); c['target_vol'] = tv; c['dc_on'] = True
            nav, log, turn = run_v5(panel, sig_df, c, rk)
            print(json.dumps(ms.metrics(nav, f'剔除{drop or "无"}|tv={tv:.0%}'), ensure_ascii=False))

    print('\n== C) 子样本 ==')
    for s0, s1 in [('2013-08-01', '2019-12-31'), ('2020-01-01', '2026-10-20')]:
        c = dict(CFG5); c['target_vol'] = 0.05; c['dc_on'] = True
        nav, log, turn = run_v5(panel, sig_df, c, ALL_RISKY, start=s0)
        nav = nav[nav.index <= pd.Timestamp(s1)]
        print(json.dumps(ms.metrics(nav, f'{s0[:7]}~{s1[:7]}'), ensure_ascii=False))
