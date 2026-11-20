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
    return (AN.ham_from_strike((10.5, 0.0, -9.5), d, (0.4, -1, 0.3)), d, (0.4, -1, 0.3))


def guard():
    """Боевая стойка: двуручный хват наискось перед собой, голова молота вверху слева."""
    return ((0.5, 18.0, -7.0), (0.45, 0.8, -0.4), (0.6, -0.3, 0.75))


def carry(bob=0.0):
    """На плече (в координатах тела): кулак у правого плеча спереди, рукоять лежит на наплечнике, голова за спиной."""
    return ((5.0, 21.0 + bob, -6.5), (0.18, 0.34, 0.92), (0.9, 0.35, -0.25), 'body')


def planted():
    """Молот стоит головой вниз (как кость hammer_ground в покое): хват в мире, d вниз, боёк вдоль x."""
    g = np.array(G.HG_PIVOT) + np.array(G.hg_local((0, G.HAM_GRIP, 0)))
    return (g, (0, -1, 0), (1, 0, 0))


def fallen(ry=135.0, rot_extra=95.0):
    """hammer_ground: упал из стоячего положения набок (поворот вокруг точки касания), голова лежит на накладке."""
    return {'rot': (rot_extra, ry, 0), 'pos': (0, 3.8, 0)}


# ================================================================== анимации
def idle(rig):
    rg = rest_ground()
    k = [K(t, 'io', **S(ham=rg, lh=0.0, torso=(1.5 * math.sin(t / 3.2 * 2 * math.pi), 0, 0),
                         head=(-3 + 2 * math.sin(t / 3.2 * 2 * math.pi + 1), 6 * math.sin(t / 3.2 * 2 * math.pi), 0),
                         bpos=(0, -0.25 + 0.25 * math.cos(t / 3.2 * 2 * math.pi), 0),
                         larm=(4 + 2 * math.sin(t / 3.2 * 2 * math.pi), 0, -9), rpole=(0.9, -0.2, 0.4)))
         for t in (0, 0.8, 1.6, 2.4, 3.2)]
    return AN.bake(rig, 'idle', 3.2, k, loop=True, ground='feet', wind=0.25)


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


def slam(rig):
    """Удар по земле двумя руками: замах из-за головы, удар в 0.75 с (событие impact), отдача."""
    gd = guard()
    d_imp = (0.0, -0.42, -0.9)
    imp = (AN.ham_from_strike((0.8, 0.0, -20.0), d_imp, (0, -1, 0)), d_imp, (0, -1, 0))
    imp2 = (AN.ham_from_strike((0.8, 1.0, -20.0), d_imp, (0, -1, 0)), d_imp, (0, -1, 0.2))
    k = [
        K(0.0, **S(ham=gd, lh=1, **GUARD_LEGS)),
        K(0.42, 'io', **S(ham=((2.0, 29.0, 3.0), (0.05, 0.42, 0.9), (0, 1, 0)), lh=1, body=(12, 0, 0), torso=(10, 0, 0), head=(14, 0, 0),
                           bpos=(0, 0.6, 0.5), right_leg=(-14, 0, 8), left_leg=(22, 0, -6), right_shin=(-4, 0, 0), left_shin=(-10, 0, 0),
                           rpole=(0.8, 0.2, 0.4), lpole=(-0.8, 0.2, 0.4))),
        K(0.62, 'in', **S(ham=((1.5, 27.0, -8.0), (0.0, 0.7, -0.72), (0, 0.6, -0.8)), lh=1, body=(-8, 0, 0), torso=(-4, 0, 0), head=(4, 0, 0),
                           bpos=(0, -0.5, -0.5), right_leg=(-18, 0, 8), left_leg=(30, 0, -6), right_shin=(-10, 0, 0), left_shin=(-24, 0, 0),
                           rpole=(0.9, -0.2, 0.3), lpole=(-0.9, -0.2, 0.3))),
        K(0.75, 'in3', **S(ham=imp, lh=1, body=(-26, 0, 0), torso=(-8, 0, 0), head=(18, 0, 0), bpos=(0, -3.0, -1.0),
                            right_leg=(-6, 0, 10), left_leg=(52, 0, -8), right_shin=(-26, 0, 0), left_shin=(-52, 0, 0),
                            rpole=(0.8, -0.4, 0.3), lpole=(-0.8, -0.4, 0.3))),
        K(0.92, 'out', **S(ham=imp2, lh=1, body=(-22, 0, 0), torso=(-6, 0, 0), head=(14, 0, 0), bpos=(0, -2.6, -1.0),
                            right_leg=(-6, 0, 10), left_leg=(48, 0, -8), right_shin=(-24, 0, 0), left_shin=(-48, 0, 0))),
        K(1.6, 'io', **S(ham=gd, lh=1, **GUARD_LEGS)),
    ]
    return AN.bake(rig, 'slam', 1.6, k, loop=False, ground='feet', events={0.42: 'windup', 0.75: 'impact'})


def swing(rig):
    """Горизонтальный размах справа налево (удар в 0.62 с, событие hit)."""
    gd = guard()
    k = [
        K(0.0, **S(ham=gd, lh=1, **GUARD_LEGS)),
        K(0.45, 'io', **S(ham=((10.0, 18.0, 4.0), (0.55, 0.25, 0.8), (0.75, 0, -0.6)), lh=1, body=(0, -38, 0), torso=(0, -14, 0), head=(0, 30, 0),
                           right_leg=(-12, 0, 12), left_leg=(18, 0, -8), right_shin=(-10, 0, 0), left_shin=(-10, 0, 0), bpos=(0, -1.2, 0),
                           rpole=(0.6, -0.6, 0.5), lpole=(-0.3, -0.7, 0.6))),
        K(0.62, 'in3', **S(ham=((2.0, 16.0, -9.5), (-0.15, 0.08, -0.99), (-1, 0, 0)), lh=1, body=(-6, 6, 0), torso=(0, 6, 0), head=(0, -4, 0),
                            right_leg=(-16, 0, 12), left_leg=(26, 0, -8), right_shin=(-14, 0, 0), left_shin=(-18, 0, 0), bpos=(0, -2.0, -0.5),
                            rpole=(0.6, -0.7, 0.3), lpole=(-0.6, -0.7, 0.3))),
        K(0.86, 'out', **S(ham=((-6.5, 18.0, -5.0), (-0.9, 0.15, -0.4), (-0.4, 0, 0.9)), lh=1, body=(-4, 42, 0), torso=(0, 16, 0), head=(0, -30, 0),
                            right_leg=(-10, 0, 12), left_leg=(20, 0, -8), right_shin=(-12, 0, 0), left_shin=(-12, 0, 0), bpos=(0, -1.6, 0),
                            rpole=(0.2, -0.8, 0.5), lpole=(-0.7, -0.6, 0.3))),
        K(1.4, 'io', **S(ham=gd, lh=1, **GUARD_LEGS)),
    ]
    return AN.bake(rig, 'swing', 1.4, k, loop=False, ground='feet', events={0.45: 'windup', 0.62: 'hit'})


def cast(rig):
    """Каст: молот на плече, левая рука поднимается и сжимается в кулак (призыв наковален/клинков; событие cast в 0.8 с)."""
    k = [
        K(0.0, **S(ham=carry(), **GUARD_LEGS)),
        K(0.5, 'io', **S(ham=carry(-0.5), larm=(60, 0, -40), lfore=(70, 0, 0), torso=(-4, 8, 0), head=(-6, 6, 0), **GUARD_LEGS)),
        K(0.8, 'back', **S(ham=carry(0.4), larm=(168, -10, -18), lfore=(6, 0, 0), torso=(8, -4, 0), head=(18, -4, 0), body=(4, 0, 0),
                            right_leg=(-8, 0, 7), left_leg=(14, 0, -6), right_shin=(-6, 0, 0), left_shin=(-14, 0, 0))),
        K(1.15, 'io', **S(ham=carry(0.2), larm=(160, -10, -18), lfore=(10, 0, 0), torso=(6, -4, 0), head=(14, -4, 0), body=(3, 0, 0), **GUARD_LEGS)),
        K(1.6, 'io', **S(ham=carry(), **GUARD_LEGS)),
    ]
    return AN.bake(rig, 'cast', 1.6, k, loop=False, ground='feet', events={0.8: 'cast'})


def forge(rig):
    """Особое «Горн» (4.0 с): три ритмичных удара по земле (1.0, 1.8, 2.6 — strike), на 3.3 — кулак к небу (ignite)."""
    gd = guard()
    d_imp = (0.0, -0.5, -0.86)
    hit = lambda y: (AN.ham_from_strike((1.0, y, -18.5), d_imp, (0, -1, 0)), d_imp, (0, -1, 0))
    up = ((2.0, 25.0, -3.0), (0.0, 0.85, -0.5), (0, 0.5, -0.86))
    low = dict(body=(-18, 0, 0), torso=(-6, 0, 0), head=(12, 0, 0), bpos=(0, -2.2, -0.6), right_leg=(-8, 0, 10), left_leg=(40, 0, -8),
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
        K(3.05, 'io', **S(ham=hit(1.5), lh=0.0, larm=(60, 0, -30), lfore=(60, 0, 0), **low)),
        K(3.3, 'back', **S(ham=hit(0.4), lh=0.0, larm=(172, -10, -12), lfore=(4, 0, 0), body=(-6, 0, 0), torso=(10, 0, 0), head=(22, 0, 0),
                            bpos=(0, -1.6, -0.3), right_leg=(-8, 0, 10), left_leg=(34, 0, -8), right_shin=(-16, 0, 0), left_shin=(-34, 0, 0))),
        K(4.0, 'io', **S(ham=hit(0.4), lh=0.0, larm=(166, -10, -12), lfore=(8, 0, 0), body=(-6, 0, 0), torso=(8, 0, 0), head=(18, 0, 0),
                          bpos=(0, -1.6, -0.3), right_leg=(-8, 0, 10), left_leg=(34, 0, -8), right_shin=(-16, 0, 0), left_shin=(-34, 0, 0))),
    ]
    return AN.bake(rig, 'forge', 4.0, k, loop='hold', ground='feet', events={1.0: 'strike', 1.8: 'strike', 2.6: 'strike', 3.3: 'ignite'})


def last_blow(rig):
    """Особое «Последний удар молота» (5.0 с): шаг в широкую стойку, медленный подъём молота над головой (заряд, дрожь),
    удар 4.0 (blow) — глубокий присед, молот в земле; 4.0–5.0 держит."""
    gd = guard()
    wide = dict(right_leg=(-14, 0, 16), left_leg=(18, 0, -16), right_shin=(-12, 0, 0), left_shin=(-18, 0, 0))
    over = ((1.0, 33.0, 2.5), (0.0, 0.25, 0.97), (0, 1, 0))
    d_imp = (0.0, -0.3, -0.95)
    imp = (AN.ham_from_strike((0.5, 0.0, -21.0), d_imp, (0, -1, 0)), d_imp, (0, -1, 0))
    k = [K(0.0, **S(ham=gd, lh=1, **GUARD_LEGS)),
         K(0.6, 'io', **S(ham=gd, lh=1, bpos=(0, -1.8, 0), body=(-4, 0, 0), **wide))]
    for i, t in enumerate((1.4, 2.2, 3.0)):
        f = (i + 1) / 3
        g = np.array(gd[0]) * (1 - f) + np.array(over[0]) * f
        dd = AN.nrm(np.array(gd[1]) * (1 - f) + np.array(over[1]) * f)
        k.append(K(t, 'io', **S(ham=(g, dd, (0, 1, 0)), lh=1, bpos=(0, -1.8 + 1.4 * f, 0), body=(-4 + 14 * f, 0, 0), torso=(10 * f, 0, 0),
                               head=(-4 + 30 * f, 0, 0), rpole=(0.8, 0.3, 0.4), lpole=(-0.8, 0.3, 0.4), **wide)))
    for i, t in enumerate(np.arange(3.1, 3.75, 0.1)):         # дрожь на пике заряда
        j = 0.35 * (1 if i % 2 else -1)
        k.append(K(float(t), 'linear', **S(ham=((over[0][0] + j, over[0][1], over[0][2] - abs(j)), over[1], over[2]), lh=1, bpos=(0, -0.4, 0),
                                           body=(10 + j, 0, 0), torso=(10, 0, 0), head=(26, 0, 0), rpole=(0.8, 0.3, 0.4), lpole=(-0.8, 0.3, 0.4), **wide)))
    k += [
        K(3.85, 'in', **S(ham=((1.0, 30.0, -9.0), (0, 0.6, -0.8), (0, 0.8, -0.6)), lh=1, bpos=(0, -1.5, -1.0), body=(-10, 0, 0), torso=(-4, 0, 0),
                           head=(10, 0, 0), right_leg=(-10, 0, 16), left_leg=(34, 0, -14), right_shin=(-16, 0, 0), left_shin=(-30, 0, 0))),
        K(4.0, 'in3', **S(ham=imp, lh=1, bpos=(0, -4.5, -1.5), body=(-30, 0, 0), torso=(-10, 0, 0), head=(24, 0, 0),
                           right_leg=(-2, 0, 18), left_leg=(62, 0, -14), right_shin=(-40, 0, 0), left_shin=(-70, 0, 0))),
        K(5.0, 'out', **S(ham=imp, lh=1, bpos=(0, -4.2, -1.5), body=(-26, 0, 0), torso=(-8, 0, 0), head=(20, 0, 0),
                           right_leg=(-2, 0, 18), left_leg=(60, 0, -14), right_shin=(-38, 0, 0), left_shin=(-66, 0, 0))),
    ]
    return AN.bake(rig, 'last_blow', 5.0, k, loop='hold', ground='feet', events={0.6: 'charge', 3.1: 'peak', 4.0: 'blow'})


def phase2(rig):
    """Переход в фазу 2 (2.0 с): полный оборот с молотом на вытянутых руках и удар головой молота в землю (1.0, roar)."""
    gd = guard()
    out_ = ((0.0, 17.0, -9.0), (0.0, 0.1, -1.0), (-1, 0, 0), 'body')
    k = [K(0.0, **S(ham=gd, lh=1, **GUARD_LEGS))]
    for i, t in enumerate((0.2, 0.4, 0.6, 0.8)):
        k.append(K(t, 'linear' if i else 'in', **S(ham=out_, lh=1, body=(-6, -90 * (i + 1) + 30, 0), bpos=(0, -1.2, 0), torso=(0, 0, 0),
                                                    head=(4, 0, 0), right_leg=(-10, 0, 10), left_leg=(10, 0, -10), right_shin=(-8, 0, 0),
                                                    left_shin=(-8, 0, 0))))
    d_imp = (0.0, -0.55, -0.83)
    imp = (AN.ham_from_strike((1.0, 0.0, -17.0), d_imp, (0, -1, 0)), d_imp, (0, -1, 0))
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
    hang = ((9.0, 13.0, -2.5), (0.25, -0.95, -0.2), (1, 0, 0))
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
    imp = (AN.ham_from_strike((0.8, 0.0, -19.5), d_imp, (0, -1, 0)), d_imp, (0, -1, 0))
    under['hg'] = {'rot': (0, 0, 0), 'pos': (0, -40, 0)}
    under['ham'] = (p[0] + np.array([0, -40.0, 0]), p[1], p[2])
    kn2 = dict(kn, hg={'rot': (0, 0, 0), 'pos': (0, 0, 0)})
    under = S(**under)
    under.update(vis=(1, 0), head=(-30, 0, 0), torso=(-10, 0, 0))
    k = [
        K(0.0, **under), K(2.0, 'linear', **under),
        K(4.5, 'out', **S(**dict(kn2, head=(-24, 0, 0), torso=(-10, 0, 0)))),
        K(5.2, 'io', **S(**dict(kn2, head=(0, 0, 0), torso=(-4, 0, 0)))),
        K(6.0, 'io', **S(ham=(p[0] + np.array([0, 2.0, 0]), p[1], p[2]), rslide=8.5, rpole=(0.6, -0.4, 0.7), head=(6, 0, 0), **GUARD_LEGS)),
        K(6.7, 'io', **S(ham=((2.0, 29.0, 3.0), (0.05, 0.42, 0.9), (0, 1, 0)), lh=1, body=(12, 0, 0), torso=(10, 0, 0), head=(16, 0, 0),
                          right_leg=(-14, 0, 8), left_leg=(22, 0, -6), right_shin=(-4, 0, 0), left_shin=(-10, 0, 0), rpole=(0.8, 0.2, 0.4),
                          lpole=(-0.8, 0.2, 0.4))),
        K(7.0, 'in3', **S(ham=imp, lh=1, body=(-26, 0, 0), torso=(-8, 0, 0), head=(18, 0, 0), bpos=(0, -3.0, -1.0), right_leg=(-6, 0, 10),
                           left_leg=(52, 0, -8), right_shin=(-26, 0, 0), left_shin=(-52, 0, 0))),
        K(7.6, 'out', **S(ham=imp, lh=1, body=(-20, 0, 0), torso=(-4, 0, 0), head=(24, 0, 0), bpos=(0, -2.6, -1.0), right_leg=(-6, 0, 10),
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
    stag = ((6.0, 12.5, -6.0), (0.4, -0.6, -0.7), (0.6, -0.6, 0.5))
    fall = fallen()
    kneel_body = dict(KNEEL)
    bow = dict(head=(-34, 0, 0), torso=(-14, 0, 0))
    lknee = dict(larm=(40, 0, -8), lfore=(50, 0, 0))            # левая рука на колене
    k = [
        K(0.0, **S(ham=gd, lh=1, **GUARD_LEGS)),
        K(0.4, 'out', **S(ham=stag, lh=0.0, larm=(-20, 0, -30), lfore=(30, 0, 0), body=(10, 0, 0), torso=(8, 0, 0), head=(14, 0, 0),
                           bpos=(0, -0.5, 1.2), right_leg=(-20, 0, 8), left_leg=(6, 0, -8), right_shin=(-20, 0, 0), left_shin=(-6, 0, 0))),
        K(1.2, 'io', **S(vis=(1, 0), lh=0.0, head=(-20, 0, 0), torso=(-10, 0, 0), **lknee, **kn)),
        K(1.25, 'linear', **S(vis=(0, 1), lh=0.0, head=(-20, 0, 0), torso=(-10, 0, 0), **lknee, **kn)),
        K(2.0, 'io', **S(vis=(0, 1), lh=0.0, **bow, **lknee, **kn)),
        K(2.6, 'io', **S(vis=(0, 1), lh=0.0, head=(-40, 0, 0), torso=(-18, 0, 0), **lknee, **kn)),
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
        k.append(K(t, 'io', **S(ham=planted(), rslide=6.5, vis=(0, 1), rpole=(0.5, -0.6, 0.6), larm=(-6, 0, -34), lfore=(80, 0, 0),
                                 body=(0, 0, 3), bpos=(0, -0.2 + 0.2 * math.cos(ph), 0), right_leg=(0, 0, 4), left_leg=(6, 0, -8), left_shin=(-10, 0, 0),
                                 torso=(1.5 * math.sin(ph), 0, -2), head=(-4 + 3 * math.sin(ph * 2), 22 * math.sin(ph), 4))))
    return AN.bake(rig, 'npc_stand', 4.0, k, loop=True, ground='feet', wind=0.3)


def npc_sit(rig):
    """Мирный NPC: сидит на голове лежащего молота (молот на земле под ней), локоть на колене, голова чуть набок."""
    # куда положить hammer_ground, чтобы центр головы оказался под ней (0, 3.4, 1.0); рукоять уходит вправо-вперёд
    R = AN.euler((95, 60, 0))
    head_rest = np.array(G.hg_local((0, G.HAM_HEAD, 0)))
    want = np.array([0.0, 3.4, 1.0])
    pos = want - (np.array(G.HG_PIVOT) + R @ head_rest)
    hg = {'rot': (95, 60, 0), 'pos': tuple(pos)}
    k = []
    for t in (0, 1, 2, 3, 4):
        ph = 2 * math.pi * t / 4
        k.append(K(t, 'io', **S(vis=(0, 1), hg=hg, rh=0.0, bpos=(0, -4.6 + 0.12 * math.cos(ph), 1.0), body=(-12, 0, 0),
                                 right_leg=(78, 0, 14), right_shin=(-96, 0, 0), left_leg=(84, 0, -10), left_shin=(-104, 0, 0),
                                 rarm=(62, 0, 6), rfore=(92, 0, 0), larm=(40, 0, -10), lfore=(36, 0, 0),
                                 torso=(-6 + 1.5 * math.sin(ph), 0, 0), head=(-6 + 2 * math.sin(ph), -10 + 8 * math.sin(ph / 2), 8))))
    return AN.bake(rig, 'npc_sit', 4.0, k, loop=True, ground=None, wind=0.25)


ALL = (idle, walk, slam, swing, cast, forge, last_blow, phase2, phase3, spawn, surrender, npc_stand, npc_sit)


def all_anims(rig):
    out = []
    for f in ALL:
        out.append(f(rig))
    return out
