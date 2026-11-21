#!/usr/bin/env python3
"""
Видео-превью анимаций боссов T26 (Тирос / Глава Культа), T27 (Ирина), T28 (Арис) — с fx.
Модели, анимации и текстуры берутся как есть из assets: код моделей — из страниц превью боссов (tools/*_preview.template.html),
fx/печати/меши fx — движком превью эффектов tools/sigil_preview.template.html (тот же, что в tools/build_sigil_preview.py).
Здесь только раскадровка: какие анимации, когда какие fx (по событиям анимаций из писем T26–T28), камера, титры.
  python3 tools/boss_video.py [t26|t27|t28 ...] [--only turntable,combat,special,finale] [--three путь/three.min.js]
Нужно: jar Iron's в libs/ (python3 tools/fetch_libs.py), Playwright + Chromium, ffmpeg.
Выход: docs/media/video/t2X_{turntable,combat,special,finale}.mp4 (1280×720, 30 fps, H.264, без звука) + t2X_turntable.gif (480 px).
Оси раскадровки: босс в начале координат смотрит в −z (как в превью боссов), x — вправо от него; единицы — пиксели модели (16 = блок);
fx задаются в блоках в тех же осях. Движок fx живёт в осях «взгляд = +Z», перевод — в адаптере (x, z → −x, −z).
"""
import base64
import glob
import io
import json
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
OUT = os.path.join(ROOT, 'docs', 'media', 'video')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
CDN = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'
FPS, W, H = 30, 1280, 720
PAUSE = 0.3
B = 16                       # пикселей модели в блоке
sys.path.insert(0, HERE)
FXDEF = {os.path.splitext(os.path.basename(f))[0]: json.load(open(f, encoding='utf-8')) for f in glob.glob(os.path.join(A, 'fx', '*.json'))}


def ease_io(x):
    x = max(0.0, min(1.0, x))
    return -(math.cos(math.pi * x) - 1) / 2


def ease_in_quad(x):
    x = max(0.0, min(1.0, x))
    return x * x


def secs(x):
    return max(1, int(round(x * FPS)))


# ---------------------------------------------------------------- данные: движок fx, модели боссов, жертва, коса
def sigil_data():
    """То же, что вшивает tools/build_sigil_preview.py: печати, меши fx, fx, стили, текстуры, шрифты."""
    data = {'sigils': {}, 'textures': {}, 'meshes': {}, 'styles': {}, 'fx': {}, 'fonts': {}}
    for key, pat in (('sigils', 'sigils/*.json'), ('meshes', 'fx/meshes/*.json'), ('fx', 'fx/*.json'), ('styles', 'fx/styles/*.json')):
        for f in sorted(glob.glob(os.path.join(A, pat))):
            data[key][os.path.splitext(os.path.basename(f))[0]] = json.load(open(f, encoding='utf-8'))
    for f in sorted(glob.glob(os.path.join(A, 'textures', 'sigil', '*.png'))):
        data['textures'][os.path.splitext(os.path.basename(f))[0]] = 'data:image/png;base64,' + base64.b64encode(open(f, 'rb').read()).decode()
    used = {l.get('texture') for s in data['sigils'].values() for l in s.get('layers', [])}
    used |= {e.get('texture') for f in data['fx'].values() for e in f.get('elements', [])}
    from PIL import Image
    for f in sorted(glob.glob(os.path.join(A, 'textures', 'fx', '*.png'))):
        name = os.path.splitext(os.path.basename(f))[0]
        if name not in used or name in data['textures']:
            continue
        im = Image.open(f)
        if max(im.size) > 256:
            im = im.resize((256, round(256 * im.size[1] / im.size[0])), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, 'PNG', optimize=True)
        data['textures'][name] = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
    for f in sorted(glob.glob(os.path.join(A, 'textures', 'sigil', 'glyphs_*.json'))):
        g = json.load(open(f, encoding='utf-8'))
        data['fonts'][g['font']] = g
    return data


def victim_anim(name='pohsmp_cult_finisher_victim'):
    """PlayerAnimator-эмоция (жертва добивания) → ключи GeckoLib для каркаса abstract_casting_mob (Стив-жертва)."""
    p = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'irons_spellbooks', 'player_animation', name + '.json')
    em = json.load(open(p, encoding='utf-8'))['emote']
    parts = {'rightArm': 'right_arm', 'leftArm': 'left_arm', 'head': 'head', 'rightLeg': 'right_leg', 'leftLeg': 'left_leg', 'torso': 'body'}
    keys = {}
    for mv in em['moves']:
        for k, v in mv.items():
            if k in parts and isinstance(v, dict):
                keys.setdefault(k, {})[mv['tick']] = v
    bones = {}
    for k, kk in keys.items():
        rot = {}
        for tick in sorted(kk):
            v = kk[tick]
            pitch, yaw, roll = v.get('pitch', 0), v.get('yaw', 0), v.get('roll', 0)
            if k in ('rightLeg', 'leftLeg'):                   # корпус наклоняется костью body (родитель ног) — ноги компенсируем
                pitch -= keys['torso'].get(tick, {}).get('pitch', 0)
            rot['%.4f' % (tick / 20)] = [-pitch, -yaw, roll]
        bones[parts[k]] = {'rotation': rot}
    return {'animation_length': em['endTick'] / 20, 'loop': 'hold_on_last_frame', 'bones': bones}


def cult_hold_anims():
    """Глава Культа вне анимаций (CultLeaderModel.setCustomAnimations): `~hold` — поза хвата Тироса (CultMath.HOLD_*), `~walk` — ходьба
    (AbstractSpellCastingMobModel Iron's: ноги ±cos·1.4·x·0.75, левая рука cos·x, корпус подпрыгивает; правая с косой неподвижна;
    x = 0.6 — наш getLimbSwing, цикл 9.43 позиции шага ≈ 0.47 с на полном ходу). Оси — оси анимаций (X/Y поворота — минус к Java)."""
    from gen_cult_leader_extra import CARRY_ARM, CARRY_HAND
    hold = {'animation_length': 1.0, 'loop': True, 'bones': {
        'right_arm': {'rotation': {'0.0': {'vector': CARRY_ARM}}}, 'bipedHandRight': {'rotation': {'0.0': {'vector': CARRY_HAND}}}}}
    L, x, R = 0.94, 0.6, 180 / math.pi
    ch = {b: {} for b in ('right_leg', 'left_leg', 'left_arm', 'body')}
    for i in range(int(L / 0.02) + 1):
        t = round(i * 0.02, 3)
        y = t / L * 2 * (2 * math.pi / 0.6662)          # два шага за цикл
        c = math.cos(y * 0.6662)
        k = '%.4g' % t if t else '0.0'
        ch['right_leg'][k] = {'vector': [round(-c * 1.4 * x * 0.75 * R, 2), 0, 0]}
        ch['left_leg'][k] = {'vector': [round(c * 1.4 * x * 0.75 * R, 2), 0, 0]}
        ch['left_arm'][k] = {'vector': [round(-c * x * R, 2), 0, 0]}
        ch['body'][k] = {'vector': [0, round(abs(math.cos((y * 1.2662 - math.pi / 2) * 0.5)) * 2 * 0.75 * x, 3), 0]}
    walk = {'animation_length': L, 'loop': True, 'bones': dict(hold['bones'], **{
        'right_leg': {'rotation': ch['right_leg']}, 'left_leg': {'rotation': ch['left_leg']}, 'left_arm': {'rotation': ch['left_arm']},
        'body': {'position': ch['body']}})}
    return {'~hold': hold, '~walk': walk}


def scythe_item():
    """Коса Главы Культа: models/item/cult_scythe.json (бруски) + палитра textures/item/cult_scythe_3d.png; острие лезвия — tip."""
    from PIL import Image
    doc = json.load(open(os.path.join(A, 'models', 'item', 'cult_scythe.json'), encoding='utf-8'))['base']
    pal = Image.open(os.path.join(A, 'textures', 'item', 'cult_scythe_3d.png')).convert('RGB')
    els = []
    for e in doc['elements']:
        fc = {f: '#%02x%02x%02x' % pal.getpixel((int(v['uv'][0]), int(v['uv'][1]))) for f, v in e['faces'].items()}
        els.append([e['from'], e['to'], e.get('rotation'), fc])
    return {'els': els, 'display': doc['display'], 'tip': [3.55, 11.34, 8.0]}


def steve_entry():
    import cult_leader_render as cr
    return cr.model_entry('steve')


def boss_lib(boss):
    """Код моделей из шаблона превью босса (до создания renderer) в отдельной области видимости + его DATA."""
    if boss == 'tyros':
        import cult_leader_render as cr
        e = cr.model_entry('cult_leader')
        e['scythe'] = False                                     # вместо силуэта — настоящая коса cult_scythe
        data = {'models': {'cult_leader': e}, 'anims': cr.iron_anims()}
        tpl = 'cult_leader_preview.template.html'
    elif boss == 'irina':
        import irina_render as ir
        data = ir.data()
        data.pop('cl', None)
        tpl = 'irina_preview.template.html'
    else:
        import aris_render as ar
        data = ar.data()
        data['models'].pop('cult_leader', None)
        tpl = 'aris_preview.template.html'
    src = open(os.path.join(HERE, tpl), encoding='utf-8').read()
    i0 = src.index('const DATA = /*DATA*/null;')
    i1 = src.index('const renderer')
    code = src[i0:i1].replace('const DATA = /*DATA*/null;', 'const DATA = %s;' % json.dumps(data, ensure_ascii=False, separators=(',', ':')), 1)
    names = ['buildModel', 'pose', 'flameFrame', 'attachStaff', 'buildMesh']
    ret = ', '.join('%s: typeof %s === "undefined" ? null : %s' % (n, n, n) for n in names)
    return '<script>\nconst BL = (() => {\n%s\nreturn { DATA, %s };\n})();\n</script>\n' % (code, ret)


# ---------------------------------------------------------------- адаптер: сцена движка fx + модели боссов
ADAPTER = r"""
<script>
window.VID = (() => {
  const D = Math.PI / 180, W = VW, H = VH, CFG = VCFG;
  const cache = {}; let RUNS = [], cap, head, fade, flash, lastTick = 0;
  const M = (p) => new THREE.Vector3(-(p[0] || 0), p[1] || 0, -(p[2] || 0));       // оси раскадровки (блоки) → оси движка fx
  // декали с yaw (линии разреза, полосы): в превью-движке yaw декали не применялся — поворачиваем плоскость вокруг вертикали
  const _make = FxRun.prototype.make;
  FxRun.prototype.make = function (it) { _make.call(this, it); const e = it.e; if (e.type === 'decal' && e.yaw && it.m) it.m.rotation.z = e.yaw * D; };
  // меши fx: плашка «проявления» в превью рассчитана на ворота 12×3 бл. — подгоняем под размер меша
  const _pmake = Portal.prototype.make;
  Portal.prototype.make = function (p) {
    const P = _pmake.call(this, p);
    if (p.type === 'boxes' && P.flash && p.boxes.length) {
      const xs = p.boxes.flatMap(b => [b[0], b[3]]), zs = p.boxes.flatMap(b => [b[2], b[5]]);
      P.flash.scale.set(Math.max(0.1, (Math.max(...xs) - Math.min(...xs)) * 1.1) / 12, 0.5, Math.max(0.1, (Math.max(...zs) - Math.min(...zs)) * 1.1) / 3);
    }
    return P;
  };
  // mesh.move.keys [тик, [x, y, z], плавность к ключу] (исполинский молот «Последнего удара»): в превью-движке не было
  const _pupd = Portal.prototype.update;
  Portal.prototype.update = function (t, dt) {
    _pupd.call(this, t, dt);
    const K = this.move && this.move.keys;
    if (!K) return;
    const lt = t - this.t0;
    let v = K[K.length - 1][1];
    if (lt < K[0][0]) v = K[0][1];
    else for (let i = 1; i < K.length; i++) if (lt <= K[i][0]) {
      const a = K[i - 1], b = K[i], k = ease(b[2] || 'linear', clamp01((lt - a[0]) / Math.max(1, b[0] - a[0])));
      v = a[1].map((x, j) => x + (b[1][j] - x) * k); break;
    }
    this.root.position.copy(this.base).add(new THREE.Vector3(-v[0], v[1], v[2]));
  };
  function itemMesh(els) {
    const grp = new THREE.Group();
    for (const [a, b, rot, fc] of els) {
      const mats = ['east', 'west', 'up', 'down', 'south', 'north'].map(f => new THREE.MeshLambertMaterial({ color: fc[f] || fc.north }));
      const m = new THREE.Mesh(new THREE.BoxGeometry(b[0] - a[0] || 0.01, b[1] - a[1] || 0.01, b[2] - a[2] || 0.01), mats);
      const c = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2];
      if (rot) {
        const p = new THREE.Group(); p.position.set(rot.origin[0] - 8, rot.origin[1] - 8, rot.origin[2] - 8);
        p.rotation[rot.axis] = rot.angle * Math.PI / 180;
        m.position.set(c[0] - rot.origin[0], c[1] - rot.origin[1], c[2] - rot.origin[2]); p.add(m); grp.add(p);
      } else { m.position.set(c[0] - 8, c[1] - 8, c[2] - 8); grp.add(m); }
    }
    return grp;
  }
  function attachItem(model, item) {                    // как у Iron's / превью Ирины: предмет в правой руке по кости bipedHandRight
    const hand = model.bones.bipedHandRight; if (!hand) return;
    const d = item.display.thirdperson_righthand;
    // GeckoLib 4.8.4 (BlockAndItemGeoLayer.renderForBone): предмет поворачивается поворотом кисти ДВАЖДЫ — второй раз здесь (dbl)
    const dbl = new THREE.Group(); hand.add(dbl); model.dbl = dbl;
    const a = new THREE.Group(); a.position.set(0, -1, -1); dbl.add(a);
    const b = new THREE.Group(); b.rotation.x = -Math.PI / 2; a.add(b);
    const t = new THREE.Group(); t.position.set(...(d.translation || [0, 0, 0])); b.add(t);
    const r = new THREE.Group(); r.quaternion.setFromEuler(new THREE.Euler(...(d.rotation || [0, 0, 0]).map(v => v * D), 'XYZ')); t.add(r);
    const s = new THREE.Group(); s.scale.set(...(d.scale || [1, 1, 1])); r.add(s);
    const it = itemMesh(item.els); s.add(it);
    const tip = new THREE.Object3D(); tip.position.set(item.tip[0] - 8, item.tip[1] - 8, item.tip[2] - 8); it.add(tip);
    model.item = a; model.tip = tip;
  }
  function init() {
    window.requestAnimationFrame = () => 0;                // цикл страницы превью fx не нужен: кадры ведём сами
    INST.forEach(s => s.dispose()); INST = [];
    caster.visible = false; grid.visible = false;
    scene.children.filter(o => o.isHemisphereLight).forEach(o => scene.remove(o));
    scene.background = new THREE.Color(CFG.bg);
    if (CFG.fog) scene.fog = new THREE.Fog(CFG.bg, 20, 60);
    scene.add(new THREE.HemisphereLight(CFG.hemi[0], CFG.hemi[1], CFG.hemi[2]));
    for (const [c, k, p] of CFG.dirs) { const l = new THREE.DirectionalLight(c, k); l.position.set(-p[0], p[1], -p[2]); scene.add(l); }
    const gc = document.createElement('canvas'); gc.width = gc.height = 64; const x = gc.getContext('2d');
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { x.fillStyle = (i + j) % 2 ? CFG.g1 : CFG.g2; x.fillRect(i * 16, j * 16, 16, 16); }
    const gt = new THREE.CanvasTexture(gc); gt.magFilter = THREE.NearestFilter; gt.wrapS = gt.wrapT = THREE.RepeatWrapping; gt.repeat.set(128, 128);
    const gr = new THREE.Mesh(new THREE.PlaneGeometry(512, 512), new THREE.MeshLambertMaterial({ map: gt }));
    gr.rotation.x = -Math.PI / 2; gr.position.y = -0.005; gr.renderOrder = -1; scene.add(gr);
    for (const el of [...document.body.children]) if (el.tagName !== 'SCRIPT') el.style.display = 'none';   // страница превью fx: оставить только сцену
    document.body.appendChild(stage);
    stage.style.cssText = `display:block;position:fixed;left:0;top:0;width:${W}px;height:${H}px;max-height:none;max-width:none;aspect-ratio:auto;margin:0;border:0;border-radius:0;overflow:hidden`;
    for (const el of stage.querySelectorAll('.hud,.hint')) el.style.display = 'none';
    document.body.style.cssText = 'margin:0;padding:0;overflow:hidden;background:#000';
    renderer.setPixelRatio(1); renderer.setSize(W, H, false); cv.style.cssText = `display:block;width:${W}px;height:${H}px`;
    cam.fov = 30; cam.aspect = W / H; cam.near = 0.05; cam.far = 700; cam.updateProjectionMatrix();
    const css = document.createElement('style');
    css.textContent = `#vcap{position:fixed;left:0;right:0;bottom:34px;text-align:center;z-index:30;font:600 30px 'DejaVu Sans',system-ui,sans-serif;
      color:#f6eee6;text-shadow:0 0 6px #000,0 0 3px #000,0 2px 2px #000} #vcap small{display:block;font:400 17px 'DejaVu Sans Mono',monospace;color:#c8bcb4;margin-top:4px}
      #vhead{position:fixed;left:22px;top:16px;z-index:30;font:600 18px 'DejaVu Sans',system-ui,sans-serif;color:#e8dcd2;opacity:.85;text-shadow:0 0 4px #000}
      #vfade,#vflash{position:fixed;left:0;top:0;width:${W}px;height:${H}px;z-index:29;pointer-events:none;opacity:0} #vfade{background:#000} #vflash{background:#fff6e8}`;
    document.head.appendChild(css);
    for (const id of ['vcap', 'vhead', 'vfade', 'vflash']) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d); }
    cap = document.getElementById('vcap'); head = document.getElementById('vhead');
    fade = document.getElementById('vfade'); flash = document.getElementById('vflash');
    RUNS = CFG.runs.map(r => Object.assign({}, r));
    for (const k of CFG.preload) getModel(k);
  }
  function getModel(a) {
    const key = a.k + '|' + (a.v || '');
    if (cache[key]) return cache[key];
    let m;
    if (a.k === 'boss') {
      if (CFG.boss === 'tyros') { m = BL.buildModel(BL.DATA.models.cult_leader, a.v === 'soul'); attachItem(m, CFG.scythe); }
      else if (CFG.boss === 'irina') { m = BL.buildModel(); BL.attachStaff(m); }
      else m = BL.buildModel(BL.DATA.models.aris, a.v || 'base');
    } else if (a.k === 'steve') {
      const e = CFG.steve;
      m = CFG.boss === 'aris' ? BL.buildModel({ geo: e.geo, tex: { base: e.tex }, glow: {} }, 'base') : BL.buildModel({ geo: e.geo, tex: e.tex });
    } else if (a.k === 'scythe') {
      m = { root: new THREE.Group(), bones: {} }; m.root.add(itemMesh(CFG.scythe.els));
    } else if (a.k.startsWith('mesh:')) {
      m = { root: BL.buildMesh(BL.DATA.meshes[a.k.slice(5)], 16), bones: {} };
    }
    m.holder = new THREE.Group(); m.holder.add(m.root); scene.add(m.holder); m.holder.visible = false;
    return cache[key] = m;
  }
  const AN = n => n ? (BL.DATA.anims[n] || VANIMS[n] || null) : null;
  function doPose(m, a, p) {
    if (!m.bones || !Object.keys(m.bones).length) return;
    const an = AN(p.anim), t = p.t || 0;
    if (CFG.boss === 'tyros') BL.pose(m, an, t);
    else if (CFG.boss === 'irina') BL.pose(m, an, a.k === 'boss' ? AN(p.cloth || 'irina_cloth_idle') : null, t, p.tc);
    else BL.pose(m, an, t, p.hide);
  }
  function applyPose(m, a) {
    doPose(m, a, a);
    if (!a.blend) return;
    const s = {};
    for (const n in m.bones) { const g = m.bones[n]; s[n] = [g.position.clone(), g.quaternion.clone(), g.scale.clone()]; }
    doPose(m, a, a.blend);
    const w = a.blend.w;
    for (const n in m.bones) {
      const g = m.bones[n];
      g.position.lerpVectors(s[n][0], g.position.clone(), w);
      g.quaternion.copy(s[n][1].clone().slerp(g.quaternion.clone(), w));
      g.scale.lerpVectors(s[n][2], g.scale.clone(), w);
    }
  }
  function setFig(r, pos) {
    FIG.caster.copy(r.cId !== undefined && pos[r.cId] ? pos[r.cId] : M(r.c || [0, 0, 0]));
    FIG.target.copy(r.tgId !== undefined && pos[r.tgId] ? pos[r.tgId] : M(r.tg || r.c || [0, 0, 0]));
    for (const [k, v] of Object.entries(r.pts || {})) FIG['point:' + k] = M(v);
  }
  function render(f) {
    const tick = f.i * 20 / CFG.fps, dt = tick - lastTick; lastTick = tick;
    if (stage.clientHeight !== H || cv.width !== W || cv.height !== H) {      // страница превью fx подгоняет сцену под себя — держим 1280×720
      stage.style.setProperty('height', H + 'px', 'important'); stage.style.setProperty('max-height', 'none', 'important'); stage.style.setProperty('aspect-ratio', 'auto', 'important');
      renderer.setSize(W, H, false); cv.style.cssText = `display:block;width:${W}px;height:${H}px`;
    }
    cam.aspect = W / H; cam.fov = 30; cam.updateProjectionMatrix();
    const c = f.cam, yaw = c.yaw * D, pitch = c.pitch * D;      // камера: оси раскадровки (пиксели) → оси движка (блоки)
    const P = [c.tx + Math.sin(yaw) * Math.cos(pitch) * c.dist, c.ty + Math.sin(pitch) * c.dist, c.tz - Math.cos(yaw) * Math.cos(pitch) * c.dist];
    cam.position.copy(M(P.map(v => v / 16))); cam.lookAt(M([c.tx / 16, c.ty / 16, c.tz / 16]));
    cam.updateMatrixWorld(true);
    if (scene.fog) { scene.fog.near = Math.max(14, c.dist / 16 * 1.3); scene.fog.far = scene.fog.near + 40; }
    for (const k in cache) cache[k].holder.visible = false;
    const pos = {};
    let bossM = null;
    for (const a of f.actors) {
      const m = getModel(a);
      m.holder.visible = a.vis !== false;
      applyPose(m, a);
      if (m.dbl) m.dbl.quaternion.copy(m.bones.bipedHandRight.quaternion);
      m.holder.position.copy(M([(a.x || 0) / 16, (a.y || 0) / 16, (a.z || 0) / 16]));
      m.holder.rotation.set((a.rx || 0) * D, ((a.ry || 0) + 180) * D, (a.rz || 0) * D, 'YXZ');
      m.root.scale.setScalar((a.s || 1) / 16);
      if (m.item) m.item.visible = !a.noItem;
      if (CFG.boss === 'tyros' && a.k === 'boss') BL.flameFrame(m, Math.floor(tick));
      if (a.k === 'boss') bossM = m;
      if (a.stick && bossM && bossM.tip) {             // жертва на косе: грудь — на острие лезвия
        bossM.holder.updateMatrixWorld(true);
        const tip = bossM.tip.getWorldPosition(new THREE.Vector3());
        const want = tip.clone().add(new THREE.Vector3(0, -1.05 * (a.s || 1), 0));
        m.holder.position.lerp(want, a.stick);
      }
      if (a.id !== undefined) pos[a.id] = m.holder.position.clone();
    }
    for (const r of RUNS) {
      if (r.s === f.i) { setFig(r, pos); r.run = new FxRun(r.id, { caster: FIG.caster.clone(), points: {}, noTarget: true, noLift: true }); r.run.t0 = tick; caster.visible = false; }
      if (r.run && r.stop === f.i) r.run.stop(tick);
      if (r.run && r.e === f.i) { r.run.dispose(); r.run = null; }
    }
    let scr = 0, tintOp = 0, tintBg = null;
    for (const r of RUNS) if (r.run) {
      setFig(r, pos); r.run.update(tick, Math.max(0.01, dt));
      scr = Math.max(scr, +screenFlash.style.opacity || 0);
      const to = +tintLayer.style.opacity || 0; if (to > tintOp) { tintOp = to; tintBg = tintLayer.style.background; }
      tintLayer.style.opacity = 0;
    }
    screenFlash.style.opacity = String(scr * CFG.flashK); tintLayer.style.opacity = String(tintOp); if (tintBg) tintLayer.style.background = tintBg;
    renderer.render(scene, cam);
    cap.innerHTML = f.cap ? f.cap + (f.sub ? '<small>' + f.sub + '</small>' : '') : '';
    head.textContent = f.head || '';
    fade.style.opacity = f.fade || 0; flash.style.opacity = f.flash || 0;
  }
  return { init, render };
})();
</script>
"""

PAGE_CSS = """<style>
body{margin:0!important;padding:0!important;overflow:hidden;background:#000}
.wrap>*{display:none!important} .wrap>.main{display:block!important} .main>*{display:none!important}
.main>#stage{display:block!important;position:fixed!important;left:0;top:0;width:%dpx;height:%dpx;border:0!important;border-radius:0!important;z-index:5;margin:0}
#stage .hud,#stage .hint{display:none!important}
</style>""" % (W, H)

SCENE = {
    'tyros': dict(bg='#1c1210', fog=True, hemi=['#d8c8c0', '#281410', 0.8], dirs=[['#fff0e0', 0.7, [30, 60, -40]], ['#ff8040', 0.35, [-40, 20, 50]]],
                  g1='#3a2e28', g2='#342822'),
    'irina': dict(bg='#15101c', fog=False, hemi=['#eee6ff', '#2a1830', 0.85], dirs=[['#fff4ea', 0.6, [30, 60, -40]], ['#ff4050', 0.25, [-40, 20, 50]]],
                  g1='#2e2a36', g2='#282430'),
    'aris': dict(bg='#15191d', fog=True, hemi=['#dde6ee', '#20262a', 0.85], dirs=[['#ffffff', 0.65, [30, 60, -40]], ['#9fe8ff', 0.3, [-40, 20, 50]]],
                 g1='#33363a', g2='#2d3034'),
}


VICTIM = {'aris': 'pohsmp_aris_finisher_victim'}          # поза жертвы добивания (PlayerAnimator) по боссу


def victim_body_y(name, t):
    """Подъём/опускание тела жертвы (канал body.y эмоции, блоки) в момент t — в раскадровке его даёт координата y актёра."""
    p = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'irons_spellbooks', 'player_animation', name + '.json')
    ks = sorted((mv['tick'] / 20, mv['body'].get('y', 0)) for mv in json.load(open(p, encoding='utf-8'))['emote']['moves'] if 'body' in mv)
    if t <= ks[0][0]:
        return ks[0][1]
    for (t0, y0), (t1, y1) in zip(ks, ks[1:]):
        if t <= t1:
            return y0 + (y1 - y0) * ease_io((t - t0) / max(1e-6, t1 - t0))
    return ks[-1][1]


def build_page(boss, three, cfg):
    html = open(os.path.join(HERE, 'sigil_preview.template.html'), encoding='utf-8').read()
    html = html.replace('/*DATA*/null', json.dumps(sigil_data(), ensure_ascii=False), 1)
    if three:
        html = html.replace(CDN, 'file://' + os.path.abspath(three))
    html = '\n'.join(l for l in html.split('\n') if 'fonts.googleapis.com' not in l)
    html = html.replace('</head>', PAGE_CSS + '</head>', 1)
    js = ADAPTER.replace('VW', str(W)).replace('VH', str(H)).replace('VCFG', json.dumps(cfg, ensure_ascii=False))
    va = {'victim': victim_anim(VICTIM.get(boss, 'pohsmp_cult_finisher_victim'))}
    if boss == 'tyros':
        va.update(cult_hold_anims())
    js = js.replace('<script>', '<script>\nconst VANIMS = %s;\n' % json.dumps(va), 1)
    return html + '\n' + boss_lib(boss) + js


# ---------------------------------------------------------------- ролик
class Reel:
    def __init__(self, head):
        self.head, self.frames, self.marks, self.runs = head, [], [], []

    @property
    def t(self):
        return len(self.frames) / FPS

    def mark(self, text):
        self.marks.append((round(self.t, 1), text))

    def add(self, n, fn):
        for i in range(n):
            f = fn(i)
            f.setdefault('head', self.head)
            self.frames.append(f)

    def fx(self, fid, t, c=(0, 0, 0), tg=None, pts=None, stop=None, end=None, cId=None, tgId=None):
        """fx `fid` в момент t (с от начала ролика); c/tg/pts — в блоках (оси раскадровки); stop — Fx.stop (с); end — убрать (с)."""
        d = FXDEF[fid]['duration']
        if end is None:
            end = (stop if stop is not None else t + (d / 20 if d > 0 else 6.0)) + 1.5
        r = {'id': fid, 's': int(round(t * FPS)), 'e': int(round(end * FPS)), 'c': list(c)}
        if stop is not None:
            r['stop'] = int(round(stop * FPS))
        if tg is not None:
            r['tg'] = list(tg)
        if pts:
            r['pts'] = {k: list(v) for k, v in pts.items()}
        if cId is not None:
            r['cId'] = cId
        if tgId is not None:
            r['tgId'] = tgId
        self.runs.append(r)


def render(boss, reel, out, three, preload, crf=20):
    os.makedirs(OUT, exist_ok=True)
    sm = None
    for i, f in enumerate(reel.frames):
        f['i'] = i
        c = f['cam']                                   # плавная камера: смены плана сглаживаются, без рывков
        if sm is None:
            sm = dict(c)
        for key in ('dist', 'ty', 'tz', 'tx', 'pitch', 'yaw'):
            sm[key] += (c[key] - sm[key]) * 0.09
        f['cam'] = dict(c, **{key: sm[key] for key in ('dist', 'ty', 'tz', 'tx', 'pitch', 'yaw')}) if not f.get('rawcam') else c
    cfg = dict(SCENE[boss], boss=boss, fps=FPS, runs=reel.runs, preload=preload, steve=steve_entry(), flashK=0.6,
               scythe=scythe_item() if boss == 'tyros' else None)
    with tempfile.TemporaryDirectory() as td:
        hp = os.path.join(td, 'page.html')
        with open(hp, 'w', encoding='utf-8') as fh:
            fh.write(build_page(boss, three, cfg))
        jp = os.path.join(td, 'job.json')
        with open(jp, 'w', encoding='utf-8') as fh:
            json.dump({'html': hp, 'out': out, 'fps': FPS, 'w': W, 'h': H, 'crf': crf, 'frames': reel.frames}, fh, ensure_ascii=False)
        r = subprocess.run(['node', os.path.join(HERE, 'boss_video.js'), jp])
        if r.returncode:
            raise SystemExit('render failed: ' + out)
    mb = os.path.getsize(out) / 1e6
    print('wrote %s (%.1f с, %.1f МБ)' % (os.path.relpath(out, ROOT), reel.t, mb))
    return mb


def gif(mp4, out):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', mp4, '-vf',
                    'fps=15,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160[p];[b][p]paletteuse=dither=bayer:bayer_scale=4',
                    out], check=True)
    print('wrote %s (%.1f МБ)' % (os.path.relpath(out, ROOT), os.path.getsize(out) / 1e6))


def steve(x, z, **kw):
    """Игрок-цель в (x, z) блоков, лицом к боссу."""
    a = {'k': 'steve', 'anim': None, 't': 0, 's': 0.9375, 'x': x * B, 'z': z * B, 'ry': 180}
    a.update(kw)
    return a


# ---------------------------------------------------------------- общая раскадровка
class Boss:
    key = ''
    title = ''
    s = 1.0
    h = 40
    idle = None
    yaw0 = 32

    def anim_len(self, name):
        return self.anims[name]['animation_length']

    def boss(self, anim, t, **kw):
        a = {'k': 'boss', 'anim': anim, 't': t, 's': self.s, 'id': 0}
        a.update(kw)
        return a

    def idle_actor(self, t, **kw):
        return self.boss(self.idle, t % self.anim_len(self.idle) if self.idle else 0, **kw)

    def cam(self, t, zoom=1.0, ty=None, yaw=None, dz=0.0, pitch=7, dx=0.0):
        y = (self.yaw0 if yaw is None else yaw) + 7 * math.sin(2 * math.pi * t / 18)
        return {'yaw': y, 'pitch': pitch, 'dist': 3.0 * self.h * zoom, 'tx': dx, 'ty': self.h * 0.52 if ty is None else ty, 'tz': dz, 'fov': 30}

    def turntable(self, dur=7.0):
        r = Reel(self.title + ' · поворот 360°')
        n = secs(dur)
        r.mark('0–%.0f с: поворот 360° в покое' % dur)
        r.add(n, lambda i: {'actors': [self.idle_actor(i / FPS, ry=-360 * i / n)],
                            'cam': dict(self.cam(0, zoom=1.0), yaw=self.yaw0), 'rawcam': True, 'cap': 'Покой', 'sub': self.idle or '(поза покоя)'})
        return r

    def sequence(self, r, items, zoom=1.0, pause=PAUSE, prev=None):
        """items: dict(anim, cap, dur?, t0?, kw?, kwf?(t), extra?(t, f), fx?[(t, id, kw)], camkw?, camf?(t), zoom?, others?(t)->[actors])"""
        for it in items:
            anim = it['anim']
            t0 = it.get('t0', 0)
            L = it.get('dur', self.anim_len(anim) - t0)
            z = it.get('zoom', zoom)
            nxt = self.actor_for(it, t0)
            if prev is not None and pause:
                np_ = secs(pause)
                r.add(np_, lambda i, prev=prev, nxt=nxt, z=z, it=it, t0=t0: {
                    'actors': [dict(prev, blend=dict(nxt, w=ease_io((i + 1) / np_)))] + (it['others'](t0) if it.get('others') else []),
                    'cam': self.cam(r.t, zoom=z, **it.get('camkw', {}))})
            r.mark('%s (`%s`)' % (it['cap'], anim))
            start = r.t
            for (ft, fid, kw) in it.get('fx', []):
                kw = dict(kw)
                for key in ('stop', 'end'):
                    if key in kw:
                        kw[key] = start + kw[key]
                r.fx(fid, start + ft, **kw)
            n = secs(L)

            def fr(i, it=it, t0=t0, z=z, anim=anim):
                t = t0 + i / FPS
                a = self.actor_for(it, t)
                f = {'actors': [a] + (it['others'](t) if it.get('others') else []), 'cam': self.cam(r.t, zoom=z, **it.get('camkw', {})),
                     'cap': it['cap'], 'sub': it.get('sub', anim)}
                if it.get('camf'):
                    f['cam'].update(it['camf'](t))
                if it.get('extra'):
                    it['extra'](t, f)
                return f
            r.add(n, fr)
            prev = self.actor_for(it, t0 + (n - 1) / FPS)
        return prev

    def actor_for(self, it, t):
        kw = dict(it.get('kw', {}))
        if it.get('kwf'):
            kw.update(it['kwf'](t))
        return self.boss(it['anim'], min(t, self.anim_len(it['anim'])) if it['anim'] else 0, **kw)

    def hold(self, r, actor, dur, cap=None, sub=None, zoom=1.0, others=None, **fx):
        r.add(secs(dur), lambda i: dict({'actors': [actor] + (others or []), 'cam': self.cam(r.t, zoom=zoom), 'cap': cap, 'sub': sub}, **fx))

    def blend_to(self, r, frm, to, dur=PAUSE, zoom=1.0, cap=None, others=None):
        n = secs(dur)
        r.add(n, lambda i: {'actors': [dict(frm, blend=dict(to, w=ease_io((i + 1) / n)))] + (others or []), 'cam': self.cam(r.t, zoom=zoom), 'cap': cap})


# ================================================================ T26: Тирос / Глава Культа
class Tyros(Boss):
    key, title = 't26', 'Тирос, Глава Культа Меллисто'
    s = 1.75
    h = 36 * 1.75
    idle = None

    def __init__(self):
        self.anims = json.load(open(os.path.join(A, 'animations', 'entity', 'cult_leader.animation.json'), encoding='utf-8'))['animations']
        self.anims.update(cult_hold_anims())
        self.idle = '~hold'

    def boss(self, anim, t, **kw):                    # вне анимаций — поза хвата (её держит код модели)
        return super().boss(anim or '~hold', t if anim else 0, **kw)

    def turntable(self, dur=7.0):
        r = super().turntable(dur)
        n = secs(2.8)
        r.mark('%.0f–%.1f с: ходьба (поза хвата, правая рука с косой не качается)' % (dur, dur + 2.8))
        r.add(n, lambda i: {'actors': [self.boss('~walk', (i / FPS) % self.anim_len('~walk'), ry=-35)],
                            'cam': dict(self.cam(0, zoom=1.0), yaw=self.yaw0), 'rawcam': True, 'cap': 'Ходьба',
                            'sub': 'поза хвата Тироса (FireBossModel Iron\'s) + шаг'})
        return r

    def combat(self):
        r = Reel(self.title + ' · бой')
        items = [
            dict(anim='scythe_backpedal', cap='Отскок назад с косой'),
            dict(anim='scythe_jump_combo', cap='Прыжок и комбо косой'),
            dict(anim='scythe_downslash_sideslash', cap='Удар сверху и боковой взмах'),
            dict(anim='scythe_horizontal_slash_spin', cap='Горизонтальный взмах с разворотом'),
            dict(anim='scythe_dagger_double_horizontal', cap='Двойной взмах: коса и кинжал'),
            dict(anim='summon_fiery_daggers', cap='Призыв огненных кинжалов'),
            dict(anim='fire_boss_acrobatic_dagger_throw', cap='Акробатический бросок кинжалов'),
            dict(anim='offhand_parry', cap='Парирование'),
            dict(anim='fire_boss_break_stance', cap='Слом стойки (оглушён)'),
        ]
        self.sequence(r, items, zoom=1.1)
        return r

    def special(self):
        r = Reel(self.title + ' · особые и новые заклинания')
        P = (0, 0, -9)                                   # центр арены (точка появления) — в 9 бл. перед боссом
        tgt = (-3.0, -6.0)                              # игрок-цель для новых приёмов
        dummy = lambda t: [steve(*tgt, id=1)]
        pil = [(tgt[0] + 2.4 * math.cos(a), 0, tgt[1] + 2.4 * math.sin(a)) for a in (0.3, 1.55, 2.8, 4.05, 5.3)]

        def wide(t):                                     # как в ТЗ: снизу вверх на печать (1.3–4.0), затем общий план с высоты
            if t < 1.3:
                return {}
            if t < 4.0:
                return {'yaw': 25, 'pitch': -32, 'dist': 34 * B, 'tx': 0, 'ty': 21 * B, 'tz': -9 * B}
            return {'yaw': 35, 'pitch': 38, 'dist': 64 * B, 'tx': 0, 'ty': 1 * B, 'tz': -9 * B}

        def sickle(t, f):                                # коса-бумеранг: z = 6(1 − cos 2πs), x = 4 sin 2πs (из cult_sickle_warn)
            if 1.0 <= t < 1.8:
                s = (t - 1.0) / 0.8
                f['actors'][0]['noItem'] = True
                f['actors'].append({'k': 'scythe', 's': 1.75 * 3, 'x': 4 * math.sin(2 * math.pi * s) * B, 'y': 1.7 * B,
                                    'z': -6 * (1 - math.cos(2 * math.pi * s)) * B, 'rx': 90, 'ry': -1440 * s})
        items = [
            dict(anim='charge_raised_hand', dur=3.0, cap='«Приговор Меллисто»', sub='charge_raised_hand + fx cult_leader_verdict (0–2 с предупреждение, 2 с — запрет)',
                 fx=[(0, 'cult_leader_verdict', {'end': 3.4})], zoom=2.4, camkw={'pitch': 22, 'ty': 40}),
            dict(anim='cult_leader_first_flame', dur=7.0, cap='«Первое Пламя»',
                 sub='cult_leader_first_flame + fx cult_first_flame: печать над ареной 1.6, столб 4.0, кольцо огня',
                 fx=[(0, 'cult_first_flame', {'pts': {'center': P}})], zoom=1.15, camf=wide),
            dict(anim='cult_leader_ash_dissolve', cap='«Пепел Меллисто»: рассыпается', sub='cult_leader_ash_dissolve + fx cult_ash_dissolve',
                 fx=[(0, 'cult_ash_dissolve', {}), (1.2, 'cult_ash_vortex', {'stop': 2.0})], zoom=1.4),
        ]
        last = self.sequence(r, items, zoom=1.15)
        r.mark('«Пепел Меллисто»: вихрь (босс скрыт, fx cult_ash_vortex), сжато до 0.8 с')
        self.hold(r, dict(last, vis=False), 0.8, cap='«Пепел Меллисто»: вихрь пепла', sub='fx cult_ash_vortex; босс скрыт', zoom=1.4)
        lineview = {'yaw': 150, 'pitch': 14, 'dist': 26 * B, 'tx': 0, 'ty': 2 * B, 'tz': -10 * B}
        items = [
            dict(anim='cult_leader_ash_reform', cap='«Пепел Меллисто»: собирается, линия разреза',
                 sub='cult_leader_ash_reform + fx cult_ash_reform, cult_ash_line (1.5 с)',
                 fx=[(0, 'cult_ash_reform', {}), (0, 'cult_ash_line', {})], camf=lambda t: lineview),
            dict(anim='cult_leader_ash_slash', dur=2.2, cap='«Пепел Меллисто»: разрез через арену', sub='cult_leader_ash_slash, удар 0.5 + fx cult_ash_slash',
                 fx=[(0.5, 'cult_ash_slash', {})], camf=lambda t: lineview),
        ]
        last = self.sequence(r, items, prev=None)
        r.mark('Ломает «Дезинтеграцию: Реплику» (fx disintegration_replica 2 с, затем `cult_leader_replica_break` + fx)')
        self.blend_to(r, last, self.boss(None, 0), dur=0.5, zoom=1.9)
        t_rep = r.t
        r.fx('disintegration_replica', t_rep, c=(0, 0, -6), tg=(0, 0, 0), stop=t_rep + 2.0 + 0.9, end=t_rep + 2.0 + 3.0)
        self.hold(r, self.boss(None, 0), 2.0, cap='На босса кастуют «Дезинтеграцию: Реплику»', sub='fx disintegration_replica', zoom=1.9)
        items = [
            dict(anim='cult_leader_replica_break', cap='Ломает «Реплику»: «Эта фальшивка на меня не сработает»',
                 sub='cult_leader_replica_break + fx: трещины, crush 0.9, косой 1.5', fx=[(0, 'cult_leader_replica_break', {})], zoom=1.9),
        ]
        last = self.sequence(r, items, prev=None)
        newv = {'zoom': 1.5, 'camkw': {'dz': -40, 'dx': -10}}
        items = [
            dict(anim='cult_leader_sickle_throw', dur=2.4, cap='Новое: «Огненный серп»', sub='cult_leader_sickle_throw: дуга 0–1 с, бросок 1.0, коса возвращается 1.8',
                 fx=[(0, 'cult_sickle_warn', {}), (1.8, 'cult_sickle_catch', {})], extra=sickle, others=dummy, **newv),
            dict(anim='cult_leader_ash_trail_dash', dur=2.4, cap='Новое: «Пепельный след»', sub='cult_leader_ash_trail_dash: полоса 0.5 с, рывок 0.5, след горит 4 с',
                 fx=[(0, 'cult_ash_trail_warn', {}), (0.5, 'cult_ash_trail_dash', {}), (0.5, 'cult_ash_trail', {})], others=dummy, **newv),
            dict(anim='cult_leader_brand', dur=4.0, cap='Новое: «Клеймо культа»', sub='cult_leader_brand: клеймо на игроке 0.55, взрыв r3 через 3 с',
                 fx=[(0.55, 'cult_brand', {'c': (tgt[0], 0, tgt[1])}), (3.55, 'cult_brand_explode', {'c': (tgt[0], 0, tgt[1])})], others=dummy, **newv),
            dict(anim='cult_leader_pillars', dur=3.2, cap='Новое: «Столпы пламени»', sub='cult_leader_pillars: круги 0.3 (1.5 с), столбы 1.8',
                 fx=[(0.3, 'cult_pillar_warn', {'c': p}) for p in pil] + [(1.8, 'cult_pillar', {'c': p}) for p in pil], others=dummy,
                 zoom=2.4, camkw={'dz': -60, 'dx': -30, 'pitch': 16}),
        ]
        self.blend_to(r, last, self.boss(items[0]['anim'], 0), zoom=1.5, others=dummy(0))
        self.sequence(r, items)
        return r

    def finale(self):
        r = Reel(self.title + ' · финал')
        L = self.anim_len('fire_boss_spawn')
        r.mark('Появление (`fire_boss_spawn` + fx cult_leader_intro, 8.75 с; 0–1.5 с босс скрыт)')
        r.fx('cult_leader_intro', 0)
        n = secs(L)
        r.add(n, lambda i: {'actors': [self.boss('fire_boss_spawn', i / FPS, vis=i / FPS >= 1.5)],
                            'cam': self.cam(r.t, zoom=1.6, dz=40, ty=self.h * 0.7), 'cap': 'Появление',
                            'sub': 'fire_boss_spawn + fx cult_leader_intro'})
        last = self.boss('fire_boss_spawn', L)
        L2 = self.anim_len('fire_boss_half_health_attack')
        self.blend_to(r, last, self.boss('fire_boss_half_health_attack', 0), zoom=1.3)
        r.mark('Переход в облик души (`fire_boss_half_health_attack`, 11.8 с; в конце fx cult_leader_phase3 и стена огня r28) → облик ×2.0125')
        t_p3 = r.t + L2 - 1.5
        r.fx('cult_leader_phase3', t_p3)
        r.fx('cult_leader_firewall', t_p3 + 1.5, end=t_p3 + 1.5 + 7.6)
        n = secs(L2)
        r.add(n, lambda i: {'actors': [self.boss('fire_boss_half_health_attack', i / FPS)], 'cam': self.cam(r.t, zoom=1.3 if i < n - 45 else 2.2),
                            'cap': 'Переход в облик души', 'sub': 'fire_boss_half_health_attack + fx cult_leader_phase3',
                            'flash': max(0.0, 1 - (n - i) / 10) * 0.8})
        soul = dict(self.boss('fire_boss_half_health_attack', L2, v='soul'), s=2.0125)
        nf = secs(0.5)
        r.add(nf, lambda i: {'actors': [soul], 'cam': self.cam(r.t, zoom=2.2), 'cap': 'Облик души',
                             'sub': 'cult_leader_soul_mode ×2.0125, стена огня r28 (fx cult_leader_firewall)', 'flash': 0.8 * (1 - (i + 1) / nf)})
        soul_idle = dict(self.boss(None, 0, v='soul'), s=2.0125)
        self.blend_to(r, soul, soul_idle, dur=0.6, zoom=2.2, cap='Облик души')
        self.hold(r, soul_idle, 1.4, cap='Облик души', sub='cult_leader_soul_mode ×2.0125, стена огня r28 (fx cult_leader_firewall)', zoom=2.2)
        r.mark('Смерть (`fire_boss_death` + fx cult_leader_death, ролик 3.5 с) + затемнение')
        self.blend_to(r, soul_idle, dict(self.boss('fire_boss_death', 0, v='soul'), s=2.0125), zoom=1.4)
        r.fx('cult_leader_death', r.t)
        for rr in r.runs:
            if rr['id'] == 'cult_leader_firewall':
                rr['stop'] = int(round((r.t + 52 / 20) * FPS))
        n = secs(4.2)
        r.add(n, lambda i: {'actors': [dict(self.boss('fire_boss_death', min(i / FPS, 8.0), v='soul'), s=2.0125)],
                            'cam': self.cam(r.t, zoom=1.4), 'cap': 'Смерть', 'sub': 'fire_boss_death (ролик 0–3.5 с) + fx cult_leader_death',
                            'fade': max(0.0, (i / FPS - 3.5) / 0.7)})
        r.add(secs(0.4), lambda i: {'actors': [], 'cam': self.cam(r.t), 'fade': 1})
        r.mark('Добивание (`cult_leader_finisher` + жертва `pohsmp_cult_finisher_victim` на косе + fx cult_leader_finisher)')
        L3 = self.anim_len('cult_leader_finisher')
        nf = secs(0.5)
        r.add(nf, lambda i: dict(self.finisher_frame(0, r.t), fade=1 - (i + 1) / nf))
        r.fx('cult_leader_finisher', r.t, tgId=1)
        n = secs(L3 + 0.9)
        r.add(n, lambda i: self.finisher_frame(i / FPS, r.t))
        return r

    def finisher_frame(self, t, rt):
        boss = self.boss('cult_leader_finisher', min(t, 2.4))
        z0, z1 = -5.0 * B, -3.0 * B
        z = z0 + (z1 - z0) * ease_in_quad(t / 0.7)
        y = 2.3 * B * ease_io((t - 1.0) / 0.7)
        sc = 0.9375 * (1 - ease_in_quad((t - 2.2) / 0.45)) if t > 2.2 else 0.9375
        victim = {'k': 'steve', 'anim': 'victim', 't': min(t, 2.4), 's': max(sc, 0.001), 'x': 0, 'y': y, 'z': z, 'ry': 180, 'vis': t < 2.3,
                  'stick': ease_io((t - 0.8) / 0.25), 'id': 1}
        cam = self.cam(rt, zoom=1.6, ty=self.h * 0.95, dz=-22, yaw=62)
        return {'actors': [boss, victim], 'cam': cam, 'cap': 'Добивание',
                'sub': ('cult_leader_finisher: тянет 0–0.7 · пронзает 1.0 · поднимает на косе · пепел 2.2' if t < 2.2
                        else 'cult_leader_finisher: 2.2 — жертва сгорает в пепел')}


# ================================================================ T27: Ирина
class Irina(Boss):
    key, title = 't27', 'Ирина, Ведьма Ревности'
    s = 1.0
    h = 54
    idle = 'irina_idle'
    PA, PB = (-3.0, -5.5), (2.0, -6.5)                 # два игрока перед Ириной (блоки)
    SIDE = {'dz': -50, 'yaw': 78, 'pitch': 12}         # сбоку: Ирина и игроки рядом в кадре

    def __init__(self):
        self.anims = json.load(open(os.path.join(A, 'animations', 'entity', 'irina.animation.json'), encoding='utf-8'))['animations']

    def boss(self, anim, t, **kw):
        kw.setdefault('cloth', 'irina_cloth_storm' if anim not in (None, 'irina_idle', 'irina_walk') else
                      ('irina_cloth_walk' if anim == 'irina_walk' else 'irina_cloth_idle'))
        kw.setdefault('tc', t)
        return super().boss(anim, t, **kw)

    def pair(self, t=0, swap=None):
        a, b = self.PA, self.PB
        if swap is not None and t >= swap:
            a, b = b, a
        return [steve(*a, id=1), steve(*b, id=2)]

    def combat(self):
        r = Reel(self.title + ' · бой')
        pa, pb = self.PA, self.PB
        v = {'others': lambda t: self.pair(), 'zoom': 2.0, 'camkw': self.SIDE}
        items = [
            dict(anim='irina_staff_attack', cap='Удар крюком посоха сверху', **v),
            dict(anim='irina_staff_sweep', cap='Взмах посохом по кругу', **v),
            dict(anim='irina_cast_short', cap='Короткий каст', **v),
            dict(anim='irina_cast_long', dur=2.0, cap='Длинный каст (цикл)', **v),
            dict(anim='irina_cast_long_end', cap='Длинный каст — завершение', **v),
            dict(anim='irina_mark', dur=2.2, cap='«Предмет ревности» — метка', sub='irina_mark 0.7 + fx irina_mark_apply → irina_mark',
                 fx=[(0.7, 'irina_mark_apply', {'c': (pa[0], 0, pa[1])}), (1.9, 'irina_mark', {'c': (pa[0], 0, pa[1]), 'stop': 2.2, 'end': 2.3})], **v),
            dict(anim='irina_bind', dur=2.4, cap='Связать пары (фаза 2)', sub='irina_bind 0.9 + fx irina_bond_1 на обоих',
                 fx=[(0.9, 'irina_bond_1', {'c': (pa[0], 0, pa[1]), 'stop': 2.4, 'end': 2.5}),
                     (0.9, 'irina_bond_1', {'c': (pb[0], 0, pb[1]), 'stop': 2.4, 'end': 2.5})], **v),
            dict(anim='irina_whip', dur=1.6, cap='Хлёст нитей (фаза 3)', sub='fx irina_whip_warn → irina_whip на 0.45',
                 fx=[(0, 'irina_whip_warn', {}), (0.45, 'irina_whip', {})], **v),
            dict(anim='irina_steal', dur=2.2, cap='Кража эффектов', sub='irina_steal + fx irina_steal_lose (игроки) и irina_steal_gather (Ирина)',
                 fx=[(0.3, 'irina_steal_lose', {'c': (pa[0], 0, pa[1])}), (0.3, 'irina_steal_lose', {'c': (pb[0], 0, pb[1])}),
                     (0.3, 'irina_steal_gather', {})], **v),
        ]
        self.sequence(r, items)
        return r

    def special(self):
        r = Reel(self.title + ' · особые и новые заклинания')
        pa, pb = self.PA, self.PB
        two = lambda t: self.pair()
        v = {'others': two, 'zoom': 2.0, 'camkw': self.SIDE}
        Z0, Z1 = -6.0, -1.8                              # жертва «Только мой»: рывком из 6 бл. к Ирине (1.0 с)

        def victim(t):
            z = Z0 + (Z1 - Z0) * ease_in_quad((t - 0.9) / 0.15)
            return [steve(pa[0], pa[1]), steve(0, z, id=1)]
        knots = [(-3, -3), (3, -4), (-1, -7), (4, -8), (-5, -7)]
        items = [
            dict(anim='irina_others_happiness', dur=6.4, cap='«Чужое счастье»',
                 sub='irina_others_happiness + fx: печать r24, искры над ней 1.4, воронка 3.6, поглощение 5.2',
                 fx=[(0, 'irina_others_happiness', {})], others=two, zoom=1.25,
                 camf=lambda t: {} if t < 0.8 else {'yaw': 30, 'pitch': 24, 'dist': 52 * B, 'tx': 0, 'ty': 2 * B, 'tz': -2 * B}),
            dict(anim='irina_only_mine', cap='«Только мой»', sub='irina_only_mine: рывок 1.0, кокон 1.6–5.4 (fx irina_yank, irina_cocoon), раздавлен 5.4',
                 kw={'cloth': 'irina_cloth_cocoon'}, others=victim, zoom=1.7, camkw={'dz': -30, 'yaw': 78, 'pitch': 10},
                 fx=[(0, 'irina_only_mine', {}), (1.0, 'irina_yank', {'c': (0, 0, Z0)}), (1.05, 'irina_yank', {'c': (0, 0, Z1)}),
                     (1.6, 'irina_cocoon', {'c': (0, 0, Z1)}), (5.4, 'irina_cocoon_crush', {'c': (0, 0, Z1)})]),
            dict(anim='irina_only_mine_broken', dur=1.6, cap='«Только мой»: кокон разорван (вариант)', sub='irina_only_mine_broken + fx irina_cocoon_break',
                 fx=[(0, 'irina_cocoon_break', {'c': (0, 0, Z1)})], others=lambda t: [steve(pa[0], pa[1]), steve(0, Z1)], zoom=1.7, camkw={'dz': -30, 'yaw': 78, 'pitch': 10}),
            dict(anim='irina_phase2', cap='Переход в фазу 2', sub='irina_phase2 + fx irina_phase2', fx=[(0, 'irina_phase2', {})], zoom=1.2),
            dict(anim='irina_phase3', cap='Переход в фазу 3', sub='irina_phase3 + fx irina_phase3', fx=[(0, 'irina_phase3', {})], zoom=1.2),
            dict(anim='irina_gaze', dur=2.4, cap='Новое: «Ревнивый взгляд»', sub='irina_gaze 0.5: око и нить на смотревших (fx irina_gaze_cast, irina_gaze_mark)',
                 fx=[(0, 'irina_gaze_cast', {}), (0.5, 'irina_gaze_mark', {'c': (pa[0], 0, pa[1])}), (0.5, 'irina_gaze_mark', {'c': (pb[0], 0, pb[1])})], **v),
            dict(anim='irina_knots', dur=2.6, cap='Новое: «Узлы»', sub='irina_knots 0.9: узлы-ловушки на земле (fx irina_knots_cast, irina_knot_trap)',
                 fx=[(0, 'irina_knots_cast', {})] + [(0.9 + 0.05 * i, 'irina_knot_trap', {'c': (x, 0, z), 'stop': 2.6, 'end': 2.7})
                                                      for i, (x, z) in enumerate(knots)],
                 others=two, zoom=2.6, camkw={'dz': -60, 'yaw': 70, 'pitch': 22}),
            dict(anim='irina_swap', dur=2.0, cap='Новое: «Подмена любимого»', sub='irina_swap 0.8: двое меняются местами (fx irina_swap в обеих точках)',
                 fx=[(0.8, 'irina_swap', {'c': (pa[0], 0, pa[1])}), (0.8, 'irina_swap', {'c': (pb[0], 0, pb[1])})],
                 others=lambda t: self.pair(t, swap=0.8), zoom=2.0, camkw=self.SIDE),
            dict(anim='irina_puppet', cap='Новое: «Марионетка»', sub='irina_puppet 0.7: крестовина и нити над игроком (fx irina_puppet)',
                 fx=[(0.7, 'irina_puppet', {'c': (pa[0], 0, pa[1])})], **v),
            dict(anim='irina_puppet_hold', dur=2.0, cap='Новое: «Марионетка» — удержание', sub='irina_puppet_hold (цикл)', **v),
        ]
        self.sequence(r, items)
        return r

    def finale(self):
        r = Reel(self.title + ' · финал')
        r.mark('Появление (`irina_spawn` + `irina_cloth_spawn` + fx irina_intro, 7 с)')
        r.fx('irina_intro', 0)
        L = self.anim_len('irina_spawn')
        r.add(secs(L), lambda i: {'actors': [self.boss('irina_spawn', i / FPS, cloth='irina_cloth_spawn')], 'cam': self.cam(r.t, zoom=1.15),
                                  'cap': 'Появление', 'sub': 'irina_spawn + irina_cloth_spawn + fx irina_intro'})
        last = self.boss('irina_spawn', L, cloth='irina_cloth_spawn')
        self.blend_to(r, last, self.idle_actor(0), zoom=1.15)
        self.hold(r, self.idle_actor(0), 0.4, zoom=1.15)
        nf = secs(0.4)
        r.add(nf, lambda i: {'actors': [self.idle_actor(0)], 'cam': self.cam(r.t, zoom=1.15), 'fade': (i + 1) / nf})
        r.mark('Добивание (`irina_finisher` + жертва + fx irina_finisher)')
        r.add(nf, lambda i: dict(self.finisher_frame(0, r.t), fade=1 - (i + 1) / nf))
        r.fx('irina_finisher', r.t, tgId=1)
        r.add(secs(2.6 + 0.9), lambda i: self.finisher_frame(i / FPS, r.t))
        r.add(nf, lambda i: dict(self.finisher_frame(3.5, r.t), fade=(i + 1) / nf))
        r.mark('Смерть (`irina_death` + `irina_cloth_death` + fx irina_death, 5 с)')
        L = self.anim_len('irina_death')
        r.add(nf, lambda i: {'actors': [self.boss('irina_death', 0, cloth='irina_cloth_death')], 'cam': self.cam(r.t, zoom=1.15),
                             'fade': 1 - (i + 1) / nf, 'cap': 'Смерть'})
        r.fx('irina_death', r.t)
        n = secs(L + 0.6)
        r.add(n, lambda i: {'actors': [self.boss('irina_death', min(i / FPS, L), cloth='irina_cloth_death')], 'cam': self.cam(r.t, zoom=1.15),
                            'cap': 'Смерть', 'sub': 'irina_death + irina_cloth_death + fx irina_death', 'fade': max(0.0, (i / FPS - L) / 0.6)})
        return r

    def finisher_frame(self, t, rt):
        boss = self.boss('irina_finisher', min(t, 2.6))
        z = -3.6 * B + (3.6 - 1.6) * B * ease_in_quad(t / 0.8)
        fall = ease_io((t - 2.2) / 0.5)
        victim = {'k': 'steve', 'anim': 'victim', 't': min(t, 1.7), 's': 0.9375, 'x': 0, 'y': 0, 'z': z - fall * 4, 'ry': 180, 'rx': -88 * fall, 'id': 1}
        return {'actors': [boss, victim], 'cam': self.cam(rt, zoom=1.0, ty=self.h * 0.45, dz=-14, yaw=55), 'cap': 'Добивание',
                'sub': 'irina_finisher: нити 0.2 · притянута 0.8 · крюк 1.3 · шёпот 1.7 · смерть 2.2'}


# ================================================================ T28: Арис
class Aris(Boss):
    key, title = 't28', 'Арис, Мифический Кузнец'
    s = 1.0             # письмо T28: масштаб рендера 1.0–1.15 — снято в 1.0
    h = 46
    idle = 'animation.aris.idle'

    def __init__(self):
        self.anims = json.load(open(os.path.join(A, 'animations', 'entity', 'aris.animation.json'), encoding='utf-8'))['animations']

    def combat(self):
        r = Reel(self.title + ' · бой')
        P = 'animation.aris.'
        ring = [(2 * math.cos(j * 2.094 + 0.5), 3, 2 * math.sin(j * 2.094 + 0.5)) for j in range(3)]
        items = [
            dict(anim=P + 'walk', dur=2.4, cap='Тяжёлый шаг, молот на плече', sub='walk (2 цикла)'),
            dict(anim=P + 'slam', dur=2.2, cap='Удар молотом по земле', sub='slam, удар 0.75 + fx aris_slam (волна металла r8)',
                 fx=[(0.75, 'aris_slam', {'c': (0, 0, -1.35)})], zoom=1.6),
            dict(anim=P + 'swing', dur=2.2, cap='Горизонтальный размах', sub='swing, удар 0.62 + fx aris_metal_wave (5 гребней вперёд)',
                 fx=[(0.62, 'aris_metal_wave', {})], zoom=1.7, camkw={'dz': -60}),
            dict(anim=P + 'cast', dur=3.2, cap='Каст: наковальня', sub='cast 0.8 + fx aris_anvil_rise (меш aris_anvil) → aris_anvil_break',
                 fx=[(0.8, 'aris_anvil_rise', {'c': (1.5, 0, -3.5), 'stop': 2.7, 'end': 2.75}), (2.7, 'aris_anvil_break', {'c': (1.5, 0, -3.5)})],
                 zoom=1.4, camkw={'dz': -20}),
            dict(anim=P + 'cast', dur=3.0, cap='Каст: клинки', sub='cast 0.8 + fx aris_blades_forge (+3 бл.), клинки aris_blade_sword / glaive на кольце r2',
                 fx=[(0.8, 'aris_blades_forge', {'c': (0, 3, 0)})] +
                    [(0.8 + k / 20, 'aris_blade_sword' if j % 2 == 0 else 'aris_blade_glaive', {'c': ring[j], 'stop': 3.0, 'end': 3.05})
                     for j, k in enumerate((20, 26, 32))],
                 zoom=1.5, camkw={'ty': 46 * 0.8}),
        ]
        self.sequence(r, items, zoom=1.1)
        return r

    def special(self):
        r = Reel(self.title + ' · особые и новые заклинания')
        P = 'animation.aris.'
        tgt = (-2.5, -6.0)
        dummy = lambda t: [steve(*tgt)]

        def mythic(t):
            return {'v': 'mythic' if t >= 1.6 else 'base'}

        def billet(t, f):                                 # слиток летит из левой руки с 0.7 с (снаряд кода с мешем aris_billet)
            if 0.7 <= t < 1.4:
                k = (t - 0.7) / 0.7
                f['actors'].append({'k': 'mesh:aris_billet', 's': 1.0, 'x': -0.45 * B, 'y': (1.4 + 2.2 * k - 3.6 * k * k) * B, 'z': -(0.8 + 6.2 * k) * B,
                                    'rx': 400 * k})
        isl = [(6 * math.cos(a), 0, 6 * math.sin(a)) for a in (0.4, 1.6, 2.8, 4.0, 5.2)]

        def lb_view(t):
            return {} if t < 1.4 else {'yaw': 75, 'pitch': 6, 'dist': 1250, 'tx': 0, 'ty': 19 * B, 'tz': -7 * B}
        items = [
            dict(anim=P + 'phase2', cap='Переход в фазу 2', sub='phase2, удар 1.0 + fx aris_phase2', fx=[(0, 'aris_phase2', {})], zoom=1.3),
            dict(anim=P + 'phase3', cap='Переход в фазу 3: броня раскаляется', sub='phase3: 1.6 — текстура aris_mythic + fx aris_phase3', kwf=mythic,
                 fx=[(0, 'aris_phase3', {})], zoom=1.3),
            dict(anim=P + 'forge', dur=6.0, cap='Особое: «Горн»', sub='forge: удары 1.0/1.8/2.6, пол вспыхивает 3.3 (fx aris_forge, островки aris_island)',
                 kw={'v': 'mythic'}, fx=[(0.3, 'aris_forge', {'end': 6.0})] + [(0.3, 'aris_island', {'c': p, 'end': 6.0}) for p in isl],
                 camf=lambda t: {} if t < 1.0 else {'yaw': 35, 'pitch': 30, 'dist': 34 * B, 'tx': 0, 'ty': 1 * B, 'tz': 0}),
            dict(anim=P + 'last_blow', cap='Особое: «Последний удар молота»',
                 sub='last_blow + fx aris_last_blow: прицел r14, исполинский молот рушится 3.5–4.0, удар 4.0',
                 kw={'v': 'mythic'}, fx=[(0, 'aris_last_blow', {'c': (0, 0, -14)})], zoom=1.15, camf=lb_view),
            dict(anim=P + 'billet', dur=4.6, cap='Новое: «Раскалённая заготовка»',
                 sub='billet: бросок 0.7 (aris_billet_throw), слиток лежит 3 с (aris_billet), взрыв r3',
                 fx=[(0.7, 'aris_billet_throw', {}), (1.4, 'aris_billet', {'c': (-0.45, 0, -7)}), (4.4, 'aris_billet_explode', {'c': (-0.45, 0, -7)})],
                 extra=billet, zoom=1.6, camkw={'dz': -50}),
            dict(anim=P + 'chains', dur=2.8, cap='Новое: «Цепи кузни»', sub='chains 0.8: четыре цепи из земли к игроку (fx aris_chains)',
                 fx=[(0.8, 'aris_chains', {'c': (tgt[0], 0, tgt[1]), 'stop': 2.8, 'end': 2.85})], others=dummy, zoom=1.5, camkw={'dz': -40, 'dx': -10}),
            dict(anim=P + 'quench', dur=3.0, cap='Новое: «Закалка»', sub='quench 0.8: всплеск и пар r5 (fx aris_quench)', fx=[(0.8, 'aris_quench', {'end': 3.0})],
                 zoom=1.5),
            dict(anim=P + 'bellows', dur=2.4, cap='Новое: «Мехи»', sub='bellows: конус 0–0.8 (aris_bellows_warn), поток жара 0.8 (aris_bellows)',
                 fx=[(0, 'aris_bellows_warn', {}), (0.8, 'aris_bellows', {})], zoom=1.6, camkw={'dz': -50, 'pitch': 14}),
        ]
        self.sequence(r, items, zoom=1.1)
        return r

    def finale(self):
        r = Reel(self.title + ' · финал')
        P = 'animation.aris.'

        def spawn_v(t):
            return 'spent' if t < 4.5 else ('dim' if t < 6.0 else 'base')
        L = self.anim_len(P + 'spawn')
        r.mark('Появление (`spawn` + fx aris_intro, 9 с; текстура spent → dim 4.5 → aris 6.0)')
        r.fx('aris_intro', 0)
        r.add(secs(L), lambda i: {'actors': [self.boss(P + 'spawn', i / FPS, v=spawn_v(i / FPS))], 'cam': self.cam(r.t, zoom=1.35),
                                  'cap': 'Появление', 'sub': 'spawn + fx aris_intro · рога: погасли → тлеют 4.5 → горят 6.0'})
        last = self.boss(P + 'spawn', L, v='base')
        TAB = [(1.2, 'base'), (2.0, 'dim'), (2.15, 'base'), (2.25, 'dim'), (2.45, 'base'), (2.5, 'dim'), (2.6, 'spent')]

        def sur_v(t):
            v = 'base'                                   # до 1.2 — «текущая»; после появления это aris
            for tt, vv in TAB:
                if t >= tt:
                    v = vv
            return v
        self.blend_to(r, last, self.boss(P + 'surrender', 0, v='base'), dur=0.5, zoom=1.15)
        L = self.anim_len(P + 'surrender')
        r.mark('Сдача (`surrender` + fx aris_surrender, 5 с: на колено 1.2, рога/глаза гаснут 2.0–2.6, молот падает 3.2, фраза 3.6)')
        r.fx('aris_surrender', r.t)
        r.add(secs(L + 0.7), lambda i: {'actors': [self.boss(P + 'surrender', min(i / FPS, L), v=sur_v(i / FPS))], 'cam': self.cam(r.t, zoom=1.15),
                                        'cap': 'Сдача' if i / FPS < 3.6 else '«Чёрт! Я сдаюсь, прекращайте...я помогу вам..»',
                                        'sub': 'surrender + fx aris_surrender · рога и глаза гаснут 2.0–2.6 · молот падает 3.2'})
        last = self.boss(P + 'surrender', L, v='spent')
        nf = secs(0.5)
        r.add(nf, lambda i: {'actors': [last], 'cam': self.cam(r.t, zoom=1.15), 'fade': (i + 1) / nf})
        r.mark('Мирный NPC: `npc_stand` (aris_dim), затем `npc_sit`')
        r.add(nf, lambda i: {'actors': [self.boss(P + 'npc_stand', 0, v='dim')], 'cam': self.cam(r.t, zoom=1.15), 'fade': 1 - (i + 1) / nf,
                             'cap': 'Мирный NPC: стоит у молота'})
        r.add(secs(4.0), lambda i: {'actors': [self.boss(P + 'npc_stand', i / FPS, v='dim')], 'cam': self.cam(r.t, zoom=1.15),
                                    'cap': 'Мирный NPC: стоит у молота', 'sub': 'npc_stand (текстура aris_dim)'})
        self.blend_to(r, self.boss(P + 'npc_stand', 4.0 - 1 / FPS, v='dim'), self.boss(P + 'npc_sit', 0, v='dim'), dur=0.5, zoom=1.15)
        r.add(secs(4.0), lambda i: {'actors': [self.boss(P + 'npc_sit', i / FPS, v='dim')], 'cam': self.cam(r.t, zoom=1.15),
                                    'cap': 'Мирный NPC: сидит на молоте', 'sub': 'npc_sit (текстура aris_dim)'})
        sit = self.boss(P + 'npc_sit', 4.0, v='dim')
        r.add(nf, lambda i: {'actors': [sit], 'cam': self.cam(r.t, zoom=1.15), 'fade': (i + 1) / nf})
        r.mark('Добивание (`finisher` + жертва `pohsmp_aris_finisher_victim` + fx aris_finisher: pull 0, windup 0.7, slam 1.5, kill 2.2)')
        r.add(nf, lambda i: dict(self.finisher_frame(0, r.t), fade=1 - (i + 1) / nf))
        r.fx('aris_finisher', r.t, tgId=1)
        r.add(secs(2.4 + 1.2), lambda i: self.finisher_frame(i / FPS, r.t))
        return r

    FIN_DIST = 1.9                                        # = ArisMath.FINISHER_DIST

    def finisher_frame(self, t, rt):
        boss = self.boss('animation.aris.finisher', min(t, 2.4))
        z = -(3.4 - (3.4 - self.FIN_DIST) * ease_io(t / 0.7)) * B
        y = victim_body_y('pohsmp_aris_finisher_victim', min(t, 2.4)) * B * 0.9375
        victim = {'k': 'steve', 'anim': 'victim', 't': min(t, 2.4), 's': 0.9375, 'x': 0, 'y': y, 'z': z, 'ry': 0, 'id': 1}   # лицом к Арис
        cam = self.cam(rt, zoom=1.0, ty=self.h * 0.42, dz=-16, yaw=68, pitch=12)
        sub = ('finisher: тянет 0–0.7 (pull) · замах 0.7 (windup) · молот в спину 1.5 (slam) · смерть 2.2 (kill)' if t < 2.2
               else 'finisher: 2.2 — kill (смерть «%1$s перекована Арис, Мифическим Кузнецом»)')
        return {'actors': [boss, victim], 'cam': cam, 'cap': 'Добивание', 'sub': sub,
                'flash': 0.25 * max(0.0, 1 - abs(t - 1.5) / 0.1)}


BOSSES = {'t26': (Tyros, 'tyros', [{'k': 'boss'}, {'k': 'boss', 'v': 'soul'}, {'k': 'steve'}, {'k': 'scythe'}]),
          't27': (Irina, 'irina', [{'k': 'boss'}, {'k': 'steve'}]),
          't28': (Aris, 'aris', [{'k': 'boss', 'v': v} for v in ('base', 'dim', 'spent', 'mythic')] + [{'k': 'steve'}, {'k': 'mesh:aris_billet'}])}


def main():
    args = sys.argv[1:]
    three = args[args.index('--three') + 1] if '--three' in args else None
    only = args[args.index('--only') + 1].split(',') if '--only' in args else ['turntable', 'combat', 'special', 'finale']
    keys = [a for a in args if a in BOSSES] or list(BOSSES)
    marks = {}
    for k in keys:
        cls, name, pre = BOSSES[k]
        b = cls()
        for what in only:
            reel = getattr(b, what)()
            out = os.path.join(OUT, '%s_%s.mp4' % (k, what))
            mb = render(name, reel, out, three, pre)
            if mb > 15:
                render(name, reel, out, three, pre, crf=26)
            marks['%s_%s' % (k, what)] = {'dur': round(reel.t, 1), 'marks': reel.marks}
            if what == 'turntable':
                gif(out, os.path.join(OUT, '%s_turntable.gif' % k))
    mp = os.path.join(OUT, 'marks.json')
    old = json.load(open(mp, encoding='utf-8')) if os.path.exists(mp) else {}
    old.update(marks)
    json.dump(old, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
