#!/usr/bin/env python3
"""
T27 «Ирина, Ведьма Ревности» — эффекты, печати, полоса босса по фазам, титры, иконки статусов, lang, звуки, проверочные кадры.
Вызывается из tools/gen_irina.py (run(M, args)).

Время — тики, углы — градусы, размеры — блоки. Цвета: красные нити #E3262F, лиловое #B99BE0, тьма капюшона.
Правило владельца: никаких лучей/нитей ОТ неё К цели — нити кружат вокруг неё и вокруг меченых игроков (orbit-следы), кража эффектов —
свет поднимается с игрока и рассеивается, а у неё собирается воронкой со всех сторон (не из точки игрока).
"""
import json
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import gen_forbidden_fx as F  # noqa: E402  (L, T, ap, E, ease, off, _icon)

M = None
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
MEDIA = os.path.join(ROOT, 'docs', 'media')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
WRITTEN = []

RED, RED_L, RED_D, RED_DD = '#C0201C', '#DC3A30', '#7A0E10', '#4E0610'
LIL, LIL_L, LIL_D = '#B99BE0', '#E2CDF5', '#6E4E9C'
CORE = '#FFE0E6'
GOLD = '#F2C14A'
HAPPY = '#FFE7A0'           # свет «чужого счастья» (тёплый золотой)
HAPPY2 = '#B8F0C8'
T_INTRO, T_DEATH, T_FIN = 140, 100, 52
R_HAPPY = 24


def write(rel, obj):
    p = os.path.join(A, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write('\n')
    WRITTEN.append(rel)


def _c(h, a=255):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)


# ================================================================== текстуры (белое на прозрачном → textures/sigil)
def save_mask(img, name, size=512):
    small = img.resize((size, size), Image.LANCZOS)
    rgba = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    rgba.putalpha(small)
    p = os.path.join(A, 'textures', 'sigil', name + '.png')
    rgba.save(p)
    WRITTEN.append('textures/sigil/%s.png' % name)


def thread_line(d, pts, w, fill=255):
    d.line(pts, fill=fill, width=int(w), joint='curve')
    r = w / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def heart_pts(cx, cy, s, n=160):
    pts = []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s, cy - y * s))
    return pts


def loop_ring(cx, cy, R, loops, amp, n=1400, phase=0.0):
    """Нить, бегущая по кругу петлями (циклоида): кольцо из узелков."""
    pts = []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        r = R + amp * math.cos(loops * t + phase)
        a = t + (amp / R) * 0.9 * math.sin(loops * t + phase)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def tex_mark():
    """«Предмет ревности»: сердце, туго перемотанное нитью, внутри — око (ревнивый взгляд); снизу хвосты нити."""
    S = 1024
    im = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(im)
    hp = heart_pts(512, 470, 22)
    thread_line(d, hp, 26)
    hp2 = heart_pts(512, 470, 17.5)
    thread_line(d, hp2, 8)
    # перемотка нитью: косые витки поперёк сердца
    mask = Image.new('L', (S, S), 0)
    ImageDraw.Draw(mask).polygon(hp, fill=255)
    wr = Image.new('L', (S, S), 0)
    dw = ImageDraw.Draw(wr)
    for k in range(-8, 9):
        x0 = 512 + k * 56
        dw.line([(x0 - 260, 160), (x0 + 260, 820)], fill=255, width=12)
    hole = Image.new('L', (S, S), 0)
    ImageDraw.Draw(hole).ellipse([352, 360, 672, 560], fill=255)
    wr = Image.composite(Image.new('L', (S, S), 0), wr, hole)
    im = Image.composite(wr, im, mask)
    d = ImageDraw.Draw(im)
    # око
    eye = [(352, 460)] + [(512 + 160 * math.cos(t), 460 - 85 * math.sin(t)) for t in np.linspace(0, math.pi, 40)][::-1] + \
          [(512 + 160 * math.cos(t), 460 + 85 * math.sin(t)) for t in np.linspace(math.pi, 0, 40)]
    d.line(eye + [eye[0]], fill=255, width=16, joint='curve')
    d.ellipse([462, 410, 562, 510], fill=255)
    d.ellipse([496, 426, 528, 494], fill=0)
    # хвосты нити, свисающие с острия сердца
    for sx in (-1, 1):
        pts = [(512 + sx * 20 * t / 10 + sx * 50 * math.sin(t / 3), 820 + t * 14) for t in range(0, 12)]
        thread_line(d, pts, 10)
    save_mask(im, 'irina_mark')


def tex_knots():
    """Метки пар фазы 2: две сцепленные петли нити + свой знак внутри (1 — сердце, 2 — луна, 3 — звезда, 4 — ромб).
    У обоих игроков пары — один и тот же знак: так видно, кто с кем связан, без линии между ними."""
    for k in range(1, 5):
        S = 1024
        im = Image.new('L', (S, S), 0)
        d = ImageDraw.Draw(im)
        for cx in (392, 632):
            d.ellipse([cx - 230, 282, cx + 230, 742], outline=255, width=30)
        # «перехлёст» — разрыв обводки там, где петли проходят друг под другом
        d.rectangle([496, 270, 528, 330], fill=0)
        d.rectangle([496, 694, 528, 754], fill=0)
        cx, cy = 512, 512
        if k == 1:
            d.polygon(heart_pts(cx, cy + 10, 6.0), fill=255)
        elif k == 2:
            d.ellipse([cx - 90, cy - 90, cx + 90, cy + 90], fill=255)
            d.ellipse([cx - 50, cy - 110, cx + 130, cy + 70], fill=0)
        elif k == 3:
            pts = [(cx + (100 if i % 2 == 0 else 42) * math.sin(math.pi * i / 5), cy - (100 if i % 2 == 0 else 42) * math.cos(math.pi * i / 5))
                   for i in range(10)]
            d.polygon(pts, fill=255)
        else:
            d.polygon([(cx, cy - 110), (cx + 75, cy), (cx, cy + 110), (cx - 75, cy)], fill=255)
            d.polygon([(cx, cy - 55), (cx + 36, cy), (cx, cy + 55), (cx - 36, cy)], fill=0)
        save_mask(im, 'irina_knot_%d' % k)
    # разорванная пара (при «разрыве нитей»)
    S = 1024
    im = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(im)
    for cx, a0, a1 in ((392, 40, 320), (632, 220, 140 + 360)):
        d.arc([cx - 230, 282, cx + 230, 742], a0, a1, fill=255, width=30)
    for x, y, a in ((560, 330, -0.6), (470, 700, 2.5), (600, 640, 0.9), (430, 370, 3.9)):
        thread_line(d, [(x, y), (x + 70 * math.cos(a), y + 70 * math.sin(a)), (x + 110 * math.cos(a + 0.5), y + 110 * math.sin(a + 0.5))], 18)
    save_mask(im, 'irina_knot_break')


def tex_thread_ring():
    S = 1024
    im = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(im)
    thread_line(d, loop_ring(512, 512, 430, 14, 46), 14)
    thread_line(d, loop_ring(512, 512, 430, 9, 30, phase=1.3), 7)
    d.ellipse([60, 60, 964, 964], outline=200, width=5)
    save_mask(im, 'irina_thread_ring')


def tex_emblem():
    """Знак 2 Ячейки Культа: шляпа ведьмы с крестом в кольце из нити, сверху — две насечки (II)."""
    S = 1024
    im = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(im)
    thread_line(d, loop_ring(512, 512, 450, 18, 22), 12)
    d.ellipse([110, 110, 914, 914], outline=255, width=14)
    # шляпа
    d.polygon([(250, 640), (774, 640), (700, 690), (324, 690)], fill=255)                  # поля
    d.polygon([(380, 640), (644, 640), (600, 360), (560, 250), (470, 300), (440, 360)], fill=255)     # тулья
    d.polygon([(560, 250), (640, 230), (690, 280), (600, 300)], fill=255)                  # загнутая верхушка
    d.rectangle([396, 580, 628, 612], fill=0)                                             # лента
    d.rectangle([496, 400, 528, 520], fill=0)                                             # крест (вырезом)
    d.rectangle([462, 436, 562, 464], fill=0)
    # II
    for x in (470, 540):
        d.polygon([(x, 150), (x + 20, 150), (x + 14, 230), (x + 6, 230)], fill=255)
    # нить обвивает знак: S-образная петля через низ
    pts = [(200 + t * 6.2, 760 + 60 * math.sin(t / 12)) for t in range(0, 101)]
    thread_line(d, pts, 12)
    save_mask(im, 'irina_emblem')


def tex_happiness():
    """«Чужое счастье»: печать r24. По кругу — 12 знаков чужого счастья (солнце, цветок, сердце, звезда, колос, нота…),
    от каждого к центру закручивается нить; в центре — сжатая ладонь в сердце из нити. Обод — кольцо из петель."""
    S = 2048
    im = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(im)
    c = S / 2
    thread_line(d, loop_ring(c, c, 960, 36, 26, n=3000), 12)
    d.ellipse([c - 900, c - 900, c + 900, c + 900], outline=255, width=8)
    d.ellipse([c - 640, c - 640, c + 640, c + 640], outline=255, width=6)
    for k in range(12):
        a = 2 * math.pi * k / 12 - math.pi / 2
        gx, gy = c + 770 * math.cos(a), c + 770 * math.sin(a)
        r = 80
        kind = k % 6
        if kind == 0:                                     # солнце
            d.ellipse([gx - 40, gy - 40, gx + 40, gy + 40], fill=255)
            for j in range(8):
                b = 2 * math.pi * j / 8
                d.line([(gx + 56 * math.cos(b), gy + 56 * math.sin(b)), (gx + r * math.cos(b), gy + r * math.sin(b))], fill=255, width=10)
        elif kind == 1:                                   # цветок
            for j in range(5):
                b = 2 * math.pi * j / 5
                d.ellipse([gx + 40 * math.cos(b) - 30, gy + 40 * math.sin(b) - 30, gx + 40 * math.cos(b) + 30, gy + 40 * math.sin(b) + 30], fill=255)
            d.ellipse([gx - 18, gy - 18, gx + 18, gy + 18], fill=0)
        elif kind == 2:                                   # сердце
            d.polygon(heart_pts(gx, gy, 4.4), fill=255)
        elif kind == 3:                                   # звезда
            d.polygon([(gx + (r if i % 2 == 0 else 34) * math.sin(math.pi * i / 5), gy - (r if i % 2 == 0 else 34) * math.cos(math.pi * i / 5))
                       for i in range(10)], fill=255)
        elif kind == 4:                                   # нота
            d.ellipse([gx - 50, gy + 10, gx - 6, gy + 50], fill=255)
            d.line([(gx - 8, gy + 30), (gx - 8, gy - 70), (gx + 40, gy - 50)], fill=255, width=12)
        else:                                             # кольцо (обручальное)
            d.ellipse([gx - 55, gy - 45, gx + 55, gy + 65], outline=255, width=14)
            d.polygon([(gx - 20, gy - 45), (gx, gy - 80), (gx + 20, gy - 45)], fill=255)
        # нить от знака спиралью к центру
        pts = []
        for i in range(120):
            u = i / 119
            rr = 680 * (1 - u) + 130 * u
            aa = a + u * 1.6
            pts.append((c + rr * math.cos(aa), c + rr * math.sin(aa)))
        thread_line(d, pts, 9)
    thread_line(d, heart_pts(c, c + 10, 10.5), 18)
    # сжатая в кулак ладонь (силуэт) в сердце
    d.ellipse([c - 70, c - 50, c + 70, c + 80], fill=255)
    for j in range(4):
        d.rounded_rectangle([c - 70 + j * 36, c - 95, c - 40 + j * 36, c - 20], 14, fill=255)
    d.rounded_rectangle([c - 110, c - 10, c - 55, c + 50], 20, fill=255)
    save_mask(im, 'irina_happiness', size=1024)


def tex_motes():
    for name, fn in (('mote_thread', 0), ('mote_heart', 1), ('mote_glee', 2)):
        S = 256
        im = Image.new('L', (S, S), 0)
        d = ImageDraw.Draw(im)
        if fn == 0:                                     # обрывок нити — завиток
            pts = [(128 + (70 - t * 2.2) * math.cos(t / 6), 128 + (70 - t * 2.2) * math.sin(t / 6)) for t in range(0, 30)]
            thread_line(d, pts, 16)
        elif fn == 1:
            d.polygon(heart_pts(128, 132, 5.6), fill=255)
        else:                                           # искра счастья — четырёхлучевая звёздочка с ореолом
            d.polygon([(128, 20), (148, 108), (236, 128), (148, 148), (128, 236), (108, 148), (20, 128), (108, 108)], fill=255)
            im = Image.composite(im, Image.new('L', (S, S), 0), im).filter(ImageFilter.GaussianBlur(1))
        save_mask(im, name, size=128)


def tex_extra():
    """+4 заклинания: узел-ловушка (видимый на земле), око с нитью («Ревнивый взгляд»), крестовина марионетки."""
    S = 1024
    im = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(im)
    thread_line(d, loop_ring(512, 512, 330, 7, 90), 26)                  # узел: петли, туго стянутые к центру
    thread_line(d, loop_ring(512, 512, 200, 5, 70, phase=0.6), 20)
    d.ellipse([452, 452, 572, 572], fill=255)
    for a in range(6):                                                   # хвосты-«щупальца» узла
        b = a * math.pi / 3 + 0.3
        pts = [(512 + (420 + t * 6) * math.cos(b + 0.15 * math.sin(t / 3)), 512 + (420 + t * 6) * math.sin(b + 0.15 * math.sin(t / 3)))
               for t in range(0, 12)]
        thread_line(d, pts, 14)
    save_mask(im, 'irina_knot_trap')
    im = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(im)
    eye = [(512 + 300 * math.cos(t), 512 - 150 * math.sin(t)) for t in np.linspace(0, math.pi, 50)] + \
          [(512 + 300 * math.cos(t), 512 + 150 * math.sin(t)) for t in np.linspace(math.pi, 2 * math.pi, 50)]
    d.line(eye + [eye[0]], fill=255, width=34, joint='curve')
    d.ellipse([412, 412, 612, 612], fill=255)
    d.ellipse([480, 440, 544, 584], fill=0)
    pts = [(200 + t * 6, 760 + 40 * math.sin(t / 10)) for t in range(0, 105)]
    thread_line(d, pts, 16)
    save_mask(im, 'irina_gaze_eye')
    im = Image.new('L', (S, S), 0)
    d = ImageDraw.Draw(im)
    d.rectangle([200, 470, 824, 554], fill=255)                          # крестовина марионетки
    d.rectangle([470, 230, 554, 794], fill=255)
    for (x, y) in ((212, 554), (812, 554), (512, 794), (512, 554)):
        thread_line(d, [(x, y), (x + 6, y + 120), (x - 4, y + 200)], 12)
    save_mask(im, 'irina_puppet_cross')


def textures():
    tex_extra()
    tex_mark()
    tex_knots()
    tex_thread_ring()
    tex_emblem()
    tex_happiness()
    tex_motes()


# ================================================================== печати
L, T, ap = F.L, F.T, F.ap


def sigil(id, comment, size, color, orientation, layers, hold=-1, flash=None, dissolve=('fade',), ddur=12, stagger=2):
    o = {'comment': comment, 'size': size, 'color': color, 'orientation': orientation, 'lifetime': -1, 'hold': hold, 'layers': layers}
    if flash:
        o['formedFlash'] = flash
    o['dissolve'] = {'modes': list(dissolve), 'duration': ddur, 'stagger': stagger}
    write('sigils/%s.json' % id, o)


def sigils_extra():
    sigil('irina_knot_trap', 'T27 «Узлы»: нитяной узел-ловушка на земле (r 0.9), ВИДЕН всем; пульсирует; наступил — опутан (код).',
          0.9, RED, 'ground', [
              L('glow', 'disc', 'glow', 1.3, -0.01, ap(0, 10, 'fade'), color=RED_DD, br=0.5, pulse=(0.3, 24)),
              L('knot', 'disc', 'irina_knot_trap', 1.0, 0.0, ap(0, 16, 'draw', startAngle=90), rot=0.8, br=1.1, pulse=(0.15, 24)),
          ], dissolve=('shatter', 'fade'), ddur=10)
    sigil('irina_gaze_eye', 'T27 «Ревнивый взгляд»: око с нитью над головой смотревшего (метка-нить, замедление).', 0.36, RED, 'ground', [
        L('eye', 'disc', 'irina_gaze_eye', 1.0, 0.0, ap(0, 8, 'grow', 'fade', easing='easeOutBack'), rot=1.0, br=1.1, pulse=(0.2, 14)),
    ], dissolve=('fade',), ddur=8)
    sigil('irina_puppet_cross', 'T27 «Марионетка»: крестовина над головой игрока-марионетки (нити свисают к нему, к Ирине — нет).',
          0.5, RED, 'facing', [
              L('cross', 'disc', 'irina_puppet_cross', 1.0, 0.0, ap(0, 10, 'unfold', 'fade', easing='easeOutBack'), br=1.1, pulse=(0.12, 10)),
          ], dissolve=('collapse', 'fade'), ddur=8)


def sigils():
    sigils_extra()
    sigil('irina_mark', 'T27 «Предмет ревности»: метка над головой меченого игрока — сердце, перемотанное нитью, с оком; медленно кружит, '
                        'пульсирует как сердцебиение. Лежит над головой (ground), видна всем.', 0.5, RED, 'ground', [
        L('glow', 'disc', 'glow', 1.5, -0.01, ap(0, 10, 'fade'), color=RED_D, br=0.5, pulse=(0.3, 16)),
        L('mark', 'disc', 'irina_mark', 1.0, 0.0, ap(0, 12, 'grow', 'fade', easing='easeOutBack'), rot=-1.5, br=1.2, pulse=(0.18, 16)),
    ], dissolve=('collapse', 'fade'), ddur=10)
    for k in range(1, 5):
        sigil('irina_knot_%d' % k, 'T27 фаза 2 «Красные нити»: метка пары №%d над головой (две сцепленные петли и свой знак). Оба игрока пары '
                                  'получают одинаковый знак — без линии между ними.' % k, 0.42, RED, 'ground', [
            L('glow', 'disc', 'glow', 1.4, -0.01, ap(0, 8, 'fade'), color=RED_D, br=0.4, pulse=(0.25, 24)),
            L('knot', 'disc', 'irina_knot_%d' % k, 1.0, 0.0, ap(0, 12, 'draw', startAngle=90, easing='easeOutCubic'), rot=1.2, br=1.1),
        ], dissolve=('fade',), ddur=8)
    sigil('irina_knot_break', 'T27: разрыв пары — разорванные петли, осколки нити; рассыпаются за 0.6 с.', 0.55, RED_L, 'ground', [
        L('knot', 'disc', 'irina_knot_break', 1.0, 0.0, ap(0, 4, 'grow', 'fade'), rot=6, br=1.4),
    ], hold=8, dissolve=('shatter', 'fade'), ddur=10)
    sigil('irina_thread_ring', 'T27: кольцо из петель нити под ногами (меченый, пара, кокон).', 0.9, RED, 'ground', [
        L('ring', 'disc', 'irina_thread_ring', 1.0, 0.0, ap(0, 14, 'draw', startAngle=90), rot=2.0, br=1.0),
        L('ring2', 'disc', 'irina_thread_ring', 0.8, 0.01, ap(4, 14, 'draw', startAngle=-90, direction=-1), rot=-3.0, br=0.6, color=LIL),
    ], dissolve=('reverse', 'fade'), ddur=10)
    sigil('irina_emblem', 'T27: знак 2 Ячейки Культа (шляпа ведьмы с крестом в кольце нити, «II») под Ириной — появление, переходы фаз.',
          3.4, LIL, 'ground', [
              L('glow', 'disc', 'glow', 1.0, -0.01, ap(0, 10, 'fade'), color=RED_D, br=0.5, pulse=(0.2, 20)),
              L('seal', 'disc', 'irina_emblem', 1.0, 0.0, ap(0, 22, 'draw', startAngle=90, easing='easeOutCubic'), rot=1.0, boost=5, color=LIL_L),
              L('ring', 'disc', 'irina_thread_ring', 1.22, 0.01, ap(10, 16, 'draw', startAngle=-90, direction=-1), rot=-2.5, color=RED, br=1.1),
          ], flash={'color': RED_L, 'size': 1.2, 'duration': 10, 'sparks': 40}, dissolve=('shatter', 'fade'), ddur=14)
    sigil('irina_happiness', 'T27 «Чужое счастье»: печать r24 под Ириной. 0–30 тиков прорисовывается (знаки чужого счастья по кругу), '
                             'нити от знаков закручиваются к центру; держится, пока идёт эффект.', R_HAPPY, LIL, 'ground', [
        L('glow', 'disc', 'glow', 1.0, -0.02, ap(0, 30, 'fade'), color=RED_DD, br=0.35, pulse=(0.12, 30)),
        L('seal', 'disc', 'irina_happiness', 1.0, 0.0, ap(0, 34, 'draw', startAngle=90, easing='easeInOutSine'), rot=-0.4, boost=3, color=LIL_L),
        T('words', 'ЧУЖОЕ СЧАСТЬЕ ✦ ВСЁ ЭТО МОЁ ✦ ', 0.97, 0.03, 0.01, ap(10, 30, 'draw', easing='linear'), font='cyrillic', color=RED_L,
          br=0.9, rot=0.3, repeat=3),
    ], flash={'color': HAPPY, 'size': 1.05, 'duration': 14, 'sparks': 120}, dissolve=('fade', 'collapse'), ddur=20)


# ================================================================== эффекты
E, ease, off = F.E, F.ease, F.off


def fx(id_, comment, dur, els):
    write('fx/%s.json' % id_, {'comment': comment, 'style': 'irina', 'duration': dur, 'elements': els})


def orbit_threads(at, delay, dur, radius, count, speed, rise=0.6, period=40, width=0.07, length=14, color='@primary', climb=None, **kw):
    o = {'radius': radius, 'speed': speed, 'rise': rise, 'risePeriod': period}
    if climb is not None:
        o['climb'] = climb
    return E('trail', delay, at, duration=dur, width=width, length=length, fade=1.2, head=0, count=count, orbit=o, color=color, follow=True, **kw)


def effects():
    write('fx/styles/irina.json', {
        'comment': 'T27 Ирина, Ведьма Ревности: красные нити ревности, лиловая ткань, тьма капюшона; движение вьющееся, плавное, '
                   'с «дыханием» (пульс сердца ревности).',
        'palette': {'primary': RED, 'secondary': LIL, 'core': CORE, 'shadow': RED_DD},
        'textures': {'sparks': 'spark_soft', 'runes': 'rune_band', 'shards': 'mote_thread', 'sigil': 'irina_emblem'},
        'blend': 'additive', 'motion': {'rotationScale': 0.8, 'jitter': 0.05, 'easing': 'easeInOutSine', 'pulse': {'amp': 0.12, 'period': 16}}})
    io = {'in': ease(8), 'out': ease(10, 'easeInSine')}

    # ---- фаза 1: «Предмет ревности»
    fx('irina_mark_apply', 'Метка «Предмет ревности» ставится (caster = меченый игрок, 24 тика). Нити сходятся к нему со всех сторон '
                           '(кольцо сжимается), вспышка у сердца. Затем код запускает irina_mark (до снятия метки). Не от Ирины — у игрока.', 24, [
        E('wave', 0, 'caster+0,1,0', duration=14, shape='ring', radius=3.2, thickness=0.25, reverse=True, color='@primary'),
        orbit_threads('caster', 0, 22, 1.6, 3, 14, rise=0.9, period=18, width=0.08),
        E('flash', 12, 'caster+0,1.2,0', duration=10, size=1.4, ring=True, color='@core'),
        E('sprites', 12, 'caster+0,1.2,0', duration=4, texture='mote_heart', count=10, rate=3, spread=0.5, speed=0.06, gravity=-0.01,
          size=[0.22, 0.05], life=16, color='@primary', glow=0.5),
    ])
    fx('irina_mark', 'Метка «Предмет ревности» (caster = меченый игрок, follow, до Fx.stop). Слать всем. Над головой — сердце с оком; '
                     'две красные нити кружат вокруг игрока (orbit), иногда срываются обрывки. Нити НЕ тянутся к Ирине.', -1, [
        E('sigil', 0, 'caster+0,2.4,0', follow=True, id='irina_mark'),
        orbit_threads('caster', 0, -1, 0.85, 2, 9, rise=0.8, period=46, width=0.06, length=16),
        orbit_threads('caster', 10, -1, 1.1, 1, -6, rise=0.5, period=60, width=0.04, length=10, color='@secondary'),
        E('sprites', 0, 'caster+0,1,0', duration=-1, texture='mote_thread', count=100000, rate=0.12, spread=0.7, speed=0.01, gravity=0.004,
          spin=8, size=[0.18, 0.06], life=30, color='@primary', follow=True),
    ])
    # ---- фаза 2: пары
    for k in range(1, 5):
        fx('irina_bond_%d' % k, 'Фаза 2 «Красные нити»: метка пары №%d (caster = игрок пары, follow, до Fx.stop). Обоим игрокам пары — один id '
                                '(одинаковый знак над головой); кольцо петель под ногами, нить кружит вокруг. Линии между игроками НЕТ.' % k, -1, [
            E('sigil', 0, 'caster+0,2.35,0', follow=True, id='irina_knot_%d' % k),
            E('sigil', 0, 'caster+0,0.05,0', follow=True, id='irina_thread_ring'),
            orbit_threads('caster', 0, -1, 0.75, 1, 8 if k % 2 else -8, rise=0.7, period=40 + 6 * k, width=0.06, length=18),
        ])
    fx('irina_bond_strain', 'Фаза 2: пара разошлась > 9 бл. — предупреждение (caster = игрок, 20 тиков, повторять каждую секунду, пока 9–12 бл.): '
                            'нить вокруг дёргается, метка мигает, хруст.', 20, [
        orbit_threads('caster', 0, 20, 0.6, 2, 20, rise=0.3, period=8, width=0.07, length=8, color='@core'),
        E('flash', 0, 'caster+0,2.35,0', duration=8, size=0.6, color='@primary'),
    ])
    fx('irina_bond_snap', 'Фаза 2: разрыв нитей (> 12 бл.) — у КАЖДОГО из пары (caster = игрок, 30 тиков), урон — код. Знак пары рвётся, '
                          'обрывки нити разлетаются, красная вспышка. Без линии между игроками.', 30, [
        E('sigil', 0, 'caster+0,2.35,0', id='irina_knot_break'),
        E('flash', 0, 'caster+0,1.1,0', duration=10, size=2.2, rays=8, screen=0.12, color='@primary'),
        E('sprites', 0, 'caster+0,1.1,0', duration=4, texture='mote_thread', count=30, rate=8, spread=0.4, speed=0.22, gravity=0.02, spin=30,
          size=[0.3, 0.08], life=20, color='@primary', glow=0.4),
        E('wave', 0, 'caster+0,0.1,0', duration=14, shape='ring', radius=2.6, thickness=0.3, color='@primary'),
        E('slash', 1, 'caster+0,1.1,0', radius=0.9, arc=300, thickness=0.12, bend=1, secondary=0.4, grow=4, life=8, tilt=70, count=3,
          interval=2, color='@primary'),
    ])
    fx('irina_bond_share', 'Фаза 2: урон делится — короткий отклик на ВТОРОМ игроке пары (caster = он, 10 тиков): нить вокруг вспыхивает.', 10, [
        orbit_threads('caster', 0, 10, 0.8, 2, 16, rise=0.2, period=10, width=0.08, length=6, color='@core'),
        E('flash', 0, 'caster+0,1,0', duration=6, size=0.9, color='@primary'),
    ])
    # ---- фаза 3 и кража эффектов
    fx('irina_steal_lose', 'Кража эффектов — у ИГРОКА (caster = игрок, 30 тиков): свет его эффектов поднимается и рассеивается '
                           'искрами (цвет эффекта — color из кода, по умолчанию золотой); нити вокруг затягиваются. НЕ луч к Ирине.', 30, [
        E('aura', 0, 'caster', duration=16, target='caster', thickness=0.12, pulse=[0.4, 6], color=HAPPY, motes=14, ring=False, **io),
        E('sprites', 0, 'caster+0,1,0', duration=14, texture='mote_glee', count=26, rate=2, spread=0.6, speed=0.05, gravity=-0.02,
          size=[0.24, 0.02], life=22, color=HAPPY, glow=0.7),
        orbit_threads('caster', 4, 24, 0.9, 2, 18, rise=0.6, period=12, width=0.06, length=10),
    ])
    fx('irina_steal_gather', 'Кража эффектов — у ИРИНЫ (caster = Ирина, 40 тиков): золотые искры собираются к ней воронкой со всех сторон '
                             '(r 6 → 0), нити вокруг стягиваются, на 30 тике — вспышка-поглощение у груди. Не из точки игрока.', 40, [
        E('vortex', 0, 'caster', duration=34, radius=6, height=0, arms=6, speed=6, pull=1.2, flow=-1, width=0.08, particles=60,
          texture='mote_glee', color=HAPPY, **io),
        E('sprites', 0, 'caster+0,0.2,0', duration=26, texture='mote_glee', count=60, rate=3, area=6, speed=0.0, gravity=-0.03,
          size=[0.22, 0.04], life=20, color=HAPPY, glow=0.6, avoid={'radius': 0.1, 'push': 0}),
        orbit_threads('caster', 0, 40, 1.6, 3, -12, rise=1.2, period=30, width=0.07, length=14),
        E('flash', 30, 'caster+0,1.4,0', duration=10, size=2.0, ring=True, color=HAPPY),
    ])
    fx('irina_fury', 'Фаза 3 «Ярость ревности»: ореол вокруг Ирины (caster = Ирина, follow, до Fx.stop) — широкие нити-плети кружат, '
                     'по земле кольцо петель, обрывки нитей.', -1, [
        orbit_threads('caster', 0, -1, 2.6, 3, 7, rise=1.4, period=50, width=0.1, length=22),
        orbit_threads('caster', 0, -1, 1.5, 2, -11, rise=0.9, period=34, width=0.07, length=16, color='@secondary'),
        E('decal', 0, 'caster', duration=-1, texture='irina_thread_ring', radius=3.2, spin=1.2, glow=0.3, follow=True, color='@primary', brightness=0.7),
        E('sprites', 0, 'caster+0,1.2,0', duration=-1, texture='mote_thread', count=100000, rate=0.3, spread=1.6, speed=0.02, gravity=-0.004,
          spin=12, size=[0.26, 0.06], life=30, color='@primary', follow=True),
    ])
    fx('irina_whip_warn', 'Фаза 3: хлёст нитей — предупреждение (caster = Ирина, 16 тиков = 0.8 с, затем irina_whip). Кольцо r1→7 по земле '
                          '(зона удара r 1.5–7), нити вокруг поднимаются.', 16, [
        E('wave', 0, 'caster+0,0.05,0', duration=16, shape='ring', radius=7, thickness=0.35, followTerrain=True, color='@primary'),
        E('decal', 0, 'caster', duration=16, texture='irina_thread_ring', radius=7, grow=14, glow=0.4, color='@primary', brightness=0.6),
        orbit_threads('caster', 0, 16, 2.0, 4, 18, rise=0.4, period=8, width=0.08, length=10, climb=0.6),
    ])
    fx('irina_whip', 'Фаза 3: хлёст нитей по площади (caster = Ирина, 24 тика; событие анимации irina_whip `lash` = 0.45 с). '
                     'Красные дуги-плети по кругу r 6–7 (три наклона), вспышка, обрывки. Урон r ≤ 7 — код.', 24, [
        E('slash', 0, 'caster+0,0.9,0', radius=6.5, arc=360, thickness=0.22, bend=1, secondary=0.5, grow=5, life=12, tilt=0, pitch=0, color='@primary'),
        E('slash', 2, 'caster+0,1.4,0', radius=5.5, arc=300, thickness=0.16, bend=1, secondary=0.3, grow=5, life=10, tilt=20, count=3, interval=2,
          tiltStep=-20, color='@core'),
        E('flash', 0, 'caster+0,1.2,0', duration=8, size=2.4, ring=True, color='@primary'),
        E('decal', 0, 'caster', duration=60, texture='slash_crack', radius=6.5, glow=0.3, fadeOut=40, color='@primary'),
        E('sprites', 0, 'caster+0,1,0', duration=6, texture='mote_thread', count=50, rate=10, spread=2.5, speed=0.25, gravity=0.02, spin=30,
          size=[0.3, 0.08], life=18, color='@primary'),
    ])
    # ---- «Только мой»: кокон
    fx('irina_cocoon', '«Только мой» — кокон на жертве (caster = жертва, follow, 80 тиков = 4 с или до Fx.stop при разрыве). Нити плотно '
                       'наматываются вокруг (orbit со сжатием), кольцо под ногами, красная оболочка; пульс как сердце. Жертва — в 2 бл. перед Ириной '
                       '(кладёт код). Ни одной нити от Ирины к жертве.', 80, [
        E('sigil', 0, 'caster+0,0.05,0', follow=True, id='irina_thread_ring', scale=1.4),
        orbit_threads('caster', 0, 80, 0.75, 4, 22, rise=1.0, period=14, width=0.09, length=20),
        orbit_threads('caster', 2, 78, 0.6, 3, -26, rise=1.0, period=11, width=0.08, length=16, color='@secondary'),
        orbit_threads('caster', 4, 76, 0.5, 3, 30, rise=1.1, period=9, width=0.07, length=14, color='@shadow'),
        E('aura', 0, 'caster', duration=80, target='caster', thickness=0.3, pulse=[0.35, 16], color='@primary', motes=20, **io),
        E('column', 0, 'caster', duration=80, radius=0.62, height=2.3, fill=0.35, color='@shadow', blend='translucent', **io),
    ])
    fx('irina_cocoon_break', 'Кокон разорван союзниками (caster = жертва, 24 тика): нити лопаются наружу, вспышка, кольцо.', 24, [
        E('flash', 0, 'caster+0,1.1,0', duration=10, size=2.6, rays=10, screen=0.1, ring=True, color='@core'),
        E('sprites', 0, 'caster+0,1.1,0', duration=4, texture='mote_thread', count=60, rate=15, spread=0.6, speed=0.3, gravity=0.03, spin=40,
          size=[0.32, 0.08], life=22, color='@primary', glow=0.4),
        E('wave', 0, 'caster+0,0.1,0', duration=16, shape='ring', radius=4, thickness=0.4, color='@primary'),
    ])
    fx('irina_cocoon_crush', 'Кокон не разорван за 4 с (caster = жертва, 24 тика): нити стягиваются, тёмная вспышка; сильный урон — код.', 24, [
        E('wave', 0, 'caster+0,1,0', duration=10, shape='sphere', radius=1.6, reverse=True, rim=1.2, color='@primary'),
        E('flash', 10, 'caster+0,1.1,0', duration=10, size=2.0, rays=6, screen=0.25, color='@primary'),
        E('sprites', 10, 'caster+0,1.1,0', duration=4, texture='mote_heart', count=16, rate=4, spread=0.5, speed=0.12, gravity=0.03,
          size=[0.24, 0.06], life=18, color=RED_D),
    ])
    fx('irina_only_mine', '«Только мой» — у Ирины (caster = Ирина, 124 тика = анимация irina_only_mine 6.2 с). 0.6 с (`reach`) — ладонь, '
                          'нити вокруг неё собираются в клубок; 1.0 (`yank`) — жертву рывком переносит код (вспышка в обеих точках — '
                          'irina_yank у жертвы); 1.6–5.4 — Ирина «обнимает» кокон, нити вокруг неё сжаты; 5.4 (`crush`) — вспышка.', 124, [
        E('tint', 0, 'caster', duration=124, radius=32, color='#3A0A1E', strength=0.28, **{'in': ease(14), 'out': ease(20, 'easeInSine')}),
        orbit_threads('caster', 0, 24, 1.8, 4, 16, rise=1.4, period=20, width=0.08, length=14),
        E('flash', 20, 'caster+0,1.4,0', duration=8, size=1.8, ring=True, color='@primary'),
        E('sigil', 30, 'caster+0,0.05,0', id='irina_emblem'),
        E('sprites', 30, 'caster+0,1.2,0', duration=78, texture='mote_heart', count=40, rate=0.5, spread=1.2, speed=0.01, gravity=-0.006,
          size=[0.2, 0.05], life=30, color='@primary', glow=0.4, follow=True),
        E('flash', 108, 'caster+0,1.4,0', duration=12, size=2.6, rays=8, color='@primary'),
    ])
    fx('irina_yank', '«Только мой» — рывок жертвы (caster = жертва в ИСХОДНОЙ точке, 16 тиков; второй вызов — в новой точке перед Ириной). '
                     'Нити хватают и исчезают вспышкой; перенос делает код (без линии между точками).', 16, [
        orbit_threads('caster', 0, 10, 0.7, 3, 30, rise=0.4, period=6, width=0.08, length=8),
        E('flash', 6, 'caster+0,1.1,0', duration=10, size=1.6, ring=True, color='@core'),
        E('sprites', 6, 'caster+0,1.1,0', duration=3, texture='mote_thread', count=16, rate=6, spread=0.4, speed=0.12, size=[0.24, 0.06], life=14,
          color='@primary'),
    ])
    # ---- «Чужое счастье»
    fx('irina_others_happiness', '«Чужое счастье» (caster = Ирина, не follow; 120 тиков = анимация irina_others_happiness 6 с). '
                                 '0–1.5 с — печать r24 прорисовывается, мир лиловеет; 1.4 (`spread`) — у всех игроков в r24 код снимает полезные '
                                 'эффекты и запускает irina_steal_lose; золотые искры поднимаются над ВСЕЙ печатью; 3.6 (`gather`) — искры '
                                 'закручиваются к Ирине воронкой r24 → 0 (со всех сторон, не от игроков); 5.2 (`absorb`) — вспышка, '
                                 'Ирина забирает эффекты себе.', 120, [
        E('tint', 0, 'caster', duration=120, radius=R_HAPPY + 8, color='#2A1040', strength=0.3, **{'in': ease(24), 'out': ease(24, 'easeInSine')}),
        E('sigil', 0, 'caster+0,0.05,0', id='irina_happiness'),
        E('sigil', 0, 'caster+0,0.08,0', id='irina_emblem'),
        E('curtain', 10, 'caster', duration=100, radius=[1.2, 2.2], count=14, height=4.5, grow=20, width=[0.08, 0.16], brightness=[0.6, 1.0],
          flicker=0.3, texture='beam_fade', color='@primary', **io),
        E('sprites', 28, 'caster+0,0.3,0', duration=44, texture='mote_glee', count=500, rate=10, area=R_HAPPY, speed=0.0, gravity=-0.02,
          sway=0.6, size=[0.32, 0.08], life=40, color=HAPPY, glow=0.7),
        E('sprites', 28, 'caster+0,0.3,0', duration=44, texture='mote_glee', count=200, rate=4, area=R_HAPPY, speed=0.0, gravity=-0.015,
          sway=0.6, size=[0.26, 0.06], life=40, color=HAPPY2, glow=0.6),
        E('vortex', 72, 'caster', duration=34, radius=R_HAPPY, height=0, arms=12, speed=5, pull=2.4, flow=-1, width=0.12, particles=240,
          life=28, size=0.3, texture='mote_glee', color=HAPPY, **io),
        orbit_threads('caster', 72, 36, 3.0, 6, -14, rise=2.0, period=30, width=0.09, length=20, climb=-0.8),
        E('flash', 104, 'caster+0,1.8,0', duration=14, size=4.5, rays=12, screen=0.3, ring=True, color=HAPPY),
        E('wave', 104, 'caster+0,0.2,0', duration=20, shape='ring', radius=10, thickness=0.6, color='@primary'),
    ])
    # ---- +4 заклинания (владелец 20.11)
    fx('irina_gaze_cast', '«Ревнивый взгляд» — у Ирины (caster = Ирина, 24 тика; анимация irina_gaze, событие gaze 0.5 с): из тьмы капюшона '
                          'вспыхивают два красных огонька, по полям шляпы бежит нить. Метку смотревшим ставит код (кто смотрел на неё > 2 с).', 24, [
        E('flash', 8, 'caster+0,2.1,0.3', duration=10, size=0.7, color='@primary'),     # перед капюшоном (z — вперёд; было −0.3 — за головой)
        orbit_threads('caster+0,2.3,0', 0, 24, 1.3, 2, 16, rise=0.1, period=10, width=0.05, length=10),
    ])
    fx('irina_gaze_mark', '«Ревнивый взгляд» — метка-нить на смотревшем (caster = игрок, follow, 80 тиков = 4 с замедления): око над головой, '
                          'нить обвивает ноги (низкая орбита). Без линии к Ирине.', 80, [
        E('sigil', 0, 'caster+0,2.3,0', follow=True, id='irina_gaze_eye'),
        orbit_threads('caster+0,0.3,0', 0, 80, 0.55, 2, 10, rise=0.15, period=20, width=0.05, length=12),
    ])
    fx('irina_knots_cast', '«Узлы» — у Ирины (caster = Ирина, 30 тиков; анимация irina_knots, событие knots 0.9 с): нити уходят в землю '
                           'волной r8. Узлы ставит код в 4–6 точках (fx irina_knot_trap в каждой).', 30, [
        E('wave', 14, 'caster+0,0.05,0', duration=16, shape='ring', radius=8, thickness=0.3, followTerrain=True, color='@primary'),
        E('sprites', 14, 'caster+0,0.2,0', duration=6, texture='mote_thread', count=24, rate=5, area=3, speed=0.02, gravity=0.01, spin=20,
          size=[0.24, 0.06], life=16, color='@primary'),
    ])
    fx('irina_knot_trap', '«Узлы» — ловушка (caster = точка на земле, −1 до Fx.stop; срабатывание или конец — код). Узел на земле ВИДЕН, '
                          'пульсирует, над ним колышутся хвосты нитей.', -1, [
        E('sigil', 0, 'caster+0,0.04,0', id='irina_knot_trap'),
        orbit_threads('caster+0,0.15,0', 0, -1, 0.45, 3, 6, rise=0.15, period=24, width=0.04, length=8),
    ])
    fx('irina_knot_snare', '«Узлы» — наступил: опутан 2 с (caster = игрок, follow, 40 тиков). Узел захлопывается, нити обвивают ноги и корпус.', 40, [
        E('flash', 0, 'caster+0,0.3,0', duration=6, size=1.0, color='@primary'),
        orbit_threads('caster+0,0.3,0', 0, 40, 0.5, 4, 22, rise=0.5, period=10, width=0.06, length=10, climb=0.4),
        E('aura', 0, 'caster', duration=40, target='caster', thickness=0.12, pulse=[0.3, 8], color='@primary', motes=8, follow=True),
    ])
    fx('irina_swap', '«Подмена любимого» — у КАЖДОГО из двух игроков (caster = игрок в точке ДО обмена, 20 тиков; второй вызов — после, '
                     'в новой точке): рябь нитей, вспышка. Обмен местами — код; без линии между ними.', 20, [
        E('wave', 0, 'caster+0,1,0', duration=10, shape='sphere', radius=1.2, reverse=True, rim=1.0, color='@primary'),
        orbit_threads('caster', 0, 14, 0.7, 3, 28, rise=0.9, period=8, width=0.05, length=8),
        E('flash', 8, 'caster+0,1,0', duration=10, size=1.4, ring=True, color='@core'),
        E('wave', 10, 'caster+0,0.1,0', duration=12, shape='ring', radius=2.2, thickness=0.2, texture='irina_thread_ring', color='@primary'),
    ])
    fx('irina_puppet', '«Марионетка» — на игроке (caster = игрок, follow, 60 тиков = 3 с или до Fx.stop при уроне по боссу): '
                       'крестовина над головой, нити обвивают тело на трёх высотах. Нитей к Ирине НЕТ — шаги к ней делает код.', 60, [
        E('sigil', 0, 'caster+0,2.6,0', follow=True, id='irina_puppet_cross'),
        orbit_threads('caster+0,0.4,0', 0, 60, 0.5, 2, 14, rise=0.1, period=14, width=0.05, length=10),
        orbit_threads('caster+0,1.0,0', 0, 60, 0.45, 2, -16, rise=0.1, period=12, width=0.05, length=10),
        orbit_threads('caster+0,1.5,0', 0, 60, 0.4, 2, 18, rise=0.1, period=10, width=0.05, length=10),
    ])
    fx('irina_puppet_break', '«Марионетка» снята (урон по боссу / конец; caster = игрок, 16 тиков): нити лопаются, крестовина рассыпается.', 16, [
        E('flash', 0, 'caster+0,1.2,0', duration=8, size=1.4, color='@core'),
        E('sprites', 0, 'caster+0,1.2,0', duration=4, texture='mote_thread', count=24, rate=8, spread=0.4, speed=0.2, gravity=0.02, spin=30,
          size=[0.26, 0.06], life=16, color='@primary'),
    ])

    # ---- переходы фаз, появление, смерть, добивание
    fx('irina_phase2', 'Переход в фазу 2 (66%, caster = Ирина, 50 тиков = анимация irina_phase2 2.5 с; если «Чужое счастье» не играет): '
                       'шляпа надвинута — знак под ней; 1.45 с (`burst`) нити разлетаются кольцом r12.', 50, [
        E('sigil', 0, 'caster+0,0.05,0', id='irina_emblem'),
        orbit_threads('caster', 0, 30, 1.0, 4, 20, rise=1.0, period=12, width=0.08, length=12),
        E('flash', 29, 'caster+0,1.6,0', duration=10, size=2.4, ring=True, color='@primary'),
        E('wave', 29, 'caster+0,0.1,0', duration=20, shape='ring', radius=12, thickness=0.5, texture='irina_thread_ring', spin=2, color='@primary'),
    ])
    fx('irina_phase3', 'Переход в фазу 3 (33%, caster = Ирина, 60 тиков = анимация irina_phase3 3 с). 1.3 с (`rage`) — вспышка, '
                       'красный мир, сфера ярости; на 30 тике код запускает irina_fury (до смерти).', 60, [
        E('tint', 0, 'caster', duration=60, radius=40, color='#5A0A14', strength=0.35, **{'in': ease(20), 'out': ease(24, 'easeInSine')}),
        orbit_threads('caster', 0, 40, 2.0, 6, -18, rise=1.8, period=16, width=0.1, length=16),
        E('flash', 26, 'caster+0,1.6,0', duration=14, size=3.6, rays=10, screen=0.3, ring=True, color='@primary'),
        E('wave', 26, 'caster+0,1,0', duration=20, shape='sphere', radius=6, rim=1.2, color='@primary'),
        E('sprites', 26, 'caster+0,1.4,0', duration=6, texture='mote_thread', count=80, rate=14, spread=1.0, speed=0.3, gravity=0.01, spin=30,
          size=[0.34, 0.08], life=26, color='@primary'),
    ])
    fx('irina_intro', 'Ролик появления (caster = точка появления = Ирина, yaw — её взгляд; 140 тиков = анимация irina_spawn 7 с). '
                      '0–2.6 с — из земли поднимается кокон нитей (она внутри, свернувшись); 2.6 (`unravel`) — нити расплетаются и '
                      'разлетаются, вспышка; 4.6 (`pose`) — поправляет шляпу, знак Ячейки под ней (титр); 5.4 (`flourish`) — взмах посохом: '
                      'кольцо нитей r10; 7.0 — полоса босса.', T_INTRO, [
        E('tint', 0, 'caster', duration=T_INTRO, radius=48, color='#24102E', strength=0.32, **{'in': ease(30), 'out': ease(30, 'easeInSine')}),
        E('sigil', 0, 'caster+0,0.05,0', id='irina_thread_ring', scale=2.2),
        orbit_threads('caster', 0, 54, 0.9, 6, 26, rise=0.2, period=60, width=0.1, length=24, climb=0.9),
        orbit_threads('caster', 6, 48, 0.75, 4, -30, rise=0.2, period=50, width=0.08, length=20, climb=0.9, color='@secondary'),
        E('column', 4, 'caster', duration=50, radius=0.9, height=2.4, fill=0.4, color='@shadow', blend='translucent', **io),
        E('flash', 52, 'caster+0,1.2,0', duration=14, size=3.2, rays=10, screen=0.2, ring=True, color='@core'),
        E('sprites', 52, 'caster+0,1.2,0', duration=6, texture='mote_thread', count=90, rate=16, spread=0.8, speed=0.3, gravity=0.01, spin=30,
          size=[0.34, 0.08], life=30, color='@primary', glow=0.4),
        orbit_threads('caster', 52, 88, 2.2, 3, 8, rise=1.4, period=46, width=0.08, length=20),
        E('sigil', 92, 'caster+0,0.06,0', id='irina_emblem'),
        E('wave', 108, 'caster+0,0.15,0', duration=24, shape='ring', radius=10, thickness=0.5, texture='irina_thread_ring', spin=2, color='@primary'),
        E('flash', 108, 'caster+0,2.4,0', duration=10, size=1.6, color='@primary'),
    ])
    fx('irina_death', 'Ролик смерти (caster = Ирина; 100 тиков = анимация irina_death 5 с). 0 (`hit`) — вспышка; 1.6 (`knees`); '
                      '2.4 (`hat`) — шляпа слетает назад-вправо, 2.9 ложится на землю — пыль (тик 58, там же, где шляпа в анимации); 3.4 (`fall`); 4.2 (`unravel`) — все нити распускаются и уносятся вверх, '
                      'мир серо-лиловый; 5.0 — исчезает.', T_DEATH, [
        E('tint', 0, 'caster', duration=T_DEATH, radius=48, color='#20182A', strength=0.3, saturation=0.5,
          **{'in': ease(20), 'out': ease(24, 'easeInSine')}),
        E('flash', 0, 'caster+0,1.4,0', duration=10, size=2.4, ring=True, color='@primary'),
        orbit_threads('caster', 0, 84, 1.4, 3, 6, rise=0.8, period=40, width=0.07, length=14),
        E('sprites', 58, 'caster+0.9,0.2,-1.0', duration=4, texture='spark_soft', count=14, rate=4, spread=0.4, speed=0.04, gravity=0.01,
          size=[0.2, 0.06], life=20, color='#8C7A92', blend='translucent'),
        E('sprites', 84, 'caster+0,0.6,0', duration=14, texture='mote_thread', count=80, rate=6, spread=1.2, speed=0.04, gravity=-0.03, spin=20,
          sway=0.5, size=[0.34, 0.06], life=40, color='@primary', glow=0.4),
        E('wave', 84, 'caster+0,0.1,0', duration=20, shape='ring', radius=5, thickness=0.4, color='@secondary'),
        E('flash', 98, 'caster+0,0.6,0', duration=10, size=1.8, color='@secondary'),
    ])
    fx('irina_finisher', 'Добивание (caster = Ирина, target = жертва; 52 тика = анимация irina_finisher 2.6 с). 0.2 (`wrap`) — нити '
                         'опутывают жертву (кружат вокруг НЕЁ); 0.8 (`pull_done`) — жертва у Ирины; 1.3 (`pierce`) — крюк посоха: '
                         'красная вспышка; 1.7 (`whisper`) — сердечки, фраза; 2.2 (`kill`) — нити стягиваются и рвутся.', T_FIN, [
        orbit_threads('target', 4, 40, 0.65, 4, 24, rise=1.0, period=12, width=0.08, length=16),
        E('aura', 4, 'target', duration=40, target='target', thickness=0.2, pulse=[0.3, 6], color='@primary', motes=12, follow=True),
        E('flash', 26, 'target+0,1.2,0', duration=8, size=1.4, color='@core', follow=True),
        E('sprites', 26, 'target+0,1.2,0', duration=3, texture='spark_soft', count=24, rate=10, spread=0.4, speed=0.18, gravity=0.02,
          size=[0.14, 0.03], life=12, color=RED_L, follow=True),
        E('sprites', 34, 'target+0,1.6,0', duration=8, texture='mote_heart', count=10, rate=2, spread=0.4, speed=0.02, gravity=-0.01,
          size=[0.2, 0.05], life=26, color='@primary', glow=0.4, follow=True),
        E('wave', 44, 'target+0,1,0', duration=8, shape='sphere', radius=1.4, reverse=True, rim=1.0, color='@primary', follow=True),
        E('flash', 44, 'target+0,1.1,0', duration=10, size=2.4, rays=8, screen=0.2, color='@primary', follow=True),
        E('sprites', 44, 'target+0,1.1,0', duration=4, texture='mote_thread', count=40, rate=12, spread=0.5, speed=0.2, gravity=0.02, spin=40,
          size=[0.3, 0.08], life=20, color='@primary', follow=True),
    ])


# ================================================================== полоса босса (192×36: строки 0–17 пустая, 18–35 полная; BossbarSprite(192, 18, 3, -1))
BP = {k: _c(v) for k, v in {
    'O': '#120A1A', 'o': '#2A1838', 'L': '#E2CDF5', 'l': '#B99BE0', 'm': '#8865BA', 'd': '#55397F',
    'R': '#FF6A5E', 'r': '#E3262F', 'q': '#B0141F', 'Q': '#7A0A16', 'e': '#2A0C1A', 'E': '#1A0812',
    'H': '#433F4E', 'h': '#2B2935', 'C': '#EFE4C8', 'G': '#F2C14A', 'W': '#FFFFFF',
    # заливка фазы 1 — лиловая (зависть), фазы 2 — тёмно-красная (нити); фаза 3 — ярко-красная (R/r/q/Q, ниже ярче)
    '1R': '#F0DCFF', '1r': '#B98AE8', '1q': '#8A5CC4', '1Q': '#5A3690',
    '2R': '#E0485A', '2r': '#A8182E', '2q': '#760C20', '2Q': '#4C0614'}.items()}


def _bar_base(full, phase=1):
    im = Image.new('RGBA', (192, 18), (0, 0, 0, 0))
    a = np.zeros((18, 192, 4), np.uint8)

    def px(x, y, k):
        if 0 <= x < 192 and 0 <= y < 18:
            a[y, x] = BP[k]
    def FK(k):                                               # цвет заливки по фазе (как у остальных боссов)
        return ('%d%s' % (phase, k)) if phase in (1, 2) else k
    x0, x1 = 3, 188
    for x in range(x0, x1 + 1):
        px(x, 7, 'O'); px(x, 16, 'O')
        px(x, 8, 'l'); px(x, 15, 'd')
        for y in range(9, 15):
            if full:
                k = 'R' if y == 9 else 'r' if y <= 11 else 'q' if y <= 13 else 'Q'
                k = FK(k)
            else:
                k = 'o' if y == 9 else 'e' if y <= 13 else 'E'
            px(x, y, k)
        if full and (x % 6 in (0, 1)):                       # витая нить в заливке
            px(x, 11 + (x // 6) % 2, FK('R'))
            px(x + 1, 12 - (x // 6) % 2, FK('q'))
    # торцы-ромбы
    for (cx, sgn) in ((2, 1), (189, -1)):
        for dy in range(-4, 5):
            w = 4 - abs(dy)
            for dx in range(-w, w + 1):
                k = 'O' if abs(dx) == w or abs(dy) == 4 else ('L' if dy < 0 else 'm')
                px(cx + dx, 11 + dy, k)
        px(cx, 11, 'r')
    # центр: шляпа ведьмы с крестом и завитки нити
    hat = ['......hh......', '.....hHHh.....', '....hHHHh.....', '....hHCHh.....', '...hHCCCHh....', '...hHHCHHh....', '..hlllllllh...',
           'hhhhhhhhhhhhhh']
    for j, row in enumerate(hat):
        for i, ch in enumerate(row):
            if ch != '.':
                px(89 + i, j, ch)
    for sgn in (-1, 1):                                      # завитки нити по сторонам
        cx = 96 + sgn * 18
        for t in np.linspace(0, 2.6 * math.pi, 40):
            r = 4.5 - t * 0.5
            x = int(round(cx + sgn * r * math.cos(t)))
            y = int(round(4 + r * math.sin(t) * 0.8))
            if 0 <= y <= 6:
                px(x, y, 'r')
        for x in range(96 + sgn * 9, 96 + sgn * 30, sgn):
            px(x, 6, 'q' if x % 3 else 'r')
    if phase >= 2:                                           # красные стежки по рамке и узелки-сердца над ней
        for x in range(6, 186, 4):
            px(x, 8, 'r'); px(x + 2, 15, 'r')
        for cx in (30, 58, 134, 162):
            for (dx, dy) in ((-1, 0), (1, 0), (-2, 1), (0, 1), (2, 1), (-1, 2), (0, 2), (1, 2), (0, 3)):
                px(cx + dx, 3 + dy, 'r')
            px(cx, 6, 'q')
    if phase >= 3:                                           # рамка рваная: лиловое местами выбито, нити торчат
        rng = random.Random(27)
        for x in range(4, 188):
            if rng.random() < 0.16:
                px(x, 8, 'O')
            if rng.random() < 0.1:
                px(x, 15, 'O')
        for x in range(10, 184, 13):
            px(x, 6, 'r'); px(x + 1, 5, 'R')
    im = Image.fromarray(a, 'RGBA')
    return im


def bossbars():
    out = {}
    for ph, name in ((1, 'irina_bossbar'), (2, 'irina_bossbar_p2'), (3, 'irina_bossbar_p3')):
        bar = Image.new('RGBA', (192, 36), (0, 0, 0, 0))
        bar.paste(_bar_base(False, ph), (0, 0))
        bar.paste(_bar_base(True, ph), (0, 18))
        if ph == 3:                                          # фаза 3 — заливка ярче
            arr = np.asarray(bar).copy()
            m = (arr[18:, :, 0] == BP['q'][0]) & (arr[18:, :, 1] == BP['q'][1])
            arr[18:][m] = BP['r']
            bar = Image.fromarray(arr, 'RGBA')
        p = os.path.join(A, 'textures', 'gui', 'sprites', 'boss_bars', name + '.png')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        bar.save(p)
        WRITTEN.append('textures/gui/sprites/boss_bars/%s.png' % name)
        out[ph] = bar
    # пульс фазы 2: стежки и узелки ярче (рисовать поверх _p2 с альфой 0.5+0.5·sin, пока на арене есть пары)
    arr = np.asarray(out[2]).copy()
    for src, dst in ((BP['r'], BP['R']), (BP['q'], BP['r']), (BP['l'], BP['L'])):
        m = (arr[..., 0] == src[0]) & (arr[..., 1] == src[1]) & (arr[..., 2] == src[2]) & (arr[..., 3] > 0)
        arr[m] = dst
    Image.fromarray(arr, 'RGBA').save(os.path.join(A, 'textures', 'gui', 'sprites', 'boss_bars', 'irina_bossbar_p2_pulse.png'))
    WRITTEN.append('textures/gui/sprites/boss_bars/irina_bossbar_p2_pulse.png')
    # фаза 3: 8 кадров по 192×14 — нити хлещут над рамкой (кадр k — строки 14k…14k+13)
    FH, NF = 14, 8
    fa = np.zeros((FH * NF, 192, 4), np.uint8)
    rng = random.Random(7)
    whips = [(rng.uniform(8, 184), rng.uniform(5, 12), rng.uniform(0, 6.28), rng.choice((-1, 1))) for _ in range(14)]
    for k in range(NF):
        t = k / NF * 2 * math.pi
        for (x0, L, p, sgn) in whips:
            if 80 <= x0 <= 112:
                continue
            for j in range(int(L * 3)):
                u = j / (L * 3)
                y = FH - 1 - u * L * (0.7 + 0.3 * math.sin(t + p))
                x = x0 + sgn * math.sin(u * 3 + t + p) * 3 * u
                xi, yi = int(round(x)), int(round(y))
                if 0 <= xi < 192 and 0 <= yi < FH:
                    fa[k * FH + yi, xi] = BP['R'] if u > 0.7 else BP['r'] if u > 0.3 else BP['q']
    Image.fromarray(fa, 'RGBA').save(os.path.join(A, 'textures', 'gui', 'sprites', 'boss_bars', 'irina_bossbar_p3_threads.png'))
    WRITTEN.append('textures/gui/sprites/boss_bars/irina_bossbar_p3_threads.png')
    b = np.asarray(out[1]).copy()[:18]
    fl = np.zeros_like(b)
    fl[..., :3] = (255, 224, 230)
    fl[..., 3] = np.where(b[..., 3] > 0, 255, 0)
    Image.fromarray(fl, 'RGBA').save(os.path.join(A, 'textures', 'gui', 'sprites', 'boss_bars', 'irina_bossbar_flash.png'))
    WRITTEN.append('textures/gui/sprites/boss_bars/irina_bossbar_flash.png')
    return out, Image.fromarray(fa, 'RGBA')


# ================================================================== титры (1024×192, две строки)
FONT_CYR = os.path.join(HERE, 'fonts', 'CormorantGaramond-BoldItalic-cyrillic.woff')
FONT_LAT = os.path.join(HERE, 'fonts', 'CormorantGaramond-BoldItalic-latin.woff')


def draw_text(mask, xy, text, size):
    """Текст по символам: кириллица — кириллическим шрифтом, остальное (цифры, латиница, знаки) — латинским."""
    fc, fl = ImageFont.truetype(FONT_CYR, size), ImageFont.truetype(FONT_LAT, size)
    d = ImageDraw.Draw(mask)
    x, y = xy
    for ch in text:
        f = fc if 'Ѐ' <= ch <= 'ӿ' else fl
        d.text((x, y), ch, font=f, fill=255)
        x += f.getlength(ch)
    return x


def text_width(text, size):
    fc, fl = ImageFont.truetype(FONT_CYR, size), ImageFont.truetype(FONT_LAT, size)
    return sum((fc if 'Ѐ' <= ch <= 'ӿ' else fl).getlength(ch) for ch in text)


def title(name, texts):
    """texts: [(lang, строка1[, строка2])]. Лиловое «серебро» с тёмным контуром и красным ореолом нитей; под надписью — красная нить
    с узелком-сердцем."""
    grad_c = [_c('#F6EEFF'), _c('#E2CDF5'), _c('#B99BE0'), _c('#7A55AE')]
    for tt in texts:
        lang, l1 = tt[0], tt[1]
        l2 = tt[2] if len(tt) > 2 else None
        S = 2
        Wd, Hd = 1024 * S, 192 * S
        mask = Image.new('L', (Wd, Hd), 0)
        sz1 = (70 if l2 else 84) * S
        while text_width(l1, sz1) > Wd * 0.9:
            sz1 -= 2
        y1 = (8 if l2 else 30) * S
        draw_text(mask, ((Wd - text_width(l1, sz1)) / 2, y1), l1, sz1)
        if l2:
            sz2 = 40 * S
            draw_text(mask, ((Wd - text_width(l2, sz2)) / 2, 100 * S), l2, sz2)
        m = np.asarray(mask, np.float32) / 255
        ys = np.where(m.max(1) > 0)[0]
        top, bot = ys.min(), ys.max()
        t = np.clip((np.arange(Hd)[:, None] - top) / max(1, bot - top), 0, 1)
        grad = np.zeros((Hd, 1, 3), np.float32)
        stops = [(0.0, grad_c[0]), (0.4, grad_c[1]), (0.75, grad_c[2]), (1.0, grad_c[3])]
        for k in range(3):
            (t0, c0), (t1, c1) = stops[k], stops[k + 1]
            sel = (t >= t0) & (t <= t1)
            u = (t - t0) / (t1 - t0)
            for chn in range(3):
                grad[..., chn] = np.where(sel, c0[chn] + (c1[chn] - c0[chn]) * u, grad[..., chn])
        rgb = np.broadcast_to(grad, (Hd, Wd, 3))
        outline = np.asarray(mask.filter(ImageFilter.MaxFilter(9)), np.float32) / 255
        halo = np.asarray(mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(20 * S)), np.float32) / 255
        o = np.zeros((Hd, Wd, 4), np.float32)
        o[..., :3] = _c(RED)[:3]
        o[..., 3] = np.clip(halo * 1.3, 0, 0.7)
        ob = np.array(_c('#1A1024')[:3], np.float32)
        o[..., :3] = o[..., :3] * (1 - outline[..., None]) + ob * outline[..., None]
        o[..., 3] = np.maximum(o[..., 3], outline)
        o[..., :3] = o[..., :3] * (1 - m[..., None]) + rgb * m[..., None]
        o[..., 3] = np.maximum(o[..., 3], m)
        o[..., 3] *= 255
        img = Image.fromarray(o.clip(0, 255).astype(np.uint8), 'RGBA').resize((1024, 192), Image.LANCZOS)
        d = ImageDraw.Draw(img)
        y = 172 if l2 else 156
        pts = [(x, y + 3 * math.sin(x / 9.0)) for x in range(170, 855)]
        for i in range(len(pts) - 1):
            k = 1 - abs(pts[i][0] - 512) / 342
            a_ = int(255 * min(1, k * 2.4))
            d.line([pts[i], pts[i + 1]], fill=_c(RED, a_), width=2)
        hp = heart_pts(512, y, 0.55)
        d.polygon(hp, fill=_c(RED))
        d.line(hp, fill=_c('#1A1024'), width=1)
        p = os.path.join(A, 'textures', 'gui', 'title', '%s_%s.png' % (name, lang))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        img.save(p)
        WRITTEN.append('textures/gui/title/%s_%s.png' % (name, lang))


def titles():
    title('irina', [('ru', 'Ирина, Ведьма Ревности', 'Глава 2 Ячейки Культа'),
                    ('en', 'Irina, Witch of Jealousy', "Head of the Cult's Second Cell")])
    title('irina_happiness', [('ru', 'Чужое счастье'), ('en', "Someone Else's Happiness")])
    title('irina_only_mine', [('ru', 'Только мой'), ('en', 'Mine Alone')])


# ================================================================== иконки статусов (18×18)
def icons():
    def mark(d, S):
        d.ellipse([S * 0.05, S * 0.05, S * 0.95, S * 0.95], fill=_c('#24102E'), outline=_c(LIL), width=int(S * 0.07))
        d.polygon(heart_pts(S / 2, S * 0.53, S * 0.021), fill=_c(RED))
        d.ellipse([S * 0.33, S * 0.42, S * 0.67, S * 0.6], fill=_c('#FFE0E6'))
        d.ellipse([S * 0.44, S * 0.42, S * 0.56, S * 0.6], fill=_c('#24102E'))
        d.line([S * 0.2, S * 0.8, S * 0.8, S * 0.3], fill=_c(RED_D), width=int(S * 0.05))

    def bond(d, S):
        d.ellipse([S * 0.05, S * 0.05, S * 0.95, S * 0.95], fill=_c('#24102E'), outline=_c(LIL), width=int(S * 0.07))
        for cx in (0.38, 0.62):
            d.ellipse([S * (cx - 0.2), S * 0.3, S * (cx + 0.2), S * 0.7], outline=_c(RED), width=int(S * 0.08))
        d.rectangle([S * 0.47, S * 0.27, S * 0.53, S * 0.36], fill=_c('#24102E'))

    def stolen(d, S):
        d.ellipse([S * 0.05, S * 0.05, S * 0.95, S * 0.95], fill=_c('#24102E'), outline=_c(LIL), width=int(S * 0.07))
        cx, cy = S / 2, S / 2
        d.polygon([(cx, S * 0.16), (cx + S * 0.08, cy - S * 0.08), (S * 0.84, cy), (cx + S * 0.08, cy + S * 0.08), (cx, S * 0.84),
                   (cx - S * 0.08, cy + S * 0.08), (S * 0.16, cy), (cx - S * 0.08, cy - S * 0.08)], fill=_c(HAPPY))
        for k in range(3):
            y = S * (0.3 + 0.2 * k)
            d.line([S * 0.18, y + S * 0.12, S * 0.82, y - S * 0.12], fill=_c(RED), width=int(S * 0.07))
    def gaze(d, S):
        d.ellipse([S * 0.05, S * 0.05, S * 0.95, S * 0.95], fill=_c('#24102E'), outline=_c(LIL), width=int(S * 0.07))
        d.ellipse([S * 0.18, S * 0.36, S * 0.82, S * 0.64], fill=_c('#E8D8F0'))
        d.ellipse([S * 0.4, S * 0.36, S * 0.6, S * 0.64], fill=_c(RED))
        d.line([S * 0.15, S * 0.78, S * 0.85, S * 0.72], fill=_c(RED), width=int(S * 0.06))

    def snared(d, S):
        d.ellipse([S * 0.05, S * 0.05, S * 0.95, S * 0.95], fill=_c('#24102E'), outline=_c(LIL), width=int(S * 0.07))
        for k in range(3):
            y = S * (0.32 + 0.18 * k)
            d.arc([S * 0.2, y - S * 0.1, S * 0.8, y + S * 0.1], 0, 360, fill=_c(RED), width=int(S * 0.07))
        d.ellipse([S * 0.42, S * 0.42, S * 0.58, S * 0.58], fill=_c(RED))

    def puppet_ic(d, S):
        d.ellipse([S * 0.05, S * 0.05, S * 0.95, S * 0.95], fill=_c('#24102E'), outline=_c(LIL), width=int(S * 0.07))
        d.rectangle([S * 0.22, S * 0.24, S * 0.78, S * 0.32], fill=_c('#C8B0E6'))
        d.rectangle([S * 0.46, S * 0.16, S * 0.54, S * 0.44], fill=_c('#C8B0E6'))
        for x in (0.26, 0.5, 0.74):
            d.line([S * x, S * 0.32, S * x, S * 0.62], fill=_c(RED), width=int(S * 0.05))
        d.ellipse([S * 0.42, S * 0.58, S * 0.58, S * 0.72], fill=_c('#E8D8F0'))
        d.line([S * 0.5, S * 0.72, S * 0.5, S * 0.84], fill=_c('#E8D8F0'), width=int(S * 0.06))
    for name, fn in (('irina_jealousy_mark', mark), ('irina_thread_bond', bond), ('irina_stolen_happiness', stolen),
                     ('irina_jealous_gaze', gaze), ('irina_snared', snared), ('irina_puppet', puppet_ic)):
        F._icon(18, fn, 'textures/mob_effect/%s.png' % name, k=8, crisp=True)
        WRITTEN.append('textures/mob_effect/%s.png' % name)


# ================================================================== lang и звуки
LANG = {
    'entity.pohsmp_core.irina': ('Ирина, Ведьма Ревности', 'Irina, Witch of Jealousy'),
    'item.pohsmp_core.irina_staff': ('Посох Ревности', 'Staff of Jealousy'),
    'ui.pohsmp_core.irina.title': ('Ирина, Ведьма Ревности', 'Irina, Witch of Jealousy'),
    'ui.pohsmp_core.irina.epithet': ('Глава 2 Ячейки Культа', "Head of the Cult's Second Cell"),
    'ui.pohsmp_core.irina.subtitle': ('Глава 2 Ячейки Культа', "Head of the Cult's Second Cell"),
    'ui.pohsmp_core.irina.mark': ('%s — предмет ревности Ирины', "%s is the object of Irina's jealousy"),
    'ui.pohsmp_core.irina.mark_self': ('Вы — предмет ревности: Ирина охотится за вами', 'You are the object of jealousy: Irina is hunting you'),
    'ui.pohsmp_core.irina.mark_others': ('Пока метка на %s, ваш урон по Ирине вдвое слабее', 'While %s is marked, your damage to Irina is halved'),
    'ui.pohsmp_core.irina.phase2': ('Красные нити связывают вас попарно…', 'Red threads bind you in pairs…'),
    'ui.pohsmp_core.irina.bond': ('Нить связала вас с %s: урон делится на двоих. Не расходитесь дальше 12 блоков!',
                                  'A thread binds you to %s: damage is shared. Stay within 12 blocks!'),
    'ui.pohsmp_core.irina.bond_strain': ('Нить натянута — вернитесь к %s!', 'The thread is taut — get back to %s!'),
    'ui.pohsmp_core.irina.bond_snap': ('Нить рвётся!', 'The thread snaps!'),
    'ui.pohsmp_core.irina.phase3': ('Ярость ревности!', 'Jealous Fury!'),
    'ui.pohsmp_core.irina.steal': ('Ирина крадёт ваше счастье: %s', 'Irina steals your happiness: %s'),
    'ui.pohsmp_core.irina.whip_warn': ('Нити поднимаются — отойдите от Ирины!', 'The threads rise — get away from Irina!'),
    'ui.pohsmp_core.irina.happiness': ('Чужое счастье', "Someone Else's Happiness"),
    'ui.pohsmp_core.irina.happiness_warn': ('Ирина тянется к чужому счастью…', "Irina reaches for others' happiness…"),
    'ui.pohsmp_core.irina.only_mine': ('Только мой', 'Mine Alone'),
    'ui.pohsmp_core.irina.only_mine_warn': ('%s в коконе! Разорвите нити уроном — 4 секунды!', '%s is cocooned! Break the threads with damage — 4 seconds!'),
    'ui.pohsmp_core.irina.only_mine_broken': ('Кокон разорван!', 'The cocoon is torn!'),
    'ui.pohsmp_core.irina.only_mine_crush': ('Нити сжимаются…', 'The threads tighten…'),
    'ui.pohsmp_core.irina.finisher_whisper': ('Теперь ты только мой.', 'Now you are mine alone.'),
    'ui.pohsmp_core.irina.death': ('Нити Ирины распускаются', "Irina's threads unravel"),
    'effect.pohsmp_core.jealousy_mark': ('Предмет ревности', 'Object of Jealousy'),
    'effect.pohsmp_core.jealousy_mark.description': ('Ирина охотится за вами; урон остальных по ней вдвое слабее, пока метка на вас.',
                                                     "Irina hunts you; others deal half damage to her while you are marked."),
    'effect.pohsmp_core.thread_bond': ('Связь нитью', 'Thread Bond'),
    'effect.pohsmp_core.thread_bond.description': ('Урон делится с напарником; дальше 12 блоков нить рвётся и ранит обоих.',
                                                   'Damage is shared with your partner; beyond 12 blocks the thread snaps and hurts you both.'),
    'effect.pohsmp_core.stolen_happiness': ('Украденное счастье', 'Stolen Happiness'),
    'effect.pohsmp_core.stolen_happiness.description': ('Ирина забрала ваши полезные эффекты себе.', 'Irina took your beneficial effects for herself.'),
    'ui.pohsmp_core.irina.gaze': ('Не смотрите на неё — ревнивый взгляд замедляет!', 'Don\'t stare at her — the jealous gaze slows you!'),
    'ui.pohsmp_core.irina.knots_warn': ('На земле узлы из нитей — не наступайте!', 'Thread knots on the ground — don\'t step on them!'),
    'ui.pohsmp_core.irina.snared': ('Вы опутаны нитями!', 'You are snared by threads!'),
    'ui.pohsmp_core.irina.swap': ('Подмена любимого: вы поменялись местами с %s', 'Beloved\'s Switch: you swapped places with %s'),
    'ui.pohsmp_core.irina.puppet': ('%s — марионетка Ирины! Бейте её, чтобы оборвать нити', '%s is Irina\'s puppet! Hit her to cut the strings'),
    'ui.pohsmp_core.irina.puppet_self': ('Вы — марионетка: ноги сами несут вас к Ирине…', 'You are a puppet: your feet carry you to Irina…'),
    'ui.pohsmp_core.irina.puppet_break': ('Нити марионетки оборваны', 'The puppet strings are cut'),
    'ui.pohsmp_core.irina.spell.gaze': ('Ревнивый взгляд', 'Jealous Gaze'),
    'ui.pohsmp_core.irina.spell.knots': ('Узлы', 'Knots'),
    'ui.pohsmp_core.irina.spell.swap': ('Подмена любимого', 'Beloved\'s Switch'),
    'ui.pohsmp_core.irina.spell.puppet': ('Марионетка', 'Marionette'),
    'effect.pohsmp_core.jealous_gaze': ('Ревнивый взгляд', 'Jealous Gaze'),
    'effect.pohsmp_core.jealous_gaze.description': ('Вы смотрели на Ирину слишком долго: нить на ногах замедляет вас.',
                                                    'You stared at Irina too long: a thread on your legs slows you.'),
    'effect.pohsmp_core.thread_snare': ('Опутан', 'Snared'),
    'effect.pohsmp_core.thread_snare.description': ('Узел из нитей держит вас на месте.', 'A thread knot holds you in place.'),
    'effect.pohsmp_core.marionette': ('Марионетка', 'Marionette'),
    'effect.pohsmp_core.marionette.description': ('Вы не управляете собой и идёте к Ирине; урон по ней обрывает нити.',
                                                  'You lose control and walk toward Irina; damaging her cuts the strings.'),
    'subtitles.pohsmp_core.irina.gaze': ('Ревнивый взгляд', 'Jealous gaze'),
    'subtitles.pohsmp_core.irina.knots': ('Нити уходят в землю', 'Threads sink into the ground'),
    'subtitles.pohsmp_core.irina.snare': ('Узел затягивается', 'Knot tightens'),
    'subtitles.pohsmp_core.irina.swap': ('Подмена', 'Switch'),
    'subtitles.pohsmp_core.irina.puppet': ('Нити марионетки', 'Puppet strings'),
    'death.attack.pohsmp_core.irina_finisher': ('%1$s теперь только её — Ирины, Ведьмы Ревности', '%1$s now belongs to Irina, Witch of Jealousy alone'),
    'death.attack.pohsmp_core.irina_threads': ('%1$s разорван красными нитями', '%1$s was torn apart by red threads'),
    'death.attack.pohsmp_core.irina_cocoon': ('%1$s задушен коконом ревности', '%1$s was smothered in a cocoon of jealousy'),
    'subtitles.pohsmp_core.irina.spawn': ('Нити расплетаются', 'Threads unravel'),
    'subtitles.pohsmp_core.irina.death': ('Ирина падает', 'Irina falls'),
    'subtitles.pohsmp_core.irina.death_final': ('Нити распускаются', 'Threads come undone'),
    'subtitles.pohsmp_core.irina.mark': ('Ревнивый взгляд', 'Jealous gaze'),
    'subtitles.pohsmp_core.irina.bind': ('Нити связывают', 'Threads bind'),
    'subtitles.pohsmp_core.irina.snap': ('Нить рвётся', 'Thread snaps'),
    'subtitles.pohsmp_core.irina.steal': ('Ирина крадёт эффекты', 'Irina steals effects'),
    'subtitles.pohsmp_core.irina.whip': ('Хлещут нити', 'Threads lash'),
    'subtitles.pohsmp_core.irina.cocoon': ('Кокон из нитей', 'Thread cocoon'),
    'subtitles.pohsmp_core.irina.cocoon_break': ('Кокон разорван', 'Cocoon torn'),
    'subtitles.pohsmp_core.irina.cocoon_crush': ('Кокон сжимается', 'Cocoon crushes'),
    'subtitles.pohsmp_core.irina.happiness': ('Чужое счастье', "Someone Else's Happiness"),
    'subtitles.pohsmp_core.irina.phase': ('Ирина ревнует', 'Irina seethes'),
    'subtitles.pohsmp_core.irina.finisher': ('Крюк посоха пронзает', 'Staff hook pierces'),
    'subtitles.pohsmp_core.irina.staff': ('Взмах посоха', 'Staff swing'),
    'subtitles.pohsmp_core.music.irina': ('Музыка: Ирина', 'Music: Irina'),
}


def S_(name, **kw):
    o = {'name': name}
    o.update(kw)
    return o


SOUNDS = {
    'irina.spawn': [S_('irons_spellbooks:raise_dead_start', pitch=1.3, volume=1.3)],
    'irina.death': [S_('irons_spellbooks:dead_king/fake_death', pitch=1.4)],
    'irina.death_final': [S_('irons_spellbooks:soulcaller_toll_failure', pitch=1.2)],
    'irina.mark': [S_('irons_spellbooks:heartstop_cast', pitch=1.2)],
    'irina.bind': [S_('irons_spellbooks:charge_chains', pitch=1.35)],
    'irina.snap': [S_('irons_spellbooks:blood_explosion', pitch=1.5), S_('irons_spellbooks:blood_explosion', pitch=1.7)],
    'irina.steal': [S_('irons_spellbooks:magic_spell_reverse_3', pitch=1.1)],
    'irina.whip': [S_('irons_spellbooks:hellrazor_swing_1', pitch=1.2), S_('irons_spellbooks:hellrazor_swing_2', pitch=1.2),
                   S_('irons_spellbooks:hellrazor_swing_3', pitch=1.2)],
    'irina.cocoon': [S_('irons_spellbooks:abyssal_shroud_cast', pitch=1.3)],
    'irina.cocoon_break': [S_('irons_spellbooks:blood_explosion', pitch=1.8)],
    'irina.cocoon_crush': [S_('irons_spellbooks:devour', pitch=1.2)],
    'irina.happiness': [S_('irons_spellbooks:dark_magic_buff_03_custom_1', pitch=0.8, volume=1.4)],
    'irina.phase': [S_('irons_spellbooks:void_tentacles_start', pitch=1.3)],
    'irina.finisher': [S_('irons_spellbooks:skewer', pitch=1.1)],
    'irina.staff': [S_('irons_spellbooks:shadow_slash', pitch=1.2)],
    'irina.gaze': [S_('irons_spellbooks:planar_sight_cast', pitch=1.3)],
    'irina.knots': [S_('irons_spellbooks:root_start', pitch=1.3)],
    'irina.snare': [S_('irons_spellbooks:root_emerge', pitch=1.4)],
    'irina.swap': [S_('irons_spellbooks:abyssal_teleport', pitch=1.3)],
    'irina.puppet': [S_('irons_spellbooks:charge_chains', pitch=1.6)],
}


def lang_sounds():
    for i, name in enumerate(('ru_ru', 'en_us')):
        p = os.path.join(A, 'lang', name + '.json')
        d = json.load(open(p, encoding='utf-8'))
        for k, v in LANG.items():
            d[k] = v[i]
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')
        WRITTEN.append('lang/%s.json (+%d ключей)' % (name, len(LANG)))
    p = os.path.join(A, 'sounds.json')
    d = json.load(open(p, encoding='utf-8'))
    for k, v in SOUNDS.items():
        d[k] = {'subtitle': 'subtitles.pohsmp_core.' + k, 'sounds': v}
    d['music.irina'] = {'category': 'record', 'subtitle': 'subtitles.pohsmp_core.music.irina',
                        'comment': 'ЗАГЛУШКА до трека владельца (Iron\'s). Трек владельца — pohsmp_core:music/irina (stream).',
                        'sounds': [S_('irons_spellbooks:dead_king/music/second_phase_melody_alt', stream=True, volume=0.6)]}
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write('\n')
    WRITTEN.append('sounds.json (+%d событий)' % (len(SOUNDS) + 1))


# ================================================================== проверочные кадры (2D)
def _tint(name, color, size, bg=None):
    im = Image.open(os.path.join(A, 'textures', 'sigil', name + '.png')).convert('RGBA').resize((size, size), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    c = np.array(_c(color)[:3], np.float32)
    o = np.zeros_like(a)
    o[..., :3] = c
    o[..., 3] = a[..., 3]
    return Image.fromarray(o.astype(np.uint8), 'RGBA')


def _glow(img, r=8, k=1.0):
    g = img.filter(ImageFilter.GaussianBlur(r))
    a = np.asarray(g).astype(np.float32)
    a[..., 3] = np.clip(a[..., 3] * k, 0, 255)
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


def _font(sz):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', sz) if os.path.exists(
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf') else ImageFont.load_default()


def _paste(bg, im, xy):
    bg.alpha_composite(_glow(im, 10, 1.4), xy)
    bg.alpha_composite(im, xy)


def sheet_fx():
    W, H = 1800, 1440
    bg = Image.new('RGBA', (W, H), _c('#120C18'))
    d = ImageDraw.Draw(bg)
    cells = [('irina_mark', RED, 'Предмет ревности', 'метка над головой (fx irina_mark)'),
             ('irina_knot_1', RED, 'Пара №1', 'irina_bond_1 — сердце'), ('irina_knot_2', RED, 'Пара №2', 'луна'),
             ('irina_knot_3', RED, 'Пара №3', 'звезда'), ('irina_knot_4', RED, 'Пара №4', 'ромб'),
             ('irina_knot_break', RED_L, 'Разрыв нити', 'irina_bond_snap'),
             ('irina_thread_ring', RED, 'Кольцо петель', 'под ногами: метка, пара, кокон'),
             ('irina_emblem', LIL_L, 'Знак 2 Ячейки', 'появление, фазы'),
             ('mote_thread', RED, 'Частицы', 'mote_thread / mote_heart / mote_glee')]
    extra = [('irina_knot_trap', RED, '«Узлы»', 'ловушка на земле'), ('irina_gaze_eye', RED, '«Ревнивый взгляд»', 'метка над головой'),
             ('irina_puppet_cross', RED, '«Марионетка»', 'крестовина над игроком')]
    for i, (n, c, lab, sub) in enumerate(cells):
        x, y = 40 + (i % 5) * 340, 40 + (i // 5) * 470
        _paste(bg, _tint(n, c, 300), (x, y))
        if n == 'mote_thread':
            _paste(bg, _tint('mote_heart', RED, 120), (x + 20, y + 170))
            _paste(bg, _tint('mote_glee', HAPPY, 120), (x + 160, y + 170))
        d.text((x, y + 320), lab, font=_font(26), fill=_c('#EFE6F6'))
        d.text((x, y + 356), sub, font=_font(18), fill=_c('#A596B8'))
    for i, (n, c, lab, sub) in enumerate(extra):
        x, y = 40 + i * 340, 980
        _paste(bg, _tint(n, c, 300), (x, y))
        d.text((x, y + 320), lab, font=_font(26), fill=_c('#EFE6F6'))
        d.text((x, y + 356), sub, font=_font(18), fill=_c('#A596B8'))
    x, y = 40 + 4 * 340, 40 + 470
    _paste(bg, _tint('irina_happiness', LIL_L, 340), (x - 20, y - 20))
    d.text((x, y + 320), '«Чужое счастье»', font=_font(26), fill=_c('#EFE6F6'))
    d.text((x, y + 356), 'печать r24 (irina_happiness)', font=_font(18), fill=_c('#A596B8'))
    bg.convert('RGB').save(os.path.join(MEDIA, 't27_fx.jpg'), quality=90)
    print('wrote docs/media/t27_fx.jpg')


def sheet_scenes():
    """Сверху на арену: как выглядят особые моменты (схема, масштаб 1 бл. = 14 px)."""
    W, H = 1800, 900
    bg = Image.new('RGBA', (W, H), _c('#120C18'))
    d = ImageDraw.Draw(bg)
    k = 14
    # 1) «Чужое счастье»: печать r24, искры над всей печатью, воронка к центру
    cx, cy = 450, 450
    _paste(bg, _tint('irina_happiness', LIL_L, 2 * R_HAPPY * k), (cx - R_HAPPY * k, cy - R_HAPPY * k))
    rng = random.Random(1)
    for _ in range(260):
        r = R_HAPPY * k * math.sqrt(rng.random())
        a = rng.random() * 6.28
        a2 = a + (1 - r / (R_HAPPY * k)) * 1.2
        x, y = cx + r * math.cos(a2), cy + r * math.sin(a2)
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=_c(HAPPY, 220))
    for (px_, py_) in ((cx + 160, cy - 120), (cx - 220, cy + 60), (cx + 40, cy + 230)):
        d.ellipse([px_ - 8, py_ - 8, px_ + 8, py_ + 8], fill=_c('#66CCFF'))
    d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=_c(RED))
    d.text((40, 20), '«Чужое счастье» — сверху: золотые искры над всей печатью r24 стягиваются воронкой к Ирине (красная точка);'
                     ' игроки (голубые) — без линий к ней', font=_font(18), fill=_c('#EFE6F6'))
    # 2) фаза 2: две пары с одинаковыми знаками, без линии
    ox = 1000
    pairs = [((ox + 120, 260), (ox + 330, 340), 1), ((ox + 200, 600), (ox + 420, 520), 2), ((ox + 560, 220), (ox + 700, 380), 3)]
    for (a, b, n) in pairs:
        for (x, y) in (a, b):
            _paste(bg, _tint('irina_thread_ring', RED, 40), (int(x - 20), int(y - 20)))
            _paste(bg, _tint('irina_knot_%d' % n, RED, 70), (int(x - 35), int(y - 85)))
            d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=_c('#66CCFF'))
    d.text((ox, 700), 'Фаза 2: пары узнаются по одинаковому знаку над головой — линии между ними нет', font=_font(18), fill=_c('#EFE6F6'))
    # 3) кокон «Только мой» и хлёст
    _paste(bg, _tint('irina_thread_ring', RED, 120), (ox + 520, 560))
    d.text((ox + 470, 690), 'кокон: нити вокруг жертвы', font=_font(16), fill=_c('#A596B8'))
    bg.convert('RGB').save(os.path.join(MEDIA, 't27_special_fx.jpg'), quality=90)
    print('wrote docs/media/t27_special_fx.jpg')


def sheet_ui(bars, threads):
    W, H = 1400, 1000
    bg = Image.new('RGBA', (W, H), _c('#1A1324'))
    d = ImageDraw.Draw(bg)
    y = 30
    for ph in (1, 2, 3):
        bar = bars[ph]
        for half, lab in ((0, 'пусто'), (1, 'полно')):
            im = bar.crop((0, 18 * half, 192, 18 * half + 18)).resize((192 * 4, 18 * 4), Image.NEAREST)
            if ph == 3 and half == 1:
                fr = threads.crop((0, 0, 192, 14)).resize((192 * 4, 14 * 4), Image.NEAREST)
                bg.alpha_composite(fr, (40, y - 20))
            bg.alpha_composite(im, (40, y))
            d.text((830, y + 24), 'фаза %d — %s' % (ph, lab), font=_font(20), fill=_c('#EFE6F6'))
            y += 84
    for i, n in enumerate(('irina_ru', 'irina_en')):
        t = Image.open(os.path.join(A, 'textures', 'gui', 'title', n + '.png')).convert('RGBA').resize((640, 120), Image.LANCZOS)
        bg.alpha_composite(t, (40 + i * 660, 560))
    for i, n in enumerate(('irina_happiness_ru', 'irina_only_mine_ru', 'irina_happiness_en', 'irina_only_mine_en')):
        t = Image.open(os.path.join(A, 'textures', 'gui', 'title', n + '.png')).convert('RGBA').resize((640, 120), Image.LANCZOS)
        bg.alpha_composite(t, (40 + (i % 2) * 660, 690 + (i // 2) * 120))
    for i, n in enumerate(('irina_jealousy_mark', 'irina_thread_bond', 'irina_stolen_happiness', 'irina_jealous_gaze', 'irina_snared',
                           'irina_puppet')):
        ic = Image.open(os.path.join(A, 'textures', 'mob_effect', n + '.png')).convert('RGBA').resize((72, 72), Image.NEAREST)
        bg.alpha_composite(ic, (1150, 40 + i * 110))
        d.text((1150, 118 + i * 110), n.replace('irina_', ''), font=_font(14), fill=_c('#A596B8'))
    bg.convert('RGB').save(os.path.join(MEDIA, 't27_ui.jpg'), quality=92)
    print('wrote docs/media/t27_ui.jpg')


def run(mod, args):
    global M
    M = mod
    textures()
    sigils()
    effects()
    bars, threads = bossbars()
    titles()
    icons()
    lang_sounds()
    if '--shots' in args:
        os.makedirs(MEDIA, exist_ok=True)
        sheet_fx()
        sheet_scenes()
        sheet_ui(bars, threads)
    print('gen_irina_fx: %d файлов' % len(WRITTEN))
    mod.WRITTEN.extend(WRITTEN)
