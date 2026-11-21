#!/usr/bin/env python3
"""
T28 «Арис» — ключевые позы всех анимаций (animation.aris.*). Подключается из gen_aris_anims.main.
Оси (как в Blockbench): x — её правая рука, y — вверх, −z — вперёд. Углы суставов, °:
  rot x > 0 — у ног/рук: вперёд; у body/torso/head: назад (запрокинуть); у голени (*_shin) < 0 — колено сгибается;
  rot y > 0 — поворот влево; rot z > 0 у правых конечностей — наружу (у левых наружу — z < 0).
Молот в руке: ham = (хват, d — от навершия к голове, f — куда смотрит ударный боёк[, 'body' — координаты тела]); lh — левая рука
на рукояти (0..1); rh — правая (0..1, отпускает); vis = (молот в руке, молот на земле).
"""
import math

import numpy as np

G = None
AN = None


def K(*a, **kw):
    return AN.K(*a, **kw)


# ---------------------------------------------------------------- общие позы
STAND = dict(body=(0, 0, 0), bpos=(0, 0, 0), torso=(0, 0, 0), head=(0, 0, 0),
             right_leg=(0, 0, 5), left_leg=(0, 0, -5), right_shin=(-2, 0, 0), left_shin=(-2, 0, 0),
             larm=(4, 0, -9), lfore=(16, 0, 0), rarm=(0, 0, 8), rfore=(10, 0, 0), lh=0.0, rh=1.0, vis=(1, 0),
             hg={'rot': (0, 0, 0), 'pos': (0, 0, 0)}, rslide=0.0, rpole=(0.7, -0.3, 0.7), lpole=(-0.7, -0.3, 0.7))
GUARD_LEGS = dict(right_leg=(-8, 0, 7), left_leg=(14, 0, -6), right_shin=(-6, 0, 0), left_shin=(-14, 0, 0))
KNEEL = dict(bpos=(0, -5.6, 0), body=(-6, 0, 0), right_leg=(84, 0, 6), right_shin=(-86, 0, 0), left_leg=(-6, 0, -4), left_shin=(-92, 0, 0))


def S(**kw):
    d = dict(STAND)
    d.update(kw)
    return d


def rest_ground():
    """Покой: голова молота стоит на земле у правой ноги, рукоять наклонно вверх к руке."""
    d = AN.nrm((0.22, -0.72, -0.66))
    return (AN.ham_from_strike((12.0, 0.0, -9.5), d, (0.4, -1, 0.3)), d, (0.4, -1, 0.3))


def guard():
    """Боевая стойка: двуручный хват наискось перед собой, голова молота вверху слева."""
    return ((0.5, 18.0, -7.0), (0.45, 0.8, -0.4), (0.85, -0.45, 0.05))     # бойки влево-вправо (не к лицу)


def carry(bob=0.0):
    """На плече (в координатах тела): кулак у правого плеча спереди, рукоять лежит на наплечнике, голова за спиной."""
    return ((5.0, 21.0 + bob, -6.5), (0.2, 0.28, 0.94), (0.3, 0.95, -0.1), 'body')      # бойки вверх-вниз: не задевают шлем и косу


WINDUP = dict(body=(10, -12, 0), torso=(8, -6, 0), head=(8, 16, 0), bpos=(0, 0.6, 0.5), right_leg=(-14, 0, 8), left_leg=(22, 0, -6),
              right_shin=(-4, 0, 0), left_shin=(-10, 0, 0), rpole=(0.9, 0.1, 0.3), lpole=(-0.6, -0.3, -0.6))


RAISE = ((8.0, 21.0, -4.0), (0.35, 0.93, 0.1), (0, 0, -1))          # молот поднят вертикально у правого плеча (путь в замах — сбоку)
FWD_UP = ((4.5, 27.0, -9.0), (0.25, 0.7, -0.67), (0, 0.67, -0.74))  # молот пошёл вниз: над правым плечом спереди, дальше удар


def windup():
    """Замах для удара сверху (правка 20.11): молот над ПРАВЫМ плечом, голова молота за спиной — рукоять не проходит сквозь шлем и рога.
    Левая рука придерживает (lh≈0.45) и перехватывает рукоять на пути вниз."""
    return ((7.0, 27.0, 4.0), (0.3, 0.45, 0.84), (0.1, 0.85, -0.5))


def planted():
    """Молот стоит головой вниз справа от неё (как hammer_ground с поворотом HG_PLANT): хват в мире, d вниз, бойки вперёд-назад (−z/+z).
    Правка 20.11: раньше бойки смотрели вдоль x — левый боёк заходил в правое колено/голень (появление, сдача, мирный NPC)."""
    g = G.hg_world_rest((0, G.HAM_GRIP, 0))
    return (g, (0, -1, 0), (0, 0, -1))


HG_PLANT = {'rot': (0, 90, 0), 'pos': (0, 0, 0)}      # hammer_ground стоит головой вниз, повёрнут на 90° вокруг рукояти: бойки вдоль z


def fallen(ry=135.0, rot_extra=95.0):
    """hammer_ground: упал из стоячего положения набок (поворот вокруг точки касания), голова лежит на накладке."""
    return {'rot': (rot_extra, ry, 0), 'pos': (0, 3.8, 0)}


# ================================================================== анимации
def idle(rig):
    """Стойка по эталону Epic Fight (21.11): опирается на молот у правой ноги, вполоборота (плечи −28°, голова на цель), правая нога
    впереди, левая сзади, вес гуляет; дыхание — период 2.8 с: колени чуть пружинят (ground_fix опускает таз), грудь ≈0.02 L."""
    d = AN.nrm((0.50, -0.72, -0.48))                       # покой rest_ground, повёрнутый вместе с плечами на −28° (вправо)
    rg = (AN.ham_from_strike((15.0, 0.0, -2.8), d, (0.21, -1, 0.45)), d, (0.21, -1, 0.45))
    L = 2.8
    k = []
    for t in (0, 0.35, 0.7, 1.05, 1.4, 1.75, 2.1, 2.45, 2.8):
        br = math.sin(t / L * 2 * math.pi)
        b = 0.5 - 0.5 * br                                   # 0 — вдох (выше), 1 — выдох (колени мягче)
        sw = math.sin(t / L * 2 * math.pi + 1.1)
        k.append(K(t, 'io', **S(ham=rg, lh=0.0, body=(-2, -28 + 1.5 * sw, 0), torso=(1.0 * br, -4, 0),
                                head=(-3 + 1.5 * br, 30 + 3 * sw, 0),
                                right_leg=(20, 22, 5), left_leg=(-14, 20, -6), right_shin=(-16, 0, 0), left_shin=(-8, 0, 0),
                                larm=(4 + 2 * br, 0, -9), rpole=(0.9, -0.2, 0.4))))
    def breathe(t, pose, P):                                 # после ground_fix: таз чуть оседает на выдохе (≈0.25 ед.)
        b = 0.5 - 0.5 * math.sin(t / L * 2 * math.pi)
        bp = pose['body'].get('pos', (0, 0, 0))
        pose['body']['pos'] = (bp[0], bp[1] - 0.25 * b, bp[2])
    return AN.bake(rig, 'idle', L, k, loop=True, ground='feet', wind=0.25, extra=breathe, exact=True)


def walk(rig):
    keys = []
    L = 1.2
    for i in range(9):
        t = L * i / 8
        ph = 2 * math.pi * t / L
        s = math.sin(ph)
        keys.append(K(t, 'linear', **S(
            right_leg=(-30 * s, 0, 4), left_leg=(30 * s, 0, -4),
            right_shin=(-8 - 32 * max(0, math.sin(ph + 1.3)), 0, 0), left_shin=(-8 - 32 * max(0, math.sin(ph + 1.3 + math.pi)), 0, 0),
            body=(-4, 4 * s, 2 * math.cos(ph)), bpos=(0, -0.6 + 0.7 * abs(math.cos(ph)), 0),
            torso=(0, -5 * s, 0), head=(2, 3 * s, 0),
            larm=(26 * s, 0, -8), lfore=(18 + 10 * max(0, s), 0, 0),
            ham=carry(0.25 * abs(math.cos(ph))), rpole=(0.8, -0.5, 0.3))))
    return AN.bake(rig, 'walk', L, keys, loop=True, ground=None, wind=0.0)


def H(psi, pitch, gphi, gr, gy, dz=0.0, turn=1):
    """Молот по дуге вокруг тела (эталон Epic Fight, 21.11): хват — цилиндр (азимут gphi: 0 — перед, + влево; радиус gr; высота gy;
    dz — вынос вперёд вместе с тазом), голова молота — по азимуту psi и углу pitch (+ вверх), боёк смотрит по ходу удара
    (turn = +1: азимут растёт — справа налево)."""
    pr = math.radians(psi)
    g = (-math.sin(math.radians(gphi)) * gr, gy, -math.cos(math.radians(gphi)) * gr + dz)
    d = (-math.sin(pr) * math.cos(math.radians(pitch)), math.sin(math.radians(pitch)), -math.cos(pr) * math.cos(math.radians(pitch)))
    f = (-math.cos(pr) * turn, 0.0, math.sin(pr) * turn)
    return (g, d, f)


def slam(rig):
    """Удар по земле двумя руками по эталону Epic Fight (21.11). Тики прежние: windup 0.42, impact 0.75 (SLAM_IMPACT 15), волна от
    удара — кодом. Замах 0–0.45 (корпус назад и вправо, вес назад), взвод до 0.60 (левая нога отрывается), удар 0.60–0.75 (левая
    нога шагает, колени глубоко, корпус в наклон −24°), молот в земле до 1.15 (удержание тяжёлого), выдёргивает, отшаг, стойка к 2.2."""
    gd = guard()
    d_imp = (0.0, -0.42, -0.9)
    imp = (AN.ham_from_strike((0.8, 0.0, -24.0), d_imp, (0, -1, 0)), d_imp, (0, -1, 0))
    imp2 = (AN.ham_from_strike((0.8, 1.2, -24.0), d_imp, (0, -1, 0)), d_imp, (0, -1, 0.2))
    W2 = ((7.5, 27.0, 5.5), (0.28, 0.12, 0.95), (0.1, 0.98, -0.15))      # голова молота почти горизонтально за спиной
    k = [
        K(0.0, **S(ham=gd, lh=1, **GUARD_LEGS)),
        K(0.18, 'io', **S(ham=RAISE, lh=0.6, body=(4, -12, 0), torso=(4, -3, 0), head=(2, 12, 0), rpole=(0.9, -0.2, 0.3), lpole=(-0.7, -0.4, 0.5),
                           right_leg=(-8, 8, 7), left_leg=(14, 8, -6), right_shin=(-6, 0, 0), left_shin=(-14, 0, 0))),
        K(0.45, 'out3', **S(ham=windup(), lh=0.45, body=(12, -38, 0), torso=(8, -8, 0), head=(8, 26, 0), bpos=(0, 0.6, 1.2),
                             right_leg=(-16, 18, 8), left_leg=(18, 18, -6), right_shin=(-6, 0, 0), left_shin=(-12, 0, 0),
                             rpole=(0.9, 0.1, 0.3), lpole=(-0.6, -0.3, -0.6))),
        K(0.62, 'linear', **S(ham=W2, lh=0.45, body=(15, -44, 0), torso=(9, -9, 0), head=(9, 28, 0), bpos=(0, 0.6, 1.5),
                            right_leg=(-18, 20, 8), left_leg=(10, 20, -6), right_shin=(-8, 0, 0), left_shin=(-30, 0, 0))),
        K(0.69, 'in', **S(ham=FWD_UP, lh=1, body=(-8, -12, 0), torso=(-4, -2, 0), head=(4, 8, 0), bpos=(0, -0.5, -1.5),
                           right_leg=(-20, 6, 8), left_leg=(34, 6, -6), right_shin=(-12, 0, 0), left_shin=(-30, 0, 0),
                           rpole=(0.9, -0.2, 0.3), lpole=(-0.9, -0.2, 0.3))),
        K(0.75, 'linear', **S(ham=imp, lh=1, body=(-24, 8, 0), torso=(-7, 2, 0), head=(16, -2, 0), bpos=(0, -3.0, -3.0),
                            right_leg=(-10, -2, 10), left_leg=(56, -2, -8), right_shin=(-30, 0, 0), left_shin=(-56, 0, 0),
                            rpole=(0.8, -0.4, 0.3), lpole=(-0.8, -0.4, 0.3))),
        K(0.84, 'out', **S(ham=imp2, lh=1, body=(-21, 4, 0), torso=(-6, 2, 0), head=(14, -2, 0), bpos=(0, -2.6, -3.0),
                            right_leg=(-10, -2, 10), left_leg=(52, -2, -8), right_shin=(-27, 0, 0), left_shin=(-52, 0, 0))),
        K(1.15, 'io', **S(ham=imp, lh=1, body=(-22, 4, 0), torso=(-6, 2, 0), head=(14, -2, 0), bpos=(0, -2.8, -3.0),
                           right_leg=(-10, -2, 10), left_leg=(54, -2, -8), right_shin=(-28, 0, 0), left_shin=(-54, 0, 0))),
        K(1.45, 'io', **S(ham=((2.0, 14.0, -11.0), (0.1, 0.35, -0.93), (0, -1, 0.3)), lh=1, body=(-12, 0, 0), torso=(-3, 0, 0), head=(6, 0, 0),
                           bpos=(0, -1.5, -2.2), right_leg=(-12, 0, 9), left_leg=(36, 0, -7), right_shin=(-18, 0, 0), left_shin=(-36, 0, 0))),
        K(1.75, 'io', **S(ham=((1.0, 17.0, -8.5), (0.35, 0.7, -0.6), (0.9, -0.4, 0.05)), lh=1, body=(-4, -4, 0), bpos=(0, -0.4, -0.6),
                           right_leg=(-8, 0, 7), left_leg=(22, 0, -6), right_shin=(-8, 0, 0), left_shin=(-34, 0, 0))),
        K(2.2, 'io', **S(ham=gd, lh=1, **GUARD_LEGS)),
    ]
    return AN.bake(rig, 'slam', 2.2, k, loop=False, ground='feet', events={0.42: 'windup', 0.75: 'impact'}, dt=0.025, exact=True)


def swing(rig):
    """Горизонтальный размах справа налево по эталону Epic Fight (21.11). Тики прежние: windup 0.45, hit 0.62 (SWING_HIT 12).
    Замах 0–0.40 (плечи −90°, молот за спиной справа, вес назад), взвод до 0.50, удар 0.50–0.71 (таз ведёт, левая нога шагает,
    молот проходит ~280° — справа через перед налево), перехлёст до 0.80 (плечи +100°), тяжёлый молот провисает, отшаг, стойка к 2.1."""
    gd = guard()
    LG = dict(rpole=(0.6, -0.6, 0.5), lpole=(-0.3, -0.7, 0.6))
    k = [
        K(0.0, **S(ham=gd, lh=1, **GUARD_LEGS)),
        K(0.16, 'io', **S(ham=H(-70, -18, -40, 8.0, 15.0, 0.3), lh=1, body=(2, -34, 0), torso=(1, -4, 0), head=(0, 18, 0),
                           right_leg=(-10, 20, 8), left_leg=(12, 20, -6), right_shin=(-8, 0, 0), left_shin=(-12, 0, 0), **LG)),
        K(0.40, 'out3', **S(ham=H(-150, 14, -112, 8.4, 19.5, 1.0), lh=1, body=(6, -96, 0), torso=(2, -8, 0), head=(0, 44, 0),
                             bpos=(0, 0, 1.0), right_leg=(-12, 52, 8), left_leg=(8, 50, -6), right_shin=(-10, 0, 0), left_shin=(-12, 0, 0), **LG)),
        K(0.50, 'linear', **S(ham=H(-168, 18, -122, 8.5, 20.0, 1.3), lh=1, body=(7, -105, 0), torso=(2, -9, 0), head=(0, 46, 0),
                            bpos=(0, 0, 1.3), right_leg=(-12, 54, 8), left_leg=(4, 52, -6), right_shin=(-10, 0, 0), left_shin=(-30, 0, 0), **LG)),
        K(0.57, 'in', **S(ham=H(-100, 8, -72, 10.2, 18.5, -0.5), lh=1, body=(0, -55, 0), torso=(0, -4, 0), head=(0, 30, 0), bpos=(0, 0, -0.8),
                           right_leg=(-14, 22, 9), left_leg=(26, 20, -6), right_shin=(-14, 0, 0), left_shin=(-30, 0, 0),
                           rpole=(0.6, -0.7, 0.3), lpole=(-0.5, -0.7, 0.4))),
        K(0.63, 'linear', **S(ham=H(-2, 0, -24, 9.8, 17.0, -3.6), lh=1, body=(-10, 12, 0), torso=(-4, 6, 0), head=(4, -4, 0), bpos=(0, 0, -3.6),
                            right_leg=(-22, -8, 9), left_leg=(36, -8, -6), right_shin=(-18, 0, 0), left_shin=(-30, 0, 0),
                            rpole=(0.6, -0.7, 0.3), lpole=(-0.6, -0.7, 0.3))),
        K(0.71, 'out', **S(ham=H(86, -6, 48, 10.2, 16.0, -5.2), lh=1, body=(-14, 72, 0), torso=(-4, 12, 0), head=(6, -36, 0), bpos=(0, 0, -5.2),
                            right_leg=(-22, -42, 9), left_leg=(34, -36, -6), right_shin=(-20, 0, 0), left_shin=(-30, 0, 0),
                            rpole=(0.2, -0.8, 0.5), lpole=(-0.7, -0.6, 0.3))),
        K(0.80, 'out', **S(ham=H(118, -12, 76, 10.0, 15.5, -5.8), lh=1, body=(-14, 105, 0), torso=(-3, 14, 0), head=(6, -45, 0), bpos=(0, 0, -5.8),
                            right_leg=(-18, -56, 9), left_leg=(32, -50, -6), right_shin=(-18, 0, 0), left_shin=(-28, 0, 0))),
        K(0.95, 'io', **S(ham=H(108, -26, 68, 9.8, 14.6, -5.6), lh=1, body=(-12, 90, 0), torso=(-2, 10, 0), head=(6, -42, 0), bpos=(0, 0, -5.6))),
        K(1.25, 'io', **S(ham=H(96, -38, 58, 9.8, 14.0, -5.2), lh=1, body=(-10, 80, 0), torso=(-2, 8, 0), head=(6, -38, 0), bpos=(0, 0, -5.2),
                           right_shin=(-14, 0, 0), left_shin=(-24, 0, 0))),
        K(1.55, 'io', **S(ham=H(60, 10, 22, 9.4, 16.5, -2.5), lh=1, body=(-4, 40, 0), torso=(0, 4, 0), head=(2, -20, 0), bpos=(0, 0, -2.5),
                           right_leg=(-12, -20, 8), left_leg=(12, -20, -6), right_shin=(-10, 0, 0), left_shin=(-34, 0, 0))),
        K(1.75, 'io', **S(ham=((-1.0, 19.0, -8.0), (0.0, 0.9, -0.4), (1, 0, 0)), lh=1, body=(-2, 10, 0), torso=(0, 2, 0), head=(0, -6, 0),
                           bpos=(0, 0, -0.6), rpole=(0.4, -0.8, 0.4), lpole=(-0.7, -0.6, 0.3), **GUARD_LEGS)),
        K(2.1, 'io', **S(ham=gd, lh=1, **GUARD_LEGS)),
    ]
    return AN.bake(rig, 'swing', 2.1, k, loop=False, ground='feet', events={0.45: 'windup', 0.62: 'hit'}, dt=0.025, exact=True)


def cast(rig):
    """Каст: молот на плече, левая рука поднимается и сжимается в кулак (призыв наковален/клинков; событие cast в 0.8 с)."""
    k = [
        K(0.0, **S(ham=carry(), **GUARD_LEGS)),
        K(0.5, 'io', **S(ham=carry(-0.5), larm=(60, 0, -40), lfore=(70, 0, 0), torso=(-4, 8, 0), head=(-6, 6, 0), **GUARD_LEGS)),
        K(0.8, 'back', **S(ham=carry(0.4), larm=(168, -10, -18), lfore=(6, 0, 0), torso=(8, -4, 0), head=(8, -4, 0), body=(4, 0, 0),
                            right_leg=(-8, 0, 7), left_leg=(14, 0, -6), right_shin=(-6, 0, 0), left_shin=(-14, 0, 0))),
        K(1.15, 'io', **S(ham=carry(0.2), larm=(160, -10, -18), lfore=(10, 0, 0), torso=(6, -4, 0), head=(6, -4, 0), body=(3, 0, 0), **GUARD_LEGS)),
        K(1.6, 'io', **S(ham=carry(), **GUARD_LEGS)),
    ]
    return AN.bake(rig, 'cast', 1.6, k, loop=False, ground='feet', events={0.8: 'cast'})


def forge(rig):
    """Особое «Горн» (4.0 с): три ритмичных удара по земле (1.0, 1.8, 2.6 — strike), на 3.3 — кулак к небу (ignite)."""
    gd = guard()
    d_imp = (0.0, -0.45, -0.89)
    hit = lambda y: (AN.ham_from_strike((1.0, y, -19.5), d_imp, (0, -1, 0)), d_imp, (0, -1, 0))
    d_h = (0.1, -0.88, -0.46)                                              # держит: рукоять почти вертикально, навершие не в кирасе
    hold = lambda y: (AN.ham_from_strike((2.0, y, -15.0), d_h, (0, -1, 0)), d_h, (0, -1, 0))
    up = ((2.0, 25.0, -7.5), (0.0, 0.85, -0.5), (0, 0.5, -0.86))           # навершие не уходит в кирасу
    low = dict(body=(-12, 0, 0), torso=(-5, 0, 0), head=(12, 0, 0), bpos=(0, -2.2, -0.6), right_leg=(-8, 0, 10), left_leg=(40, 0, -8),
               right_shin=(-20, 0, 0), left_shin=(-40, 0, 0))
    high = dict(body=(4, 0, 0), torso=(4, 0, 0), head=(6, 0, 0), bpos=(0, -0.6, 0), right_leg=(-10, 0, 9), left_leg=(22, 0, -7),
                right_shin=(-8, 0, 0), left_shin=(-18, 0, 0))
    k = [K(0.0, **S(ham=gd, lh=1, **GUARD_LEGS)), K(0.7, 'io', **S(ham=up, lh=1, **high))]
    for ti in (1.0, 1.8, 2.6):
        k.append(K(ti, 'in3', **S(ham=hit(0.0), lh=1, **low)))
        k.append(K(ti + 0.12, 'out', **S(ham=hit(0.8), lh=1, **low)))
        if ti < 2.6:
            k.append(K(ti + 0.5, 'io', **S(ham=up, lh=1, **high)))
    k += [
        K(3.05, 'io', **S(ham=hold(1.5), lh=0.0, larm=(60, 0, -30), lfore=(60, 0, 0), **low)),
        K(3.3, 'back', **S(ham=hold(0.4), lh=0.0, larm=(172, -10, -12), lfore=(4, 0, 0), body=(-6, 0, 0), torso=(10, 0, 0), head=(22, 0, 0),
                            bpos=(0, -1.6, -0.3), right_leg=(-8, 0, 10), left_leg=(34, 0, -8), right_shin=(-16, 0, 0), left_shin=(-34, 0, 0))),
        K(4.0, 'io', **S(ham=hold(0.4), lh=0.0, larm=(166, -10, -12), lfore=(8, 0, 0), body=(-6, 0, 0), torso=(8, 0, 0), head=(18, 0, 0),
                          bpos=(0, -1.6, -0.3), right_leg=(-8, 0, 10), left_leg=(34, 0, -8), right_shin=(-16, 0, 0), left_shin=(-34, 0, 0))),
    ]
    return AN.bake(rig, 'forge', 4.0, k, loop='hold', ground='feet', events={1.0: 'strike', 1.8: 'strike', 2.6: 'strike', 3.3: 'ignite'})


def last_blow(rig):
    """Особое «Последний удар молота» (5.0 с): шаг в широкую стойку, медленный подъём молота над головой (заряд, дрожь),
    удар 4.0 (blow) — глубокий присед, молот в земле; 4.0–5.0 держит."""
    gd = guard()
    wide = dict(right_leg=(-14, 0, 16), left_leg=(18, 0, -16), right_shin=(-12, 0, 0), left_shin=(-18, 0, 0))
    over = ((8.5, 30.0, 3.5), (0.25, 0.7, 0.67), (0, 0.7, -0.7))            # над правым плечом: рукоять не проходит сквозь шлем и рога
    d_imp = (0.0, -0.45, -0.89)
    imp = (AN.ham_from_strike((0.5, 0.0, -23.0), d_imp, (0, -1, 0)), d_imp, (0, -1, 0))
    k = [K(0.0, **S(ham=gd, lh=1, **GUARD_LEGS)),
         K(0.6, 'io', **S(ham=gd, lh=1, bpos=(0, -1.8, 0), body=(-4, 0, 0), **wide))]
    for i, t in enumerate((1.4, 2.2, 3.0)):
        f = (i + 1) / 3
        g = np.array(gd[0]) * (1 - f) + np.array(over[0]) * f + np.array([0, 0, -3.0 * math.sin(math.pi * f)])   # руки впереди груди
        dd = AN.nrm(np.array(gd[1]) * (1 - f) + np.array(over[1]) * f)
        k.append(K(t, 'io', **S(ham=(g, dd, (0, 1, 0)), lh=1, bpos=(0, -1.8 + 1.4 * f, 0), body=(-4 + 14 * f, 0, 0), torso=(10 * f, 0, 0),
                               head=(-4 + 30 * f, 0, 0), rpole=(0.8, 0.3, 0.4), lpole=(-0.8, 0.3, 0.4), **wide)))
    for i, t in enumerate(np.arange(3.1, 3.75, 0.1)):         # дрожь на пике заряда
        j = 0.35 * (1 if i % 2 else -1)
        k.append(K(float(t), 'linear', **S(ham=((over[0][0] + j, over[0][1], over[0][2] - abs(j)), over[1], over[2]), lh=1, bpos=(0, -0.4, 0),
                                           body=(10 + j, 0, 0), torso=(10, 0, 0), head=(26, 0, 0), rpole=(0.8, 0.3, 0.4), lpole=(-0.8, 0.3, 0.4), **wide)))
    k += [
        K(3.85, 'in', **S(ham=((4.5, 29.0, -10.0), (0.15, 0.85, -0.5), (0, 0.5, -0.86)), lh=1, bpos=(0, -1.5, -1.0), body=(-10, 0, 0), torso=(-4, 0, 0),
                           head=(10, 0, 0), right_leg=(-10, 0, 16), left_leg=(34, 0, -14), right_shin=(-16, 0, 0), left_shin=(-30, 0, 0))),
        K(4.0, 'in3', **S(ham=imp, lh=1, bpos=(0, -4.5, -1.5), body=(-20, 0, 0), torso=(-10, 0, 0), head=(24, 0, 0),
                           right_leg=(-2, 0, 18), left_leg=(62, 0, -14), right_shin=(-40, 0, 0), left_shin=(-70, 0, 0))),
        K(5.0, 'out', **S(ham=imp, lh=1, bpos=(0, -4.2, -1.5), body=(-18, 0, 0), torso=(-8, 0, 0), head=(20, 0, 0),
                           right_leg=(-2, 0, 18), left_leg=(60, 0, -14), right_shin=(-38, 0, 0), left_shin=(-66, 0, 0))),
    ]
    return AN.bake(rig, 'last_blow', 5.0, k, loop='hold', ground='feet', events={0.6: 'charge', 3.1: 'peak', 4.0: 'blow'})


def phase2(rig):
    """Переход в фазу 2 (2.0 с): полный оборот с молотом на вытянутых руках и удар головой молота в землю (1.0, roar)."""
    gd = guard()
    out_ = ((0.0, 17.0, -10.5), (0.0, 0.1, -1.0), (-1, 0, 0), 'body')
    k = [K(0.0, **S(ham=gd, lh=1, **GUARD_LEGS))]
    for i, t in enumerate((0.2, 0.4, 0.6, 0.8)):
        k.append(K(t, 'linear' if i else 'in', **S(ham=out_, lh=1, body=(-6, -90 * (i + 1) + 30, 0), bpos=(0, -1.2, 0), torso=(0, 0, 0),
                                                    head=(4, 0, 0), right_leg=(-10, 0, 10), left_leg=(10, 0, -10), right_shin=(-8, 0, 0),
                                                    left_shin=(-8, 0, 0))))
    d_imp = (0.0, -0.55, -0.83)
    imp = (AN.ham_from_strike((1.0, 0.0, -19.0), d_imp, (0, -1, 0)), d_imp, (0, -1, 0))
    k += [
        K(1.0, 'in3', **S(ham=imp, lh=1, body=(-20, -360, 0), bpos=(0, -2.5, -0.8), head=(26, 0, 0), right_leg=(-6, 0, 10), left_leg=(42, 0, -8),
                           right_shin=(-22, 0, 0), left_shin=(-44, 0, 0))),
        K(1.4, 'out', **S(ham=imp, lh=0.0, larm=(30, 0, -60), lfore=(40, 0, 0), body=(-4, -360, 0), torso=(12, 0, 0), head=(30, 0, 0),
                           bpos=(0, -1.6, -0.5), right_leg=(-6, 0, 10), left_leg=(36, 0, -8), right_shin=(-18, 0, 0), left_shin=(-36, 0, 0))),
        K(2.0, 'io', **S(ham=gd, lh=1, body=(0, -360, 0), **GUARD_LEGS)),
    ]
    return AN.bake(rig, 'phase2', 2.0, k, loop=False, ground='feet', events={1.0: 'roar'})


def phase3(rig):
    """Переход в фазу 3 «Мифический сплав» (3.0 с): сжимается, 1.6 — распрямляется, руки в стороны (ignite: текстура → aris_mythic)."""
    hang = ((10.5, 13.0, -3.5), (0.35, -0.92, -0.2), (0, 0.2, -0.98))      # молот висит у правого бедра, навершие не в боку
    k = [
        K(0.0, **S(ham=guard(), lh=1, **GUARD_LEGS)),
        K(0.7, 'io', **S(ham=hang, lh=0.0, larm=(40, 0, -10), lfore=(90, 0, 0), body=(-20, 0, 0), torso=(-14, 0, 0), head=(-26, 0, 0), bpos=(0, -2.2, 0),
                          right_leg=(18, 0, 10), left_leg=(18, 0, -10), right_shin=(-34, 0, 0), left_shin=(-34, 0, 0))),
        K(1.4, 'io', **S(ham=hang, lh=0.0, larm=(46, 0, -8), lfore=(100, 0, 0), body=(-22, 0, 0), torso=(-16, 0, 0), head=(-28, 0, 0), bpos=(0, -2.4, 0),
                          right_leg=(20, 0, 10), left_leg=(20, 0, -10), right_shin=(-38, 0, 0), left_shin=(-38, 0, 0))),
        K(1.75, 'back', **S(ham=((13.0, 19.0, -1.0), (0.85, -0.5, -0.1), (0, -1, 0)), lh=0.0, larm=(10, 0, -78), lfore=(10, 0, 0), body=(10, 0, 0),
                             torso=(12, 0, 0), head=(30, 0, 0), bpos=(0, 0.4, 0), right_leg=(0, 0, 12), left_leg=(0, 0, -12), right_shin=(-4, 0, 0),
                             left_shin=(-4, 0, 0), rpole=(0.3, -0.2, 0.9))),
        K(3.0, 'io', **S(ham=((13.0, 18.0, -1.5), (0.85, -0.5, -0.15), (0, -1, 0)), lh=0.0, larm=(8, 0, -70), lfore=(14, 0, 0), body=(6, 0, 0),
                          torso=(8, 0, 0), head=(20, 0, 0), right_leg=(0, 0, 12), left_leg=(0, 0, -12), rpole=(0.3, -0.2, 0.9))),
    ]
    return AN.bake(rig, 'phase3', 3.0, k, loop=False, ground='feet', events={1.6: 'ignite'})


def kneel_ham():
    """Стоит на колене, правая рука на древке молота, поставленного головой вниз (hammer_ground в покое)."""
    p = planted()
    return dict(ham=p, rslide=8.5, rpole=(0.6, -0.4, 0.7), **KNEEL)


def spawn(rig):
    """Появление (9.0 с): из расплава поднимается на колене, опираясь на молот (2.0–4.5), встаёт (4.5–6.0), молот над головой,
    удар 7.0 (impact) — к 9.0 боевая стойка. События: emerge 2.0, kneel 4.5, horns 6.0 (рога загораются), impact 7.0, title 7.5."""
    kn = kneel_ham()
    under = dict(kn)
    under['bpos'] = (0, -40, 0)
    gd = guard()
    p = planted()
    d_imp = (0.0, -0.45, -0.89)
    imp = (AN.ham_from_strike((0.8, 0.0, -21.0), d_imp, (0, -1, 0)), d_imp, (0, -1, 0))
    under['hg'] = {'rot': (0, 0, 0), 'pos': (0, -40, 0)}
    under['ham'] = (p[0] + np.array([0, -40.0, 0]), p[1], p[2])
    kn2 = dict(kn, hg=HG_PLANT)
    under = S(**under)
    under.update(vis=(1, 0), head=(-30, 0, 0), torso=(-10, 0, 0))
    k = [
        K(0.0, **under), K(2.0, 'linear', **under),
        K(4.5, 'out', **S(**dict(kn2, head=(-24, 0, 0), torso=(-10, 0, 0)))),
        K(5.2, 'io', **S(**dict(kn2, head=(0, 0, 0), torso=(-4, 0, 0)))),
        K(6.0, 'io', **S(ham=(p[0] + np.array([0, 2.0, 0]), p[1], p[2]), rslide=8.5, rpole=(0.6, -0.4, 0.7), head=(6, 0, 0), **GUARD_LEGS)),
        # правка 20.11: молот не крутится через корпус — поднимается вертикально у правого бока (бойки вперёд-назад), уходит
        # на правое плечо за спину и только оттуда — замах из-за головы и удар вперёд (impact по-прежнему 7.0)
        K(6.3, 'io', **S(ham=((10.0, 14.5, -1.5), (0.1, 0.98, 0.15), (0, 0, -1)), rpole=(0.9, -0.4, 0.2), head=(4, 0, 0), torso=(2, 0, 0),
                          **GUARD_LEGS)),
        K(6.55, 'io', **S(ham=((7.5, 24.0, 1.5), (0.35, 0.5, 0.8), (0, 0.85, -0.5)), lh=0.5, rpole=(0.9, 0.0, 0.4), lpole=(-0.8, 0.0, 0.5),
                           body=(6, -8, 0), torso=(6, -4, 0), head=(10, 6, 0), right_leg=(-12, 0, 8), left_leg=(18, 0, -6),
                           right_shin=(-4, 0, 0), left_shin=(-8, 0, 0))),
        K(6.75, 'io', **S(ham=windup(), lh=0.45, **WINDUP)),
        K(6.88, 'in', **S(ham=FWD_UP, lh=1, body=(-8, 0, 0), torso=(-4, 0, 0), head=(4, 0, 0),
                           bpos=(0, -0.5, -0.5), right_leg=(-18, 0, 8), left_leg=(30, 0, -6), right_shin=(-10, 0, 0), left_shin=(-24, 0, 0),
                           rpole=(0.9, -0.2, 0.3), lpole=(-0.9, -0.2, 0.3))),
        K(7.0, 'in3', **S(ham=imp, lh=1, body=(-18, 0, 0), torso=(-6, 0, 0), head=(14, 0, 0), bpos=(0, -3.0, -1.0), right_leg=(-6, 0, 10),
                           left_leg=(52, 0, -8), right_shin=(-26, 0, 0), left_shin=(-52, 0, 0))),
        K(7.6, 'out', **S(ham=imp, lh=1, body=(-15, 0, 0), torso=(-4, 0, 0), head=(24, 0, 0), bpos=(0, -2.6, -1.0), right_leg=(-6, 0, 10),
                           left_leg=(48, 0, -8), right_shin=(-24, 0, 0), left_shin=(-48, 0, 0))),
        K(9.0, 'io', **S(ham=gd, lh=1, **GUARD_LEGS)),
    ]

    def gm(t):
        return 'kneel' if 4.5 <= t <= 5.3 else ('feet' if t > 5.3 else None)
    return AN.bake(rig, 'spawn', 9.0, k, loop='hold', ground=gm, wind=0.0,
                   events={2.0: 'emerge', 4.5: 'kneel', 6.0: 'horns', 7.0: 'impact', 7.5: 'title'})


def surrender(rig):
    """Сдача (5.0 с, держит последний кадр): пошатнулась (0–0.4), ставит молот головой вниз и опускается на колено (0.4–1.2),
    1.2 — молот «отдан» земле (в руке скрыть, hammer_ground показать — в анимации это scale), опирается; 2.0 horns_dim,
    2.6 horns_out; 2.6–3.1 рука соскальзывает, молот падает (3.2 — hammer_drop, удар о землю); 3.6 — speak (фраза). Дальше держит."""
    gd = guard()
    kn = kneel_ham()
    stag = ((6.0, 12.5, -6.0), (0.4, -0.6, -0.7), (0, -0.76, 0.65))       # бойки в плоскости yz: не задевают колено
    fall = fallen()
    kneel_body = dict(KNEEL)
    bow = dict(head=(-34, 0, 0), torso=(-14, 0, 0))
    lknee = dict(larm=(40, 0, -8), lfore=(50, 0, 0))            # левая рука на колене
    k = [
        K(0.0, **S(ham=gd, lh=1, **GUARD_LEGS)),
        K(0.4, 'out', **S(ham=stag, lh=0.0, larm=(-20, 0, -30), lfore=(30, 0, 0), body=(10, 0, 0), torso=(8, 0, 0), head=(14, 0, 0),
                           bpos=(0, -0.5, 1.2), right_leg=(-20, 0, 8), left_leg=(6, 0, -8), right_shin=(-20, 0, 0), left_shin=(-6, 0, 0))),
        K(1.2, 'io', **S(vis=(1, 0), lh=0.0, head=(-20, 0, 0), torso=(-10, 0, 0), **lknee, **kn, hg=HG_PLANT)),
        K(1.25, 'linear', **S(vis=(0, 1), lh=0.0, head=(-20, 0, 0), torso=(-10, 0, 0), **lknee, **kn, hg=HG_PLANT)),
        K(2.0, 'io', **S(vis=(0, 1), lh=0.0, **bow, **lknee, **kn, hg=HG_PLANT)),
        K(2.6, 'io', **S(vis=(0, 1), lh=0.0, head=(-40, 0, 0), torso=(-18, 0, 0), **lknee, **kn, hg=HG_PLANT)),
        K(3.0, 'in', **S(vis=(0, 1), lh=0.0, rh=0.0, rarm=(14, 0, 14), rfore=(20, 0, 0), head=(-42, 0, 0), torso=(-20, 0, 0), **lknee, **kn,
                          hg={'rot': (fall['rot'][0] * 0.7, fall['rot'][1], 0), 'pos': (0, 1.6, 0)})),
        K(3.2, 'in', **S(vis=(0, 1), lh=0.0, rh=0.0, rarm=(10, 0, 12), rfore=(16, 0, 0), head=(-42, 0, 0), torso=(-20, 0, 0), **lknee, **kn, hg=fall)),
        K(3.32, 'out', **S(vis=(0, 1), lh=0.0, rh=0.0, rarm=(10, 0, 12), rfore=(16, 0, 0), head=(-40, 0, 0), torso=(-19, 0, 0), **lknee, **kn,
                            hg={'rot': (fall['rot'][0] - 6, fall['rot'][1], 0), 'pos': (0, 4.3, 0)})),
        K(3.45, 'in', **S(vis=(0, 1), lh=0.0, rh=0.0, rarm=(10, 0, 12), rfore=(16, 0, 0), head=(-38, 0, 0), torso=(-18, 0, 0), **lknee, **kn, hg=fall)),
        K(3.6, 'io', **S(vis=(0, 1), lh=0.0, rh=0.0, rarm=(6, 0, 10), rfore=(14, 0, 0), head=(-30, 0, 0), torso=(-16, 0, 0), **lknee, **kn, hg=fall)),
        K(5.0, 'io', **S(vis=(0, 1), lh=0.0, rh=0.0, rarm=(4, 0, 9), rfore=(12, 0, 0), head=(-36, 0, 0), torso=(-18, 0, 0), **lknee, **kn, hg=fall)),
    ]

    def gm(t):
        return 'feet' if t < 0.5 else 'kneel'
    return AN.bake(rig, 'surrender', 5.0, k, loop='hold', ground=gm,
                   events={0.4: 'stagger', 1.2: 'plant', 2.0: 'horns_dim', 2.6: 'horns_out', 3.2: 'hammer_drop', 3.6: 'speak'})


def npc_stand(rig):
    """Мирный NPC: стоит у молота, поставленного головой вниз справа, правая рука на древке, левая — на бедре; оглядывается."""
    k = []
    for t in (0, 1, 2, 3, 4):
        ph = 2 * math.pi * t / 4
        k.append(K(t, 'io', **S(ham=planted(), rslide=6.5, vis=(0, 1), hg=HG_PLANT, rpole=(0.5, -0.6, 0.6), larm=(-6, 0, -34), lfore=(80, 0, 0),
                                 body=(0, 0, 3), bpos=(0, -0.2 + 0.2 * math.cos(ph), 0), right_leg=(0, 0, 4), left_leg=(6, 0, -8), left_shin=(-10, 0, 0),
                                 torso=(1.5 * math.sin(ph), 0, -2), head=(-4 + 3 * math.sin(ph * 2), 22 * math.sin(ph), 4))))
    return AN.bake(rig, 'npc_stand', 4.0, k, loop=True, ground='feet', wind=0.3)


def npc_sit(rig):
    """Мирный NPC: сидит на голове лежащего молота (молот на земле под ней), локоть на колене, голова чуть набок."""
    # куда положить hammer_ground, чтобы центр головы оказался под ней (0, 3.4, 1.0); рукоять уходит вправо-вперёд
    R = AN.euler((G.HG_REST[0] + 95, 60, 0))
    head_rest = G.hg_offset((0, G.HAM_HEAD, 0))
    want = np.array([0.0, 2.9, 1.0])
    pos = want - (np.array(G.HG_PIVOT) + R @ head_rest)
    hg = {'rot': (95, 60, 0), 'pos': tuple(pos)}
    k = []
    for t in (0, 1, 2, 3, 4):
        ph = 2 * math.pi * t / 4
        k.append(K(t, 'io', **S(vis=(0, 1), hg=hg, rh=0.0, bpos=(0, -4.25 + 0.12 * math.cos(ph), 1.0), body=(-12, 0, 0),
                                 right_leg=(78, 0, 14), right_shin=(-96, 0, 0), left_leg=(84, 0, -10), left_shin=(-104, 0, 0),
                                 rarm=(62, 0, 6), rfore=(92, 0, 0), larm=(40, 0, -10), lfore=(36, 0, 0),
                                 torso=(-6 + 1.5 * math.sin(ph), 0, 0), head=(-6 + 2 * math.sin(ph), -10 + 8 * math.sin(ph / 2), 8))))
    return AN.bake(rig, 'npc_sit', 4.0, k, loop=True, ground=None, wind=0.25)


# ================================================================== +4 заклинания (владелец 20.11)
def billet(rig):
    """«Раскалённая заготовка» (1.4 с): молот на плече, левой рукой из-за бедра бросает слиток снизу вперёд (throw 0.7)."""
    k = [
        K(0.0, **S(ham=carry(), **GUARD_LEGS)),
        K(0.45, 'io', **S(ham=carry(-0.4), larm=(-40, 0, -24), lfore=(30, 0, 0), torso=(4, -16, 0), head=(-4, 10, 0), body=(0, -10, 0),
                           right_leg=(-12, 0, 7), left_leg=(10, 0, -6), right_shin=(-10, 0, 0), left_shin=(-6, 0, 0))),
        K(0.7, 'out3', **S(ham=carry(0.3), larm=(96, 0, -12), lfore=(10, 0, 0), torso=(-6, 14, 0), head=(-2, -8, 0), body=(-8, 10, 0),
                            bpos=(0, -0.8, -0.6), right_leg=(-18, 0, 7), left_leg=(30, 0, -6), right_shin=(-12, 0, 0), left_shin=(-26, 0, 0))),
        K(1.4, 'io', **S(ham=carry(), **GUARD_LEGS)),
    ]
    return AN.bake(rig, 'billet', 1.4, k, loop=False, ground='feet', events={0.7: 'throw'})


def chains(rig):
    """«Цепи кузни» (1.6 с): бьёт навершием молота в землю, левый кулак рывком вверх — цепи вырываются из земли (chains 0.8)."""
    d_dn = (0.15, -0.95, -0.25)
    pomm = ((8.5, 14.0, -5.0), (0.2, 0.95, 0.2), (0, 0, -1))             # молот головой вверх у правого плеча, навершие у земли; бойки вперёд-назад
    hitp = ((8.0, 11.5, -4.5), (0.18, 0.97, 0.15), (0, 0, -1))
    k = [
        K(0.0, **S(ham=carry(), **GUARD_LEGS)),
        K(0.5, 'io', **S(ham=pomm, larm=(40, 0, -20), lfore=(80, 0, 0), body=(6, 0, 0), torso=(6, 0, 0), head=(6, 0, 0),
                          right_leg=(-8, 0, 8), left_leg=(14, 0, -8), right_shin=(-6, 0, 0), left_shin=(-12, 0, 0))),
        K(0.8, 'in3', **S(ham=hitp, larm=(150, 0, -30), lfore=(30, 0, 0), body=(-10, 0, 0), torso=(-4, 0, 0), head=(14, 0, 0), bpos=(0, -2.0, -0.3),
                           right_leg=(-8, 0, 10), left_leg=(30, 0, -8), right_shin=(-20, 0, 0), left_shin=(-32, 0, 0))),
        K(1.1, 'out', **S(ham=hitp, larm=(140, 0, -26), lfore=(40, 0, 0), body=(-8, 0, 0), torso=(-2, 0, 0), head=(10, 0, 0), bpos=(0, -1.8, -0.3),
                           right_leg=(-8, 0, 10), left_leg=(28, 0, -8), right_shin=(-18, 0, 0), left_shin=(-28, 0, 0))),
        K(1.6, 'io', **S(ham=carry(), **GUARD_LEGS)),
    ]
    return AN.bake(rig, 'chains', 1.6, k, loop=False, ground='feet', events={0.8: 'chains'})


def quench(rig):
    """«Закалка» (1.8 с): молот в землю, левая ладонь над головой — вода окатывает её (splash 0.8), пар; голова чуть вниз."""
    rg = rest_ground()
    k = [
        K(0.0, **S(ham=guard(), lh=1, **GUARD_LEGS)),
        K(0.22, 'io', **S(ham=RAISE, lh=0.3, larm=(120, 0, -10), lfore=(40, 0, 0), head=(8, 0, 0), torso=(4, 0, 0), rpole=(0.9, -0.3, 0.2))),
        K(0.45, 'io', **S(ham=rg, larm=(176, 0, -6), lfore=(40, 0, 0), head=(16, 0, 0), torso=(8, 0, 0))),
        K(0.8, 'out', **S(ham=rg, larm=(168, 0, -10), lfore=(70, 0, 0), head=(-20, 0, 0), torso=(-10, 0, 0), body=(-6, 0, 0), bpos=(0, -0.8, 0),
                           right_shin=(-10, 0, 0), left_shin=(-10, 0, 0))),
        K(1.3, 'io', **S(ham=rg, larm=(30, 0, -36), lfore=(40, 0, 0), head=(-8, 0, 0), torso=(-4, 0, 0))),
        K(1.55, 'io', **S(ham=RAISE, lh=0.3, larm=(20, 0, -30), lfore=(40, 0, 0), head=(-2, 0, 0), rpole=(0.9, -0.3, 0.2), **GUARD_LEGS)),
        K(1.8, 'io', **S(ham=guard(), lh=1, **GUARD_LEGS)),
    ]
    return AN.bake(rig, 'quench', 1.8, k, loop=False, ground='feet', events={0.8: 'splash'})


def bellows(rig):
    """«Мехи» (1.5 с): 0–0.8 замах молотом низко назад (предупреждение-конус), 0.8 (gust) — мощный взмах снизу-вперёд, порыв жара."""
    low = ((9.5, 10.0, 4.5), (0.45, -0.3, 0.84), (0, -1, 0))
    up = ((1.5, 24.0, -8.0), (0.0, 0.75, -0.66), (0, 0.66, 0.75))
    wide = dict(right_leg=(-16, 0, 14), left_leg=(28, 0, -12), right_shin=(-14, 0, 0), left_shin=(-30, 0, 0))
    k = [
        K(0.0, **S(ham=guard(), lh=1, **GUARD_LEGS)),
        K(0.6, 'io', **S(ham=low, lh=0.25, larm=(-30, 0, -40), lfore=(30, 0, 0), body=(-14, -20, 0), torso=(-6, -10, 0), head=(14, 22, 0), bpos=(0, -2.4, 0.4), rpole=(0.8, -0.5, 0.3),
                          lpole=(-0.2, -0.8, 0.5), **wide)),
        K(0.8, 'in3', **S(ham=up, lh=1, body=(6, 8, 0), torso=(8, 4, 0), head=(4, -6, 0), bpos=(0, -1.0, -1.0), rpole=(0.8, -0.3, 0.4), **wide)),
        K(1.0, 'out', **S(ham=((1.5, 25.0, -7.5), (0.0, 0.8, -0.6), (0, 0.6, 0.8)), lh=1, body=(8, 8, 0), torso=(8, 4, 0), head=(6, -6, 0),
                           bpos=(0, -0.8, -1.0), **wide)),
        K(1.5, 'io', **S(ham=guard(), lh=1, **GUARD_LEGS)),
    ]
    return AN.bake(rig, 'bellows', 1.5, k, loop=False, ground='feet', events={0.0: 'warn', 0.8: 'gust'})


# ---------------------------------------------------------------- добивание (владелец 20.11; ТЗ T28 «Добивание»)
# Жертва лежит ничком ПЕРЕД ней: таз в FIN_DIST бл. по взгляду, голова к ней (жертва повёрнута лицом к Арис), спина — «заготовка».
FIN_DIST = 1.9                                   # = ArisMath.FINISHER_DIST (было 1.6: голова жертвы упиралась в её колени)
FIN_HIT = (0.6, 2.0, -FIN_DIST * 16 + 10.0)      # точка удара (ед. модели, −z — вперёд): низ бойка ложится на середину спины лежащей жертвы (≈4.3 над землёй)
FIN_EVENTS = {0.0: 'pull', 0.7: 'windup', 1.5: 'slam', 2.2: 'kill'}


def finisher(rig):
    """Добивание (2.4 с = 48 тиков): 0–0.7 (pull) — левая ладонь к жертве: жар и цепи тянут её и прижимают к земле; 0.7 (windup) —
    замах из-за правого плеча (как slam); 1.5 (slam) — молот сверху в спину жертвы, как по заготовке на наковальне: глубокий присед,
    искры, рога вспыхивают; 1.6–2.2 — давит всем весом; 2.2 (kill) — смерть; 2.4 — отпускает давление (держит последний кадр)."""
    gd = guard()
    d_imp = (0.0, -0.5, -0.87)
    f_imp = (0, -1, 0)
    rg = rest_ground()                                                     # 0–0.7: голова молота на земле у правой ноги (как idle)
    hit = lambda dy: (AN.ham_from_strike((FIN_HIT[0], FIN_HIT[1] + dy, FIN_HIT[2]), d_imp, f_imp), d_imp, f_imp)
    reach = dict(larm=(78, 0, -6), lfore=(8, 0, 0), body=(-6, 8, 0), torso=(-4, 4, 0), head=(-14, -6, 0), bpos=(0, -0.6, -0.4),
                 right_leg=(-10, 0, 8), left_leg=(22, 0, -6), right_shin=(-6, 0, 0), left_shin=(-16, 0, 0))
    push = dict(reach, larm=(52, 0, -6), lfore=(14, 0, 0), body=(-10, 8, 0), head=(-20, -6, 0), bpos=(0, -1.2, -0.6))
    LEAN, HX, BZ = -20, 18, 1.0                                           # наклон корпуса, голова (назад), сдвиг тела назад (рукоять мимо шлема)
    low = dict(body=(LEAN, 0, 0), torso=(-6, 0, 0), head=(HX, 0, 0), bpos=(0, -3.4, BZ), right_leg=(-6, 0, 10), left_leg=(40, 0, -8),
               right_shin=(-26, 0, 0), left_shin=(-46, 0, 0), rpole=(0.8, -0.4, 0.3), lpole=(-0.8, -0.4, 0.3))
    k = [
        K(0.0, **S(ham=gd, lh=1, **GUARD_LEGS)),
        K(0.18, 'io', **S(ham=((11.0, 15.0, -7.0), (0.55, -0.35, -0.76), (0.2, -0.9, 0.3)), lh=0.4, rpole=(0.9, -0.2, 0.4),
                           **dict(reach, larm=(40, 0, -10)))),
        K(0.35, 'io', **S(ham=rg, lh=0.0, rpole=(0.9, -0.2, 0.4), **reach)),
        K(0.7, 'io', **S(ham=rg, lh=0.0, rpole=(0.9, -0.2, 0.4), **push)),
        K(0.9, 'io', **S(ham=RAISE, lh=0.6, body=(4, -6, 0), torso=(4, -3, 0), head=(-4, 8, 0), rpole=(0.9, -0.2, 0.3),
                          lpole=(-0.7, -0.4, 0.5), **GUARD_LEGS)),
        K(1.2, 'io', **S(ham=windup(), lh=0.45, **dict(WINDUP, head=(-2, 16, 0)))),
        K(1.38, 'in', **S(ham=FWD_UP, lh=1, body=(-8, 0, 0), torso=(-4, 0, 0), head=(8, 0, 0), bpos=(0, -0.5, -0.5), right_leg=(-18, 0, 8),
                           left_leg=(30, 0, -6), right_shin=(-10, 0, 0), left_shin=(-24, 0, 0), rpole=(0.9, -0.2, 0.3), lpole=(-0.9, -0.2, 0.3))),
        K(1.5, 'in3', **S(ham=hit(0.0), lh=1, **low)),
        K(1.62, 'out', **S(ham=hit(0.9), lh=1, **dict(low, bpos=(0, -3.2, BZ), head=(HX + 2, 0, 0)))),
        K(1.85, 'io', **S(ham=hit(-0.5), lh=1, **dict(low, body=(LEAN - 2, 0, 0), bpos=(0, -3.6, BZ - 0.1)))),
        K(2.2, 'io', **S(ham=hit(-0.6), lh=1, **dict(low, body=(LEAN - 2, 0, 0), bpos=(0, -3.6, BZ - 0.1), head=(HX + 2, 0, 0)))),
        K(2.4, 'io', **S(ham=hit(0.3), lh=1, **dict(low, body=(LEAN - 1, 0, 0), head=(HX, 0, 0)))),
    ]
    return AN.bake(rig, 'finisher', 2.4, k, loop='hold', ground='feet', events=FIN_EVENTS)


def victim_emote():
    """Поза жертвы добивания Арис (PlayerAnimator irons_spellbooks:pohsmp_aris_finisher_victim, 48 тиков, держит последний кадр).
    Жертва повёрнута ЛИЦОМ к Арис (код: yaw жертвы на неё), таз — в точке holdPoint (1.9 бл. перед ней).
    0–14 (pull) — скована, её тянет (как held); 14–24 — прижата к земле: на коленях, ладони в землю, голова поднята к ней;
    27–30 — удар молотом в спину (slam 30): распластана ничком, руки в стороны, лицом в сторону; 30–34 — отдача; 44 (kill) — обмякла."""
    P = lambda p, y=0.0, r=0.0, b=None: {'pitch': p, 'yaw': y, 'roll': r, **({} if b is None else {'bend': b})}
    held = dict(rightArm=P(-12, 0, 118, -4), leftArm=P(-12, 0, -118, -4), torso=P(-12, 0, 0, -6), head=P(-38, 0, 0),
                rightLeg=P(8, 0, 4, 14), leftLeg=P(-4, 0, -4, 8), body={'y': 0.45})
    down = dict(rightArm=P(-62, 0, 14, -10), leftArm=P(-62, 0, -14, -10), torso=P(58, 0, 0, 10), head=P(-52, 0, 0),
                rightLeg=P(-6, 0, 4, 88), leftLeg=P(-6, 0, -4, 88), body={'y': -0.36})
    brace = dict(rightArm=P(-70, 0, 18, -14), leftArm=P(-70, 0, -18, -14), torso=P(66, 0, 0, 12), head=P(-58, 0, 0),
                 rightLeg=P(-4, 0, 4, 90), leftLeg=P(-4, 0, -4, 90), body={'y': -0.4})
    flat = dict(rightArm=P(-96, 0, 74, -6), leftArm=P(-96, 0, -74, -6), torso=P(90, 0, 0, 0), head=P(-6, 62, 0),
                rightLeg=P(90, 0, 6, 4), leftLeg=P(90, 0, -6, 4), body={'y': -0.62})
    squash = dict(flat, rightArm=P(-100, 0, 82, -10), leftArm=P(-100, 0, -82, -10), head=P(-2, 66, 0), body={'y': -0.66},
                  rightLeg=P(88, 0, 8, 10), leftLeg=P(88, 0, -8, 10))
    limp = dict(flat, rightArm=P(-94, 0, 70, -2), leftArm=P(-94, 0, -70, -2), head=P(-4, 70, 0), body={'y': -0.63},
                rightLeg=P(90, 0, 5, 2), leftLeg=P(90, 0, -5, 2))
    seq = [(0, held, 'easeInOutSine'), (12, held, 'easeInOutSine'), (18, down, 'easeInQuad'), (24, brace, 'easeInOutSine'),
           (27, brace, 'easeInOutSine'), (30, squash, 'easeInQuad'), (34, flat, 'easeOutCubic'), (40, flat, 'easeInOutSine'),
           (44, limp, 'easeInOutSine'), (48, limp, 'easeInOutSine')]
    moves = []
    for tick, p, ease in seq:
        for part, v in p.items():
            moves.append({'tick': tick, 'easing': ease, part: dict(v)})
    return {'version': 3, 'name': 'pohsmp_aris_finisher_victim', 'author': 'pohsmp_core',
            'emote': {'beginTick': 0, 'endTick': 48, 'stopTick': 48, 'degrees': True, 'easeBeforeKeyframe': True, 'moves': moves}}


ALL = (idle, walk, slam, swing, cast, forge, last_blow, phase2, phase3, spawn, surrender, npc_stand, npc_sit, billet, chains, quench, bellows,
       finisher)


def all_anims(rig):
    out = []
    for f in ALL:
        out.append(f(rig))
    return out
