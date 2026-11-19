#!/usr/bin/env python3
"""
T22 — визуальная часть школы «Иллюзии» (pohsmp_core:illusion). ТЗ: docs/specs/tasks/T22_illusion_school.md.
Свитки — tools/gen_illusion_scrolls.py (не здесь). Анимации игрока — tools/gen_player_anims.py (раздел T22).

Палитра школы: перламутрово-лиловый #C9A8FF, блики розовый #FFB8E6 и голубой #9AE6FF, тень #3A2A5A.
Характер: края «плывут» (двоится, мерцает), стекло и зеркало, бабочки; звуки — звон стекла, шёпот, треск зеркала.
Правило владельца: никаких лучей / нитей от заклинателя к цели (docs/inbox/README.md).

Пишет (src/main/resources/assets/pohsmp_core/):
  textures/sigil/  illusion_seal, illusion_core, illusion_crown, school_illusion_band   — тема школы (как T06, gen_school_themes.py)
                   illusion_maze, illusion_nightmare, illusion_dream, illusion_phantom    — печати Высших/Мифического и метка
                   illusion_mirror_eye, illusion_veil_ring                                — малые печати
                   mote_glass, mote_butterfly, mote_butterfly_side                        — спрайты (осколок, бабочка анфас и в профиль)
  textures/fx/     illusion_world_cracks (1024, трещины мира), illusion_haze (марево), illusion_mirror_wall (256, материал
                   зеркальной стены, непрозрачный), illusion_mirror_wall_cracks (256, трещины поверх стены, светятся)
                   «Сон бабочки»: illusion_wound_butterfly (атлас 4 кадра), illusion_dream_death (экран «смерть сна»),
                   illusion_dream_ripple; УСТАРЕЛО — illusion_wake_grid, illusion_wake_shards (.png + .json): стекло пробуждения,
                   удалить вместе с кодом DreamScreen. Каст, мир сна и пробуждение «Небесная бабочка» — tools/gen_celestial_butterfly.py
  sigils/          illusion_seal, illusion_crown, school_illusion, illusion_* (печати заклинаний)
  fx/              school_illusion, school_illusion_cast, _cast_crown, _cast_divine, illusion_*.json (касты и срабатывания)
  fx/styles/       illusion.json
  fx/meshes/       illusion_nightmare (безликое чудовище), illusion_mirror_wall (модуль стены 1×3), illusion_dome (купол r=1),
                   illusion_butterfly (стеклянная бабочка)
  textures/gui/spell_icons/<8 заклинаний>.png (16×16), textures/mob_effect/<статусы>.png (18×18),
  textures/item/illusion_prism.png + models/item/illusion_prism.json, textures/gui/school/illusion.png (значок школы 16×16)

Точки эффектов (ctx): caster — заклинатель, target — цель; point:<имя> — где сказано в комментарии эффекта.
Время — тики, углы — градусы, размеры — блоки.  Запуск:  python3 tools/gen_illusion_fx.py [--sheet]
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
import gen_school_themes as gst  # noqa: E402
from gen_school_themes import Pen, TAU, bez, local, rot, jag, star4, eye, ticks, dots, polygon  # noqa: E402

A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
OUT_SIGIL = os.path.join(A, 'textures', 'sigil')
OUT_FX = os.path.join(A, 'textures', 'fx')
WRITTEN = []

# ------------------------------------------------------------------ палитра школы
LILAC, PINK, BLUE, SHADOW, PEARL, WHITE = '#C9A8FF', '#FFB8E6', '#9AE6FF', '#3A2A5A', '#EFE6FF', '#FFFFFF'
DEEP = '#1A1028'          # тьма кошмара
NIGHT = '#2A1838'


def save_sigil(p, name, glow=0.5, glow_r=3.0):
    a = gst.save_sigil(p, name, glow, glow_r)
    WRITTEN.append('textures/sigil/%s.png' % name)
    return a


# ================================================================== рисовальные мотивы
def butterfly_shape(s=1.0):
    """Контуры крыльев правой половины (x ≥ 0), в долях s; ось тела — x = 0, голова вверху (y < 0).
    Возвращает (верхнее крыло, нижнее крыло) — замкнутые ломаные."""
    up = (bez((0.04, -0.06), (0.22, -0.72), (0.86, -1.02), (1.0, -0.66), 26)
          + bez((1.0, -0.66), (1.08, -0.36), (0.8, -0.12), (0.62, -0.04), 14)[1:]
          + bez((0.62, -0.04), (0.42, 0.02), (0.2, 0.02), (0.04, 0.02), 10)[1:])
    lo = (bez((0.04, 0.04), (0.36, 0.0), (0.74, 0.12), (0.72, 0.42), 16)
          + bez((0.72, 0.42), (0.7, 0.62), (0.52, 0.66), (0.44, 0.9), 12)[1:]      # хвостик
          + bez((0.44, 0.9), (0.34, 0.74), (0.14, 0.6), (0.04, 0.22), 14)[1:])
    sc = lambda pts: [(x * s, y * s) for x, y in pts]
    return sc(up), sc(lo)


def butterfly(p, x, y, s, ang=0.0, lw=2.0, fill=None, veins=True, body=True, open_=1.0):
    """Бабочка: контуры крыльев, жилки, тело, усики. open_ < 1 — крылья сложены (сжаты по x)."""
    up, lo = butterfly_shape(s)
    for side in (1, -1):
        for wing in (up, lo):
            pts = local((x, y), ang, [(side * px * open_, py) for px, py in wing])
            if fill is not None:
                p.poly(pts, fill)
            p.line(pts + [pts[0]], lw)
        if veins:
            for (ex, ey) in ((0.92, -0.72), (0.98, -0.42), (0.7, -0.86), (0.66, -0.12)):
                pts = bez((0.06, -0.02), (0.3, -0.1), (ex * 0.6, ey * 0.7), (ex * 0.9, ey * 0.92), 12)
                p.line(local((x, y), ang, [(side * px * s * open_, py * s) for px, py in pts]), lw * 0.55)
            for (ex, ey) in ((0.64, 0.4), (0.44, 0.78), (0.26, 0.5)):
                pts = bez((0.06, 0.06), (0.2, 0.12), (ex * 0.6, ey * 0.6), (ex * 0.92, ey * 0.92), 10)
                p.line(local((x, y), ang, [(side * px * s * open_, py * s) for px, py in pts]), lw * 0.55)
            # «глазок» на верхнем крыле
            cx, cy = local((x, y), ang, [(side * 0.62 * s * open_, -0.56 * s)])[0]
            p.circle(cx, cy, s * 0.1 * max(0.4, open_), lw * 0.6)
    if body:
        p.line(local((x, y), ang, [(0, -0.22 * s), (0, 0.5 * s)]), lw * 1.6)
        p.dot(*local((x, y), ang, [(0, -0.26 * s)])[0], lw * 1.4)
        for side in (1, -1):
            p.line(local((x, y), ang, bez((0, -0.28 * s), (side * 0.06 * s, -0.5 * s), (side * 0.16 * s, -0.62 * s),
                                          (side * 0.26 * s, -0.7 * s), 10)), lw * 0.6)


def mirror_eye(p, x, y, w, h, lw=2.0, ang=0.0, ghost=150):
    """Око над чертой зеркала и его отражение (бледнее, пунктиром нижнее веко)."""
    eye(p, x, y - h * 0.95, w, h, ang, lw, slit=False, iris=0.36)
    p.line(local((x, y), ang, [(-w * 1.25, 0), (w * 1.25, 0)]), lw * 0.8)
    up = [(-w + 2 * w * i / 30, h * math.sin(math.pi * i / 30)) for i in range(31)]
    dn = [(-w + 2 * w * i / 30, -h * math.sin(math.pi * i / 30)) for i in range(31)]
    cy = y + h * 0.95
    p.line(local((x, cy), ang, dn), lw * 0.8, fill=ghost)
    for i in range(0, 30, 3):                                   # отражение — пунктиром
        p.line(local((x, cy), ang, up[i:i + 2]), lw * 0.8, fill=ghost)
    ir = h * 0.36 * 2.2
    p.circle(x, cy, ir, lw * 0.6, fill=ghost)


def shard(p, x, y, L, W, ang, fill=255, gleam=True, lw=1.6):
    """Осколок-игла: вытянутый ромб с бликом вдоль ребра."""
    pts = local((x, y), ang, [(0, 0), (L * 0.32, -W), (L, 0), (L * 0.32, W * 0.7)])
    p.poly(pts, fill)
    if gleam:
        p.line(local((x, y), ang, [(L * 0.1, -W * 0.15), (L * 0.85, -W * 0.05)]), lw, fill=255)


def crack(p, rng, a, b, w, depth=4, amp=0.22, branches=2, fill=255):
    pts = jag(rng, a, b, depth, amp)
    n = len(pts)
    p.taper(pts, [w * (1 - 0.6 * i / (n - 1)) + 0.4 for i in range(n)], fill)
    for _ in range(branches):
        i = rng.randint(n // 4, n * 3 // 4)
        x, y = pts[i]
        ang = math.atan2(b[1] - a[1], b[0] - a[0]) + rng.choice([-1, 1]) * (0.5 + rng.random() * 0.7)
        L = math.hypot(b[0] - a[0], b[1] - a[1]) * (0.18 + rng.random() * 0.22)
        bp = jag(rng, (x, y), (x + math.cos(ang) * L, y + math.sin(ang) * L), 3, 0.25)
        p.taper(bp, [w * 0.6 * (1 - k / len(bp)) + 0.3 for k in range(len(bp))], fill)


def arc_clip(p, cx, cy, r, rmin, rmax, w, fill=255, n=360):
    """Окружность (cx, cy, r), видимая только в кольце rmin..rmax от центра холста."""
    seg = []
    for i in range(n + 1):
        a = TAU * i / n
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        d = math.hypot(x - p.cx, y - p.cy)
        if rmin <= d <= rmax:
            seg.append((x, y))
        else:
            if len(seg) > 1:
                p.line(seg, w, fill, caps=False)
            seg = []
    if len(seg) > 1:
        p.line(seg, w, fill, caps=False)


# ================================================================== тема школы (как T06)
def illusion_seal(p):
    """Печать школы: обод из призм, 12 «зеркальных окон» с бликами, калейдоскопическая решётка, 6 бабочек, трещины."""
    rng = random.Random(2201)
    p.ring(246, 4.5)
    p.ring(237, 1.6)
    for i in range(48):                                         # призмочки по ободу
        a = i * TAU / 48
        x, y = p.P(241.5, a)
        s = 3.6
        pts = local((x, y), a, [(-s, 0), (0, -s * 0.8), (s, 0), (0, s * 0.8)])
        if i % 2:
            p.poly(pts)
        else:
            p.line(pts + [pts[0]], 1.2)
    p.ring(230, 2.6)
    for i in range(12):                                         # зеркальные окна: стрельчатая арка наружу
        a0, a1 = (i + 0.08) * TAU / 12, (i + 0.92) * TAU / 12
        am = (a0 + a1) / 2
        r0, r1, rt = 198, 216, 228
        outline = [p.P(r0, a0)] + [p.P(r1, a0 + (a1 - a0) * k / 16) for k in range(17)] + [p.P(r0, a1)]
        tip = p.P(rt, am)
        left = bez(p.P(r1, a0), p.P(r1 + 7, a0 + 0.03), p.P(rt - 3, am - 0.06), tip, 10)
        right = bez(tip, p.P(rt - 3, am + 0.06), p.P(r1 + 7, a1 - 0.03), p.P(r1, a1), 10)
        pane = [p.P(r0, a0)] + left + right + [p.P(r0, a1)]
        p.poly(pane, 46)                                        # стекло — бледная заливка
        p.line(pane + [pane[0]], 2.2)
        for k, off in enumerate((-0.07, -0.02)):                # косые блики
            p.line([p.P(r0 + 3, am + off - 0.03), p.P(r1 + 2, am + off + 0.05)], 1.6 - 0.6 * k, fill=220)
        p.dot(*p.P(r0 - 6, am), 2.4)
    p.ring(194, 3.2)
    p.ring(188, 1.2)
    for k in range(12):                                         # калейдоскоп: дуги 12 окружностей
        a = k * TAU / 12
        cx, cy = p.P(124, a)
        arc_clip(p, cx, cy, 76, 106, 186, 1.6, 200)
    for k in range(6):                                          # бабочки поверх решётки (под ними решётка стёрта)
        a = (k + 0.5) * TAU / 6
        x, y = p.P(150, a)
        up, lo = butterfly_shape(30)
        for side in (1, -1):
            for wing in (up, lo):
                pts = local((x, y), a + math.pi / 2, [(side * px * 1.15, py * 1.15) for px, py in wing])
                p.poly(pts, 0)
        butterfly(p, x, y, 30, a + math.pi / 2, 2.0, fill=70)
    for k in range(6):                                          # между бабочками — ромб-призма
        a = k * TAU / 6
        x, y = p.P(150, a)
        star4(p, x, y, 12, a, 0.3)
    for _ in range(4):                                          # трещины зеркала
        a = rng.random() * TAU
        r0 = 108 + rng.random() * 20
        crack(p, rng, p.P(r0, a), p.P(232, a + rng.uniform(-0.25, 0.25)), 2.2, depth=4, amp=0.18, branches=2)
    p.ring(104, 3.5)
    p.ring(98, 1.2)


def illusion_core(p):
    """Ядро: око над чертой зеркала и его отражение, ромб-рамка, четыре звёздочки-блика."""
    p.ring(94, 3)
    p.ring(88, 1)
    d = [(p.cx, p.cy - 84), (p.cx + 84, p.cy), (p.cx, p.cy + 84), (p.cx - 84, p.cy)]
    p.line(d + [d[0]], 2.6)
    mirror_eye(p, p.cx, p.cy, 44, 22, 3.2, ghost=140)
    for k in range(4):
        x, y = p.P(68, k * TAU / 4 + math.pi / 4)
        star4(p, x, y, 8, k * TAU / 4, 0.25)


def illusion_crown(p):
    """Венец: 14 зеркальных игл наружу (длинные/короткие), бабочки между ними, кольцо призм, звезда-призма в центре."""
    rng = random.Random(2202)
    p.ring(140, 3.5)
    p.ring(128, 1.4)
    for i in range(14):
        a = i * TAU / 14
        L = 104 if i % 2 == 0 else 70
        x, y = p.P(142, a)
        shard(p, x, y, L, 13 if i % 2 == 0 else 9, a, fill=120)
        pts = local((x, y), a, [(0, 0), (L * 0.32, -13), (L, 0), (L * 0.32, 9)])
        p.line(pts + [pts[0]], 2.2)
    for i in range(7):
        a = (i + 0.5) * TAU / 7 + TAU / 28
        x, y = p.P(206, a)
        butterfly(p, x, y, 16, a + math.pi / 2, 1.6, fill=60, veins=False)
    for i in range(24):
        x, y = p.P(114, i * TAU / 24)
        p.dot(x, y, 3.2 if i % 2 else 1.8)
    pts = []
    for k in range(12):
        a = k * TAU / 12 - math.pi / 2
        pts.append(p.P(70 if k % 2 == 0 else 30, a))
    p.line(pts + [pts[0]], 3)
    for k in range(6):
        p.line([p.P(30, k * TAU / 6 + TAU / 12 - math.pi / 2), p.P(70, k * TAU / 6 - math.pi / 2 + TAU / 6)], 1.2, fill=180)
    p.dot(p.cx, p.cy, 9)
    for _ in range(3):
        a = rng.random() * TAU
        crack(p, rng, p.P(40, a), p.P(130, a + 0.2), 1.6, depth=3, branches=1)


def illusion_band(p):
    """Лента: бабочки и зеркальные очи по очереди, ромбы между ними; кромки — пунктиром «отражения»."""
    p.line([(0, 6), (p.w, 6)], 3, caps=False)
    for i in range(64):                                         # нижняя кромка — пунктир (отражение верхней)
        x0 = i * p.w / 64
        p.line([(x0 + 2, 122), (x0 + p.w / 64 * 0.6, 122)], 2.4, fill=170)
    n = 8
    for i in range(n):
        x = (i + 0.5) * p.w / n
        if i % 2 == 0:
            butterfly(p, x, 66, 46, 0, 2.6, fill=60)
        else:
            mirror_eye(p, x, 64, 34, 15, 2.6, ghost=150)
        xd = (i + 1) * p.w / n
        star4(p, xd % p.w, 64, 13, 0, 0.32)
        p.dot(xd % p.w, 36, 2.2)
        p.dot(xd % p.w, 92, 2.2)


# ================================================================== печати заклинаний
def illusion_maze(p):
    """«Зеркальный лабиринт»: круглый лабиринт (кольца с проходами, радиальные стенки), зеркальное око в центре."""
    rng = random.Random(2206)
    p.ring(248, 5)
    p.ring(238, 1.6)
    ticks(p, 236, 96, 7, 1.6, every=4)
    rings = [58, 88, 118, 148, 178, 208]
    for k, r in enumerate(rings):
        gaps = sorted(rng.uniform(0, TAU) for _ in range(2 + k // 2))
        wgap = 22 / r
        for j, g in enumerate(gaps):                            # кольцо стенки с проходами
            nxt = gaps[(j + 1) % len(gaps)] + (TAU if j == len(gaps) - 1 else 0)
            p.arc(r, g + wgap, nxt - wgap * 0.2, 3.4)
        if k + 1 < len(rings):                                  # радиальные стенки к следующему кольцу
            for _ in range(3 + k):
                a = rng.uniform(0, TAU)
                p.line([p.P(r, a), p.P(rings[k + 1], a)], 3.4)
                if rng.random() < 0.4:                          # «зеркало» на стенке — маленький ромб
                    x, y = p.P((r + rings[k + 1]) / 2, a)
                    star4(p, x, y, 6, a, 0.35)
    for i in range(16):                                         # отражения: бледные дуги снаружи
        a = i * TAU / 16
        p.arc(222, a + 0.04, a + TAU / 16 - 0.04, 2.0, fill=140)
    mirror_eye(p, p.cx, p.cy, 26, 12, 2.6, ghost=150)


def illusion_nightmare(p):
    """«Кошмар наяву»: венок из 16 пустых очей (без зрачков), когти-полумесяцы, безликий овал в центре, капли тьмы."""
    rng = random.Random(2207)
    p.ring(246, 4)
    p.ring(236, 1.4)
    for i in range(16):                                         # очи: открытые пустые и закрытые по очереди
        a = i * TAU / 16
        x, y = p.P(208, a)
        if i % 2 == 0:
            up = [(-22 + 44 * k / 30, 11 * math.sin(math.pi * k / 30)) for k in range(31)]
            dn = [(-22 + 44 * k / 30, -11 * math.sin(math.pi * k / 30)) for k in range(31)]
            p.line(local((x, y), a + math.pi / 2, up), 2.6)
            p.line(local((x, y), a + math.pi / 2, dn), 2.6)
            p.circle(x, y, 6, 1.4)                              # пустая радужка
        else:
            dn = [(-18 + 36 * k / 30, 7 * math.sin(math.pi * k / 30)) for k in range(31)]
            p.line(local((x, y), a + math.pi / 2, dn), 2.6)
            for t in (0.2, 0.4, 0.6, 0.8):                      # ресницы вниз — слёзы
                px, py = -18 + 36 * t, 7 * math.sin(math.pi * t)
                p.line(local((x, y), a + math.pi / 2, [(px, py), (px * 1.1, py + 8)]), 1.4)
    p.ring(182, 3)
    for i in range(24):                                         # когти-полумесяцы
        a = i * TAU / 24
        pts = [p.P(176 - 34 * t, a + 0.16 * math.sin(math.pi * t * 0.9)) for t in np.linspace(0, 1, 16)]
        p.taper(pts, [5 * (1 - t) + 0.6 for t in np.linspace(0, 1, 16)])
    p.ring(136, 2)
    for i in range(10):                                         # капли тьмы с обода к центру
        a = i * TAU / 10 + 0.15
        x, y = p.P(122, a)
        gst.teardrop(p, x, y, a + math.pi, 5, highlight=False)
    p.ring(104, 3.2)
    # безликое лицо: овал, пустой, тонкая тень-«маска» без черт
    pts = [(p.cx + 44 * math.cos(t), p.cy + 62 * math.sin(t)) for t in np.linspace(0, TAU, 80)]
    p.line(pts, 3.2)
    pts = [(p.cx + 34 * math.cos(t), p.cy + 50 * math.sin(t)) for t in np.linspace(0, TAU, 80)]
    p.poly(pts, 50)
    for _ in range(5):
        a = rng.random() * TAU
        crack(p, rng, p.P(108, a), p.P(176, a + 0.1), 1.8, depth=3, branches=1)


def illusion_dream(p):
    """«Сон бабочки»: большая бабочка с ячейками крыльев, кольцо из 12 фаз луны, циферблат сна, трещины-«зеркало»."""
    rng = random.Random(2208)
    p.ring(248, 5)
    p.ring(240, 1.6)
    for i in range(12):                                         # фазы луны
        a = i * TAU / 12 - math.pi / 2
        x, y = p.P(222, a)
        r = 11
        p.circle(x, y, r, 1.6)
        ph = math.cos(TAU * i / 12)
        pts = [(x + r * math.cos(t), y + r * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, 20)]
        pts += [(x + ph * r * math.cos(t), y + r * math.sin(t)) for t in np.linspace(math.pi / 2, -math.pi / 2, 20)]
        p.poly(local((x, y), a, [(px - x, py - y) for px, py in pts]) if False else pts)
    p.ring(204, 2.8)
    ticks(p, 200, 60, 8, 1.6, every=5)
    p.ring(184, 1.2)
    up, lo = butterfly_shape(168)                               # большая бабочка
    for side in (1, -1):
        for wing in (up, lo):
            pts = [(p.cx + side * px, p.cy + py + 8) for px, py in wing]
            p.poly(pts, 40)
            p.line(pts + [pts[0]], 3.2)
    for side in (1, -1):                                        # ячейки: жилки ветвятся
        for (ex, ey) in ((0.94, -0.7), (0.99, -0.46), (0.74, -0.9), (0.5, -0.86), (0.8, -0.2)):
            pts = bez((0.05, -0.02), (0.28, -0.1), (ex * 0.55, ey * 0.7), (ex * 0.93, ey * 0.95), 16)
            p.line([(p.cx + side * x * 168, p.cy + y * 168 + 8) for x, y in pts], 1.8)
        for (ex, ey) in ((0.66, 0.38), (0.5, 0.74), (0.3, 0.55)):
            pts = bez((0.05, 0.06), (0.2, 0.14), (ex * 0.6, ey * 0.6), (ex * 0.93, ey * 0.93), 12)
            p.line([(p.cx + side * x * 168, p.cy + y * 168 + 8) for x, y in pts], 1.8)
        for (cx, cy, r) in ((0.62, -0.56, 0.12), (0.44, 0.44, 0.07)):   # глазки на крыльях — маленькие луны
            X, Y = p.cx + side * cx * 168, p.cy + cy * 168 + 8
            p.circle(X, Y, r * 168, 2)
            p.dot(X + side * r * 168 * 0.3, Y, r * 168 * 0.45)
        for t in np.linspace(0.15, 0.95, 9):                   # крапинки по краю верхнего крыла
            k = int(t * (len(up) - 1))
            x, y = up[k]
            p.dot(p.cx + side * x * 0.9, p.cy + y * 0.9 + 8, 2.2)
    p.line([(p.cx, p.cy - 40), (p.cx, p.cy + 96)], 5)
    p.dot(p.cx, p.cy - 46, 7)
    for side in (1, -1):
        p.line(bez((p.cx, p.cy - 48), (p.cx + side * 10, p.cy - 84), (p.cx + side * 26, p.cy - 104), (p.cx + side * 40, p.cy - 112), 14), 2)
        p.dot(p.cx + side * 40, p.cy - 112, 3.5)
    for _ in range(7):                                          # трещины, как по стеклу
        a = rng.random() * TAU
        crack(p, rng, p.P(rng.uniform(20, 80), a), p.P(236, a + rng.uniform(-0.2, 0.2)), 2.0, depth=4, branches=2, fill=210)


def illusion_phantom(p):
    """Метка «Фантомной боли»: сердце, левая половина — сплошная, правая — пунктиром (иллюзорная), трещина посередине."""
    rng = random.Random(2209)
    p.ring(240, 10)
    for i in range(24):
        a = i * TAU / 24
        p.line([p.P(214, a), p.P(198 if i % 2 else 190, a)], 6)
    heart = []
    for t in np.linspace(0, TAU, 200):
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        heart.append((p.cx + x * 9.2, p.cy + y * 9.2 + 10))
    left = [q for q in heart if q[0] <= p.cx + 0.5]
    right = [q for q in heart if q[0] >= p.cx - 0.5]
    left.sort(key=lambda q: math.atan2(q[1] - p.cy, q[0] - p.cx))
    p.poly([(x, y) for x, y in heart if x <= p.cx] + [(p.cx, p.cy + 150)], 190)
    p.line([q for q in heart if q[0] <= p.cx + 1], 12, caps=False)
    for i in range(0, len(heart), 7):                           # правая — пунктир
        seg = heart[i:i + 4]
        if all(x >= p.cx - 1 for x, _ in seg):
            p.line(seg, 10)
    pts = jag(rng, (p.cx, p.cy - 60), (p.cx, p.cy + 150), 4, 0.12)   # трещина
    p.taper(pts, [9] * len(pts), 0)
    p.taper(pts, [3.5] * len(pts))


def illusion_mirror_eye(p):
    """Малая печать: зеркальное око в кольце с призмами (над целью «Кошмара», у ладони, метка «Чужого лица»)."""
    p.ring(240, 9)
    p.ring(222, 3)
    for i in range(16):
        a = i * TAU / 16
        x, y = p.P(231, a)
        star4(p, x, y, 10, a, 0.3)
    mirror_eye(p, p.cx, p.cy, 150, 70, 10, ghost=150)


def illusion_veil_ring(p):
    """Кольцо марева «Пелены»: волнистые двойные линии (как дрожащий воздух), редкие бабочки, блики."""
    rng = random.Random(2210)
    for k, (r, amp, kk, w, f) in enumerate(((236, 6, 11, 3.0, 255), (226, 5, 13, 2.0, 190), (214, 7, 9, 1.6, 140),
                                             (200, 4, 17, 1.2, 110))):
        pts = [p.P(r + amp * math.sin(kk * a + k) + amp * 0.4 * math.sin(3.3 * a + 2 * k), a) for a in np.linspace(0, TAU, 720)]
        p.line(pts, w, fill=f, caps=False)
    for i in range(8):
        a = i * TAU / 8 + 0.2
        x, y = p.P(172, a)
        butterfly(p, x, y, 18, a + math.pi / 2 + rng.uniform(-0.4, 0.4), 1.6, fill=50, veins=False)
    for i in range(40):
        a = rng.random() * TAU
        x, y = p.P(150 + rng.random() * 90, a)
        p.dot(x, y, 0.8 + rng.random() * 1.6, fill=200)


# ================================================================== спрайты
def mote_glass(p):
    """Осколок зеркала: неправильный треугольник с бликом и тёмной гранью."""
    pts = [(18, 102), (70, 10), (112, 84), (60, 118)]
    p.poly(pts, 120)
    p.line(pts + [pts[0]], 4)
    p.poly([(70, 10), (112, 84), (78, 66)], 220)                # светлая грань
    p.line([(30, 92), (66, 26)], 3)                              # блик
    p.line([(40, 98), (58, 66)], 2, fill=200)


def mote_butterfly(p):
    """Стеклянная бабочка анфас (крылья раскрыты): прозрачное тело крыла, яркий контур и жилки. Симметрична по u = 0.5 —
    код может делить её по середине и махать половинками."""
    up, lo = butterfly_shape(58)
    for side in (1, -1):
        for wing, f in ((up, 70), (lo, 55)):
            pts = [(64 + side * x, 66 + y) for x, y in wing]
            p.poly(pts, f)
    butterfly(p, 64, 66, 58, 0, 3.2)
    for side in (1, -1):                                        # блик на стекле
        p.line([(64 + side * 18, 40), (64 + side * 40, 24)], 3, fill=230)


def mote_butterfly_side(p):
    """Бабочка со сложенными крыльями (почти ребром) — второй кадр взмаха для спрайтов."""
    up, lo = butterfly_shape(58)
    for side in (1, -1):
        for wing, f in ((up, 110), (lo, 90)):
            pts = [(64 + side * x * 0.24, 66 + y) for x, y in wing]
            p.poly(pts, f)
    butterfly(p, 64, 66, 58, 0, 3.2, veins=False, open_=0.24)
    p.line([(60, 40), (60, 78)], 2.4, fill=230)


# ================================================================== текстуры fx (RGBA)
def _save_rgba(arr, name, sub='fx'):
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA')
    path = os.path.join(A, 'textures', sub, name + '.png')
    im.save(path)
    WRITTEN.append('textures/%s/%s.png' % (sub, name))
    return im


def world_cracks():
    """Трещины мира (1024, белое на прозрачном): точка удара в центре, радиальные трещины, кольца-сколы, мелкая сетка.
    Код кладёт её экранной накладкой и/или на «небо-зеркало» при перевороте (см. письмо)."""
    S = 1024
    p = Pen(S, S)
    rng = random.Random(2211)
    n = 17
    rays = []
    for i in range(n):
        a = i * TAU / n + rng.uniform(-0.12, 0.12)
        pts = jag(rng, (S / 2 + 8 * math.cos(a), S / 2 + 8 * math.sin(a)), (S / 2 + 760 * math.cos(a), S / 2 + 760 * math.sin(a)), 6, 0.06)
        rays.append(pts)
        n_ = len(pts)
        p.taper(pts, [7 * (1 - 0.8 * k / n_) + 0.8 for k in range(n_)])
    for ring_r in (70, 150, 260, 400):                          # сколы-кольца: ломаные между соседними лучами
        for i in range(n):
            if rng.random() < 0.25:
                continue
            a0 = i * TAU / n + rng.uniform(-0.05, 0.05)
            a1 = (i + 1) * TAU / n + rng.uniform(-0.05, 0.05)
            r0, r1 = ring_r * rng.uniform(0.85, 1.15), ring_r * rng.uniform(0.85, 1.15)
            pts = jag(rng, (S / 2 + r0 * math.cos(a0), S / 2 + r0 * math.sin(a0)), (S / 2 + r1 * math.cos(a1), S / 2 + r1 * math.sin(a1)), 3, 0.12)
            p.taper(pts, [2.6] * len(pts))
    for _ in range(90):                                         # мелкие трещинки
        a, r = rng.random() * TAU, 60 + rng.random() * 460
        x, y = S / 2 + r * math.cos(a), S / 2 + r * math.sin(a)
        b = a + rng.uniform(-1.5, 1.5)
        L = rng.uniform(14, 50)
        p.line(jag(rng, (x, y), (x + L * math.cos(b), y + L * math.sin(b)), 2, 0.2), 1.2, fill=170, caps=False)
    alpha = gst.to_alpha(p, glow=0.6, glow_r=4)
    v = np.asarray(alpha, dtype=np.float32)
    rgba = np.dstack([np.full_like(v, 255), np.full_like(v, 255), np.full_like(v, 255), v])
    _save_rgba(rgba, 'illusion_world_cracks')


def haze():
    """Марево: мягкие плывущие полосы и пятна (256, тайлится по обеим осям), белое с низкой непрозрачностью —
    для лент/куполов «Пелены» (дрожащий воздух). Синусы с целыми частотами — шва нет."""
    S = 256
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    u, v = x / S * TAU, y / S * TAU
    rng = np.random.default_rng(2214)
    w = np.zeros((S, S), np.float32)
    for _ in range(6):                                           # искривление (марево «течёт»)
        fx, fy = rng.integers(1, 4), rng.integers(1, 3)
        w += np.sin(fx * u + fy * v + rng.uniform(0, TAU)) * 0.35 / (fx + fy)
    a = np.zeros((S, S), np.float32)
    for k in range(3):                                           # три полосы, слегка волнистые
        a += 0.5 + 0.5 * np.cos(3 * (v + w * 2.2) + k * 2.1 + np.sin(u + k) * 0.6)
    a = (a / 3) ** 3
    blobs = np.zeros((S, S), np.float32)
    for _ in range(5):
        fx, fy = rng.integers(1, 4), rng.integers(1, 4)
        blobs += np.sin(fx * u + rng.uniform(0, TAU)) * np.sin(fy * v + rng.uniform(0, TAU))
    a *= 0.6 + 0.4 * (blobs / np.abs(blobs).max())
    a = a / a.max()
    rgba = np.dstack([np.full_like(a, 255), np.full_like(a, 255), np.full_like(a, 255), np.clip(a * 170, 0, 255)])
    _save_rgba(rgba, 'illusion_haze')


def _hex(h):
    return np.array([int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)], np.float32)


def mirror_wall():
    """Материал зеркальной стены «Лабиринта» (256×256 на 1 блок, тайлится по обеим осям, НЕпрозрачный):
    холодное серебро с перламутровыми разводами (лиловый → розовый → голубой по диагонали), вертикальные отсветы
    «отражения», мягкий градиент; + отдельная текстура трещин (светятся, кладутся аддитивно поверх, 2-м слоем)."""
    S = 256
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    u, v = x / S, y / S
    rng = np.random.default_rng(2212)
    # тайлящийся шум: сумма синусов с целыми частотами
    def tnoise(oct_):
        n = np.zeros((S, S), np.float32)
        for _ in range(oct_):
            fx, fy = rng.integers(1, 6), rng.integers(1, 6)
            ph = rng.uniform(0, TAU)
            n += np.sin(TAU * (fx * u + fy * v) + ph) / (fx + fy)
        return n / max(1e-6, np.abs(n).max())
    base = _hex('#B9B2CC') * 0.92
    n1, n2 = tnoise(7), tnoise(5)
    d = (u + v) % 1.0                                            # диагональ перламутра (тайлится)
    t = (d + 0.12 * n1) % 1.0
    pearl = np.stack([np.interp(t, [0, 0.33, 0.66, 1.0], [c0, c1, c2, c0])
                      for c0, c1, c2 in zip(_hex(LILAC), _hex(PINK), _hex(BLUE))], -1)
    col = base[None, None, :] * (0.9 + 0.1 * n2[..., None]) * 0.76 + pearl * 0.24
    streak = 0.5 + 0.5 * np.cos(TAU * (u - 0.3 + 0.03 * n1))      # широкий мягкий отсвет-«отражение» (один на блок)
    col += (streak ** 6 * 38)[..., None]
    col += (np.exp(-((((u - v * 0.35) % 1.0) - 0.62) / 0.02) ** 2) * 30)[..., None]   # тонкий косой блик
    col *= (0.86 + 0.14 * (1 - v))[..., None]                    # чуть светлее кверху
    # тонкие тёмные трещинки, вшитые в материал (тайлятся — рисуем с переносом)
    p = Pen(S, S)
    r = random.Random(2213)
    for _ in range(5):
        x0, y0 = r.uniform(0, S), r.uniform(0, S)
        a = r.uniform(0, TAU)
        L = r.uniform(60, 140)
        pts = jag(r, (x0, y0), (x0 + L * math.cos(a), y0 + L * math.sin(a)), 4, 0.06)
        for ox in (-S, 0, S):
            for oy in (-S, 0, S):
                p.line([(px + ox, py + oy) for px, py in pts], 1.4, caps=False)
    cr = np.asarray(gst.to_alpha(p, glow=0), np.float32) / 255
    col = col * (1 - 0.45 * cr[..., None]) + 255 * 0.0
    edge = np.roll(cr, 1, axis=1)                                 # светлая кромка трещины
    col += (np.clip(edge - cr, 0, 1) * 120)[..., None]
    rgba = np.dstack([np.clip(col, 0, 255), np.full((S, S), 255, np.float32)])
    _save_rgba(rgba, 'illusion_mirror_wall')
    # слой трещин (светится, аддитивно, на ~1/3 стен — по выбору кода)
    p = Pen(S, S)
    for _ in range(3):
        x0, y0 = r.uniform(40, S - 40), r.uniform(40, S - 40)
        for k in range(r.randint(4, 6)):
            a = r.uniform(0, TAU)
            L = r.uniform(50, 120)
            crack(p, r, (x0, y0), (x0 + L * math.cos(a), y0 + L * math.sin(a)), 1.8, depth=4, amp=0.07, branches=1)
    al = np.asarray(gst.to_alpha(p, glow=0.7, glow_r=3), np.float32)
    rgba = np.dstack([np.full_like(al, 255), np.full_like(al, 240), np.full_like(al, 255), al])
    _save_rgba(rgba, 'illusion_mirror_wall_cracks')


def textures():
    os.makedirs(OUT_SIGIL, exist_ok=True)
    p = Pen(); illusion_seal(p); seal_a = save_sigil(p, 'illusion_seal')
    p = Pen(zoom=gst.CORE_ZOOM); illusion_core(p); core_a = save_sigil(p, 'illusion_core')
    p = Pen(); illusion_crown(p); save_sigil(p, 'illusion_crown')
    p = Pen(1024, 128); illusion_band(p); save_sigil(p, 'school_illusion_band', glow=0.4, glow_r=2)
    # знак для HFx / двойного контура T15 (как sigil_<школа> у школ Iron's): печать + ядро на чёрном
    core_small = core_a.resize((int(512 * 0.4), int(512 * 0.4)), Image.LANCZOS)
    comp = np.asarray(seal_a, dtype=np.float32)
    pad = np.zeros((512, 512), np.float32)
    o = (512 - core_small.width) // 2
    pad[o:o + core_small.height, o:o + core_small.width] = np.asarray(core_small, dtype=np.float32)
    v = np.clip(np.maximum(comp, pad), 0, 255)
    _save_rgba(np.dstack([v, v, v, np.full_like(v, 255)]), 'sigil_illusion')
    for name, fn in (('illusion_maze', illusion_maze), ('illusion_nightmare', illusion_nightmare), ('illusion_dream', illusion_dream),
                     ('illusion_phantom', illusion_phantom), ('illusion_mirror_eye', illusion_mirror_eye),
                     ('illusion_veil_ring', illusion_veil_ring)):
        p = Pen(); fn(p); save_sigil(p, name)
    for name, fn in (('glass', mote_glass), ('butterfly', mote_butterfly), ('butterfly_side', mote_butterfly_side)):
        p = Pen(128, 128); fn(p); save_sigil(p, 'mote_' + name, glow=0.6, glow_r=3)
    world_cracks()
    haze()
    mirror_wall()


def sheet(path):
    """Лист-обзор текстур (для проверки глазами)."""
    names = ['illusion_seal', 'illusion_core', 'illusion_crown', 'illusion_maze', 'illusion_nightmare', 'illusion_dream',
             'illusion_phantom', 'illusion_mirror_eye', 'illusion_veil_ring', 'mote_glass', 'mote_butterfly', 'mote_butterfly_side']
    cell = 300
    cols = 4
    rows = (len(names) + cols - 1) // cols + 2
    out = Image.new('RGB', (cell * cols, cell * rows), (16, 11, 24))
    tint = (201, 168, 255)
    for i, n in enumerate(names):
        a = Image.open(os.path.join(OUT_SIGIL, n + '.png')).split()[3].resize((cell - 16, cell - 16), Image.LANCZOS)
        out.paste(Image.new('RGB', a.size, tint), ((i % cols) * cell + 8, (i // cols) * cell + 8), a)
    y0 = ((len(names) + cols - 1) // cols) * cell
    b = Image.open(os.path.join(OUT_SIGIL, 'school_illusion_band.png')).split()[3].resize((cell * cols - 16, (cell * cols - 16) // 8))
    out.paste(Image.new('RGB', b.size, tint), (8, y0 + 8), b)
    w = Image.open(os.path.join(OUT_FX, 'illusion_mirror_wall.png')).convert('RGB')
    tile = Image.new('RGB', (cell * 2 - 16, cell - 16 - 160))
    for tx in range(0, tile.width, 128):
        for ty in range(0, tile.height, 128):
            tile.paste(w.resize((128, 128)), (tx, ty))
    cr = Image.open(os.path.join(OUT_FX, 'illusion_mirror_wall_cracks.png')).resize((128, 128))
    tile.paste(cr, (128, 0), cr)
    out.paste(tile, (8, y0 + 170))
    wc = Image.open(os.path.join(OUT_FX, 'illusion_world_cracks.png')).split()[3].resize((cell - 16, cell - 16))
    out.paste(Image.new('RGB', wc.size, tint), (cell * 2 + 8, y0 + cell + 8 - 160), wc)
    hz = Image.open(os.path.join(OUT_FX, 'illusion_haze.png')).split()[3].resize((cell - 16, cell - 16))
    out.paste(Image.new('RGB', hz.size, tint), (cell * 3 + 8, y0 + cell + 8 - 160), hz)
    out.save(path)
    print('sheet', path)



# ================================================================== JSON: печати, стиль, эффекты
def write(rel, obj):
    path = os.path.join(A, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    WRITTEN.append(rel)


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


def TX(id, text, radius, size, h, appear, font='latin', color=None, br=None, rot=None, boost=None, repeat=1, side='outer', **kw):
    o = L(id, 'text', None, radius, h, appear, rot=rot, boost=boost, color=color, br=br, **kw)
    o.update({'text': text, 'font': font, 'size': size, 'repeat': repeat, 'side': side})
    return o


def sigil(id, comment, size, color, orientation, layers, hold=-1, expand=None, flash=None, children=None,
          dissolve=('shatter', 'fade'), ddur=16, stagger=2, ground_light=None):
    o = {'comment': comment + ' Сгенерировано tools/gen_illusion_fx.py.', 'size': size, 'color': color, 'orientation': orientation,
         'lifetime': -1, 'hold': hold, 'layers': layers}
    if expand:
        o['expand'] = expand
    if flash:
        o['formedFlash'] = flash
    if children:
        o['onFormed'] = children
    o['dissolve'] = {'modes': list(dissolve), 'duration': ddur, 'stagger': stagger}
    if ground_light:
        o['groundLight'] = ground_light
    write('sigils/%s.json' % id, o)


def glow(color, r=0.95, b=1.0, dur=8, pulse=None):
    return L('glow', 'disc', 'glow', r, -0.01, ap(0, dur, 'grow', 'fade'), color=color, br=b, pulse=pulse)


def ghosts(tex, r=1.0, h=0.004, delay=6, dur=14, rot=(-5, 7), br=0.3):
    """Двоение (фирменный знак школы): та же текстура чуть больше розовым и чуть меньше голубым, вращаются врозь и мерцают —
    края печати «плывут», как радужная кайма у призмы."""
    return [L('ghost_pink', 'disc', tex, r * 1.035, h, ap(delay, dur, 'fade', 'grow', easing='easeOutSine'), rot=rot[0], color=PINK, br=br,
              pulse=(0.55, 23)),
            L('ghost_blue', 'disc', tex, r * 0.968, h + 0.002, ap(delay + 3, dur, 'fade', 'grow', easing='easeOutSine'), rot=rot[1], color=BLUE,
              br=br, pulse=(0.55, 31))]


def school_sigils():
    # Высшая ступень (SchoolSeals: fx/school_illusion_cast): печать собирается из осколков, ядро-око раскрывается из ребра
    sigil('illusion_seal', 'T22, школа «Иллюзии», ступени Высшая/Мифическая/Божественная: печать под магом на время каста (hold −1). '
                           'Зеркальные окна, калейдоскоп, бабочки, трещины; осколки слетаются и встают со вспышкой, края двоятся '
                           '(розовая и голубая тени вращаются врозь), ядро — око над чертой зеркала; распад — разбивается.',
          2.4, LILAC, 'ground', [
              glow(SHADOW, 0.95, 1.1, 8),
              L('seal', 'disc', 'illusion_seal', 1.0, 0.01, ap(2, 28, 'pieces', easing='easeOutBack',
                pieces={'count': 12, 'order': 'scatter', 'pieceTime': 0.4, 'fly': 0.55, 'lift': 0.45, 'orbit': 40, 'tilt': 75, 'spin': 140,
                        'lockFlash': 1.3}), rot=-7),
              *ghosts('illusion_seal', 1.0, 0.014, delay=24, dur=12),
              L('band', 'band', 'school_illusion_band', 1.22, 0.02, ap(14, 16, 'draw', easing='easeInOutSine', startAngle=90, direction=-1),
                inner=0.88, repeat=10, color=PEARL, br=0.85, rot=10, boost=2),
              L('core', 'disc', 'illusion_core', 0.4, 0.03, ap(24, 14, 'unfold', 'fade', easing='easeOutCubic'), rot=12, color=WHITE),
              L('arcs', 'arcs', 'arc_strip', 1.3, 0.04, ap(28, 10, 'assemble', 'fade', easing='easeInOutCubic'), count=3, arcLength=70,
                width=0.03, rot=-18, boost=3, color=BLUE, br=0.8),
          ], flash={'color': WHITE, 'size': 1.35, 'duration': 10, 'sparks': 30}, dissolve=('shatter', 'fade'), ddur=16,
          ground_light={'radius': 0.7, 'strength': 0.45})
    sigil('illusion_crown', 'T22, школа «Иллюзии»: венец над головой мага для ступеней Мифическая и Божественная — зеркальные иглы, '
                            'бабочки, звезда-призма; раскрывается из ребра, двоится.', 0.75, PEARL, 'sky', [
        glow(SHADOW, 0.8, 0.9, 8),
        L('crown', 'disc', 'illusion_crown', 1.0, 0.01, ap(2, 14, 'unfold', 'fade', easing='easeOutCubic'), rot=-14, boost=2),
        *ghosts('illusion_crown', 1.0, 0.012, delay=10, dur=10, rot=(10, -16), br=0.35),
        L('ring', 'disc', 'thin_ring', 1.12, 0.02, ap(8, 10, 'grow', 'fade'), color=PINK, br=0.7),
    ], flash={'color': WHITE, 'size': 1.3, 'duration': 8, 'sparks': 14}, dissolve=('fade', 'collapse'), ddur=12, stagger=0)
    sigil('school_illusion', 'Знак школы «Иллюзии» под магом при каждом касте обычной магии (PohSpell.onCast): короткий, прорисовывается, '
                             'ядро-око раскрывается с доворотом, края двоятся.', 1.9, LILAC, 'ground', [
        glow(SHADOW, 0.8, 1.1, 5),
        L('sign', 'disc', 'illusion_seal', 0.9, 0.01, ap(0, 9, 'draw', startAngle=90, direction=1), rot=30, boost=3),
        L('ghost', 'disc', 'illusion_seal', 0.94, 0.015, ap(4, 8, 'fade', 'grow'), rot=-20, color=PINK, br=0.3, pulse=(0.5, 9)),
        L('core', 'disc', 'illusion_core', 0.36, 0.02, ap(3, 8, 'grow', 'twist', easing='easeOutBack', twist=-180), rot=-50, boost=2, color=WHITE),
        L('band', 'band', 'school_illusion_band', 1.08, 0.03, ap(2, 9, 'draw', easing='easeInOutSine', startAngle=270, direction=-1),
          inner=0.94, repeat=8, color=PEARL, br=0.85, rot=-24, boost=2),
    ], hold=12, flash={'color': PINK, 'size': 1.3, 'duration': 8, 'sparks': 18}, dissolve=('reverse', 'shatter'), ddur=10)


def spell_sigils():
    # --- 4. Фантомная боль: метка над целью
    sigil('illusion_phantom_mark', 'Фантомная боль: метка над головой цели (6 с, billboard): сердце — половина сплошная, половина пунктиром '
                                   '(иллюзорная), трещина посередине; бьётся пульсом, тонкая розовая тень дрожит рядом. Гасит код (Fx.stop).',
          0.32, PINK, 'billboard', [
              glow(SHADOW, 1.3, 0.8, 6, pulse=(0.3, 16)),
              L('heart', 'disc', 'illusion_phantom', 1.0, 0.0, ap(0, 8, 'grow', 'fade', easing='easeOutBack'), pulse=(0.25, 16)),
              L('ghost', 'disc', 'illusion_phantom', 1.08, 0.004, ap(4, 8, 'fade'), color=BLUE, br=0.35, pulse=(0.6, 7), rot=4),
          ], flash={'color': WHITE, 'size': 1.4, 'duration': 6, 'sparks': 8}, dissolve=('shatter', 'fade'), ddur=8)
    sigil('illusion_phantom_hand', 'Фантомная боль: малая метка у ладони заклинателя на взмахе (0.3–0.8 с), смотрит вперёд.', 0.22, PINK, 'facing', [
        glow(LILAC, 1.4, 0.6, 4),
        L('heart', 'disc', 'illusion_phantom', 1.0, 0.0, ap(0, 6, 'unfold', 'fade'), rot=0),
        L('ring', 'disc', 'thin_ring', 1.25, 0.01, ap(2, 6, 'grow', 'fade'), color=WHITE, br=0.8),
    ], hold=6, flash={'color': WHITE, 'size': 1.4, 'duration': 4, 'sparks': 4}, dissolve=('collapse',), ddur=6)
    # --- 3. Пелена: марево на земле
    sigil('illusion_veil_ground', 'Пелена: марево r6 на земле (10 с) — дрожащие кольца, редкие бабочки, слабая калейдоскопическая печать; '
                                  'почти прозрачное (это воздух дрожит, а не круг горит).', 6.0, LILAC, 'ground', [
        glow(SHADOW, 0.9, 0.35, 20),
        L('haze', 'disc', 'illusion_veil_ring', 1.0, 0.0, ap(0, 26, 'grow', 'fade', easing='easeOutSine'), rot=2.5, br=0.55, pulse=(0.2, 50)),
        L('haze2', 'disc', 'illusion_veil_ring', 0.97, 0.005, ap(6, 26, 'grow', 'fade', easing='easeOutSine'), rot=-3.5, color=PINK, br=0.3,
          pulse=(0.4, 37)),
        L('seal', 'disc', 'illusion_seal', 0.42, 0.01, ap(4, 20, 'draw', easing='easeInOutSine', startAngle=90), rot=-4, br=0.35),
    ], dissolve=('fade',), ddur=20)
    # --- 5. Чужое лицо: короткая рябь-знак
    sigil('illusion_face_ripple', 'Чужое лицо: рябь при смене облика / спадании (0.6 с) — зеркальное око вспыхивает перед лицом и '
                                  'расходится кругами, двоится.', 0.42, PEARL, 'facing', [
        L('eye', 'disc', 'illusion_mirror_eye', 1.0, 0.0, ap(0, 4, 'grow', 'fade', easing='easeOutCubic'), br=0.8),
        L('ghost', 'disc', 'illusion_mirror_eye', 1.1, 0.005, ap(1, 4, 'fade'), color=PINK, br=0.4, rot=-30),
        L('ring', 'disc', 'wave_ring', 1.5, 0.01, ap(0, 8, 'grow', 'fade'), color=BLUE, br=0.6),
    ], expand={'scale': 1.6, 'delay': 0, 'duration': 10, 'easing': 'easeOutCubic'}, hold=2, dissolve=('fade',), ddur=6)
    # --- 6. Зеркальный лабиринт
    sigil('illusion_maze_ground', 'Зеркальный лабиринт, каст (4 с): печать-лабиринт под заклинателем — стенки прорисовываются от центра, '
                                  'кольца с проходами крутятся врозь, по ободу двоится.', 3.6, LILAC, 'ground', [
        glow(SHADOW, 0.95, 1.0, 12, pulse=(0.12, 40)),
        L('maze', 'disc', 'illusion_maze', 1.0, 0.0, ap(0, 34, 'draw', easing='easeInOutSine', startAngle=90), rot=-3),
        *ghosts('illusion_maze', 1.0, 0.006, delay=22, dur=14, rot=(4, -6), br=0.28),
        L('eye', 'disc', 'illusion_core', 0.2, 0.012, ap(26, 12, 'unfold', 'fade'), rot=20, color=WHITE),
        TX('words', 'SPECULUM ✦ LABYRINTHUS ✦ ', 1.06, 0.07, 0.016, ap(16, 24, 'draw', easing='linear'), color=PEARL, br=0.8, rot=2, repeat=2),
        L('rim', 'band', 'thin_ring', 1.14, 0.02, ap(24, 12, 'draw', startAngle=90), inner=0.985, repeat=1, color=BLUE, br=0.8),
    ], flash={'color': WHITE, 'size': 1.25, 'duration': 12, 'sparks': 30}, dissolve=('shatter', 'fade'), ddur=16,
          ground_light={'radius': 0.75, 'strength': 0.4})
    sigil('illusion_maze_floor', 'Зеркальный лабиринт, зона (20 с): огромный бледный лабиринт по земле под куполом r14 '
                                 '(виден только врагам — код шлёт им). Почти прозрачный, медленно вращается.', 14.0, LILAC, 'ground', [
        L('maze', 'disc', 'illusion_maze', 1.0, 0.0, ap(0, 30, 'draw', easing='easeInOutSine', startAngle=90), rot=-0.6, br=0.3),
        L('ghost', 'disc', 'illusion_maze', 1.01, 0.006, ap(10, 30, 'fade'), rot=0.8, color=PINK, br=0.14, pulse=(0.5, 60)),
    ], dissolve=('fade',), ddur=20)
    # --- 7. Кошмар наяву
    sigil('illusion_nightmare_ground', 'Кошмар наяву, каст (3.5 с): тёмная печать под заклинателем — венок пустых очей, когти, '
                                       'безликий овал; очи открываются по одному (draw), тьма пульсирует.', 3.0, LILAC, 'ground', [
        glow(SHADOW, 0.9, 0.9, 10, pulse=(0.25, 18)),
        L('seal', 'disc', 'illusion_nightmare', 1.0, 0.0, ap(2, 30, 'draw', easing='easeInOutSine', startAngle=270, direction=-1), rot=4),
        *ghosts('illusion_nightmare', 1.0, 0.006, delay=20, dur=12, rot=(-6, 5), br=0.25),
        L('ring', 'band', 'thin_ring', 1.1, 0.015, ap(18, 12, 'draw', startAngle=90), inner=0.985, repeat=1, color=PINK, br=0.7),
    ], flash={'color': '#B08CFF', 'size': 1.2, 'duration': 10, 'sparks': 20}, dissolve=('reverse', 'collapse'), ddur=14)
    sigil('illusion_nightmare_over', 'Кошмар наяву: печать над головой цели (весь каст и 12 с действия), лицом вниз — пустые очи '
                                     'кружат, дрожит; её видят все рядом (знак, что цель в кошмаре).', 0.62, LILAC, 'sky', [
        L('seal', 'disc', 'illusion_nightmare', 1.0, 0.0, ap(0, 18, 'unfold', 'fade', easing='easeOutCubic'), rot=-12, boost=3, pulse=(0.2, 12)),
        L('ghost', 'disc', 'illusion_nightmare', 1.06, 0.006, ap(8, 10, 'fade'), rot=9, color=PINK, br=0.3, pulse=(0.6, 9)),
    ], flash={'color': '#B08CFF', 'size': 1.3, 'duration': 8, 'sparks': 12}, dissolve=('collapse', 'fade'), ddur=10)
    # --- 8. Сон бабочки
    sigil('illusion_dream_ground', 'Сон бабочки, каст 12 с: мифическая печать под заклинателем — большая бабочка с ячейками-лунами, '
                                   'кольцо фаз луны, циферблат сна, надпись; прорисовывается 2 с, к 4 с полностью; трещины «как стекло».',
          4.6, LILAC, 'ground', [
              glow(SHADOW, 0.95, 1.0, 20, pulse=(0.12, 60)),
              L('rays', 'spokes', 'rays', 1.4, -0.005, ap(0, 40, 'fade', 'grow'), rot=1, color=PEARL, br=0.3),
              L('dream', 'disc', 'illusion_dream', 1.0, 0.0, ap(0, 38, 'draw', easing='easeInOutSine', startAngle=90), rot=2),
              *ghosts('illusion_dream', 1.0, 0.006, delay=30, dur=20, rot=(-3, 4), br=0.3),
              L('seal', 'band', 'school_illusion_band', 1.18, 0.012, ap(18, 24, 'draw', easing='easeInOutSine', startAngle=270, direction=-1),
                inner=0.9, repeat=12, color=PEARL, br=0.9, rot=-4),
              TX('words', 'SOMNIUM PAPILIONIS ✦ QUIS SOMNIAT ✦ ', 1.27, 0.06, 0.02, ap(30, 30, 'draw', easing='linear'), color=PINK, br=0.85,
                 rot=1.5, repeat=2),
              L('rim', 'band', 'thin_ring', 1.34, 0.025, ap(40, 16, 'draw', startAngle=90), inner=0.985, repeat=1, color=BLUE, br=0.9),
              L('stars', 'disc', 'orbit_stars', 1.5, 0.03, ap(50, 20, 'grow', 'fade'), rot=-2, color=PEARL, br=0.5),
          ], flash={'color': WHITE, 'size': 1.25, 'duration': 14, 'sparks': 40}, dissolve=('shatter', 'fade'), ddur=20,
          ground_light={'radius': 0.8, 'strength': 0.5})
    sigil('illusion_dream_sky', 'Сон бабочки: печать-«небо» высоко над заклинателем (с 2 с), лицом вниз; на перевороте мира (8–10 с) '
                                'оказывается под ногами — код. Двоится, медленно вращается.', 9.0, LILAC, 'sky', [
        L('dream', 'disc', 'illusion_dream', 1.0, 0.0, ap(0, 50, 'draw', easing='easeInOutSine', startAngle=90), rot=-1.5, br=0.6),
        *ghosts('illusion_dream', 1.0, 0.006, delay=30, dur=30, rot=(2, -2.5), br=0.22),
        L('cracks', 'disc', 'illusion_world_cracks', 1.3, 0.01, ap(70, 40, 'grow', 'fade', easing='easeOutCubic'), rot=0, color=PEARL, br=0.6),
    ], dissolve=('shatter', 'fade'), ddur=20)
    sigil('illusion_mirror_crack', 'Трещина в воздухе (Сон бабочки, 4–8 с; Лабиринт — вход в стену): точка касания, от неё бегут трещины '
                                   'по невидимому зеркалу (facing, лицом к заклинателю/по взгляду).', 1.0, PEARL, 'facing', [
        L('glow', 'disc', 'glow', 0.4, -0.01, ap(0, 6, 'grow', 'fade'), color=WHITE, br=0.9, pulse=(0.2, 10)),
        L('cracks', 'disc', 'illusion_world_cracks', 1.0, 0.0, ap(0, 26, 'grow', 'fade', easing='easeOutCubic'), br=1.0),
        L('ghost', 'disc', 'illusion_world_cracks', 1.03, 0.004, ap(6, 20, 'grow', 'fade', easing='easeOutCubic'), color=PINK, br=0.4, rot=0.6),
    ], expand={'scale': 1.15, 'delay': 0, 'duration': 30, 'easing': 'easeOutSine'}, dissolve=('shatter', 'fade'), ddur=12)
    sigil('illusion_hand_eye', 'Малое зеркальное око у ладони (касты «Отражений», «Кошмара»), смотрит вперёд.', 0.24, PEARL, 'facing', [
        glow(LILAC, 1.4, 0.6, 4, pulse=(0.25, 12)),
        L('eye', 'disc', 'illusion_mirror_eye', 1.0, 0.0, ap(0, 8, 'unfold', 'fade'), rot=0),
        L('ghost', 'disc', 'illusion_mirror_eye', 1.07, 0.004, ap(3, 8, 'fade'), color=PINK, br=0.35, rot=-14),
    ], flash={'color': WHITE, 'size': 1.4, 'duration': 4, 'sparks': 4}, dissolve=('collapse', 'fade'), ddur=6)



def fx(id, comment, style, duration, elements):
    write('fx/%s.json' % id, {'comment': comment + ' Сгенерировано tools/gen_illusion_fx.py.', 'style': style, 'duration': duration,
                              'elements': elements})


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
    write('fx/styles/illusion.json', {
        'comment': 'Стиль школы «Иллюзии» (T22): перламутрово-лиловый, розовые и голубые блики, тень #3A2A5A; осколки зеркала, '
                   'стеклянные бабочки; движение плавное, с лёгким дрожанием (марево). Сгенерировано tools/gen_illusion_fx.py.',
        'palette': {'primary': LILAC, 'secondary': PINK, 'core': WHITE, 'shadow': SHADOW},
        'textures': {'sparks': 'spark_soft', 'runes': 'school_illusion_band', 'shards': 'mote_glass', 'sigil': 'illusion_seal'},
        'blend': 'additive',
        'motion': {'rotationScale': 0.8, 'jitter': 0.12, 'easing': 'easeOutSine', 'pulse': {'amp': 0.1, 'period': 23}}})


def glints(delay=4, at='caster+0,0.1,0', **kw):
    """Мерцающие блики-осколки и бабочки вокруг мага на время каста (до остановки эффекта)."""
    base = dict(follow=True, count=4000)
    return [E('sprites', delay, at, texture='mote_glass', rate=0.9, area=2.0, speed=0.008, gravity=-0.0016, spin=90, tumble=0.8,
              size=[0.2, 0.06], life=34, color='@primary', glow=0.4, **base, **kw),
            E('sprites', delay + 6, at, texture='mote_butterfly', rate=0.22, area=1.8, speed=0.012, gravity=-0.003, sway=1.4, tumble=0.25,
              size=[0.26, 0.14], life=50, color='@secondary', glow=0.5, **base, **kw),
            E('sprites', delay, 'caster+0,1.0,0', texture='spark_soft', rate=1.2, spread=1.1, speed=0.004, gravity=-0.001,
              size=[0.08, 0.0], life=24, color=BLUE, **base, **kw)]


def school_fx():
    fx('school_illusion', 'Каст обычной магии школы «Иллюзии» (PohSpell.onCast): знак под магом, рябь-сфера (воздух дрогнул), '
                          'осколки-блики и пара бабочек.', 'illusion', 36, [
        E('sigil', 0, 'caster+0,0.04,0', id='school_illusion', follow=True),
        E('wave', 0, 'caster+0,1,0', duration=12, shape='sphere', radius=1.6, rim=0.8, color='@primary', brightness=0.6),
        E('wave', 0, 'caster', duration=14, shape='ring', radius=3.0, color='@secondary'),
        E('flash', 0, 'caster+0,0.3,0', duration=8, size=1.6, color=PEARL, brightness=0.7),
        E('sprites', 2, 'caster+0,0.2,0', duration=26, follow=True, texture='mote_glass', count=14, rate=1.0, area=1.6, speed=0.02,
          gravity=-0.003, spin=100, tumble=0.8, size=[0.22, 0.08], life=22, color='@primary'),
        E('sprites', 4, 'caster+0,0.6,0', duration=10, follow=True, texture='mote_butterfly', count=3, rate=0.4, area=1.0, speed=0.02,
          gravity=-0.006, sway=1.2, size=[0.24, 0.16], life=26, color='@secondary', glow=0.4),
    ])
    seal = [E('sigil', 0, 'caster+0,0.04,0', id='illusion_seal', follow=True),
            E('flash', 0, 'caster+0,0.4,0', duration=10, size=2.2, color=PEARL, brightness=0.7),
            E('wave', 0, 'caster', duration=16, shape='ring', radius=4.0, color='@primary'),
            E('wave', 2, 'caster+0,1,0', duration=14, shape='sphere', radius=2.2, rim=0.9, color='@secondary', brightness=0.5)]
    fx('school_illusion_cast', 'T22, школа «Иллюзии», ступень Высшая (SchoolSeals): печать под магом + блики-осколки, бабочки. '
                               'duration −1: код останавливает эффект в конце каста.', 'illusion', -1, seal + glints())
    crown = [E('sigil', 10, 'caster+0,2.55,0', id='illusion_crown', follow=True),
             E('flash', 10, 'caster+0,2.55,0', duration=10, size=1.4, color='@core', brightness=0.6, rays=6)]
    fx('school_illusion_cast_crown', 'T22, школа «Иллюзии», ступень Мифическая: печать + венец над головой + блики и бабочки. duration −1.',
       'illusion', -1, seal[:1] + crown + seal[1:] + glints())
    halos = []
    n = 7
    for k in range(n):
        a = math.radians(-72 + 144 * k / (n - 1))
        x, z = 1.9 * math.sin(a), -(1.9 * math.cos(a) * 0.6 + 0.55)
        y = 1.55 + 0.35 * math.cos(a)
        halos.append(E('sigil', 23 - abs(k - n // 2) * 3, 'caster+%.2f,%.2f,%.2f' % (x, y, z), id='golden_halo', follow=True,
                       orientation='facing', sigilScale=1.15 if k == n // 2 else 0.95))
    fx('school_illusion_cast_divine', 'T22, школа «Иллюзии», ступень Божественная: печать + венец + дуга из 7 золотых кругов за спиной '
                                      '(с краёв к центру), золотые блёстки — как у остальных школ. duration −1.',
       'illusion', -1, seal[:1] + crown + seal[1:] + glints() + halos + [
           E('sprites', 16, 'caster+0,1.6,-0.9', duration=9999, follow=True, texture='@sparks', count=4000, rate=1.5, spread=1.8,
             speed=0.01, gravity=-0.002, size=[0.1, 0.02], life=40, color='#FFD36B'),
           E('flash', 22, 'caster+0,1.7,-1.0', duration=12, follow=True, size=2.4, rays=8, color='#FFE9A8', brightness=0.6)])


POOF = '#ECE8F2'          # облачко исчезновения: нейтральное, без цвета школы


def spell_fx():
    # ---------------------------------------------------------------- общее: облачко исчезновения
    fx('illusion_poof', 'Облачко исчезновения (копия «умирает», копия «Ложного шага» пропадает): ТО ЖЕ, что у игрока при рывке — '
                        'серо-белый пух, без искр и цвета школы (правило 3: никаких частиц «разоблачения»). caster = место копии. '
                        'Если код рисует рывок ванильными частицами POOF, пусть и копии гасит ими же — главное, одинаково.',
       'illusion', 20, [
           E('sprites', 0, 'caster+0,0.9,0', duration=2, texture='glow', count=16, rate=8, spread=0.45, speed=0.035, gravity=-0.0015,
             size=[0.55, 0.95], life=16, color=POOF, brightness=0.55, blend='translucent'),
           E('sprites', 0, 'caster+0,0.25,0', duration=2, texture='glow', count=8, rate=4, area=0.5, speed=0.02, gravity=-0.001,
             size=[0.45, 0.8], life=14, color=POOF, brightness=0.45, blend='translucent'),
       ])

    # ---------------------------------------------------------------- 1. Отражения
    fx('illusion_mirror_images_cast', 'Отражения, каст 0.8 с (caster): ладонь проводит перед собой — у неё малое зеркальное око; на 12 тике '
                                      'вокруг мага «трескается воздух»: сфера-рябь, кольцо осколков разлетается в стороны, куда побегут копии. '
                                      'Сами копии появляются каждая со своим illusion_mirror_image_spawn (у настоящего мага — тот же эффект: '
                                      'чтобы враг не отличил).', 'illusion', 30, [
        E('sigil', 0, 'caster.hand', follow=True, id='illusion_hand_eye', until=14),
        E('trail', 2, 'caster.hand', duration=10, follow=True, width=0.06, length=8, fade=1.5, head=1.5, color='@secondary'),
        E('wave', 12, 'caster+0,1,0', duration=12, shape='sphere', radius=2.4, rim=1.2, color='@primary', brightness=0.7),
        E('flash', 12, 'caster+0,1.1,0', duration=8, size=1.6, rays=6, color=PEARL),
        E('sprites', 12, 'caster+0,1.0,0', duration=2, texture='mote_glass', count=26, rate=13, spread=0.4, speed=0.16, gravity=0.004,
          spin=200, tumble=1, size=[0.24, 0.06], life=18, color='@primary', glow=0.4),
        E('sprites', 12, 'caster+0,1.0,0', duration=2, texture='spark_soft', count=30, rate=15, spread=0.5, speed=0.1, gravity=0,
          size=[0.14, 0.0], life=14, color=BLUE),
    ])
    fx('illusion_mirror_image_spawn', 'Отражения: появление фигуры (caster = фигура: каждая копия И настоящий маг — одинаково). '
                                      'Короткая дрожь воздуха по росту, 3 блика; 10 тиков.', 'illusion', 12, [
        E('aura', 0, 'caster', target='caster', duration=10, thickness=0.05, pulse=[0.4, 4], motes=0, color=PEARL, brightness=0.5,
          **{'in': ease(2), 'out': ease(8)}),
        E('sprites', 0, 'caster+0,1.0,0', duration=2, texture='mote_glass', count=4, rate=2, spread=0.4, speed=0.03, gravity=0.003,
          spin=120, size=[0.16, 0.04], life=10, color='@primary'),
    ])
    # ---------------------------------------------------------------- 2. Ложный шаг
    fx('illusion_false_step', 'Ложный шаг (видят ТОЛЬКО сам маг и союзники — код шлёт им; врагам нечего видеть: для них маг пропал, '
                              'а копия бежит дальше). caster = маг, follow: призрачный след рывка 8 бл., бледное двоение, рябь в точке '
                              'прибытия на 8 тике. Копию гасит illusion_poof.', 'illusion', 24, [
        E('aura', 0, 'caster', target='caster', duration=12, thickness=0.06, pulse=[0.5, 3], motes=6, texture='mote_glass', color='@primary',
          brightness=0.6, **{'in': ease(1), 'out': ease(10)}),
        E('trail', 0, 'caster+0,1.0,0', duration=10, follow=True, width=0.5, length=7, fade=1.2, head=0, color='@primary', brightness=0.35),
        E('trail', 0, 'caster+0,0.3,0', duration=10, follow=True, width=0.3, length=6, fade=1.4, head=0, color='@secondary', brightness=0.3),
        E('wave', 8, 'caster+0,1,0', duration=10, shape='sphere', radius=1.2, rim=1.0, color=PEARL, brightness=0.5),
        E('sprites', 8, 'caster+0,0.8,0', duration=2, texture='mote_glass', count=8, rate=4, spread=0.4, speed=0.05, gravity=0.004,
          spin=160, size=[0.18, 0.05], life=12, color='@primary'),
    ])
    # ---------------------------------------------------------------- 3. Пелена
    fx('illusion_veil', 'Пелена: марево r6 на 10 с (200 тиков) вокруг точки каста (caster; follow нет — марево стоит на месте; '
                        'если нужно, чтобы шло за магом, — код ставит follow). Дрожащий воздух: бледная печать-марево на земле, '
                        'стенка марева по краю r6 (вертикальные полупрозрачные ленты illusion_haze, мерцают), пузырь со слабым ободом, '
                        'плывущие блики и пара бабочек, лёгкая лиловая дымка у игроков внутри (tint). Подмену силуэтов рисует код.',
       'illusion', 200, [
           E('sigil', 0, 'caster+0,0.05,0', id='illusion_veil_ground', until=196),
           E('wave', 0, 'caster', duration=18, shape='ring', radius=6, color='@primary', brightness=0.7),
           E('wave', 0, 'caster+0,0.2,0', duration=24, shape='sphere', radius=6, rim=0.5, color=PEARL, brightness=0.25),
           E('curtain', 4, 'caster', duration=192, radius=[5.7, 6.1], count=46, height=3.6, grow=24, width=[0.35, 0.7], brightness=[0.06, 0.16],
             flicker=0.6, texture='illusion_haze', color='@primary', **{'in': ease(20, 'easeOutSine'), 'out': ease(16)}),
           E('curtain', 10, 'caster', duration=186, radius=[2.0, 5.6], count=22, height=2.6, grow=30, width=[0.3, 0.5], brightness=[0.04, 0.1],
             flicker=0.8, texture='illusion_haze', color=PINK, **{'in': ease(24, 'easeOutSine'), 'out': ease(16)}),
           E('sprites', 6, 'caster+0,0.6,0', duration=186, texture='glow', count=400, rate=1.6, area=5.6, speed=0.004, gravity=-0.0008,
             size=[0.6, 1.2], life=60, color=LILAC, brightness=0.12, comment='волны дрожащего воздуха'),
           E('sprites', 6, 'caster+0,0.3,0', duration=186, texture='mote_glass', count=400, rate=0.7, area=5.6, speed=0.004, gravity=-0.001,
             spin=60, tumble=0.8, size=[0.18, 0.04], life=40, color=PEARL, glow=0.4),
           E('sprites', 20, 'caster+0,1.2,0', duration=160, texture='mote_butterfly', count=40, rate=0.12, area=5.0, speed=0.008, gravity=-0.0012,
             sway=1.6, tumble=0.3, size=[0.26, 0.18], life=70, color='@secondary', glow=0.4),
           E('tint', 0, 'caster', duration=200, radius=6, color='#B8A0E8', strength=0.12, **{'in': ease(20), 'out': ease(20)}),
       ])
    fx('illusion_veil_flicker', 'Пелена: настоящая модель «пропала» на миг / фальшивый силуэт мигнул (видит только враг в мареве — код). '
                                'Едва заметная рябь по росту, 6 тиков; caster = фигура.', 'illusion', 8, [
        E('aura', 0, 'caster', target='caster', duration=6, thickness=0.04, pulse=[0.6, 3], motes=0, color=PEARL, brightness=0.35,
          **{'in': ease(1), 'out': ease(5)}),
    ])
    # ---------------------------------------------------------------- 4. Фантомная боль
    fx('illusion_phantom_pain_cast', 'Фантомная боль, каст 0.8 с (caster; связи с целью нет — метку цели даёт illusion_phantom_pain_mark): '
                                     'указ ладонью, у ладони вспыхивает малое сердце-метка и гаснет.', 'illusion', 18, [
        E('sigil', 4, 'caster.hand', follow=True, id='illusion_phantom_hand', until=16),
        E('flash', 8, 'caster.hand', follow=True, duration=6, size=0.7, rays=4, color='@secondary'),
        E('sprites', 8, 'caster.hand', duration=2, follow=True, texture='spark_soft', count=8, rate=4, spread=0.1, speed=0.05,
          gravity=0.001, size=[0.1, 0.0], life=10, color='@secondary'),
    ])
    fx('illusion_phantom_pain_mark', 'Фантомная боль: метка на цели (target) на 6 с (120 тиков; код гасит раньше, если надо): сердце '
                                     'над головой бьётся, розовые искры падают, слабая дрожащая оболочка. Видят все рядом.', 'illusion', 120, [
        E('sigil', 0, 'target+0,2.35,0', follow=True, id='illusion_phantom_mark', until=116),
        E('flash', 0, 'target+0,2.35,0', follow=True, duration=8, size=0.8, rays=4, color='@secondary'),
        E('aura', 0, 'target', target='target', duration=118, thickness=0.05, pulse=[0.25, 16], motes=6, texture='spark_soft', color=PINK,
          brightness=0.5, **{'in': ease(6), 'out': ease(10)}),
        E('sprites', 4, 'target+0,2.2,0', follow=True, duration=112, texture='spark_soft', count=200, rate=0.5, spread=0.15, speed=0.005,
          gravity=0.003, size=[0.08, 0.02], life=18, color=PINK),
    ])
    fx('illusion_phantom_pain_tick', 'Фантомная боль: удар по меченой цели — иллюзорная половина урона: розовая трещинка-вспышка у груди '
                                     'и мерцание метки (6 тиков); target = цель.', 'illusion', 8, [
        E('flash', 0, 'target+0,1.2,0', follow=True, duration=5, size=0.6, rays=3, color=PINK, brightness=0.8),
        E('sprites', 0, 'target+0,1.2,0', duration=1, texture='mote_glass', count=4, rate=4, spread=0.2, speed=0.05, gravity=0.004,
          spin=200, size=[0.14, 0.04], life=10, color=PINK),
    ])
    fx('illusion_return', 'Возврат иллюзорного урона (общий для школы: метка «Фантомной боли» пережита, «Лабиринт», «Сон бабочки» — где '
                          'урон возвращается): 1 с (20 тиков), target = цель. Перламутровые искры сходятся к груди со всех сторон, '
                          'мягко светится оболочка, в конце тихая вспышка. Здоровье код поднимает плавно за эти же 20 тиков.',
       'illusion', 24, [
           E('vortex', 0, 'target+0,1.1,0', duration=20, radius=1.3, height=0, arms=3, speed=6, pull=1, texture='spark_soft', particles=40,
             life=16, size=0.12, color=PEARL),
           E('sprites', 0, 'target+0,1.1,0', duration=16, follow=True, texture='spark_soft', count=60, rate=3.5, spread=1.0, speed=-0.05,
             gravity=0, size=[0.14, 0.03], life=14, color=PINK, glow=0.5, comment='speed < 0: летят к центру'),
           E('sprites', 2, 'target+0,1.1,0', duration=14, follow=True, texture='spark_soft', count=40, rate=3, spread=1.0, speed=-0.05,
             gravity=0, size=[0.12, 0.02], life=14, color=BLUE, glow=0.5),
           E('aura', 0, 'target', target='target', duration=22, thickness=0.08, pulse=[0.15, 8], motes=10, texture='spark_soft', color=PEARL,
             **{'in': ease(6), 'out': ease(10)}),
           E('flash', 18, 'target+0,1.1,0', follow=True, duration=8, size=1.0, rays=4, color=WHITE, brightness=0.7),
       ])
    # ---------------------------------------------------------------- 5. Чужое лицо
    fx('illusion_borrowed_face', 'Чужое лицо: смена облика (caster; 12 тиков, видят все): жест ладонью по лицу (анимация), на 8 тике '
                                 'рябь по всему телу и малое зеркальное око перед лицом расходится кругом. Ровно в этот тик код меняет скин/ник.',
       'illusion', 20, [
           E('sigil', 6, 'caster.eyes+0,0,0.35', follow=True, id='illusion_face_ripple', until=16),
           E('aura', 8, 'caster', target='caster', duration=10, thickness=0.07, pulse=[0.6, 3], motes=4, texture='mote_glass', color=PEARL,
             brightness=0.7, **{'in': ease(1), 'out': ease(9)}),
           E('wave', 8, 'caster+0,1,0', duration=10, shape='sphere', radius=1.3, rim=1.0, color='@primary', brightness=0.5),
       ])
    fx('illusion_borrowed_face_end', 'Чужое лицо спадает (атака/каст/30 с; caster): та же рябь, без ока, короче — облик «стекает».',
       'illusion', 12, [
           E('aura', 0, 'caster', target='caster', duration=10, thickness=0.07, pulse=[0.6, 3], motes=6, texture='mote_glass', color=PEARL,
             brightness=0.6, **{'in': ease(1), 'out': ease(9)}),
           E('sprites', 0, 'caster+0,1.6,0', duration=4, follow=True, texture='mote_glass', count=8, rate=2, spread=0.25, speed=0.01,
             gravity=0.006, spin=90, size=[0.16, 0.05], life=14, color='@primary', comment='осколки «маски» осыпаются'),
       ])
    # ---------------------------------------------------------------- 6. Зеркальный лабиринт (Высшее)
    fx('illusion_labyrinth_cast', 'Зеркальный лабиринт, каст 4 с (80 тиков; caster): ладони чертят квадрат, по кругу из земли растут '
                                  'тонкие зеркальные «пластины» (лучи-завеса), осколки кружат; на 76 тике ладони вниз — удар, вспышка, '
                                  'волна до r14 (дальше зону держит illusion_labyrinth). Печать под ногами — отдельно illusion_labyrinth_seal.',
       'illusion', 90, [
           E('sigil', 6, 'caster.hand', follow=True, id='illusion_hand_eye', until=74),
           E('trail', 8, 'caster.hand', duration=40, follow=True, width=0.05, length=14, fade=1.2, head=1.4, color='@secondary',
             comment='ладонь чертит квадрат (анимация 0.4–2.4 с)'),
           E('curtain', 14, 'caster', duration=66, radius=[2.4, 3.4], count=18, height=[1.4, 2.8], grow=30, width=[0.08, 0.16],
             brightness=[0.25, 0.5], flicker=0.25, texture='beam_fade', color=PEARL, **{'out': ease(10)}, comment='пластины-зеркала растут'),
           E('vortex', 10, 'caster+0,0.15,0', duration=66, radius=3.2, height=0, arms=4, speed=3, pull=0.4, texture='mote_glass', particles=50,
             life=30, size=0.18, color='@primary'),
           E('sprites', 30, 'caster+0,0.3,0', duration=46, follow=True, texture='mote_butterfly', count=20, rate=0.45, area=2.6, speed=0.01,
             gravity=-0.004, sway=1.4, size=[0.26, 0.18], life=40, color='@secondary', glow=0.4),
           E('flash', 76, 'caster+0,0.4,0', duration=10, size=3.2, rays=8, anamorphic=5, color=WHITE),
           E('wave', 76, 'caster', duration=20, shape='ring', radius=14, color='@primary'),
           E('wave', 76, 'caster+0,0.5,0', duration=24, shape='sphere', radius=14, rim=1.2, color=PEARL, brightness=0.5),
           E('sprites', 76, 'caster+0,0.3,0', duration=3, texture='mote_glass', count=40, rate=14, area=1.5, speed=0.2, gravity=0.006,
             spin=200, tumble=1, size=[0.26, 0.06], life=22, color='@primary', glow=0.3),
       ])
    fx('illusion_labyrinth_seal', 'Зеркальный лабиринт: печать-лабиринт под заклинателем на время каста (код запускает, если '
                                  'SchoolSeals.shown(caster) == false — иначе под ногами уже печать ступени). duration −1, гасит код.',
       'illusion', -1, [E('sigil', 0, 'caster+0,0.04,0', id='illusion_maze_ground', follow=True),
                        E('wave', 0, 'caster', duration=16, shape='ring', radius=4.0, color='@primary')])
    fx('illusion_labyrinth', 'Зеркальный лабиринт, зона r14 на 20 с (400 тиков; caster = центр, без follow). Купол из перламутровых рёбер '
                             '(mesh illusion_dome × 14), бледный лабиринт по земле, блики. Купол и пол видят ВСЕ (знак зоны), стены — '
                             'только враги (их строит код: материал textures/fx/illusion_mirror_wall + _cracks, модуль '
                             'fx/meshes/illusion_mirror_wall). Внутри у врагов — лиловая дымка (tint, код шлёт только им или всем).',
       'illusion', 400, [
           E('mesh', 0, 'caster', model='illusion_dome', scale=14, until=392),
           E('sigil', 0, 'caster+0,0.06,0', id='illusion_maze_floor', until=390),
           E('sprites', 10, 'caster+0,0.4,0', duration=380, texture='mote_glass', count=2000, rate=2.2, area=13, speed=0.004, gravity=-0.0012,
             spin=60, tumble=0.8, size=[0.24, 0.05], life=50, color=PEARL, glow=0.3),
           E('sprites', 20, 'caster+0,1.5,0', duration=360, texture='mote_butterfly', count=200, rate=0.35, area=12, speed=0.01,
             gravity=-0.001, sway=1.6, tumble=0.3, size=[0.3, 0.2], life=80, color='@secondary', glow=0.4),
           E('tint', 0, 'caster', duration=400, radius=14, color='#C8B4F0', strength=0.1, **{'in': ease(20), 'out': ease(20)}),
       ])
    fx('illusion_labyrinth_wall_hit', 'Зеркальный лабиринт: враг вошёл в зеркальную стену (point:hit — точка входа на стене, caster = '
                                      'жертва; видит только жертва): звон, осколки летят из стены навстречу, трещина-вспышка на стекле, '
                                      'короткая белая засветка экрана. Иллюзорный урон и отталкивание — код.', 'illusion', 24, [
        E('sigil', 0, 'point:hit', id='illusion_mirror_crack', scale=0.7, until=14),
        E('flash', 0, 'point:hit', duration=6, size=1.4, rays=8, screen=0.2, color=WHITE),
        E('sprites', 0, 'point:hit', duration=2, texture='mote_glass', count=30, rate=15, spread=0.3, speed=0.2, gravity=0.012, spin=260,
          tumble=1, size=[0.28, 0.08], life=20, color=PEARL, glow=0.3, cone=120),
        E('sprites', 0, 'point:hit', duration=2, texture='spark_sharp', count=14, rate=7, spread=0.2, speed=0.18, gravity=0.006,
          size=[0.16, 0.02], life=12, color=PINK, cone=140),
    ])
    # ---------------------------------------------------------------- 7. Кошмар наяву (Высшее)
    fx('illusion_nightmare_cast', 'Кошмар наяву, каст 3.5 с (70 тиков): левая ладонь закрывает глаза, правая — когтем к цели; над целью '
                                  '(target) собирается печать пустых очей, из-под её ног ползёт тьма; у мага — малое око в ладони, тёмные '
                                  'клочья у ног. Никакой линии к цели. На 66 тике печать над целью вспыхивает и сжимается в голову.',
       'illusion', 74, [
           E('sigil', 6, 'caster.hand', follow=True, id='illusion_hand_eye', until=66),
           E('sprites', 0, 'caster+0,0.1,0', duration=68, follow=True, texture='glow', count=200, rate=2.2, area=1.6, speed=0.006,
             gravity=-0.002, size=[0.5, 1.0], life=26, color=DEEP, brightness=0.7, blend='translucent', comment='тьма у ног мага'),
           E('sigil', 10, 'target+0,2.6,0', follow=True, id='illusion_nightmare_over', until=68),
           E('sprites', 10, 'target+0,0.1,0', duration=58, follow=True, texture='glow', count=200, rate=2.6, area=1.2, speed=0.008,
             gravity=-0.006, size=[0.5, 1.1], life=26, color=DEEP, brightness=0.8, blend='translucent', comment='тьма поднимается по цели'),
           E('aura', 20, 'target', target='target', duration=50, thickness=0.09, pulse=[0.3, 10], motes=10, texture='mote_eye', color='#6A4A9A',
             brightness=0.6, **{'in': ease(16), 'out': ease(6)}),
           E('tint', 30, 'target', duration=44, radius=3, color='#140A20', strength=0.3, **{'in': ease(30), 'out': ease(6)}),
           E('flash', 66, 'target+0,1.7,0', follow=True, duration=8, size=1.2, rays=6, color='#B08CFF'),
           E('wave', 66, 'target+0,1.6,0', duration=10, shape='sphere', radius=1.0, rim=1.4, color='@primary', brightness=0.6),
       ])
    fx('illusion_nightmare_seal', 'Кошмар наяву: тёмная печать под заклинателем на время каста (если SchoolSeals.shown(caster) == false). '
                                  'duration −1.', 'illusion', -1, [E('sigil', 0, 'caster+0,0.04,0', id='illusion_nightmare_ground', follow=True)])
    fx('illusion_nightmare_mark', 'Кошмар наяву: цель в кошмаре 12 с (240 тиков; target = жертва; видят все рядом — знак, что '
                                  'ей мерещится): тихая тёмная дымка у головы, редкие пустые очи-искры, печать над головой медленно гаснет '
                                  'за первые 2 с. Чудовищ вместо существ рисует клиент жертвы (mesh fx/meshes/illusion_nightmare).',
       'illusion', 240, [
           E('sigil', 0, 'target+0,2.6,0', follow=True, id='illusion_nightmare_over', until=40),
           E('sprites', 0, 'target+0,1.7,0', follow=True, duration=236, texture='glow', count=2000, rate=0.8, spread=0.35, speed=0.004,
             gravity=-0.002, size=[0.35, 0.6], life=24, color=DEEP, brightness=0.6, blend='translucent'),
           E('sprites', 0, 'target+0,1.7,0', follow=True, duration=236, texture='mote_eye', count=2000, rate=0.1, spread=0.6, speed=0.002,
             gravity=-0.001, size=[0.12, 0.08], life=30, color='#B08CFF', glow=0.4),
       ])
    fx('illusion_nightmare_monster', 'Кошмар наяву: безликое чудовище (для превью и как запасной вариант): mesh illusion_nightmare на месте '
                                     'существа, follow. Клиент жертвы рисует ТО ЖЕ чудовище вместо каждого игрока/моба (см. письмо), рост '
                                     'модели — 1.95 (масштаб под рост сущности: scale = рост / 1.95).', 'illusion', 60, [
        E('mesh', 0, 'caster', follow=True, model='illusion_nightmare', until=56),
    ])
    # ---------------------------------------------------------------- 8. Сон бабочки (Мифическое): каст, мир сна, пробуждение —
    # tools/gen_celestial_butterfly.py («Небесная бабочка», 19.11). Здесь только проявление невидимого мага.
    fx('illusion_butterfly_reveal', 'Сон бабочки: невидимый маг/союзник ударил или скастовал — мерцающий контур на 1 с (20 тиков; caster = '
                                    'проявившийся; видят жертвы). Оболочка по росту мерцает рвано (pulse 3 тика), стеклянные блики, '
                                    'контур гаснет к концу — код в эти 20 тиков рисует модель полупрозрачной.', 'illusion', 22, [
        E('aura', 0, 'caster', target='caster', duration=20, thickness=0.06, pulse=[0.7, 3], motes=8, texture='mote_glass', color=PEARL,
          **{'in': ease(1), 'out': ease(14, 'easeInSine')}),
        E('aura', 0, 'caster', target='caster', duration=16, thickness=0.11, pulse=[0.6, 5], motes=0, ring=False, color=PINK, brightness=0.5,
          **{'in': ease(1), 'out': ease(12, 'easeInSine')}),
    ])



# ================================================================== «Сон бабочки» — мир сна, смерть во сне, пробуждение (ПЕРЕСМОТР 19.11)
# ТЗ: T22, разделы «ПЕРЕСМОТР механики» (сон 2 мин = 2400 тиков, r64, урон и смерть во сне ненастоящие, возрождение во сне,
# пробуждение без урона), «Сон бабочки — улучшение» (пп. 2, 5, 6), «Музыка». Шкала: 0 = начало каста; сон — тики 240…2640 от начала
# каста (12…132 с); кульминация музыки 130.3 с (удар) и 132.0 с (второй акцент) — ролик пробуждения начинается на 2366 тике сна
# (130.3 с), стекло мира бьётся на его 34 тике = 2400 тик сна = 132.0 с.
DREAM_TICKS = 2400
WAKE_START = 2366            # тик сна, когда стартует ролик пробуждения (130.3 с от начала каста — удар в музыке)
WAKE_BREAK = 34              # тик ролика, когда стекло осыпается (= конец сна, 132.0 с — второй акцент)
WAKE_LEN = 50                # длина ролика пробуждения (2.5 с)


def _fbm(w, h, seed, octaves=5, base=3, persist=0.55):
    """Плавный шум 0..1 (значения на решётке, бикубическое растяжение), без тайлинга."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = base * 2 ** o
        g = rng.random((max(2, int(n * h / w) + 2), n + 2)).astype(np.float32)
        im = Image.fromarray(g, 'F').resize((w + 2 * w // n, h + 2 * w // n), Image.BICUBIC)
        a = np.asarray(im)[w // n:w // n + h, w // n:w // n + w]
        out += a * amp
        tot += amp
        amp *= persist
    out /= tot
    out -= out.min()
    return out / max(1e-6, out.max())


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


IRID = [PEARL, PINK, LILAC, BLUE, PEARL]


SKY_IRID = ['#FFB3E2', '#C99BFF', '#9FB2FF', '#FFD0EC', '#E6A8FF', '#FFB3E2']   # для неба: насыщеннее, без белого (кладётся на голубое)


def _irid(t, pal=None):
    """Перламутр: цикл белый → розовый → лиловый → голубой (t по модулю 1)."""
    pal = pal or IRID
    t = np.mod(t, 1.0)
    xs = np.linspace(0, 1, len(pal))
    return np.stack([np.interp(t, xs, [_hex(c)[k] for c in pal]) for k in range(3)], -1)


def _star(p, x, y, r, w=1.2, fill=255):
    """Блик-звёздочка: 4 луча (длинные горизонталь/вертикаль) + точка."""
    p.taper([(x - r, y), (x, y), (x + r, y)], [0, w * 2, 0], fill)
    p.taper([(x, y - r * 0.8), (x, y), (x, y + r * 0.8)], [0, w * 2, 0], fill)
    p.dot(x, y, w * 1.2, fill)


def _voronoi(sites, W, H):
    """Ячейки Вороного в прямоугольнике [0,W]×[0,H] отсечением полуплоскостями: [[(x, y)…] по каждой точке]."""
    cells = []
    for i, (sx, sy) in enumerate(sites):
        poly = [(0, 0), (W, 0), (W, H), (0, H)]
        for j, (tx, ty) in enumerate(sites):
            if i == j:
                continue
            mx, my, nx, ny = (sx + tx) / 2, (sy + ty) / 2, tx - sx, ty - sy        # оставляем сторону, где (p-m)·n ≤ 0
            out = []
            for k in range(len(poly)):
                a, b = poly[k], poly[(k + 1) % len(poly)]
                da, db = (a[0] - mx) * nx + (a[1] - my) * ny, (b[0] - mx) * nx + (b[1] - my) * ny
                if da <= 0:
                    out.append(a)
                if (da <= 0) != (db <= 0):
                    t = da / (da - db)
                    out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            poly = out
            if not poly:
                break
        cells.append(poly)
    return cells


def _jag_edges(cells, W, H, seed, amp=0.05, depth=3):
    """Делает общие рёбра ячеек ломаными (одинаково для обеих соседних ячеек), рёбра по краю экрана — прямые."""
    cache = {}

    def edge(a, b):
        on_border = (abs(a[0] - b[0]) < 1e-6 and (abs(a[0]) < 1e-6 or abs(a[0] - W) < 1e-6)) or \
                    (abs(a[1] - b[1]) < 1e-6 and (abs(a[1]) < 1e-6 or abs(a[1] - H) < 1e-6))
        if on_border:
            return [a, b]
        ka, kb = (round(a[0], 2), round(a[1], 2)), (round(b[0], 2), round(b[1], 2))
        key = (ka, kb) if ka <= kb else (kb, ka)
        if key not in cache:
            r = random.Random('%s%s' % (seed, key))
            cache[key] = jag(r, key[0], key[1], depth, amp)
        pts = cache[key]
        return pts if (ka, kb) == key else pts[::-1]
    out = []
    for poly in cells:
        q = []
        for k in range(len(poly)):
            q += edge(poly[k], poly[(k + 1) % len(poly)])[:-1]
        out.append(q)
    return out


# ------------------------------------------------------------------ текстуры мира сна
def wound_butterfly_atlas():
    """Бабочка-метка ранения (атлас 512×128: 4 кадра взмаха — раскрыта, 2/3, 1/3, почти сложена; цвет — стекло: розовое у тела,
    лиловое к краю, голубой отлив, белая кромка). Код рисует billboard ≈0.24 бл. и листает кадры 0-1-2-3-2-1 (период 6 тиков)."""
    W, H, F = 512, 128, 4
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rgb = np.zeros((H, W, 3), np.float32)
    al = np.zeros((H, W), np.float32)
    for k, op in enumerate((1.0, 0.68, 0.36, 0.12)):
        pf, pl = Pen(128, 128), Pen(128, 128)
        up, lo = butterfly_shape(52)
        for side in (1, -1):
            for wing, f_ in ((up, 255), (lo, 220)):
                pf.poly([(64 + side * x_ * op, 68 + y_) for x_, y_ in wing], f_)
        butterfly(pl, 64, 68, 52, 0, 3.0, veins=op > 0.3, open_=op)
        fa = np.asarray(gst.to_alpha(pf, glow=0), np.float32) / 255
        la = np.asarray(gst.to_alpha(pl, glow=0.6, glow_r=2.5), np.float32) / 255
        cx = np.abs(xx[:, :128] - 64) / 56
        base = _irid(0.2 + 0.55 * cx + 0.1 * (yy[:, :128] / 128))
        c = base * (1 - la[..., None]) + 255 * la[..., None]
        rgb[:, k * 128:(k + 1) * 128] = c
        al[:, k * 128:(k + 1) * 128] = np.clip(fa * 0.5 + la, 0, 1)
    _save_rgba(np.dstack([rgb, al * 255]), 'illusion_wound_butterfly')


def dream_death_overlay():
    """Экранная накладка «смерть сна» (1600×900, RGBA): перламутровая виньетка, по краям экран разбит в стекло (трещины гуще к краю),
    из середины к краям разлетаются белые бабочки; центр прозрачен. Тайминг — в письме (≈1.2 с)."""
    W, H = 1600, 900
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    ex, ey = (x - W / 2) / (W / 2), (y - H / 2) / (H / 2)
    r = np.hypot(ex, ey * 0.95)
    n1 = _fbm(W, H, 3331, 6, 4)
    vig = _smooth(0.42, 1.15, r + 0.12 * (n1 - 0.5))
    col = _irid(r * 1.2 + 0.4 * n1) * 0.5 + _hex('#F3EEFF')[None, None] * 0.5
    rr = random.Random(3332)
    sites = []
    for _ in range(70):                                                          # ячейки «стекла» только у края
        a = rr.uniform(0, TAU)
        rad = 0.55 + 0.6 * math.sqrt(rr.random())
        sites.append((W / 2 + rad * W / 2 * math.cos(a), H / 2 + rad * H / 2 * math.sin(a)))
    cells = _jag_edges([c for c in _voronoi(sites, W, H) if len(c) > 2], W, H, 3333, amp=0.05)
    p = Pen(W, H)
    for c in cells:
        p.line(c + [c[0]], 2.0, caps=False)
    for i in range(22):
        a = i * TAU / 22 + rr.uniform(-0.1, 0.1)
        crack(p, rr, (W / 2 + 0.5 * W / 2 * math.cos(a), H / 2 + 0.5 * H / 2 * math.sin(a)),
              (W / 2 + 1.1 * W / 2 * math.cos(a), H / 2 + 1.1 * H / 2 * math.sin(a)), 2.4, depth=3, amp=0.07, branches=1)
    cr = np.asarray(gst.to_alpha(p, glow=0.8, glow_r=4), np.float32) / 255 * _smooth(0.45, 0.85, r)
    b = Pen(W, H)
    for i in range(22):                                                          # бабочки летят из центра к краям
        a = (i + rr.uniform(0.2, 0.8)) * TAU / 22
        rad = rr.uniform(0.45, 0.95)
        bx, by = W / 2 + rad * W / 2 * math.cos(a), H / 2 + rad * H / 2 * math.sin(a)
        s = rr.uniform(22, 44) * (0.6 + 0.6 * rad)
        butterfly(b, bx, by, s, a + math.pi / 2 + rr.uniform(-0.5, 0.5), lw=max(1.4, s / 14), fill=110, veins=s > 24,
                  open_=rr.choice((1.0, 0.8, 0.5)))
    bf = np.asarray(gst.to_alpha(b, glow=0.7, glow_r=4), np.float32) / 255
    col = col * (1 - np.maximum(cr, bf)[..., None]) + 255 * np.maximum(cr, bf)[..., None]
    alpha = np.clip(vig * 0.82 + cr * 0.9 + bf * 0.95, 0, 1)
    _save_rgba(np.dstack([np.clip(col, 0, 255), alpha * 255]), 'illusion_dream_death')


def dream_ripple():
    """Рябь входа/выхода отражения и «смерти сна» (1024, белое на прозрачном): концентрические кольца, яркое внешнее,
    к центру слабее и чаще. Код растягивает её из центра экрана (0.2 → 2.4 высоты экрана за 10 тиков, альфа 0.7 → 0)
    и/или использует как карту смещения (сдвиг UV по радиусу ∝ яркости) для «водяной» дрожи картинки."""
    S = 1024
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    r = np.hypot(x - S / 2, y - S / 2) / (S / 2)
    a = np.zeros_like(r)
    for k, (rad, w, s) in enumerate(((0.96, 0.025, 1.0), (0.86, 0.02, 0.7), (0.75, 0.016, 0.5), (0.63, 0.013, 0.35), (0.5, 0.011, 0.22),
                                     (0.36, 0.009, 0.12))):
        a += np.exp(-((r - rad) / w) ** 2) * s
        a += np.exp(-((r - rad + 0.035) / (w * 2.5)) ** 2) * s * 0.25          # мягкая тень за гребнем
    a[r > 1] = 0
    v = np.clip(a, 0, 1) * 255
    _save_rgba(np.dstack([np.full_like(v, 255), np.full_like(v, 255), np.full_like(v, 255), v]), 'illusion_dream_ripple')


def wake_glass():
    """Пробуждение: экран — стекло, разбитое сеткой (1920×1080, белое на прозрачном) + атлас кусков (2048², 8×8 ячеек по 256) +
    карта кусков illusion_wake_shards.json (многоугольник каждого куска в долях экрана, место в атласе, задержка и вращение
    падения). Точка удара — (0.5, 0.46) экрана. Куски — те же ячейки, что на сетке, так что код может нарезать снимок экрана
    по многоугольникам и уронить их, а атлас (стеклянная кромка и блик) положить поверх."""
    W, H = 1920, 1080
    cx, cy = W * 0.5, H * 0.46
    rr = random.Random(3341)
    sites = [(cx, cy)]
    for ring, n in ((0.09, 5), (0.2, 8), (0.36, 11), (0.56, 14), (0.8, 16)):
        for i in range(n):
            a = (i + rr.uniform(0.15, 0.85)) * TAU / n
            rad = ring * rr.uniform(0.85, 1.15)
            sites.append((cx + rad * W * 0.62 * math.cos(a), cy + rad * W * 0.62 * math.sin(a) * 0.9))
    sites = [(min(W - 4, max(4, sx)), min(H - 4, max(4, sy))) for sx, sy in sites]
    cells = _jag_edges(_voronoi(sites, W, H), W, H, 3342, amp=0.035)
    # сетка трещин
    p = Pen(W, H)
    for c in cells:
        p.line(c + [c[0]], 2.4, caps=False)
    inner = Pen(W, H)                                                            # тонкие трещинки внутри кусков (не рвут их)
    for i in range(24):
        a = i * TAU / 24 + rr.uniform(-0.08, 0.08)
        crack(inner, rr, (cx + 10 * math.cos(a), cy + 10 * math.sin(a)), (cx + 1300 * math.cos(a), cy + 1300 * math.sin(a)), 1.2,
              depth=4, amp=0.05, branches=1, fill=200)
    for k in range(4):                                                            # звезда удара в центре
        a = k * math.pi / 4 + 0.2
        p.taper([(cx - 120 * math.cos(a), cy - 120 * math.sin(a)), (cx, cy), (cx + 120 * math.cos(a), cy + 120 * math.sin(a))], [0, 7, 0])
    p.dot(cx, cy, 9)
    grid = np.maximum(np.asarray(gst.to_alpha(p, glow=0.9, glow_r=5), np.float32),
                      np.asarray(gst.to_alpha(inner, glow=0.4, glow_r=2), np.float32) * 0.7)
    _save_rgba(np.dstack([np.full_like(grid, 255), np.full_like(grid, 250), np.full_like(grid, 255), grid]), 'illusion_wake_grid')
    # стекло кусков: кромка-фаска, косой блик, перламутровый отлив, те же внутренние трещинки
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    n1 = _fbm(W // 2, H // 2, 3343, 5, 3)
    n1 = np.asarray(Image.fromarray(n1, 'F').resize((W, H), Image.BICUBIC))
    tint = _irid((x + y) / (W + H) * 1.4 + 0.3 * n1)
    sheen = np.exp(-((((x * 0.6 - y) / W) % 0.33) - 0.16) ** 2 / 0.0006) * 0.5
    inner_a = np.asarray(gst.to_alpha(inner, glow=0.3, glow_r=2), np.float32) / 255
    atlas = np.zeros((2048, 2048, 4), np.float32)
    shards = []
    maxd = max(math.hypot(sx - cx, sy - cy) for sx, sy in sites)
    for i, c in enumerate(cells):
        xs, ys = [q[0] for q in c], [q[1] for q in c]
        x0, y0, x1, y1 = max(0, int(min(xs)) - 2), max(0, int(min(ys)) - 2), min(W, int(max(xs)) + 3), min(H, int(max(ys)) + 3)
        m = Image.new('L', (W, H), 0)
        ImageDraw.Draw(m).polygon(c, fill=255)
        mk = np.asarray(m, np.float32)[y0:y1, x0:x1] / 255
        er = np.asarray(m.crop((x0, y0, x1, y1)).filter(ImageFilter.MinFilter(9)), np.float32) / 255
        rim = np.clip(mk - er, 0, 1)                                              # фаска шириной ≈4 px
        g = tint[y0:y1, x0:x1] * 0.6 + 255 * 0.4
        a_ = mk * (0.16 + sheen[y0:y1, x0:x1] + inner_a[y0:y1, x0:x1] * 0.6) + rim * 0.85
        g = g * (1 - rim[..., None]) + 255 * rim[..., None]
        piece = np.dstack([g, np.clip(a_, 0, 1) * 255])
        w_, h_ = x1 - x0, y1 - y0
        k_ = min(1.0, 252 / max(w_, h_))
        im = Image.fromarray(np.clip(piece, 0, 255).astype(np.uint8), 'RGBA').resize((max(1, int(w_ * k_)), max(1, int(h_ * k_))), Image.LANCZOS)
        ax, ay = (i % 8) * 256 + 2, (i // 8) * 256 + 2
        atlas[ay:ay + im.height, ax:ax + im.width] = np.asarray(im, np.float32)
        scx, scy = sites[i]
        d = math.hypot(scx - cx, scy - cy) / maxd
        rs = random.Random(3350 + i)
        shards.append({'i': i,
                       'poly': [[round(px / W, 4), round(py / H, 4)] for px, py in c],
                       'screen': [round(x0 / W, 4), round(y0 / H, 4), round(x1 / W, 4), round(y1 / H, 4)],
                       'atlas': [round(ax / 2048, 5), round(ay / 2048, 5), round((ax + im.width) / 2048, 5), round((ay + im.height) / 2048, 5)],
                       'delay': int(round(d * 6)),
                       'vx': round((scx - cx) / W * 0.03 + rs.uniform(-0.004, 0.004), 4),
                       'vy': round(-0.012 - rs.uniform(0, 0.01) + (scy - cy) / H * 0.01, 4),
                       'spin': round(rs.uniform(4, 14) * rs.choice((-1, 1)), 1),
                       'tilt': round(rs.uniform(6, 18) * rs.choice((-1, 1)), 1)})
    assert len(cells) <= 64, len(cells)
    _save_rgba(atlas, 'illusion_wake_shards')
    write('textures/fx/illusion_wake_shards.json', {
        'comment': 'Пробуждение «Сна бабочки» (T22): куски разбитого экрана. poly — многоугольник куска в долях экрана (0..1, y вниз), '
                   'screen — его рамка, atlas — место картинки куска (стекло: фаска, блик, отлив) в textures/fx/illusion_wake_shards.png '
                   '(uv 0..1, рамка screen вписана с сохранением пропорций). Падение (код, на экране): с тика ролика 34 + delay, '
                   'x += vx·t, y += vy·t + g·t²/2 (g = 0.012 высоты экрана/тик²), поворот spin °/тик в плоскости экрана, наклон tilt° '
                   '(сжатие по x как поворот вокруг вертикали) к 10-му тику падения; альфа 1 → 0 на последних 6 тиках ролика. '
                   'Под кусками — настоящий мир (рисовать кусками снимок последнего кадра сна, uv = poly). Сгенерировано tools/gen_illusion_fx.py.',
        'impact': [0.5, 0.46], 'gravity': 0.012, 'atlasSize': 2048, 'shards': shards})


def dream_textures():
    """Экранные материалы мира сна, которые ещё зовёт код (DreamScreen). Мир сна, каст и пробуждение — gen_celestial_butterfly."""
    wound_butterfly_atlas()
    dream_death_overlay()
    dream_ripple()
    wake_glass()     # УСТАРЕЛО (19.11, «Небесная бабочка»): сетка трещин и куски стекла пробуждения — удалить вместе с кодом DreamScreen


# ================================================================== модели (fx/meshes, части boxes — docs/fx.md)
def _r(v):
    return round(float(v), 4)


def bar(p, q, w, d=None, tone=0):
    """Брусок вдоль отрезка p→q (сечение w×d). Поворот [rx, ry, rz] (Euler YXZ, как в docs/fx.md): ось x бруска → направление p→q."""
    p, q = np.asarray(p, float), np.asarray(q, float)
    c = (p + q) / 2
    v = q - p
    l = float(np.linalg.norm(v))
    d = w if d is None else d
    v = v / max(l, 1e-9)
    rz = math.degrees(math.asin(max(-1.0, min(1.0, v[1]))))
    ry = math.degrees(math.atan2(-v[2], v[0]))
    return [_r(c[0] - l / 2), _r(c[1] - w / 2), _r(c[2] - d / 2), _r(c[0] + l / 2), _r(c[1] + w / 2), _r(c[2] + d / 2), tone,
            [0, round(ry, 2), round(rz, 2)]]


def cube(c, h, tone, hy=None, hz=None, rot=None):
    hy = h if hy is None else hy
    hz = h if hz is None else hz
    b = [_r(c[0] - h), _r(c[1] - hy), _r(c[2] - hz), _r(c[0] + h), _r(c[1] + hy), _r(c[2] + hz), tone]
    if rot:
        b.append(rot)
    return b


def inflate(boxes, k):
    out = []
    for b in boxes:
        nb = [b[0] - k, b[1] - k, b[2] - k, b[3] + k, b[4] + k, b[5] + k] + b[6:]
        out.append([_r(v) if isinstance(v, float) else v for v in nb[:6]] + nb[6:])
    return out


def bounds_y(boxes):
    return [_r(min(b[1] for b in boxes) - 0.05), _r(max(b[4] for b in boxes) + 0.05)]


def mesh(id, comment, style_, formed, collapse, parts, extra=None):
    o = {'comment': comment + ' Сгенерировано tools/gen_illusion_fx.py.', 'style': style_, 'center': 0, 'formedAt': formed,
         'collapse': {'duration': collapse, 'easing': 'easeInCubic'}, 'parts': parts}
    if extra:
        o.update(extra)
    write('fx/meshes/%s.json' % id, o)
    return o


def mesh_dome():
    """Купол «Лабиринта» радиуса 1 (эффект масштабирует ×14): рёбра геодезической полусферы (икосаэдр, 3 деления) перламутровыми
    тонами по кругу (лиловый → розовый → голубой), узлы-огоньки, кольцо у земли."""
    t = (1 + 5 ** 0.5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    V = [np.array(v, float) / np.linalg.norm(v) for v in V]
    F = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
         (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for _ in range(3):
        cache, nf = {}, []
        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                m = V[a] + V[b]
                V.append(m / np.linalg.norm(m))
                cache[k] = len(V) - 1
            return cache[k]
        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        F = nf
    edges = set()
    for a, b, c in F:
        for x, y in ((a, b), (b, c), (c, a)):
            edges.add((min(x, y), max(x, y)))
    ribs, nodes = [], []
    used = set()
    for a, b in sorted(edges):
        pa, pb = V[a], V[b]
        if pa[1] < -0.005 or pb[1] < -0.005:
            continue
        ang = math.atan2(pa[2] + pb[2], pa[0] + pb[0])
        tone = int(((ang / TAU) * 3 + 3) * 1.0) % 3
        ribs.append(bar(pa, pb, 0.0045, tone=tone))
        used.update((a, b))
    for k in sorted(used):                                       # огоньки — только на каждом ~5-м узле, мелкие
        if V[k][1] > 0.02 and (k * 7) % 5 == 0:
            nodes.append(cube(V[k], 0.006, 3))
    for k in range(96):                                          # кольцо у земли
        a0, a1 = TAU * k / 96, TAU * (k + 1) / 96
        nodes.append(bar((math.cos(a0), 0.01, math.sin(a0)), (math.cos(a1), 0.01, math.sin(a1)), 0.01, tone=4))
    appear = {'delay': 0, 'duration': 24, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.15}
    mesh('illusion_dome', 'Купол «Зеркального лабиринта» (T22): радиус 1 — эффект ставит scale 14. Рёбра геодезической полусферы '
                          'перламутровыми тонами по кругу, узлы-огоньки, кольцо у земли; встаёт снизу вверх за 24 тика.', 'illusion', 24, 16, [
        {'type': 'boxes', 'tones': [LILAC, PINK, BLUE, WHITE, PEARL], 'glowTones': [3, 4], 'blend': 'additive', 'opacity': 0.22, 'shade': True,
         'boxes': ribs, 'appear': appear, 'bounds': [-0.02, 1.02]},
        {'type': 'boxes', 'tones': [LILAC, PINK, BLUE, WHITE, PEARL], 'glowTones': [3, 4], 'blend': 'additive', 'opacity': 0.3, 'shade': False,
         'boxes': nodes, 'appear': appear, 'bounds': [-0.02, 1.02]},
    ], extra={'hit': {'duration': 12, 'width': 0.2, 'rings': 2, 'spacing': 0.4, 'strength': 1.2, 'shake': 0.006, 'shakePeriod': 5,
                      'flash': 0.8, 'sparks': 10, 'sparkSpeed': 0.12, 'color': PEARL}})
    return len(ribs) + len(nodes)


def mesh_mirror_wall():
    """Модуль зеркальной стены «Лабиринта»: 1 × 3 × 0.14 блока (x −0.5..0.5, y 0..3, z −0.07..0.07) — плитки зеркала
    с перламутровым отливом по диагонали (непрозрачные), светлая кромка, 3 светящиеся трещины. Код может тайлить его вдоль стен
    или рисовать стены сам текстурами textures/fx/illusion_mirror_wall(+_cracks) — выглядят одинаково."""
    tiles, glow_ = [], []
    nx, ny = 8, 24
    for i in range(nx):
        for j in range(ny):
            x0, x1 = -0.5 + i / nx, -0.5 + (i + 1) / nx
            y0, y1 = 3 * j / ny, 3 * (j + 1) / ny
            u, v = (i + 0.5) / nx, (j + 0.5) / ny               # мягкие пятна перламутра на серебре (как разводы на зеркале)
            d = math.sin(TAU * (u * 0.8 + v * 1.3) + 0.6) + 0.6 * math.sin(TAU * (u * 1.7 - v * 0.9) + 2.1)
            tone = 1 if d > 0.95 else (2 if d > 0.75 else (3 if d < -1.1 else 0))
            tiles.append([_r(x0), _r(y0), -0.07, _r(x1), _r(y1), 0.07, tone])
    for y in (0.0, 3.0):                                         # кромки
        glow_.append([-0.52, _r(y - 0.025), -0.08, 0.52, _r(y + 0.025), 0.08, 4])
    for x in (-0.5, 0.5):
        glow_.append([_r(x - 0.015), 0, -0.075, _r(x + 0.015), 3, 0.075, 4])
    rng = random.Random(2215)
    for _ in range(3):                                           # трещины (на обеих сторонах)
        x, y = rng.uniform(-0.3, 0.3), rng.uniform(0.6, 2.4)
        for k in range(rng.randint(3, 5)):
            a = rng.uniform(0, TAU)
            px, py = x, y
            for seg in range(3):
                l = rng.uniform(0.08, 0.18)
                a += rng.uniform(-0.5, 0.5)
                qx, qy = max(-0.48, min(0.48, px + l * math.cos(a))), max(0.04, min(2.96, py + l * math.sin(a)))
                for z in (-0.074, 0.074):
                    glow_.append(bar((px, py, z), (qx, qy, z), 0.008, 0.004, tone=5))
                px, py = qx, qy
    appear = {'delay': 0, 'duration': 10, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.6}
    mesh('illusion_mirror_wall', 'Модуль зеркальной стены «Зеркального лабиринта» (T22): 1×3×0.14 блока, непрозрачное зеркало '
                                 '(плитки серебра с перламутровым отливом), светлая кромка, светящиеся трещинки. Вырастает из земли за 10 тиков.',
         'illusion', 10, 8, [
             {'type': 'boxes', 'tones': ['#B9B3CC', '#C4B6DE', '#CDB9D8', '#B4CAD8', PEARL, WHITE], 'glowTones': [4, 5], 'blend': 'translucent',
              'opacity': 0.97, 'shade': True, 'boxes': tiles, 'appear': appear, 'bounds': [0, 3]},
             {'type': 'boxes', 'tones': ['#B6AECB', '#C9B4E6', '#D9B8DC', '#A9D2E0', PEARL, WHITE], 'glowTones': [4, 5], 'blend': 'additive',
              'opacity': 0.8, 'shade': False, 'boxes': glow_, 'appear': appear, 'bounds': [0, 3]},
         ])


def mesh_nightmare():
    """Безликое чудовище «Кошмара наяву» (рост 1.95, ноги на y = 0, лицом к +z): сгорбленное, слишком длинные руки до колен
    с длинными пальцами-когтями, гладкая голова без черт (только бледная «маска»), лохмотья с плеч. Размытый край — два
    раздутых полупрозрачных слоя тех же брусков (дымка вокруг силуэта)."""
    body = []
    T0, T1, T2, FACE, CLAW = 0, 1, 2, 3, 4
    for sx in (-1, 1):                                           # ноги
        hip, knee, ankle, toe = (sx * 0.11, 0.98, 0.0), (sx * 0.14, 0.55, 0.09), (sx * 0.12, 0.1, -0.05), (sx * 0.12, 0.03, 0.17)
        body += [bar(hip, knee, 0.15, tone=T1), bar(knee, ankle, 0.11, tone=T0), bar(ankle, toe, 0.06, 0.1, tone=T0), cube(knee, 0.07, T0)]
        for k in (-1, 0, 1):
            body.append(bar(toe, (sx * 0.12 + k * 0.035, 0.0, 0.27), 0.02, tone=CLAW))
    body.append(cube((0, 1.0, -0.01), 0.16, T1, 0.1, 0.11))       # таз
    body.append(cube((0, 1.16, 0.0), 0.15, T0, 0.1, 0.1, rot=[8, 0, 0]))          # живот (впалый, уже)
    body.append(cube((0, 1.42, 0.08), 0.2, T1, 0.18, 0.12, rot=[22, 0, 0]))       # грудь: сгорблена вперёд
    body.append(cube((0, 1.52, 0.02), 0.22, T0, 0.07, 0.1, rot=[30, 0, 0]))       # плечевой пояс, горб
    body.append(cube((0, 1.36, -0.03), 0.12, T0, 0.16, 0.06, rot=[22, 0, 0]))     # хребет сзади
    for k in range(3):                                           # рёбра проступают спереди
        y = 1.32 + 0.08 * k
        z = 0.15 + 0.035 * k
        for sx in (-1, 1):
            body.append(bar((sx * 0.02, y, z + 0.01), (sx * 0.17, y - 0.05, z - 0.06), 0.02, 0.02, tone=T2))
    neck0, neck1 = (0, 1.56, 0.12), (0, 1.74, 0.27)
    body.append(bar(neck0, neck1, 0.1, tone=T1))
    head_c = (0, 1.84, 0.32)                                     # голова: гладкий вытянутый овал, наклонена вперёд
    body.append(cube(head_c, 0.115, T0, 0.15, 0.13, rot=[18, 0, 0]))
    body.append(cube((0, head_c[1] + 0.15, head_c[2] - 0.03), 0.09, T0, 0.03, 0.11, rot=[18, 0, 0]))      # темя
    body.append(cube((0, head_c[1] - 0.16, head_c[2] + 0.05), 0.075, T0, 0.03, 0.09, rot=[18, 0, 0]))     # подбородок
    body.append(cube((0, head_c[1] - 0.005, head_c[2] + 0.125), 0.085, FACE, 0.115, 0.012, rot=[18, 0, 0]))  # «маска»: гладкая, без черт
    for sx in (-1, 1):                                           # руки: длинные, висят ниже колен
        sh, el, wr, palm = (sx * 0.23, 1.54, 0.1), (sx * 0.33, 1.16, 0.16), (sx * 0.31, 0.76, 0.24), (sx * 0.3, 0.66, 0.27)
        body += [cube(sh, 0.08, T1), bar(sh, el, 0.1, tone=T1), bar(el, wr, 0.08, tone=T0), bar(wr, palm, 0.1, 0.05, tone=T0)]
        for k in range(4):                                       # пальцы: два сустава, загнуты внутрь — когти
            dx = (k - 1.5) * 0.028
            f0 = (palm[0] + dx, palm[1] - 0.02, palm[2])
            f1 = (palm[0] + dx * 1.4, palm[1] - 0.2, palm[2] + 0.03)
            f2 = (palm[0] + dx * 1.2 - sx * 0.03, palm[1] - 0.31, palm[2] + 0.1)
            body += [bar(f0, f1, 0.022, tone=T0), bar(f1, f2, 0.018, tone=CLAW)]
        body.append(bar((palm[0] - sx * 0.045, palm[1], palm[2]), (palm[0] - sx * 0.08, palm[1] - 0.14, palm[2] + 0.08), 0.02, tone=CLAW))
    rng = random.Random(2216)
    rags = []
    for k in range(18):                                          # лохмотья: полосы с плеч и груди, к краю шире и рванее
        a = TAU * k / 18
        x0, z0 = 0.21 * math.cos(a), 0.06 + 0.13 * math.sin(a)
        y0 = 1.56 + 0.04 * math.sin(a * 2)
        L = rng.uniform(0.55, 1.05)
        x1, z1 = x0 * 1.6 + rng.uniform(-0.05, 0.05), z0 * 1.4 - 0.05 + rng.uniform(-0.05, 0.05)
        rags.append(bar((x0, y0, z0), (x1, y0 - L, z1), 0.07, 0.012, tone=T1 if k % 3 else T2))
        if rng.random() < 0.6:
            rags.append(bar((x1, y0 - L, z1), (x1 * 1.08, y0 - L - rng.uniform(0.08, 0.2), z1), 0.03, 0.01, tone=T0))
    for sx in (-1, 1):                                           # рваные рукава
        for k in range(3):
            p0 = (sx * (0.3 + 0.01 * k), 1.2 - 0.12 * k, 0.17 + 0.02 * k)
            rags.append(bar(p0, (p0[0] + sx * 0.06, p0[1] - rng.uniform(0.25, 0.45), p0[2] - 0.04), 0.05, 0.01, tone=T1))
    tones = ['#07050B', '#120C1A', '#231833', '#4A3E5C', '#6A5A80', '#2A1A3A', '#7A5AAA']
    appear = {'delay': 0, 'duration': 12, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.6}
    b = bounds_y(body)
    core = [x for x in body if x[6] in (0, 1)]
    body += rags
    haze1 = [x[:6] + [5] + x[7:] for x in inflate(core, 0.03)]
    haze2 = [x[:6] + [5] + x[7:] for x in inflate(core, 0.07)]
    mesh('illusion_nightmare', 'Безликое чудовище «Кошмара наяву» (T22): рост 1.95 (ноги y=0, лицом к +z), сгорблено, руки до колен с '
                               'когтями, гладкая голова без лица (бледная «маска»), лохмотья; размытый край — два раздутых полупрозрачных '
                               'слоя. Клиент жертвы рисует его вместо каждого существа (масштаб = рост сущности / 1.95), качает (idle — код).',
         'illusion', 12, 10, [
             {'type': 'boxes', 'tones': tones, 'glowTones': [], 'blend': 'translucent', 'opacity': 1.0, 'shade': True, 'boxes': body,
              'appear': appear, 'bounds': b},
             {'type': 'boxes', 'tones': tones, 'glowTones': [], 'blend': 'translucent', 'opacity': 0.22, 'shade': False, 'boxes': haze1,
              'appear': appear, 'bounds': b},
             {'type': 'boxes', 'tones': tones, 'glowTones': [], 'blend': 'translucent', 'opacity': 0.09, 'shade': False, 'boxes': haze2,
              'appear': appear, 'bounds': b},
         ])
    return len(body)


def mesh_butterfly():
    """Стеклянная бабочка (размах ≈ 1 при scale 1; эффекты берут 0.4–0.6): крылья — веер тонких пластин (стекло), светящиеся
    контур и жилки, крылья подняты буквой V. Голова — к +z."""
    s = 0.5
    up, lo = butterfly_shape(1.0)
    glass, lines = [], []
    lift = math.tan(math.radians(22))
    W = lambda x, y: (x * s, abs(x) * s * lift + 0.01, -y * s)
    for side in (1, -1):
        for wing, tone in ((up, 0), (lo, 1)):
            pts = [(side * x, y) for x, y in wing]
            root = (side * 0.05, -0.02 if wing is up else 0.08)
            for k in range(0, len(pts) - 1, 2):                    # веер пластин от корня к краю
                a, b = pts[k], pts[min(len(pts) - 1, k + 2)]
                m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                wdt = math.hypot(b[0] - a[0], b[1] - a[1]) * s * 1.15
                glass.append(bar(W(*root), W(*m), wdt, 0.006, tone=tone))
            for k in range(len(pts) - 1):                          # контур
                lines.append(bar(W(*pts[k]), W(*pts[k + 1]), 0.012, 0.012, tone=3))
            for k in range(3, len(pts) - 3, max(3, len(pts) // 5)):  # жилки
                lines.append(bar(W(*root), W(*pts[k]), 0.006, 0.006, tone=4))
    lines.append(bar((0, 0.01, 0.13), (0, 0.01, -0.24), 0.03, tone=3))      # тело
    for side in (1, -1):
        lines.append(bar((0, 0.02, 0.13), (side * 0.07, 0.07, 0.3), 0.008, tone=4))   # усики
    appear = {'delay': 0, 'duration': 8, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.2}
    mesh('illusion_butterfly', 'Стеклянная бабочка «Сна бабочки» (T22): размах ≈1 (эффекты масштабируют 0.4–0.6), крылья — веер '
                               'прозрачных пластин буквой V, светящиеся контур и жилки, голова к +z.', 'illusion', 8, 8, [
        {'type': 'boxes', 'tones': [PEARL, PINK, BLUE, WHITE, LILAC], 'glowTones': [3, 4], 'blend': 'additive', 'opacity': 0.28, 'shade': True,
         'boxes': glass, 'appear': appear, 'bounds': [-0.02, 0.3]},
        {'type': 'boxes', 'tones': [PEARL, PINK, BLUE, WHITE, LILAC], 'glowTones': [3, 4], 'blend': 'additive', 'opacity': 0.9, 'shade': False,
         'boxes': lines, 'appear': appear, 'bounds': [-0.02, 0.3]},
    ])


def meshes():
    mesh_dome()
    mesh_mirror_wall()
    mesh_nightmare()
    mesh_butterfly()



# ================================================================== иконки
def _c(h, a=255):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)


def _icon(size, draw, out, frame=None, k=8, crisp=False):
    """Рисуем в k× и уменьшаем LANCZOS (как gen_divine_t21 / gen_spell_icons.ps1). frame: ('sq'|'round', обод, фон)."""
    S = size * k
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if frame:
        kind, rim, bg = frame
        if kind == 'sq':
            d.rectangle([k * 0.5, k * 0.5, S - k * 0.5, S - k * 0.5], fill=_c(bg))
            w = S * 0.07
            d.rectangle([S * 0.05 - w / 2, S * 0.05 - w / 2, S * 0.95 + w / 2, S * 0.95 + w / 2], outline=_c(rim), width=int(w))
        else:
            d.ellipse([S * 0.04, S * 0.04, S * 0.96, S * 0.96], fill=_c(bg), outline=_c(rim), width=int(S * 0.085))
    draw(d, S)
    sm = im.resize((size, size), Image.LANCZOS)
    if crisp:                                                    # статусы — чётче края (как пиксель-арт у соседей)
        a = np.asarray(sm).copy()
        a[..., 3] = np.where(a[..., 3] < 70, 0, np.where(a[..., 3] > 150, 255, a[..., 3]))
        sm = Image.fromarray(a, 'RGBA')
    path = os.path.join(A, out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sm.save(path)
    WRITTEN.append(out)


def _poly(d, S, pts, fill=None, outline=None, w=0.0):
    P = [(S * x, S * y) for x, y in pts]
    if fill is not None:
        d.polygon(P, fill=fill)
    if outline is not None:
        d.line(P + [P[0]], fill=outline, width=max(1, int(S * w)), joint='curve')


def _figure(d, S, cx, cy, h, col, outline=None):
    """Силуэт человека (голова, плечи, ноги) высотой h (доли S), низ — cy."""
    hr = h * 0.13
    d.ellipse([S * (cx - hr), S * (cy - h), S * (cx + hr), S * (cy - h + 2 * hr)], fill=col, outline=outline,
              width=int(S * 0.02) if outline else 0)
    _poly(d, S, [(cx - h * 0.2, cy - h + 2.3 * hr), (cx + h * 0.2, cy - h + 2.3 * hr), (cx + h * 0.17, cy - h * 0.38), (cx + h * 0.12, cy),
                 (cx + h * 0.03, cy), (cx, cy - h * 0.3), (cx - h * 0.03, cy), (cx - h * 0.12, cy), (cx - h * 0.17, cy - h * 0.38)],
          fill=col, outline=outline, w=0.02)


def _bfly(d, S, cx, cy, sz, cols, outline, w=0.03, open_=1.0):
    up, lo = butterfly_shape(sz)
    for side in (1, -1):
        for wing, col in ((up, cols[0]), (lo, cols[1])):
            _poly(d, S, [(cx + side * x * open_, cy + y) for x, y in wing], fill=col, outline=outline, w=w)
    d.line([S * cx, S * (cy - sz * 0.24), S * cx, S * (cy + sz * 0.5)], fill=outline, width=int(S * w * 1.4))


def _heart(d, S, cx, cy, sz, solid, dash, w):
    pts = []
    for t in np.linspace(0, TAU, 120):
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * sz / 16, cy + y * sz / 16))
    left = [p for p in pts if p[0] <= cx + 1e-6]
    _poly(d, S, left + [(cx, cy + sz * 1.06)], fill=solid)
    for k in range(0, len(pts) - 1, 1):
        a, b = pts[k], pts[k + 1]
        if a[0] <= cx and b[0] <= cx:
            d.line([S * a[0], S * a[1], S * b[0], S * b[1]], fill=solid, width=int(S * w))
        elif (k // 5) % 2 == 0:
            d.line([S * a[0], S * a[1], S * b[0], S * b[1]], fill=dash, width=int(S * w * 1.3))
    zz = [(cx, cy - sz * 0.45), (cx - sz * 0.12, cy - sz * 0.1), (cx + sz * 0.1, cy + sz * 0.2), (cx - sz * 0.05, cy + sz * 0.55),
          (cx, cy + sz * 1.0)]
    d.line([(S * x, S * y) for x, y in zz], fill=(20, 10, 30, 255), width=int(S * w * 0.9))


def _mask(d, S, cx, cy, wdt, hgt, left, right, eye):
    """Маска-лицо: левая половина одним цветом, правая другим (чужое лицо), прорези глаз."""
    sh = lambda t: (cx + wdt * math.cos(t), cy + hgt * math.sin(t) * (1.0 if math.sin(t) < 0 else 1.15))
    _poly(d, S, [sh(t) for t in np.linspace(math.pi / 2, 1.5 * math.pi, 30)], fill=left)
    _poly(d, S, [sh(t) for t in np.linspace(-math.pi / 2, math.pi / 2, 30)], fill=right)
    for sx in (-1, 1):
        d.ellipse([S * (cx + sx * wdt * 0.42 - wdt * 0.2), S * (cy - hgt * 0.22), S * (cx + sx * wdt * 0.42 + wdt * 0.2), S * (cy + hgt * 0.02)],
                  fill=eye)
    d.line([S * (cx - wdt * 0.3), S * (cy + hgt * 0.62), S * (cx + wdt * 0.3), S * (cy + hgt * 0.55)], fill=eye, width=int(S * 0.04))


def icon_mirror_images(d, S):
    _figure(d, S, 0.27, 0.84, 0.56, _c(PINK, 120))
    _figure(d, S, 0.73, 0.84, 0.56, _c(BLUE, 120))
    _figure(d, S, 0.5, 0.88, 0.66, _c('#F4EEFF'), outline=_c(LILAC))
    for x in (0.38, 0.62):
        d.line([S * x, S * 0.2, S * x, S * 0.86], fill=_c(LILAC, 160), width=int(S * 0.02))


def icon_false_step(d, S):
    for k, x in enumerate((0.3, 0.4, 0.5)):                       # след рывка
        d.line([S * (x - 0.12), S * (0.36 + 0.14 * k), S * (x + 0.18), S * (0.36 + 0.14 * k)], fill=_c(LILAC, 150 - 30 * k), width=int(S * 0.05))
    _figure(d, S, 0.28, 0.86, 0.6, _c(PINK, 90))                  # копия, бегущая дальше
    _figure(d, S, 0.72, 0.86, 0.6, _c('#F4EEFF'), outline=_c(LILAC))
    _poly(d, S, [(0.52, 0.2), (0.62, 0.26), (0.52, 0.32)], fill=_c(WHITE))


def icon_veil(d, S):
    _figure(d, S, 0.44, 0.86, 0.62, _c(PINK, 110))
    _figure(d, S, 0.56, 0.86, 0.62, _c('#EDE4FF', 200))
    for k in range(4):
        y = 0.26 + 0.16 * k
        pts = [(S * (0.14 + 0.72 * t), S * (y + 0.035 * math.sin(t * 12 + k))) for t in np.linspace(0, 1, 30)]
        d.line(pts, fill=_c(LILAC if k % 2 else BLUE, 210), width=int(S * 0.035))


def icon_phantom_pain(d, S):
    _heart(d, S, 0.5, 0.42, 0.32, _c('#FF8ACB'), _c(PINK), 0.06)


def icon_borrowed_face(d, S):
    _mask(d, S, 0.5, 0.48, 0.28, 0.32, _c(LILAC), _c('#E8C3A2'), _c('#160F22'))
    for k in range(3):
        y = 0.2 + 0.28 * k
        d.line([S * 0.14, S * y, S * 0.24, S * (y + 0.04)], fill=_c(BLUE, 200), width=int(S * 0.03))


def icon_labyrinth(d, S):
    """Квадратный лабиринт: стенки-зеркала перламутром, в центре розовое око."""
    W = int(S * 0.06)
    segs = [((0.2, 0.2), (0.8, 0.2)), ((0.8, 0.2), (0.8, 0.62)), ((0.2, 0.2), (0.2, 0.8)), ((0.2, 0.8), (0.66, 0.8)),
            ((0.34, 0.34), (0.66, 0.34)), ((0.66, 0.34), (0.66, 0.66)), ((0.34, 0.34), (0.34, 0.66)), ((0.34, 0.66), (0.52, 0.66)),
            ((0.8, 0.8), (0.8, 0.8))]
    for k, ((x0, y0), (x1, y1)) in enumerate(segs):
        d.line([S * x0, S * y0, S * x1, S * y1], fill=_c(PEARL if k < 4 else LILAC), width=W)
    d.ellipse([S * 0.44, S * 0.44, S * 0.56, S * 0.56], fill=_c(PINK))


def icon_nightmare(d, S):
    d.ellipse([S * 0.3, S * 0.18, S * 0.7, S * 0.66], fill=_c('#0C0814'), outline=_c(LILAC), width=int(S * 0.045))
    d.ellipse([S * 0.37, S * 0.27, S * 0.63, S * 0.6], fill=_c('#4A3E5C'))         # безликая «маска»
    _poly(d, S, [(0.2, 0.9), (0.32, 0.62), (0.68, 0.62), (0.8, 0.9)], fill=_c('#0C0814'), outline=_c(LILAC), w=0.04)
    for x in (0.26, 0.74):
        d.line([S * x, S * 0.72, S * (x + (0.06 if x < 0.5 else -0.06)), S * 0.92], fill=_c('#6A5A80'), width=int(S * 0.03))


def icon_butterfly(d, S):
    _bfly(d, S, 0.5, 0.52, 0.38, (_c(PINK, 170), _c(BLUE, 170)), _c(WHITE), w=0.035)
    rng = random.Random(3)
    for _ in range(3):
        a = rng.uniform(0, TAU)
        pts = jag(rng, (0.5, 0.5), (0.5 + 0.42 * math.cos(a), 0.5 + 0.42 * math.sin(a)), 2, 0.2)
        d.line([(S * x, S * y) for x, y in pts], fill=_c(PEARL, 150), width=int(S * 0.018))


def effect_icon(d, S, kind):
    if kind == 'phantom_pain':
        _heart(d, S, 0.5, 0.4, 0.36, _c('#FF7AC0'), _c(PINK), 0.075)
    elif kind == 'waking_nightmare':
        d.ellipse([S * 0.24, S * 0.08, S * 0.76, S * 0.68], fill=_c('#0C0814'), outline=_c(LILAC), width=int(S * 0.06))
        d.ellipse([S * 0.33, S * 0.2, S * 0.67, S * 0.6], fill=_c('#5A4C70'))
        _poly(d, S, [(0.14, 0.98), (0.28, 0.66), (0.72, 0.66), (0.86, 0.98)], fill=_c('#0C0814'), outline=_c(LILAC), w=0.05)
    elif kind == 'butterfly_dream':
        _bfly(d, S, 0.5, 0.5, 0.44, (_c(PINK, 220), _c(BLUE, 220)), _c(WHITE), w=0.045)
    elif kind == 'borrowed_face':
        _mask(d, S, 0.5, 0.46, 0.34, 0.38, _c(LILAC), _c('#E8C3A2'), _c('#160F22'))
    elif kind == 'mirror_images':
        _figure(d, S, 0.3, 0.92, 0.66, _c(PINK, 200))
        _figure(d, S, 0.7, 0.92, 0.66, _c(BLUE, 200))
        _figure(d, S, 0.5, 0.96, 0.78, _c('#F4EEFF'), outline=_c(SHADOW))


def school_icon(d, S):
    """Значок школы: око над чертой зеркала и его отражение в ромбе (как ядро печати)."""
    _poly(d, S, [(0.5, 0.04), (0.96, 0.5), (0.5, 0.96), (0.04, 0.5)], fill=_c('#1A1028'), outline=_c(LILAC), w=0.07)
    up = [(0.5 + 0.27 * math.cos(t), 0.42 - 0.13 * math.sin(t)) for t in np.linspace(0, math.pi, 20)]
    dn = [(0.5 + 0.27 * math.cos(t), 0.42 + 0.13 * math.sin(t)) for t in np.linspace(math.pi, 0, 20)]
    _poly(d, S, up + dn, fill=_c(WHITE))
    d.ellipse([S * 0.42, S * 0.34, S * 0.58, S * 0.5], fill=_c(LILAC))
    d.ellipse([S * 0.47, S * 0.39, S * 0.53, S * 0.45], fill=_c('#1A1028'))
    d.line([S * 0.2, S * 0.56, S * 0.8, S * 0.56], fill=_c(PINK), width=int(S * 0.04))
    dn2 = [(0.5 + 0.22 * math.cos(t), 0.6 + 0.1 * math.sin(t)) for t in np.linspace(math.pi, 0, 20)]
    d.line([(S * x, S * y) for x, y in dn2], fill=_c(BLUE, 200), width=int(S * 0.04))


def prism_icon(d, S):
    """«Призма иллюзий»: осколок зеркала (перламутровый, с радужным бликом) в серебряной оправе с камнями, на подвесе."""
    frame = [(0.5, 0.06), (0.84, 0.46), (0.5, 0.96), (0.16, 0.46)]
    _poly(d, S, frame, fill=_c('#4A3E5C'), outline=_c('#1A1028'), w=0.06)
    inner = [(0.5, 0.17), (0.74, 0.46), (0.5, 0.84), (0.26, 0.46)]
    _poly(d, S, inner, fill=_c('#CFC4E8'))
    _poly(d, S, [(0.5, 0.17), (0.74, 0.46), (0.5, 0.5)], fill=_c('#F2ECFF'))                 # светлая грань
    _poly(d, S, [(0.26, 0.46), (0.5, 0.5), (0.5, 0.84)], fill=_c('#A898C8'))                 # тёмная грань
    _poly(d, S, [(0.36, 0.42), (0.5, 0.27), (0.54, 0.31), (0.4, 0.46)], fill=_c(PINK, 230))  # радужный блик
    _poly(d, S, [(0.42, 0.5), (0.56, 0.35), (0.6, 0.39), (0.46, 0.54)], fill=_c(BLUE, 230))
    d.line([S * 0.46, S * 0.62, S * 0.56, S * 0.52, S * 0.52, S * 0.7], fill=_c('#7A6A9A'), width=int(S * 0.025))   # трещинка
    for (x, y, c) in ((0.5, 0.08, PINK), (0.84, 0.46, BLUE), (0.16, 0.46, BLUE), (0.5, 0.94, LILAC)):
        d.ellipse([S * (x - 0.055), S * (y - 0.055), S * (x + 0.055), S * (y + 0.055)], fill=_c(c), outline=_c('#1A1028'), width=int(S * 0.02))
    _poly(d, S, frame, outline=_c('#E6E0F4'), w=0.025)


def icons():
    sq, rd, my = ('sq', LILAC, '#160F22'), ('round', '#FF3B3B', '#10060E'), ('sq', '#B473FF', '#0D0716')
    for name, fn, fr in (('mirror_images', icon_mirror_images, sq), ('false_step', icon_false_step, sq), ('veil', icon_veil, sq),
                         ('phantom_pain', icon_phantom_pain, sq), ('borrowed_face', icon_borrowed_face, sq),
                         ('mirror_labyrinth', icon_labyrinth, rd), ('waking_nightmare', icon_nightmare, rd),
                         ('butterfly_dream', icon_butterfly, my)):
        _icon(16, fn, 'textures/gui/spell_icons/%s.png' % name, frame=fr)
    for kind in ('phantom_pain', 'waking_nightmare', 'butterfly_dream', 'borrowed_face', 'mirror_images'):
        _icon(18, lambda d, S, k=kind: effect_icon(d, S, k), 'textures/mob_effect/%s.png' % kind, crisp=True)
    _icon(16, school_icon, 'textures/gui/school/illusion.png', crisp=True)
    _icon(16, prism_icon, 'textures/item/illusion_prism.png', crisp=True)
    write('models/item/illusion_prism.json', {'parent': 'item/generated', 'textures': {'layer0': 'pohsmp_core:item/illusion_prism'}})


if __name__ == '__main__':
    textures()
    style()
    school_sigils()
    spell_sigils()
    school_fx()
    spell_fx()
    dream_textures()
    meshes()
    import gen_celestial_butterfly      # «Сон бабочки» — Небесная бабочка: каст, мир сна, пробуждение, кокон, следы
    gen_celestial_butterfly.write_all()
    WRITTEN += gen_celestial_butterfly.WRITTEN
    icons()
    if '--sheet' in sys.argv:
        sheet(sys.argv[sys.argv.index('--sheet') + 1] if len(sys.argv) > sys.argv.index('--sheet') + 1 else 'illusion_sheet.png')
    print('\n'.join(WRITTEN))
