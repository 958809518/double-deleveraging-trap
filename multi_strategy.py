# -*- coding: utf-8 -*-
"""
"朱格一号" v4 —— 多资产趋势择时 + 波动率目标

阿朱框架的跨资产落地:
  · 逐水草而居  -> 每个资产独立看趋势(MA200), 趋势在才配置; 趋势不在的钱去债/现金
  · 价格包含一切-> 不用估值指标, 只用价格自身均线
  · 纪律的钱    -> 波动率目标(vol targeting): 组合波动超目标就降总仓, 这是回撤的一级约束
  · A股特殊信号 -> 沪深价格分位 + M1-M2 调节 A股资产的权重(A股资产才适用)

资产池: 红利ETF / 沪深300ETF / 黄金ETF / 纳指ETF / 恒生ETF / 中证500ETF / 国债ETF / 现金
"""
import os
import numpy as np
import pandas as pd
import json
import backtest_v2 as bt

DATA = bt.DATA
COST = 0.0003

RISKY = ['红利', '沪深300', '黄金', '纳指', '恒生', '中证500']
A_SHARES = ['红利', '沪深300', '中证500']       # 受A股信号调节
HK_SHARES = ['恒生']                            # 与A股同beta, 半幅调节
MA_WIN = 200
VOL_WIN = 60     #  realized vol 窗口
COV_WIN = 250    # 协方差窗口


def load_qfq(code):
    df = pd.read_csv(os.path.join(DATA, f'etf_{code}_qfq.csv'))
    df.columns = [str(c).lower() for c in df.columns]
    df[df.columns[0]] = pd.to_datetime(df[df.columns[0]])
    df = df.set_index(df.columns[0]).sort_index()
    return df['收盘'].astype(float)


def build_panel():
    df = bt.build_signals()
    panel = pd.DataFrame({
        '红利': df['tr_hong'],
        '沪深300': df['tr_cun'],
        '国债': df['tr_bond'],
    })
    for code, nm in [('518880', '黄金'), ('513100', '纳指'),
                     ('159920', '恒生'), ('510500', '中证500')]:
        panel[nm] = load_qfq(code).reindex(panel.index)
    return panel, df


def run_multi(panel, sig_df, cfg, start='2013-08-01', verbose=False):
    p = panel[panel.index >= pd.Timestamp(start)].copy()
    p = p.dropna(subset=['红利', '沪深300', '国债'])
    # 早期缺失资产用首值回填(不产生虚假动量)
    for c in RISKY:
        if c in p.columns:
            s = p[c]
            if s.isna().any():
                first_valid = s.first_valid_index()
                if first_valid is not None:
                    p.loc[p.index < first_valid, c] = float(s.loc[first_valid])
    r = p.pct_change()

    ma = p[RISKY].rolling(MA_WIN, min_periods=min(100, MA_WIN)).mean()
    trend = p[RISKY] > ma
    vol = r[RISKY].rolling(VOL_WIN, min_periods=20).std() * np.sqrt(252)
    mom = p[RISKY].pct_change(120)   # 6个月动量, 用于趋势内排序

    nav = [1.0]; dates = []
    w_prev = pd.Series(0.0, index=RISKY)
    wb_prev = 1.0
    turn = 0.0
    cur_m = None
    log = []

    for i in range(1, len(p)):
        date = p.index[i]
        if cur_m != (date.year, date.month):
            cur_m = (date.year, date.month)
            j = i - 1   # 用上一交易日信息决策
            t = trend.iloc[j]
            v = vol.iloc[j]
            sel = [c for c in RISKY if bool(t[c]) and not np.isnan(v[c]) and v[c] > 0]
            w = pd.Series(0.0, index=RISKY)
            if sel:
                iv = 1.0 / v[sel]
                w[sel] = iv / iv.sum()
                # —— 阿朱: A股分位/资金面调节 ——
                try:
                    srow = sig_df.loc[p.index[j]]
                    pct = srow['price_pct']; m1m2 = srow['m1m2']
                    if not np.isnan(pct):
                        if pct < 0.30:
                            mult_a = cfg['a_mult_low']
                        elif pct > 0.80:
                            mult_a = cfg['a_mult_high']
                        else:
                            mult_a = 1.0
                    else:
                        mult_a = 1.0
                    if not np.isnan(m1m2) and m1m2 < cfg['m1m2_floor']:
                        mult_a *= 0.6
                except Exception:
                    mult_a = 1.0
                for c in A_SHARES:
                    w[c] *= mult_a
                for c in HK_SHARES:
                    w[c] *= (1 + (mult_a - 1) * 0.5)
                if w.sum() > 0:
                    w = w / w.sum()
                # —— 波动率目标: 总风险仓 ——
                sub = r[RISKY].iloc[max(0, j - COV_WIN):j].dropna()
                if len(sub) > 60:
                    cov = sub.cov() * 252
                    pv = float(np.sqrt(max(w.values @ cov.values @ w.values, 1e-8)))
                else:
                    pv = float(np.sqrt((w * v.fillna(0.2)) ** 2).sum()) or 0.15
                E = float(np.clip(cfg['target_vol'] / pv, 0, cfg['eq_cap']))
            else:
                E = 0.0
            w = w * E
            wb = max(1 - w.sum() - cfg['cash'], 0.0)
            turn += float(np.abs(w - w_prev).sum() + abs(wb - wb_prev))
            cost = float(np.abs(w - w_prev).sum() + abs(wb - wb_prev)) * COST
            w_prev, wb_prev = w, wb
            log.append({'date': str(date.date()), 'E': round(float(w.sum()), 3),
                        'bond': round(wb, 3),
                        **{c: round(float(w[c]), 3) for c in RISKY}})
            # 首月成本在下一日收益中扣
        pr = float((w_prev * r.iloc[i][RISKY]).sum() + wb_prev * r.iloc[i]['国债']
                   + cfg['cash'] * ((1 + 0.02) ** (1 / 252) - 1))
        newnav = nav[-1] * (1 + pr)
        if cur_m is not None and len(log) and log[-1]['date'] == str(date.date()):
            newnav *= (1 - cost)
        nav.append(newnav); dates.append(date)

    return pd.Series(nav[1:], index=dates), pd.DataFrame(log), turn / 2 / len(p)


def metrics(nav, name=''):
    ret = nav.pct_change().dropna()
    ann = (nav.iloc[-1] / nav.iloc[0]) ** (252 / len(nav)) - 1
    dd = (nav / nav.cummax() - 1).min()
    vol = ret.std() * np.sqrt(252)
    sharpe = ann / vol if vol > 0 else 0
    calmar = ann / abs(dd) if dd < -1e-6 else np.inf
    yearly = nav.resample('YE').last()
    ys = pd.concat([pd.Series([nav.iloc[0]], index=[nav.index[0] - pd.Timedelta(days=1)]), yearly])
    yret = ys.pct_change().dropna()
    return {'name': name, '年化%': round(ann * 100, 2), '波动%': round(vol * 100, 2),
            '最大回撤%': round(dd * 100, 2), '夏普': round(sharpe, 2), '卡玛': round(calmar, 2),
            '年胜率%': round((yret > 0).mean() * 100, 1)}


CFG4 = {'target_vol': 0.05, 'eq_cap': 1.0, 'cash': 0.05, 'm1m2_floor': -10,
        'a_mult_low': 1.25, 'a_mult_high': 0.45}

if __name__ == '__main__':
    panel, sig_df = build_panel()
    print('面板:', panel.shape, panel.index.min().date(), '->', panel.index.max().date())
    print('== v4 波动率目标扫描 (target_vol) ==')
    rows = []
    for tv in [0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10, 0.12]:
        c = dict(CFG4); c['target_vol'] = tv
        nav, log, turn = run_multi(panel, sig_df, c)
        m = metrics(nav, f'target_vol={tv:.0%}')
        m['换手/年'] = round(turn * 252, 1)
        rows.append(m)
        print(json.dumps(m, ensure_ascii=False))
    r = pd.DataFrame(rows)
    print('\n== 收益-回撤前沿 ==')
    print(r.to_string(index=False))
