#!/usr/bin/env python3
"""
Эффект «Врат» (T03) на всю шкалу под музыку — fx/silent_gate.json. Время в тиках = время трека × 20.
Раскадровка — docs/specs/tasks/T03_gate.md (по отрывку аниме «Секреты безмолвной ведьмы»):
  0–14 с    тихое вступление: редкие бирюзовые искры вокруг ведьмы, мир чуть темнеет в бирюзу
  14–26 с   указ рукой — вокруг руки закручиваются потоки искр, из руки к вратам тянется луч-лента света
  20–26 с   в небе впереди собирается нимб, из света сверху вниз проявляются врата, светлые полосы вниз
  26–36 с   врата висят: нимб, лучи-блики, медленное мерцание
  38–47 с   палец к губам, посох в левой руке — за спиной дугой складываются золотые круги и зелёные сферы
  47.6–49.6 «открытие врат»: створки расходятся, из проёма свет
  50 с      по небу над площадью — десятки малых печатей; залпы НАВЕДЁННЫХ лучей во враждебных (код, fx/silent_gate_beam.json —
            пишет этот же генератор) и случайный ливень по площади, на земле — кольца ударов
  62.8–65 с всё гаснет
Привязки: caster+x,y,z — в осях взгляда заклинателя в начале каста (x вправо, y вверх, z вперёд). Точки каста нет: врата в небе впереди.
Запуск: python3 tools/gen_silent_gate_fx.py
"""
import json
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'fx', 'silent_gate.json')
T = lambda sec: int(round(sec * 20))
E = []
# Точка каста не нужна (решение владельца): врата встают в небе впереди заклинателя — по взгляду в начале каста.
# Площадь ударов — под вратами (центр в 26 блоках впереди), радиус 44 (вдвое шире, решение владельца 19.11). Главного луча нет.
# Правки владельца 19.11: без лучей «игрок → врата» (и не добавлять такие), без золотых кругов в начале, без столбов от кругов
# за спиной, без ледяной горы в конце; от пальца — веер изогнутых струй искр, сходящихся на кончике (как в аниме и видео мода);
# врата медленно выходят вниз из магического круга над ними; перед ударом створки открываются, из проёма — свет.
FWD = 26
# высота врат над площадью: «намного повыше» (решение владельца 19.11; было 16) — то же число в SilentGateSpell.GATE_H
GATE_UP = 48
GATE = f'caster+0,{GATE_UP},{FWD}'    # врата
NIMBUS = f'caster+0,{GATE_UP + 17},{FWD}'    # магический круг НАД вратами, плашмя (решение владельца 19.11: не за вратами) — врата выходят из него вниз
AREA = f'caster+0,0,{FWD}'           # центр площади ударов
AREA_R = 44                          # радиус площади (было 22)


def el(**kw):
    E.append(kw)


def build():
    rnd = random.Random(1300)
    # мир в бирюзовую ночь — у всех в радиусе ролика; к концу возвращается
    el(type='tint', delay=0, duration=T(65), at='caster', radius=128, color='#1E4A5A', strength=0.28,
       **{'in': {'duration': T(6), 'easing': 'easeInOutSine'}, 'out': {'duration': T(2.5), 'easing': 'easeInSine'}})
    # 0–14 с: редкие искры у ведьмы
    el(type='sprites', delay=0, duration=T(14), at='caster+0,0.8,0', texture='@sparks', count=60, rate=0.25, spread=2.2,
       speed=0.015, gravity=-0.002, size=[0.12, 0.05], life=60, color='@primary')
    # 14.6–26 с: ОТ РУКИ — точь-в-точь как в видео мода: из поднятой руки вперёд-вверх (по взгляду) конусом раскрывается
    # «туманность» — плотный поток мельчайших белых и бледно-бирюзовых искр с розово-лиловым отливом, мягкие светящиеся облачка,
    # в потоке мерцают крупные четырёхлучевые звёздочки (textures/fx/glint4.png); у кисти — мягкое белое ядро.
    # Никаких лучей-лент от руки к вратам (решение владельца 19.11).
    hand = dict(delay=T(14.6), duration=T(11.4), at='caster.hand', follow=True)
    fade = {'in': {'duration': T(1.0), 'easing': 'easeOutCubic'}, 'out': {'duration': T(1.6), 'easing': 'easeInSine'}}
    el(type='flash', size=0.9, rays=0, color='#FFFFFF', brightness=0.9, **hand, **fade, comment='мягкое белое ядро у кисти')
    el(type='sprites', texture='spark_soft', count=4000, rate=24, cone=50, speed=0.085, gravity=-0.0006, size=[0.07, 0.02], life=48,
       glow=0.25, color='#FFFFFF', **hand, comment='мельчайшие белые искры — основа потока')
    el(type='sprites', texture='spark_soft', count=2200, rate=13, cone=62, speed=0.065, gravity=-0.0004, size=[0.09, 0.02], life=56,
       glow=0.3, color='#BFF4FF', **hand, comment='бледно-бирюзовые')
    el(type='sprites', texture='spark_soft', count=1200, rate=7, cone=74, speed=0.05, gravity=-0.0003, size=[0.08, 0.02], life=60,
       glow=0.3, color='#F2C6EE', **hand, comment='розово-лиловый отлив по краям')
    el(type='sprites', texture='glow', count=260, rate=1.6, cone=44, speed=0.045, gravity=-0.0002, size=[0.7, 2.4], life=64,
       color='#6E5C8E', **hand, comment='мягкие светящиеся облачка туманности (тусклые, аддитивно)')
    el(type='sprites', texture='glow', count=160, rate=1.0, cone=36, speed=0.055, gravity=-0.0002, size=[0.5, 1.8], life=56,
       color='#4E7E8E', **hand)
    el(type='sprites', texture='glint4', count=420, rate=2.6, cone=58, speed=0.06, gravity=-0.0004, spin=60, size=[0.42, 0.06], life=42,
       glow=0.5, color='#FFFFFF', **hand, comment='крупные четырёхлучевые звёздочки в потоке')
    el(type='sprites', delay=T(14.6), duration=T(11.4), at='caster+0,1.6,1.5', texture='glint4', count=160, rate=0.8, spread=6,
       speed=0.004, gravity=0.0, spin=30, size=[0.0, 0.5], life=50, color='#FFFFFF', comment='редкие звёздочки, мерцающие в воздухе вокруг')
    # 49.9 с: рука прямо вперёд — вспышка у руки
    el(type='flash', delay=T(49.9), duration=T(0.6), at='caster.hand', size=1.6, anamorphic=4, rays=6, color='@core')
    # 20 с: над местом врат плашмя собирается магический круг; 21.8–27 с врата МЕДЛЕННО выходят из него вниз — опускаются сквозь круг
    # на своё место, проявляясь снизу вверх (низ, прошедший сквозь круг, виден первым). Створки — отдельные модели на петлях
    # (открываются перед ударом), за ними — свет проёма.
    el(type='sigil', id='silent_nimbus', delay=T(20), until=T(63), at=NIMBUS, orientation='sky', color='@primary', scale=1.6)
    el(type='flash', delay=T(21.6), duration=T(2.0), at=NIMBUS, size=9, anamorphic=14, rays=10, screen=0.15, color='@core')
    emerge = {'from': [0, 17, 0], 'scaleFrom': 1.0, 'delay': 0, 'duration': T(5.2), 'easing': 'easeOutCubic'}
    for model, hinge in (('silent_gate', None), ('silent_gate_door_l', {'pivot': [-3, 0, 0], 'axis': 'y', 'angle': 100}),
                         ('silent_gate_door_r', {'pivot': [3, 0, 0], 'axis': 'y', 'angle': -100})):
        e = dict(type='mesh', model=model, delay=T(21.8), until=T(63), at=GATE, yaw=180, scale=1.5, move=emerge)
        if hinge:   # 47.6–49.6 с: «Открытие врат» — створки медленно расходятся внутрь, из проёма бьёт свет
            e['hinge'] = dict(hinge, delay=T(47.6) - T(21.8), duration=T(2.0), easing='easeInOutCubic')
        el(**e)
    el(type='mesh', model='silent_gate_light', delay=T(47.5), until=T(63), at=GATE, yaw=180, scale=1.5)
    el(type='flash', delay=T(48.2), duration=T(2.2), at=f'caster+0,{GATE_UP + 7},{FWD}', size=16, anamorphic=26, rays=16, screen=0.3, color='@core',
       comment='свет из открывающихся врат')
    # 26–36 с: врата висят — блики и мерцание
    el(type='flash', delay=T(26), duration=T(10), at=NIMBUS, size=10, anamorphic=0, rays=14, screen=0.0, color='@primary', brightness=0.35)
    el(type='sprites', delay=T(24), duration=T(38), at=GATE, texture='@sparks', count=300, rate=1.2, spread=9, speed=0.01,
       gravity=0.0015, size=[0.18, 0.06], life=120, color='@core')
    # 42–46 с: струйки снизу вверх, по бокам круги и сферы
    el(type='sprites', delay=T(42), duration=T(8), at='caster', texture='@sparks', count=400, rate=8, spread=1.6,
       speed=0.07, gravity=-0.006, size=[0.12, 0.04], life=36, color='@primary')
    # 38–47 с: пока ведьма прикладывает палец к губам и берёт посох в левую руку, ЗА ЕЁ СПИНОЙ дугой складываются
    # золотые круги и зелёные сферы (с краёв к центру); лучей от них нет (решение владельца 19.11)
    n = 9
    for i in range(n):
        a = math.radians(-70 + 140 * i / (n - 1))
        x, z = 3.4 * math.sin(a), -(3.4 * math.cos(a) * 0.55 + 0.6)          # за спиной
        coin = i % 2 == 0
        d = T(39) + int((4 - abs(i - n // 2)) * T(1.0))               # сначала крайние по бокам, потом сходятся к центру
        el(type='sigil', id='silent_coin' if coin else 'silent_orb', delay=d, until=T(63), at=f'caster+{x:.2f},1.5,{z:.2f}',
           orientation='facing', color='@gold' if coin else '@primary')
    # 50 с: поле малых печатей над площадью, каждая бьёт лучом вниз
    el(type='flash', delay=T(50), duration=T(0.8), at='caster+0,2,0', size=4, anamorphic=10, rays=6, screen=0.45, color='@core')
    # поле печатей-«блюдец» по всему небу под и вокруг врат (по видео мода — десятки, высоко и широко); лучей сами по себе
    # не дают: наведённые залпы в врагов пускает код (fx/silent_gate_beam.json), случайные удары по площади — beam_rain ниже
    for i in range(90):
        r = 6 + (AREA_R - 6) * math.sqrt(rnd.random())
        a = rnd.uniform(0, 2 * math.pi)
        x, z = r * math.cos(a), r * math.sin(a)
        h = rnd.uniform(17, 32)
        d = T(50) + rnd.randint(0, 16)
        green = i % 3 != 0
        el(type='sigil', id='silent_field_green' if green else 'silent_field_white', delay=d, until=T(62.8),
           at=f'caster+{x:.1f},{h:.1f},{FWD + z:.1f}', orientation='sky', scale=rnd.uniform(0.28, 0.6))   # мельче (решение владельца 19.11; было 0.7–1.5)
    # лучи — от неба ДО ЗЕМЛИ в своей точке (`ground: true`: низ луча и кольцо удара — на поверхности под точкой, не на высоте заклинателя)
    el(type='beam_rain', delay=T(50.5), duration=T(12), at=AREA, area=AREA_R, count=400, interval=0.6, width=0.22, height=40, ground=True,
       color='@secondary', impact='silent_impact')
    # 62.8–65 с: всё гаснет (ледяной горы нет — решение владельца 19.11)
    el(type='flash', delay=T(62.8), duration=T(1.2), at=f'caster+0,{GATE_UP + 7},{FWD}', size=10, anamorphic=12, rays=8, screen=0.2, color='@core')

def aimed_beam():
    """Один наведённый луч в ВРАЖДЕБНУЮ сущность (код пускает залпами: раз в 0.5 с в каждого врага 3–5 лучей из разных печатей неба).
    Должен читаться иначе, чем случайный ливень: на враге сначала вспыхивает метка захвата, затем падает толстый белый луч с бирюзовым
    ореолом, удар — яркая вспышка, кольцо, искры и осколки. at = point:from (печать в небе), target — враг (следует за ним)."""
    doc = {
        'comment': 'Наведённый луч «Безмолвных врат» во враждебную сущность (по видео мода): метка захвата на цели (0–4 тик), из печати неба '
                   '(point:from) в цель (target) падает толстый белый луч с бирюзовым ореолом (тики 3–12), удар — вспышка, кольцо, искры, осколки. '
                   'Код: залпы раз в 0.5 с, 3–5 лучей в каждого врага. Случайный ливень по площади — beam_rain в silent_gate.json. '
                   'Сгенерировано tools/gen_silent_gate_fx.py.',
        'style': 'silent', 'duration': 34,
        'elements': [
            {'type': 'sigil', 'id': 'silent_impact', 'delay': 0, 'at': 'target', 'follow': True, 'until': 6, 'sigilScale': 0.6,
             'comment': 'метка захвата на враге'},
            {'type': 'flash', 'delay': 0, 'duration': 4, 'at': 'target+0,1,0', 'follow': True, 'size': 0.9, 'rays': 4, 'color': '@primary'},
            {'type': 'beam', 'delay': 3, 'duration': 10, 'at': 'point:from', 'to': 'target+0,0.6,0', 'width': 0.95, 'core': 0.0, 'grow': 3,
             'easing': 'easeInCubic', 'color': '@primary', 'brightness': 0.55, 'out': {'duration': 6, 'easing': 'easeInSine'}, 'comment': 'ореол'},
            {'type': 'beam', 'delay': 3, 'duration': 9, 'at': 'point:from', 'to': 'target+0,0.6,0', 'width': 0.42, 'core': 0.75, 'grow': 3,
             'easing': 'easeInCubic', 'color': '@core', 'brightness': 1.4, 'out': {'duration': 5, 'easing': 'easeInSine'}, 'comment': 'белое ядро'},
            {'type': 'flash', 'delay': 6, 'duration': 8, 'at': 'target+0,0.8,0', 'size': 3.2, 'rays': 8, 'anamorphic': 6, 'color': '@core'},
            {'type': 'sigil', 'id': 'silent_impact', 'delay': 6, 'at': 'target', 'until': 28},
            {'type': 'wave', 'delay': 6, 'duration': 12, 'at': 'target', 'radius': 2.6, 'thickness': 0.35, 'color': '@primary'},
            {'type': 'sprites', 'delay': 6, 'duration': 3, 'at': 'target+0,0.6,0', 'texture': '@sparks', 'count': 26, 'rate': 10, 'spread': 0.6,
             'speed': 0.22, 'gravity': 0.012, 'size': [0.16, 0.03], 'life': 16, 'color': '@primary'},
            {'type': 'sprites', 'delay': 6, 'duration': 2, 'at': 'target+0,0.4,0', 'texture': '@shards', 'count': 10, 'rate': 6, 'spread': 0.5,
             'speed': 0.16, 'gravity': 0.03, 'spin': 400, 'size': [0.18, 0.05], 'life': 18, 'color': '@secondary'}]}
    out = os.path.join(os.path.dirname(OUT), 'silent_gate_beam.json')
    json.dump(doc, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('silent_gate_beam fx: aimed beam written')


def main():
    aimed_beam()
    build()
    doc = {
        'comment': 'Эффект «Безмолвные врата» (T03) на всю шкалу под музыку (0–65 с). Сгенерировано tools/gen_silent_gate_fx.py — правьте генератор.',
        'style': 'silent',
        'duration': T(96),
        'elements': E,
    }
    json.dump(doc, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'silent_gate fx: {len(E)} elements')


if __name__ == '__main__':
    main()
