#!/usr/bin/env python3
"""
«Дезинтеграция: Реплика» (Высшая) — те же печати и шкала, что у Дезинтеграции, но алые.
Берёт assets/pohsmp_core/sigils/disintegration_*.json и fx/disintegration.json, перекрашивает
золото в алый (белое ядро остаётся белым) и пишет disintegration_replica_*.json и fx/disintegration_replica.json.
Запускать после любой правки оригинала: python3 tools/gen_replica_fx.py
"""
import colorsys
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
HEX = re.compile(r'^#[0-9A-Fa-f]{6}$')


def scarlet(c):
    r, g, b = (int(c[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if s < 0.08:                      # белое ядро не трогаем
        return c.upper()
    h = ((352 + (h * 360 - 40) * 0.4) % 360) / 360
    s = min(1.0, s * 1.2 + 0.05)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return '#%02X%02X%02X' % (round(r * 255), round(g * 255), round(b * 255))


def conv(o, top=False):
    if isinstance(o, dict):
        return {k: conv(v) for k, v in o.items()}
    if isinstance(o, list):
        return [conv(v) for v in o]
    if isinstance(o, str):
        if HEX.match(o):
            return scarlet(o)
        if o.startswith('disintegration_') and not o.startswith('disintegration_replica'):
            return 'disintegration_replica_' + o[len('disintegration_'):]
    return o


n = 0
for f in sorted(glob.glob(os.path.join(A, 'sigils', 'disintegration_*.json'))):
    name = os.path.splitext(os.path.basename(f))[0]
    if name.startswith('disintegration_replica'):
        continue
    d = conv(json.load(open(f, encoding='utf-8')))
    out = os.path.join(A, 'sigils', 'disintegration_replica_' + name[len('disintegration_'):] + '.json')
    json.dump(d, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    n += 1

fx = conv(json.load(open(os.path.join(A, 'fx', 'disintegration.json'), encoding='utf-8')))
fx['style'] = 'higher'
fx['comment'] = 'Дезинтеграция: Реплика (Высшая). Сгенерировано tools/gen_replica_fx.py из disintegration.json — правьте оригинал.'
for e in fx['elements']:
    if e.get('type') == 'tint':
        e['color'] = '#A0101E'
json.dump(fx, open(os.path.join(A, 'fx', 'disintegration_replica.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('replica:', n, 'sigils + fx/disintegration_replica.json')
