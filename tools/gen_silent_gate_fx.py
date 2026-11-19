#!/usr/bin/env python3
"""
Эффект «Врат» (T03) на всю шкалу под музыку — fx/silent_gate.json. Время в тиках = время трека × 20.
Раскадровка — docs/specs/tasks/T03_gate.md (по отрывку аниме «Секреты безмолвной ведьмы»):
  0–14 с    тихое вступление: редкие бирюзовые искры вокруг ведьмы, мир чуть темнеет в бирюзу
  14–22 с   указ пальцем — вокруг руки и тела закручиваются потоки искр
  20–26 с   в небе впереди собирается нимб, из света сверху вниз проявляются врата, светлые полосы вниз
  26–36 с   врата висят: нимб, лучи-блики, медленное мерцание
  42–46 с   вокруг ведьмы снизу вверх струйки, по бокам появляются золотые круги и зелёные сферы
  46–49 с   круги и сферы встают дугой перед ведьмой, от каждого вверх столб света
  50 с      по небу над площадью — десятки малых печатей, каждая бьёт лучом вниз; ливень лучей
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
GATE = f'caster+0,16,{FWD}'          # врата
NIMBUS = f'caster+0,20.5,{FWD + 1}'  # нимб чуть выше и за вратами
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
    # 20–26 с: нимб, врата из света, полосы вниз
    el(type='sigil', id='silent_nimbus', delay=T(20), until=T(63), at=NIMBUS, orientation='facing', color='@primary')
    el(type='flash', delay=T(21.8), duration=T(1.2), at=GATE, size=8, anamorphic=18, rays=10, screen=0.25, color='@core')
    el(type='mesh', model='silent_gate', delay=T(22), until=T(63), at=GATE, yaw=180, scale=1.5)
    for i in range(7):
        x = -5 + i * 10 / 6
        el(type='beam', delay=T(22.3 + 0.35 * i), duration=T(3.2), at=f'caster+{x:.1f},28,{FWD}', to=f'caster+{x * 0.7:.1f},11,{FWD}',
           width=0.18 + 0.12 * (i % 2), core=0.4, taper=0.6, grow=10, color='@secondary', brightness=0.7)
    # 26–36 с: врата висят — блики и мерцание
    el(type='flash', delay=T(26), duration=T(10), at=NIMBUS, size=10, anamorphic=0, rays=14, screen=0.0, color='@primary', brightness=0.35)
    el(type='sprites', delay=T(24), duration=T(38), at=GATE, texture='@sparks', count=300, rate=1.2, spread=9, speed=0.01,
       gravity=0.0015, size=[0.18, 0.06], life=120, color='@core')
    # 42–46 с: струйки снизу вверх, по бокам круги и сферы
    el(type='sprites', delay=T(42), duration=T(8), at='caster', texture='@sparks', count=400, rate=8, spread=1.6,
       speed=0.07, gravity=-0.006, size=[0.12, 0.04], life=36, color='@primary')
    # 44–49 с: золотые круги и зелёные сферы дугой перед ведьмой, от каждого вверх столб света
    n = 9
    for i in range(n):
        a = math.radians(-70 + 140 * i / (n - 1))
        x, z = 3.4 * math.sin(a), 3.4 * math.cos(a) * 0.55 + 0.6
        coin = i % 2 == 0
        d = T(44 + (abs(i - n // 2) * 0.6 if i != n // 2 else 0))   # сначала крайние по бокам, потом сходятся к центру
        d = T(44) + int((4 - abs(i - n // 2)) * T(0.55)) if True else d
        el(type='sigil', id='silent_coin' if coin else 'silent_orb', delay=d, until=T(63), at=f'caster+{x:.2f},1.5,{z:.2f}',
           orientation='facing', color='@gold' if coin else '@primary')
        el(type='column', delay=T(46.2) + i * 2, duration=T(63) - T(46.2) - i * 2, at=f'caster+{x:.2f},1.5,{z:.2f}', radius=0.28 if coin else 0.18,
           height=7, fill=0.55, color='@gold' if coin else '@primary', brightness=0.6,
           **{'in': {'duration': 8, 'easing': 'easeOutCubic'}, 'out': {'duration': 20, 'easing': 'easeInSine'}})
    # 50 с: поле малых печатей над площадью, каждая бьёт лучом вниз
    el(type='flash', delay=T(50), duration=T(0.8), at='caster+0,2,0', size=4, anamorphic=10, rays=6, screen=0.45, color='@core')
    for i in range(30):
        r = 4 + 16 * math.sqrt(rnd.random())
        a = rnd.uniform(0, 2 * math.pi)
        x, z = r * math.cos(a), r * math.sin(a)
        h = rnd.uniform(15, 26)
        d = T(50) + rnd.randint(0, 14)
        green = i % 3 != 0
        el(type='sigil', id='silent_field_green' if green else 'silent_field_white', delay=d, until=T(62.8),
           at=f'caster+{x:.1f},{h:.1f},{FWD + z:.1f}', orientation='sky', scale=rnd.uniform(0.7, 1.4))
        el(type='beam', delay=d + 6, duration=T(62.6) - d - 6, at=f'caster+{x:.1f},{h - 0.2:.1f},{FWD + z:.1f}', to=f'caster+{x:.1f},0,{FWD + z:.1f}',
           width=0.22 + 0.12 * rnd.random(), core=0.45, grow=4, easing='easeInCubic', flicker=0.25, color='@secondary')
    el(type='beam_rain', delay=T(50.5), duration=T(12), at=AREA, area=20, count=160, interval=1.5, width=0.3, height=24,
       color='@secondary', impact='silent_orb')
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
