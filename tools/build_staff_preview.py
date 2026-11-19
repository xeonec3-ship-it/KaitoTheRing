#!/usr/bin/env python3
"""
3D-превью GeckoLib-посоха с анимациями idle / cast / flash: tools/staff_preview.html.
Берёт geo/item/<name>.geo.json, animations/item/<name>.animation.json и текстуры из assets. Запуск: python3 tools/build_staff_preview.py [name]
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
name = sys.argv[1] if len(sys.argv) > 1 else 'silent_witch_staff'
geo = json.load(open(os.path.join(A, 'geo', 'item', name + '.geo.json')))
anim = json.load(open(os.path.join(A, 'animations', 'item', name + '.animation.json')))
tex = 'data:image/png;base64,' + base64.b64encode(open(os.path.join(A, 'textures', 'item', name + '.png'), 'rb').read()).decode()
glow_p = os.path.join(A, 'textures', 'item', name + '_glowmask.png')
glow = 'data:image/png;base64,' + base64.b64encode(open(glow_p, 'rb').read()).decode() if os.path.exists(glow_p) else ''
data = {'name': name, 'geo': geo, 'anim': anim, 'tex': tex, 'glow': glow}

PAGE = r'''<title>Посох: превью</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;600&family=JetBrains+Mono:wght@400&display=swap">
<style>
:root { --bg: #f1eef8; --panel: #fff; --line: #dcd4ea; --fg: #1b1526; --muted: #6a6079; --accent: #0f8f80; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #0d0b14; --panel: #16121f; --line: #2a2238; --fg: #ece7f4; --muted: #a197b0; --accent: #7fffd0; color-scheme: dark; } }
:root[data-theme="dark"] { --bg: #0d0b14; --panel: #16121f; --line: #2a2238; --fg: #ece7f4; --muted: #a197b0; --accent: #7fffd0; color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font-family: "Golos Text", system-ui, sans-serif; padding: 16px; }
.wrap { max-width: 900px; margin: 0 auto; display: grid; gap: 12px; }
h1 { font-size: clamp(20px, 5vw, 28px); margin: 0; }
p { margin: 0; color: var(--muted); max-width: 66ch; }
.stage { position: relative; border-radius: 14px; overflow: hidden; border: 1px solid var(--line); background: radial-gradient(circle at 50% 40%, #1d2a33, #06080c);
  aspect-ratio: 3 / 4; max-height: 76vh; width: 100%; touch-action: none; }
@media (min-width: 760px) { .stage { aspect-ratio: 4 / 3; } }
canvas { display: block; width: 100%; height: 100%; }
.row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
button { font: inherit; font-size: 14px; color: var(--fg); background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 8px 14px; min-height: 40px; cursor: pointer; }
button[aria-pressed="true"] { border-color: var(--accent); color: var(--accent); font-weight: 600; }
button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.hint { position: absolute; bottom: 10px; left: 0; right: 0; text-align: center; font-size: 12px; color: rgba(230, 240, 238, .6); pointer-events: none; }
</style>
<div class="wrap">
  <h1 id="title">Посох</h1>
  <p>Модель и анимации GeckoLib в том виде, как они лежат в моде. «Покой» — в руке, «Каст» — пока идёт заклинание, «Вспышка» — в момент удара.</p>
  <div class="stage" id="stage"><canvas id="cv" aria-label="Посох в трёхмерной сцене"></canvas><div class="hint">Тяните, чтобы повернуть</div></div>
  <div class="row" role="group" aria-label="Анимация">
    <button type="button" data-a="idle" aria-pressed="true">Покой</button>
    <button type="button" data-a="cast">Каст</button>
    <button type="button" data-a="flash">Вспышка</button>
    <button type="button" id="close">Навершие крупно</button>
  </div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
const D = /*DATA*/null;
document.getElementById("title").textContent = "Посох: " + D.name;
const cv = document.getElementById("cv"), stage = document.getElementById("stage");
const renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: true, alpha: true }); renderer.setPixelRatio(Math.min(2, devicePixelRatio));
const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(32, 1, 0.1, 500);
scene.add(new THREE.AmbientLight(0xffffff, 0.65)); const sun = new THREE.DirectionalLight(0xffffff, 0.7); sun.position.set(20, 40, 30); scene.add(sun);
const loader = new THREE.TextureLoader();
function tx(src) { const t = loader.load(src); t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; return t; }
const base = new THREE.MeshLambertMaterial({ map: tx(D.tex), transparent: true, alphaTest: 0.1 });
const glow = D.glow ? new THREE.MeshBasicMaterial({ map: tx(D.glow), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }) : null;
const G = D.geo["minecraft:geometry"][0], TW = G.description.texture_width, TH = G.description.texture_height;
const D2R = Math.PI / 180, BONES = {}, root = new THREE.Group(); scene.add(root);
function cubeMesh(c) {
  const g = new THREE.BoxGeometry(c.size[0] || 0.001, c.size[1] || 0.001, c.size[2] || 0.001);
  const uv = g.attributes.uv, f = c.uv.north || Object.values(c.uv)[0];
  const u0 = f.uv[0] / TW, v0 = 1 - f.uv[1] / TH, u1 = (f.uv[0] + f.uv_size[0]) / TW, v1 = 1 - (f.uv[1] + f.uv_size[1]) / TH;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) ? u1 : u0, uv.getY(i) ? v0 : v1);
  const grp = new THREE.Group(), m = new THREE.Mesh(g, base); grp.add(m);
  if (glow) grp.add(new THREE.Mesh(g, glow));
  // как GeckoLib: x геометрии зеркалится (x -> -x), у вращений x и y меняют знак
  const cx = -(c.origin[0] + c.size[0] / 2), cy = c.origin[1] + c.size[1] / 2, cz = c.origin[2] + c.size[2] / 2;
  const piv = c.pivot ? [-c.pivot[0], c.pivot[1], c.pivot[2]] : [cx, cy, cz];
  const holder = new THREE.Group(); holder.position.set(piv[0], piv[1], piv[2]);
  const r = c.rotation || [0, 0, 0]; holder.rotation.set(-r[0] * D2R, -r[1] * D2R, r[2] * D2R, "ZYX");
  grp.position.set(cx - piv[0], cy - piv[1], cz - piv[2]);
  holder.add(grp); return holder;
}
// кости: позиция = pivot относительно родителя; анимация вращает вокруг pivot (знаки как в GeckoLib: x и y инвертированы)
for (const b of G.bones) {
  const o = new THREE.Group(), inner = new THREE.Group(); o.add(inner);
  o.userData = { pivot: [-b.pivot[0], b.pivot[1], b.pivot[2]], rest: (b.rotation || [0, 0, 0]).map((v) => v * D2R) };
  BONES[b.name] = o;
}
for (const b of G.bones) {
  const o = BONES[b.name], p = b.parent ? BONES[b.parent] : null, pp = p ? p.userData.pivot : [0, 0, 0], bp = o.userData.pivot;
  o.position.set(bp[0] - pp[0], bp[1] - pp[1], bp[2] - pp[2]);
  (p ? p.children[0] : root).add(o);
  for (const c of b.cubes || []) { const m = cubeMesh(c); m.position.x -= bp[0]; m.position.y -= bp[1]; m.position.z -= bp[2]; o.children[0].add(m); }
}
function sample(track, t, def) {
  if (!track) return def;
  const ks = Object.keys(track).map(Number).sort((a, b) => a - b);
  if (t <= ks[0]) return track[String(ks[0])] || track[ks[0].toString()];
  for (let i = 1; i < ks.length; i++) if (t <= ks[i]) {
    const a = ks[i - 1], b = ks[i], k = (t - a) / (b - a), va = track[Object.keys(track).find((x) => +x === a)], vb = track[Object.keys(track).find((x) => +x === b)];
    return [0, 1, 2].map((j) => va[j] + (vb[j] - va[j]) * k);
  }
  return track[Object.keys(track).find((x) => +x === ks[ks.length - 1])];
}
let cur = "idle", t0 = performance.now();
document.querySelectorAll("[data-a]").forEach((b) => b.addEventListener("click", () => {
  cur = b.dataset.a; t0 = performance.now();
  document.querySelectorAll("[data-a]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
}));
let yaw = 0.5, pitch = 0.12, dist = 70, tgt = 6, drag = null, close = false;
document.getElementById("close").addEventListener("click", (e) => { close = !close; e.target.setAttribute("aria-pressed", String(close)); });
stage.addEventListener("pointerdown", (e) => { drag = [e.clientX, e.clientY, yaw, pitch]; stage.setPointerCapture(e.pointerId); });
stage.addEventListener("pointermove", (e) => { if (drag) { yaw = drag[2] - (e.clientX - drag[0]) * 0.01; pitch = Math.max(-1, Math.min(1.2, drag[3] + (e.clientY - drag[1]) * 0.006)); } });
stage.addEventListener("pointerup", () => (drag = null));
window.STEP = null;   // для снимков: задать время вручную
function frame(now) {
  const A = D.anim.animations[cur], len = A.animation_length;
  let t = window.STEP !== null ? window.STEP : (now - t0) / 1000;
  if (A.loop) t %= len; else if (t > len + 0.6) { cur = "idle"; t0 = now; document.querySelector('[data-a="idle"]').click(); }
  t = Math.min(t, len);
  for (const [n, o] of Object.entries(BONES)) {
    const tr = A.bones[n] || {}, r = sample(tr.rotation, t, [0, 0, 0]), s = sample(tr.scale, t, [1, 1, 1]), p = sample(tr.position, t, [0, 0, 0]);
    const rest = o.userData.rest, inner = o.children[0];
    inner.rotation.set(-rest[0] - r[0] * D2R, -rest[1] - r[1] * D2R, rest[2] + r[2] * D2R, "ZYX");
    inner.scale.set(s[0], s[1], s[2]); inner.position.set(p[0], p[1], p[2]);
  }
  const w = stage.clientWidth, h = stage.clientHeight;
  if (cv.width !== Math.round(w * renderer.getPixelRatio())) { renderer.setSize(w, h, false); cam.aspect = w / h; cam.updateProjectionMatrix(); }
  const d = close ? 26 : dist, ty = close ? 20 : tgt;
  cam.position.set(Math.sin(yaw) * Math.cos(pitch) * d, ty + Math.sin(pitch) * d, Math.cos(yaw) * Math.cos(pitch) * d); cam.lookAt(0, ty, 0);
  renderer.render(scene, cam); requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
</script>
'''
out = os.path.join(HERE, 'staff_preview.html')
open(out, 'w', encoding='utf-8').write(PAGE.replace('/*DATA*/null', json.dumps(data, separators=(',', ':'))))
print('wrote', out)
