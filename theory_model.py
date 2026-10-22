# -*- coding: utf-8 -*-
"""
理论模型的数值验证（对应论文命题1-3）

设定:
  风险资产日收益  r_t = μ_t·dt + σ_t·√dt·ε_t
  波动率聚集: σ_t 两状态马尔可夫(低波/高波)
  夏普对波动敏感: SR_t = SR̄ - β·(σ_t - σ̄),  μ_t = SR_t·σ_t   (β>0: 高波动期夏普更低)
  这是既有理论基础(风险-收益权衡)又符合实证("高波动预示更高但风险调整更差的收益")的设定

两层风控:
  第一层 波动率目标  e^V_t = min(σ*/σ̂_t, Ē),  σ̂_t 用 EWMA 实时估计 (RiskMetrics λ=0.94)
  第二层 回撤控制    φ_t   = φ(D_t) 阶梯递减, D_t = 组合水下深度
  实际敞口           e_t   = e^V_t · φ_t

验证:
  命题1 截断不对称性: Ē=1 时 E[e^V] < E[σ*/σ̂], 缺口随 σ* 扩大
  命题2 负交互效应 :  Cov(e^V, φ) < 0, 且 |Cov| 随 ρ=corr(σ̂,D) 上升而增大
  命题3 内点最优   :  DC=on 时 R(σ*) 单峰; Ē 提高后恢复单调
"""
import os
import json
import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'paper_data')
os.makedirs(OUT, exist_ok=True)

# ---------------- 模拟参数（对标实证：多资产组合） ----------------
N = 4000          # 路径数
T = 2520          # 交易日(10年)
DT = 1.0 / 252
SIG_L, SIG_H = 0.078, 0.178          # 低波/高波年化波动(对标实证多资产组合 ~12%)
P_LH, P_HL = 1 / 65.0, 1 / 28.0      # 状态转移概率(低→高, 高→低)
SR_BAR = 0.62                        # 平均夏普(对标实证组合)
BETA = 0.9                           # 夏普对波动的敏感度
LAMBDA = 0.94                        # EWMA 波动率估计衰减因子
LAMBDA_M = 0.985                     # 趋势信号动量 EWMA 衰减因子(约对应半年窗口)
SCALE = {1: 1.0, 2: 0.70, 3: 0.40, 4: 0.15}   # 回撤控制档位(对应实证 s1/s2/s3)
DD_Q = [-0.015, -0.025, -0.035]
DD_X = [-0.005, -0.010, -0.018]


def simulate(rng, sigma_star, dc_on, ebar, dd_q=None, dd_x=None):
    """返回 (年化收益数组, 诊断字典)。用累加器统计, 不保存逐日序列(省内存)"""
    dd_q = dd_q or DD_Q
    dd_x = dd_x or DD_X
    sbar = (SIG_L + SIG_H) / 2
    mu_l = (SR_BAR - BETA * (SIG_L - sbar)) * SIG_L
    mu_h = (SR_BAR - BETA * (SIG_H - sbar)) * SIG_H

    state = rng.random(N) < 0.75            # True=低波
    var_hat = np.full(N, sbar ** 2)
    nav = np.ones(N)
    peak = np.ones(N)
    dstate = np.zeros(N, dtype=int)
    mom = np.zeros(N)                        # 趋势信号的 EWMA 动量

    # 累加器
    n = 0
    s_ev = s_phi = s_evphi = 0.0
    s_cv = s_cd = s_cvcd = s_cv2 = s_cd2 = 0.0
    s_e = 0.0
    s_ret = 0.0
    s_ret_hi = 0.0; n_hi = 0                 # 双重减仓期的后续收益统计
    maxdd = np.zeros(N)
    dbl = 0                                  # 双重减仓天数计数

    for t in range(T):
        u = rng.random(N)
        state = np.where(state, u >= P_LH, u < P_HL)
        sig = np.where(state, SIG_L, SIG_H)
        mu = np.where(state, mu_l, mu_h)
        eps = rng.standard_normal(N)

        sg = np.sqrt(var_hat)
        ev_un = sigma_star / sg
        ev = np.minimum(ev_un, ebar)
        s_t = (mom > 0).astype(float)        # 趋势信号: 动量>0 才持仓
        ev = ev * s_t
        dd = nav / peak - 1.0
        if dc_on:
            for k, q in enumerate(dd_q, start=1):
                dstate = np.where(dd <= q, np.maximum(dstate, k), dstate)
            for k, x in enumerate(dd_x, start=1):
                dstate = np.where((dstate == k) & (dd > x), k - 1, dstate)
            phi = np.select([dstate == 0, dstate == 1, dstate == 2, dstate == 3],
                            [SCALE[1], SCALE[2], SCALE[3], SCALE[4]], default=1.0)
        else:
            phi = np.ones(N)
        e = ev * phi

        r = mu * DT + sig * np.sqrt(DT) * eps
        pr = e * r
        nav = nav * (1 + pr)
        peak = np.maximum(peak, nav)
        maxdd = np.minimum(maxdd, nav / peak - 1.0)
        var_hat = LAMBDA * var_hat + (1 - LAMBDA) * (r ** 2) * 252.0
        mom = LAMBDA_M * mom + (1 - LAMBDA_M) * r

        evc = np.clip(ev, 0, 50)
        cut_v = 1.0 - np.clip(ev_un * s_t, 0, 1)     # 波动率目标层的削减
        cut_d = 1.0 - phi                            # 回撤控制层的削减
        s_ev += evc.sum(); s_phi += phi.sum(); s_evphi += (evc * phi).sum()
        s_cv += cut_v.sum(); s_cd += cut_d.sum(); s_cvcd += (cut_v * cut_d).sum()
        s_cv2 += (cut_v ** 2).sum(); s_cd2 += (cut_d ** 2).sum()
        dbl += int(((cut_v > 0.5) & (cut_d > 0)).sum())
        s_e += e.sum(); s_ret += pr.sum()
        n += N

    m_cv = s_cv / n; m_cd = s_cd / n
    var_cv = s_cv2 / n - m_cv ** 2
    var_cd = s_cd2 / n - m_cd ** 2
    cov_cvcd = s_cvcd / n - m_cv * m_cd
    rho_cut = cov_cvcd / np.sqrt(max(var_cv * var_cd, 1e-12))
    ann = nav ** (1 / (T * DT)) - 1
    diag = {'E[e^V]': s_ev / n, 'E[φ]': s_phi / n, 'E[e^V·φ]': s_evphi / n,
            'corr(cut_V,cut_D)': float(rho_cut), '双重减仓占比': float(dbl / n),
            '平均敞口': s_e / n, '最大回撤%': float(maxdd.mean() * 100),
            'E[φ|双重减仓]': float(s_phi / n)}
    return ann, diag


def summarize(ann):
    return float(np.nanmean(ann)), float(np.nanpercentile(ann, 5)), float(np.nanpercentile(ann, 95))


if __name__ == '__main__':
    rng = np.random.default_rng(20261022)
    sig_stars = [0.02, 0.03, 0.04, 0.05, 0.055, 0.06, 0.07, 0.09, 0.12, 0.16, 0.20]

    print('=== 命题3: 内点最优 vs 杠杆上限 ===')
    rows = []
    for ebar in [1.0, 1.5, 2.0]:
        for dc in [False, True]:
            for ss in sig_stars:
                ann, dg = simulate(rng, ss, dc, ebar)
                m, lo, hi = summarize(ann)
                rows.append({'Ē': ebar, 'DC': dc, 'σ*': ss, '年化%': round(m * 100, 2),
                             '最大回撤%': round(dg['最大回撤%'], 2)})
            sub = pd.DataFrame([r for r in rows if r['Ē'] == ebar and r['DC'] == dc])
            imax = sub['年化%'].idxmax()
            tail = sub[sub['σ*'] >= 0.12]['年化%'].mean()
            print(f'  Ē={ebar} DC={dc}: 峰值σ*={sub.loc[imax,"σ*"]:.3f} (年化{sub.loc[imax,"年化%"]}%), '
                  f'σ*>=12%均值={tail:.2f}%, 末端衰减={sub.loc[imax,"年化%"]-tail:+.2f}pp')
    dfP3 = pd.DataFrame(rows)
    dfP3.to_csv(os.path.join(OUT, 'P3_frontier_sim.csv'), index=False, encoding='utf-8-sig')

    print('\n=== 命题1: 截断不对称性 (DC=off) ===')
    rows1 = []
    for ebar in [1.0, 2.0]:
        for ss in sig_stars:
            ann, dg = simulate(rng, ss, False, ebar)
            rows1.append({'Ē': ebar, 'σ*': ss, 'E[e^V]': round(dg['E[e^V]'], 4),
                          '平均敞口': round(dg['平均敞口'], 4)})
        print(f'  Ē={ebar}:')
        for r in [x for x in rows1 if x['Ē'] == ebar]:
            print(f"    σ*={r['σ*']:.3f}: E[e^V]={r['E[e^V]']:.4f}  平均敞口={r['平均敞口']:.4f}")
    dfP1 = pd.DataFrame(rows1)
    dfP1.to_csv(os.path.join(OUT, 'P1_truncation_sim.csv'), index=False, encoding='utf-8-sig')

    print('\n=== 命题2: 时变过度减仓 corr(cut_V, cut_D) > 0 ===')
    rows2 = []
    for ss in [0.03, 0.055, 0.09, 0.12, 0.16]:
        ann, dg = simulate(rng, ss, True, 1.0)
        rows2.append({'σ*': ss, 'corr(cut_V,cut_D)': round(dg['corr(cut_V,cut_D)'], 3),
                      '双重减仓占比': round(dg['双重减仓占比'], 3),
                      '平均敞口': round(dg['平均敞口'], 4),
                      'E[φ]': round(dg['E[φ]'], 4)})
        r = rows2[-1]
        print(f"  σ*={ss:.3f}: corr(cut_V,cut_D)={r['corr(cut_V,cut_D)']:+.3f}  "
              f"双重减仓占比={r['双重减仓占比']:.3f}  平均敞口={r['平均敞口']:.4f}  E[φ]={r['E[φ]']:.4f}")
    dfP2 = pd.DataFrame(rows2)
    dfP2.to_csv(os.path.join(OUT, 'P2_interaction_sim.csv'), index=False, encoding='utf-8-sig')

    print('\n=== 命题4: 比较静态 —— 波动率聚集强度 → 双重减仓频率 ===')
    rows3 = []
    for persist in [(1/120., 1/60.), (1/65., 1/28.), (1/35., 1/15.)]:
        P_LH, P_HL = persist
        ann, dg = simulate(rng, 0.09, True, 1.0)
        rows3.append({'低波持续期(日)': round(1/persist[0]), '高波持续期(日)': round(1/persist[1]),
                      'corr(cut_V,cut_D)': round(dg['corr(cut_V,cut_D)'], 3),
                      '双重减仓占比': round(dg['双重减仓占比'], 3),
                      '平均敞口': round(dg['平均敞口'], 4)})
        r = rows3[-1]
        print(f"  低波{r['低波持续期(日)']}日/高波{r['高波持续期(日)']}日: "
              f"corr={r['corr(cut_V,cut_D)']:+.3f}  双重减仓占比={r['双重减仓占比']:.3f}")
    dfP4 = pd.DataFrame(rows3)
    dfP4.to_csv(os.path.join(OUT, 'P4_comparative_static.csv'), index=False, encoding='utf-8-sig')

    print('\n=== 命题5: 杠杆能否化解? 敞口实现率 ===')
    rows5 = []
    for ebar in [1.0, 2.0]:
        for dc in [False, True]:
            for ss in [0.055, 0.09, 0.12, 0.16]:
                ann, dg = simulate(rng, ss, dc, ebar)
                rows5.append({'Ē': ebar, 'DC': dc, 'σ*': ss,
                              '平均敞口': round(dg['平均敞口'], 4),
                              '年化%': round(float(np.nanmean(ann) * 100), 2),
                              '最大回撤%': round(dg['最大回撤%'], 2)})
    dfP5 = pd.DataFrame(rows5)
    print(dfP5.to_string(index=False))
    dfP5.to_csv(os.path.join(OUT, 'P5_leverage_sim.csv'), index=False, encoding='utf-8-sig')
    print('\n模拟完成 ->', OUT)
