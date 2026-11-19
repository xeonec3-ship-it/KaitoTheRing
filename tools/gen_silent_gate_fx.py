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
    # МАНА (1–9 с, 14.6–26 с и весь каст) — больше НЕ элементы эффекта: временная «туманность» (печати silent_hand_nebula,
    # искры и звёздочки у посоха) убрана 19.11 — ману рисует код, перенос из мода God Wand (MIT): client/fx/gate/GateMana —
    # «ветер» искр, полосы-марли, след посоха (ленты и осыпающиеся искры). См. docs/third_party/god-wand-MIT.txt.
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
    # Печати-«блюдца» по всему небу; из КАЖДОЙ — свой луч прямо вниз до земли, градом и вразнобой (как в аниме и в видео мода:
    # лучи вспыхивают по одному в разные моменты под своими печатями, а не все вместе). Наведённые лучи во врагов — отдельно (код).
    for i in range(90):
        r = 6 + (AREA_R - 6) * math.sqrt(rnd.random())
        a = rnd.uniform(0, 2 * math.pi)
        x, z = r * math.cos(a), r * math.sin(a)
        h = rnd.uniform(17, 32)
        d = T(50) + rnd.randint(0, 16)
        green = i % 3 != 0
        el(type='sigil', id='silent_field_green' if green else 'silent_field_white', delay=d, until=T(62.8),
           at=f'caster+{x:.1f},{h:.1f},{FWD + z:.1f}', orientation='sky', scale=rnd.uniform(0.28, 0.6))   # мельче (решение владельца 19.11; было 0.7–1.5)
        # «град»: эта печать бьёт 4–6 раз за 50.5–62.5 с, каждый раз в момент со своим сдвигом; луч — от печати до земли под ней
        start = d + rnd.randint(8, 40)
        shots = rnd.randint(4, 6)
        gap = rnd.randint(36, 56)
        el(type='beam_rain', delay=start, duration=min(T(62.5) - start, shots * gap + 10), at=f'caster+{x:.1f},0,{FWD + z:.1f}', area=0.6,
           count=shots, interval=gap, width=0.16 + 0.06 * rnd.random(), height=round(h, 1), ground=True,
           color='@secondary' if green else '@core', impact='silent_impact')
    # 62.8–65 с: всё гаснет (ледяной горы нет — решение владельца 19.11)
    el(type='flash', delay=T(62.8), duration=T(1.2), at=f'caster+0,{GATE_UP + 7},{FWD}', size=10, anamorphic=12, rays=8, screen=0.2, color='@core')

def hand_stream_meshes():
    """Модель вместо частиц (владелец 19.11): «туманность» от руки — конус вперёд-вверх (ось из кисти, +z вперёд, +y вверх), длина 6:
    сотни светящихся крупинок (белые, бледно-бирюзовые, розово-лиловые; гуще к оси) и четырёхлучевые звёздочки (скрещённые бруски).
    silent_hand_stream — крупинки и большие звёзды, проявляются от руки наружу; silent_hand_glints_a/_b — два набора мелких звёздочек,
    сменяют друг друга (мерцание)."""
    R3 = lambda v: round(v, 3)
    rnd = random.Random(1460)
    ax = (0.0, 0.5, 1.0); n_ = math.sqrt(sum(c * c for c in ax)); ax = tuple(c / n_ for c in ax)
    up = (0.0, 1.0, 0.0)
    side = (1.0, 0.0, 0.0)
    nrm = (ax[1] * side[2] - ax[2] * side[1], ax[2] * side[0] - ax[0] * side[2], ax[0] * side[1] - ax[1] * side[0])

    def point(t, rr, ang):
        L = 6.0 * t
        bend = 0.6 * t * t                     # поток загибается вверх
        rad = (0.12 + 1.9 * t ** 0.9) * rr
        return tuple(ax[k] * L + (side[k] * math.cos(ang) + nrm[k] * math.sin(ang)) * rad + up[k] * bend for k in range(3))

    def cube(c, s_, tone, out, rot=None):
        b = [R3(c[0] - s_), R3(c[1] - s_), R3(c[2] - s_), R3(c[0] + s_), R3(c[1] + s_), R3(c[2] + s_), tone]
        if rot:
            b.append(rot)
        out.append(b)

    def star(c, r, tone, out):
        th = max(0.02, r * 0.09)
        out.append([R3(c[0] - r), R3(c[1] - th), R3(c[2] - th), R3(c[0] + r), R3(c[1] + th), R3(c[2] + th), tone])
        out.append([R3(c[0] - th), R3(c[1] - r), R3(c[2] - th), R3(c[0] + th), R3(c[1] + r), R3(c[2] + th), tone])
        out.append([R3(c[0] - th), R3(c[1] - th), R3(c[2] - r * 0.7), R3(c[0] + th), R3(c[1] + th), R3(c[2] + r * 0.7), tone])
        cube(c, th * 2.2, 0, out)

    grains, stars = [], []
    for i in range(620):
        t = rnd.random() ** 0.8
        rr = abs(rnd.gauss(0, 0.45))           # гуще к оси
        c = point(t, min(1.0, rr), rnd.uniform(0, 2 * math.pi))
        tone = rnd.choices((0, 1, 2), weights=(5, 3, 2))[0]
        cube(c, rnd.uniform(0.018, 0.045) * (1.2 - 0.4 * t), tone, grains)
    for i in range(14):
        t = rnd.uniform(0.1, 0.95)
        star(point(t, rnd.uniform(0, 0.8), rnd.uniform(0, 6.28)), rnd.uniform(0.18, 0.38), 0, stars)
    tones = ['#FFFFFF', '#AEEFF8', '#E2B4E2']
    def dump_mesh(name, boxes, comment, appear):
        ys = [b[1] for b in boxes] + [b[4] for b in boxes]
        doc = {'comment': comment + ' Сгенерировано tools/gen_silent_gate_fx.py.', 'style': 'silent', 'center': 0, 'formedAt': appear['duration'],
               'collapse': {'duration': 20, 'easing': 'easeInSine'},
               'parts': [{'type': 'boxes', 'tones': tones, 'glowTones': [0, 1, 2], 'blend': 'additive', 'opacity': 0.9, 'shade': False,
                          'boxes': boxes, 'appear': appear, 'bounds': [min(ys), max(ys)]}]}
        with open(os.path.join(os.path.dirname(OUT), 'meshes', name + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(doc, fh, ensure_ascii=False, separators=(',', ':'))
        print(name, len(boxes), 'boxes')
    dump_mesh('silent_hand_stream', grains + stars, '«Безмолвные врата», от руки (14.6–26 с): модель потока-туманности из кисти вперёд-вверх.',
              {'delay': 0, 'duration': 30, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.5})
    for k in 'ab':
        gl = []
        for i in range(22):
            t = rnd.uniform(0.05, 1.0)
            star(point(t, rnd.uniform(0, 1.0), rnd.uniform(0, 6.28)), rnd.uniform(0.08, 0.2), rnd.choice((0, 0, 1)), gl)
        dump_mesh('silent_hand_glints_' + k, gl, '«Безмолвные врата», от руки: мелкие звёздочки (набор %s), мерцают по очереди с другим набором.' % k,
                  {'delay': 0, 'duration': 2, 'easing': 'easeOutCubic'})


def aimed_beam():
    """Наведённый выстрел во ВРАЖДЕБНУЮ сущность (владелец 19.11): над врагом, на высоте остальных кругов неба (point:from — код ставит
    точку над целью: высота 17–32 над землёй, сдвиг вбок до 3), появляется НОВЫЙ круг, собирается за 0.5 с и бьёт лучом в цель;
    удар на 14-м тике. Выстрелы не одновременные: код раздаёт их вразнобой (каждому врагу — раз в 12–24 тика со своим сдвигом)."""
    doc = {
        'comment': 'Наведённый выстрел «Безмолвных врат» во врага: в point:from (над целью, на высоте кругов неба) появляется новый круг, '
                   'собирается (0–10), бьёт толстым белым лучом с бирюзовым ореолом в target (10–19, удар на 14), гаснет к 40. '
                   'Код: выстрелы вразнобой, урон на 14-м тике. Сгенерировано tools/gen_silent_gate_fx.py.',
        'style': 'silent', 'duration': 44,
        'elements': [
            {'type': 'sigil', 'id': 'silent_field_white', 'delay': 0, 'until': 30, 'at': 'point:from', 'orientation': 'sky', 'scale': 0.5,
             'comment': 'новый круг над врагом'},
            {'type': 'flash', 'delay': 8, 'duration': 6, 'at': 'point:from', 'size': 2.2, 'rays': 6, 'color': '@core', 'comment': 'круг «заряжен»'},
            {'type': 'sigil', 'id': 'silent_impact', 'delay': 4, 'at': 'target', 'follow': True, 'until': 12, 'sigilScale': 0.55,
             'comment': 'метка захвата на враге'},
            {'type': 'beam', 'delay': 10, 'duration': 10, 'at': 'point:from', 'to': 'target+0,0.6,0', 'width': 0.95, 'core': 0.0, 'grow': 4,
             'easing': 'easeInCubic', 'color': '@primary', 'brightness': 0.55, 'out': {'duration': 6, 'easing': 'easeInSine'}, 'comment': 'ореол'},
            {'type': 'beam', 'delay': 10, 'duration': 9, 'at': 'point:from', 'to': 'target+0,0.6,0', 'width': 0.42, 'core': 0.75, 'grow': 4,
             'easing': 'easeInCubic', 'color': '@core', 'brightness': 1.4, 'out': {'duration': 5, 'easing': 'easeInSine'}, 'comment': 'белое ядро'},
            {'type': 'flash', 'delay': 14, 'duration': 8, 'at': 'target+0,0.8,0', 'size': 3.2, 'rays': 8, 'anamorphic': 6, 'color': '@core'},
            {'type': 'sigil', 'id': 'silent_impact', 'delay': 14, 'at': 'target', 'until': 36},
            {'type': 'wave', 'delay': 14, 'duration': 12, 'at': 'target', 'radius': 2.6, 'thickness': 0.35, 'color': '@primary'},
            {'type': 'sprites', 'delay': 14, 'duration': 3, 'at': 'target+0,0.6,0', 'texture': '@sparks', 'count': 26, 'rate': 10, 'spread': 0.6,
             'speed': 0.22, 'gravity': 0.012, 'size': [0.16, 0.03], 'life': 16, 'color': '@primary'},
            {'type': 'sprites', 'delay': 14, 'duration': 2, 'at': 'target+0,0.4,0', 'texture': '@shards', 'count': 10, 'rate': 6, 'spread': 0.5,
             'speed': 0.16, 'gravity': 0.03, 'spin': 400, 'size': [0.18, 0.05], 'life': 18, 'color': '@secondary'}]}
    out = os.path.join(os.path.dirname(OUT), 'silent_gate_beam.json')
    json.dump(doc, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('silent_gate_beam fx: aimed shot written')


def main():
    hand_stream_meshes()
    aimed_beam()
    build()
    # «Приказ» (владелец 19.11): врата готовы → ведьма ждёт ЛКМ (сколько угодно, код ограничивает тайм-аутом) → по приказу удар.
    # Поэтому эффект делится: silent_gate.json — всё до приказа (держится, пока код не остановит: duration -1, у долгих элементов нет until);
    # silent_gate_strike.json — удар, отсчёт от приказа (всё, что было на ≥ 49.9 с, сдвинуто на −49.9 с).
    CUT = T(49.9)
    strike = []
    main_ = []
    for e in E:
        if e.get('delay', 0) >= CUT - 1:
            e = dict(e)
            e['delay'] = max(0, e['delay'] - CUT)
            if 'until' in e:
                e['until'] = e['until'] - CUT
            strike.append(e)
        else:
            e = dict(e)
            if 'until' in e and e['until'] > CUT:
                del e['until']             # нимб, врата, круги за спиной — держатся до остановки эффекта кодом
            if e.get('type') == 'tint':
                e['duration'] = T(600)
                e.pop('out', None)
            main_.append(e)
    doc = {
        'comment': 'Эффект «Безмолвные врата» (T03), часть 1: от начала каста до приказа (0–49.9 с и ожидание ЛКМ); держится, пока код не '
                   'остановит (после удара). Удар — fx/silent_gate_strike.json. Сгенерировано tools/gen_silent_gate_fx.py — правьте генератор.',
        'style': 'silent', 'duration': -1, 'elements': main_}
    json.dump(doc, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    doc2 = {
        'comment': 'Эффект «Безмолвные врата» (T03), часть 2: удар по приказу (ЛКМ) — отсчёт от приказа: вспышка у руки, поле печатей неба, '
                   'лучи градом; наведённые выстрелы во врагов — код (fx/silent_gate_beam.json). 15 с. Сгенерировано tools/gen_silent_gate_fx.py.',
        'style': 'silent', 'duration': T(15.2), 'elements': strike}
    json.dump(doc2, open(os.path.join(os.path.dirname(OUT), 'silent_gate_strike.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'silent_gate fx: {len(main_)} elements; silent_gate_strike: {len(strike)}')

if __name__ == '__main__':
    main()
