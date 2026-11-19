#!/usr/bin/env python3
"""
Печати, эффекты и стили мифических заклинаний (docs/fx.md, docs/sigils.md): Застывший час, Табу, Низвержение,
Млечный путь, Пожирание душ, Закрытие пространства, Падение небес, Взрыв, Восемь щитов, Ковчег, Кровавая луна, Разлом мира.

Пишет: assets/pohsmp_core/sigils/<id>.json, fx/<id>.json, fx/meshes/<id>.json, fx/styles/<id>.json.
Текстуры — tools/gen_mythic_textures.py и tools/gen_sigil_textures.py. Правки лучше вносить здесь и перезапускать:
    python3 tools/gen_mythic_fx.py
Раскладка повторяющихся элементов (облако циферблатов, столбы гептаграммы, точки разлома) считается кодом ниже.
Время — тики, углы — градусы, размеры — блоки.
"""
import json
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
WRITTEN = []


def write(rel, obj):
    path = os.path.join(A, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write('\n')
    WRITTEN.append(rel)


# ------------------------------------------------------------------ помощники
def ap(delay, dur, *modes, easing='easeOutCubic', **kw):
    d = {'delay': delay, 'duration': dur, 'easing': easing, 'modes': list(modes)}
    d.update(kw)
    return d


def L(id, type, tex, radius, h=0.0, appear=None, rot=None, boost=None, color=None, br=None, pulse=None, **kw):
    o = {'id': id, 'type': type, 'texture': tex, 'radius': radius, 'heightOffset': h}
    if color:
        o['color'] = color
    if br is not None:
        o['brightness'] = br
    o.update(kw)
    o['appear'] = appear or ap(0, 10, 'fade')
    if rot is not None:
        o['rotation'] = {'speed': rot, **({'boost': boost} if boost else {})}
    if pulse:
        o['pulse'] = {'amp': pulse[0], 'period': pulse[1]}
    return o


def sigil(id, comment, size, color, orientation, layers, hold=-1, lifetime=-1, expand=None, flash=None, children=None,
          dissolve=('reverse', 'collapse'), ddur=20, stagger=2, hit=None):
    o = {'comment': comment, 'size': size, 'color': color, 'orientation': orientation, 'lifetime': lifetime, 'hold': hold,
         'layers': layers}
    if expand:
        o['expand'] = expand
    if flash:
        o['formedFlash'] = flash
    if children:
        o['onFormed'] = children
    if hit is not None:
        o['hit'] = hit   # T08: отклик на удар (docs/sigils.md)
    o['dissolve'] = {'modes': list(dissolve), 'duration': ddur, 'stagger': stagger}
    write('sigils/%s.json' % id, o)


def fx(id, comment, style, duration, elements):
    write('fx/%s.json' % id, {'comment': comment, 'style': style, 'duration': duration, 'elements': elements})


def E(type, delay=0, at='caster', **kw):
    o = {'type': type, 'delay': delay, 'at': at}
    o.update(kw)
    return o


def ease(d, e='easeOutCubic'):
    return {'duration': d, 'easing': e}


def off(x, y, z, base='caster'):
    return '%s+%s,%s,%s' % (base, fmt(x), fmt(y), fmt(z))


def fmt(v):
    v = round(v, 2)
    return str(int(v)) if v == int(v) else str(v)


def style(id, comment, primary, secondary, core, shadow, sparks='spark_soft', shards='shard', sig='core', rot=0.8, jitter=0.0,
          easing='easeOutSine', pulse=None):
    o = {'comment': comment, 'palette': {'primary': primary, 'secondary': secondary, 'core': core, 'shadow': shadow},
         'textures': {'sparks': sparks, 'runes': 'rune_band', 'shards': shards, 'sigil': sig}, 'blend': 'additive',
         'motion': {'rotationScale': rot, 'jitter': jitter, 'easing': easing}}
    if pulse:
        o['motion']['pulse'] = pulse
    write('fx/styles/%s.json' % id, o)


# ------------------------------------------------------------------ стили
def styles():
    style('chrono', 'Время: золото на холодном сером, бледно-ледяные отблески; циферблаты, шестерёнки, застывшие пылинки.',
          '#F2C86B', '#CFE6FF', '#FFFFFF', '#3A4458', sig='clock_face', rot=0.5)
    style('astral', 'Звёзды: фиолетовый и серебро, белое ядро; созвездия, орбиты, туманности.',
          '#A07CFF', '#D8DCFF', '#FFFFFF', '#1A0F40', sparks='spark_sharp', sig='constellation', rot=1.0)
    style('pyre', 'Пламя: оранжевый и жёлтый, белое ядро; языки огня, трещины, угли.',
          '#FF6A1E', '#FFC23A', '#FFF2C0', '#3A0A00', sparks='spark_sharp', shards='spark_sharp', sig='sigil_fire', rot=1.2, jitter=0.2)
    style('blood', 'Кровь: алый и розово-красный; луна, пульс, нити.',
          '#D0101E', '#FF5A5A', '#FFD0D0', '#2A0006', sig='sigil_blood', pulse={'amp': 0.25, 'period': 20})
    style('soul', 'Души: бирюза на чёрном; огоньки душ, клетки, спирали.',
          '#46E0D8', '#0B4F57', '#DFFFFB', '#020A0C', sparks='soul_mote', shards='soul_mote', sig='spiral_ring', rot=0.6,
          pulse={'amp': 0.3, 'period': 30})
    style('rift', 'Разлом: густой фиолетовый и чёрный, бледно-лиловое ядро.',
          '#7A2AC8', '#2A0A44', '#E8D0FF', '#06020A', sparks='spark_sharp', sig='higher_cracks', rot=1.4, jitter=0.3)


# ------------------------------------------------------------------ 1. Застывший час
GOLD, ICE, WHITE = '#F2C86B', '#CFE6FF', '#FFFFFF'


def frozen_hour():
    sigil('frozen_hour_dial', 'Застывший час: малый циферблат (облако в небе и печать под кастером). Стрелки бешено бегут при появлении и замирают.',
          1.0, GOLD, 'sky', [
              L('glow', 'disc', 'glow', 0.8, -0.01, ap(0, 10, 'fade'), br=0.35, color=ICE),
              L('gear', 'disc', 'gear', 0.55, 0.0, ap(2, 10, 'grow', 'fade', easing='easeOutBack'), rot=-6, boost=12, color=ICE, br=0.55),
              L('face', 'disc', 'clock_face', 1.0, 0.01, ap(4, 14, 'draw', easing='easeInOutSine', startAngle=90, direction=-1)),
              L('rim', 'band', 'thin_ring', 1.12, 0.012, ap(8, 10, 'draw', startAngle=90), inner=0.96, repeat=1, br=0.7),
              L('hour', 'disc', 'clock_hand_hour', 1.0, 0.02, ap(10, 26, 'fade'), rot=-0.4, boost=2800),
              L('minute', 'disc', 'clock_hand_minute', 1.0, 0.03, ap(10, 26, 'fade'), rot=-0.8, boost=4000),
          ], flash={'color': WHITE, 'size': 1.3, 'duration': 8, 'sparks': 8}, dissolve=('shatter',), ddur=14)

    sigil('frozen_hour_sky', 'Застывший час: главный циферблат над зоной. Шестерёнки, кольцо римских цифр, стрелки замирают на месте.',
          10.0, GOLD, 'sky', [
              L('glow', 'disc', 'glow', 0.9, -0.02, ap(0, 16, 'fade'), br=0.4, color=ICE, pulse=(0.15, 40)),
              L('gear_big', 'disc', 'gear', 0.62, -0.01, ap(4, 14, 'grow', 'fade', easing='easeOutBack'), rot=-3, boost=20, color=ICE, br=0.5),
              L('arcs', 'arcs', 'arc_strip', 1.08, 0.0, ap(0, 16, 'assemble', 'fade'), count=4, arcLength=70, width=0.02, rot=8, color=ICE),
              L('face', 'disc', 'clock_ornate', 1.0, 0.01, ap(8, 18, 'draw', easing='easeInOutSine', startAngle=90, direction=-1)),
              L('numerals', 'band', 'roman_band', 1.3, 0.02, ap(16, 16, 'draw', 'fade', startAngle=90), inner=1.16 / 1.3, repeat=1, rot=-2, br=0.85),
              L('gear_a', 'disc', 'gear', 0.2, 0.03, ap(18, 8, 'grow', easing='easeOutBack'), rot=24, boost=10, br=0.8),
              L('hour', 'disc', 'clock_hand_hour', 1.0, 0.04, ap(18, 30, 'fade'), rot=-0.3, boost=3200),
              L('minute', 'disc', 'clock_hand_minute', 1.0, 0.05, ap(18, 30, 'fade'), rot=-0.6, boost=4800),
              L('star', 'disc', 'star_ring', 0.3, 0.06, ap(30, 10, 'grow', 'fade'), rot=6, br=0.8, color=ICE),
          ], expand={'scale': 1.25, 'delay': 0, 'duration': 16, 'easing': 'easeOutCubic'},
          flash={'color': WHITE, 'size': 1.2, 'duration': 12, 'sparks': 30}, ddur=18)

    sigil('frozen_hour_ground', 'Застывший час: циферблат на земле по границе зоны (радиус = размер), римские цифры и засечки; тонкие кольца внутри.',
          24.0, GOLD, 'ground', [
              L('numerals', 'band', 'roman_band', 1.0, 0.0, ap(0, 14, 'draw', startAngle=90, direction=-1), inner=0.93, repeat=1, br=0.9),
              L('ring', 'band', 'thin_ring', 0.9, 0.01, ap(4, 12, 'draw', startAngle=90), inner=0.985, repeat=1, color=ICE, br=0.6),
              L('spiral', 'disc', 'spiral_ring', 0.32, 0.02, ap(6, 14, 'grow', 'fade', easing='easeOutBack'), rot=-4, color=ICE, br=0.7),
              L('hourglass', 'disc', 'hourglass', 0.12, 0.03, ap(10, 12, 'unfold', 'fade'), br=0.9),
              L('inner', 'band', 'rim', 0.16, 0.04, ap(10, 10, 'draw'), inner=0.8, repeat=1, rot=10),
          ], flash={'color': ICE, 'size': 1.05, 'duration': 10, 'sparks': 0}, ddur=16)

    sigil('frozen_hour_cast', 'Застывший час, каст (2 с): циферблат под ногами раскручивается, шестерёнки, песочные часы в центре.',
          2.6, GOLD, 'ground', [
              L('glow', 'disc', 'glow', 0.9, -0.01, ap(0, 8, 'fade'), br=0.4, color=ICE),
              L('gear', 'disc', 'gear', 0.6, 0.0, ap(0, 10, 'grow', easing='easeOutBack'), rot=-30, color=ICE, br=0.6),
              L('face', 'disc', 'clock_ornate', 1.0, 0.01, ap(2, 14, 'draw', startAngle=90, direction=-1)),
              L('hourglass', 'disc', 'hourglass', 0.22, 0.02, ap(8, 8, 'unfold', 'fade')),
              L('hour', 'disc', 'clock_hand_hour', 1.0, 0.03, ap(6, 10, 'fade'), rot=-120),
              L('minute', 'disc', 'clock_hand_minute', 1.0, 0.04, ap(6, 10, 'fade'), rot=-720),
          ], dissolve=('collapse',), ddur=8)

    fx('frozen_hour_cast', 'Застывший час, каст 40 тиков: циферблат под кастером, вокруг поднимаются бледные пылинки.', 'chrono', 46, [
        E('sigil', 0, 'caster+0,0.05,0', id='frozen_hour_cast', until=44),
        E('sprites', 0, 'caster', duration=40, texture='spark_soft', count=80, rate=2, area=2.2, speed=0.01, gravity=-0.004,
          size=[0.12, 0.03], life=30, color='@secondary'),
    ])

    # облако малых циферблатов: кольцами вокруг зоны, на разной высоте, появляются волной от центра
    rng = random.Random(13)
    clocks = []
    n = 22
    for i in range(n):
        ring_r = 7 + 15 * (i / (n - 1)) ** 0.8
        a = i * 2.399 + rng.uniform(-0.2, 0.2)
        x, z = math.cos(a) * ring_r, math.sin(a) * ring_r
        y = 10 + rng.uniform(0, 11) + (22 - ring_r) * 0.25
        sc = rng.uniform(0.9, 2.2) * (1.15 if ring_r > 15 else 1.0)
        clocks.append(E('sigil', 6 + int(ring_r * 1.6) + rng.randint(0, 4), off(x, y, z), id='frozen_hour_dial',
                        orientation='billboard' if i % 3 == 0 else 'sky', scale=round(sc, 2), until=158))

    fx('frozen_hour', 'Застывший час: мир сереет, над зоной главный циферблат и облако малых часов, золотой столб в центре, '
                      'по границе — циферблат на земле и тонкая завеса; пылинки висят в воздухе. В конце время трогается: вспышка, осколки.',
       'chrono', 166, [
           E('flash', 0, 'caster+0,1.2,0', duration=12, size=6, anamorphic=20, rays=12, screen=0.55, color='#EAF6FF'),
           E('wave', 0, 'caster+0,0.5,0', duration=18, shape='sphere', radius=24, rim=1.3, color='@secondary'),
           E('wave', 0, 'caster', duration=14, shape='ring', radius=24, color='@primary'),
           E('tint', 2, 'caster', duration=156, radius=40, color='#8E95A8', strength=0.5, **{'in': ease(8), 'out': ease(14, 'easeInSine')},
             comment='время стоит: мир серый, золото ярко'),
           E('sigil', 0, 'caster+0,0.06,0', id='frozen_hour_ground', until=158),
           E('column', 6, 'caster', duration=152, radius=0.32, height=18, rings=3, ringSpeed=3, fill=0, color='@primary',
             **{'in': ease(10), 'out': ease(12, 'easeInSine')}),
           E('sigil', 4, 'caster+0,18,0', id='frozen_hour_sky', until=158),
           *clocks,
           E('sprites', 4, 'caster+0,0.5,0', duration=152, texture='spark_soft', count=320, rate=0, area=23, speed=0.0, gravity=0,
             size=[0.1, 0.1], life=154, color='@secondary', comment='застывшие пылинки: висят, не двигаясь'),
           E('curtain', 4, 'caster', duration=152, radius=24, count=96, height=7, grow=14, width=[0.03, 0.07],
             brightness=[0.25, 0.6], texture='beam_fade', color='@secondary', **{'out': ease(10)}),
           E('wave', 150, 'caster', duration=14, shape='ring', radius=24, color='@primary'),
           E('flash', 152, 'caster+0,1.4,0', duration=10, size=8, rays=8, screen=0.35, color='#FFF4D6'),
           E('sprites', 152, 'caster+0,6,0', duration=4, texture='shard', count=90, rate=90, spread=10, speed=0.35, gravity=0.012,
             tumble=1, size=[0.4, 0.12], life=30, color='@secondary', comment='время трогается: стекло застывшей секунды бьётся'),
       ])

    sigil('frozen_hour_cap', 'Призма Застывшего часа: шестиугольное ребро сверху и снизу цели.', 0.95, ICE, 'ground', [
        L('hex', 'disc', 'hex_ring', 1.0, 0.0, ap(0, 8, 'grow', 'fade', easing='easeOutBack'), rot=4),
        L('glow', 'disc', 'glow', 0.7, -0.01, ap(0, 8, 'fade'), br=0.3),
    ], dissolve=('shatter',), ddur=10)
    fx('frozen_hour_prism', 'Стеклянная призма вокруг застывшего существа (масштаб = рост/2.3; точка top — над головой). Бьётся, когда время идёт.',
       'chrono', 166, [
           E('sigil', 0, 'caster+0,0.04,0', id='frozen_hour_cap', until=150),
           E('sigil', 2, 'point:top', id='frozen_hour_cap', until=150),
           E('curtain', 0, 'caster', duration=150, radius=0.9, count=6, height=2.3, grow=6, width=0.035, brightness=1.0,
             texture='beam', color='@secondary', **{'out': ease(4)}),
           E('sprites', 0, 'caster+0,1.1,0', duration=150, texture='spark_sharp', count=12, rate=0.1, spread=0.9, speed=0, size=[0.25, 0.05],
             life=20, color='#FFFFFF'),
           E('sprites', 150, 'caster+0,1.1,0', duration=3, texture='shard', count=26, rate=26, spread=0.7, speed=0.22, gravity=0.02,
             tumble=1, size=[0.3, 0.08], life=24, color='@secondary'),
           E('flash', 150, 'caster+0,1.1,0', duration=8, size=2.2, color='#FFFFFF'),
       ])


# ------------------------------------------------------------------ 2. Табу (Божественная)
DGOLD, DPALE = '#FFD36B', '#FFF4D6'


def taboo():
    sigil('taboo_ground', 'Табу, каст: печать под кастером — алхимический круг, круг Табу прорисовывается, мандала, обод.', 12.0, DGOLD, 'ground', [
        L('mandala', 'disc', 'pat_mandala', 0.96, -0.01, ap(0, 50, 'fade', 'grow'), rot=2, br=0.45),
        L('alchemy', 'disc', 'pat_alchemy', 0.66, 0.0, ap(10, 40, 'draw', startAngle=90), rot=5, br=0.9),
        L('taboo', 'disc', 'circle_taboo', 0.45, 0.01, ap(20, 30, 'draw', startAngle=90, direction=-1), rot=-9, color=DPALE),
        L('runes', 'band', 'rune_band', 1.0, 0.02, ap(40, 30, 'draw', startAngle=90), inner=0.93, repeat=10, rot=-3),
        L('rim', 'band', 'thin_ring', 1.04, 0.03, ap(60, 20, 'draw'), inner=0.985, repeat=1, br=0.8),
    ], flash={'color': '#FFFFFF', 'size': 1.1, 'duration': 12, 'sparks': 40},
          children=[{'id': 'golden_halo', 'anchor': 'caster', 'arc': {'count': 6, 'radius': 1.6, 'angle': 160, 'height': 1.6, 'behind': True, 'stagger': 3}}],
          hit={'duration': 10, 'width': 0.09, 'rings': 3, 'spacing': 0.14, 'tilt': 1, 'sparks': 14, 'color': DPALE})

    tiers = [('pat_stars', 4), ('pat_metatron', 6), ('pat_zodiac', 8), ('circle_taboo', 10)]
    for i, (tex, r) in enumerate(tiers):
        sigil('taboo_tier_%d' % i, 'Табу, каст: ярус столба (%s), раскрывается разворотом и вращается.' % tex, r, DGOLD, 'sky', [
            L('glow', 'disc', 'glow', 0.8, -0.02, ap(0, 16, 'fade'), br=0.3),
            L('pattern', 'disc', tex, 1.0, 0.0, ap(0, 24, 'unfold', 'grow', easing='easeOutBack'), rot=(12 if i % 2 == 0 else -12), boost=4),
            L('ring', 'band', 'thin_ring', 1.1, 0.01, ap(10, 16, 'draw'), inner=0.98, repeat=1, br=0.7),
        ], flash={'color': '#FFFFFF', 'size': 1.2, 'duration': 8, 'sparks': 16})

    sigil('taboo_sky_cast', 'Табу, каст: великая печать в небе рождается над столбом и к концу каста дорастает до границы зоны.',
          51.0, DGOLD, 'sky', [
              L('rays', 'spokes', 'spokes', 0.6, -0.05, ap(0, 40, 'fade'), rot=2, br=0.6),
              L('arcs', 'arcs', 'arc_strip', 1.06, 0.0, ap(0, 50, 'assemble', 'fade'), count=6, arcLength=40, width=0.012, rot=3),
              L('taboo', 'disc', 'circle_taboo', 1.0, 0.02, ap(20, 110, 'draw', easing='easeInOutSine', startAngle=90), rot=1.5, br=0.95),
              L('alchemy', 'disc', 'pat_alchemy', 0.55, 0.04, ap(60, 70, 'draw', startAngle=-90, direction=-1), rot=-2.5, color=DPALE, br=0.8),
              L('rim', 'band', 'thin_ring', 1.05, 0.06, ap(100, 40, 'draw'), inner=0.99, repeat=1),
          ], expand={'scale': 2.5, 'delay': 0, 'duration': 60, 'easing': 'easeInOutSine'},
          flash={'color': '#FFFFFF', 'size': 1.1, 'duration': 16, 'sparks': 80})

    fx('taboo_cast', 'Табу, каст 25 с (ролик камеры): печать под кастером, искры, ярусы-печати поднимаются по растущему столбу, '
                     'великая печать в небе дорастает до размера зоны; пузырь вокруг кастера, в конце — ливень лучей и засветка.',
       'divine', 500, [
           E('sigil', 0, 'caster+0,0.05,0', id='taboo_ground', until=500),
           E('sprites', 20, 'caster', duration=480, texture='spark_soft', count=1440, rate=3, area=3.2, speed=0.015, gravity=-0.004,
             size=[0.16, 0.03], life=60, color='@primary'),
           E('vortex', 60, 'caster', duration=440, radius=3.2, height=6, arms=4, speed=1.0, pull=0, texture='rune_taboo', color='@primary',
             comment='вихрь рун вокруг кастера (рисует движок элементов; если тип не поддержан — пропускается)'),
           E('beam', 150, 'caster', to='caster+0,56,0', duration=350, width=2.6, core=0.28, grow=130, flicker=0.1, color='@primary'),
           *[E('sigil', 150 + 30 * i, off(0, 10 + 12 * i, 0), id='taboo_tier_%d' % i, until=500) for i in range(4)],
           E('sigil', 280, 'caster+0,56,0', id='taboo_sky_cast', until=500),
           E('wave', 380, 'caster+0,1.2,0', duration=110, shape='sphere', radius=4.5, rim=1.0, color='@primary'),
           E('curtain', 400, 'caster', duration=100, radius=[5, 9], count=24, height=56, grow=40, fromTop=True, width=[0.1, 0.3],
             brightness=[0.3, 0.7], texture='beam_fade', color='@secondary'),
           E('beam_rain', 440, 'caster', duration=60, area=22, count=36, interval=2, width=0.35, height=40, impact='golden_halo',
             color='@primary'),
           E('flash', 490, 'caster+0,1.5,0', duration=12, size=9, anamorphic=34, rays=16, screen=0.6, color='#FFFFFF'),
       ])

    sigil('taboo_seal', 'Табу: великая печать над полем (радиус 128). Под ней — кольцо рун и малые круги ниже по оси; медленно дышит.',
          128.0, DGOLD, 'sky', [
              L('taboo', 'disc', 'circle_taboo', 1.0, 0.0, ap(0, 40, 'fade'), rot=0.5, pulse=(0.12, 80)),
              L('rim', 'band', 'thin_ring', 1.04, 0.2, ap(0, 30, 'draw'), inner=0.99, repeat=1, br=0.9),
              L('runes', 'band', 'rune_band', 0.86, 12, ap(20, 60, 'draw', startAngle=90), inner=0.82 / 0.86, repeat=24, rot=-0.6, br=0.8),
              L('metatron', 'disc', 'pat_metatron', 0.36, 2, ap(10, 40, 'fade', 'grow'), rot=-1, br=0.7),
              L('circle_a', 'disc', 'circle_a', 0.5, 4, ap(10, 40, 'fade'), rot=-1.4, color=DPALE, br=0.7),
              L('circle_b', 'disc', 'circle_b', 0.22, 7, ap(20, 40, 'fade'), rot=3, color=DPALE, br=0.8),
              L('zodiac', 'disc', 'pat_zodiac', 0.14, 10, ap(30, 40, 'fade'), rot=-4, br=0.8),
              L('rays', 'spokes', 'rays', 0.24, 6, ap(30, 40, 'fade'), rot=0.8, br=0.5, pulse=(0.2, 60)),
          ], ddur=40, stagger=4)
    sigil('taboo_center', 'Табу: печать у основания столба в центре поля.', 11.0, DGOLD, 'ground', [
        L('mandala', 'disc', 'pat_mandala', 1.0, 0.0, ap(0, 40, 'fade'), rot=1.5, br=0.45),
        L('taboo', 'disc', 'circle_taboo', 0.64, 0.01, ap(0, 30, 'draw', startAngle=90), rot=-4),
        L('rim', 'band', 'thin_ring', 0.78, 0.02, ap(10, 20, 'draw'), inner=0.98, repeat=1, br=0.8),
    ], ddur=30)
    sigil('taboo_gyro', 'Табу: «гироскоп» на столбе — кольца рун и пунктира, вращаются в разные стороны.', 9.0, DGOLD, 'sky', [
        L('runes', 'disc', 'orbit_runes', 1.0, 0.0, ap(0, 30, 'grow', 'fade'), rot=6),
        L('dash', 'disc', 'orbit_dash', 0.78, 0.6, ap(6, 30, 'grow', 'fade'), rot=-9, color=DPALE),
        L('stars', 'disc', 'orbit_stars', 0.55, 1.2, ap(12, 30, 'grow', 'fade'), rot=14),
    ], ddur=30)
    fx('taboo_zone', 'Табу: поле на минуты. Великая печать в 56 блоках над центром, столб света с гироскопом, печать у основания, '
                     'световая завеса по границе (радиус 128).', 'divine', -1, [
        E('flash', 0, 'caster+0,2,0', duration=16, size=14, anamorphic=40, rays=16, screen=0.7, color='#FFF4D6'),
        E('wave', 0, 'caster', duration=40, shape='ring', radius=128, color='@primary'),
        E('sigil', 0, 'caster+0,56,0', id='taboo_seal'),
        E('sigil', 0, 'caster+0,0.06,0', id='taboo_center'),
        E('column', 0, 'caster', radius=1.4, height=56, rings=4, ringSpeed=3, fill=1, color='@primary', **{'in': ease(40)}),
        E('sigil', 10, 'caster+0,26,0', id='taboo_gyro'),
        E('sigil', 20, 'caster+0,3,0', id='taboo_gyro', scale=0.36),
        E('curtain', 20, 'caster+0,-4,0', radius=128, count=96, height=64, grow=60, width=1.6, brightness=[0.12, 0.32], flicker=0.4,
          texture='beam_fade', color='@primary'),
        E('sprites', 0, 'caster+0,30,0', duration=200, texture='feather', count=240, rate=1.2, area=80, speed=0.004, gravity=0.0015,
          sway=1.2, tumble=0.6, size=[0.5, 0.3], life=200, color='@secondary', comment='перья опускаются на поле, пока печать встаёт'),
    ])


# ------------------------------------------------------------------ 3. Низвержение (Запретная)
FGOLD, FRED, FCORE = '#D4A017', '#8A1420', '#FFF0C0'


def downfall():
    sigil('downfall_ground', 'Низвержение: печать под кастером. Цепи прорисовываются, багровые трещины с перелётом, золотой обод; '
                             'формируется к 4.4 с (поза «Активация»), тогда за спиной встают шесть золотых кругов.', 7.0, FGOLD, 'ground', [
        L('glow', 'disc', 'glow', 0.8, -0.01, ap(0, 20, 'fade'), br=0.35),
        L('cracks', 'disc', 'higher_cracks', 0.7, 0.0, ap(6, 24, 'grow', 'fade', easing='easeOutBack'), rot=-4, color=FRED, br=1.2),
        L('circle', 'disc', 'circle_a', 0.62, 0.01, ap(14, 30, 'draw', easing='easeInOutSine', startAngle=90), rot=6),
        L('chains', 'band', 'chain_band', 0.95, 0.02, ap(30, 30, 'draw', startAngle=90, direction=-1), inner=0.84, repeat=10, rot=-3),
        L('rim', 'band', 'rim', 1.0, 0.03, ap(52, 14, 'draw'), inner=0.9, repeat=1, rot=2, color=FCORE),
        L('alchemy', 'disc', 'pat_alchemy', 1.32, -0.02, ap(56, 20, 'fade', 'grow'), rot=-1.5, br=0.45),
    ], expand={'scale': 1.15, 'delay': 2, 'duration': 10, 'easing': 'easeOutCubic'},
          flash={'color': FCORE, 'size': 1.25, 'duration': 12, 'sparks': 40},
          children=[{'id': 'golden_halo', 'anchor': 'caster', 'arc': {'count': 6, 'radius': 1.5, 'angle': 150, 'height': 1.55,
                                                                     'behind': True, 'stagger': 3}}])
    sigil('downfall_runes', 'Низвержение: кольцо рун на уровне груди вокруг кастера.', 4.5, FGOLD, 'ground', [
        L('runes', 'band', 'rune_band', 1.0, 0.0, ap(0, 24, 'draw', startAngle=90), inner=0.88, repeat=8, rot=14, color='#FFD36B'),
        L('ring', 'band', 'thin_ring', 0.86, 0.01, ap(8, 16, 'draw'), inner=0.98, repeat=1, rot=-10, color=FRED, br=1.2),
    ])
    sigil('downfall_sky', 'Низвержение: печать в небе над кастером — разлом и цепи, медленное тяжёлое вращение.', 18.0, FGOLD, 'sky', [
        L('glow', 'disc', 'glow', 0.7, -0.02, ap(0, 30, 'fade'), color=FRED, br=0.5),
        L('cracks', 'disc', 'higher_cracks', 0.5, 0.0, ap(0, 30, 'grow', 'fade'), rot=-2, color=FRED, br=1.3),
        L('circle_a', 'disc', 'circle_a', 1.0, 0.01, ap(10, 50, 'draw', startAngle=90), rot=3),
        L('circle_b', 'disc', 'circle_b', 0.6, 0.02, ap(30, 40, 'draw', startAngle=-90, direction=-1), rot=-6, color=FCORE, br=0.8),
        L('chains', 'band', 'chain_band', 1.12, 0.03, ap(50, 30, 'draw'), inner=0.93, repeat=16, rot=-1.5),
    ], flash={'color': FCORE, 'size': 1.15, 'duration': 14, 'sparks': 30})
    sigil('downfall_rift_ring', 'Низвержение: кольца-орбиты вокруг разлома (вертикальные, смотрят на кастера).', 2.6, FGOLD, 'facing', [
        L('ring', 'disc', 'orbit_dash', 1.0, 0.0, ap(0, 30, 'grow', 'fade'), rot=40),
        L('ring2', 'disc', 'orbit_saw', 0.8, 0.05, ap(10, 30, 'grow', 'fade'), rot=-55, color=FCORE, br=0.8),
        L('runes', 'disc', 'orbit_runes', 1.3, -0.05, ap(20, 40, 'grow', 'fade'), rot=18, color=FRED, br=1.2),
    ], ddur=16)
    sigil('downfall_rift_glow', 'Низвержение: сияние в разломе (всегда к камере).', 1.2, FGOLD, 'billboard', [
        L('glow', 'disc', 'glow', 1.0, 0.0, ap(0, 40, 'fade', 'grow'), pulse=(0.2, 12), br=0.8),
        L('rays', 'spokes', 'rays', 2.2, 0.01, ap(0, 60, 'fade', 'grow'), rot=12, br=0.6),
    ], ddur=10)

    write('fx/meshes/downfall_rift.json', {
        'comment': 'Разлом Низвержения: тёмная рваная прорезь (translucent), огненная глубина и золотая кромка; лицом к кастеру.',
        'style': 'forbidden', 'center': 2.6, 'formedAt': 30,
        'collapse': {'duration': 20, 'easing': 'easeInCubic'},
        'parts': [
            {'type': 'disc', 'texture': 'rift_tear', 'radius': 3.4, 'blend': 'translucent', 'color': '#FFFFFF',
             'appear': {'delay': 0, 'duration': 30, 'easing': 'easeOutCubic'}},
            {'type': 'disc', 'texture': 'rift_core', 'radius': 3.0, 'color': '#FFFFFF', 'brightness': 0.9,
             'appear': {'delay': 10, 'duration': 40, 'easing': 'easeOutCubic'}},
            {'type': 'disc', 'texture': 'rift_edge', 'radius': 3.1, 'color': '@primary', 'brightness': 1.2,
             'appear': {'delay': 4, 'duration': 20, 'easing': 'easeOutCubic'}},
        ]})

    fx('downfall_cast', 'Низвержение, каст 25 с: печать под кастером формируется к 4.4 с, шесть золотых кругов за спиной, пузырь-сфера, '
                        'вспышка навершия; кольцо рун, печать в небе, кольцо столбов; с 13 с — золотая нить от посоха к разлому.',
       'forbidden', 500, [
           E('sigil', 0, 'caster+0,0.05,0', id='downfall_ground', until=500),
           E('wave', 66, 'caster+0,1,0', duration=40, shape='sphere', radius=3.2, rim=1.3, color='@primary', comment='сфера-пузырь'),
           E('flash', 86, 'caster.hand+0,1.1,0.2', duration=12, size=2.6, anamorphic=7, rays=8, screen=0.3, color='#FFF0C0',
             comment='вспышка навершия к позе «Активация» (4.4 с)'),
           E('sigil', 40, 'caster+0,1.4,0', id='downfall_runes', until=500),
           E('sigil', 100, 'caster+0,28,0', id='downfall_sky', until=500),
           E('curtain', 120, 'caster', duration=380, radius=6.5, count=12, height=30, grow=40, width=[0.25, 0.4], brightness=[0.45, 0.8],
             texture='beam_fade', color='@primary'),
           E('sprites', 0, 'caster', duration=500, texture='spark_sharp', count=1000, rate=2, area=4.5, speed=0.02, gravity=-0.003,
             size=[0.14, 0.03], life=50, color='@primary'),
           E('tint', 200, 'caster', duration=300, radius=64, color='#3A0A10', strength=0.35, **{'in': ease(80), 'out': ease(10)}),
           E('beam', 260, 'caster.hand+0,1.1,0.2', to='point:riftc', follow=True, duration=240, width=0.14, core=0.4, grow=20,
             flicker=0.3, color='@primary'),
           E('beam', 300, 'caster.hand+0,1.1,0.2', to='point:riftc', follow=True, duration=200, width=0.5, core=0.1, grow=20,
             flicker=0.5, color='#5A0E14'),
       ])
    fx('downfall_rift_cast', 'Низвержение, каст: разлом рождается в точке взгляда (с 10 с), кольца вокруг, затягивание искр, вспышка к открытию.',
       'forbidden', 500, [
           E('sigil', 200, 'caster+0,0.05,0', id='downfall_ground', scale=1.0, until=500),
           E('mesh', 220, 'caster', model='downfall_rift', until=500),
           E('sigil', 200, 'caster+0,2.6,0', id='downfall_rift_glow', until=500),
           E('sigil', 240, 'caster+0,2.6,0', id='downfall_rift_ring', until=500),
           E('vortex', 380, 'caster+0,2.6,0', duration=120, radius=12, height=6, arms=5, speed=1.5, pull=1, texture='spark_sharp',
             color='@primary', comment='искры затягивает в разлом (движок элементов)'),
           E('lightning', 440, 'caster+0,30,0', to='caster+0,2.6,0', duration=60, branches=3, jaggedness=0.5, regen=3, width=0.15,
             color='#FFF0C0', comment='молния в разлом (движок элементов)'),
           E('flash', 460, 'caster+0,2.6,0', duration=40, size=12, rays=12, color='#FFE6A0'),
       ])
    fx('downfall_rift', 'Низвержение: открытый разлом (минута). Прорезь, кольца, печать на земле, угли в разлом, вспышка при открытии и закрытии.',
       'forbidden', 1200, [
           E('flash', 0, 'caster+0,2.6,0', duration=14, size=10, anamorphic=24, rays=12, screen=0.5, color='#FFE6A0'),
           E('wave', 0, 'caster', duration=20, shape='ring', radius=8, color='@primary'),
           E('mesh', 0, 'caster', model='downfall_rift', until=1190),
           E('sigil', 0, 'caster+0,0.05,0', id='downfall_ground', until=1190),
           E('sigil', 0, 'caster+0,2.6,0', id='downfall_rift_ring', until=1190),
           E('sigil', 0, 'caster+0,2.6,0', id='downfall_rift_glow', until=1190),
           E('sprites', 0, 'caster+0,0.4,0', duration=1180, texture='spark_sharp', count=2360, rate=2, area=3, speed=0.03, gravity=-0.003,
             size=[0.16, 0.03], life=40, color='@primary'),
           E('wave', 1180, 'caster', duration=20, shape='ring', radius=5, color='@primary'),
           E('flash', 1186, 'caster+0,2.6,0', duration=12, size=6, color='#FFE6A0'),
       ])


# ------------------------------------------------------------------ 4. Млечный путь (звёзды)
VIOLET, SILVER = '#A07CFF', '#D8DCFF'


def milky_way():
    sigil('milky_ground', 'Млечный путь, каст: звёздная печать под кастером — созвездия с доворотом, орбиты смыкаются, кольцо рун.',
          5.0, VIOLET, 'ground', [
              L('glow', 'disc', 'glow', 0.8, -0.01, ap(0, 20, 'fade'), br=0.4),
              L('const', 'disc', 'constellation', 0.8, 0.0, ap(0, 30, 'grow', 'twist', 'fade'), rot=6, color=SILVER, twist=-160),
              L('orbits', 'arcs', 'arc_strip', 1.0, 0.01, ap(10, 30, 'assemble', 'fade'), count=3, arcLength=80, width=0.03, rot=-12),
              L('stars', 'disc', 'orbit_stars', 0.96, 0.02, ap(30, 20, 'fade'), rot=10, color=SILVER),
              L('runes', 'band', 'rune_band', 1.18, 0.03, ap(40, 30, 'draw', startAngle=90), inner=0.9, repeat=8, rot=-4),
          ], flash={'color': '#FFFFFF', 'size': 1.2, 'duration': 12, 'sparks': 30})
    sigil('milky_halo', 'Млечный путь, каст: звёздный круг за спиной кастера.', 1.4, VIOLET, 'facing', [
        L('glow', 'disc', 'glow', 1.0, -0.01, ap(0, 12, 'fade'), br=0.45),
        L('const', 'disc', 'constellation', 0.9, 0.0, ap(0, 16, 'unfold', 'fade'), rot=10, color=SILVER),
        L('ring', 'disc', 'orbit_stars', 1.1, 0.01, ap(6, 16, 'grow', 'fade'), rot=-20),
    ])
    sigil('milky_sky', 'Млечный путь, каст: туманность-галактика над полем, рукава медленно вращаются.', 16.0, VIOLET, 'sky', [
        L('glow', 'disc', 'glow', 0.9, -0.02, ap(0, 40, 'fade'), br=0.35, pulse=(0.15, 60)),
        L('arms', 'disc', 'galaxy_arms', 1.0, 0.0, ap(0, 60, 'grow', 'twist', 'fade', easing='easeOutCubic'), rot=6, twist=-240),
        L('stars', 'disc', 'galaxy_stars', 0.95, 0.01, ap(10, 50, 'fade'), rot=8, color=SILVER),
        L('orbit', 'disc', 'orbit_runes', 1.25, 0.02, ap(40, 40, 'grow', 'fade'), rot=-3),
        L('orbit2', 'disc', 'orbit_dash', 1.45, 0.03, ap(60, 30, 'grow', 'fade'), rot=2, color=SILVER, br=0.7),
    ], flash={'color': '#FFFFFF', 'size': 1.1, 'duration': 14, 'sparks': 40})
    fx('milky_way_cast', 'Млечный путь, каст 10 с (ролик камеры): звёздная печать под ногами, круг за спиной, звёзды вьются; '
                         'над полем раскрывается галактика, мир темнеет в фиолетовую ночь, туманности; к концу — вспышка в руке.',
       'astral', 200, [
           E('sigil', 0, 'caster+0,0.05,0', id='milky_ground', until=200),
           E('sigil', 10, 'caster+0,1.5,-0.5', follow=True, id='milky_halo', until=200),
           E('sprites', 0, 'caster+0,1,0', duration=200, texture='spark_sharp', count=600, rate=3, spread=3.5, speed=0.01,
             size=[0.22, 0.02], spin=180, life=40, color='@secondary'),
           E('sigil', 60, 'caster+0,20,10', id='milky_sky', until=200),
           E('tint', 100, 'caster', duration=100, radius=48, color='#2A1A5A', strength=0.4, **{'in': ease(40), 'out': ease(8)}),
           E('sprites', 90, 'caster+0,16,10', duration=110, texture='glow', count=40, rate=1, area=28, speed=0.004,
             size=[5, 8], life=110, color='#5A3AB0', brightness=0.35, comment='туманность: крупные мягкие пятна'),
           E('sprites', 100, 'caster+0,16,10', duration=100, texture='spark_sharp', count=200, rate=2, area=30, speed=0,
             size=[0.5, 0.2], spin=90, life=100, color='#FFFFFF'),
           E('flash', 186, 'caster.hand', duration=14, size=3, anamorphic=10, rays=10, screen=0.3, color='#E8DCFF'),
       ])
    sigil('milky_galaxy', 'Млечный путь: катящаяся галактика (вертикальная, к направлению полёта), рукава вращаются.', 6.0, VIOLET, 'facing', [
        L('glow', 'disc', 'glow', 0.9, -0.02, ap(0, 10, 'fade'), br=0.5, pulse=(0.15, 16)),
        L('arms', 'disc', 'galaxy_arms', 1.0, 0.0, ap(0, 16, 'grow', 'twist', easing='easeOutBack'), rot=-140, twist=-200),
        L('stars', 'disc', 'galaxy_stars', 1.05, 0.01, ap(4, 16, 'grow', 'fade'), rot=-90, color=SILVER),
        L('ring', 'disc', 'orbit_stars', 1.2, 0.02, ap(8, 16, 'grow', 'fade'), rot=40),
        L('core', 'disc', 'spark_soft', 0.3, 0.03, ap(0, 8, 'grow'), br=1.2, color='#FFFFFF'),
    ], ddur=24, dissolve=('shatter',))
    sigil('milky_galaxy_flat', 'Млечный путь: плоская галактика поперёк катящейся — вместе дают объём.', 6.0, VIOLET, 'ground', [
        L('arms', 'disc', 'galaxy_arms', 0.9, 0.0, ap(4, 16, 'grow', 'fade'), rot=110, br=0.6),
        L('orbit', 'disc', 'orbit_runes', 1.15, 0.01, ap(8, 16, 'grow', 'fade'), rot=-30, color=SILVER, br=0.7),
    ], ddur=24, dissolve=('shatter',))
    fx('milky_way_trail', 'Млечный путь: звёзды и пыль вокруг летящей галактики (следует за ней).', 'astral', 160, [
        E('sprites', 0, 'caster', follow=True, duration=160, texture='spark_sharp', count=640, rate=4, spread=6, speed=0.02,
          size=[0.3, 0.04], spin=200, life=24, color='@secondary'),
        E('sprites', 0, 'caster', follow=True, duration=160, texture='glow', count=80, rate=0.5, spread=5, speed=0.01,
          size=[2.5, 4], life=40, color='#5A3AB0', brightness=0.4),
    ])
    fx('milky_way_end', 'Млечный путь: галактика рассыпается в конце пути.', 'astral', 40, [
        E('flash', 0, 'caster', duration=12, size=9, rays=12, anamorphic=16, screen=0.3, color='#E8DCFF'),
        E('wave', 0, 'caster', duration=20, shape='sphere', radius=7, rim=1.4, color='@primary'),
        E('sprites', 0, 'caster', duration=3, texture='spark_sharp', count=160, rate=160, spread=2, speed=0.3, gravity=0.004,
          size=[0.4, 0.05], spin=200, life=30, color='@secondary'),
    ])


# ------------------------------------------------------------------ 5. Пожирание душ
TEAL, TEAL_D = '#46E0D8', '#0B4F57'


def soul_devour():
    sigil('soul_ground', 'Пожирание душ: печать под жертвой — спираль затягивает, цепи держат, тёмно-бирюзовый обод.', 4.0, TEAL, 'ground', [
        L('glow', 'disc', 'glow', 0.9, -0.01, ap(0, 30, 'fade'), br=0.35, pulse=(0.3, 20)),
        L('spiral', 'disc', 'spiral_ring', 0.75, 0.0, ap(0, 30, 'grow', 'twist'), rot=-30, twist=-300),
        L('ender', 'disc', 'sigil_ender', 0.55, 0.01, ap(20, 30, 'draw', startAngle=90), rot=8, color='#DFFFFB', br=0.8),
        L('chains', 'band', 'chain_band', 1.0, 0.02, ap(30, 30, 'draw', startAngle=90, direction=-1), inner=0.86, repeat=8, rot=4),
        L('rim', 'band', 'rim', 1.12, 0.03, ap(50, 20, 'draw'), inner=0.9, repeat=1, color=TEAL_D, br=1.5),
    ], flash={'color': '#DFFFFB', 'size': 1.2, 'duration': 12, 'sparks': 20})
    sigil('soul_hand', 'Пожирание душ: круг у ладони кастера — сюда тянется душа.', 0.9, TEAL, 'facing', [
        L('glow', 'disc', 'glow', 1.0, -0.01, ap(0, 10, 'fade'), br=0.5, pulse=(0.3, 16)),
        L('spiral', 'disc', 'spiral_ring', 0.9, 0.0, ap(0, 14, 'unfold', 'fade'), rot=90),
        L('rim', 'disc', 'thin_ring', 1.1, 0.01, ap(4, 10, 'grow'), br=0.8),
    ])
    sigil('soul_sky', 'Пожирание душ: печать над жертвой, лицом вниз — воронка, в которую уходит свет.', 9.0, TEAL, 'sky', [
        L('glow', 'disc', 'glow', 0.7, -0.02, ap(0, 40, 'fade'), color=TEAL_D, br=0.8),
        L('spiral', 'disc', 'spiral_ring', 1.0, 0.0, ap(0, 50, 'grow', 'twist'), rot=-20, twist=-200),
        L('eldritch', 'disc', 'sigil_eldritch', 0.6, 0.01, ap(30, 40, 'draw', startAngle=90), rot=10, color='#DFFFFB', br=0.8),
        L('saw', 'disc', 'orbit_saw', 1.2, 0.02, ap(50, 30, 'grow', 'fade'), rot=-6, color=TEAL_D, br=1.5),
    ], flash={'color': '#DFFFFB', 'size': 1.1, 'duration': 12, 'sparks': 24})
    fx('soul_devour', 'Пожирание душ, каст 25 с (ролик камеры): мир темнеет, печать и клетка из лучей вокруг жертвы, '
                      'огоньки души поднимаются и по бирюзовой нити тянутся к руке кастера; над жертвой — воронка; к концу — сжатие и вспышка.',
       'soul', 500, [
           E('tint', 0, 'target', duration=500, radius=40, color='#06161C', strength=0.5, **{'in': ease(60), 'out': ease(10)}),
           E('sigil', 0, 'target+0,0.05,0', id='soul_ground', until=500),
           E('curtain', 20, 'target', duration=480, radius=1.5, count=10, height=3.4, grow=40, width=0.07, brightness=[0.7, 1.0],
             texture='beam', color='@primary', comment='клетка'),
           E('sigil', 40, 'caster.hand', follow=True, id='soul_hand', until=500),
           E('sprites', 40, 'target+0,1,0', duration=460, texture='soul_mote', count=920, rate=2, spread=0.6, speed=0.02,
             gravity=-0.003, size=[0.3, 0.06], life=50, color='@primary'),
           # луч и цепи от цели к заклинателю убраны (владелец 19.11: никакого «луча» к цели в заклинаниях с анимацией)
           E('sigil', 250, 'target+0,14,0', id='soul_sky', until=500),
           E('curtain', 300, 'target', duration=200, radius=[2.5, 4], count=24, height=14, grow=40, fromTop=True, width=[0.05, 0.15],
             brightness=[0.2, 0.5], texture='beam_fade', color='@primary'),
           E('wave', 420, 'target+0,1,0', duration=80, shape='sphere', radius=3, rim=1.5, color='@primary'),
       ])
    fx('soul_devour_end', 'Пожирание душ: душа вырвана — вспышка, огоньки разлетаются вверх, тёмный след печати гаснет.', 'soul', 90, [
        E('flash', 0, 'caster+0,1,0', duration=14, size=6, rays=10, anamorphic=12, screen=0.4, color='#BFFFF8'),
        E('wave', 0, 'caster', duration=20, shape='ring', radius=5, color='@primary'),
        E('sprites', 0, 'caster+0,1,0', duration=3, texture='soul_mote', count=80, rate=80, spread=0.4, speed=0.18, gravity=-0.012,
          size=[0.45, 0.08], life=40, color='@primary'),
        E('decal', 0, 'caster', duration=80, texture='sigil_ender', radius=2.5, fadeOut=40, color='@primary'),
    ])


# ------------------------------------------------------------------ 6. Закрытие пространства (Ковен)
CV, CV_P = '#8A6CFF', '#E4DAFF'
DOME_R = 86


def space_closure():
    sigil('closure_ground', 'Закрытие пространства, каст: печать Ковена под кастером, мандала, обод; потом подрастает.', 9.0, CV, 'ground', [
        L('mandala', 'disc', 'pat_mandala', 1.44, -0.01, ap(0, 50, 'fade', 'grow'), rot=-1.5, br=0.45),
        L('coven', 'disc', 'circle_coven', 1.0, 0.0, ap(0, 40, 'draw', startAngle=90), rot=3),
        L('circle_b', 'disc', 'circle_b', 0.36, 0.01, ap(20, 20, 'grow', 'twist', easing='easeOutBack'), rot=-16, color=CV_P),
        L('geo', 'disc', 'coven_geo', 0.6, 0.02, ap(30, 30, 'draw', startAngle=-90, direction=-1), rot=6, color=CV_P, br=0.7),
        L('rim', 'band', 'thin_ring', 1.5, 0.03, ap(40, 20, 'draw'), inner=0.985, repeat=1, br=0.8),
    ], expand={'scale': 1.2, 'delay': 20, 'duration': 40, 'easing': 'easeInOutSine'},
          flash={'color': '#FFFFFF', 'size': 1.2, 'duration': 12, 'sparks': 30})
    sigil('closure_node', 'Закрытие пространства: малый круг у основания столба гептаграммы.', 1.4, CV_P, 'ground', [
        L('circle', 'disc', 'circle_a', 1.0, 0.0, ap(0, 20, 'grow', 'twist', easing='easeOutBack'), rot=50),
        L('glow', 'disc', 'glow', 0.9, -0.01, ap(0, 20, 'fade'), br=0.4, color=CV),
    ])
    sigil('closure_sky', 'Закрытие пространства, каст: великая печать Ковена в 40 блоках над кастером.', 30.0, CV, 'sky', [
        L('rays', 'spokes', 'rays', 0.7, -0.05, ap(0, 40, 'fade'), rot=2, br=0.5),
        L('coven', 'disc', 'circle_coven', 1.0, 0.0, ap(0, 90, 'draw', easing='easeInOutSine', startAngle=90), rot=2),
        L('zodiac', 'disc', 'pat_zodiac', 0.4, 0.02, ap(40, 50, 'grow', 'twist'), rot=-5, color=CV_P, br=0.8),
        L('rim', 'band', 'thin_ring', 1.05, 0.04, ap(70, 30, 'draw'), inner=0.99, repeat=1),
    ], flash={'color': '#FFFFFF', 'size': 1.1, 'duration': 14, 'sparks': 40})

    pillars, nodes, threads = [], [], []
    for i in range(7):
        a = -math.pi / 2 + i * 2 * math.pi / 7
        x, z = math.cos(a) * 8.2, math.sin(a) * 8.2
        sx, sz = math.cos(a) * 30 * 0.82, math.sin(a) * 30 * 0.82
        nodes.append(E('sigil', 100 + i * 4, off(x, 0.06, z), id='closure_node', until=400))
        pillars.append(E('beam', 100 + i * 4, off(x, 0, z), to=off(x, 22, z), duration=300 - i * 4, width=0.5, core=0.3, grow=60,
                         color='@primary'))
        threads.append(E('beam', 170 + i * 4, off(x, 22, z), to=off(sx, 40, sz), duration=230 - i * 4, width=0.22, core=0.35, grow=60,
                         flicker=0.2, color='@secondary'))
    fx('space_closure_cast', 'Закрытие пространства, каст 20 с (ролик камеры): печать Ковена, семь столбов гептаграммы, нити от столбов '
                             'к великой печати в небе; в последней трети вокруг кастера рождается купол.', 'coven', 400, [
        E('sigil', 0, 'caster+0,0.05,0', id='closure_ground', until=400),
        E('sprites', 40, 'caster', duration=360, texture='spark_soft', count=1080, rate=3, area=3, speed=0.02, gravity=-0.004,
          size=[0.18, 0.03], life=60, color='@primary'),
        *nodes, *pillars,
        E('sigil', 160, 'caster+0,40,0', id='closure_sky', until=400),
        *threads,
        E('wave', 260, 'caster+0,0.5,0', duration=140, shape='sphere', radius=26, rim=1.2, color='@primary', comment='купол рождается'),
        E('flash', 340, 'caster+0,1.3,0', duration=60, size=6, color='#D8C8FF'),
        E('flash', 392, 'caster+0,1.3,0', duration=10, size=10, rays=14, anamorphic=30, screen=0.55, color='#FFFFFF'),
    ])

    write('fx/meshes/closure_meridian.json', {
        'comment': 'Закрытие пространства: меридиан купола — вертикальное кольцо радиуса 86 (решётку дают шесть таких с разным yaw).',
        'style': 'coven', 'center': 0, 'formedAt': 40, 'collapse': {'duration': 30, 'easing': 'easeInCubic'},
        'parts': [{'type': 'ring', 'radius': DOME_R, 'thickness': 0.12, 'color': '@primary', 'brightness': 0.55,
                   'appear': {'delay': 0, 'duration': 40, 'easing': 'easeOutCubic'}}]})
    sigil('closure_lat', 'Закрытие пространства: широта купола (радиус задаёт scale элемента): тонкое кольцо и пунктир.', 1.0, CV, 'ground', [
        L('ring', 'band', 'thin_ring', 1.0, 0.0, ap(0, 30, 'draw'), inner=0.996, repeat=1, br=0.9),
        L('dash', 'band', 'orbit_dash', 0.995, 0.0, ap(10, 30, 'fade'), inner=0.985, repeat=24, rot=-0.6, color=CV_P, br=0.6),
    ], ddur=30)
    sigil('closure_belt', 'Закрытие пространства: пояс рун на экваторе купола.', 1.0, CV, 'ground', [
        L('runes', 'band', 'rune_band', 1.0, 0.0, ap(0, 40, 'draw', startAngle=90), inner=0.985, repeat=48, rot=0.5),
        L('ring', 'band', 'thin_ring', 1.003, 0.0, ap(0, 30, 'draw'), inner=0.998, repeat=1, color=CV_P),
    ], ddur=30)
    sigil('closure_emblem', 'Закрытие пространства: печать Ковена, вписанная в оболочку купола (к зрителю).', 11.0, CV, 'billboard', [
        L('glow', 'disc', 'glow', 0.8, -0.01, ap(0, 30, 'fade'), br=0.3),
        L('coven', 'disc', 'circle_coven', 1.0, 0.0, ap(0, 30, 'grow', 'fade'), rot=3, br=0.9),
    ], ddur=30)
    sigil('closure_zenith', 'Закрытие пространства: печать в зените купола, лицом вниз.', 30.0, CV, 'sky', [
        L('coven', 'disc', 'circle_coven', 1.0, 0.0, ap(0, 40, 'fade', 'grow'), rot=2, pulse=(0.15, 60)),
        L('stars', 'disc', 'pat_stars', 0.6, 0.3, ap(10, 40, 'fade'), rot=-4, color=CV_P, br=0.6),
        L('rays', 'spokes', 'rays', 0.5, 2, ap(20, 40, 'fade'), rot=1, br=0.5),
    ], ddur=30)
    sigil('closure_center', 'Закрытие пространства: печать в центре купола на земле.', 14.0, CV, 'ground', [
        L('mandala', 'disc', 'pat_mandala', 1.43, -0.01, ap(0, 40, 'fade'), rot=1, br=0.4),
        L('coven', 'disc', 'circle_coven', 1.0, 0.0, ap(0, 40, 'draw'), rot=-2.5),
    ], ddur=30)

    lats = []
    for k, lat in enumerate((20, 40, 60, 76)):
        r, y = DOME_R * math.cos(math.radians(lat)), DOME_R * math.sin(math.radians(lat))
        lats.append(E('sigil', 20 + k * 6, off(0, y, 0), id='closure_lat', scale=round(r, 2)))
    meridians = [E('mesh', 0, 'caster', model='closure_meridian', yaw=30 * i) for i in range(6)]
    emblems = []
    for i in range(7):
        a = i * 2 * math.pi / 7
        lat = math.radians(18)
        x, y, z = math.cos(a) * math.cos(lat) * DOME_R, math.sin(lat) * DOME_R, math.sin(a) * math.cos(lat) * DOME_R
        emblems.append(E('sigil', 30 + i * 3, off(x, y, z), id='closure_emblem'))
    fx('space_closure_dome', 'Закрытие пространства: купол радиуса 86 на минуты. Вспышка-пузырь, решётка из шести меридианов и широт, '
                             'пояс рун на экваторе, семь печатей в оболочке, печать в зените и в центре.', 'coven', -1, [
        E('wave', 0, 'caster', duration=40, shape='sphere', radius=DOME_R, rim=1.6, color='@primary'),
        E('flash', 0, 'caster+0,2,0', duration=16, size=14, rays=14, anamorphic=40, screen=0.6, color='#E4DAFF'),
        *meridians,
        E('sigil', 10, 'caster+0,0.3,0', id='closure_belt', scale=DOME_R),
        *lats,
        *emblems,
        E('sigil', 20, off(0, DOME_R - 0.4, 0), id='closure_zenith'),
        E('sigil', 0, 'caster+0,0.07,0', id='closure_center'),
        E('sigil', 30, 'caster+0,4,0', id='taboo_gyro', scale=0.34, color='@primary'),
    ])
    sigil('closure_ripple', 'Закрытие пространства: рябь на оболочке, где в неё ударились (ставится вертикально, наружу).', 3.5, CV, 'facing', [
        L('cell', 'disc', 'dome_cell', 1.0, 0.0, ap(0, 6, 'grow', 'fade'), br=1.2),
        L('ring', 'disc', 'ring', 0.7, 0.01, ap(0, 6, 'grow'), color='#FFFFFF', br=0.8),
        L('coven', 'disc', 'circle_coven', 0.6, 0.02, ap(0, 8, 'grow', 'twist'), rot=60),
    ], hold=6, expand={'scale': 1.6, 'delay': 0, 'duration': 14, 'easing': 'easeOutCubic'}, dissolve=('fade',), ddur=10)
    fx('space_closure_break', 'Закрытие пространства: купол рассыпается — вспышка, осколки сыплются с оболочки.', 'coven', 80, [
        E('flash', 0, 'caster+0,20,0', duration=16, size=20, rays=14, screen=0.5, color='#E4DAFF'),
        E('sprites', 0, 'caster+0,50,0', duration=10, texture='shard', count=360, rate=36, area=70, speed=0.02, gravity=0.02, tumble=1,
          size=[1.2, 0.4], life=70, color='@primary'),
    ])


# ------------------------------------------------------------------ 7. Падение небес и 8. Взрыв (пламя)
FIRE, FIRE_Y, FIRE_C = '#FF6A1E', '#FFC23A', '#FFF2C0'


def fire():
    sigil('heaven_fall_sky', 'Падение небес: кольцо неба (радиус задаёт scale элемента): огненная печать, языки пламени, трещины.',
          1.0, FIRE, 'sky', [
              L('glow', 'disc', 'glow', 0.8, -0.02, ap(0, 20, 'fade'), color='#B0301A', br=0.6, pulse=(0.2, 30)),
              L('cracks', 'disc', 'higher_cracks', 0.7, 0.0, ap(0, 20, 'grow', 'fade'), rot=-2, color='#B0301A', br=1.3),
              L('fire', 'disc', 'sigil_fire', 0.62, 0.01, ap(6, 30, 'draw', startAngle=90), rot=4, color=FIRE_Y),
              L('flames', 'band', 'flame_band', 1.0, 0.02, ap(20, 24, 'draw', startAngle=90, direction=-1), inner=0.88, repeat=8, rot=-3),
              L('rim', 'band', 'rim', 0.86, 0.03, ap(30, 16, 'draw'), inner=0.9, repeat=1, color=FIRE_C),
          ], flash={'color': FIRE_C, 'size': 1.15, 'duration': 12, 'sparks': 30})
    fx('heaven_fall', 'Падение небес: каст 10 с — небо закрывается четырьмя кольцами огня, мир краснеет, сыплются угли; '
                      'потом 20 с метеоритного дождя (сами метеориты — meteor).', 'pyre', 640, [
        *[E('sigil', 50 * i, off(0, 42 + 5 * i, 0), id='heaven_fall_sky', scale=52 - 6 * i, until=620) for i in range(4)],   # ×2 (владелец 19.11)
        E('tint', 20, 'caster', duration=600, radius=96, color='#5A1A0A', strength=0.35, **{'in': ease(80), 'out': ease(30)}),
        E('sprites', 0, 'caster+0,18,0', duration=600, texture='spark_sharp', count=5400, rate=9, area=42, speed=0.005, gravity=0.002,
          size=[0.18, 0.05], life=90, color='@secondary', comment='угли сыплются с неба'),
        E('curtain', 150, 'caster', duration=470, radius=42, count=96, height=44, grow=40, fromTop=True, width=[0.08, 0.2],
          brightness=[0.1, 0.3], flicker=0.4, texture='beam_fade', color='@primary'),
    ])
    sigil('meteor_mark', 'Метеорит: метка удара на земле — сужающийся огненный круг.', 3.0, FIRE, 'ground', [
        L('fire', 'disc', 'sigil_fire', 1.0, 0.0, ap(0, 10, 'draw', startAngle=90), rot=60, br=0.9),
        L('flames', 'band', 'flame_band', 1.15, 0.01, ap(0, 8, 'draw'), inner=0.85, repeat=6, rot=-90, color=FIRE_Y),
    ], expand={'scale': 0.75, 'delay': 0, 'duration': 20, 'easing': 'easeInSine'}, dissolve=('shatter',), ddur=10)
    fx('meteor', 'Метеорит Падения небес: метка на земле (1 с), огненный след с неба, удар — вспышка, волна, трещины, угли.', 'pyre', 90, [
        E('sigil', 0, 'caster+0,0.05,0', id='meteor_mark', until=30),
        E('beam', 20, 'caster+0,28,0', to='caster', duration=12, width=1.4, core=0.35, grow=10, color='@primary'),
        E('flash', 30, 'caster+0,0.8,0', duration=10, size=5, rays=6, color=FIRE_C),
        E('wave', 30, 'caster', duration=14, shape='ring', radius=4.2, color='@primary'),
        E('decal', 30, 'caster', duration=60, texture='higher_cracks', radius=3, fadeOut=40, color='@primary'),
        E('sprites', 30, 'caster+0,0.3,0', duration=3, texture='spark_sharp', count=40, rate=40, spread=0.6, speed=0.25, gravity=0.02,
          size=[0.3, 0.05], life=24, color='@secondary'),
    ])

    rings = []
    for i in range(7):
        rings.append(E('sigil', 37 * (i + 1), off(0, 36 + i * 5.0, 0), id='explosion_ring', scale=round(24 - i * 2.2, 2), until=310))
    sigil('explosion_ring', 'Взрыв: один из семи кругов над целью (радиус задаёт scale): пламя, руны, обод; быстро разгоняется.',
          1.0, FIRE, 'sky', [
              L('glow', 'disc', 'glow', 0.7, -0.02, ap(0, 14, 'fade'), br=0.4, pulse=(0.2, 14)),
              L('fire', 'disc', 'sigil_fire', 0.7, 0.0, ap(0, 18, 'unfold', 'grow', easing='easeOutBack'), rot=20, boost=6),
              L('runes', 'band', 'rune_band', 1.0, 0.01, ap(4, 16, 'draw', startAngle=90), inner=0.88, repeat=8, rot=-14, color=FIRE_Y),
              L('flames', 'band', 'flame_band', 1.18, 0.02, ap(10, 14, 'draw'), inner=0.86, repeat=10, rot=10, color='#FF3A10'),
          ], flash={'color': FIRE_C, 'size': 1.2, 'duration': 10, 'sparks': 24}, dissolve=('shatter',), ddur=10)
    sigil('explosion_ground', 'Взрыв: круг на земле в точке удара, прорисовывается весь каст (радиус 24 — ×2, владелец 19.11).', 24.0, FIRE, 'ground', [
        L('cracks', 'disc', 'higher_cracks', 0.9, 0.0, ap(40, 200, 'grow', 'fade', easing='easeInSine'), color='#B0301A', br=1.2),
        L('fire', 'disc', 'sigil_fire', 0.7, 0.01, ap(0, 240, 'draw', easing='linear', startAngle=90), rot=3, br=0.9),
        L('flames', 'band', 'flame_band', 1.0, 0.02, ap(120, 120, 'draw', easing='linear'), inner=0.9, repeat=14, rot=-4, color=FIRE_Y),
    ], dissolve=('shatter',), ddur=8)
    fx('explosion_cast', 'Взрыв, каст 15 с: каждые ~2 с над целью зажигается ещё один круг (семь), круг на земле прорисовывается, '
                         'пламя поднимается, мир наливается оранжевым; в конце — столб от земли к кругам.', 'pyre', 310, [
        E('sigil', 0, 'caster+0,0.05,0', id='explosion_ground', until=305),
        *rings,
        E('sprites', 20, 'caster', duration=290, texture='spark_sharp', count=4500, rate=15, area=22, speed=0.02, gravity=-0.006,
          size=[0.22, 0.04], life=40, color='@primary'),
        E('tint', 150, 'caster', duration=160, radius=96, color='#FF5A1E', strength=0.3, **{'in': ease(140, 'easeInSine')}),
        E('beam', 260, 'caster', to='caster+0,68,0', duration=45, width=2.0, core=0.3, grow=30, flicker=0.4, color='@secondary'),
    ])
    fx('explosion_boom', 'Взрыв: удар — засветка, огненный столб, пузырь и кольцо по земле, трещины и угли.', 'pyre', 200, [
        E('flash', 0, 'caster+0,3,0', duration=20, size=44, anamorphic=90, rays=16, screen=1.0, color='#FFE2B0'),
        E('column', 0, 'caster', duration=50, radius=12, height=64, rings=4, ringSpeed=12, fill=3, color='@secondary',
          **{'out': ease(30, 'easeInSine')}),
        E('wave', 0, 'caster+0,0.5,0', duration=24, shape='sphere', radius=38, rim=2.4, color='@primary'),
        E('wave', 2, 'caster', duration=30, shape='ring', radius=48, color='@secondary'),
        E('decal', 0, 'caster', duration=200, texture='higher_cracks', radius=28, fadeOut=120, color='@primary'),
        E('sprites', 0, 'caster+0,1,0', duration=4, texture='spark_sharp', count=700, rate=175, spread=6, speed=0.8, gravity=0.02,
          size=[0.5, 0.06], life=40, color='@secondary'),
        E('sprites', 6, 'caster+0,2,0', duration=60, texture='glow', count=90, rate=1.5, spread=8, speed=0.1, gravity=-0.006,
          size=[5, 12], life=50, color='#FF6A1E', brightness=0.5, comment='огненный гриб'),
    ])


# ------------------------------------------------------------------ 9–12. Восемь щитов, Ковчег, Кровавая луна, Разлом мира
def others():
    sigil('eight_shields', 'Восемь щитов: октаграмма под кастером медленно вращается вместе со стеной щитов.', 3.4, '#9FE6FF', 'ground', [
        L('glow', 'disc', 'glow', 0.8, -0.01, ap(0, 10, 'fade'), br=0.3),
        L('oct', 'disc', 'octagram', 1.0, 0.0, ap(0, 14, 'draw', startAngle=90), rot=17),
        L('ward', 'disc', 'circle_ward', 0.5, 0.01, ap(4, 12, 'grow', 'twist', easing='easeOutBack'), rot=-30, color='#FFFFFF', br=0.7),
    ], flash={'color': '#FFFFFF', 'size': 1.3, 'duration': 10, 'sparks': 16}, ddur=12)

    sigil('ark_sky', 'Ковчег: солнце с нимбом над куполом, лицом вниз.', 18.0, DGOLD, 'sky', [
        L('rays', 'spokes', 'rays', 0.8, -0.02, ap(0, 30, 'fade'), rot=1.5, br=0.5, pulse=(0.15, 50)),
        L('sun', 'disc', 'divine_sun', 0.7, 0.0, ap(0, 30, 'grow', 'twist'), rot=3),
        L('holy', 'disc', 'holy_seal', 1.0, 0.01, ap(10, 40, 'draw', startAngle=90), rot=-1.5, color=DPALE),
        L('rim', 'band', 'thin_ring', 1.06, 0.02, ap(30, 20, 'draw'), inner=0.985, repeat=1),
    ], flash={'color': '#FFFFFF', 'size': 1.2, 'duration': 14, 'sparks': 40}, ddur=30)
    sigil('ark_ground', 'Ковчег: граница купола на земле — кольцо рун и тонкий обод (радиус 32).', 32.0, DGOLD, 'ground', [
        L('runes', 'band', 'rune_band', 1.0, 0.0, ap(0, 30, 'draw', startAngle=90), inner=0.975, repeat=24, rot=0.8, br=0.9),
        L('ring', 'band', 'thin_ring', 0.96, 0.01, ap(10, 20, 'draw'), inner=0.996, repeat=1, color=DPALE, br=0.7),
        L('center', 'disc', 'holy_seal', 0.12, 0.02, ap(0, 20, 'grow', 'fade'), rot=-4),
    ], ddur=30)
    fx('ark', 'Ковчег: купол света на минуту — пузырь и кольцо, солнце-печать над куполом, столб к нему, '
              'завеса тонких лучей по границе, кольцо рун на земле, падают перья.', 'divine', 1200, [
        E('wave', 0, 'caster', duration=30, shape='ring', radius=32, color='@primary'),
        E('wave', 0, 'caster+0,0.5,0', duration=40, shape='sphere', radius=32, rim=1.2, color='@primary'),
        E('flash', 0, 'caster+0,1.5,0', duration=14, size=8, rays=12, screen=0.4, color='#FFF4D6'),
        E('sigil', 6, 'caster+0,32,0', id='ark_sky', until=1190),
        E('sigil', 0, 'caster+0,0.06,0', id='ark_ground', until=1190),
        E('column', 10, 'caster', duration=1180, radius=0.6, height=32, rings=3, ringSpeed=4, fill=1, color='@primary',
          **{'in': ease(20), 'out': ease(20)}),
        E('curtain', 10, 'caster', duration=1180, radius=32, count=72, height=26, grow=30, width=[0.06, 0.16], brightness=[0.15, 0.4],
          flicker=0.3, texture='beam_fade', color='@primary', **{'out': ease(20)}),
        E('sprites', 10, 'caster+0,22,0', duration=1180, texture='feather', count=1180, rate=1, area=28, speed=0.003, gravity=0.0015,
          sway=1.2, tumble=0.6, size=[0.45, 0.3], life=180, color='@secondary'),
    ])

    sigil('blood_moon', 'Кровавая луна: луна над кастером (всегда к зрителю), пульсирует как сердце.', 4.0, '#D0101E', 'billboard', [
        L('halo', 'disc', 'glow', 1.6, -0.02, ap(0, 30, 'fade'), br=0.5, pulse=(0.25, 20)),
        L('moon', 'disc', 'moon_disc', 1.0, 0.0, ap(0, 30, 'grow', 'fade'), color='#FF2A2A', pulse=(0.12, 20)),
        L('ring', 'disc', 'thin_ring', 1.25, 0.01, ap(10, 20, 'grow', 'fade'), color='#8A0010', br=1.3),
    ], ddur=24)
    sigil('blood_ground', 'Кровавая луна: печать крови под кастером на всю зону (радиус 16), бьётся в такт.', 16.0, '#D0101E', 'ground', [
        L('blood', 'disc', 'sigil_blood', 0.4, 0.0, ap(0, 20, 'draw', startAngle=90), rot=-6, pulse=(0.3, 20)),
        L('runes', 'band', 'rune_band', 1.0, 0.01, ap(6, 24, 'draw', startAngle=90), inner=0.95, repeat=16, rot=3, br=0.8),
        L('rim', 'band', 'thin_ring', 0.93, 0.02, ap(10, 20, 'draw'), inner=0.99, repeat=1, color='#FF5A5A', br=0.7),
    ], ddur=20)
    fx('blood_moon', 'Кровавая луна, 20 с: мир алеет, над кастером встаёт красная луна, печать крови под ногами, капли поднимаются.',
       'blood', 400, [
           E('tint', 0, 'caster', follow=True, duration=400, radius=24, color='#6A0008', strength=0.4, **{'in': ease(30), 'out': ease(20)}),
           E('sigil', 0, 'caster+0,14,0', follow=True, id='blood_moon', until=396),
           E('sigil', 0, 'caster+0,0.06,0', follow=True, id='blood_ground', until=396),
           E('sprites', 0, 'caster', follow=True, duration=396, texture='spark_soft', count=800, rate=2, area=15, speed=0.01,
             gravity=-0.004, size=[0.2, 0.05], life=50, color='@primary'),
       ])
    fx('blood_drain', 'Кровавая луна: нить крови от жертвы к кастеру.', 'blood', 16, [
        # луч от цели к заклинателю убран (владелец 19.11)
        E('sprites', 0, 'target+0,1,0', duration=8, texture='spark_soft', count=8, rate=1, spread=0.4, speed=0.03, size=[0.2, 0.05],
          life=14, color='@secondary'),
    ])

    pts = []
    for k in range(7):
        pts += [E('decal', k, 'point:p%d' % k, duration=70, texture='higher_cracks', radius=1.8, fadeOut=30, color='@primary'),
                E('sprites', k, 'point:p%d+0,0.3,0' % k, duration=40, texture='spark_sharp', count=20, rate=1, spread=0.6, speed=0.02,
                  gravity=-0.004, size=[0.2, 0.04], life=30, color='@secondary'),
                E('beam', 30, 'point:p%d' % k, to='point:p%d+0,9,0' % k, duration=30, width=1.2, core=0.3, grow=4, color='@primary',
                  **{'out': ease(14)}),
                E('flash', 30, 'point:p%d+0,0.5,0' % k, duration=10, size=2.4, color='#E8D0FF')]
    fx('world_rift', 'Разлом мира: трещина бежит вперёд (точки p0…p6 каждые 3 блока), под ней светится разлом; '
                     'через 1.5 с из трещины бьют столбы.', 'rift', 72, [
        *pts,
        E('flash', 30, 'caster+0,1,0', duration=10, size=3, screen=0.25, color='#E8D0FF'),
    ])


if __name__ == '__main__':
    styles()
    frozen_hour()
    taboo()
    downfall()
    milky_way()
    soul_devour()
    space_closure()
    fire()
    others()
    print('\n'.join(WRITTEN))
    print(len(WRITTEN), 'files')
