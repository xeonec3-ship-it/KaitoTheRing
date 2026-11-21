#!/usr/bin/env python3
"""
T35 (визуал, часть A) — броня с боссов: «Наряд Ревности» (Ирина, `jealous`), «Латы Кузнеца» (Арис, `smith`) и
«Накидка Главы Культа» (`cult_mantle`, носится поверх любой брони). ТЗ: docs/specs/tasks/T35_boss_armor_sets.md.

Эталон (docs/inbox/README.md «Эталон моделей»): стиль Iron's/ванили, текстура ×4 (атлас 128 ед. → 512 px), ручная пиксельная
светотень. Материалы — те же, что у боссов: tools/gen_irina.py (ткань, шляпа, капюшон, ленты, нити) и tools/gen_aris.py (сталь,
бирюзовая кайма, рога, белые камни, кольчуга) — поэтому броня узнаётся рядом с боссом. Накидка — по плащу Главы Культа
(tools/gen_cult_leader.py: багровая ткань, тёмный знак культа на спине, тлеющие искры по рваному подолу).

Кости — под скелет игрока, как у брони безмолвной ведьмы (geo/armor/silent_witch_armor.geo.json, GeoArmorRenderer GeckoLib 4):
  bipedHead/armorHead (0,24,0) · bipedBody/armorBody (0,24,0) · bipedRightArm/armorRightArm (−5,22,0) · bipedLeftArm/armorLeftArm (5,22,0)
  bipedRightLeg/armorRightLeg + armorRightBoot (−1.9,12,0) · bipedLeftLeg/armorLeftLeg + armorLeftBoot (1.9,12,0)   [оси geo-файла]
Слоты GeckoLib: шлем — armorHead, нагрудник — armorBody + руки, поножи — armorRight/LeftLeg, ботинки — armorRight/LeftBoot.
Ткань/ленты/плащ — свои кости-дети этих костей, качаются анимациями idle / walk / run / cast (как у ведьмы: OutfitAnim.pick).
Правило без проходов: всё, что висит на теле (не на ноге), в walk/run заранее уведено назад на угол, при котором его не задевает
нога на ванильном шаге (размах до ±69° при ходьбе, до ±80° при беге) — проверка clearance() ниже печатает запас; качание — только
в сторону «от тела» (смещение на свою амплитуду). Знаки поворотов анимаций — оси Blockbench (свисающая ткань назад — x плюс),
перевод во внутренние оси nightmare_geo — gen_irina.bb() (один раз; см. «двойной переворот» 20.11).

Пишет (src/main/resources/assets/pohsmp_core/):
  geo/armor/{jealous,smith,cult_mantle}.geo.json
  textures/armor/{jealous,smith,cult_mantle}.png + _glowmask.png (красные нити / бирюза и глаза / тлеющие искры)
  animations/armor/{jealous,smith,cult_mantle}.animation.json  (idle, walk, run, cast)
  textures/item/{jealous,smith}_{helmet,chestplate,leggings,boots}.png, cult_mantle.png (32×32; models/item/*.json — у программиста)
Запуск: python3 tools/gen_t35_armor_a.py [--shots] [--video] [--lang (свои строки поверх — по умолчанию не пишутся)]   (кадры/видео — tools/t35_armor_render.py)
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nightmare_geo import Anim, hex2, mix, fbm, face_size, euler, to_euler, write_json, TAU  # noqa: E402
import gen_irina as GI  # noqa: E402
import gen_aris as GA  # noqa: E402

A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
WRITTEN = []
K4 = 4


# ================================================================== скелет игрока (внутренние оси: +x — правая сторона носящего, перед — −z)
def skeleton(m):
    m.bone('bipedHead', None, (0, 24, 0))
    m.bone('armorHead', 'bipedHead', (0, 24, 0))
    m.bone('bipedBody', None, (0, 24, 0))
    m.bone('armorBody', 'bipedBody', (0, 24, 0))
    m.bone('bipedRightArm', None, (5, 22, 0))
    m.bone('armorRightArm', 'bipedRightArm', (5, 22, 0))
    m.bone('bipedLeftArm', None, (-5, 22, 0))
    m.bone('armorLeftArm', 'bipedLeftArm', (-5, 22, 0))
    m.bone('bipedRightLeg', None, (1.9, 12, 0))
    m.bone('armorRightLeg', 'bipedRightLeg', (1.9, 12, 0))
    m.bone('armorRightBoot', 'bipedRightLeg', (1.9, 12, 0))
    m.bone('bipedLeftLeg', None, (-1.9, 12, 0))
    m.bone('armorLeftLeg', 'bipedLeftLeg', (-1.9, 12, 0))
    m.bone('armorLeftBoot', 'bipedLeftLeg', (-1.9, 12, 0))


def X(sx, a, b):
    return tuple(sorted((sx * a, sx * b)))


SIDES = ((1, 'r', 'Right'), (-1, 'l', 'Left'))


def strip(m, bone, p, q, w, d, mat, wdir=(1, 0, 0), ext=0.0, **kw):
    """Лента/полоса от p к q: ширина w — вдоль wdir (ортогонализуется к оси ленты), толщина d. В отличие от Model.rod ширина не
    скручивается, когда лента смотрит вниз."""
    p, q = np.asarray(p, float), np.asarray(q, float)
    yv = q - p
    L = float(np.linalg.norm(yv)) + 2 * ext
    yv = yv / np.linalg.norm(yv)
    xv = np.asarray(wdir, float)
    xv = xv - xv.dot(yv) * yv
    xv = xv / np.linalg.norm(xv)
    zv = np.cross(xv, yv)
    R = np.stack([xv, yv, zv], 1)
    mid = (p + q) / 2
    rot = to_euler(R)
    if max(abs(v) for v in rot) < 1e-6:
        rot = None
    return m.box(bone, mid - [w / 2, L / 2, d / 2], mid + [w / 2, L / 2, d / 2], mat, rot=rot, pivot=list(mid), **kw)


class PModel(GA.PixelModel):
    """Покраска попиксельно (ctx.i/j/nw/nh, как у Арис) — материалам Ирины это не мешает (их glow = None → нули)."""

    def paint(self, base_img=None):
        raw = self.materials

        def wrap(fn):
            def w(ctx):
                c, a, g = fn(ctx)
                if g is None:
                    g = np.zeros((ctx.n, 3))
                g = np.broadcast_to(np.asarray(g, float), (ctx.n, 3)) if np.ndim(g) < 2 else np.asarray(g, float)
                return c, a, g
            return w
        self.materials = {k: wrap(f) for k, f in raw.items()}
        try:
            return super().paint(base_img)
        finally:
            self.materials = raw


# ================================================================== «Наряд Ревности» (Ирина)
T_DLIL = [hex2('#A585CF'), hex2('#7E5EB0'), hex2('#604392'), hex2('#41296A')]      # тёмно-лиловое платье (тон Ирины, на ступень глубже)
T_DLIL2 = [hex2('#8A6ABA'), hex2('#674896'), hex2('#4C3278'), hex2('#321C54')]
T_PLATE = [hex2('#8E8A9A'), hex2('#6E6A7C'), hex2('#555162'), hex2('#3A3746')]      # сталь корсета — серо-лиловая, как шляпа Ирины


def mat_dress(ctx):
    info = ctx.cube.info
    tones = T_DLIL2 if info.get('deep') else T_DLIL
    c = GI.shade(ctx, tones, fold_step=3, blotch=0.6, seed=13, tex='twill')
    if info.get('cuff') and ctx.face not in ('up', 'down'):
        yy = np.floor(ctx.P[:, 1] + 64).astype(int)
        band = (yy % 4 == 0)
        c = np.where(band[:, None], GI.shade(ctx, T_DLIL2, fold_step=3, blotch=0.5, seed=14), c)
    if info.get('cuff') and ctx.face == 'down':
        e = GI.edge_dist(ctx)
        c = np.where((e < 0.6)[:, None], GI.pick(T_DLIL, np.full(ctx.n, 3)), GI.pick(GI.VOID, np.full(ctx.n, 0)))
    c = GI.trims(ctx, c, info, tones, GI.T_LIL)
    glow = None
    if info.get('threadband') and ctx.face not in ('up', 'down'):
        # красная нить, намотанная по спирали (как нити Ирины): светится
        _, _, q = GI.pxy(ctx)
        u = np.where(np.abs(ctx.N[:, 0]) > 0.5, q[:, 2], q[:, 0])
        on = ((q[:, 1] + u // 2) % 9 == 0)
        c = np.where(on[:, None], GI.pick(GI.T_RED, np.full(ctx.n, 0)), c)
        glow = np.where(on[:, None], GI.pick(GI.T_RED, np.full(ctx.n, 0)) * 0.8, 0)
    return c, 1.0, glow


def mat_plate_i(ctx):
    """Сталь корсета/наплечий: пиксельная светотень без складок, светлая фаска сверху, золотая кайма по краю, заклёпки."""
    c = GI.shade(ctx, T_PLATE, folds=False, blotch=0.5, seed=21)
    info = ctx.cube.info
    if ctx.face not in ('up', 'down'):
        r0, r1, c0, c1, w, h = GI.rows(ctx)
        e = GI.edge_dist(ctx)
        c = np.where(((e < 0.5) & (e >= 0.25))[:, None], GI.pick(GI.T_GOLD, np.full(ctx.n, 2)), c)
        if info.get('rivets'):
            pc, pr, q = GI.pxy(ctx)
            W, H = int(round(w * K4)), int(round(h * K4))
            riv = ((pc == 3) | (pc == W - 4)) & ((pr % 6) == 3)
            c = np.where(riv[:, None], GI.pick(GI.T_GOLD, np.full(ctx.n, 0)), c)
    return c, 1.0, None


def hood_open(L):
    """Проём капюшона-шлема (лицо игрока видно): стрельчатая арка над глазами, снизу открыто."""
    x, y = L[:, 0], L[:, 1]
    k = np.clip((y - 29.4) / 2.5, 0, 1)
    half = 3.35 * np.sqrt(np.clip(1 - k * k, 0, 1))
    return (np.abs(x) < half) & (y < 31.9)


def mat_hood_a(ctx):
    info = ctx.cube.info
    c, a, g = GI.mat_hood(ctx) if not info.get('shell') else (GI.shade(ctx, GI.T_BLU, fold_step=3, blotch=0.7, seed=2, tex='twill'), 1.0, None)
    if info.get('shell'):
        c = GI.trims(ctx, c, {'seam': True}, GI.T_BLU, GI.T_BLU)
        r0, r1, c0, c1, w, h = GI.rows(ctx)
        if ctx.face in ('south', 'east', 'west'):
            c = np.where((r0 <= 1)[:, None], GI.pick(GI.T_BLU, np.full(ctx.n, 3)), c)          # тень под полями шляпы
            c = np.where((r1 == 0)[:, None], GI.pick(GI.T_BLU, np.full(ctx.n, 3)), c)
            c = np.where((r1 == 1)[:, None], GI.pick(GI.T_BLU, np.full(ctx.n, 0)), c)
        if ctx.face == 'north':
            hole = hood_open(ctx.L)
            a = (~hole).astype(float)
            ring = (~hole) & hood_open(np.stack([ctx.L[:, 0] / 1.25, ctx.L[:, 1] - 0.75, ctx.L[:, 2]], 1))
            c = np.where(ring[:, None], GI.pick(GI.T_BLU, np.full(ctx.n, 0)), c)
        elif ctx.face == 'down':
            a = 0.0
    return c, a, g


def build_jealous():
    m = PModel('jealous', density=4, tex_w=128)
    m.materials.update(hat=GI.mat_hat, cross=GI.mat_cross, hood=mat_hood_a, lilac=GI.mat_lilac, gg=GI.mat_gg, boot=GI.mat_boot,
                       ribbon=GI.mat_ribbon, thread=GI.mat_thread, gold=GI.mat_gold, dark=GI.mat_dark, dress=mat_dress, plate=mat_plate_i)
    skeleton(m)
    H, B = 'armorHead', 'armorBody'
    # ---------------- шлем: капюшон Ирины (синий, открытое лицо) + её шляпа с крестом, лентами и кольцом красной нити
    m.box(H, (-4.9, 24.1, -4.75), (4.9, 32.9, 4.85), 'hood', shell=True)
    m.box(H, (-3.6, 32.8, -3.6), (3.6, 33.6, 4.2), 'hood')
    m.bone('hat', H, (0, 33.6, 0), rot=(-6, 0, 8))
    m.bone('hat_brim', 'hat', (0, 33.6, 0))
    m.cbox('hat_brim', (0, 34.3, 0), (15.6, 1.6, 15.6), 'hat', brim=True)
    for k in range(4):                                                              # свисающие края полей (как у Ирины)
        a = TAU * k / 4
        cx, cz = math.sin(a) * 9.3, -math.cos(a) * 9.3
        m.cbox('hat_brim', (cx, 33.8, cz), ((19.8, 1.6, 3.4) if k % 2 == 0 else (3.4, 1.6, 19.8)), 'hat', brim=True,
               rot=((13 if k == 0 else -13 if k == 2 else 0), 0, (13 if k == 3 else -13 if k == 1 else 0)), pivot=[cx * 0.85, 34.2, cz * 0.85])
    m.bone('hat_crown', 'hat', (0, 35.1, 0), rot=(0, 0, 5))
    m.cbox('hat_crown', (0, 36.4, 0), (9.0, 2.6, 9.0), 'hat', band=True)
    m.cbox('hat_crown', (0.3, 39.1, 0), (8.3, 2.8, 8.3), 'hat')
    m.cbox('hat_crown', (0.5, 41.3, 0), (8.5, 1.6, 8.5), 'hat', band=True)
    m.bone('hat_tip', 'hat_crown', (0.5, 42.1, 0), rot=(-8, 0, -16))
    m.cbox('hat_tip', (0.5, 45.2, 0.3), (7.5, 6.2, 7.5), 'hat')
    m.box('hat_tip', (-0.1, 42.6, -3.6), (1.2, 48.4, -3.2), 'cross')               # крест Ирины
    m.box('hat_tip', (-1.5, 45.7, -3.6), (2.6, 46.9, -3.2), 'cross')
    m.box('hat_tip', (4.25, 44.0, -1.6), (4.4, 45.0, 2.0), 'dark')
    m.bone('hat_tip2', 'hat_tip', (0.7, 48.3, 0.6), rot=(-12, 0, -14))
    m.cbox('hat_tip2', (0.9, 49.4, 0.6), (5.4, 2.3, 5.4), 'hat')
    m.bone('hat_tip3', 'hat_tip2', (1.1, 50.5, 0.8), rot=(-10, 0, -20))
    m.cbox('hat_tip3', (1.3, 51.1, 0.8), (3.2, 1.4, 3.2), 'hat')
    # ленты шляпы: две лиловые, с ленты тульи сзади на затылок (заканчиваются выше плеч — не ложатся на спину при взгляде вверх)
    for sx, sn in ((1, 'r'), (-1, 'l')):
        p0 = np.array([sx * 2.2, 36.0, 4.7])
        p1 = np.array([sx * 3.0, 31.6, 6.1])
        p2 = np.array([sx * 3.6, 27.4, 6.6])
        m.bone('hat_rib_' + sn, 'hat_crown', p0)
        strip(m, 'hat_rib_' + sn, p0, p1, 2.2, 0.5, 'ribbon', kind='lil_l', ext=0.1)
        m.bone('hat_rib_%s_b' % sn, 'hat_rib_' + sn, p1)
        strip(m, 'hat_rib_%s_b' % sn, p1, p2, 2.0, 0.5, 'ribbon', kind='lil_l', tip=True)
    # кольцо красной нити вокруг тульи — медленно вращается (знак Ирины)
    m.bone('hat_thread', 'hat_crown', (0.3, 38.6, 0))
    n = 26
    pts = []
    for i in range(n + 1):
        ang = TAU * i / n
        pts.append(np.array([0.3 + math.cos(ang) * 7.2, 38.6 + 0.9 * math.sin(ang * 2), math.sin(ang) * 7.2]))
    for i in range(n):
        if i % 7 in (3,):
            continue
        m.rod('hat_thread', pts[i], pts[i + 1], 0.7, 0.7, 'thread', ext=0.05)

    # ---------------- нагрудник: платье-доспех, корсет из пластин, капюшон-воротник, брошь, бант и ленты на спине
    m.box(B, (-4.6, 12.3, -2.6), (4.6, 24.3, 2.6), 'dress', seam=True)
    m.box(B, (-4.85, 12.2, -2.85), (4.85, 14.2, 2.85), 'lilac', trim=True)               # кушак
    for i, (y0, w) in enumerate(((19.9, 8.4), (17.6, 7.8), (15.3, 7.2))):                # корсет: пластины внахлёст
        m.box(B, (-w / 2, y0, -3.05 + i * 0.1), (w / 2, y0 + 2.4, -2.55), 'plate', rivets=True)
    m.box(B, (-1.6, 15.3, 2.55), (1.6, 21.0, 3.0), 'plate')                                # пластина спины
    m.box(B, (-5.3, 22.5, -3.35), (5.3, 24.75, 3.45), 'hood', hem=True)                  # капюшон спадает на плечи
    m.box(B, (-4.8, 21.4, 2.9), (4.8, 22.6, 3.4), 'hood')
    m.cbox(B, (0, 22.5, -3.6), (1.6, 1.6, 0.5), 'gold')                                   # брошь
    m.cbox(B, (0, 22.5, -3.95), (0.8, 0.8, 0.3), 'thread')
    m.box(B, (-1.3, 14.6, 2.85), (1.3, 17.0, 3.8), 'lilac', trim=True)                    # бант на спине (выше бедра на шаге)
    for s in (1, -1):
        m.cbox(B, (s * 2.1, 15.8, 3.3), (1.6, 1.6, 0.8), 'lilac', trim=True)
    for s, nm in ((1, 'r'), (-1, 'l')):
        p0 = np.array([s * 0.9, 22.0, -3.6])
        p1 = np.array([s * 1.6, 16.6, -3.65])                                              # короткие завязки — выше бёдер
        m.bone('tie_' + nm, B, p0)
        strip(m, 'tie_' + nm, p0, p1, 1.8, 0.5, 'ribbon', kind='lil_l', tip=True)
    # красные нити на платье: два витка по талии (светятся)
    m.box(B, (-4.75, 18.85, -2.75), (4.75, 19.15, 2.75), 'thread')
    m.box(B, (-4.75, 14.4, -2.95), (4.75, 14.7, 2.95), 'thread')

    # руки: рукав от плеча (лиловый), наплечник-капелет Ирины (серо-зелёный) с лентами, раструб (качается), красная нить
    for sx, sn, side in SIDES:
        arm = 'armor%sArm' % side
        x0, x1 = X(sx, 3.45, 8.55)
        m.box(arm, (x0, 14.6, -2.55), (x1, 24.4, 2.55), 'dress', threadband=True)
        x0, x1 = X(sx, 3.2, 8.95)
        m.box(arm, (x0, 21.2, -3.05), (x1, 24.9, 3.05), 'gg', hem=True)                   # капелет на плече
        x0, x1 = X(sx, 3.6, 8.6)
        m.box(arm, (x0, 24.9, -2.6), (x1, 25.5, 2.6), 'gg', trim=True)
        for k, (zc, kind) in enumerate(((-2.0, 'lil_l'), (0.0, 'gg'), (2.0, 'lil_l'))):   # лоскуты капелета снаружи плеча
            p0 = np.array([sx * 9.05, 22.6, zc])
            p1 = np.array([sx * 9.45, 17.6 - 0.6 * (k == 1), zc])
            bn = 'cap_%s%d' % (sn, k)
            m.bone(bn, arm, p0)
            strip(m, bn, p0, p1, 1.9, 0.5, 'ribbon', wdir=(0, 0, 1), kind=kind, tip=True)
        sl = 'sleeve_' + sn
        m.bone(sl, arm, (sx * 6.6, 15.0, 0))
        x0, x1 = X(sx, 5.0, 9.6)
        m.box(sl, (x0, 11.4, -3.2), (x1, 15.4, 3.2), 'dress', cuff=True, hem=True)        # раструб (только наружу от бедра)

    # ---------------- поножи: юбка из лент Ирины — каждая лента на своей ноге (на шаге лента идёт с ногой, сквозь ногу не проходит)
    for sx, sn, side in SIDES:
        leg = 'armor%sLeg' % side
        x0, x1 = X(sx, -0.55, 4.45)
        m.box(leg, (x0, 3.6, -2.55), (x1, 12.3, 2.55), 'boot')                           # чулки (тёмные, как сапоги Ирины)
        x0, x1 = X(sx, -0.7, 4.7)
        m.box(leg, (x0, 8.4, -2.9), (x1, 12.4, 2.9), 'gg', hem=True)                      # верхний ярус юбки (серо-зелёный)
        for k in range(8):
            a = math.radians(20 + 140 * k / 7)                                            # от переда (20°) к спине (160°), x ≥ 2
            front = math.cos(a)
            top = np.array([sx * math.sin(a) * 4.55, 11.9, -front * 3.4])
            rad = 6.0 + 0.4 * (k % 2)
            end_y = 1.6 + 1.2 * max(0.0, front) ** 2 + (k % 3 - 1) * 0.7
            bot = np.array([sx * math.sin(a) * rad, end_y, -front * rad * 0.72])
            mid = top + (bot - top) * 0.5
            w = 3.0 + 0.3 * (k % 2)
            kind = ('lil_l', 'gg')[k % 2]
            bn = 'rib_%s%d' % (sn, k)
            m.bone(bn, leg, top)
            strip(m, bn, top, mid, w, 0.55, 'ribbon', wdir=(sx * math.cos(a), 0, math.sin(a)), kind=kind, ext=0.1)
            m.bone(bn + '_b', bn, mid)
            strip(m, bn + '_b', mid, bot, w * 0.95, 0.55, 'ribbon', wdir=(sx * math.cos(a), 0, math.sin(a)), kind=kind, tip=True)
        # ботинки Ирины: тёмные, лиловый отворот
        bt = 'armor%sBoot' % side
        x0, x1 = X(sx, -0.75, 4.55)
        m.box(bt, (x0, -0.05, -3.0), (x1, 4.2, 2.7), 'boot')
        x0, x1 = X(sx, -0.95, 4.75)
        m.box(bt, (x0, 3.6, -3.2), (x1, 4.9, 2.9), 'boot', cuff=True)
        x0, x1 = X(sx, 0.4, 3.4)
        m.box(bt, (x0, -0.05, -3.9), (x1, 1.6, -2.9), 'boot')
        m.cbox(bt, (sx * 1.9, 4.25, -3.35), (1.0, 1.0, 0.4), 'thread')                    # красный узелок нити на отвороте
    return m


# ================================================================== «Латы Кузнеца» (Арис)
def build_smith():
    m = PModel('smith', density=4, tex_w=128)
    m.materials = dict(GA.MATS)
    GA.V['variant'] = 'base'
    skeleton(m)
    H, B = 'armorHead', 'armorBody'
    # ---------------- шлем: закрытый, забрало со щелями, прорезь с бирюзовыми глазами, гребень, крылья, рога-бирюза (как у Арис)
    m.box(H, (-4.75, 23.9, -4.8), (4.75, 32.9, 4.75), 'plate_l')
    m.cbox(H, (0, 29.0, 0.2), (9.9, 4.4, 9.4), 'plate_d')                                  # обод под гребнем (объём шлема)
    m.box(H, (-4.6, 24.1, -5.05), (4.6, 27.7, -4.75), 'grille')
    m.box(H, (-3.9, 27.7, -4.95), (3.9, 28.9, -4.75), 'visor')
    m.box(H, (-4.95, 28.9, -5.3), (4.95, 30.0, -4.7), 'plate_l')                           # надбровье
    m.box(H, (-0.55, 24.0, -5.6), (0.55, 33.0, -4.9), 'plate_l')                           # гребень по лицу
    m.box(H, (-0.55, 32.8, -4.4), (0.55, 34.1, 4.0), 'plate_d')                            # гребень по темени
    m.rod(H, (0, 33.8, -3.6), (0, 36.6, -4.8), 1, mat='plate_d')                           # шип
    m.box(H, (-4.9, 23.8, -5.0), (4.9, 24.4, 4.9), 'trim')                                 # бирюзовая кайма по низу шлема
    for sx in (-1, 1):
        m.cbox(H, (sx * 5.1, 29.0, 0.6), (0.9, 4.6, 5.2), 'plate')                          # нащёчники-крылья
        m.rod(H, (sx * 4.9, 27.0, 0.9), (sx * 7.1, 32.0, 1.1), 1.6, 3.4, mat='plate_l')
        m.rod(H, (sx * 5.0, 26.2, 2.0), (sx * 7.5, 29.8, 2.9), 1.2, 2.0, mat='plate')
        pts = [(3.1, 32.4, 0.5), (4.4, 34.6, 0.5), (5.4, 37.0, 0.6), (5.8, 39.6, 0.6), (5.6, 42.2, 0.4), (5.1, 44.2, 0.2)]
        ws = [2.8, 2.6, 2.35, 2.1, 1.85]
        for i in range(len(pts) - 1):
            p, q = np.array(pts[i]) * [sx, 1, 1], np.array(pts[i + 1]) * [sx, 1, 1]
            m.rod(H, p, q, ws[i], mat='horn', ext=0.25)
        m.cbox(H, (sx * 3.1, 32.7, 0.5), (3.0, 1.4, 3.2), 'plate_l')
    m.cbox(H, (0, 30.0, 4.95), (2.2, 2.2, 0.5), 'trim')                                     # кольцо на затылке (у Арис — кольцо косы)

    # ---------------- нагрудник: кольчуга, кираса с пластинами внахлёст, пластины живота, пояс с камнем, горжет, высокий воротник
    m.box(B, (-4.4, 12.2, -2.45), (4.4, 24.2, 2.45), 'chain')
    m.box(B, (-5.0, 16.8, -3.0), (5.0, 23.6, 2.85), 'plate')
    m.box(B, (-2.2, 23.3, -3.5), (2.2, 23.8, -2.8), 'trim')
    for i, (y0, w, z) in enumerate(((21.0, 9.4, -3.55), (19.0, 8.9, -3.45), (17.2, 8.4, -3.3))):
        m.box(B, (-w / 2, y0, z), (w / 2, y0 + 2.25, -2.9), 'plate_l' if i == 0 else 'plate')
    m.box(B, (-4.0, 17.0, -3.55), (4.0, 17.5, -3.05), 'trim')
    for i, (y0, w) in enumerate(((15.6, 8.6), (14.3, 8.2))):                                # пластины живота
        m.box(B, (-w / 2, y0, -2.85 + i * 0.1), (w / 2, y0 + 1.5, 2.65), 'plate')
    for sxx in (-1, 1):
        m.rod(B, (sxx * 3.9, 17.3, -3.05), (sxx * 0.1, 14.2, -3.0), 0.5, 0.5, mat='trim', ext=0.2)
    m.box(B, (-4.75, 12.0, -3.0), (4.75, 14.3, 2.85), 'leather')                           # пояс
    m.cbox(B, (0, 13.1, -3.15), (1.6, 1.6, 0.5), 'trim')
    for sxx in (-1, 1):
        m.cbox(B, (sxx * 2.8, 13.1, -3.05), (0.8, 0.8, 0.5), 'plate_l')
    m.box(B, (-3.6, 23.0, -2.9), (3.6, 25.0, 2.7), 'plate_d')                              # горжет
    m.box(B, (-3.85, 24.25, -3.15), (3.85, 24.75, 2.95), 'trim')
    m.box(B, (-4.75, 23.4, 4.95), (4.75, 27.3, 5.65), 'plate')                             # высокий воротник за шлемом
    m.box(B, (-4.5, 23.4, 2.85), (4.5, 24.0, 4.95), 'plate_d')
    m.box(B, (-4.5, 27.05, 4.95), (4.5, 27.55, 5.75), 'trim')
    m.cbox(B, (0, 19.5, 3.05), (3.0, 7.0, 0.5), 'plate')                                    # хребет спины
    m.box(B, (-1.75, 16.0, 3.3), (1.75, 16.5, 3.5), 'trim')
    for sxx in (-1, 1):                                                                     # белые камни у ключиц
        m.cbox(B, (sxx * 3.3, 23.0, -3.4), (3.0, 3.0, 0.7), 'plate_d')
        m.cbox(B, (sxx * 3.3, 23.0, -3.9), (2.3, 2.3, 1.2), 'stone')
    for sxx, nm in ((1, 'r'), (-1, 'l')):                                                   # лиловые ленты с камней (до бёдер)
        top = np.array([sxx * 3.3, 21.9, -4.3])
        p1, p2 = np.array([sxx * 3.4, 19.0, -4.35]), np.array([sxx * 3.5, 16.0, -4.45])   # до пояса: ниже — бедро на шаге
        m.bone('ribbon_%s1' % nm, B, top)
        strip(m, 'ribbon_%s1' % nm, top, p1, 2.5, 0.5, 'ribbon', ext=0.15)
        m.bone('ribbon_%s2' % nm, 'ribbon_%s1' % nm, p1)
        strip(m, 'ribbon_%s2' % nm, p1, p2, 2.5, 0.5, 'ribbon', ext=0.15)
        m.cbox('ribbon_%s2' % nm, p2 + [0, -1.0, 0], (2.5, 2.0, 0.5), 'tassel')

    # руки: кольчуга, наплечник-веер с бирюзовой каймой и «перьями», камень-ромб, налокотник, наруч, латная перчатка
    for sx, nm, side in SIDES:
        arm = 'armor%sArm' % side
        x0, x1 = X(sx, 3.55, 8.45)
        m.box(arm, (x0, 14.0, -2.45), (x1, 23.0, 2.45), 'chain')
        x0, x1 = X(sx, 3.4, 8.6)
        m.box(arm, (x0, 17.4, -2.6), (x1, 21.0, 2.6), 'plate')
        for li, (cx, cy, w, h, d, a) in enumerate(((6.4, 23.6, 6.6, 2.8, 6.8, -14), (7.4, 21.8, 6.2, 2.2, 7.2, -24), (8.2, 20.1, 5.4, 2.0, 6.8, -32))):
            r, pv = (0, 0, sx * a), [sx * cx, cy, 0]
            m.cbox(arm, (sx * cx, cy, 0), (w, h, d), 'pauldron' if li != 1 else 'plate_l', rot=r, pivot=pv)
            if li == 2:
                m.cbox(arm, (sx * cx, cy - h / 2 + 0.25, 0), (w + 0.2, 0.5, d + 0.3), 'trim', rot=r, pivot=pv)
        m.cbox(arm, (sx * 5.9, 25.3, 0), (4.6, 0.75, 5.4), 'plate_l', rot=(0, 0, sx * -14), pivot=[sx * 5.9, 25.3, 0])
        m.rod(arm, (sx * 9.0, 24.2, -1.0), (sx * 13.2, 24.5, -1.0), 1.9, 2.4, mat='plate_l')
        m.rod(arm, (sx * 9.5, 22.3, 0.75), (sx * 12.9, 21.9, 1.2), 1.7, 2.2, mat='plate')
        m.rod(arm, (sx * 9.3, 20.5, 1.5), (sx * 11.8, 19.9, 1.9), 1.4, 1.7, mat='plate_d')
        m.cbox(arm, (sx * 6.4, 23.4, -3.55), (1.9, 1.9, 0.5), 'stone', rot=(0, 0, 45), pivot=[sx * 6.4, 23.4, -3.55])
        m.cbox(arm, (sx * 6.0, 16.6, 0.25), (5.4, 2.4, 5.4), 'plate')                         # налокотник
        m.cbox(arm, (sx * 8.85, 16.6, 0.5), (0.5, 2.0, 2.2), 'trim')
        x0, x1 = X(sx, 3.45, 8.55)
        m.box(arm, (x0, 13.4, -2.55), (x1, 15.6, 2.55), 'plate')
        x0, x1 = X(sx, 3.2, 8.8)
        m.box(arm, (x0, 13.0, -2.8), (x1, 13.9, 2.8), 'plate_l')
        m.box(arm, (x0, 13.6, -2.85), (x1, 14.1, 2.85), 'trim')
        x0, x1 = X(sx, 3.4, 8.6)
        m.box(arm, (x0, 10.9, -2.6), (x1, 13.0, 2.6), 'gaunt')
        x0, x1 = X(sx, 3.6, 8.4)
        m.box(arm, (x0, 10.6, -2.2), (x1, 11.3, 2.2), 'plate_d')

    # ---------------- поножи: кольчуга, набедренник, наколенник с бирюзовым ромбом; на ноге же — набедренная латная юбка (тассеты)
    for sx, nm, side in SIDES:
        leg = 'armor%sLeg' % side
        x0, x1 = X(sx, -0.5, 4.3)
        m.box(leg, (x0, 4.2, -2.45), (x1, 12.2, 2.45), 'chain')
        x0, x1 = X(sx, -0.6, 4.4)
        m.box(leg, (x0, 7.4, -2.65), (x1, 11.2, 2.45), 'plate')
        m.cbox(leg, (sx * 1.9, 6.3, -0.4), (5.2, 2.5, 5.6), 'plate_l')                          # наколенник
        m.cbox(leg, (sx * 1.9, 6.5, -3.35), (2.0, 2.0, 0.5), 'trim', rot=(0, 0, 45), pivot=[sx * 1.9, 6.5, -3.35])
        m.cbox(leg, (sx * 4.55 if sx > 0 else -0.75, 6.3, -0.25), (0.5, 2.0, 2.2), 'trim')
        x0, x1 = X(sx, -0.55, 4.75)
        m.box(leg, (x0, 8.6, -3.45), (x1, 12.6, -2.7), 'plate')                                 # тассет спереди
        m.box(leg, (x0, 8.6, -3.7), (x1, 9.1, -2.7), 'trim')
        m.rod(leg, (sx * 4.6, 12.0, -3.55), (sx * 0.0, 9.6, -3.55), 0.5, 0.5, mat='trim', ext=0.2)
        x0, x1 = X(sx, 4.45, 5.2)
        m.box(leg, (x0, 7.2, -2.7), (x1, 12.4, 2.6), 'plate')                                   # боковой тассет
        x0, x1 = X(sx, -0.55, 4.75)
        m.box(leg, (x0, 8.4, 2.45), (x1, 12.4, 3.1), 'plate')                                    # задняя пластина
        m.box(leg, (x0, 8.4, 2.7), (x1, 8.9, 3.3), 'trim')
        # латные сапоги: поножи-голень, сабатон, носок, бирюзовая кайма
        bt = 'armor%sBoot' % side
        x0, x1 = X(sx, -0.75, 4.55)
        m.box(bt, (x0, 1.4, -2.8), (x1, 5.6, 2.6), 'plate')
        x0, x1 = X(sx, -0.95, 4.75)
        m.box(bt, (x0, 5.0, -3.0), (x1, 5.6, 2.8), 'trim')
        x0, x1 = X(sx, -0.9, 4.7)
        m.box(bt, (x0, -0.05, -3.9), (x1, 1.8, 2.7), 'plate_d')
        x0, x1 = X(sx, 0.4, 3.4)
        m.box(bt, (x0, -0.05, -4.9), (x1, 1.3, -3.6), 'plate')
        m.box(bt, (x0, 1.5, -3.15), (x1, 2.0, -1.2), 'trim')
    return m


# ================================================================== «Накидка Главы Культа»
T_CRIM = [hex2('#C2382E'), hex2('#9C2722'), hex2('#78191A'), hex2('#4C0E10')]     # багровая ткань плаща Главы
T_CRIM_IN = [hex2('#6A1416'), hex2('#521012'), hex2('#3C0B0D'), hex2('#26070A')]  # изнанка
T_IRON = [hex2('#8A7E78'), hex2('#625650'), hex2('#463C38'), hex2('#2C2422')]     # тёмное железо шипов (как наплечники Главы)
T_EMBER = [hex2('#FFE9A0'), hex2('#FFC048'), hex2('#F07A1E'), hex2('#A83A10')]
T_SIGIL = [hex2('#3A0A0C'), hex2('#2A0608'), hex2('#1C0405'), hex2('#120203')]


def sigil_mask(u, v):
    """Знак культа на спине (как на плаще Главы): «пламя-капля» — контур капли, внутри язык пламени. u, v — доли (0..1)."""
    x = (u - 0.5) * 2
    y = (v - 0.5) * 2                                # −1 сверху .. 1 снизу
    # капля: окружность снизу + острие вверх
    yy = y - 0.25
    r = np.sqrt(x * x + yy * yy)
    drop = (r < 0.62) | ((yy < 0) & (np.abs(x) < 0.62 * (1 + yy / 1.15)) & (yy > -1.15))
    inner = (r < 0.34) | ((yy < 0) & (np.abs(x) < 0.34 * (1 + yy / 0.75)) & (yy > -0.75))
    ring = drop & ~inner
    flame = (np.abs(x + 0.1 * np.sin((y + 0.3) * 5)) < 0.16 * np.clip(0.5 - y, 0, 1.4)) & (y > -0.5) & (y < 0.5)
    return ring | flame


def mat_cape(ctx):
    info = ctx.cube.info
    inner = ctx.face == 'north'                                   # перед плаща — изнанка (к спине)
    c = GI.shade(ctx, T_CRIM_IN if inner else T_CRIM, fold_step=3, blotch=0.9, seed=41, tex='twill')
    a = np.ones(ctx.n)
    g = np.zeros((ctx.n, 3))
    r0, r1, c0, c1, w, h = GI.rows(ctx)
    pc, pr, q = GI.pxy(ctx)
    if info.get('sigil') and ctx.face == 'south':
        u = (ctx.L[:, 0] - info['sig'][0]) / info['sig'][2] + 0.5
        v = (info['sig'][1] - ctx.L[:, 1]) / info['sig'][3] + 0.5
        inb = (u >= 0) & (u <= 1) & (v >= 0) & (v <= 1)
        s = inb & sigil_mask(np.clip(u, 0, 1), np.clip(v, 0, 1))
        c = np.where(s[:, None], GI.pick(T_SIGIL, np.full(ctx.n, 2)), c)
        g = np.where(s[:, None], np.tile(hex2('#5A0E08') * 0.5, (ctx.n, 1)), g)
    if info.get('rag') and ctx.face in ('north', 'south', 'east', 'west'):
        # рваный подол: зубцы разной длины по столбцам пикселей; у края — тлеющие искры (светятся)
        W = int(round(w * K4))
        col = np.where(np.abs(ctx.N[:, 0]) > 0.5, q[:, 2], q[:, 0])
        hsh = (col * 2654435761 + 97) & 0xFFFF
        cut = ((col // 3) * 40503 + 11) % 7                        # глубина выреза зубца (пиксели от низа)
        prb = np.floor((1 - ctx.t) * h * K4).astype(int)
        a = np.where(prb < cut, 0.0, 1.0)
        edge = (prb >= cut) & (prb < cut + 2)
        c = np.where(edge[:, None], GI.pick(T_CRIM, np.full(ctx.n, 3)), c)
        ember = (prb >= cut) & (prb < cut + 6) & ((hsh % 11) == 0) | ((prb == cut) & (hsh % 5 == 0))
        ec = GI.pick(T_EMBER, np.where(hsh % 3 == 0, 0, 1))
        c = np.where(ember[:, None], ec, c)
        g = np.where(ember[:, None], ec * 0.9, g)
        ash = (prb >= cut + 2) & (prb < cut + 9) & ((hsh % 13) == 5)
        c = np.where(ash[:, None], GI.pick(T_IRON, np.full(ctx.n, 2)), c)
    if info.get('hem') and ctx.face not in ('up', 'down'):
        c = np.where((r0 == 0)[:, None], GI.pick(T_CRIM, np.full(ctx.n, 0)), c)
    return c, a, g


def mat_iron(ctx):
    c = GI.shade(ctx, T_IRON, folds=False, blotch=0.8, seed=43)
    g = None
    if ctx.cube.info.get('hot'):                                  # кончики шипов раскалены, как венец Главы
        y = ctx.P[:, 1]
        top = ctx.cube.info['hot']
        k = np.clip((y - top) / 1.6, 0, 1)
        hot = k > 0.15
        ec = GI.pick(T_EMBER, np.where(k > 0.7, 0, np.where(k > 0.4, 1, 2)))
        c = np.where(hot[:, None], ec, c)
        g = np.where(hot[:, None], ec * 0.85, 0)
    return c, 1.0, g


def mat_ember(ctx):
    c = GI.shade(ctx, T_EMBER, folds=False, rim=False)
    return c, 1.0, np.clip(c * 0.95, 0, 1)


def mat_gold_c(ctx):
    return GI.shade(ctx, GI.T_GOLD, folds=False), 1.0, None


CAPE_Z = 5.85        # плащ висит за спиной так, чтобы под ним помещались любые доспехи (наш воротник Кузнеца — до z = 5.75)


def build_mantle():
    m = PModel('cult_mantle', density=4, tex_w=128)
    m.materials.update(cape=mat_cape, iron=mat_iron, ember=mat_ember, gold=mat_gold_c)
    skeleton(m)
    B = 'armorBody'
    # воротник: толстый багровый валик вокруг шеи (поверх любого нагрудника), спереди — железная застёжка с тлеющим камнем
    m.box(B, (-5.6, 23.3, -4.3), (5.6, 25.6, 6.5), 'cape', hem=True)
    m.box(B, (-4.9, 25.5, -3.6), (4.9, 26.6, 6.1), 'cape', hem=True)
    m.box(B, (-6.0, 22.5, 4.7), (6.0, 25.0, 6.6), 'cape')                                    # спинка воротника — к плащу
    m.cbox(B, (0, 23.9, -4.55), (2.6, 2.2, 0.6), 'iron')
    m.cbox(B, (0, 23.9, -4.95), (1.2, 1.2, 0.4), 'ember')
    for sx in (-1, 1):                                                                       # цепь застёжки
        m.rod(B, (sx * 1.3, 23.9, -4.6), (sx * 4.6, 24.3, -4.5), 0.6, 0.6, mat='gold', ext=0.1)
    # шипы на плечах воротника (как у наплечников Главы), кончики раскалены
    for sx in (-1, 1):
        for k, (x, z, h, lean) in enumerate(((4.4, -1.6, 3.6, 18), (5.0, 0.8, 4.4, 24), (4.6, 3.4, 3.4, 30))):
            p = np.array([sx * x, 25.3, z])
            q = p + np.array([sx * math.sin(math.radians(lean)) * h, math.cos(math.radians(lean)) * h, 0.4])
            m.rod(B, p, q, 1.2 - 0.15 * k, mat='iron', hot=q[1] - 1.4)
    # плащ: три полосы-сегмента (каждый качается на своей кости), знак культа на спине, рваный тлеющий подол
    W = 6.4
    p0 = np.array([0, 24.6, CAPE_Z])
    m.bone('cape', B, p0)
    m.box('cape', (-W, 15.8, CAPE_Z - 0.4), (W, 24.6, CAPE_Z + 0.4), 'cape', sigil=True, sig=(0, 17.2, 8.6, 11.0))
    m.bone('cape_mid', 'cape', (0, 15.8, CAPE_Z))
    m.box('cape_mid', (-W - 0.2, 8.2, CAPE_Z - 0.4), (W + 0.2, 15.9, CAPE_Z + 0.4), 'cape', sigil=True, sig=(0, 17.2, 8.6, 11.0))
    m.bone('cape_low', 'cape_mid', (0, 8.2, CAPE_Z))
    m.box('cape_low', (-W - 0.4, 2.2, CAPE_Z - 0.4), (W + 0.4, 8.3, CAPE_Z + 0.4), 'cape', rag=True)
    # боковые полы плаща (заворачивают на плечи — плащ не плоский): короткие, крепятся к спинке воротника
    for sx, sn in ((1, 'r'), (-1, 'l')):
        q0 = np.array([sx * 6.3, 24.4, 4.4])
        m.bone('cape_side_' + sn, B, q0)
        x0, x1 = X(sx, 5.95, 6.75)
        m.box('cape_side_' + sn, (x0, 16.4, 2.6), (x1, 24.4, 6.2), 'cape', rag=True)
    return m


# ================================================================== анимации ткани (оси Blockbench: свисающая ткань назад — x плюс)
def S(t, per, ph=0.0):
    return math.sin(t * TAU / per + ph)


def anim_set(name, fn_by_mode):
    out = []
    for mode, (length, fn) in fn_by_mode.items():
        a = Anim(mode, length, loop=True)
        a.sample(lambda t, fn=fn: GI.bb(fn(t)), dt=0.1 if length > 1.5 else 0.05)
        out.append(a)
    return {a.name: a.to_json() for a in out}


MODES = {'idle': (4.0, 0.0, 1.0), 'walk': (1.0, 1.0, 1.4), 'run': (0.6, 2.0, 1.8), 'cast': (1.0, 0.6, 2.2)}   # длина, ветер (0..2), амплитуда


def jealous_pose(mode):
    per, wind, amp = MODES[mode]
    w = {'idle': 0, 'walk': 14, 'run': 26, 'cast': 10}[mode]

    def fn(t):
        o = {}
        for sn, s in (('r', 1), ('l', -1)):
            for k in range(8):
                a = math.radians(20 + 140 * k / 7)
                fwd = math.cos(a)
                ph = t * TAU / per + k * 0.8 + (0 if s > 0 else 2.0)
                sw = math.sin(ph) * 2.5 * amp
                back = (w * 0.6 if fwd < 0.2 else w * 0.25) + 2.5 * amp            # лента на ноге: назад — от ноги (сзади), спереди слабее
                lat = s * (2.0 * amp + math.sin(ph * 0.5) * 1.5 * amp)              # чуть в сторону — наружу от ноги
                o['rib_%s%d' % (sn, k)] = {'rot': [(back + sw) * (1 if fwd < 0.2 else 0.6) - (fwd > 0.2) * (2 + 0.5 * w), 0, lat]}
                o['rib_%s%d_b' % (sn, k)] = {'rot': [(3 * amp + math.sin(ph - 0.9) * 3 * amp) * (1 if fwd < 0.2 else -0.6), 0, lat * 0.6]}
            o['sleeve_' + sn] = {'rot': [S(t, per, s) * 3 * amp + 3 * amp + w * 0.3, 0, s * (2 + S(t, per * 2) * 2 * amp)]}
            o['tie_' + sn] = {'rot': [S(t, per, s * 0.5) * 2.5 * amp + 2.5 * amp + w * 0.2, 0, s * 3]}
            o['hat_rib_' + sn] = {'rot': [S(t, per, s) * 4 * amp + 4 * amp + w * 0.6, 0, s * (4 + 3 * S(t, per * 2) * amp)]}
            o['hat_rib_%s_b' % sn] = {'rot': [S(t, per, s - 0.9) * 6 * amp + 5 * amp + w * 0.4, 0, s * 3 * S(t, per, -0.9) * amp]}
            for k in range(3):
                o['cap_%s%d' % (sn, k)] = {'rot': [S(t, per, k * 0.7 + s) * 3 * amp + w * 0.35, 0, s * (3 + 3 * amp + S(t, per, k) * 2 * amp)]}
        o['hat_tip'] = {'rot': [S(t, per) * 3 * amp - w * 0.2, 0, S(t, per * 2) * 4 * amp]}
        o['hat_tip2'] = {'rot': [S(t, per, -0.6) * 4 * amp - w * 0.15, 0, S(t, per * 2, -0.6) * 5 * amp]}
        o['hat_tip3'] = {'rot': [S(t, per, -1.2) * 6 * amp - w * 0.15, 0, 0]}
        o['hat_thread'] = {'rot': [0, -360 * t / per * (1 if mode != 'cast' else 2), 0]}
        return o
    return fn


def smith_pose(mode):
    per, wind, amp = MODES[mode]
    w = {'idle': 0, 'walk': 10, 'run': 22, 'cast': 6}[mode]

    def fn(t):
        o = {}
        for nm, s in (('r', 1), ('l', -1)):
            # ленты спереди: ветер движения кладёт их на грудь/бёдра (x минус = к телу) нельзя — только от тела: вперёд-наружу
            # ленты спереди висят на кирасе: качаются чуть вперёд-наружу (не в грудь), без «ветра» — на шаге их не догоняет бедро
            a1 = min(amp, 1.4)
            out = {'idle': 1.5, 'walk': 6, 'run': 24, 'cast': 8}[mode]                     # на бегу ленты разлетаются наружу — мимо бедра
            o['ribbon_%s1' % nm] = {'rot': [-(1.0 * a1 + S(t, per, s) * 1.0 * a1), 0, s * (out + S(t, per * 2, s) * 2 * a1)]}
            o['ribbon_%s2' % nm] = {'rot': [-(1.5 * a1 + S(t, per, s - 0.8) * 1.5 * a1), 0, s * (w * 0.08 + S(t, per, s - 0.8) * 1.5 * a1)]}
        return o
    return fn


def mantle_pose(mode):
    per, wind, amp = MODES[mode]
    # угол «назад» каждого сегмента (сумма по цепочке) — подобран clearance(): нога не достаёт до плаща
    base = {'idle': (3, 2, 2), 'walk': (28, 15, 13), 'run': (36, 16, 14), 'cast': (12, 8, 8)}[mode]

    def fn(t):
        f1, f2, f3 = (S(t, per), S(t, per, -0.9), S(t, per, -1.8))
        k = {'idle': 1.0, 'walk': 2.2, 'run': 3.0, 'cast': 3.4}[mode]
        o = {'cape': {'rot': [base[0] + k * (1 + f1), 0, S(t, per * 2) * 1.0 * amp]},
             'cape_mid': {'rot': [base[1] + k * 1.3 * (1 + f2), 0, S(t, per * 2, -0.9) * 1.5 * amp]},
             'cape_low': {'rot': [base[2] + k * 1.6 * (1 + f3), 0, S(t, per * 2, -1.8) * 2.0 * amp]}}
        for sn, s in (('r', 1), ('l', -1)):
            o['cape_side_' + sn] = {'rot': [base[0] * 0.4 + k * 0.6 * (1 + S(t, per, s)), 0, s * (1.5 + k * 0.5 * (1 + S(t, per, s - 1)))]}
        return o
    return fn


# ================================================================== проверка «плащ не проходит сквозь ногу»
def clearance(model, fn_by_mode, bones, legs_max=(69, 80)):
    """Мин. зазор (ед.) между нижними точками сегментов плаща/лент на теле и ногой игрока (с бронёй до +1.0) на ванильном шаге.
    Нога: брусок x 0..4, z −2..2 (+1 броня), вращается вокруг (y 12, z 0) на ±угол; плащ — точки граней в позе анимации."""
    res = {}
    for mode, (length, fn) in fn_by_mode.items():
        lim = {'run': legs_max[1], 'walk': legs_max[0], 'idle': 8, 'cast': 15}[mode]
        worst = 1e9
        for ti in range(int(length / 0.05) + 1):
            pose = GI.bb(fn(ti * 0.05))
            M = {}
            for bn in model.order:                      # FK во внутренних осях: R = euler(rest + anim)
                b = model.bones[bn]
                r = np.array(b.rot, float) + np.array(pose.get(bn, {}).get('rot', [0, 0, 0]))
                R = euler(r)
                if b.parent:
                    PM, Po = M[b.parent]
                else:
                    PM, Po = np.eye(3), np.zeros(3)
                o = PM @ (b.pivot - R @ b.pivot) + Po
                M[bn] = (PM @ R, o)
            pts = []
            for bn in bones:
                Mb, ob = M[bn]
                for c in model.bones[bn].cubes:
                    for x in np.linspace(c.frm[0], c.to[0], 7):
                        for y in np.linspace(c.frm[1], c.to[1], 5):
                            for z in (c.frm[2], c.to[2]):
                                q = np.array([x, y, z])
                                if c.rot:
                                    q = np.asarray(c.pivot, float) + euler(c.rot) @ (q - np.asarray(c.pivot, float))
                                pts.append(Mb @ q + ob)
            pts = np.array(pts)
            for ang in np.linspace(-lim, lim, 13):        # нога назад (+) и вперёд (−)
                a = math.radians(ang)
                # точка → в систему ноги (поворот вокруг x через (y 12, z 0)); нога — бокс |z| ≤ 3, y ≥ −1, x −1..5 (обе ноги — по |x|)
                y, z = pts[:, 1] - 12, pts[:, 2]
                ly = y * math.cos(a) + z * math.sin(a)
                lz = -y * math.sin(a) + z * math.cos(a)
                inx = (np.abs(pts[:, 0]) < 5.2)
                dz = np.maximum(np.abs(lz) - 3.0, 0)
                dy = np.maximum(-13 - ly, 0) + np.maximum(ly - 0, 0)
                d = np.where(inx, np.sqrt(dz * dz + dy * dy), 99)
                worst = min(worst, float(d.min()))
        res[mode] = round(worst, 2)
    return res


# ================================================================== иконки 32×32 (пиксель-арт: силуэт, тёмный контур, свет сверху-слева)
def icon(shape, pal, details=None):
    """shape: список строк 32×32 ('#' — тело, '.' — пусто, 'a'..'z' — цвет детали из details); pal = [свет, база, тень, контур]."""
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    px = im.load()
    H = len(shape)
    grid = [row.ljust(32, '.')[:32] for row in shape] + ['.' * 32] * (32 - H)
    def solid(x, y):
        return 0 <= x < 32 and 0 <= y < 32 and grid[y][x] != '.'
    for y in range(32):
        for x in range(32):
            ch = grid[y][x]
            if ch == '.':
                continue
            edge = not (solid(x - 1, y) and solid(x + 1, y) and solid(x, y - 1) and solid(x, y + 1))
            if ch != '#' and details and ch in details:          # деталь (рога, ленты, кайма): свой цвет, у края — темнее
                c = details[ch]
                k = 0.62 if (edge and not solid(x + 1, y)) or (edge and not solid(x, y + 1)) else 1.15 if (edge and not solid(x, y - 1)) else 1.0
                px[x, y] = tuple(max(0, min(255, int(v * k))) for v in c) + (255,)
                continue
            if edge:
                px[x, y] = tuple(pal[3]) + (255,)
                continue
            col = pal[1]
            if ch != '#' and details and ch in details:
                col = details[ch]
                if not solid(x, y - 2) or (y > 0 and grid[y - 1][x] != ch and grid[y - 1][x] != '.' and ch.islower()):
                    pass
            if ch == '#':
                if not solid(x - 2, y) or not solid(x, y - 2):
                    col = pal[0]
                elif not solid(x + 2, y) or not solid(x, y + 2):
                    col = pal[2]
            px[x, y] = tuple(int(v) for v in col) + (255,)
    return im


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def make_icons():
    I = {}
    # --- Ирина
    lil = [rgb('#A585CF'), rgb('#7E5EB0'), rgb('#4C3278'), rgb('#1A1024')]
    hat = [rgb('#7C7986'), rgb('#5E5A6A'), rgb('#3E3A48'), rgb('#141018')]
    I['jealous_helmet'] = icon([
        '................................',
        '.................##.............',
        '................####............',
        '...............#####............',
        '..............######............',
        '.............##ww###............',
        '.............#wwww##............',
        '............###ww###............',
        '............###ww####...........',
        '...........##########...........',
        '...........llllllllll...........',
        '...........llllllllll...........',
        '..........############..........',
        '..........rrrrrrrrrrrr..........',
        '...######################.......',
        '.##########################.....',
        '..########################......',
        '.....bbbbbbbbbbbbbbbbb..........',
        '.....bbbb.........bbbb..........',
        '.....bbb...........bbb..........',
        '.....bbb...........bbb..........',
        '.....bbbb.........bbbb..........',
        '.....bbbbbb.....bbbbbb.ll.......',
        '......bbbbbbbbbbbbbbb..ll.......',
        '.......................ll.......',
        '........................l.......',
    ], hat, {'w': rgb('#F2E8D0'), 'l': rgb('#B494DC'), 'r': rgb('#E3262F'), 'b': rgb('#6484BA')})
    I['jealous_chestplate'] = icon([
        '................................',
        '......bbbbb..........bbbbb......',
        '....ggggggggg......ggggggggg....',
        '...gggggggggggbbbbggggggggggg...',
        '...gggggggggg#yr#gggggggggggg...',
        '...ggg#######################...',
        '...###########################..',
        '...###.##ppppppppppppppp##.###..',
        '...###.##ppppppppppppppp##.###..',
        '...###.###################.###..',
        '...###.rrrrrrrrrrrrrrrrrrr.###..',
        '...###.##ppppppppppppppp##.###..',
        '..####.##ppppppppppppppp##.####.',
        '..####.###################.####.',
        '..####.##ppppppppppppppp##.####.',
        '.#####.###################.#####',
        '.#####.lllllllllllllllllll.#####',
        '.#####.lllllllllllllllllll.#####',
        '.......###################......',
        '.......###################......',
        '.......#########.#########......',
    ], lil, {'g': rgb('#6C7761'), 'b': rgb('#6484BA'), 'p': rgb('#6E6A7C'), 'r': rgb('#E3262F'), 'y': rgb('#E8B84A'),
             'l': rgb('#B494DC')})
    I['jealous_leggings'] = icon([
        '................................',
        '......gggggggggggggggggggg......',
        '.....gggggggggggggggggggggg.....',
        '....llgglgglgggggglggllgglll....',
        '....ll#ll#ll######ll#ll#ll#l....',
        '...lll#ll#ll##..##ll#ll#ll#ll...',
        '...ll##ll#ll##..##ll#ll#lll#l...',
        '...l#####lll#....#lll#####ll#...',
        '..ll#####lll#....#lll#####lll...',
        '..ll####llll#....#llll####lll...',
        '..l#####llll#....#llll#####ll...',
        '..l#####lll#......#lll#####ll...',
        '.ll####llll#......#llll####lll..',
        '.l.####l.ll#......#ll.l####.l...',
        '...####....#......#....####.....',
        '...........#......#.............',
    ], [rgb('#4C4754'), rgb('#3A3641'), rgb('#2B2731'), rgb('#120E16')],
        {'g': rgb('#6C7761'), 'l': rgb('#B494DC')})
    I['jealous_boots'] = icon([
        '................................',
        '................................',
        '................................',
        '................................',
        '....lllllllll.....lllllllll.....',
        '....lllrrllll.....llllrrlll.....',
        '....lllllllll.....lllllllll.....',
        '.....#######.......#######......',
        '.....#######.......#######......',
        '.....#######.......#######......',
        '.....#######.......#######......',
        '.....#######.......#######......',
        '.....#######.......#######......',
        '.....#######.......#######......',
        '.....########......########.....',
        '....##########....###########...',
        '...###########....############..',
        '..############....############..',
        '..############....############..',
        '..lllllllllll......lllllllllll..',
    ], [rgb('#5E5868'), rgb('#3A3641'), rgb('#2B2731'), rgb('#120E16')], {'l': rgb('#8A66BE'), 'r': rgb('#E3262F')})
    # --- Арис
    st = [rgb('#c6c6ce'), rgb('#8e8e9a'), rgb('#4c4c57'), rgb('#16161b')]
    tl = rgb('#3cd6e0')
    I['smith_helmet'] = icon([
        '....tt..................tt......',
        '....tt..................tt......',
        '...ttt..................ttt.....',
        '...tt....................tt.....',
        '...tt....................tt.....',
        '...ttt..................ttt.....',
        '....tt.................ttt......',
        '....ttt...............ttt.......',
        '.....ttt.............ttt........',
        '......###....##.....###.........',
        '......########################..',
        '....##########################..',
        '....###########..#############..',
        '..####.##################.####..',
        '..####.###kkkk##kkkk#####.####..',
        '..####.##################.####..',
        '..####.#.#.#.#..#.#.#.#.#.####..',
        '...###.#.#.#.#..#.#.#.#.#.###...',
        '....##.#.#.#.#..#.#.#.#.#.##....',
        '.......###################......',
        '.......ttttttttttttttttttt......',
    ][::1], st, {'t': tl, 'k': rgb('#7eeef2')})
    I['smith_chestplate'] = icon([
        '................................',
        '..#####.....#########.....#####.',
        '.#######...###########...#######',
        '.########.##ss#####ss##.########',
        '.########.##ss#####ss##.########',
        '.#######.#################.####.',
        '..ttttt..#################..ttt.',
        '..#####..##ttttttttttttt##..###.',
        '..#####..#################..###.',
        '..#####..#t#############t#..###.',
        '..#####..##t###########t##..###.',
        '..#####..###t#########t###..###.',
        '..#####..####tttttttt#####..###.',
        '.......cc#################cc....',
        '.......cc#################cc....',
        '.........lllllllllllllllll......',
        '.........lllllllttllllllll......',
        '.........#################......',
    ], st, {'t': tl, 's': rgb('#e8e8f0'), 'c': rgb('#9234b0'), 'l': rgb('#3a303f')})
    I['smith_leggings'] = icon([
        '................................',
        '.......##################.......',
        '.......ttttttttttttttttttt......',
        '......#########..#########......',
        '......#t#####t#..#t#####t#......',
        '......##t###t##..##t###t##......',
        '......###ttt###..###ttt###......',
        '......#########..#########......',
        '.......#######....#######.......',
        '.......###t###....###t###.......',
        '.......##ttt##....##ttt##.......',
        '.......###t###....###t###.......',
        '.......#######....#######.......',
        '.......#######....#######.......',
        '.......#######....#######.......',
    ], st, {'t': tl})
    I['smith_boots'] = icon([
        '................................',
        '................................',
        '................................',
        '................................',
        '....ttttttttt.....ttttttttt.....',
        '....#########.....#########.....',
        '....#########.....#########.....',
        '....##ttttt##.....##ttttt##.....',
        '....#########.....#########.....',
        '....#########.....#########.....',
        '....#########.....#########.....',
        '....#########.....#########.....',
        '....##########....##########....',
        '...###########....###########...',
        '..############....############..',
        '..############....############..',
        '..tttttttttttt....tttttttttttt..',
        '..############....############..',
    ], st, {'t': tl})
    # --- накидка
    cr = [rgb('#C2382E'), rgb('#9C2722'), rgb('#5E1214'), rgb('#200406')]
    I['cult_mantle'] = icon([
        '.......i...............i........',
        '......ii...............ii.......',
        '.....iii...ccccccccc...iii......',
        '.....ii..ccccccccccccc..ii......',
        '......#ccccccceeccccccc#........',
        '.....###################........',
        '.....###################........',
        '....#####################.......',
        '....#########kkk#########.......',
        '....########kk.kk########.......',
        '...########kk.k.kk########......',
        '...########kk.k.kk########......',
        '...#########kk.kk#########......',
        '..###########kkk###########.....',
        '..#########################.....',
        '..#########################.....',
        '.###########################....',
        '.###########################....',
        '.##.###.#.####.####.#.###.##....',
        '.e..#.e.#..#.e..#.#..e.#..e.....',
    ], cr, {'i': rgb('#625650'), 'c': rgb('#78191A'), 'e': rgb('#FFC048'), 'k': rgb('#2A0608')})
    return I


def lang_entries():
    ru, en = {}, {}
    P = 'item.pohsmp_core.'
    parts = (('helmet', 'шлем', 'Helmet'), ('chestplate', 'нагрудник', 'Chestplate'), ('leggings', 'поножи', 'Leggings'), ('boots', 'ботинки', 'Boots'))
    names = {
        'jealous': ({'helmet': 'Шляпа Ревности', 'chestplate': 'Платье-доспех Ревности', 'leggings': 'Юбка из лент Ревности',
                     'boots': 'Сапоги Ревности'},
                    {'helmet': 'Jealous Witch Hat', 'chestplate': 'Jealous Armored Gown', 'leggings': 'Jealous Ribbon Skirt',
                     'boots': 'Jealous Boots'}),
        'smith': ({'helmet': 'Рогатый шлем Кузнеца', 'chestplate': 'Кираса Кузнеца', 'leggings': 'Набедренники Кузнеца',
                   'boots': 'Сабатоны Кузнеца'},
                  {'helmet': "Smith's Horned Helm", 'chestplate': "Smith's Cuirass", 'leggings': "Smith's Cuisses",
                   'boots': "Smith's Sabatons"}),
    }
    for sid, (nr, ne) in names.items():
        for p, _, _ in parts:
            ru[P + '%s_%s' % (sid, p)] = nr[p]
            en[P + '%s_%s' % (sid, p)] = ne[p]
    ru[P + 'jealous.set_name'] = 'Комплект «Наряд Ревности» (Ирина)'
    en[P + 'jealous.set_name'] = 'Set: Jealous Attire (Irina)'
    ru[P + 'jealous.set_bonus'] = ' Полный комплект: ударивший вас получает «метку ревности» — 10 % его урона возвращаются ему красными нитями'
    en[P + 'jealous.set_bonus'] = ' Full set: whoever hits you gets the Mark of Jealousy — red threads return 10% of their damage'
    ru[P + 'jealous.desc'] = 'Кровь: сила заклинаний крови, мана, регенерация маны'
    en[P + 'jealous.desc'] = 'Blood: blood spell power, mana, mana regeneration'
    ru[P + 'smith.set_name'] = 'Комплект «Латы Кузнеца» (Арис)'
    en[P + 'smith.set_name'] = "Set: Smith's Plate (Aris)"
    ru[P + 'smith.set_bonus'] = ' Полный комплект: оружие «закалено» (+10 % урона оружием), иммунитет к отбрасыванию'
    en[P + 'smith.set_bonus'] = ' Full set: tempered weapons (+10% weapon damage), immune to knockback'
    ru[P + 'smith.desc'] = 'Броня и прочность брони, сопротивление отбрасыванию'
    en[P + 'smith.desc'] = 'Armor and armor toughness, knockback resistance'
    ru[P + 'cult_mantle'] = 'Накидка Главы Культа'
    en[P + 'cult_mantle'] = "Cult Head's Mantle"
    ru[P + 'cult_mantle.desc1'] = 'Надевается поверх любой брони'
    en[P + 'cult_mantle.desc1'] = 'Worn over any armor'
    ru[P + 'cult_mantle.desc2'] = 'Сопротивление огню, сила огненных заклинаний'
    en[P + 'cult_mantle.desc2'] = 'Fire resistance, fire spell power'
    ru[P + 'cult_mantle.desc3'] = 'Плащ тлеет: на бегу с подола осыпается пепел'
    en[P + 'cult_mantle.desc3'] = 'The cloak smoulders: ash falls from the hem as you run'
    ru[P + 'boss_armor.admin'] = 'Трофей с босса — выдаёт только администратор'
    en[P + 'boss_armor.admin'] = 'Boss trophy — given by an admin only'
    return ru, en


def merge_lang(path, add):
    with open(path, encoding='utf-8') as fh:
        d = json.load(fh)
    d.update(add)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(d, fh, ensure_ascii=False, indent=2)
        fh.write('\n')


# ================================================================== запись
BUILDERS = {'jealous': (build_jealous, jealous_pose, ('tie_r', 'tie_l')),
            'smith': (build_smith, smith_pose, ('ribbon_r1', 'ribbon_r2', 'ribbon_l1', 'ribbon_l2')),
            'cult_mantle': (build_mantle, mantle_pose, ('cape', 'cape_mid', 'cape_low'))}


def write_armor(name):
    build, pose, check = BUILDERS[name]
    m = build()
    m.pack()
    m.paint()
    write_json(os.path.join(A, 'geo', 'armor', name + '.geo.json'), m.geo_json(name), compact=True)
    td = os.path.join(A, 'textures', 'armor')
    os.makedirs(td, exist_ok=True)
    m.image.save(os.path.join(td, name + '.png'), optimize=True)
    WRITTEN.extend(['geo/armor/%s.geo.json' % name, 'textures/armor/%s.png' % name])
    if m.glow is not None and np.asarray(m.glow)[..., 3].any():
        m.glow.save(os.path.join(td, name + '_glowmask.png'), optimize=True)
        WRITTEN.append('textures/armor/%s_glowmask.png' % name)
    fns = {mode: (MODES[mode][0], pose(mode)) for mode in MODES}
    anims = anim_set(name, fns)
    write_json(os.path.join(A, 'animations', 'armor', name + '.animation.json'), {'format_version': '1.8.0', 'animations': anims}, compact=True)
    WRITTEN.append('animations/armor/%s.animation.json' % name)
    nc = sum(len(b.cubes) for b in m.bones.values())
    msg = '%s: bones %d, cubes %d, tex %s' % (name, len(m.bones), nc, m.tex_px)
    if check:
        msg += ', зазор до ноги (ед.): %s' % clearance(m, fns, check)
    print(msg)
    return m


def main(args):
    for name in BUILDERS:
        write_armor(name)
    it = os.path.join(A, 'textures', 'item')
    for k, im in make_icons().items():
        im.save(os.path.join(it, k + '.png'), optimize=True)
        WRITTEN.append('textures/item/%s.png' % k)
    if '--lang' in args:            # строки и models/item уже сделал программист (docs/inbox/2026-11-21_cloudcode_T35.md) — только по запросу
        ru, en = lang_entries()
        merge_lang(os.path.join(A, 'lang', 'ru_ru.json'), ru)
        merge_lang(os.path.join(A, 'lang', 'en_us.json'), en)
    print('wrote %d files' % len(WRITTEN))
    if '--shots' in args or '--video' in args:
        import t35_armor_render as R
        if '--shots' in args:
            R.shots(args)
        if '--video' in args:
            R.video(args)


if __name__ == '__main__':
    main(sys.argv[1:])
