#!/usr/bin/env python3
"""
Превью и проверочные кадры «Эреба, Длани Лжи» (T31) рядом с Эребом T30 и эталоном (Глава Культа): three.js r128 + Playwright/Chromium.
Шаблон — tools/ereb_hand_preview.template.html (копия шаблона T30 + полупрозрачные кости ghost_*, скрытие костей, варианты текстуры).
  python3 tools/gen_ereb_hand_render.py --html            → tools/ereb_hand_preview.html (three.js с CDN)
Ячейка: {"model": "ereb_hand", "anim": "ereb_hand_idle", "t": 0.5, "yaw": 25, "variant": "cracked", "hideBones": ["mask"], "with": [...]}
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cult_leader_render as CR   # noqa: E402
import gen_ereb_render as ER      # noqa: E402

A = CR.A
CDN = CR.CDN
T = os.path.join(A, 'textures', 'entity', 'ereb_hand')
VARIANTS = ('ereb_hand', 'ereb_hand_mended', 'ereb_hand_cracked')


def rapier_entry():
    doc = json.load(open(os.path.join(A, 'models', 'item', 'ereb_hand_rapier.json'), encoding='utf-8'))
    import gen_ereb as E
    import gen_ereb_hand as H
    cell = {v: k for k, v in E.RAP_CELL.items()}
    els = []
    for e in doc['base']['elements']:
        u, v = e['faces']['north']['uv'][:2]
        els.append([e['from'], e['to'], H.RAP_PAL[cell[(int(u), int(v))]], e.get('rotation')])
    return {'els': els, 'display': doc['base']['display']['thirdperson_righthand'], 'fix': ER.ITEM_FIX, 'off': ER.ITEM_OFF}


def model_entry(name):
    if name in ('ereb_hand', 'ereb_hand_noitem'):
        e = {'geo': json.load(open(os.path.join(A, 'geo', 'entity', 'ereb_hand.geo.json'), encoding='utf-8')),
             'tex': CR.b64(os.path.join(T, 'ereb_hand.png')), 'glow': CR.b64(os.path.join(T, 'ereb_hand_glowmask.png')),
             'variants': {v.replace('ereb_hand_', '').replace('ereb_hand', 'base'): {'tex': CR.b64(os.path.join(T, v + '.png')),
                                                                                       'glow': CR.b64(os.path.join(T, v + '_glowmask.png'))}
                          for v in VARIANTS},
             'height': 34, 'title': 'Эреб, Длань Лжи'}
        if name == 'ereb_hand':
            e['item'] = rapier_entry()
        return e
    if name == 'ereb_hand_giant':        # огромная рука: те же кости и атлас, что рука модели (масштаб — в ячейке/кадре)
        return {'geo': json.load(open(os.path.join(A, 'geo', 'entity', 'ereb_hand_giant.geo.json'), encoding='utf-8')),
                'tex': CR.b64(os.path.join(T, 'ereb_hand.png')), 'glow': CR.b64(os.path.join(T, 'ereb_hand_glowmask.png')), 'height': 16,
                'title': 'Огромная рука'}
    if name == 'hand_rapier':
        return {'geo': {'minecraft:geometry': [{'description': {'texture_width': 16, 'texture_height': 16},
                                                'bones': [{'name': 'bipedHandRight', 'pivot': [0, 0, 0]}]}]},
                'tex': CR.b64(os.path.join(A, 'textures', 'item', 'ereb_hand_rapier_3d.png')), 'height': 16,
                'item': dict(rapier_entry(), display={'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [1, 1, 1]}, fix=[0, 0, 0],
                             off=[0, 0, 0])}
    return ER.model_entry(name)


def tex_b64(n):
    for sub in ('sigil', 'fx'):
        p = os.path.join(A, 'textures', sub, n + '.png')
        if os.path.exists(p):
            return CR.b64(p)
    raise FileNotFoundError(n)


def anims():
    an = json.load(open(os.path.join(A, 'animations', 'entity', 'ereb_hand.animation.json'), encoding='utf-8'))['animations']
    an.update({k: v for k, v in ER.anims().items() if k.startswith('ereb_')})
    an.update(json.load(open(os.path.join(A, 'animations', 'entity', 'ereb_hand_giant.animation.json'), encoding='utf-8'))['animations'])
    return an


def page(models, cells=None, three=None):
    with open(os.path.join(HERE, 'ereb_hand_preview.template.html'), encoding='utf-8') as fh:
        html = fh.read()
    an = anims()
    if cells is not None:
        need = {w.get('anim') for c in cells['cells'] for w in [c] + c.get('with', []) if w.get('anim')}
        an = {k: v for k, v in an.items() if k in need}
    texs, meshes = {}, {}
    for c in (cells or {}).get('cells', []):
        for f in c.get('fx', []):
            texs[f['tex']] = tex_b64(f['tex'])
        for x in c.get('meshes', []):
            mj = json.load(open(os.path.join(A, 'fx', 'meshes', x['mesh'] + '.json'), encoding='utf-8'))
            meshes[x['mesh']] = mj
            for part in mj['parts']:
                if part['type'] == 'quad':
                    texs[part['texture']] = tex_b64(part['texture'])
    d = {'models': {n: model_entry(n) for n in models}, 'anims': an, 'tex': texs, 'meshes': meshes}
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
    if '--html' in sys.argv:
        with open(os.path.join(HERE, 'ereb_hand_preview.html'), 'w', encoding='utf-8') as fh:
            fh.write(page(['ereb_hand', 'ereb', 'cult_leader']))
        print('wrote tools/ereb_hand_preview.html')
