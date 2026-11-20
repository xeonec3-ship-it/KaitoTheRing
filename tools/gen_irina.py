#!/usr/bin/env python3
"""
T27 — визуал босса «Ирина, Ведьма Ревности» (Глава 2 Ячейки Культа). ТЗ: docs/specs/tasks/T27_irina_boss.md.
Референсы: docs/references/t27/irina_look.jpg (облик; владелец 20.11, второе решение: лица нет — под капюшоном тьма, как на референсе),
           docs/references/t27/irina_staff.jpg (посох — tools/gen_irina_staff.py).
Модель — с нуля (каркас tools/nightmare_geo.py), кости и их имена совместимы с магами Iron's (abstract_casting_mob: body, torso, head,
right_arm/left_arm, right_leg/left_leg, bipedHandRight/Left, rightItem/leftItem) — анимации каста Iron's (casting_animations.json) на ней
играются; плюс свои кости: шляпа (hat, hat_tip…), капюшон, ленты мантии (rib_*), рукава (sleeve_*), красные нити (thread_*).
Эталон качества (владелец 20.11) — модель Главы Культа (T26): 1 тексель = 1/16 блока, ручная пиксельная светотень без шума,
объёмные детали брусками. Сравнительный кадр рядом с ним — docs/media/t27_vs_cult_leader.jpg.

Пишет (src/main/resources/assets/pohsmp_core/):
  geo/entity/irina.geo.json                              модель (лицом к −z как в Blockbench; ноги на y = 0; 16 ед. = 1 блок)
  textures/entity/irina/irina.png, irina_glowmask.png   текстура (атлас 128 × 128, 1 тексель = 1 ед.) и свечение (нити, знак-крест)
  animations/entity/irina.animation.json                 анимации: тело (irina_*) и ткань/нити (irina_cloth_*) — два контроллера
Дальше вызывает tools/gen_irina_staff.py (посох) и tools/gen_irina_fx.py (fx, печати, полоса, титры, иконки, lang, звуки, кадры).

Запуск:  python3 tools/gen_irina.py [--shots] [--html] [--three путь/three.min.js]
  --shots  проверочные кадры docs/media/t27_*.jpg (Playwright + three.js r128)
  --html   tools/irina_preview.html (интерактивное превью: модель, посох, все анимации)
"""
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nightmare_geo import (Model, Anim, fbm, vnoise, ridge, hex2, mix, sstep, write_json, TAU, face_size)  # noqa: E402

ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
WRITTEN = []

# ================================================================== палитра (по референсу: лиловое, серо-зелёное, синий капюшон, красные нити)
HAT_D, HAT_M, HAT_L = hex2('#2B2935'), hex2('#423F4D'), hex2('#5D5969')
LIL_L, LIL, LIL_D, LIL_DD = hex2('#E2CDF5'), hex2('#B99BE0'), hex2('#8865BA'), hex2('#55397F')
BLU_L, BLU, BLU_D, BLU_DD = hex2('#A9CBF2'), hex2('#6290CF'), hex2('#3A5C98'), hex2('#1C2C52')
GG_L, GG, GG_D, GG_DD = hex2('#86927A'), hex2('#626D5A'), hex2('#414A3D'), hex2('#272D25')
RED_L, RED, RED_D, RED_DD = hex2('#FF7A66'), hex2('#E3262F'), hex2('#9A0F1E'), hex2('#4E0610')
SKIN_L, SKIN, SKIN_S, SKIN_SS = hex2('#FFF4F0'), hex2('#F7E4DF'), hex2('#E7C6C6'), hex2('#C99FAA')
BLUSH, LIP = hex2('#F29AAE'), hex2('#D9667E')
HAIR_L, HAIR, HAIR_D = hex2('#6A58A0'), hex2('#2E2448'), hex2('#170F28')
LINE = hex2('#1A1024')            # линия-контур (аниме): тёмно-фиолетовая, не чёрная
CROSS, CROSS_D = hex2('#EFE4C8'), hex2('#B9A57E')
WHITE = hex2('#FFFFFF')
IRIS_T, IRIS_M, IRIS_B = hex2('#4E0820'), hex2('#C21839'), hex2('#FF6E86')
GOLD = hex2('#E8B84A')

LIGHT = np.array([-0.45, 0.8, -0.4])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


# ================================================================== модель с разной плотностью граней (лицо крупнее)
class IModel(Model):
    def pack(self):
        k = self.density
        rects = []
        for bn in self.order:
            for ci, c in enumerate(self.bones[bn].cubes):
                kd = c.info.get('dens', {})
                for f in ('north', 'south', 'east', 'west', 'up', 'down'):
                    if f in c.info.get('hide', ()):
                        continue
                    kk = kd.get(f, k) if isinstance(kd, dict) else kd
                    w, h = face_size(c, f)
                    pw, ph = max(1, int(round(w * kk))), max(1, int(round(h * kk)))
                    rects.append((ph, pw, bn, ci, f))
        rects.sort(key=lambda r: (-r[0], -r[1]))
        W = self.tex_w * k
        x, y, row_h = 0, 0, 0
        for ph, pw, bn, ci, f in rects:
            if x + pw + 1 > W:
                x, y, row_h = 0, y + row_h + 1, 0
            c = self.bones[bn].cubes[ci]
            c.px[f] = (x, y, pw, ph)
            c.uv[f] = (x / k, y / k, pw / k, ph / k)
            x += pw + 1
            row_h = max(row_h, ph)
        H = y + row_h + 1
        hp = 1
        while hp < H:
            hp *= 2
        self.tex_px = (W, hp)
        self.tex_units = (self.tex_w, hp / k)


# ================================================================== пиксельная покраска (эталон — Глава Культа T26)
# Стандарт владельца: 1 тексель = 1/16 блока, ручная светотень по пикселям, без шума и сглаживания. Поэтому материалы ниже — не шейдеры,
# а правила «как рисует пиксельщик»: 3–4 тона на материал; верхняя грань светлее, нижняя темнее; верхний ряд пикселей боковой грани —
# блик, нижний — тень, крайние столбцы — контур; складки ткани — тёмные столбики с шагом 3 текселя; узоры — целыми пикселями.
def edge_dist(ctx):
    """Расстояние (ед. модели = тексели) от центра текселя до ближайшего ребра грани."""
    w, h = face_size(ctx.cube, ctx.face)
    return np.minimum(np.minimum(ctx.s * w, (1 - ctx.s) * w), np.minimum(ctx.t * h, (1 - ctx.t) * h))


def rows(ctx):
    """Номер ряда пикселей сверху (0 — верхний) и снизу, номер столбца слева и справа на боковой грани."""
    w, h = face_size(ctx.cube, ctx.face)
    return (np.floor(ctx.t * h)).astype(int), (np.floor((1 - ctx.t) * h)).astype(int), (np.floor(ctx.s * w)).astype(int), \
        (np.floor((1 - ctx.s) * w)).astype(int), w, h


def pick(tones, idx):
    idx = np.clip(np.asarray(idx), 0, len(tones) - 1)
    T = np.array(tones)
    return T[idx]


T_HAT = [hex2('#7C7986'), hex2('#625F6C'), hex2('#4E4B58'), hex2('#3A3743')]
T_LIL = [hex2('#DCC6F2'), hex2('#B494DC'), hex2('#9070C2'), hex2('#664894')]
T_LIL2 = [hex2('#C2A8E4'), hex2('#9A7ACA'), hex2('#7A5AAC'), hex2('#543C80')]
T_PALE = [hex2('#F4EAFC'), hex2('#E2D0F4'), hex2('#C8B0E6'), hex2('#9E82C6')]
T_BLU = [hex2('#B8D2F2'), hex2('#86A6D6'), hex2('#6484BA'), hex2('#425C92')]
T_GG = [hex2('#8E9A82'), hex2('#6C7761'), hex2('#555F4C'), hex2('#3B4336')]
T_RED = [hex2('#C0201C'), hex2('#A81A18'), hex2('#8E1414'), hex2('#7A0E10')]
T_BOOT = [hex2('#4C4754'), hex2('#3A3641'), hex2('#2B2731'), hex2('#1D1A23')]
T_CROSS = [hex2('#FFF8E8'), hex2('#F2E8D0'), hex2('#D8C8A4'), hex2('#A89470')]
T_GOLD = [hex2('#FFE89A'), hex2('#E8B84A'), hex2('#C08A2A'), hex2('#8A5A14')]
T_SKIN = [hex2('#E9DCE6'), hex2('#D2C2D0'), hex2('#B6A4B8'), hex2('#8C7A92')]       # бледные руки (холодные, в тени рукавов)
VOID = [hex2('#0E0C14'), hex2('#07060B'), hex2('#040306'), hex2('#020203')]


def ihash(*a):
    h = 2166136261
    for v in a:
        h = ((h ^ (int(v) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    return h


def fold_columns(ctx, i, step=3, phase=0):
    """Складки «рукой»: на боковых гранях тёмный столбик складки начинается/кончается в своём ряду (длина разная), рядом —
    светлый блик складки; без сплошной решётки."""
    up = ctx.N[:, 1] > 0.5
    dn = ctx.N[:, 1] < -0.5
    side = ~(up | dn)
    u = np.where(np.abs(ctx.N[:, 0]) > 0.5, ctx.P[:, 2], ctx.P[:, 0])
    col = np.floor(u + 64 + phase).astype(int)
    yy = np.floor(ctx.P[:, 1] + 64).astype(int)
    hsh = np.array([ihash(c, 7) for c in col]) if len(col) < 0 else (col * 2654435761 + 977) & 0xFFFF
    top = 64 + 14 + (hsh % 23)                                                 # где складка начинается (в мировой высоте)
    is_fold = side & (col % step == 0) & (yy < top)
    i[is_fold] = np.maximum(i[is_fold], 2)
    lit = side & (col % step == 1) & (yy < top - 1) & (yy % 3 != 0) & (i == 1)
    i[lit] = 0
    return i


def shade(ctx, tones, folds=True, rim=True, fold_step=3, fold_phase=0, blotch=0.0, seed=0):
    """tones: [блик, основной, полутень, тень]. Пиксельная светотень: верх/низ граней, контурные края, складки разной длины,
    крупные пятна-потёртости целыми тонами (blotch) — как на ткани Главы Культа."""
    n = ctx.n
    i = np.ones(n, int)
    if blotch:
        b = fbm(ctx.P, 0.3, 300 + seed, 2)
        i = i + (b > 0.6 - 0.08 * blotch).astype(int) - (b < 0.34 + 0.06 * blotch).astype(int)
    up = ctx.N[:, 1] > 0.5
    dn = ctx.N[:, 1] < -0.5
    side = ~(up | dn)
    r0, r1, c0, c1, w, h = rows(ctx)
    i[up] = np.minimum(i[up], 0) if blotch == 0 else np.clip(i[up] - 1, 0, 1)
    i[dn] = 3
    if folds:
        i = fold_columns(ctx, i, fold_step, fold_phase)
    if rim:
        i[side & (r0 == 0) & (h >= 2)] = 0                          # верхний ряд — блик
        i[side & (r1 == 0) & (h >= 3)] = 3                          # нижний ряд — глубокая тень (низ складок)
        i[side & (r1 == 1) & (h >= 6)] = np.maximum(i[side & (r1 == 1) & (h >= 6)], 2)
        i[side & ((c0 == 0) | (c1 == 0)) & (w >= 3) & (r0 > 0)] = np.maximum(i[side & ((c0 == 0) | (c1 == 0)) & (w >= 3) & (r0 > 0)], 2)
    return pick(tones, np.clip(i, 0, 3))


def trims(ctx, c, info, tones, accent):
    """Кайма, швы, строчка: hem — низ: ряд акцента над тёмным краем; trim — кант сверху и снизу; seam — вертикальный шов с
    пунктиром строчки по середине передней/задней грани."""
    if ctx.face in ('up', 'down'):
        return c
    r0, r1, c0, c1, w, h = rows(ctx)
    if info.get('hem') and h >= 3:
        c = np.where(((r1 == 1))[:, None], pick(accent, np.full(ctx.n, 1)), c)
        c = np.where(((r1 == 2) & (h >= 5) & (c0 % 2 == 0))[:, None], pick(accent, np.full(ctx.n, 2)), c)    # пунктир строчки над каймой
    if info.get('trim') and h >= 2:
        c = np.where(((r0 == 0) | (r1 == 0))[:, None], pick(accent, np.full(ctx.n, 0)), c)
    if info.get('seam') and ctx.face in ('north', 'south') and w >= 4:
        mid = np.abs(c0 - c1) <= 0
        c = np.where((mid & (r0 > 0))[:, None], pick(tones, np.full(ctx.n, 3)), c)
        st = (np.abs(c0 - c1) == 2) & (r0 % 2 == 1)
        c = np.where(st[:, None], pick(tones, np.full(ctx.n, 0)), c)
    return c


def outline(ctx, c, col, k=1.0):
    e = edge_dist(ctx)
    return mix(c, col, (e < 0.5) * k)


def no_glow(n):
    return np.zeros((n, 3))


def mat_hat(ctx):
    info = ctx.cube.info
    c = shade(ctx, T_HAT, folds=not info.get('brim'), fold_step=3, blotch=0.8, seed=1)
    if info.get('band'):                                            # лиловая лента: 2 тёмные полосы и светлый кант (референс)
        y0, y1 = ctx.cube.frm[1], ctx.cube.to[1]
        r = np.floor(ctx.L[:, 1] - y0).astype(int)
        H = int(round(y1 - y0))
        c = shade(ctx, T_LIL, folds=True, blotch=0.4, seed=11)
        if ctx.face not in ('up', 'down'):
            c = np.where(((r == 1) | ((r == H - 2) & (H >= 3)))[:, None], pick(T_LIL, np.full(ctx.n, 3)), c)
            c = np.where((r == H - 1)[:, None], pick(T_PALE, np.full(ctx.n, 1)), c)
        else:
            c = pick(T_HAT, np.full(ctx.n, 2))
    if info.get('brim'):
        r0, r1, c0, c1, w, h = rows(ctx)
        if ctx.face == 'down':
            c = pick(T_HAT, np.where(edge_dist(ctx) < 1.5, 2, 3))
        elif ctx.face == 'up':
            rr = np.maximum(np.abs(ctx.P[:, 0]), np.abs(ctx.P[:, 2]))
            b = fbm(ctx.P, 0.35, 41, 2)
            idx = np.where(rr < 5.8, 2, np.where(b > 0.6, 2, np.where(b < 0.36, 0, 1)))       # тень тульи, потёртости
            idx = np.where(edge_dist(ctx) < 0.5, 0, idx)                                      # светлый край
            c = pick(T_HAT, idx)
        else:
            c = pick(T_HAT, np.where(r1 == 0, 3, np.where(r0 == 0, 0, 2)))
    return c, 1.0, None


def mat_cross(ctx):
    c = shade(ctx, T_CROSS, folds=False)
    return c, 1.0, np.tile(hex2('#6A5A40') * 0.6, (ctx.n, 1))


def hood_hole(L):
    """Арка проёма капюшона (в координатах модели): тьма видна в этой области передней грани оболочки."""
    x, y = L[:, 0], L[:, 1]
    k = np.clip((y - 30.6) / 4.9, 0, 1)
    half = 3.3 * np.sqrt(np.clip(1 - k * k, 0, 1))                   # стрельчато-круглая арка: прямые бока, свод сверху
    return (np.abs(x) < half) & (y > 26.3)


def mat_hood(ctx):
    info = ctx.cube.info
    c = shade(ctx, T_BLU, fold_step=3, blotch=0.7, seed=2)
    c = trims(ctx, c, info, T_BLU, T_BLU)
    a = 1.0
    if info.get('shell'):
        if ctx.face == 'north':
            hole = hood_hole(ctx.L)
            a = (~hole).astype(float)
            # кант вокруг проёма: светлый ряд и тень внутри (объём края капюшона)
            x, y = ctx.L[:, 0], ctx.L[:, 1]
            near = (~hole) & hood_hole(np.stack([x * 0.82, y - 0.9, ctx.L[:, 2]], 1) * [1, 1, 1] + [0, 0, 0]) if False else None
            ring1 = (~hole) & hood_hole(np.stack([x / 1.22, y - 1.0 * (y > 32), ctx.L[:, 2]], 1))
            c = np.where(ring1[:, None], pick(T_BLU, np.full(ctx.n, 0)), c)
        elif ctx.face == 'down':
            a = 0.0
    return c, a, None


def mat_void(ctx):
    """Под капюшоном — тьма (владелец: лица нет). Передняя грань головы: почти чёрная, к краям проёма чуть светлее."""
    e = edge_dist(ctx)
    c = pick(VOID, np.where(e < 0.5, 0, 1))
    if ctx.face != 'north':
        c = pick(VOID, np.full(ctx.n, 2))
    return c, 1.0, None


def mat_skin(ctx):
    c = shade(ctx, T_SKIN, folds=False)
    if ctx.cube.info.get('hand') and ctx.face in ('north', 'south', 'east', 'west'):
        r0, r1, c0, c1, w, h = rows(ctx)
        c = mix(c, pick(T_SKIN, np.full(ctx.n, 3)), ((r1 == 0) & (c0 % 2 == 1)).astype(float))    # пальцы
    return c, 1.0, None


def mat_lilac(ctx):
    info = ctx.cube.info
    tones = T_PALE if info.get('pale') else T_LIL
    c = shade(ctx, tones, fold_step=3, blotch=0.6, seed=3)
    if info.get('cuff') and not info.get('pale') and ctx.face not in ('up', 'down'):
        # раструб: две поперечные полосы темнее (как на референсе) + строчка
        yy = np.floor(ctx.P[:, 1] + 64).astype(int)
        band = (yy % 5 == 0) | (yy % 5 == 1)
        c = np.where(band[:, None], shade(ctx, T_LIL2, fold_step=3, blotch=0.5, seed=4), c)
    if info.get('pale') and ctx.face not in ('up', 'down'):
        r0, r1, c0, c1, w, h = rows(ctx)
        c = np.where(((r0 == 0) & (c0 % 2 == 0))[:, None], pick(T_LIL, np.full(ctx.n, 2)), c)      # строчка каймы
    if info.get('cuff') and ctx.face == 'down':
        e = edge_dist(ctx)
        c = np.where((e < 0.6)[:, None], pick(T_LIL, np.full(ctx.n, 3)), pick(VOID, np.full(ctx.n, 0)))   # тёмный проём раструба
    c = trims(ctx, c, info, tones, T_PALE)
    return c, 1.0, None


def mat_gg(ctx):
    c = shade(ctx, T_GG, fold_step=3, fold_phase=1, blotch=0.9, seed=5)
    c = trims(ctx, c, ctx.cube.info, T_GG, T_LIL)
    return c, 1.0, None


def mat_boot(ctx):
    c = shade(ctx, T_LIL if ctx.cube.info.get('cuff') else T_BOOT, folds=False, blotch=0.4, seed=8)
    return c, 1.0, None


def ribbon_alpha(ctx):
    """Нижний сегмент ленты: хвост с вырезом (центральный пиксель нижнего ряда прозрачный)."""
    a = np.ones(ctx.n)
    if ctx.cube.info.get('tip') and ctx.face in ('north', 'south', 'east', 'west'):
        r0, r1, c0, c1, w, h = rows(ctx)
        if w >= 2:
            mid = np.abs(c0 - c1) <= 1
            a = np.where((r1 == 0) & mid, 0.0, 1.0)
    return a


def mat_ribbon(ctx):
    kind = ctx.cube.info.get('kind', 'lil')
    tones = {'gg': T_GG, 'lil_l': T_LIL, 'lil': T_LIL2}[kind]
    c = shade(ctx, tones, folds=False, blotch=0.7 if kind == 'gg' else 0.5, seed=6)
    r0, r1, c0, c1, w, h = rows(ctx)
    if w >= 2 and ctx.face in ('north', 'south'):
        edge = (c0 == 0) | (c1 == 0)
        c = mix(c, pick(tones, np.full(ctx.n, 2)), edge.astype(float))                     # кромка ленты
        yy = np.floor(ctx.P[:, 1] + 64).astype(int)
        if kind != 'gg':
            dot = (np.abs(c0 - c1) <= 1) & (yy % 4 == 0) & (r1 > 0)                       # пиксельные ромбики по середине
            c = mix(c, pick(tones, np.full(ctx.n, 0 if kind == 'lil' else 3)), dot.astype(float))
        else:
            st = (np.abs(c0 - c1) <= 1) & (yy % 3 == 0) & (r1 > 0)                        # лиловая строчка по серо-зелёному
            c = mix(c, pick(T_LIL, np.full(ctx.n, 2)), st.astype(float))
        c = np.where(((r1 == 1) & (h >= 4))[:, None], pick(T_PALE if kind != 'gg' else T_LIL, np.full(ctx.n, 2)), c)   # кайма у хвоста
    return c, ribbon_alpha(ctx), None


def mat_thread(ctx):
    c = shade(ctx, T_RED, folds=False, rim=False)
    return c, 1.0, np.clip(c * 0.8, 0, 1)


def mat_gold(ctx):
    return shade(ctx, T_GOLD, folds=False), 1.0, None


def mat_dark(ctx):
    return pick(VOID, np.full(ctx.n, 0)), 1.0, None


# ================================================================== построение
def build():
    m = IModel('irina', density=1, tex_w=128)
    m.materials.update(hat=mat_hat, cross=mat_cross, hood=mat_hood, void=mat_void, skin=mat_skin, lilac=mat_lilac,
                       gg=mat_gg, boot=mat_boot, ribbon=mat_ribbon, thread=mat_thread, gold=mat_gold, dark=mat_dark)
    HIP, SH, NECK = 14.0, 25.0, 27.0
    # ---- корень и тело — каркас мага Iron's (abstract_casting_mob), как у Главы Культа
    m.bone('body', None, (0, HIP, 0))
    m.bone('torso', 'body', (0, NECK, 0))
    m.box('torso', (-4.0, 14.0, -2.0), (4.0, 27.0, 2.0), 'gg', seam=True)                      # торс (8×13×4, как у мага Iron's)
    m.box('torso', (-4.25, 14.2, -2.25), (4.25, 16.4, 2.25), 'lilac', trim=True)               # кушак
    m.box('torso', (-1.3, 14.0, 2.2), (1.3, 17.0, 3.3), 'lilac', trim=True)                    # бант на спине
    # широкая наплечная накидка (серо-зелёная), поверх неё лиловые лоскуты — плечи шире, как на референсе
    m.box('torso', (-6.6, 23.2, -3.0), (6.6, 27.2, 3.0), 'gg', hem=True)
    m.bone('mantle', 'torso', (0, 27.2, 0))
    for k in range(12):
        a = TAU * (k + 0.5) / 12
        top = np.array([math.sin(a) * 5.4, 26.6, -math.cos(a) * 2.8])
        bot = np.array([math.sin(a) * 7.6, 19.6 + (k % 2) * 1.2, -math.cos(a) * 4.2])
        m.rod('mantle', top, bot, 3.0, 0.6, 'ribbon', roll=-math.degrees(a), kind=('gg', 'lil_l', 'gg', 'lil')[k % 4], tip=True)
    # брошь на воротнике
    m.cbox('torso', (0, 26.2, -3.35), (1.6, 1.6, 0.6), 'gold')
    m.cbox('torso', (0, 26.2, -3.7), (0.8, 0.8, 0.3), 'thread')
    # завязки — лиловые ленты от броши до колен
    for side, sn in ((1, 'r'), (-1, 'l')):
        p0 = np.array([side * 0.9, 25.6, -3.3])
        p1 = np.array([side * 1.7, 17.4, -3.4])
        p2 = np.array([side * 2.4, 7.6, -5.6])
        m.bone('tie_' + sn, 'torso', p0)
        m.rod('tie_' + sn, p0, p1, 2.0, 0.6, 'ribbon', kind='lil_l', ext=0.05)
        m.bone('tie_%s_b' % sn, 'tie_' + sn, p1)
        m.rod('tie_%s_b' % sn, p1, p2, 2.0, 0.6, 'ribbon', kind='lil_l', tip=True)
    for side, sn in ((1, 'r'), (-1, 'l')):
        p0 = np.array([side * 0.8, 15.4, 3.2])
        p1 = np.array([side * 1.8, 7.6, 4.8])
        m.bone('sash_' + sn, 'torso', p0)
        m.rod('sash_' + sn, p0, p1, 2.0, 0.6, 'ribbon', kind='lil', tip=True)

    # ---- голова: тёмный куб + цельный капюшон-оболочка поверх (проём арки вырезан альфой в передней грани)
    m.bone('head', 'body', (0, NECK, 0))
    m.box('head', (-4.0, NECK, -4.0), (4.0, NECK + 8, 4.0), 'void')
    m.bone('hood', 'head', (0, 35.0, 0))
    m.box('hood', (-5.0, 26.2, -4.8), (5.0, 36.6, 5.0), 'hood', shell=True)                     # оболочка вокруг головы
    m.box('hood', (-3.6, 36.4, -3.6), (3.6, 37.4, 4.4), 'hood')                                 # макушка (объём под шляпой)
    m.box('hood', (-6.2, 24.4, -4.4), (6.2, 27.4, 4.8), 'hood', hem=True)                       # капюшон спадает на плечи
    m.bone('hood_drape', 'hood', (0, 26.0, 4.6))
    m.rod('hood_drape', (0, 26.0, 4.6), (0, 18.0, 5.6), 8.4, 1.0, 'hood', hem=True)            # хвост капюшона на спине

    # ---- шляпа: толстые широкие поля (свисают на капюшон), тулья наклонена набок, крупный светлый крест
    m.bone('hat', 'head', (0, 37.2, 0), rot=(-6, 0, 9))
    m.bone('hat_brim', 'hat', (0, 37.2, 0))
    m.cbox('hat_brim', (0, 38.0, 0), (17.0, 2.0, 17.0), 'hat', brim=True)
    for k in range(4):                                                                         # свисающие края полей
        a = TAU * k / 4
        cx, cz = math.sin(a) * 10.2, -math.cos(a) * 10.2
        m.cbox('hat_brim', (cx, 37.4, cz), (23.0 if k % 2 == 0 else 3.6, 1.8, 3.6 if k % 2 == 0 else 23.0) if False else
               ((21.6, 1.8, 3.8) if k % 2 == 0 else (3.8, 1.8, 21.6)), 'hat', brim=True,
               rot=((14 if k == 0 else -14 if k == 2 else 0), 0, (14 if k == 3 else -14 if k == 1 else 0)), pivot=[cx * 0.85, 37.9, cz * 0.85])
    m.bone('hat_crown', 'hat', (0, 39.0, 0), rot=(0, 0, 6))
    m.cbox('hat_crown', (0, 40.5, 0), (10.0, 3.0, 10.0), 'hat', band=True)
    m.cbox('hat_crown', (0.3, 43.6, 0), (9.2, 3.2, 9.2), 'hat')
    m.cbox('hat_crown', (0.6, 46.1, 0), (9.4, 1.8, 9.4), 'hat', band=True)
    m.bone('hat_tip', 'hat_crown', (0.6, 47.0, 0), rot=(-8, 0, -18))
    m.cbox('hat_tip', (0.6, 50.6, 0.3), (8.4, 7.2, 8.4), 'hat')
    m.box('hat_tip', (-0.1, 47.6, -4.05), (1.3, 54.2, -3.6), 'cross')                           # крест: вертикаль 1.4×6.6
    m.box('hat_tip', (-1.7, 51.2, -4.05), (2.9, 52.6, -3.6), 'cross')                           # перекладина 4.6
    m.box('hat_tip', (4.75, 49.2, -1.8), (4.9, 50.4, 2.2), 'dark')                              # тёмная прорезь сбоку
    m.bone('hat_tip2', 'hat_tip', (0.8, 54.2, 0.6), rot=(-12, 0, -16))
    m.cbox('hat_tip2', (1.0, 55.4, 0.6), (6.2, 2.6, 6.2), 'hat')
    m.bone('hat_tip3', 'hat_tip2', (1.2, 56.6, 0.8), rot=(-10, 0, -22))
    m.cbox('hat_tip3', (1.4, 57.3, 0.8), (3.6, 1.6, 3.6), 'hat')

    # ---- руки: лиловые рукава ОТ ПЛЕЧА, книзу массивный раструб; бледные кисти; кости предметов как у Iron's
    for side, sn in ((1, 'right'), (-1, 'left')):
        arm = sn + '_arm'
        m.bone(arm, 'body', (side * 5, SH, 0))
        xa = (4.0, 8.0) if side > 0 else (-8.0, -4.0)
        m.box(arm, (xa[0], 15.0, -2.0), (xa[1], 25.6, 2.0), 'lilac', seam=True)                # рукав от плеча
        sl = 'sleeve_' + sn[0]
        m.bone(sl, arm, (side * 6.0, 16.6, 0))
        x2 = (2.5, 9.5) if side > 0 else (-9.5, -2.5)
        m.box(sl, (x2[0], 9.4, -3.6), (x2[1], 16.8, 3.6), 'lilac', cuff=True, hem=True)        # один массивный раструб с каймой
        xh = (4.9, 7.1) if side > 0 else (-7.1, -4.9)
        m.box(arm, (xh[0], 9.4, -1.1), (xh[1], 12.6, 1.1), 'skin', hand=True)
        if side > 0:
            m.bone('bipedHandRight', arm, (6, 10.6, -0.6))
            m.bone('rightItem', arm, (6, 10.0, 0), rot=(90, 0, 0))
        else:
            m.bone('bipedHandLeft', arm, (-6, 10.6, -0.6))
            m.bone('leftItem', 'bipedHandLeft', (-6, 10.0, 0))

    # ---- ноги (под юбкой; видны сапоги)
    for side, sn in ((1, 'right'), (-1, 'left')):
        leg = sn + '_leg'
        m.bone(leg, 'body', (side * 2, HIP, 0))
        xl = (0.0, 4.0) if side > 0 else (-4.0, 0.0)
        m.box(leg, (xl[0], 3.0, -2.0), (xl[1], 14.0, 2.0), 'boot')
        xb = (-0.2, 4.2) if side > 0 else (-4.2, 0.2)
        m.box(leg, (xb[0], 0.0, -2.6), (xb[1], 4.0, 2.2), 'boot')
        m.box(leg, (xb[0] - 0.2, 3.4, -2.8), (xb[1] + 0.2, 4.6, 2.4), 'boot', cuff=True)

    # ---- юбка: колокол, расходится книзу, + 20 лент-лоскутов (по 2 сегмента — качаются)
    m.bone('skirt', 'body', (0, 15.5, 0))
    for (y0, y1, sx, sz) in ((10.0, 15.8, 9.8, 6.2), (3.0, 10.2, 13.2, 9.0)):
        m.cbox('skirt', (0, (y0 + y1) / 2, 0), (sx, y1 - y0, sz), 'gg', hem=True)
        m.cbox('skirt', (0, (y0 + y1) / 2, 0), (sx * 0.78, y1 - y0, sz * 1.18), 'gg', hem=True)
    N = 20
    kinds = ('lil_l', 'gg', 'lil', 'gg', 'gg', 'lil_l', 'gg', 'lil')
    for k in range(N):
        a = TAU * (k + 0.5) / N
        front = -math.cos(a)
        top = np.array([math.sin(a) * 5.4, 15.6, -math.cos(a) * 3.6])
        end_y = 1.4 + 1.6 * max(0.0, front) ** 2 - 1.0 * max(0.0, -front) + (k % 3 - 1) * 0.9
        rad = 8.6 + 0.8 * (k % 2)
        bot = np.array([math.sin(a) * rad, end_y, -math.cos(a) * rad * 0.8])
        mid = top + (bot - top) * 0.5
        w = 3.0 + 0.6 * ((k * 7) % 3) / 2
        kind = kinds[k % len(kinds)]
        bn = 'rib_%02d' % k
        m.bone(bn, 'skirt', top)
        m.rod(bn, top, mid, w, 0.6, 'ribbon', roll=-math.degrees(a), kind=kind, ext=0.1)
        m.bone(bn + '_b', bn, mid)
        m.rod(bn + '_b', mid, bot, w * 0.95, 0.6, 'ribbon', roll=-math.degrees(a), kind=kind, tip=True)

    # ---- красные нити: тонкие (1 тексель) тёмно-красные ленты плавными петлями, рваные, с разрывами
    m.bone('threads', 'body', (0, HIP, 0))
    specs = [('thread_a', 24.0, 13.0, (22, 0, 8), 300, 0.0), ('thread_b', 11.0, 11.5, (-12, 0, -24), 260, 1.7),
             ('thread_c', 36.0, 14.0, (-18, 0, 14), 240, 3.4)]
    for si, (name, yc, R, rot, span, start) in enumerate(specs):
        m.bone(name, 'threads', (0, yc, 0), rot=rot)
        n = int(span / 6)
        pts = []
        for i in range(n + 1):
            ang = start + math.radians(span) * i / n
            wob = 0.8 * math.sin(ang * 2 + yc)
            pts.append(np.array([math.cos(ang) * (R + wob), yc + 1.4 * math.sin(ang * 1.5 + R), math.sin(ang) * (R + wob)]))
        for i in range(n):
            if (i + si * 3) % 9 in (4, 7):                     # разрывы — нить рваная
                continue
            m.rod(name, pts[i], pts[i + 1], 0.8, 0.8, 'thread', ext=0.05)
    m.bone('thread_bits', 'threads', (0, 20, 0))
    rng = np.random.RandomState(27)
    for i in range(10):
        a = rng.uniform(0, TAU)
        r = rng.uniform(8, 13)
        p = np.array([math.cos(a) * r, rng.uniform(6, 36), math.sin(a) * r])
        m.cbox('thread_bits', p, (0.8, 0.8, 0.8), 'thread', rot=(rng.uniform(0, 45), rng.uniform(0, 45), 0), pivot=list(p))
    return m


# ================================================================== анимации
def ease_io(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def env(t, a, b, c=None, d=None):
    """Огибающая: 0 до a, рост к 1 к b, держится до c, спад к 0 к d."""
    if t <= a:
        return 0.0
    if t < b:
        return ease_io((t - a) / (b - a))
    if c is None or t <= c:
        return 1.0
    if t < d:
        return 1 - ease_io((t - c) / (d - c))
    return 0.0


def lerp3(a, b, k):
    return [a[i] + (b[i] - a[i]) * k for i in range(3)]


def keys_track(t, keys):
    """keys: [(t, value_list)], плавная интерполяция (smoothstep) между ключами."""
    if t <= keys[0][0]:
        return list(keys[0][1])
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            return lerp3(v0, v1, ease_io((t - t0) / (t1 - t0))) if len(v0) == 3 else v0
    return list(keys[-1][1])


RIBS = ['rib_%02d' % k for k in range(20)]
STAFF_HOLD = {'right_arm': [12, 0, 4]}           # поза хвата посоха: предплечье чуть вперёд


def body_bones():
    return ['body', 'torso', 'head', 'hat', 'right_arm', 'left_arm', 'right_leg', 'left_leg']


def pose_mix(*poses):
    out = {}
    for p in poses:
        for b, ch in p.items():
            o = out.setdefault(b, {})
            for k, v in ch.items():
                if k in o and k != 'scale':
                    o[k] = [o[k][i] + v[i] for i in range(3)]
                else:
                    o[k] = list(v)
    return out


def idle_pose(t, per=4.0):
    br = math.sin(t * TAU / per)
    return {'body': {'pos': [0, br * 0.25, 0]}, 'torso': {'rot': [br * 1.2, 0, 0]},
            'head': {'rot': [-3 + br * 1.5, 6 * math.sin(t * TAU / (per * 2)), 4]}, 'hat': {'rot': [0, 0, 0]},
            'right_arm': {'rot': [4 + br * 2, 0, 9]}, 'left_arm': {'rot': [-36 - br * 2, 22, -4 - br * 2]},
            'right_leg': {'rot': [0, 0, 0]}, 'left_leg': {'rot': [0, 0, 0]}}


def cloth_pose(t, wind=0.0, amp=1.0, per=4.0, swirl=1.0, thr_r=1.0, walk=None):
    """Ленты/рукава/волосы/шляпа/нити. wind — наклон назад (градусы), amp — сила качания, swirl — скорость нитей."""
    o = {}
    for k, bn in enumerate(RIBS):
        a = TAU * (k + 0.5) / 20
        ph = t * TAU / per + k * 0.7
        sw = math.sin(ph) * 3.0 * amp
        tw = math.sin(ph * 0.5 + k) * 4 * amp
        front = -math.cos(a)
        wx = wind * front * 0.7 + (walk[0] * front * 1.0 if walk else 0)
        o[bn] = {'rot': [sw * front + wx, tw * 0.3, sw * math.sin(a) * 0.8]}
        o[bn + '_b'] = {'rot': [math.sin(ph - 0.9) * 5 * amp + wind * 0.4 * front, 0, math.sin(ph - 0.9) * 3 * amp * math.sin(a)]}
    for sn in 'rl':
        s = 1 if sn == 'r' else -1
        o['sleeve_' + sn] = {'rot': [math.sin(t * TAU / per + s) * 3 * amp + wind * 0.3, 0, s * math.sin(t * TAU / per * 0.5) * 2 * amp]}
        o['tie_' + sn] = {'rot': [math.sin(t * TAU / per + s * 0.5) * 6 * amp - wind * 0.5, 0, s * 3]}
        o['tie_%s_b' % sn] = {'rot': [math.sin(t * TAU / per + s * 0.5 - 1) * 8 * amp - wind * 0.3, 0, 0]}
        o['sash_' + sn] = {'rot': [math.sin(t * TAU / per * 1.3 + s) * 8 * amp + wind, 0, s * (6 + 3 * math.sin(t * TAU / per))]}
    o['hat_tip'] = {'rot': [math.sin(t * TAU / per) * 3 * amp + wind * 0.3, 0, math.sin(t * TAU / per * 0.5) * 4 * amp]}
    o['hat_tip2'] = {'rot': [math.sin(t * TAU / per - 0.6) * 4 * amp, 0, math.sin(t * TAU / per * 0.5 - 0.6) * 5 * amp]}
    o['hat_tip3'] = {'rot': [math.sin(t * TAU / per - 1.2) * 6 * amp, 0, 0]}
    o['hood_drape'] = {'rot': [math.sin(t * TAU / per + 1) * 2 * amp + wind * 0.4, 0, 0]}
    for k in range(10):
        pass
    o['mantle'] = {'rot': [0, 0, 0]}
    # нити: вращение вокруг вертикали (знак и скорость свои), лёгкое «дыхание» радиуса
    L = per
    o['thread_a'] = {'rot': [0, -360 * t / L * swirl, 0], 'scale': [thr_r] * 3}
    o['thread_b'] = {'rot': [0, 360 * t / L * swirl, 0], 'scale': [thr_r] * 3}
    o['thread_c'] = {'rot': [0, -720 * t / L * swirl, 0], 'scale': [thr_r] * 3}
    o['thread_bits'] = {'rot': [0, 360 * t / L * swirl * 0.5, 0], 'pos': [0, math.sin(t * TAU / L) * 0.6, 0]}
    o['threads'] = {'pos': [0, math.sin(t * TAU / L * 2) * 0.4, 0]}
    return o


def anims():
    out = []

    def mk(name, length, fn, loop=False, dt=0.05, events=None):
        a = Anim(name, length, loop=loop)
        a.sample(fn, dt)
        for tt, ev in (events or {}).items():
            a.instruction(tt, ev)
        out.append(a)
        return a

    # ---------------- контроллер «тело» (body/torso/head/hat/руки/ноги)
    mk('irina_idle', 4.0, lambda t: idle_pose(t), loop=True)

    def walk(t):
        ph = t / 1.2 * TAU
        s = math.sin(ph)
        p = {'body': {'pos': [0, abs(math.cos(ph)) * 0.5, 0], 'rot': [0, s * 4, 0]}, 'torso': {'rot': [3, -s * 3, 0]},
             'head': {'rot': [-2, s * 2, 3]}, 'hat': {'rot': [0, 0, 0]},
             'right_arm': {'rot': [16 - s * 6, 0, 6]}, 'left_arm': {'rot': [s * 22, 0, -10]},
             'right_leg': {'rot': [s * 26, 0, 0]}, 'left_leg': {'rot': [-s * 26, 0, 0]}}
        return p
    mk('irina_walk', 1.2, walk, loop=True)

    def cast_short(t):
        e = env(t, 0.0, 0.25, 0.45, 0.8)
        p = idle_pose(t)
        return pose_mix(p, {'torso': {'rot': [-4 * e, 18 * e, 0]}, 'head': {'rot': [-4 * e, 10 * e, 0]},
                            'left_arm': {'rot': [-70 * e, -20 * e, 18 * e]}, 'right_arm': {'rot': [-30 * e, 0, 8 * e]}})
    mk('irina_cast_short', 0.8, cast_short, dt=0.025, events={0.35: 'cast'})

    def cast_long(t):
        ph = t / 2.0 * TAU
        p = idle_pose(t)
        return pose_mix(p, {'torso': {'rot': [-6, 0, 0]}, 'head': {'rot': [-8, 0, 0]},
                            'right_arm': {'rot': [-98 + math.sin(ph) * 4, -10, 10]},
                            'left_arm': {'rot': [-60 + math.sin(ph) * 12, 30 + math.cos(ph) * 18, -24 + math.sin(ph * 2) * 6]}})
    mk('irina_cast_long', 2.0, cast_long, loop=True)

    def cast_long_end(t):
        e = 1 - env(t, 0.0, 0.5)
        return pose_mix(idle_pose(t), {'right_arm': {'rot': [-112 * e, -10 * e, 4 * e]}, 'left_arm': {'rot': [-40 * e, 30 * e, -10 * e]}})
    mk('irina_cast_long_end', 0.5, cast_long_end, dt=0.025)

    def staff_attack(t):
        # замах посохом через плечо и косой удар крюком вниз-вперёд
        wind = env(t, 0.0, 0.35, 0.4, 0.55)
        hit = env(t, 0.4, 0.58, 0.75, 1.2)
        p = idle_pose(t)
        return pose_mix(p, {'body': {'rot': [0, -24 * wind + 30 * hit, 0], 'pos': [0, -0.6 * hit, -1.2 * hit]},
                            'torso': {'rot': [10 * wind - 18 * hit, -10 * wind + 14 * hit, 0]},
                            'right_arm': {'rot': [-160 * wind + 70 * hit * (1 - wind), -20 * wind + 30 * hit, 20 * wind - 10 * hit]},
                            'left_arm': {'rot': [-20 * wind - 40 * hit, 0, -30 * hit]},
                            'right_leg': {'rot': [-20 * hit, 0, 0]}, 'left_leg': {'rot': [16 * hit, 0, 0]},
                            'head': {'rot': [6 * wind - 8 * hit, 12 * wind - 14 * hit, 0]}})
    mk('irina_staff_attack', 1.2, staff_attack, dt=0.025, events={0.55: 'hit'})

    def staff_sweep(t):
        # горизонтальный взмах крюком (по площади вокруг)
        w = env(t, 0.0, 0.3)
        s = env(t, 0.32, 0.6, 0.7, 1.0)
        p = idle_pose(t)
        return pose_mix(p, {'body': {'rot': [0, 40 * w - 120 * s * w + 0 * s, 0]},
                            'torso': {'rot': [6 * w, 0, 0]},
                            'right_arm': {'rot': [-80 * w + 10 * s, 60 * w - 110 * s, 30 * w]},
                            'left_arm': {'rot': [-20 * w, 0, -40 * w]}, 'head': {'rot': [0, -20 * w + 30 * s, 0]}})
    mk('irina_staff_sweep', 1.0, staff_sweep, dt=0.025, events={0.46: 'hit'})

    def mark(t):
        # «Предмет ревности»: склоняет голову, указывает пальцем на цель, шляпу придерживает посохом
        e = env(t, 0.0, 0.45, 1.0, 1.4)
        p = idle_pose(t)
        return pose_mix(p, {'head': {'rot': [-6 * e, 14 * e, 14 * e]}, 'torso': {'rot': [0, 20 * e, 0]},
                            'left_arm': {'rot': [-84 * e, -18 * e, 6 * e]}, 'right_arm': {'rot': [-30 * e, 0, 10 * e]}})
    mk('irina_mark', 1.4, mark, dt=0.025, events={0.7: 'mark'})

    def bind(t):
        # «Красные нити»: руки скрещиваются у груди, затем разводятся — нити связывают пары
        c = env(t, 0.0, 0.5, 0.75, 1.0)
        o = env(t, 0.8, 1.05, 1.3, 1.6)
        p = idle_pose(t)
        return pose_mix(p, {'right_arm': {'rot': [-70 * c - 50 * o, -40 * c + 40 * o, -30 * c + 50 * o]},
                            'left_arm': {'rot': [-70 * c - 50 * o, 40 * c - 40 * o, 30 * c - 50 * o]},
                            'torso': {'rot': [8 * c - 10 * o, 0, 0]}, 'head': {'rot': [10 * c - 12 * o, 0, 0]},
                            'body': {'pos': [0, -0.5 * c + 0.3 * o, 0]}})
    mk('irina_bind', 1.6, bind, dt=0.025, events={0.9: 'bind'})

    def whip(t):
        # фаза 3: нити хлещут — резкий взмах обеих рук наружу
        w = env(t, 0.0, 0.3)
        s = env(t, 0.32, 0.45, 0.6, 1.0)
        p = idle_pose(t)
        return pose_mix(p, {'right_arm': {'rot': [-60 * w + 40 * s, 30 * w, 30 * w + 60 * s]},
                            'left_arm': {'rot': [-60 * w + 40 * s, -30 * w, -30 * w - 60 * s]},
                            'torso': {'rot': [12 * w - 22 * s, 0, 0]}, 'head': {'rot': [10 * w - 16 * s, 0, 0]},
                            'body': {'pos': [0, -0.8 * w + 0.6 * s, 0]}})
    mk('irina_whip', 1.0, whip, dt=0.025, events={0.45: 'lash'})

    def steal(t):
        # кража эффектов: руки раскрыты к игрокам, затем сжимаются к груди (свет стягивается к ней)
        o = env(t, 0.0, 0.3, 0.8, 1.1)
        c = env(t, 0.85, 1.2, 1.3, 1.5)
        p = idle_pose(t)
        return pose_mix(p, {'right_arm': {'rot': [-60 * o - 50 * c, 40 * o - 50 * c, 40 * o - 20 * c]},
                            'left_arm': {'rot': [-60 * o - 50 * c, -40 * o + 50 * c, -40 * o + 20 * c]},
                            'torso': {'rot': [-8 * o + 12 * c, 0, 0]}, 'head': {'rot': [-12 * o + 16 * c, 0, 0]}})
    mk('irina_steal', 1.5, steal, dt=0.025, events={0.3: 'pull', 1.2: 'absorb'})

    def happiness(t):
        # «Чужое счастье» (6 с): поднимается над землёй, руки широко, нити разворачиваются; с 3.6 — стягивает свет к груди; 5.2 — вспышка
        rise = env(t, 0.3, 1.6, 5.2, 6.0)
        spread = env(t, 0.5, 1.4, 3.4, 4.0)
        clutch = env(t, 3.6, 4.4, 5.2, 6.0)
        sway = math.sin(t * 2.2) * spread
        p = idle_pose(t)
        return pose_mix(p, {'body': {'pos': [0, 6 * rise, 0], 'rot': [0, sway * 4, 0]},
                            'torso': {'rot': [-14 * spread + 16 * clutch, 0, 0]}, 'head': {'rot': [-26 * spread + 22 * clutch, 0, 0]},
                            'right_arm': {'rot': [-30 * spread - 90 * clutch, 0, 80 * spread - 40 * clutch]},
                            'left_arm': {'rot': [-30 * spread - 90 * clutch, 0, -80 * spread + 40 * clutch]},
                            'right_leg': {'rot': [-10 * rise, 0, 4 * rise]}, 'left_leg': {'rot': [14 * rise, 0, -4 * rise]}})
    mk('irina_others_happiness', 6.0, happiness, events={0.0: 'begin', 1.4: 'spread', 3.6: 'gather', 5.2: 'absorb', 6.0: 'end'})

    def only_mine(t):
        # «Только мой» (6.2 с): тянется к жертве (0.6), рывок к себе (1.0), обнимает кокон (1.6–5.4), сжимает (5.4)
        reach = env(t, 0.1, 0.6, 0.8, 1.1)
        yank = env(t, 0.8, 1.1, 1.3, 1.7)
        hug = env(t, 1.4, 1.9, 5.3, 5.5)
        crush = env(t, 5.3, 5.5, 5.8, 6.2)
        breathe = math.sin(t * 3) * hug
        p = idle_pose(t)
        return pose_mix(p, {'body': {'pos': [0, 0, -1.2 * reach + 1.0 * yank], 'rot': [0, 0, 0]},
                            'torso': {'rot': [-10 * reach + 16 * yank + 6 * hug + 4 * breathe - 10 * crush, 0, 0]},
                            'head': {'rot': [-6 * reach + 10 * hug + 8 * crush, 0, 16 * hug]},
                            'left_arm': {'rot': [-95 * reach - 30 * yank + (-60) * hug - 20 * crush, 10 * reach + 40 * hug, -6 * reach + 30 * hug]},
                            'right_arm': {'rot': [-20 * reach - 50 * hug - 20 * crush, 0, 10 * reach - 20 * hug]},
                            'right_leg': {'rot': [-14 * reach, 0, 0]}, 'left_leg': {'rot': [10 * reach, 0, 0]}})
    mk('irina_only_mine', 6.2, only_mine, events={0.6: 'reach', 1.0: 'yank', 1.6: 'cocoon', 5.4: 'crush', 6.2: 'end'})

    def only_mine_broken(t):
        # кокон разорван союзниками: отшатывается, хватается за шляпу
        s = env(t, 0.0, 0.15, 0.5, 1.2)
        p = idle_pose(t)
        return pose_mix(p, {'body': {'pos': [0, 0, 2.0 * s], 'rot': [0, 0, 0]}, 'torso': {'rot': [18 * s, 0, 6 * s]},
                            'head': {'rot': [20 * s, 0, -10 * s]}, 'hat': {'rot': [-10 * s, 0, 8 * s]},
                            'left_arm': {'rot': [-150 * s, 0, -10 * s]}, 'right_arm': {'rot': [-10 * s, 0, 30 * s]}})
    mk('irina_only_mine_broken', 1.2, only_mine_broken, dt=0.025, events={0.0: 'broken'})

    def phase2(t):
        # переход 66%: тянет поля шляпы вниз (тень на глаза), затем резко поднимает голову — нити расходятся
        d = env(t, 0.0, 0.6, 1.2, 1.5)
        u = env(t, 1.3, 1.6, 2.1, 2.5)
        p = idle_pose(t)
        return pose_mix(p, {'head': {'rot': [16 * d - 18 * u, 0, 0]}, 'hat': {'rot': [10 * d - 6 * u, 0, 0]},
                            'left_arm': {'rot': [-150 * d - 30 * u * 0, 0, -20 * d]}, 'right_arm': {'rot': [-20 * u, 0, 40 * u]},
                            'torso': {'rot': [8 * d - 10 * u, 0, 0]}})
    mk('irina_phase2', 2.5, phase2, events={1.45: 'burst'})

    def phase3(t):
        # переход 33%: ярость — запрокидывает голову, руки в стороны и вниз, шляпа съезжает набок
        r = env(t, 0.2, 0.9, 2.3, 3.0)
        sh = math.sin(t * 40) * env(t, 1.2, 1.4, 2.0, 2.3)
        p = idle_pose(t)
        return pose_mix(p, {'head': {'rot': [-30 * r, 0, sh * 3]}, 'hat': {'rot': [-6 * r, 0, -14 * r]},
                            'torso': {'rot': [-12 * r, 0, sh]}, 'body': {'pos': [0, 1.0 * r, 0]},
                            'right_arm': {'rot': [10 * r, 0, 70 * r]}, 'left_arm': {'rot': [10 * r, 0, -70 * r]},
                            'right_leg': {'rot': [0, 0, 6 * r]}, 'left_leg': {'rot': [0, 0, -6 * r]}})
    mk('irina_phase3', 3.0, phase3, events={1.3: 'rage'})

    def finisher(t):
        # добивание (2.6 с): нити опутывают жертву (0.2), подтягивает к себе (0.8), «только мой» — обнимает левой рукой,
        # крюком посоха пронзает (1.3), шепчет (1.7), отпускает (2.2 — kill)
        grab = env(t, 0.0, 0.3, 0.6, 0.8)
        hold = env(t, 0.7, 0.9, 2.1, 2.5)
        raise_ = env(t, 0.9, 1.15, 1.2, 1.3)
        stab = env(t, 1.2, 1.32, 1.9, 2.3)
        p = idle_pose(t)
        return pose_mix(p, {'body': {'pos': [0, 0, -0.8 * hold]},
                            'torso': {'rot': [-6 * grab + 10 * stab, 0, 0]},
                            'head': {'rot': [12 * hold, -10 * hold, 18 * hold]},
                            'left_arm': {'rot': [-80 * grab - 60 * hold, 20 * hold, 30 * hold]},
                            'right_arm': {'rot': [-150 * raise_ * (1 - stab) - 70 * stab, 10 * stab, 20 * raise_]}})
    mk('irina_finisher', 2.6, finisher, dt=0.025, events={0.2: 'wrap', 0.8: 'pull_done', 1.3: 'pierce', 1.7: 'whisper', 2.2: 'kill'})

    def spawn(t):
        # появление (7 с): кокон из нитей у земли (0–2.6) — она внутри, свернувшись; 2.6 нити расплетаются; поднимается (2.6–4.4);
        # 4.6 — поправляет шляпу (поза); 5.4 — взмах посохом, нити расходятся кольцом; 7.0 — бой
        curl = 1 - env(t, 2.6, 4.2)
        hatfix = env(t, 4.4, 4.8, 5.0, 5.4)
        flourish = env(t, 5.2, 5.6, 6.2, 7.0)
        p = idle_pose(t)
        return pose_mix(p, {'body': {'pos': [0, -9 * curl, 0]}, 'torso': {'rot': [40 * curl, 0, 0]},
                            'head': {'rot': [30 * curl - 6 * hatfix, 0, 0]}, 'hat': {'rot': [0, 0, -4 * hatfix]},
                            'right_arm': {'rot': [-40 * curl - 50 * flourish, 0, -10 * curl + 50 * flourish]},
                            'left_arm': {'rot': [-40 * curl - 150 * hatfix, 0, 10 * curl - 10 * hatfix]},
                            'right_leg': {'rot': [-80 * curl, 0, 0]}, 'left_leg': {'rot': [-80 * curl, 0, 0]}})
    mk('irina_spawn', 7.0, spawn, events={0.0: 'cocoon', 2.6: 'unravel', 4.6: 'pose', 5.4: 'flourish', 7.0: 'ready'})

    def death(t):
        # смерть (5 с): удар (0–0.6), шатается, опускается на колени (1.6), шляпа падает (2.4), тянется к шляпе, ложится на бок (3.4–4.2)
        hit = env(t, 0.0, 0.2, 0.4, 0.9)
        knee = env(t, 0.9, 1.6)
        fall = env(t, 3.2, 4.2)
        hatf = env(t, 2.3, 2.9)
        reach = env(t, 2.7, 3.2, 3.6, 4.4)
        p = idle_pose(t * 0.3)
        return pose_mix(p, {'body': {'pos': [0, -5.5 * knee - 4.5 * fall, 1.2 * hit + 4 * fall], 'rot': [-6 * hit, 0, 74 * fall]},
                            'torso': {'rot': [16 * knee - 10 * fall, 0, 0]}, 'head': {'rot': [22 * knee - 10 * fall, 0, -10 * fall]},
                            'hat': {'rot': [40 * hatf, 0, 50 * hatf], 'pos': [6 * hatf, -14 * hatf, -8 * hatf]},
                            'right_arm': {'rot': [10 * hit - 20 * knee, 0, 20 * knee - 10 * fall]},
                            'left_arm': {'rot': [-60 * reach, 20 * reach, -10 * knee]},
                            'right_leg': {'rot': [-80 * knee + 40 * fall, 0, 0]}, 'left_leg': {'rot': [-80 * knee + 30 * fall, 0, 0]}})
    a = mk('irina_death', 5.0, death, events={0.0: 'hit', 1.6: 'knees', 2.4: 'hat', 3.4: 'fall', 4.2: 'unravel', 5.0: 'gone'})
    a.loop = 'hold'

    # ---------------- контроллер «ткань и нити» (ленты, рукава, волосы, кончик шляпы, нити)
    mk('irina_cloth_idle', 4.0, lambda t: cloth_pose(t, per=4.0), loop=True)
    mk('irina_cloth_walk', 1.2, lambda t: cloth_pose(t, wind=10, amp=1.4, per=1.2, swirl=0.4,
                                                    walk=(math.sin(t / 1.2 * TAU) * 8,)), loop=True)
    mk('irina_cloth_storm', 2.0, lambda t: cloth_pose(t, wind=18, amp=2.6, per=1.0, swirl=1.0 / 1.0, thr_r=1.25), loop=True)

    def cloth_spawn(t):
        # нити плотно обвиты (радиус 0.35) и быстро вращаются — кокон; на 2.6 разлетаются (радиус 1.5), к 7.0 — обычный
        k = env(t, 2.6, 3.2)
        r = 0.32 + (1.55 - 0.32) * k - 0.55 * env(t, 3.4, 6.5)
        o = cloth_pose(t, wind=12 * (1 - env(t, 4, 7)), amp=1 + 1.5 * k, per=1.0 + env(t, 3, 7) * 3, thr_r=r)
        return o
    mk('irina_cloth_spawn', 7.0, cloth_spawn)

    def cloth_death(t):
        k = env(t, 3.6, 4.8)
        o = cloth_pose(t, amp=1 - 0.8 * k, per=2.0 + 4 * k, swirl=1 - 0.7 * k, thr_r=max(0.001, 1.0 + 0.6 * env(t, 0, 1) - 1.6 * env(t, 3.8, 5.0)))
        return o
    a = mk('irina_cloth_death', 5.0, cloth_death)
    a.loop = 'hold'

    def cloth_cocoon(t):
        # «Только мой»: нити вокруг неё уходят в кокон (сжимаются к 0 к 1.6, снова появляются к 5.8)
        r = 1.0 - env(t, 1.0, 1.6, 5.4, 5.9) * 0.999
        return cloth_pose(t, wind=8, amp=1.6, per=1.4, swirl=1.6, thr_r=max(0.001, r))
    mk('irina_cloth_cocoon', 6.2, cloth_cocoon)
    return out


# ================================================================== запись
def main(args):
    m = build()
    m.pack()
    m.paint()
    an = anims()
    write_json(os.path.join(A, 'geo', 'entity', 'irina.geo.json'), m.geo_json('irina'), compact=True)
    WRITTEN.append('geo/entity/irina.geo.json')
    td = os.path.join(A, 'textures', 'entity', 'irina')
    os.makedirs(td, exist_ok=True)
    m.image.save(os.path.join(td, 'irina.png'), optimize=True)
    WRITTEN.append('textures/entity/irina/irina.png')
    if m.glow is not None:
        m.glow.save(os.path.join(td, 'irina_glowmask.png'), optimize=True)
        WRITTEN.append('textures/entity/irina/irina_glowmask.png')
    write_json(os.path.join(A, 'animations', 'entity', 'irina.animation.json'),
               {'format_version': '1.8.0', 'animations': {a.name: a.to_json() for a in an}}, compact=True)
    WRITTEN.append('animations/entity/irina.animation.json')
    nc = sum(len(b.cubes) for b in m.bones.values())
    print('irina: bones %d, cubes %d, tex %s, anims %d' % (len(m.bones), nc, m.tex_px, len(an)))
    import gen_irina_staff
    gen_irina_staff.main()
    if '--no-fx' not in args:
        import gen_irina_fx
        gen_irina_fx.run(sys.modules[__name__], args)
    import irina_render
    if '--html' in args:
        irina_render.write_html()
    if '--shots' in args:
        irina_render.shots(args)
    return m, an


if __name__ == '__main__':
    main(sys.argv[1:])
