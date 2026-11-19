#!/usr/bin/env python3
"""
Врата для заклинания «Врата» (T03) — по кадрам аниме «Секреты безмолвной ведьмы»: белые резные врата в небе.
- Створки: толстая плита со скруглённой аркой; в арке — окно-роза (кольца, лепестки, спицы), под ней узор из лоз, по фону —
  вертикальные желобки, внизу — две филёнки с крыльями-рельефом; шов между створками светится; над аркой — шпиль с крылатой фигуркой.
- Колонны по бокам: круглые, с желобками, капители и пояса с решёткой; внизу — большие луковицы-волчки, заострённые книзу;
  на колоннах — крылья с закрученными волютами, на макушках — крылатые фигурки.
- Под створками — переплетённые завитки и подвеска: ромб-камень и лезвие-крест вниз.
Проявляются из света сверху вниз.

Пишет fx/meshes/silent_gate.json (рама), silent_gate_door_l/_r.json (створки на петлях), silent_gate_light.json (свет проёма) — часть mesh типа `boxes` (docs/fx.md): бруски [x0, y0, z0, x1, y1, z1, тон] и необязательный
поворот [rx, ry, rz] (градусы, вокруг центра бруска) — в блоках; центр низа створок — (0,0,0), +y вверх, +z — лицом к заклинателю.
Тона: 0 тень, 1 камень, 2 светлый камень, 3 белый, 4 светящееся (бирюза, аддитивно).
Запуск: python3 tools/gen_silent_gate.py
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'fx', 'meshes', 'silent_gate.json')
B = []
GROUP = ['frame']          # текущая группа брусков: 'frame' (рама, колонны, шпиль, подвеска) или 'door' (створки, делятся на левую/правую)
R3 = lambda v: round(v, 3)


def box(x0, y0, z0, x1, y1, z1, t=1, rot=None):
    b = [R3(min(x0, x1)), R3(min(y0, y1)), R3(min(z0, z1)), R3(max(x0, x1)), R3(max(y0, y1)), R3(max(z0, z1)), t]
    if rot and any(abs(a) > 1e-6 for a in rot):
        b.append([R3(a) for a in rot])
    B.append((GROUP[0], b))


def cbox(cx, cy, cz, sx, sy, sz, t=1, rot=None):
    box(cx - sx / 2, cy - sy / 2, cz - sz / 2, cx + sx / 2, cy + sy / 2, cz + sz / 2, t, rot)


def seg(x0, y0, x1, y1, z, w, d, t=1):
    """Брусок-отрезок в плоскости XY на глубине z (толщина w, глубина d)."""
    ln = math.hypot(x1 - x0, y1 - y0)
    cbox((x0 + x1) / 2, (y0 + y1) / 2, z, ln + w * 0.6, w, d, t, [0, 0, math.degrees(math.atan2(y1 - y0, x1 - x0))])


def arc(cx, cy, z, r, a0, a1, w, d, t=1, n=None):
    """Дуга окружности в плоскости XY (углы в градусах, 0 — вправо, 90 — вверх)."""
    n = n or max(4, int(abs(a1 - a0) / 12))
    for i in range(n):
        p = math.radians(a0 + (a1 - a0) * i / n)
        q = math.radians(a0 + (a1 - a0) * (i + 1) / n)
        seg(cx + r * math.cos(p), cy + r * math.sin(p), cx + r * math.cos(q), cy + r * math.sin(q), z, w, d, t)


def curl(cx, cy, z, r0, turns, start, d, t=2, w0=0.22, w1=0.08, cw=1):
    """Волюта: спираль от радиуса r0 внутрь (cw=1 — по часовой)."""
    steps = int(18 * turns)
    pts = []
    for i in range(steps + 1):
        k = i / steps
        a = math.radians(start - cw * 360 * turns * k)
        r = r0 * (1 - 0.82 * k)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a), w0 + (w1 - w0) * k))
    for (x0, y0, w), (x1, y1, _) in zip(pts, pts[1:]):
        seg(x0, y0, x1, y1, z, w, d, t)
    cbox(pts[-1][0], pts[-1][1], z, 0.14, 0.14, d * 1.2, t)


def prism(cx, cz, y0, y1, r, n=16, t=1, flute=0.0, t_alt=None):
    """Цилиндр из n граней (бруски по окружности, поворот вокруг y) и сердцевина; flute — желобки через грань."""
    side = 2 * r * math.tan(math.pi / n) + 0.01
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        rr = r - (flute if i % 2 else 0)
        th = 0.18
        cbox(cx + (rr - th / 2) * math.cos(a), (y0 + y1) / 2, cz + (rr - th / 2) * math.sin(a), th, y1 - y0, side, t_alt if (t_alt is not None and i % 2) else t,
             [0, -math.degrees(a), 0])
    cbox(cx, (y0 + y1) / 2, cz, r * 1.3, y1 - y0, r * 1.3, 0)


def lathe(cx, cz, profile, n=16, t=1):
    """Тело вращения по профилю [(y, r), ...] сверху вниз: кольца-призмы между соседними точками."""
    for (ya, ra), (yb, rb) in zip(profile, profile[1:]):
        r = (ra + rb) / 2
        if r < 0.06:
            cbox(cx, (ya + yb) / 2, cz, 0.08, abs(ya - yb), 0.08, t)
            continue
        prism(cx, cz, min(ya, yb), max(ya, yb), r, n=n, t=t)


def lattice_band(cx, cz, y, r, h, n=16, t=2):
    """Пояс с решёткой: кольцо и косые перекладины крестом."""
    prism(cx, cz, y, y + h, r, n=n, t=t)
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        for sgn in (1, -1):
            cbox(cx + (r + 0.04) * math.cos(a), y + h / 2, cz + (r + 0.04) * math.sin(a), 0.05, h * 1.15, 0.05, 0, [0, -math.degrees(a), sgn * 40])


def feathers(cx, cy, z, side, n, length, spread, base_ang, d=0.25, t=3, rows=2):
    """Крыло: веер перьев (вытянутые бруски), несколько рядов, перо ряда короче."""
    for row in range(rows):
        L = length * (1 - 0.3 * row)
        for i in range(n):
            a = math.radians(base_ang + side * spread * (i / max(1, n - 1)))
            r0 = 0.25 + 0.15 * row
            x0, y0 = cx + side * r0 * math.cos(a) * 0.4, cy + r0 * math.sin(a) * 0.4
            x1, y1 = x0 + math.cos(a) * L * (0.75 + 0.25 * math.sin(math.pi * i / max(1, n - 1))), y0 + math.sin(a) * L * (0.75 + 0.25 * math.sin(math.pi * i / max(1, n - 1)))
            seg(x0, y0, x1, y1, z + 0.06 * row, 0.24 - 0.04 * row, d, t if row == 0 else 2)


def bird(cx, cy, z, s=0.6):
    """Крылатая фигурка на шпиле/колонне: тельце и два приподнятых крыла."""
    cbox(cx, cy, z, 0.35 * s / 0.6, 0.5 * s / 0.6, 0.35, 3)
    cbox(cx, cy + 0.35 * s / 0.6, z + 0.05, 0.22, 0.22, 0.25, 3)
    for side in (-1, 1):
        feathers(cx, cy + 0.05, z, side, 4, 0.9 * s / 0.6, 50, 20 if side > 0 else 160, d=0.12, t=3, rows=1)


def build():
    W, H, D = 3.0, 6.0, 0.6                  # полуширина створок, высота до арки, полутолщина плиты
    AR = W                                    # радиус скругления арки
    # --- плита створок и ступенчатая рамка
    GROUP[0] = 'door'
    box(-W, 0, -D, W, H, D, 2)
    for i in range(14):                       # скруглённая арка ступенями
        y0 = H + AR * i / 14
        y1 = H + AR * (i + 1) / 14
        hw = math.sqrt(max(0, AR * AR - (y0 - H) ** 2))
        box(-hw, y0, -D, hw, y1, D, 2)
    GROUP[0] = 'frame'
    for s in (-1, 1):                                                     # задняя рамка — кольцом вокруг проёма (за ней свет)
        box(s * W, -0.05, -D - 0.15, s * (W + 0.3), H, -D + 0.25, 1)
    arc(0, H, -D + 0.05, AR + 0.15, 0, 180, 0.3, 0.4, 1, n=20)
    arc(0, H, D + 0.06, AR + 0.12, 0, 180, 0.24, 0.3, 3, n=20)          # профиль арки по краю лица (снаружи створок)
    for s in (-1, 1):
        box(s * W, 0, -D, s * (W + 0.24), H, D + 0.2, 3)                 # вертикальные края рамки (снаружи створок)
    GROUP[0] = 'door'
    # --- желобки по фону (вертикальные полоски), шов, оси
    x = -W + 0.45
    while x < W - 0.4:
        if abs(x) > 0.2:
            top = H + math.sqrt(max(0, (AR - 0.4) ** 2 - x * x)) - 0.2
            box(x - 0.035, 2.6, D, x + 0.035, top, D + 0.07, 1)
        x += 0.3
    box(-0.05, 0, D, 0.05, H + AR - 0.1, D + 0.14, 4)                   # светящийся шов между створками
    # --- окно-роза в арке
    RC = (0, H + 0.6)
    for r, w, t in ((1.75, 0.16, 3), (1.25, 0.1, 2), (0.6, 0.12, 3), (0.28, 0.1, 2)):
        arc(RC[0], RC[1], D + 0.14, r, 0, 360, w, 0.16, t, n=28)
    cbox(RC[0], RC[1], D + 0.12, 0.42, 0.42, 0.12, 4, [0, 0, 45])         # светящееся сердце розы
    for i in range(8):                                                   # лепестки — малые кольца между кольцами
        a = math.radians(i * 45 + 22.5)
        arc(RC[0] + 1.5 * math.cos(a), RC[1] + 1.5 * math.sin(a), D + 0.16, 0.24, 0, 360, 0.06, 0.12, 2, n=10)
        a2 = math.radians(i * 45)
        seg(RC[0] + 0.62 * math.cos(a2), RC[1] + 0.62 * math.sin(a2), RC[0] + 1.25 * math.cos(a2), RC[1] + 1.25 * math.sin(a2), D + 0.15, 0.07, 0.12, 2)
    for i in range(12):                                                  # бусины на внешнем кольце
        a = math.radians(i * 30)
        cbox(RC[0] + 1.75 * math.cos(a), RC[1] + 1.75 * math.sin(a), D + 0.22, 0.14, 0.14, 0.12, 3, [0, 0, 45])
    # --- узор из лоз под розой: стебель, симметричные завитки, листья-ромбы
    seg(0, 2.7, 0, RC[1] - 1.75, D + 0.14, 0.1, 0.14, 3)
    for s in (-1, 1):
        for yy, rr in ((3.2, 0.8), (4.1, 0.65), (4.8, 0.5)):
            arc(s * rr * 0.9, yy, D + 0.15, rr, 90 - s * 90 + (0 if s > 0 else 0), 90 - s * 90 + s * 150, 0.08, 0.12, 3, n=8)
            curl(s * (rr * 0.9 + rr * 0.75), yy + rr * 0.55, D + 0.16, 0.22, 1.2, 90 + s * 90, 0.12, 2, 0.08, 0.05, cw=s)
            cbox(s * rr * 1.6, yy - 0.15, D + 0.16, 0.18, 0.28, 0.1, 3, [0, 0, s * 40])
    # --- нижние филёнки с крыльями-рельефом
    for s in (-1, 1):
        xa, xb = s * 0.2, s * (W - 0.35)
        lo, hi = min(xa, xb), max(xa, xb)
        for y in (0.35, 2.35):
            box(lo, y, D, hi, y + 0.1, D + 0.14, 3)
        box(lo, 0.35, D, lo + 0.1, 2.45, D + 0.14, 3)
        box(hi - 0.1, 0.35, D, hi, 2.45, D + 0.14, 3)
        feathers(s * 0.6, 1.0, D + 0.12, s, 5, 1.3, 55, 15 if s > 0 else 165, d=0.1, t=3, rows=2)
        cbox(s * 0.5, 0.6, D + 0.15, 0.1, 0.1, 0.1, 3)
        cbox(s * (W - 0.6), 2.1, D + 0.15, 0.1, 0.1, 0.1, 3)
    # --- шпиль с крылатой фигуркой над аркой
    GROUP[0] = 'frame'
    box(-0.08, H + AR - 0.1, -0.08, 0.08, H + AR + 1.3, 0.08, 3)
    bird(0, H + AR + 0.4, 0.15, 0.7)
    cbox(0, H + AR + 1.4, 0, 0.22, 0.3, 0.22, 4, [0, 45, 0])
    # --- основание и подвеска под створками
    box(-W - 0.2, -0.35, -D - 0.1, W + 0.2, 0.0, D + 0.1, 3)
    for s in (-1, 1):
        curl(s * 1.2, -0.85, D * 0.2, 0.55, 1.3, 90, 0.28, 3, 0.2, 0.08, cw=-s)             # переплетённые завитки
        curl(s * 2.3, -0.75, D * 0.2, 0.45, 1.2, 90, 0.26, 2, 0.18, 0.07, cw=s)
        seg(s * 0.3, -0.35, s * 1.7, -0.45, D * 0.2, 0.18, 0.3, 3)
    cbox(0, -1.0, D * 0.2, 0.7, 0.9, 0.45, 3, [0, 0, 45])                                   # ромб-камень
    cbox(0, -1.0, D * 0.2 + 0.22, 0.38, 0.5, 0.1, 4, [0, 0, 45])
    for k, (w, h) in enumerate(((0.45, 0.6), (0.35, 0.7), (0.24, 0.7), (0.12, 0.6))):       # лезвие вниз
        y = -1.45 - sum(hh for _, hh in ((0.45, 0.6), (0.35, 0.7), (0.24, 0.7), (0.12, 0.6))[:k])
        cbox(0, y - h / 2, D * 0.2, w, h, 0.22, 3)
    cbox(0, -2.1, D * 0.2, 1.3, 0.16, 0.2, 3)                                                # перекладина креста
    for s in (-1, 1):
        cbox(s * 0.75, -2.1, D * 0.2, 0.22, 0.22, 0.2, 3, [0, 0, 45])
    # --- колонны: шахта с желобками, капитель, пояса с решёткой, луковица-волчок с остриём, крылья с волютами
    for s in (-1, 1):
        cx = s * (W + 0.95)
        prism(cx, 0, 0.0, H + 2.8, 0.62, n=16, t=2, flute=0.08, t_alt=1)
        lattice_band(cx, 0, H + 2.8, 0.82, 0.45)
        lathe(cx, 0, [(H + 3.25, 0.9), (H + 3.45, 0.95), (H + 3.6, 0.7)], n=16, t=3)
        bird(cx, H + 3.95, 0, 0.55)
        lattice_band(cx, 0, -0.45, 0.85, 0.45)
        lathe(cx, 0, [(-0.45, 0.95), (-0.75, 1.25), (-1.15, 1.32), (-1.6, 1.15), (-2.1, 0.85), (-2.6, 0.55), (-3.1, 0.3), (-3.6, 0.15), (-4.2, 0.05)], n=16, t=3)
        for y in (-1.15, -2.1):                                                             # грани-кольца на луковице
            prism(cx, 0, y - 0.05, y + 0.05, 1.32 if y > -2 else 0.88, n=16, t=1)
        # крыло с волютой на внешней стороне колонны (вверху) и малое внизу
        curl(cx + s * 0.95, H + 0.9, 0.2, 0.75, 1.35, 270 if s > 0 else 270, 0.4, 3, 0.26, 0.09, cw=-s)
        feathers(cx + s * 0.9, H + 1.5, -0.1, s, 6, 1.6, 70, 15 if s > 0 else 165, d=0.3, t=3, rows=3)
        curl(cx + s * 0.8, 2.6, 0.2, 0.5, 1.2, 90, 0.32, 2, 0.2, 0.08, cw=s)
        feathers(cx + s * 0.8, 2.2, -0.05, s, 4, 0.9, 45, -20 if s > 0 else 200, d=0.22, t=2, rows=2)


def crystals():
    """Ледяная кристаллическая гора (финал «Врат», 64 с): десятки граненых шипов из земли, в центре выше всех, наклонены наружу.
    Каждый шип — шестигранник из брусков, сужается к острию; тона: 2 светлый, 3 белый, 4 светящаяся сердцевина."""
    import random
    rnd = random.Random(64)
    C = []

    def shard(x, z, h, r, lean_x, lean_z):
        n = 6
        segs = 5
        for k in range(segs):
            y0, y1 = h * k / segs, h * (k + 1) / segs
            rr = r * (1 - 0.8 * k / segs)
            cxk, czk = x + lean_x * (y0 + y1) / 2, z + lean_z * (y0 + y1) / 2
            side = 2 * rr * math.tan(math.pi / n) + 0.02
            for i in range(n):
                a = 2 * math.pi * (i + 0.5) / n
                t = 3 if i % 2 == 0 else 2
                b = [R3(cxk + (rr - 0.06) * math.cos(a) - 0.06), R3(y0), R3(czk + (rr - 0.06) * math.sin(a) - side / 2),
                     R3(cxk + (rr - 0.06) * math.cos(a) + 0.06), R3(y1), R3(czk + (rr - 0.06) * math.sin(a) + side / 2), t,
                     [R3(-math.degrees(math.atan(lean_z))), R3(-math.degrees(a)), R3(math.degrees(math.atan(lean_x)))]]
                C.append(b)
            C.append([R3(cxk - rr * 0.5), R3(y0), R3(czk - rr * 0.5), R3(cxk + rr * 0.5), R3(y1), R3(czk + rr * 0.5), 4])
        tip_x, tip_z = x + lean_x * h, z + lean_z * h
        C.append([R3(tip_x - 0.08), R3(h), R3(tip_z - 0.08), R3(tip_x + 0.08), R3(h + r * 0.6), R3(tip_z + 0.08), 3])

    shard(0, 0, 9.0, 1.4, 0, 0)
    for i in range(22):
        a = rnd.uniform(0, 2 * math.pi)
        d = rnd.uniform(0.8, 4.2)
        h = 8.0 * (1 - d / 5.0) * rnd.uniform(0.6, 1.0) + 1.0
        r = rnd.uniform(0.35, 0.9) * (1.2 - d / 6)
        shard(d * math.cos(a), d * math.sin(a), h, r, 0.12 * math.cos(a) * d / 4, 0.12 * math.sin(a) * d / 4)
    ys = [b[1] for b in C] + [b[4] for b in C]
    doc = {
        'comment': 'Ледяная гора — финал «Врат» (T03), по кадру аниме. Сгенерировано tools/gen_silent_gate.py.',
        'style': 'silent', 'center': 0, 'formedAt': 30,
        'collapse': {'duration': 40, 'easing': 'easeInSine'},
        'parts': [{
            'type': 'boxes', 'tones': ['#5E7286', '#9CC4DC', '#CFE8F6', '#F2FAFF', '#9FF4FF'], 'glowTones': [4],
            'blend': 'translucent', 'opacity': 0.82, 'shade': True, 'boxes': C,
            'appear': {'delay': 0, 'duration': 30, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 1.5},
            'bounds': [min(ys), max(ys)]}]}
    out = OUT.replace('silent_gate.json', 'silent_crystal.json')
    json.dump(doc, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'silent_crystal: {len(C)} boxes')


def _split_doors(W):
    """Створки: брусок по центру бруска — в левую (x < 0) или правую; прямые бруски через шов режутся по x = 0."""
    L, R = [], []
    for g, b in B:
        if g != 'door':
            continue
        x0, x1 = b[0], b[3]
        if len(b) == 7 and x0 < -0.001 and x1 > 0.001:
            L.append([x0, b[1], b[2], 0.0] + b[4:])
            R.append([0.0, b[1], b[2], x1] + b[4:])
        elif (x0 + x1) / 2 < 0:
            L.append(b)
        else:
            R.append(b)
    return L, R


def _mesh(name, boxes, comment, appear, tones=None, blend='translucent', opacity=0.95):
    ys = [b[1] for b in boxes] + [b[4] for b in boxes]
    doc = {'comment': comment + ' Сгенерировано tools/gen_silent_gate.py — правьте генератор.', 'style': 'silent', 'center': 0, 'formedAt': appear['duration'],
           'collapse': {'duration': 30, 'easing': 'easeInCubic'},
           'parts': [{'type': 'boxes', 'tones': tones or ['#5E7286', '#9FB2C2', '#C4D3DF', '#EAF1F7', '@primary'], 'glowTones': [4], 'blend': blend,
                      'opacity': opacity, 'shade': True, 'boxes': boxes, 'appear': appear, 'bounds': [min(ys), max(ys)]}]}
    out = os.path.join(os.path.dirname(OUT), name + '.json')
    json.dump(doc, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'{name}: {len(boxes)} boxes')


def main():
    build()
    W, H, D = 3.0, 6.0, 0.6
    reveal = {'delay': 0, 'duration': 100, 'easing': 'easeInOutSine', 'reveal': 'down', 'front': 0.8}
    frame = [b for g, b in B if g == 'frame']
    left, right = _split_doors(W)
    _mesh('silent_gate', frame, 'Врата «Безмолвных врат» (T03): рама, колонны, шпиль, подвеска — без створок (створки — silent_gate_door_l/_r, '
          'петли на x = ∓3, свет проёма — silent_gate_light). Центр низа створок — (0,0,0), +z — к заклинателю.', reveal)
    _mesh('silent_gate_door_l', left, 'Левая створка «Безмолвных врат»: петля — вертикаль x = -3, z = 0; открывается внутрь (от заклинателя), '
          'поворот вокруг петли на +100°.', reveal)
    _mesh('silent_gate_door_r', right, 'Правая створка «Безмолвных врат»: петля — вертикаль x = +3, z = 0; открывается внутрь, поворот на -100°.', reveal)
    light = [[-W, 0, -D - 0.1, W, H, -D + 0.05, 4]]
    for i in range(14):
        y0, y1 = H + W * i / 14, H + W * (i + 1) / 14
        hw = math.sqrt(max(0, W * W - (y0 - H) ** 2))
        light.append([R3(-hw), R3(y0), -D - 0.1, R3(hw), R3(y1), -D + 0.05, 4])
    _mesh('silent_gate_light', light, 'Свет в проёме «Безмолвных врат» — виден, когда створки открываются (белое сияние за ними).',
          {'delay': 0, 'duration': 30, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 1.0},
          tones=['#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFFFF', '#E8FFF8'], blend='additive', opacity=1.0)


if __name__ == '__main__':
    main()
