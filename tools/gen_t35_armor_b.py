#!/usr/bin/env python3
"""
T35 «Броня боссов» — часть помощника B: «Доспех Полководца» (warlord, Мартин), «Камзол Предателя» (traitor, Эреб),
«Маска Лжи» (mask_of_lies, Эреб, Длань Лжи). ТЗ: docs/specs/tasks/T35_boss_armor_sets.md.

Эталон (docs/inbox/README.md): стиль Iron's/ванили, текстура ×4 как у Главы Культа (4 пикселя на единицу UV, атлас 128 ед. → 512 px),
ручная пиксельная светотень без шума. Каркас — tools/nightmare_geo.py (как у Мартина T29): per-face UV, покраска по точке тела.
Материалы Мартина берутся из tools/gen_martin.py (сталь, золото, красное сукно, чёрно-белый плащ) — броня узнаваемо «его».

Система координат при проектировании (как во всех наших генераторах на nightmare_geo): **правая сторона игрока — +x, лицо — −z**,
ноги на y = 0. В .geo.json x зеркалится (правая рука → bipedRightArm с pivot [-5, 22, 0], как у брони ведьмы и шаблона GeckoLib),
у вращений x/y меняется знак — это делает nightmare_geo, вручную знаки НЕ переворачивать (прошлая ошибка двойного переворота).

Скелет — кости GeoArmorRenderer (GeckoLib 4.8.4): bipedHead>armorHead, bipedBody>armorBody, bipedRightArm>armorRightArm,
bipedLeftArm>armorLeftArm, bipedRightLeg>armorRightLeg+armorRightBoot, bipedLeftLeg>armorLeftLeg+armorLeftBoot.
Слоты: HEAD — armorHead, CHEST — armorBody + руки, LEGS — armorRightLeg/armorLeftLeg, FEET — armorRightBoot/armorLeftBoot.

Свои кости ткани (ось у верхнего края) качаются анимацией; плащ ещё и следует за ногами в коде (см. письмо программисту):
  warlord: cape → cape_low (плащ, armorBody — в коде следует за ногой, отставшей назад); шлем: plume → plume_tip (плюмаж);
           tabard_r / tabard_l — половины табарда на костях ног (armorRightLeg / armorLeftLeg, слот LEGS): ходят с ногой, сквозь неё не проходят
  traitor: coat_front_r/_l, coat_back_r/_l — полы камзола на костях ног (слот LEGS, как юбка ведьмы), collar_back — на armorBody
  mask_of_lies: mask (поверх шлема) и mask_face (на лице без шлема) — код показывает одну из двух.
Угол в BB = внутренний угол GeckoLib (GeoBone.getRotX): x > 0 — подол вперёд (−z), x < 0 — назад.

Пишет (assets/pohsmp_core/):
  geo/armor/{warlord,traitor,mask_of_lies}.geo.json, textures/armor/<id>.png (+ _glowmask.png), animations/armor/<id>.animation.json
  textures/item/{warlord,traitor}_{helmet,chestplate,leggings,boots}.png, mask_of_lies.png (16×16), models/item/*.json
  lang: названия частей под вид моделей (ru_ru / en_us; подсказки бонусов — ключи программиста)
Запуск: python3 tools/gen_t35_armor_b.py        (кадры и видео — tools/t35_armor_render_b.py)
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nightmare_geo import Model, Anim, write_json as _wj, _hash, fbm  # noqa: E402
import gen_martin as M  # noqa: E402  (только материалы и палитры; генерация Мартина не запускается)

ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
DENS = 4
WRITTEN = []

tone, info, bevel, handf, _pix, _pix2, SIDE = M.tone, M.info, M.bevel, M.handf, M._pix, M._pix2, M.SIDE


def out(rel):
    p = os.path.join(A, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    WRITTEN.append(rel)
    return p


def write_json(rel, obj, compact=False):
    _wj(out(rel), obj, compact=compact)


# ================================================================== скелет брони (BB: правая сторона +x)
SKEL = (('bipedHead', None, (0, 24, 0)), ('armorHead', 'bipedHead', (0, 24, 0)),
        ('bipedBody', None, (0, 24, 0)), ('armorBody', 'bipedBody', (0, 24, 0)),
        ('bipedRightArm', None, (5, 22, 0)), ('armorRightArm', 'bipedRightArm', (5, 22, 0)),
        ('bipedLeftArm', None, (-5, 22, 0)), ('armorLeftArm', 'bipedLeftArm', (-5, 22, 0)),
        ('bipedRightLeg', None, (1.9, 12, 0)), ('armorRightLeg', 'bipedRightLeg', (1.9, 12, 0)),
        ('armorRightBoot', 'bipedRightLeg', (1.9, 12, 0)),
        ('bipedLeftLeg', None, (-1.9, 12, 0)), ('armorLeftLeg', 'bipedLeftLeg', (-1.9, 12, 0)),
        ('armorLeftBoot', 'bipedLeftLeg', (-1.9, 12, 0)))


def skeleton(name, tex_w=128):
    m = Model(name, density=DENS, tex_w=tex_w)
    for n, p, pv in SKEL:
        m.bone(n, p, pv)
    return m


def X(side, a, b):
    """Отрезок по x для стороны side (+1 — правая, −1 — левая): a, b — расстояния от оси тела наружу."""
    return min(side * a, side * b), max(side * a, side * b)


def sbox(m, bone, side, xa, xb, y0, y1, z0, z1, mat, **kw):
    x0, x1 = X(side, xa, xb)
    return m.box(bone, (x0, y0, z0), (x1, y1, z1), mat, **kw)


# ================================================================== палитры Эреба (как на его скине и модели T30) и маски
def ramp(*hs):
    return M.ramp(*hs)


E_BLACK = ramp('#07060a', '#0b0a0f', '#14121a', '#1d1a24', '#29252f', '#38333f')
E_GOLD = ramp('#4a2c0a', '#704612', '#a46a1c', '#d0952a', '#eab33c', '#f8d260', '#fff2b0')
E_GLASS = ramp('#12303f', '#1f4a63', '#3d8fb5', '#8fd8f2', '#e2fbff')
E_GREY = ramp('#101112', '#17181a', '#212325', '#2c2f31', '#3a3e40')
E_LEATHER = ramp('#060507', '#0e0c10', '#18151b', '#231f27', '#302a35')
MASK = ramp('#5a4c38', '#8f8068', '#bfb294', '#ddd2b6', '#efe8d4', '#fdfaf0')       # бледное белое золото («фарфор»), как у Длани
MASK_RIM = ramp('#3a2408', '#704612', '#a46a1c', '#d0952a', '#eab33c')


# ================================================================== материалы Эреба
def mat_coat(ctx):
    """Чёрное сукно камзола: складки, ручные пятна, золотая кайма по краям (trim), узоры (deco)."""
    i, j, pw, ph = _pix2(ctx)
    lv = bevel(ctx, base=info(ctx, 'base', 2), left=0, right=0)
    if ctx.face in SIDE and info(ctx, 'folds', True):
        lv = lv + np.where(i % 4 == 3, -1, 0)
    lv = lv + handf(ctx, 0.3, 0.8, 61, 0.012) * (ctx.face != 'down')
    rgb = tone(E_BLACK, lv)
    trim = info(ctx, 'trim')
    if trim:
        tw = info(ctx, 'trim_w', 1)
        g = np.zeros(ctx.n, bool)
        faces = info(ctx, 'trim_faces', SIDE)
        if ctx.face in faces:
            if 'b' in trim:
                g |= j >= ph - tw
            if 't' in trim:
                g |= j < tw
            if 'l' in trim:
                g |= i < tw
            if 'r' in trim:
                g |= i >= pw - tw
        if 'u' in trim and ctx.face == 'up':
            g |= (i == 0) | (j == 0) | (i == pw - 1) | (j == ph - 1)
        if g.any():
            rgb = np.where(g[:, None], tone(E_GOLD, np.where(j == ph - 1, 3, 5) - (ctx.face == 'down') * 2), rgb)
    deco = info(ctx, 'deco')
    if deco and ctx.face == info(ctx, 'deco_face', 'north'):
        rgb = EDECO[deco](ctx, i, j, pw, ph, rgb, lv)
    return rgb, 1.0, None


def mat_egold(ctx):
    i, j, pw, ph = _pix2(ctx)
    lv = bevel(ctx, base=info(ctx, 'base', 4))
    lv = lv + handf(ctx, 0.5, 0.6, 71, 0.008)
    rgb = tone(E_GOLD, lv)
    deco = info(ctx, 'deco')
    if deco and ctx.face == info(ctx, 'deco_face', 'north'):
        rgb = EDECO[deco](ctx, i, j, pw, ph, rgb, lv)
    return rgb, 1.0, None


def mat_glass(ctx):
    """Стекло (брошь, пряжки, камень венца): голубое, светлый блик в верхнем углу, светится в темноте (glowmask)."""
    i, j, pw, ph = _pix(ctx)
    lv = np.full(ctx.n, 2.0) + np.where(j < ph / 2, 1, 0) - np.where((i == pw - 1) | (j == ph - 1), 1, 0)
    lv = lv + np.where((i == 1) & (j == 1), 2, 0)
    rgb = tone(E_GLASS, lv)
    return rgb, 1.0, rgb * 0.75


def mat_trousers(ctx):
    i, j, pw, ph = _pix2(ctx)
    lv = bevel(ctx, base=2, left=0, right=0)
    lv = lv + handf(ctx, 0.35, 0.7, 81, 0.01)
    rgb = tone(E_GREY, lv)
    if info(ctx, 'stripe') and ctx.face in ('east', 'west'):          # золотой лампас по наружному шву
        side_face = 'east' if info(ctx, 'stripe') > 0 else 'west'
        if ctx.face == side_face:
            c = (pw - 1) / 2
            rgb = np.where((np.abs(i - c) < 0.6)[:, None], tone(E_GOLD, np.full(ctx.n, 4.0)), rgb)
    return rgb, 1.0, None


def mat_eboot(ctx):
    i, j, pw, ph = _pix2(ctx)
    lv = bevel(ctx, base=2) + handf(ctx, 0.5, 0.6, 91, 0.02)
    lv = lv + np.where((ctx.face == 'north') & (np.abs(i - (pw - 1) / 2) < 1) & (j < ph - 1), 1, 0)   # блик на носке/голенище
    return tone(E_LEATHER, lv + 1), 1.0, None


# ---------------------------------------------------------------- узоры камзола
def edeco_chest(ctx, i, j, pw, ph, rgb, lv):
    """Перед камзола: золотая планка по центру, золотые «бранденбуры» (поперечные застёжки) в 4 ряда, нагрудный узор-полумесяц."""
    c = (pw - 1) / 2
    d = np.abs(i - c)
    out_ = rgb
    placket = (d < 1.0)
    out_ = np.where(placket[:, None], tone(E_GOLD, np.where(j % 3 == 0, 5, 3)), out_)
    for r in (6, 9, 12, 15):
        bar = (j == r) & (d >= 1) & (d <= 4.6 - (r - 6) * 0.25)
        out_ = np.where(bar[:, None], tone(E_GOLD, np.full(len(i), 5.0)), out_)
        under = (j == r + 1) & (d >= 1) & (d <= 4.6 - (r - 6) * 0.25)
        out_ = np.where(under[:, None], tone(E_GOLD, np.full(len(i), 2.0)), out_)
        knot = (j == r) & (np.abs(d - (5.6 - (r - 6) * 0.25)) < 0.6)
        out_ = np.where(knot[:, None], tone(E_GOLD, np.full(len(i), 6.0)), out_)
    return out_


def edeco_back(ctx, i, j, pw, ph, rgb, lv):
    """Спина: золотой полумесяц под воротником (как на T30), золотая полоса пояса."""
    c = (pw - 1) / 2
    d = np.abs(i - c)
    arc = (j >= 3) & (j <= 6) & (np.abs(d - (5.5 - (j - 3) * 0.9)) < 0.9) & (d < 7)
    bowl = (j == 7) & (d < 2.6)
    return np.where((arc | bowl)[:, None], tone(E_GOLD, np.where(j <= 4, 5, 3)), rgb)


def edeco_cross(ctx, i, j, pw, ph, rgb, lv):
    """Золотой «крест» на рукаве (как на скине Эреба): вертикаль и перекладина, с тенью."""
    c = (pw - 1) / 2
    v = (np.abs(i - c) < 0.6) & (j >= 2) & (j <= 9)
    h = (j == 4) & (np.abs(i - c) <= 2.6)
    out_ = np.where((v | h)[:, None], tone(E_GOLD, np.full(len(i), 5.0)), rgb)
    sh = ((np.abs(i - c - 1) < 0.6) & (j >= 3) & (j <= 9) & ~v) | ((j == 5) & (np.abs(i - c) <= 2.6) & ~v)
    return np.where(sh[:, None], tone(E_GOLD, np.full(len(i), 1.0)), out_)


def edeco_tail(ctx, i, j, pw, ph, rgb, lv):
    """Пола камзола: золотая кайма по низу (двойная) и по краю разреза."""
    edge = info(ctx, 'edge', 'l')
    g = (j >= ph - 2) | ((i <= 0) if edge == 'l' else (i >= pw - 1))
    g2 = (j == ph - 4)
    out_ = np.where(g[:, None], tone(E_GOLD, np.where(j == ph - 1, 3, 5)), rgb)
    return np.where((g2 & ~g)[:, None], tone(E_GOLD, np.full(len(i), 3.0)), out_)


EDECO = {'chest': edeco_chest, 'back': edeco_back, 'cross': edeco_cross, 'tail': edeco_tail}


# ================================================================== маска: фарфоровое золото, трещины, прорезь глаза
EYE = (0.85, 3.15, 26.75, 28.6)          # прорезь у правого глаза игрока (столбцы 1–2 лица, ряд 4): x, y в мире
CRACKS = [[(2.2, 30.4), (2.5, 29.6), (2.1, 28.9)], [(3.4, 26.6), (3.9, 25.9), (3.6, 25.2), (4.1, 24.6)],
          [(0.4, 25.6), (1.1, 25.3), (1.6, 24.7)], [(4.6, 29.9), (3.9, 29.4), (3.7, 28.7)]]


def _seg_dist(px, py, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-9), 0, 1)
    return np.hypot(px - (ax + t * dx), py - (ay + t * dy))


def mat_mask(ctx):
    """Маска на пол-лица: выпуклая (светлее у скулы и лба), тёмно-золотая кайма по контуру, прорезь глаза (прозрачно),
    золотая слеза под прорезью, трещины с золотым швом (кинцуги) — они тлеют в темноте (glowmask)."""
    i, j, pw, ph = _pix(ctx)
    off = info(ctx, 'off', (0.0, 0.0, 1.0))          # сдвиг маски от лица: (dx, dy, масштаб) — у наголовной версии
    x = (ctx.L[:, 0] - off[0]) / off[2]
    y = (ctx.L[:, 1] - 24 - off[1]) / off[2] + 24
    a = np.ones(ctx.n)
    glow = np.zeros((ctx.n, 3))
    if ctx.face == 'north':
        k = 3.4 - (30.5 - y) / 5.5 * 1.6 - np.abs(x - 2.6) / 4.7 * 1.8
        lv = np.round(k)
        rgb = tone(MASK, lv)
        rim = (i == 0) | (i == pw - 1) | (j == 0) | (j == ph - 1)
        rgb = np.where(rim[:, None], tone(MASK_RIM, np.where(j == 0, 3, 1)), rgb)
        ex0, ex1, ey0, ey1 = EYE
        hole = (x > ex0) & (x < ex1) & (y > ey0) & (y < ey1)
        a = np.where(hole, 0.0, 1.0)
        near = ~hole & (x > ex0 - 0.3) & (x < ex1 + 0.3) & (y > ey0 - 0.3) & (y < ey1 + 0.3)
        rgb = np.where((near & (y >= ey1))[:, None], MASK_RIM[0], rgb)                    # тень над прорезью
        rgb = np.where((near & (y < ey1))[:, None], MASK_RIM[2], rgb)                     # золотая кайма прорези
        tear = (np.abs(x - 1.9) < 0.3) & (y < ey0 - 0.15) & (y > ey0 - 1.35) | (np.abs(x - 1.9) < 0.55) & (y < ey0 - 0.85) & (y > ey0 - 1.6)
        rgb = np.where(tear[:, None], tone(E_GOLD, np.where(y > ey0 - 0.7, 5, 4)), rgb)
        glow = np.where(tear[:, None], E_GOLD[3] * 0.6, glow)
        cr = np.zeros(ctx.n, bool)
        for pts in CRACKS:
            for p0, p1 in zip(pts, pts[1:]):
                cr |= _seg_dist(x, y, p0, p1) < 0.16
        rgb = np.where(cr[:, None], tone(E_GOLD, np.full(ctx.n, 4.0)), rgb)
        glow = np.where(cr[:, None], E_GOLD[4] * 0.7, glow)
    elif ctx.face == 'south':
        rgb = tone(MASK_RIM, np.full(ctx.n, 1.0))                                         # изнанка — тёмное золото
        ex0, ex1, ey0, ey1 = EYE
        a = np.where((x > ex0) & (x < ex1) & (y > ey0) & (y < ey1), 0.0, 1.0)
    else:
        rgb = tone(MASK_RIM, np.full(ctx.n, 3.0) - (ctx.face == 'down'))
    return rgb, a, glow


def mat_mask_part(ctx):
    """Скол надбровья и щёчная пластина: то же фарфоровое золото, кайма темнее."""
    i, j, pw, ph = _pix(ctx)
    lv = np.full(ctx.n, 3.0) - (j > ph * 0.6) + (j == 0)
    rgb = tone(MASK, lv)
    rim = (i == 0) | (i == pw - 1) | (j == ph - 1)
    rgb = np.where(rim[:, None], tone(MASK_RIM, np.full(ctx.n, 2.0)), rgb)
    if ctx.face not in ('north', 'up', 'east', 'west'):
        rgb = tone(MASK_RIM, np.full(ctx.n, 1.0))
    glow = None
    if info(ctx, 'crack') and ctx.face == 'north':
        cr = (np.abs(i - (1 + j * 0.5)) < 0.6)
        rgb = np.where(cr[:, None], tone(E_GOLD, np.full(ctx.n, 4.0)), rgb)
        glow = np.where(cr[:, None], E_GOLD[4] * 0.7, np.zeros((ctx.n, 3)))
    return rgb, 1.0, glow


# ---------------------------------------------------------------- узоры Мартина по мировым точкам (рисунок цельный через стык половин)
def _q(v, step=0.5):
    return np.floor(v / step) * step + step / 2


def wdeco_tabard_half(ctx, i, j, pw, ph, rgb, lv):
    """Половина табарда: золотая кайма снаружи и по низу, герб Мартина (корона над мечом) — по центру, через стык половин."""
    x, y = np.abs(_q(ctx.x)), _q(ctx.y)
    out_ = rgb
    gold = (x > 2.45) | (y < 3.75)
    out_ = np.where(gold[:, None], tone(M.R_GOLD, np.where(y < 3.25, 2, 4)), out_)
    seam = x < 0.25
    blade = seam & (y > 4.5) & (y < 9.0)
    guard = (x < 1.25) & (y > 8.5) & (y < 9.0)
    grip = seam & (y >= 9.0) & (y < 9.6)
    crown = (y > 10.0) & (y < 11.5) & (x < 1.5) & ~((y > 11.0) & (np.abs(x - 0.75) < 0.3))
    em = blade | guard | grip | crown
    out_ = np.where(em[:, None], tone(M.R_GOLD, np.where(guard | (y > 11.0), 5, 4)), out_)
    return out_


M.DECO['tabard_half'] = wdeco_tabard_half


def mat_wcape(ctx):
    """Плащ Мартина (чёрный, белая кайма) + на спине — красный щит с гербом, как щит у него на спине."""
    rgb, a, g = M.mat_cape(ctx)
    if ctx.face == 'south' and info(ctx, 'emblem'):
        x, y = np.abs(_q(ctx.x)), _q(ctx.y)
        top, bot = 21.5, 13.0
        w = np.where(y > 16.0, 2.75, 2.75 - (16.0 - y) * 0.9)
        shield = (y < top) & (y > bot) & (x < w)
        rim = shield & ((x > w - 0.5) | (y > top - 0.5))
        out_ = np.where(shield[:, None], tone(M.R_RED, np.full(ctx.n, 3.0) - (y < 15)), rgb)
        out_ = np.where(rim[:, None], tone(M.R_GOLD, np.full(ctx.n, 4.0)), out_)
        blade = (x < 0.25) & (y > 14.5) & (y < 18.5)
        guard = (x < 1.25) & (y > 18.0) & (y < 18.5)
        crown = (y > 19.0) & (y < 20.5) & (x < 1.5) & ~((y > 20.0) & (np.abs(x - 0.75) < 0.3))
        em = shield & ~rim & (blade | guard | crown)
        rgb = np.where(em[:, None], tone(M.R_GOLD, np.full(ctx.n, 5.0)), out_)
    return rgb, a, g


def add_mats(m):
    M.add_mats(m)
    m.materials['wcape'] = mat_wcape
    m.materials.update(coat=mat_coat, egold=mat_egold, glass=mat_glass, trousers=mat_trousers, eboot=mat_eboot, mask=mat_mask,
                       mask_part=mat_mask_part)


# ================================================================== «Доспех Полководца» (Мартин)
def build_warlord():
    m = skeleton('warlord')
    add_mats(m)
    H, B = 'armorHead', 'armorBody'
    # ---------------------------------------------------------------- шлем-корона (лицо — в пределах z ≥ −5.2: поверх ляжет Маска Лжи)
    m.box(H, (-4.6, 23.6, -4.6), (4.6, 31.4, 4.6), 'steel', base=3, fili=True)
    m.box(H, (-3.4, 24.4, -4.95), (3.4, 29.0, -4.6), 'gold', base=4)                       # золотое забрало
    m.box(H, (-3.0, 27.8, -5.05), (-0.8, 28.7, -4.9), 'eye')                                # глазные щели (холодный блеск)
    m.box(H, (0.8, 27.8, -5.05), (3.0, 28.7, -4.9), 'eye')
    m.box(H, (-4.8, 28.7, -5.2), (4.8, 30.0, -4.4), 'steel', base=4, trim='b')             # надбровье
    m.box(H, (-0.6, 24.8, -5.2), (0.6, 29.8, -4.9), 'steel', base=4)                        # наносник
    for s in (1, -1):                                                                        # нащёчники
        sbox(m, H, s, 3.9, 4.95, 23.6, 28.7, -4.85, 1.8, 'steel', base=3, trim='b')
    m.box(H, (-4.4, 22.6, 3.9), (4.4, 26.2, 5.0), 'steel', lames=4)                          # назатыльник
    m.box(H, (-4.95, 30.6, -4.95), (4.95, 31.8, 4.95), 'steel', base=4, trim='b')           # обруч короны (золотая кромка)
    m.box(H, (-3.6, 31.4, -3.6), (3.6, 32.8, 3.6), 'steel', base=4)                          # купол
    for x, h in ((-2.6, 1.6), (0.0, 2.6), (2.6, 1.6)):                                       # зубцы короны
        m.box(H, (x - 0.5, 31.8, -4.95), (x + 0.5, 31.8 + h, -4.15), 'steel', base=4)
    m.box(H, (-0.4, 32.0, -5.1), (0.4, 33.6, -4.8), 'gold', base=5)                          # золотой зубец-самоцвет
    for s in (1, -1):                                                                        # рога-зубцы, как у Мартина
        m.rod(H, (s * 3.1, 31.4, 0.4), (s * 3.9, 36.8, 0.8), 1.9, 1.1, 'steel', base=4)
        m.rod(H, (s * 3.9, 36.6, 0.8), (s * 4.0, 38.8, 1.1), 1.3, 0.9, 'steel', base=5)
        m.rod(H, (s * 3.5, 34.4, 0.9), (s * 2.3, 35.8, 0.9), 0.9, 0.9, 'steel', base=4)
        m.rod(H, (s * 3.9, 33.2, 0.8), (s * 5.1, 34.6, 0.8), 0.8, 0.8, 'steel', base=2)
    # плюмаж: красный гребень конского волоса по куполу (спереди назад, между рогами) и хвост, спадающий на затылок; две кости
    m.box(H, (-0.55, 32.6, -3.2), (0.55, 34.2, -2.5), 'gold', base=4)                            # золотая втулка гребня
    m.bone('plume', H, (0, 33.4, 0))
    m.box('plume', (-0.75, 32.8, -2.5), (0.75, 35.0, 6.1), 'red', base=4, folds=True)
    m.bone('plume_tip', 'plume', (0, 34.6, 5.4))
    m.box('plume_tip', (-0.85, 27.4, 4.7), (0.85, 35.0, 6.1), 'red', base=3, folds=True)
    # ---------------------------------------------------------------- корпус: поддоспешник, кираса, золотой горжет, пояс
    m.box(B, (-4.5, 12.0, -2.55), (4.5, 24.3, 2.55), 'red', base=2)
    m.box(B, (-3.9, 16.4, -3.1), (3.9, 24.2, 2.9), 'steel', deco='chest', base=3, fili=True)
    m.box(B, (-0.55, 16.2, -3.5), (0.55, 23.4, -3.0), 'steel', base=4)                       # рёберный кант
    m.box(B, (-3.3, 13.4, -2.95), (3.3, 16.6, 2.75), 'steel', lames=4, base=3)               # плакарт
    m.box(B, (-4.1, 16.8, 2.4), (4.1, 23.6, 3.05), 'steel', base=3, fili=True)               # спинная пластина
    m.box(B, (-3.0, 23.2, -3.3), (3.0, 24.8, 2.7), 'gold', engr=True)                        # горжет
    for s in (-1, 1):
        m.rod(B, (s * 2.6, 23.6, -3.2), (s * 0.5, 20.4, -3.25), 0.9, 0.5, 'gold', ext=0.2, base=4)
    m.box(B, (-4.7, 12.0, -2.9), (4.7, 13.5, 2.9), 'leather', deco='belt', stitch=True)
    m.box(B, (-0.9, 11.8, -3.25), (0.9, 13.7, -2.85), 'gold', base=4)                        # пряжка
    # плащ: воротник-валик на плечах, верх (до пояса) и низ (до икр) — две кости; шире ±3.9 нельзя: туда уходят руки на шаге
    m.box(B, (-3.9, 22.2, 1.9), (3.9, 24.6, 4.2), 'cape', outer='south', edge_l=False, edge_r=False)
    m.bone('cape', B, (0, 23.4, 3.6))
    m.box('cape', (-3.9, 12.2, 3.2), (3.9, 23.4, 3.95), 'wcape', outer='south', emblem=True)
    m.bone('cape_low', 'cape', (0, 12.2, 3.55))
    m.box('cape_low', (-4.6, 2.0, 3.2), (4.6, 12.2, 3.95), 'cape', outer='south', edge_b=True)
    # ---------------------------------------------------------------- руки: наплечник-веер с шипами, налокотник, наруч, золотая манжета
    for s, sn in ((1, 'Right'), (-1, 'Left')):
        R = 'armor' + sn + 'Arm'
        sbox(m, R, s, 4.0, 8.5, 12.4, 22.4, -2.45, 2.45, 'red', base=2)
        sbox(m, R, s, 4.0, 8.65, 16.6, 20.6, -2.65, 2.65, 'steel', base=3, fili=True)            # ребрасс
        sbox(m, R, s, 4.0, 9.5, 20.8, 24.8, -3.1, 3.1, 'steel', trim='b', base=4, fili=True)     # наплечник: три ламы
        sbox(m, R, s, 5.2, 9.9, 19.3, 21.2, -2.9, 2.9, 'steel', trim='b')
        sbox(m, R, s, 6.2, 10.0, 18.0, 19.6, -2.6, 2.6, 'steel', trim='b', base=2)
        for p, q, w in (((5.6, 24.6, -1.4), (6.8, 28.4, -1.8), 1.0), ((7.2, 24.4, 0.6), (9.0, 27.4, 1.0), 0.9),
                        ((8.6, 23.0, -0.6), (11.0, 24.8, -0.8), 0.8)):                          # шипы
            m.rod(R, (s * p[0], p[1], p[2]), (s * q[0], q[1], q[2]), w, w, 'steel', base=4)
        sbox(m, R, s, 3.9, 8.75, 15.4, 17.2, -2.8, 2.5, 'steel', base=4)                          # налокотник
        sbox(m, R, s, 8.75, 9.3, 14.8, 17.6, -1.4, 1.2, 'steel', base=3)                          # веер налокотника
        sbox(m, R, s, 4.0, 8.65, 13.2, 15.4, -2.65, 2.65, 'steel', base=3, fili=True)             # наруч
        sbox(m, R, s, 3.85, 8.8, 11.6, 13.4, -2.8, 2.8, 'gold', engr=True)                       # золотая манжета (перчатка под ней)
    # ---------------------------------------------------------------- поножи (LEGS): набедренник, тассет, наколенник
    for s, sn in ((1, 'Right'), (-1, 'Left')):
        L = 'armor' + sn + 'Leg'
        sbox(m, L, s, -0.3, 4.25, 6.4, 12.0, -2.45, 2.45, 'red', base=2)
        sbox(m, L, s, -0.35, 4.35, 7.0, 10.4, -2.6, 2.55, 'steel', base=3, trim='b', fili=True)   # набедренник
        sbox(m, L, s, 0.0, 4.5, 9.8, 12.4, -2.9, 2.85, 'steel', base=3, trim='b', lames=4)         # тассет (фалды) — ходит с ногой
        sbox(m, L, s, 0.3, 3.6, 5.2, 7.6, -2.95, -2.45, 'steel', base=4, trim='b')                  # наколенник (под табардом)
        sbox(m, L, s, 1.4, 2.5, 5.7, 7.1, -3.0, -2.9, 'steel', base=5)
        # табард: половина на каждой ноге (кость ходит с ногой — сквозь бедро не проходит), полы сходятся по центру
        tb = 'tabard_' + sn[0].lower()
        z = -3.05 if s > 0 else -3.1
        m.bone(tb, L, (s * 1.2, 12.4, z))
        sbox(m, tb, s, -0.15, 2.7, 3.0, 12.4, z - 0.4, z, 'red', deco='tabard_half', folds=False, base=3)
    # ---------------------------------------------------------------- сабатоны и поножи голени (FEET)
    for s, sn in ((1, 'Right'), (-1, 'Left')):
        F = 'armor' + sn + 'Boot'
        sbox(m, F, s, -0.4, 4.3, 1.4, 6.6, -2.6, 2.55, 'steel', lames=0, base=3, fili=True)
        sbox(m, F, s, 1.5, 2.3, 1.6, 6.0, -2.85, -2.6, 'steel', base=4)                               # ребро поножей
        sbox(m, F, s, -0.5, 4.4, 0.0, 1.8, -3.6, 2.7, 'steel', lames=0, base=3, trim='t')           # сабатон
        sbox(m, F, s, 0.3, 3.6, 0.0, 1.2, -4.4, -3.6, 'steel', base=4)
    return m


# ================================================================== «Камзол Предателя» (Эреб)
def build_traitor():
    m = skeleton('traitor')
    add_mats(m)
    H, B = 'armorHead', 'armorBody'
    # ---------------------------------------------------------------- венец: тонкий золотой обруч, пик со стеклом, два зубца
    m.box(H, (-4.75, 30.4, -4.75), (4.75, 31.25, 4.75), 'egold', base=4, hide=('up', 'down'))
    m.box(H, (-0.8, 30.6, -5.1), (0.8, 32.9, -4.7), 'egold', base=5)
    m.box(H, (-0.45, 31.15, -5.25), (0.45, 32.2, -5.05), 'glass')
    for s in (1, -1):
        sbox(m, H, s, 2.2, 2.9, 31.0, 32.1, -5.0, -4.7, 'egold', base=5)
        sbox(m, H, s, 4.55, 5.0, 30.0, 31.9, -1.2, 1.2, 'egold', base=3)                         # виски: золотые «крылышки»
        sbox(m, H, s, 4.65, 5.05, 30.6, 31.5, -0.45, 0.45, 'glass')
    # ---------------------------------------------------------------- камзол
    m.box(B, (-4.5, 12.2, -2.55), (4.5, 24.3, 2.55), 'coat', deco='chest', base=2)
    m.box(B, (-4.5, 12.2, 2.55), (4.5, 24.3, 2.6), 'coat', deco='back', deco_face='south', hide=('north', 'east', 'west', 'up', 'down'))
    m.box(B, (-4.75, 23.0, -2.8), (4.75, 24.6, 2.8), 'coat', trim='b', base=3)                  # мантия плеч (кайма)
    m.bone('collar_back', B, (0, 23.8, 2.55), (24, 0, 0))                                       # воротник-стойка: отклонён назад
    m.box('collar_back', (-4.75, 23.8, 2.2), (4.75, 26.6, 2.9), 'coat', trim='tlr', trim_faces=('south', 'north', 'east', 'west'), base=3)
    for s in (1, -1):
        x0, x1 = X(s, 4.0, 4.75)
        m.box(B, (x0, 23.8, -2.4), (x1, 26.0, 2.4), 'coat', rot=(0, 0, s * 22), pivot=(s * 4.4, 23.8, 0), trim='t', base=3)
    m.box(B, (-1.0, 19.8, -2.95), (1.0, 23.2, -2.55), 'egold', base=4)                          # жабо-пластина
    m.box(B, (-0.75, 20.6, -3.3), (0.75, 22.1, -2.9), 'glass')                                   # брошь — стекло
    # аксельбант: золотой шнур от правого плеча к броши (как у Эреба)
    for p, q in (((4.5, 23.6, -2.85), (1.0, 20.2, -2.95)), ((4.3, 22.9, -2.9), (2.2, 18.6, -2.95)), ((2.2, 18.6, -2.95), (0.9, 20.6, -3.0))):
        m.rod(B, p, q, 0.45, 0.35, 'egold', base=5)
    m.box(B, (-4.65, 12.2, -2.75), (4.65, 13.7, 2.75), 'coat', trim='tb', base=1)               # пояс
    m.box(B, (-1.3, 12.0, -3.05), (1.3, 14.0, -2.7), 'egold', base=4)                            # пряжка
    m.box(B, (-0.6, 12.5, -3.25), (0.6, 13.5, -3.0), 'glass')
    # ---------------------------------------------------------------- рукава: эполет с бахромой и стеклянной пряжкой, крест, манжета
    for s, sn in ((1, 'Right'), (-1, 'Left')):
        R = 'armor' + sn + 'Arm'
        outer = 'east' if s > 0 else 'west'
        sbox(m, R, s, 4.0, 8.5, 12.6, 22.6, -2.5, 2.5, 'coat', deco='cross', deco_face=outer, base=2)
        sbox(m, R, s, 3.9, 9.0, 22.4, 24.4, -2.8, 2.8, 'coat', trim='btu', base=3)                 # эполет
        sbox(m, R, s, 9.0, 9.45, 21.6, 24.2, -1.25, 1.25, 'egold', base=4)                          # пряжка эполета
        sbox(m, R, s, 9.1, 9.55, 22.4, 23.4, -0.5, 0.5, 'glass')
        for k in range(5):                                                                          # золотая бахрома
            sbox(m, R, s, 8.7, 9.2, 20.6 + (0.3 if k % 2 else 0), 22.4, -2.3 + k * 1.05, -1.8 + k * 1.05, 'egold', base=5)
        sbox(m, R, s, 3.85, 8.7, 12.0, 14.8, -2.75, 2.75, 'coat', trim='tb', base=3)               # манжета
        sbox(m, R, s, 8.7, 8.95, 12.6, 13.6, -0.5, 0.5, 'glass')                                    # стеклянная пуговица
    # ---------------------------------------------------------------- штаны (LEGS) и сапоги (FEET)
    for s, sn in ((1, 'Right'), (-1, 'Left')):
        L = 'armor' + sn + 'Leg'
        sbox(m, L, s, -0.15, 4.3, 5.0, 12.1, -2.45, 2.45, 'trousers', stripe=s)
        # полы камзола — на костях ног (как юбка безмолвной ведьмы): передняя с разрезом по центру, задняя со шлицей и боковиной
        fr, bk, sx = 'coat_front_' + sn[0].lower(), 'coat_back_' + sn[0].lower(), sn[0].lower()
        z = -3.0 if s > 0 else -3.05
        m.bone(fr, L, (s * 2.3, 12.4, z + 0.2))
        sbox(m, fr, s, -0.15, 4.75, 2.0, 12.4, z - 0.4, z, 'coat', deco='tail', edge='l' if s > 0 else 'r', base=2)
        z = 3.0 if s > 0 else 3.05
        m.bone(bk, L, (s * 2.3, 12.4, z - 0.2))
        sbox(m, bk, s, -0.15, 4.75, 1.6, 12.4, z, z + 0.4, 'coat', deco='tail', deco_face='south', edge='r' if s > 0 else 'l', base=2)
        sbox(m, bk, s, 4.75, 5.15, 1.8, 12.4, -2.7, z + 0.4, 'coat', trim='b', base=2)              # боковина: закрывает бедро сбоку
        F = 'armor' + sn + 'Boot'
        sbox(m, F, s, -0.35, 4.4, 0.0, 6.0, -2.6, 2.6, 'eboot')
        sbox(m, F, s, -0.45, 4.5, 5.2, 6.6, -2.7, 2.7, 'egold', base=3, hide=('up', 'down'))      # золотой отворот голенища
        sbox(m, F, s, -0.4, 4.45, 0.0, 0.6, -3.3, 2.7, 'eboot')                                     # подошва-носок
        sbox(m, F, s, 1.5, 2.5, 3.0, 4.0, -2.8, -2.6, 'egold', base=5)                              # пряжка
    return m


# ================================================================== «Маска Лжи» (Длань Лжи)
OVER = (0.0, 0.0, 1.12)        # наголовная версия — та же маска ×1.12 (лицо у шлемов шире)


def build_mask():
    m = skeleton('mask_of_lies', tex_w=64)
    add_mats(m)

    def mask(bone, z_back, sc, cheek_x):
        f = lambda v: v * sc                      # x от оси лица
        y = lambda v: 24 + (v - 24) * sc
        off = (0.0, 0.0, sc)
        m.box(bone, (f(-0.25), y(25.0), z_back - 0.5), (f(4.45), y(30.5), z_back), 'mask', off=off)
        m.box(bone, (f(3.35), y(29.6), z_back - 0.55), (f(4.95), y(31.35), z_back - 0.05), 'mask_part', crack=True,
              rot=(0, 0, 28), pivot=(f(4.15), y(29.6), z_back - 0.3))                                # надбровный скол — вверх к виску
        m.box(bone, (cheek_x, y(25.25), z_back - 0.45), (cheek_x + 0.6, y(29.0), z_back + 1.4), 'mask_part',
              rot=(0, -14, 0), pivot=(cheek_x + 0.3, y(27.0), z_back + 0.5))                         # щёчная пластина заходит на висок

    m.bone('mask_face', 'armorHead', (2.0, 28.0, -4.85))
    mask('mask_face', -4.6, 1.0, 4.45)
    m.bone('mask', 'armorHead', (2.2, 28.0, -5.6))
    mask('mask', -5.32, OVER[2], 5.1)
    return m


# ================================================================== анимации ткани (цикл; к ним код прибавляет следование за ногами)
def wave(t, L, a, ph=0.0):
    return a * math.sin(2 * math.pi * (t / L + ph))


def pos_wave(t, L, a, ph=0.0):
    """Всегда ≥ 0: ткань качается только наружу от тела (вперёд — у передних пол, назад — у задних)."""
    return a * (0.5 + 0.5 * math.sin(2 * math.pi * (t / L + ph)))


def anims_warlord():
    res = {}
    for name, L, cape0, capeA, low0, lowA, tab0, tabA, pl0, plA in (
            ('idle', 4.0, -2, 1.5, -1, 1.0, 2, 1.0, -2, 2),
            ('walk', 1.0, -7, 4, -4, 4, 3, 2.5, -12, 6),
            ('run', 0.6, -20, 6, -10, 7, 6, 5, -30, 9),
            ('cast', 1.0, -10, 5, -6, 6, 5, 4, -16, 8)):
        a = Anim(name, L)

        def fn(t, cape0=cape0, capeA=capeA, low0=low0, lowA=lowA, tab0=tab0, tabA=tabA, pl0=pl0, plA=plA, L=L):
            return {'cape': {'rot': [cape0 - pos_wave(t, L, capeA), wave(t, L, 1.2, 0.3), 0]},
                    'cape_low': {'rot': [low0 - pos_wave(t, L, lowA, 0.2), 0, wave(t, L, 1.5, 0.45)]},
                    'tabard_r': {'rot': [tab0 + pos_wave(t, L, tabA, 0.15), 0, 0.8 + 0.8 * pos_wave(t, L, 1.0, 0.4)]},
                    'tabard_l': {'rot': [tab0 + pos_wave(t, L, tabA, 0.65), 0, -0.8 - 0.8 * pos_wave(t, L, 1.0, 0.9)]},
                    'plume': {'rot': [0, 0, wave(t, L, 1.0, 0.25)]},
                    'plume_tip': {'rot': [pl0 - pos_wave(t, L, plA, 0.3), 0, wave(t, L, 3, 0.5)]}}
        a.sample(fn, dt=L / 16)
        res[name] = a.to_json()
    return res


def anims_traitor():
    res = {}
    for name, L, f0, fA, b0, bA, c0 in (('idle', 4.0, 2, 1.0, -3, 1.5, 0), ('walk', 1.0, 3, 3, -6, 4, -1),
                                        ('run', 0.6, 6, 5, -18, 7, -3), ('cast', 1.0, 5, 4, -10, 6, -2)):
        a = Anim(name, L)

        def fn(t, f0=f0, fA=fA, b0=b0, bA=bA, c0=c0, L=L):
            return {'coat_front_r': {'rot': [f0 + pos_wave(t, L, fA), 0, 1.5 + pos_wave(t, L, 1.0, 0.2)]},
                    'coat_front_l': {'rot': [f0 + pos_wave(t, L, fA, 0.5), 0, -1.5 - pos_wave(t, L, 1.0, 0.7)]},
                    'coat_back_r': {'rot': [b0 - pos_wave(t, L, bA, 0.1), 0, 1.0 + pos_wave(t, L, 1.2, 0.35)]},
                    'coat_back_l': {'rot': [b0 - pos_wave(t, L, bA, 0.6), 0, -1.0 - pos_wave(t, L, 1.2, 0.85)]},
                    'collar_back': {'rot': [c0 - pos_wave(t, L, 1.0, 0.2), 0, 0]}}
        a.sample(fn, dt=L / 16)
        res[name] = a.to_json()
    return res


def anims_mask():
    a = Anim('idle', 4.0)
    a.sample(lambda t: {'mask': {'rot': [0, 0, 0]}, 'mask_face': {'rot': [0, 0, 0]}}, dt=2.0)
    return {'idle': a.to_json()}


# ================================================================== запись модели, текстур, анимаций
def write_model(m, anims):
    m.pack()
    m.paint()
    write_json('geo/armor/%s.geo.json' % m.name, m.geo_json(), compact=False)
    m.image.save(out('textures/armor/%s.png' % m.name))
    if m.glow is not None:
        m.glow.save(out('textures/armor/%s_glowmask.png' % m.name))
    write_json('animations/armor/%s.animation.json' % m.name, {'format_version': '1.8.0', 'animations': anims})
    print(m.name, 'atlas', m.tex_px, 'cubes', sum(len(b.cubes) for b in m.bones.values()))


# ================================================================== иконки 16×16 (ручной пиксель-арт: левая половина, зеркалится)
ICON_PAL = {
    'S': M.R_STEEL, 'G': M.R_GOLD, 'R': M.R_RED, 'K': M.R_BLACK, 'W': M.R_WHITE, 'L': M.R_LEATHER,
    'C': E_BLACK, 'Y': E_GOLD, 'B': E_GLASS, 'D': E_GREY, 'E': E_LEATHER, 'M': MASK, 'N': MASK_RIM,
}
# строки: символ материала + цифра тона; '..' — прозрачно. Ширина 8 ячеек (16 символов) — левая половина, правая — зеркало.
ICONS = {
    'warlord_helmet': [
        '........S3......', '....S4..S4......', '....S4..S3..S4..', '....S4S3S2..S5..', '..S2S4S5S5S5S5S5',
        '..S3S5S4S4S4S4S4', '..S3S4S3S3S3S3S3', '..S3S2G4G4G4G4G5', '..S3S2G3E0E0E0S5', '..S3S2G3G3G3G3S5',
        '..S2S2G3G3G2G2S5', '..S2S2G2G2G2G2S4', '..S1S2S3S3S2G2S4', '....S1S2S2S2S2S3', '......S1S1S1S1S1', '................'],
    'warlord_chestplate': [
        '................', 'S4S5S5..G4G5G5G5', 'S3S4S5S4G3G4G5G4', 'S2S3S4S4S5G3G4S5', 'S2S3S4S3S4S5G4S6',
        '..R3S3S3S4S5S5S6', '..R2S2S3S4S4S5S6', '..R2S2S3S4S4S5S6', '..R2S2S3S3S4S4S5', '..R1L2L3L3L3G4G5',
        '....R3R3S3S3R3R4', '....R2R3G4R3R4R4', '....R2R3R3R3G5G5', '....R2G3R3R3R3G5', '....R1G3R2R2R3G5', '....G2G3G3G3G3G4'],
    'warlord_leggings': [
        '..S3S4S4S4S4S4S5', '..G3G3G4G4G4G4G4', '..S2S3S4S4S4S5S5', '..S2S3S4S4S4S4..', '..S2S3S4S4S4S4..',
        '..S2S3S4S4S5S4..', '..G2G3G4G4G4G3..', '..R2R2R3R3R3R2..', '..S2S3S4S5S5S3..', '..S2S4S5S6S5S3..',
        '..S2S3S4S5S4S3..', '..S2S3S3S4S3S2..', '..S1S2S3S3S3S2..', '..S1S2S2S3S2S2..', '..S1S1S2S2S1S1..', '................'],
    'warlord_boots': [
        '................', '................', '................', '..S3S4S5S4......', '..S2S3S5S4......',
        '..S2S3S5S4......', '..S2S3S5S4......', '..S2S3S5S4......', '..G3G4G4G4......', '..S2S3S4S4......',
        '..S2S3S4S4......', 'S3S3S4S4S5......', 'S2S3S4S4S5......', 'S2S2S3S3S4......', 'S1S1S2S2S2......', '................'],
    'traitor_helmet': [
        '................', '................', '................', '................', '..............Y5',
        '..........Y5..Y4', '..........Y4Y5B4', '..Y5Y5Y5..Y4B3B2', 'Y4B3Y4Y5Y5Y5Y5Y4', 'Y3Y4Y4Y3Y3Y3Y3Y3',
        '..Y2Y3Y2Y2Y2Y2Y2', '................', '................', '................', '................', '................'],
    'traitor_chestplate': [
        '................', '..C3C4..C4C4C3..', 'C3C4Y4Y5C4C4C5C3', 'C2C3Y5Y4C3C3C4Y4', 'Y4Y4Y5C3C3C3C4Y3',
        'C2Y4C3C3Y4Y5Y5Y5', 'C2Y5C3C3C3C3C3Y4', 'C2C4C3C3Y4Y5Y5Y5', '..C3C3C3C3C3C3Y4', '..C2C2C3Y4Y5Y5Y5',
        '..Y3Y4Y4Y4Y4Y4Y4', '..C2C2C3C3Y3B3B4', '..C2C2C3C3C3C3Y4', '..C2C2C3C3C3C3Y4', '..C1C2C2C2C2C3Y4', '..Y3Y4Y4Y4Y4Y5Y5'],
    'traitor_leggings': [
        '..D2D3D3D3D3D3D3', '..D2D3D3D3D3D3D3', '..Y4D3D3D3D3D3..', '..Y4D3D3D3D3D3..', '..Y4D2D3D3D3D3..',
        '..Y4D2D3D3D3D2..', '..Y4D2D3D3D3D2..', '..Y4D2D3D3D3D2..', '..Y4D2D3D3D3D2..', '..Y4D2D2D3D3D2..',
        '..Y4D2D2D3D3D2..', '..Y4D2D2D3D3D2..', '..Y3D1D2D2D2D1..', '..Y3D1D2D2D2D1..', '..D1D1D1D1D1D1..', '................'],
    'traitor_boots': [
        '................', '................', '..Y3Y4Y5Y5......', '..Y2Y3Y4Y4......', '..E2E3E4E3......',
        '..E2E3E4E3......', '..E2E3E4E3......', '..E2E3E4E3......', '..E2Y4Y5E3......', '..E2E3E4E3......',
        '..E2E3E4E3......', 'E2E3E3E4E4......', 'E2E2E3E4E4......', 'E1E2E2E3E3......', 'E0E1E1E1E1......', '................'],
}
MASK_ICON = [   # полная ширина 16 (не зеркалится): правая половина лица — слева на иконке, как на игроке спереди
    '................', '....N3N3........', '..N3M4M5N3N3N3..', '..N2M4M5M4M4M4N3', 'N2M3M4M5M4M4M4N2',
    'N2M3M4Y5M4M4M4N2', 'N2M3M4M3Y5M3M4N2', 'N2M3N2....N2M3N2', 'N2M2N1....N1M3N2', 'N2M2M3Y5M3M3M3N2',
    '..N2M2Y4M3M3M3N2', '..N2M2Y4M2M3N2..', '....N2M2M2M2N2..', '......N2N2N2....', '................', '................']


def paint_icon(rows, mirror=True):
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        cells = [r[k:k + 2] for k in range(0, len(r), 2)]
        if mirror:
            cells = cells + cells[::-1]
        for x, c in enumerate(cells):
            if c == '..':
                continue
            R = ICON_PAL[c[0]]
            col = R[min(int(c[1]), len(R) - 1)]
            im.putpixel((x, y), tuple(int(v * 255 + 0.5) for v in col) + (255,))
    # контур: прозрачный сосед → тёмный тон того же материала по краю (как у ванильных иконок брони)
    px = im.load()
    a = [[px[x, y][3] for x in range(16)] for y in range(16)]
    for y in range(16):
        for x in range(16):
            if not a[y][x]:
                continue
            edge = any(not (0 <= x + dx < 16 and 0 <= y + dy < 16) or not a[y + dy][x + dx] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge and (y > 0 and a[y - 1][x] == 0 or x > 0 and a[y][x - 1] == 0) is False:
                r, g, b, _ = px[x, y]
                px[x, y] = (int(r * 0.6), int(g * 0.6), int(b * 0.6), 255)
    return im


def write_icons():
    for name, rows in ICONS.items():
        paint_icon(rows).save(out('textures/item/%s.png' % name))
        write_json('models/item/%s.json' % name, {'parent': 'item/generated', 'textures': {'layer0': 'pohsmp_core:item/' + name}})
    paint_icon(MASK_ICON, mirror=False).save(out('textures/item/mask_of_lies.png'))
    write_json('models/item/mask_of_lies.json', {'parent': 'item/generated', 'textures': {'layer0': 'pohsmp_core:item/mask_of_lies'}})


# ================================================================== lang: только названия частей — под вид моделей (остальные ключи
# подсказок — у программиста: item.pohsmp_core.trophy.*, item.pohsmp_core.mask_of_lies.*). Табард — на поножах, полы камзола — на штанах.
NAMES = {
    'ru_ru': {'warlord_helmet': 'Шлем-корона Полководца', 'warlord_chestplate': 'Кираса Полководца',
              'warlord_leggings': 'Поножи с табардом Полководца', 'warlord_boots': 'Сабатоны Полководца',
              'traitor_helmet': 'Венец Предателя', 'traitor_chestplate': 'Камзол Предателя',
              'traitor_leggings': 'Полы камзола и штаны Предателя', 'traitor_boots': 'Сапоги Предателя', 'mask_of_lies': 'Маска Лжи'},
    'en_us': {'warlord_helmet': "Warlord's Crowned Helm", 'warlord_chestplate': "Warlord's Cuirass",
              'warlord_leggings': "Warlord's Tabard Greaves", 'warlord_boots': "Warlord's Sabatons",
              'traitor_helmet': "Traitor's Circlet", 'traitor_chestplate': "Traitor's Coat",
              'traitor_leggings': "Traitor's Coat Tails and Breeches", 'traitor_boots': "Traitor's Boots", 'mask_of_lies': 'Mask of Lies'},
}


def write_lang():
    """Меняет только значения существующих ключей названий (порядок и остальные ключи файла не трогает)."""
    for loc, kv in NAMES.items():
        p = os.path.join(A, 'lang', loc + '.json')
        d = json.load(open(p, encoding='utf-8'))
        for k, v in kv.items():
            d['item.pohsmp_core.' + k] = v
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(d, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
        WRITTEN.append('lang/' + loc + '.json')


MODELS = {'warlord': (build_warlord, anims_warlord), 'traitor': (build_traitor, anims_traitor), 'mask_of_lies': (build_mask, anims_mask)}


def main():
    for n, (b, an) in MODELS.items():
        write_model(b(), an())
    write_icons()
    if '--no-lang' not in sys.argv:
        write_lang()
    print('\n'.join(sorted(set(WRITTEN))))


if __name__ == '__main__':
    main()
