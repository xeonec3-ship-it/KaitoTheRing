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
