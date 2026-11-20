#!/usr/bin/env python3
"""
Каркас моделей GeckoLib (T25, бестиарий «Кошмаров»): кости, кубы, атлас UV, покраска текстуры в 3D-пространстве модели,
анимации. Используется tools/gen_nightmare_bestiary.py.

Система координат при проектировании — как в Blockbench (BB): y вверх, **лицом к −z**, правая рука существа — +x, 16 ед. = 1 блок,
ноги на y = 0. При записи .geo.json / .animation.json всё переводится в формат Bedrock, как это делает Blockbench и читает GeckoLib 4
(проверено по байткоду geckolib-forge-1.20.1-4.8.4: BakedModelFactory — pivot.x и origin.x зеркалятся, rotation x/y со знаком минус;
BakedAnimationsAdapter — у ключей rotation x/y со знаком минус; RenderUtils — повороты Z·Y·X, позиция x со знаком минус).

UV — по граням (per-face): каждая грань куба получает свой прямоугольник в атласе; текстура рисуется функцией материала от точки
поверхности **в позе покоя в мире** (чтобы потёки чернил текли вниз по всему телу без швов между гранями).
Ориентация граней (как в развёртке скина / box UV): north (−z): u от x1 к x0; south (+z): u от x0 к x1; east (+x): u от z1 к z0;
west (−x): u от z0 к z1; v у боковых — сверху вниз; up: u от x1 к x0, v от z1 к z0.
"""
import json
import math
import os

import numpy as np
from PIL import Image

TAU = 2 * math.pi


# ================================================================== матрицы
def rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def euler(r):
    """Поворот BB (градусы) → матрица, порядок как у three.js 'ZYX': R = Rz·Ry·Rx."""
    a, b, c = (math.radians(v) for v in r)
    return rz(c) @ ry(b) @ rx(a)


def to_euler(m):
    """Матрица → углы ZYX (градусы), обратное к euler()."""
    b = math.asin(max(-1.0, min(1.0, -m[2, 0])))
    if abs(m[2, 0]) < 0.9999:
        a = math.atan2(m[2, 1], m[2, 2])
        c = math.atan2(m[1, 0], m[0, 0])
    else:
        a = math.atan2(-m[1, 2], m[1, 1])
        c = 0.0
    return [math.degrees(a), math.degrees(b), math.degrees(c)]


def align_y(d, roll=0.0):
    """Матрица, переводящая ось +y в направление d (с поворотом roll° вокруг своей оси)."""
    d = np.asarray(d, float)
    d = d / np.linalg.norm(d)
    y = np.array([0.0, 1.0, 0.0])
    v = np.cross(y, d)
    s = np.linalg.norm(v)
    c = float(np.dot(y, d))
    if s < 1e-9:
        m = np.eye(3) if c > 0 else rx(math.pi)
    else:
        k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        m = np.eye(3) + k + k @ k * ((1 - c) / (s * s))
    return m @ ry(math.radians(roll))


def _r(v, n=3):
    v = round(float(v), n)
    return 0.0 if v == 0 else v


# ================================================================== шум (numpy, детерминированный)
def _hash(ix, iy, iz, seed):
    h = (ix.astype(np.int64) * 73856093) ^ (iy.astype(np.int64) * 19349663) ^ (iz.astype(np.int64) * 83492791) ^ (seed * 2654435761)
    h = h & 0xFFFFFFFF
    h = ((h ^ (h >> 15)) * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 3266489917) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / float(0x1000000)


def vnoise(p, f=1.0, seed=0):
    """Значение-шум 3D в [0, 1); p — (N, 3)."""
    q = np.asarray(p, float) * f
    i = np.floor(q)
    t = q - i
    t = t * t * (3 - 2 * t)
    i = i.astype(np.int64)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (t[:, 0] if dx else 1 - t[:, 0]) * (t[:, 1] if dy else 1 - t[:, 1]) * (t[:, 2] if dz else 1 - t[:, 2])
                out = out + w * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm(p, f=1.0, seed=0, oct=4, gain=0.5):
    s, a, tot = 0, 1.0, 0
    for k in range(oct):
        s = s + a * vnoise(p, f * (2 ** k), seed + 101 * k)
        tot += a
        a *= gain
    return s / tot


def ridge(p, f=1.0, seed=0, oct=3):
    """Хребтовый шум: тонкие линии (вены, трещины) там, где значение близко к 1."""
    n = fbm(p, f, seed, oct)
    return 1 - np.abs(n - 0.5) * 2


def hex2(h):
    return np.array([int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)], float) / 255.0


def mix(a, b, t):
    t = np.clip(t, 0, 1)[:, None] if np.ndim(t) else t
    return a * (1 - t) + b * t


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# ================================================================== модель
class Cube:
    def __init__(self, frm, to, mat, inflate=0.0, rot=None, pivot=None, info=None):
        self.frm, self.to = np.array(frm, float), np.array(to, float)
        self.mat, self.inflate = mat, inflate
        self.rot = rot                      # BB, градусы
        self.pivot = pivot
        self.info = info or {}
        self.uv = {}                        # грань -> (u, v, w, h) в единицах UV
        self.px = {}                        # грань -> (x, y, w, h) в пикселях атласа


class Bone:
    def __init__(self, name, parent, pivot, rot=(0, 0, 0)):
        self.name, self.parent = name, parent
        self.pivot = np.array(pivot, float)
        self.rot = list(rot)
        self.cubes = []


FACES = ('north', 'south', 'east', 'west', 'up', 'down')


def face_point(c, f, s, t):
    """Точка на грани куба (BB, до поворотов) по долям (s, t) ∈ [0, 1] вдоль u и v грани; и нормаль."""
    x0, y0, z0 = c.frm - c.inflate
    x1, y1, z1 = c.to + c.inflate
    s, t = np.asarray(s, float), np.asarray(t, float)
    one = np.ones_like(s)
    if f == 'north':
        P = np.stack([x1 + (x0 - x1) * s, y1 + (y0 - y1) * t, z0 * one], -1); n = (0, 0, -1)
    elif f == 'south':
        P = np.stack([x0 + (x1 - x0) * s, y1 + (y0 - y1) * t, z1 * one], -1); n = (0, 0, 1)
    elif f == 'east':
        P = np.stack([x1 * one, y1 + (y0 - y1) * t, z1 + (z0 - z1) * s], -1); n = (1, 0, 0)
    elif f == 'west':
        P = np.stack([x0 * one, y1 + (y0 - y1) * t, z0 + (z1 - z0) * s], -1); n = (-1, 0, 0)
    elif f == 'up':
        P = np.stack([x1 + (x0 - x1) * s, y1 * one, z1 + (z0 - z1) * t], -1); n = (0, 1, 0)
    else:
        P = np.stack([x1 + (x0 - x1) * s, y0 * one, z0 + (z1 - z0) * t], -1); n = (0, -1, 0)
    return P, np.array(n, float)


def face_size(c, f):
    d = (c.to - c.frm) + 2 * c.inflate
    return {'north': (d[0], d[1]), 'south': (d[0], d[1]), 'east': (d[2], d[1]), 'west': (d[2], d[1]),
            'up': (d[0], d[2]), 'down': (d[0], d[2])}[f]


class Model:
    def __init__(self, name, density=4, tex_w=128):
        self.name = name
        self.density = density              # пикселей текстуры на единицу модели
        self.tex_w = tex_w                  # ширина атласа в единицах UV
        self.bones = {}
        self.order = []
        self.materials = {}                 # имя -> функция(ctx) -> (rgb, alpha, glow)
        self.skin_faces = {}                # для «Мимика»: (кость, № куба) -> готовые UV граней (скин игрока)
        self.reserved = None                # (x, y, w, h) в единицах — занятая область атласа (скин)

    # ---------------------------------------------------------------- построение
    def bone(self, name, parent, pivot, rot=(0, 0, 0)):
        b = Bone(name, parent, pivot, rot)
        self.bones[name] = b
        self.order.append(name)
        return b

    def box(self, bone, frm, to, mat, inflate=0.0, rot=None, pivot=None, **info):
        frm, to = np.minimum(frm, to), np.maximum(frm, to)
        c = Cube(frm, to, mat, inflate, rot, pivot, info)
        self.bones[bone].cubes.append(c)
        return c

    def cbox(self, bone, center, size, mat, **kw):
        c = np.asarray(center, float)
        h = np.asarray(size, float) / 2
        return self.box(bone, c - h, c + h, mat, **kw)

    def rod(self, bone, p, q, w, d=None, mat='ink', roll=0.0, ext=0.0, **kw):
        """Брусок от p к q сечением w×d (поворот куба вокруг середины)."""
        p, q = np.asarray(p, float), np.asarray(q, float)
        d = w if d is None else d
        v = q - p
        L = float(np.linalg.norm(v)) + 2 * ext
        m = (p + q) / 2
        rot = to_euler(align_y(v, roll))
        if max(abs(x) for x in rot) < 1e-6:
            rot = None
        return self.box(bone, m - [w / 2, L / 2, d / 2], m + [w / 2, L / 2, d / 2], mat, rot=rot, pivot=list(m), **kw)

    def limb(self, parent, name, top, length, w, d=None, mat='ink', rot=(0, 0, 0), down=True, **kw):
        """Кость с куском от шарнира top вниз на length; возвращает точку следующего шарнира (без поворотов)."""
        d = w if d is None else d
        top = np.asarray(top, float)
        self.bone(name, parent, top, rot)
        self.box(name, top - [w / 2, length, d / 2], top + [w / 2, 0, d / 2], mat, **kw)
        return top - [0, length, 0]

    # ---------------------------------------------------------------- поза покоя (для покраски)
    def world_xf(self, bone):
        """Матрица и сдвиг кости в позе покоя: мир = M·x + o."""
        chain = []
        b = self.bones[bone]
        while b is not None:
            chain.append(b)
            b = self.bones.get(b.parent) if b.parent else None
        M, o = np.eye(3), np.zeros(3)
        for b in reversed(chain):                       # от корня к кости
            R = euler(b.rot)
            # x -> p + R(x - p), затем родитель
            o = M @ (b.pivot - R @ b.pivot) + o
            M = M @ R
        return M, o

    def cube_xf(self, bone, c):
        M, o = self.world_xf(bone)
        if c.rot:
            R = euler(c.rot)
            p = np.asarray(c.pivot, float)
            o = M @ (p - R @ p) + o
            M = M @ R
        return M, o

    # ---------------------------------------------------------------- атлас
    def pack(self):
        k = self.density
        rects = []
        for bn in self.order:
            for ci, c in enumerate(self.bones[bn].cubes):
                if c.info.get('skin'):
                    continue
                for f in FACES:
                    if f in c.info.get('hide', ()):
                        continue
                    w, h = face_size(c, f)
                    pw, ph = max(1, int(round(w * k))), max(1, int(round(h * k)))
                    rects.append((ph, pw, bn, ci, f))
        rects.sort(key=lambda r: (-r[0], -r[1]))
        W = self.tex_w * k
        x, y, row_h = 0, 0, 0
        if self.reserved:
            rx0, ry0, rw, rh = (v * k for v in self.reserved)
        for ph, pw, bn, ci, f in rects:
            while True:
                if x + pw + 1 > W:
                    x, y, row_h = 0, y + row_h + 1, 0
                if self.reserved and x < rx0 + rw and x + pw + 1 > rx0 and y < ry0 + rh and y + ph + 1 > ry0:
                    x = rx0 + rw + 1
                    continue
                break
            c = self.bones[bn].cubes[ci]
            c.px[f] = (x, y, pw, ph)
            c.uv[f] = (x / k, y / k, pw / k, ph / k)
            x += pw + 1
            row_h = max(row_h, ph)
        H = y + row_h + 1
        if self.reserved:
            H = max(H, (self.reserved[1] + self.reserved[3]) * k)
        hp = 1
        while hp < H:
            hp *= 2
        self.tex_px = (W, hp)
        self.tex_units = (self.tex_w, hp / k)

    # ---------------------------------------------------------------- покраска
    def paint(self, base_img=None):
        W, H = self.tex_px
        img = np.zeros((H, W, 4), float)
        glow = np.zeros((H, W, 4), float)
        if base_img is not None:
            b = np.asarray(base_img.convert('RGBA'), float) / 255.0
            img[:b.shape[0], :b.shape[1]] = b
        for bn in self.order:
            for ci, c in enumerate(self.bones[bn].cubes):
                if not c.px:
                    continue
                M, o = self.cube_xf(bn, c)
                fn = self.materials[c.mat]
                for f, (x, y, pw, ph) in c.px.items():
                    ss, tt = np.meshgrid((np.arange(pw) + 0.5) / pw, (np.arange(ph) + 0.5) / ph)
                    P, n = face_point(c, f, ss.ravel(), tt.ravel())
                    Pw = P @ M.T + o
                    nw = M @ n
                    ctx = Ctx(Pw, np.tile(nw, (len(Pw), 1)), ss.ravel(), tt.ravel(), f, c, bn, P)
                    rgb, a, g = fn(ctx)
                    a = np.broadcast_to(np.asarray(a, float), (len(Pw),))
                    img[y:y + ph, x:x + pw, :3] = np.clip(rgb, 0, 1).reshape(ph, pw, 3)
                    img[y:y + ph, x:x + pw, 3] = np.clip(a, 0, 1).reshape(ph, pw)
                    if g is not None:
                        g = np.asarray(g, float)
                        glow[y:y + ph, x:x + pw, :3] = np.clip(g[:, :3], 0, 1).reshape(ph, pw, 3)
                        glow[y:y + ph, x:x + pw, 3] = (np.clip(g.max(1), 0, 1) > 0.02).reshape(ph, pw) * np.clip(a, 0, 1).reshape(ph, pw)
        # альфа — отсечка (entityCutoutNoCull): 0 или 1
        img[..., 3] = (img[..., 3] > 0.5).astype(float)
        self.image = Image.fromarray((img * 255 + 0.5).astype(np.uint8), 'RGBA')
        self.glow = Image.fromarray((glow * 255 + 0.5).astype(np.uint8), 'RGBA') if glow[..., 3].any() else None
        return self.image

    # ---------------------------------------------------------------- запись
    def geo_json(self, ident=None):
        bones = []
        for bn in self.order:
            b = self.bones[bn]
            o = {'name': bn}
            if b.parent:
                o['parent'] = b.parent
            o['pivot'] = [_r(-b.pivot[0]), _r(b.pivot[1]), _r(b.pivot[2])]
            if any(abs(v) > 1e-6 for v in b.rot):
                o['rotation'] = [_r(-b.rot[0], 2), _r(-b.rot[1], 2), _r(b.rot[2], 2)]
            cubes = []
            for c in b.cubes:
                size = c.to - c.frm
                cj = {'origin': [_r(-c.to[0]), _r(c.frm[1]), _r(c.frm[2])], 'size': [_r(size[0]), _r(size[1]), _r(size[2])]}
                if c.inflate:
                    cj['inflate'] = _r(c.inflate)
                if c.rot:
                    cj['pivot'] = [_r(-c.pivot[0]), _r(c.pivot[1]), _r(c.pivot[2])]
                    cj['rotation'] = [_r(-c.rot[0], 2), _r(-c.rot[1], 2), _r(c.rot[2], 2)]
                uv = {}
                for f, (u, v, w, h) in c.uv.items():
                    uv[f] = {'uv': [_r(u, 4), _r(v, 4)], 'uv_size': [_r(w, 4), _r(h, 4)]}
                cj['uv'] = uv
                cubes.append(cj)
            if cubes:
                o['cubes'] = cubes
            bones.append(o)
        xs = [abs(v) for bn in self.order for c in self.bones[bn].cubes for v in (c.frm[0], c.to[0], c.frm[2], c.to[2])]
        ys = [v for bn in self.order for c in self.bones[bn].cubes for v in (c.frm[1], c.to[1])]
        return {'format_version': '1.12.0', 'minecraft:geometry': [{
            'description': {'identifier': 'geometry.' + (ident or self.name), 'texture_width': _r(self.tex_units[0]),
                            'texture_height': _r(self.tex_units[1]),
                            'visible_bounds_width': math.ceil(max(xs) * 2 / 16 + 1), 'visible_bounds_height': math.ceil(max(ys) / 16 + 1),
                            'visible_bounds_offset': [0, round(max(ys) / 32, 2), 0]},
            'bones': bones}]}


class Ctx:
    """Всё о текселе: P — точка в мире (поза покоя), N — нормаль, s/t — доли на грани, face, cube, bone, L — точка до поворотов."""

    def __init__(self, P, N, s, t, face, cube, bone, L):
        self.P, self.N, self.s, self.t, self.face, self.cube, self.bone, self.L = P, N, s, t, face, cube, bone, L
        self.n = len(P)

    @property
    def x(self):
        return self.P[:, 0]

    @property
    def y(self):
        return self.P[:, 1]

    @property
    def z(self):
        return self.P[:, 2]


# ================================================================== анимации
class Anim:
    """Ключи по костям; значения в BB (градусы / единицы). sample(fn, t0, t1, dt): fn(t) -> {кость: {'rot'|'pos'|'scale': [x,y,z]}}."""

    def __init__(self, name, length, loop=True):
        self.name, self.length, self.loop = name, length, loop
        self.keys = {}          # кость -> канал -> {t: vec}
        self.sounds = {}
        self.events = {}

    def key(self, bone, ch, t, v):
        self.keys.setdefault(bone, {}).setdefault(ch, {})[round(t, 4)] = [float(x) for x in v]

    LOOP = None             # список-ячейка из генератора: туда пишется длина циклической анимации на время sample()

    def sample(self, fn, dt=0.05, t0=0.0, t1=None):
        if Anim.LOOP is not None:
            Anim.LOOP[0] = self.length if self.loop is True else None
        t1 = self.length if t1 is None else t1
        n = max(1, int(round((t1 - t0) / dt)))
        for i in range(n + 1):
            t = t0 + (t1 - t0) * i / n
            for bone, chans in fn(t).items():
                if bone.startswith('_'):          # служебные метки позы (например, '_int' у Мартина)
                    continue
                for ch, v in chans.items():
                    self.key(bone, ch, t, v)

    def sound(self, t, effect):
        self.sounds[round(t, 4)] = effect

    def instruction(self, t, text):
        self.events[round(t, 4)] = text

    def to_json(self):
        bones = {}
        for bone, chans in self.keys.items():
            bj = {}
            for ch, kf in chans.items():
                name = {'rot': 'rotation', 'pos': 'position', 'scale': 'scale'}[ch]
                out = {}
                for t in sorted(kf):
                    v = kf[t]
                    if ch == 'rot':
                        v = [-v[0], -v[1], v[2]]
                    elif ch == 'pos':
                        v = [-v[0], v[1], v[2]]
                    out['%g' % t] = [_r(x, 3) for x in v]
                if len(out) == 1 and not self.loop:
                    pass
                bj[name] = out
            bones[bone] = bj
        o = {'loop': True if self.loop is True else ('hold_on_last_frame' if self.loop == 'hold' else False),
             'animation_length': self.length, 'bones': bones}
        if self.sounds:
            o['sound_effects'] = {'%g' % t: {'effect': e} for t, e in sorted(self.sounds.items())}
        if self.events:
            o['timeline'] = {'%g' % t: e for t, e in sorted(self.events.items())}
        return o


def write_json(path, obj, compact=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        if compact:
            json.dump(obj, fh, ensure_ascii=False, separators=(',', ':'))
        else:
            json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
