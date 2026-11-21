#!/usr/bin/env python3
"""
T29 «Мартин, Последний Полководец» (Глава 4 Ячейки Культа) — визуал босса. ТЗ: docs/specs/tasks/T29_martin_boss.md.
Референсы: docs/references/t29/martin_look.jpg (внешность), martin_sword.jpg (меч).

Каркас моделей — tools/nightmare_geo.py (как бестиарий T25). Модель строится в масштабе мага Iron's (abstract_casting_mob: кости body/torso/
head/right_arm/left_arm/right_leg/left_leg/bipedHand*/…Item с теми же шарнирами) и рисуется кодом ×2 (poseStack.scale(2)) — так все
анимации Iron's (casting_animations.json) играют без правок, а плотность текстуры 2 пикселя на единицу даёт в мире 1 тексель = 1/16 блока
(стандарт владельца 20.11: как у Главы Культа — стиль Iron's/ванили, ручная пиксельная светотень без шума).

Пишет (assets/pohsmp_core/):
  geo/entity/martin.geo.json, textures/entity/martin/martin.png (+ _glowmask), animations/entity/martin.animation.json
  models/item/martin_sword.json + textures/item/martin_sword_3d.png (3D-предмет меча; на боссе меч — кость `sword` той же формы)
  остальное — gen_martin_extra.py (солдаты, знамя, конница), gen_martin_fx.py (fx, полоса, титр, иконки, lang, звуки, кадры).
Запуск: python3 tools/gen_martin.py [--shots] [--html]      (нужен jar Iron's: python3 tools/fetch_libs.py)
"""
import json
import math
import os
import sys
import zipfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nightmare_geo import Model, Anim, euler, to_euler, fbm, vnoise, _hash, write_json as _wj, TAU  # noqa: E402

ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
JAR = os.path.join(ROOT, 'libs', 'irons_spellbooks-1.20.1-3.16.1.jar')
I = 'assets/irons_spellbooks/'
WRITTEN = []
GLOW_GOLD = 0.0          # солдаты: золотая кайма светится (glowmask)
DENS = 4                 # пикселей на единицу UV — ×4, как у эталона (cult_leader.png: атлас 128 → 512 px), ручная фактура


def out(rel):
    p = os.path.join(A, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    WRITTEN.append(rel)
    return p


def write_json(rel, obj, compact=False):
    _wj(out(rel), obj, compact=compact)


def jar_json(path):
    with zipfile.ZipFile(JAR) as z:
        return json.loads(z.read(path).decode('utf-8'))


def hx(h, a=255):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)


# ================================================================== палитры (рампы от тёмного к светлому) — как в референсе
def ramp(*hs):
    return np.array([[int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)] for h in hs])


R_STEEL = ramp('#3a3b40', '#5d5f66', '#82848b', '#a6a8ae', '#c4c6cb', '#dfe0e3', '#f7f7f8')
R_GOLD = ramp('#3e2410', '#6a4318', '#9a6a26', '#c8933a', '#e5b95a', '#f6d88a', '#fff1c4')
R_RED = ramp('#2a060c', '#4c0c14', '#74121c', '#9c1c24', '#c22a2c', '#e0463a')
R_BLACK = ramp('#08080b', '#121318', '#1c1e25', '#272a33', '#353943')
R_WHITE = ramp('#7c808a', '#a8acb5', '#cdd0d6', '#e9ebee', '#ffffff')
R_LEATHER = ramp('#1e120a', '#352014', '#4c2f1c', '#654027', '#7e5433')
R_GRIP = ramp('#0c0c10', '#17171d', '#22232b', '#30313b', '#444652')
R_DARK = ramp('#040405', '#0b0b0e', '#141419')
R_BLADE_DARK = ramp('#22160e', '#3a271a', '#523726', '#6a4a33')
R_EYE = ramp('#7fd8ff', '#c8f0ff', '#ffffff')


def _pix(ctx):
    x, y, pw, ph = ctx.cube.px[ctx.face]
    i = np.minimum((ctx.s * pw).astype(int), pw - 1)
    j = np.minimum((ctx.t * ph).astype(int), ph - 1)
    return i, j, pw, ph


def _pix2(ctx):
    """Сетка рисунка 2 пикселя на единицу (узоры, ламы, гербы — крупно), сама текстура — 4 пикселя на единицу."""
    i, j, pw, ph = _pix(ctx)
    return i // 2, j // 2, max(1, pw // 2), max(1, ph // 2)


def handf(ctx, f=0.35, amp=1.0, seed=0, dots=0.03):
    """Ручная фактура, как у эталона: крупные пятна-мазки в 2–3 тона (шум по точке тела, без швов между гранями) и редкие точки."""
    n = fbm(ctx.P, f, seed, 3)
    lv = np.clip(np.floor((n - 0.5) * 2.6 * amp + 0.5), -1, 1)
    if dots:
        i, j, pw, ph = _pix(ctx)
        h = _hash(i + ctx.cube.px[ctx.face][0], j + ctx.cube.px[ctx.face][1], np.zeros_like(i), seed + 7)
        lv = lv - (h < dots) + (h > 1 - dots * 0.6)
    return lv


SIDE = ('north', 'south', 'east', 'west')


def bevel(ctx, base=3, top=1, bottom=-1, left=0, right=-1, up=1, down=-2):
    """Уровень тона по грани: ручная пиксельная светотень — светлая кромка сверху, тёмная снизу/справа, верх светлее, низ темнее."""
    i, j, pw, ph = _pix(ctx)
    lv = np.full(ctx.n, float(base))
    if ctx.face in SIDE:
        if ph > 2:
            lv = lv + np.where(j == 0, top, 0) + np.where(j == ph - 1, bottom, 0)
        if pw > 2:
            lv = lv + np.where(i == 0, left, 0) + np.where(i == pw - 1, right, 0)
    elif ctx.face == 'up':
        lv = lv + up
        edge = (i == 0) | (j == 0) | (i == pw - 1) | (j == ph - 1)
        lv = lv + np.where(edge & (pw > 2) & (ph > 2), 1, 0)
    else:
        lv = lv + down
    return lv


def tone(R, lv):
    k = np.clip(np.round(lv).astype(int), 0, len(R) - 1)
    return R[k]


def info(ctx, k, d=None):
    return ctx.cube.info.get(k, d)


# ---------------------------------------------------------------- материалы Мартина
def mat_steel(ctx):
    i, j, pw, ph = _pix2(ctx)
    lv = bevel(ctx, base=info(ctx, 'base', 3))
    R = np.repeat(R_STEEL[None], ctx.n, 0)
    lames = info(ctx, 'lames')
    if lames and ctx.face in SIDE:                                   # пластины-ламы: тёмная бороздка, под ней светлая кромка
        jj = (j + info(ctx, 'lame_off', 0)) % lames
        lv = lv + np.where(jj == lames - 1, -2, 0) + np.where((jj == 0) & (j > 0), 1, 0)
    vl = info(ctx, 'vlames')
    if vl and ctx.face in SIDE:
        ii = i % vl
        lv = lv + np.where(ii == vl - 1, -1, 0)
    trim = info(ctx, 'trim')                                         # золотая кайма (по нижнему краю / по контуру)
    g = np.zeros(ctx.n, bool)
    if trim and ctx.face in SIDE:
        tw = info(ctx, 'trim_w', 1)
        if 'b' in trim:
            g |= j >= ph - tw
        if 't' in trim:
            g |= j < tw
        if 'l' in trim:
            g |= i < tw
        if 'r' in trim:
            g |= i >= pw - tw
    if trim and 'u' in trim and ctx.face == 'up':
        g |= (i == 0) | (j == 0) | (i == pw - 1) | (j == ph - 1)
    lv = lv + handf(ctx, 0.32, 0.7, 11, 0.004) * (ctx.face != 'down')
    rgb = tone(R_STEEL, lv)
    if g.any():
        lg = np.where(j == ph - 1, 2, 4) if ctx.face in SIDE else np.full(ctx.n, 4)
        rgb = np.where(g[:, None], tone(R_GOLD, lg - (ctx.face == 'down') * 2), rgb)
    deco = info(ctx, 'deco')
    if deco and ctx.face == info(ctx, 'deco_face', 'north'):
        rgb = DECO[deco](ctx, i, j, pw, ph, rgb, lv)
    if info(ctx, 'rivets') and ctx.face in SIDE and pw > 4 and ph > 3:   # заклёпки по углам
        rv = ((i == 1) | (i == pw - 2)) & ((j == 1) | (j == ph - 2))
        rgb = np.where(rv[:, None], R_GOLD[5], rgb)
    return rgb, 1.0, None


def mat_gold(ctx):
    i, j, pw, ph = _pix2(ctx)
    lv = bevel(ctx, base=info(ctx, 'base', 3))
    if info(ctx, 'engr') and ctx.face in SIDE and pw > 3 and ph > 3:  # гравировка: шахматный завиток
        lv = lv + np.where(((i + j) % 4 == 0) & (i > 0) & (j > 0) & (i < pw - 1) & (j < ph - 1), -1, 0)
    lv = lv + handf(ctx, 0.5, 0.6, 31, 0.008)
    rgb = tone(R_GOLD, lv)
    deco = info(ctx, 'deco')
    if deco and ctx.face == info(ctx, 'deco_face', 'north'):
        rgb = DECO[deco](ctx, i, j, pw, ph, rgb, lv)
    g = rgb * GLOW_GOLD if GLOW_GOLD else None
    return rgb, 1.0, g


def mat_red(ctx):
    i, j, pw, ph = _pix2(ctx)
    lv = bevel(ctx, base=info(ctx, 'base', 3), left=0, right=0)
    if ctx.face in SIDE and info(ctx, 'folds', True):                 # складки ткани: вертикальные тени через 3 пикселя
        lv = lv + np.where(i % 4 == 3, -1, 0)
    lv = lv + handf(ctx, 0.3, 1.0, 23, 0.02)
    rgb = tone(R_RED, lv)
    deco = info(ctx, 'deco')
    if deco and ctx.face == info(ctx, 'deco_face', 'north'):
        rgb = DECO[deco](ctx, i, j, pw, ph, rgb, lv)
    return rgb, 1.0, None


def mat_cape(ctx):
    """Чёрно-белый плащ: снаружи чёрный с белой каймой по краям и низу, изнутри — белая подкладка в тени."""
    i, j, pw, ph = _pix2(ctx)
    lv = bevel(ctx, base=2, left=0, right=0, top=0)
    out_face = info(ctx, 'outer', 'south')
    inner = {'south': 'north', 'north': 'south', 'east': 'west', 'west': 'east'}[out_face]
    if ctx.face == out_face:
        lv = lv + np.where(i % 5 == 4, -1, 0) + np.where(i % 5 == 0, 1, 0) * 0     # складки
        rgb = tone(R_BLACK, lv + handf(ctx, 0.25, 0.8, 41, 0.015))
        edge = np.zeros(ctx.n, bool)
        if info(ctx, 'edge_l', True):
            edge |= i <= 1
        if info(ctx, 'edge_r', True):
            edge |= i >= pw - 2
        if info(ctx, 'edge_b', False):
            edge |= j >= ph - 2
        rgb = np.where(edge[:, None], tone(R_WHITE, np.where((i == 1) | (i == pw - 2) | (j == ph - 2), 3, 2)), rgb)
    elif ctx.face == inner:
        rgb = tone(R_BLACK, 2 + np.where(i % 5 == 4, -1, 0))
        rgb = np.where(((i <= 0) | (i >= pw - 1) | (j >= ph - 1))[:, None], R_WHITE[2], rgb)
    elif ctx.face in SIDE:
        rgb = tone(R_WHITE, np.full(ctx.n, 3.0) - (j == ph - 1))
    elif ctx.face == 'down':
        rgb = tone(R_WHITE, np.full(ctx.n, 1.0))
    else:
        rgb = tone(R_BLACK, lv)
    return rgb, 1.0, None


def mat_leather(ctx):
    i, j, pw, ph = _pix2(ctx)
    lv = bevel(ctx, base=2)
    if ctx.face in SIDE and info(ctx, 'stitch'):
        lv = lv + np.where((j == 1) & (i % 2 == 0), 1, 0)
    return tone(R_LEATHER, lv + handf(ctx, 0.6, 0.8, 51, 0.04)), 1.0, None


def mat_dark(ctx):
    return tone(R_DARK, bevel(ctx, base=1, top=0, bottom=0, right=0)), 1.0, None


def mat_grip(ctx):
    i, j, pw, ph = _pix2(ctx)
    lv = bevel(ctx, base=2, top=0, bottom=0)
    if ctx.face in SIDE:                                            # обмотка: косые витки
        lv = lv + np.where((i + j) % 3 == 0, 1, 0)
    return tone(R_GRIP, lv), 1.0, None


def mat_blade(ctx):
    """Клинок как на референсе: светлая кромка, золото, тёмный дол по центру; плоскости — north/south (толщина по z)."""
    i, j, pw, ph = _pix(ctx)
    if ctx.face in ('north', 'south'):
        u = (i + 0.5) / pw
        if ctx.face == 'north':
            u = 1 - u
        rgb = np.where((u < 2.4 / pw)[:, None] | (u > 1 - 2.4 / pw)[:, None], R_GOLD[6], R_GOLD[4])
        if info(ctx, 'fuller', True):
            dol = np.abs(u - 0.5) < (0.5 - 3.4 / pw) if pw >= 9 else np.zeros(ctx.n, bool)
            lv = np.where(j % 12 < 2, 2, 1)
            rgb = np.where(dol[:, None], tone(R_BLADE_DARK, lv - (np.abs(u - 0.5) > 0.12)), rgb)
        # отблеск — блик вдоль кромки
        rgb = np.where(((u < 2.4 / pw) & (j % 14 < 2))[:, None], np.ones(3), rgb)
    elif ctx.face in ('east', 'west'):
        rgb = tone(R_GOLD, np.full(ctx.n, 5.0) + (ctx.face == 'east'))
    elif ctx.face == 'up':
        rgb = tone(R_GOLD, np.full(ctx.n, 6.0))
    else:
        rgb = tone(R_GOLD, np.full(ctx.n, 3.0))
    return rgb, 1.0, None


def mat_eye(ctx):
    """Глазная щель забрала: тьма, в глубине — холодный блеск глаз (glowmask)."""
    i, j, pw, ph = _pix(ctx)
    rgb = tone(R_DARK, np.zeros(ctx.n))
    g = np.zeros((ctx.n, 3))
    if ctx.face == 'north':
        eye = (j == ph // 2) & (np.abs(i - pw * 0.5 + 0.5) < 1.1)
        rgb = np.where(eye[:, None], np.array([0.30, 0.52, 0.62]), rgb)
        g = np.where(eye[:, None], np.array([0.22, 0.42, 0.52]), g)
    return rgb, 1.0, g


# ---------------------------------------------------------------- рисунки на гранях (deco): (ctx, i, j, pw, ph, rgb, lv) -> rgb
def deco_visor(ctx, i, j, pw, ph, rgb, lv):
    """Золотое забрало: дыхательные прорези рядами внизу, гравированная кромка."""
    return rgb


def deco_chest(ctx, i, j, pw, ph, rgb, lv):
    """Кираса: выпуклая грудь (светлее по центру), гравированное золотом «крыло» по верхнему краю, центральный рёберный кант."""
    c = (pw - 1) / 2
    d = np.abs(i - c) / max(1, c)
    l2 = lv + np.where(d < 0.35, 1, 0) + np.where(d > 0.85, -1, 0)
    out_ = tone(R_STEEL, l2)
    wing = (j == 2 + (np.abs(i - c) // 3).astype(int)) & (d > 0.25) & (j < ph // 2)
    out_ = np.where(wing[:, None], R_GOLD[4], out_)
    out_ = np.where(((j == 3 + (np.abs(i - c) // 3).astype(int)) & (d > 0.25) & (j < ph // 2))[:, None], R_GOLD[2], out_)
    return out_


def deco_tabard(ctx, i, j, pw, ph, rgb, lv):
    """Табард: красное поле, золотая кайма, герб — корона над мечом остриём вниз (как на щите и знамени)."""
    gold = (i == 0) | (i == pw - 1) | (j >= ph - 2)
    rgb = np.where(gold[:, None], tone(R_GOLD, np.where(j == ph - 1, 2, 4)), rgb)
    c = (pw - 1) / 2
    blade = (np.abs(i - c) < 0.6) & (j >= 9) & (j <= ph - 6)
    guard = (np.abs(i - c) <= 2.6) & (j == 9)
    crown = (j >= 3) & (j <= 6) & (np.abs(i - c) <= 2.6) & ~((j == 3) & (np.abs(i - c) % 2.5 > 0.6))
    em = blade | guard | crown
    rgb = np.where(em[:, None], tone(R_GOLD, np.where(j == 6, 3, 5)), rgb)
    return rgb


def deco_shield(ctx, i, j, pw, ph, rgb, lv):
    """Башенный щит: стальной обод, золотая внутренняя кайма, красное поле, золотой герб (корона над мечом), заклёпки."""
    rim = (i < 1) | (i >= pw - 1) | (j < 1) | (j >= ph - 1)
    trim = ((i == 1) | (i == pw - 2) | (j == 1) | (j == ph - 2)) & ~rim
    field = ~rim & ~trim
    out_ = tone(R_RED, np.full(len(i), 3.0) + np.where(i < pw / 2, 0, -1) + np.where(j < 4, 1, 0))
    out_ = np.where(rim[:, None], tone(R_STEEL, np.where(j < 1, 5, 3)), out_)
    out_ = np.where(trim[:, None], tone(R_GOLD, np.where(j == ph - 2, 2, 4)), out_)
    c = (pw - 1) / 2
    blade = (np.abs(i - c) < 0.6) & (j >= 12) & (j <= ph - 6)
    tip = (np.abs(i - c) < 0.6) & (j == ph - 5)
    guard = (np.abs(i - c) <= 3.5) & (j == 12)
    grip = (np.abs(i - c) < 0.6) & (j >= 9) & (j <= 11)
    crown = (j >= 4) & (j <= 7) & (np.abs(i - c) <= 3.6) & ~((j == 4) & (np.abs(i - c) % 1.8 > 0.6)) & ~((j == 5) & (np.abs(i - c) % 1.8 > 1.2))
    em = (blade | tip | guard | grip | crown) & field
    out_ = np.where(em[:, None], tone(R_GOLD, np.where((j == 7) | (j == 12), 3, 5)), out_)
    rv = field & ((i == 3) | (i == pw - 4)) & (j % 6 == 3)
    out_ = np.where(rv[:, None], R_STEEL[5], out_)
    return out_


def deco_belt(ctx, i, j, pw, ph, rgb, lv):
    plaque = (i % 6 == 2) & (j > 0) & (j < ph - 1)
    return np.where(plaque[:, None], R_GOLD[4], rgb)


def deco_crest(ctx, i, j, pw, ph, rgb, lv):
    """Обруч короны: золотая полоса с самоцветами."""
    g = tone(R_GOLD, np.where(j == 0, 5, 3))
    gem = (i % 5 == 2) & (j == ph // 2)
    return np.where(gem[:, None], R_RED[5], g)


def deco_skirt(ctx, i, j, pw, ph, rgb, lv):
    gold = (j >= ph - 2) | (i == 0) | (i == pw - 1)
    return np.where(gold[:, None], tone(R_GOLD, np.where(j == ph - 1, 2, 4)), rgb)


def deco_plate(ctx, i, j, pw, ph, rgb, lv):
    """Центральная пластина: рёбра-ступени, чуть светлее по оси."""
    c = (pw - 1) / 2
    l2 = lv + np.where(np.abs(i - c) < 1, 1, 0) + np.where(j % 6 == 5, -2, 0)
    out_ = tone(R_STEEL, l2)
    return np.where(((i == 0) | (i == pw - 1) | (j == ph - 1))[:, None], rgb, out_)


DECO = {'skirt': deco_skirt, 'plate': deco_plate, 'visor': deco_visor, 'chest': deco_chest, 'tabard': deco_tabard, 'shield': deco_shield, 'belt': deco_belt, 'crest': deco_crest}


def add_mats(m):
    m.materials.update(steel=mat_steel, gold=mat_gold, red=mat_red, cape=mat_cape, leather=mat_leather, dark=mat_dark,
                       grip=mat_grip, blade=mat_blade, eye=mat_eye)


# ================================================================== меч (общая форма: кость `sword` на боссе и 3D-предмет)
# Локальные координаты меча: клинок вдоль +y, гарда у y = 0..3.2, рукоять y −5…0 (правая рука у −1.2, левая у −3.6), плоскость клинка — xy.
def sword_parts():
    P = []   # (from, to, материал, info)

    def b(f, t, mat, **kw):
        P.append((np.array(f, float), np.array(t, float), mat, kw))

    # клинок с долом и ступенчатым острием
    b((-1.2, 3.2, -0.4), (1.2, 13.8, 0.4), 'blade')
    b((-0.9, 13.8, -0.35), (0.9, 15.0, 0.35), 'blade')
    b((-0.55, 15.0, -0.3), (0.55, 16.0, 0.3), 'blade', fuller=False)
    b((-0.25, 16.0, -0.25), (0.25, 16.6, 0.25), 'blade', fuller=False)
    # рикассо/лангеты: золотой корень клинка с «ушками»-завитками
    b((-1.1, 2.0, -0.6), (1.1, 3.6, 0.6), 'gold', engr=True)
    b((1.1, 2.6, -0.4), (2.0, 3.4, 0.4), 'gold')
    b((-2.0, 2.2, -0.4), (-1.1, 3.0, 0.4), 'gold')
    b((1.6, 3.4, -0.35), (2.3, 4.2, 0.35), 'gold', base=4)
    # крестовина: широкая золотая перекладина с завитками вверх (справа) и вниз (слева) — узор как на референсе
    b((-4.0, 1.0, -0.55), (4.0, 2.0, 0.55), 'gold', engr=True)
    b((3.2, 2.0, -0.45), (4.0, 3.6, 0.45), 'gold')
    b((2.4, 3.0, -0.45), (3.2, 3.8, 0.45), 'gold', base=4)
    b((-4.0, -0.8, -0.45), (-3.2, 1.0, 0.45), 'gold')
    b((-3.2, -1.2, -0.45), (-2.4, -0.4, 0.45), 'gold', base=2)
    b((4.0, 0.6, -0.4), (4.7, 1.6, 0.4), 'gold', base=4)
    b((-4.7, 1.4, -0.4), (-4.0, 2.4, 0.4), 'gold', base=4)
    # корзина: ветви вперёд и назад (по z), дуга-защита пальцев вдоль рукояти
    b((-0.5, 0.2, -2.4), (0.5, 1.2, -0.55), 'gold')
    b((-0.5, -4.6, -2.4), (0.5, 0.2, -1.7), 'gold', engr=True)
    b((-0.45, -5.0, -2.2), (0.45, -4.4, -0.6), 'gold', base=2)
    b((-1.9, -1.8, -2.0), (-1.1, 0.6, -1.3), 'gold', base=2)
    b((1.1, -2.6, -1.9), (1.9, 0.4, -1.2), 'gold')
    b((0.5, -0.4, -2.2), (1.6, 0.3, -1.6), 'gold', base=4)
    b((-0.5, 0.4, 0.55), (0.5, 1.2, 2.2), 'gold')
    b((-0.45, -1.6, 1.6), (0.45, 0.6, 2.3), 'gold', base=2)
    b((-1.6, -0.6, 1.4), (-0.6, 0.2, 2.1), 'gold', base=4)
    b((0.6, 0.4, 1.0), (1.8, 1.0, 1.7), 'gold')
    b((2.0, -0.6, -0.4), (2.8, 1.0, 0.4), 'gold', base=2)
    b((-2.6, 2.0, 0.4), (-1.8, 2.8, 1.2), 'gold', base=4)
    # гарда-воротник у рукояти
    b((-1.0, -0.4, -0.8), (1.0, 1.0, 0.8), 'gold', base=4)
    # рукоять: чёрная обмотка, золотые кольца
    b((-0.5, -5.0, -0.5), (0.5, -0.4, 0.5), 'grip')
    for y in (-2.5, -4.7):
        b((-0.65, y, -0.65), (0.65, y + 0.45, 0.65), 'gold', base=4)
    # навершие: узорный узел из брусков
    b((-0.9, -6.8, -0.9), (0.9, -5.0, 0.9), 'gold', engr=True)
    b((-1.4, -6.4, -0.5), (-0.9, -5.4, 0.5), 'gold', base=4)
    b((0.9, -6.2, -0.5), (1.4, -5.2, 0.5), 'gold', base=2)
    b((-0.5, -6.2, -1.4), (0.5, -5.4, -0.9), 'gold', base=4)
    b((-0.4, -6.4, 0.9), (0.4, -5.6, 1.4), 'gold', base=2)
    b((-0.5, -7.4, -0.5), (0.5, -6.8, 0.5), 'gold', base=5)
    b((0.4, -7.2, 0.2), (1.0, -6.6, 0.8), 'gold', base=3)
    return P


GRIP_R, GRIP_L = -1.4, -3.6          # y в координатах меча: где держат правая и левая руки
SWORD_LEN = 24.0


def add_sword(m, bone, parent, pivot, rot=(-90, 0, 0)):
    """Кость меча: шарнир в точке хвата правой руки, локально клинок вдоль +y (поворот кости переводит его вперёд)."""
    m.bone(bone, parent, pivot, rot)
    piv = np.asarray(pivot, float)
    for f, t, mat, kw in sword_parts():
        m.box(bone, piv + f - [0, GRIP_R, 0], piv + t - [0, GRIP_R, 0], mat, **kw)


# ================================================================== щит (башенный, цвета лат)
def add_shield(m, bone, parent, pivot, center, rot=(0, 0, 0), face='north'):
    """Башенный щит 10×17 ед. (в мире ×2: 1.25×2.1 бл.). Лицо — грань face (north = вперёд по −z)."""
    m.bone(bone, parent, pivot, rot)
    c = np.asarray(center, float)
    s = -1 if face == 'north' else 1                              # куда выступают накладки
    m.box(bone, c + [-5, -8.5, -0.45], c + [5, 8.5, 0.45], 'steel', deco='shield', deco_face=face)
    # стальная окантовка-рамка (объёмная) и гребень
    for x0, x1 in ((-5.3, -4.5), (4.5, 5.3)):
        m.box(bone, c + [x0, -8.8, -0.7], c + [x1, 8.8, 0.7], 'steel', lames=6, base=3)
    m.box(bone, c + [-5.3, 8.5, -0.7], c + [5.3, 9.3, 0.7], 'steel', trim='b')
    m.box(bone, c + [-3.2, 9.3, -0.6], c + [-1.6, 10.0, 0.6], 'steel', base=4)            # зубцы сверху
    m.box(bone, c + [1.6, 9.3, -0.6], c + [3.2, 10.0, 0.6], 'steel', base=4)
    m.box(bone, c + [-5.3, -9.3, -0.7], c + [5.3, -8.5, 0.7], 'steel', trim='t')
    m.box(bone, c + [-2.6, -10.2, -0.6], c + [2.6, -9.3, 0.6], 'steel', base=2)          # нижний клин
    # умбон-герб: золотая корона-накладка и перекрестье
    z0, z1 = (c[2] + 0.45 * s, c[2] + 1.0 * s)
    zz = (min(z0, z1), max(z0, z1))
    m.box(bone, [c[0] - 1.3, c[1] + 1.6, zz[0]], [c[0] + 1.3, c[1] + 3.6, zz[1]], 'gold', engr=True)
    m.box(bone, [c[0] - 2.2, c[1] + 1.0, zz[0]], [c[0] + 2.2, c[1] + 1.6, zz[1]], 'gold', base=4)
    # ручка с обратной стороны
    zb = (c[2] - 1.4 * s, c[2] - 0.45 * s)
    m.box(bone, [c[0] - 0.6, c[1] - 3, min(zb)], [c[0] + 0.6, c[1] + 3, max(zb)], 'leather')


# ================================================================== Мартин
def build_martin():
    m = Model('martin', density=DENS, tex_w=128)
    add_mats(m)
    m.bone('body', None, (0, 12, 0))
    # ---------------------------------------------------------------- торс
    m.bone('torso', 'body', (0, 24, 0))
    m.box('torso', (-4.5, 12, -2.5), (4.5, 24, 2.5), 'red', base=2)                         # красный поддоспешник
    m.box('torso', (-3.5, 16.6, -3.1), (3.5, 24, 2.9), 'steel', deco='chest', lames=0, fili=True)       # кираса
    m.box('torso', (-0.55, 16.4, -3.55), (0.55, 23.4, -3.0), 'steel', base=4)               # рёберный кант
    m.box('torso', (-2.8, 13.4, -3.0), (2.8, 16.8, 2.8), 'steel', lames=4, base=3)           # пластины живота (плакарт)
    m.box('torso', (-4.4, 17.0, 2.4), (4.4, 23.6, 3.1), 'steel', base=3, fili=True)                    # спинная пластина
    # золотой ворот (горжет) и V-кант к груди — как на референсе
    m.box('torso', (-3.0, 23.2, -3.3), (3.0, 24.8, 2.7), 'gold', engr=True)
    for sx in (-1, 1):
        m.rod('torso', (sx * 2.6, 23.6, -3.25), (sx * 0.5, 20.4, -3.3), 0.9, 0.5, 'gold', ext=0.2, base=4)
    # пояс с золотой пряжкой
    m.box('torso', (-4.7, 12.0, -2.9), (4.7, 13.5, 2.9), 'leather', deco='belt', stitch=True)
    m.box('torso', (-0.9, 11.8, -3.25), (0.9, 13.7, -2.85), 'gold', base=4)
    # фалды (набедренная юбка из пластин) — спереди и по бокам
    m.box('torso', (-4.6, 10.4, -3.0), (4.6, 12.1, 2.8), 'steel', trim='b', lames=0, base=3)
    # табард: красный с золотой каймой и гербом, спереди и сзади
    m.bone('tabard_front', 'torso', (0, 12.2, -3.1))
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 1.4, sx * 4.5))
        m.box('tabard_front', (x0, 3.2, -3.4), (x1, 12.2, -3.0), 'red', deco='skirt', base=3)
    m.box('tabard_front', (-1.9, 3.6, -3.75), (1.9, 12.2, -3.3), 'steel', base=4, trim='lrb', deco='plate')
    m.box('tabard_front', (-1.1, 2.2, -3.7), (1.1, 3.6, -3.35), 'steel', base=3, trim='b')
    m.bone('tabard_back', 'torso', (0, 12.2, 3.0))
    m.box('tabard_back', (-2.8, 3.4, 2.95), (2.8, 12.2, 3.3), 'red', deco='tabard', deco_face='south', folds=False)
    # плащ: воротник-валик, верх от плеч, низ до земли (две кости для взмаха)
    m.box('torso', (-7.4, 22.4, 1.6), (7.4, 24.6, 4.3), 'cape', outer='south', edge_l=False, edge_r=False)
    m.bone('cape', 'torso', (0, 23.6, 3.6))
    m.box('cape', (-7.6, 11.0, 3.3), (7.6, 23.6, 4.1), 'cape', outer='south')
    for sx in (-1, 1):                                                                       # полы плаща заворачивают вперёд
        x0, x1 = sorted((sx * 7.6, sx * 8.4))
        m.box('cape', (x0, 11.0, 0.2), (x1, 22.6, 4.1), 'cape', outer='east' if sx > 0 else 'west', edge_r=False)
    m.bone('cape_low', 'cape', (0, 11.0, 3.7))
    m.box('cape_low', (-8.0, 0.4, 3.3), (8.0, 11.0, 4.1), 'cape', outer='south', edge_b=True)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 8.0, sx * 8.8))
        m.box('cape_low', (x0, 0.4, -0.4), (x1, 11.0, 4.1), 'cape', outer='east' if sx > 0 else 'west', edge_r=False, edge_b=True)
    # ---------------------------------------------------------------- голова: шлем-корона, рога, золотое забрало
    m.bone('head', 'body', (0, 24, 0))
    m.box('head', (-4.1, 24.2, -4.1), (4.1, 31.6, 4.1), 'steel', lames=0, base=3, fili=True)
    m.box('head', (-3.2, 25.0, -4.6), (3.2, 29.4, -4.1), 'gold', deco='visor', base=4)       # забрало
    m.box('head', (-3.0, 28.0, -4.75), (-0.7, 28.9, -4.5), 'eye')                         # глазные щели
    m.box('head', (0.7, 28.0, -4.75), (3.0, 28.9, -4.5), 'eye')
    m.box('head', (-4.4, 28.9, -4.9), (4.4, 30.2, -4.0), 'steel', base=4)         # надбровье
    m.box('head', (-0.6, 25.4, -5.1), (0.6, 30.0, -4.55), 'steel', base=4)                  # наносник
    for sx in (-1, 1):                                                                       # нащёчники
        m.box('head', (min(sx * 3.7, sx * 4.7), 24.0, -4.5), (max(sx * 3.7, sx * 4.7), 29.0, 1.6), 'steel', base=3, trim='b')
    m.box('head', (-4.0, 23.2, 3.5), (4.0, 26.6, 4.7), 'steel', lames=4)                    # назатыльник
    # корона: обруч с самоцветами + зубцы, купол
    m.box('head', (-4.5, 30.8, -4.5), (4.5, 32.0, 4.5), 'steel', base=4)
    m.box('head', (-3.5, 31.6, -3.5), (3.5, 33.0, 3.5), 'steel', base=4)
    for x, h in ((-2.6, 1.6), (0.0, 2.6), (2.6, 1.6)):
        m.box('head', (x - 0.5, 32.0, -4.5), (x + 0.5, 32.0 + h, -3.7), 'steel', base=4)
    m.box('head', (-0.35, 32.0, -4.65), (0.35, 33.4, -4.35), 'steel', base=5)
    # высокие рога-зубцы (как на референсе: почти вертикальные, с отростком внутрь)
    for sx in (-1, 1):
        m.rod('head', (sx * 3.0, 31.6, 0.4), (sx * 3.8, 37.0, 0.8), 1.9, 1.1, 'steel', base=4)
        m.rod('head', (sx * 3.8, 36.8, 0.8), (sx * 3.9, 39.0, 1.1), 1.3, 0.9, 'steel', base=5)
        m.rod('head', (sx * 3.4, 34.6, 0.9), (sx * 2.2, 36.0, 0.9), 0.9, 0.9, 'steel', base=4)
        m.rod('head', (sx * 3.8, 33.4, 0.8), (sx * 5.0, 34.8, 0.8), 0.8, 0.8, 'steel', base=2)
    # ---------------------------------------------------------------- руки (кости Iron's + предплечья для поз двуручником)
    for side, sn in ((1, 'right'), (-1, 'left')):
        X = side * 5.6
        arm = sn + '_arm'
        fore = sn + '_forearm'
        m.bone(arm, 'body', (X, 22, 0))
        xs = lambda a, b: (min(X + side * a, X + side * b), max(X + side * a, X + side * b))
        x0, x1 = xs(-1.5, 1.5)
        m.box(arm, (x0, 16.4, -1.5), (x1, 22.4, 1.5), 'red', base=2)
        x0, x1 = xs(-1.7, 1.75)
        m.box(arm, (x0, 17.0, -1.75), (x1, 20.6, 1.75), 'steel', base=3, fili=True)                  # наплечник руки (ребрасс)
        # наплечник: три ламы + шипы
        x0, x1 = xs(-2.2, 3.0)
        m.box(arm, (x0, 21.0, -3.0), (x1, 24.2, 3.0), 'steel', trim='b', base=4, fili=True)
        x0, x1 = xs(-0.6, 3.4)
        m.box(arm, (x0, 19.4, -2.8), (x1, 21.4, 2.8), 'steel', trim='b')
        x0, x1 = xs(0.4, 3.5)
        m.box(arm, (x0, 18.0, -2.5), (x1, 19.8, 2.5), 'steel', trim='b', base=2)
        for p, q, w in (((X + side * 0.4, 24.0, -1.4), (X + side * 1.6, 28.0, -1.8), 1.0),
                        ((X + side * 1.8, 23.8, 0.6), (X + side * 3.8, 27.0, 1.0), 0.9),
                        ((X + side * 2.8, 22.6, -0.6), (X + side * 5.4, 24.4, -0.8), 0.8)):
            m.rod(arm, p, q, w, w, 'steel', base=4)
        # предплечье: локоть, наруч, золотая манжета, перчатка
        m.bone(fore, arm, (X, 16.6, 0))
        x0, x1 = xs(-1.45, 1.45)
        m.box(fore, (x0, 12.6, -1.45), (x1, 16.6, 1.45), 'red', base=2)
        m.box(fore, (X - 1.8, 15.4, -1.9), (X + 1.8, 17.4, 1.7), 'steel', base=4)            # налокотник
        x0, x1 = xs(1.7, 2.3)
        m.box(fore, (x0, 14.8, -1.4), (x1, 17.8, 1.2), 'steel', base=3)                      # веер налокотника
        m.box(fore, (X - 1.75, 12.8, -1.75), (X + 1.75, 15.4, 1.75), 'steel', base=3, fili=True)        # наруч
        m.box(fore, (X - 2.0, 11.8, -2.0), (X + 2.0, 13.2, 2.0), 'gold', engr=True)          # золотая манжета
        m.box(fore, (X - 1.4, 9.4, -1.4), (X + 1.4, 11.8, 1.4), 'gold', base=2)              # латная перчатка
        m.box(fore, (X - 1.5, 9.0, -1.5), (X + 1.5, 9.8, 1.5), 'steel', base=3)              # пальцы
        m.bone('bipedHand' + sn.capitalize(), fore, (X, 10.6, -0.2))
        m.bone(sn + 'Item', 'bipedHand' + sn.capitalize(), (X, 10.6, 0), (90, 0, 0))
    # ---------------------------------------------------------------- ноги: набедренник, наколенник, поножи, сабатоны
    for side, sn in ((1, 'right'), (-1, 'left')):
        X = side * 2.3
        leg = sn + '_leg'
        m.bone(leg, 'body', (X, 12, 0))
        m.box(leg, (X - 2.0, 6.6, -2.0), (X + 2.0, 12.0, 2.0), 'red', base=2)
        m.box(leg, (X - 2.2, 7.2, -2.3), (X + 2.2, 11.4, 2.0), 'steel', base=3, trim='b', fili=True)              # набедренник
        m.box(leg, (X - 1.8, 5.2, -2.9), (X + 1.8, 7.8, -1.6), 'steel', base=4, trim='b')    # наколенник
        m.box(leg, (X - 1.2, 5.8, -3.25), (X + 1.2, 7.2, -2.9), 'steel', base=5)
        m.box(leg, (X - 2.0, 1.6, -2.1), (X + 2.0, 6.6, 2.0), 'steel', lames=0, base=3, fili=True)       # поножи
        m.box(leg, (X - 0.4, 1.8, -2.4), (X + 0.4, 6.0, -2.1), 'steel', base=4)              # ребро поножей
        m.box(leg, (X - 2.2, 0.0, -3.6), (X + 2.2, 1.8, 2.2), 'steel', lames=0, base=3, trim='t')  # сабатон
        m.box(leg, (X - 1.6, 0.0, -4.4), (X + 1.6, 1.2, -3.6), 'steel', base=4)
    # ---------------------------------------------------------------- меч, щит (на спине и в руке), знамя в руке (для установки знамени)
    add_sword(m, 'sword', 'right_forearm', (5.6, 10.6, -0.2))
    add_shield(m, 'shield_back', 'torso', (0,) + SHB_PIV, (0,) + SHB_CENTER, rot=(SHB_TILT, 0, 0), face='south')
    add_shield(m, 'shield_hand', 'left_forearm', (-5.6, 14.0, 0), (-5.6, 12.5, -3.9), face='north')
    build_held_banner(m)
    return m


def build_held_banner(m):
    """Знамя в левой руке (кость banner_held) — только в анимации установки знамени; потом его заменяет сущность знамени."""
    m.bone('banner_held', 'left_forearm', (-5.6, 10.6, -0.2), (-90, 0, 0))
    p = np.array([-5.6, 10.6, -0.2])
    m.box('banner_held', p + [-0.5, -10, -0.5], p + [0.5, 22, 0.5], 'leather', base=3)
    m.box('banner_held', p + [-0.8, 22, -0.8], p + [0.8, 23.6, 0.8], 'gold', base=4)
    m.box('banner_held', p + [-0.4, 23.6, -0.4], p + [0.4, 26.4, 0.4], 'gold', base=5)
    m.box('banner_held', p + [-5.5, 20.4, -0.4], p + [5.5, 21.2, 0.4], 'gold', base=3)
    m.box('banner_held', p + [-5.0, 8.0, -0.2], p + [5.0, 20.4, 0.2], 'red', deco='tabard', folds=False)


# ================================================================== FK/IK для поз (две руки на рукояти)
def bone_chain(m, name):
    ch = []
    b = m.bones[name]
    while b is not None:
        ch.append(b)
        b = m.bones.get(b.parent) if b.parent else None
    return ch[::-1]


def fk(m, pose, name):
    """Мир-трансформ кости (M, o) с позой: pose[bone] = {'rot': [..], 'pos': [..]} (BB, градусы)."""
    M, o = np.eye(3), np.zeros(3)
    for b in bone_chain(m, name):
        p = pose.get(b.name, {})
        r = np.add(b.rot, p.get('rot', (0, 0, 0)))
        d = np.asarray(p.get('pos', (0, 0, 0)), float)
        R = euler(r)
        o = M @ (b.pivot + d - R @ b.pivot) + o
        M = M @ R
    return M, o


def world_pt(m, pose, bone, pt):
    M, o = fk(m, pose, bone)
    return M @ np.asarray(pt, float) + o


def grip_point(m, pose, y):
    """Точка на рукояти меча (y в координатах меча) в мире."""
    piv = m.bones['sword'].pivot
    return world_pt(m, pose, 'sword', piv + [0, y - getattr(m, 'grip_r', GRIP_R), 0])


HAND = {'left': np.array([-5.6, 10.6, -0.2]), 'right': np.array([5.6, 10.6, -0.2])}


ARM_STARTS = ([60.0, 0.0, 0.0, 20.0], [-40.0, 0.0, 0.0, 30.0], [10.0, 0.0, 0.0, 50.0], [100.0, 0.0, 0.0, 30.0], [160.0, 0.0, 0.0, 40.0],
              [40.0, 0.0, -40.0, 40.0], [40.0, 0.0, 40.0, 40.0], [120.0, 30.0, 0.0, 70.0], [120.0, -30.0, 0.0, 70.0])


def solve_arm(m, pose, side, target, init=None, iters=300):
    """Повороты <side>_arm (x, y, z) и <side>_forearm (x), чтобы кисть легла в target (покоординатный спуск).
    Внутренние оси (как у GeckoLib): forearm X > 0 — кисть к передней стороне плеча (сгиб локтя), X < 0 — разгиб назад —
    запрещён (правка 20.11: раньше штраф стоял наоборот, и IK выворачивал локоть). С init (решение прошлого кадра) — малый
    шаг и штраф за отход от него: решение не перескакивает на другую ветвь между кадрами. Без init — несколько стартов."""
    arm, fore = side + '_arm', side + '_forearm'

    def err(v, ref=None):
        p = dict(pose)
        p[arm] = dict(pose.get(arm, {}), rot=[v[0], v[1], v[2]])
        p[fore] = {'rot': [v[3], 0, 0]}
        e = world_pt(m, p, fore, getattr(m, 'hand', HAND)[side]) - target
        pen = 0.002 * (max(0, -v[3]) ** 2 + max(0, v[3] - 125) ** 2) + 0.00002 * (v[1] ** 2 + v[2] ** 2)
        if ref is not None:
            pen += 0.0004 * float(np.sum((v - ref) ** 2))
        return float(e @ e) + pen

    def descend(x, step, ref):
        best = err(x, ref)
        for _ in range(iters):
            improved = False
            for k in range(4):
                for d in (step, -step):
                    y = x.copy()
                    y[k] += d
                    e = err(y, ref)
                    if e < best:
                        best, x, improved = e, y, True
            if not improved:
                step *= 0.6
                if step < 0.05:
                    break
        return x

    if init is not None:
        ref = np.array(init, float)
        x = descend(ref.copy(), 3.0, ref)
    else:
        cands = [descend(np.array(s0, float), 16.0, None) for s0 in ARM_STARTS]
        x = min(cands, key=lambda v: err(v))
    return x, math.sqrt(max(0, err(x)))


def solve_left(m, pose, target, init=None, iters=300):
    return solve_arm(m, pose, 'left', target, init, iters)


# ================================================================== анимации
def ease(k, kind='io'):
    k = min(1.0, max(0.0, k))
    if kind == 'in':                        # удар: разгон. Было k³ — последний кадр (0.04 с) давал половину пути, клинок
        return k * k                        # «прыгал» на 100°+; k² — треть пути (правка 20.11)
    if kind == 'out':
        return 1 - (1 - k) ** 3
    if kind == 'back':                      # с перехлёстом (удар)
        c = 1.6
        return 1 + (c + 1) * (k - 1) ** 3 + c * (k - 1) ** 2
    if kind == 'lin':
        return k
    return k * k * (3 - 2 * k)


def track(t, keys):
    """keys: [(t, value, ease_kind_to_this_key), ...]; value — число или список. Интерполяция по ключам."""
    if t <= keys[0][0]:
        return np.asarray(keys[0][1], float)
    for (t0, v0, *_), (t1, v1, *e) in zip(keys, keys[1:]):
        if t <= t1:
            k = ease((t - t0) / max(1e-6, t1 - t0), e[0] if e else 'io')
            return np.asarray(v0, float) * (1 - k) + np.asarray(v1, float) * k
    return np.asarray(keys[-1][1], float)


HIDE = [0, 0, 0]
SHOW = [1, 1, 1]


# ------------------------------------------------------------------ плащ, табард, щит на спине (правка 20.11)
# Знак: во внутренних углах генератора (Anim.key; в JSON знак X меняется) поворот X > 0 уводит НИЗ свисающей кости ВПЕРЁД (−z),
# X < 0 — НАЗАД. Раньше cape_follow писал «+ = назад» → плащ шёл вперёд сквозь ноги (замечание владельца по видео T29).
# Теперь плащ висит «по гравитации» в мире: желаемый угол назад от вертикали + ограничения в боковой плоскости (y, z): не входит
# в спину, позади ног и заднего табарда, над землёй, под щитом на спине (щит подвешен у верхнего края и качается вместе с плащом).
CAPE_PIV = (23.6, 3.6)          # кость cape (y, z модели)
CAPE_HINGE = (11.0, 3.7)        # кость cape_low
CAPE_HEM = 0.4                  # низ плаща (y)
CAPE_FRONT, CAPE_BACK = 3.3, 4.1
SHB_PIV = (25.0, 4.4)           # щит на спине: ось у верхнего края (ремень)
SHB_CENTER = (15.0, 5.3)
SHB_TILT = -4.0                 # покой: низ щита чуть отходит назад от спины (внутр. угол X)
SHB_INNER = 4.6                 # внутренняя грань рамки щита (z покоя) и низ щита (y)
SHB_BOTTOM = 4.8
TAB_F = ((12.2, -3.1), 2.2)     # табард спереди: ось (y, z), низ (y)
TAB_B = ((12.2, 3.0), 3.4)      # табард сзади


def _R(a, v):
    a = math.radians(a)
    c, s = math.cos(a), math.sin(a)
    return np.array([v[0] * c - v[1] * s, v[0] * s + v[1] * c])


def _rx(o, b):
    v = o.get(b, {}).get('rot')
    return float(v[0]) if v is not None else 0.0


class Side:
    """Боковая плоскость (y вверх, z назад) позы o: мировые точки body/torso/ног (повороты X; Y/Z костей малы и не учитываются)."""

    def __init__(self, o):
        pos = o.get('body', {}).get('pos', [0, 0, 0])
        self.Ob = np.array([12.0 + pos[1], pos[2]])
        self.Ab = _rx(o, 'body')
        self.At = self.Ab + _rx(o, 'torso')
        self.Ot = self.Ob + _R(self.Ab, (12.0, 0.0))
        self.legs = [self.Ab + _rx(o, 'right_leg'), self.Ab + _rx(o, 'left_leg')]

    def torso(self, p, rel=0.0, piv=None):
        """Точка p (y, z модели) кости-ребёнка торса с осью piv и своим поворотом rel."""
        if piv is None:
            return self.Ot + _R(self.At, np.subtract(p, (24.0, 0.0)))
        return self.torso(piv) + _R(self.At + rel, np.subtract(p, piv))

    def leg_pts(self):
        out = []
        for a in self.legs:
            for y, z in ((12, 2.0), (9, 2.0), (6.6, 2.0), (4, 2.0), (1.8, 2.2), (0, 2.2), (0, -1), (0, -3.6), (0, -4.4), (1.2, -4.4),
                         (4, -2.3), (6, -3.25), (9, -2.3), (12, -2.3)):
                out.append(self.Ob + _R(a, (y - 12.0, z)))
        return out


def _behind(P0, P1, pts, off, margin, front=False, smin=-0.5):
    """Насколько точки pts заходят за грань полосы P0→P1 (грань смещена на off по нормали «назад»; front — по нормали «вперёд»).
    > 0 — пересечение. Нормаль «назад» для отвесного отрезка сверху вниз — +z."""
    d = P1 - P0
    L = float(np.linalg.norm(d))
    d = d / L
    n = np.array([d[1], -d[0]]) * (-1 if front else 1)
    worst = -1e9
    for q in pts:
        w = q - P0
        s = float(w @ d)
        if smin <= s <= L + 0.3:
            worst = max(worst, float(w @ n) - off + margin)
    return worst


def cape_follow(t, o, base=4.0, sway=1.0, lag=0.0, period=3.0, wind=0.0, side=0.0):
    """Плащ: lag/wind — отлёт НАЗАД от движения (градусы, +), sway — колыхание, side — отлёт вбок (Z).
    Только запоминает желаемое; итоговые углы cape/cape_low/табардов/щита на спине считает solve_cape() из vis()."""
    bb_in(o)
    s = math.sin(TAU * t / period)
    back = max(1.5, base + lag + wind + 1.5 * sway * s)
    low = max(0.0, 2.0 + 0.6 * max(lag, 0.0) + 0.4 * wind + 2.0 * sway * math.sin(TAU * t / period - 0.8))
    tw = o.get('torso', {}).get('rot', [0, 0, 0])[1] + (((o.get('body', {}).get('rot', [0, 0, 0])[1] + 180) % 360) - 180)
    z = 0.8 * sway * math.sin(TAU * t / period * 0.5) + side - 0.15 * tw       # поворот корпуса — полы отстают вбок
    o['_cape'] = dict(back=back, low=low, z=max(-9.0, min(9.0, z)), tab=1.5 * sway * s)
    return o


def solve_cape(o, shield_back):
    """Итоговые углы cape, cape_low, tabard_front/back и shield_back для позы o (внутренние углы: X < 0 — низ назад)."""
    prm = o.pop('_cape', None) or dict(back=3.0, low=2.0, z=0.0, tab=0.0)
    S = Side(o)
    legs = S.leg_pts()
    # --- табарды: висят отвесно (+ лёгкое колыхание), не входят в ноги и в землю. Верх (3 ед. у оси) не проверяем: торс
    #     вращается вокруг плеч, и у пояса бёдра и так заходят под табард — это шов модели, поворотом табарда его не убрать
    tb = float(np.clip(-S.At + 0.5 * prm['tab'], -80, 4))
    for _ in range(80):
        P0, P1 = S.torso(TAB_B[0]), S.torso((TAB_B[1], TAB_B[0][1]), tb, TAB_B[0])
        if (_behind(P0, P1, legs, -0.1, 0.2, smin=3.0) <= 0 and P1[0] >= 0.2) or tb < -70:
            break
        tb -= 1.5
    tf = float(np.clip(-S.At - 0.5 * prm['tab'], -6, 80))
    for _ in range(80):
        P0, P1 = S.torso(TAB_F[0]), S.torso((TAB_F[1], TAB_F[0][1]), tf, TAB_F[0])
        if (_behind(P0, P1, legs, 0.3, 0.0, front=True, smin=3.0) <= 0 and P1[0] >= 0.2) or tf > 70:
            break
        tf += 1.5      # грань наколенника (−3.25) в покое уже под табардом — сверяем с лицевой гранью (−3.4)
    obst = legs + [S.torso((y, 3.05), tb, TAB_B[0]) for y in (12.2, 7.8, 3.4)]      # грань табарда 3.3 = грань плаща (касание)
    # --- плащ и щит
    rc = min(-0.5, -prm['back'] - S.At)
    rl = -prm['low']

    def cape(rc, rl):
        Pc = S.torso(CAPE_PIV)
        Ph = S.torso(CAPE_HINGE, rc, CAPE_PIV)
        Pe = Ph + _R(S.At + rc + rl, (CAPE_HEM - CAPE_HINGE[0], 0.0))
        return Pc, Ph, Pe

    def cape_back_pts(rc, rl):
        up = [S.torso((y, CAPE_BACK), rc, CAPE_PIV) for y in (20.0, 16.0, 12.0)]
        Ph = S.torso(CAPE_HINGE, rc, CAPE_PIV)
        lo = [Ph + _R(S.At + rc + rl, (y - CAPE_HINGE[0], CAPE_BACK - CAPE_HINGE[1])) for y in (9.0, 7.0, 5.0)]
        return up + lo

    def shield(rc):
        top = S.torso((24.0, SHB_INNER), rc + SHB_TILT, SHB_PIV)
        bot = S.torso((SHB_BOTTOM, SHB_INNER), rc + SHB_TILT, SHB_PIV)
        out = S.torso((SHB_BOTTOM, 6.0), rc + SHB_TILT, SHB_PIV)
        return top, bot, out

    def v_cape_shield(rc, rl):
        if not shield_back:
            return -1.0
        top, bot, _ = shield(rc)
        return _behind(top, bot, cape_back_pts(rc, rl), 0.0, 0.1)

    for _ in range(400):
        Pc, Ph, Pe = cape(rc, rl)
        v_up = _behind(Pc, Ph, obst, CAPE_FRONT - CAPE_PIV[1], 0.3)
        v_lo = _behind(Ph, Pe, obst, CAPE_FRONT - CAPE_PIV[1], 0.3)
        v_gr = 0.25 - min(Pe[0], (Pe + _R(S.At + rc + rl, (0.0, 0.8)))[0])      # высота — y (индекс 0)
        if shield_back:
            top, bot, out = shield(rc)
            v_sh = max(0.25 - min(bot[0], out[0]), _behind(top, bot, legs, 0.0, 0.3))
        else:
            v_sh = -1.0
        v_cs = v_cape_shield(rc, rl)
        if max(v_up, v_lo, v_gr, v_sh, v_cs) <= 0 or rc < -120:
            break
        if v_up > 0 or v_sh > 0:
            rc -= 1.0
        elif v_lo > 0 or v_gr > 0:
            if rl > -110 and v_cape_shield(rc, rl - 1.5) <= 0:
                rl -= 1.5
            else:
                rc -= 1.0
        else:
            rl += 0.5
    o['cape'] = {'rot': [rc, 0, prm['z']]}
    o['cape_low'] = {'rot': [rl, 0, -0.4 * prm['z']]}
    o['tabard_front'] = {'rot': [tf, 0, 0]}
    o['tabard_back'] = {'rot': [tb, 0, 0]}
    o['shield_back'] = dict(o.get('shield_back', {}), rot=[rc if shield_back else 0.0, 0, 0.6 * prm['z'] if shield_back else 0.0])
    return o


CLOTH = ('cape', 'cape_low', 'tabard_front', 'tabard_back', 'shield_back')


def smooth_cloth(a, rate=450.0):
    """Ткань и щит на спине не прыгают: скорость угла не больше rate °/с (ткань чуть отстаёт, а не дёргается, когда ограничения
    решателя переключаются от кадра к кадру). У петли — два прохода, чтобы начало совпало с концом."""
    for b in CLOTH:
        kf = a.keys.get(b, {}).get('rot')
        if not kf:
            continue
        ts = sorted(kf)
        cur = np.array(kf[ts[-1]] if a.loop is True else kf[ts[0]], float)
        for _ in range(2 if a.loop is True else 1):
            prev_t = ts[0]
            for t in ts:
                lim = rate * max(t - prev_t, 0.04 if t == ts[0] and a.loop is True else 0.0)
                tgt = np.array(kf[t], float)
                cur = cur + np.clip(tgt - cur, -lim, lim) if t != ts[0] or a.loop is True else tgt
                kf[t] = [float(x) for x in cur]
                prev_t = t
    return a


def vis(o, shield_hand=False, banner=False):
    bb_in(o)
    o['shield_hand'] = dict(o.get('shield_hand', {}), scale=SHOW if shield_hand else HIDE)
    o['shield_back'] = dict(o.get('shield_back', {}), scale=HIDE if shield_hand else SHOW)
    o['banner_held'] = dict(o.get('banner_held', {}), scale=SHOW if banner else HIDE)
    solve_cape(o, not shield_hand)
    o.pop('_int', None)
    return o


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def bb_in(o):
    """Позы в анимациях заданы вручную по правилам Blockbench/Iron's (X > 0 — руку/ногу назад, торс вперёд; X < 0 — руку вперёд,
    голову вверх). Внутренние оси генератора (FK/IK, Anim.key) — это оси GeckoLib после чтения JSON: X и Y со знаком минус.
    Переводим ручные углы ОДИН раз на позу, до IK (цель кисти — в осях торса) и до решателя плаща. Углы, которые потом
    дописывают IK/решатель, уже внутренние. До правки 20.11 перевода не было, и Anim.to_json переворачивал X/Y ещё раз:
    вручную заданные кости (торс, голова, свободная левая рука, предплечья, ноги, плащ) шли в обратную сторону."""
    if o.get('_int'):
        return o
    for b, ch in list(o.items()):
        if isinstance(ch, dict) and 'rot' in ch:
            r = ch['rot']
            o[b] = dict(ch, rot=[-r[0], -r[1], r[2]])
    o['_int'] = True
    return o


class Grip:
    """Хват меча: кисть правой руки — в точку hand (координаты торса в покое), клинок — по направлению d (тоже в осях торса),
    левая рука (по желанию, с весом w) — на рукоять. Решения переносятся между кадрами (плавно, без скачков)."""

    def __init__(self, m):
        self.m = m
        self.reset()

    def reset(self):
        self.pr, self.pl, self.c, self.a = None, None, None, None

    def __call__(self, o, hand, d, left=1.0, ly=GRIP_L):
        bb_in(o)
        m = self.m
        Mt, ot = fk(m, o, 'torso')
        tgt = Mt @ np.asarray(hand, float) + ot
        sol, _ = solve_arm(m, o, 'right', tgt, self.pr)
        self.pr = sol
        o['right_arm'] = dict(o.get('right_arm', {}), rot=list(sol[:3]))
        o['right_forearm'] = {'rot': [sol[3], 0, 0]}
        Mf, _ = fk(m, o, 'right_forearm')
        v = Mf.T @ (Mt @ unit(d))
        # углы кости меча [a, 0, c]: у направления два равных представления (a, c) и (180 − a, c + 180), а у клинка вдоль оси Z
        # предплечья крен c вообще не определён. Берём вариант, ближайший к прошлому кадру (правка 20.11: были провороты на 180°)
        c0 = math.degrees(math.atan2(-v[0], v[1]))
        cands = [c0, c0 + 180.0] + ([self.c] if self.c is not None else [])
        best = None
        for c in cands:
            cr = math.radians(c)
            a = math.degrees(math.atan2(v[2], -math.sin(cr) * v[0] + math.cos(cr) * v[1]))
            ar = math.radians(a)
            dirr = np.array([-math.sin(cr) * math.cos(ar), math.cos(cr) * math.cos(ar), math.sin(ar)])
            derr = float(np.linalg.norm(dirr - v))
            if self.c is not None:
                c += 360 * round((self.c - c) / 360)
                a += 360 * round((self.a - a) / 360)
                cost = abs(c - self.c) + abs(a - self.a) + 400 * derr
            else:
                cost = abs(a) + 400 * derr
            if best is None or cost < best[0]:
                best = (cost, a, c)
        _, a, c = best
        self.a, self.c = a, c
        rest = m.bones['sword'].rot
        o['sword'] = {'rot': [a - rest[0], 0, c - rest[2]]}
        if left > 0.001:
            tl = grip_point(m, o, ly)
            sl, _ = solve_arm(m, o, 'left', tl, self.pl)
            self.pl = sl
            own = np.array(o.get('left_arm', {}).get('rot', [0, 0, 0]), float)
            ownf = np.array(o.get('left_forearm', {}).get('rot', [0, 0, 0]), float)
            o['left_arm'] = dict(o.get('left_arm', {}), rot=list(own * (1 - left) + sl[:3] * left))
            o['left_forearm'] = {'rot': list(ownf * (1 - left) + np.array([sl[3], 0, 0]) * left)}
        return o


class ShieldFront:
    """Щит в левой руке лицом вперёд: кисть — в точку hand (оси торса), щит повёрнут к торсу (tilt — наклон назад, yaw — разворот)."""

    def __init__(self, m):
        self.m = m
        self.prev = None

    def __call__(self, o, hand, tilt=0.0, yaw=0.0, w=1.0):
        bb_in(o)
        m = self.m
        Mt, ot = fk(m, o, 'torso')
        sol, _ = solve_arm(m, o, 'left', Mt @ np.asarray(hand, float) + ot, self.prev)
        self.prev = sol
        own = np.array(o.get('left_arm', {}).get('rot', [0, 0, 0]), float)
        o['left_arm'] = dict(o.get('left_arm', {}), rot=list(own * (1 - w) + sol[:3] * w))
        o['left_forearm'] = {'rot': [sol[3] * w, 0, 0]}
        Mf, _ = fk(m, o, 'left_forearm')
        R = Mf.T @ Mt @ euler([tilt, yaw, 0])
        o['shield_hand'] = dict(o.get('shield_hand', {}), rot=list(np.array(to_euler(R)) * w))
        return o


def slerp_dir(a, b, k):
    a, b = unit(a), unit(b)
    w = math.acos(max(-1.0, min(1.0, float(a @ b))))
    if w < 1e-4:
        return a
    return unit((math.sin((1 - k) * w) * a + math.sin(k * w) * b) / math.sin(w))


VIA_FWD = (0.0, 0.3, -1.0)      # почти противоположные направления клинка — проводим через «вперёд»


def lerp_dir(a, b, k, via=None):
    """Направление клинка между a и b: по дуге (slerp), равномерно по углу. Было линейное смешение векторов — у почти
    противоположных (размах справа налево, замах → удар сверху, меч из земли вверх) вектор проходил возле нуля и клинок
    разворачивался на 110–130° за кадр (правка 20.11). Угол > 140° без via — через VIA_FWD."""
    a, b = unit(a), unit(b)
    if via is None and float(a @ b) < math.cos(math.radians(140)):
        via = VIA_FWD
    if via is None:
        return slerp_dir(a, b, k)
    v = unit(via)
    wa = math.acos(max(-1.0, min(1.0, float(a @ v))))
    wb = math.acos(max(-1.0, min(1.0, float(v @ b))))
    s0 = k * (wa + wb)
    return slerp_dir(a, v, s0 / wa) if s0 <= wa else slerp_dir(v, b, (s0 - wa) / max(1e-6, wb))


# ключевые хваты (точки кисти и направления клинка в осях торса; торс в покое: плечи y 22, пояс y 12, перед −z)
AROUND_HEAD = np.array([2.0, 0.0, -5.0])     # подъём меча над головой: кисть идёт дугой вперёд-вправо, клинок не режет шлем и рога
GUARD = ((2.2, 14.6, -6.4), (-0.3, 0.72, -0.62))           # стойка: клинок вверх-вперёд, острие на противника
LEAN = ((0.3, 18.6, -7.6), (0.0, -0.99, -0.12))            # опирается: меч остриём в землю перед ним
SHOULDER = ((4.6, 18.0, -4.6), (0.18, 0.62, 0.76))         # на плече (ходьба): клинок назад через плечо


def anims(m):
    an = []
    g = Grip(m)
    sf = ShieldFront(m)

    def A(name, length, loop=False):
        a = Anim('martin_' + name, length, loop)
        an.append(a)
        g.reset()
        sf.prev = None
        if loop is True:                       # петля: прогон «вхолостую», чтобы IK к кадру 0 пришёл с ветви конца петли
            raw = a.sample

            def sample(fn, dt=0.05, t0=0.0, t1=None, raw=raw):
                for _ in range(2):
                    n = max(1, int(round(length / dt)))
                    for i in range(n + 1):
                        fn(length * i / n)
                return raw(fn, dt, t0, t1)
            a.sample = sample
        return a

    # ---------------------------------------------------------------- idle, swing, overhead, thrust, shield_bash — по эталону Epic Fight
    # (пилот 21.11, tools/gen_martin_ef.py; правила — docs/specs/anim_style_epicfight.md)
    import gen_martin_ef as EF
    EF.define(A, m, sys.modules[__name__], g, sf)

    # ---------------------------------------------------------------- walk: тяжёлый шаг, меч на плече, свободная рука качается
    def walk(t):
        ph = TAU * t / 1.6
        s = math.sin(ph)
        drop = abs(math.cos(ph)) ** 6
        o = {'body': {'pos': [0, -0.7 * drop + 0.2, 0], 'rot': [0, 4 * s, 0]}, 'torso': {'rot': [4 + 1.5 * drop, -3 * s, 1.5 * s]},
             'head': {'rot': [-3, 3 * s, 0]}, 'right_leg': {'rot': [-26 * s, 0, 0]}, 'left_leg': {'rot': [26 * s, 0, 0]},
             'left_arm': {'rot': [-22 * s, 0, -6]}, 'left_forearm': {'rot': [-14 - 8 * max(0, s), 0, 0]}}
        cape_follow(t, o, lag=5 + 3 * abs(s), period=0.8)
        g(o, np.add(SHOULDER[0], [0, -0.4 * drop, 0]), SHOULDER[1], left=0)
        return vis(o)
    a = A('walk', 1.6, True)
    a.sample(walk, 0.05)
    a.instruction(0.4, 'step')
    a.instruction(1.2, 'step')

    # ---------------------------------------------------------------- command: «в атаку!» — меч вверх-вперёд одной рукой, рёв (0.85)
    def command(t):
        k = float(track(t, [(0, 0), (0.6, 1, 'out'), (1.6, 1), (2.2, 0)]))
        p = float(track(t, [(0, 0), (0.6, 0), (0.85, 1, 'back'), (1.6, 1), (2.2, 0)]))
        o = {'torso': {'rot': [-6 * k, 16 * k, 0]}, 'head': {'rot': [-14 * p, -12 * k, 0]},
             'left_arm': {'rot': [-24 * k + 8 * p, 0, -42 * k + 10 * p]}, 'left_forearm': {'rot': [-34 * k, 0, 0]},
             'right_leg': {'rot': [-10 * k, 0, 0]}, 'left_leg': {'rot': [16 * k, 0, 0]}}
        cape_follow(t, o, lag=6 * p, wind=4 * p)
        up = (5.5, 31.0, -3.0)
        fw = (4.5, 27.0, -9.0)
        hand = np.asarray(GUARD[0]) * (1 - k) + (np.asarray(up) * (1 - p) + np.asarray(fw) * p) * k
        d = lerp_dir(GUARD[1], lerp_dir((0.1, 0.95, 0.2), (0.05, 0.35, -0.94), p), k)
        g(o, hand, d, left=max(0, 1 - 3 * k))
        return vis(o)
    a = A('command', 2.2)
    a.sample(command, 0.04)
    a.instruction(0.85, 'command')

    # ---------------------------------------------------------------- banner_plant: поднимает знамя левой рукой и вонзает (plant 1.3)
    def plant(t):
        k = float(track(t, [(0, 0), (0.7, 1, 'out'), (1.15, 1), (1.3, -0.4, 'in'), (1.8, -0.4), (2.4, 0)]))
        dn = max(0, -k) * 2.5
        o = {'body': {'pos': [0, -1.5 * dn, 0]}, 'torso': {'rot': [-10 * max(0, k) + 16 * dn, -14 * k, 0]},
             'left_arm': {'rot': [-150 * max(0, k) - 50 * dn, 0, -10 * max(0, k)]},
             'left_forearm': {'rot': [-10 * max(0, k), 0, 0]}, 'banner_held': {'rot': [90 * dn, 0, 0]},
             'head': {'rot': [16 * max(0, k) - 10 * dn, 0, 0]},
             'right_leg': {'rot': [-24 * dn, 0, 0]}, 'left_leg': {'rot': [20 * dn, 0, 0]}}
        cape_follow(t, o, lag=10 * dn)
        g(o, SHOULDER[0], SHOULDER[1], left=0)
        return vis(o, banner=t < 1.3)
    a = A('banner_plant', 2.4)
    a.sample(plant, 0.04)
    a.instruction(0.7, 'raise')
    a.instruction(1.3, 'plant')

    # ---------------------------------------------------------------- особое 1: «Атака конницы» — меч к небу (call 1.0), взмах вперёд (charge 2.0)
    def cavalry(t):
        k = float(track(t, [(0, 0), (0.8, 1, 'out'), (1.7, 1), (2.0, 2, 'in'), (2.8, 2), (3.4, 3)]))
        P = [GUARD[0], (5.0, 33.0, -1.0), (4.0, 21.0, -11.0), (4.0, 21.0, -11.0), GUARD[0]]
        D = [GUARD[1], (0.05, 1.0, 0.05), (0.0, -0.15, -0.99), (0.0, -0.15, -0.99), GUARD[1]]
        i = min(3, int(k))
        f = k - i
        up = (2 - k) if 1 <= k < 2 else (k if k < 1 else 0)          # без разрывов (правка 20.11: были скачки на 2.0 и 3.4)
        fw = (3 - k) if k >= 2 else (k - 1 if k >= 1 else 0)
        o = {'body': {'pos': [0, -1.2 * fw, -1.4 * fw]}, 'torso': {'rot': [-12 * up + 14 * fw, 0, 0]},
             'head': {'rot': [26 * up * (1 - fw) - 6 * fw, 0, 0]},
             'left_arm': {'rot': [-10 * up, 0, -36 * up]}, 'left_forearm': {'rot': [-20, 0, 0]},
             'right_leg': {'rot': [-26 * fw, 0, 0]}, 'left_leg': {'rot': [24 * fw, 0, 0]}}
        cape_follow(t, o, lag=12 * fw, wind=6 * up)
        g(o, np.asarray(P[i]) * (1 - f) + np.asarray(P[i + 1]) * f + AROUND_HEAD * math.sin(math.pi * f) * (i == 0), lerp_dir(D[i], D[i + 1], f),
          left=max(0, 1 - k) if k < 1 else (k - 3 if k > 3 else 0))
        return vis(o)
    a = A('cavalry', 3.4)
    a.sample(cavalry, 0.04)
    a.instruction(1.0, 'call')
    a.instruction(2.0, 'charge')

    # ---------------------------------------------------------------- особое 2: «Приказ стоять насмерть» — щит в землю перед собой (wall 1.1)
    def hold_pose(k, br=0.0):
        return {'body': {'pos': [0, -2.4 * k + 0.1 * br, -0.6 * k]}, 'torso': {'rot': [12 * k + br, 0, 0]}, 'head': {'rot': [-10 * k - br, 0, 0]},
                'right_leg': {'rot': [-36 * k, 0, 6 * k]}, 'left_leg': {'rot': [24 * k, 0, -6 * k]}}

    HOLD_SW = ((5.0, 30.0, -2.0), (0.1, 0.9, -0.42))           # меч поднят над щитом, острие вперёд

    def hold(t):
        k = float(track(t, [(0, 0), (0.7, 0.4), (1.1, 1, 'in'), (2.5, 1)]))
        o = hold_pose(k)
        cape_follow(t, o, lag=8 * k)
        sf(o, (-0.8, 12.6, -6.4), tilt=8, w=min(1, t / 0.5))
        g(o, np.asarray(GUARD[0]) * (1 - k) + np.asarray(HOLD_SW[0]) * k, lerp_dir(GUARD[1], HOLD_SW[1], k), left=0)
        return vis(o, shield_hand=t > 0.15)
    a = A('hold_the_line', 2.5, 'hold')
    a.sample(hold, 0.04)
    a.instruction(0.15, 'shield_draw')
    a.instruction(1.1, 'wall')

    def hold_loop(t):
        br = math.sin(TAU * t / 2.0)
        o = hold_pose(1.0, br)
        cape_follow(t, o, lag=8, period=2.0)
        sf(o, (-0.8, 12.6, -6.4), tilt=8)
        g(o, np.add(HOLD_SW[0], [0, 0.2 * br, 0]), HOLD_SW[1], left=0)
        return vis(o, shield_hand=True)
    A('hold_loop', 2.0, True).sample(hold_loop, 0.1)

    def hold_end(t):
        k = float(track(t, [(0, 1), (0.8, 0)]))
        o = hold_pose(k)
        cape_follow(t, o, lag=8 * k)
        sf(o, (-0.8, 12.6, -6.4), tilt=8, w=k)
        g(o, np.asarray(GUARD[0]) * (1 - k) + np.asarray(HOLD_SW[0]) * k, lerp_dir(GUARD[1], HOLD_SW[1], k), left=0)
        return vis(o, shield_hand=t < 0.7)
    A('hold_end', 0.8).sample(hold_end, 0.04)

    # ---------------------------------------------------------------- переходы фаз
    def phase2(t):
        # 66%: вонзает меч в землю перед собой (plant 0.6), руки на навершии, выпрямляется и ревёт (roar 1.4) — сигнал «Знамени»
        k = float(track(t, [(0, 0), (0.6, 1, 'in'), (2.4, 1), (3.0, 0)]))
        r = float(track(t, [(0, 0), (1.2, 0), (1.5, 1, 'back'), (2.4, 1), (3.0, 0)]))
        o = {'torso': {'rot': [6 * k - 8 * r, 0, 0]}, 'head': {'rot': [-26 * r, 0, 0]}}
        cape_follow(t, o, wind=6 * r)
        g(o, np.asarray(GUARD[0]) * (1 - k) + np.asarray(LEAN[0]) * k, lerp_dir(GUARD[1], LEAN[1], k))
        return vis(o)
    a = A('phase2', 3.0)
    a.sample(phase2, 0.04)
    a.instruction(0.6, 'plant')
    a.instruction(1.4, 'roar')

    def phase3(t):
        # 33%: «Последний полководец» — солдаты исчезают; присед (kneel 0.8), рывком выдёргивает меч, оборот (spin 1.4),
        # меч над головой (roar 2.0), верхняя стойка
        k = float(track(t, [(0, 0), (0.8, 1), (1.4, 1), (1.9, 2, 'out'), (2.6, 2), (3.2, 3)]))
        P = [GUARD[0], LEAN[0], (2.0, 32.0, -1.0), GUARD[0]]
        D = [GUARD[1], LEAN[1], (0.1, 0.95, 0.3), GUARD[1]]
        i = min(2, int(k))
        f = k - i
        sq = float(track(t, [(0, 0), (0.8, 1), (1.4, 0.4), (1.9, 0)]))
        o = {'body': {'pos': [0, -2.6 * sq, 0], 'rot': [0, 360 * ease(min(1, max(0, (t - 1.4) / 0.5))), 0]},
             'torso': {'rot': [16 * sq - 8 * (1 if 2 <= k < 2.6 else 0), 0, 0]}, 'head': {'rot': [-20 * (1 if 1.9 <= k < 2.8 else 0), 0, 0]},
             'right_leg': {'rot': [-30 * sq, 0, 0]}, 'left_leg': {'rot': [30 * sq, 0, 0]}}
        cape_follow(t, o, wind=10 * (1 if k >= 1.9 else 0))
        g(o, np.asarray(P[i]) * (1 - f) + np.asarray(P[i + 1]) * f + AROUND_HEAD * math.sin(math.pi * f) * (i == 1), lerp_dir(D[i], D[i + 1], f))
        return vis(o)
    a = A('phase3', 3.2)
    a.sample(phase3, 0.04)
    a.instruction(0.8, 'kneel')
    a.instruction(1.4, 'spin')
    a.instruction(2.0, 'roar')

    # ---------------------------------------------------------------- появление: на колене, руки на мече (воткнут), встаёт, салют, стойка
    def spawn(t):
        kneel = float(track(t, [(0, 1), (2.6, 1), (3.6, 0, 'io')]))
        lift = float(track(t, [(0, 0), (1.0, 0), (2.4, 1, 'out')]))
        k = float(track(t, [(0, 0), (3.6, 0), (4.4, 1, 'out'), (5.0, 2, 'out'), (5.8, 2), (6.5, 3)]))
        SAL = ((0.5, 26.0, -5.5), (0.0, 1.0, -0.05))                      # салют: клинок вертикально перед лицом
        P = [LEAN[0], GUARD[0], SAL[0], GUARD[0]]
        D = [LEAN[1], GUARD[1], SAL[1], GUARD[1]]
        i = min(2, int(k))
        f = k - i
        o = {'body': {'pos': [0, -6.2 * kneel, 0]}, 'torso': {'rot': [12 * kneel, 0, 0]},
             'head': {'rot': [26 * kneel * (1 - lift) - 4 * lift * kneel, 0, 0]},
             'right_leg': {'rot': [-86 * kneel, 0, 6 * kneel]}, 'left_leg': {'rot': [86 * kneel, 0, 0]}}
        cape_follow(t, o, sway=0.6)
        hand = np.asarray(P[i]) * (1 - f) + np.asarray(P[i + 1]) * f
        if k < 1:
            hand = hand + np.array([0, 6.2 * kneel - 1.2 * kneel, 0])    # меч стоит на земле, пока он на колене
        g(o, hand, lerp_dir(D[i], D[i + 1], f), left=1.0 if k < 2 or k > 2.6 else 0.0)
        return vis(o)
    a = A('spawn', 6.5)
    a.sample(spawn, 0.04)
    a.instruction(1.0, 'look')
    a.instruction(2.6, 'rise')
    a.instruction(4.0, 'pull')
    a.instruction(5.0, 'salute')

    # ---------------------------------------------------------------- блок-сдача: щит вверх (block 0.2), отдача, опускает оружие (lower 1.2), говорит (speak 2.4)
    def yield_(t):
        b = float(track(t, [(0, 0), (0.15, 1, 'out'), (0.9, 1), (2.0, 0, 'io')]))
        rec = float(track(t, [(0, 0), (0.2, 0), (0.3, 1, 'out'), (0.7, 0)]))
        low = float(track(t, [(0, 0), (1.2, 0), (2.6, 1, 'io')]))
        o = {'body': {'pos': [0, -1.2 * b, 1.6 * rec]}, 'torso': {'rot': [8 * b - 10 * rec + 4 * low, -18 * b, 0]},
             'head': {'rot': [-6 * b + 14 * low, 0, 0]},
             'right_leg': {'rot': [-14 * b, 0, 0]}, 'left_leg': {'rot': [16 * b, 0, 0]}}
        cape_follow(t, o, lag=6 * rec)
        DOWN = ((4.0, 13.5, -4.0), (0.12, -0.55, -0.83))                   # опущенный меч, острие к земле
        if b > 0.01:
            sf(o, (-1.2, 17.5 - 1.0 * rec, -6.0), tilt=-10 + 8 * rec, yaw=-10, w=b)
        g(o, np.asarray(GUARD[0]) * (1 - low) + np.asarray(DOWN[0]) * low, lerp_dir(GUARD[1], DOWN[1], low), left=0)
        return vis(o, shield_hand=t < 2.1)
    a = A('block_yield', 3.2, 'hold')
    a.sample(yield_, 0.04)
    a.instruction(0.2, 'block')
    a.instruction(1.2, 'lower')
    a.instruction(2.4, 'speak')

    # ---------------------------------------------------------------- мирный NPC: стоит, опираясь на меч (меч остриём в землю, руки на рукояти)
    def npc(t):
        br = math.sin(TAU * t / 4.0)
        o = {'body': {'pos': [0, 0.1 * br, 0]}, 'torso': {'rot': [5 + 0.8 * br, 0, 0]}, 'head': {'rot': [3 - 0.6 * br, 0, 0]},
             'right_leg': {'rot': [-2, 8, 2]}, 'left_leg': {'rot': [2, -8, -2]}}
        cape_follow(t, o, sway=0.7, period=4.0)
        g(o, LEAN[0], LEAN[1])
        return vis(o)
    A('npc_idle', 4.0, True).sample(npc, 0.1)

    def to_npc(t):  # из конца block_yield в позу NPC
        k = float(track(t, [(0, 0), (1.2, 1)]))
        o = {'torso': {'rot': [4 + k, 0, 0]}, 'head': {'rot': [14 - 11 * k, 0, 0]}}
        cape_follow(t, o, sway=0.7)
        DOWN = ((4.0, 13.5, -4.0), (0.12, -0.55, -0.83))
        g(o, np.asarray(DOWN[0]) * (1 - k) + np.asarray(LEAN[0]) * k, lerp_dir(DOWN[1], LEAN[1], k), left=k)
        return vis(o)
    A('to_npc', 1.2, 'hold').sample(to_npc, 0.04)

    # ================================================================ +4 заклинания (владелец 20.11)
    def shieldwall(t):
        # «Стена щитов»: щит со спины — вверх и с размаху в землю (slam 1.0), меч поднят; затем стойка
        up = float(track(t, [(0, 0), (0.6, 1, 'out'), (0.85, 1), (1.0, 0, 'in'), (1.6, 0), (2.0, -1)]))
        k = float(track(t, [(0, 0), (0.3, 1), (1.6, 1), (2.0, 0)]))
        dn = float(track(t, [(0, 0), (0.85, 0), (1.0, 1, 'in'), (1.6, 1), (2.0, 0)]))
        o = {'body': {'pos': [0, -2.4 * dn, -0.6 * dn]}, 'torso': {'rot': [-8 * max(0, up) + 14 * dn, 0, 0]}, 'head': {'rot': [-8 * dn, 0, 0]},
             'right_leg': {'rot': [-30 * dn, 0, 4]}, 'left_leg': {'rot': [22 * dn, 0, -4]}}
        cape_follow(t, o, lag=8 * dn)
        hand = np.array([-1.5, 22.0, -5.5]) * max(0, up) + np.array([-0.8, 12.6, -6.4]) * (1 - max(0, up))
        if k > 0.01:
            sf(o, hand, tilt=-16 * max(0, up) + 8 * (1 - max(0, up)), w=k)
        g(o, np.asarray(GUARD[0]) * (1 - k) + np.array([5.0, 30.0, -2.0]) * k, lerp_dir(GUARD[1], (0.1, 0.9, -0.42), k), left=0)
        return vis(o, shield_hand=0.15 < t < 1.9)
    a = A('shield_wall', 2.0)
    a.sample(shieldwall, 0.04)
    a.instruction(0.15, 'shield_draw')
    a.instruction(1.0, 'slam')

    def volley(t):
        # «Залп лучников»: меч к небу — «натянуть!» (draw 0.8), резкий взмах вперёд-вниз — «пли!» (loose 1.2)
        k = float(track(t, [(0, 0), (0.8, 1, 'out'), (1.05, 1), (1.2, 2, 'in'), (1.7, 2), (2.2, 3)]))
        P = [GUARD[0], (5.0, 33.0, -1.0), (4.0, 19.0, -11.0), GUARD[0]]
        D = [GUARD[1], (0.0, 1.0, 0.1), (0.0, -0.35, -0.94), GUARD[1]]
        i = min(2, int(k))
        f = k - i
        up = max(0.0, 2 - k) if k >= 1 else k                       # без разрыва на 1.2 (правка 20.11)
        fw = float(track(t, [(0, 0), (1.05, 0), (1.2, 1, 'in'), (1.7, 1), (2.2, 0)]))
        o = {'body': {'pos': [0, -1.0 * fw, -1.0 * fw]}, 'torso': {'rot': [-10 * up + 12 * fw, 0, 0]}, 'head': {'rot': [22 * up - 6 * fw, 0, 0]},
             'left_arm': {'rot': [-30 * up, 0, -50 * up]}, 'left_forearm': {'rot': [-20, 0, 0]},
             'right_leg': {'rot': [-22 * fw, 0, 0]}, 'left_leg': {'rot': [20 * fw, 0, 0]}}
        cape_follow(t, o, lag=10 * fw, wind=4 * up)
        g(o, np.asarray(P[i]) * (1 - f) + np.asarray(P[i + 1]) * f + AROUND_HEAD * math.sin(math.pi * f) * (i == 0), lerp_dir(D[i], D[i + 1], f),
          left=max(0, 1 - 3 * k) if k < 2.5 else (k - 2.5) * 2)
        return vis(o)
    a = A('volley', 2.2)
    a.sample(volley, 0.04)
    a.instruction(0.8, 'draw')
    a.instruction(1.2, 'loose')

    def duel(t):
        # «Вызов на дуэль»: остриё меча на выбранного игрока одной рукой, левая — к груди (challenge 0.9), затем стойка
        k = float(track(t, [(0, 0), (0.7, 1, 'out'), (1.5, 1), (2.0, 0)]))
        p = float(track(t, [(0, 0), (0.7, 0), (0.9, 1, 'back'), (1.5, 1), (2.0, 0)]))
        o = {'torso': {'rot': [-4 * k, -20 * k, 0]}, 'head': {'rot': [-4 * k, 14 * k, 0]},
             'left_arm': {'rot': [-50 * k, 0, 30 * k]}, 'left_forearm': {'rot': [-80 * k, 0, 0]},
             'right_leg': {'rot': [-14 * p, 0, 0]}, 'left_leg': {'rot': [12 * p, 0, 0]}}
        cape_follow(t, o, lag=4 * p)
        g(o, np.asarray(GUARD[0]) * (1 - k) + np.array([6.0, 21.0, -10.5 - 1.5 * p]) * k, lerp_dir(GUARD[1], (0.0, 0.05, -1.0), k),
          left=max(0, 1 - 3 * k))
        return vis(o)
    a = A('duel', 2.0)
    a.sample(duel, 0.04)
    a.instruction(0.9, 'challenge')

    def warcry(t):
        # «Боевой клич»: вдох, корпус назад, руки в стороны, рёв (cry 0.6) — волна сбивает касты; затем стойка
        k = float(track(t, [(0, 0), (0.5, 1, 'out'), (1.3, 1), (1.8, 0)]))
        c = float(track(t, [(0, 0), (0.5, 0), (0.62, 1, 'back'), (1.3, 1), (1.8, 0)]))
        sh = math.sin(t * 60) * c * 0.6
        o = {'body': {'pos': [0, -1.0 * c, 0.6 * c]}, 'torso': {'rot': [-14 * c + 6 * (k - c), 0, sh]}, 'head': {'rot': [-30 * c, 0, sh * 2]},
             'left_arm': {'rot': [-20 * k, 0, -70 * k]}, 'left_forearm': {'rot': [-30 * k, 0, 0]},
             'right_leg': {'rot': [-12 * c, 0, 8 * c]}, 'left_leg': {'rot': [12 * c, 0, -8 * c]}}
        cape_follow(t, o, lag=-4 * c, wind=8 * c)
        g(o, np.asarray(GUARD[0]) * (1 - k) + np.array([9.5, 20.0, -2.0]) * k, lerp_dir(GUARD[1], (0.6, 0.6, -0.5), k), left=max(0, 1 - 3 * k))
        return vis(o)
    a = A('warcry', 1.8)
    a.sample(warcry, 0.04)
    a.instruction(0.6, 'cry')

    # ================================================================ добивание (владелец 20.11; ТЗ T29 «Добивание»)
    def finisher(t):
        # 0–0.4 выпад, пронзает жертву спереди (impale 0.4); 0.4–0.8 приподнимает на клинке (raise 0.8); 0.8–1.5 вскидывает над
        # головой, 1.5–1.7 держит; 1.7–2.0 бросает к ногам ударом вниз (throw 1.7, slam 2.0 — солдаты бьют щитами); kill 2.3; 2.5 стойка.
        # Клинок всё время направлен в грудь жертвы — её точка по MartinMath.finisherHold (код программиста T29).
        lunge = float(track(t, [(0, 0), (0.4, 1, 'in'), (0.8, 1), (1.5, 0.3), (1.7, 0.3), (2.0, 1, 'in'), (2.5, 0)]))
        lift = float(track(t, [(0, 0), (0.8, 0), (1.5, 1), (1.7, 1), (1.9, 0), (2.5, 0)]))
        thr = float(track(t, [(0, 0), (1.7, 0), (2.0, 1, 'in'), (2.2, 1), (2.5, 0)]))
        o = {'body': {'pos': [0, -1.6 * thr - 0.6 * lunge, -3.0 * lunge]},
             'torso': {'rot': [14 * lunge * (1 - lift) - 8 * lift + 16 * thr, 0, 0]},
             'head': {'rot': [-6 * lunge - 26 * lift + 10 * thr, 0, 0]},
             'right_leg': {'rot': [-30 * lunge, 0, 4]}, 'left_leg': {'rot': [26 * lunge, 0, -4]}}
        cape_follow(t, o, lag=10 * lunge + 6 * thr, wind=6 * lift)
        # кисть (оси торса) по участкам
        H = [(0.0, GUARD[0]), (0.4, (2.5, 14.0, -11.0)), (0.8, (2.5, 19.0, -9.5)), (1.5, (2.5, 30.0, -6.0)), (1.7, (2.5, 30.0, -6.0)),
             (2.0, (1.0, 13.0, -10.0)), (2.2, (1.0, 13.0, -10.0)), (2.5, GUARD[0])]
        hand = np.asarray(track(t, [(a, b, 'io') if i else (a, b) for i, (a, b) in enumerate(H)]), float)
        bb_in(o)
        Mt, ot = fk(m, o, 'torso')
        tick = t * 20
        fh = finisher_hold(tick)
        chest = np.array([0.0, (fh[1] + 1.2) * 8.0, -fh[0] * 8.0])        # мир модели: 1 бл. = 8 ед. (модель ×2)
        hw = Mt @ hand + ot
        aim = Mt.T @ unit(chest - hw)                                       # направление на грудь — в осях торса
        if t < 0.25:
            d = lerp_dir(GUARD[1], aim, ease(t / 0.25))
        elif t <= 1.7:
            d = aim
        elif t <= 2.0:
            d = lerp_dir(FIN_AIM17, (0.0, -0.5, -0.87), ease((t - 1.7) / 0.3, 'in'))
        elif t <= 2.2:
            d = unit((0.0, -0.5, -0.87))
        else:
            d = lerp_dir((0.0, -0.5, -0.87), GUARD[1], ease((t - 2.2) / 0.3))
        if abs(t - 1.7) < 0.021:
            FIN_AIM17[:] = list(aim)
        g(o, hand, d)
        return vis(o)
    FIN_AIM17 = [0.0, 0.95, 0.3]
    a = A('finisher', 2.5)
    a.sample(finisher, 0.04)
    a.instruction(0.4, 'impale')
    a.instruction(0.8, 'raise')
    a.instruction(1.7, 'throw')
    a.instruction(2.0, 'slam')
    a.instruction(2.3, 'kill')
    return an


def finisher_hold(tick):
    """Порт MartinMath.finisherHold (программист T29): {вперёд, бл.; высота ног над землёй, бл.} на тике добивания."""
    PIERCE, RAISE, RAISED, THROW, SLAM = 8, 16, 30, 34, 40
    e = lambda u: 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, u)))
    if tick <= RAISE:
        return 3.2, (0.0 if tick <= PIERCE else 1.6 * e((tick - PIERCE) / (RAISE - PIERCE)))
    if tick <= RAISED:
        k = e((tick - RAISE) / (RAISED - RAISE))
        return 3.2 - 2.6 * k, 1.6 + 3.2 * k
    if tick <= THROW:
        return 0.6, 4.8
    if tick <= SLAM:
        k = (tick - THROW) / (SLAM - THROW)
        return 0.6 + 1.6 * k, 4.8 * (1 - k * k)
    return 2.2, 0.0


def iron_anims():
    """Все анимации заклинаний Iron's (их зовёт логика AbstractSpellCastingMob) + ключи скрытия щита в руке и знамени."""
    src = jar_json(I + 'animations/casting_animations.json')['animations']
    out_ = {}
    for k, v in src.items():
        v = json.loads(json.dumps(v))
        bones = v.setdefault('bones', {})
        bones['shield_hand'] = {'scale': {'0': [0, 0, 0]}}
        bones['banner_held'] = {'scale': {'0': [0, 0, 0]}}
        # у Iron's нет предплечий и кости меча: без явных ключей GeckoLib оставит их в позе прошлой анимации Мартина
        # (согнутый локоть, повёрнутый меч) — задаём покой: рука прямая, меч как предмет Iron's в руке (правка 20.11)
        for b in ('right_forearm', 'left_forearm', 'sword'):
            bones.setdefault(b, {})['rotation'] = {'0': [0, 0, 0]}
        bones['shield_back'] = dict(bones.get('shield_back', {}), scale={'0': [1, 1, 1]})
        bones['sword'] = dict(bones['sword'], scale={'0': [1, 1, 1]})
        iron_cape(v)
        out_[k] = v
    return out_


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0                          # molang-выражения Iron's: для плаща считаем 0


def _chan_at(chan, t):
    if isinstance(chan, dict) and 'vector' in chan:
        chan = chan['vector']
    if isinstance(chan, list):
        return [_num(x) for x in chan]
    ks = sorted((float(k), (v.get('vector') if isinstance(v, dict) else v)) for k, v in chan.items())
    ks = [(k, [_num(x) for x in v]) for k, v in ks]
    if t <= ks[0][0]:
        return ks[0][1]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t <= t1:
            f = (t - t0) / max(1e-6, t1 - t0)
            return [a + (b - a) * f for a, b in zip(v0, v1)]
    return ks[-1][1]


def iron_cape(v):
    """Анимации Iron's не знают о плаще: по их ключам body/torso/ног считаем плащ, табарды и щит на спине тем же решателем
    (иначе на наклонах/приседаниях каста плащ висит «как приклеенный» к торсу и уходит в ноги)."""
    bones = v['bones']
    ts = {0.0}
    for b in ('body', 'torso', 'right_leg', 'left_leg'):
        for ch in ('rotation', 'position'):
            c = bones.get(b, {}).get(ch)
            if isinstance(c, dict) and 'vector' not in c:
                ts.update(float(k) for k in c)
    length = float(v.get('animation_length') or max(ts))
    ts = sorted(t for t in ts if t <= length + 1e-6)
    dense = []
    for a, b in zip(ts, ts[1:]):
        n = max(1, int((b - a) / 0.1))
        dense += [a + (b - a) * i / n for i in range(n)]
    dense.append(ts[-1])
    an = Anim('tmp', length, False)
    for t in dense:
        o = {}
        for b in ('body', 'torso', 'right_leg', 'left_leg'):
            r = bones.get(b, {}).get('rotation')
            if r is not None:
                x, y, z = _chan_at(r, t)
                o[b] = {'rot': [-x, -y, z]}
            if b == 'body' and bones.get(b, {}).get('position') is not None:
                x, y, z = _chan_at(bones[b]['position'], t)
                o.setdefault(b, {})['pos'] = [-x, y, z]
        o['_cape'] = dict(back=3.0, low=2.0, z=0.0, tab=0.0)
        solve_cape(o, True)
        for b in ('cape', 'cape_low', 'tabard_front', 'tabard_back', 'shield_back'):
            an.key(b, 'rot', t, o[b]['rot'])
    for b, j in an.to_json()['bones'].items():
        bones.setdefault(b, {})['rotation'] = j['rotation']


# ================================================================== 3D-предмет меча (models/item/martin_sword.json)
PAL = {
    'g0': '#3e2410', 'g1': '#6a4318', 'g2': '#9a6a26', 'g3': '#c8933a', 'g4': '#e5b95a', 'g5': '#f6d88a', 'g6': '#fff1c4',
    'd0': '#3a271a', 'd1': '#523726', 'k0': '#0c0c10', 'k1': '#22232b', 'k2': '#30313b',
}


def item_model():
    pal = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    cell = {k: (i % 16, i // 16) for i, k in enumerate(PAL)}
    for k, (x, y) in cell.items():
        pal.putpixel((x, y), hx(PAL[k]))
    pal.save(out('textures/item/martin_sword_3d.png'))
    S = 0.62                    # ед. меча → пиксели предмета (24 ед. → 15 пикс.; в руке босса/игрока дисплей ×2)
    els = []

    def face(c):
        u, v = cell[c]
        return {'uv': [u + .25, v + .25, u + .75, v + .75], 'texture': '#p'}

    for f, t, mat, kw in sword_parts():
        base = kw.get('base', 3)
        if mat == 'gold':
            cols = {'up': 'g%d' % min(6, base + 1), 'down': 'g%d' % max(0, base - 2), 'north': 'g%d' % base, 'south': 'g%d' % base,
                    'east': 'g%d' % max(0, base - 1), 'west': 'g%d' % min(6, base)}
        elif mat == 'grip':
            cols = {k: ('k1' if k in ('north', 'south') else 'k2' if k == 'up' else 'k0') for k in ('up', 'down', 'north', 'south', 'east', 'west')}
        else:   # клинок: плоскости — золото, а дол и кромки — отдельные бруски ниже
            cols = {'up': 'g6', 'down': 'g3', 'north': 'g4', 'south': 'g4', 'east': 'g5', 'west': 'g6'}
        els.append(_el(f, t, S, {k: face(v) for k, v in cols.items()}))
        if mat == 'blade' and kw.get('fuller', True):
            w = (t[0] - f[0])
            ff = np.array([-w * 0.22, f[1] + 0.3, f[2] - 0.05])
            tt = np.array([w * 0.22, t[1] - 0.4, t[2] + 0.05])
            els.append(_el(ff, tt, S, {k: face('d0' if k in ('north', 'south') else 'd1') for k in ('up', 'down', 'north', 'south', 'east', 'west')}))
            for sx in (-1, 1):
                e0 = np.array([sx * w / 2 - (0.25 if sx > 0 else 0), f[1], f[2] - 0.03])
                e1 = np.array([sx * w / 2 + (0 if sx > 0 else 0.25), t[1], t[2] + 0.03])
                els.append(_el(np.minimum(e0, e1), np.maximum(e0, e1), S, {k: face('g6') for k in ('up', 'down', 'north', 'south', 'east', 'west')}))
    T = {   # меч в руке: остриём вверх-вперёд, как двуручники Iron's (template_verylarge_sword), ×2 к модели
        'thirdperson_righthand': {'rotation': [0, -90, 0], 'translation': [0, 6.5, 1.5], 'scale': [1.6, 1.6, 1.6]},
        'thirdperson_lefthand': {'rotation': [0, 90, 0], 'translation': [0, 6.5, 1.5], 'scale': [1.6, 1.6, 1.6]},
        'firstperson_righthand': {'rotation': [0, -90, 25], 'translation': [1.13, 5.0, 1.13], 'scale': [1.0, 1.0, 1.0]},
        'firstperson_lefthand': {'rotation': [0, 90, -25], 'translation': [1.13, 5.0, 1.13], 'scale': [1.0, 1.0, 1.0]},
        'gui': {'rotation': [0, 0, -45], 'translation': [0, 0, 0], 'scale': [0.95, 0.95, 0.95]},
        'ground': {'rotation': [0, 0, 0], 'translation': [0, 2, 0], 'scale': [0.6, 0.6, 0.6]},
        'fixed': {'rotation': [0, 0, -45], 'scale': [0.95, 0.95, 0.95]},
        'head': {'rotation': [0, 0, 0], 'scale': [1.0, 1.0, 1.0]},
    }
    doc = {'comment': 'T29: двуручник Мартина (золотой узорный, по референсу docs/references/t29/martin_sword.jpg). Сгенерировано tools/gen_martin.py.',
           'gui_light': 'front', 'textures': {'p': 'pohsmp_core:item/martin_sword_3d', 'particle': 'pohsmp_core:item/martin_sword_3d'},
           'elements': els, 'display': T}
    write_json('models/item/martin_sword.json', doc)
    return doc


def _el(f, t, S, faces):
    o = np.array([8, 3.5, 8])                        # рукоять у центра предмета, клинок вверх
    a = o + np.asarray(f) * S
    b = o + np.asarray(t) * S
    r = lambda v: [round(float(x), 3) for x in v]
    return {'from': r(np.minimum(a, b)), 'to': r(np.maximum(a, b)), 'faces': faces}


# ================================================================== сборка
def build_all():
    m = build_martin()
    m.pack()
    m.paint()
    an = [smooth_cloth(a) for a in anims(m)]
    write_json('geo/entity/martin.geo.json', m.geo_json(), compact=True)
    m.image.save(out('textures/entity/martin/martin.png'), optimize=True)
    if m.glow is not None:
        m.glow.save(out('textures/entity/martin/martin_glowmask.png'), optimize=True)
    allan = iron_anims()
    allan.update({a.name: a.to_json() for a in an})
    import gen_replica_break as RB          # «Реплика»: martin_replica_break (+ fx/печати в main)
    RB.add_anims('martin', allan)
    write_json('animations/entity/martin.animation.json', {'format_version': '1.8.0', 'animations': allan}, compact=True)
    item_model()
    ncubes = sum(len(b.cubes) for b in m.bones.values())
    print('martin: bones %d cubes %d tex %s anims %s' % (len(m.bones), ncubes, m.tex_px, ', '.join(a.name for a in an)))
    return m, an


def main(args):
    m, an = build_all()
    import gen_martin_extra as X
    X.run(sys.modules[__name__], args)
    import gen_martin_fx as FX
    FX.run(sys.modules[__name__], args)
    import gen_martin_spells as SP
    SP.run(sys.modules[__name__], args)
    import gen_replica_break as RB
    RB.run_assets(('martin',))


if __name__ == '__main__':
    if '--model-only' in sys.argv:
        build_all()
    else:
        main(sys.argv[1:])
