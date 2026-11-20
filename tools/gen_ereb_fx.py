#!/usr/bin/env python3
"""
T30 «Эреб, Первый Предатель» — эффекты, полоса босса по фазам, титры, lang, проверочные кадры.
Вызывается из tools/gen_ereb.py (run(M, args)). Время — тики, углы — градусы, размеры — блоки.
Переиспользует «Иллюзии» (T22, tools/gen_illusion_fx.py): спрайты mote_glass / mote_butterfly / mote_butterfly_side, печати
illusion_seal / illusion_face_ripple / illusion_mirror_crack, модель стеклянной бабочки fx/meshes/illusion_butterfly;
«Сон бабочки» — заклинание T22 целиком (tools/gen_celestial_butterfly.py), здесь только то, что до и после него.
Правило владельца: никаких лучей / нитей от босса к цели (docs/inbox/README.md) — связь с целью только бликом у самой цели.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
MEDIA = os.path.join(ROOT, 'docs', 'media')
M = None

GOLD, GOLD_HI, GLASS, GLASS_HI, INK, WHITE = '#E8B84A', '#FFE7A0', '#BFE6FF', '#E8FAFF', '#14121A', '#FFFFFF'
T_INTRO = 100        # появление = анимация ereb_spawn (5.0 с)
T_FINALE = 130       # финал = анимация ereb_finale (6.5 с)
PALM = 'caster-0.15,1.25,0.55'       # ладонь в позе финала (левая рука вперёд), оси взгляда: x — вправо, y — вверх, z — вперёд
RAISED = 'caster-0.3,2.1,0.2'        # поднятая ладонь (каст)


def E(type, delay=0, at='caster', **kw):
    o = {'type': type, 'delay': delay, 'at': at}
    o.update(kw)
    return o


def ease(d, e='easeOutCubic'):
    return {'duration': d, 'easing': e}


def fx(id_, comment, dur, els, style='ereb'):
    M.write_json('fx/%s.json' % id_, {'comment': comment + ' Сгенерировано tools/gen_ereb.py (gen_ereb_fx.py).', 'style': style,
                                      'duration': dur, 'elements': els})


def butterflies(delay, at, count, rate, dur, spread=0.5, speed=0.05, gravity=-0.008, life=40, size=(0.32, 0.12), color=GLASS, side=True, **kw):
    """Рой стеклянных бабочек: анфас и в профиль (как в T22), с мягким ореолом."""
    els = [E('sprites', delay, at, duration=dur, texture='mote_butterfly', count=count, rate=rate, spread=spread, speed=speed,
             gravity=gravity, sway=0.6, size=list(size), life=life, color=color, glow=0.45, **kw)]
    if side:
        els.append(E('sprites', delay, at, duration=dur, texture='mote_butterfly_side', count=max(1, count // 2), rate=max(0.5, rate / 2),
                     spread=spread, speed=speed, gravity=gravity, sway=0.6, size=[size[0] * 0.9, size[1]], life=life, color=GOLD_HI,
                     glow=0.35, **kw))
    return els


def glass(delay, at, count, rate=None, dur=2, spread=0.6, speed=0.08, gravity=0.006, life=18, size=(0.18, 0.05), color=GLASS_HI, **kw):
    return E('sprites', delay, at, duration=dur, texture='mote_glass', count=count, rate=rate or count, spread=spread, speed=speed,
             gravity=gravity, spin=140, tumble=True, size=list(size), life=life, color=color, **kw)


def effects():
    M.write_json('fx/styles/ereb.json', {
        'comment': 'T30 Эреб: золото отделки камзола и стекло иллюзий (холодный блик), тень — чёрное сукно. Движение плавное, '
                   'с короткими «звонкими» вспышками стекла. Сгенерировано tools/gen_ereb.py.',
        'palette': {'primary': GOLD, 'secondary': GLASS, 'core': WHITE, 'shadow': INK},
        'textures': {'sparks': 'spark_soft', 'runes': 'school_illusion_band', 'shards': 'mote_glass', 'sigil': 'illusion_seal'},
        'blend': 'additive', 'motion': {'rotationScale': 0.8, 'jitter': 0.08, 'easing': 'easeOutSine', 'pulse': {'amp': 0.08, 'period': 20}}})
    # ---------------------------------------------------------------- появление
    fx('ereb_intro', 'Появление (5.0 с = 100 тиков = анимация ereb_spawn). caster = Эреб на конечной точке, yaw — его взгляд. '
       '0–2.2 с: под ним печать иллюзий, из-за края арены слетается рой стеклянных бабочек и кружит воронкой (модель НЕ рисовать 0–44 тиков); '
       '1.5–2.2 с: рой сжимается в силуэт (оболочка); 2.2 с (form) — звон стекла: вспышка, бабочки разлетаются, он стоит; 2.6 поклон; '
       '3.9 с (salute) — салют рапирой, блик на клинке, титр; 5.0 — полоса босса.', T_INTRO + 10, [
        E('tint', 0, 'caster', duration=T_INTRO, radius=40, color='#1C1830', strength=0.22, **{'in': ease(20), 'out': ease(24, 'easeInSine')}),
        E('sigil', 4, 'caster+0,0.05,0', id='illusion_seal', until=T_INTRO, comment='печать иллюзий под ним'),
        *butterflies(0, 'caster+0,1.2,0', 140, 4, 40, spread=7.0, speed=0.02, gravity=-0.002, life=48, size=(0.36, 0.2),
                     comment='слетаются со всей арены'),
        E('vortex', 6, 'caster+0,0.1,0', duration=40, radius=2.6, height=2.6, arms=4, speed=9, pull=0.55, texture='mote_butterfly',
          particles=70, life=26, size=0.3, color=GLASS, funnel=0.35, turns=1.4, out=ease(8), comment='рой кружит воронкой'),
        E('aura', 30, 'caster', target='caster', duration=16, thickness=0.09, pulse=[0.6, 4], motes=6, texture='mote_glass', color=GLASS,
          brightness=0.8, **{'in': ease(10, 'easeInCubic'), 'out': ease(6)}, comment='рой сжимается в силуэт'),
        E('flash', 44, 'caster+0,1.1,0', duration=10, size=2.6, rays=8, color=WHITE, brightness=1.2, comment='form: звон стекла'),
        E('wave', 44, 'caster+0,1,0', duration=12, shape='sphere', radius=2.4, rim=1.0, color='@secondary', brightness=0.7),
        glass(44, 'caster+0,1.1,0', 30, spread=1.1, speed=0.14, gravity=0.012, life=22),
        *butterflies(44, 'caster+0,1.1,0', 26, 26, 2, spread=0.8, speed=0.11, gravity=-0.006, life=34),
        E('wave', 46, 'caster+0,0.05,0', duration=18, shape='ring', radius=8, color='@primary', brightness=0.5),
        E('flash', 78, 'caster+0.35,2.3,0.25', duration=7, size=0.5, rays=4, anamorphic=1.4, color=GOLD_HI, comment='салют: блик на клинке'),
    ])
    # ---------------------------------------------------------------- «Ложный союзник»
    fx('ereb_false_ally_glint', '«Ложный союзник», предупреждение (0.7 с): caster = игрок, в спину которому ударит Эреб. За спиной (0.9 бл. сзади, '
       'на высоте плеч) коротко звенит стекло: узкий блик с лучиками и три осколка. Без линий к боссу. Слать всем в 32 бл. '
       '(кто внимателен — увидит у союзника). Удар — через 16 тиков (ereb_vanish → ereb_appear → ereb_backstab).', 14, [
        E('flash', 0, 'caster+0,1.45,-0.9', follow=True, duration=7, size=0.9, anamorphic=1.8, rays=4, color=GLASS_HI, brightness=1.3),
        E('flash', 3, 'caster+0.25,1.7,-0.85', follow=True, duration=5, size=0.35, rays=4, color=WHITE),
        E('wave', 0, 'caster+0,1.45,-0.9', follow=True, duration=8, shape='sphere', radius=0.55, rim=1.0, color='@secondary', brightness=0.6),
        glass(1, 'caster+0,1.45,-0.9', 3, spread=0.25, speed=0.03, gravity=0.004, life=12),
    ])
    fx('ereb_vanish', 'Исчезновение (0.8 с, анимация ereb_vanish, событие gone 0.6 с): caster = Эреб. Оболочка-стекло, тело рассыпается осколками '
       'и парой бабочек. На 12 тике (gone) код прячет модель и делает босса неуязвимым до ereb_appear.', 18, [
        E('aura', 0, 'caster', target='caster', duration=12, thickness=0.06, pulse=[0.5, 3], motes=0, color=GLASS, brightness=0.6,
          **{'in': ease(3), 'out': ease(4)}),
        glass(10, 'caster+0,1.0,0', 18, dur=3, spread=0.55, speed=0.05, gravity=0.004, life=16),
        *butterflies(10, 'caster+0,1.2,0', 6, 3, 2, spread=0.4, speed=0.06, gravity=-0.01, life=24, side=False),
        E('flash', 12, 'caster+0,1.0,0', duration=6, size=1.2, color=GLASS_HI, brightness=0.8),
    ])
    fx('ereb_appear', 'Появление за спиной (0.5 с): caster = Эреб в новой точке (в облике союзника — тот же fx). Воздух «трескается» по росту, '
       'осколки слетаются внутрь, короткая вспышка. Сразу за ним — ereb_backstab (удар на 0.45 с).', 10, [
        E('aura', 0, 'caster', target='caster', duration=8, thickness=0.07, pulse=[0.6, 3], motes=0, color=GLASS_HI, brightness=0.7,
          **{'in': ease(1), 'out': ease(6)}),
        E('wave', 0, 'caster+0,1,0', duration=7, shape='sphere', radius=1.1, rim=1.0, color='@secondary', brightness=0.5),
        glass(0, 'caster+0,1,0', 10, spread=0.9, speed=-0.05, gravity=0.0, life=8),
        E('flash', 1, 'caster+0,1.1,0', duration=5, size=1.0, rays=6, color=WHITE),
    ])
    # ---------------------------------------------------------------- фехтование и иллюзии
    fx('ereb_thrust', 'Укол рапирой (событие hit анимаций ereb_lunge / ereb_flurry / ereb_parry / ereb_backstab): caster = Эреб. '
       'Узкий золотой блик на острие (2.2 бл. вперёд на высоте груди) — не луч и не след до цели.', 8, [
        E('flash', 0, 'caster+0.1,1.35,2.2', duration=5, size=0.45, anamorphic=1.2, rays=4, color=GOLD_HI, brightness=1.1),
        E('sprites', 0, 'caster+0.1,1.35,2.2', duration=1, texture='spark_soft', count=5, rate=5, spread=0.15, speed=0.06, gravity=0.01,
          size=[0.1, 0.02], life=7, color=GOLD),
    ])
    fx('ereb_shards', 'Магия руками — «стеклянные осколки» (анимация ereb_shard_cast, событие release 0.55 с = 11 тик): caster = Эреб. '
       'В ладони собирается стекло (0–11), на release — вспышка и веер осколков конусом вперёд (сами снаряды — сущности кода; '
       'этот fx — только вылет из ладони, без линии до цели).', 22, [
        glass(0, 'caster+0.25,1.35,0.6', 10, rate=1, dur=10, spread=0.35, speed=-0.03, gravity=0.0, life=8, comment='стекло стягивается к ладони'),
        E('flash', 2, 'caster+0.25,1.35,0.6', duration=9, size=0.45, color=GLASS_HI, brightness=0.8),
        E('flash', 11, 'caster+0.25,1.35,0.7', duration=6, size=1.0, rays=6, color=WHITE, brightness=1.1),
        E('sprites', 11, 'caster+0.25,1.35,0.7', duration=2, texture='mote_glass', count=14, rate=7, spread=0.1, speed=0.35, cone=40,
          gravity=0.004, spin=200, tumble=True, size=[0.2, 0.08], life=10, color=GLASS_HI),
    ])
    fx('ereb_parry', 'Парирование (событие parry 0.15 с анимации ereb_parry): caster = Эреб. Искры и звон у гарды.', 10, [
        E('flash', 0, 'caster+0.2,1.7,0.6', duration=6, size=0.7, rays=6, color=GOLD_HI, brightness=1.2),
        E('sprites', 0, 'caster+0.2,1.7,0.6', duration=1, texture='spark_soft', count=10, rate=10, spread=0.25, speed=0.12, gravity=0.02,
          size=[0.12, 0.02], life=9, color=GOLD),
    ])
    fx('ereb_cast_illusion', 'Каст иллюзий (анимация ereb_cast_illusion, событие cast 0.75 с — щелчок пальцами): caster = Эреб. Над поднятой '
       'левой рукой — блик стекла и кольцо-рябь, вокруг него — мерцание. Сами заклинания («Отражения», «Пелена», лабиринт) — их fx из T22.', 20, [
        E('flash', 14, 'caster-0.3,2.15,0.25', duration=8, size=0.7, rays=6, color=GLASS_HI, brightness=1.1),
        E('wave', 15, 'caster-0.3,2.15,0.25', duration=10, shape='sphere', radius=0.9, rim=1.0, color='@secondary', brightness=0.6),
        E('aura', 10, 'caster', target='caster', duration=10, thickness=0.05, pulse=[0.4, 4], motes=4, texture='mote_glass', color=GLASS,
          brightness=0.5),
    ])
    fx('ereb_disguise', 'Смена облика (анимация ereb_disguise, событие swap 0.5 с = 10 тик): caster = Эреб. Ладонь проводит по лицу — рябь '
       'зеркала у лица, по телу пробегает стеклянная оболочка; ровно на 10 тике код меняет облик (скин/ник участника, как T22 «Чужое лицо»). '
       'Обратная смена (снять облик) — тот же fx.', 20, [
        E('sigil', 4, 'caster.eyes+0,0,0.35', follow=True, id='illusion_face_ripple', until=16),
        E('aura', 8, 'caster', target='caster', duration=10, thickness=0.07, pulse=[0.6, 3], motes=4, texture='mote_glass', color=GLASS_HI,
          brightness=0.7, **{'in': ease(1), 'out': ease(9)}),
        E('wave', 10, 'caster+0,1,0', duration=10, shape='sphere', radius=1.3, rim=1.0, color='@secondary', brightness=0.5),
        E('sprites', 10, 'caster+0,1,0', duration=2, texture='spark_soft', count=8, rate=4, spread=0.5, speed=0.03, gravity=-0.004,
          size=[0.12, 0.03], life=14, color=GOLD),
    ])
    fx('ereb_false_face', 'Фаза 3 «Предательство»: союзник, который выглядит как Эреб (6 с = 120 тиков; caster = союзник, follow; видит только '
       'обманутый игрок). Едва заметная подсказка: раз в ~1.5 с по силуэту пробегает стеклянный отблеск и падает осколок — '
       'кто присмотрится, отличит ложного Эреба от настоящего.', 120, [
        E('aura', 0, 'caster', target='caster', follow=True, duration=120, thickness=0.035, pulse=[0.5, 30], motes=0, ring=False,
          color=GLASS, brightness=0.35),
        glass(0, 'caster+0,1.6,0', 4, rate=0.04, dur=110, spread=0.3, speed=0.0, gravity=0.004, life=20, size=(0.12, 0.04), follow=True),
    ])
    for n, (dur, txt, crack) in {2: (40, 'Фаза 2 «Чужое лицо» (66%)', 'illusion_mirror_crack'), 3: (50, 'Фаза 3 «Предательство» (33%)',
                                                                                                    'illusion_mirror_crack')}.items():
        fx('ereb_phase%d' % n, txt + ': caster = Эреб (анимация ereb_phase, событие phase 0.8 с = 16 тик). Вокруг него на миг проступает '
           'стекло: трещины по воздуху на 16 тике, осколки осыпаются, кольцо по земле r12' + (', мир на 2 с тускнеет' if n == 3 else '') + '.', dur, [
            E('sigil', 10, 'caster+0,1.2,0', id=crack, until=34, comment='трещины стекла в воздухе перед ним'),
            E('flash', 16, 'caster+0,1.2,0', duration=8, size=2.0, rays=8, color=WHITE, brightness=1.0),
            E('wave', 16, 'caster+0,1,0', duration=14, shape='sphere', radius=3.0, rim=1.0, color='@secondary', brightness=0.6),
            E('wave', 17, 'caster+0,0.05,0', duration=20, shape='ring', radius=12, color='@primary', brightness=0.5),
            glass(16, 'caster+0,2.2,0', 40, rate=10, dur=6, spread=2.0, speed=0.04, gravity=0.02, life=30),
            *([E('tint', 16, 'caster', duration=40, radius=32, color='#101420', strength=0.35, **{'in': ease(6), 'out': ease(20)})] if n == 3 else []),
        ])
    # ---------------------------------------------------------------- финал: «Сон бабочки» и исчезновение
    fx('ereb_finale', 'Финал (6.5 с = 130 тиков = анимация ereb_finale; при 5% ХП). caster = Эреб (не follow: он стоит). '
       '0.3 с (smile) — код меняет текстуру на ereb_smile; 1.4 с (butterfly, тик 28) — из ладони вырастает стеклянная бабочка '
       '(модель illusion_butterfly T22, ×0.24), трепещет у ладони; 3.2 с (cast, тик 64) — он поднимает её, она вспархивает со вспышкой: '
       'код начинает «Сон бабочки» (ButterflyDreamSpell) с caster = ТОЧКА Эреба (не сущность — он исчезнет); '
       '2.4 с (speak, тик 48) — фраза «В любом случае, от вас мне больше нет пользы» (ui…ereb.vanish_line: чат r48 + субтитр); 5.0 с (vanish, тик 100) — Эреб рассыпается бабочками (fx ereb_butterfly_dissolve — уже внутри этого fx; модель спрятать на 104).',
       T_FINALE + 10, [
        E('flash', 26, PALM, duration=10, size=0.6, color=GLASS_HI, brightness=0.9, comment='свет в ладони'),
        glass(26, PALM, 8, rate=4, dur=2, spread=0.15, speed=-0.02, gravity=0.0, life=6, comment='осколки складываются в бабочку'),
        E('mesh', 28, PALM, model='illusion_butterfly', scale=0.24, until=64, comment='стеклянная бабочка в ладони'),
        E('sprites', 30, PALM, duration=34, texture='glow', count=34, rate=1, spread=0.12, speed=0.004, gravity=-0.002, size=[0.16, 0.04],
          life=10, color=GLASS, brightness=0.6),
        E('mesh', 62, RAISED, model='illusion_butterfly', scale=0.26, until=70, comment='поднял над головой'),
        E('flash', 64, RAISED, duration=12, size=1.6, rays=8, color=WHITE, brightness=1.2, comment='cast: вспорхнула — дальше «Сон бабочки»'),
        *butterflies(64, RAISED, 10, 10, 2, spread=0.3, speed=0.09, gravity=-0.02, life=30),
        *dissolve_elements(100),
    ])
    fx('ereb_butterfly_dissolve', 'Исчезновение бабочками (3 с = 60 тиков): caster = Эреб. Оболочка-стекло, тело рассыпается роем стеклянных '
       'и золотых бабочек снизу вверх, они улетают вверх и в стороны; на 4 тике код прячет модель (в финале — внутри ereb_finale, тик 100). '
       'Можно и отдельно (если финал прерван).', 64, dissolve_elements(0))


def dissolve_elements(d0):
    return [
        E('aura', d0, 'caster', target='caster', duration=8, thickness=0.09, pulse=[0.8, 3], motes=10, texture='mote_glass', color=GLASS_HI,
          brightness=0.9, **{'in': ease(2), 'out': ease(6)}),
        E('flash', d0 + 3, 'caster+0,1.1,0', duration=10, size=2.2, rays=6, color=WHITE, brightness=1.0),
        *butterflies(d0 + 2, 'caster+0,0.3,0', 24, 8, 3, spread=0.35, speed=0.06, gravity=-0.012, life=46, size=(0.34, 0.16)),
        *butterflies(d0 + 3, 'caster+0,1.0,0', 40, 10, 4, spread=0.4, speed=0.08, gravity=-0.014, life=50, size=(0.36, 0.16)),
        *butterflies(d0 + 4, 'caster+0,1.7,0', 26, 13, 2, spread=0.35, speed=0.1, gravity=-0.016, life=50, size=(0.34, 0.14)),
        E('sprites', d0 + 4, 'caster+0,1,0', duration=40, texture='mote_sky_butterfly', count=12, rate=0.3, spread=1.5, speed=0.03,
          gravity=-0.01, sway=0.6, size=[0.4, 0.2], life=50, color=GOLD_HI, glow=0.5, comment='последние — золотые'),
        glass(d0 + 3, 'caster+0,1,0', 26, rate=13, dur=2, spread=0.55, speed=0.07, gravity=0.012, life=24),
        E('wave', d0 + 4, 'caster+0,0.05,0', duration=20, shape='ring', radius=5, color='@secondary', brightness=0.4),
    ]


# ================================================================== полоса босса (192×36, формат tyros_bossbar: 0–17 пустая, 18–35 полная)
BUTTERFLY = ['.gg.........gg.',
             'gzzg..g.g..gzzg',
             'gyzzg.gtg.gzzyg',
             '.gyzzgtktgzzyg.',
             '..gyygtktgyyg..',
             '..gxyg.t.gyxg..',
             '...gg.....gg...']
BUTTERFLY_BROKEN = ['.gg.........z..',
                    'gzzg..g.g...y.z',
                    'gyzzg.gtg.g..y.',
                    '.gyzzgtktg.z...',
                    '..gyygtktgy..y.',
                    '..gxyg.t.g.x...',
                    '...gg.....g....']
MASKS = ['..ggggg.ggggg..',            # фаза 2: две маски — светлая и чёрная («Чужое лицо»)
         '.gzzzzzgkkkkkg.',
         '.gzkzkzgkzkzkg.',
         '.gzzzzzgkkkkkg.',
         '..gzzzg.gkkkg..',
         '...gzg...gkg...',
         '....g.....g....']
BAR_COL = {'g': '#e2b443', 't': '#fff2b0', 'k': '#0b0a0f', 'x': '#1f4a63', 'y': '#3d8fb5', 'z': '#8fd8f2', 'o': '#704612', 's': '#f8d260'}
FILL = {1: ['#fff2b0', '#f8d260', '#eab33c', '#d0952a', '#a46a1c'],          # золото
        2: ['#f8d260', '#d0952a', '#a46a1c', '#7a4c14', '#5a3610'],          # тусклее: лицо прячется
        3: ['#e8faff', '#bfe6ff', '#8fd8f2', '#3d8fb5', '#1f4a63']}          # стекло
EMPTY = ['#29252f', '#1d1a24', '#14121a', '#0b0a0f', '#0b0a0f']


def _put_art(img, art, x0, y0, cols=BAR_COL):
    for j, r in enumerate(art):
        for i, ch in enumerate(r):
            if ch != '.':
                img.putpixel((x0 + i, y0 + j), M.hx(cols[ch]))


def bossbar(phase):
    src = M.jar_img(M.I + 'textures/gui/sprites/boss_bars/tyros_bossbar.png')
    a = np.asarray(src).copy()
    for half in (0, 18):
        a[half:half + 7, :] = 0                                         # убрать узор Тироса
        for y in range(half + 7, half + 12):                            # табличка с крестом в середине → обычная полоса
            a[y, 88:104] = a[y, 80]
    img = Image.fromarray(a, 'RGBA').copy()
    px = img.load()
    for half, ramp in ((0, EMPTY), (18, FILL[phase])):
        # внутренность полосы — красные пиксели Тироса; перекрашиваем по строке: свет сверху, тень снизу
        rows = sorted({y for y in range(half, half + 18) for x in range(192) if px[x, y][3] and px[x, y][0] > px[x, y][1] + 40})
        for x in range(192):
            for y in range(half, half + 18):
                r, g, b, al = px[x, y]
                if al and r > g + 40:
                    k = rows.index(y) if y in rows else 0
                    c = ramp[min(len(ramp) - 1, int(k * len(ramp) / max(1, len(rows))))]
                    if half == 18 and phase == 3 and (x * 7 + y * 3) % 23 == 0:
                        c = '#ffffff'                                       # искорки стекла в заливке
                    px[x, y] = M.hx(c)
    for half in (0, 18):
        art = {1: BUTTERFLY, 2: MASKS, 3: BUTTERFLY_BROKEN}[phase]
        _put_art(img, art, 96 - 7, half + 1)
        # филигрань по сторонам: тонкая золотая нить, сходящая на нет, с бусинами и стеклянной каплей
        for sgn in (-1, 1):
            for dx in range(9, 47):
                x = 96 + sgn * dx - (1 if sgn < 0 else 0)
                img.putpixel((x, half + 6), M.hx(BAR_COL['g' if dx < 30 else 'o']))
            for dx, ch in ((14, 's'), (22, 'z'), (30, 's'), (40, 'g')):
                x = 96 + sgn * dx - (1 if sgn < 0 else 0)
                img.putpixel((x, half + 5), M.hx(BAR_COL[ch]))
                if ch == 'z':
                    img.putpixel((x, half + 4), M.hx(BAR_COL['g']))
        if phase >= 2:
            # трещины зеркала по рамке: стеклянные зигзаги через полосу
            for cx in ((40, 133, 170) if phase == 2 else (22, 40, 61, 133, 150, 170)):
                for (dx, dy) in ((0, 6), (1, 7), (1, 8), (0, 9), (1, 10), (2, 11), (2, 12)):
                    x, y = cx + dx, half + dy
                    if px[x, y][3]:
                        px[x, y] = M.hx('#e8faff' if dy in (7, 10) else '#8fd8f2')
        if phase == 3:
            for (x, y, ch) in ((30, 4, 'z'), (31, 3, 'y'), (58, 5, 'z'), (138, 4, 'z'), (139, 5, 'y'), (162, 3, 'z'), (163, 4, 'x')):
                img.putpixel((x, half + y), M.hx(BAR_COL[ch]))       # осколки над рамкой
    return img


def bossbars():
    names = {1: 'ereb_bossbar', 2: 'ereb_bossbar_p2', 3: 'ereb_bossbar_p3'}
    bars = {}
    for p, nm in names.items():
        im = bossbar(p)
        im.save(M.out('textures/gui/sprites/boss_bars/%s.png' % nm))
        bars[p] = im
    # вспышка смены фазы: силуэт полосы светлым стеклом (192×18)
    full = np.asarray(bars[1].crop((0, 18, 192, 36))).copy()
    m = full[..., 3] > 0
    fl = np.zeros_like(full)
    fl[m] = M.hx('#e8faff')
    Image.fromarray(fl, 'RGBA').save(M.out('textures/gui/sprites/boss_bars/ereb_bossbar_flash.png'))
    return bars


# ================================================================== титры (1024×192): золото по чёрному, ореол — стекло
def _font(name, sz):
    return ImageFont.truetype(os.path.join(HERE, 'fonts', name), sz)



LAT, CYR = 'CormorantGaramond-BoldItalic-latin.woff', 'CormorantGaramond-BoldItalic-cyrillic.woff'


class MixFont:
    """Кириллица — из cyrillic-шрифта, всё прочее (цифры, запятая, апостроф) — из latin (в cyrillic-подмножестве их нет)."""

    def __init__(self, size):
        self.c, self.l = _font(CYR, size), _font(LAT, size)

    def f(self, ch):
        return self.c if '\u0400' <= ch <= '\u04ff' else self.l

    def length(self, text):
        return sum(self.f(ch).getlength(ch) for ch in text)

    def bbox(self, text):
        x0, y0, x1, y1 = 0, 1e9, 0, -1e9
        for ch in text:
            b = self.f(ch).getbbox(ch)
            if b[3] > b[1]:
                y0, y1 = min(y0, b[1]), max(y1, b[3])
        return (0, y0, self.length(text), y1)

    def draw(self, d, xy, text):
        x, y = xy
        for ch in text:
            d.text((x, y), ch, font=self.f(ch), fill=255)
            x += self.f(ch).getlength(ch)


def title_img(text, font, sub=None, sub_font=None, mark=None):
    gold = [M.hx(c) for c in ('#fff2b0', '#f8d260', '#eab33c', '#a46a1c')]
    S = 2
    Wd, Hd = 1024 * S, 192 * S
    size = (84 if not sub else 70) * S
    fnt = MixFont(size)
    bb = fnt.bbox(text)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    if tw > Wd * 0.92:
        fnt = MixFont(int(size * Wd * 0.92 / tw))
        bb = fnt.bbox(text)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
    tx, ty = (Wd - tw) / 2 - bb[0], (18 if not sub else 6) * S - bb[1] + ((96 if not sub else 80) * S - th) / 2
    mask = Image.new('L', (Wd, Hd), 0)
    fnt.draw(ImageDraw.Draw(mask), (tx, ty), text)
    if sub:
        f2 = MixFont(40 * S)
        b2 = f2.bbox(sub)
        f2.draw(ImageDraw.Draw(mask), ((Wd - (b2[2] - b2[0])) / 2 - b2[0], 96 * S - b2[1]), sub)
        th = 96 * S + (b2[3] - b2[1]) - (ty + bb[1])
    m = np.asarray(mask, np.float32) / 255
    yy = np.linspace(0, 1, Hd)[:, None]
    t = np.clip((yy * Hd - (ty + bb[1])) / th, 0, 1)
    grad = np.zeros((Hd, 1, 3), np.float32)
    stops = [(0.0, gold[0]), (0.4, gold[1]), (0.78, gold[2]), (1.0, gold[3])]
    for k in range(len(stops) - 1):
        (t0, c0), (t1, c1) = stops[k], stops[k + 1]
        sel = (t >= t0) & (t <= t1)
        u = (t - t0) / (t1 - t0)
        for ch in range(3):
            grad[..., ch] = np.where(sel, c0[ch] + (c1[ch] - c0[ch]) * u, grad[..., ch])
    rgb = np.broadcast_to(grad, (Hd, Wd, 3))
    outline = np.asarray(mask.filter(ImageFilter.MaxFilter(9)), np.float32) / 255
    halo = np.asarray(mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(20 * S)), np.float32) / 255
    o = np.zeros((Hd, Wd, 4), np.float32)
    o[..., :3] = np.array(M.hx('#5fb8e0')[:3], np.float32)          # холодный ореол стекла
    o[..., 3] = np.clip(halo * 1.3, 0, 0.6)
    ob = np.array(M.hx('#0b0a0f')[:3], np.float32)
    o[..., :3] = o[..., :3] * (1 - outline[..., None]) + ob * outline[..., None]
    o[..., 3] = np.maximum(o[..., 3], outline)
    o[..., :3] = o[..., :3] * (1 - m[..., None]) + rgb * m[..., None]
    o[..., 3] = np.maximum(o[..., 3], m)
    o[..., 3] *= 255
    img = Image.fromarray(o.clip(0, 255).astype(np.uint8), 'RGBA').resize((1024, 192), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    y = 150 if not sub else 170
    for x in range(150, 874):
        k = 1 - abs(x - 512) / 362
        a_ = int(255 * min(1, k * 2.2))
        if abs(x - 512) < 34 and mark is not None:
            continue
        d.point((x, y), fill=M.hx('#f8d260', a_))
        d.point((x, y + 1), fill=M.hx('#a46a1c', a_))
        d.point((x, y - 1), fill=M.hx('#0b0a0f', int(a_ * 0.8)))
        d.point((x, y + 2), fill=M.hx('#0b0a0f', int(a_ * 0.8)))
    if mark is not None:
        img.alpha_composite(mark, (512 - mark.width // 2, y - mark.height // 2))
    return img


def titles(bars):
    mark = bars[1].crop((89, 1, 104, 8)).resize((45, 21), Image.NEAREST)
    for lang, name, nf, sub, sf in (('ru', 'Эреб, Первый Предатель', CYR, 'Глава 1 Ячейки Культа', CYR),
                                    ('en', 'Ereb, the First Traitor', LAT, 'Head of the Cult\'s First Cell', LAT)):
        title_img(name, nf, sub, sf, mark).save(M.out('textures/gui/title/ereb_%s.png' % lang))
    for key, ru, en in (('false_ally', 'Ложный союзник', 'The False Ally'), ('butterfly', 'Сон бабочки', 'The Butterfly Dream'),
                        ('labyrinth', 'Зеркальный лабиринт', 'The Mirror Labyrinth')):
        title_img(ru, CYR, mark=mark).save(M.out('textures/gui/title/ereb_%s_ru.png' % key))
        title_img(en, LAT, mark=mark).save(M.out('textures/gui/title/ereb_%s_en.png' % key))


# ================================================================== lang
LANG = {
    'entity.pohsmp_core.ereb': ('Эреб, Первый Предатель', 'Ereb, the First Traitor'),
    'item.pohsmp_core.ereb_rapier': ('Рапира Эреба', 'Ereb\'s Rapier'),
    'ui.pohsmp_core.ereb.title': ('Эреб, Первый Предатель', 'Ereb, the First Traitor'),
    'ui.pohsmp_core.ereb.epithet': ('Глава 1 Ячейки Культа', 'Head of the Cult\'s First Cell'),
    'ui.pohsmp_core.ereb.phase1': ('«Две правды»', '"Two Truths"'),
    'ui.pohsmp_core.ereb.phase2': ('«Чужое лицо» — Эреб прячется среди вас.', '"A Borrowed Face" — Ereb hides among you.'),
    'ui.pohsmp_core.ereb.phase3': ('«Предательство» — не верь тем, кто рядом.', '"Betrayal" — trust no one beside you.'),
    'ui.pohsmp_core.ereb.false_ally_warn': ('За спиной блеснуло стекло…', 'Glass glints behind you…'),
    'ui.pohsmp_core.ereb.false_ally': ('Эреб наносит удар в спину!', 'Ereb strikes you in the back!'),
    'ui.pohsmp_core.ereb.false_ally_title': ('Ложный союзник', 'The False Ally'),
    'ui.pohsmp_core.ereb.labyrinth': ('Зеркальный лабиринт', 'The Mirror Labyrinth'),
    'ui.pohsmp_core.ereb.betrayal_hint': ('Союзники выглядят как Эреб — присмотрись к отблеску стекла.',
                                          'Your allies look like Ereb — watch for the glint of glass.'),
    'ui.pohsmp_core.ereb.finale': ('Эреб улыбается…', 'Ereb smiles…'),
    'ui.pohsmp_core.ereb.butterfly': ('Сон бабочки', 'The Butterfly Dream'),
    'ui.pohsmp_core.ereb.vanish': ('Эреб исчез. Бой окончен.', 'Ereb has vanished. The battle is over.'),
    'ui.pohsmp_core.ereb.vanish_line': ('В любом случае, от вас мне больше нет пользы.', 'Either way, you are of no further use to me.'),
}


def lang():
    for i, name in enumerate(('ru_ru', 'en_us')):
        p = os.path.join(M.A, 'lang', name + '.json')
        d = json.load(open(p, encoding='utf-8'))
        for k, v in LANG.items():
            d[k] = v[i]
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')
        M.WRITTEN.append('lang/%s.json (+%d ключей)' % (name, len(LANG)))


# ================================================================== обзорные картинки
def font(sz):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def sheet_ui(bars):
    Wd, Hd = 1600, 1000
    img = Image.new('RGBA', (Wd, Hd), M.hx('#16151b'))
    d = ImageDraw.Draw(img)
    f1, f2 = font(24), font(18)
    d.text((24, 14), 'T30 — полоса Эреба по фазам (×4) и титры ru/en', font=f1, fill=(240, 230, 210))

    def bar_at(src, x, y, p):
        e = src.crop((0, 0, 192, 18))
        f = src.crop((0, 18, 192, 36))
        w = int(3 + p * (192 - 6))
        e.alpha_composite(f.crop((0, 0, w, 18)), (0, 0))
        img.alpha_composite(e.resize((192 * 4, 72), Image.NEAREST), (x, y))
    ty = M.jar_img(M.I + 'textures/gui/sprites/boss_bars/tyros_bossbar.png')
    rows = [(ty, 0.7, 'tyros_bossbar (исходник Iron\'s — формат)'), (bars[1], 0.9, 'фаза 1 «Две правды» — 90%: золото, стеклянная бабочка'),
            (bars[2], 0.5, 'фаза 2 «Чужое лицо» — 50%: две маски, трещины зеркала'),
            (bars[3], 0.2, 'фаза 3 «Предательство» — 20%: стекло, бабочка разбита')]
    for i, (b, p, lab) in enumerate(rows):
        bar_at(b.copy(), 24, 60 + i * 96, p)
        d.text((24 + 192 * 4 + 20, 84 + i * 96), lab, font=f2, fill=(210, 200, 185))
    fl = Image.open(os.path.join(M.A, 'textures/gui/sprites/boss_bars/ereb_bossbar_flash.png')).convert('RGBA')
    img.alpha_composite(fl.resize((192 * 4, 72), Image.NEAREST), (24, 448))
    d.text((24 + 192 * 4 + 20, 472), 'ereb_bossbar_flash — вспышка смены фазы', font=f2, fill=(210, 200, 185))
    for i, lang_ in enumerate(('ru', 'en')):
        t = Image.open(os.path.join(M.A, 'textures/gui/title/ereb_%s.png' % lang_)).convert('RGBA')
        bg = Image.new('RGBA', (1024, 192), M.hx('#2a2833'))
        bg.alpha_composite(t)
        img.alpha_composite(bg.resize((768, 144)), (24, 540 + i * 160))
    for i, k in enumerate(('false_ally_ru', 'butterfly_en', 'labyrinth_ru')):
        t = Image.open(os.path.join(M.A, 'textures/gui/title/ereb_%s.png' % k)).convert('RGBA')
        bg = Image.new('RGBA', (1024, 192), M.hx('#2a2833'))
        bg.alpha_composite(t)
        img.alpha_composite(bg.resize((640, 120)), (820, 540 + i * 136))
    img.convert('RGB').save(os.path.join(MEDIA, 't30_ui.jpg'), quality=92)
    print('wrote docs/media/t30_ui.jpg')


def sheet_textures():
    Wd, Hd = 1600, 820
    img = Image.new('RGBA', (Wd, Hd), M.hx('#16151b'))
    d = ImageDraw.Draw(img)
    f1, f2 = font(24), font(18)
    d.text((24, 14), 'T30 — текстуры Эреба 128×128 (1 тексель = 1/16 блока, ×5) и скин владельца', font=f1, fill=(240, 230, 210))
    T_ = os.path.join(M.A, 'textures', 'entity', 'ereb')
    for i, nm in enumerate(('ereb', 'ereb_smile', 'ereb_glowmask')):
        t = Image.open(os.path.join(T_, nm + '.png')).convert('RGBA')
        bg = Image.new('RGBA', t.size, M.hx('#3a3a40') if 'glow' not in nm else M.hx('#000000'))
        bg.alpha_composite(t)
        img.alpha_composite(bg.resize((480, 480), Image.NEAREST), (24 + i * 500, 60))
        d.text((24 + i * 500, 546), nm + '.png', font=f2, fill=(220, 210, 195))
    # лица крупно
    for i, nm in enumerate(('ereb', 'ereb_smile')):
        t = Image.open(os.path.join(T_, nm + '.png')).convert('RGBA').crop((8, 8, 16, 16)).resize((160, 160), Image.NEAREST)
        img.alpha_composite(t, (24 + i * 180, 590))
    d.text((24, 760), 'лицо: обычное / улыбка (финал)', font=f2, fill=(220, 210, 195))
    ref = Image.open(os.path.join(ROOT, 'docs', 'references', 't30', 'ereb_front.jpg')).convert('RGBA')
    ref = ref.crop((60, 50, 270, 140)).resize((420, 180), Image.NEAREST)
    img.alpha_composite(ref, (400, 590))
    d.text((400, 776), 'скин владельца (фото)', font=f2, fill=(220, 210, 195))
    r3 = Image.open(os.path.join(M.A, 'textures', 'item', 'ereb_rapier.png')).convert('RGBA')
    bg = Image.new('RGBA', (16, 16), M.hx('#3a3a40'))
    bg.alpha_composite(r3)
    img.alpha_composite(bg.resize((160, 160), Image.NEAREST), (900, 590))
    d.text((900, 760), 'ereb_rapier.png (GUI)', font=f2, fill=(220, 210, 195))
    img.convert('RGB').save(os.path.join(MEDIA, 't30_textures.jpg'), quality=92)
    print('wrote docs/media/t30_textures.jpg')


def run(mod, args):
    global M
    M = mod
    effects()
    bars = bossbars()
    titles(bars)
    lang()
    os.makedirs(MEDIA, exist_ok=True)
    sheet_ui(bars)
    sheet_textures()
    if '--shots' in args:
        import gen_ereb_shots as SH
        SH.shots(M, args)
    if '--html' in args:
        import gen_ereb_render as R
        with open(os.path.join(HERE, 'ereb_preview.html'), 'w', encoding='utf-8') as fh:
            fh.write(R.page(['ereb', 'cult_leader']))
        print('wrote tools/ereb_preview.html')
