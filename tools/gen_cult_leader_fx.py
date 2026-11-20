#!/usr/bin/env python3
"""
T26 «Глава Культа Меллисто» — эффекты, печати, полоса босса, титр, иконка, lang, звуки, проверочные кадры.
Вызывается из tools/gen_cult_leader.py (run(M, args)); отдельно не запускается.

Время — тики, углы — градусы, размеры — блоки. Цвета огня — из палитры tyros_flame (Iron's), тёмные — из палитры Тироса.
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from gen_sigil_textures import C, SS, W, canvas, polar, ring, save  # noqa: E402
import gen_forbidden_fx as F  # noqa: E402  (помощники печатей/эффектов: L, T, ap, sigil, E, ease, _icon, _polar_glyph, _pline)

M = None              # модуль gen_cult_leader (A, out, write_json, WRITTEN, jar_img …)
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
MEDIA = os.path.join(ROOT, 'docs', 'media')

# палитра огня (tyros_flame) и Тироса
FIRE, FIRE_HOT, FIRE_CORE, FIRE_DEEP = '#FF7A1E', '#FFD24A', '#FFF4D8', '#C8320C'
CLOTH, CLOTH_D, SOOT, ASH = '#792426', '#4A0E10', '#1A0E0C', '#62514E'
SEAL = '#F05A1E'          # цвет печати «Приговора» (между FIRE и FIRE_DEEP)

R_VERDICT, R_WALL = 24, 28
T_WARN, T_BAN = 40, 200   # предупреждение 2 с, запрет 10 с
T_INTRO = 175             # ролик появления = анимация fire_boss_spawn (8.75 с)
T_DEATH = 70              # ролик смерти 3.5 с (первые 3.5 с анимации fire_boss_death)
GATE = -3.75              # проём огня — за спиной босса: fire_boss_spawn начинает с body.z = +60 px (3.75 бл. позади) и выводит вперёд


def write(rel, obj):
    M.write_json(rel, obj)


# ================================================================== текстуры (белое на прозрачном → textures/sigil)
def _save_sigil(img, name, size=(512, 512)):
    small = img.resize(size, Image.LANCZOS)
    rgba = Image.new('RGBA', size, (255, 255, 255, 0))
    rgba.putalpha(small)
    rgba.save(M.out('textures/sigil/%s.png' % name))


def _flame_poly(cx, cy, w, h, ang=0.0, lean=0.0, n=24):
    """Язык пламени: основание (cx, cy), высота h вдоль направления ang (рад, 0 — вверх по экрану), ширина w, изгиб lean."""
    pts = []
    for k in range(n + 1):
        t = k / n
        r = w * 0.5 * math.sin(math.pi * min(1, t * 1.15)) ** 0.8 * (1 - t) ** 0.35
        y = -h * t
        x = lean * h * t * t
        pts.append((x - r, y))
    for k in range(n, -1, -1):
        t = k / n
        r = w * 0.5 * math.sin(math.pi * min(1, t * 1.15)) ** 0.8 * (1 - t) ** 0.35
        pts.append((lean * h * t * t + r, -h * t))
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts]


def tex_verdict():
    """«Приговор Меллисто» — печать r24 на земле. Обод из языков пламени, обращённых внутрь (огонь сжимает круг);
    кольцо под надпись (текст — слоем печати); восемь знаков школ магии, каждый перечёркнут; знаки скованы цепью-восьмиугольником;
    четыре клинка-приговора от ока к ободу; в центре — око в пламени (знак культа, как на медальоне и полосе босса)."""
    img = canvas()
    d = ImageDraw.Draw(img)
    rng = random.Random(2611)
    ring(d, C * 0.99, 7 * SS)
    ring(d, C * 0.962, 2.5 * SS)
    for i in range(36):                                                   # языки пламени внутрь
        a = 2 * math.pi * i / 36
        bx, by = polar(C * 0.95, a)
        h = C * (0.12 if i % 2 == 0 else 0.075)
        d.polygon(_flame_poly(bx, by, C * 0.05, h, ang=a - math.pi / 2 + math.pi, lean=0.25 if i % 4 < 2 else -0.25), fill=255)
    ring(d, C * 0.805, 3 * SS)
    ring(d, C * 0.69, 3 * SS)                                             # между 0.69 и 0.805 — надпись (слой text)
    for i in range(72):                                                   # насечки по кольцу надписи
        a = 2 * math.pi * i / 72
        d.line([*polar(C * 0.69, a), *polar(C * 0.705, a)], fill=255, width=2 * SS)
    # восемь знаков школ, перечёркнутых
    marks = []
    for k in range(8):
        a = 2 * math.pi * k / 8 + math.pi / 8
        cx, cy = polar(C * 0.52, a)
        marks.append((cx, cy))
    for k in range(8):                                                    # цепь-восьмиугольник между знаками
        (x0, y0), (x1, y1) = marks[k], marks[(k + 1) % 8]
        n = 9
        for j in range(n):
            t0, t1 = (j + 0.2) / n, (j + 0.8) / n
            xa, ya = x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0
            xb, yb = x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1
            if j in (0, n - 1):
                continue
            wdt = C * 0.018
            if j % 2:
                d.line([xa, ya, xb, yb], fill=255, width=int(3 * SS))
            else:
                d.ellipse([(xa + xb) / 2 - wdt, (ya + yb) / 2 - wdt * 0.6, (xa + xb) / 2 + wdt, (ya + yb) / 2 + wdt * 0.6], outline=255, width=int(2.5 * SS))
    R = C * 0.085
    for k, (cx, cy) in enumerate(marks):
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=0, outline=255, width=int(4 * SS))
        r = R * 0.55
        if k == 0:                                                       # огонь — треугольник
            d.polygon([(cx, cy - r), (cx + r * 0.9, cy + r * 0.6), (cx - r * 0.9, cy + r * 0.6)], outline=255, width=int(3 * SS))
        elif k == 1:                                                     # лёд — снежинка
            for j in range(3):
                a = math.pi / 3 * j
                d.line([cx - r * math.cos(a), cy - r * math.sin(a), cx + r * math.cos(a), cy + r * math.sin(a)], fill=255, width=int(3 * SS))
        elif k == 2:                                                     # молния
            F._pline(d, [(cx - r * 0.2, cy - r), (cx + r * 0.25, cy - r * 0.1), (cx - r * 0.25, cy + r * 0.1), (cx + r * 0.2, cy + r)], 3 * SS)
        elif k == 3:                                                     # природа — лист
            d.ellipse([cx - r * 0.45, cy - r, cx + r * 0.45, cy + r], outline=255, width=int(3 * SS))
            d.line([cx, cy - r, cx, cy + r], fill=255, width=int(2 * SS))
        elif k == 4:                                                     # свет — звезда-крест
            d.line([cx, cy - r, cx, cy + r], fill=255, width=int(3 * SS))
            d.line([cx - r, cy, cx + r, cy], fill=255, width=int(3 * SS))
            d.ellipse([cx - r * 0.3, cy - r * 0.3, cx + r * 0.3, cy + r * 0.3], fill=255)
        elif k == 5:                                                     # кровь — капля
            d.polygon(_flame_poly(cx, cy + r * 0.8, r * 1.1, r * 1.7, ang=0), outline=255)
            d.ellipse([cx - r * 0.5, cy - r * 0.1, cx + r * 0.5, cy + r * 0.8], outline=255, width=int(3 * SS))
        elif k == 6:                                                     # эндер — око
            d.ellipse([cx - r, cy - r * 0.45, cx + r, cy + r * 0.45], outline=255, width=int(3 * SS))
            d.ellipse([cx - r * 0.25, cy - r * 0.25, cx + r * 0.25, cy + r * 0.25], fill=255)
        else:                                                            # мистика — спираль
            pts = [(cx + r * t * math.cos(t * 9), cy + r * t * math.sin(t * 9)) for t in np.linspace(0.05, 1, 40)]
            F._pline(d, pts, 3 * SS)
        a = math.atan2(cy - C, cx - C) + math.pi / 4                        # черта запрета
        d.line([cx - R * 1.15 * math.cos(a), cy - R * 1.15 * math.sin(a), cx + R * 1.15 * math.cos(a), cy + R * 1.15 * math.sin(a)],
               fill=255, width=int(6 * SS))
    for k in range(4):                                                    # клинки приговора
        a = 2 * math.pi * k / 4
        x0, y0 = polar(C * 0.2, a)
        x1, y1 = polar(C * 0.68, a)
        nx, ny = -math.sin(a), math.cos(a)
        wd = C * 0.022
        d.polygon([(x0 + nx * wd, y0 + ny * wd), (x1, y1), (x0 - nx * wd, y0 - ny * wd)], fill=255)
        gx, gy = polar(C * 0.235, a)
        d.line([gx + nx * wd * 2.6, gy + ny * wd * 2.6, gx - nx * wd * 2.6, gy - ny * wd * 2.6], fill=255, width=int(5 * SS))
    ring(d, C * 0.19, 4 * SS)
    # око в пламени
    d.polygon(_flame_poly(C, C + C * 0.11, C * 0.2, C * 0.26), fill=255)
    d.polygon(_flame_poly(C, C + C * 0.08, C * 0.13, C * 0.17), fill=0)
    ew, eh = C * 0.085, C * 0.04
    d.chord([C - ew, C - eh, C + ew, C + eh], 0, 360, fill=255)
    d.ellipse([C - eh * 0.75, C - eh * 0.75, C + eh * 0.75, C + eh * 0.75], fill=0)
    d.ellipse([C - eh * 0.32, C - eh * 0.32, C + eh * 0.32, C + eh * 0.32], fill=255)
    _save_sigil(img, 'mellisto_verdict')


def tex_emblem():
    """Малый знак культа (око в пламени, обод языков) — печать под боссом в ролике и на переходах фаз, метка над головой при запрете."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.97, 6 * SS)
    for i in range(16):
        a = 2 * math.pi * i / 16
        bx, by = polar(C * 0.92, a)
        d.polygon(_flame_poly(bx, by, C * 0.12, C * (0.22 if i % 2 == 0 else 0.14), ang=a + math.pi / 2), fill=255)
    ring(d, C * 0.62, 4 * SS)
    d.polygon(_flame_poly(C, C + C * 0.42, C * 0.7, C * 0.95), fill=255)
    d.polygon(_flame_poly(C, C + C * 0.32, C * 0.48, C * 0.62), fill=0)
    ew, eh = C * 0.3, C * 0.14
    d.chord([C - ew, C - eh, C + ew, C + eh], 0, 360, fill=255)
    d.ellipse([C - eh * 0.75, C - eh * 0.75, C + eh * 0.75, C + eh * 0.75], fill=0)
    d.ellipse([C - eh * 0.3, C - eh * 0.3, C + eh * 0.3, C + eh * 0.3], fill=255)
    _save_sigil(img, 'cult_emblem')
    # метка «магия под запретом»: тот же знак, перечёркнутый, в кольце
    d.line([C - C * 0.68, C + C * 0.68, C + C * 0.68, C - C * 0.68], fill=0, width=int(26 * SS))
    d.line([C - C * 0.7, C + C * 0.7, C + C * 0.7, C - C * 0.7], fill=255, width=int(12 * SS))
    _save_sigil(img, 'cult_verdict_mark')


def tex_flame_tongue():
    """Язык пламени для `curtain` стены огня: 128×512, широкое основание, 2–3 отростка, мягкое затухание кверху."""
    S = 4
    w, h = 128 * S, 512 * S
    img = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(img)
    rng = random.Random(28)
    d.polygon(_flame_poly(w / 2, h, w * 0.9, h * 0.92, lean=0.04), fill=255)
    for (ox, sc, ln) in ((-0.22, 0.42, -0.2), (0.24, 0.36, 0.25), (0.05, 0.3, 0.1)):
        d.polygon(_flame_poly(w / 2 + ox * w, h * 0.7, w * sc, h * 0.62 * (sc / 0.42), lean=ln), fill=255)
    a = np.asarray(img, np.float32) / 255
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4 * S)), np.float32) / 255
    yy = np.linspace(0, 1, h)[:, None]
    a = a * (0.25 + 0.75 * yy ** 0.8)                                     # кверху слабее
    core = np.asarray(Image.fromarray((np.clip(a * 1.6 - 0.55, 0, 1) * 255).astype(np.uint8)), np.float32) / 255
    a = np.clip(a * 0.85 + core * 0.3, 0, 1)
    rgba = Image.new('RGBA', (w // S, h // S), (255, 255, 255, 0))
    rgba.putalpha(Image.fromarray((a * 255).astype(np.uint8)).resize((w // S, h // S), Image.LANCZOS))
    rgba.save(M.out('textures/sigil/cult_flame_tongue.png'))


def tex_scorch_ring():
    """Выжженное кольцо по краю арены (decal r29.5): полоса 0.92–1.0 радиуса с рваными краями и трещинами к центру."""
    img = canvas()
    d = ImageDraw.Draw(img)
    rng = random.Random(29)
    pts_o, pts_i = [], []
    for k in range(360):
        a = 2 * math.pi * k / 360
        pts_o.append(polar(C * (0.985 - 0.012 * rng.random()), a))
        pts_i.append(polar(C * (0.925 + 0.014 * math.sin(k * 0.7) + 0.01 * rng.random()), a))
    d.polygon(pts_o, fill=255)
    d.polygon(pts_i, fill=0)
    for k in range(70):                                                    # трещины внутрь
        a = 2 * math.pi * rng.random()
        r = C * 0.93
        pts = [polar(r, a)]
        for j in range(4):
            r -= C * (0.012 + rng.random() * 0.02)
            a += (rng.random() - 0.5) * 0.04
            pts.append(polar(r, a))
        F._pline(d, pts, (3 - min(2, k % 3)) * SS)
    _save_sigil(img, 'cult_scorch_ring')


def textures():
    tex_verdict()
    tex_emblem()
    tex_flame_tongue()
    tex_scorch_ring()


# ================================================================== печати
L, T, ap = F.L, F.T, F.ap


def sigils():
    F.sigil('cult_verdict', 'T26 «Приговор Меллисто»: печать r24 на земле. Прорисовывается 2 с (предупреждение), на 40 тике — вспышка '
                            '(запрет начался), держится, пока эффект не кончится (10 с запрета). Знаки восьми школ перечёркнуты, цепь, '
                            'четыре клинка, око в пламени; надпись по кольцу. Сгенерировано tools/gen_cult_leader.py.',
            R_VERDICT, SEAL, 'ground', [
                L('glow', 'disc', 'glow', 1.0, -0.02, ap(0, 40, 'fade', easing='easeInSine'), color=CLOTH_D, br=0.35, pulse=(0.12, 30)),
                L('seal', 'disc', 'mellisto_verdict', 1.0, 0.0, ap(0, 38, 'draw', easing='easeInOutSine', startAngle=90), rot=0.25, boost=3),
                T('verdict', 'ПРИГОВОР МЕЛЛИСТО ✦ МАГИЯ ПОД ЗАПРЕТОМ ✦ ', 0.748, 0.05, 0.01, ap(8, 30, 'draw', easing='linear'),
                  font='cyrillic', color=FIRE_HOT, br=0.9, rot=-0.35, repeat=3),
                L('arcs', 'arcs', 'arc_strip', 1.03, 0.02, ap(26, 14, 'assemble', 'fade'), count=6, arcLength=40, width=0.012, rot=-1.2,
                  color=FIRE, br=1.1),
            ], hold=-1, flash={'color': FIRE_HOT, 'size': 1.05, 'duration': 14, 'sparks': 120}, dissolve=('fade', 'collapse'), ddur=20)
    F.sigil('cult_emblem', 'T26: знак культа (око в пламени) под Главой Культа — ролик появления и переходы фаз. Сгенерировано tools/gen_cult_leader.py.',
            3.2, FIRE, 'ground', [
                L('glow', 'disc', 'glow', 1.0, -0.01, ap(0, 10, 'fade'), color=FIRE_DEEP, br=0.6, pulse=(0.2, 16)),
                L('seal', 'disc', 'cult_emblem', 1.0, 0.0, ap(0, 18, 'draw', startAngle=90, easing='easeOutCubic'), rot=1.5, boost=6),
                L('rim', 'band', 'school_fire_band', 1.18, 0.01, ap(8, 12, 'draw', startAngle=90, direction=-1), inner=0.9, repeat=3, rot=-2.5,
                  color=FIRE_HOT, br=0.8),
            ], hold=-1, flash={'color': FIRE_HOT, 'size': 1.3, 'duration': 10, 'sparks': 40}, dissolve=('shatter', 'fade'), ddur=14)
    F.sigil('cult_verdict_mark', 'T26: метка над головой игрока под «Приговором» (магия под запретом) — перечёркнутый знак культа, лежит над головой.',
            0.42, SEAL, 'ground', [
                L('mark', 'disc', 'cult_verdict_mark', 1.0, 0.0, ap(0, 8, 'grow', 'fade'), rot=2.0, br=1.1, pulse=(0.15, 20)),
            ], hold=-1, dissolve=('fade',), ddur=8)


# ================================================================== эффекты
E, ease = F.E, F.ease


def fx(id_, comment, dur, els, style='cult_leader'):
    write('fx/%s.json' % id_, {'comment': comment, 'style': style, 'duration': dur, 'elements': els})


def at(base, x=0.0, y=0.0, z=0.0):
    return F.off(base, x, y, z)


def ring_points(base, r, n, y=0.0):
    return [at(base, r * math.cos(2 * math.pi * k / n), y, r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def effects():
    write('fx/styles/cult_leader.json', {
        'comment': 'T26 Глава Культа Меллисто: огонь Тироса (палитра tyros_flame) и багровая ткань культа; движение тяжёлое, с рывками пламени.',
        'palette': {'primary': FIRE, 'secondary': FIRE_HOT, 'core': FIRE_CORE, 'shadow': CLOTH_D},
        'textures': {'sparks': 'spark_soft', 'runes': 'school_fire_band', 'shards': 'mote_flame', 'sigil': 'cult_emblem'},
        'blend': 'additive', 'motion': {'rotationScale': 0.9, 'jitter': 0.2, 'easing': 'easeOutCubic', 'pulse': {'amp': 0.15, 'period': 8}}})
    G = at('caster', 0, 0, GATE)
    # ---------------------------------------------------------------- появление
    fx('cult_leader_intro', 'Ролик появления (8.75 с = 175 тиков = анимация fire_boss_spawn). caster = босс на конечной точке, yaw — куда он смотрит. '
       'Проём огня G — в 3.75 бл. за спиной босса (анимация выводит его оттуда). 0–2 с трещины и жар у G, 1–6.5 с завеса пламени и столб в G, '
       '2–6.4 с силуэт идёт сквозь огонь (огненный венок на теле), 6.0 с — взмах косой: волна r12 и вспышка; 6.5 с — знак культа под ним (титр), '
       '8.75 с — полоса босса (код).', T_INTRO, [
        E('tint', 0, 'caster', duration=T_INTRO, radius=48, color='#3A0A04', strength=0.32, **{'in': ease(30), 'out': ease(30, 'easeInSine')}),
        E('decal', 0, G, duration=T_INTRO, texture='higher_cracks', radius=6, grow=36, glow=0.5, fadeOut=40, color=FIRE_DEEP, brightness=1.1,
          comment='земля трескается, из трещин жар'),
        E('sprites', 0, at(G, 0, 0.1, 0), duration=150, texture='mote_flame', count=100000, rate=0.5, area=3.5, speed=0.02, gravity=-0.012,
          size=[0.22, 0.04], life=34, color=FIRE, glow=0.6, comment='искры из трещин'),
        E('sigil', 10, at(G, 0, 0.05, 0), id='cult_emblem', comment='знак культа под проёмом'),
        E('curtain', 22, G, duration=118, radius=[0.4, 2.1], count=30, height=5.6, grow=30, width=[0.6, 1.3], brightness=[0.6, 1.0], flicker=0.55,
          texture='cult_flame_tongue', color='@primary', out=ease(28, 'easeInSine'), comment='стена пламени — из неё выходит силуэт'),
        E('curtain', 30, G, duration=100, radius=[0.2, 1.4], count=16, height=3.4, grow=24, width=[0.4, 0.9], brightness=[0.8, 1.0], flicker=0.6,
          texture='cult_flame_tongue', color='@secondary', out=ease(24, 'easeInSine')),
        E('column', 26, G, duration=96, radius=1.5, height=8, fill=0.45, color='@primary', out=ease(26, 'easeInSine')),
        E('sprites', 30, at(G, 0, 0.4, 0), duration=100, texture='mote_flame', count=100000, rate=1.4, spread=1.4, speed=0.06, gravity=-0.02,
          size=[0.7, 0.1], life=26, color='@secondary', glow=0.8),
        E('aura', 40, 'caster', duration=92, follow=True, target='caster', thickness=0.16, pulse=[0.25, 10], color='@primary', motes=24,
          texture='mote_flame', ring=False, out=ease(20), comment='огненный венок на силуэте, пока он идёт сквозь пламя'),
        E('wave', 120, 'caster', duration=26, shape='ring', radius=12, thickness=2.2, followTerrain=True, color='@primary', comment='взмах косой (6.0 с)'),
        E('flash', 120, at('caster', 0, 2.0, 0), duration=12, size=3.2, rays=8, color='@secondary', ring=True),
        E('sprites', 121, at('caster', 0, 1.2, 0), duration=6, texture='mote_flame', count=60, rate=10, spread=1.2, speed=0.3, gravity=0.01,
          size=[0.5, 0.05], life=24, color='@primary', glow=0.7),
        E('sigil', 130, at('caster', 0, 0.04, 0), id='cult_emblem', comment='знак под боссом — в этот момент титр (6.5 с)'),
        E('sprites', 130, at('caster', 0, 0.2, 0), duration=45, texture='mote_flame', count=100000, rate=0.4, area=2.4, speed=0.02, gravity=-0.01,
          size=[0.25, 0.04], life=30, color=FIRE),
    ])
    # ---------------------------------------------------------------- Приговор Меллисто
    fx('cult_leader_verdict', 'Фаза 2: «Приговор Меллисто». caster = центр зоны (босс в момент приговора; не follow). 0–40 тиков (2 с) — '
       'предупреждение: печать r24 прорисовывается, мир краснеет, низкая завеса по краю; на 40 тике вспышка — ЗАПРЕТ НАЧАЛСЯ (код: 40…240); '
       '40–240 — печать держится, по краю r24 — завеса, пепел падает; конец — печать гаснет. Всего 240 тиков.', T_WARN + T_BAN, [
        E('sigil', 0, at('caster', 0, 0.06, 0), id='cult_verdict', scale=1.0),
        E('tint', 0, 'caster', duration=T_WARN + T_BAN, radius=R_VERDICT, color='#4A0A08', strength=0.28, **{'in': ease(40, 'easeInSine'), 'out': ease(20)}),
        E('curtain', 0, 'caster', duration=T_WARN, radius=R_VERDICT, count=140, height=1.2, grow=40, width=[0.06, 0.16], brightness=[0.3, 0.6],
          texture='beam_fade', flicker=0.6, color='@primary', out=ease(6), comment='предупреждение: край зоны прорастает'),
        E('aura', 0, 'caster', duration=T_WARN, target='caster', thickness=0.22, pulse=[0.3, 8], color='@secondary', motes=30, comment='босс поднял руку'),
        E('flash', T_WARN, at('caster', 0, 1.0, 0), duration=14, size=4.5, rays=12, screen=0.12, ring=True, color='@secondary'),
        E('wave', T_WARN, 'caster', duration=18, shape='ring', radius=R_VERDICT, thickness=1.6, followTerrain=True, color='@primary'),
        E('curtain', T_WARN, 'caster', duration=T_BAN, radius=R_VERDICT, count=180, height=3.2, grow=8, width=[0.08, 0.22], brightness=[0.3, 0.65],
          texture='beam_fade', flicker=0.35, color='@primary', out=ease(20), comment='граница запрета'),
        E('sprites', T_WARN, at('caster', 0, 6, 0), duration=T_BAN, texture='mote_ash', count=100000, rate=1.2, area=R_VERDICT - 1, speed=0.0,
          gravity=0.004, spin=30, size=[0.18, 0.08], life=80, color=ASH, blend='translucent', comment='пепел оседает в зоне'),
        E('sprites', T_WARN, at('caster', 0, 0.1, 0), duration=T_BAN, texture='mote_flame', count=100000, rate=0.6, area=R_VERDICT, speed=0.01,
          gravity=-0.01, size=[0.2, 0.03], life=30, color=FIRE),
    ])
    fx('cult_leader_verdict_mark', 'Метка над головой игрока, пока на нём запрет (caster = игрок, follow). Слать всем; длительность — до конца запрета (код ставит 200).',
       T_BAN, [E('sigil', 0, at('caster', 0, 2.35, 0), follow=True, id='cult_verdict_mark')])
    fx('cult_leader_verdict_fizzle', 'Игрок под запретом пытается колдовать: заклинание гаснет в руке пеплом (caster = игрок).', 14, [
        E('flash', 0, 'caster.hand', duration=8, size=0.9, color=FIRE_DEEP),
        E('sprites', 0, 'caster.hand', duration=4, texture='mote_ash', count=14, rate=6, spread=0.3, speed=0.06, gravity=0.01, spin=60,
          size=[0.16, 0.04], life=16, color=ASH, blend='translucent'),
        E('sprites', 0, 'caster.hand', duration=3, texture='spark_soft', count=8, rate=4, spread=0.2, speed=0.08, size=[0.12, 0.02], life=8, color=FIRE),
    ])
    # ---------------------------------------------------------------- стена огня (фаза 3)
    wall = [
        E('wave', 0, 'caster', duration=30, shape='ring', radius=R_WALL, thickness=3.0, followTerrain=True, color='@primary', comment='огонь бежит от центра к краю'),
        E('decal', 26, 'caster', texture='cult_scorch_ring', radius=R_WALL + 1.5, blend='translucent', color=SOOT, grow=8, comment='выжженный край'),
        E('decal', 26, 'caster', texture='cult_scorch_ring', radius=R_WALL + 1.5, glow=0.4, pulse=30, color='@primary', brightness=0.8, grow=8),
        E('curtain', 26, 'caster', radius=[R_WALL - 0.4, R_WALL + 0.4], count=240, height=4.6, grow=22, width=[0.8, 1.5],
          brightness=[0.6, 1.0], flicker=0.6, texture='cult_flame_tongue', color='@primary', out=ease(30, 'easeInSine'), comment='стена пламени'),
        E('curtain', 30, 'caster', radius=[R_WALL - 0.2, R_WALL + 0.2], count=140, height=2.6, grow=18, width=[0.5, 1.0],
          brightness=[0.7, 1.0], flicker=0.7, texture='cult_flame_tongue', color='@secondary', out=ease(30, 'easeInSine')),
        E('tint', 26, 'caster', radius=R_WALL, color='#5A1A08', strength=0.16, **{'in': ease(30), 'out': ease(30)}),
    ]
    for p in ring_points('caster', R_WALL, 16, 0.3):
        wall.append(E('sprites', 30, p, texture='mote_flame', count=100000, rate=0.35, spread=1.6, speed=0.03, gravity=-0.03,
                      size=[0.5, 0.06], life=28, color='@secondary', glow=0.6))
    fx('cult_leader_firewall', 'Фаза 3: стена огня по краю арены r28 от точки появления (caster = центр арены, не follow). Держится до Fx.stop '
       '(смерть босса / сброс). Волна от центра 0–30 тиков, стена встаёт к 26–48. Урон при пересечении — код (r 27.5–28.5), '
       'на игроке — cult_leader_firewall_burn. Блоки не жечь.', -1, wall)
    fx('cult_leader_firewall_burn', 'Игрок пересёк стену огня: вспышка пламени на нём (caster = игрок).', 18, [
        E('aura', 0, 'caster', duration=16, target='caster', thickness=0.25, pulse=[0.4, 4], color='@primary', motes=20, follow=True),
        E('sprites', 0, at('caster', 0, 0.8, 0), duration=5, texture='mote_flame', count=30, rate=8, spread=0.7, speed=0.12, gravity=-0.02,
          size=[0.5, 0.06], life=14, color='@secondary', glow=0.7),
        E('flash', 0, at('caster', 0, 1, 0), duration=6, size=1.4, color=FIRE),
    ])
    # ---------------------------------------------------------------- переходы фаз
    fx('cult_leader_phase2', 'Переход в фазу 2 (66% ХП): «Глава Культа взывает к Меллисто» — рёв, знак культа под ним, кольцо r16 (caster = босс, follow). 3 с.', 60, [
        E('sigil', 0, at('caster', 0, 0.04, 0), id='cult_emblem', follow=True),
        E('aura', 0, 'caster', duration=44, target='caster', thickness=0.24, pulse=[0.3, 6], color='@primary', motes=40, follow=True),
        E('flash', 12, at('caster', 0, 1.8, 0), duration=12, size=3.4, rays=10, screen=0.12, color='@secondary'),
        E('wave', 12, 'caster', duration=24, shape='ring', radius=16, thickness=2.4, followTerrain=True, color='@primary'),
        E('sprites', 12, at('caster', 0, 1.2, 0), duration=6, texture='mote_flame', count=70, rate=12, spread=1.4, speed=0.32, gravity=0.012,
          size=[0.5, 0.05], life=26, color='@primary', glow=0.6),
        E('tint', 0, 'caster', duration=60, radius=32, color='#4A0A08', strength=0.25, **{'in': ease(10), 'out': ease(30)}),
    ])
    fx('cult_leader_phase3', 'Переход в фазу 3 (33% ХП): «Истинное пламя» — столб огня из босса, волна к краю арены r28 (на 30 тике код запускает '
       'cult_leader_firewall), вспышка. caster = босс. 4 с.', 80, [
        E('column', 0, 'caster', duration=44, radius=1.8, height=16, fill=0.7, color='@primary', out=ease(18, 'easeInSine')),
        E('vortex', 0, 'caster', duration=40, radius=3.2, height=6, arms=3, speed=9, texture='mote_flame', color='@secondary', out=ease(10)),
        E('sigil', 0, at('caster', 0, 0.04, 0), id='cult_emblem', scale=1.6),
        E('flash', 30, at('caster', 0, 2.0, 0), duration=16, size=5.5, rays=12, screen=0.28, color='@secondary', ring=True),
        E('wave', 30, 'caster', duration=30, shape='ring', radius=R_WALL, thickness=3.0, followTerrain=True, color='@primary'),
        E('tint', 0, 'caster', duration=80, radius=40, color='#6A1A06', strength=0.34, **{'in': ease(20), 'out': ease(40)}),
    ])
    fx('cult_leader_fury', 'Фаза 3, «ярость души» (облик души Тироса): огненный ореол на боссе, пока длится (caster = босс, follow, до Fx.stop).', -1, [
        E('aura', 0, 'caster', target='caster', follow=True, thickness=0.2, pulse=[0.25, 12], color='@secondary', motes=30, texture='mote_flame'),
        E('sprites', 0, at('caster', 0, 1.2, 0), follow=True, texture='mote_flame', count=100000, rate=0.6, spread=0.7, speed=0.02,
          gravity=-0.02, size=[0.35, 0.05], life=22, color='@primary', glow=0.6),
    ])
    fx('cult_leader_summon', 'Призыв огненного культиста (фаза 3, 2–4 шт.): caster = точка появления. Печать огня, столб, вспышка; на 24 тике код ставит культиста.', 40, [
        E('sigil', 0, at('caster', 0, 0.04, 0), id='fire_seal'),
        E('column', 6, 'caster', duration=26, radius=0.8, height=4.5, fill=0.6, color='@primary', out=ease(10)),
        E('curtain', 6, 'caster', duration=22, radius=[0.3, 1.1], count=12, height=2.6, grow=10, width=[0.4, 0.8], brightness=[0.7, 1.0], flicker=0.6,
          texture='cult_flame_tongue', color='@secondary', out=ease(8)),
        E('flash', 22, at('caster', 0, 1, 0), duration=8, size=2.2, color='@secondary'),
        E('sprites', 22, at('caster', 0, 0.8, 0), duration=4, texture='mote_flame', count=24, rate=8, spread=0.8, speed=0.18, size=[0.4, 0.05], life=16,
          color='@primary', glow=0.6),
    ])
    fx('fire_cultist_aura', 'Огненный культист: тлеющие угли у подола (caster = культист, follow, до Fx.stop). Необязательно — у модели есть glowmask.', -1, [
        E('sprites', 0, at('caster', 0, 0.2, 0), follow=True, texture='mote_flame', count=100000, rate=0.12, spread=0.4, speed=0.01,
          gravity=-0.015, size=[0.16, 0.03], life=24, color=FIRE),
    ])
    # ---------------------------------------------------------------- смерть
    fx('cult_leader_death', 'Ролик смерти 3.5 с (70 тиков = начало анимации fire_boss_death): 0–2.6 с босс падает на колени, пламя спиралью '
       'стекает вниз; 2.6 с (52) — пламя головы гаснет (код выключает слой огня), дымный выдох, искры; 2.6–3.5 — пепел поднимается с тела. '
       'caster = босс. Стену огня гасить на 52 тике (Fx.stop).', T_DEATH + 30, [
        E('tint', 0, 'caster', duration=T_DEATH + 30, radius=32, color='#2A0806', strength=0.3, **{'in': ease(20), 'out': ease(30)}),
        E('vortex', 0, 'caster', duration=52, radius=1.4, height=3.2, arms=3, speed=-6, flow=-1, texture='mote_flame', color='@primary', out=ease(12),
          comment='пламя спиралью стекает вниз по телу'),
        E('sprites', 0, at('caster', 0, 1.6, 0), duration=50, texture='mote_flame', count=100000, rate=0.8, spread=0.6, speed=0.02, gravity=0.01,
          size=[0.4, 0.05], life=20, color='@secondary'),
        E('flash', 52, at('caster', 0, 1.9, 0), duration=10, size=2.4, color=FIRE_HOT, comment='пламя гаснет'),
        E('sprites', 52, at('caster', 0, 2.0, 0), duration=8, texture='mote_ash', count=40, rate=6, spread=0.5, speed=0.05, gravity=-0.012, spin=40,
          size=[0.5, 0.2], life=40, color=SOOT, blend='translucent', comment='дымный выдох'),
        E('sprites', 52, at('caster', 0, 1.0, 0), duration=6, texture='spark_soft', count=50, rate=10, spread=0.8, speed=0.2, gravity=0.015,
          size=[0.15, 0.02], life=18, color=FIRE),
        E('sprites', 54, at('caster', 0, 0.9, 0), duration=46, texture='mote_ash', count=100000, rate=1.2, spread=0.7, speed=0.01, gravity=-0.008,
          spin=30, size=[0.22, 0.06], life=50, color=ASH, blend='translucent', comment='пепел с тела'),
        E('decal', 52, 'caster', duration=48, texture='glow', radius=3.0, blend='translucent', color=SOOT, fadeOut=30, comment='выжженное пятно'),
        E('wave', 52, 'caster', duration=20, shape='ring', radius=8, thickness=1.2, followTerrain=True, color=FIRE_DEEP),
    ])


# ================================================================== полоса босса (192×36, формат tyros_bossbar: BossbarSprite(192, 18, 3, -1))
BAR_COLS = {'A': '#491b10', 'B': '#2b1111', 'C': '#9c5e2c', 'D': '#e8e895', 'E': '#b9892e', 'F': '#ffffff', 'G': '#d6af39',
            'H': '#733c25', 'O': '#ec0d00', 'R': '#b90b00', 'N': '#6e0500'}
# левая половина узора, i = x − 58 (x 58…95); правая — зеркально (x' = 191 − x). '.' — прозрачно, '?' — как в основе полосы.
BAR_ART = {
    0: {37: 'B'},
    1: {24: 'B', 25: 'B', 36: 'B', 37: 'G', 14: 'E'},
    2: {23: 'B', 24: 'D', 25: 'B', 19: 'B', 35: 'B', 36: 'G', 37: 'D', 8: 'C'},
    3: {24: 'B', 25: 'G', 26: 'B', 18: 'B', 19: 'G', 20: 'B', 12: 'B', 34: 'B', 35: 'G', 36: 'D', 37: 'B'},
    4: {25: 'B', 26: 'G', 27: 'B', 18: 'B', 19: 'D', 20: 'B', 11: 'B', 12: 'G', 13: 'B', 5: 'B', 33: 'B', 34: 'G', 35: 'D', 36: 'B', 37: 'O'},
    5: {26: 'B', 27: 'E', 28: 'B', 17: 'B', 18: 'G', 19: 'D', 20: 'G', 21: 'B', 11: 'B', 12: 'D', 13: 'B', 4: 'B', 5: 'G', 6: 'B',
        33: 'B', 34: 'E', 35: 'G', 36: 'D', 37: 'B'},
    6: {26: 'B', 27: 'E', 28: 'G', 29: 'B', 17: 'B', 18: 'E', 19: 'G', 20: 'E', 21: 'B', 10: 'B', 11: 'E', 12: 'G', 13: 'E', 14: 'B',
        4: 'B', 5: 'E', 6: 'B', 32: 'B', 33: 'E', 34: 'G', 35: 'G', 36: 'D', 37: 'D'},
    7: {27: 'B', 28: 'E', 29: 'G', 30: 'B', 31: 'B', 32: 'E', 33: 'G', 34: 'G', 35: 'G', 36: 'D', 37: 'F'},
    8: {31: 'B', 32: 'B', 33: 'E', 34: 'G', 35: 'G', 36: 'D', 37: 'D'},
    9: {32: 'B', 33: 'B', 34: 'E', 35: 'G', 36: 'D', 37: 'F'},
    10: {33: 'B', 34: 'B', 35: 'E', 36: 'G', 37: 'D'},
    11: {34: 'B', 35: 'B', 36: 'E', 37: 'G'},
    12: {35: 'B', 36: 'B', 37: 'B'},
}


def bossbar():
    src = M.jar_img(M.I + 'textures/gui/sprites/boss_bars/tyros_bossbar.png')
    a = np.asarray(src).copy()
    for half in (0, 18):
        a[half:half + 7, :] = 0                                        # убрать старый узор (над полосой)
        for y in range(half + 7, half + 12):                           # табличку с крестом в середине — заменить обычной полосой
            a[y, 88:104] = a[y, 80]
    img = Image.fromarray(a, 'RGBA')
    for half in (0, 18):
        for row, cols in BAR_ART.items():
            for i, ch in cols.items():
                x = 58 + i
                for xx in (x, 191 - x):
                    img.putpixel((xx, half + row), M.hx(BAR_COLS[ch]))
    img.save(M.out('textures/gui/sprites/boss_bars/cult_leader_bossbar.png'))
    return img


# ================================================================== титр
def title(bar, name='cult_leader', texts=None):
    gold = [M.hx(c) for c in ('#e8e895', '#d6af39', '#b9892e', '#9c5e2c')]
    texts = texts or (('ru', 'Head of the Cult of Mellisto', 'CormorantGaramond-BoldItalic-latin.woff'),     # имя — английское
                      ('en', 'Head of the Cult of Mellisto', 'CormorantGaramond-BoldItalic-latin.woff'))
    for lang, text, font in texts:
        S = 2
        Wd, Hd = 1024 * S, 192 * S
        fnt = ImageFont.truetype(os.path.join(HERE, 'fonts', font), 92 * S)
        if True:
            fnt = ImageFont.truetype(os.path.join(HERE, 'fonts', font), 84 * S)
        bb = fnt.getbbox(text)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        tx, ty = (Wd - tw) / 2 - bb[0], 18 * S - bb[1] + (96 * S - th) / 2
        mask = Image.new('L', (Wd, Hd), 0)
        ImageDraw.Draw(mask).text((tx, ty), text, font=fnt, fill=255)
        m = np.asarray(mask, np.float32) / 255
        yy = np.linspace(0, 1, Hd)[:, None]
        t = np.clip((yy * Hd - (ty + bb[1])) / th, 0, 1)                # вертикальный градиент золота по высоте букв
        grad = np.zeros((Hd, 1, 3), np.float32)
        stops = [(0.0, gold[0]), (0.45, gold[1]), (0.8, gold[2]), (1.0, gold[3])]
        for k in range(len(stops) - 1):
            (t0, c0), (t1, c1) = stops[k], stops[k + 1]
            sel = (t >= t0) & (t <= t1)
            u = (t - t0) / (t1 - t0)
            for ch in range(3):
                grad[..., ch] = np.where(sel, c0[ch] + (c1[ch] - c0[ch]) * u, grad[..., ch])
        rgb = np.broadcast_to(grad, (Hd, Wd, 3))
        outline = np.asarray(mask.filter(ImageFilter.MaxFilter(9)), np.float32) / 255
        halo = np.asarray(mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(22 * S)), np.float32) / 255
        out_ = np.zeros((Hd, Wd, 4), np.float32)
        hc = np.array(M.hx('#c8320c')[:3], np.float32)
        out_[..., :3] = hc
        out_[..., 3] = np.clip(halo * 1.4, 0, 0.75)                     # жар за буквами
        ob = np.array(M.hx('#2b1111')[:3], np.float32)
        out_[..., :3] = out_[..., :3] * (1 - outline[..., None]) + ob * outline[..., None]
        out_[..., 3] = np.maximum(out_[..., 3], outline)
        out_[..., :3] = out_[..., :3] * (1 - m[..., None]) + rgb * m[..., None]
        out_[..., 3] = np.maximum(out_[..., 3], m)
        out_[..., 3] *= 255
        img = Image.fromarray(out_.clip(0, 255).astype(np.uint8), 'RGBA').resize((1024, 192), Image.LANCZOS)
        # орнамент под надписью: линия, сходящая на нет, и знак-око с полосы босса (×3, пиксельно)
        d = ImageDraw.Draw(img)
        y = 150
        for x in range(150, 874):
            k = 1 - abs(x - 512) / 362
            a_ = int(255 * min(1, k * 2.2))
            d.point((x, y), fill=M.hx('#d6af39', a_))
            d.point((x, y + 1), fill=M.hx('#9c5e2c', a_))
            d.point((x, y - 1), fill=M.hx('#2b1111', int(a_ * 0.8)))
            d.point((x, y + 2), fill=M.hx('#2b1111', int(a_ * 0.8)))
        crop = bar.crop((84, 0, 108, 13)).resize((72, 39), Image.NEAREST)
        img.alpha_composite(crop, (512 - 36, y - 22))
        img.save(M.out('textures/gui/title/%s_%s.png' % (name, lang)))


# ================================================================== иконка эффекта (18×18)
def icon():
    def draw(d, S):
        d.ellipse([S * 0.06, S * 0.06, S * 0.94, S * 0.94], fill=F._c('#2b1111'), outline=F._c('#b9892e'), width=int(S * 0.07))
        cx, cy = S / 2, S / 2
        d.polygon(_flame_poly(cx, cy + S * 0.3, S * 0.48, S * 0.6), fill=F._c('#ff7a1e'))
        d.polygon(_flame_poly(cx, cy + S * 0.24, S * 0.3, S * 0.36), fill=F._c('#2b1111'))
        d.ellipse([cx - S * 0.17, cy - S * 0.07, cx + S * 0.17, cy + S * 0.07], fill=F._c('#ffd24a'))
        d.ellipse([cx - S * 0.05, cy - S * 0.05, cx + S * 0.05, cy + S * 0.05], fill=F._c('#2b1111'))
        d.line([S * 0.22, S * 0.78, S * 0.78, S * 0.22], fill=F._c('#2b1111'), width=int(S * 0.16))
        d.line([S * 0.22, S * 0.78, S * 0.78, S * 0.22], fill=F._c('#ec0d00'), width=int(S * 0.09))
    F._icon(18, draw, 'textures/mob_effect/mellisto_verdict.png', k=8, crisp=True)


# ================================================================== lang и звуки
LANG = {
    'entity.pohsmp_core.cult_leader': ('Head of the Cult of Mellisto', 'Head of the Cult of Mellisto'),     # владелец: имя на обоих языках — английское
    'entity.pohsmp_core.fire_cultist': ('Огненный культист', 'Fire Cultist'),
    'ui.pohsmp_core.cult_leader.title': ('Head of the Cult of Mellisto', 'Head of the Cult of Mellisto'),
    'ui.pohsmp_core.cult_leader.subtitle': ('Пламя, что выносит приговор', 'The flame that passes judgement'),
    'ui.pohsmp_core.cult_leader.verdict_warn': ('Глава Культа выносит приговор…', 'The Cult Leader passes judgement…'),
    'ui.pohsmp_core.cult_leader.verdict': ('Приговор Меллисто: магия под запретом (%s с)', 'Mellisto\'s Verdict: magic is forbidden (%ss)'),
    'ui.pohsmp_core.cult_leader.verdict_blocked': ('Приговор Меллисто запрещает колдовать', 'Mellisto\'s Verdict forbids casting'),
    'ui.pohsmp_core.cult_leader.verdict_end': ('Приговор снят — магия вернулась', 'The Verdict is lifted — magic returns'),
    'ui.pohsmp_core.cult_leader.phase2': ('Глава Культа взывает к Меллисто', 'The Cult Leader calls upon Mellisto'),
    'ui.pohsmp_core.cult_leader.phase3': ('Истинное пламя! Края арены охвачены огнём', 'True Flame! The arena\'s edge is ablaze'),
    'ui.pohsmp_core.cult_leader.firewall': ('Стена огня обжигает', 'The wall of fire burns'),
    'ui.pohsmp_core.cult_leader.summon': ('Культисты откликаются на зов', 'Cultists answer the call'),
    'ui.pohsmp_core.cult_leader.death': ('Пламя Главы Культа гаснет', 'The Cult Leader\'s flame dies out'),
    'effect.pohsmp_core.mellisto_verdict': ('Приговор Меллисто', 'Mellisto\'s Verdict'),
    'effect.pohsmp_core.mellisto_verdict.description': ('Магия под запретом: заклинания не читаются, пока действует приговор.',
                                                        'Magic is forbidden: spells cannot be cast while the Verdict lasts.'),
    'subtitles.pohsmp_core.cult_leader.spawn': ('Глава Культа выходит из пламени', 'Cult Leader emerges from the flames'),
    'subtitles.pohsmp_core.cult_leader.death': ('Глава Культа падает', 'Cult Leader falls'),
    'subtitles.pohsmp_core.cult_leader.death_final': ('Пламя гаснет', 'Flame dies out'),
    'subtitles.pohsmp_core.cult_leader.verdict': ('Приговор Меллисто', 'Mellisto\'s Verdict'),
    'subtitles.pohsmp_core.cult_leader.verdict_lock': ('Магия скована', 'Magic is sealed'),
    'subtitles.pohsmp_core.cult_leader.verdict_end': ('Приговор снят', 'Verdict lifted'),
    'subtitles.pohsmp_core.cult_leader.phase': ('Глава Культа ярится', 'Cult Leader rages'),
    'subtitles.pohsmp_core.cult_leader.firewall': ('Вспыхивает стена огня', 'Wall of fire ignites'),
    'subtitles.pohsmp_core.cult_leader.firewall_loop': ('Ревёт стена огня', 'Wall of fire roars'),
    'subtitles.pohsmp_core.cult_leader.summon': ('Культист призван', 'Cultist summoned'),
    'subtitles.pohsmp_core.music.cult_leader': ('Музыка: Глава Культа', 'Music: Cult Leader'),
}


def lang():
    for i, name in enumerate(('ru_ru', 'en_us')):
        p = os.path.join(M.A, 'lang', name + '.json')
        d = json.load(open(p, encoding='utf-8'))
        for k, v in LANG.items():
            d[k] = v[i]
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')
        M.WRITTEN.append('lang/%s.json (+%d ключей)' % (name, len(LANG)))


def S_(name, **kw):
    o = {'name': name}
    o.update(kw)
    return o


SOUNDS = {
    'cult_leader.spawn': [S_('irons_spellbooks:fire_boss/fire_boss_summon_scythe', pitch=0.75, volume=1.4)],
    'cult_leader.death': [S_('irons_spellbooks:fire_boss/fire_boss_death', pitch=0.9)],
    'cult_leader.death_final': [S_('irons_spellbooks:fire_boss/fire_boss_death_final', pitch=0.85)],
    'cult_leader.verdict': [S_('irons_spellbooks:fire_boss/fire_boss_enter_soul', pitch=0.65, volume=1.3)],
    'cult_leader.verdict_lock': [S_('minecraft:block/respawn_anchor/deplete1', pitch=0.6), S_('minecraft:block/respawn_anchor/deplete2', pitch=0.6)],
    'cult_leader.verdict_end': [S_('minecraft:block/respawn_anchor/charge1', pitch=0.8), S_('minecraft:block/respawn_anchor/charge2', pitch=0.8)],
    'cult_leader.phase': [S_('irons_spellbooks:fire_boss/fire_boss_stance_break', pitch=0.85)],
    'cult_leader.firewall': [S_('irons_spellbooks:fire_boss/fire_boss_summon_scythe', pitch=0.55, volume=1.5)],
    'cult_leader.firewall_loop': [S_('minecraft:fire/fire', volume=1.0, pitch=0.7)],
    'cult_leader.summon': [S_('irons_spellbooks:fire_boss/fire_boss_fireball', pitch=0.7)],
}


def sounds():
    p = os.path.join(M.A, 'sounds.json')
    d = json.load(open(p, encoding='utf-8'))
    for k, v in SOUNDS.items():
        d[k] = {'subtitle': 'subtitles.pohsmp_core.' + k, 'sounds': v}
    d['music.cult_leader'] = {'category': 'record', 'subtitle': 'subtitles.pohsmp_core.music.cult_leader',
                              'comment': 'ЗАГЛУШКА до трека владельца: фон боя Тироса (Iron\'s). Трек владельца — pohsmp_core:music/cult_leader (stream).',
                              'sounds': [S_('irons_spellbooks:fire_boss/music/backtrack', stream=True, volume=0.6)]}
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write('\n')
    M.WRITTEN.append('sounds.json (+%d событий)' % (len(SOUNDS) + 1))


# ================================================================== проверочные кадры
def _tint(name, color, size=None, bg=None):
    im = Image.open(os.path.join(M.A, 'textures', 'sigil', name + '.png')).convert('RGBA')
    if size:
        im = im.resize(size, Image.LANCZOS)
    a = np.asarray(im, np.float32)
    c = np.array(M.hx(color)[:3], np.float32)
    o = np.zeros_like(a)
    o[..., :3] = c
    o[..., 3] = a[..., 3]
    return Image.fromarray(o.astype(np.uint8), 'RGBA')


def _glow(img, r=6, k=1.0):
    p = 3 * r
    big = Image.new('RGBA', (img.width + 2 * p, img.height + 2 * p), (0, 0, 0, 0))
    big.alpha_composite(img, (p, p))
    g = big.filter(ImageFilter.GaussianBlur(r))
    a = np.asarray(g, np.float32)
    a[..., 3] = np.clip(a[..., 3] * k, 0, 255)
    return Image.fromarray(a.astype(np.uint8), 'RGBA'), p


def _paste_glow(img, t, xy, r=6, k=1.2):
    g, p = _glow(t, r, k)
    img.alpha_composite(g, (int(xy[0] - p), int(xy[1] - p)))
    img.alpha_composite(t, (int(xy[0]), int(xy[1])))


def _ring_text(img, text, cx, cy, r, size, color, start=-90):
    """Надпись по окружности (как слой text печати) — только для проверочного листа."""
    fnt = ImageFont.truetype(os.path.join(HERE, 'fonts', 'CormorantGaramond-BoldItalic-cyrillic.woff'), size)
    ang = math.radians(start)
    for ch in text:
        w = max(4, fnt.getlength(ch))
        tile = Image.new('RGBA', (size * 2, size * 2), (0, 0, 0, 0))
        ImageDraw.Draw(tile).text((size - w / 2, size * 0.35), ch, font=fnt, fill=color)
        rot = tile.rotate(-math.degrees(ang) - 90, resample=Image.BICUBIC)
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
        img.alpha_composite(rot, (int(x - size), int(y - size)))
        ang += (w + size * 0.08) / r


def _font(sz):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def sheet_fx():
    """Сверху на арену: печать «Приговора» r24, стена огня r28, знак культа, плюс текстуры отдельно."""
    Wd, Hd = 1800, 1000
    img = Image.new('RGBA', (Wd, Hd), M.hx('#120a08'))
    d = ImageDraw.Draw(img)
    f1, f2 = _font(26), _font(18)
    # арена: 1 блок = 15 px, центр (520, 520)
    cx, cy, k = 500, 520, 15.5
    for x in range(-34, 35, 2):
        for y in range(-34, 35, 2):
            if (x + y) % 4 == 0:
                d.rectangle([cx + x * k, cy + y * k, cx + (x + 2) * k, cy + (y + 2) * k], fill=M.hx('#1c1210'))
    R = int(R_VERDICT * k)
    seal = _tint('mellisto_verdict', SEAL, (2 * R, 2 * R))
    _paste_glow(img, seal, (cx - R, cy - R), 8)
    txt = 'ПРИГОВОР МЕЛЛИСТО ✦ МАГИЯ ПОД ЗАПРЕТОМ ✦ '
    _ring_text(img, txt * 2, cx, cy, R * 0.748, 20, M.hx(FIRE_HOT))
    Rw = int((R_WALL + 1.5) * k)
    sc = _tint('cult_scorch_ring', '#3a1408', (2 * Rw, 2 * Rw))
    img.alpha_composite(sc, (cx - Rw, cy - Rw))
    rng = random.Random(5)
    tongue = _tint('cult_flame_tongue', FIRE, (14, 56))
    tongue2 = _tint('cult_flame_tongue', FIRE_HOT, (10, 34))
    for i in range(160):
        a = 2 * math.pi * i / 160 + rng.random() * 0.02
        x, y = cx + R_WALL * k * math.cos(a), cy + R_WALL * k * math.sin(a)
        t = tongue if i % 3 else tongue2
        _paste_glow(img, t, (int(x - t.width / 2), int(y - t.height + 6)), 3, 1.4)
    em = _tint('cult_emblem', FIRE, (100, 100))
    _paste_glow(img, em, (cx - 50, cy - 50), 5)
    d.text((24, 18), 'T26 — арена сверху: «Приговор Меллисто» r24 (печать), стена огня r28 (фаза 3), знак культа под боссом', font=f1, fill=(240, 226, 214))
    d.text((24, 52), 'надпись по кольцу печати — слоем text: «ПРИГОВОР МЕЛЛИСТО ✦ МАГИЯ ПОД ЗАПРЕТОМ ✦»', font=f2, fill=(200, 180, 168))
    # справа — текстуры
    x0 = 1060
    items = [('mellisto_verdict', SEAL, 330, 'mellisto_verdict — печать r24'), ('cult_emblem', FIRE, 210, 'cult_emblem'),
             ('cult_verdict_mark', SEAL, 210, 'cult_verdict_mark (над головой)')]
    xx, yy = x0, 110
    for n, c, s, lab in items:
        t = _tint(n, c, (s, s))
        _paste_glow(img, t, (xx, yy), 6)
        d.text((xx, yy + s + 6), lab, font=f2, fill=(220, 200, 190))
        if n == 'mellisto_verdict':
            xx, yy = x0 + 360, 110
        else:
            yy += s + 40
    t = _tint('cult_flame_tongue', FIRE, (90, 360))
    _paste_glow(img, t, (x0 + 40, 520), 6)
    d.text((x0, 890), 'cult_flame_tongue (curtain)', font=f2, fill=(220, 200, 190))
    sc = _tint('cult_scorch_ring', FIRE_DEEP, (300, 300))
    img.alpha_composite(sc, (x0 + 200, 560))
    d.text((x0 + 230, 870), 'cult_scorch_ring (decal r29.5)', font=f2, fill=(220, 200, 190))
    img.convert('RGB').save(os.path.join(MEDIA, 't26_fx.jpg'), quality=90)
    print('wrote docs/media/t26_fx.jpg')


def sheet_ui(bar):
    Wd, Hd = 1600, 900
    img = Image.new('RGBA', (Wd, Hd), M.hx('#141010'))
    d = ImageDraw.Draw(img)
    f1, f2 = _font(24), _font(18)
    d.text((24, 16), 'T26 — полоса босса (×4, слева Тирос Iron\'s, справа наша), титр ru/en, иконка «Приговора»', font=f1, fill=(240, 226, 214))
    ty = M.jar_img(M.I + 'textures/gui/sprites/boss_bars/tyros_bossbar.png')

    def bar_at(src, x, y, p):
        e = src.crop((0, 0, 192, 18))
        f = src.crop((0, 18, 192, 36))
        w = int(3 + p * (192 - 6))
        e.alpha_composite(f.crop((0, 0, w, 18)), (0, 0)) if p > 0 else None
        img.alpha_composite(e.resize((192 * 4, 72), Image.NEAREST), (x, y))
    bar_at(ty.copy(), 24, 70, 0.6)
    bar_at(bar.copy(), 24, 170, 0.6)
    bar_at(bar.copy(), 24, 260, 1.0)
    bar_at(bar.copy(), 24, 350, 0.15)
    d.text((24 + 192 * 4 + 20, 92), 'tyros_bossbar (исходник)', font=f2, fill=(200, 180, 168))
    d.text((24 + 192 * 4 + 20, 192), 'cult_leader_bossbar — 60%', font=f2, fill=(200, 180, 168))
    d.text((24 + 192 * 4 + 20, 282), '100%', font=f2, fill=(200, 180, 168))
    d.text((24 + 192 * 4 + 20, 372), '15%', font=f2, fill=(200, 180, 168))
    for i, lang_ in enumerate(('ru', 'en')):
        t = Image.open(os.path.join(M.A, 'textures/gui/title/cult_leader_%s.png' % lang_)).convert('RGBA')
        bg = Image.new('RGBA', (1024, 192), M.hx('#2a1c18'))
        bg.alpha_composite(t)
        img.alpha_composite(bg, (24, 450 + i * 210))
    ic = Image.open(os.path.join(M.A, 'textures/mob_effect/mellisto_verdict.png')).convert('RGBA')
    img.alpha_composite(ic.resize((144, 144), Image.NEAREST), (1120, 470))
    d.text((1120, 625), 'mob_effect/mellisto_verdict (18×18)', font=f2, fill=(200, 180, 168))
    img.convert('RGB').save(os.path.join(MEDIA, 't26_ui.jpg'), quality=92)
    print('wrote docs/media/t26_ui.jpg')


def sheet_textures():
    """Исходник Тироса (×) против нашей 512: те же цвета, больше деталей; глоумаска, облик души, культист."""
    import gen_cult_leader as G
    Wd, Hd = 1800, 1060
    img = Image.new('RGBA', (Wd, Hd), M.hx('#141010'))
    d = ImageDraw.Draw(img)
    f1, f2 = _font(24), _font(18)
    d.text((24, 14), 'T26 — текстуры: исходник Iron\'s (96 → ×5.33) | наша 512 (атлас 128 ед.) | глоумаска | облик души | культист', font=f1, fill=(240, 226, 214))
    T_ = os.path.join(M.A, 'textures', 'entity', 'cult_leader')
    src = M.jar_img(M.I + 'textures/entity/fire_boss/tyros.png')
    s96 = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    s96.paste(src, (0, 0))
    tiles = [(s96.resize((512, 512), Image.NEAREST), 'tyros.png (исходник, 96)'),
             (Image.open(os.path.join(T_, 'cult_leader.png')).convert('RGBA'), 'cult_leader.png'),
             (Image.open(os.path.join(T_, 'cult_leader_glowmask.png')).convert('RGBA'), 'cult_leader_glowmask.png')]
    for i, (t, lab) in enumerate(tiles):
        bg = Image.new('RGBA', t.size, M.hx('#3a3a3a') if 'glow' not in lab else M.hx('#000000'))
        bg.alpha_composite(t)
        img.alpha_composite(bg.resize((420, 420), Image.NEAREST), (24 + i * 440, 60))
        d.text((24 + i * 440, 486), lab, font=f2, fill=(220, 200, 190))
    # крупно: грудь (рёбра доспеха) — до/после
    box = (64, 16, 96, 40)
    a1 = s96.crop(box).resize((256, 192), Image.NEAREST)
    a2 = Image.open(os.path.join(T_, 'cult_leader.png')).convert('RGBA').crop(tuple(v * 4 for v in box)).resize((256, 192), Image.NEAREST)
    img.alpha_composite(a1, (1340, 60))
    img.alpha_composite(a2, (1340, 270))
    d.text((1340, 470), 'доспех груди: было / стало', font=f2, fill=(220, 200, 190))
    tiles = [(Image.open(os.path.join(T_, 'cult_leader_soul_mode.png')).convert('RGBA'), 'cult_leader_soul_mode.png'),
             (Image.open(os.path.join(T_, 'fire_cultist.png')).convert('RGBA'), 'fire_cultist.png'),
             (Image.open(os.path.join(T_, 'fire_cultist_glowmask.png')).convert('RGBA'), 'fire_cultist_glowmask.png'),
             (Image.open(os.path.join(T_, 'cult_leader_flame.png')).convert('RGBA'), 'cult_leader_flame.png')]
    for i, (t, lab) in enumerate(tiles):
        bg = Image.new('RGBA', t.size, M.hx('#3a3a3a') if 'glow' not in lab else M.hx('#000000'))
        bg.alpha_composite(t)
        sz = (420, 420) if t.width == t.height else (60, 480)
        img.alpha_composite(bg.resize(sz, Image.NEAREST), (24 + i * 440, 530))
        d.text((24 + i * 440, 530 + sz[1] + 6), lab, font=f2, fill=(220, 200, 190))
    img.convert('RGB').save(os.path.join(MEDIA, 't26_textures.jpg'), quality=90)
    print('wrote docs/media/t26_textures.jpg')


def shots(args):
    import cult_leader_render as R
    three = args[args.index('--three') + 1] if '--three' in args else None
    R.sheet(os.path.join(MEDIA, 't26_model.jpg'), {'cols': 4, 'cells': [
        {'model': 'cult_leader', 'yaw': 0, 'pitch': 5, 'label': 'Глава Культа', 'sub': 'спереди'},
        {'model': 'cult_leader', 'yaw': 180, 'label': 'сзади', 'sub': 'рваный плащ, знак культа'},
        {'model': 'cult_leader', 'yaw': 10, 'pitch': 3, 'dist': 1.0, 'ty': 30, 'dim': 0.35, 'label': 'в темноте', 'sub': 'глоумаска: глаза, медальон, венец'},
        {'model': 'cult_leader', 'soul': True, 'yaw': -30, 'label': 'облик души', 'sub': 'фаза 3: ярость'},
        {'model': 'tyros', 'yaw': 25, 'label': 'Эхо Тироса', 'sub': 'исходник Iron\'s — для сравнения'},
        {'model': 'cult_leader', 'yaw': 25, 'label': 'Глава Культа', 'sub': 'тот же ракурс'},
        {'model': 'fire_cultist', 'anim': 'blank', 'yaw': 20, 'label': 'огненный культист', 'sub': 'облик для огненных магов Iron\'s'},
        {'model': 'fire_cultist', 'anim': 'charge_raised_hand', 't': 0.6, 'yaw': 200, 'label': 'культист сзади', 'sub': 'каст'},
    ]}, three, (1600, 1000))
    cells = []
    for t, lab in ((0.3, '0.3 с — в проёме огня'), (2.5, '2.5 с — идёт сквозь пламя'), (5.0, '5.0 с'), (6.3, '6.3 с — взмах косой'),
                   (7.6, '7.6 с — поза, титр')):
        cells.append({'model': 'cult_leader', 'anim': 'fire_boss_spawn', 't': t, 'yaw': 30, 'pitch': 10, 'dist': 3.0, 'ty': 20,
                      'label': 'появление', 'sub': lab})
    for t, lab in ((0.4, '0.4 с — удар'), (1.4, '1.4 с — шатается'), (2.6, '2.6 с — на коленях, пламя гаснет'), (3.5, '3.5 с — конец ролика'),
                   (6.0, '6.0 с (после ролика)')):
        cells.append({'model': 'cult_leader', 'anim': 'fire_boss_death', 't': t, 'yaw': 35, 'pitch': 8, 'dist': 2.4, 'ty': 18,
                      'label': 'смерть', 'sub': lab, 'noGlow': t >= 2.6})
    R.sheet(os.path.join(MEDIA, 't26_poses.jpg'), {'cols': 5, 'cells': cells}, three, (1800, 820))


def run(mod, args):
    global M
    M = mod
    F.WRITTEN = M.WRITTEN
    textures()
    sigils()
    effects()
    bar = bossbar()
    title(bar)
    icon()
    lang()
    sounds()
    os.makedirs(MEDIA, exist_ok=True)
    sheet_fx()
    sheet_ui(bar)
    sheet_textures()
    import gen_cult_leader_extra as X
    X.run(M, sys.modules[__name__], args)
    if '--shots' in args:
        shots(args)
    if '--html' in args:
        import cult_leader_render as R
        with open(os.path.join(HERE, 'cult_leader_preview.html'), 'w', encoding='utf-8') as fh:
            fh.write(R.page(['cult_leader', 'fire_cultist', 'tyros', 'pyromancer'], anims=R.iron_anims()))
        print('wrote tools/cult_leader_preview.html')
