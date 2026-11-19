#!/usr/bin/env python3
"""
Собирает tools/sigil_preview.html: вшивает в шаблон все печати (assets/pohsmp_core/sigils/*.json)
и текстуры (assets/pohsmp_core/textures/sigil/*.png). Запуск: python3 tools/build_sigil_preview.py
"""
import base64
import glob
import io
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')

data = {'sigils': {}, 'textures': {}, 'meshes': {}, 'styles': {}, 'fx': {}, 'fonts': {}}
for f in sorted(glob.glob(os.path.join(ASSETS, 'sigils', '*.json'))):
    data['sigils'][os.path.splitext(os.path.basename(f))[0]] = json.load(open(f, encoding='utf-8'))
for f in sorted(glob.glob(os.path.join(ASSETS, 'fx', 'meshes', '*.json'))):
    data['meshes'][os.path.splitext(os.path.basename(f))[0]] = json.load(open(f, encoding='utf-8'))
for f in sorted(glob.glob(os.path.join(ASSETS, 'fx', '*.json'))):
    data['fx'][os.path.splitext(os.path.basename(f))[0]] = json.load(open(f, encoding='utf-8'))
for f in sorted(glob.glob(os.path.join(ASSETS, 'fx', 'styles', '*.json'))):
    data['styles'][os.path.splitext(os.path.basename(f))[0]] = json.load(open(f, encoding='utf-8'))
for f in sorted(glob.glob(os.path.join(ASSETS, 'textures', 'sigil', '*.png'))):
    data['textures'][os.path.splitext(os.path.basename(f))[0]] = 'data:image/png;base64,' + base64.b64encode(open(f, 'rb').read()).decode()

used = {l.get('texture') for s in data['sigils'].values() for l in s.get('layers', [])}
used |= {e.get('texture') for f in data['fx'].values() for e in f.get('elements', [])}
for f in sorted(glob.glob(os.path.join(ASSETS, 'textures', 'fx', '*.png'))):          # как в игре (FxDraw): сначала sigil/, потом fx/
    if os.path.splitext(os.path.basename(f))[0] not in used:                          # только те, что упомянуты в печатях и эффектах
        continue
    name = os.path.splitext(os.path.basename(f))[0]
    if name in data['textures']:
        continue
    im = Image.open(f)                                                                  # в превью хватит 256 px: страница не пухнет
    if max(im.size) > 256:
        im = im.resize((256, round(256 * im.size[1] / im.size[0])), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    data['textures'][name] = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

for f in sorted(glob.glob(os.path.join(ASSETS, 'textures', 'sigil', 'glyphs_*.json'))):     # карты атласов надписей (T07)
    g = json.load(open(f, encoding='utf-8'))
    data['fonts'][g['font']] = g

page = open(os.path.join(HERE, 'sigil_preview.template.html'), encoding='utf-8').read()
page = page.replace('/*DATA*/null', json.dumps(data, ensure_ascii=False))
open(os.path.join(HERE, 'sigil_preview.html'), 'w', encoding='utf-8').write(page)
print('wrote tools/sigil_preview.html:', len(data['sigils']), 'sigils,', len(data['meshes']), 'meshes,', len(data['textures']), 'textures,', len(data['fonts']), 'fonts,', len(page) // 1024, 'KB')
