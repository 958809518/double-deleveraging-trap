# -*- coding: utf-8 -*-
"""下载回测所需数据: 指数/ETF/宏观/两融, 保存为CSV"""
import akshare as ak
import pandas as pd
import os, time, traceback

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)
PY = None  # 仅作标记

START, END = "20100101", "20261021"

def save(df, name):
    p = os.path.join(DATA, name)
    df.to_csv(p, index=False, encoding="utf-8-sig")
    print(f"  saved {name}: {len(df)} rows, {df.columns.tolist()[:6]}")

def try_fetch(name, fn, *args, **kw):
    try:
        df = fn(*args, **kw)
        save(df, name)
        return df
    except Exception as e:
        print(f"  [FAIL] {name}: {type(e).__name__} {str(e)[:120]}")
        return None

print("== 1. 指数/ETF ==")
# 沪深300
df = try_fetch("hs300.csv", ak.stock_zh_index_daily, symbol="sh000300")
time.sleep(1)
# 中证红利 (000922)
df = try_fetch("zzhonghongli.csv", ak.stock_zh_index_daily, symbol="sh000922")
time.sleep(1)
# 上证国债指数 (000012) — 长期债市代理
df = try_fetch("gzindex.csv", ak.stock_zh_index_daily, symbol="sh000012")
time.sleep(1)
# 中证A500 (000510)
df = try_fetch("zza500.csv", ak.stock_zh_index_daily, symbol="sh000510")
time.sleep(1)
# 中证1000 (000852) 小盘代理
df = try_fetch("zz1000.csv", ak.stock_zh_index_daily, symbol="sh000852")
time.sleep(1)

print("== 2. 红利ETF 510880 (前复权) ==")
df = try_fetch("etf_510880.csv", ak.fund_etf_hist_em, symbol="510880",
               period="daily", start_date=START, end_date=END, adjust="qfq")
time.sleep(1)

print("== 3. 国债ETF 511010 (前复权) ==")
df = try_fetch("etf_511010.csv", ak.fund_etf_hist_em, symbol="511010",
               period="daily", start_date=START, end_date=END, adjust="qfq")
time.sleep(1)

print("== 4. 沪深300ETF 510300 ==")
df = try_fetch("etf_510300.csv", ak.fund_etf_hist_em, symbol="510300",
               period="daily", start_date=START, end_date=END, adjust="qfq")
time.sleep(1)

print("== 5. 宏观: 10Y国债收益率 ==")
# akshare 中国国债收益率历史
try:
    df = ak.bond_zh_us_rate(start_date="20100101")
    save(df, "cn_us_bond_rate.csv")
except Exception as e:
    print(f"  [FAIL] bond_zh_us_rate: {str(e)[:100]}")
    # 备选
    try:
        df = ak.macro_china_bond_public()
        save(df, "macro_bond.csv")
    except Exception as e2:
        print(f"  [FAIL] macro_china_bond_public: {str(e2)[:100]}")

print("== 6. 宏观: M1/M2 ==")
for fname, fn in [("macro_m1m2.csv", None)]:
    pass
try:
    df = ak.macro_china_money_supply()
    save(df, "macro_money_supply.csv")
except Exception as e:
    print(f"  [FAIL] money_supply: {str(e)[:100]}")

print("== 7. 两融余额 ==")
try:
    df = ak.stock_margin_sse(start_date="20100101", end_date="20261021")
    save(df, "margin_sse.csv")
except Exception as e:
    print(f"  [FAIL] margin_sse: {str(e)[:100]}")
    try:
        df = ak.stock_margin_detail_sse(date="20240101")
        save(df, "margin_detail.csv")
    except Exception as e2:
        print(f"  [FAIL] margin_detail: {str(e2)[:100]}")

print("\nDONE. files in data/:")
for f in sorted(os.listdir(DATA)):
    print("  ", f, os.path.getsize(os.path.join(DATA, f)) // 1024, "KB")
