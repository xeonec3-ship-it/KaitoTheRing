#!/usr/bin/env python3
"""
Текстуры мифических заклинаний (Застывший час, Кровавая луна, Восемь щитов, Взрыв): белое на прозрачном,
цвет задаётся в JSON печати. Рисуются своими штрихами, как в gen_sigil_textures.py (его помощники и берём).

Запуск:  python3 tools/gen_mythic_textures.py   (нужны Pillow и numpy)
Пишет:   src/main/resources/assets/pohsmp_core/textures/sigil/{clock_ornate,hourglass,roman_band,moon_disc,octagram,flame_band}.png
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_sigil_textures import C, SS, W, canvas, draw_roman, polar, ring, roman, save  # noqa: E402


def clock_ornate():
    """Главный циферблат Застывшего часа: два кольца римских цифр, засечки, три малых циферблата внутри, ажурная звезда."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.985, 6 * SS)
    ring(d, C * 0.95, 2 * SS)
    for i in range(120):                                  # засечки по ободу
        a = 2 * math.pi * i / 120
        big = i % 10 == 0
        d.line([*polar(C * (0.88 if big else 0.915), a), *polar(C * 0.95, a)], fill=255, width=(5 if big else 2) * SS)
    ring(d, C * 0.88, 2 * SS)
    for h in range(1, 13):                                # внешнее кольцо цифр
        a = 2 * math.pi * h / 12 - math.pi / 2
        x, y = polar(C * 0.78, a)
        draw_roman(d, x, y, C * 0.1, roman(h), a, 4 * SS)
    ring(d, C * 0.68, 3 * SS)
    ring(d, C * 0.655, 1 * SS)
    for k in range(24):                                   # ажурная 12-лучевая звезда
        a0 = 2 * math.pi * k / 24
        a1 = 2 * math.pi * (k + 5) / 24
        d.line([*polar(C * 0.64, a0), *polar(C * 0.64, a1)], fill=170, width=2 * SS)
    for j in range(3):                                    # три малых циферблата
        a = 2 * math.pi * j / 3 - math.pi / 2
        cx, cy = polar(C * 0.36, a)
        r = C * 0.17
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=255, width=3 * SS)
        for t in range(12):
            b = 2 * math.pi * t / 12
            d.line([cx + math.cos(b) * r * 0.78, cy + math.sin(b) * r * 0.78, cx + math.cos(b) * r * 0.95, cy + math.sin(b) * r * 0.95],
                   fill=255, width=2 * SS)
        b = a + 1.1 * (j + 1)
        d.line([cx, cy, cx + math.cos(b) * r * 0.7, cy + math.sin(b) * r * 0.7], fill=255, width=3 * SS)
    ring(d, C * 0.12, 4 * SS)
    ring(d, C * 0.05, 3 * SS)
    save(img, 'clock_ornate')


def hourglass():
    """Песочные часы в круге: рамка, колбы, струйка песка и горка внизу."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.96, 4 * SS)
    ring(d, C * 0.9, 2 * SS)
    w, h, neck = C * 0.36, C * 0.62, C * 0.05
    top, bot = C - h, C + h
    d.line([C - w - 30 * SS, top, C + w + 30 * SS, top], fill=255, width=7 * SS)
    d.line([C - w - 30 * SS, bot, C + w + 30 * SS, bot], fill=255, width=7 * SS)
    for s in (-1, 1):
        d.line([C + s * (w + 18 * SS), top, C + s * (w + 18 * SS), bot], fill=200, width=4 * SS)
    glass = [(C - w, top + 14 * SS), (C - neck, C), (C - w, bot - 14 * SS)]
    d.line(glass, fill=255, width=4 * SS)
    d.line([(2 * C - x, y) for x, y in glass], fill=255, width=4 * SS)
    d.polygon([(C - w * 0.55, top + h * 0.45), (C + w * 0.55, top + h * 0.45), (C, C - 10 * SS)], fill=150)   # песок сверху
    d.line([C, C, C, bot - h * 0.32], fill=255, width=3 * SS)                                                  # струйка
    d.polygon([(C - w * 0.8, bot - 16 * SS), (C + w * 0.8, bot - 16 * SS), (C, bot - h * 0.34)], fill=190)   # горка
    save(img, 'hourglass')


def roman_band():
    """Полоса для слоя band (repeat 1): двенадцать римских цифр I…XII с засечками минут — циферблат на земле."""
    bw, bh = 2048 * SS, 128 * SS
    img = canvas(bw, bh)
    d = ImageDraw.Draw(img)
    d.line([0, 8 * SS, bw, 8 * SS], fill=255, width=4 * SS)
    d.line([0, 22 * SS, bw, 22 * SS], fill=180, width=2 * SS)
    d.line([0, bh - 10 * SS, bw, bh - 10 * SS], fill=255, width=3 * SS)
    for t in range(60):                                   # засечки минут вдоль верхней линии
        x = bw * (t + 0.5) / 60
        d.line([x, 8 * SS, x, (36 if t % 5 == 2 else 24) * SS], fill=255, width=(6 if t % 5 == 2 else 2) * SS)
    for h in range(12):
        draw_roman(d, bw * (h + 0.5) / 12, bh * 0.62, bh * 0.42, roman(h + 1)[::-1], math.pi / 2, 5 * SS)
    save(img, 'roman_band', (2048, 128))


def moon_disc():
    """Полная луна: мягкий диск с кратерами и тонким светлым краем (цвет — в JSON, для Кровавой луны красный)."""
    y, x = np.mgrid[0:W, 0:W].astype(np.float32)
    nx, ny = (x - C) / C, (y - C) / C
    r = np.hypot(nx, ny)
    disc = np.clip((0.82 - r) / 0.01, 0, 1)
    shade = 0.75 + 0.25 * np.clip(1 - np.hypot(nx + 0.25, ny + 0.25) / 0.9, 0, 1)
    val = disc * shade
    rng = np.random.default_rng(5)
    for _ in range(26):                                   # кратеры: тёмное пятно с ярким краем
        cx, cy = rng.uniform(-0.6, 0.6, 2)
        if math.hypot(cx, cy) > 0.7:
            continue
        cr = rng.uniform(0.04, 0.14)
        dd = np.hypot(nx - cx, ny - cy) / cr
        val -= disc * 0.35 * np.clip(1 - dd, 0, 1)
        val += disc * 0.18 * np.exp(-((dd - 1) ** 2) * 30)
    val += np.exp(-((r - 0.83) ** 2) * 900) * 0.9         # светлый край
    img = Image.fromarray((np.clip(val, 0, 1) * 255).astype(np.uint8), 'L')
    save(img, 'moon_disc')


def octagram():
    """Восьмиконечная звезда из двух квадратов, восьмиугольник и восемь малых щитов-ромбов по ободу (Восемь щитов)."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.97, 4 * SS)
    ring(d, C * 0.9, 2 * SS)
    for rot in (0, math.pi / 4):
        pts = [polar(C * 0.86, rot + k * math.pi / 2) for k in range(4)]
        d.line(pts + [pts[0]], fill=255, width=5 * SS)
    pts = [polar(C * 0.6, math.pi / 8 + k * math.pi / 4) for k in range(8)]
    d.line(pts + [pts[0]], fill=255, width=3 * SS)
    for k in range(8):                                    # малые щиты по ободу
        a = k * math.pi / 4
        cx, cy = polar(C * 0.935, a)
        s = C * 0.05
        d.polygon([(cx + math.cos(a) * s, cy + math.sin(a) * s), (cx + math.cos(a + 1.57) * s * 0.7, cy + math.sin(a + 1.57) * s * 0.7),
                   (cx - math.cos(a) * s, cy - math.sin(a) * s), (cx + math.cos(a - 1.57) * s * 0.7, cy + math.sin(a - 1.57) * s * 0.7)], fill=255)
    ring(d, C * 0.3, 3 * SS)
    for k in range(8):
        a = k * math.pi / 4
        d.line([*polar(C * 0.3, a), *polar(C * 0.6, a + math.pi / 8)], fill=200, width=2 * SS)
    ring(d, C * 0.08, 5 * SS)
    save(img, 'octagram')


def flame_band():
    """Полоса языков пламени для слоя band (Взрыв, Падение небес): языки разной высоты, растут к внешнему краю (v = 0)."""
    bw, bh = 1024 * SS, 128 * SS
    img = canvas(bw, bh)
    d = ImageDraw.Draw(img)
    rng = random.Random(3)
    n = 14
    cell = bw / n
    for i in range(n):
        cx = i * cell + cell / 2
        hgt = bh * rng.uniform(0.55, 0.92)
        wd = cell * rng.uniform(0.28, 0.4)
        base = bh * 0.94
        tip = (cx + rng.uniform(-0.15, 0.15) * cell, base - hgt)
        pts = [(cx - wd, base)]
        for k in range(1, 6):
            t = k / 6
            pts.append((cx - wd * (1 - t) + math.sin(t * 5 + i) * wd * 0.2, base - hgt * t))
        pts.append(tip)
        for k in range(5, 0, -1):
            t = k / 6
            pts.append((cx + wd * (1 - t) + math.sin(t * 4 + i) * wd * 0.2, base - hgt * t))
        pts.append((cx + wd, base))
        d.polygon(pts, fill=150)
        d.line(pts, fill=255, width=4 * SS)
    d.line([0, bh * 0.95, bw, bh * 0.95], fill=255, width=5 * SS)
    save(img, 'flame_band', (1024, 128))


if __name__ == '__main__':
    clock_ornate()
    hourglass()
    roman_band()
    moon_disc()
    octagram()
    flame_band()
