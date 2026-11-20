#!/usr/bin/env python3
"""
T26 — визуал босса «Head of the Cult of Mellisto» (владелец: имя на обоих языках английское; в ТЗ — «Глава Культа Меллисто»). ТЗ: docs/specs/tasks/T26_cult_leader_boss.md.
Основа — «Echo of Tyros» из Iron's Spellbooks (FireBossEntity). Всё исходное берётся из jar Iron's:
  libs/irons_spellbooks-1.20.1-3.16.1.jar  (скачать: python3 tools/fetch_libs.py)
  geo/tyros.geo.json, textures/entity/fire_boss/{tyros,tyros_soul_mode,tyros_flame}.png, textures/gui/sprites/boss_bars/tyros_bossbar.png,
  geo/abstract_casting_mob.geo.json (основа культиста). Анимации НЕ копируются: босс играет те же casting_animations.json Iron's.

Правило владельца: «цвета оставляем что были» — палитра Тироса не меняется. Высокое разрешение рисуется только цветами исходной палитры
(и промежуточными тонами между соседними цветами одного семейства): Scale2x×2 (пиксель-арт ×4 без новых цветов) + ткань/металл/кромки.

Пишет (src/main/resources/assets/pohsmp_core/):
  geo/entity/cult_leader.geo.json          — модель Тироса (кости и их имена — как были) + детали: зубчатый венец на капюшоне,
                                              рваный плащ (новая кость cape), медальон-печать на груди, шипы наплечников, амулеты на поясе
  textures/entity/cult_leader/cult_leader.png, cult_leader_soul_mode.png (512×512 = атлас 128 ед. ×4; старые UV — те же пиксели)
                              cult_leader_glowmask.png, cult_leader_soul_mode_glowmask.png (эмиссив: глаза, медальон, угли по подолу)
                              cult_leader_flame.png (64×512, 8 кадров по вертикали — как tyros_flame 16×128)
  geo/entity/fire_cultist.geo.json + textures/entity/cult_leader/fire_cultist.png, fire_cultist_glowmask.png — облик огненных культистов
  textures/gui/sprites/boss_bars/cult_leader_bossbar.png (192×36, формат tyros_bossbar), textures/gui/title/cult_leader_{ru,en}.png
  textures/sigil/mellisto_verdict.png, cult_flame_tongue.png, cult_scorch_ring.png, mote_ash_flake.png; sigils/cult_*.json
  fx/styles/cult_leader.json; fx/cult_leader_*.json, fire_cultist_*.json; textures/mob_effect/mellisto_verdict.png
  lang (ru_ru/en_us), sounds.json (события cult_leader.* — на файлах Iron's/ванили, music.cult_leader — заглушка)

Запуск:  python3 tools/gen_cult_leader.py [--shots] [--html]
  --shots  проверочные кадры docs/media/t26_*.jpg (Playwright + three.js; --three путь/three.min.js — локальный three r128)
  --html   tools/cult_leader_preview.html (интерактивное превью: модель, все анимации Iron's, облик «души»)
"""
import json
import math
import os
import random
import sys
import zipfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
JAR = os.path.join(ROOT, 'libs', 'irons_spellbooks-1.20.1-3.16.1.jar')
I = 'assets/irons_spellbooks/'
TEX = 'textures/entity/cult_leader/'
K = 4                        # пикселей текстуры на единицу UV
WRITTEN = []


def jar(path):
    with zipfile.ZipFile(JAR) as z:
        return z.read(path)


def jar_img(path):
    import io
    return Image.open(io.BytesIO(jar(path))).convert('RGBA')


def jar_json(path):
    return json.loads(jar(path).decode('utf-8'))


def out(rel):
    p = os.path.join(A, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    WRITTEN.append(rel)
    return p


def write_json(rel, obj, indent=1):
    with open(out(rel), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
        f.write('\n')


def hx(c, a=255):
    c = c.lstrip('#')
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


# ================================================================== box UV → грани
def box_faces(c):
    """Грани куба с box UV (как Blockbench/GeckoLib): {грань: (u, v, w, h)} в единицах атласа, w/h могут быть < 0 (зеркально)."""
    u, v = c['uv']
    w, h, d = [math.floor(s + 1e-6) if s >= 1 else s for s in c['size']]
    return {'east': (u, v + d, d, h), 'north': (u + d, v + d, w, h), 'west': (u + d + w, v + d, d, h),
            'south': (u + 2 * d + w, v + d, w, h), 'up': (u + d + w, v + d, -w, -d), 'down': (u + d + 2 * w, v, -w, d)}


def face_rects(geo):
    """Все прямоугольники граней атласа: [(x0, y0, x1, y1, кость, грань)] в единицах UV (нормализованные)."""
    res = []
    for b in geo['minecraft:geometry'][0]['bones']:
        for c in b.get('cubes', []):
            uv = c.get('uv')
            if isinstance(uv, list):
                fs = box_faces(c)
                tag = tuple(uv)
            elif isinstance(uv, dict) and uv:
                fs = {k: (f['uv'][0], f['uv'][1], f['uv_size'][0], f['uv_size'][1]) for k, f in uv.items()}
                tag = None
            else:
                continue
            for k, (x, y, w, h) in fs.items():
                x0, x1 = sorted((x, x + w))
                y0, y1 = sorted((y, y + h))
                if x1 - x0 >= 0.99 and y1 - y0 >= 0.99:
                    res.append((x0, y0, x1, y1, b['name'], k, tag))
    return res


# ================================================================== палитра и пиксель-арт ×4
def family(rgb):
    r, g, b = [x / 255 for x in rgb[:3]]
    mx, mn = max(r, g, b), min(r, g, b)
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    sat = 0 if mx == 0 else (mx - mn) / mx
    if lum < 0.10:
        return 'black'
    if sat < 0.22:
        return 'neutral'
    hue = 0.0
    if mx == r:
        hue = ((g - b) / (mx - mn)) % 6 / 6
    elif mx == g:
        hue = ((b - r) / (mx - mn) + 2) / 6
    else:
        hue = ((r - g) / (mx - mn) + 4) / 6
    return 'red' if (hue < 0.035 or hue > 0.94) else 'warm'


class Palette:
    """Палитра исходной текстуры по семействам (ткань/металл/чернь/золото); ступени — исходные цвета + середины соседних тонов."""

    def __init__(self, img):
        a = np.asarray(img)
        cols = {tuple(int(x) for x in p[:3]) for p in a.reshape(-1, 4) if p[3] > 0}
        self.fam = {}
        groups = {}
        for c in cols:
            f = family(c)
            groups.setdefault(f, []).append(c)
        self.steps = {}
        for f, cs in groups.items():
            cs.sort(key=lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2])
            st = [cs[0]]
            for c in cs[1:]:
                p = st[-1]
                if sum(abs(c[i] - p[i]) for i in range(3)) > 24:     # промежуточный тон между соседями
                    st.append(tuple((c[i] + p[i]) // 2 for i in range(3)))
                st.append(c)
            self.steps[f] = st
        self.index = {}
        for f, st in self.steps.items():
            for i, c in enumerate(st):
                self.index[c] = (f, i)

    def shift(self, c, d):
        f, i = self.index.get(tuple(c[:3]), (None, None))
        if f is None:
            return c
        st = self.steps[f]
        return st[max(0, min(len(st) - 1, i + d))]

    def nearest(self, rgb, fam=None):
        best, bd = None, 1e9
        for f, st in self.steps.items():
            if fam and f != fam:
                continue
            for c in st:
                dd = sum((c[i] - rgb[i]) ** 2 for i in range(3))
                if dd < bd:
                    best, bd = c, dd
        return best


def scale2x(a):
    """EPX/Scale2x на массиве uint32 (h, w) — без новых цветов."""
    p = np.pad(a, 1, mode='edge')
    B, D, E, F, H = p[:-2, 1:-1], p[1:-1, :-2], p[1:-1, 1:-1], p[1:-1, 2:], p[2:, 1:-1]
    c = (B != H) & (D != F)
    e0 = np.where(c & (B == D), D, E)
    e1 = np.where(c & (B == F), F, E)
    e2 = np.where(c & (D == H), D, E)
    e3 = np.where(c & (H == F), F, E)
    h, w = a.shape
    o = np.empty((h * 2, w * 2), a.dtype)
    o[0::2, 0::2], o[0::2, 1::2], o[1::2, 0::2], o[1::2, 1::2] = e0, e1, e2, e3
    return o


def pack(img):
    a = np.asarray(img).astype(np.uint32)
    return (a[..., 0] << 24) | (a[..., 1] << 16) | (a[..., 2] << 8) | a[..., 3]


def unpack(p):
    return np.stack([(p >> 24) & 255, (p >> 16) & 255, (p >> 8) & 255, p & 255], -1).astype(np.uint8)


def hires(atlas, rects, pal, seed, cloth_folds=True):
    """atlas (RGBA, единицы UV) → ×4: Scale2x×2 по каждой грани отдельно (без протекания соседних граней), затем фактура по семействам:
    ткань — саржа, нити, мягкие складки; металл/кость — блик верхней кромки, тень нижней, царапины, заклёпки; на всех — кромка граней."""
    W, H = atlas.size
    big = atlas.resize((W * K, H * K), Image.NEAREST)
    bp = pack(big)
    ap = pack(atlas)
    for (x0, y0, x1, y1, *_r) in rects:
        X0, Y0, X1, Y1 = int(math.floor(x0)), int(math.floor(y0)), int(math.ceil(x1)), int(math.ceil(y1))
        sub = ap[Y0:Y1, X0:X1]
        if sub.size == 0:
            continue
        bp[Y0 * K:Y1 * K, X0 * K:X1 * K] = scale2x(scale2x(sub))
    img = unpack(bp)
    rng = random.Random(seed)
    out_ = img.copy()
    for ri, (x0, y0, x1, y1, bone, face, *_t) in enumerate(rects):
        X0, Y0, X1, Y1 = int(round(x0 * K)), int(round(y0 * K)), int(round(x1 * K)), int(round(y1 * K))
        w, h = X1 - X0, Y1 - Y0
        if w < 2 or h < 2:
            continue
        r2 = random.Random(seed * 1000 + ri)
        ph = [r2.random() * 6.28 for _ in range(4)]
        fold_n = r2.choice([1.5, 2, 2.5, 3])
        for y in range(h):
            for x in range(w):
                px = img[Y0 + y, X0 + x]
                if px[3] == 0:
                    continue
                c = tuple(int(v) for v in px[:3])
                f = pal.index.get(c, (None,))[0]
                if f is None:
                    continue
                d = 0
                hsh = ((X0 + x) * 73856093 ^ (Y0 + y) * 19349663 ^ seed * 83492791) & 0xFFFF
                nz = hsh / 65535.0
                edge = min(x, y, w - 1 - x, h - 1 - y)
                if f == 'red':
                    if (x + y * 2) % 5 == 0 and nz < 0.55:
                        d -= 1                                                   # саржа
                    if nz > 0.965:
                        d += 1                                                   # светлая нить
                    if cloth_folds and face in ('north', 'south', 'east', 'west') and h > 12:
                        s = math.sin(x / w * math.pi * fold_n * 2 + ph[0] + 0.25 * math.sin(y / h * 2.5 + ph[1]))
                        d += 1 if s > 0.985 else (-1 if s < -0.97 else 0)       # тонкие складки вдоль ткани
                elif f in ('neutral', 'warm'):
                    if y == 0 or (y == 1 and nz < 0.5):
                        d += 1                                                   # блик верхней кромки
                    if y >= h - 1:
                        d -= 1
                    if nz < 0.035:
                        d += 1 if nz < 0.018 else -1                            # точечная выщербина
                elif f == 'black':
                    if nz > 0.985:
                        d += 1
                if edge == 0 and f != 'black':
                    d -= 1                                                       # тёмная кромка грани: объём читается
                if d:
                    out_[Y0 + y, X0 + x, :3] = pal.shift(c, d)
        # царапины и заклёпки на крупных металлических гранях
        if w >= 6 * K and h >= 4 * K:
            cx, cy = X0 + w // 2, Y0 + h // 2
            cc = tuple(int(v) for v in img[cy, cx, :3])
            if pal.index.get(cc, (None,))[0] in ('neutral', 'warm') and img[cy, cx, 3]:
                for _ in range(max(1, w * h // 900)):
                    sx, sy = X0 + r2.randrange(2, w - 2), Y0 + r2.randrange(2, h - 2)
                    ln, dx = r2.randrange(3, 7), r2.choice((-1, 1))
                    for k in range(ln):
                        xx, yy = sx + k * dx, sy + k // 2
                        if X0 < xx < X1 - 1 and Y0 < yy < Y1 - 1 and img[yy, xx, 3]:
                            c0 = tuple(int(v) for v in out_[yy, xx, :3])
                            out_[yy, xx, :3] = pal.shift(c0, 1)
                for (rx, ry) in ((X0 + 3, Y0 + 3), (X1 - 4, Y0 + 3), (X0 + 3, Y1 - 4), (X1 - 4, Y1 - 4)):
                    if img[ry, rx, 3] and pal.index.get(tuple(int(v) for v in img[ry, rx, :3]), (None,))[0] in ('neutral', 'warm'):
                        c0 = tuple(int(v) for v in img[ry, rx, :3])
                        out_[ry, rx, :3] = pal.shift(c0, 2)
                        out_[ry + 1, rx + 1, :3] = pal.shift(c0, -1)
    return Image.fromarray(out_, 'RGBA')


# ================================================================== модель «Главы Культа»
class UVAlloc:
    """Раскладка новых граней в свободной части атласа 128×128 (правая полоса x ≥ 96 и нижняя y ≥ 96)."""

    def __init__(self):
        self.shelves = [[96, 0, 128, 96, 96, 0, 0], [0, 96, 128, 128, 0, 96, 0]]   # x0, y0, x1, y1, курсор x, y, высота полки

    def take(self, w, h):
        w, h = max(1, math.ceil(w)), max(1, math.ceil(h))
        for s in self.shelves:
            x0, y0, x1, y1, cx, cy, sh = s
            if cx + w > x1:
                cx, cy, sh = x0, cy + sh, 0
            if cy + h <= y1 and cx + w <= x1:
                s[4], s[5], s[6] = cx + w, cy, max(sh, h)
                return cx, cy
        raise RuntimeError('UV: нет места под %sx%s' % (w, h))


NEW_FACES = []        # (bone, имя детали, грань, x, y, w, h) — для раскраски


def cube(alloc, bone, name, origin, size, faces=('north', 'south', 'east', 'west', 'up', 'down'), pivot=None, rotation=None, inflate=None):
    """Куб с per-face UV; грани получают свои прямоугольники в свободной части атласа."""
    w, h, d = size
    dims = {'north': (w, h), 'south': (w, h), 'east': (d, h), 'west': (d, h), 'up': (w, d), 'down': (w, d)}
    uv = {}
    for f in faces:
        fw, fh = dims[f]
        x, y = alloc.take(fw, fh)
        uv[f] = {'uv': [x, y], 'uv_size': [fw, fh]}
        NEW_FACES.append((bone, name, f, x, y, max(1, math.ceil(fw)), max(1, math.ceil(fh))))
    c = {'origin': origin, 'size': size, 'uv': uv}
    if pivot:
        c['pivot'] = pivot
    if rotation:
        c['rotation'] = rotation
    if inflate:
        c['inflate'] = inflate
    return c


def build_model():
    geo = jar_json(I + 'geo/tyros.geo.json')
    g = geo['minecraft:geometry'][0]
    g['description'].update({'identifier': 'geometry.cult_leader', 'texture_width': 128, 'texture_height': 128,
                             'visible_bounds_width': 6, 'visible_bounds_height': 6, 'visible_bounds_offset': [0, 2.5, 0]})
    bones = {b['name']: b for b in g['bones']}
    al = UVAlloc()
    NEW_FACES.clear()

    def add(bone, c):
        bones[bone].setdefault('cubes', []).append(c)

    # венец на капюшоне: обруч по бокам капюшона + 7 зубцов спереди (наклон капюшона −12.5° — те же pivot/rotation)
    hp, hr = [2.5, 32.25, -5.5], [-12.5, 0, 0]
    add('armor_head', cube(al, 'armor_head', 'crown_band', [-4.75, 33.0, -5.75], [9.5, 1.25, 10.5], ('north', 'south', 'east', 'west'),
                           pivot=hp, rotation=hr))
    for i, (x, hgt) in enumerate(((-4.3, 1.75), (-2.45, 2.75), (-0.5, 3.75), (1.7, 2.75), (3.55, 1.75))):
        add('armor_head', cube(al, 'armor_head', 'crown_tine_%d' % i, [x, 34.25, -5.85], [0.75, hgt, 0.75],
                               ('north', 'south', 'east', 'west', 'up'), pivot=hp, rotation=hr))
        add('armor_head', cube(al, 'armor_head', 'crown_tip_%d' % i, [x + 0.19, 34.25 + hgt, -5.66], [0.375, 0.75, 0.375],
                               ('north', 'south', 'east', 'west', 'up'), pivot=hp, rotation=hr))
    # медальон-печать на груди (поверх рёбер доспеха)
    add('armor_chest', cube(al, 'armor_chest', 'medallion', [-1.75, 19.5, -3.15], [3.5, 3.5, 0.6]))
    add('armor_chest', cube(al, 'armor_chest', 'medallion_chain', [-2.75, 23.0, -2.95], [5.5, 0.6, 0.4], ('north',)))
    # амулеты на поясе: цепочка + пластина, по бокам бёдер
    for s, nm in ((-1, 'r'), (1, 'l')):
        x = 4.55 if s > 0 else -5.55
        add('torso', cube(al, 'torso', 'amulet_chain_' + nm, [x + 0.25, 10.5, -1.6], [0.5, 3.5, 0.5], ('north', 'south', 'east', 'west')))
        add('torso', cube(al, 'torso', 'amulet_plate_' + nm, [x - 0.25, 8.0, -1.85], [1.5, 2.5, 1.0]))
    # шипы наплечников
    add('armor_right_arm', cube(al, 'armor_right_arm', 'spike_r1', [-9.5, 26.0, -1.0], [1.5, 3.5, 1.5], pivot=[-8.75, 26, -0.25], rotation=[0, 0, 25]))
    add('armor_right_arm', cube(al, 'armor_right_arm', 'spike_r2', [-9.0, 26.0, 1.0], [1.0, 2.5, 1.0], pivot=[-8.5, 26, 1.5], rotation=[-15, 0, 20]))
    add('armor_left_arm', cube(al, 'armor_left_arm', 'spike_l1', [8.0, 27.0, -1.25], [1.5, 3.5, 1.5], pivot=[8.75, 27, -0.5], rotation=[0, 0, -30]))
    add('armor_left_arm', cube(al, 'armor_left_arm', 'spike_l2', [7.0, 27.5, 0.75], [1.0, 2.5, 1.0], pivot=[7.5, 27.5, 1.25], rotation=[-15, 0, -25]))
    # рваный плащ — новая кость (дочь torso): код может качать её (см. письмо), анимации Iron's её не трогают
    g['bones'].insert(g['bones'].index(bones['armorBipedBody']), {
        'name': 'cape', 'parent': 'torso', 'pivot': [0, 26, 2.75], 'rotation': [6, 0, 0],
        'cubes': [cube(al, 'cape', 'cape', [-5, 7, 2.6], [10, 19, 0.5], ('north', 'south', 'east', 'west', 'up'))]})
    write_json('geo/entity/cult_leader.geo.json', geo, indent=2)
    return geo


# ---------------------------------------------------------------- раскраска новых деталей (в единицах атласа, цвета исходной палитры)
def paint_new(atl, soul=False):
    """Новые грани. Цвета — только из палитры Тироса (в облике души — из палитры tyros_soul_mode)."""
    d = ImageDraw.Draw(atl)
    if not soul:
        RED, RED_D, RED_L, RED_H = '#792426', '#6a1618', '#883335', '#8f3a3c'
        M0, M1, M2, M3, M4, M5 = '#151515', '#241f20', '#322727', '#372c2b', '#4d403d', '#62514e'
        M6, M7, M8 = '#7a6a68', '#958a89', '#958a89'
    else:
        RED, RED_D, RED_L, RED_H = '#26252b', '#1b1415', '#393737', '#3e3e3e'          # палитра tyros_soul_mode
        M0, M1, M2, M3, M4, M5 = '#151515', '#491b10', '#733c25', '#9c5e2c', '#b9892e', '#d6af39'
        M6, M7, M8 = '#d6af39', '#e8e895', '#e8e895'
    rng = random.Random(26 + soul)
    for bone, name, f, x, y, w, h in NEW_FACES:
        box = [x, y, x + w - 1, y + h - 1]
        if name == 'cape':
            if f in ('north', 'south'):
                for yy in range(h):
                    for xx in range(w):
                        c = RED if (xx + yy // 3) % 4 else RED_D
                        if yy < 2:
                            c = RED_L
                        if xx in (0, w - 1):
                            c = RED_D
                        d.point((x + xx, y + yy), fill=c)
                if f == 'south':                                                    # знак культа сзади: язык пламени с оком
                    E_ = M3 if not soul else M4
                    for (ex, ey) in ((4, 3), (5, 3), (4, 4), (5, 4), (3, 5), (6, 5), (3, 6), (6, 6), (2, 7), (7, 7), (2, 8), (7, 8),
                                     (2, 9), (7, 9), (3, 10), (6, 10), (4, 11), (5, 11), (5, 2)):
                        d.point((x + ex, y + ey), fill=E_)
                    for (ex, ey) in ((4, 8), (5, 8)):
                        d.point((x + ex, y + ey), fill=RED_H if not soul else M6)
                # рваный подол — отсечка альфы
                for xx in range(w):
                    cut = rng.choice((0, 1, 1, 2, 3, 2, 4, 1))
                    for k in range(cut):
                        d.point((x + xx, y + h - 1 - k), fill=(0, 0, 0, 0))
                    if cut < h:
                        d.point((x + xx, y + h - 1 - cut), fill=RED_D)
                for _ in range(3):                                                  # прорехи
                    hx_, hy = rng.randrange(1, w - 2), rng.randrange(8, h - 4)
                    d.point((x + hx_, y + hy), fill=(0, 0, 0, 0))
            else:
                d.rectangle(box, fill=RED_D)
        elif name == 'crown_band':
            d.rectangle(box, fill=M3)
            for xx in range(w):
                d.point((x + xx, y), fill=M5 if xx % 3 else M6)
                if xx % 4 == 2:
                    d.point((x + xx, y + h - 1), fill=M1)
        elif name.startswith('crown_t'):
            d.rectangle(box, fill=M4)
            if f in ('north', 'south'):
                d.line([x, y, x, y + h - 1], fill=M6)
                d.point((x, y), fill=M7)
            if f == 'up':
                d.rectangle(box, fill=M6)
        elif name == 'hood_tail':
            d.rectangle(box, fill=RED)
            for xx in range(w):
                for yy in range(h):
                    if (xx + yy) % 3 == 0:
                        d.point((x + xx, y + yy), fill=RED_D)
            if f in ('north', 'south', 'east', 'west'):
                d.line([x, y + h - 1, x + w - 1, y + h - 1], fill=RED_D)
        elif name == 'medallion':
            d.rectangle(box, fill=M3)
            if f == 'north':                                                        # печать: кольцо, в нём око-пламя
                d.rectangle(box, fill=M2)
                d.rectangle([x, y, x + w - 1, y], fill=M6)
                d.point((x + 1, y + 1), fill=M5)
                d.point((x + 2, y + 1), fill=M5)
                d.point((x + 1, y + 2), fill=RED_H if not soul else M7)
                d.point((x + 2, y + 2), fill=RED_H if not soul else M7)
                d.rectangle([x, y + h - 1, x + w - 1, y + h - 1], fill=M1)
            else:
                d.line([x, y, x + w - 1, y], fill=M5)
        elif name == 'medallion_chain':
            for xx in range(w):
                d.point((x + xx, y), fill=M5 if xx % 2 else M2)
        elif name.startswith('amulet_chain'):
            for yy in range(h):
                d.line([x, y + yy, x + w - 1, y + yy], fill=M5 if yy % 2 else M2)
        elif name.startswith('amulet_plate'):
            d.rectangle(box, fill=M4)
            if f == 'north':
                d.rectangle(box, fill=M3)
                d.point((x, y), fill=M6)
                d.point((x + w - 1, y + h - 1), fill=M1)
                if w >= 2 and h >= 3:
                    d.point((x + 1, y + 1), fill=RED_H if not soul else M7)
        elif name.startswith('spike'):
            d.rectangle(box, fill=M3)
            if f in ('north', 'east', 'west', 'south'):
                d.line([x, y, x, y + h - 1], fill=M5)
                d.point((x, y), fill=M6)
                d.line([x + w - 1, y, x + w - 1, y + h - 1], fill=M1)
            if f == 'up':
                d.rectangle(box, fill=M6)


def clear_soul_mouth(atl, geo, k=1):
    """Облик души: на передних гранях кубов кости head перекрашивает золотые/рыжие пиксели (полоса у рта из tyros_soul_mode Iron's)
    в тёмный тон лица — лицо остаётся пустой тьмой (владелец 20.11)."""
    px = atl.load()
    g = geo['minecraft:geometry'][0] if 'minecraft:geometry' in geo else geo
    for b in g['bones']:
        if b['name'] != 'head':
            continue
        for c in b.get('cubes', []):
            if not isinstance(c.get('uv'), list):
                continue
            sx, sy, sz = c['size']
            u, v = c['uv'][0] + sz, c['uv'][1] + sz
            for x in range(int(u * k), int((u + sx) * k)):
                for y in range(int(v * k), int((v + sy) * k)):
                    r, gg, bb, a = px[x, y]
                    if a and r > 100 and r - bb > 60:
                        px[x, y] = (28, 20, 22, a)



def paint_eyes(atl, soul=False):
    """Тёмное «лицо» в капюшоне (внутренний куб головы, uv 40,80, грань north 48..56 × 88..96): тлеющие щели глаз."""
    d = ImageDraw.Draw(atl)
    c = '#6a1618' if not soul else '#3c4141'
    for x in (49, 50, 53, 54):
        d.point((x, 91), fill=c)


# ---------------------------------------------------------------- огонь: палитра tyros_flame
def flame_palette():
    im = jar_img(I + 'textures/entity/fire_boss/tyros_flame.png')
    cols = sorted({tuple(int(v) for v in p[:3]) for p in np.asarray(im).reshape(-1, 4) if p[3] > 0}, key=lambda c: sum(c))
    return cols


def glow_paint(size, spots):
    """Глоумаска: прозрачная, светятся только перечисленные пятна (x, y, цвет, радиус) в пикселях 512."""
    im = Image.new('RGBA', size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for (x, y, c, r) in spots:
        if r <= 0.5:
            d.point((x, y), fill=c)
        else:
            d.ellipse([x - r, y - r, x + r, y + r], fill=c)
    return im


def textures_leader(geo):
    base = jar_img(I + 'textures/entity/fire_boss/tyros.png')
    soul = jar_img(I + 'textures/entity/fire_boss/tyros_soul_mode.png')
    rects = face_rects(geo)
    fl = flame_palette()
    hot, mid, deep = fl[-1], fl[len(fl) * 2 // 3], fl[len(fl) // 3]
    res = {}
    for nm, src, is_soul in (('cult_leader', base, False), ('cult_leader_soul_mode', soul, True)):
        atl = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
        atl.paste(src, (0, 0))
        paint_new(atl, is_soul)
        if not is_soul:                               # в облике души лицо — пустая тьма, как у Iron's (владелец: без золота на лице)
            paint_eyes(atl, is_soul)
        pal = Palette(atl)
        big = hires(atl, rects, pal, 26 if not is_soul else 27)
        if is_soul:
            big = big.copy()
            clear_soul_mouth(big, geo, K)             # владелец 20.11: убрать «золотую часть» в области рта (она из tyros_soul_mode Iron's)
        big.save(out(TEX + nm + '.png'))
        res[nm] = big
        # --- свечение
        spots = []
        # глаза: щели 2×1 ед. → в 512
        for ex in ((49, 53) if not is_soul else ()):
            for xx in range(ex * K, (ex + 2) * K):
                for yy in range(91 * K + 1, 92 * K - 1):
                    spots.append((xx, yy, hot + (255,) if xx % 4 in (1, 2) else mid + (255,), 0))
        # медальон: око-пламя
        for bone, name, f, x, y, w, h in NEW_FACES:
            if name == 'medallion' and f == 'north':
                spots += [(x * K + 6 + i, y * K + 6 + j, deep + (255,), 0) for i in range(3) for j in range(2)]
                spots += [(x * K + 7, y * K + 6, mid + (255,), 0)]
            if name.startswith('amulet_plate') and f == 'north':
                spots += [(x * K + 5, y * K + 5, deep + (255,), 0.6)]
            if name.startswith('crown_tip') and f in ('north', 'up'):
                spots += [(x * K + 1, y * K + 1, deep + (255,), 0.6)]
        gm = glow_paint(big.size, spots)
        a = np.asarray(gm).copy()
        b = np.asarray(big)
        # угли по подолу робы и плаща: редкие тлеющие точки на нижних 1–1.5 ед. граней ткани ног/плаща
        rng = random.Random(260 + is_soul)
        for (x0, y0, x1, y1, bone, face, *_t) in rects:
            if face in ('up', 'down'):
                continue
            if bone in ('right_leg', 'left_leg') or (bone == 'cape'):
                Y1 = int(y1 * K)
                for X in range(int(x0 * K), int(x1 * K)):
                    for Y in range(Y1 - 6, Y1):
                        if b[Y, X, 3] and family(b[Y, X, :3]) in ('red', 'neutral', 'black') and rng.random() < 0.10 * (1 - (Y1 - Y) / 7):
                            c = hot if rng.random() < 0.3 else (mid if rng.random() < 0.6 else deep)
                            a[Y, X] = c + (255,)
        if is_soul:                                   # облик души: золото светится вполсилы
            gold = (b[..., 3] > 0) & (b[..., 0].astype(int) > 150) & (b[..., 1].astype(int) > 100) & (b[..., 2] < 140)
            a[gold] = np.concatenate([(b[gold][:, :3] * 0.55).astype(np.uint8), np.full((gold.sum(), 1), 255, np.uint8)], 1)
        Image.fromarray(a, 'RGBA').save(out(TEX + nm + '_glowmask.png'))
    # пламя головы: 16×128 → 64×512, Scale2x×2 по каждому кадру + мерцающие «языки» тех же цветов
    fsrc = jar_img(I + 'textures/entity/fire_boss/tyros_flame.png')
    fp = pack(fsrc)
    frames = [scale2x(scale2x(fp[i * 16:(i + 1) * 16])) for i in range(8)]
    big = unpack(np.concatenate(frames, 0))
    fpal = Palette(fsrc)
    rng = random.Random(9)
    o = big.copy()
    for y in range(big.shape[0]):
        for x in range(big.shape[1]):
            if big[y, x, 3] and rng.random() < 0.08:
                o[y, x, :3] = fpal.shift(tuple(int(v) for v in big[y, x, :3]), rng.choice((-1, 1)))
    Image.fromarray(o, 'RGBA').save(out(TEX + 'cult_leader_flame.png'))
    return res


# ================================================================== огненный культист
def build_cultist():
    geo = jar_json(I + 'geo/abstract_casting_mob.geo.json')
    g = geo['minecraft:geometry'][0]
    g['description'].update({'identifier': 'geometry.fire_cultist', 'texture_width': 128, 'texture_height': 128})
    bones = {b['name']: b for b in g['bones']}
    al = UVAlloc()
    al.shelves = [[64, 0, 128, 64, 64, 0, 0], [0, 64, 128, 128, 0, 64, 0]]
    NEW_FACES.clear()

    def add(bone, c):
        bones[bone].setdefault('cubes', []).append(c)

    # капюшон: большой короб вокруг головы с проёмом спереди (грань north — рамка с прозрачным окном) + острый хвост
    add('head', cube(al, 'head', 'hood', [-4.5, 23.7, -4.7], [9.0, 8.8, 9.2]))
    add('head', cube(al, 'head', 'hood_peak', [-1.5, 29.0, 3.6], [3.0, 3.0, 2.5], pivot=[0, 32.4, 4.4], rotation=[50, 0, 0]))
    # мантия-оплечье и короткий плащ
    add('torso', cube(al, 'torso', 'mantle', [-4.8, 19.0, -2.6], [9.6, 5.2, 5.2], ('north', 'south', 'east', 'west', 'up')))
    add('torso', cube(al, 'torso', 'sash', [-1.25, 4.5, -2.45], [2.5, 8.0, 0.4], ('north',)))
    g['bones'].insert(g['bones'].index(bones['armorBipedBody']), {
        'name': 'cape', 'parent': 'torso', 'pivot': [0, 24, 2.4], 'rotation': [5, 0, 0],
        'cubes': [cube(al, 'cape', 'cape', [-4.5, 5.5, 2.3], [9, 18.5, 0.5], ('north', 'south', 'east', 'west', 'up'))]})
    write_json('geo/entity/fire_cultist.geo.json', geo, indent=2)
    return geo


def textures_cultist(geo):
    RED, RED_D, RED_L, RED_H = '#792426', '#6a1618', '#883335', '#8f3a3c'
    M1, M2, M3, M4, M5, M6 = '#241f20', '#322727', '#372c2b', '#4d403d', '#62514e', '#7a6a68'
    BLK, BLK2 = '#151515', '#1f1f1f'
    atl = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(atl)
    rects = face_rects(geo)

    def faces_of(u, v):
        return {r[5]: r for r in rects if r[6] == (u, v)}

    def fill(r, c):
        d.rectangle([int(r[0]), int(r[1]), int(r[2]) - 1, int(r[3]) - 1], fill=c)

    def robe(r, belt=None, hem=True, stripe=False):
        x0, y0, x1, y1 = int(r[0]), int(r[1]), int(r[2]), int(r[3])
        for y in range(y0, y1):
            for x in range(x0, x1):
                c = RED if (x + (y - y0) // 3) % 5 else RED_D
                if y == y0:
                    c = RED_L
                d.point((x, y), fill=c)
        if stripe:
            cx = (x0 + x1) // 2
            d.line([cx - 1, y0, cx - 1, y1 - 1], fill=BLK2)
            d.line([cx, y0, cx, y1 - 1], fill=BLK2)
        if belt is not None:
            d.line([x0, y0 + belt, x1 - 1, y0 + belt], fill=M3)
            d.line([x0, y0 + belt + 1, x1 - 1, y0 + belt + 1], fill=M2)
        if hem:
            d.line([x0, y1 - 1, x1 - 1, y1 - 1], fill=M2)
            for x in range(x0, x1, 2):
                d.point((x, y1 - 2), fill=RED_H)

    # голова (uv 0,0): тёмное лицо в тени капюшона; слой шляпы (32,0) остаётся пустым — капюшон отдельный куб
    for f, r in faces_of(0, 0).items():
        fill(r, BLK if f == 'north' else RED_D)
    nr = faces_of(0, 0)['north']
    for x in (1, 2, 5, 6):
        d.point((int(nr[0]) + x, int(nr[1]) + 4), fill=RED_D)
    # торс (16,16): роба, чёрная полоса, пояс; слой куртки (16,32): знак культа на груди
    for f, r in faces_of(16, 16).items():
        if f in ('up', 'down'):
            fill(r, RED_D)
        else:
            robe(r, belt=8, hem=False, stripe=(f == 'north'))
    r = faces_of(16, 32)['north']
    x0, y0 = int(r[0]), int(r[1])
    for (x, y, c) in ((3, 1, M5), (4, 1, M5), (2, 2, M4), (5, 2, M4), (2, 3, M4), (5, 3, M4), (3, 3, RED_H), (4, 3, RED_H), (3, 4, M4), (4, 4, M4)):
        d.point((x0 + x, y0 + y), fill=c)
    # руки (40,16 / 32,48): рукава, наручи, перчатки; слой рукава (40,32) правой руки — раструб
    for uv in ((40, 16), (32, 48)):
        for f, r in faces_of(*uv).items():
            if f in ('up', 'down'):
                fill(r, RED_D if f == 'up' else BLK)
                continue
            robe(r, hem=False)
            x0, x1, y1 = int(r[0]), int(r[2]), int(r[3])
            d.line([x0, y1 - 4, x1 - 1, y1 - 4], fill=M4)
            d.rectangle([x0, y1 - 3, x1 - 1, y1 - 1], fill=BLK2)
    for f, r in faces_of(40, 32).items():
        if f not in ('up', 'down'):
            x0, x1, y1 = int(r[0]), int(r[2]), int(r[3])
            d.rectangle([x0, y1 - 6, x1 - 1, y1 - 5], fill=RED_D)
            d.line([x0, y1 - 5, x1 - 1, y1 - 5], fill=M4)
    # ноги (0,16 / 16,48): подол робы, сапоги; слой штанин (0,32 / 0,48): полы с вышивкой и окантовкой
    for uv in ((0, 16), (16, 48)):
        for f, r in faces_of(*uv).items():
            if f in ('up', 'down'):
                fill(r, BLK)
                continue
            robe(r)
            d.rectangle([int(r[0]), int(r[3]) - 2, int(r[2]) - 1, int(r[3]) - 1], fill=BLK2)
    for uv in ((0, 32), (0, 48)):
        for f, r in faces_of(*uv).items():
            if f in ('up', 'down'):
                continue
            x0, y0, x1, y1 = int(r[0]), int(r[1]), int(r[2]), int(r[3])
            if f == 'north':
                for y in range(y0, y1 - 2):
                    d.point((x0, y), fill=M3)
                    d.point((x1 - 1, y), fill=M3)
            for x in range(x0, x1):
                d.point((x, y1 - 4), fill=RED_H if x % 2 else M4)
    # новые детали
    rng = random.Random(77)
    for bone, name, f, x, y, w, h in NEW_FACES:
        box = [x, y, x + w - 1, y + h - 1]
        if name == 'hood':
            d.rectangle(box, fill=RED)
            for yy in range(h):
                for xx in range(w):
                    if (xx + yy * 2) % 5 == 0:
                        d.point((x + xx, y + yy), fill=RED_D)
            if f == 'north':                                                       # проём лица
                d.rectangle([x + 2, y + 2, x + w - 3, y + h - 1], fill=(0, 0, 0, 0))
                d.rectangle([x + 1, y + 1, x + w - 2, y + 1], fill=RED_D)
                d.line([x + 1, y + 2, x + 1, y + h - 1], fill=RED_D)
                d.line([x + w - 2, y + 2, x + w - 2, y + h - 1], fill=RED_D)
                d.point((x + 2, y + 2), fill=RED_D)
                d.point((x + w - 3, y + 2), fill=RED_D)
            if f == 'down':
                d.rectangle([x + 1, y + 1, x + w - 2, y + h - 2], fill=(0, 0, 0, 0))
            if f in ('east', 'west', 'north', 'south'):
                d.line([x, y + h - 1, x + w - 1, y + h - 1], fill=M3)
        elif name == 'hood_peak':
            d.rectangle(box, fill=RED_D if f != 'up' else RED)
        elif name == 'mantle':
            d.rectangle(box, fill=RED_D)
            d.line([x, y + h - 1, x + w - 1, y + h - 1], fill=M4)
            d.line([x, y + h - 2, x + w - 1, y + h - 2], fill=M2)
            if f == 'north':
                d.rectangle([x + w // 2 - 1, y, x + w // 2, y + h - 1], fill=BLK2)
        elif name == 'sash':
            d.rectangle(box, fill=BLK2)
            d.line([x, y, x + w - 1, y], fill=M4)
            d.point((x + 1, y + 3), fill=RED_H)
            for xx in range(w):
                if rng.random() < 0.6:
                    d.point((x + xx, y + h - 1), fill=(0, 0, 0, 0))
        elif name == 'cape':
            d.rectangle(box, fill=RED)
            if f in ('north', 'south'):
                for yy in range(h):
                    for xx in range(w):
                        if (xx + yy // 3) % 4 == 0:
                            d.point((x + xx, y + yy), fill=RED_D)
                for xx in range(w):
                    cut = rng.choice((0, 1, 2, 1, 3))
                    for k in range(cut):
                        d.point((x + xx, y + h - 1 - k), fill=(0, 0, 0, 0))
    pal = Palette(atl)
    big = hires(atl, rects, pal, 31)
    big.save(out(TEX + 'fire_cultist.png'))
    fl = flame_palette()
    hot, mid = fl[-1], fl[len(fl) * 2 // 3]
    spots = []
    nx, ny = int(nr[0]), int(nr[1])
    for ex in (1, 5):
        for xx in range((nx + ex) * K, (nx + ex + 2) * K):
            for yy in range((ny + 4) * K + 1, (ny + 5) * K - 1):
                spots.append((xx, yy, (hot if xx % 4 in (1, 2) else mid) + (255,), 0))
    gm = glow_paint(big.size, spots)
    a = np.asarray(gm).copy()
    b = np.asarray(big)
    rng = random.Random(311)
    for (x0, y0, x1, y1, bone, face, *_t) in rects:
        if face in ('up', 'down') or bone not in ('right_leg', 'left_leg', 'cape'):
            continue
        Y1 = int(y1 * K)
        for X in range(int(x0 * K), int(x1 * K)):
            for Y in range(Y1 - 5, Y1):
                if b[Y, X, 3] and rng.random() < 0.08:
                    a[Y, X] = (hot if rng.random() < 0.4 else mid) + (255,)
    Image.fromarray(a, 'RGBA').save(out(TEX + 'fire_cultist_glowmask.png'))


# ================================================================== main
def main():
    args = sys.argv[1:]
    if not os.path.exists(JAR):
        sys.exit('нет %s — запустите python3 tools/fetch_libs.py' % JAR)
    geo = build_model()
    textures_leader(geo)
    cg = build_cultist()
    textures_cultist(cg)
    import gen_cult_leader_fx as FX
    FX.run(sys.modules[__name__], args)
    print('\n'.join('  ' + w for w in WRITTEN))


if __name__ == '__main__':
    main()
