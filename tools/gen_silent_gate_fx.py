#!/usr/bin/env python3
"""
Эффект «Врат» (T03) на всю шкалу под музыку — fx/silent_gate.json. Время в тиках = время трека × 20.
Раскадровка — docs/specs/tasks/T03_gate.md (по отрывку аниме «Секреты безмолвной ведьмы»):
  0–14 с    тихое вступление: редкие бирюзовые искры вокруг ведьмы, мир чуть темнеет в бирюзу
  14–26 с   указ рукой — вокруг руки закручиваются потоки искр, из руки к вратам тянется луч-лента света
  20–26 с   в небе впереди собирается нимб, из света сверху вниз проявляются врата, светлые полосы вниз
  26–36 с   врата висят: нимб, лучи-блики, медленное мерцание
  38–47 с   палец к губам, посох в левой руке — за спиной дугой складываются золотые круги и зелёные сферы, струйки снизу вверх
  46–49 с   от каждого круга и сферы вверх столб света
  50 с      по небу над площадью — десятки малых печатей; залпы наведённых лучей во врагов (код, fx/silent_gate_beam.json)
            и случайный ливень по площади, на земле — кольца ударов
  62.5–65 с всё гаснет, в центре площади вырастает ледяная гора
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
# Площадь ударов — под вратами (центр в 26 блоках впереди); ледяная гора в финале — в центре площади. Главного луча нет.
FWD = 26
# высота врат над площадью: «намного повыше» (решение владельца 19.11; было 16) — то же число в SilentGateSpell.GATE_H
GATE_UP = 48
GATE = f'caster+0,{GATE_UP},{FWD}'    # врата
NIMBUS = f'caster+0,{GATE_UP + 10},{FWD + 2}'    # нимб за верхом врат, крупнее их (как в аниме)
AREA = f'caster+0,0,{FWD}'           # центр площади ударов


def el(**kw):
    E.append(kw)


def build():
    rnd = random.Random(1300)
    # мир в бирюзовую ночь — у всех в радиусе ролика; к концу возвращается
    el(type='tint', delay=0, duration=T(65), at='caster', radius=64, color='#1E4A5A', strength=0.28,
       **{'in': {'duration': T(6), 'easing': 'easeInOutSine'}, 'out': {'duration': T(2.5), 'easing': 'easeInSine'}})
    # 0–14 с: редкие искры у ведьмы
    el(type='sprites', delay=0, duration=T(14), at='caster+0,0.8,0', texture='@sparks', count=60, rate=0.25, spread=2.2,
       speed=0.015, gravity=-0.002, size=[0.12, 0.05], life=60, color='@primary')
    el(type='sigil', id='silent_gate_ground', delay=T(1), until=T(64), at='caster', color='@primary', scale=0.8)
    # 14–22 с: потоки искр вокруг руки и тела — несколько вихрей частиц от руки
    for k in range(4):
        el(type='sprites', delay=T(14 + k * 0.5), duration=T(8), at='caster.hand', texture='@sparks', count=220, rate=6,
           spread=0.6 + 0.4 * k, speed=0.05, gravity=-0.003, spin=180 + 60 * k, tumble=0.4, size=[0.14, 0.04], life=40,
           color='@primary' if k % 2 == 0 else '@secondary')
    # 14–26 с: свет от руки — тонкий луч-лента из руки вперёд-вверх к месту врат (как в аниме и в видео мода), мерцает
    el(type='beam', delay=T(14.6), duration=T(11.4), at='caster.hand', to=GATE, width=0.08, core=0.6, taper=0.8, grow=T(1.2),
       flicker=0.2, color='@primary', **{'out': {'duration': T(1.5), 'easing': 'easeInSine'}})
    el(type='beam', delay=T(14.6), duration=T(11.4), at='caster.hand', to=GATE, width=0.22, core=0.0, taper=0.8, grow=T(1.2),
       color='@primary', brightness=0.35, **{'out': {'duration': T(1.5), 'easing': 'easeInSine'}})
    # 49.9 с: рука прямо вперёд — вспышка у руки
    el(type='flash', delay=T(49.9), duration=T(0.6), at='caster.hand', size=1.6, anamorphic=4, rays=6, color='@core')
    # 20–26 с: нимб, врата из света, полосы вниз
    el(type='sigil', id='silent_nimbus', delay=T(20), until=T(63), at=NIMBUS, orientation='facing', color='@primary')
    el(type='flash', delay=T(21.8), duration=T(1.2), at=GATE, size=8, anamorphic=18, rays=10, screen=0.25, color='@core')
    el(type='mesh', model='silent_gate', delay=T(22), until=T(63), at=GATE, yaw=180, scale=1.5)
    for i in range(7):
        x = -5 + i * 10 / 6
        el(type='beam', delay=T(22.3 + 0.35 * i), duration=T(3.2), at=f'caster+{x:.1f},{GATE_UP + 12},{FWD}', to=f'caster+{x * 0.7:.1f},{GATE_UP - 5},{FWD}',
           width=0.18 + 0.12 * (i % 2), core=0.4, taper=0.6, grow=10, color='@secondary', brightness=0.7)
    # 26–36 с: врата висят — блики и мерцание
    el(type='flash', delay=T(26), duration=T(10), at=NIMBUS, size=10, anamorphic=0, rays=14, screen=0.0, color='@primary', brightness=0.35)
    el(type='sprites', delay=T(24), duration=T(38), at=GATE, texture='@sparks', count=300, rate=1.2, spread=9, speed=0.01,
       gravity=0.0015, size=[0.18, 0.06], life=120, color='@core')
    # 42–46 с: струйки снизу вверх, по бокам круги и сферы
    el(type='sprites', delay=T(42), duration=T(8), at='caster', texture='@sparks', count=400, rate=8, spread=1.6,
       speed=0.07, gravity=-0.006, size=[0.12, 0.04], life=36, color='@primary')
    # 38–47 с: пока ведьма прикладывает палец к губам и берёт посох в левую руку, ЗА ЕЁ СПИНОЙ дугой складываются
    # золотые круги и зелёные сферы (с краёв к центру); с 46.2 с от каждого вверх столб света
    n = 9
    for i in range(n):
        a = math.radians(-70 + 140 * i / (n - 1))
        x, z = 3.4 * math.sin(a), -(3.4 * math.cos(a) * 0.55 + 0.6)          # за спиной
        coin = i % 2 == 0
        d = T(39) + int((4 - abs(i - n // 2)) * T(1.0))               # сначала крайние по бокам, потом сходятся к центру
        el(type='sigil', id='silent_coin' if coin else 'silent_orb', delay=d, until=T(63), at=f'caster+{x:.2f},1.5,{z:.2f}',
           orientation='facing', color='@gold' if coin else '@primary')
        el(type='column', delay=T(46.2) + i * 2, duration=T(63) - T(46.2) - i * 2, at=f'caster+{x:.2f},1.5,{z:.2f}', radius=0.28 if coin else 0.18,
           height=7, fill=0.55, color='@gold' if coin else '@primary', brightness=0.6,
           **{'in': {'duration': 8, 'easing': 'easeOutCubic'}, 'out': {'duration': 20, 'easing': 'easeInSine'}})
    # 50 с: поле малых печатей над площадью, каждая бьёт лучом вниз
    el(type='flash', delay=T(50), duration=T(0.8), at='caster+0,2,0', size=4, anamorphic=10, rays=6, screen=0.45, color='@core')
    # поле печатей-«блюдец» по всему небу под и вокруг врат (по видео мода — десятки, высоко и широко); лучей сами по себе
    # не дают: наведённые залпы в врагов пускает код (fx/silent_gate_beam.json), случайные удары по площади — beam_rain ниже
    for i in range(48):
        r = 3 + 22 * math.sqrt(rnd.random())
        a = rnd.uniform(0, 2 * math.pi)
        x, z = r * math.cos(a), r * math.sin(a)
        h = rnd.uniform(17, 32)
        d = T(50) + rnd.randint(0, 16)
        green = i % 3 != 0
        el(type='sigil', id='silent_field_green' if green else 'silent_field_white', delay=d, until=T(62.8),
           at=f'caster+{x:.1f},{h:.1f},{FWD + z:.1f}', orientation='sky', scale=rnd.uniform(0.28, 0.6))   # мельче (решение владельца 19.11; было 0.7–1.5)
    el(type='beam_rain', delay=T(50.5), duration=T(12), at=AREA, area=22, count=200, interval=1.2, width=0.22, height=26,
       color='@secondary', impact='silent_impact')
    # 62.5–65 с: всё гаснет, ледяная гора на месте удара
    el(type='mesh', model='silent_crystal', delay=T(62.8), until=T(95), at=AREA, yaw=0, scale=1.2)
    el(type='flash', delay=T(62.8), duration=T(1.2), at=f'caster+0,3,{FWD}', size=8, anamorphic=12, rays=8, screen=0.35, color='@core')
    el(type='sprites', delay=T(62.8), duration=T(20), at=f'caster+0,4,{FWD}', texture='@shards', count=80, rate=4, spread=5, speed=0.02,
       gravity=0.004, spin=60, tumble=0.6, size=[0.3, 0.1], life=80, color='@secondary')


def main():
    build()
    doc = {
        'comment': 'Эффект «Врата» (T03) на всю шкалу под музыку (0–65 с). Сгенерировано tools/gen_silent_gate_fx.py — правьте генератор.',
        'style': 'silent',
        'duration': T(96),
        'elements': E,
    }
    json.dump(doc, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'silent_gate fx: {len(E)} elements')


if __name__ == '__main__':
    main()
