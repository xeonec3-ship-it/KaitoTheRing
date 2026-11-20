#!/usr/bin/env python3
"""
T30 — визуал босса «Эреб, Первый Предатель» («Глава 1 Ячейки Культа»). ТЗ: docs/specs/tasks/T30_ereb_boss.md.
Оригинал владельца — скин игрока docs/references/t30/ereb_*.jpg: светлые взъерошенные волосы, голубые глаза, чёрный камзол
с золотой отделкой (золотые «кресты» на рукавах, нагрудный узор, золотые полосы-застёжки, кайма по подолу).
Эталон качества — модель Главы Культа (docs/inbox/README.md, «Эталон моделей»): стиль Iron's/ванили, 1 тексель = 1/16 блока,
ручная пиксельная светотень без шума и сглаживания, чистый силуэт, объёмные детали брусками поверх каркаса мага Iron's.

Основа — каркас мага Iron's: geo/abstract_casting_mob.geo.json из jar (libs/irons_spellbooks-1.20.1-3.16.1.jar,
скачать: python3 tools/fetch_libs.py). Кости и их имена — как были (их двигает AbstractSpellCastingMobModel и анимации каста Iron's).
Атлас расширен 64 → 128: левый верхний квадрат 64×64 — раскладка скина игрока (скин владельца, перерисован вручную по пикселю
с фото), новые бруски — в свободной части атласа.

Пишет (src/main/resources/assets/pohsmp_core/):
  geo/entity/ereb.geo.json                       — модель (identifier geometry.ereb)
  textures/entity/ereb/ereb.png                  — текстура 128×128 (1 тексель = 1/16 блока)
  textures/entity/ereb/ereb_smile.png            — то же, лицо с улыбкой (финал: «Эреб улыбается»)
  textures/entity/ereb/ereb_glowmask.png         — свечение: радужки глаз, стекло броши и пряжек
  animations/entity/ereb.animation.json          — все анимации casting_animations.json Iron's (те же имена) + ereb_* (наши)
  models/item/ereb_rapier.json + textures/item/ereb_rapier_3d.png, ereb_rapier.png — рапира (3D в руке, плоская иконка в GUI)
Эффекты, полоса, титры, lang, кадры — tools/gen_ereb_fx.py (вызывается отсюда). Превью — tools/gen_ereb_render.py.

Запуск:  python3 tools/gen_ereb.py [--shots] [--html]
"""
import json
import math
import os
import sys
import zipfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
JAR = os.path.join(ROOT, 'libs', 'irons_spellbooks-1.20.1-3.16.1.jar')
I = 'assets/irons_spellbooks/'
TEX = 'textures/entity/ereb/'
WRITTEN = []


def jar(path):
    with zipfile.ZipFile(JAR) as z:
        return z.read(path)


def jar_json(path):
    return json.loads(jar(path).decode('utf-8'))


def jar_img(path):
    import io
    return Image.open(io.BytesIO(jar(path))).convert('RGBA')


def out(rel):
    p = os.path.join(A, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    WRITTEN.append(rel)
    return p


def write_json(rel, obj, indent=1, compact=False):
    with open(out(rel), 'w', encoding='utf-8', newline='\n') as f:
        if compact:
            json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=indent)
        f.write('\n')


def hx(c, a=255):
    c = c.lstrip('#')
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), a)


# ================================================================== палитра (ручные ступени, без промежуточного шума)
# Буквы — для пиксель-арта граней. '.' — прозрачно.
PAL = {
    # чёрное сукно камзола (холодный, чуть лиловый чёрный): a — глубокая тень … e — блик
    'a': '#0b0a0f', 'b': '#14121a', 'c': '#1d1a24', 'd': '#29252f', 'e': '#38333f',
    # золото отделки: o — тень … t — блик
    'o': '#704612', 'p': '#a46a1c', 'q': '#d0952a', 'r': '#eab33c', 's': '#f8d260', 't': '#fff2b0',
    # стекло (брошь, пряжки, гарда): x … Z
    'x': '#1f4a63', 'y': '#3d8fb5', 'z': '#8fd8f2', 'Z': '#e2fbff',
    # тёмно-серое сукно (штаны и подбой полы — как на скине)
    'u': '#17181a', 'v': '#212325', 'V': '#2c2f31', 'W': '#3a3e40',
    # кожа (1 — тень … 5 — блик)
    '1': '#c88a72', '2': '#e6ae94', '3': '#f4cdb6', '4': '#fbe0cf', '5': '#fff0e6',
    # волосы — светлое золото: A — тень … F — блик
    'A': '#b88a30', 'B': '#dcb048', 'C': '#efcd5c', 'D': '#f7de74', 'E': '#fdeb98', 'F': '#fff8d4',
    # глаза: w — белок, i — радужка (тёмная), j — радужка (светлая), k — блик/ресница, l — ресница (тень века), m — губы
    'w': '#e3ecf1', 'i': '#17506a', 'j': '#45b6d4', 'k': '#c7f1ff', 'l': '#5e4420', 'm': '#c47f6c',
    # белые перчатки
    'G': '#7e7a88', 'H': '#aeaab8', 'J': '#d8d5e0', 'K': '#f3f1f7',
}


class Atlas:
    def __init__(self, w=128, h=128):
        self.img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        self.px = self.img.load()

    def put(self, x, y, ch):
        if ch == '.' or ch == ' ':
            return
        self.px[x, y] = hx(PAL[ch])

    def art(self, x0, y0, rows, flip=False):
        for j, r in enumerate(rows):
            if flip:
                r = r[::-1]
            for i, ch in enumerate(r):
                self.put(x0 + i, y0 + j, ch)

    def fill(self, x0, y0, w, h, ch):
        for j in range(h):
            for i in range(w):
                self.put(x0 + i, y0 + j, ch)

    def clear(self, x0, y0, w, h):
        for j in range(h):
            for i in range(w):
                self.px[x0 + i, y0 + j] = (0, 0, 0, 0)


def mirror(rows):
    return [r[::-1] for r in rows]


# ================================================================== скин владельца (раскладка 64×64), перерисован вручную
# Лицо: светлая чёлка, тёмно-золотые брови, глаза — белок снаружи, радужка у переносицы (тёмная сверху, голубая снизу), как на скине.
FACE = ['DEDDEDDC',
        'CDCEDDCB',
        'BC4CD3CB',
        'CBB44BBC',
        'Cwi44iwC',
        '3wj44jw3',
        '23444432',
        '12333321']
FACE_SMILE = ['DEDDEDDC',
              'CDCEDDCB',
              'BC4CD3CB',
              'C4BB4BBC',          # брови чуть приподняты (одна выше — насмешка)
              'Cll44llC',          # глаза прищурены: веко
              '3ji44ij3',
              '2344mm32',          # улыбка уголком
              '12333321']
HEAD_R = ['DDEDDEDD',              # правая сторона головы: спереди — col 7 (стык с лицом)
          'CDDCDDCD',
          'BCDCCDCC',
          'BCCBC4CC',
          'ABCB234C',
          'ABB2343B',
          'AB233443',
          'A1233332']
HEAD_BACK = ['DEDDEDDE', 'CDDCDCDD', 'CCDCCDCC', 'BCCBCCBC', 'BCBBCBCB', 'ABBABBAB', 'A1AB2A1A', '11222211']
HEAD_TOP = ['CDDEDDCD', 'DDEFEDDC', 'CDEEDEDD', 'DDEDFEDC', 'CDDEEDDD', 'DCDDEDCD', 'CDCDDCDC', 'BCCBCCCB']
HEAD_BOTTOM = ['BBAAAABB', 'B111111B', 'A122221A', 'A123321A', 'A123321A', 'A122221A', 'B111111B', 'BBAAAABB']
# слой «шляпы» (+0.25): второй слой волос — объём и рваный край
HAT_FRONT = ['EDDEDEED', 'DC.DE.CD', 'C......C', 'B......B', 'B......B', '........', '........', '........']
HAT_R = ['DEDDEDDE', 'CDDCDDCD', 'BCCDCCDC', 'BCBCB..C', 'ABBA...B', 'AB.A....', 'A.......', '........']
HAT_BACK = ['EDDEDEED', 'DCDDCDDC', 'CDCCDCCD', 'BCBCCBCB', 'BBCBBCBB', 'ABBABBAB', 'A.BA.B.A', '........']
HAT_TOP = ['DEDEFEDD', 'EDFEEDED', 'DEEDFEED', 'EDFEDEFD', 'DEEDEEDE', 'EDDFEDED', 'DEDEEDDE', 'CDDEDDCD']

# камзол — тело (8×12): ворот золотом, брошь, лацканы, две пары золотых застёжек-«бранденбуров», пояс
TORSO_F = ['bdr44rdb',
           'bcrssrcb',
           'bcqtsqcb',
           'bcbrqbcb',
           'bcbqqbcb',
           'bcbbbbcb',
           'rrsbbsrr',
           'pqrbbrqp',
           'rrsbbsrr',
           'pqrbbrqp',
           'bcbbbbcb',
           'abaaaaba']
TORSO_B = ['dddddddd',
           'cccccccc',
           'cbcbbcbc',
           'cbbbbbbc',
           'crbbbbrc',
           'cqrssrqc',
           'cbqrrqbc',
           'cbbbbbbc',
           'rsrrrrsr',
           'pqqqqqqp',
           'bbbbbbbb',
           'abbaabba']
TORSO_S = ['dddd', 'cccc', 'cbbc', 'cbbc', 'cbbc', 'cbbc', 'bbbb', 'bbbb', 'rsrr', 'pqqp', 'bbbb', 'abba']
TORSO_TOP = ['dede', 'edde']                         # 8×4 — ниже собираем по строкам
JACKET_F = ['........',
            '..r..r..',
            '..q..q..',
            '........',
            '........',
            '........',
            'rrs..srr',
            'pq....qp',
            'rrs..srr',
            'pq....qp',
            '........',
            '........']
JACKET_B = ['........', '........', '........', '........', '.r....r.', '.qrssrq.', '..qrrq..', '........', 'rsrrrrsr', 'pqqqqqqp', '........', '........']
JACKET_S = ['....', '....', '....', '....', '....', '....', '....', '....', 'rsrr', 'pqqp', '....', '....']
# рукав (4×12): наплечник закрывает 0–1, золотые «кресты» 2–5, полоса 7, манжета 8–10, перчатка 11
SLEEVE_OUT = ['dccd', 'cbbc', 'cbbc', 'bccb', 'bccb', 'cbbc', 'cbbc', 'cbbc', 'bbbb', 'bbbb', 'bbbb', 'HJJH']
SLEEVE_F = ['dccd', 'cbbc', 'cbbc', 'bccb', 'bccb', 'cbbc', 'cbbc', 'cbbc', 'bbbb', 'bbbb', 'bbbb', 'HJKH']
SLEEVE_IN = ['cccc', 'cbbc', 'cbbc', 'bbbb', 'bbbb', 'bbbb', 'bbbb', 'cbbc', 'bbbb', 'bbbb', 'bbbb', 'GHHG']
SLEEVE_B = ['cccc', 'cbbc', 'cbbc', 'bccb', 'bccb', 'cbbc', 'bbbb', 'cbbc', 'bbbb', 'bbbb', 'bbbb', 'GHJG']
SLEEVE_OV_OUT = ['....', '....', 's..r', '.tr.', '.rq.', 'r..q', '....', '....', '....', '....', '....', '....']
SLEEVE_OV_F = ['....', '....', '....', '.sr.', '.rq.', '....', '....', '....', '....', '....', '....', '....']
# штаны (4×12): тёмно-серые со стрелкой, сапоги (брусок) закрывают 7–11
LEG_F = ['uvvu', 'vVWv', 'vVWv', 'vVWv', 'vVWv', 'vVWv', 'uVWu', 'uvvu', 'uvvu', 'uvvu', 'uvvu', 'uuuu']
LEG_S = ['uvvu', 'vvvv', 'vVvv', 'vVvv', 'vVvv', 'vVvv', 'uvvu', 'uvvu', 'uvvu', 'uvvu', 'uvvu', 'uuuu']


def box_regions(u, v, w, h, d):
    """Грани box UV (раскладка скина): имя → (x, y, ширина, высота)."""
    return {'up': (u + d, v, w, d), 'down': (u + d + w, v, w, d), 'east': (u, v + d, d, h), 'north': (u + d, v + d, w, h),
            'west': (u + d + w, v + d, d, h), 'south': (u + 2 * d + w, v + d, w, h)}


def paint_skin(at, smile=False):
    # голова (0,0) и слой волос (32,0)
    r = box_regions(0, 0, 8, 8, 8)
    at.art(*r['north'][:2], FACE_SMILE if smile else FACE)
    at.art(*r['east'][:2], HEAD_R)
    at.art(*r['west'][:2], mirror(HEAD_R))
    at.art(*r['south'][:2], HEAD_BACK)
    at.art(*r['up'][:2], HEAD_TOP)
    at.art(*r['down'][:2], HEAD_BOTTOM)
    r = box_regions(32, 0, 8, 8, 8)
    at.art(*r['north'][:2], HAT_FRONT)
    at.art(*r['east'][:2], HAT_R)
    at.art(*r['west'][:2], mirror(HAT_R))
    at.art(*r['south'][:2], HAT_BACK)
    at.art(*r['up'][:2], HAT_TOP)
    # тело (16,16) и слой камзола (16,32)
    r = box_regions(16, 16, 8, 12, 4)
    at.art(*r['north'][:2], TORSO_F)
    at.art(*r['south'][:2], TORSO_B)
    at.art(*r['east'][:2], TORSO_S)
    at.art(*r['west'][:2], TORSO_S)
    at.art(*r['up'][:2], ['eddddddd', 'dccccccd', 'dccccccd', 'cbbbbbbc'])
    at.art(*r['down'][:2], ['abbbbbba', 'bvvvvvvb', 'bvvvvvvb', 'abbbbbba'])
    r = box_regions(16, 32, 8, 12, 4)
    at.art(*r['north'][:2], JACKET_F)
    at.art(*r['south'][:2], JACKET_B)
    at.art(*r['east'][:2], JACKET_S)
    at.art(*r['west'][:2], JACKET_S)
    # руки: правая (40,16) / слой (40,32); левая (32,48) / слой (48,48). Наружная грань правой — east, левой — west.
    for (u, v), (ou, ov), outer in (((40, 16), (40, 32), 'east'), ((32, 48), (48, 48), 'west')):
        inner = 'west' if outer == 'east' else 'east'
        r = box_regions(u, v, 4, 12, 4)
        at.art(*r[outer][:2], SLEEVE_OUT)
        at.art(*r['north'][:2], SLEEVE_F)
        at.art(*r[inner][:2], SLEEVE_IN)
        at.art(*r['south'][:2], SLEEVE_B)
        at.art(*r['up'][:2], ['dddd', 'dccd', 'dccd', 'cccc'])
        at.art(*r['down'][:2], ['GHHG', 'HJJH', 'HJJH', 'GHHG'])
        r = box_regions(ou, ov, 4, 12, 4)
        at.art(*r[outer][:2], SLEEVE_OV_OUT)
        at.art(*r['north'][:2], SLEEVE_OV_F)
        at.art(*r['south'][:2], SLEEVE_OV_F)
    # ноги: правая (0,16), левая (16,48); слои штанин (0,32)/(0,48) пусты — полы камзола отдельные бруски
    for (u, v) in ((0, 16), (16, 48)):
        r = box_regions(u, v, 4, 12, 4)
        at.art(*r['north'][:2], LEG_F)
        at.art(*r['south'][:2], LEG_S)
        at.art(*r['east'][:2], LEG_S)
        at.art(*r['west'][:2], LEG_S)
        at.art(*r['up'][:2], ['vvvv'] * 4)
        at.art(*r['down'][:2], ['aaaa'] * 4)


# ================================================================== новые бруски (per-face UV в свободной части атласа)
class UVAlloc:
    def __init__(self):
        self.shelves = [[64, 0, 128, 64, 64, 0, 0], [0, 64, 128, 128, 0, 64, 0]]

    def take(self, w, h):
        w, h = max(1, math.ceil(w - 1e-6)), max(1, math.ceil(h - 1e-6))
        for s in self.shelves:
            x0, y0, x1, y1, cx, cy, sh = s
            if cx + w > x1:
                cx, cy, sh = x0, cy + sh, 0
            if cy + h <= y1 and cx + w <= x1:
                s[4], s[5], s[6] = cx + w, cy, max(sh, h)
                return cx, cy
        raise RuntimeError('UV: нет места под %sx%s' % (w, h))


NEW = []          # (кость, деталь, грань, x, y, w, h)
ALL6 = ('north', 'south', 'east', 'west', 'up', 'down')


def cube(al, bone, name, origin, size, faces=ALL6, pivot=None, rotation=None, inflate=None):
    w, h, d = size
    dims = {'north': (w, h), 'south': (w, h), 'east': (d, h), 'west': (d, h), 'up': (w, d), 'down': (w, d)}
    uv = {}
    for f in faces:
        fw, fh = dims[f]
        x, y = al.take(fw, fh)
        uv[f] = {'uv': [x, y], 'uv_size': [fw, fh]}
        NEW.append((bone, name, f, x, y, max(1, math.ceil(fw - 1e-6)), max(1, math.ceil(fh - 1e-6))))
    c = {'origin': [round(v, 3) for v in origin], 'size': size, 'uv': uv}
    if pivot:
        c['pivot'] = pivot
    if rotation:
        c['rotation'] = rotation
    if inflate:
        c['inflate'] = inflate
    return c


# кости пол камзола (дочери body, ось у пояса): их качает анимация; в процедурной ходьбе Iron's — код (см. письмо)
COAT_BONES = ('coat_front_r', 'coat_front_l', 'coat_back_r', 'coat_back_l')
WAIST = 12.75


def build_model():
    geo = jar_json(I + 'geo/abstract_casting_mob.geo.json')
    g = geo['minecraft:geometry'][0]
    g['description'].update({'identifier': 'geometry.ereb', 'texture_width': 128, 'texture_height': 128,
                             'visible_bounds_width': 4, 'visible_bounds_height': 4, 'visible_bounds_offset': [0, 1.5, 0]})
    bones = {b['name']: b for b in g['bones']}
    al = UVAlloc()
    NEW.clear()

    def add(bone, c):
        bones[bone].setdefault('cubes', []).append(c)

    # ---------------------------------------------------------------- волосы: объёмные пряди (кость head)
    add('head', cube(al, 'head', 'hair_cap', [-4.5, 31.5, -4.5], [9, 1.0, 9], ('north', 'south', 'east', 'west', 'up')))
    tufts = [  # макушка — взъерошенные вихры (origin, size, rotation, pivot)
        ([-3.75, 32.25, -2.75], [3, 1, 3], [0, 10, 14], [-2.25, 32.5, -1.25]),
        ([0.25, 32.25, -3.25], [3, 1, 3], [-10, -8, -12], [1.75, 32.5, -1.75]),
        ([-1.75, 32.25, 0.5], [3.5, 1, 3], [12, 20, 0], [0, 32.5, 2]),
        ([1.5, 32.25, 1.25], [2.5, 1, 3], [8, 0, -18], [2.75, 32.25, 2.75]),
        ([-0.75, 32.75, -1.25], [2, 1, 2], [-14, 30, 8], [0.25, 33.25, -0.25]),
    ]
    for i, (o, s, r, p) in enumerate(tufts):
        add('head', cube(al, 'head', 'hair_tuft_%d' % i, o, s, ('north', 'south', 'east', 'west', 'up'), pivot=p, rotation=r))
    # чёлка: пряди над глазами (низ — не ниже 28.5: брови в ряду 3 = y 28…29), разной длины, с наклоном
    fringe = [(-4.6, 2.0, 2.75, 10), (-2.75, 1.75, 3.25, -6), (-1.0, 1.75, 2.5, 12), (0.75, 1.75, 3.0, -10), (2.5, 2.0, 2.5, 8)]
    for i, (x, w, ln, rz) in enumerate(fringe):
        add('head', cube(al, 'head', 'hair_fringe_%d' % i, [x, 31.5 - ln, -4.85], [w, ln + 0.25, 0.75], ('north', 'east', 'west', 'down'),
                         pivot=[x + w / 2, 31.5, -4.5], rotation=[-8, 0, rz]))
    # виски: пряди перед ушами
    for s, nm in ((-1, 'r'), (1, 'l')):
        x = -4.85 if s < 0 else 4.1
        add('head', cube(al, 'head', 'hair_side_' + nm, [x, 26.5, -3.5], [0.75, 4.75, 2.5], ('north', 'south', 'east', 'west', 'down'),
                         pivot=[x + 0.375, 31, -2.25], rotation=[6, 0, 3 * s]))
        add('head', cube(al, 'head', 'hair_side2_' + nm, [x, 27.5, 0.0], [0.75, 3.75, 3.5], ('north', 'south', 'east', 'west', 'down'),
                         pivot=[x + 0.375, 31, 1.75], rotation=[-8, 0, 2 * s]))
    # затылок: пряди на шею
    for i, (x, w, ln, rz) in enumerate([(-4.5, 3.0, 4.5, 6), (-1.5, 3.0, 5.0, -3), (1.5, 3.0, 4.25, -7)]):
        add('head', cube(al, 'head', 'hair_back_%d' % i, [x, 31.25 - ln, 4.1], [w, ln, 0.75], ('south', 'east', 'west', 'down'),
                         pivot=[x + w / 2, 31.25, 4.4], rotation=[14, 0, rz]))

    # ---------------------------------------------------------------- воротник-стойка и мантия плеч (кость torso)
    add('torso', cube(al, 'torso', 'mantle', [-4.75, 23.0, -2.75], [9.5, 1.25, 5.5], ('north', 'south', 'east', 'west', 'up', 'down')))
    add('torso', cube(al, 'torso', 'collar_back', [-4.75, 23.5, 2.25], [9.5, 3.25, 0.75], pivot=[0, 23.5, 2.6], rotation=[-22, 0, 0]))
    for s, nm in ((-1, 'r'), (1, 'l')):
        x = -4.75 if s < 0 else 4.0
        add('torso', cube(al, 'torso', 'collar_' + nm, [x, 23.5, -2.25], [0.75, 2.75, 4.75], pivot=[x + 0.375, 23.5, 0], rotation=[0, 0, 24 * s]))
    # брошь-жабо: золотая пластина и стеклянный камень
    add('torso', cube(al, 'torso', 'jabot', [-1.0, 20.25, -2.65], [2.0, 3.25, 0.5]))
    add('torso', cube(al, 'torso', 'brooch', [-0.75, 21.0, -3.0], [1.5, 1.5, 0.5]))
    # аксельбант: золотой шнур двумя петлями от правого плеча к броши
    for k, (o, sz, rot, pv) in enumerate((([-4.6, 19.5, -2.7], [0.5, 4.0, 0.4], [0, 0, -40], [-4.35, 23.5, -2.5]),
                                          ([-4.4, 18.25, -2.75], [0.5, 4.75, 0.4], [0, 0, -62], [-4.15, 23.0, -2.55]),
                                          ([-2.0, 19.75, -2.8], [0.5, 1.25, 0.4], [0, 0, 0], [-1.75, 21.0, -2.6]))):
        add('torso', cube(al, 'torso', 'aiguillette_%d' % k, o, sz, ('north', 'east', 'west', 'down', 'up'), pivot=pv, rotation=rot))
    # пояс с пряжкой
    add('torso', cube(al, 'torso', 'belt', [-4.5, 12.5, -2.5], [9.0, 1.5, 5.0], ('north', 'south', 'east', 'west')))
    add('torso', cube(al, 'torso', 'buckle', [-1.25, 12.25, -2.85], [2.5, 2.0, 0.5]))

    # ---------------------------------------------------------------- плечи: наплечник с золотой пряжкой, манжеты (кости рук)
    for arm, s, nm in (('right_arm', -1, 'r'), ('left_arm', 1, 'l')):
        xo = -8.6 if s < 0 else 3.6                                   # наплечник шире руки на 0.6 наружу
        add(arm, cube(al, arm, 'epaulet_' + nm, [xo, 22.5, -2.5], [5.0, 1.75, 5.0]))
        xb = -8.95 if s < 0 else 8.45
        add(arm, cube(al, arm, 'clasp_' + nm, [xb, 21.75, -1.25], [0.5, 2.5, 2.5]))
        xs = -8.9 if s < 0 else 4.0
        add(arm, cube(al, arm, 'strap_' + nm, [-8.0 if s < 0 else 4.4, 24.25, -0.5], [3.6, 0.5, 1.0], ('north', 'south', 'up', 'east', 'west')))
        for k in range(5):                                            # золотая бахрома по наружному краю наплечника
            xf = -8.75 if s < 0 else 8.25
            add(arm, cube(al, arm, 'fringe_%s%d' % (nm, k), [xf, 20.75 + (0.25 if k % 2 else 0), -2.25 + k * 1.0], [0.5, 1.75, 0.5],
                          ('north', 'south', 'east', 'west', 'down')))
        xc = -8.5 if s < 0 else 3.5
        add(arm, cube(al, arm, 'cuff_' + nm, [xc, 13.25, -2.5], [5.0, 2.75, 5.0], ('north', 'south', 'east', 'west', 'up', 'down')))
        del xs

    # ---------------------------------------------------------------- полы камзола: 4 кости у пояса (передние — разрез, задние — со шлицей)
    g['bones'] = [b for b in g['bones']]
    ib = g['bones'].index(bones['right_leg'])
    coat = []
    for nm, s in (('coat_front_r', -1), ('coat_front_l', 1)):
        x = -4.6 if s < 0 else 0.6
        coat.append({'name': nm, 'parent': 'body', 'pivot': [x + (2 if s < 0 else 2), WAIST, -2.6], 'rotation': [-3, 0, -4 * s],
                     'cubes': [cube(al, nm, nm, [x, 1.5, -2.85], [4.0, WAIST - 1.5, 0.5])]})
    for nm, s in (('coat_back_r', -1), ('coat_back_l', 1)):
        x = -4.6 if s < 0 else 0.0
        xs = -4.85 if s < 0 else 4.35
        coat.append({'name': nm, 'parent': 'body', 'pivot': [x + 2.3, WAIST, 2.6], 'rotation': [5, 0, -3 * s],
                     'cubes': [cube(al, nm, nm, [x, 1.0, 2.35], [4.6, WAIST - 1.0, 0.5]),
                               cube(al, nm, nm + '_side', [xs, 1.25, -2.4], [0.5, WAIST - 1.25, 4.75])]})
    g['bones'][ib:ib] = coat
    # ---------------------------------------------------------------- сапоги (кости ног)
    for leg, s in (('right_leg', -1), ('left_leg', 1)):
        x = -4.3 if s < 0 else -0.3
        add(leg, cube(al, leg, 'boot_' + leg, [x, 0.0, -2.3], [4.6, 5.0, 4.6]))
        add(leg, cube(al, leg, 'bootcuff_' + leg, [x - 0.1, 4.25, -2.4], [4.8, 1.25, 4.8], ('north', 'south', 'east', 'west', 'up', 'down')))
    write_json('geo/entity/ereb.geo.json', geo, indent=2)
    return geo


# ---------------------------------------------------------------- раскраска новых брусков (ручная светотень по правилам грани)
def paint_new(at):
    for bone, name, f, x, y, w, h in NEW:
        def row(j, ch):
            at.fill(x, y + j, w, 1, ch)

        def col(i, ch):
            at.fill(x + i, y, 1, h, ch)
        side = f in ('east', 'west')
        if name.startswith('hair'):
            # волосы: верх светлее, к кончикам темнее; прядки — столбцы через один чуть темнее
            base = ['F', 'E', 'E', 'D', 'D', 'C', 'C', 'B']
            for j in range(h):
                for i in range(w):
                    k = min(len(base) - 1, int(j * 6 / max(1, h - 1))) if h > 1 else 1
                    ch = base[k]
                    if (i + (j // 2)) % 3 == 2 and k < 6:
                        ch = base[min(len(base) - 1, k + 1)]
                    if f == 'up':
                        ch = 'E' if (i + j) % 3 else ('F' if (i * 7 + j) % 5 == 0 else 'D')
                    if f == 'down':
                        ch = 'B'
                    if side:
                        ch = {'F': 'E', 'E': 'D', 'D': 'C', 'C': 'C', 'B': 'B'}.get(ch, ch)
                    at.put(x + i, y + j, ch)
            if name.startswith('hair_fringe') and f == 'north':
                at.put(x + w - 1, y + h - 1, '.') if w > 1 else None                # кончик пряди заострён
        elif name in ('mantle',):
            at.fill(x, y, w, h, 'c' if f != 'down' else 'a')
            if f == 'up':
                at.fill(x, y, w, h, 'd')
                for i in range(w):
                    at.put(x + i, y + h - 1, 'e')
            elif f in ('north', 'south', 'east', 'west'):
                row(0, 'e' if f != 'south' else 'd')
                row(h - 1, 'a')
        elif name.startswith('collar'):
            # стойка: снаружи чёрное сукно, по верху золотая кромка, изнутри — золотой подбой
            inside = (name == 'collar_back' and f == 'north') or (name == 'collar_r' and f == 'west') or (name == 'collar_l' and f == 'east')
            if f == 'up':
                at.fill(x, y, w, h, 's')
                continue
            if f == 'down':
                at.fill(x, y, w, h, 'a')
                continue
            if name in ('collar_r', 'collar_l') and f == 'north':
                at.fill(x, y, w, h, 'r')
                row(0, 't')
                continue
            if inside:
                at.fill(x, y, w, h, 'q')
                row(0, 's')
                row(h - 1, 'p')
                for i in range(1, w - 1, 3):
                    at.put(x + i, y + 1, 'r')
            else:
                at.fill(x, y, w, h, 'c')
                row(0, 'r')
                row(1, 'b')
                row(h - 1, 'b')
                if w >= 4:
                    for i in range(w):
                        if i % 4 == 1:
                            at.put(x + i, y + 1, 'q')                                # золотой «стежок» под кромкой
        elif name == 'jabot':
            at.fill(x, y, w, h, 'r')
            if f == 'north':
                at.art(x, y, ['st', 'rs', 'qr'][:h] if w == 2 else ['s' * w])
                row(h - 1, 'q')
            elif f == 'down':
                at.fill(x, y, w, h, 'p')
        elif name == 'brooch' or name.startswith('clasp'):
            # золотая оправа, стеклянный камень (светится)
            at.fill(x, y, w, h, 'q')
            if (name == 'brooch' and f == 'north') or (name.startswith('clasp') and f in ('east', 'west')):
                if w >= 2 and h >= 2:
                    at.fill(x, y, w, h, 'r')
                    at.put(x, y, 's')
                    if w >= 3 and h >= 3:
                        at.fill(x + 1, y + 1, w - 2, h - 2, 'y')
                        at.put(x + 1, y + 1, 'Z')
                    else:
                        at.put(x + w - 1, y + h - 1, 'y')
                        at.put(x, y + h - 1, 'z')
            elif f == 'up':
                at.fill(x, y, w, h, 's')
        elif name == 'belt':
            at.fill(x, y, w, h, 'b')
            row(0, 'd')
            row(h - 1, 'a') if h > 1 else None
            for i in range(0, w, 3):
                at.put(x + i, y, 'q') if f in ('north', 'south') else None
        elif name == 'buckle':
            at.fill(x, y, w, h, 'r')
            if f == 'north':
                at.art(x, y, ['ts', 'rq'][:h] if w == 2 else ['tsr', 'sbq'][:h])
                if w >= 3 and h >= 2:
                    at.put(x + 1, y + 1, 'a')
            elif f in ('down', 'east', 'west'):
                at.fill(x, y, w, h, 'q')
        elif name.startswith('epaulet'):
            # наплечник: чёрный, по краю золотая кайма, сверху — золотой «крест» как на рукаве
            at.fill(x, y, w, h, 'c')
            if f == 'up':
                at.fill(x, y, w, h, 'd')
                for i in range(w):
                    at.put(x + i, y, 'r')
                    at.put(x + i, y + h - 1, 'q')
                for j in range(h):
                    at.put(x, y + j, 'r')
                    at.put(x + w - 1, y + j, 'q')
                cx, cy = x + w // 2, y + h // 2
                for (dx, dy, ch) in ((0, 0, 't'), (-1, 0, 'r'), (1, 0, 'r'), (0, -1, 's'), (0, 1, 'q')):
                    at.put(cx + dx, cy + dy, ch)
            elif f == 'down':
                at.fill(x, y, w, h, 'a')
            else:
                row(0, 'e')
                row(h - 1, 's')
                if h > 2:
                    row(h - 2, 'b')
        elif name.startswith('fringe'):
            at.fill(x, y, w, h, 'r')
            if f in ('north', 'south', 'east', 'west'):
                at.fill(x, y + h - 1, w, 1, 'q')
                at.put(x, y, 's')
            elif f == 'down':
                at.fill(x, y, w, h, 'p')
        elif name.startswith('aiguillette'):
            for j in range(h):
                for i in range(w):
                    at.put(x + i, y + j, 's' if (i + j) % 2 == 0 else 'q')        # витой шнур
            if f == 'down':
                at.fill(x, y, w, h, 'r')
        elif name.startswith('strap'):
            at.fill(x, y, w, h, 'b')
            if f == 'up':
                row(0, 'd')
                at.put(x + w // 2, y, 'r')
        elif name.startswith('cuff'):
            # отворот манжеты: чёрный, две золотые полосы, внизу тёмный край
            at.fill(x, y, w, h, 'c')
            if f in ('up', 'down'):
                at.fill(x, y, w, h, 'a' if f == 'down' else 'd')
                if f == 'up':
                    for i in range(w):
                        at.put(x + i, y, 'q')
                continue
            row(0, 's')
            row(1, 'b')
            row(h - 1, 'a')
            if f in ('east', 'west') and h > 2:                                      # пуговицы манжеты снаружи
                at.put(x + w // 2, y + 1, 'r')
        elif name.startswith('coat_'):
            paint_coat(at, name, f, x, y, w, h)
        elif name.startswith('boot'):
            cuff = name.startswith('bootcuff')
            at.fill(x, y, w, h, 'b')
            if f == 'up':
                at.fill(x, y, w, h, 'q' if cuff else 'b')
                if cuff:
                    for i in range(1, w - 1):
                        for j in range(1, h - 1):
                            at.put(x + i, y + j, 'a')
                continue
            if f == 'down':
                at.fill(x, y, w, h, 'a')
                continue
            if cuff:
                row(0, 's')
                row(h - 1, 'q') if h > 1 else None
            else:
                for j in range(h):
                    at.put(x + (1 if f in ('north', 'south') else 0), y + j, 'd')     # блик кожи по ребру
                    at.put(x + w - 1, y + j, 'a')
                row(h - 1, 'a')
                row(h - 2, 'o') if f == 'north' else None                           # золотой рант носка спереди


def paint_coat(at, name, f, x, y, w, h):
    """Полы камзола. Спереди — внутренний край золотой (разрез расходится к подолу), подол — золотая кайма в 2 ряда
    с узором-«кистью»; ткань — вертикальные складки (свет/тень столбцами), не шум. Изнанка — тёмно-серый подбой."""
    side = name.endswith('_side')
    front = name.startswith('coat_front')
    right = name.endswith('_r') or name.endswith('_r_side')
    if f in ('up', 'down'):
        at.fill(x, y, w, h, 'r' if f == 'down' else 'c')
        return
    inner_face = (front and f == 'south') or (not front and not side and f == 'north') or \
        (side and ((right and f == 'west') or (not right and f == 'east')))
    if inner_face:
        at.fill(x, y, w, h, 'v')
        for i in range(w):
            if i % 2:
                at.fill(x + i, y, 1, h, 'u')
        at.fill(x, y + h - 1, w, 1, 'q')
        return
    if (side or front) and f in ('east', 'west') and w <= 1:
        at.fill(x, y, w, h, 'c')
        at.fill(x, y + h - 2, w, 2, 'q')
        return
    # складки: повторяющийся «свет — основа — тень»
    folds = 'dcbab' if w >= 5 else 'dcba'
    for i in range(w):
        at.fill(x + i, y, 1, h, folds[i % len(folds)] if not side else ('cbab'[i % 4]))
    at.fill(x, y, w, 1, 'd')                               # под поясом — светлая строка
    # подол: золотая кайма + узор
    at.fill(x, y + h - 2, w, 1, 's')
    at.fill(x, y + h - 1, w, 1, 'q')
    for i in range(w):
        if i % 3 == 1:
            at.put(x + i, y + h - 3, 'r')                       # «кисти» над каймой
    if front and f == 'north':
        # внутренний край: справа у правой полы (u растёт к +x), слева — у левой
        ie = w - 1 if right else 0
        at.fill(x + ie, y, 1, h, 'r')
        at.put(x + ie, y, 's')
        for j in range(2, h - 2, 3):
            at.put(x + ie, y + j, 's')                          # блики на золотом галуне
        oe = 0 if right else w - 1
        at.fill(x + oe, y + 1, 1, h - 3, 'b')
    if not front and not side and f == 'south':
        # шлица: у середины золотая кромка (u растёт к −x на south), сверху — золотой полумесяц-узор как на спине скина
        ie = w - 1 if right else 0
        at.fill(x + ie, y + 4, 1, h - 4, 'q')
        for i in range(1, w - 1):
            at.put(x + i, y + 2, 'r' if i in (1, w - 2) else 'p')
    if side:
        at.fill(x, y + 1, w, 1, 'c')


def paint_glow(at_img):
    """Глоумаска: только радужки глаз (едва), стекло броши и пряжек."""
    g = Image.new('RGBA', at_img.size, (0, 0, 0, 0))
    px = at_img.load()
    gp = g.load()
    glass = {hx(PAL[c])[:3] for c in 'yzZ'}
    for yy in range(at_img.size[1]):
        for xx in range(at_img.size[0]):
            p = px[xx, yy]
            if p[3] and p[:3] in glass:
                gp[xx, yy] = p
    # радужки лица: (8..16, 8..16) — ряды 4–5
    for (cx, cy) in ((10, 12), (13, 12), (10, 13), (13, 13)):
        p = px[cx, cy]
        if p[:3] in (hx(PAL['i'])[:3], hx(PAL['j'])[:3]):
            gp[cx, cy] = hx('#1d6a80') if p[:3] == hx(PAL['j'])[:3] else hx('#0e3442')
    return g


def textures(geo):
    res = {}
    for nm, smile in (('ereb', False), ('ereb_smile', True)):
        at = Atlas()
        paint_skin(at, smile)
        paint_new(at)
        at.img.save(out(TEX + nm + '.png'))
        res[nm] = at.img
    paint_glow(res['ereb']).save(out(TEX + 'ereb_glowmask.png'))
    return res


# ================================================================== рапира — 3D-предмет из брусков
RAP_PAL = {'k': '#0b0a0f', 'k1': '#17141c', 'k2': '#27222c', 'k3': '#3a3440',
           'g0': '#5b3c10', 'g1': '#86591a', 'g2': '#b07c26', 'g3': '#d4a038', 'g4': '#ecc85c', 'g5': '#fff0a6',
           'c1': '#3d8fb5', 'c2': '#8fd8f2'}
RAP_CELL = {k: (i % 16, i // 16) for i, k in enumerate(RAP_PAL)}


def rapier_elements():
    """Рапира строится вертикально (клинок вверх по y, центр x = z = 8), затем вся модель поворачивается на −45° вокруг z
    (как спрайт handheld: рукоять снизу-слева, острие вверху-справа). Один поворот на элемент — разрешённый Minecraft ±45°."""
    el = []

    def box(x0, y0, z0, x1, y1, z1, col, side=None):
        faces = {}
        for f in ALL6:
            u, v = RAP_CELL[(side or {}).get(f, col)]
            faces[f] = {'uv': [u + .25, v + .25, u + .75, v + .75], 'texture': '#p'}
        el.append({'from': [round(x0, 3), round(y0, 3), round(z0, 3)], 'to': [round(x1, 3), round(y1, 3), round(z1, 3)], 'faces': faces,
                   'rotation': {'angle': -45, 'axis': 'z', 'origin': [8, 8, 8]}})

    def bar(cx, cy, cz, sx, sy, sz, col, side=None):
        box(cx - sx / 2, cy - sy / 2, cz - sz / 2, cx + sx / 2, cy + sy / 2, cz + sz / 2, col, side)
    C = 8.0
    # навершие: золотой шар-«яблоко» с гранями
    bar(C, 0.9, C, 1.5, 1.0, 1.5, 'g2', {'up': 'g3', 'north': 'g3', 'west': 'g1', 'down': 'g1'})
    bar(C, 0.9, C, 1.1, 1.4, 1.1, 'g3', {'up': 'g4', 'north': 'g4'})
    bar(C, 0.1, C, 0.5, 0.4, 0.5, 'g4')
    # рукоять: чёрная, витая (чередование тонов), три золотых кольца
    for i in range(8):
        y = 1.6 + i * 0.42
        bar(C, y + 0.21, C, 0.8, 0.42, 0.8, 'k1' if i % 2 else 'k2', {'north': 'k3' if i % 2 == 0 else 'k2'})
    for y in (1.75, 3.25, 4.75):
        bar(C, y, C, 1.0, 0.24, 1.0, 'g3', {'north': 'g4', 'up': 'g4', 'down': 'g1'})
    # крестовина с загнутыми концами
    bar(C, 5.3, C, 5.6, 0.42, 0.5, 'g3', {'up': 'g4', 'north': 'g4', 'down': 'g1'})
    bar(C - 2.95, 5.75, C, 0.5, 0.9, 0.55, 'g3', {'up': 'g5'})
    bar(C + 2.95, 4.85, C, 0.5, 0.9, 0.55, 'g3', {'down': 'g1'})
    bar(C - 2.95, 6.25, C, 0.7, 0.4, 0.7, 'g4')                 # шарики-финиалы
    bar(C + 2.95, 4.35, C, 0.7, 0.4, 0.7, 'g4')
    # чашка гарды: золотая, внутри — тёмная, по ободу — блик; на чашке — стеклянная вставка
    bar(C, 5.95, C, 2.7, 0.7, 2.7, 'g2', {'up': 'g3', 'north': 'g3', 'south': 'g1'})
    bar(C, 6.45, C, 3.2, 0.3, 3.2, 'g3', {'up': 'k2', 'north': 'g4', 'east': 'g4'})
    bar(C, 6.62, C, 2.4, 0.06, 2.4, 'k1')
    bar(C, 5.95, C - 1.42, 0.7, 0.5, 0.12, 'c1', {'north': 'c2'})
    # витая дужка (защита пальцев): от крестовины вниз к навершию ступенями, «витьё» — чередование тонов
    bow = [(C + 2.6, 4.2), (C + 2.3, 3.4), (C + 2.0, 2.6), (C + 1.7, 1.8), (C + 1.3, 1.2), (C + 0.8, 0.8)]
    for i, (bx, by) in enumerate(bow):
        bar(bx, by, C, 0.42, 0.85, 0.42, 'g3' if i % 2 else 'g2', {'north': 'g4' if i % 2 else 'g3'})
    # боковые кольца-«ветви» (витая гарда): две петли по бокам рикассо
    for s in (-1, 1):
        for (dy, dx) in ((7.0, 1.05), (7.55, 0.95), (8.0, 0.7)):
            bar(C + s * dx, dy, C, 0.32, 0.55, 0.32, 'g3', {'north': 'g4'})
        bar(C + s * 1.0, 6.75, C + 0.0, 0.34, 0.4, 0.34, 'g2')
    # рикассо и клинок: чёрный, золотая кромка с двух сторон, золотой дол по середине (2/3 длины), сужение к острию
    bar(C, 7.4, C, 0.75, 1.3, 0.42, 'k1', {'north': 'k2'})
    L0, L1 = 8.0, 23.0
    n = 10
    for i in range(n):
        y0 = L0 + (L1 - L0) * i / n
        y1 = L0 + (L1 - L0) * (i + 1) / n
        t = (i + 0.5) / n
        wdt = 0.8 - 0.42 * t
        box(C - wdt / 2, y0, C - 0.13, C + wdt / 2, y1, C + 0.13, 'k1', {'north': 'k2', 'south': 'k2', 'up': 'k3'})
        e = 0.14
        box(C - wdt / 2 - e, y0, C - 0.07, C - wdt / 2, y1, C + 0.07, 'g4', {'west': 'g5'})
        box(C + wdt / 2, y0, C - 0.07, C + wdt / 2 + e, y1, C + 0.07, 'g3', {'east': 'g4'})
        if t < 0.66:
            box(C - 0.07, y0, C - 0.16, C + 0.07, y1, C + 0.16, 'g2', {'north': 'g3', 'south': 'g3'})
    bar(C, L1 + 0.35, C, 0.22, 0.7, 0.16, 'g4')                     # острие
    bar(C, L1 + 0.85, C, 0.1, 0.4, 0.1, 'g5')
    return el


def rapier():
    pal = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for k, (x, y) in RAP_CELL.items():
        pal.putpixel((x, y), hx(RAP_PAL[k]))
    pal.save(out('textures/item/ereb_rapier_3d.png'))
    # плоская иконка (GUI, на земле, в рамке): рапира по диагонали, 16×16, ручной пиксель-арт
    icon = Atlas(16, 16)
    rows = ['...............t',
            '..............sr',
            '.............rb.',
            '............rb..',
            '...........rb...',
            '..........rq....',
            '.........rb.....',
            '........rq......',
            '.......rb.......',
            '..r..qrr........',
            '..sryzr.........',
            '...rsr..........',
            '..qbrq..........',
            '.qbq.r..........',
            'tsq..q..........',
            'rq..............']
    icon.art(0, 0, rows)
    icon.img.save(out('textures/item/ereb_rapier.png'))
    els = rapier_elements()
    T = {   # как handheld (меч в руке), рапира длиннее — масштаб чуть больше
        'thirdperson_righthand': {'rotation': [0, -90, 55], 'translation': [0, 4.0, 0.5], 'scale': [0.95, 0.95, 0.95]},
        'thirdperson_lefthand': {'rotation': [0, 90, -55], 'translation': [0, 4.0, 0.5], 'scale': [0.95, 0.95, 0.95]},
        'firstperson_righthand': {'rotation': [0, -90, 25], 'translation': [1.13, 3.2, 1.13], 'scale': [0.68, 0.68, 0.68]},
        'firstperson_lefthand': {'rotation': [0, 90, -25], 'translation': [1.13, 3.2, 1.13], 'scale': [0.68, 0.68, 0.68]},
        'head': {'rotation': [0, 0, 0], 'scale': [1.0, 1.0, 1.0]},
    }
    flat = {'parent': 'minecraft:item/handheld', 'textures': {'layer0': 'pohsmp_core:item/ereb_rapier'}}
    doc = {'loader': 'forge:separate_transforms', 'gui_light': 'front',
           'base': {'textures': {'p': 'pohsmp_core:item/ereb_rapier_3d', 'particle': 'pohsmp_core:item/ereb_rapier'},
                    'elements': els, 'display': T},
           'perspectives': {'gui': flat, 'ground': flat, 'fixed': flat}}
    write_json('models/item/ereb_rapier.json', doc)
    return doc


# ================================================================== main
def main():
    args = sys.argv[1:]
    if not os.path.exists(JAR):
        sys.exit('нет %s — запустите python3 tools/fetch_libs.py' % JAR)
    geo = build_model()
    textures(geo)
    rapier()
    import gen_ereb_anims as AN
    AN.write(sys.modules[__name__])
    if '--no-fx' not in args:
        import gen_ereb_fx as FX
        FX.run(sys.modules[__name__], args)
    print('\n'.join('  ' + w for w in WRITTEN))


if __name__ == '__main__':
    main()
