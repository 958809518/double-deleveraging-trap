# -*- coding: utf-8 -*-
"""生成论文配图(纯 SVG, 离线可嵌)。排布原则: 标注一律避开曲线, 注释放到绘图区下方。"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'paper_data')
os.makedirs(OUT, exist_ok=True)

TVS = [0.03, 0.035, 0.04, 0.045, 0.05, 0.055, 0.06, 0.065, 0.07, 0.08, 0.09, 0.10,
       0.12, 0.15]

E1_N = ([5.48, 5.87, 6.27, 6.66, 7.05, 7.44, 7.83, 8.23, 8.61, 9.24, 9.80, 10.34,
         11.28, 11.79],
        [4.14, 4.63, 5.35, 6.08, 6.80, 7.52, 8.27, 9.02, 9.76, 11.23, 12.72, 14.48,
         17.96, 21.90])
E1_D = ([5.09, 5.27, 5.35, 5.62, 5.91, 6.47, 6.35, 6.24, 6.45, 6.78, 6.23, 7.28,
         5.37, 5.06],
        [4.21, 4.14, 4.08, 4.02, 4.25, 4.15, 4.54, 4.25, 4.60, 5.32, 5.89, 5.54,
         6.06, 6.28])
E2_N = ([5.48, 5.87, 6.27, 6.66, 7.05, 7.44, 7.83, 8.22, 8.61, 9.38, 10.14, 10.89,
         12.46, 14.69],
        [4.14, 4.63, 5.35, 6.08, 6.80, 7.52, 8.27, 9.02, 9.76, 11.23, 12.72, 14.48,
         17.96, 23.04])
E2_D = ([5.09, 5.27, 5.35, 5.62, 5.91, 6.47, 6.35, 6.22, 6.45, 7.19, 6.32, 6.98,
         6.34, 7.73],
        [4.21, 4.14, 4.08, 4.02, 4.25, 4.15, 4.54, 4.25, 4.60, 5.32, 5.89, 5.37,
         6.32, 6.93])

P1_N = ([5.28, 5.64, 6.00, 6.36, 6.72, 7.07, 7.42, 7.76, 8.11, 8.79, 9.40, 10.03,
         10.95, 11.96],
        [4.45, 5.27, 6.10, 7.10, 8.25, 9.38, 10.50, 11.41, 12.08, 13.22, 14.49,
         16.03, 17.67, 18.12])
P1_D = ([4.89, 5.21, 5.65, 6.10, 6.32, 6.32, 6.49, 6.49, 6.03, 6.87, 5.89, 6.13,
         5.92, 5.75],
        [4.18, 4.10, 4.04, 3.92, 3.94, 4.27, 4.55, 4.60, 4.85, 5.71, 6.58, 5.93,
         6.92, 6.92])
P2_N = ([5.28, 5.64, 6.00, 6.36, 6.72, 7.07, 7.42, 7.77, 8.12, 8.81, 9.49, 10.20,
         11.65, 13.77],
        [4.45, 5.27, 6.10, 7.10, 8.25, 9.38, 10.50, 11.59, 12.65, 14.71, 16.67,
         18.59, 22.37, 26.24])
P2_D = ([4.89, 5.21, 5.65, 6.10, 6.32, 6.32, 6.49, 6.53, 6.06, 7.05, 5.85, 5.69,
         6.55, 7.76],
        [4.18, 4.10, 4.04, 3.92, 3.94, 4.27, 4.55, 4.60, 4.85, 5.71, 6.58, 5.72,
         7.03, 6.30])

C = {'e1n': '#1a4d7c', 'e1d': '#c0392b', 'e2n': '#8899a6', 'e2d': '#e08a00'}
FONT = 'Microsoft YaHei, "Heiti SC", sans-serif'


def sc(v, v0, v1, a, b):
    return a + (v - v0) / (v1 - v0) * (b - a)


def frame(x0, x1, y0, y1, ax, bx, ay, by, xt, yt, xlab, ylab, title):
    s = [f'<rect x="{ax}" y="{ay}" width="{bx-ax}" height="{by-ay}" fill="#fcfdfe" '
         f'stroke="#dde4ea"/>']
    for t in yt:
        yy = sc(t, y0, y1, by, ay)
        s.append(f'<line x1="{ax}" y1="{yy:.1f}" x2="{bx}" y2="{yy:.1f}" '
                 f'stroke="#eef2f6"/>')
        s.append(f'<text x="{ax-7}" y="{yy+4:.1f}" font-size="11" fill="#6b7785" '
                 f'text-anchor="end" font-family="{FONT}">{t:g}</text>')
    for t in xt:
        xx = sc(t, x0, x1, ax, bx)
        s.append(f'<line x1="{xx:.1f}" y1="{ay}" x2="{xx:.1f}" y2="{by}" '
                 f'stroke="#eef2f6"/>')
        s.append(f'<text x="{xx:.1f}" y="{by+16}" font-size="11" fill="#6b7785" '
                 f'text-anchor="middle" font-family="{FONT}">{t:g}</text>')
    s.append(f'<text x="{(ax+bx)/2}" y="{by+34}" font-size="12" fill="#4a5568" '
             f'text-anchor="middle" font-family="{FONT}">{xlab}</text>')
    s.append(f'<text x="{ax-36}" y="{(ay+by)/2}" font-size="12" fill="#4a5568" '
             f'text-anchor="middle" font-family="{FONT}" '
             f'transform="rotate(-90 {ax-36} {(ay+by)/2})">{ylab}</text>')
    s.append(f'<text x="{ax}" y="{ay-14}" font-size="13" font-weight="600" '
             f'fill="#24405c" font-family="{FONT}">{title}</text>')
    return ''.join(s)


def curve(xs, ys, x0, x1, y0, y1, ax, bx, ay, by, color, dash=False):
    pts = ' '.join(f'{sc(a,x0,x1,ax,bx):.1f},{sc(b,y0,y1,by,ay):.1f}'
                   for a, b in zip(xs, ys))
    d = ' stroke-dasharray="6 3"' if dash else ''
    s = [f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.1"'
         f'{d} stroke-linejoin="round"/>']
    for a, b in zip(xs, ys):
        s.append(f'<circle cx="{sc(a,x0,x1,ax,bx):.1f}" '
                 f'cy="{sc(b,y0,y1,by,ay):.1f}" r="2.6" fill="#fff" '
                 f'stroke="{color}" stroke-width="1.5"/>')
    return ''.join(s)


def legend(items, x, y, anchor='start'):
    s = []
    for i, (lab, col, dash) in enumerate(items):
        yy = y + i * 19
        d = ' stroke-dasharray="6 3"' if dash else ''
        s.append(f'<line x1="{x}" y1="{yy}" x2="{x+26}" y2="{yy}" stroke="{col}" '
                 f'stroke-width="2.4"{d}/>')
        s.append(f'<circle cx="{x+13}" cy="{yy}" r="2.6" fill="#fff" stroke="{col}" '
                 f'stroke-width="1.5"/>')
        s.append(f'<text x="{x+33}" y="{yy+4}" font-size="11.5" fill="#4a5568" '
                 f'font-family="{FONT}">{lab}</text>')
    return ''.join(s)


def note(x, y, txt, fill='#8a949e', size=11, anchor='start'):
    a = f' text-anchor="{anchor}"' if anchor != 'start' else ''
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}"{a} '
            f'font-family="{FONT}">{txt}</text>')


def wrap(title, inner, h):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 {h}" '
            f'width="100%" font-family="{FONT}">'
            f'<rect width="900" height="{h}" fill="#ffffff"/>'
            f'<text x="450" y="21" font-size="13.5" font-weight="700" '
            f'fill="#17324a" text-anchor="middle">{title}</text>'
            f'{inner}</svg>')


def fig1():
    s = []
    ax, bx, ay, by = 66, 430, 56, 352
    s.append(frame(3, 15.5, 4, 15, ax, bx, ay, by,
                   [3, 5, 7, 9, 11, 13, 15], [4, 6, 8, 10, 12, 14],
                   '目标波动 σ* (%)', '年化收益 (%)', 'A　收益—目标波动平面'))
    tvp = [t * 100 for t in TVS]
    for dat, k, dash in [(E1_N, 'e1n', False), (E1_D, 'e1d', False),
                         (E2_N, 'e2n', True), (E2_D, 'e2d', True)]:
        s.append(curve(tvp, dat[0], 3, 15.5, 4, 15, ax, bx, ay, by, C[k], dash))
    px = sc(5.5, 3, 15.5, ax, bx)
    py = sc(6.47, 4, 15, by, ay)
    s.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="none" '
             f'stroke="#c0392b" stroke-width="2.2"/>')
    s.append(note(px + 10, py - 11, '峰值', '#c0392b', 11.5))
    s.append(legend([('Ē=1 无回撤控制（零售）', C['e1n'], False),
                     ('Ē=1 有回撤控制（零售）', C['e1d'], False),
                     ('Ē=2 无回撤控制（机构）', C['e2n'], True),
                     ('Ē=2 有回撤控制（机构）', C['e2d'], True)], ax + 6, ay + 14))

    ax2, bx2 = 505, 872
    s.append(frame(3.5, 23.5, 4, 15, ax2, bx2, ay, by,
                   [4, 8, 12, 16, 20], [4, 6, 8, 10, 12, 14],
                   '最大回撤绝对值 (%)', '年化收益 (%)', 'B　收益—回撤平面（有效前沿）'))
    for dat, k, dash in [(E1_N, 'e1n', False), (E1_D, 'e1d', False),
                         (E2_N, 'e2n', True), (E2_D, 'e2d', True)]:
        s.append(curve(dat[1], dat[0], 3.5, 23.5, 4, 15, ax2, bx2, ay, by,
                       C[k], dash))
    s.append(note(bx2, ay + 20, '高 σ* 段向左下折返（被支配）', '#c0392b', 11, 'end'))
    return wrap('图1　两种约束集下的有效前沿（红圈：单峰顶点）', ''.join(s), 410)


def fig2():
    s = []
    ax, bx, ay, by = 66, 430, 56, 322
    g = [0.5, 1, 2, 4, 8]
    no_dc = [2.688, 2.475, 2.051, 1.048, 0.071]
    has_dc = [0.406, 0.363, 0.275, 0.100, 0.068]
    s.append(frame(0, 8.6, 0, 3.0, ax, bx, ay, by,
                   [0.5, 1, 2, 4, 8], [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
                   '风险厌恶系数 γ', '约束成本（年化收益当量，pp）',
                   'A　杠杆约束的成本随 γ 递减，且被回撤控制大幅压缩'))
    s.append(curve(g, no_dc, 0, 8.6, 0, 3.0, ax, bx, ay, by, C['e1n']))
    s.append(curve(g, has_dc, 0, 8.6, 0, 3.0, ax, bx, ay, by, C['e1d']))
    for a, b in zip(g, no_dc):
        s.append(note(sc(a, 0, 8.6, ax, bx), sc(b, 0, 3.0, by, ay) - 10,
                      f'{b:.2f}', C['e1n'], 10.5, 'middle'))
    for a, b in zip(g, has_dc):
        s.append(note(sc(a, 0, 8.6, ax, bx), sc(b, 0, 3.0, by, ay) + 17,
                      f'{b:.2f}', C['e1d'], 10.5, 'middle'))
    s.append(legend([('无回撤控制', C['e1n'], False),
                     ('有回撤控制', C['e1d'], False)], ax + 240, ay + 14))
    s.append(note(ax, by + 54, 'γ=1 时：无回撤控制 2.48pp　→　有回撤控制 0.36pp（降幅 85%）'))

    ax2, bx2 = 505, 872
    tg = [5, 6, 7, 8, 9, 10]
    r1 = [4.02, 4.15, 5.54, 9.02, 11.23, 14.48]
    r2 = [4.02, 4.15, 5.32, 9.02, 11.23, 12.72]
    s.append(frame(4.4, 10.4, 0, 15.5, ax2, bx2, ay, by,
                   [5, 6, 7, 8, 9, 10], [0, 3, 6, 9, 12, 15],
                   '收益目标 (%)', '所需承担的最小回撤 (%)',
                   'B　给定收益目标所需承担的最小回撤'))
    s.append(curve(tg, r1, 4.4, 10.4, 0, 15.5, ax2, bx2, ay, by, C['e1d']))
    s.append(curve(tg, r2, 4.4, 10.4, 0, 15.5, ax2, bx2, ay, by, C['e2d'], True))
    s.append(legend([('Ē=1（零售）', C['e1d'], False),
                     ('Ē=2（机构）', C['e2d'], True)], ax2 + 8, ay + 14))
    s.append(note(ax2, by + 54, '收益目标 ≤6% 时两条线完全重合：低收益目标下杠杆无价值'))
    return wrap('图2　约束成本的量化：回撤控制“消灭”了杠杆的价值', ''.join(s), 400)


def fig3():
    s = []
    ax, bx, ay, by = 66, 500, 56, 342
    tvp = [t * 100 for t in TVS]
    s.append(frame(3, 15.5, 4, 15, ax, bx, ay, by,
                   [3, 5, 7, 9, 11, 13, 15], [4, 6, 8, 10, 12, 14],
                   '目标波动 σ* (%)', '年化收益 (%)',
                   '纯风险 overlay（无趋势、无价格分位、无宏观信号）'))
    for dat, k, dash in [(P1_N, 'e1n', False), (P1_D, 'e1d', False),
                         (P2_D, 'e2d', True)]:
        s.append(curve(tvp, dat[0], 3, 15.5, 4, 15, ax, bx, ay, by, C[k], dash))
    px = sc(8, 3, 15.5, ax, bx)
    py = sc(6.87, 4, 15, by, ay)
    s.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="none" '
             f'stroke="#c0392b" stroke-width="2.2"/>')
    s.append(note(px + 10, py - 14, '峰值 σ*=8%', '#c0392b', 11.5))
    s.append(legend([('Ē=1 无回撤控制', C['e1n'], False),
                     ('Ē=1 有回撤控制', C['e1d'], False),
                     ('Ē=2 有回撤控制', C['e2d'], True)], ax + 6, ay + 14))
    s.append(note(ax, by + 54,
                  '高 σ* 区（≥10%）年均收益：无回撤控制 10.98%　→　有回撤控制 5.93%'
                  '（−5.05pp）'))
    s.append(note(ax, by + 70,
                  '低 σ* 区（≤5.5%）年均收益：无回撤控制 6.18%　→　有回撤控制 5.75%'
                  '（−0.43pp）'))
    return wrap('图3　关闭全部战术信号后，前沿分岔依然存在（红圈：单峰顶点）',
                ''.join(s), 440)


def bars(xs, ys, x0, x1, y0, y1, ax, bx, ay, by, color, lab=True):
    s = []
    n = len(xs)
    step = (bx - ax) / n
    w = step * 0.42
    y0p = sc(y0, y0, y1, by, ay)
    for x, y in zip(xs, ys):
        cx = sc(x, x0, x1, ax, bx)
        yp = sc(y, y0, y1, by, ay)
        s.append(f'<rect x="{cx - w/2:.1f}" y="{yp:.1f}" width="{w:.1f}" '
                 f'height="{y0p - yp:.1f}" fill="{color}" opacity="0.88"/>')
        if lab:
            s.append(note(cx, yp - 8, f'{y:.2f}', color, 10.5, 'middle'))
    return ''.join(s)


def fig4():
    s = []
    ax, bx, ay, by = 66, 430, 56, 342
    Es = [0.25, 0.44, 0.70, 0.85, 1.00]
    cost = [0.56, 1.10, 3.58, 5.14, 7.37]
    s.append(frame(0.15, 1.10, 0, 8, ax, bx, ay, by,
                   [0.25, 0.44, 0.70, 0.85, 1.00], [0, 2, 4, 6, 8],
                   '固定敞口 E（波动率目标层已关闭）',
                   '回撤控制的年化成本 (pp)',
                   'A　回撤控制的成本随可削减敞口单调放大'))
    s.append(bars(Es, cost, 0.15, 1.10, 0, 8, ax, bx, ay, by, C['e1d']))
    s.append(note(ax, by + 54,
                  'E=1.00（满仓）时成本 7.37pp，且夏普由 0.80 降至 0.69：'
                  '无处可退时的削减不再“划算”'))

    ax2, bx2 = 505, 872
    tvp = [3.0, 4.5, 5.5, 7.0, 9.0, 12.0]
    series = [([5.09, 5.62, 6.47, 6.45, 6.23, 5.37], C['e1d'], False, '基准'),
              ([4.78, 5.00, 4.88, 5.17, 6.37, 6.04], '#e08a00', False, '严格'),
              ([5.30, 6.22, 6.74, 7.14, 7.72, 7.86], C['e1n'], True, '宽松'),
              ([5.39, 6.43, 7.01, 7.95, 8.66, 9.13], '#8899a6', True, '极宽')]
    s.append(frame(2.6, 12.6, 4, 10, ax2, bx2, ay, by,
                   [3, 5, 7, 9, 11], [4, 5, 6, 7, 8, 9, 10],
                   '目标波动 σ* (%)', '年化收益 (%)',
                   'B　阈值放宽后前沿恢复单调：内点最优是条件性的'))
    for dat, k, dash, _ in series:
        s.append(curve(tvp, dat, 2.6, 12.6, 4, 10, ax2, bx2, ay, by, k, dash))
    s.append(legend([(lab, k, d) for _, k, d, lab in series], ax2 + 6, ay + 14))
    s.append(note(ax2, by + 54,
                  '仅“基准”与“严格”两组出现内点最优；阈值放宽至 −2%/−4%/−6% '
                  '及以上时前沿单调递增'))
    return wrap('图4　回撤控制成本的分离与条件性（A：表10；B：表19）', ''.join(s), 430)


for name, fn in [('fig1_frontier', fig1), ('fig2_constraint_cost', fig2),
                 ('fig3_nosignal', fig3), ('fig4_boundary', fig4)]:
    p = os.path.join(OUT, name + '.svg')
    open(p, 'w', encoding='utf-8').write(fn())
    print('生成', p)
