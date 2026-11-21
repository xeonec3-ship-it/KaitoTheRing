#!/usr/bin/env python3
"""
T26: коса «Главы Культа Меллисто» — объёмная, детализированная (владелец 20.11), В ЦВЕТАХ косы Тироса (decrepit_scythe Iron's:
тёмно-бордовое древко, серо-бурое лезвие). Модель из брусков в той же плоскости и пропорциях, что плоский спрайт Iron's 16×16
(древко по диагонали снизу-слева вверх-вправо, лезвие-полумесяц сверху влево), поэтому дисплей берём как у template_verylarge_sword (×3).
  models/item/cult_scythe.json — в руке 3D, в GUI — плоская иконка Iron's (decrepit_scythe_gui), forge:separate_transforms.
  textures/item/cult_scythe_3d.png — палитра (каждый цвет — клетка 1×1).
Предмет pohsmp_core:cult_scythe регистрирует код и даёт его боссу вместо DECREPIT_SCYTHE.
Превью: tools/cult_scythe_preview.html. Запуск: python3 tools/gen_cult_scythe.py
"""
import json, math, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
PAL = {   # владелец 20.11: в обеих фазах — как облик души босса: тёмное древко и сталь, золото венца (палитра cult_leader_soul_mode)
    'k': '#120d0e', 'w0': '#1b1415', 'w1': '#26252b', 'w2': '#2e2a2f', 'w3': '#393737', 'w4': '#9c5e2c',
    'b0': '#1b1415', 'b1': '#26252b', 'b2': '#b9892e', 'b3': '#d6af39', 'b4': '#e8e895', 'b5': '#f6f2c4',
}
CELL = {k: (i % 16, i // 16) for i, k in enumerate(PAL)}
R3 = lambda v: round(v, 3)
ANG = (-45, -22.5, 0, 22.5, 45)


class M:
    def __init__(self):
        self.el = []

    def box(self, cx, cy, cz, sx, sy, sz, col, ang=0.0, side=None):
        a = min(ANG, key=lambda q: abs(q - ang))
        faces = {}
        for f in ('north', 'south', 'east', 'west', 'up', 'down'):
            u, v = CELL[(side or {}).get(f, col)]
            faces[f] = {'uv': [u + .25, v + .25, u + .75, v + .75], 'texture': '#p'}
        e = {'from': [R3(cx - sx / 2), R3(cy - sy / 2), R3(cz - sz / 2)], 'to': [R3(cx + sx / 2), R3(cy + sy / 2), R3(cz + sz / 2)], 'faces': faces}
        if a:
            e['rotation'] = {'axis': 'z', 'angle': a, 'origin': [R3(cx), R3(cy), R3(cz)]}
        self.el.append(e)

    def seg(self, p, q, w, d, col, z=8.0, side=None):
        """Брусок вдоль отрезка p→q (в плоскости xy), толщина w поперёк, глубина d."""
        cx, cy = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        ang = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
        ang = (ang + 90) % 180 - 90                      # брусок симметричен: направление «влево» = «вправо»
        a = min(ANG, key=lambda x: abs(x - ang)) if abs(ang) <= 67.5 else None
        if a is None:   # почти вертикаль: брусок по y
            self.box(cx, cy, z, w, L, d, col, ang - 90 if ang > 0 else ang + 90, side)
        else:
            self.box(cx, cy, z, L + w * 0.3, w, d, col, ang, side)


def build():
    m = M()
    Z = 8.0
    # --- древко: диагональ от (1.6,1.6) к (11.2,11.2), 45°
    s0, s1 = (1.6, 1.6), (11.2, 11.2)
    m.seg(s0, s1, 0.62, 0.62, 'w1', Z, side={'up': 'w3', 'north': 'w3'})
    m.seg((s0[0] + .05, s0[1] + .25), (s1[0] - .25, s1[1] - .05), 0.18, 0.66, 'w3', Z)        # блик по ребру
    # обмотка: кольца с шагом, ближе к низу — хват
    for i in range(9):
        t = 0.08 + i * 0.045
        x, y = s0[0] + (s1[0] - s0[0]) * t, s0[1] + (s1[1] - s0[1]) * t
        m.box(x, y, Z, 0.36, 0.86, 0.78, 'w4' if i % 2 else 'w2', 45)
    for t in (0.55, 0.72):                                                                       # стальные кольца по древку
        x, y = s0[0] + (s1[0] - s0[0]) * t, s0[1] + (s1[1] - s0[1]) * t
        m.box(x, y, Z, 0.3, 0.92, 0.84, 'b3', 45, side={'north': 'b4'})
    # подток: шип внизу
    m.seg((1.6, 1.6), (0.6, 0.6), 0.5, 0.5, 'b1', Z)
    m.seg((0.6, 0.6), (0.1, 0.1), 0.26, 0.3, 'b3', Z)
    m.box(1.3, 0.8, Z, 0.9, 0.3, 0.5, 'k', 0)                                                   # перекладина-крюк у подтока
    # --- навершие: ступица на конце древка
    hx, hy = 11.6, 11.6
    m.box(hx, hy, Z, 1.5, 1.5, 1.1, 'b1', 45, side={'north': 'b2', 'up': 'b2'})
    m.box(hx, hy, Z, 1.0, 1.0, 1.25, 'w3', 45)
    m.box(hx + .35, hy + .35, Z, 0.5, 0.5, 1.3, 'b4', 0)                                       # заклёпка
    # «рог» за ступицей вниз-вправо (крюк, как у спрайта)
    hook = [(12.3, 12.0), (13.3, 11.6), (14.0, 10.8), (14.3, 9.8), (14.1, 9.0)]
    for i in range(len(hook) - 1):
        w = 0.7 - i * 0.12
        m.seg(hook[i], hook[i + 1], w, 0.48, 'b1' if i < 2 else 'b0', Z, side={'up': 'b2'})
    # --- лезвие-полумесяц: от ступицы влево-вверх, дугой к острию слева
    # ломаная по разрешённым углам Minecraft (−45…45 с шагом 22.5): направления влево-вверх → влево → влево-вниз
    heads = [157.5, 157.5, 180, 180, 180, 202.5, 202.5, 225]
    lens = [1.2, 1.1, 1.2, 1.2, 1.1, 1.0, 0.9, 0.8]
    pts = [(12.2, 12.3)]
    for h, l in zip(heads, lens):
        x, y = pts[-1]
        pts.append((x + l * math.cos(math.radians(h)), y + l * math.sin(math.radians(h))))
    N = len(heads)
    for i in range(N):
        t = (i + .5) / N
        p, q = pts[i], pts[i + 1]
        spine = 0.46 * (1 - 0.5 * t)
        body = 1.6 * (1 - t ** 1.5) + 0.2                                                       # ширина лезвия вниз от обуха
        # нормаль «вниз» от обуха для этого сегмента
        dx, dy = q[0] - p[0], q[1] - p[1]; L = math.hypot(dx, dy); nx, ny = dy / L, -dx / L
        if ny > 0: nx, ny = -nx, -ny
        off = lambda k: ((p[0] + nx * k, p[1] + ny * k), (q[0] + nx * k, q[1] + ny * k))
        m.seg(*off(-spine * .4), spine, 0.5, 'b2', Z, side={'up': 'b4', 'north': 'b3'})        # обух
        m.seg(*off(body / 2), body, 0.34, 'b1', Z, side={'north': 'b2', 'south': 'b2'})        # тело
        if t < 0.75:
            m.seg(*off(body * .38), 0.16, 0.38, 'b0', Z)                                         # дол
        m.seg(*off(body), 0.16, 0.18, 'b5' if t > .1 else 'b4', Z)                             # кромка
        if 0.1 < t < 0.5:                                                                        # зазубрины у пяты
            a, b = off(body + .18)
            m.box((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, Z, 0.22, 0.3, 0.14, 'b3', -22.5)
    # острие
    tx, ty = pts[-1]
    m.seg((tx, ty), (tx - .7, ty - .55), 0.18, 0.16, 'b5', Z)
    # руны-насечки на обухе у пяты (тёмные точки)
    for i in (1, 2, 3):
        m.box(pts[i][0], pts[i][1] - .45, Z, 0.18, 0.18, 0.4, 'k', 0)
    return m.el


def main():
    pal = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for k, (x, y) in CELL.items():
        h = PAL[k]
        pal.putpixel((x, y), (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255))
    pal.save(os.path.join(A, 'textures', 'item', 'cult_scythe_3d.png'))
    els = build()
    T = {   # дисплей template_verylarge_sword Iron's (тот же размер и хват, что у косы Тироса), толщина z не сжимается — модель объёмная
        # хват на 3 px ближе к подтоку, вдоль древка (21.11): у хвата Тироса лезвие иначе касается земли при покачивании руки;
        # сдвиг — здесь, в модели предмета (одинаково во всех кадрах), а не ключами кисти (они отрывали косу от кулака)
        'thirdperson_righthand': {'rotation': [0, -90, 55], 'translation': [0, 5.546, 0.521], 'scale': [3, 3, 3]},
        'thirdperson_lefthand': {'rotation': [0, 90, -55], 'translation': [0, 5.546, 0.521], 'scale': [3, 3, 3]},
        'firstperson_righthand': {'rotation': [0, -90, 25], 'translation': [1.13, 7.2, 1.13], 'scale': [1.7, 1.7, 1.7]},
        'firstperson_lefthand': {'rotation': [0, 90, -25], 'translation': [1.13, 7.2, 1.13], 'scale': [1.7, 1.7, 1.7]},
        'head': {'rotation': [0, 0, 0], 'scale': [1.6, 1.6, 1.6]},
    }
    flat = {'parent': 'minecraft:item/handheld', 'textures': {'layer0': 'irons_spellbooks:item/decrepit_scythe_gui'}}
    doc = {'loader': 'forge:separate_transforms', 'gui_light': 'front',
           'base': {'textures': {'p': 'pohsmp_core:item/cult_scythe_3d', 'particle': 'irons_spellbooks:item/decrepit_scythe'},
                    'elements': els, 'display': T},
           'perspectives': {'gui': flat, 'ground': flat, 'fixed': flat}}
    with open(os.path.join(A, 'models', 'item', 'cult_scythe.json'), 'w', encoding='utf-8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print('wrote models/item/cult_scythe.json', len(els), 'elements')
    # превью
    js = [[e['from'], e['to'], PAL[next(k for k, c in CELL.items() if c == (int(e['faces']['north']['uv'][0]), int(e['faces']['north']['uv'][1])))],
           e.get('rotation')] for e in els]
    html = '''<!doctype html><meta charset="utf-8"><title>Коса Главы Культа</title><style>body{margin:0;background:#262a33}</style><body>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script><script>
const D=%s;const W=innerWidth,H=innerHeight;const R=new THREE.WebGLRenderer({antialias:true});R.setSize(W,H);document.body.appendChild(R.domElement);
const S=new THREE.Scene();S.background=new THREE.Color(0x262a33);S.add(new THREE.AmbientLight(0xffffff,.55));const L=new THREE.DirectionalLight(0xffffff,.8);L.position.set(-3,5,6);S.add(L);
const C=new THREE.PerspectiveCamera(30,W/H,.1,200);let yaw=.3,pitch=.1;const G=new THREE.Group();
for(const [a,b,col,rot] of D){const m=new THREE.Mesh(new THREE.BoxGeometry(b[0]-a[0],b[1]-a[1],b[2]-a[2]),new THREE.MeshLambertMaterial({color:col}));
 const c=[(a[0]+b[0])/2,(a[1]+b[1])/2,(a[2]+b[2])/2];
 if(rot){const p=new THREE.Group();p.position.set(rot.origin[0]-8,rot.origin[1]-8,rot.origin[2]-8);p.rotation.z=rot.angle*Math.PI/180;m.position.set(c[0]-rot.origin[0],c[1]-rot.origin[1],c[2]-rot.origin[2]);p.add(m);G.add(p);}
 else{m.position.set(c[0]-8,c[1]-8,c[2]-8);G.add(m);}}
S.add(G);window.setView=(y,p)=>{yaw=y;pitch=p};
function f(){const d=30;C.position.set(Math.sin(yaw)*Math.cos(pitch)*d,Math.sin(pitch)*d,Math.cos(yaw)*Math.cos(pitch)*d);C.lookAt(0,0,0);R.render(S,C);requestAnimationFrame(f)}f();
</script>''' % json.dumps(js)
    with open(os.path.join(HERE, 'cult_scythe_preview.html'), 'w', encoding='utf-8') as f:
        f.write(html)


if __name__ == '__main__':
    main()
