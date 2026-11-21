#!/usr/bin/env python3
"""
T29 Мартин — пилот анимаций по эталону Epic Fight (владелец 21.11; правила — docs/specs/anim_style_epicfight.md).
Переделаны: martin_idle, martin_swing, martin_overhead, martin_thrust, martin_shield_bash. Остальные — tools/gen_martin.py без изменений.
Вызывается из gen_martin.anims(); пишет ключи через те же A() / Grip / ShieldFront / cape_follow / vis.

Устройство (как у эталона):
  * тело — ключевые позы (anim_body.Keys): таз (смещение, просадка), плечи (body: поворот/наклон/крен), грудь (torso, малое
    запаздывание), стопы — точками на земле (anim_body.Rig.plant: шаг в удар, поворот стоп на опорной ноге), голова смотрит на
    цель с запаздыванием 70 мс, плащ отстаёт от таза на ~100 мс;
  * оружие — путь по параметру s (кисть — цилиндр вокруг таза, клинок — азимут/угол в вертикальной плоскости), а время s(t) задаёт
    профиль скорости: замах — замедление в позу (out), «взвод» — медленное дотягивание, удар — разгон-торможение с пиком у
    события hit, затем перехлёст, удержание тяжёлого меча и долгий возврат с шагами.
Все углы — во внутренних осях (anim_body: Y > 0 — влево, body X > 0 — наклон назад, нога X > 0 — вперёд); o['_int'] = True.
Тики событий (MartinMath) НЕ изменены; длины анимаций выросли (возврат) — см. docs/inbox/2026-11-21_mgr_anim_epicfight.md.
"""
import math

import numpy as np

import anim_body as B
from anim_body import Keys, cyl, sag_dir

TAU = 2 * math.pi
# стойка (мир): плечи развёрнуты вправо (у эталона 32–75°), левая нога впереди, задняя стопа развёрнута наружу
STANCE = dict(yaw=-32.0, pitch=-4.0, roll=0.0, tyaw=0.0, tpitch=0.0, pel=(0.3, 0.0), drop=0.35,
              rf=(3.4, 2.5, -38.0, 0.0), lf=(-2.6, -2.7, -8.0, 0.0))
# хват в стойке (мир): кисть перед правым бедром, клинок вверх-вперёд на противника
GUARD_W = dict(hphi=-14.0, hr=7.2, hy=14.8, byaw=12.0, bth=46.0)
REACH = 11.2                     # плечо → кисть (ед. модели), с запасом


def beta_cdf(k, a, b, n=200):
    """Профиль удара: скорость ∝ k^(a−1)(1−k)^(b−1) — пик на (a−1)/(a+b−2)."""
    k = min(1.0, max(0.0, k))
    xs = np.linspace(0, 1, n + 1)
    v = xs ** (a - 1) * (1 - xs) ** (b - 1)
    c = np.concatenate([[0], np.cumsum((v[1:] + v[:-1]) / 2)])
    c /= c[-1]
    return float(np.interp(k, xs, c))


class STime:
    """s(t): кусочно, каждый участок — своя кривая ('out', 'io', 'lin', ('beta', a, b), 'back')."""

    def __init__(self, segs):
        self.segs = segs          # [(t0, s0), (t1, s1, кривая), ...]

    def __call__(self, t):
        pts = self.segs
        if t <= pts[0][0]:
            return pts[0][1]
        for (t0, s0, *_), (t1, s1, e) in zip(pts, pts[1:]):
            if t <= t1:
                k = (t - t0) / max(1e-6, t1 - t0)
                if isinstance(e, tuple):
                    k = beta_cdf(k, e[1], e[2])
                else:
                    k = B.ease(k, e)
                return s0 + (s1 - s0) * k
        return pts[-1][1]


def path_at(path, s):
    """path: [(s, {hphi, hr, hy, byaw, bth, lw}), ...] — линейно по s (равномерная угловая скорость внутри участка)."""
    if s <= path[0][0]:
        return dict(path[0][1])
    for (s0, a), (s1, b) in zip(path, path[1:]):
        if s <= s1:
            k = (s - s0) / max(1e-9, s1 - s0)
            return {n: a[n] * (1 - k) + b[n] * k for n in a}
    return dict(path[-1][1])


class Body:
    def __init__(self, m, G, g, sf=None):
        self.m, self.G, self.g, self.sf = m, G, g, sf
        self.rig = B.Rig(m, G.fk)

    # ---------------------------------------------------------------- тело
    def body(self, K, t, look=0.0, head_lag=0.07, cape_lag=0.1, wind=0.0, sway=1.0, period=3.0):
        f = lambda n, d=0.0: K(t, n, STANCE.get(n, d)) if not isinstance(STANCE.get(n, d), tuple) else K(t, n, STANCE[n])
        yaw, pitch, roll = float(f('yaw')), float(f('pitch')), float(f('roll'))
        pel = np.asarray(K(t, 'pel', STANCE['pel']), float)
        o = {'_int': True,
             'body': {'rot': [pitch, yaw, roll], 'pos': [float(pel[0]), 0.0, float(pel[1])]},
             'torso': {'rot': [float(f('tpitch')), float(f('tyaw')), 0.0]}}
        feet = {'right_leg': tuple(K(t, 'rf', STANCE['rf'])), 'left_leg': tuple(K(t, 'lf', STANCE['lf']))}
        self.rig.plant(o, feet, drop=float(f('drop')))
        # голова: смотрит на цель (мир: yaw look), догоняет поворот плеч с запаздыванием
        yl = float(K(max(0.0, t - head_lag), 'yaw', STANCE['yaw']))
        pl = float(K(max(0.0, t - head_lag), 'pitch', STANCE['pitch']))
        hy = max(-45.0, min(45.0, 0.5 * (look - yl)))
        hp = float(K(t, 'hpitch', 0.0)) - 0.6 * pl
        o['head'] = {'rot': [hp, hy, -0.3 * float(K(max(0.0, t - head_lag), 'roll', 0.0))]}
        # плащ: отлёт назад от скорости таза вперёд (с запаздыванием), вбок — от поворота плеч
        dt = 0.04
        tc = max(0.0, t - cape_lag)
        vz = -(float(K(tc + dt, 'pel', STANCE['pel'])[1]) - float(K(max(0.0, tc - dt), 'pel', STANCE['pel'])[1])) / (2 * dt)
        vy = (float(K(tc + dt, 'yaw', STANCE['yaw'])) - float(K(max(0.0, tc - dt), 'yaw', STANCE['yaw']))) / (2 * dt)
        # (на плаще висит щит — тяжёлый: отлёт ограничен, иначе на рывках плащ со щитом взлетает горизонтально)
        self.G.cape_follow(t, o, lag=float(np.clip(0.2 * vz, -4, 10)), wind=wind + min(4.0, abs(vy) / 120.0), sway=sway, period=period,
                           side=float(np.clip(-vy / 90.0, -4, 4)))
        return o

    # ---------------------------------------------------------------- оружие
    def weapon(self, o, w, left=1.0):
        """w: {hphi, hr, hy, byaw, bth} — мир, вокруг таза. Кисть подтягивается к плечу, если дальше вытянутой руки."""
        G, m = self.G, self.m
        pel = o['body']['pos']
        hw = cyl(w['hphi'], w['hr'], w['hy']) + np.array([pel[0], 0.0, pel[2]])
        sh = G.world_pt(m, o, 'right_arm', m.bones['right_arm'].pivot)
        d = hw - sh
        if np.linalg.norm(d) > REACH:
            hw = sh + d / np.linalg.norm(d) * REACH
        dw = sag_dir(w['byaw'], w['bth'])
        Mt, ot = G.fk(m, o, 'torso')
        self.g(o, Mt.T @ (hw - ot), Mt.T @ dw, left=left)
        return o


# ================================================================== анимации
def define(A, m, G, g, sf):
    bd = Body(m, G, g, sf)
    vis = G.vis

    # ---------------------------------------------------------------- idle: стойка вполоборота, дыхание 3 с, вес чуть гуляет
    def idle(t):
        br = math.sin(TAU * t / 3.0)
        sw = math.sin(TAU * t / 3.0 + 1.1)
        K = Keys([(0, dict(drop=STANCE['drop'] - 0.12 * br, tpitch=0.7 * br, pitch=-4.0 - 0.5 * br, pel=(0.3 + 0.25 * sw, 0.05 * br),
                           yaw=-32.0 + 1.2 * sw, hpitch=-1.0 + 0.6 * br))])
        o = bd.body(K, t)
        w = dict(GUARD_W)
        w['hy'] += 0.2 * br
        w['bth'] += 1.0 * br
        bd.weapon(o, w)
        return vis(o)
    A('idle', 3.0, True).sample(idle, 0.1)

    # ---------------------------------------------------------------- swing: горизонтальный справа налево (hit 0.75; звук/шлейф 0.6)
    # замах 0–0.46 (плечи −105°, вес на заднюю ногу, таз назад), взвод 0.46–0.60, удар 0.60–0.90 (пик ~0.72, левая нога шагает
    # вперёд и разворачивается, таз −0.45 L вперёд и вниз, бёдра ведут плечи), перехлёст до 0.90, тяжёлый меч провисает до 1.25,
    # возврат 1.25–1.9 с шагом назад.
    SW_T = STime([(0, 0), (0.46, 0.20, 'out'), (0.60, 0.23, 'lin'), (0.90, 0.85, ('beta', 2.0, 2.4)), (1.05, 0.90, 'out'),
                  (1.30, 0.93, 'io'), (2.00, 1.0, 'io')])
    SW_P = [(0.0, dict(GUARD_W)),
            (0.20, dict(hphi=-118.0, hr=8.0, hy=21.5, byaw=-172.0, bth=22.0)),
            (0.23, dict(hphi=-124.0, hr=8.2, hy=22.0, byaw=-182.0, bth=25.0)),
            (0.45, dict(hphi=-70.0, hr=9.8, hy=19.0, byaw=-95.0, bth=8.0)),
            (0.62, dict(hphi=0.0, hr=10.2, hy=16.5, byaw=0.0, bth=-4.0)),
            (0.78, dict(hphi=70.0, hr=9.8, hy=15.8, byaw=92.0, bth=-10.0)),
            (0.85, dict(hphi=88.0, hr=9.4, hy=15.4, byaw=120.0, bth=-14.0)),
            (0.90, dict(hphi=82.0, hr=9.0, hy=14.6, byaw=112.0, bth=-30.0)),
            (0.93, dict(hphi=72.0, hr=8.6, hy=14.8, byaw=100.0, bth=-24.0)),
            (1.0, dict(GUARD_W))]
    SW_K = Keys([
        (0.0, dict(yaw=-32.0, pitch=-4.0, roll=0.0, tyaw=0.0, tpitch=0.0, pel=(0.3, 0.0), drop=0.35,
                   rf=(3.4, 2.5, -38.0, 0.0), lf=(-2.6, -2.7, -8.0, 0.0))),
        (0.46, dict(yaw=-105.0, pitch=5.0, roll=-6.0, tyaw=6.0, pel=(0.7, 1.5), drop=0.6, rf=(3.4, 2.5, -55.0, 0.0),
                    lf=(-2.4, -1.8, -20.0, 0.0)), 'out'),
        (0.60, dict(yaw=-112.0, pitch=6.0, roll=-7.0, tyaw=7.0, pel=(0.7, 1.7), drop=0.7, lf=(-2.5, -2.4, -18.0, 1.0)), 'lin'),
        (0.66, dict(yaw=-62.0, tyaw=-6.0, rf=(3.4, 2.5, -20.0, 0.0)), 'in'),
        (0.72, dict(yaw=12.0, pitch=-14.0, roll=4.0, tyaw=-10.0, pel=(-0.4, -3.6), drop=1.4, rf=(3.4, 2.5, 15.0, 0.0),
                    lf=(-3.6, -8.6, 22.0, 0.0)), 'in'),
        (0.80, dict(yaw=72.0, pitch=-18.0, roll=8.0, tyaw=-8.0, pel=(-0.8, -5.6), drop=1.6, rf=(2.8, 0.2, 40.0, 0.0)), 'out2'),
        (0.88, dict(yaw=98.0, tyaw=4.0, pel=(-0.8, -6.1), rf=(2.0, -1.6, 55.0, 0.0)), 'out'),
        (1.05, dict(yaw=86.0, pitch=-15.0, roll=6.0, tyaw=0.0, drop=1.3), 'io'),
        (1.30, dict(yaw=80.0, pitch=-12.0, pel=(-0.6, -5.2), drop=1.2, lf=(-3.6, -8.6, 22.0, 0.0), rf=(2.0, -1.6, 50.0, 0.0)), 'io'),
        (1.48, dict(lf=(-3.1, -5.6, 8.0, 1.1), rf=(2.6, 0.6, 0.0, 1.0)), 'io'),
        (1.65, dict(yaw=-10.0, lf=(-2.6, -2.7, -8.0, 0.0), rf=(3.4, 2.5, -30.0, 0.0), pel=(0.0, -1.2)), 'io'),
        (2.00, dict(yaw=-32.0, pitch=-4.0, roll=0.0, tyaw=0.0, pel=(0.3, 0.0), drop=0.35, rf=(3.4, 2.5, -38.0, 0.0)), 'io'),
    ])

    def swing(t):
        o = bd.body(SW_K, t)
        bd.weapon(o, path_at(SW_P, SW_T(t)))
        return vis(o)
    a = A('swing', 2.0)
    a.sample(swing, 0.02)
    a.instruction(0.6, 'swing')
    a.instruction(0.75, 'hit')

    # ---------------------------------------------------------------- overhead: рубящий сверху (звук 0.8, hit 0.95 — клинок в земле)
    # замах 0–0.55 (меч за правое плечо, корпус назад, вес назад), взвод до 0.76, удар 0.76–0.98 (дуга ~200° в вертикальной
    # плоскости, левая нога шагает вперёд, таз вниз 0.2 L и вперёд 0.55 L, корпус в наклон −30°), клинок в земле 0.98–1.40
    # (удержание — эталонный hit-stop тяжёлого оружия), выдёргивает 1.40–1.70, возврат с шагом назад до 2.4.
    OV_T = STime([(0, 0), (0.55, 0.25, 'out'), (0.76, 0.29, 'lin'), (0.98, 0.80, ('beta', 2.2, 1.7)), (1.06, 0.815, 'out'),
                  (1.40, 0.82, 'lin'), (1.70, 0.90, 'io'), (2.40, 1.0, 'io')])
    OV_P = [(0.0, dict(GUARD_W)),
            (0.11, dict(hphi=-78.0, hr=9.6, hy=23.5, byaw=-70.0, bth=95.0)),        # клинок поднимается справа от шлема
            (0.25, dict(hphi=-80.0, hr=9.0, hy=28.0, byaw=40.0, bth=168.0)),       # за угол 90° азимут «переворачивается»:
            (0.29, dict(hphi=-82.0, hr=9.0, hy=28.6, byaw=40.0, bth=176.0)),       # +40 при 170° — назад-ВПРАВО, мимо рогов
            (0.45, dict(hphi=-22.0, hr=10.8, hy=26.0, byaw=-14.0, bth=96.0)),       # вертикально — кисти уже вынесены вперёд
            (0.80, dict(hphi=-2.0, hr=10.6, hy=12.0, byaw=2.0, bth=-48.0)),
            (0.815, dict(hphi=-2.0, hr=10.4, hy=12.5, byaw=2.0, bth=-41.0)),
            (0.82, dict(hphi=-2.0, hr=10.4, hy=12.4, byaw=2.0, bth=-43.0)),
            (0.90, dict(hphi=-10.0, hr=8.8, hy=15.5, byaw=8.0, bth=10.0)),
            (1.0, dict(GUARD_W))]
    OV_K = Keys([
        (0.0, dict(yaw=-32.0, pitch=-4.0, roll=0.0, tyaw=0.0, tpitch=0.0, pel=(0.3, 0.0), drop=0.35, hpitch=0.0,
                   rf=(3.4, 2.5, -38.0, 0.0), lf=(-2.6, -2.7, -8.0, 0.0))),
        (0.55, dict(yaw=-62.0, pitch=12.0, roll=-5.0, tpitch=-6.0, pel=(0.5, 1.8), drop=0.2, hpitch=6.0, lf=(-2.4, -1.4, -15.0, 0.0)), 'out'),
        (0.76, dict(yaw=-70.0, pitch=15.0, roll=-6.0, tpitch=-7.0, pel=(0.5, 2.0), drop=0.25, lf=(-2.5, -2.4, -12.0, 1.4)), 'lin'),
        (0.92, dict(yaw=12.0, pitch=-18.0, roll=3.0, tpitch=8.0, pel=(-0.6, -6.2), drop=1.8, hpitch=-14.0, rf=(3.2, -0.6, -18.0, 0.0),
                    lf=(-3.4, -10.6, 6.0, 0.0)), 'in'),
        (1.02, dict(yaw=18.0, pitch=-20.0, pel=(-0.6, -6.4), drop=2.0), 'out'),
        (1.40, dict(yaw=14.0, pitch=-17.0, roll=2.0, pel=(-0.6, -6.0), drop=1.7, lf=(-3.4, -10.6, 6.0, 0.0), rf=(3.2, -0.6, -18.0, 0.0)), 'io'),
        (1.70, dict(yaw=-4.0, pitch=-14.0, tpitch=2.0, pel=(-0.4, -4.6), drop=1.3, hpitch=-4.0), 'io'),
        (1.95, dict(lf=(-3.0, -6.4, -2.0, 1.2), rf=(3.3, 1.2, -30.0, 0.0), pel=(-0.1, -2.6), drop=0.9), 'io'),
        (2.15, dict(lf=(-2.6, -2.7, -8.0, 0.0), rf=(3.4, 2.5, -38.0, 0.0)), 'io'),
        (2.40, dict(yaw=-32.0, pitch=-4.0, roll=0.0, tpitch=0.0, pel=(0.3, 0.0), drop=0.35, hpitch=0.0, rf=(3.4, 2.5, -38.0, 0.0)), 'io'),
    ])

    def overhead(t):
        o = bd.body(OV_K, t)
        bd.weapon(o, path_at(OV_P, OV_T(t)))
        return vis(o)
    a = A('overhead', 2.4)
    a.sample(overhead, 0.02)
    a.instruction(0.8, 'swing')
    a.instruction(0.95, 'hit')

    # ---------------------------------------------------------------- thrust: выпад (hit 0.6; звук/шлейф 0.55)
    # замах 0–0.36 (кисть к правому бедру, остриём вперёд, плечи −70°, таз назад), взвод до 0.44, укол 0.46–0.63 (левая нога —
    # длинный выпад, таз вперёд 0.65 L и вниз, плечи доворачиваются вперёд), держит до 0.80, возврат с отшагом до 1.7.
    TH_T = STime([(0, 0), (0.36, 0.30, 'out'), (0.46, 0.33, 'lin'), (0.63, 0.75, ('beta', 2.0, 2.2)), (0.80, 0.80, 'out'),
                  (1.70, 1.0, 'io')])
    TH_P = [(0.0, dict(GUARD_W)),
            (0.30, dict(hphi=-96.0, hr=6.2, hy=15.6, byaw=-2.0, bth=8.0)),
            (0.33, dict(hphi=-102.0, hr=6.4, hy=15.8, byaw=-2.0, bth=9.0)),
            (0.75, dict(hphi=-4.0, hr=17.0, hy=17.4, byaw=0.0, bth=2.0)),
            (0.80, dict(hphi=-4.0, hr=16.4, hy=17.0, byaw=0.0, bth=0.0)),
            (1.0, dict(GUARD_W))]
    TH_K = Keys([
        (0.0, dict(yaw=-32.0, pitch=-4.0, roll=0.0, tyaw=0.0, pel=(0.3, 0.0), drop=0.35, rf=(3.4, 2.5, -38.0, 0.0), lf=(-2.6, -2.7, -8.0, 0.0))),
        (0.36, dict(yaw=-72.0, pitch=5.0, roll=-5.0, tyaw=5.0, pel=(0.6, 1.9), drop=0.8, lf=(-2.4, -1.8, -14.0, 0.0)), 'out'),
        (0.46, dict(yaw=-78.0, pitch=6.0, pel=(0.6, 2.2), drop=0.85, lf=(-2.5, -2.6, -12.0, 1.4)), 'lin'),
        (0.59, dict(yaw=8.0, pitch=-13.0, roll=2.0, tyaw=-6.0, pel=(-0.6, -7.6), drop=1.6, rf=(3.2, -1.0, -15.0, 0.0),
                    lf=(-3.2, -13.0, 2.0, 0.0)), 'in'),
        (0.70, dict(yaw=12.0, pitch=-15.0, tyaw=2.0, pel=(-0.6, -7.9), drop=1.7, rf=(3.1, -1.6, -12.0, 0.0)), 'back'),
        (0.80, dict(yaw=8.0, pitch=-12.0, pel=(-0.5, -7.4), drop=1.5, lf=(-3.2, -13.0, 2.0, 0.0), rf=(3.1, -1.6, -12.0, 0.0)), 'io'),
        (1.20, dict(yaw=-10.0, pitch=-10.0, pel=(-0.2, -4.6), drop=1.2, lf=(-3.0, -7.6, -4.0, 1.2), rf=(3.3, 0.8, -25.0, 0.0)), 'io'),
        (1.40, dict(lf=(-2.6, -2.7, -8.0, 0.0), rf=(3.4, 2.5, -38.0, 0.0), pel=(0.1, -1.4), drop=0.6), 'io'),
        (1.70, dict(yaw=-32.0, pitch=-4.0, roll=0.0, tyaw=0.0, pel=(0.3, 0.0), drop=0.35, rf=(3.4, 2.5, -38.0, 0.0)), 'io'),
    ])

    def thrust(t):
        o = bd.body(TH_K, t)
        bd.weapon(o, path_at(TH_P, TH_T(t)))
        return vis(o)
    a = A('thrust', 1.7)
    a.sample(thrust, 0.02)
    a.instruction(0.6, 'hit')

    # ---------------------------------------------------------------- shield_bash: щит в руку (0.12), сжаться за щитом, рывок
    # (кодом 0.45–0.75, ноги бегут), толчок щитом с плеча (hit 0.75), отдача, возврат.
    BS_K = Keys([
        (0.0, dict(yaw=-32.0, pitch=-4.0, roll=0.0, tyaw=0.0, pel=(0.3, 0.0), drop=0.35, rf=(3.4, 2.5, -38.0, 0.0), lf=(-2.6, -2.7, -8.0, 0.0))),
        (0.35, dict(yaw=-80.0, pitch=-18.0, roll=-3.0, tyaw=4.0, pel=(0.2, 1.0), drop=2.0, lf=(-2.6, -2.2, -20.0, 0.0)), 'out'),
        (0.45, dict(yaw=-78.0, pitch=-20.0, drop=2.1), 'lin'),
        (0.53, dict(rf=(2.6, -1.0, -25.0, 2.2), pel=(0.1, -1.2)), 'io'),
        (0.61, dict(rf=(2.6, -5.6, -25.0, 0.0), lf=(-2.8, -3.4, -20.0, 1.8), pel=(0.0, -3.0), drop=1.8), 'io'),
        (0.70, dict(lf=(-3.0, -9.0, -15.0, 0.0), yaw=-40.0, pitch=-22.0, pel=(-0.2, -5.0), drop=1.7), 'io'),
        (0.75, dict(yaw=-4.0, pitch=-26.0, roll=3.0, tyaw=-6.0, pel=(-0.3, -6.0), drop=1.6), 'in'),
        (0.86, dict(yaw=-24.0, pitch=-14.0, tyaw=2.0, pel=(-0.2, -5.0), drop=1.1), 'back'),
        (1.05, dict(yaw=-28.0, pitch=-10.0, rf=(2.6, -5.6, -25.0, 0.0), lf=(-3.0, -9.0, -15.0, 0.0)), 'io'),
        (1.20, dict(rf=(3.2, -1.5, -35.0, 1.2), pel=(0.0, -3.2)), 'io'),
        (1.32, dict(rf=(3.4, 2.5, -38.0, 0.0), lf=(-2.8, -6.0, -10.0, 1.0), pel=(0.1, -1.5), drop=0.6), 'io'),
        (1.50, dict(yaw=-32.0, pitch=-4.0, roll=0.0, tyaw=0.0, pel=(0.3, 0.0), drop=0.35, lf=(-2.6, -2.7, -8.0, 0.0)), 'io'),
    ])
    SH = Keys([(0, dict(k=0.0, p=0.0)), (0.35, dict(k=1.0), 'out'), (0.66, dict(p=0.0)), (0.75, dict(p=1.0), 'in'),
               (0.86, dict(p=0.55), 'back'), (1.15, dict(k=1.0, p=0.3)), (1.5, dict(k=0.0, p=0.0))])

    def bash(t):
        o = bd.body(BS_K, t)
        k, p = SH.f(t, 'k'), SH.f(t, 'p')
        if k > 0.01:
            sf(o, (-1.2, 15.8, -6.0 - 4.5 * p), tilt=-4 - 8 * p, yaw=-12 + 6 * p, w=min(1, k * 1.3))
        # меч — отведён вправо-назад, остриём назад (не мешает щиту)
        w = path_at([(0.0, dict(GUARD_W)), (1.0, dict(hphi=-112.0, hr=6.4, hy=14.0, byaw=-160.0, bth=30.0))], k)
        bd.weapon(o, w, left=0.0)
        return vis(o, shield_hand=0.12 < t < 1.4)
    a = A('shield_bash', 1.5)
    a.sample(bash, 0.04)
    a.instruction(0.12, 'shield_draw')
    a.instruction(0.45, 'dash')
    a.instruction(0.75, 'hit')


# ================================================================== жесты с мечом (приказы, вызов, клич) — эталон EF, 21.11
# Тики событий и длины — прежние (MartinMath: COMMAND 44/17, VOLLEY 44/16/24, DUEL 40/18, WARCRY 36/12; cavalry 3.4 с: call 1.0,
# charge 2.0). Устройство: стойка → предвосхищение (уход в противоположную сторону, 'out') → рывок к позе события ('in') с перехлёстом
# ('back') → удержание с дрожью/дыханием → возврат в стойку. Свободная левая рука — во внутренних осях (X > 0 — вперёд/вверх, Z < 0 —
# в сторону); вес левой руки на рукояти lw (0 — своя поза, 1 — на рукояти).
def define_gestures(A, m, G, g, sf):
    bd = Body(m, G, g, sf)
    vis = G.vis

    def run(K, P_, t, look=0.0, wind=0.0):
        o = bd.body(K, t, look=look, wind=float(K(t, 'wind', 0.0)) + wind)
        lw = float(K(t, 'lw', 1.0))
        o['left_arm'] = {'rot': list(np.asarray(K(t, 'larm', (0.0, 0.0, 0.0)), float))}
        o['left_forearm'] = {'rot': [float(K(t, 'lfore', 0.0)), 0.0, 0.0]}
        bd.weapon(o, path_at(P_[0], P_[1](t)), left=lw)
        return vis(o)

    ST = dict(yaw=-32.0, pitch=-4.0, roll=0.0, pel=(0.3, 0.0), drop=0.35, hpitch=0.0, rf=(3.4, 2.5, -38.0, 0.0), lf=(-2.6, -2.7, -8.0, 0.0),
              lw=1.0, larm=(0.0, 0.0, 0.0), lfore=0.0, wind=0.0)

    # ---------------------------------------------------------------- command «в атаку!» (command 0.85): собирается (меч вниз-назад,
    # плечи вправо), рывком выбрасывает меч вверх-вперёд одной рукой, левая — в сторону, рёв; держит; стойка к 2.2
    CM_T = STime([(0, 0), (0.45, 0.3, 'out'), (0.62, 0.34, 'lin'), (0.85, 0.85, ('beta', 2.0, 1.8)), (0.95, 0.9, 'out'), (1.6, 0.92, 'lin'),
                  (2.2, 1.0, 'io')])
    CM_P = [(0.0, dict(GUARD_W)), (0.15, dict(hphi=-60.0, hr=8.0, hy=13.5, byaw=-60.0, bth=10.0)),     # меч — вниз-назад через правый бок
            (0.3, dict(hphi=-100.0, hr=7.0, hy=14.0, byaw=-135.0, bth=-28.0)),
            (0.34, dict(hphi=-104.0, hr=7.0, hy=13.6, byaw=-138.0, bth=-32.0)), (0.85, dict(hphi=-12.0, hr=8.5, hy=31.0, byaw=0.0, bth=72.0)),
            (0.9, dict(hphi=-10.0, hr=8.6, hy=31.6, byaw=0.0, bth=66.0)), (0.92, dict(hphi=-10.0, hr=8.6, hy=31.4, byaw=0.0, bth=68.0)),
            (1.0, dict(GUARD_W))]
    CM_K = Keys([(0.0, dict(ST)),
                 (0.20, dict(lw=0.0), 'io'),
                 (0.45, dict(yaw=-55.0, pitch=-8.0, drop=1.4, hpitch=-8.0, larm=(10.0, 0.0, -14.0), lfore=30.0, pel=(0.5, 0.8)), 'out'),
                 (0.62, dict(yaw=-58.0, pitch=-9.0, drop=1.5, hpitch=-9.0), 'lin'),
                 (0.85, dict(yaw=-8.0, pitch=8.0, drop=0.2, hpitch=20.0, larm=(30.0, 0.0, -48.0), lfore=34.0, pel=(0.0, -1.2), wind=6.0,
                             lf=(-2.8, -4.4, -4.0, 0.0)), 'in'),
                 (0.95, dict(yaw=-4.0, pitch=10.0, hpitch=24.0, larm=(34.0, 0.0, -54.0)), 'back'),
                 (1.6, dict(yaw=-8.0, pitch=8.0, hpitch=18.0, larm=(30.0, 0.0, -50.0), lw=0.0, wind=4.0, lf=(-2.8, -4.4, -4.0, 0.0)), 'io'),
                 (2.0, dict(lw=1.0), 'io'),
                 (2.2, dict(ST), 'io')])
    a = A('command', 2.2)
    a.sample(lambda t: run(CM_K, (CM_P, CM_T), t), 0.02)
    a.instruction(0.85, 'command')

    # ---------------------------------------------------------------- volley «натянуть!» (draw 0.8) — «пли!» (loose 1.2)
    VO_T = STime([(0, 0), (0.8, 0.40, 'out'), (1.06, 0.43, 'lin'), (1.24, 0.85, ('beta', 2.2, 1.9)), (1.34, 0.88, 'out'), (1.7, 0.9, 'lin'),
                  (2.2, 1.0, 'io')])
    VO_P = [(0.0, dict(GUARD_W)), (0.40, dict(hphi=-28.0, hr=4.2, hy=32.0, byaw=40.0, bth=96.0)),
            (0.43, dict(hphi=-30.0, hr=4.0, hy=33.0, byaw=40.0, bth=100.0)), (0.85, dict(hphi=-6.0, hr=10.0, hy=18.0, byaw=0.0, bth=-30.0)),
            (0.88, dict(hphi=-6.0, hr=10.0, hy=17.0, byaw=0.0, bth=-38.0)), (0.9, dict(hphi=-6.0, hr=9.8, hy=17.4, byaw=0.0, bth=-34.0)),
            (1.0, dict(GUARD_W))]
    VO_K = Keys([(0.0, dict(ST)),
                 (0.25, dict(lw=0.0), 'io'),
                 (0.8, dict(yaw=-24.0, pitch=8.0, drop=0.1, hpitch=18.0, larm=(30.0, 0.0, -50.0), lfore=20.0, pel=(0.6, 1.0), wind=4.0), 'out'),
                 (1.06, dict(yaw=-26.0, pitch=10.0, hpitch=20.0, larm=(32.0, 0.0, -54.0), lf=(-2.6, -2.4, -8.0, 1.2)), 'lin'),
                 (1.22, dict(yaw=-6.0, pitch=-16.0, drop=1.6, hpitch=-6.0, larm=(18.0, 0.0, -30.0), pel=(-0.4, -4.0),
                             lf=(-3.2, -7.4, 4.0, 0.0)), 'in'),
                 (1.34, dict(pitch=-19.0, drop=1.9, pel=(-0.5, -4.6)), 'back'),
                 (1.7, dict(pitch=-14.0, drop=1.5, lw=0.0, lf=(-3.2, -7.4, 4.0, 0.0)), 'io'),
                 (1.95, dict(lw=1.0, lf=(-2.6, -2.7, -8.0, 0.0), pel=(0.1, -1.0)), 'io'),
                 (2.2, dict(ST), 'io')])
    a = A('volley', 2.2)
    a.sample(lambda t: run(VO_K, (VO_P, VO_T), t), 0.02)
    a.instruction(0.8, 'draw')
    a.instruction(1.2, 'loose')

    # ---------------------------------------------------------------- cavalry «Атака конницы» (call 1.0 — меч к небу, charge 2.0 — взмах)
    CA_T = STime([(0, 0), (1.0, 0.40, 'out'), (1.86, 0.44, 'lin'), (2.04, 0.85, ('beta', 2.2, 1.9)), (2.14, 0.88, 'out'), (2.8, 0.9, 'lin'),
                  (3.4, 1.0, 'io')])
    CA_K = Keys([(0.0, dict(ST)),
                 (0.3, dict(lw=0.0), 'io'),
                 (1.0, dict(yaw=-20.0, pitch=10.0, drop=0.1, hpitch=24.0, larm=(28.0, 0.0, -40.0), lfore=20.0, pel=(0.4, 0.8), wind=6.0), 'out'),
                 (1.5, dict(yaw=-24.0, pitch=11.0, hpitch=26.0, larm=(30.0, 0.0, -44.0)), 'io'),
                 (1.86, dict(yaw=-26.0, pitch=12.0, hpitch=22.0, lf=(-2.6, -2.4, -8.0, 1.2)), 'lin'),
                 (2.02, dict(yaw=-4.0, pitch=-18.0, drop=1.8, hpitch=-6.0, larm=(16.0, 0.0, -28.0), pel=(-0.5, -4.4),
                             lf=(-3.2, -7.8, 4.0, 0.0), wind=10.0), 'in'),
                 (2.14, dict(pitch=-21.0, drop=2.0, pel=(-0.6, -5.0)), 'back'),
                 (2.8, dict(pitch=-15.0, drop=1.5, lw=0.0, lf=(-3.2, -7.8, 4.0, 0.0), wind=4.0), 'io'),
                 (3.1, dict(lw=1.0, lf=(-2.6, -2.7, -8.0, 0.0), pel=(0.1, -1.0)), 'io'),
                 (3.4, dict(ST), 'io')])
    a = A('cavalry', 3.4)
    a.sample(lambda t: run(CA_K, (VO_P, CA_T), t), 0.02)
    a.instruction(1.0, 'call')
    a.instruction(2.0, 'charge')

    # ---------------------------------------------------------------- duel «Вызов на дуэль» (challenge 0.9): оттягивает меч к бедру,
    # выбрасывает остриё на игрока одной рукой (плечи в профиль), левая ладонь к груди; держит; стойка к 2.0
    DU_T = STime([(0, 0), (0.55, 0.35, 'out'), (0.7, 0.38, 'lin'), (0.9, 0.85, ('beta', 2.0, 2.0)), (1.0, 0.88, 'out'), (1.5, 0.9, 'lin'),
                  (2.0, 1.0, 'io')])
    DU_P = [(0.0, dict(GUARD_W)), (0.35, dict(hphi=-96.0, hr=6.4, hy=15.2, byaw=-4.0, bth=8.0)),
            (0.38, dict(hphi=-100.0, hr=6.4, hy=15.4, byaw=-4.0, bth=8.0)), (0.85, dict(hphi=-10.0, hr=12.0, hy=21.0, byaw=0.0, bth=4.0)),
            (0.88, dict(hphi=-10.0, hr=12.4, hy=21.2, byaw=0.0, bth=3.0)), (0.9, dict(hphi=-10.0, hr=12.2, hy=21.0, byaw=0.0, bth=4.0)),
            (1.0, dict(GUARD_W))]
    DU_K = Keys([(0.0, dict(ST)),
                 (0.25, dict(lw=0.0), 'io'),
                 (0.55, dict(yaw=-60.0, pitch=2.0, drop=0.9, pel=(0.6, 1.4), larm=(30.0, 0.0, 10.0), lfore=60.0), 'out'),
                 (0.7, dict(yaw=-62.0, pitch=2.0, drop=1.0), 'lin'),
                 (0.9, dict(yaw=-48.0, pitch=-8.0, drop=0.9, pel=(-0.2, -2.6), larm=(50.0, 0.0, 30.0), lfore=80.0,
                            lf=(-3.0, -6.0, -2.0, 0.0)), 'in'),
                 (1.0, dict(yaw=-46.0, pitch=-9.0, pel=(-0.3, -2.9)), 'back'),
                 (1.5, dict(yaw=-48.0, pitch=-7.0, lw=0.0, lf=(-3.0, -6.0, -2.0, 0.0)), 'io'),
                 (1.8, dict(lw=1.0, lf=(-2.6, -2.7, -8.0, 0.0), pel=(0.2, -0.6)), 'io'),
                 (2.0, dict(ST), 'io')])
    a = A('duel', 2.0)
    a.sample(lambda t: run(DU_K, (DU_P, DU_T), t, look=0.0), 0.02)
    a.instruction(0.9, 'challenge')

    # ---------------------------------------------------------------- warcry «Боевой клич» (cry 0.6): вдох — сжимается, меч к себе;
    # рёв — корпус назад, руки в стороны, таз вниз, дрожь; держит; стойка к 1.8
    WC_T = STime([(0, 0), (0.42, 0.35, 'out'), (0.62, 0.8, ('beta', 2.0, 1.6)), (0.72, 0.84, 'out'), (1.3, 0.86, 'lin'), (1.8, 1.0, 'io')])
    WC_P = [(0.0, dict(GUARD_W)), (0.35, dict(hphi=-30.0, hr=5.6, hy=15.0, byaw=10.0, bth=70.0)),
            (0.8, dict(hphi=-92.0, hr=10.4, hy=20.0, byaw=-70.0, bth=40.0)), (0.84, dict(hphi=-96.0, hr=10.6, hy=20.6, byaw=-74.0, bth=44.0)),
            (0.86, dict(hphi=-94.0, hr=10.5, hy=20.3, byaw=-72.0, bth=42.0)), (1.0, dict(GUARD_W))]
    WC_K = Keys([(0.0, dict(ST)),
                 (0.15, dict(lw=0.0), 'io'),
                 (0.42, dict(yaw=-20.0, pitch=-10.0, drop=1.2, hpitch=-10.0, larm=(30.0, 0.0, -6.0), lfore=50.0), 'out'),
                 (0.6, dict(yaw=-24.0, pitch=12.0, drop=1.4, hpitch=26.0, larm=(20.0, 0.0, -70.0), lfore=30.0, pel=(0.2, 0.6), wind=8.0,
                            rf=(3.8, 2.8, -40.0, 0.0), lf=(-3.2, -3.0, -6.0, 0.0)), 'in'),
                 (0.72, dict(pitch=14.0, hpitch=30.0, larm=(22.0, 0.0, -76.0)), 'back'),
                 (1.3, dict(pitch=12.0, hpitch=26.0, larm=(20.0, 0.0, -70.0), lw=0.0, wind=6.0, rf=(3.8, 2.8, -40.0, 0.0),
                            lf=(-3.2, -3.0, -6.0, 0.0)), 'io'),
                 (1.6, dict(lw=1.0), 'io'),
                 (1.8, dict(ST), 'io')])

    def warcry(t):
        o = run(WC_K, (WC_P, WC_T), t)
        c = max(0.0, 1.0 - abs(t - 0.9) / 0.4) if 0.55 < t < 1.3 else 0.0         # дрожь рёва — только голова и грудь
        if c > 0:
            o['torso']['rot'][2] += 0.8 * c * math.sin(t * 60)
            o['head']['rot'][2] += 1.6 * c * math.sin(t * 60 + 0.7)
        return o
    a = A('warcry', 1.8)
    a.sample(warcry, 0.02)
    a.instruction(0.6, 'cry')


# ================================================================== остаток Мартина (ходьба, особые, фазы, сцены) — эталон EF, 21.11
# Длины и тики событий — прежние (MartinMath). Все начинаются и кончаются в стойке STANCE с хватом GUARD_W (как idle), кроме петель
# и «держащих» (hold_the_line → hold_loop → hold_end, block_yield → to_npc → npc_idle — стыки между ними совпадают).
# Оружие — путь по времени из точек трёх видов: ('G',) — хват стойки (мир, от таза), ('T', кисть, клинок) — в осях торса
# (как старые GUARD/LEAN/HOLD_SW), ('W', кисть, клинок) — неподвижно в мире (меч воткнут в землю: остриё не ездит вместе с телом).
class FnK:
    """Ключи-функция: fn(t) → dict (для петель — ходьба, дыхание)."""

    def __init__(self, fn):
        self.fn = fn

    def __call__(self, t, name, default=0.0):
        v = self.fn(t).get(name, default)
        return np.asarray(v, float) if isinstance(v, (tuple, list)) else v

    def f(self, t, name, default=0.0):
        return float(self(t, name, default))


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def define_rest(A, m, G, g, sf):
    bd = Body(m, G, g, sf)
    vis = G.vis
    ST = dict(yaw=-32.0, pitch=-4.0, roll=0.0, tyaw=0.0, tpitch=0.0, pel=(0.3, 0.0), drop=0.35, hpitch=0.0,
              rf=(3.4, 2.5, -38.0, 0.0), lf=(-2.6, -2.7, -8.0, 0.0), lw=1.0, larm=(0.0, 0.0, 0.0), lfore=0.0, wind=0.0)
    GUARD_T, LEAN_T = G.GUARD, G.LEAN
    LEAN_W = ('W', (0.3, 18.6, -7.6), (0.0, -0.99, -0.12))                 # опора на меч (как прежний LEAN в покое): остриё в земле
    HOLD_SW = ('T', (5.0, 30.0, -2.0), (0.1, 0.9, -0.42))                   # меч поднят над щитом
    DOWN_T = ('T', (4.0, 13.5, -4.0), (0.12, -0.45, -0.88))                 # опущенный меч (сдача), остриё у земли

    def wp(o, p):
        if p[0] == 'G':
            pel = o['body']['pos']
            return (cyl(GUARD_W['hphi'], GUARD_W['hr'], GUARD_W['hy']) + np.array([pel[0], 0.0, pel[2]]),
                    sag_dir(GUARD_W['byaw'], GUARD_W['bth']))
        if p[0] == 'T':
            Mt, ot = G.fk(m, o, 'torso')
            return Mt @ np.asarray(p[1], float) + ot, Mt @ _unit(p[2])
        return np.asarray(p[1], float), _unit(p[2])

    def wpath(o, P, t):
        """P: [(t, точка, кривая)] → (кисть, клинок) в мире."""
        if t <= P[0][0]:
            return wp(o, P[0][1])
        for (t0, p0, *_), (t1, p1, e) in zip(P, P[1:]):
            if t <= t1:
                k = B.ease((t - t0) / max(1e-6, t1 - t0), e)
                h0, d0 = wp(o, p0)
                h1, d1 = wp(o, p1)
                return h0 * (1 - k) + h1 * k, G.lerp_dir(d0, d1, k)
        return wp(o, P[-1][1])

    def arm_to(o, hw, dw, left):
        sh = G.world_pt(m, o, 'right_arm', m.bones['right_arm'].pivot)
        d = hw - sh
        if np.linalg.norm(d) > REACH:
            hw = sh + d / np.linalg.norm(d) * REACH
        Mt, ot = G.fk(m, o, 'torso')
        g(o, Mt.T @ (hw - ot), Mt.T @ _unit(dw), left=left)

    def pose(K, t, look=0.0, cape_lag=0.1, sway=1.0, period=3.0):
        o = bd.body(K, t, look=look, wind=float(K(t, 'wind', 0.0)), cape_lag=cape_lag, sway=sway, period=period)
        o['left_arm'] = {'rot': list(np.asarray(K(t, 'larm', (0.0, 0.0, 0.0)), float))}
        o['left_forearm'] = {'rot': [float(K(t, 'lfore', 0.0)), 0.0, 0.0]}
        return o

    def shield(o, K, t):
        w = float(K(t, 'sw', 0.0))
        if w > 0.005:
            sf(o, tuple(K(t, 'sh', (-0.8, 12.6, -6.4))), tilt=float(K(t, 'stilt', 8.0)), yaw=float(K(t, 'syaw', 0.0)), w=min(1.0, w))

    # ---------------------------------------------------------------- walk (петля 1.6; step 0.4 / 1.2 — удар правой / левой пяткой)
    # стопы — точки на земле: опора уезжает назад под телом, перенос — дугой вперёд; таз ниже всего на ударе пятки и выше всего над
    # опорой, качается к опорной ноге; плечи крутятся против бёдер, свободная рука — против ноги; меч на плече.
    S = 4.2

    def foot(u, x):
        if u < 0.5:
            return (x, -S + 2 * S * u / 0.5, 0.0, 0.0)
        v = (u - 0.5) / 0.5
        return (x, S - 2 * S * B.ease(v, 'io'), 0.0, 2.2 * math.sin(math.pi * v))

    def walk_k(t):
        u = (t / 1.6 - 0.25) % 1.0
        c = math.cos(TAU * u)
        return dict(yaw=-8.0 - 7.0 * c, pitch=-5.0, roll=-1.5 * math.sin(TAU * u), tyaw=2.5 * c, tpitch=1.0 * math.cos(2 * TAU * u),
                    pel=(0.35 * math.sin(TAU * u), -0.3), drop=0.55 + 0.35 * math.cos(2 * TAU * u),
                    rf=foot(u, 2.8), lf=foot((u + 0.5) % 1.0, -2.8), hpitch=1.0,
                    larm=(20.0 * c, 0.0, -7.0), lfore=14.0 + 8.0 * max(0.0, c), wind=3.0)
    WK = FnK(walk_k)

    def walk(t):
        o = pose(WK, t, period=0.8)
        g(o, G.SHOULDER[0], G.SHOULDER[1], left=0)
        return vis(o)
    a = A('walk', 1.6, True)
    a.sample(walk, 0.05)
    a.instruction(0.4, 'step')
    a.instruction(1.2, 'step')

    # ---------------------------------------------------------------- banner_plant (raise 0.7, plant 1.3): знамя в левой — вверх
    # (корпус назад, вес назад), удар древком в землю с шагом левой и просадкой, держит, стойка к 2.4. Меч — одной правой у бедра.
    def bp_k(dn, up):
        return dict(larm=(150.0 * up + 50.0 * dn, 0.0, -10.0 * up), lfore=10.0 * up)
    BP_K = Keys([(0.0, dict(ST)),
                 (0.2, dict(lw=0.0), 'io'),
                 (0.7, dict(yaw=-4.0, pitch=8.0, roll=-3.0, drop=0.2, pel=(0.3, 0.8), hpitch=16.0, **bp_k(0, 1), wind=3.0), 'out'),
                 (1.15, dict(yaw=-2.0, pitch=10.0, drop=0.3, hpitch=18.0, pel=(0.3, 1.0), lf=(-2.6, -2.7, -8.0, 1.6), **bp_k(0, 1)), 'io'),
                 (1.3, dict(yaw=4.0, pitch=-16.0, roll=2.0, drop=1.8, pel=(-0.2, -2.0), hpitch=-10.0, lf=(-2.9, -6.2, -4.0, 0.0),
                            **bp_k(1, 0), wind=0.0), 'in'),
                 (1.4, dict(pitch=-18.0, drop=1.95), 'back'),
                 (1.8, dict(yaw=2.0, pitch=-14.0, drop=1.7, pel=(-0.2, -1.9), lf=(-2.9, -6.2, -4.0, 0.0), **bp_k(1, 0)), 'io'),
                 (2.05, dict(lf=(-2.7, -4.0, -6.0, 1.2), pel=(0.1, -0.8), drop=0.9, **bp_k(0, 0)), 'io'),
                 (2.2, dict(lw=0.0), 'io'),
                 (2.4, dict(ST), 'io')])
    BP_BAN = Keys([(0.0, dict(r=0.0)), (1.15, dict(r=0.0)), (1.3, dict(r=-90.0), 'in'), (2.4, dict(r=-90.0))])
    BP_W = [(0.0, ('G',), 'io'), (0.6, ('T', (4.6, 14.0, -4.0), (0.25, 0.75, -0.6)), 'io'), (1.8, ('T', (4.6, 14.0, -4.0), (0.25, 0.75, -0.6)), 'io'),
            (2.4, ('G',), 'io')]

    # Подмена знамени сущностью (MartinFight.plantBanner, тик PLANT_AT = 26 = 1.3 с): к 1.3 древко в руке стоит ВЕРТИКАЛЬНО, низ — в точке
    # сущности (MartinMath.BANNER_FWD / BANNER_LEFT, бл. → ед. модели Мартина ×8), полотнище лицом вперёд, размер — как у сущности
    # (масштаб кости). 1.3–1.4 рука держит древко на месте (перекрытие на тик), потом знамя в руке скрыто, рука отпускает.
    BAN_B = np.array([-1.125 * 8.0, 0.0, -1.5 * 8.0])          # = MartinMath.BANNER_LEFT 1.125, BANNER_FWD 1.5
    BAN_S = [0.7, 0.871, 0.871]                                 # высота 63.4 px и полотнище 14 px — как martin_banner.geo.json
    BAN_P = np.array([-5.6, 10.6, -0.2])                        # шарнир banner_held = кисть; древко — ось y, низ на −10
    BAN_GRIP = 14.0                                             # кисть над землёй в момент вонзания (рука дотягивается)
    BAN_HAND = Keys([(0.9, dict(h=0.0)), (1.15, dict(h=1.0)), (1.4, dict(h=1.0)), (1.75, dict(h=0.0))])
    BAN_DROP = Keys([(0.0, dict(y=12.0)), (1.15, dict(y=12.0)), (1.3, dict(y=0.0), 'in'), (2.4, dict(y=0.0))])
    bprev = [None]

    def plant(t):
        o = pose(BP_K, t)
        o['banner_held'] = {'rot': [BP_BAN.f(t, 'r'), 0.0, 0.0]}
        arm_to(o, *wpath(o, BP_W, t), left=BP_K.f(t, 'lw'))
        w = B.ease(BAN_HAND.f(t, 'h'), 'io')
        if w > 0.001:
            # кисть: от позы по ключам к точке над местом сущности (знамя опускается на BAN_DROP), решатель руки
            hk = G.world_pt(m, o, 'left_forearm', BAN_P)
            ht = BAN_B + np.array([0.0, BAN_GRIP + BAN_DROP.f(t, 'y'), 0.0])
            sol, _ = G.solve_arm(m, o, 'left', hk * (1 - w) + ht * w, bprev[0])
            bprev[0] = sol
            o['left_arm'] = dict(o['left_arm'], rot=list(sol[:3]))
            o['left_forearm'] = {'rot': [sol[3], 0, 0]}
            # древко вертикально: полный поворот кости = I (коробки знамени заданы стоя) → углы = to_euler(Mf^T) − покой кости
            Mf, _ = G.fk(m, o, 'left_forearm')
            rv = np.array(G.to_euler(Mf.T), float) - np.asarray(m.bones['banner_held'].rot, float)
            rk = np.array(o['banner_held']['rot'], float)
            rv += 360.0 * np.round((rk - rv) / 360.0)
            o['banner_held']['rot'] = list(rk * (1 - w) + rv * w)
            # низ древка — в точку (кисть держит выше по древку): сдвиг кости вдоль древка в осях предплечья
            low = G.world_pt(m, o, 'banner_held', BAN_P + np.array([0.0, -10.0 * BAN_S[1], 0.0]))
            want = BAN_B + np.array([0.0, -0.5 + BAN_DROP.f(t, 'y'), 0.0])
            top = G.world_pt(m, o, 'banner_held', BAN_P + np.array([0.0, 26.4 * BAN_S[1], 0.0]))
            ax = (top - low) / np.linalg.norm(top - low)
            o['banner_held']['pos'] = list(Mf.T @ (ax * float((want - low) @ ax)) * w)       # только вдоль древка: оно всегда в кулаке
        else:
            bprev[0] = None
        o = vis(o, banner=0.15 < t < 1.4)            # знамя «в руке» — когда левая отпустила рукоять; до 1.4 — перекрытие с сущностью
        if 0.15 < t < 1.4:
            o['banner_held']['scale'] = list(BAN_S)
        return o
    a = A('banner_plant', 2.4)
    a.sample(plant, 0.02)
    a.instruction(0.7, 'raise')
    a.instruction(1.3, 'plant')

    # ---------------------------------------------------------------- «Стоять насмерть»: hold_the_line (shield_draw 0.15, wall 1.1),
    # hold_loop (2.0, дыхание), hold_end (0.8). Щит со спины — вверх (собирается, вес назад), с размаху в землю перед собой с шагом левой,
    # широкая низкая стойка лицом к врагу, меч поднят над щитом.
    HOLD = dict(yaw=-8.0, pitch=-10.0, roll=0.0, tyaw=0.0, pel=(0.0, -1.0), drop=1.9, hpitch=6.0, rf=(4.0, 3.4, -25.0, 0.0),
                lf=(-3.4, -5.0, -5.0, 0.0), lw=0.0, sw=1.0, sh=(-0.8, 12.6, -6.4), stilt=8.0, wind=0.0)
    HT_K = Keys([(0.0, dict(ST, sw=0.0, sh=(-1.2, 15.0, -6.0), stilt=0.0)),
                 (0.15, dict(lw=0.0), 'io'),
                 (0.45, dict(sw=1.0), 'io'),
                 (0.7, dict(yaw=-16.0, pitch=5.0, drop=0.5, pel=(0.3, 0.9), hpitch=4.0, sh=(-1.2, 18.0, -6.0), stilt=-8.0,
                            lf=(-2.6, -2.7, -8.0, 0.0)), 'out'),
                 (0.85, dict(lf=(-3.0, -4.0, -6.0, 1.4)), 'io'),
                 (1.1, dict(HOLD, pitch=-12.0, drop=2.0), 'in'),
                 (1.25, dict(pitch=-13.0, drop=2.05), 'back'),
                 (1.5, dict(HOLD), 'io'),
                 (2.5, dict(HOLD), 'io')])
    HT_W = [(0.0, ('G',), 'io'), (0.7, ('T', (4.6, 24.0, -3.0), (0.15, 0.95, -0.25)), 'out'), (1.1, HOLD_SW, 'in'), (2.5, HOLD_SW, 'io')]

    def hold(t):
        o = pose(HT_K, t)
        shield(o, HT_K, t)
        arm_to(o, *wpath(o, HT_W, t), left=HT_K.f(t, 'lw'))
        return vis(o, shield_hand=t > 0.15)
    a = A('hold_the_line', 2.5, 'hold')
    a.sample(hold, 0.02)
    a.instruction(0.15, 'shield_draw')
    a.instruction(1.1, 'wall')

    def hl_k(t):
        br = math.sin(TAU * t / 2.0)
        return dict(HOLD, drop=HOLD['drop'] - 0.12 * br, pitch=HOLD['pitch'] + 1.0 * br, tpitch=0.6 * br, hpitch=HOLD['hpitch'] - 0.8 * br)
    HL_K = FnK(hl_k)

    def hold_loop(t):
        o = pose(HL_K, t, period=2.0)
        shield(o, HL_K, t)
        br = math.sin(TAU * t / 2.0)
        arm_to(o, *wp(o, ('T', (5.0, 30.0 + 0.2 * br, -2.0), HOLD_SW[2])), left=0.0)
        return vis(o, shield_hand=True)
    A('hold_loop', 2.0, True).sample(hold_loop, 0.05)

    HE_K = Keys([(0.0, dict(HOLD)),
                 (0.2, dict(drop=1.6, pitch=-8.0), 'io'),
                 (0.42, dict(lf=(-2.9, -4.0, -6.0, 1.2), rf=(3.7, 3.0, -32.0, 0.0), pel=(0.1, -0.5), drop=1.0), 'io'),
                 (0.6, dict(sw=0.15, sh=(-1.2, 15.0, -6.0), stilt=0.0), 'io'),
                 (0.65, dict(sw=0.0, lw=0.0), 'io'),
                 (0.8, dict(ST, sw=0.0, sh=(-1.2, 15.0, -6.0), stilt=0.0), 'io')])
    HE_W = [(0.0, HOLD_SW, 'io'), (0.8, ('G',), 'io')]

    def hold_end(t):
        o = pose(HE_K, t)
        shield(o, HE_K, t)
        arm_to(o, *wpath(o, HE_W, t), left=HE_K.f(t, 'lw'))
        return vis(o, shield_hand=t < 0.7)
    A('hold_end', 0.8).sample(hold_end, 0.02)

    # ---------------------------------------------------------------- phase2 (66%; plant 0.6, roar 1.4): меч вверх остриём вниз
    # (вес назад) — вонзает в землю перед собой с шагом и просадкой, налегает на навершие; выпрямляется и ревёт (корпус назад, голова
    # вверх); к 2.4 выдёргивает меч и встаёт в стойку — в 2.4 код запускает banner_plant (MartinMath.P2_PLANT_ANIM), стык — стойка.
    P_PLANT = ('W', (0.3, 17.4, -9.6), (0.0, -0.97, -0.24))
    P2_K = Keys([(0.0, dict(ST)),
                 (0.42, dict(yaw=-18.0, pitch=7.0, drop=0.2, pel=(0.3, 0.8), hpitch=8.0), 'out'),
                 (0.5, dict(lf=(-2.8, -4.4, -6.0, 1.2)), 'io'),
                 (0.6, dict(yaw=-6.0, pitch=-16.0, roll=2.0, drop=1.9, pel=(0.0, -1.6), hpitch=-14.0, lf=(-3.0, -5.6, -6.0, 0.0)), 'in'),
                 (0.7, dict(pitch=-18.0, drop=2.0), 'back'),
                 (1.15, dict(pitch=-12.0, drop=1.6, hpitch=-8.0), 'io'),
                 (1.4, dict(yaw=-10.0, pitch=10.0, roll=0.0, drop=0.6, pel=(0.1, -0.6), hpitch=28.0, wind=8.0), 'in'),
                 (1.5, dict(pitch=12.0, hpitch=31.0), 'back'),
                 (1.9, dict(pitch=9.0, hpitch=24.0, wind=5.0, drop=0.7, lf=(-3.0, -5.6, -6.0, 0.0)), 'io'),
                 (2.12, dict(pitch=-6.0, drop=1.1, hpitch=0.0, pel=(0.2, -1.0), wind=0.0, lf=(-2.8, -4.0, -8.0, 1.0)), 'io'),
                 (2.4, dict(ST), 'io'), (3.0, dict(ST), 'io')])
    P2_W = [(0.0, ('G',), 'io'), (0.42, ('T', (1.6, 27.0, -6.6), (0.05, -0.55, -0.83)), 'out'), (0.6, P_PLANT, 'in'), (1.95, P_PLANT, 'io'),
            (2.15, ('T', (2.2, 19.0, -7.5), (-0.1, 0.4, -0.9)), 'out'), (2.4, ('G',), 'io')]

    def phase2(t):
        o = pose(P2_K, t)
        arm_to(o, *wpath(o, P2_W, t), left=1.0)
        return vis(o)
    a = A('phase2', 3.0)
    a.sample(phase2, 0.02)
    a.instruction(0.6, 'plant')
    a.instruction(1.4, 'roar')

    # ---------------------------------------------------------------- phase3 (33%; kneel 0.8, spin 1.4, roar 2.0): оседает на воткнутый
    # меч (низкая стойка), рывком выдёргивает и оборачивается на месте (стопы проворачиваются на носках), меч над головой, рёв; стойка к 3.2.
    # Поворот на 360° — как и прежде, кость body заканчивает на yaw стойки + 360 (тот же поворот).
    P3_K = Keys([(0.0, dict(ST, spin=0.0)),
                 (0.5, dict(lf=(-2.8, -4.6, -6.0, 1.2)), 'io'),
                 (0.8, dict(yaw=-10.0, pitch=-20.0, roll=3.0, drop=2.0, pel=(0.0, -1.6), hpitch=-20.0, lf=(-3.0, -6.0, -4.0, 0.0),
                            rf=(3.6, 3.6, -30.0, 0.0)), 'out'),
                 (1.3, dict(pitch=-17.0, drop=1.9, hpitch=-14.0), 'io'),
                 (1.45, dict(pitch=-4.0, drop=1.2, hpitch=0.0, spin=0.0, lf=(-3.0, -6.0, -4.0, 0.4), rf=(3.6, 3.6, -30.0, 0.4)), 'io'),
                 (1.9, dict(spin=360.0, pitch=6.0, drop=0.9, wind=6.0, lf=(-3.0, -6.0, -4.0, 0.0), rf=(3.6, 3.6, -30.0, 0.0)), 'io'),
                 (2.0, dict(pitch=12.0, hpitch=28.0, drop=0.7, wind=10.0), 'in'),
                 (2.1, dict(pitch=14.0, hpitch=31.0), 'back'),
                 (2.6, dict(pitch=11.0, hpitch=24.0, wind=6.0, drop=0.8, lf=(-3.0, -6.0, -4.0, 0.0), rf=(3.6, 3.6, -30.0, 0.0)), 'io'),
                 (2.85, dict(lf=(-2.8, -4.0, -6.0, 1.0), pel=(0.2, -0.8), wind=0.0, hpitch=0.0, pitch=-4.0), 'io'),
                 (3.0, dict(rf=(3.4, 2.5, -38.0, 0.0)), 'io'),
                 (3.2, dict(ST, spin=360.0), 'io')])
    P3_PLANT = ('W', (0.3, 15.6, -9.4), (0.0, -0.96, -0.28))
    OVER = ('T', (2.0, 32.0, -1.0), (0.1, 0.95, 0.3))
    P3_W = [(0.0, ('G',), 'io'), (0.8, P3_PLANT, 'out'), (1.4, P3_PLANT, 'io'), (1.52, ('T', (2.4, 22.0, -9.0), (0.0, 0.35, -0.94)), 'out'),
            (1.72, ('T', (3.6, 29.0, -7.0), (0.1, 0.8, -0.6)), 'io'), (1.95, OVER, 'io'), (2.6, OVER, 'io'), (3.2, ('G',), 'io')]

    class Spin:
        def __call__(self, t, name, default=0.0):
            v = P3_K(t, name, default)
            if name == 'yaw':
                return float(v) + P3_K.f(t, 'spin')
            if name in ('rf', 'lf'):
                ph = math.radians(P3_K.f(t, 'spin'))
                x, z, yw, lift = [float(q) for q in v]
                return np.array([x * math.cos(ph) + z * math.sin(ph), -x * math.sin(ph) + z * math.cos(ph), yw + math.degrees(ph), lift])
            return v

        def f(self, t, name, default=0.0):
            return float(self(t, name, default))
    SP = Spin()

    def phase3(t):
        o = pose(SP, t)
        arm_to(o, *wpath(o, P3_W, t), left=1.0)
        return vis(o)
    a = A('phase3', 3.2)
    a.sample(phase3, 0.02)
    a.instruction(0.8, 'kneel')
    a.instruction(1.4, 'spin')
    a.instruction(2.0, 'roar')

    # ---------------------------------------------------------------- spawn (6.5; look 1.0, rise 2.6, pull 4.0, salute 5.0): на колене
    # (позы ног — прежние), руки на воткнутом мече, поднимает голову; встаёт, перенося вес вперёд; выдёргивает меч с замахом вверх,
    # салют (клинок перед лицом, лицом к цели), шаг правой назад — стойка.
    KN_L = {'right_leg': [86.0, 0.0, 6.0], 'left_leg': [-86.0, 0.0, 0.0]}                    # прежнее колено (внутренние оси)
    SAL = ('T', (0.5, 26.0, -5.5), (0.0, 1.0, -0.05))
    SN_K = Keys([(0.0, dict(ST, yaw=0.0, pitch=-12.0, hpitch=-26.0, kn=1.0, lw=1.0, rf=(2.8, 0.0, 0.0, 0.0), lf=(-2.8, 0.0, 0.0, 0.0), drop=0.3)),
                 (1.0, dict(hpitch=-26.0), 'io'),
                 (2.4, dict(hpitch=4.0, pitch=-10.0), 'out'),
                 (2.6, dict(kn=1.0, pitch=-10.0), 'io'),
                 (3.2, dict(kn=0.35, pitch=-18.0, hpitch=-2.0, drop=1.2, pel=(0.0, -1.0)), 'io'),
                 (3.6, dict(kn=0.0, pitch=-6.0, drop=0.6, pel=(0.1, -0.4), rf=(3.0, 1.2, -20.0, 0.0), lf=(-2.8, -2.0, -6.0, 0.0)), 'out'),
                 (3.9, dict(pitch=-10.0, drop=1.0, yaw=-12.0), 'io'),
                 (4.4, dict(pitch=6.0, drop=0.3, yaw=-4.0, hpitch=6.0, wind=4.0), 'out'),
                 (4.6, dict(lw=1.0), 'io'), (4.8, dict(lw=0.0, larm=(4.0, 0.0, -6.0)), 'io'),
                 (5.0, dict(yaw=0.0, pitch=2.0, drop=0.25, hpitch=0.0, wind=0.0), 'in'),
                 (5.1, dict(pitch=3.0), 'back'),
                 (5.8, dict(pitch=1.0, lw=0.0, rf=(3.0, 1.2, -20.0, 0.0)), 'io'),
                 (6.05, dict(rf=(3.3, 2.0, -32.0, 1.2), lw=1.0, larm=(0.0, 0.0, 0.0)), 'io'),
                 (6.25, dict(rf=(3.4, 2.5, -38.0, 0.0), lf=(-2.6, -2.7, -8.0, 0.0)), 'io'),
                 (6.5, dict(ST), 'io')])
    SN_W = [(0.0, ('T', (0.3, 23.6, -7.6), LEAN_T[1]), 'io'), (2.6, ('T', (0.3, 23.6, -7.6), LEAN_T[1]), 'io'),
            (3.6, LEAN_W, 'io'), (3.9, LEAN_W, 'io'), (4.4, ('G',), 'out'), (5.0, SAL, 'in'), (5.8, SAL, 'io'), (6.5, ('G',), 'io')]

    def spawn(t):
        o = pose(SN_K, t, sway=0.6)
        kn = SN_K.f(t, 'kn')
        if kn > 0.001:                                      # колено: прежние углы ног и просадка, смешиваются с ногами на земле
            for leg, r in KN_L.items():
                cur = np.asarray(o[leg]['rot'], float)
                o[leg] = dict(o[leg], rot=list(cur * (1 - kn) + np.asarray(r) * kn))
            p = o['body']['pos']
            o['body']['pos'] = [p[0], p[1] * (1 - kn) - 6.2 * kn, p[2]]
        arm_to(o, *wpath(o, SN_W, t), left=SN_K.f(t, 'lw'))
        return vis(o)
    a = A('spawn', 6.5)
    a.sample(spawn, 0.04)
    a.instruction(1.0, 'look')
    a.instruction(2.6, 'rise')
    a.instruction(4.0, 'pull')
    a.instruction(5.0, 'salute')

    # ---------------------------------------------------------------- block_yield (3.2, держит; block 0.2, lower 1.2, speak 2.4): щит
    # рывком вверх, отдача удара (отшаг правой, корпус назад), держит; щит за спину, меч опускается остриём к земле, голова вниз.
    YE = dict(yaw=-10.0, pitch=-5.0, roll=0.0, tyaw=0.0, pel=(0.2, 0.4), drop=0.3, hpitch=-12.0, rf=(3.0, 1.6, -20.0, 0.0),
              lf=(-2.8, -1.4, -6.0, 0.0), lw=0.0, sw=0.0, larm=(4.0, 0.0, -5.0), lfore=10.0, wind=0.0)
    BY_K = Keys([(0.0, dict(ST, sw=0.0, sh=(-1.2, 17.5, -6.0), stilt=-10.0, syaw=-10.0)),
                 (0.1, dict(lw=0.0), 'io'),
                 (0.15, dict(sw=1.0, yaw=-30.0, pitch=-8.0, drop=1.1, hpitch=-4.0), 'out'),
                 (0.2, dict(pel=(0.3, 0.0)), 'io'),
                 (0.3, dict(pitch=2.0, pel=(0.4, 1.6), drop=1.3, sh=(-1.2, 16.5, -5.2), stilt=-4.0, rf=(3.5, 3.8, -38.0, 0.0)), 'out'),
                 (0.7, dict(pitch=-6.0, pel=(0.3, 1.0), drop=1.0, sh=(-1.2, 17.5, -6.0), stilt=-10.0), 'io'),
                 (0.9, dict(sw=1.0), 'io'),
                 (1.2, dict(yaw=-18.0, drop=0.7, hpitch=-6.0), 'io'),
                 (2.0, dict(sw=0.0, sh=(-1.2, 15.0, -6.0), stilt=0.0, rf=(3.0, 1.6, -20.0, 0.0)), 'io'),
                 (1.75, dict(rf=(3.3, 2.6, -28.0, 1.0)), 'io'),
                 (2.6, dict(YE), 'io'),
                 (3.2, dict(YE), 'io')])
    BY_W = [(0.0, ('G',), 'io'), (1.2, ('G',), 'io'), (2.6, DOWN_T, 'io'), (3.2, DOWN_T, 'io')]

    def yield_(t):
        o = pose(BY_K, t)
        shield(o, BY_K, t)
        arm_to(o, *wpath(o, BY_W, t), left=BY_K.f(t, 'lw'))
        return vis(o, shield_hand=0.1 < t < 2.1)
    a = A('block_yield', 3.2, 'hold')
    a.sample(yield_, 0.02)
    a.instruction(0.2, 'block')
    a.instruction(1.2, 'lower')
    a.instruction(2.4, 'speak')

    # ---------------------------------------------------------------- мирный NPC: опирается на воткнутый меч, вес гуляет, дыхание 4 с
    NPC = dict(yaw=-8.0, pitch=-4.0, roll=0.0, tyaw=0.0, pel=(0.2, 0.0), drop=0.3, hpitch=2.0, rf=(3.0, 1.0, -22.0, 0.0),
               lf=(-3.0, -1.0, -10.0, 0.0), lw=1.0, larm=(0.0, 0.0, 0.0), lfore=0.0, wind=0.0)

    def npc_k(t):
        br = math.sin(TAU * t / 4.0)
        sw = math.sin(TAU * t / 4.0 + 1.3)
        return dict(NPC, drop=NPC['drop'] - 0.1 * br, pitch=NPC['pitch'] - 0.6 * br, tpitch=0.6 * br, pel=(0.2 + 0.3 * sw, 0.03 * br),
                    yaw=NPC['yaw'] + 1.0 * sw, hpitch=NPC['hpitch'] + 0.6 * br)
    NK = FnK(npc_k)

    def npc(t):
        o = pose(NK, t, sway=0.7, period=4.0)
        arm_to(o, *wp(o, LEAN_W), left=1.0)
        return vis(o)
    A('npc_idle', 4.0, True).sample(npc, 0.1)

    TN_K = Keys([(0.0, dict(YE)), (0.5, dict(lw=0.3), 'io'), (1.2, dict(npc_k(0.0)), 'io')])
    TN_W = [(0.0, DOWN_T, 'io'), (1.2, LEAN_W, 'io')]

    def to_npc(t):
        o = pose(TN_K, t, sway=0.7)
        arm_to(o, *wpath(o, TN_W, t), left=TN_K.f(t, 'lw'))
        return vis(o)
    A('to_npc', 1.2, 'hold').sample(to_npc, 0.04)

    # ---------------------------------------------------------------- shield_wall (2.0; shield_draw 0.15, slam 1.0): щит со спины над
    # головой (корпус назад, вес назад), с размаху в землю с шагом левой и просадкой, меч поднят; стойка к 2.0
    SW_K = Keys([(0.0, dict(ST, sw=0.0, sh=(-1.2, 15.0, -6.0), stilt=0.0)),
                 (0.15, dict(lw=0.0), 'io'),
                 (0.4, dict(sw=1.0), 'io'),
                 (0.6, dict(yaw=-14.0, pitch=9.0, drop=0.15, pel=(0.3, 1.0), hpitch=10.0, sh=(-1.5, 22.0, -5.5), stilt=-16.0, wind=3.0), 'out'),
                 (0.85, dict(pitch=10.0, sh=(-1.5, 22.5, -5.2), stilt=-18.0, lf=(-2.9, -4.2, -6.0, 1.4)), 'lin'),
                 (1.0, dict(yaw=-6.0, pitch=-14.0, drop=2.0, pel=(0.0, -1.2), hpitch=0.0, sh=(-0.8, 12.6, -6.4), stilt=8.0, wind=0.0,
                            lf=(-3.3, -5.4, -5.0, 0.0), rf=(3.9, 3.2, -26.0, 0.0)), 'in'),
                 (1.12, dict(pitch=-16.0, drop=2.05), 'back'),
                 (1.6, dict(pitch=-12.0, drop=1.85, sw=1.0, lf=(-3.3, -5.4, -5.0, 0.0), rf=(3.9, 3.2, -26.0, 0.0)), 'io'),
                 (1.75, dict(lf=(-2.9, -4.0, -6.0, 1.2), pel=(0.2, -0.6), drop=1.0), 'io'),
                 (1.85, dict(sw=0.0, lw=0.0), 'io'),
                 (2.0, dict(ST, sw=0.0, sh=(-1.2, 15.0, -6.0), stilt=0.0), 'io')])
    SWL_W = [(0.0, ('G',), 'io'), (0.6, ('T', (4.6, 24.0, -3.0), (0.15, 0.95, -0.25)), 'out'), (1.0, HOLD_SW, 'in'), (1.6, HOLD_SW, 'io'),
             (2.0, ('G',), 'io')]

    def shieldwall(t):
        o = pose(SW_K, t)
        shield(o, SW_K, t)
        arm_to(o, *wpath(o, SWL_W, t), left=SW_K.f(t, 'lw'))
        return vis(o, shield_hand=0.15 < t < 1.9)
    a = A('shield_wall', 2.0)
    a.sample(shieldwall, 0.02)
    a.instruction(0.15, 'shield_draw')
    a.instruction(1.0, 'slam')

    # ---------------------------------------------------------------- finisher (2.5; impale 0.4, raise 0.8, throw 1.7, slam 2.0, kill 2.3):
    # выпад с шагом левой (таз вперёд и вниз, плечи к цели), поднимает жертву на клинке, корпус назад — над головой, бросает к ногам
    # ударом вниз с просадкой, стойка. Клинок всё время в груди жертвы (MartinMath.finisherHold — как и прежде).
    FN_K = Keys([(0.0, dict(ST)),
                 (0.3, dict(lf=(-2.8, -5.0, -6.0, 1.4)), 'io'),
                 (0.4, dict(yaw=-6.0, pitch=-12.0, roll=2.0, drop=1.5, pel=(-0.2, -3.0), hpitch=-6.0, lf=(-3.0, -7.4, -4.0, 0.0),
                            rf=(3.4, 2.0, -30.0, 0.0)), 'in'),
                 (0.5, dict(pitch=-13.0, drop=1.6), 'back'),
                 (0.8, dict(pitch=-6.0, drop=1.2, hpitch=4.0), 'io'),
                 (1.5, dict(yaw=-4.0, pitch=10.0, drop=0.6, pel=(-0.1, -2.4), hpitch=22.0, wind=6.0), 'io'),
                 (1.7, dict(pitch=11.0, hpitch=24.0, wind=6.0, lf=(-3.0, -7.4, -4.0, 0.0)), 'io'),
                 (2.0, dict(pitch=-20.0, drop=1.9, pel=(-0.2, -3.2), hpitch=-10.0, wind=0.0), 'in'),
                 (2.08, dict(pitch=-21.0, drop=1.95), 'back'),
                 (2.2, dict(pitch=-18.0, drop=1.8, lf=(-3.0, -7.4, -4.0, 0.0), rf=(3.4, 2.0, -30.0, 0.0)), 'io'),
                 (2.36, dict(lf=(-2.8, -4.0, -6.0, 1.0), rf=(3.4, 2.5, -38.0, 0.0), pel=(0.1, -1.0), drop=0.9, pitch=-6.0, hpitch=0.0), 'io'),
                 (2.5, dict(ST), 'io')])
    FN_H = [(0.0, ('G',), 'io'), (0.4, ('T', (2.5, 14.0, -11.0), GUARD_T[1]), 'in'), (0.8, ('T', (2.5, 19.0, -9.5), GUARD_T[1]), 'io'),
            (1.5, ('T', (2.5, 30.0, -6.0), GUARD_T[1]), 'io'), (1.7, ('T', (2.5, 30.0, -6.0), GUARD_T[1]), 'io'),
            (2.0, ('T', (1.0, 13.0, -10.0), GUARD_T[1]), 'in'), (2.2, ('T', (1.0, 13.0, -10.0), GUARD_T[1]), 'io'), (2.5, ('G',), 'io')]
    FIN17 = [None]

    def finisher(t):
        o = pose(FN_K, t)
        hw, _ = wpath(o, FN_H, t)
        fh = G.finisher_hold(t * 20)
        chest = np.array([0.0, (fh[1] + 1.2) * 8.0, -fh[0] * 8.0])        # мир модели: 1 бл. = 8 ед. (модель ×2)
        aim = _unit(chest - hw)
        Mt, _ = G.fk(m, o, 'torso')
        dn = Mt @ _unit((0.0, -0.5, -0.87))
        gd = wp(o, ('G',))[1]
        if t < 0.25:
            d = G.lerp_dir(gd, aim, B.ease(t / 0.25, 'io'))
        elif t <= 1.7:
            d = aim
            if abs(t - 1.7) < 0.011:
                FIN17[0] = aim
        elif t <= 2.0:
            d = G.lerp_dir(FIN17[0] if FIN17[0] is not None else aim, dn, B.ease((t - 1.7) / 0.3, 'in'))
        elif t <= 2.2:
            d = dn
        else:
            d = G.lerp_dir(dn, gd, B.ease((t - 2.2) / 0.3, 'io'))
        arm_to(o, hw, d, left=1.0)
        return vis(o)
    a = A('finisher', 2.5)
    a.sample(finisher, 0.02)
    a.instruction(0.4, 'impale')
    a.instruction(0.8, 'raise')
    a.instruction(1.7, 'throw')
    a.instruction(2.0, 'slam')
    a.instruction(2.3, 'kill')
