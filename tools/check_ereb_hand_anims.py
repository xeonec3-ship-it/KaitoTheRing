#!/usr/bin/env python3
"""
Покадровая проверка анимаций T31 «Эреб, Длань Лжи» (шаг 0.1 с) — то, что владелец ловил у других боссов:
  1) стыки: начало/конец каждой анимации = поза покоя (или поза соседней по цепочке CHAIN) — без скачков между анимациями;
  2) рывки: поворот кости за 0.1 с не больше порога (кроме заявленных ударов — порог выше);
  3) рука и рапира не проходят сквозь тело (точки брусков ghost_* и клинка внутри брусков тела, головы, рук, ног);
  4) накидка не входит в ноги и тело (ткань назад/вниз);
  5) без выворотов: пределы поворота рук, кисти, головы;
  6) удары ВПЕРЁД: на событиях hit — острие перед Эребом, slam/grab — ладонь перед ним; касты второй партии (throw, mirror) — «Длань»
     перед ним, выпуск (release, mirror) — ладонь призрачной руки перед ним;
  7) ничего не в земле: тело, накидка, полы, рука (y ≥ −0.6 ед.; удар slam — ладонь до −1.5); рука не входит в маску.
Запуск: python3 tools/check_ereb_hand_anims.py [--quiet]. Код выхода 1 — есть ошибки.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ereb_hand_fk as F           # noqa: E402
import gen_ereb_hand_anims as AN   # noqa: E402

BODY_SOLID = ('torso', 'head', 'right_arm', 'left_arm', 'right_leg', 'left_leg')
STEP_MAX = 62          # град. за 0.1 с — плавно
STEP_HIT = 95          # у ударов (slam, выпад) — допустимо быстрее
STEP_STRIKE = 300      # в окне самого удара (hit/slam ± 0.2 с) — скорость эталона Epic Fight (21.11)
LIMITS = {'right_arm': ((-185, 40), (-60, 70), (-40, 75)), 'left_arm': ((-185, 40), (-70, 60), (-110, 40)),
          'head': ((-40, 30), (-45, 45), (-12, 12)), 'bipedHandRight': ((-60, 100), (-60, 60), (-30, 30))}


def pose_of(an, name, t):
    return F.sample(an[name], t)


def dict_pose(p):
    """Поза-словарь генератора (IDLE0) → формат F.sample."""
    o = {}
    for k, v in p.items():
        if k.endswith('_pos'):
            o.setdefault(k[:-4], [[0, 0, 0], [0, 0, 0], [1, 1, 1]])[1] = v
        elif k.endswith('_scale'):
            o.setdefault(k[:-6], [[0, 0, 0], [0, 0, 0], [1, 1, 1]])[2] = v
        else:
            o.setdefault(k, [[0, 0, 0], [0, 0, 0], [1, 1, 1]])[0] = v
    return o


def diff(a, b):
    m = 0.0
    for bn in set(a) | set(b):
        ra = a.get(bn, ([0, 0, 0], [0, 0, 0], [1, 1, 1]))
        rb = b.get(bn, ([0, 0, 0], [0, 0, 0], [1, 1, 1]))
        for i in range(3):
            m = max(m, abs(ra[0][i] - rb[0][i]), abs(ra[1][i] - rb[1][i]) * 4, abs(ra[2][i] - rb[2][i]) * 40)
    return m


def main():
    quiet = '--quiet' in sys.argv
    an = json.load(open(os.path.join(F.A, 'animations', 'entity', 'ereb_hand.animation.json'), encoding='utf-8'))['animations']
    model = F.Model()
    idle0 = dict_pose(AN.IDLE0)
    if 'bipedHandRight' in idle0:            # 21.11: в файле ключ кисти — половина видимого поворота (anim_cloth.visible_hand)
        import anim_cloth
        idle0['bipedHandRight'][0] = anim_cloth.V(idle0['bipedHandRight'][0])
    errors, notes = [], []
    names = sorted(k for k in an if k.startswith('ereb_hand_'))
    for name in names:
        a = an[name]
        L = a['animation_length']
        loop = a.get('loop') is True
        events = {round(float(t), 2): v for t, v in a.get('timeline', {}).items()}
        ts = [round(i * 0.1, 2) for i in range(int(L / 0.1 + 1e-6) + 1)]
        if ts[-1] < L:
            ts.append(L)
        for t in events:
            if t not in ts:
                ts.append(t)
        ts.sort()
        # 1) стыки
        p0, p1 = pose_of(an, name, 0), pose_of(an, name, L)
        src, dst = AN.CHAIN.get(name, (None, None))
        if loop:
            if diff(p0, p1) > 0.5:
                errors.append('%s: петля не сходится (%.1f)' % (name, diff(p0, p1)))
        else:
            for which, ref, p in (('начало', src, p0), ('конец', dst, p1)):
                if ref in ('hidden', 'maskless'):
                    continue
                refp = idle0 if ref is None else pose_of(an, ref, 0)
                d = diff(p, refp)
                if d > 0.6:
                    errors.append('%s: %s не совпадает с %s (расхождение %.1f°)' % (name, which, ref or 'покоем', d))
        prev = None
        worst_step = 0
        for t in ts:
            pose = pose_of(an, name, t)
            # 2) рывки
            if prev is not None:
                dt = t - prev[0]
                st = 0
                for bn, (r, p, s) in pose.items():
                    r0 = prev[1].get(bn, ([0, 0, 0],))[0]
                    st = max(st, max(abs(r[i] - r0[i]) for i in range(3)) * (0.1 / max(dt, 1e-3)))
                worst_step = max(worst_step, st)
                fast = any(abs(t - te) <= 0.25 and ev in ('hit', 'slam', 'phase', 'crack', 'tear', 'squeeze', 'grab', 'stagger', 'snap', 'break', 'release', 'shatter', 'grip',
                                                          'throw', 'leap', 'land', 'kneel', 'wave', 'emerge')
                           for te, ev in events.items())
                # окно самого удара (hit/slam ± 0.2 с) — до 300°/0.1 с: эталон Epic Fight (владелец 21.11), удар 0.08–0.24 с, пик 1750–2500°/с
                strike = any(abs(t - te) <= 0.2 and ev in ('hit', 'slam') for te, ev in events.items())
                if st > (STEP_STRIKE if strike else STEP_HIT if fast else STEP_MAX):
                    errors.append('%s t=%.2f: рывок %.0f° за 0.1 с' % (name, t, st))
            prev = (t, pose)
            # 5) пределы
            for bn, lim in LIMITS.items():
                r = pose.get(bn, ([0, 0, 0],))[0]
                for i in range(3):
                    if not (lim[i][0] <= r[i] <= lim[i][1]):
                        errors.append('%s t=%.2f: %s ось %s = %.0f° вне %s' % (name, t, bn, 'xyz'[i], r[i], lim[i]))
            W = model.world(pose)
            # 3) рука сквозь тело
            gscale = pose.get('ghost_hand', ([0, 0, 0], [0, 0, 0], [1, 1, 1]))[2][0]
            sol = model.solids(W, BODY_SOLID, 0.3)
            if gscale > 0.15:
                hit_parts = set()
                for gb in AN.GHOST:
                    for sb in model.hits(sol, model.points(W, gb, 3)):
                        hit_parts.add('%s→%s' % (gb, sb))
                if hit_parts:
                    errors.append('%s t=%.2f: рука в теле: %s' % (name, t, ', '.join(sorted(hit_parts))))
                hm = model.hits(model.solids(W, ('mask',), 0.0), [p for gb in AN.GHOST for p in model.points(W, gb, 3)])
                if hm:
                    errors.append('%s t=%.2f: рука в маске' % (name, t))
            # 7) земля (вторая партия, AN.SPELLS2): ничего не ниже y = −0.6 ед. (у старых анимаций допущено принятое «приседание» —
            #    ступни на 1–2 ед. в земле при опущенном корпусе, их не трогаем)
            low = []
            for bn in ('torso', 'head', 'right_arm', 'left_arm', 'cape', 'cape_mid', 'cape_low', 'coat_front_r', 'coat_front_l', 'coat_back_r',
                       'coat_back_l', 'right_leg', 'left_leg') + (tuple(AN.GHOST) if gscale > 0.15 else ()):
                if name in AN.SPELLS2 and bn in model.bones and model.cubes(bn):
                    y = min(p[1] for p in model.points(W, bn, 2))
                    if y < -0.6:
                        low.append('%s %.1f' % (bn, y))
            if low:
                errors.append('%s t=%.2f: в земле: %s' % (name, t, ', '.join(low)))
            # рапира сквозь тело (клинок от гарды к острию; правая рука держит — её не считаем)
            blade = F.rapier_points(W, model, 10)[2:]
            hit_parts = model.hits(model.solids(W, ('torso', 'head', 'mask', 'left_arm', 'right_leg', 'left_leg', 'cape', 'cape_mid', 'cape_low'), 0.0), blade)
            if blade[-1][1] < -0.6:
                errors.append('%s t=%.2f: острие рапиры в земле (y=%.1f)' % (name, t, blade[-1][1]))
            if hit_parts:
                errors.append('%s t=%.2f: клинок в %s' % (name, t, ', '.join(sorted(hit_parts))))
            # 4) накидка
            cp = model.points(W, 'cape', 3) + model.points(W, 'cape_mid', 3) + model.points(W, 'cape_low', 3)
            bad = model.hits(model.solids(W, ('right_leg', 'left_leg', 'torso'), 0.3), cp)
            if bad:
                errors.append('%s t=%.2f: накидка в %s' % (name, t, ', '.join(sorted(bad))))
            # 6) направление на событиях
            ev = events.get(round(t, 2))
            if ev in ('hit', 'stab'):
                tip = F.rapier_points(W, model, 1)[-1]
                if tip[2] > -12:
                    errors.append('%s t=%.2f: удар не вперёд (острие z=%.1f)' % (name, t, tip[2]))
                notes.append('%s %s %.2f: острие (x %.1f, y %.1f, z %.1f)' % (name, ev, t, *tip))
            if ev in ('throw', 'mirror'):
                lh = model.point(W, 'left_arm', [6, 12.5, 0])
                if lh[2] > -6:
                    errors.append('%s t=%.2f: «Длань» не вперёд (z=%.1f)' % (name, t, lh[2]))
                notes.append('%s %s %.2f: «Длань» (x %.1f, y %.1f, z %.1f)' % (name, ev, t, *lh))
            if ev in ('release', 'mirror', 'emerge', 'wave') and name.endswith(('swarm_of_lies', 'traitor_reflection', 'false_dawn')):
                pc = model.point(W, 'ghost_palm', [-15.5, 35.5, 4.25])
                if ev in ('release', 'mirror') and pc[2] > -8:
                    errors.append('%s t=%.2f: ладонь не впереди (z=%.1f)' % (name, t, pc[2]))
                notes.append('%s %s %.2f: ладонь (x %.1f, y %.1f, z %.1f)' % (name, ev, t, *pc))
            if ev in ('slam', 'grab', 'squeeze', 'snap'):
                pc = model.point(W, 'ghost_palm', [-15.5, 35.5, 4.25])
                if ev in ('slam', 'grab') and pc[2] > -10:
                    errors.append('%s t=%.2f: ладонь не впереди (z=%.1f)' % (name, t, pc[2]))
                notes.append('%s %s %.2f: ладонь (x %.1f, y %.1f, z %.1f)' % (name, ev, t, *pc))
        notes.append('%s: L=%.2f, макс. поворот за 0.1 с = %.0f°' % (name, L, worst_step))
    # точка удержания схваченного игрока
    W = model.world(pose_of(an, 'ereb_hand_grab_hold', 0))
    pc = model.point(W, 'ghost_palm', [-15.5, 35.5, 3.0])
    notes.append('удержание: середина ладони спереди (x %.1f, y %.1f, z %.1f) ед. = (%.2f, %.2f, %.2f) бл.' % (*pc, *(pc / 16)))
    if not quiet:
        print('\n'.join(notes))
    print('\nОШИБОК: %d' % len(errors))
    print('\n'.join(errors[:200]))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
