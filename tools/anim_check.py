#!/usr/bin/env python3
"""
Покадровая проверка анимаций боссов (T26 Глава Культа, T30 Эреб): прямая кинематика костей .geo.json как в превью
(tools/cult_leader_preview.template.html: оси three.js, x модели отражён, Euler ZYX), предмет в правой руке — как у Iron's
(HumanoidRenderer: кость bipedHandRight → −1/16 z, −1/16 y, X −90°, затем display thirdperson_righthand предмета).

Оси результата: босс в начале координат смотрит в −z («вперёд» = −z), x — влево от босса (как в three.js превью), y — вверх; пиксели модели.

  python3 tools/anim_check.py [cult_leader|ereb] [--anim имя] [--dt 0.1] [--json путь]
Печатает по каждой анимации найденные нарушения:
  dir      — в момент удара (события timeline / тики AttackKeyframe Iron's) острие/рука позади босса (z > 0) или острие не впереди груди;
  body     — оружие проходит сквозь корпус/голову/ноги (точки лезвия и древка внутри кубов торса, головы, ног);
  ground   — оружие ниже земли (y < −0.5);
  spin     — оружие прокручивается в руке (поворот за 0.1 с > 120°, не на взмахе) или скачок кости;
  arm      — рука в вывороте (кисть позади плеча больше чем на 5 px при поднятой руке / рука сквозь торс);
  cloth    — ткань вперёд или сквозь ноги (плащ / полы камзола);
  jump     — у кости ключи с разрывом ≥ 180° между соседними ключами (переход через ±180°).
"""
import json
import math
import os
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
JAR = os.path.join(ROOT, 'libs', 'irons_spellbooks-1.20.1-3.16.1.jar')
D = math.pi / 180
HAND2 = '~hand_rot'          # в W: поворот кости bipedHandRight ещё раз (как рисует предмет GeckoLib, см. Model.item_world)

# тики ударов Iron's (FireBossEntity: AttackAnimationData → AttackKeyframe), 20 тиков/с
IRON_HITS = {
    'scythe_dagger_double_horizontal': [15, 36, 42], 'scythe_backpedal': [20], 'scythe_sideslash_downslash_sideslash': [18, 30, 50],
    'scythe_jump_combo': [20, 35], 'scythe_downslash_sideslash': [22, 40], 'scythe_horizontal_slash_spin': [14, 30],
    'scythe_dagger_combo_1': [20, 36, 42, 52, 61, 74],
}
# какие анимации Iron's играют на боссах: SpellAnimations (касты заклинаний) + у Главы — FireBossEntity (удары, особые, появление/смерть)
SPELL_ANIMS = ['instant_projectile', 'continuous_thrust', 'charged_throw', 'long_cast', 'long_cast_finish', 'continuous_overhead', 'instant_slash',
               'charge_arrow', 'charge_wavy', 'instant_self', 'charge_spit', 'charge_spit_finish', 'charge_black_hole', 'overhead_two_handed_swing',
               'touch_ground', 'horizontal_slash_one_handed', 'katana_upslash', 'charge_raised_hand', 'stomp', 'cross_arms', 'cast_t_pose',
               'kneeling_prayer', 'self_cast_two_hands', 'continuous_thrust_one_handed', 'throw_item', 'charge_one_handed_ray', 'shoot_one_handed_ray']
PLAYS = {'cult_leader': SPELL_ANIMS + list(IRON_HITS) + ['fire_boss_spawn', 'fire_boss_death', 'fire_boss_break_stance', 'fire_boss_half_health_attack',
                                                         'fire_boss_acrobatic_dagger_throw', 'summon_fiery_daggers', 'offhand_parry', 'magma_throw'],
         'ereb': SPELL_ANIMS, 'ereb_hand': SPELL_ANIMS}
STRIKE_EVENTS = {'slash', 'impale', 'hit', 'stab', 'throw', 'shatter', 'release', 'dash', 'brand', 'erupt', 'pillar', 'plant', 'crush', 'cast'}
WEAPON_EVENTS = {'slash', 'impale', 'hit', 'stab', 'throw', 'shatter', 'plant'}

CFG = {
    'cult_leader': dict(geo='geo/entity/cult_leader.geo.json', anim='animations/entity/cult_leader.animation.json',
                        item='models/item/cult_scythe.json', tip=[3.55, 11.34, 8.0], cloth={'cape': 'back'}),
    'ereb': dict(geo='geo/entity/ereb.geo.json', anim='animations/entity/ereb.animation.json', item='models/item/ereb_rapier.json', tip=None,
                 cloth={'coat_back_r': 'back', 'coat_back_l': 'back', 'coat_front_r': 'front', 'coat_front_l': 'front'}),
    # T31 Эреб, Длань Лжи — тот же скелет, что у Эреба (+ призрачная рука ghost_*), стеклянная рапира тем же слоем Iron's (21.11: для
    # проверщика рывков tools/scythe_jitter.py --boss ereb_hand)
    'ereb_hand': dict(geo='geo/entity/ereb_hand.geo.json', anim='animations/entity/ereb_hand.animation.json', item='models/item/ereb_hand_rapier.json',
                      tip=None, cloth={'coat_back_r': 'back', 'coat_back_l': 'back', 'coat_front_r': 'front', 'coat_front_l': 'front'}),
}


# ------------------------------------------------------------------ матрицы
def T(x, y, z):
    m = np.eye(4)
    m[:3, 3] = (x, y, z)
    return m


def Rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1.0]])


def Ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1.0]])


def Rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]])


def S(x, y, z):
    return np.diag([x, y, z, 1.0])


def ap(m, p):
    return (m @ np.array([p[0], p[1], p[2], 1.0]))[:3]


# ------------------------------------------------------------------ анимации GeckoLib (как chanAt превью)
def _ease(name, t):
    t = max(0.0, min(1.0, t))
    E = {
        None: t, 'linear': t, 'step': 0.0 if t < 1 else 1.0,
        'easeInSine': 1 - math.cos(t * math.pi / 2), 'easeOutSine': math.sin(t * math.pi / 2), 'easeInOutSine': -(math.cos(math.pi * t) - 1) / 2,
        'easeInQuad': t * t, 'easeOutQuad': 1 - (1 - t) ** 2, 'easeInOutQuad': 2 * t * t if t < .5 else 1 - (-2 * t + 2) ** 2 / 2,
        'easeInCubic': t ** 3, 'easeOutCubic': 1 - (1 - t) ** 3, 'easeInOutCubic': 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2,
        'easeInQuart': t ** 4, 'easeOutQuart': 1 - (1 - t) ** 4, 'easeInOutQuart': 8 * t ** 4 if t < .5 else 1 - (-2 * t + 2) ** 4 / 2,
        'easeInOutQuint': 16 * t ** 5 if t < .5 else 1 - (-2 * t + 2) ** 5 / 2,
    }
    return E.get(name, t)


def _keys(chan):
    if isinstance(chan, list):
        return [(0.0, chan, None)]
    if 'vector' in chan:
        return [(0.0, chan['vector'], chan.get('easing'))]
    ks = []
    for k, v in chan.items():
        if isinstance(v, list):
            ks.append((float(k), v, None))
        else:
            ks.append((float(k), v.get('vector') or v.get('post') or v.get('pre'), v.get('easing')))
    ks.sort(key=lambda x: x[0])
    return ks


def chan_at(chan, t):
    ks = _keys(chan)
    if t <= ks[0][0]:
        return list(ks[0][1])
    if t >= ks[-1][0]:
        return list(ks[-1][1])
    for i in range(len(ks) - 1):
        if ks[i + 1][0] >= t:
            a, b = ks[i], ks[i + 1]
            k = _ease(b[2], (t - a[0]) / (b[0] - a[0]))
            return [x + (y - x) * k for x, y in zip(a[1], b[1])]


# ------------------------------------------------------------------ модель
class Model:
    def __init__(self, name):
        c = CFG[name]
        self.name = name
        g = json.load(open(os.path.join(A, c['geo']), encoding='utf-8'))['minecraft:geometry'][0]
        self.bones = {}
        for b in g['bones']:
            piv = np.array([-b['pivot'][0], b['pivot'][1], b['pivot'][2]], float)
            r = b.get('rotation') or [0, 0, 0]
            cubes = []
            for cu in b.get('cubes', []):
                if not isinstance(cu.get('uv'), list) and not cu.get('uv'):
                    continue
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
        doc = json.load(open(os.path.join(A, c['item']), encoding='utf-8'))['base']
        d = doc['display']['thirdperson_righthand']
        tr, rot, sc = d.get('translation', [0, 0, 0]), d.get('rotation', [0, 0, 0]), d.get('scale', [1, 1, 1])
        self.item_m = (T(0, -1, -1) @ Rx(-math.pi / 2) @ T(*tr) @ Rx(rot[0] * D) @ Ry(rot[1] * D) @ Rz(rot[2] * D) @ S(*sc) @ T(-8, -8, -8))
        # точки предмета: центры брусков и их концы по длинной оси
        pts = []
        for e in doc['elements']:
            a, b = np.array(e['from'], float), np.array(e['to'], float)
            m = np.eye(4)
            if e.get('rotation'):
                ro = e['rotation']
                o = np.array(ro['origin'], float)
                R = {'x': Rx, 'y': Ry, 'z': Rz}[ro['axis']](ro['angle'] * D)
                m = T(*o) @ R @ T(*-o)
            ax = int(np.argmax(b - a))
            for f in (0.0, 0.25, 0.5, 0.75, 1.0):
                p = (a + b) / 2
                p[ax] = a[ax] + (b[ax] - a[ax]) * f
                pts.append(ap(m, p))
        self.item_pts = np.array(pts)
        # «острие» — самая дальняя от рукояти точка; рукоять — центр хвата (ближайшая к началу координат кисти точка)
        hp = np.array([ap(self.item_m, p) for p in self.item_pts])
        self.grip_i = int(np.argmin(np.linalg.norm(hp, axis=1)))
        if c.get('tip'):                                   # острие лезвия косы (как tip в tools/boss_video.py)
            self.item_pts = np.vstack([self.item_pts, [c['tip']]])
            self.tip_i = len(self.item_pts) - 1
        else:                                              # рапира: верх клинка
            self.tip_i = int(np.argmax(self.item_pts[:, 1]))
        self.cloth = c['cloth']

    def world(self, anim, t, override=None):
        """{кость: мировая матрица} для анимации (None — покой) в момент t; override — {кость: [rx, ry, rz]} вместо ключей."""
        W = {}
        HR = [np.eye(4)]
        bones = anim['bones'] if anim else {}

        def wm(n):
            if n in W:
                return W[n]
            b = self.bones[n]
            r, p, s = [0, 0, 0], [0, 0, 0], [1, 1, 1]
            bk = bones.get(n)
            if bk:
                if 'rotation' in bk:
                    r = chan_at(bk['rotation'], t)
                if 'position' in bk:
                    p = chan_at(bk['position'], t)
                if 'scale' in bk:
                    s = chan_at(bk['scale'], t)
                    if not isinstance(s, list):
                        s = [s] * 3
            if override and n in override:
                r = override[n]
            rest = b['rest']
            rot = Rz(rest[2] + r[2] * D) @ Ry(rest[1] - r[1] * D) @ Rx(rest[0] - r[0] * D)
            m = T(b['base'][0] - p[0], b['base'][1] + p[1], b['base'][2] + p[2]) @ rot @ S(*[max(1e-4, x) for x in s])
            if n == 'bipedHandRight':
                HR[0] = rot
            par = b['parent']
            W[n] = (wm(par) if par else np.eye(4)) @ m
            return W[n]
        for n in self.bones:
            wm(n)
        W[HAND2] = HR[0]
        return W

    def with_hand(self, W, anim, t, r, dp=None):
        """Тот же кадр W, но поворот кисти bipedHandRight = r (оси анимаций): пересчитывается только кисть (у неё нет дочерних костей)."""
        b = self.bones['bipedHandRight']
        bk = (anim['bones'] if anim else {}).get('bipedHandRight', {})
        p = chan_at(bk['position'], t) if 'position' in bk else [0, 0, 0]
        if dp is not None:
            p = [p[0] + dp[0], p[1] + dp[1], p[2] + dp[2]]
        s = chan_at(bk['scale'], t) if 'scale' in bk else [1, 1, 1]
        if not isinstance(s, list):
            s = [s] * 3
        rest = b['rest']
        rot = Rz(rest[2] + r[2] * D) @ Ry(rest[1] - r[1] * D) @ Rx(rest[0] - r[0] * D)
        m = T(b['base'][0] - p[0], b['base'][1] + p[1], b['base'][2] + p[2]) @ rot @ S(*[max(1e-4, x) for x in s])
        W2 = dict(W)
        W2['bipedHandRight'] = W[b['parent']] @ m
        W2[HAND2] = rot
        return W2

    def item_world(self, W):
        # GeckoLib 4.8.4 (BlockAndItemGeoLayer.renderForBone): матрица кости уже повёрнута (prepMatrixForBone), затем
        # translateAndRotateMatrixForBone поворачивает её ВТОРОЙ раз поворотом той же кости — предмет в игре повёрнут кистью дважды
        m = W['bipedHandRight'] @ W.get(HAND2, np.eye(4)) @ self.item_m
        if getattr(self, '_pts_h', None) is None or len(self._pts_h) != len(self.item_pts):
            self._pts_h = np.hstack([self.item_pts, np.ones((len(self.item_pts), 1))])
        return (self._pts_h @ m.T)[:, :3]

    def inside(self, W, bone, pts, margin=0.4):
        """Какие точки внутри кубов кости (с запасом margin внутрь)."""
        res = np.zeros(len(pts), bool)
        for hm, lo, hi in self.bones[bone]['cubes']:
            if np.prod(hi - lo) < 1:
                continue
            inv = np.linalg.inv(W[bone] @ hm)
            q = (inv[:3, :3] @ pts.T).T + inv[:3, 3]
            res |= np.all((q > lo + margin) & (q < hi - margin), axis=1)
        return res


def load_anims(name):
    return json.load(open(os.path.join(A, CFG[name]['anim']), encoding='utf-8'))['animations']


def iron_names():
    with zipfile.ZipFile(JAR) as z:
        return set(json.loads(z.read('assets/irons_spellbooks/animations/casting_animations.json'))['animations'])


def hit_times(name, an):
    tl = an.get('timeline', {})
    hs = [(float(k), v) for k, v in tl.items() if v in STRIKE_EVENTS]
    hs += [(k / 20.0, 'hit') for k in IRON_HITS.get(name, [])]
    return sorted(hs)


def arm_dir(W, side):
    """Направление руки (плечо → кисть) в мировых осях."""
    b = W[side + '_arm']
    sh = ap(b, (0, 0, 0))
    hand = ap(W['bipedHand' + ('Right' if side == 'right' else 'Left')], (0, 0, 0))
    return sh, hand


def check(name, only=None, dt=0.1, verbose=False):
    M = Model(name)
    anims = load_anims(name)
    iron = iron_names()
    report = {}
    body_parts = [b for b in ('torso', 'head', 'armor_head', 'right_leg', 'left_leg') if b in M.bones]
    for an_name, an in anims.items():
        if only and an_name not in only:
            continue
        if not only and an_name in iron and an_name not in PLAYS[name]:
            continue
        L = float(an.get('animation_length', 0) or 0)
        n = max(1, int(round(L / dt)))
        issues = []
        prev = None
        prev_W = None
        hits = hit_times(an_name, an)
        for i in range(n + 1):
            t = min(L, i * dt)
            W = M.world(an, t)
            ip = M.item_world(W)
            tip, grip = ip[M.tip_i], ip[M.grip_i]
            vis = np.linalg.det(W['bipedHandRight'][:3, :3]) > 1e-6
            if vis:
                # сквозь тело
                for bp in body_parts:
                    hit = M.inside(W, bp, ip, margin=0.6)
                    if hit.sum() >= 2:
                        issues.append((t, 'body', '%d точек оружия внутри %s' % (hit.sum(), bp)))
                planted = an_name == 'cult_leader_first_flame' and 0.9 <= t <= 5.2      # подток древка воткнут в землю нарочно
                if ip[:, 1].min() < -0.5 and not planted:
                    issues.append((t, 'ground', 'оружие ниже земли на %.1f px' % -ip[:, 1].min()))
                # прокрутка в руке: ориентация предмета относительно кисти не меняется (жёстко), поэтому смотрим скорость оси предмета
                ax = tip - grip
                ax /= np.linalg.norm(ax) + 1e-9
                if prev is not None:
                    ang = math.degrees(math.acos(max(-1, min(1, float(ax @ prev)))))
                    if ang > 120:
                        issues.append((t, 'spin', 'ось оружия повернулась на %.0f° за %.1f с' % (ang, dt)))
                prev = ax
            # руки
            for side in ('right', 'left'):
                sh, hd = arm_dir(W, side)
                bodyW = W['torso'] if 'torso' in W else W['body']
                inv = np.linalg.inv(bodyW)
                hl = ap(inv, hd)
                shl = ap(inv, sh)
                # кисть сзади плеча (в осях торса +z — назад) при поднятой руке — «локоть назад»
                if hl[2] - shl[2] > 7 and hl[1] > shl[1] - 4:
                    issues.append((t, 'arm', '%s: кисть поднята за спиной (%.1f px назад)' % (side, hl[2] - shl[2])))
                if M.inside(W, 'torso', np.array([hd]), margin=1.0).any():
                    issues.append((t, 'arm', '%s: кисть внутри торса' % side))
            # ткань
            for bn, kind in M.cloth.items():
                if bn not in W:
                    continue
                bw = W[bn]
                top, bot = ap(bw, (0, 0, 0)), ap(bw, (0, -10, 0))
                v = bot - top
                # отклонение от вертикали вперёд — по горизонтальному взгляду корпуса (кость body)
                f = W['body'][:3, :3] @ np.array([0.0, 0.0, -1.0])
                f[1] = 0
                f /= np.linalg.norm(f) + 1e-9
                fwd = float(v @ f) / (np.linalg.norm(v) + 1e-9)
                if kind == 'back':
                    lim = 0.05
                else:                                   # передняя пола: вперёд только вслед за ногой (не дальше ноги +30°)
                    leg = W['right_leg' if bn.endswith('_r') else 'left_leg']
                    lv = ap(leg, (0, -10, 0)) - ap(leg, (0, 0, 0))
                    lim = max(math.sin(math.radians(8)), float(lv @ f) / (np.linalg.norm(lv) + 1e-9) + math.sin(math.radians(30)))
                if fwd > lim:
                    issues.append((t, 'cloth', '%s вперёд на %.0f°' % (bn, math.degrees(math.asin(min(1, fwd))))))
                # сквозь ноги: точки ткани внутри ног
                cpts = np.array([ap(bw, (x, y, 0)) for x in (-1.5, 0, 1.5) for y in (-3, -6, -9)])
                for leg in ('right_leg', 'left_leg'):
                    h = M.inside(W, leg, cpts, margin=0.5)
                    if h.sum() >= 2:
                        issues.append((t, 'cloth', '%s сквозь %s' % (bn, leg)))
            prev_W = W
        # направление удара: у наших — точно в момент события; у Iron's — в окне ±0.1 с (тик удара сервера и кадр клиента
        # расходятся на 1–2 тика), в анимациях с кинжалом засчитывается и левая кисть
        for ht, ev in hits:
            win = [ht] if an_name not in iron else [ht + d for d in (-0.1, -0.05, 0, 0.05, 0.1)]
            good, info = False, ''
            for tt in win:
                W = M.world(an, max(0, min(L, tt)))
                ip = M.item_world(W)
                tip = ip[M.tip_i]
                _, hr = arm_dir(W, 'right')
                _, hl = arm_dir(W, 'left')
                if tt == ht:
                    info = 'остриё (%.1f, %.1f, %.1f), кисти R z=%.1f L z=%.1f' % (tip[0], tip[1], tip[2], hr[2], hl[2])
                if tip[2] < -2 or ('dagger' in an_name and hl[2] < -6):
                    good = True
            if ev in WEAPON_EVENTS and not good:
                issues.append((ht, 'dir', '%s: остриё не перед боссом: %s' % (ev, info)))
            elif verbose:
                issues.append((ht, 'ok', '%s: %s' % (ev, info)))
        # разрывы ключей
        for bn, bk in an['bones'].items():
            if 'rotation' not in bk:
                continue
            ks = _keys(bk['rotation'])
            for a, b in zip(ks, ks[1:]):
                dv = max(abs(x - y) for x, y in zip(a[1], b[1]))
                wrap = max(abs((x - y + 180) % 360 - 180) for x, y in zip(a[1], b[1]))
                if b[2] == 'step' or wrap < 30:
                    continue
                if dv >= 180 and (b[0] - a[0]) < 0.25:
                    issues.append((b[0], 'jump', '%s: %.0f° за %.2f с' % (bn, dv, b[0] - a[0])))
        report[an_name] = {'iron': an_name in iron, 'length': L, 'issues': issues}
    return report


def summarize(rep, verbose=False):
    for n, r in rep.items():
        iss = r['issues']
        kinds = {}
        for t, k, msg in iss:
            kinds.setdefault(k, []).append((t, msg))
        bad = {k: v for k, v in kinds.items() if k != 'ok'}
        tag = 'Iron' if r['iron'] else 'наша'
        if not bad and not verbose:
            continue
        print('== %s (%s, %.2f с)' % (n, tag, r['length']))
        for k, v in kinds.items():
            ts = sorted(set(round(t, 2) for t, _ in v))
            print('   %-6s %d кадров: %s … %s' % (k, len(v), ts[:6], v[0][1]))


if __name__ == '__main__':
    args = sys.argv[1:]
    name = args[0] if args and not args[0].startswith('--') else 'cult_leader'
    only = None
    if '--anim' in args:
        only = set(args[args.index('--anim') + 1].split(','))
    dt = float(args[args.index('--dt') + 1]) if '--dt' in args else 0.1
    rep = check(name, only, dt, verbose='-v' in args)
    summarize(rep, '-v' in args)
    if '--json' in args:
        json.dump(rep, open(args[args.index('--json') + 1], 'w'), ensure_ascii=False, indent=1)
