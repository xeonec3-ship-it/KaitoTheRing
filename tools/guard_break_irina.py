#!/usr/bin/env python3
"""
T32 п. 4 «Сломать блок» — Ирина (irina_guard_break): нити из левой ладони обвивают защиту и рывком раздёргивают её, затем удар
посохом сверху (крюком). Позы — целями в мире, углы — решателями tools/guard_break_lib.py. Вызывается из tools/gen_irina.main.
Это анимация контроллера «тело» (как все irina_*): ткань — свой контроллер (irina_cloth_*), его не трогаем.

Тайминг: warn 0.10 (тик 2; вспышка на левой ладони — нити), hit 0.70 (тик 14) — крюк посоха в блок; длина 1.8 с (36 тиков).
  0.10–0.32 левая рука выбрасывает ладонь к цели (нити летят и обвивают защиту), посох уходит вверх за правое плечо;
  0.32–0.50 рывок: левая рука резко на себя к бедру, плечи раскрываются вправо (рвёт защиту), вес назад;
  0.50–0.60 взвод посоха (медленное дотягивание за плечом); 0.60–0.76 удар: шаг левой, корпус вперёд и влево, крюк по дуге
  сверху справа в блок (пик ~0.69); перехлёст вниз-влево; 0.9–1.8 возврат в хват покоя с отшагом.
"""
import numpy as np

import guard_break_lib as GL
from guard_break_lib import Keys, yaw_dir

WARN, HIT, LENGTH = 0.10, 0.70, 1.8
HEAD_PT = np.array([0.0, 1.5, -28.0])          # крюк (навершие) посоха — в осях кисти

S0 = dict(body=(0.0, 0.0, 0.0), torso=(0.0, 0.0, 0.0), pel=(0.0, 0.0), drop=0.0, rf=(2.2, 0.6, 6.0, 0.0), lf=(-2.2, -0.6, -6.0, 0.0),
          lh=(-3.4, 13.6, -8.7))


def special(M):
    return {'strike': (np.zeros(3), HEAD_PT)}


def stance():
    """Стойка Ирины (gen_irina.STANCE_I, эталон Epic Fight 21.11) — JSON-поза: удары начинаются и кончаются в ней."""
    import gen_irina as GI
    pose = {}
    for b, ch in GI.STANCE_I.items():
        pose[b] = {('rotation' if c == 'rot' else 'position'): list(v) for c, v in ch.items()}
    return pose


def build():
    M = GL.JModel('irina', anims={})
    sv = GL.Solver(M)
    pose0 = stance()
    st, W0 = GL.stance_targets(M, pose0)
    h0 = st['hand_r']
    d0 = GL.nrm(GL.ap(W0['bipedHandRight'], HEAD_PT) - h0)
    y0, p0 = float(np.degrees(np.arctan2(d0[0], -d0[2]))), float(np.degrees(np.arcsin(d0[1])))
    S0 = dict(body=tuple(pose0['body']['rotation']), torso=(0.0, 0.0, 0.0), pel=(0.0, 0.0), drop=0.0, rf=st['rf'], lf=st['lf'],
              lh=tuple(float(x) for x in st['hand_l']))
    K = Keys([
        (0.0, dict(S0)),
        (0.10, dict(body=(2.0, 30.0, 0.0)), 'io'),
        (0.30, dict(body=(6.0, 18.0, 2.0), torso=(2.0, 6.0, 0.0), pel=(0.3, -0.8), lh=(-1.5, 23.0, -16.0), lf=(-2.4, -2.2, -10.0, 0.0)), 'out'),
        (0.40, dict(lh=(-2.0, 22.5, -15.0)), 'io'),
        (0.50, dict(body=(-3.0, 58.0, -3.0), torso=(-3.0, 10.0, 0.0), pel=(0.6, 1.6), drop=0.8, lh=(-9.5, 14.5, 4.0),
                    rf=(2.4, 1.6, 20.0, 0.0), lf=(-2.6, -1.8, -14.0, 1.2)), 'in'),
        (0.58, dict(body=(-4.0, 62.0, -4.0), torso=(-4.0, 11.0, 0.0), pel=(0.7, 1.9), drop=0.9, lh=(-9.8, 14.0, 4.6)), 'lin'),
        (0.635, dict(body=(6.0, 26.0, 0.0), torso=(0.0, 2.0, 0.0), pel=(0.2, -2.6)), 'in'),
        (0.695, dict(body=(20.0, -24.0, 4.0), torso=(6.0, -8.0, 0.0), pel=(-0.4, -5.6), drop=1.8, lh=(-8.5, 15.0, 1.0),
                    rf=(2.6, 1.0, 8.0, 0.0), lf=(-2.8, -9.0, -18.0, 0.0)), 'in'),
        (0.78, dict(body=(24.0, -36.0, 5.0), torso=(8.0, -10.0, 0.0), pel=(-0.5, -6.4), drop=2.0), 'out2'),
        (0.95, dict(body=(18.0, -28.0, 3.0), torso=(5.0, -6.0, 0.0), pel=(-0.4, -5.8), drop=1.7, rf=(2.6, 1.0, 8.0, 0.0),
                    lf=(-2.8, -9.0, -18.0, 0.0)), 'io'),
        (1.20, dict(body=(8.0, -6.0, 1.0), torso=(2.0, -2.0, 0.0), pel=(-0.2, -3.0), drop=1.0, lf=(-2.6, -5.0, -10.0, 1.4),
                    lh=(-5.0, 14.0, -5.0)), 'io'),
        (1.42, dict(lf=(-2.2, -0.6, -6.0, 0.0), pel=(0.0, -0.8), drop=0.3), 'io'),
        (1.80, dict(S0), 'io'),
    ])
    ST = GL.stime([(0, 0.0), (0.10, 0.0, 'lin'), (0.50, 0.22, 'out'), (0.585, 0.255, 'lin'), (0.715, 0.80, ('beta', 2.2, 2.0)),
                   (0.88, 0.86, 'out'), (1.05, 0.90, 'io'), (1.80, 1.0, 'io')])
    # правая рука — одна кость (локтя нет): путь задаётся направлением руки от плеча (ayaw — вправо +, apit — вверх +) и
    # направлением посоха «кисть → крюк» (byaw, bpit)
    sh0 = GL.ap(W0['right_arm'], (0, 0, 0))
    a0 = GL.nrm(h0 - sh0)
    ARM = float(np.linalg.norm(h0 - sh0))
    HOLD = dict(ayaw=float(np.degrees(np.arctan2(a0[0], -a0[2]))), apit=float(np.degrees(np.arcsin(a0[1]))), byaw=y0, bpit=p0)
    P = [(0.0, dict(HOLD)),
         (0.12, dict(ayaw=40.0, apit=10.0, byaw=-10.0, bpit=88.0)),
         (0.22, dict(ayaw=62.0, apit=42.0, byaw=-30.0, bpit=144.0)),        # посох за правым плечом: рука вверх-вправо, крюк назад
         (0.255, dict(ayaw=64.0, apit=46.0, byaw=-31.0, bpit=149.0)),
         (0.45, dict(ayaw=26.0, apit=48.0, byaw=-14.0, bpit=88.0)),
         (0.80, dict(ayaw=-4.0, apit=-14.0, byaw=-3.0, bpit=-4.0)),          # крюк в блок (грудь цели)
         (0.86, dict(ayaw=-22.0, apit=-16.0, byaw=-24.0, bpit=-12.0)),
         (0.90, dict(ayaw=-16.0, apit=-18.0, byaw=-18.0, bpit=0.0)),
         (1.0, dict(HOLD))]

    def pose(t):
        pel = K.v(t, 'pel')
        o = {'body': {'rotation': K.v(t, 'body'), 'position': [pel[0], 0.0, pel[1]]}, 'torso': {'rotation': K.v(t, 'torso')}}
        sv.legs(o, {'right_leg': tuple(K.v(t, 'rf')), 'left_leg': tuple(K.v(t, 'lf'))}, drop=K.f(t, 'drop'))
        b = K.v(t, 'body')
        bl = K.v(max(0.0, t - 0.06), 'body')
        o['head'] = {'rotation': [-0.7 * b[0] - 3.0, -0.8 * bl[1], 4.0 - 0.5 * b[2]]}
        o['hat'] = {'rotation': [0.0, 0.0, 0.0]}
        w = GL.path_at(P, ST(t))
        sh = GL.ap(M.chain(o, 'right_arm'), (0, 0, 0))
        sv.arm(o, 'right', sh + yaw_dir(w['ayaw'], w['apit']) * ARM)
        sv.wrist(o, yaw_dir(w['byaw'], w['bpit']), far=HEAD_PT)
        sv.arm(o, 'left', np.array(K.v(t, 'lh')))
        return o

    sv.reset()
    for _ in range(2):
        pose(0.0)
    return GL.bake(GL.blend_edges(pose, pose0, LENGTH), LENGTH, 0.02, events={WARN: 'warn', HIT: 'hit'})
