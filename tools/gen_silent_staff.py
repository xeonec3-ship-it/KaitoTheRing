#!/usr/bin/env python3
"""
Посох безмолвной ведьмы (T18) по аниме «Секреты безмолвной ведьмы» и снимкам владельца (кадр аниме, реплики посоха):
длинное тонкое золотое древко с лапкой внизу, ромбовидная муфта с камнями, перекладина с завитками, большое круглое кольцо,
внутри — «глаз» (камень подвешен к верху кольца, под ним галочка в остриё вниз), сверху три острия веером с бусинами.
По бокам парят два украшения (остриё-тюльпан с камнями, бусина, капля) — они колышутся (решение владельца):
плавно поднимаются и опускаются с отставанием частей, покачиваются, тюльпаны медленно поворачиваются.

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
    'shaft': ['#E2C26A', '#D2AE52', '#EBD083', '#B8933C'],
    'm1': ['#F6E2A0', '#D9B85E', '#E8CB7A', '#8E6A22'],
    'm2': ['#C9A24A', '#A9852F', '#B8933C', '#5E4612'],
    'm3': ['#E8E4F4', '#B8B0D0', '#CCC6E0', '#6A6286'],     # серебро цепочек
    'core': ['#FFFFFF', '#D8FFF2', '#7FFFD0', '#2FB89A'],    # бирюзовая сфера
    'core2': ['#FFFFFF', '#F0FFFA', '#BFFFEA', '#7FFFD0'],   # капли-подвески
    'hot': ['#7FFFD0', '#FFFFFF'],
    'gem': ['#F4E4FF', '#D49CF2', '#9A52D0', '#5A2290'],     # лиловый камень
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


def taper(cx, y0, steps, mat, depth=None, down=False):
    """Веретено/конус из стопки коробок: steps = [(ширина, высота)] снизу вверх (или сверху вниз при down)."""
    y = y0
    for w, h in steps:
        d = depth if depth else w
        if down:
            add(C(cx, y - h / 2, 8, w, h, d, mat))
            y -= h
        else:
            add(C(cx, y + h / 2, 8, w, h, d, mat))
            y += h
    return y


def ring(mat, cx, cy, r_out, band, depth, n=20, lit=False):
    """Круглое кольцо-обод из n отрезков (плоская лента лицом к зрителю)."""
    rm = r_out - band / 2
    seg = 2 * rm * math.tan(math.pi / n) + 0.02
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = cx + rm * math.cos(a), cy + rm * math.sin(a)
        add(C(x, y, 8, band, seg, depth, mat, math.degrees(a), 'z', lit=lit))


def bar(mat, x0, y0, x1, y1, w, depth):
    """Брусок от точки до точки в плоскости XY."""
    ln = math.hypot(x1 - x0, y1 - y0)
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    add(C((x0 + x1) / 2, (y0 + y1) / 2, 8, ln, w, depth, mat, ang, 'z'))


def gem_round(cx, cy, size, depth, mat='gem'):
    add(C(cx, cy, 8, size, size * 0.72, depth, mat, lit=True))
    add(C(cx, cy, 8, size * 0.72, size, depth, mat, lit=True))
    add(C(cx, cy, 8, size * 0.86, size * 0.86, depth, mat, 45, 'z', lit=True))


def build():
    """По снимкам владельца (кадр аниме и реплики посоха): круглое кольцо, внутри «глаз» — круглый лиловый камень у верха, под ним галочка и остриё вниз;
    сверху три острия веером с лиловыми бусинами; под кольцом перекладина с завитками; ромбовидная муфта с камнями;
    по бокам ПАРЯТ два украшения — остриё-тюльпан с тремя камнями, бусина и капля-подвеска; внизу — лапка-наконечник."""
    # древко
    add(C(8, -1.0, 8, 0.6, 27.0, 0.6, 'wood'))                       # y -14.5..12.5
    # наконечник-лапка внизу: чашка и 4 когтя, камни
    add(C(8, -14.5, 8, 0.9, 0.5, 0.9, 'm1'))
    add(C(8, -14.95, 8, 1.3, 0.4, 1.3, 'm2', 45))
    for s in (1, -1):
        add(box((8 + s * 0.3 - 0.15, -15.9, 7.85), (8 + s * 0.3 + 0.15, -14.7, 8.15), 'm1', rot(-s * 35, 'z', (8 + s * 0.3, -14.7, 8))))
        add(box((7.85, -15.9, 8 + s * 0.3 - 0.15), (8.15, -14.7, 8 + s * 0.3 + 0.15), 'm1', rot(s * 35, 'x', (8, -14.7, 8 + s * 0.3))))
    add(C(8, -14.95, 8, 0.45, 0.45, 1.5, 'gem', 45, 'z', lit=True))
    add(C(8, -14.95, 8, 1.5, 0.45, 0.45, 'gem', lit=True))
    add(C(8, -13.9, 8, 0.8, 0.3, 0.8, 'm1'))
    # муфта-веретено под перекладиной, с вытянутыми камнями спереди и сзади
    taper(8, 12.3, [(0.75, 0.4), (0.95, 0.5), (1.2, 0.6), (1.4, 0.8), (1.45, 0.7), (1.3, 0.6), (1.05, 0.5), (0.85, 0.5)], 'm1')
    add(C(8, 14.2, 8, 0.4, 1.3, 1.6, 'gem', lit=True))
    add(C(8, 12.2, 8, 0.9, 0.25, 0.9, 'm2'))
    # перекладина с завитками-спиралями на концах (загибаются вверх и внутрь)
    add(C(8, 17.2, 8, 7.6, 0.5, 0.6, 'm1'))
    add(C(8, 16.75, 8, 2.4, 0.45, 0.55, 'm2'))
    for s in (1, -1):
        chain(8 + s * 3.75, 17.2, [(-80 * s, 0.6), (-35 * s, 0.55), (15 * s, 0.5), (70 * s, 0.45), (125 * s, 0.4), (175 * s, 0.35)], 'm1', 0.45, 0.3)
    # щиток-«крылья» от перекладины к кольцу
    for s in (1, -1):
        bar('m2', 8 + s * 0.6, 17.4, 8 + s * 2.4, 18.7, 0.45, 0.5)
    # кольцо (центр 22.6, внешний радиус 4.3, широкая плоская лента)
    CY = 22.6
    ring('m1', 8, CY, 4.3, 0.8, 0.9, n=24)
    ring('m2', 8, CY, 3.55, 0.12, 1.0, n=24)                          # тонкий внутренний кант
    # «глаз»: дуга-бровь сверху внутри кольца, камень, нижние «веки» сходятся в остриё вниз
    for s in (1, -1):
        bar('m1', 8 + s * 3.55, CY + 0.9, 8 + s * 0.55, CY - 1.0, 0.8, 0.8)        # галочка: от стенок вниз к центру под камнем
        bar('m1', 8 + s * 1.7, CY + 1.45, 8 + s * 0.9, CY + 3.55, 0.45, 0.7)       # подвес камня к верху кольца
    add(C(8, CY + 3.3, 8, 2.4, 0.5, 0.8, 'm1'))                                     # скоба у верха кольца
    gem_round(8, CY + 1.1, 1.8, 1.0)
    add(C(8, CY + 1.1, 8, 2.15, 2.15, 0.7, 'm2', 45, 'z'))                          # оправа камня
    taper(8, CY - 1.0, [(0.9, 0.6), (0.7, 0.6), (0.5, 0.6), (0.3, 0.5), (0.15, 0.4)], 'm1', depth=0.6, down=True)   # остриё вниз
    add(C(8, CY - 3.9, 8, 0.6, 0.9, 0.7, 'm1'))                                     # стык кольца с древком
    # три острия веером на макушке, у основания — лиловые бусины
    for ang, a_deg in ((22, 115), (0, 90), (-22, 65)):
        a = math.radians(a_deg)
        bx, by = 8 + 4.3 * math.cos(a), CY + 4.3 * math.sin(a)
        add(C(bx, by, 8, 0.6, 0.6, 0.6, 'gem', 45, 'y', lit=True))
        chain(bx, by + 0.25, [(ang, 0.7), (ang, 0.8), (ang, 0.8), (ang, 0.7), (ang, 0.6)], 'm1', 0.6, 0.18)
    # парящие украшения по бокам: остриё-тюльпан с тремя камнями, бусина, капля-подвеска — три части отдельно, каждая своя кость
    for s, nm in ((1, 'float_r'), (-1, 'float_l')):
        fx = 8 + s * 5.4
        bone(nm, None, fx, 14.5, 8)
        bone(nm + '_top', nm, fx, 15.6, 8)
        add(C(fx, 15.25, 8, 1.0, 0.35, 1.0, 'm2', 45))                               # венчик снизу
        taper(fx, 15.4, [(1.2, 0.5), (0.95, 0.5), (0.7, 0.5), (0.45, 0.5), (0.22, 0.5)], 'm1')
        for dx, dz in ((-0.55, 0), (0.55, 0), (0, 0.55)):
            add(C(fx + dx, 15.35, 8 + dz, 0.35, 0.5, 0.35, 'gem', lit=True))
        bone(nm + '_bead', nm, fx, 14.3, 8)
        add(C(fx, 14.3, 8, 0.38, 0.38, 0.38, 'm1', 45, 'y'))
        bone(nm + '_drop', nm, fx, 13.6, 8)
        taper(fx, 13.6, [(0.55, 0.4), (0.75, 0.6), (0.7, 0.6), (0.5, 0.6), (0.3, 0.5), (0.14, 0.4)], 'm1', down=True)
        add(C(fx, 12.6, 8, 0.3, 0.6, 0.9, 'gem', lit=True))
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
    """Покой: украшения парят — плавно поднимаются и опускаются (три части с отставанием), чуть покачиваются и медленно поворачиваются;
    камни мерцают. Каст: украшения расходятся в стороны, кружатся быстрее, острия-тюльпаны вращаются. Вспышка: рывок наружу и назад."""
    idle, cast, flash = {}, {}, {}
    for s, nm in ((1, 'float_r'), (-1, 'float_l')):
        ph = 0 if s > 0 else 0.5
        idle[nm] = {'position': wave(4, (0, 0, 0), [('W', 1, ph, 0, 0.45, 0)]),
                    'rotation': wave(4, (0, 0, 0), [('W', 1, ph + 0.25, 0, 0, 4 * s), ('W', 1, ph, 3, 0, 0)])}
        idle[nm + '_top'] = {'rotation': wave(4, (0, 0, 0), [('S', 0.25, 0, 1, 0)]), 'position': wave(4, (0, 0, 0), [('W', 1, ph - 0.08, 0, 0.15, 0)])}
        idle[nm + '_bead'] = {'position': wave(4, (0, 0, 0), [('W', 1, ph - 0.16, 0, 0.2, 0)])}
        idle[nm + '_drop'] = {'position': wave(4, (0, 0, 0), [('W', 1, ph - 0.24, 0, 0.3, 0)]),
                              'rotation': wave(4, (0, 0, 0), [('W', 1, ph - 0.24, 0, 0, 6 * s)])}
        cast[nm] = {'position': wave(1, (-0.9 * s, 0.6, 0), [('W', 2, ph, 0, 0.35, 0)]),
                    'rotation': wave(1, (0, 0, 0), [('W', 1, ph, 0, 0, 8 * s)])}
        cast[nm + '_top'] = {'rotation': wave(1, (0, 0, 0), [('S', 1, 0, 1, 0)]), 'position': wave(1, (0, 0.25, 0), [('W', 2, ph - 0.1, 0, 0.15, 0)])}
        cast[nm + '_bead'] = {'position': wave(1, (0, 0.1, 0), [('W', 2, ph - 0.2, 0, 0.2, 0)])}
        cast[nm + '_drop'] = {'position': wave(1, (0, -0.2, 0), [('W', 2, ph - 0.3, 0, 0.3, 0)]),
                              'rotation': wave(1, (0, 0, 0), [('W', 2, ph - 0.3, 0, 0, 10 * s)])}
        flash[nm] = {'position': keys((0, -0.9 * s, 0.6, 0), (0.12, -2.2 * s, 1.2, 0), (0.7, 0, 0, 0))}
        flash[nm + '_drop'] = {'rotation': keys((0, 0, 0, 0), (0.12, 0, 0, 25 * s), (0.35, 0, 0, -10 * s), (0.7, 0, 0, 0))}
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
