#!/usr/bin/env python3
"""
T32 «Сломать блок» — общий модуль для боссов на каркасе мага Iron's (Ирина, Эреб, «Эреб, Длань Лжи», Глава Культа):
поза задаётся ЦЕЛЯМИ в мире (таз, повороты корпуса, точки стоп на земле, кисть и направление оружия, левая кисть на древке),
а углы костей подбираются численно в той же прямой кинематике, что у проверки и превью (tools/anim_check.py: GeckoLib-JSON →
Euler ZYX, x модели отражён). Поэтому знаки X/Y не переворачиваются ни разу (ошибка прошлого — двойной переворот) — что решено,
то и окажется в файле; итог проверяется кадрами и tools/guard_break_check.py.

Оси целей (мир «R» = мир anim_check): босс в начале координат смотрит в −z, x — ВПРАВО от него, y — вверх; единицы — пиксели модели (16 = блок
при масштабе 1). В JSON (как у Iron's, см. gen_ereb_anims): body.rot y > 0 — поворот к своей правой стороне, body.rot x > 0 —
наклон вперёд; эти углы корпуса пишутся прямо (они простые), всё остальное — решателями.

Темп — как у пилота T29 (gen_martin_ef.STime, anim_body.Keys): тело ключевыми позами с кривыми, оружие — путь по параметру s и
профиль скорости s(t). Ключи запекаются через 0.02 с (GeckoLib между ключами — линейно).
"""
import json
import math
import os

import numpy as np

import anim_check as AC
from anim_check import T, Rx, Ry, Rz, S, ap

A = AC.A
D = math.pi / 180

BOSS = {
    'irina': dict(geo='irina', item='irina_staff', scale=1.0, chest='torso'),
    'ereb': dict(geo='ereb', item='ereb_rapier', scale=1.0, chest='torso'),
    'ereb_hand': dict(geo='ereb_hand', item='ereb_hand_rapier', scale=1.0, chest='torso'),
    # hand2: предмет в руке рисуется GeckoLib 4.8.4 с поворотом кисти ДВАЖДЫ (BlockAndItemGeoLayer.renderForBone, письмо
    # docs/inbox/2026-11-21_mgr_t26_hold_tyros.md §1; anim_check.Model.item_world). Включено у Главы; Ирина/Эреб/Длань — по решению
    # помощника по хвату (их guard_break он перепроверяет), флаг тот же.
    'cult_leader': dict(geo='cult_leader', item='cult_scythe', scale=1.75, chest='torso', hand2=True),
    # Арис — своя модель (голени, предплечья), молот — кость hammer; только для проверки метрик (анимацию пишет gen_aris_anims)
    'aris': dict(geo='aris', item=None, scale=1.0, chest='torso', weapon_bone='hammer', shin=True),
}


def flip(p):
    """Мир anim_check → R-мир. Проверено 21.11 по FK: правая рука (bipedHandRight) в мире anim_check на +x, поворот body.y > 0
    (к своей правой стороне) уводит перед корпуса в +x, рука x −90 — кисть вперёд (−z) и вверх: это и есть R-мир (x — вправо).
    Перевод — тождественный (подпись «x — влево» в anim_check относится к виду камеры превью, не к осям)."""
    return np.asarray(p, float)


def nrm(v):
    v = np.asarray(v, float)
    return v / max(1e-9, np.linalg.norm(v))


def yaw_dir(yaw, pitch=0.0):
    """R-мир: yaw 0 — вперёд (−z), + — вправо; pitch + — вверх (градусы)."""
    y, p = math.radians(yaw), math.radians(pitch)
    return np.array([math.sin(y) * math.cos(p), math.sin(p), -math.cos(y) * math.cos(p)])


def cyl(phi, r, y):
    """Точка вокруг вертикали: phi 0 — перед, + — вправо."""
    return np.array([math.sin(math.radians(phi)) * r, y, -math.cos(math.radians(phi)) * r])


class JModel:
    """Модель из geo.json + предмет в правой руке (Iron's HumanoidRenderer: bipedHandRight → −1/16 z, −1/16 y, X −90°, display)."""

    def __init__(self, boss, anims=None):
        c = BOSS[boss]
        self.boss, self.scale, self.chest = boss, c['scale'], c['chest']
        self.hand2 = bool(c.get('hand2'))
        g = json.load(open(os.path.join(A, 'geo', 'entity', c['geo'] + '.geo.json'), encoding='utf-8'))['minecraft:geometry'][0]
        self.bones = {}
        for b in g['bones']:
            piv = np.array([-b['pivot'][0], b['pivot'][1], b['pivot'][2]], float)
            r = b.get('rotation') or [0, 0, 0]
            cubes = []
            for cu in b.get('cubes', []):
                inf = cu.get('inflate', 0)
                o, s = cu['origin'], cu['size']
                lo = np.array([-(o[0] + s[0]) - inf, o[1] - inf, o[2] - inf])
                hi = np.array([-o[0] + inf, o[1] + s[1] + inf, o[2] + s[2] + inf])
                cp = np.array([-cu['pivot'][0], cu['pivot'][1], cu['pivot'][2]]) if cu.get('pivot') else piv
                hm = T(*(cp - piv))
                if cu.get('rotation'):
                    q = cu['rotation']
                    hm = hm @ Rz(q[2] * D) @ Ry(-q[1] * D) @ Rx(-q[0] * D)
                cubes.append((hm, lo - cp, hi - cp))
            self.bones[b['name']] = dict(piv=piv, rest=[-r[0] * D, -r[1] * D, r[2] * D], parent=b.get('parent'), cubes=cubes)
        for n, b in self.bones.items():
            pp = self.bones[b['parent']]['piv'] if b['parent'] else np.zeros(3)
            b['base'] = b['piv'] - pp
        # длина ноги: от шарнира до низа кубов кости ноги
        lp = self.bones['right_leg']['piv']
        self.leg_len = float(lp[1])
        self.scale = c['scale'] * self.leg_len / 12.0        # рост относительно игрока (нога игрока 12 px = 0.75 бл.)
        self.foot = (0.0, -self.leg_len, 0.0)
        self.foot_bones = {'right_leg': 'right_leg', 'left_leg': 'left_leg'}
        if c.get('shin'):                                   # нога из двух звеньев: стопа — низ голени
            self.foot_bones = {'right_leg': 'right_shin', 'left_leg': 'left_shin'}
            self.foot_of = {k: (0.0, -self.bones[v]['piv'][1], 0.0) for k, v in self.foot_bones.items()}
        self.anims = anims if anims is not None else self._load_anims()
        self.special = {}
        self.weapon_bone = c.get('weapon_bone')
        if self.weapon_bone:                                # оружие-кость: точка удара — центр дальних брусков (голова молота)
            b = self.bones[self.weapon_bone]
            ctr = []
            for hm, lo, hi in b['cubes']:
                ctr.append(ap(hm, (lo + hi) / 2))
            ctr = np.array(ctr)
            far = ctr[np.linalg.norm(ctr, axis=1) > 0.75 * np.max(np.linalg.norm(ctr, axis=1))]
            self.special['strike'] = (np.zeros(3), far.mean(axis=0))
            self.item_hand = np.zeros((1, 3))
            self.axis_far = far.mean(axis=0)
            return
        # предмет
        doc = json.load(open(os.path.join(A, 'models', 'item', c['item'] + '.json'), encoding='utf-8'))
        doc = doc.get('base', doc)
        d = doc['display']['thirdperson_righthand']
        tr, rot, sc = d.get('translation', [0, 0, 0]), d.get('rotation', [0, 0, 0]), d.get('scale', [1, 1, 1])
        self.item_m = (T(0, -1, -1) @ Rx(-math.pi / 2) @ T(*tr) @ Rx(rot[0] * D) @ Ry(rot[1] * D) @ Rz(rot[2] * D) @ S(*sc) @ T(-8, -8, -8))
        pts = []
        for e in doc['elements']:
            a, b = np.array(e['from'], float), np.array(e['to'], float)
            m = np.eye(4)
            if e.get('rotation'):
                ro = e['rotation']
                o = np.array(ro['origin'], float)
                R = {'x': Rx, 'y': Ry, 'z': Rz}[ro['axis']](ro['angle'] * D)
                m = T(*o) @ R @ T(*-o)
            for f in (0.0, 0.5, 1.0):
                for ax in range(3):
                    p = (a + b) / 2
                    p[ax] = a[ax] + (b[ax] - a[ax]) * f
                    pts.append(ap(m, p))
        self.item_pts = np.array(pts)
        hp = np.array([ap(self.item_m, p) for p in self.item_pts])     # в осях кисти (bipedHandRight)
        self.item_hand = hp
        # ось предмета: от кисти к самой дальней точке
        far = hp[int(np.argmax(np.linalg.norm(hp, axis=1)))]
        self.axis_far = far
        self.anims = anims if anims is not None else self._load_anims()
        self.special = {}                  # точки, заданные боссом: {'tip': p (оси кисти), 'butt': p, ...}

    def _load_anims(self):
        p = os.path.join(A, 'animations', 'entity', BOSS[self.boss]['geo'] + '.animation.json')
        return json.load(open(p, encoding='utf-8'))['animations'] if os.path.exists(p) else {}

    # ------------------------------------------------------------ прямая кинематика (как anim_check.Model.world)
    def world_pose(self, pose):
        """pose: {кость: {'rotation': [..], 'position': [..]}} — значения как в JSON. → {кость: мировая матрица (мир anim_check)}."""
        W = {}

        def wm(n):
            if n in W:
                return W[n]
            b = self.bones[n]
            bp = pose.get(n, {})
            r = bp.get('rotation', (0, 0, 0))
            p = bp.get('position', (0, 0, 0))
            rest = b['rest']
            m = T(b['base'][0] - p[0], b['base'][1] + p[1], b['base'][2] + p[2]) @ \
                Rz(rest[2] + r[2] * D) @ Ry(rest[1] - r[1] * D) @ Rx(rest[0] - r[0] * D)
            par = b['parent']
            W[n] = (wm(par) if par else np.eye(4)) @ m
            return W[n]
        for n in self.bones:
            wm(n)
        return W

    def chain(self, pose, name):
        """Матрица одной кости (только цепочка родителей) — быстро для решателей."""
        ch = []
        n = name
        while n:
            ch.append(n)
            n = self.bones[n]['parent']
        M = np.eye(4)
        for n in reversed(ch):
            b = self.bones[n]
            bp = pose.get(n, {})
            r = bp.get('rotation', (0, 0, 0))
            p = bp.get('position', (0, 0, 0))
            rest = b['rest']
            M = M @ T(b['base'][0] - p[0], b['base'][1] + p[1], b['base'][2] + p[2]) @ \
                Rz(rest[2] + r[2] * D) @ Ry(rest[1] - r[1] * D) @ Rx(rest[0] - r[0] * D)
        return M

    def hand_rot(self, pose):
        """Поворот кости bipedHandRight (4×4, у шарнира) — второй раз GeckoLib поворачивает им предмет (если hand2)."""
        if not self.hand2:
            return np.eye(4)
        b = self.bones['bipedHandRight']
        r = pose.get('bipedHandRight', {}).get('rotation', (0, 0, 0))
        rest = b['rest']
        return Rz(rest[2] + r[2] * D) @ Ry(rest[1] - r[1] * D) @ Rx(rest[0] - r[0] * D)

    def item_frame(self, pose, W=None):
        """Матрица, которой рисуется предмет в правой руке (мир): кисть [· поворот кисти ещё раз]."""
        Mh = W['bipedHandRight'] if W is not None else self.chain(pose, 'bipedHandRight')
        return Mh @ self.hand_rot(pose)

    def world(self, an, t):
        pose = {}
        for n, bk in an['bones'].items():
            if n not in self.bones:
                continue
            q = {}
            if 'rotation' in bk:
                q['rotation'] = AC.chan_at(bk['rotation'], t)
            if 'position' in bk:
                q['position'] = AC.chan_at(bk['position'], t)
            pose[n] = q
        W = self.world_pose(pose)
        W['~item'] = self.item_frame(pose, W)
        for n, bk in an['bones'].items():           # скрытые кости (scale 0) — как у GeckoLib
            if n in W and 'scale' in bk:
                s = AC.chan_at(bk['scale'], t)
                if not isinstance(s, list):
                    s = [s] * 3
                if max(s) < 1e-3:
                    W[n] = W[n] @ np.diag([1e-4, 1e-4, 1e-4, 1.0])
        return W

    def item_world(self, W):
        m = W.get('~item', W['bipedHandRight'])
        return np.array([ap(m, p) for p in self.item_hand])

    def foot_pt(self, W, leg):
        if hasattr(self, 'foot_of'):
            return ap(W[self.foot_bones[leg]], self.foot_of[leg])
        return ap(W[leg], self.foot)

    def strike_pts(self, W):
        """(основание, точка удара) — R-мир, для метрик."""
        m = W[self.weapon_bone] if getattr(self, 'weapon_bone', None) else W.get('~item', W['bipedHandRight'])
        a, b = self.special.get('strike', (np.zeros(3), self.axis_far))
        return flip(ap(m, a)), flip(ap(m, b))

    def inside(self, W, bone, pts, margin=0.4):
        res = np.zeros(len(pts), bool)
        for hm, lo, hi in self.bones[bone]['cubes']:
            if np.prod(hi - lo) < 1:
                continue
            inv = np.linalg.inv(W[bone] @ hm)
            q = (inv[:3, :3] @ pts.T).T + inv[:3, 3]
            res |= np.all((q > lo + margin) & (q < hi - margin), axis=1)
        return res


_MODELS = {}


def model(boss):
    if boss not in _MODELS:
        _MODELS[boss] = JModel(boss)
        import importlib
        try:
            mod = importlib.import_module('guard_break_' + boss)
            if hasattr(mod, 'special'):
                _MODELS[boss].special = mod.special(_MODELS[boss])
        except ImportError:
            pass
    return _MODELS[boss]


# ================================================================== решатели
def descend(f, x, step, iters=200, tol=0.02):
    """Покоординатный спуск (как в gen_martin.solve_arm): без scipy."""
    x = np.array(x, float)
    best = f(x)
    n = len(x)
    while step > tol and iters > 0:
        iters -= 1
        imp = False
        for k in range(n):
            for d in (step, -step):
                y = x.copy()
                y[k] += d
                e = f(y)
                if e < best:
                    best, x, imp = e, y, True
        if not imp:
            step *= 0.5
    return x, best


class Solver:
    """Покадровый решатель позы с переносом решения с прошлого кадра (без скачков между ветвями)."""

    def __init__(self, M):
        self.M = M
        self.prev = {}

    def reset(self):
        self.prev = {}

    # ---------------- стопы: таз опускается, чтобы дальняя стопа доставала (ноги без колена), стопы — в точках на земле
    def legs(self, pose, feet, drop=0.0, max_drop=3.0):
        """feet: {нога: (x, z, toe_yaw, подъём)} — R-мир. Пишет body.position[1] и углы ног."""
        M = self.M
        L = M.leg_len
        body = pose.setdefault('body', {})
        bp = list(body.get('position', [0, 0, 0]))
        body['position'] = [bp[0], 0.0, bp[2]]
        need = []
        hips = {}
        feet = dict(feet)
        for leg in ('right_leg', 'left_leg'):
            fx, fz, toe, up = feet[leg]
            h = flip(ap(M.chain(pose, leg), (0, 0, 0)))
            hips[leg] = h
            hmin = L - max_drop
            d = math.hypot(fx - h[0], fz - h[2])
            dlim = math.sqrt(max(0.0, L ** 2 - max(0.0, hmin - up) ** 2))
            if d > dlim > 0:
                k = dlim / d
                fx, fz = h[0] + (fx - h[0]) * k, h[2] + (fz - h[2]) * k
                feet[leg] = (fx, fz, toe, up)
                d = dlim
            need.append(up + math.sqrt(max(1.0, L ** 2 - d * d)) - h[1])
        dy = min(0.0, min(need)) - drop
        body['position'] = [bp[0], dy, bp[2]]
        for leg in ('right_leg', 'left_leg'):
            fx, fz, toe, up = feet[leg]
            h = hips[leg] + np.array([0, dy, 0])
            d = math.hypot(fx - h[0], fz - h[2])
            hy = h[1] - up
            dmax = math.sqrt(max(0.0, L ** 2 - (hy + 0.3) ** 2))
            if 1e-6 < d < dmax:                     # нога длиннее, чем нужно: стопа отходит наружу по той же линии (колена нет)
                s = dmax / d
                fx, fz = h[0] + (fx - h[0]) * s, h[2] + (fz - h[2]) * s
                d = dmax
            elif d <= 1e-6:
                fz = h[2] - dmax
                d = dmax
            vy = math.sqrt(max(0.0, L ** 2 - d * d))
            tgt = np.array([fx, h[1] - vy, fz])
            toe_d = yaw_dir(toe)
            x0 = self.prev.get(leg, [0.0, 0.0, 0.0])

            def f(v, leg=leg, tgt=tgt):
                pose[leg] = {'rotation': [v[0], v[1], v[2]]}
                Mw = M.chain(pose, leg)
                e = flip(ap(Mw, M.foot)) - tgt
                fw = flip(Mw[:3, :3] @ np.array([0.0, 0.0, -1.0]))
                fw[1] = 0
                return float(e @ e) + 4.0 * float(np.sum((nrm(fw) - toe_d) ** 2)) + 1e-5 * float(np.sum((v - x0) ** 2))
            v, _ = descend(f, x0, 16.0 if leg not in self.prev else 4.0)
            pose[leg] = {'rotation': [float(x) for x in v]}
            self.prev[leg] = v
        return pose

    # ---------------- правая рука + кисть: кисть в точке hand (R-мир), ось предмета по d, «верх» предмета по up
    def arm(self, pose, side, hand, w_reg=2e-4):
        M = self.M
        bn = side + '_arm'
        hb = 'bipedHandRight' if side == 'right' else 'bipedHandLeft'
        x0 = self.prev.get(bn, pose.get(bn, {}).get('rotation', [0.0, 0.0, 0.0]))
        x0 = np.array(x0, float)
        # рука — одна кость: кисть всегда на расстоянии длины руки от плеча. Недостижимую цель проецируем на эту сферу (ближайшая
        # достижимая точка единственна) и решаем тёплым стартом — без перескоков между ветвями; несколько стартов — только в 1-м кадре
        sh = flip(ap(M.chain(pose, bn), (0, 0, 0)))
        if not hasattr(self, '_arm_len'):
            self._arm_len = {}
        if bn not in self._arm_len:
            self._arm_len[bn] = float(np.linalg.norm(flip(ap(M.chain({}, hb), (0, 0, 0))) - flip(ap(M.chain({}, bn), (0, 0, 0)))))
        reach = sh + nrm(np.asarray(hand, float) - sh) * self._arm_len[bn]

        def f(v):
            pose[bn] = {'rotation': [v[0], v[1], v[2]]}
            e = flip(ap(M.chain(pose, hb), (0, 0, 0))) - reach
            return float(e @ e) + w_reg * float(np.sum((v - x0) ** 2)) + 2e-4 * v[1] ** 2
        if bn in self.prev:
            v, err = descend(f, x0, 5.0, iters=300)
        else:
            best = None
            for s0 in (x0, [-90, 0, 0], [-45, 0, 20], [-140, 0, 0], [-20, 0, 10], [-90, 30, 60], [-90, -30, -40]):
                x0 = np.array(s0, float)
                c = descend(f, x0, 20.0, iters=300)
                if best is None or c[1] < best[1]:
                    best = c
            v, err = best
        pose[bn] = {'rotation': [float(x) for x in v]}
        ex = float(np.linalg.norm(flip(ap(M.chain(pose, hb), (0, 0, 0))) - np.asarray(hand, float)))
        self.err = max(getattr(self, 'err', 0.0), ex)
        return ex

    def wrist(self, pose, d, up=None, base=(0, 0, 0), far=None, w_up=0.3):
        """Двойной поворот кисти (hand2): решаем ВИДИМЫЙ поворот предмета (непрерывен), ключ — его половина (кватернион, знак —
        ближе к прошлому кадру), чтобы ключи шли без перескоков между ветвями и GeckoLib не проворачивал предмет между кадрами."""
        M = self.M
        if not M.hand2:
            return self._wrist(pose, d, up, base, far, w_up)
        saved = self.prev.get('hand')
        rest = M.bones['bipedHandRight']['rest']
        far_ = M.axis_far if far is None else np.asarray(far, float)
        a_l = nrm(far_ - np.asarray(base, float))                       # ось предмета и его «верх» — в осях кисти (до её поворота)
        u_l = np.asarray(M.item_up, float)
        u_l = nrm(u_l - a_l * float(u_l @ a_l))
        pose['bipedHandRight'] = dict(pose.get('bipedHandRight', {}), rotation=[0.0, 0.0, 0.0])
        d_w = nrm(d)
        u_w0 = np.asarray(up if up is not None else (0.0, 1.0, 0.0), float)
        u_w0 = u_w0 - d_w * float(u_w0 @ d_w)
        if np.linalg.norm(u_w0) < 1e-6:
            u_w0 = np.cross(d_w, [1.0, 0.0, 0.0])
        u_w0 = nrm(u_w0)
        Bl = np.column_stack([a_l, u_l, np.cross(a_l, u_l)])
        Bworld = np.column_stack([d_w, u_w0, np.cross(d_w, u_w0)])
        # скручивание руки вокруг её оси (кисть остаётся на месте) — свободно: берём такое, при котором кисть поворачивает предмет
        # меньше всего (видимый поворот кисти < 180°: тогда ключ — главная половина, без перескока ветвей) и ближе к прошлому кадру
        side = 'right_arm'
        r_arm = np.array(pose[side]['rotation'], float)
        rest_a = M.bones[side]['rest']
        Ra = (Rz(rest_a[2] + r_arm[2] * D) @ Ry(rest_a[1] - r_arm[1] * D) @ Rx(rest_a[0] - r_arm[0] * D))[:3, :3]
        v_l = nrm(M.bones['bipedHandRight']['base'])
        tw0 = self.prev.get('twist', 0.0)

        def rel(th):
            K_ = np.array([[0, -v_l[2], v_l[1]], [v_l[2], 0, -v_l[0]], [-v_l[1], v_l[0], 0]])
            Rt = np.eye(3) + math.sin(th) * K_ + (1 - math.cos(th)) * K_ @ K_
            e = _euler_zyx(Ra @ Rt)
            key = [-(e[0] - rest_a[0]) / D, -(e[1] - rest_a[1]) / D, (e[2] - rest_a[2]) / D]
            key = [p_ + ((k - p_ + 180) % 360 - 180) for p_, k in zip(r_arm, key)]
            pose[side] = {'rotation': key}
            P0 = M.chain(pose, 'bipedHandRight')[:3, :3]
            R_ = P0.T @ Bworld @ Bl.T
            ang = math.acos(max(-1.0, min(1.0, (np.trace(R_) - 1) / 2)))
            return ang, R_, key
        best = None
        for th in np.radians(np.arange(-120, 121, 10)) + tw0:
            ang, R_, key = rel(th)
            cost = ang + 0.15 * abs(th - tw0) + (3.0 if ang > math.radians(165) else 0.0)
            if best is None or cost < best[0]:
                best = (cost, th, R_, key)
        th0 = best[1]
        for th in np.radians(np.arange(-9, 10, 1.5)) + th0:
            ang, R_, key = rel(th)
            cost = ang + 0.15 * abs(th - tw0) + (3.0 if ang > math.radians(165) else 0.0)
            if cost < best[0]:
                best = (cost, th, R_, key)
        _, th, R, key_arm = best
        pose[side] = {'rotation': [float(x) for x in key_arm]}
        self.prev[side] = np.array(key_arm, float)
        self.prev['twist'] = float(th) * 0.0                            # скручивание считаем от решения руки каждого кадра
        err = 0.0
        q = _quat(R)
        cands = []
        for sgn in (1.0, -1.0):
            h = np.array([1.0, 0, 0, 0]) + sgn * q
            if np.linalg.norm(h) > 1e-6:
                cands.append(h / np.linalg.norm(h))
        qp = self.prev.get('hand_q')
        qh = max(cands, key=lambda c: abs(float(c @ qp))) if qp is not None else max(cands, key=lambda c: c[0])
        if qp is not None and float(qh @ qp) < 0:
            qh = -qh
        self.prev['hand_q'] = qh
        e = _euler_zyx(_qmat(qh))                          # R = Rz(c)·Ry(b)·Rx(a); ключ: x = −(a − rest0), y = −(b − rest1), z = c − rest2
        key = [-(e[0] - rest[0]) / D, -(e[1] - rest[1]) / D, (e[2] - rest[2]) / D]
        if saved is not None:
            key = [p_ + ((k - p_ + 180) % 360 - 180) for p_, k in zip(saved, key)]
        pose['bipedHandRight'] = dict(pose.get('bipedHandRight', {}), rotation=[float(x) for x in key])
        self.prev['hand'] = np.array(key, float)
        return err

    def _wrist(self, pose, d, up=None, base=(0, 0, 0), far=None, w_up=0.3):
        """bipedHandRight: ось предмета (base → far, оси кисти) по направлению d (R-мир), ребро/плоскость по up."""
        M = self.M
        far = M.axis_far if far is None else far
        x0 = np.array(self.prev.get('hand', [0.0, 0.0, 0.0]), float)
        d = nrm(d)
        base = np.asarray(base, float)

        def f(v):
            pose['bipedHandRight'] = dict(pose.get('bipedHandRight', {}), rotation=[v[0], v[1], v[2]])
            Mw = M.item_frame(pose)
            a = flip(ap(Mw, base))
            b = flip(ap(Mw, far))
            ax = nrm(b - a)
            e = float(np.sum((ax - d) ** 2))
            if up is not None:
                u = flip(Mw[:3, :3] @ M.item_up)
                e += w_up * float(np.sum((nrm(u - ax * float(u @ ax)) - nrm(up)) ** 2))
            return e + 1e-6 * float(np.sum((v - x0) ** 2))
        v, err = descend(f, x0, 30.0 if 'hand' not in self.prev else 6.0, iters=400)
        pose['bipedHandRight'] = dict(pose.get('bipedHandRight', {}), rotation=[float(x) for x in v])
        self.prev['hand'] = v
        return err


def _quat(R):
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1) * 2
        return np.array([0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s])
    i = int(np.argmax([R[0, 0], R[1, 1], R[2, 2]]))
    if i == 0:
        s = math.sqrt(1 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        return np.array([(R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s])
    if i == 1:
        s = math.sqrt(1 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        return np.array([(R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s])
    s = math.sqrt(1 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
    return np.array([(R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s])


def _qmat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def _euler_zyx(R):
    """R = Rz(c)·Ry(b)·Rx(a) → (a, b, c), радианы."""
    b = math.asin(max(-1.0, min(1.0, -R[2, 0])))
    if abs(R[2, 0]) < 0.9999:
        return math.atan2(R[2, 1], R[2, 2]), b, math.atan2(R[1, 0], R[0, 0])
    return math.atan2(-R[1, 2], R[1, 1]), b, 0.0


def hand_pt(M, pose, side='right'):
    hb = 'bipedHandRight' if side == 'right' else 'bipedHandLeft'
    return flip(ap(M.chain(pose, hb), (0, 0, 0)))


def item_pt(M, pose, p):
    """Точка предмета (оси кисти) → R-мир (с вторым поворотом кисти, если hand2)."""
    return flip(ap(M.item_frame(pose), p))


# ================================================================== запекание
def unwrap(prev, v):
    if prev is None:
        return v
    return [p + ((x - p + 180) % 360 - 180) for p, x in zip(prev, v)]


def bake(fn, length, dt=0.02, events=None, keep=None):
    """fn(t) -> поза {кость: {'rotation'|'position'|'scale': [..]}} (значения JSON). → анимация GeckoLib (ключи списками — линейно)."""
    n = int(round(length / dt))
    bones = {}
    last = {}
    for i in range(n + 1):
        t = round(length * i / n, 4)
        for b, ch in fn(t).items():
            if b.startswith('_'):
                continue
            for c, v in ch.items():
                name = {'rotation': 'rotation', 'position': 'position', 'scale': 'scale', 'rot': 'rotation', 'pos': 'position'}[c]
                v = [float(x) for x in v]
                if name == 'rotation':
                    v = unwrap(last.get(b), v)
                    last[b] = v
                bones.setdefault(b, {}).setdefault(name, {})['%g' % t if t else '0.0'] = [round(x, 2) for x in v]
    o = {'animation_length': length, 'bones': bones}
    if events:
        o['timeline'] = {('%g' % t): e for t, e in sorted(events.items())}
    return o


# ================================================================== кривые (как у пилота T29)
def ease(k, kind='io'):
    import anim_body
    return anim_body.ease(k, kind)


class Keys:
    """Ключи параметров: [(t, {имя: значение}, кривая)] (anim_body.Keys, но значения — числа/кортежи)."""

    def __init__(self, keys):
        import anim_body
        self.k = anim_body.Keys(keys)

    def __call__(self, t, name, default=0.0):
        return self.k(t, name, default)

    def f(self, t, name, default=0.0):
        return float(self.k(t, name, default))

    def v(self, t, name, default=(0, 0, 0)):
        return [float(x) for x in np.atleast_1d(self.k(t, name, default))]


def stime(segs):
    import gen_martin_ef as EF
    return EF.STime(segs)


def path_at(path, s):
    import gen_martin_ef as EF
    return EF.path_at(path, s)


# ================================================================== сшивка с позой стойки на краях
def stance_targets(M, pose):
    """Цели стойки из её JSON-позы (FK): стопы (x, z, носок, 0), кисти, направление предмета (yaw, pitch)."""
    W = M.world_pose(pose)
    W['~item'] = M.item_frame(pose, W)
    out = {}
    for leg, key in (('right_leg', 'rf'), ('left_leg', 'lf')):
        p = ap(W[leg], M.foot)
        f = W[leg][:3, :3] @ np.array([0.0, 0.0, -1.0])
        out[key] = (float(p[0]), float(p[2]), math.degrees(math.atan2(f[0], -f[2])), 0.0)
    out['hand_r'] = ap(W['bipedHandRight'], (0, 0, 0))
    out['hand_l'] = ap(W['bipedHandLeft'], (0, 0, 0))
    return out, W


def blend_edges(fn, pose0, length, t_in=0.08, t_out=0.3):
    """fn(t) → поза; в первые t_in с и последние t_out с поза плавно сводится к pose0 (стойка) — стык с покоем без скачка."""
    def g(t):
        o = fn(t)
        if t < t_in:
            w = 1 - ease(t / t_in, 'io')
        elif t > length - t_out:
            w = ease((t - (length - t_out)) / t_out, 'io')
        else:
            return o
        for b, ch in pose0.items():
            for c, v in ch.items():
                cur = o.setdefault(b, {}).get(c, [0.0, 0.0, 0.0] if c != 'scale' else [1.0, 1.0, 1.0])
                if c == 'rotation':
                    v = [cv + ((x - cv + 180) % 360 - 180) for cv, x in zip(cur, v)]
                o[b][c] = [cv * (1 - w) + x * w for cv, x in zip(cur, v)]
        return o
    return g
