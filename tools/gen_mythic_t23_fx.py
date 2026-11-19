#!/usr/bin/env python3
"""
T23 — визуал трёх Мифических: «Древо мира» (world_tree, природа), «Око бездны» (abyss_eye, мистическая), «Последний рассвет»
(last_dawn, святая). ТЗ: docs/specs/tasks/T23_mythic_four.md («Чёрное солнце» отменено). Каст 12 / 12 / 10 с, ролик камеры у каждого.
Правила владельца: никаких лучей/нитей от заклинателя к цели; блоки мира не меняются (всё — модели и эффекты).

Пишет (src/main/resources/assets/pohsmp_core/):
  textures/sigil/yggdrasil.png, abyss_sigil.png, abyss_swirl.png, dawn_sunrise.png, mote_cloud.png, mote_petal.png
  sigils/world_tree_*.json, abyss_*.json, dawn_*.json
  fx/meshes/world_tree.json (ствол, ветви, корни у основания — рост снизу вверх по секциям), world_tree_crown.json (крона),
           world_tree_bloom.json (цветы финала), world_tree_root.json (корень-щупальце), abyss_eye.json (глазное яблоко, раскрывается
           от щели к краям), abyss_eye_lids.json (веки, «ресницы»-щупальца), abyss_eye_pupil.json (зрачок — отдельно, код двигает/крутит),
           dawn_sun.json (солнце с короной лучей)
  fx/styles/world_tree.json, abyss_eye.json, last_dawn.json; fx/world_tree_*.json, abyss_eye_*.json, last_dawn_*.json
  textures/gui/spell_icons/<id>.png (16×16), textures/mob_effect/entangled.png, abyss_dread.png, dawn_grace.png (18×18)

Время — тики, углы — градусы, размеры — блоки. Запуск:  python3 tools/gen_mythic_t23_fx.py [--sheet out.png]
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
import gen_forbidden_fx as F  # noqa: E402  (общие помощники: печати, эффекты, иконки, мазки)

A = F.A
OUT_SIGIL = F.OUT_SIGIL
WRITTEN = F.WRITTEN
ap, L, T, sigil, fx, E, ease, off, fmt = F.ap, F.L, F.T, F.sigil, F.fx, F.E, F.ease, F.off, F.fmt
_pline, _polar_glyph, _c = F._pline, F._polar_glyph, F._c

# палитры
N_GREEN, N_LIGHT, N_GOLD, N_BARK, N_PINK = '#7EE04A', '#D8FF9A', '#FFE38A', '#5A3A20', '#FFB8E0'
E_TEAL, E_PALE, E_MAG, E_DARK, E_VOID = '#3FD6B8', '#B8FFF0', '#C02A6A', '#1A0A2A', '#07040C'
H_GOLD, H_PALE, H_WHITE, H_ROSE, H_AMBER = '#FFD36B', '#FFF4D6', '#FFFFFF', '#FFB38A', '#FF9A3A'


# ================================================================== текстуры
def tex_yggdrasil():
    """Древо мира: в круге — дерево, крона кругом наверху и зеркальные корни внизу; девять малых кругов-миров на ветвях и корнях;
    обод с лозой из листьев, кольцо рун."""
    img = canvas()
    d = ImageDraw.Draw(img)
    rng = random.Random(23)
    ring(d, C * 0.985, 6 * SS)
    ring(d, C * 0.955, 2 * SS)
    for i in range(48):                                         # лоза: листья по ободу
        a = 2 * math.pi * i / 48
        x, y = polar(C * 0.915, a)
        la = a + (0.9 if i % 2 else -0.9)
        L_ = C * 0.04
        pts = []
        for k in range(13):
            t = k / 12
            w = math.sin(math.pi * t) * L_ * 0.38
            px = x + math.cos(la) * L_ * (t - 0.5) * 2 - math.sin(la) * w
            py = y + math.sin(la) * L_ * (t - 0.5) * 2 + math.cos(la) * w
            pts.append((px, py))
        for k in range(12, -1, -1):
            t = k / 12
            w = math.sin(math.pi * t) * L_ * 0.38
            pts.append((x + math.cos(la) * L_ * (t - 0.5) * 2 + math.sin(la) * w, y + math.sin(la) * L_ * (t - 0.5) * 2 - math.cos(la) * w))
        d.polygon(pts, fill=255)
    ring(d, C * 0.87, 3 * SS)
    for i in range(40):
        _polar_glyph(d, C * 0.815, 2 * math.pi * i / 40, C * 0.07, C * 0.045, rng, 3.2 * SS)
    ring(d, C * 0.76, 3 * SS)
    # ствол
    tw = C * 0.05
    d.polygon([(C - tw, C - C * 0.28), (C + tw, C - C * 0.28), (C + tw * 1.4, C + C * 0.28), (C - tw * 1.4, C + C * 0.28)], fill=255)

    def branch(x, y, a, length, width, depth, sign):
        if depth == 0 or length < C * 0.04:
            return
        pts = []
        for k in range(16):
            t = k / 15
            aa = a + sign * 0.35 * t
            pts.append((x + math.cos(aa) * length * t, y + math.sin(aa) * length * t))
        d.line(pts, fill=255, width=max(2, int(width)), joint='curve')
        ex, ey = pts[-1]
        aa = a + sign * 0.35
        branch(ex, ey, aa - 0.45, length * 0.62, width * 0.62, depth - 1, sign)
        branch(ex, ey, aa + 0.45, length * 0.62, width * 0.62, depth - 1, sign)
    for s in (-1, 1):                                            # крона (вверх) и корни (вниз), зеркально
        y0 = C - s * C * 0.24
        for a0 in (-0.55, 0.0, 0.55):
            branch(C, y0, -s * math.pi / 2 + a0 * 1.6, C * 0.2, 7 * SS, 3, 1 if a0 >= 0 else -1)
    ring(d, C * 0.6, 2 * SS)
    worlds = [(0, -0.52), (-0.36, -0.38), (0.36, -0.38), (-0.5, 0.0), (0.5, 0.0), (-0.36, 0.38), (0.36, 0.38), (0, 0.52), (0, 0)]
    for x, y in worlds:                                          # девять миров
        cx, cy = C + x * C, C + y * C
        R = C * (0.065 if (x, y) != (0, 0) else 0.09)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=0, outline=255, width=4 * SS)
        d.ellipse([cx - R * 0.35, cy - R * 0.35, cx + R * 0.35, cy + R * 0.35], fill=255)
    save(img, 'yggdrasil')


def tex_abyss_sigil():
    """Око бездны: в центре миндаль глаза со щелью зрачка, вокруг — шесть изогнутых щупалец-спиралей, кольцо из восьми малых глаз,
    рваный внешний обод."""
    img = canvas()
    d = ImageDraw.Draw(img)
    rng = random.Random(66)
    for i in range(90):                                          # рваный обод: зубья разной длины
        a = 2 * math.pi * i / 90
        r1 = C * (0.97 - 0.05 * rng.random())
        d.line([*polar(C * 0.9, a), *polar(r1, a)], fill=255, width=3 * SS)
    ring(d, C * 0.9, 4 * SS)
    for k in range(8):                                           # малые глаза
        a = 2 * math.pi * k / 8 + math.pi / 8
        cx, cy = polar(C * 0.78, a)
        ew, eh = C * 0.075, C * 0.04
        pts = [(cx + ew * math.cos(t) * math.cos(a + math.pi / 2) - eh * math.sin(t) * math.sin(a + math.pi / 2) * (1 if t < math.pi else 1),
                cy + ew * math.cos(t) * math.sin(a + math.pi / 2) + eh * math.sin(t) * math.cos(a + math.pi / 2)) for t in np.linspace(0, 2 * math.pi, 40)]
        d.line(pts, fill=255, width=3 * SS, joint='curve')
        d.ellipse([cx - eh * 0.6, cy - eh * 0.6, cx + eh * 0.6, cy + eh * 0.6], fill=255)
    ring(d, C * 0.68, 3 * SS)
    for k in range(6):                                           # щупальца-спирали от центра к кольцу
        a0 = 2 * math.pi * k / 6
        pts = []
        for j in range(60):
            t = j / 59
            r = C * (0.2 + 0.46 * t)
            a = a0 + 2.2 * t ** 1.2
            pts.append(polar(r, a))
        for j in range(len(pts) - 1):
            w = (9 - 7 * j / len(pts)) * SS
            d.line([pts[j], pts[j + 1]], fill=255, width=int(w))
        for j in range(8, 56, 7):                                # присоски
            x, y = pts[j]
            q = (4 - 3 * j / 60) * SS
            d.ellipse([x - q * 1.8, y - q * 1.8, x + q * 1.8, y + q * 1.8], outline=255, width=max(2, int(q * 0.6)))
    ring(d, C * 0.2, 4 * SS)
    ew, eh = C * 0.17, C * 0.09                                  # центральный глаз
    top = [(C + ew * math.cos(t), C - eh * math.sin(t)) for t in np.linspace(0, math.pi, 30)]
    bot = [(C + ew * math.cos(t), C - eh * math.sin(t)) for t in np.linspace(math.pi, 2 * math.pi, 30)]
    d.polygon(top + bot, fill=255)
    d.ellipse([C - eh * 0.85, C - eh * 0.85, C + eh * 0.85, C + eh * 0.85], fill=0)
    d.ellipse([C - eh * 0.7, C - eh * 0.7, C + eh * 0.7, C + eh * 0.7], outline=255, width=3 * SS)
    d.ellipse([C - eh * 0.16, C - eh * 0.62, C + eh * 0.16, C + eh * 0.62], fill=255)
    save(img, 'abyss_sigil')


def tex_abyss_swirl():
    """Тучи над Оком: логарифмическая спираль из рваных облачных рукавов, к центру плотнее, в центре — тёмный провал."""
    S = 1024
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    x, y = (xx - S / 2) / (S / 2), (yy - S / 2) / (S / 2)
    r = np.hypot(x, y) + 1e-6
    a = np.arctan2(y, x)
    nz1 = np.asarray(Image.effect_noise((64, 64), 80).resize((S, S), Image.BICUBIC), np.float32) / 255.0
    nz2 = np.asarray(Image.effect_noise((256, 256), 60).resize((S, S), Image.BICUBIC), np.float32) / 255.0
    arms = 5
    phase = arms * (a + 2.4 * np.log(r)) + 3.0 * (nz1 - 0.5)
    band = (0.5 + 0.5 * np.cos(phase)) ** 2.2
    v = band * (0.55 + 0.6 * (nz2 - 0.5) + 0.4 * nz1)
    v *= np.clip((1.0 - r) / 0.25, 0, 1) * np.clip((r - 0.12) / 0.2, 0, 1)
    v = np.clip(v * 1.4, 0, 1)
    img = Image.fromarray((v * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(1.5)).resize((512, 512), Image.LANCZOS)
    rgba = Image.new('RGBA', (512, 512), (255, 255, 255, 0))
    rgba.putalpha(img)
    rgba.save(os.path.join(OUT_SIGIL, 'abyss_swirl.png'))


def tex_dawn_sunrise():
    """Рассвет: линия горизонта через центр, над ней половина солнца с веером из 13 лучей, под ней — бледное отражение пунктиром;
    обод с двенадцатью малыми солнцами, кольцо засечек."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.985, 6 * SS)
    ring(d, C * 0.95, 2 * SS)
    for i in range(12):
        a = 2 * math.pi * i / 12
        cx, cy = polar(C * 0.875, a)
        R = C * 0.035
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=255)
        for k in range(8):
            b = 2 * math.pi * k / 8
            d.line([cx + math.cos(b) * R * 1.4, cy + math.sin(b) * R * 1.4, cx + math.cos(b) * R * 2.0, cy + math.sin(b) * R * 2.0],
                   fill=255, width=2 * SS)
    ring(d, C * 0.8, 3 * SS)
    for i in range(96):
        a = 2 * math.pi * i / 96
        d.line([*polar(C * 0.77, a), *polar(C * (0.73 if i % 4 == 0 else 0.75), a)], fill=255, width=2 * SS)
    d.line([C - C * 0.74, C, C + C * 0.74, C], fill=255, width=5 * SS)          # горизонт
    R = C * 0.22
    d.pieslice([C - R, C - R, C + R, C + R], 180, 360, fill=255)              # солнце
    d.arc([C - R * 1.25, C - R * 1.25, C + R * 1.25, C + R * 1.25], 180, 360, fill=255, width=3 * SS)
    for k in range(13):                                                        # веер лучей
        a = math.pi + math.pi * (k + 0.5) / 13
        r1 = C * (0.7 if k % 2 == 0 else 0.52)
        w0 = 0.05 if k % 2 == 0 else 0.035
        d.polygon([polar(R * 1.4, a - w0), polar(R * 1.4, a + w0), polar(r1, a)], fill=255)
    for k in range(13):                                                        # отражение пунктиром
        a = math.pi * (k + 0.5) / 13
        r1 = C * (0.55 if k % 2 == 0 else 0.4)
        for t in np.arange(0.0, 1.0, 0.18):
            p0 = polar(R * 1.2 + (r1 - R * 1.2) * t, a)
            p1 = polar(R * 1.2 + (r1 - R * 1.2) * (t + 0.09), a)
            d.line([p0, p1], fill=150, width=3 * SS)
    d.arc([C - R, C - R, C + R, C + R], 0, 180, fill=150, width=3 * SS)
    save(img, 'dawn_sunrise')


def tex_motes():
    S = 128 * SS
    img = Image.new('L', (S, S), 0)                              # облачко: несколько кругов, сильно размытых
    d = ImageDraw.Draw(img)
    rng = random.Random(4)
    for k in range(9):
        x, y = S * (0.3 + rng.random() * 0.4), S * (0.38 + rng.random() * 0.26)
        q = S * (0.12 + rng.random() * 0.12)
        d.ellipse([x - q, y - q, x + q, y + q], fill=255)
    img = img.filter(ImageFilter.GaussianBlur(SS * 9))
    sm = img.resize((128, 128), Image.LANCZOS)
    rgba = Image.new('RGBA', (128, 128), (255, 255, 255, 0))
    rgba.putalpha(sm)
    rgba.save(os.path.join(OUT_SIGIL, 'mote_cloud.png'))
    img = Image.new('L', (S, S), 0)                              # лепесток: капля с выемкой на конце и жилкой
    d = ImageDraw.Draw(img)
    pts = []
    for k in range(41):
        t = k / 40
        w = math.sin(math.pi * t) ** 0.8 * (1 - 0.25 * t) * S * 0.26
        pts.append((S * 0.5 + w, S * 0.1 + S * 0.8 * t))
    pts += [(S - x, y) for x, y in reversed(pts)]
    d.polygon(pts, fill=255)
    d.polygon([(S * 0.44, S * 0.09), (S * 0.56, S * 0.09), (S * 0.5, S * 0.2)], fill=0)
    d.line([S * 0.5, S * 0.25, S * 0.5, S * 0.8], fill=150, width=3 * SS)
    sm = img.filter(ImageFilter.GaussianBlur(SS * 0.6)).resize((128, 128), Image.LANCZOS)
    rgba = Image.new('RGBA', (128, 128), (255, 255, 255, 0))
    rgba.putalpha(sm)
    rgba.save(os.path.join(OUT_SIGIL, 'mote_petal.png'))


def textures():
    tex_yggdrasil()
    tex_abyss_sigil()
    tex_abyss_swirl()
    tex_dawn_sunrise()
    tex_motes()
    for n in ('yggdrasil', 'abyss_sigil', 'abyss_swirl', 'dawn_sunrise', 'mote_cloud', 'mote_petal'):
        WRITTEN.append('textures/sigil/%s.png' % n)


# ================================================================== модели (fx/meshes, части boxes — docs/fx.md)
def _r(v):
    return round(float(v), 3)


def bar(p, q, w, d=None, tone=0):
    """Брусок вдоль отрезка p→q (сечение w×d), поворот [rx, ry, rz] (Euler YXZ): ось x бруска → направление p→q."""
    p, q = np.asarray(p, float), np.asarray(q, float)
    c = (p + q) / 2
    v = q - p
    l = float(np.linalg.norm(v))
    d = w if d is None else d
    v = v / max(l, 1e-9)
    rz = math.degrees(math.asin(max(-1.0, min(1.0, v[1]))))
    ry = math.degrees(math.atan2(-v[2], v[0]))
    return [_r(c[0] - l / 2), _r(c[1] - w / 2), _r(c[2] - d / 2), _r(c[0] + l / 2), _r(c[1] + w / 2), _r(c[2] + d / 2), tone,
            [0, round(ry, 1), round(rz, 1)]]


def box(c, sx, sy, sz, tone, rot=None):
    b = [_r(c[0] - sx / 2), _r(c[1] - sy / 2), _r(c[2] - sz / 2), _r(c[0] + sx / 2), _r(c[1] + sy / 2), _r(c[2] + sz / 2), tone]
    if rot:
        b.append([round(r, 1) for r in rot])
    return b


def bounds_y(boxes):
    return [_r(min(b[1] for b in boxes) - 0.05), _r(max(b[4] for b in boxes) + 0.05)]


def mesh(id, comment, style_, formed, collapse, parts):
    write_obj = {'comment': comment + ' Сгенерировано tools/gen_mythic_t23_fx.py.', 'style': style_, 'center': 0, 'formedAt': formed,
                 'collapse': {'duration': collapse, 'easing': 'easeInCubic'}, 'parts': parts}
    path = os.path.join(A, 'fx', 'meshes', id + '.json')          # компактно, как gen_silent_gate.py: модели большие
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(write_obj, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')
    WRITTEN.append('fx/meshes/%s.json' % id)
    return write_obj


def part(boxes, tones, glow, appear, opacity=0.95, shade=True):
    return {'type': 'boxes', 'tones': tones, 'glowTones': glow, 'blend': 'translucent', 'opacity': opacity, 'shade': shade,
            'boxes': boxes, 'appear': appear, 'bounds': bounds_y(boxes)}


def _path(p0, dirs, length, n, bend, rng):
    """Изогнутая ветвь: n точек от p0, направление поворачивается на bend (вектор) по длине, лёгкая случайная волна."""
    pts = [np.asarray(p0, float)]
    v = np.asarray(dirs, float)
    v = v / np.linalg.norm(v)
    step = length / n
    for k in range(n):
        v = v + np.asarray(bend, float) / n + np.array([rng.uniform(-0.08, 0.08), rng.uniform(-0.04, 0.06), rng.uniform(-0.08, 0.08)])
        v = v / np.linalg.norm(v)
        pts.append(pts[-1] + v * step)
    return pts


TREE_TONES = ['#2E1C10', '#4A2E18', '#6A4628', '#3E6A2A', '#B8FF7A']          # кора тёмная/средняя/светлая, мох, светящиеся жилы
CROWN_TONES = ['#1F5A22', '#2F7A2E', '#4FAE3A', '#7FD04E', '#D8FF9A']         # листва от тени к свету, светящиеся листья
BLOOM_TONES = ['#FFB8E0', '#FFE38A', '#FFFFFF']


def _trunk_center(y):
    return np.array([0.7 * math.sin(y / 9.0), y, 0.55 * math.sin(y / 7.0 + 1.0)])


def _trunk_r(y):
    return 3.1 * (1 - y / 36.0) + 0.7 + 2.4 * math.exp(-y / 1.7)


def gen_world_tree():
    """Исполинское дерево ~40 бл.: ствол из колец коры с закруткой и спиральными светящимися жилами, корни-«ноги» у основания,
    8 главных ветвей с отростками; крона — отдельной моделью (облака листвы на концах ветвей и купол сверху); цветы — третьей."""
    rng = random.Random(40)
    trunk, crown, bloom = [], [], []
    TOP = 25.0
    y = 0.0
    while y < TOP:                                               # кора: кольца брусков вдоль окружности
        c = _trunk_center(y + 0.5)
        r = _trunk_r(y + 0.5)
        n = max(9, int(2 * math.pi * r / 1.25))
        tw = y * 0.075
        for k in range(n):
            th = 2 * math.pi * k / n + tw
            tx, tz = -math.sin(th), math.cos(th)
            ry = math.degrees(math.atan2(-tz, tx))
            vein = any(abs(((th - y * 0.13 - 2 * math.pi * s / 5) + math.pi) % (2 * math.pi) - math.pi) < 0.11 for s in range(5))
            tone = 4 if vein else rng.choice([0, 1, 1, 2] if y > 2 else [0, 0, 1, 3])
            if not vein and y < 5 and rng.random() < 0.15:
                tone = 3
            rr = r - 0.3 + (0.08 if vein else rng.uniform(-0.06, 0.1))
            trunk.append(box((c[0] + rr * math.cos(th), c[1], c[2] + rr * math.sin(th)), 2 * math.pi * r / n * 1.1, 1.06,
                             0.75 if not vein else 0.5, tone, [0, ry, 0]))
        y += 1.0
    for k in range(9):                                           # корни-«ноги» у основания: дугой в землю
        a = 2 * math.pi * k / 9 + rng.uniform(-0.15, 0.15)
        L_ = rng.uniform(6.5, 10.0)
        prev = None
        for j in range(13):
            t = j / 12
            rad = 2.6 + L_ * t
            hgt = 2.6 * (1 - t) ** 1.4 + 0.5 * math.sin(math.pi * t) + 0.15
            p = np.array([rad * math.cos(a + 0.2 * t), hgt, rad * math.sin(a + 0.2 * t)])
            if prev is not None:
                w = 1.6 * (1 - t) + 0.35
                trunk.append(bar(prev, p, w, w * 0.9, 4 if (j % 4 == 0 and t < 0.8) else rng.choice([0, 1, 1, 3])))
            prev = p
    ends = []
    for k in range(8):                                           # главные ветви
        a = k * 2.39996 + 0.4
        ys = 13.5 + (k % 4) * 2.6 + rng.uniform(-0.6, 0.6)
        c = _trunk_center(ys)
        r = _trunk_r(ys)
        d0 = np.array([math.cos(a), rng.uniform(0.55, 0.9), math.sin(a)])
        pts = _path(c + np.array([math.cos(a), 0, math.sin(a)]) * r * 0.6, d0, rng.uniform(11, 14.5), 8,
                    np.array([math.cos(a) * 0.3, 0.25, math.sin(a) * 0.3]), rng)
        for j in range(len(pts) - 1):
            t = j / (len(pts) - 1)
            w = 1.5 * (1 - t) + 0.35
            trunk.append(bar(pts[j], pts[j + 1] + (pts[j + 1] - pts[j]) * 0.08, w, w, 4 if j in (2, 5) else rng.choice([1, 1, 2])))
        ends.append(pts[-1])
        for s in range(3):                                       # отростки
            j0 = rng.randint(3, 6)
            b = rng.uniform(-1, 1)
            dd = np.array([math.cos(a + b), rng.uniform(0.3, 1.0), math.sin(a + b)])
            sp = _path(pts[j0], dd, rng.uniform(4, 7), 4, np.array([0, 0.3, 0]), rng)
            for j in range(len(sp) - 1):
                w = 0.65 * (1 - j / len(sp)) + 0.2
                trunk.append(bar(sp[j], sp[j + 1] + (sp[j + 1] - sp[j]) * 0.1, w, w, rng.choice([1, 2])))
            ends.append(sp[-1])
    top = _trunk_center(TOP)                                     # макушка: несколько коротких ветвей вверх
    for k in range(5):
        a = 2 * math.pi * k / 5
        sp = _path(top, np.array([math.cos(a) * 0.5, 1, math.sin(a) * 0.5]), 6, 4, np.array([0, 0.2, 0]), rng)
        for j in range(len(sp) - 1):
            w = 0.9 * (1 - j / len(sp)) + 0.25
            trunk.append(bar(sp[j], sp[j + 1], w, w, rng.choice([1, 2])))
        ends.append(sp[-1])
    # крона: облака листвы вокруг концов ветвей и купол сверху
    clusters = [(e, rng.uniform(3.2, 4.6)) for e in ends] + [(np.array([0, 33.5, 0]), 6.5), (np.array([0, 29, 0]), 7.5)]
    for cen, R in clusters:
        n = int(R * R * 2.1)
        for _ in range(n):
            u = np.array([rng.gauss(0, 1), rng.gauss(0, 0.7), rng.gauss(0, 1)])
            u = u / np.linalg.norm(u) * R * rng.random() ** 0.45
            p = cen + u
            if p[1] < 12:
                continue
            light = (p[1] - 14) / 26 + u[1] / (2 * R)          # выше и снаружи — светлее
            tone = 4 if rng.random() < 0.08 else int(np.clip(round(light * 3 + rng.uniform(-0.6, 0.6)), 0, 3))
            s = rng.uniform(1.1, 2.1)
            crown.append(box(p, s, s * rng.uniform(0.7, 1.0), s, tone, [rng.uniform(-20, 20), rng.uniform(0, 90), rng.uniform(-20, 20)]))
            if rng.random() < 0.3 and u[1] > -R * 0.2:           # цветы — в верхней половине облаков
                q = p + u / max(np.linalg.norm(u), 1e-6) * s * 0.55
                bloom.append(box(q, 0.55, 0.3, 0.55, 0, [0, rng.uniform(0, 90), 0]))
                bloom.append(box(q + np.array([0, 0.18, 0]), 0.22, 0.2, 0.22, 1))
    mesh('world_tree', 'Древо мира (T23): ствол ~25 бл. с закрученной корой и пятью спиральными светящимися жилами, 9 корней-«ног», 8 ветвей '
                       'с отростками (верх ветвей ~36 бл.). Появление — снизу вверх (reveal up): в эффекте ещё и рост из ростка (move.scaleFrom).',
         'world_tree', 200, 40, [part(trunk, TREE_TONES, [4], {'delay': 0, 'duration': 200, 'easing': 'easeInOutSine', 'reveal': 'up', 'front': 2.5},
                                      opacity=0.97)])
    mesh('world_tree_crown', 'Древо мира (T23): крона — облака листвы на концах ветвей и купол (верх ~40 бл., размах ~34 бл.), '
                             '8% листьев светятся. Появляется снизу вверх после ствола.', 'world_tree', 210, 50,
         [part(crown, CROWN_TONES, [4], {'delay': 120, 'duration': 90, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 3.0}, opacity=0.86)])
    mesh('world_tree_bloom', 'Древо мира (T23): цветение финала — розовые цветы с золотой серединкой по кроне (светятся). '
                             'Раскрываются сверху вниз за 1 с.', 'world_tree', 20, 30,
         [part(bloom, BLOOM_TONES, [0, 1, 2], {'delay': 0, 'duration': 20, 'easing': 'easeOutCubic', 'reveal': 'down', 'front': 3.0},
               opacity=1.0, shade=False)])
    return len(trunk), len(crown), len(bloom)


def gen_root():
    """Корень-щупальце: выходит из земли рядом с ногами жертвы (0.9 бл. сбоку), обвивает её спиралью по ногам и корпусу
    (1.6 оборота, до высоты 1.7), кончик загибается наружу; шипы, светящаяся жила по спине."""
    rng = random.Random(7)
    boxes = []
    pts = []
    for j in range(8):                                           # выход из земли
        t = j / 7
        pts.append(np.array([0.95 - 0.25 * t, -0.4 + 0.55 * t, 0.15 * math.sin(t * 2)]))
    a0 = math.atan2(pts[-1][2], pts[-1][0])
    for j in range(1, 46):                                       # спираль вокруг жертвы
        t = j / 45
        a = a0 + t * 2 * math.pi * 1.6
        rad = 0.62 - 0.12 * t
        pts.append(np.array([rad * math.cos(a), 0.15 + 1.55 * t, rad * math.sin(a)]))
    last = pts[-1]
    out = last / max(np.linalg.norm([last[0], 0, last[2]]), 1e-6)
    for j in range(1, 6):                                        # кончик загибается наружу и вверх
        pts.append(last + np.array([out[0] * 0.12 * j, 0.1 * j, out[2] * 0.12 * j]))
    n = len(pts)
    for j in range(n - 1):
        t = j / (n - 1)
        w = 0.27 * (1 - t) ** 0.8 + 0.05
        tone = 4 if j % 5 == 2 else rng.choice([0, 1, 1, 2])
        boxes.append(bar(pts[j], pts[j + 1] + (pts[j + 1] - pts[j]) * 0.15, w, w, tone))
        if j % 6 == 3 and t < 0.85:                              # шипы наружу
            radial = pts[j] / max(np.linalg.norm([pts[j][0], 0, pts[j][2]]), 1e-6)
            tip = pts[j] + np.array([radial[0] * 0.28, 0.08, radial[2] * 0.28])
            boxes.append(bar(pts[j], tip, w * 0.35, w * 0.35, 2))
    mesh('world_tree_root', 'Корень-щупальце «Древа мира» (T23): выходит из земли и спиралью обвивает жертву (жертва — в начале координат, '
                            'рост 1.8). Появление снизу вверх за 10 тиков — «обвивает».', 'world_tree', 10, 8,
         [part(boxes, TREE_TONES, [4], {'delay': 0, 'duration': 10, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.4}, opacity=1.0)])
    return len(boxes)


EYE_A, EYE_B, EYE_SAG = 15.0, 7.4, 2.6      # полудлина, полуширина миндаля, провис центра линзы вниз


def _eye_halfwidth(x):
    t = max(0.0, 1 - (x / EYE_A) ** 2)
    return EYE_B * t ** 0.75


def _eye_y(x, z):
    """Нижняя поверхность глаза (линза, провисает вниз): центр щели ниже краёв — reveal up раскрывает глаз от щели к векам."""
    hw = _eye_halfwidth(x)
    u = min(1.0, abs(z) / max(hw, 1e-3))
    return -EYE_SAG * (1 - u ** 2) * (1 - 0.35 * (x / EYE_A) ** 2)


EYE_TONES = ['#B9AFC6', '#D6CEDF', '#8E819E', '#C02A6A', '#3FD6B8', '#2A0F3A', '#140820', '#FF5AA0']
#            склера тень / свет / складка, сосуд (свет), радужка бирюза (свет), радужка глубина, веко, блик радужки (свет)


def gen_abyss_eye():
    rng = random.Random(30)
    ball, lids, pupil = [], [], []
    IR_OUT, IR_IN = 6.3, 4.9
    veins = []
    for k in range(18):                                          # сосуды: ломаные от края к радужке
        a = rng.uniform(0, 2 * math.pi)
        p = np.array([math.cos(a) * EYE_A * 0.95, math.sin(a) * EYE_B * 0.9])
        path = [p.copy()]
        for j in range(10):
            p = p + (np.zeros(2) - p) * 0.12 + np.array([rng.uniform(-0.6, 0.6), rng.uniform(-0.4, 0.4)])
            path.append(p.copy())
        veins.append(path)

    def near_vein(x, z):
        for path in veins:
            for q0, q1 in zip(path, path[1:]):
                d_ = q1 - q0
                t = np.clip(np.dot([x - q0[0], z - q0[1]], d_) / max(np.dot(d_, d_), 1e-6), 0, 1)
                if np.hypot(x - q0[0] - d_[0] * t, z - q0[1] - d_[1] * t) < 0.42:
                    return True
        return False
    step = 0.9
    for x in np.arange(-EYE_A + step / 2, EYE_A, step):
        hw = _eye_halfwidth(x)
        for z in np.arange(-hw + step / 2, hw, step):
            y = _eye_y(x, z)
            rr = math.hypot(x, z)
            gx = (_eye_y(x + 0.3, z) - _eye_y(x - 0.3, z)) / 0.6     # наклон плитки по поверхности
            gz = (_eye_y(x, z + 0.3) - _eye_y(x, z - 0.3)) / 0.6
            rot = [math.degrees(math.atan(gz)), 0, -math.degrees(math.atan(gx))]
            if rr < IR_OUT:
                if rr > IR_IN:
                    tone = 4 if rng.random() < 0.7 else 7
                else:
                    ang = math.atan2(z, x)
                    streak = abs(math.sin(ang * 9 + rr * 0.6)) > 0.86
                    tone = 3 if streak and rr > 1.6 else 5
                ball.append(box((x, y - 0.06, z), step * 1.04, 0.22, step * 1.04, tone, rot))
            else:
                tone = 3 if near_vein(x, z) else (1 if rng.random() < 0.6 else 0)
                if abs(z) > hw - step * 1.2:
                    tone = 2                                     # складка у края века
                ball.append(box((x, y, z), step * 1.04, 0.3, step * 1.04, tone, rot))
    for sgn in (-1, 1):                                          # веки: толстый край по миндалю, складка над ним
        prev = None
        for k in range(61):
            x = -EYE_A + 2 * EYE_A * k / 60
            p = np.array([x, 0.35, sgn * _eye_halfwidth(x)])
            if prev is not None:
                lids.append(bar(prev, p, 1.0, 1.25, 6))
                lids.append(bar(prev + np.array([0, 0.6, sgn * 0.8]), p + np.array([0, 0.6, sgn * 0.8]), 0.7, 1.1, 6))
            prev = p
        for k in range(15):                                      # «ресницы» — щупальца наружу и вверх
            x = -EYE_A * 0.86 + 2 * EYE_A * 0.86 * (k + 0.5) / 15
            base = np.array([x, 0.5, sgn * (_eye_halfwidth(x) + 0.4)])
            L_ = rng.uniform(4, 8.5) * (1 - 0.5 * abs(x) / EYE_A)
            d0 = np.array([x / EYE_A * 0.4, rng.uniform(0.25, 0.6), sgn * 1.0])
            pts = _path(base, d0, L_, 7, np.array([0, 0.6, -sgn * 0.3]), rng)
            for j in range(len(pts) - 1):
                w = 0.55 * (1 - j / len(pts)) + 0.08
                lids.append(bar(pts[j], pts[j + 1] + (pts[j + 1] - pts[j]) * 0.1, w, w, 3 if j == len(pts) - 2 else 6))
    for x in np.arange(-0.8, 0.81, 0.4):                         # зрачок: вертикальная щель (вдоль z), край светится
        for z in np.arange(-4.4, 4.41, 0.4):
            e = (x / 0.85) ** 2 + (z / 4.5) ** 2
            if e <= 1:
                pupil.append(box((x, 0, z), 0.42, 0.25, 0.42, 1 if e > 0.62 else 0))
    pupil.append(box((0, -0.05, 0), 1.0, 0.05, 6.0, 2))
    mesh('abyss_eye', 'Око бездны (T23): глазное яблоко ~30×15 бл. в небе, линза провисает вниз (центр щели ниже краёв) — reveal up раскрывает '
                      'глаз от щели к векам. Склера бледная с багровыми сосудами, радужка бирюзово-маджента r6.3. Центр в начале координат, '
                      'смотрит вниз. Зрачок — отдельная модель abyss_eye_pupil.', 'abyss_eye', 70, 40,
         [part(ball, EYE_TONES, [3, 4, 7], {'delay': 0, 'duration': 70, 'easing': 'easeInOutCubic', 'reveal': 'up', 'front': 0.7}, opacity=0.95)])
    mesh('abyss_eye_lids', 'Око бездны (T23): веки (толстый тёмный край миндаля) и «ресницы»-щупальца наружу и вверх. Появляются первыми.',
         'abyss_eye', 30, 40,
         [part(lids, EYE_TONES, [3], {'delay': 0, 'duration': 30, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 2.0}, opacity=1.0)])
    mesh('abyss_eye_pupil', 'Око бездны (T23): зрачок — чёрная вертикальная щель 1.7×9 бл. со светящимся краем, плоско (смотрит вниз). '
                            'Отдельной моделью: код двигает его по радужке к цели (смещение ≤3 бл.) и поворачивает по yaw (щель поперёк взгляда).',
         'abyss_eye', 10, 10,
         [part(pupil, ['#030106', '#3FD6B8', '#FF5AA0'], [1, 2], {'delay': 0, 'duration': 10, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.3},
               opacity=0.97, shade=False)])
    return len(ball), len(lids), len(pupil)


SUN_TONES = ['#FFFFFF', '#FFF4D6', '#FFD36B', '#FF9A3A', '#FFB38A']


def gen_dawn_sun():
    """Солнце «Последнего рассвета»: шар-оболочка R5.5 (к центру белее), венец из 24 лучей в плоскости XY (лицом к заклинателю),
    тонкое кольцо-гало R8. Всё светится."""
    rng = random.Random(10)
    boxes = []
    R = 5.5
    s = 1.0
    for x in np.arange(-R, R + 0.01, s):
        for y in np.arange(-R, R + 0.01, s):
            for z in np.arange(-R, R + 0.01, s):
                r = math.sqrt(x * x + y * y + z * z)
                if R - 1.1 <= r <= R:
                    tone = 1 if z < -1.5 else (2 if rng.random() < 0.6 else 3)
                    boxes.append(box((x, y, z), s * 1.02, s * 1.02, s * 1.02, tone))
    boxes.append(box((0, 0, -0.5), 7.2, 7.2, 7.2, 0))            # горячее ядро (видно сквозь оболочку спереди)
    for k in range(24):
        a = 2 * math.pi * k / 24
        L_ = 13.5 if k % 2 == 0 else 9.0
        p0 = np.array([math.cos(a) * (R + 0.6), math.sin(a) * (R + 0.6), -1.0])
        p1 = np.array([math.cos(a) * L_, math.sin(a) * L_, -1.0])
        segs = 5
        for j in range(segs):
            q0 = p0 + (p1 - p0) * j / segs
            q1 = p0 + (p1 - p0) * (j + 1) / segs
            w = (0.9 if k % 2 == 0 else 0.6) * (1 - j / segs) + 0.12
            boxes.append(bar(q0, q1, w, 0.3, 2 if j < 2 else 4))
    for k in range(64):
        a = 2 * math.pi * k / 64
        p0 = np.array([math.cos(a) * 8.0, math.sin(a) * 8.0, -1.2])
        p1 = np.array([math.cos(a + 2 * math.pi / 64) * 8.0, math.sin(a + 2 * math.pi / 64) * 8.0, -1.2])
        boxes.append(bar(p0, p1, 0.18, 0.18, 1))
    mesh('dawn_sun', 'Солнце «Последнего рассвета» (T23): шар R5.5 (оболочка, к заклинателю белее), горячее ядро, венец из 24 лучей до 13.5 бл. '
                     'в плоскости XY (лицом к заклинателю, −z), гало R8. Всё светится. Восход — move.from снизу в эффекте.',
         'last_dawn', 20, 40,
         [part(boxes, SUN_TONES, [0, 1, 2, 3, 4], {'delay': 0, 'duration': 20, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 3.0},
               opacity=1.0, shade=False)])
    return len(boxes)


def meshes():
    print('tree', gen_world_tree(), 'root', gen_root(), 'eye', gen_abyss_eye(), 'sun', gen_dawn_sun())


# ================================================================== печати
def sigils():
    sigil('world_tree_seal', 'Древо мира: печать в точке, где растёт дерево (под заклинателем — та же, scale 0.5). Древо девяти миров '
                             'прорисовывается, кольцо рун природы, надпись «ДРЕВО МИРА ✦ КОРНИ ДЕВЯТИ МИРОВ», золотой обод.',
          8.0, N_GREEN, 'ground', [
              L('glow', 'disc', 'glow', 1.0, -0.01, ap(0, 24, 'fade'), color='#3E8A2A', br=0.4, pulse=(0.15, 50)),
              L('tree', 'disc', 'yggdrasil', 0.92, 0.0, ap(0, 40, 'draw', easing='easeInOutSine', startAngle=-90), rot=2, boost=2),
              L('band', 'band', 'school_nature_band', 1.06, 0.01, ap(16, 26, 'draw', startAngle=90), inner=0.95, repeat=10, rot=-3, color=N_LIGHT),
              T('words', 'ДРЕВО МИРА ✦ КОРНИ ДЕВЯТИ МИРОВ ✦ ', 1.14, 0.045, 0.015, ap(26, 34, 'draw', easing='linear'), font='cyrillic',
                color=N_GOLD, br=0.9, rot=1.5, repeat=2),
              L('rim', 'band', 'thin_ring', 1.22, 0.02, ap(34, 16, 'draw', startAngle=-90, direction=-1), inner=0.985, repeat=1, color=N_GOLD),
          ], flash={'color': N_LIGHT, 'size': 1.2, 'duration': 16, 'sparks': 40}, ddur=30, stagger=3)
    sigil('world_tree_zone', 'Древо мира: граница зоны корней r24 — тонкое кольцо и лента рун природы, медленно вращается.', 24.0, N_GREEN, 'ground', [
        L('band', 'band', 'school_nature_band', 1.0, 0.0, ap(0, 30, 'draw', startAngle=90), inner=0.985, repeat=48, rot=-0.6, br=0.7),
        L('rim', 'band', 'thin_ring', 0.99, 0.01, ap(0, 24, 'draw', startAngle=90, direction=-1), inner=0.996, repeat=1, color=N_GOLD, br=0.8),
    ], ddur=30, dissolve=('fade',))
    sigil('abyss_seal', 'Око бездны: печать под заклинателем — малые глаза по кругу, щупальца-спирали к центральному глазу, '
                        'кольцо рун, «ОКО ВИДИТ ✦ БЕЗДНА СМОТРИТ В ОТВЕТ».', 5.0, E_TEAL, 'ground', [
        L('glow', 'disc', 'glow', 1.0, -0.01, ap(0, 20, 'fade'), color=E_MAG, br=0.35, pulse=(0.25, 30)),
        L('sigil', 'disc', 'abyss_sigil', 0.95, 0.0, ap(0, 36, 'draw', easing='easeInOutSine', startAngle=90), rot=-4, boost=3),
        L('band', 'band', 'school_eldritch_band', 1.08, 0.01, ap(14, 24, 'draw', startAngle=-90), inner=0.94, repeat=8, rot=3, color=E_PALE),
        T('words', 'ОКО ВИДИТ ✦ БЕЗДНА СМОТРИТ В ОТВЕТ ✦ ', 1.17, 0.055, 0.015, ap(24, 30, 'draw', easing='linear'), font='cyrillic',
          color=E_MAG, br=1.1, rot=-2, repeat=2),
        L('rim', 'band', 'thin_ring', 1.25, 0.02, ap(30, 14, 'draw', startAngle=90), inner=0.985, repeat=1, br=0.9),
    ], flash={'color': E_PALE, 'size': 1.2, 'duration': 14, 'sparks': 30}, ddur=24)
    sigil('abyss_sky', 'Око бездны: тучи над заклинателем (r40, лицом вниз) — два рукава спирали туч крутятся навстречу, в центре — знак Ока, '
                       'где раскроется глаз. Светятся тускло (бирюза и маджента), тьму даёт tint и тёмные облака-спрайты.', 40.0, E_TEAL, 'sky', [
        L('swirl', 'disc', 'abyss_swirl', 1.0, 0.0, ap(0, 80, 'fade', 'twist', twist=120, easing='easeOutCubic'), rot=7, boost=3, color='#5A2A8A', br=0.55),
        L('swirl2', 'disc', 'abyss_swirl', 0.72, 0.05, ap(30, 80, 'fade', 'twist', twist=-90), rot=-11, boost=2, color=E_TEAL, br=0.32),
        L('core', 'disc', 'abyss_sigil', 0.3, 0.1, ap(60, 60, 'grow', 'fade', easing='easeOutBack'), rot=-6, color=E_MAG, br=0.7, pulse=(0.3, 24)),
        L('rim', 'band', 'thin_ring', 1.0, 0.12, ap(20, 60, 'draw', startAngle=90), inner=0.995, repeat=1, color=E_TEAL, br=0.5),
    ], ddur=40, dissolve=('fade', 'collapse'))
    sigil('dawn_seal', 'Последний рассвет: печать под заклинателем — восходящее солнце над горизонтом, веер лучей, отражение пунктиром, '
                       'двенадцать малых солнц, «ДА ВЗОЙДЁТ ПОСЛЕДНИЙ РАССВЕТ».', 5.0, H_GOLD, 'ground', [
        L('glow', 'disc', 'glow', 1.0, -0.01, ap(0, 18, 'fade'), color=H_ROSE, br=0.4, pulse=(0.12, 40)),
        L('rays', 'spokes', 'rays', 1.45, -0.005, ap(10, 40, 'fade', 'grow'), rot=1, color=H_PALE, br=0.3),
        L('sun', 'disc', 'dawn_sunrise', 0.95, 0.0, ap(0, 34, 'draw', easing='easeInOutSine', startAngle=180, direction=-1), rot=1.5),
        L('band', 'band', 'school_holy_band', 1.08, 0.01, ap(14, 24, 'draw', startAngle=90), inner=0.94, repeat=8, rot=-2, color=H_PALE),
        T('words', 'ДА ВЗОЙДЁТ ПОСЛЕДНИЙ РАССВЕТ ✦ ', 1.17, 0.055, 0.015, ap(24, 30, 'draw', easing='linear'), font='cyrillic', color=H_ROSE,
          br=1.0, rot=1, repeat=2),
        L('rim', 'band', 'thin_ring', 1.25, 0.02, ap(30, 14, 'draw', startAngle=-90), inner=0.985, repeat=1, color=H_WHITE, br=0.8),
    ], flash={'color': H_PALE, 'size': 1.2, 'duration': 14, 'sparks': 30}, ddur=24)
    sigil('dawn_ring', 'Последний рассвет: круг r30 — граница рассвета: золотое кольцо, лента святых рун, надпись по кругу.', 30.0, H_GOLD, 'ground', [
        L('band', 'band', 'school_holy_band', 1.0, 0.0, ap(0, 40, 'draw', startAngle=90), inner=0.988, repeat=56, rot=0.5, br=0.8),
        L('rim', 'band', 'thin_ring', 0.985, 0.01, ap(0, 30, 'draw', startAngle=90, direction=-1), inner=0.997, repeat=1, color=H_WHITE, br=0.9),
        T('words', 'ПОСЛЕДНИЙ РАССВЕТ ✦ ', 0.965, 0.011, 0.012, ap(20, 40, 'draw', easing='linear'), font='cyrillic', color=H_ROSE, br=0.9,
          rot=0.5, repeat=10),
    ], ddur=40, dissolve=('fade',))


# ================================================================== эффекты
def style(id, comment, primary, secondary, core, shadow, shards, sig, rot=0.6):
    F.write('fx/styles/%s.json' % id, {
        'comment': comment, 'palette': {'primary': primary, 'secondary': secondary, 'core': core, 'shadow': shadow},
        'textures': {'sparks': 'spark_soft', 'runes': 'rune_band', 'shards': shards, 'sigil': sig}, 'blend': 'additive',
        'motion': {'rotationScale': rot, 'jitter': 0.0, 'easing': 'easeInOutSine'}})


TREE = 'point:tree'
WT_CAST, WT_ZONE = 240, 400          # каст 12 с, корни 20 с
WT_BLOOM = WT_CAST + WT_ZONE         # 640: цветение


def world_tree_fx():
    style('world_tree', 'Древо мира: живая зелень, светлая листва, золото света; кора тёмная.', N_GREEN, N_LIGHT, '#FFFFFF', '#2A5A10',
          'mote_leaf', 'yggdrasil', rot=0.5)
    grow = {'from': [0, 0, 0], 'scaleFrom': 0.05, 'delay': 0, 'duration': 210, 'easing': 'easeInOutSine'}
    fx('world_tree_cast', 'Древо мира, каст 12 с (240 тиков) + 20 с корней + цветение. Точки: caster — заклинатель, point:tree — точка взгляда '
                          '(до 32 бл., на земле). 0–1 с печать под заклинателем и в точке; 1–2 с земля трескается, бьёт росток; 1–11.5 с ствол '
                          'растёт из ростка (scale 0.05→1 и проявление снизу вверх по секциям), по нему вьются ленты света; 7–11 с крона; 11.8 с '
                          'вспышка кроны, волна до r24 — зона корней. 12–32 с дерево стоит (корни — fx/world_tree_root, код). На 640 тике код '
                          'запускает fx/world_tree_bloom (цветение) — дерево рассыпается листвой к 700.',
       'world_tree', 720, [
           E('sigil', 0, 'caster+0,0.04,0', id='world_tree_seal', scale=0.5, until=236),
           E('sigil', 6, TREE + '+0,0.05,0', id='world_tree_seal', until=250),
           E('decal', 20, TREE + '+0,0.06,0', duration=240, texture='higher_cracks', radius=4.2, grow=24, fadeOut=60, color=N_GREEN, brightness=0.7,
             comment='земля трескается светом'),
           E('flash', 22, TREE + '+0,0.6,0', duration=12, size=2.5, rays=6, color=N_LIGHT, comment='бьёт росток'),
           E('sprites', 20, TREE + '+0,0.3,0', duration=40, texture='mote_leaf', count=80, rate=2, area=2.0, speed=0.06, gravity=0.004,
             spin=90, tumble=1, size=[0.3, 0.15], life=40, color=N_GREEN),
           E('sprites', 20, TREE + '+0,0.2,0', duration=220, texture='spark_soft', count=600, rate=2.8, area=6.0, speed=0.01, gravity=-0.006,
             size=[0.2, 0.03], life=60, color=N_LIGHT, glow=0.5, comment='свет поднимается от земли к стволу'),
           E('mesh', 20, TREE, model='world_tree', duration=640, move=grow, comment='рост по секциям: проявление снизу вверх 200 тиков'),
           E('mesh', 20, TREE, model='world_tree_crown', duration=640, move=grow, comment='крона проявляется с 7 с (appear.delay в модели — 120)'),
           E('trail', 40, TREE + '+0,0.5,0', duration=190, width=0.35, length=26, count=3, color='@secondary', brightness=1.2,
             orbit={'radius': 4.0, 'speed': 4.5, 'climb': 3.2, 'rise': 0.3, 'risePeriod': 30}, comment='ленты света вьются вверх по стволу'),
           E('trail', 60, TREE + '+0,0.5,0', duration=170, width=0.22, length=20, count=2, color=N_GOLD,
             orbit={'radius': 5.2, 'speed': -3.5, 'climb': 3.6}),
           E('sprites', 160, TREE + '+0,30,0', duration=560, texture='mote_leaf', count=2000, rate=1.4, area=14, speed=0.002, gravity=0.0015,
             sway=1.2, tumble=0.6, size=[0.4, 0.3], life=200, color=N_GREEN, brightness=0.9, comment='листья опадают с кроны'),
           E('sprites', 200, TREE + '+0,4,0', duration=500, texture='spark_soft', count=2000, rate=1.2, area=16, speed=0.004, gravity=-0.0006,
             size=[0.14, 0.04], life=90, color=N_GOLD, glow=0.6, comment='светлячки под кроной'),
           E('flash', 234, TREE + '+0,30,0', duration=16, size=22, rays=10, anamorphic=6, color=N_LIGHT, comment='11.7 с: крона вспыхивает'),
           E('wave', 236, TREE + '+0,0.1,0', duration=30, shape='ring', radius=24, thickness=1.6, color=N_GREEN),
           E('sigil', 240, TREE + '+0,0.06,0', id='world_tree_zone', until=WT_BLOOM, comment='граница зоны корней r24'),
           E('tint', 200, TREE, duration=460, radius=26, color='#B8F07A', strength=0.12, **{'in': ease(40), 'out': ease(40)}),
       ])
    fx('world_tree_bloom', 'Древо мира: цветение (код на 640 тике, caster = точка дерева). Крона покрывается цветами, облако спор r10 '
                           '(Яд II + Слепота — код), лепестки и листва осыпаются; модель дерева сжимается к 700 (в world_tree_cast).',
       'world_tree', 90, [
           E('mesh', 0, 'caster', model='world_tree_bloom', duration=40),
           E('flash', 2, 'caster+0,30,0', duration=20, size=18, rays=8, color=N_PINK),
           E('wave', 6, 'caster+0,1.2,0', duration=26, shape='sphere', radius=10, rim=0.8, color='#D8E86A', brightness=0.5),
           E('wave', 6, 'caster+0,0.1,0', duration=24, shape='ring', radius=10, thickness=0.8, color=N_GOLD),
           E('sprites', 6, 'caster+0,1.5,0', duration=30, texture='mote_cloud', count=90, rate=3, area=9, speed=0.01, gravity=-0.0005,
             size=[3.0, 5.0], life=70, color='#9AB83A', blend='translucent', brightness=0.8, comment='облако спор r10'),
           E('sprites', 6, 'caster+0,1.2,0', duration=50, texture='spark_soft', count=400, rate=8, area=10, speed=0.01, gravity=-0.001,
             size=[0.14, 0.05], life=50, color='#E8FF6A', glow=0.4, comment='споры'),
           E('sprites', 10, 'caster+0,30,0', duration=60, texture='mote_petal', count=500, rate=8, area=15, speed=0.01, gravity=0.003,
             sway=1.5, tumble=0.8, size=[0.35, 0.25], life=110, color=N_PINK, comment='лепестки'),
           E('sprites', 20, 'caster+0,28,0', duration=60, texture='mote_leaf', count=700, rate=12, area=16, speed=0.02, gravity=0.004,
             sway=1.3, tumble=1, size=[0.45, 0.3], life=100, color=N_GREEN, comment='дерево рассыпается листвой (3 с)'),
       ])
    fx('world_tree_root', 'Древо мира: корень-щупальце на жертве (caster = жертва, follow — едет с ней, пока корень тянет к стволу). '
                          'duration −1: код останавливает (Fx.stop), когда корень сломан или жертва вышла из зоны — модель уходит в землю.',
       'world_tree', -1, [
           E('mesh', 0, 'caster', follow=True, model='world_tree_root'),
           E('decal', 0, 'caster+0,0.04,0', follow=True, duration=30, texture='higher_cracks', radius=1.3, grow=6, fadeOut=20, color=N_GREEN,
             brightness=0.6),
           E('sprites', 0, 'caster+0,0.1,0', duration=4, texture='mote_leaf', count=14, rate=4, spread=0.4, speed=0.08, gravity=0.01,
             tumble=1, size=[0.22, 0.12], life=20, color='#6A4628', blend='translucent', comment='комья земли'),
           E('flash', 2, 'caster+0,0.8,0', follow=True, duration=6, size=1.2, rays=4, color=N_LIGHT),
           E('sprites', 6, 'caster+0,0.9,0', follow=True, texture='spark_soft', count=100000, rate=0.4, spread=0.6, speed=0.004,
             gravity=-0.002, size=[0.1, 0.02], life=20, color=N_LIGHT, glow=0.4),
       ])
    fx('world_tree_root_break', 'Древо мира: корень сломан (caster = точка корня/жертва): щепки, листья, зелёная вспышка. Перед ним — Fx.stop '
                                'у world_tree_root.', 'world_tree', 20, [
        E('flash', 0, 'caster+0,0.9,0', duration=6, size=1.4, rays=5, color=N_LIGHT),
        E('sprites', 0, 'caster+0,0.8,0', duration=3, texture='shard', count=26, rate=9, spread=0.5, speed=0.12, gravity=0.012, tumble=1,
          size=[0.2, 0.08], life=22, color='#6A4628', blend='translucent', comment='щепки'),
        E('sprites', 0, 'caster+0,1.0,0', duration=3, texture='mote_leaf', count=16, rate=6, spread=0.5, speed=0.08, gravity=0.004, sway=1,
          tumble=1, size=[0.25, 0.15], life=30, color=N_GREEN),
    ])
    fx('world_tree_heal', 'Древо мира: союзник под кроной (Регенерация II), каждые ~2 с (caster = союзник, follow): листья опадают светом '
                          'и тают у плеч, мягкие искры.', 'world_tree', 40, [
        E('sprites', 0, 'caster+0,2.8,0', follow=True, duration=20, texture='mote_leaf', count=10, rate=0.5, area=0.7, speed=0.002,
          gravity=0.002, sway=1, tumble=0.5, size=[0.25, 0.12], life=26, color=N_LIGHT, glow=0.5),
        E('sprites', 4, 'caster+0,1.0,0', follow=True, duration=20, texture='spark_soft', count=16, rate=0.8, spread=0.4, speed=0.006,
          gravity=-0.004, size=[0.12, 0.02], life=20, color=N_GOLD, glow=0.5),
    ])


EYE_Y = 32           # глаз над заклинателем
AE_CAST, AE_ZONE = 240, 300


def abyss_eye_fx():
    style('abyss_eye', 'Око бездны: бирюза и маджента в фиолетово-чёрных тучах, бледная склера, тьма.', E_TEAL, E_PALE, '#FFFFFF', E_DARK,
          'mote_eye', 'abyss_sigil', rot=0.7)
    eye = 'caster+0,%d,0' % EYE_Y
    flick = []
    rng = random.Random(5)
    for k in range(10):                                          # молнии внутри туч (горизонтальные, к цели не идут)
        a, b = rng.uniform(0, 2 * math.pi), rng.uniform(8, 26)
        x0, z0 = b * math.cos(a), b * math.sin(a)
        a2 = a + rng.uniform(0.3, 0.9)
        x1, z1 = (b + rng.uniform(-4, 6)) * math.cos(a2), (b + rng.uniform(-4, 6)) * math.sin(a2)
        flick.append(E('lightning', 40 + 18 * k + rng.randint(0, 8), off('caster', x0, EYE_Y + 2, z0), to=off('caster', x1, EYE_Y + 1, z1),
                       duration=6, branches=2, jaggedness=0.25, width=0.18, color=E_TEAL if k % 2 else E_MAG, brightness=1.3))
    fx('abyss_eye_cast', 'Око бездны, каст 12 с (240) + 15 с Ока (300) + закрытие. caster — заклинатель (глаз над ним на +32). 0–3 с небо '
                         'темнеет, тучи начинают закручиваться (печать-спираль r40); 3–8 с тучи быстрее, молнии внутри; 7.5 с веки; 8–11.5 с глаз '
                         'раскрывается от щели к векам; на 228 тике код ставит зрачок (fx/abyss_eye_pupil, отдельный экземпляр — код ведёт его к '
                         'цели); 11.5 с вспышка-взгляд, волна до r40. 12–27 с Око смотрит; 27 с закрывается (сжатие), тучи расходятся.',
       'abyss_eye', 600, [
           E('sigil', 0, 'caster+0,0.04,0', id='abyss_seal', until=236),
           E('tint', 0, 'caster', duration=580, radius=40, color='#140A22', strength=0.55, **{'in': ease(80, 'easeInOutSine'), 'out': ease(40)}),
           E('sigil', 0, off('caster', 0, EYE_Y + 3, 0), id='abyss_sky', until=AE_CAST + AE_ZONE + 10),
           E('sprites', 0, off('caster', 0, EYE_Y + 1, 0), duration=AE_CAST + AE_ZONE, texture='mote_cloud', count=100000, rate=3.5, area=36,
             speed=0.006, gravity=0, size=[7, 12], life=140, color='#0A0612', blend='translucent', comment='тёмные тучи'),
           E('vortex', 20, off('caster', 0, EYE_Y + 1.5, 0), duration=AE_CAST + AE_ZONE - 20, radius=30, height=0, arms=5, speed=0.9, pull=1,
             texture='mote_cloud', particles=160, life=80, size=3.5, color='#3A1A5A', **{'in': ease(60)}, comment='тучи закручиваются'),
           E('vortex', 100, off('caster', 0, EYE_Y + 2, 0), duration=AE_CAST + AE_ZONE - 100, radius=22, height=0, arms=3, speed=1.8, pull=1,
             texture='spark_soft', particles=120, life=40, size=0.5, color=E_TEAL, brightness=0.6),
           *flick,
           E('mesh', 150, eye, model='abyss_eye_lids', duration=AE_CAST + AE_ZONE - 150, comment='7.5 с: веки'),
           E('mesh', 160, eye, model='abyss_eye', duration=AE_CAST + AE_ZONE - 160, comment='8–11.5 с: раскрывается от щели'),
           E('flash', 160, off('caster', 0, EYE_Y - 2.6, 0), duration=40, size=12, anamorphic=30, color=E_MAG, brightness=0.8,
             **{'in': ease(10), 'out': ease(26)}, comment='свет в щели'),
           E('flash', 230, off('caster', 0, EYE_Y - 2.6, 0), duration=16, size=26, rays=12, color=E_PALE, comment='11.5 с: Око смотрит'),
           E('wave', 232, 'caster+0,0.2,0', duration=36, shape='ring', radius=40, thickness=2.0, color=E_MAG),
           E('sprites', 240, off('caster', 0, EYE_Y - 4, 0), duration=AE_ZONE, texture='mote_eye', count=100000, rate=0.8, area=30, speed=0.004,
             gravity=0.004, spin=30, size=[0.6, 0.3], life=160, color=E_TEAL, brightness=0.8, comment='«глазки» осыпаются из туч'),
           E('flash', AE_CAST + AE_ZONE, off('caster', 0, EYE_Y - 2.6, 0), duration=20, size=16, anamorphic=20, color=E_MAG,
             comment='27 с: Око закрывается'),
       ])
    fx('abyss_eye_pupil', 'Око бездны: зрачок (отдельный экземпляр, код запускает на 228 тике каста в точке центра глаза — над '
                          'заклинателем на +29.3 — и двигает Fx.move: смещение к цели по горизонтали ≤3 бл., yaw — на цель; Fx.stop в конце).',
       'abyss_eye', -1, [
           E('mesh', 0, 'caster', follow=True, model='abyss_eye_pupil'),
           E('flash', 0, 'caster', follow=True, duration=12, size=6, rays=6, color=E_TEAL),
       ])
    fx('abyss_eye_gaze', 'Око бездны: взгляд на Око (caster = жертва). Магента-вспышка в глазах (засветка экрана жертвы), «глазки» '
                         'разлетаются от головы, тёмная сфера; бирюзовая оболочка — застывание 1 с.', 'abyss_eye', 26, [
        E('flash', 0, 'caster.eyes', follow=True, duration=8, size=1.4, rays=8, screen=0.45, color=E_MAG),
        E('aura', 0, 'caster', target='caster', duration=22, thickness=0.12, pulse=[0.4, 6], motes=12, texture='mote_eye', color=E_TEAL,
          **{'in': ease(2), 'out': ease(8)}),
        E('sprites', 0, 'caster+0,1.7,0', follow=True, duration=3, texture='mote_eye', count=18, rate=6, spread=0.4, speed=0.08, gravity=0,
          spin=60, size=[0.35, 0.15], life=18, color=E_PALE),
        E('wave', 1, 'caster+0,1.2,0', duration=12, shape='sphere', radius=1.8, rim=1.3, color=E_MAG),
    ])
    fx('abyss_eye_whisper', 'Око бездны: урон рассудку раз в секунду (caster = жертва под открытым небом): тихие «глазки» у головы, '
                            'фиолетовая дымка.', 'abyss_eye', 20, [
        E('sprites', 0, 'caster+0,1.8,0', follow=True, duration=10, texture='mote_eye', count=4, rate=0.4, spread=0.5, speed=0.004,
          gravity=-0.001, spin=20, size=[0.25, 0.1], life=18, color=E_TEAL, brightness=0.7),
        E('sprites', 0, 'caster+0,1.4,0', follow=True, duration=8, texture='mote_cloud', count=3, rate=0.4, spread=0.3, speed=0.003,
          size=[0.8, 1.2], life=20, color='#2A1040', blend='translucent'),
    ])


SUN_Z, SUN_Y = 42, 9          # солнце: вперёд по взгляду заклинателя и над землёй (итоговая высота)
LD_CAST, LD_ZONE = 200, 240


def last_dawn_fx():
    style('last_dawn', 'Последний рассвет: золото зари, розовато-янтарный горизонт, белый свет.', H_GOLD, H_PALE, '#FFFFFF', '#8A6420',
          'mote_feather', 'dawn_sunrise', rot=0.4)
    sun = 'caster+0,%d,%d' % (SUN_Y, SUN_Z)
    rays = []
    for k in range(11):                                          # лучи зари веером из-за горизонта (от солнца в небо; не к целям)
        a = math.radians(-75 + 15 * k)
        rays.append(E('beam', 150 + 4 * abs(k - 5), sun, to=off('caster', 46 * math.sin(a), SUN_Y + 46 * math.cos(a), SUN_Z + 6), duration=LD_ZONE + 60,
                      width=0.9 if k % 2 == 0 else 0.5, core=0.25, grow=40, taper=0.7, brightness=0.35, color=H_GOLD if k % 2 else H_ROSE,
                      **{'out': ease(30)}))
    fx('last_dawn_cast', 'Последний рассвет, каст 10 с (200) + 12 с рассвета (240) + закат. caster — заклинатель; солнце — впереди по взгляду '
                         '(+42 вперёд, итог +9 вверх). 0–2 с печать, молитва; 0.5–3 с круг r30; 1–10 с на горизонте разгорается заря (полоса '
                         'света), 2–10 с солнце восходит из-за горизонта, с 7.5 с веер лучей; 10 с — солнце взошло: вспышка, тёплый tint r30 '
                         '(день — код). 10–22 с золотые искры и перья в круге. 22 с — солнце гаснет.',
       'last_dawn', 500, [
           E('sigil', 0, 'caster+0,0.04,0', id='dawn_seal', until=196),
           E('sprites', 0, 'caster+0,0.2,0', duration=60, texture='spark_soft', count=120, rate=2, area=3, speed=0.01, gravity=-0.005,
             size=[0.16, 0.03], life=36, color=H_PALE, glow=0.4),
           E('sigil', 10, 'caster+0,0.06,0', id='dawn_ring', until=LD_CAST + LD_ZONE),
           E('flash', 20, off('caster', 0, 1.5, SUN_Z), duration=200, size=12, anamorphic=36, color=H_AMBER, brightness=0.9,
             **{'in': ease(160, 'easeInSine'), 'out': ease(20)}, comment='заря: полоса света на горизонте'),
           E('flash', 60, off('caster', 0, 3, SUN_Z + 2), duration=170, size=26, color=H_ROSE, brightness=0.35,
             **{'in': ease(140, 'easeInSine'), 'out': ease(20)}, comment='розовое небо над горизонтом'),
           E('mesh', 40, sun, model='dawn_sun', duration=LD_ZONE + 180,
             move={'from': [0, -20, 0], 'scaleFrom': 0.75, 'delay': 0, 'duration': 160, 'easing': 'easeOutSine'}, comment='солнце восходит'),
           *rays,
           E('flash', 200, sun, duration=20, size=34, rays=14, anamorphic=10, screen=0.35, color=H_WHITE, comment='10 с: солнце взошло'),
           E('wave', 200, 'caster+0,0.2,0', duration=34, shape='ring', radius=30, thickness=1.8, color=H_GOLD),
           E('tint', 196, 'caster', duration=LD_ZONE + 60, radius=30, color='#FFC98A', strength=0.3, **{'in': ease(24), 'out': ease(40)}),
           E('sprites', 200, 'caster+0,0.5,0', duration=LD_ZONE, texture='spark_soft', count=100000, rate=4, area=28, speed=0.006,
             gravity=-0.003, size=[0.18, 0.04], life=80, color=H_GOLD, glow=0.5, comment='золотые искры в круге'),
           E('sprites', 200, 'caster+0,9,0', duration=LD_ZONE, texture='mote_feather', count=100000, rate=0.6, area=24, speed=0.002,
             gravity=0.0012, sway=1.2, tumble=0.6, size=[0.4, 0.3], life=180, color=H_PALE),
           E('flash', LD_CAST + LD_ZONE, sun, duration=40, size=24, anamorphic=20, color=H_AMBER, **{'out': ease(36)}, comment='22 с: закат'),
       ])
    fx('last_dawn_undying', 'Последний рассвет: союзник не умер (урон срезан до 1 hp; caster = союзник). Золотая вспышка у груди, нимб, '
                            'перья.', 'last_dawn', 20, [
        E('flash', 0, 'caster+0,1.2,0', follow=True, duration=10, size=2.2, rays=8, color=H_WHITE),
        E('halo', 0, 'caster', follow=True, duration=20, size=0.4, spin=4, color=H_GOLD, **{'in': ease(2), 'out': ease(10)}),
        E('sprites', 0, 'caster+0,1.2,0', follow=True, duration=3, texture='mote_feather', count=12, rate=4, spread=0.4, speed=0.06,
          gravity=0.002, sway=1, tumble=1, size=[0.3, 0.2], life=30, color=H_PALE),
    ])
    fx('last_dawn_heal', 'Последний рассвет: после 12 с союзник лечится на 50% записанного урона за 2 с (caster = союзник, follow): '
                         'золотые искры поднимаются, тёплая оболочка.', 'last_dawn', 44, [
        E('aura', 0, 'caster', target='caster', duration=40, thickness=0.1, pulse=[0.2, 10], motes=24, texture='spark_soft', color=H_GOLD,
          **{'in': ease(6), 'out': ease(14)}),
        E('sprites', 0, 'caster+0,0.4,0', follow=True, duration=40, texture='spark_soft', count=80, rate=2, area=0.6, speed=0.01,
          gravity=-0.006, size=[0.16, 0.02], life=26, color=H_GOLD, glow=0.6),
    ])
    fx('last_dawn_burn', 'Последний рассвет: нежить / Кровь / Запретная горят в свете (каждую секунду, caster = жертва): бело-золотое пламя '
                         'по телу, искры.', 'last_dawn', 22, [
        E('sprites', 0, 'caster+0,0.9,0', follow=True, duration=14, texture='mote_flame', count=24, rate=1.8, spread=0.4, speed=0.01,
          gravity=-0.006, size=[0.35, 0.1], life=16, color='#FFE9A0'),
        E('flash', 0, 'caster+0,1.0,0', follow=True, duration=6, size=1.0, rays=4, color=H_WHITE),
    ])


# ================================================================== иконки
MYTH = ('#B473FF', '#0D0716')       # рамка Мифической ступени (как у «Сна бабочки»)


def _icon(size, draw, out, frame=None, crisp=False):
    F._icon(size, draw, out, frame=frame, crisp=crisp)


def icon_world_tree(d, S):
    d.polygon([(S * 0.44, S * 0.86), (S * 0.47, S * 0.5), (S * 0.53, S * 0.5), (S * 0.56, S * 0.86)], fill=_c('#7A5634'))     # ствол
    for x0, x1 in ((0.44, 0.2), (0.56, 0.8), (0.47, 0.32), (0.53, 0.68)):                                                     # корни
        d.line([S * x0, S * 0.84, S * x1, S * 0.9], fill=_c('#7A5634'), width=int(S * 0.05))
    for cx, cy, r, col in ((0.5, 0.34, 0.25, '#2F7A2E'), (0.3, 0.42, 0.15, '#3E8A2A'), (0.7, 0.42, 0.15, '#3E8A2A'),
                           (0.5, 0.28, 0.17, '#4FAE3A'), (0.4, 0.24, 0.1, '#7FD04E'), (0.6, 0.3, 0.09, '#7FD04E')):
        d.ellipse([S * (cx - r), S * (cy - r), S * (cx + r), S * (cy + r)], fill=_c(col))
    for x, y in ((0.36, 0.3), (0.58, 0.22), (0.66, 0.4), (0.46, 0.42), (0.28, 0.44)):
        d.ellipse([S * (x - 0.03), S * (y - 0.03), S * (x + 0.03), S * (y + 0.03)], fill=_c('#FFE38A'))


def icon_abyss_eye(d, S):
    for k in range(3):                                                         # тучи-спираль
        d.arc([S * (0.1 + k * 0.06), S * (0.1 + k * 0.06), S * (0.9 - k * 0.06), S * (0.9 - k * 0.06)], 200 + k * 40, 340 + k * 40,
              fill=_c('#5A2A8A'), width=int(S * 0.05))
    top = [(0.5 + 0.44 * math.cos(t), 0.52 - 0.24 * math.sin(t)) for t in np.linspace(0, math.pi, 20)]
    bot = [(0.5 + 0.44 * math.cos(t), 0.52 - 0.24 * math.sin(t)) for t in np.linspace(math.pi, 2 * math.pi, 20)]
    d.polygon([(S * x, S * y) for x, y in top + bot], fill=_c('#D6CEDF'), outline=_c('#140820'))
    d.ellipse([S * 0.37, S * 0.39, S * 0.63, S * 0.65], fill=_c('#C02A6A'))
    d.ellipse([S * 0.37, S * 0.39, S * 0.63, S * 0.65], outline=_c('#3FD6B8'), width=int(S * 0.04))
    d.ellipse([S * 0.47, S * 0.41, S * 0.53, S * 0.63], fill=_c('#05020A'))
    d.line([(S * x, S * y) for x, y in top], fill=_c('#140820'), width=int(S * 0.05))


def icon_last_dawn(d, S):
    for k in range(9):
        a = math.pi + math.pi * (k + 0.5) / 9
        r1 = 0.44 if k % 2 == 0 else 0.34
        d.line([S * (0.5 + 0.2 * math.cos(a)), S * (0.66 + 0.2 * math.sin(a)), S * (0.5 + r1 * math.cos(a)), S * (0.66 + r1 * math.sin(a))],
               fill=_c('#FFE38A' if k % 2 == 0 else '#FFB38A'), width=int(S * 0.045))
    d.pieslice([S * 0.28, S * 0.44, S * 0.72, S * 0.88], 180, 360, fill=_c('#FFD36B'))
    d.pieslice([S * 0.36, S * 0.52, S * 0.64, S * 0.8], 180, 360, fill=_c('#FFF4D6'))
    d.rectangle([S * 0.1, S * 0.66, S * 0.9, S * 0.71], fill=_c('#FF9A3A'))
    d.line([S * 0.22, S * 0.79, S * 0.78, S * 0.79], fill=_c('#FFB38A', 160), width=int(S * 0.035))


def effect_icon(d, S, kind):
    if kind == 'entangled':                                                    # корни обвили ноги
        d.rectangle([S * 0.36, S * 0.1, S * 0.64, S * 0.92], fill=_c('#5A5A6A'))
        for k in range(4):
            y = 0.25 + k * 0.18
            d.arc([S * 0.22, S * (y - 0.08), S * 0.78, S * (y + 0.08)], 0, 200, fill=_c('#7A5634'), width=int(S * 0.09))
            d.arc([S * 0.22, S * (y - 0.08), S * 0.78, S * (y + 0.08)], 20, 120, fill=_c('#B8FF7A'), width=int(S * 0.035))
    elif kind == 'abyss_dread':                                                # око в тучах
        icon_abyss_eye(d, S)
    elif kind == 'dawn_grace':                                                 # золотое солнце с нимбом
        d.ellipse([S * 0.12, S * 0.12, S * 0.88, S * 0.88], outline=_c('#FFD36B'), width=int(S * 0.07))
        d.ellipse([S * 0.3, S * 0.3, S * 0.7, S * 0.7], fill=_c('#FFF4D6'), outline=_c('#FF9A3A'), width=int(S * 0.05))
        for k in range(8):
            a = 2 * math.pi * k / 8
            d.line([S * (0.5 + 0.25 * math.cos(a)), S * (0.5 + 0.25 * math.sin(a)), S * (0.5 + 0.36 * math.cos(a)), S * (0.5 + 0.36 * math.sin(a))],
                   fill=_c('#FFE38A'), width=int(S * 0.05))


def icons():
    for name, fn in (('world_tree', icon_world_tree), ('abyss_eye', icon_abyss_eye), ('last_dawn', icon_last_dawn)):
        _icon(16, fn, 'textures/gui/spell_icons/%s.png' % name, frame=MYTH)
    for kind in ('entangled', 'abyss_dread', 'dawn_grace'):
        _icon(18, lambda d, S, k=kind: effect_icon(d, S, k), 'textures/mob_effect/%s.png' % kind, crisp=True)


def sheet(path):
    names = [('yggdrasil', (126, 224, 74)), ('abyss_sigil', (63, 214, 184)), ('abyss_swirl', (150, 90, 200)), ('dawn_sunrise', (255, 211, 107)),
             ('mote_cloud', (200, 200, 220)), ('mote_petal', (255, 184, 224))]
    cell = 300
    out = Image.new('RGB', (cell * 3, cell * 2), (14, 12, 18))
    for i, (n, col) in enumerate(names):
        a = Image.open(os.path.join(OUT_SIGIL, n + '.png')).split()[3].resize((cell - 16, cell - 16), Image.LANCZOS)
        out.paste(Image.new('RGB', a.size, col), ((i % 3) * cell + 8, (i // 3) * cell + 8), a)
    out.save(path)
    print('sheet', path)


if __name__ == '__main__':
    textures()
    meshes()
    sigils()
    world_tree_fx()
    abyss_eye_fx()
    last_dawn_fx()
    icons()
    if '--sheet' in sys.argv:
        sheet(sys.argv[sys.argv.index('--sheet') + 1])
    print(len(WRITTEN), 'files')
