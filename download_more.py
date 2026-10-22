# -*- coding: utf-8 -*-
"""下载跨资产 ETF 原始价: 黄金518880 / 纳指513100 / 恒生159920 / 十年国债511260 / 商品豆粕159985"""
import os, time
import pandas as pd
import akshare as ak

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")

TARGETS = {
    '518880': '黄金ETF',
    '513100': '纳指ETF',
    '159920': '恒生ETF',
    '511260': '十年国债ETF',
    '159985': '豆粕ETF',
    '512690': '酒ETF',
}

for code, nm in TARGETS.items():
    out = os.path.join(DATA, f'etf_{code}_raw.csv')
    if os.path.exists(out):
        print('skip', code, nm); continue
    try:
        df = ak.fund_etf_hist_em(symbol=code, period='daily',
                                 start_date='20120101', end_date='20261231', adjust='')
        df.to_csv(out, index=False, encoding='utf-8-sig')
        print(f'OK {code} {nm}: {len(df)} rows {df.iloc[0,0]} -> {df.iloc[-1,0]}')
    except Exception as e:
        print(f'FAIL {code} {nm}: {e}')
    time.sleep(1)

# 红利低波 / 中证500ETF 作为进攻仓备选
for code, nm in {'512890': '红利低波ETF', '510500': '中证500ETF'}.items():
    out = os.path.join(DATA, f'etf_{code}_raw.csv')
    if os.path.exists(out):
        print('skip', code, nm); continue
    try:
        df = ak.fund_etf_hist_em(symbol=code, period='daily',
                                 start_date='20120101', end_date='20261231', adjust='')
        df.to_csv(out, index=False, encoding='utf-8-sig')
        print(f'OK {code} {nm}: {len(df)} rows {df.iloc[0,0]} -> {df.iloc[-1,0]}')
    except Exception as e:
        print(f'FAIL {code} {nm}: {e}')
    time.sleep(1)
