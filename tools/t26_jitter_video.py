#!/usr/bin/env python3
"""
Ролик проверки рывков косы Главы Культа: docs/media/video/t26_jitter_check.mp4 — крупно коса, 60 кадров/с, замедление ×0.5:
покой → ходьба → «Удар сверху и боковой взмах» → «Двойной взмах» → покой (переходы как в игре: анимации начинаются и кончаются
в позе хвата, код держит её вне анимаций). Рендер — tools/boss_video.py (тот же движок, двойной поворот кисти GeckoLib).
  python3 tools/t26_jitter_video.py [--three путь/three.min.js]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boss_video as BV  # noqa: E402

FPS, SLOW = 60, 0.5
SEQ = [('~hold', 1.0, 'Покой — поза хвата'), ('~walk', 1.88, 'Ходьба'),
       ('scythe_downslash_sideslash', None, 'Удар сверху и боковой взмах'),
       ('scythe_dagger_double_horizontal', None, 'Двойной взмах: коса и кинжал'), ('~hold', 1.0, 'Покой')]


def reel(T):
    r = BV.Reel(T.title + ' · проверка рывков косы (60 к/с, ×0.5)')
    dt = SLOW / FPS
    for anim, dur, cap in SEQ:
        L = dur if dur is not None else T.anim_len(anim)
        n = int(round(L / dt))
        r.mark('%s (`%s`)' % (cap, anim))

        def fr(i, anim=anim, cap=cap, L=L):
            t = i * dt
            if anim == '~walk':
                t %= T.anim_len('~walk')
            a = T.boss(anim, min(t, L) if not anim.startswith('~') else t, ry=0)
            return {'actors': [a], 'rawcam': True,
                    'cam': {'yaw': 38, 'pitch': 12, 'dist': 1.75 * T.h, 'tx': 0, 'ty': T.h * 0.45, 'tz': -4, 'fov': 30},
                    'cap': cap, 'sub': '%s · %.2f с · 60 к/с, замедление ×0.5' % (anim, min(t, L))}
        r.add(n, fr)
    return r


def main():
    args = sys.argv[1:]
    three = args[args.index('--three') + 1] if '--three' in args else None
    BV.FPS = FPS                                    # кадры 60/с (время анимаций идёт ×0.5)
    T = BV.Tyros()
    out = os.path.join(BV.OUT, 't26_jitter_check.mp4')
    BV.render('tyros', reel(T), out, three, [{'k': 'boss'}], crf=18)


if __name__ == '__main__':
    main()
