#!/usr/bin/env python3
"""
Одежда безмолвной ведьмы (T19) по артам «Секретов безмолвной ведьмы» и в стиле объёмной Minecraft-косметики (примеры сценариста):
почти чёрное платье-мантия; юбка и задний клин собраны из вертикальных полос-складок разной длины и глубины (рваный подол),
по низу — ровные сплошные полосы на одной высоте: серо-зелёная, тёмно-серая и широкая горчично-золотая, под подолом бордовая оборка;
пелерина в два слоя с выступающей каймой (золото с тёмным зигзагом), полы пелерины спереди расходятся; выпуклый золотой узор
по переду; рукава-колокола с бордовой изнанкой; капюшон с толстым подвёрнутым краем и бордовым нутром; зелёная ленточка;
кот Неро (на плече / на капюшоне).

Текстура — пиксельная, 1 пиксель текстуры на 1 пиксель модели: у каждой грани каждого бруска своя развёртка в атласе
(раскладка полками), цвет считается по мировым координатам грани (складки по x/z, полосы — от низа своей складки),
тон ступеньками, светлая кромка сверху, тёмная снизу. Это и даёт объём, как у примеров.

GeckoLib-броня: кости armorHead / armorBody / armorRightArm / armorLeftArm / armorRightLeg / armorLeftLeg. ВАЖНО для кода: юбка сидит
на костях ног, рендер брони ведьмы поворачивает bipedRightLeg / bipedLeftLeg только на 25 % от поворота ноги игрока (переопределить
applyBaseTransformations), иначе платье на шаге разъезжается; и пока надета юбка (поножи ведьмы),
сам игрок шагает вдвое мельче (поворот его ног ×0.5) — иначе нога на шаге выходит из-под платья. Колышутся: cape (пелерина), cape_low (задний клин), hood_tip, hem_r / hem_l
(нижний ярус юбки); кот — две копии: nero* на плече и nero_hood* на капюшоне, свой контроллер анимаций.

Выход (assets/pohsmp_core): geo/armor/silent_witch_armor.geo.json, animations/armor/silent_witch_armor.animation.json,
textures/armor/silent_witch_armor.png (+ _glowmask.png — глаза кота и выпуклое золото узора слегка светятся ночью).
Анимации ткани: idle, walk, run, cast; кота: nero_shoulder, nero_jump_up, nero_head, nero_jump_down, nero_dragon, nero_return, nero_hidden.
Координаты — геометрия Bedrock/GeckoLib в пикселях (голова — куб от -4,24,-4 размером 8; +x — левая сторона, перед — -z).
Запуск: python3 tools/gen_silent_outfit.py
"""
import json
import math
import os
import random

from PIL import Image

NAME = 'silent_witch_armor'
HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
TW = TH = 256

# ---------------------------------------------------------------- палитра: рампы от тёмного к светлому (по артам)
RAMP = {
    'cloth': ['#17171F', '#22222C', '#2E2E3A', '#3C3C4B', '#4E4E60'],
    'lining': ['#3A0F1A', '#4E1624', '#621E2E', '#782838', '#8E3446'],
    'green': ['#4E5A54', '#64726A', '#7A8A80', '#93A398', '#AEBDB2'],
    'slate': ['#262A36', '#30353F', '#3C4250', '#4A5060', '#5A6172'],
    'gold': ['#6E5014', '#946E24', '#B8923A', '#D6B25A', '#F2DA8E'],
    'fur': ['#0E0D12', '#16141C', '#1E1B26', '#28242F', '#36313F'],
    'ribbon': ['#245A30', '#2E7440', '#3C8E50', '#52A866', '#72C284'],
    'eye': ['#8A6A08', '#C89A10', '#E2BE22', '#F2D23A', '#FFF2A0'],
    'nose': ['#B86A80', '#CC7C92', '#DC8EA4', '#E89AB0', '#F4B8C8'],
}
GLOW = {'eye', 'gold_raised'}


def hx(h):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))


RAMPC = {k: [hx(c) for c in v] for k, v in RAMP.items()}


def tone(ramp, k):
    """k — ступень 0..4 (дробная обрезается): пиксельные ступени, а не плавный градиент."""
    r = RAMPC[ramp]
    return r[max(0, min(len(r) - 1, int(k)))]


def h3(x, y, z):
    """Детерминированный «шум» по целым координатам."""
    n = (int(math.floor(x)) * 73856093) ^ (int(math.floor(y)) * 19349663) ^ (int(math.floor(z)) * 83492791)
    return ((n * 2654435761) & 0xFFFFFFFF) / 0xFFFFFFFF


# ---------------------------------------------------------------- материалы: цвет пикселя грани
# ctx: материал, мировая точка (x, y, z), нормаль n, локальная v (0 сверху грани .. 1 снизу), высота грани в пикселях,
# низ бруска (yb), параметры полос (bands) для подола.
def shade_cloth(ramp, x, y, z, n, v, H, base=2.0, folds=True):
    k = base
    if folds and n[1] == 0:
        u = x if n[0] == 0 else z                                    # складки идут поперёк грани
        k += 1.15 * math.sin(u * 1.1 + 0.7 * math.sin(u * 0.45)) - 0.1
    k += (h3(x * 1.0, y * 1.0, z * 1.0) - 0.5) * 0.7                 # пиксельное зерно
    if n[1] > 0:
        k += 1.0                                                     # верх — светлее
    elif n[1] < 0:
        k -= 1.2                                                     # низ — темнее
    else:
        if v * H < 1:
            k += 1.0                                                 # светлая кромка сверху
        if (1 - v) * H < 1:
            k -= 1.0                                                 # тёмная кромка снизу
    return tone(ramp, k)


def paint_px(mat, x, y, z, n, v, H, yb, cube):
    if mat in ('cloth', 'hood'):
        k_base = 2.2 - 0.5 * v if n[1] == 0 else 2.0
        return shade_cloth('cloth', x, y, z, n, v, H, base=k_base)
    if mat == 'lining':
        return shade_cloth('lining', x, y, z, n, v, H, base=2.0)
    if mat == 'hood_in':
        return shade_cloth('lining', x, y, z, n, v, H, base=0.8 + 1.2 * v, folds=False)
    if mat in ('skirt', 'skirt_back'):
        # полосы на одной высоте по всей юбке (как на артах): золото снизу до 4.4, тёмная нить, тёмно-серая 4.7..5.7,
        # тёмная нить, серо-зелёная 6.0..7.0; внутри полос — только складки, без зерна, чтобы полоса читалась сплошной
        if n[1] == 0:
            def band(ramp, base):
                u = x if n[0] == 0 else z
                k = base + 0.8 * math.sin(u * 1.1 + 0.7 * math.sin(u * 0.45))
                if v * H < 1:
                    k += 0.8
                return tone(ramp, k)
            if y < 4.4:
                return band('gold', 2.3 if y > 1.6 else 1.6)
            if y < 4.7:
                return tone('cloth', 1)
            if y < 5.7:
                return band('slate', 2.0)
            if y < 6.0:
                return tone('cloth', 1)
            if y < 7.0:
                return band('green', 2.0)
        c = shade_cloth('cloth', x, y, z, n, v, H, base=2.0 - 0.4 * v)
        if n[1] == 0 and h3(x * 0.5, y * 0.33, z * 0.5) > 0.965:       # редкие золотые ромбики-искры
            return tone('gold', 3)
        return c
    if mat == 'capelet':
        hb = y - yb
        if n[1] == 0 and 0.9 <= hb < 1.8:
            return shade_cloth('green', x, y, z, n, v, H, base=1.8)   # серая полоса над каймой
        return shade_cloth('cloth', x, y, z, n, v, H, base=2.3)
    if mat == 'trim':
        # золотая лента с тёмным зигзагом: треугольники вниз по горизонтали
        if n[1] != 0:
            return tone('gold', 2)
        h = y - yb
        top = cube['size'][1]
        u = (x if n[0] == 0 else z)
        tri = abs((u % 3.0) / 1.5 - 1.0)                               # 0..1, треугольник шириной 3 пикселя
        if 0.25 * top < h < 0.75 * top and (h - 0.25 * top) / (0.5 * top) > tri:
            return tone('cloth', 1)
        k = 3 if v * H < 1 else 1 if (1 - v) * H < 1 else 2.4
        return tone('gold', k + (h3(x, y, z) - 0.5) * 0.6)
    if mat in ('gold', 'gold_raised'):
        k = 3.6 if (n[1] > 0 or v * H < 1) else 1.2 if (1 - v) * H < 1 or n[1] < 0 else 2.6
        return tone('gold', k + (h3(x, y, z) - 0.5) * 0.5)
    if mat == 'ribbon':
        return tone('ribbon', 3 if v < 0.4 else 2)
    if mat == 'fur':
        k = 2 + (h3(x, y, z) - 0.5) * 1.2 + (1 if n[1] > 0 else -0.8 if n[1] < 0 else 0)
        if n[1] == 0 and v * H < 1:
            k += 1.2                                                   # светлая кромка, чтобы чёрный кот читался
        return tone('fur', k)
    if mat == 'eye':
        return tone('eye', 4 if (v < 0.5 and h3(x * 3, y * 3, z) > 0.5) else 3)
    if mat == 'nose':
        return tone('nose', 3)
    return (255, 0, 255)


# ---------------------------------------------------------------- атлас: у каждой грани своя развёртка, раскладка полками
class Atlas:
    def __init__(self):
        self.x = self.y = self.row = 0
        self.items = []

    def alloc(self, w, h):
        w, h = max(1, w), max(1, h)
        if self.x + w > TW:
            self.x, self.y, self.row = 0, self.y + self.row, 0
        r = (self.x, self.y)
        self.x += w
        self.row = max(self.row, h)
        assert self.y + h <= TH, 'атлас переполнен — увеличьте TW/TH'
        return r


ATLAS = Atlas()
IMG = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
GLOWIMG = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))

# грань: нормаль и оси (u вправо по грани, v вниз по грани) в мировых координатах модели
FACES = {
    'north': ((0, 0, -1), (-1, 0, 0), (0, -1, 0)),
    'south': ((0, 0, 1), (1, 0, 0), (0, -1, 0)),
    'east': ((-1, 0, 0), (0, 0, 1), (0, -1, 0)),
    'west': ((1, 0, 0), (0, 0, -1), (0, -1, 0)),
    'up': ((0, 1, 0), (-1, 0, 0), (0, 0, 1)),
    'down': ((0, -1, 0), (-1, 0, 0), (0, 0, -1)),
}


def face_uv(cube, mat):
    """Размечает и рисует все 6 граней бруска (без поворота — цвет по координатам до поворота, этого достаточно)."""
    ox, oy, oz = cube['origin']
    sx, sy, sz = cube['size']
    px, gpx = IMG.load(), GLOWIMG.load()
    uv = {}
    for f, (nrm, ua, va) in FACES.items():
        if f in ('north', 'south'):
            W, H = sx, sy
        elif f in ('east', 'west'):
            W, H = sz, sy
        else:
            W, H = sx, sz
        w, h = max(1, round(W)), max(1, round(H))
        u0, v0 = ATLAS.alloc(w, h)
        # стартовая точка грани (левый верх) в мире
        cx, cy, cz = ox + sx / 2, oy + sy / 2, oz + sz / 2
        start = [cx + nrm[0] * sx / 2 - ua[0] * W / 2 - va[0] * H / 2,
                 cy + nrm[1] * sy / 2 - ua[1] * W / 2 - va[1] * H / 2,
                 cz + nrm[2] * sz / 2 - ua[2] * W / 2 - va[2] * H / 2]
        for j in range(h):
            for i in range(w):
                fu, fv = (i + 0.5) / w * W, (j + 0.5) / h * H
                wx = start[0] + ua[0] * fu + va[0] * fv
                wy = start[1] + ua[1] * fu + va[1] * fv
                wz = start[2] + ua[2] * fu + va[2] * fv
                c = paint_px(mat, wx, wy, wz, nrm, (j + 0.5) / h, h, oy, cube)
                px[u0 + i, v0 + j] = c + (255,)
                if mat in GLOW:
                    gpx[u0 + i, v0 + j] = c + (255,)
        uv[f] = {'uv': [u0, v0], 'uv_size': [w, h]}
    return uv


# ---------------------------------------------------------------- геометрия
BONES = {}
ORDER = []


def bone(name, parent, pivot, rotation=None):
    b = {'name': name, 'pivot': [round(v, 3) for v in pivot]}
    if parent:
        b['parent'] = parent
    if rotation:
        b['rotation'] = rotation
    b['cubes'] = []
    BONES[name] = b
    ORDER.append(name)


def box(bn, x0, y0, z0, x1, y1, z1, mat, rot=None, pivot=None):
    o = [min(x0, x1), min(y0, y1), min(z0, z1)]
    s = [abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)]
    c = {'origin': [round(v, 3) for v in o], 'size': [round(v, 3) for v in s]}
    c['uv'] = face_uv(c, mat)
    if rot:
        c['rotation'] = rot
        c['pivot'] = [round(v, 3) for v in (pivot or [o[0] + s[0] / 2, o[1] + s[1] / 2, o[2] + s[2] / 2])]
    BONES[bn]['cubes'].append(c)


def pleats(bn, x0, x1, z, depth, y_top, y_bot, mat, side, seed, step=1.5, jag=1.6, out=0.0):
    """Ряд вертикальных складок по оси x на плоскости z (side = -1 перед, +1 зад): каждая своей глубины и длины — рваный подол."""
    rnd = random.Random(seed)
    x = x0
    i = 0
    while x < x1 - 0.05:
        w = min(step, x1 - x)
        d = depth * (0.55 + 0.45 * ((i % 3) / 2)) + out
        yb = y_bot - rnd.random() * jag
        zz = z + side * d
        box(bn, x, yb, min(z, zz), x + w, y_top, max(z, zz), mat)
        x += w
        i += 1


def pleats_side(bn, xs, z0, z1, depth, y_top, y_bot, mat, side, seed, step=1.5, jag=1.6, out=0.0):
    """Складки по оси z на боковой плоскости x = xs (side = -1 правый бок, +1 левый)."""
    rnd = random.Random(seed)
    z = z0
    i = 0
    while z < z1 - 0.05:
        w = min(step, z1 - z)
        d = depth * (0.55 + 0.45 * (((i + 1) % 3) / 2)) + out
        yb = y_bot - rnd.random() * jag
        xx = xs + side * d
        box(bn, min(xs, xx), yb, z, max(xs, xx), y_top, z + w, mat)
        z += w
        i += 1


def build():
    bone('bipedHead', None, [0, 24, 0]); bone('armorHead', 'bipedHead', [0, 24, 0])
    bone('bipedBody', None, [0, 24, 0]); bone('armorBody', 'bipedBody', [0, 24, 0])
    bone('bipedRightArm', None, [-5, 22, 0]); bone('armorRightArm', 'bipedRightArm', [-5, 22, 0])
    bone('bipedLeftArm', None, [5, 22, 0]); bone('armorLeftArm', 'bipedLeftArm', [5, 22, 0])
    bone('bipedRightLeg', None, [-1.9, 12, 0]); bone('armorRightLeg', 'bipedRightLeg', [-1.9, 12, 0])
    bone('bipedLeftLeg', None, [1.9, 12, 0]); bone('armorLeftLeg', 'bipedLeftLeg', [1.9, 12, 0])

    # ---- капюшон: толстые стенки, подвёрнутый край вокруг лица (выступает вперёд), бордовое нутро, округлая макушка, хвостик
    H = 'armorHead'
    box(H, -4.8, 32.0, -4.4, 4.8, 33.2, 5.0, 'hood')                      # верх
    box(H, -3.8, 33.2, -3.4, 3.8, 34.0, 4.2, 'hood')                      # купол
    box(H, -2.4, 34.0, -2.0, 2.4, 34.5, 3.0, 'hood')
    for s in (-1, 1):
        box(H, s * 4.0, 23.4, -4.4, s * 5.2, 32.4, 5.0, 'hood')             # бока
        box(H, s * 5.2, 24.4, -3.2, s * 5.7, 31.4, 4.0, 'hood')             # скругление боков
        box(H, s * 3.9, 23.6, -4.6, s * 4.1, 32.0, -3.2, 'hood_in')          # нутро
        box(H, s * 3.9, 23.0, -5.8, s * 5.3, 32.2, -4.4, 'hood')            # подвёрнутый край — толстый валик
    box(H, -5.3, 31.8, -5.9, 5.3, 33.3, -4.4, 'hood')                     # валик сверху (козырёк)
    box(H, -4.0, 31.7, -4.6, 4.0, 32.0, -3.2, 'hood_in')
    box(H, -5.0, 23.0, 4.0, 5.0, 32.4, 5.3, 'hood')                       # затылок
    box(H, -5.4, 23.0, 3.2, 5.4, 25.0, 5.8, 'hood')                       # капюшон ложится на плечи сзади
    bone('hood_tip', H, [0, 30.5, 5.2])
    box('hood_tip', -2.6, 26.6, 5.0, 2.6, 30.8, 6.4, 'hood')
    box('hood_tip', -1.6, 24.4, 5.6, 1.6, 27.0, 6.8, 'hood', rot=[14, 0, 0], pivot=[0, 27.0, 6.2])

    # ---- лиф, воротник, ленточка, выпуклый золотой узор
    B = 'armorBody'
    box(B, -4.4, 12.0, -2.5, 4.4, 24.0, 2.5, 'cloth')
    box(B, -3.2, 23.6, -3.2, 3.2, 25.2, 3.2, 'hood')                       # стоячий воротник
    box(B, -0.7, 22.2, -3.5, 0.7, 23.6, -3.0, 'ribbon')
    box(B, -1.8, 21.0, -3.4, -0.6, 22.8, -3.0, 'ribbon', rot=[0, 0, 15], pivot=[-1.2, 22.8, -3.2])
    box(B, 0.6, 21.0, -3.4, 1.8, 22.8, -3.0, 'ribbon', rot=[0, 0, -15], pivot=[1.2, 22.8, -3.2])
    # узор: столбик ромбов-уголков по центру переда (выступают над тканью)
    for yy, w in ((20.6, 2.6), (17.6, 3.4), (14.4, 2.6)):
        box(B, -0.45, yy - 1.1, -2.95, 0.45, yy + 1.1, -2.5, 'gold_raised')
        box(B, -w / 2, yy - 0.25, -2.85, w / 2, yy + 0.25, -2.5, 'gold_raised')
        for s in (-1, 1):
            box(B, s * w / 2 - 0.25, yy - 0.9, -2.85, s * w / 2 + 0.25, yy + 0.25, -2.5, 'gold_raised')
    # пелерина: внутренний слой длиннее, внешний короче, полы спереди расходятся, кайма — отдельный выступающий брусок
    bone('cape', B, [0, 24.4, 0])
    for s in (-1, 1):
        box('cape', s * 0.6, 17.4, -3.5, s * 6.8, 24.6, -2.5, 'capelet')     # правая/левая пола спереди
        box('cape', s * 6.8, 17.4, -3.5, s * 7.4, 24.6, 3.5, 'capelet')      # бока
        box('cape', s * 0.4, 16.2, -3.9, s * 7.0, 17.8, -3.3, 'trim')       # кайма пол
        box('cape', s * 7.0, 16.2, -3.9, s * 7.7, 17.8, 3.9, 'trim')
        box('cape', s * 1.2, 19.8, -4.0, s * 7.2, 24.8, -3.4, 'capelet')     # внешний слой — короче
        box('cape', s * 1.0, 19.0, -4.3, s * 7.4, 20.4, -3.8, 'trim')
    box('cape', -6.8, 17.4, 2.5, 6.8, 24.6, 3.5, 'capelet')                 # спина
    box('cape', -7.0, 16.2, 3.3, 7.0, 17.8, 3.9, 'trim')
    box('cape', -7.2, 19.8, 3.4, 7.2, 24.8, 4.0, 'capelet')
    box('cape', -7.4, 19.0, 3.8, 7.4, 20.4, 4.3, 'trim')
    box('cape', -6.6, 17.2, -3.2, 6.6, 17.5, 3.2, 'lining')
    # задний клин юбки — полосами-складками, рваный подол; колышется сильнее всего
    bone('cape_low', B, [0, 12.2, 2.6])
    pleats('cape_low', -5.8, 5.8, 2.6, 1.0, 12.4, 2.2, 'skirt_back', +1, 7, step=1.45, jag=0.8)
    box('cape_low', -5.6, 2.0, 2.4, 5.6, 12.0, 2.6, 'lining')

    # ---- рукава-колокола: пышный верх, раструб с бордовой изнанкой, золотая нить по краю
    for s, bn in ((-1, 'armorRightArm'), (1, 'armorLeftArm')):
        box(bn, s * 3.4, 20.0, -2.9, s * 8.8, 24.4, 2.9, 'cloth')
        box(bn, s * 3.2, 17.8, -3.3, s * 9.3, 21.0, 3.3, 'cloth')           # пышная середина
        box(bn, s * 3.0, 15.2, -3.7, s * 9.7, 18.0, 3.7, 'cloth')           # раструб
        box(bn, s * 3.2, 15.0, -3.5, s * 9.5, 15.3, 3.5, 'lining')          # изнанка видна снизу
        box(bn, s * 2.9, 14.6, -3.8, s * 9.8, 15.1, 3.8, 'lining')          # бордовый край
        box(bn, s * 2.9, 15.1, -3.85, s * 9.8, 15.4, 3.85, 'gold')

    # ---- кот Неро: две копии — на левом плече (в теле) и на макушке капюшона (в голове)
    cat('nero', B, 6.2, 24.8, 0.0)
    cat('nero_hood', H, 0.0, 34.5, 1.0)

    # ---- юбка: верхний ярус на ногах, нижний ярус (колышется) — складки по переду, боку и заду, рваный подол
    for s, bn, hem in ((-1, 'armorRightLeg', 'hem_r'), (1, 'armorLeftLeg', 'hem_l')):
        xi, xo = -s * 0.6, s * 4.9                                          # от середины (с заходом) до бока
        lo, hi = min(xi, xo), max(xi, xo)
        box(bn, lo, 7.4, -2.8, hi, 12.4, 2.8, 'cloth')                       # основа верхнего яруса
        pleats(bn, lo, hi, -2.8, 0.7, 12.4, 7.2, 'cloth', -1, 11 + s, step=1.4, jag=0.4)
        pleats(bn, lo, hi, 2.8, 0.7, 12.4, 7.2, 'cloth', +1, 21 + s, step=1.4, jag=0.4)
        bone(hem, bn, [s * 1.9, 7.6, 0])
        xo2 = s * 5.6
        lo2, hi2 = min(xi, xo2), max(xi, xo2)
        box(hem, lo2, 2.6, -3.4, hi2, 7.8, 3.4, 'skirt')                     # основа нижнего яруса
        pleats(hem, lo2, hi2, -3.4, 1.0, 7.8, 2.2, 'skirt', -1, 31 + s, step=1.5, jag=0.8)
        pleats(hem, lo2, hi2, 3.4, 1.0, 7.8, 2.2, 'skirt', +1, 41 + s, step=1.5, jag=0.8)
        pleats_side(hem, xo2, -3.4, 3.4, 1.0, 7.8, 2.2, 'skirt', s, 51 + s, step=1.5, jag=0.8)
        box(hem, lo2 + 0.2, 1.6, -3.8, hi2 - 0.2, 2.6, 3.8, 'lining')         # бордовая оборка под подолом


def cat(p, parent, ox, oy, oz):
    """Сидящий чёрный кот: туловище, лапы, голова с ушами и носом, глаза (моргают), хвост. Опорная точка — середина под котом."""
    def b(bn, x0, y0, z0, x1, y1, z1, mat):
        box(bn, ox + x0, oy + y0, oz + z0, ox + x1, oy + y1, oz + z1, mat)
    bone(p, parent, [ox, oy, oz])
    b(p, -1.3, 0.0, -1.0, 1.5, 2.2, 2.4, 'fur')
    b(p, -1.0, 0.0, -1.6, 1.2, 0.8, -0.8, 'fur')
    bone(p + '_head', p, [ox + 0.1, oy + 2.0, oz - 1.0])
    b(p + '_head', -1.2, 1.8, -3.0, 1.4, 4.2, -0.6, 'fur')
    b(p + '_head', -1.1, 4.1, -2.4, -0.4, 5.0, -1.6, 'fur')
    b(p + '_head', 0.6, 4.1, -2.4, 1.3, 5.0, -1.6, 'fur')
    b(p + '_head', -0.1, 2.4, -3.15, 0.3, 2.7, -3.0, 'nose')
    bone(p + '_eyes', p + '_head', [ox + 0.1, oy + 3.2, oz - 3.05])
    b(p + '_eyes', -0.85, 2.9, -3.15, -0.25, 3.5, -3.0, 'eye')
    b(p + '_eyes', 0.45, 2.9, -3.15, 1.05, 3.5, -3.0, 'eye')
    bone(p + '_tail', p, [ox + 0.1, oy + 0.4, oz + 2.2])
    b(p + '_tail', -0.2, -2.4, 2.0, 0.4, 0.6, 2.6, 'fur')
    b(p + '_tail', -0.2, -3.4, 2.2, 0.4, -2.2, 3.4, 'fur')


def write_geo():
    bones = []
    for n in ORDER:
        b = dict(BONES[n])
        if not b['cubes']:
            del b['cubes']
        bones.append(b)
    geo = {'format_version': '1.12.0', 'minecraft:geometry': [{
        'description': {'identifier': f'geometry.{NAME}', 'texture_width': TW, 'texture_height': TH,
                        'visible_bounds_width': 3, 'visible_bounds_height': 3.5, 'visible_bounds_offset': [0, 1.25, 0]},
        'bones': bones}]}
    os.makedirs(os.path.join(A, 'geo', 'armor'), exist_ok=True)
    json.dump(geo, open(os.path.join(A, 'geo', 'armor', NAME + '.geo.json'), 'w'), separators=(',', ':'))


# ---------------------------------------------------------------- анимации
def r3(v):
    return round(v, 3)


def wave(length, base, terms, n=None):
    if n is None:
        n = 8
        for tm in terms:
            n = max(n, min(96, int(16 * tm[0])))
    o = {}
    for i in range(n + 1):
        u = i / n
        v = list(base)
        for cyc, ph, x, y, z in terms:
            m = math.sin(2 * math.pi * (cyc * u + ph))
            v[0] += x * m; v[1] += y * m; v[2] += z * m
        o[f'{length * u:.4g}'] = [r3(c) for c in v]
    return o


def keys(*kv):
    return {f'{t:.4g}': [r3(x), r3(y), r3(z)] for t, x, y, z in kv}


def cat_life(p, length=4):
    """Кот живой: моргает, вертит головой, машет хвостом."""
    b = length * 0.55
    return {p + '_tail': {'rotation': wave(length, (10, 0, 0), [(1, 0, 0, 0, 18), (2, 0.25, 6, 0, 0)])},
            p + '_head': {'rotation': wave(length, (0, 0, 0), [(1, 0, 4, 18, 0)])},
            p + '_eyes': {'scale': keys((0, 1, 1, 1), (b, 1, 1, 1), (b + 0.06, 1, 0.12, 1), (b + 0.14, 1, 1, 1), (length, 1, 1, 1))}}


HIDE = {'scale': keys((0, 0, 0, 0))}
SHOW = {'scale': keys((0, 1, 1, 1))}


def cat_anims():
    """Отдельный контроллер кота (код): плечо ⇄ капюшон на касте; превращение в тень дракона на «Чёрном пламени Ворганы».
    Смещения — в пикселях модели; плечо (6, 24.6, 0) → макушка (0, 33.5, 1) — это около (-6, +9, +1) в теле, но голова свою копию держит сама."""
    an = {}
    a = {'nero': SHOW, 'nero_hood': HIDE}
    a.update(cat_life('nero'))
    an['nero_shoulder'] = {'loop': True, 'animation_length': 4, 'bones': a}
    # прыжок на капюшон: присел, дуга вверх-внутрь, исчез на плече; на макушке «приземлился» с пружинкой
    an['nero_jump_up'] = {'loop': 'hold_on_last_frame', 'animation_length': 0.5, 'bones': {
        'nero': {'position': keys((0, 0, 0, 0), (0.08, 0, -0.6, 0), (0.25, 3, 6, 0.5), (0.35, 5, 9, 1)),
                 'scale': keys((0, 1, 1, 1), (0.08, 1.1, 0.8, 1.1), (0.3, 1, 1, 1), (0.34, 1, 1, 1), (0.35, 0, 0, 0), (0.5, 0, 0, 0))},
        'nero_hood': {'scale': keys((0, 0, 0, 0), (0.349, 0, 0, 0), (0.35, 1.15, 0.8, 1.15), (0.43, 0.95, 1.08, 0.95), (0.5, 1, 1, 1))}}}
    a = {'nero': HIDE, 'nero_hood': SHOW}
    a.update(cat_life('nero_hood'))
    a['nero_hood_head'] = {'rotation': wave(4, (-8, 0, 0), [(1, 0, 3, 10, 0)])}       # смотрит вперёд, туда же, куда ведьма
    an['nero_head'] = {'loop': True, 'animation_length': 4, 'bones': a}
    an['nero_jump_down'] = {'loop': 'hold_on_last_frame', 'animation_length': 0.5, 'bones': {
        'nero_hood': {'scale': keys((0, 1, 1, 1), (0.08, 1.1, 0.8, 1.1), (0.14, 1, 1, 1), (0.15, 0, 0, 0), (0.5, 0, 0, 0))},
        'nero': {'position': keys((0, 5, 9, 1), (0.149, 5, 9, 1), (0.3, 2, 4, 0.5), (0.42, 0, 0, 0)),
                 'scale': keys((0, 0, 0, 0), (0.149, 0, 0, 0), (0.15, 1, 1, 1), (0.42, 1.15, 0.8, 1.15), (0.5, 1, 1, 1))}}}
    # превращение: кот спрыгивает вперёд с плеча, вытягивается и растворяется — в этот момент код запускает тень дракона
    an['nero_dragon'] = {'loop': 'hold_on_last_frame', 'animation_length': 0.6, 'bones': {
        'nero': {'position': keys((0, 0, 0, 0), (0.1, 0, -0.5, 0), (0.35, -1, 4, -6), (0.6, -2, 6, -10)),
                 'scale': keys((0, 1, 1, 1), (0.1, 1.1, 0.85, 1.1), (0.35, 1.2, 1.2, 1.6), (0.55, 0.3, 0.3, 0.6), (0.6, 0, 0, 0))},
        'nero_hood': HIDE}}
    an['nero_return'] = {'loop': 'hold_on_last_frame', 'animation_length': 0.5, 'bones': {
        'nero': {'scale': keys((0, 0, 0, 0), (0.2, 0, 0, 0), (0.32, 1.2, 1.2, 1.2), (0.42, 0.95, 0.95, 0.95), (0.5, 1, 1, 1))},
        'nero_hood': HIDE}}
    an['nero_hidden'] = {'loop': True, 'animation_length': 1, 'bones': {'nero': HIDE, 'nero_hood': HIDE}}
    return an


def write_anim():
    """Знаки: у задних частей отрицательный x — отлёт назад (так GeckoLib поворачивает кость); у пол положительный x — вперёд."""
    anims = {}
    a = {'cape': {'rotation': wave(4, (0, 0, 0), [(1, 0, -1.2, 0, 0.8)])},
         'cape_low': {'rotation': wave(4, (-3, 0, 0), [(1, -0.1, -2.5, 0, 1.2)])},
         'hood_tip': {'rotation': wave(4, (0, 0, 0), [(1, -0.2, -3, 0, 2)])},
         'hem_r': {'rotation': wave(4, (0, 0, 0), [(1, 0, 1.5, 0, -1.5)])}, 'hem_l': {'rotation': wave(4, (0, 0, 0), [(1, 0.5, 1.5, 0, 1.5)])}}
    anims['idle'] = {'loop': True, 'animation_length': 4, 'bones': a}
    a = {'cape': {'rotation': wave(1, (-3, 0, 0), [(2, 0, -2, 0, 0)])},
         'cape_low': {'rotation': wave(1, (-5, 0, 0), [(2, -0.15, -3, 0, 1)])},
         'hood_tip': {'rotation': wave(1, (-6, 0, 0), [(2, -0.25, -5, 0, 3)])},
         'hem_r': {'rotation': wave(1, (0, 0, 0), [(1, 0, 9, 0, -3)])}, 'hem_l': {'rotation': wave(1, (0, 0, 0), [(1, 0.5, 9, 0, 3)])}}
    anims['walk'] = {'loop': True, 'animation_length': 1, 'bones': a}
    a = {'cape': {'rotation': wave(0.6, (-10, 0, 0), [(2, 0, -4, 0, 0)])},
         'cape_low': {'rotation': wave(0.6, (-12, 0, 0), [(2, -0.15, -4, 0, 1.5)])},
         'hood_tip': {'rotation': wave(0.6, (-24, 0, 0), [(2, -0.25, -8, 0, 4)])},
         'hem_r': {'rotation': wave(0.6, (-3, 0, 0), [(1, 0, 8, 0, -2)])}, 'hem_l': {'rotation': wave(0.6, (-3, 0, 0), [(1, 0.5, 8, 0, 2)])}}
    anims['run'] = {'loop': True, 'animation_length': 0.6, 'bones': a}
    a = {'cape': {'rotation': wave(1, (-8, 0, 0), [(3, 0, -4, 0, 2)])},
         'cape_low': {'rotation': wave(1, (-9, 0, 0), [(3, -0.2, -3, 0, 1.5)])},
         'hood_tip': {'rotation': wave(1, (-24, 0, 0), [(3, -0.3, -6, 0, 3)])},
         'hem_r': {'rotation': wave(1, (4, 0, -3), [(3, 0, 4, 0, -2)])}, 'hem_l': {'rotation': wave(1, (4, 0, 3), [(3, 0.5, 4, 0, 2)])}}
    anims['cast'] = {'loop': True, 'animation_length': 1, 'bones': a}
    anims.update(cat_anims())
    for an in anims.values():
        for b in an['bones']:
            assert b in BONES, b
    os.makedirs(os.path.join(A, 'animations', 'armor'), exist_ok=True)
    json.dump({'format_version': '1.8.0', 'animations': anims}, open(os.path.join(A, 'animations', 'armor', NAME + '.animation.json'), 'w'),
              separators=(',', ':'))


def main():
    build()
    d = os.path.join(A, 'textures', 'armor')
    os.makedirs(d, exist_ok=True)
    IMG.save(os.path.join(d, NAME + '.png'))
    GLOWIMG.save(os.path.join(d, NAME + '_glowmask.png'))
    write_geo()
    write_anim()
    n = sum(len(BONES[b]['cubes']) for b in ORDER)
    print(f'{NAME}: {n} cubes, {len(ORDER)} bones, atlas {TW}x{TH} used to y={ATLAS.y + ATLAS.row}')


if __name__ == '__main__':
    main()
