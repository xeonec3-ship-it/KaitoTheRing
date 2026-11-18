#!/usr/bin/env python3
"""
Генератор анимаций игрока для заклинаний pohsmp_core (формат GeckoLib 1.8.0, который читает PlayerAnimator).

Файл кладётся в пространство имён Iron's (assets/irons_spellbooks/player_animation/), поэтому в заклинании
достаточно new AnimationHolder("<имя>", true) — Iron's сам допишет irons_spellbooks: к имени, в любой версии.

Позы рук задаются не углами, а направлениями: куда смотрит рука от плеча (arm) и куда смотрит посох в руке
(staff). Углы считает solve(). Оси модели: +X — влево от игрока, +Y — вверх, +Z — вперёд.
Перевод в углы Bedrock/GeckoLib: x — как есть (минус = рука вперёд и вверх), y и z — с обратным знаком
(z плюс у правой руки = рука в сторону вправо, как в cast_t_pose у Iron's).

Запуск:  python3 tools/gen_player_anims.py
"""
import json
import math
import os

import numpy as np

OUT = os.path.join(os.path.dirname(__file__), '..', 'src', 'main', 'resources', 'assets',
                   'irons_spellbooks', 'player_animation', 'pohsmp_core_casting.json')

EASE = 'easeInOutSine'


def _n(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def solve(arm, staff):
    """Направление руки + направление посоха -> углы Bedrock [x, y, z] в градусах."""
    y = -_n(arm)                      # локальная ось +Y руки смотрит от кисти к плечу
    s = np.asarray(staff, dtype=float)
    z = _n(s - np.dot(s, y) * y)      # предмет в руке торчит по локальной +Z
    x = np.cross(y, z)
    m = np.column_stack([x, y, z])    # m = Rz(c) Ry(b) Rx(a)  (порядок ModelPart: X, потом Y, потом Z)
    b = math.asin(max(-1.0, min(1.0, -m[2, 0])))
    if abs(m[2, 0]) < 0.9999:
        a = math.atan2(m[2, 1], m[2, 2])
        c = math.atan2(m[1, 0], m[0, 0])
    else:
        a = math.atan2(-m[1, 2], m[1, 1])
        c = 0.0
    return [round(math.degrees(a), 2), round(-math.degrees(b), 2), round(-math.degrees(c), 2)]


def _closest(prev, v):
    """Та же ориентация, записанная углами, ближайшими к prev: чтобы рука не крутилась длинным путём."""
    a, b, c = v
    best = None
    for base in ([a, b, c], [a + 180, -180 - b, c - 180]):
        cand = [x + 360 * round((p - x) / 360) for x, p in zip(base, prev)]
        d = sum(abs(x - p) for x, p in zip(cand, prev))
        if best is None or d < best[0]:
            best = (d, cand)
    return best[1]


def track(keys, ease=EASE, rotation=True):
    """keys: [(время, [x, y, z]), ...] -> канал GeckoLib."""
    if rotation:
        fixed, prev = [], None
        for t, v in keys:
            v = list(v) if prev is None else _closest(prev, v)
            fixed.append((t, v))
            prev = v
        keys = fixed
    out = {}
    for i, (t, v) in enumerate(keys):
        k = {'vector': [round(float(a), 2) for a in v]}
        if i:
            k['easing'] = ease
        out['%.4g' % t if t % 1 else '%.1f' % t] = k
    return out


def sway(t0, t1, period, amp, base, axis=0):
    """Медленное покачивание вокруг base между t0 и t1."""
    keys, t, sign = [], t0, 1
    while t < t1 - 1e-6:
        v = list(base)
        v[axis] += amp * sign
        keys.append((t, v))
        t += period / 2
        sign = -sign
    keys.append((t1, list(base)))
    return keys


# ---------------------------------------------------------------- Низвержение
# Каст 25 с (DownfallSpell.CAST = 500 тиков). Опорные моменты заклинания:
#   5 с — рёв, 10 с — открывается разлом, 15 с — от посоха к разлому тянется золотая нить,
#   20 с — заряд Хранителя, 24 с — врата.
# Хореография по присланному видео: рука к сердцу -> взмах посохом снизу через сторону -> посох вверх ->
# посох поперёк груди двумя руками; дальше держим, на 15 с поднимаем посох над головой и держим до конца.

REST = [0, 0, 0]

R_HEART = solve(arm=(0.62, -0.55, 0.56), staff=(-0.25, 0.85, 0.45))     # кисть у сердца, посох на плече
R_LOW = solve(arm=(0.45, -0.85, 0.3), staff=(0.55, -0.45, 0.7))         # замах: посох низко слева
R_ARC = solve(arm=(-0.85, 0.05, 0.5), staff=(-0.35, 0.75, 0.55))        # дуга: рука в сторону вправо
R_HIGH = solve(arm=(-0.25, 0.5, 0.83), staff=(-0.1, 0.86, -0.5))        # посох высоко над головой
R_PRESENT = solve(arm=(0.22, -0.42, 0.88), staff=(1, 0.04, 0.05))       # посох поперёк груди
R_LIFT = solve(arm=(-0.12, 0.55, 0.83), staff=(0.02, 0.83, -0.55))      # 15 с: посох вверх, нить к разлому
R_STRAIN = solve(arm=(-0.08, 0.68, 0.73), staff=(0.02, 0.73, -0.68))     # 20 с: тянемся ещё выше
R_THRUST = solve(arm=(-0.1, 0.25, 0.96), staff=(-0.05, 0.97, -0.2))     # 24 с: посох вперёд, к разлому

L_HEART = solve(arm=(0.12, -0.97, 0.18), staff=(0, 0, 1))
L_LOW = solve(arm=(0.35, -0.9, -0.15), staff=(0, 0, 1))
L_HIGH = solve(arm=(0.55, 0.45, 0.7), staff=(0, 0.7, 0.7))              # левая рука раскрыта вверх-в сторону
L_PRESENT = solve(arm=(-0.32, -0.42, 0.85), staff=(0, 0.5, 0.86))       # держит другой конец посоха
L_LIFT = solve(arm=(0.75, 0.2, 0.62), staff=(0, 0.8, 0.6))              # ладонь раскрыта в сторону
L_STRAIN = solve(arm=(0.8, 0.35, 0.48), staff=(0, 0.8, 0.6))
L_THRUST = solve(arm=(0.6, -0.3, 0.74), staff=(0, 0.6, 0.8))


def downfall_cast():
    L = 25.0
    ra = [(0.0, REST), (0.7, R_HEART), (1.6, R_HEART), (2.05, R_LOW), (2.5, R_ARC), (3.0, R_HIGH),
          (3.8, R_PRESENT)]
    ra += sway(3.8, 14.4, 2.4, 3, R_PRESENT)
    ra += [(15.0, R_LIFT)] + sway(15.0, 19.6, 1.6, 2.5, R_LIFT)[1:]
    ra += [(20.0, R_STRAIN)] + sway(20.0, 23.6, 0.6, 1.5, R_STRAIN)[1:]   # дрожь от напряжения
    ra += [(24.2, R_THRUST), (L, R_THRUST)]

    la = [(0.0, REST), (0.7, L_HEART), (1.6, L_HEART), (2.05, L_LOW), (2.5, L_HEART), (3.0, L_HIGH),
          (3.8, L_PRESENT)]
    la += sway(3.8, 14.4, 2.4, 3, L_PRESENT)
    la += [(15.0, L_LIFT)] + sway(15.0, 19.6, 1.6, 2.5, L_LIFT)[1:]
    la += [(20.0, L_STRAIN)] + sway(20.0, 23.6, 0.6, 1.5, L_STRAIN)[1:]
    la += [(24.2, L_THRUST), (L, L_THRUST)]

    # торс: x плюс — наклон вперёд, y плюс — поворот вправо
    torso = [(0.0, REST), (0.7, [8, 0, 0]), (1.6, [8, 0, 0]), (2.05, [10, -28, 0]), (2.5, [-4, 22, 0]),
             (3.0, [-8, 5, 0]), (3.8, [2, 0, 0])]
    torso += sway(3.8, 14.4, 2.4, 2, [2, 0, 0])
    torso += [(15.0, [-6, 0, 0]), (20.0, [-9, 0, 0]), (23.6, [-9, 0, 0]), (24.2, [6, 0, 0]), (L, [6, 0, 0])]

    # голова: x плюс — взгляд вниз
    head = [(0.0, REST), (0.7, [16, 0, 0]), (1.6, [16, 0, 0]), (2.05, [10, -20, 0]), (2.5, [-5, 15, 0]),
            (3.0, [-22, 0, 0]), (3.8, [0, 0, 0]), (14.4, [0, 0, 0]), (15.0, [-25, 0, 0]), (20.0, [-30, 0, 0]),
            (23.6, [-30, 0, 0]), (24.2, [-5, 0, 0]), (L, [-5, 0, 0])]

    # руки чуть приподнимаются в плечах, когда тянутся вверх (смещение в пикселях)
    rpos = [(0.0, REST), (3.0, [0, 1.5, 0]), (3.8, REST), (14.4, REST), (15.0, [0, 1.5, 0]), (20.0, [0, 2.5, 0]),
            (23.6, [0, 2.5, 0]), (24.2, [0, 0.5, -1]), (L, [0, 0.5, -1])]

    return {
        'loop': 'hold_on_last_frame',
        'animation_length': L,
        'bones': {
            'right_arm': {'rotation': track(ra), 'position': track(rpos, rotation=False)},
            'left_arm': {'rotation': track(la), 'position': track(rpos, rotation=False)},
            'torso': {'rotation': track(torso)},
            'head': {'rotation': track(head)},
        },
    }


def downfall_finish():
    """После каста: резкий толчок посохом вперёд и возврат в покой."""
    L = 1.4
    ra = [(0.0, R_THRUST), (0.15, solve(arm=(-0.08, 0.1, 0.99), staff=(-0.05, 0.99, -0.1))), (0.45, R_THRUST),
          (L, REST)]
    la = [(0.0, L_THRUST), (0.15, L_THRUST), (L, REST)]
    torso = [(0.0, [6, 0, 0]), (0.15, [12, 0, 0]), (0.45, [6, 0, 0]), (L, REST)]
    head = [(0.0, [-5, 0, 0]), (L, REST)]
    return {
        'animation_length': L,
        'bones': {
            'right_arm': {'rotation': track(ra)},
            'left_arm': {'rotation': track(la)},
            'torso': {'rotation': track(torso)},
            'head': {'rotation': track(head)},
        },
    }


ANIMS = {
    'pohsmp_downfall_cast': downfall_cast,
    'pohsmp_downfall_finish': downfall_finish,
}


def main():
    data = {'format_version': '1.8.0', 'animations': {k: f() for k, f in ANIMS.items()}}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print('wrote', os.path.normpath(OUT), '—', ', '.join(ANIMS))
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, 'anim_preview.template.html'), encoding='utf-8') as fh:
        page = fh.read().replace('/*ANIMS*/null', json.dumps(data, ensure_ascii=False))
    with open(os.path.join(here, 'anim_preview.html'), 'w', encoding='utf-8') as fh:
        fh.write(page)
    print('wrote tools/anim_preview.html')


if __name__ == '__main__':
    main()
