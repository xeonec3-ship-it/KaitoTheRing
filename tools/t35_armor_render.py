#!/usr/bin/env python3
"""
Кадры и видео брони T35 (часть A: «Наряд Ревности», «Латы Кузнеца», «Накидка Главы Культа»): three.js r128 + Playwright/Chromium + ffmpeg.
Код моделей/анимаций — из tools/cult_leader_preview.template.html (тот же импорт .geo.json и GeckoLib-анимаций, что у кадров боссов).

Игрок — ванильный скелет (скин Стива из client-extra.jar Forge, иначе рисованный), шаг — как у ванили (HumanoidModel.setupAnim:
нога = cos(φ)·1.4·amount, рука — противофазно cos(φ)·amount; ходьба amount ≈ 0.86 → ±69°, бег — 1.0 → ±80°). Броня рисуется как
GeoArmorRenderer: кости bipedHead/Body/RightArm/… брони повторяют повороты частей игрока, ткань играет нашу анимацию idle/walk/run.
Незерит — ванильная модель брони (слой 1 — inflate 1.0, слой 2 — 0.5) с текстурой netherite_layer_1/2.png из того же jar.

  python3 tools/t35_armor_render.py --shots   → docs/media/t35_armor_A.jpg
  python3 tools/t35_armor_render.py --video   → docs/media/video/t35_armor_A.mp4
"""
import base64
import io
import json
import math
import os
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cult_leader_render as CR  # noqa: E402

ROOT = os.path.join(HERE, '..')
A = CR.A
MEDIA = os.path.join(ROOT, 'docs', 'media')
MC = os.path.expanduser('~/.gradle/caches/forge_gradle/minecraft_repo/versions/1.20.1/client-extra.jar')
SETS = ('jealous', 'smith', 'cult_mantle')


def mc_png(path):
    if os.path.exists(MC):
        with zipfile.ZipFile(MC) as z:
            return CR.b64(z.read('assets/minecraft/' + path))
    return None


def box(origin, size, uv, inflate=0.0, mirror=False):
    c = {'origin': origin, 'size': size, 'uv': uv}
    if inflate:
        c['inflate'] = inflate
    if mirror:
        c['mirror'] = True
    return c


def geo(name, tw, th, bones):
    return {'format_version': '1.12.0', 'minecraft:geometry': [{'description': {'identifier': 'geometry.' + name, 'texture_width': tw,
                                                                               'texture_height': th}, 'bones': bones}]}


def player_geo():
    """Игрок (оси geo-файла: правая рука — x минус). Кости названы как части HumanoidModel."""
    return geo('player', 64, 64, [
        {'name': 'body', 'pivot': [0, 24, 0], 'cubes': [box([-4, 12, -2], [8, 12, 4], [16, 16])]},
        {'name': 'head', 'pivot': [0, 24, 0], 'cubes': [box([-4, 24, -4], [8, 8, 8], [0, 0]), box([-4, 24, -4], [8, 8, 8], [32, 0], 0.5)]},
        {'name': 'right_arm', 'pivot': [-5, 22, 0], 'cubes': [box([-8, 12, -2], [4, 12, 4], [40, 16])]},
        {'name': 'left_arm', 'pivot': [5, 22, 0], 'cubes': [box([4, 12, -2], [4, 12, 4], [32, 48])]},
        {'name': 'right_leg', 'pivot': [-1.9, 12, 0], 'cubes': [box([-3.9, 0, -2], [4, 12, 4], [0, 16])]},
        {'name': 'left_leg', 'pivot': [1.9, 12, 0], 'cubes': [box([-0.1, 0, -2], [4, 12, 4], [16, 48])]},
    ])


def netherite_geo(layer):
    """Ванильная броня: слой 1 (шлем, нагрудник, руки, ботинки) inflate 1.0, слой 2 (поножи) — 0.5; UV 64×32, левые части — зеркало."""
    if layer == 1:
        i = 1.0
        bones = [
            {'name': 'head', 'pivot': [0, 24, 0], 'cubes': [box([-4, 24, -4], [8, 8, 8], [0, 0], i)]},
            {'name': 'body', 'pivot': [0, 24, 0], 'cubes': [box([-4, 12, -2], [8, 12, 4], [16, 16], i)]},
            {'name': 'right_arm', 'pivot': [-5, 22, 0], 'cubes': [box([-8, 12, -2], [4, 12, 4], [40, 16], i)]},
            {'name': 'left_arm', 'pivot': [5, 22, 0], 'cubes': [box([4, 12, -2], [4, 12, 4], [40, 16], i, True)]},
            {'name': 'right_leg', 'pivot': [-1.9, 12, 0], 'cubes': [box([-3.9, 0, -2], [4, 12, 4], [0, 16], i)]},
            {'name': 'left_leg', 'pivot': [1.9, 12, 0], 'cubes': [box([-0.1, 0, -2], [4, 12, 4], [0, 16], i, True)]},
        ]
    else:
        i = 0.5
        bones = [
            {'name': 'body', 'pivot': [0, 24, 0], 'cubes': [box([-4, 12, -2], [8, 12, 4], [16, 16], i)]},
            {'name': 'right_leg', 'pivot': [-1.9, 12, 0], 'cubes': [box([-3.9, 0, -2], [4, 12, 4], [0, 16], i)]},
            {'name': 'left_leg', 'pivot': [1.9, 12, 0], 'cubes': [box([-0.1, 0, -2], [4, 12, 4], [0, 16], i, True)]},
        ]
    return geo('netherite_%d' % layer, 64, 32, bones)


def armor_entry(name):
    T = os.path.join(A, 'textures', 'armor')
    e = {'geo': json.load(open(os.path.join(A, 'geo', 'armor', name + '.geo.json'), encoding='utf-8')),
         'tex': CR.b64(os.path.join(T, name + '.png'))}
    g = os.path.join(T, name + '_glowmask.png')
    if os.path.exists(g):
        e['glow'] = CR.b64(g)
    return e


def boss_entry(name):
    if name == 'cult_leader':
        e = CR.model_entry('cult_leader')
        e['scale'] = 1.75
        return e
    T = os.path.join(A, 'textures', 'entity', name)
    e = {'geo': json.load(open(os.path.join(A, 'geo', 'entity', name + '.geo.json'), encoding='utf-8')),
         'tex': CR.b64(os.path.join(T, name + '.png')), 'glow': CR.b64(os.path.join(T, name + '_glowmask.png')), 'scale': 1.0}
    if name == 'aris':           # молот на земле в покое — в кадре не нужен (рядом стоит игрок)
        for b in e['geo']['minecraft:geometry'][0]['bones']:
            if b['name'] == 'hammer_ground':
                b.pop('cubes', None)
    return e


def boss_anims():
    out = {}
    for name, keys in (('irina', ('irina_idle', 'irina_cloth_idle')), ('aris', ('animation.aris.idle',))):
        an = json.load(open(os.path.join(A, 'animations', 'entity', name + '.animation.json'), encoding='utf-8'))['animations']
        merged = {'loop': True, 'animation_length': an[keys[0]]['animation_length'], 'bones': {}}
        for k in keys:
            merged['bones'].update(an[k]['bones'])
        out[name + '_idle'] = merged
    return out


def data():
    skin = mc_png('textures/entity/player/wide/steve.png') or CR.pil_b64(CR.steve_skin())
    models = {'player': {'geo': player_geo(), 'tex': skin}}
    n1, n2 = mc_png('textures/models/armor/netherite_layer_1.png'), mc_png('textures/models/armor/netherite_layer_2.png')
    if n1:
        models['netherite_1'] = {'geo': netherite_geo(1), 'tex': n1}
        models['netherite_2'] = {'geo': netherite_geo(2), 'tex': n2}
    for s in SETS:
        models[s] = armor_entry(s)
    for b in ('irina', 'aris', 'cult_leader'):
        models[b] = boss_entry(b)
    anims = boss_anims()
    for s in SETS:
        an = json.load(open(os.path.join(A, 'animations', 'armor', s + '.animation.json'), encoding='utf-8'))['animations']
        for k, v in an.items():
            anims[s + ':' + k] = v
    return {'models': models, 'anims': anims}


def lib_code():
    src = open(os.path.join(HERE, 'cult_leader_preview.template.html'), encoding='utf-8').read()
    i0 = src.index('// ------------------------------------------------------------------ .geo.json')
    i1 = src.index('// ------------------------------------------------------------------ сцена')
    return src[i0:i1]


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#120c0a;overflow:hidden;font:600 15px 'DejaVu Sans',sans-serif;color:#f4ece4}
.lab{position:absolute;padding:3px 7px;background:rgba(10,6,6,.62);border-radius:4px;line-height:1.25}
.lab small{display:block;font:400 12px 'DejaVu Sans',sans-serif;color:#d8ccc0}
#ttl{position:absolute;left:0;right:0;top:0;height:%(th)dpx;line-height:%(th)dpx;text-align:center;font:700 22px 'DejaVu Sans',sans-serif;background:#1d1210;color:#f2d79a}
#cap{position:absolute;left:18px;bottom:16px;padding:6px 12px;background:rgba(10,6,6,.7);border-radius:6px;font:700 22px 'DejaVu Sans',sans-serif}
#cap small{display:block;font:400 15px 'DejaVu Sans',sans-serif;color:#d8ccc0}
</style><script src="%(three)s"></script></head><body><div id="ttl">%(title)s</div>
<script>
const DATA = %(data)s;
%(lib)s
const TH = %(th)d, D = Math.PI / 180;
const CACHE = {};
function inst(name) {                       // новая копия модели (текстуры общие)
  const m = buildModel(DATA.models[name], false);
  const s = DATA.models[name].scale || 1; m.root.scale.set(s, s, s);
  return m;
}
// ---- игрок: ванильный шаг (HumanoidModel.setupAnim); в three.js +x поворота свисающей части — вперёд
const MODES = { idle: [0, 0], walk: [0.86, 0.6662 * 0.86 * 20], run: [1.0, 0.6662 * 1.0 * 20], cast: [0, 0] };
function playerRot(mode, t) {
  const [amt, w] = MODES[mode], ph = t * w;
  const leg = Math.cos(ph) * 1.4 * amt, arm = Math.cos(ph + Math.PI) * amt;
  const br = Math.sin(t * 2 * Math.PI / 3.0);
  const r = { head: [0, 0, 0], body: [0, 0, 0], right_arm: [arm, 0, 0.05 + 0.03 * br], left_arm: [-arm, 0, -0.05 - 0.03 * br],
              right_leg: [leg, 0, 0], left_leg: [-leg, 0, 0] };
  if (mode === 'cast') { r.right_arm = [1.35, -0.2, 0.25]; r.left_arm = [1.35, 0.2, -0.25]; }
  return r;
}
const MAP = { head: ['bipedHead', 'head'], body: ['bipedBody', 'body'], right_arm: ['bipedRightArm', 'right_arm'], left_arm: ['bipedLeftArm', 'left_arm'],
              right_leg: ['bipedRightLeg', 'right_leg'], left_leg: ['bipedLeftLeg', 'left_leg'] };
function actor(a, scene) {
  const g = new THREE.Group();
  if (a.kind === 'boss') {
    const m = inst(a.name); pose(m, a.anim ? DATA.anims[a.anim] : null, a.t || 0); g.add(m.root);
  } else {
    const rot = playerRot(a.mode || 'idle', a.t || 0);
    const parts = [inst('player')];
    for (const v of (a.vanilla || [])) parts.push(inst(v));
    for (const p of parts) { pose(p, null, 0); for (const k in rot) { const b = p.bones[k]; if (b) b.rotation.set(rot[k][0], rot[k][1], rot[k][2], 'ZYX'); } g.add(p.root); }
    for (const s of (a.armor || [])) {
      const m = inst(s);
      const mode = a.cloth || a.mode || 'idle', an = DATA.anims[s + ':' + mode];
      pose(m, an, (a.t || 0) %% an.animation_length);
      for (const k in rot) { const b = m.bones[MAP[k][0]]; if (b) b.rotation.set(rot[k][0], rot[k][1], rot[k][2], 'ZYX'); }
      if (a.hide) for (const h of a.hide) if (m.bones[h]) m.bones[h].visible = false;
      g.add(m.root);
    }
  }
  g.position.set(a.x || 0, 0, a.z || 0); g.rotation.y = (a.yaw || 0) * D;
  scene.add(g);
}
function groundTex() {
  const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d');
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { x.fillStyle = (i + j) %% 2 ? '#3a302a' : '#2e2622'; x.fillRect(i * 16, j * 16, 16, 16); }
  const g = new THREE.CanvasTexture(c); g.magFilter = THREE.NearestFilter; g.wrapS = g.wrapT = THREE.RepeatWrapping; g.repeat.set(16, 16); return g;
}
const GT = groundTex();
function scene0(bg) {
  const scene = new THREE.Scene(); scene.background = new THREE.Color(bg || 0x1a1412);
  scene.add(new THREE.HemisphereLight(0xe8dcd0, 0x302018, 0.85));
  const dl = new THREE.DirectionalLight(0xfff4e8, 0.7); dl.position.set(30, 60, -40); scene.add(dl);
  const dl2 = new THREE.DirectionalLight(0xffb070, 0.35); dl2.position.set(-40, 20, 50); scene.add(dl2);
  const gr = new THREE.Mesh(new THREE.PlaneGeometry(256, 256), new THREE.MeshLambertMaterial({ map: GT })); gr.rotation.x = -Math.PI / 2; scene.add(gr);
  return scene;
}
function camera(c, aspect) {
  const cam = new THREE.PerspectiveCamera(c.fov || 30, aspect, 0.5, 3000);
  const yaw = (c.yaw || 0) * D, pitch = (c.pitch ?? 8) * D, dist = c.dist || 90, ty = c.ty ?? 17, tx = c.tx || 0;
  cam.position.set(tx + Math.sin(yaw) * Math.cos(pitch) * dist, ty + Math.sin(pitch) * dist, -Math.cos(yaw) * Math.cos(pitch) * dist);
  cam.lookAt(tx, ty, 0);
  return cam;
}
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(innerWidth, innerHeight); renderer.setScissorTest(true);
document.body.appendChild(renderer.domElement);
function drawCells(CELLS, COLS) {
  const W = innerWidth, H = innerHeight - TH, rows = Math.ceil(CELLS.length / COLS), cw = W / COLS, ch = H / rows;
  CELLS.forEach((c, i) => {
    const scene = scene0(c.bg); for (const a of c.actors) actor(a, scene);
    const x = (i %% COLS) * cw, y = H - (Math.floor(i / COLS) + 1) * ch;
    renderer.setViewport(x, y, cw, ch); renderer.setScissor(x, y, cw, ch); renderer.render(scene, camera(c.cam || {}, cw / ch));
    const d = document.createElement('div'); d.className = 'lab'; d.style.left = (x + 6) + 'px'; d.style.top = (TH + Math.floor(i / COLS) * ch + 6) + 'px';
    d.innerHTML = (c.label || '') + (c.sub ? '<small>' + c.sub + '</small>' : ''); document.body.appendChild(d);
  });
}
window.VID = {
  render(f) {
    const scene = scene0(); for (const a of f.actors) actor(a, scene);
    renderer.setViewport(0, 0, innerWidth, innerHeight); renderer.setScissor(0, 0, innerWidth, innerHeight);
    renderer.render(scene, camera(f.cam, innerWidth / innerHeight));
    let cap = document.getElementById('cap'); if (!cap) { cap = document.createElement('div'); cap.id = 'cap'; document.body.appendChild(cap); }
    cap.innerHTML = (f.cap || '') + (f.sub ? '<small>' + f.sub + '</small>' : ''); cap.style.display = f.cap ? 'block' : 'none';
  }
};
const CELLS = %(cells)s, COLS = %(cols)d;
THREE.DefaultLoadingManager.onLoad = () => { if (!window.READY) setTimeout(() => { if (CELLS) drawCells(CELLS, COLS); window.READY = true; }, 50); };
for (const n in DATA.models) inst(n);
</script></body></html>
"""


def page(cells=None, cols=1, title='', three=None):
    th = 40 if title else 0
    return PAGE % dict(th=th, title=title, three='file://' + os.path.abspath(three) if three else CR.CDN,
                       data=json.dumps(data(), ensure_ascii=False, separators=(',', ':')), lib=lib_code(),
                       cells=json.dumps(cells, ensure_ascii=False) if cells else 'null', cols=cols)


def three_arg(args):
    return args[args.index('--three') + 1] if '--three' in args else None


# ================================================================== кадр-лист
def P(armor, mode='idle', t=0.0, **kw):
    d = {'kind': 'player', 'armor': armor if isinstance(armor, list) else [armor], 'mode': mode, 't': t}
    d.update(kw)
    return d


def shots(args=()):
    three = three_arg(list(args))
    V = {'front': (25, 8), 'side': (90, 6), 'back': (180, 8), 'walk': (75, 6)}
    cells = []
    rows = (('jealous', '«Наряд Ревности» (Ирина)', 'irina', 'Ирина', 44, 24),
            ('smith', '«Латы Кузнеца» (Арис)', 'aris', 'Арис', 36, 20),
            ('cult_mantle', '«Накидка Главы Культа»', 'cult_leader', 'Глава Культа ×1.75', 0, 0))
    for sid, title, boss, bname, _, _ in rows:
        base = {'vanilla': ['netherite_1', 'netherite_2']} if sid == 'cult_mantle' else {}
        under = ' поверх незерита' if sid == 'cult_mantle' else ''
        dist = 128 if sid == 'jealous' else 112 if sid == 'smith' else 100
        ty = 24 if sid == 'jealous' else 20 if sid == 'smith' else 17
        cells.append({'actors': [P(sid, 'idle', 0.8, **base)], 'cam': {'yaw': V['front'][0], 'pitch': V['front'][1], 'dist': dist, 'ty': ty},
                      'label': title, 'sub': 'спереди (3/4)' + under})
        cells.append({'actors': [P(sid, 'idle', 1.6, **base)], 'cam': {'yaw': 90, 'pitch': 6, 'dist': dist, 'ty': ty}, 'label': 'сбоку', 'sub': 'покой'})
        cells.append({'actors': [P(sid, 'idle', 2.4, **base)], 'cam': {'yaw': 180, 'pitch': 8, 'dist': dist, 'ty': ty}, 'label': 'сзади'})
        # шаг: кадр, где правая нога отведена назад до упора (≈69°) — видно, что ткань её не задевает
        tw = math.pi / (0.6662 * 0.86 * 20)
        cells.append({'actors': [P(sid, 'walk', tw, **base)], 'cam': {'yaw': 90, 'pitch': 6, 'dist': dist, 'ty': ty},
                      'label': 'сбоку, ходьба', 'sub': 'нога назад до упора (±69°), ткань — walk'})
        if sid == 'cult_mantle':
            actors = [P(['smith', 'cult_mantle'], 'idle', 0.5, x=-13, yaw=-12), {'kind': 'boss', 'name': 'cult_leader', 'x': 16, 'yaw': 12}]
            sub = 'поверх «Лат Кузнеца»; один масштаб'
        else:
            actors = [P(sid, 'idle', 0.5, x=-11, yaw=-10), {'kind': 'boss', 'name': boss, 'anim': boss + '_idle', 't': 0.5, 'x': 12, 'yaw': 10}]
            sub = 'один масштаб и свет'
        cells.append({'actors': actors, 'cam': {'yaw': 0, 'pitch': 7, 'dist': 150 if sid != 'cult_mantle' else 175, 'ty': 26 if sid != 'cult_mantle' else 32},
                      'label': 'рядом с боссом: ' + bname, 'sub': sub})
    out = os.path.join(MEDIA, 't35_armor_A.jpg')
    CR.shoot(page(cells, 5, 'T35 — броня с боссов (часть A): Ирина, Арис, накидка Главы Культа', three), out, size=(2400, 1640))


# ================================================================== видео
FPS = 30


def video(args=()):
    three = three_arg(list(args))
    frames = []

    def seg(dur, fn):
        n = int(round(dur * FPS))
        for i in range(n):
            frames.append(fn(i / FPS, i / max(1, n - 1)))

    def turntable(sid, title, extra=None, dist=86, ty=17, yaw0=20):
        base = extra or {}
        armor = base.pop('armor', [sid])
        # 14 с, полный оборот камеры: покой 3 с → шаг 6 с → бег 3 с → каст 2 с
        def fn(t, k):
            mode = 'idle' if t < 3 else 'walk' if t < 9 else 'run' if t < 12 else 'cast'
            sub = {'idle': 'покой', 'walk': 'ходьба (ванильный шаг, ткань — walk)', 'run': 'бег (±80°, ткань — run)', 'cast': 'каст (ткань — cast)'}[mode]
            return {'actors': [dict(P(armor, mode, t), **base)], 'cam': {'yaw': yaw0 + 360 * k, 'pitch': 7, 'dist': dist, 'ty': ty},
                    'cap': title, 'sub': sub}
        seg(14, fn)

    turntable('jealous', '«Наряд Ревности» (Ирина)', dist=132, ty=25)
    turntable('smith', '«Латы Кузнеца» (Арис)', dist=116, ty=22)
    turntable('cult_mantle', '«Накидка Главы Культа» поверх незерита', {'vanilla': ['netherite_1', 'netherite_2']}, dist=100, ty=17)
    turntable('cult_mantle', '«Накидка Главы Культа» поверх «Лат Кузнеца»', {'armor': ['smith', 'cult_mantle']}, dist=118, ty=22, yaw0=200)
    # крупно сбоку: ходьба и бег, ткань против ноги
    for sid, title, extra in (('jealous', 'Ирина: ленты юбки на шаге', {}), ('cult_mantle', 'Накидка: плащ на бегу', {'vanilla': ['netherite_1', 'netherite_2']})):
        def fn(t, k, sid=sid, title=title, extra=extra):
            mode = 'walk' if t < 3 else 'run'
            return {'actors': [dict(P(sid, mode, t), **extra)], 'cam': {'yaw': 90, 'pitch': 4, 'dist': 80, 'ty': 15}, 'cap': title,
                    'sub': 'сбоку: ходьба → бег'}
        seg(5, fn)
    out = os.path.join(MEDIA, 'video', 't35_armor_A.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    W, H = 1280, 720
    with tempfile.TemporaryDirectory() as td:
        hp = os.path.join(td, 'page.html')
        with open(hp, 'w', encoding='utf-8') as fh:
            fh.write(page(None, 1, '', three))
        jp = os.path.join(td, 'job.json')
        with open(jp, 'w', encoding='utf-8') as fh:
            json.dump({'html': hp, 'out': out, 'fps': FPS, 'w': W, 'h': H, 'frames': frames}, fh, ensure_ascii=False)
        js = r"""
const { chromium } = require('playwright'); const { spawn } = require('child_process'); const fs = require('fs');
(async () => {
  const job = JSON.parse(fs.readFileSync(process.argv[1], 'utf-8'));
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
  const pg = await b.newPage({ viewport: { width: job.w, height: job.h }, deviceScaleFactor: 1 });
  pg.on('pageerror', e => console.log('pageerror', e.message));
  await pg.goto('file://' + job.html);
  await pg.waitForFunction('window.READY === true', null, { timeout: 240000 });
  const tmp = require('path').join(require('os').tmpdir(), 't35_' + process.pid + '.mp4');
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(job.fps), '-c:v', 'mjpeg', '-i', '-',
    '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', String(job.fps), '-movflags', '+faststart', tmp],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise(r => ff.on('close', r));
  for (let i = 0; i < job.frames.length; i++) {
    await pg.evaluate(f => VID.render(f), job.frames[i]);
    const buf = await pg.screenshot({ type: 'jpeg', quality: 94 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 300 === 0) console.log('  frame', i, '/', job.frames.length);
  }
  ff.stdin.end(); const code = await done;
  if (!code) { fs.copyFileSync(tmp, job.out); fs.unlinkSync(tmp); }
  await b.close(); process.exit(code ? 1 : 0);
})();
"""
        r = subprocess.run(['node', '-e', js, jp])
        if r.returncode:
            raise SystemExit('video failed')
    print('wrote', os.path.relpath(out, ROOT), '(%.1f с, %.1f МБ)' % (len(frames) / FPS, os.path.getsize(out) / 1e6))


def frame(out, f, three=None, size=(1280, 720)):
    """Один кадр видео в файл (для проверки)."""
    html = page(None, 1, '', three)
    html = html.replace("window.READY = true; }, 50); };", "VID.render(%s); window.READY = true; }, 50); };" % json.dumps(f, ensure_ascii=False))
    CR.shoot(html, out, size=size)


if __name__ == '__main__':
    a = sys.argv[1:]
    if '--shots' in a:
        shots(a)
    if '--video' in a:
        video(a)
