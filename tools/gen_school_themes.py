#!/usr/bin/env python3
"""
T06. Темы печатей для школ Iron's: Огонь, Лёд, Молния, Природа, Святая, Кровь, Край, Мистическая (eldritch),
Призывание (evocation), Ветер.

Один генератор на всё, что относится к теме школы:
  textures/sigil/<школа>_seal.png      — главная печать (512), детальный рисунок с характером школы, без центра
  textures/sigil/<школа>_core.png      — центральная эмблема (512), отдельный слой: крутится навстречу / раскрывается
  textures/sigil/<школа>_crown.png     — венец над головой (512) для ступеней Мифическая/Божественная
  textures/sigil/school_<школа>_band.png — лента мотивов школы (1024×128, повторяется по окружности)
  textures/sigil/mote_<мотив>.png      — спрайты частиц школы (128): языки огня, льдинки, искры-зигзаги, листья…
  textures/fx/sigil_<школа>.png        — печать + ядро на чёрном (знак обычного каста PohSpell и двойной контур T15)
  textures/fx/circle_ward.png          — круг-оберег Восьми щитов (перенесён из tools/gen_school_sigils.ps1)
  sigils/<школа>_seal.json, sigils/<школа>_crown.json — печати ступеней (формат docs/sigils.md)
  sigils/school_<школа>.json           — знак обычного каста (лёгкий, на новых текстурах)
  fx/school_<школа>_cast.json          — каст на ступени Высшая: печать под магом + частицы школы
  fx/school_<школа>_cast_crown.json    — Мифическая: то же + венец над головой
  fx/school_<школа>_cast_divine.json   — Божественная: печать + венец + дуга из 7 золотых кругов за спиной (раскрываются с краёв
                                         к центру, как у «Безмолвных врат»), золотые блёстки (решение владельца 19.11)
  fx/styles/<стиль>.json               — палитра, текстуры частиц, характер движения

Всё рисуется белым на прозрачном (цвет задаёт JSON), в 4 раза крупнее с уменьшением — края гладкие;
к линиям добавляется мягкий ореол. Руны — тот же алфавит, что в tools/gen_sigil_textures.py.

Запуск:  python3 tools/gen_school_themes.py            (нужны Pillow и numpy)
         python3 tools/gen_school_themes.py --sheet    ещё и лист-обзор всех текстур в docs/media/school_themes_sheet.png
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_sigil_textures import glyph  # noqa: E402  — общий алфавит рун

ASSETS = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
OUT_SIGIL = os.path.join(ASSETS, 'textures', 'sigil')
OUT_FX = os.path.join(ASSETS, 'textures', 'fx')
SS = 4
CORE_ZOOM = 2.6          # ядро рисуется в радиусе ~95 и растягивается на холст (слой core: radius 0.4 ≈ 100/256)
TAU = 2 * math.pi
WRITTEN = []


# ====================================================================== кисть
class Pen:
    """Холст в координатах итоговой картинки (w×h), рисуем в SS раз крупнее. fill=0 — стирает (гравировка).
    zoom — масштаб рисунка от центра: ядра рисуются в тех же координатах, что и печать (радиус ~95), но на весь холст."""

    def __init__(self, w=512, h=512, zoom=1.0):
        self.w, self.h, self.k = w, h, zoom
        self.img = Image.new('L', (w * SS, h * SS), 0)
        self.d = ImageDraw.Draw(self.img)
        self.cx, self.cy = w / 2, h / 2

    def P(self, r, a, cx=None, cy=None):
        return ((self.cx if cx is None else cx) + r * math.cos(a), (self.cy if cy is None else cy) + r * math.sin(a))

    def _t(self, x, y):
        return ((self.cx + (x - self.cx) * self.k) * SS, (self.cy + (y - self.cy) * self.k) * SS)

    def _s(self, pts):
        return [self._t(x, y) for x, y in pts]

    def line(self, pts, w, fill=255, caps=True):
        pts = list(pts)
        if len(pts) < 2:
            return
        self.d.line(self._s(pts), fill=fill, width=max(1, int(round(w * SS * self.k))), joint='curve')
        if caps:
            for p in (pts[0], pts[-1]):
                self.dot(p[0], p[1], w / 2, fill)

    def dot(self, x, y, r, fill=255):
        X, Y = self._t(x, y)
        R = r * self.k * SS
        self.d.ellipse([X - R, Y - R, X + R, Y + R], fill=fill)

    def circle(self, x, y, r, w, fill=255):
        X, Y = self._t(x, y)
        R = r * self.k * SS
        self.d.ellipse([X - R, Y - R, X + R, Y + R], outline=fill, width=max(1, int(round(w * SS * self.k))))

    def ring(self, r, w, fill=255):
        self.circle(self.cx, self.cy, r, w, fill)

    def poly(self, pts, fill=255):
        self.d.polygon(self._s(pts), fill=fill)

    def arc(self, r, a0, a1, w, fill=255, n=None, cx=None, cy=None):
        n = n or max(8, int(abs(a1 - a0) * r / 3))
        self.line([self.P(r, a0 + (a1 - a0) * i / n, cx, cy) for i in range(n + 1)], w, fill)

    def taper(self, pts, widths, fill=255, cap=True):
        """Штрих переменной ширины по средней линии pts (ширины — полные, по точкам)."""
        pts = list(pts)
        n = len(pts)
        left, right = [], []
        for i in range(n):
            x0, y0 = pts[max(0, i - 1)]
            x1, y1 = pts[min(n - 1, i + 1)]
            dx, dy = x1 - x0, y1 - y0
            L = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / L, dx / L
            h = widths[i] / 2
            left.append((pts[i][0] + nx * h, pts[i][1] + ny * h))
            right.append((pts[i][0] - nx * h, pts[i][1] - ny * h))
        self.poly(left + right[::-1], fill)
        if cap:
            for i in (0, n - 1):
                if widths[i] > 0.6:
                    self.dot(pts[i][0], pts[i][1], widths[i] / 2, fill)


def rot(pts, a, cx, cy):
    c, s = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


def bez(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def local(origin, ang, pts):
    """Точки (x вдоль направления ang, y поперёк) от origin."""
    c, s = math.cos(ang), math.sin(ang)
    return [(origin[0] + x * c - y * s, origin[1] + x * s + y * c) for x, y in pts]


# ====================================================================== мотивы
def flame(pen, base, ang, L, W, curl=0.25, layers=True, fill=255):
    """Язык пламени от base вдоль ang: изгиб S, острый загнутый кончик, внутри — вырезанный язычок и горячее ядро."""
    def shape(l, w, t0=0.0):
        pts, ws = [], []
        for i in range(33):
            t = i / 32
            x = t0 * L + t * l
            y = curl * L * (0.35 * math.sin(math.pi * t) * (1 - t) + 0.55 * t ** 2.2) * (1 if curl >= 0 else 1)
            pts.append((x, y))
            ws.append(w * (1 - t) ** 0.75 * min(1.0, 0.45 + t * 5))
        return local(base, ang, pts), ws
    p, w = shape(L, W)
    pen.taper(p, w, fill)
    if layers:
        p, w = shape(L * 0.62, W * 0.46, 0.08)
        pen.taper(p, w, 0 if fill else 255)
        p, w = shape(L * 0.32, W * 0.2, 0.14)
        pen.taper(p, w, fill)


def leaf(pen, base, ang, L, W, veins=True, fill=255, bend=0.0):
    """Лист с вырезанной средней жилкой и боковыми жилками."""
    up, dn, mid = [], [], []
    for i in range(29):
        t = i / 28
        yb = bend * L * t * t
        h = W / 2 * math.sin(math.pi * t) ** 0.85 * (1 - 0.25 * t)
        up.append((t * L, yb + h))
        dn.append((t * L, yb - h))
        mid.append((t * L, yb))
    pen.poly(local(base, ang, up + dn[::-1]), fill)
    if veins and W > 5:
        e = 0 if fill else 255
        pen.line(local(base, ang, mid[1:25]), max(0.9, W * 0.09), e)
        for k in range(1, 5):
            t = k / 5.5
            x, y = t * L, bend * L * t * t
            h = W / 2 * math.sin(math.pi * t) ** 0.85 * 0.8
            for sgn in (1, -1):
                pen.line(local(base, ang, [(x, y), (x + h * 0.7, y + sgn * h)]), max(0.7, W * 0.06), e)


def feather(pen, base, ang, L, W, fill=255):
    """Перо: несимметричное опахало, вырезанный стержень, косые бородки."""
    up, dn = [], []
    for i in range(31):
        t = i / 30
        up.append((t * L, W * 0.62 * math.sin(math.pi * min(1, t * 1.05)) ** 0.7 * (1 - 0.15 * t)))
        dn.append((t * L, -W * 0.38 * math.sin(math.pi * min(1, t * 1.05)) ** 0.7))
    pen.poly(local(base, ang, up + dn[::-1]), fill)
    e = 0 if fill else 255
    pen.line(local(base, ang, [(-L * 0.08, 0), (L * 0.92, 0)]), max(0.9, W * 0.1), e)
    for k in range(2, 9):
        t = k / 10
        pen.line(local(base, ang, [(t * L, 0), (t * L + W * 0.45, W * 0.5)]), max(0.6, W * 0.05), e, caps=False)
        pen.line(local(base, ang, [(t * L, 0), (t * L + W * 0.3, -W * 0.32)]), max(0.6, W * 0.05), e, caps=False)


def teardrop(pen, cx, cy, ang, s, fill=255, highlight=True):
    """Капля: круг радиуса s, острый кончик в сторону ang."""
    D = 2.5 * s
    phi = math.acos(s / D)
    pts = [(cx + D * math.cos(ang), cy + D * math.sin(ang))]
    for i in range(41):
        a = ang + phi + (TAU - 2 * phi) * i / 40
        pts.append((cx + s * math.cos(a), cy + s * math.sin(a)))
    pen.poly(pts, fill)
    if highlight and s > 4:
        hx, hy = cx + s * 0.35 * math.cos(ang + 2.2), cy + s * 0.35 * math.sin(ang + 2.2)
        pen.dot(hx, hy, s * 0.28, 0 if fill else 255)


def jag(rng, a, b, depth, amp):
    """Ломаная молнии a→b: смещение середины, depth уровней."""
    pts = [a, b]
    for d in range(depth):
        nxt = [pts[0]]
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            L = math.hypot(x1 - x0, y1 - y0)
            nx, ny = -(y1 - y0) / (L or 1), (x1 - x0) / (L or 1)
            o = (rng.random() * 2 - 1) * amp * L
            nxt += [((x0 + x1) / 2 + nx * o, (y0 + y1) / 2 + ny * o), pts[i + 1]]
        pts = nxt
    return pts


def bolt(pen, rng, a, b, w0, w1, branches=2, depth=4, amp=0.28):
    pts = jag(rng, a, b, depth, amp)
    n = len(pts)
    pen.taper(pts, [w0 + (w1 - w0) * i / (n - 1) for i in range(n)])
    for _ in range(branches):
        i = rng.randint(n // 5, n * 3 // 5)
        x, y = pts[i]
        dx, dy = b[0] - a[0], b[1] - a[1]
        ang = math.atan2(dy, dx) + rng.choice([-1, 1]) * (0.5 + rng.random() * 0.5)
        L = math.hypot(dx, dy) * (0.25 + rng.random() * 0.2)
        e = (x + math.cos(ang) * L, y + math.sin(ang) * L)
        bp = jag(rng, (x, y), e, 3, 0.3)
        wb = w0 + (w1 - w0) * i / (n - 1)
        pen.taper(bp, [wb * 0.6 * (1 - k / len(bp)) + 0.6 for k in range(len(bp))])


def star4(pen, x, y, r, ang=0.0, thin=0.22, fill=255):
    pts = []
    for i in range(8):
        a = ang + i * TAU / 8
        rr = r if i % 2 == 0 else r * thin
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    pen.poly(pts, fill)


def eye(pen, x, y, w, h, ang=0.0, lw=2.0, slit=True, iris=0.32, lashes=0):
    """Око: миндаль из двух дуг, радужка, зрачок (у Края — щель)."""
    up = [(-w + 2 * w * i / 30, h * math.sin(math.pi * i / 30)) for i in range(31)]
    dn = [(-w + 2 * w * i / 30, -h * math.sin(math.pi * i / 30)) for i in range(31)]
    pen.line(local((x, y), ang, up), lw)
    pen.line(local((x, y), ang, dn), lw)
    ir = h * iris * 2.2
    pen.circle(x, y, ir, lw * 0.8)
    pen.dot(x, y, ir * 0.62)
    if slit:
        pen.poly(local((x, y), ang, [(0, -ir * 0.62), (ir * 0.16, 0), (0, ir * 0.62), (-ir * 0.16, 0)]), 0)
    else:
        pen.dot(x - ir * 0.2, y - ir * 0.2, ir * 0.18, 0)
    for k in range(lashes):
        t = (k + 1) / (lashes + 1)
        px, py = -w + 2 * w * t, h * math.sin(math.pi * t)
        a = math.atan2(py, px * 0.3) if px else math.pi / 2
        pen.line(local((x, y), ang, [(px, py), (px * 1.12, py + h * 0.55)]), lw * 0.7)


def glyph_at(pen, rng, x, y, h, ang, w):
    """Руна из общего алфавита, повернута на ang (верх руны — наружу)."""
    strokes, dot = glyph(rng)
    sx, sy = h * 0.35, h / 3
    for (ax, ay), (bx, by) in strokes:
        pts = [((ax - 1) * sx, (ay - 1.5) * sy), ((bx - 1) * sx, (by - 1.5) * sy)]
        pen.line(local((x, y), ang, [(py, -px) for px, py in pts]), w)
    if dot:
        p = local((x, y), ang, [(0, -(sx * 1.6))])[0]
        pen.dot(p[0], p[1], w * 0.9)


def glyph_ring(pen, r1, r2, n, seed, w):
    rng = random.Random(seed)
    for i in range(n):
        a = i * TAU / n
        x, y = pen.P((r1 + r2) / 2, a)
        glyph_at(pen, rng, x, y, (r2 - r1) * 0.8, a + math.pi, w)


def ticks(pen, r, n, l, w, every=0, lmul=1.8):
    for i in range(n):
        a = i * TAU / n
        ll = l * (lmul if every and i % every == 0 else 1)
        pen.line([pen.P(r, a), pen.P(r - ll, a)], w)


def dots(pen, r, n, s, a0=0.0):
    for i in range(n):
        x, y = pen.P(r, a0 + i * TAU / n)
        pen.dot(x, y, s)


def polygon(pen, r, n, a0, w, step=1):
    i, pts = 0, []
    while True:
        pts.append(pen.P(r, a0 + i * TAU / n))
        i = (i + step) % n
        if i == 0:
            break
    pts.append(pts[0])
    pen.line(pts, w)


def spiral(pen, r0, r1, a0, turn, w0, w1, n=80, cx=None, cy=None, wmid=None):
    pts, ws = [], []
    for i in range(n + 1):
        t = i / n
        pts.append(pen.P(r0 + (r1 - r0) * t, a0 + turn * t, cx, cy))
        ws.append(w0 + (w1 - w0) * t if wmid is None else (w0 + (wmid - w0) * t * 2 if t < 0.5 else wmid + (w1 - wmid) * (t - 0.5) * 2))
    pen.taper(pts, ws)
    return pts


def curl(pen, x, y, r, a0, turns, w, direction=1):
    pts = []
    for i in range(61):
        t = i / 60
        rr = r * (1 - 0.85 * t)
        a = a0 + direction * turns * TAU * t
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    pen.line(pts, w)


# ====================================================================== вывод
def to_alpha(pen, glow=0.5, glow_r=3.0):
    small = pen.img.resize((pen.w, pen.h), Image.LANCZOS)
    a = np.asarray(small, dtype=np.float32)
    if glow:
        g = np.asarray(small.filter(ImageFilter.GaussianBlur(glow_r)), dtype=np.float32) * glow * 1.6
        a = np.maximum(a, np.minimum(255, g))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'L')


def save_sigil(pen, name, glow=0.5, glow_r=3.0):
    alpha = to_alpha(pen, glow, glow_r)
    rgba = Image.new('RGBA', alpha.size, (255, 255, 255, 0))
    rgba.putalpha(alpha)
    os.makedirs(OUT_SIGIL, exist_ok=True)
    rgba.save(os.path.join(OUT_SIGIL, name + '.png'))
    WRITTEN.append(('sigil', name))
    return alpha


def save_fx_black(alpha, name):
    """Как в старом gen_school_sigils.ps1: белое на непрозрачном чёрном (аддитивно)."""
    v = np.asarray(alpha)
    rgba = np.dstack([v, v, v, np.full_like(v, 255)])
    Image.fromarray(rgba, 'RGBA').save(os.path.join(OUT_FX, name + '.png'))
    WRITTEN.append(('fx', name))


# ====================================================================== общие рамки
def frame_outer(pen, w1=5, w2=2):
    pen.ring(246, w1)
    pen.ring(238, w2)


# ====================================================================== ОГОНЬ
def fire_seal(p):
    rng = random.Random(101)
    frame_outer(p)
    ticks(p, 238, 120, 5, 1.6, every=5, lmul=2)
    # венец пламени: большие и малые языки, загнуты по ходу вращения
    for i in range(18):
        a = i * TAU / 18
        flame(p, p.P(168, a), a + 0.18, 64, 26, curl=0.32)
        a2 = a + TAU / 36
        flame(p, p.P(170, a2), a2 + 0.22, 36, 13, curl=0.4)
    p.ring(168, 4.5)
    p.ring(160, 1.6)
    glyph_ring(p, 128, 156, 30, 11, 2.2)
    p.ring(126, 3.5)
    # алхимический огонь: два треугольника, на вершинах — угольки
    polygon(p, 124, 3, -math.pi / 2, 4)
    polygon(p, 124, 3, math.pi / 2, 2.4)
    for k in range(6):
        x, y = p.P(124, -math.pi / 2 + k * TAU / 6)
        p.dot(x, y, 7)
        p.dot(x, y, 3.5, 0)
    # угли между рунами и пламенем
    for _ in range(40):
        a, r = rng.random() * TAU, 100 + rng.random() * 22
        x, y = p.P(r, a)
        p.dot(x, y, 0.8 + rng.random() * 1.6)
    p.ring(98, 3)


def fire_core(p):
    p.ring(94, 3.5)
    p.ring(88, 1.2)
    for i in range(16):   # корона языков внутри кольца
        a = i * TAU / 16
        flame(p, p.P(62, a), a + 0.25, 24 if i % 2 == 0 else 15, 9 if i % 2 == 0 else 6, curl=0.4, layers=False)
    p.ring(60, 2)
    for i in range(3):   # три языка, закрученные вихрем вокруг центра
        a = i * TAU / 3
        spiral(p, 18, 56, a, 2.0, 7, 0.8, wmid=8)
    p.dot(p.cx, p.cy, 15)
    p.poly([p.P(10, -math.pi / 2 + k * TAU / 3) for k in range(3)], 0)
    p.dot(p.cx, p.cy + 1, 2.6)


def fire_crown(p):
    p.ring(150, 6)
    p.ring(140, 2)
    for i in range(14):
        a = i * TAU / 14
        flame(p, p.P(150, a), a - 0.1, 92 if i % 2 == 0 else 60, 30 if i % 2 == 0 else 20, curl=-0.3)
    glyph_ring(p, 104, 134, 18, 12, 2.4)
    p.ring(100, 3)
    polygon(p, 96, 3, -math.pi / 2, 3.5)
    p.dot(p.cx, p.cy, 18)
    p.dot(p.cx, p.cy, 9, 0)


def fire_band(p):
    rng = random.Random(7)
    p.line([(0, 6), (p.w, 6)], 3, caps=False)
    p.line([(0, 122), (p.w, 122)], 3, caps=False)
    for i in range(12):
        x = (i + 0.5) * p.w / 12
        for dx in (-p.w, 0, p.w):
            flame(p, (x + dx, 118), -math.pi / 2 + 0.12, 92, 40, curl=0.28)
            flame(p, (x + dx + p.w / 24, 118), -math.pi / 2 + 0.2, 52, 22, curl=0.35)
    for _ in range(40):
        p.dot(rng.random() * p.w, 12 + rng.random() * 40, 1 + rng.random() * 1.8)


# ====================================================================== ЛЁД
def ice_branch(p, x, y, ang, L, w, depth):
    e = (x + math.cos(ang) * L, y + math.sin(ang) * L)
    p.taper([(x, y), e], [w, w * 0.45])
    if depth <= 0:
        return
    for t, s in ((0.38, 0.5), (0.68, 0.36)):
        bx, by = x + math.cos(ang) * L * t, y + math.sin(ang) * L * t
        for sg in (1, -1):
            ice_branch(p, bx, by, ang + sg * math.pi / 3, L * s, w * 0.62, depth - 1)


def crystal(p, x, y, ang, L, W):
    pts = local((x, y), ang, [(0, 0), (L * 0.35, W / 2), (L, 0), (L * 0.35, -W / 2)])
    p.poly(pts)
    p.line(local((x, y), ang, [(L * 0.08, 0), (L * 0.9, 0)]), max(0.8, W * 0.12), 0)
    p.line(local((x, y), ang, [(L * 0.35, W / 2 - 1.5), (L * 0.6, 0)]), max(0.6, W * 0.07), 0, caps=False)


def ice_seal(p):
    frame_outer(p, 4, 2)
    for i in range(36):   # сосульки внутрь от обода
        a = i * TAU / 36
        L = 34 if i % 3 == 0 else (22 if i % 3 == 1 else 14)
        crystal(p, *p.P(236, a), a + math.pi, L, 9 if i % 3 == 0 else 6)
    polygon(p, 196, 6, 0, 3.2)
    polygon(p, 196, 6, math.pi / 6, 1.8)
    for k in range(6):   # большие лучи снежинки с ветвями
        a = k * TAU / 6
        x, y = p.P(100, a)
        ice_branch(p, x, y, a, 88, 6.5, 2)
        crystal(p, *p.P(186, a), a, 22, 13)
        b = a + TAU / 12   # малые лучи между
        x, y = p.P(104, b)
        ice_branch(p, x, y, b, 46, 3.6, 1)
        cx, cy = p.P(166, b)
        polygon_at(p, cx, cy, 9, 6, b, 2)
        p.dot(cx, cy, 2.5)
    p.ring(100, 3)
    p.ring(108, 1.2)


def polygon_at(p, cx, cy, r, n, a0, w):
    pts = [(cx + r * math.cos(a0 + i * TAU / n), cy + r * math.sin(a0 + i * TAU / n)) for i in range(n + 1)]
    p.line(pts, w)


def ice_core(p):
    polygon(p, 94, 6, math.pi / 6, 3.5)
    p.ring(82, 1.5)
    for k in range(6):
        a = k * TAU / 6
        crystal(p, p.cx, p.cy, a, 80, 22)
        crystal(p, *p.P(30, a + TAU / 12), a + TAU / 12, 30, 9)
    polygon(p, 16, 6, 0, 2.5)
    p.dot(p.cx, p.cy, 5)


def ice_crown(p):
    p.ring(120, 4)
    polygon(p, 120, 6, 0, 2.5)
    for k in range(6):
        a = k * TAU / 6
        crystal(p, *p.P(116, a), a, 110, 30)
        crystal(p, *p.P(110, a + TAU / 12), a + TAU / 12, 48, 14)
        ice_branch(p, p.cx, p.cy, a, 104, 5, 1)
    p.ring(40, 3)
    polygon(p, 26, 6, math.pi / 6, 2.5)


def ice_band(p):
    p.line([(0, 6), (p.w, 6)], 3, caps=False)
    p.line([(0, 120), (p.w, 120)], 2, caps=False)
    for i in range(16):
        x = (i + 0.5) * p.w / 16
        for dx in (-p.w, 0, p.w):
            X = x + dx
            crystal(p, X, 8, math.pi / 2, 70 if i % 2 == 0 else 44, 18 if i % 2 == 0 else 12)
            if i % 2:
                for k in range(6):
                    a = k * TAU / 6
                    p.line([(X + p.w / 32, 92), (X + p.w / 32 + 14 * math.cos(a), 92 + 14 * math.sin(a))], 2.2)
                p.dot(X + p.w / 32, 92, 3)


# ====================================================================== МОЛНИЯ
def lightning_seal(p):
    rng = random.Random(303)
    p.ring(246, 5)
    zz = []   # зубчатое кольцо-разряд
    for i in range(145):
        a = i * TAU / 144
        zz.append(p.P(236 if i % 2 == 0 else 224, a))
    p.line(zz, 2.4)
    p.ring(218, 2.2)
    polygon(p, 172, 8, math.pi / 8, 2.4, 3)
    for k in range(8):   # разветвлённые разряды от обода внутрь
        a = k * TAU / 8
        bolt(p, rng, p.P(214, a), p.P(104, a + 0.18), 7, 2.5, branches=3, depth=4, amp=0.22)
        star4(p, *p.P(196, a + TAU / 16), 11, a, 0.2)
        star4(p, *p.P(140, a + TAU / 16), 6, a + 0.4, 0.25)
    p.ring(100, 4)
    p.ring(108, 1.4)


def lightning_core(p):
    rng = random.Random(304)
    p.ring(94, 3)
    for i in range(24):
        a = i * TAU / 24
        p.line([p.P(94, a), p.P(84 if i % 2 else 76, a)], 2)
    star4(p, p.cx, p.cy, 74, 0, 0.16)
    star4(p, p.cx, p.cy, 54, math.pi / 4, 0.18)
    star4(p, p.cx, p.cy, 50, 0, 0.12, fill=0)
    zz = [p.P(26 if i % 2 else 34, i * TAU / 24) for i in range(25)]   # зубчатое «око бури»
    p.line(zz, 2.2)
    p.dot(p.cx, p.cy, 9)


def lightning_crown(p):
    rng = random.Random(305)
    p.ring(118, 5)
    p.ring(106, 2)
    for k in range(8):
        a = k * TAU / 8
        bolt(p, rng, p.P(118, a), p.P(236, a + 0.12), 8, 1.5, branches=2, depth=4, amp=0.25)
    star4(p, p.cx, p.cy, 84, 0, 0.18)
    star4(p, p.cx, p.cy, 60, math.pi / 4, 0.2)
    p.dot(p.cx, p.cy, 10, 0)


def lightning_band(p):
    rng = random.Random(9)
    p.line([(0, 8), (p.w, 8)], 3, caps=False)
    p.line([(0, 120), (p.w, 120)], 3, caps=False)
    pts = []
    for i in range(65):
        pts.append((i * p.w / 64, 64 + (34 if i % 2 else -34)))
    p.line(pts, 4)
    for i in range(8):
        x = (i + 0.5) * p.w / 8
        star4(p, x, 64, 16, 0, 0.18)
        bolt(p, rng, (x + 40, 14), (x + 52, 114), 4, 1.5, branches=1, depth=3, amp=0.3)


# ====================================================================== ПРИРОДА
def nature_seal(p):
    rng = random.Random(404)
    p.ring(246, 4)
    p.ring(240, 1.4)
    for ph in (0, math.pi):   # две лозы, переплетённые волной
        pts = [p.P(214 + 12 * math.sin(10 * a + ph), a) for a in [i * TAU / 720 for i in range(721)]]
        p.line(pts, 3.2)
    for i in range(40):   # листья на лозах, попеременно наружу/внутрь
        a = i * TAU / 40
        sg = 1 if i % 2 == 0 else -1
        r = 214 + 12 * math.sin(10 * a + (0 if sg > 0 else math.pi))
        x, y = p.P(r, a)
        leaf(p, (x, y), a + sg * 0.9 + (math.pi if sg < 0 else 0) * 0 + (0 if sg > 0 else math.pi - 1.8), 26, 12, bend=0.12 * sg)
    for i in range(20):
        a = (i + 0.5) * TAU / 20
        x, y = p.P(236, a)
        p.dot(x, y, 3)
    p.ring(186, 3)
    p.ring(180, 1.2)
    for k in range(8):   # побеги с усиками от внутреннего круга
        a = k * TAU / 8
        pts = bez(p.P(102, a), p.P(140, a - 0.25), p.P(160, a + 0.3), p.P(170, a + 0.05), 30)
        p.taper(pts, [5 - 3 * i / 30 for i in range(31)])
        ex, ey = pts[-1]
        curl(p, ex, ey, 9, a + math.pi / 2, 1.3, 1.8)
        leaf(p, pts[12], a - 0.9, 30, 14, bend=0.1)
        leaf(p, pts[20], a + 0.9, 24, 11, bend=-0.1)
        for j in range(3):
            q = pts[6 + j * 7]
            p.dot(q[0] + rng.uniform(-6, 6), q[1] + rng.uniform(-6, 6), 1.6)
    p.ring(100, 3)


def nature_core(p):
    p.ring(94, 3)
    for k in range(8):   # цветок: 8 лепестков-листьев + 8 малых между
        a = k * TAU / 8
        leaf(p, (p.cx, p.cy), a, 88, 36)
        leaf(p, p.P(30, a + TAU / 16), a + TAU / 16, 50, 16, veins=False)
    p.dot(p.cx, p.cy, 30, 0)
    p.circle(p.cx, p.cy, 30, 2.5)
    ga = math.pi * (3 - math.sqrt(5))   # семена по золотому углу
    for i in range(60):
        r = 2.6 * math.sqrt(i + 1)
        x, y = p.P(r * 1.05, i * ga)
        p.dot(x, y, 1.2 + 0.02 * i)


def nature_crown(p):
    p.ring(150, 3)
    for i in range(22):
        a = i * TAU / 22
        leaf(p, p.P(150, a), a - 0.55, 70, 30, bend=0.08)
        leaf(p, p.P(150, a + 0.12), a + 0.75, 38, 15, bend=-0.08)
    for i in range(11):
        x, y = p.P(128, i * TAU / 11)
        p.dot(x, y, 5)
    p.ring(108, 2)
    for k in range(5):
        leaf(p, (p.cx, p.cy), k * TAU / 5 - math.pi / 2, 60, 26)
    p.dot(p.cx, p.cy, 10, 0)


def nature_band(p):
    p.line([(0, 6), (p.w, 6)], 2.5, caps=False)
    p.line([(0, 122), (p.w, 122)], 2.5, caps=False)
    pts = [(x, 64 + 26 * math.sin(x / p.w * TAU * 4)) for x in np.linspace(0, p.w, 300)]
    p.line(pts, 4)
    pts2 = [(x, 64 - 18 * math.sin(x / p.w * TAU * 4 + 0.7)) for x in np.linspace(0, p.w, 300)]
    p.line(pts2, 2)
    for i in range(16):
        x = (i + 0.25) * p.w / 16
        y = 64 + 26 * math.sin(x / p.w * TAU * 4)
        sg = 1 if i % 2 else -1
        leaf(p, (x, y), -math.pi / 2 * sg + 0.5 * sg, 40, 18, bend=0.1)
        curl(p, x + p.w / 32, 64 - 30 * sg, 9, 0, 1.2, 1.6)


# ====================================================================== СВЯТАЯ
def feather_shape(base, ang, L, W):
    """Контур пера: скруглённый кончик, чуть несимметричное опахало."""
    up, dn = [], []
    for i in range(25):
        t = i / 24
        prof = math.sin(math.pi * min(1.0, 0.12 + t * 0.95)) ** 0.55
        up.append((t * L, W * 0.55 * prof))
        dn.append((t * L, -W * 0.45 * prof))
    return local(base, ang, up + dn[::-1])


def feather_line(p, base, ang, L, W, lw=2.0):
    """Перо линией поверх уже нарисованного: под ним вычищается место, затем контур, стержень и пара бородок."""
    sh = feather_shape(base, ang, L, W)
    p.poly(sh, 0)
    p.line(sh + [sh[0]], lw)
    p.line(local(base, ang, [(-L * 0.06, 0), (L * 0.86, 0)]), lw * 0.8)
    for t in (0.35, 0.55, 0.72):
        p.line(local(base, ang, [(t * L, 0), (t * L + W * 0.32, W * 0.38)]), lw * 0.55, caps=False)


def wing(p, side, root, span=1.0):
    """Крыло: маховые перья (длинные) веером, поверх — кроющие и мелкие у корня. side +1 — вправо, −1 — влево."""
    rx, ry = root
    rows = ((6, 84, 132, 32, -1.15, 0.3, 0, 2.6), (5, 52, 70, 30, -1.0, 0.2, 12, 2.4), (4, 28, 36, 24, -0.8, 0.1, 22, 2.2))
    for n, L0, L1, W, a0, a1, inset, lw in rows:
        for i in range(n)[::-1]:
            t = i / (n - 1)
            a = a0 + (a1 - a0) * t
            ang = a if side > 0 else math.pi - a
            L = (L1 - (L1 - L0) * t) * span
            bx = rx + side * (inset + 6 * t) * span
            by = ry - 8 * (1 - t) * span
            feather_line(p, (bx, by), ang, L, W * span, lw)


def holy_seal(p):
    frame_outer(p, 5, 2)
    for i in range(24):   # кресты и бусины по ободу
        a = i * TAU / 24
        x, y = p.P(228, a)
        if i % 2 == 0:
            p.line(local((x, y), a, [(-6, 0), (6, 0)]), 2.4)
            p.line(local((x, y), a, [(0, -4), (0, 4)]), 2.4)
        else:
            p.dot(x, y, 2.4)
    p.ring(218, 2.2)
    for i in range(48):   # лучи-клинья
        a = i * TAU / 48
        L = 212 if i % 4 == 0 else (176 if i % 2 == 0 else 146)
        w = 9 if i % 4 == 0 else (5 if i % 2 == 0 else 3)
        p.taper([p.P(104, a), p.P(L, a)], [w, 0.8])
    for sg in (1, -1):   # два крыла из-за внутреннего круга
        wing(p, sg, (p.cx + sg * 88, p.cy - 4), 1.0)
    p.dot(p.cx, p.cy, 102, 0)
    p.ring(104, 4)
    p.ring(96, 1.4)


def holy_core(p):
    p.ring(92, 3.5)
    p.ring(80, 1.4)
    pts = []
    for i in range(16):   # восьмиконечная звезда: 4 длинных, 4 коротких
        a = -math.pi / 2 + i * TAU / 16
        r = 76 if i % 4 == 0 else (46 if i % 2 == 0 else 14)
        pts.append(p.P(r, a))
    p.poly(pts)
    pts2 = []
    for i in range(16):
        a = -math.pi / 2 + i * TAU / 16
        r = 62 if i % 4 == 0 else (34 if i % 2 == 0 else 9)
        pts2.append(p.P(r, a))
    p.poly(pts2, 0)
    p.circle(p.cx, p.cy, 22, 3)
    p.dot(p.cx, p.cy, 8)


def holy_crown(p):
    p.ring(132, 7)
    p.ring(120, 2)
    p.ring(144, 1.6)
    for i in range(36):
        a = i * TAU / 36
        L = 236 if i % 3 == 0 else 196
        p.taper([p.P(150, a), p.P(L, a)], [7 if i % 3 == 0 else 4, 0.6])
    for k in range(4):
        x, y = p.P(132, k * TAU / 4 - math.pi / 4)
        star4(p, x, y, 18, math.pi / 4 * 0, 0.22)
    p.ring(70, 3)
    star4(p, p.cx, p.cy, 56, -math.pi / 2, 0.16)


def holy_band(p):
    p.line([(0, 6), (p.w, 6)], 3, caps=False)
    p.line([(0, 122), (p.w, 122)], 3, caps=False)
    for i in range(12):
        x = (i + 0.5) * p.w / 12
        for k in range(7):
            a = -math.pi / 2 + (k - 3) * 0.28
            p.taper([(x, 96), (x + 72 * math.cos(a), 96 + 72 * math.sin(a))], [5 if k == 3 else 3, 0.6])
        p.dot(x, 100, 10)
        p.dot(x, 100, 5, 0)
        X2 = x + p.w / 24
        p.line([(X2, 46), (X2, 106)], 3)
        p.line([(X2 - 12, 64), (X2 + 12, 64)], 3)


# ====================================================================== КРОВЬ
def vein(p, rng, x, y, ang, L, w, depth):
    pts, ws = [(x, y)], [w]
    a = ang
    steps = 14
    for i in range(steps):
        a += rng.uniform(-0.28, 0.28)
        x += math.cos(a) * L / steps
        y += math.sin(a) * L / steps
        pts.append((x, y))
        ws.append(w * (1 - (i + 1) / steps * 0.7))
    p.taper(pts, ws)
    if depth > 0:
        for j in (5, 9):
            if rng.random() < 0.85:
                vein(p, rng, *pts[j], a + rng.choice([-1, 1]) * rng.uniform(0.5, 0.9), L * 0.55, ws[j] * 0.75, depth - 1)


def blood_seal(p):
    rng = random.Random(606)
    p.ring(246, 5)
    p.ring(230, 3.2)
    for i in range(40):   # шипы наружу и внутрь
        a = i * TAU / 40
        sg = 1 if i % 2 == 0 else -1
        p.poly([p.P(230, a - 0.035), p.P(230 + sg * 12, a + 0.02 * sg), p.P(230, a + 0.035)])
    for i in range(12):   # капли на нитях, свисают внутрь
        a = i * TAU / 12
        L = 26 if i % 2 == 0 else 14
        p.line([p.P(228, a), p.P(228 - L, a)], 1.6)
        x, y = p.P(228 - L - 10, a)
        teardrop(p, x, y, a, 7 if i % 2 == 0 else 5)
    p.ring(178, 2.2)
    for k in range(10):   # вены от внутреннего кольца наружу
        a = k * TAU / 10 + 0.2
        vein(p, rng, *p.P(110, a), a + rng.uniform(-0.3, 0.3), 70, 5.5, 2)
    for k in range(10):
        a = k * TAU / 10 + 0.2 + TAU / 20
        x, y = p.P(150, a)
        teardrop(p, x, y, a + math.pi, 4.5, highlight=False)
    p.ring(108, 4.5)
    p.ring(100, 1.4)


def blood_core(p):
    p.ring(94, 3.5)
    for i in range(24):
        a = i * TAU / 24
        p.poly([p.P(94, a - 0.06), p.P(84, a), p.P(94, a + 0.06)])
    # полумесяц: круг минус смещённый круг
    p.dot(p.cx, p.cy, 70)
    p.dot(p.cx + 26, p.cy - 14, 62, 0)
    teardrop(p, p.cx + 14, p.cy - 4, math.pi / 2 + math.pi, 20)   # капля в лоне месяца
    for k in range(3):
        a = math.pi * 0.7 + k * 0.32
        x, y = p.P(56, a)
        p.dot(x, y, 3, 0)


def blood_crown(p):
    p.ring(130, 4)
    p.ring(118, 2)
    pts = []   # терновый венец: две переплетённые ветви
    for ph in (0, math.pi):
        pts = [p.P(124 + 10 * math.sin(7 * a + ph), a) for a in [i * TAU / 400 for i in range(401)]]
        p.line(pts, 3.5)
    for i in range(28):
        a = i * TAU / 28
        sg = 1 if i % 2 == 0 else -1
        p.poly([p.P(124, a - 0.05), p.P(124 + sg * (26 if i % 4 == 0 else 16), a + 0.04 * sg), p.P(124, a + 0.05)])
    for i in range(7):
        a = i * TAU / 7
        teardrop(p, *p.P(186, a), a, 12)
        p.line([p.P(150, a), p.P(170, a)], 2)
    teardrop(p, p.cx, p.cy + 8, -math.pi / 2, 26)


def blood_band(p):
    p.line([(0, 6), (p.w, 6)], 4, caps=False)
    for i in range(16):
        x = (i + 0.5) * p.w / 16
        for dx in (-p.w, 0, p.w):
            X = x + dx
            L = 44 if i % 2 == 0 else 26
            p.taper([(X, 6), (X, 6 + L)], [5, 2.4])
            teardrop(p, X, 6 + L + 10, math.pi * 1.5, 9 if i % 2 == 0 else 7)
            p.poly([(X + p.w / 32 - 5, 6), (X + p.w / 32, 26), (X + p.w / 32 + 5, 6)])
    p.line([(0, 120), (p.w, 120)], 2, caps=False)


# ====================================================================== КРАЙ
def ender_seal(p):
    rng = random.Random(707)
    p.ring(246, 4)
    p.ring(214, 2.4)
    for _ in range(420):   # крапинки эндерняка
        a, r = rng.random() * TAU, 218 + rng.random() * 24
        x, y = p.P(r, a)
        p.dot(x, y, 0.8 + rng.random() * 1.8)
    for i in range(12):   # глаза Края
        a = i * TAU / 12
        x, y = p.P(188, a)
        eye(p, x, y, 18, 9, a + math.pi / 2, 2.2, slit=True)
    # тоннель портала: кольца, смещённые по спирали — глубина
    for k in range(6):
        r = 166 - k * 12
        off = 3.5 * k
        p.circle(p.cx + off * math.cos(k * 0.9), p.cy + off * math.sin(k * 0.9), r, 2.8 - k * 0.25)
    for _ in range(46):   # частицы Края: квадратики и звёзды
        a, r = rng.random() * TAU, 104 + rng.random() * 66
        x, y = p.P(r, a)
        if rng.random() < 0.6:
            s = 1.5 + rng.random() * 3
            p.poly(rot([(x - s, y - s), (x + s, y - s), (x + s, y + s), (x - s, y + s)], rng.random(), x, y))
        else:
            star4(p, x, y, 4 + rng.random() * 4, rng.random(), 0.25)
    p.ring(100, 3.5)


def ender_core(p):
    p.ring(94, 3)
    for i in range(16):
        a = i * TAU / 16
        x, y = p.P(86, a)
        s = 3.2
        p.poly(rot([(x - s, y - s), (x + s, y - s), (x + s, y + s), (x - s, y + s)], a, x, y))
    eye(p, p.cx, p.cy, 72, 40, 0, 4, slit=True, iris=0.42)
    p.circle(p.cx, p.cy, 30, 1.6)


def ender_crown(p):
    rng = random.Random(708)
    for k in range(5):
        p.circle(p.cx + 4 * k * math.cos(k), p.cy + 4 * k * math.sin(k), 150 - k * 20, 4 - k * 0.5)
    for i in range(8):
        a = i * TAU / 8
        x, y = p.P(196, a)
        eye(p, x, y, 26, 13, a + math.pi / 2, 2.6, slit=True)
    for _ in range(40):
        a, r = rng.random() * TAU, 60 + rng.random() * 60
        x, y = p.P(r, a)
        s = 1.6 + rng.random() * 2.4
        p.poly(rot([(x - s, y - s), (x + s, y - s), (x + s, y + s), (x - s, y + s)], rng.random(), x, y))
    p.dot(p.cx, p.cy, 22)
    p.poly([(p.cx, p.cy - 16), (p.cx + 4, p.cy), (p.cx, p.cy + 16), (p.cx - 4, p.cy)], 0)


def ender_band(p):
    rng = random.Random(10)
    p.line([(0, 6), (p.w, 6)], 3, caps=False)
    p.line([(0, 122), (p.w, 122)], 3, caps=False)
    for i in range(10):
        x = (i + 0.5) * p.w / 10
        eye(p, x, 64, 34, 18, 0, 3, slit=True)
    for _ in range(140):
        x, y = rng.random() * p.w, 14 + rng.random() * 100
        if abs(((x / (p.w / 10)) % 1) - 0.5) < 0.38:
            continue
        s = 1 + rng.random() * 2.6
        p.poly(rot([(x - s, y - s), (x + s, y - s), (x + s, y + s), (x - s, y + s)], rng.random(), x, y))


# ====================================================================== МИСТИЧЕСКАЯ (eldritch)
def wobbly(p, r, amp, k, w, ph=0.0):
    pts = [p.P(r + amp * math.sin(k * a + ph) + amp * 0.5 * math.sin(3.7 * a + 1.3 + ph), a) for a in [i * TAU / 720 for i in range(721)]]
    p.line(pts, w)


def tentacle(p, rng, base, ang, L, w0, coil, suckers=True):
    pts, ws = [], []
    a = ang
    x, y = base
    n = 44
    for i in range(n + 1):
        t = i / n
        pts.append((x, y))
        ws.append(max(0.8, w0 * (1 - t) ** 0.9))
        a += coil * (0.4 + 2.2 * t * t) / n
        x += math.cos(a) * L / n
        y += math.sin(a) * L / n
    p.taper(pts, ws)
    if suckers:
        for i in range(4, n - 8, 4):
            nx, ny = -math.sin(ang), math.cos(ang)
            q = pts[i]
            p.dot(q[0], q[1], ws[i] * 0.22, 0)
    return pts


def eldritch_seal(p):
    rng = random.Random(808)
    wobbly(p, 242, 3, 7, 4.5)
    wobbly(p, 232, 2.5, 9, 1.8, 1.0)
    polygon(p, 152, 7, -math.pi / 2, 2.2, 3)
    for k in range(7):   # щупальца с присосками, закручены внутрь
        a = k * TAU / 7
        tentacle(p, rng, p.P(228, a), a + math.pi + 0.35, 150, 16, 2.6)
    for k in range(14):   # глаза между щупальцами
        a = k * TAU / 14 + TAU / 28
        r = 200 if k % 2 == 0 else 126
        s = 1.0 if k % 2 == 0 else 0.7
        x, y = p.P(r, a)
        eye(p, x, y, 15 * s, 8 * s, a + math.pi / 2, 2, slit=False, iris=0.4)
    for _ in range(60):
        a, r = rng.random() * TAU, 104 + rng.random() * 120
        x, y = p.P(r, a)
        p.dot(x, y, 0.6 + rng.random() * 1.3)
    wobbly(p, 100, 2, 5, 3.2)


def eldritch_core(p):
    wobbly(p, 92, 3, 6, 3)
    for i in range(30):   # ресницы-шипы вокруг ока
        a = i * TAU / 30
        p.taper([p.P(56, a), p.P(84 if i % 2 else 74, a + 0.05)], [4, 0.6])
    eye(p, p.cx, p.cy, 66, 34, 0, 4, slit=False, iris=0.5)
    p.circle(p.cx, p.cy, 22, 1.4)
    for k in range(3):
        x, y = p.P(36, -math.pi / 2 + k * TAU / 3)
        p.dot(x, y, 2.4)


def eldritch_crown(p):
    rng = random.Random(809)
    wobbly(p, 128, 4, 6, 4)
    wobbly(p, 116, 3, 8, 1.6, 2)
    for k in range(9):
        a = k * TAU / 9
        x, y = p.P(176, a)
        eye(p, x, y, 26, 13, a + math.pi / 2, 2.4, slit=False, iris=0.45)
        tentacle(p, rng, p.P(132, a + TAU / 18), a + TAU / 18 + 0.2, 100, 9, 3.2, suckers=False)
    eye(p, p.cx, p.cy, 54, 28, 0, 3.4, slit=False, iris=0.5)


def eldritch_band(p):
    p.line([(0, 6), (p.w, 6)], 2.5, caps=False)
    p.line([(0, 122), (p.w, 122)], 2.5, caps=False)
    pts = [(x, 64 + 30 * math.sin(x / p.w * TAU * 5) * math.cos(x / p.w * TAU * 2)) for x in np.linspace(0, p.w, 400)]
    p.taper(pts, [6 + 3 * math.sin(i / 400 * TAU * 10) for i in range(400)])
    for i in range(10):
        x = (i + 0.5) * p.w / 10
        y = 64 + 30 * math.sin(x / p.w * TAU * 5) * math.cos(x / p.w * TAU * 2)
        eye(p, x, 30 if y > 64 else 98, 18, 10, 0, 2.2, slit=False, iris=0.42)


# ====================================================================== ПРИЗЫВАНИЕ (evocation)
def fang(p, x, y, ang, L, W):
    """Клык заклинателя (evoker fangs): пара изогнутых зубьев."""
    for sg in (1, -1):
        pts = local((x, y), ang, [(0, sg * W * 0.5), (L * 0.55, sg * W * 0.55), (L, sg * W * 0.05), (L * 0.5, sg * W * 0.12), (0, sg * W * 0.1)])
        p.poly(pts)


def evocation_seal(p):
    frame_outer(p, 5, 2)
    glyph_ring(p, 206, 234, 34, 81, 2.4)
    p.ring(204, 3)
    polygon(p, 204, 4, 0, 2)
    polygon(p, 204, 4, math.pi / 4, 2)
    rng = random.Random(82)
    for arm in range(3):   # вихрь рун: три рукава по спирали, вдоль каждого — направляющая
        a0 = arm * TAU / 3
        p.line([p.P(116 + 82 * t, a0 + 2.4 * t - 0.16) for t in np.linspace(0, 1, 60)], 1.3)
        for j in range(11):
            t = j / 10
            r = 122 + 74 * t
            a = a0 + 2.4 * t
            x, y = p.P(r, a)
            glyph_at(p, rng, x, y, 15 + 13 * t, a + math.pi / 2 + 0.55, 2.0 + 1.0 * t)
    for i in range(16):   # клыки по внутреннему кругу
        a = i * TAU / 16
        fang(p, *p.P(110, a), a, 28, 14)
    for i in range(8):
        x, y = p.P(172, i * TAU / 8 + TAU / 16)
        p.circle(x, y, 9, 1.8)
        p.dot(x, y, 3)
    p.ring(104, 3.5)


def evocation_core(p):
    p.ring(94, 3.5)
    glyph_ring(p, 70, 90, 16, 83, 1.8)
    p.ring(68, 2)
    polygon(p, 66, 3, -math.pi / 2, 3)
    polygon(p, 66, 3, math.pi / 2, 3)
    for k in range(6):
        x, y = p.P(66, -math.pi / 2 + k * TAU / 6)
        p.dot(x, y, 6)
        p.dot(x, y, 3, 0)
    p.ring(30, 2.4)
    for sg in (1, -1):   # крылья векса в центре
        for k in range(3):
            feather(p, (p.cx, p.cy), math.pi / 2 * (1 - sg) + sg * (-0.5 + k * 0.45) + (0 if sg > 0 else 0), 26 - k * 4, 9)
    p.dot(p.cx, p.cy, 5)


def evocation_crown(p):
    p.ring(150, 4)
    glyph_ring(p, 116, 146, 20, 84, 2.6)
    p.ring(114, 2)
    for i in range(12):
        a = i * TAU / 12
        fang(p, *p.P(152, a), a, 64, 26)
    polygon(p, 110, 3, -math.pi / 2, 2.4)
    polygon(p, 110, 3, math.pi / 2, 2.4)
    p.ring(40, 3)
    p.dot(p.cx, p.cy, 12)


def evocation_band(p):
    rng = random.Random(85)
    p.line([(0, 6), (p.w, 6)], 3, caps=False)
    p.line([(0, 122), (p.w, 122)], 3, caps=False)
    for i in range(10):
        x = (i + 0.5) * p.w / 10
        p.line([(x - 40, 24), (x + 40, 24), (x + 40, 104), (x - 40, 104), (x - 40, 24)], 2.2)
        glyph_at(p, rng, x, 64, 64, -math.pi / 2, 4)
        fang(p, x + p.w / 20, 118, -math.pi / 2, 40, 18)


# ====================================================================== ВЕТЕР
def wind_seal(p):
    rng = random.Random(909)
    for i in range(24):   # обод из порывов: дуги с разрывами
        a = i * TAU / 24
        p.arc(244, a, a + TAU / 24 * 0.72, 4)
    p.ring(236, 1.2)
    for k in range(6):   # потоки: спирали с тонкими линиями тока по бокам
        a = k * TAU / 6
        spiral(p, 104, 230, a, 2.0, 2, 1.2, wmid=9)
        for off, w in ((0.13, 1.5), (-0.13, 1.5), (0.24, 1.0)):
            pts = [p.P(116 + 104 * t, a + off + 1.8 * t + 0.15) for t in np.linspace(0.1, 0.85, 40)]
            p.line(pts, w)
    for k in range(12):   # завитки
        a = k * TAU / 12 + 0.25
        x, y = p.P(168 if k % 2 else 206, a)
        curl(p, x, y, 13 if k % 2 else 9, a, 1.6, 2.2, -1)
    for _ in range(18):   # короткие штрихи-порывы
        a, r = rng.random() * TAU, 120 + rng.random() * 100
        p.arc(r, a, a + 0.12 + rng.random() * 0.1, 1.6)
    p.ring(100, 2.4)


def wind_core(p):
    p.ring(94, 2.4)
    for k in range(3):   # трискель из сужающихся спиралей
        a = k * TAU / 3
        spiral(p, 6, 86, a, 3.0, 2, 1, wmid=13)
        spiral(p, 28, 78, a + 1.0, 1.6, 1, 0.8, wmid=4)
    p.dot(p.cx, p.cy, 9)


def wind_crown(p):
    for k in range(5):
        a = k * TAU / 5
        spiral(p, 60, 240, a, 2.3, 2, 0.8, wmid=12)
    for i in range(30):
        a = i * TAU / 30
        p.arc(140, a, a + TAU / 30 * 0.6, 2.4)
    for k in range(3):
        spiral(p, 4, 54, k * TAU / 3, 2.6, 2, 1, wmid=9)


def wind_band(p):
    p.line([(0, 6), (p.w, 6)], 2, caps=False)
    for i in range(8):
        x = (i + 0.5) * p.w / 8
        pts = [(x - 70 + 140 * t, 70 - 30 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 40)]
        p.taper(pts, [1 + 6 * math.sin(math.pi * t) for t in np.linspace(0, 1, 40)])
        curl(p, x + 70, 70, 18, math.pi, 1.4, 3, -1)
        pts = [(x - 50 + 90 * t, 104) for t in np.linspace(0, 1, 2)]
        p.line(pts, 2)
    p.line([(0, 122), (p.w, 122)], 2, caps=False)


# ====================================================================== спрайты частиц (128)
def mote(name, fn, glow=0.7):
    p = Pen(128, 128)
    fn(p)
    save_sigil(p, 'mote_' + name, glow=glow, glow_r=4)


def motes():
    mote('flame', lambda p: flame(p, (64, 118), -math.pi / 2 + 0.05, 108, 52, curl=0.18))
    mote('ice', lambda p: crystal(p, 64, 120, -math.pi / 2, 112, 34))
    def bolt_m(p):
        bolt(p, random.Random(5), (76, 4), (52, 124), 9, 3, branches=1, depth=3, amp=0.3)
    mote('bolt', bolt_m)
    mote('leaf', lambda p: leaf(p, (14, 110), -math.pi / 4, 128, 54, bend=0.08))
    mote('feather', lambda p: feather(p, (18, 112), -math.pi / 4, 130, 40))
    mote('drop', lambda p: teardrop(p, 64, 82, -math.pi / 2, 30))
    def ender_m(p):
        p.poly(rot([(40, 40), (88, 40), (88, 88), (40, 88)], 0.3, 64, 64))
        p.poly(rot([(52, 52), (76, 52), (76, 76), (52, 76)], 0.3, 64, 64), 0)
        p.dot(64, 64, 6)
    mote('ender', ender_m)
    mote('eye', lambda p: eye(p, 64, 64, 56, 30, 0, 5, slit=False, iris=0.5))
    mote('rune', lambda p: glyph_at(p, random.Random(3), 64, 64, 100, -math.pi / 2, 9))
    def wisp(p):
        pts = [(10 + 100 * t, 80 - 40 * math.sin(math.pi * t * 0.9)) for t in np.linspace(0, 1, 40)]
        p.taper(pts, [1 + 12 * math.sin(math.pi * t) for t in np.linspace(0, 1, 40)])
        curl(p, 108, 74, 16, math.pi, 1.3, 4, -1)
    mote('wisp', wisp)


# ====================================================================== оберег Восьми щитов (бывший gen_school_sigils.ps1)
def circle_ward():
    p = Pen()
    rng = random.Random(21)
    p.ring(248, 7)
    p.ring(236, 3)
    ticks(p, 236, 64, 10, 3)
    for i in range(36):
        a = i * TAU / 36
        x, y = p.P(210, a)
        glyph_at(p, rng, x, y, 22, a + math.pi, 3)
    p.ring(194, 4)
    polygon(p, 186, 8, math.pi / 8, 6)
    for i in range(8):
        a = i * TAU / 8
        x, y = p.P(150, a)
        sh = [(-18, -20), (18, -20), (18, 2), (0, 24), (-18, 2), (-18, -20)]
        p.line(local((x, y), a + math.pi / 2, [(sy, -sx) for sx, sy in sh]), 4)
        p.line(local((x, y), a + math.pi / 2, [(-14, 0), (14, 0)]), 3)
        p.line(local((x, y), a + math.pi / 2, [(-4, -10), (-4, 10)]), 3)
    p.ring(112, 4)
    polygon(p, 108, 8, 0, 3, 3)
    p.ring(52, 3)
    polygon(p, 50, 4, math.pi / 4, 4)
    save_fx_black(to_alpha(p, glow=0), 'circle_ward')


# ====================================================================== школы: данные
SCHOOLS = {
    'fire': dict(name='Огонь', style='fire', palette=dict(primary='#FF7A2A', secondary='#FFD27A', core='#FFF4E0', shadow='#7A1E00'),
                 seal_color='#FF7A2A', core_color='#FFD27A', band_color='#FFB04A', crown_color='#FF9A3A', mote='flame',
                 motion=dict(rotationScale=1.2, jitter=0.15, easing='easeOutCubic', pulse=dict(amp=0.12, period=9)),
                 idea='языки пламени по ободу, алхимический треугольник огня, вихрь из трёх языков в центре'),
    'ice': dict(name='Лёд', style='ice', palette=dict(primary='#9FE0FF', secondary='#E8FAFF', core='#FFFFFF', shadow='#2A5A8A'),
                seal_color='#9FE0FF', core_color='#E8FAFF', band_color='#BFEFFF', crown_color='#CFF4FF', mote='ice',
                motion=dict(rotationScale=0.6, jitter=0.0, easing='easeOutCubic'),
                idea='снежинка с ветвящимися лучами, сосульки по ободу, кристаллы с гранями'),
    'lightning': dict(name='Молния', style='lightning', palette=dict(primary='#6BE6FF', secondary='#E6FBFF', core='#FFFFFF', shadow='#1A3A8A'),
                      seal_color='#6BE6FF', core_color='#E6FBFF', band_color='#9AF0FF', crown_color='#BFF6FF', mote='bolt',
                      motion=dict(rotationScale=1.8, jitter=0.6, easing='easeOutCubic', pulse=dict(amp=0.25, period=4)),
                      idea='разветвлённые разряды от обода внутрь, зубчатое кольцо, звезда бури в центре'),
    'nature': dict(name='Природа', style='nature', palette=dict(primary='#7EE04A', secondary='#D8FF9A', core='#FFFFFF', shadow='#2A5A10'),
                   seal_color='#7EE04A', core_color='#D8FF9A', band_color='#A8F070', crown_color='#B8F27A', mote='leaf',
                   motion=dict(rotationScale=0.5, jitter=0.0, easing='easeOutSine', pulse=dict(amp=0.1, period=40)),
                   idea='венок из двух переплетённых лоз с листьями, побеги с усиками, цветок с семенами по золотому углу'),
    'holy': dict(name='Святая', style='holy', palette=dict(primary='#FFE38A', secondary='#FFFBE6', core='#FFFFFF', shadow='#8A6420'),
                 seal_color='#FFE38A', core_color='#FFFBE6', band_color='#FFEFB0', crown_color='#FFF2C0', mote='feather',
                 motion=dict(rotationScale=0.5, jitter=0.0, easing='easeOutSine'),
                 idea='лучи-клинья, два крыла из трёх рядов перьев, восьмиконечная звезда'),
    'blood': dict(name='Кровь', style='school_blood', palette=dict(primary='#E0242C', secondary='#FF8A8A', core='#FFD6D6', shadow='#4A0006'),
                  seal_color='#E0242C', core_color='#FF5A5A', band_color='#C8101C', crown_color='#FF3A3A', mote='drop',
                  motion=dict(rotationScale=0.8, jitter=0.0, easing='easeOutSine', pulse=dict(amp=0.22, period=16)),
                  idea='вены от внутреннего круга, капли на нитях, терновое кольцо, полумесяц с каплей'),
    'ender': dict(name='Край', style='ender', palette=dict(primary='#C060FF', secondary='#F0C8FF', core='#FFFFFF', shadow='#2A0A4A'),
                  seal_color='#C060FF', core_color='#F0C8FF', band_color='#9A50E0', crown_color='#D890FF', mote='ender',
                  motion=dict(rotationScale=0.9, jitter=0.2, easing='easeOutCubic'),
                  idea='тоннель портала из смещённых колец, глаза Края, крапинки эндерняка, частицы-квадратики'),
    'eldritch': dict(name='Мистическая', style='eldritch', palette=dict(primary='#3FD6B8', secondary='#B8FFF0', core='#FFFFFF', shadow='#0A3A30'),
                     seal_color='#3FD6B8', core_color='#B8FFF0', band_color='#2AA890', crown_color='#7FF0D8', mote='eye',
                     motion=dict(rotationScale=0.7, jitter=0.3, easing='easeInOutSine', pulse=dict(amp=0.18, period=26)),
                     idea='щупальца с присосками, глаза между ними, кривые «живые» кольца, око с ресницами-шипами'),
    'evocation': dict(name='Призывание', style='evocation', palette=dict(primary='#DDE6F0', secondary='#FFFFFF', core='#FFFFFF', shadow='#5A6A80'),
                      seal_color='#DDE6F0', core_color='#FFFFFF', band_color='#C8D6E6', crown_color='#E8F0FA', mote='rune',
                      motion=dict(rotationScale=1.0, jitter=0.0, easing='easeOutCubic'),
                      idea='вихрь рун тремя рукавами, клыки заклинателя, круг призыва с крыльями векса'),
    'wind': dict(name='Ветер', style='wind', palette=dict(primary='#BFF2E8', secondary='#FFFFFF', core='#FFFFFF', shadow='#3A7A70'),
                 seal_color='#BFF2E8', core_color='#FFFFFF', band_color='#A8E8DC', crown_color='#D8FFF6', mote='wisp',
                 motion=dict(rotationScale=1.6, jitter=0.1, easing='easeOutSine'),
                 idea='спиральные потоки с линиями тока, завитки, обод из порывов, трискель'),
}

DRAW = {s: (globals()[s + '_seal'], globals()[s + '_core'], globals()[s + '_crown'], globals()[s + '_band']) for s in SCHOOLS}


# ====================================================================== печати: как появляется и распадается каждая школа
def L_glow(color, r=0.95, b=1.1, dur=8):
    return dict(id='glow', type='disc', texture='glow', radius=r, heightOffset=0.0, color=color, brightness=b,
                appear=dict(delay=0, duration=dur, easing='easeOutCubic', modes=['grow', 'fade']))


def seal_def(s):
    S = SCHOOLS[s]
    c, cc, bc, sh = S['seal_color'], S['core_color'], S['band_color'], S['palette']['shadow']
    seal = dict(id='seal', type='disc', texture=s + '_seal', radius=1.0, heightOffset=0.01)
    band = dict(id='band', type='band', texture='school_%s_band' % s, radius=1.22, inner=0.87, repeat=10, heightOffset=0.02, color=bc, brightness=0.85)
    core = dict(id='core', type='disc', texture=s + '_core', radius=0.4, heightOffset=0.03, color=cc)
    arcs = dict(id='arcs', type='arcs', texture='arc_strip', radius=1.3, width=0.03, heightOffset=0.04, count=3, arcLength=70, color=bc, brightness=0.8)
    flash = dict(color=S['palette']['secondary'], size=1.35, duration=10, sparks=28)
    d = dict(size=2.4, color=c, orientation='ground', lifetime=-1, hold=-1)
    if s == 'fire':
        # языки пламени слетаются по частям и встают со вспышкой, лента прорисовывается навстречу; распад — вспышкой наружу
        seal.update(appear=dict(delay=2, duration=26, easing='easeOutBack', modes=['pieces'],
                                pieces=dict(count=12, order='scatter', pieceTime=0.4, fly=0.5, lift=0.35, orbit=30, tilt=50, spin=60, lockFlash=1.0)),
                    rotation=dict(speed=22, boost=0), pulse=dict(amp=0.1, period=9))
        band.update(appear=dict(delay=10, duration=16, easing='easeInOutSine', modes=['draw'], startAngle=270, direction=-1), rotation=dict(speed=-30, boost=2))
        core.update(appear=dict(delay=20, duration=12, easing='easeOutBack', modes=['grow', 'twist'], twist=-240), rotation=dict(speed=-70, boost=3))
        arcs.update(appear=dict(delay=24, duration=10, easing='easeInOutCubic', modes=['assemble', 'fade']), rotation=dict(speed=40, boost=4))
        d['dissolve'] = dict(modes=['shatter', 'fade'], duration=14, stagger=2)
        flash.update(sparks=40)
    elif s == 'ice':
        # кристаллы нарастают по кругу один за другим (как иней), ядро-снежинка раскрывается из ребра; распад — раскол
        seal.update(appear=dict(delay=2, duration=30, easing='easeOutCubic', modes=['pieces'],
                                pieces=dict(count=6, order='around', pieceTime=0.45, fly=0.25, lift=0.6, orbit=0, tilt=90, spin=0, lockFlash=1.4)),
                    rotation=dict(speed=6, boost=0))
        band.update(appear=dict(delay=14, duration=18, easing='easeOutSine', modes=['draw'], startAngle=90, direction=1), rotation=dict(speed=-8, boost=1))
        core.update(appear=dict(delay=26, duration=12, easing='easeOutCubic', modes=['unfold', 'fade']), rotation=dict(speed=-14, boost=0))
        arcs.update(appear=dict(delay=30, duration=10, easing='easeInOutCubic', modes=['assemble', 'fade']), rotation=dict(speed=10, boost=2))
        d['dissolve'] = dict(modes=['shatter', 'reverse'], duration=16, stagger=2)
        flash.update(size=1.25, sparks=24)
    elif s == 'lightning':
        # всё быстро: разряд прорисовывается за 6 тиков и бешено крутится, пульс-мерцание; распад — мгновенное угасание
        seal.update(appear=dict(delay=0, duration=6, easing='easeOutCubic', modes=['draw', 'fade'], startAngle=0, direction=1),
                    rotation=dict(speed=50, boost=8), pulse=dict(amp=0.22, period=4))
        band.update(appear=dict(delay=2, duration=6, easing='linear', modes=['draw'], startAngle=180, direction=-1), rotation=dict(speed=-90, boost=4), pulse=dict(amp=0.3, period=3))
        core.update(appear=dict(delay=6, duration=6, easing='easeOutBack', modes=['grow']), rotation=dict(speed=-120, boost=2), pulse=dict(amp=0.25, period=5))
        arcs.update(count=4, arcLength=50, appear=dict(delay=4, duration=8, easing='easeOutCubic', modes=['assemble', 'fade']), rotation=dict(speed=120, boost=3))
        d['dissolve'] = dict(modes=['fade', 'shatter'], duration=8, stagger=1)
        flash.update(size=1.6, duration=6, sparks=50)
    elif s == 'nature':
        # медленно прорастает: рост с доворотом из центра, лозы тянутся по кругу, цветок раскрывается; распад — увядание
        seal.update(appear=dict(delay=0, duration=30, easing='easeOutSine', modes=['grow', 'twist', 'fade'], twist=-90), rotation=dict(speed=5, boost=1))
        band.update(appear=dict(delay=12, duration=26, easing='easeInOutSine', modes=['draw'], startAngle=90, direction=1), rotation=dict(speed=-4, boost=1))
        core.update(appear=dict(delay=24, duration=16, easing='easeOutBack', modes=['grow', 'twist'], twist=120), rotation=dict(speed=-10, boost=0),
                    pulse=dict(amp=0.12, period=40))
        arcs = None
        d['dissolve'] = dict(modes=['reverse', 'fade', 'collapse'], duration=24, stagger=4)
        flash.update(size=1.2, sparks=16)
    elif s == 'holy':
        # раскрывается из ребра, как крылья; после формирования мягко вырастает; распад — растворение в свете
        seal.update(appear=dict(delay=2, duration=20, easing='easeOutCubic', modes=['unfold', 'fade']), rotation=dict(speed=4, boost=0))
        band.update(appear=dict(delay=10, duration=16, easing='easeInOutSine', modes=['draw'], startAngle=90, direction=1), rotation=dict(speed=-6, boost=1))
        core.update(appear=dict(delay=18, duration=12, easing='easeOutBack', modes=['grow', 'fade']), rotation=dict(speed=-10, boost=0),
                    pulse=dict(amp=0.12, period=30))
        arcs.update(appear=dict(delay=22, duration=10, easing='easeInOutCubic', modes=['assemble', 'fade']), rotation=dict(speed=12, boost=2))
        d['expand'] = dict(scale=1.18, delay=0, duration=14, easing='easeOutSine')
        d['dissolve'] = dict(modes=['fade', 'reverse'], duration=20, stagger=3)
        flash.update(size=1.6, duration=14, sparks=30)
    elif s == 'blood':
        # прорисовывается пером сверху вниз, бьётся пульсом сердца; распад — стягивается в каплю
        seal.update(appear=dict(delay=2, duration=18, easing='easeInOutSine', modes=['draw'], startAngle=90, direction=-1),
                    rotation=dict(speed=10, boost=2), pulse=dict(amp=0.2, period=16))
        band.update(appear=dict(delay=8, duration=16, easing='easeInOutSine', modes=['draw'], startAngle=90, direction=1), rotation=dict(speed=-12, boost=2))
        core.update(appear=dict(delay=16, duration=10, easing='easeOutBack', modes=['grow']), rotation=dict(speed=-16, boost=0), pulse=dict(amp=0.25, period=16))
        arcs.update(appear=dict(delay=20, duration=10, easing='easeInOutCubic', modes=['assemble', 'fade']), rotation=dict(speed=20, boost=3))
        d['dissolve'] = dict(modes=['reverse', 'collapse'], duration=16, stagger=2)
        flash.update(sparks=22)
    elif s == 'ender':
        # части телепортируются: прилетают парами напротив друг друга с полуоборота, без кувырка; распад — затягивает в портал
        seal.update(appear=dict(delay=2, duration=24, easing='easeOutCubic', modes=['pieces'],
                                pieces=dict(count=8, order='alternate', pieceTime=0.3, fly=0.15, lift=1.2, orbit=180, tilt=0, spin=180, lockFlash=1.6)),
                    rotation=dict(speed=-12, boost=0))
        band.update(appear=dict(delay=12, duration=14, easing='easeOutCubic', modes=['draw', 'fade'], startAngle=0, direction=1), rotation=dict(speed=20, boost=3))
        core.update(appear=dict(delay=20, duration=12, easing='easeOutCubic', modes=['unfold', 'twist'], twist=180), rotation=dict(speed=30, boost=2))
        arcs.update(appear=dict(delay=22, duration=10, easing='easeInOutCubic', modes=['assemble', 'fade']), rotation=dict(speed=-30, boost=4))
        d['dissolve'] = dict(modes=['collapse', 'fade'], duration=14, stagger=0)
        flash.update(size=1.2, sparks=34)
    elif s == 'eldritch':
        # щупальца выползают по частям с кувырком, око открывается (unfold); дыхание-пульс; распад — рвётся на клочья
        seal.update(appear=dict(delay=2, duration=30, easing='easeOutCubic', modes=['pieces'],
                                pieces=dict(count=7, order='scatter', pieceTime=0.5, fly=0.6, lift=0.2, orbit=70, tilt=110, spin=90, lockFlash=0.6)),
                    rotation=dict(speed=-6, boost=0), pulse=dict(amp=0.15, period=26))
        band.update(appear=dict(delay=14, duration=18, easing='easeInOutSine', modes=['draw'], startAngle=270, direction=-1), rotation=dict(speed=9, boost=2))
        core.update(appear=dict(delay=26, duration=14, easing='easeInOutSine', modes=['unfold', 'fade']), rotation=dict(speed=4, boost=0), pulse=dict(amp=0.2, period=26))
        arcs.update(count=5, arcLength=40, appear=dict(delay=28, duration=12, easing='easeInOutCubic', modes=['assemble', 'fade']), rotation=dict(speed=-18, boost=3))
        d['dissolve'] = dict(modes=['reverse', 'shatter'], duration=18, stagger=3)
        flash.update(size=1.3, sparks=20)
    elif s == 'evocation':
        # руны-ячейки ленты встают по кругу одна за другой, печать прорисовывается, клыки смыкаются; распад — обратный
        band.update(appear=dict(delay=2, duration=26, easing='easeOutBack', modes=['pieces'],
                                pieces=dict(count=10, order='around', pieceTime=0.35, fly=0.3, lift=0.5, orbit=20, tilt=80, spin=0, lockFlash=1.0)),
                    rotation=dict(speed=-16, boost=0), repeat=10)
        seal.update(appear=dict(delay=6, duration=16, easing='easeInOutSine', modes=['draw'], startAngle=90, direction=1), rotation=dict(speed=14, boost=3))
        core.update(appear=dict(delay=18, duration=12, easing='easeOutCubic', modes=['grow', 'twist'], twist=-180), rotation=dict(speed=-28, boost=2))
        arcs.update(appear=dict(delay=24, duration=10, easing='easeInOutCubic', modes=['assemble', 'fade']), rotation=dict(speed=24, boost=4))
        d['dissolve'] = dict(modes=['reverse', 'collapse'], duration=14, stagger=2)
    elif s == 'wind':
        # закручивается вихрем: большой доворот и быстрое вращение, которое оседает; распад — сдувает наружу
        seal.update(appear=dict(delay=0, duration=18, easing='easeOutCubic', modes=['grow', 'twist', 'fade'], twist=-320), rotation=dict(speed=36, boost=6))
        band.update(appear=dict(delay=6, duration=14, easing='easeOutSine', modes=['draw', 'fade'], startAngle=0, direction=1), rotation=dict(speed=48, boost=3))
        core.update(appear=dict(delay=12, duration=10, easing='easeOutCubic', modes=['grow', 'twist'], twist=360), rotation=dict(speed=90, boost=2))
        arcs.update(count=5, arcLength=36, appear=dict(delay=10, duration=12, easing='easeOutCubic', modes=['assemble', 'fade']), rotation=dict(speed=70, boost=3))
        d['dissolve'] = dict(modes=['shatter', 'fade'], duration=14, stagger=1)
        flash.update(sparks=20)
    layers = [L_glow(sh), seal, band, core] + ([arcs] if arcs else [])
    d['layers'] = layers
    d['formedFlash'] = flash
    d['groundLight'] = dict(radius=0.7, strength=0.45)
    d = {'comment': 'T06, школа «%s», ступени Высшая/Мифическая/Божественная: печать под магом на время каста (hold -1 — гасит код в конце каста). '
                    'Рисунок: %s. Сгенерировано tools/gen_school_themes.py.' % (S['name'], S['idea']), **d}
    return d


def crown_def(s):
    S = SCHOOLS[s]
    c = S['crown_color']
    mode = {'fire': (['grow', 'fade'], 'easeOutBack', 50), 'ice': (['unfold', 'fade'], 'easeOutCubic', 10),
            'lightning': (['draw', 'fade'], 'easeOutCubic', 110), 'nature': (['grow', 'twist'], 'easeOutSine', 8),
            'holy': (['unfold', 'fade'], 'easeOutSine', 6), 'blood': (['draw'], 'easeInOutSine', 14),
            'ender': (['grow', 'twist'], 'easeOutCubic', -24), 'eldritch': (['unfold', 'fade'], 'easeInOutSine', -8),
            'evocation': (['draw', 'fade'], 'easeInOutSine', 20), 'wind': (['grow', 'twist', 'fade'], 'easeOutCubic', 80)}[s]
    ap = dict(delay=2, duration=14, easing=mode[1], modes=mode[0])
    if 'draw' in mode[0]:
        ap.update(startAngle=90, direction=1)
    if 'twist' in mode[0]:
        ap['twist'] = 270
    layers = [
        L_glow(S['palette']['shadow'], 0.8, 0.9, 8),
        dict(id='crown', type='disc', texture=s + '_crown', radius=1.0, heightOffset=0.01, appear=ap, rotation=dict(speed=mode[2], boost=2),
             **({'pulse': S['motion']['pulse']} if 'pulse' in S['motion'] else {})),
        dict(id='ring', type='disc', texture='thin_ring', radius=1.12, heightOffset=0.02, color=S['palette']['secondary'], brightness=0.7,
             appear=dict(delay=8, duration=10, easing='easeOutCubic', modes=['grow', 'fade'])),
    ]
    return {'comment': 'T06, школа «%s»: венец над головой мага для ступеней Мифическая и Божественная (fx/school_%s_cast_crown.json). '
                       'Сгенерировано tools/gen_school_themes.py.' % (S['name'], s),
            'size': 0.75, 'color': c, 'orientation': 'sky', 'lifetime': -1, 'hold': -1, 'layers': layers,
            'formedFlash': dict(color=S['palette']['core'], size=1.3, duration=8, sparks=14),
            'dissolve': dict(modes=['fade', 'collapse'], duration=12, stagger=0)}


def ordinary_def(s):
    """Знак обычного каста (PohSpell.onCast): лёгкий, короткий — новые текстуры печати и ядра."""
    S = SCHOOLS[s]
    return {'comment': 'Знак школы «%s» под магом при каждом касте обычной магии (PohSpell.onCast): короткий, на текстурах T06 (%s_seal, %s_core). '
                       'Сгенерировано tools/gen_school_themes.py.' % (S['name'], s, s),
            'size': 1.9, 'color': S['seal_color'], 'orientation': 'ground', 'lifetime': -1, 'hold': 12,
            'layers': [
                L_glow(S['palette']['shadow'], 0.8, 1.1, 5),
                dict(id='sign', type='disc', texture=s + '_seal', radius=0.9, heightOffset=0.01,
                     appear=dict(delay=0, duration=9, easing='easeOutCubic', modes=['draw'], startAngle=90, direction=1), rotation=dict(speed=30, boost=3)),
                dict(id='core', type='disc', texture=s + '_core', radius=0.36, heightOffset=0.02, color=S['core_color'],
                     appear=dict(delay=3, duration=8, easing='easeOutBack', modes=['grow', 'twist'], twist=-180), rotation=dict(speed=-50, boost=2)),
                dict(id='band', type='band', texture='school_%s_band' % s, radius=1.08, inner=0.94, repeat=8, heightOffset=0.03,
                     color=S['band_color'], brightness=0.85,
                     appear=dict(delay=2, duration=9, easing='easeInOutSine', modes=['draw'], startAngle=270, direction=-1), rotation=dict(speed=-24, boost=2)),
            ],
            'formedFlash': dict(color=S['palette']['secondary'], size=1.3, duration=8, sparks=18),
            'dissolve': dict(modes=['reverse', 'collapse'], duration=10, stagger=2)}


# ====================================================================== эффекты каста
def particles(s):
    """Частицы школы на время каста (элементы fx). Без duration — до остановки эффекта."""
    m = 'mote_' + SCHOOLS[s]['mote']
    base = dict(type='sprites', delay=4, at='caster+0,0.1,0', follow=True, texture=m, count=2000, color='@primary')
    if s == 'fire':
        return [dict(base, rate=1.6, area=2.2, speed=0.025, gravity=-0.004, spin=30, size=[0.34, 0.08], life=26, glow=0.6),
                dict(base, texture='spark_soft', rate=2.5, area=1.4, speed=0.05, gravity=-0.006, size=[0.1, 0.02], life=30, color='@secondary')]
    if s == 'ice':
        return [dict(base, at='caster+0,2.6,0', rate=1.2, area=2.4, speed=0.0, gravity=0.0015, spin=40, tumble=0.6, sway=0.6, size=[0.24, 0.16], life=60, color='@secondary'),
                dict(base, texture='snowflake', at='caster+0,2.2,0', rate=0.6, area=2.0, speed=0.0, gravity=0.001, spin=60, size=[0.3, 0.1], life=60)]
    if s == 'lightning':
        return [dict(base, rate=2.0, area=2.2, speed=0.04, gravity=0.0, spin=200, size=[0.3, 0.05], life=8, glow=0.8, color='@secondary'),
                dict(type='lightning', delay=6, duration=9999, at='caster+1.6,0.1,0', to='caster+-1.6,0.1,0.4', branches=2, jaggedness=0.35, regen=3, width=0.05, color='@primary'),
                dict(type='lightning', delay=10, duration=9999, at='caster+0,0.1,1.7', to='caster+0.3,0.1,-1.6', branches=1, jaggedness=0.35, regen=4, width=0.04, color='@secondary')]
    if s == 'nature':
        return [dict(base, rate=0.8, area=2.4, speed=0.012, gravity=-0.0015, spin=40, tumble=0.8, sway=1.0, size=[0.26, 0.2], life=60),
                dict(base, texture='spark_soft', rate=1.0, area=2.0, speed=0.01, gravity=-0.002, size=[0.08, 0.03], life=50, color='@secondary')]
    if s == 'holy':
        return [dict(base, at='caster+0,3.0,0', rate=0.5, area=2.2, speed=0.0, gravity=0.0012, sway=1.0, tumble=0.6, size=[0.3, 0.22], life=70, color='@secondary'),
                dict(type='curtain', delay=10, duration=9999, at='caster', count=12, radius=[1.6, 2.4], height=[3, 5], grow=20, width=[0.04, 0.08],
                     brightness=[0.3, 0.6], texture='beam_fade', flicker=0.2, color='@primary', **{'in': dict(duration=20, easing='easeOutSine')})]
    if s == 'blood':
        return [dict(base, at='caster+0,1.4,0', rate=0.9, area=1.6, speed=0.0, gravity=0.004, size=[0.2, 0.14], life=24, blend='translucent', color='@primary'),
                dict(type='aura', delay=8, duration=9999, at='caster', target='caster', thickness=0.12, pulse=dict(amp=0.4, period=16), motes=8, color='@primary')]
    if s == 'ender':
        return [dict(type='vortex', delay=6, duration=9999, at='caster+0,0.15,0', radius=2.4, height=0, arms=4, speed=4, pull=0.6, texture=m, particles=40, life=30, size=0.16, color='@primary'),
                dict(base, rate=0.9, area=2.0, speed=0.01, gravity=-0.001, spin=90, size=[0.16, 0.05], life=40, color='@secondary')]
    if s == 'eldritch':
        return [dict(type='ribbon', delay=8, duration=9999, at='caster+0,0.2,0', width=0.18, length=18, fade=1.5, count=5,
                     orbit=dict(radius=1.8, speed=5, rise=0.6, risePeriod=40, climb=0), color='@primary'),
                dict(base, rate=0.35, area=2.2, speed=0.006, gravity=-0.0012, size=[0.12, 0.3], life=50, color='@secondary')]
    if s == 'evocation':
        return [dict(type='trail', delay=6, duration=9999, at='caster+0,0.3,0', width=0.08, length=12, count=3,
                     orbit=dict(radius=1.4, speed=8, rise=0.8, risePeriod=30, climb=0), color='@primary'),
                dict(base, rate=0.8, area=2.0, speed=0.018, gravity=-0.002, spin=0, size=[0.3, 0.1], life=36, color='@secondary')]
    if s == 'wind':
        return [dict(type='vortex', delay=4, duration=9999, at='caster', radius=2.2, height=3.2, arms=3, speed=9, pull=0.2, funnel=0.45, turns=1.4, width=0.08,
                     texture=m, particles=36, life=24, size=0.28, color='@primary'),
                dict(base, rate=1.2, area=2.6, speed=0.05, gravity=-0.001, spin=120, size=[0.36, 0.1], life=22, color='@secondary')]
    return []


def cast_fx(s, crown):
    S = SCHOOLS[s]
    el = [dict(type='sigil', id=s + '_seal', delay=0, at='caster+0,0.04,0', follow=True),
          dict(type='flash', delay=0, duration=10, at='caster+0,0.4,0', size=2.2, color='@secondary', brightness=0.7),
          dict(type='wave', shape='ring', delay=0, duration=16, at='caster', radius=4.0, color='@primary')]
    el += particles(s)
    if crown:
        el.insert(1, dict(type='sigil', id=s + '_crown', delay=10, at='caster+0,2.55,0', follow=True))
        el.append(dict(type='flash', delay=10, duration=10, at='caster+0,2.55,0', size=1.4, color='@core', brightness=0.6, rays=6))
    tier = 'Мифическая: печать + венец над головой' if crown else 'Высшая: печать под магом'
    return {'comment': 'T06, школа «%s», ступень %s + частицы школы. duration -1: код останавливает эффект в конце каста (Fx.stop). '
                       'Сгенерировано tools/gen_school_themes.py.' % (S['name'], tier),
            'style': S['style'], 'duration': -1, 'elements': el}


def divine_fx(s):
    """Божественная ступень: как у Мифической (печать + венец) и дуга из 7 золотых кругов за спиной — с краёв к центру,
    чуть наклонены к магу; золотые блёстки поднимаются от дуги."""
    d = cast_fx(s, True)
    n = 7
    for i in range(n):
        a = math.radians(-72 + 144 * i / (n - 1))
        x, z = 1.9 * math.sin(a), -(1.9 * math.cos(a) * 0.6 + 0.55)
        y = 1.55 + 0.35 * math.cos(a)
        delay = 14 + (n // 2 - abs(i - n // 2)) * 0 + abs(i - n // 2) * -3 + 9
        d['elements'].append(dict(type='sigil', id='golden_halo', delay=delay, at='caster+%.2f,%.2f,%.2f' % (x, y, z), follow=True,
                                  orientation='facing', sigilScale=1.15 if i == n // 2 else 0.95))
    d['elements'].append(dict(type='sprites', delay=16, duration=9999, at='caster+0,1.6,-0.9', follow=True, texture='@sparks', count=4000,
                              rate=1.5, spread=1.8, speed=0.01, gravity=-0.002, size=[0.1, 0.02], life=40, color='#FFD36B'))
    d['elements'].append(dict(type='flash', delay=22, duration=12, at='caster+0,1.7,-1.0', follow=True, size=2.4, rays=8, color='#FFE9A8', brightness=0.6))
    d['comment'] = ('T06, школа «%s», ступень Божественная: печать под магом + венец над головой + дуга из 7 золотых кругов за спиной '
                    '(с краёв к центру), золотые блёстки. duration -1: код останавливает эффект в конце каста. Сгенерировано tools/gen_school_themes.py.'
                    % SCHOOLS[s]['name'])
    return d


def ordinary_fx(s):
    S = SCHOOLS[s]
    return {'comment': 'Каст обычной магии школы «%s» (PohSpell.onCast): знак под магом, волна, частицы школы. Сгенерировано tools/gen_school_themes.py.' % S['name'],
            'style': S['style'], 'duration': 36,
            'elements': [dict(type='sigil', id='school_' + s, delay=0, at='caster+0,0.04,0', follow=True),
                         dict(type='wave', shape='ring', delay=0, duration=14, at='caster', radius=3.0, color='@primary'),
                         dict(type='flash', delay=0, duration=8, at='caster+0,0.3,0', size=1.6, color='@secondary', brightness=0.7),
                         dict(type='sprites', delay=2, duration=30, at='caster+0,0.2,0', follow=True, texture='@shards', count=16, rate=1.2, area=1.6,
                              speed=0.02, gravity=-0.003 if s not in ('ice', 'holy', 'blood') else 0.002, spin=80, size=[0.22, 0.1], life=22, color='@secondary')]}


def style_def(s):
    S = SCHOOLS[s]
    return {'comment': 'Стиль школы Iron\'s «%s» (T06): %s. Сгенерировано tools/gen_school_themes.py.' % (S['name'], S['idea']),
            'palette': S['palette'],
            'textures': {'sparks': 'spark_soft', 'runes': 'school_%s_band' % s, 'shards': 'mote_' + S['mote'], 'sigil': s + '_seal'},
            'blend': 'additive', 'motion': S['motion']}


def write_json(rel, obj):
    path = os.path.join(ASSETS, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write('\n')
    WRITTEN.append(('json', rel))


# ====================================================================== лист-обзор
def sheet(path):
    cols, cell = 5, 220
    names = list(SCHOOLS)
    rows = []
    for s in names:
        row = Image.new('RGB', (cell * 4 + 10, cell), (14, 11, 22))
        tint = tuple(int(SCHOOLS[s]['seal_color'][i:i + 2], 16) for i in (1, 3, 5))
        for j, (n, sz) in enumerate(((s + '_seal', cell), (s + '_core', cell), (s + '_crown', cell))):
            a = Image.open(os.path.join(OUT_SIGIL, n + '.png')).split()[3].resize((sz - 10, sz - 10), Image.LANCZOS)
            col = Image.new('RGB', a.size, tint)
            row.paste(col, (j * cell + 5, 5), a)
        b = Image.open(os.path.join(OUT_SIGIL, 'school_%s_band.png' % s)).split()[3].resize((cell - 10, 28))
        row.paste(Image.new('RGB', b.size, tint), (3 * cell + 5, cell // 2 - 40), b)
        m = Image.open(os.path.join(OUT_SIGIL, 'mote_%s.png' % SCHOOLS[s]['mote'])).split()[3].resize((80, 80))
        row.paste(Image.new('RGB', m.size, tint), (3 * cell + 70, cell // 2 + 10), m)
        rows.append(row)
    out = Image.new('RGB', (rows[0].width * 2, cell * ((len(rows) + 1) // 2)), (14, 11, 22))
    for i, r in enumerate(rows):
        out.paste(r, ((i % 2) * r.width, (i // 2) * cell))
    out.save(path)
    print('sheet', path)


# ====================================================================== main
def main():
    os.makedirs(OUT_SIGIL, exist_ok=True)
    for s, (fs, fc, fcr, fb) in DRAW.items():
        p = Pen(); fs(p); seal_a = save_sigil(p, s + '_seal')
        p = Pen(zoom=CORE_ZOOM); fc(p); core_a = save_sigil(p, s + '_core')
        p = Pen(); fcr(p); save_sigil(p, s + '_crown')
        p = Pen(1024, 128); fb(p); save_sigil(p, 'school_%s_band' % s, glow=0.4, glow_r=2)
        # знак для HFx / двойного контура T15: печать + ядро (в 0.4 радиуса) на чёрном
        core_small = core_a.resize((int(512 * 0.4), int(512 * 0.4)), Image.LANCZOS)
        comp = np.asarray(seal_a, dtype=np.float32)
        pad = np.zeros((512, 512), np.float32)
        o = (512 - core_small.width) // 2
        pad[o:o + core_small.height, o:o + core_small.width] = np.asarray(core_small, dtype=np.float32)
        save_fx_black(Image.fromarray(np.clip(np.maximum(comp, pad), 0, 255).astype(np.uint8), 'L'), 'sigil_' + s)
        write_json('sigils/%s_seal.json' % s, seal_def(s))
        write_json('sigils/%s_crown.json' % s, crown_def(s))
        write_json('sigils/school_%s.json' % s, ordinary_def(s))
        write_json('fx/school_%s_cast.json' % s, cast_fx(s, False))
        write_json('fx/school_%s_cast_crown.json' % s, cast_fx(s, True))
        write_json('fx/school_%s_cast_divine.json' % s, divine_fx(s))
        write_json('fx/school_%s.json' % s, ordinary_fx(s))
        write_json('fx/styles/%s.json' % SCHOOLS[s]['style'], style_def(s))
        print('school', s)
    motes()
    circle_ward()
    print('written:', len(WRITTEN))
    if '--sheet' in sys.argv:
        sheet(os.path.join(HERE, '..', 'docs', 'media', 'school_themes_sheet.png'))


if __name__ == '__main__':
    main()
