# -*- coding: utf-8 -*-
"""
"朱格一号" v2 —— 基于阿朱投资框架的股债配置择时模型
干净数据: 原始价 + 天天基金F10分红记录构建全收益序列

信号（全部来自阿朱文章语料，因子宜少）:
  S1 价格分位 price_pct   —— 逐水草而居（洼地重仓/高位回归）
  S2 年线趋势 trend_ok    —— 趋势在才持仓（价格包含一切）
  S3 成交额冷热 vol_ratio —— 场内资金确认
  S4 M1-M2剪刀差 m1m2     —— 场外资金确认
  S5 月度回撤熔断          —— 纪律的钱
规则（月度调仓，月末信号，次月首日执行近似为当月生效）
"""
import pandas as pd
import numpy as np
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")

CASH_YLD = 0.02

# ---------------- 分红记录（除息日, 每份分红）----------------
DIVS = {
    'hong': {  # 510880
        '2014-01-21': 0.059, '2015-01-20': 0.080, '2016-01-20': 0.050, '2017-01-23': 0.091,
        '2018-01-23': 0.109, '2019-01-16': 0.098, '2020-01-17': 0.144, '2021-01-18': 0.141,
        '2022-01-17': 0.086, '2023-01-16': 0.138, '2024-01-23': 0.131, '2025-01-21': 0.142,
        '2026-01-21': 0.143,
    },
    'cun': {  # 510300 沪深300ETF
        '2014-01-21': 0.048, '2015-01-20': 0.035, '2016-01-20': 0.051, '2017-01-23': 0.055,
        '2018-01-23': 0.046, '2019-01-16': 0.059, '2019-12-11': 0.062, '2021-01-18': 0.072,
        '2022-01-19': 0.075, '2023-01-16': 0.064, '2024-01-18': 0.069, '2025-06-18': 0.088,
        '2026-01-19': 0.123,
    },
    'bond': {  # 511010 国债ETF
        '2015-10-09': 1.000, '2025-09-23': 1.450, '2025-12-26': 0.654, '2026-03-25': 0.5715,
        '2026-06-25': 0.8144, '2026-09-18': 0.6204,
    },
}

def load_raw(fn):
    df = pd.read_csv(os.path.join(DATA, fn))
    df.columns = [str(c).lower() for c in df.columns]
    dc = df.columns[0]
    df[dc] = pd.to_datetime(df[dc])
    df = df.set_index(dc).sort_index()
    return df['收盘'].astype(float)

def build_tr(price, divs):
    """原始价格 + 分红 -> 全收益序列 (起点归一为1)"""
    r = price.pct_change()
    for d, amt in divs.items():
        d = pd.Timestamp(d)
        if d in price.index:
            idx = price.index.get_loc(d)
            if idx > 0:
                prev = price.iloc[idx - 1]
                r.iloc[idx] += amt / prev
    tr = (1 + r.fillna(0)).cumprod()
    return tr

def build_signals():
    hs = pd.read_csv(os.path.join(DATA, 'hs300.csv'))
    hs.columns = [c.lower() for c in hs.columns]
    hs[hs.columns[0]] = pd.to_datetime(hs[hs.columns[0]])
    hs = hs.set_index(hs.columns[0]).sort_index()
    df = pd.DataFrame(index=hs.index)
    df['hs300'] = hs['close'].astype(float)
    df['vol'] = hs['volume'].astype(float)

    df['price_pct'] = (df['hs300'] - df['hs300'].rolling(1250, min_periods=250).min()) / \
        (df['hs300'].rolling(1250, min_periods=250).max() - df['hs300'].rolling(1250, min_periods=250).min() + 1e-9)
    df['ma250'] = df['hs300'].rolling(250, min_periods=120).mean()
    df['trend_ok'] = df['hs300'] > df['ma250']
    df['mom20'] = df['hs300'].pct_change(20)
    df['vol_ratio'] = df['vol'].rolling(20, min_periods=10).mean() / \
                      df['vol'].rolling(250, min_periods=60).mean()

    m = pd.read_csv(os.path.join(DATA, 'macro_money_supply.csv'))
    m.columns = [c.lower() for c in m.columns]
    m.index = pd.to_datetime(m['月份'].str.replace('年', '-').str.replace('月份', '').str.replace('月', ''))
    gap = (m['货币(m1)-同比增长'].astype(float) - m['货币和准货币(m2)-同比增长'].astype(float)).sort_index()
    df['m1m2'] = gap.reindex(df.index, method='ffill')

    df['tr_hong'] = build_tr(load_raw('etf_510880_raw.csv'), DIVS['hong'])
    df['tr_cun'] = build_tr(load_raw('etf_510300_raw.csv'), DIVS['cun'])
    df['tr_bond'] = build_tr(load_raw('etf_511010_raw.csv'), DIVS['bond'])
    for c in ['tr_hong', 'tr_cun', 'tr_bond']:
        df[f'r_{c}'] = df[c].pct_change()
    df['r_cash'] = (1 + CASH_YLD) ** (1 / 252) - 1
    df['hs_ret_m'] = df['hs300'].pct_change()
    return df

def decide_targets(row, prev_mdd, cfg):
    """核心规则: 返回 (hong, cun, bond, cash) 目标权重"""
    pct, trend, mom, volr, m1m2 = row['price_pct'], row['trend_ok'], row['mom20'], row['vol_ratio'], row['m1m2']
    if pd.isna(pct) or pd.isna(trend):
        return 0.15, 0.0, 0.70, 0.15
    cap = cfg['eq_cap']
    # 资金面否决
    liq_bad = (m1m2 < cfg['m1m2_floor']) or (volr < cfg['vol_floor'])
    # —— 阿朱: 潮涨潮落逐水草而居. 分位低=洼地(加), 分位高=炒高(减) ——
    if pct < 0.30 and trend:
        # 洼地+趋势修复: 国家队托底概率+耐心资本重仓
        h, c = cap * 0.62, cap * 0.38
    elif pct < 0.30 and not trend:
        # 洼地但趋势未修复: 左侧分批
        h, c = cap * 0.50, 0.0
    elif pct > 0.80:
        # 炒高: 阳极阴起, 估值回归预期 — 收缩
        h, c = 0.15, 0.0
    elif not trend:
        # 中枢但趋势不在: 潮退了退场
        h, c = 0.10, 0.0
    else:
        # 中枢+趋势在: 底仓+小弹性
        h, c = cap * 0.67, cap * 0.33
    if liq_bad:
        c = 0.0
    # 动量刹车: 快速下跌期减速
    if mom < -0.10:
        h, c = h * 0.6, c * 0.4
    # 权益总仓封顶
    if h + c > cap:
        sc = (cap - c) / h if h > 0 else 0
        h = h * sc
    # —— 纪律的钱: 月度回撤熔断 ——
    if prev_mdd <= cfg['dd3']:
        h, c = min(h, 0.05), 0.0
    elif prev_mdd <= cfg['dd2']:
        h, c = h * 0.5, 0.0
    elif prev_mdd <= cfg['dd1']:
        h, c = h * 0.8, c * 0.5
    b = max(1 - h - c - 0.05, 0)
    return h, c, b, 0.05

def run_backtest(df, cfg, start='2013-04-01'):
    d = df[df.index >= start].dropna(subset=['r_tr_hong', 'r_tr_cun', 'r_tr_bond']).copy()
    wh, wc, wb, wy = 0.15, 0.0, 0.70, 0.15
    nav = [1.0]; dates = []
    month_ret = 0.0
    cur_m = None
    pos_mdd = 0.0       # 当月最大回撤(相对月初)
    month_start_nav = 1.0
    prev_month_mdd = 0.0
    alloc_log, grid_log = [], []
    turnover = 0.0
    for i in range(1, len(d)):
        date, row = d.index[i], d.iloc[i]
        if cur_m != (date.year, date.month):
            if cur_m is not None:
                prev_month_mdd = month_mdd  # 上月月内最大回撤
            cur_m = (date.year, date.month)
            month_mdd = 0.0
            month_start_nav = nav[-1]
            # —— 月末再平衡（用上日信号）——
            sig = d.iloc[i - 1]
            nh, nc, nb, ny = decide_targets(sig, prev_month_mdd, cfg)
            # 大跌网格: 上月沪深300大跌且处于洼地/中枢(非高位) → 进攻仓+grid_add
            if cur_m is not None and i >= 22:
                hs_m = d['hs300'].iloc[i - 1] / d['hs300'].iloc[i - 22] - 1
                if hs_m <= -0.08 and sig['price_pct'] < 0.50:
                    add = min(cfg['grid_add'], nb)
                    nc += add; nb -= add
                    grid_log.append((str(date.date()), round(float(hs_m), 3)))
            turnover += abs(nh - wh) + abs(nc - wc) + abs(nb - wb) + abs(ny - wy)
            wh, wc, wb, wy = nh, nc, nb, ny
            alloc_log.append({'date': str(date.date()), 'h': round(wh, 3), 'c': round(wc, 3),
                              'b': round(wb, 3), 'y': round(wy, 3)})
            month_ret = 0.0
        pr = wh * row['r_tr_hong'] + wc * row['r_tr_cun'] + wb * row['r_tr_bond'] + wy * row['r_cash']
        new_nav = nav[-1] * (1 + pr)
        cur_mdd = min(new_nav / month_start_nav - 1, new_nav / max([n for n in nav[-30:]], default=new_nav) - 1)
        month_mdd = min(month_mdd, cur_mdd)
        nav.append(new_nav)
        dates.append(date)
    nav_s = pd.Series(nav[1:], index=dates)
    return nav_s, pd.DataFrame(alloc_log), grid_log, turnover / 2 / len(d)

def metrics(nav, name=''):
    ret = nav.pct_change().dropna()
    ann = (nav.iloc[-1] / nav.iloc[0]) ** (252 / len(nav)) - 1
    dd = (nav / nav.cummax() - 1).min()
    sharpe = ret.mean() / ret.std() * np.sqrt(252) if ret.std() > 0 else 0
    calmar = ann / abs(dd) if dd < 0 else np.inf
    yearly = nav.resample('YE').last().pct_change().dropna()
    win = (yearly > 0).mean()
    return {'name': name, '年化%': round(ann * 100, 2), '最大回撤%': round(dd * 100, 2),
            '夏普': round(sharpe, 2), '卡玛': round(calmar, 2), '年胜率%': round(win * 100, 1)}

BASE_CFG = {'eq_cap': 0.35, 'm1m2_floor': -10, 'vol_floor': 0.6, 'grid_add': 0.10,
            'dd1': -0.02, 'dd2': -0.03, 'dd3': -0.045}

if __name__ == '__main__':
    df = build_signals()
    df.to_pickle(os.path.join(DATA, 'signals_v2.pkl'))
    print('信号表:', df.shape, df.index.min().date(), '->', df.index.max().date())
    # 全收益序列 sanity check
    for c in ['tr_hong', 'tr_cun', 'tr_bond']:
        s = df[c].dropna(); s = s[s.index >= '2013-04-01']
        print(f'{c}: {s.iloc[0]:.3f} -> {s.iloc[-1]:.3f} | 年化 {((s.iloc[-1]/s.iloc[0])**(252/len(s))-1)*100:.2f}% | MDD {(s/s.cummax()-1).min()*100:.1f}%')

    nav, allocs, grid, turn = run_backtest(df, BASE_CFG)
    print('\n== 朱格一号 v2 基准 ==')
    print(json.dumps(metrics(nav, '朱格一号'), ensure_ascii=False))
    print('网格加仓次数:', len(grid), '| 年化换手:', round(turn * 252, 2))

    # 基准资产
    for c, nm in [('tr_hong', '满仓红利'), ('tr_cun', '满仓沪深300'), ('tr_bond', '满仓国债')]:
        s = df[c].dropna(); s = s[s.index >= '2013-04-01']
        nav_b = s / s.iloc[0]
        print(json.dumps(metrics(nav_b, nm), ensure_ascii=False))
