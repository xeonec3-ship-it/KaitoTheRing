#!/usr/bin/env python3
"""
Стенд кадров и видео T35 (броня боссов на игроке): three.js r128 + Playwright/Chromium (как остальные наши превью).

Сцена повторяет GeckoLib 4.8.4 (GeoArmorRenderer): кости bipedX/armorX, x геометрии зеркален, повороты Z·Y·X, у ключей анимаций
x/y со знаком минус; поза игрока — формулы ванильного HumanoidModel.setupAnim (шаг/бег: ноги ±1.4·amount рад, руки ±amount),
переведённые в кадр GeckoLib: (−xRot, −yRot, zRot). Полы/плащ/табард следуют за ногами по таблице FOLLOW (её же получает программист:
docs/inbox/2026-11-21_mgr_T35_visuals_B.md). Шлемы для проверки маски — ванильные текстуры из client-extra.jar (кэш ForgeGradle),
в репозиторий они не кладутся.

  python3 tools/t35_armor_render.py --sheet docs/media/t35_armor_B.jpg
  python3 tools/t35_armor_render.py --video docs/media/video/t35_armor_B.mp4
  python3 tools/t35_armor_render.py --check     → кадры-проверки ходьбы (scratch) + числовая проверка проходов ткани сквозь ноги
"""
import base64
import glob
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
CDN = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'
CLIENT = glob.glob(os.path.expanduser('~/.gradle/caches/forge_gradle/minecraft_repo/versions/1.20.1/client-extra.jar'))

# Следование ткани за ногами: кость -> (какие ноги, направление, множитель). rel = rotX(ноги) − rotX(armorBody), внутр. угол GeckoLib.
#   'front': += k · max(0, rel)  (нога вперёд толкает полу вперёд)   'back': += k · min(0, rel)  (нога назад — пола назад)
FOLLOW = {
    'warlord': {'cape': ('both', 'back', 0.35), 'cape_low': ('both', 'back', 0.45)},
}


def b64(data):
    if isinstance(data, str):
        data = open(data, 'rb').read()
    return 'data:image/png;base64,' + base64.b64encode(data).decode()


def pil_b64(img):
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    return b64(buf.getvalue())


def vanilla(path):
    if not CLIENT:
        return None
    with zipfile.ZipFile(CLIENT[0]) as z:
        try:
            return z.read('assets/minecraft/' + path)
        except KeyError:
            return None


# ---------------------------------------------------------------- модели
def box_uv(u, v, w, h, d):
    """Box UV (как в Blockbench / ванильный скин) -> развёртка по граням."""
    return {'north': {'uv': [u + d, v + d], 'uv_size': [w, h]}, 'east': {'uv': [u, v + d], 'uv_size': [d, h]},
            'south': {'uv': [u + 2 * d + w, v + d], 'uv_size': [w, h]}, 'west': {'uv': [u + d + w, v + d], 'uv_size': [d, h]},
            'up': {'uv': [u + d + w, v + d], 'uv_size': [-w, -d]}, 'down': {'uv': [u + d + 2 * w, v], 'uv_size': [-w, d]}}


def _cube(o, s, uv, inflate=0):
    c = {'origin': o, 'size': s, 'uv': box_uv(*uv, *s)}
    if inflate:
        c['inflate'] = inflate
    return c


def player_geo():
    """Игрок 64×64 (широкие руки) с внешним слоем; координаты — как в .geo.json (правая сторона −x)."""
    B = [('bipedHead', [0, 24, 0], [([-4, 24, -4], [8, 8, 8], (0, 0), 0), ([-4, 24, -4], [8, 8, 8], (32, 0), 0.5)]),
         ('bipedBody', [0, 24, 0], [([-4, 12, -2], [8, 12, 4], (16, 16), 0), ([-4, 12, -2], [8, 12, 4], (16, 32), 0.25)]),
         ('bipedRightArm', [-5, 22, 0], [([-8, 12, -2], [4, 12, 4], (40, 16), 0), ([-8, 12, -2], [4, 12, 4], (40, 32), 0.25)]),
         ('bipedLeftArm', [5, 22, 0], [([4, 12, -2], [4, 12, 4], (32, 48), 0), ([4, 12, -2], [4, 12, 4], (48, 48), 0.25)]),
         ('bipedRightLeg', [-1.9, 12, 0], [([-3.9, 0, -2], [4, 12, 4], (0, 16), 0), ([-3.9, 0, -2], [4, 12, 4], (0, 32), 0.25)]),
         ('bipedLeftLeg', [1.9, 12, 0], [([-0.1, 0, -2], [4, 12, 4], (16, 48), 0), ([-0.1, 0, -2], [4, 12, 4], (0, 48), 0.25)])]
    bones = [{'name': n, 'pivot': p, 'cubes': [_cube(o, s, uv, inf) for o, s, uv, inf in cs]} for n, p, cs in B]
    return {'minecraft:geometry': [{'description': {'texture_width': 64, 'texture_height': 64}, 'bones': bones}]}


def helmet_geo():
    return {'minecraft:geometry': [{'description': {'texture_width': 64, 'texture_height': 32}, 'bones': [
        {'name': 'bipedHead', 'pivot': [0, 24, 0]},
        {'name': 'armorHead', 'parent': 'bipedHead', 'pivot': [0, 24, 0], 'cubes': [_cube([-4, 24, -4], [8, 8, 8], (0, 0), 1.0)]}]}]}


def tint(png, rgb):
    im = Image.open(io.BytesIO(png)).convert('RGBA')
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            px[x, y] = (r * rgb[0] // 255, g * rgb[1] // 255, b * rgb[2] // 255, a)
    return im


HELMETS = ('iron', 'gold', 'diamond', 'netherite', 'chainmail', 'leather', 'turtle')
HELMET_RU = {'iron': 'железный', 'gold': 'золотой', 'diamond': 'алмазный', 'netherite': 'незеритовый', 'chainmail': 'кольчужный',
             'leather': 'кожаный', 'turtle': 'черепаший'}


def models():
    d = {}
    for n in ('warlord', 'traitor', 'mask_of_lies'):
        glow = os.path.join(A, 'textures', 'armor', n + '_glowmask.png')
        d[n] = {'geo': json.load(open(os.path.join(A, 'geo', 'armor', n + '.geo.json'))),
                'tex': b64(os.path.join(A, 'textures', 'armor', n + '.png')), 'glow': b64(glow) if os.path.exists(glow) else None,
                'anims': json.load(open(os.path.join(A, 'animations', 'armor', n + '.animation.json')))['animations'],
                'follow': FOLLOW.get(n, {})}
    steve = vanilla('textures/entity/player/wide/steve.png')
    if steve is None:
        import cult_leader_render as CR
        steve_img = CR.steve_skin()
        d['player'] = {'geo': player_geo(), 'tex': pil_b64(steve_img)}
    else:
        d['player'] = {'geo': player_geo(), 'tex': b64(steve)}
    for h in HELMETS:
        png = vanilla('textures/models/armor/%s_layer_1.png' % h)
        if png is None:
            continue
        if h == 'leather':
            base = tint(png, (0xA0, 0x65, 0x40))
            ov = vanilla('textures/models/armor/leather_layer_1_overlay.png')
            if ov:
                base.alpha_composite(Image.open(io.BytesIO(ov)).convert('RGBA'))
            png = io.BytesIO()
            base.save(png, 'PNG')
            png = png.getvalue()
        d['helmet_' + h] = {'geo': helmet_geo(), 'tex': b64(png)}
    for n, sc in (('martin', 2.0), ('ereb', 1.0), ('ereb_hand', 1.0)):
        tex = os.path.join(A, 'textures', 'entity', n, n + '.png')
        glow = os.path.join(A, 'textures', 'entity', n, n + '_glowmask.png')
        an = json.load(open(os.path.join(A, 'animations', 'entity', n + '.animation.json')))['animations']
        d[n] = {'geo': json.load(open(os.path.join(A, 'geo', 'entity', n + '.geo.json'))), 'tex': b64(tex),
                'glow': b64(glow) if os.path.exists(glow) else None, 'scale': sc,
                'anims': {k: v for k, v in an.items() if k in ('martin_npc_idle', 'martin_idle', 'ereb_idle', 'ereb_hand_idle')}}
    return d


PAGE = r'''<!doctype html><meta charset="utf-8"><title>T35 броня B</title>
<style>
html, body { margin: 0; background: #14161c; color: #e9e6ef; font-family: "Golos Text", "DejaVu Sans", sans-serif; overflow: hidden; }
canvas { display: block; }
.lab { position: absolute; font-size: 15px; font-weight: 600; text-shadow: 0 1px 2px #000; pointer-events: none; }
.lab small { display: block; font-weight: 400; font-size: 12px; color: #b9b2c7; }
.cap { position: absolute; left: 0; right: 0; bottom: 18px; text-align: center; font-size: 26px; font-weight: 600; text-shadow: 0 2px 4px #000; }
.cap small { display: block; font-size: 17px; font-weight: 400; color: #c9c2d6; }
</style>
<canvas id="cv"></canvas><div id="labs"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
const D = /*DATA*/null, CELLS = /*CELLS*/null;
const D2R = Math.PI / 180;
const cv = document.getElementById("cv");
const W = CELLS.size[0], H = CELLS.size[1];
const renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H); renderer.autoClear = false;
const loader = new THREE.TextureLoader();
let pending = 0;
function tx(src) { pending++; const t = loader.load(src, () => pending--); t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; return t; }
const TEX = {};
for (const [n, m] of Object.entries(D)) TEX[n] = { base: tx(m.tex), glow: m.glow ? tx(m.glow) : null };

// ------------------------------------------------------------------ модель GeckoLib -> three.js
function cubeMesh(c, mats, TW, TH) {
  const inf = c.inflate || 0;
  const g = new THREE.BoxGeometry((c.size[0] + 2 * inf) || 0.001, (c.size[1] + 2 * inf) || 0.001, (c.size[2] + 2 * inf) || 0.001);
  const uv = g.attributes.uv, ORDERF = ["east", "west", "up", "down", "south", "north"];
  const keep = [];
  for (let fi = 0; fi < 6; fi++) {
    const f = c.uv[ORDERF[fi]];
    if (!f) { for (let i = fi * 4; i < fi * 4 + 4; i++) uv.setXY(i, 0, 0); continue; }
    keep.push(fi);
    const u0 = f.uv[0] / TW, v0 = 1 - f.uv[1] / TH, u1 = (f.uv[0] + f.uv_size[0]) / TW, v1 = 1 - (f.uv[1] + f.uv_size[1]) / TH;
    for (let i = fi * 4; i < fi * 4 + 4; i++) uv.setXY(i, uv.getX(i) ? u1 : u0, uv.getY(i) ? v0 : v1);
  }
  // грани без развёртки (hide) убираем из индекса
  const idx = g.index.array, ni = [];
  for (const fi of keep) for (let k = 0; k < 6; k++) ni.push(idx[fi * 6 + k]);
  g.setIndex(ni);
  const grp = new THREE.Group();
  for (const m of mats) grp.add(new THREE.Mesh(g, m));
  const cx = -(c.origin[0] + c.size[0] / 2), cy = c.origin[1] + c.size[1] / 2, cz = c.origin[2] + c.size[2] / 2;
  const piv = c.pivot ? [-c.pivot[0], c.pivot[1], c.pivot[2]] : [cx, cy, cz];
  const holder = new THREE.Group(); holder.position.set(piv[0], piv[1], piv[2]);
  const r = c.rotation || [0, 0, 0]; holder.rotation.set(-r[0] * D2R, -r[1] * D2R, r[2] * D2R, "ZYX");
  grp.position.set(cx - piv[0], cy - piv[1], cz - piv[2]);
  holder.add(grp); return holder;
}
function build(name) {
  const M = D[name], G = M.geo["minecraft:geometry"][0], TW = G.description.texture_width, TH = G.description.texture_height;
  const mats = [new THREE.MeshLambertMaterial({ map: TEX[name].base, transparent: true, alphaTest: 0.1, side: THREE.DoubleSide })];
  if (TEX[name].glow) mats.push(new THREE.MeshBasicMaterial({ map: TEX[name].glow, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0.0 }));
  const root = new THREE.Group(), bones = {};
  for (const b of G.bones) {
    const o = new THREE.Group(), inner = new THREE.Group(); o.add(inner);
    o.userData = { pivot: [-b.pivot[0], b.pivot[1], b.pivot[2]], rest: (b.rotation || [0, 0, 0]).map((v) => v * D2R) };
    bones[b.name] = o;
  }
  for (const b of G.bones) {
    const o = bones[b.name], p = b.parent ? bones[b.parent] : null, pp = p ? p.userData.pivot : [0, 0, 0], bp = o.userData.pivot;
    o.position.set(bp[0] - pp[0], bp[1] - pp[1], bp[2] - pp[2]);
    (p ? p.children[0] : root).add(o);
    for (const c of b.cubes || []) { const m = cubeMesh(c, mats, TW, TH); m.position.x -= bp[0]; m.position.y -= bp[1]; m.position.z -= bp[2]; o.children[0].add(m); }
  }
  const s = M.scale || 1; root.scale.set(s, s, s);
  return { name, root, bones, mats, anims: M.anims || {}, follow: M.follow || {} };
}
function sample(track, t, def) {
  if (!track) return def;
  if (Array.isArray(track)) return track;
  const ks = Object.keys(track).map(Number).sort((a, b) => a - b), val = (k) => { const v = track[Object.keys(track).find((x) => +x === k)]; return Array.isArray(v) ? v : (v.post || v.vector || v); };
  if (t <= ks[0]) return val(ks[0]);
  for (let i = 1; i < ks.length; i++) if (t <= ks[i]) { const a = ks[i - 1], b = ks[i], k = (t - a) / (b - a), va = val(a), vb = val(b); return [0, 1, 2].map((j) => +va[j] + (+vb[j] - +va[j]) * k); }
  return val(ks[ks.length - 1]);
}
// поворот кости: rest + анимация (знаки GeckoLib) + доп. внутренний угол extra [x, y, z] (поза игрока, следование)
function setBone(o, r, extra, pos) {
  const rest = o.userData.rest, inner = o.children[0];
  inner.rotation.set(-rest[0] - r[0] * D2R + extra[0], -rest[1] - r[1] * D2R + extra[1], rest[2] + r[2] * D2R + extra[2], "ZYX");
  if (pos) inner.position.set(-pos[0], pos[1], pos[2]);
}
function animate(m, animName, t, extra) {
  const A = m.anims[animName], len = A ? A.animation_length : 1;
  let tt = A ? (A.loop ? t % len : Math.min(t, len)) : 0;
  for (const [n, o] of Object.entries(m.bones)) {
    const tr = A ? (A.bones[n] || {}) : {};
    setBone(o, sample(tr.rotation, tt, [0, 0, 0]), (extra && extra[n]) || [0, 0, 0], tr.position ? sample(tr.position, tt, [0, 0, 0]) : null);
  }
}

// ------------------------------------------------------------------ ванильная поза игрока (кадр GeckoLib)
function pose(motion, t, look) {
  const age = t * 20;
  let amount = 0, p = 0;
  if (motion === "walk") { amount = 0.86; p = age * 0.86; }
  if (motion === "run") { amount = 1.0; p = age * 1.0; }
  if (motion === "step") { amount = 1.0; p = t; }                  // ручная фаза: t — limbSwing
  const c = Math.cos(p * 0.6662), c2 = Math.cos(p * 0.6662 + Math.PI);
  let rA = c2 * 2 * amount * 0.5, lA = c * 2 * amount * 0.5, rL = c * 1.4 * amount, lL = c2 * 1.4 * amount;
  const bobZ = Math.cos(age * 0.09) * 0.05 + 0.05, bobX = Math.sin(age * 0.067) * 0.05;
  rA += bobX; lA -= bobX;
  const L = look || [0, 0];
  return { bipedHead: [-L[0], -L[1], 0], bipedBody: [0, 0, 0], bipedRightArm: [-rA, 0, bobZ], bipedLeftArm: [-lA, 0, -bobZ],
           bipedRightLeg: [-rL, 0, 0], bipedLeftLeg: [-lL, 0, 0] };
}
const SLOT = { head: ["armorHead"], chest: ["armorBody", "armorRightArm", "armorLeftArm"], legs: ["armorRightLeg", "armorLeftLeg"], feet: ["armorRightBoot", "armorLeftBoot"] };
const ARMOR_OF = { bipedHead: "armorHead", bipedBody: "armorBody", bipedRightArm: "armorRightArm", bipedLeftArm: "armorLeftArm",
                   bipedRightLeg: "armorRightLeg", bipedLeftLeg: "armorLeftLeg" };

// фигура игрока в броне: {armor: "warlord", pieces: [...], helmet: "iron" | null, mask: true, motion, look}
function player(spec) {
  const g = new THREE.Group(), parts = [build("player")];
  const armor = spec.armor ? build(spec.armor) : null;
  if (armor) {
    const show = new Set(); for (const p of spec.pieces || ["head", "chest", "legs", "feet"]) for (const b of SLOT[p]) show.add(b);
    for (const b of Object.values(SLOT).flat()) if (armor.bones[b]) armor.bones[b].visible = show.has(b);
    parts.push(armor);
  }
  if (spec.helmet && D["helmet_" + spec.helmet]) parts.push(build("helmet_" + spec.helmet));
  if (spec.mask) {
    const mk = build("mask_of_lies");
    const covered = !!(spec.helmet || (armor && (spec.pieces || ["head"]).includes("head")));
    mk.bones.mask.visible = covered; mk.bones.mask_face.visible = !covered;
    parts.push(mk);
  }
  if (spec.hideSkin) parts[0].root.visible = false;
  for (const p of parts) g.add(p.root);
  return { group: g, parts, spec, armor };
}
function posePlayer(f, t) {
  const P = pose(f.spec.motion || "idle", t, f.spec.look);
  const anim = { idle: "idle", walk: "walk", run: "run", step: "walk" }[f.spec.motion || "idle"];
  for (const m of f.parts) {
    const extra = {};
    for (const [bn, r] of Object.entries(P)) { extra[bn] = [0, 0, 0]; if (ARMOR_OF[bn]) extra[ARMOR_OF[bn]] = [0, 0, 0]; }
    if (m.name === "player") for (const [bn, r] of Object.entries(P)) extra[bn] = r;
    else {
      for (const [bn, r] of Object.entries(P)) if (ARMOR_OF[bn]) extra[ARMOR_OF[bn]] = r;
      extra.armorRightBoot = P.bipedRightLeg; extra.armorLeftBoot = P.bipedLeftLeg;
      const body = P.bipedBody[0], relR = P.bipedRightLeg[0] - body, relL = P.bipedLeftLeg[0] - body;
      for (const [bn, [legs, dir, k]] of Object.entries(m.follow)) {
        const v = legs === "right" ? [relR] : legs === "left" ? [relL] : [relR, relL];
        const a = dir === "front" ? Math.max(0, ...v) : Math.min(0, ...v);
        extra[bn] = [k * a, 0, 0];
      }
    }
    animate(m, m.anims[anim] ? anim : "idle", t, extra);
  }
}

// ------------------------------------------------------------------ сцена ячейки
function cellScene(cell) {
  const scene = new THREE.Scene();
  scene.add(new THREE.AmbientLight(0xffffff, cell.dark ? 0.12 : 0.62));
  const sun = new THREE.DirectionalLight(0xffffff, cell.dark ? 0.1 : 0.62); sun.position.set(30, 50, -40); scene.add(sun);
  const fill = new THREE.DirectionalLight(0xffffff, cell.dark ? 0.05 : 0.22); fill.position.set(-40, 20, 40); scene.add(fill);
  // пол: шахматка 1 блок = 16 ед.
  const cnv = document.createElement("canvas"); cnv.width = cnv.height = 2; const cx = cnv.getContext("2d");
  cx.fillStyle = cell.floor || "#2b2e36"; cx.fillRect(0, 0, 2, 2); cx.fillStyle = cell.floor2 || "#33363f"; cx.fillRect(0, 0, 1, 1); cx.fillRect(1, 1, 1, 1);
  const ft = new THREE.CanvasTexture(cnv); ft.magFilter = THREE.NearestFilter; ft.wrapS = ft.wrapT = THREE.RepeatWrapping; ft.repeat.set(16, 16);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(256, 256), new THREE.MeshLambertMaterial({ map: ft }));
  floor.rotation.x = -Math.PI / 2; floor.position.y = -0.01; scene.add(floor);
  const figs = [];
  for (const f of cell.figs) {
    let fig;
    if (f.boss) { const m = build(f.boss); fig = { group: new THREE.Group(), parts: [m], boss: f }; fig.group.add(m.root); }
    else fig = player(f);
    fig.group.position.set(...(f.pos || [0, 0, 0])); fig.group.rotation.y = (f.ry || 0) * D2R;
    fig.t = f.t || 0; scene.add(fig.group); figs.push(fig);
    for (const m of fig.parts) for (const mm of m.mats) if (mm.blending === THREE.AdditiveBlending) mm.opacity = cell.dark ? 0.9 : 0.0;
  }
  return { scene, figs, sun };
}
function poseCell(cs, cell, t) {
  for (const f of cs.figs) {
    const tt = (f.t || 0) + t;
    if (f.boss) animate(f.parts[0], f.boss.anim, tt, null);
    else posePlayer(f, tt);
  }
}
function camFor(cell, w, h, t) {
  const c = cell.cam || {}, cam = new THREE.PerspectiveCamera(c.fov || 30, w / h, 0.5, 2000);
  const yaw = ((c.yaw || 0) + (c.spin || 0) * t) * D2R, pit = (c.pitch || 6) * D2R, d = c.dist || 90, ty = c.ty || 17, tx = c.tx || 0;
  cam.position.set(tx + Math.sin(yaw) * Math.cos(pit) * d, ty + Math.sin(pit) * d, -Math.cos(yaw) * Math.cos(pit) * d);
  cam.lookAt(tx, ty, 0); return cam;
}
// ------------------------------------------------------------------ кадр-лист / видео
const SCENES = CELLS.cells.map(cellScene);
function layout() {
  const cols = CELLS.cols, rows = Math.ceil(CELLS.cells.length / cols), cw = Math.floor(W / cols), ch = Math.floor(H / rows);
  return CELLS.cells.map((c, i) => ({ x: (i % cols) * cw, y: Math.floor(i / cols) * ch, w: c.wide ? cw * c.wide : cw, h: ch }));
}
const LAY = layout();
function drawAll(t) {
  renderer.setScissorTest(true);
  renderer.setClearColor(0x14161c); renderer.clear();
  CELLS.cells.forEach((cell, i) => {
    const L = LAY[i], cs = SCENES[i];
    poseCell(cs, cell, cell.time !== undefined ? cell.time : t);
    renderer.setViewport(L.x, H - L.y - L.h, L.w, L.h); renderer.setScissor(L.x + 1, H - L.y - L.h + 1, L.w - 2, L.h - 2);
    renderer.setClearColor(cell.dark ? 0x07070a : (cell.bg || 0x1c1f27)); renderer.clear();
    renderer.render(cs.scene, camFor(cell, L.w, L.h, t));
  });
}
function labels(t) {
  const labs = document.getElementById("labs"); labs.innerHTML = "";
  CELLS.cells.forEach((cell, i) => {
    const L = LAY[i];
    if (cell.label) { const d = document.createElement("div"); d.className = "lab"; d.style.left = (L.x + 10) + "px"; d.style.top = (L.y + 8) + "px";
      d.innerHTML = cell.label + (cell.sub ? "<small>" + cell.sub + "</small>" : ""); labs.appendChild(d); }
    if (cell.caption) { const d = document.createElement("div"); d.className = "cap"; d.innerHTML = cell.caption; labs.appendChild(d); }
  });
}
window.frameAt = (t) => { drawAll(t); labels(t); return true; };
function ready() { if (pending > 0) return setTimeout(ready, 50); window.frameAt(0); window.READY = true; }
ready();
</script>
'''


def page(cells, size):
    d = models()
    html = PAGE.replace('/*DATA*/null', json.dumps(d, separators=(',', ':')))
    html = html.replace('/*CELLS*/null', json.dumps(dict(cells, size=list(size)), ensure_ascii=False))
    three = os.path.join(HERE, '..', 'build', 'three.min.js')
    return html


JS_SHOT = r"""
const { chromium } = require('playwright');
(async () => {
  const [html, out, w, h, frames, fps] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
  const pg = await b.newPage({ viewport: { width: +w, height: +h } });
  pg.on('console', m => { if (m.type() === 'error') console.log('console:', m.text()); });
  pg.on('pageerror', e => console.log('pageerror:', e.message));
  await pg.goto('file://' + html);
  await pg.waitForFunction('window.READY === true', null, { timeout: 240000 });
  if (+frames <= 0) {
    await pg.screenshot({ path: out, type: out.endsWith('.jpg') ? 'jpeg' : 'png', quality: out.endsWith('.jpg') ? 92 : undefined });
  } else {
    for (let i = 0; i < +frames; i++) {
      await pg.evaluate((t) => window.frameAt(t), i / +fps);
      await pg.screenshot({ path: out + '/f' + String(i).padStart(5, '0') + '.png' });
    }
  }
  await b.close();
})();
"""


def run_page(html, out, size, frames=0, fps=30):
    tmpd = tempfile.mkdtemp(prefix='t35r_')
    hp = os.path.join(tmpd, 'p.html')
    with open(hp, 'w', encoding='utf-8') as fh:
        fh.write(html)
    js = os.path.join(tmpd, 'shot.js')
    with open(js, 'w') as fh:
        fh.write(JS_SHOT)
    env = dict(os.environ, NODE_PATH=subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True).stdout.strip())
    r = subprocess.run(['node', js, hp, out, str(size[0]), str(size[1]), str(frames), str(fps)], capture_output=True, text=True, env=env)
    if r.stdout.strip() or r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
    shutil.rmtree(tmpd, ignore_errors=True)


# ================================================================== содержание кадр-листа
def fig(armor, x=0, ry=0, **kw):
    d = {'armor': armor, 'pos': [x, 0, 0], 'ry': ry}
    d.update(kw)
    return d


def sheet_cells():
    C = []
    for a, ru in (('warlord', '«Доспех Полководца»'), ('traitor', '«Камзол Предателя»')):
        for yaw, nm in ((0, 'спереди'), (90, 'сбоку'), (180, 'сзади'), (35, '3/4, шаг')):
            C.append({'label': ru + ' — ' + nm, 'sub': 'все 4 части' if yaw != 35 else 'полы/плащ следуют за ногами',
                      'figs': [fig(a, motion='step' if yaw == 35 else 'idle', t=2.2 if yaw == 35 else 0)],
                      'cam': {'yaw': yaw, 'dist': 82, 'ty': 18}, 'time': 0})
    # рядом с боссом (в одном масштабе: Мартин ×2, как в игре)
    C.append({'label': 'рядом с Мартином', 'sub': 'Мартин ×2, как в игре', 'time': 0.4,
              'figs': [fig('warlord', x=-12, ry=-10), {'boss': 'martin', 'anim': 'martin_npc_idle', 'pos': [16, 0, 6], 'ry': 15}],
              'cam': {'yaw': 8, 'dist': 175, 'ty': 32, 'tx': 4}})
    C.append({'label': 'рядом с Эребом', 'sub': 'в одном масштабе и свете', 'time': 0.4,
              'figs': [fig('traitor', x=-10, ry=-12), {'boss': 'ereb', 'anim': 'ereb_idle', 'pos': [10, 0, 0], 'ry': -20}],
              'cam': {'yaw': 0, 'dist': 98, 'ty': 18}})
    C.append({'label': 'Маска Лжи рядом с Дланью', 'sub': 'на лице без шлема', 'time': 0.4,
              'figs': [fig(None, x=-10, ry=-12, mask=True), {'boss': 'ereb_hand', 'anim': 'ereb_hand_idle', 'pos': [10, 0, 0], 'ry': 12}],
              'cam': {'yaw': 0, 'dist': 70, 'ty': 24}})
    C.append({'label': 'в темноте', 'sub': 'glowmask: стекло, трещины маски', 'dark': True, 'time': 0,
              'figs': [fig('traitor', x=-9, mask=True), fig('warlord', x=9)], 'cam': {'yaw': 0, 'dist': 92, 'ty': 18}})
    # маска поверх шлемов: крупно, 3/4
    hs = [None, 'leather', 'chainmail', 'iron', 'gold', 'diamond', 'netherite', 'turtle']
    for h in hs:
        C.append({'label': 'маска: ' + ('без шлема' if h is None else HELMET_RU[h] + ' шлем'), 'time': 0,
                  'figs': [fig(None, mask=True, helmet=h)], 'cam': {'yaw': 28, 'pitch': 4, 'dist': 34, 'ty': 27, 'fov': 26}})
    for a, ru in (('warlord', 'на Шлеме Полководца'), ('traitor', 'на Венце Предателя')):
        C.append({'label': 'маска ' + ru, 'time': 0, 'figs': [fig(a, mask=True)], 'cam': {'yaw': 28, 'pitch': 4, 'dist': 38, 'ty': 28, 'fov': 26}})
    C.append({'label': 'маска сбоку', 'sub': 'незерит: не проходит сквозь шлем', 'time': 0, 'figs': [fig(None, mask=True, helmet='netherite')],
              'cam': {'yaw': 70, 'pitch': 0, 'dist': 52, 'ty': 27, 'fov': 26}})
    C.append({'label': 'маска сверху', 'sub': 'не сливается с волосами', 'time': 0, 'figs': [fig(None, mask=True, look=[-0.5, 0])],
              'cam': {'yaw': 20, 'pitch': 50, 'dist': 34, 'ty': 27, 'fov': 26}})
    return {'cols': 4, 'cells': C}


def make_sheet(out):
    cells = sheet_cells()
    rows = math.ceil(len(cells['cells']) / cells['cols'])
    size = (1600, 450 * rows)
    run_page(page(cells, size), os.path.abspath(out), size)
    print('wrote', out)


# ================================================================== проверочные кадры ходьбы (по фазам шага)
def check_cells(armor, motion='step'):
    C = []
    for k, ph in enumerate((0.0, 1.2, 2.36, 3.5, 4.7, 5.9, 7.1, 8.3)):
        C.append({'label': '%s фаза %.1f' % (armor, ph), 'time': 0, 'figs': [fig(armor, motion='step', t=ph)],
                  'cam': {'yaw': 90 if k < 4 else 60, 'dist': 80, 'ty': 15}})
    return {'cols': 4, 'cells': C}


# ================================================================== видео (turntable + ходьба)
SEGMENTS = [   # (длительность, ячейка-шаблон)
    (6.0, {'caption': '«Доспех Полководца» <small>комплект Мартина: шлем-корона с плюмажем, кираса, табард, плащ</small>',
           'figs': [fig('warlord')], 'cam': {'yaw': 0, 'spin': 60, 'dist': 80, 'ty': 18}}),
    (6.0, {'caption': '«Доспех Полководца» — шаг <small>табард и плащ следуют за ногами</small>',
           'figs': [fig('warlord', motion='walk')], 'cam': {'yaw': 0, 'spin': -60, 'dist': 80, 'ty': 18}}),
    (3.0, {'caption': '«Доспех Полководца» — бег', 'figs': [fig('warlord', motion='run')], 'cam': {'yaw': 70, 'spin': 20, 'dist': 80, 'ty': 18}}),
    (4.0, {'caption': 'рядом с Мартином <small>в одном масштабе (Мартин ×2)</small>',
           'figs': [fig('warlord', x=-12, ry=-10), {'boss': 'martin', 'anim': 'martin_npc_idle', 'pos': [16, 0, 6], 'ry': 15}],
           'cam': {'yaw': -10, 'spin': 8, 'dist': 175, 'ty': 32, 'tx': 4}}),
    (6.0, {'caption': '«Камзол Предателя» <small>комплект Эреба: венец со стеклом, камзол, брюки, сапоги</small>',
           'figs': [fig('traitor')], 'cam': {'yaw': 0, 'spin': 60, 'dist': 80, 'ty': 18}}),
    (6.0, {'caption': '«Камзол Предателя» — шаг <small>полы камзола следуют за ногами</small>',
           'figs': [fig('traitor', motion='walk')], 'cam': {'yaw': 0, 'spin': -60, 'dist': 80, 'ty': 18}}),
    (3.0, {'caption': '«Камзол Предателя» — бег', 'figs': [fig('traitor', motion='run')], 'cam': {'yaw': 70, 'spin': 20, 'dist': 80, 'ty': 18}}),
    (4.0, {'caption': 'рядом с Эребом', 'figs': [fig('traitor', x=-10, ry=-12), {'boss': 'ereb', 'anim': 'ereb_idle', 'pos': [10, 0, 0], 'ry': -20}],
           'cam': {'yaw': -10, 'spin': 8, 'dist': 98, 'ty': 18}}),
]


def video_cells():
    segs = list(SEGMENTS)
    for h in (None, 'leather', 'chainmail', 'iron', 'gold', 'diamond', 'netherite', 'turtle', 'warlord', 'traitor'):
        armor = h if h in ('warlord', 'traitor') else None
        nm = 'без шлема' if h is None else ('Шлем Полководца' if h == 'warlord' else 'Венец Предателя' if h == 'traitor' else HELMET_RU[h] + ' шлем')
        segs.append((1.6, {'caption': '«Маска Лжи» поверх любого шлема <small>%s</small>' % nm,
                           'figs': [fig(armor, mask=True, helmet=None if armor else h, pieces=['head'])],
                           'cam': {'yaw': -50, 'spin': 60, 'dist': 40, 'ty': 26, 'fov': 26}}))
    segs.append((4.0, {'caption': '«Маска Лжи» рядом с Дланью Лжи',
                       'figs': [fig(None, x=-10, ry=-12, mask=True), {'boss': 'ereb_hand', 'anim': 'ereb_hand_idle', 'pos': [10, 0, 0], 'ry': 12}],
                       'cam': {'yaw': -10, 'spin': 8, 'dist': 72, 'ty': 22}}))
    segs.append((5.0, {'caption': 'шаг в полном комплекте с маской', 'figs': [fig('traitor', motion='walk', mask=True, x=-15), fig('warlord', motion='walk', mask=True, x=15)],
                       'cam': {'yaw': 0, 'spin': 72, 'dist': 120, 'ty': 18}}))
    return segs


def make_video(out, fps=30, size=(1280, 720)):
    frames_dir = tempfile.mkdtemp(prefix='t35v_')
    n = 0
    for si, (dur, cell) in enumerate(video_cells()):
        nf = int(round(dur * fps))
        sd = os.path.join(frames_dir, 's%02d' % si)
        os.makedirs(sd)
        run_page(page({'cols': 1, 'cells': [cell]}, size), sd, size, frames=nf, fps=fps)
        for f in sorted(os.listdir(sd)):
            os.rename(os.path.join(sd, f), os.path.join(frames_dir, 'g%05d.png' % n))
            n += 1
        print('segment', si, nf, 'frames')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(fps), '-i', os.path.join(frames_dir, 'g%05d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '27', '-preset', 'slow', '-movflags', '+faststart', out], check=True)
    shutil.rmtree(frames_dir, ignore_errors=True)
    print('wrote', out, n, 'frames')


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--sheet' in args:
        make_sheet(args[args.index('--sheet') + 1])
    if '--check' in args:
        out = args[args.index('--check') + 1]
        for a in ('warlord', 'traitor'):
            cells = check_cells(a)
            run_page(page(cells, (1600, 900)), os.path.abspath(out.replace('.jpg', '_%s.jpg' % a)), (1600, 900))
    if '--cells' in args:                                   # отладка: --cells cells.json out.jpg
        i = args.index('--cells')
        cells = json.load(open(args[i + 1], encoding='utf-8'))
        size = tuple(cells.get('size', (1600, 900)))
        run_page(page(cells, size), os.path.abspath(args[i + 2]), size)
    if '--video' in args:
        make_video(args[args.index('--video') + 1])
