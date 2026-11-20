#!/usr/bin/env python3
"""
T27: посох Ирины — объёмная модель предмета из брусков по референсу docs/references/t27/irina_staff.jpg.
Длинное красное древко с чёрными кольцами-вставками, чёрный подток снизу; чёрное навершие — изогнутая «S»/серп с красными завитками
и красными режущими кромками; с левого «уха» навершия на цепочке свисают золотая бусина и красная кисть.

Раскладка — как у посохов Iron's (graybeard_staff и др.): древко вертикально по y в плоскости x = 8, z = 8, от −16 до 32; навершие —
в плоскости XY. Хват — около y = −2 (нижняя треть).
  models/item/irina_staff.json      — в руке 3D, в GUI/на земле/в рамке — та же 3D-модель (уменьшена и повёрнута)
  textures/item/irina_staff_3d.png   — 64×64 (×4, как эталон): каждый тон — клетка 4×4 с ручной светотенью (блик сверху-слева,
                                       тень снизу-справа, искра лака у красного и золота)
Превью: tools/irina_staff_preview.html; кадр docs/media/t27_staff.png (делает tools/irina_render.py).
Предмет pohsmp_core:irina_staff регистрирует код (без рецепта, игрокам не выдаётся) и даёт его боссу в правую руку.
Запуск: python3 tools/gen_irina_staff.py
"""
import json
import math
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
PAL = {
    'k': '#0C090B', 'k1': '#1A1417', 'k2': '#2B2226', 'k3': '#463A3F',          # чернёный металл / лак (тёмный → блик)
    'r0': '#4A0610', 'r1': '#7E0C18', 'r2': '#B4182A', 'r3': '#DE3341', 'r4': '#FF7F80',   # красный лак древка и кромок
    'g1': '#9C6A12', 'g2': '#E2A92E', 'g3': '#FFE38A',                       # золото бусины
    't1': '#6E0A16', 't2': '#A3192A', 't3': '#CF3A46',                       # кисть
}
CELL = {k: (i % 16, i // 16) for i, k in enumerate(PAL)}
R3 = lambda v: round(v, 3)
ANG = (-45, -22.5, 0, 22.5, 45)
Z = 8.0


class M:
    def __init__(self):
        self.el = []

    def box(self, cx, cy, cz, sx, sy, sz, col, ang=0.0, side=None, axis='z'):
        a = min(ANG, key=lambda q: abs(q - ang))
        faces = {}
        for f in ('north', 'south', 'east', 'west', 'up', 'down'):
            u, v = CELL[(side or {}).get(f, col)]
            faces[f] = {'uv': [u + .03, v + .03, u + .97, v + .97], 'texture': '#p'}
        e = {'from': [R3(cx - sx / 2), R3(cy - sy / 2), R3(cz - sz / 2)], 'to': [R3(cx + sx / 2), R3(cy + sy / 2), R3(cz + sz / 2)],
             'faces': faces}
        if a:
            e['rotation'] = {'axis': axis, 'angle': a, 'origin': [R3(cx), R3(cy), R3(cz)]}
        self.el.append(e)

    def seg(self, p, q, w, d, col, z=Z, side=None):
        """Брусок вдоль отрезка p→q в плоскости XY; толщина w поперёк, глубина d (по z). Угол — ближайший разрешённый (кратно 22.5°)."""
        cx, cy = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        ang = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
        ang = (ang + 90) % 180 - 90
        if abs(ang) <= 56.25:
            self.box(cx, cy, z, L + w * 0.35, w, d, col, ang, side)
        else:
            self.box(cx, cy, z, w, L + w * 0.35, d, col, ang - 90 if ang > 0 else ang + 90, side)

    def ring(self, y, w, h, col, side=None, oct_=True):
        """Кольцо на древке: квадрат + повёрнутый на 45° вокруг y (восьмигранник)."""
        self.box(8, y, Z, w, h, w, col, 0, side)
        if oct_:
            self.box(8, y, Z, w * 0.83, h, w * 0.83, col, 45, side, axis='y')

    def curve(self, pts, w0, w1, d, col, side=None, z=Z):
        n = len(pts) - 1
        for i in range(n):
            t = i / max(1, n - 1)
            self.seg(pts[i], pts[i + 1], w0 + (w1 - w0) * t, d, col, z, side)


def bez(p0, p1, p2, p3, n):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def spiral(cx, cy, r0, r1, turns, a0, n, sgn=1):
    return [(cx + (r0 + (r1 - r0) * i / n) * math.cos(a0 + sgn * turns * 2 * math.pi * i / n),
             cy + (r0 + (r1 - r0) * i / n) * math.sin(a0 + sgn * turns * 2 * math.pi * i / n)) for i in range(n + 1)]


def build():
    m = M()
    # ---- древко: красное, с бликом по ребру; снизу подток, чёрные вставки
    m.box(8, 2.5, Z, 0.9, 37.0, 0.9, 'r3', side={'north': 'r4', 'south': 'r4', 'west': 'r2', 'east': 'r2'})        # −16 … 21
    m.box(7.68, 2.5, Z - 0.3, 0.22, 36.4, 0.4, 'r4')                                                # блик
    # подток (чёрный, остриё вниз) и нижние кольца
    m.box(8, -15.3, Z, 0.55, 1.4, 0.55, 'k2')
    m.box(8, -14.2, Z, 0.85, 1.2, 0.85, 'k1', side={'north': 'k2'})
    m.ring(-13.2, 1.25, 0.9, 'k', side={'north': 'k2'})
    m.ring(-12.4, 1.05, 0.5, 'r3')
    m.ring(-11.7, 1.3, 0.9, 'k1', side={'north': 'k3'})
    # нижняя вставка у хвата (чёрная бусина с кольцами)
    m.ring(-6.2, 1.1, 0.4, 'k1', side={'north': 'k3'})
    m.ring(-5.0, 1.45, 1.9, 'k', side={'north': 'k2'})
    m.ring(-3.8, 1.1, 0.4, 'k1', side={'north': 'k3'})
    # хват: обмотка тёмно-красной лентой
    for i in range(6):
        m.box(8, -1.8 + i * 0.75, Z, 1.06, 0.36, 1.06, 'r0' if i % 2 else 'r1', 0)
    # средние тонкие кольца
    for y in (6.5, 12.0):
        m.ring(y, 1.12, 0.45, 'k1', side={'north': 'k3'})
    # верхний воротник под навершием: точёные чёрные кольца разной толщины (как на референсе)
    collar = [(16.2, 1.05, 0.5, 'k1'), (17.0, 1.4, 1.1, 'k'), (17.8, 1.2, 0.5, 'r2'), (18.6, 1.55, 1.1, 'k'),
              (19.5, 1.25, 0.7, 'k1'), (20.4, 1.7, 1.2, 'k'), (21.3, 1.35, 0.6, 'k2')]
    for y, w, h, c in collar:
        m.ring(y, w, h, c, side={'north': 'k3' if c[0] == 'k' else 'r4'})
    # ---- навершие: чёрная «S» — ствол от воротника вверх-влево, большой серп поверху вправо и вниз (крюк), нижний завиток вправо
    D = 1.5                                                    # толщина навершия по z
    trunk = bez((8.0, 21.6), (7.4, 23.6), (5.2, 25.5), (5.6, 28.4), 6)
    m.curve(trunk, 1.9, 1.6, D, 'k1', side={'north': 'k2', 'up': 'k2'})
    top = bez((5.6, 28.2), (5.9, 31.4), (11.8, 32.4), (15.3, 29.6), 9)          # верхняя дуга серпа
    m.curve(top, 1.7, 1.2, D, 'k1', side={'north': 'k2', 'up': 'k3'})
    hook = bez((15.3, 29.6), (16.6, 28.2), (16.0, 25.6), (13.6, 24.3), 6)       # крюк вниз, остриё внутрь
    m.curve(hook, 1.2, 0.45, D * 0.9, 'k', side={'north': 'k2'})
    # красная режущая кромка по внутренней стороне крюка и дуги
    inner = bez((9.0, 29.9), (12.2, 30.5), (15.2, 28.6), (14.6, 26.2), 8)
    m.curve(inner, 0.7, 0.55, D * 0.75, 'r3', side={'north': 'r4', 'south': 'r4'})
    edge = bez((15.0, 28.6), (15.4, 27.0), (14.9, 25.4), (13.3, 24.4), 5)
    m.curve(edge, 0.6, 0.35, D * 0.7, 'r3', side={'north': 'r4', 'south': 'r4'})
    # «щёки» навершия: сплошная тёмная пластина внутри S (чтобы силуэт был массивным, как на референсе)
    for (x, y, sx, sy, a) in ((7.2, 26.6, 2.6, 3.4, 22.5), (8.6, 28.9, 3.4, 2.0, -22.5), (6.6, 24.0, 2.0, 2.4, -22.5)):
        m.box(x, y, Z, sx, sy, D * 0.85, 'k1', a, side={'north': 'k2'})
    # нижний завиток S вправо + шип
    low = bez((7.6, 23.4), (9.4, 23.2), (11.0, 24.2), (10.6, 25.8), 5)
    m.curve(low, 1.1, 0.7, D * 0.85, 'k1', side={'north': 'k2'})
    m.seg((10.8, 23.6), (12.6, 23.0), 0.5, D * 0.6, 'k', side={'north': 'k2'})
    m.seg((12.2, 23.1), (13.2, 22.8), 0.28, D * 0.5, 'r3')                      # красное остриё шипа
    # левые шипы (как на референсе: два крючка влево-вниз с красными кончиками)
    m.seg((6.4, 22.6), (4.6, 21.6), 0.6, D * 0.6, 'k', side={'north': 'k2'})
    m.seg((4.8, 21.7), (3.9, 21.4), 0.3, D * 0.5, 'r3')
    m.seg((5.4, 26.4), (3.8, 26.0), 0.55, D * 0.6, 'k', side={'north': 'k2'})
    m.seg((4.0, 26.05), (3.2, 25.6), 0.28, D * 0.5, 'r3')
    # «ухо» вверху слева — к нему крепится цепочка
    m.box(5.0, 30.0, Z, 1.1, 1.1, 0.9, 'k', 45, side={'north': 'k3'})
    m.box(4.3, 30.3, Z, 0.5, 0.5, 0.5, 'k2', 0)
    # красные завитки-узоры на обеих сторонах навершия (на поверхности: z = ±(D/2 + 0.05))
    for zz in (Z - D / 2 - 0.06, Z + D / 2 + 0.06):
        s1 = spiral(9.0, 28.9, 1.25, 0.25, 1.3, math.radians(200), 10, -1)
        m.curve(s1, 0.32, 0.26, 0.14, 'r2', side={'north': 'r3', 'south': 'r3'}, z=zz)
        s2 = spiral(7.4, 25.4, 1.0, 0.2, 1.2, math.radians(30), 9, 1)
        m.curve(s2, 0.3, 0.24, 0.14, 'r2', side={'north': 'r3', 'south': 'r3'}, z=zz)
        tail = bez((6.0, 27.6), (6.6, 28.6), (7.6, 29.6), (8.2, 30.2), 4)           # связка завитков (как «S»-узор)
        m.curve(tail, 0.26, 0.22, 0.14, 'r2', side={'north': 'r3', 'south': 'r3'}, z=zz)
        m.curve(bez((9.6, 26.0), (10.3, 26.6), (10.0, 27.4), (9.4, 27.6), 3), 0.24, 0.2, 0.14, 'r2', z=zz)
        m.box(8.0, 22.2, zz, 0.9, 0.25, 0.14, 'r3', 0)                               # красный кант над воротником
    # ---- цепочка с бусиной и кистью (с «уха» вниз)
    cx = 4.6
    y = 29.4
    for i in range(7):                                          # звенья: чередуются плоскостью
        if i % 2:
            m.box(cx, y - 0.32, Z, 0.42, 0.62, 0.14, 'k2', 0)
        else:
            m.box(cx, y - 0.32, Z, 0.14, 0.62, 0.42, 'k3', 0)
        y -= 0.62
    m.box(cx, y - 0.2, Z, 0.6, 0.35, 0.6, 'k1', 0)
    y -= 0.4
    m.box(cx, y - 0.55, Z, 1.15, 1.1, 1.15, 'g2', 0, side={'north': 'g3', 'west': 'g3', 'down': 'g1', 'east': 'g1'})   # бусина
    m.box(cx, y - 0.55, Z, 0.9, 1.25, 0.9, 'g2', 45, side={'north': 'g3', 'south': 'g1'}, axis='y')
    m.box(cx, y - 0.55, Z, 1.3, 0.6, 1.3, 'g1', 45, axis='y')
    y -= 1.2
    for (h, w, c) in ((0.3, 0.5, 'k1'), (0.35, 0.8, 'k'), (0.3, 0.45, 'k2'), (0.45, 0.95, 'k1'), (0.3, 0.5, 'k')):   # «рыбка»-подвес
        m.box(cx, y - h / 2, Z, w, h, w, c, 0, side={'north': 'k3'})
        y -= h
    m.box(cx, y - 0.3, Z, 0.9, 0.6, 0.9, 'r1', 0, side={'north': 't3'})          # узел кисти
    y -= 0.6
    top_y = y
    L = 5.8
    for j, (dx, dz, c) in enumerate(((-0.42, 0, 't2'), (0.42, 0, 't1'), (0, -0.42, 't3'), (0, 0.42, 't1'), (0, 0, 't2'),
                                     (-0.3, -0.3, 't3'), (0.3, 0.3, 't1'), (0.3, -0.3, 't2'), (-0.3, 0.3, 't2'))):
        spread = 1.0 + 0.9 * (j % 3) / 2
        m.seg((cx + dx * 0.4, top_y), (cx + dx * spread * 1.6, top_y - L + 0.25 * (j % 2)), 0.32, 0.32, c, z=Z + dz * spread)
    m.box(cx, top_y - 0.5, Z, 1.0, 0.35, 1.0, 'g2', 0)                           # золотой поясок кисти
    return m.el


DISPLAY = {   # Iron's (HumanoidRenderer.renderStackForBone): у кости руки item поворачивается X −90 — без поворота посох смотрел бы вперёд.
    # Проверка анимаций 20.11: прежний хват [−28, 90, 90] + сдвиг 8.5 клал древко вдоль руки вверх (держало предплечье, не кулак) —
    # при любом подъёме руки навершие уходило назад сквозь капюшон и поля шляпы. Теперь: кулак на нижней трети древка (y предмета 0),
    # древко под 80° к руке вперёд-вверх; при руке вперёд на 50° (покой) посох стоит наклонно перед ней, крюк впереди.
    # translation = −R·S·(0, 0 − 8, 0): точка хвата (8, 0, 8) предмета ложится в кость кисти. Проверка: tools/irina_anim_check.py.
    'thirdperson_righthand': {'rotation': [-80, 90, 90], 'translation': [0, 6.7, 1.18], 'scale': [0.85, 0.85, 0.85]},
    'thirdperson_lefthand': {'rotation': [-80, -90, -90], 'translation': [0, 6.7, 1.18], 'scale': [0.85, 0.85, 0.85]},
    'firstperson_righthand': {'rotation': [0, 0, 0], 'translation': [1.5, 0, -2.75], 'scale': [0.6, 0.6, 0.6]},
    'firstperson_lefthand': {'rotation': [0, 0, 0], 'translation': [1.5, 0, -2.75], 'scale': [0.6, 0.6, 0.6]},
    'gui': {'rotation': [0, 0, -38], 'translation': [-0.5, -1.5, 0], 'scale': [0.34, 0.34, 0.34]},
    'ground': {'translation': [0, 4, 0], 'scale': [0.4, 0.4, 0.4]},
    'fixed': {'rotation': [0, 0, -38], 'translation': [0, -1, 0], 'scale': [0.34, 0.34, 0.34]},
    'head': {'translation': [0, 14, 0], 'scale': [0.6, 0.6, 0.6]},
}


def main():
    pal = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    for k, (x, y) in CELL.items():
        h = PAL[k]
        base = [int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)]
        for dy in range(4):
            for dx in range(4):
                f = 1.0
                if dx == 0 or dy == 0:
                    f = 1.16                                         # блик по верхней-левой кромке
                if dx == 3 or dy == 3:
                    f = 0.78                                         # тень по нижней-правой
                if (dx, dy) == (1, 1) and k[0] in 'rgt':
                    f = 1.32                                         # искра лака / металла
                if (dx, dy) == (2, 2) and k[0] == 'k':
                    f = 1.25                                         # тусклый отблеск чернёного металла
                c = tuple(max(0, min(255, int(v * f))) for v in base)
                pal.putpixel((x * 4 + dx, y * 4 + dy), c + (255,))
    os.makedirs(os.path.join(A, 'textures', 'item'), exist_ok=True)
    pal.save(os.path.join(A, 'textures', 'item', 'irina_staff_3d.png'))
    els = build()
    lo = [min(e['from'][i] for e in els) for i in range(3)]
    hi = [max(e['to'][i] for e in els) for i in range(3)]
    assert all(v >= -16 for v in lo) and all(v <= 32 for v in hi), (lo, hi)
    doc = {'comment': 'T27 посох Ирины (tools/gen_irina_staff.py). Объёмная модель из брусков; вертикально, как посохи Iron\'s.',
           'gui_light': 'front', 'textures': {'p': 'pohsmp_core:item/irina_staff_3d', 'particle': 'pohsmp_core:item/irina_staff_3d'},
           'elements': els, 'display': DISPLAY}
    os.makedirs(os.path.join(A, 'models', 'item'), exist_ok=True)
    with open(os.path.join(A, 'models', 'item', 'irina_staff.json'), 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print('irina_staff: %d elements, bounds %s … %s' % (len(els), lo, hi))
    return doc


def preview_data():
    """Для превью three.js: [from, to, цвет, rotation, цвета граней]."""
    doc = json.load(open(os.path.join(A, 'models', 'item', 'irina_staff.json'), encoding='utf-8'))
    inv = {v: k for k, v in CELL.items()}
    out = []
    for e in doc['elements']:
        fc = {f: PAL[inv[(int(v['uv'][0]), int(v['uv'][1]))]] for f, v in e['faces'].items()}
        out.append([e['from'], e['to'], e.get('rotation'), fc])
    return {'els': out, 'display': doc['display']}


if __name__ == '__main__':
    main()
