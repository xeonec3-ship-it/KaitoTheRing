#!/usr/bin/env python3
"""
Реакция боссов культа на «Дезинтеграцию: Реплику» (решение владельца 20.11): заклинание на них не действует —
у каждого своя анимация разрушения печатей. Глава Культа (T26) — tools/gen_cult_leader_extra.py; здесь — четверо:
  Ирина (T27)  irina_replica_break   — нити оплетают печати, сжатая ладонь рвёт их на алые лоскуты, те втягиваются в рукава;
  Арис (T28)   animation.aris.replica_break — молот бьёт по печати как по заготовке: искры, печати плющатся, краснеют, окалина; рога вспыхивают;
  Мартин (T29) martin_replica_break  — Реплика принята на щит (лязг, искры), двуручник рассекает печати крест-накрест;
  Эреб (T30)   ereb_replica_break    — щелчок пальцев: печати — стекло с рябью отражения, осыпаются осколками и бабочками; лёгкий поклон.
Фраз нет (фраза только у Главы). Лучей/линий от босса к заклинателю нет.

Что пишет (только своё):
  animations/entity/<босс>.animation.json — ДОПИСЫВАЕТ одну анимацию (остальные не трогает; файл перезаписывается тем же compact-JSON);
  fx/<босс>_replica_break.json, sigils/<босс>_replica_*.json, textures/sigil/<босс>_replica_*.png;
  docs/media/replica_break_all.jpg (--shots [--three путь/three.min.js]) — по 3 кадра на босса (до / break / после) с условными fx.

Генераторы боссов зовут add_anims()/write_fx() сами (gen_irina.py, gen_aris_anims.py, gen_martin.py, gen_ereb_anims.py,
gen_*_fx.py), так что при полной пересборке ничего не теряется. Отдельный запуск: python3 tools/gen_replica_break.py [--shots].

Печати Реплики (fx disintegration_replica, target = босс): поле r 4.5 на +0.06, ярус r 3.4 на +2.42, верхняя r 4.8 на +4.82
(size × expand 4). Наши печати-наложения ставятся туда же, size 1 × scale = радиус.
Анимации собраны из поз уже принятых анимаций босса (сэмплы) + правки, запечены по 0.05 с (как у Ирины) — смотрятся одинаково
в GeckoLib и в превью любого из четырёх шаблонов.
"""
import base64
import io
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
MEDIA = os.path.join(ROOT, 'docs', 'media')
WRITTEN = []

REPLICA, REPLICA_HI, REPLICA_D = '#FF1934', '#FF6676', '#7A0612'
SEALS = (('field', 0.06, 4.5), ('tier', 2.42, 3.4), ('top', 4.82, 4.8))      # печать Реплики, высота, радиус (блоки)
DT = 0.05


# ================================================================== запись
def _dump(rel, obj, compact=False):
    p = os.path.join(A, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        if compact:
            json.dump(obj, f, ensure_ascii=False, separators=(',', ':'))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write('\n')
    WRITTEN.append(rel)


def hx(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


# ================================================================== позы: сэмплы чужих анимаций → запечённая анимация
def _keys(ch):
    """Канал GeckoLib → [(t, [x, y, z])] по возрастанию."""
    if isinstance(ch, list):
        return [(0.0, ch)]
    if isinstance(ch, (int, float)):
        return [(0.0, [ch, ch, ch])]
    if 'vector' in ch:
        return [(0.0, ch['vector'])]
    out = []
    for k, v in ch.items():
        if isinstance(v, dict):
            v = v.get('vector', v.get('post', v.get('pre')))
            if isinstance(v, dict):
                v = v.get('vector')
        if isinstance(v, (int, float)):
            v = [v, v, v]
        out.append((float(k), [float(x) if not isinstance(x, str) else 0.0 for x in v]))
    return sorted(out)


def _at(keys, t):
    if t <= keys[0][0]:
        return list(keys[0][1])
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            k = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            return [a[i] + (b[i] - a[i]) * k for i in range(3)]
    return list(keys[-1][1])


def sample(anims, name, t):
    """Поза = {кость: {канал: [x, y, z]}} анимации name в момент t."""
    a = anims[name]
    return {b: {c: _at(_keys(v), t) for c, v in chs.items()} for b, chs in a['bones'].items()}


def mod(pose, **bones):
    """Копия позы с правками: bone=dict(rotation=[...] | rot_add=[...], position=..., pos_add=..., scale=...)."""
    p = {b: {c: list(v) for c, v in chs.items()} for b, chs in pose.items()}
    for b, ch in bones.items():
        d = p.setdefault(b, {})
        for k, v in ch.items():
            if k.endswith('_add'):
                c = {'rot_add': 'rotation', 'pos_add': 'position'}[k]
                base = d.get(c, [0.0, 0.0, 0.0])
                d[c] = [base[i] + v[i] for i in range(3)]
            else:
                d[k] = list(v)
    return p


EASE = {
    None: lambda k: k,
    'io': lambda k: 0.5 - 0.5 * math.cos(math.pi * k),
    'out': lambda k: 1 - (1 - k) ** 3,
    'in': lambda k: k ** 3,
    'outq': lambda k: 1 - (1 - k) ** 4,
    'inq': lambda k: k ** 4,
    'back': lambda k: 1 + 2.2 * (k - 1) ** 3 + 1.2 * (k - 1) ** 2,
}
DEF = {'rotation': [0.0, 0.0, 0.0], 'position': [0.0, 0.0, 0.0], 'scale': [1.0, 1.0, 1.0]}


def _tk(t):
    """Ключ времени: всегда с точкой ('1.0', не '1') — иначе в JS целые ключи встают в начало объекта и ломают порядок."""
    s = '%.4g' % t
    return s if '.' in s else s + '.0'


def bake(length, keys, timeline, step_scale=True):
    """keys: [(t, pose, ease)] — ease действует на отрезке, который ЗАКАНЧИВАЕТСЯ в этом ключе. Scale-каналы — ступенькой
    (видимость меча/щита: 0/1 переключается в момент ключа, как в анимациях Мартина)."""
    bones = {}
    for _, p, _ in keys:
        for b, chs in p.items():
            bones.setdefault(b, set()).update(chs)
    n = int(round(length / DT))
    out = {}
    for b, chs in sorted(bones.items()):
        o = {}
        for c in sorted(chs):
            seq = {}
            for i in range(n + 1):
                t = round(i * DT, 4)
                j = max(k for k in range(len(keys)) if keys[k][0] <= t + 1e-9)
                t0, p0, _ = keys[j]
                v0 = p0.get(b, {}).get(c, DEF[c])
                if j + 1 < len(keys):
                    t1, p1, e = keys[j + 1]
                    v1 = p1.get(b, {}).get(c, DEF[c])
                    if c == 'scale' and step_scale:
                        k = 0.0
                    else:
                        k = EASE[e]((t - t0) / (t1 - t0))
                    v = [v0[q] + (v1[q] - v0[q]) * k for q in range(3)]
                else:
                    v = v0
                seq[_tk(t)] = [round(x, 3) for x in v]
            o[c] = seq
        out[b] = o
    a = {'loop': False, 'animation_length': length, 'bones': out}
    if timeline:
        a['timeline'] = {_tk(t): ev for t, ev in timeline}
    return a


def _anim_file(boss):
    return os.path.join(A, 'animations', 'entity', boss + '.animation.json')


def _load_anims(boss):
    return json.load(open(_anim_file(boss), encoding='utf-8'))['animations']


ANIM_NAME = {'irina': 'irina_replica_break', 'aris': 'animation.aris.replica_break',
             'martin': 'martin_replica_break', 'ereb': 'ereb_replica_break'}


# ================================================================== кадры: наложение условных fx на рендер босса (его же шаблоном)
# Ячейка шаблона получает ключ rbfx — список элементов (блоки; x — вправо от босса, y — вверх, z — вперёд):
#   {k:'seal', tex, y, r, op, color, rot, sx, sz}         — плоская печать (вид сверху) на высоте y, радиус r; sx/sz — сплющить
#   {k:'spr', tex, n, at, spread, size:[a,b], color, op, spin, seed, ring:[r0,r1], y}  — спрайты (ring — по кольцу печати)
#   {k:'tube', pts:[[x,y,z]…], w, color, op}               — светящаяся нить/след (Catmull-Rom), с ореолом
RBFX_JS = r"""
<script>
(function(){
  const TX = {}, L = new THREE.TextureLoader();
  for (const k in RBTEX) { const t = L.load(RBTEX[k]); t.minFilter = THREE.LinearMipMapLinearFilter; TX[k] = t; }
  const SX = 1;      // «вправо от босса» в осях шаблона (модель смотрит на −z)
  function rnd(seed) { let x = (seed || 7) * 9301 + 49297; return () => { x = (x * 9301 + 49297) % 233280; return x / 233280; }; }
  function mat(f, tex) {
    return new THREE.MeshBasicMaterial({ map: tex || null, color: new THREE.Color(f.color || '#ffffff'), transparent: true, depthWrite: false,
      opacity: f.op ?? 1, blending: f.normal ? THREE.NormalBlending : THREE.AdditiveBlending, side: THREE.DoubleSide });
  }
  const P = v => new THREE.Vector3(SX * v[0] * 16, v[1] * 16, -v[2] * 16);
  window.RBFX = function(sc, cam, c) {
    for (const f of (c.rbfx || [])) {
      if (f.k === 'seal') {
        const m = new THREE.Mesh(new THREE.PlaneGeometry(f.r * 32, f.r * 32), mat(f, TX[f.tex]));
        m.rotation.order = 'YXZ'; m.rotation.x = -Math.PI / 2; m.rotation.y = (f.rot || 0) * Math.PI / 180;
        if (f.tilt) { m.rotation.x += f.tilt[0] * Math.PI / 180; m.rotation.z = (f.tilt[1] || 0) * Math.PI / 180; }
        m.scale.set(f.sx || 1, f.sz || 1, 1);
        m.position.copy(P([f.x || 0, f.y, f.z || 0])); m.renderOrder = 4 + (f.order || 0); sc.add(m);
      } else if (f.k === 'spr') {
        const R = rnd(f.seed), n = f.n || 1, sp = f.spread || [0, 0, 0], at = f.at || [0, 0, 0];
        const mt = mat(f, TX[f.tex]);
        for (let i = 0; i < n; i++) {
          const sz = (f.size ? f.size[0] + (f.size[1] - f.size[0]) * R() : 1) * 16;
          const m = new THREE.Mesh(new THREE.PlaneGeometry(sz, sz), mt);
          let p;
          if (f.ring) { const a = R() * Math.PI * 2, r = f.ring[0] + (f.ring[1] - f.ring[0]) * Math.sqrt(R());
            p = [at[0] + Math.cos(a) * r, at[1] + (R() * 2 - 1) * sp[1], at[2] + Math.sin(a) * r]; }
          else p = [at[0] + (R() * 2 - 1) * sp[0], at[1] + (R() * 2 - 1) * sp[1], at[2] + (R() * 2 - 1) * sp[2]];
          m.position.copy(P(p));
          m.userData.rbspin = (R() * 2 - 1) * (f.spin ?? 0.6);
          m.renderOrder = 6; sc.add(m);
          m.quaternion.copy(cam.quaternion); m.rotateZ(m.userData.rbspin);
        }
      } else if (f.k === 'tube') {
        const curve = new THREE.CatmullRomCurve3(f.pts.map(P));
        const seg = Math.max(16, f.pts.length * 12);
        for (const [w, op] of [[f.w, f.op ?? 1], [f.w * 3.2, (f.op ?? 1) * 0.22]]) {
          const g = new THREE.TubeGeometry(curve, seg, Math.max(0.05, w * 8), 8, !!f.closed);
          const m = new THREE.Mesh(g, mat(Object.assign({}, f, { op }), null)); m.renderOrder = 5; sc.add(m);
        }
      }
    }
  };
})();
</script>
"""


def _png_b64(img):
    b = io.BytesIO()
    img.save(b, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def _tex_b64(name):
    for d in ('sigil', 'fx'):
        p = os.path.join(A, 'textures', d, name + '.png')
        if os.path.exists(p):
            return 'data:image/png;base64,' + base64.b64encode(open(p, 'rb').read()).decode()
    raise FileNotFoundError(name)


def inject(html, cells, extra_tex=None):
    """Вставить движок наложений сразу за three.js (текстуры начнут грузиться до onLoad шаблона) и вызов перед render."""
    need = set()
    for c in cells:
        for f in c.get('rbfx', []):
            if f.get('tex'):
                need.add(f['tex'])
    tex = {}
    for n in need:
        tex[n] = (extra_tex or {}).get(n) or _tex_b64(n)
    js = '<script>const RBTEX = ' + json.dumps(tex) + ';</script>' + RBFX_JS
    i = html.find('three.min.js')
    j = html.find('</script>', i) + len('</script>')
    html = html[:j] + js + html[j:]
    assert 'renderer.render(sc, cam);' in html
    return html.replace('renderer.render(sc, cam);', 'if (window.RBFX) RBFX(sc, cam, c); renderer.render(sc, cam);', 1)


def _three(args):
    return args[args.index('--three') + 1] if '--three' in args else None


def render(boss, cells, out, three=None, cols=3, size=(1800, 640), extra_tex=None):
    """Кадры шаблоном босса (его модель, свет, анимации из файла) + наложения rbfx."""
    sys.path.insert(0, HERE)
    import cult_leader_render as CR
    sheet = {'cols': cols, 'cells': cells}
    if boss == 'irina':
        import irina_render as R
        html = R.page(sheet, three)
    elif boss == 'aris':
        import aris_render as R
        html = R.page(sheet, three)
    elif boss == 'martin':
        import martin_render as R
        names = sorted({c['model'] for c in cells} | {x['model'] for c in cells for x in c.get('models', [])})
        html = R.page(R.data(names), sheet, three, [], [])
    else:
        import gen_ereb_render as R
        names = sorted({c['model'] for c in cells} | {w['model'] for c in cells for w in c.get('with', [])})
        html = R.page(names, sheet, three)
    CR.shoot(inject(html, cells, extra_tex), out, size)


# ================================================================== анимации
def anim_irina(an):
    """Ирина, 2.0 с: левая ладонь вверх к печатям (нити ползут), 'bind' 0.5 — нити оплели; дрожь натяжения;
    'break' 1.0 — сжала ладонь и рванула к себе; 1.0–1.6 лоскуты втягиваются в рукава (руки чуть врозь), 2.0 — покой."""
    idle = sample(an, 'irina_idle', 0)
    # оси как у Iron's: рука вперёд/вверх — x минус (−160 — над головой), левая в сторону — z минус; голова вверх — x минус.
    # Проверка 20.11: ладонь вверх-вперёд-в сторону (не над головой — иначе рука проходит сквозь поля шляпы); правая держит посох
    # в хвате покоя (tools/gen_irina.py R_HOLD), без резких поворотов древка.
    reach = mod(idle, left_arm=dict(rotation=[-124, 6, 30]), head=dict(rotation=[-22, -8, 4]), torso=dict(rotation=[-6, -10, 0]),
                right_arm=dict(rotation=[-44, 0, 16]))
    strain = mod(reach, left_arm=dict(rot_add=[5, 0, -4]), torso=dict(rot_add=[2, 2, 0]), head=dict(rot_add=[3, 0, 0]))
    clench = mod(idle, left_arm=dict(rotation=[-62, 22, -6]), torso=dict(rotation=[10, 16, 0]), head=dict(rotation=[12, 10, 4]),
                 right_arm=dict(rotation=[-42, 0, 14]), body=dict(position=[0, -0.6, 0]))
    draw = mod(idle, left_arm=dict(rotation=[-28, -6, -52]), right_arm=dict(rotation=[-40, 0, 30]), torso=dict(rotation=[-4, 0, 0]),
               head=dict(rotation=[-6, 0, 4]))
    speak = mod(clench, head=dict(rotation=[2, -16, 10]), left_arm=dict(rotation=[-48, 18, -16]), torso=dict(rotation=[2, 8, 0]))
    keys = [(0, idle, None), (0.45, reach, 'io'), (0.62, strain, 'io'), (0.78, reach, 'io'), (0.9, strain, 'io'),
            (1.0, clench, 'inq'), (1.25, speak, 'io'), (1.6, mod(draw, head=dict(rotation=[0, -10, 8])), 'io'), (2.2, idle, 'io')]
    return bake(2.2, keys, [(0.5, 'bind'), (1.0, 'break'), (1.25, 'speak')])


def anim_aris(an):
    """Арис, 2.0 с: замах, 'strike' 0.65 — удар по печати-заготовке под ногами (искры, звон); короткий подъём,
    'break' 1.15 — второй удар: печати плющатся и осыпаются окалиной, рога вспыхивают; 1.4–2.0 молот на плечо → покой."""
    idle = sample(an, 'animation.aris.idle', 0)
    wind = sample(an, 'animation.aris.slam', 0.6)
    hit = sample(an, 'animation.aris.slam', 0.75)
    half = mod(sample(an, 'animation.aris.slam', 0.5), body=dict(pos_add=[0, 0.5, 0]))
    hold = mod(hit, head=dict(rot_add=[-8, -12, 0]), torso=dict(rot_add=[-6, 0, 0]), left_arm=dict(rot_add=[-18, 0, -14]))
    keys = [(0, idle, None), (0.25, sample(an, 'animation.aris.slam', 0.42), 'io'), (0.5, wind, 'out'), (0.65, hit, 'inq'),
            (0.75, hit, None), (0.95, half, 'out'), (1.15, hit, 'inq'), (1.4, hold, 'out'), (2.0, idle, 'io')]
    return bake(2.0, keys, [(0.65, 'strike'), (1.15, 'break'), (1.4, 'speak')])


def anim_martin(an):
    """Мартин (×2), 2.2 с: щит вверх над головой — 'block' 0.4 (лязг, искры); щит за спину, хват двумя руками;
    'slash' 0.9 — первый косой удар справа сверху; 'break' 1.35 — второй, крест-накрест; 2.2 — покой. Видимость щитов —
    ключами scale (shield_hand / shield_back / banner_held), как в остальных анимациях Мартина."""
    SH_HAND = dict(shield_hand=dict(scale=[1, 1, 1]), shield_back=dict(scale=[0, 0, 0]), banner_held=dict(scale=[0, 0, 0]))
    SH_BACK = dict(shield_hand=dict(scale=[0, 0, 0]), shield_back=dict(scale=[1, 1, 1]), banner_held=dict(scale=[0, 0, 0]))
    idle = mod(sample(an, 'martin_idle', 0), **SH_BACK)
    up = mod(sample(an, 'martin_shield_wall', 0.6), **SH_HAND)
    up = mod(up, left_arm=dict(rot_add=[-66, 0, -12]), head=dict(rot_add=[-16, 0, 0]))
    jolt = mod(up, body=dict(pos_add=[0, -1.2, 0]), left_arm=dict(rot_add=[10, 0, 0]), torso=dict(rot_add=[4, 0, 0]))
    ow, oh = sample(an, 'martin_overhead', 0.6), sample(an, 'martin_overhead', 0.96)
    w1 = mod(ow, **SH_BACK, torso=dict(rot_add=[-8, -30, 26]), head=dict(rot_add=[-12, 0, 0]))
    h1 = mod(oh, **SH_BACK, torso=dict(rot_add=[8, 34, -30]))
    w2 = mod(ow, **SH_BACK, torso=dict(rot_add=[-8, 30, -26]), head=dict(rot_add=[-12, 0, 0]))
    h2 = mod(oh, **SH_BACK, torso=dict(rot_add=[8, -34, 30]))
    keys = [(0, idle, None), (0.15, mod(idle, **SH_HAND), 'io'), (0.38, up, 'outq'), (0.45, jolt, 'out'), (0.6, up, 'io'),
            (0.62, mod(up, **SH_BACK), None), (0.78, w1, 'io'), (0.92, h1, 'inq'), (1.05, h1, None), (1.2, w2, 'io'),
            (1.35, h2, 'inq'), (1.5, h2, None), (1.75, mod(h2, torso=dict(rot_add=[-10, 20, -18]), head=dict(rot_add=[-6, 12, 0])), 'io'),
            (2.4, idle, 'io')]
    return bake(2.4, keys, [(0.4, 'block'), (0.9, 'slash'), (1.35, 'break'), (1.7, 'speak')])


def anim_ereb(an):
    """Эреб, 1.8 с: левая рука вверх к печатям, 'snap' 0.55 — щелчок (печати становятся стеклом, по ним рябь отражения);
    'break' 0.95 — стекло осыпается осколками и бабочками; 1.1–1.5 лёгкий поклон (как в появлении), 1.8 — покой."""
    idle = sample(an, 'ereb_idle', 0)
    cast = sample(an, 'ereb_cast_illusion', 0.75)
    raise_ = mod(cast, left_arm=dict(rotation=[-172, 0, -24]), head=dict(rotation=[-18, 6, 0]))
    snap = mod(raise_, left_arm=dict(rot_add=[8, 0, 4]), bipedHandLeft=dict(rotation=[-18, 0, 0]))
    watch = mod(raise_, left_arm=dict(rotation=[-120, -20, -20]), head=dict(rotation=[-10, 4, 0]))
    bow = sample(an, 'ereb_spawn', 3.0)
    talk = mod(idle, left_arm=dict(rotation=[-42, -14, -22]), head=dict(rotation=[-4, 14, 8]))
    keys = [(0, idle, None), (0.42, raise_, 'out'), (0.55, snap, 'inq'), (0.75, snap, None), (0.95, watch, 'io'),
            (1.25, bow, 'io'), (1.35, bow, None), (1.6, talk, 'io'), (1.95, talk, None), (2.3, idle, 'io')]
    return bake(2.3, keys, [(0.55, 'snap'), (0.95, 'break'), (1.55, 'speak')])


ANIMS = {'irina': anim_irina, 'aris': anim_aris, 'martin': anim_martin, 'ereb': anim_ereb}


def add_anims(boss, animations):
    """Для генераторов боссов: дописать нашу анимацию в их словарь animations (имя → json) перед записью файла."""
    animations[ANIM_NAME[boss]] = ANIMS[boss](animations)
    return animations


def patch_anim_file(boss):
    """Отдельный запуск: дописать анимацию в уже собранный файл (тот же compact-JSON, остальное — байт в байт)."""
    p = _anim_file(boss)
    doc = json.load(open(p, encoding='utf-8'))
    add_anims(boss, doc['animations'])
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')
    WRITTEN.append('animations/entity/%s.animation.json (+%s)' % (boss, ANIM_NAME[boss]))


# ================================================================== текстуры наложений (маски: белый + альфа, 512)
S2 = 1024          # рисуем ×2 и уменьшаем


def _save_mask(mask, name):
    small = mask.resize((512, 512), Image.LANCZOS)
    rgba = Image.new('RGBA', (512, 512), (255, 255, 255, 0))
    rgba.putalpha(small)
    rgba.save(os.path.join(A, 'textures', 'sigil', name + '.png'), optimize=True)
    WRITTEN.append('textures/sigil/%s.png' % name)
    return rgba


def _glowed(mask, r, k):
    g = mask.filter(ImageFilter.GaussianBlur(r))
    return Image.fromarray(np.clip(np.maximum(np.asarray(mask, np.float32), np.asarray(g, np.float32) * k), 0, 255).astype(np.uint8))


def _wob(rng, n=4):
    return [(rng.uniform(0.004, 0.02), rng.randint(2, 9), rng.uniform(0, 6.3)) for _ in range(n)]


def tex_irina_web():
    """Нити ревности, оплетающие печать: три петлистых кольца-узла, хорды через диск (нить обмотана вокруг печати), узелки."""
    rng = random.Random(27)
    im = Image.new('L', (S2, S2), 0)
    d = ImageDraw.Draw(im)
    c = S2 / 2
    for R, loops, amp, w in ((0.94, 22, 0.022, 7), (0.72, 16, 0.03, 6), (0.47, 11, 0.035, 5)):
        pts = []
        for i in range(1601):
            t = 2 * math.pi * i / 1600
            r = R + amp * math.cos(loops * t)
            a = t + (amp / R) * 0.9 * math.sin(loops * t)
            pts.append((c + c * r * math.cos(a), c + c * r * math.sin(a)))
        d.line(pts, fill=255, width=w, joint='curve')
    for k in range(14):                                   # хорды: нить перекинута через печать, чуть провисает
        a0 = rng.uniform(0, 2 * math.pi)
        a1 = a0 + rng.uniform(2.0, 3.6)
        p0 = (c + c * 0.97 * math.cos(a0), c + c * 0.97 * math.sin(a0))
        p1 = (c + c * 0.97 * math.cos(a1), c + c * 0.97 * math.sin(a1))
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        nx, ny = -(p1[1] - p0[1]), p1[0] - p0[0]
        L = math.hypot(nx, ny) or 1
        sag = rng.uniform(-0.08, 0.08) * c
        pts = []
        for i in range(81):
            u = i / 80
            b = 4 * u * (1 - u)
            pts.append((p0[0] + (p1[0] - p0[0]) * u + nx / L * sag * b, p0[1] + (p1[1] - p0[1]) * u + ny / L * sag * b))
        d.line(pts, fill=215, width=4, joint='curve')
    for k in range(18):                                   # узелки на пересечениях с ободом
        a = rng.uniform(0, 2 * math.pi)
        r = rng.choice((0.94, 0.72, 0.47)) * c
        x, y = c + r * math.cos(a), c + r * math.sin(a)
        d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=255)
    return _save_mask(_glowed(im, 6, 0.7), 'irina_replica_web')


def tex_aris_hot():
    """Раскалённая заготовка: металл светится от центра к краю пятнами, вмятины от молота (светлые края), сетка окалины."""
    rng = random.Random(28)
    y, x = np.mgrid[0:S2, 0:S2] / (S2 / 2) - 1.0
    r = np.hypot(x, y)
    base = np.clip(1 - r, 0, 1) ** 0.6 * 0.55 + np.exp(-((r - 0.82) / 0.12) ** 2) * 0.35
    noise = np.zeros_like(r)
    for k in range(5):
        f = 2 ** k * 3
        ph = rng.uniform(0, 6.3)
        noise += np.sin(x * f + ph) * np.cos(y * f * 1.3 - ph) / (k + 1)
    base *= 0.75 + 0.25 * noise / 2
    img = Image.fromarray(np.clip(base * 255 * (r < 1), 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    c = S2 / 2
    for k in range(6):                                    # вмятины
        a, rr = rng.uniform(0, 6.3), rng.uniform(0.1, 0.7)
        cx, cy, s = c + c * rr * math.cos(a), c + c * rr * math.sin(a), rng.uniform(40, 80)
        d.ellipse([cx - s, cy - s * 0.7, cx + s, cy + s * 0.7], outline=255, width=6)
        d.ellipse([cx - s * 0.6, cy - s * 0.42, cx + s * 0.6, cy + s * 0.42], fill=40)
    small = 256                                           # окалина: сетка Вороного — тёмные швы между чешуйками
    pts = np.array([(rng.uniform(-1, 1), rng.uniform(-1, 1)) for _ in range(90)])
    yy, xx = np.mgrid[0:small, 0:small] / (small / 2) - 1.0
    dd = np.sort(np.hypot(xx[..., None] - pts[:, 0], yy[..., None] - pts[:, 1]), axis=2)
    seam = np.clip(1 - (dd[..., 1] - dd[..., 0]) / 0.035, 0, 1)
    seam = np.asarray(Image.fromarray((seam * 255).astype(np.uint8)).resize((S2, S2), Image.BILINEAR), np.float32) / 255
    arr = np.asarray(img, np.float32) * (1 - 0.85 * seam)
    img = Image.fromarray(arr.astype(np.uint8))
    return _save_mask(img.filter(ImageFilter.GaussianBlur(1.2)), 'aris_replica_hot')


def tex_martin_cut(name, ang):
    """Разрез мечом поперёк печати: тонкое яркое ядро, ореол, рваные края-сколы по обе стороны."""
    rng = random.Random(29 if ang > 0 else 31)
    im = Image.new('L', (S2, S2), 0)
    d = ImageDraw.Draw(im)
    c = S2 / 2
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    P = lambda u, v: (c + c * (u * ca - v * sa), c + c * (u * sa + v * ca))
    d.line([P(-1.02, 0), P(1.02, 0)], fill=255, width=9)
    for k in range(26):                                   # сколы от линии разреза
        u = rng.uniform(-0.9, 0.9)
        side = rng.choice((-1, 1))
        L = rng.uniform(0.04, 0.16) * (1 - abs(u) * 0.6)
        pts = [P(u, 0)]
        uu, vv = u, 0.0
        for s in range(3):
            uu += rng.uniform(-0.03, 0.03)
            vv += side * L / 3
            pts.append(P(uu, vv))
        d.line(pts, fill=200, width=4)
    g = _glowed(im, 14, 0.9)
    core = Image.new('L', (S2, S2), 0)
    ImageDraw.Draw(core).line([P(-1.0, 0), P(1.0, 0)], fill=255, width=3)
    return _save_mask(Image.fromarray(np.maximum(np.asarray(g), np.asarray(core))), name)


def tex_ereb_glass():
    """Печать стала стеклом: рябь отражения (кольца разной силы), косые блики, редкая звезда трещин от центра."""
    rng = random.Random(30)
    y, x = np.mgrid[0:S2, 0:S2] / (S2 / 2) - 1.0
    r = np.hypot(x, y)
    rip = (0.5 + 0.5 * np.cos(r * 46 - 1.2)) ** 6 * (0.35 + 0.65 * np.exp(-((r - 0.55) / 0.35) ** 2))
    streak = np.zeros_like(r)
    for off, w, s in ((-0.35, 0.05, 0.9), (-0.18, 0.02, 0.7), (0.25, 0.08, 0.55), (0.42, 0.025, 0.6)):
        streak += s * np.exp(-(((x + y) / math.sqrt(2) - off) / w) ** 2)
    rim = np.exp(-((r - 0.97) / 0.025) ** 2)
    base = (0.10 + 0.55 * rip + 0.5 * streak + 0.9 * rim) * (r < 1)
    img = Image.fromarray(np.clip(base * 255, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    c = S2 / 2
    for k in range(7):
        a = k * 2 * math.pi / 7 + rng.uniform(-0.3, 0.3)
        pts, rr = [(c, c)], 0.0
        while rr < 0.9:
            rr += rng.uniform(0.08, 0.16)
            a += rng.uniform(-0.12, 0.12)
            pts.append((c + c * rr * math.cos(a), c + c * rr * math.sin(a)))
        d.line(pts, fill=230, width=3)
    return _save_mask(img, 'ereb_replica_glass')


def textures():
    tex_irina_web()
    tex_aris_hot()
    tex_martin_cut('martin_replica_cut_a', 45)
    tex_martin_cut('martin_replica_cut_b', -45)
    tex_ereb_glass()


# ================================================================== печати-наложения (size 1 → в fx scale = радиус печати Реплики)
def _sigil(id_, comment, color, layers, dissolve, expand=None):
    o = {'comment': comment, 'size': 1.0, 'color': color, 'orientation': 'ground', 'lifetime': -1, 'hold': -1, 'layers': layers}
    if expand:
        o['expand'] = expand
    o['dissolve'] = dissolve
    _dump('sigils/%s.json' % id_, o)


def _disc(id_, tex, appear, br=1.3, h=0.012, **kw):
    o = {'id': id_, 'type': 'disc', 'texture': tex, 'radius': 1.0, 'heightOffset': h, 'brightness': br, 'appear': appear}
    o.update(kw)
    return o


def _ap(delay, dur, *modes, easing='easeOutCubic', **kw):
    o = {'delay': delay, 'duration': dur, 'easing': easing, 'modes': list(modes)}
    o.update(kw)
    return o


def sigils():
    where = 'Ставить на печати Реплики: +0.06 (scale 4.5), +2.42 (3.4), +4.82 (4.8).'
    _sigil('irina_replica_web', 'T27: нити ревности оплетают печать «Реплики». ' + where, '#E3262F',
           [_disc('glow', 'glow', _ap(0, 6, 'fade'), br=0.35, h=0.006),
            _disc('web', 'irina_replica_web', _ap(0, 8, 'draw', startAngle=90), br=1.5, rotation={'speed': -4})],
           {'modes': ['shatter', 'fade'], 'duration': 10})
    _sigil('aris_replica_hot', 'T28: печать «Реплики» как заготовка на наковальне: раскаляется, плющится (expand), раскалывается окалиной. ' + where,
           '#FF6A1E', [_disc('glow', 'glow', _ap(0, 6, 'fade'), br=0.55, h=0.006),
                       _disc('hot', 'aris_replica_hot', _ap(0, 6, 'fade'), br=1.5, pulse={'amp': 0.2, 'period': 6})],
           {'modes': ['cracks'], 'duration': 26,
            'cracks': {'count': 10, 'rings': 2, 'irregular': 0.5, 'jag': 0.3, 'crackTime': 0.3, 'fallTime': 0.5, 'gap': 0.04, 'push': 0.18,
                       'pop': 0.15, 'fall': 1.6, 'tumble': 120, 'spin': 40, 'glow': 1.8, 'dust': 40, 'color': '#FF7A1E'}},
           expand={'scale': 1.14, 'delay': 2, 'duration': 8, 'easing': 'easeOutBack'})
    for k, (s, ang) in enumerate((('a', 'справа сверху'), ('b', 'слева сверху'))):
        cr = {'modes': ['fade'], 'duration': 8} if s == 'a' else {
            'modes': ['cracks'], 'duration': 24, 'cracks': {'count': 4, 'rings': 1, 'irregular': 0.3, 'jag': 0.15, 'crackTime': 0.25,
                                                            'fallTime': 0.55, 'push': 0.3, 'pop': 0.2, 'fall': 1.4, 'tumble': 90,
                                                            'spin': 30, 'glow': 2.0, 'dust': 30, 'color': '#FFF1C4'}}
        _sigil('martin_replica_cut_' + s, 'T29: разрез двуручником по печати «Реплики» (%s; a — первый удар, b — второй, крест-накрест; '
               'b раскалывает печать). ' % ang + where, '#FFF1C4',
               [_disc('cut', 'martin_replica_cut_' + s, _ap(0, 3, 'fade', 'grow', easing='easeOutQuart'), br=1.8, h=0.02 + 0.004 * k)], cr)
    _sigil('ereb_replica_glass', 'T30: щелчок Эреба — печать «Реплики» становится стеклом с рябью отражения, потом трескается и осыпается. ' + where,
           '#BFE6FF', [_disc('glow', 'glow', _ap(0, 4, 'fade'), br=0.4, h=0.006),
                       _disc('glass', 'ereb_replica_glass', _ap(0, 5, 'fade', 'grow', easing='easeOutBack'), br=1.35, rotation={'speed': 3},
                             pulse={'amp': 0.25, 'period': 10})],
           {'modes': ['cracks'], 'duration': 28,
            'cracks': {'count': 11, 'rings': 2, 'irregular': 0.4, 'jag': 0.3, 'crackTime': 0.25, 'fallTime': 0.55, 'gap': 0.03, 'push': 0.25,
                       'pop': 0.3, 'fall': 1.4, 'tumble': 200, 'spin': 90, 'glow': 2.0, 'dust': 44, 'color': '#E8F6FF'}})


# ================================================================== fx (caster = босс; печати Реплики — fx disintegration_replica, target = тот же босс)
def E(type_, delay=0, at='caster', **kw):
    o = {'type': type_, 'delay': delay, 'at': at}
    o.update(kw)
    return o


def at(x, y, z):
    f = lambda v: ('%g' % round(v, 3))
    return 'caster+%s,%s,%s' % (f(x), f(y), f(z))


def on_seals(fn):
    """Элементы на каждой из трёх печатей Реплики: fn(имя, высота, радиус, номер) → список."""
    out = []
    for i, (n, y, r) in enumerate(SEALS):
        out += fn(n, y, r, i)
    return out


def fx_irina():
    T = 'T27 Ирина ломает «Дезинтеграцию: Реплику» (caster = Ирина, анимация irina_replica_break 2.0 с). '
    els = [E('trail', 0, at(-0.55, 1.6, 0.6), duration=22, width=0.07, length=14, fade=1.2, head=0, count=6, follow=True, color='@primary',
             orbit={'radius': 1.3, 'speed': 16, 'rise': 0.3, 'risePeriod': 26, 'climb': 6.0}, comment='нити ползут из рукавов вверх по печатям'),
           E('trail', 2, at(0, 0.4, 0), duration=16, width=0.06, length=12, fade=1.2, head=0, count=5, follow=True, color='@primary',
             orbit={'radius': 3.4, 'speed': -12, 'rise': 0.2, 'risePeriod': 20})]
    els += on_seals(lambda n, y, r, i: [
        E('sigil', 5 + 2 * i, at(0, y, 0), id='irina_replica_web', scale=r, until=20, comment='сеть нитей на печати ' + n),
        E('sprites', 10, at(0, y, 0), duration=3, texture='mote_thread', count=18, rate=8, area=r, speed=0.02, spin=60, size=[0.3, 0.2], life=14,
          color='#E3262F', glow=0.4, comment='bind: нити затянулись')])
    els += [E('flash', 10, at(-0.55, 2.03, 0.74), duration=8, size=0.9, color='@primary', comment='поднятая ладонь (кисть в 0.5 с, проверка 20.11)')]
    els += [E('flash', 20, at(0, 2.42, 0), duration=10, size=3.2, rays=8, color='#FF1934', comment='break: сжала ладонь — печати рвутся'),
            E('flash', 20, at(-0.11, 1.11, 0.78), duration=6, size=0.8, color='#FFE0E6')]
    els += on_seals(lambda n, y, r, i: [
        E('sprites', 20, at(0, y, 0), duration=3, texture='mote_thread', count=55, rate=20, area=r, speed=0.12, gravity=0.0, spin=140, tumble=True,
          size=[0.42, 0.18], life=26, color='#E3262F', glow=0.5, comment='алые лоскуты-нити'),
        E('sprites', 21, at(0, y, 0), duration=3, texture='spark_soft', count=30, rate=12, area=r, speed=0.06, gravity=0.01, size=[0.14, 0.04],
          life=16, color='#FF1934', glow=0.6)])
    els += [E('vortex', 22, at(0, 1.2, 0), duration=18, radius=4.6, height=4.4, arms=6, speed=20, pull=0.45, funnel=0.12, turns=1.5, width=0.12,
              texture='mote_thread', particles=140, life=18, size=0.28, color='@primary', comment='лоскуты втягиваются к ней воронкой'),
            E('sprites', 30, at(-0.97, 0.97, 0.4), duration=10, texture='mote_thread', count=18, rate=3, spread=0.35, speed=-0.04, size=[0.3, 0.06],
              life=10, color='#E3262F', glow=0.4, comment='в левый рукав'),
            E('sprites', 30, at(0.69, 0.89, 0.6), duration=10, texture='mote_thread', count=18, rate=3, spread=0.35, speed=-0.04, size=[0.3, 0.06],
              life=10, color='#E3262F', glow=0.4, comment='в правый рукав'),
            E('flash', 40, at(-0.9, 0.92, 0.45), duration=6, size=0.6, color='@secondary'),
            E('flash', 40, at(0.68, 0.9, 0.6), duration=6, size=0.6, color='@secondary')]
    return 'irina', (T + '0–20 нити ползут из рукавов и оплетают печати Реплики (+0.06/+2.42/+4.82); 10 (bind) — затянулись; '
           '20 (break) — Ирина сжала ладонь: код Fx.stop экземпляра Реплики, сети рвутся алыми лоскутами; 22–40 лоскуты втягиваются в рукава. '
           'Лучей к заклинателю нет.'), 46, els


def fx_aris():
    T = 'T28 Арис ломает «Дезинтеграцию: Реплику» (caster = Арис, анимация animation.aris.replica_break 2.0 с). '
    HIT = (-0.25, 0.12, 1.35)
    els = [E('sigil', 2, at(0, 0.06, 0), id='aris_replica_hot', scale=4.5, until=23, comment='печать под ногами — заготовка: раскаляется'),
           E('flash', 13, at(*HIT), duration=10, size=2.8, rays=8, color='#FFC060', comment='strike: удар по печати-заготовке'),
           E('sprites', 13, at(*HIT), duration=2, texture='spark_soft', count=110, rate=60, spread=0.5, speed=0.42, gravity=0.09, size=[0.16, 0.04],
             life=18, color='#FFD27A', glow=0.7, comment='сноп искр'),
           E('wave', 13, at(0, 0.06, 0), duration=10, shape='ring', radius=4.6, thickness=0.6, followTerrain=True, color='#FF7A1E'),
           E('sigil', 14, at(0, 2.42, 0), id='aris_replica_hot', scale=3.4, until=23),
           E('sigil', 15, at(0, 4.82, 0), id='aris_replica_hot', scale=4.8, until=23),
           E('flash', 23, at(*HIT), duration=12, size=3.4, rays=10, color='#FFE2A0', comment='break: второй удар — печати плющатся и лопаются'),
           E('sprites', 23, at(*HIT), duration=2, texture='spark_soft', count=90, rate=50, spread=0.5, speed=0.5, gravity=0.1, size=[0.18, 0.04],
             life=20, color='#FFD27A', glow=0.7),
           E('flash', 23, at(0, 2.75, 0), duration=14, size=1.9, rays=6, color='@primary', comment='рога вспыхивают бирюзой'),
           E('sprites', 23, at(0, 2.8, 0), duration=6, texture='spark_soft', count=36, rate=8, spread=0.45, speed=0.06, gravity=-0.02, size=[0.14, 0.03],
             life=20, color='@primary', glow=0.6)]
    els += on_seals(lambda n, y, r, i: [
        E('sprites', 23 + i, at(0, y, 0), duration=4, texture='mote_ash', count=50, rate=14, area=r, speed=0.03, gravity=0.06, spin=120,
          size=[0.32, 0.14], life=30, color='#2A1E1C', blend='translucent', comment='окалина осыпается с печати ' + n),
        E('sprites', 23 + i, at(0, y, 0), duration=4, texture='mote_flame', count=34, rate=10, area=r, speed=0.04, gravity=0.04, size=[0.2, 0.05],
          life=22, color='#FF7A1E', glow=0.5)])
    els += [E('sprites', 30, at(0, 0.2, 0), duration=10, texture='mote_cloud', count=14, rate=2, area=2.5, speed=0.02, gravity=-0.01, size=[0.6, 1.2],
              life=30, color='#4A403C', blend='translucent', comment='дымок над остывшей окалиной')]
    return 'aris', (T + '2 — печать под ногами раскаляется; 13 (strike) — удар молотом как по заготовке: искры, звон, верхние печати тоже краснеют '
           'и плющатся (expand); 23 (break) — второй удар: код Fx.stop экземпляра Реплики, раскалённые печати раскалываются окалиной, рога вспыхивают.'), 48, els


def fx_martin():
    T = 'T29 Мартин ломает «Дезинтеграцию: Реплику» (caster = Мартин ×2, анимация martin_replica_break 2.2 с). '
    SH = (-0.9, 3.9, 0.8)
    els = [E('flash', 8, at(*SH), duration=8, size=2.6, rays=10, color='#FFF1C4', comment='block: Реплика принята на щит — лязг'),
           E('flash', 8, at(*SH), duration=6, size=1.4, color='#FF1934'),
           E('sprites', 8, at(*SH), duration=2, texture='spark_soft', count=80, rate=45, spread=0.4, speed=0.34, gravity=0.08, size=[0.18, 0.04],
             life=16, color='#FFE6A0', glow=0.7, comment='сноп искр от щита'),
           E('slash', 17, at(0, 3.4, 1.0), radius=5.4, arc=150, thickness=0.55, bend=1, tilt=55, dir=1, grow=4, life=12, secondary=0.6,
             color='@secondary', comment='slash: первый косой удар справа сверху'),
           E('slash', 26, at(0, 3.4, 1.0), radius=5.4, arc=150, thickness=0.55, bend=1, tilt=-55, dir=-1, grow=4, life=12, secondary=0.6,
             color='@secondary', comment='break: второй — крест-накрест'),
           E('flash', 26, at(0, 2.42, 0), duration=10, size=3.4, rays=10, color='#FF1934')]
    els += on_seals(lambda n, y, r, i: [
        E('sigil', 18, at(0, y, 0), id='martin_replica_cut_a', scale=r, until=30),
        E('sigil', 27, at(0, y, 0), id='martin_replica_cut_b', scale=r, until=29, comment='второй разрез раскалывает печать ' + n),
        E('sprites', 27, at(0, y, 0), duration=3, texture='spark_soft', count=46, rate=18, area=r, speed=0.06, gravity=0.05, spin=90,
          size=[0.24, 0.06], life=24, color='#FF1934', glow=0.6, comment='осколки печати гаснут'),
        E('sprites', 18, at(0, y, 0), duration=2, texture='spark_soft', count=20, rate=12, area=r * 0.8, speed=0.05, gravity=0.04,
          size=[0.16, 0.04], life=14, color='#FFF1C4', glow=0.6)])
    return 'martin', (T + '8 (block) — Реплику принимает на поднятый щит: лязг, сноп искр (призрачные солдаты — martin_soldier_brace в этот же тик); '
           '17 (slash) — первый косой удар, по печатям Реплики бежит разрез; 26 (break) — второй крест-накрест: код Fx.stop экземпляра Реплики, '
           'печати раскалываются по разрезам и гаснут.'), 54, els


def fx_ereb():
    T = 'T30 Эреб ломает «Дезинтеграцию: Реплику» (caster = Эреб, анимация ereb_replica_break 1.8 с). '
    els = [E('flash', 11, at(-0.35, 2.15, 0.1), duration=6, size=0.8, rays=4, color='#FFFFFF', comment='snap: щелчок пальцами')]
    els += on_seals(lambda n, y, r, i: [
        E('sigil', 11 + i, at(0, y, 0), id='ereb_replica_glass', scale=r, until=19, comment='печать %s становится стеклом' % n),
        E('wave', 12 + i, at(0, y, 0), duration=12, shape='ring', radius=r, thickness=0.35 * r, color='#BFE6FF', comment='рябь отражения'),
        E('sprites', 19, at(0, y, 0), duration=3, texture='mote_glass', count=46, rate=18, area=r, speed=0.05, gravity=0.06, spin=200, tumble=True,
          size=[0.24, 0.1], life=30, color='#BFE6FF', glow=0.4, comment='break: осыпается осколками'),
        E('sprites', 19 + i, at(0, y, 0), duration=6, texture='mote_butterfly', count=9 - 2 * i, rate=3, area=r * 0.85, speed=0.05, gravity=-0.015,
          sway=0.6, size=[0.34, 0.3], life=44, color='#BFE6FF', glow=0.45),
        E('sprites', 20 + i, at(0, y, 0), duration=6, texture='mote_butterfly_side', count=4, rate=2, area=r * 0.7, speed=0.04, gravity=-0.015,
          sway=0.6, size=[0.3, 0.26], life=40, color='#E8B84A', glow=0.45)])
    els += [E('flash', 19, at(0, 2.42, 0), duration=10, size=3.0, color='#E8F6FF')]
    return 'ereb', (T + '11 (snap) — щелчок: печати Реплики становятся стеклом, по ним бежит рябь; 19 (break) — код Fx.stop экземпляра Реплики, '
           'стекло трескается и осыпается осколками и бабочками; 24–30 — поклон.'), 44, els


FX = {'irina': fx_irina, 'aris': fx_aris, 'martin': fx_martin, 'ereb': fx_ereb}


def write_fx(boss):
    style, comment, dur, els = FX[boss]()
    _dump('fx/%s_replica_break.json' % boss, {'comment': comment, 'style': style, 'duration': dur, 'elements': els})


def run_assets(bosses=('irina', 'aris', 'martin', 'ereb')):
    """Текстуры, печати и fx (без анимаций). Генераторы боссов зовут это из своих gen_*_fx.py — идемпотентно."""
    textures()
    sigils()
    for b in bosses:
        write_fx(b)


# ================================================================== кадры docs/media/replica_break_all.jpg
def _tex_arr(name, size):
    for d in ('sigil', 'fx'):
        p = os.path.join(A, 'textures', d, name + '.png')
        if os.path.exists(p):
            im = Image.open(p).convert('RGBA')
            return im
    raise FileNotFoundError(name)


def _rgb(h):
    return np.array(hx(h)[:3], np.float32) / 255


def seal_image(sid, px=768):
    """Печать Реплики (sigils/<sid>.json) как плоская картинка: слои disc/band/arcs, тонированные, сложенные аддитивно.
    Возвращает (RGB-картинка, доля радиуса печати, которую занимает половина картинки)."""
    d = json.load(open(os.path.join(A, 'sigils', sid + '.json'), encoding='utf-8'))
    ext = max(l.get('radius', 1) for l in d['layers']) * 1.04
    acc = np.zeros((px, px, 3), np.float32)
    c = px / 2
    yy, xx = np.mgrid[0:px, 0:px]
    rr = np.hypot(xx - c, yy - c) / c * ext
    aa = (np.arctan2(yy - c, xx - c) / (2 * math.pi)) % 1.0
    for l in d['layers']:
        col = _rgb(l.get('color', d['color'])) * l.get('brightness', 1.0)
        R = l.get('radius', 1.0)
        if l['type'] == 'disc':
            s = max(2, int(round(px * R / ext)))
            t = np.asarray(_tex_arr(l['texture'], s).resize((s, s), Image.LANCZOS), np.float32) / 255
            a = t[..., 3:4] * t[..., :3].mean(axis=2, keepdims=True)
            o = int(round(c - s / 2))
            x0, y0, x1, y1 = max(0, o), max(0, o), min(px, o + s), min(px, o + s)
            acc[y0:y1, x0:x1] += a[y0 - o:y1 - o, x0 - o:x1 - o] * col
        elif l['type'] == 'band':
            inner = l.get('inner', 0.9) * R
            t = np.asarray(_tex_arr(l['texture'], 0), np.float32) / 255
            th, tw = t.shape[:2]
            m = (rr >= inner) & (rr <= R)
            u = ((aa * l.get('repeat', 8)) % 1.0 * (tw - 1)).astype(int)
            v = ((1 - (rr - inner) / max(1e-6, R - inner)).clip(0, 1) * (th - 1)).astype(int)
            a = t[v, u, 3] * m
            acc += a[..., None] * col
        elif l['type'] == 'arcs':
            w = l.get('width', 0.05)
            n, L = l.get('count', 4), l.get('arcLength', 50) / 360
            m = (np.abs(rr - R) < w / 2) & ((aa * n) % 1.0 < L * n)
            acc += m[..., None] * col * 0.3
    img = Image.fromarray(np.clip(acc * 255, 0, 255).astype(np.uint8))
    return img.filter(ImageFilter.GaussianBlur(0.6)), ext


def _replica_tex():
    out, ext = {}, {}
    for n, _, _ in SEALS:
        im, e = seal_image('disintegration_replica_' + n)
        out['rep_' + n], ext[n] = _png_b64(im), e
    return out, ext


H_BOSS = {'irina': 52, 'aris': 44, 'martin': 66, 'ereb': 34}


def _cam(boss, yaw=28, pitch=21, D=20.0, Y=2.3):
    return {'yaw': yaw, 'pitch': pitch, 'dist': D * 16 / H_BOSS[boss], 'ty': Y * 16}


def seals(ext, op=(0.85, 0.55, 0.85), sx=1, sz=1, color='#ffffff', only=None):
    out = []
    for (n, y, r), o in zip(SEALS, op):
        if o > 0 and (only is None or n in only):
            out.append({'k': 'seal', 'tex': 'rep_' + n, 'y': y, 'r': r * ext[n], 'op': o, 'sx': sx, 'sz': sz, 'color': color})
    return out


def overlay(tex, color, op=1.0, sx=1, sz=1, rot=0, which=(0, 1, 2), lift=0.03):
    return [{'k': 'seal', 'tex': tex, 'y': SEALS[i][1] + lift, 'r': SEALS[i][2], 'op': op, 'color': color, 'sx': sx, 'sz': sz, 'rot': rot,
             'order': 1} for i in which]


def spr(tex, n, at, spread=(0, 0, 0), size=(0.2, 0.3), color='#ffffff', op=1.0, seed=7, spin=0.6, ring=None, normal=False):
    o = {'k': 'spr', 'tex': tex, 'n': n, 'at': list(at), 'spread': list(spread), 'size': list(size), 'color': color, 'op': op, 'seed': seed,
         'spin': spin}
    if ring:
        o['ring'] = list(ring)
    if normal:
        o['normal'] = True
    return o


def glow(at, size, color, op=0.9):
    return spr('glow', 1, at, size=(size, size), color=color, op=op, spin=0)


def helix(x0, y0, y1, r0, r1, turns, phase=0.0, n=60, z0=0.0):
    pts = []
    for i in range(n + 1):
        u = i / n
        a = phase + turns * 2 * math.pi * u
        r = r0 + (r1 - r0) * u
        pts.append([x0 + r * math.cos(a), y0 + (y1 - y0) * u, z0 + r * math.sin(a)])
    return pts


def arc_pts(c, R, tilt, span=150, n=40, fwd=1.0):
    t = math.radians(tilt)
    u = (math.cos(t), math.sin(t), 0.0)
    pts = []
    for i in range(n + 1):
        a = math.radians(-span / 2 + span * i / n)
        pts.append([c[0] + R * math.sin(a) * u[0], c[1] + R * math.sin(a) * u[1], c[2] + fwd * R * math.cos(a) * 0.55])
    return pts


def frames():
    """3 кадра на босса (до / break / после). Возвращает {босс: [ячейки]}."""
    _, ext = _replica_tex()
    RED, HOT, SPARK = '#E3262F', '#FF6A1E', '#FFD27A'
    F = {}
    # ---------------------------------------------------------------- Ирина
    cam = _cam('irina')
    threads = []
    for k, (y1, r1) in enumerate(((0.1, 4.3), (2.45, 3.2), (4.85, 4.6), (2.45, 3.3), (4.85, 4.5), (0.1, 4.4))):
        sx_ = -0.5 if k % 2 == 0 else 0.5
        threads.append({'k': 'tube', 'pts': helix(0, 1.4, y1, 0.55, r1, 0.75 + 0.1 * k, phase=k * 2.1), 'w': 0.022, 'color': RED, 'op': 0.9})
    for i, (n, y, r) in enumerate(SEALS):
        threads.append({'k': 'tube', 'pts': helix(0, y + 0.08, y + 0.12, r * 0.98, r * 0.98, 1.0, phase=i, n=90), 'w': 0.04, 'color': RED,
                        'op': 0.9, 'closed': True})
    F['irina'] = [
        dict(cam, anim='irina_replica_break', t=0.55, label='Ирина — до разрыва', sub='0.5 с (bind): нити оплели печати Реплики',
             rbfx=seals(ext) + overlay('irina_replica_web', RED, 1.0) + threads + [glow([-0.55, 2.03, 0.74], 0.9, RED)]),
        dict(cam, anim='irina_replica_break', t=1.0, label='break — 1.0 с', sub='сжала ладонь: печати рвутся алыми лоскутами',
             rbfx=seals(ext, (0.55, 0.35, 0.55)) + overlay('irina_replica_web', RED, 0.45, sx=1.08, sz=1.08) +
             [glow([0, y, 0], 1.6 * r, '#FF1934', 0.28) for _, y, r in SEALS] +
             [spr('mote_thread', 70, [0, y, 0], (0, 0.25, 0), (0.35, 0.6), RED, 1.0, seed=11 + i, spin=3, ring=(0.35 * r, r))
              for i, (_, y, r) in enumerate(SEALS)] +
             [spr('spark_soft', 40, [0, y, 0], (0, 0.2, 0), (0.12, 0.22), '#FF1934', 0.9, seed=21 + i, ring=(0.5 * r, r))
              for i, (_, y, r) in enumerate(SEALS)] + [glow([-0.11, 1.11, 0.78], 0.8, '#FFE0E6', 0.8)]),
        dict(cam, anim='irina_replica_break', t=1.45, label='после — 1.45 с', sub='лоскуты-нити втягиваются в её рукава',
             rbfx=[spr('mote_thread', 26, [0, 0.9 + 0.75 * k, 0], (0, 0.15, 0), (0.3, 0.5), RED, 0.95, seed=40 + k, spin=3,
                       ring=(0.5 + 0.45 * k, 0.9 + 0.55 * k)) for k in range(5)] +
             [{'k': 'tube', 'pts': helix(0, 4.2 - 0.3 * k, 1.45, 3.4 - 0.2 * k, 0.45, -1.3, phase=k * 1.25), 'w': 0.03, 'color': RED,
               'op': 0.85} for k in range(5)] +
             [glow([-0.97, 0.97, 0.4], 0.7, '#B99BE0', 0.8), glow([0.69, 0.89, 0.6], 0.7, '#B99BE0', 0.8)])]
    # ---------------------------------------------------------------- Арис
    cam = _cam('aris')
    HIT = [-0.25, 0.12, 1.35]
    F['aris'] = [
        dict(cam, model='aris', anim='animation.aris.replica_break', t=0.66, label='Арис — удар по заготовке',
             sub='0.65 с (strike): искры, звон; печать под ногами раскалилась',
             rbfx=seals(ext) + overlay('aris_replica_hot', HOT, 1.0, which=(0,)) + overlay('glow', HOT, 0.5, which=(0,)) +
             [glow(HIT, 2.4, '#FFC060', 0.95), spr('spark_soft', 120, [HIT[0], 0.7, HIT[2]], (1.2, 0.7, 1.0), (0.08, 0.16), SPARK, 1.0, seed=3)]),
        dict(cam, model='aris', anim='animation.aris.replica_break', t=1.16, label='break — 1.15 с',
             sub='второй удар: печати сплющены, докрасна; рога вспыхнули',
             rbfx=seals(ext, (0.45, 0.4, 0.45), sx=1.14, sz=0.9, color='#FF9060') +
             overlay('aris_replica_hot', HOT, 1.0, sx=1.14, sz=0.9) + overlay('glow', HOT, 0.4, sx=1.14, sz=0.9) +
             [glow(HIT, 3.0, '#FFE2A0', 1.0), spr('spark_soft', 110, [HIT[0], 0.8, HIT[2]], (1.4, 0.8, 1.1), (0.08, 0.16), SPARK, 1.0, seed=5),
              glow([0, 2.75, 0], 1.9, '#3CD6E0', 0.95), spr('spark_soft', 30, [0, 2.9, 0], (0.6, 0.4, 0.4), (0.06, 0.12), '#3CD6E0', 1.0, seed=6)]),
        dict(cam, model='aris', anim='animation.aris.replica_break', t=1.5, label='после — 1.5 с', sub='печати осыпаются окалиной, угли гаснут',
             rbfx=[spr('mote_ash', 60, [0, y - 0.6, 0], (0, 0.9, 0), (0.22, 0.4), '#2A1E1C', 0.95, seed=60 + i, spin=3, ring=(0.3 * r, r), normal=True)
                   for i, (_, y, r) in enumerate(SEALS)] +
             [spr('mote_flame', 40, [0, y - 0.5, 0], (0, 0.8, 0), (0.1, 0.2), '#FF7A1E', 0.95, seed=70 + i, ring=(0.3 * r, r))
              for i, (_, y, r) in enumerate(SEALS)] +
             overlay('aris_replica_hot', '#7A2A10', 0.35, which=(0,), sx=1.14, sz=0.9) +
             [glow([0, 2.75, 0], 1.2, '#3CD6E0', 0.6)])]
    # ---------------------------------------------------------------- Мартин (×2)
    cam = _cam('martin', D=21, Y=2.6)
    SH = [-0.9, 3.9, 0.8]
    soldiers = [{'model': 'martin_soldier', 'anim': 'martin_soldier_brace', 't': 0.6, 'pos': [x, 0, 3.0], 'ry': 0} for x in (-3.6, 3.6)]
    soldiers_idle = [dict(s, anim='martin_soldier_idle', t=0.4) for s in soldiers]
    F['martin'] = [
        dict(cam, model='martin', anim='martin_replica_break', t=0.42, models=soldiers_idle, label='Мартин — Реплика на щит',
             sub='0.4 с (block): лязг, сноп искр',
             rbfx=seals(ext) + [glow(SH, 2.4, '#FFF1C4', 1.0), glow(SH, 1.3, '#FF1934', 0.8),
                                spr('spark_soft', 110, SH, (1.0, 0.8, 0.8), (0.08, 0.16), '#FFE6A0', 1.0, seed=8)]),
        dict(cam, model='martin', anim='martin_replica_break', t=1.36, models=soldiers, label='break — 1.35 с',
             sub='крест-накрест двуручником; солдаты подняли щиты',
             rbfx=seals(ext, (0.6, 0.4, 0.6)) + overlay('martin_replica_cut_a', '#FFF1C4', 1.0) + overlay('martin_replica_cut_b', '#FFF1C4', 1.0, lift=0.05) +
             [{'k': 'tube', 'pts': arc_pts([0, 3.2, 1.2], 2.6, 55, span=120), 'w': 0.06, 'color': '#FFF1C4', 'op': 0.5},
              {'k': 'tube', 'pts': arc_pts([0, 3.2, 1.2], 2.6, -55, span=120), 'w': 0.08, 'color': '#FFF1C4', 'op': 0.95},
              glow([0, 2.42, 0], 5, '#FF1934', 0.45)] +
             [spr('spark_soft', 50, [0, y, 0], (0, 0.2, 0), (0.12, 0.22), '#FF1934', 0.95, seed=80 + i, ring=(0.2 * r, r))
              for i, (_, y, r) in enumerate(SEALS)]),
        dict(cam, model='martin', anim='martin_replica_break', t=1.75, models=soldiers, label='после — 1.75 с',
             sub='печати раскалываются по разрезам и гаснут',
             rbfx=[spr('spark_soft', 50, [0, y - 0.5, 0], (0, 0.7, 0), (0.12, 0.24), '#FF1934', 0.75, seed=90 + i, ring=(0.4 * r, r))
                   for i, (_, y, r) in enumerate(SEALS)] +
             [{'k': 'seal', 'tex': 'rep_%s' % n, 'y': y - 0.15 - 0.25 * q, 'r': r * ext[n] * 0.5, 'op': 0.28, 'x': dx * r * 0.5, 'z': dz * r * 0.5,
               'rot': 40 * q, 'tilt': [18 * dx, 14 * dz]}
              for (n, y, r) in SEALS for q, (dx, dz) in enumerate(((0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)))] +
             overlay('martin_replica_cut_b', '#FFF1C4', 0.25, lift=0.05))]
    # ---------------------------------------------------------------- Эреб
    cam = _cam('ereb')
    GLASS = '#BFE6FF'
    F['ereb'] = [
        dict(cam, model='ereb', anim='ereb_replica_break', t=0.62, label='Эреб — щелчок', sub='0.55 с (snap): печати стали стеклом, рябь отражения',
             rbfx=seals(ext, (0.45, 0.3, 0.45)) + overlay('ereb_replica_glass', GLASS, 0.95) +
             [{'k': 'seal', 'tex': 'thin_ring', 'y': y + 0.05, 'r': r * 0.75, 'op': 0.8, 'color': '#FFFFFF'} for _, y, r in SEALS] +
             [glow([-0.35, 2.15, 0.1], 0.9, '#FFFFFF', 0.9)]),
        dict(cam, model='ereb', anim='ereb_replica_break', t=0.96, label='break — 0.95 с', sub='стекло трескается и осыпается',
             rbfx=seals(ext, (0.25, 0.15, 0.25)) + overlay('ereb_replica_glass', GLASS, 0.7, sx=1.05, sz=1.05) +
             overlay('higher_cracks', '#FFFFFF', 0.9, lift=0.06) +
             [spr('mote_glass', 60, [0, y, 0], (0, 0.35, 0), (0.18, 0.34), GLASS, 1.0, seed=100 + i, spin=3, ring=(0.3 * r, r))
              for i, (_, y, r) in enumerate(SEALS)] + [glow([0, 2.42, 0], 4.5, '#E8F6FF', 0.35)]),
        dict(cam, model='ereb', anim='ereb_replica_break', t=1.35, label='после — 1.35 с', sub='осколки и бабочки; лёгкий поклон',
             rbfx=[spr('mote_glass', 45, [0, y - 0.8, 0], (0, 0.9, 0), (0.16, 0.3), GLASS, 0.9, seed=110 + i, spin=3, ring=(0.3 * r, r))
                   for i, (_, y, r) in enumerate(SEALS)] +
             [spr('mote_butterfly', 9, [0, y + 0.3, 0], (0, 0.6, 0), (0.4, 0.55), GLASS, 0.95, seed=120 + i, spin=0.5, ring=(0.4 * r, 0.9 * r))
              for i, (_, y, r) in enumerate(SEALS)] +
             [spr('mote_butterfly_side', 5, [0, y + 0.4, 0], (0, 0.5, 0), (0.35, 0.5), '#E8B84A', 0.95, seed=130 + i, spin=0.5,
                  ring=(0.4 * r, 0.8 * r)) for i, (_, y, r) in enumerate(SEALS)])]
    return F


NAMES = {'irina': 'Ирина (T27)', 'aris': 'Арис (T28)', 'martin': 'Мартин (T29)', 'ereb': 'Эреб (T30)'}


def shots(three=None, only=None):
    tex, _ = _replica_tex()
    F = frames()
    rows = []
    for b in ('irina', 'aris', 'martin', 'ereb'):
        if only and b not in only:
            continue
        out = os.path.join(MEDIA, '_rb_%s.jpg' % b)
        render(b, F[b], out, three, cols=3, size=(1800, 640), extra_tex=tex)
        rows.append((b, Image.open(out).convert('RGB')))
        os.remove(out)
    W = 1800
    head = 56
    sheet = Image.new('RGB', (W, head + sum(im.height + 34 for _, im in rows)), (14, 12, 16))
    d = ImageDraw.Draw(sheet)
    fp = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    f1 = ImageFont.truetype(fp, 26) if os.path.exists(fp) else ImageFont.load_default()
    f2 = ImageFont.truetype(fp, 19) if os.path.exists(fp) else ImageFont.load_default()
    d.text((16, 14), 'Боссы культа ломают «Дезинтеграцию: Реплику» — до / break / после (масштаб как в игре: печати Реплики r 4.5 / 3.4 / 4.8 '
                     'на +0 / +2.4 / +4.8)', font=f2, fill=(236, 228, 220))
    y = head
    for b, im in rows:
        d.text((16, y + 6), NAMES[b] + ' — ' + ANIM_NAME[b] + ', fx ' + b + '_replica_break', font=f2, fill=(255, 196, 160))
        sheet.paste(im, (0, y + 34))
        y += im.height + 34
    p = os.path.join(MEDIA, 'replica_break_all.jpg' if not only else '_rb_check.jpg')
    sheet.save(p, quality=90)
    print('wrote', os.path.relpath(p, ROOT))


if __name__ == '__main__':
    args = sys.argv[1:]
    for b in ('irina', 'aris', 'martin', 'ereb'):
        patch_anim_file(b)
    run_assets()
    if '--shots' in args:
        shots(_three(args))
    print('\n'.join('  ' + w for w in WRITTEN))
