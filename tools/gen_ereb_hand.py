#!/usr/bin/env python3
"""
T31 — визуал босса «Эреб, Длань Лжи» («Глава Культа Меллисто»), поздняя версия Эреба. ТЗ: docs/specs/tasks/T31_ereb_hand_of_lies.md.
Основа — принятая модель Эреба T30 (tools/gen_ereb.py: скин владельца, волосы, лицо, полы камзола, сапоги). Файлы T30 не меняются:
всё T31 — новые файлы. Эталон качества — Глава Культа T26 (docs/inbox/README.md): текстура ×4 (атлас UV 128 → картинка 512),
ручная пиксельная светотень без шума и сглаживания, детали брусками поверх каркаса мага Iron's.

Что нового против T30:
  камзол чёрно-багровый с золотом, на груди медальон со знаком Меллисто (око в пламени, как cult_emblem у Главы);
  накидка Главы Культа (кость cape) с цепью-застёжкой на плечах, знак культа на спине; тонкий золотой венец;
  маска на пол-лица (кость mask: её срывают в «Падении маски», можно скрыть) — 4 вида текстуры: целая с тонкими трещинами,
  «собранная» после «Падения маски» (золотые швы), «треснувшая» (фаза 3), глоумаски к каждой;
  левая рука — «Длань Лжи»: стеклянно-золотая латная перчатка до локтя с трещинами и отражением (глоумаска);
  призрачная рука над правым плечом — 18 костей ghost_*: запястье, ладонь, 4 пальца по 3 фаланги, большой палец 2 фаланги;
  рапира со стеклянным клинком — models/item/ereb_hand_rapier.json.

Пишет (src/main/resources/assets/pohsmp_core/):
  geo/entity/ereb_hand.geo.json                                — модель (geometry.ereb_hand), атлас 128×128 ед.
  textures/entity/ereb_hand/ereb_hand.png (+ _mended, _cracked) — 512×512 (×4), + *_glowmask.png
  animations/entity/ereb_hand.animation.json                   — tools/gen_ereb_hand_anims.py
  models/item/ereb_hand_rapier.json, textures/item/ereb_hand_rapier.png, ereb_hand_rapier_3d.png
  полоса, титры, lang — tools/gen_ereb_hand_ui.py; кадры — tools/gen_ereb_hand_shots.py

Запуск: python3 tools/gen_ereb_hand.py [--shots [--three путь/three.min.js]] [--html]   (нужен jar Iron's: python3 tools/fetch_libs.py)
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_ereb as E            # noqa: E402  (T30: палитра, лицо и волосы, рапира — только читаем)
import gen_cult_leader as G     # noqa: E402  (T26: Scale2x, грани атласа)

ROOT = E.ROOT
A = E.A
I = E.I
TEX = 'textures/entity/ereb_hand/'
K = 4
WRITTEN = []
jar_json, jar_img, hx = E.jar_json, E.jar_img, E.hx


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


# ================================================================== палитра: T30 + багрянец + призрачное стекло
PAL = dict(E.PAL)
PAL.update({
    # багрянец Культа (камзол, накидка): L — глубокая тень … Q — блик
    'L': '#1e070c', 'M': '#3a0d16', 'N': '#5c1420', 'O': '#7e1f2b', 'P': '#a3323b', 'Q': '#c95560',
    # призрачное стекло руки (холодное, чуть лиловое): f … n
    'f': '#28316a', 'g': '#4a64b8', 'h': '#8eaeee', 'n': '#e6efff',
})
E.PAL.update({k: v for k, v in PAL.items() if k not in E.PAL})      # E.Atlas красит по E.PAL (новые буквы не пересекаются с T30)
FAM = {}
for fam, ramp in (('black', 'abcde'), ('crimson', 'LMNOPQ'), ('gold', 'opqrst'), ('glass', 'xyzZ'), ('ghost', 'fghn'),
                  ('grey', 'uvVW'), ('hair', 'ABCDEF'), ('skin', '12345'), ('glove', 'GHJK')):
    for i, ch in enumerate(ramp):
        FAM[hx(PAL[ch])[:3]] = (fam, i, ramp)


def shift(rgb, d):
    f = FAM.get(tuple(rgb[:3]))
    if not f:
        return tuple(rgb[:3])
    fam, i, ramp = f
    return hx(PAL[ramp[max(0, min(len(ramp) - 1, i + d))]])[:3]


def C(ch, a=255):
    return hx(PAL[ch], a)


# ================================================================== раскладка скина (64×64) — T30 + новый камзол
TORSO_F = ['bdNOONdb',
           'bcNNONcb',
           'bcMNNMcb',
           'bcNNNNcb',
           'bcMNONcb',
           'bcNONMcb',
           'bcrssrcb',          # золотые шнуры-«бранденбуры» поперёк багряного жилета
           'bcNMNMcb',
           'bcrssrcb',
           'bcMNNMcb',
           'bcNMNNcb',
           'abMLLMba']
TORSO_B = ['dddddddd', 'cccccccc', 'cbcbbcbc', 'cbbbbbbc', 'cbbbbbbc', 'cbbbbbbc', 'cbbbbbbc', 'cbbbbbbc',
           'rsrrrrsr', 'pqqqqqqp', 'bbbbbbbb', 'abbaabba']
TORSO_S = ['dddd', 'cccc', 'cbbc', 'cbbc', 'cbbc', 'cbbc', 'bbbb', 'bbbb', 'rsrr', 'pqqp', 'bbbb', 'abba']
JACKET_F = ['dr....rd',             # распахнутый чёрный камзол (слой +0.25) поверх багряного жилета: лацканы с золотой кромкой
            'cr....rc',
            'cr....rc',
            'cr....rc',
            'br....rb',
            'br....rb',
            'b......b',
            'b......b',
            'b......b',
            'b......b',
            'br....rb',
            'ar....ra']
JACKET_S = ['....'] * 8 + ['rsrr', 'pqqp', '....', '....']
# рукав (4×12): багряная полоса вдоль, золотой «крест» у плеча; низ правого рукава — отворот, левого — перчатка «Длани»
SLEEVE_OUT = ['dccd', 'cbbc', 'cbbc', 'bccb', 'bccb', 'NOON', 'MNNM', 'cbbc', 'bbbb', 'bbbb', 'bbbb', 'HJJH']
SLEEVE_F = ['dccd', 'cbbc', 'cbbc', 'bccb', 'bccb', 'cNNc', 'cMMc', 'cbbc', 'bbbb', 'bbbb', 'bbbb', 'HJKH']
SLEEVE_IN = ['cccc', 'cbbc', 'cbbc', 'bbbb', 'bbbb', 'bMMb', 'bLLb', 'cbbc', 'bbbb', 'bbbb', 'bbbb', 'GHHG']
SLEEVE_B = ['cccc', 'cbbc', 'cbbc', 'bccb', 'bccb', 'cNNc', 'bMMb', 'cbbc', 'bbbb', 'bbbb', 'bbbb', 'GHJG']
SLEEVE_OV_OUT = ['....', '....', 's..r', '.tr.', '.rq.', 'r..q', '....', '....', '....', '....', '....', '....']
# лицо: правый глаз (за маской, в прорези) — золотая «ложная» радужка (светится); левый — голубой, как у T30
FACE = ['DEDDEDDC',
        'CDCEDDCB',
        'BC4CD3CB',
        'CBB44BBC',
        'Cws44iwC',
        '3wq44jw3',
        '23444432',
        '12333321']


def paint_skin(at):
    E.paint_skin(at)                               # голова, волосы, ноги — как у T30
    r = E.box_regions(0, 0, 8, 8, 8)
    at.art(*r['north'][:2], FACE)
    r = E.box_regions(16, 16, 8, 12, 4)
    at.art(*r['north'][:2], TORSO_F)
    at.art(*r['south'][:2], TORSO_B)
    at.art(*r['east'][:2], TORSO_S)
    at.art(*r['west'][:2], TORSO_S)
    r = E.box_regions(16, 32, 8, 12, 4)
    for f in ('north', 'south', 'east', 'west', 'up', 'down'):
        at.clear(*r[f])
    at.art(*r['north'][:2], JACKET_F)
    at.art(*r['east'][:2], JACKET_S)
    at.art(*r['west'][:2], JACKET_S)
    for (u, v), (ou, ov), outer in (((40, 16), (40, 32), 'east'), ((32, 48), (48, 48), 'west')):
        inner = 'west' if outer == 'east' else 'east'
        r = E.box_regions(u, v, 4, 12, 4)
        at.art(*r[outer][:2], SLEEVE_OUT)
        at.art(*r['north'][:2], SLEEVE_F)
        at.art(*r[inner][:2], SLEEVE_IN)
        at.art(*r['south'][:2], SLEEVE_B)
        r = E.box_regions(ou, ov, 4, 12, 4)
        for f in ('north', 'south', 'east', 'west', 'up', 'down'):
            at.clear(*r[f])
        at.art(*r[outer][:2], SLEEVE_OV_OUT)


# ================================================================== новые бруски
class UVAlloc(E.UVAlloc):
    pass


NEW = []
ALL6 = E.ALL6


def cube(al, bone, name, origin, size, faces=ALL6, pivot=None, rotation=None, inflate=None, density=1.0):
    """Брусок с per-face UV. density < 1 — грань занимает меньше атласа (растянута): для крупного призрачного стекла."""
    w, h, d = size
    dims = {'north': (w, h), 'south': (w, h), 'east': (d, h), 'west': (d, h), 'up': (w, d), 'down': (w, d)}
    uv = {}
    for f in faces:
        fw, fh = dims[f]
        fw, fh = max(1, math.ceil(fw * density - 1e-6)), max(1, math.ceil(fh * density - 1e-6))
        if density == 1.0:
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


COAT_BONES = E.COAT_BONES
WAIST = E.WAIST
# призрачная рука: (кость, родитель, ось) — ось и бруски в «покое»: ладонь вертикально над правым плечом, ладонью вперёд
GW = (-15.5, 30.0, 5.5)          # запястье
FINGERS = (('index', -12.1, 41.0, (4.5, 3.25, 2.75)), ('middle', -14.4, 41.25, (5.0, 3.5, 3.0)),
           ('ring', -16.6, 41.0, (4.5, 3.25, 2.75)), ('pinky', -18.8, 40.25, (3.5, 2.5, 2.25)))
GHOST_BONES = ['ghost_hand', 'ghost_wrist', 'ghost_palm'] + ['ghost_%s_%d' % (f[0], k) for f in FINGERS for k in (1, 2, 3)] + \
              ['ghost_thumb_1', 'ghost_thumb_2']


def build_model():
    geo = jar_json(I + 'geo/abstract_casting_mob.geo.json')
    g = geo['minecraft:geometry'][0]
    g['description'].update({'identifier': 'geometry.ereb_hand', 'texture_width': 128, 'texture_height': 128,
                             'visible_bounds_width': 5, 'visible_bounds_height': 5, 'visible_bounds_offset': [0, 1.75, 0]})
    bones = {b['name']: b for b in g['bones']}
    al = UVAlloc()
    NEW.clear()

    def add(bone, c):
        bones[bone].setdefault('cubes', []).append(c)

    # ---------------------------------------------------------------- волосы — как у T30 (кость head)
    add('head', cube(al, 'head', 'hair_cap', [-4.5, 31.5, -4.5], [9, 1.0, 9], ('north', 'south', 'east', 'west', 'up')))
    tufts = [([-3.75, 32.25, -2.75], [3, 1, 3], [0, 10, 14], [-2.25, 32.5, -1.25]),
             ([0.25, 32.25, -3.25], [3, 1, 3], [-10, -8, -12], [1.75, 32.5, -1.75]),
             ([-1.75, 32.25, 0.5], [3.5, 1, 3], [12, 20, 0], [0, 32.5, 2]),
             ([1.5, 32.25, 1.25], [2.5, 1, 3], [8, 0, -18], [2.75, 32.25, 2.75]),
             ([-0.75, 32.75, -1.25], [2, 1, 2], [-14, 30, 8], [0.25, 33.25, -0.25])]
    for i, (o, s, r, p) in enumerate(tufts):
        add('head', cube(al, 'head', 'hair_tuft_%d' % i, o, s, ('north', 'south', 'east', 'west', 'up'), pivot=p, rotation=r))
    fringe = [(-4.6, 2.0, 2.75, 10), (-2.75, 1.75, 3.25, -6), (-1.0, 1.75, 2.5, 12), (0.75, 1.75, 3.0, -10), (2.5, 2.0, 2.5, 8)]
    for i, (x, w, ln, rz) in enumerate(fringe):
        add('head', cube(al, 'head', 'hair_fringe_%d' % i, [x, 31.5 - ln, -4.85], [w, ln + 0.25, 0.75], ('north', 'east', 'west', 'down'),
                         pivot=[x + w / 2, 31.5, -4.5], rotation=[-8, 0, rz]))
    for s, nm in ((-1, 'r'), (1, 'l')):
        x = -4.85 if s < 0 else 4.1
        add('head', cube(al, 'head', 'hair_side_' + nm, [x, 26.5, -3.5], [0.75, 4.75, 2.5], ('north', 'south', 'east', 'west', 'down'),
                         pivot=[x + 0.375, 31, -2.25], rotation=[6, 0, 3 * s]))
        add('head', cube(al, 'head', 'hair_side2_' + nm, [x, 27.5, 0.0], [0.75, 3.75, 3.5], ('north', 'south', 'east', 'west', 'down'),
                         pivot=[x + 0.375, 31, 1.75], rotation=[-8, 0, 2 * s]))
    for i, (x, w, ln, rz) in enumerate([(-4.5, 3.0, 4.5, 6), (-1.5, 3.0, 5.0, -3), (1.5, 3.0, 4.25, -7)]):
        add('head', cube(al, 'head', 'hair_back_%d' % i, [x, 31.25 - ln, 4.1], [w, ln, 0.75], ('south', 'east', 'west', 'down'),
                         pivot=[x + w / 2, 31.25, 4.4], rotation=[14, 0, rz]))
    # ---------------------------------------------------------------- тонкий золотой венец (поверх волос, кольцо ±5.25)
    # тонкое кольцо по макушке, над чёлкой и висками (между шапкой волос ±4.5 и вихрами), зубец со багряным камнем спереди
    add('head', cube(al, 'head', 'circlet_f', [-4.85, 31.8, -4.85], [9.7, 0.45, 0.35], ('north', 'south', 'up', 'down', 'east', 'west')))
    add('head', cube(al, 'head', 'circlet_b', [-4.85, 31.8, 4.5], [9.7, 0.45, 0.35], ('north', 'south', 'up', 'down')))
    add('head', cube(al, 'head', 'circlet_r', [-4.85, 31.8, -4.5], [0.35, 0.45, 9.0], ('east', 'west', 'up', 'down')))
    add('head', cube(al, 'head', 'circlet_l', [4.5, 31.8, -4.5], [0.35, 0.45, 9.0], ('east', 'west', 'up', 'down')))
    add('head', cube(al, 'head', 'circlet_peak', [-0.75, 32.2, -4.95], [1.5, 1.75, 0.4], ('north', 'south', 'east', 'west', 'up'),
                     pivot=[0, 32.2, -4.75], rotation=[10, 0, 0]))
    for i, x in enumerate((-3.0, 2.4)):
        add('head', cube(al, 'head', 'circlet_tine_%d' % i, [x, 32.2, -4.92], [0.6, 0.8, 0.35], ('north', 'east', 'west', 'up'),
                         pivot=[x + 0.3, 32.2, -4.75], rotation=[10, 0, 0]))
    # ---------------------------------------------------------------- маска на пол-лица (своя кость: её срывают в «Падении маски»)
    mask = {'name': 'mask', 'parent': 'head', 'pivot': [-2.0, 28.0, -4.85], 'cubes': [
        cube(al, 'mask', 'mask', [-4.45, 25.0, -5.1], [4.7, 5.5, 0.5], ('north', 'west', 'up')),
        cube(al, 'mask', 'mask_brow', [-4.95, 29.6, -5.15], [1.6, 1.75, 0.5], ('north', 'east', 'west', 'up', 'south'),
             pivot=[-4.15, 29.6, -4.9], rotation=[0, 0, -28]),
        cube(al, 'mask', 'mask_cheek', [-5.05, 25.25, -4.95], [0.6, 3.75, 1.6], ('north', 'east', 'west', 'down', 'up'),
             pivot=[-4.75, 27, -4.15], rotation=[0, 14, 0]),
    ]}
    # ---------------------------------------------------------------- воротник-стойка (изнутри — багрянец), мантия плеч
    add('torso', cube(al, 'torso', 'mantle', [-4.75, 23.0, -2.75], [9.5, 1.25, 5.5]))
    add('torso', cube(al, 'torso', 'collar_back', [-4.75, 23.5, 2.25], [9.5, 3.25, 0.75], pivot=[0, 23.5, 2.6], rotation=[-22, 0, 0]))
    for s, nm in ((-1, 'r'), (1, 'l')):
        x = -4.75 if s < 0 else 4.0
        add('torso', cube(al, 'torso', 'collar_' + nm, [x, 23.5, -2.25], [0.75, 2.75, 4.75], pivot=[x + 0.375, 23.5, 0], rotation=[0, 0, 24 * s]))
    # медальон со знаком Меллисто (око в пламени) — золото, багряное око
    add('torso', cube(al, 'torso', 'medallion', [-1.75, 17.5, -2.9], [3.5, 4.5, 0.6], ('north', 'east', 'west', 'up', 'down')))
    # застёжка накидки на плечах: две золотые бляхи с багряным камнем и цепь между ними (провисает к медальону)
    for s, nm in ((-1, 'r'), (1, 'l')):
        x = -4.55 if s < 0 else 3.25
        add('torso', cube(al, 'torso', 'clasp_' + nm, [x, 22.15, -2.95], [1.3, 1.3, 0.5]))
        add('torso', cube(al, 'torso', 'chain_' + nm, [-3.4 if s < 0 else 0, 22.0, -2.75], [3.4, 0.4, 0.35], ('north', 'up', 'down'),
                         pivot=[-3.4 if s < 0 else 3.4, 22.6, -2.6], rotation=[0, 0, 13 * s]))
    add('torso', cube(al, 'torso', 'belt', [-4.5, 12.5, -2.5], [9.0, 1.5, 5.0], ('north', 'south', 'east', 'west')))
    add('torso', cube(al, 'torso', 'buckle', [-1.25, 12.25, -2.85], [2.5, 2.0, 0.5]))
    # ---------------------------------------------------------------- накидка Главы Культа (кость cape, ось у плеч сзади)
    cape = {'name': 'cape', 'parent': 'torso', 'pivot': [0, 23.0, 3.25], 'rotation': [5, 0, 0], 'cubes': [
        cube(al, 'cape', 'cape', [-5.25, 4.5, 3.0], [10.5, 18.5, 0.5], ('north', 'south', 'east', 'west', 'down')),
        cube(al, 'cape', 'cape_roll', [-5.5, 22.0, 2.6], [11.0, 1.4, 1.4], ('north', 'south', 'east', 'west', 'up', 'down')),
    ]}
    # ---------------------------------------------------------------- плечи
    for arm, s, nm in (('right_arm', -1, 'r'), ('left_arm', 1, 'l')):
        xo = -8.6 if s < 0 else 3.6
        add(arm, cube(al, arm, 'epaulet_' + nm, [xo, 22.5, -2.5], [5.0, 1.75, 5.0]))
        xb = -8.95 if s < 0 else 8.45
        add(arm, cube(al, arm, 'eclasp_' + nm, [xb, 21.75, -1.25], [0.5, 2.5, 2.5]))
        for k in range(5):
            xf = -8.75 if s < 0 else 8.25
            add(arm, cube(al, arm, 'fringe_%s%d' % (nm, k), [xf, 20.75 + (0.25 if k % 2 else 0), -2.25 + k * 1.0], [0.5, 1.75, 0.5],
                          ('north', 'south', 'east', 'west', 'down')))
    add('right_arm', cube(al, 'right_arm', 'cuff_r', [-8.5, 13.25, -2.5], [5.0, 2.75, 5.0]))
    # ---------------------------------------------------------------- «Длань Лжи»: стеклянно-золотая латная перчатка до локтя
    LA = 'left_arm'
    add(LA, cube(al, LA, 'gaunt', [3.65, 11.75, -2.35], [4.7, 5.0, 4.7]))                     # наруч
    add(LA, cube(al, LA, 'gaunt_couter', [3.4, 16.5, -2.6], [5.2, 1.5, 5.2]))                 # раструб у локтя
    add(LA, cube(al, LA, 'gaunt_wing', [8.45, 15.25, -1.5], [0.6, 3.25, 3.0], ('north', 'south', 'east', 'west', 'up', 'down'),
                 pivot=[8.6, 16.75, 0], rotation=[0, 0, -18]))                                # гребень-крыло снаружи локтя
    add(LA, cube(al, LA, 'gaunt_knuck', [3.55, 10.5, -2.5], [4.9, 1.5, 4.9]))                 # латная кисть
    for k in range(4):                                                                         # пластины пальцев спереди
        add(LA, cube(al, LA, 'gaunt_finger_%d' % k, [3.75 + k * 1.15, 9.25, -2.6], [1.0, 1.5, 1.3], ('north', 'east', 'west', 'down', 'south')))
    # ---------------------------------------------------------------- полы камзола (как T30) и сапоги
    g['bones'] = [b for b in g['bones']]
    ib = g['bones'].index(bones['right_leg'])
    coat = []
    for nm, s in (('coat_front_r', -1), ('coat_front_l', 1)):
        x = -4.6 if s < 0 else 0.6
        coat.append({'name': nm, 'parent': 'body', 'pivot': [x + 2, WAIST, -2.6], 'rotation': [-3, 0, -4 * s],
                     'cubes': [cube(al, nm, nm, [x, 1.5, -2.85], [4.0, WAIST - 1.5, 0.5])]})
    for nm, s in (('coat_back_r', -1), ('coat_back_l', 1)):
        x = -4.6 if s < 0 else 0.0
        xs = -4.85 if s < 0 else 4.35
        coat.append({'name': nm, 'parent': 'body', 'pivot': [x + 2.3, WAIST, 2.6], 'rotation': [5, 0, -3 * s],
                     'cubes': [cube(al, nm, nm, [x, 1.0, 2.35], [4.6, WAIST - 1.0, 0.5]),
                               cube(al, nm, nm + '_side', [xs, 1.25, -2.4], [0.5, WAIST - 1.25, 4.75])]})
    for leg, s in (('right_leg', -1), ('left_leg', 1)):
        x = -4.3 if s < 0 else -0.3
        add(leg, cube(al, leg, 'boot_' + leg, [x, 0.0, -2.3], [4.6, 5.0, 4.6]))
        add(leg, cube(al, leg, 'bootcuff_' + leg, [x - 0.1, 4.25, -2.4], [4.8, 1.25, 4.8]))
    # ---------------------------------------------------------------- призрачная рука (дочь body): стекло, отдельные кости
    gx, gy, gz = GW
    D = 0.5                                           # плотность атласа стекла: 2 пикселя картинки на единицу (крупно и прозрачно)
    ghost = [{'name': 'ghost_hand', 'parent': 'body', 'pivot': [gx, gy, gz], 'cubes': [
                 cube(al, 'ghost_hand', 'ghost_mist', [gx - 2.0, gy - 5.5, gz - 1.6], [4.0, 5.0, 3.2],
                      ('north', 'south', 'east', 'west'), density=D)]},
             {'name': 'ghost_wrist', 'parent': 'ghost_hand', 'pivot': [gx, gy, gz], 'cubes': [
                 cube(al, 'ghost_wrist', 'ghost_wrist', [gx - 2.5, gy - 0.75, gz - 1.9], [5.0, 2.25, 3.8], density=D)]},
             {'name': 'ghost_palm', 'parent': 'ghost_wrist', 'pivot': [gx, gy + 1.25, gz], 'cubes': [
                 cube(al, 'ghost_palm', 'ghost_palm', [gx - 4.5, gy + 1.0, gz - 1.5], [9.0, 10.0, 3.0], density=D),
                 cube(al, 'ghost_palm', 'ghost_thenar', [gx + 2.25, gy + 1.25, gz - 2.0], [2.5, 5.0, 3.4], density=D)]}]
    for fname, cx, by, lens in FINGERS:
        par, y0 = 'ghost_palm', by
        for k, ln in enumerate(lens, 1):
            wdt, dep = (2.0, 2.5) if k == 1 else ((1.8, 2.25) if k == 2 else (1.6, 2.0))
            nm = 'ghost_%s_%d' % (fname, k)
            ghost.append({'name': nm, 'parent': par, 'pivot': [cx, y0, gz], 'rotation': [6 if k > 1 else 3, 0, 0], 'cubes': [
                cube(al, nm, nm, [cx - wdt / 2, y0, gz - dep / 2], [wdt, ln + (0.15 if k < 3 else 0), dep],
                     ('north', 'south', 'east', 'west', 'up') if k == 3 else ('north', 'south', 'east', 'west'), density=D)]})
            par, y0 = nm, y0 + ln
    tx, ty = gx + 4.5, gy + 3.0                       # большой палец — от края ладони к телу (+x), вверх
    ghost.append({'name': 'ghost_thumb_1', 'parent': 'ghost_palm', 'pivot': [tx, ty, gz], 'rotation': [0, 0, -42], 'cubes': [
        cube(al, 'ghost_thumb_1', 'ghost_thumb_1', [tx, ty - 1.2, gz - 1.25], [3.5, 2.4, 2.5], ('north', 'south', 'up', 'down', 'east'), density=D)]})
    ghost.append({'name': 'ghost_thumb_2', 'parent': 'ghost_thumb_1', 'pivot': [tx + 3.5, ty, gz], 'rotation': [0, 0, -12], 'cubes': [
        cube(al, 'ghost_thumb_2', 'ghost_thumb_2', [tx + 3.5, ty - 1.05, gz - 1.1], [2.75, 2.1, 2.2], ('north', 'south', 'up', 'down', 'east'),
             density=D)]})
    g['bones'][ib:ib] = coat + [cape]
    ih = g['bones'].index(bones['armorBipedHead'])
    g['bones'][ih:ih] = [mask]
    g['bones'] += ghost
    write_json('geo/entity/ereb_hand.geo.json', geo, indent=2)
    return geo


# ================================================================== раскраска новых брусков (в единицах атласа; ×4 — потом)
def paint_new(at):
    for bone, name, f, x, y, w, h in NEW:
        def row(j, ch):
            at.fill(x, y + j, w, 1, ch)

        if name.startswith('hair'):
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
                    if f in ('east', 'west'):
                        ch = {'F': 'E', 'E': 'D', 'D': 'C', 'C': 'C', 'B': 'B'}.get(ch, ch)
                    at.put(x + i, y + j, ch)
            if name.startswith('hair_fringe') and f == 'north' and w > 1:
                at.put(x + w - 1, y + h - 1, '.')
        elif name.startswith('circlet'):
            at.fill(x, y, w, h, 'r')
            if f in ('up',):
                at.fill(x, y, w, h, 's')
            elif f == 'down':
                at.fill(x, y, w, h, 'p')
        elif name.startswith('mask'):
            at.fill(x, y, w, h, 'r' if f != 'down' else 'q')
            if f == 'up':
                at.fill(x, y, w, h, 's')
        elif name == 'mantle':
            at.fill(x, y, w, h, 'c' if f != 'down' else 'a')
            if f == 'up':
                at.fill(x, y, w, h, 'd')
                row(h - 1, 'e')
            elif f != 'down':
                row(0, 'e' if f != 'south' else 'd')
                row(h - 1, 'a')
        elif name.startswith('collar'):
            inside = (name == 'collar_back' and f == 'north') or (name == 'collar_r' and f == 'west') or (name == 'collar_l' and f == 'east')
            if f == 'up':
                at.fill(x, y, w, h, 's')
            elif f == 'down':
                at.fill(x, y, w, h, 'a')
            elif name in ('collar_r', 'collar_l') and f == 'north':
                at.fill(x, y, w, h, 'r')
                row(0, 't')
            elif inside:
                at.fill(x, y, w, h, 'N')
                row(0, 's')
                row(h - 1, 'M')
            else:
                at.fill(x, y, w, h, 'c')
                row(0, 'r')
                row(1, 'b')
                row(h - 1, 'b')
        elif name in ('medallion',) or name.startswith('clasp') or name.startswith('eclasp'):
            at.fill(x, y, w, h, 'q')
            if f == 'up':
                at.fill(x, y, w, h, 's')
            elif f == 'down':
                at.fill(x, y, w, h, 'p')
            elif (name.startswith('clasp') and f == 'north') or (name.startswith('eclasp') and f in ('east', 'west')):
                at.fill(x, y, w, h, 'r')
                if w >= 2 and h >= 2:
                    at.fill(x + w // 2 - 1 + (w % 2), y + h // 2 - 1 + (h % 2), 1, 1, 'O')
        elif name.startswith('chain'):
            for i in range(w):
                at.fill(x + i, y, 1, h, 's' if i % 2 == 0 else 'p')
        elif name == 'belt':
            at.fill(x, y, w, h, 'b')
            row(0, 'd')
            row(h - 1, 'a') if h > 1 else None
            for i in range(0, w, 3):
                at.put(x + i, y, 'q') if f in ('north', 'south') else None
        elif name == 'buckle':
            at.fill(x, y, w, h, 'r')
            if f == 'north':
                at.art(x, y, ['ts', 'rq'][:h] if w == 2 else ['tsr', 'sOq'][:h])
            elif f in ('down', 'east', 'west'):
                at.fill(x, y, w, h, 'q')
        elif name == 'cape' or name == 'cape_roll':
            paint_cape(at, name, f, x, y, w, h)
        elif name.startswith('epaulet'):
            at.fill(x, y, w, h, 'N')
            if f == 'up':
                at.fill(x, y, w, h, 'O')
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
                at.fill(x, y, w, h, 'L')
            else:
                row(0, 'P')
                row(h - 1, 's')
                if h > 2:
                    row(h - 2, 'M')
        elif name.startswith('fringe'):
            at.fill(x, y, w, h, 'r')
            if f != 'down' and f != 'up':
                at.fill(x, y + h - 1, w, 1, 'q')
                at.put(x, y, 's')
            elif f == 'down':
                at.fill(x, y, w, h, 'p')
        elif name.startswith('cuff'):
            at.fill(x, y, w, h, 'N')
            if f in ('up', 'down'):
                at.fill(x, y, w, h, 'L' if f == 'down' else 'M')
                if f == 'up':
                    for i in range(w):
                        at.put(x + i, y, 'q')
                continue
            row(0, 's')
            row(1, 'M')
            row(h - 1, 'L')
            if f in ('east', 'west') and h > 2:
                at.put(x + w // 2, y + 1, 'r')
        elif name.startswith('gaunt'):
            paint_gauntlet(at, name, f, x, y, w, h)
        elif name.startswith('coat_'):
            paint_coat(at, name, f, x, y, w, h)
        elif name.startswith('boot'):
            cuff = name.startswith('bootcuff')
            at.fill(x, y, w, h, 'b')
            if f == 'up':
                at.fill(x, y, w, h, 'q' if cuff else 'b')
                if cuff:
                    at.fill(x + 1, y + 1, w - 2, h - 2, 'a')
                continue
            if f == 'down':
                at.fill(x, y, w, h, 'a')
                continue
            if cuff:
                row(0, 's')
                row(h - 1, 'q') if h > 1 else None
            else:
                for j in range(h):
                    at.put(x + (1 if f in ('north', 'south') else 0), y + j, 'd')
                    at.put(x + w - 1, y + j, 'a')
                row(h - 1, 'a')
                row(h - 2, 'o') if f == 'north' else None
        elif name.startswith('ghost'):
            paint_ghost(at, name, f, x, y, w, h)


def paint_cape(at, name, f, x, y, w, h):
    """Накидка: багрянец, вертикальные складки столбцами, золотая кайма по краям и подолу; изнанка — тёмный багрянец."""
    if name == 'cape_roll':
        at.fill(x, y, w, h, 'N')
        if f in ('north', 'south', 'east', 'west'):
            at.fill(x, y, w, 1, 'P')
            at.fill(x, y + h - 1, w, 1, 'q')
        elif f == 'up':
            at.fill(x, y, w, h, 'O')
        return
    if f in ('east', 'west'):
        at.fill(x, y, w, h, 'q')
        return
    if f == 'down':
        at.fill(x, y, w, h, 'p')
        return
    if f == 'north':                                   # изнанка (к спине)
        for i in range(w):
            at.fill(x + i, y, 1, h, 'M' if i % 3 else 'L')
        at.fill(x, y + h - 1, w, 1, 'q')
        return
    folds = 'POONMNO'
    for i in range(w):
        at.fill(x + i, y, 1, h, folds[i % len(folds)])
    at.fill(x, y, w, 1, 'P')
    at.fill(x, y, 1, h, 'r')
    at.fill(x + w - 1, y, 1, h, 'q')
    at.fill(x, y + h - 2, w, 1, 's')
    at.fill(x, y + h - 1, w, 1, 'q')


def paint_gauntlet(at, name, f, x, y, w, h):
    """«Длань Лжи»: стекло (x…Z) в золотом каркасе: золото — рёбра и кромки, стекло — пластины."""
    if name == 'gaunt_couter' or name == 'gaunt_wing':
        at.fill(x, y, w, h, 'r')
        if f in ('north', 'south', 'east', 'west'):
            at.fill(x, y, w, 1, 't')
            at.fill(x, y + h - 1, w, 1, 'p')
            if name == 'gaunt_wing' and h > 2:
                at.fill(x, y + 1, w, h - 2, 'y')
        elif f == 'down':
            at.fill(x, y, w, h, 'p')
        return
    at.fill(x, y, w, h, 'y')
    if f in ('up', 'down'):
        at.fill(x, y, w, h, 'q' if f == 'up' else 'x')
        return
    for j in range(h):
        for i in range(w):
            at.put(x + i, y + j, 'z' if (i + h - j) % 7 == 0 else ('y' if j < h - 1 else 'x'))
    at.fill(x, y, w, 1, 's')
    at.fill(x, y + h - 1, w, 1, 'q')
    if name == 'gaunt' and w >= 4:
        at.fill(x + w // 2, y, 1, h, 'r')                 # золотое ребро вдоль наруча


def paint_ghost(at, name, f, x, y, w, h):
    """Призрачное стекло: светлая кромка, глубина к центру; прозрачность и трещины — на ×4."""
    at.fill(x, y, w, h, 'g')
    for j in range(h):
        for i in range(w):
            if (i + j) % 4 == 0:
                at.put(x + i, y + j, 'h')
    if w > 1 and h > 1:
        at.fill(x, y, w, 1, 'n')
        at.fill(x, y, 1, h, 'h')
        at.fill(x + w - 1, y, 1, h, 'f')
        at.fill(x, y + h - 1, w, 1, 'f')


def paint_coat(at, name, f, x, y, w, h):
    """Полы камзола: чёрное сукно столбцами-складками, багряный подбой, золотая кайма подола, золотой галун разреза."""
    side = name.endswith('_side')
    front = name.startswith('coat_front')
    right = name.endswith('_r') or name.endswith('_r_side')
    if f in ('up', 'down'):
        at.fill(x, y, w, h, 'r' if f == 'down' else 'c')
        return
    inner_face = (front and f == 'south') or (not front and not side and f == 'north') or \
        (side and ((right and f == 'west') or (not right and f == 'east')))
    if inner_face:
        for i in range(w):
            at.fill(x + i, y, 1, h, 'N' if i % 2 else 'M')
        at.fill(x, y + h - 1, w, 1, 'q')
        return
    if (side or front) and f in ('east', 'west') and w <= 1:
        at.fill(x, y, w, h, 'c')
        at.fill(x, y + h - 2, w, 2, 'q')
        return
    folds = 'dcbab' if w >= 5 else 'dcba'
    for i in range(w):
        at.fill(x + i, y, 1, h, folds[i % len(folds)] if not side else ('cbab'[i % 4]))
    at.fill(x, y, w, 1, 'd')
    at.fill(x, y + h - 3, w, 1, 'O')                      # багряная полоса над каймой
    at.fill(x, y + h - 2, w, 1, 's')
    at.fill(x, y + h - 1, w, 1, 'q')
    if front and f == 'north':
        ie = w - 1 if right else 0
        at.fill(x + ie, y, 1, h, 'r')
        at.put(x + ie, y, 's')
        for j in range(2, h - 3, 3):
            at.put(x + ie, y + j, 's')
    if not front and not side and f == 'south':
        ie = w - 1 if right else 0
        at.fill(x + ie, y + 4, 1, h - 4, 'q')
    if side:
        at.fill(x, y + 1, w, 1, 'c')


# ================================================================== ×4: Scale2x×2 по граням + фактура по материалам + ручные детали
def faces_px(geo):
    """(x0, y0, x1, y1, кость, деталь, грань) в пикселях 512 для всех граней (box UV и per-face)."""
    names = {(b, f, x, y): n for (b, n, f, x, y, w, h) in NEW}
    res = []
    for (x0, y0, x1, y1, bone, face, tag) in G.face_rects(geo):
        nm = names.get((bone, face, int(x0), int(y0)), bone)
        res.append((int(round(x0 * K)), int(round(y0 * K)), int(round(x1 * K)), int(round(y1 * K)), bone, nm, face))
    return res


def upscale(atlas, geo):
    W, H = atlas.size
    big = atlas.resize((W * K, H * K), Image.NEAREST)
    bp = G.pack(big)
    ap = G.pack(atlas)
    for (x0, y0, x1, y1, *_r) in G.face_rects(geo):
        X0, Y0, X1, Y1 = int(math.floor(x0)), int(math.floor(y0)), int(math.ceil(x1)), int(math.ceil(y1))
        sub = ap[Y0:Y1, X0:X1]
        if sub.size:
            bp[Y0 * K:Y1 * K, X0 * K:X1 * K] = G.scale2x(G.scale2x(sub))
    return G.unpack(bp)


def texture_pass(img, rects):
    """Фактура по материалам — правилами (не шум): саржа сукна, нить и складки багрянца, кромки золота, блики стекла."""
    src = img.copy()
    for (X0, Y0, X1, Y1, bone, name, face) in rects:
        w, h = X1 - X0, Y1 - Y0
        if w < 3 or h < 3 or name.startswith(('hair', 'ghost')) or bone == 'head' and not name.startswith(('circlet', 'mask')):
            continue
        r2 = random.Random(hash((X0, Y0)) & 0xFFFF)
        fold_n = r2.choice([1.5, 2, 2.5])
        ph = r2.random() * 6.28
        for y in range(h):
            for x in range(w):
                px = src[Y0 + y, X0 + x]
                if px[3] == 0:
                    continue
                c = tuple(int(v) for v in px[:3])
                f = FAM.get(c)
                if not f:
                    continue
                fam = f[0]
                d = 0
                edge = min(x, y, w - 1 - x, h - 1 - y)
                if fam == 'black':
                    if (x + 2 * y) % 6 == 0:
                        d -= 1
                    if edge == 0:
                        d -= 1
                elif fam == 'crimson':
                    if (x + y) % 4 == 0 and (x // 2 + y) % 3:
                        d -= 1
                    if (x * 13 + y * 7) % 41 == 0:
                        d += 1
                    if face in ('north', 'south', 'east', 'west') and h > 24 and w > 8:
                        s = math.sin(x / w * math.pi * fold_n * 2 + ph + 0.3 * math.sin(y / h * 3))
                        d += 1 if s > 0.93 else (-1 if s < -0.9 else 0)
                    if edge == 0:
                        d -= 1
                elif fam == 'gold':
                    if y == 0:
                        d += 1
                    if y == h - 1:
                        d -= 1
                    if (x * 7 + y * 11) % 43 == 0:
                        d += 2
                elif fam == 'glass':
                    if (x - y) % 9 == 0:
                        d += 1
                    if edge == 0:
                        d += 1
                elif fam in ('grey',):
                    if (x + 2 * y) % 6 == 0:
                        d -= 1
                if d:
                    img[Y0 + y, X0 + x, :3] = shift(c, d)
    return img


def _set(img, x, y, rgba):
    if 0 <= x < img.shape[1] and 0 <= y < img.shape[0]:
        img[y, x] = rgba


def _line(img, pts, rgba, clip=None):
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        n = max(abs(xb - xa), abs(yb - ya), 1)
        for k in range(n + 1):
            x, y = int(round(xa + (xb - xa) * k / n)), int(round(ya + (yb - ya) * k / n))
            if clip is None or (clip[0] <= x < clip[2] and clip[1] <= y < clip[3]):
                _set(img, x, y, rgba)


def face_of(rects, name, face):
    for r in rects:
        if r[5] == name and r[6] == face:
            return r
    raise KeyError((name, face))


# ---------------------------------------------------------------- знак Меллисто (око в пламени), пиксель-арт 14×18
EMBLEM = ['......r.......',
          '.....rs.......',
          '....rsr...r...',
          '....rssr.rs...',
          '..r.rsssrrsr..',
          '..rs.rsssssr..',
          '.rssrsqqqqssr.',
          '.rsqqqLLLLqqsr',
          'rsqLLOPPOLLLqr',
          'rqLLOtLLtOLLqr',
          'rqLOPLaaLPOLqr',
          'rqLLOtLLtOLLqr',
          'rsqLLOPPOLLLqr',
          '.rsqqLLLLLqqr.',
          '.rssqqqqqqssr.',
          '..rsssssssrr..',
          '...rrssssrr...',
          '.....rrrr.....']
EMB_COL = {'r': 'q', 's': 's', 'q': 'p', 'L': 'M', 'O': 'O', 'P': 'Q', 't': 't', 'a': 'a'}


def paint_emblem(img, x0, y0, scale=1, glow=None):
    for j, rr in enumerate(EMBLEM):
        for i, ch in enumerate(rr):
            if ch == '.':
                continue
            for a in range(scale):
                for b in range(scale):
                    _set(img, x0 + i * scale + a, y0 + j * scale + b, C(EMB_COL[ch]))
                    if glow is not None and ch in 'OPt':
                        _set(glow, x0 + i * scale + a, y0 + j * scale + b, C({'O': 'N', 'P': 'O', 't': 'r'}[ch]))


# ---------------------------------------------------------------- маска: золото, прорезь глаза, трещины по виду
MASK_CRACKS = {
    'base': [[(9, 0), (10, 3), (9, 5)], [(17, 13), (15, 15), (16, 18)]],
    'mended': [[(9, 0), (10, 3), (9, 5), (11, 8)], [(17, 13), (15, 15), (16, 18), (14, 21)], [(0, 14), (4, 15), (6, 18), (9, 21)],
               [(18, 4), (14, 6), (13, 9)], [(4, 3), (6, 6)]],
    'cracked': [[(9, 0), (10, 3), (9, 6), (11, 9)], [(17, 13), (15, 15), (16, 18), (14, 21)], [(0, 14), (4, 15), (6, 18), (9, 21)],
                [(18, 4), (15, 6), (14, 10)], [(3, 2), (5, 5), (4, 9)], [(11, 17), (12, 20)]],
}


def paint_mask(img, glow, rects, variant):
    X0, Y0, X1, Y1, *_ = face_of(rects, 'mask', 'north')
    w, h = X1 - X0, Y1 - Y0                               # ≈ 19×22: столбец 0 — край у правого виска (−x), h-1 — низ (скула)
    gold = ['o', 'p', 'q', 'r', 's']
    for y in range(h):
        for x in range(w):
            # объём маски: выпуклая, свет сверху-слева, тень к низу и к краю у носа
            k = 3.4 - y / h * 1.8 - abs(x - w * 0.42) / w * 2.2 + (0.5 if (x * 3 + y) % 11 == 0 else 0)
            ch = gold[max(0, min(4, int(round(k))))]
            img[Y0 + y, X0 + x] = C(ch)
    # контур: справа (у переносицы) — ломаный край, снизу — дуга скулы
    for y in range(h):
        cut = 0
        if y > h * 0.55:
            cut = int((y - h * 0.55) / (h * 0.45) * 7)          # край у носа уходит к скуле
        for x in range(w - cut, w):
            img[Y0 + y, X0 + x] = (0, 0, 0, 0)
        if w - cut - 1 >= 0:
            img[Y0 + y, X0 + w - cut - 1] = C('p')
    for x in range(w):
        lift = int(max(0, (x - w * 0.15)) / w * 4)              # нижний край — дуга
        for y in range(h - lift, h):
            img[Y0 + y, X0 + x] = (0, 0, 0, 0)
        if h - lift - 1 >= 0 and img[Y0 + h - lift - 1, X0 + x, 3]:
            img[Y0 + h - lift - 1, X0 + x] = C('o')
    # прорезь глаза: глаз лица — столбцы 1–2 строки 4 (ед.), маска начинается с x = −4.45 → +0.45 ед. ≈ 2 px
    ex, ey, ew, eh = 6, 11, 8, 5                          # глаз лица: x −3…−1 (столбцы 6…13 маски), y 26…28 (строки 10…18 от верха 30.5)
    for y in range(ey, ey + eh):
        for x in range(ex, ex + ew):
            if (y in (ey, ey + eh - 1)) and x in (ex, ex + ew - 1):
                continue
            img[Y0 + y, X0 + x] = (0, 0, 0, 0)
    _line(img, [(X0 + ex, Y0 + ey - 1), (X0 + ex + ew - 1, Y0 + ey - 1)], C('a'))     # тёмная кромка над прорезью
    _line(img, [(X0 + ex + 1, Y0 + ey + eh), (X0 + ex + ew - 2, Y0 + ey + eh)], C('t'))   # блик под прорезью
    # золотая слеза-капля под прорезью (знак лжеца)
    for (dx, dy, ch) in ((4, 1, 's'), (4, 2, 'r'), (3, 2, 'q'), (4, 3, 'q'), (4, 4, 'p')):
        img[Y0 + ey + eh + dy, X0 + ex + dx] = C(ch)
        if glow is not None and variant != 'base':
            glow[Y0 + ey + eh + dy, X0 + ex + dx] = C('p')
    # трещины: тёмная линия + светлая кромка; у «собранной» — золото по шву (кинцуги), у треснувшей — светятся
    for pts in MASK_CRACKS[variant]:
        P = [(X0 + px, Y0 + py) for (px, py) in pts]
        light = [(X0 + px + 1, Y0 + py) for (px, py) in pts]
        if variant != 'cracked':
            _line(img, light, C('t'), (X0, Y0, X1, Y1))
        _line(img, P, C('a' if variant != 'mended' else 'O'), (X0, Y0, X1, Y1))
        if glow is not None and variant == 'cracked':
            _line(glow, P, C('r'), (X0, Y0, X1, Y1))           # фаза 3: в трещинах тлеет золото
    if variant == 'cracked':
        # выбитый кусок у виска: прозрачно, по краю — тёмный скол
        for (px, py) in ((0, 15), (0, 16), (1, 16), (0, 17), (1, 17), (2, 17), (0, 18), (1, 18), (0, 19)):
            img[Y0 + py, X0 + px] = (0, 0, 0, 0)
        for (px, py) in ((1, 15), (2, 16), (3, 17), (2, 18), (1, 19)):
            img[Y0 + py, X0 + px] = C('o')
    # мелкие грани маски — золото с тенью
    for nm in ('mask_brow', 'mask_cheek'):
        for face in ('north', 'east', 'west', 'up', 'down', 'south'):
            try:
                r = face_of(rects, nm, face)
            except KeyError:
                continue
            a0, b0, a1, b1 = r[:4]
            for y in range(b0, b1):
                for x in range(a0, a1):
                    img[y, x] = C('s' if y == b0 else ('r' if (y - b0) < (b1 - b0) * 0.6 else 'q'))
            if variant == 'cracked' and nm == 'mask_brow' and face == 'north':
                _line(img, [(a0 + 1, b0), (a0 + 3, b0 + 3), (a0 + 2, b1 - 1)], C('a'))
                if glow is not None:
                    _line(glow, [(a0 + 1, b0), (a0 + 3, b0 + 3), (a0 + 2, b1 - 1)], C('r'))


# ---------------------------------------------------------------- накидка: знак культа на спине, фестоны подола
def paint_cape_hi(img, glow, rects):
    X0, Y0, X1, Y1, *_ = face_of(rects, 'cape', 'south')
    w, h = X1 - X0, Y1 - Y0
    paint_emblem(img, X0 + (w - 28) // 2, Y0 + 14, 2, glow)
    # фестоны (зубцы) по подолу: V-вырезы, кромка золотом
    for face in ('south', 'north'):
        X0, Y0, X1, Y1, *_ = face_of(rects, 'cape', face)
        w, h = X1 - X0, Y1 - Y0
        for x in range(w):
            k = x % 8
            cut = [0, 1, 2, 3, 4, 3, 2, 1][k]
            for y in range(h - cut, h):
                img[Y0 + y, X0 + x] = (0, 0, 0, 0)
            img[Y0 + h - cut - 1, X0 + x] = C('q')
            if h - cut - 2 >= 0:
                img[Y0 + h - cut - 2, X0 + x] = C('s')


# ---------------------------------------------------------------- «Длань Лжи»: трещины (кинцуги) и отражение
def paint_gauntlet_hi(img, glow, rects):
    rng = random.Random(31)
    for (X0, Y0, X1, Y1, bone, name, face) in rects:
        if not name.startswith(('gaunt', 'gaunt_knuck', 'gaunt_finger')) or face in ('up', 'down'):
            continue
        w, h = X1 - X0, Y1 - Y0
        glass = [(x, y) for y in range(Y0, Y1) for x in range(X0, X1) if FAM.get(tuple(int(v) for v in img[y, x, :3]), ('',))[0] == 'glass']
        for (x, y) in glass:                                             # мерцающее отражение в стекле — глоумаска
            t = ((x - X0) * 2 + (y - Y0)) % 23
            if t in (0, 1):
                glow[y, x] = C('z' if t == 0 else 'y')
            elif (x * 5 + y * 3) % 29 == 0:
                glow[y, x] = C('x')
        if name in ('gaunt', 'gaunt_knuck') and w >= 8 and h >= 6:       # трещины с золотым швом
            for _ in range(2 if name == 'gaunt' else 1):
                x, y = X0 + rng.randrange(1, w - 1), Y0 + rng.randrange(1, max(2, h // 2))
                pts = [(x, y)]
                for _k in range(4):
                    x += rng.choice((-2, -1, 1, 2))
                    y += rng.choice((2, 3))
                    pts.append((x, min(Y1 - 2, y)))
                _line(img, pts, C('s'), (X0, Y0, X1, Y1))
                _line(glow, pts, C('q'), (X0, Y0, X1, Y1))


# ---------------------------------------------------------------- призрачная рука: прозрачность, золотые швы фаланг, трещины
GHOST_A, GHOST_RIM, GHOST_CRACK = 150, 205, 255


def paint_ghost_hi(img, glow, rects):
    rng = random.Random(77)
    for (X0, Y0, X1, Y1, bone, name, face) in rects:
        if not bone.startswith('ghost'):
            continue
        w, h = X1 - X0, Y1 - Y0
        for y in range(Y0, Y1):
            for x in range(X0, X1):
                if img[y, x, 3] == 0:
                    continue
                c = tuple(int(v) for v in img[y, x, :3])
                fam = FAM.get(c, ('', 0))
                rim = min(x - X0, y - Y0, X1 - 1 - x, Y1 - 1 - y) == 0
                a = GHOST_RIM if rim else GHOST_A
                if name == 'ghost_mist':                              # «туман» запястья тает книзу
                    a = int(GHOST_A * max(0.0, 1 - (y - Y0) / h) ** 1.4)
                img[y, x, 3] = a
                gl = {'f': 0, 'g': 1, 'h': 2, 'n': 3}.get('fghn'[fam[1]] if fam[0] == 'ghost' else 'f', 0)
                glow[y, x] = (*C('fghn'[min(3, gl + (1 if rim else 0))])[:3], 255 if a > 40 else 0)
        # золотой шов у основания каждой фаланги (стекло собрано золотом) и трещины на ладони
        if face in ('north', 'south', 'east', 'west') and (name.startswith('ghost_') and name[-1:].isdigit()):
            for x in range(X0, X1):
                img[Y0, x] = C('s', GHOST_CRACK)
                glow[Y0, x] = C('r')
        if name == 'ghost_palm' and face in ('north', 'south'):
            for _ in range(3):
                x, y = X0 + rng.randrange(2, w - 2), Y0 + rng.randrange(1, h // 2)
                pts = [(x, y)]
                for _k in range(5):
                    x += rng.choice((-2, -1, 1, 2))
                    y += rng.choice((1, 2))
                    pts.append((x, min(Y1 - 1, y)))
                _line(img, pts, C('s', GHOST_CRACK), (X0, Y0, X1, Y1))
                _line(glow, pts, C('s'), (X0, Y0, X1, Y1))
        if name == 'ghost_wrist' and face in ('north', 'south', 'east', 'west'):
            yy = Y0 + h // 2
            for x in range(X0, X1):
                img[yy, x] = C('r', GHOST_CRACK)
                glow[yy, x] = C('q')


def textures(geo):
    at = E.Atlas()
    paint_skin(at)
    paint_new(at)
    rects = faces_px(geo)
    base = upscale(at.img, geo)
    base = texture_pass(base, rects)
    res = {}
    for variant, nm in (('base', 'ereb_hand'), ('mended', 'ereb_hand_mended'), ('cracked', 'ereb_hand_cracked')):
        img = base.copy()
        glow = np.zeros_like(img)
        X0, Y0, X1, Y1, *_ = face_of(rects, 'medallion', 'north')
        img[Y0:Y1, X0:X1] = C('L')
        img[Y0, X0:X1] = C('s')
        img[Y1 - 1, X0:X1] = C('p')
        img[Y0:Y1, X0] = C('r')
        img[Y0:Y1, X1 - 1] = C('q')
        paint_emblem(img, X0, Y0, 1, glow)
        paint_mask(img, glow, rects, variant)
        paint_cape_hi(img, glow, rects)
        paint_gauntlet_hi(img, glow, rects)
        paint_ghost_hi(img, glow, rects)
        # венец: камень на зубце — багряный, светится
        X0, Y0, X1, Y1, *_ = face_of(rects, 'circlet_peak', 'north')
        for (dx, dy, ch) in ((2, 2, 'P'), (3, 2, 'Q'), (2, 3, 'O'), (3, 3, 'P'), (2, 4, 'N'), (3, 4, 'O')):
            img[Y0 + dy, X0 + dx] = C(ch)
            glow[Y0 + dy, X0 + dx] = C('N')
        # глаза: левая радужка (голубая) едва светится; правая — золотая «ложная» в прорези маски
        for (x, y) in ((5, 4), (5, 5)):
            for a in range(K):
                for b in range(K):
                    X, Y = (8 + x) * K + a, (8 + y) * K + b
                    glow[Y, X] = hx('#1d6a80') if FAM.get(tuple(int(v) for v in img[Y, X, :3]), ('',))[0] != 'skin' else glow[Y, X]
        for (x, y) in ((2, 4), (2, 5)):
            for a in range(K):
                for b in range(K):
                    X, Y = (8 + x) * K + a, (8 + y) * K + b
                    if 0 < a < K - 1 and (y == 4 or b < 2):
                        glow[Y, X] = C('q') if (a + b) % 2 else C('r')
        im = Image.fromarray(img, 'RGBA')
        im.save(out(TEX + nm + '.png'))
        Image.fromarray(glow, 'RGBA').save(out(TEX + nm + '_glowmask.png'))
        res[nm] = im
    return res


# ================================================================== рапира со стеклянным клинком
RAP_PAL = dict(E.RAP_PAL)
RAP_PAL.update({'k': '#5f86c8', 'k1': '#9cc4f2', 'k2': '#d4ecff', 'k3': '#f4fbff',      # клинок — стекло (вместо чёрной стали)
                'c1': '#7e1f2b', 'c2': '#c95560'})                                     # вставка гарды — багряный камень


def rapier():
    pal = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for k, (x, y) in E.RAP_CELL.items():
        pal.putpixel((x, y), hx(RAP_PAL[k]))
    pal.save(out('textures/item/ereb_hand_rapier_3d.png'))
    icon = E.Atlas(16, 16)
    E.PAL.update({'0': '#9cc4f2', '9': '#e8f6ff', '8': '#5f86c8'})
    rows = ['...............9',
            '..............90',
            '.............908',
            '............908.',
            '...........908..',
            '..........90r...',
            '.........908....',
            '........90r.....',
            '.......908......',
            '..r..qr8........',
            '..srOPr.........',
            '...rsr..........',
            '..qbrq..........',
            '.qbq.r..........',
            'tsq..q..........',
            'rq..............']
    icon.art(0, 0, rows)
    icon.img.save(out('textures/item/ereb_hand_rapier.png'))
    doc = _rapier_doc()
    doc['base']['textures'] = {'p': 'pohsmp_core:item/ereb_hand_rapier_3d', 'particle': 'pohsmp_core:item/ereb_hand_rapier'}
    flat = {'parent': 'minecraft:item/handheld', 'textures': {'layer0': 'pohsmp_core:item/ereb_hand_rapier'}}
    doc['perspectives'] = {'gui': flat, 'ground': flat, 'fixed': flat}
    write_json('models/item/ereb_hand_rapier.json', doc)
    return doc


def _rapier_doc():
    """Документ рапиры T30 (бруски и дисплей) — читаем принятый файл T30, не меняя его."""
    return json.load(open(os.path.join(A, 'models', 'item', 'ereb_rapier.json'), encoding='utf-8'))



# ================================================================== main
def main():
    args = sys.argv[1:]
    if not os.path.exists(E.JAR):
        sys.exit('нет %s — запустите python3 tools/fetch_libs.py' % E.JAR)
    geo = build_model()
    textures(geo)
    rapier()
    import gen_ereb_hand_anims as AN
    AN.write(sys.modules[__name__])
    if '--no-ui' not in args:
        import gen_ereb_hand_ui as UI
        UI.run(sys.modules[__name__], args)
    print('\n'.join('  ' + w for w in WRITTEN))


if __name__ == '__main__':
    main()
