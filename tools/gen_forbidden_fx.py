#!/usr/bin/env python3
"""
Запретная школа, ступень «Мироздание» — визуал. Сейчас: T24 «Стёртое имя» (erased_name).
ТЗ: docs/specs/tasks/T24_erased_name.md (каст 15 с = 300 тиков, стирание из мира на 10 мин). Суть школы — docs/lore/forbidden_school.md.

Стиль отличается от «Низвержения» (золото на чёрном, багровый разлом, цепи): «Стёртое имя» — бумага и чернила.
Пепельно-белые строки, вычёркивания багровым «пером», мир выцветает в серое, контур цели рассыпается буквами в пустоту.
Общая для школы печать ступени «Мироздание» (`forbidden_creation_seal`) — «сломанные законы мира»: пять медальонов-законов
(тяготение, время, причинность, пространство, мир), каждый перечёркнут, внутри — искривлённая решётка пространства.

Пишет (src/main/resources/assets/pohsmp_core/):
  textures/sigil/creation_laws.png, creation_warp.png, erase_ledger.png, erase_plate.png, erase_void.png, erase_quill.png,
                 mote_erased.png, mote_ash.png                                          — рисунки (белое на прозрачном)
  textures/gui/overlay/erased_vignette.png, erased_letters.png                           — накладка экрана стёртого (цветная)
  sigils/forbidden_creation_seal.json, erased_*.json                                     — печати
  fx/styles/erased_name.json; fx/school_forbidden_cast_creation.json, erased_name_cast.json, erased_vanish.json,
  erased_return.json, erased_self.json                                                   — эффекты
  textures/gui/spell_icons/erased_name.png (16×16), textures/mob_effect/erased.png (18×18)

Время — тики, углы — градусы, размеры — блоки. Запуск:  python3 tools/gen_forbidden_fx.py [--sheet out.png]
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_sigil_textures import C, SS, W, canvas, glyph, polar, ring, save  # noqa: E402

A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
OUT_SIGIL = os.path.join(A, 'textures', 'sigil')
WRITTEN = []

# ------------------------------------------------------------------ палитры
ASH, PAPER, GREY, INK, CRIMSON, CRIMSON_D, GOLD = '#E9E4D8', '#F6F2E8', '#9C978E', '#16141A', '#C8182E', '#6A0A16', '#D4A017'
VOID = '#050506'


def write(rel, obj):
    path = os.path.join(A, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write('\n')
    WRITTEN.append(rel)


# ================================================================== текстуры
def _pline(d, pts, width, fill=255):
    d.line(pts, fill=fill, width=int(width), joint='curve')
    r = width / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _polar_glyph(d, r, a, h, w, rng, width, fill=255):
    """Руна на окружности: «верх» буквы — наружу; h — высота (по радиусу), w — ширина (по дуге), в пикселях."""
    strokes, dot = glyph(rng)

    def P(gx, gy):                                               # gx 0..2 по дуге, gy 0..3 сверху вниз
        rr = r + h / 2 - gy * h / 3
        aa = a - (gx - 1) * (w / 2) / rr
        return polar(rr, aa)
    for (ax, ay), (bx, by) in strokes:
        _pline(d, [P(ax, ay), P(bx, by)], width, fill)
    if dot:
        x, y = P(2.7, 1.5)
        q = width * 0.9
        d.ellipse([x - q, y - q, x + q, y + q], fill=fill)


def _arc_pts(r, a0, a1, n=None, wob=0.0, rng=None):
    n = n or max(8, int(abs(a1 - a0) * r / (6 * SS)))
    out = []
    for k in range(n + 1):
        t = k / n
        rr = r + (wob * math.sin(t * math.pi * 3 + (rng.random() * 6 if rng else 0)) if wob else 0)
        out.append(polar(rr, a0 + (a1 - a0) * t))
    return out


def _brush(d, pts, w0, rng, fill=255, dry=0.0):
    """Мазок кисти по ломаной: ширина сужается к концам (sin), dry — «сухая кисть» (продольные просветы)."""
    n = len(pts)
    for k in range(n - 1):
        t = k / max(1, n - 2)
        w = w0 * (0.25 + 0.75 * math.sin(math.pi * min(1.0, 0.08 + t * 0.92)) ** 0.6)
        d.line([pts[k], pts[k + 1]], fill=fill, width=max(1, int(w)))
        q = w / 2
        d.ellipse([pts[k + 1][0] - q, pts[k + 1][1] - q, pts[k + 1][0] + q, pts[k + 1][1] + q], fill=fill)
    if dry:                                                      # просветы сухой кисти: тонкие тёмные нити вдоль мазка
        for s in range(int(6 * dry)):
            off = (rng.random() - 0.5) * w0 * 0.7
            k0 = rng.randint(0, n // 2)
            k1 = min(n - 1, k0 + rng.randint(n // 4, n // 2 + 1))
            seg = []
            for k in range(k0, k1 + 1):
                if k + 1 < n:
                    dx, dy = pts[k + 1][0] - pts[k][0], pts[k + 1][1] - pts[k][1]
                else:
                    dx, dy = pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]
                L = math.hypot(dx, dy) or 1
                seg.append((pts[k][0] - dy / L * off, pts[k][1] + dx / L * off))
            if len(seg) > 1:
                d.line(seg, fill=0, width=max(1, int(w0 * 0.05 * (0.5 + rng.random()))))


def tex_creation_laws():
    """Печать ступени «Мироздание» (Запретная): пять медальонов-законов мира, каждый перечёркнут; обод с засечками-делениями,
    кольцо «формул» (руны), внутреннее кольцо со смещённым центром — мир «съехал»."""
    img = canvas()
    d = ImageDraw.Draw(img)
    rng = random.Random(24)
    ring(d, C * 0.985, 6 * SS)
    ring(d, C * 0.955, 2 * SS)
    for i in range(120):                                         # деления, как на лимбе: каждое 10-е длиннее
        a = 2 * math.pi * i / 120
        r0 = C * (0.905 if i % 10 == 0 else 0.93)
        d.line([*polar(r0, a), *polar(C * 0.952, a)], fill=255, width=(4 if i % 10 == 0 else 2) * SS)
    ring(d, C * 0.9, 3 * SS)
    for i in range(44):                                          # кольцо формул
        _polar_glyph(d, C * 0.835, 2 * math.pi * i / 44 + 0.03, C * 0.075, C * 0.05, rng, 3.4 * SS)
    ring(d, C * 0.775, 3 * SS)
    # пять медальонов-законов
    laws = ('gravity', 'time', 'cause', 'space', 'world')
    for k, law in enumerate(laws):
        a = -math.pi / 2 + 2 * math.pi * k / 5
        cx, cy = polar(C * 0.6, a)
        R = C * 0.15
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=0, outline=255, width=5 * SS)
        d.ellipse([cx - R * 0.84, cy - R * 0.84, cx + R * 0.84, cy + R * 0.84], outline=255, width=2 * SS)
        s = R * 0.55
        lw = 4 * SS
        if law == 'gravity':                                     # стрелка вниз и «земля»
            _pline(d, [(cx, cy - s), (cx, cy + s * 0.55)], lw)
            d.polygon([(cx - s * 0.42, cy + s * 0.2), (cx + s * 0.42, cy + s * 0.2), (cx, cy + s * 0.8)], fill=255)
            _pline(d, [(cx - s * 0.75, cy + s * 0.95), (cx + s * 0.75, cy + s * 0.95)], lw)
        elif law == 'time':                                      # песочные часы
            _pline(d, [(cx - s * 0.6, cy - s), (cx + s * 0.6, cy - s)], lw)
            _pline(d, [(cx - s * 0.6, cy + s), (cx + s * 0.6, cy + s)], lw)
            d.line([(cx - s * 0.5, cy - s), (cx + s * 0.5, cy + s)], fill=255, width=lw)
            d.line([(cx + s * 0.5, cy - s), (cx - s * 0.5, cy + s)], fill=255, width=lw)
            d.polygon([(cx - s * 0.32, cy + s * 0.9), (cx + s * 0.32, cy + s * 0.9), (cx, cy + s * 0.35)], fill=255)
        elif law == 'cause':                                     # два звена: причина → следствие
            for dx in (-0.38, 0.38):
                d.ellipse([cx + s * dx - s * 0.5, cy - s * 0.32, cx + s * dx + s * 0.5, cy + s * 0.32], outline=255, width=lw)
            _pline(d, [(cx - s * 0.95, cy + s * 0.7), (cx + s * 0.75, cy + s * 0.7)], lw)
            d.polygon([(cx + s * 0.6, cy + s * 0.5), (cx + s * 1.0, cy + s * 0.7), (cx + s * 0.6, cy + s * 0.9)], fill=255)
        elif law == 'space':                                     # куб (изометрия)
            pts = [(cx + s * 0.9 * math.cos(math.pi / 6 + j * math.pi / 3), cy + s * 0.9 * math.sin(math.pi / 6 + j * math.pi / 3)) for j in range(6)]
            d.line(pts + [pts[0]], fill=255, width=lw, joint='curve')
            for j in (1, 3, 5):
                d.line([(cx, cy), pts[j]], fill=255, width=lw)
        else:                                                    # мир: круг, меридиан, экватор
            d.ellipse([cx - s * 0.85, cy - s * 0.85, cx + s * 0.85, cy + s * 0.85], outline=255, width=lw)
            d.ellipse([cx - s * 0.36, cy - s * 0.85, cx + s * 0.36, cy + s * 0.85], outline=255, width=int(lw * 0.7))
            d.line([cx - s * 0.85, cy, cx + s * 0.85, cy], fill=255, width=int(lw * 0.7))
        # вычеркнут: мазок наискось через медальон (с выносом за край)
        b = a + 0.7
        p0 = (cx - math.cos(b) * R * 1.25, cy - math.sin(b) * R * 1.25)
        p1 = (cx + math.cos(b) * R * 1.25, cy + math.sin(b) * R * 1.25)
        _brush(d, [(p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t + math.sin(t * 3.1) * R * 0.05) for t in np.linspace(0, 1, 24)],
               9 * SS, rng)
        # связки между медальонами — дуги, разорванные посередине
        a1 = a + 2 * math.pi / 5
        _pline(d, _arc_pts(C * 0.6, a + 0.27, a + math.pi / 5 - 0.06), 3 * SS)
        _pline(d, _arc_pts(C * 0.6, a + math.pi / 5 + 0.06, a1 - 0.27), 3 * SS)
    # внутреннее кольцо со смещённым центром (мир «съехал») и концентрическое
    off = C * 0.035
    d.ellipse([C - C * 0.37 + off, C - C * 0.37 - off * 0.5, C + C * 0.37 + off, C + C * 0.37 - off * 0.5], outline=255, width=3 * SS)
    ring(d, C * 0.41, 2 * SS)
    for i in range(10):                                          # десять лучей-«спиц» от центра, обрываются
        a = 2 * math.pi * i / 10 + 0.31
        _pline(d, [polar(C * 0.17, a), polar(C * (0.3 if i % 2 else 0.36), a)], 3 * SS)
    ring(d, C * 0.14, 4 * SS)
    save(img, 'creation_laws')


def tex_creation_warp():
    """Искривлённая решётка пространства: квадратная сетка, закрученная к центру (воронка), гаснет к краю круга."""
    img = canvas()
    d = ImageDraw.Draw(img)
    n = 22
    R = C * 0.96

    def warp(x, y):                                             # x, y ∈ [−1, 1]
        r = math.hypot(x, y)
        a = math.atan2(y, x) + 1.25 * math.exp(-r * 2.4)          # закрутка к центру
        r2 = r ** 1.35                                            # «проваливается» внутрь
        return C + R * r2 * math.cos(a), C + R * r2 * math.sin(a)
    for k in range(n + 1):
        v = -1 + 2 * k / n
        for horiz in (True, False):
            seg = []
            for j in range(161):
                u = -1 + 2 * j / 160
                x, y = (u, v) if horiz else (v, u)
                if math.hypot(x, y) > 1:
                    if len(seg) > 1:
                        d.line(seg, fill=255, width=2 * SS, joint='curve')
                    seg = []
                    continue
                seg.append(warp(x, y))
            if len(seg) > 1:
                d.line(seg, fill=255, width=2 * SS, joint='curve')
    a = np.asarray(img, np.float32)                                # к краю гаснет
    yy, xx = np.mgrid[0:W, 0:W]
    rr = np.hypot(xx - C, yy - C) / C
    a *= np.clip((1.0 - rr) / 0.35, 0, 1) * np.clip(rr / 0.12, 0.15, 1)
    save(Image.fromarray(a.astype(np.uint8), 'L'), 'creation_warp')


def tex_erase_ledger():
    """«Книга имён»: концентрические строки рукописи (руны), часть строк перечёркнута мазками; линовка-колонки,
    обод с засечками, пустой центр с рамкой-картушем, перечёркнутым насквозь."""
    img = canvas()
    d = ImageDraw.Draw(img)
    rng = random.Random(1124)
    ring(d, C * 0.985, 4 * SS)
    ring(d, C * 0.955, 2 * SS)
    for i in range(36):
        a = 2 * math.pi * i / 36
        d.line([*polar(C * 0.955, a), *polar(C * 0.985, a)], fill=255, width=2 * SS)
    rows = [0.9, 0.82, 0.74, 0.66, 0.58]
    cols = 12
    for i in range(cols):                                        # линовка: тонкие радиальные линии-колонки
        a = 2 * math.pi * i / cols
        d.line([*polar(C * 0.53, a), *polar(C * 0.94, a)], fill=150, width=2 * SS)
    for ri, r in enumerate(rows):
        h = C * 0.052
        ring(d, C * (r - 0.038), 1 * SS, fill=110)               # линейка под строкой
        a = 0.0
        while a < 2 * math.pi - 0.05:                           # слова: группы рун, пробелы
            nw = rng.randint(3, 7)
            w = C * 0.032
            start = a
            for j in range(nw):
                gw = w * (0.8 + rng.random() * 0.4)
                aa = a + (gw / 2) / (C * r)
                if aa > 2 * math.pi - 0.03:
                    break
                _polar_glyph(d, C * r, aa, h, gw, rng, 2.6 * SS)
                a += (gw * 1.35) / (C * r)
            end = a
            if rng.random() < 0.38 and end - start > 0.05:     # строка вычеркнута
                pts = _arc_pts(C * (r + rng.uniform(-0.006, 0.006)), start - 0.01, end, wob=C * 0.004, rng=rng)
                _brush(d, pts, 10 * SS, rng, dry=0.35)
            a += (C * 0.045) / (C * r)
    ring(d, C * 0.52, 3 * SS)
    ring(d, C * 0.49, 1.5 * SS)
    # картуш в центре: имя стёрто — рамка пустая, через неё мазок
    cw, ch = C * 0.34, C * 0.11
    d.rounded_rectangle([C - cw, C - ch, C + cw, C + ch], radius=int(ch * 0.9), outline=255, width=4 * SS)
    d.rounded_rectangle([C - cw * 0.93, C - ch * 0.72, C + cw * 0.93, C + ch * 0.72], radius=int(ch * 0.6), outline=200, width=2 * SS)
    for sx in (-1, 1):                                           # уши-завитки картуша
        x0 = C + sx * cw
        d.arc([x0 - ch * 0.5 + sx * ch * 0.35, C - ch * 0.5, x0 + ch * 0.5 + sx * ch * 0.35, C + ch * 0.5], 0, 360, fill=255, width=3 * SS)
    pts = [(C - cw * 1.25 + 2.5 * cw * t, C + ch * 0.12 - ch * 0.35 * t + math.sin(t * 7) * ch * 0.04) for t in np.linspace(0, 1, 40)]
    _brush(d, pts, 14 * SS, rng, dry=1.0)
    for k in range(4):                                           # точки-ромбы над и под картушем
        for sy in (-1, 1):
            x = C + (k - 1.5) * cw * 0.45
            y = C + sy * ch * 2.0
            q = 6 * SS
            d.polygon([(x, y - q), (x + q, y), (x, y + q), (x - q, y)], fill=255)
    ring(d, C * 0.4, 2 * SS, fill=170)
    save(img, 'erase_ledger')


def tex_erase_plate():
    """Табличка имени над целью: вытянутый картуш с завитками на концах, двойная рамка; внутри пусто — туда пишется имя."""
    img = canvas()
    d = ImageDraw.Draw(img)
    cw, ch = C * 0.86, C * 0.2
    d.rounded_rectangle([C - cw, C - ch, C + cw, C + ch], radius=int(ch * 0.55), outline=255, width=5 * SS)
    d.rounded_rectangle([C - cw * 0.96, C - ch * 0.78, C + cw * 0.96, C + ch * 0.78], radius=int(ch * 0.4), outline=170, width=2 * SS)
    for sx in (-1, 1):
        x = C + sx * cw
        for k, rr in enumerate((0.55, 0.33)):                  # спиральки на концах
            d.arc([x - ch * rr + sx * ch * 0.25, C - ch * rr, x + ch * rr + sx * ch * 0.25, C + ch * rr],
                  90 if sx > 0 else -90, 270 if sx > 0 else 90, fill=255, width=(4 - k) * SS)
        q = 10 * SS
        y = C
        xx = x + sx * ch * 0.95
        d.polygon([(xx, y - q), (xx + sx * q * 1.6, y), (xx, y + q), (xx - sx * q * 0.6, y)], fill=255)
    for sy in (-1, 1):                                           # засечки сверху и снизу рамки
        for k in range(9):
            x = C - cw * 0.8 + k * cw * 0.2
            y = C + sy * ch
            d.line([x, y, x, y + sy * 10 * SS], fill=200, width=2 * SS)
    save(img, 'erase_plate')


def tex_erase_void():
    """Пустота: кольцо обломков букв вокруг пустого центра; внутренний край изъеден, обломки редеют наружу."""
    img = canvas()
    d = ImageDraw.Draw(img)
    rng = random.Random(77)
    for k in range(260):
        r = C * (0.34 + (rng.random() ** 1.8) * 0.58)
        a = rng.random() * 2 * math.pi
        h = C * (0.06 - 0.035 * (r / C - 0.34))
        _polar_glyph(d, r, a, h, h * 0.7, rng, max(1.5, 3.2 * (1.05 - r / C)) * SS, fill=int(255 * (1.1 - r / C)))
    ring(d, C * 0.31, 3 * SS)
    arr = np.asarray(img, np.float32)
    nz = np.asarray(Image.effect_noise((W // 16, W // 16), 64).resize((W, W), Image.BICUBIC), np.float32) / 255.0
    yy, xx = np.mgrid[0:W, 0:W]
    rr = np.hypot(xx - C, yy - C) / C
    edge = np.clip((rr - 0.29 - 0.08 * (nz - 0.5)) / 0.05, 0, 1)    # изъеденный внутренний край
    halo = np.clip(1 - np.abs(rr - 0.31) / 0.02, 0, 1) * 160 * (nz > 0.45)
    arr = np.maximum(arr * edge, halo)
    save(Image.fromarray(arr.astype(np.uint8), 'L'), 'erase_void')


def tex_erase_quill():
    """Малая печать у ладони: перо-«ластик» — наконечник пера в кольце, под ним короткая черта; кольцо рун."""
    img = canvas()
    d = ImageDraw.Draw(img)
    rng = random.Random(9)
    ring(d, C * 0.97, 6 * SS)
    for i in range(16):
        _polar_glyph(d, C * 0.84, 2 * math.pi * i / 16, C * 0.13, C * 0.09, rng, 5 * SS)
    ring(d, C * 0.7, 4 * SS)
    # наконечник пера (вниз), с прорезью и отверстием
    nib = [(C, C + C * 0.42), (C + C * 0.2, C - C * 0.05), (C + C * 0.13, C - C * 0.36), (C - C * 0.13, C - C * 0.36), (C - C * 0.2, C - C * 0.05)]
    d.polygon(nib, fill=255)
    d.line([C, C + C * 0.4, C, C - C * 0.05], fill=0, width=5 * SS)
    d.ellipse([C - C * 0.05, C - C * 0.12, C + C * 0.05, C - C * 0.02], fill=0)
    _brush(d, [(C - C * 0.5 + C * t, C + C * 0.5 - C * 0.03 * t) for t in np.linspace(0, 1, 20)], 12 * SS, rng)
    save(img, 'erase_quill')


def tex_motes():
    """Спрайты: mote_erased — руна, перечёркнутая чертой, правый край крошится; mote_ash — чернильный пепел-хлопья."""
    S = 128 * SS
    img = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(img)
    rng = random.Random(3)
    g = ([((1, 0), (1, 3)), ((0, 0), (2, 1)), ((0, 2), (2, 2)), ((1, 3), (2, 2))], False)
    sx, sy = S * 0.22, S * 0.2
    x0, y0 = S * 0.28, S * 0.2
    for (ax, ay), (bx, by) in g[0]:
        _pline(d, [(x0 + ax * sx, y0 + ay * sy), (x0 + bx * sx, y0 + by * sy)], 9 * SS)
    _brush(d, [(S * 0.12 + S * 0.76 * t, S * 0.52 - S * 0.06 * t) for t in np.linspace(0, 1, 16)], 11 * SS, rng)
    arr = np.asarray(img, np.float32)
    nz = np.asarray(Image.effect_noise((S // 8, S // 8), 90).resize((S, S), Image.NEAREST), np.float32) / 255.0
    xx = np.mgrid[0:S, 0:S][1] / S
    arr *= np.where((xx > 0.62) & (nz < (xx - 0.55) * 1.6), 0, 1)   # правый край крошится
    sm = Image.fromarray(arr.astype(np.uint8), 'L').resize((128, 128), Image.LANCZOS)
    rgba = Image.new('RGBA', (128, 128), (255, 255, 255, 0))
    rgba.putalpha(sm)
    rgba.save(os.path.join(OUT_SIGIL, 'mote_erased.png'))
    WRITTEN.append('textures/sigil/mote_erased.png')
    img = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(img)
    pts = []
    for k in range(14):
        a = 2 * math.pi * k / 14
        r = S * (0.26 + rng.random() * 0.16) * (1.0 if k % 3 else 0.7)
        pts.append((S / 2 + r * math.cos(a) * 1.15, S / 2 + r * math.sin(a) * 0.8))
    d.polygon(pts, fill=255)
    for k in range(3):                                          # трещинки-прожилки
        x, y = S * (0.35 + rng.random() * 0.3), S * (0.4 + rng.random() * 0.2)
        d.line([x, y, x + S * rng.uniform(-0.15, 0.15), y + S * rng.uniform(-0.1, 0.1)], fill=90, width=2 * SS)
    img = img.filter(ImageFilter.GaussianBlur(SS * 0.5))
    sm = img.resize((128, 128), Image.LANCZOS)
    rgba = Image.new('RGBA', (128, 128), (255, 255, 255, 0))
    rgba.putalpha(sm)
    rgba.save(os.path.join(OUT_SIGIL, 'mote_ash.png'))
    WRITTEN.append('textures/sigil/mote_ash.png')


def tex_overlay():
    """Накладка экрана стёртого (textures/gui/overlay/, цветная RGBA, растягивается на весь экран как ванильная виньетка):
    erased_vignette — выцветшие пепельные края с «зерном» бумаги, тонкими строками-вычёркиваниями у краёв, центр прозрачный;
    erased_letters — редкие бледные буквы вдоль краёв (второй слой, код медленно сдвигает его вверх и пульсирует)."""
    Wd, Ht = 1024, 512
    out = os.path.join(A, 'textures', 'gui', 'overlay')
    os.makedirs(out, exist_ok=True)
    yy, xx = np.mgrid[0:Ht, 0:Wd]
    u, v = (xx + 0.5) / Wd * 2 - 1, (yy + 0.5) / Ht * 2 - 1
    e = np.maximum(np.abs(u) ** 3.4, np.abs(v) ** 4.2)                 # «прямоугольная» виньетка: края сильнее, центр чист
    r = np.clip((np.hypot(u * 1.0, v * 1.1) - 0.7) / 0.7, 0, 1)
    k = np.clip(np.maximum(e * 1.25, r ** 1.6), 0, 1)
    rng = np.random.default_rng(24)
    grain = rng.random((Ht, Wd)).astype(np.float32)
    nz = np.asarray(Image.effect_noise((Wd // 32, Ht // 32), 80).resize((Wd, Ht), Image.BICUBIC), np.float32) / 255.0
    alpha = np.clip(k * (0.78 + 0.25 * (nz - 0.5)) + (grain - 0.5) * 0.06 * k, 0, 0.74)
    col = np.zeros((Ht, Wd, 3), np.float32)
    base = np.array([214, 210, 202], np.float32)                      # пепельно-бумажный
    dark = np.array([120, 116, 112], np.float32)
    mix = np.clip(nz * 0.6 + grain * 0.15, 0, 1)[..., None] * (k[..., None] ** 0.7)
    col[:] = base * (1 - mix * 0.45) + dark * (mix * 0.45)
    im = Image.fromarray(np.dstack([col, alpha * 255]).astype(np.uint8), 'RGBA')
    d = ImageDraw.Draw(im)
    rs = random.Random(5)
    for _ in range(30):                                           # строки-вычёркивания у краёв: тонкие, полупрозрачные
        side = rs.choice('tblr')
        if side in 'tb':
            y = rs.uniform(6, 70) if side == 't' else rs.uniform(Ht - 70, Ht - 6)
            x0 = rs.uniform(0, Wd - 260)
            x1 = x0 + rs.uniform(80, 300)
        else:
            x0 = rs.uniform(0, 110) if side == 'l' else rs.uniform(Wd - 200, Wd - 90)
            x1 = x0 + rs.uniform(40, 110)
            y = rs.uniform(10, Ht - 10)
        a = rs.randint(40, 95)
        tone = rs.choice([(70, 66, 64), (90, 84, 80), (150, 30, 40)])
        d.line([x0, y, x1, y + rs.uniform(-3, 3)], fill=tone + (a,), width=rs.choice([1, 2, 2, 3]))
    im.save(os.path.join(out, 'erased_vignette.png'))
    WRITTEN.append('textures/gui/overlay/erased_vignette.png')
    # буквы по краям (бледные, на прозрачном), тайлится по вертикали
    S2 = 4
    big = Image.new('L', (Wd * S2, Ht * S2), 0)
    d = ImageDraw.Draw(big)
    rng2 = random.Random(8)
    for _ in range(120):
        side = rng2.random()
        if side < 0.42:
            x = rng2.uniform(0.01, 0.13) * Wd
        elif side < 0.84:
            x = rng2.uniform(0.87, 0.99) * Wd
        else:
            x = rng2.uniform(0.15, 0.85) * Wd
        y = rng2.uniform(0, 1) * Ht if side < 0.84 else rng2.choice([rng2.uniform(0.02, 0.1), rng2.uniform(0.9, 0.98)]) * Ht
        h = rng2.uniform(9, 20)
        g = glyph(rng2)
        sx, sy = h * 0.35 * S2, h / 3 * S2
        for (ax, ay), (bx, by) in g[0]:
            _pline(d, [(x * S2 + ax * sx, y * S2 + ay * sy), (x * S2 + bx * sx, y * S2 + by * sy)], 1.6 * S2, fill=rng2.randint(120, 255))
    a = big.resize((Wd, Ht), Image.LANCZOS)
    lt = Image.new('RGBA', (Wd, Ht), (235, 230, 220, 0))
    lt.putalpha(a.point(lambda p: int(p * 0.7)))
    lt.save(os.path.join(out, 'erased_letters.png'))
    WRITTEN.append('textures/gui/overlay/erased_letters.png')


def textures():
    os.makedirs(OUT_SIGIL, exist_ok=True)
    tex_creation_laws()
    tex_creation_warp()
    tex_erase_ledger()
    tex_erase_plate()
    tex_erase_void()
    tex_erase_quill()
    for n in ('creation_laws', 'creation_warp', 'erase_ledger', 'erase_plate', 'erase_void', 'erase_quill'):
        WRITTEN.append('textures/sigil/%s.png' % n)
    tex_motes()
    tex_overlay()


# ================================================================== печати
def ap(delay, dur, *modes, easing='easeOutCubic', **kw):
    o = {'delay': delay, 'duration': dur, 'easing': easing, 'modes': list(modes)}
    o.update(kw)
    return o


def L(id, type, tex, radius, h=0.0, appear=None, rot=None, boost=None, color=None, br=None, pulse=None, **kw):
    o = {'id': id, 'type': type}
    if tex:
        o['texture'] = tex
    o.update({'radius': radius, 'heightOffset': h})
    if color:
        o['color'] = color
    if br is not None:
        o['brightness'] = br
    o.update(kw)
    o['appear'] = appear or ap(0, 10, 'fade')
    if rot is not None:
        o['rotation'] = {'speed': rot, **({'boost': boost} if boost else {})}
    if pulse:
        o['pulse'] = {'amp': pulse[0], 'period': pulse[1]}
    return o


def T(id, text, radius, size, h, appear, font='runic', color=None, br=None, rot=None, boost=None, repeat=1, side='outer', **kw):
    o = L(id, 'text', None, radius, h, appear, rot=rot, boost=boost, color=color, br=br, **kw)
    o.update({'text': text, 'font': font, 'size': size, 'repeat': repeat, 'side': side})
    return o


def sigil(id, comment, size, color, orientation, layers, hold=-1, expand=None, flash=None, children=None,
          dissolve=('reverse', 'collapse'), ddur=20, stagger=2, extra=None):
    o = {'comment': comment, 'size': size, 'color': color, 'orientation': orientation, 'lifetime': -1, 'hold': hold, 'layers': layers}
    if expand:
        o['expand'] = expand
    if flash:
        o['formedFlash'] = flash
    if children:
        o['onFormed'] = children
    if extra:
        o.update(extra)
    o['dissolve'] = {'modes': list(dissolve), 'duration': ddur, 'stagger': stagger}
    write('sigils/%s.json' % id, o)


STRIKE = '—' * 9          # «вычёркивание» надписью: длинные тире пишутся буква за буквой слева направо (draw), как росчерк пера


def creation_sigils():
    sigil('forbidden_creation_seal', 'Запретная школа, ступень «Мироздание» — печать каста (общая для заклинаний школы; T24). '
                                     'Искривлённая решётка пространства закручивается к центру, пять медальонов-законов мира '
                                     '(тяготение, время, причинность, пространство, мир) прорисовываются и перечёркиваются, кольцо формул, '
                                     'тёмно-золотой обод ступени, багровые дуги. Медленное тяжёлое вращение, внутреннее кольцо — против.',
          4.6, GOLD, 'ground', [
              L('glow', 'disc', 'glow', 1.0, -0.01, ap(0, 20, 'fade'), color=CRIMSON_D, br=0.45, pulse=(0.15, 60)),
              L('warp', 'disc', 'creation_warp', 0.78, 0.0, ap(0, 34, 'fade', 'twist', twist=-120, easing='easeOutCubic'), rot=-6, boost=4,
                color=ASH, br=0.35),
              L('laws', 'disc', 'creation_laws', 1.0, 0.006, ap(6, 34, 'draw', easing='easeInOutSine', startAngle=90), rot=2.5, boost=2),
              T('formula', 'ЗАКОН ПРЕЛОМЛЁН ✦ МИР ПЕРЕПИСАН ✦ ', 1.075, 0.06, 0.012, ap(22, 26, 'draw', easing='linear'), font='cyrillic',
                color=ASH, br=0.75, rot=-1.5, repeat=2),
              L('rim', 'band', 'rim', 1.14, 0.018, ap(28, 14, 'draw', startAngle=90, direction=-1), inner=0.9, repeat=1, br=0.95),
              L('arcs', 'arcs', 'arc_strip', 1.24, 0.024, ap(34, 22, 'assemble', 'fade'), count=5, arcLength=46, width=0.02, rot=-9,
                color=CRIMSON, br=1.1),
          ], flash={'color': PAPER, 'size': 1.15, 'duration': 14, 'sparks': 26}, ddur=24, stagger=3)

    sigil('erased_ground', 'Стёртое имя: «книга имён» поверх печати ступени под заклинателем — строки рукописи прорисовываются по кругу, '
                           'по ним проходит багровая черта, картуш в центре; пепельно-белое.', 2.25, ASH, 'ground', [
        L('glow', 'disc', 'glow', 0.9, -0.005, ap(0, 16, 'fade'), color=GREY, br=0.3),
        L('ledger', 'disc', 'erase_ledger', 1.0, 0.0, ap(0, 30, 'draw', easing='easeInOutSine', startAngle=90, direction=-1), rot=-3),
        T('strike', STRIKE * 6, 0.705, 0.11, 0.008, ap(34, 26, 'draw', easing='easeInOutSine'), font='latin', color=CRIMSON, br=1.3,
          rot=-3, spacing=-0.32, side='outer'),
        L('rim', 'band', 'thin_ring', 1.05, 0.012, ap(16, 14, 'draw', startAngle=-90), inner=0.98, repeat=1, color=PAPER, br=0.8),
    ], ddur=20)

    sigil('erased_quill', 'Стёртое имя: малая печать-«перо» у правой ладони заклинателя (смотрит туда же, куда он).', 0.3, ASH, 'facing', [
        L('glow', 'disc', 'glow', 1.6, -0.01, ap(0, 10, 'fade'), color=PAPER, br=0.45, pulse=(0.25, 18)),
        L('quill', 'disc', 'erase_quill', 1.0, 0.0, ap(0, 14, 'unfold', 'fade', easing='easeOutBack'), rot=30, boost=3),
        L('ring', 'band', 'thin_ring', 1.3, 0.01, ap(4, 10, 'draw'), inner=0.94, repeat=1, color=CRIMSON, br=1.2),
    ], dissolve=('collapse', 'fade'), ddur=8)

    sigil('erased_target', 'Стёртое имя: печать под целью — книга имён меньше, надпись «ТЕБЯ НЕ БЫЛО», которую перечёркивает багровая '
                           'черта; к 13 с разбирается «осколками» (cracks) с пеплом.', 1.9, ASH, 'ground', [
        L('glow', 'disc', 'glow', 0.95, -0.005, ap(0, 20, 'fade'), color=GREY, br=0.35, pulse=(0.12, 40)),
        L('ledger', 'disc', 'erase_ledger', 0.92, 0.0, ap(0, 36, 'draw', easing='easeInOutSine', startAngle=90), rot=2),
        T('words', 'ТЕБЯ НЕ БЫЛО ✕ ', 1.02, 0.1, 0.008, ap(30, 40, 'draw', easing='linear'), font='cyrillic', color=PAPER, br=0.95,
          rot=-2, repeat=3),
        T('strike', STRIKE * 9, 1.0, 0.13, 0.014, ap(100, 40, 'draw', easing='easeInOutSine'), font='latin', color=CRIMSON, br=1.5,
          rot=-2, spacing=-0.32),
        L('rim', 'band', 'thin_ring', 1.13, 0.02, ap(20, 16, 'draw', startAngle=90, direction=-1), inner=0.985, repeat=1, br=0.8),
    ], ddur=24, dissolve=('cracks',), extra={'dissolveCracks': None})

    sigil('erased_sky', 'Стёртое имя: «небесная книга» над целью (план сверху): огромная книга имён, кольцо надписи '
                        '«ЧЕГО НЕ ПОМНЯТ — ТОГО НЕТ», багровые дуги вычёркиваний; тихо вращается, гаснет к тишине.', 6.0, ASH, 'sky', [
        L('glow', 'disc', 'glow', 1.0, -0.01, ap(0, 30, 'fade'), color=GREY, br=0.22),
        L('warp', 'disc', 'creation_warp', 0.62, 0.0, ap(0, 40, 'fade'), rot=4, color=GREY, br=0.35),
        L('ledger', 'disc', 'erase_ledger', 0.9, 0.005, ap(6, 46, 'draw', easing='easeInOutSine', startAngle=90), rot=-1.5),
        T('motto', 'ЧЕГО НЕ ПОМНЯТ — ТОГО НЕТ ✦ ', 1.0, 0.055, 0.01, ap(34, 50, 'draw', easing='linear'), font='cyrillic', color=PAPER,
          br=0.85, rot=1, repeat=2),
        L('rim', 'band', 'rim', 1.1, 0.015, ap(40, 18, 'draw', startAngle=-90), inner=0.9, repeat=1, color=GOLD, br=0.7),
        L('arcs', 'arcs', 'arc_strip', 1.2, 0.02, ap(60, 30, 'assemble', 'fade'), count=6, arcLength=30, width=0.012, rot=-5,
          color=CRIMSON, br=1.0),
    ], ddur=30, dissolve=('fade', 'shatter'))

    sigil('erased_nameplate', 'Стёртое имя: табличка с ИМЕНЕМ цели над её головой (всегда к камере). Имя — слот «name» (код: ник цели; '
                              'без слота — «НЕКТО»), пишется буква за буквой 0–2 с; в 4.5 с (90-й тик печати) багровая черта перечёркивает '
                              'его слева направо; к 10.3 с буквы рассыпаются.', 0.95, PAPER, 'billboard', [
        L('glow', 'disc', 'glow', 1.0, -0.01, ap(0, 14, 'fade'), color=GREY, br=0.35),
        L('plate', 'disc', 'erase_plate', 1.0, 0.0, ap(0, 16, 'unfold', 'fade', easing='easeOutCubic'), color=ASH, br=0.85),
        T('name', 'НЕКТО', 0.0, 0.25, 0.01, ap(10, 30, 'draw', easing='linear'), font='cyrillic', side='line', slot='name', color=PAPER,
          br=1.2, change=10, changeFlash=0.6),
        T('strike', STRIKE * 2, 0.05, 0.36, 0.02, ap(90, 9, 'draw', easing='easeInCubic'), font='latin', side='line', color=CRIMSON,
          br=1.8, spacing=-0.34),
    ], flash={'color': PAPER, 'size': 0.9, 'duration': 8, 'sparks': 8}, dissolve=('shatter', 'fade'), ddur=24)

    sigil('erased_line', 'Стёртое имя: строка рун, обвивающая тело цели кольцом (3 штуки на высотах 0.5 / 1.05 / 1.6), '
                         'пишется, потом её перечёркивают — и она рвётся.', 0.62, ASH, 'ground', [
        T('runes', 'NOMEN NESCIO ✕ ', 1.0, 0.24, 0.0, ap(0, 26, 'draw', easing='linear'), font='runic', color=PAPER, br=1.25, rot=20, repeat=2),
        T('strike', STRIKE * 5, 1.0, 0.24, 0.01, ap(40, 18, 'draw', easing='easeInOutSine'), font='latin', color=CRIMSON, br=1.6, rot=20,
          spacing=-0.32),
    ], dissolve=('shatter', 'fade'), ddur=16)

    sigil('erased_void', 'Стёртое имя: пустота на месте груди (к камере) — кольцо обломков букв вокруг пустого центра, '
                         'сжимается в точку за 1 с (цель уходит в ничто).', 1.2, PAPER, 'billboard', [
        L('void', 'disc', 'erase_void', 1.0, 0.0, ap(0, 3, 'fade', 'grow', easing='easeOutCubic'), rot=-40, color=PAPER, br=1.3),
        L('ring', 'band', 'thin_ring', 0.36, 0.01, ap(0, 4, 'fade'), inner=0.9, repeat=1, color=CRIMSON, br=1.6),
    ], expand={'scale': 0.04, 'delay': 2, 'duration': 18, 'easing': 'easeInCubic'}, hold=0, dissolve=('fade',), ddur=4)

    sigil('erased_nameplate_return', 'Стёртое имя, возвращение: табличка с именем над вернувшимся (слот «name»), имя вписывается заново, '
                                     'без черты; тёплая вспышка, гаснет через 2 с.', 0.95, PAPER, 'billboard', [
        L('glow', 'disc', 'glow', 1.0, -0.01, ap(0, 10, 'fade'), color='#FFE6B0', br=0.4),
        L('plate', 'disc', 'erase_plate', 1.0, 0.0, ap(0, 10, 'unfold', 'fade'), color='#FFF1D6', br=0.9),
        T('name', 'НЕКТО', 0.0, 0.25, 0.01, ap(4, 16, 'draw', easing='linear'), font='cyrillic', side='line', slot='name', color='#FFFFFF', br=1.3),
    ], hold=26, flash={'color': '#FFF4DE', 'size': 1.0, 'duration': 10, 'sparks': 14}, dissolve=('fade',), ddur=14)


def _fix_cracks():
    """Разборка `cracks` у erased_target: пепельная крошка вместо золота (docs/sigils.md, «Распад трещинами»)."""
    p = os.path.join(A, 'sigils', 'erased_target.json')
    o = json.load(open(p, encoding='utf-8'))
    o.pop('dissolveCracks', None)
    o['dissolve'] = {'modes': ['cracks'], 'duration': 34,
                     'cracks': {'count': 8, 'rings': 1, 'irregular': 0.45, 'jag': 0.3, 'crackTime': 0.35, 'fallTime': 0.5, 'gap': 0.03,
                                'push': 0.15, 'pop': 0.2, 'fall': 0.8, 'tumble': 120, 'spin': 50, 'glow': 1.2, 'dust': 40, 'color': '#D8D2C6'}}
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(o, f, ensure_ascii=False, indent=1)
        f.write('\n')


# ================================================================== эффекты
def fx(id, comment, style_, duration, elements):
    write('fx/%s.json' % id, {'comment': comment, 'style': style_, 'duration': duration, 'elements': elements})


def E(type, delay=0, at='caster', **kw):
    o = {'type': type, 'delay': delay, 'at': at}
    o.update(kw)
    return o


def ease(d, e='easeOutCubic'):
    return {'duration': d, 'easing': e}


def fmt(v):
    v = round(v, 2)
    return str(int(v)) if v == int(v) else str(v)


def off(base, x, y, z):
    return '%s+%s,%s,%s' % (base, fmt(x), fmt(y), fmt(z))


def style():
    write('fx/styles/erased_name.json', {
        'comment': 'Стёртое имя (Запретная, «Мироздание»): бумага и чернила — пепельно-белые строки, багровые вычёркивания, серая пустота; '
                   'движение тихое и вязкое, без рывков.',
        'palette': {'primary': ASH, 'secondary': CRIMSON, 'core': '#FFFFFF', 'shadow': INK},
        'textures': {'sparks': 'spark_soft', 'runes': 'rune_band', 'shards': 'mote_erased', 'sigil': 'erase_ledger'},
        'blend': 'additive', 'motion': {'rotationScale': 0.5, 'jitter': 0.05, 'easing': 'easeInOutSine'},
        'sigilTheme': 'книга имён, вычёркивание, пепел букв'})


PLATE_Y = 2.75     # табличка имени над ногами цели
CAST = 300         # каст 15 с
SILENCE = 280      # 14.0 с — «тишина»: все элементы уже погасли, только серый мир
STRIKE_T = 290     # 14.5 с — последний росчерк: код запускает fx/erased_vanish на цели, на 300 тике прячет её


def school_fx():
    fx('school_forbidden_cast_creation', 'Запретная, ступень «Мироздание»: печать каста под заклинателем (общая для школы, как '
                                         'school_<школа>_cast_divine у других). Держится, пока код не остановит (duration −1).', 'forbidden', -1, [
        E('sigil', 0, 'caster+0,0.04,0', id='forbidden_creation_seal'),
        E('sprites', 0, 'caster+0,0.15,0', texture='mote_erased', count=100000, rate=0.35, area=4.2, speed=0.004, gravity=-0.0025,
          spin=40, size=[0.14, 0.04], life=60, color=ASH, brightness=0.7, comment='буквы-формулы медленно поднимаются от печати'),
        E('sprites', 10, 'caster+0,0.1,0', texture='spark_sharp', count=100000, rate=0.25, area=4.4, speed=0.006, gravity=-0.004,
          size=[0.1, 0.02], life=26, color=GOLD, glow=0.4),
    ])


def erased_fx():
    style()
    tgt = 'target'
    # строки-вычёркивания по телу цели: серия прямых росчерков (slash, bend 0) поперёк взгляда заклинателя, снизу вверх и обратно
    strikes = []
    rng = random.Random(24)
    heights = [0.35, 0.7, 1.05, 1.4, 1.75, 1.2, 0.55, 0.9, 1.55, 0.45, 1.3, 0.8, 1.65, 1.0, 0.6, 1.45]
    for k, hgt in enumerate(heights):
        strikes.append(E('slash', 124 + 7 * k, off(tgt, rng.uniform(-0.08, 0.08), hgt, 0), radius=0.75, arc=82, thickness=0.05,
                         bend=0, secondary=0.35 if k % 3 == 0 else 0, grow=5, life=16, tilt=rng.uniform(-9, 9), dir=1 if k % 2 == 0 else -1,
                         color=CRIMSON if k % 3 != 1 else PAPER, brightness=1.4))
    lines = [E('sigil', 60 + 22 * k, off(tgt, 0, h, 0), follow=True, id='erased_line', until=196 + 18 * k)
             for k, h in enumerate((0.5, 1.05, 1.6))]
    fx('erased_name_cast', 'Стёртое имя, каст 15 с (300 тиков). Точки: caster — заклинатель, target — цель. Ни одного луча/нити от заклинателя '
                           'к цели: связь — табличка с именем над целью и жест «вычеркнуть». '
                           '0–2 с печать ступени «Мироздание» и книга имён под заклинателем, перо у ладони; 1–3.5 с над целью табличка, '
                           'её ИМЯ пишется буква за буквой (слот name); 2–6 с мир вокруг цели выцветает (tint, серое), под ней книга имён, '
                           'над ней небесная книга; 6 с — жест «вычеркнуть»: багровая черта по имени; 6.2–11.5 с по телу бегут строки-'
                           'вычёркивания, кольца рун обвивают тело и рвутся, контур распадается на буквы; 11–13.8 с буквы стягивает '
                           'вихрем; 14.0–14.5 с ТИШИНА — всё погасло, только серый мир; 14.5 с (290) код запускает fx/erased_vanish на цели, '
                           'на 300 цель исчезает. Хвост — серость уходит до 330.',
       'erased_name', 330, [
           # заклинатель
           E('sigil', 0, 'caster+0,0.04,0', id='forbidden_creation_seal', until=284),
           E('sigil', 8, 'caster+0,0.07,0', id='erased_ground', until=280),
           E('sprites', 0, 'caster+0,0.15,0', duration=270, texture='mote_erased', count=400, rate=0.9, area=3.8, speed=0.004,
             gravity=-0.003, spin=40, size=[0.16, 0.04], life=56, color=ASH, brightness=0.75, comment='буквы поднимаются от печатей'),
           E('sprites', 6, 'caster+0,0.1,0', duration=40, texture='spark_soft', count=60, rate=1.5, area=3.0, speed=0.01, gravity=-0.004,
             size=[0.14, 0.02], life=30, color=PAPER, glow=0.4),
           E('sigil', 22, 'caster.hand', follow=True, id='erased_quill', until=296, comment='перо у ладони — «пишет» и «вычёркивает»'),
           E('sprites', 24, 'caster.hand', follow=True, duration=260, texture='spark_soft', count=300, rate=1.1, spread=0.08, speed=0.004,
             gravity=-0.002, size=[0.07, 0.01], life=14, color=PAPER, glow=0.5, comment='след пера в воздухе'),
           E('flash', 118, 'caster.hand', follow=True, duration=8, size=0.8, rays=4, color=CRIMSON, comment='6 с: росчерк рукой'),
           E('flash', 288, 'caster.hand', follow=True, duration=10, size=1.2, rays=6, anamorphic=3, color=CRIMSON,
             comment='14.4 с: последний росчерк'),
           # цель: табличка с именем
           E('sigil', 24, off(tgt, 0, PLATE_Y, 0), follow=True, id='erased_nameplate', until=206,
             comment='имя пишется 34–64 тик, черта по имени 114–123 тик (6 с), рассыпается 206–230'),
           E('slash', 114, off(tgt, 0, PLATE_Y + 0.02, 0), follow=True, radius=0.62, arc=96, thickness=0.07, bend=0, secondary=0.5, grow=8,
             life=20, tilt=-4, dir=1, color=CRIMSON, brightness=1.8, comment='голова росчерка по имени (сама черта — в табличке)'),
           E('flash', 122, off(tgt, 0.45, PLATE_Y, 0), follow=True, duration=8, size=0.6, rays=4, color=CRIMSON),
           E('sprites', 206, off(tgt, 0, PLATE_Y, 0), follow=True, duration=16, texture='mote_erased', count=40, rate=2.5, spread=0.35,
             speed=0.012, gravity=0.004, spin=90, tumble=1, size=[0.2, 0.06], life=40, color=PAPER, comment='буквы имени осыпаются'),
           # мир вокруг цели выцветает; книги имён под и над ней
           E('tint', 40, tgt, duration=290, radius=12, color='#8E8A84', strength=0.6, saturation=0.08,
             **{'in': ease(110, 'easeInOutSine'), 'out': ease(30, 'easeInOutSine')},
             comment='мир серый: saturation — доп. параметр (0 — ч/б); без него tint просто серит'),
           E('sigil', 30, off(tgt, 0, 0.05, 0), follow=True, id='erased_target', until=262),
           E('sigil', 44, off(tgt, 0, 9.0, 0), id='erased_sky', until=262),
           *lines,
           *strikes,
           E('aura', 136, tgt, target='target', duration=136, thickness=0.06, pulse=[0.25, 18], motes=20, texture='mote_erased',
             color=PAPER, **{'in': ease(30), 'out': ease(14)}, comment='контур цели светится и сыплется буквами'),
           E('sprites', 140, off(tgt, 0, 1.0, 0), follow=True, duration=70, texture='mote_erased', count=120, rate=1.6, spread=0.42,
             speed=0.012, gravity=-0.0035, spin=60, tumble=0.5, size=[0.18, 0.05], life=44, color=PAPER),
           E('sprites', 196, off(tgt, 0, 1.0, 0), follow=True, duration=74, texture='mote_erased', count=300, rate=4.0, spread=0.48,
             speed=0.018, gravity=-0.004, spin=80, tumble=0.6, size=[0.2, 0.05], life=36, color=PAPER, comment='распад усиливается'),
           E('sprites', 170, off(tgt, 0, 1.0, 0), follow=True, duration=100, texture='mote_ash', count=160, rate=1.6, spread=0.5,
             speed=0.01, gravity=-0.002, spin=40, tumble=1, size=[0.16, 0.06], life=50, color='#2A2628', blend='translucent',
             comment='чернильный пепел'),
           E('vortex', 222, off(tgt, 0, 0.1, 0), duration=54, radius=2.2, height=2.4, arms=3, speed=2.2, pull=1, texture='mote_erased',
             particles=70, life=22, size=0.15, color=ASH, **{'out': ease(10)}, comment='11–13.8 с: буквы стягивает к телу — вдох перед тишиной'),
       ])

    fx('erased_vanish', 'Стёртое имя: исчезновение (код на 290 тике каста, caster = цель; на 10 тике этого эффекта = 300 тике каста '
                        'цель скрывают). Тело рассыпается буквами и пеплом, пустота на месте груди сжимается в точку, по земле — '
                        'бледное кольцо; ни вспышки, ни звона — тихо. Годится и для других случаев «исчезнуть из мира».',
       'erased_name', 50, [
           E('sigil', 0, 'caster+0,1.0,0', id='erased_void', until=24),
           E('sprites', 0, 'caster+0,1.0,0', duration=4, texture='mote_erased', count=90, rate=30, spread=0.45, speed=0.07, gravity=-0.002,
             spin=120, tumble=1, size=[0.22, 0.05], life=34, color=PAPER),
           E('sprites', 0, 'caster+0,1.0,0', duration=6, texture='mote_ash', count=50, rate=10, spread=0.5, speed=0.05, gravity=-0.001,
             tumble=1, size=[0.2, 0.08], life=40, color='#1E1B1E', blend='translucent'),
           E('aura', 0, 'caster', target='caster', duration=12, thickness=0.1, motes=30, texture='mote_erased', color=PAPER,
             **{'in': ease(1), 'out': ease(10, 'easeInCubic')}),
           E('wave', 2, 'caster+0,1.0,0', duration=14, shape='sphere', radius=1.6, rim=0.8, color=ASH, brightness=0.5),
           E('wave', 8, 'caster+0,0.05,0', duration=30, shape='ring', radius=4.0, thickness=0.18, color=ASH, brightness=0.5),
           E('decal', 8, 'caster+0,0.03,0', duration=42, texture='void', radius=0.9, grow=10, fadeOut=30, color=VOID, blend='translucent',
             comment='пустое место, где стояла цель'),
           E('sprites', 14, 'caster+0,1.4,0', duration=24, texture='mote_erased', count=16, rate=0.7, spread=0.5, speed=0.002,
             gravity=0.0015, spin=30, size=[0.12, 0.05], life=30, color=GREY, comment='последние буквы оседают'),
       ])

    fx('erased_return', 'Стёртое имя: возвращение в мир (код при истечении 10 мин / «Благословении», caster = вернувшийся, follow). '
                        '0–18 буквы со всех сторон стягиваются к нему, контур проявляется; над головой заново вписывается имя (слот name); '
                        'на 18 тике — мягкая тёплая вспышка, кольцо: мир «вспомнил». Модель показывать с 18 тика (по желанию — '
                        'полупрозрачной 18–30).', 'erased_name', 60, [
        E('vortex', 0, 'caster+0,0.1,0', follow=True, duration=20, radius=2.6, height=2.2, arms=4, speed=3, pull=1, texture='mote_erased',
          particles=90, life=18, size=0.16, color=PAPER),
        E('aura', 4, 'caster', target='caster', duration=40, thickness=0.08, motes=16, texture='spark_soft', color='#FFF1D6',
          **{'in': ease(14), 'out': ease(24, 'easeInSine')}),
        E('sigil', 6, 'caster+0,%s,0' % fmt(PLATE_Y), follow=True, id='erased_nameplate_return', until=56),
        E('tint', 0, 'caster', duration=36, radius=6, color='#8E8A84', strength=0.4, saturation=0.2,
          **{'in': ease(2), 'out': ease(30, 'easeInOutSine')}, comment='серость уходит — мир снова цветной'),
        E('flash', 18, 'caster+0,1.1,0', follow=True, duration=12, size=2.0, rays=6, anamorphic=3, color='#FFF4DE'),
        E('wave', 18, 'caster+0,0.05,0', duration=22, shape='ring', radius=3.2, thickness=0.14, color='#FFE6B0', brightness=0.8),
        E('sprites', 18, 'caster+0,0.9,0', follow=True, duration=20, texture='spark_soft', count=50, rate=2.5, spread=0.4, speed=0.02,
          gravity=-0.005, size=[0.16, 0.02], life=26, color='#FFE6B0', glow=0.6, comment='цвет возвращается тёплыми искрами'),
    ])

    fx('erased_self', 'Стёртое имя: тихий фон у самого стёртого (только ему: Fx…only(игрок), duration −1, follow; код останавливает при '
                      'возвращении). Редкие бледные буквы и пепел медленно плывут вокруг — «мир тебя не помнит». Накладка экрана — '
                      'textures/gui/overlay/erased_*.png (код).', 'erased_name', -1, [
        E('sprites', 0, 'caster+0,1.2,0', follow=True, texture='mote_erased', count=100000, rate=0.12, spread=3.2, speed=0.002,
          gravity=-0.0006, spin=20, size=[0.12, 0.04], life=80, color=GREY, brightness=0.6),
        E('sprites', 0, 'caster+0,1.6,0', follow=True, texture='mote_ash', count=100000, rate=0.06, spread=3.6, speed=0.002,
          gravity=0.0008, tumble=0.8, size=[0.12, 0.05], life=90, color='#4A4648', blend='translucent'),
    ])


# ================================================================== иконки
def _c(h, a=255):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)


def _icon(size, draw, out, frame=None, k=8, crisp=False):
    """Рисуем в k× и уменьшаем LANCZOS (как gen_divine_t21 / gen_illusion_fx). frame: (обод, фон) — квадрат ступени."""
    S = size * k
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if frame:
        rim, bg = frame
        d.rectangle([k * 0.5, k * 0.5, S - k * 0.5, S - k * 0.5], fill=_c(bg))
        w = S * 0.07
        d.rectangle([S * 0.05 - w / 2, S * 0.05 - w / 2, S * 0.95 + w / 2, S * 0.95 + w / 2], outline=_c(rim), width=int(w))
    draw(d, S)
    sm = im.resize((size, size), Image.LANCZOS)
    if crisp:
        a = np.asarray(sm).copy()
        a[..., 3] = np.where(a[..., 3] < 70, 0, np.where(a[..., 3] > 150, 255, a[..., 3]))
        sm = Image.fromarray(a, 'RGBA')
    path = os.path.join(A, out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sm.save(path)
    WRITTEN.append(out)


def icon_erased_name(d, S):
    """Табличка с именем: тёмные буквы на бледном картуше, правый край таблички крошится квадратиками-буквами вверх;
    через всё — багровый росчерк пера."""
    d.rectangle([S * 0.12, S * 0.3, S * 0.7, S * 0.7], fill=_c('#ECE7DB'))
    d.line([S * 0.12, S * 0.3, S * 0.7, S * 0.3], fill=_c('#8A8478'), width=int(S * 0.05))
    d.line([S * 0.12, S * 0.7, S * 0.7, S * 0.7], fill=_c('#8A8478'), width=int(S * 0.05))
    for x, y, q in ((0.76, 0.36, 0.06), (0.75, 0.58, 0.055), (0.84, 0.46, 0.05), (0.82, 0.26, 0.045), (0.9, 0.34, 0.035), (0.88, 0.16, 0.03)):
        d.rectangle([S * (x - q), S * (y - q), S * (x + q), S * (y + q)], fill=_c('#ECE7DB'))
    for k, x in enumerate((0.19, 0.31, 0.43, 0.55)):                              # «буквы» имени
        d.rectangle([S * x, S * 0.39, S * (x + 0.075), S * 0.61], fill=_c('#1A1612'))
        if k % 2 == 0:
            d.rectangle([S * (x + 0.075), S * 0.39, S * (x + 0.11), S * 0.45], fill=_c('#1A1612'))
    d.line([S * 0.06, S * 0.64, S * 0.94, S * 0.38], fill=_c('#C8182E'), width=int(S * 0.13))
    d.line([S * 0.12, S * 0.615, S * 0.88, S * 0.39], fill=_c('#FF6A78'), width=int(S * 0.04))


def effect_erased(d, S):
    """Статус «Стёрт»: бледный силуэт по плечи (тёмный контур), правая половина рассыпается квадратиками; багровая черта наискось."""
    col, edge = _c('#D8D2C6'), _c('#26222A')
    d.ellipse([S * 0.27, S * 0.08, S * 0.63, S * 0.44], fill=col, outline=edge, width=int(S * 0.06))
    d.rounded_rectangle([S * 0.08, S * 0.5, S * 0.82, S * 1.04], radius=int(S * 0.18), fill=col, outline=edge, width=int(S * 0.06))
    d.rectangle([S * 0.56, S * 0.0, S * 1.0, S * 1.0], fill=(0, 0, 0, 0))                      # правая часть «стёрта»
    for x, y, q in ((0.6, 0.18, 0.05), (0.6, 0.34, 0.05), (0.7, 0.26, 0.04), (0.61, 0.6, 0.055), (0.61, 0.8, 0.055), (0.72, 0.7, 0.05),
                    (0.72, 0.9, 0.045), (0.82, 0.62, 0.035), (0.84, 0.82, 0.035), (0.8, 0.14, 0.03), (0.92, 0.72, 0.03)):
        d.rectangle([S * (x - q), S * (y - q), S * (x + q), S * (y + q)], fill=col)
    d.line([S * 0.02, S * 0.74, S * 0.98, S * 0.36], fill=edge, width=int(S * 0.17))
    d.line([S * 0.02, S * 0.74, S * 0.98, S * 0.36], fill=_c('#E0203A'), width=int(S * 0.1))


def icons():
    _icon(16, icon_erased_name, 'textures/gui/spell_icons/erased_name.png', frame=(GOLD, '#050304'))
    _icon(18, effect_erased, 'textures/mob_effect/erased.png', crisp=True)


def sheet(path):
    """Лист-обзор текстур (для проверки глазами)."""
    names = ['creation_laws', 'creation_warp', 'erase_ledger', 'erase_plate', 'erase_void', 'erase_quill', 'mote_erased', 'mote_ash']
    cell, cols = 320, 4
    out = Image.new('RGB', (cell * cols, cell * 2 + 360), (14, 13, 16))
    tint = (233, 228, 216)
    for i, n in enumerate(names):
        a = Image.open(os.path.join(OUT_SIGIL, n + '.png')).split()[3].resize((cell - 16, cell - 16), Image.LANCZOS)
        out.paste(Image.new('RGB', a.size, tint if n != 'creation_laws' else (212, 160, 23)), ((i % cols) * cell + 8, (i // cols) * cell + 8), a)
    bg = Image.new('RGB', (cell * cols - 16, 340), (60, 90, 50))                    # накладка поверх «мира»
    for x in range(0, bg.width, 40):
        ImageDraw.Draw(bg).rectangle([x, 200, x + 38, 340], fill=(90 + (x // 40) % 3 * 10, 70, 40))
    ov = Image.open(os.path.join(A, 'textures', 'gui', 'overlay', 'erased_vignette.png')).resize(bg.size)
    lt = Image.open(os.path.join(A, 'textures', 'gui', 'overlay', 'erased_letters.png')).resize(bg.size)
    bg.paste(ov, (0, 0), ov)
    bg.paste(lt, (0, 0), lt)
    out.paste(bg, (8, cell * 2 + 10))
    out.save(path)
    print('sheet', path)


if __name__ == '__main__':
    textures()
    creation_sigils()
    _fix_cracks()
    school_fx()
    erased_fx()
    icons()
    if '--sheet' in sys.argv:
        sheet(sys.argv[sys.argv.index('--sheet') + 1])
    print('\n'.join(WRITTEN))
