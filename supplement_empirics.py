# -*- coding: utf-8 -*-
"""
论文补充实证:
  A 有杠杆对照组  —— 验证"无杠杆约束"是内点最优的根源
  B 交互效应回归  —— Return ~ σ* + DC + σ*×DC
  C block bootstrap 显著性
  D 机制检验 I   —— corr(已实现波动率, 水下深度)
  E 机制检验 II  —— 事件研究: 双重减仓日 vs 单一减仓日 的后续收益
  F 数据校正影响量化
"""
import os
import json
import numpy as np
import pandas as pd
import multi_strategy as ms
from multi_v5 import run_v5, ALL_RISKY, CFG5

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'paper_data')
os.makedirs(OUT, exist_ok=True)

STRICT = dict(dc1=-0.015, dc2=-0.025, dc3=-0.035, x1=-0.005, x2=-0.010, x3=-0.018,
              s1=0.70, s2=0.40, s3=0.15)
START = '2013-08-01'
BORROW = 0.03           # 融资利率(年化), 高于现金收益2%

panel, sig_df = ms.build_panel()
TVS = [0.03, 0.04, 0.05, 0.055, 0.06, 0.07, 0.09, 0.12]

results = {}


def cfg_of(tv, dc, cap):
    c = dict(CFG5); c.update(STRICT); c['target_vol'] = tv; c['dc_on'] = dc; c['eq_cap'] = cap
    return c


# ================= A. 有杠杆对照组 =================
print('=== A. 有杠杆对照组 (eq_cap=2.0, 融资利率3%) ===')
lev_rows = []
for dc in [False, True]:
    for tv in TVS:
        c = cfg_of(tv, dc, 2.0)
        nav, log, turn = run_v5(panel, sig_df, c, ALL_RISKY, start=START, borrow=BORROW)
        m = ms.metrics(nav, f'cap2|DC={dc}|tv={tv:.1%}')
        m['tv'] = tv; m['DC'] = dc; m['cap'] = 2.0
        m['换手/年'] = round(turn * 252, 2)
        lev_rows.append(m)
        print(json.dumps(m, ensure_ascii=False))
print('--- 无杠杆基线 (eq_cap=1.0) ---')
nolev_rows = []
for dc in [False, True]:
    for tv in TVS:
        c = cfg_of(tv, dc, 1.0)
        nav, log, turn = run_v5(panel, sig_df, c, ALL_RISKY, start=START)
        m = ms.metrics(nav, f'cap1|DC={dc}|tv={tv:.1%}')
        m['tv'] = tv; m['DC'] = dc; m['cap'] = 1.0
        m['换手/年'] = round(turn * 252, 2)
        nolev_rows.append(m)
        print(json.dumps(m, ensure_ascii=False))

dfA = pd.DataFrame(lev_rows + nolev_rows)
dfA.to_csv(os.path.join(OUT, 'A_leverage.csv'), index=False, encoding='utf-8-sig')
# 单调性诊断: 峰值位置
print('\n峰值位置诊断:')
for cap in [1.0, 2.0]:
    for dc in [False, True]:
        sub = dfA[(dfA['cap'] == cap) & (dfA['DC'] == dc)].sort_values('tv')
        imax = sub['年化%'].idxmax()
        tail = sub[sub['tv'] >= 0.09]['年化%'].mean()
        print(f'  cap={cap} DC={dc}: 峰值tv={sub.loc[imax,"tv"]:.1%} (年化{sub.loc[imax,"年化%"]}%), '
              f'tv>=9%平均年化={tail:.2f}%, 末端衰减={sub.loc[imax,"年化%"]-tail:+.2f}pp')
results['A'] = dfA.to_dict('records')


# ================= B. 交互效应回归 =================
print('\n=== B. 交互效应回归 ===')
try:
    import statsmodels.api as sm
    reg = dfA[dfA['cap'] == 1.0].copy()
    reg['tv100'] = reg['tv'] * 100
    reg['D'] = reg['DC'].astype(int)
    reg['inter'] = reg['tv100'] * reg['D']
    X = sm.add_constant(reg[['tv100', 'D', 'inter']])
    for ycol in ['年化%', '夏普', '卡玛']:
        m = sm.OLS(reg[ycol], X).fit()
        print(f'\n--- 因变量: {ycol} ---')
        print(m.summary().as_text()[:900])
        results[f'B_{ycol}'] = {'params': m.params.round(4).to_dict(),
                                'pvalues': m.pvalues.round(4).to_dict(),
                                'r2': round(m.rsquared, 4), 'nobs': int(m.nobs)}
except Exception as e:
    print('statsmodels 不可用:', e)


# ================= C. block bootstrap =================
print('\n=== C. block bootstrap 显著性 (block=21日, 2000次) ===')
rng = np.random.default_rng(20261022)


def block_bootstrap_sharpe_diff(r1, r2, block=21, n=2000):
    """r1, r2: 两个日收益序列(对齐). 返回夏普差的经验分布与p值(双侧)"""
    r1 = np.asarray(r1); r2 = np.asarray(r2)
    L = min(len(r1), len(r2)); r1 = r1[-L:]; r2 = r2[-L:]
    nb = int(np.ceil(L / block))

    def sh(x):
        return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0

    obs = sh(r1) - sh(r2)
    diffs = np.empty(n)
    for k in range(n):
        starts = rng.integers(0, L - block, nb)
        idx = np.concatenate([np.arange(s, s + block) for s in starts])[:L]
        diffs[k] = sh(r1[idx]) - sh(r2[idx])
    p = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
    return obs, float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5)), float(p)


def nav_of(tv, dc, cap=1.0, borrow=0.0, risky=None):
    c = cfg_of(tv, dc, cap)
    nav, _, _ = run_v5(panel, sig_df, c, risky or ALL_RISKY, start=START, borrow=borrow)
    return nav


nav_best = nav_of(0.055, True)
nav_hip  = nav_of(0.12, True)
nav_nodc = nav_of(0.055, False)
nav_hs300 = panel['沪深300'][panel.index >= START].dropna()
nav_hs300 = nav_hs300 / nav_hs300.iloc[0]
nav_hong = panel['红利'][panel.index >= START].dropna()
nav_hong = nav_hong / nav_hong.iloc[0]
nav_bond = panel['国债'][panel.index >= START].dropna()
nav_bond = nav_bond / nav_bond.iloc[0]

tests = [
    ('最优策略 vs 沪深300', nav_best, nav_hs300),
    ('最优策略 vs 红利ETF', nav_best, nav_hong),
    ('最优策略 vs 国债ETF', nav_best, nav_bond),
    ('内点最优(tv5.5%) vs 高目标(tv12%)  [同为DC=on]', nav_best, nav_hip),
    ('DC=on vs DC=off  [同为tv5.5%]', nav_best, nav_nodc),
]
boot_rows = []
for nm, a, b_ in tests:
    ra = a.pct_change().dropna(); rb = b_.pct_change().dropna()
    obs, lo, hi, p = block_bootstrap_sharpe_diff(ra.values, rb.values)
    boot_rows.append({'对比': nm, '夏普差': round(obs, 3),
                      '95%CI下': round(lo, 3), '95%CI上': round(hi, 3), 'p值': round(p, 4)})
    print(f'{nm}: ΔSharpe={obs:+.3f}  CI=[{lo:.3f},{hi:.3f}]  p={p:.4f}')
pd.DataFrame(boot_rows).to_csv(os.path.join(OUT, 'C_bootstrap.csv'), index=False, encoding='utf-8-sig')
results['C'] = boot_rows


# ================= D. 机制检验 I: corr(σ, D) =================
print('\n=== D. 机制检验 I: corr(已实现波动率, 水下深度) ===')
mech_rows = []
pools = {'全池(6资产)': ALL_RISKY,
         '剔除纳指': [c for c in ALL_RISKY if c != '纳指'],
         '剔除黄金': [c for c in ALL_RISKY if c != '黄金'],
         '仅A股+港股': ['红利', '沪深300', '中证500', '恒生'],
         '仅A股': ['红利', '沪深300', '中证500']}
for nm, rk in pools.items():
    navs = {}
    for tv in [0.055, 0.09, 0.12]:
        navs[tv] = nav_of(tv, True, risky=rk)
    r = navs[0.055].pct_change().dropna()
    sig = r.rolling(60, min_periods=20).std() * np.sqrt(252)
    ddd = (navs[0.055] / navs[0.055].cummax() - 1)
    cc = pd.concat([sig, ddd], axis=1).dropna()
    rho = float(cc.iloc[:, 0].corr(cc.iloc[:, 1]))
    # 交互衰减: 峰值 -> tv=12%
    ann055 = ms.metrics(navs[0.055], 'a')['年化%']
    ann12 = ms.metrics(navs[0.12], 'a')['年化%']
    decay = ann12 - ann055
    mech_rows.append({'资产池': nm, 'corr(σ,D)': round(rho, 3),
                      '年化@tv5.5%': ann055, '年化@tv12%': ann12,
                      '衰减pp': round(decay, 2)})
    print(f'{nm}: corr(σ,D)={rho:.3f}  年化 {ann055}% -> {ann12}%  衰减 {decay:+.2f}pp')
dfD = pd.DataFrame(mech_rows)
dfD.to_csv(os.path.join(OUT, 'D_mechanism.csv'), index=False, encoding='utf-8-sig')
results['D'] = mech_rows


# ================= E. 机制检验 II: 事件研究 =================
print('\n=== E. 机制检验 II: 事件研究(双重减仓 vs 单一减仓) ===')


def run_diag(tv, risky, start=START):
    """返回每日 state / 有效权益仓 / 目标权益仓 的日频诊断"""
    c = cfg_of(tv, True, 1.0)
    ms.RISKY = risky
    p = panel[panel.index >= pd.Timestamp(start)].copy()
    p = p.dropna(subset=['红利', '沪深300', '国债'])
    for cc in risky:
        s = p[cc]; fv = s.first_valid_index()
        if fv is not None:
            p.loc[p.index < fv, cc] = float(s.loc[fv])
    r = p.pct_change()
    ma = p[risky].rolling(c['ma'], min_periods=100).mean()
    trend = p[risky] > ma
    vol = r[risky].rolling(60, min_periods=20).std() * np.sqrt(252)
    nav = [1.0]; peak = 1.0; state = 0; cur_m = None
    rows = []
    w_prev = pd.Series(0.0, index=risky); wb_prev = 1.0
    tgt = 0.15
    for i in range(1, len(p)):
        date = p.index[i]
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
                        mu = c['a_mult_low'] if pct < 0.30 else (c['a_mult_high'] if pct > 0.80 else 1.0)
                    if not np.isnan(m1m2) and m1m2 < c['m1m2_floor']:
                        mu *= 0.6
                except Exception:
                    mu = 1.0
                for x in risky:
                    w[x] *= mu if x in ['红利', '沪深300', '中证500'] else (1 + (mu - 1) * 0.5)
                if w.sum() > 0:
                    w = w / w.sum()
                sub = r[risky].iloc[max(0, j - 250):j].dropna()
                pv = float(np.sqrt(max(w.values @ (sub.cov() * 252).values @ w.values, 1e-8))) if len(sub) > 60 else 0.15
                E = float(np.clip(c['target_vol'] / pv, 0, c['eq_cap']))
            else:
                E = 0.0
            w = w * E
            tgt = w.sum()
            wb_prev = max(1 - w.sum() - c['cash'], 0.0); w_prev = w
        dd = nav[-1] / peak - 1
        if dd <= c['dc3']:
            state = 3
        elif dd <= c['dc2']:
            state = max(state, 2)
        elif dd <= c['dc1']:
            state = max(state, 1)
        if state == 3 and dd > c['x3']:
            state = 2
        elif state == 2 and dd > c['x2']:
            state = 1
        elif state == 1 and dd > c['x1']:
            state = 0
        sc = [1.0, c['s1'], c['s2'], c['s3']][state]
        eff = tgt * sc
        rows.append({'date': date, 'state': state, 'scale': sc, 'tgt': tgt, 'eff': eff,
                     'dd': dd, 'nav': nav[-1]})
        w_eff = w_prev * sc
        extra = float(w_prev.sum() * (1 - sc))
        pr = float((w_eff * r.iloc[i][risky]).sum() + (wb_prev + extra) * r.iloc[i]['国债']
                   + c['cash'] * ((1 + 0.02) ** (1 / 252) - 1))
        nn = nav[-1] * (1 + pr)
        nav.append(nn); peak = max(peak, nn)
    dg = pd.DataFrame(rows).set_index('date')
    dg['nav'] = nav[1:len(rows) + 1]
    return dg


dg = run_diag(0.055, ALL_RISKY)
# 波动率目标层是否也在减仓: tgt < 其历史中位数 => vol层在收缩
med_tgt = dg['tgt'].median()
dg['vol_cut'] = dg['tgt'] < med_tgt
dg['dc_cut'] = dg['state'] >= 1
dg['double'] = dg['vol_cut'] & dg['dc_cut']
dg['single'] = dg['vol_cut'] & ~dg['dc_cut']

print(f'样本天数 {len(dg)}: 双重减仓 {int(dg["double"].sum())} 天, '
      f'单一减仓 {int(dg["single"].sum())} 天, 无减仓 {int((~dg["vol_cut"]).sum())} 天')

fwd_rows = []
for h in [10, 20, 40, 60]:
    fwd = dg['nav'].shift(-h) / dg['nav'] - 1
    a = fwd[dg['double']].dropna()
    b_ = fwd[dg['single']].dropna()
    c_ = fwd[~dg['vol_cut']].dropna()
    row = {'持有期(日)': h}
    for nm, arr in [('双重减仓日', a), ('单一减仓日', b_), ('未减仓日', c_)]:
        row[f'{nm}均值%'] = round(arr.mean() * 100, 3)
        row[f'{nm}中位数%'] = round(arr.median() * 100, 3)
        row[f'{nm}N'] = int(len(arr))
    # 均值差 t 检验
    from math import sqrt
    se = sqrt(a.var() / len(a) + b_.var() / len(b_))
    t = (a.mean() - b_.mean()) / se if se > 0 else np.nan
    row['双重-单一 差值pp'] = round((a.mean() - b_.mean()) * 100, 3)
    row['t值'] = round(float(t), 2)
    fwd_rows.append(row)
    print(f'  h={h:3d}: 双重{a.mean()*100:+.3f}% vs 单一{b_.mean()*100:+.3f}% vs 未减仓{c_.mean()*100:+.3f}%  '
          f'差{(a.mean()-b_.mean())*100:+.3f}pp  t={t:.2f}')
dfE = pd.DataFrame(fwd_rows)
dfE.to_csv(os.path.join(OUT, 'E_eventstudy.csv'), index=False, encoding='utf-8-sig')
results['E'] = fwd_rows
dg.to_csv(os.path.join(OUT, 'E_daily_diag.csv'), encoding='utf-8-sig')


# ================= F. 数据校正影响 =================
print('\n=== F. 份额折算校正的影响 ===')
corr_rows = []
for code, nm in [('513100', '纳指ETF'), ('510500', '中证500ETF'),
                 ('518880', '黄金ETF'), ('159920', '恒生ETF')]:
    raw = ms.load_qfq if False else None
    praw = pd.read_csv(os.path.join(BASE, 'data', f'etf_{code}_raw.csv'))
    praw.columns = [str(x).lower() for x in praw.columns]
    praw[praw.columns[0]] = pd.to_datetime(praw[praw.columns[0]])
    praw = praw.set_index(praw.columns[0]).sort_index()['收盘'].astype(float)
    pqfq = ms.load_qfq(code)
    s_raw = praw[praw.index >= START]; s_qfq = pqfq[pqfq.index >= START]
    a_raw = (s_raw.iloc[-1] / s_raw.iloc[0]) ** (252 / len(s_raw)) - 1
    a_qfq = (s_qfq.iloc[-1] / s_qfq.iloc[0]) ** (252 / len(s_qfq)) - 1
    v_raw = s_raw.pct_change().std() * np.sqrt(252)
    v_qfq = s_qfq.pct_change().std() * np.sqrt(252)
    corr_rows.append({'资产': nm, '未校正年化%': round(a_raw * 100, 2), '校正后年化%': round(a_qfq * 100, 2),
                      '年化偏差pp': round((a_qfq - a_raw) * 100, 2),
                      '未校正波动%': round(v_raw * 100, 2), '校正后波动%': round(v_qfq * 100, 2)})
    print(f'{nm}: 年化 {a_raw*100:.2f}% -> {a_qfq*100:.2f}% (偏差 {(a_qfq-a_raw)*100:+.2f}pp), '
          f'波动 {v_raw*100:.1f}% -> {v_qfq*100:.1f}%')
dfF = pd.DataFrame(corr_rows)
dfF.to_csv(os.path.join(OUT, 'F_datacorrection.csv'), index=False, encoding='utf-8-sig')
results['F'] = corr_rows

with open(os.path.join(OUT, 'supplement_results.json'), 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=1, default=str)
print('\n全部完成 ->', OUT)
