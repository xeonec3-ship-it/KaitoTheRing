#!/usr/bin/env python3
"""
Кадр-лист «хват косы»: Тирос Iron's (эталон) / Глава Культа было / Глава Культа стало (владелец 21.11: «держит косу как Тирос, везде»).
Рисует как в игре: GeckoLib 4.8.4 поворачивает предмет кистью ДВАЖДЫ (BlockAndItemGeoLayer.renderForBone) — здесь тоже.
  * Тирос: tyros.geo.json + текстура Iron's, коса hellrazor (спрайт 48×48 → бруски, как item/generated, template_verylarge_sword),
    анимации casting_animations.json из jar как есть; вне анимаций — FireBossModel: рука (−30, −30, 10), кисть (−5, 0, −48) в осях модели,
    шаг — AbstractSpellCastingMobModel (у FireBossModel правая рука качается на 0.25 от базовой).
  * Глава было: файл анимаций и поза «несёт косу» (рука −25, 10, 15 / кисть 0, −5.5, 96 в осях анимаций) из коммита BASE.
  * Глава стало: текущие assets + поза хвата Тироса (CultMath.HOLD_*, сдвиг косы 3 px вдоль древка, рука с косой не качается).
На земле — красная стрелка «вперёд» (куда смотрит босс), жёлтый след острия за 0.15 с до кадра (конус — куда оно идёт).
  python3 tools/t26_hold_sheet.py [out.jpg] [--base e0ab4cf] [--three путь/three.min.js]
Нужно: jar Iron's в libs/ (python3 tools/fetch_libs.py), Playwright + Chromium.
"""
import json
import math
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import boss_video as BV  # noqa: E402
import cult_leader_render as CR  # noqa: E402

BASE = 'e0ab4cf'                       # последний коммит с позой «несёт косу» (до правки 21.11)
ANIM = 'src/main/resources/assets/pohsmp_core/animations/entity/cult_leader.animation.json'
OLD_ARM, OLD_HAND = [-25, 10, 15], [0, -5.5, 96]
IRON_ARM, IRON_HAND = [30, 30, 10], [5, 0, -48]          # FireBossModel (−30, −30, 10) / (−5, 0, −48) в осях модели → оси анимаций


def hellrazor_item():
    """hellrazor: item/generated из текстуры 48×48 (1 пиксель = 1/3 ед.), толщина 1 ед. (z 7.5…8.5); display — template_verylarge_sword."""
    from PIL import Image
    import io
    with zipfile.ZipFile(CR.JAR) as z:
        im = Image.open(io.BytesIO(z.read('assets/irons_spellbooks/textures/item/hellrazor.png'))).convert('RGBA')
        disp = json.loads(z.read('assets/irons_spellbooks/models/item/template_verylarge_sword.json'))['display']
    w, h = im.size
    k = 16 / w
    els, tip = [], None
    for y in range(h):
        for x in range(w):
            r, g, b, a = im.getpixel((x, y))
            if a < 128:
                continue
            c = '#%02x%02x%02x' % (r, g, b)
            els.append([[x * k, 16 - (y + 1) * k, 7.5], [(x + 1) * k, 16 - y * k, 8.5], None, {f: c for f in ('north', 'south', 'east', 'west', 'up', 'down')}])
            if y < h * 0.45 and (tip is None or x < tip[0]):          # остриё — самый левый пиксель лезвия (верхняя часть)
                tip = (x, y)
    return {'els': els, 'display': disp, 'tip': [(tip[0] + 0.5) * k, 16 - (tip[1] + 0.5) * k, 8.0]}


def walk_anim(arm, hand, pos, x, arm_net, L=0.94):
    """Ходьба вне анимаций: ноги ±cos·1.4·x·0.75, левая рука cos·x, правая (с косой) — поза хвата + arm_net·cos(+π)·x (оси анимаций)."""
    R = 180 / math.pi
    ch = {b: {} for b in ('right_leg', 'left_leg', 'left_arm', 'right_arm', 'body')}
    for i in range(int(L / 0.02) + 1):
        t = round(i * 0.02, 3)
        y = t / L * 2 * (2 * math.pi / 0.6662)
        c = math.cos(y * 0.6662)
        kk = '%.4g' % t if t else '0.0'
        ch['right_leg'][kk] = {'vector': [round(-c * 1.4 * x * 0.75 * R, 2), 0, 0]}
        ch['left_leg'][kk] = {'vector': [round(c * 1.4 * x * 0.75 * R, 2), 0, 0]}
        ch['left_arm'][kk] = {'vector': [round(-c * x * R, 2), 0, 0]}
        ch['right_arm'][kk] = {'vector': [round(arm[0] - arm_net * math.cos(y * 0.6662 + math.pi) * x * R, 2), arm[1], arm[2]]}
        ch['body'][kk] = {'vector': [0, round(abs(math.cos((y * 1.2662 - math.pi / 2) * 0.5)) * 2 * 0.75 * x, 3), 0]}
    bones = {b: {'rotation': v} for b, v in ch.items() if b != 'body'}
    bones['body'] = {'position': ch['body']}
    bones['bipedHandRight'] = {'rotation': {'0.0': {'vector': hand}}}
    if pos:
        bones['bipedHandRight']['position'] = {'0.0': {'vector': pos}}
    return {'animation_length': L, 'loop': True, 'bones': bones}


def hold_anim(arm, hand, pos=None):
    b = {'right_arm': {'rotation': {'0.0': {'vector': arm}}}, 'bipedHandRight': {'rotation': {'0.0': {'vector': hand}}}}
    if pos:
        b['bipedHandRight']['position'] = {'0.0': {'vector': pos}}
    return {'animation_length': 1.0, 'bones': b}


def data(base):
    from gen_cult_leader_extra import CARRY_ARM, CARRY_HAND, CARRY_POS
    with zipfile.ZipFile(CR.JAR) as z:
        iron = json.loads(z.read('assets/irons_spellbooks/animations/casting_animations.json'))['animations']
    old = json.loads(subprocess.run(['git', 'show', '%s:%s' % (base, ANIM)], cwd=ROOT, capture_output=True, check=True).stdout)['animations']
    new = json.load(open(os.path.join(ROOT, ANIM), encoding='utf-8'))['animations']
    an = {}
    for pre, src in (('iron:', iron), ('old:', old), ('new:', new)):
        for k, v in src.items():
            an[pre + k] = v
    an['iron:~hold'] = hold_anim(IRON_ARM, IRON_HAND)
    an['iron:~walk'] = walk_anim(IRON_ARM, IRON_HAND, None, 1.0, 0.25)          # Тирос: getLimbSwing без ×0.6
    an['old:~hold'] = hold_anim(OLD_ARM, OLD_HAND)
    an['old:~walk'] = walk_anim(OLD_ARM, OLD_HAND, None, 0.6, 0.25)
    an['new:~hold'] = hold_anim(CARRY_ARM, CARRY_HAND, CARRY_POS)
    an['new:~walk'] = walk_anim(CARRY_ARM, CARRY_HAND, CARRY_POS, 0.6, 0.0)
    tyros = CR.model_entry('tyros')
    tyros['scythe'] = False
    head = CR.model_entry('cult_leader')
    head['scythe'] = False
    return {'models': {'tyros': tyros, 'cult_leader': head}, 'anims': an,
            'items': {'hellrazor': hellrazor_item(), 'scythe': BV.scythe_item()}}


# столбцы: (подпись, анимация, t, yaw камеры, pitch); у добивания у Тироса пусто
COLS = [
    ('Покой', '~hold', 0.0, 35, 12),
    ('Ходьба', '~walk', 0.235, 35, 12),
    ('Боковой взмах', 'scythe_downslash_sideslash', 2.05, 20, 30),
    ('Взмах с разворотом', 'scythe_horizontal_slash_spin', 1.6, 20, 30),
    ('Двойной взмах', 'scythe_dagger_double_horizontal', 1.88, 20, 30),
    ('Удар сверху', 'scythe_sideslash_downslash_sideslash', 1.52, 70, 10),
    ('Прыжок, удар', 'scythe_jump_combo', 1.75, 70, 10),
    ('Появление', 'fire_boss_spawn', 7.4, 35, 12),
    ('Добивание', 'cult_leader_finisher', 1.35, 70, 12),
]
ROWS = [('Тирос Iron\'s — эталон', 'tyros', 'hellrazor', 'iron:'), ('Глава — было', 'cult_leader', 'scythe', 'old:'),
        ('Глава — стало', 'cult_leader', 'scythe', 'new:')]

PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;background:#120c0a;overflow:hidden;font:14px 'DejaVu Sans',system-ui,sans-serif;color:#f0e2d6}
.lab{position:fixed;z-index:3;font:600 15px 'DejaVu Sans',sans-serif;text-shadow:0 0 4px #000,0 0 2px #000;pointer-events:none}
.lab small{display:block;font:400 12px 'DejaVu Sans Mono',monospace;color:#d8c0b0}
.row{position:fixed;z-index:3;left:6px;font:700 17px 'DejaVu Sans',sans-serif;color:#ffd9a0;text-shadow:0 0 5px #000;writing-mode:vertical-rl;transform:rotate(180deg)}
.no{position:fixed;z-index:3;color:#8a7468;font:15px 'DejaVu Sans',sans-serif;text-align:center}
</style></head><body>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
LIB
<script>
const SD = SHEETDATA;
const D = Math.PI / 180;
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
function attachItem(model, item) {        // HumanoidRenderer Iron's + GeckoLib: кисть → (поворот кисти ещё раз) → −1/16 z, −1/16 y, X −90° → display
  const hand = model.bones.bipedHandRight;
  const dbl = new THREE.Group(); hand.add(dbl); model.dbl = dbl;
  const a = new THREE.Group(); a.position.set(0, -1, -1); dbl.add(a);
  const b = new THREE.Group(); b.rotation.x = -Math.PI / 2; a.add(b);
  const d = item.display.thirdperson_righthand;
  const t = new THREE.Group(); t.position.set(...(d.translation || [0, 0, 0])); b.add(t);
  const r = new THREE.Group(); r.quaternion.setFromEuler(new THREE.Euler(...(d.rotation || [0, 0, 0]).map(v => v * D), 'XYZ')); t.add(r);
  const s = new THREE.Group(); s.scale.set(...(d.scale || [1, 1, 1])); r.add(s);
  s.add(itemMesh(item.els));
  const tip = new THREE.Object3D(); tip.position.set(item.tip[0] - 8, item.tip[1] - 8, item.tip[2] - 8); s.children[0].add(tip);
  model.tip = tip;
}
function poseAt(m, an, t) { BL.pose(m, an, t); m.dbl.quaternion.copy(m.bones.bipedHandRight.quaternion); m.root.updateMatrixWorld(true); }
const W = innerWidth, H = innerHeight, cols = SD.cols.length, rows = SD.rows.length, LM = 34, TM = 30;
const cw = (W - LM) / cols, chh = (H - TM) / rows;
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H); renderer.setScissorTest(true); document.body.appendChild(renderer.domElement);
renderer.setClearColor(0x120c0a); renderer.clear();
function groundTex() {
  const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d');
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) { x.fillStyle = (i + j) % 2 ? '#3a2e28' : '#30251f'; x.fillRect(i * 16, j * 16, 16, 16); }
  const g = new THREE.CanvasTexture(c); g.magFilter = THREE.NearestFilter; g.wrapS = g.wrapT = THREE.RepeatWrapping; g.repeat.set(16, 16); return g;
}
const GT = groundTex();
SD.cols.forEach((c, ci) => {
  const d = document.createElement('div'); d.className = 'lab'; d.style.left = (LM + ci * cw + 8) + 'px'; d.style.top = '6px'; d.textContent = c[0]; document.body.appendChild(d);
});
function drawAll() {
document.querySelectorAll('.row,.no,.cl').forEach(e => e.remove());
SD.rows.forEach((r, ri) => {
  const d = document.createElement('div'); d.className = 'row'; d.style.top = (TM + ri * chh) + 'px'; d.style.height = chh + 'px';
  d.style.textAlign = 'center'; d.textContent = r[0]; document.body.appendChild(d);
  SD.cols.forEach((c, ci) => {
    const x0 = LM + ci * cw, y0 = TM + ri * chh;
    const key = r[3] + c[1], an = SD.anims[key];
    const vx = Math.round(x0) + 1, vy = Math.round(H - y0 - chh) + 1, vw = Math.round(cw) - 2, vh = Math.round(chh) - 2;
    if (!an) {
      renderer.setViewport(vx, vy, vw, vh); renderer.setScissor(vx, vy, vw, vh); renderer.setClearColor(0x1a1210); renderer.clear();
      const n = document.createElement('div'); n.className = 'no'; n.style.left = x0 + 'px'; n.style.width = cw + 'px'; n.style.top = (y0 + chh / 2 - 10) + 'px';
      n.textContent = 'у Тироса нет'; document.body.appendChild(n); return;
    }
    const scene = new THREE.Scene(); scene.background = new THREE.Color(0x1c1210);
    scene.add(new THREE.HemisphereLight(0xd8c8c0, 0x281410, 0.85));
    const dl = new THREE.DirectionalLight(0xfff0e0, 0.7); dl.position.set(30, 60, -40); scene.add(dl);
    const d2 = new THREE.DirectionalLight(0xff8040, 0.3); d2.position.set(-40, 20, 50); scene.add(d2);
    const gr = new THREE.Mesh(new THREE.PlaneGeometry(256, 256), new THREE.MeshLambertMaterial({ map: GT })); gr.rotation.x = -Math.PI / 2; scene.add(gr);
    // стрелка «вперёд» (−z модели)
    const red = new THREE.MeshBasicMaterial({ color: 0xff3a2a });
    const sh = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.3, 16), red); sh.position.set(0, 0.2, -18); scene.add(sh);
    const hd = new THREE.Mesh(new THREE.ConeGeometry(3, 6, 12), red); hd.rotation.x = -Math.PI / 2; hd.position.set(0, 0.2, -29); scene.add(hd);
    const m = BL.buildModel(SD.models[r[1]], false); attachItem(m, SD.items[r[2]]); scene.add(m.root);
    // след острия: 0.15 с до кадра
    const pts = [];
    for (let k = 6; k >= 0; k--) { poseAt(m, an, Math.max(0, c[2] - k * 0.025)); pts.push(m.tip.getWorldPosition(new THREE.Vector3())); }
    poseAt(m, an, c[2]); BL.flameFrame(m, Math.floor(c[2] * 20));
    if (pts[0].distanceTo(pts[pts.length - 1]) > 1.5) {
      const curve = new THREE.CatmullRomCurve3(pts);
      const yel = new THREE.MeshBasicMaterial({ color: 0xffd23a, transparent: true, opacity: 0.9, depthTest: false });
      const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 24, 0.45, 6, false), yel); tube.renderOrder = 5; scene.add(tube);
      const dir = pts[pts.length - 1].clone().sub(pts[pts.length - 2]).normalize();
      const cone = new THREE.Mesh(new THREE.ConeGeometry(1.4, 3.5, 10), yel); cone.renderOrder = 5;
      cone.position.copy(pts[pts.length - 1]); cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir); scene.add(cone);
    }
    const h = SD.models[r[1]].height || 34, yaw = c[3] * D, pitch = c[4] * D, dist = 3.6 * h * Math.max(1, (chh / cw) * 0.75);
    const cam = new THREE.PerspectiveCamera(30, vw / vh, 0.5, 3000), ty = h * 0.5;
    cam.position.set(Math.sin(yaw) * Math.cos(pitch) * dist, ty + Math.sin(pitch) * dist, -Math.cos(yaw) * Math.cos(pitch) * dist);
    cam.lookAt(0, ty, -4);
    renderer.setViewport(vx, vy, vw, vh); renderer.setScissor(vx, vy, vw, vh); renderer.render(scene, cam);
    const lab = document.createElement('div'); lab.className = 'lab cl'; lab.style.left = (x0 + 8) + 'px'; lab.style.top = (y0 + chh - 22) + 'px';
    lab.innerHTML = '<small>' + c[1] + (c[1].startsWith('~') ? '' : ' · ' + c[2].toFixed(2) + ' с') + '</small>'; document.body.appendChild(lab);
  });
});
}
// текстуры моделей грузятся асинхронно: сначала прогрев (строим и рисуем один раз), потом чистовой кадр
{ const sc = new THREE.Scene(), cm = new THREE.PerspectiveCamera();
  for (const k in SD.models) sc.add(BL.buildModel(SD.models[k], false).root);
  renderer.setViewport(0, 0, 4, 4); renderer.setScissor(0, 0, 4, 4); renderer.render(sc, cm); }
setTimeout(() => { drawAll(); setTimeout(() => { drawAll(); window.READY = true; }, 1500); }, 2500);
</script></body></html>"""


def main():
    args = sys.argv[1:]
    out = args[0] if args and not args[0].startswith('--') else os.path.join(ROOT, 'docs', 'media', 't26_hold_tyros.jpg')
    base = args[args.index('--base') + 1] if '--base' in args else BASE
    three = args[args.index('--three') + 1] if '--three' in args else None
    lib = BV.boss_lib('tyros')                     # buildModel / pose / flameFrame из превью Главы (в области BL)
    d = data(base)
    sd = {'models': d['models'], 'anims': d['anims'], 'items': d['items'], 'cols': COLS, 'rows': ROWS}
    html = PAGE.replace('LIB', lib).replace('SHEETDATA', json.dumps(sd, ensure_ascii=False, separators=(',', ':')))
    if three:
        html = html.replace(CR.CDN, 'file://' + os.path.abspath(three))
    CR.shoot(html, out, size=(2400, 1060))


if __name__ == '__main__':
    main()
