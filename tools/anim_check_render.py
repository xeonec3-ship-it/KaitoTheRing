#!/usr/bin/env python3
"""
Кадры покадровой проверки анимаций T26/T30 (tools/anim_check.py): модель и анимации из assets, код моделей — из шаблонов превью
(tools/cult_leader_preview.template.html, tools/ereb_preview.template.html), предмет в правой руке — как у Iron's (HumanoidRenderer:
bipedHandRight → её поворот ещё раз (GeckoLib) → −1/16 z, −1/16 y, X −90°, display thirdperson_righthand) — так же, как в tools/boss_video.py.
На земле — жёлтая стрелка «вперёд» (взгляд босса), красная точка — остриё оружия.

  from anim_check_render import sheet
  sheet('out.jpg', 'cult_leader', cells, cols=6, three='path/three.min.js', size=(1920, 1080), title='...')
  ячейка: {'marks': [[x, y, z, r]] — зелёные цели, 'boxes': [[x, y, z, w, h, d]] — силуэты, 'anim': имя, 't': с, 'view': 'side'|'top'|'front'|'back'|'34', 'label': '...', 'sub': '...', 'bad': bool, 'anims': {имя: json}}
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cult_leader_render as CR  # noqa: E402

A = CR.A
VIEWS = {'side': (90, 6), 'side_r': (-90, 6), 'top': (0, 88), 'front': (0, 6), 'back': (180, 6), '34': (35, 14), '34b': (145, 14)}


def item_els(boss):
    if boss == 'cult_leader':
        import boss_video as BV
        it = BV.scythe_item()
        return {'els': it['els'], 'display': it['display']['thirdperson_righthand'], 'tip': it['tip']}
    import gen_ereb_render as ER
    import anim_check as AC
    r = ER.rapier_entry()
    els = [[a, b, rot, {'north': col}] for a, b, col, rot in r['els']]
    m = AC.Model('ereb')
    tip = [float(x) for x in m.item_pts[m.tip_i]]            # остриё — с учётом поворота брусков (−45° по z)
    return {'els': els, 'display': r['display'], 'tip': tip}


def lib(boss, anims):
    if boss == 'cult_leader':
        e = CR.model_entry('cult_leader')
        e['scythe'] = False
        tpl = 'cult_leader_preview.template.html'
    else:
        import gen_ereb_render as ER
        e = ER.model_entry('ereb')
        e.pop('item', None)
        tpl = 'ereb_preview.template.html'
    data = {'models': {boss: e}, 'anims': anims}
    src = open(os.path.join(HERE, tpl), encoding='utf-8').read()
    i0 = src.index('const DATA = /*DATA*/null;')
    i1 = src.index('const renderer')
    code = src[i0:i1].replace('const DATA = /*DATA*/null;', 'const DATA = %s;' % json.dumps(data, ensure_ascii=False, separators=(',', ':')), 1)
    code = code.replace('const CELLS = /*CELLS*/null;', '')
    return '<script>\nconst BL = (() => {\n%s\nreturn { DATA, buildModel, pose };\n})();\n</script>\n' % code


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#120c0a;overflow:hidden;font:600 15px 'DejaVu Sans',sans-serif;color:#f4ece4}
.lab{position:absolute;padding:3px 7px;background:rgba(10,6,6,.62);border-radius:4px;line-height:1.25;max-width:%(cw)dpx}
.lab small{display:block;font:400 12px 'DejaVu Sans Mono',monospace;color:#d8ccc0}
.lab.bad{border-left:4px solid #ff4a3a}.lab.ok{border-left:4px solid #5ad06a}
#ttl{position:absolute;left:0;right:0;top:0;height:%(th)dpx;line-height:%(th)dpx;text-align:center;font:700 22px 'DejaVu Sans',sans-serif;background:#1d1210;color:#f2d79a}
</style><script src="%(three)s"></script></head><body><div id="ttl">%(title)s</div>
%(lib)s
<script>
const CELLS = %(cells)s, ITEM = %(item)s, BOSS = %(boss)s, COLS = %(cols)d, TH = %(th)d;
const D = Math.PI / 180;
const VIEWS = %(views)s;
function itemMesh(els) {
  const grp = new THREE.Group();
  for (const [a, b, rot, fc] of els) {
    const col = fc.north || Object.values(fc)[0];
    const m = new THREE.Mesh(new THREE.BoxGeometry(Math.max(0.05, b[0] - a[0]), Math.max(0.05, b[1] - a[1]), Math.max(0.05, b[2] - a[2])),
                             new THREE.MeshLambertMaterial({ color: col }));
    const c = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2];
    if (rot) {
      const p = new THREE.Group(); p.position.set(rot.origin[0] - 8, rot.origin[1] - 8, rot.origin[2] - 8);
      p.rotation[rot.axis] = rot.angle * D; m.position.set(c[0] - rot.origin[0], c[1] - rot.origin[1], c[2] - rot.origin[2]); p.add(m); grp.add(p);
    } else { m.position.set(c[0] - 8, c[1] - 8, c[2] - 8); grp.add(m); }
  }
  return grp;
}
function attachItem(model) {
  const hand = model.bones.bipedHandRight, d = ITEM.display;
  // GeckoLib 4.8.4 (BlockAndItemGeoLayer): предмет поворачивается поворотом кисти ДВАЖДЫ — второй раз здесь (dbl)
  const dbl = new THREE.Group(); hand.add(dbl); model.dbl = dbl;
  const a = new THREE.Group(); a.position.set(0, -1, -1); dbl.add(a);
  const b = new THREE.Group(); b.rotation.x = -Math.PI / 2; a.add(b);
  const t = new THREE.Group(); t.position.set(...(d.translation || [0, 0, 0])); b.add(t);
  const r = new THREE.Group(); r.quaternion.setFromEuler(new THREE.Euler(...(d.rotation || [0, 0, 0]).map(v => v * D), 'XYZ')); t.add(r);
  const s = new THREE.Group(); s.scale.set(...(d.scale || [1, 1, 1])); r.add(s);
  const it = itemMesh(ITEM.els); s.add(it);
  const tip = new THREE.Mesh(new THREE.SphereGeometry(0.9 / Math.max(...(d.scale || [1, 1, 1])), 10, 8), new THREE.MeshBasicMaterial({ color: 0xff2020, depthTest: false }));
  tip.renderOrder = 9; tip.position.set(ITEM.tip[0] - 8, ITEM.tip[1] - 8, ITEM.tip[2] - 8); it.add(tip);
}
function groundTex() {
  const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d');
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { x.fillStyle = (i + j) %% 2 ? '#3a302a' : '#2e2622'; x.fillRect(i * 16, j * 16, 16, 16); }
  const g = new THREE.CanvasTexture(c); g.magFilter = THREE.NearestFilter; g.wrapS = g.wrapT = THREE.RepeatWrapping; g.repeat.set(16, 16); return g;
}
function arrow(scene) {
  const m = new THREE.MeshBasicMaterial({ color: 0xffd23a, side: THREE.DoubleSide });
  const sh = new THREE.Shape(); sh.moveTo(-1.6, 0); sh.lineTo(1.6, 0); sh.lineTo(1.6, 26); sh.lineTo(5, 26); sh.lineTo(0, 36); sh.lineTo(-5, 26); sh.lineTo(-1.6, 26); sh.closePath();
  const g = new THREE.Mesh(new THREE.ShapeGeometry(sh), m); g.rotation.x = -Math.PI / 2; g.position.y = 0.15;
  // фигура вдоль +y формы → после поворотов смотрит в −z (вперёд от босса)
  scene.add(g);
}
const W = innerWidth, H = innerHeight - TH;
const rows = Math.ceil(CELLS.length / COLS), cw = W / COLS, ch = H / rows;
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(innerWidth, innerHeight); renderer.setScissorTest(true);
document.body.appendChild(renderer.domElement);
function draw() {
  CELLS.forEach((c, i) => {
    const scene = new THREE.Scene(); scene.background = new THREE.Color(c.bad ? 0x2a1412 : 0x1a1412);
    scene.add(new THREE.HemisphereLight(0xe8dcd0, 0x302018, 0.85));
    const dl = new THREE.DirectionalLight(0xfff4e8, 0.7); dl.position.set(30, 60, -40); scene.add(dl);
    const dl2 = new THREE.DirectionalLight(0xffb070, 0.35); dl2.position.set(-40, 20, 50); scene.add(dl2);
    const gr = new THREE.Mesh(new THREE.PlaneGeometry(256, 256), new THREE.MeshLambertMaterial({ map: groundTex() }));
    gr.rotation.x = -Math.PI / 2; scene.add(gr);
    arrow(scene);
    const m = BL.buildModel(BL.DATA.models[BOSS], false); attachItem(m);
    BL.pose(m, c.anim ? BL.DATA.anims[c.anim] : null, c.t || 0);
    if (m.dbl) m.dbl.quaternion.copy(m.bones.bipedHandRight.quaternion);
    scene.add(m.root);
    for (const mk of (c.marks || [])) {                       // цели (например, грудь жертвы): зелёный шар
      const g = new THREE.Mesh(new THREE.SphereGeometry(mk[3] || 1.6, 12, 10), new THREE.MeshBasicMaterial({ color: 0x30e060, transparent: true, opacity: 0.8 }));
      g.position.set(mk[0], mk[1], mk[2]); scene.add(g);
    }
    for (const bx of (c.boxes || [])) {                       // силуэт жертвы: бокс [x, y, z, w, h, d]
      const g = new THREE.Mesh(new THREE.BoxGeometry(bx[3], bx[4], bx[5]), new THREE.MeshLambertMaterial({ color: 0x4a8ad0, transparent: true, opacity: 0.55 }));
      g.position.set(bx[0], bx[1] + bx[4] / 2, bx[2]); scene.add(g);
    }
    const [yaw, pitch] = VIEWS[c.view || 'side'];
    const cam = new THREE.PerspectiveCamera(32, cw / ch, 0.5, 3000);
    const dist = c.dist || 120, ty = c.ty ?? 18;
    cam.position.set(Math.sin(yaw * D) * Math.cos(pitch * D) * dist, ty + Math.sin(pitch * D) * dist, -Math.cos(yaw * D) * Math.cos(pitch * D) * dist);
    if (pitch > 80) cam.up.set(0, 0, -1);
    cam.lookAt(0, pitch > 80 ? 0 : ty, pitch > 80 ? -6 : 0);
    const x = (i %% COLS) * cw, y = H - (Math.floor(i / COLS) + 1) * ch;
    renderer.setViewport(x, y, cw, ch); renderer.setScissor(x, y, cw, ch); renderer.render(scene, cam);
    const d = document.createElement('div'); d.className = 'lab ' + (c.bad ? 'bad' : (c.ok ? 'ok' : ''));
    d.style.left = (x + 6) + 'px'; d.style.top = (TH + Math.floor(i / COLS) * ch + 6) + 'px';
    d.innerHTML = (c.label || '') + (c.sub ? '<small>' + c.sub + '</small>' : ''); document.body.appendChild(d);
  });
  window.READY = true;
}
THREE.DefaultLoadingManager.onLoad = () => { if (!window.READY) setTimeout(draw, 50); };
BL.buildModel(BL.DATA.models[BOSS], false);
</script></body></html>
"""


def sheet(out, boss, cells, cols=6, three=None, size=(1920, 1080), title='', anims=None):
    if anims is None:
        p = os.path.join(A, 'animations', 'entity', boss + '.animation.json')
        allan = json.load(open(p, encoding='utf-8'))['animations']
        anims = {c['anim']: allan[c['anim']] for c in cells if c.get('anim') and not c.get('anim_json')}
    for c in cells:
        if c.get('anim_json'):
            anims[c['anim']] = c.pop('anim_json')
    th = 40 if title else 0
    rows = -(-len(cells) // cols)
    html = PAGE % dict(cw=size[0] // cols - 20, th=th, title=title, lib=lib(boss, anims), cells=json.dumps(cells, ensure_ascii=False),
                       item=json.dumps(item_els(boss)), boss=json.dumps(boss), cols=cols, views=json.dumps(VIEWS),
                       three='file://' + os.path.abspath(three) if three else CR.CDN)
    tmp = out + '.html'
    with open(tmp, 'w', encoding='utf-8') as fh:
        fh.write(html)
    js = """
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
  const pg = await b.newPage({ viewport: { width: %d, height: %d }, deviceScaleFactor: 1 });
  pg.on('pageerror', e => console.log('pageerror:', e.message));
  pg.on('console', m => { if (m.type() === 'error') console.log('console:', m.text()); });
  await pg.goto('file://%s');
  await pg.waitForFunction('window.READY === true', null, { timeout: 300000 });
  await pg.waitForTimeout(200);
  await pg.screenshot({ path: '%s', type: 'jpeg', quality: 88 });
  await b.close();
})();
""" % (size[0], size[1], os.path.abspath(tmp), out)
    r = subprocess.run(['node', '-e', js], capture_output=True, text=True)
    if r.stdout.strip() or r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
    os.remove(tmp)
    print('wrote', out, '(%d кадров)' % len(cells))
