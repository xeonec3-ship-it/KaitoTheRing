#!/usr/bin/env python3
"""
T28 «Арис» — сборка: модель/текстуры (4 варианта), молот-предмет, анимации (FK/IK, вторичная динамика лент и косы), запись,
затем fx (tools/gen_aris_fx.py) и кадры. Запускается из tools/gen_aris.py (main(G, args)).

Анимации задаются ключевыми позами. Молот в руке задаётся своим положением в мире (точка хвата + направление рукояти «от навершия к
голове» + направление бойка), руки ставятся на рукоять двухзвенным IK (правая — на хват, левая — у навершия), кость hammer
получает поворот/сдвиг относительно предплечья. Ленты, кисти, коса — пружинная симуляция (гравитация + инерция), набедренники
идут за бёдрами. Всё запекается ключами через 0.05 с.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

from nightmare_geo import Anim, euler, to_euler

G = None                 # модуль gen_aris
DT = 0.05


# ================================================================== вектора/повороты
def nrm(v):
    v = np.asarray(v, float)
    return v / max(1e-9, np.linalg.norm(v))


def axis_angle(ax, a):
    ax = nrm(ax)
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K


def align(a, b):
    """Поворот, переводящий направление a в b."""
    a, b = nrm(a), nrm(b)
    v = np.cross(a, b)
    s, c = np.linalg.norm(v), float(np.dot(a, b))
    if s < 1e-9:
        if c > 0:
            return np.eye(3)
        p = np.cross(a, [1, 0, 0])
        if np.linalg.norm(p) < 1e-6:
            p = np.cross(a, [0, 1, 0])
        return axis_angle(p, math.pi)
    return axis_angle(v, math.atan2(s, c))


def quat(M):
    t = np.trace(M)
    if t > 0:
        s = math.sqrt(t + 1) * 2
        return np.array([0.25 * s, (M[2, 1] - M[1, 2]) / s, (M[0, 2] - M[2, 0]) / s, (M[1, 0] - M[0, 1]) / s])
    i = int(np.argmax([M[0, 0], M[1, 1], M[2, 2]]))
    if i == 0:
        s = math.sqrt(1 + M[0, 0] - M[1, 1] - M[2, 2]) * 2
        return np.array([(M[2, 1] - M[1, 2]) / s, 0.25 * s, (M[0, 1] + M[1, 0]) / s, (M[0, 2] + M[2, 0]) / s])
    if i == 1:
        s = math.sqrt(1 + M[1, 1] - M[0, 0] - M[2, 2]) * 2
        return np.array([(M[0, 2] - M[2, 0]) / s, (M[0, 1] + M[1, 0]) / s, 0.25 * s, (M[1, 2] + M[2, 1]) / s])
    s = math.sqrt(1 + M[2, 2] - M[0, 0] - M[1, 1]) * 2
    return np.array([(M[1, 0] - M[0, 1]) / s, (M[0, 2] + M[2, 0]) / s, (M[1, 2] + M[2, 1]) / s, 0.25 * s])


def qmat(q):
    w, x, y, z = q / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def slerp(q0, q1, t):
    d = float(np.dot(q0, q1))
    if d < 0:
        q1, d = -q1, -d
    if d > 0.9995:
        q = q0 + (q1 - q0) * t
        return q / np.linalg.norm(q)
    a = math.acos(d)
    return (math.sin((1 - t) * a) * q0 + math.sin(t * a) * q1) / math.sin(a)


EASE = {
    'linear': lambda t: t,
    'in': lambda t: t * t, 'out': lambda t: 1 - (1 - t) ** 2, 'io': lambda t: t * t * (3 - 2 * t),
    'in3': lambda t: t ** 3, 'out3': lambda t: 1 - (1 - t) ** 3, 'io3': lambda t: 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2,
    'back': lambda t: 1 + 2.2 * (t - 1) ** 3 + 1.2 * (t - 1) ** 2,          # с перелётом
    'step': lambda t: 0.0 if t < 1 else 1.0,
}


# ================================================================== риг: FK
class Rig:
    def __init__(self, m):
        self.m = m
        self.b = {n: (bn.parent, np.array(bn.pivot, float), np.array(bn.rot, float)) for n, bn in m.bones.items()}

    def world(self, pose, upto=None):
        """pose: {кость: {'rot': (x,y,z)°, 'pos': (x,y,z)}} → {кость: (M, o)}: мировая точка = M·x + o (x — координаты покоя)."""
        W = {}

        def get(n):
            if n in W:
                return W[n]
            par, piv, rest = self.b[n]
            p = pose.get(n, {})
            R = euler(rest + np.asarray(p.get('rot', (0, 0, 0)), float))
            t = np.asarray(p.get('pos', (0, 0, 0)), float)
            # локально: x → t + piv + R(x − piv)
            Ml, ol = R, t + piv - R @ piv
            if par:
                Mp, op = get(par)
                W[n] = (Mp @ Ml, Mp @ ol + op)
            else:
                W[n] = (Ml, ol)
            return W[n]
        for n in (upto or self.b):
            get(n)
        return W


def apply(X, p):
    return X[0] @ np.asarray(p, float) + X[1]


# ================================================================== IK руки (двухзвенная, локоть по шарниру x предплечья)
def solve_arm(rig, pose, side, target, pole):
    """Ставит руку side ('right'/'left') так, чтобы центр кулака пришёл в target (мир). Пишет rot в pose. Возвращает невязку."""
    sx = 1 if side == 'right' else -1
    arm, fore = side + '_arm', side + '_forearm'
    S = np.array(G.SHOULDER_R) * [sx, 1, 1]
    E0 = np.array(G.ELBOW_R) * [sx, 1, 1]
    F0 = np.array(G.FIST_R) * [sx, 1, 1]
    T = np.asarray(target, float)
    for it in range(4):
        W = rig.world(pose, ['body'])
        Mb, ob = W['body']
        Tl = Mb.T @ (T - ob)                       # цель в координатах body
        pl = Mb.T @ np.asarray(pole, float)
        u, l = E0 - S, F0 - E0
        D = Tl - S
        d = np.linalg.norm(D)
        f = lambda b: np.linalg.norm(u + euler((math.degrees(b), 0, 0)) @ l)
        lo, hi = 0.0, math.radians(160)
        dmax, dmin = f(lo), f(hi)
        d = min(max(d, dmin + 1e-3), dmax - 1e-3)
        for _ in range(40):
            mid = (lo + hi) / 2
            if f(mid) > d:
                lo = mid
            else:
                hi = mid
        beta = (lo + hi) / 2
        v = u + euler((math.degrees(beta), 0, 0)) @ l
        R0 = align(v, D)
        Dn = nrm(D)
        e0 = R0 @ u
        e_perp = e0 - Dn * np.dot(e0, Dn)
        p_perp = pl - Dn * np.dot(pl, Dn)
        if np.linalg.norm(e_perp) > 1e-6 and np.linalg.norm(p_perp) > 1e-6:
            a, b_ = nrm(e_perp), nrm(p_perp)
            ang = math.atan2(np.dot(np.cross(a, b_), Dn), np.dot(a, b_))
            R0 = axis_angle(Dn, ang) @ R0
        pose[arm] = {'rot': to_euler(R0)}
        pose[fore] = {'rot': (math.degrees(beta), 0, 0)}
        W = rig.world(pose, [fore])
        got = apply(W[fore], F0)
        err = T - got
        if np.linalg.norm(err) < 0.05:
            break
        T = T + err * 0.0   # без коррекции: невязка = недотягивание
        break
    return float(np.linalg.norm(np.asarray(target) - got))


# ================================================================== молот: положение в мире
def ham_R(d, f):
    """Поворот молота: локальная −z (к голове) → d, локальная +x (боёк) → f (ортогонализуется)."""
    d = nrm(d)
    f = np.asarray(f, float)
    f = nrm(f - d * np.dot(f, d))
    y = np.cross(-d, f)
    return np.stack([f, y, -d], 1)


def ham_from_strike(point, d, f):
    """Хват, при котором центр ударной плоскости бойка (+x) приходит в point."""
    d = nrm(d)
    R = ham_R(d, f)
    off = R @ np.array([G.HAM_FACE * G.HAM_S, 0, -(G.HAM_HEAD - G.HAM_GRIP) * G.HAM_S])
    return np.asarray(point, float) - off


# ================================================================== ключевые позы → запечённые ключи
JOINTS = ('body', 'torso', 'head', 'right_leg', 'left_leg', 'right_shin', 'left_shin', 'larm', 'lfore', 'rarm', 'rfore')
ALIAS = {'larm': 'left_arm', 'lfore': 'left_forearm', 'rarm': 'right_arm', 'rfore': 'right_forearm'}


class K:
    """Ключевая поза в момент t. Поля: углы суставов (BB, °), bpos — сдвиг body, ham = (хват, d, f, frame), lh — вес левой руки
    на рукояти (0..1), rpole/lpole — куда смотрит локоть, hg — {'rot','pos'} молота на земле, vis — (молот в руке, на земле),
    ease — плавность сегмента, приходящего в этот ключ."""

    def __init__(self, t, ease='io', **kw):
        self.t, self.ease, self.kw = t, ease, kw


def lerp(a, b, k):
    return np.asarray(a, float) * (1 - k) + np.asarray(b, float) * k


DEF = {'bpos': (0, 0, 0), 'lh': 0.0, 'rpole': (0.6, -0.2, 0.8), 'lpole': (-0.6, -0.2, 0.8), 'vis': (1, 0),
       'hg': {'rot': (0, 0, 0), 'pos': (0, 0, 0)}, 'rslide': 0.0, 'wind': 0.0}


def interp(keys, t):
    """Поза в момент t (поля заполняются от предыдущих ключей: если поле не задано в ключе — держится прошлое)."""
    full = []
    cur = {}
    for k in keys:
        cur = dict(cur)
        cur.update(k.kw)
        full.append((k.t, k.ease, cur))
    if t <= full[0][0]:
        return dict(full[0][2])
    if t >= full[-1][0]:
        return dict(full[-1][2])
    i = 0
    while full[i + 1][0] < t:
        i += 1
    (t0, _, a), (t1, e, b) = full[i], full[i + 1]
    k = EASE[e]((t - t0) / (t1 - t0))
    out = {}
    for name in set(a) | set(b):
        va, vb = a.get(name, b.get(name)), b.get(name, a.get(name))
        if name == 'ham':
            if va is None or vb is None:
                out[name] = vb if k > 0.5 else va
                continue
            fr = va[3] if len(va) > 3 else 'root'
            ga, gb = np.asarray(va[0], float), np.asarray(vb[0], float)
            qa, qb = quat(ham_R(va[1], va[2])), quat(ham_R(vb[1], vb[2]))
            R = qmat(slerp(qa, qb, k))
            out[name] = (lerp(ga, gb, k), -R[:, 2], R[:, 0], fr)
        elif name == 'hg':
            out[name] = {c: lerp(va.get(c, (0, 0, 0)), vb.get(c, (0, 0, 0)), k) for c in ('rot', 'pos')}
        elif name == 'vis':
            out[name] = vb if k >= 1 - 1e-6 else va
        else:
            out[name] = lerp(va, vb, k)
    return out


def resolve(rig, P, report=None):
    """Поза-описание → поза рига {кость: {rot, pos, scale}}."""
    pose = {}
    for j in JOINTS:
        if j in P:
            pose[ALIAS.get(j, j)] = {'rot': tuple(P[j])}
    pose.setdefault('body', {})['pos'] = tuple(P.get('bpos', (0, 0, 0)))
    vis = P.get('vis', DEF['vis'])
    hg = P.get('hg', DEF['hg'])
    pose['hammer_ground'] = {'rot': tuple(hg['rot']), 'pos': tuple(hg['pos']), 'scale': (1, 1, 1) if vis[1] else (0, 0, 0)}
    ham = P.get('ham')
    if ham is not None:
        g, d, f = np.asarray(ham[0], float), nrm(ham[1]), np.asarray(ham[2], float)
        fr = ham[3] if len(ham) > 3 else 'root'
        if fr == 'body':                                    # задано в координатах body (носит на плече: качается вместе с телом)
            Wb = rig.world(pose, ['body'])['body']
            g, d, f = apply(Wb, g), Wb[0] @ d, Wb[0] @ f
        R = ham_R(d, f)
        slide = float(P.get('rslide', 0.0))
        hand = g + nrm(d) * slide
        rmanual = {a_: dict(pose.get(a_, {})) for a_ in ('right_arm', 'right_forearm')}
        e1 = solve_arm(rig, pose, 'right', hand, P.get('rpole', DEF['rpole']))
        rh = float(P.get('rh', 1.0))
        if rh < 0.999:                                       # рука отпускает рукоять: смесь IK и ручной позы
            for a_ in ('right_arm', 'right_forearm'):
                ik = np.asarray(pose[a_]['rot'], float)
                mn = np.asarray(rmanual[a_].get('rot', (0, 0, 0)), float)
                pose[a_]['rot'] = tuple(unwrap_to(mn, ik) * rh + mn * (1 - rh))
            e1 = 0.0
        lh = float(P.get('lh', 0.0))
        e2 = 0.0
        if lh > 0.001:
            lt = g + R @ np.array([0, 0, (G.HAM_GRIP - G.HAM_GRIP2) * G.HAM_S])
            manual = {a: dict(pose.get(a, {})) for a in ('left_arm', 'left_forearm')}
            e2 = solve_arm(rig, pose, 'left', lt, P.get('lpole', DEF['lpole']))
            if lh < 0.999:
                for a in ('left_arm', 'left_forearm'):
                    ik = np.asarray(pose[a]['rot'], float)
                    mn = np.asarray(manual[a].get('rot', (0, 0, 0)), float)
                    pose[a]['rot'] = tuple(unwrap_to(mn, ik) * lh + mn * (1 - lh))
        W = rig.world(pose, ['right_forearm'])
        Mf, of = W['right_forearm']
        Rl = Mf.T @ R
        pos = Mf.T @ (g - of) - np.array(G.FIST_R)
        pose['hammer'] = {'rot': tuple(to_euler(Rl)), 'pos': tuple(pos), 'scale': (1, 1, 1) if vis[0] else (0, 0, 0)}
        if report is not None and vis[0]:
            report.append((e1, e2))
    else:
        pose['hammer'] = {'rot': (0, 0, 0), 'pos': (0, 0, 0), 'scale': (1, 1, 1) if vis[0] else (0, 0, 0)}
    return pose


def unwrap_to(ref, a):
    return ref + (np.asarray(a) - ref + 180) % 360 - 180


# ---------------------------------------------------------------- земля: ноги не проваливаются
FOOT_PTS = [(2, 0, -4.5), (2, 0, 2.25), (0, 0, -3.5), (4, 0, 2.25)]
KNEE_PT = (2, 5.0, -2.4)


def ground_fix(rig, pose, mode):
    """mode 'feet' — поднять/опустить тело, чтобы нижняя точка стоп была на 0; 'kneel' — с учётом колена."""
    W = rig.world(pose)
    ys = []
    for side, sx in (('right', 1), ('left', -1)):
        X = W[side + '_shin']
        for p in FOOT_PTS:
            ys.append(apply(X, (p[0] * sx, p[1], p[2]))[1])
        if mode == 'kneel':
            ys.append(apply(X, (KNEE_PT[0] * sx, KNEE_PT[1] - 2.0, KNEE_PT[2]))[1])
    dy = -min(ys)
    bp = np.asarray(pose['body'].get('pos', (0, 0, 0)), float) + [0, dy, 0]
    pose['body']['pos'] = tuple(bp)


# ---------------------------------------------------------------- вторичная динамика (ленты, кисти, коса)
CHAINS = [  # (кость, следующая точка цепи в покое — задаёт «вниз» кости), жёсткость, затухание
    ('ribbon_r1', 'ribbon_r2'), ('ribbon_r2', 'ribbon_r3'), ('ribbon_r3', None),
    ('ribbon_l1', 'ribbon_l2'), ('ribbon_l2', 'ribbon_l3'), ('ribbon_l3', None),
    ('hair1', 'hair2'), ('hair2', 'hair3'), ('hair3', None),
    ('tassel_r', None), ('tassel_l', None),
]


class Spring:
    def __init__(self, v):
        self.x = np.asarray(v, float)
        self.v = np.zeros(3)

    def step(self, target, k=90.0, c=11.0, dt=DT):
        a = k * (np.asarray(target) - self.x) - c * self.v
        self.v = self.v + a * dt
        self.x = self.x + self.v * dt
        return self.x


def secondary(rig, poses, times, loop, wind=0.0):
    """Ленты/коса висят по гравитации с инерцией (пружина на направлении), набедренники — за бёдрами."""
    m = rig.m
    down = np.array([0, -1.0, 0])
    springs = {}
    prev_tip = {}
    passes = 2 if loop else 1
    for ps in range(passes):
        for idx, (t, pose) in enumerate(zip(times, poses)):
            # набедренники и задняя пластина
            for side in ('right', 'left'):
                lr = np.asarray(pose.get(side + '_leg', {}).get('rot', (0, 0, 0)), float)
                a = min(32.0, 0.8 * max(0.0, lr[0])) + 0.2 * min(0.0, lr[0])     # юбка идёт за бедром, но свисает (на колене — не торчит)
                pose['tasset_' + side[0]] = {'rot': (a, 0, (1 if side == 'right' else -1) * max(0.0, abs(lr[2]) * 0.6))}
            back = min(0.0, *(float(pose.get(s + '_leg', {}).get('rot', (0, 0, 0))[0]) for s in ('right', 'left')))
            pose['fauld_b'] = {'rot': (0.7 * back, 0, 0)}
            for bone, nxt in CHAINS:
                W = rig.world(pose, [m.bones[bone].parent])
                Mp, op = W[m.bones[bone].parent]
                piv = m.bones[bone].pivot
                if nxt:
                    tip_rest = m.bones[nxt].pivot
                else:
                    cs = m.bones[bone].cubes
                    lo = min(c.frm[1] for c in cs)
                    tip_rest = np.array([piv[0], lo, piv[2]])
                rest_dir = nrm(tip_rest - piv)
                world_piv = apply((Mp, op), piv)
                key = bone
                vel = np.zeros(3)
                if key in prev_tip:
                    vel = (world_piv - prev_tip[key]) / DT
                prev_tip[key] = world_piv
                sway = wind * np.array([math.sin(t * 2.1 + hash(bone) % 7), 0, 0.6 * math.cos(t * 1.7 + hash(bone) % 5)])
                desired = nrm(down * 9.0 - vel * 0.12 + sway)
                # кость не уходит внутрь тела: ограничение по родителю (не дальше 75° от покоя)
                par_rest_world = nrm(Mp @ rest_dir)
                ang = math.acos(max(-1, min(1, np.dot(desired, par_rest_world))))
                lim = math.radians(70)
                if ang > lim:
                    ax = np.cross(par_rest_world, desired)
                    if np.linalg.norm(ax) > 1e-6:
                        desired = axis_angle(ax, lim) @ par_rest_world
                if key not in springs:
                    springs[key] = Spring(desired)
                    springs[key].x = desired.copy()
                dirw = nrm(springs[key].step(desired, k=70.0 if bone.startswith('hair') else 110.0, c=9.0 if bone.startswith('hair') else 12.0))
                local = Mp.T @ dirw
                R = align(rest_dir, local)
                pose[bone] = {'rot': tuple(to_euler(R))}
    return poses


# ---------------------------------------------------------------- запекание
def bake(rig, name, length, keys, loop=True, ground=None, wind=0.0, events=None, sounds=None, extra=None):
    """keys → Anim (animation.aris.<name>). ground: None | 'feet' | 'kneel' | функция(t)->режим."""
    n = int(round(length / DT))
    times = [i * DT for i in range(n + 1)]
    poses = []
    rep = []
    bad = []
    for t in times:
        P = interp(keys, t)
        n0 = len(rep)
        pose = resolve(rig, P, rep)
        if len(rep) > n0 and max(rep[-1]) > 0.8:
            bad.append((round(t, 2), round(rep[-1][0], 1), round(rep[-1][1], 1)))
        gm = ground(t) if callable(ground) else ground
        if gm:
            ground_fix(rig, pose, gm)
        if extra:
            extra(t, pose, P)
        poses.append(pose)
    secondary(rig, poses, times, loop, wind)
    a = Anim('animation.aris.' + name, length, loop=loop)
    last = {}
    for t, pose in zip(times, poses):
        for bone, ch in pose.items():
            for c, v in ch.items():
                v = np.asarray(v, float)
                if c == 'rot':
                    if (bone, c) in last:
                        v = unwrap_to(last[(bone, c)], v)
                    last[(bone, c)] = v
                a.key(bone, c, t, v)
    for t, e in (events or {}).items():
        a.instruction(t, e)
    for t, e in (sounds or {}).items():
        a.sound(t, e)
    if rep:
        worst = max(max(r) for r in rep)
        if worst > 0.8:
            print('  ! %s: рука не дотягивается до рукояти на %.1f ед.' % (name, worst), bad[:3], '…', bad[-2:])
    return compact(a)


def compact(a):
    """Убирает лишние ключи: постоянные каналы → один ключ; почти линейные участки прореживаются."""
    for bone in list(a.keys):
        for ch in list(a.keys[bone]):
            kf = a.keys[bone][ch]
            ts = sorted(kf)
            vals = np.array([kf[t] for t in ts])
            if np.all(np.abs(vals - vals[0]) < 1e-3):
                if ch in ('rot', 'pos') and np.all(np.abs(vals[0]) < 1e-3):
                    del a.keys[bone][ch]
                else:
                    a.keys[bone][ch] = {ts[0]: list(vals[0])}
                continue
            keep = [0]
            for i in range(1, len(ts) - 1):
                t0, t1, t2 = ts[keep[-1]], ts[i], ts[i + 1]
                v0, v2 = vals[keep[-1]], vals[i + 1]
                pred = v0 + (v2 - v0) * (t1 - t0) / (t2 - t0)
                tol = 0.25 if ch == 'rot' else 0.03
                if np.any(np.abs(pred - vals[i]) > tol) or ch == 'scale':
                    keep.append(i)
            keep.append(len(ts) - 1)
            a.keys[bone][ch] = {ts[i]: list(vals[i]) for i in keep}
        if not a.keys[bone]:
            del a.keys[bone]
    return a


# ================================================================== запись модели и текстур
def write_model(m):
    G.write_json('geo/entity/aris.geo.json', m.geo_json(), compact=True)
    names = {'base': 'aris', 'dim': 'aris_dim', 'spent': 'aris_spent', 'mythic': 'aris_mythic'}
    for v in G.VARIANTS:
        G.V['variant'] = v
        m.paint()
        m.image.save(G.out(G.TEXD + names[v] + '.png'), optimize=True)
        m.glow.save(G.out(G.TEXD + names[v] + '_glowmask.png'), optimize=True)
    G.V['variant'] = 'base'
    m.paint()


def share_hammer_uv(m):
    """hammer_ground — та же геометрия, что hammer: те же UV (атлас меньше; покраска граней молота не зависит от места)."""
    for c in m.bones['hammer_ground'].cubes:
        c.info['skin'] = True
    m.pack()
    for a, b in zip(m.bones['hammer'].cubes, m.bones['hammer_ground'].cubes):
        b.uv, b.px = a.uv, {}


# ================================================================== предмет-молот (models/item/aris_hammer.json)
def write_item():
    mats = ['hk', 'hd', 'hs', 'hs2', 'hsh', 'hg', 'hw', 'hst']
    # палитра: каждому материалу — 4 тона (ручная светотень по граням: верх, перед/зад, бока, низ)
    pal = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    tones = {'hk': (G.DARK, 0.25), 'hd': (G.DARK, 0.62), 'hs': (G.STEEL, 0.5), 'hs2': (G.STEEL, 0.66), 'hsh': (G.DARK, 0.45),
             'hg': (G.TEAL, 0.66), 'hw': (G.PURP, 0.58), 'hst': (G.STONE, 0.6)}
    cell = {}
    glow_cells = []
    for mi, mk in enumerate(mats):
        r, base = tones[mk]
        for fi, (fn, dv) in enumerate((('up', 0.16), ('ns', 0.0), ('ew', -0.08), ('down', -0.22))):
            c = G.pick(r, base + dv)
            pal.putpixel((fi, mi), tuple(int(x * 255 + 0.5) for x in c) + (255,))
            cell[(mk, fn)] = (fi, mi)
            if mk == 'hg':
                glow_cells.append(mi * 16 + fi)
    pal.save(G.out('textures/item/aris_hammer_3d.png'))
    els = []
    S, OX = 0.9, 8.0
    for (cx, cy, cz, sx, sy, sz, mat, rz_) in G.hammer_parts():
        fr = [OX + (cx - sx / 2) * S, (cy - sy / 2) * S, OX + (cz - sz / 2) * S]
        to = [OX + (cx + sx / 2) * S, (cy + sy / 2) * S, OX + (cz + sz / 2) * S]
        faces = {}
        for f in ('north', 'south', 'east', 'west', 'up', 'down'):
            fn = {'north': 'ns', 'south': 'ns', 'east': 'ew', 'west': 'ew', 'up': 'up', 'down': 'down'}[f]
            u, v = cell[(mat, fn)]
            faces[f] = {'uv': [u + 0.25, v + 0.25, u + 0.75, v + 0.75], 'texture': '#p'}
        e = {'from': [round(x, 3) for x in fr], 'to': [round(x, 3) for x in to], 'faces': faces}
        if rz_:
            e['rotation'] = {'axis': 'z', 'angle': rz_, 'origin': [round(OX + cx * S, 3), round(cy * S, 3), round(OX + cz * S, 3)]}
        if mat == 'hg':
            for f in faces.values():
                f['emissivity'] = 15                       # Forge: бирюзовые вставки светятся (полная яркость)
        els.append(e)
    disp = {   # рукоять вдоль +y; хват — верх обмотки (y ≈ 7.1 предмета ×0.9): двуручный молот, держат за низ рукояти
        'thirdperson_righthand': {'rotation': [0, 90, 0], 'translation': [0, 4.5, 1.5], 'scale': [1.0, 1.0, 1.0]},
        'thirdperson_lefthand': {'rotation': [0, -90, 0], 'translation': [0, 4.5, 1.5], 'scale': [1.0, 1.0, 1.0]},
        'firstperson_righthand': {'rotation': [-10, 90, 20], 'translation': [2.5, 3.0, 0], 'scale': [0.6, 0.6, 0.6]},
        'firstperson_lefthand': {'rotation': [-10, -90, -20], 'translation': [2.5, 3.0, 0], 'scale': [0.6, 0.6, 0.6]},
        'gui': {'rotation': [20, -45, -40], 'translation': [1.5, -3.5, 0], 'scale': [0.42, 0.42, 0.42]},
        'ground': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [0.35, 0.35, 0.35]},
        'fixed': {'rotation': [0, 0, -45], 'translation': [2, -2, 0], 'scale': [0.45, 0.45, 0.45]},
        'head': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [0.6, 0.6, 0.6]},
    }
    doc = {'credit': 'T28 Молот Арис — tools/gen_aris.py (форма по docs/references/t28/aris_hammer.jpg, палитра Арис)',
           'textures': {'p': 'pohsmp_core:item/aris_hammer_3d', 'particle': 'pohsmp_core:item/aris_hammer_3d'},
           'gui_light': 'side', 'elements': els, 'display': disp}
    G.write_json('models/item/aris_hammer.json', doc)
    import aris_render
    aris_render.GLOW_CELLS[:] = glow_cells
    return len(els)


# ================================================================== main
def main(gmod, args):
    global G
    G = gmod
    m = G.build_model()
    share_hammer_uv(m)
    write_model(m)
    nel = write_item()
    rig = Rig(m)
    import aris_anims_def as D
    D.G, D.AN = G, sys.modules[__name__]
    anims = D.all_anims(rig)
    G.write_json('animations/entity/aris.animation.json',
                 {'format_version': '1.8.0', 'animations': {a.name: a.to_json() for a in anims}}, compact=True)
    print('aris: костей %d, кубов %d, атлас %s, молот-предмет %d брусков, анимаций %d'
          % (len(m.bones), sum(len(b.cubes) for b in m.bones.values()), m.tex_px, nel, len(anims)))
    import gen_aris_fx as FX
    FX.run(G, sys.modules[__name__], args, anims)
    import aris_render as R
    if '--html' in args:
        R.write_html()
    if '--shots' in args:
        import aris_shots
        aris_shots.run(G, args)
