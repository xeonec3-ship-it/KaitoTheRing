#!/usr/bin/env python3
"""
T34: кадр-лист и видео шести наградных заклинаний — игрок (анимации PlayerAnimator из assets/irons_spellbooks/player_animation,
со сгибами локтей/колен как в tools/anim_preview.template.html) + fx из assets (движок превью tools/sigil_preview.template.html,
меши зеркалятся как в игре: +x меша — вправо от заклинателя) + манекен-цель.

  python3 tools/t34_video.py [--sheet] [--top] [--video] [--three путь/three.min.js]
Выход: docs/media/t34_spells.jpg (6 заклинаний × 4 фазы, вид 3/4 спереди-справа), docs/media/t34_spells_top.jpg (вид сверху —
проверка «вперёд»: жёлтая стрелка = взгляд игрока, манекен впереди), docs/media/video/t34_spells.mp4.
Нужно: Playwright + Chromium, ffmpeg. Оси сцены — оси движка fx: игрок в начале координат смотрит в +Z, его правая рука — к −X.
"""
import json
import math
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import boss_video as BV  # noqa: E402
import gen_t34_anims as TA  # noqa: E402

MEDIA = os.path.join(ROOT, 'docs', 'media')
PA = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'irons_spellbooks', 'player_animation')
FPS, W, H = 30, 1280, 720
NAMES = {'ashen_harvest': ('Пепельная Жатва', 'Глава Культа'), 'jealous_embrace': ('Объятия Ревности', 'Ирина'),
         'anvil_strike': ('Удар Наковальни', 'Арис'), 'warlord_banner': ('Знамя Полководца', 'Мартин'),
         'mirror_step': ('Шаг сквозь отражение', 'Эреб'), 'hand_of_lies': ('Длань Лжи', 'Длань Лжи')}

PLAYER_JS = r"""
<script>
window.VID = (() => {
  const D = Math.PI / 180, W = VW, H = VH, CFG = VCFG, S = 1 / 16;
  let RUNS = [], cap, head, lastTick = 0;
  const EASE = { LINEAR: t => t, INOUTSINE: t => -(Math.cos(Math.PI * t) - 1) / 2, EASEINOUTSINE: t => -(Math.cos(Math.PI * t) - 1) / 2 };
  function tracks(emote) {
    const out = {};
    for (const m of emote.moves) for (const part in m) {
      if (part === 'tick' || part === 'easing' || part === 'turn') continue;
      for (const ch in m[part]) ((out[part] ||= {})[ch] ||= []).push([m.tick, m[part][ch]]);
    }
    for (const p in out) for (const c in out[p]) out[p][c].sort((x, y) => x[0] - y[0]);
    return out;
  }
  const TR = {}; for (const k in ANIMS) TR[k] = tracks(ANIMS[k].emote);
  function value(tr, part, ch, tick) {
    const k = tr && tr[part] && tr[part][ch]; if (!k) return 0;
    let prev = [0, 0];
    for (const cur of k) { if (tick <= cur[0]) { const sp = cur[0] - prev[0], f = sp <= 0 ? 1 : (tick - prev[0]) / sp; return prev[1] + (cur[1] - prev[1]) * f; } prev = cur; }
    return prev[1];
  }
  // ---- модель игрока как в tools/anim_preview.template.html (корпус гнётся у y=18, руки/ноги — сгиб посередине)
  function box(w, h, d, color, oy, op) {
    const g = new THREE.BoxGeometry(w * S, h * S, d * S); g.translate(0, oy * S, 0);
    return new THREE.Mesh(g, new THREE.MeshLambertMaterial(Object.assign({ color }, op ? { transparent: true, opacity: op } : {})));
  }
  function makePlayer(c, withItem) {
    const root = new THREE.Group();
    const torso = new THREE.Group(); torso.position.y = 12 * S; root.add(torso);
    torso.add(box(8, 6, 4, c.robe, 3)); torso.add(box(8.2, 1.2, 4.2, c.trim, 1.2));
    const chest = new THREE.Group(); chest.position.y = 6 * S; torso.add(chest); chest.add(box(8, 6, 4, c.robe, 3));
    chest.add(box(8.2, 1.0, 4.2, c.trim, 5.6));
    const head = new THREE.Group(); head.position.y = 6 * S; chest.add(head);
    head.add(box(8, 8, 8, c.skin, 4)); head.add(box(8.4, 2.4, 8.4, c.hair, 7.2));
    const eyes = box(5, 1, 0.4, c.eyes, 4); eyes.position.z = 4.1 * S; head.add(eyes);
    const nose = box(1.2, 1.2, 0.6, c.skin2, 3.2); nose.position.z = 4.2 * S; head.add(nose);
    function limb(parent, x, y, top, low, arm) {
      const t = new THREE.Group(); t.position.set(x * S, y * S, 0); parent.add(t);
      const ox = arm ? Math.sign(x) : 0, up = arm ? 2 : 0, len = 12, mid = up - len / 2;
      const a = box(4, len / 2, 4, top, up - len / 4); a.position.x = ox * S; t.add(a);
      const l = new THREE.Group(); l.position.set(ox * S, mid * S, 0); t.add(l);
      l.add(box(4, len / 2, 4, low, -len / 4));
      if (arm) l.add(box(4.05, 2, 4.05, c.skin, -len / 2 + 1));
      else l.add(box(4.1, 1.6, 4.4, c.boot, -len / 2 + 0.8));
      return { t, l };
    }
    const rA = limb(chest, -5, 4, c.sleeve, c.sleeve, true), lA = limb(chest, 5, 4, c.sleeve, c.sleeve, true);
    const rL = limb(root, -1.9, 12, c.pants, c.pants, false), lL = limb(root, 1.9, 12, c.pants, c.pants, false);
    let item = null;
    if (withItem) {        // меч в правой руке: по локальной +Z предплечья, хват в 5 px ниже локтя (как посох превью)
      item = new THREE.Group(); item.position.set(0, -5 * S, 0); rA.l.add(item);
      const bl = new THREE.Mesh(new THREE.BoxGeometry(1.0 * S, 0.5 * S, 13 * S), new THREE.MeshLambertMaterial({ color: 0xdfe6ee, emissive: 0x222830 }));
      bl.position.z = 8.5 * S; item.add(bl);
      const gd = new THREE.Mesh(new THREE.BoxGeometry(4 * S, 0.8 * S, 0.8 * S), new THREE.MeshLambertMaterial({ color: 0x8a6a2a })); gd.position.z = 1.8 * S; item.add(gd);
      const hl = new THREE.Mesh(new THREE.BoxGeometry(0.9 * S, 0.9 * S, 3 * S), new THREE.MeshLambertMaterial({ color: 0x4a3020 })); hl.position.z = 0; item.add(hl);
    }
    const holder = new THREE.Group(); holder.add(root); scene.add(holder);
    return { holder, root, torso, chest, head, rA, lA, rL, lL, item };
  }
  const rot = (o, p, y, r) => o.rotation.set(p * D, -y * D, -r * D, 'ZYX');
  function pose(m, name, tick) {
    const tr = TR[name];
    const v = (part, ch) => value(tr, part, ch, tick);
    m.root.position.set(0, v('body', 'y'), v('body', 'z'));
    rot(m.torso, v('torso', 'pitch'), v('torso', 'yaw'), v('torso', 'roll'));
    m.chest.rotation.set(v('torso', 'bend') * D, 0, 0);
    rot(m.head, v('head', 'pitch'), v('head', 'yaw'), v('head', 'roll'));
    for (const [part, l] of [['rightArm', m.rA], ['leftArm', m.lA], ['rightLeg', m.rL], ['leftLeg', m.lL]]) {
      rot(l.t, v(part, 'pitch'), v(part, 'yaw'), v(part, 'roll')); l.l.rotation.set(v(part, 'bend') * D, 0, 0);
    }
  }
  const SKIN = {
    caster: { robe: 0x2c2638, trim: 0xd8a93b, skin: 0xc9956b, skin2: 0xb07e58, hair: 0x2b1c12, eyes: 0x30406a, sleeve: 0x3a3048, pants: 0x262230, boot: 0x1a1414 },
    dummy: { robe: 0xb89a62, trim: 0x7a5a30, skin: 0xd8c08a, skin2: 0xc8a878, hair: 0xa88a52, eyes: 0x5a3a20, sleeve: 0xb08e58, pants: 0x9a7c48, boot: 0x5a4028 },
  };
  const models = {};
  function getM(a) {
    const key = a.k + (a.id ?? '');
    if (!models[key]) models[key] = makePlayer(SKIN[a.skin || (a.k === 'player' ? 'caster' : 'dummy')], a.k === 'player');
    return models[key];
  }
  const M = p => new THREE.Vector3(p[0] || 0, p[1] || 0, p[2] || 0);
  let arrow, ring;
  // меши fx: плашка «проявления» превью рассчитана на ворота 12×3 бл. — подгоняем под размер меша (как tools/boss_video.py)
  const _pmake = Portal.prototype.make;
  Portal.prototype.make = function (p) {
    const P = _pmake.call(this, p);
    if (p.type === 'boxes' && P.flash) {
      if (!p.appear) P.flash.visible = false;
      else if (p.boxes.length) {
        const xs = p.boxes.flatMap(b => [b[0], b[3]]), zs = p.boxes.flatMap(b => [b[2], b[5]]);
        P.flash.scale.set(Math.max(0.1, (Math.max(...xs) - Math.min(...xs)) * 1.1) / 12, 0.5, Math.max(0.1, (Math.max(...zs) - Math.min(...zs)) * 1.1) / 3);
      }
    }
    return P;
  };
  // mesh.move.keys [тик, [x, y, z], плавность] — в превью-движке не было (как tools/boss_video.py); единицы — меша, × scale (как MeshDraw)
  const _pupd = Portal.prototype.update;
  Portal.prototype.update = function (t, dt) {
    _pupd.call(this, t, dt);
    const mv = this.move; if (!mv) return;
    const K = mv.keys;
    if (!K) {                    // move.from: в игре смещение × scale (MeshDraw), в превью — без
      if (mv.from) { const e = ease(mv.easing || 'easeOutCubic', clamp01((t - this.t0 - (mv.delay || 0)) / (mv.duration || 1))), f = mv.from;
        this.root.position.copy(this.base).add(new THREE.Vector3(-f[0], f[1], f[2]).multiplyScalar((1 - e) * this.s)); }
      return;
    }
    const lt = t - this.t0; let v = K[K.length - 1][1];
    if (lt < K[0][0]) v = K[0][1];
    else for (let i = 1; i < K.length; i++) if (lt <= K[i][0]) { const a = K[i - 1], b = K[i], k = ease(b[2] || 'linear', clamp01((lt - a[0]) / Math.max(1, b[0] - a[0]))); v = a[1].map((x, j) => x + (b[1][j] - x) * k); break; }
    this.root.position.copy(this.base).add(new THREE.Vector3(-v[0] * this.s, v[1] * this.s, v[2] * this.s));
  };
  function init() {
    window.requestAnimationFrame = () => 0;
    INST.forEach(s => s.dispose()); INST = [];
    caster.visible = false; grid.visible = false;
    scene.children.filter(o => o.isHemisphereLight).forEach(o => scene.remove(o));
    scene.background = new THREE.Color(CFG.bg);
    scene.add(new THREE.HemisphereLight(0xe8e0ff, 0x302838, 0.9));
    const sun = new THREE.DirectionalLight(0xfff4e8, 0.6); sun.position.set(-4, 9, 6); scene.add(sun);
    const gc = document.createElement('canvas'); gc.width = gc.height = 64; const x = gc.getContext('2d');
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { x.fillStyle = (i + j) % 2 ? CFG.g1 : CFG.g2; x.fillRect(i * 16, j * 16, 16, 16); }
    const gt = new THREE.CanvasTexture(gc); gt.magFilter = THREE.NearestFilter; gt.wrapS = gt.wrapT = THREE.RepeatWrapping; gt.repeat.set(64, 64);
    const gr = new THREE.Mesh(new THREE.PlaneGeometry(256, 256), new THREE.MeshLambertMaterial({ map: gt }));
    gr.rotation.x = -Math.PI / 2; gr.position.y = -0.005; gr.renderOrder = -1; scene.add(gr);
    // жёлтая стрелка «вперёд» (взгляд игрока) на земле
    const sh = new THREE.Shape(); sh.moveTo(-0.08, 0); sh.lineTo(0.08, 0); sh.lineTo(0.08, 0.9); sh.lineTo(0.22, 0.9); sh.lineTo(0, 1.25); sh.lineTo(-0.22, 0.9); sh.lineTo(-0.08, 0.9); sh.closePath();
    arrow = new THREE.Mesh(new THREE.ShapeGeometry(sh), new THREE.MeshBasicMaterial({ color: 0xffd23a, transparent: true, opacity: 0.85, side: THREE.DoubleSide }));
    arrow.rotation.x = Math.PI / 2; arrow.position.y = 0.01; scene.add(arrow);
    for (const el of [...document.body.children]) if (el.tagName !== 'SCRIPT') el.style.display = 'none';
    document.body.appendChild(stage);
    stage.style.cssText = `display:block;position:fixed;left:0;top:0;width:${W}px;height:${H}px;max-height:none;max-width:none;aspect-ratio:auto;margin:0;border:0;border-radius:0;overflow:hidden`;
    for (const el of stage.querySelectorAll('.hud,.hint')) el.style.display = 'none';
    document.body.style.cssText = 'margin:0;padding:0;overflow:hidden;background:#000';
    renderer.setPixelRatio(1); renderer.setSize(W, H, false); cv.style.cssText = `display:block;width:${W}px;height:${H}px`;
    cam.fov = 30; cam.aspect = W / H; cam.near = 0.05; cam.far = 400; cam.updateProjectionMatrix();
    const css = document.createElement('style');
    css.textContent = `#vcap{position:fixed;left:0;right:0;bottom:26px;text-align:center;z-index:30;font:600 28px 'DejaVu Sans',sans-serif;color:#f6eee6;text-shadow:0 0 6px #000,0 2px 2px #000}
      #vcap small{display:block;font:400 17px 'DejaVu Sans Mono',monospace;color:#d8ccc4;margin-top:4px}
      #vhead{position:fixed;left:20px;top:14px;z-index:30;font:600 18px 'DejaVu Sans',sans-serif;color:#e8dcd2;text-shadow:0 0 4px #000}`;
    document.head.appendChild(css);
    for (const id of ['vcap', 'vhead']) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d); }
    cap = document.getElementById('vcap'); head = document.getElementById('vhead');
    RUNS = CFG.runs.map(r => Object.assign({}, r));
    for (const k of Object.keys(EXTRA_FX)) DATA.fx[k] = EXTRA_FX[k];
  }
  function setFig(r, pos) {
    FIG.caster.copy(r.cId !== undefined && pos[r.cId] ? pos[r.cId] : M(r.c || [0, 0, 0]));
    FIG.target.copy(r.tgId !== undefined && pos[r.tgId] ? pos[r.tgId] : M(r.tg || r.c || [0, 0, 0]));
  }
  function render(f) {
    const tick = f.tick !== undefined ? f.tick : f.i * 20 / CFG.fps, dt = Math.min(2, Math.max(0.01, tick - lastTick)); lastTick = tick;
    if (stage.clientHeight !== H || cv.width !== W || cv.height !== H) {
      stage.style.setProperty('height', H + 'px', 'important'); renderer.setSize(W, H, false); cv.style.cssText = `display:block;width:${W}px;height:${H}px`;
    }
    cam.aspect = W / H; cam.fov = f.cam.fov || 30; cam.updateProjectionMatrix();
    cam.position.copy(M(f.cam.p)); cam.up.set(0, 1, 0); if (f.cam.upz) cam.up.set(0, 0, 1);
    cam.lookAt(M(f.cam.t)); cam.updateMatrixWorld(true);
    for (const k in models) models[k].holder.visible = false;
    const pos = {};
    for (const a of f.actors) {
      const m = getM(a);
      m.holder.visible = a.vis !== false;
      if (a.anim) pose(m, a.anim, a.t); else pose(m, null, 0);
      m.holder.position.set(a.x || 0, a.y || 0, a.z || 0);
      m.holder.rotation.set((a.rx || 0) * D, (a.ry || 0) * D, (a.rz || 0) * D, 'YXZ');
      m.holder.traverse(o => { if (o.material && o.material.opacity !== undefined) { o.material.transparent = (a.op ?? 1) < 1; o.material.opacity = a.op ?? 1; } });
      if (a.id !== undefined) pos[a.id] = m.holder.position.clone();
    }
    arrow.visible = !!f.arrow; if (f.arrow) { arrow.position.set(f.arrow[0], 0.012, f.arrow[2]); arrow.rotation.set(Math.PI / 2, 0, (f.arrow[3] || 0) * D); }
    for (const r of RUNS) {
      if (r.s <= f.i && !r.run && !r.done && (r.e === undefined || f.i < r.e)) {
        setFig(r, pos); r.run = new FxRun(r.id, { caster: FIG.caster.clone(), points: {}, noTarget: true, noLift: true }); r.run.mirrorMeshes = true; r.run.t0 = tick;
      }
      if (r.run && r.stop !== undefined && r.stop <= f.i && !r.stopped) { r.run.stop(tick); r.stopped = true; }
      if (r.run && r.e !== undefined && f.i >= r.e) { r.run.dispose(); r.run = null; r.done = true; }
    }
    let scr = 0;
    for (const r of RUNS) if (r.run) { setFig(r, pos); r.run.update(tick, dt); scr = Math.max(scr, +screenFlash.style.opacity || 0); }
    screenFlash.style.opacity = String(scr * 0.5); tintLayer.style.opacity = 0;
    renderer.render(scene, cam);
    cap.innerHTML = f.cap ? f.cap + (f.sub ? '<small>' + f.sub + '</small>' : '') : '';
    head.textContent = f.head || '';
  }
  return { init, render };
})();
</script>
"""

DRIVER = r"""
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
(async () => {
  const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'));
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
  const pg = await b.newPage({ viewport: { width: job.w, height: job.h }, deviceScaleFactor: 1 });
  const errs = []; pg.on('pageerror', e => errs.push(e.message)); pg.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await pg.goto('file://' + job.html);
  await pg.waitForFunction('window.VID && typeof FxRun !== "undefined"', null, { timeout: 240000 });
  await pg.evaluate(() => VID.init()); await pg.waitForTimeout(2500);
  let ff = null, done = null;
  if (job.mp4) {
    ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(job.fps), '-c:v', 'mjpeg', '-i', '-', '-an', '-c:v', 'libx264',
      '-preset', 'slow', '-crf', '21', '-pix_fmt', 'yuv420p', '-r', String(job.fps), '-movflags', '+faststart', job.mp4], { stdio: ['pipe', 'inherit', 'inherit'] });
    done = new Promise(r => ff.on('close', r));
  }
  for (let i = 0; i < job.frames.length; i++) {
    const f = job.frames[i];
    try { await pg.evaluate(f => { try { VID.render(f); } catch (e) { throw new Error(e.message + ' | ' + e.stack); } }, f); } catch (e) { console.log('frame', i, String(e.message).slice(0, 1500)); throw e; }
    if (f.png) await pg.screenshot({ path: f.png, type: 'png' });
    if (ff) { const buf = await pg.screenshot({ type: 'jpeg', quality: 93 }); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); }
    if (i % 200 === 0) console.log('  frame', i, '/', job.frames.length);
  }
  if (ff) { ff.stdin.end(); await done; }
  if (errs.length) console.log('page errors:', JSON.stringify(errs.slice(0, 5)));
  await b.close();
})();
"""

# fx только для ролика (в мод не идут): призрачный солдат у знамени — в игре это сущность (код), здесь — меш martin_soldier_ghost
EXTRA_FX = {
    'vid_soldier': {'style': 'martin_ghost', 'duration': -1, 'elements': [
        {'type': 'mesh', 'delay': 0, 'at': 'caster', 'model': 'martin_soldier_ghost', 'scale': 0.5, 'follow': True, 'duration': 100000}]},
}


def anims():
    return {'pohsmp_' + s: json.load(open(os.path.join(PA, 'pohsmp_%s.json' % s), encoding='utf-8')) for s in TA.SPEC}


def page(three):
    html = open(os.path.join(HERE, 'sigil_preview.template.html'), encoding='utf-8').read()
    data = BV.sigil_data()
    for m in data['meshes'].values():              # превью-движку нужны bounds у boxes (у мешей Длани их нет — в игре не нужны)
        for p_ in m.get('parts', []):
            if p_.get('type') == 'boxes' and 'bounds' not in p_ and p_.get('boxes'):
                p_['bounds'] = [min(b[1] for b in p_['boxes']), max(b[4] for b in p_['boxes'])]
    html = html.replace('/*DATA*/null', json.dumps(data, ensure_ascii=False), 1)
    if three:
        html = html.replace(BV.CDN, 'file://' + os.path.abspath(three))
    html = '\n'.join(l for l in html.split('\n') if 'fonts.googleapis.com' not in l)
    html = html.replace('</head>', BV.PAGE_CSS + '</head>', 1)
    return html


def run_job(frames, runs, three, mp4=None):
    cfg = {'fps': FPS, 'runs': runs, 'bg': '#1a161e', 'g1': '#34303a', 'g2': '#2e2a34'}
    js = PLAYER_JS.replace('VW', str(W)).replace('VH', str(H)).replace('VCFG', json.dumps(cfg, ensure_ascii=False))
    js = js.replace('<script>', '<script>\nconst ANIMS = %s;\nconst EXTRA_FX = %s;\n' % (json.dumps(anims()), json.dumps(EXTRA_FX)), 1)
    with tempfile.TemporaryDirectory() as td:
        hp = os.path.join(td, 'page.html')
        open(hp, 'w', encoding='utf-8').write(page(three) + '\n' + js)
        jp = os.path.join(td, 'job.json')
        for i, f in enumerate(frames):
            f['i'] = i
        json.dump({'html': hp, 'w': W, 'h': H, 'fps': FPS, 'frames': frames, 'mp4': mp4}, open(jp, 'w', encoding='utf-8'), ensure_ascii=False)
        dp = os.path.join(td, 'driver.js')
        open(dp, 'w').write(DRIVER)
        env = dict(os.environ, NODE_PATH=subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True).stdout.strip())
        r = subprocess.run(['node', dp, jp], env=env)
        if r.returncode:
            raise SystemExit('render failed')


# ---------------------------------------------------------------- сцены: актёры и fx по тику анимации
# каждая сцена: функция (tick) -> (актёры, камера-цель) и список fx [(тик, id, caster: 'p'|'d'|(x,y,z), stop_tick|None)]
DUMMY = {'ashen_harvest': (0.6, 0, 3.0), 'jealous_embrace': (0, 0, 8.0), 'anvil_strike': (0, 0, 6.0), 'warlord_banner': (2.6, 0, 6.0),
         'mirror_step': (0, 0, 4.0), 'hand_of_lies': (0, 0, 6.0)}


def scene(sid, tick):
    """Актёры в момент tick (тики анимации): игрок (id 0) и манекен (id 1). Оси движка fx: +Z — вперёд игрока, его правая рука — −X."""
    dx, _, dz = DUMMY[sid]
    L = TA.TIMING[sid]['length']
    pl = {'k': 'player', 'id': 0, 'anim': 'pohsmp_' + sid, 't': min(tick, L), 'x': 0, 'z': 0, 'ry': 0}
    du = {'k': 'dummy', 'id': 1, 'anim': None, 't': 0, 'x': dx, 'z': dz, 'ry': 180}
    if sid == 'jealous_embrace':                       # код тянет цель 14–20 до 1.6 бл. перед игроком
        u = min(1.0, max(0.0, (tick - 14) / 6.0))
        u = 1 - (1 - u) ** 2
        du['z'] = dz + (1.6 - dz) * u
        if 24 <= tick <= 28:                           # отброс от удара крюком
            du['z'] = 1.6 + 0.5 * (1 - math.cos(math.pi * min(1.0, (tick - 24) / 4)))
            du['rx'] = -8 * math.sin(math.pi * min(1.0, (tick - 24) / 4))
        elif tick > 28:
            du['z'] = 2.6
    if sid == 'anvil_strike' and tick >= 15:           # отброс от удара молотом
        u = min(1.0, (tick - 15) / 6.0)
        du['z'] = dz + 1.6 * (1 - (1 - u) ** 2)
        du['y'] = 0.9 * math.sin(math.pi * u)
    if sid == 'mirror_step' and tick >= 4:             # телепорт за спину цели, лицом к ней
        pl.update(z=dz + 1.4, ry=180)
    if sid == 'mirror_step':
        pl['op'] = 1.0 if tick < 10 else max(0.25, 1 - (tick - 10) / 8)
    return [pl, du]


FXS = {
    'ashen_harvest': [(0, 'ashen_harvest', 'p', None), (12, 'ashen_harvest_trail', 'p', None)],
    'jealous_embrace': [(6, 'jealous_embrace_bind', 'd', None), (14, 'jealous_embrace_pull', 'd', None), (24, 'jealous_embrace_hit', 'p', None),
                        (24, 'jealous_embrace_mark', 'd', 120)],
    'anvil_strike': [(0, 'anvil_strike', 'impact', None), (15, 'anvil_strike_tempered', 'p', 120)],
    'warlord_banner': [(14, 'warlord_banner_plant', 'banner', None), (14, 'warlord_banner', 'banner', None), (14, 'warlord_banner_buff', 'p', None),
                       (30, 'warlord_banner_soldier', 'sol_l', None), (30, 'warlord_banner_soldier', 'sol_r', None),
                       (36, 'vid_soldier', 'sol_l', None), (36, 'vid_soldier', 'sol_r', None)],
    'mirror_step': [(0, 'mirror_step_out', 'p', None), (4, 'mirror_step_in', 'p_new', None), (8, 'mirror_step_hit', 'd', None),
                    (10, 'mirror_step_veil', 'p_new', None)],
    'hand_of_lies': [(0, 'hand_of_lies', 'd', None), (10, 'hand_of_lies_hold', 'd', 60), (60, 'hand_of_lies_release', 'd', None)],
}


def fx_pos(sid, who):
    dx, _, dz = DUMMY[sid]
    return {'p': [0, 0, 0], 'impact': [dx, 0, dz], 'banner': [0, 0, 1.3], 'sol_l': [1.6, 0, 1.6], 'sol_r': [-1.6, 0, 1.6],
            'p_new': [dx, 0, dz + 1.4]}[who]


def runs_for(sid, f0, tick_of_frame, f_end):
    """fx -> runs (кадры старта/стопа/конца)."""
    out = []
    for tk, fid, who, stop in FXS[sid]:
        s = next((i for i in range(f0, f_end + 1) if tick_of_frame(i) >= tk - 1e-6), None)
        if s is None:
            continue
        r = {'id': fid, 's': s, 'e': f_end}
        if who == 'd':
            r['cId'] = 1
            r['tgId'] = 1
        elif who == 'p':
            r['cId'] = 0
        else:
            r['c'] = fx_pos(sid, who)
        if stop is not None:
            r['stop'] = next((i for i in range(f0, f_end + 1) if tick_of_frame(i) >= stop), f_end)
        out.append(r)
    return out


CAM34 = {'p': [-5.2, 3.0, -3.2], 't': [0.0, 1.0, 2.4]}         # 3/4: справа-сзади-сбоку от игрока, видно и его, и манекен


def cam_for(sid, view):
    dz = DUMMY[sid][2]
    mid = min(dz, 4.5) / 2
    if view == 'side_p':          # проверка поз: крупно сбоку (справа от игрока), игрок в центре
        return {'p': [-4.6, 1.2, 0.9], 't': [0.0, 1.0, 0.9], 'fov': 30}
    if view == 'top_p':
        return {'p': [0.0, 6.5, 0.81], 't': [0.0, 0.0, 0.8], 'upz': True, 'fov': 36}
    if view == 'top':
        return {'p': [0.0, 15.0, mid + 0.01], 't': [0.0, 0.0, mid], 'upz': True, 'fov': 40}
    if view == 'side':
        return {'p': [-9.0, 1.8, mid], 't': [0.0, 1.1, mid], 'fov': 34}
    k = {'jealous_embrace': 1.25, 'anvil_strike': 1.2, 'warlord_banner': 1.1}.get(sid, 1.0)
    return {'p': [-5.0 * k, 2.6 * k, -2.2 * k + mid * 0.3], 't': [0.0, 1.0, mid + 0.6], 'fov': 32}


PHASES = {   # 4 фазы на заклинание (тики) + подписи
    'ashen_harvest': [(9, 'замах'), (11, 'удар (урон)'), (14, 'перехлёст, след'), (30, 'возврат')],
    'jealous_embrace': [(10, 'нити на цели'), (16, 'рывок к себе'), (24, 'удар крюком'), (32, 'метка')],
    'anvil_strike': [(11, 'замах'), (14, 'удар'), (16, 'молот упал'), (30, 'возврат')],
    'warlord_banner': [(10, 'подъём древка'), (14, 'знамя в земле'), (28, 'клич'), (40, 'солдаты')],
    'mirror_step': [(3, 'шаг в рябь'), (6, 'за спиной цели'), (8, 'укол (урон)'), (14, 'невидим')],
    'hand_of_lies': [(7, 'ладонь к цели'), (10, 'хват'), (20, 'держит'), (36, 'отпустил')],
}


def font(sz, bold=True):
    p = '/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if bold else '')
    return ImageFont.truetype(p, sz)


def sheet(three, view='34', out='t34_spells.jpg', phases=None, nofx=False):
    """6 × 4 кадров: для каждой ячейки — отдельный прогон сцены от тика 0 до нужного тика (fx живут правильно)."""
    td = tempfile.mkdtemp()
    frames, runs = [], []
    for si, sid in enumerate(TA.SPEC):
        for pi, (tk, label) in enumerate((phases or PHASES)[sid]):
            f0 = len(frames)
            n = int(math.ceil(tk / 20 * FPS))               # кадры 0..tk с шагом 1/30 с — чтобы fx отработали
            ticks = [min(tk, i * 20 / FPS) for i in range(n + 1)]
            if ticks[-1] < tk:
                ticks.append(tk)
            tof = lambda i, f0=f0, ticks=ticks: ticks[min(len(ticks) - 1, i - f0)]
            f_end = f0 + len(ticks) - 1
            for j, tkk in enumerate(ticks):
                actors = scene(sid, tkk)
                if nofx:                                  # проверка поз: игрок на месте, лицом вперёд, без манекена
                    actors[0].update(x=0, z=0, ry=0, op=1.0)
                    actors = actors[:1]
                fr = {'tick': tkk + 1000 * (si * 4 + pi + 1), 'actors': actors, 'cam': cam_for(sid, view),
                      'arrow': [0, 0, 0.0, 0] if view == 'top' else [0, 0, 0.0, 0]}
                if j == len(ticks) - 1:
                    fr['png'] = os.path.join(td, '%d_%d.png' % (si, pi))
                frames.append(fr)
            for r in ([] if nofx else runs_for(sid, f0, lambda i, tof=tof, si=si, pi=pi: tof(i), f_end)):
                r['e'] = f_end + 1
                runs.append(r)
    run_job(frames, runs, three)
    ph = phases or PHASES
    ncol = max(len(v) for v in ph.values())
    cw, ch = (400, 225) if ncol <= 4 else (300, 169)
    top = 40
    im = Image.new('RGB', (230 + ncol * cw + (ncol + 1) * 6, top + 6 * (ch + 6) + 6), (24, 22, 28))
    d = ImageDraw.Draw(im)
    d.text((10, 8), 'T34 — наградные заклинания боссов: игрок + fx + манекен-цель (%s)' % ('вид сверху: жёлтая стрелка = взгляд игрока'
           if view.startswith('top') else 'проверка поз, сбоку справа' if view == 'side_p' else 'вид 3/4, игрок смотрит вперёд на манекен; жёлтая стрелка у ног = «вперёд»'), font=font(18), fill=(240, 230, 220))
    for si, sid in enumerate(TA.SPEC):
        y = top + si * (ch + 6)
        d.text((10, y + 70), NAMES[sid][0], font=font(17), fill=(255, 216, 96))
        d.text((10, y + 96), NAMES[sid][1], font=font(14, False), fill=(200, 190, 180))
        d.text((10, y + 118), 'pohsmp_' + sid, font=font(11, False), fill=(160, 150, 145))
        for pi, (tk, label) in enumerate(ph[sid]):
            x = 230 + pi * (cw + 6)
            c = Image.open(os.path.join(td, '%d_%d.png' % (si, pi))).convert('RGB').resize((cw, ch), Image.LANCZOS)
            im.paste(c, (x, y))
            d.rectangle([x, y, x + cw, y + 24], fill=(0, 0, 0))
            d.text((x + 6, y + 3), 'тик %g · %s' % (tk, label), font=font(14), fill=(255, 240, 220))
    p = out if os.path.isabs(out) else os.path.join(MEDIA, out)
    im.save(p, quality=90)
    print('wrote', os.path.relpath(p, ROOT))


def video(three):
    frames, runs = [], []
    seg_ticks = {'ashen_harvest': 90, 'jealous_embrace': 130, 'anvil_strike': 90, 'warlord_banner': 120, 'mirror_step': 70, 'hand_of_lies': 100}
    epoch = 0
    for si, sid in enumerate(TA.SPEC):
        name, boss = NAMES[sid]
        L = TA.TIMING[sid]['length']
        tm = TA.TIMING[sid]
        evs = ', '.join('%s %d' % (k, v) for k, v in tm.items() if k not in ('length', 'windup', 'end'))
        # 1) на нормальной скорости (3/4), 2) замедленно ×0.33 (сбоку), 3) вид сверху на нормальной
        for pass_, (view, speed, lbl) in enumerate((('34', 1.0, 'скорость ×1'), ('side', 0.33, 'замедленно ×⅓, вид сбоку'),
                                                    ('top', 1.0, 'вид сверху: стрелка = взгляд'))):
            total = (seg_ticks[sid] if pass_ != 1 else L + 10) / speed
            n = int(total / 20 * FPS)
            f0 = len(frames)
            ticks = [-8 + i * 20 / FPS * speed for i in range(n)]
            epoch += 1
            for j, tk in enumerate(ticks):
                tkc = max(0.0, tk)
                frames.append({'tick': epoch * 2000 + tk, 'actors': scene(sid, tkc), 'cam': cam_for(sid, view), 'arrow': [0, 0, 0, 0],
                               'cap': '%s <span style="color:#ffd860">(%s)</span>' % (name, boss),
                               'sub': 'тик %5.1f / %d · %s · %s' % (tkc, L, lbl, evs), 'head': 'T34 · %d/6' % (si + 1)})
            f_end = len(frames) - 1

            def tof(i, f0=f0, ticks=ticks):
                return ticks[min(len(ticks) - 1, i - f0)]
            for r in runs_for(sid, f0, tof, f_end):
                r['e'] = f_end + 1
                runs.append(r)
    out = os.path.join(MEDIA, 'video', 't34_spells.mp4')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print('video: %d frames (%.1f s)' % (len(frames), len(frames) / FPS))
    run_job(frames, runs, three, mp4=out)
    print('wrote %s (%.1f МБ)' % (os.path.relpath(out, ROOT), os.path.getsize(out) / 1e6))


def main(args):
    three = args[args.index('--three') + 1] if '--three' in args else None
    if '--sheet' in args:
        sheet(three)
    if '--top' in args:
        sheet(three, 'top', 't34_spells_top.jpg')
    if '--video' in args:
        video(three)
    if '--poses' in args:      # проверка поз: 6 фаз, без fx, сбоку и сверху (в docs/media не пишется — scratch)
        ph = {}
        for sid in TA.SPEC:
            tm = TA.TIMING[sid]
            ks = sorted({0, max(0, tm['hit'] - 4), tm['hit'] - 2, tm['hit'], tm['hit'] + 2, tm['hit'] + 5, (tm['hit'] + tm['length']) // 2})
            ph[sid] = [(k, '') for k in ks]
        out = args[args.index('--poses') + 1]
        sheet(three, 'side_p', os.path.abspath(out + '_side.jpg'), ph, nofx=True)
        sheet(three, 'top_p', os.path.abspath(out + '_top.jpg'), ph, nofx=True)


if __name__ == '__main__':
    main(sys.argv[1:])
