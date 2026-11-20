#!/usr/bin/env python3
"""
T29 «Мартин» — призрачные солдаты (GeckoLib), боевое знамя (GeckoLib: сущность с хитбоксом, её можно срубить), призрачная конница
(fx-мэш из брусков). Вызывается из tools/gen_martin.py (run(M, args)); отдельно: python3 tools/gen_martin_extra.py.

Солдаты и знамя рисуются ×1 (обычный рост), текстура ×4 (4 px на единицу UV, как у эталона cult_leader.png).
Призрачность солдат — у кода: RenderType.entityTranslucent + альфа вершин ~0.65 (getRenderColor), свечение — glowmask.
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nightmare_geo import Model, Anim, TAU, write_json as _wj  # noqa: E402

M = None


def ramp(*hs):
    return np.array([[int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)] for h in hs])


# призрачная палитра: латы — холодное серебро с бирюзой, кайма — бледное «лунное золото», ткань — глубокая синь
G_STEEL = ramp('#16303c', '#244a5a', '#3a6a7e', '#5c90a4', '#86b8c8', '#b4dce6', '#e4f8fc')
G_GOLD = ramp('#2c3c34', '#465c4c', '#6a8468', '#94ae8a', '#bed6ae', '#e0f0cc', '#f8fff0')
G_RED = ramp('#0a1620', '#10222e', '#183244', '#22465c', '#2e5e78', '#447e98')
G_BLACK = ramp('#060c12', '#0c1620', '#14202c', '#1c2c3a', '#283a4a')
G_WHITE = ramp('#5a8496', '#80a8b8', '#a8ccd8', '#cce8f0', '#f0fcff')
G_LEATHER = ramp('#0e1a22', '#162834', '#203846', '#2c4a5a', '#3a5e70')


class ghost_palette:
    """На время покраски подменяет палитры материалов gen_martin на призрачные (и включает свечение золотой каймы)."""
    NAMES = ('R_STEEL', 'R_GOLD', 'R_RED', 'R_BLACK', 'R_WHITE', 'R_LEATHER', 'R_GRIP')

    def __enter__(self):
        self.old = {n: getattr(M, n) for n in self.NAMES}
        for n, v in zip(self.NAMES, (G_STEEL, G_GOLD, G_RED, G_BLACK, G_WHITE, G_LEATHER, G_LEATHER)):
            setattr(M, n, v)
        self.glow = M.GLOW_GOLD
        M.GLOW_GOLD = 0.55

    def __exit__(self, *a):
        for n, v in self.old.items():
            setattr(M, n, v)
        M.GLOW_GOLD = self.glow


# ================================================================== призрачный солдат (martin_soldier)
SOL_GRIP_R = -0.6


def build_soldier():
    m = Model('martin_soldier', density=M.DENS, tex_w=128)
    M.add_mats(m)
    m.hand = {'left': np.array([-5.0, 11.0, -0.2]), 'right': np.array([5.0, 11.0, -0.2])}
    m.grip_r = SOL_GRIP_R
    m.bone('body', None, (0, 12, 0))
    m.bone('torso', 'body', (0, 24, 0))
    m.box('torso', (-4.0, 12, -2.2), (4.0, 24, 2.2), 'red', base=2)
    m.box('torso', (-3.4, 16.4, -2.8), (3.4, 23.8, 2.6), 'steel', deco='chest', base=3)
    m.box('torso', (-2.6, 13.2, -2.7), (2.6, 16.6, 2.5), 'steel', lames=4)
    m.box('torso', (-2.8, 23.0, -3.0), (2.8, 24.6, 2.6), 'gold', base=3)
    m.box('torso', (-4.2, 12.0, -2.6), (4.2, 13.3, 2.6), 'leather', deco='belt')
    m.box('torso', (-4.1, 10.6, -2.7), (4.1, 12.1, 2.6), 'steel', trim='b')
    m.bone('tabard_front', 'torso', (0, 12.2, -2.8))
    m.box('tabard_front', (-2.2, 4.0, -3.1), (2.2, 12.2, -2.75), 'red', deco='tabard', folds=False)
    m.bone('cape', 'torso', (0, 23.4, 2.6))                                     # короткий рваный плащ-накидка
    m.box('cape', (-4.6, 9.0, 2.5), (4.6, 23.6, 3.1), 'cape', outer='south', edge_b=True)
    # шлем: топфхельм с гребнем-плюмажем
    m.bone('head', 'body', (0, 24, 0))
    m.box('head', (-3.6, 24.2, -3.6), (3.6, 31.4, 3.6), 'steel', base=3)
    m.box('head', (-3.0, 27.6, -3.9), (-0.5, 28.4, -3.6), 'eye')
    m.box('head', (0.5, 27.6, -3.9), (3.0, 28.4, -3.6), 'eye')
    m.box('head', (-0.5, 24.6, -4.1), (0.5, 30.6, -3.6), 'gold', base=4)
    m.box('head', (-3.8, 28.4, -4.0), (3.8, 29.4, 3.8), 'steel', base=4)
    m.box('head', (-0.7, 31.4, -3.0), (0.7, 33.6, 3.6), 'gold', base=4)              # гребень
    m.rod('head', (0, 33.4, 2.6), (0, 30.0, 7.4), 1.0, 1.6, 'cape', outer='south')     # плюмаж назад
    for side, sn in ((1, 'right'), (-1, 'left')):
        X = side * 5.0
        arm, fore = sn + '_arm', sn + '_forearm'
        m.bone(arm, 'body', (X, 22, 0))
        m.box(arm, (X - 1.4, 16.6, -1.4), (X + 1.4, 22.4, 1.4), 'red', base=2)
        x0, x1 = sorted((X - side * 1.8, X + side * 2.6))
        m.box(arm, (x0, 20.4, -2.4), (x1, 23.4, 2.4), 'steel', trim='b', base=4)
        m.bone(fore, arm, (X, 16.6, 0))
        m.box(fore, (X - 1.5, 12.6, -1.5), (X + 1.5, 16.8, 1.5), 'steel', base=3)
        m.box(fore, (X - 1.7, 11.8, -1.7), (X + 1.7, 13.0, 1.7), 'gold', base=3)
        m.box(fore, (X - 1.3, 9.6, -1.3), (X + 1.3, 11.8, 1.3), 'leather', base=2)
    for side, sn in ((1, 'right'), (-1, 'left')):
        X = side * 2.1
        leg = sn + '_leg'
        m.bone(leg, 'body', (X, 12, 0))
        m.box(leg, (X - 1.9, 6.0, -1.9), (X + 1.9, 12.0, 1.9), 'red', base=2)
        m.box(leg, (X - 2.0, 6.8, -2.1), (X + 2.0, 11.0, 1.9), 'steel', base=3)
        m.box(leg, (X - 1.6, 5.0, -2.6), (X + 1.6, 7.2, -1.6), 'steel', base=4)
        m.box(leg, (X - 1.9, 0.0, -2.8), (X + 1.9, 5.4, 1.9), 'steel', base=3, trim='t')
    # меч (одноручный, клинок вдоль +y, шарнир в хвате) и башенный щит на левом предплечье
    m.bone('sword', 'right_forearm', (5.0, 11.0, -0.2), (-90, 0, 0))
    p = np.array([5.0, 11.0, -0.2]) - [0, SOL_GRIP_R, 0]
    m.box('sword', p + [-0.7, 1.6, -0.25], p + [0.7, 12.4, 0.25], 'blade')
    m.box('sword', p + [-0.4, 12.4, -0.2], p + [0.4, 13.6, 0.2], 'blade', fuller=False)
    m.box('sword', p + [-2.4, 1.0, -0.45], p + [2.4, 1.7, 0.45], 'gold', base=4)
    m.box('sword', p + [-0.4, -2.0, -0.4], p + [0.4, 1.0, 0.4], 'grip')
    m.box('sword', p + [-0.7, -2.8, -0.7], p + [0.7, -2.0, 0.7], 'gold', base=4)
    m.bone('shield', 'left_forearm', (-5.0, 13.5, 0))
    c = np.array([-5.0, 13.0, -3.0])
    m.box('shield', c + [-4.2, -7.2, -0.4], c + [4.2, 7.2, 0.4], 'steel', deco='shield')
    for x0, x1 in ((-4.5, -3.8), (3.8, 4.5)):
        m.box('shield', c + [x0, -7.5, -0.6], c + [x1, 7.5, 0.6], 'steel', base=3)
    m.box('shield', c + [-4.5, 7.2, -0.6], c + [4.5, 7.9, 0.6], 'steel', base=4)
    m.box('shield', c + [-4.5, -7.9, -0.6], c + [4.5, -7.2, 0.6], 'steel', base=2)
    m.box('shield', c + [-1.1, 1.0, -1.0], c + [1.1, 3.0, -0.4], 'gold', engr=True)
    m.box('shield', c + [-0.5, -3.0, 0.4], c + [0.5, 3.0, 1.3], 'leather')
    return m


def soldier_anims(m):
    an = []
    g = M.Grip(m)
    track, ease = M.track, M.ease

    def A(name, length, loop=False):
        a = Anim('martin_soldier_' + name, length, loop)
        an.append(a)
        g.reset()
        return a

    READY = ((2.2, 15.0, -5.6), (0.0, 0.55, -0.83))          # меч над краем щита, остриём на врага
    SHIELD_FWD = {'left_arm': {'rot': [-42, -18, 0]}, 'left_forearm': {'rot': [-34, 0, 0]}, 'shield': {'rot': [20, 26, 0]}}

    def base(t, k=1.0):
        o = {k2: {'rot': list(np.array(v['rot']) * k)} for k2, v in SHIELD_FWD.items()}
        o['cape'] = {'rot': [6 + 2 * math.sin(TAU * t / 2.4), 0, 0]}
        o['tabard_front'] = {'rot': [-1.5 * math.sin(TAU * t / 2.4), 0, 0]}
        return o

    def idle(t):
        br = math.sin(TAU * t / 2.4)
        o = base(t)
        o.update({'body': {'pos': [0, -0.6 + 0.12 * br, 0]}, 'torso': {'rot': [5 + br, -8, 0]}, 'head': {'rot': [-3, 8, 0]},
                  'right_leg': {'rot': [-12, 8, 0]}, 'left_leg': {'rot': [14, -6, 0]}})
        g(o, READY[0], READY[1], left=0)
        return o
    A('idle', 2.4, True).sample(idle, 0.1)

    def walk(t):
        ph = TAU * t / 1.0
        s = math.sin(ph)
        o = base(t)
        o.update({'body': {'pos': [0, -0.4 * abs(math.cos(ph)), 0]}, 'torso': {'rot': [6, -6, 0]},
                  'right_leg': {'rot': [-28 * s, 0, 0]}, 'left_leg': {'rot': [28 * s, 0, 0]}})
        g(o, np.add(READY[0], [0, 0.3 * s, 0]), READY[1], left=0)
        return o
    A('walk', 1.0, True).sample(walk, 0.05)

    def attack(t):
        k = float(track(t, [(0, 0), (0.3, 1), (0.45, 2, 'in'), (0.7, 2), (1.0, 3)]))
        P = [READY[0], (3.5, 18.0, 1.5), (1.0, 17.5, -11.0), (1.0, 17.5, -11.0), READY[0]]
        D = [READY[1], (0.0, 0.2, -0.98), (0.0, 0.02, -1.0), (0.0, 0.02, -1.0), READY[1]]
        i = min(3, int(k))
        f = k - i
        l = float(track(t, [(0, 0), (0.3, -0.3), (0.45, 1, 'in'), (0.7, 1), (1.0, 0)]))
        o = base(t)
        o.update({'body': {'pos': [0, -0.8 * max(0, l), -3.5 * max(0, l)]}, 'torso': {'rot': [10 * max(0, l), -16 * l, 0]},
                  'right_leg': {'rot': [-30 * max(0, l), 0, 0]}, 'left_leg': {'rot': [26 * max(0, l), 0, 0]}})
        g(o, np.asarray(P[i]) * (1 - f) + np.asarray(P[i + 1]) * f, M.lerp_dir(D[i], D[i + 1], f), left=0)
        return o
    a = A('attack', 1.0)
    a.sample(attack, 0.04)
    a.instruction(0.45, 'hit')

    def brace(t):
        # «Строй»: щит вперёд и вниз, плечом в щит, ноги широко — держит удар (петля)
        br = math.sin(TAU * t / 1.6)
        o = {'body': {'pos': [0, -2.2 + 0.1 * br, 0]}, 'torso': {'rot': [16 + br, 14, 0]}, 'head': {'rot': [-12, -10, 0]},
             'left_arm': {'rot': [-64, -30, 0]}, 'left_forearm': {'rot': [-10, 0, 0]}, 'shield': {'rot': [4, 44, 0]},
             'right_leg': {'rot': [16, 0, 8]}, 'left_leg': {'rot': [-34, 0, -8]},
             'cape': {'rot': [12 + 2 * br, 0, 0]}, 'tabard_front': {'rot': [-6, 0, 0]}}
        g(o, (3.0, 18.5, -2.5), (0.05, 0.75, -0.66), left=0)
        return o
    A('brace', 1.6, True).sample(brace, 0.1)

    def spawn(t):
        # поднимается из земли (код ставит сущность на землю; модель идёт снизу), шаг вперёд, щит вперёд
        k = float(track(t, [(0, 0), (1.0, 1, 'out')]))
        o = base(t, k)
        o.update({'body': {'pos': [0, -30 * (1 - k), 0]}, 'torso': {'rot': [24 * (1 - k) + 5, 0, 0]}, 'head': {'rot': [30 * (1 - k), 0, 0]}})
        g(o, READY[0], READY[1], left=0)
        return o
    a = A('spawn', 1.2, 'hold')
    a.sample(spawn, 0.04)
    a.instruction(0.0, 'rise')

    def vanish(t):
        k = float(track(t, [(0, 0), (0.8, 1, 'in')]))
        o = base(t, 1 - k)
        o.update({'body': {'pos': [0, -6 * k, 0], 'scale': [1 + 0.2 * k, 1 - 0.6 * k, 1 + 0.2 * k]}, 'torso': {'rot': [20 * k, 0, 0]},
                  'head': {'rot': [26 * k, 0, 0]}})
        g(o, READY[0], READY[1], left=0)
        return o
    a = A('vanish', 0.8, 'hold')
    a.sample(vanish, 0.04)
    a.instruction(0.8, 'gone')
    return an


# ================================================================== знамя (martin_banner)
def mat_banner(ctx):
    """Полотнище: красное поле, золотая кайма и бахрома, герб Мартина (корона над мечом остриём вниз) — по мировым координатам,
    поэтому рисунок сквозной через все три куска; низ — «ласточкин хвост» (вырез по альфе)."""
    P = ctx.P
    x, y = P[:, 0], P[:, 1]
    lv = np.full(ctx.n, 3.0) + M.handf(ctx, 0.3, 1.0, 61, 0.015) + np.where(((x + 7) * 2).astype(int) % 6 == 5, -1, 0)
    rgb = M.tone(M.R_RED, lv)
    a = np.ones(ctx.n)
    if ctx.face in ('north', 'south'):
        top, bot = 53.0, 22.0
        notch = (y < bot + 6) & (np.abs(x) < (bot + 6 - y) * 0.9)          # вырез «ласточкин хвост»
        a = np.where(notch | (y < bot), 0.0, 1.0)
        border = (np.abs(x) > 6.2) | (y > top - 1.0) | ((y < bot + 6.8) & (np.abs(x) > (bot + 6 - y) * 0.9 - 0.8) & ~notch & (y < bot + 6.6))
        border |= (y < bot + 0.9) & ~notch
        rgb = np.where(border[:, None], M.tone(M.R_GOLD, np.where((x * 4).astype(int) % 3 == 0, 3, 5)), rgb)
        cx = np.abs(x)
        crown = (y > 44.0) & (y < 47.6) & (cx < 4.4) & ~((y > 46.4) & (np.abs(((x + 4.4) % 2.2) - 1.1) > 0.45))
        band = (y > 43.2) & (y < 44.4) & (cx < 4.6)
        blade = (cx < 0.7) & (y > 28.0) & (y < 39.4)
        tip = (cx < (y - 26.4) * 0.45) & (y <= 28.0) & (y > 26.4)
        guard = (cx < 3.6) & (y > 39.4) & (y < 40.6)
        grip = (cx < 0.5) & (y > 40.6) & (y < 42.2)
        em = crown | band | blade | tip | guard | grip
        shade = np.where(band | guard, 3, 5)
        rgb = np.where(em[:, None], M.tone(M.R_GOLD, shade), rgb)
        rgb = np.where((blade & (np.abs(x) < 0.25))[:, None], M.R_GOLD[2], rgb)
    return rgb, a, None


def build_banner():
    m = Model('martin_banner', density=M.DENS, tex_w=128)
    M.add_mats(m)
    m.materials['banner'] = mat_banner
    m.bone('root', None, (0, 0, 0))
    m.bone('pole_low', 'root', (0, 0, 0))
    m.box('pole_low', (-0.7, -1.0, -0.7), (0.7, 20.0, 0.7), 'leather', base=3)
    m.box('pole_low', (-1.0, 0.0, -1.0), (1.0, 2.0, 1.0), 'steel', base=3, trim='t')             # оковка у земли
    m.box('pole_low', (-0.9, 12.0, -0.9), (0.9, 13.0, 0.9), 'gold', base=4)
    m.bone('pole_top', 'pole_low', (0, 20, 0))                                                   # место «сруба»
    m.box('pole_top', (-0.7, 20.0, -0.7), (0.7, 56.0, 0.7), 'leather', base=3)
    m.box('pole_top', (-0.9, 30.0, -0.9), (0.9, 31.0, 0.9), 'gold', base=4)
    m.box('pole_top', (-7.8, 53.0, -0.6), (7.8, 54.2, 0.6), 'gold', engr=True)                   # перекладина
    for sx in (-1, 1):
        m.box('pole_top', (sx * 7.8 - 0.6, 52.4, -0.8), (sx * 7.8 + 0.6, 54.8, 0.8), 'gold', base=5)
        m.box('pole_top', (sx * 7.8 - 0.3, 48.8, -0.3), (sx * 7.8 + 0.3, 52.4, 0.3), 'gold', base=3)  # кисти
        m.box('pole_top', (sx * 7.8 - 0.55, 47.4, -0.55), (sx * 7.8 + 0.55, 48.8, 0.55), 'gold', base=4)
    # навершие: золотая корона с копейным острием
    m.box('pole_top', (-1.4, 56.0, -1.4), (1.4, 57.6, 1.4), 'gold', engr=True)
    for dx, dz in ((-1.1, -1.1), (1.1, -1.1), (-1.1, 1.1), (1.1, 1.1)):
        m.box('pole_top', (dx - 0.3, 57.6, dz - 0.3), (dx + 0.3, 58.8, dz + 0.3), 'gold', base=5)
    m.box('pole_top', (-0.5, 57.6, -0.5), (0.5, 61.0, 0.5), 'steel', base=5)
    m.box('pole_top', (-0.25, 61.0, -0.25), (0.25, 62.4, 0.25), 'steel', base=6)
    # полотнище — три куска-кости для волны
    tops = (53.0, 42.6, 32.2)
    prev = 'pole_top'
    for k, ytop in enumerate(tops):
        nm = 'cloth_%d' % (k + 1)
        m.bone(nm, prev, (0, ytop, 0.0))
        m.box(nm, (-7.0, ytop - 10.4, -0.2), (7.0, ytop, 0.2), 'banner')
        prev = nm
    return m


def banner_anims(m):
    an = []
    track = M.track

    def wave(t, amp=1.0, period=2.0):
        o = {}
        for k in range(3):
            ph = TAU * t / period - k * 0.9
            o['cloth_%d' % (k + 1)] = {'rot': [amp * (5 + 6 * k) * math.sin(ph) + 3 * k, amp * 6 * math.sin(ph * 0.5 + k), 0]}
        return o

    a = Anim('martin_banner_idle', 2.0, True)
    a.sample(lambda t: wave(t), 0.1)
    an.append(a)

    def plant(t):
        # вонзили: древко дрожит, полотнище взлетает и оседает (код ставит сущность в момент plant у Мартина)
        k = float(track(t, [(0, 1), (1.2, 0, 'out')]))
        o = wave(t, 1 + 2.5 * k, 1.0)
        o['pole_low'] = {'rot': [6 * k * math.sin(t * 38), 0, 5 * k * math.cos(t * 31)], 'pos': [0, -3 * max(0, 0.15 - t) / 0.15, 0]}
        return o
    a = Anim('martin_banner_plant', 1.2, False)
    a.sample(plant, 0.04)
    a.instruction(0.0, 'impact')
    an.append(a)

    def hit(t):
        k = float(track(t, [(0, 1), (0.4, 0)]))
        o = wave(t, 1 + 2 * k, 1.0)
        o['pole_low'] = {'rot': [8 * k * math.sin(t * 50), 0, 6 * k * math.sin(t * 43)]}
        return o
    a = Anim('martin_banner_hit', 0.4, False)
    a.sample(hit, 0.02)
    an.append(a)

    def cut(t):
        # срубили: верх древка ломается у отметки 20, валится набок с отскоком, полотнище комкается; держит последний кадр
        f = float(track(t, [(0, 0), (0.15, 0.08), (0.9, 1.0, 'in'), (1.05, 0.93, 'out'), (1.2, 1.0, 'in')]))
        o = wave(t, 0.4 + 2 * (1 - f), 0.8)
        o['pole_top'] = {'rot': [-12 * f, 0, 92 * f], 'pos': [0, -1.2 * f, 0]}
        o['cloth_1']['rot'][0] += 30 * f
        o['cloth_2']['rot'][0] += 20 * f
        o['pole_low'] = {'rot': [3 * (1 - f) * math.sin(t * 40), 0, 0]}
        return o
    a = Anim('martin_banner_cut', 1.6, 'hold')
    a.sample(cut, 0.04)
    a.instruction(0.0, 'snap')
    a.instruction(1.0, 'fall')
    an.append(a)
    return an


# ================================================================== призрачная конница (fx-мэш из брусков)
def build_rider():
    """Всадник и конь в «летящем галопе» (передние ноги вперёд, задние назад), копьё с флажком вперёд. Ед. 16 = 1 блок, морда к −z."""
    m = Model('martin_cavalry_rider', density=1, tex_w=64)
    for n in ('steel', 'dark', 'gold', 'horse', 'mane', 'cloth', 'eye'):
        m.materials[n] = lambda ctx: (np.zeros((ctx.n, 3)), 1.0, None)
    m.bone('horse', None, (0, 0, 0))
    b = 'horse'
    m.box(b, (-4.5, 15, -11), (4.5, 24, 11), 'horse')                                  # корпус
    m.box(b, (-5.0, 20, -9), (5.0, 25.5, 9), 'steel')                                  # попона-броня
    m.rod(b, (0, 21, -10), (0, 31, -16), 5.0, 5.5, 'horse')                            # шея
    m.rod(b, (0, 29, -15), (0, 31, -24), 4.0, 5.2, 'horse')                            # голова
    m.rod(b, (0, 30.5, -14), (0, 33, -22.5), 4.6, 1.6, 'steel')                       # налобник (шанфрон)
    m.box(b, (-2.4, 31, -20), (2.4, 31.8, -19), 'eye')
    m.rod(b, (0, 33, -12), (0, 23, -6), 1.4, 2.2, 'mane')                              # грива
    m.rod(b, (0, 24, 11), (0, 16, 20), 2.0, 2.0, 'mane')                               # хвост
    for sx, front in ((-1, True), (1, True), (-1, False), (1, False)):
        z = -8 if front else 8
        hip = np.array([sx * 3.2, 17, z])
        if front:
            knee = hip + [0, -5, -8]
            hoof = knee + [0, -6, -3 + (2 if sx > 0 else 0)]
        else:
            knee = hip + [0, -6, 7]
            hoof = knee + [0, -5, 5 - (2 if sx > 0 else 0)]
        m.rod(b, hip, knee, 2.8, 3.0, 'horse', ext=0.6)
        m.rod(b, knee, hoof, 2.0, 2.0, 'horse', ext=0.4)
        m.rod(b, hoof, hoof + (hoof - knee) / np.linalg.norm(hoof - knee) * 1.6, 2.4, 2.4, 'steel')
    # всадник
    m.box(b, (-3.6, 25, -3.4), (3.6, 37, 2.6), 'steel')                               # корпус в латах
    m.box(b, (-3.8, 33, -3.8), (3.8, 35, 3.0), 'gold')                                # кайма
    for sx in (-1, 1):
        m.rod(b, (sx * 3.6, 27, -1), (sx * 5.2, 21, -4), 2.8, 3.0, 'steel')           # ноги в стременах
        m.rod(b, (sx * 5.2, 21, -4), (sx * 5.2, 15.5, -2), 2.4, 2.6, 'steel')
    m.cbox(b, (0, 40.5, -0.6), (6.4, 7, 6.4), 'steel')                                 # шлем
    m.box(b, (-2.4, 40.4, -4.0), (2.4, 41.2, -3.7), 'eye')
    m.box(b, (-0.5, 44, -3.2), (0.5, 46, 3.6), 'gold')                                # гребень
    m.rod(b, (0, 45.5, 2.6), (0, 41, 9), 1.4, 2.4, 'mane')                             # плюмаж
    m.rod(b, (4.2, 35, -1), (5.6, 29, -6), 2.4, 2.4, 'steel')                          # правая рука к копью
    m.rod(b, (5.6, 30.5, 10), (5.6, 30.5, -40), 1.2, 1.2, 'dark')                      # копьё
    m.rod(b, (5.6, 30.5, -40), (5.6, 30.5, -45), 0.7, 0.7, 'steel')                    # наконечник
    m.box(b, (5.4, 30.6, -38.5), (5.8, 34.6, -31), 'cloth')                            # флажок
    m.rod(b, (-4.2, 35, -1), (-5.6, 30, -4), 2.4, 2.4, 'steel')
    m.box(b, (-7.2, 25, -8), (-6.4, 37, 0), 'steel')                                   # щит слева
    m.box(b, (-7.4, 29, -5.4), (-7.2, 33, -2.6), 'gold')
    m.bone('cape', 'horse', (0, 36, 3))                                                 # развевающийся плащ
    m.rod('cape', (0, 36, 3), (0, 30, 14), 8.0, 0.6, 'cloth')
    return m


def mesh_from_model(m, tones_of, flip=True, scale=1.0 / 16):
    """Модель (поза покоя) → список брусков fx-мэша [x0,y0,z0,x1,y1,z1,тон,[rx,ry,rz]] в блоках; поворот — Euler «YXZ» (R = Ry·Rx·Rz).
    flip: модель смотрит в −z, мэш едет вперёд по +z — поворачиваем на 180° вокруг y."""
    F = np.diag([-1.0, 1.0, -1.0]) if flip else np.eye(3)
    boxes = []
    for bn in m.order:
        for c in m.bones[bn].cubes:
            Mx, o = m.cube_xf(bn, c)
            ctr = F @ (Mx @ ((c.frm + c.to) / 2) + o) * scale
            R = F @ Mx
            size = (c.to - c.frm) * scale
            a = math.asin(max(-1.0, min(1.0, -R[1, 2])))
            b = math.atan2(R[0, 2], R[2, 2])
            cc = math.atan2(R[1, 0], R[1, 1])
            e = [round(math.degrees(v), 2) for v in (a, b, cc)]
            row = [round(float(v), 4) for v in (*(ctr - size / 2), *(ctr + size / 2))] + [tones_of[c.mat]]
            if any(abs(v) > 0.01 for v in e):
                row.append(e)
            boxes.append(row)
    return boxes


def cavalry_mesh():
    m = build_rider()
    tones = ['#86bcd2', '#3e6a80', '#e4f2c8', '#a6d6e6', '#c8f4ff', '#5e94ac', '#ffffff']
    idx = {'steel': 0, 'dark': 1, 'gold': 2, 'horse': 3, 'mane': 4, 'cloth': 5, 'eye': 6}
    boxes = mesh_from_model(m, idx)
    ys = [b[1] for b in boxes] + [b[4] for b in boxes]
    doc = {'comment': 'T29: призрачный всадник Мартина (конь в летящем галопе, копьё с флажком вперёд по +z). Центр — под копытами, '
                      'едет вперёд по оси z мэша. Сгенерировано tools/gen_martin_extra.py — правьте генератор.',
           'style': 'martin_ghost', 'center': 0, 'formedAt': 6, 'collapse': {'duration': 10, 'easing': 'easeInCubic'},
           'parts': [{'type': 'boxes', 'tones': tones, 'glowTones': [2, 4, 6], 'blend': 'translucent', 'opacity': 0.55, 'shade': True,
                      'boxes': boxes, 'appear': {'delay': 0, 'duration': 6, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.6},
                      'bounds': [round(min(ys), 3), round(max(ys), 3)]}]}
    M.write_json('fx/meshes/martin_cavalry_rider.json', doc, compact=True)
    return doc


# ================================================================== сборка
def run(mod, args=()):
    global M
    M = mod
    for build, anims, sub in ((build_soldier, soldier_anims, True), (build_banner, banner_anims, False)):
        m = build()
        m.pack()
        if sub:
            with ghost_palette():
                m.paint()
        else:
            m.paint()
        an = anims(m)
        name = m.name
        M.write_json('geo/entity/%s.geo.json' % name, m.geo_json(), compact=True)
        m.image.save(M.out('textures/entity/martin/%s.png' % name), optimize=True)
        if m.glow is not None:
            m.glow.save(M.out('textures/entity/martin/%s_glowmask.png' % name), optimize=True)
        M.write_json('animations/entity/%s.animation.json' % name, {'format_version': '1.8.0', 'animations': {a.name: a.to_json() for a in an}},
                     compact=True)
        print('%s: bones %d cubes %d tex %s anims %s' % (name, len(m.bones), sum(len(b.cubes) for b in m.bones.values()), m.tex_px,
                                                         ', '.join(a.name for a in an)))
    d = cavalry_mesh()
    print('martin_cavalry_rider mesh: %d boxes' % len(d['parts'][0]['boxes']))


if __name__ == '__main__':
    import gen_martin
    run(gen_martin, sys.argv[1:])
