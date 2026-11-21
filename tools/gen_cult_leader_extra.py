#!/usr/bin/env python3
"""
T26 — дополнения управляющего (20.11): анимации босса (GeckoLib), особые заклинания «Первое Пламя» и «Пепел Меллисто»,
реакция на «Дезинтеграцию: Реплику», добивание, полоса здоровья по фазам. Вызывается из gen_cult_leader_fx.run().

Анимации: assets/pohsmp_core/animations/entity/cult_leader.animation.json = ВСЕ анимации casting_animations.json Iron's (те же имена —
логика FireBoss их ищет) + наши cult_leader_*. Модели босса подменить getAnimationResource на этот файл.
Оси анимаций (как у Iron's): rotation x минус — рука вперёд/вверх (−90 вперёд, −180 вверх), right_arm z плюс — в сторону вправо,
left_arm z минус — влево; body x плюс — наклон вперёд; position в пикселях модели (z минус — вперёд, y минус — ниже).
"""
import json
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from gen_sigil_textures import C, SS, canvas, polar, ring  # noqa: E402
import gen_forbidden_fx as F  # noqa: E402

M = FX = None
HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.join(HERE, '..', 'docs', 'media')
REPLICA = '#FF1934'


# ================================================================== анимации GeckoLib
def ch(*keys):
    """Канал: ключи (t, [x, y, z], easing?) → {"t": {"vector": …, "easing": …}}."""
    o = {}
    for k in keys:
        t, v = k[0], k[1]
        e = {'vector': [round(x, 3) for x in v]}
        if len(k) > 2 and k[2]:
            e['easing'] = k[2]
        o['%.4g' % t if t else '0.0'] = e
    return o


def A(length, bones, timeline=None):
    o = {'animation_length': length, 'bones': bones}
    if timeline:
        o['timeline'] = {('%.4g' % t): v for t, v in timeline}
    return o


Z = [0, 0, 0]
ONE = [1, 1, 1]
# Поза хвата = поза Тироса (владелец 21.11: «держит косу как Тирос Iron's, везде»): FireBossModel Iron's вне анимаций —
# pushRotation(right_arm, −30, −30, 10), (bipedHandRight, −5, 0, −48) в осях модели = (30, 30, 10) / (5, 0, −48) в осях анимаций
# (GeckoLib при загрузке ключей меняет знак X/Y поворота). Тот же поворот кисти — в анимациях Iron's (их ключи не трогаем).
# Внимание: GeckoLib поворачивает предмет кистью ДВАЖДЫ (BlockAndItemGeoLayer) — ключи кисти в наших анимациях задаются видимым
# поворотом через anim_cloth.V(...) (в файл пишется половина). Прежняя поза «несёт косу» (рука −25,10,15 / кисть 0,−5.5,96) была
# подобрана по превью с одним поворотом: в игре кисть 96° давала ~192° — коса стояла боком, лезвие у головы.
# Коса сдвинута в кулаке на 3 px вдоль древка к лезвию-вверх (CARRY_POS, ориентация та же): у Тироса в покое лезвие на 0.7 px
# ниже земли при покачивании руки, в ходьбе — на 3.4 px; со сдвигом и без качания правой руки при ходьбе — 0.8 px над землёй.
CARRY_ARM, CARRY_HAND, CARRY_POS = [30, 30, 10], [5, 0, -48], [-0.96, 0.09, 2.84]
from anim_cloth import V  # noqa: E402
IO, OC, IQ = 'easeInOutSine', 'easeOutCubic', 'easeInQuart'


def boss_anims():
    an = {}
    # «Первое Пламя» (6 с): 0.9 — коса в землю, 1.6 — рука к небу (печать), 4.0 — столб падает (рывок), 6.0 — обратно
    an['cult_leader_first_flame'] = A(6.0, {
        'body': {'rotation': ch((0, Z), (0.5, [15, 0, 0], IO), (1.0, [5, 0, 0], IO), (1.6, [-6, 0, 0], IO), (3.95, [-6, 0, 0]),
                                (4.1, [8, 0, 0], OC), (4.6, [0, 0, 0], IO), (6.0, Z)),
                 'position': ch((0, Z), (0.5, [0, -3, 0], IO), (1.0, [0, -1, 0], IO), (1.6, Z, IO), (6.0, Z))},
        'torso': {'rotation': ch((0, Z), (1.6, [-8, -10, 0], IO), (4.0, [-8, -10, 0]), (4.1, [6, -10, 0], OC), (5.2, [0, -6, 0], IO), (6.0, Z, IO))},
        'head': {'rotation': ch((0, Z), (0.9, [15, 0, 0], IO), (1.6, [-35, 0, 0], OC), (3.95, [-38, 0, 0]), (4.1, [-5, 0, 0], OC),
                                (4.6, [10, 0, 0], IO), (6.0, Z, IO))},
        'right_arm': {'rotation': ch((0, Z), (0.5, [-150, 20, 10], IO), (0.9, [-117, 47, -1], IQ), (5.2, [-117, 47, -1]), (6.0, Z, IO))},
        'left_arm': {'rotation': ch((0, Z), (0.9, [-20, 0, -10], IO), (1.6, [-170, -5, 10], OC), (3.95, [-176, -5, 16]),
                                    (4.1, [-150, 0, 30], OC), (5.2, [-165, 0, 10], IO), (6.0, Z, IO))},
        'right_leg': {'rotation': ch((0, Z), (0.5, [-15, 0, 5], IO), (5.2, [-15, 0, 5]), (6.0, Z, IO))},
        'left_leg': {'rotation': ch((0, Z), (0.5, [12, 0, -5], IO), (5.2, [12, 0, -5]), (6.0, Z, IO))},
    }, [(0.9, 'plant'), (1.6, 'sigil'), (4.0, 'pillar')])
    # «Пепел Меллисто»: рассыпание (1.2 с) → [вихрь 1.8 с, модель скрыта] → сборка (1.0 с) → разрез (1.5 с, удар 0.5)
    windup = {'body': ([20, 0, 0], [0, -3, 0]), 'torso': [0, 35, 0], 'head': [10, -30, 0], 'right_arm': [-40, 30, 80], 'left_arm': [-70, 0, -20],
              'right_leg': [-25, 0, 5], 'left_leg': [20, 0, -5]}
    an['cult_leader_ash_dissolve'] = A(1.2, {
        'body': {'scale': ch((0, ONE), (0.5, [1.06, 1.06, 1.06], IO), (1.2, [0.02, 0.02, 0.02], 'easeInCubic')),
                 'position': ch((0, Z), (1.2, [0, 6, 0], 'easeInCubic'))},
        'head': {'rotation': ch((0, Z), (0.35, [-30, 0, 0], OC))},
        'right_arm': {'rotation': ch((0, Z), (0.35, [-20, 0, 60], OC), (1.2, [-30, 0, 80], IO))},
        'left_arm': {'rotation': ch((0, Z), (0.35, [-20, 0, -60], OC), (1.2, [-30, 0, -80], IO))},
    }, [(0.0, 'ignite'), (1.2, 'gone')])
    an['cult_leader_ash_reform'] = A(1.0, {
        'body': {'scale': ch((0, [0.02, 0.02, 0.02]), (0.6, [1.08, 1.08, 1.08], OC), (1.0, ONE, IO)),
                 'rotation': ch((0, Z), (1.0, windup['body'][0], IO)), 'position': ch((0, [0, 6, 0]), (0.6, Z, OC), (1.0, windup['body'][1], IO))},
        'torso': {'rotation': ch((0, Z), (1.0, windup['torso'], IO))},
        'head': {'rotation': ch((0, Z), (1.0, windup['head'], IO))},
        'right_arm': {'rotation': ch((0, [-30, 0, 80]), (1.0, windup['right_arm'], IO))},
        'left_arm': {'rotation': ch((0, [-30, 0, -80]), (1.0, windup['left_arm'], IO))},
        'right_leg': {'rotation': ch((0, Z), (1.0, windup['right_leg'], IO))},
        'left_leg': {'rotation': ch((0, Z), (1.0, windup['left_leg'], IO))},
    }, [(0.0, 'reform'), (1.0, 'ready')])
    an['cult_leader_ash_slash'] = A(1.5, {
        'body': {'rotation': ch((0, windup['body'][0]), (0.42, [24, 0, 0], IO), (0.6, [10, -10, 0], 'easeOutQuart'), (1.5, Z, IO)),
                 'position': ch((0, windup['body'][1]), (0.42, [0, -3.5, 1], IO), (0.6, [0, -2, -7], 'easeOutQuart'), (1.5, Z, IO))},
        'torso': {'rotation': ch((0, windup['torso']), (0.42, [0, 40, 0], IO), (0.6, [5, -55, 0], 'easeOutQuart'), (1.0, [0, -45, 0], IO), (1.5, Z, IO))},
        'head': {'rotation': ch((0, windup['head']), (0.6, [5, 25, 0], 'easeOutQuart'), (1.5, Z, IO))},
        # коса (проверка 20.11): на slash лезвие идёт ПЕРЕД боссом справа налево низко над землёй — разрез вдоль линии вперёд
        # (раньше коса стояла вертикально над головой, лезвие в ноге/в земле)
        'right_arm': {'rotation': ch((0, windup['right_arm']), (0.42, [-62.5, 38.3, 55], IO), (0.5, [-66, 27, 5], 'easeOutQuart'),
                                     (0.6, [-61, -1, -5.6], 'easeOutQuart'), (1.0, [-70, -35, -5], IO), (1.5, Z, IO))},
        # slash (21.11): ключи кисти — в осях игры как есть (без V): по верной кинематике (двойной поворот) лезвие режет плоскостью
        # по ходу, остриё впереди (0°, +0.89); пересчёт через V и подбор давали скручивание косы на ударе (проверка рывков)
        'bipedHandRight': {'rotation': ch((0, Z), (0.42, [-7, 45.6, -45], IO), (0.5, [15.6, 55, -45.7], 'easeOutQuart'),
                                          (0.6, [16.3, 56.7, -49.6], 'easeOutQuart'), (1.0, [16.3, 56.7, -58], IO), (1.5, Z, IO))},
        'left_arm': {'rotation': ch((0, windup['left_arm']), (0.6, [20, 0, -40], 'easeOutQuart'), (1.5, Z, IO))},
        'right_leg': {'rotation': ch((0, windup['right_leg']), (0.6, [-35, 0, 5], 'easeOutQuart'), (1.5, Z, IO))},
        'left_leg': {'rotation': ch((0, windup['left_leg']), (0.6, [30, 0, -5], 'easeOutQuart'), (1.5, Z, IO))},
    }, [(0.5, 'slash')])
    # Реплика: 0.4 смотрит вверх, 0.9 сжимает верхние печати левой рукой (crush), 1.5 косой снизу вверх по печатям (shatter), 1.9 фраза
    an['cult_leader_replica_break'] = A(2.6, {
        'body': {'position': ch((0, Z), (0.9, [0, -1, 0], OC), (1.5, [0, 0, -1], OC), (2.6, Z, IO))},
        'torso': {'rotation': ch((0, Z), (0.4, [-5, 0, 0], IO), (1.2, [0, 30, 0], IO), (1.5, [-10, -30, 0], 'easeOutQuart'), (2.0, Z, IO), (2.6, Z))},
        'head': {'rotation': ch((0, Z), (0.4, [-25, 0, 0], IO), (0.9, [-10, 0, 0], OC), (1.5, [-20, -15, 0], OC), (1.9, [5, 0, 10], IO),
                                (2.4, [5, 0, 10]), (2.6, Z, IO))},
        'left_arm': {'rotation': ch((0, Z), (0.4, [-150, -10, 10], OC), (0.7, [-156, -10, 15], IO), (0.9, [-70, 0, -15], IQ), (1.2, [-40, 0, -10], IO),
                                    (1.9, [-30, 0, -45], IO), (2.3, [-25, 0, -40]), (2.6, Z, IO))},
        # коса (проверка 20.11): несёт её до 0.9, 1.2 — лезвие внизу справа впереди, 1.5 (shatter) — взмах снизу вверх ПЕРЕД собой
        # к печатям над головой (раньше лезвие уходило за спину)
        'right_arm': {'rotation': ch((0, Z), (0.3, CARRY_ARM, IO), (0.9, CARRY_ARM), (1.2, [-50.2, -13.2, 83.9], IO),
                                     (1.5, [-143.7, -13.5, -1.7], 'easeOutQuart'), (2.0, [-77.9, 1.5, 6.3], IO), (2.6, Z, IO))},
        'bipedHandRight': {'rotation': ch((0, Z), (0.3, CARRY_HAND, IO), (0.9, CARRY_HAND), (1.2, V([-20.1, -54.6, -3]), IO),
                                          (1.5, V([27.6, 0.7, 1.8]), 'easeOutQuart'), (2.0, V([12.1, 3.5, 0.8]), IO), (2.6, Z, IO))},
    }, [(0.9, 'crush'), (1.5, 'shatter'), (1.9, 'speak')])
    # Добивание (2.4 с): 0–0.7 тянет жертву левой рукой, 1.0 пронзает косой (impale), 1.0–1.7 поднимает, 1.7 вспышка, 2.2 смерть.
    # Разгон к impale — easeInQuad (21.11, проверка рывков: easeInQuart давал скорость косы 2300 °/с и остановку за кадр)
    an['cult_leader_finisher'] = A(2.4, {
        'body': {'rotation': ch((0, Z), (0.7, [0, 0, 0]), (1.0, [10, 0, 0], 'easeInQuad'), (1.7, [-5, 0, 0], IO), (2.4, Z, IO)),
                 'position': ch((0, Z), (1.0, [0, -1, -3], 'easeInQuad'), (1.7, Z, IO), (2.4, Z))},
        'torso': {'rotation': ch((0, Z), (0.7, [0, 25, 0], IO), (1.0, [10, -10, 0], 'easeInQuad'), (1.7, [-12, 0, 0], IO), (2.4, Z, IO))},
        'head': {'rotation': ch((0, Z), (0.3, [10, 0, 0], IO), (1.0, [5, 0, 0]), (1.7, [-25, 0, 0], IO), (2.2, [-25, 0, 0]), (2.4, Z, IO))},
        'left_arm': {'rotation': ch((0, Z), (0.3, [-90, 10, -5], OC), (0.7, [-55, 20, -20], IO), (1.0, [-45, 0, -12], IO), (2.4, Z, IO))},
        # коса (проверка 20.11, tools/anim_check.py): остриё — в груди жертвы перед боссом: 1.0 — 3.0 бл. вперёд на высоте груди,
        # 1.0–1.7 — поднимает её на +2.3 бл. (как код двигает жертву), держит до kill; раньше на 1.7–2.2 коса уходила за голову
        'right_arm': {'rotation': ch((0, Z), (0.7, [-30, 10, 60], IO), (1.0, [-86, -2.5, 1], 'easeInQuad'), (1.35, [-108, 4.4, -2.2], 'easeInOutQuad'),
                                     (1.7, [-117, 2, -3], 'easeInOutQuad'), (2.2, [-124, 0, -2]), (2.4, [-40, 0, 15], IO))},
        # кисть на impale (21.11): ключ в осях игры (без V), подобран по метрике ударов Тироса — лезвие входит остриём вперёд, плоскость
        # лезвия по ходу (было: плашмя, 67°, остриё назад); остриё там же, в груди жертвы; ключи подъёма повёрнуты так же
        'bipedHandRight': {'rotation': ch((0, Z), (0.7, Z), (1.0, [8.2, 66.2, 23.9], 'easeInQuad'), (1.35, [5.31, 69.01, 12.91], 'easeInOutQuad'),
                                          (1.7, [7.17, 69.5, 17.76], 'easeInOutQuad'), (2.2, [13.49, 68.91, 23.38]), (2.4, Z, IO))},
        'right_leg': {'rotation': ch((0, Z), (1.0, [20, 0, 0], 'easeInQuad'), (1.7, [5, 0, 0], IO), (2.4, Z, IO))},
        'left_leg': {'rotation': ch((0, Z), (1.0, [-25, 0, 0], 'easeInQuad'), (1.7, [-5, 0, 0], IO), (2.4, Z, IO))},
    }, [(0.7, 'pull_done'), (1.0, 'impale'), (1.7, 'flame'), (2.2, 'kill')])
    import gen_cult_leader_spells4 as S4                       # «+4 заклинания» (Огненный серп, Пепельный след, Клеймо, Столпы)
    an.update(S4.anims())
    return an


def write_anims():
    src = M.jar_json(M.I + 'animations/casting_animations.json')
    ours = boss_anims()
    out = {'format_version': src['format_version'], 'geckolib_format_version': src['geckolib_format_version'],
           'comment': 'T26: все анимации casting_animations.json Iron\'s (те же имена — их зовёт логика FireBoss) + cult_leader_* (наши). '
                      'Сгенерировано tools/gen_cult_leader.py — правьте генератор.',
           'animations': {**src['animations'], **ours}}
    # проверка анимаций 20.11 (tools/anim_check.py): явные ключи костей у наших анимаций; плащ (cape) — назад и мимо ног во всех
    import anim_cloth
    anim_cloth.explicit(out['animations'], list(ours), ('body', 'torso', 'head', 'right_arm', 'left_arm', 'right_leg', 'left_leg',
                                                        'bipedHandRight'))
    anim_cloth.bake('cult_leader', out['animations'])
    print('  удары без толчка (easing):', anim_cloth.strike_ease(out['animations'], list(ours)))
    # коса: все анимации, что играют на боссе (наши + удары FireBoss и касты Iron's), начинаются и кончаются в позе хвата; в кадрах,
    # где лезвие в земле или сквозь тело/ноги, — наименьший доворот кисти (три прохода: следующие добирают плавные переходы прежних)
    import anim_check
    plays = list(ours) + [n for n in anim_check.PLAYS['cult_leader'] if n in src['animations']]
    # fire_boss_spawn: на 6.42 с коса возникает в руке, влетая из точки сбоку-снизу (21, −6, 0) — лезвие проходило сквозь землю;
    # влетает сбоку-сверху (10, 10, 0), время то же
    out['animations']['fire_boss_spawn']['bones']['bipedHandRight']['position']['6.4167']['vector'] = [10, 10, 0]
    # короткие касты Iron's (< 0.5 с): правая рука с косой не дёргается вверх на долю секунды — держит косу, кастует левая
    still = [n for n in anim_check.SPELL_ANIMS if n in out['animations'] and float(out['animations'][n]['animation_length']) < 0.5]
    # «Пепел Меллисто» — цепочка: рассыпание → (вихрь, модель скрыта) → сборка → разрез; сборка кончается замахом, разрез с него
    # начинается — эти стыки не через позу хвата (иначе «замах → хват → замах»)
    hold = anim_cloth.hold_additive(out['animations'], plays, CARRY_ARM, CARRY_HAND, hand_pos=CARRY_POS,
                                    no_end=('fire_boss_death', 'cult_leader_ash_dissolve', 'cult_leader_ash_reform'),
                                    no_start=('cult_leader_ash_reform', 'cult_leader_ash_slash'), still=still)
    print('  поза хвата всю анимацию:', sorted(n for n, v in hold.items() if v != 'edges'))
    # поправки косы ниже начинаются с нуля на первом кадре (там поза кода) — кроме цепочки «Пепла» и коротких кастов (у них корпус
    # Iron's с первого кадра в позе каста — скачок корпуса и так есть, в игре у Тироса тоже)
    fs = ('cult_leader_ash_reform', 'cult_leader_ash_slash', *still)
    ag = {'cult_leader_first_flame': (0.9, 5.2)}
    # коса в земле/сквозь тело (проверка рывков 21.11): плавный сдвиг косы в кулаке (anim_cloth.smooth_clear), поворот косы —
    # как в анимации; прежние weapon/nudge меняли поправку ступеньками каждые 0.025 с — коса дёргалась
    print('  коса: плавный сдвиг', anim_cloth.smooth_clear('cult_leader', out['animations'], plays, allow_ground=ag, free_start=fs))
    print('  коса: плавный доворот (где сдвига нет)', anim_cloth.smooth_clear('cult_leader', out['animations'], plays, allow_ground=ag, free_start=fs,
                                                                             kind='rot'))
    for _ in range(2):
        print('  коса: плавный сдвиг (добор)', anim_cloth.smooth_clear('cult_leader', out['animations'], plays, allow_ground=ag, free_start=fs))
        print('  коса: плавный доворот (добор)', anim_cloth.smooth_clear('cult_leader', out['animations'], plays, allow_ground=ag, free_start=fs,
                                                                       kind='rot'))
    with open(M.out('animations/entity/cult_leader.animation.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    return ours


# ================================================================== поза жертвы добивания (PlayerAnimator) — в gen_player_anims.py
# (функция cult_finisher_victim там; здесь только напоминание об именах)


# ================================================================== текстуры особых заклинаний
def tex_first_flame():
    """«Первое Пламя» — печать над ареной (sky, r22): обод из 24 языков наружу, кольцо рун, 12 лучей, гексаграмма, в центре — пламя-первоогонь."""
    img = canvas()
    d = ImageDraw.Draw(img)
    rng = random.Random(4011)
    ring(d, C * 0.9, 6 * SS)
    ring(d, C * 0.87, 2 * SS)
    for i in range(24):
        a = 2 * math.pi * i / 24
        bx, by = polar(C * 0.89, a)
        d.polygon(FX._flame_poly(bx, by, C * 0.07, C * (0.1 if i % 2 else 0.065), ang=a + math.pi / 2, lean=0.2), fill=255)
    ring(d, C * 0.80, 3 * SS)
    for i in range(48):
        F._polar_glyph(d, C * 0.755, 2 * math.pi * i / 48, C * 0.06, C * 0.035, rng, 3 * SS)
    ring(d, C * 0.705, 3 * SS)
    for i in range(12):
        a = 2 * math.pi * i / 12
        x0, y0 = polar(C * 0.3, a)
        x1, y1 = polar(C * 0.69, a)
        nx, ny = -math.sin(a), math.cos(a)
        w = C * (0.03 if i % 2 == 0 else 0.016)
        d.polygon([(x0 + nx * w, y0 + ny * w), (x1, y1), (x0 - nx * w, y0 - ny * w)], fill=255)
    for s in (0, math.pi / 6):
        pts = [polar(C * 0.55, s + 2 * math.pi * k / 6 - math.pi / 2) for k in range(6)]
        for k in range(6):
            d.line([*pts[k], *pts[(k + 2) % 6]], fill=255, width=int(3 * SS))
    ring(d, C * 0.3, 5 * SS)
    d.polygon(FX._flame_poly(C, C + C * 0.2, C * 0.34, C * 0.44), fill=255)
    d.polygon(FX._flame_poly(C, C + C * 0.16, C * 0.2, C * 0.28), fill=0)
    d.polygon(FX._flame_poly(C, C + C * 0.12, C * 0.1, C * 0.15), fill=255)
    FX._save_sigil(img, 'cult_first_flame')


def tex_fire_ring():
    """Рисунок для `wave.texture`: кольцо огня у самого края (языки наружу) — растёт вместе с волной «Первого Пламени»."""
    img = canvas()
    d = ImageDraw.Draw(img)
    ring(d, C * 0.955, 9 * SS)
    for i in range(96):
        a = 2 * math.pi * i / 96 + (i % 3) * 0.01
        bx, by = polar(C * 0.95, a)
        h = C * (0.045 if i % 2 else 0.03)
        d.polygon(FX._flame_poly(bx, by, C * 0.03, h, ang=a + math.pi / 2, lean=0.3 if i % 4 < 2 else -0.3), fill=255)
    FX._save_sigil(img, 'cult_fire_ring')


# ================================================================== печати и эффекты особых заклинаний
def sigils():
    L, T, ap = F.L, F.T, F.ap
    F.sigil('cult_first_flame', 'T26 «Первое Пламя»: огромная печать над центром арены (sky, r22). Прорисовывается 1.6–3.0 с ролика, держится до '
                                'падения столба (4.0 с), затем гаснет. Сгенерировано tools/gen_cult_leader.py.', 22, FX.FIRE, 'sky', [
        L('glow', 'disc', 'glow', 1.0, 0.0, ap(0, 30, 'fade'), color=FX.FIRE_DEEP, br=0.5, pulse=(0.15, 20)),
        L('seal', 'disc', 'cult_first_flame', 1.0, 0.01, ap(0, 28, 'draw', 'twist', twist=60, startAngle=90, easing='easeOutCubic'), rot=0.6, boost=4),
        T('name', 'ПЕРВОЕ ПЛАМЯ ✦ ОГОНЬ ДО НАЧАЛА ✦ ', 0.985, 0.04, 0.02, ap(10, 24, 'draw', easing='linear'), font='cyrillic',
          color=FX.FIRE_HOT, br=0.9, rot=-0.4, repeat=4),
        L('arcs', 'arcs', 'arc_strip', 1.08, 0.03, ap(20, 14, 'assemble', 'fade'), count=8, arcLength=30, width=0.012, rot=1.5,
          color=FX.FIRE_HOT, br=1.1),
    ], hold=-1, flash={'color': FX.FIRE_HOT, 'size': 1.1, 'duration': 16, 'sparks': 160}, dissolve=('shatter', 'fade'), ddur=24)
    F.sigil('cult_replica_cracks', 'T26: трещины по печати «Реплики» перед тем, как босс её сломает (ставить в те же точки, что печати Реплики: '
                                   '+4.8 верхняя, +2.4 ярус, 0 поле). Цвет Реплики.', 1.25, REPLICA, 'ground', [
        L('cracks', 'disc', 'higher_cracks', 1.0, 0.012, ap(0, 8, 'draw', startAngle=0, easing='easeOutCubic'), br=1.3),
    ], hold=-1, dissolve=('shatter',), ddur=10)


def effects():
    E, ease, fx, at = F.E, F.ease, FX.fx, FX.at
    C_ = 'point:center'
    # ---------------------------------------------------------------- «Первое Пламя» (6 с = 120 тиков; анимация cult_leader_first_flame)
    fx('cult_first_flame', '«Первое Пламя» (фаза 2, раз за бой). caster = босс, point:center = центр арены (точка появления). '
       '0.9 с (18) — коса в землю: трещины и вспышка у босса; 1.6 с (32) — над центром на +26 раскрывается печать; 2.0–4.0 с (40–80) — '
       'ПРЕДУПРЕЖДЕНИЕ: центр трескается, кольцо подсвечено, с печати сыплются искры; 4.0 с (80) — столб пламени в центр, '
       'от него по земле бежит кольцо огня 3→28 бл. за 2 с (80–120; урон — код: |d − r(t)| < 0.8 и игрок ниже 1 бл. над землёй, '
       'r(t) = 3 + 25·(t − 80)/40). Бой не замораживается.', 130, [
        E('aura', 0, 'caster', duration=34, target='caster', thickness=0.22, pulse=[0.3, 8], color='@primary', motes=30, follow=True),
        E('flash', 18, at('caster', 1.05, 0.2, 2.1), duration=8, size=1.6, color='@secondary', comment='коса входит в землю'),
        E('decal', 18, at('caster', 1.05, 0, 2.1), duration=110, texture='higher_cracks', radius=4, grow=10, glow=0.5, fadeOut=30, color=FX.FIRE_DEEP),
        E('sigil', 32, at(C_, 0, 26, 0), id='cult_first_flame'),
        E('tint', 30, C_, duration=100, radius=44, color='#5A1406', strength=0.32, **{'in': ease(30), 'out': ease(30)}),
        E('sprites', 40, at(C_, 0, 24, 0), duration=40, texture='mote_flame', count=100000, rate=2.0, area=18, speed=0.0, gravity=0.03,
          size=[0.35, 0.08], life=34, color='@secondary', glow=0.6, comment='с печати сыплются искры (предупреждение)'),
        E('decal', 40, C_, duration=90, texture='higher_cracks', radius=8, grow=40, glow=0.6, pulse=10, fadeOut=30, color=FX.FIRE,
          comment='центр арены трескается'),
        E('decal', 40, C_, duration=40, texture='cult_fire_ring', radius=3.4, glow=0.6, pulse=8, color='@secondary',
          comment='кольцо подсвечено там, откуда оно побежит'),
        E('wave', 40, C_, duration=20, shape='ring', radius=28, thickness=0.6, reverse=True, followTerrain=True, color='@primary', brightness=0.5),
        E('wave', 60, C_, duration=20, shape='ring', radius=28, thickness=0.6, reverse=True, followTerrain=True, color='@primary', brightness=0.6),
        E('column', 80, C_, duration=24, radius=3.0, height=26, fill=0.8, color='@secondary', out=ease(12, 'easeInSine'), comment='СТОЛБ'),
        E('flash', 80, at(C_, 0, 2, 0), duration=16, size=8, rays=14, screen=0.35, ring=True, color='@secondary'),
        E('wave', 80, C_, duration=40, shape='ring', radius=28, thickness=1.2, texture='cult_fire_ring', spin=0.5, followTerrain=True,
          color='@primary', brightness=1.2, comment='кольцо огня по земле: 3 → 28 бл. за 40 тиков (перепрыгнуть)'),
        E('sprites', 80, at(C_, 0, 1, 0), duration=8, texture='mote_flame', count=160, rate=20, spread=3, speed=0.4, gravity=0.01,
          size=[0.8, 0.1], life=30, color='@primary', glow=0.7),
        E('decal', 82, C_, duration=48, texture='glow', radius=6, blend='translucent', color=FX.SOOT, fadeOut=30),
    ])
    # ---------------------------------------------------------------- «Пепел Меллисто»
    fx('cult_ash_dissolve', '«Пепел Меллисто», 0–1.2 с: босс сгорает в пепел (с анимацией cult_leader_ash_dissolve; caster = босс).', 34, [
        E('flash', 0, at('caster', 0, 2.8, 0), duration=10, size=3.4, color='@secondary'),
        E('aura', 0, 'caster', duration=24, target='caster', thickness=0.3, pulse=[0.4, 4], color='@primary', motes=40, follow=True),
        E('vortex', 4, 'caster', duration=26, radius=2.6, height=6.5, arms=3, speed=10, texture='mote_ash', color=FX.SOOT, out=ease(8)),
        E('sprites', 6, at('caster', 0, 2.1, 0), duration=18, texture='mote_ash', count=100000, rate=6, spread=1.5, speed=0.06, gravity=-0.02,
          spin=60, size=[0.4, 0.12], life=36, color=FX.SOOT, blend='translucent'),
        E('sprites', 6, at('caster', 0, 2.1, 0), duration=18, texture='mote_flame', count=100000, rate=3, spread=1.5, speed=0.08, gravity=-0.02,
          size=[0.3, 0.04], life=20, color='@primary'),
    ])
    fx('cult_ash_vortex', '«Пепел Меллисто», 1.2–3.0 с: пепельный вихрь проносится по арене (caster = невидимый босс, follow; до Fx.stop).', -1, [
        E('vortex', 0, 'caster', follow=True, radius=2.8, height=6.8, arms=4, speed=14, texture='mote_ash', color=FX.SOOT),
        E('vortex', 0, 'caster', follow=True, radius=1.9, height=5.6, arms=3, speed=-10, texture='mote_flame', color='@primary'),
        E('sprites', 0, at('caster', 0, 0.3, 0), follow=True, texture='mote_ash', count=100000, rate=3, spread=1.2, speed=0.02, gravity=-0.01,
          spin=50, size=[0.3, 0.1], life=40, color=FX.ASH, blend='translucent', comment='шлейф пепла за вихрем'),
    ])
    fx('cult_ash_reform', '«Пепел Меллисто», 3.0–4.0 с: пепел стягивается в фигуру перед сильнейшим врагом (caster = босс, анимация cult_leader_ash_reform).', 24, [
        E('vortex', 0, 'caster', duration=18, radius=3.4, height=6.8, arms=4, speed=-16, pull=1.0, texture='mote_ash', color=FX.SOOT, out=ease(4)),
        E('sprites', 0, at('caster', 0, 2.1, 0), duration=14, texture='mote_flame', count=100000, rate=4, spread=3.2, speed=-0.08, size=[0.3, 0.05],
          life=14, color='@primary'),
        E('flash', 18, at('caster', 0, 2.4, 0), duration=8, size=3.0, color='@secondary'),
    ])
    fx('cult_ash_line', '«Пепел Меллисто», 3.0–4.5 с: огненная линия на земле — траектория разреза (caster = босс, yaw = направление удара). '
       'Горит 1.5 с (30 тиков) до удара, пульсирует; длина 56 бл. (через всю арену), ширина зоны урона — код (предл. 1.5 бл.).', 34, [
        E('decal', 0, at('caster', 0, 0, 28), duration=34, shape='crack', length=56, width=1.4, grow=8, branches=10, pulse=0.6, yaw=90,
          glow=0.6, color='@primary', out=ease(4)),
        E('sprites', 0, at('caster', 0, 0.1, 14), duration=30, texture='mote_flame', count=100000, rate=1.2, area=2, speed=0.01, gravity=-0.02,
          size=[0.3, 0.05], life=20, color='@secondary'),
        E('sprites', 0, at('caster', 0, 0.1, 40), duration=30, texture='mote_flame', count=100000, rate=1.2, area=2, speed=0.01, gravity=-0.02,
          size=[0.3, 0.05], life=20, color='@secondary'),
    ])
    slash = [E('slash', 0, at('caster', 0, 2.1, 2.6), radius=6.3, arc=170, thickness=0.55, bend=1, secondary=0.6, tilt=0, grow=4, life=12,
               color='@secondary', comment='взмах косой (удар 4.5 с)'),
             E('flash', 0, at('caster', 0, 2.1, 3.5), duration=10, size=4, rays=8, screen=0.2, color='@secondary'),
             E('decal', 2, at('caster', 0, 0, 28), duration=200, shape='crack', length=56, width=1.2, grow=10, branches=14, yaw=90,
               blend='translucent', color=FX.SOOT, fadeOut=80, comment='выжженный след разреза')]
    for k in range(14):                                                  # огонь вырывается по линии, волной от босса
        z = 2 + k * 4
        slash.append(E('column', 1 + k // 2, at('caster', 0, 0, z), duration=12, radius=0.9, height=3.4, fill=0.7, color='@primary', out=ease(6)))
        slash.append(E('sprites', 1 + k // 2, at('caster', 0, 0.3, z), duration=3, texture='mote_flame', count=10, rate=4, spread=0.8, speed=0.2,
                       size=[0.5, 0.06], life=16, color='@secondary', glow=0.6))
    fx('cult_ash_slash', '«Пепел Меллисто», 4.5 с: огненный разрез через всю арену по линии cult_ash_line (caster = босс, yaw — тот же). '
       'Огонь вырывается по линии волной за 7 тиков. Урон — в момент события slash анимации cult_leader_ash_slash.', 40, slash)
    # ---------------------------------------------------------------- Реплика
    fx('cult_leader_replica_break', 'Босс ломает «Дезинтеграцию: Реплику» (caster = босс, анимация cult_leader_replica_break, 52 тика). '
       '10 — трещины бегут по печатям Реплики; 18 (crush) — верхние печати (+4.8, +2.4) лопаются: код Fx.stop(экземпляр Реплики), '
       'здесь — осколки; 30 (shatter) — разрез косой снизу вверх: остатки поля и венца рассыпаются, осколки падают. Цвет — Реплики.', 56, [
        E('sigil', 10, at('caster', 0, 4.82, 0), id='cult_replica_cracks', scale=1.0),
        E('sigil', 10, at('caster', 0, 2.42, 0), id='cult_replica_cracks', scale=0.72),
        E('sigil', 14, at('caster', 0, 0.06, 0), id='cult_replica_cracks', scale=0.95),
        E('flash', 18, at('caster', 0, 4.8, 0), duration=8, size=2.2, color=REPLICA),
        E('sprites', 18, at('caster', 0, 4.8, 0), duration=3, texture='spark_soft', count=60, rate=20, area=1.4, speed=0.18, gravity=0.03,
          spin=90, size=[0.22, 0.06], life=26, color=REPLICA, glow=0.6, comment='осколки верхней печати'),
        E('sprites', 19, at('caster', 0, 2.4, 0), duration=3, texture='spark_soft', count=40, rate=14, area=1.0, speed=0.15, gravity=0.03,
          size=[0.2, 0.05], life=24, color=REPLICA, glow=0.6),
        E('slash', 30, at('caster', 0.7, 4.0, 1.4), radius=4.5, arc=150, thickness=0.4, bend=1, tilt=70, grow=4, life=10, color='@secondary'),
        E('flash', 30, at('caster', 0, 6.5, 0), duration=10, size=3.2, rays=10, color=REPLICA),
        E('sprites', 30, at('caster', 0, 6.5, 0), duration=4, texture='spark_soft', count=90, rate=24, spread=2.2, speed=0.2, gravity=0.04,
          spin=120, size=[0.26, 0.06], life=34, color=REPLICA, glow=0.6, comment='венец и апекс рассыпаются'),
        E('wave', 30, 'caster', duration=16, shape='ring', radius=4, thickness=0.8, followTerrain=True, color=REPLICA),
        E('sprites', 32, at('caster', 0, 0.2, 0), duration=6, texture='mote_ash', count=24, rate=6, area=1.2, speed=0.03, gravity=-0.01,
          size=[0.25, 0.08], life=30, color=FX.ASH, blend='translucent'),
    ], style='cult_leader')
    # ---------------------------------------------------------------- добивание
    fx('cult_leader_finisher', 'Добивание (caster = босс, target = жертва; 48 тиков = анимация cult_leader_finisher 2.4 с). 0–14 огонь тянет '
       'жертву; 20 (impale) — коса пронзает: искры; 34 (flame) — жертва поднята на косе, вспышка пламени; 44 (kill) — смерть, пепел.', 56, [
        E('aura', 0, 'target', duration=20, target='target', thickness=0.2, pulse=[0.3, 5], color='@primary', motes=16, follow=True,
          comment='огненная хватка'),
        E('flash', 20, at('target', 0, 1.1, 0), duration=6, size=1.2, color='@secondary'),
        E('sprites', 20, at('target', 0, 1.1, 0), duration=3, texture='spark_soft', count=30, rate=12, spread=0.5, speed=0.2, gravity=0.02,
          size=[0.14, 0.03], life=14, color=FX.FIRE_HOT),
        E('flash', 34, at('target', 0, 1.2, 0), duration=14, size=3.4, rays=10, screen=0.15, ring=True, color=FX.FIRE_HOT,
          comment='вспышка пламени на поднятой жертве (follow — жертва уже поднята кодом)', follow=True),
        E('column', 34, 'target', duration=14, radius=0.8, height=3.5, fill=0.7, color='@primary', follow=True, out=ease(8)),
        E('sprites', 34, at('target', 0, 1.0, 0), duration=6, texture='mote_flame', count=50, rate=12, spread=0.8, speed=0.22, gravity=-0.01,
          size=[0.6, 0.06], life=22, color='@primary', glow=0.7, follow=True),
        E('sprites', 44, at('target', 0, 1.0, 0), duration=8, texture='mote_ash', count=40, rate=8, spread=0.6, speed=0.04, gravity=-0.012,
          spin=40, size=[0.3, 0.1], life=40, color=FX.SOOT, blend='translucent'),
    ])


# ================================================================== полоса здоровья по фазам
PAL = {k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in {
    'A': '#491b10', 'B': '#2b1111', 'C': '#9c5e2c', 'D': '#e8e895', 'E': '#b9892e', 'F': '#ffffff', 'G': '#d6af39', 'H': '#733c25',
    'I': '#570400', 'J': '#4e0400', 'K': '#490400', 'L': '#400300', 'M': '#390300', 'N': '#6e0500', 'O': '#ec0d00', 'P': '#7c0700',
    'Q': '#890800', 'R': '#b90b00', 'S': '#bd0b00', 'T': '#ad0a00', 'U': '#730600', 'V': '#8c0700'}.items()}


def _recolor(img, mp, rows=None):
    a = np.asarray(img).copy()
    inv = {v: k for k, v in PAL.items()}
    for y in (rows if rows is not None else range(a.shape[0])):
        for x in range(a.shape[1]):
            p = tuple(int(v) for v in a[y, x, :3])
            k = inv.get(p)
            if a[y, x, 3] and k in mp:
                a[y, x, :3] = PAL[mp[k]]
    return Image.fromarray(a, 'RGBA')


def bossbars(bar1):
    """Фаза 1 — cult_leader_bossbar (уже есть). Фаза 2 — руны запрета по рамке, пламя темнее, золотые знаки по краям; _p2_pulse — яркий кадр
    для пульса во время запрета. Фаза 3 — заливка ярче, с трещинами, рамка опалена; _p3_flames — 8 кадров языков огня над рамкой.
    _flash — силуэт полосы для вспышки при смене фазы."""
    full = list(range(18, 36))
    # ---- фаза 2
    p2 = _recolor(bar1, {'O': 'R', 'R': 'Q', 'V': 'P', 'D': 'G', 'F': 'D'}, full)             # пламя заливки темнее, блики приглушены
    d = ImageDraw.Draw(p2)
    for half in (0, 18):
        for x in range(14, 178, 10):                                                        # руны запрета по верхней кромке рамки
            if 78 <= x <= 114:
                continue
            g = (x // 10) % 3
            col = PAL['E']
            if g == 0:
                d.point((x, half + 8), fill=col + (255,)); d.point((x + 1, half + 8), fill=col + (255,)); d.point((x + 2, half + 8), fill=col + (255,))
                d.point((x + 1, half + 7), fill=PAL['B'] + (255,))
            elif g == 1:
                d.point((x, half + 8), fill=col + (255,)); d.point((x + 2, half + 8), fill=col + (255,)); d.point((x + 1, half + 7), fill=col + (255,))
            else:
                d.point((x + 1, half + 8), fill=PAL['D'] + (255,)); d.point((x, half + 7), fill=col + (255,)); d.point((x + 2, half + 7), fill=col + (255,))
            d.point((x + 1, half + 14), fill=PAL['C'] + (255,))                              # и по нижней
        for cx in (8, 183):                                                                 # золотые знаки по краям: ромб с перечёркнутым оком
            for (dx, dy, c) in ((0, -3, 'B'), (-1, -2, 'B'), (1, -2, 'B'), (0, -2, 'G'), (-2, -1, 'B'), (2, -1, 'B'), (-1, -1, 'G'), (1, -1, 'G'),
                                (0, -1, 'O'), (-1, 0, 'B'), (1, 0, 'B'), (0, 0, 'E'), (0, 1, 'B')):
                d.point((cx + dx, half + 5 + dy), fill=PAL[c] + (255,))
    p2.save(M.out('textures/gui/sprites/boss_bars/cult_leader_bossbar_p2.png'))
    pulse = _recolor(p2, {'E': 'G', 'G': 'D', 'C': 'E', 'A': 'H', 'Q': 'O', 'R': 'O', 'P': 'R', 'K': 'J', 'M': 'L'})
    pulse.save(M.out('textures/gui/sprites/boss_bars/cult_leader_bossbar_p2_pulse.png'))
    # ---- фаза 3
    p3 = _recolor(bar1, {'R': 'O', 'V': 'S', 'N': 'R', 'G': 'E', 'D': 'G', 'F': 'D'}, None)
    a = np.asarray(p3).copy()
    rng = random.Random(33)
    for half in (0, 18):
        for x in range(4, 188):                                                             # рамка опалена: местами тёмные пятна
            if rng.random() < 0.18:
                for y in (half + 8, half + 14):
                    if a[y, x, 3]:
                        a[y, x, :3] = PAL['H'] if rng.random() < 0.6 else PAL['C']
    for x0 in range(9, 186, 11):                                                            # трещины: тёмные изломы по раскалённой заливке
        if 84 <= x0 <= 108:
            continue
        x, y = x0 + rng.randrange(-2, 3), 28
        for step in range(3):
            if a[y, x, 3]:
                a[y, x, :3] = PAL['N'] if step else PAL['B']
                if x + 1 < 192 and a[y, x + 1, 3] and rng.random() < 0.5:
                    a[y, x + 1, :3] = PAL['D']                                              # раскалённый край трещины
            x += rng.choice((-1, 1))
            y += 1
    for x in range(3, 189):                                                                 # жар по верхней линии заливки
        if a[28, x, 3] and tuple(a[28, x, :3]) == PAL['O'] and rng.random() < 0.25:
            a[28, x, :3] = PAL['G']
    p3 = Image.fromarray(a, 'RGBA')
    p3.save(M.out('textures/gui/sprites/boss_bars/cult_leader_bossbar_p3.png'))
    # ---- языки огня: 8 кадров по 192×14 (полоса 192×112, кадр k — строки 14k…14k+13), рисовать над рамкой: низ кадра = строка 9 спрайта
    FH, NF = 14, 8
    fl = Image.new('RGBA', (192, FH * NF), (0, 0, 0, 0))
    fa = np.asarray(fl).copy()
    cols = [PAL['D'], PAL['G'], PAL['O'], PAL['R'], PAL['Q']]
    tongues = [(rng.uniform(4, 188), rng.uniform(2.5, 4.5), rng.uniform(5, 13), rng.random() * 6.28, rng.choice((-1, 1)))
               for _ in range(30)]
    for k in range(NF):
        t = k / NF * 2 * math.pi
        hmap = np.zeros(192)
        for (x0, w, H, p, sgn) in tongues:
            xc = x0 + sgn * 1.5 * math.sin(t + p)                                           # язык качается
            hh = H * (0.65 + 0.35 * math.sin(t * (1 + (int(p * 10) % 2)) + p))             # и дышит (период 8 или 4 кадра)
            if 80 <= xc <= 111:
                hh *= 0.4                                                                   # над знаком в центре — низко
            edge = min(xc - 2, 189 - xc)
            hh *= max(0.0, min(1.0, edge / 10))
            for x in range(max(2, int(xc - w)), min(190, int(xc + w) + 1)):
                hmap[x] = max(hmap[x], hh * (1 - abs(x - xc) / w) ** 0.8)
        for x in range(2, 190):
            h = int(round(min(FH, hmap[x])))
            for j in range(h):
                frac = j / max(1, h)
                c = cols[0] if frac < 0.2 else cols[1] if frac < 0.42 else cols[2] if frac < 0.66 else cols[3] if frac < 0.88 else cols[4]
                y = k * FH + FH - 1 - j
                fa[y, x, :3] = c
                fa[y, x, 3] = 255
    Image.fromarray(fa, 'RGBA').save(M.out('textures/gui/sprites/boss_bars/cult_leader_bossbar_p3_flames.png'))
    # ---- вспышка смены фазы: силуэт полосы (верхняя половина) золотисто-белым
    b = np.asarray(bar1).copy()[:18]
    fla = np.zeros_like(b)
    fla[..., :3] = PAL['D']
    fla[..., 3] = np.where(b[..., 3] > 0, 255, 0)
    Image.fromarray(fla, 'RGBA').save(M.out('textures/gui/sprites/boss_bars/cult_leader_bossbar_flash.png'))
    return p2, pulse, p3, Image.fromarray(fa, 'RGBA')


# ================================================================== lang, звуки
LANG = {
    'ui.pohsmp_core.cult_leader.first_flame': ('Первое Пламя', 'The First Flame'),
    'ui.pohsmp_core.cult_leader.first_flame_warn': ('Земля трескается — перепрыгните кольцо огня!', 'The ground cracks — jump the ring of fire!'),
    'ui.pohsmp_core.cult_leader.ash': ('Пепел Меллисто', 'Ashes of Mellisto'),
    'ui.pohsmp_core.cult_leader.ash_warn': ('Огненная линия — уйдите с неё!', 'A line of fire — get off it!'),
    'ui.pohsmp_core.cult_leader.replica_taunt': ('Эта фальшивка на меня не сработает', 'This forgery won\'t work on me'),
    'death.attack.pohsmp_core.cult_finisher': ('%1$s пал от косы Тироса, Главы Культа Меллисто', '%1$s was finished off by Tyros, Head of the Cult of Mellisto'),
    'subtitles.pohsmp_core.cult_leader.first_flame': ('Раскрывается Первое Пламя', 'The First Flame unfolds'),
    'subtitles.pohsmp_core.cult_leader.first_flame_impact': ('Столб пламени', 'Pillar of flame'),
    'subtitles.pohsmp_core.cult_leader.ash': ('Глава Культа рассыпается пеплом', 'Cult Leader turns to ash'),
    'subtitles.pohsmp_core.cult_leader.ash_slash': ('Огненный разрез', 'Fiery slash'),
    'subtitles.pohsmp_core.cult_leader.replica_break': ('Печати Реплики разбиты', 'Replica seals shattered'),
    'subtitles.pohsmp_core.cult_leader.finisher': ('Коса пронзает', 'Scythe impales'),
}

SOUNDS = {
    'cult_leader.first_flame': [{'name': 'irons_spellbooks:fire_boss/fire_boss_enter_soul', 'pitch': 0.5, 'volume': 1.5}],
    'cult_leader.first_flame_impact': [{'name': 'minecraft:random/explode1', 'pitch': 0.6, 'volume': 1.4},
                                       {'name': 'minecraft:random/explode2', 'pitch': 0.6, 'volume': 1.4}],
    'cult_leader.ash': [{'name': 'minecraft:random/fizz', 'pitch': 0.5, 'volume': 1.3}],
    'cult_leader.ash_slash': [{'name': 'irons_spellbooks:fire_boss/fire_boss_stance_break', 'pitch': 1.2, 'volume': 1.4}],
    'cult_leader.replica_break': [{'name': 'minecraft:random/glass1', 'pitch': 0.7}, {'name': 'minecraft:random/glass2', 'pitch': 0.7},
                                  {'name': 'minecraft:random/glass3', 'pitch': 0.7}],
    'cult_leader.finisher': [{'name': 'minecraft:item/trident/pierce1', 'pitch': 0.7}, {'name': 'minecraft:item/trident/pierce2', 'pitch': 0.7}],
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


# ================================================================== проверочные кадры
def sheet_bars(bars):
    p2, pulse, p3, flames = bars
    bar1 = Image.open(os.path.join(M.A, 'textures/gui/sprites/boss_bars/cult_leader_bossbar.png')).convert('RGBA')
    img = Image.new('RGBA', (1000, 760), (20, 16, 16, 255))
    d = ImageDraw.Draw(img)
    f1, f2 = FX._font(22), FX._font(16)
    d.text((20, 12), 'T26 — полоса босса по фазам (×4): заливка 70%', font=f1, fill=(240, 226, 214))

    def draw(src, y, p=0.7, fl=None):
        e = src.crop((0, 0, 192, 18)).copy()
        f = src.crop((0, 18, 192, 36))
        w = int(3 + p * 186)
        e.alpha_composite(f.crop((0, 0, w, 18)), (0, 0))
        canvas_ = Image.new('RGBA', (192, 24), (0, 0, 0, 0))
        canvas_.alpha_composite(e, (0, 6))
        if fl is not None:
            canvas_.alpha_composite(fl, (0, 6 + 9 - 14))
            canvas_.alpha_composite(e.crop((0, 7, 192, 18)), (0, 13))                        # рамка поверх нижних языков
        img.alpha_composite(canvas_.resize((768, 96), Image.NEAREST), (20, y))
    draw(bar1, 50)
    d.text((800, 90), 'фаза 1', font=f2, fill=(220, 200, 190))
    draw(p2, 160)
    d.text((800, 200), 'фаза 2', font=f2, fill=(220, 200, 190))
    draw(pulse, 270)
    d.text((800, 300), 'фаза 2, пульс\n(запрет магии)', font=f2, fill=(220, 200, 190))
    for i, k in enumerate((0, 3)):
        draw(p3, 380 + i * 110, fl=flames.crop((0, k * 14, 192, k * 14 + 14)))
        d.text((800, 420 + i * 110), 'фаза 3, кадр %d' % k, font=f2, fill=(220, 200, 190))
    img.alpha_composite(flames.resize((768, 224), Image.NEAREST).crop((0, 0, 768, 112)), (20, 610))
    d.text((800, 640), 'p3_flames: 8 кадров\n192×14 (здесь 4)', font=f2, fill=(220, 200, 190))
    img.convert('RGB').save(os.path.join(MEDIA, 't26_bossbar_phases.jpg'), quality=92)


def sheet_special_fx():
    img = Image.new('RGBA', (1600, 560), (18, 10, 8, 255))
    d = ImageDraw.Draw(img)
    f1, f2 = FX._font(22), FX._font(16)
    d.text((20, 12), 'T26 — особые заклинания: печать «Первого Пламени» (sky, r22), кольцо огня (wave.texture), титры', font=f1, fill=(240, 226, 214))
    t = FX._tint('cult_first_flame', FX.FIRE, (440, 440))
    FX._paste_glow(img, t, (20, 60), 8)
    t = FX._tint('cult_fire_ring', FX.FIRE_HOT, (300, 300))
    FX._paste_glow(img, t, (500, 120), 6)
    for i, n in enumerate(('cult_first_flame_ru', 'cult_first_flame_en', 'cult_ash_ru', 'cult_ash_en')):
        tt = Image.open(os.path.join(M.A, 'textures/gui/title/%s.png' % n)).convert('RGBA').resize((512, 96), Image.LANCZOS)
        bg = Image.new('RGBA', tt.size, (42, 28, 24, 255))
        bg.alpha_composite(tt)
        img.alpha_composite(bg, (840 + (i % 2) * 0, 70 + i * 116))
    img.convert('RGB').save(os.path.join(MEDIA, 't26_special_fx.jpg'), quality=90)


def shots_anims(args):
    import cult_leader_render as R
    three = args[args.index('--three') + 1] if '--three' in args else None
    cells = []
    plan = [('cult_leader_first_flame', [(0.9, 'коса в землю'), (2.5, 'рука к печати'), (4.15, 'столб: рывок')]),
            ('cult_leader_ash_dissolve', [(0.4, 'сгорает'), (1.0, 'рассыпается')]),
            ('cult_leader_ash_reform', [(1.0, 'собран: замах')]),
            ('cult_leader_ash_slash', [(0.6, 'разрез (удар 0.5)')]),
            ('cult_leader_replica_break', [(0.7, 'хватает печать'), (1.5, 'косой снизу вверх'), (1.95, '«фальшивка»')]),
            ('cult_leader_finisher', [(0.5, 'тянет жертву'), (1.0, 'пронзает'), (1.8, 'поднимает, вспышка')])]
    an = R.iron_anims()
    an.update(boss_anims())
    for name, ts in plan:
        for t, lab in ts:
            cells.append({'model': 'cult_leader', 'anim': name, 't': t, 'yaw': 35, 'pitch': 8, 'dist': 2.4, 'ty': 18,
                          'label': name.replace('cult_leader_', ''), 'sub': '%.2g с — %s' % (t, lab)})
    html = R.page(['cult_leader'], {'cols': 5, 'cells': cells}, three, anims=an)
    R.shoot(html, os.path.join(MEDIA, 't26_special_anims.jpg'), (1800, 1080))


def shots_scale(three=None):
    """Рост ×1.75 (как Тирос Iron's): Глава рядом с игроком и с оригинальным Тиросом; облик души ×2.0125; добивание — высота подъёма."""
    import cult_leader_render as R
    base = {'yaw': 0, 'pitch': 6, 'fov': 30, 'ground': True}
    cells = [
        dict(base, model='cult_leader', scale=1.75, x=0, label='×1.75: игрок · Глава · Тирос Iron\'s',
             sub='Глава ≈ 3.7 бл. (хитбокс 1.49×3.68), игрок 1.8 бл.', dist=7.0, ty=32,
             models=[{'model': 'steve', 'x': 3.2}, {'model': 'tyros', 'scale': 1.75, 'x': -3.6}]),
        dict(base, model='cult_leader', scale=2.0125, soul=True, x=0, yaw=20, label='облик души ×2.0125', sub='≈ 4.2 бл.', dist=4.6, ty=36,
             models=[{'model': 'steve', 'x': 2.4}]),
        dict(base, model='cult_leader', anim='cult_leader_finisher', t=1.8, scale=1.75, yaw=70, label='добивание, 1.8 с',
             sub='жертва в 3.0 бл. перед ним, поднята на +2.3', dist=5.2, ty=42,
             models=[{'model': 'steve', 'z': -3.0, 'y': 2.3, 'ry': 180}]),
    ]
    cells[0].update(dist=4.4, ty=30)
    cells[2].update(yaw=100, pitch=4, dist=7.5, ty=40)
    R.sheet(os.path.join(MEDIA, 't26_scale.jpg'), {'cols': 1, 'cells': cells[:1]}, three, (1800, 900))
    R.sheet(os.path.join(MEDIA, 't26_scale_soul_finisher.jpg'), {'cols': 2, 'cells': cells[1:]}, three, (1600, 900))


def run(mod, fxmod, args):
    global M, FX
    M, FX = mod, fxmod
    write_anims()
    tex_first_flame()
    tex_fire_ring()
    sigils()
    effects()
    bar1 = Image.open(os.path.join(M.A, 'textures/gui/sprites/boss_bars/cult_leader_bossbar.png')).convert('RGBA')
    FX.title(bar1, 'cult_first_flame', (('ru', 'Первое Пламя', 'CormorantGaramond-BoldItalic-cyrillic.woff'),
                                        ('en', 'The First Flame', 'CormorantGaramond-BoldItalic-latin.woff')))
    FX.title(bar1, 'cult_ash', (('ru', 'Пепел Меллисто', 'CormorantGaramond-BoldItalic-cyrillic.woff'),
                                ('en', 'Ashes of Mellisto', 'CormorantGaramond-BoldItalic-latin.woff')))
    bars = bossbars(bar1)
    lang_sounds()
    sheet_bars(bars)
    sheet_special_fx()
    import gen_cult_leader_spells4 as S4
    S4.run(M, FX, args)
    if '--shots' in args:
        shots_anims(args)
        shots_scale(args[args.index('--three') + 1] if '--three' in args else None)
        S4.shots(args[args.index('--three') + 1] if '--three' in args else None)
