#!/usr/bin/env python3
"""
Текстуры для системы печатей (docs/specs/sigils_spec.md): белое на прозрачном, цвет задаётся в JSON печати.
Рисуется в 4 раза крупнее и уменьшается — края гладкие. Руны свои: глифы собираются из штрихов по сетке узлов (seed).

Запуск:  python3 tools/gen_sigil_textures.py   (нужны Pillow и numpy)
Пишет:   src/main/resources/assets/pohsmp_core/textures/sigil/*.png
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'textures', 'sigil')
SIZE, SS = 512, 4                      # итоговый размер и сверхвыборка
W = SIZE * SS
C = W / 2


def canvas(w=W, h=W):
    return Image.new('L', (w, h), 0)


def save(img, name, size=(SIZE, SIZE), blur=0.0):
    small = img.resize(size, Image.LANCZOS)
    if blur:
        small = small.filter(ImageFilter.GaussianBlur(blur))
    rgba = Image.new('RGBA', size, (255, 255, 255, 0))
    rgba.putalpha(small)
    os.makedirs(OUT, exist_ok=True)
    rgba.save(os.path.join(OUT, name + '.png'))
    print('wrote', name, size)


def ring(d, r, width, fill=255):
    d.ellipse([C - r, C - r, C + r, C + r], outline=fill, width=int(width))


def polar(r, a):
    return C + r * math.cos(a), C + r * math.sin(a)


# ------------------------------------------------------------------ руны
NODES = [(x, y) for y in range(4) for x in range(3)]            # сетка 3×4


def glyph(rng):
    """Глиф: 3–5 штрихов между соседними узлами + иногда точка или дуга."""
    strokes = []
    spine_x = rng.choice([0, 1, 2])
    strokes.append(((spine_x, 0), (spine_x, 3)))                # вертикальная основа — руны читаются как один алфавит
    for _ in range(rng.randint(2, 4)):
        a = rng.choice(NODES)
        b = (min(2, max(0, a[0] + rng.choice([-1, 0, 1]))), min(3, max(0, a[1] + rng.choice([-1, 1]))))
        if a != b:
            strokes.append((a, b))
    dot = rng.random() < 0.35
    return strokes, dot


def draw_glyph(d, x0, y0, w, h, g, width):
    strokes, dot = g
    sx, sy = w / 2.0, h / 3.0
    for (ax, ay), (bx, by) in strokes:
        d.line([x0 + ax * sx, y0 + ay * sy, x0 + bx * sx, y0 + by * sy], fill=255, width=int(width))
        for px, py in ((ax, ay), (bx, by)):                     # скруглённые концы
            r = width / 2
            d.ellipse([x0 + px * sx - r, y0 + py * sy - r, x0 + px * sx + r, y0 + py * sy + r], fill=255)
    if dot:
        r = width * 0.9
        d.ellipse([x0 + w + r * 1.5 - r, y0 + h / 2 - r, x0 + w + r * 1.5 + r, y0 + h / 2 + r], fill=255)


def rune_band():
    """Полоса рун для слоя band: 1024×128, повторяется по окружности. Сверху и снизу тонкие линии."""
    bw, bh = 1024 * SS, 128 * SS
    img = canvas(bw, bh)
    d = ImageDraw.Draw(img)
    rng = random.Random(7)
    line = 3 * SS
    d.line([0, 10 * SS, bw, 10 * SS], fill=255, width=line)
    d.line([0, bh - 10 * SS, bw, bh - 10 * SS], fill=255, width=line)
    n = 12
    cell = bw / n
    for i in range(n):
        gw, gh = cell * 0.42, bh * 0.52
        draw_glyph(d, i * cell + (cell - gw) / 2, (bh - gh) / 2, gw, gh, glyph(rng), 5 * SS)
    save(img, 'rune_band', (1024, 128))


# ------------------------------------------------------------------ кольца и диски
def glow():
    y, x = np.mgrid[0:SIZE, 0:SIZE]
    r = np.hypot(x - SIZE / 2 + 0.5, y - SIZE / 2 + 0.5) / (SIZE / 2)
    a = np.clip(np.exp(-(r ** 2) * 4.0) - np.exp(-4.0), 0, 1) / (1 - math.exp(-4.0))
    img = Image.fromarray((a * 255).astype(np.uint8), 'L')
    rgba = Image.new('RGBA', (SIZE, SIZE), (255, 255, 255, 0))
    rgba.putalpha(img)
    os.makedirs(OUT, exist_ok=True)
    rgba.save(os.path.join(OUT, 'glow.png'))
    print('wrote glow')


def thin_ring():
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.96, 5 * SS)
    save(img, 'thin_ring')


def rim():
    """Внешний обод: двойная линия, засечки, ромбы на сторонах света."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.97, 5 * SS)
    ring(d, C * 0.88, 3 * SS)
    for i in range(72):
        a = 2 * math.pi * i / 72
        long_tick = i % 6 == 0
        r0 = C * (0.885 if long_tick else 0.9)
        r1 = C * (0.965 if long_tick else 0.93)
        d.line([*polar(r0, a), *polar(r1, a)], fill=255, width=(4 if long_tick else 2) * SS)
    for i in range(8):
        a = 2 * math.pi * i / 8 + math.pi / 8
        cx, cy = polar(C * 0.925, a)
        s = C * 0.03
        d.polygon([(cx + s * math.cos(a), cy + s * math.sin(a)), (cx + s * math.cos(a + 1.57), cy + s * math.sin(a + 1.57)),
                   (cx - s * math.cos(a), cy - s * math.sin(a)), (cx - s * math.cos(a + 1.57), cy - s * math.sin(a + 1.57))], fill=255)
    save(img, 'rim')


def spiral_ring():
    """Кольцо «бегущих завитков» (витрувианская волна) между двумя тонкими окружностями."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.95, 4 * SS)
    ring(d, C * 0.62, 4 * SS)
    n = 10
    mid, s = C * 0.785, C * 0.12
    period = 2 * math.pi / n
    for i in range(n):
        base = 2 * math.pi * i / n
        er = (math.cos(base), math.sin(base))
        et = (-math.sin(base), math.cos(base))
        cx, cy = polar(mid, base)
        pts = []
        # подъём: от внутреннего края позади завитка к его внешней вершине, плавной S-кривой
        for k in range(40):
            u = k / 39
            sm = u * u * (3 - 2 * u)
            pts.append(polar(mid - s * 0.95 + (2 * s * 0.95) * sm, base - period * 0.62 * (1 - u)))
        # завиток: от внешней вершины вперёд, вниз и внутрь
        for k in range(1, 110):
            th = k / 109 * 2.25 * math.pi
            rho = s * (1 - 0.82 * k / 109)
            px = cx + rho * (math.cos(th) * er[0] + math.sin(th) * et[0])
            py = cy + rho * (math.cos(th) * er[1] + math.sin(th) * et[1])
            pts.append((px, py))
        d.line(pts, fill=255, width=6 * SS, joint='curve')
    save(img, 'spiral_ring')


def core():
    """Ядро-мандала: лепестки, вложенные кольца, точка в центре."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.95, 5 * SS)
    ring(d, C * 0.55, 4 * SS)
    ring(d, C * 0.2, 4 * SS)
    d.ellipse([C - C * 0.07, C - C * 0.07, C + C * 0.07, C + C * 0.07], fill=255)
    for i in range(8):                                           # лепестки
        a = 2 * math.pi * i / 8
        tip, l, rr = polar(C * 0.9, a), polar(C * 0.32, a - 0.32), polar(C * 0.32, a + 0.32)
        d.line([l, tip, rr], fill=255, width=4 * SS)
        d.line([*polar(C * 0.22, a), *polar(C * 0.5, a)], fill=255, width=3 * SS)
    for i in range(16):                                          # точки между лепестками
        a = 2 * math.pi * (i + 0.5) / 16
        x, y = polar(C * 0.73, a)
        r = C * 0.022
        d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    save(img, 'core')


def spokes():
    """Лучи от центра, к концам тоньше."""
    img = canvas()
    d = ImageDraw.Draw(img)
    for i in range(24):
        a = 2 * math.pi * i / 24
        w = (10 if i % 3 == 0 else 5) * SS
        r1 = C * (0.97 if i % 3 == 0 else 0.8)
        d.polygon([polar(C * 0.08, a - 0.02), polar(r1, a), polar(C * 0.08, a + 0.02)], fill=255)
    save(img, 'spokes', blur=0.4)


def coven_geo():
    """Ковен: геометрия — вложенные многоугольники и гексаграмма, вершины с кружками."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.96, 4 * SS)
    ring(d, C * 0.9, 2 * SS)

    def poly(n, r, rot, width):
        pts = [polar(r, rot + 2 * math.pi * k / n) for k in range(n)]
        d.line(pts + [pts[0]], fill=255, width=width * SS, joint='curve')
        return pts
    tri1 = poly(3, C * 0.9, -math.pi / 2, 4)
    poly(3, C * 0.9, math.pi / 2, 4)
    poly(6, C * 0.52, 0, 3)
    poly(6, C * 0.52, math.pi / 6, 2)
    ring(d, C * 0.45, 3 * SS)
    for x, y in [polar(C * 0.9, -math.pi / 2 + k * math.pi / 3) for k in range(6)]:
        r = C * 0.045
        d.ellipse([x - r, y - r, x + r, y + r], outline=255, width=3 * SS)
    for k in range(3):                                           # линии от вершин к центру
        a = -math.pi / 2 + 2 * math.pi * k / 3
        d.line([*polar(C * 0.45, a), *polar(C * 0.84, a)], fill=255, width=2 * SS)
    r = C * 0.1
    d.ellipse([C - r, C - r, C + r, C + r], outline=255, width=4 * SS)
    save(img, 'coven_geo')


def arc_strip():
    """Полоса для слоя arcs: яркая линия по центру с мягкими краями, 256×32 (растягивается вдоль дуги)."""
    v = np.linspace(-1, 1, 32)
    col = np.clip(1.15 - np.abs(v) * 1.6, 0, 1) ** 1.6
    a = np.tile(col[:, None], (1, 256))
    rgba = Image.new('RGBA', (256, 32), (255, 255, 255, 0))
    rgba.putalpha(Image.fromarray((a * 255).astype(np.uint8), 'L'))
    os.makedirs(OUT, exist_ok=True)
    rgba.save(os.path.join(OUT, 'arc_strip.png'))
    print('wrote arc_strip')


# ------------------------------------------------------------------ тематические печати по школам
def roman(n):
    vals = [(10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
    out = ''
    for v, sym in vals:
        while n >= v:
            out += sym
            n -= v
    return out


def draw_roman(d, cx, cy, h, text, ang, width):
    """Римские цифры штрихами (без шрифтов), повёрнуты к центру циферблата."""
    w = h * 0.5
    total = len(text) * w * 0.9
    ux, uy = math.cos(ang + math.pi / 2), math.sin(ang + math.pi / 2)    # вдоль строки
    vx, vy = -math.cos(ang), -math.sin(ang)                                # «вверх» буквы — к центру
    x0 = -total / 2
    for ch in text:
        def P(a, b):
            return (cx + ux * (x0 + a * w) + vx * (b * h - h / 2), cy + uy * (x0 + a * w) + vy * (b * h - h / 2))
        if ch == 'I':
            d.line([P(0.4, 0), P(0.4, 1)], fill=255, width=width)
        elif ch == 'V':
            d.line([P(0, 1), P(0.4, 0), P(0.8, 1)], fill=255, width=width)
        elif ch == 'X':
            d.line([P(0, 0), P(0.8, 1)], fill=255, width=width)
            d.line([P(0.8, 0), P(0, 1)], fill=255, width=width)
        x0 += w * 0.9


def clock_face():
    """Время: циферблат с римскими цифрами, засечками минут и внутренним кольцом."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.97, 5 * SS)
    ring(d, C * 0.9, 2 * SS)
    ring(d, C * 0.58, 3 * SS)
    ring(d, C * 0.08, 4 * SS)
    for i in range(60):
        a = 2 * math.pi * i / 60 - math.pi / 2
        big = i % 5 == 0
        d.line([*polar(C * (0.9 if big else 0.92), a), *polar(C * 0.97, a)], fill=255, width=(5 if big else 2) * SS)
    for h in range(1, 13):
        a = 2 * math.pi * h / 12 - math.pi / 2
        x, y = polar(C * 0.74, a)
        draw_roman(d, x, y, C * 0.13, roman(h), a, 4 * SS)
    save(img, 'clock_face')


def clock_hand(name, length, width, tail):
    """Стрелка из центра вверх (на 12 часов): ромбовидная, с хвостом и кольцом у оси."""
    img = canvas()
    d = ImageDraw.Draw(img)
    tip, back = (C, C - C * length), (C, C + C * tail)
    wd = C * width
    d.polygon([tip, (C + wd, C - C * 0.12), back, (C - wd, C - C * 0.12)], fill=255)
    r = C * 0.06
    d.ellipse([C - r, C - r, C + r, C + r], outline=255, width=3 * SS)
    save(img, name)


def gear():
    """Шестерёнка: зубья по ободу, спицы и ступица (кладётся слоями поверх циферблата)."""
    img = canvas()
    d = ImageDraw.Draw(img)
    n = 18
    pts = []
    for k in range(n * 4):
        a = 2 * math.pi * k / (n * 4)
        r = C * (0.95 if (k % 4) in (1, 2) else 0.82)
        pts.append(polar(r, a))
    d.line(pts + [pts[0]], fill=255, width=4 * SS)
    ring(d, C * 0.7, 3 * SS)
    ring(d, C * 0.18, 4 * SS)
    for k in range(6):
        a = 2 * math.pi * k / 6
        d.line([*polar(C * 0.18, a), *polar(C * 0.7, a)], fill=255, width=4 * SS)
    save(img, 'gear')


def constellation():
    """Звёзды: орбиты-эллипсы, созвездия из точек и линий по кольцу."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.96, 3 * SS)
    for k in range(3):                                           # наклонённые орбиты
        rot = k * math.pi / 3
        pts = [(C + C * 0.82 * math.cos(t) * math.cos(rot) - C * 0.32 * math.sin(t) * math.sin(rot),
                C + C * 0.82 * math.cos(t) * math.sin(rot) + C * 0.32 * math.sin(t) * math.cos(rot))
               for t in [2 * math.pi * i / 180 for i in range(181)]]
        d.line(pts, fill=200, width=2 * SS)
    rng = random.Random(11)
    for g in range(7):                                           # 7 созвездий по кольцу
        base = 2 * math.pi * g / 7
        stars = [polar(C * (0.6 + 0.3 * rng.random()), base + (rng.random() - 0.5) * 0.7) for _ in range(rng.randint(4, 6))]
        stars.sort(key=lambda p: math.atan2(p[1] - C, p[0] - C))
        d.line(stars, fill=170, width=2 * SS)
        for (x, y) in stars:
            r = C * (0.012 + 0.018 * rng.random())
            d.polygon(star(4, r * 0.4, r * 2.2, rng.random()) if False else [(x - r, y), (x, y - r * 2), (x + r, y), (x, y + r * 2)], fill=255)
            d.polygon([(x - r * 2, y), (x, y - r), (x + r * 2, y), (x, y + r)], fill=255)
    r = C * 0.06
    d.ellipse([C - r, C - r, C + r, C + r], fill=255)
    save(img, 'constellation')


def divine_sun():
    """Божественная: солнце — лучи-клинья чередуются с тонкими, двойной нимб, перья-лепестки внутри."""
    img = canvas()
    d = ImageDraw.Draw(img)
    for k in range(24):
        a = 2 * math.pi * k / 24
        if k % 2 == 0:
            d.polygon([polar(C * 0.6, a - 0.07), polar(C * 0.98, a), polar(C * 0.6, a + 0.07)], fill=255)
        else:
            d.line([*polar(C * 0.62, a), *polar(C * 0.86, a)], fill=200, width=3 * SS)
    ring(d, C * 0.58, 5 * SS)
    ring(d, C * 0.52, 2 * SS)
    for k in range(12):                                          # лепестки-перья
        a = 2 * math.pi * k / 12
        d.line([polar(C * 0.16, a - 0.18), polar(C * 0.46, a), polar(C * 0.16, a + 0.18)], fill=255, width=3 * SS)
    ring(d, C * 0.14, 4 * SS)
    save(img, 'divine_sun')


def higher_cracks():
    """Высшая: рваные трещины от центра, остриё-клинки по кольцу."""
    img = canvas()
    d = ImageDraw.Draw(img)
    rng = random.Random(5)
    for k in range(9):
        a = 2 * math.pi * k / 9 + rng.random() * 0.3
        pts, r = [(C, C)], 0.0
        while r < 0.9:
            r += 0.08 + rng.random() * 0.12
            a += (rng.random() - 0.5) * 0.5
            pts.append(polar(C * r, a))
            if rng.random() < 0.3 and r > 0.3:                   # ответвление
                b = a + (0.4 if rng.random() < 0.5 else -0.4)
                d.line([pts[-1], polar(C * min(0.95, r + 0.18), b)], fill=200, width=2 * SS)
        d.line(pts, fill=255, width=4 * SS, joint='curve')
    for k in range(12):                                          # клинки по кольцу
        a = 2 * math.pi * k / 12
        d.polygon([polar(C * 0.78, a - 0.05), polar(C * 0.98, a + 0.08), polar(C * 0.84, a + 0.03)], fill=255)
    ring(d, C * 0.78, 3 * SS)
    save(img, 'higher_cracks')


def holy_seal():
    """Святая печать (Дезинтеграция): двенадцатиконечная звезда из двух шестиугольников, кольцо рун-засечек, крест в центре."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.97, 4 * SS)
    ring(d, C * 0.92, 2 * SS)
    for k in range(48):                                          # засечки между ободами
        a = 2 * math.pi * k / 48
        d.line([*polar(C * 0.92, a), *polar(C * (0.97 if k % 4 == 0 else 0.945), a)], fill=255, width=2 * SS)
    for rot in (0, math.pi / 6):                                 # двенадцатиконечная звезда: два шестиугольных «звёздных» хода
        pts = [polar(C * 0.86, rot + 2 * math.pi * k * 5 / 12) for k in range(13)]
        d.line(pts, fill=255, width=3 * SS, joint='curve')
    ring(d, C * 0.5, 4 * SS)
    ring(d, C * 0.44, 2 * SS)
    for k in range(4):                                           # крест
        a = math.pi / 2 * k
        d.polygon([polar(C * 0.08, a - 0.4), polar(C * 0.42, a), polar(C * 0.08, a + 0.4)], fill=255)
    r = C * 0.06
    d.ellipse([C - r, C - r, C + r, C + r], fill=255)
    for k in range(12):                                          # точки на концах лучей
        x, y = polar(C * 0.86, 2 * math.pi * k / 12)
        rr = C * 0.022
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=255)
    save(img, 'holy_seal')


def wave_ring():
    """Волнистое (зубчатое) кольцо: двойная синусоида по окружности, как в башне Дезинтеграции."""
    img = canvas()
    d = ImageDraw.Draw(img)
    for base, amp, w in ((0.86, 0.06, 5), (0.8, 0.04, 2)):
        pts = []
        for k in range(721):
            a = 2 * math.pi * k / 720
            pts.append(polar(C * (base + amp * math.sin(a * 24)), a))
        d.line(pts, fill=255, width=w * SS, joint='curve')
    ring(d, C * 0.7, 2 * SS)
    save(img, 'wave_ring')


def cross_spikes():
    """Двенадцатиугольная рама с четырьмя шипами наружу, на концах — кресты."""
    img = canvas()
    d = ImageDraw.Draw(img)
    pts = [polar(C * 0.62, 2 * math.pi * k / 12 + math.pi / 12) for k in range(13)]
    d.line(pts, fill=255, width=4 * SS, joint='curve')
    ring(d, C * 0.56, 2 * SS)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        d.line([*polar(C * 0.62, a), *polar(C * 0.92, a)], fill=255, width=4 * SS)
        cx, cy = polar(C * 0.86, a)
        t = (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2))
        L = C * 0.07
        d.line([cx - t[0] * L, cy - t[1] * L, cx + t[0] * L, cy + t[1] * L], fill=255, width=4 * SS)
        rr = C * 0.025
        x2, y2 = polar(C * 0.95, a)
        d.ellipse([x2 - rr, y2 - rr, x2 + rr, y2 + rr], fill=255)
    save(img, 'cross_spikes')


def star_ring():
    """Кольцо из двенадцати четырёхконечных звёзд — венец башни."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.62, 2 * SS)
    for k in range(12):
        x, y = polar(C * 0.78, 2 * math.pi * k / 12)
        r = C * 0.11
        pts = []
        for j in range(8):
            rr = r if j % 2 == 0 else r * 0.28
            a = j * math.pi / 4 - math.pi / 2
            pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
        d.polygon(pts, fill=255)
    save(img, 'star_ring')


def tooth_band():
    """Полоса жёлтых брусьев-зубьев для колеса верхней печати Дезинтеграции (слой band)."""
    bw, bh = 1024 * SS, 128 * SS
    img = canvas(bw, bh)
    d = ImageDraw.Draw(img)
    n = 16
    cell = bw / n
    for i in range(n):
        x0 = i * cell + cell * 0.18
        d.rectangle([x0, bh * 0.12, x0 + cell * 0.5, bh * 0.88], fill=255)
    d.line([0, bh * 0.04, bw, bh * 0.04], fill=180, width=3 * SS)
    d.line([0, bh * 0.96, bw, bh * 0.96], fill=180, width=3 * SS)
    save(img, 'tooth_band', (1024, 128))


def dodeca_ring():
    """Двойной двенадцатиугольник с кругом внутри — средняя печать Дезинтеграции."""
    img = canvas()
    d = ImageDraw.Draw(img)
    for r, w in ((0.95, 5), (0.86, 3)):
        pts = [polar(C * r, 2 * math.pi * k / 12 + math.pi / 12) for k in range(13)]
        d.line(pts, fill=255, width=w * SS, joint='curve')
    ring(d, C * 0.74, 3 * SS)
    ring(d, C * 0.68, 2 * SS)
    for k in range(12):
        a = 2 * math.pi * k / 12 + math.pi / 12
        d.line([*polar(C * 0.74, a), *polar(C * 0.86, a)], fill=200, width=2 * SS)
    save(img, 'dodeca_ring')


def hex_ring():
    """Кольцо шести шестиугольников с волной-цепью — печать заклинателя Дезинтеграции."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.97, 4 * SS)
    pts = [polar(C * (0.8 + 0.035 * math.sin(2 * math.pi * k / 720 * 30)), 2 * math.pi * k / 720) for k in range(721)]
    d.line(pts, fill=230, width=4 * SS, joint='curve')
    for k in range(6):
        cx, cy = polar(C * 0.8, 2 * math.pi * k / 6 + math.pi / 6)
        r = C * 0.12
        hp = [(cx + r * math.cos(2 * math.pi * j / 6), cy + r * math.sin(2 * math.pi * j / 6)) for j in range(7)]
        d.polygon(hp, fill=0)
        d.line(hp, fill=255, width=5 * SS, joint='curve')
    ring(d, C * 0.62, 3 * SS)
    save(img, 'hex_ring')


def beam_fade():
    """Вертикальная полоса луча: яркая внизу, гаснет кверху (64×256)."""
    y = np.linspace(0, 1, 256)[:, None]
    x = np.linspace(-1, 1, 64)[None, :]
    a = np.clip(1 - np.abs(x) ** 2, 0, 1) * np.clip(1 - y ** 1.6, 0, 1)
    rgba = Image.new('RGBA', (64, 256), (255, 255, 255, 0))
    rgba.putalpha(Image.fromarray((a[::-1] * 255).astype(np.uint8), 'L'))
    os.makedirs(OUT, exist_ok=True)
    rgba.save(os.path.join(OUT, 'beam_fade.png'))
    print('wrote beam_fade')


def chain_band():
    """Запретная: полоса из звеньев цепи для слоя band (1024×128), звенья чередуются плашмя и ребром."""
    bw, bh = 1024 * SS, 128 * SS
    img = canvas(bw, bh)
    d = ImageDraw.Draw(img)
    n = 10
    cell = bw / n
    for i in range(n):
        x = i * cell
        if i % 2 == 0:                                           # плашмя: овал
            d.ellipse([x - cell * 0.1, bh * 0.25, x + cell * 1.1, bh * 0.75], outline=255, width=7 * SS)
        else:                                                    # ребром: перемычка
            d.line([x - cell * 0.15, bh / 2, x + cell * 1.15, bh / 2], fill=255, width=9 * SS)
    save(img, 'chain_band', (1024, 128))


# ------------------------------------------------------------------ спрайты частиц для эффектов (textures/fx/)
FX_OUT = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'textures', 'fx')


def save_fx(img, name, size=128, blur=0.0):
    small = img.resize((size, size), Image.LANCZOS)
    if blur:
        small = small.filter(ImageFilter.GaussianBlur(blur))
    rgba = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    rgba.putalpha(small)
    os.makedirs(FX_OUT, exist_ok=True)
    rgba.save(os.path.join(FX_OUT, name + '.png'))
    print('wrote fx/' + name)


def star(points, inner, outer, rot=0.0):
    pts = []
    for k in range(points * 2):
        r = outer if k % 2 == 0 else inner
        a = rot + math.pi * k / points
        pts.append(polar(r, a))
    return pts


def fx_sprites():
    # мягкая искра: четырёхлучевая звезда с ореолом
    img = canvas()
    d = ImageDraw.Draw(img)
    d.polygon(star(4, C * 0.12, C * 0.95, -math.pi / 2), fill=255)
    halo = Image.new('L', (W, W), 0)
    ImageDraw.Draw(halo).ellipse([C - C * 0.45, C - C * 0.45, C + C * 0.45, C + C * 0.45], fill=110)
    halo = halo.filter(ImageFilter.GaussianBlur(C * 0.18))
    img = Image.fromarray(np.maximum(np.array(img), np.array(halo)))
    save_fx(img, 'spark_soft', blur=0.6)
    # острая искра: тонкие длинные лучи
    img = canvas()
    d = ImageDraw.Draw(img)
    d.polygon(star(4, C * 0.05, C * 0.98, -math.pi / 2), fill=255)
    d.polygon(star(4, C * 0.04, C * 0.5, -math.pi / 4), fill=200)
    save_fx(img, 'spark_sharp')
    # перо: изогнутый стержень, асимметричное опахало (узкое и широкое), пушистое основание
    img = canvas()
    d = ImageDraw.Draw(img)

    def shaft(t):                                                # t: 0 — основание, 1 — кончик; лёгкий изгиб
        return (C + C * 0.28 * math.sin(t * 1.4) - C * 0.1, C * 1.92 - C * 1.82 * t)
    d.line([shaft(k / 40) for k in range(41)], fill=255, width=5 * SS, joint='curve')
    for k in range(34):
        t = 0.18 + 0.8 * k / 33
        x, y = shaft(t)
        env = math.sin(math.pi * min(1, (t - 0.12) / 0.86)) ** 0.7
        wl, wr = C * 0.24 * env, C * 0.4 * env                   # левое опахало уже правого
        d.line([x, y, x - wl, y - C * 0.2], fill=235, width=3 * SS)
        d.line([x, y, x + wr, y - C * 0.12], fill=235, width=3 * SS)
    rng = random.Random(3)
    for k in range(18):                                          # пух у основания
        t = 0.04 + 0.14 * rng.random()
        x, y = shaft(t)
        a0 = math.pi * (0.9 + 0.8 * rng.random()) * (1 if rng.random() < 0.5 else -1)
        L = C * (0.08 + 0.12 * rng.random())
        d.line([x, y, x + L * math.cos(a0), y + L * math.sin(a0) - C * 0.05], fill=150, width=2 * SS)
    save_fx(img, 'feather', blur=0.3)
    # осколок: вытянутый кристалл с яркой гранью
    img = canvas()
    d = ImageDraw.Draw(img)
    shard = [(C, C * 0.06), (C + C * 0.32, C * 0.8), (C + C * 0.12, C * 1.94), (C - C * 0.3, C * 1.1)]
    d.polygon(shard, fill=150)
    d.line([shard[0], shard[1], shard[2]], fill=255, width=7 * SS)
    d.line([shard[0], (C - C * 0.02, C * 1.3)], fill=255, width=4 * SS)
    save_fx(img, 'shard')
    # огонёк души: капля-пламя, ярче к низу
    y, x = np.mgrid[0:W, 0:W].astype(np.float32)
    nx, ny = (x - C) / C, (y - C) / C
    body = np.clip(1 - np.hypot(nx * (1.6 + ny * 0.9), (ny - 0.25) * 1.25), 0, 1)
    img = Image.fromarray((np.clip(body * 1.4, 0, 1) ** 1.3 * 255).astype(np.uint8), 'L')
    save_fx(img, 'soul_mote', blur=0.8)


if __name__ == '__main__':
    glow()
    thin_ring()
    rim()
    spiral_ring()
    core()
    spokes()
    coven_geo()
    rune_band()
    arc_strip()
    fx_sprites()
    clock_face()
    clock_hand('clock_hand_hour', 0.45, 0.05, 0.08)
    clock_hand('clock_hand_minute', 0.72, 0.035, 0.12)
    gear()
    constellation()
    divine_sun()
    higher_cracks()
    chain_band()
    holy_seal()
    wave_ring()
    cross_spikes()
    star_ring()
    tooth_band()
    dodeca_ring()
    hex_ring()
    beam_fade()
