#!/usr/bin/env python3
"""
Прямая кинематика модели GeckoLib (та же математика, что в шаблоне превью tools/ereb_hand_preview.template.html и в GeckoLib:
кость = перенос на ось + поворот ZYX; x и y поворота в кадре three.js инвертированы, x координат — тоже).
Координаты на выходе — модельные (как в .geo.json): x — к левому боку модели, y — вверх, z — назад (вперёд = −z). Единица — 1/16 блока.
Используется проверкой анимаций tools/check_ereb_hand_anims.py и письмом (где держится схваченный игрок).
"""
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')


def rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]])


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]])


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])


def tr(x, y, z):
    m = np.eye(4)
    m[:3, 3] = (x, y, z)
    return m


def sc(x, y, z):
    return np.diag([x, y, z, 1.0])


def euler_zyx(x, y, z):
    return rz(z) @ ry(y) @ rx(x)


D2R = math.pi / 180

EASE = {
    'linear': lambda t: t,
    'easeInSine': lambda t: 1 - math.cos(t * math.pi / 2), 'easeOutSine': lambda t: math.sin(t * math.pi / 2),
    'easeInOutSine': lambda t: -(math.cos(math.pi * t) - 1) / 2,
    'easeInQuad': lambda t: t * t, 'easeOutQuad': lambda t: 1 - (1 - t) ** 2,
    'easeInCubic': lambda t: t ** 3, 'easeOutCubic': lambda t: 1 - (1 - t) ** 3,
    'easeInOutCubic': lambda t: 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2,
    'easeInQuart': lambda t: t ** 4, 'easeOutQuart': lambda t: 1 - (1 - t) ** 4,
    'easeOutBack': lambda t: 1 + 2.70158 * (t - 1) ** 3 + 1.70158 * (t - 1) ** 2,
}


def chan_at(chan, t, dflt):
    if isinstance(chan, list):
        return chan
    if 'vector' in chan:
        return chan['vector']
    ks = sorted(chan, key=float)
    get = lambda k: (chan[k]['vector'] if isinstance(chan[k], dict) else chan[k], chan[k].get('easing') if isinstance(chan[k], dict) else None)
    if not ks:
        return dflt
    if t <= float(ks[0]):
        return get(ks[0])[0]
    if t >= float(ks[-1]):
        return get(ks[-1])[0]
    i = 0
    while float(ks[i + 1]) < t:
        i += 1
    a, b = float(ks[i]), float(ks[i + 1])
    va, _ = get(ks[i])
    vb, e = get(ks[i + 1])
    k = EASE.get(e or 'linear', EASE['linear'])((t - a) / (b - a))
    return [va[j] + (vb[j] - va[j]) * k for j in range(3)]


def sample(anim, t):
    """{кость: (rot, pos, scale)} в момент t."""
    o = {}
    for bn, ch in (anim or {}).get('bones', {}).items():
        r = chan_at(ch['rotation'], t, [0, 0, 0]) if 'rotation' in ch else [0, 0, 0]
        p = chan_at(ch['position'], t, [0, 0, 0]) if 'position' in ch else [0, 0, 0]
        s = chan_at(ch['scale'], t, [1, 1, 1]) if 'scale' in ch else [1, 1, 1]
        if not isinstance(s, list):
            s = [s, s, s]
        o[bn] = (r, p, s)
    return o


class Model:
    def __init__(self, geo_path=None):
        geo_path = geo_path or os.path.join(A, 'geo', 'entity', 'ereb_hand.geo.json')
        g = json.load(open(geo_path, encoding='utf-8'))['minecraft:geometry'][0]
        self.bones = {b['name']: b for b in g['bones']}
        self.order = [b['name'] for b in g['bones']]

    def world(self, pose):
        """Мировые матрицы костей (в кадре three: x инвертирован)."""
        W = {}

        def get(n):
            if n in W:
                return W[n]
            b = self.bones[n]
            piv = np.array([-b['pivot'][0], b['pivot'][1], b['pivot'][2]], float)
            r0 = b.get('rotation', [0, 0, 0])
            par = b.get('parent')
            pp = np.array([-self.bones[par]['pivot'][0], self.bones[par]['pivot'][1], self.bones[par]['pivot'][2]]) if par else np.zeros(3)
            r, p, s = pose.get(n, ([0, 0, 0], [0, 0, 0], [1, 1, 1]))
            base = piv - pp
            m = tr(base[0] - p[0], base[1] + p[1], base[2] + p[2]) @ \
                euler_zyx((-r0[0] - r[0]) * D2R, (-r0[1] - r[1]) * D2R, (r0[2] + r[2]) * D2R) @ sc(*[max(1e-4, v) for v in s])
            W[n] = (get(par) if par else np.eye(4)) @ m
            return W[n]
        for n in self.order:
            get(n)
        return W

    def cubes(self, name):
        """[(локальная матрица бруска, (x0, y0, z0), (x1, y1, z1))] в кадре кости (относительно оси кости, кадр three)."""
        b = self.bones[name]
        piv = np.array([-b['pivot'][0], b['pivot'][1], b['pivot'][2]], float)
        res = []
        for c in b.get('cubes', []):
            if c['size'][0] * c['size'][1] * c['size'][2] == 0:
                continue
            inf = c.get('inflate', 0)
            x0, x1 = -(c['origin'][0] + c['size'][0]) - inf, -c['origin'][0] + inf
            y0, y1 = c['origin'][1] - inf, c['origin'][1] + c['size'][1] + inf
            z0, z1 = c['origin'][2] - inf, c['origin'][2] + c['size'][2] + inf
            cp = np.array([-c['pivot'][0], c['pivot'][1], c['pivot'][2]]) if 'pivot' in c else piv
            rot = c.get('rotation', [0, 0, 0])
            m = tr(*(cp - piv)) @ euler_zyx(-rot[0] * D2R, -rot[1] * D2R, rot[2] * D2R)
            lo = np.array([x0, y0, z0]) - cp
            hi = np.array([x1, y1, z1]) - cp
            res.append((m, lo, hi))
        return res

    def points(self, W, name, n=3):
        """Точки бруска(ов) кости в мире (модельные координаты): углы и решётка n×n×n."""
        pts = []
        for m, lo, hi in self.cubes(name):
            for i in range(n):
                for j in range(n):
                    for k in range(n):
                        f = np.array([i, j, k]) / (n - 1)
                        q = lo + (hi - lo) * f
                        w = W[name] @ m @ np.array([q[0], q[1], q[2], 1.0])
                        pts.append(np.array([-w[0], w[1], w[2]]))
        return pts

    def solids(self, W, names, shrink=0.25):
        """Подготовка проверки «точка внутри»: [(кость, обратная матрица, lo, hi)]."""
        res = []
        for n in names:
            for m, lo, hi in self.cubes(n):
                res.append((n, np.linalg.inv(W[n] @ m), lo + shrink, hi - shrink))
        return res

    @staticmethod
    def hits(solids, pts):
        """Какие кости содержат хоть одну из точек pts (модельные координаты)."""
        if not pts:
            return set()
        P = np.array([[-p[0], p[1], p[2], 1.0] for p in pts]).T
        out = set()
        for n, inv, lo, hi in solids:
            L = (inv @ P)[:3]
            ok = np.all((L > lo[:, None]) & (L < hi[:, None]), axis=0)
            if ok.any():
                out.add(n)
        return out

    def inside(self, W, name, p, shrink=0.25):
        return bool(self.hits(self.solids(W, [name], shrink), [p]))

    def point(self, W, name, local):
        """Модельная точка, заданная в модельных координатах покоя (как в .geo.json), после позы."""
        b = self.bones[name]
        piv = np.array([-b['pivot'][0], b['pivot'][1], b['pivot'][2]], float)
        q = np.array([-local[0], local[1], local[2]]) - piv
        w = W[name] @ np.array([q[0], q[1], q[2], 1.0])
        return np.array([-w[0], w[1], w[2]])


# ---------------------------------------------------------------- рапира в кости bipedHandRight (как buildItem шаблона)
def rapier_points(W, model, n=8):
    """Точки клинка (от гарды к острию) в модельных координатах. Хват — как в превью (ITEM_FIX, ITEM_OFF, display thirdperson_righthand)."""
    disp = {'rotation': [0, -90, 55], 'translation': [0, 4.0, 0.5], 'scale': [0.95, 0.95, 0.95]}
    fix, off = [-90, 0, 0], [0, -1, 0]
    hold = tr(*off) @ (rx(fix[0] * D2R) @ ry(fix[1] * D2R) @ rz(fix[2] * D2R))
    dm = tr(*disp['translation']) @ (rx(disp['rotation'][0] * D2R) @ ry(disp['rotation'][1] * D2R) @ rz(disp['rotation'][2] * D2R)) @ \
        sc(*disp['scale'])
    el = tr(0, 0, 0) @ rz(-45 * D2R)            # бруски повёрнуты на −45° вокруг z у (8, 8, 8); рукоять в y≈1, острие y≈24 (после −8)
    pts = []
    for k in range(n + 1):
        y = 6.5 + (24.2 - 6.5) * k / n
        q = np.array([0.0, y - 8, 0.0, 1.0])
        w = W['bipedHandRight'] @ hold @ dm @ el @ q
        pts.append(np.array([-w[0], w[1], w[2]]))
    return pts
