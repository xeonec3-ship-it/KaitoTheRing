#!/usr/bin/env python3
"""
Превью и проверочные кадры «Ирины, Ведьмы Ревности» (T27): three.js r128 + Playwright/Chromium.
Используется из tools/gen_irina.py (--html, --shots); можно и напрямую:
  python3 tools/irina_render.py --html                                     → tools/irina_preview.html (three.js с CDN)
  python3 tools/irina_render.py --sheet out.jpg CELLS.json [--three путь/three.min.js] [--size 1600x1000]
CELLS.json: {"cols": 3, "cells": [{"anim": "irina_idle", "cloth": "irina_cloth_idle", "t": 0.5, "yaw": 25, "label": "..."}]}
"""
import base64
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
MEDIA = os.path.join(ROOT, 'docs', 'media')
CDN = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'


def b64(path):
    return 'data:image/png;base64,' + base64.b64encode(open(path, 'rb').read()).decode()


def data():
    sys.path.insert(0, HERE)
    import gen_irina_staff
    T = os.path.join(A, 'textures', 'entity', 'irina')
    return {'geo': json.load(open(os.path.join(A, 'geo', 'entity', 'irina.geo.json'), encoding='utf-8')),
            'tex': b64(os.path.join(T, 'irina.png')), 'glow': b64(os.path.join(T, 'irina_glowmask.png')),
            'anims': json.load(open(os.path.join(A, 'animations', 'entity', 'irina.animation.json'), encoding='utf-8'))['animations'],
            'staff': gen_irina_staff.preview_data(), 'height': 52,
            'cl': {'geo': json.load(open(os.path.join(A, 'geo', 'entity', 'cult_leader.geo.json'), encoding='utf-8')),
                   'tex': b64(os.path.join(A, 'textures', 'entity', 'cult_leader', 'cult_leader.png')),
                   'glow': b64(os.path.join(A, 'textures', 'entity', 'cult_leader', 'cult_leader_glowmask.png'))}}


def page(cells=None, three=None):
    html = open(os.path.join(HERE, 'irina_preview.template.html'), encoding='utf-8').read()
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
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=600)
    if r.stdout.strip() or r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
    os.remove(tmp)
    print('wrote', os.path.relpath(out, ROOT))


def sheet(out, cells, three=None, size=(1600, 1000), scale=1):
    shoot(page(cells, three), out, size, scale)


def write_html():
    with open(os.path.join(HERE, 'irina_preview.html'), 'w', encoding='utf-8') as fh:
        fh.write(page())
    print('wrote tools/irina_preview.html')


def three_arg(args):
    if '--three' in args:
        return args[args.index('--three') + 1]
    for p in (os.path.join(HERE, 'node_modules', 'three', 'build', 'three.min.js'),):
        if os.path.exists(p):
            return p
    return None


def shots(args):
    three = three_arg(args)
    os.makedirs(MEDIA, exist_ok=True)
    V = dict(dist=1.25, ty=26, pitch=4)
    sheet(os.path.join(MEDIA, 't27_model.jpg'), {'cols': 4, 'cells': [
        dict(V, yaw=0, label='Спереди', sub='лицо под полями шляпы'),
        dict(V, yaw=35, label='Три четверти'),
        dict(V, yaw=110, label='Сбоку'),
        dict(V, yaw=200, label='Сзади', sub='хвост капюшона, кушак'),
    ]}, three, (1800, 1000))
    # сверка с референсом владельца (тот же ракурс 3/4, тёмный фон)
    tmp = os.path.join(MEDIA, '_t27_ref_tmp.jpg')
    sheet(tmp, {'cols': 2, 'cells': [dict(yaw=-28, pitch=10, dist=2.5, ty=28, bg='#050307', ground=False, label='модель (ракурс референса)'),
                                     dict(yaw=28, pitch=10, dist=2.5, ty=28, bg='#050307', ground=False, label='с другой стороны')]},
          three, (1200, 800))
    from PIL import Image
    r = Image.open(os.path.join(ROOT, 'docs', 'references', 't27', 'irina_look.jpg')).convert('RGB').resize((735, 738))
    mm = Image.open(tmp).convert('RGB')
    c = Image.new('RGB', (735 + 553 * 2, 738))
    c.paste(r, (0, 0))
    c.paste(mm.crop((0, 0, 600, 800)).resize((553, 738)), (735, 0))
    c.paste(mm.crop((600, 0, 1200, 800)).resize((553, 738)), (735 + 553, 0))
    c.save(os.path.join(MEDIA, 't27_vs_reference.jpg'), quality=90)
    os.remove(tmp)
    print('wrote docs/media/t27_vs_reference.jpg')
    sheet(os.path.join(MEDIA, 't27_vs_cult_leader.jpg'), {'cols': 2, 'cells': [
        dict(compare=13, yaw=0, pitch=4, dist=1.9, ty=26, label='Ирина ← → Глава Культа (эталон)', sub='один масштаб и свет, спереди'),
        dict(compare=13, yaw=30, pitch=4, dist=1.9, ty=26, label='три четверти'),
        dict(compare=13, yaw=0, pitch=2, dist=0.75, ty=31, tx=-13, label='капюшон крупно', sub='лица нет — тьма, как на референсе'),
        dict(compare=13, yaw=180, pitch=4, dist=1.9, ty=26, label='сзади'),
    ]}, three, (1800, 1400))
    an = [('irina_idle', 1.0, 'idle'), ('irina_walk', 0.3, 'walk'), ('irina_cast_short', 0.35, 'cast_short'), ('irina_cast_long', 0.6, 'cast_long'),
          ('irina_staff_attack', 0.3, 'staff_attack: замах'), ('irina_staff_attack', 0.6, 'staff_attack: удар'),
          ('irina_mark', 0.8, 'mark'), ('irina_bind', 0.9, 'bind'), ('irina_whip', 0.45, 'whip'), ('irina_steal', 1.25, 'steal'),
          ('irina_phase2', 1.0, 'phase2'), ('irina_phase3', 1.4, 'phase3')]
    sheet(os.path.join(MEDIA, 't27_anims.jpg'), {'cols': 6, 'cells': [
        dict(anim=a, t=t, cloth='irina_cloth_storm' if a not in ('irina_idle', 'irina_walk') else
             ('irina_cloth_walk' if a == 'irina_walk' else 'irina_cloth_idle'), yaw=30, dist=1.45, ty=26, label=l) for a, t, l in an]},
          three, (2000, 1000))
    sp = [('irina_spawn', 'irina_cloth_spawn', 1.0, 'spawn 1.0: кокон'), ('irina_spawn', 'irina_cloth_spawn', 3.4, 'spawn 3.4: нити расходятся'),
          ('irina_spawn', 'irina_cloth_spawn', 5.6, 'spawn 5.6: взмах'),
          ('irina_others_happiness', 'irina_cloth_storm', 2.2, '«Чужое счастье» 2.2'), ('irina_others_happiness', 'irina_cloth_storm', 4.6, '«Чужое счастье» 4.6'),
          ('irina_only_mine', 'irina_cloth_cocoon', 0.7, '«Только мой» 0.7: тянется'), ('irina_only_mine', 'irina_cloth_cocoon', 3.0, '«Только мой» 3.0: кокон'),
          ('irina_finisher', 'irina_cloth_storm', 1.35, 'добивание 1.35: пронзает'),
          ('irina_death', 'irina_cloth_death', 1.8, 'смерть 1.8: на коленях'), ('irina_death', 'irina_cloth_death', 2.8, 'смерть 2.8: шляпа упала'),
          ('irina_death', 'irina_cloth_death', 5.0, 'смерть 5.0')]
    sheet(os.path.join(MEDIA, 't27_poses.jpg'), {'cols': 4, 'cells': [
        dict(anim=a, cloth=c, t=t, yaw=30, dist=1.55, ty=24, label=l) for a, c, t, l in sp]}, three, (2000, 1500))
    sheet(os.path.join(MEDIA, 't27_staff.png'), {'cols': 3, 'cells': [
        dict(staffOnly=True, spin=0, yaw=180, pitch=0, dist=1.9, ty=8, ground=False, label='Посох (как на референсе)'),
        dict(staffOnly=True, spin=0, yaw=180, pitch=0, dist=0.75, ty=25, ground=False, label='Навершие крупно'),
        dict(staffOnly=True, spin=0, yaw=140, pitch=12, dist=0.85, ty=25, ground=False, label='Навершие, три четверти'),
    ]}, three, (1500, 900))


def staff_shot(args):
    sheet(os.path.join(MEDIA, 't27_staff.png'), {'cols': 3, 'cells': [
        dict(staffOnly=True, spin=0, yaw=180, pitch=0, dist=1.9, ty=8, ground=False, label='Посох (как на референсе)'),
        dict(staffOnly=True, spin=0, yaw=180, pitch=0, dist=0.75, ty=25, ground=False, label='Навершие крупно'),
        dict(staffOnly=True, spin=0, yaw=140, pitch=12, dist=0.85, ty=25, ground=False, label='Навершие, три четверти'),
    ]}, three_arg(args), (1500, 900))


if __name__ == '__main__':
    if '--staff' in sys.argv:
        staff_shot(sys.argv[1:])
    args = sys.argv[1:]
    if '--html' in args:
        write_html()
    if '--sheet' in args:
        i = args.index('--sheet')
        out, cells = args[i + 1], json.load(open(args[i + 2], encoding='utf-8'))
        sheet(out, cells, three_arg(args))
    if '--shots' in args:
        shots(args)
