#!/usr/bin/env python3
"""
T22 «Сон бабочки» — новый образ «Небесная бабочка» (владелец 19.11, docs/inbox/2026-11-19_ideas_butterfly_dream_rework.md;
ТЗ docs/specs/tasks/T22_illusion_school.md, последний раздел). Заменяет стекло, трещины и зеркальную плёнку мира сна.
Тон: «детализировано и красиво, как в аниме» — пастельный рассвет, витраж (перламутр, золото, лиловый), свет, лепестки.
Правило владельца: никаких лучей от заклинателя к цели — река бабочек течёт к Небесной бабочке, а не к заклинателю.

Пишет (src/main/resources/assets/pohsmp_core/):
  textures/fx/     illusion_celestial_wing_fore / _hind (витраж крыльев, translucent, 2048×1152 / 1536×1408),
                   illusion_celestial_wing_fore_glow / _hind_glow (светящиеся прожилки и контур, additive),
                   illusion_celestial_halo (мягкое свечение под телом), illusion_dream_bloom (цветок-след, декаль),
                   illusion_dawn_flash (экран: мягкая вспышка рассвета при пробуждении, 1024)
  textures/sigil/  mote_dream_petal, mote_pollen, mote_firefly, mote_sky_butterfly (спрайты), illusion_celestial_mini (силуэт
                   Небесной бабочки для кокона, цветной), illusion_cocoon_ring (кольцо бабочек для halo)
  fx/meshes/       illusion_celestial_butterfly (мир сна, 2400 тиков: взмахи, складывание на пробуждении),
                   illusion_celestial_cast (каст: раскрывается и делает первый взмах), illusion_celestial_flutter (малая в ладонях),
                   illusion_isle_s / _m / _l (парящие островки: трава, цветы, земля, корни)
  fx/              illusion_butterfly_cast, illusion_butterfly_world, illusion_dream_enter/_exit/_wound/_death/_respawn/_ripple,
                   illusion_dream_wake, illusion_butterfly_wake, illusion_butterfly_wake_hit (переписаны),
                   illusion_dream_bloom, illusion_dream_cocoon (новые; имена — как уже зовёт ButterflyDreamSpell)
Новое для кода (docs/inbox/2026-11-19_mgr_T22_celestial_visuals.md): часть mesh `quad` (текстурная плоскость на петле с ключами),
`mesh.move.keys`, у `sprites` — `wrap`, `avoid`, `path`.
Запуск: python3 tools/gen_celestial_butterfly.py  (или вместе со школой: python3 tools/gen_illusion_fx.py)
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_illusion_fx as G  # noqa: E402
from gen_illusion_fx import fx, E, ease, write, mesh, bar, cube, _hex, _fbm, _smooth, WRITTEN  # noqa: E402

A = G.A
LILAC, PINK, BLUE, PEARL, WHITE = G.LILAC, G.PINK, G.BLUE, G.PEARL, G.WHITE
GOLD, AMBER, VIOLET, PEACH = '#FFD27A', '#FFB45E', '#7A5CE0', '#FFC9A8'
DAWN = {'zenith': '#B7B4EC', 'mid': '#F3BFD8', 'horizon': '#FFDDB4', 'fog': '#F7D6DC', 'sun': '#FFF0C8'}

# ------------------------------------------------------------------ шкала (тики), как в gen_illusion_fx
DREAM = 2400                 # сон, тики
WAKE_START = 2366            # старт ролика пробуждения (тик сна; 130.3 с от начала каста)
WAKE_BREAK = 34              # тик ролика: конец сна (132.0 с)
SKY_AT = 'caster+0,42,14'    # где висит Небесная бабочка: 42 бл. над жертвой, 14 вперёд (по взгляду в начале сна)
SKY_OFF = (0.0, 42.0, 14.0)

# ------------------------------------------------------------------ геометрия крыльев (блоки при scale 1)
# Модель: тело вдоль z (голова к +z), крылья в плоскости XZ, y — вверх. Правое крыло — x > 0.
FORE_PX, HIND_PX = (2048, 1152), (1536, 1408)
FORE_W, HIND_W = 36.0, 26.0                                  # ширина квада (u: от петли к кончику)
FORE_D, HIND_D = FORE_W * FORE_PX[1] / FORE_PX[0], HIND_W * HIND_PX[1] / HIND_PX[0]   # глубина (v: от головы к хвосту)
FORE_X0, FORE_Z0 = 0.7, 8.4                                   # угол квада (u=0, v=0) — у петли, со стороны головы
HIND_X0, HIND_Z0 = 0.5, 0.6
FORE_HINGE = (0.0, 0.40)     # точка петли в uv (центр веера жилок)
HIND_HINGE = (0.0, 0.10)

FORE_OUT = [(0.0, 0.22), (0.10, 0.13), (0.26, 0.06), (0.46, 0.02), (0.66, 0.01), (0.83, 0.03), (0.94, 0.09), (0.995, 0.19),
            (0.99, 0.31), (0.94, 0.45), (0.86, 0.60), (0.77, 0.74), (0.67, 0.87), (0.58, 0.97), (0.45, 0.985), (0.31, 0.93),
            (0.18, 0.83), (0.07, 0.71), (0.0, 0.62)]
HIND_OUT = [(0.0, 0.03), (0.16, 0.0), (0.36, 0.02), (0.56, 0.08), (0.74, 0.17), (0.88, 0.29), (0.975, 0.44), (0.985, 0.58),
            (0.93, 0.70), (0.85, 0.78), (0.78, 0.83), (0.765, 0.91), (0.745, 0.975), (0.71, 0.997), (0.675, 0.975), (0.655, 0.91),
            (0.62, 0.875), (0.52, 0.87),
            (0.40, 0.86), (0.27, 0.78), (0.15, 0.62), (0.05, 0.42), (0.0, 0.25)]
HIND_EYE = (0.70, 0.62, 0.105)    # «глазок» на заднем крыле: uv центра, радиус в долях ширины


def _catmull(pts, n=14, closed=True):
    out = []
    P = pts + pts[:3] if closed else [pts[0]] + pts + [pts[-1]]
    m = len(pts) if closed else len(pts) - 1
    for i in range(m):
        p0, p1, p2, p3 = (np.array(P[i + k], float) for k in range(4))
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)))
    return out


def _scallop(poly, W, H, amp, n, start, end):
    """Фестоны по внешнему краю: точки между долями start..end длины контура слегка вдавлены внутрь (к центру крыла)."""
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    out = []
    N = len(poly)
    for i, (x, y) in enumerate(poly):
        f = i / N
        if start <= f <= end:
            k = (f - start) / (end - start)
            d = 0.5 - 0.5 * math.cos(k * n * 2 * math.pi)
            vx, vy = cx - x, cy - y
            L = math.hypot(vx, vy) + 1e-9
            x += vx / L * amp * d * W
            y += vy / L * amp * d * H
        out.append((x, y))
    return out


def _mask(poly, W, H, ss=2):
    im = Image.new('L', (W * ss, H * ss), 0)
    ImageDraw.Draw(im).polygon([(x * ss, y * ss) for x, y in poly], fill=255)
    return np.asarray(im.resize((W, H), Image.LANCZOS)).astype(np.float32) / 255


def _blur(a, r):
    if r <= 0:
        return a
    im = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im).astype(np.float32) / 255


def _blurf(a, r):
    """Размытие float-массива с большим диапазоном (через масштаб 0..1)."""
    m = max(1e-6, float(a.max()))
    return _blur(a / m, r) * m


def _nearest2(sites, W, H, chunk=24):
    """Номер ближайшей точки и расстояние до границы ячейки Вороного (по биссектрисе), пикселями."""
    S = np.asarray(sites, np.float32)
    lab = np.zeros((H, W), np.int32)
    edge = np.zeros((H, W), np.float32)
    xs = np.arange(W, dtype=np.float32)
    for y0 in range(0, H, chunk):
        ys = np.arange(y0, min(H, y0 + chunk), dtype=np.float32)
        X, Y = np.meshgrid(xs, ys)
        d = (X[..., None] - S[:, 0]) ** 2 + (Y[..., None] - S[:, 1]) ** 2
        i1 = np.argmin(d, -1)
        d1 = np.take_along_axis(d, i1[..., None], -1)[..., 0]
        d[np.arange(d.shape[0])[:, None], np.arange(d.shape[1])[None, :], i1] = np.inf
        i2 = np.argmin(d, -1)
        d2 = np.take_along_axis(d, i2[..., None], -1)[..., 0]
        sep = np.linalg.norm(S[i1] - S[i2], axis=-1) + 1e-6
        lab[y0:y0 + len(ys)] = i1
        edge[y0:y0 + len(ys)] = (d2 - d1) / (2 * sep)
    return lab, edge


def _seg_dist(X, Y, pts, width_fn=None):
    """Расстояние (px) от пикселей до ломаной pts; возвращает и параметр вдоль (0..1)."""
    best = np.full(X.shape, np.inf, np.float32)
    along = np.zeros(X.shape, np.float32)
    L = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    tot = L[-1] or 1
    for k, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
        ax, ay, bx, by = a[0], a[1], b[0], b[1]
        vx, vy = bx - ax, by - ay
        l2 = vx * vx + vy * vy + 1e-9
        t = np.clip(((X - ax) * vx + (Y - ay) * vy) / l2, 0, 1)
        d = np.hypot(X - ax - t * vx, Y - ay - t * vy)
        m = d < best
        best = np.where(m, d, best)
        along = np.where(m, (L[k] + t * math.sqrt(l2)) / tot, along)
    return best, along


def _pal(stops, t):
    """Градиент по точкам [(t, '#hex'), …] → RGB 0..255."""
    ts = [s[0] for s in stops]
    cs = np.array([_hex(s[1]) for s in stops], np.float32)
    t = np.clip(t, ts[0], ts[-1])
    return np.stack([np.interp(t, ts, cs[:, k]) for k in range(3)], -1)


def wing_texture(kind):
    """Крыло-витраж. kind: 'fore' | 'hind'. Пишет illusion_celestial_wing_<kind> (стекло: цвет ячеек, свинцовые линии — золото,
    альфа) и _glow (аддитивный свет: прожилки, контур, блики). u — от петли к кончику, v — от головы к хвосту."""
    W, H = FORE_PX if kind == 'fore' else HIND_PX
    Wb = FORE_W if kind == 'fore' else HIND_W
    ppb = W / Wb                                                         # пикселей на блок
    out = FORE_OUT if kind == 'fore' else HIND_OUT
    hu, hv = FORE_HINGE if kind == 'fore' else HIND_HINGE
    seed = 11 if kind == 'fore' else 23
    rng = random.Random(seed)
    poly = _catmull([(x * W, y * H) for x, y in out], 18)
    poly = _scallop(poly, W, H, 0.012, 7 if kind == 'fore' else 6, 0.42 if kind == 'fore' else 0.30, 0.78 if kind == 'fore' else 0.72)
    mask = _mask(poly, W, H)
    hx, hy = hu * W, hv * H
    # --- жилки: веер от петли к краю (как у настоящей бабочки), слегка изогнуты
    ang_poly = [math.atan2(y - hy, x - hx) for x, y in poly]
    a0, a1 = min(ang_poly), max(ang_poly)
    nv = 9 if kind == 'fore' else 8
    veins = []
    for i in range(nv):
        a = a0 + (a1 - a0) * (i + 0.5) / nv + rng.uniform(-0.03, 0.03)
        # где луч пересекает контур
        R = 0
        for r in np.linspace(0, 1.5 * max(W, H), 900):
            x, y = hx + math.cos(a) * r, hy + math.sin(a) * r
            if 0 <= x < W and 0 <= y < H and mask[int(y), int(x)] > 0.5:
                R = r
        bend = rng.uniform(-0.10, 0.10)
        pts = []
        for t in np.linspace(0, 1, 24):
            aa = a + bend * math.sin(t * math.pi) * (1 - t * 0.3)
            pts.append((hx + math.cos(aa) * R * t * 0.995, hy + math.sin(aa) * R * t * 0.995))
        veins.append((a, R, pts))
    # --- ячейки: кольца вокруг петли, в каждом кольце — по секторам между жилками (как розетка витража)
    sites, info = [], []
    ring_step = 2.5 * ppb
    maxR = max(v[1] for v in veins)
    nr = int(maxR / ring_step) + 2
    for ri in range(1, nr):
        r = (ri + 0.15) * ring_step * (1 + 0.012 * ri)
        arc = r * (a1 - a0)
        n = max(nv, int(arc / (2.7 * ppb)))
        for k in range(n):
            a = a0 + (a1 - a0) * (k + 0.5 + rng.uniform(-0.18, 0.18)) / n
            rr = r + rng.uniform(-0.22, 0.22) * ring_step
            x, y = hx + math.cos(a) * rr, hy + math.sin(a) * rr
            if 0 <= x < W and 0 <= y < H and mask[int(y), int(x)] > 0.02:
                sites.append((x, y))
                info.append((ri, a, rr))
    # мелкие ячейки у самой петли
    for k in range(10):
        a = a0 + (a1 - a0) * (k + 0.5) / 10
        sites.append((hx + math.cos(a) * ring_step * 0.55, hy + math.sin(a) * ring_step * 0.55))
        info.append((0, a, ring_step * 0.55))
    lab, edge = _nearest2(sites, W, H)
    Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
    # радиус как доля пути до края по данному направлению
    ang = np.arctan2(Y - hy, X - hx)
    vr = np.array([v[1] for v in veins])
    va = np.array([v[0] for v in veins])
    Rdir = np.interp(ang, va, vr)
    rad = np.hypot(X - hx, Y - hy) / np.maximum(Rdir, 1)
    cell_r = np.array([i[2] for i in info], np.float32)
    cell_a = np.array([i[1] for i in info], np.float32)
    cr = cell_r / np.maximum(np.interp(cell_a, va, vr), 1)
    cr = cr[lab]                                                       # нормированный радиус ячейки (0 у петли … 1 у края)
    ca = ((cell_a - a0) / (a1 - a0))[lab]
    jit = np.array([rng.random() for _ in sites], np.float32)[lab]
    # --- цвет стекла: от петли фиолет → лилово-голубой перламутр → светлый перламутр/розовый → золотая полоса → лиловая кайма
    irid = (ca * 1.7 + jit * 0.35 + cr * 0.6) % 1.0
    mid = G._irid(irid, ['#B193FF', '#FFAEDF', '#93B4FF', '#D9B8FF', '#FFB3D3', '#B193FF'])
    pearl = G._irid(irid + 0.3, ['#FFE9F6', '#FFCDE9', '#D2ECFF', '#EBD9FF', '#FFF3D6', '#FFE9F6'])
    base = _pal([(0, '#5B3FC4'), (0.16, '#7E5CF0'), (0.3, '#A58BFF')], cr)
    gold = _pal([(0, '#FFE6A3'), (0.5, '#FFD27A'), (1, '#FFB869')], jit)
    rim = _pal([(0, '#8D6BF2'), (1, '#6E4FD8')], jit)
    w_mid = _smooth(0.10, 0.24, cr)
    w_pearl = _smooth(0.36, 0.5, cr) * (1 - 0.35 * _smooth(0.5, 0.62, cr))
    w_gold = _smooth(0.74, 0.8, cr) * (1 - _smooth(0.9, 0.93, cr))
    w_rim = _smooth(0.92, 0.95, cr)
    col = base
    col = col * (1 - w_mid[..., None]) + mid * w_mid[..., None]
    col = col * (1 - w_pearl[..., None]) + pearl * w_pearl[..., None]
    col = col * (1 - w_gold[..., None]) + gold * w_gold[..., None]
    col = col * (1 - w_rim[..., None]) + rim * w_rim[..., None]
    alpha_cell = 0.58 + 0.12 * (1 - w_pearl) + 0.2 * w_gold + 0.24 * w_rim
    # глазок на заднем крыле: кольца золото / фиолет / белый центр
    eye_r = np.zeros_like(rad)
    if kind == 'hind':
        ex, ey, er = HIND_EYE[0] * W, HIND_EYE[1] * H, HIND_EYE[2] * W
        de = np.hypot(X - ex, Y - ey) / er
        eye_r = de
        ring_col = _pal([(0, '#FFFFFF'), (0.28, '#FFF2C4'), (0.36, '#7A5CE0'), (0.62, '#5B3FC4'), (0.7, '#FFD27A'), (0.92, '#FFB869'),
                         (1.0, '#C9A8FF')], de)
        we = 1 - _smooth(0.98, 1.04, de)
        col = col * (1 - we[..., None]) + ring_col * we[..., None]
        alpha_cell = alpha_cell * (1 - we) + (0.78 - 0.2 * (de < 0.3)) * we
    # «луны» — белые точки в лиловой кайме
    moons = np.zeros_like(rad)
    for i in range(nv):
        a = a0 + (a1 - a0) * (i + 1.0) / (nv + 0.0) - (a1 - a0) / nv / 2
        R = np.interp(a, va, vr) * 0.935
        mx, my = hx + math.cos(a) * R, hy + math.sin(a) * R
        moons = np.maximum(moons, 1 - _smooth(0.3 * ppb, 0.42 * ppb, np.hypot(X - mx, Y - my)))
    col = col * (1 - moons[..., None]) + np.array(_hex('#FFFDF4'), np.float32) * moons[..., None]
    alpha_cell = np.maximum(alpha_cell, moons * 0.9)
    # стекло светится изнутри: середина ячейки светлее, края насыщеннее
    inner = _smooth(0.0, 0.9 * ppb, edge)
    col = col * (0.8 + 0.2 * inner[..., None]) + (255 - col) * (0.22 * inner[..., None])
    # перелив: косые полосы блика + мелкая неоднородность стекла
    n1 = _fbm(W, H, seed + 3, octaves=5, base=4)
    sheen = 0.5 + 0.5 * np.sin((X * 0.8 + Y) / (3.8 * ppb) + n1 * 5)
    col = col * (0.93 + 0.1 * sheen[..., None]) + 18 * (sheen[..., None] ** 6)
    col = col * (0.95 + 0.08 * n1[..., None])
    # --- свинцовые линии (жилки ячеек), главные жилки, контур
    lead_w = 0.075 * ppb
    lead = 1 - _smooth(lead_w * 0.55, lead_w, edge)
    vein_d = np.full_like(rad, np.inf)
    for a, R, pts in veins:
        d, t = _seg_dist(X, Y, pts)
        vein_d = np.minimum(vein_d, d + t * 0.06 * ppb)                 # к краю жилка тоньше
    vein = 1 - _smooth(0.11 * ppb, 0.17 * ppb, vein_d)
    # контур
    cont = Image.new('L', (W, H), 0)
    ImageDraw.Draw(cont).line([(x, y) for x, y in poly] + [poly[0]], fill=255, width=max(2, int(0.22 * ppb)), joint='curve')
    cont = np.asarray(cont).astype(np.float32) / 255 * (mask > 0.02)
    cont = _blur(cont, 1.2)
    eye_line = np.zeros_like(rad)
    if kind == 'hind':
        for rr in (0.3, 0.64, 1.0):
            eye_line = np.maximum(eye_line, 1 - _smooth(0.018, 0.034, np.abs(eye_r - rr)))
    if kind == 'hind':
        lead *= _smooth(1.02, 1.1, eye_r)                                 # внутри глазка — свои кольца, без сетки ячеек
        vein *= _smooth(1.0, 1.08, eye_r)
    # тонкая вторая линия-фаска внутри каждой ячейки (огранка стекла)
    facet = np.exp(-((edge - 0.3 * ppb) / (0.045 * ppb)) ** 2) * (1 - w_rim * 0.5)
    col = col + (255 - col) * (0.32 * facet)[..., None]
    lines = np.clip(np.maximum.reduce([lead * 0.9, vein, cont, eye_line]), 0, 1)
    lead_col = np.array(_hex('#F2C46A'), np.float32)
    rgb = col * (1 - lines[..., None]) + lead_col * lines[..., None]
    # подсветка свинца: ближе к жилке — светлее (как раскалённое золото)
    rgb = rgb + (np.array(_hex('#FFF6DA'), np.float32) - rgb) * (np.maximum(vein, cont) * 0.55)[..., None]
    alpha = np.clip(alpha_cell * (1 - lines) + 0.96 * lines, 0, 1) * mask
    # к петле крыло плотнее, к кромке — мягкий растворяющийся край (призрачность)
    alpha *= 0.86 + 0.14 * (1 - rad.clip(0, 1))
    G._save_rgba(np.dstack([rgb, alpha * 255]), 'illusion_celestial_wing_%s' % kind)
    # --- свечение (additive): прожилки и контур с ореолом; искры на узлах
    core = np.clip(np.maximum.reduce([lead * 0.55, vein, cont * 1.0, eye_line * 0.9]), 0, 1) * mask
    halo = _blurf(core, 0.35 * ppb) * 1.6 + _blurf(core, 1.1 * ppb) * 1.0
    glow_col = col * 0.55 + np.array(_hex('#FFE7A8'), np.float32) * 0.45
    g_rgb = glow_col * (1 - core[..., None]) + np.array(_hex('#FFFBEA'), np.float32) * core[..., None]
    # искры: на пересечениях главных жилок с кольцами и вдоль контура
    sp = np.zeros_like(rad)
    for a, R, pts in veins:
        for t in (0.62, 0.84, 0.95):
            if rng.random() < 0.35:
                continue
            x, y = pts[int(t * (len(pts) - 1))]
            r0 = (0.32 + 0.25 * rng.random()) * ppb
            d = np.hypot(X - x, Y - y)
            sp = np.maximum(sp, np.exp(-(d / r0) ** 2) + 0.6 * np.exp(-(np.abs(X - x) / (r0 * 2.4)) ** 2 - (np.abs(Y - y) / (r0 * 0.12)) ** 2)
                            + 0.6 * np.exp(-(np.abs(Y - y) / (r0 * 2.4)) ** 2 - (np.abs(X - x) / (r0 * 0.12)) ** 2))
    g_a = np.clip(core * 0.95 + halo * 0.45 + sp * 0.9 + moons * 0.5, 0, 1) * np.clip(mask * 1.5 + _blur(mask, 0.9 * ppb), 0, 1)
    g_a *= 0.25 + 0.75 * _smooth(0.05, 0.3, rad)                       # у петли жилки сходятся — не пересвечивать
    g_rgb = g_rgb * (1 - sp[..., None].clip(0, 1)) + 255 * sp[..., None].clip(0, 1)
    G._save_rgba(np.dstack([g_rgb, g_a * 255]), 'illusion_celestial_wing_%s_glow' % kind)
    return poly




# ================================================================== спрайты и малые текстуры
SS = 4


def _canvas(n):
    return Image.new('L', (n * SS, n * SS), 0)


def _down(im, n):
    return np.asarray(im.resize((n, n), Image.LANCZOS)).astype(np.float32) / 255


def _save_white(a, name, sub='sigil'):
    """Белый спрайт с альфой (красится цветом элемента)."""
    a = np.clip(a, 0, 1)
    G._save_rgba(np.dstack([np.full(a.shape, 255.0)] * 3 + [a * 255]), name, sub)


def _petal_poly(cx, cy, L, W, ang, notch=0.18, n=40):
    pts = []
    for i in range(n + 1):
        t = i / n                                   # 0..1 по одной стороне от основания к кончику и обратно
        a = math.pi * t
        r = math.sin(a) ** 0.8
        x = (1 - math.cos(a)) / 2 * L
        y = r * W / 2 * (1 - 0.35 * (x / L) ** 3)
        pts.append((x, y))
    side = [(x, -y) for x, y in reversed(pts)]
    poly = pts + side
    # выемка на кончике (лепесток сакуры)
    poly = [(x - notch * L * max(0, 1 - abs(y) / (W * 0.18)) * (x > L * 0.9), y) for x, y in poly]
    c, s = math.cos(ang), math.sin(ang)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in poly]


def mote_petal():
    n = 128
    im = _canvas(n)
    d = ImageDraw.Draw(im)
    S = n * SS
    d.polygon(_petal_poly(S * 0.12, S * 0.5, S * 0.78, S * 0.38, 0.0, notch=0.12), fill=200)
    a = _down(im, n)
    y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    vein = np.exp(-((y - 0.5) / 0.012) ** 2) * (x > 0.16) * (x < 0.8) * 0.25
    tip = _smooth(0.4, 0.9, x) * 0.2                                    # к кончику светлее
    edge = np.clip(a - _blur(a, 2.5), 0, 1) * 1.4
    _save_white(np.clip(a * (0.72 + tip) + vein * a + edge, 0, 1), 'mote_dream_petal')


def mote_pollen():
    n = 64
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    r = np.hypot(x - n / 2 + 0.5, y - n / 2 + 0.5) / (n / 2)
    _save_white(np.exp(-(r / 0.16) ** 2) + 0.45 * np.exp(-(r / 0.45) ** 2), 'mote_pollen')


def mote_firefly():
    n = 96
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    dx, dy = (x - n / 2 + 0.5) / (n / 2), (y - n / 2 + 0.5) / (n / 2)
    r = np.hypot(dx, dy)
    rays = np.exp(-(np.abs(dy) / 0.025) ** 2 - (np.abs(dx) / 0.75) ** 2) + np.exp(-(np.abs(dx) / 0.025) ** 2 - (np.abs(dy) / 0.55) ** 2)
    _save_white(np.clip(np.exp(-(r / 0.1) ** 2) * 1.2 + 0.5 * np.exp(-(r / 0.32) ** 2) + 0.18 * np.exp(-(r / 0.75) ** 2) + 0.5 * rays, 0, 1),
                'mote_firefly')


def _bfly_wings(cx, cy, s, open_=1.0):
    """Контуры правой пары крыльев (вид сверху) для спрайтов: [(верхнее), (нижнее)] в пикселях, левое — зеркально."""
    def W(pts, hinge):
        return [(cx + (hinge[0] + x * open_) * s, cy + y * s) for x, y in pts]
    up = _catmull([(0.02, -0.08), (0.25, -0.42), (0.6, -0.62), (0.92, -0.6), (0.98, -0.42), (0.8, -0.18), (0.5, -0.02), (0.1, 0.02)], 10)
    lo = _catmull([(0.04, 0.02), (0.4, 0.04), (0.72, 0.2), (0.78, 0.45), (0.6, 0.68), (0.36, 0.74), (0.18, 0.55), (0.05, 0.25)], 10)
    return W(up, (0, 0)), W(lo, (0, 0))


def mote_sky_butterfly():
    """Светящаяся бабочка реки (вид сверху, крылья раскрыты): заливка с прожилками, белая, красится цветом элемента."""
    n = 128
    S = n * SS
    im = _canvas(n)
    d = ImageDraw.Draw(im)
    for side in (1, -1):
        up, lo = _bfly_wings(S / 2, S / 2, S * 0.46)
        for poly, f in ((lo, 170), (up, 200)):
            d.polygon([(S / 2 + side * (x - S / 2), y) for x, y in poly], fill=f)
    a = _down(im, n)
    vein = _canvas(n)
    dv = ImageDraw.Draw(vein)
    for side in (1, -1):
        for ang in (-62, -40, -18, 8, 34, 58):
            r = math.radians(ang)
            dv.line([(S / 2, S / 2), (S / 2 + side * math.cos(r) * S * 0.42, S / 2 + math.sin(r) * S * 0.42)], fill=255, width=SS * 2)
    v = _down(vein, n) * (a > 0.05)
    body = _canvas(n)
    db = ImageDraw.Draw(body)
    db.ellipse([S * 0.475, S * 0.3, S * 0.525, S * 0.72], fill=255)
    for side in (1, -1):
        db.line([(S / 2, S * 0.32), (S / 2 + side * S * 0.12, S * 0.12)], fill=255, width=SS * 2)
        db.ellipse([S / 2 + side * S * 0.12 - SS * 3, S * 0.12 - SS * 3, S / 2 + side * S * 0.12 + SS * 3, S * 0.12 + SS * 3], fill=255)
    b = _down(body, n)
    edge = np.clip(a - _blur(a, 2.0), 0, 1) * 1.6
    _save_white(np.clip(a * 0.62 + v * 0.35 + edge + b, 0, 1), 'mote_sky_butterfly')


def celestial_mini(fore_poly, hind_poly):
    """Маленький силуэт Небесной бабочки (вид сверху, цветной) для кокона над спящей жертвой: сводит настоящие текстуры крыльев."""
    T = os.path.join(A, 'textures', 'fx')
    n = 512
    scale = n / 82.0                                  # блоков модели → пикселей (размах ~74 + поля)
    cx, cy = n / 2, n * 0.47
    out = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    glow = Image.new('RGBA', (n, n), (0, 0, 0, 0))
    for kind, X0, Z0, Wb, Db in (('hind', HIND_X0, HIND_Z0, HIND_W, HIND_D), ('fore', FORE_X0, FORE_Z0, FORE_W, FORE_D)):
        g = Image.open(os.path.join(T, 'illusion_celestial_wing_%s.png' % kind)).convert('RGBA')
        gl = Image.open(os.path.join(T, 'illusion_celestial_wing_%s_glow.png' % kind)).convert('RGBA')
        w, h = int(Wb * scale), int(Db * scale)
        for img, dst in ((g, out), (gl, glow)):
            r = img.resize((w, h), Image.LANCZOS)
            dst.alpha_composite(r, (int(cx + X0 * scale), int(cy - Z0 * scale)))
            dst.alpha_composite(r.transpose(Image.FLIP_LEFT_RIGHT), (int(cx - X0 * scale - w), int(cy - Z0 * scale)))
    a = np.asarray(out).astype(np.float32)
    gg = np.asarray(glow).astype(np.float32)
    rgb = a[..., :3] + gg[..., :3] * (gg[..., 3:] / 255) * 0.9
    al = np.clip(a[..., 3] / 255 * 1.15 + gg[..., 3] / 255 * 0.6, 0, 1)
    # тело и усики
    body = Image.new('L', (n, n), 0)
    d = ImageDraw.Draw(body)
    d.ellipse([cx - 1.4 * scale, cy - 9.5 * scale, cx + 1.4 * scale, cy + 1.5 * scale], fill=255)
    d.ellipse([cx - 1.0 * scale, cy - 1 * scale, cx + 1.0 * scale, cy + 16 * scale], fill=230)
    for side in (1, -1):
        pts = [(cx + side * (0.5 + 5.5 * t ** 1.6) * scale, cy - (9 + 13 * t) * scale) for t in np.linspace(0, 1, 12)]
        d.line(pts, fill=255, width=max(2, int(0.35 * scale)))
        x, y = pts[-1]
        d.ellipse([x - 0.9 * scale, y - 0.9 * scale, x + 0.9 * scale, y + 0.9 * scale], fill=255)
    b = np.asarray(body).astype(np.float32) / 255
    bc = np.array(_hex('#FFF4DA'), np.float32)
    rgb = rgb * (1 - b[..., None]) + bc * b[..., None]
    al = np.maximum(al, b)
    halo = _blur(al, 10) * 0.5
    rgb = rgb * (al[..., None] / np.maximum(al + halo, 1e-4)[..., None]) + np.array(_hex('#FFE2F0'), np.float32) * (halo / np.maximum(al + halo, 1e-4))[..., None]
    G._save_rgba(np.dstack([np.clip(rgb, 0, 255), np.clip(al + halo, 0, 1) * 255]), 'illusion_celestial_mini', 'sigil')


def cocoon_ring():
    """Кольцо бабочек для halo кокона (512, цветное): 9 бабочек по кругу, тонкое светлое кольцо, искры."""
    n = 512
    S = n * 2
    col_im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(col_im)
    R = S * 0.39
    d.ellipse([S / 2 - R, S / 2 - R, S / 2 + R, S / 2 + R], outline=(255, 236, 214, 150), width=6)
    cols = [(255, 214, 140), (255, 190, 230), (205, 178, 255)]
    for k in range(9):
        a = k / 9 * 2 * math.pi
        bx, by = S / 2 + math.cos(a) * R, S / 2 + math.sin(a) * R
        ang = a + math.pi / 2
        s = S * 0.075
        c = cols[k % 3]
        for side in (1, -1):
            up, lo = _bfly_wings(0, 0, s, 0.85 + 0.15 * (k % 2))
            for poly, al in ((lo, 190), (up, 225)):
                pts = []
                for x, y in poly:
                    x *= side
                    pts.append((bx + x * math.cos(ang) - y * math.sin(ang), by + x * math.sin(ang) + y * math.cos(ang)))
                d.polygon(pts, fill=c + (al,))
        d.ellipse([bx - 3, by - 3, bx + 3, by + 3], fill=(255, 255, 255, 255))
    im = col_im.resize((n, n), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    halo = _blur(a[..., 3] / 255, 6) * 0.55
    al = np.clip(a[..., 3] / 255 + halo, 0, 1)
    rgb = np.where(a[..., 3:] > 8, a[..., :3], np.array([255, 226, 240], np.float32))
    G._save_rgba(np.dstack([rgb, al * 255]), 'illusion_cocoon_ring', 'sigil')


def celestial_halo():
    n = 512
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    r = np.hypot(x - n / 2 + 0.5, (y - n / 2 + 0.5) * 0.8) / (n / 2)
    a = np.exp(-(r / 0.35) ** 2) * 0.8 + np.exp(-(r / 0.7) ** 2) * 0.3
    a *= 1 - _smooth(0.6, 0.97, np.maximum(np.abs(x - n / 2) / (n / 2), np.abs(y - n / 2) / (n / 2)))
    rgb = _pal([(0, '#FFF6E0'), (0.35, '#FFD9A0'), (0.7, '#FFB9DC'), (1, '#C9A8FF')], r)
    G._save_rgba(np.dstack([rgb, np.clip(a, 0, 1) * 255]), 'illusion_celestial_halo')


def dream_bloom():
    """Цветок-след (декаль 256, цветная, светится): 3–4 маленьких пятилепестковых цветка с листиками и пыльцой."""
    n = 256
    S = n * SS
    rng = random.Random(5)
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k in range(5):                                  # листики
        a = rng.uniform(0, 2 * math.pi)
        d.polygon(_petal_poly(S / 2, S / 2, S * 0.36, S * 0.12, a, notch=0), fill=(150, 214, 140, 200))
    flowers = [(0.5, 0.5, 0.22, (255, 196, 228)), (0.3, 0.36, 0.13, (255, 246, 252)), (0.7, 0.33, 0.12, (214, 196, 255)),
               (0.66, 0.7, 0.14, (255, 230, 150)), (0.32, 0.68, 0.1, (255, 210, 236))]
    for fx_, fy, fr, c in flowers:
        cx, cy, R = fx_ * S, fy * S, fr * S
        a0 = rng.uniform(0, 2 * math.pi)
        for k in range(5):
            a = a0 + k * 2 * math.pi / 5
            d.polygon(_petal_poly(cx, cy, R, R * 0.8, a, notch=0.12), fill=c + (235,))
        d.ellipse([cx - R * 0.22, cy - R * 0.22, cx + R * 0.22, cy + R * 0.22], fill=(255, 214, 120, 255))
        d.ellipse([cx - R * 0.1, cy - R * 0.1, cx + R * 0.1, cy + R * 0.1], fill=(255, 250, 230, 255))
    im = im.resize((n, n), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    halo = _blur(a[..., 3] / 255, 7) * 0.5
    al = np.clip(a[..., 3] / 255 + halo, 0, 1)
    rgb = np.where(a[..., 3:] > 8, a[..., :3], np.array([255, 220, 238], np.float32))
    G._save_rgba(np.dstack([rgb, al * 255]), 'illusion_dream_bloom')


def dawn_flash():
    """Экран пробуждения (1024): мягкая вспышка рассвета — тёплый белый центр, персик, розовый к краям, лучи. Код кладёт её
    на весь экран (растянуть по большей стороне) поверх мира, аддитивно."""
    n = 1024
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    dx, dy = (x - n / 2) / (n / 2), (y - n * 0.46) / (n / 2)
    r = np.hypot(dx, dy)
    th = np.arctan2(dy, dx)
    rays = 0.5 + 0.5 * np.cos(th * 9 + 0.6 * np.sin(th * 4)) * (0.5 + 0.5 * np.cos(th * 5 + 1.3))
    a = np.exp(-(r / 0.38) ** 2) + 0.55 * np.exp(-(r / 0.95) ** 2) + 0.22 * rays * np.exp(-(r / 0.8) ** 2)
    rgb = _pal([(0, '#FFFDF4'), (0.3, '#FFEBC8'), (0.6, '#FFD1C0'), (0.9, '#FFC0DA'), (1.4, '#D9C2FF')], r)
    G._save_rgba(np.dstack([rgb, np.clip(a, 0, 1) * 255]), 'illusion_dawn_flash')


def textures():
    fp = wing_texture('fore')
    hp = wing_texture('hind')
    mote_petal()
    mote_pollen()
    mote_firefly()
    mote_sky_butterfly()
    celestial_mini(fp, hp)
    cocoon_ring()
    celestial_halo()
    dream_bloom()
    dawn_flash()


# ================================================================== модели
REST, FOLD = 10.0, 88.0      # покой крыла (°, вверх от горизонтали) и сложенные крылья (почти вертикально, сомкнуты над спиной)


def flap(t0, amp=1.0, lag=0, up=60.0, down=-26.0, tu=38, td=14, tr=40):
    """Один взмах (ключи петли): покой → медленный подъём (tu) → быстрый удар вниз (td) → возврат в покой (tr).
    Удар вниз (самая нижняя точка) — тик t0 + lag + tu + td: в него рождается волна света."""
    t = t0 + lag
    return [[t, REST, 'easeInOutSine'], [t + tu, REST + (up - REST) * amp, 'easeInOutSine'],
            [t + tu + td, REST + (down - REST) * amp, 'easeInCubic'], [t + tu + td + tr, REST, 'easeOutSine']]


def flutter(t0, t1, period=6, amp=1.0, lag=0):
    """Частые взмахи малой бабочки (в ладонях, взлёт)."""
    k = []
    t = t0
    while t < t1:
        k += [[t + lag, REST, 'easeInOutSine'], [t + lag + period / 2, REST + 58 * amp, 'easeInOutSine'],
              [t + lag + period, REST - 18 * amp, 'easeInOutSine']]
        t += period
    return k


def _body_boxes():
    """Тело Небесной бабочки (блоки модели): грудь, голова, глаза, брюшко сегментами, усики с булавами, светящийся «шов» по спине."""
    solid, glow = [], []
    for k, (z, rx, ry) in enumerate([(8.0, 1.2, 1.1), (6.5, 1.8, 1.5), (4.6, 2.05, 1.7), (2.6, 1.85, 1.55), (1.0, 1.4, 1.25)]):
        solid.append(cube((0, 0.1, z), rx, 0, hy=ry, hz=0.95))
    solid.append(cube((0, 0.35, 9.6), 1.25, 1, hy=1.15, hz=1.1))                # голова
    for side in (1, -1):
        glow.append(cube((side * 1.1, 0.6, 10.2), 0.55, 3))                       # глаза
    z = 0.0
    for k in range(10):                                                           # брюшко
        r = 1.5 * (1 - k / 11) ** 0.8 + 0.22
        L = 1.75 - k * 0.05
        solid.append(cube((0, 0.0 - k * 0.05, z - L / 2), r, 0 if k % 2 == 0 else 1, hy=r * 0.9, hz=L / 2 - 0.08))
        glow.append(cube((0, 0.0 - k * 0.05, z - 0.04), r + 0.08, 4, hy=r * 0.9 + 0.08, hz=0.06))   # золотые кольца между сегментами
        z -= L
    glow.append(bar((0, 1.25, 8.0), (0, 0.95, 1.0), 0.16, tone=3))                # шов по спине
    glow.append(bar((0, 0.95, 1.0), (0, 0.35, -14.0), 0.12, tone=3))
    for side in (1, -1):                                                          # усики: дуга вперёд и в стороны, булава
        pts = [(side * (0.6 + 6.5 * t ** 1.4), 1.0 + 3.5 * math.sin(t * 1.4), 10.6 + 15.0 * t) for t in np.linspace(0, 1, 13)]
        for a, b in zip(pts[:-1], pts[1:]):
            glow.append(bar(a, b, 0.26, tone=4))
        glow.append(cube(pts[-1], 0.65, 3, hy=0.55, hz=0.95))
    return solid, glow


def _wing_parts(fore_keys, hind_keys, pulse=(0.12, 37)):
    parts = []
    for kind, X0, Z0, Wd, D, keys in (('hind', HIND_X0, HIND_Z0, HIND_W, HIND_D, hind_keys), ('fore', FORE_X0, FORE_Z0, FORE_W, FORE_D, fore_keys)):
        for side in (1, -1):
            c = [[side * X0, 0.0, Z0], [side * (X0 + Wd), 0.0, Z0], [side * (X0 + Wd), 0.0, Z0 - D], [side * X0, 0.0, Z0 - D]]
            c = [[round(v, 3) for v in p] for p in c]
            hinge = {'origin': [side * 0.4, 0.0, 0.0], 'axis': [0, 0, side], 'keys': keys}
            parts.append({'type': 'quad', 'comment': '%s, %s крыло: стекло' % ('переднее' if kind == 'fore' else 'заднее',
                                                                             'правое' if side > 0 else 'левое'),
                          'texture': 'illusion_celestial_wing_%s' % kind, 'blend': 'translucent', 'opacity': 0.92, 'doubleSided': True,
                          'corners': c, 'hinge': hinge})
            parts.append({'type': 'quad', 'comment': 'свет прожилок (тот же квад, чуть над стеклом)',
                          'texture': 'illusion_celestial_wing_%s_glow' % kind, 'blend': 'additive', 'opacity': 1.0, 'doubleSided': True,
                          'corners': [[p[0], p[1] + 0.03, p[2]] for p in c], 'hinge': hinge, 'pulse': list(pulse)})
    return parts


def celestial_mesh(id, comment, fore_keys, hind_keys, collapse=10):
    solid, glow = _body_boxes()
    tones = ['#A58BF5', '#7E62DE', BLUE, '#FFF4D8', GOLD]
    parts = [{'type': 'quad', 'comment': 'мягкое свечение под телом', 'texture': 'illusion_celestial_halo', 'blend': 'additive', 'opacity': 0.3,
              'doubleSided': True, 'corners': [[-15, -0.6, 17], [15, -0.6, 17], [15, -0.6, -21], [-15, -0.6, -21]]}]
    parts += _wing_parts(fore_keys, hind_keys)
    parts += [{'type': 'boxes', 'tones': tones, 'glowTones': [3, 4], 'blend': 'translucent', 'opacity': 0.85, 'shade': True,
               'boxes': solid, 'appear': {'delay': 0, 'duration': 6, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 1.0},
               'bounds': [-1.6, 1.6]},
              {'type': 'boxes', 'tones': tones, 'glowTones': [3, 4], 'blend': 'additive', 'opacity': 1.0, 'shade': False, 'boxes': glow,
               'appear': {'delay': 0, 'duration': 6, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 1.0}, 'bounds': [-1.6, 4.0]}]
    return mesh(id, comment, 'illusion', 6, collapse, parts, extra={'span': round(2 * (FORE_X0 + FORE_W), 2),
                                                                  'wingRest': REST, 'wingFold': FOLD})


def flap_schedule(start, end, seed):
    """Тики начала взмахов: раз в 8–10 с (160–200 тиков), с небольшим разбросом; первый — на start."""
    rng = random.Random(seed)
    t, out = start, []
    while t + 100 < end:
        out.append(t)
        t += rng.randint(160, 200)
    return out


WORLD_FLAPS = flap_schedule(30, WAKE_START - 10, 7)
FLAP_HIT = 38 + 14            # тик удара крыла вниз от начала взмаха (flap: tu + td)
FLAP_COLORS = [('#FFD98A', 'золото'), ('#C9A8FF', 'лиловый'), ('#FFC6E6', 'перламутр-розовый')]


def meshes():
    # мир сна: взмахи по расписанию, на пробуждении (тик сна 2366) крылья складываются вверх и смыкаются за 22 тика
    fk, hk = [[0, REST, 'linear']], [[0, REST, 'linear']]
    for t0 in WORLD_FLAPS:
        fk += flap(t0)
        hk += flap(t0, amp=0.85, lag=3)
    fk += [[WAKE_START, REST, 'easeInOutSine'], [WAKE_START + 22, FOLD, 'easeInOutSine']]
    hk += [[WAKE_START + 2, REST, 'easeInOutSine'], [WAKE_START + 24, FOLD - 4, 'easeInOutSine']]
    celestial_mesh('illusion_celestial_butterfly', 'Небесная бабочка «Сна бабочки» (T22, мир сна у жертвы): размах ≈75 бл. при scale 1, '
                                                   'крылья — витраж (4 квада на петлях вдоль тела, часть quad), тело и усики — boxes. '
                                                   'Ключи петель — на всю шкалу сна (2400 тиков): взмах раз в 8–10 с, удар вниз на +52 тике '
                                                   'взмаха; с тика 2366 крылья складываются (88°), на 2400 код делает Fx.stop — модель '
                                                   'сжимается за 10 тиков, её место занимают светлячки (illusion_dream_wake).', fk, hk)
    # каст: взлетела малой, на 120 тике каста (элемент с 0) раскрывается из сложенной и делает два взмаха (удары вниз 180 и 234 тик каста)
    ck = [[0, FOLD, 'linear'], [34, REST, 'easeOutCubic']] + flap(34, up=64, tu=16, td=10, tr=28)[1:] + flap(88, up=60, tu=16, td=10, tr=30)[1:]
    chk = [[0, FOLD - 4, 'linear'], [37, REST, 'easeOutCubic']] + flap(34, 0.85, 3, up=64, tu=16, td=10, tr=28)[1:] + \
        flap(88, 0.85, 3, up=60, tu=16, td=10, tr=30)[1:]
    celestial_mesh('illusion_celestial_cast', 'Небесная бабочка в ролике каста: элемент стартует на 120 тике каста (6.0 с) из сложенных крыльев, '
                                              'раскрывается к 154, первый удар вниз — на 60 тике элемента (180 каста = 9.0 с, вспышка), '
                                              'второй — на 114 (234 каста, «шаг в сон»).', ck, chk, collapse=14)
    celestial_mesh('illusion_celestial_flutter', 'Малая бабочка в ладонях и на взлёте (каст 1.2–6 с): та же модель (scale 0.012–0.06), '
                                                 'частые взмахи (период 6 тиков).', flutter(0, 160, 6), flutter(0, 160, 6, 0.85, 1), collapse=6)
    isles()


ISLE_TONES = ['#9BDB84', '#8E6547', '#7C7389', '#6B4A36', '#7CCB72', '#FFB3D9', '#FFF6FB', '#FFE38A', '#CDB2FF', '#FFF4D0', '#FFC4DF']
ISLE_GLOW = [5, 6, 7, 8, 9]


def isle(R, seed, tree=False):
    """Парящий островок: верх — трава (тонкий слой) и цветы, под ним земля, ниже — камень конусом вниз, корни и лозы свисают.
    Блоки 1×1 (как мир); центр верха — (0, 0, 0)."""
    rng = random.Random(seed)
    solid, glow = [], []
    cells = []
    n = int(R) + 2
    for i in range(-n, n):
        for j in range(-n, n):
            cx, cz = i + 0.5, j + 0.5
            d = math.hypot(cx, cz) + rng.uniform(-0.45, 0.45)
            if d < R:
                top = 0 if not (R >= 2.5 and d < R * 0.45 and rng.random() < 0.5) else 1
                depth = 0.8 + (R - d) ** 1.25 * 1.15 + rng.uniform(0, 1.0)
                cells.append((i, j, top, depth, d))
    for i, j, top, depth, d in cells:
        x0, z0 = i, j
        solid.append([x0, top - 0.22, z0, x0 + 1, top, z0 + 1, 0])
        dirt = depth if depth < 3.2 else round(depth * 0.72, 2)              # низ — земля с корнями, камень только в глубине
        solid.append([x0, round(top - dirt, 2), z0, x0 + 1, top - 0.22, z0 + 1, 1])
        if depth > dirt:
            solid.append([x0, round(top - depth, 2), z0, x0 + 1, round(top - dirt, 2), z0 + 1, 2])
    bottoms = sorted(cells, key=lambda c: -c[3])
    # корни: из нижних блоков, извиваются вниз
    for k in range(int(3 + R * 2.2)):
        i, j, top, depth, d = rng.choice(cells)
        x, y, z = i + rng.uniform(0.2, 0.8), top - depth + 0.05, j + rng.uniform(0.2, 0.8)
        L = rng.uniform(1.0, 2.2 + R * 0.5)
        segs = 6
        px, py, pz = x, y, z
        ax, az = rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3)
        for s_ in range(segs):
            nx = px + ax * L / segs + rng.uniform(-0.12, 0.12)
            nz = pz + az * L / segs + rng.uniform(-0.12, 0.12)
            ny = py - L / segs
            solid.append(bar((px, py, pz), (nx, ny, nz), 0.11 * (1 - s_ / segs * 0.6), tone=3))
            px, py, pz = nx, ny, nz
        if rng.random() < 0.55:
            glow.append(cube((px, py - 0.05, pz), 0.07, 9))                         # капля-огонёк на кончике корня
    # лозы по краю
    edge = [c for c in cells if c[4] > R - 1.2]
    for k in range(int(2 + R * 1.5)):
        i, j, top, depth, d = rng.choice(edge)
        ang = math.atan2(j + 0.5, i + 0.5)
        x, z = i + 0.5 + math.cos(ang) * 0.52, j + 0.5 + math.sin(ang) * 0.52
        L = rng.uniform(0.8, 2.0)
        solid.append(bar((x, top - 0.1, z), (x, top - 0.1 - L, z), 0.06, 0.06, tone=4))
        for q in range(int(L / 0.35)):
            solid.append(cube((x + rng.uniform(-0.08, 0.08), top - 0.3 - q * 0.35, z), 0.09, 4, hy=0.05, hz=0.07))
    # цветы и трава сверху
    for i, j, top, depth, d in cells:
        for q in range(2):
            r = rng.random()
            x, z = i + rng.uniform(0.15, 0.85), j + rng.uniform(0.15, 0.85)
            if r < 0.32:
                h = rng.uniform(0.3, 0.6)
                solid.append(bar((x, top, z), (x + rng.uniform(-0.05, 0.05), top + h, z), 0.035, tone=4))
                glow.append(cube((x, top + h + 0.04, z), rng.uniform(0.08, 0.12), rng.choice([5, 5, 6, 7, 8]), hy=0.05))
            elif r < 0.7:
                h = rng.uniform(0.25, 0.5)
                a = rng.uniform(0, 90)
                solid.append([round(x - 0.2, 3), top, round(z - 0.02, 3), round(x + 0.2, 3), round(top + h, 3), round(z + 0.02, 3), 4, [0, round(a, 1), 0]])
                solid.append([round(x - 0.2, 3), top, round(z - 0.02, 3), round(x + 0.2, 3), round(top + h, 3), round(z + 0.02, 3), 4, [0, round(a + 90, 1), 0]])
    if tree:
        top = max(c[2] for c in cells if c[4] < 1.5) if any(c[4] < 1.5 for c in cells) else 0
        base = (0.5, top, 0.5)
        trunk = [base, (0.7, top + 1.4, 0.4), (0.5, top + 2.6, 0.6)]
        for a, b in zip(trunk[:-1], trunk[1:]):
            solid.append(bar(a, b, 0.32, tone=3))
        for k in range(3):
            ang = k * 2.1 + 0.4
            solid.append(bar((0.6, top + 1.9, 0.5), (0.6 + math.cos(ang) * 1.1, top + 2.6, 0.5 + math.sin(ang) * 1.1), 0.16, tone=3))
        for k in range(26):                                                        # крона: сакура из кубиков
            a, e = rng.uniform(0, 2 * math.pi), rng.uniform(-0.3, 0.9)
            rr = rng.uniform(0.4, 1.8)
            c = (0.6 + math.cos(a) * rr, top + 2.9 + e * 0.9, 0.5 + math.sin(a) * rr)
            solid.append(cube(c, rng.uniform(0.3, 0.55), 10, rot=[0, round(rng.uniform(0, 90), 1), 0]))
        for k in range(14):
            a, rr = rng.uniform(0, 2 * math.pi), rng.uniform(0.6, 2.0)
            glow.append(cube((0.6 + math.cos(a) * rr, top + 2.6 + rng.uniform(-0.2, 1.4), 0.5 + math.sin(a) * rr), 0.07, rng.choice([5, 6])))
    ys = [b[1] for b in solid] + [b[4] for b in solid]
    bounds = [round(min(ys) - 0.1, 2), round(max(ys) + 0.1, 2)]
    return solid, glow, bounds


ISLES = {'s': (1.7, 31, False), 'm': (2.6, 47, False), 'l': (3.9, 59, True)}


def isles():
    for k, (R, seed, tree) in ISLES.items():
        solid, glow, bounds = isle(R, seed, tree)
        ap_ = {'delay': 0, 'duration': 4, 'easing': 'easeOutCubic', 'reveal': 'down', 'front': 0.5}
        mesh('illusion_isle_%s' % k, 'Парящий островок мира сна (T22 «Небесная бабочка»), размер %s (r≈%.1f бл.): трава и светящиеся цветы '
                                     'сверху, земля и камень конусом вниз, свисают корни с огоньками и лозы%s. Центр верха — точка привязки; '
                                     'отрывается от земли (move.from вниз), парит (move.keys), опускается на пробуждении.' %
             (k.upper(), R, ', на большом — цветущее дерево' if tree else ''), 'illusion', 4, 12, [
                 {'type': 'boxes', 'tones': ISLE_TONES, 'glowTones': ISLE_GLOW, 'blend': 'translucent', 'opacity': 1.0, 'shade': True,
                  'boxes': solid, 'appear': ap_, 'bounds': bounds},
                 {'type': 'boxes', 'tones': ISLE_TONES, 'glowTones': ISLE_GLOW, 'blend': 'additive', 'opacity': 1.0, 'shade': False,
                  'boxes': glow, 'appear': ap_, 'bounds': bounds}], extra={'radius': R})


# ================================================================== эффекты
def _sky(dx=0.0, dy=0.0, dz=0.0):
    return 'caster+%s,%s,%s' % (G.fmt(SKY_OFF[0] + dx), G.fmt(SKY_OFF[1] + dy), G.fmt(SKY_OFF[2] + dz))


def isle_layout(n, rmin, rmax, hmin, hmax, seed):
    """Раскладка островков вокруг точки: [(тип, x, h, z)] — x вправо, z вперёд (оси взгляда в начале), h — высота верха над землёй."""
    rng = random.Random(seed)
    out = []
    for i in range(n):
        a = (i + rng.uniform(-0.3, 0.3)) / n * 2 * math.pi
        r = rmin + (rmax - rmin) * (rng.random() ** 0.8)
        kind = 'l' if rng.random() < 0.22 else ('m' if rng.random() < 0.5 else 's')
        x, z = r * math.cos(a), r * math.sin(a)
        if math.hypot(x, (z - 8) * 0.8) < 10:                       # не заслонять Небесную бабочку (она впереди-вверху)
            a += math.pi * 0.35
            r = max(r, 12)
        h = hmin + (hmax - hmin) * ((r - rmin) / (rmax - rmin)) * rng.uniform(0.6, 1.0) + rng.uniform(0, 1.5)
        out.append((kind, round(r * math.cos(a), 2), round(h, 2), round(r * math.sin(a), 2), rng))
    return out


def isle_elements(layout, rise0, rise_span, until, sink_at=None, bob=True, comment=''):
    els = []
    for k, (kind, x, h, z, rng) in enumerate(layout):
        d0 = rise0 + int(rng.uniform(0, rise_span))                 # элемент появляется в тик отрыва (до него острова нет)
        dur = int(rng.uniform(70, 120))
        h0 = round(-h - 0.25, 2)                                     # старт: трава чуть под поверхностью — «выламывается» из земли
        keys = [[0, [0, h0, 0], 'linear'], [dur, [0, 0, 0], 'easeOutCubic']]
        t = dur
        amp, per = rng.uniform(0.25, 0.55), rng.randint(70, 110)
        sgn = 1
        end = (sink_at if sink_at is not None else until) - 4 - d0
        while bob and t + per // 2 < end:
            t += per // 2
            keys.append([t, [0, round(sgn * amp, 2), 0], 'easeInOutSine'])
            sgn = -sgn
        if sink_at is not None:
            s0 = sink_at - d0 + int(rng.uniform(0, 8))
            keys += [[s0, [0, 0, 0], 'easeInOutSine'], [s0 + 26, [0, round(-h * 0.97, 2), 0], 'easeInCubic']]
        spin = rng.uniform(12, 30) * rng.choice([-1, 1]) * (until / 2400)
        els.append(E('mesh', d0, 'caster+%s,%s,%s' % (G.fmt(x), G.fmt(h), G.fmt(z)), model='illusion_isle_%s' % kind,
                     scale=round(rng.uniform(0.9, 1.1), 2), until=until,
                     move={'from': [0, h0, 0], 'delay': 0, 'duration': dur, 'easing': 'easeOutCubic', 'keys': keys},
                     hinge={'pivot': [0, 0, 0], 'axis': 'y', 'keys': [[0, 0, 'linear'], [until - d0, round(spin, 1), 'linear']]},
                     comment=(comment if k == 0 else None)))
    for e in els:
        if e.get('comment') is None:
            e.pop('comment', None)
    return els


def frozen_motes(T, heights=(0.5, 1.4, 2.4, 3.6, 5.0, 6.6), area=16, k=1.0):
    """Пыльца, лепестки и капли висят неподвижно (wrap — заполняют куб вокруг жертвы, avoid — расступаются)."""
    els = []
    kinds = [('mote_dream_petal', PINK, [0.2, 0.2], 0.25, 40), ('mote_dream_petal', '#FFF2F8', [0.17, 0.17], 0.2, 22),
             ('mote_pollen', GOLD, [0.14, 0.14], 0.7, 46), ('mote_firefly', '#D8EEFF', [0.12, 0.12], 0.6, 14)]
    for i, h in enumerate(heights):
        for tex, col, size, glow, cnt in kinds:
            c = int(cnt * k)
            els.append(E('sprites', 0, 'caster+0,%s,0' % G.fmt(h), duration=T, follow=True, texture=tex, count=c, rate=c / 8.0, area=area,
                         speed=0.0, gravity=0.0, sway=0.12, spin=6, tumble=0.25 if tex == 'mote_dream_petal' else 0.0, size=size, life=T + 40,
                         color=col, glow=glow, wrap=area, avoid={'radius': 1.8, 'push': 1.1},
                         **({'comment': 'замершие пыльца, лепестки и капли: висят, у жертвы расступаются (wrap, avoid — новое, см. письмо)'}
                            if i == 0 and tex == 'mote_dream_petal' and col == PINK else {})))
    return els


RIVERS = [
    ['caster+-30,1.5,-14', 'caster+-21,2.2,-7', 'caster+-15,3.5,2', 'caster+-12,8,10', 'caster+-7,18,15', 'caster+-3,30,15', _sky(0, -1, -1)],
    ['caster+28,1.6,-20', 'caster+20,2.6,-12', 'caster+14,4.5,-2', 'caster+11,10,7', 'caster+6,20,12', 'caster+2,31,14', _sky(0, -1, -2)],
    ['caster+-4,1.4,-34', 'caster+3,2.4,-24', 'caster+-2,4,-14', 'caster+-6,9,-4', 'caster+-3,19,4', 'caster+-1,30,10', _sky(0, -1, 0)],
]


def river(T, k=1.0, delay=0):
    els = []
    for ri, path in enumerate(RIVERS):
        for ci, (col, tex, size, rate, glow) in enumerate([(GOLD, 'mote_sky_butterfly', [0.6, 0.45], 0.55, 0.3),
                                                          ('#FFC6E6', 'mote_sky_butterfly', [0.55, 0.4], 0.45, 0.3),
                                                          ('#CDB8FF', 'mote_sky_butterfly', [0.55, 0.4], 0.4, 0.3),
                                                          ('#FFF4D8', 'mote_firefly', [0.2, 0.1], 1.0, 0.3)]):
            extra = {'comment': 'река светящихся бабочек к Небесной бабочке (path — новое: частицы текут по кривой Catmull-Rom за life '
                                'тиков, разброс width сужается к концу; без поддержки — всплывают у первой точки)'} if ri == 0 and ci == 0 else {}
            els.append(E('sprites', delay, path[0], duration=T, follow=True, texture=tex, count=int(20000 * k), rate=round(rate * k, 2),
                         spread=1.2, speed=0.0, gravity=-0.003, sway=0.9 if tex != 'mote_firefly' else 0.4, tumble=0.5 if tex != 'mote_firefly' else 0,
                         size=size, life=300, color=col, glow=glow, path=path, width=1.6, **extra))
    return els


def flap_light(t_hit, col, tint=True, ground_r=40):
    """Волна света от удара крыльев вниз: сфера от бабочки, свет по земле, перекраска мира в цвет крыла, сыплется пыльца."""
    els = [E('flash', t_hit - 2, _sky(), duration=16, size=34, rays=10, anamorphic=0, color=col, brightness=0.55),
           E('wave', t_hit, _sky(), duration=44, shape='sphere', radius=78, rim=1.0, color=col, brightness=0.55),
           E('wave', t_hit + 10, 'caster', duration=50, shape='ring', radius=ground_r, followTerrain=True, thickness=6, color=col, brightness=0.6),
           E('sprites', t_hit, _sky(0, -1, 0), duration=6, texture='mote_pollen', count=140, rate=24, area=28, speed=0.02, gravity=0.0012,
             sway=1.2, size=[0.5, 0.3], life=120, color=col, glow=0.6),
           E('sprites', t_hit, _sky(0, -1, 0), duration=6, texture='mote_firefly', count=60, rate=10, area=30, speed=0.015, gravity=0.0009,
             sway=1.5, size=[0.35, 0.2], life=140, color='#FFF6E0', glow=0.4)]
    if tint:
        els.append(E('tint', t_hit, 'caster', duration=110, radius=64, color=col, strength=0.34, **{'in': ease(8, 'easeOutSine'), 'out': ease(80, 'easeInOutSine')}))
    return els


def world_fx():
    T = DREAM
    body_keys = [[0, [0, 0, 0], 'linear']]
    for t0 in WORLD_FLAPS:
        body_keys += [[t0 + 40, [0, -0.6, 0], 'easeInOutSine'], [t0 + FLAP_HIT + 4, [0, 1.8, 0], 'easeOutCubic'], [t0 + 120, [0, 0, 0], 'easeInOutSine']]
    els = [
        E('mesh', 0, SKY_AT, follow=True, model='illusion_celestial_butterfly', scale=1.0, until=T,
          move={'from': [0, 0, 0], 'scaleFrom': 0.92, 'delay': 0, 'duration': 30, 'easing': 'easeOutCubic', 'keys': body_keys},
          comment='Небесная бабочка: 42 бл. над жертвой, 14 вперёд; ключи взмахов — в модели, подскок тела на ударе — move.keys'),
        E('sprites', 0, _sky(0, -1, 0), duration=T, follow=True, texture='mote_firefly', count=20000, rate=0.7, area=30, speed=0.004,
          gravity=0.0006, sway=1.4, size=[0.4, 0.2], life=200, color='#FFF0C8', glow=0.6, comment='с крыльев всегда чуть сыплется свет'),
        E('tint', 0, 'caster', duration=T, radius=64, color='#FFD3E4', strength=0.1, **{'in': ease(40), 'out': ease(20)},
          comment='пастель сна; небо и туман — рассвет (код, см. письмо)'),
        E('sprites', 0, 'caster+0,0.1,0', duration=T, follow=True, texture='mote_pollen', count=20000, rate=0.5, area=12, speed=0.002,
          gravity=-0.0008, sway=0.8, size=[0.12, 0.05], life=160, color=GOLD, glow=0.5, comment='от травы тихо поднимается пыльца'),
    ]
    for i, t0 in enumerate(WORLD_FLAPS):
        els += flap_light(t0 + FLAP_HIT, FLAP_COLORS[i % 3][0])
    els += isle_elements(isle_layout(16, 8, 34, 4.5, 17, 3), 0, 90, T, sink_at=WAKE_START,
                         comment='16 островков вокруг места, где жертва уснула (follow нет — это мир): отрываются от земли за 1–5 с, '
                                 'парят, медленно поворачиваются, с тика 2366 опускаются на землю')
    els += frozen_motes(T)
    els += river(T)
    fx('illusion_butterfly_world', 'Сон бабочки — мир сна «Небесная бабочка», все 2 минуты (2400 тиков), у КАЖДОЙ жертвы (только ей; caster = '
                                   'жертва). Над жертвой на полнеба — Небесная бабочка (витраж: перламутр, золото, лиловый), взмах раз в '
                                   '8–10 с: волна света, мир на 3–5 с в цвете крыла (золото → лиловый → перламутр). Вокруг отрываются и парят '
                                   '16 островков с травой и цветами; пыльца, лепестки и капли висят неподвижно и расступаются вокруг жертвы; '
                                   'река светящихся бабочек течёт к Небесной бабочке. Пастель, рассветное небо (код). На пробуждении '
                                   '(ролик с тика 2366) крылья складываются, острова опускаются; на 2400 код делает Fx.stop.',
       'illusion', T + 20, els)


def cast_fx():
    hands = (0.0, 1.3, 0.42)
    k_small = 0.06
    frm = [round((hands[i] - SKY_OFF[i]) / k_small, 1) for i in range(3)]
    up = [E('sprites', 44 + k * 6, 'caster+0,1.4,0.4', duration=30, texture='mote_sky_butterfly', count=22, rate=0.7, spread=0.2, speed=0.03,
            gravity=-0.009, sway=1.8, tumble=0.4, size=[0.3, 0.22], life=80, color=c, glow=0.6)
          for k, c in enumerate(('#FFC6E6', GOLD, '#CDB8FF'))]
    flap1, flap2 = 120 + 60, 120 + 114
    els = [
        E('sigil', 0, 'caster+0,0.05,0', id='illusion_dream_ground', until=244),
        E('sprites', 0, 'caster+0,0.2,0', duration=40, texture='mote_pollen', count=110, rate=2.7, area=4.0, speed=0.01, gravity=-0.004,
          size=[0.16, 0.05], life=36, color=GOLD, glow=0.5, comment='свет поднимается от печати'),
        E('flash', 10, 'caster+0,1.25,0.35', follow=True, duration=34, size=0.8, color='#FFE2B8', brightness=0.7, comment='свет в ладонях 0.5–2 с'),
        E('mesh', 24, 'caster+0,1.28,0.42', model='illusion_celestial_flutter', scale=0.012, until=46,
          comment='в ладонях — Небесная бабочка размером с ладонь (та же модель, scale 0.012), трепещет'),
        E('flash', 42, 'caster+0,1.4,0.42', duration=10, size=1.3, rays=6, color=WHITE, comment='вспорхнула'),
        E('mesh', 46, SKY_AT, model='illusion_celestial_flutter', scale=k_small, until=122,
          move={'from': frm, 'scaleFrom': 0.2, 'delay': 0, 'duration': 74, 'easing': 'easeInCubic'},
          comment='2–6 с: летит из ладоней в небо (ускоряясь), к 6 с — на месте Небесной бабочки (42 бл. вверх, 14 вперёд)'),
        *up,
        E('trail', 44, 'caster+0,0.6,0', duration=76, follow=True, width=0.12, length=16, fade=1.3, head=1.2, count=3, color=GOLD,
          orbit={'radius': 1.6, 'speed': 7, 'rise': 1.2, 'risePeriod': 50, 'climb': 1.2}, comment='поток света спиралью вверх за ней'),
        E('flash', 86, 'point:touch', duration=10, size=1.0, rays=8, color='#FFE2B8', comment='4.3 с: ладонь отпускает бабочку ввысь (без трещин)'),
        E('sprites', 86, 'point:touch', duration=4, texture='mote_dream_petal', count=18, rate=5, spread=0.25, speed=0.05, gravity=-0.003, sway=1.2,
          tumble=0.8, size=[0.2, 0.16], life=40, color=PINK, glow=0.3),
        E('flash', 116, _sky(), duration=14, size=10, rays=10, anamorphic=12, color='#FFE9C2', brightness=0.9, comment='в небе — звезда'),
        # 6–8 с: вырастает в Небесную, небо светлеет
        E('mesh', 120, SKY_AT, model='illusion_celestial_cast', scale=1.0, until=250,
          move={'from': [0, 0, 0], 'scaleFrom': k_small, 'delay': 0, 'duration': 44, 'easing': 'easeOutCubic'},
          comment='6.0–8.2 с: вырастает из звезды в Небесную бабочку на полнеба и раскрывает крылья; удары вниз — 180 и 234 тик'),
        E('flash', 120, _sky(), duration=40, size=60, rays=14, color='#FFD9EA', brightness=0.45),
        E('tint', 120, 'caster', duration=124, radius=64, color='#FFC9DC', strength=0.16, **{'in': ease(40, 'easeInOutSine'), 'out': ease(16)},
          comment='мир светлеет в пастель рассвета (код в ролике плавно красит небо, см. письмо)'),
        E('sprites', 124, _sky(0, -1, 0), duration=110, texture='mote_firefly', count=200, rate=1.8, area=28, speed=0.004, gravity=0.0008,
          sway=1.4, size=[0.4, 0.2], life=160, color='#FFF0C8', glow=0.6),
        # 9.0 с: первый взмах — волна света, земля отрывается
        *flap_light(flap1, '#FFD98A'),
        E('flash', flap1, 'caster+0,1.4,0', duration=12, size=4.0, rays=12, anamorphic=10, screen=0.3, color='#FFF1D6'),
        E('sprites', flap1, 'caster+0,0.2,0', duration=30, texture='mote_dream_petal', count=240, rate=8, area=16, speed=0.01, gravity=-0.0035,
          sway=1.5, tumble=0.9, spin=60, size=[0.24, 0.2], life=90, color=PINK, glow=0.3, comment='с травы взлетают и замирают лепестки'),
        E('vortex', 164, 'caster+0,0.5,0', duration=60, radius=9, height=7, arms=5, speed=6, pull=-0.2, funnel=0.3, turns=1.5, width=0.1,
          texture='mote_sky_butterfly', particles=120, life=40, size=0.36, color='#FFC6E6', comment='вихрь бабочек на перевороте'),
        E('vortex', 168, 'caster+0,0.5,0', duration=56, radius=6, height=5, arms=3, speed=-5, pull=0.2, funnel=0.4, turns=1.2, width=0.06,
          texture='mote_dream_petal', particles=80, life=30, size=0.24, color='#FFF2F8'),
        E('wave', flap1, 'caster+0,1,0', duration=20, shape='sphere', radius=6, rim=1.4, color='@primary'),
        # 10–12 с: острова парят, река бабочек в небо, волна по зоне, второй взмах — «шаг в сон»
        *river(64, k=1.4, delay=196),
        E('wave', 222, 'caster', duration=34, shape='ring', radius=64, color=PEACH),
        E('wave', 224, 'caster+0,0.5,0', duration=38, shape='sphere', radius=64, rim=1.0, color='#FFE2F0', brightness=0.4),
        *flap_light(flap2, '#FFC6E6', tint=False, ground_r=64),
        E('flash', 236, 'caster+0,1.4,0', duration=12, size=5.0, rays=12, anamorphic=12, screen=0.5, color='#FFEBC8', comment='мягкая вспышка: шаг в сон'),
        E('sprites', 236, 'caster+0,1.4,0', duration=3, texture='mote_dream_petal', count=70, rate=24, spread=0.6, speed=0.18, gravity=-0.001,
          sway=1.2, tumble=1, spin=200, size=[0.28, 0.2], life=40, color=PINK, glow=0.4),
    ]
    # заклинатель и зрители видят, как вокруг заклинателя отрывается земля (8 островков, с первого взмаха)
    els += isle_elements(isle_layout(9, 6, 22, 2.5, 10, 17), flap1 - 4, 20, 250, bob=True,
                         comment='с первым взмахом (9.0 с) земля вокруг отрывается островками; после ролика — сжимаются (collapse)')
    fx('illusion_butterfly_cast', 'Сон бабочки, каст 12 с (240 тиков) + хвост до 260; caster = маг; видят все в ролике. Планы камеры — ТЗ T22, '
                                  '«Небесная бабочка — ролик». 0–2 с: под магом печать, в ладонях рождается светящаяся бабочка; 2–6 с: она '
                                  'взлетает и уходит в небо (поток света спиралью), на 4.3 с ладонь отпускает её (point:touch); 6–8 с: в небе '
                                  'звезда вырастает в Небесную бабочку на полнеба, мир светлеет в рассвет; 9.0 с: первый взмах — волна света, '
                                  'земля вокруг отрывается островками, лепестки взлетают и замирают (переворот 180° камеры — как было); '
                                  '10–12 с: река бабочек течёт в небо, волна по зоне r64, 11.7 с второй взмах и мягкая вспышка — шаг в сон.',
       'illusion', 260, els)


def wake_fx():
    B = WAKE_BREAK
    common = [
        E('sprites', 0, 'caster+0,1.5,0', follow=True, duration=B, texture='mote_pollen', count=140, rate=4, area=10, speed=0.003,
          gravity=-0.0015, size=[0.14, 0.04], life=26, color=GOLD, glow=0.5, comment='0–1.7 с: воздух звенит светом'),
        E('sprites', 26, _sky(0, 0, 0), follow=True, duration=10, texture='mote_firefly', count=450, rate=45, area=34, speed=0.03,
          gravity=0.0016, sway=1.6, size=[0.45, 0.2], life=90, color='#FFE2A0', glow=0.3,
          comment='1.3–1.8 с: сложенная бабочка рассыпается светлячками (на 34 код делает Fx.stop мира — модель сжимается)'),
        E('sprites', 28, _sky(0, 0, 0), follow=True, duration=8, texture='mote_sky_butterfly', count=160, rate=20, area=26, speed=0.05,
          gravity=0.0012, sway=1.8, tumble=0.5, size=[0.6, 0.3], life=80, color='#FFC6E6', glow=0.3),
        E('sprites', 30, _sky(0, 0, 0), follow=True, duration=8, texture='mote_firefly', count=300, rate=38, area=30, speed=0.02,
          gravity=0.0014, sway=1.5, size=[0.4, 0.2], life=90, color='#CDB8FF', glow=0.3),
        E('sprites', B, 'caster+0,3.5,0', follow=True, duration=3, texture='mote_dream_petal', count=320, rate=110, area=14, speed=0.0, gravity=0.012,
          sway=1.6, tumble=1, spin=90, size=[0.22, 0.18], life=40, color=PINK, glow=0.3, comment='замершие лепестки разом падают'),
        E('sprites', B, 'caster+0,1.5,0', follow=True, duration=3, texture='mote_dream_petal', count=200, rate=70, area=12, speed=0.0, gravity=0.014,
          sway=1.4, tumble=1, spin=-80, size=[0.18, 0.15], life=34, color='#FFF2F8', glow=0.3),
        E('flash', B, 'caster+0,1.5,0', follow=True, duration=14, size=3.5, rays=12, anamorphic=10, color='#FFE6C4',
          comment='мягкая вспышка рассвета (экран — illusion_dawn_flash, код)'),
        E('tint', B, 'caster', duration=50, radius=64, color='#FFD9A8', strength=0.2, **{'in': ease(3), 'out': ease(44, 'easeInOutSine')}),
        E('wave', B, 'caster', duration=20, shape='ring', radius=24, color=PEACH, brightness=0.7),
    ]
    fx('illusion_dream_wake', 'Сон бабочки — ролик пробуждения «рассвет» (caster = жертва, follow; также на заклинателе — caster = он). Старт — тик '
                              'сна 2366 (130.3 с от каста, удар в музыке). 0–22: Небесная бабочка складывает крылья (ключи модели мира), '
                              'острова опускаются (move.keys мира), воздух звенит светом; 26–36: бабочка рассыпается светлячками и малыми '
                              'бабочками, они медленно сыплются вниз; 34 (132.0 с, конец сна): замершие лепестки разом падают, мягкая вспышка '
                              'рассвета (экран — код, textures/fx/illusion_dawn_flash), тёплый свет мира гаснет 2 с. Код на 34: Fx.stop мира сна.',
       'illusion', 90, common)
    fx('illusion_butterfly_wake', 'Сон бабочки, пробуждение у заклинателя — видят ВСЕ в r64 (урона нет: «это был просто сон»). Тот же старт, что ролик '
                                  '(тик сна 2366); 26–36: над зоной сыплются светлячки и малые бабочки (рассыпалась Небесная бабочка); '
                                  '34: мягкая тёплая вспышка, кольцо света до r64. Звук на 34 (предложение): AMETHYST_BLOCK_RESONATE + '
                                  'тихий BELL_RESONATE, без стекла.', 'illusion', 90, [
        E('sprites', 0, 'caster+0,2,0', duration=B, texture='mote_pollen', count=200, rate=6, area=24, speed=0.004, gravity=-0.0015,
          size=[0.16, 0.05], life=26, color=GOLD, glow=0.5),
        E('sprites', 24, 'caster+0,18,0', duration=12, texture='mote_firefly', count=700, rate=58, area=56, speed=0.02, gravity=0.0018, sway=1.6,
          size=[0.45, 0.2], life=110, color='#FFE2A0', glow=0.3, comment='светлячки над всей зоной'),
        E('sprites', 26, 'caster+0,16,0', duration=10, texture='mote_sky_butterfly', count=220, rate=22, area=50, speed=0.03, gravity=0.0012,
          sway=1.8, tumble=0.5, size=[0.6, 0.3], life=100, color='#FFC6E6', glow=0.6),
        E('flash', B, 'caster+0,1.5,0', duration=14, size=4, rays=12, anamorphic=12, screen=0.2, color='#FFE6C4'),
        E('wave', B, 'caster', duration=26, shape='ring', radius=64, color=PEACH),
        E('wave', B + 2, 'caster+0,1,0', duration=28, shape='sphere', radius=48, rim=1.2, color='#FFE2F0', brightness=0.45),
    ])
    fx('illusion_butterfly_wake_hit', 'Сон бабочки (без урона): на 34 тике ролика пробуждения бабочки-метки ранений жертвы (target = жертва; '
                                      'видят жертва и заклинатель) вспыхивают и улетают светлячками вверх — «раны были сном». Код в этот тик '
                                      'убирает свои метки. 30 тиков.', 'illusion', 30, [
        E('sprites', 0, 'target+0,1.1,0', duration=3, texture='mote_sky_butterfly', count=12, rate=4, spread=0.9, speed=0.06, gravity=-0.006,
          sway=1.6, tumble=0.4, size=[0.3, 0.1], life=28, color='#FFC6E6', glow=0.6, comment='бабочки-метки улетают вверх'),
        E('sprites', 0, 'target+0,1.1,0', duration=4, texture='mote_firefly', count=30, rate=8, spread=0.8, speed=0.05, gravity=-0.004,
          sway=1.0, size=[0.24, 0.08], life=26, color='#FFF0C8', glow=0.6),
        E('flash', 0, 'target+0,1.2,0', follow=True, duration=8, size=1.6, rays=8, color='#FFE2B8'),
    ])


def small_fx():
    fx('illusion_dream_enter', 'Сон бабочки: вход в сон (12 тиков; caster = жертва, follow; только ей). Лепестки и пыльца закручиваются вокруг '
                               'жертвы, мягкая рассветная засветка, кольцо по земле. Экранная рябь и зеркалирование — как было (код).', 'illusion', 14, [
        E('wave', 0, 'caster+0,1,0', follow=True, duration=10, shape='sphere', radius=3.5, rim=1.0, color='#FFE2F0', brightness=0.5),
        E('wave', 2, 'caster', follow=True, duration=12, shape='ring', radius=10, color=PEACH),
        E('flash', 4, 'caster+0,1.4,0', follow=True, duration=8, size=1.8, screen=0.22, color='#FFEBD2'),
        E('sprites', 0, 'caster+0,1,0', follow=True, duration=6, texture='mote_dream_petal', count=40, rate=8, spread=2.2, speed=-0.05, sway=1.2,
          tumble=1, spin=120, size=[0.22, 0.18], life=14, color=PINK, glow=0.3),
        E('sprites', 0, 'caster+0,1,0', follow=True, duration=6, texture='mote_pollen', count=30, rate=6, spread=1.8, speed=-0.04,
          size=[0.14, 0.06], life=14, color=GOLD, glow=0.5),
    ])
    fx('illusion_dream_exit', 'Сон бабочки: выход без ролика (сон кончился раньше — сопротивление, «Благословение»; caster = жертва): лепестки '
                              'осыпаются, мягкая вспышка; на этом же тике код делает Fx.stop мира (модель бабочки и острова сжимаются).',
       'illusion', 16, [
           E('wave', 0, 'caster+0,1,0', follow=True, duration=10, shape='sphere', radius=4, rim=1.0, color='#FFE2F0', brightness=0.45),
           E('flash', 0, 'caster+0,1.4,0', follow=True, duration=8, size=1.6, screen=0.2, color='#FFE6C4'),
           E('sprites', 0, 'caster+0,2.5,0', follow=True, duration=3, texture='mote_dream_petal', count=80, rate=27, area=6, speed=0.0, gravity=0.012,
             sway=1.4, tumble=1, spin=90, size=[0.2, 0.16], life=26, color=PINK, glow=0.3),
           E('sprites', 0, 'caster+0,1.2,0', follow=True, duration=3, texture='mote_firefly', count=24, rate=8, spread=1.2, speed=0.03,
             gravity=-0.002, size=[0.24, 0.1], life=24, color='#FFF0C8', glow=0.6),
       ])
    fx('illusion_dream_wound', 'Сон бабочки: удар по жертве во сне (caster = жертва; видят жертва и заклинатель): вспышка и всплеск лепестков у '
                               'груди, рождается бабочка-метка (рисует код, атлас illusion_wound_butterfly). 14 тиков.', 'illusion', 14, [
        E('flash', 0, 'caster+0,1.2,0', follow=True, duration=6, size=0.8, rays=6, color=PINK, brightness=0.8),
        E('sprites', 0, 'caster+0,1.2,0', follow=True, duration=2, texture='mote_dream_petal', count=12, rate=6, spread=0.2, speed=0.07, gravity=0.003,
          sway=0.8, tumble=1, spin=200, size=[0.18, 0.14], life=14, color=PINK, glow=0.3),
        E('sprites', 1, 'caster+0,1.2,0', follow=True, duration=2, texture='mote_pollen', count=8, rate=4, spread=0.2, speed=0.05,
          size=[0.12, 0.0], life=10, color=GOLD, glow=0.5),
    ])
    fx('illusion_dream_death', 'Сон бабочки: «смерть» во сне — видит ТОЛЬКО жертва (caster = жертва). Тело рассыпается в бабочки и лепестки '
                               'снизу вверх (ноги 0–6, корпус 4–12, голова 8–14 тик), светлячки, мягкая вспышка; накладка «смерть сна» '
                               '(код, с 4 тика), перенос на 22 тике.', 'illusion', 32, [
        E('aura', 0, 'caster', target='caster', duration=16, thickness=0.08, pulse=[0.5, 3], motes=14, texture='mote_firefly', color='#FFE2F0',
          **{'in': ease(2), 'out': ease(10, 'easeInSine')}),
        E('sprites', 0, 'caster+0,0.2,0', duration=6, texture='mote_sky_butterfly', count=26, rate=4.4, area=0.4, speed=0.05, gravity=-0.006,
          sway=1.8, tumble=0.4, size=[0.32, 0.2], life=30, color='#CDB8FF', glow=0.5, comment='ноги'),
        E('sprites', 4, 'caster+0,1.0,0', duration=6, texture='mote_sky_butterfly', count=28, rate=4.6, spread=0.35, speed=0.06, gravity=-0.006,
          sway=1.8, tumble=0.4, size=[0.34, 0.2], life=30, color='#FFC6E6', glow=0.5, comment='корпус'),
        E('sprites', 8, 'caster+0,1.7,0', duration=6, texture='mote_sky_butterfly', count=22, rate=3.6, spread=0.25, speed=0.07, gravity=-0.007,
          sway=1.8, tumble=0.4, size=[0.32, 0.2], life=30, color=GOLD, glow=0.5, comment='голова'),
        E('sprites', 2, 'caster+0,1,0', duration=12, texture='mote_dream_petal', count=44, rate=3.6, spread=0.5, speed=0.03, gravity=0.002,
          sway=2, tumble=1, spin=90, size=[0.2, 0.16], life=36, color=PINK, glow=0.3),
        E('sprites', 2, 'caster+0,1,0', duration=12, texture='mote_firefly', count=30, rate=2.6, spread=0.45, speed=0.03, gravity=-0.003,
          size=[0.22, 0.08], life=30, color='#FFF0C8', glow=0.6),
        E('flash', 4, 'caster+0,1.1,0', duration=10, size=2.6, rays=8, anamorphic=4, color='#FFEBD2'),
        E('wave', 6, 'caster', duration=14, shape='ring', radius=5, color=PEACH),
    ])
    fx('illusion_dream_respawn', 'Сон бабочки: жертва появляется в новой точке сна (caster = она в новой точке; видит она). Бабочки и лепестки '
                                 'слетаются в силуэт, оболочка проявляется, у ног распускаются цветы. 24 тика (модель видна с 14).', 'illusion', 26, [
        E('sprites', 0, 'caster+0,1,0', duration=6, texture='mote_sky_butterfly', count=40, rate=7, spread=2.4, speed=-0.12, sway=1,
          size=[0.32, 0.18], life=12, color='#FFC6E6', glow=0.6, comment='бабочки слетаются в тело'),
        E('sprites', 0, 'caster+0,1,0', duration=6, texture='mote_dream_petal', count=24, rate=4, spread=2.0, speed=-0.1, spin=120, tumble=1,
          size=[0.2, 0.14], life=12, color=PINK, glow=0.3),
        E('aura', 8, 'caster', target='caster', duration=14, thickness=0.07, pulse=[0.4, 4], motes=10, texture='mote_firefly', color='#FFE2F0',
          **{'in': ease(4), 'out': ease(8, 'easeInSine')}),
        E('decal', 12, 'caster+0,0.05,0', duration=60, texture='illusion_dream_bloom', radius=1.3, grow=8, glow=0.3, color=WHITE, fadeOut=20, lift=0.02),
        E('flash', 12, 'caster+0,1.1,0', duration=8, size=2.0, rays=6, color='#FFEBD2'),
        E('wave', 12, 'caster', duration=12, shape='ring', radius=4, color=PEACH),
    ])
    fx('illusion_dream_ripple', 'Сон бабочки: что видят ОСТАЛЬНЫЕ, когда жертва «умерла во сне» и перенеслась (старая и новая точка): короткая '
                               'рябь воздуха в рост человека, кольцо, пара лепестков. 16 тиков.', 'illusion', 16, [
        E('wave', 0, 'caster+0,1,0', duration=12, shape='sphere', radius=1.4, rim=1.3, color='#FFE2F0', brightness=0.45),
        E('wave', 0, 'caster', duration=14, shape='ring', radius=2.4, color=PEACH),
        E('flash', 0, 'caster+0,1,0', duration=6, size=1.4, color='#FFE6C4', brightness=0.5),
        E('sprites', 0, 'caster+0,1,0', duration=3, texture='mote_dream_petal', count=10, rate=4, spread=0.5, speed=0.03, gravity=0.002,
          sway=0.8, tumble=1, spin=200, size=[0.16, 0.12], life=14, color=PINK, glow=0.3),
    ])
    fx('illusion_dream_bloom', 'Сон бабочки — цветущий след (только жертве): код играет на шагах жертвы по земле (сейчас каждые 1.3 бл., можно ≈0.9 бл.; '
                                    'лучше точка под стопой: 0.16 бл. вбок от центра, ноги по очереди; не чаще раза в 6 тиков; живых следов ≤ 24). '
                                    'Цветы распускаются за 6 тиков и светятся, держатся ≈3 с, на 46–70 тике осыпаются лепестками.',
       'illusion', 80, [
           E('decal', 0, 'caster+0,0.02,0', duration=66, texture='illusion_dream_bloom', radius=0.55, grow=6, glow=0.3, color=WHITE, fadeOut=20,
             lift=0.02, comment='цветы под стопой'),
           E('sprites', 0, 'caster+0,0.1,0', duration=2, texture='mote_pollen', count=4, rate=2, spread=0.15, speed=0.012, gravity=-0.001,
             size=[0.1, 0.03], life=24, color=GOLD, glow=0.5),
           E('sprites', 46, 'caster+0,0.1,0', duration=20, texture='mote_dream_petal', count=7, rate=0.35, area=0.35, speed=0.006, gravity=-0.0012,
             sway=0.7, tumble=1, spin=60, size=[0.14, 0.1], life=34, color=PINK, glow=0.3, comment='осыпаются лепестками (уносит ветерком)'),
           E('sprites', 50, 'caster+0,0.1,0', duration=16, texture='mote_dream_petal', count=4, rate=0.25, area=0.3, speed=0.005, gravity=-0.001,
             sway=0.6, tumble=1, spin=-50, size=[0.12, 0.08], life=30, color='#FFF2F8', glow=0.3),
       ])
    fx('illusion_dream_cocoon', 'Сон бабочки — кокон для ОСТАЛЬНЫХ (видят все, кроме самой жертвы — у неё мир сна; caster = жертва, follow): '
                                'над спящей кружит тонкое кольцо бабочек и висит маленький светящийся силуэт Небесной бабочки — все видят, '
                                'кто выведен из боя. На всё время сна; код останавливает Fx.stop при пробуждении/выходе.', 'illusion', DREAM + 10, [
        E('halo', 0, 'caster', follow=True, duration=DREAM, texture='illusion_cocoon_ring', size=0.95, tilt=0, spin=2.5, flap=[0.06, 70],
          offset=[0, 1.15, 0], color=WHITE, brightness=0.8, **{'in': ease(16)}, comment='кольцо бабочек на уровне пояса'),
        E('halo', 0, 'caster', follow=True, duration=DREAM, texture='illusion_cocoon_ring', size=0.7, tilt=10, spin=-3.5, flap=[0.05, 55],
          offset=[0, 1.95, 0], color='#FFE2F0', brightness=0.6, **{'in': ease(20)}),
        E('sprites', 0, 'caster+0,2.85,0', follow=True, duration=DREAM, texture='illusion_celestial_mini', count=1, rate=1, speed=0.0,
          size=[1.2, 1.2], life=DREAM + 10, color=WHITE, glow=0.2, blend='translucent', comment='маленький силуэт Небесной бабочки над головой'),
        E('sprites', 0, 'caster+0,1.5,0', follow=True, duration=DREAM, texture='mote_sky_butterfly', count=20000, rate=0.12, spread=0.7,
          speed=0.006, gravity=-0.0015, sway=0.9, tumble=0.4, size=[0.18, 0.08], life=60, color='#FFC6E6', glow=0.5),
        E('sprites', 0, 'caster+0,0.3,0', follow=True, duration=DREAM, texture='mote_pollen', count=20000, rate=0.25, area=0.8, speed=0.003,
          gravity=-0.0012, size=[0.08, 0.02], life=50, color=GOLD, glow=0.5),
    ])


def write_all():
    textures()
    meshes()
    world_fx()
    cast_fx()
    wake_fx()
    small_fx()


if __name__ == '__main__':
    write_all()
    print('\n'.join(WRITTEN))
