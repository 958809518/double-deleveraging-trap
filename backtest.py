# -*- coding: utf-8 -*-
"""
"朱格一号" 量化模型回测引擎
—— 基于"阿朱说"投资框架的股债配置择时模型

核心思想（来自文章语料）:
  1. 场外+场内资金定牛熊 (大A历次牛市的形成原因 / 牛还在不在)
  2. 估值分位定赔率: 洼地重仓、高位回归 (逐水草而居/潮涨潮落)
  3. 红利底仓=耐心资本等分红 (板块轮动有规律/新韭菜)
  4. 大跌即机会, 每年1-2次 (牛还在不在)
  5. 纪律的钱: 月度回撤熔断 (股市本质是赚四个钱)
  6. 因子宜少 (量化技术的反常识): 仅5个信号
"""
import pandas as pd
import numpy as np
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
PY_ = None

# ---------- 参数 ----------
COST = 0.0003          # 单边交易成本 0.03%（ETF佣金+滑点）
CASH_YLD = 0.02        # 现金年化（货基/逆回购）
EQ_CAP = 0.40          # 权益总仓上限（参数化便于敏感性分析）
DD_TRIG1, DD_TRIG2 = -0.025, -0.040   # 月度回撤熔断阈值
GRID_MIN_DROP = -0.08  # 沪深300单月大跌阈值（网格加仓）
PCT_WIN = 1250         # 估值分位回看窗口（5年）
MIN_WIN = 250

def load(fn, datecol=None):
    df = pd.read_csv(os.path.join(DATA, fn))
    df.columns = [c.lower() for c in df.columns]
    # 日期列判定: 指定的列 / 第一列
    dc = datecol or df.columns[0]
    df[dc] = pd.to_datetime(df[dc])
    df = df.set_index(dc).sort_index()
    return df

def build_signals():
    hs = load('hs300.csv')
    df = pd.DataFrame(index=hs.index)
    df['hs300'] = hs['close'].astype(float)
    df['vol'] = hs['volume'].astype(float)

    # 1) 价格分位（估值代理）
    roll_max = df['hs300'].rolling(PCT_WIN, min_periods=MIN_WIN).max()
    roll_min = df['hs300'].rolling(PCT_WIN, min_periods=MIN_WIN).min()
    df['price_pct'] = (df['hs300'] - roll_min) / (roll_max - roll_min + 1e-9)

    # 2) 趋势（年线）
    df['ma250'] = df['hs300'].rolling(250, min_periods=120).mean()
    df['trend_ok'] = df['hs300'] > df['ma250']

    # 3) 动量（20日）
    df['mom20'] = df['hs300'].pct_change(20)

    # 4) 场内资金（成交额冷热: 20日/250日均量）
    df['vol_ratio'] = df['vol'].rolling(20, min_periods=10).mean() / \
                      df['vol'].rolling(250, min_periods=60).mean()

    # 5) 场外资金（M1-M2剪刀差，月度）
    m = pd.read_csv(os.path.join(DATA, 'macro_money_supply.csv'))
    m.columns = [c.lower() for c in m.columns]
    m.index = pd.to_datetime(m['月份'].str.replace('年', '-').str.replace('月份', '').str.replace('月', ''))
    m1 = m['货币(m1)-同比增长'].astype(float)
    m2 = m['货币和准货币(m2)-同比增长'].astype(float)
    gap = (m1 - m2).sort_index()
    df['m1m2'] = gap.reindex(df.index, method='ffill')

    # 资产价格
    hong = load('etf_510880.csv')
    df['hong'] = hong['收盘'].astype(float).reindex(df.index, method='ffill')
    hs300etf = load('etf_510300.csv')
    df['hs300etf'] = hs300etf['收盘'].astype(float).reindex(df.index, method='ffill')
    bond = load('etf_511010.csv')
    df['bond'] = bond['收盘'].astype(float).reindex(df.index, method='ffill')
    return df

def decide_targets(row, prev_mdd_equity, eq_cap):
    """根据信号决定目标权重: (hong, hs300etf, bond, cash)"""
    pct, trend = row['price_pct'], row['trend_ok']
    mom, volr, m1m2 = row['mom20'], row['vol_ratio'], row['m1m2']
    # 资金面否决: 场外退潮或场内萎缩 → 进攻仓上限5%
    liquidity_bad = (m1m2 < -10) or (volr < 0.6)
    cap300 = 0.05 if liquidity_bad else eq_cap - 0.40 if eq_cap > 0.40 else eq_cap  # 沪深300上限
    # —— 阿朱规则 ——
    if pd.isna(pct):
        return 0.30, 0.0, 0.50, 0.20   # 数据不足: 保守
    if pct < 0.30:                    # 高位: 估值回归预期, 等待
        h, c = 0.25, 0.0
    elif pct > 0.70 and trend and mom > -0.05:   # 洼地+趋势向上: 重仓
        h, c = 0.40, min(0.35, cap300)
    elif pct > 0.70 and not trend:               # 洼地但趋势未修复: 左侧小仓
        h, c = 0.45, min(0.05, cap300)
    else:                                         # 中枢
        h, c = (0.40, min(0.10, cap300)) if trend else (0.35, 0.0)
    # 权益超上限 → 超额划入债
    if h + c > eq_cap:
        scale = (eq_cap - c) / h if h > 0 else 0
        h = max(h * scale, 0.10)
    # 熔断降档
    if prev_mdd_equity <= DD_TRIG2:
        h, c = min(h, 0.20), 0.0
    elif prev_mdd_equity <= DD_TRIG1:
        h, c = h * 0.7, c * 0.5
    b = 1 - h - c - 0.05
    return h, c, b, 0.05

def backtest(df, eq_cap=EQ_CAP, use_grid=True, use_breaker=True, start='2013-04-01'):
    df = df[df.index >= start].copy()
    d = df.dropna(subset=['hong', 'hs300etf', 'bond']).copy()
    # 日收益
    for col in ['hong', 'hs300etf', 'bond']:
        d[f'r_{col}'] = d[col].pct_change()
    d['r_cash'] = (1 + CASH_YLD) ** (1 / 252) - 1
    d['hs300_mom_chg'] = d['hs300'].pct_change()  # 月末用于网格判断

    weights = {'h': 0.30, 'c': 0.0, 'b': 0.50, 'y': 0.20}
    nav, dates = [1.0], []
    grid_bonus = 0.0
    prev_mdd_equity = 0.0
    month_prev_nav = 1.0
    cur_month = None
    results = []

    for i in range(1, len(d)):
        date = d.index[i]
        row = d.iloc[i]
        new_month = date.month != cur_month
        if new_month:
            cur_month = date.month
            # —— 月末调仓: 用上个月末信号 ——
            sig_row = d.iloc[i - 1]
            h, c, b, y = decide_targets(sig_row, prev_mdd_equity if use_breaker else 0.0, eq_cap)
            # 网格: 上月沪深300大跌且估值不低 → 追加进攻仓
            if use_grid and new_month:
                pass
            weights = {'h': h, 'c': c, 'b': b, 'y': y}
            grid_bonus = 0.0
            # 记录
            results.append({'date': str(date.date()), 'h': round(h, 3), 'c': round(c, 3),
                            'b': round(b, 3), 'y': round(y, 3)})
        # 日组合收益
        port_ret = (weights['h'] * row['r_hong'] + weights['c'] * row['r_hs300etf']
                    + weights['b'] * row['r_bond'] + weights['y'] * row['r_cash'])
        nav.append(nav[-1] * (1 + port_ret))
        dates.append(date)
        # 月度回撤跟踪
        if date.month != cur_month or i == len(d) - 1:
            pass

    nav_s = pd.Series(nav[1:], index=dates)
    return nav_s, pd.DataFrame(results)

def metrics(nav, name=''):
    ret = nav.pct_change().dropna()
    ann = (nav.iloc[-1] / nav.iloc[0]) ** (252 / len(nav)) - 1
    dd = (nav / nav.cummax() - 1).min()
    sharpe = ret.mean() / ret.std() * np.sqrt(252) if ret.std() > 0 else 0
    calmar = ann / abs(dd) if dd < 0 else np.inf
    # 年度收益
    yearly = nav.resample('YE').last().pct_change()
    win_rate = (yearly > 0).mean()
    return {'name': name, '年化': round(ann * 100, 2), '最大回撤': round(dd * 100, 2),
            '夏普': round(sharpe, 2), '卡玛': round(calmar, 2),
            '年胜率': round(win_rate * 100, 1), '天数': len(nav)}

if __name__ == '__main__':
    df = build_signals()
    df.to_pickle(os.path.join(BATA := DATA, 'signals.pkl'))
    print('信号表:', df.shape, '区间:', df.index.min().date(), '->', df.index.max().date())

    nav, allocs = backtest(df)
    m = metrics(nav, '朱格一号(基准)')
    print(json.dumps(m, ensure_ascii=False))

    # 基准对比: 满仓红利 / 满仓沪深300 / 60-40
    nav_h = df['hong'].dropna(); nav_h = nav_h[nav_h.index >= '2013-04-01']
    nav_h = nav_h / nav_h.iloc[0]
    print(json.dumps(metrics(nav_h, '满仓红利ETF'), ensure_ascii=False))
    nav_3 = df['hs300etf'].dropna(); nav_3 = nav_3[nav_3.index >= '2013-04-01']
    nav_3 = nav_3 / nav_3.iloc[0]
    print(json.dumps(metrics(nav_3, '满仓沪深300ETF'), ensure_ascii=False))
    nav_b = df['bond'].dropna(); nav_b = nav_b[nav_b.index >= '2013-04-01']
    nav_b = nav_b / nav_b.iloc[0]
    print(json.dumps(metrics(nav_b, '满仓国债ETF'), ensure_ascii=False))

    # 60/40 静态再平衡(红利60/债40)
    r_h = df['hong'].pct_change(); r_b = df['bond'].pct_change()
    port = 0.6 * r_h + 0.4 * r_b
    port = port[port.index >= '2013-04-01'].dropna()
    nav6040 = (1 + port).cumprod()
    print(json.dumps(metrics(nav6040, '静态60/40(红利/国债)'), ensure_ascii=False))
