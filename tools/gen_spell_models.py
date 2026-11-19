"""Модели заклинаний из брусков (fx/meshes, часть boxes, docs/fx.md) — владелец 19.11.2026 просил свои модели:

  lightning_rod.json  — «Громоотвод»: каменное основание, медная мачта с поясами, светящаяся катушка, три зубца-короны
                        и парящий кристалл (без тонкого шпиля). Высота ~3.1.
  oblivion_blade.json — «Клинки забвения»: тёмный изогнутый клинок вдоль +z (остриём вперёд), фиолетовая кромка, руны, гарда.
  fire_whip.json      — «Огненная плеть»: рукоять и огненный хлыст 6 блоков вдоль +z с провисом, ядро светится.

Локальные оси модели: x вправо, y вверх, z вперёд (по yaw/pitch эффекта). Запуск: python tools/gen_spell_models.py
"""
import json, math, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'fx', 'meshes')


def r(v):
    return round(v, 3)


def box(cx, cy, cz, sx, sy, sz, tone, rot=None):
    b = [r(cx - sx / 2), r(cy - sy / 2), r(cz - sz / 2), r(cx + sx / 2), r(cy + sy / 2), r(cz + sz / 2), tone]
    if rot and any(rot):
        b.append([r(x) for x in rot])
    return b


def dump(name, obj):
    with open(os.path.join(ROOT, name), 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, separators=(',', ':'))
    n = sum(len(p.get('boxes', [])) for p in obj['parts'])
    print('wrote fx/meshes/%s: %d boxes' % (name, n))


# ---------------------------------------------------------------- lightning rod
solid, glow = [], []
for k in range(8):   # octagonal plinth
    a = k * math.pi / 4
    solid.append(box(math.cos(a) * 0.42, 0.12, math.sin(a) * 0.42, 0.36, 0.24, 0.2, 0, [0, -math.degrees(a) + 90, 0]))
solid.append(box(0, 0.14, 0, 0.62, 0.28, 0.62, 0))
solid.append(box(0, 0.3, 0, 0.5, 0.06, 0.5, 1))                       # copper cap of the plinth
solid.append(box(0, 1.3, 0, 0.16, 2.0, 0.16, 2))                      # iron mast
for y in (0.55, 1.2, 1.85, 2.3):                                      # copper bands
    solid.append(box(0, y, 0, 0.24, 0.07, 0.24, 1))
for k in range(18):                                                   # glowing coil around the mast
    a = k * 0.9
    y = 0.6 + k * 0.085
    glow.append(box(math.cos(a) * 0.16, y, math.sin(a) * 0.16, 0.07, 0.05, 0.07, 4))
solid.append(box(0, 2.42, 0, 0.36, 0.1, 0.36, 1))                     # crown plate
for k in range(3):                                                    # three short prongs, leaning out
    a = k * 2 * math.pi / 3
    solid.append(box(math.cos(a) * 0.17, 2.62, math.sin(a) * 0.17, 0.07, 0.36, 0.07, 1,
                     [math.sin(a) * 22, 0, -math.cos(a) * 22]))
glow.append(box(0, 2.95, 0, 0.26, 0.26, 0.26, 4, [45, 45, 0]))        # floating crystal
glow.append(box(0, 2.95, 0, 0.13, 0.13, 0.13, 3, [45, 45, 0]))        # its white heart
APPEAR = {'delay': 0, 'duration': 8, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.5}
dump('lightning_rod.json', {
    'comment': 'Громоотвод: каменное основание, медная мачта с поясами, светящаяся катушка, корона из трёх зубцов и парящий кристалл. '
               'Сгенерировано tools/gen_spell_models.py.',
    'style': 'lightning', 'center': 0, 'formedAt': 8, 'collapse': {'duration': 8, 'easing': 'easeInCubic'},
    'parts': [
        {'type': 'boxes', 'tones': ['#3A3F4A', '#C8743A', '#5A6070', '#FFFFFF', '#6BE6FF'], 'glowTones': [3, 4], 'blend': 'translucent',
         'opacity': 0.97, 'shade': True, 'boxes': solid, 'appear': APPEAR, 'bounds': [0.0, 3.1]},
        {'type': 'boxes', 'tones': ['#3A3F4A', '#C8743A', '#5A6070', '#FFFFFF', '#6BE6FF'], 'glowTones': [3, 4], 'blend': 'translucent',
         'opacity': 0.97, 'shade': True, 'boxes': glow, 'appear': APPEAR, 'bounds': [0.0, 3.1]},
    ]})

# ---------------------------------------------------------------- oblivion blade (point along +z)
body, edge = [], []
body.append(box(0, 0, -0.32, 0.06, 0.06, 0.26, 0))                    # grip
body.append(box(0, 0, -0.47, 0.1, 0.1, 0.06, 1))                      # pommel
body.append(box(0, 0, -0.17, 0.42, 0.06, 0.06, 1))                    # guard
for s in (-1, 1):
    body.append(box(s * 0.24, 0, -0.13, 0.12, 0.05, 0.05, 1, [0, s * 35, 0]))
N, L = 10, 1.1
for k in range(N):                                                    # the blade: tapering, bending slightly to the right
    u0, u1 = k / N, (k + 1) / N
    z = -0.12 + (u0 + u1) / 2 * L
    w = 0.16 * (1 - u0) + 0.03
    bend = 0.12 * ((u0 + u1) / 2) ** 2
    turn = math.degrees(math.atan(0.24 * (u0 + u1) / 2))
    body.append(box(bend, 0, z, w, 0.03, L / N + 0.01, 2, [0, turn, 0]))
    edge.append(box(bend + w / 2, 0, z, 0.025, 0.035, L / N + 0.01, 3, [0, turn, 0]))
    if k % 3 == 1:
        edge.append(box(bend - w * 0.1, 0.018, z, 0.035, 0.01, 0.05, 4, [0, turn, 0]))   # runes
edge.append(box(0.12, 0, -0.12 + L + 0.02, 0.03, 0.035, 0.08, 3, [0, 18, 0]))         # the point
dump('oblivion_blade.json', {
    'comment': 'Клинок забвения: тёмный изогнутый клинок вдоль +z (остриём вперёд), фиолетовая кромка и руны, гарда с крылышками. '
               'Сгенерировано tools/gen_spell_models.py.',
    'style': 'higher', 'center': 0, 'formedAt': 6, 'collapse': {'duration': 8, 'easing': 'easeInCubic'},
    'parts': [
        {'type': 'boxes', 'tones': ['#1A1420', '#4A2A66', '#140A1E', '#B06CFF', '#E0C8FF'], 'glowTones': [3, 4], 'blend': 'translucent',
         'opacity': 0.95, 'shade': True, 'boxes': body, 'appear': {'delay': 0, 'duration': 6, 'easing': 'easeOutCubic'}},
        {'type': 'boxes', 'tones': ['#1A1420', '#4A2A66', '#140A1E', '#B06CFF', '#E0C8FF'], 'glowTones': [3, 4], 'blend': 'translucent',
         'opacity': 0.95, 'shade': True, 'boxes': edge, 'appear': {'delay': 0, 'duration': 6, 'easing': 'easeOutCubic'}},
    ]})

# ---------------------------------------------------------------- fire whip (handle at 0, lash along +z, sagging)
handle, lash = [], []
handle.append(box(0, 0, -0.22, 0.08, 0.08, 0.36, 0))
handle.append(box(0, 0, -0.03, 0.13, 0.13, 0.05, 1))
handle.append(box(0, 0, -0.42, 0.11, 0.11, 0.05, 1))
LEN, SEG = 6.0, 24
for k in range(SEG):
    u0, u1 = k / SEG, (k + 1) / SEG
    z0, z1 = u0 * LEN, u1 * LEN
    y0, y1 = -math.sin(u0 * math.pi) * 0.6, -math.sin(u1 * math.pi) * 0.6
    pitch = math.degrees(math.atan2(-(y1 - y0), z1 - z0))
    th = 0.14 * (1 - u0) + 0.035
    seg = math.hypot(z1 - z0, y1 - y0) + 0.02
    cz, cy = (z0 + z1) / 2, (y0 + y1) / 2
    lash.append(box(0, cy, cz, th * 1.8, th * 1.8, seg, 2, [pitch, 0, 0]))     # flame sheath
    lash.append(box(0, cy, cz, th * 0.8, th * 0.8, seg, 3, [pitch, 0, 0]))     # white-hot core
    if k % 3 == 0:
        lash.append(box(0, cy, cz, th * 2.4, th * 0.5, 0.05, 4, [pitch, k * 25, 0]))   # ember rings
dump('fire_whip.json', {
    'comment': 'Огненная плеть: рукоять и огненный хлыст 6 блоков вдоль +z с провисом; пламя полупрозрачное, ядро и угли светятся. '
               'FireWhipSpell поворачивает его по дуге взмаха. Сгенерировано tools/gen_spell_models.py.',
    'style': 'fire', 'center': 0, 'formedAt': 2, 'collapse': {'duration': 5, 'easing': 'easeInSine'},
    'parts': [
        {'type': 'boxes', 'tones': ['#2A1A10', '#B8742A', '#FF6A1A', '#FFE7A0', '#FFB040'], 'glowTones': [2, 3, 4], 'blend': 'translucent',
         'opacity': 0.95, 'shade': True, 'boxes': handle, 'appear': {'delay': 0, 'duration': 1, 'easing': 'linear'}},
        {'type': 'boxes', 'tones': ['#2A1A10', '#B8742A', '#FF6A1A', '#FFE7A0', '#FFB040'], 'glowTones': [2, 3, 4], 'blend': 'translucent',
         'opacity': 0.8, 'shade': True, 'boxes': lash, 'appear': {'delay': 0, 'duration': 2, 'easing': 'easeOutCubic'}},
    ]})
