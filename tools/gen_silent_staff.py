#!/usr/bin/env python3
"""
Посох безмолвной ведьмы (T18) по аниме «Секреты безмолвной ведьмы»: длинное тонкое золотое древко, кольцо-колесо со светящейся
бирюзовой сферой, над ним ажурная золотая рама-лилия с лиловым камнем, завитки с листьями-остриями, подвески на цепочках.
Части навершия колышутся (решение владельца): подвески качаются маятником с отставанием по звеньям, завитки покачиваются,
колесо медленно поворачивается.

Те же правила, что у остальных посохов мода (tools/gen_school_staffs.ps1): текстура 32x32 с областями материалов, модель в координатах
предмета (центр 8,8; y от -16 до 32), GeckoLib-геометрия (x = 8 - x, z = z - 8), анимации idle / cast / flash, glowmask для светящихся частей.

Выход (assets/pohsmp_core): geo/item/silent_witch_staff.geo.json, animations/item/silent_witch_staff.animation.json,
textures/item/silent_witch_staff.png (+ _glowmask.png), models/item/silent_witch_staff.json; превью — tools/staff_preview/silent_witch_staff.json.
Запуск: python3 tools/gen_silent_staff.py
"""
import json
import math
import os

from PIL import Image

NAME = 'silent_witch_staff'
HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')

# ---------------------------------------------------------------- текстура (как в gen_school_staffs.ps1)
UVMAP = {'wood': (0, 0, 1, 16), 'm1': (1, 0, 3, 4), 'm2': (3, 0, 5, 4), 'core': (5, 0, 7, 4), 'hot': (7, 0, 8, 4), 'gem': (8, 0, 12, 4),
         'frame': (12, 0, 16, 4), 'm3': (1, 4, 3, 8), 'm4': (3, 4, 5, 8), 'core2': (5, 4, 7, 8)}
PAL = {
    'shaft': ['#F2D77A', '#E0B850', '#FBE7A0', '#C99A30'],
    'm1': ['#FFF4C0', '#E8C25A', '#F6DC86', '#9A6E14'],
    'm2': ['#E0B850', '#B88A22', '#CC9E36', '#6E4E12'],
    'm3': ['#E8E4F4', '#B8B0D0', '#CCC6E0', '#6A6286'],     # серебро цепочек
    'core': ['#FFFFFF', '#D8FFF2', '#7FFFD0', '#2FB89A'],    # бирюзовая сфера
    'core2': ['#FFFFFF', '#F0FFFA', '#BFFFEA', '#7FFFD0'],   # капли-подвески
    'hot': ['#7FFFD0', '#FFFFFF'],
    'gem': ['#F6E6FF', '#C484F2', '#7A34B0', '#3C1466'],     # лиловый камень
}


def hx(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


def paint():
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    px = im.load()
    sh = PAL['shaft']
    for y in range(32):
        for x in range(2):
            px[x, y] = hx(sh[(y * 3 + x * 5 + (y * 7 + x) % 2) % 4])
    for y in (5, 13, 21, 29):                        # блики-гравировка на древке
        px[0, y] = hx('#FFF8D8')

    def metal(x0, y0, m):
        for y in range(8):
            for x in range(4):
                h = m[0] if (y == 0 or x == 0) else m[3] if (y == 7 or x == 3) else m[2] if (x + y) % 3 == 0 else m[1]
                px[x0 + x, y0 + y] = hx(h)

    def core(x0, y0, c):
        for y in range(8):
            for x in range(4):
                d = abs(x - 1.5) / 2 + abs(y - 3.5) / 4
                px[x0 + x, y0 + y] = hx(c[0] if d < 0.35 else c[1] if d < 0.6 else c[2] if d < 0.85 else c[3])

    metal(2, 0, PAL['m1']); metal(6, 0, PAL['m2']); core(10, 0, PAL['core'])
    metal(2, 8, PAL['m3']); metal(6, 8, PAL['m1']); core(10, 8, PAL['core2'])
    for y in range(8):
        for x in (14, 15):
            px[x, y] = hx(PAL['hot'][0] if y in (0, 7) else PAL['hot'][1])
    g = PAL['gem']
    for y in range(8):
        for x in range(8):
            d = math.hypot(x - 3.5, y - 3.5)
            px[16 + x, y] = hx(g[0] if d < 1.3 else g[1] if d < 2.4 else g[2] if d < 3.4 else g[3])
    px[18, 2] = hx('#FFFFFF')
    return im


# ---------------------------------------------------------------- элементы
ALLF = ['north', 'east', 'south', 'west', 'up', 'down']
els = []
bones = {'root': {'pivot': [0, 0, 0]}}
BN = [None]
LIT = set()


def r3(v):
    return round(float(v), 3)


def rot(angle, axis, origin):
    return {'angle': angle, 'axis': axis, 'origin': [r3(o) for o in origin]}


def box(fr, to, mat, rotation=None, lit=False):
    e = {'from': [r3(v) for v in fr], 'to': [r3(v) for v in to], 'faces': {f: {'uv': list(UVMAP[mat]), 'texture': '#0'} for f in ALLF}}
    if rotation and rotation['angle'] != 0:
        e['rotation'] = rotation
    if lit:
        e['shade'] = False
        LIT.add(mat)
        for f in e['faces'].values():
            f['forge_data'] = {'block_light': 15, 'sky_light': 15, 'ambient_occlusion': False}
    e['_b'] = BN[0] or 'root'
    e['_m'] = mat
    return e


def C(cx, cy, cz, sx, sy, sz, mat, ra=0, rax='y', lit=False):
    rr = rot(ra, rax, (cx, cy, cz)) if ra else None
    return box((cx - sx / 2, cy - sy / 2, cz - sz / 2), (cx + sx / 2, cy + sy / 2, cz + sz / 2), mat, rr, lit)


def add(e):
    els.append(e)


def bone(name, parent, mx, my, mz):
    bones[name] = {'parent': parent or 'root', 'pivot': [r3(8 - mx), r3(my), r3(mz - 8)]}
    BN[0] = name


def octo(mat, cx, cy, rx, ry, th, dz, lit=False):
    """Восьмиугольная рамка в плоскости XY."""
    hx_, hy = rx * 0.4142, ry * 0.4142
    z0, z1 = 8 - dz, 8 + dz
    add(box((cx - hx_, cy + ry - th, z0), (cx + hx_, cy + ry + th, z1), mat, lit=lit))
    add(box((cx - hx_, cy - ry - th, z0), (cx + hx_, cy - ry + th, z1), mat, lit=lit))
    add(box((cx + rx - th, cy - hy, z0), (cx + rx + th, cy + hy, z1), mat, lit=lit))
    add(box((cx - rx - th, cy - hy, z0), (cx - rx + th, cy + hy, z1), mat, lit=lit))
    hl = (math.hypot(rx - hx_, ry - hy) + th) / 2
    for sx, sy, a in ((1, 1, -45), (-1, -1, -45), (-1, 1, 45), (1, -1, 45)):
        mx, my = cx + sx * (hx_ + rx) / 2, cy + sy * (ry + hy) / 2
        add(box((mx - hl, my - th, z0), (mx + hl, my + th, z1), mat, rot(a, 'z', (mx, my, 8)), lit))


def chain(sx, sy, segs, mat, w0, w1, tip=None, tip_size=0.5, seg_bone=None, down=False, lit=False, tip_lit=None):
    """Цепочка изогнутых звеньев в плоскости XY. segs = [(угол°, длина)], 0° — вверх (или вниз при down), минус — вправо.
    seg_bone: каждое звено — своя кость (дочерняя к предыдущей), опорная точка в начале звена — для качания."""
    px_, py_ = sx, sy
    keep = BN[0]
    parent = BN[0] or 'root'
    n = len(segs)
    for i, (ang, ln) in enumerate(segs):
        if seg_bone:
            bone(f'{seg_bone}{i}', parent if i == 0 else f'{seg_bone}{i - 1}', px_, py_, 8)
        w = w0 + (w1 - w0) * (i / max(1, n - 1))
        hw = w / 2
        if down:
            add(box((px_ - hw, py_ - ln, 8 - hw), (px_ + hw, py_, 8 + hw), mat, rot(ang, 'z', (px_, py_, 8)), lit))
        else:
            add(box((px_ - hw, py_, 8 - hw), (px_ + hw, py_ + ln, 8 + hw), mat, rot(ang, 'z', (px_, py_, 8)), lit))
        a = math.radians(ang)
        sg = -1 if down else 1
        px_ += sg * (-ln * math.sin(a))
        py_ += sg * ln * math.cos(a)
    if tip:
        add(C(px_, py_ - (tip_size * 0.5 if down else -tip_size * 0.5), 8, tip_size, tip_size, tip_size * 0.8, tip, 45, 'z', lit=lit if tip_lit is None else tip_lit))
    BN[0] = keep
    return px_, py_


def build():
    # древко: тонкое, золотое, с кольцами-перехватами
    add(C(8, -1.5, 8, 0.7, 26, 0.7, 'wood'))
    for y in (-9, -3, 3, 8.5):
        add(C(8, y, 8, 1.1, 0.4, 1.1, 'm1'))
        add(C(8, y + 0.45, 8, 0.9, 0.25, 0.9, 'm2'))
    add(C(8, -14.9, 8, 1.1, 0.6, 1.1, 'm1'))
    add(C(8, -15.5, 8, 0.6, 0.6, 0.5, 'm1', 45, 'z'))
    # воротник под колесом
    add(C(8, 11.7, 8, 1.3, 0.8, 1.3, 'm1'))
    add(C(8, 12.2, 8, 1.7, 0.35, 1.7, 'm2', 45))
    # кольцо-колесо со спицами (крутится) и сфера (пульсирует)
    bone('wheel', None, 8, 15, 8)
    octo('m1', 8, 15, 2.4, 2.4, 0.22, 0.3)
    octo('m2', 8, 15, 2.75, 2.75, 0.1, 0.18)
    for a in (0, 45, 90, 135):
        add(C(8, 15, 8, 4.5, 0.18, 0.22, 'm2', a, 'z'))
    for a in range(0, 360, 45):                       # бусины на ободе
        rr = math.radians(a + 22.5)
        add(C(8 + 2.75 * math.cos(rr), 15 + 2.75 * math.sin(rr), 8, 0.35, 0.35, 0.35, 'm1', 45, 'z'))
    bone('orb', None, 8, 15, 8)
    add(C(8, 15, 8, 1.3, 1.3, 1.3, 'core', lit=True))
    add(C(8, 15, 8, 1.15, 1.15, 1.15, 'core', 45, 'y', lit=True))
    add(C(8, 15, 8, 1.15, 1.15, 1.15, 'core', 45, 'x', lit=True))
    BN[0] = None
    # стебель к раме
    add(C(8, 18.1, 8, 0.7, 1.3, 0.7, 'm1'))
    add(C(8, 18.9, 8, 1.2, 0.3, 1.2, 'm2', 45))
    # ажурная рама-лилия: овальная петля, камень, малая петля сверху, острие
    octo('m1', 8, 22.6, 1.9, 3.0, 0.24, 0.3)
    bone('gem', None, 8, 22.6, 8)
    add(C(8, 22.6, 8, 1.15, 2.3, 0.7, 'gem', lit=True))
    add(C(8, 22.6, 8, 1.2, 1.2, 0.75, 'gem', 45, 'z', lit=True))
    BN[0] = None
    octo('m1', 8, 27.0, 0.85, 0.85, 0.18, 0.25)
    add(C(8, 28.3, 8, 0.5, 0.5, 0.4, 'm1', 45, 'z'))
    add(C(8, 29.2, 8, 0.22, 1.3, 0.22, 'm1'))
    add(C(8, 25.6, 8, 0.4, 0.4, 0.35, 'm1', 45, 'z'))
    # завитки по бокам рамы: вверх-наружу, потом загибаются вниз (лилия), на конце лист-остриё; качаются
    for s, nm in ((1, 'curl_r'), (-1, 'curl_l')):
        bone(nm, None, 8 + s * 1.9, 21.2, 8)
        tx, ty = chain(8 + s * 1.9, 21.2, [(-30 * s, 1.3), (-75 * s, 1.2), (-120 * s, 1.0), (-160 * s, 0.8)], 'm1', 0.42, 0.26)
        add(C(tx, ty - 0.35, 8, 0.45, 0.9, 0.3, 'm1', 0, 'z'))                       # лист-остриё
        add(C(tx, ty - 0.85, 8, 0.25, 0.25, 0.25, 'm1', 45, 'z'))
        # подвеска с конца завитка: цепочка из 3 звеньев и капля
        chain(tx, ty - 0.95, [(0, 0.55), (0, 0.55), (0, 0.5)], 'm3', 0.14, 0.14, tip='core2', tip_size=0.42,
              seg_bone=f'{nm}_pend', down=True, tip_lit=True)
        BN[0] = None
    # нижние лепестки лилии под рамой (короткие, тоже чуть качаются)
    for s, nm in ((1, 'petal_r'), (-1, 'petal_l')):
        bone(nm, None, 8 + s * 0.5, 19.4, 8)
        chain(8 + s * 0.5, 19.4, [(-115 * s, 1.1), (-150 * s, 0.8)], 'm1', 0.32, 0.22, tip='m1', tip_size=0.32)
        BN[0] = None
    # длинные подвески с боков колеса (как ленты-цепочки в аниме): 4 звена и лиловая капля
    for s, nm in ((1, 'pend_r'), (-1, 'pend_l')):
        BN[0] = None
        add(C(8 + s * 2.9, 15, 8, 0.4, 0.4, 0.4, 'm1', 45, 'z'))
        chain(8 + s * 2.9, 14.8, [(0, 0.7), (0, 0.7), (0, 0.65), (0, 0.6)], 'm3', 0.14, 0.14, tip='gem', tip_size=0.5,
              seg_bone=nm, down=True, tip_lit=True)
        BN[0] = None


# ---------------------------------------------------------------- GeckoLib
def write_geo():
    cubes = {b: [] for b in bones}
    for el in els:
        b = el['_b']
        f, t = el['from'], el['to']
        cube = {'origin': [r3(8 - t[0]), r3(f[1]), r3(f[2] - 8)], 'size': [r3(t[0] - f[0]), r3(t[1] - f[1]), r3(t[2] - f[2])]}
        if 'rotation' in el:
            o = el['rotation']['origin']
            cube['pivot'] = [r3(8 - o[0]), r3(o[1]), r3(o[2] - 8)]
            a = el['rotation']['angle']
            cube['rotation'] = {'x': [-a, 0, 0], 'y': [0, -a, 0], 'z': [0, 0, a]}[el['rotation']['axis']]
        cube['uv'] = {fn: {'uv': [2 * fc['uv'][0], 2 * fc['uv'][1]], 'uv_size': [2 * (fc['uv'][2] - fc['uv'][0]), 2 * (fc['uv'][3] - fc['uv'][1])]}
                      for fn, fc in el['faces'].items()}
        cubes[b].append(cube)
    out = []
    for b, d in bones.items():
        bo = {'name': b}
        if b != 'root':
            bo['parent'] = d['parent']
        bo['pivot'] = d['pivot']
        if cubes[b]:
            bo['cubes'] = cubes[b]
        out.append(bo)
    geo = {'format_version': '1.12.0', 'minecraft:geometry': [{
        'description': {'identifier': f'geometry.{NAME}', 'texture_width': 32, 'texture_height': 32,
                        'visible_bounds_width': 4, 'visible_bounds_height': 4, 'visible_bounds_offset': [0, 1, 0]},
        'bones': out}]}
    os.makedirs(os.path.join(A, 'geo', 'item'), exist_ok=True)
    json.dump(geo, open(os.path.join(A, 'geo', 'item', NAME + '.geo.json'), 'w'), separators=(',', ':'))


def wave(length, base, terms, n=None):
    """Кадры канала: base + Σ vec·sin(2π(cycles·u + phase)) и вращения ('S', обороты, ось) — как Ch в gen_school_staffs.ps1."""
    if n is None:
        n = 8
        for tm in terms:
            if tm[0] != 'S':
                n = max(n, min(96, int(16 * tm[1])))
    o = {}
    for i in range(n + 1):
        u = i / n
        v = list(base)
        for tm in terms:
            if tm[0] == 'S':
                m = 360 * tm[1] * u
                v = [v[k] + tm[2 + k] * m for k in range(3)]
            else:
                m = math.sin(2 * math.pi * (tm[1] * u + tm[2]))
                v = [v[k] + tm[3 + k] * m for k in range(3)]
        o[f'{length * u:.4g}'] = [r3(x) for x in v]
    return o


def keys(*kv):
    return {f'{t:.4g}': [r3(x), r3(y), r3(z)] for t, x, y, z in kv}


def pendulum(length, cycles, amp, lag, n_links, side, prefix, x_amp=0.0):
    """Качание цепочки: каждое следующее звено отстаёт по фазе на lag и качается чуть сильнее (хлёст)."""
    out = {}
    for i in range(n_links):
        ph = -lag * i
        a = amp * (1 + 0.25 * i)
        terms = [('W', cycles, ph, 0, 0, a * side)]
        if x_amp:
            terms.append(('W', cycles, ph + 0.25, x_amp * (1 + 0.2 * i), 0, 0))
        out[f'{prefix}{i}'] = {'rotation': wave(length, (0, 0, 0), terms)}
    return out


def write_anim():
    idle, cast, flash = {}, {}, {}
    # колесо: 8-кратная симметрия — поворот на 45° за цикл замыкается бесшовно
    idle['wheel'] = {'rotation': wave(4, (0, 0, 0), [('S', 0.125, 0, 0, 1)])}
    cast['wheel'] = {'rotation': wave(1, (0, 0, 0), [('S', 0.5, 0, 0, 1)]), 'scale': wave(1, (1.06, 1.06, 1.06), [('W', 2, 0, 0.03, 0.03, 0.03)])}
    flash['wheel'] = {'scale': keys((0, 1, 1, 1), (0.12, 1.25, 1.25, 1.25), (0.7, 1, 1, 1))}
    idle['orb'] = {'scale': wave(4, (1, 1, 1), [('W', 2, 0, 0.08, 0.08, 0.08)]), 'rotation': wave(4, (0, 0, 0), [('S', 1, 0, 1, 0)])}
    cast['orb'] = {'scale': wave(1, (1.35, 1.35, 1.35), [('W', 2, 0, 0.12, 0.12, 0.12)]), 'rotation': wave(1, (0, 0, 0), [('S', 1, 0, 1, 0)])}
    flash['orb'] = {'scale': keys((0, 1.35, 1.35, 1.35), (0.15, 2.3, 2.3, 2.3), (0.7, 1, 1, 1))}
    idle['gem'] = {'scale': wave(4, (1, 1, 1), [('W', 4, 0, 0.04, 0.04, 0.04)])}
    cast['gem'] = {'scale': wave(1, (1.08, 1.08, 1.08), [('W', 4, 0, 0.05, 0.05, 0.05)])}
    for s, nm in ((1, 'curl_r'), (-1, 'curl_l')):
        ph = 0 if s > 0 else 0.5
        idle[nm] = {'rotation': wave(4, (0, 0, 0), [('W', 1, ph, 0, 0, -3 * s), ('W', 2, ph + 0.1, 2, 0, 0)])}
        cast[nm] = {'rotation': wave(1, (0, 0, -4 * s), [('W', 2, ph, 0, 0, -5 * s)])}
        flash[nm] = {'rotation': keys((0, 0, 0, 0), (0.12, 0, 0, -12 * s), (0.35, 0, 0, 5 * s), (0.7, 0, 0, 0))}
        idle.update(pendulum(4, 1, 7, 0.08, 3, s, f'{nm}_pend', x_amp=4))
        cast.update(pendulum(1, 2, 12, 0.07, 3, s, f'{nm}_pend', x_amp=6))
        flash.update({f'{nm}_pend{i}': {'rotation': keys((0, 0, 0, 0), (0.1, 0, 0, 25 * s * (1 + 0.3 * i)), (0.3, 0, 0, -14 * s), (0.5, 0, 0, 6 * s), (0.7, 0, 0, 0))}
                      for i in range(3)})
    for s, nm in ((1, 'petal_r'), (-1, 'petal_l')):
        idle[nm] = {'rotation': wave(4, (0, 0, 0), [('W', 1, 0.3, 0, 0, 2 * s)])}
        cast[nm] = {'rotation': wave(1, (0, 0, 0), [('W', 2, 0.3, 0, 0, 4 * s)])}
    for s, nm in ((1, 'pend_r'), (-1, 'pend_l')):
        ph = 0 if s > 0 else 0.37
        idle.update(pendulum(4, 1, 6, 0.09, 4, s, nm, x_amp=5))
        for i in range(4):                                  # левая подвеска — в своей фазе, чтобы не качались зеркально
            k = f'{nm}{i}'
            idle[k] = {'rotation': wave(4, (0, 0, 0), [('W', 1, ph - 0.09 * i, 0, 0, 6 * (1 + 0.25 * i) * s), ('W', 1, ph + 0.25 - 0.09 * i, 5 * (1 + 0.2 * i), 0, 0)])}
            cast[k] = {'rotation': wave(1, (0, 0, 0), [('W', 2, ph - 0.07 * i, 0, 0, 14 * (1 + 0.25 * i) * s), ('W', 2, ph + 0.25 - 0.07 * i, 8 * (1 + 0.2 * i), 0, 0)])}
            flash[k] = {'rotation': keys((0, 0, 0, 0), (0.1, 0, 0, 30 * s * (1 + 0.3 * i)), (0.3, 0, 0, -16 * s), (0.5, 0, 0, 7 * s), (0.7, 0, 0, 0))}
    doc = {'format_version': '1.8.0', 'animations': {
        'idle': {'loop': True, 'animation_length': 4, 'bones': idle},
        'cast': {'loop': True, 'animation_length': 1, 'bones': cast},
        'flash': {'loop': False, 'animation_length': 0.7, 'bones': flash}}}
    for a in doc['animations'].values():
        for b in a['bones']:
            assert b in bones, b
    os.makedirs(os.path.join(A, 'animations', 'item'), exist_ok=True)
    json.dump(doc, open(os.path.join(A, 'animations', 'item', NAME + '.animation.json'), 'w'), separators=(',', ':'))


DISPLAY = {
    'thirdperson_righthand': {'translation': [0, 2, 1.25]}, 'thirdperson_lefthand': {'translation': [0, 2, 1.25]},
    'firstperson_righthand': {'translation': [1.5, -1, -2.75]}, 'firstperson_lefthand': {'translation': [1.5, -1, -2.75]},
    'ground': {'translation': [0, 8, 0], 'scale': [0.5, 0.5, 0.5]},
    'gui': {'rotation': [-13, 128, 65], 'translation': [0.5, -0.5, 0], 'scale': [0.56, 0.56, 0.56]},
    'fixed': {'translation': [0, 0, -0.75], 'scale': [0.48, 0.48, 0.48]}}


def main():
    im = paint()
    tex = os.path.join(A, 'textures', 'item')
    im.save(os.path.join(tex, NAME + '.png'))
    build()
    for el in els:
        for v in el['from'] + el['to']:
            assert -16 <= v <= 32, (v, el)
    gm = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    src, dst = im.load(), gm.load()
    for m in LIT:
        u = UVMAP[m]
        for y in range(2 * u[1], 2 * u[3]):
            for x in range(2 * u[0], 2 * u[2]):
                c = src[x, y]
                if m == 'gem' and sum(c[:3]) < 60:
                    continue
                dst[x, y] = c
    gm.save(os.path.join(tex, NAME + '_glowmask.png'))
    write_geo()
    write_anim()
    prev = os.path.join(HERE, 'staff_preview')
    os.makedirs(prev, exist_ok=True)
    clean = [{k: v for k, v in e.items() if not k.startswith('_')} for e in els]
    json.dump({'texture_size': [32, 32], 'textures': {'0': f'pohsmp_core:item/{NAME}'}, 'elements': clean, 'display': DISPLAY},
              open(os.path.join(prev, NAME + '.json'), 'w'), separators=(',', ':'))
    item = {'parent': 'minecraft:builtin/entity', 'textures': {'particle': f'pohsmp_core:item/{NAME}'}, 'gui_light': 'front', 'display': DISPLAY}
    json.dump(item, open(os.path.join(A, 'models', 'item', NAME + '.json'), 'w'), separators=(',', ':'))
    print(f'{NAME}: {len(els)} elements, {len(bones)} bones, glow: {sorted(LIT)}')


if __name__ == '__main__':
    main()
