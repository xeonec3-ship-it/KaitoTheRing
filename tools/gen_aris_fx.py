#!/usr/bin/env python3
"""
T28 «Арис, Мифический Кузнец» — эффекты (fx/aris_*.json, стиль fx/styles/aris.json), меши (fx/meshes/aris_*.json: наковальня,
клинки её ковки, исполинский молот), печати (sigils/aris_*.json + textures/sigil/aris_*.png), полоса здоровья по фазам
(textures/gui/sprites/boss_bars/aris_bossbar*.png), титры (textures/gui/title/aris*_{ru,en}.png), иконки статусов
(textures/mob_effect/aris_*.png), lang ru/en, звуки (sounds.json, ваниль с другим pitch), обзорные листы docs/media/t28_*.
Вызывается из tools/gen_aris.py (run(G, AN, args, anims)).

Время — тики (20 в секунду), размеры — блоки, углы — градусы. Палитра: тёмная сталь, серая сталь, бирюза (свечение), лиловый,
белый камень; раскалённый металл — от вишнёвого к бело-жёлтому (HOT).
"""
import json
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

G = None
AN = None
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
MEDIA = os.path.join(ROOT, 'docs', 'media')

TEAL, TEAL_HI, TEAL_D = '#3CD6E0', '#C8FBFC', '#0F6470'
STEEL, STEEL_L, STEEL_D = '#60606C', '#A9A9B4', '#2A2A32'
LILAC, LILAC_D = '#AD46C6', '#561A6C'
MOLTEN, MOLTEN_HI, MOLTEN_CORE, MOLTEN_D = '#F4A852', '#FFD490', '#FFF6E2', '#A8502A'
STONE = '#E8E8F0'
R_ARENA = 24             # радиус арены (как у T26: 24–28)
T_INTRO = 180            # ролик появления = анимация spawn (9.0 с)
WRITTEN = []


def write(rel, obj):
    G.write_json(rel, obj)


def E(type_, delay=0, at='caster', **kw):
    o = {'type': type_, 'delay': delay, 'at': at}
    o.update(kw)
    return o


def ease(d, e='easeOutCubic'):
    return {'duration': d, 'easing': e}


def at(base, x=0.0, y=0.0, z=0.0):
    """Якорь fx со смещением в осях взгляда кастера: x — вправо, y — вверх, z — ВПЕРЁД (FxDef.Anchor: forward = +z).
    Внимание: в осях модели (Blockbench/GeckoLib) вперёд — это −z; точку модели (mx, my, mz) в ед. переводить как
    at(F, mx/16, my/16, −mz/16). Смещение к уже смещённому якорю складывается (раньше получалось «caster+0,0,1+0,0.6,0»)."""
    f = lambda v: (str(int(v)) if float(v) == int(v) else str(round(v, 2)))
    if '+' in base:
        base, off = base.split('+', 1)
        ox, oy, oz = (float(v) for v in off.split(','))
        x, y, z = x + ox, y + oy, z + oz
    return '%s+%s,%s,%s' % (base, f(x), f(y), f(z))


def fx(id_, comment, dur, els, style='aris'):
    write('fx/%s.json' % id_, {'comment': comment + ' Сгенерировано tools/gen_aris.py.', 'style': style, 'duration': dur, 'elements': els})


def hx(c, a=255):
    c = c.lstrip('#')
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


# ================================================================== рисунки печатей (белое на прозрачном, 512×512)
S4 = 4                       # рисуем ×4 и уменьшаем


def canvas(n=512):
    im = Image.new('L', (n * S4, n * S4), 0)
    return im, ImageDraw.Draw(im), n * S4 / 2


def save_sigil(im, name, n=512):
    small = im.resize((n, n), Image.LANCZOS)
    rgba = Image.new('RGBA', (n, n), (255, 255, 255, 0))
    rgba.putalpha(small)
    rgba.save(G.out('textures/sigil/%s.png' % name))


def ring(d, c, r, w, fill=255):
    d.ellipse([c - r, c - r, c + r, c + r], outline=fill, width=int(w))


def anvil_poly(cx, cy, s):
    """Силуэт наковальни (вид сбоку): рог слева, основание-ступенька."""
    p = [(-0.95, -0.35), (-0.55, -0.42), (0.75, -0.42), (0.75, -0.12), (0.35, -0.08), (0.28, 0.12), (0.5, 0.18), (0.55, 0.38),
         (-0.45, 0.38), (-0.4, 0.18), (-0.18, 0.12), (-0.25, -0.08), (-0.55, -0.15)]
    return [(cx + x * s, cy + y * s) for x, y in p]


def hammer_poly(cx, cy, s, ang):
    """Силуэт двуглавого молота (вид спереди), повёрнутый на ang (рад)."""
    pts = [(-0.55, -0.62), (0.55, -0.62), (0.55, -0.28), (0.07, -0.28), (0.07, 0.62), (-0.07, 0.62), (-0.07, -0.28), (-0.55, -0.28)]
    c, s_ = math.cos(ang), math.sin(ang)
    return [(cx + (x * c - y * s_) * s, cy + (x * s_ + y * c) * s) for x, y in pts]


def tex_emblem():
    """Знак Арис: наковальня, над ней два скрещённых молота, рога-полумесяц; кольцо с насечками."""
    im, d, c = canvas()
    ring(d, c, c * 0.95, 14)
    ring(d, c, c * 0.86, 6)
    for k in range(48):
        a = 2 * math.pi * k / 48
        r0, r1 = c * 0.87, c * (0.93 if k % 4 else 0.95)
        d.line([(c + r0 * math.cos(a), c + r0 * math.sin(a)), (c + r1 * math.cos(a), c + r1 * math.sin(a))], fill=255, width=10)
    d.polygon(anvil_poly(c, c + c * 0.28, c * 0.62), fill=255)
    for sgn in (-1, 1):
        d.polygon(hammer_poly(c + sgn * c * 0.12, c - c * 0.22, c * 0.42, sgn * 0.6), fill=255)
    # рога над знаком
    for sgn in (-1, 1):
        pts = [(c + sgn * c * (0.2 + 0.25 * t ** 0.8), c - c * (0.38 + 0.4 * t)) for t in np.linspace(0, 1, 20)]
        for i in range(len(pts) - 1):
            d.line([pts[i], pts[i + 1]], fill=255, width=int(40 * (1 - i / 22)))
    save_sigil(im, 'aris_emblem')


def tex_forge_ring():
    """«Горн»: кольцо огнеупорного кирпича (кладка), внутри — решётка колосника и угли; знаки ковки по ободу."""
    im, d, c = canvas()
    ring(d, c, c * 0.97, 22)
    ring(d, c, c * 0.88, 10)
    for k in range(64):                                   # кладка кирпичей в ободе
        a = 2 * math.pi * k / 64
        r0, r1 = c * 0.885, c * 0.965
        d.line([(c + r0 * math.cos(a), c + r0 * math.sin(a)), (c + r1 * math.cos(a), c + r1 * math.sin(a))], fill=255, width=8)
    for k in range(12):                                   # знаки: молот / наковальня попеременно
        a = 2 * math.pi * k / 12
        x, y = c + c * 0.78 * math.cos(a), c + c * 0.78 * math.sin(a)
        if k % 2:
            d.polygon(anvil_poly(x, y, c * 0.07), fill=255)
        else:
            d.polygon(hammer_poly(x, y, c * 0.07, a + math.pi / 2), fill=255)
    ring(d, c, c * 0.68, 8)
    for k in range(-6, 7):                                # колосник
        x = c + k * c * 0.1
        h = math.sqrt(max(0, (c * 0.66) ** 2 - (x - c) ** 2))
        d.line([(x, c - h), (x, c + h)], fill=150, width=10)
    save_sigil(im, 'aris_forge_ring')


def tex_target():
    """«Последний удар молота»: прицел-печать: концентрические кольца, крест рисок, силуэт молота в центре, клинья к центру."""
    im, d, c = canvas()
    for r, w in ((0.97, 18), (0.8, 8), (0.62, 12), (0.42, 6), (0.22, 10)):
        ring(d, c, c * r, w)
    for k in range(16):
        a = 2 * math.pi * k / 16
        r0, r1 = c * (0.62 if k % 2 else 0.42), c * 0.97
        d.line([(c + r0 * math.cos(a), c + r0 * math.sin(a)), (c + r1 * math.cos(a), c + r1 * math.sin(a))], fill=255, width=12 if k % 2 == 0 else 6)
    for k in range(8):                                    # клинья, «сходящиеся» к центру
        a = 2 * math.pi * (k + 0.5) / 8
        tip = (c + c * 0.66 * math.cos(a), c + c * 0.66 * math.sin(a))
        b1 = (c + c * 0.78 * math.cos(a - 0.08), c + c * 0.78 * math.sin(a - 0.08))
        b2 = (c + c * 0.78 * math.cos(a + 0.08), c + c * 0.78 * math.sin(a + 0.08))
        d.polygon([tip, b1, b2], fill=255)
    d.polygon(hammer_poly(c, c, c * 0.34, 0), fill=255)
    save_sigil(im, 'aris_target')


def tex_reforge():
    """Метка «перековки» на оружии игрока: перечёркнутый клинок под молотом, в кольце."""
    im, d, c = canvas(256)
    ring(d, c, c * 0.92, 16)
    d.polygon([(c - c * 0.08, c + c * 0.7), (c + c * 0.08, c + c * 0.7), (c + c * 0.08, c - c * 0.35), (c, c - c * 0.6),
               (c - c * 0.08, c - c * 0.35)], fill=255)
    d.rectangle([c - c * 0.3, c + c * 0.38, c + c * 0.3, c + c * 0.46], fill=255)
    d.polygon(hammer_poly(c + c * 0.25, c - c * 0.3, c * 0.42, 0.7), fill=255)
    for k in range(5):                                    # трещины по клинку
        y = c - c * 0.2 + k * c * 0.16
        d.line([(c - c * 0.12, y), (c + c * 0.12, y + c * 0.07)], fill=0, width=10)
    save_sigil(im, 'aris_reforge', 256)


def tex_island():
    """Безопасный островок в «Горне»: остывший камень — кольцо с насечками и снежинка-ромб в центре."""
    im, d, c = canvas(256)
    ring(d, c, c * 0.94, 18)
    for k in range(24):
        a = 2 * math.pi * k / 24
        d.line([(c + c * 0.78 * math.cos(a), c + c * 0.78 * math.sin(a)), (c + c * 0.9 * math.cos(a), c + c * 0.9 * math.sin(a))],
               fill=255, width=8)
    d.polygon([(c, c - c * 0.4), (c + c * 0.4, c), (c, c + c * 0.4), (c - c * 0.4, c)], outline=255, width=14)
    save_sigil(im, 'aris_island', 256)


def tex_molten_ring():
    """Текстура волны раскалённого металла (wave.texture): рваный гребень с каплями."""
    n = 512
    im = Image.new('L', (n * S4, 64 * S4), 0)
    d = ImageDraw.Draw(im)
    rng = random.Random(28)
    W, H = n * S4, 64 * S4
    pts = [(0, H)]
    for x in range(0, W + 1, 24):
        y = H * (0.35 + 0.25 * math.sin(x / W * 2 * math.pi * 6) + rng.uniform(-0.08, 0.08))
        pts.append((x, y))
    pts.append((W, H))
    d.polygon(pts, fill=255)
    for k in range(40):
        x, y = rng.uniform(0, W), rng.uniform(0, H * 0.4)
        r = rng.uniform(6, 18)
        d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    im = im.resize((n, 64), Image.LANCZOS)
    rgba = Image.new('RGBA', im.size, (255, 255, 255, 0))
    rgba.putalpha(im)
    rgba.save(G.out('textures/sigil/aris_molten_ring.png'))


def tex_molten_floor():
    """Пол-горн (decal): раскалённая трещиноватая корка — сеть трещин (ярко) по тёмным плиткам."""
    n = 512
    im = Image.new('L', (n * 2, n * 2), 0)
    d = ImageDraw.Draw(im)
    rng = random.Random(281)
    c = n
    for k in range(70):                                   # трещины ветвятся от центра и по кругу
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0, c * 0.95)
        x, y = c + r * math.cos(a), c + r * math.sin(a)
        for s in range(rng.randint(3, 7)):
            a += rng.uniform(-0.8, 0.8)
            L = rng.uniform(20, 70)
            nx, ny = x + L * math.cos(a), y + L * math.sin(a)
            if math.hypot(nx - c, ny - c) > c * 0.98:
                break
            d.line([(x, y), (nx, ny)], fill=255, width=rng.choice((3, 4, 6)))
            x, y = nx, ny
    im = im.filter(ImageFilter.MaxFilter(3)).resize((n, n), Image.LANCZOS)
    # мягкий жар под трещинами
    glow = im.filter(ImageFilter.GaussianBlur(10))
    a = np.maximum(np.asarray(im, float), np.asarray(glow, float) * 0.6)
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot(xx - n / 2, yy - n / 2) / (n / 2)
    a = a * np.clip((1 - r) * 8, 0, 1)
    rgba = Image.new('RGBA', (n, n), (255, 255, 255, 0))
    rgba.putalpha(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)))
    rgba.save(G.out('textures/sigil/aris_molten_floor.png'))


def textures():
    tex_emblem()
    tex_forge_ring()
    tex_target()
    tex_reforge()
    tex_island()
    tex_molten_ring()
    tex_molten_floor()


# ================================================================== печати
def ap(delay, dur, *modes, easing='easeOutCubic', **kw):
    o = {'delay': delay, 'duration': dur, 'easing': easing, 'modes': list(modes)}
    o.update(kw)
    return o


def L(id_, type_, tex, radius, h=0.0, appear=None, rot=None, color=None, br=None, pulse=None, **kw):
    o = {'id': id_, 'type': type_}
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
        o['rotation'] = {'speed': rot}
    if pulse:
        o['pulse'] = {'amp': pulse[0], 'period': pulse[1]}
    return o


def Tx(id_, text, radius, size, h, appear, color=None, br=None, rot=None, repeat=1):
    o = L(id_, 'text', None, radius, h, appear, rot=rot, color=color, br=br)
    o.update({'text': text, 'font': 'cyrillic', 'size': size, 'repeat': repeat, 'side': 'outer'})
    return o


def sigil(id_, comment, size, color, layers, flash=None, dissolve=('fade', 'collapse'), ddur=16):
    o = {'comment': comment + ' Сгенерировано tools/gen_aris.py.', 'size': size, 'color': color, 'orientation': 'ground',
         'lifetime': -1, 'hold': -1, 'layers': layers}
    if flash:
        o['formedFlash'] = flash
    o['dissolve'] = {'modes': list(dissolve), 'duration': ddur, 'stagger': 2}
    write('sigils/%s.json' % id_, o)


def sigils():
    sigil('aris_emblem', 'T28: знак Арис (наковальня, два молота, рога) под ней — появление, переходы фаз, сдача.', 3.2, TEAL, [
        L('glow', 'disc', 'glow', 1.0, -0.01, ap(0, 10, 'fade'), color=TEAL_D, br=0.6, pulse=(0.15, 18)),
        L('seal', 'disc', 'aris_emblem', 1.0, 0.0, ap(0, 18, 'draw', startAngle=90), rot=0.8),
        L('rim', 'band', 'chain_band', 1.16, 0.01, ap(8, 12, 'draw', startAngle=90, direction=-1), inner=0.9, repeat=3, rot=-1.5,
          color=STEEL_L, br=0.7),
    ], flash={'color': TEAL_HI, 'size': 1.3, 'duration': 10, 'sparks': 40}, dissolve=('shatter', 'fade'), ddur=14)
    sigil('aris_forge', 'T28 «Горн»: обод горна r24 по краю арены (кладка, знаки ковки, колосник). 0–60 тиков прорисовывается '
          '(предупреждение), дальше держится до конца эффекта.', R_ARENA, MOLTEN, [
        L('glow', 'disc', 'glow', 1.0, -0.02, ap(0, 60, 'fade', easing='easeInSine'), color=MOLTEN_D, br=0.4, pulse=(0.12, 24)),
        L('ring', 'disc', 'aris_forge_ring', 1.0, 0.0, ap(0, 56, 'draw', startAngle=90, easing='easeInOutSine'), rot=0.15),
        Tx('words', 'ГОРН АРИС ✦ МЕТАЛЛ ПЛАВИТСЯ ✦ ИЩИ ХОЛОДНЫЙ КАМЕНЬ ✦ ', 0.75, 0.045, 0.01, ap(10, 40, 'draw', easing='linear'),
           color=MOLTEN_HI, br=0.9, rot=-0.3, repeat=2),
    ], flash={'color': MOLTEN_HI, 'size': 1.05, 'duration': 14, 'sparks': 160})
    sigil('aris_island', 'T28 «Горн»: безопасный островок r2.2 (остывший камень) — бирюзовое кольцо; code ставит 4–6 шт.', 2.2, TEAL, [
        L('stone', 'disc', 'glow', 1.0, -0.01, ap(0, 10, 'fade'), color=STEEL_L, br=0.35),
        L('ring', 'disc', 'aris_island', 1.0, 0.0, ap(0, 14, 'draw', startAngle=90), rot=0.6, pulse=(0.15, 20)),
    ], dissolve=('fade',), ddur=10)
    sigil('aris_target', 'T28 «Последний удар молота»: прицел r14 в центре арены — прорисовывается 3.5 с (предупреждение), '
          'клинья сходятся к центру.', 14, TEAL, [
        L('glow', 'disc', 'glow', 1.0, -0.02, ap(0, 70, 'fade', easing='easeInSine'), color=TEAL_D, br=0.5, pulse=(0.2, 10)),
        L('seal', 'disc', 'aris_target', 1.0, 0.0, ap(0, 60, 'draw', startAngle=90, easing='easeInOutSine'), rot=-0.6),
        L('arcs', 'arcs', 'arc_strip', 1.04, 0.02, ap(30, 30, 'assemble', 'fade'), count=8, arcLength=30, width=0.012, rot=2.0,
          color=TEAL_HI, br=1.1),
    ], flash={'color': TEAL_HI, 'size': 1.1, 'duration': 12, 'sparks': 100})
    sigil('aris_reforge', 'T28 «Перековка»: метка над рукой игрока (оружие ослаблено 10 с) — перечёркнутый клинок под молотом.', 0.42, MOLTEN, [
        L('mark', 'disc', 'aris_reforge', 1.0, 0.0, ap(0, 8, 'grow', 'fade'), rot=1.5, br=1.1, pulse=(0.15, 16)),
    ], dissolve=('fade',), ddur=8)


# ================================================================== меши (fx/meshes, части boxes — docs/fx.md)
def bx(x0, y0, z0, x1, y1, z1, tone, rot=None):
    b = [round(min(x0, x1), 4), round(min(y0, y1), 4), round(min(z0, z1), 4), round(max(x0, x1), 4), round(max(y0, y1), 4),
         round(max(z0, z1), 4), tone]
    if rot:
        b.append(rot)
    return b


def mesh(id_, comment, parts, formed=10, collapse=10, extra=None):
    o = {'comment': comment + ' Сгенерировано tools/gen_aris.py.', 'style': 'aris', 'center': 0, 'formedAt': formed,
         'collapse': {'duration': collapse, 'easing': 'easeInCubic'}, 'parts': parts}
    if extra:
        o.update(extra)
    write('fx/meshes/%s.json' % id_, o)


def mesh_anvil():
    """Наковальня-препятствие 2.6×1.6×1.2 бл. (рог к −x), раскалённая: светятся швы и рабочая поверхность; растёт из земли."""
    T = {'d': 0, 's': 1, 'l': 2, 'hot': 3, 'teal': 4, 'k': 5}
    b = [
        bx(-0.7, 0, -0.55, 0.7, 0.25, 0.55, T['d']), bx(-0.55, 0.25, -0.42, 0.55, 0.4, 0.42, T['s']),     # основание
        bx(-0.32, 0.4, -0.3, 0.32, 0.95, 0.3, T['d']),                                                   # шейка
        bx(-0.95, 0.95, -0.42, 0.95, 1.45, 0.42, T['s']),                                                 # тело
        bx(-0.95, 1.45, -0.42, 0.95, 1.55, 0.42, T['l']),                                                 # наличник
        bx(0.95, 1.05, -0.32, 1.25, 1.55, 0.32, T['s']),                                                  # пятка
        bx(-1.35, 1.2, -0.25, -0.95, 1.5, 0.25, T['s']), bx(-1.65, 1.3, -0.15, -1.35, 1.45, 0.15, T['l']),  # рог
        bx(0.55, 1.5, -0.08, 0.7, 1.56, 0.08, T['k']), bx(0.3, 1.5, -0.06, 0.4, 1.56, 0.06, T['k']),       # отверстия
        bx(-0.68, 0.24, -0.56, 0.68, 0.27, 0.56, T['teal']),                                              # бирюзовый пояс
    ]
    glow = [bx(-0.9, 1.555, -0.36, 0.5, 1.6, 0.36, T['hot']),                                             # раскалённая поверхность
            bx(-0.96, 0.94, -0.43, 0.96, 0.98, 0.43, T['hot']), bx(-0.33, 0.4, -0.31, 0.33, 0.44, 0.31, T['hot'])]
    tones = ['#2A2A32', '#4C4C57', '#8E8E9A', MOLTEN_HI, TEAL, '#0E0E12']
    mesh('aris_anvil', 'T28 «Ковка»: наковальня-препятствие 2.6×1.6×1.2 бл. (рог к −x модели), растёт из земли за 12 тиков, '
                       'раскалённые швы. Коллизию даёт сущность кода (AABB 2.6×1.6×1.2), меш — только вид; разборка — collapse 10 тиков.',
         [{'type': 'boxes', 'tones': tones, 'glowTones': [3, 4], 'blend': 'translucent', 'opacity': 1.0, 'shade': True, 'boxes': b,
           'appear': {'delay': 0, 'duration': 12, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.4}, 'bounds': [0, 1.6]},
          {'type': 'boxes', 'tones': tones, 'glowTones': [3], 'blend': 'additive', 'opacity': 0.9, 'shade': False, 'boxes': glow,
           'appear': {'delay': 8, 'duration': 8, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.2}, 'bounds': [0, 1.6]}],
         formed=16, collapse=10)


def blade_boxes(kind):
    """Клинок вдоль +z (остриё вперёд), плоскость лезвия — XZ? нет: лезвие в плоскости YZ (ребро вверх) — так он «режет» воздух."""
    T = {'d': 0, 's': 1, 'l': 2, 'edge': 3, 'teal': 4, 'lil': 5}
    b, g = [], []
    if kind == 'sword':                                       # прямой меч: 1.8 бл.
        b += [bx(-0.05, -0.12, -0.55, 0.05, 0.12, 0.85, T['s']), bx(-0.06, -0.04, -0.55, 0.06, 0.04, 0.8, T['l']),
              bx(-0.04, -0.07, 0.85, 0.04, 0.07, 1.0, T['s'])]
        b += [bx(-0.09, -0.3, -0.62, 0.09, 0.3, -0.52, T['d']), bx(-0.05, -0.05, -0.95, 0.05, 0.05, -0.62, T['lil']),
              bx(-0.07, -0.07, -1.02, 0.07, 0.07, -0.95, T['d'])]
        g += [bx(-0.02, 0.11, -0.5, 0.02, 0.135, 0.95, T['edge']), bx(-0.02, -0.135, -0.5, 0.02, -0.11, 0.95, T['edge']),
              bx(-0.1, -0.08, -0.6, 0.1, 0.08, -0.54, T['teal'])]
    else:                                                     # глефа-тесак: широкое изогнутое лезвие 1.6 бл.
        b += [bx(-0.05, -0.2, -0.2, 0.05, 0.16, 0.6, T['s']), bx(-0.05, -0.12, 0.6, 0.05, 0.12, 0.85, T['s']),
              bx(-0.05, -0.04, 0.85, 0.05, 0.06, 1.0, T['s']), bx(-0.06, -0.02, -0.2, 0.06, 0.04, 0.7, T['l'])]
        b += [bx(-0.08, -0.22, -0.3, 0.08, 0.22, -0.2, T['d']), bx(-0.05, -0.05, -0.8, 0.05, 0.05, -0.3, T['lil'])]
        g += [bx(-0.02, -0.235, -0.15, 0.02, -0.2, 0.6, T['edge']), bx(-0.02, -0.13, 0.6, 0.02, -0.1, 0.85, T['edge']),
              bx(-0.03, 0.1, 0.1, 0.03, 0.16, 0.4, T['teal'])]
    return b, g


def mesh_blades():
    tones = ['#2A2A32', '#76768A', '#A9A9B4', '#E8FFFE', TEAL, LILAC]
    for kind, nm in (('sword', 'aris_blade_sword'), ('glaive', 'aris_blade_glaive')):
        b, g = blade_boxes(kind)
        mesh(nm, 'T28 «Оружейная»: парящий клинок её ковки (%s), остриё вдоль +z модели (yaw/pitch — по полёту), длина ~1.8 бл. '
                 'Код: сущность-клинок (сбиваемая, ХП/хитбокс 0.6), fx aris_blade с mesh follow + pitch. Кромка и бирюзовая вставка светятся.'
             % ('меч' if kind == 'sword' else 'глефа'),
             [{'type': 'boxes', 'tones': tones, 'glowTones': [3, 4], 'blend': 'translucent', 'opacity': 1.0, 'shade': True, 'boxes': b,
               'appear': {'delay': 0, 'duration': 8, 'easing': 'easeOutCubic', 'reveal': 'down', 'front': 0.3}, 'bounds': [-0.3, 0.3]},
              {'type': 'boxes', 'tones': tones, 'glowTones': [3, 4], 'blend': 'additive', 'opacity': 0.95, 'shade': False, 'boxes': g,
               'appear': {'delay': 4, 'duration': 6, 'easing': 'easeOutCubic', 'reveal': 'down', 'front': 0.2}, 'bounds': [-0.3, 0.3]}],
             formed=10, collapse=6)


def mesh_giant_hammer():
    """Исполинский призрачный молот для «Последнего удара»: та же форма, что у её молота (hammer_parts), ×8 (≈ 14 бл. длиной),
    голова внизу (бьёт по центру); бирюзовое полупрозрачное тело + светящиеся вставки."""
    K = 8 * 0.0625 * 0.9                                      # ед. предмета → блоки, ×8
    mat_tone = {'hk': 0, 'hd': 0, 'hs': 1, 'hs2': 2, 'hsh': 0, 'hg': 3, 'hw': 4, 'hst': 5}
    body, glow = [], []
    top = 32.7
    for (cx, cy, cz, sx, sy, sz, mat, rz_) in G.hammer_parts():
        y = (top - cy) * K                                    # голова внизу, рукоять вверх
        b = bx((cx - sx / 2) * K, y - sy / 2 * K, (cz - sz / 2) * K, (cx + sx / 2) * K, y + sy / 2 * K, (cz + sz / 2) * K,
               mat_tone[mat], [0, 0, rz_] if rz_ else None)
        (glow if mat in ('hg', 'hst') else body).append(b)
    tones = ['#0F6470', '#168E9E', '#22B4C4', TEAL_HI, LILAC, '#FFFFFF']
    mesh('aris_giant_hammer', 'T28 «Последний удар молота»: исполинский призрачный молот (её молот ×8, ~14 бл.), голова внизу, '
                              'точка (0,0,0) — низ головы. Появляется сверху (move.keys в эффекте aris_last_blow) и бьёт в центр.',
         [{'type': 'boxes', 'tones': tones, 'glowTones': [], 'blend': 'additive', 'opacity': 0.55, 'shade': True, 'boxes': body,
           'appear': {'delay': 0, 'duration': 30, 'easing': 'easeOutCubic', 'reveal': 'down', 'front': 2.0}, 'bounds': [0, 15]},
          {'type': 'boxes', 'tones': tones, 'glowTones': [3, 5], 'blend': 'additive', 'opacity': 1.0, 'shade': False, 'boxes': glow,
           'appear': {'delay': 10, 'duration': 24, 'easing': 'easeOutCubic', 'reveal': 'down', 'front': 1.5}, 'bounds': [0, 15]}],
         formed=34, collapse=14)


def meshes():
    mesh_anvil()
    mesh_blades()
    mesh_giant_hammer()


# ================================================================== эффекты
def effects():
    write('fx/styles/aris.json', {
        'comment': 'T28 Арис, Мифический Кузнец: кузня — бирюзовое свечение рогов и каймы, раскалённый металл (вишнёвый → бело-жёлтый), '
                   'искры, сталь. Движение тяжёлое, ударное: короткие вспышки, волны по земле. Сгенерировано tools/gen_aris.py.',
        'palette': {'primary': TEAL, 'secondary': MOLTEN, 'core': MOLTEN_CORE, 'shadow': STEEL_D},
        'textures': {'sparks': 'spark_soft', 'runes': 'chain_band', 'shards': 'mote_flame', 'sigil': 'aris_emblem'},
        'blend': 'additive', 'motion': {'rotationScale': 0.8, 'jitter': 0.15, 'easing': 'easeOutCubic', 'pulse': {'amp': 0.12, 'period': 10}}})

    def sparks(t, p, n=40, spd=0.35, life=18, dur=4, col='@secondary'):
        return E('sprites', t, p, duration=dur, texture='spark_soft', count=n, rate=max(1, n // dur), spread=0.6, speed=spd, gravity=0.03,
                 size=[0.16, 0.02], life=life, color=col, glow=0.9)

    def impact(t, p, r=8.0, big=1.0):
        return [E('flash', t, at(p, 0, 0.6, 0), duration=10, size=2.6 * big, rays=10, color='@core', ring=True),
                E('wave', t, p, duration=22, shape='ring', radius=r, thickness=1.6 * big, followTerrain=True, texture='aris_molten_ring',
                  color='@secondary', comment='волна раскалённого металла'),
                E('decal', t, p, duration=120, texture='aris_molten_floor', radius=2.2 * big, glow=0.8, fadeOut=80, color='@secondary',
                  brightness=1.2, comment='раскалённая вмятина остывает 4 с'),
                sparks(t, at(p, 0, 0.3, 0), int(60 * big), 0.45 * big, 22),
                E('sprites', t, at(p, 0, 0.2, 0), duration=6, texture='mote_ash', count=int(24 * big), rate=6, spread=1.2 * big, speed=0.08,
                  gravity=-0.004, spin=40, size=[0.6, 0.2], life=30, color=STEEL, blend='translucent', comment='пыль/окалина')]

    F = 'caster'
    # ---------------------------------------------------------------- появление
    fx('aris_intro', 'Ролик появления 9.0 с (180 тиков = анимация animation.aris.spawn). caster = точка появления, yaw — взгляд Арис. '
       '0–2 с: земля трескается, расплав набухает, трижды бьёт невидимый молот (вспышки на 0.6/1.2/1.8 с); 2.0–4.5 с — Арис поднимается '
       'из озера расплава на колене, опираясь на молот (анимация); 6.0 с — рога загораются (код: текстура aris_dim → aris); '
       '7.0 с — удар молотом: волна r14, вспышка; 7.5 с — знак Арис под ней + титр; 9.0 с — полоса босса.', T_INTRO, [
        E('tint', 0, F, duration=T_INTRO, radius=40, color='#2A140C', strength=0.28, **{'in': ease(30), 'out': ease(30, 'easeInSine')}),
        E('decal', 0, F, duration=150, texture='higher_cracks', radius=5, grow=30, glow=0.8, fadeOut=40, color='@secondary', brightness=1.2,
          comment='трещины с жаром'),
        E('decal', 20, F, duration=120, texture='aris_molten_floor', radius=3.4, grow=20, glow=1.0, fadeOut=50, color='@secondary',
          brightness=1.3, comment='озеро расплава'),
        E('column', 40, F, duration=60, radius=1.6, height=3.5, fill=0.35, color='@secondary', out=ease(20, 'easeInSine')),
        E('sprites', 20, at(F, 0, 0.1, 0), duration=110, texture='mote_flame', count=100000, rate=0.8, area=2.6, speed=0.03, gravity=-0.02,
          size=[0.35, 0.05], life=24, color='@secondary', glow=0.7, comment='пузыри и брызги расплава'),
        *[E('flash', t, at(F, 0, 0.3, 0), duration=8, size=2.0, color='@core') for t in (12, 24, 36)],
        *[E('wave', t, F, duration=14, shape='ring', radius=4, thickness=0.8, followTerrain=True, color='@secondary') for t in (12, 24, 36)],
        *[sparks(t, at(F, 0, 0.3, 0), 30, 0.3, 16) for t in (12, 24, 36)],
        E('sigil', 90, at(F, 0, 0.04, 0), id='aris_emblem', comment='знак под ней, когда встаёт на колено'),
        E('aura', 120, F, duration=20, follow=True, target='caster', thickness=0.18, pulse=[0.3, 6], color='@primary', motes=20,
          comment='6.0 с: рога и кайма вспыхивают'),
        *impact(140, at(F, 0.05, 0, 1.3), r=14, big=1.4),                  # боёк на 7.0: ≈1.3 бл. ВПЕРЕДИ (+z)
        E('flash', 140, at(F, 0, 2.0, 0), duration=12, size=4.0, rays=12, screen=0.15, color='@primary'),
        E('sigil', 150, at(F, 0, 0.05, 0), id='aris_emblem', comment='7.5 с — титр'),
    ])
    # ---------------------------------------------------------------- фаза 1 «Ковка»
    fx('aris_slam', 'Удар молотом по земле (фаза 1, событие impact анимации slam/forge, 0.75 с). caster = точка удара (голова молота: '
       '≈1.35 бл. перед Арис по её взгляду; у forge ≈1.2, у last_blow ≈1.45), не follow. Волна раскалённого металла r8 бежит 1.1 с: урон кодом по кольцу |d − r(t)| < 0.7, '
       'r(t) = 8·t/22 тиков; перепрыгнуть можно (выше 1 бл.).', 40, impact(0, F, r=8))
    fx('aris_metal_wave', 'Волна раскалённого металла веером вперёд (фаза 1): caster = Арис, yaw — направление; 5 гребней по линии 10 бл. '
       'с шагом 2 тика (код наносит урон по полосе ширины 3 бл.).', 40, [
        *[E('decal', 2 * k, at(F, 0, 0, 2 + 2 * k), duration=60, texture='aris_molten_floor', radius=1.4 + 0.2 * k, glow=1.0, fadeOut=40,
            color='@secondary', brightness=1.2) for k in range(5)],
        *[E('curtain', 2 * k, at(F, 0, 0, 2 + 2 * k), duration=14, radius=[0.2, 1.2], count=8, height=1.4, grow=4, width=[0.3, 0.6],
            brightness=[0.7, 1.0], flicker=0.6, texture='mote_flame', color='@secondary', out=ease(8)) for k in range(5)],
        *[sparks(2 * k, at(F, 0, 0.3, 2 + 2 * k), 16, 0.25, 14, 2) for k in range(5)],
    ])
    fx('aris_anvil_rise', 'Наковальня-препятствие вырастает из земли (фаза 1): caster = место, yaw — поворот. 0–12 тиков растёт (меш '
       'aris_anvil), пыль и искры; держится до Fx.stop (код: 8 с) — тогда разборка 10 тиков и fx aris_anvil_break.', -1, [
        E('mesh', 0, F, model='aris_anvil', follow=False),
        E('decal', 0, F, duration=40, texture='higher_cracks', radius=1.8, glow=0.6, fadeOut=20, color='@secondary'),
        E('sprites', 0, at(F, 0, 0.1, 0), duration=10, texture='mote_ash', count=30, rate=4, spread=1.2, speed=0.06, gravity=-0.003,
          spin=40, size=[0.5, 0.15], life=24, color=STEEL, blend='translucent'),
        sparks(10, at(F, 0, 1.55, 0), 24, 0.25, 14, 3),
        E('sprites', 16, at(F, 0, 1.6, 0), texture='mote_flame', count=100000, rate=0.15, area=0.7, speed=0.01, gravity=-0.015,
          size=[0.15, 0.03], life=20, color='@secondary', comment='жар над раскалённой поверхностью'),
    ])
    fx('aris_anvil_break', 'Наковальня рассыпается (caster = её место): окалина, искры, вспышка.', 20, [
        E('flash', 0, at(F, 0, 0.8, 0), duration=6, size=1.6, color='@secondary'),
        sparks(0, at(F, 0, 0.8, 0), 40, 0.3, 16),
        E('sprites', 0, at(F, 0, 0.8, 0), duration=4, texture='mote_ash', count=30, rate=8, spread=0.9, speed=0.12, gravity=0.02, spin=60,
          size=[0.35, 0.12], life=20, color=STEEL_D, blend='translucent'),
    ])
    # ---------------------------------------------------------------- фаза 2 «Оружейная»
    for kind in ('sword', 'glaive'):
        fx('aris_blade_%s' % kind, 'Парящий клинок её ковки (фаза 2): caster = сущность-клинок, follow; yaw/pitch — по направлению полёта '
           '(MeshDraw: pitch наклоняет ось +z). Меш aris_blade_%s + бирюзовый ореол, искры с кромки. До Fx.stop.' % kind, -1, [
            E('mesh', 0, F, model='aris_blade_%s' % kind, follow=True, comment='yaw/pitch — из ctx (код передаёт направление полёта)'),
            E('sprites', 0, F, follow=True, texture='spark_soft', count=100000, rate=0.4, spread=0.3, speed=0.01, gravity=0.01,
              size=[0.1, 0.02], life=10, color='@primary', glow=0.8),
        ])
    fx('aris_blades_forge', 'Призыв клинков (фаза 2, событие cast анимации cast): caster = точка над Арис (+3 бл.), где куются клинки; '
       '3 вспышки-удара (молот невидим), на 20/26/32 тике код ставит клинки (3 шт., по кругу r2).', 40, [
        E('sigil', 0, at(F, 0, 0.0, 0), id='aris_emblem'),
        *[E('flash', t, at(F, 2 * math.cos(k * 2.09), 0, 2 * math.sin(k * 2.09)), duration=8, size=1.4, color='@core') for k, t in
          enumerate((20, 26, 32))],
        *[sparks(t, at(F, 2 * math.cos(k * 2.09), 0, 2 * math.sin(k * 2.09)), 26, 0.3, 14, 3) for k, t in enumerate((20, 26, 32))],
    ])
    fx('aris_blade_strike', 'Клинок бьёт игрока (caster = точка попадания): короткая вспышка, искры.', 12, [
        E('flash', 0, F, duration=6, size=1.0, color='@primary'), sparks(0, F, 20, 0.25, 10, 2, '@primary')])
    fx('aris_blade_shatter', 'Клинок сбит (caster = место): разлетается осколками стали и бирюзы.', 24, [
        E('flash', 0, F, duration=8, size=1.4, color=TEAL_HI),
        E('sprites', 0, F, duration=3, texture='mote_ash', count=24, rate=8, spread=0.4, speed=0.18, gravity=0.03, spin=120,
          size=[0.25, 0.1], life=22, color=STEEL_L, blend='translucent', comment='осколки стали'),
        sparks(0, F, 30, 0.3, 16, 3, '@primary')])
    fx('aris_phase2', 'Переход в фазу 2 «Оружейная» (66% ХП, анимация phase2: оборот и удар в 1.0 с): caster = Арис, follow.', 50, [
        E('aura', 0, F, duration=20, follow=True, target='caster', thickness=0.2, pulse=[0.3, 4], color='@primary', motes=24),
        E('vortex', 4, F, duration=16, radius=2.6, height=2.2, arms=3, speed=12, texture='spark_soft', color='@primary', out=ease(6),
          comment='оборот с молотом'),
        *impact(20, at(F, 0.05, 0, 1.2), r=14, big=1.3),                  # удар phase2 1.0: боёк ≈1.2 бл. впереди
        E('sigil', 20, at(F, 0, 0.04, 0), id='aris_emblem', follow=True),
    ])
    # ---------------------------------------------------------------- фаза 3 «Мифический сплав»
    fx('aris_phase3', 'Переход в фазу 3 «Мифический сплав» (33% ХП, анимация phase3, событие ignite 1.6 с): caster = Арис, follow. '
       '0–1.6 с — сжимается, жар нарастает (искры к ней); 1.6 с — вспышка, броня раскаляется добела (код: текстура → aris_mythic), волна.', 70, [
        E('vortex', 0, F, duration=32, radius=2.4, height=2.6, arms=4, speed=-8, flow=-1, texture='mote_flame', color='@secondary',
          out=ease(6), comment='жар стягивается к ней'),
        E('tint', 0, F, duration=70, radius=30, color='#3A1406', strength=0.3, **{'in': ease(24), 'out': ease(30)}),
        E('flash', 32, at(F, 0, 1.6, 0), duration=14, size=5.0, rays=12, screen=0.25, color='@core', ring=True),
        E('wave', 32, F, duration=26, shape='ring', radius=R_ARENA, thickness=2.2, followTerrain=True, texture='aris_molten_ring', color='@secondary'),
        sparks(32, at(F, 0, 1.2, 0), 90, 0.5, 24, 6),
    ])
    fx('aris_mythic_aura', 'Фаза 3: раскалённая броня (caster = Арис, follow, до Fx.stop): марево, капли металла, искры.', -1, [
        E('aura', 0, F, follow=True, target='caster', thickness=0.16, pulse=[0.2, 10], color='@secondary', motes=24, texture='mote_flame'),
        E('sprites', 0, at(F, 0, 1.2, 0), follow=True, texture='spark_soft', count=100000, rate=0.5, spread=0.7, speed=0.03, gravity=0.02,
          size=[0.12, 0.02], life=14, color='@core', glow=0.9),
        E('sprites', 0, at(F, 0, 0.6, 0), follow=True, texture='mote_flame', count=100000, rate=0.15, spread=0.5, speed=0.0, gravity=0.03,
          size=[0.2, 0.05], life=16, color='@secondary', comment='капли раскалённого металла'),
    ])
    fx('aris_reforge', 'Перековка (фаза 3): на игроке 10 с снижен урон оружия. caster = игрок, follow; метка над рукой с оружием, '
       'окалина сыплется с руки. Слать всем. 200 тиков.', 200, [
        E('sigil', 0, at('caster.hand', 0, 0.45, 0), follow=True, id='aris_reforge'),
        E('flash', 0, 'caster.hand', duration=8, size=1.0, color='@secondary'),
        E('sprites', 0, 'caster.hand', follow=True, duration=200, texture='mote_ash', count=100000, rate=0.3, spread=0.15, speed=0.0,
          gravity=0.02, spin=60, size=[0.1, 0.05], life=16, color=STEEL_D, blend='translucent', comment='окалина'),
    ])
    fx('aris_reforge_hit', 'Удар «перековки» по игроку (caster = игрок): кузнечный удар — вспышка и искры у оружия.', 14, [
        E('flash', 0, 'caster.hand', duration=8, size=1.2, color='@core'), sparks(0, 'caster.hand', 24, 0.25, 12, 2)])
    # ---------------------------------------------------------------- особые
    T_WARN_F, T_HOLD_F = 60, 200
    fx('aris_forge', 'Особое «Горн» (≈75% ХП, с роликом, бой не замораживается; анимация forge 4.0 с). caster = центр арены, не follow. '
       '0–60 тиков (3 с) — ПРЕДУПРЕЖДЕНИЕ: обод горна r24 прорисовывается, пол краснеет, островки отмечены (код ставит fx aris_island '
       'в 4–6 точках сразу на 0 тике); 60 — пол вспыхивает (событие ignite анимации — на 3.3 с ≈ 66 тиков, ставить fx за 0.3 с до); '
       '60–260 (10 с) — пол раскалён: урон кодом всем на земле вне островков r2.2; 260–300 — остывает. Всего 300.', T_WARN_F + T_HOLD_F + 40, [
        E('sigil', 0, at(F, 0, 0.05, 0), id='aris_forge'),
        E('tint', 0, F, duration=300, radius=R_ARENA + 4, color='#3A1004', strength=0.34, **{'in': ease(60, 'easeInSine'), 'out': ease(40)}),
        E('decal', 0, F, duration=300, texture='aris_molten_floor', radius=R_ARENA, grow=60, glow=0.3, fadeOut=40, color=MOLTEN_D,
          brightness=0.8, comment='предупреждение: трещины расползаются'),
        E('flash', T_WARN_F, at(F, 0, 1.0, 0), duration=16, size=7, rays=14, screen=0.2, color='@core', ring=True),
        E('wave', T_WARN_F, F, duration=24, shape='ring', radius=R_ARENA, thickness=2.6, followTerrain=True, texture='aris_molten_ring',
          color='@secondary'),
        E('decal', T_WARN_F, F, duration=T_HOLD_F + 40, texture='aris_molten_floor', radius=R_ARENA, glow=1.2, fadeOut=40, pulse=24,
          color='@secondary', brightness=1.4, comment='пол-горн раскалён'),
        E('curtain', T_WARN_F, F, duration=T_HOLD_F, radius=[1, R_ARENA], count=220, height=0.9, grow=10, width=[0.2, 0.5],
          brightness=[0.4, 0.8], flicker=0.7, texture='mote_flame', color='@secondary', out=ease(30), comment='низкие языки над полом'),
        E('sprites', T_WARN_F, at(F, 0, 0.2, 0), duration=T_HOLD_F, texture='spark_soft', count=100000, rate=3.0, area=R_ARENA, speed=0.02,
          gravity=-0.03, size=[0.14, 0.02], life=30, color='@core', glow=0.9, comment='искры поднимаются от пола'),
    ])
    fx('aris_island', 'Островок «Горна» (caster = точка, не follow): холодный камень r2.2 — печать aris_island, пар по кругу. 300 тиков.', 300, [
        E('sigil', 0, at(F, 0, 0.06, 0), id='aris_island'),
        E('sprites', 60, at(F, 0, 0.1, 0), duration=200, texture='mote_ash', count=100000, rate=0.4, area=2.2, speed=0.0, gravity=-0.01,
          size=[0.6, 0.2], life=30, color='#C8D8DC', blend='translucent', comment='пар'),
    ])
    fx('aris_forge_burn', 'Игрок на раскалённом полу «Горна» (caster = игрок): вспышка жара у ног.', 12, [
        E('flash', 0, at(F, 0, 0.2, 0), duration=6, size=1.0, color='@secondary'), sparks(0, at(F, 0, 0.2, 0), 12, 0.15, 10, 2)])
    T_LB_WARN, T_LB = 70, 80
    fx('aris_last_blow', 'Особое «Последний удар молота» (≈10% ХП, с роликом; анимация last_blow 5.0 с, событие blow 4.0 с). caster = центр '
       'арены, не follow. 0–70 тиков (3.5 с) — ПРЕДУПРЕЖДЕНИЕ: прицел r14 прорисовывается, клинья сходятся; над центром на высоте 20 '
       'проявляется исполинский призрачный молот (меш aris_giant_hammer, ×8). 70–80 — молот падает (move.keys 20 → 0 бл.). '
       '80 тиков (= blow) — УДАР: урон кодом всем в r14 (больше в центре), вспышка на экран, волна r30, кратер остывает 6 с.', 200, [
        E('sigil', 0, at(F, 0, 0.06, 0), id='aris_target'),
        E('tint', 0, F, duration=200, radius=34, color='#062A30', strength=0.3, **{'in': ease(40), 'out': ease(60)}),
        E('mesh', 0, at(F, 0, 0, 0), model='aris_giant_hammer', follow=False, until=T_LB + 14,
          move={'keys': [[0, [0, 20, 0], 'linear'], [T_LB_WARN, [0, 18, 0], 'easeOutSine'], [T_LB, [0, 0, 0], 'easeInCubic']]},
          comment='висит над центром, медленно опускается, на 70–80 рушится; collapse после until'),
        E('sprites', 20, at(F, 0, 18, 0), duration=50, texture='spark_soft', count=100000, rate=1.2, area=4, speed=0.0, gravity=0.04,
          size=[0.2, 0.03], life=30, color='@primary', glow=0.9, comment='искры осыпаются с молота'),
        E('flash', T_LB, at(F, 0, 1.0, 0), duration=18, size=10, rays=16, screen=0.45, color='@core', ring=True),
        *impact(T_LB, F, r=30, big=3.0),
        E('decal', T_LB, F, duration=120, texture='higher_cracks', radius=14, glow=1.0, fadeOut=80, color='@secondary', comment='кратер'),
        E('column', T_LB, F, duration=30, radius=3, height=14, fill=0.6, color='@primary', out=ease(20, 'easeInSine')),
    ])
    # ---------------------------------------------------------------- сдача
    fx('aris_surrender', 'Сдача (анимация surrender, 5 с; caster = Арис, не follow): 0.4 с — пошатнулась (искры); 1.2 с — молот в землю '
       '(пыль, трещины); 2.0–2.6 с — рога гаснут: бирюзовые искры поднимаются с рогов и тают; 3.2 с — молот падает (глухой удар, пыль); '
       '3.6 с — фраза. Жар и бирюза уходят из мира.', 100, [
        sparks(8, at(F, 0, 1.4, 0), 20, 0.2, 12, 3, '@primary'),
        E('decal', 24, at(F, 0.62, 0, 0.19), duration=76, texture='higher_cracks', radius=1.2, glow=0.2, fadeOut=40, color=STEEL),
        E('sprites', 24, at(F, 0.62, 0.1, 0.19), duration=5, texture='mote_ash', count=16, rate=4, spread=0.6, speed=0.05, gravity=-0.003,
          spin=40, size=[0.5, 0.15], life=26, color=STEEL, blend='translucent'),
        E('sprites', 40, at(F, 0, 2.6, 0), duration=14, texture='spark_soft', count=60, rate=5, spread=0.5, speed=0.03, gravity=-0.02,
          size=[0.14, 0.0], life=30, color='@primary', glow=0.9, comment='бирюза уходит с рогов'),
        E('sprites', 52, at(F, 0, 2.6, 0), duration=6, texture='mote_ash', count=10, rate=2, spread=0.4, speed=0.02, gravity=-0.01,
          size=[0.5, 0.2], life=30, color='#9AA8AC', blend='translucent', comment='дымок, рога погасли'),
        E('sprites', 64, at(F, 0.8, 0.2, 0.37), duration=5, texture='mote_ash', count=24, rate=6, spread=1.0, speed=0.06, gravity=-0.004,
          spin=40, size=[0.6, 0.2], life=30, color=STEEL, blend='translucent', comment='молот упал'),
        E('wave', 64, at(F, 0.8, 0, 0.37), duration=12, shape='ring', radius=2.5, thickness=0.4, followTerrain=True, color=STEEL_L),
        E('tint', 0, F, duration=100, radius=30, color='#0A1416', strength=0.18, **{'in': ease(40), 'out': ease(40)}),
    ])
    # ---------------------------------------------------------------- добивание (владелец 20.11; ТЗ T28 «Добивание»)
    HIT = at(F, -0.05, 0.3, 1.45)                 # низ бойка в момент slam: спина лежащей жертвы (таз — 1.9 бл. перед Арис)
    HORNS = [at(F, sx * 0.33, 2.82, 0.13) for sx in (-1, 1)]       # концы рогов в момент удара (она в приседе)
    fx('aris_finisher', 'Добивание (48 тиков = анимация animation.aris.finisher 2.4 с): caster = Арис (не follow, yaw — на жертву), '
       'target = жертва (её таз в holdPoint, 1.9 бл. перед Арис, голова к Арис; поза irons_spellbooks:pohsmp_aris_finisher_victim). 0–14 (pull) — '
       'жар и бирюзовые цепи тянут жертву и прижимают к земле; 14 (windup) — замах; 30 (slam) — молот бьёт в спину, как по заготовке '
       'на наковальне: вспышка, сноп искр, раскалённое пятно, рога и кайма вспыхивают; 30–44 — жар и окалина; 44 (kill) — смерть: '
       'последний сноп искр и пар.', 60, [
        E('tint', 0, F, duration=56, radius=12, color='#2A140C', strength=0.22, **{'in': ease(8), 'out': ease(12, 'easeInSine')}),
        E('aura', 0, 'target', duration=30, target='target', follow=True, thickness=0.16, pulse=[0.3, 5], color='@primary', motes=14,
          comment='бирюзовая хватка: жертву тянет и прижимает'),
        E('decal', 0, at(F, 0, 0.02, 1.6), duration=58, texture='aris_molten_floor', radius=1.2, grow=14, glow=0.9, fadeOut=14,
          color='@secondary', brightness=1.0, comment='«наковальня»: земля под жертвой раскаляется'),
        E('sprites', 2, at(F, -0.3, 1.5, 0.4), duration=12, texture='spark_soft', count=24, rate=2, spread=0.2, speed=0.12, gravity=0.0,
          size=[0.1, 0.02], life=10, color='@primary', glow=0.9, comment='с левой ладони к жертве'),
        E('sprites', 14, at(F, 0.45, 2.3, -0.2), duration=14, texture='spark_soft', count=20, rate=2, spread=0.4, speed=0.03, gravity=0.02,
          size=[0.14, 0.02], life=16, color='@secondary', glow=0.9, comment='windup: искры с поднятого молота'),
        # slam
        E('flash', 30, HIT, duration=10, size=3.2, rays=12, screen=0.06, color='@core', ring=True),
        E('wave', 30, at(F, 0, 0, 1.5), duration=14, shape='ring', radius=3.2, thickness=0.8, followTerrain=True, texture='aris_molten_ring',
          color='@secondary', comment='короткое кольцо жара (без урона)'),
        E('sprites', 30, HIT, duration=4, texture='spark_soft', count=110, rate=28, spread=0.5, speed=0.5, gravity=0.035, size=[0.18, 0.02],
          life=22, color='@secondary', glow=1.0, comment='сноп искр, как из-под молота на наковальне'),
        E('sprites', 30, HIT, duration=3, texture='spark_soft', count=40, rate=14, spread=0.3, speed=0.3, gravity=0.03, size=[0.12, 0.02],
          life=14, color='@core', glow=1.0),
        E('column', 30, at(F, 0, 0, 1.5), duration=10, radius=0.9, height=1.6, fill=0.3, color='@secondary', out=ease(8),
          comment='выброс жара'),
        *[E('flash', 30, h, duration=12, size=0.9, rays=6, color='@primary', brightness=1.3, comment='рога вспыхивают') for h in HORNS],
        E('aura', 30, F, duration=16, follow=True, target='caster', thickness=0.2, pulse=[0.5, 4], color='@primary', motes=24,
          comment='рога и кайма брони вспыхивают на ударе'),
        # жар на жертве, окалина
        E('sprites', 32, at(F, 0, 0.3, 1.55), duration=12, texture='mote_flame', count=36, rate=3, spread=0.5, speed=0.03, gravity=-0.02,
          size=[0.45, 0.05], life=20, color='@secondary', glow=0.7, comment='жар поднимается со спины'),
        E('sprites', 32, at(F, 0, 0.2, 1.55), duration=10, texture='mote_ash', count=16, rate=2, spread=0.6, speed=0.04, gravity=-0.004,
          spin=40, size=[0.5, 0.15], life=26, color=STEEL, blend='translucent', comment='окалина'),
        # kill
        E('flash', 44, HIT, duration=8, size=1.8, rays=8, color='@secondary'),
        E('sprites', 44, HIT, duration=3, texture='spark_soft', count=50, rate=18, spread=0.5, speed=0.3, gravity=0.03, size=[0.14, 0.02],
          life=16, color='@secondary', glow=0.9),
        E('sprites', 44, at(F, 0, 0.3, 1.55), duration=8, texture='mote_ash', count=24, rate=3, spread=0.5, speed=0.03, gravity=-0.01,
          size=[0.6, 0.2], life=34, color='#9AA8AC', blend='translucent', comment='пар/дым'),
    ])


# ================================================================== полоса здоровья (192×36, формат tyros_bossbar: 0–17 пустая, 18–35 полная)
def _bar(phase):
    """Своя полоса: стальная рамка с заклёпками, бирюзовая заливка; по центру — знак (наковальня под рогами).
    phase 1 — бирюза; 2 — бирюза + клинки по краям; 3 — заливка раскалена (бело-оранжевая), рамка с трещинами."""
    W, H = 192, 18
    img = Image.new('RGBA', (W, 36), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fill_cols = {1: ('#22B4C4', '#3CD6E0', '#7EEEF2', '#0F6470'), 2: ('#22B4C4', '#3CD6E0', '#7EEEF2', '#0F6470'),
                 3: ('#D87A34', '#F4A852', '#FFD490', '#A8502A')}[phase]
    for half in (0, 18):
        y0 = half
        # рамка
        d.rectangle([2, y0 + 6, W - 3, y0 + 13], fill=hx('#1C1C22'))
        d.rectangle([3, y0 + 7, W - 4, y0 + 12], fill=hx('#0E0E12'))
        d.line([2, y0 + 6, W - 3, y0 + 6], fill=hx('#8E8E9A'))
        d.line([2, y0 + 13, W - 3, y0 + 13], fill=hx('#2A2A32'))
        for x in range(10, W - 10, 16):                                       # заклёпки
            d.point((x, y0 + 6), fill=hx('#C6C6CE'))
            d.point((x, y0 + 13), fill=hx('#60606C'))
        # концы рамки — клинья
        for sx_, x in ((1, 0), (-1, W - 1)):
            for k in range(4):
                d.line([x + sx_ * k, y0 + 9 - k + 1, x + sx_ * k, y0 + 10 + k - 1], fill=hx('#4C4C57'))
        if half == 18:                                                        # заливка (полная)
            c0, c1, c2, c3 = (hx(c) for c in fill_cols)
            d.rectangle([3, y0 + 7, W - 4, y0 + 12], fill=c0)
            d.line([3, y0 + 7, W - 4, y0 + 7], fill=c2)
            d.line([3, y0 + 8, W - 4, y0 + 8], fill=c1)
            d.line([3, y0 + 12, W - 4, y0 + 12], fill=c3)
            for x in range(6, W - 6, 6):                                      # насечки «кованого» металла
                d.point((x, y0 + 10), fill=c1)
        else:
            d.line([3, y0 + 12, W - 4, y0 + 12], fill=hx('#16161B'))
        # центральный знак: наковальня под рогами
        cx = W // 2
        d.rectangle([cx - 9, y0 + 3, cx + 9, y0 + 16], fill=hx('#1C1C22'))
        d.rectangle([cx - 8, y0 + 4, cx + 8, y0 + 15], fill=hx('#4C4C57'))
        d.line([cx - 8, y0 + 4, cx + 8, y0 + 4], fill=hx('#A9A9B4'))
        d.rectangle([cx - 5, y0 + 10, cx + 5, y0 + 11], fill=hx('#C6C6CE'))     # наковальня
        d.rectangle([cx - 2, y0 + 12, cx + 2, y0 + 13], fill=hx('#8E8E9A'))
        d.rectangle([cx - 4, y0 + 14, cx + 4, y0 + 14], fill=hx('#8E8E9A'))
        d.point((cx - 6, y0 + 10), fill=hx('#C6C6CE'))
        hc = '#3CD6E0' if phase < 3 else '#FFD490'
        for sx_ in (-1, 1):                                                   # рога
            for k, (dx, dy) in enumerate(((2, 8), (3, 7), (4, 6), (4, 5), (4, 4), (3, 3))):
                d.point((cx + sx_ * dx, y0 + dy), fill=hx(hc if k > 1 else '#8E8E9A'))
        if phase >= 2:                                                        # клинки по краям рамки
            for sx_, x0 in ((1, 14), (-1, W - 15)):
                for k in range(14):
                    d.point((x0 + sx_ * k, y0 + 4), fill=hx('#A9A9B4' if k < 11 else '#E8FFFE'))
                    d.point((x0 + sx_ * k, y0 + 15), fill=hx('#A9A9B4' if k < 11 else '#E8FFFE'))
                d.line([x0, y0 + 3, x0, y0 + 5], fill=hx('#3CD6E0'))
                d.line([x0, y0 + 14, x0, y0 + 16], fill=hx('#3CD6E0'))
        if phase == 3:                                                        # трещины с раскалёнными краями
            rng = random.Random(3 + half)
            for k in range(9):
                x = rng.randint(12, W - 12)
                if abs(x - cx) < 12:
                    continue
                d.line([x, y0 + 6, x + rng.choice((-1, 1)), y0 + 9], fill=hx('#FFD490'))
                d.point((x, y0 + 6), fill=hx('#FFF6E2'))
    return img


def bossbars():
    paths = {}
    for ph, nm in ((1, 'aris_bossbar'), (2, 'aris_bossbar_p2'), (3, 'aris_bossbar_p3')):
        im = _bar(ph)
        im.save(G.out('textures/gui/sprites/boss_bars/%s.png' % nm))
        paths[ph] = im
    # фаза 3: 8 кадров жара над рамкой (192×14 каждый), как языки у T26
    fr = Image.new('RGBA', (192, 112), (0, 0, 0, 0))
    d = ImageDraw.Draw(fr)
    rng = random.Random(28)
    xs = [rng.randint(6, 186) for _ in range(26)]
    for k in range(8):
        for i, x in enumerate(xs):
            h = 3 + int(4 * (0.5 + 0.5 * math.sin(k / 8 * 2 * math.pi + i * 1.7)))
            for t in range(h):
                c = ('#FFF6E2', '#FFD490', '#F4A852', '#D87A34', '#A8502A')[min(4, t * 5 // max(1, h))]
                d.point((x, 14 * k + 13 - t), fill=hx(c, 230 - t * 25))
                if t < h - 2 and i % 2:
                    d.point((x + 1, 14 * k + 13 - t), fill=hx(c, 200 - t * 25))
    fr.save(G.out('textures/gui/sprites/boss_bars/aris_bossbar_p3_heat.png'))
    # вспышка смены фазы: силуэт полосы светлой бирюзой
    a = np.asarray(paths[1])[:18, :, 3] > 0
    fl = np.zeros((18, 192, 4), np.uint8)
    fl[a] = hx('#C8FBFC')
    Image.fromarray(fl, 'RGBA').save(G.out('textures/gui/sprites/boss_bars/aris_bossbar_flash.png'))
    return paths


# ================================================================== титры (1024×192, две строки)
def _font(name, sz):
    return ImageFont.truetype(os.path.join(HERE, 'fonts', name), sz)


LAT, CYR = 'CormorantGaramond-BoldItalic-latin.woff', 'CormorantGaramond-BoldItalic-cyrillic.woff'


class MixFont:
    """Cormorant разбит на два файла: кириллица (без цифр и знаков) и латиница. Текст набирается кусками: кириллица — из
    cyrillic, остальное (цифры, запятые, точки, кавычки, латиница) — из latin."""

    def __init__(self, sz):
        self.c, self.l = _font(CYR, sz), _font(LAT, sz)

    def runs(self, text):
        out = []
        for ch in text:
            f = self.c if ('\u0400' <= ch <= '\u04ff') else self.l
            if out and out[-1][0] is f:
                out[-1][1] += ch
            else:
                out.append([f, ch])
        return out

    def getbbox(self, text):
        w = sum(f.getlength(t) for f, t in self.runs(text))
        b = self.l.getbbox('ÁgМ')
        bc = self.c.getbbox('Мд')
        return (0, min(b[1], bc[1]), int(w), max(b[3], bc[3]))

    def draw(self, d, xy, text, fill):
        x, y = xy
        for f, t in self.runs(text):
            d.text((x, y), t, font=f, fill=fill)
            x += f.getlength(t)


def title_img(line1, f1, line2=None, f2=None, hot=False):
    S = 2
    Wd, Hd = 1024 * S, 192 * S
    big = MixFont((70 if line2 else 84) * S)
    mask = Image.new('L', (Wd, Hd), 0)
    dm = ImageDraw.Draw(mask)
    bb = big.getbbox(line1)
    ty = (8 if line2 else 20) * S
    big.draw(dm, ((Wd - (bb[2] - bb[0])) / 2 - bb[0], ty - bb[1] + (80 * S - (bb[3] - bb[1])) / 2), line1, 255)
    if line2:
        sm = MixFont(40 * S)
        b2 = sm.getbbox(line2)
        sm.draw(dm, ((Wd - (b2[2] - b2[0])) / 2 - b2[0], 98 * S - b2[1]), line2, 255)
    m = np.asarray(mask, np.float32) / 255
    yy = np.linspace(0, 1, Hd)[:, None, None]
    top = np.array(hx('#E8FFFE')[:3], np.float32) if not hot else np.array(hx('#FFF6E2')[:3], np.float32)
    mid = np.array(hx('#7EEEF2')[:3], np.float32) if not hot else np.array(hx('#F4A852')[:3], np.float32)
    bot = np.array(hx('#A9A9B4')[:3], np.float32)
    k = np.clip(yy * 1.6, 0, 1)
    grad = np.where(k < 0.5, top + (mid - top) * (k / 0.5), mid + (bot - mid) * ((k - 0.5) / 0.5))
    rgb = np.broadcast_to(grad, (Hd, Wd, 3))
    outline = np.asarray(mask.filter(ImageFilter.MaxFilter(9)), np.float32) / 255
    halo = np.asarray(mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(20 * S)), np.float32) / 255
    o = np.zeros((Hd, Wd, 4), np.float32)
    hc = np.array(hx('#168E9E' if not hot else '#A8502A')[:3], np.float32)
    o[..., :3] = hc
    o[..., 3] = np.clip(halo * 1.3, 0, 0.7)
    ob = np.array(hx('#0E0E12')[:3], np.float32)
    o[..., :3] = o[..., :3] * (1 - outline[..., None]) + ob * outline[..., None]
    o[..., 3] = np.maximum(o[..., 3], outline)
    o[..., :3] = o[..., :3] * (1 - m[..., None]) + rgb * m[..., None]
    o[..., 3] = np.maximum(o[..., 3], m)
    o[..., 3] *= 255
    img = Image.fromarray(o.clip(0, 255).astype(np.uint8), 'RGBA').resize((1024, 192), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    y = 172 if line2 else 156                                         # кованая полоса под надписью: сталь + бирюзовая жила
    for x in range(160, 864):
        a_ = int(255 * min(1, (1 - abs(x - 512) / 352) * 2.2))
        d.point((x, y - 1), fill=hx('#0E0E12', int(a_ * 0.8)))
        d.point((x, y), fill=hx('#A9A9B4', a_))
        d.point((x, y + 1), fill=hx('#3CD6E0' if not hot else '#F4A852', a_))
        d.point((x, y + 2), fill=hx('#0E0E12', int(a_ * 0.8)))
    return img


def titles():
    out = {}
    for lang, l1, f1, l2, f2 in (('ru', 'Арис, Мифический Кузнец', CYR, 'Глава 3 Ячейки Культа', CYR),
                                 ('en', 'Aris, the Mythic Smith', LAT, "Head of the Cult's Third Cell", LAT)):
        im = title_img(l1, f1, l2, f2)
        im.save(G.out('textures/gui/title/aris_%s.png' % lang))
        out['aris_' + lang] = im
    for nm, ru, en, hot in (('aris_forge', 'Горн', 'The Forge', True), ('aris_last_blow', 'Последний удар молота', 'The Final Hammerfall', False)):
        for lang, txt, fnt in (('ru', ru, CYR), ('en', en, LAT)):
            im = title_img(txt, fnt, hot=hot)
            im.save(G.out('textures/gui/title/%s_%s.png' % (nm, lang)))
            out['%s_%s' % (nm, lang)] = im
    return out


# ================================================================== иконки статусов (18×18, пиксель-арт)
def icon(name, draw):
    k = 8
    im = Image.new('RGBA', (18 * k, 18 * k), (0, 0, 0, 0))
    draw(ImageDraw.Draw(im), 18 * k)
    im = im.resize((18, 18), Image.NEAREST)
    a = np.asarray(im).copy()
    a[..., 3] = np.where(a[..., 3] > 100, 255, 0)
    Image.fromarray(a, 'RGBA').save(G.out('textures/mob_effect/%s.png' % name))
    return Image.fromarray(a, 'RGBA')


def icons():
    def reforged(d, S):
        d.ellipse([S * .05, S * .05, S * .95, S * .95], fill=hx('#1C1C22'), outline=hx('#A8502A'), width=int(S * .08))
        d.polygon([(S * .44, S * .8), (S * .56, S * .8), (S * .56, S * .35), (S * .5, S * .2), (S * .44, S * .35)], fill=hx('#A9A9B4'))
        d.rectangle([S * .32, S * .62, S * .68, S * .68], fill=hx('#60606C'))
        for i, y in enumerate((.32, .44, .54)):
            d.line([S * .42, S * y, S * .58, S * (y + .05)], fill=hx('#F4A852'), width=int(S * .06))
        d.polygon(hammer_poly(S * .68, S * .3, S * .3, 0.7), fill=hx('#3CD6E0'))
    icons_ = {'aris_reforged': icon('aris_reforged', reforged)}

    def scorched(d, S):
        d.ellipse([S * .05, S * .05, S * .95, S * .95], fill=hx('#2A1006'), outline=hx('#D87A34'), width=int(S * .08))
        for k in range(5):
            x = S * (.25 + .12 * k)
            h = S * (.28 + .1 * (k % 2))
            d.polygon([(x - S * .06, S * .72), (x + S * .06, S * .72), (x, S * .72 - h)], fill=hx('#F4A852'))
            d.polygon([(x - S * .03, S * .72), (x + S * .03, S * .72), (x, S * .72 - h * .55)], fill=hx('#FFF6E2'))
        d.rectangle([S * .2, S * .72, S * .8, S * .78], fill=hx('#FFD490'))
    icons_['aris_scorched'] = icon('aris_scorched', scorched)
    return icons_


# ================================================================== lang и звуки
LANG = {
    'entity.pohsmp_core.aris': ('Арис, Мифический Кузнец', 'Aris, the Mythic Smith'),
    'entity.pohsmp_core.aris_npc': ('Арис', 'Aris'),
    'entity.pohsmp_core.aris_anvil': ('Раскалённая наковальня', 'Red-hot Anvil'),
    'entity.pohsmp_core.aris_blade': ('Клинок ковки Арис', 'Blade of Aris\'s Forge'),
    'item.pohsmp_core.aris_hammer': ('Молот Арис', 'Hammer of Aris'),
    'ui.pohsmp_core.aris.title': ('Арис, Мифический Кузнец', 'Aris, the Mythic Smith'),
    'ui.pohsmp_core.aris.epithet': ('Глава 3 Ячейки Культа', 'Head of the Cult\'s Third Cell'),
    'ui.pohsmp_core.aris.subtitle': ('Глава 3 Ячейки Культа', 'Head of the Cult\'s Third Cell'),
    'ui.pohsmp_core.aris.phase1': ('«Ковка»: металл кипит под её молотом', '"Forging": metal boils beneath her hammer'),
    'ui.pohsmp_core.aris.phase2': ('«Оружейная»: Арис выковывает клинки', '"The Armory": Aris forges her blades'),
    'ui.pohsmp_core.aris.phase3': ('«Мифический сплав»: броня Арис раскалена добела', '"Mythic Alloy": Aris\'s armor glows white-hot'),
    'ui.pohsmp_core.aris.anvil': ('Из земли вырастают наковальни', 'Anvils rise from the ground'),
    'ui.pohsmp_core.aris.blades': ('Клинки её ковки кружат над ареной', 'Blades of her forge circle the arena'),
    'ui.pohsmp_core.aris.reforge': ('Перековка! Ваше оружие ослаблено (%s с)', 'Reforged! Your weapon is weakened (%ss)'),
    'ui.pohsmp_core.aris.forge_warn': ('Арена становится горном — ищите холодный камень!', 'The arena becomes a forge — find the cold stone!'),
    'ui.pohsmp_core.aris.forge': ('Горн', 'The Forge'),
    'ui.pohsmp_core.aris.forge_end': ('Горн остывает', 'The forge cools'),
    'ui.pohsmp_core.aris.last_blow_warn': ('Арис заносит молот для последнего удара…', 'Aris raises her hammer for the final blow…'),
    'ui.pohsmp_core.aris.last_blow': ('Последний удар молота', 'The Final Hammerfall'),
    'ui.pohsmp_core.aris.surrender': ('Чёрт! Я сдаюсь, прекращайте...я помогу вам..', 'Damn it! I give up, stop it... I\'ll help you..'),
    'ui.pohsmp_core.aris.surrendered': ('Арис сдалась', 'Aris has surrendered'),
    'effect.pohsmp_core.aris_reforged': ('Перековка', 'Reforged'),
    'effect.pohsmp_core.aris_reforged.description': ('Арис перековала ваше оружие: урон снижен, пока действует эффект.',
                                                     'Aris has reforged your weapon: its damage is reduced while the effect lasts.'),
    'effect.pohsmp_core.aris_scorched': ('Раскалённый пол', 'Scorched'),
    'effect.pohsmp_core.aris_scorched.description': ('Пол-горн обжигает: стойте на холодном камне.', 'The forge floor burns: stand on the cold stone.'),
    'subtitles.pohsmp_core.aris.spawn': ('Арис поднимается из расплава', 'Aris rises from molten metal'),
    'subtitles.pohsmp_core.aris.slam': ('Удар молота о землю', 'Hammer strikes the ground'),
    'subtitles.pohsmp_core.aris.swing': ('Молот рассекает воздух', 'Hammer whooshes'),
    'subtitles.pohsmp_core.aris.anvil': ('Вырастает наковальня', 'Anvil rises'),
    'subtitles.pohsmp_core.aris.blade': ('Клинок выкован', 'Blade forged'),
    'subtitles.pohsmp_core.aris.blade_break': ('Клинок разбит', 'Blade shatters'),
    'subtitles.pohsmp_core.aris.forge': ('Ревёт горн', 'The forge roars'),
    'subtitles.pohsmp_core.aris.last_blow': ('Последний удар молота', 'The Final Hammerfall'),
    'subtitles.pohsmp_core.aris.phase': ('Арис ярится', 'Aris rages'),
    'subtitles.pohsmp_core.aris.reforge': ('Перековка', 'Reforge'),
    'subtitles.pohsmp_core.aris.surrender': ('Арис сдаётся', 'Aris surrenders'),
    'subtitles.pohsmp_core.aris.hammer_drop': ('Молот падает', 'Hammer falls'),
    'subtitles.pohsmp_core.music.aris': ('Музыка: Арис', 'Music: Aris'),
}


def S_(name, **kw):
    o = {'name': name}
    o.update(kw)
    return o


SOUNDS = {
    'aris.spawn': [S_('minecraft:block/anvil/land', pitch=0.5, volume=1.4), S_('minecraft:block/lava/pop', pitch=0.6)],
    'aris.slam': [S_('minecraft:block/anvil/land', pitch=0.6, volume=1.2), S_('minecraft:block/anvil/land', pitch=0.7, volume=1.2)],
    'aris.swing': [S_('minecraft:entity/player/attack/sweep1', pitch=0.6), S_('minecraft:entity/player/attack/sweep2', pitch=0.55)],
    'aris.anvil': [S_('minecraft:block/anvil/place', pitch=0.7), S_('minecraft:block/anvil/place', pitch=0.8)],
    'aris.blade': [S_('minecraft:block/anvil/use', pitch=1.3), S_('minecraft:block/smithing_table/smithing_table1', pitch=1.1)],
    'aris.blade_break': [S_('minecraft:random/break', pitch=0.8), S_('minecraft:block/anvil/break', pitch=1.2)],
    'aris.forge': [S_('minecraft:block/fire/ignite', pitch=0.5, volume=1.4), S_('minecraft:item/firecharge/use', pitch=0.6)],
    'aris.last_blow': [S_('minecraft:block/anvil/land', pitch=0.4, volume=2.0)],
    'aris.phase': [S_('minecraft:block/anvil/use', pitch=0.6, volume=1.3)],
    'aris.reforge': [S_('minecraft:block/smithing_table/smithing_table2', pitch=0.7), S_('minecraft:block/anvil/use', pitch=0.9)],
    'aris.surrender': [S_('minecraft:block/anvil/destroy', pitch=0.7)],
    'aris.hammer_drop': [S_('minecraft:block/anvil/fall', pitch=0.6, volume=1.3)],
}


def lang_sounds():
    for i, name in enumerate(('ru_ru', 'en_us')):
        p = os.path.join(G.A, 'lang', name + '.json')
        d = json.load(open(p, encoding='utf-8'))
        for k, v in LANG.items():
            d[k] = v[i]
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')
        G.WRITTEN.append('lang/%s.json (+%d ключей)' % (name, len(LANG)))
    p = os.path.join(G.A, 'sounds.json')
    d = json.load(open(p, encoding='utf-8'))
    for k, v in SOUNDS.items():
        d[k] = {'subtitle': 'subtitles.pohsmp_core.' + k, 'sounds': v}
    d['music.aris'] = {'category': 'record', 'subtitle': 'subtitles.pohsmp_core.music.aris',
                       'comment': 'ЗАГЛУШКА до трека владельца (тишина-тон наковальни). Трек — pohsmp_core:music/aris (stream).',
                       'sounds': [S_('minecraft:music/game/creative/creative1', stream=True, volume=0.4, pitch=0.8)]}
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write('\n')


# ================================================================== +4 заклинания (владелец 20.11): заготовка, цепи, закалка, мехи
def tex_cone():
    """Конус-предупреждение «Мехов» (decal): клин 60° — вершина в центре картинки, раскрывается к верхнему краю (= вперёд по yaw);
    кромки ярче, внутри — штриховка-«потоки» к вершине."""
    n = 512
    im, d, c = canvas(n)
    W = n * S4
    half = math.radians(30)
    apex = (c, c)
    R = c * 0.98
    pts = [apex] + [(c + R * math.sin(a), c - R * math.cos(a)) for a in np.linspace(-half, half, 40)]
    d.polygon(pts, fill=70)
    d.line([apex, pts[1]], fill=255, width=16)
    d.line([apex, pts[-1]], fill=255, width=16)
    d.line(pts[1:], fill=255, width=16)
    for k in range(1, 6):
        r = R * k / 6
        arc = [(c + r * math.sin(a), c - r * math.cos(a)) for a in np.linspace(-half, half, 24)]
        d.line(arc, fill=170, width=8)
    save_sigil(im, 'aris_cone')


def tex_chain_seal():
    """Печать «Цепей кузни» под скованным: кольцо из звеньев и четыре скобы-якоря."""
    im, d, c = canvas(256)
    for k in range(20):
        a = 2 * math.pi * k / 20
        x, y = c + c * 0.8 * math.cos(a), c + c * 0.8 * math.sin(a)
        r1, r2 = c * 0.11, c * 0.06
        if k % 2:
            d.ellipse([x - r1, y - r2, x + r1, y + r2], outline=255, width=14)
        else:
            d.ellipse([x - r2, y - r1, x + r2, y + r1], outline=255, width=14)
    for k in range(4):
        a = 2 * math.pi * k / 4 + math.pi / 4
        x, y = c + c * 0.45 * math.cos(a), c + c * 0.45 * math.sin(a)
        d.rectangle([x - c * 0.08, y - c * 0.08, x + c * 0.08, y + c * 0.08], outline=255, width=14)
    save_sigil(im, 'aris_chain_seal', 256)


def mesh_billet():
    """Раскалённый слиток-заготовка 0.6×0.22×0.3 бл.: тело светится (бело-жёлтая сердцевина, оранжевые грани), окалина-пятна."""
    b = [bx(-0.3, 0, -0.15, 0.3, 0.2, 0.15, 1), bx(-0.27, 0.2, -0.12, 0.27, 0.23, 0.12, 2)]
    sc = [bx(-0.18, 0.229, -0.05, -0.08, 0.235, 0.04, 0), bx(0.1, 0.229, 0.02, 0.2, 0.235, 0.1, 0), bx(-0.31, 0.05, -0.08, -0.299, 0.12, 0.0, 0)]
    tones = ['#3A2420', MOLTEN, MOLTEN_HI]
    mesh('aris_billet', 'T28 «Раскалённая заготовка»: слиток 0.6×0.22×0.3 бл., светится; окалина тёмными пятнами. Точка (0,0,0) — низ.',
         [{'type': 'boxes', 'tones': tones, 'glowTones': [1, 2], 'blend': 'additive', 'opacity': 1.0, 'shade': True, 'boxes': b,
           'appear': {'delay': 0, 'duration': 4, 'easing': 'easeOutCubic', 'reveal': 'down', 'front': 0.1}, 'bounds': [0, 0.25]},
          {'type': 'boxes', 'tones': tones, 'glowTones': [], 'blend': 'translucent', 'opacity': 1.0, 'shade': True, 'boxes': sc,
           'appear': {'delay': 0, 'duration': 4, 'easing': 'easeOutCubic', 'reveal': 'down', 'front': 0.1}, 'bounds': [0, 0.25]}],
         formed=4, collapse=4)


def spells4():
    tex_cone()
    tex_chain_seal()
    mesh_billet()
    F = 'caster'

    def sparks(t, p, n=20, spd=0.3, life=14, dur=3, col='@secondary'):
        return E('sprites', t, p, duration=dur, texture='spark_soft', count=n, rate=max(1, n // dur), spread=0.5, speed=spd, gravity=0.03,
                 size=[0.14, 0.02], life=life, color=col, glow=0.9)
    # ---------------------------------------------------------------- 1. Раскалённая заготовка
    # FX audit 21.11: was 'caster.hand' — the code plays it without a caster (at + yaw), so the hand fell back to base+1.6, 0.45 lower
    # and to the right of where the billet leaves (ArisFight: boss + 1.6 up + 0.5 forward). The anchor is now that very point.
    THROW = 'caster+0,1.6,0.5'
    fx('aris_billet_throw', '«Раскалённая заготовка», бросок (событие throw 0.7 с анимации billet): at = Арис + yaw. '
       'Вспышка и искры там, откуда вылетает слиток (+1.6 вверх, 0.5 вперёд, как в ArisFight); сам слиток в полёте — меш aris_billet.', 12, [
        E('flash', 0, THROW, duration=6, size=0.9, color='@secondary'), sparks(0, THROW, 14, 0.2, 10, 2)])
    pulse = []
    for t in (0, 20, 36, 46, 52, 56, 58):                                  # пульс жара учащается к взрыву (3 с = 60 тиков)
        pulse.append(E('wave', t, F, duration=10, shape='ring', radius=3, thickness=0.35, followTerrain=True, color='@secondary',
                       brightness=0.5 + t / 100))
    fx('aris_billet', '«Раскалённая заготовка» лежит (caster = слиток, follow, 60 тиков): меш слитка, жаркий круг r3 на земле '
       '(ВИДНО зону взрыва), пульс-кольца r3 учащаются (0/20/36/46/52/56/58), марево и искры. На 60 тике код взрывает: '
       'урон r3 + fx aris_billet_explode.', 60, [
        E('mesh', 0, F, model='aris_billet', follow=True),
        E('decal', 0, F, duration=60, texture='glow', radius=3, follow=True, glow=0.6, pulse=10, color='@secondary', brightness=0.6,
          comment='зона r3'),
        E('decal', 0, F, duration=60, texture='aris_molten_floor', radius=1.2, follow=True, glow=1.0, color='@secondary', grow=40),
        *pulse,
        E('sprites', 0, at(F, 0, 0.25, 0), follow=True, duration=60, texture='spark_soft', count=100000, rate=0.5, spread=0.2, speed=0.03,
          gravity=0.02, size=[0.1, 0.02], life=12, color='@core', glow=0.9),
        E('sprites', 0, at(F, 0, 0.3, 0), follow=True, duration=60, texture='mote_ash', count=100000, rate=0.2, spread=0.2, speed=0.0,
          gravity=-0.01, size=[0.4, 0.15], life=24, color='#5A4A44', blend='translucent', comment='дымок'),
    ])
    fx('aris_billet_explode', 'Слиток взрывается (caster = место): вспышка, огненный шар r3, брызги металла, обожжённое пятно.', 40, [
        E('flash', 0, at(F, 0, 0.5, 0), duration=12, size=3.4, rays=10, screen=0.08, color='@core', ring=True),
        E('wave', 0, F, duration=10, shape='sphere', radius=3, thickness=0.6, color='@secondary'),
        E('wave', 0, F, duration=14, shape='ring', radius=3.5, thickness=0.8, followTerrain=True, texture='aris_molten_ring', color='@secondary'),
        E('sprites', 0, at(F, 0, 0.4, 0), duration=4, texture='mote_flame', count=50, rate=14, spread=1.2, speed=0.3, gravity=0.03,
          size=[0.4, 0.05], life=18, color='@secondary', glow=0.8, comment='брызги металла'),
        sparks(0, at(F, 0, 0.4, 0), 50, 0.5, 18, 4),
        E('decal', 0, F, duration=40, texture='aris_molten_floor', radius=2.2, glow=0.7, fadeOut=30, color='@secondary'),
    ])
    # ---------------------------------------------------------------- 2. Цепи кузни
    anchors = [(1.6, 0.0), (-1.6, 0.0), (0.0, 1.6), (0.0, -1.6)]
    ch = []
    for i, (x, z) in enumerate(anchors):
        ch.append(E('chains', 2 + i, at(F, x, 0.05, z), to='caster+0,0.8,0', follow=True, link=0.2, sag=0.15, tension=0.85, grow=6,
                    rattle=0.04, color=STEEL_L, comment='цепь из земли к поясу скованного'))
        ch.append(E('decal', i, at(F, x, 0, z), texture='higher_cracks', radius=0.8, glow=0.6, color='@secondary', fadeOut=10))
        ch.append(E('sprites', 2 + i, at(F, x, 0.1, z), duration=4, texture='mote_ash', count=8, rate=2, spread=0.3, speed=0.05, gravity=-0.003,
                    spin=40, size=[0.4, 0.1], life=18, color=STEEL, blend='translucent'))
    fx('aris_chains', '«Цепи кузни» на игроке (caster = скованный, follow; до Fx.stop: 4 с = 80 тиков или 3 удара союзников). '
       'Четыре цепи вырываются из земли в 1.6 бл. вокруг и тянутся к поясу; печать звеньев под ногами; звенья с раскалёнными '
       'стыками. Удар союзника по цепям — fx aris_chains_hit; разбиты/время вышло — Fx.stop + aris_chains_break.', -1, [
        E('sigil', 0, at(F, 0, 0.05, 0), id='aris_chain_seal'), *ch,
        E('aura', 4, F, follow=True, target='caster', thickness=0.1, pulse=[0.2, 8], color=STEEL_L, motes=8, comment='скован'),
    ])
    fx('aris_chains_hit', 'Удар союзника по цепям (caster = скованный): лязг — искры и вспышка у пояса; код считает 3 удара.', 10, [
        E('flash', 0, at(F, 0, 0.8, 0), duration=5, size=0.9, color=STEEL_L), sparks(0, at(F, 0, 0.8, 0), 16, 0.3, 10, 2, '@core')])
    fx('aris_chains_break', 'Цепи разбиты / время вышло (caster = освобождённый): звенья разлетаются и тают, печать гаснет.', 24, [
        E('flash', 0, at(F, 0, 0.8, 0), duration=8, size=1.6, color=STEEL_L, ring=True),
        E('sprites', 0, at(F, 0, 0.6, 0), duration=3, texture='mote_ash', count=30, rate=10, spread=1.0, speed=0.2, gravity=0.04, spin=120,
          size=[0.22, 0.1], life=20, color=STEEL_L, blend='translucent', comment='звенья'),
        sparks(0, at(F, 0, 0.6, 0), 24, 0.35, 14, 3)])
    # ---------------------------------------------------------------- 3. Закалка
    fx('aris_quench', '«Закалка» (событие splash 0.8 с анимации quench; caster = Арис, НЕ follow — облако стоит на месте, 100 тиков = 5 с): '
       'всплеск воды над ней, шипение — пар клубами r5; мир в облаке серый (tint saturation). Код: урон по Арис ×0.6, пока она в r5; '
       'у игроков в облаке — туман (эффект aris_steamed / FogRenderer).', 100, [
        E('sprites', 0, at(F, 0, 2.8, 0), duration=4, texture='glow', count=24, rate=8, spread=0.6, speed=0.05, gravity=0.04,
          size=[0.5, 0.1], life=14, color='#9FD8F0', blend='translucent', comment='вода окатывает'),
        E('flash', 2, at(F, 0, 1.4, 0), duration=8, size=2.4, color='#E8F6FA'),
        E('sprites', 2, at(F, 0, 1.0, 0), duration=80, texture='mote_ash', count=100000, rate=3.0, area=4.5, speed=0.01, gravity=-0.006,
          spin=20, size=[2.2, 1.0], life=50, color='#D8E4E8', blend='translucent', comment='клубы пара r5'),
        E('sprites', 2, at(F, 0, 0.3, 0), duration=80, texture='mote_ash', count=100000, rate=1.5, area=5.0, speed=0.0, gravity=-0.002,
          size=[3.0, 1.5], life=60, color='#B8C8CC', blend='translucent', comment='стелется по земле'),
        E('tint', 0, F, duration=100, radius=5, color='#C8D4D8', strength=0.35, saturation=0.5, **{'in': ease(10), 'out': ease(30)}),
        E('aura', 2, F, duration=90, follow=False, target='caster', thickness=0.12, pulse=[0.2, 10], color='#E8F6FA', motes=10),
    ])
    # ---------------------------------------------------------------- 4. Мехи
    fx('aris_bellows_warn', '«Мехи», предупреждение (0–0.8 с анимации bellows; caster = Арис, yaw — направление, не follow, 16 тиков): '
       'конус 60° длиной 8 бл. на земле (decal aris_cone, вершина у Арис, раскрывается вперёд) наливается жаром, по краям — искры.', 16, [
        E('decal', 0, F, duration=16, texture='aris_cone', radius=8, yaw=0, glow=0.8, color='@secondary', brightness=1.0, grow=10,
          pulse=6, comment='вершина — в центре картинки, раскрытие — вперёд по yaw'),
        E('sprites', 0, at(F, 0, 0.2, 4), duration=16, texture='spark_soft', count=100000, rate=1.5, area=3, speed=0.02, gravity=-0.02,
          size=[0.12, 0.02], life=10, color='@secondary', glow=0.9),
    ])
    fx('aris_bellows', '«Мехи», порыв (событие gust 0.8 с; caster = Арис, yaw — направление, 24 тика): поток горячего воздуха и искр '
       'по конусу 8 бл. (sprites по path), марево, вспышка у молота. Код: всем в конусе — отброс и поджог.', 24, [
        E('flash', 0, at(F, 0, 1.4, 1.5), duration=8, size=2.2, color='@core'),
        E('sprites', 0, at(F, 0, 1.2, 1.0), duration=10, texture='mote_flame', count=120, rate=12, path=[at(F, 0, 1.2, 1.0), at(F, 0, 1.0, 4.5),
          at(F, 0, 0.8, 8.5)], width=3.6, size=[0.6, 0.1], life=12, color='@secondary', glow=0.8, comment='поток жара конусом'),
        E('sprites', 0, at(F, 0, 1.2, 1.0), duration=10, texture='spark_soft', count=90, rate=9, path=[at(F, 0, 1.4, 1.0), at(F, 0, 1.2, 5.0),
          at(F, 0, 1.0, 9.0)], width=4.2, size=[0.14, 0.02], life=10, color='@core', glow=0.9),
        E('sprites', 2, at(F, 0, 1.0, 1.0), duration=10, texture='mote_ash', count=40, rate=4, path=[at(F, 0, 1.0, 1.0), at(F, 0, 1.0, 8.0)],
          width=3.0, size=[1.2, 0.4], life=16, color='#6A5048', blend='translucent', comment='марево/дым'),
    ])
    fx('aris_bellows_burn', 'Игрока задел порыв «Мехов» (caster = игрок): вспышка жара, искры по ветру.', 12, [
        E('flash', 0, at(F, 0, 1.0, 0), duration=6, size=1.2, color='@secondary'), sparks(0, at(F, 0, 1.0, 0), 14, 0.25, 10, 2)])
    sigil('aris_chain_seal', 'T28 «Цепи кузни»: печать звеньев под скованным (r1.8).', 1.8, STEEL_L, [
        L('ring', 'disc', 'aris_chain_seal', 1.0, 0.0, ap(0, 8, 'draw', startAngle=90), rot=-0.8, br=0.9)], dissolve=('shatter', 'fade'), ddur=10)


def icons4():
    def chained(d, S):
        d.ellipse([S * .05, S * .05, S * .95, S * .95], fill=hx('#1C1C22'), outline=hx('#A9A9B4'), width=int(S * .08))
        for k, (x, y) in enumerate(((.3, .3), (.42, .42), (.54, .54), (.66, .66))):
            w = (.14, .08) if k % 2 else (.08, .14)
            d.ellipse([S * (x - w[0]), S * (y - w[1]), S * (x + w[0]), S * (y + w[1])], outline=hx('#C6C6CE'), width=int(S * .06))
        d.rectangle([S * .2, S * .72, S * .8, S * .8], fill=hx('#60606C'))
        d.point((S * .5, S * .76), fill=hx('#F4A852'))

    def steamed(d, S):
        d.ellipse([S * .05, S * .05, S * .95, S * .95], fill=hx('#2A3438'), outline=hx('#9FD8F0'), width=int(S * .08))
        for k, (x, y, r) in enumerate(((.38, .42, .16), (.6, .38, .14), (.5, .58, .2), (.32, .62, .12), (.68, .6, .13))):
            d.ellipse([S * (x - r), S * (y - r), S * (x + r), S * (y + r)], fill=hx('#D8E4E8' if k % 2 else '#B8C8CC'))
    return {'aris_chained': icon('aris_chained', chained), 'aris_steamed': icon('aris_steamed', steamed)}


LANG.update({
    'ui.pohsmp_core.aris.billet': ('Раскалённая заготовка — отойдите, сейчас взорвётся!', 'Red-hot Billet — get clear, it\'s about to blow!'),
    'ui.pohsmp_core.aris.chains': ('Цепи кузни сковали %s — бейте по цепям!', 'Forge Chains bind %s — strike the chains!'),
    'ui.pohsmp_core.aris.chains_self': ('Вас сковали цепи кузни', 'You are bound by the Forge Chains'),
    'ui.pohsmp_core.aris.chains_break': ('Цепи разбиты', 'The chains shatter'),
    'ui.pohsmp_core.aris.quench': ('Закалка: Арис окутана паром', 'Quench: Aris is wreathed in steam'),
    'ui.pohsmp_core.aris.bellows_warn': ('Мехи! Уйдите с конуса жара', 'Bellows! Get out of the heat cone'),
    'ui.pohsmp_core.aris.bellows': ('Мехи', 'Bellows'),
    'effect.pohsmp_core.aris_chained': ('Скован', 'Chained'),
    'effect.pohsmp_core.aris_chained.description': ('Цепи кузни держат на месте. Союзники могут разбить их тремя ударами.',
                                                    'The Forge Chains hold you in place. Allies can break them with three strikes.'),
    'effect.pohsmp_core.aris_steamed': ('В паре', 'Steamed'),
    'effect.pohsmp_core.aris_steamed.description': ('Густой пар «Закалки»: видно лишь на пару блоков.', 'Thick steam from the Quench: you can barely see.'),
    'entity.pohsmp_core.aris_billet': ('Раскалённая заготовка', 'Red-hot Billet'),
    'subtitles.pohsmp_core.aris.billet': ('Шипит раскалённый слиток', 'Red-hot billet hisses'),
    'subtitles.pohsmp_core.aris.billet_explode': ('Слиток взрывается', 'Billet explodes'),
    'subtitles.pohsmp_core.aris.chains': ('Звенят цепи кузни', 'Forge chains rattle'),
    'subtitles.pohsmp_core.aris.chains_break': ('Цепи разбиты', 'Chains shatter'),
    'subtitles.pohsmp_core.aris.quench': ('Шипит пар', 'Steam hisses'),
    'subtitles.pohsmp_core.aris.bellows': ('Ревут мехи', 'Bellows roar'),
})
SOUNDS.update({
    'aris.billet': [S_('minecraft:block/lava/pop', pitch=1.2), S_('minecraft:block/fire/extinguish', pitch=1.6, volume=0.5)],
    'aris.billet_explode': [S_('minecraft:random/explode1', pitch=1.2), S_('minecraft:random/explode2', pitch=1.2)],
    'aris.chains': [S_('minecraft:block/chain/place', pitch=0.6, volume=1.3), S_('minecraft:block/chain/step1', pitch=0.5, volume=1.3)],
    'aris.chains_break': [S_('minecraft:block/chain/break1', pitch=0.7), S_('minecraft:block/anvil/break', pitch=1.4)],
    'aris.quench': [S_('minecraft:block/fire/extinguish', pitch=0.5, volume=1.5), S_('minecraft:block/lava/extinguish', pitch=0.6, volume=1.4)],
    'aris.bellows': [S_('minecraft:item/firecharge/use', pitch=0.5, volume=1.4), S_('minecraft:entity/blaze/shoot', pitch=0.5)],
})


# ================================================================== обзорные листы (PIL)
def _tint(name, color, size, bg=(14, 16, 20)):
    im = Image.open(os.path.join(G.A, 'textures', 'sigil', name + '.png')).convert('RGBA').resize(size, Image.LANCZOS)
    a = np.asarray(im, np.float32)[..., 3:] / 255
    c = np.array(hx(color)[:3], np.float32)
    out = np.array(bg, np.float32) * (1 - a) + c * a
    glow = Image.fromarray(out.astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))
    return Image.blend(glow, Image.fromarray(out.astype(np.uint8)), 0.75)


def sheet_ui(bars, ttl, icns):
    W, H = 1600, 1000
    im = Image.new('RGB', (W, H), (14, 16, 20))
    d = ImageDraw.Draw(im)
    f = MixFont(30)
    y = 20
    for ph in (1, 2, 3):
        f.draw(d, (40, y), 'Фаза %d' % ph, (220, 236, 240))
        b = bars[ph]
        for k, prog in enumerate((1.0, 0.55)):
            row = Image.new('RGBA', (192, 18), (0, 0, 0, 0))
            row.alpha_composite(b.crop((0, 0, 192, 18)))
            wfull = int(3 + prog * 186)
            row.alpha_composite(b.crop((0, 18, wfull, 36)), (0, 0))
            im.paste(row.resize((192 * 3, 54), Image.NEAREST), (220 + k * 640, y - 6), row.resize((192 * 3, 54), Image.NEAREST))
        y += 80
    heat = Image.open(os.path.join(G.A, 'textures/gui/sprites/boss_bars/aris_bossbar_p3_heat.png')).convert('RGBA')
    f.draw(d, (40, y), 'Фаза 3: жар над рамкой (кадр 0)', (220, 236, 240))
    row = Image.new('RGBA', (192, 24), (0, 0, 0, 0))
    row.alpha_composite(heat.crop((0, 0, 192, 14)), (0, 0))
    row.alpha_composite(bars[3].crop((0, 18, 192, 36)), (0, 5))
    im.paste(row.resize((576, 72), Image.NEAREST), (520, y - 10), row.resize((576, 72), Image.NEAREST))
    y += 90
    for i, k in enumerate(('aris_ru', 'aris_en')):
        t = ttl[k].resize((768, 144))
        im.paste(t, (40 + (i % 2) * 790, y), t)
    y += 160
    for i, k in enumerate(('aris_forge_ru', 'aris_last_blow_ru', 'aris_forge_en', 'aris_last_blow_en')):
        t = ttl[k].resize((768, 144))
        im.paste(t, (40 + (i % 2) * 790, y + (i // 2) * 150), t)
    y += 310
    for i, (k, v) in enumerate(icns.items()):
        ic = v.resize((108, 108), Image.NEAREST)
        im.paste(ic, (40 + i * 400, y), ic)
        f.draw(d, (40 + i * 400 + 120, y + 36), {'aris_reforged': 'Перековка', 'aris_scorched': 'Раскалённый пол', 'aris_chained': 'Скован',
                                                'aris_steamed': 'В паре'}[k], (220, 236, 240))
    im.save(os.path.join(MEDIA, 't28_ui.jpg'), quality=90)


def sheet_sigils():
    W, H = 2100, 520
    im = Image.new('RGB', (W, H), (14, 16, 20))
    d = ImageDraw.Draw(im)
    f = MixFont(26)
    items = [('aris_cone', MOLTEN, 'конус «Мехов»'), ('aris_chain_seal', STEEL_L, 'печать цепей'), ('aris_emblem', TEAL, 'знак Арис'), ('aris_forge_ring', MOLTEN, '«Горн» r24'), ('aris_target', TEAL, '«Последний удар» r14'),
             ('aris_island', TEAL, 'островок'), ('aris_reforge', MOLTEN, 'перековка'), ('aris_molten_floor', MOLTEN, 'пол-горн, вмятины')]
    for i, (n, c, lab) in enumerate(items):
        t = _tint(n, c, (240, 240))
        im.paste(t, (20 + i * 262, 60))
        f.draw(d, (24 + i * 262, 320), lab, (220, 236, 240))
    mr = _tint('aris_molten_ring', MOLTEN, (1500, 90))
    im.paste(mr, (50, 380))
    f.draw(d, (50, 476), 'волна раскалённого металла (wave.texture)', (220, 236, 240))
    im.save(os.path.join(MEDIA, 't28_sigils.jpg'), quality=90)


# ================================================================== запуск
def run(gmod, anmod, args, anims):
    global G, AN
    G, AN = gmod, anmod
    textures()
    sigils()
    meshes()
    effects()
    bars = bossbars()
    ttl = titles()
    icns = icons()
    spells4()
    icns.update(icons4())
    lang_sounds()
    os.makedirs(MEDIA, exist_ok=True)
    sheet_ui(bars, ttl, icns)
    sheet_sigils()
    print('aris fx: печатей 5, мешей 4, эффектов %d, полос 3 (+жар, вспышка), титров 6, иконок 2, lang %d ключей, звуков %d'
          % (len([f for f in os.listdir(os.path.join(G.A, 'fx')) if f.startswith('aris_')]), len(LANG), len(SOUNDS) + 1))
