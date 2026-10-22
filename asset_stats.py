# -*- coding: utf-8 -*-
"""多资产池统计(已校正份额折算): 年化/波动/夏普/MDD 与相关性矩阵"""
import os
import numpy as np
import pandas as pd
import backtest_v2 as bt

DATA = bt.DATA


def load_qfq(code):
    df = pd.read_csv(os.path.join(DATA, f'etf_{code}_qfq.csv'))
    df.columns = [str(c).lower() for c in df.columns]
    df[df.columns[0]] = pd.to_datetime(df[df.columns[0]])
    df = df.set_index(df.columns[0]).sort_index()
    p = df['收盘'].astype(float)
    return p / p.iloc[0]


def stats(s, name):
    s = s.dropna()
    r = s.pct_change().dropna()
    ann = (s.iloc[-1] / s.iloc[0]) ** (252 / len(s)) - 1
    vol = r.std() * np.sqrt(252)
    dd = (s / s.cummax() - 1).min()
    return {'资产': name, '年化%': round(ann * 100, 2), '波动%': round(vol * 100, 2),
            '夏普': round(ann / vol, 2), 'MDD%': round(dd * 100, 2)}


if __name__ == '__main__':
    df = bt.build_signals()
    series = {'红利ETF': df['tr_hong'], '沪深300ETF': df['tr_cun'], '国债ETF': df['tr_bond']}
    for code, nm in [('518880', '黄金ETF'), ('513100', '纳指ETF'),
                     ('159920', '恒生ETF'), ('510500', '中证500ETF')]:
        series[nm] = load_qfq(code)

    print('== 全样本(各自起始日) ==')
    print(pd.DataFrame([stats(s, k) for k, s in series.items()]).to_string(index=False))

    st = '2013-08-01'
    sub = {k: s[s.index >= st] for k, s in series.items()
           if s.dropna().index.min() <= pd.Timestamp(st)}
    print(f'\n== 统一区间 {st} -> ==')
    print(pd.DataFrame([stats(s / s.iloc[0], k) for k, s in sub.items()]).to_string(index=False))

    rets = pd.DataFrame({k: s.pct_change() for k, s in sub.items()}).dropna()
    print('\n== 日收益相关性 ==')
    print(rets.corr().round(2).to_string())
    rets.to_csv(os.path.join(DATA, 'multi_returns.csv'), encoding='utf-8-sig')

    # 等权 & 风险平价 静态对照
    print('\n== 静态对照(等权 / 逆波动) ==')
    vol = rets.std()
    for name, w in [('等权', pd.Series(1 / len(rets.columns), index=rets.columns)),
                    ('逆波动', (1 / vol) / (1 / vol).sum()),
                    ('60债40股', pd.Series({'国债ETF': 0.6, '红利ETF': 0.2, '沪深300ETF': 0.2}))]:
        w = w.reindex(rets.columns).fillna(0)
        w = w / w.sum()
        pr = (rets * w).sum(axis=1)
        nav = (1 + pr).cumprod()
        print(f'{name}:', stats(nav, name))
