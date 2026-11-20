// Покадровый драйвер видео-превью боссов (вставляется tools/boss_video_b.py вместо блока CELLS шаблона превью).
// window.frame(spec) рисует один кадр: модели (с анимацией и временем), мэши fx/meshes, спрайты-эффекты, подписи. Модели и визуал — из ассетов как есть.
const VTEX = /*VTEX*/null;
const PRELOAD = /*PRELOAD*/null;
const IS_EREB = !!(DATA && DATA.models);
document.getElementById('ui').style.display = 'none';
const VW = window.innerWidth, VH = window.innerHeight;
renderer.setViewport(0, 0, VW, VH); renderer.setScissor(0, 0, VW, VH);

const STEX = {};
function stex(n) {
  if (!STEX[n]) { const t = new THREE.TextureLoader().load(VTEX[n]); t.magFilter = THREE.LinearFilter; t.minFilter = THREE.LinearFilter; t.generateMipmaps = false; STEX[n] = t; }
  return STEX[n];
}
function entryOf(n) { return IS_EREB ? DATA.models[n] : DATA[n]; }
function animOf(n, a) { if (!a) return null; return IS_EREB ? DATA.anims[a] : (DATA[n].anims || {})[a]; }

const OBJ = {}, MESH = {};
function getObj(o) {
  const k = o.key || o.model;
  if (!OBJ[k]) {
    let e = entryOf(o.model);
    if (o.smile && e.smile) e = Object.assign({}, e, { texOverride: e.smile });
    const m = IS_EREB ? buildModel(e, false) : buildModel(e);
    const mats = new Map();
    m.root.traverse(x => { if (x.isMesh && x.material && !mats.has(x.material)) mats.set(x.material, { op: x.material.opacity, tr: x.material.transparent, at: x.material.alphaTest, dw: x.material.depthWrite }); });
    OBJ[k] = { m, mats, base: m.root.scale.x, lastOp: 1 };
  }
  return OBJ[k];
}
function setOp(ob, op) {
  if (Math.abs(ob.lastOp - op) < 1e-4) return;
  for (const [mt, b] of ob.mats) {
    const fade = op < 0.999;
    mt.opacity = b.op * op;
    const tr = b.tr || fade, at = fade ? Math.min(b.at, 0.02) : b.at;
    if (mt.transparent !== tr || mt.alphaTest !== at) { mt.transparent = tr; mt.alphaTest = at; mt.needsUpdate = true; }
  }
  ob.lastOp = op;
}
// плавный переход между позами: поза A, запомнить, поза B, смешать
function poseMix(m, a, ta, b, tb, k) {
  pose(m, a, ta);
  const saved = {};
  for (const n in m.bones) { const g = m.bones[n]; saved[n] = [g.position.clone(), g.rotation.clone(), g.scale.clone()]; }
  pose(m, b, tb);
  for (const n in m.bones) {
    const g = m.bones[n], s = saved[n];
    g.position.lerpVectors(s[0], g.position, k);
    g.rotation.set(s[1].x + (g.rotation.x - s[1].x) * k, s[1].y + (g.rotation.y - s[1].y) * k, s[1].z + (g.rotation.z - s[1].z) * k, 'ZYX');
    g.scale.lerpVectors(s[2], g.scale, k);
  }
}

let SCENE = null, SKEY = null, LIGHTS = [];
const TR = new THREE.Group();
function groundMesh(size) {
  const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d');
  const A = IS_EREB ? ['#3a2e28', '#342822'] : ['#2a2420', '#24201c'];
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { x.fillStyle = (i + j) % 2 ? A[0] : A[1]; x.fillRect(i * 16, j * 16, 16, 16); }
  const gt = new THREE.CanvasTexture(c); gt.magFilter = THREE.NearestFilter; gt.wrapS = gt.wrapT = THREE.RepeatWrapping; gt.repeat.set(size, size);
  const gr = new THREE.Mesh(new THREE.PlaneGeometry(size * 16, size * 16), new THREE.MeshLambertMaterial({ map: gt }));
  gr.rotation.x = -Math.PI / 2; gr.position.y = -0.01;
  return gr;
}
function sceneFor(f) {
  const key = JSON.stringify([f.bg || 0, f.ground !== false, f.groundSize || 96, f.fog || 0]);
  if (SKEY === key) return SCENE;
  const sc = IS_EREB ? makeScene({ bg: f.bg, ground: false }) : makeScene(Object.assign({}, entryOf('martin'), f.bg ? { bg: f.bg } : {}), false);
  if (f.fog) sc.fog = new THREE.Fog(sc.background, f.fog[0] * 16, f.fog[1] * 16);
  if (f.ground !== false) sc.add(groundMesh(f.groundSize || 96));
  LIGHTS = sc.children.filter(o => o.isLight).map(l => [l, l.intensity]);
  sc.add(TR);
  for (const k in OBJ) if (OBJ[k].m.root.parent) OBJ[k].m.root.parent.remove(OBJ[k].m.root);
  for (const k in MESH) if (MESH[k].parent) MESH[k].parent.remove(MESH[k]);
  SCENE = sc; SKEY = key;
  return sc;
}

const PLANE = new THREE.PlaneGeometry(1, 1);
const SMAT = {};
function spriteMat(s) {
  const op = Math.round(Math.max(0, Math.min(1, s.op ?? 1)) * 50) / 50;
  const key = [s.tex, s.color || '#ffffff', s.add === false ? 0 : 1, op].join('|');
  if (!SMAT[key]) SMAT[key] = new THREE.MeshBasicMaterial({ map: stex(s.tex), color: new THREE.Color(s.color || '#ffffff'), transparent: true, depthWrite: false,
    opacity: op, blending: s.add === false ? THREE.NormalBlending : THREE.AdditiveBlending, side: THREE.DoubleSide });
  return SMAT[key];
}

const OV = {};
function overlay() {
  const css = document.createElement('style');
  css.textContent = `
  #vcap{position:fixed;left:0;right:0;bottom:14px;text-align:center;z-index:9;pointer-events:none}
  #vcap .b{display:inline-block;background:rgba(10,7,9,.62);border:1px solid rgba(232,185,90,.35);border-radius:6px;padding:5px 18px 6px;max-width:1100px}
  #vcap .n{font:600 24px "DejaVu Serif",serif;color:#f1e3c4;text-shadow:0 0 6px #000}
  #vcap .s{font:400 14px "DejaVu Sans",sans-serif;color:#cbbcae;margin-top:3px}
  #vtitle{position:fixed;left:0;right:0;top:26px;text-align:center;z-index:9;pointer-events:none}
  #vtitle img{width:540px}
  #vtitle .t{font:700 44px "DejaVu Serif",serif;color:#e8c372;text-shadow:0 0 10px #000,0 0 3px #000;letter-spacing:1px}
  #vspeech{position:fixed;left:0;right:0;bottom:96px;text-align:center;z-index:9;pointer-events:none;font:italic 400 28px "DejaVu Serif",serif;color:#fff;text-shadow:0 0 6px #000,0 0 2px #000}
  #vtag{position:fixed;left:16px;top:12px;z-index:9;font:600 15px "DejaVu Sans",sans-serif;color:rgba(232,220,200,.55);pointer-events:none}
  #vtint{position:fixed;inset:0;z-index:8;pointer-events:none}
  #vfade{position:fixed;inset:0;z-index:10;background:#000;pointer-events:none}`;
  document.head.appendChild(css);
  for (const id of ['vcap', 'vtitle', 'vspeech', 'vtag', 'vtint', 'vfade']) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d); OV[id] = d; }
}
overlay();
const last = {};
function setHTML(id, html) { if (last[id] !== html) { OV[id].innerHTML = html; last[id] = html; } }

window.frame = (f) => {
  const sc = sceneFor(f);
  for (const [l, i] of LIGHTS) l.intensity = i * (f.dim ?? 1);
  while (TR.children.length) TR.remove(TR.children[0]);
  for (const k in OBJ) OBJ[k].m.root.visible = false;
  for (const k in MESH) MESH[k].visible = false;
  for (const o of (f.objs || [])) {
    const ob = getObj(o), r = ob.m.root;
    if (r.parent !== sc) sc.add(r);
    const op = o.op ?? 1;
    r.visible = op > 0.003;
    if (o.mix) poseMix(ob.m, animOf(o.model, o.anim), o.t || 0, animOf(o.model, o.mix.anim), o.mix.t || 0, o.mix.k);
    else pose(ob.m, animOf(o.model, o.anim), o.t || 0);
    r.position.set(o.pos[0] * 16, o.pos[1] * 16, o.pos[2] * 16);
    r.rotation.set(0, (o.ry || 0) * Math.PI / 180, 0);
    r.scale.setScalar(ob.base * (o.scale ?? 1));
    setOp(ob, op);
  }
  for (const m of (f.meshes || [])) {
    const k = m.key || m.mesh;
    if (!MESH[k]) {
      const g = buildBoxes(m.mesh);
      g.traverse(o => { if (o.material) { o.material = o.material.clone(); o.userData.bop = o.material.opacity; o.material.transparent = true; o.material.depthWrite = false; } });
      MESH[k] = g;
    }
    const g = MESH[k];
    if (g.parent !== sc) sc.add(g);
    g.visible = (m.op ?? 1) > 0.003;
    g.position.set(m.pos[0] * 16, m.pos[1] * 16, m.pos[2] * 16);
    g.rotation.set((m.rx || 0) * Math.PI / 180, (m.ry || 0) * Math.PI / 180, (m.rz || 0) * Math.PI / 180, 'YXZ');
    g.scale.set(m.sx ?? m.scale ?? 1, m.sy ?? m.scale ?? 1, m.sz ?? m.scale ?? 1);
    g.traverse(o => { if (o.material) o.material.opacity = o.userData.bop * (m.op ?? 1); });
  }
  const cam = new THREE.PerspectiveCamera(f.cam.fov || 30, VW / VH, 0.5, 8000);
  cam.position.set(f.cam.pos[0] * 16, f.cam.pos[1] * 16, f.cam.pos[2] * 16);
  cam.lookAt(f.cam.look[0] * 16, f.cam.look[1] * 16, f.cam.look[2] * 16);
  for (const s of (f.sprites || [])) {
    if ((s.op ?? 1) <= 0.01) continue;
    const m = new THREE.Mesh(PLANE, spriteMat(s));
    m.scale.set((s.w ?? s.size) * 16, (s.h ?? s.size) * 16, 1);
    m.position.set(s.at[0] * 16, s.at[1] * 16, s.at[2] * 16);
    if (s.ground) { m.rotation.set(-Math.PI / 2, 0, (s.rot || 0) * Math.PI / 180); m.position.y = (s.at[1] || 0.03) * 16; }
    else if (s.vertical) m.rotation.set(0, (s.ry || 0) * Math.PI / 180, (s.rot || 0) * Math.PI / 180, 'YXZ');
    else { m.quaternion.copy(cam.quaternion); m.rotateZ((s.rot || 0) * Math.PI / 180); }
    m.renderOrder = s.order ?? 5; TR.add(m);
  }
  renderer.render(sc, cam);
  setHTML('vcap', f.cap ? `<div class="b"><div class="n">${f.cap}</div>${f.sub ? `<div class="s">${f.sub}</div>` : ''}</div>` : '');
  OV.vcap.style.opacity = f.capOp ?? 1;
  setHTML('vtitle', f.title ? (f.title.img ? `<img src="${VTEX[f.title.img]}">` : `<div class="t">${f.title.text}</div>`) : '');
  OV.vtitle.style.opacity = f.title ? (f.title.op ?? 1) : 0;
  setHTML('vspeech', f.speech ? `<span style="background:rgba(8,6,8,.5);padding:4px 14px;border-radius:5px">${f.speech.text}</span>` : ''); OV.vspeech.style.opacity = f.speech ? (f.speech.op ?? 1) : 0;
  setHTML('vtag', f.tag || '');
  OV.vtint.style.background = f.tint ? f.tint[0] : 'transparent'; OV.vtint.style.opacity = f.tint ? f.tint[1] : 0;
  OV.vfade.style.opacity = Math.min(0.82, f.fade || 0);   // затемнение на стыках — не до чёрного
};

// предзагрузка моделей и текстур, затем READY
for (const o of (PRELOAD || [])) getObj(o);
for (const k in VTEX) stex(k);
THREE.DefaultLoadingManager.onLoad = () => { setTimeout(() => { window.READY = true; }, 100); };
