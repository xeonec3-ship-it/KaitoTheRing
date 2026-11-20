#!/usr/bin/env python3
"""
T28 — визуал босса «Арис, Мифический Кузнец» («Глава 3 Ячейки Культа»). ТЗ: docs/specs/tasks/T28_aris_boss.md.
Референсы: docs/references/t28/aris_look.jpg (внешность), docs/references/t28/aris_hammer.jpg (форма молота; цвета — палитра Арис).
Каркас моделей — tools/nightmare_geo.py (кости, кубы, атлас UV по граням, покраска в 3D, анимации).

Модель — своя, GeckoLib, кости совместимы с магами Iron's (abstract_casting_mob: body, torso, head, right_arm, left_arm, right_leg,
left_leg, bipedHandRight/Left, rightItem/leftItem, armorBiped*), плюс свои: root (над body), локти *_forearm, колени *_shin,
ленты ribbon_*, кисти tassel_*, набедренники tasset_*, задняя пластина fauld_b, коса hair1..3, молот hammer (в руке) и
hammer_ground (лежит/стоит отдельно — сдача и мирный NPC).

Пишет (src/main/resources/assets/pohsmp_core/):
  geo/entity/aris.geo.json                         модель (identifier geometry.aris), лицом к −z, ноги на y = 0
  textures/entity/aris/aris.png (+ _glowmask)      бой: рога и кайма светятся бирюзой
  textures/entity/aris/aris_dim.png (+ _glowmask)  рога гаснут (промежуточный кадр сдачи) и мирный NPC
  textures/entity/aris/aris_spent.png (+ _glowmask, пустая)  рога погасли (сдача)
  textures/entity/aris/aris_mythic.png (+ _glowmask)  фаза 3 «Мифический сплав»: броня раскалена добела
  animations/entity/aris.animation.json            аниме-анимации (animation.aris.*) — см. ANIMS
  models/item/aris_hammer.json + textures/item/aris_hammer_3d.png  молот — 3D-предмет из брусков
Остальное (fx, печати, полоса, титры, иконки, lang, звуки, кадры) — tools/gen_aris_fx.py (вызывается отсюда).

Запуск:  python3 tools/gen_aris.py [--shots] [--html]
  --shots  проверочные кадры docs/media/t28_*.jpg (Playwright + three.js r128 из node_modules или --three путь)
  --html   tools/aris_preview.html (интерактивное превью: модель, все анимации, варианты текстур, молот, меши fx)
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nightmare_geo import (Model, Anim, hex2, face_size, euler, to_euler, rx, ry, rz)  # noqa: E402

ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
TEXD = 'textures/entity/aris/'
WRITTEN = []
VARIANTS = ('base', 'dim', 'spent', 'mythic')


def out(rel):
    p = os.path.join(A, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    WRITTEN.append(rel)
    return p


def write_json(rel, obj, compact=False, indent=1):
    with open(out(rel), 'w', encoding='utf-8', newline='\n') as f:
        if compact:
            json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=indent)
        f.write('\n')


# ================================================================== палитра Арис (рампы тонов; рисуем как пиксель-арт ванили)
# Эталон — модель Главы Культа (T26): 1 тексель = 1/16 блока (= 1 ед. модели), ручная светотень по текселям без шума и сглаживания.
# Текстура хранится ×4 (4 пикселя на ед., как у cult_leader 512×512), но каждый тексель 1×1 ед. закрашен одним цветом
# (класс PixelModel: материал вызывается в центрах текселей). Кайма, ремни, камни, обручи — объёмные бруски, не рисунок.
def ramp(*hs):
    return np.array([hex2(h) for h in hs])


STEEL = ramp('#1c1c22', '#2a2a32', '#3a3a44', '#4c4c57', '#60606c', '#767682', '#8e8e9a', '#a9a9b4', '#c6c6ce')
DARK = ramp('#0e0e12', '#16161b', '#1f1f26', '#292931', '#34343e', '#42424d')
TEAL = ramp('#0a3c46', '#0f6470', '#168e9e', '#22b4c4', '#3cd6e0', '#7eeef2', '#c8fbfc')
PURP = ramp('#3a1048', '#561a6c', '#74268e', '#9234b0', '#ad46c6', '#c460d4', '#da8ce6')
STONE = ramp('#80808e', '#9e9eac', '#babac6', '#d4d4de', '#e8e8f0', '#f8f8fc')
HAIR = ramp('#6a667e', '#8a86a0', '#aaa6c0', '#c8c5da', '#e0deec', '#f2f1f8')
LEATH = ramp('#141017', '#1f1922', '#2b232f', '#3a303f', '#4a3e50')
HOT = ramp('#3a2420', '#6a3222', '#a8502a', '#d87a34', '#f4a852', '#ffd490', '#fff0d2', '#fffaf2')
TEAL_DEAD = ramp('#101a1d', '#172428', '#1e3034', '#273c40', '#314a4e', '#3c5a5e')

V = {'variant': 'base'}           # текущий вариант покраски
FACE_L = {'up': 0.16, 'north': 0.0, 'south': -0.03, 'east': -0.07, 'west': -0.07, 'down': -0.22}


def pick(r, v):
    """Тон рампы r по значению v ∈ [0, 1]."""
    i = np.clip(np.floor(np.asarray(v) * (len(r) - 0.001)), 0, len(r) - 1).astype(int)
    return r[i]


def thash(ctx, seed=0):
    """Детерминированное «случайное» число на тексель (по его центру в мире) — для редких ручных крапин."""
    q = np.floor(ctx.P * 2.0 + 0.5).astype(np.int64)
    h = (q[:, 0] * 73856093) ^ (q[:, 1] * 19349663) ^ (q[:, 2] * 83492791) ^ (seed * 2654435761 + hash(ctx.face) % 977)
    h = h & 0xFFFFFFFF
    h = ((h ^ (h >> 15)) * 2246822519) & 0xFFFFFFFF
    h = h ^ (h >> 13)
    return (h & 0xFFFF) / 65536.0


def rows(ctx):
    """Номер текселя по ширине/высоте грани и их число: (i, j, nw, nh); j = 0 — верхний ряд (у боковых граней)."""
    return ctx.i, ctx.j, ctx.nw, ctx.nh


def shade(ctx, base, edge=True, speck=0.06, seed=0):
    """Ручная светотень ванили: грань по направлению, верхний ряд — блик (фаска), нижний — тень, кант по краю, редкие крапины."""
    i, j, nw, nh = rows(ctx)
    v = base + FACE_L[ctx.face] + 0 * ctx.s
    if edge:
        side = ctx.face in ('north', 'south', 'east', 'west')
        top = (j == 0) & (nh > 1)
        bot = (j == nh - 1) & (nh > 1)
        lr = ((i == 0) | (i == nw - 1)) & (nw > 2)
        if side:
            v = v + top * 0.12 - bot * 0.14 - lr * 0.06
        else:
            v = v - (((i == 0) | (i == nw - 1) | (j == 0) | (j == nh - 1)) & (nw > 2) & (nh > 2)) * 0.07
    h = thash(ctx, seed)
    v = v - (h < speck) * 0.09 + (h > 1 - speck * 0.6) * 0.07
    return v


def no_glow(n):
    return np.zeros((n, 3))


def teal_glow(ctx, v=0.7):
    """(rgb, glow) бирюзы с учётом варианта текстуры."""
    n = ctx.n
    va = V['variant']
    if va == 'base':
        rgb = pick(TEAL, v)
        return rgb, rgb * 0.55
    if va == 'dim':
        rgb = pick(TEAL, v - 0.3)
        return rgb, rgb * 0.3
    if va == 'spent':
        return pick(TEAL_DEAD, v - 0.1), no_glow(n)
    rgb = pick(TEAL, v + 0.15)          # mythic: бирюза раскалена до бело-голубого
    return rgb, rgb * 0.7


def steel_rgb(ctx, v, dark=False):
    """Сталь; в варианте mythic — раскалена: края текселей-кантов почти белые, середина — оранжевый жар (и светится)."""
    r = DARK if dark else STEEL
    rgb = pick(r, v)
    if V['variant'] != 'mythic':
        return rgb, no_glow(ctx.n)
    i, j, nw, nh = rows(ctx)
    edge = (((i == 0) | (i == nw - 1) | (j == 0) | (j == nh - 1)) & (nw > 3) & (nh > 2)).astype(float)
    # кромки (кант) — бело-жёлтый накал и светятся; середина пластины — тёмная сталь с вишнёвым отливом
    heat = np.clip(0.3 + 0.45 * edge + (v - 0.5) * 0.5, 0, 1)
    hot = pick(HOT, heat)
    rgb = np.where(edge[:, None] > 0.5, hot, rgb * 0.7 + pick(HOT, 0.3 + (v - 0.5) * 0.4) * 0.3)
    g = np.where(edge[:, None] > 0.5, hot * 0.45, 0.0)
    return rgb, g


# ---------------------------------------------------------------- материалы
def m_plate(base=0.55, dark=False, rivets=False, seed=0):
    def fn(ctx):
        v = shade(ctx, base, seed=seed)
        rgb, g = steel_rgb(ctx, v, dark)
        if rivets and ctx.face in ('north', 'south', 'east', 'west'):
            i, j, nw, nh = rows(ctx)
            riv = ((i == 1) | (i == nw - 2)) & (j == 1) & (nw > 4) & (nh > 2)
            rgb = np.where(riv[:, None], pick(STEEL, 0.95 + 0 * v), rgb)
        return rgb, 1.0, g
    return fn


def m_chain(ctx):
    """Поддоспешник-кольчуга: шахматка тёмных колец по текселям."""
    i, j, nw, nh = rows(ctx)
    ring = ((i + j) % 2 == 0)
    v = 0.3 + ring * 0.25 + FACE_L[ctx.face]
    return pick(DARK, v), 1.0, no_glow(ctx.n)


def m_trim(ctx):
    i, j, nw, nh = rows(ctx)
    v = 0.5 + FACE_L[ctx.face] * 0.8 + ((j == 0) & (nh > 1)) * 0.12 - ((j == nh - 1) & (nh > 1)) * 0.12
    rgb, g = teal_glow(ctx, v)
    return rgb, 1.0, g


def m_stone(ctx):
    i, j, nw, nh = rows(ctx)
    v = 0.55 + FACE_L[ctx.face] * 1.2 + ((i == 0) | (j == 0)) * 0.18 - ((i == nw - 1) | (j == nh - 1)) * 0.2
    rgb = pick(STONE, v)
    g = no_glow(ctx.n)
    if V['variant'] == 'mythic':
        g = pick(HOT, 0.75 + 0 * v) * 0.3
    return rgb, 1.0, g


def m_horn(ctx):
    """Рог: у основания — сталь, выше — бирюза, светится к кончику; кольца-сегменты по 1.5 ед."""
    y = ctx.P[:, 1]
    k = np.clip((y - 34.0) / 10.0, 0, 1)
    seg = (np.floor(y / 1.5) % 2) * 0.07
    steel, _ = steel_rgb(ctx, shade(ctx, 0.5, seed=21) + seg)
    va = V['variant']
    n = ctx.n
    lo = {'base': 0.05, 'dim': 0.5, 'mythic': 0.0, 'spent': 0.05}[va]
    blend = (k > lo)[:, None]
    t = np.clip((k - lo) / (1 - lo + 1e-6), 0, 1)
    tv = 0.34 + 0.36 * t + seg + FACE_L[ctx.face] * 0.6
    if va == 'spent':
        rgb = np.where(blend, pick(TEAL_DEAD, tv - 0.1), steel)
        return rgb, 1.0, no_glow(n)
    if va == 'dim':
        tv = tv - 0.28
    if va == 'mythic':
        tv = tv + 0.15
    tc = pick(TEAL, tv)
    rgb = np.where(blend, tc, steel)
    gk = {'base': 0.7, 'dim': 0.3, 'mythic': 0.8}[va]
    g = np.where(blend, tc * gk * (0.45 + 0.4 * t)[:, None], 0)
    return rgb, 1.0, g


def m_visor(ctx):
    """Чёрная прорезь визора; в глубине — два бирюзовых глаза (светятся, гаснут при сдаче)."""
    x = ctx.P[:, 0]
    rgb = pick(DARK, 0.0 + 0 * x)
    g = no_glow(ctx.n)
    if False:
        eye = (np.abs(np.abs(x) - 1.5) < 0.5)
        ec = pick(TEAL, (0.62 if V['variant'] != 'dim' else 0.36) + 0 * x)
        rgb = np.where(eye[:, None], ec, rgb)
        g = np.where(eye[:, None], ec * (0.8 if V['variant'] != 'dim' else 0.3), g)
    return rgb, 1.0, g


def m_grille(ctx):
    """Забрало: сталь с рядами отверстий (каждый второй тексель — тёмный)."""
    v = shade(ctx, 0.56, seed=33)
    rgb, g = steel_rgb(ctx, v)
    if ctx.face == 'north':
        i, j, nw, nh = rows(ctx)
        hole = (i % 2 == 1) & (j >= 1) & (j <= 2) & (i > 0) & (i < nw - 1) & (np.abs(ctx.P[:, 0]) > 0.8)
        rgb = np.where(hole[:, None], pick(STEEL, 0.15 + 0 * v), rgb)
    return rgb, 1.0, g


def m_ribbon(fringe=False):
    def fn(ctx):
        i, j, nw, nh = rows(ctx)
        v = 0.66 + FACE_L[ctx.face] * 0.8 + ((i == 0) | (i == nw - 1)) * -0.16 + ((j % 4) == 0) * 0.08
        rgb = pick(PURP, v)
        a = np.ones(ctx.n)
        if fringe and ctx.face in ('north', 'south', 'east', 'west'):
            a = np.where((j >= nh - 2) & (i % 2 == 1) & (nh > 3), 0.0, 1.0)
        return rgb, a, no_glow(ctx.n)
    return fn


def m_hair(ctx):
    i, j, nw, nh = rows(ctx)
    v = 0.6 + FACE_L[ctx.face] * 0.9 + (i % 2 == 1) * -0.12 + ((j % 3) == 0) * 0.06 - ((i == 0) | (i == nw - 1)) * 0.1
    return pick(HAIR, v), 1.0, no_glow(ctx.n)


def m_leather(ctx):
    v = shade(ctx, 0.5, speck=0.1, seed=71)
    return pick(LEATH, v), 1.0, no_glow(ctx.n)


def m_h(kind):
    """Материалы молота: hk — ударная плоскость, hd — тёмная сталь бойков, hs/hs2 — серая сталь обручей, hsh — древко,
    hg — бирюзовые светящиеся вставки, hw — лиловая обмотка, hst — белый камень."""
    def fn(ctx):
        if kind == 'hk':
            rgb, g = steel_rgb(ctx, shade(ctx, 0.25, seed=101), True)
            return rgb, 1.0, g
        if kind == 'hd':
            rgb, g = steel_rgb(ctx, shade(ctx, 0.62, seed=103), True)
            return rgb, 1.0, g
        if kind in ('hs', 'hs2'):
            rgb, g = steel_rgb(ctx, shade(ctx, 0.5 if kind == 'hs' else 0.66, seed=107))
            return rgb, 1.0, g
        if kind == 'hsh':
            rgb, g = steel_rgb(ctx, shade(ctx, 0.45, edge=False, seed=109), True)
            return rgb, 1.0, g
        if kind == 'hg':
            return m_trim(ctx)
        if kind == 'hw':
            i, j, nw, nh = rows(ctx)
            v = 0.58 + FACE_L[ctx.face] * 0.8 - (j == nh - 1) * 0.18
            return pick(PURP, v), 1.0, no_glow(ctx.n)
        if kind == 'hst':
            return m_stone(ctx)
        raise KeyError(kind)
    return fn


MATS = {
    'plate': m_plate(0.56, seed=1), 'plate_l': m_plate(0.7, seed=2), 'plate_d': m_plate(0.62, dark=True, seed=3),
    'pauldron': m_plate(0.62, rivets=True, seed=7), 'gaunt': m_plate(0.72, dark=True, rivets=True, seed=8),
    'chain': m_chain, 'trim': m_trim, 'stone': m_stone, 'horn': m_horn, 'visor': m_visor, 'grille': m_grille,
    'ribbon': m_ribbon(), 'tassel': m_ribbon(True), 'hair': m_hair, 'leather': m_leather,
    'hk': m_h('hk'), 'hd': m_h('hd'), 'hs': m_h('hs'), 'hs2': m_h('hs2'), 'hsh': m_h('hsh'), 'hg': m_h('hg'), 'hw': m_h('hw'),
    'hst': m_h('hst'),
}


class PixelModel(Model):
    """Model с покраской по текселям 1×1 ед.: материал получает центры текселей (ctx.i, ctx.j, ctx.nw, ctx.nh)."""

    def paint(self, base_img=None):
        from nightmare_geo import Ctx, face_point
        W, H = self.tex_px
        img = np.zeros((H, W, 4), float)
        glow = np.zeros((H, W, 4), float)
        for bn in self.order:
            for ci, c in enumerate(self.bones[bn].cubes):
                if not c.px:
                    continue
                M, o = self.cube_xf(bn, c)
                fn = self.materials[c.mat]
                for f, (x, y, pw, ph) in c.px.items():
                    fw, fh = face_size(c, f)
                    nw, nh = max(1, int(round(fw))), max(1, int(round(fh)))
                    ss, tt = np.meshgrid((np.arange(pw) + 0.5) / pw, (np.arange(ph) + 0.5) / ph)
                    ii = np.minimum(np.floor(ss.ravel() * nw), nw - 1)
                    jj = np.minimum(np.floor(tt.ravel() * nh), nh - 1)
                    s2, t2 = (ii + 0.5) / nw, (jj + 0.5) / nh
                    P, nrm = face_point(c, f, s2, t2)
                    Pw = P @ M.T + o
                    ctx = Ctx(Pw, np.tile(M @ nrm, (len(Pw), 1)), s2, t2, f, c, bn, P)
                    ctx.i, ctx.j, ctx.nw, ctx.nh = ii.astype(int), jj.astype(int), nw, nh
                    rgb, a, g = fn(ctx)
                    a = np.broadcast_to(np.asarray(a, float), (len(Pw),))
                    img[y:y + ph, x:x + pw, :3] = np.clip(rgb, 0, 1).reshape(ph, pw, 3)
                    img[y:y + ph, x:x + pw, 3] = np.clip(a, 0, 1).reshape(ph, pw)
                    g = np.asarray(g, float)
                    glow[y:y + ph, x:x + pw, :3] = np.clip(g[:, :3], 0, 1).reshape(ph, pw, 3)
                    glow[y:y + ph, x:x + pw, 3] = (np.clip(g.max(1), 0, 1) > 0.02).reshape(ph, pw) * np.clip(a, 0, 1).reshape(ph, pw)
        img[..., 3] = (img[..., 3] > 0.5).astype(float)
        self.image = Image.fromarray((img * 255 + 0.5).astype(np.uint8), 'RGBA')
        self.glow = Image.fromarray((glow * 255 + 0.5).astype(np.uint8), 'RGBA')
        return self.image


# ================================================================== молот (общая геометрия: предмет и кость модели)
# Единицы предмета (1/16 блока): рукоять вдоль +y, низ навершия y = 0, центр x = z = 0. Бойки — по ±x, накладка-ромб смотрит в ±z.
# (cx, cy, cz, sx, sy, sz, материал, поворот вокруг z, °)
def hammer_parts():
    P = []

    def b(cx, cy, cz, sx, sy, sz, mat, rz_=0.0):
        P.append((cx, cy, cz, sx, sy, sz, mat, rz_))
    # навершие-противовес и белый камень внизу
    b(0, -0.15, 0, 1.0, 0.3, 1.0, 'hst')
    b(0, 0.3, 0, 1.8, 0.6, 1.8, 'hd')
    b(0, 1.35, 0, 2.5, 1.5, 2.5, 'hs')
    b(0, 1.35, 0, 2.7, 0.5, 2.7, 'hg')
    # рукоять: обмотка кольцами (лиловая) с серыми обручами
    y = 2.1
    k = 0
    while y < 8.9:
        h = 0.72
        b(0, y + h / 2, 0, 2.0 if k % 2 == 0 else 1.8, h - 0.06, 2.0 if k % 2 == 0 else 1.8, 'hw')
        y += h
        k += 1
    for yy in (4.45, 6.85):
        b(0, yy, 0, 2.25, 0.4, 2.25, 'hs2')
    b(0, 9.15, 0, 2.5, 0.5, 2.5, 'hs2')            # гарда хвата
    b(0, 9.65, 0, 2.2, 0.5, 2.2, 'hg')
    # древко
    b(0, 15.5, 0, 1.55, 11.8, 1.55, 'hsh')
    b(0, 12.9, 0, 1.9, 0.55, 1.9, 'hs')
    # «лесенка» под головой (на референсе золотая — у Арис серая сталь + бирюза)
    for sx in (-1, 1):
        b(sx * 1.2, 18.2, 0, 0.5, 6.0, 1.5, 'hs2')
    for yy in (15.9, 17.5, 19.1, 20.6):
        b(0, yy, 0, 2.3, 0.45, 1.75, 'hg')
    b(1.95, 17.6, 0, 0.5, 2.6, 1.2, 'hs2')          # крюк-завиток сбоку (асимметрия, как на референсе)
    b(2.35, 16.4, 0, 0.9, 0.5, 1.2, 'hg')
    # втулка под головой
    b(0, 20.8, 0, 2.4, 0.8, 2.4, 'hd')
    b(0, 21.6, 0, 3.4, 0.9, 3.4, 'hs2')
    # голова: сердцевина серой стали, обручи, бирюзовые вставки
    b(0, 26.5, 0, 10.4, 7.8, 6.0, 'hs')
    for sx in (-1, 1):
        b(sx * 4.35, 26.5, 0, 0.95, 8.6, 6.7, 'hs2')       # обручи
        b(sx * 2.85, 26.5, 0, 0.5, 8.15, 6.3, 'hg')        # бирюзовые полосы
        b(sx * 1.3, 26.5, 0, 0.55, 8.1, 6.25, 'hs2')
        # бойки — тёмная сталь, массивные
        b(sx * 7.1, 26.5, 0, 3.8, 9.8, 8.0, 'hd')
        b(sx * 9.25, 26.5, 0, 0.5, 8.6, 6.8, 'hk')         # ударная плоскость
        b(sx * 7.1, 31.55, 0, 3.4, 0.4, 7.2, 'hs2')        # светлая фаска сверху
        b(sx * 7.1, 21.45, 0, 3.4, 0.4, 7.2, 'hs')
        b(sx * 5.35, 26.5, 0, 0.35, 9.4, 8.1, 'hg')        # бирюзовый шов между головой и бойком
        b(sx * 7.1, 26.5, sx * 0, 3.0, 1.2, 8.3, 'hs')     # пояс по бойку
    # накладка-ромб в центре (обе стороны): бирюзовая рамка, сталь, белый камень
    for sz in (-1, 1):
        b(0, 26.5, sz * 3.1, 4.6, 4.6, 0.6, 'hg', 45)
        b(0, 26.5, sz * 3.35, 3.2, 3.2, 0.6, 'hs2', 45)
        b(0, 26.5, sz * 3.6, 1.7, 1.7, 0.6, 'hst', 45)
        b(0, 30.0, sz * 3.15, 1.6, 0.7, 0.5, 'hg')
        b(0, 23.0, sz * 3.15, 1.6, 0.7, 0.5, 'hg')
    # верх головы: корона-шип
    b(0, 30.9, 0, 2.6, 1.0, 2.6, 'hs2')
    b(0, 31.75, 0, 1.4, 0.8, 1.4, 'hg')
    b(0, 32.4, 0, 0.6, 0.6, 0.6, 'hst')
    return P


HAM_GRIP = 7.9           # точка хвата правой рукой (ед. предмета от низа навершия): верх обмотки
HAM_GRIP2 = 3.2          # левая рука — у навершия
HAM_HEAD = 26.5          # центр головы
HAM_FACE = 9.5           # от оси до ударной плоскости
HAM_S = 0.75             # масштаб молота на модели (ед. предмета → ед. модели): длина ≈ 1.74 бл.


def add_hammer(m, bone, xform):
    """Кубы молота в кость. xform(точка предмета) → точка модели (без поворота рукояти — его даёт кость)."""
    for (cx, cy, cz, sx, sy, sz, mat, rz_) in hammer_parts():
        c = np.array(xform((cx, cy, cz)))
        s = np.array([sx, sz, sy]) * HAM_S            # предмет (x, y, z) → кость (x, z, −y): высота по y предмета → глубина по z
        if rz_:
            m.cbox(bone, c, s, mat, rot=(0, rz_, 0), pivot=list(c))
        else:
            m.cbox(bone, c, s, mat)


def ham_local(p):
    """Точка предмета → локальные координаты кости hammer (пивот = хват правой руки, рукоять вдоль −z: голова впереди)."""
    x, y, z = p
    return (x * HAM_S, z * HAM_S, -(y - HAM_GRIP) * HAM_S)


# ================================================================== модель
FIST_R = np.array([6.0, 12.0, 0.0])      # центр кулака (покой), правая
ELBOW_R = np.array([6.0, 17.0, 0.0])
SHOULDER_R = np.array([5.0, 22.0, 0.0])


def mirror(p):
    return (-p[0], p[1], p[2])


def build_model():
    m = PixelModel('aris', density=4, tex_w=128)
    m.materials = MATS
    m.bone('root', None, (0, 0, 0))
    m.bone('body', 'root', (0, 12, 0))
    m.bone('torso', 'body', (0, 24, 0))
    m.bone('armorBipedBody', 'torso', (0, 24, 0))
    m.bone('head', 'body', (0, 24, 0))
    m.bone('armorBipedHead', 'head', (0, 24, 0))
    T = 'torso'

    # ---------------- торс: кольчуга, кираса, пластины живота, пояс, горжет; кайма — бруски
    m.box(T, (-3, 12, -2), (3, 24, 2), 'chain')
    m.box(T, (-4.5, 17, -2.75), (4.5, 23.5, 2.25), 'plate')
    m.box(T, (-2.0, 23.25, -3.3), (2.0, 23.75, -2.6), 'trim')                   # кайма по вырезу кирасы
    for i, (y0, w, z) in enumerate(((21.0, 8.5, -3.25), (19.0, 8.0, -3.15), (17.25, 7.5, -3.0))):   # грудь: горизонтальные пластины внахлёст
        m.box(T, (-w / 2, y0, z), (w / 2, y0 + 2.25, -2.5), 'plate_l' if i == 0 else 'plate')
    m.box(T, (-3.5, 17.0, -3.25), (3.5, 17.5, -2.75), 'trim')
    for i, (y0, w) in enumerate(((15.75, 7.25), (14.5, 6.75), (13.25, 6.5))):  # пластины живота
        m.box(T, (-w / 2, y0, -2.5 + i * 0.1), (w / 2, y0 + 1.5, 2.1), 'plate')
    m.box(T, (-3.25, 13.25, -2.75), (3.25, 13.75, 2.25), 'trim')                 # кайма нижней пластины
    for sx in (-1, 1):                                                          # V-кайма (как на референсе)
        m.rod(T, (sx * 3.4, 17.3, -2.75), (sx * 0.1, 14.2, -2.75), 0.5, 0.5, mat='trim', ext=0.2)
    m.box(T, (-3.75, 12, -2.5), (3.75, 13.25, 2.35), 'leather')                  # пояс
    m.cbox(T, (0, 12.6, -2.75), (1.5, 1.5, 0.5), 'trim')                          # пряжка-камень
    for sx in (-1, 1):
        m.cbox(T, (sx * 2.5, 12.6, -2.6), (0.75, 0.75, 0.5), 'plate_l')
    m.box(T, (-2.75, 23, -2.5), (2.75, 25, 2.25), 'plate_d')                      # горжет
    m.box(T, (-3.0, 24.25, -2.75), (3.0, 24.75, 2.5), 'trim')                     # бирюза у воротника (как на референсе)
    m.box(T, (-4.75, 23.5, 0.5), (4.75, 27.5, 2.75), 'plate')                      # высокий воротник за головой
    m.box(T, (-4.5, 27.25, 0.75), (4.5, 27.75, 2.75), 'trim')
    m.cbox(T, (0, 19.5, 2.5), (3, 7, 0.75), 'plate')                               # хребет спины
    m.box(T, (-1.75, 16, 2.75), (1.75, 16.5, 3.0), 'trim')
    for sx in (-1, 1):                                                          # белые камни у ключиц + оправа
        m.cbox(T, (sx * 3.25, 23.25, -3.0), (3.25, 3.25, 0.75), 'plate_d')
        m.cbox(T, (sx * 3.25, 23.25, -3.5), (2.5, 2.5, 1.5), 'stone')

    # ---------------- голова: закрытый шлем, прорезь, забрало, гребень, шип, «крылья», рога
    H = 'head'
    m.cbox(H, (0, 28.25, 0), (6.5, 7, 6.5), 'plate_d')
    m.box(H, (-3.75, 24.5, -4), (3.75, 32, 3.75), 'plate_l')
    m.box(H, (-3.75, 25, -4.25), (3.75, 28.25, -3.9), 'grille')                    # забрало с отверстиями
    m.box(H, (-3, 28.25, -4.15), (3, 29.25, -3.9), 'visor')                        # прорезь с глазами
    m.box(H, (-4, 29.25, -4.4), (4, 30.25, -3.75), 'plate_l')                      # надбровье
    m.box(H, (-0.5, 25, -4.6), (0.5, 32.75, -4.0), 'plate_l')                     # гребень по лицу
    m.box(H, (-0.5, 31.75, -3.5), (0.5, 33, 3), 'plate_d')                        # гребень по темени
    m.rod(H, (0, 32.75, -2.75), (0, 35.75, -4), 1, mat='plate_d')                 # шип на темени (как на референсе)
    for sx in (-1, 1):
        m.cbox(H, (sx * 4.25, 29.25, 0.5), (1, 4.5, 4.75), 'plate')                # нащёчники-крылья
        m.rod(H, (sx * 4.0, 27.0, 0.75), (sx * 6.5, 32.5, 1.0), 1.75, 3.5, mat='plate_l')  # крылья шлема вверх к рогам
        m.rod(H, (sx * 4.25, 26.0, 1.75), (sx * 7.0, 30.0, 2.75), 1.25, 2.0, mat='plate')
        # рога: с верха шлема, толстые, почти вертикальные с лёгким S-изгибом (как на референсе)
        pts = [(2.75, 31.25, 0.5), (4.25, 33.75, 0.5), (5.5, 36.5, 0.6), (6.0, 39.5, 0.6), (5.75, 42.5, 0.4), (5.25, 45.0, 0.2)]
        ws = [3.0, 2.75, 2.5, 2.25, 2.0]
        for i in range(len(pts) - 1):
            p, q = np.array(pts[i]) * [sx, 1, 1], np.array(pts[i + 1]) * [sx, 1, 1]
            m.rod(H, p, q, ws[i], mat='horn', ext=0.25)
        m.cbox(H, (sx * 2.75, 31.5, 0.5), (3, 1.5, 3.25), 'plate_l')                # основание рога
    m.cbox(H, (0, 29.75, 4.0), (2.25, 2.25, 0.75), 'trim')                        # кольцо косы

    # ---------------- коса (серебряные волосы из-под шлема)
    m.bone('hair1', H, (0, 29.5, 4.25))
    m.rod('hair1', (0, 29.5, 4.25), (0, 24.75, 5.75), 2, 1.5, mat='hair', ext=0.3)
    m.bone('hair2', 'hair1', (0, 24.75, 5.75))
    m.rod('hair2', (0, 24.75, 5.75), (0, 19.5, 6.25), 1.75, 1.5, mat='hair', ext=0.3)
    m.cbox('hair2', (0, 24.5, 5.8), (2.25, 0.75, 2), 'ribbon')
    m.bone('hair3', 'hair2', (0, 19.5, 6.25))
    m.rod('hair3', (0, 19.5, 6.25), (0, 14.5, 6.0), 1.5, 1.25, mat='hair', ext=0.3)
    m.rod('hair3', (0, 14.5, 6.0), (0, 12.5, 5.75), 0.75, 0.75, mat='hair')
    m.cbox('hair3', (0, 15.0, 6.0), (1.75, 0.5, 1.5), 'trim')

    # ---------------- ленты с камней, кисти на бёдрах, набедренники, задняя пластина
    for sx, nm in ((1, 'r'), (-1, 'l')):
        top = np.array([sx * 3.25, 22.25, -3.9])
        p1, p2, p3 = np.array([sx * 3.4, 16.0, -3.9]), np.array([sx * 3.5, 9.75, -4.1]), np.array([sx * 3.6, 4.0, -4.3])
        m.bone('ribbon_%s1' % nm, T, top)
        m.rod('ribbon_%s1' % nm, top, p1, 2.75, 0.5, mat='ribbon', ext=0.15)
        m.bone('ribbon_%s2' % nm, 'ribbon_%s1' % nm, p1)
        m.rod('ribbon_%s2' % nm, p1, p2, 2.75, 0.5, mat='ribbon', ext=0.15)
        m.bone('ribbon_%s3' % nm, 'ribbon_%s2' % nm, p2)
        m.rod('ribbon_%s3' % nm, p2, p3, 2.75, 0.5, mat='ribbon', ext=0.15)
        m.cbox('ribbon_%s3' % nm, p3 + [0, -1.25, 0], (2.75, 2.5, 0.5), 'tassel')
        m.bone('tassel_%s' % nm, 'body', (sx * 5.5, 12.75, -0.5))
        x0, x1 = sorted((sx * 5.0, sx * 6.0))
        m.box('tassel_%s' % nm, (x0, 2.5, -2.5), (x1, 12.5, 1.5), 'tassel')
        x0, x1 = sorted((sx * 4.75, sx * 6.25))
        m.box('tassel_%s' % nm, (x0, 11.75, -2.75), (x1, 12.75, 1.75), 'plate_d')
        # латная юбка до земли (идёт за ногой): две пластины внахлёст спереди, боковая; бирюзовые шевроны — бруски
        m.bone('tasset_%s' % nm, 'body', (sx * 2.5, 12.5, -0.5))
        X = lambda a, b: tuple(sorted((sx * a, sx * b)))
        x0, x1 = X(0.0, 4.75)
        m.box('tasset_%s' % nm, (x0, 7.0, -3.0), (x1, 12.5, -2.25), 'plate')
        m.box('tasset_%s' % nm, (x0, 7.0, -3.25), (x1, 7.5, -2.25), 'trim')
        x0, x1 = X(0.0, 5.25)
        m.box('tasset_%s' % nm, (x0, 1.0, -3.75), (x1, 7.25, -2.75), 'plate_d')
        m.box('tasset_%s' % nm, (x0, 1.0, -4.0), (x1, 1.5, -2.75), 'trim')
        m.rod('tasset_%s' % nm, (sx * 4.75, 11.75, -3.2), (sx * 0.25, 9.0, -3.2), 0.5, 0.5, mat='trim', ext=0.2)
        m.rod('tasset_%s' % nm, (sx * 5.0, 5.75, -3.95), (sx * 0.25, 3.25, -3.95), 0.5, 0.5, mat='trim', ext=0.2)
        x0, x1 = X(4.5, 5.25)
        m.box('tasset_%s' % nm, (x0, 1.0, -2.75), (x1, 12.25, 2.5), 'plate')
    m.bone('fauld_b', 'body', (0, 12.5, 2.25))
    m.box('fauld_b', (-4.75, 7.0, 2.25), (4.75, 12.5, 2.75), 'plate')
    m.box('fauld_b', (-5.25, 1.0, 2.5), (5.25, 7.25, 3.5), 'plate_d')
    m.box('fauld_b', (-5.25, 6.75, 2.75), (5.25, 7.25, 3.75), 'trim')
    m.box('fauld_b', (-5.25, 1.0, 3.25), (5.25, 1.5, 3.75), 'trim')

    # ---------------- руки
    for sx, nm, side in ((1, 'right', 'Right'), (-1, 'left', 'Left')):
        S = np.array(SHOULDER_R) * [sx, 1, 1]
        E = np.array(ELBOW_R) * [sx, 1, 1]
        arm, fore = nm + '_arm', nm + '_forearm'
        X = lambda a, b: tuple(sorted((sx * a, sx * b)))
        m.bone(arm, 'body', S)
        m.bone('armorBiped%sArm' % side, arm, S)
        x0, x1 = X(4.25, 7.75)
        m.box(arm, (x0, 17, -1.75), (x1, 22.5, 1.75), 'chain')
        x0, x1 = X(4, 8)
        m.box(arm, (x0, 17.5, -2), (x1, 20.75, 2), 'plate')
        # наплечник: три пластины веером, под каждой — бирюзовая кайма-брусок; «перья» в стороны (как на референсе)
        for li, (cx, cy, w, h, d, a) in enumerate(((6.5, 23, 6.5, 3, 7, -14), (7.5, 21, 6.25, 2.25, 7.5, -24), (8.25, 19.25, 5.5, 2, 7, -32))):
            r, pv = (0, 0, sx * a), [sx * cx, cy, 0]
            m.cbox(arm, (sx * cx, cy, 0), (w, h, d), 'pauldron' if li != 1 else 'plate_l', rot=r, pivot=pv)
            if li == 2:
                m.cbox(arm, (sx * cx, cy - h / 2 + 0.25, 0), (w + 0.2, 0.5, d + 0.3), 'trim', rot=r, pivot=pv)
        m.cbox(arm, (sx * 6, 24.75, 0), (4.5, 0.75, 5.5), 'plate_l', rot=(0, 0, sx * -14), pivot=[sx * 6, 24.75, 0])
        m.rod(arm, (sx * 9.0, 23.75, -1.0), (sx * 15.0, 24.0, -1.0), 2.0, 2.5, mat='plate_l')
        m.rod(arm, (sx * 9.5, 21.75, 0.75), (sx * 14.5, 21.25, 1.25), 1.75, 2.25, mat='plate')
        m.rod(arm, (sx * 9.0, 19.75, 1.5), (sx * 13.0, 19.0, 2.0), 1.5, 1.75, mat='plate_d')
        m.cbox(arm, (sx * 6.5, 23, -3.6), (2, 2, 0.5), 'stone', rot=(0, 0, 45), pivot=[sx * 6.5, 23, -3.6])
        # предплечье
        m.bone(fore, arm, E)
        m.cbox(fore, (sx * 6, 17, 0.25), (4.5, 2.5, 4.5), 'plate')                      # налокотник
        m.cbox(fore, (sx * 8.4, 17, 0.5), (0.5, 2, 2.25), 'trim')                       # бирюзовый веер на локте
        x0, x1 = X(4.1, 7.9)
        m.box(fore, (x0, 13.5, -2.1), (x1, 16, 2.1), 'plate')
        x0, x1 = X(3.75, 8.25)
        m.box(fore, (x0, 13, -2.5), (x1, 14, 2.5), 'plate_l')
        m.box(fore, (x0, 13.75, -2.6), (x1, 14.25, 2.6), 'trim')
        x0, x1 = X(4.25, 7.75)
        m.box(fore, (x0, 10.75, -2.25), (x1, 13, 2.25), 'gaunt')
        x0, x1 = X(4, 8)
        m.box(fore, (x0, 10.5, -1.75), (x1, 11.25, 1.75), 'plate_d')
        m.bone('bipedHand%s' % side, fore, (sx * 6, 13, -1))
        if nm == 'right':
            m.bone('rightItem', fore, (6, 12, 0), rot=(90, 0, 0))
        else:
            m.bone('leftItem', 'bipedHandLeft', (-6, 12, 0))
    m.bone('hammer', 'right_forearm', FIST_R)
    add_hammer(m, 'hammer', lambda p: FIST_R + ham_local(p))
    m.bone('hammer_ground', 'root', HG_PIVOT)
    add_hammer(m, 'hammer_ground', lambda p: HG_PIVOT + hg_local(p))

    # ---------------- ноги
    for sx, nm, side in ((1, 'right', 'Right'), (-1, 'left', 'Left')):
        leg, shin = nm + '_leg', nm + '_shin'
        X = lambda a, b: tuple(sorted((sx * a, sx * b)))
        m.bone(leg, 'body', (sx * 2, 12, 0))
        m.bone('armorBiped%sLeg' % side, leg, (sx * 2, 12, 0))
        m.bone('armorBiped%sFoot' % side, leg, (sx * 2, 12, 0))
        x0, x1 = X(0.25, 3.75)
        m.box(leg, (x0, 6, -1.75), (x1, 12, 1.75), 'chain')
        x0, x1 = X(0, 4)
        m.box(leg, (x0, 7, -2.25), (x1, 11, 1.75), 'plate')
        m.bone(shin, leg, (sx * 2, 6.25, 0))
        m.cbox(shin, (sx * 2, 6.25, -0.5), (4.5, 2.5, 3.75), 'plate_l')                # наколенник
        m.cbox(shin, (sx * 2, 6.5, -2.5), (2, 2, 0.5), 'trim', rot=(0, 0, 45), pivot=[sx * 2, 6.5, -2.5])
        m.cbox(shin, (sx * 4.35, 6.25, -0.25), (0.5, 2, 2.25), 'trim')
        x0, x1 = X(0.1, 3.9)
        m.box(shin, (x0, 1.5, -2.1), (x1, 5.25, 1.9), 'plate')
        x0, x1 = X(-0.15, 4.15)
        m.box(shin, (x0, 4.75, -2.35), (x1, 5.25, 2.15), 'trim')
        x0, x1 = X(-0.1, 4.1)
        m.box(shin, (x0, 0, -3.5), (x1, 1.75, 2.25), 'plate_d')                        # сабатон
        x0, x1 = X(0.5, 3.5)
        m.box(shin, (x0, 0, -4.5), (x1, 1.25, -3.25), 'plate')
        m.box(shin, (x0, 1.5, -2.75), (x1, 2, -1.0), 'trim')
    return m


# молот отдельно от руки: пивот — точка касания земли (под короной головы); в покое стоит головой вниз, рукоятью вверх, справа от Арис.
# Анимации: сдача — она ставит молот так, потом он падает (поворот вокруг пивота), мирный NPC — стоит/лежит рядом.
HG_PIVOT = np.array([10.0, 0.0, -3.0])
HG_TOP = 32.7            # верх короны (ед. предмета) — касается земли
HG_SINK = 0.5            # чуть вдавлен в землю


def hg_local(p):
    x, y, z = p
    return (x * HAM_S, (HG_TOP - y) * HAM_S - HG_SINK, z * HAM_S)


if __name__ == '__main__':
    import gen_aris_anims as AN   # noqa: E402
    AN.main(sys.modules[__name__], sys.argv[1:])
