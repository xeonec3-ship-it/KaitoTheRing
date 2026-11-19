#!/usr/bin/env python3
"""
Одежда безмолвной ведьмы (T19) по артам «Секретов безмолвной ведьмы» (кадры, постеры и 3D-фигура, присланные владельцем и сценаристом):
почти чёрное длинное платье-мантия с широкой расклешённой юбкой; внизу юбки полосы — серо-зелёная, тёмно-серая и широкая
горчично-золотая; бордовая подкладка; капюшон чёрный, внутри бордовый; пелерина на плечах с золотым зигзагом и серой полосой;
по переду — золотой геометрический узор, по юбке — мелкие золотые ромбики; короткие пышные рукава; зелёная ленточка у ворота;
кот Неро на левом плече.

Текстура 128x128: у каждой части своя прорисовка (складки, светотень, затемнение книзу, полосы и узоры — прямо на ткани),
а не один мелкий узор на все грани. GeckoLib-броня: одна геометрия на комплект с костями armorHead / armorBody / armorRightArm /
armorLeftArm / armorRightLeg / armorLeftLeg. ВАЖНО для кода: юбка сидит на костях ног, поэтому рендер брони ведьмы должен
поворачивать кости ног (bipedRightLeg / bipedLeftLeg) только на 25 % от поворота ноги игрока — иначе платье на шаге разъезжается
пополам (переопределить applyBaseTransformations в GeoArmorRenderer). Колышутся свои кости: cape (пелерина), cape_low (задний клин юбки), hood_tip, hem_r / hem_l
(низ юбки); кот — две копии: nero* на плече и nero_hood* на капюшоне, свой контроллер анимаций.

Выход (assets/pohsmp_core): geo/armor/silent_witch_armor.geo.json, animations/armor/silent_witch_armor.animation.json,
textures/armor/silent_witch_armor.png (+ _glowmask.png — глаза кота и золото узора на переде слегка светятся ночью, сила — в отрисовщике).
Анимации ткани: idle, walk, run, cast; кота (отдельный контроллер): nero_shoulder, nero_jump_up, nero_head, nero_jump_down,
nero_dragon, nero_return, nero_hidden. Координаты — геометрия Bedrock/GeckoLib в пикселях (голова — куб от -4,24,-4 размером 8;
+x — левая сторона, перед — -z). Запуск: python3 tools/gen_silent_outfit.py
"""
import json
import math
import os
import random

from PIL import Image

NAME = 'silent_witch_armor'
HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
TW = TH = 128

# ---------------------------------------------------------------- палитра (по артам)
CLOTH = (38, 37, 46)          # почти чёрная ткань с лёгкой синевой
LINING = (92, 30, 44)         # бордовая подкладка
BAND_GREEN = (118, 134, 124)  # серо-зелёная полоса
BAND_SLATE = (62, 66, 80)     # тёмно-серая полоса
BAND_GOLD = (184, 150, 62)    # широкая горчично-золотая полоса
GOLD = (214, 178, 84)
GOLD_HI = (246, 222, 150)
GOLD_LO = (138, 104, 36)
RIBBON = (86, 170, 96)
FUR = (30, 28, 36)

# области текстуры: имя -> (x, y, w, h)
R = {
    'skirt': (0, 0, 32, 48),       # юбка: складки, полосы внизу, ромбики
    'skirt_back': (32, 0, 32, 48),
    'bodice': (64, 0, 16, 24),     # лиф
    'front': (80, 0, 16, 48),      # перед с золотым узором (лиф + юбка)
    'capelet': (96, 0, 32, 16),    # пелерина: серая полоса, золотой зигзаг по низу
    'hood': (96, 16, 16, 16),
    'hood_in': (112, 16, 16, 16),  # бордовое нутро капюшона
    'lining': (64, 24, 16, 16),
    'sleeve': (96, 32, 16, 16),    # пышный рукав с бордовым краем
    'gold': (112, 32, 8, 8),
    'ribbon': (120, 32, 8, 8),
    'fur': (112, 40, 8, 8),
    'eye': (120, 40, 8, 8),
    'nose': (64, 40, 4, 4),
    'trim': (0, 48, 32, 8),        # отдельная лента золотого зигзага
    'skirt_top': (0, 56, 32, 24),  # верх юбки: только ткань со складками и ромбиками (полосы — внизу, на подоле)
}
GLOW = {'eye'}


def clamp(c):
    return tuple(max(0, min(255, int(round(v)))) for v in c)


def mul(c, k):
    return clamp((c[0] * k, c[1] * k, c[2] * k))


class Tex:
    def __init__(self):
        self.im = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
        self.px = self.im.load()
        self.rnd = random.Random(19)

    def put(self, x, y, c, a=255):
        self.px[x, y] = clamp(c) + (a,)

    def region(self, name, fn):
        x0, y0, w, h = R[name]
        for y in range(h):
            for x in range(w):
                self.put(x0 + x, y0 + y, fn(x, y, w, h))


def fold(x, w, period, phase=0.0):
    """Мягкие вертикальные складки: примерно 0.8..1.12 по ширине."""
    return 0.95 + 0.17 * math.sin(2 * math.pi * (x / period + phase)) * (0.7 + 0.3 * math.sin(2 * math.pi * x / (period * 2.7)))


def paint():
    t = Tex()
    rnd = t.rnd

    def cloth(x, y, w, h, period=6.0, top_shadow=0.0):
        k = fold(x, w, period) * (1.08 - 0.22 * (y / h))           # светлее сверху, к низу темнее
        if top_shadow and y < top_shadow:
            k *= 0.78 + 0.22 * (y / top_shadow)                         # тень под пелериной / поясом
        k *= 0.97 + 0.06 * rnd.random()                                 # зерно ткани
        return mul(CLOTH, k)

    def skirt(x, y, w, h, back=False):
        # полосы снизу вверх (в пикселях области 48): золото 0..9, тёмно-серая 9..13, серо-зелёная 14..18
        yb = h - 1 - y
        wave_ = 1.2 * math.sin(2 * math.pi * x / w * 2 + (0.6 if back else 0))   # полосы чуть волной, как ткань колышется
        k = fold(x, w, 7.0, 0.3 if back else 0) * (0.97 + 0.06 * rnd.random())
        if yb < 9 + wave_:
            c = mul(BAND_GOLD, k * (0.86 + 0.14 * (yb / 9)))
            if yb < 1:
                c = mul(BAND_GOLD, 0.62)                                 # подгиб
        elif yb < 13 + wave_:
            c = mul(BAND_SLATE, k)
        elif yb < 14 + wave_:
            c = mul(CLOTH, k * 0.9)
        elif yb < 18.5 + wave_:
            c = mul(BAND_GREEN, k * 0.92)
        else:
            c = cloth(x, y, w, h, 7.0, top_shadow=5)
        return c

    t.region('skirt', lambda x, y, w, h: skirt(x, y, w, h))
    t.region('skirt_back', lambda x, y, w, h: skirt(x, y, w, h, back=True))
    t.region('skirt_top', lambda x, y, w, h: mul(CLOTH, fold(x, w, 7.0) * (1.02 - 0.12 * (y / h)) * (0.8 + 0.2 * min(1, y / 4)) * (0.97 + 0.06 * rnd.random())))
    for name, spots in (('skirt', ((7, 14), (21, 9), (27, 20))), ('skirt_back', ((5, 12), (19, 7), (27, 17), (11, 22), (23, 26))),
                        ('skirt_top', ((6, 10), (20, 15), (27, 6)))):   # мелкие золотые ромбики по юбке
        x0, y0, w, h = R[name]
        for cx, cy in spots:
            for dx, dy in ((0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)):
                t.put(x0 + cx + dx, y0 + cy + dy, GOLD_HI if (dx, dy) == (0, -1) else GOLD)
    t.region('bodice', lambda x, y, w, h: cloth(x, y, w, h, 5.0) if y > 1 else mul(CLOTH, 0.7))

    def front(x, y, w, h):
        """Перед: по центру золотой геометрический узор — вытянутые ромбы и уголки сверху вниз, по краям ткань; ниже — полосы юбки."""
        base = skirt(x, y, w, h) if y >= 30 else cloth(x, y, w, h, 5.0)
        cx = (w - 1) / 2
        d = abs(x - cx)
        for top, ln, wid in ((3, 9, 3.2), (13, 7, 2.4), (21, 9, 3.6), (31, 8, 2.8)):
            if top <= y < top + ln:
                u = (y - top) / ln
                half = wid * (1 - abs(2 * u - 1))
                if d <= half:
                    return GOLD_LO if half - d < 0.9 else (GOLD_HI if x < cx and u < 0.5 else GOLD)
        if 1 <= y < 30 and abs(d - 3.6) < 0.5 and y % 6 in (0, 1, 2):
            return GOLD
        return base
    t.region('front', front)

    def capelet(x, y, w, h):
        if y >= 11:                                                      # золотая лента с тёмным зигзагом по низу
            if y in (11, 15):
                return GOLD_LO
            tip = abs((x % 4) - 2)
            return mul(CLOTH, 0.8) if 12 + tip <= y <= 14 else GOLD
        if 8 <= y <= 9:
            return mul(BAND_GREEN, 0.85 * fold(x, w, 6))                 # серая полоса над лентой
        return cloth(x, y, w, h, 5.0)
    t.region('capelet', capelet)

    t.region('hood', lambda x, y, w, h: mul(CLOTH, (1.12 - 0.3 * abs(x - w / 2) / (w / 2)) * (1.05 - 0.15 * y / h) * (0.97 + 0.06 * rnd.random())))
    t.region('hood_in', lambda x, y, w, h: mul(LINING, 0.55 + 0.35 * (y / h)))
    t.region('lining', lambda x, y, w, h: mul(LINING, fold(x, w, 5) * (0.75 + 0.25 * (y / h))))

    def sleeve(x, y, w, h):
        if y >= 13:
            return mul(LINING, 0.85 if y < 15 else 0.6)                   # бордовый край
        puff = 0.85 + 0.3 * math.sin(math.pi * (y + 1) / 14)               # пышность: светлее посередине
        return mul(CLOTH, puff * fold(x, w, 4) * (0.97 + 0.06 * rnd.random()))
    t.region('sleeve', sleeve)

    t.region('gold', lambda x, y, w, h: GOLD_HI if (x == 0 or y == 0) else GOLD_LO if (x == w - 1 or y == h - 1) else GOLD)
    t.region('ribbon', lambda x, y, w, h: mul(RIBBON, 1.15 if y < 3 else 0.9))
    t.region('fur', lambda x, y, w, h: mul(FUR, 1.35 if (x == 0 or y == 0) else 0.85 if (x == w - 1 or y == h - 1) else 1.0 + 0.1 * rnd.random()))
    t.region('eye', lambda x, y, w, h: (255, 246, 176) if (x, y) in ((2, 2), (3, 2)) else (242, 210, 58) if 1 <= x <= 6 and 1 <= y <= 6 else (200, 154, 16))
    t.region('nose', lambda x, y, w, h: (232, 154, 176))

    def trim(x, y, w, h):
        if y in (0, 7):
            return GOLD_LO
        tip = abs((x % 4) - 2)
        return mul(CLOTH, 0.8) if 2 + tip <= y <= 5 else GOLD
    t.region('trim', trim)
    return t.im


def uvf(mat):
    x0, y0, w, h = R[mat]
    f = {n: {'uv': [x0, y0], 'uv_size': [w, h]} for n in ('north', 'east', 'south', 'west')}
    hh = min(h, 4)
    f['up'] = {'uv': [x0, y0], 'uv_size': [w, hh]}
    f['down'] = {'uv': [x0, y0 + h - hh], 'uv_size': [w, hh]}
    return f


# ---------------------------------------------------------------- геометрия
BONES = {}
ORDER = []
LITMATS = set()


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
    c = {'origin': [round(v, 3) for v in o], 'size': [round(v, 3) for v in s], 'uv': uvf(mat)}
    if rot:
        c['rotation'] = rot
        c['pivot'] = [round(v, 3) for v in (pivot or [o[0] + s[0] / 2, o[1] + s[1] / 2, o[2] + s[2] / 2])]
    BONES[bn]['cubes'].append(c)
    if mat in GLOW:
        LITMATS.add(mat)


def build():
    bone('bipedHead', None, [0, 24, 0]); bone('armorHead', 'bipedHead', [0, 24, 0])
    bone('bipedBody', None, [0, 24, 0]); bone('armorBody', 'bipedBody', [0, 24, 0])
    bone('bipedRightArm', None, [-5, 22, 0]); bone('armorRightArm', 'bipedRightArm', [-5, 22, 0])
    bone('bipedLeftArm', None, [5, 22, 0]); bone('armorLeftArm', 'bipedLeftArm', [5, 22, 0])
    bone('bipedRightLeg', None, [-1.9, 12, 0]); bone('armorRightLeg', 'bipedRightLeg', [-1.9, 12, 0])
    bone('bipedLeftLeg', None, [1.9, 12, 0]); bone('armorLeftLeg', 'bipedLeftLeg', [1.9, 12, 0])

    # ---- капюшон: округлый, открыт спереди, бордовое нутро у лица, небольшой хвостик назад
    H = 'armorHead'
    box(H, -4.6, 32.0, -4.6, 4.6, 33.1, 4.8, 'hood')
    box(H, -3.6, 33.1, -3.6, 3.6, 33.6, 3.8, 'hood')
    for s in (-1, 1):
        box(H, s * 3.95, 23.6, -4.8, s * 5.0, 32.4, 4.8, 'hood')
        box(H, s * 3.8, 24.0, -4.6, s * 3.95, 32.0, -3.4, 'hood_in')
        box(H, s * 4.9, 24.4, -3.6, s * 5.3, 31.6, 3.6, 'hood')
    box(H, -4.8, 23.4, 3.95, 4.8, 32.4, 5.0, 'hood')
    box(H, -4.0, 31.8, -4.0, 4.0, 32.0, -3.4, 'hood_in')
    box(H, -4.8, 31.6, -5.2, 4.8, 32.6, -4.6, 'hood')
    bone('hood_tip', H, [0, 30.5, 5.0])
    box('hood_tip', -2.4, 26.8, 4.8, 2.4, 30.8, 6.0, 'hood')
    box('hood_tip', -1.4, 24.6, 5.4, 1.4, 27.2, 6.4, 'hood', rot=[14, 0, 0], pivot=[0, 27.2, 5.9])

    # ---- лиф, перед с узором, воротник, ленточка, пелерина
    B = 'armorBody'
    box(B, -4.4, 12.0, -2.5, 4.4, 24.0, 2.5, 'bodice')
    box(B, -1.8, 4.0, -2.8, 1.8, 23.6, -2.45, 'front')
    box(B, -2.8, 23.6, -2.9, 2.8, 24.8, 2.9, 'hood')
    box(B, -0.6, 22.2, -3.2, 0.6, 23.4, -2.8, 'ribbon')
    box(B, -1.5, 21.2, -3.15, -0.5, 22.6, -2.9, 'ribbon', rot=[0, 0, 15], pivot=[-1, 22.6, -3])
    box(B, 0.5, 21.2, -3.15, 1.5, 22.6, -2.9, 'ribbon', rot=[0, 0, -15], pivot=[1, 22.6, -3])
    bone('cape', B, [0, 24.4, 0])
    box('cape', -6.6, 18.4, -3.3, 6.6, 24.6, 3.3, 'capelet')
    box('cape', -6.4, 18.6, -3.1, 6.4, 18.8, 3.1, 'lining')
    box('cape', -2.2, 18.2, -3.45, 2.2, 22.0, -3.25, 'front')
    # задний клин юбки: длинный, расклешённый — колышется сильнее всего
    bone('cape_low', B, [0, 12.2, 2.6])
    box('cape_low', -5.6, 2.6, 2.5, 5.6, 12.4, 3.4, 'skirt_back')
    box('cape_low', -5.4, 2.8, 2.3, 5.4, 12.0, 2.5, 'lining')

    # ---- короткие пышные рукава (дальше рука своя)
    for s, bn in ((-1, 'armorRightArm'), (1, 'armorLeftArm')):
        box(bn, s * 3.4, 17.2, -2.9, s * 9.0, 24.4, 2.9, 'sleeve')
        box(bn, s * 3.6, 17.0, -2.7, s * 8.8, 17.3, 2.7, 'lining')

    # ---- кот Неро: две копии — на левом плече (в теле) и на макушке капюшона (в голове, следует за поворотом головы).
    # Какая видна — решает отдельный контроллер анимаций кота (nero_shoulder / nero_jump_up / nero_head / nero_jump_down / nero_dragon / nero_return).
    cat('nero', B, 6.0, 24.6, 0.0)
    cat('nero_hood', H, 0.0, 33.5, 1.0)

    # ---- юбка на ногах: широкая, расклешённая, до середины голени; низ колышется
    for s, bn, hem in ((-1, 'armorRightLeg', 'hem_r'), (1, 'armorLeftLeg', 'hem_l')):
        px = s * 1.9
        x_in, x_out = -s * 0.6, px + s * 2.9                             # половина юбки: заходит за середину — половины перекрываются, щели нет
        box(bn, min(x_in, x_out), 7.0, -3.0, max(x_in, x_out), 12.4, 3.0, 'skirt_top')
        bone(hem, bn, [px, 7.0, 0])
        xo2 = px + s * 3.8
        box(hem, min(x_in, xo2), 2.4, -3.8, max(x_in, xo2), 7.2, 3.8, 'skirt')
        box(hem, min(x_in, xo2) + 0.2, 2.6, -3.6, max(x_in, xo2) - 0.2, 2.8, 3.6, 'lining')


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
         'cape_low': {'rotation': wave(1, (-12, 0, 0), [(2, -0.15, -6, 0, 2)])},
         'hood_tip': {'rotation': wave(1, (-6, 0, 0), [(2, -0.25, -5, 0, 3)])},
         'hem_r': {'rotation': wave(1, (0, 0, 0), [(1, 0, 9, 0, -3)])}, 'hem_l': {'rotation': wave(1, (0, 0, 0), [(1, 0.5, 9, 0, 3)])}}
    anims['walk'] = {'loop': True, 'animation_length': 1, 'bones': a}
    a = {'cape': {'rotation': wave(0.6, (-10, 0, 0), [(2, 0, -4, 0, 0)])},
         'cape_low': {'rotation': wave(0.6, (-30, 0, 0), [(2, -0.15, -9, 0, 4)])},
         'hood_tip': {'rotation': wave(0.6, (-24, 0, 0), [(2, -0.25, -8, 0, 4)])},
         'hem_r': {'rotation': wave(0.6, (-6, 0, 0), [(1, 0, 15, 0, -4)])}, 'hem_l': {'rotation': wave(0.6, (-6, 0, 0), [(1, 0.5, 15, 0, 4)])}}
    anims['run'] = {'loop': True, 'animation_length': 0.6, 'bones': a}
    a = {'cape': {'rotation': wave(1, (-8, 0, 0), [(3, 0, -4, 0, 2)])},
         'cape_low': {'rotation': wave(1, (-32, 0, 0), [(3, -0.2, -8, 0, 4)])},
         'hood_tip': {'rotation': wave(1, (-24, 0, 0), [(3, -0.3, -6, 0, 3)])},
         'hem_r': {'rotation': wave(1, (8, 0, -10), [(3, 0, 6, 0, -4)])}, 'hem_l': {'rotation': wave(1, (8, 0, 10), [(3, 0.5, 6, 0, 4)])}}
    anims['cast'] = {'loop': True, 'animation_length': 1, 'bones': a}
    anims.update(cat_anims())
    for an in anims.values():
        for b in an['bones']:
            assert b in BONES, b
    os.makedirs(os.path.join(A, 'animations', 'armor'), exist_ok=True)
    json.dump({'format_version': '1.8.0', 'animations': anims}, open(os.path.join(A, 'animations', 'armor', NAME + '.animation.json'), 'w'),
              separators=(',', ':'))


def main():
    im = paint()
    d = os.path.join(A, 'textures', 'armor')
    os.makedirs(d, exist_ok=True)
    im.save(os.path.join(d, NAME + '.png'))
    build()
    gm = Image.new('RGBA', (TW, TH), (0, 0, 0, 0))
    src, dst = im.load(), gm.load()
    for m in list(LITMATS) + ['front']:                       # глаза кота и золото узора на переде
        x0, y0, w, h = R[m]
        for y in range(h):
            for x in range(w):
                c = src[x0 + x, y0 + y]
                if m == 'front' and not (c[0] > 150 and c[1] > 110 and c[2] < 140):
                    continue
                dst[x0 + x, y0 + y] = c
    gm.save(os.path.join(d, NAME + '_glowmask.png'))
    write_geo()
    write_anim()
    n = sum(len(BONES[b]['cubes']) for b in ORDER)
    print(f'{NAME}: {n} cubes, {len(ORDER)} bones, texture {TW}x{TH}')


if __name__ == '__main__':
    main()
