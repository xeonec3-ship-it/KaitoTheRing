#!/usr/bin/env python3
"""
Собирает tools/sigil_preview.html: вшивает в шаблон все печати (assets/pohsmp_core/sigils/*.json)
и текстуры (assets/pohsmp_core/textures/sigil/*.png). Запуск: python3 tools/build_sigil_preview.py
"""
import base64
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')

data = {'sigils': {}, 'textures': {}}
for f in sorted(glob.glob(os.path.join(ASSETS, 'sigils', '*.json'))):
    data['sigils'][os.path.splitext(os.path.basename(f))[0]] = json.load(open(f, encoding='utf-8'))
for f in sorted(glob.glob(os.path.join(ASSETS, 'textures', 'sigil', '*.png'))):
    data['textures'][os.path.splitext(os.path.basename(f))[0]] = 'data:image/png;base64,' + base64.b64encode(open(f, 'rb').read()).decode()

page = open(os.path.join(HERE, 'sigil_preview.template.html'), encoding='utf-8').read()
page = page.replace('/*DATA*/null', json.dumps(data, ensure_ascii=False))
open(os.path.join(HERE, 'sigil_preview.html'), 'w', encoding='utf-8').write(page)
print('wrote tools/sigil_preview.html:', len(data['sigils']), 'sigils,', len(data['textures']), 'textures,', len(page) // 1024, 'KB')
