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
