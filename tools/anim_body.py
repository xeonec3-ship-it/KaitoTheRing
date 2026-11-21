#!/usr/bin/env python3
"""
Механика тела для анимаций боссов на каркасе мага Iron's (кости body / torso / head / right_leg / left_leg, руки — дети body)
по правилам эталона Epic Fight (docs/specs/anim_style_epicfight.md). Пилот — T29 Мартин (tools/gen_martin.py), дальше T26–T31.

Всё здесь — во ВНУТРЕННИХ осях генератора (оси GeckoLib после чтения JSON): вперёд −z, вверх +y, вправо от персонажа +x;
поворот Y > 0 — влево (против часовой сверху); body/torso X > 0 — наклон НАЗАД (у body; у torso, висящего от шеи, — пояс вперёд);
нога X > 0 — стопа ВПЕРЁД; Z > 0 — крен влево. Позы помечаются o['_int'] = True — bb_in() их не переворачивает (до правки 20.11
перевод знаков X/Y делался дважды; здесь он не делается ни разу, а итог проверяется кадрами и tools/martin_anim_audit.py).

Ключи (Keys): [(t, {параметр: значение}, ease_к_этому_ключу)], параметры интерполируются по отдельности; отсутствующий в ключе
параметр берётся из ближайших ключей, где он задан. Кривые: 'out' — замедление в позу (замах, остановка), 'in' — разгон (удар),
'io' — плавно (возврат, шаги), 'back' — с перехлёстом (остановка удара), 'lin', 'hold' — держать прежнее значение до ключа.
"""
import math

import numpy as np


def ease(k, kind='io'):
    k = min(1.0, max(0.0, k))
    if kind == 'in':
        return k * k * (1.6 - 0.6 * k)            # разгон: к концу скорость максимальна, но без «телепорта» последнего кадра
    if kind == 'in3':
        return k * k * k
    if kind == 'out':
        return 1 - (1 - k) ** 3
    if kind == 'out2':
        return 1 - (1 - k) ** 2
    if kind == 'back':                            # перехлёст ~8% и возврат
        c = 1.4
        return 1 + (c + 1) * (k - 1) ** 3 + c * (k - 1) ** 2
    if kind == 'lin':
        return k
    if kind == 'hold':
        return 0.0 if k < 1 else 1.0
    return k * k * (3 - 2 * k)


class Keys:
    def __init__(self, keys):
        self.keys = sorted(keys, key=lambda k: k[0])
        self.names = sorted({n for _, d, *_ in self.keys for n in d})

    def __call__(self, t, name, default=0.0):
        ks = [(k[0], k[1][name], k[2] if len(k) > 2 else 'io') for k in self.keys if name in k[1]]
        if not ks:
            return default
        if t <= ks[0][0]:
            return np.asarray(ks[0][1], float)
        for (t0, v0, _), (t1, v1, e) in zip(ks, ks[1:]):
            if t <= t1:
                k = ease((t - t0) / max(1e-6, t1 - t0), e)
                return np.asarray(v0, float) * (1 - k) + np.asarray(v1, float) * k
        return np.asarray(ks[-1][1], float)

    def f(self, t, name, default=0.0):
        return float(self(t, name, default))


# ---------------------------------------------------------------- геометрия
def rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def yaw_dir(yaw, pitch=0.0):
    """Направление: yaw — от «вперёд» (−z), + влево; pitch — + вверх (градусы)."""
    y, p = math.radians(yaw), math.radians(pitch)
    return np.array([-math.sin(y) * math.cos(p), math.sin(p), -math.cos(y) * math.cos(p)])


def cyl(phi, r, y):
    """Точка вокруг вертикальной оси тела: phi — азимут (0 — перед, + влево, −90 — справа), r — радиус, y — высота."""
    return np.array([-math.sin(math.radians(phi)) * r, y, -math.cos(math.radians(phi)) * r])


def sag_dir(yaw, theta):
    """Клинок в вертикальной плоскости, повёрнутой на yaw: theta = 0 — вперёд, 90 — вверх, 180 — назад, −45 — вперёд-вниз."""
    th = math.radians(theta)
    f = yaw_dir(yaw)
    return f * math.cos(th) + np.array([0.0, 1.0, 0.0]) * math.sin(th)


def to_euler(R):
    """Матрица → углы ZYX (градусы), R = Rz·Ry·Rx."""
    b = math.asin(max(-1.0, min(1.0, -R[2, 0])))
    if abs(R[2, 0]) < 0.9999:
        a = math.atan2(R[2, 1], R[2, 2])
        c = math.atan2(R[1, 0], R[0, 0])
    else:
        a = math.atan2(-R[1, 2], R[1, 1])
        c = 0.0
    return [math.degrees(a), math.degrees(b), math.degrees(c)]


def leg_angles(v, toe):
    """Углы ноги (внутр., ZYX), чтобы её ось (0, −1, 0) легла по v, а носок (0, 0, −1) смотрел по toe (оба — в осях родителя)."""
    v = np.asarray(v, float)
    v = v / np.linalg.norm(v)
    t = np.asarray(toe, float)
    t = t - v * float(t @ v)
    if np.linalg.norm(t) < 1e-6:
        t = np.array([0.0, 0.0, -1.0]) - v * (-v[2])
    t = t / np.linalg.norm(t)
    ey, ez = -v, -t
    ex = np.cross(ey, ez)
    return to_euler(np.column_stack([ex, ey, ez]))


class Rig:
    """Каркас мага Iron's: модель генератора (nightmare_geo.Model) + её fk(m, pose, bone) -> (M, o)."""

    def __init__(self, m, fk, leg_len=12.0, legs=(('right_leg', 1), ('left_leg', -1))):
        self.m, self.fk, self.L = m, fk, leg_len
        self.legs = legs

    def hip(self, o, leg):
        M, p = self.fk(self.m, o, 'body')
        return M @ self.m.bones[leg].pivot + p, M

    def plant(self, o, feet, drop=0.0, sink=0.7, max_drop=2.0):
        """Ставит стопы в точки feet = {нога: (x, z, toe_yaw, подъём)} (мир, земля y = 0): высота таза — чтобы дальняя нога
        доставала (ноги без колена), плюс drop вниз; ближняя стопа — по направлению на цель, при нехватке длины стопа отходит
        по горизонтали (не уходит под землю). Пишет body.pos[1] и углы ног."""
        body = o.setdefault('body', {})
        pos = list(body.get('pos', [0.0, 0.0, 0.0]))
        # высота таза: каждая нога длиной L, стопа на высоте подъёма
        need = []
        body['pos'] = [pos[0], 0.0, pos[2]]
        feet = dict(feet)
        hmin = self.L - max_drop                   # ниже таз не садится: дальняя стопа подтягивается к бедру (проворот на носке)
        for leg, _ in self.legs:
            fx, fz, toe, up = feet[leg]
            h, _ = self.hip(o, leg)
            d = math.hypot(fx - h[0], fz - h[2])
            dlim = math.sqrt(max(0.0, self.L ** 2 - max(0.0, hmin - up) ** 2))
            if d > dlim > 0:
                k = dlim / d
                fx, fz = h[0] + (fx - h[0]) * k, h[2] + (fz - h[2]) * k
                feet[leg] = (fx, fz, toe, up)
                d = dlim
            need.append(up + math.sqrt(max(1.0, self.L ** 2 - d * d)) - h[1])     # насколько таз может подняться/должен опуститься
        dy = min(0.0, min(need)) - drop
        pos[1] = dy
        body['pos'] = pos
        for leg, _ in self.legs:
            fx, fz, toe, up = feet[leg]
            h, M = self.hip(o, leg)
            hy = h[1] - up
            d = math.hypot(fx - h[0], fz - h[2])
            dmax = math.sqrt(max(0.0, self.L ** 2 - (hy + sink) ** 2))
            if d < dmax:                                    # нога длиннее, чем нужно (стопа под бедром; у ног нет колена):
                side = M @ np.array([1.0 if leg.startswith('right') else -1.0, 0.0, 0.0])    # стопа уходит в сторону от корпуса
                u = np.array([side[0], side[2]])
                u = u / max(1e-6, np.linalg.norm(u))
                v = np.array([fx - h[0], fz - h[2]])
                vu = float(v @ u)
                e = -vu + math.sqrt(max(0.0, vu * vu - float(v @ v) + dmax * dmax))
                fx, fz = fx + u[0] * e, fz + u[1] * e       # (правка 21.11: раньше — вдоль линии к цели; под бедром линия
                #                                             переворачивалась, и нога щёлкала вперёд-назад за кадр)
            d = math.hypot(fx - h[0], fz - h[2])
            w = np.array([fx - h[0], -math.sqrt(max(0.0, self.L ** 2 - d * d)), fz - h[2]])
            o[leg] = dict(o.get(leg, {}), rot=leg_angles(M.T @ w, M.T @ yaw_dir(toe)))
        return o


def lagged(fn, t, lag, t0=0.0):
    """Запаздывание (overlap): значение параметра на lag секунд раньше."""
    return fn(max(t0, t - lag))
