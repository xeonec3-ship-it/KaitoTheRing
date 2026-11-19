"""Зеркальная темница: модель клетки fx/meshes/mirror_prison.json (куб 3x3x3, как MirrorPrisonSpell HALF=1.5, H=3).

Грани — полупрозрачное серебристое «зеркало», рёбра — светящиеся бруски, на каждой стене две косые полосы-блика
и ромб-печать в центре. Появляется снизу вверх. Запуск: python tools/gen_mirror_prison.py
"""
import json, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
HALF, H, T = 1.5, 3.0, 0.035   # half width, height, pane thickness
E = 0.06                         # edge bar half-thickness


def r(v):
    return round(v, 3)


def box(x0, y0, z0, x1, y1, z1, tone, rot=None):
    b = [r(x0), r(y0), r(z0), r(x1), r(y1), r(z1), tone]
    if rot:
        b.append(rot)
    return b


glass, frame = [], []
# panes: four walls and the roof (tone 0/1 alternate for a faint two-tone sheen)
glass.append(box(-HALF, 0, -HALF - T, HALF, H, -HALF + T, 0))
glass.append(box(-HALF, 0, HALF - T, HALF, H, HALF + T, 1))
glass.append(box(-HALF - T, 0, -HALF, -HALF + T, H, HALF, 1))
glass.append(box(HALF - T, 0, -HALF, HALF + T, H, HALF, 0))
glass.append(box(-HALF, H - T, -HALF, HALF, H + T, HALF, 1))

# edges: 4 verticals, 4 bottom, 4 top
for sx in (-1, 1):
    for sz in (-1, 1):
        frame.append(box(sx * HALF - E, 0, sz * HALF - E, sx * HALF + E, H + E, sz * HALF + E, 2))
for y in (0.0, H):
    for s in (-1, 1):
        frame.append(box(-HALF - E, y - E, s * HALF - E, HALF + E, y + E, s * HALF + E, 2))
        frame.append(box(s * HALF - E, y - E, -HALF - E, s * HALF + E, y + E, HALF + E, 2))


def wall(face, along_rot):
    """Glints and a diamond seal on one wall; face = (nx, nz) outward normal."""
    nx, nz = face
    off = HALF + T + 0.01
    out = []
    for k, (dy, dl) in enumerate(((0.9, -0.4), (1.9, 0.5))):   # two slanted glints
        cx, cz = nx * off + (nz * dl), nz * off + (-nx * dl)
        L, w = 0.9 - 0.25 * k, 0.03
        if nx != 0:
            out.append(box(cx - 0.01, dy - L / 2, cz - w, cx + 0.01, dy + L / 2, cz + w, 3, [35 + 10 * k, along_rot, 0]))
        else:
            out.append(box(cx - w, dy - L / 2, cz - 0.01, cx + w, dy + L / 2, cz + 0.01, 3, [0, along_rot, 35 + 10 * k]))
    # diamond seal: four bars around the centre of the wall, turned 45 degrees
    cx, cz = nx * off, nz * off
    s, w = 0.32, 0.025
    for dy, dl in ((0.23, 0), (-0.23, 0), (0, 0.23), (0, -0.23)):
        px, pz = cx + nz * dl, cz - nx * dl
        if nx != 0:
            out.append(box(px - 0.01, H / 2 + dy - s / 2, pz - w, px + 0.01, H / 2 + dy + s / 2, pz + w, 4, [45, along_rot, 0]))
        else:
            out.append(box(px - w, H / 2 + dy - s / 2, pz - 0.01, px + w, H / 2 + dy + s / 2, pz + 0.01, 4, [0, along_rot, 45]))
    return out


for f in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    frame += wall(f, 0)

APPEAR = {'delay': 0, 'duration': 12, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.6}
mesh = {
    'comment': 'Зеркальная темница: клетка-куб 3x3x3 (MirrorPrisonSpell HALF=1.5, H=3): серебристые зеркальные грани, светящиеся рёбра, '
               'блики и ромб-печать на стенах. Сгенерировано tools/gen_mirror_prison.py.',
    'style': 'higher', 'center': 0, 'formedAt': 12, 'collapse': {'duration': 12, 'easing': 'easeInCubic'},
    'parts': [
        {'type': 'boxes', 'tones': ['#B8CCE0', '#D8E6F4', '#FFFFFF', '#FFFFFF', '#E6F2FF'], 'glowTones': [], 'blend': 'translucent',
         'opacity': 0.32, 'shade': True, 'boxes': glass, 'appear': APPEAR, 'bounds': [0.0, H]},
        {'type': 'boxes', 'tones': ['#B8CCE0', '#D8E6F4', '#DDEBFF', '#FFFFFF', '#BFD8FF'], 'glowTones': [2, 3, 4], 'blend': 'translucent',
         'opacity': 0.9, 'shade': True, 'boxes': frame, 'appear': APPEAR, 'bounds': [0.0, H]},
    ],
}
with open(os.path.join(ROOT, 'fx', 'meshes', 'mirror_prison.json'), 'w', encoding='utf-8') as fh:
    json.dump(mesh, fh, ensure_ascii=False, separators=(',', ':'))
print('wrote fx/meshes/mirror_prison.json:', len(glass), 'panes,', len(frame), 'bars')
