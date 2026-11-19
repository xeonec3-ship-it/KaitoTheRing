#!/usr/bin/env python3
"""
T14 «Раскалённые угли» — объёмный ВАРИАНТ меча (на выбор владельца), обычная модель предмета из брусков (без кода):
  models/item/ember_blade_3d.json, ember_blade_hot_3d.json — в руке 3D, в инвентаре/на земле (gui, ground, fixed) — плоская иконка
  (`forge:separate_transforms`); раскалённый клинок светится сам (`forge_data`: block_light/sky_light 15).
  textures/item/ember_blade_3d.png — палитра 16×16 (каждый цвет — один пиксель, грани берут uv своей клетки).
По референсу «Ruination»: длинный однолезвийный изогнутый клинок с приподнятым остриём (обух толще, кромка тоньше, дол, руны у пяты),
пята с крюком к обуху, круглая рукоять в спиральной обмотке, расширенное навершие.
Подключить вместо плоского: в models/item/ember_blade.json заменить содержимое на «parent: pohsmp_core:item/ember_blade_3d» (и hot так же).
Превью: tools/ember_blade_3d_preview.html. Запуск: python3 tools/gen_ember_blade_3d.py
"""
import json
import math
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')

# палитра: имя → клетка (x, y) на 16×16
PAL = {
    'leather0': '#0C0A09', 'leather1': '#1E1A18', 'leather2': '#342E2B', 'leather3': '#4C4440',
    'iron0': '#101014', 'iron1': '#1E1E24', 'iron2': '#2E2E36', 'iron3': '#44444E', 'iron4': '#5E5E68', 'iron5': '#7E7E8A',
    'iron6': '#A6A6B0', 'iron7': '#D2D2DA', 'rune': '#9C9CAA',
    'hot0': '#3A0600', 'hot1': '#6A1004', 'hot2': '#A82408', 'hot3': '#E04A0C', 'hot4': '#FF7A1E', 'hot5': '#FFA83A',
    'hot6': '#FFD27A', 'hot7': '#FFF2C0',
}
CELL = {k: (i % 16, i // 16) for i, k in enumerate(PAL)}
R3 = lambda v: round(v, 3)


def palette_png():
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for k, (x, y) in CELL.items():
        h = PAL[k]
        im.putpixel((x, y), (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), 255))
    im.save(os.path.join(A, 'textures', 'item', 'ember_blade_3d.png'))


class Model:
    def __init__(self):
        self.el = []

    def box(self, x0, y0, z0, x1, y1, z1, col, side=None, rot=None, glow=False, name=None):
        """col — цвет всех граней; side — {'north': 'iron6', ...} — свой цвет у отдельных граней. rot: (axis, angle, origin)."""
        faces = {}
        for f in ('north', 'south', 'east', 'west', 'up', 'down'):
            c = (side or {}).get(f, col)
            u, v = CELL[c]
            fd = {'uv': [u + 0.25, v + 0.25, u + 0.75, v + 0.75], 'texture': '#p'}
            if glow:
                fd['forge_data'] = {'block_light': 15, 'sky_light': 15}
            faces[f] = fd
        e = {'from': [R3(min(x0, x1)), R3(min(y0, y1)), R3(min(z0, z1))], 'to': [R3(max(x0, x1)), R3(max(y0, y1)), R3(max(z0, z1))],
             'faces': faces}
        if name:
            e['name'] = name
        if rot:
            e['rotation'] = {'axis': rot[0], 'angle': rot[1], 'origin': [R3(v) for v in rot[2]]}
        self.el.append(e)

    def cbox(self, cx, cy, cz, sx, sy, sz, col, **kw):
        self.box(cx - sx / 2, cy - sy / 2, cz - sz / 2, cx + sx / 2, cy + sy / 2, cz + sz / 2, col, **kw)


def build(hot):
    m = Model()
    CX, CZ = 8.0, 8.0
    # --- навершие (y 1.2–3.6): расширенная головка, гранёная
    m.cbox(CX, 2.0, CZ, 3.4, 1.4, 3.0, 'iron3', side={'up': 'iron4', 'down': 'iron1'}, name='pommel')
    m.cbox(CX, 2.0, CZ, 2.6, 1.6, 3.6, 'iron2')
    m.cbox(CX, 1.0, CZ, 2.2, 0.6, 2.2, 'iron1')
    m.cbox(CX, 3.2, CZ, 2.4, 0.8, 2.4, 'iron4')
    # --- рукоять (y 3.6–10): восьмигранная (две скрещённые призмы) + спиральная обмотка
    m.cbox(CX, 6.8, CZ, 2.0, 6.4, 1.4, 'leather1', name='grip')
    m.cbox(CX, 6.8, CZ, 1.4, 6.4, 2.0, 'leather1')
    y = 4.0
    k = 0
    while y < 9.6:
        m.cbox(CX, y + 0.3, CZ, 2.25, 0.55, 2.25, 'leather3' if k % 2 else 'leather2', rot=('z', 22.5, (CX, y + 0.3, CZ)))
        y += 0.95
        k += 1
    # --- пята (y 10–12): шейка, крюк к обуху (−x), кольцо-ободок
    m.cbox(CX, 10.4, CZ, 2.6, 0.8, 2.4, 'iron2', side={'up': 'iron4'}, name='guard')
    m.cbox(CX - 0.2, 11.4, CZ, 3.6, 1.2, 1.4, 'iron3', side={'up': 'iron5', 'west': 'iron4'})
    m.cbox(CX - 2.2, 12.0, CZ, 1.0, 1.8, 1.0, 'iron3', rot=('z', 22.5, (CX - 2.2, 12.0, CZ)))      # крюк
    m.cbox(CX - 2.7, 13.0, CZ, 0.7, 0.9, 0.8, 'iron4', rot=('z', 45, (CX - 2.7, 13.0, CZ)))
    # --- клинок (y 12.6–32): сегменты по 1.25, изгиб — смещение по x; обух (−x) толстый, тело, дол, кромка (+x) тонкая
    n, y0, y1 = 16, 12.6, 32.0
    seg = (y1 - y0) / n
    for i in range(n):
        t = (i + 0.5) / n
        ya, yb = y0 + i * seg, y0 + (i + 1) * seg + 0.05
        bend = -1.3 * math.sin(t * math.pi * 0.9) + 1.2 * t ** 3              # обух выгнут, остриё чуть приподнято к кромке
        w = 3.8 * (1 - t ** 2.1) + 0.5                                          # ширина клинка (к острию сужается)
        spine_x0 = CX - 1.4 + bend
        edge_x1 = spine_x0 + w
        if hot:
            c_sp, c_body, c_full, c_edge = 'hot1', ('hot3' if t < 0.35 else 'hot4'), ('hot4' if t < 0.35 else 'hot5'), 'hot7'
        else:
            c_sp, c_body, c_full, c_edge = 'iron1', 'iron3', 'iron5', 'iron7'
        g = hot
        sp_w = min(0.9, w * 0.3)
        m.box(spine_x0, ya, CZ - 0.5, spine_x0 + sp_w, yb, CZ + 0.5, c_sp, side={'west': 'iron2' if not hot else 'hot2'}, glow=g)   # обух
        m.box(spine_x0 + sp_w, ya, CZ - 0.38, edge_x1 - w * 0.25, yb, CZ + 0.38, c_body, glow=g)                                       # тело
        m.box(spine_x0 + sp_w + 0.2, ya, CZ - 0.42, spine_x0 + sp_w + 0.2 + max(0.3, w * 0.18), yb, CZ + 0.42,
              c_full if not hot else 'hot6', glow=g)                                                                                     # дол
        m.box(edge_x1 - w * 0.25, ya, CZ - 0.22, edge_x1, yb, CZ + 0.22, c_edge, glow=g)                                                # кромка
        if i < 5:                                                                       # руны у пяты — по обеим сторонам
            for zz in (CZ - 0.47, CZ + 0.41):
                m.box(spine_x0 + sp_w + 0.6, ya + 0.25, zz, spine_x0 + sp_w + 0.95, yb - 0.35, zz + 0.06, 'hot7' if hot else 'rune', glow=g)
    # остриё
    bend1 = -1.3 * math.sin(math.pi * 0.9) + 1.2
    tx = CX - 1.4 + bend1
    m.box(tx, 31.8, CZ - 0.3, tx + 0.9, 32.0, CZ + 0.3, 'hot7' if hot else 'iron6', glow=hot)
    flat = 'pohsmp_core:item/ember_blade_hot' if hot else 'pohsmp_core:item/ember_blade'
    base = {
        'textures': {'p': 'pohsmp_core:item/ember_blade_3d', 'particle': flat},
        'elements': m.el,
        'display': {
            'thirdperson_righthand': {'rotation': [0, -90, 10], 'translation': [0, 1.5, 0.5], 'scale': [0.85, 0.85, 0.85]},
            'thirdperson_lefthand': {'rotation': [0, 90, -10], 'translation': [0, 1.5, 0.5], 'scale': [0.85, 0.85, 0.85]},
            'firstperson_righthand': {'rotation': [0, -90, -20], 'translation': [1.13, 1.6, 1.13], 'scale': [0.68, 0.68, 0.68]},
            'firstperson_lefthand': {'rotation': [0, 90, 20], 'translation': [1.13, 1.6, 1.13], 'scale': [0.68, 0.68, 0.68]},
            'head': {'rotation': [0, 0, -45], 'translation': [0, 6, 0], 'scale': [0.8, 0.8, 0.8]},
        },
    }
    doc = {
        'loader': 'forge:separate_transforms',
        'gui_light': 'front',
        'base': base,
        'perspectives': {
            'gui': {'parent': 'item/generated', 'textures': {'layer0': flat}},
            'ground': {'parent': 'item/generated', 'textures': {'layer0': flat}},
            'fixed': {'parent': 'item/generated', 'textures': {'layer0': flat}},
        },
    }
    return doc, m.el


def preview(els):
    """Страница превью: рисует бруски моделей (без текстуры — цвет клетки палитры), два меча рядом."""
    def to_js(el):
        out = []
        for e in el:
            u, v = e['faces']['north']['uv'][:2]
            key = next(k for k, c in CELL.items() if c == (int(u), int(v)))
            out.append([e['from'], e['to'], PAL[key], 1 if 'forge_data' in e['faces']['north'] else 0,
                        [e['rotation']['axis'], e['rotation']['angle'], e['rotation']['origin']] if 'rotation' in e else None])
        return out
    data = {'cold': to_js(els[0]), 'hot': to_js(els[1])}
    html = '''<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Меч 3D</title>
<style>body{margin:0;background:#262a33;color:#ddd;font:14px system-ui}#t{position:fixed;left:12px;top:8px}</style></head><body>
<div id="t">«Раскалённые угли» — объёмный вариант (тяните мышью)</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script><script>
const D=%s;const W=innerWidth,H=innerHeight;const R=new THREE.WebGLRenderer({antialias:true});R.setSize(W,H);R.setPixelRatio(devicePixelRatio||1);document.body.appendChild(R.domElement);
const S=new THREE.Scene();S.background=new THREE.Color(0x262a33);S.add(new THREE.AmbientLight(0xffffff,0.5));const L=new THREE.DirectionalLight(0xffffff,0.85);L.position.set(-3,4,5);S.add(L);
const C=new THREE.PerspectiveCamera(32,W/H,0.1,200);let yaw=0.5,pitch=0.15;
function make(list,ox){const g=new THREE.Group();for(const [a,b,col,glow,rot] of list){const sx=b[0]-a[0],sy=b[1]-a[1],sz=b[2]-a[2];
 const m=new THREE.Mesh(new THREE.BoxGeometry(sx,sy,sz),glow?new THREE.MeshBasicMaterial({color:col}):new THREE.MeshLambertMaterial({color:col}));
 const c=[(a[0]+b[0])/2,(a[1]+b[1])/2,(a[2]+b[2])/2];
 if(rot){const p=new THREE.Group();p.position.set(rot[2][0]-8,rot[2][1]-16,rot[2][2]-8);const ang=rot[1]*Math.PI/180;p.rotation[rot[0]]=ang;
  m.position.set(c[0]-rot[2][0],c[1]-rot[2][1],c[2]-rot[2][2]);p.add(m);g.add(p);}else{m.position.set(c[0]-8,c[1]-16,c[2]-8);g.add(m);}}
 g.position.x=ox;g.rotation.z=-0.62;S.add(g);return g;}
const G=[make(D.cold,-9),make(D.hot,9)];
let drag=null;addEventListener('pointerdown',e=>drag=[e.clientX,e.clientY,yaw,pitch]);addEventListener('pointerup',()=>drag=null);
addEventListener('pointermove',e=>{if(!drag)return;yaw=drag[2]-(e.clientX-drag[0])*0.01;pitch=Math.max(-1.2,Math.min(1.2,drag[3]+(e.clientY-drag[1])*0.01));});
window.setView=(y,p)=>{yaw=y;pitch=p;};
function f(){const d=62;C.position.set(Math.sin(yaw)*Math.cos(pitch)*d,Math.sin(pitch)*d,Math.cos(yaw)*Math.cos(pitch)*d);C.lookAt(0,0,0);R.render(S,C);requestAnimationFrame(f);}f();
</script></body></html>''' % json.dumps(data)
    with open(os.path.join(HERE, 'ember_blade_3d_preview.html'), 'w', encoding='utf-8') as fh:
        fh.write(html)


if __name__ == '__main__':
    palette_png()
    els = []
    for hot, name in ((False, 'ember_blade_3d'), (True, 'ember_blade_hot_3d')):
        doc, el = build(hot)
        els.append(el)
        with open(os.path.join(A, 'models', 'item', name + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=1)
        print('wrote', name, len(el), 'elements')
    preview(els)
    print('wrote tools/ember_blade_3d_preview.html')
