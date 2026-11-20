#!/usr/bin/env python3
"""
Превью и проверочные кадры «Эреба» (T30) рядом с эталоном — Главой Культа: three.js r128 + Playwright/Chromium.
Шаблон — tools/ereb_preview.template.html (копия шаблона T26 + рапира в руке, несколько моделей в одном кадре).
  python3 tools/gen_ereb_render.py --html                  → tools/ereb_preview.html (three.js с CDN)
  из tools/gen_ereb.py --shots: R.sheet(out, cells, three)
Ячейка: {"model": "ereb", "anim": "ereb_lunge", "t": 0.5, "yaw": 25, "label": "...", "with": [{"model": "cult_leader", "x": 14}], "h": 36}
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cult_leader_render as CR  # noqa: E402

A = CR.A
CDN = CR.CDN
T = os.path.join(A, 'textures', 'entity', 'ereb')
# хват рапиры в превью (подобран по ванильному handheld: рука опущена — клинок вперёд и чуть вверх). В игре проверить.
ITEM_FIX = [-90, 0, 0]
ITEM_OFF = [0, -1, 0]


def rapier_entry():
    doc = json.load(open(os.path.join(A, 'models', 'item', 'ereb_rapier.json'), encoding='utf-8'))
    import gen_ereb as G
    cell = {v: k for k, v in G.RAP_CELL.items()}
    els = []
    for e in doc['base']['elements']:
        u, v = e['faces']['north']['uv'][:2]
        els.append([e['from'], e['to'], G.RAP_PAL[cell[(int(u), int(v))]], e.get('rotation')])
    return {'els': els, 'display': doc['base']['display']['thirdperson_righthand'], 'fix': ITEM_FIX, 'off': ITEM_OFF}


def model_entry(name):
    if name == 'ereb':
        return {'geo': json.load(open(os.path.join(A, 'geo', 'entity', 'ereb.geo.json'), encoding='utf-8')),
                'tex': CR.b64(os.path.join(T, 'ereb.png')), 'smile': CR.b64(os.path.join(T, 'ereb_smile.png')),
                'glow': CR.b64(os.path.join(T, 'ereb_glowmask.png')), 'item': rapier_entry(), 'height': 34,
                'title': 'Эреб, Первый Предатель'}
    if name == 'rapier':                # только рапира (в руке пустого каркаса) — крупный план предмета
        return {'geo': {'minecraft:geometry': [{'description': {'texture_width': 16, 'texture_height': 16},
                                                'bones': [{'name': 'bipedHandRight', 'pivot': [0, 0, 0]}]}]},
                'tex': CR.b64(os.path.join(A, 'textures', 'item', 'ereb_rapier_3d.png')), 'height': 16,
                'item': dict(rapier_entry(), display={'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]}, fix=[0, 0, 0],
                             off=[0, 0, 0])}
    if name == 'ereb_noitem':
        e = model_entry('ereb')
        e.pop('item')
        return e
    return CR.model_entry(name)


def anims():
    ours = json.load(open(os.path.join(A, 'animations', 'entity', 'ereb.animation.json'), encoding='utf-8'))['animations']
    return ours


def page(models, cells=None, three=None):
    with open(os.path.join(HERE, 'ereb_preview.template.html'), encoding='utf-8') as fh:
        html = fh.read()
    an = anims()
    if cells is not None:
        need = set()
        for c in cells['cells']:
            for w in [c] + c.get('with', []):
                if w.get('anim'):
                    need.add(w['anim'])
        an = {k: v for k, v in an.items() if k in need}
    texs = {}
    for c in (cells or {}).get('cells', []):
        for f in c.get('fx', []):
            texs[f['tex']] = CR.b64(os.path.join(A, 'textures', 'sigil', f['tex'] + '.png'))
    d = {'models': {n: model_entry(n) for n in models}, 'anims': an, 'tex': texs}
    html = html.replace('/*DATA*/null', json.dumps(d, ensure_ascii=False, separators=(',', ':')))
    html = html.replace('/*CELLS*/null', json.dumps(cells, ensure_ascii=False) if cells else 'null')
    if three:
        html = html.replace(CDN, 'file://' + os.path.abspath(three))
    return html


def sheet(out, cells, three=None, size=(1600, 1000), scale=1):
    models = set()
    for c in cells['cells']:
        models.add(c['model'])
        for w in c.get('with', []):
            models.add(w['model'])
    CR.shoot(page(sorted(models), cells, three), out, size, scale)


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--html' in args:
        with open(os.path.join(HERE, 'ereb_preview.html'), 'w', encoding='utf-8') as fh:
            fh.write(page(['ereb', 'cult_leader']))
        print('wrote tools/ereb_preview.html')
