#!/usr/bin/env python3
"""
T32 «Сломать блок»: метрики стиля Epic Fight (tools/anim_style_check.py — те же метрики и пороги эталона) по guard_break шести боссов.
  python3 tools/guard_break_check.py [martin aris irina ereb ereb_hand cult_leader] [-v]
Точка удара («остриё») у каждого своя — то, что бьёт в блок: навершие меча Мартина, боёк молота Ариса, крюк посоха Ирины,
острие рапиры Эреба и Длани, древко косы Главы (удар древком). Время приводится к росту игрока (÷√роста, как у Мартина).
Тела боссов на каркасе мага Iron's считаются прямой кинематикой готового JSON (anim_check: как превью/GeckoLib).
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import anim_style_check as C  # noqa: E402

A = C.A
# босс: (анимация, класс эталона, рост относительно игрока (нога босса / 0.75 бл.))
BOSSES = {
    'martin': ('martin_guard_break', 'thrust', 2.0),
    'aris': ('animation.aris.guard_break', 'heavy', None),
    'irina': ('irina_guard_break', 'heavy', None),
    'ereb': ('ereb_guard_break', 'thrust', None),
    'ereb_hand': ('ereb_hand_guard_break', 'thrust', None),
    'cult_leader': ('cult_leader_guard_break', 'thrust', None),
}


# ---------------------------------------------------------------- Мартин: модель генератора (как anim_style_check.MartinRig)
def martin_sig(name):
    rig = C.MartinRig()
    sig0, L = rig.signals(name)
    G, m = rig.G, rig.m
    piv = m.bones['sword'].pivot

    def sig(t):
        s = sig0(t)
        p = rig.AU.pose_at(rig.an[name], t)
        Ms, os_ = G.fk(m, p, 'sword')
        s['tool'] = (Ms @ (piv + [0, 2.0, 0]) + os_) / rig.L          # над хватом
        s['tip'] = (Ms @ (piv + [0, -6.0, 0]) + os_) / rig.L          # навершие
        return s
    return sig, L, rig.events(name)


# ---------------------------------------------------------------- боссы на JSON-кинематике (anim_check.Model; x — влево → переворачиваем)
def json_sig(boss, name):
    import guard_break_lib as GL
    M = GL.model(boss)
    an = M.anims[name]
    L = float(an['animation_length'])
    leg = M.leg_len

    def sig(t):
        W = M.world(an, t)
        f = lambda p: GL.flip(p) / leg
        pt = lambda b, q=(0, 0, 0): f(GL.ap(W[b], q))
        fw = lambda b: GL.flip(W[b][:3, :3] @ np.array([0.0, 0.0, -1.0]))
        hy = [C.yaw_of(fw(b)) for b in ('right_leg', 'left_leg')]
        tool, tip = M.strike_pts(W)
        s = {'pelvis': pt('body'), 'chest': pt(M.chest), 'head': pt('head'),
             'sh_r': pt('right_arm'), 'sh_l': pt('left_arm'),
             'hip_yaw': math.degrees(math.atan2(sum(math.sin(math.radians(x)) for x in hy), sum(math.cos(math.radians(x)) for x in hy))),
             'foot_r': f(M.foot_pt(W, 'right_leg')), 'foot_l': f(M.foot_pt(W, 'left_leg')),
             'tool': f(tool), 'tip': f(tip), 'head_fwd': fw('head'), 'chest_fwd': fw(M.chest)}
        return s
    ev = {float(k): v for k, v in an.get('timeline', {}).items()}
    return sig, L, ev, M.scale


def measure(boss):
    name, cls, scale = BOSSES[boss]
    if boss == 'martin':
        sig, L, ev = martin_sig(name)
    else:
        sig, L, ev, scale = json_sig(boss, name)
    th = [t for t, e in ev.items() if e == 'hit']
    win = (th[0] - 0.3, th[0] + 0.12) if th else None
    m = C.normalize(C.metrics(sig, L, win), scale)
    m['event'] = ('hit', th[0] if th else None)
    m['cls'] = cls
    m['scale'] = scale
    return name, m


def main(args):
    bosses = [a for a in args if a in BOSSES] or list(BOSSES)
    res = {}
    for b in bosses:
        try:
            n, m = measure(b)
        except KeyError as e:
            print('%s: нет анимации/кости %s' % (b, e))
            continue
        res[n] = m
        if '-v' in args:
            C.print_row(n, m)
    lines = []
    fails = C.report(res, {}, out=lines.append)
    print('\n'.join(lines))
    tot_ok = tot = 0
    for n, m in res.items():
        ok, t = C.score({n: m}, {})
        tot_ok, tot = tot_ok + ok, tot + t
        print('%-30s рост ×%.2f  в норме %d из %d (%.0f%%)' % (n, m['scale'], ok, t, 100.0 * ok / max(1, t)))
    print('всего: %d из %d (%.0f%%)' % (tot_ok, tot, 100.0 * tot_ok / max(1, tot)))
    if '--json' in args:
        json.dump(res, open(args[args.index('--json') + 1], 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
