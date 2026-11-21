#!/usr/bin/env python3
"""
Рендер эталона Epic Fight / Nightfall / Weapons of Miracles (biped) — для ИЗУЧЕНИЯ (кадр-листы «эталон: фазы удара»).
Данные анимаций читаются из jar вне репо (tools/ef_ref.py, EF_REF_DIR) и вшиваются во ВРЕМЕННЫЙ html (tempfile, вне репо);
в docs/media попадает только картинка — наш рендер манекена.
  python3 tools/ef_ref_render.py --sheet out.jpg CELLS.json [--three three.min.js] [--size 1600x900]
CELLS: {"cols": 6, "cells": [{"ref": "NF ng_great_auto1", "t": 0.5, "yaw": 60, "pitch": 10, "dist": 2.4, "label": "...", "scale": 1}]}
  ref — ключ из ef_ref.REF_SET / REF_THRUST / REF_IDLE или «src:путь/в/jar.json».
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ef_ref as R  # noqa: E402

CDN = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'
ALL = {}
ALL.update(R.REF_SET)
ALL.update(R.REF_THRUST)
ALL.update(R.REF_IDLE)


def load(jars, key):
    if key in ALL:
        src, mem = ALL[key][0], ALL[key][1]
    else:
        src, mem = key.split(':', 1)
    return R.EFAnim(jars, mem, src)


def payload(jars, keys):
    parent, order, bind = R.armature(jars)
    out = {'joints': [{'name': n, 'parent': parent[n], 'bind': [float(x) for x in bind[n].reshape(-1)]} for n in order], 'anims': {}}
    for k in keys:
        an = load(jars, k)
        tr = {}
        for j, (ts, qs, ps) in an.tracks.items():
            tr[j] = {'t': [float(x) for x in ts], 'q': [[float(x) for x in q] for q in qs], 'p': [[float(x) for x in p] for p in ps]}
        out['anims'][k] = {'length': an.length, 'tracks': tr}
    return out


def html(jars, cells, three=None):
    keys = sorted({c['ref'] for c in cells['cells']})
    for c in cells['cells']:
        c['anim'] = c['ref']
    with open(os.path.join(HERE, 'ef_ref_preview.template.html'), encoding='utf-8') as fh:
        h = fh.read()
    h = h.replace('/*REF*/null', json.dumps(payload(jars, keys), separators=(',', ':')))
    h = h.replace('/*CELLS*/null', json.dumps(cells, ensure_ascii=False))
    if three:
        h = h.replace(CDN, 'file://' + os.path.abspath(three))
    return h


def shoot(page, out, size=(1600, 900)):
    fd, tmp = tempfile.mkstemp(suffix='.html', prefix='ef_ref_')          # вне репо: данные эталона в git не попадают
    with os.fdopen(fd, 'w', encoding='utf-8') as fh:
        fh.write(page)
    js = """
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
  const pg = await b.newPage({ viewport: { width: %d, height: %d }, deviceScaleFactor: 1 });
  pg.on('pageerror', e => console.log('pageerror:', e.message));
  await pg.goto('file://%s');
  await pg.waitForFunction('window.READY === true', null, { timeout: 240000 });
  await pg.screenshot(%s);
  await b.close();
})();
""" % (size[0], size[1], tmp, json.dumps({'path': out, 'type': 'jpeg', 'quality': 92} if out.endswith('.jpg') else {'path': out}))
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    os.remove(tmp)
    if r.stdout.strip() or r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])


def sheet(out, cells, three=None, size=(1600, 900), ref_dir=None):
    jars = R.find_jars(ref_dir)
    shoot(html(jars, cells, three), out, size)
    print('wrote', out)


if __name__ == '__main__':
    a = sys.argv[1:]
    three = a[a.index('--three') + 1] if '--three' in a else None
    size = tuple(int(x) for x in a[a.index('--size') + 1].split('x')) if '--size' in a else (1600, 900)
    i = a.index('--sheet')
    sheet(a[i + 1], json.load(open(a[i + 2], encoding='utf-8')), three, size)
