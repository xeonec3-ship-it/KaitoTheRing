#!/usr/bin/env python3
"""
Превью и проверочные кадры «Главы Культа Меллисто» (T26): three.js r128 + Playwright/Chromium.
Используется из tools/gen_cult_leader.py (--html, --shots); можно и напрямую:
  python3 tools/cult_leader_render.py --html                      → tools/cult_leader_preview.html (three.js с CDN)
  python3 tools/cult_leader_render.py --sheet out.jpg CELLS.json [--three path/three.min.js] [--size 1600x1000]
CELLS.json: {"cols": 3, "cells": [{"model": "cult_leader", "anim": "fire_boss_spawn", "t": 6.5, "yaw": 25, "label": "..."}]}
Анимации берутся из jar Iron's (libs/irons_spellbooks-1.20.1-3.16.1.jar, casting_animations.json) — босс играет их же.
"""
import base64
import io
import json
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
JAR = os.path.join(ROOT, 'libs', 'irons_spellbooks-1.20.1-3.16.1.jar')
CDN = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'


def jar_bytes(path):
    with zipfile.ZipFile(JAR) as z:
        return z.read(path)


def jar_json(path):
    return json.loads(jar_bytes(path).decode('utf-8'))


def b64(data_or_path):
    data = data_or_path if isinstance(data_or_path, (bytes, bytearray)) else open(data_or_path, 'rb').read()
    return 'data:image/png;base64,' + base64.b64encode(data).decode()


def pil_b64(img):
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    return b64(buf.getvalue())


def iron_anims(names=None):
    ours = os.path.join(A, 'animations', 'entity', 'cult_leader.animation.json')     # наш файл = анимации Iron's + cult_leader_*
    an = (json.load(open(ours, encoding='utf-8')) if os.path.exists(ours)
          else jar_json('assets/irons_spellbooks/animations/casting_animations.json'))['animations']
    return {k: v for k, v in an.items() if names is None or k in names}


def model_entry(name):
    """Наши модели из assets (после генерации)."""
    if name == 'tyros':                 # исходник Iron's — для сравнения
        I = 'assets/irons_spellbooks/'
        return {'geo': jar_json(I + 'geo/tyros.geo.json'), 'tex': b64(jar_bytes(I + 'textures/entity/fire_boss/tyros.png')),
                'soul': b64(jar_bytes(I + 'textures/entity/fire_boss/tyros_soul_mode.png')),
                'flame': b64(jar_bytes(I + 'textures/entity/fire_boss/tyros_flame.png')), 'scythe': True, 'height': 34,
                'title': 'Эхо Тироса (исходник Iron\'s)'}
    T = os.path.join(A, 'textures', 'entity', 'cult_leader')
    if name == 'cult_leader':
        e = {'geo': json.load(open(os.path.join(A, 'geo', 'entity', 'cult_leader.geo.json'), encoding='utf-8')),
             'tex': b64(os.path.join(T, 'cult_leader.png')), 'soul': b64(os.path.join(T, 'cult_leader_soul_mode.png')),
             'glow': b64(os.path.join(T, 'cult_leader_glowmask.png')), 'soulGlow': b64(os.path.join(T, 'cult_leader_soul_mode_glowmask.png')),
             'flame': b64(os.path.join(T, 'cult_leader_flame.png')), 'scythe': True, 'height': 36, 'title': 'Head of the Cult of Mellisto'}
        return e
    if name == 'fire_cultist':
        return {'geo': json.load(open(os.path.join(A, 'geo', 'entity', 'fire_cultist.geo.json'), encoding='utf-8')),
                'tex': b64(os.path.join(T, 'fire_cultist.png')), 'glow': b64(os.path.join(T, 'fire_cultist_glowmask.png')),
                'height': 33, 'title': 'Огненный культист'}
    if name == 'steve':                 # игрок для сравнения роста: каркас мага Iron's + простой «Стив» (рисуется здесь, в мод не идёт)
        return {'geo': jar_json('assets/irons_spellbooks/geo/abstract_casting_mob.geo.json'), 'tex': pil_b64(steve_skin()), 'height': 32,
                'title': 'игрок'}
    if name == 'pyromancer':
        I = 'assets/irons_spellbooks/'
        return {'geo': jar_json(I + 'geo/abstract_casting_mob.geo.json'), 'tex': b64(jar_bytes(I + 'textures/entity/pyromancer.png')),
                'height': 32, 'title': 'Пиромант (исходник)'}
    raise KeyError(name)


def steve_skin():
    from PIL import Image, ImageDraw
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    SK, HA, SH, PA, BO = (188, 134, 98, 255), (59, 40, 26, 255), (0, 168, 168, 255), (60, 60, 170, 255), (90, 90, 90, 255)

    def box(u, v, w, h, dd, side, top=None, bottom=None, front=None):
        d.rectangle([u, v + dd, u + 2 * (dd + w) - 1, v + dd + h - 1], fill=side)
        d.rectangle([u + dd, v, u + dd + w - 1, v + dd - 1], fill=top or side)
        d.rectangle([u + dd + w, v, u + dd + 2 * w - 1, v + dd - 1], fill=bottom or side)
        if front:
            front(u + dd, v + dd)
    def face(x, y):
        d.rectangle([x, y, x + 7, y + 1], fill=HA)
        d.point((x + 1, y + 4), fill=(255, 255, 255, 255)); d.point((x + 2, y + 4), fill=(70, 50, 140, 255))
        d.point((x + 6, y + 4), fill=(255, 255, 255, 255)); d.point((x + 5, y + 4), fill=(70, 50, 140, 255))
        d.rectangle([x + 3, y + 6, x + 4, y + 6], fill=(110, 60, 40, 255))
    box(0, 0, 8, 8, 8, SK, top=HA, front=face)
    d.rectangle([0, 8, 31, 9], fill=HA)
    face(8, 8)
    box(16, 16, 8, 12, 4, SH)
    for (u, v) in ((40, 16), (32, 48)):
        box(u, v, 4, 12, 4, SK)
        d.rectangle([u, v + 4, u + 15, v + 8], fill=SH)
    for (u, v) in ((0, 16), (16, 48)):
        box(u, v, 4, 12, 4, PA)
        d.rectangle([u, v + 13, u + 15, v + 15], fill=BO)
    return im


def page(models, cells=None, three=None, anims=None):
    with open(os.path.join(HERE, 'cult_leader_preview.template.html'), encoding='utf-8') as fh:
        html = fh.read()
    if anims is None:
        need = None if cells is None else ({c['anim'] for c in cells['cells'] if c.get('anim')}
                                           | {x['anim'] for c in cells['cells'] for x in c.get('models', []) if x.get('anim')})
        anims = iron_anims(need)
    d = {'models': {n: model_entry(n) for n in models}, 'anims': anims}
    html = html.replace('/*DATA*/null', json.dumps(d, ensure_ascii=False, separators=(',', ':')))
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
  pg.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') console.log('console:', m.text()); });
  pg.on('pageerror', e => console.log('pageerror:', e.message));
  await pg.goto('file://%s');
  await pg.waitForFunction('window.READY === true', null, { timeout: 180000 });
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
    models = sorted({c['model'] for c in cells['cells']} | {x['model'] for c in cells['cells'] for x in c.get('models', [])})
    shoot(page(models, cells, three), out, size, scale)


if __name__ == '__main__':
    args = sys.argv[1:]
    three = args[args.index('--three') + 1] if '--three' in args else None
    if '--html' in args:
        names = ['cult_leader', 'fire_cultist', 'tyros', 'pyromancer']
        with open(os.path.join(HERE, 'cult_leader_preview.html'), 'w', encoding='utf-8') as fh:
            fh.write(page(names, anims=iron_anims()))
        print('wrote tools/cult_leader_preview.html')
    if '--sheet' in args:
        i = args.index('--sheet')
        out, cells = args[i + 1], json.load(open(args[i + 2], encoding='utf-8'))
        size = (1600, 1000)
        if '--size' in args:
            w, h = args[args.index('--size') + 1].split('x')
            size = (int(w), int(h))
        sheet(out, cells, three, size)
