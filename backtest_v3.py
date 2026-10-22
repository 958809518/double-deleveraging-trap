# -*- coding: utf-8 -*-
"""
"朱格一号" v3 —— 连续仓位 + 日度滞回风控（组合保险）

v2 的问题: 月度离散调仓 + 月度熔断 => 风控太粗，回撤只能靠压低仓位实现(收益封顶~6.5%)
v3 的改动:
  1) 权益敞口连续化: 分位/趋势/资金面/动量 各自乘一个系数，不再跳档
  2) 日度滞回风控(核心): 追踪自身NAV水下深度 dd, 分三档降仓, 且用"进/出阈值不同"的滞回带
     防止阈值附近反复横跳。回撤被硬约束 => 可以把基础仓位 cap 提上去 => 收益提升
  3) 红利/进攻仓内部按相对动量倾斜
  4) 计入交易成本(单边万三)
"""
import pandas as pd
import numpy as np
import json, os

import backtest_v2 as bt

COST = 0.0003          # 单边交易成本 万三
CASH_YLD = bt.CASH_YLD


# ---------------- 1. 权益敞口连续函数 ----------------
def equity_target(row, cfg):
    """返回目标权益总仓(0~1)。阿朱框架: 逐水草而居 × 趋势在才持仓 × 资金面确认"""
    pct, trend, volr, m1m2, mom = (
        row['price_pct'], row['trend_ok'], row['vol_ratio'], row['m1m2'], row['mom20'])
    if pd.isna(pct) or pd.isna(trend):
        return 0.15
    base = cfg['eq_cap']
    # (a) 估值分位: 洼地重仓, 炒高收缩
    if pct < 0.20:
        m = 1.00
    elif pct < 0.40:
        m = 0.90
    elif pct < 0.60:
        m = 0.72
    elif pct < 0.80:
        m = 0.48
    else:
        m = cfg['top_mult']          # 炒高档系数(可调)
    # (b) 趋势: 年线之上才谈仓位
    if not trend:
        m *= cfg['notrend_mult']
    # (c) 场外资金 M1-M2
    if m1m2 < cfg['m1m2_floor']:
        m *= 0.70
    # (d) 场内资金 成交额冷热
    if volr < cfg['vol_floor']:
        m *= 0.80
    # (e) 动量刹车
    if mom < -0.10:
        m *= 0.60
    return float(np.clip(base * m, 0.0, cfg['eq_cap']))


def split_equity(row, eq, cfg):
    """权益内部: 红利(防守/高股息) vs 沪深300(进攻) —— 按相对动量+分位倾斜"""
    if eq <= 0:
        return 0.0, 0.0
    mom_h = row.get('mom60_hong', np.nan)
    mom_c = row.get('mom60_cun', np.nan)
    pct = row['price_pct']
    # 默认配比: 洼地偏红利(有股息垫), 趋势强偏300(弹性)
    base_h = 0.60 if (pd.isna(pct) or pct > 0.5) else 0.50
    if pd.notna(mom_h) and pd.notna(mom_c):
        tilt = np.clip((mom_h - mom_c) * 2.0, -0.30, 0.30)   # 相对动量偏移
        base_h = float(np.clip(base_h + tilt, 0.20, 0.90))
    h = eq * base_h
    c = eq - h
    return h, c


# ---------------- 2. 日度滞回风控 ----------------
def risk_scale(dd, state, cfg):
    """水下深度 -> 仓位缩放系数。进/出阈值不同(滞回)"""
    hd, wd, sd = cfg['hard_dd'], cfg['warn_dd'], cfg['soft_dd']
    hx, wx, sx = cfg['hard_exit'], cfg['warn_exit'], cfg['soft_exit']
    if dd <= hd:
        state = 3
    elif dd <= wd:
        state = max(state, 2)
    elif dd <= sd:
        state = max(state, 1)
    # 退出(需回到更浅的水位)
    if state == 3 and dd > hx:
        state = 2
    elif state == 2 and dd > wx:
        state = 1
    elif state == 1 and dd > sx:
        state = 0
    scale = {0: 1.0, 1: cfg['s1'], 2: cfg['s2'], 3: cfg['s3']}[state]
    return scale, state


# ---------------- 3. 回测主循环 ----------------
def run_v3(df, cfg, start='2013-04-01', rebal='M', verbose=False):
    cols = ['r_tr_hong', 'r_tr_cun', 'r_tr_bond']
    d = df[df.index >= start].dropna(subset=cols).copy()
    d['mom60_hong'] = d['tr_hong'].pct_change(60)
    d['mom60_cun'] = d['tr_cun'].pct_change(60)

    wh, wc, wb, wy = 0.10, 0.0, 0.75, 0.15
    nav = [1.0]; dates = []
    peak = 1.0; state = 0
    cur_key = None
    tgt_eq = 0.15
    turnover = 0.0
    alloc_log = []
    state_days = {0: 0, 1: 0, 2: 0, 3: 0}

    for i in range(1, len(d)):
        date, row = d.index[i], d.iloc[i]
        # ---- 择时层: 月度/周度 重新计算目标权益 ----
        key = (date.year, date.month) if rebal == 'M' else date.isocalendar()[:2]
        if cur_key != key:
            cur_key = key
            sig = d.iloc[i - 1]
            tgt_eq = equity_target(sig, cfg)
        # ---- 风控层: 每日 ----
        sc, state = risk_scale(nav[-1] / peak - 1, state, cfg)
        state_days[state] += 1
        th, tc = split_equity(d.iloc[i - 1], tgt_eq * sc, cfg)
        tb = max(1 - th - tc - cfg['cash'], 0.0)
        ty = cfg['cash']
        # ---- 换手与成本 ----
        turnover += abs(th - wh) + abs(tc - wc) + abs(tb - wb)
        cost = (abs(th - wh) + abs(tc - wc) + abs(tb - wb)) * COST
        wh, wc, wb, wy = th, tc, tb, ty
        pr = (wh * row['r_tr_hong'] + wc * row['r_tr_cun']
              + wb * row['r_tr_bond'] + wy * row['r_cash'])
        nn = nav[-1] * (1 + pr) * (1 - cost)
        peak = max(peak, nn)
        nav.append(nn); dates.append(date)
        alloc_log.append({'date': str(date.date()), 'eq': round(th + tc, 3),
                          'scale': sc, 'state': state})

    nav_s = pd.Series(nav[1:], index=dates)
    return nav_s, pd.DataFrame(alloc_log), turnover / 2 / len(d), state_days


def metrics(nav, name=''):
    ret = nav.pct_change().dropna()
    ann = (nav.iloc[-1] / nav.iloc[0]) ** (252 / len(nav)) - 1
    dd = (nav / nav.cummax() - 1).min()
    sharpe = ret.mean() / ret.std() * np.sqrt(252) if ret.std() > 0 else 0
    calmar = ann / abs(dd) if dd < -1e-6 else np.inf
    yearly = nav.resample('YE').last()
    yr_start = pd.concat([pd.Series([nav.iloc[0]], index=[nav.index[0] - pd.Timedelta(days=1)]), yearly])
    yret = yr_start.pct_change().dropna()
    return {'name': name, '年化%': round(ann * 100, 2), '最大回撤%': round(dd * 100, 2),
            '夏普': round(sharpe, 2), '卡玛': round(calmar, 2),
            '年胜率%': round((yret > 0).mean() * 100, 1)}


CFG3 = {
    'eq_cap': 0.60, 'top_mult': 0.18, 'notrend_mult': 0.45,
    'm1m2_floor': -10, 'vol_floor': 0.6, 'cash': 0.05,
    # 日度风控滞回带
    'hard_dd': -0.022, 'warn_dd': -0.013, 'soft_dd': -0.007,
    'hard_exit': -0.010, 'warn_exit': -0.005, 'soft_exit': -0.002,
    's1': 0.70, 's2': 0.40, 's3': 0.15,
}

if __name__ == '__main__':
    df = bt.build_signals()
    print('== v3 基础扫描: 权益上限 eq_cap × 风控档位 ==')
    rows = []
    for cap in [0.45, 0.55, 0.65, 0.75, 0.85, 1.00]:
        for s3 in [0.10, 0.15, 0.25]:
            c = dict(CFG3); c['eq_cap'] = cap; c['s3'] = s3
            nav, alog, turn, sd = run_v3(df, c)
            m = metrics(nav, f'cap={cap} s3={s3}')
            m['换手/年'] = round(turn * 252, 1)
            rows.append(m)
            print(json.dumps(m, ensure_ascii=False))
    r = pd.DataFrame(rows).sort_values('年化%', ascending=False)
    print('\n按年化排序 top6:')
    print(r.head(6).to_string(index=False))
