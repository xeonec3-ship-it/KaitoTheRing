#!/usr/bin/env python3
"""
Эффекты четырёх заклинаний посоха безмолвной ведьмы (T20): модели и эффекты под то, что передаёт код (docs/specs/tasks/T20_silent_staff_spells.md,
раздел «Как сделано в коде»). Стиль `silent`.

Модели (fx/meshes, часть `boxes` — docs/fx.md):
  silent_spear   — прозрачное копьё ветра: вытянутый ромб вдоль +z, светлые грани, светящийся стержень, три кольца-завихрения
  silent_dome    — купол Барьера: шестиугольные ячейки на сфере радиуса 1 (масштаб эффекта = радиус), собирается снизу вверх
  worgan_dragon  — тень чёрного дракона: встаёт из правого плеча, шея S-изгибом вверх-вперёд, детальная голова с раскрытой пастью;
                   тёмная полупрозрачная, фиолетовые глаза и контуры; смотрит в +z; начало модели — правое плечо
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
    doc = mesh_doc('Купол Барьера (T20): шестиугольные ячейки, узлы-огоньки, грани, кольцо с рунами; радиус 1 — масштаб эффекта задаёт радиус. '
                   'Удар по куполу (T08, Fx.hit) — рябь: кольцо света бежит по ячейкам от точки удара к противоположной стороне. '
                   'Сгенерировано tools/gen_silent_staff_fx.py.', 'silent', B, ['#6E8AA0', '#7FD8C8', '#BFF6E8', '#DFFFF6', '#FFFFFF'], [3, 4], 0.16,
                   {'delay': 0, 'duration': 18, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.2}, 18, collapse=10, blend='additive')
    # T08: рябь по куполу (docs/sigils.md «Отклик на удар», для меша — расстояние по сфере, docs/fx.md «hit у меша»)
    doc['hit'] = {'duration': 12, 'width': 0.2, 'rings': 3, 'spacing': 0.42, 'strength': 1.3, 'shake': 0.012, 'shakePeriod': 5,
                  'flash': 1.0, 'sparks': 14, 'sparkSpeed': 0.14, 'color': '#E8FFF6'}
    return doc


# ---------------------------------------------------------------- тень дракона: матрицы и локальные системы координат
def _rot(rx, ry, rz):
    """Матрица поворота как three.js Euler 'YXZ': R = Ry·Rx·Rz (градусы)."""
    a, b, c = (math.radians(v) for v in (rx, ry, rz))
    ca, sa, cb, sb, cc, sc = math.cos(a), math.sin(a), math.cos(b), math.sin(b), math.cos(c), math.sin(c)
    Rx = [[1, 0, 0], [0, ca, -sa], [0, sa, ca]]
    Ry = [[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]]
    Rz = [[cc, -sc, 0], [sc, cc, 0], [0, 0, 1]]
    return _mm(Ry, _mm(Rx, Rz))


def _mm(A, Bm):
    return [[sum(A[i][k] * Bm[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _mv(M, v):
    return tuple(sum(M[i][k] * v[k] for k in range(3)) for i in range(3))


def _euler(M):
    """Обратно в Euler 'YXZ' (как Euler.setFromRotationMatrix в three.js)."""
    m23 = max(-1.0, min(1.0, M[1][2]))
    x = math.asin(-m23)
    if abs(m23) < 0.9999999:
        y, z = math.atan2(M[0][2], M[2][2]), math.atan2(M[1][0], M[1][1])
    else:
        y, z = math.atan2(-M[2][0], M[0][0]), 0.0
    return [math.degrees(x), math.degrees(y), math.degrees(z)]


def _nrm(v):
    ln = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / ln for c in v)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _axes(T, up):
    """Матрица со столбцами X (вбок), Y (≈up, ортогонален T), Z = T."""
    T = _nrm(T)
    d = sum(u * t for u, t in zip(up, T))
    N = _nrm(tuple(u - d * t for u, t in zip(up, T)))
    X = _cross(N, T)
    return [[X[0], N[0], T[0]], [X[1], N[1], T[1]], [X[2], N[2], T[2]]]


class Frame:
    """Локальная система (начало + поворот) поверх Boxes: голова, челюсть, рог строятся в своих осях, бруски пишутся в осях модели."""
    I = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]

    def __init__(self, B, o=(0, 0, 0), M=None):
        self.B, self.o, self.M = B, tuple(o), M or Frame.I

    def pt(self, p):
        q = _mv(self.M, p)
        return tuple(o + c for o, c in zip(self.o, q))

    def child(self, o, M=None):
        return Frame(self.B, self.pt(o), _mm(self.M, M or Frame.I))

    def box(self, c, size, t, rot=None, M=None):
        Mw = _mm(self.M, M if M is not None else (_rot(*rot) if rot else Frame.I))
        e = _euler(Mw)
        x, y, z = self.pt(c)
        self.B.cbox(x, y, z, size[0], size[1], size[2], t, e)

    def seg(self, p, q, w, t, h=None, roll=0.0, ext=0.5):
        """Брусок от p до q (в осях кадра), сечение w×h, roll — поворот сечения вокруг оси бруска."""
        dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
        ln = math.sqrt(dx * dx + dy * dy + dz * dz)
        yaw = math.degrees(math.atan2(dx, dz))
        pitch = -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
        self.box(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2), (w, h if h else w, ln + w * ext), t, [pitch, yaw, roll])

    def taper(self, pts, w0, w1, t, glow=None, gw=0.016, band=None):
        """Сужающийся изогнутый рог/шип по точкам; band — каждый второй отрезок другим тоном (кольчатые рога), glow — светящаяся линия по верху."""
        n = len(pts) - 1
        for i, (p, q) in enumerate(zip(pts, pts[1:])):
            w = w0 + (w1 - w0) * (i + 0.5) / n
            self.seg(p, q, w, band if band is not None and i % 2 else t)
            if glow is not None and i < n - 1:
                self.seg((p[0], p[1] + w * 0.45, p[2]), (q[0], q[1] + w * 0.45, q[2]), gw, glow, ext=0)


def _catmull(P, n):
    """Сплайн Катмулла–Рома через точки P (концы продлены), n отрезков на участок."""
    P = [tuple(2 * a - b for a, b in zip(P[0], P[1]))] + list(P) + [tuple(2 * a - b for a, b in zip(P[-1], P[-2]))]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            u = k / n
            out.append(tuple(0.5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u ** 3)
                             for a, b, c, d in zip(p0, p1, p2, p3)))
    out.append(P[-2])
    return out


# Где стоит тень относительно заклинателя (оси взгляда: x вправо, y вверх от ног, z вперёд): основание шеи — на правом плече.
DRAGON_AT = (0.45, 1.35, 0.0)
DRAGON_SCALE = 1.0
DRAGON_HEAD_PITCH = 10.0          # голова опущена на 10° — морда смотрит туда же, куда прицел (голова на ~1.4 блока выше глаз)
DRAGON_JAW = 30.0                 # пасть раскрыта на 30°
# Хребет шеи (в осях модели, от основания на плече): нижняя дуга выгибается вперёд, верхняя — назад (над головой ведьмы, выше глаз),
# затем шея загибается вперёд к голове — S-изгиб змеиного горла. Последняя точка — затылок, касательная там = направление головы.
DRAGON_SPINE = [(0.00, -0.12, 0.22), (0.08, 0.30, 0.50), (0.26, 0.78, 0.40), (0.42, 1.22, 0.00), (0.50, 1.60, 0.08),
                (0.49, 1.80, 0.45), (0.47, 1.80, 0.72)]
DRAGON_MOUTH = None               # точка между челюстями (в осях модели) — считает dragon(), из неё дышит эффект


def dragon():
    """Тень чёрного дракона Ворганы (по аниме: Неро — чёрный дракон). Встаёт из правого плеча заклинателя: шея S-изгибом вверх и вперёд
    (нижняя дуга вперёд, верхняя — назад над головой, затем к голове), голова впереди-сверху смотрит по взгляду, пасть раскрыта —
    из неё выдох (DRAGON_MOUTH). Шея — восьмигранная труба с брюшными пластинами, боковой чешуёй и гребнем шипов, светящаяся линия по хребту.
    Голова: затылок и темя с гребнем, надбровья, глаза-щели, сужающаяся морда, ноздри, носовой рожок, кольчатые рога назад-вверх,
    малые рога, гребни-«уши», шипы по скулам, нижняя челюсть на шарнире с зубами, клыки, язык и фиолетовый жар в горле, шипы-бородка.
    Тёмная полупрозрачная, глаза и контуры светятся фиолетовым. Ничего не уходит за спину ниже глаз (проверка check_dragon())."""
    global DRAGON_MOUTH
    B = Boxes()
    W = Frame(B)
    UP = (0, 1, 0)

    # ---- шея
    S = _catmull(DRAGON_SPINE, 4)
    n = len(S) - 1
    rad = lambda u: 0.2 - 0.07 * u                                # полутолщина: 0.4 у плеча → 0.26 у затылка
    for i, (p, q) in enumerate(zip(S, S[1:])):
        u = (i + 0.5) / n
        T = _nrm(tuple(b - a for a, b in zip(p, q)))
        dors = (0, T[2], -T[1])                                    # «спина» шеи: назад, пока шея вертикальна, вверх — когда горизонтальна
        F = W.child(tuple((a + b) / 2 for a, b in zip(p, q)), _axes(T, dors))
        ln = math.dist(p, q) + 0.03
        r = rad(u)
        F.box((0, 0, 0), (2 * r, 2 * r * 0.92, ln), 1)                               # восьмигранник: квадрат + повёрнутый на 45°
        F.box((0, 0, 0), (2 * r * 0.9, 2 * r * 0.84, ln), 1, M=_rot(0, 0, 45))
        F.box((0, -r * 0.82, 0), (2 * r * 0.78, r * 0.32, ln * 0.78), 2)             # брюшная пластина — полосами, видна сегментация
        for sd in (-1, 1):                                                          # боковая чешуя, вразбежку
            if i % 2 == (0 if sd > 0 else 1):
                F.box((sd * r * 0.88, r * 0.15, 0), (r * 0.28, r * 0.7, ln * 0.7), 0, rot=[0, sd * 8, sd * 20])
        F.seg((0, r * 0.95, -ln * 0.3), (0, r * 0.95, ln * 0.55), 0.022, 4, ext=0)     # светящийся хребет
        if i % 2 == 0 and u < 0.97 and p[1] > 0.3:                                  # гребень: шип назад-вверх, выше к середине шеи (не у плеча — там он смотрел бы за спину)
            hgt = 0.12 + 0.16 * math.sin(math.pi * min(1.0, u * 1.15))
            F.taper([(0, r * 0.8, ln * 0.2), (0, r + hgt * 0.55, -ln * 0.05), (0, r + hgt, -ln * 0.45)], 0.075, 0.025, 0)
            F.seg((0, r + hgt * 0.5, -ln * 0.02), (0, r + hgt * 0.95, -ln * 0.42), 0.014, 4, ext=0)
    # основание: тень вытекает из плеча струйками дыма (вниз и вбок, перед спиной, не за ней)
    for k, (dx, dz) in enumerate(((-0.18, 0.12), (0.2, 0.05), (0.05, 0.22), (-0.05, 0.02), (0.22, 0.2))):
        pts = [(0.0 + dx * j * 0.35 + 0.03 * math.sin(j * 1.7 + k), -0.05 - j * 0.11, 0.06 + dz * j * 0.3) for j in range(5)]
        W.taper(pts, 0.12, 0.03, 1 if k % 2 else 2)

    # ---- голова: начало — затылок (конец хребта), ось z — вдоль морды, опущена на DRAGON_HEAD_PITCH
    j = DRAGON_SPINE[-1]
    H = W.child(j, _rot(DRAGON_HEAD_PITCH, 0, 0))
    H.box((0, 0.03, 0.1), (0.42, 0.36, 0.4), 1)                                     # затылок
    H.box((0, 0.02, 0.1), (0.36, 0.32, 0.42), 1, M=_rot(0, 0, 45))
    H.box((0, 0.2, 0.3), (0.34, 0.08, 0.52), 0, rot=[4, 0, 0])                      # темя — тёмная пластина
    H.box((0, 0.27, 0.22), (0.05, 0.07, 0.44), 0)                                   # срединный гребень на темени
    H.seg((0, 0.31, 0.02), (0, 0.29, 0.45), 0.014, 4, ext=0)
    for k in range(3):                                                               # шипы на затылке — продолжение гребня шеи
        H.taper([(0, 0.2, 0.02 - 0.1 * k), (0, 0.33 - 0.03 * k, -0.06 - 0.1 * k), (0, 0.42 - 0.05 * k, -0.2 - 0.1 * k)], 0.06, 0.02, 0)
    # морда: сужается вперёд, верхняя линия чуть опускается к носу
    ns = 6
    for k in range(ns):
        z0, z1 = 0.42 + 0.13 * k, 0.42 + 0.13 * (k + 1)
        f = (k + 0.5) / ns
        w, h = 0.33 - 0.15 * f, 0.21 - 0.08 * f
        H.box((0, -0.06 + h / 2, (z0 + z1) / 2), (w, h, z1 - z0 + 0.02), 1, rot=[3, 0, 0])
        H.box((0, -0.06 + h + 0.012, (z0 + z1) / 2), (w * 0.62, 0.035, z1 - z0), 0, rot=[3, 0, 0])   # спинка носа
        for sd in (-1, 1):                                                           # верхние зубы по краю пасти
            big = k == ns - 2
            ln = 0.15 if big else 0.07 + 0.01 * (k % 2)
            H.seg((sd * (w / 2 - 0.025), -0.05, (z0 + z1) / 2), (sd * (w / 2 - 0.035), -0.05 - ln, (z0 + z1) / 2 + 0.01), 0.035 if big else 0.025, 3, ext=0)
    H.box((0, 0.0, 1.22), (0.17, 0.13, 0.12), 1, rot=[18, 0, 0])                     # кончик носа
    H.taper([(0, 0.06, 1.08), (0, 0.13, 1.02), (0, 0.19, 0.94)], 0.05, 0.015, 0)    # носовой рожок
    for sd in (-1, 1):
        H.box((sd * 0.055, 0.06, 1.24), (0.04, 0.025, 0.04), 4)                     # ноздри — фиолетовый жар
        H.seg((sd * 0.06, 0.07, 1.22), (sd * 0.09, 0.1, 1.29), 0.03, 2, ext=0)      # раздутые края ноздрей
        # надбровья: тяжёлая скошенная дуга над глазом
        H.box((sd * 0.15, 0.19, 0.5), (0.13, 0.07, 0.3), 0, rot=[-6, sd * -14, sd * 16])
        H.seg((sd * 0.2, 0.2, 0.34), (sd * 0.11, 0.16, 0.64), 0.016, 4, ext=0)
        # глаз: щель с ярким зрачком
        H.box((sd * 0.165, 0.11, 0.5), (0.05, 0.045, 0.13), 4, rot=[0, sd * -14, 0])
        H.box((sd * 0.185, 0.11, 0.505), (0.012, 0.055, 0.025), 3, rot=[0, sd * -14, 0])
        H.seg((sd * 0.18, 0.105, 0.44), (sd * 0.22, 0.12, 0.3), 0.012, 4, ext=0)    # след-прищур от глаза назад
        # главные рога: назад-вверх и наружу, кольчатые, загиб на концах; светящаяся линия по верху
        horn = [(sd * 0.12, 0.22, 0.14), (sd * 0.2, 0.36, -0.04), (sd * 0.28, 0.48, -0.26), (sd * 0.34, 0.54, -0.5),
                (sd * 0.35, 0.53, -0.72), (sd * 0.31, 0.46, -0.9), (sd * 0.25, 0.38, -1.0)]
        H.taper(horn, 0.12, 0.03, 1, glow=4, band=0)
        # малые рога под главными
        H.taper([(sd * 0.17, 0.1, 0.1), (sd * 0.27, 0.12, -0.08), (sd * 0.35, 0.12, -0.28), (sd * 0.38, 0.09, -0.42)], 0.07, 0.02, 0, glow=4, gw=0.012)
        # гребни-«уши»: веер из трёх тонких пластин за глазом, кромка светится
        for m in range(3):
            a = sd * (25 + 18 * m)
            q = (sd * (0.2 + 0.2 * math.cos(math.radians(abs(a)))), 0.04 + 0.2 * math.sin(math.radians(abs(a))) - 0.1 * m, -0.12 - 0.08 * m)
            H.seg((sd * 0.19, 0.05, 0.2), q, 0.03, 0, h=0.09, roll=sd * (30 + 20 * m))
            H.seg((q[0] - sd * 0.02, q[1], q[2] + 0.04), q, 0.016, 4, ext=0)
        # шипы по скуле, назад-наружу
        for m in range(3):
            H.taper([(sd * 0.17, -0.04, 0.42 - 0.12 * m), (sd * 0.27, -0.03 - 0.02 * m, 0.33 - 0.12 * m), (sd * 0.34, -0.04 - 0.03 * m, 0.22 - 0.12 * m)],
                    0.05, 0.015, 0)
        H.seg((sd * 0.165, -0.05, 0.42), (sd * 0.11, -0.05, 1.2), 0.016, 4, ext=0)   # светящаяся линия губы

    # ---- нижняя челюсть на шарнире у затылка, раскрыта на DRAGON_JAW
    J = H.child((0, -0.07, 0.28), _rot(DRAGON_JAW, 0, 0))
    nj = 6
    for k in range(nj):
        z0, z1 = 0.0 + 0.15 * k, 0.15 * (k + 1)
        f = (k + 0.5) / nj
        w = 0.3 - 0.14 * f
        J.box((0, -0.055, (z0 + z1) / 2), (w, 0.1, z1 - z0 + 0.02), 1)
        J.box((0, -0.11, (z0 + z1) / 2), (w * 0.7, 0.03, z1 - z0), 2)                   # горловая пластина снизу
        for sd in (-1, 1):                                                           # нижние зубы — вверх
            big = k == nj - 2
            ln = 0.12 if big else 0.06
            J.seg((sd * (w / 2 - 0.025), -0.01, (z0 + z1) / 2), (sd * (w / 2 - 0.03), -0.01 + ln, (z0 + z1) / 2 - 0.01), 0.03 if big else 0.022, 3, ext=0)
            J.seg((sd * (w / 2), -0.03, z0), (sd * (w / 2 - 0.01), -0.03, z1), 0.014, 4, ext=0)   # светящаяся кромка челюсти
    J.box((0, -0.06, 0.93), (0.13, 0.08, 0.08), 1)                                  # подбородок
    for sd in (-1, 0, 1):                                                            # шипы-бородка под подбородком
        J.taper([(sd * 0.05, -0.1, 0.85), (sd * 0.07, -0.2, 0.78), (sd * 0.08, -0.3, 0.66)], 0.04, 0.012, 0)
    for sd in (-1, 1):                                                               # шипы на углу челюсти
        J.taper([(sd * 0.14, -0.06, 0.08), (sd * 0.24, -0.12, -0.04), (sd * 0.3, -0.2, -0.12)], 0.05, 0.015, 0)
    # язык (раздвоенный) и жар в горле
    J.box((0, 0.0, 0.42), (0.1, 0.025, 0.6), 4)
    for sd in (-1, 1):
        J.seg((0, 0.0, 0.7), (sd * 0.04, 0.02, 0.86), 0.018, 4, ext=0)
    H.box((0, -0.08, 0.3), (0.2, 0.14, 0.2), 4)                                      # жар в глотке, между челюстями
    # точка выдоха — между кончиками челюстей
    tip_up = H.pt((0, -0.08, 1.22))
    tip_dn = J.pt((0, 0.0, 0.92))
    DRAGON_MOUTH = tuple((a + b) / 2 for a, b in zip(tip_up, tip_dn))

    return mesh_doc('Тень чёрного дракона Ворганы (T20, «Чёрное пламя»): встаёт из правого плеча, шея S-изгибом вверх и вперёд, голова впереди-сверху смотрит '
                    'по взгляду, пасть раскрыта. Начало модели — правое плечо (эффект ставит её в caster+0.45,1.35,0). Сгенерировано tools/gen_silent_staff_fx.py.',
                    'forbidden', B, ['#050407', '#120D18', '#2A1D38', '#E8DDF4', '#8A46E0'], [3, 4], 0.78,
                    {'delay': 0, 'duration': 30, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.5}, 30, collapse=20)


def check_dragon(B_boxes):
    """Ничего за спиной (z < 0) ниже глаз (1.62) ближе 1.5 блока к голове заклинателя; вершины брусков — в осях заклинателя."""
    eye = (0.0, 1.62, 0.0)
    bad = 0
    for b in B_boxes:
        c = ((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2)
        hs = ((b[3] - b[0]) / 2, (b[4] - b[1]) / 2, (b[5] - b[2]) / 2)
        M = _rot(*b[7]) if len(b) > 7 else Frame.I
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    v = _mv(M, (sx * hs[0], sy * hs[1], sz * hs[2]))
                    p = tuple(DRAGON_AT[i] + DRAGON_SCALE * (c[i] + v[i]) for i in range(3))
                    if p[2] < -0.05 and p[1] < eye[1] and math.dist(p, eye) < 1.5:
                        bad += 1
    return bad


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
    # пламя Ворганы: тень дракона встаёт из правого плеча (DRAGON_AT), пламя — из пасти (DRAGON_MOUTH, считает dragon()), конусом по взгляду
    at = lambda p: 'caster+' + ','.join(f'{v:.2f}' for v in p)
    loc = lambda m: tuple(DRAGON_AT[i] + DRAGON_SCALE * m[i] for i in range(3))
    mouth = loc(DRAGON_MOUTH)
    head = loc(DRAGON_SPINE[-1])
    mid = loc(DRAGON_SPINE[3])
    out.append(fx('silent_worgan_flame', 'Чёрное пламя Ворганы (T20): за каст (40 тиков) из правого плеча встаёт тень дракона — шея S-изгибом вверх и вперёд, '
                  'голова впереди-сверху; на 38 тике вспышка в пасти, затем выдох — конус чёрного пламени с фиолетовой кромкой на 12 блоков (3 с) из пасти '
                  'по взгляду, жар в пасти, пепел; тень рассыпается. Следует за заклинателем.', 'forbidden', 130, [
                      {'type': 'mesh', 'model': 'worgan_dragon', 'delay': 0, 'until': 112, 'at': at(DRAGON_AT), 'follow': True, 'scale': DRAGON_SCALE},
                      {'type': 'sprites', 'delay': 0, 'duration': 40, 'at': at(mid), 'follow': True, 'texture': 'soul_mote', 'count': 60,
                       'rate': 2, 'spread': 0.6, 'speed': 0.01, 'gravity': -0.002, 'size': [0.4, 0.1], 'life': 30, 'color': '#2A1638'},
                      {'type': 'sprites', 'delay': 20, 'duration': 20, 'at': at(head), 'follow': True, 'texture': '@sparks', 'count': 30,
                       'rate': 2, 'spread': 0.35, 'speed': 0.005, 'gravity': -0.003, 'size': [0.12, 0.02], 'life': 16, 'color': '#9A5CF0'},
                      {'type': 'flash', 'delay': 38, 'duration': 6, 'at': at(mouth), 'follow': True, 'size': 1.4, 'rays': 5, 'color': '#9A5CF0'},
                      {'type': 'flash', 'delay': 40, 'duration': 60, 'at': at(mouth), 'follow': True, 'size': 0.7, 'rays': 0, 'color': '#6A2CC0'},
                      {'type': 'sprites', 'delay': 40, 'duration': 60, 'at': at(mouth), 'follow': True, 'texture': 'soul_mote', 'count': 900,
                       'rate': 16, 'spread': 0.25, 'speed': 0.42, 'gravity': -0.002, 'size': [0.35, 1.1], 'life': 22, 'color': '#1A0C24', 'cone': 40},
                      {'type': 'sprites', 'delay': 40, 'duration': 60, 'at': at(mouth), 'follow': True, 'texture': '@sparks', 'count': 500,
                       'rate': 9, 'spread': 0.2, 'speed': 0.44, 'size': [0.18, 0.05], 'life': 20, 'color': '#9A5CF0', 'cone': 40},
                      {'type': 'sprites', 'delay': 60, 'duration': 60, 'at': 'caster+0,1,6', 'follow': True, 'texture': '@shards', 'count': 120, 'rate': 2,
                       'spread': 4, 'speed': 0.01, 'gravity': 0.002, 'size': [0.18, 0.06], 'life': 50, 'color': '#3A3440'}]))
    return out


def main():
    md = os.path.join(A, 'fx', 'meshes')
    for name, doc in (('silent_spear', spear()), ('silent_dome', dome()), ('worgan_dragon', dragon())):
        json.dump(doc, open(os.path.join(md, name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        print(f'mesh {name}: {len(doc["parts"][0]["boxes"])} boxes')
        if name == 'worgan_dragon':
            bad = check_dragon(doc['parts'][0]['boxes'])
            print(f'  dragon: mouth {tuple(round(v, 2) for v in DRAGON_MOUTH)} (model axes), corners behind caster below eyes within 1.5: {bad}')
            assert bad == 0, 'worgan_dragon: part of the model is behind the caster below eye level'
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
