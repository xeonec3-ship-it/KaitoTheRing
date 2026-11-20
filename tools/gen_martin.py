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
from nightmare_geo import Model, Anim, euler, write_json as _wj, TAU  # noqa: E402

ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
JAR = os.path.join(ROOT, 'libs', 'irons_spellbooks-1.20.1-3.16.1.jar')
I = 'assets/irons_spellbooks/'
WRITTEN = []
DENS = 2                 # пикселей на единицу модели (модель ×2 в мире → 1 тексель = 1/16 блока)


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
    i, j, pw, ph = _pix(ctx)
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
    i, j, pw, ph = _pix(ctx)
    lv = bevel(ctx, base=info(ctx, 'base', 3))
    if info(ctx, 'engr') and ctx.face in SIDE and pw > 3 and ph > 3:  # гравировка: шахматный завиток
        lv = lv + np.where(((i + j) % 4 == 0) & (i > 0) & (j > 0) & (i < pw - 1) & (j < ph - 1), -1, 0)
    rgb = tone(R_GOLD, lv)
    deco = info(ctx, 'deco')
    if deco and ctx.face == info(ctx, 'deco_face', 'north'):
        rgb = DECO[deco](ctx, i, j, pw, ph, rgb, lv)
    g = None
    return rgb, 1.0, g


def mat_red(ctx):
    i, j, pw, ph = _pix(ctx)
    lv = bevel(ctx, base=info(ctx, 'base', 3), left=0, right=0)
    if ctx.face in SIDE and info(ctx, 'folds', True):                 # складки ткани: вертикальные тени через 3 пикселя
        lv = lv + np.where(i % 4 == 3, -1, 0)
    rgb = tone(R_RED, lv)
    deco = info(ctx, 'deco')
    if deco and ctx.face == info(ctx, 'deco_face', 'north'):
        rgb = DECO[deco](ctx, i, j, pw, ph, rgb, lv)
    return rgb, 1.0, None


def mat_cape(ctx):
    """Чёрно-белый плащ: снаружи чёрный с белой каймой по краям и низу, изнутри — белая подкладка в тени."""
    i, j, pw, ph = _pix(ctx)
    lv = bevel(ctx, base=2, left=0, right=0, top=0)
    out_face = info(ctx, 'outer', 'south')
    inner = {'south': 'north', 'north': 'south', 'east': 'west', 'west': 'east'}[out_face]
    if ctx.face == out_face:
        lv = lv + np.where(i % 5 == 4, -1, 0) + np.where(i % 5 == 0, 1, 0) * 0     # складки
        rgb = tone(R_BLACK, lv)
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
    i, j, pw, ph = _pix(ctx)
    lv = bevel(ctx, base=2)
    if ctx.face in SIDE and info(ctx, 'stitch'):
        lv = lv + np.where((j == 1) & (i % 2 == 0), 1, 0)
    return tone(R_LEATHER, lv), 1.0, None


def mat_dark(ctx):
    return tone(R_DARK, bevel(ctx, base=1, top=0, bottom=0, right=0)), 1.0, None


def mat_grip(ctx):
    i, j, pw, ph = _pix(ctx)
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
        rgb = np.where((u < 1.2 / pw)[:, None] | (u > 1 - 1.2 / pw)[:, None], R_GOLD[6], R_GOLD[4])
        if info(ctx, 'fuller', True):
            dol = np.abs(u - 0.5) < (0.5 - 1.6 / pw) if pw >= 5 else np.zeros(ctx.n, bool)
            lv = np.where(j % 6 == 0, 2, 1)
            rgb = np.where(dol[:, None], tone(R_BLADE_DARK, lv - (np.abs(u - 0.5) > 0.12)), rgb)
        # отблеск — блик вдоль кромки
        rgb = np.where(((u < 1.2 / pw) & (j % 7 == 2))[:, None], np.ones(3), rgb)
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
        eye = (j == ph // 2) & (np.abs(i - pw * 0.5 + 0.5) < 0.6)
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
    m.box('torso', (-3.5, 16.6, -3.1), (3.5, 24, 2.9), 'steel', deco='chest', lames=0)       # кираса
    m.box('torso', (-0.55, 16.4, -3.55), (0.55, 23.4, -3.0), 'steel', base=4)               # рёберный кант
    m.box('torso', (-2.8, 13.4, -3.0), (2.8, 16.8, 2.8), 'steel', lames=4, base=3)           # пластины живота (плакарт)
    m.box('torso', (-4.4, 17.0, 2.4), (4.4, 23.6, 3.1), 'steel', base=3)                    # спинная пластина
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
    m.box('head', (-4.1, 24.2, -4.1), (4.1, 31.6, 4.1), 'steel', lames=0, base=3)
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
        m.box(arm, (x0, 17.0, -1.75), (x1, 20.6, 1.75), 'steel', base=3)                  # наплечник руки (ребрасс)
        # наплечник: три ламы + шипы
        x0, x1 = xs(-2.2, 3.0)
        m.box(arm, (x0, 21.0, -3.0), (x1, 24.2, 3.0), 'steel', trim='b', base=4)
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
        m.box(fore, (X - 1.75, 12.8, -1.75), (X + 1.75, 15.4, 1.75), 'steel', base=3)        # наруч
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
        m.box(leg, (X - 2.2, 7.2, -2.3), (X + 2.2, 11.4, 2.0), 'steel', base=3, trim='b')              # набедренник
        m.box(leg, (X - 1.8, 5.2, -2.9), (X + 1.8, 7.8, -1.6), 'steel', base=4, trim='b')    # наколенник
        m.box(leg, (X - 1.2, 5.8, -3.25), (X + 1.2, 7.2, -2.9), 'steel', base=5)
        m.box(leg, (X - 2.0, 1.6, -2.1), (X + 2.0, 6.6, 2.0), 'steel', lames=0, base=3)       # поножи
        m.box(leg, (X - 0.4, 1.8, -2.4), (X + 0.4, 6.0, -2.1), 'steel', base=4)              # ребро поножей
        m.box(leg, (X - 2.2, 0.0, -3.6), (X + 2.2, 1.8, 2.2), 'steel', lames=0, base=3, trim='t')  # сабатон
        m.box(leg, (X - 1.6, 0.0, -4.4), (X + 1.6, 1.2, -3.6), 'steel', base=4)
    # ---------------------------------------------------------------- меч, щит (на спине и в руке), знамя в руке (для установки знамени)
    add_sword(m, 'sword', 'right_forearm', (5.6, 10.6, -0.2))
    add_shield(m, 'shield_back', 'torso', (0, 17, 4.6), (0, 15.0, 5.0), face='south')
    add_shield(m, 'shield_hand', 'left_forearm', (-5.6, 14.0, 0), (-5.6, 12.5, -3.2), face='north')
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
    return world_pt(m, pose, 'sword', piv + [0, y - GRIP_R, 0])


HAND = {'left': np.array([-5.6, 10.6, -0.2]), 'right': np.array([5.6, 10.6, -0.2])}


def solve_arm(m, pose, side, target, init=None, iters=300):
    """Повороты <side>_arm (x, y, z) и <side>_forearm (x), чтобы кисть легла в target (покоординатный спуск)."""
    x = np.array(init if init is not None else [-60.0, 0.0, 0.0, -20.0], float)
    arm, fore = side + '_arm', side + '_forearm'

    def err(v):
        p = dict(pose)
        p[arm] = dict(pose.get(arm, {}), rot=[v[0], v[1], v[2]])
        p[fore] = {'rot': [v[3], 0, 0]}
        e = world_pt(m, p, fore, HAND[side]) - target
        pen = 0.002 * (max(0, v[3]) ** 2 + max(0, -v[3] - 125) ** 2) + 0.0004 * (v[1] ** 2 + v[2] ** 2) * 0.05
        return float(e @ e) + pen
    step = 16.0
    best = err(x)
    for _ in range(iters):
        improved = False
        for k in range(4):
            for d in (step, -step):
                y = x.copy()
                y[k] += d
                e = err(y)
                if e < best:
                    best, x, improved = e, y, True
        if not improved:
            step *= 0.6
            if step < 0.05:
                break
    return x, math.sqrt(max(0, best))


def solve_left(m, pose, target, init=None, iters=300):
    return solve_arm(m, pose, 'left', target, init, iters)


# ================================================================== анимации
def ease(k, kind='io'):
    k = min(1.0, max(0.0, k))
    if kind == 'in':
        return k * k * k
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


def cape_follow(t, o, base=4.0, sway=1.0, lag=0.0, period=3.0, wind=0.0):
    """Плащ: лёгкое колыхание + отставание от движения корпуса (lag: + назад, градусы)."""
    s = math.sin(TAU * t / period)
    o['cape'] = {'rot': [base + lag + wind + 1.5 * sway * s, 0, 0.8 * sway * math.sin(TAU * t / period * 0.5)]}
    o['cape_low'] = {'rot': [2.0 + lag * 0.6 + 2.0 * sway * math.sin(TAU * t / period - 0.8), 0, 0]}
    o['tabard_front'] = {'rot': [-1.5 * sway * s - lag * 0.25, 0, 0]}
    o['tabard_back'] = {'rot': [1.5 * sway * s + lag * 0.3, 0, 0]}
    return o


def vis(o, shield_hand=False, banner=False):
    o['shield_hand'] = dict(o.get('shield_hand', {}), scale=SHOW if shield_hand else HIDE)
    o['shield_back'] = dict(o.get('shield_back', {}), scale=HIDE if shield_hand else SHOW)
    o['banner_held'] = dict(o.get('banner_held', {}), scale=SHOW if banner else HIDE)
    return o


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


class Grip:
    """Хват меча: кисть правой руки — в точку hand (координаты торса в покое), клинок — по направлению d (тоже в осях торса),
    левая рука (по желанию, с весом w) — на рукоять. Решения переносятся между кадрами (плавно, без скачков)."""

    def __init__(self, m):
        self.m = m
        self.reset()

    def reset(self):
        self.pr, self.pl, self.c = None, None, None

    def __call__(self, o, hand, d, left=1.0, ly=GRIP_L):
        m = self.m
        Mt, ot = fk(m, o, 'torso')
        tgt = Mt @ np.asarray(hand, float) + ot
        sol, _ = solve_arm(m, o, 'right', tgt, self.pr)
        self.pr = sol
        o['right_arm'] = dict(o.get('right_arm', {}), rot=list(sol[:3]))
        o['right_forearm'] = {'rot': [sol[3], 0, 0]}
        Mf, _ = fk(m, o, 'right_forearm')
        v = Mf.T @ (Mt @ unit(d))
        a = math.degrees(math.asin(max(-1, min(1, v[2]))))
        c = math.degrees(math.atan2(-v[0], v[1]))
        if self.c is not None:
            c += 360 * round((self.c - c) / 360)
        self.c = c
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


def lerp_dir(a, b, k):
    return unit(np.asarray(a, float) * (1 - k) + np.asarray(b, float) * k)


# ключевые хваты (точки кисти и направления клинка в осях торса; торс в покое: плечи y 22, пояс y 12, перед −z)
GUARD = ((2.2, 14.6, -6.4), (-0.3, 0.72, -0.62))           # стойка: клинок вверх-вперёд, острие на противника
LEAN = ((0.3, 18.6, -7.6), (0.0, -0.99, -0.12))            # опирается: меч остриём в землю перед ним
SHOULDER = ((4.6, 18.0, -4.6), (0.18, 0.62, 0.76))         # на плече (ходьба): клинок назад через плечо


def anims(m):
    an = []
    g = Grip(m)

    def A(name, length, loop=False):
        a = Anim('martin_' + name, length, loop)
        an.append(a)
        g.reset()
        return a

    # ---------------------------------------------------------------- idle: двуручник в стойке, тяжёлое дыхание
    def idle(t):
        br = math.sin(TAU * t / 3.0)
        o = {'body': {'pos': [0, -0.3 + 0.15 * br, 0]}, 'torso': {'rot': [2 + 0.8 * br, 8, 0]}, 'head': {'rot': [-2 - 0.6 * br, -6, 0]},
             'right_leg': {'rot': [-8, 14, 3]}, 'left_leg': {'rot': [10, -10, -3]}}
        cape_follow(t, o)
        g(o, np.add(GUARD[0], [0, 0.25 * br, 0]), GUARD[1])
        return vis(o)
    A('idle', 3.0, True).sample(idle, 0.1)

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

    # ---------------------------------------------------------------- swing: горизонтальный размах справа налево (удар 0.75)
    def swing(t):
        k = float(track(t, [(0, 0), (0.55, 1), (0.75, 2, 'in'), (1.0, 2.4, 'out'), (1.6, 3)]))
        P = [GUARD[0], (7.0, 18.0, -1.0), (-2.5, 16.5, -8.0), (-6.0, 15.0, -3.0), GUARD[0]]
        D = [GUARD[1], (0.9, 0.3, 0.3), (-0.95, 0.12, -0.3), (-0.55, -0.1, 0.83), GUARD[1]]
        i = min(3, int(k))
        f = k - i
        hand = np.asarray(P[i]) * (1 - f) + np.asarray(P[i + 1]) * f
        d = lerp_dir(D[i], D[i + 1], f)
        tw = float(track(t, [(0, 0), (0.55, 1), (0.8, -1, 'in'), (1.0, -1.1), (1.6, 0)]))
        o = {'body': {'rot': [0, -30 * tw, 0], 'pos': [0, -0.6 * abs(tw), -1.2 * max(0, -tw)]}, 'torso': {'rot': [4, -20 * tw, -3 * tw]},
             'right_leg': {'rot': [10 * tw, 18 * tw, 0]}, 'left_leg': {'rot': [-12 * tw, 10 * tw, 0]}, 'head': {'rot': [0, 22 * tw, 0]}}
        cape_follow(t, o, lag=8 * abs(tw))
        g(o, hand, d)
        return vis(o)
    a = A('swing', 1.6)
    a.sample(swing, 0.04)
    a.instruction(0.62, 'swing')
    a.instruction(0.75, 'hit')

    # ---------------------------------------------------------------- overhead: рубящий сверху, клинок в землю (удар 0.95)
    def overhead(t):
        k = float(track(t, [(0, 0), (0.7, 1, 'out'), (0.95, 2, 'in'), (1.5, 2), (2.0, 3)]))
        P = [GUARD[0], (1.0, 31.0, 0.5), (0.5, 12.5, -9.0), (0.5, 12.5, -9.0), GUARD[0]]
        D = [GUARD[1], (0.0, 0.25, 0.97), (0.0, -0.5, -0.87), (0.0, -0.5, -0.87), GUARD[1]]
        i = min(3, int(k))
        f = k - i
        hand = np.asarray(P[i]) * (1 - f) + np.asarray(P[i + 1]) * f
        d = lerp_dir(D[i], D[i + 1], f)
        up = float(track(t, [(0, 0), (0.7, 1, 'out'), (0.95, -1, 'in'), (1.5, -1), (2.0, 0)]))
        dn = max(0, -up)
        o = {'body': {'pos': [0, -2.4 * dn, -1.6 * dn]}, 'torso': {'rot': [-10 * max(0, up) + 30 * dn, 0, 0]},
             'head': {'rot': [8 * max(0, up) - 20 * dn, 0, 0]},
             'right_leg': {'rot': [-34 * dn, 0, 4]}, 'left_leg': {'rot': [40 * dn, 0, -4]}}
        cape_follow(t, o, lag=-6 * max(0, up) + 14 * dn)
        g(o, hand, d)
        return vis(o)
    a = A('overhead', 2.0)
    a.sample(overhead, 0.04)
    a.instruction(0.82, 'swing')
    a.instruction(0.95, 'hit')

    # ---------------------------------------------------------------- thrust: выпад (удар 0.6), корпус уходит вперёд
    def thrust(t):
        k = float(track(t, [(0, 0), (0.4, 1), (0.6, 2, 'in'), (0.9, 2), (1.4, 3)]))
        P = [GUARD[0], (4.5, 16.0, 1.5), (1.0, 17.0, -11.0), (1.0, 17.0, -11.0), GUARD[0]]
        D = [GUARD[1], (-0.05, 0.08, -1.0), (0, 0.02, -1.0), (0, 0.02, -1.0), GUARD[1]]
        i = min(3, int(k))
        f = k - i
        hand = np.asarray(P[i]) * (1 - f) + np.asarray(P[i + 1]) * f
        d = lerp_dir(D[i], D[i + 1], f)
        l = float(track(t, [(0, 0), (0.4, -0.3), (0.6, 1, 'in'), (0.9, 1), (1.4, 0)]))
        o = {'body': {'pos': [0, -1.4 * max(0, l), -6 * max(0, l)]}, 'torso': {'rot': [12 * max(0, l), -24 * l, 0]},
             'right_leg': {'rot': [-42 * max(0, l), 0, 0]}, 'left_leg': {'rot': [36 * max(0, l), 0, 0]}, 'head': {'rot': [-8 * max(0, l), 20 * l, 0]}}
        cape_follow(t, o, lag=16 * max(0, l))
        g(o, hand, d)
        return vis(o)
    a = A('thrust', 1.4)
    a.sample(thrust, 0.04)
    a.instruction(0.6, 'hit')

    # ---------------------------------------------------------------- shield_bash: щит в руку, рывок (dash 0.45–0.75), удар 0.75
    def bash(t):
        k = float(track(t, [(0, 0), (0.35, 1), (1.15, 1), (1.5, 0)]))
        d = float(track(t, [(0, 0), (0.45, 0), (0.75, 1, 'in'), (0.85, 1.1), (1.5, 0)]))
        o = {'body': {'pos': [0, -1.0 * k, -2 * d], 'rot': [0, 20 * k, 0]}, 'torso': {'rot': [16 * k, 12 * k, 0]},
             'left_arm': {'rot': [-72 * k, -24 * k, 0]}, 'left_forearm': {'rot': [-14 * k, 0, 0]}, 'shield_hand': {'rot': [0, 54 * k, 0]},
             'right_leg': {'rot': [-30 * d, 0, 0]}, 'left_leg': {'rot': [30 * d, 0, 0]}, 'head': {'rot': [-8 * k, -18 * k, 0]}}
        cape_follow(t, o, lag=18 * d)
        g(o, np.asarray(GUARD[0]) * (1 - k) + np.array([6.5, 14.0, 2.0]) * k, lerp_dir(GUARD[1], (0.35, 0.3, 0.88), k), left=0)
        return vis(o, shield_hand=0.12 < t < 1.4)
    a = A('shield_bash', 1.5)
    a.sample(bash, 0.04)
    a.instruction(0.12, 'shield_draw')
    a.instruction(0.45, 'dash')
    a.instruction(0.75, 'hit')

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
        up = 1.0 if 1 <= k < 2 else (k if k < 1 else 0)
        fw = 1.0 if 2 <= k < 3 else (k - 1 if 1 <= k < 2 else (3 - k if k >= 3 else 0))
        o = {'body': {'pos': [0, -1.2 * fw, -1.4 * fw]}, 'torso': {'rot': [-12 * up + 14 * fw, 0, 0]},
             'head': {'rot': [26 * up * (1 - fw) - 6 * fw, 0, 0]},
             'left_arm': {'rot': [-10 * up, 0, -36 * up]}, 'left_forearm': {'rot': [-20, 0, 0]},
             'right_leg': {'rot': [-26 * fw, 0, 0]}, 'left_leg': {'rot': [24 * fw, 0, 0]}}
        cape_follow(t, o, lag=12 * fw, wind=6 * up)
        g(o, np.asarray(P[i]) * (1 - f) + np.asarray(P[i + 1]) * f, lerp_dir(D[i], D[i + 1], f), left=max(0, 1 - k) if k < 1 else (k - 3 if k > 3 else 0))
        return vis(o)
    a = A('cavalry', 3.4)
    a.sample(cavalry, 0.04)
    a.instruction(1.0, 'call')
    a.instruction(2.0, 'charge')

    # ---------------------------------------------------------------- особое 2: «Приказ стоять насмерть» — щит в землю перед собой (wall 1.1)
    def hold_pose(k, br=0.0):
        return {'body': {'pos': [0, -2.4 * k + 0.1 * br, -0.6 * k]}, 'torso': {'rot': [12 * k + br, 0, 0]}, 'head': {'rot': [-10 * k - br, 0, 0]},
                'left_arm': {'rot': [-44 * k, -14 * k, 4 * k]}, 'left_forearm': {'rot': [-30 * k, 0, 0]}, 'shield_hand': {'rot': [34 * k, 28 * k, 4 * k]},
                'right_leg': {'rot': [-36 * k, 0, 6 * k]}, 'left_leg': {'rot': [24 * k, 0, -6 * k]}}

    HOLD_SW = ((5.0, 30.0, -2.0), (0.1, 0.9, -0.42))           # меч поднят над щитом, острие вперёд

    def hold(t):
        k = float(track(t, [(0, 0), (0.7, 0.4), (1.1, 1, 'in'), (2.5, 1)]))
        o = hold_pose(k)
        cape_follow(t, o, lag=8 * k)
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
        g(o, np.add(HOLD_SW[0], [0, 0.2 * br, 0]), HOLD_SW[1], left=0)
        return vis(o, shield_hand=True)
    A('hold_loop', 2.0, True).sample(hold_loop, 0.1)

    def hold_end(t):
        k = float(track(t, [(0, 1), (0.8, 0)]))
        o = hold_pose(k)
        cape_follow(t, o, lag=8 * k)
        g(o, np.asarray(GUARD[0]) * (1 - k) + np.asarray(HOLD_SW[0]) * k, lerp_dir(GUARD[1], HOLD_SW[1], k), left=1 - k)
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
        g(o, np.asarray(P[i]) * (1 - f) + np.asarray(P[i + 1]) * f, lerp_dir(D[i], D[i + 1], f))
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
             'left_arm': {'rot': [-80 * b + 10 * rec, -30 * b, 0]}, 'left_forearm': {'rot': [-20 * b, 0, 0]},
             'shield_hand': {'rot': [0, 60 * b, 0]}, 'right_leg': {'rot': [-14 * b, 0, 0]}, 'left_leg': {'rot': [16 * b, 0, 0]}}
        cape_follow(t, o, lag=6 * rec)
        DOWN = ((4.0, 13.5, -4.0), (0.12, -0.55, -0.83))                   # опущенный меч, острие к земле
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
    return an


def iron_anims():
    """Все анимации заклинаний Iron's (их зовёт логика AbstractSpellCastingMob) + ключи скрытия щита в руке и знамени."""
    src = jar_json(I + 'animations/casting_animations.json')['animations']
    out_ = {}
    for k, v in src.items():
        v = json.loads(json.dumps(v))
        bones = v.setdefault('bones', {})
        bones['shield_hand'] = {'scale': {'0': [0, 0, 0]}}
        bones['banner_held'] = {'scale': {'0': [0, 0, 0]}}
        out_[k] = v
    return out_


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
    an = anims(m)
    write_json('geo/entity/martin.geo.json', m.geo_json(), compact=True)
    m.image.save(out('textures/entity/martin/martin.png'), optimize=True)
    if m.glow is not None:
        m.glow.save(out('textures/entity/martin/martin_glowmask.png'), optimize=True)
    allan = iron_anims()
    allan.update({a.name: a.to_json() for a in an})
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


if __name__ == '__main__':
    if '--model-only' in sys.argv:
        build_all()
    else:
        main(sys.argv[1:])
