#!/usr/bin/env python3
"""
Превью и проверочные кадры «Арис, Мифический Кузнец» (T28): three.js r128 + Playwright/Chromium.
Используется из tools/gen_aris.py (--html, --shots). three.js: по умолчанию с CDN; для кадров без сети — локальный three.min.js
(--three путь, или node_modules/three/build/three.min.js рядом/в каталоге запуска, или переменная ARIS_THREE).
CELLS: {"cols": 3, "cells": [{"model": "aris", "anim": "animation.aris.slam", "t": 0.75, "yaw": 25, "variant": "base", "label": "..."}]}
"""
import base64
import io
import json
import os
import subprocess

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
CDN = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'
GLOW_CELLS = []          # клетки палитры молота, которые светятся (заполняет gen_aris)


def b64(path):
    return 'data:image/png;base64,' + base64.b64encode(open(path, 'rb').read()).decode()


def find_three(explicit=None):
    for p in (explicit, os.environ.get('ARIS_THREE'), os.path.join(os.getcwd(), 'node_modules/three/build/three.min.js'),
              os.path.join(ROOT, 'node_modules/three/build/three.min.js')):
        if p and os.path.exists(p):
            return p
    return None


def data():
    T = os.path.join(A, 'textures', 'entity', 'aris')
    tex, glow = {}, {}
    for v, f in (('base', 'aris'), ('dim', 'aris_dim'), ('spent', 'aris_spent'), ('mythic', 'aris_mythic')):
        tex[v] = b64(os.path.join(T, f + '.png'))
        g = os.path.join(T, f + '_glowmask.png')
        if os.path.exists(g):
            glow[v] = b64(g)
    models = {'aris': {'geo': json.load(open(os.path.join(A, 'geo', 'entity', 'aris.geo.json'), encoding='utf-8')),
                       'tex': tex, 'glow': glow, 'height': 44, 'title': 'Арис, Мифический Кузнец'}}
    anims = json.load(open(os.path.join(A, 'animations', 'entity', 'aris.animation.json'), encoding='utf-8'))['animations']
    items = {}
    ip = os.path.join(A, 'models', 'item', 'aris_hammer.json')
    if os.path.exists(ip):
        doc = json.load(open(ip, encoding='utf-8'))
        pal = Image.open(os.path.join(A, 'textures', 'item', 'aris_hammer_3d.png')).convert('RGB')
        cols = ['#%02x%02x%02x' % pal.getpixel((i % 16, i // 16)) for i in range(256)]
        items['aris_hammer'] = {'elements': doc['elements'], 'pal': cols, 'glowCells': GLOW_CELLS, 'title': 'Молот Арис (предмет)'}
    meshes = {}
    md = os.path.join(A, 'fx', 'meshes')
    style = {}
    sp = os.path.join(A, 'fx', 'styles', 'aris.json')
    if os.path.exists(sp):
        style = json.load(open(sp, encoding='utf-8')).get('palette', {})
    if os.path.isdir(md):
        for f in sorted(os.listdir(md)):
            if f.startswith('aris_'):
                d = json.load(open(os.path.join(md, f), encoding='utf-8'))
                d['palette'] = style
                meshes[f[:-5]] = d
    return {'models': models, 'anims': anims, 'items': items, 'meshes': meshes}


def page(cells=None, three=None):
    with open(os.path.join(HERE, 'aris_preview.template.html'), encoding='utf-8') as fh:
        html = fh.read()
    html = html.replace('/*DATA*/null', json.dumps(data(), ensure_ascii=False, separators=(',', ':')))
    html = html.replace('/*CELLS*/null', json.dumps(cells, ensure_ascii=False) if cells else 'null')
    if three:
        html = html.replace(CDN, 'file://' + os.path.abspath(three))
    return html


def shoot(html, out, size=(1600, 1000), scale=1):
    tmp = out + '.html'
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write(html)
    js = """
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
  const pg = await b.newPage({ viewport: { width: %d, height: %d }, deviceScaleFactor: %s });
  pg.on('console', m => { if (m.type() === 'error') console.log('console:', m.text()); });
  pg.on('pageerror', e => console.log('pageerror:', e.message));
  await pg.goto('file://%s');
  await pg.waitForFunction('window.READY === true', null, { timeout: 240000 });
  await pg.waitForTimeout(300);
  await pg.screenshot(%s);
  await b.close();
})();
""" % (size[0], size[1], scale, os.path.abspath(tmp),
       json.dumps({'path': out, 'type': 'jpeg', 'quality': 90} if out.endswith('.jpg') else {'path': out}))
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    if r.stdout.strip() or r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
    os.remove(tmp)
    print('wrote', os.path.relpath(out, ROOT))


def sheet(out, cells, three=None, size=(1600, 1000), scale=1):
    shoot(page(cells, find_three(three)), out, size, scale)


def write_html():
    p = os.path.join(HERE, 'aris_preview.html')
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(page())
    print('wrote tools/aris_preview.html')
