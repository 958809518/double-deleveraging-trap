# -*- coding: utf-8 -*-
"""日频诊断引擎: 输出每日 目标敞口/有效敞口/风控状态/水下深度, 供机制检验使用

注意: 本引擎必须与 multi_v5.run_v5 保持同一交易成本口径(单边万三, 调仓日扣减),
否则机制检验(表6/7/8)与主结果(表3)会出现年化收益不一致。
"""
import numpy as np
import pandas as pd
import multi_strategy as ms
from multi_v5 import COST

START = '2013-08-01'


def run_diag(panel, sig_df, cfg, risky, start=START):
    """返回 DataFrame: state / scale / tgt / eff / dd / nav"""
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
    vol = r[risky].rolling(60, min_periods=20).std() * np.sqrt(252)

    nav = [1.0]; peak = 1.0; state = 0; cur_m = None
    w_prev = pd.Series(0.0, index=risky); wb_prev = 1.0
    tgt = 0.15
    rows = []
    for i in range(1, len(p)):
        date = p.index[i]
        cost = 0.0
        if cur_m != (date.year, date.month):
            cur_m = (date.year, date.month)
            j = i - 1
            t, v = trend.iloc[j], vol.iloc[j]
            sel = [x for x in risky if bool(t[x]) and not np.isnan(v[x]) and v[x] > 0]
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
                # 必须与 multi_v5.run_v5 完全一致: 仅A股三只全额调节, 恒生半额,
                # 黄金/纳指不调节。早期版本对黄金/纳指也施加了半额调节, 导致机制
                # 检验(表6/7/8)与主结果(表3)年化收益不一致。
                for x in risky:
                    if x in ['红利', '沪深300', '中证500']:
                        w[x] *= mu
                    elif x == '恒生':
                        w[x] *= (1 + (mu - 1) * 0.5)
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
            tgt = float(w.sum())
            wb_new = max(1 - tgt - cfg['cash'], 0.0)
            cost = float(np.abs(w - w_prev).sum() + abs(wb_new - wb_prev)) * COST
            w_prev, wb_prev = w, wb_new

        dd = nav[-1] / peak - 1
        if cfg['dc_on']:
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
        else:
            sc = 1.0
        eff = tgt * sc
        rows.append({'date': date, 'state': state, 'scale': sc, 'tgt': tgt,
                     'eff': eff, 'dd': dd})
        w_eff = w_prev * sc
        extra = float(w_prev.sum() * (1 - sc))
        pr = float((w_eff * r.iloc[i][risky]).sum() + (wb_prev + extra) * r.iloc[i]['国债']
                   + cfg['cash'] * ((1 + 0.02) ** (1 / 252) - 1))
        nn = nav[-1] * (1 + pr)
        nn *= (1 - cost)
        nav.append(nn); peak = max(peak, nn)

    dg = pd.DataFrame(rows).set_index('date')
    dg['nav'] = nav[1:len(rows) + 1]
    return dg
