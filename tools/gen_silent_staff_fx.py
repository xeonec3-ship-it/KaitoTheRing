#!/usr/bin/env python3
"""
Эффекты четырёх заклинаний посоха безмолвной ведьмы (T20): модели и эффекты под то, что передаёт код (docs/specs/tasks/T20_silent_staff_spells.md,
раздел «Как сделано в коде»). Стиль `silent`.

Модели (fx/meshes, часть `boxes` — docs/fx.md):
  silent_spear   — прозрачное копьё ветра: вытянутый ромб вдоль +z, светлые грани, светящийся стержень, три кольца-завихрения
  silent_dome    — купол Барьера: шестиугольные ячейки на сфере радиуса 1 (масштаб эффекта = радиус), собирается снизу вверх
  worgan_dragon  — тень чёрного дракона: голова с рогами и шея, тёмная полупрозрачная, фиолетовая кромка и глаза; смотрит в +z
Эффекты (fx):
  silent_wind_spears      — на одно копьё: модель копья и шлейф ветра; сервер двигает экземпляр (Fx.move) и гасит при попадании
  silent_wind_spears_hit  — попадание копья: кольцо ветра, вспышка, искры (играет код в точке попадания)
  silent_volley           — 24 печати веером за спиной (как SilentVolleySpell.seal: дуга 200°, r 2.5, ряды 1.15 / 2.15), собираются по одной
  silent_volley_arrow     — одна стрела залпа: яркое ядро и шлейф; сервер двигает экземпляр, как копьё
  silent_barrier_dome     — купол: модель silent_dome, сфера-свечение, кольцо на земле, искры по поверхности
  silent_worgan_flame     — тень дракона над правым плечом встаёт за каст, выдох чёрного пламени конусом, пепел, тень рассыпается
Запуск: python3 tools/gen_silent_staff_fx.py
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
R3 = lambda v: round(v, 3)


class Boxes:
    def __init__(self):
        self.b = []

    def box(self, x0, y0, z0, x1, y1, z1, t=1, rot=None):
        e = [R3(min(x0, x1)), R3(min(y0, y1)), R3(min(z0, z1)), R3(max(x0, x1)), R3(max(y0, y1)), R3(max(z0, z1)), t]
        if rot and any(abs(a) > 1e-6 for a in rot):
            e.append([R3(a) for a in rot])
        self.b.append(e)

    def cbox(self, cx, cy, cz, sx, sy, sz, t=1, rot=None):
        self.box(cx - sx / 2, cy - sy / 2, cz - sz / 2, cx + sx / 2, cy + sy / 2, cz + sz / 2, t, rot)

    def seg3(self, p, q, w, t=1):
        """Брусок-отрезок между двумя точками в пространстве (поворот: yaw вокруг y, затем pitch)."""
        dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
        ln = math.sqrt(dx * dx + dy * dy + dz * dz)
        yaw = math.degrees(math.atan2(dx, dz))
        pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
        self.cbox((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2, w, w, ln + w * 0.5, t, [pitch, yaw, 0])

    def bounds(self):
        ys = [e[1] for e in self.b] + [e[4] for e in self.b]
        return [min(ys), max(ys)]


def mesh_doc(comment, style, B, tones, glow, opacity, appear, formed, collapse=12, blend='translucent'):
    return {'comment': comment, 'style': style, 'center': 0, 'formedAt': formed,
            'collapse': {'duration': collapse, 'easing': 'easeInCubic'},
            'parts': [{'type': 'boxes', 'tones': tones, 'glowTones': glow, 'blend': blend, 'opacity': opacity, 'shade': True,
                       'boxes': B.b, 'appear': appear, 'bounds': B.bounds()}]}


def ring3(B, c, r, axis, w, t, n=24, phase=0.0, arc=360.0, wob=0.0):
    """Кольцо/дуга из отрезков вокруг оси z (axis='z'), y или x — для лент, колец и кромок."""
    pts = []
    for i in range(n + 1):
        a = math.radians(phase + arc * i / n)
        rr = r * (1 + wob * math.sin(3 * a))
        if axis == 'z':
            pts.append((c[0] + rr * math.cos(a), c[1] + rr * math.sin(a), c[2]))
        elif axis == 'y':
            pts.append((c[0] + rr * math.cos(a), c[1], c[2] + rr * math.sin(a)))
        else:
            pts.append((c[0], c[1] + rr * math.cos(a), c[2] + rr * math.sin(a)))
    for p, q in zip(pts, pts[1:]):
        B.seg3(p, q, w, t)


def spear():
    """Копьё ветра: гранёный кристалл-ромб вдоль +z (остриё впереди), полупрозрачные грани светлого льда-ветра, светящийся сердечник,
    блик на острие, вокруг — две ленты ветра спиралью и развевающиеся хвосты сзади."""
    B = Boxes()
    L, W = 3.0, 0.36
    nose, tail = 1.9, -1.1                                       # остриё и хвост по z
    N = 16
    for k in range(N):                                           # ромб: 4 грани в каждом сечении, сужение к остриё/хвосту
        z0 = tail + (nose - tail) * k / N
        z1 = tail + (nose - tail) * (k + 1) / N
        zc = (z0 + z1) / 2
        f = (zc - tail) / (0.0 - tail) if zc < 0 else 1 - zc / nose
        f = max(0.06, f) ** 0.8
        w = W * f
        for i in range(4):                                       # 4 грани ромба как наклонные плитки
            ang = 45 + 90 * i
            cx, cy = 0.5 * w * math.cos(math.radians(ang)), 0.5 * w * math.sin(math.radians(ang)) * 0.75
            B.cbox(cx, cy, zc, w * 0.72, 0.035, z1 - z0 + 0.02, 2 if i < 2 else 1, [0, 0, ang + 90])
        B.cbox(0, 0, zc, w * 0.5, w * 0.35, z1 - z0, 0)            # тёмная сердцевина — глубина кристалла
    B.cbox(0, 0, 0.35, 0.05, 0.05, nose - tail - 0.5, 4)          # светящийся сердечник
    B.cbox(0, 0.03, nose - 0.25, 0.04, 0.04, 0.45, 3)              # блик на острие
    for s_ in (-1, 1):                                             # гарда-крылышки у основания
        B.seg3((0, 0, -0.2), (s_ * 0.55, 0.05, -0.55), 0.06, 3)
        B.seg3((s_ * 0.55, 0.05, -0.55), (s_ * 0.7, 0.12, -0.9), 0.04, 3)
    for strand, ph in ((0, 0.0), (1, 180.0)):                      # две ленты ветра спиралью вокруг копья
        pts = []
        for i in range(48):
            u = i / 47
            z = tail - 0.4 + (nose - tail + 0.2) * u
            r = 0.42 * (1 - 0.55 * u) + 0.06
            a = math.radians(ph + 540 * u)
            pts.append((r * math.cos(a), r * math.sin(a), z))
        for p, q in zip(pts, pts[1:]):
            B.seg3(p, q, 0.022 if strand == 0 else 0.016, 4 if strand == 0 else 3)
    for i, (dx, dy) in enumerate(((0.18, 0.1), (-0.15, 0.14), (0.05, -0.18))):   # хвосты-ленты сзади, волной
        pts = [(dx * (1 + 0.6 * j / 8) + 0.08 * math.sin(j * 0.9 + i), dy * (1 + 0.6 * j / 8) + 0.06 * math.cos(j + i), tail - 0.1 - j * 0.16) for j in range(9)]
        for p, q in zip(pts, pts[1:]):
            B.seg3(p, q, 0.018 - 0.002 * i, 4)
    return mesh_doc('Копьё ветра (T20): гранёный кристалл, сердечник, ленты ветра спиралью, хвосты. Сгенерировано tools/gen_silent_staff_fx.py.', 'silent', B,
                    ['#3E5568', '#9CCFE2', '#D4F1FA', '#FFFFFF', '@primary'], [3, 4], 0.6,
                    {'delay': 0, 'duration': 6, 'easing': 'easeOutCubic', 'reveal': 'down', 'front': 0.6}, 6, collapse=4)


def dome():
    """Купол Барьера: шестиугольная сетка на сфере r=1 (двойственная к подразделённому икосаэдру) — светящиеся рёбра, узлы-огоньки,
    полупрозрачные грани-ячейки (тонкие пластины в центре каждой ячейки), у земли — двойное кольцо с рунами-насечками."""
    t = (1 + 5 ** 0.5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    nrm = lambda p: tuple(c / math.sqrt(sum(x * x for x in p)) for c in p)
    n = 4
    tris = []
    for a, b, c in F:
        A_, B_, C_ = V[a], V[b], V[c]
        pts = {}
        for i in range(n + 1):
            for j in range(n + 1 - i):
                k = n - i - j
                pts[(i, j)] = nrm(tuple((A_[m] * i + B_[m] * j + C_[m] * k) / n for m in range(3)))
        for i in range(n):
            for j in range(n - i):
                tris.append((pts[(i, j)], pts[(i + 1, j)], pts[(i, j + 1)]))
                if i + j < n - 1:
                    tris.append((pts[(i + 1, j)], pts[(i + 1, j + 1)], pts[(i, j + 1)]))
    cent = [nrm(tuple(sum(p[m] for p in tr) / 3 for m in range(3))) for tr in tris]
    key = lambda p: tuple(round(c, 4) for c in p)
    edges, verts = {}, {}
    for ti, tr in enumerate(tris):
        for u in range(3):
            e = tuple(sorted((key(tr[u]), key(tr[(u + 1) % 3]))))
            edges.setdefault(e, []).append(ti)
            verts.setdefault(key(tr[u]), tr[u])
    B = Boxes()
    keep = lambda p: p[1] > -0.12
    nodes = set()
    for e, ts in edges.items():
        if len(ts) != 2:
            continue
        p, q = cent[ts[0]], cent[ts[1]]
        if not (keep(p) or keep(q)):
            continue
        B.seg3(p, q, 0.016, 3)
        nodes.add(key(p)); nodes.add(key(q))
    for k in nodes:                                                  # узлы-огоньки на стыках ячеек
        B.cbox(k[0], k[1], k[2], 0.035, 0.035, 0.035, 4)
    for k, v in verts.items():                                       # грани-ячейки: тонкая пластина по касательной в центре ячейки
        if v[1] < -0.05:
            continue
        yaw = math.degrees(math.atan2(v[0], v[2]))
        pitch = -math.degrees(math.atan2(v[1], math.hypot(v[0], v[2])))
        B.cbox(v[0] * 0.995, v[1] * 0.995, v[2] * 0.995, 0.17, 0.17, 0.004, 2 if v[1] > 0.5 else 1, [pitch, yaw, 0])
    ring3(B, (0, -0.08, 0), 1.02, 'y', 0.04, 4, n=72)                 # двойное кольцо у земли с насечками-рунами
    ring3(B, (0, -0.08, 0), 1.14, 'y', 0.025, 3, n=72)
    for i in range(36):
        a = 2 * math.pi * i / 36
        h = 0.05 if i % 3 else 0.09
        B.seg3((1.05 * math.cos(a), -0.08, 1.05 * math.sin(a)), (1.11 * math.cos(a), -0.08 + h * 0.2, 1.11 * math.sin(a)), 0.014, 4)
    return mesh_doc('Купол Барьера (T20): шестиугольные ячейки, узлы-огоньки, грани, кольцо с рунами; радиус 1 — масштаб эффекта задаёт радиус. '
                    'Сгенерировано tools/gen_silent_staff_fx.py.', 'silent', B, ['#6E8AA0', '#7FD8C8', '#BFF6E8', '#DFFFF6', '#FFFFFF'], [3, 4], 0.16,
                    {'delay': 0, 'duration': 18, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.2}, 18, collapse=10, blend='additive')


def dragon():
    """Тень чёрного дракона Ворганы (по аниме: Неро — чёрный дракон): изгиб шеи с пластинами и гребнем, вытянутая морда, надбровья,
    загнутые назад рога, приоткрытая пасть с клыками, скулы-шипы; тёмный полупрозрачный, фиолетовые глаза и тонкие светящиеся контуры."""
    B = Boxes()
    neck = []
    for k in range(9):                                               # шея: S-изгиб снизу-сзади к голове
        u = k / 8
        y = -2.2 + 2.1 * math.sin(u * math.pi / 2)
        z = -1.6 + 1.3 * u + 0.25 * math.sin(u * math.pi)
        neck.append((0, y, z, 0.78 - 0.22 * u))
    for (x0, y0, z0, w0), (x1, y1, z1, w1) in zip(neck, neck[1:]):
        B.seg3((x0, y0, z0), (x1, y1, z1), (w0 + w1) / 2, 1)
        B.seg3((x0, y0 - w0 * 0.42, z0 + 0.02), (x1, y1 - w1 * 0.42, z1 + 0.02), (w0 + w1) * 0.32, 2)   # брюшные пластины
        B.seg3((x0, y0 + w0 * 0.5, z0), (x0, y0 + w0 * 0.5 + 0.28, z0 - 0.12), 0.07, 0)               # гребень-шипы
    # череп и морда
    B.cbox(0, 0.05, 0.15, 0.8, 0.62, 0.95, 1)
    B.cbox(0, 0.36, 0.2, 0.62, 0.14, 0.85, 0)                        # темя
    for s in (-1, 1):
        B.cbox(s * 0.26, 0.3, 0.62, 0.22, 0.12, 0.4, 0, [0, 0, s * 12])   # надбровья
    B.cbox(0, 0.0, 0.95, 0.56, 0.36, 0.85, 1, [6, 0, 0])               # верхняя челюсть
    B.cbox(0, 0.12, 1.42, 0.38, 0.22, 0.32, 1, [10, 0, 0])             # кончик морды
    for s in (-1, 1):
        B.cbox(s * 0.11, 0.16, 1.58, 0.07, 0.05, 0.05, 2)               # ноздри
    B.cbox(0, -0.38, 0.88, 0.46, 0.14, 0.8, 1, [-20, 0, 0])            # нижняя челюсть — пасть приоткрыта
    B.cbox(0, -0.2, 0.9, 0.42, 0.12, 0.7, 4, [-8, 0, 0])               # отсвет фиолетового пламени в пасти
    for s in (-1, 1):
        for k in range(3):                                            # клыки сверху и снизу
            B.cbox(s * (0.12 + 0.05 * k), -0.2, 1.25 - 0.18 * k, 0.04, 0.14, 0.04, 3)
            B.cbox(s * (0.12 + 0.05 * k), -0.3, 1.12 - 0.18 * k, 0.035, 0.1, 0.035, 3)
        B.cbox(s * 0.24, 0.16, 0.66, 0.13, 0.07, 0.12, 4)              # глаза
        B.cbox(s * 0.24, 0.16, 0.6, 0.2, 0.03, 0.03, 4)                # прищур-свечение
        horn = [(s * 0.28, 0.38, 0.05), (s * 0.5, 0.7, -0.35), (s * 0.62, 0.85, -0.8), (s * 0.6, 0.8, -1.2), (s * 0.5, 0.62, -1.45)]
        for i, (p, q) in enumerate(zip(horn, horn[1:])):
            B.seg3(p, q, 0.16 - 0.03 * i, 1)
        B.seg3(horn[0], (s * 0.52, 0.2, -0.3), 0.08, 0)               # малый рог назад
        for k in range(4):                                            # шипы по скуле
            B.seg3((s * 0.4, 0.0 - 0.04 * k, 0.4 - 0.22 * k), (s * 0.62, 0.08 - 0.04 * k, 0.25 - 0.22 * k), 0.06, 0)
        # тонкие светящиеся контуры: линия челюсти, надбровья, вдоль рога
        B.seg3((s * 0.28, -0.08, 0.5), (s * 0.2, -0.06, 1.45), 0.02, 4)
        B.seg3((s * 0.38, 0.36, 0.45), (s * 0.1, 0.3, 0.85), 0.02, 4)
        for p, q in zip(horn, horn[1:]):
            B.seg3((p[0], p[1] + 0.06, p[2]), (q[0], q[1] + 0.06, q[2]), 0.018, 4)
    for (x0, y0, z0, w0), (x1, y1, z1, w1) in zip(neck, neck[1:]):     # светящийся контур по гребню шеи
        B.seg3((x0, y0 + w0 * 0.52, z0), (x1, y1 + w1 * 0.52, z1), 0.02, 4)
    return mesh_doc('Тень чёрного дракона Ворганы (T20, «Чёрное пламя»): детальная голова и шея, фиолетовые глаза и контуры. Сгенерировано tools/gen_silent_staff_fx.py.',
                    'forbidden', B, ['#050407', '#120D18', '#2A1D38', '#E8DDF4', '#8A46E0'], [3, 4], 0.78,
                    {'delay': 0, 'duration': 30, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.6}, 30, collapse=20)


def fx(name, comment, style, duration, elements):
    return name, {'comment': comment + ' Сгенерировано tools/gen_silent_staff_fx.py.', 'style': style, 'duration': duration, 'elements': elements}


def build_fx():
    out = []
    out.append(fx('silent_wind_spears', 'Одно копьё ветра (T20): модель вдоль полёта и шлейф; сервер двигает экземпляр (Fx.move, yaw — к цели) и гасит при попадании.',
                  'silent', -1, [
                      {'type': 'flash', 'delay': 0, 'duration': 6, 'at': 'caster', 'follow': True, 'size': 0.9, 'rays': 4, 'color': '@core'},
                      {'type': 'mesh', 'model': 'silent_spear', 'delay': 0, 'at': 'caster', 'follow': True, 'scale': 1.0},
                      {'type': 'sprites', 'delay': 0, 'duration': 200, 'at': 'caster', 'follow': True, 'texture': '@sparks', 'count': 400, 'rate': 3,
                       'spread': 0.25, 'speed': 0.01, 'size': [0.14, 0.03], 'life': 8, 'color': '@primary'}]))
    out.append(fx('silent_wind_spears_hit', 'Попадание копья ветра (T20): кольцо ветра, вспышка, искры. Код играет в точке попадания.',
                  'silent', 30, [
                      {'type': 'flash', 'delay': 0, 'duration': 6, 'at': 'caster', 'size': 1.8, 'anamorphic': 4, 'rays': 6, 'color': '@core'},
                      {'type': 'wave', 'shape': 'sphere', 'delay': 0, 'duration': 8, 'at': 'caster', 'radius': 1.4, 'rim': 0.9, 'color': '@primary'},
                      {'type': 'sprites', 'delay': 0, 'duration': 4, 'at': 'caster', 'texture': '@sparks', 'count': 30, 'rate': 30, 'spread': 0.3,
                       'speed': 0.18, 'gravity': 0.01, 'size': [0.16, 0.03], 'life': 14, 'color': '@primary'}]))
    # залп: печати веером за спиной — как SilentVolleySpell.seal (x = sin a · r, z = cos a · r в осях взгляда, a от 80° до 280°)
    els = []
    n, arc, r = 24, 200.0, 2.5
    for i in range(n):
        k = i / (n - 1)
        a = math.radians(180 - arc / 2 + arc * k)
        up = (1.15 if i % 2 == 0 else 2.15) + 0.25 * math.sin(k * math.pi)
        x, z = math.sin(a) * r, math.cos(a) * r
        els.append({'type': 'sigil', 'id': 'silent_volley_seal', 'delay': int(i * 48 / n), 'at': f'caster+{x:.2f},{up:.2f},{z:.2f}', 'follow': True,
                    'orientation': 'billboard'})
    els.append({'type': 'sprites', 'delay': 0, 'duration': 60, 'at': 'caster+0,1.5,-1', 'follow': True, 'texture': '@sparks', 'count': 120, 'rate': 2,
                'spread': 2.6, 'speed': 0.01, 'gravity': -0.002, 'size': [0.12, 0.03], 'life': 30, 'color': '@primary'})
    out.append(fx('silent_volley', 'Безмолвный залп (T20): 24 печати веером за спиной, собираются по одной за 80 % каста; стрелы — silent_volley_arrow.',
                  'silent', -1, els))
    out.append(fx('silent_volley_arrow', 'Одна стрела залпа (T20): яркое ядро и шлейф; сервер двигает экземпляр (Fx.move) по дуге к цели и гасит при попадании, '
                  'там же играет silent_wind_spears_hit (меньшим масштабом).', 'silent', -1, [
                      {'type': 'flash', 'delay': 0, 'duration': 200, 'at': 'caster', 'follow': True, 'size': 0.45, 'rays': 0, 'color': '@core'},
                      {'type': 'sprites', 'delay': 0, 'duration': 200, 'at': 'caster', 'follow': True, 'texture': '@sparks', 'count': 300, 'rate': 3,
                       'spread': 0.08, 'speed': 0.005, 'size': [0.12, 0.02], 'life': 10, 'color': '@secondary'}]))
    out.append(fx('silent_barrier_dome', 'Купол Барьера (T20): шестиугольные ячейки собираются снизу вверх, мягкая сфера-свечение, кольцо на земле, искры. '
                  'Масштаб = радиус; следует за заклинателем; длительность = время купола.', 'silent', -1, [
                      {'type': 'mesh', 'model': 'silent_dome', 'delay': 0, 'at': 'caster', 'follow': True},
                      {'type': 'wave', 'shape': 'sphere', 'delay': 2, 'at': 'caster', 'follow': True, 'radius': 1.0, 'rim': 0.6, 'speed': 0, 'color': '@primary',
                       'brightness': 0.35, 'in': {'duration': 14, 'easing': 'easeOutCubic'}},
                      {'type': 'sigil', 'id': 'silent_impact', 'delay': 0, 'at': 'caster', 'follow': True, 'sigilScale': 2.4},
                      {'type': 'sprites', 'delay': 4, 'at': 'caster+0,1,0', 'follow': True, 'texture': '@sparks', 'count': 600, 'rate': 1,
                       'spread': 1.0, 'speed': 0.004, 'gravity': -0.001, 'size': [0.12, 0.03], 'life': 40, 'color': '@primary'}]))
    # пламя Ворганы: тень дракона над правым плечом (WorganFlameSpell.headPos: справа 0.95, над головой, чуть сзади)
    out.append(fx('silent_worgan_flame', 'Чёрное пламя Ворганы (T20): за каст (40 тиков) над правым плечом встаёт тень дракона, затем выдох — '
                  'конус чёрного пламени с фиолетовой кромкой на 12 блоков (3 с), пепел; тень рассыпается. Следует за заклинателем.', 'forbidden', 130, [
                      {'type': 'mesh', 'model': 'worgan_dragon', 'delay': 0, 'until': 112, 'at': 'caster+0.95,2.6,-0.25', 'follow': True, 'scale': 1.3},
                      {'type': 'sprites', 'delay': 0, 'duration': 40, 'at': 'caster+0.95,2.2,-0.25', 'follow': True, 'texture': 'soul_mote', 'count': 60,
                       'rate': 2, 'spread': 0.8, 'speed': 0.01, 'gravity': -0.002, 'size': [0.4, 0.1], 'life': 30, 'color': '#2A1638'},
                      {'type': 'flash', 'delay': 38, 'duration': 6, 'at': 'caster+0.95,2.6,1.2', 'follow': True, 'size': 1.4, 'rays': 5, 'color': '#9A5CF0'},
                      {'type': 'sprites', 'delay': 40, 'duration': 60, 'at': 'caster+0.95,2.5,1.4', 'follow': True, 'texture': 'soul_mote', 'count': 900,
                       'rate': 16, 'spread': 0.35, 'speed': 0.42, 'gravity': -0.002, 'size': [0.35, 1.1], 'life': 22, 'color': '#1A0C24', 'cone': 40},
                      {'type': 'sprites', 'delay': 40, 'duration': 60, 'at': 'caster+0.95,2.5,1.4', 'follow': True, 'texture': '@sparks', 'count': 500,
                       'rate': 9, 'spread': 0.3, 'speed': 0.44, 'size': [0.18, 0.05], 'life': 20, 'color': '#9A5CF0', 'cone': 40},
                      {'type': 'sprites', 'delay': 60, 'duration': 60, 'at': 'caster+0,1,6', 'follow': True, 'texture': '@shards', 'count': 120, 'rate': 2,
                       'spread': 4, 'speed': 0.01, 'gravity': 0.002, 'size': [0.18, 0.06], 'life': 50, 'color': '#3A3440'}]))
    return out


def main():
    md = os.path.join(A, 'fx', 'meshes')
    for name, doc in (('silent_spear', spear()), ('silent_dome', dome()), ('worgan_dragon', dragon())):
        json.dump(doc, open(os.path.join(md, name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        print(f'mesh {name}: {len(doc["parts"][0]["boxes"])} boxes')
    for name, doc in build_fx():
        json.dump(doc, open(os.path.join(A, 'fx', name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'fx {name}: {len(doc["elements"])} elements')
    seal = {
        'comment': 'Малая печать залпа (T20): собирается по частям за спиной ведьмы, из неё вылетает стрела. Сгенерировано tools/gen_silent_staff_fx.py.',
        'size': 0.32, 'color': '#7FFFD0', 'orientation': 'billboard', 'lifetime': -1, 'hold': -1,
        'layers': [
            {'id': 'glow', 'type': 'disc', 'texture': 'glow', 'radius': 1.3, 'brightness': 0.55,
             'appear': {'delay': 4, 'duration': 6, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}, 'pulse': {'amp': 0.2, 'period': 24}},
            {'id': 'seal', 'type': 'disc', 'texture': 'silent_nimbus', 'radius': 1.0,
             'appear': {'delay': 0, 'duration': 10, 'easing': 'easeOutBack', 'modes': ['pieces'],
                        'pieces': {'count': 6, 'order': 'scatter', 'pieceTime': 0.5, 'fly': 0.8, 'lift': 0.4, 'orbit': 40, 'tilt': 70, 'spin': 90}},
             'rotation': {'speed': 30, 'boost': 2.0}}],
        'formedFlash': {'color': '#FFFFFF', 'size': 1.2, 'duration': 6, 'sparks': 6},
        'dissolve': {'modes': ['collapse'], 'duration': 8}}
    json.dump(seal, open(os.path.join(A, 'sigils', 'silent_volley_seal.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('sigil silent_volley_seal')


if __name__ == '__main__':
    main()
