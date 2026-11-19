#!/usr/bin/env python3
"""
T25 — визуальная часть школы «Кошмары» (pohsmp_core:nightmare). ТЗ: docs/specs/tasks/T25_nightmare_school.md.
Свитки — tools/gen_nightmare_scrolls.py (не здесь). Анимации игрока — tools/gen_player_anims.py (раздел T25).
Бестиарий (модели GeckoLib, текстуры, анимации чудовищ) — tools/gen_nightmare_bestiary.py (вызывается отсюда; каркас tools/nightmare_geo.py),
превью — tools/nightmare_bestiary_preview.html (собирает tools/render_bestiary.py --html).

Палитра школы: чернильно-чёрный #0A0610, багрово-фиолетовый #7A1040, болезненно-бледный #E8E0D8; кровь #B01A4A.
Характер: края «текут» чернилами, всё капает вниз; мотивы — сломанная колыбельная (гребёнка музыкальной шкатулки, ноты),
глаза, зубы, руки, двери, луна. Правило владельца: никаких лучей / нитей от заклинателя к цели (docs/inbox/README.md).

Пишет (src/main/resources/assets/pohsmp_core/):
  textures/sigil/  nightmare_seal, nightmare_core, nightmare_crown, school_nightmare_band   — тема школы (как T06)
                   nightmare_house, nightmare_moon, nightmare_abyss, nightmare_eye, nightmare_hands_ring — печати заклинаний и метки
                   nightmare_silhouette_0..2 (силуэты на краю зрения, квадрат 512)
                   mote_ink, mote_moth, mote_eye_n, mote_nm_ash                                — спрайты
  textures/fx/     nightmare_stage1..3 (1024, экранные накладки стадий), nightmare_shadow_reach (512, тени-руки на земле),
                   nightmare_face_overlay (128, искажённое лицо),
                   nightmare_moths_screen (1024), nightmare_ink_flood (512, тайл), nightmare_ink_screen (1024, чернила сверху),
                   nightmare_wall / _floor / _ceiling / _door / _door_open (коридор «Дома, которого нет»)
  textures/entity/nightmare/face_overlay_skin.png (64×64 по развёртке скина: искажённое лицо поверх головы игрока)
  textures/environment/nightmare_moon_phases.png (как ванильный moon_phases: 4×2 фазы, красная луна), nightmare_sky.png
  textures/block/nightmare/*.png  — подмены вида мира стадии 3 (16×16, как ванильные): гниющая трава, мёртвая листва, голая кора,
                   чёрная вода (анимированная, .mcmeta); textures/colormap/nightmare_grass.png, nightmare_foliage.png (256)
  sigils/, fx/ (school_nightmare*, nightmare_*.json), fx/styles/nightmare.json, fx/meshes/nightmare_corridor, nightmare_door,
  nightmare_branches
  textures/gui/spell_icons/<3>.png, textures/mob_effect/<статусы>.png, textures/item/broken_lullaby.png + models/item/broken_lullaby.json,
  textures/gui/school/nightmare.png; lang ru_ru / en_us (ключи T25)
Время — тики, углы — градусы, размеры — блоки.  Запуск:  python3 tools/gen_nightmare_fx.py [--no-beasts] [--sheet]
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
from gen_school_themes import Pen, TAU, bez, local, jag, eye, ticks, dots  # noqa: E402

A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
OUT_SIGIL = os.path.join(A, 'textures', 'sigil')
OUT_FX = os.path.join(A, 'textures', 'fx')
WRITTEN = []

# ------------------------------------------------------------------ палитра школы
INK, CRIMSON, PALE, BLOOD, VIOLET = '#0A0610', '#7A1040', '#E8E0D8', '#B01A4A', '#4A2448'
SHADOW = '#1A0A16'
GLOWRED = '#E0285A'          # «свет» школы на печатях: багрово-алый (на тёмном фоне)
BONE = '#D8CCB8'
GEN = 'Сгенерировано tools/gen_nightmare_fx.py.'


def save_sigil(p, name, glow=0.5, glow_r=3.0):
    a = gst.save_sigil(p, name, glow, glow_r)
    WRITTEN.append('textures/sigil/%s.png' % name)
    return a


def _hex(h):
    return np.array([int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)], np.float32)


def _save(arr, rel):
    path = os.path.join(A, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA' if arr.shape[-1] == 4 else 'RGB')
    im.save(path, optimize=True)
    WRITTEN.append(rel)
    return im


# ------------------------------------------------------------------ тайлящийся шум (решётка по модулю)
def tnoise(S, cells, seed, H=None):
    H = H or S
    rng = np.random.default_rng(seed)
    cy = max(1, int(round(cells * H / S)))
    g = rng.random((cy, cells)).astype(np.float32)
    y, x = np.mgrid[0:H, 0:S].astype(np.float32)
    fx, fy = x / S * cells, y / H * cy
    ix, iy = np.floor(fx).astype(int), np.floor(fy).astype(int)
    tx, ty = fx - ix, fy - iy
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a = g[iy % cy, ix % cells]
    b = g[iy % cy, (ix + 1) % cells]
    c = g[(iy + 1) % cy, ix % cells]
    d = g[(iy + 1) % cy, (ix + 1) % cells]
    return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty


def tfbm(S, cells, seed, oct=4, H=None):
    s, a, tot = 0, 1.0, 0
    for k in range(oct):
        s = s + a * tnoise(S, cells * 2 ** k, seed + k * 31, H)
        tot += a
        a *= 0.5
    return s / tot


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ================================================================== мотивы для печатей
def drip_ring(p, r, n, rng, lmin=8, lmax=40, w=7):
    """Кольцо, с которого внутрь (к центру) стекают капли чернил: капля — сужающийся штрих с круглой каплей на конце."""
    p.ring(r, 3.2)
    for i in range(n):
        a = TAU * i / n + rng.uniform(-0.04, 0.04)
        L = rng.uniform(lmin, lmax)
        ww = w * rng.uniform(0.6, 1.1)
        pts = [p.P(r - k * L / 10, a + 0.01 * math.sin(k)) for k in range(11)]
        p.taper(pts, [ww * (1 - 0.65 * k / 10) for k in range(11)])
        x, y = p.P(r - L - ww * 0.3, a)
        p.dot(x, y, ww * 0.55)


def note(p, x, y, s, ang=0.0, broken=False, fill=255):
    """Нота-восьмая: головка, штиль, флажок; broken — штиль переломлен."""
    pts = local((x, y), ang, [(0, 0)])
    hx, hy = pts[0]
    p.poly(local((hx, hy), ang - 0.4, [(-s * 0.55 * math.cos(t), s * 0.38 * math.sin(t)) for t in np.linspace(0, TAU, 20)]), fill)
    top = local((x, y), ang, [(s * 0.48, 0), (s * 0.48, -s * 2.6)])
    if broken:
        mid = local((x, y), ang, [(s * 0.48, -s * 1.3), (s * 0.9, -s * 2.2)])
        p.line([top[0], mid[0]], s * 0.16, fill)
        p.line([mid[0], mid[1]], s * 0.16, fill)
        return
    p.line(top, s * 0.16, fill)
    p.line(local((x, y), ang, [(s * 0.48, -s * 2.6), (s * 1.3, -s * 1.8), (s * 1.1, -s * 1.3)]), s * 0.14, fill)


def comb(p, cx, cy, w, h, n, ang=0.0, broken=(), fill=255):
    """Гребёнка музыкальной шкатулки: планка и n язычков разной длины; broken — номера сломанных (короче, с зубцом)."""
    p.poly(local((cx, cy), ang, [(-w / 2, 0), (w / 2, 0), (w / 2, h * 0.16), (-w / 2, h * 0.16)]), fill)
    for k in range(n):
        x = -w / 2 + w * (k + 0.5) / n
        L = h * (0.45 + 0.55 * (1 - k / (n - 1)))
        if k in broken:
            L *= 0.45
        q = local((cx, cy), ang, [(x, h * 0.16), (x, h * 0.16 + L)])
        p.line(q, w / n * 0.5, fill, caps=False)
        if k in broken:
            e = local((cx, cy), ang, [(x - w / n * 0.25, h * 0.16 + L), (x, h * 0.16 + L + w / n * 0.5), (x + w / n * 0.25, h * 0.16 + L)])
            p.poly(e, fill)


def closed_eye(p, x, y, w, ang=0.0, lw=2.0, tear=0.0):
    """Закрытый глаз-дуга с ресницами вниз; tear — длина чернильной слезы."""
    pts = local((x, y), ang, [(-w + 2 * w * i / 20, w * 0.35 * math.sin(math.pi * i / 20)) for i in range(21)])
    p.line(pts, lw)
    for k in range(5):
        t = (k + 1) / 6
        px_, py_ = -w + 2 * w * t, w * 0.35 * math.sin(math.pi * t)
        p.line(local((x, y), ang, [(px_, py_), (px_ * 1.15, py_ + w * 0.35)]), lw * 0.7)
    if tear:
        q = local((x, y), ang, [(w * 0.1, w * 0.4), (w * 0.12, w * 0.4 + tear)])
        p.taper([q[0], q[1]], [lw * 1.4, lw * 0.6])
        p.dot(q[1][0], q[1][1], lw * 1.1)


def hand_sil(p, x, y, s, ang, fingers=5, fill=255):
    """Тонкая рука-силуэт (ладонь + длинные пальцы), растёт вдоль ang."""
    pts = local((x, y), ang, [(0, -s * 0.12), (s * 0.55, -s * 0.2), (s * 0.55, s * 0.2), (0, s * 0.12)])
    p.poly(pts, fill)
    for k in range(fingers):
        f = (k - (fingers - 1) / 2) / ((fingers - 1) / 2)
        a2 = f * 0.35
        b = local((x, y), ang, [(s * 0.52, f * s * 0.17)])[0]
        L = s * (0.65 - 0.15 * abs(f)) if k else s * 0.4
        seg = [b]
        for j in range(1, 4):
            seg.append((seg[-1][0] + math.cos(ang + a2 + 0.25 * j * (1 if f >= 0 else -1) * 0.5) * L / 3,
                        seg[-1][1] + math.sin(ang + a2 + 0.25 * j * (1 if f >= 0 else -1) * 0.5) * L / 3))
        p.taper(seg, [s * 0.075, s * 0.06, s * 0.05, s * 0.025])


def tooth_ring(p, r, n, L, w, inward=True, fill=255):
    for i in range(n):
        a = TAU * i / n
        a0, a1 = a - TAU / n * 0.4, a + TAU / n * 0.4
        tip = p.P(r - L if inward else r + L, a)
        p.poly([p.P(r, a0), p.P(r, a1), tip], fill)


# ================================================================== тема школы (как T06): печать, ядро, венец, полоса
def nightmare_seal(p):
    """Печать школы: внешнее кольцо со стекающими внутрь каплями, венок из 8 глаз (4 закрыты и плачут, 4 открыты),
    сломанная гребёнка шкатулки дугой, ноты (две с переломленными штилями), трещины, внутреннее кольцо зубов; ядро — луна-колыбель."""
    rng = random.Random(2501)
    p.ring(244, 5)
    p.ring(236, 1.6)
    drip_ring(p, 222, 46, rng, 6, 34, 6)
    for i in range(8):
        a = TAU * i / 8 - math.pi / 2
        x, y = p.P(160, a)
        if i % 2 == 0:
            eye(p, x, y, 26, 13, a + math.pi / 2, 2.8, slit=True, iris=0.36, lashes=5)
        else:
            closed_eye(p, x, y, 22, a + math.pi / 2, 2.6, tear=26)
    for i in range(8):                                             # гребёнка дугами между глазами
        a = TAU * (i + 0.5) / 8 - math.pi / 2
        x, y = p.P(186, a)
        comb(p, x, y, 46, 30, 7, a + math.pi / 2 + math.pi, broken=(1, 4) if i % 3 == 0 else (5,))
    for i in range(6):
        a = TAU * i / 6 + 0.3
        x, y = p.P(118, a)
        note(p, x, y, 9, a + math.pi / 2, broken=(i % 3 == 1))
    p.ring(98, 3)
    tooth_ring(p, 98, 30, 14, 3, inward=True)
    p.ring(70, 2)
    for _ in range(7):                                             # трещины по печати
        a = rng.uniform(0, TAU)
        r0 = rng.uniform(80, 150)
        pts = jag(rng, p.P(r0, a), p.P(r0 + rng.uniform(40, 90), a + rng.uniform(-0.25, 0.25)), 3, 0.25)
        p.taper(pts, [3.2 - 2.4 * k / (len(pts) - 1) for k in range(len(pts))])


def nightmare_core(p):
    """Ядро: месяц-колыбель (рогами вверх), над ним открытое око со щелью, из ока — чернильная слеза в колыбель."""
    c = p.cx
    p.poly([(c + 82 * math.cos(t), c + 10 + 82 * math.sin(t)) for t in np.linspace(0.15, math.pi - 0.15, 40)]
           + [(c + 76 * math.cos(t), c - 12 + 72 * math.sin(t)) for t in np.linspace(math.pi - 0.2, 0.2, 40)])
    eye(p, c, c - 40, 42, 20, 0, 4.0, slit=True, iris=0.4, lashes=6)
    p.taper([(c + 2, c - 18), (c + 3, c + 4), (c + 1, c + 22)], [7, 5, 3])
    p.dot(c + 1, c + 26, 6)
    for k in range(3):
        y = c + 56 + k * 12
        p.line([(c - 30 + k * 10, y), (c + 30 - k * 10, y)], 2.4)


def nightmare_crown(p):
    """Венец (над головой мага, Мифическая/Божественная): колючий обруч из язычков гребёнки и зубов, на каждом третьем — глаз."""
    rng = random.Random(2502)
    p.ring(150, 6)
    p.ring(126, 2.5)
    for i in range(24):
        a = TAU * i / 24
        L = 70 if i % 3 == 0 else rng.uniform(36, 56)
        b0, b1 = p.P(150, a - 0.06), p.P(150, a + 0.06)
        tip = p.P(150 + L, a + rng.uniform(-0.05, 0.05))
        p.poly([b0, b1, tip])
        if i % 3 == 0:
            x, y = p.P(150 + L + 18, a)
            eye(p, x, y, 13, 7, a + math.pi / 2, 2.2, slit=True, iris=0.4)
    for i in range(12):
        x, y = p.P(104, TAU * i / 12)
        p.dot(x, y, 5)
    tooth_ring(p, 126, 24, 18, 3, inward=True)


def nightmare_band(p):
    """Полоса рун школы (512×64, повтор): ноты, глаза, зубцы и капли, стекающие вниз."""
    W, H = p.w, p.h
    p.line([(0, 8), (W, 8)], 3, caps=False)
    p.line([(0, H - 10), (W, H - 10)], 2, caps=False)
    rng = random.Random(2503)
    for k in range(8):
        x = W * (k + 0.5) / 8
        if k % 4 == 0:
            eye(p, x, H * 0.45, 20, 10, 0, 2.4, slit=True, iris=0.38)
        elif k % 4 == 2:
            closed_eye(p, x, H * 0.38, 18, 0, 2.4, tear=12)
        else:
            note(p, x - 6, H * 0.62, 8, 0, broken=(k % 4 == 3))
    for k in range(32):
        x = W * (k + 0.5) / 32
        L = rng.uniform(4, 16)
        p.taper([(x, 9), (x, 9 + L)], [4, 1.5])
        p.dot(x, 9 + L, 2.2)


# ================================================================== печати заклинаний
def nightmare_house(p):
    """«Дом, которого нет»: коридор в перспективе — 7 вложенных дверных проёмов, сходящихся к точке; двери по бокам приоткрыты,
    из щелей тянутся руки; по кругу — обои-узор и капли."""
    rng = random.Random(2504)
    c = p.cx
    p.ring(238, 4)
    drip_ring(p, 226, 36, rng, 6, 26, 5)
    for k in range(7):
        s = 0.92 * (0.72 ** k)
        w, h = 190 * s, 210 * s
        p.line([(c - w / 2, c + h / 2), (c - w / 2, c - h / 2 + w * 0.25), (c, c - h / 2 - w * 0.05), (c + w / 2, c - h / 2 + w * 0.25),
                (c + w / 2, c + h / 2)], 4.2 - k * 0.45, caps=False)
    for k in range(6):                                              # рёбра коридора: пол и потолок сходятся
        s0, s1 = 0.92 * (0.72 ** k), 0.92 * (0.72 ** (k + 1))
        for sx in (-1, 1):
            p.line([(c + sx * 95 * s0, c + 105 * s0), (c + sx * 95 * s1, c + 105 * s1)], 1.6, caps=False)
    for k in (1, 2, 3):                                             # двери по стенам, приоткрыты, щель тёмная
        s = 0.92 * (0.72 ** k)
        for sx in (-1, 1):
            x0 = c + sx * 95 * s * 1.15
            p.line([(x0, c + 100 * s), (x0, c - 50 * s), (x0 + sx * 22 * s, c - 44 * s), (x0 + sx * 22 * s, c + 96 * s)], 2.6, caps=False)
            if k == 1:
                hand_sil(p, x0 + sx * 6 * s, c + 10 * s, 50 * s, math.pi if sx > 0 else 0)
    for i in range(10):
        a = TAU * i / 10
        x, y = p.P(200, a)
        note(p, x, y, 7, a + math.pi / 2, broken=i % 2 == 0)


def nightmare_moon(p):
    """«Ночь без рассвета»: огромная луна в кольце, с её нижнего края стекают кровавые капли; по ободу — 12 фаз луны,
    из которых одна — «съеденная» (затмение); узор из звёзд-глаз."""
    rng = random.Random(2505)
    c = p.cx
    p.ring(244, 4)
    p.ring(232, 1.5)
    for i in range(12):
        a = TAU * i / 12 - math.pi / 2
        x, y = p.P(206, a)
        ph = i / 12
        p.circle(x, y, 13, 2.2)
        if i == 6:
            p.dot(x, y, 13)
        else:
            sh = (ph - 0.5) * 2
            p.poly([(x + 13 * math.cos(t), y + 13 * math.sin(t)) for t in np.linspace(-math.pi / 2, math.pi / 2, 16)]
                   + [(x + 13 * sh * math.cos(t), y + 13 * math.sin(t)) for t in np.linspace(math.pi / 2, -math.pi / 2, 16)])
    p.ring(176, 3)
    p.circle(c, c, 120, 5)
    p.circle(c, c, 112, 1.6)
    for _ in range(14):                                             # пятна-«моря» луны
        a, r = rng.uniform(0, TAU), rng.uniform(0, 80)
        x, y = c + r * math.cos(a), c + r * math.sin(a)
        p.circle(x, y, rng.uniform(8, 22), 2)
    for i in range(13):                                             # кровь стекает с нижней дуги
        a = math.pi * (0.15 + 0.7 * i / 12)
        x, y = c + 120 * math.cos(a), c + 120 * math.sin(a)
        L = rng.uniform(16, 60) * math.sin(a) + 6
        p.taper([(x, y), (x + 0.5, y + L * 0.6), (x, y + L)], [8, 5, 2.4])
        p.dot(x, y + L + 2, 4.4)
    for i in range(16):
        x, y = p.P(150, TAU * i / 16 + 0.1)
        gst.star4(p, x, y, 5 if i % 2 else 8, 0.0, 0.25)


def nightmare_abyss(p):
    """«Пробуждение не наступит» (мифическая): закрытые глаза спиралью к центру, руки тянутся из обода внутрь, циферблат без
    стрелок (время остановилось — 12 меток, все надломлены), внутри — колыбель-месяц и капля; толстое чернильное кольцо."""
    rng = random.Random(2506)
    c = p.cx
    p.ring(246, 6)
    p.ring(236, 2)
    drip_ring(p, 226, 60, rng, 8, 44, 6)
    for i in range(12):
        a = TAU * i / 12 + 0.13
        hand_sil(p, *p.P(222, a), 70, a + math.pi + rng.uniform(-0.15, 0.15))
    for i in range(12):                                             # надломленные метки часов
        a = TAU * i / 12
        p0, p1 = p.P(140, a), p.P(118, a)
        mid = p.P(129, a + 0.03)
        p.line([p0, mid], 5, caps=False)
        p.line([p.P(127, a - 0.02), p1], 5, caps=False)
    for k in range(26):                                             # спираль закрытых глаз
        t = k / 26
        a = t * TAU * 1.6
        r = 104 - 70 * t
        x, y = c + r * math.cos(a), c + r * math.sin(a)
        closed_eye(p, x, y, 11 - 6 * t, a + math.pi / 2, 1.8 - 0.8 * t, tear=10 - 6 * t)
    p.poly([(c + 26 * math.cos(t), c + 4 + 26 * math.sin(t)) for t in np.linspace(0.2, math.pi - 0.2, 24)]
           + [(c + 18 * math.cos(t) - 2, c + 18 * math.sin(t)) for t in np.linspace(math.pi - 0.25, 0.25, 24)])


def nightmare_eye_mark(p):
    """Метка над жертвой (и для статуса): широко открытое око с узким зрачком; три слезы стекают; ресницы-шипы."""
    c = p.cx
    eye(p, c, c - 16, 150, 74, 0, 9, slit=True, iris=0.42, lashes=9)
    for k, dx in enumerate((-50, 0, 46)):
        L = (90, 140, 70)[k]
        p.taper([(c + dx, c + 50), (c + dx + 3, c + 50 + L * 0.6), (c + dx, c + 50 + L)], [16, 10, 5])
        p.dot(c + dx, c + 54 + L, 9)
    p.ring(236, 6)


def nightmare_hands_ring(p):
    """Кольцо рук на земле (руки из земли / «Ночь» — тени тянутся к центру): 18 рук к центру, рваный край."""
    rng = random.Random(2507)
    for i in range(18):
        a = TAU * i / 18 + rng.uniform(-0.08, 0.08)
        L = rng.uniform(90, 140)
        hand_sil(p, *p.P(240, a), L, a + math.pi + rng.uniform(-0.2, 0.2))
    p.ring(244, 5)


# ================================================================== спрайты
def mote_ink(p):
    """Капля чернил (64): вытянутая, с бликом-вырезом."""
    c = p.cx
    p.poly([(c + 18 * math.sin(t) * (1 - 0.0 * t), c + 6 - 26 * math.cos(t)) for t in np.linspace(-math.pi, math.pi, 40)])
    p.taper([(c, c - 26), (c, c - 6)], [2, 14])
    p.dot(c - 6, c + 2, 4, 0)


def mote_moth(p):
    """Мотылёк анфас (64): крылья с глазами-кругами (вырезы), тело."""
    c = p.cx
    for sx in (-1, 1):
        p.poly([(c + sx * (4 + 24 * math.sin(t) ** 0.8), c - 18 * math.cos(t) - 2) for t in np.linspace(0.05, math.pi - 0.05, 20)] + [(c + sx * 3, c + 10)])
        p.poly([(c + sx * (3 + 14 * math.sin(t)), c + 6 + 12 * (1 - math.cos(t))) for t in np.linspace(0.1, math.pi - 0.1, 16)])
        p.dot(c + sx * 15, c - 4, 6.5, 0)
        p.dot(c + sx * 15, c - 4, 3.2, 255)
        p.dot(c + sx * 15, c - 4, 1.4, 0)
    p.line([(c, c - 16), (c, c + 18)], 4)
    p.line([(c, c - 16), (c - 8, c - 26)], 1.5)
    p.line([(c, c - 16), (c + 8, c - 26)], 1.5)


def mote_eye_n(p):
    """Глазок-искра (64): миндаль, зрачок-щель."""
    eye(p, p.cx, p.cy, 26, 13, 0, 3, slit=True, iris=0.45)


def mote_nm_ash(p):
    """Пепел/хлопья тьмы (64): рваный лоскут."""
    rng = random.Random(9)
    c = p.cx
    pts = [(c + (14 + rng.uniform(-6, 6)) * math.cos(t), c + (10 + rng.uniform(-5, 5)) * math.sin(t)) for t in np.linspace(0, TAU, 14, endpoint=False)]
    p.poly(pts)


def sigil_textures():
    jobs = [('nightmare_seal', nightmare_seal, 512, 512, 1.0, 0.5), ('nightmare_core', nightmare_core, 512, 512, gst.CORE_ZOOM, 0.5),
            ('nightmare_crown', nightmare_crown, 512, 512, 1.0, 0.5), ('school_nightmare_band', nightmare_band, 512, 64, 1.0, 0.4),
            ('nightmare_house', nightmare_house, 512, 512, 1.0, 0.5), ('nightmare_moon', nightmare_moon, 512, 512, 1.0, 0.5),
            ('nightmare_abyss', nightmare_abyss, 512, 512, 1.0, 0.5), ('nightmare_eye', nightmare_eye_mark, 512, 512, 1.0, 0.5),
            ('nightmare_hands_ring', nightmare_hands_ring, 512, 512, 1.0, 0.4),
            ('mote_ink', mote_ink, 64, 64, 1.0, 0.3), ('mote_moth', mote_moth, 64, 64, 1.0, 0.3), ('mote_eye_n', mote_eye_n, 64, 64, 1.0, 0.3),
            ('mote_nm_ash', mote_nm_ash, 64, 64, 1.0, 0.2)]
    for name, fn, w, h, zoom, gl in jobs:
        p = Pen(w, h, zoom)
        fn(p)
        save_sigil(p, name, gl, 3.0 if w > 100 else 1.5)


# ================================================================== экранные накладки и fx-текстуры (RGBA)
def _ink_edge_mask(S, seed, depth, drips=0, drip_len=0.35, fingers=0):
    """Маска тьмы, наползающей с краёв экрана: рваная кромка + капли сверху + «пальцы» теней с углов."""
    y, x = np.mgrid[0:S, 0:S].astype(np.float32) / S
    n = tfbm(S, 6, seed, 4)
    d = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    m = sstep(depth + 0.06, depth - 0.06, d + (n - 0.5) * 0.12)
    out = m
    rng = np.random.default_rng(seed)
    for _ in range(drips):                                       # потёки от верхнего края
        cx_ = rng.random()
        L = depth + rng.random() * drip_len
        w = 0.004 + rng.random() * 0.01
        wob = 0.006 * np.sin(y * 40 + rng.random() * 6)
        col = np.abs(x - cx_ - wob) < w * (1.4 - y / max(L, 1e-3) * 0.8)
        bulb = np.hypot(x - cx_, (y - L) * 0.8) < w * 1.8
        out = np.maximum(out, ((col & (y < L)) | bulb).astype(np.float32))
    for k in range(fingers):                                     # пальцы-тени тянутся от краёв к центру
        side = k % 4
        t0 = 0.15 + 0.7 * rng.random()
        L = 0.12 + 0.22 * rng.random()
        if side == 0:
            u, v = x, y
        elif side == 1:
            u, v = 1 - x, y
        elif side == 2:
            u, v = y, x
        else:
            u, v = 1 - y, x
        wob = 0.02 * np.sin(u * 30 + k)
        w = 0.012 * (1 - u / L)
        f = (u < L) & (np.abs(v - t0 - wob - u * 0.3 * (rng.random() - 0.5)) < np.maximum(w, 0))
        out = np.maximum(out, f.astype(np.float32))
    return np.clip(out, 0, 1)


def stage_overlays():
    """Экранные накладки стадий Погружения (1024, RGBA; рисовать поверх экрана, растянуть на весь экран, альфа как есть):
    1 — тьма по краям с пальцами теней; 2 — гуще, по краям проступают вены; 3 — тяжёлые чернила, текут сверху, багровый отлив."""
    S = 1024
    y, x = np.mgrid[0:S, 0:S].astype(np.float32) / S
    vein = tfbm(S, 10, 77, 4)
    ridge = 1 - np.abs(vein - 0.5) * 2
    for st, depth, drips, fingers, red in ((1, 0.07, 0, 14, 0.0), (2, 0.11, 10, 22, 0.15), (3, 0.16, 46, 30, 0.35)):
        m = _ink_edge_mask(S, 2500 + st, depth, drips, 0.3 + 0.15 * st, fingers)
        d = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
        halo = sstep(depth * 2.6, 0.0, d) * (0.35 + 0.12 * st)
        a = np.maximum(m, halo)
        col = np.zeros((S, S, 3), np.float32) + _hex(INK)
        if st >= 2:
            v = sstep(0.93, 0.985, ridge) * sstep(depth * 3.2, depth * 0.8, d)
            col = col * (1 - v[..., None]) + _hex(CRIMSON) * v[..., None]
            a = np.maximum(a, v * 0.85)
        col = col + _hex(CRIMSON) * (red * halo)[..., None] * 0.6
        _save(np.dstack([col, a * 255]), 'textures/fx/nightmare_stage%d.png' % st)


def shadow_reach():
    """Тени-руки на земле (512, RGBA, тёмное; decal translucent): 9 вытянутых теней с длинными пальцами тянутся от края к центру,
    центр пуст (там стоит жертва). Вращать медленно и «дышать» масштабом — тени шевелятся."""
    S = 512
    p = Pen(S, S)
    rng = random.Random(2511)
    for i in range(9):
        a = TAU * i / 9 + rng.uniform(-0.15, 0.15)
        L = rng.uniform(150, 210)
        x0, y0 = p.P(256, a)
        # «рука» — вытянутое предплечье + кисть
        pts = [p.P(256 - k * L / 12, a + 0.05 * math.sin(k * 0.8 + i)) for k in range(13)]
        p.taper(pts, [26 - 12 * k / 12 for k in range(13)])
        hand_sil(p, *pts[-1], 70, a + math.pi + rng.uniform(-0.2, 0.2))
    alpha = np.asarray(p.img.resize((S, S), Image.LANCZOS).filter(ImageFilter.GaussianBlur(3.5)), np.float32)
    n = tfbm(S, 8, 2512, 3)
    alpha = alpha * (0.7 + 0.3 * n)
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    r = np.hypot(x - S / 2, y - S / 2) / (S / 2)
    alpha = alpha * sstep(1.0, 0.85, r) * 0.92
    col = np.zeros((S, S, 3), np.float32) + _hex('#050208')
    _save(np.dstack([col, alpha]), 'textures/fx/nightmare_shadow_reach.png')


def silhouettes():
    """Силуэты на краю зрения (textures/sigil, 512×512, белое + альфа; тонировать тёмным — спрайт рисуется translucent): 0 — высокий худой без лица, 1 — ребёнок с волосами, 2 — сгорбленный с длинными руками.
    Чёрные, края размыты — для мелькания billboard-спрайтом 2–6 тиков."""
    W, H = 256, 512
    for k in range(3):
        im = Image.new('L', (W * 2, H * 2), 0)
        d = ImageDraw.Draw(im)
        S = 2
        if k == 0:
            d.ellipse([W - 30 * S, 30 * S, W + 30 * S, 120 * S], fill=255)
            d.polygon([(W - 18 * S, 110 * S), (W + 18 * S, 110 * S), (W + 46 * S, 150 * S), (W + 40 * S, 300 * S), (W + 22 * S, 300 * S),
                       (W + 24 * S, 500 * S), (W + 8 * S, 500 * S), (W, 320 * S), (W - 8 * S, 500 * S), (W - 24 * S, 500 * S), (W - 22 * S, 300 * S),
                       (W - 40 * S, 300 * S), (W - 46 * S, 150 * S)], fill=255)
            for sx in (-1, 1):
                d.line([(W + sx * 44 * S, 150 * S), (W + sx * 60 * S, 330 * S), (W + sx * 56 * S, 470 * S)], fill=255, width=12 * S)
                for f in range(4):
                    d.line([(W + sx * 56 * S, 470 * S), (W + sx * (50 + f * 5) * S, 505 * S)], fill=255, width=3 * S)
        elif k == 1:
            d.ellipse([W - 44 * S, 230 * S, W + 44 * S, 320 * S], fill=255)
            d.polygon([(W - 50 * S, 260 * S), (W + 50 * S, 260 * S), (W + 52 * S, 380 * S), (W - 52 * S, 380 * S)], fill=255)
            d.polygon([(W - 30 * S, 320 * S), (W + 30 * S, 320 * S), (W + 70 * S, 470 * S), (W - 70 * S, 470 * S)], fill=255)
            for sx in (-1, 1):
                d.line([(W + sx * 14 * S, 470 * S), (W + sx * 16 * S, 508 * S)], fill=255, width=9 * S)
                d.line([(W + sx * 36 * S, 335 * S), (W + sx * 44 * S, 420 * S)], fill=255, width=8 * S)
        else:
            d.ellipse([W + 10 * S, 170 * S, W + 66 * S, 236 * S], fill=255)
            d.polygon([(W - 40 * S, 200 * S), (W + 30 * S, 190 * S), (W + 40 * S, 300 * S), (W - 30 * S, 330 * S)], fill=255)
            d.line([(W - 20 * S, 320 * S), (W - 30 * S, 420 * S), (W - 20 * S, 508 * S)], fill=255, width=14 * S)
            d.line([(W + 20 * S, 310 * S), (W + 30 * S, 420 * S), (W + 34 * S, 508 * S)], fill=255, width=14 * S)
            for sx in (-1, 1):
                d.line([(W + sx * 30 * S + 10 * S, 215 * S), (W + sx * 50 * S + 20 * S, 360 * S), (W + sx * 44 * S + 20 * S, 470 * S)], fill=255, width=10 * S)
        im = im.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2.2))
        a = np.asarray(im, np.float32)
        n = tnoise(W, 8, 2520 + k, H)
        a = a * (0.85 + 0.15 * n)
        sq = np.zeros((H, H), np.float32)                      # квадрат 512 (фигура по центру): спрайт/печать квадратные
        sq[:, (H - W) // 2:(H + W) // 2] = a
        _save(np.dstack([np.full((H, H, 3), 255.0), sq]), 'textures/sigil/nightmare_silhouette_%d.png' % k)


def face_overlays():
    """Искажённые лица стадии 3.
    face_overlay_skin.png (64×64, развёртка скина): на передней грани головы (8,8)-(16,16) и слое шляпы (40,8)-(48,16) — чёрные
    провалы глаз со слезами-потёками, рот растянут до ушей; код рисует его вторым слоем поверх головы игрока (и мобов-гуманоидов).
    nightmare_face_overlay.png (128, RGBA) — то же для любых лиц декалью/billboard (мобы с нестандартной головой)."""
    # 128 — общий: провалы глаз оплывают вниз, рот разодран в беззвучном крике (вытянут вниз), неровные зубы по краю
    S = 128
    p = Pen(S, S)
    rng = random.Random(2525)
    for sx in (-1, 1):
        p.poly([(64 + sx * 24 + 11 * math.cos(t) * (1 - 0.25 * max(0, math.sin(t))), 46 + 15 * math.sin(t) + 6 * max(0, math.sin(t)))
                for t in np.linspace(0, TAU, 40)])
        for k in range(3):
            x0 = 64 + sx * 24 + (k - 1) * 5
            L = rng.uniform(14, 34)
            p.taper([(x0, 58), (x0 + rng.uniform(-1, 1), 58 + L * 0.6), (x0, 58 + L)], [5, 3.5, 2])
            p.dot(x0, 60 + L, 2.4)
    mouth = [(64 + 17 * math.cos(t) * (1 + 0.15 * math.sin(t)), 92 + 22 * math.sin(t) + (4 if math.sin(t) > 0 else 0)) for t in np.linspace(0, TAU, 50)]
    p.poly(mouth)
    a = np.asarray(p.img.resize((S, S), Image.LANCZOS), np.float32)
    col = np.zeros((S, S, 3), np.float32) + _hex('#070205')
    yy, xx = np.mgrid[0:S, 0:S]
    teeth = np.zeros((S, S), bool)
    for k in range(-4, 5):                                   # зубы сверху и снизу, неровные
        x0 = 64 + k * 3.6
        L1, L2 = rng.uniform(3, 7), rng.uniform(3, 6)
        top = 71 + abs(k) * 0.9
        bot = 117 - abs(k) * 1.2
        teeth |= (np.abs(xx - x0) < 1.3 * (1 - (yy - top) / L1)) & (yy >= top) & (yy < top + L1)
        teeth |= (np.abs(xx - x0) < 1.3 * (1 - (bot - yy) / L2)) & (yy <= bot) & (yy > bot - L2)
    col[teeth & (a > 100)] = _hex('#CFC2A6')
    inner = (np.hypot((xx - 64) / 10, (yy - 94) / 14) < 1) & (a > 200)
    col[inner] = _hex('#3A0418')
    _save(np.dstack([col, a]), 'textures/fx/nightmare_face_overlay.png')
    # 64×64 по развёртке скина
    sk = np.zeros((64, 64, 4), np.float32)
    small = Image.fromarray(np.dstack([col, a]).astype(np.uint8), 'RGBA').resize((8, 8), Image.LANCZOS)
    f = np.asarray(small, np.float32)
    f[..., 3] = np.where(f[..., 3] > 90, 255, 0)
    sk[8:16, 8:16] = f
    sk[8:16, 40:48] = f                                  # слой шляпы — поверх объёмной головы
    _save(sk, 'textures/entity/nightmare/face_overlay_skin.png')


def moths_screen():
    """Мотыльки на экране (1024, RGBA): облепляют края (больше в углах), центр свободен; крылья с глазами."""
    S = 1024
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    src = Image.open(os.path.join(OUT_SIGIL, 'mote_moth.png'))
    m = np.asarray(src, np.float32)[..., 3]
    rng = random.Random(2530)
    for _ in range(140):
        while True:
            x, y = rng.random(), rng.random()
            d = min(x, 1 - x, y, 1 - y)
            if d < 0.2 * rng.random() ** 0.5:
                break
        s = int(rng.uniform(50, 130) * (1.2 - d * 2))
        ang = rng.uniform(0, 360)
        a = Image.fromarray(m.astype(np.uint8), 'L').resize((s, s), Image.LANCZOS).rotate(ang, expand=True)
        body = Image.new('RGBA', a.size, (52, 40, 40, 255))
        arr = np.asarray(body).copy()
        arr[..., 3] = np.asarray(a)
        # глаза на крыльях — багровые точки поверх (по маске вырезов)
        im.alpha_composite(Image.fromarray(arr, 'RGBA'), (int(x * S - a.size[0] / 2), int(y * S - a.size[1] / 2)))
    arr = np.asarray(im, np.float32)
    n = tfbm(S, 12, 2531, 3)
    arr[..., :3] = arr[..., :3] * (0.7 + 0.6 * n[..., None])
    arr[..., 0] += (n > 0.62) * 70
    _save(arr, 'textures/fx/nightmare_moths_screen.png')


def ink_textures():
    """Чернила: nightmare_ink_flood (512, тайл по обеим осям — поверхность «чернильного моря» мифического ролика: тёмная, с
    маслянистыми разводами и бликами) и nightmare_ink_screen (1024, экранная накладка — чернила стекают сверху по «стеклу»)."""
    S = 512
    n1 = tfbm(S, 4, 2540, 5)
    n2 = tfbm(S, 9, 2541, 4)
    swirl = 1 - np.abs(np.sin((n1 * 6 + n2 * 2) * math.pi))
    col = np.zeros((S, S, 3), np.float32) + _hex('#06030A')
    col += _hex('#2A1838') * (swirl ** 6)[..., None] * 0.9
    col += _hex('#7A1040') * (sstep(0.72, 0.9, n2) * 0.35)[..., None]
    col += 200 * (sstep(0.985, 1.0, swirl) * sstep(0.5, 0.7, n1))[..., None] / 255 * _hex('#B8A8D0') / 255 * 255 * 0.3
    _save(np.dstack([col, np.full((S, S), 255, np.float32)]), 'textures/fx/nightmare_ink_flood.png')
    S = 1024
    y, x = np.mgrid[0:S, 0:S].astype(np.float32) / S
    a = np.zeros((S, S), np.float32)
    rng = np.random.default_rng(2542)
    top = 0.05 + 0.08 * tnoise(S, 7, 2543)
    a = np.maximum(a, (y < top).astype(np.float32))
    for _ in range(80):
        cx_ = rng.random()
        L = 0.1 + rng.random() ** 1.6 * 0.85
        w = 0.003 + rng.random() * 0.012
        wob = 0.004 * np.sin(y * 50 + rng.random() * 6)
        col_ = np.abs(x - cx_ - wob) < w * (1.3 - 0.6 * y / L)
        bulb = np.hypot(x - cx_, (y - L) * 0.7) < w * 1.7
        a = np.maximum(a, ((col_ & (y < L)) | bulb).astype(np.float32))
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32)
    col = np.zeros((S, S, 3), np.float32) + _hex('#07030B')
    hl = sstep(0.4, 0.9, tfbm(S, 30, 2544, 2)) * (a > 200)
    col += _hex('#3A2848') * hl[..., None] * 0.6
    _save(np.dstack([col, a]), 'textures/fx/nightmare_ink_screen.png')


# ================================================================== коридор «Дома, которого нет» (тайлы по 1 блоку, 256 px)
def corridor_textures():
    """Материалы коридора (тайлятся): стена — отклеивающиеся обои с выцветшим узором (колыбельки и луны), плесень, потёки чернил,
    снизу деревянная панель; пол — тёмные доски; потолок — треснувшая штукатурка с пятнами; дверь (128×256 на 1×2 блока) — старая
    филёнчатая с латунной ручкой, из-под двери сочатся чернила; открытая дверь — чёрный проём с едва видными глазами."""
    S = 256
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    u, v = x / S, y / S
    # стена: обои
    base = _hex('#3A2A30') * (0.85 + 0.3 * tfbm(S, 6, 2550, 4))[..., None]
    stripe = (np.abs(((u * 8) % 1.0) - 0.5) < 0.06).astype(np.float32)
    base = base * (1 - 0.18 * stripe[..., None])
    p = Pen(S, S)                                    # узор: месяцы-колыбели и точки в шахматку
    for i in range(4):
        for j in range(4):
            cx_, cy_ = (i + 0.5 + 0.5 * (j % 2)) * S / 4 % S, (j + 0.5) * S / 4
            for ox in (0, -S, S):
                p.arc(16, 0.3, math.pi - 0.3, 3, cx=cx_ + ox, cy=cy_ - 6)
                p.dot(cx_ + ox, cy_ + 16, 3)
    pat = np.asarray(p.img.resize((S, S), Image.LANCZOS), np.float32) / 255
    base = base + _hex('#6A4A50') * (pat * 0.35)[..., None]
    peel = sstep(0.62, 0.66, tfbm(S, 5, 2551, 4))                     # отклеившиеся куски — под ними серая штукатурка
    base = base * (1 - peel[..., None]) + _hex('#5A5458') * (0.8 + 0.3 * tfbm(S, 16, 2552, 2))[..., None] * peel[..., None]
    edge = sstep(0.6, 0.62, tfbm(S, 5, 2551, 4)) - peel
    base = base + _hex('#C8B8A8') * (np.clip(edge, 0, 1) * 0.4)[..., None]
    mold = sstep(0.68, 0.85, tfbm(S, 10, 2553, 4)) * sstep(0.3, 1.0, v)
    base = base * (1 - 0.55 * mold[..., None]) + _hex('#1A2418') * (0.55 * mold)[..., None]
    # потёки чернил сверху вниз (тайл по x, по y — от верхнего края блока)
    rng = np.random.default_rng(2554)
    drip = np.zeros((S, S), np.float32)
    for _ in range(9):
        cx_ = rng.random()
        L = 0.2 + rng.random() * 0.75
        w = 0.008 + rng.random() * 0.014
        wob = 0.006 * np.sin(v * 30 + rng.random() * 6)
        dx = np.minimum(np.abs(u - cx_ - wob), 1 - np.abs(u - cx_ - wob))
        drip = np.maximum(drip, ((dx < w * (1.4 - v / L)) & (v < L)).astype(np.float32))
    base = base * (1 - drip[..., None]) + _hex('#06030A') * drip[..., None]
    _save(np.dstack([base, np.full((S, S), 255.0)]), 'textures/fx/nightmare_wall.png')
    # пол: доски вдоль коридора (по v), щели, потёртость, чернильные пятна
    plank = np.floor(u * 4)
    off = (plank * 0.37) % 1.0
    g = tfbm(S, 4, 2555, 3)
    grain = 0.5 + 0.5 * np.sin((u * 4 % 1.0) * 40 + tnoise(S, 6, 2556) * 8)
    base = _hex('#2A1C16') * (0.75 + 0.25 * grain + 0.2 * g)[..., None]
    gap = (np.abs((u * 4 % 1.0) - 0.0) < 0.02) | (np.abs(((v + off) % 1.0) - 0.0) < 0.012)
    base[gap] = _hex('#080406')
    stain = sstep(0.62, 0.7, tfbm(S, 5, 2557, 4))
    base = base * (1 - stain[..., None]) + _hex('#07030A') * stain[..., None] + _hex('#3A2848') * (sstep(0.7, 0.72, tfbm(S, 5, 2557, 4)) * 0.4)[..., None]
    _save(np.dstack([base, np.full((S, S), 255.0)]), 'textures/fx/nightmare_floor.png')
    # потолок
    base = _hex('#4A4448') * (0.75 + 0.35 * tfbm(S, 6, 2558, 4))[..., None]
    cr = 1 - np.abs(tfbm(S, 7, 2559, 3) - 0.5) * 2
    base = base * (1 - 0.7 * sstep(0.95, 0.99, cr)[..., None])
    wet = sstep(0.6, 0.8, tfbm(S, 4, 2560, 3))
    base = base * (1 - 0.5 * wet[..., None]) + _hex('#2A1820') * (0.5 * wet)[..., None]
    _save(np.dstack([base, np.full((S, S), 255.0)]), 'textures/fx/nightmare_ceiling.png')
    # дверь 128×256
    W, H = 128, 256
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    g = tnoise(W, 5, 2561, H)
    grain = 0.5 + 0.5 * np.sin(y / H * 60 + tnoise(W, 4, 2562, H) * 10)
    base = _hex('#3A2418') * (0.7 + 0.2 * grain + 0.2 * g)[..., None]
    for (x0, y0, x1, y1) in ((14, 14, 114, 112), (14, 128, 114, 242)):       # филёнки
        inn = (x > x0) & (x < x1) & (y > y0) & (y < y1)
        rim = inn & ~((x > x0 + 6) & (x < x1 - 6) & (y > y0 + 6) & (y < y1 - 6))
        base[rim] *= 0.6
        base[inn & ~rim] *= 0.85
    frame = (x < 4) | (x > W - 5) | (y < 4)
    base[frame] = base[frame] * 0.5
    knob = np.hypot(x - 104, y - 132) < 7
    base[knob] = _hex('#8A7040')
    base[np.hypot(x - 102, y - 130) < 2.5] = _hex('#E0C890')
    ink = (y > H - 10 - 26 * tnoise(W, 9, 2563, H)[0:1, :]) | ((np.abs(x - 40) < 2.5) & (y > 200)) | ((np.abs(x - 90) < 2) & (y > 225))
    base = np.where(ink[..., None], _hex('#07030A'), base)
    scratch = (np.abs((x * 0.7 + y * 0.2) % 23 - 11) < 0.6) & (y > 140) & (y < 200) & (x > 30) & (x < 80)
    base[scratch] = _hex('#C8B0A0') * 0.6
    _save(np.dstack([base, np.full((H, W), 255.0)]), 'textures/fx/nightmare_door.png')
    # открытая: чёрный проём, туман внизу, два-три тусклых глаза
    base = np.zeros((H, W, 3), np.float32) + _hex('#020103')
    fog = sstep(0.6, 1.0, y / H) * (0.5 + 0.5 * tnoise(W, 6, 2564, H))
    base += _hex('#2A1838') * fog[..., None] * 0.6
    for ex, ey in ((52, 96), (76, 96), (90, 150), (99, 150)):
        e = np.hypot((x - ex) / 3.2, (y - ey) / 1.6) < 1
        base[e] = _hex('#E0285A')
    _save(np.dstack([base, np.full((H, W), 255.0)]), 'textures/fx/nightmare_door_open.png')


# ================================================================== луна, небо, подмены вида мира стадии 3
def moon_sky():
    """Красная луна: textures/environment/nightmare_moon_phases.png — та же раскладка, что ванильный moon_phases.png (4×2 фазы),
    512×256 (клетка 128); красная, с тёмными «морями», с нижнего края стекает. nightmare_sky.png (1024×512) — небо-купол:
    кроваво-чёрные рваные облака, ниже горизонта чернее (код рисует сферой/бэкдропом вместо неба у жертвы)."""
    S = 128
    out = np.zeros((256, 512, 4), np.float32)
    y, x = np.mgrid[0:S, 0:S].astype(np.float32)
    r = np.hypot(x - 64, y - 64) / 40
    seas = tfbm(S, 5, 2570, 4)
    for ph in range(8):
        col = _hex('#C8203A') * (0.75 + 0.35 * seas)[..., None]
        col = col * (1 - 0.45 * sstep(0.55, 0.7, seas)[..., None])
        col = col * (1 - 0.25 * r[..., None] ** 2)
        a = (r < 1).astype(np.float32)
        rng = np.random.default_rng(2571)
        for _ in range(6):                                     # потёки вниз
            cx_ = 64 + rng.uniform(-28, 28)
            L = rng.uniform(6, 22)
            ybot = 64 + math.sqrt(max(0, 1600 - (cx_ - 64) ** 2))
            dd = (np.abs(x - cx_) < 1.6 - (y - ybot) / L) & (y > ybot - 3) & (y < ybot + L)
            a = np.maximum(a, dd.astype(np.float32))
        # фаза: 0 полная … 4 новолуние … 7 (как у ванили): освещённость шара светом под углом φ к зрителю
        phi = math.pi * (ph if ph <= 4 else 8 - ph) / 4
        sgn = 1 if ph <= 4 else -1
        uu, vv = (x - 64) / 40, (y - 64) / 40
        ww = np.sqrt(np.clip(1 - uu ** 2 - vv ** 2, 0, 1))
        lit = uu * sgn * math.sin(phi) + ww * math.cos(phi)
        shade = sstep(-0.08, 0.08, lit)
        col = col * (0.1 + 0.9 * shade)[..., None]
        glow = sstep(1.5, 1.0, r) * (r >= 1) * 0.55
        a = np.maximum(a, glow)
        col = np.where((r >= 1)[..., None] & (a < 1)[..., None], _hex('#8A1028'), col)
        cx0, cy0 = (ph % 4) * S, (ph // 4) * S
        out[cy0:cy0 + S, cx0:cx0 + S] = np.dstack([col, a * 255])
    _save(out, 'textures/environment/nightmare_moon_phases.png')
    W, H = 1024, 512
    n = tfbm(W, 6, 2572, 5, H)
    n2 = tfbm(W, 14, 2573, 3, H)
    yy = np.mgrid[0:H, 0:W][0].astype(np.float32) / H
    col = _hex('#120408') * (1 - yy[..., None]) + _hex('#030104') * yy[..., None]
    cloud = sstep(0.45, 0.75, n) * (0.6 + 0.4 * n2)
    col = col + _hex('#5A0A1E') * (cloud * (1 - yy) * 0.9)[..., None]
    col = col + _hex('#B01A4A') * (sstep(0.7, 0.8, n) * sstep(0.85, 0.95, n2) * (1 - yy) * 0.5)[..., None]
    col = col * (1 - 0.6 * sstep(0.5, 0.9, yy))[..., None]
    _save(np.dstack([col, np.full((H, W), 255.0)]), 'textures/environment/nightmare_sky.png')


def _tile16(fn, name, frames=1):
    """Блочная текстура 16×16 (или полоса кадров 16×(16·frames) с .mcmeta)."""
    arr = np.concatenate([fn(f) for f in range(frames)], 0)
    _save(arr, 'textures/block/nightmare/%s.png' % name)
    if frames > 1:
        path = os.path.join(A, 'textures', 'block', 'nightmare', name + '.png.mcmeta')
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump({'animation': {'frametime': 3, 'interpolate': True}}, fh, indent=1)
            fh.write('\n')
        WRITTEN.append('textures/block/nightmare/%s.png.mcmeta' % name)


def world_swaps():
    """Подмены вида мира стадии 3 (только у жертвы; блоки мира не меняются). 16×16 в стиле ванили, уже окрашены
    (рисовать БЕЗ биомного оттенка); колормапы 256×256 — если проще подменять цвет травы/листвы через BlockColors."""
    rng = np.random.default_rng(2580)
    P = lambda *c: np.array(c, np.float32)

    def noise16(seed, cells=4):
        return tnoise(16, cells, seed)

    def grass_top(_):
        n = noise16(1, 8)
        c = P(74, 62, 52) * (0.75 + 0.45 * n)[..., None]
        rot = noise16(2, 4) > 0.6
        c[rot] = c[rot] * 0.6 + P(40, 28, 44) * 0.4
        c[noise16(3, 16) > 0.82] = P(110, 104, 70)               # жухлые травинки
        return np.dstack([c, np.full((16, 16), 255.0)])

    def grass_side(_):
        n = noise16(4, 8)
        c = P(92, 66, 50) * (0.7 + 0.4 * n)[..., None]          # земля
        top = 3 + (noise16(5, 16)[0] * 3).astype(int)
        for x in range(16):
            c[:top[x], x] = P(70, 58, 50) * (0.8 + 0.3 * n[:top[x], x])[..., None]
            if rng.random() < 0.3:
                c[top[x]:top[x] + 2, x] = P(20, 12, 24)          # чернила стекают с края
        return np.dstack([c, np.full((16, 16), 255.0)])

    def leaves(_):
        n = noise16(6, 8)
        c = P(58, 44, 40) * (0.7 + 0.5 * n)[..., None]
        a = (noise16(7, 8) > 0.66).astype(np.float32) * 255      # редкие мёртвые листья, остальное — прозрачно (почти голые ветки)
        twig = np.zeros((16, 16), bool)
        for k in range(3):
            x0 = rng.integers(0, 16)
            for yy in range(16):
                xx = (x0 + (yy // 3) * (1 if k % 2 else -1)) % 16
                twig[yy, xx] = rng.random() < 0.7
        c[twig] = P(28, 20, 22)
        a[twig] = 255
        return np.dstack([c, a])

    def log_side(_):
        y, x = np.mgrid[0:16, 0:16]
        n = noise16(8, 8)
        bark = 0.6 + 0.4 * np.sin(x * 1.7 + n * 3) ** 2
        c = P(46, 40, 42) * (bark * (0.8 + 0.3 * n))[..., None]
        c[(x % 5 == 2) & (noise16(9, 16) > 0.5)] = P(14, 10, 14)
        return np.dstack([c, np.full((16, 16), 255.0)])

    def water(f):
        ph = f / 32 * TAU
        y, x = np.mgrid[0:16, 0:16].astype(np.float32)
        w = 0.5 + 0.5 * np.sin(x / 16 * TAU * 2 + ph) * np.sin(y / 16 * TAU + ph * 2)
        c = P(10, 6, 16) + P(40, 24, 56) * (w ** 6)[..., None] + P(90, 20, 40) * ((w > 0.97) * 0.4)[..., None]
        return np.dstack([c, np.full((16, 16), 235.0)])

    def water_flow(f):
        ph = f / 32 * TAU
        y, x = np.mgrid[0:16, 0:16].astype(np.float32)
        w = 0.5 + 0.5 * np.sin(y / 16 * TAU * 2 - ph * 2 + np.sin(x / 16 * TAU) * 0.8)
        c = P(8, 4, 12) + P(44, 26, 60) * (w ** 5)[..., None]
        return np.dstack([c, np.full((16, 16), 235.0)])
    _tile16(grass_top, 'grass_block_top')
    _tile16(grass_side, 'grass_block_side')
    _tile16(leaves, 'leaves_dead')
    _tile16(log_side, 'log_dead')
    _tile16(water, 'water_still', 32)
    _tile16(water_flow, 'water_flow', 32)
    # колормапы (256×256, как ванильные grass.png / foliage.png): все биомы — гниль
    y, x = np.mgrid[0:256, 0:256].astype(np.float32) / 255
    for name, a, b in (('nightmare_grass', P(84, 70, 58), P(52, 40, 50)), ('nightmare_foliage', P(66, 50, 46), P(40, 30, 38))):
        c = a * (1 - y[..., None]) + b * y[..., None]
        c = c * (0.9 + 0.1 * x[..., None])
        _save(np.dstack([c, np.full((256, 256), 255.0)]), 'textures/colormap/%s.png' % name)


def textures():
    sigil_textures()
    stage_overlays()
    shadow_reach()
    silhouettes()
    face_overlays()
    moths_screen()
    ink_textures()
    corridor_textures()
    moon_sky()
    world_swaps()


# ================================================================== обзорные листы (docs/media)
def _thumb(path, size, bg=(40, 32, 44), tint=None, scale_nearest=False):
    im = Image.open(path).convert('RGBA')
    if tint:
        a = im.split()[3]
        im = Image.new('RGBA', im.size, tint + (255,))
        im.putalpha(a)
    im = im.resize(size, Image.NEAREST if scale_nearest else Image.LANCZOS)
    out = Image.new('RGBA', size, bg + (255,))
    out.alpha_composite(im)
    return out.convert('RGB')


def sheet_textures(path):
    """Лист текстур: печати (багровым на тёмном), экранные накладки (на сером фоне-«мире»), коридор, луна, небо, блоки ×8."""
    from PIL import ImageFont
    cell = 220
    items = []
    for n in ('nightmare_seal', 'nightmare_core', 'nightmare_crown', 'nightmare_house', 'nightmare_moon', 'nightmare_abyss', 'nightmare_eye',
              'nightmare_hands_ring', 'mote_ink', 'mote_moth', 'mote_eye_n', 'mote_nm_ash'):
        items.append((n, _thumb(os.path.join(OUT_SIGIL, n + '.png'), (cell, cell), (14, 8, 16), (224, 40, 90))))
    for n in ('nightmare_silhouette_0', 'nightmare_silhouette_1', 'nightmare_silhouette_2'):
        items.append((n, _thumb(os.path.join(OUT_SIGIL, n + '.png'), (cell, cell), (120, 130, 120), (4, 2, 6))))
    for n in ('nightmare_stage1', 'nightmare_stage2', 'nightmare_stage3', 'nightmare_ink_screen', 'nightmare_moths_screen', 'nightmare_shadow_reach',
              'nightmare_face_overlay'):
        items.append((n, _thumb(os.path.join(OUT_FX, n + '.png'), (cell, cell), (120, 130, 120))))
    for n in ('nightmare_wall', 'nightmare_floor', 'nightmare_ceiling', 'nightmare_door', 'nightmare_door_open', 'nightmare_ink_flood'):
        items.append((n, _thumb(os.path.join(OUT_FX, n + '.png'), (cell, cell))))
    items.append(('moon_phases', _thumb(os.path.join(A, 'textures/environment/nightmare_moon_phases.png'), (cell, cell // 2 * 2))))
    items.append(('nightmare_sky', _thumb(os.path.join(A, 'textures/environment/nightmare_sky.png'), (cell, cell))))
    for n in ('grass_block_top', 'grass_block_side', 'leaves_dead', 'log_dead', 'water_still'):
        im = Image.open(os.path.join(A, 'textures/block/nightmare', n + '.png')).crop((0, 0, 16, 16)).convert('RGBA')
        out = Image.new('RGBA', (cell, cell), (90, 110, 140, 255))
        out.alpha_composite(im.resize((cell, cell), Image.NEAREST))
        items.append((n, out.convert('RGB')))
    cols = 8
    rows = (len(items) + cols - 1) // cols
    sh = Image.new('RGB', (cols * cell, rows * (cell + 22)), (10, 6, 12))
    d = ImageDraw.Draw(sh)
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    except OSError:
        font = None
    for i, (n, im) in enumerate(items):
        x, y = (i % cols) * cell, (i // cols) * (cell + 22)
        sh.paste(im, (x, y + 22))
        d.text((x + 4, y + 4), n, fill=(232, 224, 216), font=font)
    sh.save(path, quality=88)
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


def TX(id, text, radius, size, h, appear, font='latin', color=None, br=None, rot=None, repeat=1, side='outer', **kw):
    o = L(id, 'text', None, radius, h, appear, rot=rot, color=color, br=br, **kw)
    o.update({'text': text, 'font': font, 'size': size, 'repeat': repeat, 'side': side})
    return o


def sigil(id, comment, size, color, orientation, layers, hold=-1, expand=None, flash=None, children=None,
          dissolve=('fade',), ddur=16, stagger=2, ground_light=None):
    o = {'comment': comment + ' ' + GEN, 'size': size, 'color': color, 'orientation': orientation, 'lifetime': -1, 'hold': hold, 'layers': layers}
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


def pool(r=0.95, b=1.0, dur=8, color=SHADOW, pulse=None, h=-0.01):
    """Тёмная «лужа» под печатью (disc glow тёмным цветом рисуется translucent — печать читается и днём)."""
    return L('pool', 'disc', 'glow', r, h, ap(0, dur, 'grow', 'fade'), color=color, br=b, pulse=pulse)


def bleed(tex, r=1.0, h=0.004, delay=6, dur=14, br=0.35):
    """Фирменный знак школы: та же текстура чуть больше, тёмно-багровым, «оплывает» вниз-наружу — края текут."""
    return [L('bleed', 'disc', tex, r * 1.03, h, ap(delay, dur, 'fade', 'grow', easing='easeOutSine'), rot=-1.5, color=CRIMSON, br=br,
              pulse=(0.35, 37)),
            L('smear', 'disc', tex, r * 1.075, h - 0.002, ap(delay + 4, dur + 6, 'fade', 'grow', easing='easeOutSine'), rot=1.0, color=SHADOW,
              br=0.8, pulse=(0.25, 53))]


def school_sigils():
    sigil('nightmare_seal', 'T25, школа «Кошмары», ступени Высшая/Мифическая/Божественная: печать под магом на время каста (hold −1). '
                            'Кольцо, с которого внутрь стекают капли чернил; венок из глаз (открытые и плачущие закрытые), сломанные '
                            'гребёнки музыкальной шкатулки, ноты с переломленными штилями, кольцо зубов; ядро — око над месяцем-колыбелью. '
                            'Прорисовывается от верхней точки по часовой, края оплывают багровым; распад — стекает.',
          2.4, GLOWRED, 'ground', [
              pool(1.02, 1.0, 10),
              L('seal', 'disc', 'nightmare_seal', 1.0, 0.01, ap(0, 26, 'draw', easing='easeInOutSine', startAngle=270, direction=1), rot=-5),
              *bleed('nightmare_seal', 1.0, 0.014, delay=18, dur=14),
              L('band', 'band', 'school_nightmare_band', 1.2, 0.02, ap(12, 16, 'draw', easing='easeInOutSine', startAngle=90, direction=-1),
                inner=0.89, repeat=10, color=PALE, br=0.6, rot=6, boost=2),
              L('core', 'disc', 'nightmare_core', 0.4, 0.03, ap(22, 14, 'unfold', 'fade', easing='easeOutCubic'), rot=0, color=PALE, br=0.9,
                pulse=(0.12, 24)),
          ], flash={'color': BLOOD, 'size': 1.3, 'duration': 10, 'sparks': 20}, dissolve=('reverse', 'fade'), ddur=16,
          ground_light={'radius': 0.7, 'strength': 0.35})
    sigil('nightmare_crown', 'T25, школа «Кошмары»: венец над головой мага (Мифическая/Божественная) — колючий обруч из язычков гребёнки '
                             'и зубов, на остриях — глаза; раскрывается из ребра, оплывает.', 0.75, GLOWRED, 'sky', [
        pool(0.85, 0.9, 8),
        L('crown', 'disc', 'nightmare_crown', 1.0, 0.01, ap(2, 14, 'unfold', 'fade', easing='easeOutCubic'), rot=-10, boost=2),
        *bleed('nightmare_crown', 1.0, 0.012, delay=10, dur=10),
    ], flash={'color': BLOOD, 'size': 1.3, 'duration': 8, 'sparks': 12}, dissolve=('fade', 'collapse'), ddur=12, stagger=0)
    sigil('school_nightmare', 'Знак школы «Кошмары» под магом при каждом касте (PohSpell.onCast): короткий, прорисовывается, око в ядре '
                              'открывается с доворотом, капли сбегают к центру.', 1.9, GLOWRED, 'ground', [
        pool(0.8, 1.0, 5),
        L('sign', 'disc', 'nightmare_seal', 0.9, 0.01, ap(0, 9, 'draw', startAngle=270, direction=1), rot=24, boost=3),
        L('bleed', 'disc', 'nightmare_seal', 0.94, 0.006, ap(4, 8, 'fade', 'grow'), rot=-16, color=SHADOW, br=0.8, pulse=(0.4, 9)),
        L('core', 'disc', 'nightmare_core', 0.36, 0.02, ap(3, 8, 'grow', 'twist', easing='easeOutBack', twist=150), rot=-30, boost=2, color=PALE),
        L('band', 'band', 'school_nightmare_band', 1.08, 0.03, ap(2, 9, 'draw', easing='easeInOutSine', startAngle=270, direction=-1),
          inner=0.94, repeat=8, color=PALE, br=0.6, rot=-20, boost=2),
    ], hold=12, flash={'color': BLOOD, 'size': 1.3, 'duration': 8, 'sparks': 14}, dissolve=('reverse', 'fade'), ddur=10)


def spell_sigils():
    # --- «Дом, которого нет»
    sigil('nightmare_house_ground', '«Дом, которого нет», каст (2.5 с): печать-коридор под заклинателем — проёмы прорисовываются от '
                                    'дальнего к ближнему, двери по бокам приоткрываются, из щели тянется рука.', 3.0, GLOWRED, 'ground', [
        pool(0.95, 1.0, 10, pulse=(0.15, 30)),
        L('house', 'disc', 'nightmare_house', 1.0, 0.0, ap(0, 32, 'draw', easing='easeInOutSine', startAngle=270), rot=-2),
        *bleed('nightmare_house', 1.0, 0.006, delay=20, dur=14),
        L('core', 'disc', 'nightmare_core', 0.22, 0.012, ap(24, 12, 'unfold', 'fade'), color=PALE, br=0.8),
    ], flash={'color': BLOOD, 'size': 1.2, 'duration': 10, 'sparks': 18}, dissolve=('reverse', 'fade'), ddur=14)
    sigil('nightmare_house_over', '«Дом, которого нет»: печать над головой цели (весь каст), лицом вниз: коридор-проём, медленно вращается '
                                  'и «втягивается» (сжимается) к 46 тику; её видят все рядом — знак, кого забирает дом.', 0.7, GLOWRED, 'sky', [
        pool(1.0, 0.9, 8),
        L('house', 'disc', 'nightmare_house', 1.0, 0.0, ap(0, 16, 'unfold', 'fade'), rot=-8, boost=2, pulse=(0.15, 14)),
        *bleed('nightmare_house', 1.0, 0.006, delay=8, dur=10, br=0.4),
    ], flash={'color': BLOOD, 'size': 1.3, 'duration': 8, 'sparks': 10}, dissolve=('collapse', 'fade'), ddur=8)
    # --- «Ночь без рассвета»
    sigil('nightmare_night_ground', '«Ночь без рассвета», каст (3 с): лунная печать под заклинателем — фазы луны по ободу, «съеденная» фаза, '
                                    'кровь стекает с диска.', 3.2, GLOWRED, 'ground', [
        pool(0.95, 1.0, 10),
        L('moon', 'disc', 'nightmare_moon', 1.0, 0.0, ap(0, 34, 'draw', easing='easeInOutSine', startAngle=90, direction=-1), rot=1.5),
        *bleed('nightmare_moon', 1.0, 0.006, delay=22, dur=14),
        L('band', 'band', 'school_nightmare_band', 1.14, 0.015, ap(16, 20, 'draw', easing='easeInOutSine', startAngle=90), inner=0.92, repeat=12,
          color=PALE, br=0.5, rot=-3),
    ], flash={'color': BLOOD, 'size': 1.25, 'duration': 12, 'sparks': 22}, dissolve=('reverse', 'fade'), ddur=14,
          ground_light={'radius': 0.75, 'strength': 0.3})
    sigil('nightmare_night_floor', '«Ночь без рассвета», зона r24 (2 мин): огромная бледная печать по земле — луна и кольцо рук, тянущихся '
                                   'к центру; почти прозрачная, медленно вращается (у врагов внутри; заклинателю — тоже, как границу).',
          24.0, CRIMSON, 'ground', [
              L('hands', 'disc', 'nightmare_hands_ring', 1.0, 0.0, ap(0, 40, 'grow', 'fade', easing='easeOutSine'), rot=-0.4, br=0.35, pulse=(0.25, 80)),
              L('moon', 'disc', 'nightmare_moon', 0.45, 0.004, ap(10, 40, 'draw', easing='easeInOutSine', startAngle=90), rot=0.3, br=0.25),
          ], dissolve=('fade',), ddur=30)
    sigil('nightmare_red_moon', '«Ночь без рассвета»: красная луна в небе над зоной (запасной вариант, если код не подменяет луну неба): '
                                'диск-печать лицом вниз высоко (≈ +40), кровь стекает.', 6.0, '#C8203A', 'sky', [
        L('glow', 'disc', 'glow', 1.6, -0.01, ap(0, 40, 'grow', 'fade'), color='#8A1028', br=0.6, pulse=(0.1, 90)),
        L('moon', 'disc', 'nightmare_moon', 1.0, 0.0, ap(0, 40, 'grow', 'fade', easing='easeOutSine'), rot=0.2),
    ], dissolve=('fade',), ddur=40)
    # --- «Пробуждение не наступит»
    sigil('nightmare_abyss_ground', '«Пробуждение не наступит», каст 12 с: мифическая печать под заклинателем — руки из обода, часы без '
                                    'стрелок с надломленными метками, спираль закрытых плачущих глаз; прорисовывается 3 с, оплывает чернилами.',
          5.0, GLOWRED, 'ground', [
              pool(1.05, 1.0, 30, pulse=(0.12, 60)),
              L('abyss', 'disc', 'nightmare_abyss', 1.0, 0.0, ap(0, 60, 'draw', easing='easeInOutSine', startAngle=270), rot=0.8),
              *bleed('nightmare_abyss', 1.0, 0.006, delay=40, dur=30, br=0.45),
              L('band', 'band', 'school_nightmare_band', 1.16, 0.012, ap(30, 30, 'draw', easing='easeInOutSine', startAngle=270, direction=-1),
                inner=0.91, repeat=14, color=PALE, br=0.6, rot=-2),
              TX('words', 'DORMI ✦ NON EXPERGISCERIS ✦ ', 1.28, 0.06, 0.02, ap(60, 40, 'draw', easing='linear'), color=PALE, br=0.6,
                 rot=1.2, repeat=2),
              L('rim', 'band', 'thin_ring', 1.36, 0.025, ap(80, 16, 'draw', startAngle=90), inner=0.985, repeat=1, color=BLOOD, br=0.9),
          ], flash={'color': BLOOD, 'size': 1.25, 'duration': 14, 'sparks': 40}, dissolve=('reverse', 'fade'), ddur=20,
          ground_light={'radius': 0.8, 'strength': 0.4})
    sigil('nightmare_abyss_sky', '«Пробуждение не наступит»: печать-«небо» (с 4 с ролика), лицом вниз — спираль глаз; на 9 с глаза '
                                 '«открываются» (вспышка), на 11 с гаснет вместе с миром.', 14.0, CRIMSON, 'sky', [
        L('abyss', 'disc', 'nightmare_abyss', 1.0, 0.0, ap(0, 50, 'draw', easing='easeInOutSine', startAngle=270), rot=-0.6, br=0.7),
        *bleed('nightmare_abyss', 1.0, 0.006, delay=30, dur=30, br=0.3),
    ], dissolve=('fade',), ddur=20)
    # --- метки и малое
    sigil('nightmare_eye_over', 'Око над жертвой школы (метка Погружения у ЗАКЛИНАТЕЛЯ и союзников — кто под кошмаром): широко открыто, '
                                'плачет чернилами, моргает пульсом. Код может показывать его только своим (жертва его не видит).',
          0.42, GLOWRED, 'billboard', [
              pool(1.2, 0.8, 6, pulse=(0.3, 16)),
              L('eye', 'disc', 'nightmare_eye', 1.0, 0.0, ap(0, 8, 'grow', 'fade', easing='easeOutBack'), pulse=(0.2, 16)),
          ], flash={'color': BLOOD, 'size': 1.3, 'duration': 6, 'sparks': 6}, dissolve=('collapse', 'fade'), ddur=8)
    sigil('nightmare_hand_eye', 'Малое око у ладони заклинателя (жесты «Дома» и «Ночи»), смотрит вперёд.', 0.24, GLOWRED, 'facing', [
        pool(1.4, 0.8, 4),
        L('eye', 'disc', 'nightmare_eye', 1.0, 0.0, ap(0, 8, 'unfold', 'fade'), rot=0),
    ], flash={'color': BLOOD, 'size': 1.4, 'duration': 4, 'sparks': 4}, dissolve=('collapse', 'fade'), ddur=6)
    sigil('nightmare_hands_ground', 'Руки из земли / тени тянутся (стадия 3, «Ночь», «Руки из земли»): кольцо рук-теней к центру, '
                                    'тёмное, шевелится (пульс и вращение туда-обратно).', 3.0, SHADOW, 'ground', [
        L('hands', 'disc', 'nightmare_hands_ring', 1.0, 0.0, ap(0, 12, 'grow', 'fade', easing='easeOutBack'), rot=2, br=1.0, pulse=(0.08, 14)),
    ], dissolve=('collapse', 'fade'), ddur=10)


def fx(id, comment, style, duration, elements):
    write('fx/%s.json' % id, {'comment': comment + ' ' + GEN, 'style': style, 'duration': duration, 'elements': elements})


def E(type, delay=0, at='caster', **kw):
    o = {'type': type, 'delay': delay, 'at': at}
    o.update(kw)
    return o


def ease(d, e='easeOutCubic'):
    return {'duration': d, 'easing': e}


def style():
    write('fx/styles/nightmare.json', {
        'comment': 'Стиль школы «Кошмары» (T25): багрово-алый свет печатей на чернильной тьме; тени и чернила рисуются translucent '
                   '(тёмные цвета), блики — бледные. Капли чернил (@shards = mote_ink), движение вязкое, с рывками. ' + GEN,
        'palette': {'primary': GLOWRED, 'secondary': CRIMSON, 'core': PALE, 'shadow': INK},
        'textures': {'sparks': 'spark_soft', 'runes': 'school_nightmare_band', 'shards': 'mote_ink', 'sigil': 'nightmare_seal'},
        'blend': 'additive',
        'motion': {'rotationScale': 0.6, 'jitter': 0.25, 'easing': 'easeInOutSine', 'pulse': {'amp': 0.12, 'period': 26}}})


INKC = '#07030B'           # цвет чернил у спрайтов/декалей (тёмный → translucent)


def ink_drips(delay=0, at='caster+0,0.1,0', follow=True, rate=0.8, area=1.6, dur=9999, **kw):
    """Чернила сочатся из земли вокруг и падают каплями сверху (капли всплывают вверх и опадают)."""
    return [E('sprites', delay, at, duration=dur, follow=follow, texture='mote_ink', count=4000, rate=rate, area=area, speed=0.02,
              gravity=-0.004, size=[0.14, 0.05], life=26, color=INKC, blend='translucent', **kw),
            E('sprites', delay, at, duration=dur, follow=follow, texture='glow', count=4000, rate=rate * 0.5, area=area * 0.8, speed=0.004,
              gravity=-0.0008, size=[0.5, 0.9], life=30, color='#120814', brightness=0.6, blend='translucent', **kw)]


def school_fx():
    fx('school_nightmare', 'Каст обычной магии школы «Кошмары» (PohSpell.onCast): знак под магом, тьма вздрагивает (тёмная сфера), '
                           'капли чернил всплывают и опадают, тихий багровый отсвет.', 'nightmare', 36, [
        E('sigil', 0, 'caster+0,0.04,0', id='school_nightmare', follow=True),
        E('wave', 0, 'caster+0,1,0', duration=12, shape='sphere', radius=1.6, rim=0.8, color=INKC, brightness=0.8),
        E('wave', 0, 'caster', duration=14, shape='ring', radius=3.0, color='@secondary'),
        E('flash', 0, 'caster+0,0.3,0', duration=8, size=1.4, color=CRIMSON, brightness=0.6),
        E('sprites', 2, 'caster+0,0.15,0', duration=20, follow=True, texture='mote_ink', count=16, rate=1.2, area=1.4, speed=0.05,
          gravity=0.004, size=[0.16, 0.06], life=20, color=INKC, blend='translucent'),
    ])
    seal = [E('sigil', 0, 'caster+0,0.04,0', id='nightmare_seal', follow=True),
            E('flash', 0, 'caster+0,0.4,0', duration=10, size=2.0, color=CRIMSON, brightness=0.6),
            E('wave', 0, 'caster', duration=16, shape='ring', radius=4.0, color='@primary'),
            E('wave', 2, 'caster+0,1,0', duration=14, shape='sphere', radius=2.2, rim=0.9, color=INKC, brightness=0.8)]
    fx('school_nightmare_cast', 'T25, школа «Кошмары», ступень Высшая (SchoolSeals): печать под магом + чернила сочатся из земли. '
                                'duration −1: код останавливает эффект в конце каста.', 'nightmare', -1, seal + ink_drips(4))
    crown = [E('sigil', 10, 'caster+0,2.55,0', id='nightmare_crown', follow=True),
             E('flash', 10, 'caster+0,2.55,0', duration=10, size=1.3, color=CRIMSON, brightness=0.6, rays=6)]
    fx('school_nightmare_cast_crown', 'T25, школа «Кошмары», ступень Мифическая: печать + венец над головой + чернила. duration −1.',
       'nightmare', -1, seal[:1] + crown + seal[1:] + ink_drips(4))
    halos = []
    n = 7
    for k in range(n):
        a = math.radians(-72 + 144 * k / (n - 1))
        x, z = 1.9 * math.sin(a), -(1.9 * math.cos(a) * 0.6 + 0.55)
        y = 1.55 + 0.35 * math.cos(a)
        halos.append(E('sigil', 23 - abs(k - n // 2) * 3, 'caster+%.2f,%.2f,%.2f' % (x, y, z), id='golden_halo', follow=True,
                       orientation='facing', sigilScale=1.15 if k == n // 2 else 0.95))
    fx('school_nightmare_cast_divine', 'T25, школа «Кошмары», ступень Божественная: печать + венец + дуга из 7 золотых кругов за спиной '
                                       '(с краёв к центру), золотые блёстки — как у остальных школ. duration −1.',
       'nightmare', -1, seal[:1] + crown + seal[1:] + ink_drips(4) + halos + [
           E('sprites', 16, 'caster+0,1.6,-0.9', duration=9999, follow=True, texture='@sparks', count=4000, rate=1.5, spread=1.8,
             speed=0.01, gravity=-0.002, size=[0.1, 0.02], life=40, color='#FFD36B'),
           E('flash', 22, 'caster+0,1.7,-1.0', duration=12, follow=True, size=2.4, rays=8, color='#FFE9A8', brightness=0.6)])


def stage_fx():
    """Погружение — у ЖЕРТВЫ (пакет только ей), follow, duration −1: код включает нужную стадию и гасит прошлую (Fx.stop).
    Экранные накладки textures/fx/nightmare_stage1..3.png и подмены вида мира — код (см. письмо)."""
    s1 = [E('decal', 0, 'caster+0,0.06,0', duration=999999, follow=True, texture='nightmare_shadow_reach', radius=5.0, blend='translucent',
            color='#050208', spin=0.35, pulse=46, grow=30, **{'in': ease(30, 'easeOutSine')}),
          E('decal', 20, 'caster+0,0.07,0', duration=999999, follow=True, texture='nightmare_shadow_reach', radius=3.6, blend='translucent',
            color='#050208', spin=-0.5, rotation=40, pulse=33, grow=30),
          E('tint', 0, 'caster', duration=999999, radius=4, color=INK, strength=0.12, **{'in': ease(40, 'easeOutSine')}),
          E('sprites', 10, 'caster+0,0.2,0', duration=999999, follow=True, texture='mote_nm_ash', count=99999, rate=0.25, area=6, speed=0.01,
            gravity=-0.0015, spin=60, tumble=0.6, size=[0.18, 0.08], life=60, color=INKC, blend='translucent')]
    fx('nightmare_stage1', 'Погружение, стадия 1 «Тени» (жертва, follow, до остановки): тени на земле тянутся к ногам и медленно '
                           'вращаются/дышат, мир чуть темнее, в воздухе — хлопья тьмы. Мелькающие силуэты — nightmare_silhouette.',
       'nightmare', -1, s1)
    s2 = [dict(s1[0], radius=7.0, spin=0.5), dict(s1[1], radius=5.0, spin=-0.7), dict(s1[2], strength=0.2, radius=6), dict(s1[3], rate=0.45),
          E('sprites', 30, 'caster+0,1.4,0', duration=999999, follow=True, texture='mote_eye_n', count=99999, rate=0.05, area=9, speed=0.0,
            gravity=0.0, size=[0.22, 0.0], life=40, color=GLOWRED, glow=0.6),
          *ink_drips(0, rate=0.35, area=3.0, dur=999999)]
    fx('nightmare_stage2', 'Погружение, стадия 2 «Галлюцинации» (жертва): тени гуще и ближе, в темноте на 3–9 бл. открываются и '
                           'закрываются багровые глаза, чернила сочатся из земли. Фальшивые фигуры/звуки — код.', 'nightmare', -1, s2)
    s3 = [dict(s1[0], radius=9.0, spin=0.7), dict(s1[1], radius=6.0, spin=-0.9), E('tint', 0, 'caster', duration=999999, radius=48,
          color='#1A0408', strength=0.34, **{'in': ease(60, 'easeOutSine')}), dict(s2[3], rate=0.8, area=10), dict(s2[4], rate=0.12, area=14),
          *ink_drips(0, rate=0.9, area=6.0, dur=999999),
          E('sprites', 0, 'caster+0,9,0', duration=999999, follow=True, texture='mote_ink', count=99999, rate=1.4, area=16, speed=0.0,
            gravity=0.012, size=[0.12, 0.08], life=50, color=INKC, blend='translucent'),
          E('sigil', 0, 'caster+0,0.08,0', follow=True, id='nightmare_hands_ground', scale=1.4)]
    fx('nightmare_stage3', 'Погружение, стадия 3 «Кошмар» (жертва): мир темнеет и краснеет (tint r48), с неба моросят чернила, у ног — '
                           'кольцо рук-теней, глаза в темноте. Подмены текстур мира/неба/лиц и чудовища — код.', 'nightmare', -1, s3)
    fx('nightmare_stage_up', 'Погружение: стадия глубже (жертва, 24 тика): тьма схлопывается к жертве — тёмное кольцо внутрь, удар сердца '
                             '(багровая вспышка на 6 тике), капли.', 'nightmare', 24, [
        E('wave', 0, 'caster', duration=16, shape='ring', radius=6.0, color=INKC, brightness=1.0, reverse=True),   # (доп.) reverse — кольцо сходится к центру
        E('wave', 2, 'caster+0,1,0', duration=14, shape='sphere', radius=3.0, rim=1.0, color=INKC, brightness=0.9),
        E('flash', 6, 'caster+0,1.2,0', duration=8, size=2.2, color=CRIMSON, brightness=0.8, screen=0.25),
        E('sprites', 6, 'caster+0,1.0,0', duration=3, texture='mote_ink', count=24, rate=8, spread=0.6, speed=0.12, gravity=0.01,
          size=[0.2, 0.08], life=18, color=INKC, blend='translucent')])
    fx('nightmare_stage_down', 'Погружение: стадия спала (жертва, 30 тиков): тьма отступает кольцом наружу, бледный вздох.', 'nightmare', 30, [
        E('wave', 0, 'caster', duration=24, shape='ring', radius=8.0, color='#3A2A40', brightness=0.6),
        E('flash', 0, 'caster+0,1.4,0', duration=10, size=1.6, color=PALE, brightness=0.35),
        E('sprites', 0, 'caster+0,0.2,0', duration=10, texture='mote_nm_ash', count=16, rate=2, area=2.0, speed=0.03, gravity=-0.004,
          size=[0.16, 0.0], life=24, color=INKC, blend='translucent')])
    for k in range(3):
        fx('nightmare_silhouette_%d' % k, 'Мелькающий силуэт на краю зрения (жертва; caster = точка на земле, где он стоит; код выбирает точку '
                                          'в 8–16 бл. под углом 50–80° от взгляда). 8 тиков: проявляется за 2, стоит, гаснет; вариант %d.' % k,
           'nightmare', 8, [E('sprites', 0, 'caster+0,1.25,0', duration=1, texture='nightmare_silhouette_%d' % k, count=1, rate=1, spread=0.0,
                              speed=0.0, gravity=0.0, size=[2.6, 2.5], life=8, color='#030104', blend='translucent')])
    fx('nightmare_mark', 'Метка «под кошмаром» (у заклинателя и союзников над жертвой; жертве не слать): око над головой, плачет. '
                         'follow, −1 — гасить Fx.stop, когда стадия 0.', 'nightmare', -1, [
        E('sigil', 0, 'caster+0,2.4,0', follow=True, id='nightmare_eye_over'),
        E('sprites', 4, 'caster+0,2.25,0', duration=999999, follow=True, texture='mote_ink', count=99999, rate=0.2, spread=0.08, speed=0.0,
          gravity=0.006, size=[0.08, 0.05], life=20, color=INKC, blend='translucent')])


def spell_fx():
    # ---------------------------------------------------------------- «Дом, которого нет» (Высшее): каст 50 тиков
    fx('nightmare_house_seal', '«Дом, которого нет»: печать под заклинателем на время каста — играть, только если SchoolSeals.shown(caster) '
                               '== false (иначе две печати).', 'nightmare', -1, [E('sigil', 0, 'caster+0,0.05,0', id='nightmare_house_ground', follow=True)])
    fx('nightmare_house_cast', '«Дом, которого нет», каст 2.5 с (50 тиков; caster + target): над целью раскрывается печать-коридор '
                               '(никаких линий к цели), у ладони — око; на 44 тике печать «втягивается», на 46 — у ног цели чернила '
                               'смыкаются (видят все: цель «проваливается» только для себя). Анимация pohsmp_nightmare_house_cast.',
       'nightmare', 56, [
           E('sigil', 0, 'caster.hand', follow=True, id='nightmare_hand_eye', until=46),
           E('sigil', 4, 'target+0,2.6,0', follow=True, id='nightmare_house_over', until=46),
           E('sprites', 6, 'target+0,2.4,0', duration=40, follow=True, texture='mote_ink', count=200, rate=0.8, spread=0.4, speed=0.0,
             gravity=0.01, size=[0.12, 0.06], life=20, color=INKC, blend='translucent'),
           E('decal', 20, 'target+0,0.06,0', duration=36, texture='nightmare_shadow_reach', radius=2.4, grow=26, spin=1.2, blend='translucent',
             color='#050208', follow=True),
           E('wave', 44, 'target+0,1,0', duration=8, shape='sphere', radius=1.2, rim=1.2, color=INKC, brightness=1.0, reverse=True),
           E('vortex', 40, 'target+0,0.1,0', duration=14, radius=1.6, height=2.4, arms=4, speed=-18, pull=0.6, texture='mote_ink', color=INKC,
             follow=True),
           E('flash', 46, 'target+0,1,0', duration=8, size=1.8, color=CRIMSON, brightness=0.7),
           E('sprites', 46, 'target+0,0.2,0', duration=3, texture='mote_ink', count=30, rate=10, area=1.2, speed=0.14, gravity=0.012,
             size=[0.22, 0.08], life=20, color=INKC, blend='translucent'),
       ])
    fx('nightmare_house_enter', '«Дом»: вход в коридор — ТОЛЬКО ЖЕРТВЕ (follow, 30 тиков): мир тонет в черноте за 10 тиков (tint 1.0), '
                                'падение (код: лёгкий крен/опускание камеры), из темноты проступает коридор (код включает модули на 20 тике).',
       'nightmare', 30, [
           E('tint', 0, 'caster', duration=30, radius=64, color='#000000', strength=1.0, **{'in': ease(10, 'easeInCubic'), 'out': ease(10, 'easeOutSine')}),
           E('sprites', 0, 'caster+0,2.5,0', duration=10, follow=True, texture='mote_ink', count=60, rate=6, area=3, speed=0.0, gravity=0.03,
             size=[0.3, 0.2], life=14, color=INKC, blend='translucent'),
           E('flash', 18, 'caster+0,1.4,0', duration=6, size=2.0, color=CRIMSON, brightness=0.4)])
    fx('nightmare_house_corridor', '«Дом»: атмосфера коридора у жертвы (follow, 1200 тиков = 1 мин; гасить Fx.stop при выходе): пыль в луче '
                                   'лампы, туман у пола, капли с потолка; тени — nightmare_house_shadow. Модули — fx/meshes/nightmare_corridor (код).',
       'nightmare', 1200, [
           E('sprites', 0, 'caster+0,1.2,0', duration=1200, follow=True, texture='spark_soft', count=99999, rate=0.6, area=4, speed=0.003,
             gravity=-0.0002, size=[0.04, 0.0], life=60, color='#A89070', brightness=0.4),
           E('sprites', 0, 'caster+0,0.1,0', duration=1200, follow=True, texture='glow', count=99999, rate=0.5, area=4, speed=0.003,
             gravity=0.0, size=[1.2, 2.0], life=70, color='#100818', brightness=0.5, blend='translucent'),
           E('sprites', 0, 'caster+0,3.3,0', duration=1200, follow=True, texture='mote_ink', count=99999, rate=0.3, area=3, speed=0.0,
             gravity=0.02, size=[0.1, 0.06], life=20, color=INKC, blend='translucent'),
           E('tint', 0, 'caster', duration=1200, radius=64, color='#120A08', strength=0.25, **{'in': ease(20), 'out': ease(20)})])
    fx('nightmare_house_shadow', '«Дом»: тень выходит из двери (жертва; caster = точка двери на полу коридора, yaw — внутрь коридора; '
                                 '40 тиков): дверь распахивается (mesh nightmare_door, петля), из проёма вытекает тьма, проступает силуэт '
                                 '(через 12 тиков код ставит на это место тень — модель nm_lurker с appear). ',
       'nightmare', 40, [
           E('mesh', 0, 'caster', model='nightmare_door', follow=False, until=40,
             hinge={'pivot': [-0.5, 0, 0], 'axis': 'y', 'keys': [[0, 0, 'linear'], [3, -6, 'easeOutCubic'], [6, -4, 'easeInOutSine'],
                                                                 [12, -105, 'easeOutBack'], [36, -100, 'easeInOutSine']]}),
           E('sprites', 8, 'caster+0,0.2,0.3', duration=20, texture='glow', count=40, rate=2, area=0.8, speed=0.02, gravity=0.0,
             size=[0.8, 1.6], life=26, color='#05020A', brightness=0.8, blend='translucent', cone=60),
           E('sprites', 10, 'caster+0,1.1,0.4', duration=1, texture='nightmare_silhouette_0', count=1, rate=1, spread=0, speed=0, gravity=0,
             size=[1.0, 2.6], life=14, color='#030104', blend='translucent'),
           E('decal', 8, 'caster+0,0.05,0.8', duration=32, texture='nightmare_shadow_reach', radius=1.6, grow=12, blend='translucent',
             color='#050208')])
    fx('nightmare_house_exit', '«Дом»: выход из коридора (жертва, 30 тиков): коридор растворяется чернилами вверх, свет возвращается '
                               'бледной вспышкой; дальше — стадия 2 (nightmare_stage2).', 'nightmare', 30, [
        E('tint', 0, 'caster', duration=30, radius=64, color='#000000', strength=0.9, **{'in': ease(4), 'out': ease(24, 'easeOutSine')}),
        E('sprites', 0, 'caster+0,0.5,0', duration=12, follow=True, texture='mote_ink', count=80, rate=7, area=4, speed=0.02, gravity=-0.02,
          size=[0.24, 0.1], life=20, color=INKC, blend='translucent'),
        E('flash', 4, 'caster+0,1.5,0', duration=10, size=2.4, color=PALE, brightness=0.4)])
    # ---------------------------------------------------------------- «Ночь без рассвета» (Высшее): каст 60 тиков, зона r24 на 2 мин
    fx('nightmare_night_seal', '«Ночь без рассвета»: печать под заклинателем на время каста (правило SchoolSeals.shown).', 'nightmare', -1,
       [E('sigil', 0, 'caster+0,0.05,0', id='nightmare_night_ground', follow=True)])
    fx('nightmare_night_cast', '«Ночь без рассвета», каст 3 с (60 тиков): левая ладонь гасит «свет» (око у ладони), правая поднимается к '
                               'небу — над заклинателем всходит красная луна (печать nightmare_red_moon, растёт), с 30 тика небо темнеет; '
                               'на 56 тике — «закат навсегда»: тёмная волна по земле до r24. Анимация pohsmp_nightmare_night_cast.',
       'nightmare', 70, [
           E('sigil', 0, 'caster.hand', follow=True, id='nightmare_hand_eye', until=30),
           E('sigil', 10, 'caster+0,9,0', id='nightmare_red_moon', scale=0.5, until=70),
           E('sprites', 12, 'caster+0,9,0', duration=40, texture='mote_ink', count=200, rate=4, spread=1.5, speed=0.0, gravity=0.02,
             size=[0.16, 0.08], life=30, color='#3A0410', blend='translucent'),
           E('tint', 30, 'caster', duration=40, radius=30, color='#12020A', strength=0.4, **{'in': ease(26, 'easeInSine'), 'out': ease(14)}),
           E('wave', 56, 'caster', duration=24, shape='ring', radius=24, thickness=3, color=INKC, brightness=1.0, followTerrain=True),
           E('wave', 56, 'caster+0,1,0', duration=20, shape='sphere', radius=6, rim=1.0, color=CRIMSON, brightness=0.6),
           E('flash', 56, 'caster+0,1.4,0', duration=10, size=3.0, color=CRIMSON, brightness=0.7, screen=0.2),
       ])
    fx('nightmare_night_zone', '«Ночь без рассвета», зона 2 мин (2400 тиков; caster = центр зоны, не follow; гасить Fx.stop): печать по '
                               'земле r24, по краю — тёмная завеса (вертикальные струи тьмы), внутри — сумрак с красным отливом (tint r24), '
                               'хлопья тьмы и капли. Вечная ночь и красная луна неба у врагов внутри — код (см. письмо); nightmare_red_moon — '
                               'запасной диск в небе.', 'nightmare', 2400, [
        E('sigil', 0, 'caster+0,0.06,0', id='nightmare_night_floor', until=2390),
        E('sigil', 0, 'caster+0,40,0', id='nightmare_red_moon', until=2390),
        E('curtain', 0, 'caster', duration=2400, count=64, radius=24, height=[6, 14], grow=40, width=[0.6, 1.4], brightness=[0.6, 1.0],
          texture='beam_fade', color=INKC, flicker=0.2, **{'in': ease(40), 'out': ease(40)}),
        E('tint', 0, 'caster', duration=2400, radius=24, color='#1A0208', strength=0.38, **{'in': ease(40), 'out': ease(40)}),
        E('sprites', 0, 'caster+0,8,0', duration=2400, texture='mote_nm_ash', count=999999, rate=3.0, area=24, speed=0.0, gravity=0.004,
          spin=40, tumble=0.8, size=[0.2, 0.1], life=120, color=INKC, blend='translucent'),
        E('sprites', 0, 'caster+0,0.2,0', duration=2400, texture='glow', count=999999, rate=1.0, area=24, speed=0.002, gravity=-0.0004,
          size=[1.6, 2.6], life=90, color='#14040C', brightness=0.6, blend='translucent'),
    ])
    fx('nightmare_night_pulse', '«Ночь»: каждые 8 с — «стадия глубже» (caster = центр зоны, 36 тиков): от края зоны к центру бежит тёмное '
                                'кольцо (сжатие), удар сердца — багровая вспышка в центре на 20 тике.', 'nightmare', 36, [
        E('wave', 0, 'caster', duration=20, shape='ring', radius=24, thickness=2.5, color=INKC, brightness=1.0, reverse=True, followTerrain=True),
        E('flash', 20, 'caster+0,1,0', duration=10, size=4, color=CRIMSON, brightness=0.6),
        E('wave', 20, 'caster', duration=14, shape='ring', radius=6, color='@secondary', brightness=0.7)])
    fx('nightmare_night_light', '«Ночь»: настоящий свет (блочный ≥ 10) удерживает стадию — на источнике (caster = точка блока) бледный '
                                'ореол-сопротивление, тьма вокруг отступает кольцом (40 тиков; показывать жертве, когда свет её спас).',
       'nightmare', 40, [
           E('flash', 0, 'caster+0,0.5,0', duration=30, size=2.4, color='#FFE8C0', brightness=0.5),
           E('wave', 0, 'caster', duration=30, shape='ring', radius=4.0, color='#FFE8C0', brightness=0.5),
           E('sprites', 0, 'caster+0,0.5,0', duration=20, texture='mote_nm_ash', count=20, rate=1, area=3, speed=0.05, gravity=0.0,
             size=[0.2, 0.0], life=20, color=INKC, blend='translucent')])
    # ---------------------------------------------------------------- «Пробуждение не наступит» (Мифическое): каст 240 тиков + хвост
    t = 20                   # тиков в секунде
    cast = [
        # 0–2 с: печать прорисовывается, из трещин в земле сочатся чернила, сломанная колыбельная (звук — код)
        E('sigil', 0, 'caster+0,0.05,0', id='nightmare_abyss_ground', until=244),
        E('decal', 0, 'caster+0,0.06,0', duration=80, texture='slash_crack', radius=6, grow=40, blend='translucent', color=INKC, rotation=20),
        *ink_drips(4, 'caster+0,0.1,0', follow=False, rate=1.2, area=5, dur=2 * t * 6 - 4),
        # 2–4 с: чернила поднимаются — лужа расползается до r16, капли падают ВВЕРХ, струи-ленты
        E('decal', 2 * t, 'caster+0,0.07,0', duration=200, texture='nightmare_ink_flood', radius=16, grow=50, blend='translucent', color='#0A0610',
          spin=0.15),
        E('sprites', 2 * t, 'caster+0,0.3,0', duration=4 * t, texture='mote_ink', count=1200, rate=8, area=12, speed=0.0, gravity=-0.02,
          size=[0.18, 0.06], life=40, color=INKC, blend='translucent'),
        E('ribbon', 2 * t, 'caster+0,0.2,0', duration=6 * t, width=0.5, length=26, fade=1.2, color=INKC, texture='strip_soft',
          orbit={'radius': 4, 'speed': 5, 'rise': 1.2, 'risePeriod': 40, 'climb': 2.2}, count=6),
        # 4–6 с: небо гаснет, «небо-печать» спиралью глаз, у ног — тени-руки (кольцо r12)
        E('sigil', 4 * t, 'caster+0,24,0', id='nightmare_abyss_sky', until=11 * t),
        E('tint', 4 * t, 'caster', duration=8 * t, radius=64, color='#0A0206', strength=0.55, **{'in': ease(2 * t, 'easeInSine'), 'out': ease(10)}),
        E('decal', 4 * t, 'caster+0,0.09,0', duration=7 * t, texture='nightmare_shadow_reach', radius=12, grow=30, spin=0.6, blend='translucent',
          color='#050208'),
        # 6–8 с: мир тонет — стена чернил встаёт кольцом r28 и растёт до неба, воронка вокруг мага
        E('curtain', 6 * t, 'caster', duration=5 * t, count=120, radius=[22, 30], height=[10, 40], grow=2 * t, width=[1.2, 2.6],
          brightness=[0.8, 1.0], texture='beam_fade', color=INKC, fromTop=False),
        E('vortex', 6 * t, 'caster+0,0.2,0', duration=4 * t, radius=10, height=12, arms=6, speed=6, pull=0.3, texture='mote_ink', color=INKC,
          width=0.6, particles=200, life=40, size=0.2),
        E('wave', 6 * t, 'caster+0,1,0', duration=2 * t, shape='sphere', radius=8, rim=1.0, color=INKC, brightness=1.0),
        # 8–10 с: в чернилах открываются глаза (багровые искры), на 9 с — удар сердца, облик мага меняется (код: nm_dread у жертв)
        E('sprites', 8 * t, 'caster+0,6,0', duration=2 * t, texture='mote_eye_n', count=160, rate=4, area=20, speed=0.0, gravity=0.0,
          size=[0.5, 0.0], life=36, color=GLOWRED, glow=0.8),
        E('flash', 9 * t, 'caster+0,1.6,0', duration=10, size=5, color=CRIMSON, brightness=0.9, screen=0.35),
        E('wave', 9 * t, 'caster', duration=16, shape='ring', radius=20, color='@primary', brightness=0.8),
        # 10–11.8 с: всё чёрное, тишина; на 11 с — одиночный удар сердца (тусклая багровая вспышка)
        E('tint', 10 * t, 'caster', duration=int(1.8 * t), radius=64, color='#000000', strength=1.0, **{'in': ease(12, 'easeInCubic'), 'out': ease(2)}),
        E('flash', 11 * t, 'caster+0,1.6,0', duration=6, size=2.0, color=DEEP_RED_GLOW, brightness=0.6),
        # 11.8–12 с: глаза открываются — багровая вспышка, волна до r64; мир возвращается кошмаром (стадия 3 у всех жертв)
        E('flash', 236, 'caster+0,1.6,0', duration=10, size=6, color=BLOOD, brightness=1.0, screen=0.6, rays=8),
        E('wave', 236, 'caster', duration=30, shape='ring', radius=64, thickness=6, color='@primary', brightness=0.9, followTerrain=True),
        E('wave', 236, 'caster+0,1,0', duration=24, shape='sphere', radius=24, rim=1.2, color=INKC, brightness=1.0),
        E('sprites', 236, 'caster+0,1.4,0', duration=3, texture='mote_ink', count=80, rate=30, spread=1.0, speed=0.35, gravity=0.01,
          size=[0.3, 0.1], life=30, color=INKC, blend='translucent'),
    ]
    fx('nightmare_abyss_cast', '«Пробуждение не наступит», каст 12 с = 240 тиков + хвост 20 (caster; видят все в r64 — это ролик). '
                               'Шкала = ролик (ТЗ T25, «Ролик») и анимация pohsmp_nightmare_abyss_cast: 0–2 печать и чернила из трещин; '
                               '2–4 лужа до r16, капли вверх, ленты; 4–6 небо гаснет, печать-небо, тени-руки; 6–8 стена чернил r22–30, '
                               'воронка; 8–10 глаза в чернилах, 9 с — удар сердца (облик мага → nm_dread у жертв); 10–11.8 тьма и тишина; '
                               '11.8 (236 тик) — вспышка, волна до r64, у всех жертв — стадия 3.', 'nightmare', 260, cast)
    fx('nightmare_abyss_world', '«Пробуждение не наступит»: мир-кошмар жертвы на 5 мин (follow, 6000 тиков; гасить Fx.stop при снятии): '
                                'всё стадии 3 + гуще: чернильный дождь, глаза в темноте ближе и чаще, тени у ног шире, багровый туман. '
                                'Подмены мира/неба/лиц, чудовища, сны-места (дом жертвы тенями) — код.', 'nightmare', 6000, [
        E('decal', 0, 'caster+0,0.06,0', duration=6000, follow=True, texture='nightmare_shadow_reach', radius=11, blend='translucent',
          color='#050208', spin=0.8, pulse=40),
        E('tint', 0, 'caster', duration=6000, radius=64, color='#200208', strength=0.42, **{'in': ease(40), 'out': ease(40)}),
        E('sprites', 0, 'caster+0,10,0', duration=6000, follow=True, texture='mote_ink', count=999999, rate=2.4, area=18, speed=0.0,
          gravity=0.014, size=[0.14, 0.08], life=50, color=INKC, blend='translucent'),
        E('sprites', 0, 'caster+0,1.5,0', duration=6000, follow=True, texture='mote_eye_n', count=999999, rate=0.2, area=12, speed=0.0,
          gravity=0.0, size=[0.3, 0.0], life=40, color=GLOWRED, glow=0.7),
        E('sprites', 0, 'caster+0,0.2,0', duration=6000, follow=True, texture='glow', count=999999, rate=0.8, area=14, speed=0.002,
          gravity=0.0, size=[2.0, 3.0], life=90, color='#18040C', brightness=0.7, blend='translucent'),
        E('sigil', 0, 'caster+0,0.08,0', follow=True, id='nightmare_hands_ground', scale=2.0, until=5990)])
    fx('nightmare_abyss_thicken', '«Пробуждение не наступит»: каждую минуту кошмар сгущается (жертва, 60 тиков): мир на миг гаснет '
                                  '(tint к чёрному за 6 тиков), два удара сердца (багровые вспышки на 10 и 22 тике), тьма сжимается кольцом к '
                                  'жертве, глаза вокруг разом открываются. Шаги сгущения (больше галлюцинаций → союзники нападают → ники '
                                  'пропадают) — код; эффект один и тот же.', 'nightmare', 60, [
        E('tint', 0, 'caster', duration=40, radius=64, color='#000000', strength=0.85, **{'in': ease(6, 'easeInCubic'), 'out': ease(30, 'easeOutSine')}),
        E('flash', 10, 'caster+0,1.4,0', duration=8, size=3, color=CRIMSON, brightness=0.8, screen=0.3),
        E('flash', 22, 'caster+0,1.4,0', duration=8, size=3.6, color=BLOOD, brightness=0.9, screen=0.4),
        E('wave', 8, 'caster', duration=24, shape='ring', radius=16, thickness=3, color=INKC, brightness=1.0, reverse=True),
        E('sprites', 22, 'caster+0,1.6,0', duration=4, texture='mote_eye_n', count=40, rate=10, area=8, speed=0.0, gravity=0.0,
          size=[0.45, 0.0], life=30, color=GLOWRED, glow=0.9)])
    fx('nightmare_abyss_dispel', '«Пробуждение не наступит»: кошмар рассеивается (заклинатель убит / «Благословение»; у каждой жертвы, '
                                 '40 тиков): чернила стекают вниз и уходят в землю, бледная вспышка, тьма кольцом наружу.', 'nightmare', 40, [
        E('tint', 0, 'caster', duration=40, radius=64, color='#000000', strength=0.6, **{'in': ease(2), 'out': ease(36, 'easeOutSine')}),
        E('flash', 2, 'caster+0,1.6,0', duration=14, size=4, color=PALE, brightness=0.5, screen=0.3),
        E('wave', 2, 'caster', duration=30, shape='ring', radius=20, color='#C8C0D0', brightness=0.5),
        E('sprites', 0, 'caster+0,3,0', duration=10, follow=True, texture='mote_ink', count=120, rate=12, area=6, speed=0.0, gravity=0.05,
          size=[0.25, 0.1], life=16, color=INKC, blend='translucent')])
    # ---------------------------------------------------------------- бестиарий: появление/исчезновение и удары
    fx('nm_spawn', 'Кошмар-моб появляется (caster = сущность; играть вместе с её анимацией appear): лужа чернил растёт, всплеск, капли '
                   'летят вверх и опадают. 24 тика. Видят только жертвы (как сам моб).', 'nightmare', 24, [
        E('decal', 0, 'caster+0,0.05,0', duration=24, texture='nightmare_ink_flood', radius=1.6, grow=8, blend='translucent', color='#0A0610',
          fadeOut=10),
        E('sprites', 0, 'caster+0,0.1,0', duration=6, texture='mote_ink', count=24, rate=4, area=1.0, speed=0.06, gravity=0.008,
          size=[0.2, 0.06], life=20, color=INKC, blend='translucent'),
        E('sprites', 0, 'caster+0,0.3,0', duration=10, texture='glow', count=10, rate=1, area=1.0, speed=0.01, gravity=-0.002,
          size=[1.2, 1.8], life=20, color='#100816', brightness=0.7, blend='translucent')])
    fx('nm_despawn', 'Кошмар-моб исчезает — рассыпается чернилами (caster = сущность, 24 тика; при спаде кошмара и смерти копии): брызги '
                     'капель во все стороны по росту сущности, клочья тьмы, лужа на месте.', 'nightmare', 24, [
        E('sprites', 0, 'caster+0,1.0,0', duration=3, texture='mote_ink', count=40, rate=14, spread=0.6, speed=0.12, gravity=0.012,
          size=[0.22, 0.06], life=22, color=INKC, blend='translucent'),
        E('sprites', 0, 'caster+0,1.0,0', duration=4, texture='mote_nm_ash', count=20, rate=5, spread=0.6, speed=0.05, gravity=-0.004,
          spin=90, size=[0.25, 0.0], life=24, color=INKC, blend='translucent'),
        E('decal', 2, 'caster+0,0.05,0', duration=22, texture='nightmare_ink_flood', radius=1.3, grow=4, blend='translucent', color='#0A0610',
          fadeOut=12)])
    fx('nm_hands_grab', 'Руки из земли хватают (caster = жертва у ног; 30 тиков = 1.5 с удержания): тени-руки смыкаются у ног, брызги, '
                        'тёмное кольцо.', 'nightmare', 30, [
        E('sigil', 0, 'caster+0,0.06,0', id='nightmare_hands_ground', scale=0.5, until=30),
        E('sprites', 0, 'caster+0,0.2,0', duration=3, texture='mote_ink', count=16, rate=6, area=0.6, speed=0.08, gravity=0.01,
          size=[0.18, 0.06], life=14, color=INKC, blend='translucent')])
    fx('nm_maw_roar', 'Рёв Пасти (caster = Пасть, 40 тиков; вместе с анимацией roar): тёмная волна-сфера r8 из пасти, брызги, '
                      'у жертв — дрожь экрана (код по инструкции roar).', 'nightmare', 40, [
        E('wave', 4, 'caster+0,2.6,-1.0', duration=24, shape='sphere', radius=8, rim=1.2, color=INKC, brightness=0.9),
        E('wave', 4, 'caster', duration=28, shape='ring', radius=10, color='@secondary', brightness=0.7),
        E('sprites', 4, 'caster+0,2.4,-1.4', duration=20, texture='mote_ink', count=60, rate=3, spread=0.8, speed=0.15, gravity=0.01,
          size=[0.2, 0.08], life=20, color=INKC, blend='translucent', cone=70)])
    fx('nm_weeper_aura', 'Плакальщица плачет (caster = она, follow, −1 пока слышно): капли чернил падают с лица, тёмная дымка у подола, '
                         'фиолетовый отсвет слёз — знак, что остальные кошмары сильнее.', 'nightmare', -1, [
        E('sprites', 0, 'caster+0,2.3,-0.2', duration=999999, follow=True, texture='mote_ink', count=999999, rate=0.5, spread=0.1, speed=0.0,
          gravity=0.01, size=[0.08, 0.05], life=24, color=INKC, blend='translucent'),
        E('sprites', 0, 'caster+0,0.1,0', duration=999999, follow=True, texture='glow', count=999999, rate=0.3, area=1.4, speed=0.002,
          gravity=-0.0006, size=[1.0, 1.6], life=50, color='#120818', brightness=0.6, blend='translucent'),
        E('aura', 0, 'caster', target='caster', duration=999999, thickness=0.04, pulse=[0.3, 40], motes=0, color='#5A2A70', brightness=0.25)])
    fx('nm_lurker_dissolve', 'Тень-за-углом растворяется, когда на неё смотрят прямо (caster = она, 14 тиков; вместе с анимацией dissolve): '
                             'клочья тьмы рвутся в стороны и вверх.', 'nightmare', 14, [
        E('sprites', 0, 'caster+0,1.4,0', duration=6, texture='mote_nm_ash', count=40, rate=8, spread=0.9, speed=0.08, gravity=-0.006, spin=120,
          size=[0.35, 0.0], life=14, color=INKC, blend='translucent'),
        E('sprites', 0, 'caster+0,1.4,0', duration=4, texture='glow', count=10, rate=3, spread=0.6, speed=0.03, gravity=-0.004,
          size=[1.4, 0.4], life=14, color='#06030A', brightness=0.8, blend='translucent')])


DEEP_RED_GLOW = '#8A1028'


# ================================================================== модели (fx/meshes, части boxes — docs/fx.md)
def _r(v):
    return round(float(v), 4)


def bar(p, q, w, d=None, tone=0):
    """Брусок вдоль отрезка p→q (сечение w×d). Поворот [rx, ry, rz] (Euler YXZ, как в docs/fx.md)."""
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


def bx(x0, y0, z0, x1, y1, z1, tone, rot=None):
    b = [_r(min(x0, x1)), _r(min(y0, y1)), _r(min(z0, z1)), _r(max(x0, x1)), _r(max(y0, y1)), _r(max(z0, z1)), tone]
    if rot:
        b.append(rot)
    return b


def mesh(id, comment, parts, formed=10, collapse=10, extra=None):
    o = {'comment': comment + ' ' + GEN, 'style': 'nightmare', 'center': 0, 'formedAt': formed,
         'collapse': {'duration': collapse, 'easing': 'easeInCubic'}, 'parts': parts}
    if extra:
        o.update(extra)
    write('fx/meshes/%s.json' % id, o)


def mesh_corridor():
    """Модуль коридора «Дома, которого нет»: 3 бл. шириной (x −1.5…1.5), 3.5 бл. высотой, 4 бл. длиной (z 0…4) — ставить подряд вдоль z
    (стыкуется без шва). В середине модуля по двери на каждой стене (проём 1×2.2 в нише, дверь закрыта — для «открытой» код ставит
    отдельную nightmare_door). Обои — полосы двух тонов, деревянная панель снизу, плинтус, карниз, потолок, лампа (тусклый тёплый свет),
    пустая рама для картины, пятна сырости, потёки чернил по стенам, доски пола."""
    T = {'floor0': 0, 'floor1': 1, 'gap': 2, 'wall0': 3, 'wall1': 4, 'panel': 5, 'trim': 6, 'ceil': 7, 'door': 8, 'frame': 9, 'knob': 10,
         'lamp': 11, 'ink': 12, 'stain': 13, 'picture': 14, 'void': 15}
    b = []
    for i in range(6):                                                         # пол: доски вдоль z
        x0 = -1.5 + i * 0.5
        for j, (z0, z1) in enumerate(((0, 1.6 + 0.4 * (i % 2)), (1.6 + 0.4 * (i % 2), 4))):
            b.append(bx(x0 + 0.01, -0.1, z0 + 0.01, x0 + 0.49, 0.0, z1 - 0.01, T['floor0'] if (i + j) % 2 else T['floor1']))
    b.append(bx(-1.5, -0.12, 0, 1.5, -0.1, 4, T['gap']))
    for sx in (-1, 1):
        xw = sx * 1.5
        xin = sx * 1.45
        # стены: полосы обоев, кроме проёма двери (z 1.5…2.5, y 0…2.2)
        for k in range(8):
            z0, z1 = k * 0.5, k * 0.5 + 0.5
            tone = T['wall0'] if k % 2 else T['wall1']
            if 1.5 <= z0 < 2.5:
                b.append(bx(xin, 2.35, z0, xw + sx * 0.05, 3.5, z1, tone))
            else:
                b.append(bx(xin, 1.0, z0, xw + sx * 0.05, 3.5, z1, tone))
                b.append(bx(xin - sx * 0.03, 0.0, z0, xw, 1.0, z1, T['panel']))              # панель снизу
        b.append(bx(xin - sx * 0.06, 0.95, 0, xin, 1.05, 1.5, T['trim']))
        b.append(bx(xin - sx * 0.06, 0.95, 2.5, xin, 1.05, 4, T['trim']))
        b.append(bx(xin - sx * 0.08, 0.0, 0, xin, 0.15, 1.5, T['trim']))                   # плинтус
        b.append(bx(xin - sx * 0.08, 0.0, 2.5, xin, 0.15, 4, T['trim']))
        b.append(bx(xin - sx * 0.12, 3.35, 0, xin, 3.5, 4, T['trim']))                     # карниз
        # дверь в нише: рама, полотно, ручка
        b.append(bx(xin - sx * 0.1, 0, 1.38, xin + sx * 0.05, 2.45, 1.5, T['frame']))
        b.append(bx(xin - sx * 0.1, 0, 2.5, xin + sx * 0.05, 2.45, 2.62, T['frame']))
        b.append(bx(xin - sx * 0.1, 2.35, 1.38, xin + sx * 0.05, 2.5, 2.62, T['frame']))
        b.append(bx(xin + sx * 0.04, 0, 1.5, xin + sx * 0.12, 2.35, 2.5, T['door']))
        for (y0, y1) in ((0.15, 1.05), (1.2, 2.2)):                                      # филёнки
            b.append(bx(xin + sx * 0.03, y0, 1.6, xin + sx * 0.04, y1, 2.4, T['frame']))
        b.append(bx(xin - sx * 0.0, 1.0, 2.3, xin + sx * 0.04, 1.08, 2.38, T['knob']))
        b.append(bx(xin + sx * 0.0, 0.0, 1.5, xin + sx * 0.04, 0.02, 2.5, T['ink']))      # чернила из-под двери
        b.append(bx(xin - sx * 0.5, 0.0, 1.55, xin, 0.012, 2.45, T['ink']))
        # рама картины (пустая, чёрная внутри) и пятна, потёки
        zc = 0.75 if sx > 0 else 3.25
        b.append(bx(xin - sx * 0.04, 1.6, zc - 0.4, xin, 2.5, zc + 0.4, T['frame']))
        b.append(bx(xin - sx * 0.05, 1.7, zc - 0.3, xin - sx * 0.01, 2.4, zc + 0.3, T['void']))
        rng = random.Random(25 + sx)
        for k in range(7):
            z = rng.uniform(0.1, 3.9)
            if 1.35 < z < 2.65:
                continue
            top = rng.uniform(2.4, 3.4)
            L = rng.uniform(0.6, 2.2)
            b.append(bx(xin - sx * 0.015, max(1.06, top - L), z - 0.03, xin, top, z + 0.03, T['ink']))
            b.append(bx(xin - sx * 0.02, max(1.06, top - L) - 0.05, z - 0.045, xin, max(1.06, top - L) + 0.04, z + 0.045, T['ink']))
        for k in range(3):
            z = rng.uniform(0.2, 3.8)
            y = rng.uniform(1.4, 3.0)
            b.append(bx(xin - sx * 0.01, y - 0.3, z - 0.35, xin, y + 0.3, z + 0.35, T['stain']))
    b.append(bx(-1.55, 3.5, 0, 1.55, 3.6, 4, T['ceil']))
    for k in range(4):                                                          # балки-кессоны потолка
        b.append(bx(-1.5, 3.42, k + 0.45, 1.5, 3.5, k + 0.55, T['trim']))
    lamp = [bx(-0.02, 3.0, 1.98, 0.02, 3.5, 2.02, T['trim']), bx(-0.22, 2.84, 1.8, 0.22, 3.0, 2.2, T['frame'])]
    glow = [bx(-0.16, 2.78, 1.86, 0.16, 2.86, 2.14, T['lamp'])]
    tones = ['#2A1C16', '#22160F', '#080406', '#3A2A30', '#332428', '#24160F', '#1A100C', '#3A363A', '#2E1C12', '#1A100A', '#8A7040',
             '#FFB070', '#07030A', '#141A12', '#120A08', '#020103']
    mesh('nightmare_corridor', 'Модуль коридора «Дома, которого нет» (T25): 3 (x) × 3.5 (y) × 4 (z) блока, стыкуется подряд вдоль +z; '
                               'в середине — по двери на каждой стене (закрыты). Код ставит модули вокруг жертвы и «едет» ими вместе '
                               'с ней (коридор бесконечный), видит только жертва. Материалы для своей отрисовки — textures/fx/nightmare_*.',
         [{'type': 'boxes', 'tones': tones, 'glowTones': [], 'blend': 'translucent', 'opacity': 1.0, 'shade': True, 'boxes': b + lamp,
           'appear': {'delay': 0, 'duration': 16, 'easing': 'easeOutCubic', 'reveal': 'down', 'front': 0.8}, 'bounds': [-0.15, 3.65]},
          {'type': 'boxes', 'tones': tones, 'glowTones': [11], 'blend': 'additive', 'opacity': 0.9, 'shade': False, 'boxes': glow,
           'appear': {'delay': 8, 'duration': 10, 'easing': 'easeOutCubic', 'reveal': 'down', 'front': 0.3}, 'bounds': [2.7, 2.9]}],
         formed=16, collapse=14)


def mesh_door():
    """Створка двери 1×2.2 (петля у x = −0.5, ручка у x = +0.35; лицом к −z) — для nightmare_house_shadow (поворот на петле — hinge)."""
    T0, T1, KN, INKT = 0, 1, 2, 3
    b = [bx(-0.5, 0, -0.04, 0.5, 2.2, 0.04, T0)]
    for (y0, y1) in ((0.12, 1.0), (1.15, 2.08)):
        b.append(bx(-0.4, y0, -0.05, 0.4, y1, -0.04, T1))
        b.append(bx(-0.4, y0, 0.04, 0.4, y1, 0.05, T1))
    b += [bx(0.3, 1.0, -0.1, 0.4, 1.08, -0.04, KN), bx(0.3, 1.0, 0.04, 0.4, 1.08, 0.1, KN)]
    for k in range(4):
        x = -0.35 + k * 0.22
        b.append(bx(x, 0, -0.045, x + 0.03, 0.2 + 0.25 * (k % 2), -0.04, INKT))
    mesh('nightmare_door', 'Створка двери «Дома» (T25): 1×2.2, петля у x = −0.5 (hinge pivot [−0.5, 0, 0]), лицом к −z.',
         [{'type': 'boxes', 'tones': ['#2E1C12', '#22140C', '#8A7040', '#07030A'], 'glowTones': [], 'blend': 'translucent', 'opacity': 1.0,
           'shade': True, 'boxes': b, 'appear': {'delay': 0, 'duration': 4, 'easing': 'easeOutCubic', 'reveal': 'down', 'front': 0.4},
           'bounds': [0, 2.2]}], formed=4, collapse=8)


def mesh_branches():
    """Голые скрюченные ветви (стадия 3: деревья «голые и скрюченные»): кластер ветвей радиусом ~2.5, высота 3, от точки (0,0,0) —
    ставить на верх ствола вместо листвы (листву код прячет/делает почти прозрачной текстурой leaves_dead)."""
    rng = random.Random(2590)
    b = []

    def branch(p, d, L, w, depth):
        if depth == 0 or L < 0.15:
            return
        n = 4
        cur = np.array(p, float)
        dd = np.array(d, float)
        for k in range(n):
            dd = dd + np.array([rng.uniform(-0.45, 0.45), rng.uniform(-0.25, 0.35), rng.uniform(-0.45, 0.45)])
            dd = dd / np.linalg.norm(dd)
            nxt = cur + dd * L / n
            b.append(bar(cur, nxt, w * (1 - 0.15 * k), tone=0 if depth > 1 else 1))
            cur = nxt
            if k in (1, 3) and depth > 1:
                side = np.cross(dd, [0, 1, 0])
                side = side / max(1e-6, np.linalg.norm(side)) * rng.choice([-1, 1])
                branch(cur, dd * 0.5 + side * 0.8 + [0, 0.3, 0], L * 0.55, w * 0.6, depth - 1)
        branch(cur, dd, L * 0.5, w * 0.55, depth - 1)
    for k in range(5):
        a = TAU * k / 5 + rng.uniform(-0.3, 0.3)
        branch((0, 0, 0), (math.cos(a) * 0.7, 1.0, math.sin(a) * 0.7), 1.8, 0.16, 3)
    mesh('nightmare_branches', 'Голые скрюченные ветви (T25, стадия 3): кластер ~2.5 бл., от (0,0,0) вверх-в стороны; на верх ствола '
                               'вместо листвы (только у жертвы).',
         [{'type': 'boxes', 'tones': ['#1E1618', '#2A2024'], 'glowTones': [], 'blend': 'translucent', 'opacity': 1.0, 'shade': True,
           'boxes': b, 'appear': {'delay': 0, 'duration': 20, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.6}, 'bounds': [-0.1, 3.5]}],
         formed=20, collapse=12)
    return len(b)


def meshes():
    mesh_corridor()
    mesh_door()
    mesh_branches()


# ================================================================== иконки
def _c(h, a=255):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)


def _icon(size, draw, out, frame=None, k=8, crisp=False):
    """Рисуем в k× и уменьшаем LANCZOS (как gen_illusion_fx). frame: ('sq'|'round', обод, фон)."""
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
    if crisp:
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


def _eye(d, S, cx, cy, w, h, white, iris, pupil, lw=0.04, outline=None):
    up = [(cx - w + 2 * w * i / 20, cy - h * math.sin(math.pi * i / 20)) for i in range(21)]
    dn = [(cx + w - 2 * w * i / 20, cy + h * math.sin(math.pi * i / 20)) for i in range(21)]
    _poly(d, S, up + dn, fill=white, outline=outline, w=lw)
    r = h * 0.85
    d.ellipse([S * (cx - r), S * (cy - r), S * (cx + r), S * (cy + r)], fill=iris)
    d.ellipse([S * (cx - r * 0.28), S * (cy - r * 0.85), S * (cx + r * 0.28), S * (cy + r * 0.85)], fill=pupil)


def _drip(d, S, x, y0, L, w, col):
    d.line([S * x, S * y0, S * x, S * (y0 + L)], fill=col, width=max(1, int(S * w)))
    d.ellipse([S * (x - w * 0.9), S * (y0 + L - w * 0.6), S * (x + w * 0.9), S * (y0 + L + w * 1.2)], fill=col)


def icon_house(d, S):
    """«Дом, которого нет»: коридор в перспективе — проёмы сходятся к тёмной двери, из щели свет-багрянец, капли с потолка."""
    for k in range(4):
        s = 0.6 * 0.68 ** k
        x0, x1 = 0.5 - s / 2, 0.5 + s / 2
        y0, y1 = 0.5 - s * 0.55, 0.5 + s * 0.5
        d.rectangle([S * x0, S * y0, S * x1, S * y1], outline=_c(PALE if k < 2 else '#9A8C98'), width=max(1, int(S * (0.05 - 0.01 * k))))
    d.rectangle([S * 0.44, S * 0.42, S * 0.56, S * 0.62], fill=_c('#05020A'))
    d.line([S * 0.555, S * 0.42, S * 0.555, S * 0.62], fill=_c(BLOOD), width=max(1, int(S * 0.025)))
    for x in (0.36, 0.6):
        _drip(d, S, x, 0.17, 0.1, 0.03, _c(BLOOD))


def icon_night(d, S):
    """«Ночь без рассвета»: огромная красная луна, кровь стекает, чёрные силуэты деревьев внизу."""
    d.ellipse([S * 0.22, S * 0.14, S * 0.78, S * 0.7], fill=_c('#C8203A'))
    d.ellipse([S * 0.36, S * 0.26, S * 0.5, S * 0.38], fill=_c('#8A1028'))
    d.ellipse([S * 0.52, S * 0.44, S * 0.64, S * 0.54], fill=_c('#8A1028'))
    for x, L in ((0.36, 0.14), (0.5, 0.2), (0.62, 0.12)):
        _drip(d, S, x, 0.62, L, 0.03, _c('#C8203A'))
    _poly(d, S, [(0.06, 0.94), (0.12, 0.72), (0.16, 0.8), (0.22, 0.66), (0.28, 0.82), (0.36, 0.76), (0.42, 0.9), (0.58, 0.88), (0.66, 0.74),
                 (0.72, 0.84), (0.8, 0.7), (0.86, 0.8), (0.94, 0.94)], fill=_c('#05020A'))


def icon_abyss(d, S):
    """«Пробуждение не наступит»: закрытый глаз, из него чернильный поток вниз; вокруг — циферблат без стрелок."""
    d.ellipse([S * 0.12, S * 0.12, S * 0.88, S * 0.88], outline=_c(PALE), width=max(1, int(S * 0.05)))
    for i in range(12):
        a = TAU * i / 12
        d.line([S * (0.5 + 0.38 * math.cos(a)), S * (0.5 + 0.38 * math.sin(a)), S * (0.5 + 0.31 * math.cos(a)), S * (0.5 + 0.31 * math.sin(a))],
               fill=_c(PALE, 200), width=max(1, int(S * 0.03)))
    pts = [(0.26 + 0.48 * i / 20, 0.44 + 0.13 * math.sin(math.pi * i / 20)) for i in range(21)]
    d.line([(S * x, S * y) for x, y in pts], fill=_c(BLOOD), width=max(1, int(S * 0.06)))
    for k in range(5):
        x = 0.31 + 0.095 * k
        d.line([S * x, S * (0.5 + 0.08 * math.sin(math.pi * (k + 0.5) / 5)), S * (x - 0.02), S * 0.64], fill=_c(BLOOD), width=max(1, int(S * 0.03)))
    _poly(d, S, [(0.44, 0.58), (0.56, 0.58), (0.6, 0.92), (0.4, 0.92)], fill=_c('#05020A'))


def effect_icon(d, S, kind):
    if kind == 'immersion_1':                                   # тень-рука тянется снизу: ладонь и четыре длинных пальца
        _poly(d, S, [(0.3, 1.0), (0.34, 0.62), (0.66, 0.62), (0.7, 1.0)], fill=_c('#120814'), outline=_c(CRIMSON), w=0.05)
        for k, (x, top) in enumerate(((0.3, 0.2), (0.44, 0.06), (0.58, 0.1), (0.72, 0.24))):
            d.line([S * (0.36 + 0.09 * k), S * 0.64, S * x, S * top], fill=_c(CRIMSON), width=max(1, int(S * 0.13)))
            d.line([S * (0.36 + 0.09 * k), S * 0.64, S * x, S * top], fill=_c('#120814'), width=max(1, int(S * 0.07)))
        d.line([S * 0.32, S * 0.74, S * 0.14, S * 0.5], fill=_c(CRIMSON), width=max(1, int(S * 0.12)))
        d.line([S * 0.32, S * 0.74, S * 0.14, S * 0.5], fill=_c('#120814'), width=max(1, int(S * 0.06)))
    elif kind == 'immersion_2':                                 # глаз из тьмы
        d.ellipse([S * 0.04, S * 0.2, S * 0.96, S * 0.8], fill=_c('#120814'))
        _eye(d, S, 0.5, 0.5, 0.36, 0.18, _c(PALE), _c(BLOOD), _c('#05020A'), outline=_c('#05020A'))
    elif kind in ('immersion_3', 'no_awakening'):               # глаз плачет чернилами
        _eye(d, S, 0.5, 0.36, 0.42, 0.2, _c(PALE), _c(BLOOD), _c('#05020A'), outline=_c('#05020A'))
        for x, L in ((0.36, 0.42), (0.5, 0.56), (0.64, 0.36)):
            _drip(d, S, x, 0.5, L * 0.8, 0.07, _c('#120614'))
        if kind == 'no_awakening':
            d.ellipse([S * 0.02, S * 0.02, S * 0.98, S * 0.98], outline=_c('#B473FF'), width=max(1, int(S * 0.06)))
    elif kind == 'endless_night':
        d.ellipse([S * 0.14, S * 0.08, S * 0.86, S * 0.8], fill=_c('#C8203A'))
        d.ellipse([S * 0.36, S * 0.2, S * 0.52, S * 0.36], fill=_c('#8A1028'))
        for x, L in ((0.34, 0.16), (0.5, 0.2), (0.66, 0.14)):
            _drip(d, S, x, 0.74, L, 0.06, _c('#C8203A'))
    elif kind == 'house_that_isnt':
        icon_house(d, S)


def school_icon(d, S):
    """Значок школы: в тёмном ромбе — месяц-колыбель, над ним око, из ока — капля."""
    _poly(d, S, [(0.5, 0.04), (0.96, 0.5), (0.5, 0.96), (0.04, 0.5)], fill=_c('#0A0610'), outline=_c(CRIMSON), w=0.07)
    up = [(0.5 + 0.24 * math.cos(t), 0.6 + 0.2 * math.sin(t)) for t in np.linspace(0.2, math.pi - 0.2, 20)]
    dn = [(0.5 + 0.2 * math.cos(t), 0.56 + 0.15 * math.sin(t)) for t in np.linspace(math.pi - 0.25, 0.25, 20)]
    _poly(d, S, up + dn, fill=_c(PALE))
    _eye(d, S, 0.5, 0.38, 0.2, 0.1, _c(PALE), _c(BLOOD), _c('#05020A'))
    _drip(d, S, 0.5, 0.46, 0.16, 0.05, _c(BLOOD))


def lullaby_icon(d, S):
    """«Сломанная колыбельная»: треснувшая музыкальная шкатулка (тёмное дерево, латунный ключ сбоку), крышка приоткрыта,
    внутри видна гребёнка, по корпусу трещина и стекают чернила; над крышкой — сломанная нота."""
    _poly(d, S, [(0.12, 0.5), (0.86, 0.5), (0.86, 0.9), (0.12, 0.9)], fill=_c('#3A2418'), outline=_c('#120806'), w=0.05)   # корпус
    _poly(d, S, [(0.1, 0.5), (0.88, 0.5), (0.82, 0.3), (0.16, 0.3)], fill=_c('#4A2E1E'), outline=_c('#120806'), w=0.05)    # крышка открыта
    _poly(d, S, [(0.18, 0.5), (0.8, 0.5), (0.76, 0.42), (0.22, 0.42)], fill=_c('#120806'))
    for k in range(6):                                           # гребёнка (латунь)
        x = 0.26 + k * 0.09
        d.line([S * x, S * 0.5, S * x, S * (0.44 + 0.01 * k)], fill=_c('#C8A860'), width=max(1, int(S * 0.03)))
    d.rectangle([S * 0.86, S * 0.62, S * 0.96, S * 0.68], fill=_c('#C8A860'))                                      # ключ
    d.rectangle([S * 0.92, S * 0.54, S * 0.98, S * 0.76], fill=_c('#8A7040'))
    d.line([S * 0.5, S * 0.5, S * 0.46, S * 0.66, S * 0.54, S * 0.74, S * 0.5, S * 0.9], fill=_c('#05020A'), width=max(1, int(S * 0.04)))  # трещина
    _drip(d, S, 0.3, 0.88, 0.08, 0.04, _c('#05020A'))
    _drip(d, S, 0.7, 0.88, 0.06, 0.04, _c('#05020A'))
    d.ellipse([S * 0.38, S * 0.18, S * 0.5, S * 0.27], fill=_c(BLOOD))                                             # нота
    d.line([S * 0.49, S * 0.22, S * 0.49, S * 0.06], fill=_c(BLOOD), width=max(1, int(S * 0.04)))
    d.line([S * 0.49, S * 0.06, S * 0.58, S * 0.12], fill=_c(BLOOD), width=max(1, int(S * 0.04)))


def icons():
    rd, my = ('round', '#FF3B3B', '#10060E'), ('sq', '#B473FF', '#0D0716')
    for name, fn, fr in (('house_that_isnt', icon_house, rd), ('endless_night', icon_night, rd), ('no_awakening', icon_abyss, my)):
        _icon(16, fn, 'textures/gui/spell_icons/%s.png' % name, frame=fr)
    for kind in ('immersion_1', 'immersion_2', 'immersion_3', 'endless_night', 'no_awakening', 'house_that_isnt'):
        _icon(18, lambda d, S, k=kind: effect_icon(d, S, k), 'textures/mob_effect/%s.png' % kind, crisp=True)
    _icon(16, school_icon, 'textures/gui/school/nightmare.png', crisp=True)
    _icon(16, lullaby_icon, 'textures/item/broken_lullaby.png', crisp=True)
    write('models/item/broken_lullaby.json', {'parent': 'item/generated', 'textures': {'layer0': 'pohsmp_core:item/broken_lullaby'}})


# ================================================================== lang
LANG = {
    'school.pohsmp_core.nightmare': ('Кошмары', 'Nightmares'),
    'attribute.pohsmp_core.nightmare_spell_power': ('Сила кошмаров', 'Nightmare Spell Power'),
    'attribute.pohsmp_core.nightmare_magic_resist': ('Стойкость рассудка', 'Sanity'),
    'item.pohsmp_core.broken_lullaby': ('Сломанная колыбельная', 'Broken Lullaby'),
    'item.pohsmp_core.broken_lullaby.desc': ('Треснувшая музыкальная шкатулка: фокус школы «Кошмары» для стола надписей',
                                             'A cracked music box: the Nightmares school focus for the inscription table'),
    'death.attack.nightmare_magic': ('%1$s не проснулся', '%1$s never woke up'),
    'death.attack.nightmare_magic.item': ('%1$s не проснулся: %2$s наслал кошмар с помощью %3$s', '%1$s never woke up from %2$s\'s nightmare using %3$s'),
    'death.attack.nightmare_magic.player': ('%1$s не проснулся, убегая от %2$s', '%1$s never woke up while fleeing %2$s'),
    'spell.pohsmp_core.house_that_isnt': ('Дом, которого нет', 'The House That Isn\'t'),
    'spell.pohsmp_core.house_that_isnt.guide': (
        'Цель проваливается в бесконечный тёмный коридор с дверями — на минуту настоящий мир для неё исчезает. Из дверей выходят тени и бьют '
        'её; заклинатель видит цель и бьёт по-настоящему, а для неё он — лишь одна из теней. После выхода кошмар не отпускает.',
        'The target falls into an endless dark corridor of doors — for a minute the real world is gone for them. Shadows step out of the doors '
        'and strike; the caster sees the target and strikes for real, yet to them is just another shadow. The nightmare lingers after.'),
    'spell.pohsmp_core.endless_night': ('Ночь без рассвета', 'Night Without Dawn'),
    'spell.pohsmp_core.endless_night.guide': (
        'Две минуты над врагами в круге стоит вечная ночь под красной луной, и каждые восемь секунд кошмар становится глубже. Удержаться можно '
        'только у настоящего света.',
        'For two minutes enemies in the circle live under an eternal night and a red moon, and every eight seconds the nightmare deepens. '
        'Only real light holds it back.'),
    'spell.pohsmp_core.no_awakening': ('Пробуждение не наступит', 'No Awakening'),
    'spell.pohsmp_core.no_awakening.guide': (
        'Мир тонет в чернилах. Пять минут все враги вокруг живут в худшем кошмаре, собранном из мест, где они были: чудовища охотятся, '
        'союзники предают, имена людей исчезают — и каждую минуту становится хуже. Самое страшное чудовище — сам заклинатель. '
        'Проснуться можно, только убив его.',
        'The world drowns in ink. For five minutes every enemy around lives in their worst nightmare, built from the places they have been: '
        'monsters hunt, allies betray, names vanish — and every minute it gets worse. The most terrible monster is the caster. '
        'The only way to wake is to kill them.'),
    'effect.pohsmp_core.immersion': ('Погружение', 'Immersion'),
    'effect.pohsmp_core.immersion.description': ('Мир вокруг становится кошмаром: тени, затем галлюцинации, затем сам кошмар. Спадает, если '
                                                 'двадцать секунд не попадать под новые чары.',
                                                 'The world turns into a nightmare: shadows, then hallucinations, then the nightmare itself. '
                                                 'Fades after twenty seconds without new spells.'),
    'effect.pohsmp_core.endless_night': ('Ночь без рассвета', 'Night Without Dawn'),
    'effect.pohsmp_core.endless_night.description': ('Вечная ночь и красная луна; кошмар глубже каждые 8 с. Держитесь у света.',
                                                     'Eternal night and a red moon; the nightmare deepens every 8 s. Stay near light.'),
    'effect.pohsmp_core.no_awakening': ('Пробуждение не наступит', 'No Awakening'),
    'effect.pohsmp_core.no_awakening.description': ('Худший кошмар. Не верь никому. Убей того, кто его наслал.',
                                                    'The worst nightmare. Trust no one. Kill the one who cast it.'),
    'effect.pohsmp_core.house_that_isnt': ('Дом, которого нет', 'The House That Isn\'t'),
    'effect.pohsmp_core.house_that_isnt.description': ('Вокруг только коридор и двери. Из дверей выходят тени.',
                                                       'Only a corridor and doors. Shadows come out of the doors.'),
    'fx.pohsmp_core.no_awakening.title': ('Пробуждение не наступит', 'No Awakening'),
    'ui.pohsmp_core.nightmare.stage': ('Погружение: %s', 'Immersion: %s'),
    'ui.pohsmp_core.nightmare.stage.1': ('тени', 'shadows'),
    'ui.pohsmp_core.nightmare.stage.2': ('галлюцинации', 'hallucinations'),
    'ui.pohsmp_core.nightmare.stage.3': ('кошмар', 'nightmare'),
    'ui.pohsmp_core.nightmare.resisted': ('Рассудок устоял', 'Your mind held'),
    'ui.pohsmp_core.nightmare.no_target': ('Нет цели', 'No target'),
    'ui.pohsmp_core.nightmare.light_holds': ('Свет удерживает кошмар', 'The light holds the nightmare back'),
    'ui.pohsmp_core.house_that_isnt.time': ('Дом: %s с', 'House: %s s'),
    'ui.pohsmp_core.endless_night.zone': ('Ночь: радиус %s, %s с', 'Night: radius %s, %s s'),
    'ui.pohsmp_core.no_awakening.cast': ('Мир тонет…', 'The world is drowning…'),
    'ui.pohsmp_core.no_awakening.time': ('Кошмар: %s с', 'Nightmare: %s s'),
    'ui.pohsmp_core.no_awakening.thicken.1': ('Кошмар сгущается', 'The nightmare thickens'),
    'ui.pohsmp_core.no_awakening.thicken.2': ('Не верь своим', 'Do not trust your own'),
    'ui.pohsmp_core.no_awakening.thicken.3': ('Имена исчезают', 'Names are fading'),
    'ui.pohsmp_core.no_awakening.thicken.4': ('Пробуждение не наступит', 'There will be no awakening'),
    'entity.pohsmp_core.nm_lurker': ('Тень-за-углом', 'Lurker'),
    'entity.pohsmp_core.nm_crawler': ('Ползун', 'Crawler'),
    'entity.pohsmp_core.nm_mimic': ('Мимик', 'Mimic'),
    'entity.pohsmp_core.nm_hollow_child': ('Пустой ребёнок', 'Hollow Child'),
    'entity.pohsmp_core.nm_hands': ('Руки из земли', 'Grasping Hands'),
    'entity.pohsmp_core.nm_maw': ('Пасть', 'Maw'),
    'entity.pohsmp_core.nm_weeper': ('Плакальщица', 'Weeper'),
    'entity.pohsmp_core.nm_moth': ('Мотыльки-глаза', 'Eye Moths'),
    'entity.pohsmp_core.nm_dread': ('Ужас', 'Dread'),
}


def lang():
    for code, idx in (('ru_ru', 0), ('en_us', 1)):
        path = os.path.join(A, 'lang', code + '.json')
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
        for k, v in LANG.items():
            data[k] = v[idx]
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
        WRITTEN.append('lang/%s.json' % code)


def main():
    args = sys.argv[1:]
    textures()
    style()
    school_sigils()
    spell_sigils()
    school_fx()
    stage_fx()
    spell_fx()
    meshes()
    icons()
    lang()
    if '--no-beasts' not in args:
        import gen_nightmare_bestiary as gb
        gb.main()
        WRITTEN.extend(gb.WRITTEN)
    if '--sheet' in args:
        sheet_textures(os.path.join(HERE, '..', 'docs', 'media', 't25_nightmare_textures.jpg'))
    print('T25: записано файлов:', len(WRITTEN))


if __name__ == '__main__':
    main()


def sheet_icons(path):
    """Иконки ×8 (nearest) на тёмном и светлом фоне."""
    A_ = lambda r: os.path.join(A, r)
    files = ['textures/gui/school/nightmare.png', 'textures/item/broken_lullaby.png'] + \
        ['textures/gui/spell_icons/%s.png' % n for n in ('house_that_isnt', 'endless_night', 'no_awakening')] + \
        ['textures/mob_effect/%s.png' % n for n in ('immersion_1', 'immersion_2', 'immersion_3', 'endless_night', 'no_awakening', 'house_that_isnt')]
    k = 8
    W = sum(Image.open(A_(f)).width * k + 16 for f in files) + 16
    out = Image.new('RGB', (W, 2 * (18 * k + 16) + 16), (20, 14, 24))
    x = 16
    for f in files:
        im = Image.open(A_(f)).convert('RGBA')
        big = im.resize((im.width * k, im.height * k), Image.NEAREST)
        for row, bg in enumerate(((20, 14, 24), (198, 198, 198))):
            tile = Image.new('RGBA', big.size, bg + (255,))
            tile.alpha_composite(big)
            out.paste(tile.convert('RGB'), (x, 16 + row * (18 * k + 16)))
        x += big.width + 16
    out.save(path)
    print('sheet', path)
