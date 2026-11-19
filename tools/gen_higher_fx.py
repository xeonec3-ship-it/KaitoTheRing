#!/usr/bin/env python3
"""
Эффекты Высшей школы (стиль `higher`: алый, тёмно-багровый, белое ядро; острые осколки, трещины) — замена временных:
  fx/scarlet_cut.json  — «Алый разрез» (T02). Один экземпляр = один разрез: `at` — середина дуги, `point:ground` — трещина под ней,
                         yaw — взгляд. Сервер взрывает трещину на тике 20 — взрыв держать на 20.
  fx/star_fall.json    — «Падение звезды» (T05). Точки `point:impact`, `point:sky`; каст 0–160, звезда с 100 (easeInCubic), удар на 160,
                         кратер до 760 (ролик камеры рассчитан на эти числа).
Печати: sigils/scarlet_cut_seal.json, star_fall_target.json, star_fall_sky.json; модель fx/meshes/star_glass.json (алое «стекло» в кратере).
Запуск: python3 tools/gen_higher_fx.py
"""
import json
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
R3 = lambda v: round(v, 3)


def dump(rel, doc, compact=False):
    with open(os.path.join(A, rel), 'w', encoding='utf-8') as f:
        if compact:
            json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
        else:
            json.dump(doc, f, ensure_ascii=False, indent=1)
    print('wrote', rel)


def sigils():
    dump('sigils/scarlet_cut_seal.json', {
        'comment': 'Алая печать у разреза (T02): вспыхивает поперёк взгляда в начале взмаха, клинки по ободу, гаснет со сколами.',
        'size': 0.7, 'color': '#FF2A3A', 'orientation': 'facing', 'lifetime': -1, 'hold': 4,
        'layers': [
            {'id': 'glow', 'type': 'disc', 'texture': 'glow', 'radius': 1.3, 'brightness': 0.7, 'color': '#FF5A64',
             'appear': {'delay': 0, 'duration': 3, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}},
            {'id': 'cracks', 'type': 'disc', 'texture': 'higher_cracks', 'radius': 1.0,
             'appear': {'delay': 0, 'duration': 4, 'easing': 'easeOutBack', 'modes': ['grow', 'twist', 'fade'], 'twist': -90}, 'rotation': {'speed': 120}},
            {'id': 'blades', 'type': 'disc', 'texture': 'cross_spikes', 'radius': 1.15, 'color': '#FFFFFF',
             'appear': {'delay': 1, 'duration': 3, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}, 'rotation': {'speed': -200}}],
        'dissolve': {'modes': ['shatter'], 'duration': 8}})
    dump('sigils/star_fall_target.json', {
        'comment': 'Печать-прицел «Падения звезды» на земле (T05): собирается по частям за каст, звёздное кольцо, руны, шипы; '
                   'к удару раскручивается быстрее. Радиус 8 блоков.',
        'size': 2.0, 'color': '#FF2A3A', 'orientation': 'ground', 'lifetime': -1, 'hold': -1,
        'layers': [
            {'id': 'glow', 'type': 'disc', 'texture': 'glow', 'radius': 1.05, 'heightOffset': -0.02, 'brightness': 0.5, 'color': '#7A0A1E',
             'appear': {'delay': 0, 'duration': 20, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}, 'pulse': {'amp': 0.25, 'period': 30}},
            {'id': 'cracks', 'type': 'disc', 'texture': 'higher_cracks', 'radius': 0.95, 'color': '#FF5A64', 'brightness': 0.8,
             'appear': {'delay': 0, 'duration': 30, 'easing': 'easeInOutSine', 'modes': ['draw']}, 'rotation': {'speed': 4}},
            {'id': 'star', 'type': 'disc', 'texture': 'star_ring', 'radius': 0.62, 'color': '#FFFFFF',
             'appear': {'delay': 10, 'duration': 30, 'easing': 'easeOutBack', 'modes': ['pieces'],
                        'pieces': {'count': 8, 'order': 'alternate', 'pieceTime': 0.4, 'fly': 0.6, 'lift': 0.6, 'orbit': 40, 'tilt': 80, 'spin': 120}},
             'rotation': {'speed': -10, 'boost': 1.0}},
            {'id': 'runes', 'type': 'band', 'texture': 'rune_band', 'radius': 0.86, 'inner': 0.8, 'repeat': 8, 'color': '#FF2A3A',
             'appear': {'delay': 26, 'duration': 30, 'easing': 'easeInOutSine', 'modes': ['draw']}, 'rotation': {'speed': 8}},
            {'id': 'spikes', 'type': 'disc', 'texture': 'cross_spikes', 'radius': 0.42, 'color': '#FFD0D4',
             'appear': {'delay': 40, 'duration': 16, 'easing': 'easeOutBack', 'modes': ['grow', 'twist', 'fade']}, 'rotation': {'speed': 30, 'boost': 2}},
            {'id': 'rim', 'type': 'disc', 'texture': 'rim', 'radius': 1.0, 'heightOffset': 0.02,
             'appear': {'delay': 50, 'duration': 16, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}, 'rotation': {'speed': -3}}],
        'expand': {'scale': 4.0, 'delay': 2, 'duration': 30, 'easing': 'easeOutCubic'},
        'formedFlash': {'color': '#FFD0D4', 'size': 1.2, 'duration': 16, 'sparks': 60},
        'dissolve': {'modes': ['shatter'], 'duration': 12}})
    dump('sigils/star_fall_sky.json', {
        'comment': 'Звёздная печать в небе (T05): раскрывается перед падением, созвездие и звёздное кольцо, из её центра падает звезда.',
        'size': 2.5, 'color': '#FF5A64', 'orientation': 'sky', 'lifetime': -1, 'hold': -1,
        'layers': [
            {'id': 'glow', 'type': 'disc', 'texture': 'glow', 'radius': 1.1, 'brightness': 0.6, 'color': '#FF2A3A',
             'appear': {'delay': 0, 'duration': 12, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}, 'pulse': {'amp': 0.3, 'period': 20}},
            {'id': 'stars', 'type': 'disc', 'texture': 'constellation', 'radius': 1.0, 'color': '#FFFFFF',
             'appear': {'delay': 0, 'duration': 20, 'easing': 'easeOutCubic', 'modes': ['grow', 'twist', 'fade'], 'twist': -160},
             'rotation': {'speed': 12, 'boost': 3}},
            {'id': 'ring', 'type': 'disc', 'texture': 'star_ring', 'radius': 0.7,
             'appear': {'delay': 6, 'duration': 16, 'easing': 'easeOutBack', 'modes': ['grow', 'fade']}, 'rotation': {'speed': -20, 'boost': 2}},
            {'id': 'rim', 'type': 'disc', 'texture': 'rim', 'radius': 1.04,
             'appear': {'delay': 12, 'duration': 10, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}}],
        'expand': {'scale': 4.0, 'delay': 0, 'duration': 22, 'easing': 'easeOutCubic'},
        'formedFlash': {'color': '#FFFFFF', 'size': 1.3, 'duration': 14, 'sparks': 50},
        'dissolve': {'modes': ['reverse', 'collapse'], 'duration': 20, 'stagger': 3}})


def star_glass():
    """Алое «стекло» в кратере: десятки граненых осколков-кристаллов из земли, наклонены от центра, ниже к краю (только вид)."""
    rnd = random.Random(160)
    C = []

    def shard(x, z, h, r, lx, lz):
        n, segs = 5, 4
        for k in range(segs):
            y0, y1 = h * k / segs, h * (k + 1) / segs
            rr = r * (1 - 0.82 * k / segs)
            cx, cz = x + lx * (y0 + y1) / 2, z + lz * (y0 + y1) / 2
            side = 2 * rr * math.tan(math.pi / n) + 0.02
            for i in range(n):
                a = 2 * math.pi * (i + 0.5) / n
                C.append([R3(cx + (rr - 0.05) * math.cos(a) - 0.05), R3(y0), R3(cz + (rr - 0.05) * math.sin(a) - side / 2),
                          R3(cx + (rr - 0.05) * math.cos(a) + 0.05), R3(y1), R3(cz + (rr - 0.05) * math.sin(a) + side / 2),
                          3 if i % 2 == 0 else 2, [0, R3(-math.degrees(a)), 0]])
            C.append([R3(cx - rr * 0.45), R3(y0), R3(cz - rr * 0.45), R3(cx + rr * 0.45), R3(y1), R3(cz + rr * 0.45), 4])
    for i in range(34):
        a = rnd.uniform(0, 2 * math.pi)
        d = rnd.uniform(1.0, 6.5)
        h = (2.6 * (1 - d / 7.5) + 0.4) * rnd.uniform(0.6, 1.0)
        r = rnd.uniform(0.18, 0.5)
        shard(d * math.cos(a), d * math.sin(a), h, r, 0.25 * math.cos(a), 0.25 * math.sin(a))
    ys = [b[1] for b in C] + [b[4] for b in C]
    dump('fx/meshes/star_glass.json', {
        'comment': 'Алое «стекло» в кратере «Падения звезды» (T05): осколки-кристаллы из земли, только вид. Сгенерировано tools/gen_higher_fx.py.',
        'style': 'higher', 'center': 0, 'formedAt': 14, 'collapse': {'duration': 40, 'easing': 'easeInSine'},
        'parts': [{'type': 'boxes', 'tones': ['#2A0008', '#7A0A1E', '#C21A2E', '#FF7A84', '#FF2A3A'], 'glowTones': [4], 'blend': 'translucent',
                   'opacity': 0.85, 'shade': True, 'boxes': C,
                   'appear': {'delay': 0, 'duration': 14, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.6}, 'bounds': [min(ys), max(ys)]}]},
         compact=True)


def scarlet_cut():
    E = [
        {'type': 'sigil', 'id': 'scarlet_cut_seal', 'delay': 0, 'at': 'caster', 'comment': 'алая печать поперёк взгляда в начале взмаха'},
        {'type': 'trail', 'shape': 'slash', 'delay': 0, 'duration': 9, 'at': 'caster', 'radius': 2.7, 'arc': 120, 'thickness': 0.46, 'sweep': 3,
         'bend': 0.32, 'roll': 18, 'rollAlt': True, 'secondary': 0.75, 'color': '@primary', 'brightness': 1.5, 'comment': 'главный серп: алый, белое ядро'},
        {'type': 'trail', 'shape': 'slash', 'delay': 1, 'duration': 12, 'at': 'caster', 'radius': 2.95, 'arc': 100, 'thickness': 0.22, 'sweep': 4,
         'bend': 0.36, 'roll': 18, 'rollAlt': True, 'secondary': 0.0, 'color': '@secondary', 'brightness': 0.8, 'comment': 'послеобраз: тёмно-багровый, шире и позже'},
        {'type': 'trail', 'shape': 'slash', 'delay': 0, 'duration': 6, 'at': 'caster', 'radius': 2.6, 'arc': 130, 'thickness': 0.08, 'sweep': 3,
         'bend': 0.3, 'roll': 18, 'rollAlt': True, 'secondary': 0.0, 'color': '@core', 'brightness': 1.8, 'comment': 'тонкая белая кромка лезвия'},
        {'type': 'flash', 'delay': 2, 'duration': 5, 'at': 'caster', 'size': 1.6, 'anamorphic': 6, 'rays': 4, 'color': '@core'},
        {'type': 'sprites', 'delay': 2, 'duration': 4, 'at': 'caster', 'texture': '@sparks', 'count': 30, 'rate': 8, 'spread': 1.6, 'speed': 0.14,
         'gravity': 0.012, 'size': [0.16, 0.02], 'life': 12, 'color': '@primary', 'comment': 'искры с лезвия'},
        {'type': 'sprites', 'delay': 3, 'duration': 3, 'at': 'caster', 'texture': '@shards', 'count': 10, 'rate': 4, 'spread': 1.2, 'speed': 0.08,
         'gravity': 0.02, 'spin': 500, 'size': [0.14, 0.04], 'life': 14, 'color': '@primary', 'comment': 'сколы воздуха'},
        {'type': 'decal', 'shape': 'crack', 'delay': 2, 'duration': 22, 'at': 'point:ground', 'length': 4.2, 'width': 0.15, 'grow': 5, 'branches': 8,
         'pulse': 1.0, 'fadeOut': 3, 'color': '@primary', 'brightness': 1.3, 'comment': 'трещина-разлом, пульсирует всё чаще к взрыву'},
        {'type': 'decal', 'delay': 4, 'duration': 18, 'at': 'point:ground', 'texture': 'glow', 'radius': 1.6, 'fadeOut': 4, 'color': '@secondary',
         'brightness': 0.6, 'comment': 'жар под трещиной'},
        {'type': 'sprites', 'delay': 6, 'duration': 14, 'at': 'point:ground+0,0.1,0', 'texture': '@sparks', 'count': 40, 'rate': 3, 'area': 1.8,
         'speed': 0.02, 'gravity': -0.003, 'size': [0.1, 0.02], 'life': 16, 'color': '@primary', 'comment': 'искры поднимаются из трещины'},
        # тик 20 — взрыв трещины (сервер наносит урон в этот же тик)
        {'type': 'flash', 'delay': 20, 'duration': 9, 'at': 'point:ground+0,0.5,0', 'size': 2.6, 'anamorphic': 8, 'rays': 8, 'screen': 0.15, 'color': '@core'},
        {'type': 'beam', 'delay': 20, 'duration': 8, 'at': 'point:ground+-1.2,0,0', 'to': 'point:ground+-1.4,2.6,0', 'width': 0.18, 'core': 0.5, 'grow': 3,
         'color': '@primary', 'out': {'duration': 5, 'easing': 'easeInSine'}, 'comment': 'алые столбы-осколки бьют из трещины'},
        {'type': 'beam', 'delay': 20, 'duration': 9, 'at': 'point:ground', 'to': 'point:ground+0.2,3.4,0', 'width': 0.26, 'core': 0.55, 'grow': 3,
         'color': '@primary', 'out': {'duration': 6, 'easing': 'easeInSine'}},
        {'type': 'beam', 'delay': 21, 'duration': 8, 'at': 'point:ground+1.3,0,0', 'to': 'point:ground+1.6,2.4,0', 'width': 0.16, 'core': 0.5, 'grow': 3,
         'color': '@primary', 'out': {'duration': 5, 'easing': 'easeInSine'}},
        {'type': 'wave', 'delay': 20, 'duration': 10, 'at': 'point:ground', 'radius': 2.2, 'thickness': 0.4, 'color': '@primary'},
        {'type': 'sprites', 'delay': 20, 'duration': 2, 'at': 'point:ground+0,0.2,0', 'texture': '@shards', 'count': 34, 'rate': 34, 'area': 1.8,
         'speed': 0.2, 'gravity': 0.03, 'spin': 400, 'tumble': 0.8, 'size': [0.24, 0.08], 'life': 22, 'color': '@primary', 'comment': 'осколки вдоль трещины'},
        {'type': 'sprites', 'delay': 21, 'duration': 3, 'at': 'point:ground+0,0.3,0', 'texture': '@sparks', 'count': 40, 'rate': 14, 'area': 1.6,
         'speed': 0.16, 'gravity': 0.01, 'size': [0.14, 0.02], 'life': 14, 'color': '@core'},
        {'type': 'decal', 'delay': 22, 'duration': 22, 'at': 'point:ground', 'texture': 'higher_cracks', 'radius': 1.5, 'fadeOut': 18, 'color': '@secondary',
         'comment': 'выжженный след после взрыва'},
    ]
    # the cut flies forward (owner, 19.11.2026): blade, its flash and sparks start 2 blocks back and travel 0.5 block/tick
    for e in E:
        if e['at'] == 'caster' and e['type'] in ('trail', 'flash', 'sprites'):
            if e['type'] == 'trail':
                e['duration'] += 5
            e['at'] = 'caster+0,0,-2'
            e['travel'] = round(0.5 * e['duration'], 2)
    dump('fx/scarlet_cut.json', {
        'comment': '«Алый разрез» (T02). Один экземпляр = один разрез: at = середина дуги (на высоте груди), point:ground = место трещины под ней, '
                   'yaw — взгляд заклинателя. Сервер (ScarletCutSpell) взрывает трещину на тике 20 — взрыв держать на 20. Сгенерировано tools/gen_higher_fx.py.',
        'style': 'higher', 'duration': 44, 'elements': E})


def star_fall():
    SF = 3   # радиус удара ×3 (владелец 19.11: 8 → 24 блока); то же в StarFallSpell.R
    E = [
        # каст 0–160: прицел на земле собирается, искры поднимаются, лучи-наводки
        {'type': 'sigil', 'id': 'star_fall_target', 'delay': 0, 'until': 164, 'at': 'point:impact', 'scale': SF, 'comment': 'печать-прицел радиусом 24 (владелец 19.11: ×3, было 8)'},
        {'type': 'sprites', 'at': 'point:impact', 'delay': 10, 'duration': 150, 'count': 900, 'rate': 6, 'area': 7.5 * SF, 'speed': 0.03, 'gravity': -0.004,
         'life': 50, 'size': [0.14, 0.02], 'texture': '@sparks', 'color': '#FF6A70', 'comment': 'искры поднимаются над прицелом'},
        {'type': 'wave', 'at': 'point:impact', 'delay': 60, 'duration': 40, 'radius': 8 * SF, 'color': '@primary', 'brightness': 0.6},
        {'type': 'wave', 'at': 'point:impact', 'delay': 110, 'duration': 40, 'radius': 8 * SF, 'color': '#FF6A70', 'brightness': 0.9},
        # луч-наводка с земли убран (владелец, 19.11.2026)
        # звёздная печать в небе раскрывается, звезда вспыхивает
        {'type': 'sigil', 'id': 'star_fall_sky', 'delay': 64, 'until': 150, 'at': 'point:sky', 'orientation': 'sky'},
        {'type': 'flash', 'at': 'point:sky', 'delay': 96, 'duration': 16, 'size': 10, 'rays': 10, 'anamorphic': 16, 'color': '#FFFFFF'},
        # падение 100–160: шлейф (алый, широкий), ядро (белое), искры вдоль пути
        {'type': 'beam', 'at': 'point:sky', 'to': 'point:impact', 'delay': 100, 'duration': 62, 'grow': 60, 'easing': 'easeInCubic', 'tail': 0.45,
         'width': 2.8, 'core': 0.3, 'taper': 0.9, 'head': 3.8, 'color': '@primary', 'brightness': 1.2, 'comment': 'шлейф и голова звезды'},
        {'type': 'beam', 'at': 'point:sky', 'to': 'point:impact', 'delay': 100, 'duration': 62, 'grow': 60, 'easing': 'easeInCubic', 'tail': 0.25,
         'width': 1.5, 'core': 0.5, 'taper': 0.8, 'head': 4.2, 'color': '@secondary', 'brightness': 0.9},
        {'type': 'beam', 'at': 'point:sky', 'to': 'point:impact', 'delay': 100, 'duration': 62, 'grow': 60, 'easing': 'easeInCubic', 'tail': 0.12,
         'width': 0.9, 'core': 0.7, 'taper': 0.6, 'head': 4.6, 'color': '#FFFFFF', 'brightness': 1.6, 'comment': 'белое ядро'},
        {'type': 'sprites', 'at': 'point:sky', 'delay': 100, 'duration': 60, 'texture': '@sparks', 'count': 400, 'rate': 7, 'spread': 2.5, 'speed': 0.05,
         'gravity': 0.01, 'size': [0.2, 0.04], 'life': 30, 'color': '#FF6A70', 'comment': 'искры с неба'},
        {'type': 'tint', 'delay': 100, 'duration': 90, 'at': 'point:impact', 'radius': 64 * 2, 'color': '#5A0A14', 'strength': 0.3,
         'in': {'duration': 40, 'easing': 'easeInSine'}, 'out': {'duration': 30, 'easing': 'easeOutSine'}, 'comment': 'мир краснеет к удару'},
        # удар 160
        {'type': 'flash', 'at': 'point:impact+0,1.5,0', 'delay': 160, 'duration': 26, 'size': 18 * 2, 'rays': 14, 'anamorphic': 30, 'color': '#FFFFFF', 'screen': 0.85},
        {'type': 'column', 'at': 'point:impact', 'delay': 160, 'duration': 18, 'radius': 4.5 * SF, 'height': 60, 'fill': 0.8, 'color': '#FF2A3A',
         'out': {'duration': 12, 'easing': 'easeInSine'}, 'comment': 'столб света в момент удара'},
        {'type': 'wave', 'shape': 'sphere', 'at': 'point:impact', 'delay': 160, 'duration': 24, 'radius': 10 * SF, 'rim': 1.0, 'color': '#FF6A70'},
        {'type': 'wave', 'at': 'point:impact', 'delay': 160, 'duration': 30, 'radius': 22 * SF, 'thickness': 1.2 * SF, 'color': '#FFFFFF', 'brightness': 1.4},
        {'type': 'wave', 'at': 'point:impact', 'delay': 164, 'duration': 40, 'radius': 15 * SF, 'thickness': 0.8 * SF, 'color': '@primary'},
        {'type': 'sprites', 'at': 'point:impact+0,0.5,0', 'delay': 160, 'duration': 4, 'texture': '@shards', 'count': 480, 'rate': 120, 'spread': 1.5 * SF,
         'speed': 0.6, 'gravity': 0.04, 'spin': 300, 'tumble': 1, 'size': [0.4, 0.14], 'life': 50, 'color': '#3A0A10', 'comment': 'обломки земли'},
        {'type': 'sprites', 'at': 'point:impact+0,0.5,0', 'delay': 160, 'duration': 6, 'texture': '@sparks', 'count': 600, 'rate': 120, 'spread': 1.0 * SF,
         'speed': 0.5, 'gravity': 0.02, 'size': [0.22, 0.04], 'life': 30, 'color': '#FF6A70'},
        # кратер и «стекло» до 760
        {'type': 'decal', 'at': 'point:impact', 'delay': 162, 'duration': 598, 'texture': 'glow', 'radius': 6 * SF, 'fadeOut': 120, 'color': '#2A0008',
         'blend': 'translucent', 'comment': 'тёмная выжженная чаша (под трещинами)'},
        {'type': 'decal', 'at': 'point:impact', 'delay': 162, 'duration': 598, 'texture': 'higher_cracks', 'radius': 7 * SF, 'fadeOut': 80, 'color': '#C21A2E',
         'brightness': 0.9, 'comment': 'трещины кратера'},
        {'type': 'mesh', 'model': 'star_glass', 'delay': 164, 'until': 760, 'at': 'point:impact', 'scale': SF, 'comment': 'алое стекло-кристаллы'},
        {'type': 'sprites', 'at': 'point:impact+0,0.3,0', 'delay': 170, 'duration': 500, 'texture': '@sparks', 'count': 2400, 'rate': 4.8, 'area': 6 * SF,
         'speed': 0.01, 'gravity': -0.002, 'size': [0.12, 0.02], 'life': 60, 'color': '#FF6A70', 'comment': 'тлеющие искры над кратером'},
    ]
    dump('fx/star_fall.json', {
        'comment': '«Падение звезды» (T05, Высшая). Точки point:impact и point:sky; каст 0–160 (прицел собирается), 64 — звёздная печать в небе, '
                   '100 — звезда падает (easeInCubic), 160 — удар, кратер и алое стекло до 760. Ролик камеры (DownfallCut, сцена 6) — на этих числах. '
                   'Сгенерировано tools/gen_higher_fx.py.',
        'style': 'higher', 'duration': 760, 'elements': E})


if __name__ == '__main__':
    sigils()
    star_glass()
    scarlet_cut()
    star_fall()
