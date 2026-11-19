#!/usr/bin/env python3
"""
T25 «Кошмары» — бестиарий: модели GeckoLib (.geo.json), текстуры (+ _glowmask), анимации для 9 сущностей-кошмаров.
ТЗ: docs/specs/tasks/T25_nightmare_school.md. Каркас — tools/nightmare_geo.py. Вызывается из tools/gen_nightmare_fx.py
(или сам: python3 tools/gen_nightmare_bestiary.py [--only nm_lurker,...]).

Пишет (src/main/resources/assets/pohsmp_core/):
  geo/entity/nm_<id>.geo.json             модели (лицом к −z как в Blockbench; ноги на y = 0; 16 ед. = 1 блок)
  textures/entity/nightmare/nm_<id>.png   текстуры (отсечка альфы: RenderType.entityCutoutNoCull — по умолчанию у GeoEntityRenderer)
  textures/entity/nightmare/nm_<id>_glowmask.png   светящиеся места (AutoGlowingGeoLayer GeckoLib)
  animations/entity/nm_<id>.animation.json  анимации: animation.nm_<id>.idle / walk / attack / appear / vanish (+ свои)
Мимик: geo/entity/nm_mimic.geo.json (+ _slim) — тело по развёртке скина игрока (64×64), атлас 128×64: слева скин (код копирует
скин игрока), справа — пасть/зубы/улыбка (textures/entity/nightmare/nm_mimic_template.png).

Стиль: чернильно-чёрный #0A0610, багрово-фиолетовый #7A1040, болезненно-бледный #E8E0D8; всё «течёт» чернилами — на текстуре
потёки сверху вниз (в мировых координатах позы покоя), а с пальцев/подбородка/глаз свисают капли-кости `drip*`, которые в каждой
анимации тянутся и срываются (масштаб по y от шарнира наверху).
"""
import math
import os
import random
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nightmare_geo import (Model, Anim, Ctx, fbm, vnoise, ridge, hex2, mix, sstep, _hash, write_json, TAU)  # noqa: E402

A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
WRITTEN = []

INK0, INK1, INK2, SHEEN = hex2('#060308'), hex2('#120A18'), hex2('#1E1228'), hex2('#4A3060')
CRIMSON, BLOOD, DEEPRED = hex2('#7A1040'), hex2('#B01A4A'), hex2('#3A0418')
PALE, PALE2, BRUISE, VEIN = hex2('#E8E0D8'), hex2('#BDB3AE'), hex2('#8C7A8E'), hex2('#4A2448')
SICK = hex2('#B4B49C')


# ================================================================== общие узоры
def _col_hash(c, k, seed):
    z = np.zeros_like(c)
    return _hash(c, z + k, z + 7, seed)


def streaks(P, y0, y1, seed=0, cw=0.85, p=0.42, lmin=2.0, lmax=14.0):
    """Потёки чернил сверху вниз: столбики по двум горизонтальным осям; у каждого — свой верх и длина, капля-утолщение внизу.
    Возвращает (маска 0..1, «блик» по средней линии 0..1)."""
    out = np.zeros(len(P))
    hl = np.zeros(len(P))
    y = P[:, 1]
    for k, (ax, az) in enumerate(((0.8, 0.6), (-0.6, 0.8), (0.98, -0.2))):
        h = P[:, 0] * ax + P[:, 2] * az + (vnoise(P * [0.0, 0.35, 0.0] + [k * 3.1, 0, 0], 1.0, seed + k) - 0.5) * 0.5
        c = np.floor(h / cw)
        fr = h / cw - c
        c = c.astype(np.int64)
        r1, r2, r3, r4 = (_col_hash(c, k * 4 + j, seed) for j in range(4))
        has = r1 < p
        top = y0 + (y1 - y0) * (0.35 + 0.65 * r2)
        L = lmin + (lmax - lmin) * r3 ** 1.5
        u = (top - y) / L
        inside = has & (u >= 0) & (u <= 1.08)
        w = 0.12 + 0.16 * (1 - u) + 0.22 * np.exp(-((u - 1.0) / 0.06) ** 2) + 0.06 * r4
        d = np.abs(fr - 0.5)
        m = inside & (d < w)
        out = np.maximum(out, m * (1 - sstep(w * 0.75, w, d)))
        hl = np.maximum(hl, m * np.exp(-(d / (w * 0.35 + 1e-6)) ** 2) * (u > 0.05))
    return out, hl


def ink_rgb(ctx, seed=0, sheen=1.0):
    """Мокрые чернила: почти чёрный с фиолетовым отливом, вертикальные блестящие струйки, блик на верхних гранях."""
    P = ctx.P
    n = fbm(P, 0.18, seed, 4)
    base = mix(INK0, INK2, n * 0.9)
    flow = ridge(P * [1.0, 0.18, 1.0], 0.7, seed + 9, 2)
    base = base + SHEEN * (sstep(0.86, 0.98, flow) * 0.5 * sheen)[:, None]
    up = np.clip(ctx.N[:, 1], 0, 1)
    base = base + SHEEN * (up * 0.25 * sheen)[:, None]
    gl = sstep(0.93, 1.0, vnoise(P, 1.6, seed + 3)) * 0.35 * sheen
    return base + np.array([0.75, 0.6, 0.85]) * gl[:, None]


def skin_rgb(ctx, seed=0, base=PALE, bruise=0.55, veins=0.8, dirt=0.4):
    """Болезненно-бледная кожа: крупные синяки, тонкие фиолетовые вены, сероватая грязь пятнами, редкие тонкие трещины."""
    P = ctx.P
    n1 = fbm(P, 0.09, seed, 4)
    c = mix(base, PALE2, n1 * 0.7)
    c = mix(c, BRUISE, sstep(0.55, 0.8, fbm(P, 0.05, seed + 5, 3)) * bruise)
    c = mix(c, SICK, sstep(0.5, 0.85, fbm(P, 0.11, seed + 6, 2)) * 0.22)
    v = ridge(P, 0.16, seed + 11, 3)
    c = mix(c, VEIN, sstep(0.95, 0.99, v) * veins)
    c = mix(c, hex2('#6A5E64'), sstep(0.6, 0.85, fbm(P, 0.14, seed + 13, 3)) * dirt * 0.6)
    cr = ridge(P, 0.2, seed + 17, 2)
    c = mix(c, hex2('#2A1420'), sstep(0.985, 0.998, cr) * 0.8)
    return c * (0.96 + 0.04 * vnoise(P, 1.2, seed + 19))[:, None]


def flesh_rgb(ctx, seed=0):
    P = ctx.P
    c = mix(DEEPRED, CRIMSON, fbm(P, 0.4, seed, 3))
    c = mix(c, BLOOD, sstep(0.6, 0.9, fbm(P, 1.1, seed + 2, 2)) * 0.6)
    wet = sstep(0.9, 1.0, vnoise(P, 2.2, seed + 4))
    return c + np.array([0.9, 0.7, 0.75]) * (wet * 0.4)[:, None]


def teeth_rgb(ctx, seed=0):
    P = ctx.P
    c = mix(hex2('#E6DCC4'), hex2('#A8946C'), fbm(P, 0.8, seed, 3) * 0.9)
    # к корню (по нормали «к десне» не знаем — темнее внизу/вверху куба по t)
    root = ctx.cube.info.get('root', 'up')
    tt = ctx.t if root == 'up' else 1 - ctx.t
    if ctx.face in ('up', 'down'):
        tt = np.full(ctx.n, 0.5)
    c = mix(c, hex2('#6A2A2A'), sstep(0.25, 0.0, tt) * 0.7)
    c = mix(c, hex2('#3A2A18'), sstep(0.7, 0.95, vnoise(P, 3.0, seed + 1)) * 0.6)
    return c


def cloth_rgb(ctx, seed=0, a=hex2('#0E0A12'), b=hex2('#2A1E32')):
    P = ctx.P
    h = P[:, 0] * 0.7 + P[:, 2] * 0.7
    folds = 0.5 + 0.5 * np.sin(h * 1.7 + fbm(P * [1, 0.2, 1], 0.4, seed, 2) * 6)
    c = mix(a, b, folds * 0.6 + fbm(P, 0.5, seed + 1, 3) * 0.4)
    return c


def tatter_alpha(ctx, seed=0, depth=0.35, freq=9.0):
    """Рваный нижний край ткани (t → 1 — низ грани), на боковых гранях."""
    if ctx.face in ('up', 'down'):
        return np.ones(ctx.n)
    s = ctx.s
    edge = 1 - depth * (0.5 + 0.5 * np.sin(s * freq * TAU / 3 + seed)) * (0.4 + 0.6 * vnoise(np.stack([s * 9, np.zeros_like(s) + seed, np.zeros_like(s)], -1), 1.0, seed))
    holes = vnoise(ctx.P, 0.9, seed + 3) > 0.83
    return ((ctx.t < edge) & ~holes).astype(float)


def no_glow(n):
    return None


def glow_of(rgb, mask):
    return rgb[None, :] * np.asarray(mask, float)[:, None] if np.ndim(rgb) == 1 else rgb * np.asarray(mask, float)[:, None]


# ================================================================== материалы
def add_common(m, y0, y1, seed=0, skin=PALE):
    """Общие материалы: ink (чернильное тело), skin (бледная кожа с потёками), cloth/rag (рваная ткань), drip (капля),
    pool (лужа чернил: видна только верхняя грань, круг с рваным краем), flesh, teeth, void (чёрная пустота глаз)."""

    def ink(ctx):
        return ink_rgb(ctx, seed), 1.0, None

    def skin_m(ctx):
        c = skin_rgb(ctx, seed, base=skin)
        sm, hl = streaks(ctx.P, y0, y1, seed + 1, p=0.3)
        c = mix(c, ink_rgb(ctx, seed), sm)
        c = c + SHEEN * (hl * 0.6)[:, None]
        return c, 1.0, None

    def cloth(ctx):
        c = cloth_rgb(ctx, seed)
        sm, hl = streaks(ctx.P, y0, y1, seed + 2, p=0.25)
        c = mix(c, INK0, sm * 0.8) + SHEEN * (hl * 0.4)[:, None]
        return c, 1.0, None

    def rag(ctx):
        c, _, _ = cloth(ctx)
        return c, tatter_alpha(ctx, seed + int(ctx.cube.frm[0] * 13 + ctx.cube.frm[2] * 7) % 97), None

    def drip(ctx):
        c = ink_rgb(ctx, seed + 4, 1.4)
        return c, 1.0, None

    def pool(ctx):
        if ctx.face != 'up':
            return np.zeros((ctx.n, 3)), 0.0, None
        P = ctx.P
        cx = ctx.cube.frm + (ctx.cube.to - ctx.cube.frm) / 2
        R = (ctx.cube.to[0] - ctx.cube.frm[0]) / 2
        d = np.hypot(P[:, 0] - cx[0], P[:, 2] - cx[2]) / R
        ang = np.arctan2(P[:, 2] - cx[2], P[:, 0] - cx[0])
        edge = 0.78 + 0.16 * np.sin(ang * 5 + 1) * 0.5 + 0.18 * (vnoise(np.stack([np.cos(ang) * 3, np.sin(ang) * 3, np.zeros_like(ang)], -1), 1.0, seed) - 0.5)
        splat = (vnoise(P * [1, 0, 1], 0.5, seed + 2) > 0.72) & (d < 1.0)
        a = (d < edge) | splat
        c = ink_rgb(ctx, seed + 6, 1.2)
        ring = np.exp(-((d - edge * 0.6) / 0.08) ** 2) * 0.25
        return c + SHEEN * ring[:, None], a.astype(float), None

    def flesh(ctx):
        return flesh_rgb(ctx, seed), 1.0, None

    def teeth(ctx):
        return teeth_rgb(ctx, seed), 1.0, None

    def void(ctx):
        c = np.tile(hex2('#030104'), (ctx.n, 1))
        return c, 1.0, None

    m.materials.update(ink=ink, skin=skin_m, cloth=cloth, rag=rag, drip=drip, pool=pool, flesh=flesh, teeth=teeth, void=void)


def pool_bone(m, r=10.0):
    m.bone('pool', 'root', (0, 0, 0))
    m.box('pool', (-r, 0.02, -r), (r, 0.08, r), 'pool', hide=('north', 'south', 'east', 'west', 'down'))


def drip(m, parent, name, top, length=2.4, w=0.45):
    """Капля-кость: шарнир наверху (top), висит вниз. Анимации тянут её (scale y) и срывают."""
    top = np.asarray(top, float)
    m.bone(name, parent, top)
    m.box(name, top - [w / 2, length, w / 2], top + [w / 2, 0, w / 2], 'drip')
    m.box(name, top - [w * 0.75, length + w * 0.9, w * 0.75], top - [-w * 0.75, length - w * 0.4, -w * 0.75], 'drip')   # капля на конце
    m.drips = getattr(m, 'drips', []) + [name]


LOOP_L = [None]          # длина текущей циклической анимации (периоды подгоняются, чтобы цикл был бесшовным)
Anim.LOOP = LOOP_L


def per(p):
    L = LOOP_L[0]
    return L / max(1, round(L / p)) if L else p


def drip_keys(m, t, period=2.2, amp=0.9):
    """Капли: тянутся 0.3→1+amp и резко срываются (сброс к 0.3), каждая со своей фазой."""
    out = {}
    period = per(period)
    for i, d in enumerate(getattr(m, 'drips', [])):
        ph = ((t / period) + i * 0.37) % 1.0
        s = 0.3 + (amp + 0.7) * ph ** 1.6 if ph < 0.92 else 0.3 + (amp + 0.7) * (1 - (ph - 0.92) / 0.08) * 0.92 ** 1.6
        out[d] = {'scale': [1, s, 1]}
    for i, b in enumerate(n for n in m.bones if n.startswith('wisp')):      # чернильные струйки колышутся
        out[b] = {'rot': [math.sin(t * TAU / per(1.7) + i * 1.3) * 14, 0, math.sin(t * TAU / per(2.3) + i * 2.1) * 12]}
    return out


def chain(m, parent, names, pts, widths, mat, depths=None, ext=0.15, **kw):
    """Цепочка костей по точкам: кость names[i] в pts[i] держит брусок pts[i] → pts[i+1]."""
    depths = depths or widths
    prev = parent
    for i, nm in enumerate(names):
        m.bone(nm, prev, pts[i])
        m.rod(nm, pts[i], pts[i + 1], widths[i], depths[i], mat, ext=ext, **kw)
        prev = nm
    return names[-1]


def hand(m, parent, name, wrist, dirv, palm_len, palm_w, finger_len, fingers=4, fw=0.35, mat='skin', spread=14, curl=20,
         side=1, thumb=True, claw='ink', joints=2):
    """Кисть: ладонь от запястья по dirv, пальцы веером (каждый палец — кость у корня, 2–3 фаланги, на конце коготь)."""
    dirv = np.asarray(dirv, float)
    dirv = dirv / np.linalg.norm(dirv)
    wrist = np.asarray(wrist, float)
    # боковая ось ладони — горизонталь ⟂ направлению
    lat = np.cross(dirv, [0, 0, 1.0]) if abs(dirv[2]) < 0.9 else np.cross(dirv, [1.0, 0, 0])
    lat = lat / np.linalg.norm(lat)
    nrm = np.cross(lat, dirv)
    m.bone(name, parent, wrist)
    knuck = wrist + dirv * palm_len
    m.rod(name, wrist, knuck, palm_w, palm_w * 0.4, mat, ext=0.1)
    fnames = []
    for k in range(fingers):
        f = (k - (fingers - 1) / 2) / max(1, (fingers - 1) / 2)
        base = knuck + lat * f * palm_w * 0.42
        ang = math.radians(spread * f)
        d0 = dirv * math.cos(ang) + lat * math.sin(ang)
        L = finger_len * (1 - 0.18 * abs(f))
        fn = '%s_f%d' % (name, k)
        m.bone(fn, name, base)
        p = base
        seg = [0.45, 0.33, 0.22][:joints] if joints < 3 else [0.42, 0.33, 0.25]
        seg = np.array(seg) / sum(seg)
        dcur = d0
        for j in range(joints):
            a = math.radians(curl * (j + 1) / joints)
            dcur = dcur * math.cos(a) - nrm * math.sin(a) * side
            dcur = dcur / np.linalg.norm(dcur)
            q = p + dcur * L * seg[j]
            m.rod(fn, p, q, fw * (1 - 0.15 * j), fw * (1 - 0.15 * j), mat if j < joints - 1 else claw, ext=0.05)
            p = q
        m.rod(fn, p, p + dcur * fw * 1.8, fw * 0.5, fw * 0.5, claw, ext=0.0)
        fnames.append(fn)
        m.tips = getattr(m, 'tips', {})
        m.tips[fn] = p + dcur * fw * 1.8
    if thumb:
        tb = wrist + dirv * palm_len * 0.35 - lat * palm_w * 0.55 * side
        tq = tb + (dirv * 0.6 - lat * 0.8 * side) / np.linalg.norm(dirv * 0.6 - lat * 0.8 * side) * finger_len * 0.55
        m.bone(name + '_th', name, tb)
        m.rod(name + '_th', tb, tq, fw * 1.05, fw * 1.05, mat, ext=0.05)
        fnames.append(name + '_th')
    return knuck, fnames


# ================================================================== 1. Тень-за-углом (nm_lurker)
def build_lurker():
    m = Model('nm_lurker', density=4, tex_w=128)
    add_common(m, 0, 42, seed=11)

    def body(ctx):                                   # тело — чернила, на «лице» едва заметные впадины глаз
        c = ink_rgb(ctx, 11)
        if ctx.bone == 'head' and ctx.face == 'north':
            P = ctx.P
            for sx in (-1, 1):
                d = np.hypot((P[:, 0] - sx * 0.85) / 0.6, (P[:, 1] - 38.6) / 0.35)
                c = mix(c, hex2('#010002'), sstep(1.0, 0.3, d) * 0.9)
            d = np.hypot(P[:, 0] / 0.25, (P[:, 1] - 36.6) / 1.2)
            c = mix(c, hex2('#010002'), sstep(1.0, 0.2, d) * 0.5)
        return c, 1.0, None
    m.materials['body'] = body
    m.bone('root', None, (0, 0, 0))
    pool_bone(m, 11)
    m.bone('body', 'root', (0, 20, 0))
    # таз, талия, грудь (узкие, вытянутые), горб
    m.box('body', (-2.3, 18.4, -1.3), (2.3, 21.2, 1.4), 'body')
    m.bone('torso', 'body', (0, 21, 0))
    m.box('torso', (-1.5, 21, -1.0), (1.5, 25.5, 1.1), 'body')
    m.rod('torso', (0, 25, 0.2), (0, 31.6, -0.6), 5.4, 3.0, 'body')
    m.rod('torso', (0, 30.5, -0.3), (0, 32.4, -0.9), 7.6, 2.2, 'body')                # плечевой пояс
    for k in range(6):                                                               # позвонки на спине
        y = 22 + k * 1.7
        m.cbox('torso', (0, y, 1.15 + 0.12 * k), (0.8, 0.9, 0.7), 'body')
    for k in range(4):                                                               # рёбра проступают
        y = 26.2 + k * 1.25
        for sx in (-1, 1):
            m.rod('torso', (sx * 0.4, y, -1.75 + k * 0.06), (sx * 2.5, y - 0.7, -0.9), 0.38, 0.38, 'body')
    # шея и голова: гладкий вытянутый овал, без лица, наклонена вперёд
    m.bone('neck', 'torso', (0, 32, -0.6))
    m.rod('neck', (0, 32, -0.6), (0, 35.4, -1.6), 1.25, 1.25, 'body')
    m.bone('head', 'neck', (0, 35.2, -1.6))
    hc = np.array([0, 38.0, -2.0])
    m.cbox('head', hc, (3.2, 6.0, 3.4), 'body')
    m.cbox('head', hc + [0, 0.2, 0], (2.6, 7.2, 2.8), 'body')
    m.cbox('head', hc + [0, -0.4, 0], (3.6, 4.2, 2.8), 'body')
    m.cbox('head', hc + [0, 0.4, 0.2], (2.4, 5.4, 3.9), 'body')
    m.cbox('head', hc + [0, -3.2, -0.3], (1.6, 0.8, 1.8), 'body')                     # острый подбородок
    drip(m, 'head', 'drip_chin', hc + [0, -3.6, -0.4], 2.6, 0.4)
    for k in range(5):                                                               # чернильные «волосы»-струйки вверх с темени
        a = TAU * k / 5 + 0.4
        b = np.array([math.cos(a) * 0.9, 41.3, -2.0 + math.sin(a) * 0.9])
        m.bone('wisp%d' % k, 'head', b)
        m.rod('wisp%d' % k, b, b + [math.cos(a) * 1.6, 3.2 + k % 2, math.sin(a) * 1.4 + 0.8], 0.55, 0.55, 'drip')
        m.rod('wisp%d' % k, b + [math.cos(a) * 1.6, 3.2 + k % 2, math.sin(a) * 1.4 + 0.8],
              b + [math.cos(a) * 1.2, 5.6 + k % 2, math.sin(a) * 1.0 + 1.8], 0.32, 0.32, 'drip')
    # руки до земли
    for side, sn in ((1, 'r'), (-1, 'l')):
        sh = np.array([side * 3.7, 31.6, -0.6])
        el = np.array([side * 4.6, 21.0, -1.4])
        wr = np.array([side * 4.4, 10.2, -2.2])
        m.bone('arm_' + sn, 'torso', sh)
        m.cbox('arm_' + sn, sh, (1.9, 1.9, 1.9), 'body')
        m.rod('arm_' + sn, sh, el, 1.3, 1.3, 'body', ext=0.2)
        m.bone('fore_' + sn, 'arm_' + sn, el)
        m.cbox('fore_' + sn, el, (1.4, 1.4, 1.4), 'body')
        m.rod('fore_' + sn, el, wr, 1.05, 1.05, 'body', ext=0.15)
        _, fn = hand(m, 'fore_' + sn, 'hand_' + sn, wr, (0, -1, -0.12), 2.6, 1.7, 6.2, fingers=4, fw=0.34, mat='body', claw='body',
                     spread=10, curl=24, side=1, joints=3)
        for k, f in enumerate(fn[1:4:2]):
            drip(m, f, 'drip_%s%d' % (sn, k), m.tips[f] + [0, 0.2, 0], 1.6, 0.3)
    # ноги: длинные, тонкие
    for side, sn in ((1, 'r'), (-1, 'l')):
        hip = np.array([side * 1.6, 19.2, 0])
        kn = np.array([side * 1.9, 10.2, -1.0])
        an = np.array([side * 1.8, 1.0, 0.4])
        m.bone('leg_' + sn, 'body', hip)
        m.rod('leg_' + sn, hip, kn, 1.5, 1.5, 'body', ext=0.2)
        m.bone('shin_' + sn, 'leg_' + sn, kn)
        m.cbox('shin_' + sn, kn, (1.3, 1.3, 1.3), 'body')
        m.rod('shin_' + sn, kn, an, 1.1, 1.1, 'body', ext=0.2)
        m.rod('shin_' + sn, an + [0, 0, 0.3], an + [side * 0.1, -0.6, -3.2], 1.1, 0.7, 'body')     # стопа-коготь
    # рваные ленты-тени с плеч и пояса
    rng = random.Random(25)
    for k in range(9):
        a = -0.9 + 1.8 * k / 8
        x = math.sin(a) * 3.0
        z = 1.0 + math.cos(a) * 0.3
        L = rng.uniform(5, 11)
        m.rod('torso', (x, 31.4, z), (x * 1.15, 31.4 - L, z + 0.8), 1.3, 0.12, 'rag')
    for k in range(7):
        a = TAU * k / 7
        x, z = math.cos(a) * 2.2, math.sin(a) * 1.4
        L = rng.uniform(4, 8)
        m.rod('body', (x, 20.4, z), (x * 1.25, 20.4 - L, z * 1.2), 1.4, 0.12, 'rag')
    return m


def lurker_anims(m):
    an = []
    LEGS = {}

    def idle(t):
        o = drip_keys(m, t)
        sway = math.sin(t * TAU / 4)
        o.update({'body': {'rot': [0, 0, sway * 1.2]}, 'torso': {'rot': [-4 + math.sin(t * TAU / 2) * 1.2, 0, 0]},
                  'arm_r': {'rot': [math.sin(t * TAU / 4 + 1) * 2, 0, 2]}, 'arm_l': {'rot': [math.sin(t * TAU / 4 + 2) * 2, 0, -2]},
                  'pool': {'scale': [0, 0, 0]}})
        # рывок головы: 1.3–1.45 с — резко набок, держит, медленно возвращает
        jerk = 0 if t < 1.3 else (min(1, (t - 1.3) / 0.12) if t < 2.4 else max(0, 1 - (t - 2.4) / 1.0))
        o['head'] = {'rot': [6, 0, 28 * jerk + math.sin(t * 13) * 0.6]}
        o['neck'] = {'rot': [4, 0, 6 * jerk]}
        for s in 'rl':
            for k in range(4):
                o['hand_%s_f%d' % (s, k)] = {'rot': [math.sin(t * 9 + k * 1.7 + (s == 'l')) * 4, 0, 0]}
        return o
    a = Anim('animation.nm_lurker.idle', 4.0)
    a.sample(idle)
    an.append(a)

    def walk(t):
        ph = t / 1.6 * TAU
        o = drip_keys(m, t)
        s = math.sin(ph)
        o.update({'body': {'pos': [0, -abs(math.cos(ph)) * 0.8, 0], 'rot': [0, s * 4, 0]},
                  'torso': {'rot': [-10, -s * 6, 0]}, 'head': {'rot': [8, s * 5, 0]}, 'pool': {'scale': [0, 0, 0]},
                  'leg_r': {'rot': [s * 26, 0, 0]}, 'leg_l': {'rot': [-s * 26, 0, 0]},
                  'shin_r': {'rot': [-max(0, -math.cos(ph)) * 34, 0, 0]}, 'shin_l': {'rot': [-max(0, math.cos(ph)) * 34, 0, 0]},
                  'arm_r': {'rot': [-s * 10 + 4, 0, 3]}, 'arm_l': {'rot': [s * 10 + 4, 0, -3]},
                  'fore_r': {'rot': [-6 + s * 4, 0, 0]}, 'fore_l': {'rot': [-6 - s * 4, 0, 0]}})
        return o
    a = Anim('animation.nm_lurker.walk', 1.6)
    a.sample(walk)
    an.append(a)

    def attack(t):
        # 0–0.35 замах: руки взлетают над головой, корпус назад; 0.35–0.5 удар вниз; 0.5–1.0 возврат
        o = drip_keys(m, t)
        if t < 0.35:
            k = (t / 0.35) ** 0.7
            ar, tr = 165 * k, 12 * k
        elif t < 0.5:
            k = (t - 0.35) / 0.15
            ar, tr = 165 - 135 * k ** 2, 12 - 42 * k ** 2
        else:
            k = (t - 0.5) / 0.5
            k = k * k * (3 - 2 * k)
            ar, tr = 30 * (1 - k), -30 * (1 - k)
        o.update({'torso': {'rot': [tr, 0, 0]}, 'arm_r': {'rot': [ar, 0, 8]}, 'arm_l': {'rot': [ar, 0, -8]},
                  'fore_r': {'rot': [ar * 0.15, 0, 0]}, 'fore_l': {'rot': [ar * 0.15, 0, 0]}, 'head': {'rot': [-tr * 0.6, 0, 0]},
                  'pool': {'scale': [0, 0, 0]}})
        for s in 'rl':
            for k2 in range(4):
                o['hand_%s_f%d' % (s, k2)] = {'rot': [30 if 0.3 < t < 0.55 else 0, 0, 0]}
        return o
    a = Anim('animation.nm_lurker.attack', 1.0, loop=False)
    a.sample(attack, 0.025)
    a.instruction(0.45, 'hit')
    an.append(a)

    def lunge(t):
        # «бросок» (смотрел спиной 3 с): присед 0–0.25, рывок вперёд 0.25–0.45 (руки вперёд), удар 0.45 — код двигает сущность
        o = drip_keys(m, t)
        if t < 0.25:
            k = t / 0.25
            o.update({'body': {'pos': [0, -3 * k, 0]}, 'torso': {'rot': [-30 * k, 0, 0]}, 'arm_r': {'rot': [-20 * k, 0, 10]},
                      'arm_l': {'rot': [-20 * k, 0, -10]}, 'leg_r': {'rot': [30 * k, 0, 0]}, 'leg_l': {'rot': [30 * k, 0, 0]},
                      'shin_r': {'rot': [-55 * k, 0, 0]}, 'shin_l': {'rot': [-55 * k, 0, 0]}})
        else:
            k = min(1, (t - 0.25) / 0.2)
            k2 = max(0, (t - 0.6) / 0.4)
            e = k * (1 - k2)
            o.update({'body': {'pos': [0, -3 * (1 - k), 0]}, 'torso': {'rot': [-30 - 15 * e + 45 * k2, 0, 0]},
                      'arm_r': {'rot': [100 * e, 0, 12]}, 'arm_l': {'rot': [100 * e, 0, -12]},
                      'leg_r': {'rot': [30 - 50 * e, 0, 0]}, 'leg_l': {'rot': [30 + 10 * e, 0, 0]},
                      'shin_r': {'rot': [-55 * (1 - k), 0, 0]}, 'shin_l': {'rot': [-55 * (1 - k) - 20 * e, 0, 0]},
                      'head': {'rot': [-20 * e, 0, 0]}})
        o['pool'] = {'scale': [0, 0, 0]}
        return o
    a = Anim('animation.nm_lurker.lunge', 1.0, loop=False)
    a.sample(lunge, 0.025)
    a.instruction(0.45, 'hit')
    an.append(a)
    an += rise_sink(m, 'nm_lurker', 42)

    def dissolve(t):
        # «посмотрели прямо» — 0.5 с: силуэт рвётся по ширине и опадает чернилами
        k = min(1, t / 0.5)
        o = drip_keys(m, t)
        o.update({'body': {'scale': [1 - k * 0.95, 1 + 0.15 * k, 1 - k * 0.95], 'pos': [0, -18 * k ** 2, 0]},
                  'pool': {'scale': [k * 1.2, 1, k * 1.2]}})
        return o
    a = Anim('animation.nm_lurker.dissolve', 0.6, loop='hold')
    a.sample(dissolve, 0.025)
    an.append(a)
    return an


def rise_sink(m, mid, height, body='body', dur_in=1.2, dur_out=1.0):
    """Появление (из лужи чернил — поднимается, вытягиваясь) и исчезновение (тонет в луже, сжимаясь). Одинаково у всех."""

    def appear(t):
        o = drip_keys(m, t)
        k = min(1, t / dur_in)
        e = 1 - (1 - k) ** 3
        pool = min(1, t / 0.25) * (1 - max(0, (t - dur_in * 0.8) / (dur_in * 0.2)))
        o[body] = {'pos': [0, -height * (1 - e), 0], 'scale': [0.55 + 0.45 * e, 1.0 + 0.25 * (1 - e) * e * 4 * 0.25, 0.55 + 0.45 * e]}
        o['pool'] = {'scale': [max(0.001, pool * 1.1), 1, max(0.001, pool * 1.1)]}
        return o
    a1 = Anim('animation.%s.appear' % mid, dur_in, loop='hold')
    a1.sample(appear, 0.04)

    def vanish(t):
        o = drip_keys(m, t)
        k = min(1, t / dur_out)
        e = k ** 2.2
        pool = min(1, t / 0.2) * (1 - max(0, (t - dur_out * 0.85) / (dur_out * 0.15)))
        o[body] = {'pos': [0, -height * e, 0], 'scale': [1 - 0.5 * k, 1 + 0.2 * math.sin(k * math.pi), 1 - 0.5 * k]}
        o['pool'] = {'scale': [max(0.001, pool * 1.2), 1, max(0.001, pool * 1.2)]}
        return o
    a2 = Anim('animation.%s.vanish' % mid, dur_out, loop='hold')
    a2.sample(vanish, 0.04)
    return [a1, a2]


# ================================================================== 2. Ползун (nm_crawler)
def build_crawler():
    m = Model('nm_crawler', density=4, tex_w=128)
    add_common(m, 2, 17, seed=23, skin=hex2('#D2CBC6'))

    def crack(ctx):                                  # мякоть по линии трещины-рта: мокрая, тёмно-багровая, светится изнутри
        c = flesh_rgb(ctx, 23) * 0.7
        g = glow_of(np.array([0.55, 0.05, 0.16]), sstep(0.3, 0.9, fbm(ctx.P, 0.8, 5, 2)) * 0.8)
        return c, 1.0, g

    def face(ctx):                                    # гладкая кожа без черт; у трещины — потёки чернил вниз
        c = skin_rgb(ctx, 23, base=hex2('#D8D0CA'), bruise=0.35, veins=0.5)
        if ctx.face in ('north', 'up', 'down'):
            P = ctx.P
            d = np.abs(P[:, 0])
            c = mix(c, hex2('#5A2030'), sstep(0.9, 0.2, d) * 0.6)
            sm = (d < 0.25 + 0.5 * vnoise(P * [0, 0.6, 0], 1, 3)) & (P[:, 1] < 12.4)
            c = mix(c, ink_rgb(ctx, 4), sm.astype(float) * 0.9)
        return c, 1.0, None
    m.materials.update(crack=crack, face=face)
    m.bone('root', None, (0, 0, 0))
    pool_bone(m, 12)
    m.bone('body', 'root', (0, 11.5, 0))
    m.rod('body', (0, 11.6, -1.4), (0, 12.2, -8.4), 6.2, 4.4, 'skin')          # грудная клетка
    m.rod('body', (0, 11.2, -1.8), (0, 11.4, 4.6), 4.2, 3.0, 'skin')           # впалый живот
    m.rod('body', (0, 11.6, 4.2), (0, 11.2, 8.0), 5.6, 3.6, 'skin')            # таз
    for k in range(12):                                                       # позвонки
        z = -7.8 + k * 1.35
        top = 14.4 if z < -1.6 else (12.9 if z < 4.2 else 13.6)
        m.cbox('body', (0, top - 0.1, z), (1.0, 0.9, 0.85), 'skin')
    for sx in (-1, 1):
        m.rod('body', (sx * 1.6, 14.1, -7.0), (sx * 3.6, 15.8, -4.0), 2.2, 0.45, 'skin')     # лопатки торчат
        for k in range(5):
            z = -7.4 + k * 1.25
            m.rod('body', (sx * 2.7, 13.7, z), (sx * 3.3, 10.4, z + 0.4), 0.45, 0.45, 'skin')  # рёбра
        m.rod('body', (sx * 2.0, 12.3, 4.8), (sx * 2.9, 13.6, 7.6), 0.9, 0.9, 'skin')         # тазовые кости
    # шея и голова: два полушария вдоль вертикальной трещины-рта (раскрываются в стороны)
    m.bone('neck', 'body', (0, 12.6, -8.0))
    m.rod('neck', (0, 12.6, -8.0), (0, 11.6, -10.6), 2.0, 2.0, 'skin', ext=0.3)
    m.bone('head', 'neck', (0, 11.6, -10.6))
    hc = np.array([0, 12.0, -13.4])
    for sx, nm in ((1, 'head_r'), (-1, 'head_l')):
        m.bone(nm, 'head', (sx * 0.05, 12.0, -10.8))
        m.box(nm, hc + [sx * 0.28, -2.6, -2.8], hc + [sx * 2.4, 2.6, 2.6], 'face')
        m.box(nm, hc + [sx * 0.28, -2.1, -3.15], hc + [sx * 2.0, 2.1, 2.9], 'face')
        m.box(nm, hc + [sx * 0.28, -3.0, -2.2], hc + [sx * 1.9, 3.0, 2.0], 'face')
        m.box(nm, hc + [sx * 0.0, -2.5, -2.75], hc + [sx * 0.3, 2.5, 2.5], 'crack')
        for k in range(8):                                                    # зубы вдоль трещины
            y = 9.9 + k * 0.6
            z = -16.0 + 0.35 * abs(k - 3.5) * 0.4
            m.rod(nm, (sx * 0.2, y, z + 0.3), (-sx * 0.45, y + 0.12 * (1 if k < 4 else -1), z + 0.25), 0.34, 0.42, 'teeth', root='up')
            m.rod(nm, (sx * 0.2, y + 0.3, z + 1.3), (-sx * 0.3, y + 0.3, z + 1.3), 0.3, 0.32, 'teeth', root='up')
    drip(m, 'head', 'drip_mouth', (0, 9.4, -15.9), 2.4, 0.42)
    m.cbox('head', (0, 12.0, -12.0), (0.9, 4.0, 3.0), 'void')                   # глотка в глубине
    # руки: локти вывернуты вверх, предплечья в землю, кисти распластаны, пальцы длинные
    for side, sn in ((1, 'r'), (-1, 'l')):
        sh = np.array([side * 3.0, 12.2, -6.8])
        el = np.array([side * 6.8, 18.0, -8.6])
        wr = np.array([side * 7.6, 1.4, -12.2])
        m.bone('arm_' + sn, 'body', sh)
        m.cbox('arm_' + sn, sh, (2.0, 2.0, 2.0), 'skin')
        m.rod('arm_' + sn, sh, el, 1.6, 1.6, 'skin', ext=0.2)
        m.bone('fore_' + sn, 'arm_' + sn, el)
        m.cbox('fore_' + sn, el, (1.8, 1.8, 1.8), 'skin')                       # острый локоть
        m.rod('fore_' + sn, el + [0, 0.4, 0.6], el + [side * 0.2, 1.5, 1.4], 0.6, 0.6, 'skin')
        m.rod('fore_' + sn, el, wr, 1.25, 1.25, 'skin', ext=0.15)
        hand(m, 'fore_' + sn, 'hand_' + sn, wr, (side * 0.3, -0.18, -1.0), 2.4, 2.0, 5.2, fingers=4, fw=0.38, mat='skin', claw='ink',
             spread=22, curl=34, side=-1, joints=3)
    for side, sn in ((1, 'r'), (-1, 'l')):
        hip = np.array([side * 2.6, 11.2, 6.8])
        kn = np.array([side * 6.6, 17.2, 10.4])
        an = np.array([side * 6.8, 1.2, 9.0])
        m.bone('leg_' + sn, 'body', hip)
        m.rod('leg_' + sn, hip, kn, 2.0, 2.0, 'skin', ext=0.2)
        m.bone('shin_' + sn, 'leg_' + sn, kn)
        m.cbox('shin_' + sn, kn, (2.0, 2.0, 2.0), 'skin')
        m.rod('shin_' + sn, kn, an, 1.4, 1.4, 'skin', ext=0.15)
        m.bone('foot_' + sn, 'shin_' + sn, an)
        m.rod('foot_' + sn, an, an + [side * 0.4, -0.6, -3.4], 1.6, 0.8, 'skin')
        for k in range(3):
            b = an + [side * 0.4 + (k - 1) * 0.5, -0.6, -3.4]
            m.rod('foot_' + sn, b, b + [(k - 1) * 0.4, -0.3, -1.4], 0.32, 0.32, 'ink')
    # клочья волос
    rng = random.Random(7)
    for k in range(6):
        b = hc + [rng.uniform(-1.6, 1.6), 2.4, rng.uniform(0, 2.4)]
        m.rod('head', b, b + [rng.uniform(-0.6, 0.6), -rng.uniform(2, 5), 1.5 + rng.uniform(0, 1)], 0.6, 0.1, 'rag')
    return m


def crawler_anims(m):
    an = []

    def idle(t):
        o = drip_keys(m, t)
        jerk = [0, 0]
        for t0, ang in ((0.6, 32), (1.25, -18), (2.1, 40)):
            if t >= t0:
                jerk = [t0, ang]
        tw = max(0, min(1, (t - jerk[0]) / 0.06)) if jerk[0] else 0
        prev = {0.6: 0, 1.25: 32, 2.1: -18}.get(jerk[0], 0)
        yaw = prev + (jerk[1] - prev) * tw if jerk[0] else 0
        if t > 2.6:
            yaw *= max(0, 1 - (t - 2.6) / 0.4)
        o.update({'body': {'pos': [0, math.sin(t * TAU / per(1.5)) * 0.25, 0]}, 'head': {'rot': [0, yaw, math.sin(t * 7) * 2 + 8]},
                  'pool': {'scale': [0, 0, 0]}})
        for s in 'rl':
            for k in range(4):
                o['hand_%s_f%d' % (s, k)] = {'rot': [max(0, math.sin(t * TAU / per(0.75) + k * 0.9 + (s == 'l') * 2)) * 18, 0, 0]}
        return o
    a = Anim('animation.nm_crawler.idle', 3.0)
    a.sample(idle)
    an.append(a)

    def walk(t):
        ph = t / 0.8 * TAU
        o = drip_keys(m, t)
        s, c = math.sin(ph), math.cos(ph)
        o.update({'body': {'pos': [0, abs(c) * 0.7, 0], 'rot': [0, s * 6, s * 3]}, 'head': {'rot': [0, -s * 8, 0]},
                  'arm_r': {'rot': [s * 24, 0, -max(0, s) * 10]}, 'fore_r': {'rot': [-s * 12, 0, 0]},
                  'arm_l': {'rot': [-s * 24, 0, max(0, -s) * 10]}, 'fore_l': {'rot': [s * 12, 0, 0]},
                  'leg_l': {'rot': [s * 22, 0, 0]}, 'shin_l': {'rot': [-s * 10, 0, 0]},
                  'leg_r': {'rot': [-s * 22, 0, 0]}, 'shin_r': {'rot': [s * 10, 0, 0]}, 'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.nm_crawler.walk', 0.8)
    a.sample(walk, 0.04)
    an.append(a)

    def attack(t):
        # 0–0.3 встаёт на задние: перед вверх, голова раскрывается; 0.3–0.5 бросок вниз-вперёд, укус на 0.45; 0.5–0.9 назад
        o = drip_keys(m, t)
        if t < 0.3:
            k = (t / 0.3) ** 0.8
            up, op = 38 * k, 34 * k
        elif t < 0.5:
            k = (t - 0.3) / 0.2
            up, op = 38 - 50 * k, 34 if t < 0.43 else 34 * (1 - (t - 0.43) / 0.07)
        else:
            k = (t - 0.5) / 0.4
            k = min(1, k)
            up, op = -12 * (1 - k), 0
        o.update({'body': {'rot': [up, 0, 0], 'pos': [0, max(0, up) * 0.12, 0]}, 'head': {'rot': [-up * 0.6, 0, 0]},
                  'head_r': {'rot': [0, -op, 0]}, 'head_l': {'rot': [0, op, 0]},
                  'arm_r': {'rot': [up * 1.2, 0, 0]}, 'arm_l': {'rot': [up * 1.2, 0, 0]},
                  'leg_r': {'rot': [-up * 0.8, 0, 0]}, 'leg_l': {'rot': [-up * 0.8, 0, 0]}, 'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.nm_crawler.attack', 0.9, loop=False)
    a.sample(attack, 0.025)
    a.instruction(0.45, 'hit')
    an.append(a)

    def pounce(t):
        # прыжок с потолка/стены (код переворачивает модель на потолке): сжаться 0–0.2, растопыриться 0.2–0.7 (голова раскрыта), приземлиться
        o = drip_keys(m, t)
        if t < 0.2:
            k = t / 0.2
            sp, op = -18 * k, 0
        elif t < 0.7:
            k = (t - 0.2) / 0.5
            sp, op = -18 + 58 * min(1, k * 2.5), 40
        else:
            k = (t - 0.7) / 0.3
            sp, op = 40 * (1 - k), 40 * (1 - k)
        o.update({'arm_r': {'rot': [sp, 0, -sp * 0.5]}, 'arm_l': {'rot': [sp, 0, sp * 0.5]},
                  'leg_r': {'rot': [-sp, 0, -sp * 0.3]}, 'leg_l': {'rot': [-sp, 0, sp * 0.3]},
                  'head_r': {'rot': [0, -op, 0]}, 'head_l': {'rot': [0, op, 0]}, 'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.nm_crawler.pounce', 1.0, loop=False)
    a.sample(pounce, 0.025)
    a.instruction(0.75, 'hit')
    an.append(a)
    an += rise_sink(m, 'nm_crawler', 20)
    return an


# ================================================================== 3. Пустой ребёнок (nm_hollow_child)
def build_child():
    m = Model('nm_hollow_child', density=6, tex_w=96)
    add_common(m, 0, 19, seed=37, skin=hex2('#E6DED6'))

    def gown(ctx):                                    # грязная ночная рубашка: пятна, к подолу пропитана чернилами
        P = ctx.P
        c = mix(hex2('#D6CEC0'), hex2('#A89C88'), fbm(P, 0.3, 37, 4))
        c = mix(c, hex2('#7A6A58'), sstep(0.62, 0.85, fbm(P, 0.25, 41, 3)) * 0.7)
        folds = 0.5 + 0.5 * np.sin((P[:, 0] * 0.8 + P[:, 2] * 0.6) * 2.2 + fbm(P, 0.3, 2, 2) * 4)
        c = c * (0.86 + 0.14 * folds)[:, None]
        soak = 3.2 + 2.6 * fbm(P * [1, 0, 1], 0.5, 43, 3)
        c = mix(c, ink_rgb(ctx, 37), sstep(soak + 0.6, soak - 0.6, P[:, 1]))
        sm, hl = streaks(P, 6, 13, 44, p=0.25, lmax=6)
        c = mix(c, ink_rgb(ctx, 37), sm * 0.85)
        a = tatter_alpha(ctx, 37, depth=0.18, freq=7) if ctx.cube.info.get('hem') else 1.0
        return c, a, None

    def face(ctx):
        P = ctx.P
        c = skin_rgb(ctx, 37, base=hex2('#ECE4DC'), bruise=0.3, veins=0.6, dirt=0.25)
        g = np.zeros((ctx.n, 3))
        if ctx.face == 'north':
            for sx in (-1, 1):
                d = np.hypot((P[:, 0] - sx * 1.35) / 0.95, (P[:, 1] - 15.6) / 1.15)
                c = mix(c, hex2('#3A2030'), sstep(1.5, 1.0, d) * 0.7)                  # тёмные круги
                c = mix(c, hex2('#010001'), sstep(1.0, 0.85, d))                      # дыры
                pin = np.hypot((P[:, 0] - sx * 1.3) / 0.16, (P[:, 1] - 15.5) / 0.16)
                g = g + glow_of(np.array([0.85, 0.08, 0.22]), sstep(1.0, 0.0, pin))   # искра в глубине
                # чернильные слёзы из дыр
                tear = (np.abs(P[:, 0] - sx * (1.2 + 0.2 * np.sin(P[:, 1] * 1.3))) < 0.22 + 0.12 * (P[:, 1] < 13.2)) & (P[:, 1] < 15.0)
                c = mix(c, ink_rgb(ctx, 5), tear.astype(float))
            mouth = (np.abs(P[:, 1] - (13.3 - 0.25 * np.cos(P[:, 0] * 1.4))) < 0.16) & (np.abs(P[:, 0]) < 1.3)
            c = mix(c, hex2('#200810'), mouth.astype(float))
        return c, 1.0, g

    def hair(ctx):
        P = ctx.P
        st = 0.5 + 0.5 * np.sin((P[:, 0] * 3.1 + P[:, 2] * 2.3) * 2.0 + fbm(P, 0.6, 5, 2) * 3)
        c = mix(hex2('#050306'), hex2('#2A2030'), st * 0.6 + 0.2 * fbm(P, 2, 6, 2))
        a = tatter_alpha(ctx, int(abs(ctx.cube.frm[0]) * 31) % 50, depth=0.45, freq=13)
        return c, a, None
    m.materials.update(gown=gown, cface=face, hair=hair)
    m.bone('root', None, (0, 0, 0))
    pool_bone(m, 7)
    m.bone('body', 'root', (0, 6, 0))
    m.box('body', (-2.3, 6.5, -1.4), (2.3, 11.6, 1.4), 'gown')
    m.box('body', (-2.6, 10.2, -1.6), (2.6, 11.7, 1.6), 'gown')                    # плечики
    m.bone('skirt', 'body', (0, 7.4, 0))
    for k in range(10):
        a = TAU * k / 10
        top = np.array([math.sin(a) * 2.0, 7.6, -math.cos(a) * 1.3])
        bot = np.array([math.sin(a) * 3.6, 1.0 + 0.25 * math.sin(a * 3), -math.cos(a) * 2.6])
        m.rod('skirt', top, bot, 2.0, 0.22, 'gown', roll=-math.degrees(a), hem=True)
    m.bone('neck', 'body', (0, 11.6, 0))
    m.cbox('neck', (0, 12.1, 0), (1.2, 1.4, 1.2), 'skin')
    m.bone('head', 'neck', (0, 12.4, 0))
    hc = np.array([0, 15.4, -0.1])
    m.cbox('head', hc, (5.6, 6.0, 5.4), 'cface')
    m.cbox('head', hc + [0, 0.1, 0], (5.0, 6.6, 4.8), 'cface')
    m.cbox('head', hc + [0, 0, 0.1], (6.0, 5.2, 5.0), 'cface')
    # волосы: шапка и длинные пряди до пояса спереди по бокам и сзади
    m.cbox('head', hc + [0, 2.0, 0.4], (6.2, 2.6, 5.6), 'hair')
    rng = random.Random(3)
    for k in range(16):
        a = -2.4 + 4.8 * k / 15
        x, z = math.sin(a) * 3.05, math.cos(a) * 2.8 + 0.2
        L = rng.uniform(5.5, 9.5) if abs(a) > 0.6 else rng.uniform(3.0, 5.0)
        m.rod('head', (x, 18.0, z), (x * 1.08, 18.0 - L, z * 1.06), 1.3, 0.16, 'hair', roll=math.degrees(a))
    for sx in (-1, 1):                                    # пряди на лицо
        m.rod('head', (sx * 2.2, 18.2, -2.9), (sx * 2.4, 12.6, -3.0), 1.4, 0.14, 'hair')
    # руки тонкие, кисти с длинными пальцами
    for side, sn in ((1, 'r'), (-1, 'l')):
        sh = np.array([side * 2.6, 11.0, 0])
        el = np.array([side * 3.1, 7.8, 0.1])
        wr = np.array([side * 3.0, 4.6, -0.4])
        m.bone('arm_' + sn, 'body', sh)
        m.rod('arm_' + sn, sh, el, 1.1, 1.1, 'skin', ext=0.15)
        m.rod('arm_' + sn, sh, sh + [side * 0.2, -1.8, 0], 1.6, 1.6, 'gown')            # рукавчик
        m.bone('fore_' + sn, 'arm_' + sn, el)
        m.rod('fore_' + sn, el, wr, 0.9, 0.9, 'skin', ext=0.1)
        hand(m, 'fore_' + sn, 'hand_' + sn, wr, (0, -1, -0.1), 1.2, 1.1, 2.6, fingers=4, fw=0.22, mat='skin', claw='ink', spread=8,
             curl=18, joints=2, thumb=False)
    for side, sn in ((1, 'r'), (-1, 'l')):
        hip = np.array([side * 1.0, 6.4, 0])
        m.bone('leg_' + sn, 'body', hip)
        m.rod('leg_' + sn, hip, (side * 1.1, 0.4, 0.1), 1.0, 1.0, 'skin', ext=0.1)
        m.box('leg_' + sn, (side * 1.1 - 0.55, 0, -1.4), (side * 1.1 + 0.55, 0.6, 0.6), 'skin')
    drip(m, 'head', 'drip_eye_r', (1.3, 12.3, -2.75), 1.6, 0.3)
    drip(m, 'head', 'drip_eye_l', (-1.3, 12.0, -2.75), 1.9, 0.3)
    drip(m, 'skirt', 'drip_hem0', (1.8, 1.4, -2.2), 1.2, 0.35)
    drip(m, 'skirt', 'drip_hem1', (-2.4, 1.3, 1.6), 1.0, 0.35)
    return m


def child_anims(m):
    an = []

    def idle(t):
        o = drip_keys(m, t)
        k = 0.5 - 0.5 * math.cos(t * TAU / 5.0)
        o.update({'body': {'rot': [0, 0, math.sin(t * TAU / 2.5) * 2]}, 'head': {'rot': [4, 0, 24 * k]}, 'skirt': {'rot': [0, math.sin(t * TAU / 2.5) * 3, 0]},
                  'arm_r': {'rot': [math.sin(t * TAU / 2.5) * 3, 0, 0]}, 'arm_l': {'rot': [-math.sin(t * TAU / 2.5) * 3, 0, 0]},
                  'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.nm_hollow_child.idle', 5.0)
    a.sample(idle)
    an.append(a)

    def walk(t):
        ph = t / 1.2 * TAU
        s = math.sin(ph)
        o = drip_keys(m, t)
        o.update({'body': {'pos': [0, abs(math.cos(ph)) * 0.3, 0], 'rot': [0, 0, s * 3]}, 'head': {'rot': [6, 0, 10 + s * 4]},
                  'leg_r': {'rot': [s * 18, 0, 0]}, 'leg_l': {'rot': [-s * 18, 0, 0]}, 'skirt': {'rot': [0, s * 5, 0]},
                  'arm_r': {'rot': [-s * 4, 0, 0]}, 'arm_l': {'rot': [s * 4, 0, 0]}, 'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.nm_hollow_child.walk', 1.2)
    a.sample(walk, 0.04)
    an.append(a)

    def laugh(t):
        # смех: плечи трясутся, голова запрокидывается и клонится; звук — код (смех со всех сторон)
        o = drip_keys(m, t)
        env = math.sin(min(1, t / 2.0) * math.pi)
        sh = math.sin(t * TAU * 6) * env
        o.update({'body': {'rot': [-6 * env, 0, sh * 2], 'pos': [0, abs(sh) * 0.2, 0]}, 'head': {'rot': [20 * env, 0, 18 * env + sh * 4]},
                  'arm_r': {'rot': [sh * 4, 0, 0]}, 'arm_l': {'rot': [-sh * 4, 0, 0]}, 'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.nm_hollow_child.laugh', 2.0, loop=False)
    a.sample(laugh, 0.025)
    a.instruction(0.0, 'laugh')
    an.append(a)

    def attack(t):
        o = drip_keys(m, t)
        k = min(1, t / 0.25)
        r = max(0, (t - 0.55) / 0.35)
        e = k * (1 - r)
        o.update({'arm_r': {'rot': [110 * e, 0, 14 * e]}, 'arm_l': {'rot': [110 * e, 0, -14 * e]},
                  'fore_r': {'rot': [-20 * e, 0, 0]}, 'fore_l': {'rot': [-20 * e, 0, 0]},
                  'body': {'rot': [-14 * e, 0, 0]}, 'head': {'rot': [-10 * e, 0, 30 * e]}, 'pool': {'scale': [0, 0, 0]}})
        for s in 'rl':
            for k2 in range(4):
                o['hand_%s_f%d' % (s, k2)] = {'rot': [50 if 0.35 < t < 0.6 else 0, 0, 0]}
        return o
    a = Anim('animation.nm_hollow_child.attack', 0.9, loop=False)
    a.sample(attack, 0.025)
    a.instruction(0.45, 'hit')
    an.append(a)
    an += rise_sink(m, 'nm_hollow_child', 20, dur_in=0.6, dur_out=0.4)
    return an


# ================================================================== 4. Руки из земли (nm_hands)
def build_hands():
    m = Model('nm_hands', density=4, tex_w=128)
    add_common(m, 0, 16, seed=53)

    def arm(ctx):                                     # бледные руки, из земли — в чернилах и грязи по запястье
        P = ctx.P
        c = skin_rgb(ctx, 53, base=hex2('#E0D8D0'), bruise=0.5, veins=0.9, dirt=0.55)
        lvl = 2.0 + 3.5 * fbm(P, 0.3, 54, 3)
        c = mix(c, ink_rgb(ctx, 53), sstep(lvl + 0.7, lvl - 0.7, P[:, 1]))
        sm, hl = streaks(P, 4, 16, 55, p=0.35, lmax=7)
        c = mix(c, ink_rgb(ctx, 53), sm * 0.85) + SHEEN * (hl * 0.4)[:, None]
        return c, 1.0, None
    m.materials['arm'] = arm

    def puddle(ctx):
        c, a, g = m.materials['pool'](ctx)
        return c, a, None
    m.materials['puddle'] = puddle
    m.bone('root', None, (0, 0, 0))
    m.bone('puddle', 'root', (0, 0, 0))
    m.box('puddle', (-15, 0.02, -15), (15, 0.08, 15), 'puddle', hide=('north', 'south', 'east', 'west', 'down'))
    rng = random.Random(1907)
    n = 16
    m.arms = []
    for k in range(n):
        r = 2.0 + 9.0 * math.sqrt((k + 0.5) / n)
        a = k * 2.39996 + 0.3
        base = np.array([math.cos(a) * r, -0.6, math.sin(a) * r])
        inward = -base / max(1e-6, np.linalg.norm(base))
        inward[1] = 0
        up = np.array([0, 1.0, 0])
        L1, L2 = rng.uniform(4.5, 9.0), rng.uniform(4.0, 7.0)
        out = -inward
        d1 = up + out * rng.uniform(0.0, 0.35) + np.array([rng.uniform(-0.25, 0.25), 0, rng.uniform(-0.25, 0.25)])
        d1 /= np.linalg.norm(d1)
        el = base + d1 * L1
        tw = rng.uniform(-1, 1)                                   # предплечье: вверх и вбок/к центру — тянется, ищет
        side = np.cross(up, inward)
        d2 = up * rng.uniform(0.6, 1.0) + inward * rng.uniform(-0.1, 0.4) + side * tw * 0.5
        d2 /= np.linalg.norm(d2)
        wr = el + d2 * L2
        an_, fo, hd = 'arm%d' % k, 'fore%d' % k, 'hand%d' % k
        m.bone(an_, 'root', base)
        m.rod(an_, base, el, 1.25, 1.25, 'arm', ext=0.2)
        m.bone(fo, an_, el)
        m.cbox(fo, el, (1.3, 1.3, 1.3), 'arm')
        m.rod(fo, el, wr, 1.05, 1.05, 'arm', ext=0.15)
        hdir = d2 * 0.6 + up * 0.5
        hand(m, fo, hd, wr, hdir, 1.5, 1.4, rng.uniform(2.6, 3.6), fingers=4, fw=0.3, mat='arm', claw='ink', spread=rng.uniform(12, 26),
             curl=rng.uniform(30, 60), joints=3)
        m.arms.append((an_, fo, hd, a))
    for k in range(4):
        drip(m, 'hand%d' % (k * 4 + 1), 'drip%d' % k, m.tips['hand%d_f1' % (k * 4 + 1)], 1.4, 0.28)
    return m


def hands_anims(m):
    an = []

    def idle(t):
        o = drip_keys(m, t)
        for i, (a_, f_, h_, ang) in enumerate(m.arms):
            ph = i * 1.71
            o[a_] = {'rot': [math.sin(t * TAU / per(2.0) + ph) * 9, 0, math.sin(t * TAU / per(1.5) + ph * 1.3) * 9]}
            o[f_] = {'rot': [math.sin(t * TAU / per(1.0) + ph * 0.7) * 14, 0, 0]}
            for k in range(4):
                o['%s_f%d' % (h_, k)] = {'rot': [math.sin(t * TAU / per(0.6) + ph + k) * 18 - 8, 0, 0]}
        return o
    a = Anim('animation.nm_hands.idle', 3.0)
    a.sample(idle)
    an.append(a)

    def grab(t):
        # хватают за ноги (удержание 1.5 с): 0–0.12 рывок к центру, пальцы сжаты; держат с дрожью; 1.4–1.6 отпускают
        o = drip_keys(m, t)
        k = min(1, t / 0.12)
        r = max(0, (t - 1.4) / 0.2)
        e = k * (1 - r)
        for i, (a_, f_, h_, ang) in enumerate(m.arms):
            sh = math.sin(t * 40 + i) * 2 * e
            # наклон к центру: ось поворота ⟂ направлению на центр
            tilt = 22 * e
            o[a_] = {'rot': [-math.sin(ang) * tilt + sh, 0, math.cos(ang) * tilt + sh]}
            o[f_] = {'rot': [26 * e, 0, 0]}
            for kk in range(4):
                o['%s_f%d' % (h_, kk)] = {'rot': [70 * e, 0, 0]}
        return o
    a = Anim('animation.nm_hands.grab', 1.6, loop=False)
    a.sample(grab, 0.02)
    a.instruction(0.12, 'grab')
    an.append(a)

    def appear(t):
        o = drip_keys(m, t)
        o['puddle'] = {'scale': [max(0.001, min(1, t / 0.3)), 1, max(0.001, min(1, t / 0.3))]}
        for i, (a_, f_, h_, ang) in enumerate(m.arms):
            k = max(0, min(1, (t - 0.15 - (i % 5) * 0.08) / 0.5))
            e = 1 - (1 - k) ** 3
            o[a_] = {'pos': [0, -14 * (1 - e), 0], 'rot': [math.sin(t * 9 + i) * 10 * (1 - e), 0, 0]}
        return o
    a = Anim('animation.nm_hands.appear', 1.0, loop='hold')
    a.sample(appear, 0.04)
    an.append(a)

    def vanish(t):
        o = drip_keys(m, t)
        for i, (a_, f_, h_, ang) in enumerate(m.arms):
            k = max(0, min(1, (t - (i % 5) * 0.06) / 0.5))
            o[a_] = {'pos': [0, -16 * k ** 2, 0]}
            for kk in range(4):
                o['%s_f%d' % (h_, kk)] = {'rot': [40 * k, 0, 0]}
        s = 1 - max(0, (t - 0.6) / 0.3)
        o['puddle'] = {'scale': [max(0.001, s), 1, max(0.001, s)]}
        return o
    a = Anim('animation.nm_hands.vanish', 0.9, loop='hold')
    a.sample(vanish, 0.04)
    an.append(a)
    return an


# ================================================================== 5. Пасть (nm_maw)
def build_maw():
    m = Model('nm_maw', density=3, tex_w=192)
    add_common(m, 20, 60, seed=71, skin=hex2('#CEC4BE'))

    def hide(ctx):                                    # шкура челюсти: бугристая, серо-бледная, в синяках, складки, потёки
        P = ctx.P
        c = skin_rgb(ctx, 71, base=hex2('#C8BEB8'), bruise=0.7, veins=0.9, dirt=0.5)
        lump = fbm(P, 0.12, 72, 3)
        c = c * (0.82 + 0.28 * lump)[:, None]
        wr = 0.5 + 0.5 * np.sin(P[:, 1] * 1.4 + fbm(P, 0.15, 77, 2) * 5)                 # складки шкуры поперёк
        c = c * (0.9 + 0.1 * wr)[:, None]
        sm, hl = streaks(P, 30, 58, 73, p=0.45, lmax=16, cw=1.2)
        c = mix(c, ink_rgb(ctx, 71), sm) + SHEEN * (hl * 0.5)[:, None]
        return c, 1.0, None

    def gum(ctx):
        c = flesh_rgb(ctx, 71)
        return c, 1.0, glow_of(np.array([0.3, 0.02, 0.08]), sstep(0.55, 0.9, fbm(ctx.P, 0.5, 9, 2)))

    def throat(ctx):                                  # глубина глотки — багровый свет из темноты
        P = ctx.P
        c = mix(hex2('#0A0206'), DEEPRED, sstep(0.3, 0.8, fbm(P, 0.3, 74, 3)))
        g = glow_of(np.array([0.75, 0.06, 0.2]), sstep(0.35, 0.85, fbm(P, 0.25, 75, 3)) * 0.85)
        return c, 1.0, g

    def eye(ctx):                                     # слепые молочные глаза по краю панциря
        P = ctx.P
        c = mix(hex2('#E8E4DA'), hex2('#B8B0A8'), fbm(P, 2, 76, 2))
        cen = ctx.cube.frm + (ctx.cube.to - ctx.cube.frm) / 2
        d = np.linalg.norm(P - cen, axis=1) / (0.5 * np.max(ctx.cube.to - ctx.cube.frm))
        c = mix(c, hex2('#7A1040'), sstep(0.5, 0.3, d) * 0.5)
        return c, 1.0, glow_of(np.array([0.5, 0.45, 0.4]), sstep(0.6, 0.0, d) * 0.5)
    m.materials.update(hide=hide, gum=gum, throat=throat, eye=eye)
    m.bone('root', None, (0, 0, 0))
    pool_bone(m, 22)
    m.bone('body', 'root', (0, 38, 4))
    # глотка-туловище сзади (шея к челюстям), горб с шипами
    m.cbox('body', (0, 41, 9.5), (14, 13, 9), 'hide')
    m.cbox('body', (0, 42, 13), (10, 10, 4), 'hide')
    for k in range(7):                                                      # шипы-позвонки по хребту
        z = 4 + k * 2.2
        m.rod('body', (0, 47.4 + (2 if k < 3 else 0), z), (0, 51 + (2 if k < 3 else 0) - k * 0.3, z + 1.6), 1.0 - k * 0.06, 1.0, 'ink')
    m.cbox('body', (0, 41, 5.5), (12, 9, 1), 'throat')
    # верхняя челюсть (панцирь-череп) и нижняя — шарнир сзади
    m.bone('jaw_top', 'body', (0, 41, 6))
    m.box('jaw_top', (-11, 42, -13), (11, 49, 6), 'hide')
    m.box('jaw_top', (-9, 49, -11), (9, 52, 5), 'hide')
    m.box('jaw_top', (-6, 52, -7), (6, 53.5, 3), 'hide')
    m.box('jaw_top', (-10.4, 43, -13.8), (10.4, 47.6, -12.4), 'hide')                  # надбровный валик
    m.box('jaw_top', (-11.8, 42.6, -11), (11.8, 47, 4), 'hide')                       # скулы шире
    for k in range(5):                                                         # гребни-складки по куполу
        z = -9 + k * 3.2
        m.rod('jaw_top', (-8.5, 52.2 - abs(k - 2) * 0.3, z), (8.5, 52.2 - abs(k - 2) * 0.3, z), 1.2, 1.0, 'hide')
    m.box('jaw_top', (-11.6, 41, -13.6), (11.6, 42.6, 5.5), 'gum')                # десна по кромке
    m.box('jaw_top', (-9.5, 42, -11.5), (9.5, 43, 5), 'throat', hide=('up',))     # нёбо
    for sx in (-1, 1):
        for k, (y, z) in enumerate(((47.5, -12.6), (46.2, -11.9), (48.6, -10.4))):
            m.cbox('jaw_top', (sx * (6.5 - k * 2.2), y, z), (1.6, 1.6, 0.9), 'eye')
    m.bone('jaw_bot', 'body', (0, 40, 6))
    m.box('jaw_bot', (-10.4, 31, -12.4), (10.4, 39, 6), 'hide')
    m.box('jaw_bot', (-8, 29, -10), (8, 31.5, 4), 'hide')
    m.box('jaw_bot', (-5, 27.6, -11.5), (5, 30, -4), 'hide')                           # подбородок
    m.box('jaw_bot', (-11, 33, -10), (11, 38, 4), 'hide')
    m.box('jaw_bot', (-11, 38.2, -13), (11, 40, 5.5), 'gum')
    m.box('jaw_bot', (-9, 37.4, -11), (9, 38.5, 4.5), 'throat', hide=('down',))
    m.cbox('jaw_bot', (0, 39.0, -4), (6, 1.4, 12), 'flesh')                          # язык
    rng = random.Random(4)

    def teeth_row(bone, y, down, n, x0, x1, z, L, w):
        for k in range(n):
            x = x0 + (x1 - x0) * (k + 0.5) / n + rng.uniform(-0.2, 0.2)
            l = L * rng.uniform(0.6, 1.25)
            tip = np.array([x + rng.uniform(-0.5, 0.5), y - l if down else y + l, z + rng.uniform(-0.6, 0.6)])
            m.rod(bone, (x, y, z), tip, w, w * 0.8, 'teeth', root='up' if down else 'down')
    teeth_row('jaw_top', 41.4, True, 11, -10.5, 10.5, -12.8, 4.0, 1.25)               # передний ряд сверху
    teeth_row('jaw_top', 41.6, True, 13, -9.0, 9.0, -10.4, 2.6, 0.9)                  # второй ряд
    teeth_row('jaw_bot', 39.4, False, 10, -10.0, 10.0, -12.2, 3.6, 1.2)
    teeth_row('jaw_bot', 39.0, False, 12, -8.5, 8.5, -9.8, 2.2, 0.85)
    for sx in (-1, 1):                                                         # клыки по бокам
        for k in range(5):
            z = -10 + k * 3.0
            m.rod('jaw_top', (sx * 10.6, 41.4, z), (sx * 10.2, 37.6 + k * 0.4, z + 0.3), 1.0, 1.0, 'teeth', root='up')
            m.rod('jaw_bot', (sx * 10.1, 39.4, z + 1.4), (sx * 9.8, 42.4 - k * 0.3, z + 1.6), 0.95, 0.95, 'teeth', root='down')
    drip(m, 'jaw_bot', 'drip0', (-5, 30.4, -9), 4.0, 0.7)
    drip(m, 'jaw_bot', 'drip1', (3, 30.0, -8), 5.0, 0.6)
    drip(m, 'jaw_bot', 'drip2', (8.5, 31.0, -11.5), 3.0, 0.6)
    drip(m, 'jaw_top', 'drip3', (-10.8, 41.0, -12), 3.4, 0.55)
    # четыре тонкие ноги-ходули: колени выше туловища (как у паука)
    m.legs = []
    for i, (sx, z0) in enumerate(((1, -2), (-1, -2), (1, 10), (-1, 10))):
        hip = np.array([sx * 6.5, 35.0, z0])
        kn = np.array([sx * 18.0, 54.0, z0 + (-6 if z0 < 4 else 6)])
        an = np.array([sx * 24.0, 1.0, z0 + (-12 if z0 < 4 else 14)])
        ln = 'leg%d' % i
        m.bone(ln, 'body', hip)
        m.cbox(ln, hip, (3.0, 3.0, 3.0), 'hide')
        m.rod(ln, hip, kn, 1.8, 1.8, 'hide', ext=0.3)
        m.bone('shin%d' % i, ln, kn)
        m.cbox('shin%d' % i, kn, (2.4, 2.4, 2.4), 'hide')
        m.rod('shin%d' % i, kn, kn + (kn - hip) / np.linalg.norm(kn - hip) * 2.4, 0.9, 0.9, 'ink')       # шип колена
        m.rod('shin%d' % i, kn, an, 1.3, 1.3, 'hide', ext=0.2)
        for k in range(3):
            m.rod('shin%d' % i, an, an + [(k - 1) * 1.2, -1.0, (-1.6 if z0 < 4 else 1.6)], 0.6, 0.6, 'ink')
        m.legs.append((ln, 'shin%d' % i, sx, z0))
    return m


def maw_anims(m):
    an = []

    def idle(t):
        o = drip_keys(m, t, period=2.6, amp=1.2)
        br = 0.5 - 0.5 * math.cos(t * TAU / per(3.0))
        o.update({'jaw_top': {'rot': [3 * br, 0, 0]}, 'jaw_bot': {'rot': [-4 * br, 0, 0]}, 'body': {'pos': [0, -br * 0.6, 0]},
                  'pool': {'scale': [0, 0, 0]}})
        for (ln, sn, sx, z0) in m.legs:
            o[sn] = {'rot': [0, 0, sx * br * 2]}
        return o
    a = Anim('animation.nm_maw.idle', 3.0)
    a.sample(idle)
    an.append(a)

    def walk(t):
        ph = t / 2.4 * TAU
        o = drip_keys(m, t, period=2.4, amp=1.2)
        o.update({'body': {'pos': [0, -abs(math.sin(ph)) * 1.4, 0], 'rot': [0, math.sin(ph) * 3, math.sin(ph) * 2]},
                  'jaw_bot': {'rot': [-3 - 3 * abs(math.sin(ph)), 0, 0]}, 'pool': {'scale': [0, 0, 0]}})
        for i, (ln, sn, sx, z0) in enumerate(m.legs):
            p = ph + (0 if i in (0, 3) else math.pi)
            lift = max(0, math.sin(p))
            o[ln] = {'rot': [math.cos(p) * 14, 0, -sx * lift * 12]}
            o[sn] = {'rot': [-math.cos(p) * 6, 0, sx * lift * 10]}
        return o
    a = Anim('animation.nm_maw.walk', 2.4)
    a.sample(walk)
    an.append(a)

    def roar(t):
        # рёв: 0–0.4 раскрывается, 0.4–1.6 держит и трясётся (экран дрожит — код по инструкции 'roar'), 1.6–2.0 закрывается
        o = drip_keys(m, t, period=0.8, amp=1.6)
        k = min(1, t / 0.4) if t < 1.6 else max(0, 1 - (t - 1.6) / 0.4)
        e = k * k * (3 - 2 * k)
        sh = math.sin(t * 50) * 0.6 * (0.4 < t < 1.6)
        o.update({'jaw_top': {'rot': [34 * e, 0, sh]}, 'jaw_bot': {'rot': [-38 * e, 0, -sh]},
                  'body': {'rot': [12 * e, 0, sh * 1.5], 'pos': [sh * 0.4, 1.2 * e, 0]}, 'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.nm_maw.roar', 2.0, loop=False)
    a.sample(roar, 0.025)
    a.instruction(0.4, 'roar')
    an.append(a)

    def attack(t):
        # укус-таран: 0–0.35 пасть раскрывается, корпус назад; 0.35–0.55 бросок вперёд-вниз, захлопывается на 0.55 (удар, отброс)
        o = drip_keys(m, t)
        if t < 0.35:
            k = t / 0.35
            op, lean = 40 * k, 10 * k
        elif t < 0.55:
            k = (t - 0.35) / 0.2
            op, lean = 40 * (1 - k ** 3), 10 - 30 * k
        else:
            k = min(1, (t - 0.55) / 0.45)
            op, lean = 0, -20 * (1 - k)
        o.update({'jaw_top': {'rot': [op * 0.45, 0, 0]}, 'jaw_bot': {'rot': [-op, 0, 0]}, 'body': {'rot': [lean, 0, 0], 'pos': [0, 0, min(0, lean) * 0.4]},
                  'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.nm_maw.attack', 1.0, loop=False)
    a.sample(attack, 0.025)
    a.instruction(0.55, 'hit')
    an.append(a)
    an += rise_sink(m, 'nm_maw', 60, dur_in=1.6, dur_out=1.3)
    return an


# ================================================================== 6. Плакальщица (nm_weeper)
def build_weeper():
    m = Model('nm_weeper', density=4, tex_w=128)
    add_common(m, 0, 44, seed=89, skin=hex2('#EAE2DC'))

    def dress(ctx):
        c = cloth_rgb(ctx, 89, a=hex2('#08060A'), b=hex2('#2A1A30'))
        P = ctx.P
        c = c + hex2('#3A2448') * (sstep(0.8, 1.0, ridge(P * [1, 0.15, 1], 0.7, 90, 2)) * 0.35)[:, None]      # блеск атласа
        sm, hl = streaks(P, 10, 36, 91, p=0.25)
        c = mix(c, INK0, sm * 0.6) + SHEEN * (hl * 0.35)[:, None]
        a = tatter_alpha(ctx, 89, depth=0.12, freq=11) if ctx.cube.info.get('hem') else 1.0
        return c, a, None

    def veil(ctx):                                    # чёрное кружево: соты-дырочки и вьюнок; сквозь него видно лицо
        P = ctx.P
        u = P[:, 0] * 1.25 + P[:, 2] * 1.25 * (ctx.face in ('east', 'west')) + 0.3 * np.sin(P[:, 1] * 0.7)
        v = P[:, 1] * 1.25
        hx = np.abs(((u + (np.floor(v) % 2) * 0.5) % 1.0) - 0.5)
        hy = np.abs((v % 1.0) - 0.5)
        hole = (hx < 0.22 + 0.1 * vnoise(P, 0.4, 94)) & (hy < 0.24)
        motif = np.abs(np.sin(u * 0.9) * 1.6 - ((v * 0.5) % 3.2 - 1.6)) < 0.25
        a = (~hole | motif).astype(float)
        if ctx.cube.info.get('hem'):
            a = a * tatter_alpha(ctx, 92, depth=0.2, freq=15)
        c = mix(hex2('#060408'), hex2('#2A2030'), fbm(P, 0.8, 93, 2) * 0.6)
        return c, a, None

    def wface(ctx):                                   # лицо под вуалью: восковая бледность, чёрные слёзы-реки от глаз
        P = ctx.P
        c = skin_rgb(ctx, 89, base=hex2('#EEE6E0'), bruise=0.25, veins=0.6, dirt=0.15)
        g = None
        if ctx.face == 'north':
            g = np.zeros((ctx.n, 3))
            for sx in (-1, 1):
                d = np.hypot((P[:, 0] - sx * 1.0) / 0.75, (P[:, 1] - 40.4) / 0.42)
                c = mix(c, hex2('#020103'), sstep(1.0, 0.6, d))
                c = mix(c, hex2('#3A1A2A'), sstep(1.6, 1.0, d) * 0.6)
                wob = 0.12 * np.sin(P[:, 1] * 2.2 + sx)
                tear = (np.abs(P[:, 0] - sx * 1.0 - wob) < 0.32 + 0.1 * (40.0 - P[:, 1]) / 4) & (P[:, 1] < 40.3)
                c = mix(c, ink_rgb(ctx, 7, 1.5), tear.astype(float))
                g = g + glow_of(np.array([0.22, 0.05, 0.3]), tear.astype(float) * 0.6)
            mouth = (np.hypot(P[:, 0] / 0.7, (P[:, 1] - 38.3) / 0.45) < 1)
            c = mix(c, hex2('#1A0610'), mouth.astype(float))
        return c, 1.0, g
    m.materials.update(dress=dress, veil=veil, wface=wface)
    m.bone('root', None, (0, 0, 0))
    pool_bone(m, 12)
    m.bone('body', 'root', (0, 26, 0))
    m.box('body', (-2.6, 26, -1.6), (2.6, 33.4, 1.7), 'dress')
    m.box('body', (-3.2, 31.4, -1.8), (3.2, 34.2, 1.9), 'dress')
    m.box('body', (-2.0, 25.2, -1.3), (2.0, 27.0, 1.4), 'dress')
    m.bone('skirt', 'body', (0, 26, 0))
    for k in range(14):
        a = TAU * k / 14
        top = np.array([math.sin(a) * 2.4, 26.4, -math.cos(a) * 1.6])
        bot = np.array([math.sin(a) * 7.2, 0.0, -math.cos(a) * 6.2 + 0.8])
        m.rod('skirt', top, bot, 3.6, 0.24, 'dress', roll=-math.degrees(a), hem=True)
    for k in range(5):                                                         # шлейф сзади по земле
        x = -3 + k * 1.5
        m.rod('skirt', (x, 1.2, 5.5), (x * 1.3, 0.15, 12 + (k % 2) * 2), 2.2, 0.2, 'dress', hem=True)
    m.bone('neck', 'body', (0, 34, 0))
    m.rod('neck', (0, 33.8, 0), (0, 37.4, -0.5), 1.4, 1.4, 'skin')
    m.bone('head', 'neck', (0, 37.2, -0.5))
    hc = np.array([0, 39.9, -0.6])
    m.cbox('head', hc, (3.6, 5.2, 3.8), 'wface')
    m.cbox('head', hc + [0, -0.3, 0], (3.0, 5.6, 3.2), 'wface')
    # вуаль: колпак и полотнища до лопаток, спереди — полупрозрачное кружево перед лицом
    m.cbox('head', hc + [0, 2.0, 0.1], (4.4, 1.6, 4.4), 'veil')
    m.box('head', (-2.3, 34.2, -2.75), (2.3, 42.9, -2.55), 'veil', hem=True)
    for sx in (-1, 1):
        m.rod('head', (sx * 2.25, 42.6, 0.1), (sx * 3.6, 30.5, 0.9), 4.6, 0.2, 'veil', roll=90, hem=True)
    m.rod('head', (0, 42.6, 2.3), (0, 27.0, 4.6), 4.6, 0.2, 'veil', hem=True)
    # руки в длинных рукавах; кисти у лица (плачет)
    for side, sn in ((1, 'r'), (-1, 'l')):
        sh = np.array([side * 3.4, 33.4, 0])
        el = np.array([side * 4.6, 27.6, -2.2])
        wr = np.array([side * 1.7, 35.6, -3.6])
        m.bone('arm_' + sn, 'body', sh)
        m.rod('arm_' + sn, sh, el, 1.5, 1.5, 'dress', ext=0.2)
        m.bone('fore_' + sn, 'arm_' + sn, el)
        m.rod('fore_' + sn, el, wr, 1.3, 1.3, 'dress', ext=0.2)
        m.rod('fore_' + sn, wr + (el - wr) * 0.22, wr + (el - wr) * 0.05, 2.4, 2.4, 'dress')         # раструб манжеты
        hand(m, 'fore_' + sn, 'hand_' + sn, wr, (-side * 0.25, 1.0, -0.25), 1.8, 1.4, 4.2, fingers=4, fw=0.28, mat='skin', claw='ink',
             spread=16, curl=12, joints=3)
    drip(m, 'head', 'drip_r', (0.95, 37.0, -2.6), 2.4, 0.32)
    drip(m, 'head', 'drip_l', (-1.05, 37.3, -2.6), 2.0, 0.32)
    drip(m, 'skirt', 'drip_s', (5.0, 1.0, -4.0), 1.0, 0.4)
    return m


def weeper_anims(m):
    an = []

    def idle(t):
        o = drip_keys(m, t)
        sob = max(0, math.sin(t * TAU / per(1.5))) ** 3
        jit = math.sin(t * 38) * sob
        o.update({'body': {'rot': [-3 - 3 * sob, 0, jit * 0.8], 'pos': [0, sob * 0.2, 0]}, 'head': {'rot': [-12 - 6 * sob, 0, jit * 1.5]},
                  'skirt': {'rot': [0, math.sin(t * TAU / per(3.0)) * 2, 0]}, 'arm_r': {'rot': [sob * 4, 0, 0]}, 'arm_l': {'rot': [sob * 4, 0, 0]},
                  'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.nm_weeper.idle', 3.0)
    a.sample(idle)
    a.instruction(0.0, 'weep')
    an.append(a)

    def walk(t):
        ph = t / 2.0 * TAU
        o = drip_keys(m, t)
        o.update({'body': {'pos': [0, 0.6 + math.sin(ph * 2) * 0.3, 0], 'rot': [-4, 0, math.sin(ph) * 2]},
                  'skirt': {'rot': [4 + math.sin(ph) * 3, math.sin(ph) * 4, 0]}, 'head': {'rot': [-14, 0, math.sin(ph) * 3]},
                  'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.nm_weeper.walk', 2.0)
    a.sample(walk)
    an.append(a)

    def flee(t):
        # убегает от взгляда: скользит быстро, корпус наклонён, голова отвёрнута, юбка тянется назад
        ph = t / 0.8 * TAU
        o = drip_keys(m, t)
        o.update({'body': {'pos': [0, 1.0 + math.sin(ph * 2) * 0.2, 0], 'rot': [-16, 0, math.sin(ph) * 3]},
                  'skirt': {'rot': [16, 0, 0]}, 'head': {'rot': [-10, 70, 10]}, 'neck': {'rot': [0, 25, 0]},
                  'arm_r': {'rot': [-30, 0, 20]}, 'arm_l': {'rot': [-24, 0, -10]}, 'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.nm_weeper.flee', 0.8)
    a.sample(flee, 0.04)
    an.append(a)

    def wail(t):
        # вопль (усиливает остальных): голова запрокидывается, руки раскидываются, пальцы скрючены
        o = drip_keys(m, t, period=0.8, amp=1.5)
        k = min(1, t / 0.4) if t < 2.1 else max(0, 1 - (t - 2.1) / 0.4)
        e = k * k * (3 - 2 * k)
        sh = math.sin(t * 45) * e
        o.update({'head': {'rot': [40 * e, 0, sh * 2]}, 'neck': {'rot': [12 * e, 0, 0]}, 'body': {'rot': [10 * e, 0, sh]},
                  'arm_r': {'rot': [-40 * e, 0, 60 * e]}, 'arm_l': {'rot': [-40 * e, 0, -60 * e]},
                  'fore_r': {'rot': [-30 * e, 0, 0]}, 'fore_l': {'rot': [-30 * e, 0, 0]}, 'pool': {'scale': [0, 0, 0]}})
        for s in 'rl':
            for k2 in range(4):
                o['hand_%s_f%d' % (s, k2)] = {'rot': [45 * e, 0, 0]}
        return o
    a = Anim('animation.nm_weeper.wail', 2.5, loop=False)
    a.sample(wail, 0.025)
    a.instruction(0.4, 'wail')
    an.append(a)
    an += rise_sink(m, 'nm_weeper', 46)
    return an


# ================================================================== 7. Мотыльки-глаза (nm_moth): рой из 12 мотыльков
def build_moth():
    m = Model('nm_moth', density=8, tex_w=64)
    add_common(m, 0, 30, seed=101)

    def wing(ctx):                                    # пыльное крыло, жилки; в центре — глаз (белок, багровая радужка, зрачок)
        L = ctx.L
        c0 = ctx.cube.frm
        sz = ctx.cube.to - ctx.cube.frm
        u = (L[:, 0] - c0[0]) / sz[0]
        v = (L[:, 2] - c0[2]) / sz[2]
        side = ctx.cube.info['side']
        uu = u if side > 0 else 1 - u                  # 0 — у тела, 1 — кончик
        vv = (v - 0.5) * 2                             # −1..1, симметрично (спереди/сзади одинаково)
        prof = 0.95 * np.sin(np.clip(uu, 0, 1) * math.pi * 0.92 + 0.12) ** 0.7
        scal = 0.05 * np.sin(uu * 26) * (uu > 0.6)
        inside = np.abs(vv) < prof - scal
        c = mix(hex2('#5E5048'), hex2('#2E2428'), fbm(np.stack([u * 8, v * 8, np.zeros_like(u)], -1), 1, 102, 3))
        c = mix(c, hex2('#1A1216'), sstep(0.75, 1.0, np.abs(vv) / np.maximum(prof, 1e-3)))
        for k in range(5):
            ang = -0.8 + 0.4 * k
            vein = np.abs(vv - np.tan(ang) * uu * 0.6) < 0.035
            c = mix(c, hex2('#140C10'), vein.astype(float) * 0.7)
        d = np.hypot((uu - 0.55) / 0.3, vv / 0.55)
        ring = [(1.0, '#E8E0D8'), (0.72, '#7A1040'), (0.5, '#C83060'), (0.36, '#050205')]
        g = np.zeros((ctx.n, 3))
        for r_, col in ring:
            c = mix(c, hex2(col), sstep(r_, r_ - 0.06, d))
        g = g + glow_of(np.array([0.85, 0.12, 0.3]), sstep(0.72, 0.6, d) * sstep(0.34, 0.42, d))
        hl = np.hypot((uu - 0.5) / 0.05, (vv + 0.12) / 0.08) < 1
        c = mix(c, hex2('#FFFFFF'), hl.astype(float))
        g = g + glow_of(np.array([1, 1, 1]), hl.astype(float) * 0.8)
        return c, inside.astype(float), g

    def mbody(ctx):
        c = mix(hex2('#2A2024'), hex2('#5A4A40'), fbm(ctx.P, 3, 103, 2))
        return c, 1.0, None
    m.materials.update(wing=wing, mbody=mbody)
    m.bone('root', None, (0, 0, 0))
    m.bone('swarm', 'root', (0, 24, 0))
    rng = random.Random(55)
    m.moths = []
    for k in range(12):
        a = k * 2.39996
        r = 4 + 7 * rng.random()
        p = np.array([math.cos(a) * r, 24 + rng.uniform(-8, 8), math.sin(a) * r])
        nm = 'moth%d' % k
        m.bone(nm, 'swarm', p)
        s = rng.uniform(0.8, 1.25)
        m.cbox(nm, p, (0.7 * s, 0.7 * s, 2.6 * s), 'mbody')
        m.rod(nm, p + [0, 0.2, -1.3 * s], p + [0.6 * s, 0.6 * s, -2.6 * s], 0.12, 0.12, 'mbody')
        m.rod(nm, p + [0, 0.2, -1.3 * s], p + [-0.6 * s, 0.6 * s, -2.6 * s], 0.12, 0.12, 'mbody')
        for side in (1, -1):
            wn = '%s_w%s' % (nm, 'r' if side > 0 else 'l')
            m.bone(wn, nm, p + [side * 0.3 * s, 0.2 * s, 0])
            x0 = side * 0.3 * s
            m.box(wn, p + [min(x0, x0 + side * 4.4 * s), 0.18 * s, -2.4 * s], p + [max(x0, x0 + side * 4.4 * s), 0.24 * s, 1.6 * s], 'wing',
                  side=side, hide=('north', 'south', 'east', 'west'))
        m.moths.append((nm, p, s, rng.uniform(0, TAU), rng.uniform(0.7, 1.3)))
    return m


def moth_anims(m):
    an = []

    def fly(t):
        o = {}
        for i, (nm, p, s, ph, sp) in enumerate(m.moths):
            # беспорядочная орбита: петли вокруг своего места (бесшовно за 4 с)
            w = TAU / 4.0
            k1, k2 = 1 + i % 2, 2 + i % 3
            o[nm] = {'pos': [math.sin(w * k1 * t + ph) * 3.0, math.sin(w * k2 * t + ph * 1.7) * 2.2, math.cos(w * k1 * t + ph) * 3.0],
                     'rot': [math.sin(w * k2 * t + ph) * 15, math.degrees(w * k1 * t) if i % 2 else -math.degrees(w * k1 * t), 0]}
            fl = math.sin(t * TAU * 5 * (1 if i % 2 else 1) + ph) * 55
            o[nm + '_wr'] = {'rot': [0, 0, fl]}
            o[nm + '_wl'] = {'rot': [0, 0, -fl]}
        o['swarm'] = {'rot': [0, t / 4.0 * 360 * 0.0, 0]}
        return o
    a = Anim('animation.nm_moth.idle', 4.0)
    a.sample(fly, 0.025)
    an.append(a)
    b = Anim('animation.nm_moth.walk', 4.0)
    b.keys = a.keys
    an.append(b)

    def swarm_face(t):
        # «облепить»: рой стягивается в плоский диск перед лицом жертвы (точка +z вперёд — код ставит сущность у головы)
        o = fly(t)
        k = min(1, t / 0.5)
        for i, (nm, p, s, ph, sp) in enumerate(m.moths):
            a_ = TAU * i / len(m.moths)
            tgt = np.array([math.cos(a_) * 6, 24 + math.sin(a_) * 4.5, -8.0]) - p
            pos = np.array(o[nm]['pos']) * (1 - k) + tgt * k
            o[nm]['pos'] = list(pos)
            o[nm]['rot'] = [-90 * k + o[nm]['rot'][0] * (1 - k), o[nm]['rot'][1] * (1 - k), 0]
        return o
    a = Anim('animation.nm_moth.attack', 1.5, loop=False)
    a.sample(swarm_face, 0.025)
    a.instruction(0.5, 'cover_screen')
    an.append(a)

    def appear(t):
        o = fly(t)
        k = min(1, t / 0.8)
        e = 1 - (1 - k) ** 3
        o['swarm'] = {'scale': [max(0.01, e), max(0.01, e), max(0.01, e)]}
        return o
    a = Anim('animation.nm_moth.appear', 0.8, loop='hold')
    a.sample(appear, 0.025)
    an.append(a)

    def vanish(t):
        o = fly(t)
        k = min(1, t / 0.8)
        for i, (nm, p, s, ph, sp) in enumerate(m.moths):
            out = (p - [0, 24, 0]) / max(1e-6, np.linalg.norm(p - [0, 24, 0])) * 30 * k ** 2
            o[nm]['pos'] = list(np.array(o[nm]['pos']) + out)
            o[nm]['scale'] = [max(0.01, 1 - k)] * 3
        return o
    a = Anim('animation.nm_moth.vanish', 0.8, loop='hold')
    a.sample(vanish, 0.025)
    an.append(a)
    return an


# ================================================================== 8. Ужас (nm_dread): заклинатель глазами жертвы (мифическое)
def build_dread():
    m = Model('nm_dread', density=4, tex_w=128)
    add_common(m, 0, 50, seed=131)

    def mask(ctx):                                    # фарфоровая маска куклы: трещины, из глазниц льются чернила, улыбка нарисована
        P = ctx.P
        c = mix(hex2('#F2ECE2'), hex2('#CFC6BA'), fbm(P, 0.4, 131, 3) * 0.8)
        cr = ridge(P, 0.45, 132, 3)
        c = mix(c, hex2('#1A0A12'), sstep(0.955, 0.99, cr))
        g = None
        if ctx.face == 'north':
            g = np.zeros((ctx.n, 3))
            for sx in (-1, 1):
                d = np.hypot((P[:, 0] - sx * 1.25) / 0.8, (P[:, 1] - 47.2) / 0.62)
                c = mix(c, hex2('#020103'), sstep(1.0, 0.85, d))
                pin = np.hypot((P[:, 0] - sx * 1.2) / 0.22, (P[:, 1] - 47.1) / 0.22)
                g = g + glow_of(np.array([0.95, 0.1, 0.25]), sstep(1.0, 0.0, pin))
                wob = 0.15 * np.sin(P[:, 1] * 1.9 + sx * 2)
                tear = (np.abs(P[:, 0] - sx * 1.25 - wob) < 0.42 + 0.06 * (47 - P[:, 1])) & (P[:, 1] < 47.0)
                c = mix(c, ink_rgb(ctx, 9, 1.5), tear.astype(float))
            sm = np.abs(P[:, 1] - (44.6 + 0.08 * P[:, 0] ** 2)) < 0.14
            c = mix(c, hex2('#7A1040'), (sm & (np.abs(P[:, 0]) < 2.6)).astype(float))
            for k in range(-4, 5):                                             # стежки-зубы поперёк улыбки
                st = (np.abs(P[:, 0] - k * 0.55) < 0.07) & (np.abs(P[:, 1] - (44.6 + 0.08 * (k * 0.55) ** 2)) < 0.42)
                c = mix(c, hex2('#3A0418'), st.astype(float))
            for sx in (-1, 1):                                                 # румянец куклы
                d = np.hypot((P[:, 0] - sx * 2.0) / 0.7, (P[:, 1] - 45.4) / 0.45)
                c = mix(c, hex2('#C86A80'), sstep(1, 0, d) * 0.45)
        return c, 1.0, g

    def comb(ctx):                                    # гребёнка музыкальной шкатулки — потемневшая латунь
        P = ctx.P
        c = mix(hex2('#8A7448'), hex2('#3A2E1C'), fbm(P, 1.2, 133, 3))
        c = mix(c, hex2('#C8B07A'), sstep(0.85, 1.0, vnoise(P, 3, 134)) * 0.6)
        return c, 1.0, None

    def robe(ctx):
        c, a, g = m.materials['rag'](ctx)
        return c, a, None
    m.materials.update(mask=mask, comb=comb, robe=robe)
    m.bone('root', None, (0, 0, 0))
    pool_bone(m, 14)
    m.bone('body', 'root', (0, 30, 0))
    # без ног: балахон висит и стекает чернильными щупальцами
    m.box('body', (-3.6, 30, -2.2), (3.6, 40, 2.4), 'ink')
    m.box('body', (-4.6, 37.4, -2.6), (4.6, 41.4, 2.8), 'cloth')
    m.rod('body', (0, 38, 2.6), (0, 32, 4.4), 6.0, 1.4, 'ink')                         # горб
    for k in range(7):                                                         # хребет-шипы
        y = 41 - k * 1.6
        m.rod('body', (0, y, 2.4 + k * 0.15), (0, y + 1.0, 5.2 + k * 0.2), 0.9, 0.9, 'ink')
    for k in range(5):                                                         # рёбра наружу
        y = 38.4 - k * 1.5
        for sx in (-1, 1):
            m.rod('body', (sx * 2.6, y, -2.2), (sx * 4.2, y - 1.2, -0.8), 0.45, 0.45, 'mask')
    m.bone('robe', 'body', (0, 31, 0))
    rng = random.Random(77)
    for k in range(16):
        a = TAU * k / 16
        top = np.array([math.sin(a) * 3.6, 36.0, -math.cos(a) * 2.6])
        bot = np.array([math.sin(a) * 7.0, rng.uniform(4, 12), -math.cos(a) * 6.0])
        m.rod('robe', top, bot, 3.4, 0.22, 'rag', roll=-math.degrees(a))
    m.tendrils = []
    for k in range(6):                                                         # щупальца чернил под балахоном
        a = TAU * k / 6 + 0.3
        b = np.array([math.sin(a) * 2.4, 30.5, -math.cos(a) * 1.8])
        names = ['tent%d_%d' % (k, j) for j in range(3)]
        pts = [b, b + [math.sin(a) * 2.5, -9, -math.cos(a) * 2.5], b + [math.sin(a) * 4.5, -18, -math.cos(a) * 4.0],
               b + [math.sin(a) * 5.5, -27.5, -math.cos(a) * 5.0]]
        chain(m, 'body', names, pts, [1.6, 1.2, 0.8], 'drip')
        m.tendrils.append(names)
    # шея и голова-маска, гребёнка шкатулки венцом
    m.bone('neck', 'body', (0, 41.2, -0.2))
    m.rod('neck', (0, 41.2, -0.2), (0, 43.4, -0.8), 1.6, 1.6, 'ink')
    m.bone('head', 'neck', (0, 43.2, -0.8))
    hc = np.array([0, 46.6, -0.9])
    m.cbox('head', hc, (5.4, 7.0, 5.0), 'ink')
    m.box('head', hc + [-2.9, -3.6, -2.75], hc + [2.9, 3.4, -2.45], 'mask')
    m.box('head', hc + [-2.5, -4.0, -2.65], hc + [2.5, 3.8, -2.35], 'mask')
    for k in range(9):                                                         # венец из язычков гребёнки, разной длины, погнуты
        x = -3.2 + k * 0.8
        L = 2.5 + 3.2 * math.sin(math.pi * (k + 0.5) / 9) + (0.8 if k % 3 == 1 else 0)
        m.rod('head', (x, hc[1] + 3.2, hc[2] + 0.4), (x * 1.25, hc[1] + 3.2 + L, hc[2] + 0.8 + (k % 2) * 0.8), 0.5, 0.3, 'comb')
    m.rod('head', (-3.6, hc[1] + 3.3, hc[2] + 0.4), (3.6, hc[1] + 3.3, hc[2] + 0.4), 0.9, 0.9, 'comb')
    drip(m, 'head', 'drip_er', hc + [1.25, -3.9, -2.8], 3.6, 0.42)
    drip(m, 'head', 'drip_el', hc + [-1.25, -3.6, -2.8], 3.0, 0.42)
    # четыре руки: пара обычных (длинные, до колен) и пара из-за спины над плечами
    m.armset = []
    for side, sn in ((1, 'r'), (-1, 'l')):
        sh = np.array([side * 4.4, 40.6, 0])
        el = np.array([side * 6.2, 30.0, -1.2])
        wr = np.array([side * 6.0, 19.0, -2.6])
        m.bone('arm_' + sn, 'body', sh)
        m.cbox('arm_' + sn, sh, (2.4, 2.4, 2.4), 'cloth')
        m.rod('arm_' + sn, sh, el, 1.5, 1.5, 'ink', ext=0.2)
        m.bone('fore_' + sn, 'arm_' + sn, el)
        m.rod('fore_' + sn, el, wr, 1.25, 1.25, 'ink', ext=0.15)
        hand(m, 'fore_' + sn, 'hand_' + sn, wr, (0, -1, -0.15), 2.4, 2.0, 6.0, fingers=4, fw=0.36, mat='mask', claw='ink', spread=12,
             curl=26, joints=3)
        sb = np.array([side * 2.4, 40.4, 2.8])
        eb = np.array([side * 7.4, 50.0, 4.4])
        wb = np.array([side * 9.6, 41.0, -2.4])
        m.bone('xarm_' + sn, 'body', sb)
        m.rod('xarm_' + sn, sb, eb, 1.2, 1.2, 'ink', ext=0.2)
        m.bone('xfore_' + sn, 'xarm_' + sn, eb)
        m.cbox('xfore_' + sn, eb, (1.5, 1.5, 1.5), 'mask')
        m.rod('xfore_' + sn, eb, wb, 1.0, 1.0, 'ink', ext=0.15)
        hand(m, 'xfore_' + sn, 'xhand_' + sn, wb, (side * 0.1, -0.7, -0.7), 2.0, 1.7, 5.0, fingers=4, fw=0.3, mat='mask', claw='ink', spread=20,
             curl=40, joints=3)
        m.armset.append(sn)
    return m


def dread_anims(m):
    an = []

    def tent(o, t, amp=1.0, spd=1.0):
        for i, names in enumerate(m.tendrils):
            for j, nm in enumerate(names):
                o[nm] = {'rot': [math.sin(t * TAU / per(2.0 / spd) + i + j * 0.8) * 10 * amp, 0, math.cos(t * TAU / per(2.0 / spd) + i * 1.3 + j) * 10 * amp]}

    def idle(t):
        o = drip_keys(m, t)
        bob = math.sin(t * TAU / per(4.0))
        o.update({'body': {'pos': [0, 1.2 + bob * 0.8, 0]}, 'head': {'rot': [-6, math.sin(t * TAU / per(4.0)) * 8, math.sin(t * TAU / per(2.0)) * 4]},
                  'robe': {'rot': [math.sin(t * TAU / per(2.0)) * 3, 0, 0]}, 'pool': {'scale': [0, 0, 0]}})
        for s in 'rl':
            o['xarm_' + s] = {'rot': [math.sin(t * TAU / per(4.0) + (s == 'l')) * 6, 0, 0]}
            o['xfore_' + s] = {'rot': [math.sin(t * TAU / per(2.0) + (s == 'l')) * 10, 0, 0]}
            for k in range(4):
                o['xhand_%s_f%d' % (s, k)] = {'rot': [math.sin(t * TAU / per(1.0) + k) * 15, 0, 0]}
        tent(o, t)
        return o
    a = Anim('animation.nm_dread.idle', 4.0)
    a.sample(idle)
    an.append(a)

    def walk(t):
        o = idle(t)
        o['body']['rot'] = [-12, 0, 0]
        o['robe'] = {'rot': [14, 0, 0]}
        tent(o, t, 1.6, 2.0)
        return o
    a = Anim('animation.nm_dread.walk', 2.0)
    a.sample(walk)
    an.append(a)

    def attack(t):
        # все четыре руки: верхние заносятся и бьют сверху, нижние — вперёд; удар на 0.45
        o = drip_keys(m, t)
        if t < 0.3:
            k = t / 0.3
            up, fw = 60 * k, -20 * k
        elif t < 0.45:
            k = (t - 0.3) / 0.15
            up, fw = 60 - 120 * k ** 2, -20 + 110 * k ** 2
        else:
            k = min(1, (t - 0.45) / 0.45)
            up, fw = -60 * (1 - k), 90 * (1 - k)
        o.update({'xarm_r': {'rot': [up, 0, 0]}, 'xarm_l': {'rot': [up, 0, 0]}, 'arm_r': {'rot': [fw, 0, 8]}, 'arm_l': {'rot': [fw, 0, -8]},
                  'body': {'rot': [-max(0, fw) * 0.2, 0, 0], 'pos': [0, 1.2, 0]}, 'head': {'rot': [-10, 0, 0]}, 'pool': {'scale': [0, 0, 0]}})
        tent(o, t, 1.5, 2)
        return o
    a = Anim('animation.nm_dread.attack', 0.9, loop=False)
    a.sample(attack, 0.025)
    a.instruction(0.45, 'hit')
    an.append(a)

    def scream(t):
        o = drip_keys(m, t, period=0.6, amp=1.8)
        k = min(1, t / 0.15) if t < 1.2 else max(0, 1 - (t - 1.2) / 0.3)
        sh = math.sin(t * 60) * k
        o.update({'head': {'rot': [26 * k, sh * 3, sh * 6]}, 'body': {'rot': [8 * k, 0, sh], 'pos': [0, 1.2, 0]},
                  'xarm_r': {'rot': [-40 * k, 0, 30 * k]}, 'xarm_l': {'rot': [-40 * k, 0, -30 * k]}, 'pool': {'scale': [0, 0, 0]}})
        tent(o, t, 2.5, 3)
        return o
    a = Anim('animation.nm_dread.scream', 1.5, loop=False)
    a.sample(scream, 0.025)
    a.instruction(0.1, 'scream')
    an.append(a)
    an += rise_sink(m, 'nm_dread', 52, dur_in=1.6)
    return an


# ================================================================== 9. Мимик (nm_mimic): копия игрока по развёртке скина
SKIN = {  # (u, v, w, h, d) — развёртка скина 64×64 (как в ванили); w — ширина по x, h — высота, d — глубина
    'head': (0, 0, 8, 8, 8), 'hat': (32, 0, 8, 8, 8), 'body': (16, 16, 8, 12, 4), 'jacket': (16, 32, 8, 12, 4),
    'rarm': (40, 16, 4, 12, 4), 'rsleeve': (40, 32, 4, 12, 4), 'larm': (32, 48, 4, 12, 4), 'lsleeve': (48, 48, 4, 12, 4),
    'rleg': (0, 16, 4, 12, 4), 'rpants': (0, 32, 4, 12, 4), 'lleg': (16, 48, 4, 12, 4), 'lpants': (0, 48, 4, 12, 4)}


def skin_faces(part, w=None, rows=None):
    """UV граней по развёртке (east = правый бок персонажа (+x BB), north = перед). rows=(r0, r1) — только строки боковых граней
    (для головы, разрезанной на череп и челюсть); w — узкая рука (slim = 3)."""
    u, v, w0, h, d = SKIN[part]
    w = w or w0
    r0, r1 = rows or (0, h)
    hh = r1 - r0
    f = {'east': (u, v + d + r0, d, hh), 'north': (u + d, v + d + r0, w, hh), 'west': (u + d + w, v + d + r0, d, hh),
         'south': (u + 2 * d + w, v + d + r0, w, hh)}
    if r0 == 0:
        f['up'] = (u + d, v, w, d)
    if r1 == h:
        f['down'] = (u + d + w, v, w, d)
    return f


def build_mimic(slim=False):
    name = 'nm_mimic_slim' if slim else 'nm_mimic'
    m = Model(name, density=4, tex_w=128)
    m.reserved = (0, 0, 64, 64)
    add_common(m, 20, 36, seed=151)

    def gum(ctx):
        return flesh_rgb(ctx, 151), 1.0, glow_of(np.array([0.25, 0.02, 0.08]), sstep(0.5, 0.9, fbm(ctx.P, 0.6, 3, 2)))

    def grin(ctx):                                    # накладка-улыбка: от уха до уха, тонкая чёрная прорезь; глаза чуть темнее
        P = ctx.P
        a = np.zeros(ctx.n)
        c = np.tile(hex2('#140608'), (ctx.n, 1))
        if ctx.face == 'north':
            x, y = P[:, 0], P[:, 1]
            yc = 28.5 + 0.1 * x ** 2
            th = 0.34 - 0.025 * np.abs(x)
            line = (np.abs(y - yc) < th) & (np.abs(x) < 4.0)
            a = line.astype(float)
            for k in range(-6, 7):                                             # мелкие зубы в прорези
                t_ = (np.abs(x - k * 0.55) < 0.12) & (np.abs(y - yc) < th * 0.8)
                c = np.where(t_[:, None], hex2('#D8CCB0'), c)
            c = np.where((np.abs(y - yc) > th * 0.6)[:, None] & line[:, None], hex2('#4A0A1C'), c)   # губы — багровые края
        return c, a, None

    def throat(ctx):
        c = mix(hex2('#050103'), DEEPRED, sstep(0.4, 0.9, fbm(ctx.P, 0.5, 4, 2)))
        return c, 1.0, glow_of(np.array([0.5, 0.04, 0.12]), sstep(0.5, 0.9, fbm(ctx.P, 0.4, 5, 2)) * 0.7)
    m.materials.update(gum=gum, grin=grin, mthroat=throat)
    aw = 3 if slim else 4

    def sbox(bone, frm, to, part, inflate=0.0, rows=None, w=None, hide=()):
        c = m.box(bone, frm, to, 'skin', inflate=inflate, skin=True)
        for f, (u, v, ww, hh) in skin_faces(part, w, rows).items():
            if f not in hide:
                c.uv[f] = (u, v, ww, hh)
        return c
    NECK = 3.0
    m.bone('root', None, (0, 0, 0))
    pool_bone(m, 9)
    m.bone('body', 'root', (0, 24, 0))
    sbox('body', (-4, 12, -2), (4, 24, 2), 'body')
    sbox('body', (-4, 12, -2), (4, 24, 2), 'jacket', 0.25)
    # шея: на 3 длиннее — кожа с подбородка (нижняя строка лица растянута)
    m.bone('neck', 'body', (0, 24, 0))
    c = m.box('neck', (-1.7, 23.6, -1.7), (1.7, 24 + NECK + 0.4, 1.7), 'skin', skin=True)
    for f in ('north', 'south', 'east', 'west'):
        c.uv[f] = (9, 15, 6, 1)
    m.bone('head', 'neck', (0, 24 + NECK, 0))
    H0 = 24 + NECK
    # череп (строки лица 0–4) и челюсть (5–7); шарнир челюсти сзади-снизу
    m.bone('skull', 'head', (0, H0 + 3, 4))
    sbox('skull', (-4, H0 + 3, -4), (4, H0 + 8, 4), 'head', rows=(0, 5))
    sbox('skull', (-4, H0 + 3, -4), (4, H0 + 8, 4), 'hat', 0.5, rows=(0, 5))
    m.box('skull', (-3.6, H0 + 2.6, -3.7), (3.6, H0 + 3.0, 3.4), 'gum', hide=('up',))           # нёбо
    m.box('skull', (-4.0, H0 + 3.0, -4.6), (4.0, H0 + 8.0, -4.55), 'grin', hide=('south', 'east', 'west', 'up', 'down'))
    m.bone('jaw', 'head', (0, H0 + 3, 3.5))
    sbox('jaw', (-4, H0, -4), (4, H0 + 3, 4), 'head', rows=(5, 8))
    sbox('jaw', (-4, H0, -4), (4, H0 + 3, 4), 'hat', 0.5, rows=(5, 8))
    m.box('jaw', (-3.6, H0 + 3.0, -3.7), (3.6, H0 + 3.4, 3.4), 'gum', hide=('down',))
    m.box('jaw', (-4.0, H0, -4.6), (4.0, H0 + 3.0, -4.55), 'grin', hide=('south', 'east', 'west', 'up', 'down'))
    m.cbox('jaw', (0, H0 + 3.6, -0.6), (3.0, 0.6, 5.0), 'flesh')                                 # язык
    m.cbox('head', (0, H0 + 2.9, 2.0), (4.0, 3.6, 2.6), 'mthroat')                                # глотка
    # зубы: длинные, неровные, в два ряда (видны только когда пасть раскрыта)
    rng = random.Random(9)
    for k in range(14):
        a = -1.25 + 2.5 * k / 13
        x, z = math.sin(a) * 3.5, -math.cos(a) * 3.4
        m.rod('skull', (x, H0 + 3.1, z), (x * 0.95, H0 + 3.1 - rng.uniform(1.6, 2.6), z * 0.95), 0.55, 0.45, 'teeth', root='up')
        m.rod('jaw', (x, H0 + 2.9, z + 0.2), (x * 0.95, H0 + 2.9 + rng.uniform(1.2, 2.2), z * 0.95 + 0.2), 0.5, 0.45, 'teeth', root='down')
    drip(m, 'jaw', 'drip_lip', (1.4, H0 + 0.1, -4.2), 1.8, 0.35)
    for side, sn, part, sleeve in ((1, 'r', 'rarm', 'rsleeve'), (-1, 'l', 'larm', 'lsleeve')):
        x0 = 4 if side > 0 else -4 - aw
        m.bone('arm_' + sn, 'body', (side * (4 + aw / 2 - 1), 22, 0))
        sbox('arm_' + sn, (x0, 12, -2), (x0 + aw, 24, 2), part, w=aw)
        sbox('arm_' + sn, (x0, 12, -2), (x0 + aw, 24, 2), sleeve, 0.25, w=aw)
    for side, sn, part, pants in ((1, 'r', 'rleg', 'rpants'), (-1, 'l', 'lleg', 'lpants')):
        x0 = -0.1 if side > 0 else -3.9
        m.bone('leg_' + sn, 'body', (side * 1.9, 12, 0))
        sbox('leg_' + sn, (x0, 0, -2), (x0 + 4, 12, 2), part)
        sbox('leg_' + sn, (x0, 0, -2), (x0 + 4, 12, 2), pants, 0.25)
    return m


def preview_skin():
    """Пробный скин для превью (не для мода): тёмная куртка, бледное лицо, короткие волосы."""
    rng = np.random.default_rng(5)
    im = np.zeros((64, 64, 4), np.uint8)

    def fill(x, y, w, h, col, noise=10):
        c = np.array(col, float)
        im[y:y + h, x:x + w, :3] = np.clip(c + rng.normal(0, noise, (h, w, 3)), 0, 255)
        im[y:y + h, x:x + w, 3] = 255
    for part, col in (('head', (196, 160, 136)), ('body', (52, 58, 78)), ('rarm', (52, 58, 78)), ('larm', (52, 58, 78)),
                      ('rleg', (40, 38, 46)), ('lleg', (40, 38, 46))):
        u, v, w, h, d = SKIN[part]
        fill(u + d, v, w * 2, d, col)
        fill(u, v + d, 2 * (w + d), h, col)
    u, v = 0, 0
    fill(8, 0, 8, 8, (60, 40, 30))                         # волосы сверху
    fill(0, 8, 32, 2, (60, 40, 30))
    fill(24, 8, 8, 8, (60, 40, 30))
    for x in (9, 13):
        fill(x, 12, 2, 1, (240, 240, 240), 2)
        fill(x + 1, 12, 1, 1, (40, 60, 90), 2)
    fill(11, 14, 2, 1, (150, 100, 90), 4)
    fill(10, 15, 4, 1, (120, 70, 70), 4)
    for part in ('rarm', 'larm'):                          # кисти
        u, v, w, h, d = SKIN[part]
        fill(u, v + d + 10, 2 * (w + d), 2, (196, 160, 136))
    return Image.fromarray(im, 'RGBA')


def mimic_anims(m):
    an = []
    mid = m.name

    def idle(t):
        o = drip_keys(m, t)
        br = math.sin(t * TAU / per(4.0))
        tilt = 0 if t < 2.0 else math.sin(min(1, (t - 2.0) / 1.2) * math.pi) * 34      # голова клонится слишком далеко — и обратно
        o.update({'body': {'rot': [br * 0.8, 0, 0]}, 'arm_r': {'rot': [0, 0, 2 + br * 1.5]}, 'arm_l': {'rot': [0, 0, -2 - br * 1.5]},
                  'head': {'rot': [0, 0, tilt]}, 'neck': {'rot': [0, 0, tilt * 0.3]}, 'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.%s.idle' % mid, 4.0)
    a.sample(idle)
    an.append(a)

    def walk(t):
        ph = t / 1.0 * TAU
        s = math.sin(ph)
        o = drip_keys(m, t)
        o.update({'leg_r': {'rot': [s * 30, 0, 0]}, 'leg_l': {'rot': [-s * 30, 0, 0]}, 'arm_r': {'rot': [-s * 28, 0, 2]},
                  'arm_l': {'rot': [s * 28, 0, -2]}, 'head': {'rot': [0, 0, math.sin(ph * 0.5) * 3]}, 'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.%s.walk' % mid, 1.0)
    a.sample(walk, 0.04)
    an.append(a)

    def call(t):
        # «зовёт голосом»: поднимает руку, машет, голова наклоняется набок на 50° (слишком сильно)
        o = drip_keys(m, t)
        k = min(1, t / 0.4) if t < 2.2 else max(0, 1 - (t - 2.2) / 0.3)
        wave = math.sin(t * TAU * 1.5) * 18 * k
        o.update({'arm_r': {'rot': [150 * k, 0, 20 * k + wave]}, 'head': {'rot': [4 * k, 0, 50 * k]}, 'neck': {'rot': [0, 0, 16 * k]},
                  'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.%s.call' % mid, 2.5, loop=False)
    a.sample(call, 0.025)
    a.instruction(0.3, 'voice')
    an.append(a)

    def reveal(t):
        # вблизи лицо раскрывается пастью: голова запрокидывается, челюсть отваливается до груди, шея вытягивается
        o = drip_keys(m, t, period=0.7, amp=1.6)
        k = min(1, t / 0.7)
        e = k * k * (3 - 2 * k)
        sh = math.sin(t * 50) * (k > 0.6) * 1.5
        o.update({'skull': {'rot': [34 * e, 0, sh]}, 'jaw': {'rot': [-70 * e, 0, -sh]}, 'neck': {'scale': [1, 1 + 0.5 * e, 1]},
                  'head': {'pos': [0, 1.6 * e, 0], 'rot': [0, 0, 0]}, 'arm_r': {'rot': [30 * e, 0, 14 * e]}, 'arm_l': {'rot': [30 * e, 0, -14 * e]},
                  'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.%s.reveal' % mid, 1.0, loop='hold')
    a.sample(reveal, 0.025)
    an.append(a)

    def attack(t):
        # из раскрытой пасти: бросок головой, укус на 0.4, руки хватают
        o = drip_keys(m, t)
        bite = 1 - min(1, max(0, (t - 0.32) / 0.08)) + max(0, (t - 0.55) / 0.3)
        bite = min(1, bite)
        lunge = math.sin(min(1, t / 0.5) * math.pi)
        o.update({'skull': {'rot': [34 * bite - 10 * lunge, 0, 0]}, 'jaw': {'rot': [-70 * bite, 0, 0]}, 'neck': {'scale': [1, 1.5, 1]},
                  'head': {'pos': [0, 1.6, -3.0 * lunge]}, 'body': {'rot': [-18 * lunge, 0, 0]},
                  'arm_r': {'rot': [80 * lunge + 20, 0, 10]}, 'arm_l': {'rot': [80 * lunge + 20, 0, -10]}, 'pool': {'scale': [0, 0, 0]}})
        return o
    a = Anim('animation.%s.attack' % mid, 0.9, loop=False)
    a.sample(attack, 0.025)
    a.instruction(0.4, 'hit')
    an.append(a)
    an += rise_sink(m, mid, 36)
    return an


# ================================================================== запись / сборка
OUT_GEO = os.path.join(A, 'geo', 'entity')
OUT_TEX = os.path.join(A, 'textures', 'entity', 'nightmare')
OUT_ANIM = os.path.join(A, 'animations', 'entity')

BEASTS = {}
ORDER = []
META = {}


CACHE = os.path.join(HERE, '.cache')


def beast(fn_build, fn_anims):
    def run():
        m = fn_build()
        m.pack()
        m.paint()
        anims = fn_anims(m)
        name = m.name
        tex = META.get(name, {}).get('texture', name)
        write_json(os.path.join(OUT_GEO, name + '.geo.json'), m.geo_json(), compact=True)
        WRITTEN.append('geo/entity/%s.geo.json' % name)
        os.makedirs(OUT_TEX, exist_ok=True)
        m.image.save(os.path.join(OUT_TEX, tex + '.png'), optimize=True)
        WRITTEN.append('textures/entity/nightmare/%s.png' % tex)
        if m.glow is not None:
            m.glow.save(os.path.join(OUT_TEX, tex + '_glowmask.png'), optimize=True)
            WRITTEN.append('textures/entity/nightmare/%s_glowmask.png' % tex)
        if name.startswith('nm_mimic'):                    # превью: пробный скин в левой половине атласа (в мод не пишется)
            os.makedirs(CACHE, exist_ok=True)
            comp = m.image.copy()
            comp.paste(preview_skin().resize((64 * m.density, 64 * m.density), Image.NEAREST), (0, 0))
            path = os.path.join(CACHE, name + '_preview.png')
            comp.save(path)
            META[name]['preview_texture'] = path
        if not META.get(name, {}).get('anims'):
            write_json(os.path.join(OUT_ANIM, name + '.animation.json'),
                       {'format_version': '1.8.0', 'animations': {a.name: a.to_json() for a in anims}}, compact=True)
            WRITTEN.append('animations/entity/%s.animation.json' % name)
        ncubes = sum(len(b.cubes) for b in m.bones.values())
        print('%-16s bones %3d  cubes %4d  tex %s  anims %s' % (name, len(m.bones), ncubes, m.tex_px, ', '.join(a.name.split('.')[-1] for a in anims)))
        return m, anims
    return run


BEASTS['nm_lurker'] = beast(build_lurker, lurker_anims)
META['nm_lurker'] = {'title': 'Тень-за-углом (nm_lurker)', 'height': 46,
                     'desc': 'Стадия 1+. Вытянутый чёрный силуэт без лица, рост 2.4, руки до земли. Стоит на краю зрения; посмотрели прямо — '
                             'dissolve; спиной 3 с — lunge и удар.'}



BEASTS['nm_crawler'] = beast(build_crawler, crawler_anims)
META['nm_crawler'] = {'title': 'Ползун (nm_crawler)', 'height': 30,
                      'desc': 'Стадия 2+. Человек на четвереньках, локти и колени вывернуты вверх, вместо лица — гладкая кожа с трещиной-ртом '
                              '(голова раскрывается на две половины). Ползает по стенам/потолку (код переворачивает модель), pounce — прыжок.'}
BEASTS['nm_mimic'] = beast(lambda: build_mimic(False), mimic_anims)
BEASTS['nm_mimic_slim'] = beast(lambda: build_mimic(True), mimic_anims)
META['nm_mimic'] = {'title': 'Мимик (nm_mimic)', 'height': 42, 'texture': 'nm_mimic_template',
                    'desc': 'Стадия 2+. Копия игрока сервера: скин игрока (код копирует в левую половину атласа 128×64), шея на 3 длиннее, '
                            'улыбка от уха до уха. call — зовёт; reveal — лицо раскрывается пастью; attack — укус.'}
META['nm_mimic_slim'] = dict(META['nm_mimic'], title='Мимик, тонкие руки (nm_mimic_slim)', anims='nm_mimic')
BEASTS['nm_hollow_child'] = beast(build_child, child_anims)
META['nm_hollow_child'] = {'title': 'Пустой ребёнок (nm_hollow_child)', 'height': 19,
                           'desc': 'Стадия 2+. Маленькая фигура в ночной рубашке, вместо глаз — дыры (в глубине тлеет искра), чернильные слёзы, '
                                   'тихий смех (laugh). На подходе — vanish и appear за спиной.'}
BEASTS['nm_hands'] = beast(build_hands, hands_anims)
META['nm_hands'] = {'title': 'Руки из земли (nm_hands)', 'height': 30,
                    'desc': 'Стадия 3. Кластер из 16 бледных рук из лужи чернил. grab — хватают за ноги (удержание 1.5 с).'}
BEASTS['nm_maw'] = beast(build_maw, maw_anims)
META['nm_maw'] = {'title': 'Пасть (nm_maw)', 'height': 66,
                  'desc': 'Стадия 3. Огромная челюсть-туловище на четырёх тонких ногах-ходулях, рост 4. roar — рёв (экран дрожит), attack — укус-таран.'}
BEASTS['nm_weeper'] = beast(build_weeper, weeper_anims)
META['nm_weeper'] = {'title': 'Плакальщица (nm_weeper)', 'height': 44,
                     'desc': 'Стадия 3. Высокая женщина в чёрной вуали, по лицу текут чернила. idle — плачет (усиливает кошмары), '
                             'flee — убегает от взгляда, wail — вопль.'}
BEASTS['nm_moth'] = beast(build_moth, moth_anims)
META['nm_moth'] = {'title': 'Мотыльки-глаза (nm_moth)', 'height': 34,
                   'desc': 'Стадия 1+. Рой из 12 мотыльков с глазами на крыльях. attack — рой стягивается перед лицом (код добавляет '
                           'экранную накладку nightmare_moths_screen).'}
BEASTS['nm_dread'] = beast(build_dread, dread_anims)
META['nm_dread'] = {'title': 'Ужас (nm_dread)', 'height': 56,
                    'desc': 'Только мифическое: так жертва видит самого заклинателя. Фарфоровая маска куклы с чернильными слезами, '
                            'венец из гребёнки музыкальной шкатулки, четыре руки, балахон стекает щупальцами.'}

ORDER[:] = list(BEASTS)


def main(only=None):
    out = {}
    for k, fn in BEASTS.items():
        if only and k not in only:
            continue
        out[k] = fn()
    return out


if __name__ == '__main__':
    only = None
    if '--only' in sys.argv:
        only = sys.argv[sys.argv.index('--only') + 1].split(',')
    main(only)
