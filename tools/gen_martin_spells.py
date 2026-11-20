#!/usr/bin/env python3
"""
T29 «Мартин» — «+4 заклинания» (владелец 20.11): «Стена щитов», «Залп лучников», «Вызов на дуэль», «Боевой клич».
Анимации Мартина — в gen_martin.anims (martin_shield_wall, martin_volley, martin_duel, martin_warcry). Здесь: мэши (стена щитов,
призрачный лучник, стрела), рисунки (метка залпа, кольцо дуэли), fx, иконки статусов, lang, звуки, кадр docs/media/t29_spells4.jpg.
Вызывается из tools/gen_martin.py (run(M, args)).
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_martin_fx as FX  # noqa: E402
import gen_martin_extra as X  # noqa: E402
from nightmare_geo import Model  # noqa: E402
from gen_martin_fx import E, ease, at, hx, GHOST, GHOST_HOT, CRIMSON, DUST  # noqa: E402

M = None
WALL_W, WALL_PUSH, WALL_T = 24.0, 18.0, 160     # ширина стены, путь, время прохода (тики)
MARK_T = 30                                       # метка залпа 1.5 с
DUEL_R, DUEL_T = 6.0, 120                         # кольцо дуэли r6, 6 с
CRY_R, CRY_BUFF = 12.0, 120                       # клич r12, баф 6 с

GHOST_TONES = ['#86bcd2', '#3e6a80', '#e4f2c8', '#2e5e78', '#c8f4ff', '#a6d6e6', '#16303c']


def _mesh_doc(comment, boxes, opacity=0.5, glow=(2, 4), appear=10):
    ys = [b[1] for b in boxes] + [b[4] for b in boxes]
    return {'comment': comment, 'style': 'martin_ghost', 'center': 0, 'formedAt': appear, 'collapse': {'duration': 12, 'easing': 'easeInCubic'},
            'parts': [{'type': 'boxes', 'tones': GHOST_TONES, 'glowTones': list(glow), 'blend': 'translucent', 'opacity': opacity, 'shade': True,
                       'boxes': boxes, 'appear': {'delay': 0, 'duration': appear, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.5},
                       'bounds': [round(min(ys), 3), round(max(ys), 3)]}]}


# ================================================================== мэши
def mesh_shield_line():
    """Стена башенных щитов шириной WALL_W бл. лицом вперёд (+z): группы по 4 щита, между группами — просветы 1.6 бл."""
    boxes = []
    x = -WALL_W / 2
    k = 0
    while x < WALL_W / 2 - 1.0:
        for _ in range(4):
            if x > WALL_W / 2 - 1.0:
                break
            cx = x + 0.6
            r = lambda a, b, t: [round(v, 3) for v in a] + [round(v, 3) for v in b] + [t]
            boxes.append(r((cx - 0.58, 0.0, -0.06), (cx + 0.58, 2.3, 0.06), 0))           # полотно щита
            boxes.append(r((cx - 0.62, 2.3, -0.08), (cx + 0.62, 2.42, 0.08), 5))          # верхняя кромка
            boxes.append(r((cx - 0.62, 0.0, -0.08), (cx - 0.54, 2.3, 0.08), 5))           # боковые кромки
            boxes.append(r((cx + 0.54, 0.0, -0.08), (cx + 0.62, 2.3, 0.08), 5))
            boxes.append(r((cx - 0.16, 1.2, 0.06), (cx + 0.16, 1.55, 0.14), 2))           # умбон-корона (светится)
            boxes.append(r((cx - 0.3, 1.08, 0.06), (cx + 0.3, 1.16, 0.12), 2))
            boxes.append(r((cx - 0.05, 2.42, -0.05), (cx + 0.05, 3.0, 0.05), 1))          # копьё над щитом
            boxes.append(r((cx - 0.08, 3.0, -0.08), (cx + 0.08, 3.25, 0.08), 4))
            x += 1.24
            k += 1
        x += 1.6
    M.write_json('fx/meshes/martin_shield_line.json', _mesh_doc(
        'T29 «Стена щитов»: призрачная стена башенных щитов шириной %g бл. лицом вперёд (+z), группы по 4 щита, просветы 1.6 бл. между '
        'группами (x просветов: см. письмо). Центр низа — (0,0,0). Сгенерировано gen_martin_spells.py.' % WALL_W, boxes, opacity=0.55), compact=True)
    gaps = []
    x = -WALL_W / 2
    while x < WALL_W / 2 - 1.0:
        x += 1.24 * 4
        gaps.append(round(x + 0.8, 2))
        x += 1.6
    return gaps[:-1] if gaps and gaps[-1] > WALL_W / 2 else gaps


def mesh_archer():
    """Призрачный лучник: солдат в лёгких латах, лук натянут вверх-вперёд (навесная стрельба), колчан за спиной."""
    m = Model('martin_archer', density=1, tex_w=64)
    for n in ('steel', 'dark', 'gold', 'cloth', 'eye', 'bow'):
        m.materials[n] = lambda ctx: (np.zeros((ctx.n, 3)), 1.0, None)
    b = 'b'
    m.bone(b, None, (0, 0, 0))
    for sx in (-1, 1):
        m.rod(b, (sx * 2.0, 12, 0), (sx * 2.4, 0.5, -1.0 if sx > 0 else 1.5), 3.6, 3.6, 'steel')       # ноги в шаге
    m.box(b, (-4, 12, -2.2), (4, 24, 2.2), 'steel')
    m.box(b, (-4.2, 10.5, -2.4), (4.2, 13, 2.4), 'cloth')
    m.box(b, (-4.3, 22.6, -2.6), (4.3, 24.4, 2.6), 'gold')
    m.cbox(b, (0, 28, -0.2), (7.2, 7.4, 7.2), 'steel')                                               # шлем-шапель
    m.cbox(b, (0, 28.6, -0.2), (10, 0.8, 10), 'steel')                                               # поля шапеля
    m.box(b, (-2.6, 27.6, -3.9), (2.6, 28.4, -3.7), 'eye')
    m.box(b, (2.0, 14, 2.2), (4.4, 25, 4.4), 'dark')                                                 # колчан
    for k in range(4):
        m.box(b, (2.4 + 0.5 * k, 25, 2.6), (2.7 + 0.5 * k, 27.5, 2.9), 'gold')                       # оперения
    # руки и лук: лук поднят под 45° вперёд-вверх
    d = np.array([0, 0.7071, -0.7071])
    grip = np.array([-1.0, 30.0, -8.5])
    m.rod(b, (-4.4, 22.5, 0), grip, 2.6, 2.6, 'steel')                                               # левая рука к рукояти
    m.rod(b, (4.4, 22.5, 0), (1.0, 25.0, -2.0), 2.6, 2.6, 'steel')                                   # правая натягивает
    up = np.array([0, 0.7071, 0.7071])                                                                # ось плеч лука
    for s in (-1, 1):
        p1 = grip + up * s * 6.0 + d * 1.6
        p2 = grip + up * s * 11.0 - d * 0.4
        m.rod(b, grip, p1, 0.9, 0.9, 'bow')
        m.rod(b, p1, p2, 0.7, 0.7, 'bow')
        m.rod(b, p2, (1.0, 25.0, -2.0), 0.25, 0.25, 'gold')                                          # тетива
    m.rod(b, (1.0, 25.0, -2.0), grip + d * 4.0, 0.4, 0.4, 'gold')                                    # стрела на тетиве
    idx = {'steel': 0, 'dark': 6, 'gold': 2, 'cloth': 3, 'eye': 4, 'bow': 5}
    boxes = X.mesh_from_model(m, idx)
    M.write_json('fx/meshes/martin_archer_ghost.json', _mesh_doc(
        'T29 «Залп лучников»: призрачный лучник, лук натянут вверх-вперёд (+z), лицом вперёд по +z мэша. Сгенерировано gen_martin_spells.py.',
        boxes, opacity=0.5), compact=True)


def mesh_arrow():
    """Призрачная стрела остриём вниз (−y): древко 1.6 бл., наконечник, оперение. Низ острия — (0,0,0)."""
    r = lambda a, b, t: [round(v, 3) for v in a] + [round(v, 3) for v in b] + [t]
    boxes = [r((-0.04, 0.3, -0.04), (0.04, 1.9, 0.04), 5),
             r((-0.11, 0.08, -0.03), (0.11, 0.32, 0.03), 4), r((-0.03, 0.08, -0.11), (0.03, 0.32, 0.11), 4),
             r((-0.04, 0.0, -0.04), (0.04, 0.1, 0.04), 4),
             r((-0.2, 1.55, -0.015), (0.2, 1.95, 0.015), 2), r((-0.015, 1.55, -0.2), (0.015, 1.95, 0.2), 2)]
    M.write_json('fx/meshes/martin_arrow.json', _mesh_doc('T29 «Залп лучников»: призрачная стрела остриём вниз; низ острия — (0,0,0). '
                                                          'Сгенерировано gen_martin_spells.py.', boxes, opacity=0.8, glow=(2, 4), appear=2),
                 compact=True)


# ================================================================== рисунки
def tex_mark():
    """Метка залпа: кольцо с четырьмя стрелами-шевронами к центру и точкой — куда упадут стрелы."""
    W = 256
    im, d = FX._canvas(W, W)
    S = FX.SS
    c = W * S / 2
    for r, w in ((0.46, 9), (0.36, 3)):
        R = r * W * S
        d.ellipse([c - R, c - R, c + R, c + R], outline=255, width=w * S)
    for k in range(4):
        a = math.pi / 2 * k + math.pi / 4
        p = lambda r, da=0.0: (c + math.cos(a + da) * r * W * S, c + math.sin(a + da) * r * W * S)
        d.polygon([p(0.3, -0.18), p(0.16), p(0.3, 0.18), p(0.25)], fill=255)
    R = 0.05 * W * S
    d.ellipse([c - R, c - R, c + R, c + R], fill=255)
    FX._save(im, 'martin_arrow_mark', W, W, glow=2)


def tex_duel():
    """Кольцо дуэли: двойной обод, по сторонам света — скрещённые мечи, между ними — насечки."""
    W = 512
    im, d = FX._canvas(W, W)
    S = FX.SS
    c = W * S / 2
    for r, w in ((0.48, 12), (0.43, 4)):
        R = r * W * S
        d.ellipse([c - R, c - R, c + R, c + R], outline=255, width=w * S)
    for k in range(4):
        a = math.pi / 2 * k
        cx, cy = c + math.cos(a) * 0.455 * W * S, c + math.sin(a) * 0.455 * W * S
        L = 0.07 * W * S
        for sgn in (-1, 1):
            b = a + sgn * math.pi / 4
            d.line([(cx - math.cos(b) * L, cy - math.sin(b) * L), (cx + math.cos(b) * L, cy + math.sin(b) * L)], fill=255, width=7 * S)
        d.ellipse([cx - 9 * S, cy - 9 * S, cx + 9 * S, cy + 9 * S], fill=255)
    for k in range(64):
        if k % 16 in (15, 0, 1):
            continue
        a = 2 * math.pi * k / 64
        r0, r1 = 0.40 * W * S, 0.425 * W * S
        d.line([(c + math.cos(a) * r0, c + math.sin(a) * r0), (c + math.cos(a) * r1, c + math.sin(a) * r1)], fill=255, width=3 * S)
    FX._save(im, 'martin_duel_ring', W, W, glow=3)


# ================================================================== эффекты
def effects(gaps):
    fx = FX.fx
    # ---------------------------------------------------------------- «Стена щитов»
    fx('martin_shield_wall', 'Особое «Стена щитов» (caster = центр низа стены на краю арены за Мартином, yaw = к игрокам; запуск на событии slam = 1.0 с '
       'анимации martin_shield_wall). 0–20 тиков — стена встаёт из земли (мэш martin_shield_line, %g бл. шириной, группы по 4 щита, просветы '
       '1.6 бл. с центрами x = %s); 20–%d — идёт вперёд на %g бл. (линейно). Код толкает игроков перед стеной: в тике t стена в z = %g·(t−20)/%d, '
       'толчок, если 0 < z_игрока − z < 0.8 и игрок не в просвете; конец — стена рассыпается.' % (WALL_W, gaps, 20 + WALL_T, WALL_PUSH, WALL_PUSH, WALL_T),
       20 + WALL_T + 20, [
           E('mesh', 0, 'caster', model='martin_shield_line', duration=20 + WALL_T + 14, out=ease(14, 'easeInCubic'),
             move={'keys': [[0, [0, -2.4, 0]], [20, [0, 0, 0], 'easeOutCubic'], [20 + WALL_T, [0, 0, WALL_PUSH], 'linear']]}),
           E('sprites', 0, at('caster', 0, 0.2, 0), duration=20 + WALL_T, travel=WALL_PUSH, texture='mote_ash', count=100000, rate=3.0,
             area=WALL_W / 2, speed=0.03, gravity=-0.002, size=[0.6, 1.2], life=26, color=DUST, blend='translucent', comment='пыль у подножия'),
           E('sprites', 0, at('caster', 0, 1.2, 0), duration=20 + WALL_T, travel=WALL_PUSH, texture='mote_wisp', count=100000, rate=1.2,
             area=WALL_W / 2, speed=0.01, gravity=-0.004, size=[0.8, 1.4], life=40, color=GHOST, blend='translucent'),
           E('wave', 18, 'caster', duration=16, shape='ring', radius=WALL_W / 2, thickness=1.2, followTerrain=True, color='@primary'),
       ], style='martin_ghost')
    # ---------------------------------------------------------------- «Залп лучников»
    arch = []
    for k in range(7):
        x = (k - 3) * 1.8
        z = -5.0 - abs(k - 3) * 0.6
        arch.append(E('mesh', 2 * abs(k - 3), at('caster', x, 0, z), model='martin_archer_ghost', duration=66 - 2 * abs(k - 3), out=ease(10),
                      move={'from': [0, -2.2, 0], 'scaleFrom': 1.0, 'delay': 0, 'duration': 14, 'easing': 'easeOutCubic'},
                      comment='лучник %d за спиной Мартина' % (k + 1)))
        arch.append(E('sprites', 24, at('caster', x + 0.1, 2.6, z + 1.0), duration=6, texture='spark_soft', count=4, rate=1, spread=0.1,
                      speed=0.6, gravity=-0.04, size=[0.2, 0.05], life=10, color=GHOST_HOT, comment='стрела ушла вверх (loose)'))
    fx('martin_volley', 'Особое «Залп лучников» (caster = Мартин, yaw — взгляд; запуск на draw = 0.8 с анимации martin_volley): за спиной встают '
       '7 призрачных лучников дугой, на loose (тик 8 от запуска = 1.2 с анимации) стреляют вверх. Метки — martin_volley_mark в точках падения '
       '(запускать на loose).', 70, arch + [mist_el()], style='martin_ghost')
    arrows = [E('decal', 0, 'caster', duration=MARK_T + 20, texture='martin_arrow_mark', radius=1.6, grow=8, glow=0.3, pulse=8,
                color=CRIMSON, fadeOut=14, comment='ПРЕДУПРЕЖДЕНИЕ 1.5 с: сюда упадут стрелы')]
    for k, (dx, dz) in enumerate(((0, 0), (0.6, -0.4), (-0.5, 0.5), (0.3, 0.7), (-0.6, -0.5))):
        t0 = MARK_T - 6 + k
        arrows.append(E('mesh', t0, at('caster', dx, 0, dz), model='martin_arrow', duration=16,
                        move={'keys': [[0, [0, 14, 0]], [6, [0, 0.05, 0], 'easeInQuad']]}, out=ease(6)))
    arrows += [E('flash', MARK_T, at('caster', 0, 0.3, 0), duration=6, size=1.4, color=GHOST_HOT, ring=True),
               E('sprites', MARK_T, at('caster', 0, 0.2, 0), duration=3, texture='mote_ash', count=16, rate=6, area=1.0, speed=0.08,
                 gravity=0.004, size=[0.4, 0.8], life=18, color=DUST, blend='translucent'),
               E('decal', MARK_T, 'caster', duration=30, texture='higher_cracks', radius=1.4, glow=0.2, fadeOut=20, color=GHOST)]
    fx('martin_volley_mark', 'Одна метка залпа (caster = точка на земле; 3–6 меток вокруг игроков). 0–%d тиков — метка горит красным (1.5 с); '
       'с %d по %d падают 5 призрачных стрел; урон — код на %d тике, r1.5.' % (MARK_T, MARK_T - 6, MARK_T + 4, MARK_T), MARK_T + 30, arrows,
       style='martin_ghost')
    # ---------------------------------------------------------------- «Вызов на дуэль»
    fx('martin_duel', 'Особое «Вызов на дуэль» (caster = центр кольца — середина между Мартином и выбранным игроком; запуск на challenge = 0.9 с '
       'анимации martin_duel; %d тиков = 6 с или Fx.stop). Кольцо r%g: герб-кольцо на земле, золото-красная завеса по краю. Внутри урон только '
       'у них двоих (код); чужих кольцо отталкивает — martin_duel_push в точке касания.' % (DUEL_T, DUEL_R), DUEL_T, [
        E('decal', 0, 'caster', duration=DUEL_T, texture='martin_duel_ring', radius=DUEL_R + 0.4, grow=10, glow=0.35, pulse=20, color='@primary',
          fadeOut=14),
        E('wave', 0, 'caster', duration=14, shape='ring', radius=DUEL_R, thickness=1.0, followTerrain=True, color='@secondary'),
        E('curtain', 0, 'caster', duration=DUEL_T, radius=[DUEL_R - 0.1, DUEL_R + 0.1], count=90, height=3.4, grow=12, width=[0.08, 0.18],
          brightness=[0.35, 0.7], texture='beam_fade', flicker=0.3, color='@primary', out=ease(12), comment='стена кольца'),
        E('curtain', 0, 'caster', duration=DUEL_T, radius=[DUEL_R - 0.05, DUEL_R + 0.05], count=40, height=1.6, grow=12, width=[0.1, 0.2],
          brightness=[0.4, 0.7], texture='beam_fade', flicker=0.4, color=CRIMSON, out=ease(12)),
        E('sprites', 0, at('caster', 0, 0.2, 0), duration=DUEL_T, texture='spark_soft', count=100000, rate=0.5, area=DUEL_R, speed=0.01,
          gravity=-0.01, size=[0.14, 0.02], life=30, color='@secondary'),
    ])
    fx('martin_duel_mark', 'Выбранный на дуэль игрок (caster = игрок, follow, %d тиков): золотой ореол и кольцо под ногами.' % DUEL_T, DUEL_T, [
        E('aura', 0, 'caster', follow=True, target='caster', duration=DUEL_T, thickness=0.14, pulse=[0.3, 12], color='@primary', motes=10),
        E('decal', 0, 'caster', follow=True, duration=DUEL_T, texture='martin_duel_ring', radius=1.1, glow=0.3, color=CRIMSON, fadeOut=10),
    ])
    fx('martin_duel_push', 'Чужой игрок толкнут кольцом дуэли (caster = точка касания на кольце, 10 тиков).', 10, [
        E('flash', 0, at('caster', 0, 1.0, 0), duration=8, size=1.4, color='@secondary', ring=True),
        E('wave', 0, at('caster', 0, 1.0, 0), duration=10, shape='sphere', radius=1.2, rim=0.8, color='@primary'),
    ])
    # ---------------------------------------------------------------- «Боевой клич»
    fx('martin_warcry', 'Особое «Боевой клич» (caster = Мартин; запуск на cry = 0.6 с анимации martin_warcry). Три звуковых кольца до r%g, '
       'сфера-волна, короткая красная засветка; касты в r%g прерываются (код, на каждом — martin_warcry_interrupt), солдатам — martin_warcry_buff.'
       % (CRY_R, CRY_R), 40, [
        E('flash', 0, at('caster', 0, 4.6, -0.4), duration=10, size=3.0, rays=12, color=CRIMSON, screen=0.12, ring=True),
        E('wave', 0, at('caster', 0, 4.0, 0), duration=16, shape='sphere', radius=CRY_R, rim=0.6, color='@primary'),
        *[E('wave', 4 * k, 'caster', duration=18, shape='ring', radius=CRY_R, thickness=1.0 + 0.4 * k, followTerrain=True,
            texture='sound_ring', color=CRIMSON if k == 1 else '@primary') for k in range(3)],
        E('tint', 0, 'caster', duration=30, radius=CRY_R + 4, color='#5A0A10', strength=0.25, **{'in': ease(3), 'out': ease(20)}),
        E('sprites', 0, at('caster', 0, 0.2, 0), duration=4, texture='mote_ash', count=40, rate=10, area=3, speed=0.16, gravity=-0.002,
          size=[0.6, 1.2], life=24, color=DUST, blend='translucent'),
    ])
    fx('martin_warcry_interrupt', 'Каст игрока сорван кличем (caster = игрок): заклинание лопается в руке красными осколками.', 14, [
        E('flash', 0, 'caster.hand', duration=8, size=1.0, color=CRIMSON),
        E('sprites', 0, 'caster.hand', duration=3, texture='spark_soft', count=14, rate=6, spread=0.3, speed=0.14, gravity=0.02,
          size=[0.14, 0.02], life=12, color=CRIMSON),
    ])
    fx('martin_warcry_buff', 'Солдат под кличем (caster = солдат, follow, %d тиков = 6 с): кроваво-золотой ореол.' % CRY_BUFF, CRY_BUFF, [
        E('aura', 0, 'caster', follow=True, target='caster', duration=CRY_BUFF, thickness=0.14, pulse=[0.35, 8], color=CRIMSON, motes=10,
          ring=False, out=ease(14)),
    ])


def mist_el():
    return E('sprites', 0, at('caster', 0, 0.2, -6), duration=60, texture='mote_wisp', count=100000, rate=1.0, area=6.0, speed=0.01,
             gravity=-0.004, size=[0.9, 1.6], life=50, color=GHOST, blend='translucent', comment='туман, из которого встают лучники')


# ================================================================== иконки, lang, звуки
def icons():
    out_ = {}

    def wall(d, S):
        for k, x in enumerate((0.22, 0.42, 0.62)):
            d.rectangle([S * x, S * 0.3, S * (x + 0.16), S * 0.74], fill=hx('#8fd8f0'), outline=hx('#120c0e'), width=int(S * 0.03))
        d.polygon([(S * 0.82, S * 0.4), (S * 0.92, S * 0.52), (S * 0.82, S * 0.64)], fill=hx('#d8f6ff'))
    out_['status_shield_wall'] = FX._icon('status_shield_wall', wall, rim='#8fd8f0')

    def volley(d, S):
        for x in (0.3, 0.5, 0.7):
            d.line([(S * x, S * 0.2), (S * x, S * 0.7)], fill=hx('#d8f6ff'), width=int(S * 0.05))
            d.polygon([(S * (x - 0.07), S * 0.62), (S * (x + 0.07), S * 0.62), (S * x, S * 0.8)], fill=hx('#8fd8f0'))
    out_['status_volley'] = FX._icon('status_volley', volley, rim='#8fd8f0')

    def duel(d, S):
        for sgn in (-1, 1):
            d.line([(S * (0.5 - 0.28 * sgn), S * 0.22), (S * (0.5 + 0.28 * sgn), S * 0.78)], fill=hx('#f6d88a'), width=int(S * 0.08))
        d.ellipse([S * 0.18, S * 0.18, S * 0.82, S * 0.82], outline=hx('#c22a2c'), width=int(S * 0.05))
    out_['status_duel'] = FX._icon('status_duel', duel, rim='#e5b95a')

    def cry(d, S):
        for k, r in enumerate((0.16, 0.28, 0.4)):
            d.arc([S * (0.5 - r), S * (0.5 - r), S * (0.5 + r), S * (0.5 + r)], -60, 60, fill=hx('#c22a2c' if k == 1 else '#f6d88a'), width=int(S * 0.06))
        d.ellipse([S * 0.18, S * 0.4, S * 0.38, S * 0.6], fill=hx('#f6d88a'))
    out_['status_warcry'] = FX._icon('status_warcry', cry, rim='#c22a2c')
    return out_


LANG = {
    'ui.pohsmp_core.martin.shield_wall': ('«Стена щитов!» — ищите просветы в строю', '"Shield Wall!" — find the gaps in the line'),
    'ui.pohsmp_core.martin.volley': ('«Лучники — залп!»', '"Archers — loose!"'),
    'ui.pohsmp_core.martin.volley_warn': ('Стрелы! Уйдите с красных меток', 'Arrows! Get off the red marks'),
    'ui.pohsmp_core.martin.duel': ('Мартин вызывает %s на дуэль!', 'Martin challenges %s to a duel!'),
    'ui.pohsmp_core.martin.duel_blocked': ('Не вмешивайтесь в дуэль', 'Do not interfere in the duel'),
    'ui.pohsmp_core.martin.duel_end': ('Дуэль окончена', 'The duel is over'),
    'ui.pohsmp_core.martin.warcry': ('«Боевой клич!» — заклинания сорваны', '"War Cry!" — spells are interrupted'),
    'ui.pohsmp_core.martin.warcry_interrupt': ('Клич Мартина сорвал ваше заклинание', 'Martin\'s war cry broke your spell'),
    'ui.pohsmp_core.martin.status.shield_wall': ('Стена щитов', 'Shield Wall'),
    'ui.pohsmp_core.martin.status.volley': ('Залп лучников', 'Archer Volley'),
    'ui.pohsmp_core.martin.status.duel': ('Дуэль', 'Duel'),
    'ui.pohsmp_core.martin.status.warcry': ('Боевой клич', 'War Cry'),
    'subtitles.pohsmp_core.martin.shield_wall': ('Стена щитов надвигается', 'Shield wall advances'),
    'subtitles.pohsmp_core.martin.volley': ('Призрачные луки звенят', 'Phantom bows twang'),
    'subtitles.pohsmp_core.martin.arrow_hit': ('Стрелы вонзаются в землю', 'Arrows strike the ground'),
    'subtitles.pohsmp_core.martin.duel': ('Брошен вызов на дуэль', 'A duel is declared'),
    'subtitles.pohsmp_core.martin.warcry': ('Боевой клич Мартина', 'Martin\'s war cry'),
}
S_ = FX.S_
SOUNDS = {
    'martin.shield_wall': [S_('minecraft:random/anvil_land', pitch=0.5, volume=1.2), S_('minecraft:item/shield/block5', pitch=0.6, volume=1.4)],
    'martin.volley': [S_('minecraft:random/bow', pitch=0.7, volume=1.4)],
    'martin.arrow_hit': [S_('minecraft:random/bowhit%d' % k, pitch=0.8) for k in (1, 2, 3, 4)],
    'martin.duel': [S_('minecraft:random/anvil_use', pitch=0.7, volume=1.2)],
    'martin.warcry': [S_('minecraft:mob/ravager/roar%d' % k, pitch=0.6, volume=2.0) for k in (1, 2, 3)],
}


def lang_sounds():
    for i, name in enumerate(('ru_ru', 'en_us')):
        p = os.path.join(M.A, 'lang', name + '.json')
        d = json.load(open(p, encoding='utf-8'))
        for k, v in LANG.items():
            d[k] = v[i]
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')
    p = os.path.join(M.A, 'sounds.json')
    d = json.load(open(p, encoding='utf-8'))
    for k, v in SOUNDS.items():
        d[k] = {'subtitle': 'subtitles.pohsmp_core.' + k, 'sounds': v}
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write('\n')


# ================================================================== кадр
def shot():
    import martin_render as R
    three = os.environ.get('MARTIN_THREE') or None
    wall = [dict(mesh='martin_shield_line', pos=[0, 0, -7], ry=180)]
    archers = [dict(mesh='martin_archer_ghost', pos=[(k - 3) * 1.8, 0, 5.0 + abs(k - 3) * 0.6], ry=180) for k in range(7)]
    marks = [dict(tex='martin_arrow_mark', pos=[x, 0.04, z], r=1.6, color='#c22a2c', opacity=0.9) for x, z in ((-4, -5), (2, -7), (5, -4))]
    arrows = [dict(mesh='martin_arrow', pos=[2 + dx, 2 + dy, -7 + dz]) for dx, dy, dz in ((0, 0, 0), (0.6, 2.0, -0.4), (-0.5, 4, 0.5))]
    R.sheet(os.path.join(FX.MEDIA, 't29_spells4.jpg'), {'cols': 4, 'cells': [
        dict(model='martin', anim='martin_shield_wall', t=1.1, yaw=-150, pitch=30, dist=5.0, ty=24, label='«Стена щитов»',
             sub='щит в землю (slam) — стена с просветами идёт на игроков', meshes=wall),
        dict(model='martin', anim='martin_volley', t=1.25, yaw=-25, pitch=38, dist=5.4, ty=24, label='«Залп лучников»',
             sub='лучники за спиной, метки 1.5 с, стрелы', meshes=archers + arrows, decals=marks),
        dict(model='martin', anim='martin_duel', t=1.1, yaw=-40, pitch=30, dist=3.6, ty=30, label='«Вызов на дуэль»',
             sub='кольцо r6: внутри — только двое', decals=[dict(tex='martin_duel_ring', pos=[0, 0.04, -3], r=6.4, color='#e8b95a', opacity=0.9)]),
        dict(model='martin', anim='martin_warcry', t=0.8, yaw=-20, pitch=12, dist=2.8, ty=36, label='«Боевой клич»',
             sub='рёв: касты в r12 сорваны, солдаты сильнее',
             decals=[dict(tex='martin_banner_ring', pos=[0, 0.04, 0], r=6, color='#c22a2c', opacity=0.8)])]}, three, (1800, 700))


def run(mod, args=()):
    global M
    M = mod
    FX.M = mod
    X.M = mod
    gaps = mesh_shield_line()
    mesh_archer()
    mesh_arrow()
    tex_mark()
    tex_duel()
    effects(gaps)
    icons()
    lang_sounds()
    if '--shots' in args:
        shot()
    print('+4 заклинания: готово; просветы стены x =', gaps)


if __name__ == '__main__':
    import gen_martin
    run(gen_martin, sys.argv[1:])
