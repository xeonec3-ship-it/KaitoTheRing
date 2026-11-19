#!/usr/bin/env python3
"""
Превью и проверочные кадры бестиария T25 (three.js r128 + Playwright/Chromium).
  python3 tools/render_bestiary.py --html                 → tools/nightmare_bestiary_preview.html (интерактивное, three.js с CDN)
  python3 tools/render_bestiary.py --sheet out.jpg CELLS.json [--three path/three.min.js] [--size 1600x1000]
CELLS.json: {"cols": 3, "cells": [{"model": "nm_lurker", "anim": "idle", "t": 0.5, "yaw": 25, "label": "..."}]}
Без --three страница грузит three.js с cdnjs (как остальные превью в tools/).
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')

META = {}   # имя -> {'title', 'desc', 'height', 'bg'} — заполняет gen_nightmare_bestiary.META


def _b64(path):
    with open(path, 'rb') as fh:
        return 'data:image/png;base64,' + base64.b64encode(fh.read()).decode()


def data(names=None):
    sys.path.insert(0, HERE)
    import gen_nightmare_bestiary as gb
    out = {}
    for n in (names or gb.ORDER):
        geo = json.load(open(os.path.join(A, 'geo', 'entity', n + '.geo.json'), encoding='utf-8'))
        src = gb.META.get(n, {}).get('anims', n)
        an = json.load(open(os.path.join(A, 'animations', 'entity', src + '.animation.json'), encoding='utf-8'))['animations']
        an = {k.replace('animation.%s.' % src, 'animation.%s.' % n): v for k, v in an.items()}
        tex_name = gb.META.get(n, {}).get('texture', n)
        tex = os.path.join(A, 'textures', 'entity', 'nightmare', tex_name + '.png')
        prev = os.path.join(HERE, '.cache', n + '_preview.png') if n.startswith('nm_mimic') else None
        if prev:
            tex = prev
        glow = os.path.join(A, 'textures', 'entity', 'nightmare', tex_name + '_glowmask.png')
        e = {'geo': geo, 'anims': an, 'tex': _b64(tex), 'glow': _b64(glow) if os.path.exists(glow) else None}
        e.update({k: v for k, v in gb.META.get(n, {}).items() if k in ('title', 'desc', 'height', 'bg')})
        out[n] = e
    return out


def page(d, cells=None, three=None):
    with open(os.path.join(HERE, 'nightmare_bestiary_preview.template.html'), encoding='utf-8') as fh:
        html = fh.read()
    html = html.replace('/*DATA*/null', json.dumps(d, ensure_ascii=False, separators=(',', ':')))
    html = html.replace('/*CELLS*/null', json.dumps(cells, ensure_ascii=False) if cells else 'null')
    meshes = {}
    for n in ('nightmare_corridor', 'nightmare_door', 'nightmare_branches'):
        f = os.path.join(A, 'fx', 'meshes', n + '.json')
        if os.path.exists(f):
            meshes[n] = json.load(open(f, encoding='utf-8'))
    html = html.replace('/*MESHES*/null', json.dumps(meshes, separators=(',', ':')))
    if three:
        html = html.replace('https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js', 'file://' + os.path.abspath(three))
    return html


def shoot(html, out, size=(1600, 1000), scale=1):
    """Скриншот через Node Playwright (require('playwright'), Chromium с программным WebGL)."""
    import subprocess
    tmp = out + '.html'
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write(html)
    js = """
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
  const pg = await b.newPage({ viewport: { width: %d, height: %d }, deviceScaleFactor: %s });
  pg.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('console:', m.text()); });
  pg.on('pageerror', e => console.log('pageerror:', e.message));
  await pg.goto('file://%s');
  await pg.waitForFunction('window.READY === true', null, { timeout: 180000 });
  await pg.waitForTimeout(300);
  await pg.screenshot(%s);
  await b.close();
})();
""" % (size[0], size[1], scale, os.path.abspath(tmp),
       json.dumps({'path': out, 'type': 'jpeg', 'quality': 88} if out.endswith('.jpg') else {'path': out}))
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    print(r.stdout[-3000:], r.stderr[-3000:])
    os.remove(tmp)
    print('wrote', out)


if __name__ == '__main__':
    args = sys.argv[1:]
    three = None
    if '--three' in args:
        three = args[args.index('--three') + 1]
    if '--html' in args:
        with open(os.path.join(HERE, 'nightmare_bestiary_preview.html'), 'w', encoding='utf-8') as fh:
            fh.write(page(data()))
        print('wrote tools/nightmare_bestiary_preview.html')
    if '--sheet' in args:
        i = args.index('--sheet')
        out, cells = args[i + 1], json.load(open(args[i + 2], encoding='utf-8'))
        size = (1600, 1000)
        if '--size' in args:
            w, h = args[args.index('--size') + 1].split('x')
            size = (int(w), int(h))
        names = sorted({c['model'] for c in cells['cells']} | {x['model'] for c in cells['cells'] for x in c.get('models', [])})
        shoot(page(data(names), cells, three), out, size)
