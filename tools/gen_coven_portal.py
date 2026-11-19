#!/usr/bin/env python3
"""
Портал Ковена (элемент `mesh` из docs/fx.md): геометрическая рама из вложенных колец, многоугольников и граней,
которая раскрывается из маленького многогранника. Пишет описание частями — отрисовщик строит из них геометрию:

- ring:    кольцо-трубка радиусом radius и толщиной thickness; при появлении крутится вокруг своей оси tiltAxis
           (как армиллярная сфера) и ложится в плоскость портала;
- polygon: рама-многоугольник из трубок (sides, radius, rotation);
- facet:   плоская светящаяся треугольная грань: в начале — грань многогранника в центре, потом летит на своё место на раме;
- disc:    плоский диск с текстурой (космос внутри портала);
- seed:    исходный многогранник (октаэдр) в центре, гаснет, когда грани разлетаются.

Плоскость портала — XY (вертикальная, смотрит по +Z), центр в (0, 0, 0), высота центра над землёй — `center`.
Время в тиках. Запуск: python3 tools/gen_coven_portal.py
"""
import json
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'fx', 'meshes', 'coven_portal.json')

R = 2.6                     # внешний радиус рамы, блоки
rng = random.Random(42)

parts = []

# многогранник-семя в центре
parts.append({'type': 'seed', 'shape': 'octahedron', 'radius': 0.35, 'spin': [40, 70, 0],
              'appear': {'delay': 0, 'duration': 10, 'easing': 'easeOutBack'},
              'vanish': {'delay': 34, 'duration': 10}})

# грани октаэдра разлетаются на раму: 8 граней -> 8 мест по кругу между внешними кольцами
OCTA = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
FACES = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
for k, (a, b, c) in enumerate(FACES):
    src = [[v * 0.35 for v in OCTA[i]] for i in (a, b, c)]
    ang = 2 * math.pi * k / 8 + math.pi / 8
    rr = R * 0.9
    cx, cy = rr * math.cos(ang), rr * math.sin(ang)
    s = 0.28
    # на раме — треугольник, вершиной наружу
    out = [[cx + math.cos(ang) * s * 1.6, cy + math.sin(ang) * s * 1.6, 0],
           [cx + math.cos(ang + 2.2) * s, cy + math.sin(ang + 2.2) * s, 0],
           [cx + math.cos(ang - 2.2) * s, cy + math.sin(ang - 2.2) * s, 0]]
    parts.append({'type': 'facet', 'from': src, 'to': out, 'color': '@core', 'brightness': 1.0,
                  'appear': {'delay': 30 + k * 2, 'duration': 22, 'easing': 'easeInOutCubic'}, 'spinOnFly': 360})

# вложенные кольца: каждое крутится вокруг своей оси и ложится в плоскость (армиллярная сфера)
rings = [(1.00, 0.07, [1, 0, 0], 360, 18), (0.93, 0.03, [0, 1, 0], -540, -10),
         (0.78, 0.05, [1, 1, 0], 450, 24), (0.62, 0.035, [1, -1, 0], -360, -30), (0.45, 0.04, [0, 1, 0], 720, 40)]
for i, (k, th, axis, turn, spin) in enumerate(rings):
    parts.append({'type': 'ring', 'radius': R * k, 'thickness': th, 'color': '@primary' if i % 2 == 0 else '@secondary',
                  'tiltAxis': axis, 'tiltTurns': turn, 'spin': spin,
                  'appear': {'delay': 12 + i * 5, 'duration': 40, 'easing': 'easeOutCubic'}})

# многоугольные рамы: шестиугольник и треугольники Ковена
for sides, k, rot, spin, d in [(6, 0.86, 0, 6, 46), (3, 0.70, 90, -12, 54), (3, 0.70, -90, 12, 58), (6, 0.36, 30, -20, 62)]:
    parts.append({'type': 'polygon', 'sides': sides, 'radius': R * k, 'rotation': rot, 'thickness': 0.035, 'color': '@primary',
                  'spin': spin, 'appear': {'delay': d, 'duration': 16, 'easing': 'easeOutBack'}})

# космос внутри
parts.append({'type': 'disc', 'texture': 'glow', 'radius': R * 0.62, 'color': '@shadow', 'brightness': 1.0, 'blend': 'translucent',
              'appear': {'delay': 40, 'duration': 24, 'easing': 'easeOutCubic'}})
parts.append({'type': 'disc', 'texture': 'constellation', 'radius': R * 0.58, 'color': '@secondary', 'brightness': 0.9, 'spin': 4,
              'appear': {'delay': 48, 'duration': 24, 'easing': 'easeOutCubic'}})

portal = {
    'comment': 'Портал Ковена. Сгенерировано tools/gen_coven_portal.py — правки вносить в генератор.',
    'style': 'coven',
    # низ «космоса» (диска R*0.62) у самой земли, чтобы из портала выходили по земле, а не из воздуха; нижняя дуга
    # внешних колец уходит в землю (владелец, 19.11: «портал в воздухе»). = CovenArrivalSpell.PORTAL_Y
    'center': round(R * 0.62 + 0.25, 2),
    'formedAt': 80,
    'collapse': {'duration': 24, 'easing': 'easeInCubic'},
    'parts': parts,
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(portal, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('wrote', os.path.relpath(OUT, os.path.join(HERE, '..')), len(parts), 'parts')
