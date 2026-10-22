# -*- coding: utf-8 -*-
"""投稿用图: matplotlib 重绘三张图, 输出 300dpi PNG (A4 版心宽 15cm)"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'paper_data')

for f in ['Microsoft YaHei', 'SimHei', 'SimSun']:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        CJK = f
        break
    except Exception:
        continue
else:
    CJK = 'DejaVu Sans'
print('中文字体:', CJK)
plt.rcParams['font.sans-serif'] = [CJK]
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.family'] = 'sans-serif'

TVS = [3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 8, 9, 10, 12, 15]

E1_N = ([5.48, 5.87, 6.27, 6.66, 7.05, 7.44, 7.83, 8.23, 8.61, 9.24, 9.80, 10.34,
         11.28, 11.79],
        [-4.14, -4.63, -5.35, -6.08, -6.80, -7.52, -8.27, -9.02, -9.76, -11.23,
         -12.72, -14.48, -17.96, -21.90])
E1_D = ([5.09, 5.27, 5.35, 5.62, 5.91, 6.47, 6.35, 6.24, 6.45, 6.78, 6.23, 7.28,
         5.37, 5.06],
        [-4.21, -4.14, -4.08, -4.02, -4.25, -4.15, -4.54, -4.25, -4.60, -5.32,
         -5.89, -5.54, -6.06, -6.28])
E2_N = ([5.48, 5.87, 6.27, 6.66, 7.05, 7.44, 7.83, 8.22, 8.61, 9.38, 10.14, 10.89,
         12.46, 14.69],
        [-4.14, -4.63, -5.35, -6.08, -6.80, -7.52, -8.27, -9.02, -9.76, -11.23,
         -12.72, -14.48, -17.96, -23.04])
E2_D = ([5.09, 5.27, 5.35, 5.62, 5.91, 6.47, 6.35, 6.22, 6.45, 7.19, 6.32, 6.98,
         6.34, 7.73],
        [-4.21, -4.14, -4.08, -4.02, -4.25, -4.15, -4.54, -4.25, -4.60, -5.32,
         -5.89, -5.37, -6.32, -6.93])

P1_N = ([5.28, 5.64, 6.00, 6.36, 6.72, 7.07, 7.42, 7.76, 8.11, 8.79, 9.40, 10.03,
         10.95, 11.96],
        [-4.45, -5.27, -6.10, -7.10, -8.25, -9.38, -10.50, -11.41, -12.08, -13.22,
         -14.49, -16.03, -17.67, -18.12])
P1_D = ([4.89, 5.21, 5.65, 6.10, 6.32, 6.32, 6.49, 6.49, 6.03, 6.87, 5.89, 6.13,
         5.92, 5.75],
        [-4.18, -4.10, -4.04, -3.92, -3.94, -4.27, -4.55, -4.60, -4.85, -5.71,
         -6.58, -5.93, -6.92, -6.92])
P2_D = ([4.89, 5.21, 5.65, 6.10, 6.32, 6.32, 6.49, 6.53, 6.06, 7.05, 5.85, 5.69,
         6.55, 7.76],
        [-4.18, -4.10, -4.04, -3.92, -3.94, -4.27, -4.55, -4.60, -4.85, -5.71,
         -6.58, -5.72, -7.03, -6.30])

C1, C2, C3, C4 = '#1a4d7c', '#c0392b', '#8899a6', '#e08a00'
CM = 1 / 2.54


def style(ax, xlab, ylab):
    ax.set_xlabel(xlab, fontsize=9)
    ax.set_ylabel(ylab, fontsize=9)
    ax.tick_params(labelsize=8, direction='in')
    ax.grid(True, color='#eef2f6', lw=0.6)
    ax.set_axisbelow(True)
    for s in ['top', 'right']:
        ax.spines[s].set_visible(False)
    for s in ['left', 'bottom']:
        ax.spines[s].set_color('#8899a6')
        ax.spines[s].set_linewidth(0.8)


def fig1():
    fig, (a, b) = plt.subplots(1, 2, figsize=(15 * CM, 6.0 * CM))
    for dat, c, d, lab in [(E1_N, C1, '-', 'Ē=1 无回撤控制'),
                           (E1_D, C2, '-', 'Ē=1 有回撤控制'),
                           (E2_N, C3, '--', 'Ē=2 无回撤控制'),
                           (E2_D, C4, '--', 'Ē=2 有回撤控制')]:
        a.plot(TVS, dat[0], d, color=c, lw=1.4, ms=3.4, marker='o', mfc='white',
               label=lab)
    a.plot([5.5], [6.47], 'o', mfc='none', mec=C2, mew=1.6, ms=9)
    a.annotate('峰值 σ*=5.5%', xy=(5.5, 6.47), xytext=(7.0, 4.55), fontsize=8,
               color=C2, arrowprops=dict(arrowstyle='->', color=C2, lw=0.8))
    a.set_xlim(2.5, 15.8)
    a.set_ylim(4, 15.2)
    style(a, '目标波动 σ* (%)', '年化收益 (%)')
    a.set_title('A  收益—目标波动平面', fontsize=9.5, loc='left', pad=5)
    a.legend(fontsize=7.4, frameon=False, loc='lower right')

    for dat, c, d in [(E1_N, C1, '-'), (E1_D, C2, '-'), (E2_N, C3, '--'),
                      (E2_D, C4, '--')]:
        b.plot([abs(v) for v in dat[1]], dat[0], d, color=c, lw=1.4, ms=3.4,
               marker='o', mfc='white')
    b.set_xlim(3.2, 23.8)
    b.set_ylim(4, 15.2)
    style(b, '最大回撤绝对值 (%)', '年化收益 (%)')
    b.set_title('B  收益—回撤平面（有效前沿）', fontsize=9.5, loc='left', pad=5)
    b.annotate('高 σ* 段向左下折返（被支配）', xy=(6.06, 5.37),
               xytext=(9.0, 8.6), fontsize=8, color=C2,
               arrowprops=dict(arrowstyle='->', color=C2, lw=0.8))
    fig.tight_layout()
    return fig


def fig2():
    fig, (a, b) = plt.subplots(1, 2, figsize=(15 * CM, 5.6 * CM))
    g = [0.5, 1, 2, 4, 8]
    a.plot(g, [2.688, 2.475, 2.051, 1.048, 0.071], '-o', color=C1, lw=1.4, ms=3.6,
           mfc='white', label='无回撤控制')
    a.plot(g, [0.406, 0.363, 0.275, 0.100, 0.068], '-s', color=C2, lw=1.4, ms=3.6,
           mfc='white', label='有回撤控制')
    for x, y in zip(g, [2.688, 2.475, 2.051, 1.048, 0.071]):
        a.annotate(f'{y:.2f}', (x, y), textcoords='offset points', xytext=(0, 6),
                   fontsize=7.4, color=C1, ha='center')
    for x, y in zip(g, [0.406, 0.363, 0.275, 0.100, 0.068]):
        a.annotate(f'{y:.2f}', (x, y), textcoords='offset points', xytext=(0, -13),
                   fontsize=7.4, color=C2, ha='center')
    a.set_ylim(-0.15, 3.15)
    style(a, '风险厌恶系数 γ', '约束成本（年化收益当量，pp）')
    a.set_title('A  杠杆约束成本随 γ 递减，且被回撤控制压缩', fontsize=9.5,
                loc='left', pad=5)
    a.legend(fontsize=7.8, frameon=False, loc='upper right')

    tg = [5, 6, 7, 8, 9, 10]
    b.plot(tg, [4.02, 4.15, 5.54, 9.02, 11.23, 14.48], '-o', color=C2, lw=1.4,
           ms=3.6, mfc='white', label='Ē=1（零售）')
    b.plot(tg, [4.02, 4.15, 5.32, 9.02, 11.23, 12.72], '--s', color=C4, lw=1.4,
           ms=3.6, mfc='white', label='Ē=2（机构）')
    b.set_ylim(0, 15.5)
    style(b, '收益目标 (%)', '所需承担的最小回撤 (%)')
    b.set_title('B  给定收益目标所需承担的最小回撤', fontsize=9.5, loc='left', pad=5)
    b.legend(fontsize=7.8, frameon=False, loc='upper left')
    fig.tight_layout()
    return fig


def fig3():
    fig, a = plt.subplots(1, 1, figsize=(11 * CM, 6.4 * CM))
    for dat, c, d, lab in [(P1_N, C1, '-', 'Ē=1 无回撤控制'),
                           (P1_D, C2, '-', 'Ē=1 有回撤控制'),
                           (P2_D, C4, '--', 'Ē=2 有回撤控制')]:
        a.plot(TVS, dat[0], d, color=c, lw=1.4, ms=3.4, marker='o', mfc='white',
               label=lab)
    a.plot([8], [6.87], 'o', mfc='none', mec=C2, mew=1.6, ms=9)
    a.annotate('峰值 σ*=8%，末端衰减 1.12pp', xy=(8, 6.87), xytext=(9.6, 8.4),
               fontsize=8, color=C2,
               arrowprops=dict(arrowstyle='->', color=C2, lw=0.8))
    a.set_xlim(2.5, 15.8)
    a.set_ylim(4, 13.2)
    style(a, '目标波动 σ* (%)', '年化收益 (%)')
    a.legend(fontsize=8, frameon=False, loc='upper left')
    fig.tight_layout()
    return fig


def fig4():
    fig, (a, b) = plt.subplots(1, 2, figsize=(15 * CM, 5.6 * CM))
    Es = [0.25, 0.44, 0.70, 0.85, 1.00]
    cost = [0.56, 1.10, 3.58, 5.14, 7.37]
    a.bar([str(e) for e in Es], cost, width=0.5, color=C2, alpha=0.88)
    for x, y in zip(range(5), cost):
        a.annotate(f'{y:.2f}', (x, y), textcoords='offset points', xytext=(0, 4),
                   fontsize=7.8, color=C2, ha='center')
    a.set_ylim(0, 8.4)
    style(a, '固定敞口 E（波动率目标层已关闭）', '回撤控制的年化成本 (pp)')
    a.set_title('A  成本随可削减敞口单调放大', fontsize=9.5, loc='left', pad=5)

    tvp = [3.0, 4.5, 5.5, 7.0, 9.0, 12.0]
    for dat, c, d, lab in [([5.09, 5.62, 6.47, 6.45, 6.23, 5.37], C2, '-', '基准'),
                           ([4.78, 5.00, 4.88, 5.17, 6.37, 6.04], C4, '-', '严格'),
                           ([5.30, 6.22, 6.74, 7.14, 7.72, 7.86], C1, '--', '宽松'),
                           ([5.39, 6.43, 7.01, 7.95, 8.66, 9.13], C3, '--', '极宽')]:
        b.plot(tvp, dat, d, color=c, lw=1.4, ms=3.4, marker='o', mfc='white',
               label=lab)
    b.set_xlim(2.5, 12.6)
    b.set_ylim(4, 10)
    style(b, '目标波动 σ* (%)', '年化收益 (%)')
    b.set_title('B  阈值放宽后前沿恢复单调', fontsize=9.5, loc='left', pad=5)
    b.legend(fontsize=7.6, frameon=False, loc='upper left')
    fig.tight_layout()
    return fig


for name, fn in [('docx_fig1', fig1), ('docx_fig2', fig2), ('docx_fig3', fig3),
                 ('docx_fig4', fig4)]:
    p = os.path.join(OUT, name + '.png')
    fn().savefig(p, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close('all')
    print('生成', p)
