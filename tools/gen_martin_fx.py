#!/usr/bin/env python3
"""
T29 «Мартин» — эффекты (fx/*.json, стили, мэши барьера и полос), рисунки (textures/sigil), полоса здоровья по 3 фазам, титры,
иконки статусов, lang ru/en, звуки, проверочные кадры docs/media/t29_*. Вызывается из tools/gen_martin.py (run(M, args)).
Время — тики, углы — градусы, размеры — блоки. Формат fx — docs/fx.md.
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
MEDIA = os.path.join(ROOT, 'docs', 'media')
M = None

GOLD, GOLD_HOT, GOLD_DEEP = '#E8B95A', '#FFF1C4', '#9A6A26'
SILVER, CRIMSON, CRIMSON_D = '#C4C6CB', '#C22A2C', '#4C0C14'
GHOST, GHOST_HOT, GHOST_D = '#8FD8F0', '#D8F6FF', '#1C3A4A'
DUST = '#8A8070'

T_INTRO = 130          # ролик появления = анимация martin_spawn (6.5 с)
LANE_L, LANE_W = 40.0, 3.0
T_WARN = 40            # предупреждение конницы 2 с
T_RIDE = 22            # проход всадников по полосе
T_HOLD = 200           # «Приказ стоять насмерть» 10 с


def E(type_, delay=0, at='caster', **kw):
    o = {'type': type_, 'delay': delay, 'at': at}
    o.update(kw)
    return o


def ease(d, e='easeOutCubic'):
    return {'duration': d, 'easing': e}


def at(base, x=0.0, y=0.0, z=0.0):
    f = lambda v: str(int(v)) if float(v) == int(v) else str(round(v, 2))
    return '%s+%s,%s,%s' % (base, f(x), f(y), f(z))


def write(rel, obj):
    M.write_json(rel, obj)


def fx(id_, comment, dur, els, style='martin'):
    write('fx/%s.json' % id_, {'comment': comment, 'style': style, 'duration': dur, 'elements': els})


def hx(h, a=255):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)


# ================================================================== рисунки (белое на прозрачном → textures/sigil/)
SS = 4


def _canvas(w, h):
    im = Image.new('L', (w * SS, h * SS), 0)
    return im, ImageDraw.Draw(im)


def _save(mask, name, w, h, glow=0):
    m = mask.resize((w, h), Image.LANCZOS)
    if glow:
        g = m.filter(ImageFilter.GaussianBlur(glow))
        m = Image.fromarray(np.maximum(np.asarray(m), (np.asarray(g) * 0.6).astype(np.uint8)))
    img = Image.new('RGBA', (w, h), (255, 255, 255, 0))
    img.putalpha(m)
    img.save(M.out('textures/sigil/%s.png' % name))
    return img


def _crown_sword(d, cx, cy, s, fill=255):
    """Герб Мартина: корона над мечом остриём вниз (как на щите, табарде и знамени)."""
    k = s / 100
    # корона
    d.rectangle([cx - 44 * k, cy - 70 * k, cx + 44 * k, cy - 56 * k], fill=fill)
    for i, x in enumerate((-44, -22, 0, 22, 44)):
        h = 30 if i % 2 == 0 else 20
        d.polygon([(cx + (x - 9) * k, cy - 70 * k), (cx + (x + 9) * k, cy - 70 * k), (cx + x * k, cy - (70 + h) * k)], fill=fill)
    # меч
    d.rectangle([cx - 52 * k, cy - 44 * k, cx + 52 * k, cy - 34 * k], fill=fill)          # гарда
    d.rectangle([cx - 6 * k, cy - 54 * k, cx + 6 * k, cy - 44 * k], fill=fill)            # рукоять
    d.polygon([(cx - 11 * k, cy - 34 * k), (cx + 11 * k, cy - 34 * k), (cx + 11 * k, cy + 70 * k), (cx, cy + 92 * k),
               (cx - 11 * k, cy + 70 * k)], fill=fill)
    d.rectangle([cx - 2 * k, cy - 30 * k, cx + 2 * k, cy + 66 * k], fill=0)                # дол


def tex_emblem():
    W = 512
    im, d = _canvas(W, W)
    c = W * SS / 2
    for r, w in ((0.47, 0.018), (0.42, 0.008)):
        R = r * W * SS
        d.ellipse([c - R, c - R, c + R, c + R], outline=255, width=int(w * W * SS))
    for k in range(12):                                        # 12 щитов строя по кругу
        a = 2 * math.pi * k / 12
        x, y = c + math.cos(a) * 0.445 * W * SS, c + math.sin(a) * 0.445 * W * SS
        s = 0.035 * W * SS
        d.polygon([(x - s, y - s * 1.2), (x + s, y - s * 1.2), (x + s, y + s * 0.4), (x, y + s * 1.5), (x - s, y + s * 0.4)], fill=255)
    for k in range(48):                                        # насечки
        a = 2 * math.pi * (k + 0.5) / 48
        r0, r1 = 0.36 * W * SS, 0.40 * W * SS
        d.line([(c + math.cos(a) * r0, c + math.sin(a) * r0), (c + math.cos(a) * r1, c + math.sin(a) * r1)], fill=255, width=SS * 3)
    _crown_sword(d, c, c + 0.02 * W * SS, 0.15 * W * SS)
    _save(im, 'martin_emblem', W, W, glow=3)


def tex_lane():
    """Полоса конницы (для quad на земле: верх картинки — дальний конец): кромки и шевроны «вперёд»."""
    w, h = 128, 1024
    im, d = _canvas(w, h)
    W, H = w * SS, h * SS
    for x in (4, w - 10):
        d.rectangle([x * SS, 0, (x + 6) * SS, H], fill=255)
    for k in range(10):
        y = (k + 0.5) * H / 10
        d.polygon([(W * 0.18, y + 22 * SS), (W * 0.5, y - 20 * SS), (W * 0.82, y + 22 * SS), (W * 0.82, y + 40 * SS),
                   (W * 0.5, y - 2 * SS), (W * 0.18, y + 40 * SS)], fill=200)
    a = np.asarray(im, np.float32)
    a *= np.linspace(1.0, 0.75, a.shape[0])[:, None]                      # к ближнему концу (низ) — чуть слабее
    _save(Image.fromarray(a.astype(np.uint8)), 'martin_lane', w, h, glow=2)


def tex_barrier():
    """Щит-барьер «Приказа стоять насмерть»: чешуя из башенных щитов, яркие края, к верху гаснет."""
    w, h = 256, 256
    im, d = _canvas(w, h)
    W, H = w * SS, h * SS
    cw, ch = 64 * SS, 86 * SS
    for row in range(-1, 8):
        for col in range(-1, 9):
            x = col * cw + (cw / 2 if row % 2 else 0)
            y = row * ch * 0.82
            pts = [(x + 3 * SS, y + 3 * SS), (x + cw - 3 * SS, y + 3 * SS), (x + cw - 3 * SS, y + ch * 0.6), (x + cw / 2, y + ch - 2 * SS),
                   (x + 3 * SS, y + ch * 0.6)]
            d.polygon(pts, outline=255, width=3 * SS)
            d.polygon([(px + (x + cw / 2 - px) * 0.35, py + (y + ch / 2 - py) * 0.35) for px, py in pts], fill=70)
    a = np.asarray(im, np.float32)
    a *= np.clip(1.15 - np.linspace(0, 1, a.shape[0])[:, None] ** 1.5 * 0.0 - (1 - np.linspace(1, 0, a.shape[0])[:, None]) * 0.55, 0, 1)
    a[:6 * SS] = 0
    a[-4 * SS:] = 255
    _save(Image.fromarray(a.astype(np.uint8)), 'martin_barrier', w, h, glow=2)


def tex_ring():
    """Кольцо знамени: двойной обод, лучи-копья внутрь (аура «усиление знамени» на земле)."""
    W = 512
    im, d = _canvas(W, W)
    c = W * SS / 2
    for r, w in ((0.48, 10), (0.44, 4)):
        R = r * W * SS
        d.ellipse([c - R, c - R, c + R, c + R], outline=255, width=w * SS)
    for k in range(16):
        a = 2 * math.pi * k / 16
        r0, r1 = 0.30 * W * SS, 0.43 * W * SS
        p = lambda r, da=0.0: (c + math.cos(a + da) * r, c + math.sin(a + da) * r)
        d.polygon([p(r1, -0.03), p(r1, 0.03), p(r0)], fill=255)
    _save(im, 'martin_banner_ring', W, W, glow=3)


def textures():
    tex_emblem()
    tex_lane()
    tex_barrier()
    tex_ring()


# ================================================================== мэши (quad): полоса конницы, щит-барьер
def meshes():
    hw = LANE_W / 2
    write('fx/meshes/martin_lane_warn.json', {
        'comment': 'T29: полоса атаки конницы на земле: от точки at вперёд по yaw на %g бл., ширина %g бл. Сгенерировано gen_martin_fx.py.' % (LANE_L, LANE_W),
        'style': 'martin_ghost', 'center': 0, 'formedAt': 4, 'collapse': {'duration': 8, 'easing': 'easeInCubic'},
        'parts': [{'type': 'quad', 'texture': 'martin_lane', 'blend': 'additive', 'opacity': 0.9, 'doubleSided': True, 'color': '@primary',
                   'pulse': [0.45, 10], 'corners': [[-hw, 0.06, LANE_L], [hw, 0.06, LANE_L], [hw, 0.06, 0], [-hw, 0.06, 0]]}]})
    # барьер: дуга 120° радиуса 2.4 перед носителем, высота 4.4 (под рост Мартина ×2), 6 плоскостей
    parts = []
    n, R, H = 6, 2.4, 4.4
    for k in range(n):
        a0 = math.radians(-60 + 120 * k / n)
        a1 = math.radians(-60 + 120 * (k + 1) / n)
        p0 = [round(math.sin(a0) * R, 3), round(math.cos(a0) * R, 3)]
        p1 = [round(math.sin(a1) * R, 3), round(math.cos(a1) * R, 3)]
        parts.append({'type': 'quad', 'texture': 'martin_barrier', 'blend': 'additive', 'opacity': 0.5, 'doubleSided': True,
                      'color': '@secondary', 'pulse': [0.25, 14],
                      'corners': [[p0[0], H, p0[1]], [p1[0], H, p1[1]], [p1[0], 0.0, p1[1]], [p0[0], 0.0, p0[1]]]})
    write('fx/meshes/martin_shield_wall.json', {
        'comment': 'T29 «Приказ стоять насмерть»: щит-барьер дугой 120° (r %g, высота %g) перед носителем (по yaw), follow. '
                   'Масштаб элемента: 1 — Мартин, 0.5 — солдат. Сгенерировано gen_martin_fx.py.' % (R, H),
        'style': 'martin', 'center': 0, 'formedAt': 10, 'collapse': {'duration': 12, 'easing': 'easeInCubic'}, 'parts': parts})


# ================================================================== эффекты
def effects():
    write('fx/styles/martin.json', {
        'comment': 'T29 Мартин, Последний Полководец: золото герба и серебро лат, кровавый табард; движение тяжёлое, с ударами.',
        'palette': {'primary': GOLD, 'secondary': GOLD_HOT, 'core': '#FFFFFF', 'shadow': CRIMSON_D},
        'textures': {'sparks': 'spark_soft', 'runes': 'school_holy_band', 'shards': 'spark_soft', 'sigil': 'martin_emblem'},
        'blend': 'additive', 'motion': {'rotationScale': 0.6, 'jitter': 0.1, 'easing': 'easeOutCubic', 'pulse': {'amp': 0.12, 'period': 12}}})
    write('fx/styles/martin_ghost.json', {
        'comment': 'T29 призрачное войско Мартина: холодный лунный свет, туман; движение плавное, мерное.',
        'palette': {'primary': GHOST, 'secondary': GHOST_HOT, 'core': '#FFFFFF', 'shadow': GHOST_D},
        'textures': {'sparks': 'spark_soft', 'runes': 'school_holy_band', 'shards': 'mote_wisp', 'sigil': 'martin_emblem'},
        'blend': 'additive', 'motion': {'rotationScale': 0.5, 'jitter': 0.0, 'easing': 'easeInOutSine', 'pulse': {'amp': 0.15, 'period': 20}}})

    mist = lambda d, t, a='caster', area=6.0, rate=0.6: E('sprites', d, at(a, 0, 0.2, 0), duration=t, texture='mote_wisp', count=100000, rate=rate,
                                                       area=area, speed=0.01, gravity=-0.004, size=[0.9, 1.6], life=60, color=GHOST,
                                                       blend='translucent', comment='стелющийся призрачный туман')
    # ---------------------------------------------------------------- появление (6.5 с = martin_spawn)
    fx('martin_intro', 'Ролик появления (6.5 с = 130 тиков = анимация martin_spawn). caster = Мартин (стоит на колене, меч воткнут перед ним), '
       'yaw — его взгляд. 0–1 с туман и тьма, 0.5 с герб под ним, 1.0 с (look) — блик в щели забрала, луч света сверху; '
       '1–2.6 с за его спиной из тумана встают ряды призрачных солдат (мэш) и опускаются; 2.6 (rise) — волна; 4.0 (pull) — меч из земли: '
       'искры и трещины; 5.0 (salute) — вспышка на клинке, золотое кольцо; 5.4 с — титр; 6.5 с — полоса (код).', T_INTRO, [
        E('tint', 0, 'caster', duration=T_INTRO, radius=48, color='#10141C', strength=0.35, **{'in': ease(20), 'out': ease(30, 'easeInSine')}),
        mist(0, 110, area=9.0, rate=1.2),
        E('decal', 10, 'caster', duration=T_INTRO - 10, texture='martin_emblem', radius=5.5, grow=30, glow=0.35, fadeOut=30, color='@primary',
          comment='герб под Мартином'),
        E('column', 16, 'caster', duration=70, radius=1.6, height=18, fill=0.25, color='@secondary', out=ease(20, 'easeInSine'),
          comment='луч света сверху на коленопреклонённого'),
        E('flash', 20, at('caster', 0, 4.6, -0.5), duration=10, size=0.8, color=GHOST_HOT, anamorphic=1.8, comment='блик в щели забрала (look)'),
        *[E('mesh', 22 + 4 * r, at('caster', (c - 2) * 2.2, 0, -4.5 - 2.6 * r), model='martin_soldier_ghost', yaw=0, duration=58 - 4 * r,
            move={'from': [0, -2.4, 0], 'scaleFrom': 1.0, 'delay': 0, 'duration': 22, 'easing': 'easeOutCubic'},
            comment='ряд %d, место %d: призрачный солдат встаёт из тумана за спиной' % (r + 1, c + 1))
          for r in range(2) for c in range(5)],
        E('wave', 52, 'caster', duration=24, shape='ring', radius=10, thickness=1.6, followTerrain=True, color='@primary', comment='rise'),
        E('decal', 80, at('caster', 0, 0, 2.8), texture='higher_cracks', radius=2.2, glow=0.4, fadeOut=40, color='@primary',
          comment='pull: меч выходит из земли'),
        E('sprites', 80, at('caster', 0, 0.3, 2.8), duration=6, texture='spark_soft', count=40, rate=8, spread=0.6, speed=0.22, gravity=0.02,
          size=[0.18, 0.03], life=16, color='@secondary'),
        E('sprites', 80, at('caster', 0, 0.3, 2.8), duration=8, texture='mote_ash', count=24, rate=4, spread=0.8, speed=0.06, gravity=-0.004,
          size=[0.5, 0.9], life=30, color=DUST, blend='translucent'),
        E('flash', 100, at('caster', 0, 6.0, 1.2), duration=14, size=2.6, rays=8, color='@secondary', ring=True, comment='salute: клинок у лица'),
        E('wave', 100, 'caster', duration=26, shape='ring', radius=14, thickness=2.0, followTerrain=True, color='@primary'),
        E('aura', 100, 'caster', duration=30, target='caster', thickness=0.18, pulse=[0.3, 10], color='@primary', motes=20, out=ease(16)),
    ], style='martin')

    # ---------------------------------------------------------------- фаза 1: «Строй»
    fx('martin_formation', 'Фаза 1 «Строй» (caster = Мартин, follow, до Fx.stop): герб строя на земле r4, призрачные искры от щитов. '
       'Пока строй стоит, урон по Мартину через строй слабее (код).', -1, [
        E('decal', 0, 'caster', follow=True, texture='martin_emblem', radius=4.2, glow=0.25, pulse=40, color='@primary', grow=16, brightness=0.7),
        E('sprites', 0, at('caster', 0, 0.3, 0), follow=True, texture='spark_soft', count=100000, rate=0.15, area=4.0, speed=0.01, gravity=-0.01,
          size=[0.14, 0.02], life=40, color=GHOST),
    ], style='martin_ghost')
    fx('martin_soldier_spawn', 'Призрачный солдат встаёт (caster = точка, 30 тиков): холодный круг, туман столбом, вспышка. '
       'Сущность ставить на 4 тике и играть martin_soldier_spawn (1.2 с, модель идёт из-под земли).', 30, [
        E('decal', 0, 'caster', duration=30, texture='martin_banner_ring', radius=1.2, grow=6, glow=0.4, fadeOut=14, color='@primary'),
        E('column', 0, 'caster', duration=24, radius=0.6, height=3.2, fill=0.35, color='@primary', out=ease(10)),
        E('sprites', 0, at('caster', 0, 0.2, 0), duration=16, texture='mote_wisp', count=26, rate=2.0, area=0.9, speed=0.03, gravity=-0.01,
          size=[0.6, 1.1], life=30, color=GHOST, blend='translucent'),
        E('flash', 4, at('caster', 0, 1.0, 0), duration=8, size=1.3, color='@secondary'),
    ], style='martin_ghost')
    fx('martin_soldier_aura', 'Призрачный солдат: туман у ног и мерцание (caster = солдат, follow, до Fx.stop).', -1, [
        E('sprites', 0, at('caster', 0, 0.1, 0), follow=True, texture='mote_wisp', count=100000, rate=0.12, area=0.5, speed=0.005,
          gravity=-0.003, size=[0.5, 0.9], life=40, color=GHOST, blend='translucent'),
    ], style='martin_ghost')
    fx('martin_soldier_vanish', 'Солдат рассеивается (caster = солдат; 20 тиков, вместе с анимацией martin_soldier_vanish 0.8 с).', 20, [
        E('sprites', 0, at('caster', 0, 1.0, 0), duration=10, texture='mote_wisp', count=30, rate=4, spread=0.6, speed=0.04, gravity=-0.012,
          size=[0.6, 1.2], life=24, color=GHOST, blend='translucent'),
        E('sprites', 0, at('caster', 0, 1.0, 0), duration=6, texture='spark_soft', count=20, rate=5, spread=0.5, speed=0.1, gravity=-0.01,
          size=[0.12, 0.02], life=16, color='@secondary'),
    ], style='martin_ghost')
    fx('martin_formation_block', 'Удар по Мартину пришёлся через строй: щит солдата гасит часть урона (caster = точка удара на щите / солдат, 8 тиков).', 8, [
        E('flash', 0, 'caster', duration=6, size=0.9, color='@secondary', ring=True),
        E('sprites', 0, 'caster', duration=2, texture='spark_soft', count=12, rate=6, spread=0.3, speed=0.16, gravity=0.02, size=[0.12, 0.02],
          life=10, color='@primary'),
    ], style='martin_ghost')
    fx('martin_command', 'Жест «в атаку!» (событие command анимации martin_command; caster = Мартин): вспышка на клинке, золотая волна к солдатам.', 30, [
        E('flash', 0, at('caster', 0.6, 5.6, 1.6), duration=12, size=1.8, rays=6, color='@secondary'),
        E('wave', 0, 'caster', duration=22, shape='ring', radius=12, thickness=1.2, followTerrain=True, color='@primary'),
    ])

    # ---------------------------------------------------------------- фаза 2: «Знамя»
    fx('martin_banner_plant', 'Знамя вонзено (caster = основание знамени; событие plant у Мартина = 1.3 с martin_banner_plant). Сущность знамени — '
       'на 0 тике (анимация martin_banner_plant). Удар в землю: вспышка, волна r10, пыль, трещины.', 40, [
        E('flash', 0, at('caster', 0, 1.2, 0), duration=12, size=2.4, rays=8, color='@secondary', screen=0.06, ring=True),
        E('wave', 0, 'caster', duration=22, shape='ring', radius=10, thickness=1.6, followTerrain=True, color='@primary'),
        E('decal', 0, 'caster', texture='higher_cracks', radius=2.4, glow=0.4, fadeOut=30, duration=40, color='@primary'),
        E('sprites', 0, at('caster', 0, 0.2, 0), duration=6, texture='mote_ash', count=40, rate=8, area=1.4, speed=0.08, gravity=-0.002,
          size=[0.5, 1.0], life=34, color=DUST, blend='translucent'),
    ])
    fx('martin_banner_aura', 'Знамя стоит (caster = знамя, follow, до Fx.stop): золотое кольцо r8 на земле пульсирует, вверх летят искры; '
       'солдаты в r8 сильнее (код) и получают martin_banner_buff.', -1, [
        E('decal', 0, 'caster', follow=True, texture='martin_banner_ring', radius=8, glow=0.25, pulse=30, grow=16, color='@primary', brightness=0.8),
        E('curtain', 0, 'caster', radius=[7.8, 8.0], count=48, height=1.2, grow=16, width=[0.06, 0.12], brightness=[0.3, 0.55],
          texture='beam_fade', flicker=0.3, color='@primary'),
        E('sprites', 0, at('caster', 0, 0.2, 0), follow=True, texture='spark_soft', count=100000, rate=0.4, area=8, speed=0.02, gravity=-0.012,
          size=[0.14, 0.02], life=40, color='@secondary'),
        E('sprites', 0, at('caster', 0, 3.3, 0), follow=True, texture='spark_soft', count=100000, rate=0.3, spread=0.4, speed=0.01, gravity=-0.008,
          size=[0.2, 0.03], life=30, color='@secondary', glow=0.6, comment='блики у навершия'),
    ])
    fx('martin_banner_buff', 'Солдат усилен знаменем (caster = солдат, follow, до Fx.stop): золотой ореол поверх призрачного.', -1, [
        E('aura', 0, 'caster', follow=True, target='caster', thickness=0.12, pulse=[0.3, 16], color='@primary', motes=8, ring=False),
    ])
    fx('martin_banner_hit', 'Удар по знамени (caster = точка удара, 6 тиков): щепки и искры; анимация martin_banner_hit.', 6, [
        E('sprites', 0, 'caster', duration=2, texture='mote_ash', count=8, rate=4, spread=0.25, speed=0.14, gravity=0.04, size=[0.2, 0.1],
          life=14, color='#6A4A30', blend='translucent'),
        E('flash', 0, 'caster', duration=4, size=0.6, color='@primary'),
    ])
    fx('martin_banner_cut', 'Знамя срублено (caster = основание; 40 тиков, анимация martin_banner_cut): треск, щепки, золото гаснет, кольцо '
       'сходится к древку. На 0 — Fx.stop martin_banner_aura и всех martin_banner_buff; сущность убрать через 2 с.', 40, [
        E('flash', 0, at('caster', 0, 1.25, 0), duration=10, size=1.8, color='@secondary', ring=True),
        E('sprites', 0, at('caster', 0, 1.25, 0), duration=4, texture='mote_ash', count=30, rate=8, spread=0.4, speed=0.2, gravity=0.04,
          size=[0.25, 0.1], life=22, color='#6A4A30', blend='translucent', comment='щепки'),
        E('wave', 0, 'caster', duration=18, shape='ring', radius=8, thickness=1.0, followTerrain=True, color='@primary', reverse=True),
        E('sprites', 10, at('caster', 0, 2.5, 0), duration=30, texture='spark_soft', count=100000, rate=0.8, spread=1.2, speed=0.01,
          gravity=0.01, size=[0.14, 0.02], life=20, color='@primary', comment='золото гаснет, осыпается'),
    ])

    # ---------------------------------------------------------------- особое: «Атака конницы»
    fx('martin_cavalry_cast', 'Особое «Атака конницы» (caster = Мартин; анимация martin_cavalry 3.4 с: call 1.0, charge 2.0). Меч к небу: '
       'столб света, небо мрачнеет, вдали — туман. Полосы — martin_cavalry_lane (запускать на 1.0 с, call).', 68, [
        E('tint', 0, 'caster', duration=68, radius=48, color='#101820', strength=0.3, **{'in': ease(16), 'out': ease(24)}),
        E('beam', 14, at('caster', 0.6, 6.4, 0.2), fromSky=24, width=0.5, core=0.4, duration=26, color='@secondary', out=ease(8),
          comment='свет с неба на поднятый клинок'),
        E('flash', 20, at('caster', 0.6, 6.6, 0.2), duration=14, size=2.6, rays=10, color=GHOST_HOT, screen=0.08, comment='call'),
        E('wave', 20, 'caster', duration=30, shape='ring', radius=26, thickness=2.4, followTerrain=True, color=GHOST),
        E('flash', 40, at('caster', 0, 4.4, 2.2), duration=10, size=2.0, color='@primary', anamorphic=3, comment='charge: взмах вперёд'),
    ])
    lane = [E('mesh', 0, 'caster', model='martin_lane_warn', duration=T_WARN + T_RIDE, out=ease(8),
              comment='предупреждение: светится полоса %g×%g бл.' % (LANE_L, LANE_W)),
            E('sprites', 0, at('caster', 0, 0.2, 2), duration=T_WARN, texture='mote_wisp', count=100000, rate=0.5, spread=1.0, speed=0.02,
              gravity=-0.004, size=[1.0, 1.8], life=40, color=GHOST, blend='translucent', comment='туман у начала полосы: оттуда выйдут всадники')]
    for k, dx in enumerate((-0.8, 0.9, 0.0)):
        z0 = -4.0 - 3.2 * k
        lane.append(E('mesh', T_WARN + 2 * k, 'caster', model='martin_cavalry_rider', duration=T_RIDE + 6,
                      move={'keys': [[0, [dx, 0, z0]], [T_RIDE + 6, [dx, 0, z0 + LANE_L + 12], 'linear']]},
                      comment='всадник %d несётся по полосе' % (k + 1)))
        lane.append(E('sprites', T_WARN + 2 * k, at('caster', dx, 0.3, z0), duration=T_RIDE + 4, travel=LANE_L + 12, texture='mote_ash',
                      count=100000, rate=3, spread=0.8, speed=0.03, gravity=-0.002, size=[0.6, 1.2], life=24, color=DUST, blend='translucent',
                      comment='пыль из-под копыт'))
    lane.append(E('flash', T_WARN, at('caster', 0, 1.2, 0), duration=8, size=2.0, color='@secondary'))
    fx('martin_cavalry_lane', 'Одна полоса конницы: caster = начало полосы на земле (край арены), yaw = направление полосы. 0–%d тиков — '
       'ПРЕДУПРЕЖДЕНИЕ (полоса светится, шевроны «вперёд»); %d–%d — три всадника проносятся по полосе. Урон — код: всадник k (0, 1, 2) '
       'выходит на тике %d + 2k и в тике t стоит в z = −4 − 3.2k + %g·(t − %d − 2k)/%d бл. от начала по yaw; урон — если игрок в полосе '
       '(|x| < %g) и |z_игрока − z| < 1.5. Полос — 3–5, параллельно или веером через арену.'
       % (T_WARN, T_WARN, T_WARN + T_RIDE + 4, T_WARN, LANE_L + 12, T_WARN, T_RIDE + 6, LANE_W / 2),
       T_WARN + T_RIDE + 10, lane, style='martin_ghost')

    # ---------------------------------------------------------------- особое: «Приказ стоять насмерть»
    fx('martin_hold_the_line', 'Особое «Приказ стоять насмерть» (caster = Мартин, follow; 10 с = %d тиков, запускать на событии wall = 1.1 с '
       'анимации martin_hold_the_line). Спереди — щит-барьер дугой 120° (мэш martin_shield_wall), под ногами полукруг-герб; спереди неуязвим '
       '(код), бить со спины. Конец — Fx.stop или по длительности; затем анимация martin_hold_end.' % T_HOLD, T_HOLD, [
        E('flash', 0, at('caster', 0, 2.2, 2.2), duration=12, size=3.0, rays=10, color='@secondary', screen=0.06, ring=True),
        E('wave', 0, 'caster', duration=22, shape='ring', radius=12, thickness=1.6, followTerrain=True, color='@primary'),
        E('mesh', 0, 'caster', follow=True, model='martin_shield_wall', duration=T_HOLD, out=ease(12)),
        E('decal', 0, 'caster', follow=True, texture='martin_emblem', radius=3.0, glow=0.3, pulse=24, color='@primary', duration=T_HOLD,
          fadeOut=12),
        E('sprites', 0, at('caster', 0, 0.2, 2.2), follow=True, duration=T_HOLD, texture='spark_soft', count=100000, rate=0.5, spread=1.6,
          speed=0.01, gravity=-0.01, size=[0.14, 0.02], life=30, color='@secondary'),
    ])
    fx('martin_hold_soldier', 'То же на солдате (caster = солдат, follow, 10 с): малый щит-барьер (scale 0.5).', T_HOLD, [
        E('mesh', 0, 'caster', follow=True, model='martin_shield_wall', scale=0.5, duration=T_HOLD, out=ease(12)),
    ])
    fx('martin_hold_deflect', 'Удар спереди отражён барьером (caster = точка удара на барьере, 10 тиков): золотые искры, звон.', 10, [
        E('flash', 0, 'caster', duration=8, size=1.1, color='@secondary', ring=True),
        E('sprites', 0, 'caster', duration=2, texture='spark_soft', count=16, rate=8, spread=0.3, speed=0.2, gravity=0.03, size=[0.14, 0.02],
          life=12, color='@primary'),
    ])

    # ---------------------------------------------------------------- удары
    fx('martin_slam', 'Рубящий сверху: клинок в землю (событие hit анимации martin_overhead; caster = точка удара ≈ 4.5 бл. перед Мартином на земле).', 30, [
        E('decal', 0, 'caster', texture='higher_cracks', radius=2.6, glow=0.3, fadeOut=24, duration=30, color='@primary'),
        E('wave', 0, 'caster', duration=14, shape='ring', radius=5, thickness=1.0, followTerrain=True, color='@primary'),
        E('sprites', 0, at('caster', 0, 0.2, 0), duration=4, texture='mote_ash', count=30, rate=10, area=1.2, speed=0.12, gravity=0.004,
          size=[0.5, 1.0], life=26, color=DUST, blend='translucent'),
        E('sprites', 0, at('caster', 0, 0.3, 0), duration=3, texture='spark_soft', count=20, rate=8, spread=0.6, speed=0.24, gravity=0.03,
          size=[0.16, 0.02], life=12, color='@secondary'),
    ])
    fx('martin_swing_trail', 'След клинка в размахе/выпаде (caster = Мартин; запуск на событии swing, 10 тиков): золотой разрез на высоте груди.', 10, [
        E('slash', 0, at('caster', 0, 2.6, 0.6), duration=8, radius=4.6, arc=150, thickness=0.35, bend=1.0, color='@primary', secondary=0.5),
    ])
    fx('martin_dash', 'Рывок щитом (события dash → hit анимации martin_shield_bash; caster = Мартин, follow, 16 тиков): след, пыль, удар.', 16, [
        E('trail', 0, at('caster', -0.9, 2.0, 1.4), follow=True, duration=12, width=1.2, length=8, color='@primary'),
        E('sprites', 0, at('caster', 0, 0.2, 0), follow=True, duration=10, texture='mote_ash', count=100000, rate=3, area=0.8, speed=0.04,
          gravity=-0.002, size=[0.5, 1.0], life=20, color=DUST, blend='translucent'),
        E('flash', 6, at('caster', -0.8, 2.0, 2.0), duration=6, size=1.6, color='@secondary', ring=True, comment='hit'),
    ])

    # ---------------------------------------------------------------- переходы фаз
    fx('martin_phase2', 'Переход 66% → «Знамя» (caster = Мартин; анимация martin_phase2 3 с: plant 0.6, roar 1.4). Меч в землю, рёв: '
       'знамёнщики-солдаты отзываются; на 2.4 с код запускает martin_banner_plant/анимацию martin_banner_plant.', 60, [
        E('decal', 12, at('caster', 0, 0, 1.6), texture='higher_cracks', radius=2.0, glow=0.4, fadeOut=30, duration=48, color='@primary'),
        E('flash', 28, at('caster', 0, 4.6, 0), duration=14, size=3.2, rays=10, color=CRIMSON, screen=0.1, ring=True),
        E('wave', 28, 'caster', duration=26, shape='ring', radius=16, thickness=2.0, followTerrain=True, color=CRIMSON),
        E('tint', 0, 'caster', duration=60, radius=32, color='#3A0A10', strength=0.25, **{'in': ease(10), 'out': ease(30)}),
    ])
    fx('martin_phase3', 'Переход 33% → «Последний полководец» (caster = Мартин; анимация martin_phase3 3.2 с: kneel 0.8, spin 1.4, roar 2.0). '
       'Все солдаты рассеиваются (martin_soldier_vanish на каждом в 0–0.8 с), знамя гаснет; на roar — золотой взрыв, затем martin_fury.', 64, [
        E('wave', 0, 'caster', duration=22, shape='ring', radius=24, thickness=2.0, followTerrain=True, color=GHOST, reverse=True,
          comment='войско уходит: волна сходится к нему'),
        E('vortex', 16, 'caster', duration=24, radius=3.0, height=6, arms=3, speed=-10, texture='spark_soft', color='@primary', out=ease(8),
          comment='оборот с мечом'),
        E('flash', 40, at('caster', 0, 5.8, 0), duration=16, size=5.0, rays=12, color='@secondary', screen=0.2, ring=True, comment='roar'),
        E('wave', 40, 'caster', duration=30, shape='ring', radius=20, thickness=2.6, followTerrain=True, color='@primary'),
        E('tint', 0, 'caster', duration=64, radius=40, color='#3A2A08', strength=0.3, **{'in': ease(12), 'out': ease(30)}),
    ])
    fx('martin_fury', 'Фаза 3 «Последний полководец» (caster = Мартин, follow, до Fx.stop): золотой ореол и искры с клинка.', -1, [
        E('aura', 0, 'caster', follow=True, target='caster', thickness=0.16, pulse=[0.25, 14], color='@primary', motes=18, texture='spark_soft'),
        E('sprites', 0, at('caster', 0, 0.1, 0), follow=True, texture='mote_ash', count=100000, rate=0.3, area=1.4, speed=0.01, gravity=-0.002,
          size=[0.5, 0.9], life=30, color=DUST, blend='translucent'),
    ])

    # ---------------------------------------------------------------- сдача: блок
    fx('martin_block', 'Блок-сдача (событие block = 0.2 с анимации martin_block_yield; caster = Мартин, yaw — к ударившему): удар игрока принят '
       'на щит — лязг, сноп искр, звон-волна, короткая засветка; в мире замирание 3 тика (код, по желанию).', 24, [
        E('flash', 0, at('caster', -0.6, 3.0, 2.4), duration=10, size=2.4, rays=12, color='#FFFFFF', screen=0.12, ring=True),
        E('sprites', 0, at('caster', -0.6, 3.0, 2.4), duration=3, texture='spark_soft', count=60, rate=20, spread=0.5, speed=0.36,
          gravity=0.03, size=[0.2, 0.02], life=16, color='@secondary', comment='сноп искр от щита'),
        E('sprites', 0, at('caster', -0.6, 3.0, 2.4), duration=2, texture='spark_soft', count=20, rate=10, spread=0.3, speed=0.5, gravity=0.04,
          size=[0.12, 0.02], life=10, color='#FFFFFF'),
        E('wave', 0, at('caster', -0.6, 3.0, 2.4), duration=12, shape='sphere', radius=2.6, rim=0.8, color='@primary', comment='звон'),
        E('wave', 0, 'caster', duration=16, shape='ring', radius=6, thickness=0.8, followTerrain=True, color='@primary'),
    ])
    fx('martin_yield', 'Мартин опускает оружие (с события lower = 1.2 с; caster = Мартин, 80 тиков): строй и знамя гаснут, тьма уходит, '
       'мягкий золотой свет; на speak (2.4 с) — фраза ui.pohsmp_core.martin.yield.', 80, [
        E('aura', 0, 'caster', duration=70, target='caster', thickness=0.12, pulse=[0.15, 30], color='@primary', motes=10, out=ease(30)),
        E('sprites', 0, at('caster', 0, 0.2, 0), duration=60, texture='spark_soft', count=100000, rate=0.4, area=3, speed=0.01, gravity=-0.006,
          size=[0.14, 0.02], life=40, color='@secondary'),
        E('wave', 24, 'caster', duration=30, shape='ring', radius=14, thickness=1.2, followTerrain=True, color='@secondary'),
    ])


# ================================================================== полоса босса (192×36: строки 0–17 пустая, 18–35 полная)
BAR = {
    1: dict(frame=('#3a3b40', '#a6a8ae', '#dfe0e3'), fill=('#82848b', '#c4c6cb', '#f7f7f8'), gem='#9fd8f0', accent='#a6a8ae'),
    2: dict(frame=('#2a060c', '#9c1c24', '#e0463a'), fill=('#4c0c14', '#c22a2c', '#e8705c'), gem='#ffd060', accent='#dfe0e3'),
    3: dict(frame=('#3e2410', '#c8933a', '#fff1c4'), fill=('#9a6a26', '#e5b95a', '#fff1c4'), gem='#c22a2c', accent='#f6d88a'),
}
CROWN = [  # 24×7, центр полосы (x 84…107), '.' прозрачно, 'o' обвод, 'm' металл, 'h' блик, 'g' камень
    '...o.....o....o.....o...',
    '..omo...omo..omo...omo..',
    '..omho.omhmoomhmo.ohmo..',
    '..ommmmmmmmmmmmmmmmmmo..',
    '..omgmmmmmmgmmmmmmmgmo..',
    '..ommmmmmmmmmmmmmmmmmo..',
    '...oooooooooooooooooo...',
]


def bossbar(phase):
    st = BAR[phase]
    fr = [hx(c) for c in st['frame']]
    fi = [hx(c) for c in st['fill']]
    img = Image.new('RGBA', (192, 36), (0, 0, 0, 0))
    px = img.load()
    O = hx('#120c0e')
    for half in (0, 18):
        full = half == 18
        for x in range(1, 191):
            px[x, half + 6] = O
            px[x, half + 12] = O
        for y in range(half + 7, half + 12):
            px[1, y] = O
            px[190, y] = O
        for x in range(2, 190):
            px[x, half + 7] = fr[2]
            px[x, half + 11] = fr[0]
        for y in range(half + 8, half + 11):
            px[2, y] = fr[1]
            px[189, y] = fr[1]
        for x in range(3, 189):                                   # заливка
            if full:
                cols = (fi[2], fi[1], fi[0])
                if phase == 2 and (x // 6) % 2 == 0:
                    cols = (fi[2], fi[1], hx('#74121c'))
                if phase == 3 and x % 9 == 4:
                    cols = (hx('#ffffff'), fi[2], fi[1])
            else:
                cols = (hx('#2c2a30'), hx('#1c1a20'), hx('#141218'))
            for k, y in enumerate(range(half + 8, half + 11)):
                px[x, y] = cols[k]
        for x in (24, 48, 72, 119, 143, 167):                     # заклёпки-деления
            px[x, half + 7] = hx(st['accent'])
        # концы: «гарды» меча по краям
        for sx in (0, 1):
            x0 = 0 if sx == 0 else 186
            for dy in range(4, 15):
                for dx in range(0, 6):
                    xx = x0 + dx
                    if (dy in (4, 14) and 1 <= dx <= 4) or (dx in (0, 5) and 5 <= dy <= 13):
                        px[xx, half + dy] = O
                    elif 5 <= dy <= 13 and 1 <= dx <= 4 and not (7 <= dy <= 11 and 1 < dx < 4 and False):
                        px[xx, half + dy] = fr[2] if dy == 5 else (fr[0] if dy == 13 else fr[1])
            gx = 2 if sx == 0 else 188
            px[gx, half + 9] = hx(st['gem'])
            px[gx + 1, half + 9] = hx(st['gem'])
        # корона в центре над полосой
        for j, row in enumerate(CROWN):
            for i, ch in enumerate(row):
                if ch == '.':
                    continue
                c = {'o': O, 'm': fr[1], 'h': fr[2], 'g': hx(st['gem'])}[ch]
                px[84 + i, half + j] = c
        # подвеска-острие под центром
        for j, w in enumerate((3, 2, 1)):
            for i in range(-w, w):
                px[96 + i, half + 13 + j] = fr[1] if abs(i + 0.5) < w - 0.5 else O
    sfx = '' if phase == 1 else '_p%d' % phase
    img.save(M.out('textures/gui/sprites/boss_bars/martin_bossbar%s.png' % sfx))
    return img


def bossbar_flash(bar):
    a = np.asarray(bar).copy()
    a = a[18:36]
    out_ = np.zeros_like(a)
    out_[..., :3] = 255
    out_[..., 3] = (a[..., 3] > 0) * 255
    img = Image.fromarray(out_, 'RGBA')
    img.save(M.out('textures/gui/sprites/boss_bars/martin_bossbar_flash.png'))
    return img


# ================================================================== титры (1024×192)
def _font(name, sz):
    return ImageFont.truetype(os.path.join(HERE, 'fonts', name), sz)


class MixFont:
    """Кириллическая часть Cormorant Garamond не содержит цифр и знаков — их берём из латинской (запятая, «4», кавычки, тире)."""

    def __init__(self, sz):
        self.c, self.l = _font(CYR, sz), _font(LAT, sz)

    def runs(self, text):
        out_, cur, fc = [], '', None
        for ch in text:
            f = self.c if ('\u0400' <= ch <= '\u04ff') else self.l
            if f is not fc and cur:
                out_.append((cur, fc))
                cur = ''
            fc = f
            cur += ch
        if cur:
            out_.append((cur, fc))
        return out_

    def getbbox(self, text):
        x, top, bot = 0, 1e9, -1e9
        for r, f in self.runs(text):
            b = f.getbbox(r)
            top, bot = min(top, b[1]), max(bot, b[3])
            x += f.getlength(r)
        return (0, top, x, bot)

    def draw(self, d, xy, text, fill):
        x, y = xy
        for r, f in self.runs(text):
            d.text((x, y), r, font=f, fill=fill)
            x += f.getlength(r)


def title(name, line1, f1, line2=None, f2=None, metal='silver'):
    S = 2
    Wd, Hd = 1024 * S, 192 * S
    fnt = MixFont((84 if not line2 else 70) * S)
    bb = fnt.getbbox(line1)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    tx, ty = (Wd - tw) / 2 - bb[0], (18 if not line2 else 6) * S - bb[1] + ((96 if not line2 else 80) * S - th) / 2
    mask = Image.new('L', (Wd, Hd), 0)
    fnt.draw(ImageDraw.Draw(mask), (tx, ty), line1, 255)
    sub = Image.new('L', (Wd, Hd), 0)
    if line2:
        f2_ = MixFont(40 * S)
        b2 = f2_.getbbox(line2)
        f2_.draw(ImageDraw.Draw(sub), ((Wd - (b2[2] - b2[0])) / 2 - b2[0], 98 * S - b2[1]), line2, 255)
    stops_main = {'silver': ['#ffffff', '#dfe0e3', '#a6a8ae', '#6e7078'], 'gold': ['#fff1c4', '#e5b95a', '#c8933a', '#7a4e1c']}[metal]
    stops_sub = ['#fff1c4', '#e5b95a', '#c8933a', '#9a6a26']

    def grad(stops, top, h):
        cols = [np.array(hx(c)[:3], np.float32) for c in stops]
        t = np.clip((np.arange(Hd)[:, None] - top) / max(1, h), 0, 1)
        g = np.zeros((Hd, 1, 3), np.float32)
        pts = [0, 0.45, 0.8, 1.0]
        for k in range(3):
            sel = (t >= pts[k]) & (t <= pts[k + 1])
            u = (t - pts[k]) / (pts[k + 1] - pts[k])
            for ch in range(3):
                g[..., ch] = np.where(sel, cols[k][ch] + (cols[k + 1][ch] - cols[k][ch]) * u, g[..., ch])
        return np.broadcast_to(g, (Hd, Wd, 3))
    both = Image.fromarray(np.maximum(np.asarray(mask), np.asarray(sub)))
    m1 = np.asarray(mask, np.float32) / 255
    m2 = np.asarray(sub, np.float32) / 255
    outline = np.asarray(both.filter(ImageFilter.MaxFilter(9)), np.float32) / 255
    halo = np.asarray(both.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(20 * S)), np.float32) / 255
    out_ = np.zeros((Hd, Wd, 4), np.float32)
    out_[..., :3] = np.array(hx('#8a1018')[:3], np.float32)
    out_[..., 3] = np.clip(halo * 1.3, 0, 0.7)                         # кровавый отсвет за буквами
    ob = np.array(hx('#120c0e')[:3], np.float32)
    out_[..., :3] = out_[..., :3] * (1 - outline[..., None]) + ob * outline[..., None]
    out_[..., 3] = np.maximum(out_[..., 3], outline)
    out_[..., :3] = out_[..., :3] * (1 - m1[..., None]) + grad(stops_main, ty + bb[1], th) * m1[..., None]
    out_[..., :3] = out_[..., :3] * (1 - m2[..., None]) + grad(stops_sub, 98 * S, 40 * S) * m2[..., None]
    out_[..., 3] = np.maximum(out_[..., 3], np.maximum(m1, m2))
    out_[..., 3] *= 255
    img = Image.fromarray(out_.clip(0, 255).astype(np.uint8), 'RGBA').resize((1024, 192), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    y = 150 if not line2 else 174
    for x in range(150, 874):                                          # линия-клинок, сходящая на нет
        k = 1 - abs(x - 512) / 362
        a_ = int(255 * min(1, k * 2.2))
        d.point((x, y), fill=hx('#dfe0e3', a_))
        d.point((x, y + 1), fill=hx('#82848b', a_))
        d.point((x, y - 1), fill=hx('#120c0e', int(a_ * 0.8)))
        d.point((x, y + 2), fill=hx('#120c0e', int(a_ * 0.8)))
    crown = Image.new('RGBA', (24, 7), (0, 0, 0, 0))
    st = BAR[3]
    for j, row in enumerate(CROWN):
        for i, ch in enumerate(row):
            if ch != '.':
                crown.putpixel((i, j), {'o': hx('#120c0e'), 'm': hx(st['frame'][1]), 'h': hx(st['frame'][2]), 'g': hx(st['gem'])}[ch])
    img.alpha_composite(crown.resize((72, 21), Image.NEAREST), (512 - 36, y - 10))
    img.save(M.out('textures/gui/title/%s.png' % name))
    return img


LAT, CYR = 'CormorantGaramond-BoldItalic-latin.woff', 'CormorantGaramond-BoldItalic-cyrillic.woff'


def titles():
    out_ = {}
    out_['martin_ru'] = title('martin_ru', 'Мартин, Последний Полководец', CYR, 'Глава 4 Ячейки Культа', CYR)
    out_['martin_en'] = title('martin_en', 'Martin, the Last Warlord', LAT, 'Head of the Cult\'s Fourth Cell', LAT)
    out_['martin_cavalry_ru'] = title('martin_cavalry_ru', 'Атака конницы', CYR, metal='gold')
    out_['martin_cavalry_en'] = title('martin_cavalry_en', 'Cavalry Charge', LAT, metal='gold')
    out_['martin_hold_ru'] = title('martin_hold_ru', 'Приказ стоять насмерть', CYR, metal='gold')
    out_['martin_hold_en'] = title('martin_hold_en', 'Hold the Line to the Death', LAT, metal='gold')
    return out_


# ================================================================== иконки статусов (18×18, textures/gui/martin/)
def _icon(name, draw, bg='#1a1416', rim='#a6a8ae'):
    K = 8
    S = 18 * K
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([K * 0.5, K * 0.5, S - K * 0.5, S - K * 0.5], radius=K * 3, fill=hx(bg), outline=hx(rim), width=K)
    draw(d, S)
    sm = im.resize((18, 18), Image.LANCZOS)
    a = np.asarray(sm).copy()
    a[..., 3] = np.where(a[..., 3] > 100, 255, 0)
    img = Image.fromarray(a, 'RGBA')
    img.save(M.out('textures/gui/martin/%s.png' % name))
    return img


def _shield(d, cx, cy, s, fill, out='#120c0e'):
    pts = [(cx - s, cy - s * 1.2), (cx + s, cy - s * 1.2), (cx + s, cy + s * 0.3), (cx, cy + s * 1.3), (cx - s, cy + s * 0.3)]
    d.polygon(pts, fill=hx(fill), outline=hx(out), width=int(s * 0.18))


def icons():
    out_ = {}

    def formation(d, S):
        for k, x in enumerate((0.28, 0.5, 0.72)):
            _shield(d, S * x, S * (0.52 if k != 1 else 0.46), S * 0.14, '#8fd8f0' if k != 1 else '#d8f6ff')
    out_['status_formation'] = _icon('status_formation', formation, rim='#8fd8f0')

    def banner(d, S):
        d.rectangle([S * 0.27, S * 0.15, S * 0.33, S * 0.88], fill=hx('#7e5433'))
        d.polygon([(S * 0.33, S * 0.18), (S * 0.8, S * 0.18), (S * 0.8, S * 0.62), (S * 0.57, S * 0.5), (S * 0.33, S * 0.62)], fill=hx('#c22a2c'),
                  outline=hx('#e5b95a'), width=int(S * 0.04))
        d.rectangle([S * 0.5, S * 0.26, S * 0.62, S * 0.32], fill=hx('#f6d88a'))
    out_['status_banner'] = _icon('status_banner', banner, rim='#e5b95a')

    def hold(d, S):
        _shield(d, S * 0.5, S * 0.47, S * 0.24, '#e5b95a')
        d.rectangle([S * 0.47, S * 0.3, S * 0.53, S * 0.68], fill=hx('#7a4e1c'))
        d.rectangle([S * 0.36, S * 0.4, S * 0.64, S * 0.45], fill=hx('#7a4e1c'))
    out_['status_hold'] = _icon('status_hold', hold, rim='#e5b95a')

    def cavalry(d, S):   # голова коня в шанфроне
        d.polygon([(S * 0.3, S * 0.84), (S * 0.36, S * 0.4), (S * 0.5, S * 0.18), (S * 0.58, S * 0.3), (S * 0.8, S * 0.55), (S * 0.74, S * 0.66),
                   (S * 0.55, S * 0.55), (S * 0.56, S * 0.84)], fill=hx('#8fd8f0'), outline=hx('#120c0e'), width=int(S * 0.04))
        d.rectangle([S * 0.5, S * 0.36, S * 0.56, S * 0.42], fill=hx('#ffffff'))
        d.line([(S * 0.4, S * 0.3), (S * 0.3, S * 0.62)], fill=hx('#d8f6ff'), width=int(S * 0.06))
    out_['status_cavalry'] = _icon('status_cavalry', cavalry, rim='#8fd8f0')

    def last(d, S):      # фаза 3: меч и корона
        d.polygon([(S * 0.46, S * 0.24), (S * 0.54, S * 0.24), (S * 0.54, S * 0.7), (S * 0.5, S * 0.82), (S * 0.46, S * 0.7)], fill=hx('#f6d88a'))
        d.rectangle([S * 0.3, S * 0.3, S * 0.7, S * 0.36], fill=hx('#c8933a'))
        d.rectangle([S * 0.47, S * 0.14, S * 0.53, S * 0.24], fill=hx('#22232b'))
    out_['status_last_warlord'] = _icon('status_last_warlord', last, rim='#c22a2c')
    return out_


# ================================================================== lang и звуки
YIELD_RU = 'Хорошо, вы доказали свою силу...Я помогу Эребу, если эта ваша просьба'
YIELD_EN = 'Very well, you have proven your strength... I will help Erebus, if that is your request'
LANG = {
    'entity.pohsmp_core.martin': ('Мартин, Последний Полководец', 'Martin, the Last Warlord'),
    'entity.pohsmp_core.martin_soldier': ('Призрачный солдат', 'Phantom Soldier'),
    'entity.pohsmp_core.martin_banner': ('Знамя Мартина', 'Martin\'s Banner'),
    'ui.pohsmp_core.martin.title': ('Мартин, Последний Полководец', 'Martin, the Last Warlord'),
    'ui.pohsmp_core.martin.epithet': ('Глава 4 Ячейки Культа', 'Head of the Cult\'s Fourth Cell'),
    'ui.pohsmp_core.martin.subtitle': ('Глава 4 Ячейки Культа', 'Head of the Cult\'s Fourth Cell'),
    'ui.pohsmp_core.martin.formation': ('«Строй!» — призрачные солдаты прикрывают Мартина щитами', '"Form ranks!" — phantom soldiers shield Martin'),
    'ui.pohsmp_core.martin.formation_block': ('Строй принимает удар на щиты', 'The ranks take the blow on their shields'),
    'ui.pohsmp_core.martin.command': ('«В атаку!»', '"Charge!"'),
    'ui.pohsmp_core.martin.phase2': ('«Знамя!» — пока оно стоит, солдаты сильнее. Срубите знамя!', '"Raise the banner!" — while it stands, the soldiers grow stronger. Cut it down!'),
    'ui.pohsmp_core.martin.banner_cut': ('Знамя срублено!', 'The banner has fallen!'),
    'ui.pohsmp_core.martin.phase3': ('«Последний полководец»: войско уходит, Мартин сражается сам', '"The Last Warlord": the army fades, Martin fights alone'),
    'ui.pohsmp_core.martin.cavalry': ('Атака конницы', 'Cavalry Charge'),
    'ui.pohsmp_core.martin.cavalry_warn': ('Конница! Уйдите с отмеченных полос', 'Cavalry! Get off the marked lanes'),
    'ui.pohsmp_core.martin.hold': ('Приказ стоять насмерть: спереди неуязвимы — бейте со спины (%s с)', 'Hold the Line to the Death: invulnerable from the front — strike from behind (%ss)'),
    'ui.pohsmp_core.martin.hold_blocked': ('Щит! Бейте со спины', 'Shielded! Strike from behind'),
    'ui.pohsmp_core.martin.hold_end': ('Строй дрогнул — приказ снят', 'The line wavers — the order is lifted'),
    'ui.pohsmp_core.martin.yield': (YIELD_RU, YIELD_EN),
    'ui.pohsmp_core.martin.status.formation': ('Строй', 'Formation'),
    'ui.pohsmp_core.martin.status.banner': ('Знамя', 'Banner'),
    'ui.pohsmp_core.martin.status.hold': ('Стоять насмерть', 'Hold the Line'),
    'ui.pohsmp_core.martin.status.cavalry': ('Конница', 'Cavalry'),
    'ui.pohsmp_core.martin.status.last_warlord': ('Последний полководец', 'The Last Warlord'),
    'subtitles.pohsmp_core.martin.spawn': ('Мартин поднимается', 'Martin rises'),
    'subtitles.pohsmp_core.martin.step': ('Тяжёлые шаги', 'Heavy footsteps'),
    'subtitles.pohsmp_core.martin.swing': ('Свист двуручника', 'Greatsword swings'),
    'subtitles.pohsmp_core.martin.slam': ('Меч врубается в землю', 'Greatsword strikes the ground'),
    'subtitles.pohsmp_core.martin.bash': ('Удар щитом', 'Shield bash'),
    'subtitles.pohsmp_core.martin.block': ('Лязг щита', 'Shield clangs'),
    'subtitles.pohsmp_core.martin.command': ('Мартин командует', 'Martin gives an order'),
    'subtitles.pohsmp_core.martin.horn': ('Трубит рог', 'A war horn sounds'),
    'subtitles.pohsmp_core.martin.gallop': ('Топот призрачной конницы', 'Phantom cavalry gallops'),
    'subtitles.pohsmp_core.martin.banner_plant': ('Знамя вонзается в землю', 'Banner is planted'),
    'subtitles.pohsmp_core.martin.banner_cut': ('Древко знамени ломается', 'Banner pole snaps'),
    'subtitles.pohsmp_core.martin.hold': ('Щиты сомкнулись', 'Shields lock together'),
    'subtitles.pohsmp_core.martin.soldier': ('Встаёт призрачный солдат', 'Phantom soldier rises'),
    'subtitles.pohsmp_core.martin.soldier_vanish': ('Призрачный солдат рассеивается', 'Phantom soldier fades'),
    'subtitles.pohsmp_core.martin.phase': ('Мартин ревёт', 'Martin roars'),
    'subtitles.pohsmp_core.music.martin': ('Музыка: Мартин', 'Music: Martin'),
}


def S_(name, **kw):
    o = {'name': name}
    o.update(kw)
    return o


SOUNDS = {
    'martin.spawn': [S_('irons_spellbooks:dead_king/spawn', pitch=0.8, volume=1.4)],
    'martin.step': [S_('minecraft:mob/irongolem/walk%d' % k, pitch=0.7, volume=1.1) for k in (1, 2, 3, 4)],
    'martin.swing': [S_('irons_spellbooks:dead_king/swing_01', pitch=0.8), S_('irons_spellbooks:dead_king/swing_02', pitch=0.8)],
    'martin.slam': [S_('irons_spellbooks:dead_king/attack_slam', pitch=0.85, volume=1.3)],
    'martin.bash': [S_('minecraft:item/shield/block%d' % k, pitch=0.6, volume=1.4) for k in (1, 2, 3)],
    'martin.block': [S_('minecraft:random/anvil_land', pitch=1.4, volume=1.2), S_('minecraft:item/shield/block4', pitch=0.8, volume=1.4)],
    'martin.command': [S_('minecraft:mob/ravager/roar%d' % k, pitch=1.3, volume=1.2) for k in (1, 2, 3)],
    'martin.horn': [S_('minecraft:event/raid/raidhorn', pitch=0.9, volume=1.6, stream=True)],
    'martin.gallop': [S_('minecraft:mob/horse/gallop%d' % k, pitch=0.75, volume=1.3) for k in (1, 2, 3, 4)],
    'martin.banner_plant': [S_('minecraft:random/anvil_land', pitch=0.6, volume=1.1)],
    'martin.banner_cut': [S_('minecraft:mob/zombie/woodbreak', pitch=0.8, volume=1.2)],
    'martin.hold': [S_('minecraft:block/beacon/activate', pitch=0.7, volume=1.2)],
    'martin.soldier': [S_('minecraft:block/beacon/ambient', pitch=1.6, volume=0.6)],
    'martin.soldier_vanish': [S_('minecraft:block/beacon/deactivate', pitch=1.5, volume=0.5)],
    'martin.phase': [S_('minecraft:mob/ravager/roar%d' % k, pitch=0.8, volume=1.5) for k in (1, 2, 3)],
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


def sounds():
    p = os.path.join(M.A, 'sounds.json')
    d = json.load(open(p, encoding='utf-8'))
    for k, v in SOUNDS.items():
        d[k] = {'subtitle': 'subtitles.pohsmp_core.' + k, 'sounds': v}
    d['music.martin'] = {'category': 'record', 'subtitle': 'subtitles.pohsmp_core.music.martin',
                         'comment': 'ЗАГЛУШКА до трека владельца: тема Мёртвого Короля (Iron\'s). Трек владельца — pohsmp_core:music/martin (stream).',
                         'sounds': [S_('irons_spellbooks:dead_king/music/first_phase_melody', stream=True, volume=0.6)]}
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
        f.write('\n')
    M.WRITTEN.append('sounds.json (+%d событий)' % (len(SOUNDS) + 1))


# ================================================================== солдат-мэш для роликов (поза покоя модели солдата → бруски)
def soldier_mesh():
    import gen_martin_extra as X
    X.M = M
    m = X.build_soldier()
    tones = ['#86bcd2', '#3e6a80', '#e4f2c8', '#2e5e78', '#c8f4ff', '#a6d6e6', '#16303c']
    idx = {'steel': 0, 'dark': 1, 'gold': 2, 'red': 3, 'eye': 4, 'blade': 5, 'grip': 1, 'leather': 6, 'cape': 6}
    boxes = X.mesh_from_model(m, idx)
    ys = [b[1] for b in boxes] + [b[4] for b in boxes]
    write('fx/meshes/martin_soldier_ghost.json', {
        'comment': 'T29: призрачный солдат для роликов (поза «смирно», щит на руке), лицом вперёд по +z мэша. Сгенерировано gen_martin_fx.py из модели martin_soldier.',
        'style': 'martin_ghost', 'center': 0, 'formedAt': 10, 'collapse': {'duration': 14, 'easing': 'easeInCubic'},
        'parts': [{'type': 'boxes', 'tones': tones, 'glowTones': [2, 4], 'blend': 'translucent', 'opacity': 0.5, 'shade': True, 'boxes': boxes,
                   'appear': {'delay': 0, 'duration': 14, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.5},
                   'bounds': [round(min(ys), 3), round(max(ys), 3)]}]})


# ================================================================== проверочные кадры
def _three():
    p = os.path.join(os.environ.get('MARTIN_THREE', ''), '')
    return os.environ.get('MARTIN_THREE') or None


def shots():
    import martin_render as R
    three = _three()
    os.makedirs(MEDIA, exist_ok=True)
    big = dict(dist=2.6, ty=40)
    # 1. модель: спереди, 3/4, сзади, сбоку; рядом эталон в том же свете и масштабе мира
    R.sheet(os.path.join(MEDIA, 't29_model.jpg'), {'cols': 4, 'cells': [
        dict(model='martin', anim='martin_npc_idle', t=0.5, yaw=0, pitch=4, label='Мартин — спереди', sub='поза мирного NPC', **big),
        dict(model='martin', anim='martin_idle', t=0.5, yaw=35, pitch=6, label='3/4 — боевая стойка', **big),
        dict(model='martin', anim='martin_idle', t=0.5, yaw=180, pitch=6, label='сзади — щит, плащ', **big),
        dict(model='martin', anim='martin_walk', t=0.4, yaw=90, pitch=6, label='сбоку — шаг', **big)]}, three, (1600, 900))
    R.sheet(os.path.join(MEDIA, 't29_vs_cult_leader.jpg'), {'cols': 1, 'cells': [
        dict(model='martin', anim='martin_npc_idle', t=0.5, yaw=12, pitch=6, dist=3.0, ty=40, tx=-1.8, tz=0,
             label='Мартин (×2) рядом с Главой Культа (эталон T26) — один масштаб мира и свет',
             models=[dict(model='cult_leader', pos=[-4.0, 0, 0.0], ry=0)])]}, three, (1400, 900))
    # 2. анимации
    A = [('martin_spawn', 0.5, 'появление: на колене'), ('martin_spawn', 5.2, 'появление: салют'), ('martin_swing', 0.55, 'размах: замах'),
         ('martin_swing', 0.8, 'размах: удар'), ('martin_overhead', 0.7, 'сверху: замах'), ('martin_overhead', 1.1, 'сверху: удар'),
         ('martin_thrust', 0.7, 'выпад'), ('martin_shield_bash', 0.8, 'рывок щитом'), ('martin_command', 1.0, 'команда «в атаку»'),
         ('martin_banner_plant', 0.9, 'знамя: поднял'), ('martin_banner_plant', 1.5, 'знамя: вонзил'), ('martin_cavalry', 1.2, 'конница: меч к небу'),
         ('martin_cavalry', 2.3, 'конница: «вперёд!»'), ('martin_hold_the_line', 1.6, 'стоять насмерть'), ('martin_phase2', 1.8, 'фаза 2: рёв'),
         ('martin_phase3', 2.3, 'фаза 3: меч над головой'), ('martin_block_yield', 0.3, 'блок-сдача: блок'), ('martin_block_yield', 3.0, 'сдача: опустил'),
         ('martin_npc_idle', 1.0, 'мирный NPC'), ('martin_walk', 1.0, 'тяжёлый шаг')]
    R.sheet(os.path.join(MEDIA, 't29_poses.jpg'), {'cols': 5, 'cells': [
        dict(model='martin', anim=a, t=t, yaw=30, pitch=8, dist=2.9, ty=40, label=l) for a, t, l in A]}, three, (1800, 1500))
    # 3. солдаты, знамя
    R.sheet(os.path.join(MEDIA, 't29_army.jpg'), {'cols': 4, 'cells': [
        dict(model='martin_soldier', anim='martin_soldier_idle', t=0.3, yaw=30, label='призрачный солдат', sub='entityTranslucent, альфа ~0.65 + glowmask'),
        dict(model='martin_soldier', anim='martin_soldier_brace', t=0.3, yaw=40, label='«Строй»: щит вперёд'),
        dict(model='martin_soldier', anim='martin_soldier_attack', t=0.5, yaw=60, label='удар из-за щита'),
        dict(model='martin_soldier', anim='martin_soldier_spawn', t=0.6, yaw=30, label='встаёт из земли'),
        dict(model='martin_banner', anim='martin_banner_idle', t=0.5, yaw=20, dist=2.0, label='знамя', sub='полотнище — 3 кости'),
        dict(model='martin_banner', anim='martin_banner_idle', t=0.5, yaw=200, dist=2.0, label='знамя сзади'),
        dict(model='martin_banner', anim='martin_banner_hit', t=0.1, yaw=60, dist=2.0, label='удар по знамени'),
        dict(model='martin_banner', anim='martin_banner_cut', t=1.5, yaw=20, dist=2.0, label='знамя срублено')]}, three, (1600, 1100))
    # 4. сцены fx: строй, знамя, конница по полосам, «стоять насмерть»
    ring = [dict(model='martin_soldier', anim='martin_soldier_brace', t=0.2, pos=[math.sin(a) * 3.2, 0, -math.cos(a) * 3.2],
                 ry=-math.degrees(a)) for a in [math.radians(v) for v in (-60, -30, 0, 30, 60)]]
    lanes = [dict(tex='martin_lane', pos=[x, 0.04, -24], w=3, h=40, color='#8fd8f0', opacity=0.9) for x in (-7, 0, 7)]
    riders = [dict(mesh='martin_cavalry_rider', pos=[x + dx, 0, z], ry=0) for x, dx, z in ((-7, -0.6, -30), (0, 0.6, -16), (7, 0, -36))]
    R.sheet(os.path.join(MEDIA, 't29_fx.jpg'), {'cols': 2, 'cells': [
        dict(model='martin', anim='martin_command', t=1.0, yaw=-25, pitch=24, dist=3.0, ty=30, label='Фаза 1 «Строй»',
             sub='солдаты держат щиты перед Мартином; герб строя r4', models=ring,
             decals=[dict(tex='martin_emblem', pos=[0, 0.03, 0], r=4.2, color='#8fd8f0', opacity=0.6)]),
        dict(model='martin', anim='martin_idle', t=0.5, yaw=-40, pitch=22, dist=3.4, ty=30, label='Фаза 2 «Знамя»',
             sub='кольцо r8 — солдаты сильнее; знамя можно срубить',
             models=[dict(model='martin_banner', anim='martin_banner_idle', t=0.4, pos=[-3.6, 0, -2.4])] + ring[1:4],
             decals=[dict(tex='martin_banner_ring', pos=[-3.6, 0.03, -2.4], r=8, color='#e8b95a', opacity=0.7)]),
        dict(model='martin', anim='martin_cavalry', t=2.3, yaw=-28, pitch=36, dist=4.2, ty=10, tz=-20, tx=0,
             label='«Атака конницы»', sub='полосы 40×3 бл.: 2 с предупреждения, затем всадники', decals=lanes, meshes=riders),
        dict(model='martin', anim='martin_hold_loop', t=0.5, yaw=20, pitch=10, dist=3.0, ty=34, label='«Приказ стоять насмерть»',
             sub='щит-барьер спереди 120° — бить со спины', meshes=[dict(mesh='martin_shield_wall', pos=[0, 0, 0], ry=180, scale=1)])]},
            three, (1600, 1100))


def sheet_ui(bars, flash, tit, ic):
    W = 1280
    img = Image.new('RGBA', (W, 980), hx('#16101a'))
    d = ImageDraw.Draw(img)
    f = MixFont(26)
    y = 20
    for ph, b in bars.items():
        f.draw(d, (30, y), 'Фаза %d — %s' % (ph, {1: 'серебро («Строй»)', 2: 'красный («Знамя»)', 3: 'золото («Последний полководец»)'}[ph]),
               hx('#e8e0d8'))
        big = b.resize((192 * 5, 36 * 5), Image.NEAREST)
        top = big.crop((0, 0, 960, 90))
        full = big.crop((0, 90, 960, 180))
        k = 0.62
        comp = top.copy()
        comp.paste(full.crop((0, 0, int(15 + k * 930), 90)), (0, 0))
        img.alpha_composite(comp, (30, y + 34))
        y += 140
    img.alpha_composite(flash.resize((192 * 5, 18 * 5), Image.NEAREST), (30, y + 4))
    MixFont(20).draw(d, (1000, y + 30), 'вспышка смены фазы', hx('#b0a8a0'))
    y += 110
    for n in ('martin_ru', 'martin_en'):
        img.alpha_composite(tit[n].resize((600, 112), Image.LANCZOS), (30 if n.endswith('ru') else 650, y))
    y += 120
    for n in ('martin_cavalry_ru', 'martin_hold_ru'):
        img.alpha_composite(tit[n].resize((600, 112), Image.LANCZOS), (30 if 'cavalry' in n else 650, y))
    y += 130
    x = 30
    for n, im in ic.items():
        img.alpha_composite(im.resize((72, 72), Image.NEAREST), (x, y))
        d.text((x + 82, y + 22), n.replace('status_', ''), font=_font(LAT, 22), fill=hx('#e8e0d8'))
        x += 250
    img.convert('RGB').save(os.path.join(MEDIA, 't29_ui.jpg'), quality=90)


def sheet_textures():
    names = ['martin', 'martin_soldier', 'martin_banner']
    tiles = []
    for n in names:
        im = Image.open(os.path.join(M.A, 'textures', 'entity', 'martin', n + '.png')).convert('RGBA')
        bg = Image.new('RGBA', im.size, hx('#2a2430'))
        bg.alpha_composite(im)
        tiles.append(bg.resize((512, int(512 * im.size[1] / im.size[0])), Image.NEAREST))
    for n in ('martin_emblem', 'martin_banner_ring', 'martin_barrier', 'martin_lane'):
        im = Image.open(os.path.join(M.A, 'textures', 'sigil', n + '.png')).convert('RGBA')
        bg = Image.new('RGBA', im.size, hx('#16101a'))
        bg.alpha_composite(im)
        h = 256
        tiles.append(bg.resize((max(1, int(h * im.size[0] / im.size[1])), h), Image.LANCZOS))
    W = 1600
    H = 40 + max(t.size[1] for t in tiles[:3]) + 300
    out_ = Image.new('RGB', (W, H), (22, 16, 26))
    x = 20
    for t in tiles[:3]:
        out_.paste(t.convert('RGB'), (x, 20))
        x += t.size[0] + 10
    x = 20
    y = 40 + max(t.size[1] for t in tiles[:3])
    for t in tiles[3:]:
        out_.paste(t.convert('RGB'), (x, y))
        x += t.size[0] + 20
    out_.save(os.path.join(MEDIA, 't29_textures.jpg'), quality=90)


# ================================================================== запуск
def run(mod, args=()):
    global M
    M = mod
    textures()
    meshes()
    soldier_mesh()
    effects()
    bars = {p: bossbar(p) for p in (1, 2, 3)}
    flash = bossbar_flash(bars[3])
    tit = titles()
    ic = icons()
    lang()
    sounds()
    os.makedirs(MEDIA, exist_ok=True)
    sheet_ui(bars, flash, tit, ic)
    sheet_textures()
    if '--shots' in args:
        shots()
    if '--html' in args:
        import martin_render as R
        R.html_preview()
    print('fx/ui/lang готово')


if __name__ == '__main__':
    import sys
    sys.path.insert(0, HERE)
    import gen_martin
    run(gen_martin, sys.argv[1:])
