#!/usr/bin/env python3
"""
Вид огненного меча-хлыста (T14, рабочее «Раскалённые угли»), стиль `pyre`:
  fx/ember_last_heat.json   — спецатака в форме меча «Последний жар»: клинок в землю (at = точка удара, ~1.2 блока перед
                              владельцем), три волны огненных столбов наружу (r 3 / 5 / 7), трещины, угли; клинок остывает — пар.
  fx/ember_vortex.json      — спецатака в форме хлыста «Огненный вихрь»: полный оборот хлыста вокруг владельца (at = владелец),
                              огненное кольцо r 5, языки пламени по кругу, волна наружу (отброс).
  fx/ember_heat.json        — раскалённый клинок (пока жар > 0): угли и искры с клинка; follow, гасится кодом (stop).
  textures/gui/ember_heat_bar.png — HUD шкалы жара над хотбаром: 128×32, верх 16 — рамка-«угли», низ 16 — заливка (градиент),
                              код рисует рамку и заливку по доле жара; при полной шкале — пульсация (код, альфа заливки).
Запуск: python3 tools/gen_ember_fx.py
"""
import json
import math
import os
import random
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')


def dump(rel, doc):
    with open(os.path.join(A, rel), 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print('wrote', rel)


def last_heat():
    rnd = random.Random(14)
    E = [
        {'type': 'flash', 'delay': 0, 'duration': 8, 'at': 'caster+0,0.3,0', 'size': 3, 'rays': 10, 'anamorphic': 8, 'screen': 0.2, 'color': '@core',
         'comment': 'клинок входит в землю'},
        {'type': 'decal', 'delay': 0, 'duration': 120, 'at': 'caster', 'texture': 'higher_cracks', 'radius': 3.5, 'grow': 6, 'fadeOut': 50,
         'color': '@primary', 'brightness': 1.2, 'comment': 'раскалённые трещины от клинка'},
        {'type': 'decal', 'delay': 2, 'duration': 160, 'at': 'caster', 'texture': 'glow', 'radius': 8, 'grow': 26, 'fadeOut': 80,
         'color': '@shadow', 'blend': 'translucent', 'comment': 'выжженный круг'},
    ]
    for wave, (r, n, d) in enumerate(((3.0, 8, 4), (5.0, 12, 12), (7.0, 16, 20))):
        E.append({'type': 'wave', 'delay': d - 2, 'duration': 12, 'at': 'caster', 'radius': r + 0.6, 'thickness': 0.5, 'color': '@primary'})
        for i in range(n):
            a = 2 * math.pi * (i + 0.5 * (wave % 2)) / n + rnd.uniform(-0.08, 0.08)
            x, z = r * math.cos(a), r * math.sin(a)
            h = rnd.uniform(3.2, 4.6) - wave * 0.4
            dd = d + rnd.randint(0, 2)
            E.append({'type': 'column', 'delay': dd, 'duration': 16, 'at': f'caster+{x:.2f},0,{z:.2f}', 'radius': rnd.uniform(0.35, 0.5),
                      'height': round(h, 2), 'fill': 0.8, 'color': '@primary' if i % 2 else '@secondary',
                      'in': {'duration': 3, 'easing': 'easeOutCubic'}, 'out': {'duration': 8, 'easing': 'easeInSine'}})
            E.append({'type': 'sprites', 'delay': dd, 'duration': 6, 'at': f'caster+{x:.2f},0.3,{z:.2f}', 'texture': '@sparks', 'count': 14,
                      'rate': 4, 'spread': 0.4, 'speed': 0.14, 'gravity': -0.004, 'size': [0.16, 0.03], 'life': 24, 'color': '@secondary'})
        E.append({'type': 'decal', 'delay': d, 'duration': 90, 'at': 'caster', 'texture': 'thin_ring', 'radius': r + 0.3, 'fadeOut': 50,
                  'color': '@primary', 'comment': f'горящее кольцо волны {wave + 1}'})
    E += [
        {'type': 'sprites', 'delay': 4, 'duration': 40, 'at': 'caster+0,0.2,0', 'texture': '@sparks', 'count': 220, 'rate': 6, 'area': 7,
         'speed': 0.03, 'gravity': -0.005, 'size': [0.14, 0.02], 'life': 40, 'color': '@primary', 'comment': 'угли поднимаются по всей площади'},
        {'type': 'sprites', 'delay': 30, 'duration': 50, 'at': 'caster+0,0.6,0', 'texture': 'glow', 'count': 60, 'rate': 1.2, 'spread': 0.25,
         'speed': 0.02, 'gravity': -0.003, 'size': [0.5, 1.4], 'life': 50, 'color': '#8A8A92', 'blend': 'translucent',
         'comment': 'клинок остывает: пар и дым от рукояти'},
    ]
    dump('fx/ember_last_heat.json', {
        'comment': '«Последний жар» (T14, форма меча): at = место, куда вонзён клинок; три волны огненных столбов r 3/5/7 на тиках 4/12/20 '
                   '(урон кода — по этим тикам), горящие кольца, угли; потом клинок остывает (пар). Сгенерировано tools/gen_ember_fx.py.',
        'style': 'pyre', 'duration': 160, 'elements': E})


def vortex():
    E = [
        {'type': 'slash', 'delay': 0, 'at': 'caster+0,1.0,0', 'radius': 4.6, 'arc': 360, 'thickness': 0.5, 'bend': 1, 'secondary': 0.7, 'grow': 8,
         'life': 14, 'tilt': 0, 'pitch': -4, 'color': '@primary', 'comment': 'хлыст: полный оборот вокруг владельца'},
        {'type': 'slash', 'delay': 2, 'at': 'caster+0,0.7,0', 'radius': 5.0, 'arc': 360, 'thickness': 0.25, 'bend': 1, 'secondary': 0, 'grow': 8,
         'life': 12, 'tilt': 0, 'pitch': 3, 'color': '@secondary'},
        {'type': 'trail', 'delay': 0, 'duration': 14, 'at': 'caster+0,1.0,0', 'width': 0.4, 'length': 8, 'head': 3, 'count': 3,
         'orbit': {'radius': 4.6, 'speed': 45, 'rise': 0.3, 'risePeriod': 10}, 'color': '@secondary', 'comment': 'раскалённый конец хлыста'},
        {'type': 'wave', 'delay': 4, 'duration': 14, 'at': 'caster', 'radius': 6, 'thickness': 0.9, 'color': '@primary', 'comment': 'отброс наружу'},
        {'type': 'wave', 'delay': 6, 'duration': 18, 'at': 'caster', 'radius': 7.5, 'thickness': 0.4, 'color': '@core'},
        {'type': 'flash', 'delay': 7, 'duration': 6, 'at': 'caster+0,1,0', 'size': 4, 'rays': 8, 'screen': 0.12, 'color': '@secondary'},
        {'type': 'decal', 'delay': 6, 'duration': 100, 'at': 'caster', 'texture': 'thin_ring', 'radius': 5.2, 'fadeOut': 50, 'color': '@primary',
         'brightness': 1.3, 'comment': 'огненное кольцо на земле'},
        {'type': 'decal', 'delay': 6, 'duration': 120, 'at': 'caster', 'texture': 'glow', 'radius': 5.6, 'fadeOut': 70, 'color': '@shadow',
         'blend': 'translucent'},
    ]
    for i in range(16):
        a = 2 * math.pi * i / 16
        x, z = 5 * math.cos(a), 5 * math.sin(a)
        E.append({'type': 'column', 'delay': 4 + i // 4, 'duration': 30, 'at': f'caster+{x:.2f},0,{z:.2f}', 'radius': 0.3, 'height': 2.2 + 0.4 * (i % 3),
                  'fill': 0.7, 'color': '@primary' if i % 2 else '@secondary', 'in': {'duration': 4, 'easing': 'easeOutBack'},
                  'out': {'duration': 16, 'easing': 'easeInSine'}})
    E.append({'type': 'sprites', 'delay': 4, 'duration': 30, 'at': 'caster+0,0.4,0', 'texture': '@sparks', 'count': 260, 'rate': 9, 'spread': 5,
              'speed': 0.05, 'gravity': -0.004, 'spin': 220, 'size': [0.16, 0.03], 'life': 30, 'color': '@primary', 'comment': 'вихрь искр'})
    dump('fx/ember_vortex.json', {
        'comment': '«Огненный вихрь» (T14, форма хлыста): at = владелец; хлыст делает оборот за 8 тиков, кольцо огня r 5, волна наружу на тике 4 '
                   '(урон, поджог и отброс кода — на этом тике). Сгенерировано tools/gen_ember_fx.py.',
        'style': 'pyre', 'duration': 120, 'elements': E})


def heat():
    dump('fx/ember_heat.json', {
        'comment': 'Раскалённый клинок (T14): пока жар > 0; at = caster.hand, follow; яркость/частоту код задаёт через scale эффекта по доле жара. '
                   'Гасится stop. Сгенерировано tools/gen_ember_fx.py.',
        'style': 'pyre', 'duration': -1, 'elements': [
            {'type': 'sprites', 'delay': 0, 'at': 'caster.hand', 'follow': True, 'texture': '@sparks', 'count': 4000, 'rate': 1.5, 'spread': 0.35,
             'speed': 0.01, 'gravity': -0.004, 'size': [0.1, 0.02], 'life': 20, 'color': '@primary'},
            {'type': 'sprites', 'delay': 0, 'at': 'caster.hand', 'follow': True, 'texture': '@sparks', 'count': 2000, 'rate': 0.6, 'spread': 0.2,
             'speed': 0.03, 'gravity': 0.01, 'size': [0.08, 0.02], 'life': 14, 'color': '@secondary', 'comment': 'капли-угли падают'}]})


def hud():
    W, H = 128, 16
    im = Image.new('RGBA', (W, 32), (0, 0, 0, 0))
    hexc = lambda h, a=255: (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)
    curve = lambda x: int(round(3 * (1 - ((x - W / 2) / (W / 2)) ** 2)))   # полоса изогнута дугой вверх к центру
    rnd = random.Random(7)
    # рамка: тёмный обугленный металл, по краям — «когти»-языки
    for x in range(W):
        top = 4 - curve(x)
        for y in range(top, top + 9):
            edge = y in (top, top + 8) or x in (0, W - 1)
            im.putpixel((x, y), hexc('#140806' if edge else ('#2A100A' if (x + y) % 7 else '#3A160C')))
        if x % 9 == 4:                                                # шипы-угли над рамкой
            for k in range(2):
                if top - 1 - k >= 0:
                    im.putpixel((x, top - 1 - k), hexc('#5A1E0C' if k else '#2A100A'))
    # заливка: тёмно-красный → оранжевый → жёлто-белый к правому краю, искорки
    ramp = ['#5A0A04', '#8A1A06', '#C2360C', '#FF6A1E', '#FF9A3A', '#FFC23A', '#FFF2C0']
    for x in range(1, W - 1):
        top = 16 + 5 - curve(x)
        k = x / (W - 1) * (len(ramp) - 1)
        c0, c1, t = ramp[int(k)], ramp[min(len(ramp) - 1, int(k) + 1)], k - int(k)
        col = tuple(int(int(c0[i:i + 2], 16) * (1 - t) + int(c1[i:i + 2], 16) * t) for i in (1, 3, 5))
        for y in range(top, top + 7):
            sh = 1.15 if y == top + 1 else (0.75 if y >= top + 5 else 1.0)
            c = tuple(min(255, int(v * sh)) for v in col) + (255,)
            if rnd.random() < 0.04:
                c = hexc('#FFF2C0')
            im.putpixel((x, y), c)
    os.makedirs(os.path.join(A, 'textures', 'gui'), exist_ok=True)
    im.save(os.path.join(A, 'textures', 'gui', 'ember_heat_bar.png'))
    print('wrote textures/gui/ember_heat_bar.png')


if __name__ == '__main__':
    last_heat()
    vortex()
    heat()
    hud()
