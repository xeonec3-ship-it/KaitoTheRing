#!/usr/bin/env python3
"""
T28 «Арис» — проверка анимаций по запечённому animations/entity/aris.animation.json (то, что увидит GeckoLib):
  1) направление ударов: где голова молота (и ударный боёк) в момент событий удара/броска — по взгляду головы (вперёд = −z модели,
     в fx-якорях это +z «caster+x,y,z»); сзади/сбоку — ошибка;
  2) пересечения молота (hammer, hammer_ground) с телом/головой/рогами/ногами по всем кадрам (руки, держащие рукоять, не в счёт).
  python3 tools/aris_check.py [anim ...]
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_aris as G                     # noqa: E402
import gen_aris_anims as AN              # noqa: E402

AN.G = G
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
# моменты удара: (анимация, время, что проверяем) — 'head' голова молота перед ней; 'hand' левая рука (бросок/каст) перед ней
HITS = [('slam', 0.75, 'head'), ('swing', 0.62, 'head'), ('forge', 1.0, 'head'), ('forge', 1.8, 'head'), ('forge', 2.6, 'head'),
        ('last_blow', 4.0, 'head'), ('phase2', 1.0, 'head'), ('spawn', 7.0, 'head'), ('bellows', 0.8, 'head'),
        ('chains', 0.8, 'pommel'), ('billet', 0.7, 'lhand'), ('cast', 0.8, 'lhand')]
BODY = {'torso', 'head', 'body', 'right_leg', 'left_leg', 'right_shin', 'left_shin', 'right_arm', 'left_arm', 'hair1', 'hair2', 'fauld_b',
        'tasset_r', 'tasset_l'}


def load():
    m = G.build_model()
    rig = AN.Rig(m)
    anims = json.load(open(os.path.join(A, 'animations', 'entity', 'aris.animation.json'), encoding='utf-8'))['animations']
    return m, rig, anims


def chan(ch, t):
    ks = sorted(ch, key=float)
    ts = [float(k) for k in ks]
    if t <= ts[0]:
        return np.array(ch[ks[0]], float)
    if t >= ts[-1]:
        return np.array(ch[ks[-1]], float)
    i = 0
    while ts[i + 1] < t:
        i += 1
    k = (t - ts[i]) / (ts[i + 1] - ts[i])
    return np.array(ch[ks[i]], float) * (1 - k) + np.array(ch[ks[i + 1]], float) * k


def pose_at(an, t):
    P = {}
    for b, chs in an['bones'].items():
        p = {}
        if 'rotation' in chs:
            v = chan(chs['rotation'], t)
            p['rot'] = (-v[0], -v[1], v[2])
        if 'position' in chs:
            v = chan(chs['position'], t)
            p['pos'] = (-v[0], v[1], v[2])
        if 'scale' in chs:
            p['scale'] = tuple(chan(chs['scale'], t))
        P[b] = p
    return P


def cube_world(m, W, bone, c):
    Mb, ob = W[bone]
    M, o = Mb, ob
    if c.rot:
        R = AN.euler(c.rot)
        p = np.asarray(c.pivot, float)
        o = Mb @ (p - R @ p) + ob
        M = Mb @ R
    return M, o


def samples(c, n=3):
    lo, hi = c.frm - c.inflate, c.to + c.inflate
    g = [np.linspace(lo[i], hi[i], n) for i in range(3)]
    return np.array([(x, y, z) for x in g[0] for y in g[1] for z in g[2]])


def depth(m, W, bone, c, pts):
    """Глубина точек внутри куба (ед. модели; ≤ 0 — снаружи)."""
    M, o = cube_world(m, W, bone, c)
    loc = (pts - o) @ M                       # M ортонормирована: M.T·(p − o)
    lo, hi = c.frm - c.inflate, c.to + c.inflate
    return np.min(np.minimum(loc - lo, hi - loc), axis=1)


def view(W):
    """Взгляд головы (горизонт) и центр тела: вперёд = голова·(0,0,−1)."""
    Mh, oh = W['head']
    f = Mh @ np.array([0, 0, -1.0])
    f[1] = 0
    f = f / max(1e-9, np.linalg.norm(f))
    c = AN.apply(W['torso'], (0, 18, 0))
    return f, c


def ham_pt(W, p, ground=False):
    if ground:
        return AN.apply(W['hammer_ground'], G.HG_PIVOT + G.hg_offset(p))
    return AN.apply(W['hammer'], G.FIST_R + np.array(G.ham_local(p)))


def check_hits(m, rig, anims, only=None):
    print('== удары: где голова молота относительно взгляда (вперёд/вправо/вверх, ед. модели; угол от взгляда по горизонтали)')
    bad = 0
    for name, t, what in HITS:
        if only and name not in only:
            continue
        an = anims['animation.aris.' + name]
        W = rig.world(pose_at(an, t))
        f, c = view(W)
        Mb, ob = W['body']
        bf = Mb @ np.array([0, 0, -1.0])
        bf[1] = 0
        bf /= np.linalg.norm(bf)
        r = np.cross(f, [0, 1, 0])
        if what == 'head':
            p = ham_pt(W, (0, G.HAM_HEAD, 0))
        elif what == 'pommel':
            p = ham_pt(W, (0, 0, 0))
        else:
            p = AN.apply(W['left_forearm'], np.array(G.FIST_R) * [-1, 1, 1])
        d = p - c
        fw, rt, up = float(d @ f), float(d @ r), float(d[1])
        ang = math.degrees(math.atan2(rt, fw))
        bang = math.degrees(math.atan2(float(np.cross(bf, f)[1]), float(bf @ f)))
        ok = fw > 2.0 and abs(ang) < 50
        bad += not ok
        print('  %-10s %4.2f %-6s вперёд %6.1f  вправо %6.1f  вверх %6.1f  угол %5.0f°  (корпус к голове %4.0f°)  %s'
              % (name, t, what, fw, rt, up, ang, bang, 'ok' if ok else '<-- НЕ ВПЕРЕДИ'))
    return bad


def part(c):
    """Часть молота по кубу (в осях кости hammer: рукоять вдоль −z от хвата)."""
    z = (c.frm[2] + c.to[2]) / 2 - G.FIST_R[2]
    return 'голова' if z < -9.0 else 'рукоять'


def check_clip(m, rig, anims, only=None, tol=0.6, step=0.05):
    """Молот внутри тела глубже tol ед. (касание брони и рукоять в кулаке не в счёт)."""
    print('== пересечения молота с телом глубже %.1f ед. (кадры через %.2f с)' % (tol, step))
    hc = [(b, c, part(c) if b == 'hammer' else 'на земле:' + part_g(c)) for b in ('hammer', 'hammer_ground') for c in m.bones[b].cubes]
    hpts = [samples(c) for _, c, _ in hc]
    bc = [(b, c) for b in BODY for c in m.bones[b].cubes]
    total, rep = 0, {}
    for full, an in anims.items():
        name = full.split('.')[-1]
        if only and name not in only:
            continue
        L = an['animation_length']
        worst = {}
        frames = set()
        for i in range(int(round(L / step)) + 1):
            t = round(i * step, 3)
            P = pose_at(an, t)
            W = rig.world(P)
            vis = {b: (np.min(P.get(b, {}).get('scale', (1, 1, 1))) > 0.01) for b in ('hammer', 'hammer_ground')}
            for (hb, c, pn), sp in zip(hc, hpts):
                if not vis[hb]:
                    continue
                M, o = cube_world(m, W, hb, c)
                pts = sp @ M.T + o
                for bb, c2 in bc:
                    d = float(np.max(depth(m, W, bb, c2, pts)))
                    if d > tol:
                        frames.add(t)
                        k = (pn, bb)
                        if d > worst.get(k, (0, 0))[0]:
                            worst[k] = (d, t)
        rep[name] = (sorted(frames), worst)
        if frames:
            total += len(frames)
            fr = sorted(frames)
            seg, s0 = [], fr[0]
            for a, b in zip(fr, fr[1:] + [None]):
                if b is None or b - a > step + 1e-3:
                    seg.append('%g–%g' % (s0, a))
                    s0 = b
            print('  %-13s %3d кадров  [%s]' % (name, len(fr), ', '.join(seg)))
            for (pn, bb), (d, t) in sorted(worst.items(), key=lambda x: -x[1][0])[:6]:
                print('       %-16s в %-11s глубина %.1f (t=%g)' % (pn, bb, d, t))
    print('  итого кадров с пересечениями:', total)
    return total, rep


def part_g(c):
    z = (c.frm[2] + c.to[2]) / 2 - G.HG_PIVOT[2]            # от короны (пивот) вдоль рукояти: голова — первые ≈9 ед.
    return 'голова' if z < 9.0 else 'рукоять'


if __name__ == '__main__':
    only = sys.argv[1:] or None
    m, rig, anims = load()
    b = check_hits(m, rig, anims, only)
    c, _ = check_clip(m, rig, anims, only)
    print('ИТОГ: удары не вперёд — %d, кадров с пересечениями — %d' % (b, c))
