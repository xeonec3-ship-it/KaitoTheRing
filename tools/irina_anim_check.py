#!/usr/bin/env python3
"""
T27 «Ирина»: покадровая проверка анимаций (шаг 0.1 с) — та же математика, что у GeckoLib 4 / превью three.js.
  Модель: geo/entity/irina.geo.json (x зеркалится, поворот кости (−x, −y, z), порядок Z·Y·X — RenderUtils.rotateMatrixAroundBone).
  Анимации: animations/entity/irina.animation.json — тело и ткань (контроллеры не пересекаются по костям).
  Посох: models/item/irina_staff.json на кости bipedHandRight (повёрнут кистью дважды — GeckoLib 4.8.4), как Iron's renderStackForBone:
         translate(0, −1/16, −1/16), X −90, затем display thirdperson_righthand (translation, rotationXYZ, scale), −0.5.
Система координат проверки — модельная: вперёд (по взгляду) = −z, вправо = +x, вверх = +y; 16 ед. = 1 блок.

Что проверяется (правила владельца, 20.11):
  1 направление — у атак кисть/навершие посоха перед ней (z < 0), а не за спиной;
  2 посох — в хвате (кость руки), не проходит сквозь торс, капюшон, поля шляпы и землю; нет рывков и прокрутки (> 60°/0.1 с; в окне удара hit ± 0.2 с — > 300°/0.1 с, эталон Epic Fight 21.11);
  3 руки — плечо не уходит назад за спину (> 50° назад) и не выворачивается; ключи у всех костей тела; переходы без
    разворотов через ±180° (разница первого кадра и позы покоя);
  4 ткань — концы лент юбки не уходят сквозь ноги и не выходят вперёд при шаге; шляпа не проваливается в капюшон;
  кисть не протыкает боковые стенки раструба.
Запуск:  python3 tools/irina_anim_check.py [--verbose]       → таблица нарушений; код выхода 1, если есть ошибки
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
DT = 0.1
HAND2 = '~hand_rot'     # в W: второй поворот кисти для посоха (как в игре, GeckoLib 4.8.4)

# анимация тела → ткань, с которой она играет в игре (письмо T27, раздел 2)
COMBOS = {
    'irina_idle': 'irina_cloth_idle', 'irina_walk': 'irina_cloth_walk',
    'irina_cast_short': 'irina_cloth_storm', 'irina_cast_long': 'irina_cloth_storm', 'irina_cast_long_end': 'irina_cloth_storm',
    'irina_staff_attack': 'irina_cloth_idle', 'irina_staff_sweep': 'irina_cloth_idle', 'irina_mark': 'irina_cloth_storm',
    'irina_bind': 'irina_cloth_storm', 'irina_whip': 'irina_cloth_storm', 'irina_steal': 'irina_cloth_storm',
    'irina_others_happiness': 'irina_cloth_storm', 'irina_only_mine': 'irina_cloth_cocoon', 'irina_only_mine_broken': 'irina_cloth_storm',
    'irina_phase2': 'irina_cloth_storm', 'irina_phase3': 'irina_cloth_storm', 'irina_finisher': 'irina_cloth_storm',
    'irina_spawn': 'irina_cloth_spawn', 'irina_death': 'irina_cloth_death', 'irina_gaze': 'irina_cloth_storm',
    'irina_knots': 'irina_cloth_storm', 'irina_swap': 'irina_cloth_storm', 'irina_puppet': 'irina_cloth_storm',
    'irina_puppet_hold': 'irina_cloth_storm', 'irina_replica_break': 'irina_cloth_storm',
}
# атаки/касты, направленные на цель: кисть (или навершие) в момент события — перед ней
AIMED = {'irina_staff_attack': ('hit', 'staff'), 'irina_staff_sweep': ('hit', 'staff'), 'irina_cast_short': ('cast', 'left'),
         'irina_mark': ('mark', 'left'), 'irina_whip': ('lash', 'both'), 'irina_puppet': ('puppet', 'both'),
         'irina_only_mine': ('reach', 'left'), 'irina_finisher': ('pierce', 'staff'), 'irina_steal': ('pull', 'both'),
         'irina_swap': ('swap', 'both'), 'irina_knots': ('knots', 'left'), 'irina_cast_long': (None, 'right'),
         'irina_bind': ('bind', 'both')}
BODY = ['body', 'torso', 'head', 'hat', 'right_arm', 'left_arm', 'right_leg', 'left_leg']
TAU20 = 2 * math.pi / 20
LEGS_FWD = 5      # нога вынесена вперёд больше этого — передние ленты она толкает вперёд (не ошибка)


def R3(ax, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    if ax == 'x':
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if ax == 'y':
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def M4(R=None, T=None, S=None):
    m = np.eye(4)
    if R is not None:
        m[:3, :3] = R
    if S is not None:
        m[:3, :3] = m[:3, :3] @ np.diag(S)
    if T is not None:
        m[:3, 3] = T
    return m


def zyx(r):
    return R3('z', r[2]) @ R3('y', r[1]) @ R3('x', r[0])


def blend(A_, B_, k):
    """Смесь двух мировых матриц: позиция — по прямой, поворот — по углам Z·Y·X (для коротких перелётов без оборотов)."""
    a, b = euler_zyx(A_[:3, :3]), euler_zyx(B_[:3, :3])
    d = (b - a + 180) % 360 - 180
    return M4(zyx(a + d * k), A_[:3, 3] + (B_[:3, 3] - A_[:3, 3]) * k)


def euler_zyx(R):
    """R = Rz·Ry·Rx → [x, y, z] в градусах (внутренние оси)."""
    y = math.asin(max(-1.0, min(1.0, -R[2, 0])))
    x = math.atan2(R[2, 1], R[2, 2])
    z = math.atan2(R[1, 0], R[0, 0])
    return np.degrees([x, y, z])


_RIG = []


def rig_cached():
    if not _RIG:
        _RIG.append(Rig())
    return _RIG[0]


class Rig:
    def __init__(self):
        g = json.load(open(os.path.join(A, 'geo', 'entity', 'irina.geo.json'), encoding='utf-8'))['minecraft:geometry'][0]
        self.anims = json.load(open(os.path.join(A, 'animations', 'entity', 'irina.animation.json'), encoding='utf-8'))['animations']
        self.bones, self.order = {}, []
        for b in g['bones']:
            piv = np.array([-b['pivot'][0], b['pivot'][1], b['pivot'][2]], float)
            r = b.get('rotation', [0, 0, 0])
            cubes = []
            for c in b.get('cubes', []):
                o, s, inf = c['origin'], c['size'], c.get('inflate', 0)
                lo = np.array([-(o[0] + s[0]) - inf, o[1] - inf, o[2] - inf])
                hi = np.array([-o[0] + inf, o[1] + s[1] + inf, o[2] + s[2] + inf])
                cp = np.array([-c['pivot'][0], c['pivot'][1], c['pivot'][2]]) if 'pivot' in c else piv
                cr = c.get('rotation')
                cubes.append((lo, hi, cp, None if not cr else zyx([-cr[0], -cr[1], cr[2]])))
            self.bones[b['name']] = dict(piv=piv, rest=np.array([-r[0], -r[1], r[2]], float), parent=b.get('parent'), cubes=cubes)
            self.order.append(b['name'])
        for n in self.order:
            b = self.bones[n]
            pp = self.bones[b['parent']]['piv'] if b['parent'] else np.zeros(3)
            b['base'] = b['piv'] - pp
        st = json.load(open(os.path.join(A, 'models', 'item', 'irina_staff.json'), encoding='utf-8'))
        self.staff_disp = st['display']['thirdperson_righthand']
        els = st['elements']
        ys = [e['from'][1] for e in els]
        # ключевые точки посоха (координаты предмета, 0..16): низ подтока, хват, верх древка, навершие (центр крюка), кончик крюка
        fr = np.array([e['from'] for e in els], float)
        to = np.array([e['to'] for e in els], float)
        head = (fr[:, 1] > 18)
        self.staff_pts = {
            'butt': np.array([8.0, fr[:, 1].min(), 8.0]),
            'grip': np.array([8.0, 8.0, 8.0]),
            'neck': np.array([8.0, 18.0, 8.0]),
            'head': (fr[head].min(0) + to[head].max(0)) / 2,
            'hook': np.array([to[head][:, 0].max(), (fr[head][:, 1].min() + to[head][:, 1].max()) / 2, 8.0]),
            'top': np.array([8.0, to[:, 1].max(), 8.0]),
        }
        # тонкая «ось» посоха для пересечений: 24 точки от подтока до верха + точки крюка
        self.staff_line = [np.array([8.0, y, 8.0]) for y in np.linspace(fr[:, 1].min(), to[:, 1].max(), 32)]
        self.staff_line += [(fr[i] + to[i]) / 2 for i in np.where(head)[0][::3]]
        del ys

    # ---------------------------------------------------------------- позы
    @staticmethod
    def chan(ch, t, default):
        ks = sorted(ch, key=float)
        ts = [float(k) for k in ks]

        def get(i):
            v = ch[ks[i]]
            return v if isinstance(v, list) else (v.get('vector') or v.get('post') or v.get('pre'))
        if t <= ts[0]:
            return list(get(0))
        if t >= ts[-1]:
            return list(get(len(ts) - 1))
        i = 0
        while ts[i + 1] < t:
            i += 1
        a, b = get(i), get(i + 1)
        k = (t - ts[i]) / (ts[i + 1] - ts[i])
        return [a[j] + (b[j] - a[j]) * k for j in range(3)]

    def anim_time(self, an, t):
        if an is None:
            return 0
        L = an['animation_length']
        return t % L if an.get('loop') is True and t >= L else min(t, L)

    def pose(self, body, cloth, t, tc=None):
        """Мировые матрицы костей (модельное пространство) при анимациях body/cloth в момент t."""
        A_ = [(self.anims.get(body), self.anim_time(self.anims.get(body), t)),
              (self.anims.get(cloth), self.anim_time(self.anims.get(cloth), t if tc is None else tc))]
        W, raw = {}, {}
        for n in self.order:
            b = self.bones[n]
            r, p, s = [0, 0, 0], [0, 0, 0], [1, 1, 1]
            for an, tt in A_:
                bk = an and an['bones'].get(n)
                if not bk:
                    continue
                if 'rotation' in bk:
                    r = self.chan(bk['rotation'], tt, r)
                if 'position' in bk:
                    p = self.chan(bk['position'], tt, p)
                if 'scale' in bk:
                    s = self.chan(bk['scale'], tt, s)
                    if not isinstance(s, list):
                        s = [s] * 3
            raw[n] = (r, p)
            rot = b['rest'] + np.array([-r[0], -r[1], r[2]])
            L = M4(zyx(rot), b['base'] + np.array([-p[0], p[1], p[2]]), [max(1e-4, v) for v in s])
            W[n] = (W[b['parent']] @ L) if b['parent'] else L
            if n == 'bipedHandRight':
                W[HAND2] = M4(zyx(rot))
        return W, raw

    def world_json(self, pose):
        """Мировые матрицы по позе в осях Blockbench/JSON ({кость: {'rot': [...], 'pos': [...]}}), без анимаций из файла."""
        W = {}
        for n in self.order:
            b = self.bones[n]
            o = pose.get(n, {})
            r, p = o.get('rot', [0, 0, 0]), o.get('pos', [0, 0, 0])
            L = M4(zyx(b['rest'] + np.array([-r[0], -r[1], r[2]])), b['base'] + np.array([-p[0], p[1], p[2]]))
            W[n] = (W[b['parent']] @ L) if b['parent'] else L
            if n == 'bipedHandRight':
                W[HAND2] = M4(zyx(b['rest'] + np.array([-r[0], -r[1], r[2]])))
        return W

    def local_json(self, parent_world, bone, D):
        """Ключи кости bone (оси Blockbench: rot, pos), при которых её мировая матрица = D при мировой матрице родителя parent_world."""
        b = self.bones[bone]
        L = np.linalg.inv(parent_world) @ D
        tot = euler_zyx(L[:3, :3])
        r = (tot - b['rest'] + 180) % 360 - 180
        q = L[:3, 3] - b['base']
        return {'rot': [float(-r[0]), float(-r[1]), float(r[2])], 'pos': [float(-q[0]), float(q[1]), float(q[2])]}

    def pt(self, W, bone, p):
        """Точка p (модельные координаты позы покоя) на кости bone → мир."""
        v = np.append(np.asarray(p, float) - self.bones[bone]['piv'], 1.0)
        return (W[bone] @ v)[:3]

    def staff_M(self, W):
        d = self.staff_disp
        a = M4(T=[0, -1, -1]) @ M4(R3('x', -90))
        rx, ry, rz = d.get('rotation', [0, 0, 0])
        a = a @ M4(T=d.get('translation', [0, 0, 0])) @ M4(R3('x', rx) @ R3('y', ry) @ R3('z', rz)) @ M4(S=d.get('scale', [1, 1, 1]))
        # GeckoLib 4.8.4 (BlockAndItemGeoLayer.renderForBone): предмет повёрнут поворотом кисти ВТОРОЙ раз (у шарнира кисти)
        return W['bipedHandRight'] @ W.get(HAND2, np.eye(4)) @ a

    def staff_world(self, W, p):
        return (self.staff_M(W) @ np.append(np.asarray(p, float) - 8.0, 1.0))[:3]

    def cube_inv(self, W, bone, ci, shrink=0.0):
        """Функция «точка внутри бруска» (shrink — запас внутрь, ед.)."""
        lo, hi, cp, cr = self.bones[bone]['cubes'][ci]
        Mi = np.linalg.inv(W[bone])
        piv = self.bones[bone]['piv']

        def inside(q):
            v = (Mi @ np.append(q, 1.0))[:3] + piv          # в координатах кости (поза покоя)
            if cr is not None:
                v = cr.T @ (v - cp) + cp
            return bool(np.all(v > lo + shrink) and np.all(v < hi - shrink))
        return inside

    def depth_in(self, W, bone, ci, q):
        lo, hi, cp, cr = self.bones[bone]['cubes'][ci]
        v = (np.linalg.inv(W[bone]) @ np.append(q, 1.0))[:3] + self.bones[bone]['piv']
        if cr is not None:
            v = cr.T @ (v - cp) + cp
        return float(min(np.min(v - lo), np.min(hi - v)))


def arm_dir(rig, W, side):
    """Направление руки (плечо → кисть), единичный вектор."""
    arm = side + '_arm'
    sh = rig.pt(W, arm, rig.bones[arm]['piv'])
    hand = rig.pt(W, 'bipedHand' + side.capitalize(), rig.bones['bipedHand' + side.capitalize()]['piv'])
    v = hand - sh
    return v / (np.linalg.norm(v) + 1e-9), sh, hand


class Frame:
    """Поза в момент t: мировые матрицы, обратные (кэш), «сырые» ключи."""

    def __init__(self, rig, body, cloth, t):
        self.rig, self.t = rig, t
        self.W, self.raw = rig.pose(body, cloth, t)
        self._inv = {}

    def inv(self, bone):
        if bone not in self._inv:
            self._inv[bone] = np.linalg.inv(self.W[bone])
        return self._inv[bone]

    def local(self, bone, q):
        """Мировая точка → координаты кости в позе покоя."""
        return (self.inv(bone) @ np.append(q, 1.0))[:3] + self.rig.bones[bone]['piv']

    def depth(self, bone, ci, q):
        lo, hi, cp, cr = self.rig.bones[bone]['cubes'][ci]
        v = self.local(bone, q)
        if cr is not None:
            v = cr.T @ (v - cp) + cp
        return float(min(np.min(v - lo), np.min(hi - v)))

    def cube_pts(self, bone, ci, n=3, inset=0.0):
        """Точки поверхности/объёма бруска в мире (сетка n×n×n)."""
        lo, hi, cp, cr = self.rig.bones[bone]['cubes'][ci]
        out = []
        for x in np.linspace(lo[0] + inset, hi[0] - inset, n):
            for y in np.linspace(lo[1] + inset, hi[1] - inset, n):
                for z in np.linspace(lo[2] + inset, hi[2] - inset, n):
                    c = np.array([x, y, z])
                    if cr is not None:
                        c = cr @ (c - cp) + cp
                    out.append(self.rig.pt(self.W, bone, c))
        return out


def cubes(rig, bone):
    return [(bone, i) for i in range(len(rig.bones[bone]['cubes']))]


TIPS = ['rib_%02d_b' % k for k in range(20)] + ['tie_r_b', 'tie_l_b', 'sash_r', 'sash_l', 'hood_drape', 'sleeve_r', 'sleeve_l']
# концы ткани меряются в осях кости, к которой подвешена цепочка (иначе «вперёд» дал бы наклон торса или подъём руки)
TIP_ROOT = dict({'rib_%02d_b' % k: 'skirt' for k in range(20)}, tie_r_b='torso', tie_l_b='torso', sash_r='torso', sash_l='torso',
                hood_drape='hood', sleeve_r='right_arm', sleeve_l='left_arm')


def tip_point(rig, bone):
    """Нижний конец ленты/рукава (поза покоя): середина нижней грани первого бруска кости."""
    lo, hi, cp, cr = rig.bones[bone]['cubes'][0]
    c = np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2])
    if cr is not None:
        far = [cr @ (np.array([x, y, z]) - cp) + cp for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
        c = min(far, key=lambda v: v[1])
    return c


def check(verbose=False, only=None):
    rig = Rig()
    issues = []
    rest = Frame(rig, 'irina_idle', 'irina_cloth_idle', 0.0)
    STAFF_SOLID = (cubes(rig, 'torso')[:1] + cubes(rig, 'head') + cubes(rig, 'hood') + cubes(rig, 'skirt') + cubes(rig, 'right_leg') +
                   cubes(rig, 'left_leg') + cubes(rig, 'left_arm') + cubes(rig, 'sleeve_l'))
    NAMES_RU = {'torso': 'торс', 'head': 'голову', 'hood': 'капюшон', 'skirt': 'юбку', 'right_leg': 'правую ногу', 'left_leg': 'левую ногу',
                'left_arm': 'левую руку', 'sleeve_l': 'левый раструб'}
    brim = cubes(rig, 'hat_brim')
    hat_all = brim + cubes(rig, 'hat_crown') + cubes(rig, 'hat_tip') + cubes(rig, 'hat_tip2') + cubes(rig, 'hat_tip3')
    hood = cubes(rig, 'hood')
    names = [n for n in COMBOS if n in rig.anims and (only is None or n in only)]
    idle0 = rest.raw
    tip_rest = {b: rest.local(TIP_ROOT[b], rig.pt(rest.W, b, tip_point(rig, b))) for b in TIPS}
    for name in names:
        an = rig.anims[name]
        cloth = COMBOS[name]
        L = an['animation_length']
        ev = {v: float(k) for k, v in an.get('timeline', {}).items()}
        # ключи у всех костей тела
        miss = [b for b in BODY if b not in an['bones'] or 'rotation' not in an['bones'][b]]
        if miss:
            issues.append((name, 0, 'keys', 'нет ключей rotation у костей тела: ' + ', '.join(miss)))
        if 'position' not in an['bones'].get('body', {}):
            issues.append((name, 0, 'keys', 'нет ключей position у body'))
        prev = None
        n = int(round(L / DT))
        for i in range(n + 1):
            t = min(L, i * DT)
            F = Frame(rig, name, cloth, t)
            W, raw = F.W, F.raw
            # ---- переход из покоя: разница углов первого кадра (переход GeckoLib идёт по прямой — через ±180° = оборот)
            if i == 0 and name != 'irina_idle':
                for b in BODY:
                    d = np.abs(np.array(raw[b][0]) - np.array(idle0[b][0]))
                    if d.max() > 150:
                        issues.append((name, t, 'jump', 'переход из idle: %s поворот %.0f° (через ±180°?)' % (b, d.max())))
            ax = rig.staff_world(W, rig.staff_pts['top']) - rig.staff_world(W, rig.staff_pts['butt'])
            ax /= np.linalg.norm(ax)
            # ---- скачки за кадр
            if prev is not None:
                # быстрее 600°/с — рывок. В окне удара (событие hit ± 0.2 с) — до 3000°/с: эталон Epic Fight (владелец 21.11,
                # docs/specs/anim_style_epicfight.md) — сам удар 0.08–0.24 с, пик угловой скорости оружия 1750–2500°/с
                lim = 300 if ('hit' in ev and abs(t - ev['hit']) <= 0.2) else 60
                for b in BODY:
                    d = np.abs(np.array(raw[b][0]) - np.array(prev[1][b][0]))
                    if np.max(d) > lim:
                        issues.append((name, t, 'jump', '%s повернулась на %.0f° за 0.1 с' % (b, np.max(d))))
                ang = math.degrees(math.acos(max(-1, min(1, float(prev[2] @ ax)))))
                if ang > lim:
                    issues.append((name, t, 'staff', 'посох повернулся на %.0f° за 0.1 с (рывок/прокрутка)' % ang))
            prev = (W, raw, ax)
            # ---- посох сквозь тело/капюшон/шляпу/землю
            hit = set()
            for q in rig.staff_line:
                w = rig.staff_world(W, q)
                if w[1] < -0.5:
                    hit.add('землю (y=%.1f)' % w[1])
                for (bn, ci) in STAFF_SOLID:
                    if F.depth(bn, ci, w) > 0.6:
                        hit.add(NAMES_RU[bn])
                for (bn, ci) in hat_all:
                    if F.depth(bn, ci, w) > 0.3:
                        hit.add('поля шляпы' if bn == 'hat_brim' else 'тулью шляпы')
            for h in sorted(hit):
                issues.append((name, t, 'staff', 'посох проходит сквозь ' + h))
            # ---- руки: не за спиной
            for side in ('right', 'left'):
                d, sh, hand = arm_dir(rig, W, side)
                tz = W['torso'][:3, :3] @ np.array([0, 0, 1.0])
                back = float(d @ tz)
                if back > 0.55:
                    issues.append((name, t, 'arm', '%s рука уходит назад за спину (z=%.2f)' % (side, back)))
            # ---- кисть сквозь стенку раструба; кисть/раструб сквозь поля шляпы
            for side, sl in (('right', 'sleeve_r'), ('left', 'sleeve_l')):
                lo, hi, cp, cr = rig.bones[side + '_arm']['cubes'][1]       # кисть
                corners = [np.array([x, y, z]) for x in (lo[0], hi[0]) for y in (lo[1] + 0.2, hi[1]) for z in (lo[2], hi[2])]
                slo, shi, _, _ = rig.bones[sl]['cubes'][0]
                out = 0
                for c in corners:
                    v = F.local(sl, rig.pt(W, side + '_arm', c))
                    if v[1] > slo[1] + 0.3 and (v[0] < slo[0] or v[0] > shi[0] or v[2] < slo[2] or v[2] > shi[2]):
                        out += 1
                if out:
                    issues.append((name, t, 'sleeve', 'кисть %s протыкает стенку раструба (%d углов)' % (side, out)))
                pts = F.cube_pts(side + '_arm', 1, 2) + F.cube_pts(sl, 0, 3)
                if any(F.depth(bn, ci, q) > 0.5 for q in pts for (bn, ci) in brim):
                    issues.append((name, t, 'hat', '%s кисть/раструб проходит сквозь поля шляпы' % side))
            # ---- шляпа в капюшон (глубже, чем в покое)
            worst = 0.0
            for (bn, ci) in brim:
                lo, hi, cp, cr = rig.bones[bn]['cubes'][ci]
                for c in [np.array([x, lo[1], z]) for x in np.linspace(lo[0], hi[0], 4) for z in np.linspace(lo[2], hi[2], 4)]:
                    if cr is not None:
                        c = cr @ (c - cp) + cp
                    w = rig.pt(W, bn, c)
                    w0 = rig.pt(rest.W, bn, c)
                    for (hb, hi_) in hood:
                        dd = F.depth(hb, hi_, w)
                        d0 = rest.depth(hb, hi_, w0)
                        if dd > 1.0 and dd > d0 + 0.8:
                            worst = max(worst, dd)
            if worst:
                issues.append((name, t, 'hat', 'поля шляпы уходят в капюшон на %.1f ед.' % worst))
            # ---- ленты юбки сквозь ноги; концы ткани — не вперёд (в осях тела) сильнее 3 ед. от покоя
            for k in range(20):
                for seg in ('rib_%02d' % k, 'rib_%02d_b' % k):
                    lo, hi, cp, cr = rig.bones[seg]['cubes'][0]
                    mid = (lo + hi) / 2
                    if cr is not None:
                        mid = cr @ (mid - cp) + cp
                    w = rig.pt(W, seg, mid)
                    for leg in ('right_leg', 'left_leg'):
                        for ci in range(len(rig.bones[leg]['cubes'])):
                            if F.depth(leg, ci, w) > 0.8:
                                issues.append((name, t, 'cloth', '%s (лента) внутри ноги %s' % (seg, leg)))
            for b in TIPS:
                root = TIP_ROOT[b]
                cur = F.local(root, rig.pt(W, b, tip_point(rig, b)))
                r0 = tip_rest[b]
                if root.endswith('_arm'):            # рукав: «вперёд» вдоль руки = к кисти не считаем, только в сторону ладони/спины
                    continue
                legs_fwd = max(-raw['right_leg'][0][0], -raw['left_leg'][0][0])
                if b.startswith('rib_') and math.cos(TAU20 * (int(b[4:6]) + 0.5)) > 0 and legs_fwd > LEGS_FWD:
                    continue
                if cur[2] - r0[2] < -3.0:
                    issues.append((name, t, 'cloth', '%s: конец уходит вперёд на %.1f ед.' % (b, r0[2] - cur[2])))
        # ---- направление в момент события
        if name in AIMED:
            evn, what = AIMED[name]
            te = ev.get(evn, L * 0.5) if evn else L * 0.5
            W, _ = rig.pose(name, cloth, te)
            body_c = W['body'][:3, 3]
            pts = []
            if what == 'staff':
                pts.append(('навершие посоха', rig.staff_world(W, rig.staff_pts['head'])))
            if what in ('left', 'both'):
                pts.append(('левая кисть', rig.pt(W, 'bipedHandLeft', rig.bones['bipedHandLeft']['piv'])))
            if what in ('right', 'both'):
                pts.append(('правая кисть', rig.pt(W, 'bipedHandRight', rig.bones['bipedHandRight']['piv'])))
            for lab, p in pts:
                z = p[2] - body_c[2]
                if verbose:
                    print('  %-24s %-6s %.2f с  %s z=%+.1f (вперёд <0)' % (name, evn, te, lab, z))
                if z > -2.0:
                    issues.append((name, te, 'aim', '%s не перед ней в момент «%s» (z=%+.1f, вперёд = −z)' % (lab, evn, z)))
    return issues


def summarize(issues):
    by = {}
    for name, t, kind, msg in issues:
        by.setdefault((name, kind, msg.split(' (')[0] if kind != 'aim' else msg), []).append(t)
    rows = []
    for (name, kind, msg), ts in sorted(by.items()):
        rows.append('%-26s %-7s %s  [t: %s]' % (name, kind, msg, ', '.join('%.1f' % t for t in ts[:8]) + (' …' if len(ts) > 8 else '')))
    return rows


if __name__ == '__main__':
    only = [a for a in sys.argv[1:] if not a.startswith('--')] or None
    iss = check('--verbose' in sys.argv, only)
    for r in summarize(iss):
        print(r)
    print('нарушений: %d' % len(iss))
    sys.exit(1 if iss else 0)
