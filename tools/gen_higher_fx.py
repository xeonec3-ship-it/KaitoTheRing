#!/usr/bin/env python3
"""
Высшие заклинания и знаки школ на системе эффектов (docs/fx.md, docs/sigils.md): текстуры печатей, спрайты частиц
и однотипные JSON (знаки 10 школ Iron's, 6 рун Печати запрета, 4 карты Звезды судьбы).
Белое на прозрачном, цвет задаётся в JSON. Хелперы рисования — из tools/gen_sigil_textures.py.

Запуск:  python3 tools/gen_higher_fx.py   (нужны Pillow и numpy)
Пишет:   textures/sigil/{cradle_,fate_,gravity_,event_,seal_,asc_,ashless_,school_}*.png,
         textures/fx/{leaf,drop,snowflake,swirl,crescent,star5}.png,
         sigils/school_*.json, sigils/higher_seal_glyph_*.json, sigils/higher_fate_card_*.json,
         fx/school_*.json, fx/higher_fate_*.json, fx/styles/<школа>.json
Остальные JSON Высших (higher_cradle_*, higher_sing_*, higher_seal_*, higher_asc_*, higher_ashless_*) написаны руками.
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_sigil_textures import (C, OUT, SIZE, SS, W, canvas, draw_glyph, glyph, polar, ring, save, save_fx,  # noqa: E402
                                star)

ASSETS = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
BW, BH = 1024 * SS, 128 * SS          # полоса для слоя band


# ------------------------------------------------------------------ помощники
def lighter(dst, src, x=0, y=0):
    """Кладёт src на dst (оба 'L') по максимуму, левый верхний угол в (x, y)."""
    box = Image.new('L', dst.size, 0)
    box.paste(src, (int(x), int(y)))
    return ImageChops.lighter(dst, box)


def stamp(dst, src, cx, cy, deg):
    """Повёрнутый на deg (против часовой) src с центром в (cx, cy)."""
    r = src.rotate(deg, resample=Image.BICUBIC, expand=True)
    return lighter(dst, r, cx - r.size[0] / 2, cy - r.size[1] / 2)


def disc_ring(d, r, w):
    ring(d, r, w)


def crescent(d, cx, cy, r, phase=0.55, ang=0.0, fill=255):
    """Полумесяц: круг минус сдвинутый круг (phase — сдвиг в долях r)."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    ox, oy = cx + math.cos(ang) * r * phase, cy + math.sin(ang) * r * phase
    rr = r * 0.92
    d.ellipse([ox - rr, oy - rr, ox + rr, oy + rr], fill=0)


def star_at(d, cx, cy, n, inner, outer, rot=-math.pi / 2, fill=255):
    pts = []
    for k in range(n * 2):
        r = outer if k % 2 == 0 else inner
        a = rot + math.pi * k / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=fill)


def flame(w, h, sway=0.35, hollow=True):
    """Язык пламени остриём вверх, картинка 'L' w×h."""
    img = Image.new('L', (int(w), int(h)), 0)
    d = ImageDraw.Draw(img)

    def outline(scale, bright):
        left, right = [], []
        for k in range(41):
            s = k / 40                                            # 0 — основание, 1 — кончик
            hw = w * 0.48 * scale * math.sin(math.pi * (0.08 + 0.92 * (1 - s))) ** 0.8 * (1 - s) ** 0.45
            x = w / 2 + math.sin(s * 3.2) * w * sway * s
            y = h - 1 - s * (h - 2) * (0.62 + 0.38 * scale)
            left.append((x - hw, y))
            right.append((x + hw, y))
        d.polygon(left + right[::-1], fill=bright)
    outline(1.0, 255)
    if hollow:
        outline(0.55, 90)
    return img


def band_lines(d):
    d.line([0, 10 * SS, BW, 10 * SS], fill=255, width=3 * SS)
    d.line([0, BH - 10 * SS, BW, BH - 10 * SS], fill=255, width=3 * SS)


def save_band(img, name):
    save(img, name, (1024, 128))


def glyph_img(seed, w, h, width):
    g = glyph(random.Random(seed))
    img = Image.new('L', (int(w * 1.4), int(h * 1.1)), 0)
    draw_glyph(ImageDraw.Draw(img), w * 0.15, h * 0.05, w, h, g, width)
    return img


def rune_ring(img, r0, r1, n, seed, width=4 * SS):
    """Пояс глифов между радиусами r0 и r1, глифы смотрят к центру."""
    h = (r1 - r0) * 0.7
    for i in range(n):
        a = 2 * math.pi * i / n
        g = glyph_img(seed * 100 + i, h * 0.55, h, width)
        cx, cy = polar((r0 + r1) / 2, a)
        img = stamp(img, g, cx, cy, -math.degrees(a) - 90)
    return img


# ------------------------------------------------------------------ Колыбель кошмара
def cradle_dream():
    """Сон: большой полумесяц в центре, колыбельная спираль, кольцо полумесяцев и звёзд, точечный обод."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.97, 5 * SS)
    ring(d, C * 0.89, 2 * SS)
    for i in range(72):
        x, y = polar(C * 0.93, 2 * math.pi * i / 72)
        r = (7 if i % 9 == 0 else 3.5) * SS
        d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    for i in range(8):
        a = 2 * math.pi * i / 8
        x, y = polar(C * 0.77, a)
        crescent(d, x, y, C * 0.075, 0.5, a + math.pi)
        x, y = polar(C * 0.77, a + math.pi / 8)
        star_at(d, x, y, 4, C * 0.012, C * 0.045)
    ring(d, C * 0.66, 3 * SS)
    for arm in range(3):
        pts = []
        for k in range(120):
            s = k / 119
            r = C * (0.2 + 0.42 * s)
            a = arm * 2 * math.pi / 3 + s * 3.4
            pts.append(polar(r, a))
        d.line(pts, fill=255, width=4 * SS, joint='curve')
    crescent(d, C, C, C * 0.17, 0.48, -math.pi / 4)
    star_at(d, C + C * 0.07, C - C * 0.07, 4, C * 0.008, C * 0.035)
    save(img, 'cradle_dream')


def cradle_moon_band():
    """Фазы луны по кругу: полоса для слоя band."""
    img = canvas(BW, BH)
    d = ImageDraw.Draw(img)
    band_lines(d)
    n = 8
    cell = BW / n
    for i in range(n):
        cx, cy, r = i * cell + cell / 2, BH / 2, BH * 0.27
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=255, width=3 * SS)
        crescent(d, cx, cy, r * 0.86, 0.25 + 1.4 * abs(i - n / 2) / n, 0.0)
    for i in range(n + 1):
        star_at(d, i * cell, BH / 2, 4, BH * 0.02, BH * 0.08, 0)
    save_band(img, 'cradle_moon_band')


# ------------------------------------------------------------------ Звезда судьбы
PENTA = [(0.0, -0.62), (0.59, -0.19), (0.36, 0.5), (-0.36, 0.5), (-0.59, -0.19)]


def fate_constellation():
    """Созвездие-пентаграмма, кольцо двенадцати домов со звёздочками, мелкие созвездия."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.97, 5 * SS)
    ring(d, C * 0.92, 2 * SS)
    for i in range(12):
        a = 2 * math.pi * i / 12
        d.line([*polar(C * 0.78, a), *polar(C * 0.92, a)], fill=255, width=2 * SS)
        x, y = polar(C * 0.85, a + math.pi / 12)
        star_at(d, x, y, 4, C * 0.008, C * 0.03)
    ring(d, C * 0.78, 3 * SS)
    for i in range(48):
        x, y = polar(C * 0.73, 2 * math.pi * i / 48)
        d.ellipse([x - 3 * SS, y - 3 * SS, x + 3 * SS, y + 3 * SS], fill=255)
    pts = [(C + x * C, C + y * C) for x, y in PENTA]
    for k in range(5):
        d.line([pts[k], pts[(k + 2) % 5]], fill=255, width=3 * SS)
    for x, y in pts:
        star_at(d, x, y, 4, C * 0.015, C * 0.075)
        d.ellipse([x - C * 0.03, y - C * 0.03, x + C * 0.03, y + C * 0.03], outline=255, width=2 * SS)
    rng = random.Random(11)
    for g in range(6):
        a0 = 2 * math.pi * g / 6 + 0.5
        base = polar(C * 0.6, a0)
        last = base
        for k in range(3):
            nx, ny = last[0] + (rng.random() - 0.5) * C * 0.16, last[1] + (rng.random() - 0.5) * C * 0.16
            d.line([last, (nx, ny)], fill=170, width=2 * SS)
            d.ellipse([nx - 5 * SS, ny - 5 * SS, nx + 5 * SS, ny + 5 * SS], fill=255)
            last = (nx, ny)
    star_at(d, C, C, 8, C * 0.03, C * 0.11)
    save(img, 'fate_constellation')


def card_frame(d):
    ring(d, C * 0.97, 6 * SS)
    ring(d, C * 0.9, 2 * SS)
    for i in range(4):                                             # углы карты — ромбы на сторонах света
        x, y = polar(C * 0.935, math.pi / 2 * i)
        star_at(d, x, y, 2, C * 0.02, C * 0.05, math.pi / 2 * i)


def fate_card(name):
    img = canvas()
    d = ImageDraw.Draw(img)
    card_frame(d)
    if name == 'sun':
        for i in range(24):
            a = 2 * math.pi * i / 24
            long_ray = i % 2 == 0
            r1 = C * (0.82 if long_ray else 0.6)
            w = C * (0.05 if long_ray else 0.025)
            d.polygon([polar(C * 0.3, a - w / C / 0.3), polar(r1, a), polar(C * 0.3, a + w / C / 0.3)], fill=255)
        d.ellipse([C - C * 0.27, C - C * 0.27, C + C * 0.27, C + C * 0.27], fill=0, outline=255, width=8 * SS)
        d.ellipse([C - C * 0.12, C - C * 0.12, C + C * 0.12, C + C * 0.12], fill=255)
    elif name == 'moon':
        crescent(d, C, C, C * 0.48, 0.45, -math.pi / 5)
        rng = random.Random(5)
        for k in range(9):
            x, y = C + (rng.random() - 0.5) * C * 1.2, C + (rng.random() - 0.5) * C * 1.2
            if math.hypot(x - C, y - C) < C * 0.5 or math.hypot(x - C, y - C) > C * 0.8:
                continue
            star_at(d, x, y, 4, C * 0.01, C * 0.05)
        for k in range(7):                                         # капли росы, как на карте Луны
            x, y = polar(C * 0.62, math.pi * (0.25 + 0.5 * k / 6))
            d.polygon([(x, y - C * 0.05), (x + C * 0.025, y + C * 0.01), (x, y + C * 0.035), (x - C * 0.025, y + C * 0.01)], fill=255)
    elif name == 'tower':
        x0, x1, y0, y1 = C - C * 0.18, C + C * 0.18, C - C * 0.35, C + C * 0.62
        d.rectangle([x0, y0, x1, y1], outline=255, width=7 * SS)
        for k in range(4):                                         # зубцы
            cx = x0 + (x1 - x0) * (k + 0.5) / 4
            d.rectangle([cx - C * 0.03, y0 - C * 0.08, cx + C * 0.03, y0], fill=255)
        for k in range(3):                                         # окна
            cy = y0 + (y1 - y0) * (0.25 + 0.25 * k)
            d.rectangle([C - C * 0.035, cy - C * 0.06, C + C * 0.035, cy + C * 0.06], fill=255)
        bolt = [(C + C * 0.55, C - C * 0.8), (C + C * 0.22, C - C * 0.52), (C + C * 0.35, C - C * 0.5), (C + C * 0.05, C - C * 0.36)]
        d.line(bolt, fill=255, width=9 * SS, joint='curve')
        for k, (dx, dy) in enumerate([(-0.35, -0.2), (0.32, -0.05), (-0.4, 0.15), (0.38, 0.3)]):   # падающие камни
            x, y = C + dx * C, C + dy * C
            s = C * 0.035
            d.polygon([(x - s, y), (x, y - s), (x + s, y), (x, y + s)], fill=255)
    elif name == 'world':
        for k in range(36):                                        # венок из листьев по овалу
            a = 2 * math.pi * k / 36
            x, y = C + math.cos(a) * C * 0.5, C + math.sin(a) * C * 0.66
            leaf = Image.new('L', (int(C * 0.16), int(C * 0.07)), 0)
            ImageDraw.Draw(leaf).ellipse([0, 0, leaf.size[0] - 1, leaf.size[1] - 1], fill=255)
            img = stamp(img, leaf, x, y, -math.degrees(a) + (60 if k % 2 else -60))
        d = ImageDraw.Draw(img)
        star_at(d, C, C, 4, C * 0.05, C * 0.3)
        for i in range(4):
            x, y = polar(C * 0.78, math.pi / 4 + math.pi / 2 * i)
            d.ellipse([x - C * 0.06, y - C * 0.06, x + C * 0.06, y + C * 0.06], outline=255, width=4 * SS)
    save(img, 'fate_card_' + name)


# ------------------------------------------------------------------ Сингулярность
def gravity_well():
    """Колодец: кольца сгущаются к центру, радиальные линии закручены, как сетка, продавленная тяжестью."""
    img = canvas()
    d = ImageDraw.Draw(img)
    r = 0.97
    k = 0
    while r > 0.06:
        ring(d, C * r, max(1, int((5 - k * 0.4) * SS)))
        r *= 0.8
        k += 1
    for i in range(16):
        a0 = 2 * math.pi * i / 16
        pts = [polar(C * (0.06 + 0.91 * s / 60), a0 + 1.6 * (1 - s / 60) ** 2) for s in range(61)]
        d.line(pts, fill=200, width=2 * SS, joint='curve')
    save(img, 'gravity_well')


def gravity_spiral():
    """Аккреционный диск: пять логарифмических рукавов, толще к краю."""
    img = canvas()
    d = ImageDraw.Draw(img)
    for arm in range(5):
        for s in range(160):
            u0, u1 = s / 160, (s + 1) / 160
            r0, r1 = 0.12 + 0.84 * u0, 0.12 + 0.84 * u1
            a0 = arm * 2 * math.pi / 5 + 2.4 * math.log(r0 / 0.12)
            a1 = arm * 2 * math.pi / 5 + 2.4 * math.log(r1 / 0.12)
            w = (2 + 14 * u0 * (1 - u0) * 2) * SS
            d.line([*polar(C * r0, a0), *polar(C * r1, a1)], fill=int(140 + 115 * (1 - u0)), width=int(w))
    ring(d, C * 0.12, 6 * SS)
    save(img, 'gravity_spiral')


def event_ring():
    """Кольцо горизонта событий: тонкое яркое кольцо с ореолом."""
    y, x = np.mgrid[0:SIZE, 0:SIZE]
    r = np.hypot(x - SIZE / 2 + 0.5, y - SIZE / 2 + 0.5) / (SIZE / 2)
    a = np.exp(-((r - 0.78) / 0.025) ** 2) + 0.45 * np.exp(-((r - 0.78) / 0.12) ** 2) + 0.25 * np.exp(-((r - 0.9) / 0.03) ** 2)
    a = np.clip(a, 0, 1) * (r < 0.99)
    rgba = Image.new('RGBA', (SIZE, SIZE), (255, 255, 255, 0))
    rgba.putalpha(Image.fromarray((a * 255).astype(np.uint8), 'L'))
    rgba.save(os.path.join(OUT, 'event_ring.png'))
    print('wrote event_ring')


# ------------------------------------------------------------------ Печать запрета
def seal_ward():
    """Запрет: кольцо рун, гексаграмма с шестью гнёздами-замками на вершинах, в центре — перечёркнутый круг."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.97, 7 * SS)
    ring(d, C * 0.93, 2 * SS)
    ring(d, C * 0.8, 3 * SS)
    img = rune_ring(img, C * 0.8, C * 0.93, 30, 41)
    d = ImageDraw.Draw(img)
    for t in range(2):
        pts = [polar(C * 0.78, math.pi / 3 * (2 * k + t) - math.pi / 2 + math.pi / 6) for k in range(3)]   # вершины на 0°, 60°…
        d.polygon(pts, outline=255, width=4 * SS)
    for k in range(6):
        x, y = polar(C * 0.78, math.pi / 3 * k)
        d.ellipse([x - C * 0.1, y - C * 0.1, x + C * 0.1, y + C * 0.1], fill=0, outline=255, width=5 * SS)
        d.ellipse([x - C * 0.04, y - C * 0.06, x + C * 0.04, y + C * 0.0], outline=255, width=3 * SS)     # дужка замка
        d.rectangle([x - C * 0.05, y - C * 0.02, x + C * 0.05, y + C * 0.05], fill=255)
    ring(d, C * 0.42, 4 * SS)
    for k in range(24):                                            # звенья цепи по кругу
        a = 2 * math.pi * k / 24
        x, y = polar(C * 0.42, a)
        s = C * 0.035
        if k % 2:
            d.ellipse([x - s, y - s, x + s, y + s], outline=255, width=3 * SS)
    ring(d, C * 0.2, 6 * SS)
    d.line([*polar(C * 0.2, -math.pi * 3 / 4), *polar(C * 0.2, math.pi / 4)], fill=255, width=7 * SS)
    save(img, 'seal_ward')


def seal_glyph(k):
    """Одна руна запрета в круге — висит над гнездом гексаграммы."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.95, 8 * SS)
    ring(d, C * 0.84, 3 * SS)
    for i in range(4):
        a = math.pi / 4 + math.pi / 2 * i
        d.line([*polar(C * 0.84, a), *polar(C * 0.95, a)], fill=255, width=5 * SS)
    g = glyph_img(900 + k, C * 0.6, C * 1.0, 16 * SS)
    img = lighter(img, g, C - g.size[0] / 2, C - g.size[1] / 2)
    save(img, 'seal_glyph_%d' % k)


# ------------------------------------------------------------------ Вознесение
def wing(scale):
    """Крыло из пяти перьев веером, основание слева внизу, 'L' картинка."""
    w, h = int(C * 0.5 * scale), int(C * 0.3 * scale)
    img = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(img)
    for k in range(6):
        a = math.radians(-8 - k * 13)
        L = w * (0.95 - k * 0.1)
        pts = [(w * 0.04 + L * s * math.cos(a), h * 0.92 + L * s * math.sin(a) * 0.9 - math.sin(s * math.pi) * h * 0.05) for s in np.linspace(0, 1, 20)]
        d.line(pts, fill=255, width=int(5 * SS * scale), joint='curve')
        tx, ty = pts[-1]
        d.ellipse([tx - 4 * SS, ty - 4 * SS, tx + 4 * SS, ty + 4 * SS], fill=255)
    return img


def asc_wings():
    """Вознесение: четыре пары крыльев по кругу, перьевой обод, звезда в центре."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.97, 5 * SS)
    ring(d, C * 0.9, 2 * SS)
    for i in range(48):
        a = 2 * math.pi * i / 48
        d.line([*polar(C * 0.9, a), *polar(C * 0.9 + C * 0.06, a + 0.05)], fill=255, width=3 * SS)
    for i in range(4):
        a = math.pi / 2 * i
        wg = wing(1.0)
        wf = wg.transpose(Image.FLIP_LEFT_RIGHT)
        x, y = polar(C * 0.55, a)
        img = stamp(img, wg, x + math.cos(a + math.pi / 2) * C * 0.13, y + math.sin(a + math.pi / 2) * C * 0.13, -math.degrees(a) - 90 + 90)
        img = stamp(img, wf, x - math.cos(a + math.pi / 2) * C * 0.13, y - math.sin(a + math.pi / 2) * C * 0.13, -math.degrees(a) - 90 - 90 + 180)
    d = ImageDraw.Draw(img)
    ring(d, C * 0.3, 4 * SS)
    star_at(d, C, C, 8, C * 0.05, C * 0.25)
    save(img, 'asc_wings')


def asc_halo():
    """Нимб: толстое кольцо, внутреннее тонкое и короткие лучи наружу."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.78, 14 * SS)
    ring(d, C * 0.66, 3 * SS)
    for i in range(32):
        a = 2 * math.pi * i / 32
        d.line([*polar(C * 0.84, a), *polar(C * (0.97 if i % 2 == 0 else 0.91), a)], fill=255, width=4 * SS)
    save(img, 'asc_halo')


# ------------------------------------------------------------------ Без пепла
def ashless_flames():
    """Кольцо пламени: языки остриями наружу (верх полосы — внешний край слоя band)."""
    img = canvas(BW, BH)
    n = 10
    cell = BW / n
    for i in range(n):
        for j, (wk, hk) in enumerate(((0.8, 1.0), (0.5, 0.7))):
            f = flame(cell * wk, BH * 0.92 * hk, 0.3 if (i + j) % 2 else -0.3)
            img = lighter(img, f, i * cell + j * cell * 0.5 + (cell * 0.5 - f.size[0]) / 2 + cell * 0.25 * (1 - j), BH - f.size[1])
    d = ImageDraw.Draw(img)
    d.line([0, BH - 6 * SS, BW, BH - 6 * SS], fill=255, width=5 * SS)
    save_band(img, 'ashless_flames')


def ashless_sigil():
    """Печать синего огня: треугольник огня, языки пламени по кругу, кольцо рун."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.97, 6 * SS)
    ring(d, C * 0.88, 2 * SS)
    img = rune_ring(img, C * 0.88, C * 0.97, 36, 77, 3 * SS)
    for i in range(12):
        a = 2 * math.pi * i / 12
        f = flame(C * 0.14, C * 0.2, 0.25)
        x, y = polar(C * 0.76, a)
        img = stamp(img, f, x, y, -math.degrees(a) - 90)
    d = ImageDraw.Draw(img)
    ring(d, C * 0.62, 4 * SS)
    tri = [polar(C * 0.6, -math.pi / 2 + 2 * math.pi * k / 3) for k in range(3)]
    d.polygon(tri, outline=255, width=6 * SS)
    for x, y in tri:
        d.ellipse([x - C * 0.05, y - C * 0.05, x + C * 0.05, y + C * 0.05], fill=255)
    ring(d, C * 0.3, 3 * SS)
    f = flame(C * 0.3, C * 0.42, 0.2)
    img = lighter(img, f, C - f.size[0] / 2, C - f.size[1] * 0.62)
    save(img, 'ashless_sigil')


# ------------------------------------------------------------------ знаки школ: ленты
def band_fire():
    img = canvas(BW, BH)
    n = 12
    for i in range(n):
        hk = 0.9 if i % 2 == 0 else 0.6
        f = flame(BW / n * 0.7, BH * 0.78 * hk, 0.3 if i % 2 else -0.3)
        img = lighter(img, f, i * BW / n + (BW / n - f.size[0]) / 2, BH - 12 * SS - f.size[1])
    band_lines(ImageDraw.Draw(img))
    return img


def snowflake(d, cx, cy, r, w):
    for k in range(6):
        a = math.pi / 3 * k
        ex, ey = cx + math.cos(a) * r, cy + math.sin(a) * r
        d.line([cx, cy, ex, ey], fill=255, width=w)
        for s in (0.45, 0.7):
            bx, by = cx + math.cos(a) * r * s, cy + math.sin(a) * r * s
            for side in (-1, 1):
                d.line([bx, by, bx + math.cos(a + side * 0.8) * r * 0.28, by + math.sin(a + side * 0.8) * r * 0.28], fill=255, width=w)


def band_ice():
    img = canvas(BW, BH)
    d = ImageDraw.Draw(img)
    band_lines(d)
    n = 8
    for i in range(n):
        cx = (i + 0.5) * BW / n
        snowflake(d, cx, BH / 2, BH * 0.3, 3 * SS)
    for i in range(n + 1):
        x = i * BW / n
        d.polygon([(x, BH * 0.22), (x + BH * 0.09, BH / 2), (x, BH * 0.78), (x - BH * 0.09, BH / 2)], outline=255, width=3 * SS)
    return img


def band_lightning():
    img = canvas(BW, BH)
    d = ImageDraw.Draw(img)
    band_lines(d)
    rng = random.Random(3)
    pts = []
    n = 24
    for i in range(n + 1):
        pts.append((i * BW / n, BH * (0.3 if i % 2 else 0.7) + (rng.random() - 0.5) * BH * 0.12))
    pts[-1] = (BW, pts[0][1])
    d.line(pts, fill=255, width=5 * SS, joint='curve')
    for i in range(0, n, 3):                                       # отростки
        x, y = pts[i]
        d.line([x, y, x + BW / n * 0.6, y + (BH * 0.25 if y < BH / 2 else -BH * 0.25)], fill=200, width=3 * SS)
    return img


def band_nature():
    img = canvas(BW, BH)
    d = ImageDraw.Draw(img)
    band_lines(d)
    n = 4
    pts = [(x, BH / 2 + math.sin(x / BW * 2 * math.pi * n) * BH * 0.18) for x in np.linspace(0, BW, 200)]
    d.line(pts, fill=255, width=4 * SS, joint='curve')
    for k in range(n * 4):
        x = (k + 0.5) * BW / (n * 4)
        y = BH / 2 + math.sin(x / BW * 2 * math.pi * n) * BH * 0.18
        side = 1 if k % 2 else -1
        leaf = Image.new('L', (int(BH * 0.34), int(BH * 0.14)), 0)
        ImageDraw.Draw(leaf).ellipse([0, 0, leaf.size[0] - 1, leaf.size[1] - 1], fill=255)
        img = stamp(img, leaf, x + side * BH * 0.06, y + side * BH * 0.14, 45 * side)
    return img


def band_holy():
    img = canvas(BW, BH)
    d = ImageDraw.Draw(img)
    band_lines(d)
    n = 8
    for i in range(n):
        cx = (i + 0.5) * BW / n
        r = BH * 0.12
        d.ellipse([cx - r, BH / 2 - r, cx + r, BH / 2 + r], outline=255, width=3 * SS)
        for k in range(8):
            a = math.pi / 4 * k
            d.line([cx + math.cos(a) * r * 1.4, BH / 2 + math.sin(a) * r * 1.4, cx + math.cos(a) * r * 2.3, BH / 2 + math.sin(a) * r * 2.3],
                   fill=255, width=3 * SS)
    for i in range(n + 1):                                         # кресты на стыках ячеек, крайние — половинками у шва
        x = i * BW / n
        d.line([x, BH * 0.28, x, BH * 0.72], fill=255, width=4 * SS)
        d.line([x - BH * 0.12, BH * 0.42, x + BH * 0.12, BH * 0.42], fill=255, width=4 * SS)
    return img


def band_blood():
    img = canvas(BW, BH)
    d = ImageDraw.Draw(img)
    band_lines(d)
    n = 14
    for i in range(n):
        cx = (i + 0.5) * BW / n
        L = BH * (0.38 if i % 2 else 0.55)
        d.polygon([(cx - BH * 0.03, 10 * SS), (cx + BH * 0.03, 10 * SS), (cx + BH * 0.07, 10 * SS + L), (cx, 10 * SS + L + BH * 0.08),
                   (cx - BH * 0.07, 10 * SS + L)], fill=255)
    for i in range(n + 1):                                         # шипы снизу
        x = i * BW / n
        d.polygon([(x - BH * 0.05, BH - 10 * SS), (x, BH * 0.7), (x + BH * 0.05, BH - 10 * SS)], fill=255)
    return img


def band_ender():
    img = canvas(BW, BH)
    d = ImageDraw.Draw(img)
    band_lines(d)
    n = 6
    for i in range(n):
        cx, cy = (i + 0.5) * BW / n, BH / 2
        w, h = BW / n * 0.32, BH * 0.22
        top = [(cx + w * math.cos(t), cy - h * math.sin(t)) for t in np.linspace(0, math.pi, 30)]
        bot = [(cx + w * math.cos(t), cy + h * math.sin(t)) for t in np.linspace(math.pi, 0, 30)]
        d.line(top + bot, fill=255, width=4 * SS, joint='curve')
        d.ellipse([cx - h * 0.6, cy - h * 0.6, cx + h * 0.6, cy + h * 0.6], fill=255)
        d.ellipse([cx - h * 0.2, cy - h * 0.45, cx + h * 0.2, cy + h * 0.45], fill=0)
    for i in range(n + 1):
        star_at(d, i * BW / n, BH / 2, 4, BH * 0.03, BH * 0.15, 0)
    return img


def band_evocation():
    img = canvas(BW, BH)
    d = ImageDraw.Draw(img)
    band_lines(d)
    n = 10
    for i in range(n):
        x = i * BW / n
        for k in range(3):
            ox = x + k * BW / n * 0.14
            d.line([ox, BH * 0.28, ox + BH * 0.16, BH / 2, ox, BH * 0.72], fill=255, width=4 * SS)
        cx = x + BW / n * 0.72
        d.polygon([(cx, BH * 0.25), (cx + BH * 0.13, BH / 2), (cx, BH * 0.75), (cx - BH * 0.13, BH / 2)], outline=255, width=3 * SS)
        d.ellipse([cx - 5 * SS, BH / 2 - 5 * SS, cx + 5 * SS, BH / 2 + 5 * SS], fill=255)
    return img


def band_eldritch():
    img = canvas(BW, BH)
    d = ImageDraw.Draw(img)
    band_lines(d)
    n = 7
    for i in range(n):
        x0 = i * BW / n
        pts = []
        for s in np.linspace(0, 1, 60):                            # щупальце с завитком на конце
            if s < 0.6:
                pts.append((x0 + s / 0.6 * BW / n * 0.6, BH * 0.62 - math.sin(s / 0.6 * math.pi) * BH * 0.2))
            else:
                u = (s - 0.6) / 0.4
                a = math.pi + u * 2.6 * math.pi
                rr = BH * 0.14 * (1 - u * 0.8)
                pts.append((x0 + BW / n * 0.6 + BH * 0.14 + math.cos(a) * rr, BH * 0.62 + math.sin(a) * rr))
        d.line(pts, fill=255, width=4 * SS, joint='curve')
        for k in range(3):
            cx, cy = x0 + BW / n * (0.2 + 0.18 * k), BH * 0.3
            r = 3 * SS + k * SS
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    return img


def band_wind():
    img = canvas(BW, BH)
    d = ImageDraw.Draw(img)
    band_lines(d)
    n = 6
    for i in range(n):
        x0 = i * BW / n
        cx, cy = x0 + BW / n * 0.72, BH * 0.48
        pts = [(cx + math.cos(a) * BH * 0.2 * (1 - k / 80), cy + math.sin(a) * BH * 0.2 * (1 - k / 80))
               for k, a in enumerate(np.linspace(math.pi / 2, math.pi / 2 + 3.2 * math.pi, 80))]
        tail = [(x0, cy + BH * 0.2), (cx, cy + BH * 0.2)]
        d.line(tail + pts, fill=255, width=4 * SS, joint='curve')
        d.line([x0 + BW / n * 0.1, BH * 0.3, x0 + BW / n * 0.45, BH * 0.3], fill=180, width=3 * SS)
    return img


# ------------------------------------------------------------------ спрайты частиц
def sprites():
    img = canvas()
    d = ImageDraw.Draw(img)
    d.polygon([(C, C * 0.1), (C + C * 0.42, C * 0.8), (C, C * 1.85), (C - C * 0.42, C * 0.8)], fill=200)
    d.ellipse([C - C * 0.42, C * 0.15, C + C * 0.42, C * 1.85], fill=210)
    d.line([C, C * 0.15, C, C * 1.95], fill=255, width=8 * SS)
    for k in range(5):
        y = C * (0.5 + 0.25 * k)
        d.line([C, y, C - C * 0.3, y - C * 0.25], fill=255, width=4 * SS)
        d.line([C, y, C + C * 0.3, y - C * 0.25], fill=255, width=4 * SS)
    save_fx(img, 'leaf', blur=0.3)
    img = canvas()
    d = ImageDraw.Draw(img)
    d.ellipse([C - C * 0.5, C * 0.75, C + C * 0.5, C * 1.75], fill=255)
    d.polygon([(C, C * 0.1), (C + C * 0.46, C * 1.1), (C - C * 0.46, C * 1.1)], fill=255)
    d.ellipse([C - C * 0.28, C * 1.0, C - C * 0.08, C * 1.35], fill=120)
    save_fx(img, 'drop', blur=0.4)
    img = canvas()
    snowflake(ImageDraw.Draw(img), C, C, C * 0.9, 12 * SS)
    save_fx(img, 'snowflake', blur=0.3)
    img = canvas()
    d = ImageDraw.Draw(img)
    pts = [(C + math.cos(a) * C * 0.85 * (1 - k / 90), C + math.sin(a) * C * 0.85 * (1 - k / 90))
           for k, a in enumerate(np.linspace(0, 3.6 * math.pi, 90))]
    d.line(pts, fill=255, width=14 * SS, joint='curve')
    save_fx(img, 'swirl', blur=0.6)
    img = canvas()
    crescent(ImageDraw.Draw(img), C, C, C * 0.85, 0.45, 0)
    save_fx(img, 'crescent', blur=0.5)
    img = canvas()
    star_at(ImageDraw.Draw(img), C, C, 5, C * 0.38, C * 0.95)
    save_fx(img, 'star5', blur=0.5)


# ------------------------------------------------------------------ JSON знаков школ
def write_json(rel, obj):
    path = os.path.join(ASSETS, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('wrote', rel)


# школа: (основной, вторичный, тень, спрайт частиц, скорость вращения, пояснение, сколько повторов ленты)
SCHOOLS = {
    'fire':      ('#FF7A2A', '#FFD27A', '#7A1E00', 'soul_mote', 40, 'огонь: языки пламени по ободу, искры-огоньки вверх', 6),
    'ice':       ('#9FE0FF', '#E8FAFF', '#2A5A8A', 'snowflake', -14, 'лёд: снежинки и кристаллы, снежинки медленно падают', 6),
    'lightning': ('#6BE6FF', '#E6FBFF', '#1A3A8A', 'spark_sharp', 90, 'молния: ломаная молния по ободу, резкие искры', 4),
    'nature':    ('#7EE04A', '#D8FF9A', '#2A5A10', 'leaf', 10, 'природа: лоза с листьями, кружатся листья', 4),
    'holy':      ('#FFE38A', '#FFFBE6', '#8A6420', 'feather', 8, 'свет: солнца и кресты, падают перья', 6),
    'blood':     ('#E0242C', '#FF8A8A', '#4A0006', 'drop', -20, 'кровь: капли с обода и шипы, падают капли', 5),
    'ender':     ('#C060FF', '#F0C8FF', '#2A0A4A', 'spark_soft', -30, 'Эндер: глаза и звёзды, искры затягивает к центру', 4),
    'evocation': ('#DDE6F0', '#FFFFFF', '#5A6A80', 'spark_soft', 24, 'воплощение: шевроны и ромбы, белые искры', 5),
    'eldritch':  ('#3FD6B8', '#B8FFF0', '#0A3A30', 'soul_mote', -12, 'потустороннее: щупальца с завитками, бирюзовые огоньки', 4),
    'wind':      ('#BFF2E8', '#FFFFFF', '#3A7A70', 'swirl', 70, 'ветер: вихри по ободу, закрученные потоки', 4),
}


def school_json():
    for s, (pri, sec, sh, spr, rot, note, rep) in SCHOOLS.items():
        style = 'school_blood' if s == 'blood' else s   # fx/styles/blood.json is the mythic Blood Moon style
        write_json('fx/styles/%s.json' % style, {
            'comment': 'Школа Iron\'s «%s» для знаков при касте (fx/school_%s.json): %s.' % (s, s, note),
            'palette': {'primary': pri, 'secondary': sec, 'core': '#FFFFFF', 'shadow': sh},
            'textures': {'sparks': 'spark_soft', 'runes': 'school_%s_band' % s, 'shards': spr, 'sigil': 'sigil_' + s},
            'blend': 'additive',
            'motion': {'rotationScale': 1.0, 'jitter': 0.0, 'easing': 'easeOutCubic'},
        })
        write_json('sigils/school_%s.json' % s, {
            'comment': 'Знак школы «%s» под магом при каждом касте обычной магии: %s. Прорисовка пером, лента школы навстречу, дуги смыкаются.' % (s, note),
            'size': 1.9, 'color': pri, 'orientation': 'ground', 'lifetime': -1, 'hold': 12,
            'layers': [
                {'id': 'glow', 'type': 'disc', 'texture': 'glow', 'radius': 0.8, 'heightOffset': 0.0, 'color': sh, 'brightness': 1.2,
                 'appear': {'delay': 0, 'duration': 5, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}},
                {'id': 'sign', 'type': 'disc', 'texture': 'sigil_' + s, 'radius': 0.86, 'heightOffset': 0.01,
                 'appear': {'delay': 0, 'duration': 9, 'easing': 'easeOutCubic', 'modes': ['draw'], 'startAngle': 90, 'direction': 1},
                 'rotation': {'speed': rot, 'boost': 3}},
                {'id': 'band', 'type': 'band', 'texture': 'school_%s_band' % s, 'radius': 1.12, 'inner': 0.9, 'repeat': rep, 'heightOffset': 0.02,
                 'color': sec, 'brightness': 0.9,
                 'appear': {'delay': 2, 'duration': 9, 'easing': 'easeInOutSine', 'modes': ['draw'], 'startAngle': 270, 'direction': -1},
                 'rotation': {'speed': -rot * 0.6, 'boost': 2}},
                {'id': 'arcs', 'type': 'arcs', 'texture': 'arc_strip', 'radius': 1.22, 'width': 0.035, 'heightOffset': 0.03, 'count': 3, 'arcLength': 80,
                 'appear': {'delay': 3, 'duration': 10, 'easing': 'easeInOutCubic', 'modes': ['assemble', 'fade']}, 'rotation': {'speed': rot * 0.4, 'boost': 4}},
            ],
            'formedFlash': {'color': sec, 'size': 1.3, 'duration': 8, 'sparks': 18},
            'dissolve': {'modes': ['reverse', 'collapse'], 'duration': 10, 'stagger': 2},
        })
        falls = s in ('ice', 'holy', 'blood', 'nature')
        sprite = {'type': 'sprites', 'delay': 2, 'duration': 30, 'at': 'caster+0,%s,0' % ('2.2' if falls else '0.2'), 'follow': True,
                  'texture': '@shards', 'count': 16, 'rate': 1.2, 'area': 1.6, 'speed': 0.02,
                  'gravity': 0.002 if falls else -0.003, 'spin': rot * 2, 'size': [0.22, 0.1], 'life': 22, 'color': '@secondary'}
        if s in ('holy', 'nature'):
            sprite.update({'tumble': 0.6, 'sway': 0.6})
        write_json('fx/school_%s.json' % s, {
            'comment': 'Каст обычной магии школы «%s» (PohSpell.onCast): знак под магом, его малая копия у пояса, волна, частицы школы.' % s,
            'style': style,
            'duration': 36,
            'elements': [
                {'type': 'sigil', 'id': 'school_' + s, 'delay': 0, 'at': 'caster+0,0.04,0', 'follow': True},
                {'type': 'sigil', 'id': 'school_' + s, 'delay': 3, 'at': 'caster+0,1.0,0', 'follow': True, 'scale': 0.42},
                {'type': 'wave', 'shape': 'ring', 'delay': 0, 'duration': 14, 'at': 'caster', 'radius': 3.0, 'color': '@primary'},
                {'type': 'flash', 'delay': 0, 'duration': 8, 'at': 'caster+0,0.3,0', 'size': 1.6, 'color': '@secondary', 'brightness': 0.7},
                sprite,
            ],
        })


# ------------------------------------------------------------------ JSON рун Печати запрета и карт Звезды судьбы
def seal_json():
    for k in range(6):
        write_json('sigils/higher_seal_glyph_%d.json' % k, {
            'comment': 'Печать запрета: руна %d из шести над гнездом гексаграммы (к камере). Ломается, когда цель выходит из круга — разборка shatter.' % (k + 1),
            'size': 0.42, 'color': '#FF3B3B', 'orientation': 'billboard', 'lifetime': -1, 'hold': -1,
            'layers': [
                {'id': 'glow', 'type': 'disc', 'texture': 'glow', 'radius': 1.3, 'color': '#7A0A1E', 'brightness': 1.2,
                 'appear': {'delay': 0, 'duration': 6, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}, 'pulse': {'amp': 0.3, 'period': 24}},
                {'id': 'rune', 'type': 'disc', 'texture': 'seal_glyph_%d' % k, 'radius': 1.0, 'heightOffset': 0.01, 'color': '#FF6A5A',
                 'appear': {'delay': 2, 'duration': 10, 'easing': 'easeOutBack', 'modes': ['unfold', 'fade']}},
            ],
            'formedFlash': {'color': '#FFFFFF', 'size': 1.2, 'duration': 6, 'sparks': 8},
            'dissolve': {'modes': ['shatter'], 'duration': 10},
        })
        write_json('fx/higher_seal_rune_%d.json' % k, {
            'comment': 'Печать запрета, руна %d: точка эффекта — гнездо на ободе круга, target — запечатанная цель. Гнездо на земле, '
                       'столб-штырь, руна над ним и цепь от руны к цели. SealSpell останавливает его, когда руна ломается.' % (k + 1),
            'style': 'higher',
            'duration': -1,
            'elements': [
                {'type': 'sigil', 'id': 'higher_seal_socket', 'delay': 0, 'at': 'caster+0,0.06,0'},
                {'type': 'sigil', 'id': 'higher_seal_glyph_%d' % k, 'delay': 2 + k, 'at': 'caster+0,1.15,0'},
                {'type': 'beam', 'delay': k, 'at': 'caster', 'to': 'caster+0,2.2,0', 'width': 0.1, 'core': 0.35, 'taper': 0.5, 'flicker': 0.25,
                 'grow': 8, 'color': '#FF4A3A', 'in': {'duration': 4, 'easing': 'easeOutCubic'}},
                {'type': 'chains', 'delay': 6 + k, 'at': 'caster+0,1.0,0', 'to': 'target+0,1.0,0', 'follow': True, 'link': 0.2, 'sag': 0.25,
                 'tension': 0.7, 'color': '#FF6A5A', 'in': {'duration': 6, 'easing': 'easeOutCubic'}},
                {'type': 'sprites', 'delay': 0, 'at': 'caster', 'texture': 'spark_sharp', 'count': 600, 'rate': 0.3, 'area': 0.3,
                 'speed': 0.004, 'gravity': -0.003, 'size': [0.1, 0.02], 'life': 20, 'color': '#FF8A7A'},
            ],
        })


CARDS = {
    'sun':   ('#FFC94D', '#FFF0B0', 'карта Солнца: лучистое солнце, удар поджигает', 'spark_soft'),
    'moon':  ('#A8C8FF', '#E8F0FF', 'карта Луны: полумесяц, звёзды и капли росы, удар ослепляет', 'crescent'),
    'tower': ('#FF4D4D', '#FFB0A0', 'карта Башни: башня под молнией, двойной удар по цели и отдача магу', 'shard'),
    'world': ('#7DFFB0', '#D8FFE8', 'карта Мира: венок и звезда, звёзды падают ещё на двух врагов', 'star5'),
}


def fate_json():
    for c, (pri, sec, note, spr) in CARDS.items():
        write_json('sigils/higher_fate_card_%s.json' % c, {
            'comment': 'Звезда судьбы, %s. Ложится под цель, пока горит созвездие.' % note,
            'size': 2.4, 'color': pri, 'orientation': 'ground', 'lifetime': -1, 'hold': -1,
            'layers': [
                {'id': 'glow', 'type': 'disc', 'texture': 'glow', 'radius': 0.7, 'color': sec, 'brightness': 0.5,
                 'appear': {'delay': 0, 'duration': 20, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}, 'pulse': {'amp': 0.25, 'period': 16}},
                {'id': 'card', 'type': 'disc', 'texture': 'fate_card_' + c, 'radius': 0.8, 'heightOffset': 0.01,
                 'appear': {'delay': 0, 'duration': 24, 'easing': 'easeInOutSine', 'modes': ['draw'], 'startAngle': 90, 'direction': -1},
                 'rotation': {'speed': 5}},
                {'id': 'houses', 'type': 'disc', 'texture': 'fate_constellation', 'radius': 1.0, 'heightOffset': 0.02, 'color': sec, 'brightness': 0.6,
                 'appear': {'delay': 10, 'duration': 20, 'easing': 'easeOutCubic', 'modes': ['fade', 'twist'], 'twist': -120}, 'rotation': {'speed': -8}},
                {'id': 'orbit', 'type': 'arcs', 'texture': 'arc_strip', 'radius': 1.1, 'width': 0.025, 'heightOffset': 0.03, 'count': 4, 'arcLength': 60,
                 'appear': {'delay': 20, 'duration': 22, 'easing': 'easeInOutCubic', 'modes': ['assemble', 'fade']}, 'rotation': {'speed': 20, 'boost': 4}},
            ],
            'formedFlash': {'color': sec, 'size': 1.2, 'duration': 10, 'sparks': 20},
            'dissolve': {'modes': ['shatter'], 'duration': 12},
        })
        elements = [
            {'type': 'sigil', 'id': 'higher_fate_sky', 'delay': 0, 'at': 'target+0,7,0', 'follow': True, 'until': 62, 'color': pri},
            {'type': 'sigil', 'id': 'higher_fate_card_' + c, 'delay': 6, 'at': 'target+0,0.05,0', 'follow': True, 'until': 62},
            {'type': 'sprites', 'delay': 0, 'duration': 56, 'at': 'target+0,7,0', 'follow': True, 'texture': spr, 'count': 40, 'rate': 0.8,
             'spread': 2.6, 'speed': 0.01, 'gravity': 0.0, 'spin': 60, 'size': [0.25, 0.05], 'life': 30, 'color': sec},
            {'type': 'beam', 'delay': 46, 'duration': 16, 'at': 'target+0,7,0', 'to': 'target', 'follow': True, 'width': 0.5, 'core': 0.3,
             'taper': 0.6, 'grow': 14, 'color': pri, 'in': {'duration': 4, 'easing': 'easeOutCubic'}},
            {'type': 'flash', 'delay': 46, 'duration': 16, 'at': 'target+0,7,0', 'follow': True, 'size': 2.6, 'rays': 6, 'color': sec},
            {'type': 'flash', 'delay': 60, 'duration': 14, 'at': 'target+0,0.4,0', 'size': 6, 'anamorphic': 12, 'rays': 10, 'screen': 0.2, 'color': pri},
            {'type': 'wave', 'shape': 'ring', 'delay': 60, 'duration': 22, 'at': 'target', 'radius': 4.5, 'color': pri},
            {'type': 'wave', 'shape': 'sphere', 'delay': 60, 'duration': 14, 'at': 'target+0,0.5,0', 'radius': 3.2, 'rim': 0.9, 'color': sec,
             'out': {'duration': 8, 'easing': 'easeInSine'}},
            {'type': 'sigil', 'id': 'higher_fate_impact', 'delay': 60, 'at': 'target+0,0.06,0', 'color': pri},
            {'type': 'sprites', 'delay': 60, 'duration': 30, 'at': 'target+0,0.6,0', 'texture': spr, 'count': 40, 'rate': 0, 'spread': 0.6,
             'speed': 0.22, 'gravity': 0.01, 'spin': 200, 'size': [0.35, 0.08], 'life': 28, 'color': sec},
            {'type': 'decal', 'delay': 62, 'duration': 60, 'at': 'target', 'texture': 'fate_card_' + c, 'radius': 2.4, 'fadeOut': 50, 'color': pri,
             'brightness': 0.6},
        ]
        if c == 'sun':
            elements.append({'type': 'column', 'delay': 60, 'duration': 16, 'at': 'target', 'radius': 1.6, 'height': 9, 'fill': 1, 'color': '#FF8A2A',
                             'out': {'duration': 10, 'easing': 'easeInSine'}})
        elif c == 'moon':
            elements.append({'type': 'tint', 'delay': 56, 'duration': 30, 'at': 'target', 'radius': 6, 'color': '#2A3A80', 'strength': 0.35,
                             'in': {'duration': 4, 'easing': 'easeOutCubic'}, 'out': {'duration': 20, 'easing': 'easeInSine'}})
        elif c == 'tower':
            elements.append({'type': 'lightning', 'delay': 52, 'duration': 12, 'at': 'target+0,7,0', 'to': 'target', 'follow': True,
                             'branches': 3, 'jaggedness': 0.5, 'regen': 2, 'width': 0.18, 'color': '#FFD0C0'})
            elements.append({'type': 'decal', 'delay': 62, 'duration': 80, 'at': 'target', 'texture': 'higher_cracks', 'radius': 3, 'fadeOut': 40,
                             'color': pri})
        elif c == 'world':
            elements.append({'type': 'wave', 'shape': 'ring', 'delay': 66, 'duration': 26, 'at': 'target', 'radius': 7, 'color': sec})
        write_json('fx/higher_fate_%s.json' % c, {
            'comment': 'Звезда судьбы, %s. Созвездие над целью 3 с (следует за ней), под целью карта; на 46-м тике звезда падает лучом, '
                       'на 60-м удар (тики совпадают с FateStarSpell.FALL). Цвет созвездия — цвет карты.' % note,
            'style': 'higher',
            'duration': 120,
            'elements': elements,
        })


if __name__ == '__main__':
    cradle_dream()
    cradle_moon_band()
    fate_constellation()
    for n in ('sun', 'moon', 'tower', 'world'):
        fate_card(n)
    gravity_well()
    gravity_spiral()
    event_ring()
    seal_ward()
    for k in range(6):
        seal_glyph(k)
    asc_wings()
    asc_halo()
    ashless_flames()
    ashless_sigil()
    for s, fn in (('fire', band_fire), ('ice', band_ice), ('lightning', band_lightning), ('nature', band_nature), ('holy', band_holy),
                  ('blood', band_blood), ('ender', band_ender), ('evocation', band_evocation), ('eldritch', band_eldritch), ('wind', band_wind)):
        save_band(fn(), 'school_%s_band' % s)
    sprites()
    school_json()
    seal_json()
    fate_json()
