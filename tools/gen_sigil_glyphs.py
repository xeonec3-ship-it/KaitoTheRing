#!/usr/bin/env python3
"""
Атласы символов для слоя печати `text` (T07, docs/sigils.md, раздел «Надписи»).

Три шрифта, белое на прозрачном (цвет задаёт печать):
  runic    — свои руны в стиле печатей мода: прямые штрихи со скруглёнными концами по сетке узлов 3×4, вертикальная основа
             (как `rune_band`). Одна руна на звук: латиница и кириллица пишутся одними рунами (А = A, Б = B, В = V …),
             у Ж Ч Ш Щ Ъ Ь Э Ю Я Q W X — свои. Цифры — «монастырские» (цистерцианские) знаки: основа и метка в углу.
  latin    — каллиграфичная антиква с засечками: Cormorant Garamond Bold Italic (шрифт под OFL, лежит в tools/fonts/).
  cyrillic — та же гарнитура, кириллица; всё, чего в ней нет (цифры, латиница, знаки), берётся из `latin` (поле fallback).
У всех трёх — общие украшения-разделители: · • ✦ ✧ ◆ ◇ ☉ ☽ ★ ❖.

Атлас — сетка 16 × N ячеек по 128 px (рисуется в 4 раза крупнее и уменьшается — края гладкие). Ячейка = «кегль»: квадрат,
в котором буква стоит на базовой линии `baseline` (доля высоты ячейки сверху), по горизонтали — по центру своей ширины.
Рядом с PNG пишется карта glyphs_<font>.json:
  { "font", "texture", "cell", "cols", "rows", "baseline", "space", "upper", "fallback",
    "glyphs": { "<символ>": [номер ячейки, ширина], … } }
ширина (advance) — доля высоты ячейки; ячейка k — столбец k % cols, строка k / cols.

Запуск:  python3 tools/gen_sigil_glyphs.py      (нужны Pillow и numpy)
Пишет:   src/main/resources/assets/pohsmp_core/textures/sigil/glyphs_{runic,latin,cyrillic}.{png,json}
         docs/media/sigil_glyphs.png — лист-образец всех трёх атласов
"""
import json
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'textures', 'sigil')
MEDIA = os.path.join(HERE, '..', 'docs', 'media')
FONTS = os.path.join(HERE, 'fonts')

CELL, SS, COLS = 128, 4, 16           # итоговая ячейка, сверхвыборка, столбцов
CB = CELL * SS                         # ячейка при рисовании
BASE = 0.70                            # базовая линия (доля ячейки сверху)
CAP = 0.44                             # высота прописных (доля ячейки) — под неё подогнаны и руны
PAD = 3 * SS                           # поле внутри ячейки, чтобы при уменьшении соседи не подмешивались

ORNAMENTS = '·•✦✧◆◇☉☽★❖'


# ------------------------------------------------------------------ общее
def new_atlas(n):
    rows = max(1, math.ceil(n / COLS))
    return Image.new('L', (COLS * CB, rows * CB), 0), rows


def cell_xy(k):
    return (k % COLS) * CB, (k // COLS) * CB


def save_atlas(img, rows, name, meta):
    small = img.resize((COLS * CELL, rows * CELL), Image.LANCZOS)
    rgba = Image.new('RGBA', small.size, (255, 255, 255, 0))
    rgba.putalpha(small)
    os.makedirs(OUT, exist_ok=True)
    rgba.save(os.path.join(OUT, name + '.png'), optimize=True)
    meta = {'font': meta['font'], 'texture': name, 'cell': CELL, 'cols': COLS, 'rows': rows, 'baseline': BASE,
            'capHeight': CAP, 'space': meta['space'], 'upper': meta.get('upper', False), 'fallback': meta.get('fallback'),
            'glyphs': meta['glyphs']}
    with open(os.path.join(OUT, name + '.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')
    print('wrote', name, small.size, len(meta['glyphs']), 'символов')
    return small


def round_line(d, pts, w):
    """Ломаная со скруглёнными концами и стыками (штрих рун)."""
    d.line(pts, fill=255, width=int(w), joint='curve')
    r = w / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=255)


# ------------------------------------------------------------------ украшения (во всех атласах)
def ornament(d, ch, cx, cy, h, w):
    """Разделитель высотой ~h с центром (cx, cy) — те же мотивы, что в текстурах печатей."""
    if ch == '·':
        r = w * 0.95
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    elif ch == '•':
        r = h * 0.17
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    elif ch in '✦✧':
        R, r = h * 0.5, h * 0.11
        pts = []
        for i in range(8):
            a = -math.pi / 2 + i * math.pi / 4
            rr = R if i % 2 == 0 else r
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        if ch == '✦':
            d.polygon(pts, fill=255)
        else:
            d.line(pts + [pts[0]], fill=255, width=int(w * 0.8), joint='curve')
    elif ch in '◆◇':
        R = h * 0.42
        pts = [(cx, cy - R), (cx + R * 0.62, cy), (cx, cy + R), (cx - R * 0.62, cy)]
        if ch == '◆':
            d.polygon(pts, fill=255)
        else:
            d.line(pts + [pts[0]], fill=255, width=int(w), joint='curve')
    elif ch == '☉':
        R = h * 0.4
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=255, width=int(w))
        r = w * 1.1
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    elif ch == '☽':
        R = h * 0.42
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
        o = R * 0.42
        d.ellipse([cx - R + o, cy - R - o * 0.25, cx + R + o, cy + R - o * 0.25], fill=0)
    elif ch == '★':
        R, r = h * 0.5, h * 0.2
        pts = [(cx + math.cos(-math.pi / 2 + i * math.pi / 5) * (R if i % 2 == 0 else r),
                cy + math.sin(-math.pi / 2 + i * math.pi / 5) * (R if i % 2 == 0 else r)) for i in range(10)]
        d.polygon(pts, fill=255)
    elif ch == '❖':
        R = h * 0.25
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            x, y = cx + dx * R, cy + dy * R
            pts = [(x, y - R * 0.95), (x + R * 0.95, y), (x, y + R * 0.95), (x - R * 0.95, y)]
            d.polygon(pts, fill=255)
        r = R * 0.35
        d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=0)


ORN_ADV = {'·': 0.30, '•': 0.36, '✦': 0.56, '✧': 0.56, '◆': 0.46, '◇': 0.46, '☉': 0.52, '☽': 0.50, '★': 0.56, '❖': 0.56}


def draw_ornaments(img, start, glyphs, stroke):
    d = ImageDraw.Draw(img)
    for i, ch in enumerate(ORNAMENTS):
        k = start + i
        x0, y0 = cell_xy(k)
        cy = y0 + CB * (BASE - CAP / 2)              # по середине высоты прописных
        ornament(d, ch, x0 + CB / 2, cy, CB * CAP, stroke)
        glyphs[ch] = [k, ORN_ADV[ch]]
    return start + len(ORNAMENTS)


# ------------------------------------------------------------------ руны
RUNE_W, RUNE_H = 0.30, CAP + 0.08                # ширина и высота руны (доли ячейки); чуть выше прописных — руны «весомее»
GRID = [(x, y) for y in range(4) for x in range(3)]

# Звук → руна: кириллица пишется рунами своих латинских звуков, у остальных — свои.
RUNE_KEYS = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + ['ZH', 'CH', 'SH', 'SCH', 'HARD', 'SOFT', 'EH', 'YU', 'YA']
CYR = {'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'E', 'Ж': 'ZH', 'З': 'Z', 'И': 'I', 'Й': 'J',
       'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F',
       'Х': 'H', 'Ц': 'C', 'Ч': 'CH', 'Ш': 'SH', 'Щ': 'SCH', 'Ъ': 'HARD', 'Ы': 'Y', 'Ь': 'SOFT', 'Э': 'EH', 'Ю': 'YU',
       'Я': 'YA'}


def rune_strokes(rng):
    """Руна: вертикальная основа (иногда две) + 1–3 ветви от основы: косые, перекладины, «клювы», петли."""
    sx = rng.choice([0, 1, 1, 2])
    strokes = [((sx, 0), (sx, 3))]
    if rng.random() < 0.18:                                    # вторая основа (как у H, M)
        ox = 2 if sx == 0 else 0
        strokes.append(((ox, 0), (ox, 3)))
    side = [s for s in (-1, 1) if 0 <= sx + s <= 2]
    for _ in range(rng.choice([1, 2, 2, 3])):
        kind = rng.random()
        s = rng.choice(side)
        y = rng.choice([0, 1, 2])
        if kind < 0.40:                                        # косая ветвь от основы
            dy = rng.choice([-1, 1])
            y = max(0, min(3, y + (1 if dy < 0 and y == 0 else 0)))
            strokes.append(((sx, y), (sx + s, max(0, min(3, y + dy)))))
        elif kind < 0.58:                                      # перекладина
            strokes.append(((sx, y), (sx + s, y)))
        elif kind < 0.80:                                      # «клюв»: к узлу и обратно на основу ниже
            strokes.append(((sx, y), (sx + s, y + 0.5), (sx, min(3, y + 1))))
        else:                                                  # длинная косая через всю руну
            strokes.append(((sx - s if 0 <= sx - s <= 2 else sx, 0), (sx + s, 3)))
    dot = rng.random() < 0.22
    return strokes, dot


def rune_sig(g):
    strokes, dot = g
    return tuple(sorted(tuple(map(tuple, s)) for s in strokes)) + (dot,)


def make_runes():
    rng = random.Random(0x5161)                               # одно зерно — один алфавит; меняйте, если хотите другой
    seen, runes = set(), {}
    for key in RUNE_KEYS:
        while True:
            g = rune_strokes(rng)
            sig = rune_sig(g)
            n = len(g[0])
            if sig not in seen and 2 <= n <= 4:
                seen.add(sig)
                runes[key] = g
                break
    return runes


def draw_rune(d, x0, y0, g, w):
    strokes, dot = g
    rw, rh = CB * RUNE_W, CB * RUNE_H
    xs = [p[0] for s in strokes for p in s]
    lo, hi = min(xs), max(xs) + (0.55 if dot else 0)        # руна стоит по центру своих штрихов, а не сетки
    left = x0 + CB / 2 - (lo + hi) / 2 * rw / 2
    top = y0 + CB * BASE - rh
    P = lambda x, y: (left + x * rw / 2, top + y * rh / 3)
    for s in strokes:
        round_line(d, [P(*p) for p in s], w)
    if dot:
        r = w * 0.85
        x, y = P(max(xs) + 0.55, 1.5)
        d.ellipse([x - r, y - r, x + r, y + r], fill=255)


def draw_cistercian(d, x0, y0, n, w):
    """Монастырская цифра (единицы): основа + метка в правом верхнем углу; 0 — основа с кольцом."""
    rh = CB * RUNE_H
    cx, top, q = x0 + CB / 2, y0 + CB * BASE - rh, rh * 0.36
    round_line(d, [(cx, top), (cx, top + rh)], w)
    A, B = (cx, top), (cx + q, top)                            # верх основы, правый верх
    C, D = (cx, top + q), (cx + q, top + q)                    # на трети вниз
    marks = {1: [[A, B]], 2: [[C, D]], 3: [[A, D]], 4: [[C, B]], 5: [[A, B], [C, B]], 6: [[B, D]],
             7: [[A, B, D]], 8: [[C, D, B]], 9: [[A, B, D, C]]}
    if n == 0:
        r = q * 0.42
        cy = top + rh * 0.5
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=255, width=int(w))
    for m in marks.get(n, []):
        round_line(d, m, w)


def runic():
    runes = make_runes()
    keys = RUNE_KEYS
    punct = ['.', ',', ':', ';', '!', '?', '-', "'"]
    total = len(keys) + 10 + len(punct) + len(ORNAMENTS)
    img, rows = new_atlas(total)
    d = ImageDraw.Draw(img)
    w = CB * 0.05
    glyphs, k = {}, 0
    adv = RUNE_W + 0.16
    index = {}
    for key in keys:
        x0, y0 = cell_xy(k)
        draw_rune(d, x0, y0, runes[key], w)
        index[key] = k
        k += 1
    for ch in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        glyphs[ch] = [index[ch], round(adv, 3)]
    for ch, key in CYR.items():
        glyphs[ch] = [index[key], round(adv, 3)]
    for n in range(10):
        x0, y0 = cell_xy(k)
        draw_cistercian(d, x0, y0, n, w)
        glyphs[str(n)] = [k, round(RUNE_W * 0.9 + 0.12, 3)]
        k += 1
    # знаки: точки-«узлы» вместо привычной пунктуации, чтобы не выбиваться из рун
    for ch in punct:
        x0, y0 = cell_xy(k)
        cx, base, top = x0 + CB / 2, y0 + CB * BASE, y0 + CB * (BASE - RUNE_H)
        r = w * 0.9
        dots = {'.': [base - r], ',': [base - r], ':': [base - r, top + CB * RUNE_H * 0.35], ';': [base - r, top + CB * RUNE_H * 0.35],
                '!': [base - r], '?': [base - r], '-': [], "'": [top + r]}[ch]
        for y in dots:
            d.ellipse([cx - r, y - r, cx + r, y + r], fill=255)
        if ch == '-':
            round_line(d, [(cx - CB * 0.1, base - CB * RUNE_H / 2), (cx + CB * 0.1, base - CB * RUNE_H / 2)], w)
        if ch == '!':
            round_line(d, [(cx, top), (cx, base - CB * 0.12)], w)
        if ch == '?':
            round_line(d, [(cx - CB * 0.07, top + CB * 0.05), (cx, top), (cx + CB * 0.07, top + CB * 0.08), (cx, base - CB * 0.14)], w)
        if ch == ',':
            round_line(d, [(cx, base - r), (cx - CB * 0.04, base + CB * 0.07)], w * 0.8)
        glyphs[ch] = [k, 0.3 if ch != '-' else 0.4]
        k += 1
    k = draw_ornaments(img, k, glyphs, w)
    return save_atlas(img, rows, 'glyphs_runic', {'font': 'runic', 'space': 0.30, 'upper': True, 'glyphs': glyphs})


# ------------------------------------------------------------------ буквы из шрифта
def load_font(name):
    return ImageFont.truetype(os.path.join(FONTS, name), int(CB * CAP / 0.63))   # у Cormorant прописные ≈ 0.63 кегля


def missing_mask(font):
    m = font.getmask('')
    return bytes(m), m.size


def has_glyph(font, ch, notdef):
    m = font.getmask(ch)
    return (bytes(m), m.size) != notdef


def draw_text_glyphs(img, chars, fonts, start, glyphs):
    """chars рисуются первым шрифтом из fonts, в котором они есть; возвращает следующий свободный номер ячейки."""
    d = ImageDraw.Draw(img)
    k = start
    notdefs = [missing_mask(f) for f in fonts]
    for ch in chars:
        font = next((f for f, nd in zip(fonts, notdefs) if has_glyph(f, ch, nd)), None)
        if font is None:
            print('  нет в шрифте:', repr(ch))
            continue
        x0, y0 = cell_xy(k)
        feat = ['lnum', 'tnum'] if ch.isdigit() else None      # цифры прописные и одной ширины — счётчик не «пляшет»
        adv = font.getlength(ch, features=feat)
        x = x0 + (CB - adv) / 2
        y = y0 + CB * BASE
        l, t, r, b = d.textbbox((x, y), ch, font=font, anchor='ls', features=feat)
        dx = 0                                               # курсивные хвосты не должны вылезать из ячейки
        if l + dx < x0 + PAD:
            dx = x0 + PAD - l
        if r + dx > x0 + CB - PAD:
            dx = x0 + CB - PAD - r
        if t < y0 + PAD or b > y0 + CB - PAD:
            print('  выше/ниже ячейки:', repr(ch), t - y0, b - y0)
        d.text((x + dx, y), ch, font=font, fill=255, anchor='ls', features=feat)
        glyphs[ch] = [k, round(adv / CB, 3)]
        k += 1
    return k


LATIN_CHARS = [chr(c) for c in range(33, 127)] + list('«»—–…’‘“”№')


def latin():
    f = load_font('CormorantGaramond-BoldItalic-latin.woff')
    chars = [c for c in LATIN_CHARS if c not in ORNAMENTS]
    img, rows = new_atlas(len(chars) + len(ORNAMENTS))
    glyphs = {}
    k = draw_text_glyphs(img, chars, [f], 0, glyphs)
    draw_ornaments(img, k, glyphs, CB * 0.035)
    space = round(f.getlength(' ') / CB, 3)
    return save_atlas(img, rows, 'glyphs_latin', {'font': 'latin', 'space': space, 'glyphs': glyphs})


def cyrillic():
    fc = load_font('CormorantGaramond-BoldItalic-cyrillic.woff')
    fl = load_font('CormorantGaramond-BoldItalic-latin.woff')
    letters = [chr(c) for c in range(0x410, 0x450)] + ['Ё', 'ё']
    extra = list('0123456789.,:;!?-—«»()…№')                  # самое нужное, чтобы атлас годился и без запасного
    img, rows = new_atlas(len(letters) + len(extra) + len(ORNAMENTS))
    glyphs = {}
    k = draw_text_glyphs(img, letters + extra, [fc, fl], 0, glyphs)
    draw_ornaments(img, k, glyphs, CB * 0.035)
    space = round(fl.getlength(' ') / CB, 3)
    return save_atlas(img, rows, 'glyphs_cyrillic', {'font': 'cyrillic', 'space': space, 'fallback': 'latin', 'glyphs': glyphs})


# ------------------------------------------------------------------ лист-образец (docs/media)
def sheet(atlases):
    """Атласы на тёмном фоне в цветах печатей — для отчёта и глаз."""
    colors = [(242, 210, 122), (143, 243, 255), (180, 155, 255)]
    titles = ['runic', 'latin', 'cyrillic']
    w = COLS * CELL // 2
    blocks = []
    for a, c in zip(atlases, colors):
        s = a.resize((a.width // 2, a.height // 2), Image.LANCZOS)
        glow = s.filter(ImageFilter.GaussianBlur(4))
        arr = np.clip(np.asarray(s, np.float32) + np.asarray(glow, np.float32) * 0.8, 0, 255) / 255.0
        rgb = np.zeros((s.height, s.width, 3), np.float32)
        for i in range(3):
            rgb[..., i] = 14 + arr * (c[i] - 14)
        blocks.append(Image.fromarray(rgb.astype(np.uint8)))
    pad = 24
    h = sum(b.height for b in blocks) + pad * (len(blocks) + 1) + 40 * len(blocks)
    out = Image.new('RGB', (w + pad * 2, h), (14, 12, 22))
    d = ImageDraw.Draw(out)
    lab = ImageFont.truetype(os.path.join(FONTS, 'CormorantGaramond-BoldItalic-latin.woff'), 30)
    y = pad
    for b, t, c in zip(blocks, titles, colors):
        d.text((pad, y), 'glyphs_' + t, font=lab, fill=c)
        y += 40
        out.paste(b, (pad, y))
        y += b.height + pad
    os.makedirs(MEDIA, exist_ok=True)
    out.save(os.path.join(MEDIA, 'sigil_glyphs.png'), optimize=True)
    print('wrote docs/media/sigil_glyphs.png', out.size)


if __name__ == '__main__':
    sheet([runic(), latin(), cyrillic()])
