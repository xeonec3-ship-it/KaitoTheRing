#!/usr/bin/env python3
"""
Переводит печати Дезинтеграции на формирование «как небесная печать Silent Gate» (silent_gate_sky):
4 дуги смыкаются в кольцо и быстро крутятся → свечение → слои изнутри наружу (ядро с отскоком, кольца,
руны прорисовываются, обод) → вся печать растёт ×4 → белая вспышка с искрами; разборка — обратный порядок со сжатием в точку.
Цвета и рисунок каждой печати (канон «Слизи») не меняются. Запуск: python3 tools/apply_silent_gate_formation.py
(потом tools/gen_replica_fx.py — алая копия).
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SIG = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'sigils')
NAMES = ['field', 'top', 'tier', 'sunburst', 'wave', 'frame', 'crown', 'apex', 'caster', 'bead']
EXPAND = 4.0


def timings(d):
    end = max(l['appear'].get('delay', 0) + l['appear'].get('duration', 0) for l in d['layers'])
    e = d.get('expand')
    return end, (end + e['delay'] + e['duration']) if e else end


def convert(d, final_size, small):
    layers = d['layers']
    glow = next((l for l in layers if l['id'] == 'glow'), None)
    arcs = next((l for l in layers if l['type'] == 'arcs'), None)
    rest = [l for l in layers if l is not glow and l is not arcs]
    outer = max([1.0] + [l.get('radius', 1.0) for l in rest])
    if arcs is None:
        arcs = {'id': 'arcs', 'type': 'arcs', 'texture': 'arc_strip', 'radius': outer, 'width': 0.05, 'heightOffset': 0.0,
                'count': 4, 'arcLength': 55, 'color': '#FFFFFF'}
    arcs.update({'radius': outer, 'count': 4, 'arcLength': 55,
                 'appear': {'delay': 0, 'duration': 22, 'easing': 'easeInOutCubic', 'modes': ['assemble', 'fade']},
                 'rotation': {'speed': 60, 'boost': 3.0}})
    if glow is None:
        glow = {'id': 'glow', 'type': 'disc', 'texture': 'glow', 'radius': 0.55, 'heightOffset': -0.01, 'brightness': 0.8}
    glow['appear'] = {'delay': 18, 'duration': 10, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}
    glow['pulse'] = {'amp': 0.25, 'period': 30}
    rest.sort(key=lambda l: l.get('radius', 1.0))
    step = 4 if small else 6
    for i, l in enumerate(rest):
        first, last = i == 0, i == len(rest) - 1
        if l['type'] == 'band':
            ap = {'delay': 22 + i * step, 'duration': 10, 'easing': 'easeInOutSine', 'modes': ['draw']}
            if 'startAngle' in l.get('appear', {}):
                ap['startAngle'] = l['appear']['startAngle']
        elif first:
            ap = {'delay': 22, 'duration': 8, 'easing': 'easeOutBack', 'modes': ['grow', 'fade']}
        elif last and len(rest) > 1:
            ap = {'delay': 22 + i * step, 'duration': 8, 'easing': 'easeOutCubic', 'modes': ['fade', 'grow']}
        else:
            ap = {'delay': 22 + i * step, 'duration': 8, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}
        if 'unfold' in l.get('appear', {}).get('modes', []):      # печать заклинателя ещё и разворачивается к зрителю
            ap['modes'] = ['unfold'] + ap['modes']
        l['appear'] = ap
        rot = l.setdefault('rotation', {'speed': 8 if i % 2 else -8})
        rot['boost'] = 2.0
    d['layers'] = [arcs, glow] + rest
    d['size'] = round(final_size / EXPAND, 4)
    d['expand'] = {'scale': EXPAND, 'delay': 4, 'duration': 20, 'easing': 'easeOutCubic'}
    d['formedFlash'] = {'color': '#FFFFFF', 'size': 1.25, 'duration': 12, 'sparks': 12 if small else 40}
    d['dissolve'] = {'modes': ['reverse', 'collapse'], 'duration': 20, 'stagger': 3}
    d['comment'] = (d.get('comment', '').split(' Формирование')[0] +
                    ' Формирование — как у небесной печати Silent Gate (tools/apply_silent_gate_formation.py); итоговый радиус %s.' % final_size)
    return d


for n in NAMES:
    f = os.path.join(SIG, 'disintegration_%s.json' % n)
    d = json.load(open(f, encoding='utf-8'))
    final = d['size'] * d['expand']['scale'] if 'expand' in d else d['size']
    if 'expand' in d:                       # уже переведена: пересобрать с итогового размера
        pass
    d = convert(d, final, n == 'bead')
    json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    end, formed = timings(d)
    print('%-10s r %.2f  слои до %d, сформирована на %d тике' % (n, final, end, formed))
