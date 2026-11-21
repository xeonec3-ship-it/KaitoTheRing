#!/usr/bin/env python3
"""
T32 п. 4 «Сломать блок» — «Эреб, Длань Лжи» (ereb_hand_guard_break): призрачная рука хватает защиту и отводит её в сторону,
в открытое место — укол стеклянной рапирой. Позы — целями в мире, углы — решателями tools/guard_break_lib.py; призрачная рука —
точка ладони в мире (её position подбирается по FK), пальцы — gen_ereb_hand_anims.hand(). Вызывается из gen_ereb_hand_anims.build().

Тайминг: warn 0.10 (тик 2; вспышка на призрачной ладони), hit 0.70 (тик 14) — укол; длина 1.8 с (36 тиков).
  0.10–0.40 призрачная рука летит к защите цели (раскрыта), Эреб уходит в стойку, рапира к бедру остриём вперёд;
  0.40–0.52 хватает (кулак) и рывком отводит защиту вправо-вниз — грудь цели открыта; корпус скручивается влево, вес назад;
  0.52–0.60 взвод; 0.60–0.74 выпад правой ногой, укол в грудь (пик ~0.69); держит руку до 0.88;
  0.88–1.8 рука отпускает и возвращается за плечо, отшаг, стойка покоя.
"""
import numpy as np

import guard_break_lib as GL
from guard_break_lib import Keys, yaw_dir

WARN, HIT, LENGTH = 0.10, 0.70, 1.8
PALM_PT = np.array([0.0, 5.0, 0.0])            # середина ладони — в осях кости ghost_palm (от её шарнира)

G0 = dict(body=(4.0, -38.0, 0.0), torso=(0.0, 4.0, 0.0), pel=(0.0, 0.0), drop=1.2,
          rf=(1.7, -5.7, -10.0, 0.0), lf=(-1.2, 5.9, -22.0, 0.0), larm=(-10.0, -6.0, -8.0), cape=4.0)


def special(M):
    return {'strike': (np.zeros(3), M.axis_far)}


def build():
    import gen_ereb_hand_anims as HA
    M = GL.JModel('ereb_hand', anims={})
    sv = GL.Solver(M)
    K = Keys([
        (0.0, dict(G0, gp=(15.7, 36.6, 4.0), grot=(24.0, -10.0, -4.0), curl=0.3, spread=0.0, thumb=0.2)),
        (0.10, dict(body=(4.0, -40.0, 0.0)), 'io'),
        (0.36, dict(body=(6.0, -46.0, -1.0), torso=(0.0, -2.0, 0.0), pel=(0.3, 0.8), drop=1.8, gp=(2.0, 23.0, -32.0), grot=(10.0, -4.0, 4.0),
                    curl=0.0, spread=1.0, thumb=0.0, cape=8.0), 'out'),
        (0.44, dict(gp=(2.0, 22.0, -33.5), curl=0.85, spread=0.0, thumb=0.8), 'in'),
        (0.54, dict(body=(2.0, -74.0, -3.0), torso=(-3.0, -7.0, 0.0), pel=(0.5, 1.6), drop=2.3, gp=(11.0, 16.0, -33.0), grot=(6.0, -2.0, 30.0),
                    curl=0.9, thumb=0.9, cape=10.0), 'in'),
        (0.60, dict(body=(1.0, -78.0, -3.0), pel=(0.5, 1.7), drop=2.4, gp=(11.5, 15.5, -33.0), rf=(1.8, -6.6, -8.0, 0.9)), 'lin'),
        (0.66, dict(body=(10.0, -52.0, 0.0), torso=(2.0, 0.0, 0.0), pel=(0.2, -3.0), drop=2.6), 'in'),
        (0.71, dict(body=(18.0, -18.0, 3.0), torso=(6.0, 8.0, 0.0), pel=(0.0, -6.0), drop=3.0, rf=(2.2, -14.0, -4.0, 0.0),
                    lf=(-1.6, 5.0, -30.0, 0.0), larm=(30.0, -8.0, -30.0), cape=13.0), 'in'),
        (0.78, dict(body=(20.0, -14.0, 3.0), torso=(7.0, 10.0, 0.0), pel=(0.0, -6.4), drop=3.2, cape=15.0), 'out2'),
        (0.82, dict(body=(18.0, -18.0, 2.0), torso=(5.0, 7.0, 0.0), pel=(0.0, -6.0), drop=3.0, rf=(2.2, -14.0, -4.0, 0.0),
                    lf=(-1.6, 5.0, -30.0, 0.0), larm=(26.0, -8.0, -30.0), gp=(11.5, 15.5, -33.0), curl=0.9, spread=0.0, thumb=0.9,
                    cape=13.0), 'io'),
        (0.98, dict(curl=0.0, spread=1.0, thumb=0.0), 'out'),
        (1.12, dict(body=(10.0, -34.0, 1.0), torso=(2.0, 4.0, 0.0), pel=(0.0, -3.0), drop=2.0, rf=(2.0, -10.0, -8.0, 1.6), cape=12.0), 'io'),
        (1.32, dict(rf=(1.7, -5.7, -10.0, 0.0), pel=(0.0, -0.6), drop=1.5, larm=(-6.0, -6.0, -8.0)), 'io'),
        (1.40, dict(gp=(12.0, 31.0, -6.0), grot=(20.0, -10.0, -4.0), curl=0.3, spread=0.2, thumb=0.2), 'io'),
        (1.80, dict(G0, gp=(15.7, 36.6, 4.0), grot=(24.0, -10.0, -4.0), curl=0.3, spread=0.0, thumb=0.2), 'io'),
    ])
    ST = GL.stime([(0, 0.0), (0.10, 0.0, 'lin'), (0.40, 0.30, 'out'), (0.62, 0.36, 'io'),
                   (0.735, 0.80, ('beta', 2.1, 2.0)), (0.82, 0.82, 'out'), (1.80, 1.0, 'io')])
    P = [(0.0, dict(hx=4.4, hy=17.8, hz=-12.2, byaw=-5.0, bpit=6.0)),
         (0.30, dict(hx=7.0, hy=14.6, hz=-1.0, byaw=4.0, bpit=-2.0)),          # рапира у бедра, остриём на цель
         (0.36, dict(hx=7.2, hy=14.4, hz=0.0, byaw=4.0, bpit=-1.0)),
         (0.80, dict(hx=3.0, hy=15.0, hz=-21.0, byaw=-2.0, bpit=3.0)),         # укол в грудь (защита отведена рукой)
         (0.82, dict(hx=3.0, hy=15.2, hz=-20.6, byaw=-2.0, bpit=3.5)),
         (1.0, dict(hx=4.4, hy=17.8, hz=-12.2, byaw=-5.0, bpit=6.0))]
    gprev = {'p': np.array([1.0, -1.0, -2.0])}

    def pose(t):
        pel = K.v(t, 'pel')
        o = {'body': {'rotation': K.v(t, 'body'), 'position': [pel[0], 0.0, pel[1]]}, 'torso': {'rotation': K.v(t, 'torso')}}
        sv.legs(o, {'right_leg': tuple(K.v(t, 'rf')), 'left_leg': tuple(K.v(t, 'lf'))}, drop=K.f(t, 'drop'))
        b = K.v(t, 'body')
        bl = K.v(max(0.0, t - 0.06), 'body')
        o['head'] = {'rotation': [-0.75 * b[0] + 2.0, -0.92 * bl[1], 0.0]}
        o['mask'] = {'rotation': [0.0, 0.0, 0.0]}
        o['left_arm'] = {'rotation': K.v(t, 'larm')}
        o['bipedHandLeft'] = {'rotation': [0.0, 0.0, 0.0]}
        c = K.f(t, 'cape')
        o['cape'], o['cape_mid'], o['cape_low'] = ({'rotation': [c * 0.6, 0.0, 0.0]}, {'rotation': [c * 0.38, 0.0, 0.0]},
                                                   {'rotation': [-c * 0.12 if c > 15 else c * 0.15, 0.0, 0.0]})
        w = GL.path_at(P, ST(t))
        sv.arm(o, 'right', np.array([w['hx'], w['hy'], w['hz']]))
        sv.wrist(o, yaw_dir(w['byaw'], w['bpit']))
        # призрачная рука: пальцы и поворот — ключами, position — чтобы середина ладони легла в точку gp (мир)
        gh = HA.hand(rot=tuple(K.v(t, 'grot')), curl=K.f(t, 'curl'), spread=K.f(t, 'spread'), thumb=K.f(t, 'thumb'))
        for k, v in gh.items():
            if k.endswith('_scale'):
                o.setdefault(k[:-6], {})['scale'] = list(v)
            elif k.endswith('_pos'):
                continue
            else:
                o.setdefault(k, {})['rotation'] = list(v)
        tgt = np.array(K.v(t, 'gp'))

        def f(v):
            o['ghost_hand']['position'] = [v[0], v[1], v[2]]
            e = GL.ap(M.chain(o, 'ghost_palm'), PALM_PT) - tgt
            return float(e @ e)
        v, _ = GL.descend(f, gprev['p'], 2.0)
        gprev['p'] = v
        o['ghost_hand']['position'] = [float(x) for x in v]
        o['ghost_trail'] = {'scale': [1.0, 1.0, 1.0]}
        return o

    sv.reset()
    for _ in range(2):
        pose(0.0)
    # края — сшивка со стойкой ereb_hand_guard (её ключи кисти — уже под двойной поворот GeckoLib): вход и выход без скачка крена клинка
    p0 = GL.pose_at('ereb_hand', 'ereb_hand_guard', 0.0, ('body', 'torso', 'head', 'right_arm', 'left_arm', 'right_leg', 'left_leg', 'bipedHandRight', 'bipedHandLeft'))
    return GL.bake(GL.blend_edges(pose, p0, LENGTH), LENGTH, 0.02, events={WARN: 'warn', HIT: 'hit'})
