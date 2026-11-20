#!/usr/bin/env python3
"""
T26 — «+4 заклинания» Тироса (владелец 20.11): «Огненный серп», «Пепельный след», «Клеймо культа», «Столпы пламени».
Обычные приёмы без ролика; у каждого видимое предупреждение; лучей к цели нет. Коса — наш предмет cult_scythe (модель уже есть).

Пишет: анимации cult_leader_sickle_throw / _ash_trail_dash / _brand / _pillars (в animations/entity/cult_leader.animation.json),
fx/cult_sickle_*.json, cult_ash_trail*.json, cult_brand*.json, cult_pillar*.json, sigils/cult_brand.json,
textures/mob_effect/cult_brand.png, lang (ru/en).

Запуск отдельно (только эти файлы, остальное не перегенерирует):  python3 tools/gen_cult_leader_spells4.py
При полной перегенерации (tools/gen_cult_leader.py) вызывается из gen_cult_leader_extra.run().
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_forbidden_fx as F  # noqa: E402

M = FX = None

# ================================================================== анимации (оси — как в gen_cult_leader_extra)
Z, IO, OC, IQ, OQ = [0, 0, 0], 'easeInOutSine', 'easeOutCubic', 'easeInQuart', 'easeOutQuart'
SICKLE_THROW, SICKLE_CATCH = 1.0, 1.8         # с: бросок после 1 с дуги-предупреждения; коса возвращается в руку
DASH_T = 0.5                                  # с: рывок после 0.5 с линии-предупреждения
BRAND_T = 0.55
PILLAR_MARK, PILLAR_ERUPT = 0.3, 1.8           # круги на 0.3 с, столбы через 1.5 с


def anims():
    from gen_cult_leader_extra import A, ch
    an = {}
    wind = {'torso': [0, 45, 0], 'right_arm': [-35, 35, 85], 'left_arm': [-60, 0, -25], 'body': [12, 0, 0], 'head': [5, -30, 0]}
    an['cult_leader_sickle_throw'] = A(2.2, {
        'body': {'rotation': ch((0, Z), (0.6, wind['body'], IO), (SICKLE_THROW, [16, 0, 0]), (1.15, [6, -8, 0], OQ), (2.2, Z, IO)),
                 'position': ch((0, Z), (0.6, [0, -2, 0], IO), (1.15, [0, -1, -3], OQ), (2.2, Z, IO))},
        'torso': {'rotation': ch((0, Z), (0.6, wind['torso'], IO), (SICKLE_THROW, [0, 50, 0]), (1.15, [0, -45, 0], OQ),
                                 (SICKLE_CATCH, [0, -20, 0], IO), (1.95, [0, 10, 0], OC), (2.2, Z, IO))},
        'head': {'rotation': ch((0, Z), (0.6, wind['head'], IO), (1.15, [0, 20, 0], OQ), (SICKLE_CATCH, [0, 10, 0]), (2.2, Z, IO))},
        'right_arm': {'rotation': ch((0, Z), (0.6, wind['right_arm'], IO), (SICKLE_THROW, [-30, 40, 92]), (1.15, [-90, -35, -5], OQ),
                                     (1.65, [-80, -20, 10], IO), (SICKLE_CATCH, [-95, 0, 15], OC), (1.95, [-60, 20, 30], OC), (2.2, Z, IO))},
        'left_arm': {'rotation': ch((0, Z), (0.6, wind['left_arm'], IO), (1.15, [20, 0, -35], OQ), (2.2, Z, IO))},
        'right_leg': {'rotation': ch((0, Z), (0.6, [-20, 0, 5], IO), (1.15, [-30, 0, 5], OQ), (2.2, Z, IO))},
        'left_leg': {'rotation': ch((0, Z), (0.6, [15, 0, -5], IO), (1.15, [25, 0, -5], OQ), (2.2, Z, IO))},
    }, [(0.0, 'warn'), (SICKLE_THROW, 'throw'), (SICKLE_CATCH, 'catch')])
    an['cult_leader_ash_trail_dash'] = A(1.4, {
        'body': {'rotation': ch((0, Z), (0.4, [18, 0, 0], IO), (DASH_T, [38, 0, 0], OQ), (0.9, [38, 0, 0]), (1.05, [-8, 0, 0], OC), (1.4, Z, IO)),
                 'position': ch((0, Z), (0.4, [0, -3, 2], IO), (DASH_T, [0, -2, -2], OQ), (0.9, [0, -2, -2]), (1.05, [0, -1, 2], OC), (1.4, Z, IO))},
        'head': {'rotation': ch((0, Z), (0.4, [-15, 0, 0], IO), (DASH_T, [-30, 0, 0], OQ), (1.05, [5, 0, 0], OC), (1.4, Z, IO))},
        'right_arm': {'rotation': ch((0, Z), (0.4, [20, 10, 30], IO), (DASH_T, [45, 10, 25], OQ), (0.9, [45, 10, 25]), (1.05, [-40, 0, 30], OC),
                                     (1.4, Z, IO))},
        'left_arm': {'rotation': ch((0, Z), (0.4, [20, 0, -20], IO), (DASH_T, [50, 0, -15], OQ), (0.9, [50, 0, -15]), (1.05, [-30, 0, -40], OC),
                                    (1.4, Z, IO))},
        'right_leg': {'rotation': ch((0, Z), (0.4, [-30, 0, 0], IO), (DASH_T, [30, 0, 0], OQ), (0.9, [30, 0, 0]), (1.05, [-20, 0, 0], OC), (1.4, Z, IO))},
        'left_leg': {'rotation': ch((0, Z), (0.4, [20, 0, 0], IO), (DASH_T, [-45, 0, 0], OQ), (0.9, [-45, 0, 0]), (1.05, [15, 0, 0], OC), (1.4, Z, IO))},
    }, [(0.0, 'warn'), (DASH_T, 'dash'), (0.9, 'stop')])
    an['cult_leader_brand'] = A(1.2, {
        'torso': {'rotation': ch((0, Z), (0.3, [0, -20, 0], IO), (BRAND_T, [-5, -25, 0], OQ), (1.2, Z, IO))},
        'head': {'rotation': ch((0, Z), (0.3, [0, 20, 0], IO), (1.2, Z, IO))},
        'left_arm': {'rotation': ch((0, Z), (0.3, [-95, 15, -5], OC), (0.45, [-100, 15, -5]), (BRAND_T, [-85, 15, 0], OQ), (0.8, [-80, 10, 0]),
                                    (1.2, Z, IO))},
    }, [(BRAND_T, 'brand')])
    an['cult_leader_pillars'] = A(2.3, {
        'body': {'rotation': ch((0, Z), (0.3, [-8, 0, 0], OC), (1.6, [-10, 0, 0]), (PILLAR_ERUPT, [22, 0, 0], IQ), (2.3, Z, IO)),
                 'position': ch((0, Z), (1.6, Z), (PILLAR_ERUPT, [0, -4, 0], IQ), (2.3, Z, IO))},
        'head': {'rotation': ch((0, Z), (0.3, [-25, 0, 0], OC), (1.6, [-25, 0, 0]), (PILLAR_ERUPT, [15, 0, 0], IQ), (2.3, Z, IO))},
        'right_arm': {'rotation': ch((0, Z), (0.3, [-175, 0, -10], OC), (1.6, [-178, 0, -12]), (PILLAR_ERUPT, [-110, 40, 0], IQ),
                                     (2.0, [-115, 45, 0]), (2.3, Z, IO))},
        'left_arm': {'rotation': ch((0, Z), (0.3, [-175, 0, 10], OC), (1.6, [-178, 0, 12]), (PILLAR_ERUPT, [-80, 0, -10], IQ), (2.3, Z, IO))},
        'right_leg': {'rotation': ch((0, Z), (PILLAR_ERUPT, [-15, 0, 5], IQ), (2.3, Z, IO))},
        'left_leg': {'rotation': ch((0, Z), (PILLAR_ERUPT, [15, 0, -5], IQ), (2.3, Z, IO))},
    }, [(PILLAR_MARK, 'mark'), (PILLAR_ERUPT, 'erupt')])
    return an


# ================================================================== эффекты
def effects():
    E, ease, fx, at = F.E, F.ease, FX.fx, FX.at
    # Огненный серп: путь косы — петля вперёд и назад в осях взгляда: z = 6·(1 − cos 2πs), x = 4·sin 2πs (s 0…1)
    path = [(4 * math.sin(2 * math.pi * s), 6 * (1 - math.cos(2 * math.pi * s))) for s in [k / 18 for k in range(1, 18)]]
    warn = [E('decal', k // 2, at('caster', x, 0, z), duration=24 - k // 2, texture='glow', radius=0.9, glow=0.6, pulse=8, color='@primary',
              out=ease(4)) for k, (x, z) in enumerate(path)]
    fx('cult_sickle_warn', '«Огненный серп»: дуга-предупреждение на земле 1 с (caster = босс, yaw — взгляд). Путь косы-бумеранга в осях взгляда: '
       'z = 6·(1 − cos 2πs), x = 4·sin 2πs, s 0…1 (12 бл. вперёд, справа туда, слева обратно); бросок — событие throw (1.0 с).', 26, warn)
    fx('cult_sickle_spin', '«Огненный серп»: огненный след летящей косы (caster = сущность-коса, follow, до Fx.stop). Саму косу рисует код: '
       'предмет cult_scythe, вращение ~40°/тик.', -1, [
        E('trail', 0, 'caster', follow=True, width=0.6, length=8, fade=1, color='@primary'),
        E('aura', 0, 'caster', follow=True, target='caster', thickness=0.2, pulse=[0.3, 4], color='@secondary', motes=12, ring=False),
        E('sprites', 0, 'caster', follow=True, texture='mote_flame', count=100000, rate=1.5, spread=0.5, speed=0.02, gravity=-0.02,
          size=[0.4, 0.05], life=12, color='@secondary', glow=0.6),
    ])
    fx('cult_sickle_catch', '«Огненный серп»: коса вернулась в руку (событие catch).', 8, [
        E('flash', 0, 'caster.hand', duration=8, size=1.3, color='@secondary'),
        E('sprites', 0, 'caster.hand', duration=2, texture='mote_flame', count=12, rate=8, spread=0.4, speed=0.1, size=[0.3, 0.04], life=10, color='@primary'),
    ])
    # Пепельный след: рывок 12 бл. по прямой (если код рвётся на другое расстояние — .scale(dist / 12))
    fx('cult_ash_trail_warn', '«Пепельный след»: линия рывка 0.5 с (caster = босс, yaw — направление; длина 12 бл.).', 12, [
        E('decal', 0, at('caster', 0, 0, 6), duration=12, shape='crack', length=12, width=0.9, grow=4, pulse=0.6, yaw=90, glow=0.5, color='@primary'),
    ])
    burn = [E('decal', 0, at('caster', 0, 0, 6), duration=80, shape='crack', length=12, width=1.8, grow=6, branches=8, yaw=90,
              blend='translucent', color=FX.SOOT, fadeOut=20),
            E('decal', 0, at('caster', 0, 0, 6), duration=80, shape='crack', length=12, width=1.4, grow=6, branches=6, yaw=90, glow=0.5,
              pulse=0.3, color='@primary', out=ease(16))]
    for z in range(1, 12, 2):
        burn.append(E('sprites', 2, at('caster', 0, 0.1, z), duration=76, texture='mote_flame', count=100000, rate=0.7, area=0.8, speed=0.01,
                      gravity=-0.03, size=[0.45, 0.06], life=18, color='@secondary', glow=0.5))
        burn.append(E('sprites', 2, at('caster', 0, 0.3, z), duration=76, texture='mote_ash', count=100000, rate=0.25, area=0.8, speed=0.01,
                      gravity=-0.01, spin=30, size=[0.25, 0.08], life=30, color=FX.ASH, blend='translucent'))
    fx('cult_ash_trail', '«Пепельный след»: горящая полоса 4 с за рывком (caster = точка начала рывка, yaw — направление, 12 бл., ширина ~1.6). '
       'Огонь не ставится; урон в полосе — код.', 80, burn)
    fx('cult_ash_trail_dash', '«Пепельный след»: шлейф пепла за боссом во время рывка (caster = босс, follow, 0.4 с).', 10, [
        E('sprites', 0, at('caster', 0, 1.0, 0), follow=True, duration=8, texture='mote_ash', count=100000, rate=6, spread=0.7, speed=0.02,
          spin=60, size=[0.4, 0.12], life=20, color=FX.SOOT, blend='translucent'),
        E('aura', 0, 'caster', follow=True, duration=8, target='caster', thickness=0.25, color='@primary', motes=20, ring=False),
    ])
    # Клеймо культа: 3 с (60 тиков) → взрыв r3
    fx('cult_brand', '«Клеймо культа» на игроке (caster = игрок, follow, 60 тиков = 3 с, слать всем): клеймо над головой, по земле — кольцо r3 '
       '(зона взрыва — союзникам видно, куда не стоять), пульс учащается к 40 тику. На 60 — код: взрыв r3 и cult_brand_explode.', 60, [
        E('sigil', 0, at('caster', 0, 2.5, 0), follow=True, id='cult_brand'),
        E('decal', 0, 'caster', follow=True, duration=40, texture='cult_fire_ring', radius=3.0, glow=0.5, pulse=12, color='@primary'),
        E('decal', 40, 'caster', follow=True, duration=20, texture='cult_fire_ring', radius=3.0, glow=0.8, pulse=4, color='@secondary'),
        E('aura', 0, 'caster', follow=True, duration=60, target='caster', thickness=0.15, pulse=[0.3, 10], color='@primary', motes=8, ring=False),
    ])
    fx('cult_brand_explode', '«Клеймо культа»: взрыв r3 на месте меченого (caster = игрок).', 24, [
        E('flash', 0, at('caster', 0, 1, 0), duration=10, size=3.2, rays=8, screen=0.15, ring=True, color='@secondary'),
        E('wave', 0, 'caster', duration=12, shape='ring', radius=3.2, thickness=1.0, followTerrain=True, color='@primary'),
        E('column', 0, 'caster', duration=10, radius=1.2, height=4, fill=0.7, color='@primary', out=ease(6)),
        E('sprites', 0, at('caster', 0, 0.8, 0), duration=3, texture='mote_flame', count=50, rate=20, spread=1.4, speed=0.3, gravity=0.01,
          size=[0.6, 0.06], life=20, color='@primary', glow=0.6),
        E('decal', 2, 'caster', duration=22, texture='glow', radius=3, blend='translucent', color=FX.SOOT, fadeOut=14),
    ])
    # Столпы пламени: 5 кругов на 1.5 с (30 тиков), затем столбы
    fx('cult_pillar_warn', '«Столпы пламени»: круг-предупреждение 1.5 с (caster = точка столба, на земле). Код ставит 5 штук вокруг игроков '
       '(событие mark анимации), столб — через 30 тиков (событие erupt).', 30, [
        E('decal', 0, 'caster', duration=30, texture='cult_fire_ring', radius=1.6, grow=6, glow=0.6, pulse=8, color='@primary'),
        E('decal', 0, 'caster', duration=30, texture='higher_cracks', radius=1.4, grow=30, glow=0.4, color=FX.FIRE_DEEP),
        E('sprites', 0, at('caster', 0, 0.1, 0), duration=30, texture='mote_flame', count=100000, rate=0.6, area=1.4, speed=0.01, gravity=-0.02,
          size=[0.25, 0.04], life=14, color='@secondary'),
    ])
    fx('cult_pillar', '«Столпы пламени»: столб огня r1.4 высотой 9 (caster = точка; урон — код, 1 с).', 30, [
        E('column', 0, 'caster', duration=22, radius=1.4, height=9, fill=0.75, color='@primary', out=ease(10, 'easeInSine')),
        E('curtain', 0, 'caster', duration=22, radius=[0.3, 1.3], count=10, height=5, grow=4, width=[0.5, 1.0], brightness=[0.7, 1.0], flicker=0.6,
          texture='cult_flame_tongue', color='@secondary', out=ease(10)),
        E('flash', 0, at('caster', 0, 1, 0), duration=8, size=2.2, color='@secondary'),
        E('sprites', 0, at('caster', 0, 0.5, 0), duration=4, texture='mote_flame', count=30, rate=10, spread=1, speed=0.25, size=[0.5, 0.06],
          life=18, color='@primary', glow=0.6),
        E('decal', 2, 'caster', duration=28, texture='glow', radius=1.8, blend='translucent', color=FX.SOOT, fadeOut=16),
    ])


def sigils_icon():
    L, ap = F.L, F.ap
    F.sigil('cult_brand', 'T26 «Клеймо культа»: клеймо над головой меченого (лежит над головой, раскалено; знак культа, кольцо).',
            0.55, '#FF5A1E', 'ground', [
                L('glow', 'disc', 'glow', 1.2, -0.01, ap(0, 6, 'fade'), color=FX.FIRE_DEEP, br=0.8, pulse=(0.3, 10)),
                L('mark', 'disc', 'cult_emblem', 1.0, 0.0, ap(0, 8, 'grow', 'fade', easing='easeOutBack'), rot=4, br=1.3, pulse=(0.2, 6)),
            ], hold=-1, dissolve=('fade',), ddur=6)

    def draw(d, S):
        d.ellipse([S * 0.06, S * 0.06, S * 0.94, S * 0.94], fill=F._c('#2b1111'), outline=F._c('#ec0d00'), width=int(S * 0.08))
        cx, cy = S / 2, S / 2
        d.polygon(FX._flame_poly(cx, cy + S * 0.32, S * 0.5, S * 0.62), fill=F._c('#ff7a1e'))
        d.polygon(FX._flame_poly(cx, cy + S * 0.25, S * 0.3, S * 0.38), fill=F._c('#2b1111'))
        d.ellipse([cx - S * 0.17, cy - S * 0.07, cx + S * 0.17, cy + S * 0.07], fill=F._c('#ffd24a'))
        d.ellipse([cx - S * 0.05, cy - S * 0.05, cx + S * 0.05, cy + S * 0.05], fill=F._c('#2b1111'))
        for a in (-0.6, 0, 0.6):                                                        # три «зубца» тавра над знаком
            x = cx + math.sin(a) * S * 0.36
            y = cy - math.cos(a) * S * 0.36
            d.ellipse([x - S * 0.05, y - S * 0.05, x + S * 0.05, y + S * 0.05], fill=F._c('#ffd24a'))
    F._icon(18, draw, 'textures/mob_effect/cult_brand.png', k=8, crisp=True)


LANG = {
    'ui.pohsmp_core.cult_leader.sickle': ('Огненный серп', 'Fiery Sickle'),
    'ui.pohsmp_core.cult_leader.ash_trail': ('Пепельный след', 'Ash Trail'),
    'ui.pohsmp_core.cult_leader.brand': ('Клеймо культа', 'Cult Brand'),
    'ui.pohsmp_core.cult_leader.brand_warn': ('На вас Клеймо культа — отойдите от союзников!', 'You bear the Cult Brand — move away from allies!'),
    'ui.pohsmp_core.cult_leader.pillars': ('Столпы пламени', 'Pillars of Flame'),
    'effect.pohsmp_core.cult_brand': ('Клеймо культа', 'Cult Brand'),
    'effect.pohsmp_core.cult_brand.description': ('Через 3 с клеймо взорвётся пламенем (r3) — держитесь подальше от союзников.',
                                                  'In 3 s the brand explodes in flame (r3) — keep away from allies.'),
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


def patch_anims():
    """Только добавить/обновить наши 4 анимации в готовом файле (без перегенерации остального)."""
    p = os.path.join(M.A, 'animations', 'entity', 'cult_leader.animation.json')
    d = json.load(open(p, encoding='utf-8'))
    d['animations'].update(anims())
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, separators=(',', ':'))


def run(mod, fxmod, args=()):
    global M, FX
    M, FX = mod, fxmod
    F.WRITTEN = M.WRITTEN
    effects()
    sigils_icon()
    lang()


def shots(three=None):
    import cult_leader_render as R
    cells = []
    for name, ts in (('cult_leader_sickle_throw', [(0.6, 'замах, дуга горит'), (1.15, 'бросок'), (1.85, 'поймал')]),
                     ('cult_leader_ash_trail_dash', [(0.4, 'присел'), (0.7, 'рывок')]),
                     ('cult_leader_brand', [(0.55, 'клеймо')]),
                     ('cult_leader_pillars', [(1.0, 'коса над головой, круги'), (1.85, 'удар — столбы')])):
        for t, lab in ts:
            cells.append({'model': 'cult_leader', 'anim': name, 't': t, 'yaw': 35, 'pitch': 8, 'dist': 2.4, 'ty': 18,
                          'label': name.replace('cult_leader_', ''), 'sub': '%.2g с — %s' % (t, lab)})
    R.sheet(os.path.join(HERE, '..', 'docs', 'media', 't26_spells4_anims.jpg'), {'cols': 4, 'cells': cells}, three, (1600, 760))


if __name__ == '__main__':
    import gen_cult_leader as GM
    import gen_cult_leader_fx as GFX
    GFX.M = GM
    run(GM, GFX)
    M = GM
    patch_anims()
    if '--shots' in sys.argv:
        shots(sys.argv[sys.argv.index('--three') + 1] if '--three' in sys.argv else None)
    print('\n'.join('  ' + w for w in GM.WRITTEN))
