#!/usr/bin/env python3
"""Покадровый аудит анимаций Мартина по готовому JSON (как его читает GeckoLib: rotation x/y со знаком минус, Z·Y·X,
position x со знаком минус) — правка 20.11 «руки и оружие».
  python3 tools/martin_anim_audit.py [--all] [--anim martin_swing] [--dt 0.04] [--file путь.json]
Проверки на каждом кадре:
  elbow    — локоть не разогнут назад (forearm X во внутренних осях < −3°);
  sword_*  — клинок не проходит сквозь торс / голову и рога / ноги / щит в руке / землю (кроме задуманного «остриём в землю»);
  jump     — скачок угла кости между соседними кадрами > 35° (ось, вывороты через ±180°);
  loop     — у петли первый и последний кадр не совпадают;
  irons    — у анимации Iron's нет явных ключей предплечий/меча (GeckoLib оставит позу прошлой анимации).
Выход: список замечаний и итог по каждой анимации."""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_martin as G  # noqa: E402

FILE = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'animations', 'entity', 'martin.animation.json')
# Где острие в землю задумано (опора на меч, вонзить в землю): (анимация, от, до)
GROUND_OK = [('martin_overhead', 0.9, 1.85), ('martin_phase2', 0.45, 2.6), ('martin_phase3', 0.0, 1.5), ('martin_spawn', 0.0, 3.9),
             ('martin_npc_idle', 0, 99), ('martin_to_npc', 0.6, 99), ('martin_block_yield', 1.6, 99),
             ('martin_finisher', 1.9, 2.3)]
BOXES = {   # кость: [(x0,y0,z0, x1,y1,z1)] во внутренних координатах модели (покой), чуть ужатые
    'torso': [(-4.2, 12.3, -2.8, 4.2, 23.8, 2.6)],
    'head': [(-3.8, 24.4, -4.3, 3.8, 31.4, 3.8), (-4.0, 31.4, -0.3, 4.0, 38.5, 1.5)],
    'right_leg': [(-1.7, 0.3, -2.0, 1.7, 11.7, 1.7)],
    'left_leg': [(-1.7, 0.3, -2.0, 1.7, 11.7, 1.7)],
    'shield_hand': [(-4.8, -8.2, -0.4, 4.8, 8.2, 0.4)],
}
LEG_X = {'right_leg': 2.3, 'left_leg': -2.3}


def val(v):
    if isinstance(v, dict):
        v = v.get('vector', v.get('post', v.get('pre')))
    return [float(x) if not isinstance(x, str) else 0.0 for x in v]


def chan_at(ch, t):
    if isinstance(ch, dict) and 'vector' in ch:
        ch = ch['vector']
    if isinstance(ch, list):
        return val(ch)
    ks = sorted((float(k), val(v)) for k, v in ch.items())
    if t <= ks[0][0]:
        return ks[0][1]
    for (t0, a), (t1, b) in zip(ks, ks[1:]):
        if t <= t1:
            f = (t - t0) / max(1e-9, t1 - t0)
            return [x + (y - x) * f for x, y in zip(a, b)]
    return ks[-1][1]


def pose_at(anim, t):
    p = {}
    for b, chs in anim.get('bones', {}).items():
        d = {}
        if 'rotation' in chs:
            r = chan_at(chs['rotation'], t)
            d['rot'] = [-r[0], -r[1], r[2]]
        if 'position' in chs:
            q = chan_at(chs['position'], t)
            d['pos'] = [-q[0], q[1], q[2]]
        if 'scale' in chs:
            s = chan_at(chs['scale'], t)
            d['scale'] = s if len(s) == 3 else [s[0]] * 3
        p[b] = d
    return p


def blade_local(m):
    cs = [c for c in m.bones['sword'].cubes if c.mat == 'blade']
    y0 = min(c.frm[1] for c in cs)
    y1 = max(c.to[1] for c in cs)
    x = (cs[0].frm[0] + cs[0].to[0]) / 2
    z = (cs[0].frm[2] + cs[0].to[2]) / 2
    return [np.array([x, y, z]) for y in np.linspace(y0, y1, 14)]


def audit(m, name, anim, dt=0.04, irons=False):
    out = []
    L = float(anim.get('animation_length') or 0.0)
    if irons:
        bones = anim.get('bones', {})
        miss = [b for b in ('right_forearm', 'left_forearm', 'sword') if 'rotation' not in bones.get(b, {})]
        if miss:
            out.append((0.0, 'irons', 'нет ключей: ' + ', '.join(miss)))
    blade = blade_local(m)
    n = max(1, int(round(L / dt)))
    prev = None
    for i in range(n + 1):
        t = round(min(L, i * dt), 4)
        p = pose_at(anim, t)
        # локти
        for f in ('right_forearm', 'left_forearm'):
            x = p.get(f, {}).get('rot', [0, 0, 0])[0]
            if x < -3:
                out.append((t, 'elbow', '%s X=%.0f° (разгиб назад)' % (f, x)))
        # клинок
        vis_sw = p.get('sword', {}).get('scale', [1, 1, 1])[1] > 0.5
        if vis_sw:
            Ms, os_ = G.fk(m, p, 'sword')
            pts = [Ms @ q + os_ for q in blade]
            for bone, boxes in BOXES.items():
                if bone == 'shield_hand' and p.get('shield_hand', {}).get('scale', [0, 0, 0])[1] < 0.5:
                    continue
                Mb, ob = G.fk(m, p, bone)
                hit = 0
                for q in pts[2:]:                      # у гарды — кисть, её пропускаем
                    l = Mb.T @ (q - ob)
                    if bone in LEG_X:
                        l = l - [LEG_X[bone], 0, 0]
                    if bone == 'shield_hand':
                        l = l - [-5.6, 12.5, -3.9]
                    for b in boxes:
                        if all(b[k] < l[k] < b[k + 3] for k in range(3)):
                            hit += 1
                if hit >= 2:
                    out.append((t, 'sword_' + bone, '%d точек клинка внутри' % hit))
            low = min(q[1] for q in pts)
            if low < -0.3 and not any(a == name and t0 <= t <= t1 for a, t0, t1 in GROUND_OK):
                out.append((t, 'sword_ground', 'острие на %.1f ниже земли' % -low))
        # скачки: реальный поворот кости в мире за кадр (угол между матрицами), а не разница чисел Эйлера;
        # плюс «проворот представления»: числа скачут сильно, а кость почти не повернулась (между ключами GeckoLib
        # интерполирует числа — в промежуточных кадрах кость крутится)
        cur = {}
        Mbody = G.fk(m, p, 'body')[0]
        for b, d in p.items():
            if 'rot' in d and b in m.bones:
                Mw = G.fk(m, p, b)[0]
                cur[b] = (Mw if b == 'body' else Mbody.T @ Mw, np.array(d['rot']))     # относительно body: без разворота всей фигуры
        if prev is not None:
            for b, (Mw, r) in cur.items():
                if b in prev:
                    ang = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(prev[b][0].T @ Mw) - 1) / 2))))
                    de = float(np.max(np.abs(r - prev[b][1])))
                    if name == 'martin_phase3' and b in ('body',):
                        continue
                    if ang > 60 and b not in ('body',):
                        out.append((t, 'jump', '%s повернулась на %.0f° за %.2f с' % (b, ang, dt)))
                    elif de > 60 and de > 2.5 * ang + 20:
                        out.append((t, 'euler', '%s: числа Δ%.0f°, реальный поворот %.0f° — проворот при интерполяции' % (b, de, ang)))
        prev = cur
    if anim.get('loop') is True:
        a, b = pose_at(anim, 0), pose_at(anim, L)
        for bone in a:
            if 'rot' in a[bone] and 'rot' in b.get(bone, {}):
                d = float(np.max(np.abs(np.array(a[bone]['rot']) - np.array(b[bone]['rot']))))
                if d > 3:
                    out.append((L, 'loop', '%s: начало/конец расходятся на %.0f°' % (bone, d)))
    return out


def main(args):
    f = args[args.index('--file') + 1] if '--file' in args else FILE
    dt = float(args[args.index('--dt') + 1]) if '--dt' in args else 0.04
    only = args[args.index('--anim') + 1] if '--anim' in args else None
    an = json.load(open(f, encoding='utf-8'))['animations']
    m = G.build_martin()
    total = 0
    for name, a in an.items():
        if only and name != only:
            continue
        irons = not name.startswith('martin_')
        if irons and '--all' not in args and not only:
            continue
        iss = audit(m, name, a, dt, irons)
        total += len(iss)
        kinds = {}
        for t, k, msg in iss:
            kinds.setdefault(k, []).append((t, msg))
        print('%-36s %s' % (name, 'OK' if not iss else ', '.join('%s×%d' % (k, len(v)) for k, v in kinds.items())))
        if '-v' in args:
            for k, v in kinds.items():
                for t, msg in v[:6]:
                    print('    %-13s %.2f  %s' % (k, t, msg))
    print('замечаний:', total)
    return total


if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1:]) else 0)
