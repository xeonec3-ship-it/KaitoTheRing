#!/usr/bin/env python3
"""
T21 — визуальная часть «Печати души» (soul_seal) и «Благословения» (blessing), Божественная ступень.
ТЗ: docs/specs/tasks/T21_soul_seal_blessing.md (шкала каста 10 с = 200 тиков у обоих заклинаний).

Пишет (src/main/resources/assets/pohsmp_core/):
  textures/sigil/soul_lock.png, soul_mark.png, bless_halo.png, bless_rose.png   — рисунки печатей (белое на прозрачном, 512)
  sigils/soul_seal_*.json, blessing_*.json                                       — печати
  fx/soul_seal_cast.json, soul_seal_lock_in.json, soul_seal_deny.json, soul_seal_mark.json, fx/blessing_cast.json
  fx/styles/soul_seal.json, blessing.json                                        — палитры
  textures/gui/spell_icons/soul_seal.png, blessing.png (16×16), textures/mob_effect/soul_seal.png (18×18)

Точки эффектов: каст — `caster` (заклинатель) и `target` (цель, задаёт код); `soul_seal_lock_in`, `_deny`, `_mark` —
привязаны к `caster` = запечатанный игрок (код запускает их с ним в роли кастера).
Время — тики, углы — градусы, размеры — блоки. Запуск:  python3 tools/gen_divine_t21.py
"""
import json
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_sigil_textures import C, SS, W, canvas, polar, ring, save  # noqa: E402

A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
WRITTEN = []

# ------------------------------------------------------------------ палитры
S_GOLD, S_GOLD_D, S_WHITE, S_VIOLET, S_VIOLET_D = '#D9A441', '#9A6A1C', '#E6F0FF', '#9A6CFF', '#3A1E6A'   # Печать души
B_GOLD, B_WHITE, B_PALE, B_BLUE, B_WARM = '#FFC94D', '#FFFFFF', '#FFF4D6', '#A8DCFF', '#FFE7A0'            # Благословение
DARK_SHARD = '#2A0F3A'


def write(rel, obj):
    path = os.path.join(A, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write('\n')
    WRITTEN.append(rel)


# ================================================================== текстуры
def _ellipse_at(d, cx, cy, rx, ry, ang, width, fill=255, n=48):
    """Повёрнутый эллипс-контур (звено цепи)."""
    pts = []
    for k in range(n + 1):
        t = 2 * math.pi * k / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + x * math.cos(ang) - y * math.sin(ang), cy + x * math.sin(ang) + y * math.cos(ang)))
    d.line(pts, fill=fill, width=int(width), joint='curve')


def _bar(d, cx, cy, length, ang, width, fill=255):
    dx, dy = math.cos(ang) * length / 2, math.sin(ang) * length / 2
    d.line([cx - dx, cy - dy, cx + dx, cy + dy], fill=fill, width=int(width))
    r = width / 2
    for px, py in ((cx - dx, cy - dy), (cx + dx, cy + dy)):
        d.ellipse([px - r, py - r, px + r, py + r], fill=fill)


def _chain_ring(d, r, n, link_len, link_w, width):
    """Кольцо цепи: n звеньев по окружности радиуса r, чётные — плашмя (овал), нечётные — ребром (перемычка)."""
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = polar(r, a)
        tang = a + math.pi / 2
        if i % 2 == 0:
            _ellipse_at(d, x, y, link_len / 2, link_w / 2, tang, width)
        else:
            _bar(d, x, y, link_len * 0.95, tang, width * 1.35)


def _keyhole(d, cx, cy, s, fill=255):
    """Замочная скважина: круг и расширяющаяся книзу ножка; s — радиус круга."""
    d.ellipse([cx - s, cy - s * 1.35 - s, cx + s, cy - s * 1.35 + s], fill=fill)
    d.polygon([(cx - s * 0.42, cy - s * 1.2), (cx + s * 0.42, cy - s * 1.2), (cx + s * 0.85, cy + s * 1.55), (cx - s * 0.85, cy + s * 1.55)],
              fill=fill)


def _dot(d, x, y, r, fill=255):
    d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _lens(d, r0, r1, a, half_w, fill=255, curve=0.0, outline=None, width=0, feather=False):
    """Лепесток/перо: «линза» вдоль луча угла a от радиуса r0 до r1, полуширина half_w (пиксели), изгиб curve (рад к концу).
    feather — профиль пера: узкое основание, шире всего у 0.7 длины, скруглённый кончик."""
    left, right = [], []
    n = 40
    for k in range(n + 1):
        s = k / n
        r = r0 + (r1 - r0) * s
        w = half_w * (s ** 0.7 * max(0.0, 1 - s ** 6) ** 0.5 * 1.25 if feather else math.sin(math.pi * s) ** 0.75)
        ang = a + curve * s * s
        da = w / max(r, 1)
        left.append(polar(r, ang - da))
        right.append(polar(r, ang + da))
    pts = left + right[::-1]
    if fill is not None:
        d.polygon(pts, fill=fill)
    if outline is not None:
        d.line(pts + [pts[0]], fill=outline, width=int(width), joint='curve')


def tex_soul_lock():
    """Печать-замок: засовы-зубья по ободу, кольцо цепи, кодовый лимб, четыре ригеля к центру, замочная скважина."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.985, 7 * SS)
    ring(d, C * 0.955, 2 * SS)
    for i in range(24):                                        # засовы сейфа: трапеции внутрь
        a = 2 * math.pi * (i + 0.5) / 24
        w0, w1 = 0.05, 0.032
        d.polygon([polar(C * 0.945, a - w0), polar(C * 0.945, a + w0), polar(C * 0.885, a + w1), polar(C * 0.885, a - w1)], fill=255)
    ring(d, C * 0.87, 3 * SS)
    _chain_ring(d, C * 0.77, 20, C * 0.27, C * 0.11, 7 * SS)  # цепь, обвившая печать
    ring(d, C * 0.665, 3 * SS)
    ring(d, C * 0.64, 1 * SS)
    for k in range(16):                                        # тонкая звезда-решётка за ригелями
        a0 = 2 * math.pi * k / 16
        a1 = 2 * math.pi * (k + 6) / 16
        d.line([*polar(C * 0.63, a0), *polar(C * 0.63, a1)], fill=120, width=2 * SS)
    for k in range(4):                                         # ригели: двойная тяга, наконечник и поперечина
        a = 2 * math.pi * k / 4 + math.pi / 4
        for off in (-0.022, 0.022):
            p0, p1 = polar(C * 0.36, a + off * 1.6), polar(C * 0.6, a + off * 0.9)
            d.line([*p0, *p1], fill=255, width=4 * SS)
        tip = polar(C * 0.655, a)
        d.polygon([polar(C * 0.585, a - 0.07), tip, polar(C * 0.585, a + 0.07)], fill=255)
        cx, cy = polar(C * 0.47, a)
        _bar(d, cx, cy, C * 0.13, a + math.pi / 2, 4 * SS)
        _dot(d, *polar(C * 0.53, a), 9 * SS)
    for k in range(4):                                         # между ригелями — малые печати-заклёпки
        a = 2 * math.pi * k / 4
        x, y = polar(C * 0.52, a)
        d.ellipse([x - C * 0.05, y - C * 0.05, x + C * 0.05, y + C * 0.05], outline=255, width=3 * SS)
        _dot(d, x, y, 6 * SS)
    ring(d, C * 0.355, 3 * SS)
    ring(d, C * 0.32, 6 * SS)
    for i in range(40):                                        # кодовый лимб
        a = 2 * math.pi * i / 40
        big = i % 5 == 0
        d.line([*polar(C * (0.24 if big else 0.265), a), *polar(C * 0.305, a)], fill=255, width=(4 if big else 2) * SS)
    ring(d, C * 0.205, 4 * SS)
    _keyhole(d, C, C + C * 0.03, C * 0.065)
    save(img, 'soul_lock')


def tex_soul_mark():
    """Малый знак на груди: толстые линии, читается в 20 пикселей — кольцо цепи, четырёхлучевая звезда, скважина."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.96, 12 * SS)
    _chain_ring(d, C * 0.8, 12, C * 0.36, C * 0.17, 12 * SS)
    ring(d, C * 0.62, 9 * SS)
    star = []
    for k in range(8):
        a = 2 * math.pi * k / 8 - math.pi / 2
        star.append(polar(C * (0.58 if k % 2 == 0 else 0.2), a))
    d.polygon(star, fill=255)
    for k in range(4):
        _dot(d, *polar(C * 0.44, 2 * math.pi * k / 4 + math.pi / 4), 16 * SS)
    d.ellipse([C - C * 0.17, C - C * 0.17, C + C * 0.17, C + C * 0.17], fill=0)
    _keyhole(d, C, C + C * 0.025, C * 0.055)
    save(img, 'soul_mark')


def tex_bless_halo():
    """Нимб-печать: венец из 32 перьев наружу, кольца, лучи-клинья, точки и восьмиконечная звезда в центре."""
    img = canvas()
    d = ImageDraw.Draw(img)
    n = 32
    for i in range(n):                                         # перья: тело пера, стержень, бородки
        a = 2 * math.pi * i / n
        _lens(d, C * 0.64, C * 0.985, a, C * 0.05, fill=150, curve=0.09, feather=True)
        _lens(d, C * 0.64, C * 0.985, a, C * 0.05, fill=None, curve=0.09, outline=255, width=3 * SS, feather=True)
        pts = [polar(C * (0.64 + 0.33 * s), a + 0.09 * s * s) for s in [k / 20 for k in range(21)]]
        d.line(pts, fill=255, width=3 * SS)
        for s in (0.3, 0.45, 0.6, 0.75):                       # бородки
            r = C * (0.64 + 0.33 * s)
            ang = a + 0.09 * s * s
            for side in (-1, 1):
                p0 = polar(r, ang)
                p1 = polar(r + C * 0.035, ang + side * 0.03)
                d.line([*p0, *p1], fill=210, width=2 * SS)
    ring(d, C * 0.63, 7 * SS)
    ring(d, C * 0.595, 2 * SS)
    for i in range(48):                                        # жемчуг
        _dot(d, *polar(C * 0.56, 2 * math.pi * i / 48), (6 if i % 2 == 0 else 3.5) * SS)
    ring(d, C * 0.52, 2 * SS)
    for i in range(24):                                        # лучи-клинья
        a = 2 * math.pi * i / 24
        long = i % 2 == 0
        r1 = C * (0.49 if long else 0.4)
        w = 0.05 if long else 0.035
        d.polygon([polar(C * 0.2, a - w), polar(r1, a), polar(C * 0.2, a + w)], fill=230 if long else 160)
    ring(d, C * 0.2, 6 * SS)
    ring(d, C * 0.165, 2 * SS)
    star = []
    for k in range(16):
        a = 2 * math.pi * k / 16 - math.pi / 2
        star.append(polar(C * (0.14 if k % 2 == 0 else 0.055), a))
    d.polygon(star, fill=255)
    save(img, 'bless_halo')


def tex_bless_rose():
    """Розетка Благословения: зубчатый обод из арок, 12 лепестков (двойной контур), цветок жизни в центре, жемчуг."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.985, 6 * SS)
    ring(d, C * 0.9, 3 * SS)
    n = 24
    for i in range(n):                                         # арки обода
        a = 2 * math.pi * (i + 0.5) / n
        x, y = polar(C * 0.9, a)
        r = C * 0.9 * math.sin(math.pi / n)
        d.arc([x - r, y - r, x + r, y + r], math.degrees(a) - 90, math.degrees(a) + 90, fill=255, width=3 * SS)
        _dot(d, *polar(C * 0.955, 2 * math.pi * i / n), 6 * SS)
    for i in range(12):                                        # большие лепестки
        a = 2 * math.pi * i / 12
        _lens(d, C * 0.27, C * 0.86, a, C * 0.13, fill=60)
        _lens(d, C * 0.27, C * 0.86, a, C * 0.13, fill=None, outline=255, width=4 * SS)
        _lens(d, C * 0.36, C * 0.76, a, C * 0.065, fill=None, outline=200, width=2 * SS)
        d.line([*polar(C * 0.4, a), *polar(C * 0.72, a)], fill=170, width=2 * SS)
    for i in range(12):                                        # малые лепестки между
        a = 2 * math.pi * (i + 0.5) / 12
        _lens(d, C * 0.5, C * 0.8, a, C * 0.055, fill=120)
        _dot(d, *polar(C * 0.84, a), 7 * SS)
    for i in range(60):
        _dot(d, *polar(C * 0.255, 2 * math.pi * i / 60), 3 * SS)
    d.ellipse([C - C * 0.235, C - C * 0.235, C + C * 0.235, C + C * 0.235], fill=0)
    ring(d, C * 0.235, 4 * SS)
    rr = C * 0.115                                              # цветок жизни: 6 кругов через центр
    for k in range(6):
        x, y = polar(rr, 2 * math.pi * k / 6)
        d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=255, width=3 * SS)
    d.ellipse([C - rr, C - rr, C + rr, C + rr], outline=255, width=3 * SS)
    _dot(d, C, C, 10 * SS)
    save(img, 'bless_rose')


def textures():
    tex_soul_lock()
    tex_soul_mark()
    tex_bless_halo()
    tex_bless_rose()


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
          dissolve=('reverse', 'collapse'), ddur=20, stagger=2, hit=None):
    o = {'comment': comment, 'size': size, 'color': color, 'orientation': orientation, 'lifetime': -1, 'hold': hold, 'layers': layers}
    if expand:
        o['expand'] = expand
    if flash:
        o['formedFlash'] = flash
    if children:
        o['onFormed'] = children
    if hit is not None:
        o['hit'] = hit
    o['dissolve'] = {'modes': list(dissolve), 'duration': ddur, 'stagger': stagger}
    write('sigils/%s.json' % id, o)


def soul_sigils():
    sigil('soul_seal_ground', 'Печать души, каст 0–2 с: божественная печать под заклинателем — мандала, решётка Метатрона прорисовывается, '
                              'замок в центре с доворотом, кольцо цепи, руны «ПЕЧАТЬ ДУШИ», обод. Держится весь каст (hold −1).',
          3.4, S_GOLD, 'ground', [
              L('glow', 'disc', 'glow', 0.95, -0.01, ap(0, 16, 'fade'), color=S_VIOLET, br=0.35, pulse=(0.15, 40)),
              L('mandala', 'disc', 'pat_mandala', 1.32, 0.0, ap(0, 34, 'fade', 'grow'), rot=1.5, br=0.4),
              L('metatron', 'disc', 'pat_metatron', 0.8, 0.005, ap(4, 26, 'draw', easing='easeInOutSine', startAngle=90), rot=-4, color=S_WHITE, br=0.4),
              L('lock', 'disc', 'soul_lock', 0.46, 0.01, ap(8, 22, 'grow', 'twist', 'fade', easing='easeOutBack', twist=-140), rot=6, boost=3),
              L('chains', 'band', 'chain_band', 1.0, 0.015, ap(14, 22, 'draw', startAngle=90, direction=-1), inner=0.9, repeat=14, rot=-3,
                color=S_VIOLET, br=1.2),
              T('runes', 'ПЕЧАТЬ ДУШИ ✦ ', 0.84, 0.085, 0.02, ap(18, 22, 'draw', easing='linear'), color=S_WHITE, br=0.85, rot=2, repeat=3),
              L('rim', 'band', 'thin_ring', 1.08, 0.025, ap(24, 14, 'draw', startAngle=90), inner=0.985, repeat=1, br=0.9),
              L('rim2', 'band', 'thin_ring', 0.7, 0.03, ap(28, 10, 'draw', startAngle=-90, direction=-1), inner=0.97, repeat=1, color=S_VIOLET),
          ], flash={'color': S_WHITE, 'size': 1.2, 'duration': 12, 'sparks': 30}, ddur=18)

    sigil('soul_seal_hand', 'Печать души: малый замок у ладони заклинателя (2–9.5 с), смотрит на цель.', 0.42, S_GOLD, 'facing', [
        L('glow', 'disc', 'glow', 1.4, -0.01, ap(0, 10, 'fade'), color=S_VIOLET, br=0.55, pulse=(0.3, 14)),
        L('lock', 'disc', 'soul_lock', 1.0, 0.0, ap(0, 14, 'unfold', 'fade', easing='easeOutBack'), rot=40, boost=3),
        L('ring', 'disc', 'orbit_dash', 1.35, 0.01, ap(4, 12, 'grow', 'fade'), rot=-60, color=S_WHITE, br=0.7),
    ], flash={'color': S_WHITE, 'size': 1.6, 'duration': 6, 'sparks': 6}, dissolve=('collapse',), ddur=8)

    sigil('soul_seal_lock', 'Печать-замок над целью (2–6 с собирается из лучей, лицом вниз): дуги смыкаются, замок прорисовывается, '
                            'руны «ДУША ЗАПЕЧАТАНА» бегут по кругу, внешняя цепь, засовы; в 9.3 с сжимается в точку (вдавливается в грудь).',
          1.45, S_GOLD, 'sky', [
              L('glow', 'disc', 'glow', 1.05, -0.02, ap(0, 20, 'fade'), color=S_VIOLET, br=0.55, pulse=(0.2, 24)),
              L('arcs', 'arcs', 'arc_strip', 1.32, 0.0, ap(0, 26, 'assemble', 'fade'), count=4, arcLength=60, width=0.025, rot=14, color=S_WHITE),
              L('lock', 'disc', 'soul_lock', 1.0, 0.01, ap(10, 36, 'draw', easing='easeInOutSine', startAngle=90), rot=8, boost=2),
              L('dial', 'disc', 'orbit_runes', 0.58, 0.02, ap(24, 18, 'grow', 'fade', easing='easeOutBack'), rot=-20, boost=2, color=S_WHITE, br=0.8),
              T('runes', 'ДУША ЗАПЕЧАТАНА ✦ ', 1.17, 0.11, 0.025, ap(30, 30, 'draw', easing='linear'), color=S_WHITE, br=0.95, rot=-16, repeat=2),
              L('chain', 'band', 'chain_band', 1.5, 0.03, ap(46, 24, 'draw', startAngle=90), inner=0.9, repeat=12, rot=7, color=S_VIOLET, br=1.3),
              L('rim', 'band', 'thin_ring', 1.56, 0.035, ap(56, 14, 'draw', startAngle=-90, direction=-1), inner=0.985, repeat=1, br=0.9),
              L('spikes', 'disc', 'cross_spikes', 0.34, 0.04, ap(62, 12, 'grow', 'twist', easing='easeOutBack', twist=90), rot=30, color=S_WHITE),
          ], expand={'scale': 1.12, 'delay': 0, 'duration': 10, 'easing': 'easeOutCubic'},
          flash={'color': S_WHITE, 'size': 1.4, 'duration': 12, 'sparks': 24}, dissolve=('collapse',), ddur=10)

    sigil('soul_seal_gyro', 'Печать-замок: вертикальные кольца над целью (вместе с замком дают объём «гироскопа»).', 1.05, S_GOLD, 'facing', [
        L('saw', 'disc', 'orbit_saw', 1.0, 0.0, ap(0, 20, 'grow', 'fade'), rot=-40, boost=3, color=S_VIOLET, br=1.2),
        L('dash', 'disc', 'orbit_dash', 1.2, 0.02, ap(8, 20, 'grow', 'fade'), rot=26, color=S_WHITE, br=0.7),
    ], dissolve=('collapse',), ddur=10)

    sigil('soul_seal_bind', 'Печать души: кольцо цепи вокруг тела цели (6–9 с) — стягивается (expand 0.4), пока цепи сжимаются.',
          1.3, S_VIOLET, 'ground', [
              L('glow', 'disc', 'glow', 0.9, -0.01, ap(0, 10, 'fade'), br=0.25),
              L('chain', 'band', 'chain_band', 1.0, 0.0, ap(0, 14, 'draw', startAngle=90), inner=0.86, repeat=8, rot=30, br=1.4),
              L('ring', 'band', 'thin_ring', 0.84, 0.01, ap(4, 10, 'draw', startAngle=-90, direction=-1), inner=0.95, repeat=1, color=S_WHITE),
          ], expand={'scale': 0.42, 'delay': 6, 'duration': 40, 'easing': 'easeInOutCubic'}, dissolve=('collapse', 'fade'), ddur=8)

    sigil('soul_seal_mark', 'Знак Печати души на груди (постоянный, виден всем рядом): малая печать-цепь, медленно вращается.',
          0.17, S_GOLD, 'facing', [
              L('glow', 'disc', 'glow', 1.5, -0.01, ap(0, 12, 'fade'), color=S_VIOLET, br=0.4, pulse=(0.25, 60)),
              L('mark', 'disc', 'soul_mark', 1.0, 0.0, ap(0, 12, 'grow', 'fade', easing='easeOutBack'), rot=9),
              L('ring', 'band', 'chain_band', 1.32, 0.005, ap(4, 12, 'draw', startAngle=90), inner=0.82, repeat=6, rot=-5, color=S_VIOLET, br=1.1),
          ], dissolve=('collapse', 'fade'), ddur=12)

    sigil('soul_seal_mark_in', 'Печать души, вдавливание: замок вспыхивает на груди большим и сжимается до малого знака.', 0.9, S_GOLD, 'facing', [
        L('glow', 'disc', 'glow', 1.3, -0.01, ap(0, 3, 'fade'), color=S_WHITE, br=0.9),
        L('lock', 'disc', 'soul_lock', 1.0, 0.0, ap(0, 3, 'fade'), rot=90),
        L('mark', 'disc', 'soul_mark', 0.6, 0.01, ap(0, 4, 'fade'), rot=-30, color=S_WHITE),
        L('chain', 'band', 'chain_band', 1.25, 0.02, ap(0, 4, 'fade'), inner=0.86, repeat=10, rot=-60, color=S_VIOLET, br=1.4),
    ], expand={'scale': 0.19, 'delay': 0, 'duration': 14, 'easing': 'easeInCubic'}, hold=4, dissolve=('fade',), ddur=8)

    sigil('soul_seal_deny', 'Печать души: вспышка знака на груди при попытке колдовать — знак вырастает, цепь дёргается, гаснет.',
          0.3, S_GOLD, 'facing', [
              L('glow', 'disc', 'glow', 1.4, -0.01, ap(0, 3, 'fade'), color=S_VIOLET, br=0.9),
              L('mark', 'disc', 'soul_mark', 1.0, 0.0, ap(0, 4, 'grow', 'fade', easing='easeOutBack'), rot=-120, br=1.3),
              L('chain', 'band', 'chain_band', 1.35, 0.01, ap(0, 5, 'grow', 'fade', easing='easeOutBack'), inner=0.82, repeat=8, rot=200,
                color=S_VIOLET, br=1.5),
          ], expand={'scale': 1.5, 'delay': 0, 'duration': 6, 'easing': 'easeOutCubic'}, hold=2, dissolve=('collapse', 'fade'), ddur=8)


def bless_sigils():
    sigil('blessing_ground', 'Благословение, 0–2 с: золотой круг под заклинателем (и меньший — под целью, scale 0.62): розетка '
                             'прорисовывается, священная печать с доворотом, надпись «БЛАГОСЛОВЕНИЕ», нежно-голубой обод.',
          2.6, B_GOLD, 'ground', [
              L('glow', 'disc', 'glow', 0.95, -0.01, ap(0, 14, 'fade'), color=B_WARM, br=0.4, pulse=(0.12, 50)),
              L('rays', 'spokes', 'rays', 1.4, -0.005, ap(0, 30, 'fade', 'grow'), rot=1, color=B_PALE, br=0.35),
              L('rose', 'disc', 'bless_rose', 0.96, 0.0, ap(0, 28, 'draw', easing='easeInOutSine', startAngle=90), rot=3),
              L('holy', 'disc', 'holy_seal', 0.42, 0.01, ap(10, 20, 'grow', 'twist', 'fade', easing='easeOutBack', twist=-120), rot=-6, color=B_WHITE),
              T('words', 'БЛАГОСЛОВЕНИЕ ✦ ', 1.03, 0.085, 0.02, ap(16, 22, 'draw', easing='linear'), font='cyrillic', color=B_BLUE,
                br=0.95, rot=-1.5, repeat=3),
              L('rim', 'band', 'thin_ring', 1.13, 0.025, ap(22, 14, 'draw', startAngle=90), inner=0.985, repeat=1, color=B_BLUE),
              L('star', 'disc', 'star_ring', 0.2, 0.03, ap(26, 10, 'grow', 'fade'), rot=12, color=B_WHITE),
          ], flash={'color': B_PALE, 'size': 1.2, 'duration': 12, 'sparks': 24}, ddur=24)

    sigil('blessing_halo', 'Благословение, 2–6 с: нимб-печать над целью лицом вниз — венец из перьев раскрывается из ребра, '
                           'солнце в центре, лучи, кольцо рун «ДА БУДЕТ СВЕТ»; мягко дышит. Гаснет к финальной вспышке.',
          1.25, B_GOLD, 'sky', [
              L('glow', 'disc', 'glow', 1.2, -0.02, ap(0, 20, 'fade'), color=B_WARM, br=0.5, pulse=(0.15, 30)),
              L('rays', 'spokes', 'rays', 1.9, -0.01, ap(10, 40, 'fade', 'grow'), rot=2, color=B_PALE, br=0.45),
              L('halo', 'disc', 'bless_halo', 1.0, 0.0, ap(0, 34, 'unfold', 'fade', easing='easeOutCubic'), rot=5, boost=2),
              L('sun', 'disc', 'divine_sun', 0.34, 0.01, ap(16, 20, 'grow', 'twist', easing='easeOutBack', twist=-90), rot=-8, color=B_WHITE),
              T('words', 'ДА БУДЕТ СВЕТ ✦ ', 1.16, 0.1, 0.02, ap(30, 30, 'draw', easing='linear'), font='cyrillic', color=B_BLUE, br=0.9,
                rot=-4, repeat=2),
              L('rim', 'band', 'thin_ring', 1.3, 0.03, ap(44, 16, 'draw', startAngle=90), inner=0.985, repeat=1, color=B_BLUE, br=0.9),
              L('dots', 'disc', 'orbit_stars', 1.45, 0.035, ap(50, 20, 'grow', 'fade'), rot=-3, color=B_PALE, br=0.6),
          ], expand={'scale': 1.15, 'delay': 0, 'duration': 14, 'easing': 'easeOutCubic'},
          flash={'color': B_WHITE, 'size': 1.3, 'duration': 14, 'sparks': 30}, dissolve=('fade', 'shatter'), ddur=12)


# ================================================================== эффекты
def fx(id, comment, style, duration, elements):
    write('fx/%s.json' % id, {'comment': comment, 'style': style, 'duration': duration, 'elements': elements})


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


def style(id, comment, primary, secondary, core, shadow, sparks='spark_soft', shards='feather', sig='core', rot=0.6):
    write('fx/styles/%s.json' % id, {
        'comment': comment, 'palette': {'primary': primary, 'secondary': secondary, 'core': core, 'shadow': shadow},
        'textures': {'sparks': sparks, 'runes': 'rune_band', 'shards': shards, 'sigil': sig}, 'blend': 'additive',
        'motion': {'rotationScale': rot, 'jitter': 0.0, 'easing': 'easeOutSine'}})


LOCK_Y = 3.0      # высота печати-замка над ногами цели
CHEST = 1.35      # грудь цели (точка вдавливания)


def soul_fx():
    style('soul_seal', 'Печать души: тёмное золото, холодный белый, фиолетовые цепи.', S_GOLD, S_WHITE, '#FFFFFF', S_VIOLET_D,
          shards='shard', sig='soul_lock', rot=0.7)
    lock = off('target', 0, LOCK_Y, 0)
    chest = off('target', 0, CHEST, 0)
    rays = []
    for i in range(6):                                      # 2–4.5 с: лучи сходятся в точку замка и собирают его
        a = 2 * math.pi * i / 6 + 0.3
        src = off('target', 2.6 * math.cos(a), LOCK_Y + 3.2 + 0.6 * (i % 2), 2.6 * math.sin(a))
        rays.append(E('beam', 40 + 5 * i, src, to=lock, follow=True, duration=34, width=0.05, core=0.5, grow=14, head=1.2,
                      color=S_WHITE if i % 2 else '@primary', **{'out': ease(10)}))
    chains = []
    for i in range(4):                                      # 6–9 с: цепи от замка к груди
        a = 2 * math.pi * i / 4 + math.pi / 4
        src = off('target', 0.95 * math.cos(a), LOCK_Y - 0.1, 0.95 * math.sin(a))
        chains.append(E('chains', 120 + 3 * i, src, to=chest, follow=True, duration=46 - 3 * i, link=0.16, sag=0.35, tension=0.25,
                        grow=24, rattle=0.02, color=S_VIOLET))
        chains.append(E('chains', 166, src, to=chest, follow=True, duration=22, link=0.16, sag=0.0, tension=1.0, rattle=0.06,
                        color=S_VIOLET, brightness=1.4, comment='цепи натянуты: провис уходит, дрожь'))
    binds = [E('sigil', 128 + 7 * k, off('target', 0, h, 0), follow=True, id='soul_seal_bind', until=188) for k, h in enumerate((0.55, 1.05, 1.55))]
    fx('soul_seal_cast', 'Печать души, каст 10 с (200 тиков). Точки: caster — заклинатель, target — цель. '
                         '0–2 с печать под заклинателем, свет стягивается к рукам; 2–6 с из лучей над целью собирается печать-замок, '
                         'малый замок у ладони; 6–9 с цепи тянутся от замка к груди и сжимаются, кольца цепи стягивают тело; '
                         '9.3–9.8 с замок сжимается в точку и луч вбивает его в грудь. Финал — fx/soul_seal_lock_in (код, на 200 тике).',
       'soul_seal', 200, [
           E('sigil', 0, 'caster+0,0.05,0', id='soul_seal_ground', until=196),
           E('sprites', 0, 'caster+0,0.15,0', duration=44, texture='spark_soft', count=110, rate=2.5, area=3.0, speed=0.012, gravity=-0.005,
             size=[0.16, 0.03], life=34, color='@secondary', glow=0.4, comment='свет поднимается от печати'),
           E('vortex', 4, 'caster+0,1.25,0.45', duration=40, radius=1.4, height=0, arms=3, speed=4, pull=1, texture='spark_soft',
             particles=60, life=20, size=0.12, color='@primary', comment='руки собирают свет'),
           E('flash', 34, 'caster+0,1.25,0.45', duration=10, size=1.1, rays=6, color=S_WHITE),
           E('sigil', 40, 'caster.hand', follow=True, id='soul_seal_hand', until=190),
           E('beam', 44, 'caster.hand', to=lock, follow=True, duration=146, width=0.035, core=0.6, grow=16, flicker=0.2, scroll=1.2,
             color=S_WHITE, brightness=0.7, comment='тонкий луч от ладони к замку'),
           E('aura', 40, 'target', target='target', duration=152, thickness=0.08, pulse=[0.25, 24], motes=10, texture='spark_soft',
             color=S_VIOLET, **{'in': ease(20), 'out': ease(8)}),
           *rays,
           E('vortex', 40, lock, duration=60, radius=2.4, height=0, arms=4, speed=3, pull=1, texture='spark_sharp', particles=80, life=24,
             size=0.14, color=S_WHITE, comment='искры затягивает в печать'),
           E('sigil', 44, lock, follow=True, id='soul_seal_lock', until=186),
           E('sigil', 56, lock, follow=True, id='soul_seal_gyro', until=186),
           E('sprites', 80, lock, follow=True, duration=100, texture='rune', count=50, rate=0.5, spread=1.2, speed=0.006, gravity=0.0,
             spin=60, size=[0.18, 0.1], life=30, color=S_WHITE, comment='символы вокруг печати'),
           *chains,
           *binds,
           E('tint', 120, 'target', duration=80, radius=12, color='#20103A', strength=0.25, **{'in': ease(30), 'out': ease(6)}),
           E('beam', 182, lock, to=chest, follow=True, duration=14, width=0.3, core=0.35, grow=6, easing='easeInCubic', head=3,
             color=S_WHITE, **{'out': ease(6)}, comment='замок вбивается в грудь'),
           E('flash', 188, 'caster.hand', duration=8, size=1.4, rays=6, color=S_VIOLET, comment='рывок «запереть»'),
       ])

    me = 'caster+0,%s,0.2' % fmt(CHEST)
    fx('soul_seal_lock_in', 'Печать души, финал (на 200 тике каста; caster = запечатанный игрок): вспышка на груди, звон-волна, '
                            'замок сжимается в малый знак, искры и обрывки цепи разлетаются. Дальше знак держит fx/soul_seal_mark.',
       'soul_seal', 40, [
           E('flash', 0, me, follow=True, duration=12, size=2.6, anamorphic=7, rays=10, screen=0.3, color=S_WHITE),
           E('flash', 2, me, follow=True, duration=16, size=1.4, ring=True, color=S_VIOLET),
           E('wave', 0, 'caster+0,1.3,0', duration=16, shape='sphere', radius=2.0, rim=1.5, color=S_VIOLET),
           E('wave', 0, 'caster', duration=20, shape='ring', radius=4.5, color='@primary'),
           E('sigil', 0, me, follow=True, id='soul_seal_mark_in', until=22),
           E('sprites', 0, me, duration=3, texture='spark_sharp', count=46, rate=46, spread=0.25, speed=0.2, gravity=0.006,
             size=[0.22, 0.03], life=20, color=S_WHITE, glow=0.5),
           E('sprites', 0, me, duration=3, texture='chain_link', count=12, rate=12, spread=0.3, speed=0.12, gravity=0.012, tumble=1,
             size=[0.22, 0.12], life=22, color=S_VIOLET, comment='обрывки цепи'),
           E('sigil', 16, me, follow=True, id='soul_seal_mark', until=40, comment='знак проявляется; дальше его держит soul_seal_mark'),
       ])
    fx('soul_seal_deny', 'Печать души: попытка колдовать (caster = запечатанный игрок) — знак на груди вспыхивает, цепь дёргается, '
                         'фиолетовые искры. Короткий (16 тиков), можно запускать хоть каждую попытку.',
       'soul_seal', 16, [
           E('sigil', 0, me, follow=True, id='soul_seal_deny', until=8),
           E('flash', 0, me, follow=True, duration=8, size=0.9, rays=4, color=S_VIOLET),
           E('sprites', 0, me, follow=True, duration=2, texture='spark_sharp', count=14, rate=14, spread=0.15, speed=0.08, gravity=0.004,
             size=[0.14, 0.02], life=12, color=S_VIOLET),
       ])
    fx('soul_seal_mark', 'Печать души: постоянный знак на груди (duration −1, пока код не остановит; caster = запечатанный игрок, '
                         'follow — едет за ним). Тихие фиолетовые пылинки.', 'soul_seal', -1, [
        E('sigil', 0, me, follow=True, id='soul_seal_mark'),
        E('sprites', 0, me, follow=True, texture='spark_soft', count=100000, rate=0.15, spread=0.12, speed=0.004, gravity=-0.001,
          size=[0.06, 0.01], life=30, color=S_VIOLET),
    ])


def bless_fx():
    style('blessing', 'Благословение: тёплое золото, белый, нежно-голубой; перья, нимб, столб мягкого света.', B_GOLD, B_PALE,
          '#FFFFFF', '#5A8AB8', shards='feather', sig='bless_halo', rot=0.5)
    halo = off('target', 0, 2.7, 0)
    burns = []
    rng = random.Random(21)
    for k in range(9):                                      # 6.5–9 с: тёмные осколки сгорают — маленькие вспышки над целью
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.3, 0.8)
        burns.append(E('flash', 130 + 6 * k + rng.randint(0, 3), off('target', r * math.cos(a), rng.uniform(1.9, 2.6), r * math.sin(a)),
                       duration=7, size=rng.uniform(0.35, 0.6), rays=4, color=B_WARM))
    halos = [E('sigil', 18 + 4 * k, off('caster', x, 1.75 + 0.25 * abs(x), -0.55), id='golden_halo') for k, x in enumerate((-1.2, 1.2, -0.7, 0.7))]
    fx('blessing_cast', 'Благословение, каст 10 с (200 тиков) и финал до 220. Точки: caster — заклинатель, target — цель '
                        '(без цели код передаёт target = caster). 0–2 с золотые круги под обоими, падают перья, за спиной встают золотые круги; '
                        '2–6 с над целью раскрывается нимб-печать, сверху столб мягкого света; 6–9 с свет опускается на цель, тёмные '
                        'осколки дебаффов вылетают и сгорают; 9.5–10 с вспышка, кольцо по земле, перья разлетаются.',
       'blessing', 220, [
           E('sigil', 0, 'caster+0,0.05,0', id='blessing_ground', until=198),
           E('sigil', 6, 'target+0,0.07,0', id='blessing_ground', scale=0.62, until=198),
           E('sprites', 0, 'caster+0,0.2,0', duration=40, texture='spark_soft', count=90, rate=2.2, area=2.4, speed=0.01, gravity=-0.004,
             size=[0.15, 0.03], life=36, color=B_WARM, glow=0.4),
           E('sprites', 0, 'caster+0,4.2,0', duration=190, texture='feather', count=110, rate=0.6, area=2.6, speed=0.003, gravity=0.0012,
             sway=1.2, tumble=0.6, size=[0.32, 0.22], life=150, color='@secondary', comment='перья падают у заклинателя'),
           E('sprites', 10, 'target+0,4.6,0', duration=180, texture='feather', count=110, rate=0.6, area=2.0, speed=0.003, gravity=0.0012,
             sway=1.2, tumble=0.6, size=[0.32, 0.22], life=150, color=B_BLUE, brightness=0.8, comment='перья падают у цели'),
           *halos,
           E('sigil', 40, halo, follow=True, id='blessing_halo', until=188),
           E('column', 50, 'target', duration=150, radius=0.85, height=18, rings=3, ringSpeed=2, fill=0, brightness=0.5, color='@secondary',
             **{'in': ease(30, 'easeInOutSine'), 'out': ease(10)}, comment='столб мягкого света сверху'),
           E('curtain', 60, 'target', duration=130, radius=[1.1, 2.3], count=14, height=16, grow=40, width=[0.04, 0.1],
             brightness=[0.2, 0.5], flicker=0.2, texture='beam_fade', color=B_BLUE, **{'out': ease(12)}),
           E('beam', 70, 'caster.hand', to='target+0,1.3,0', follow=True, duration=118, width=0.05, core=0.5, grow=24, flicker=0.12,
             scroll=-0.8, color=B_WARM, brightness=0.7, **{'out': ease(8)}, comment='нить света от ладоней к цели'),
           E('halo', 110, 'target', follow=True, duration=90, size=0.42, spin=2, color='@primary', **{'in': ease(12), 'out': ease(8)}),
           E('beam', 120, halo, to='target+0,0.1,0', follow=True, duration=70, width=0.55, core=0.3, grow=40, easing='easeInOutSine',
             color='@secondary', brightness=0.8, **{'out': ease(10)}, comment='свет опускается на цель'),
           E('aura', 124, 'target', target='target', duration=76, thickness=0.12, pulse=[0.2, 20], motes=18, texture='spark_soft',
             color=B_PALE, **{'in': ease(16), 'out': ease(8)}),
           E('sprites', 124, 'target+0,1.0,0', follow=True, duration=56, texture='shard', count=70, rate=1.25, spread=0.45, speed=0.05,
             gravity=-0.0035, tumble=1, size=[0.3, 0.06], life=26, color=DARK_SHARD, blend='translucent',
             comment='тёмные осколки дебаффов вылетают из тела вверх'),
           E('sprites', 128, 'target+0,2.1,0', follow=True, duration=56, texture='spark_soft', count=120, rate=2.1, spread=0.85, speed=0.02,
             gravity=-0.004, size=[0.22, 0.02], life=18, color='#FFB347', glow=0.6, comment='и сгорают золотыми искрами'),
           *burns,
           E('flash', 190, 'target+0,1.3,0', duration=14, size=5, anamorphic=12, rays=12, screen=0.45, color='#FFF8E6'),
           E('wave', 190, 'target', duration=22, shape='ring', radius=7, color='@primary'),
           E('wave', 192, 'target', duration=26, shape='ring', radius=4.5, color=B_BLUE),
           E('wave', 190, 'target+0,1,0', duration=18, shape='sphere', radius=2.6, rim=1.2, color=B_BLUE),
           E('sprites', 190, 'target+0,1.4,0', duration=3, texture='feather', count=40, rate=40, spread=0.4, speed=0.2, gravity=0.003,
             sway=1.0, tumble=1, size=[0.45, 0.3], life=50, color='@secondary', comment='перья разлетаются'),
           E('sprites', 191, 'target+0,1.2,0', duration=3, texture='spark_soft', count=60, rate=60, spread=0.5, speed=0.16, gravity=-0.002,
             size=[0.25, 0.03], life=26, color=B_WARM, glow=0.5),
       ])


# ================================================================== иконки
def _hex(h, a=255):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)


def _icon(size, draw, out, frame=None):
    """Рисуем в 8× и уменьшаем LANCZOS — как в gen_spell_icons.ps1 (там 4× и бикубика)."""
    k = 8
    S = size * k
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if frame:                                               # рамка Божественной ступени (gen_spell_icons.ps1: Frame)
        rim, bg = frame
        d.rectangle([k * 0.5, k * 0.5, S - k * 0.5, S - k * 0.5], fill=_hex(bg))
        w = S * 0.07
        d.rectangle([S * 0.05 - w / 2, S * 0.05 - w / 2, S * 0.95 + w / 2, S * 0.95 + w / 2], outline=_hex(rim), width=int(w))
    draw(d, S)
    sm = im.resize((size, size), Image.LANCZOS)
    path = os.path.join(A, out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sm.save(path)
    WRITTEN.append(out)


def _ring(d, S, cx, cy, r, w, col):
    d.ellipse([S * (cx - r), S * (cy - r), S * (cx + r), S * (cy + r)], outline=col, width=int(S * w))


def _keyhole_px(d, S, cx, cy, s, col):
    """Скважина для иконок (доли S)."""
    d.ellipse([S * (cx - s), S * (cy - s * 2.2), S * (cx + s), S * (cy - s * 0.2)], fill=col)
    d.polygon([(S * (cx - s * 0.45), S * (cy - s)), (S * (cx + s * 0.45), S * (cy - s)), (S * (cx + s * 0.85), S * (cy + s * 1.4)),
               (S * (cx - s * 0.85), S * (cy + s * 1.4))], fill=col)


def _padlock(d, S, cx, cy, w, col, dark, shackle):
    """Навесной замок: дужка и корпус со скважиной (доли S)."""
    h = w * 0.82
    d.arc([S * (cx - w * 0.34), S * (cy - h * 1.05), S * (cx + w * 0.34), S * (cy - h * 0.05 + w * 0.2)], 180, 360, fill=shackle,
          width=int(S * w * 0.16))
    d.line([S * (cx - w * 0.34 + w * 0.08), S * (cy - h * 0.45), S * (cx - w * 0.34 + w * 0.08), S * (cy - h * 0.05)], fill=shackle,
           width=int(S * w * 0.16))
    d.line([S * (cx + w * 0.34 - w * 0.08), S * (cy - h * 0.45), S * (cx + w * 0.34 - w * 0.08), S * (cy - h * 0.05)], fill=shackle,
           width=int(S * w * 0.16))
    d.rounded_rectangle([S * (cx - w / 2), S * (cy - h * 0.12), S * (cx + w / 2), S * (cy + h * 0.72)], radius=int(S * w * 0.1), fill=col)
    d.rectangle([S * (cx - w / 2), S * (cy - h * 0.12), S * (cx + w / 2), S * (cy - h * 0.02)], fill=_hex('#FFE9A0'))
    _keyhole_px(d, S, cx, cy + h * 0.36, w * 0.09, dark)


def icon_soul_seal(d, S):
    for a in (math.pi / 4, -math.pi / 4):                             # фиолетовые цепи крест-накрест за замком
        for k in range(-3, 4):
            x, y = 0.5 + k * 0.105 * math.cos(a), 0.5 + k * 0.105 * math.sin(a)
            if k % 2:
                bl = 0.05
                d.line([S * (x - bl * math.cos(a)), S * (y - bl * math.sin(a)), S * (x + bl * math.cos(a)),
                        S * (y + bl * math.sin(a))], fill=_hex('#B08CFF'), width=int(S * 0.06))
            else:
                rx, ry = 0.07, 0.04
                pts = [(S * (x + rx * math.cos(t) * math.cos(a) - ry * math.sin(t) * math.sin(a)),
                        S * (y + rx * math.cos(t) * math.sin(a) + ry * math.sin(t) * math.cos(a))) for t in [2 * math.pi * i / 24 for i in range(25)]]
                d.line(pts, fill=_hex('#8A5CFF'), width=int(S * 0.045))
    d.ellipse([S * 0.2, S * 0.2, S * 0.8, S * 0.8], outline=_hex('#6A3CD0', 200), width=int(S * 0.04))
    _padlock(d, S, 0.5, 0.56, 0.4, _hex('#E8AE3E'), _hex('#140E1E'), _hex('#E6F0FF'))


def icon_blessing(d, S):
    for k in range(12):                                                # мягкие лучи
        a = 2 * math.pi * k / 12
        r0, r1 = 0.1, (0.36 if k % 3 == 0 else 0.26)
        d.line([S * (0.5 + r0 * math.cos(a)), S * (0.6 + r0 * math.sin(a)), S * (0.5 + r1 * math.cos(a)), S * (0.6 + r1 * math.sin(a))],
               fill=_hex('#FFE7A0', 150), width=int(S * 0.035))
    d.ellipse([S * 0.22, S * 0.12, S * 0.78, S * 0.32], outline=_hex('#FFC94D'), width=int(S * 0.08))                         # нимб
    d.polygon([(S * 0.5, S * 0.34), (S * 0.565, S * 0.535), (S * 0.76, S * 0.6), (S * 0.565, S * 0.665), (S * 0.5, S * 0.88),
               (S * 0.435, S * 0.665), (S * 0.24, S * 0.6), (S * 0.435, S * 0.535)], fill=_hex('#FFFFFF'))                    # звезда
    d.ellipse([S * 0.45, S * 0.55, S * 0.55, S * 0.65], fill=_hex('#FFF4D6'))
    for x, y, r in ((0.24, 0.42, 0.045), (0.78, 0.8, 0.04), (0.8, 0.42, 0.03)):                                               # голубые искры
        d.polygon([(S * x, S * (y - 2 * r)), (S * (x + r), S * y), (S * x, S * (y + 2 * r)), (S * (x - r), S * y)], fill=_hex('#A8DCFF'))


def effect_soul_seal(im):
    """18×18, пиксель-арт как divine_backlash: фиолетовое кольцо-цепь с тёмным контуром и золотой замок."""
    px = im.load()
    c = 8.5
    for y in range(18):
        for x in range(18):
            dx, dy = x + 0.5 - c, y + 0.5 - c
            r = math.hypot(dx, dy)
            ang = (math.degrees(math.atan2(dy, dx)) + 360) % 45
            if 6.0 <= r <= 7.6:
                link = min(ang, 45 - ang) < 7
                px[x, y] = _hex('#E0D0FF' if link else ('#9A6CFF' if r < 6.8 else '#7A4CE0'))
            elif 7.6 < r <= 8.45 or 5.25 <= r < 6.0:
                px[x, y] = _hex('#1A0A2E')
    lock = ['..SSSS..',
            '.S....S.',
            '.S....S.',
            'HHHHHHHH',
            'GGGKKGGG',
            'GGGKKGGG',
            'GGGGGGGG',
            'DDDDDDDD']
    col = {'S': '#E6F0FF', 'H': '#FFE18A', 'G': '#E0A63A', 'D': '#9A6A1C', 'K': '#1A0A2E'}
    ox, oy = 5, 5
    filled = set()
    for j, row in enumerate(lock):
        for i, ch in enumerate(row):
            if ch != '.':
                filled.add((ox + i, oy + j))
                px[ox + i, oy + j] = _hex(col[ch])
    for (x, y) in list(filled):                                         # тёмный контур замка
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in filled and 0 <= nx < 18 and 0 <= ny < 18 and math.hypot(nx + 0.5 - c, ny + 0.5 - c) < 5.25:
                px[nx, ny] = _hex('#1A0A2E')


def icons():
    _icon(16, icon_soul_seal, 'textures/gui/spell_icons/soul_seal.png', frame=('#FFD34D', '#140E1E'))
    _icon(16, icon_blessing, 'textures/gui/spell_icons/blessing.png', frame=('#FFD34D', '#1E1A06'))
    im = Image.new('RGBA', (18, 18), (0, 0, 0, 0))
    effect_soul_seal(im)
    im.save(os.path.join(A, 'textures/mob_effect/soul_seal.png'))
    WRITTEN.append('textures/mob_effect/soul_seal.png')


if __name__ == '__main__':
    textures()
    soul_sigils()
    bless_sigils()
    soul_fx()
    bless_fx()
    icons()
    print('\n'.join(WRITTEN))
    print(len(WRITTEN), 'files (+ 4 textures)')
