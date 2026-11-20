#!/usr/bin/env python3
"""
Превью и проверочные кадры T29 «Мартин» (three.js r128 + Playwright/Chromium). Вызывается из gen_martin*.py; можно и напрямую:
  python3 tools/martin_render.py --html                       → tools/martin_preview.html (интерактивное, three.js с CDN)
  python3 tools/martin_render.py --sheet out.jpg CELLS.json [--three path/three.min.js] [--size 1600x1000]
CELLS: {"cols": 3, "cells": [{"model": "martin", "anim": "martin_idle", "t": 0.5, "yaw": 25, "label": "...",
         "models": [{"model": "martin_soldier", "anim": "...", "pos": [x, y, z], "ry": 0}], "meshes": [{"mesh": "...", "pos": [..]}],
         "decals": [{"tex": "...", "pos": [x, y, z], "r": 3}]}]}
"""
import base64
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
CDN = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'

MODELS = {   # имя -> (geo, текстура, glow, анимации, рост для камеры, масштаб в мире, прочее)
    'martin': dict(geo='martin', tex='martin/martin', anims='martin', height=66, scale=2, title='Мартин, Последний Полководец (×2)',
                   bg=0x231a1c, ironsHide='martin_'),
    'martin_soldier': dict(geo='martin_soldier', tex='martin/martin_soldier', anims='martin_soldier', height=34, scale=1, opacity=0.84,
                           emissive=0x08121a, title='Призрачный солдат', bg=0x141c24),
    'martin_banner': dict(geo='martin_banner', tex='martin/martin_banner', anims='martin_banner', height=60, scale=1, title='Знамя Мартина',
                          bg=0x231a1c),
    'cult_leader': dict(geo='cult_leader', tex='cult_leader/cult_leader', anims='cult_leader', height=36, scale=1,
                        title='Глава Культа (эталон, T26)', bg=0x231a1c),
}


def _b64(path):
    with open(path, 'rb') as fh:
        return 'data:image/png;base64,' + base64.b64encode(fh.read()).decode()


def data(names=None):
    out = {}
    for n in (names or MODELS):
        e = MODELS[n]
        geo = os.path.join(A, 'geo', 'entity', e['geo'] + '.geo.json')
        if not os.path.exists(geo):
            continue
        d = {k: v for k, v in e.items() if k not in ('geo', 'tex', 'anims')}
        d['geo'] = json.load(open(geo, encoding='utf-8'))
        d['tex'] = _b64(os.path.join(A, 'textures', 'entity', e['tex'] + '.png'))
        g = os.path.join(A, 'textures', 'entity', e['tex'] + '_glowmask.png')
        d['glow'] = _b64(g) if os.path.exists(g) else None
        an = os.path.join(A, 'animations', 'entity', e['anims'] + '.animation.json')
        d['anims'] = json.load(open(an, encoding='utf-8'))['animations'] if os.path.exists(an) else {}
        out[n] = d
    return out


def textures(names):
    t = {}
    for n in names:
        for sub in ('sigil', 'fx'):
            p = os.path.join(A, 'textures', sub, n + '.png')
            if os.path.exists(p):
                t[n] = _b64(p)
                break
    return t


def page(d, cells=None, three=None, meshes=None, texs=None):
    with open(os.path.join(HERE, 'martin_preview.template.html'), encoding='utf-8') as fh:
        html = fh.read()
    html = html.replace('/*DATA*/null', json.dumps(d, ensure_ascii=False, separators=(',', ':')))
    html = html.replace('/*CELLS*/null', json.dumps(cells, ensure_ascii=False) if cells else 'null')
    ms = {}
    for n in (meshes or []):
        f = os.path.join(A, 'fx', 'meshes', n + '.json')
        if os.path.exists(f):
            ms[n] = json.load(open(f, encoding='utf-8'))
    html = html.replace('/*MESHES*/null', json.dumps(ms, separators=(',', ':')))
    html = html.replace('/*TEXS*/null', json.dumps(textures(texs or []), separators=(',', ':')))
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
    print('wrote', out)


def sheet(out, cells, three=None, size=(1600, 1000), scale=1):
    names = set()
    meshes, texs = set(), set()
    for c in cells['cells']:
        names.add(c['model'])
        for x in c.get('models', []):
            names.add(x['model'])
        for x in c.get('meshes', []):
            meshes.add(x['mesh'])
        for x in c.get('decals', []):
            texs.add(x['tex'])
    for n in meshes:
        f = os.path.join(A, 'fx', 'meshes', n + '.json')
        if os.path.exists(f):
            for p in json.load(open(f, encoding='utf-8'))['parts']:
                if p.get('texture'):
                    texs.add(p['texture'])
    shoot(page(data(sorted(names)), cells, three, sorted(meshes), sorted(texs)), out, size, scale)


def html_preview():
    with open(os.path.join(HERE, 'martin_preview.html'), 'w', encoding='utf-8') as fh:
        fh.write(page(data()))
    print('wrote tools/martin_preview.html')


if __name__ == '__main__':
    args = sys.argv[1:]
    three = args[args.index('--three') + 1] if '--three' in args else None
    if '--html' in args:
        html_preview()
    if '--sheet' in args:
        i = args.index('--sheet')
        size = (1600, 1000)
        if '--size' in args:
            w, h = args[args.index('--size') + 1].split('x')
            size = (int(w), int(h))
        sheet(args[i + 1], json.load(open(args[i + 2], encoding='utf-8')), three, size)
