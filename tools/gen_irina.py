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
    """Тон по индексу; дробный индекс квантуется до половин — промежуточный тон = середина соседних (мягкий переход целыми пикселями)."""
    f = np.clip(np.round(np.asarray(idx, float) * 2) / 2, 0, len(tones) - 1)
    T = np.array(tones)
    lo = np.floor(f).astype(int)
    hi = np.minimum(lo + 1, len(tones) - 1)
    k = (f - lo)[..., None]
    return T[lo] * (1 - k) + T[hi] * k


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


K4 = 4    # пикселей на единицу UV (эталон Главы Культа: 512 px на атлас 128)


def pxy(ctx):
    """Пиксельные столбец/ряд внутри грани (при ×4) и мировые координаты на сетке 1/4 ед. (для непрерывных узоров)."""
    w, h = face_size(ctx.cube, ctx.face)
    pc = np.floor(ctx.s * w * K4).astype(int)
    pr = np.floor(ctx.t * h * K4).astype(int)
    q = np.floor(ctx.P * K4 + 4096).astype(np.int64)
    return pc, pr, q


def phash(q, seed=0):
    h = (q[:, 0] * 73856093) ^ (q[:, 1] * 19349663) ^ (q[:, 2] * 83492791) ^ (seed * 2654435761)
    h = h & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return (h & 0xFFFF) / 65536.0


def weave(ctx, kind, seed=0):
    """Фактура ткани (поправка тона, ≤ 0.5): только МЕСТАМИ (пятнами по низкочастотной маске) и слабее — как на ткани эталона.
    twill — саржа: диагональный рубчик; satin — лента: продольная нить; knit — вязь. felt (фетр) — без штриховки: только пятна."""
    pc, pr, q = pxy(ctx)
    d = np.zeros(ctx.n)
    side = np.abs(ctx.N[:, 1]) < 0.5
    patch = fbm(ctx.P, 0.28, 700 + seed, 2) > 0.56                         # где фактура видна
    if kind == 'twill':
        u = q[:, 0] + q[:, 2]
        d += 0.5 * ((((u + q[:, 1]) % 4) == 0) & patch)
    elif kind == 'satin':
        d -= 0.5 * ((pc % 3 == 1) & side & patch)
    elif kind == 'knit':
        d += 0.5 * (((((q[:, 0] + q[:, 2]) // 2 + q[:, 1]) % 3) == 0) & ((q[:, 1] // 2) % 2 == 0) & patch)
    return d


def fold_columns(ctx, i, step=3, phase=0):
    """Складки «рукой» при ×4: тёмная складка 2 px, рядом блик 1 px; каждая складка начинается на своей высоте и сходит на нет
    (верхний конец — 1 px). Шаг — step единиц."""
    up = ctx.N[:, 1] > 0.5
    dn = ctx.N[:, 1] < -0.5
    side = ~(up | dn)
    u = np.where(np.abs(ctx.N[:, 0]) > 0.5, ctx.P[:, 2], ctx.P[:, 0])
    c4 = np.floor((u + 64 + phase) * K4).astype(int)
    per = step * K4
    k = c4 // per
    m_ = c4 % per
    hsh = (k * 2654435761 + 977) & 0xFFFF
    top = (14 + (hsh % 23)) * K4                                          # верх складки (в 1/4 ед. мировой высоты)
    yy = np.floor((ctx.P[:, 1] + 64) * K4).astype(int)
    rel = (64 * K4 + top) - yy                                            # >0 — ниже верха складки
    core = side & (rel > 0) & (m_ == 0)
    soft = side & (rel > 4) & ((m_ == 1) | (m_ == per - 1))                 # полутон по бокам складки — мягкий переход
    fade = side & (rel > 0) & (rel <= 4) & (m_ == 0)                        # верх складки сходит на нет
    lit = side & (rel > 3) & (m_ == 2)
    i = i.astype(float)
    i[soft] = np.maximum(i[soft], 1.5)
    i[core] = np.maximum(i[core], 2.0)
    i[fade] = np.minimum(i[fade], 1.5)
    i[lit & (i == 1)] = 0.5
    return i


def shade(ctx, tones, folds=True, rim=True, fold_step=3, fold_phase=0, blotch=0.0, seed=0, tex=None):
    """tones: [блик, основной, полутень, тень]. Пиксельная светотень: верх/низ граней, контурные края, складки разной длины,
    крупные пятна-потёртости целыми тонами (blotch) — как на ткани Главы Культа."""
    n = ctx.n
    i = np.ones(n, float)
    if blotch:
        b1 = fbm(ctx.P, 0.18, 300 + seed, 3)                                       # крупные пятна
        b2 = fbm(ctx.P, 0.55, 340 + seed, 2)                                       # мелкие
        i = i.astype(float) + 0.5 * (b1 > 0.62) + 0.5 * (b1 > 0.7) * blotch + 0.5 * ((b2 > 0.74) & (b1 > 0.45)) \
            - 0.5 * ((b1 < 0.3) & (b2 < 0.45))                                     # потёртости светлее
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
    if tex:
        i = i + weave(ctx, tex, seed)
    if rim:                                                              # 1 px контур по краю грани (чёткость, как у эталона)
        e = edge_dist(ctx)
        i = np.where(side & (e < 1.0 / K4), np.maximum(i, 2), i)
    return pick(tones, np.clip(i, 0, 3))


def trims(ctx, c, info, tones, accent):
    """Кайма, швы, строчка: hem — низ: ряд акцента над тёмным краем; trim — кант сверху и снизу; seam — вертикальный шов с
    пунктиром строчки по середине передней/задней грани."""
    if ctx.face in ('up', 'down'):
        return c
    r0, r1, c0, c1, w, h = rows(ctx)
    pc, pr, q = pxy(ctx)
    prb = np.floor((1 - ctx.t) * h * K4).astype(int)                    # ряд пикселей снизу
    if info.get('hem') and h >= 3:
        c = np.where(((r1 == 1))[:, None], pick(accent, np.full(ctx.n, 1)), c)
        c = np.where(((prb == 4) | (prb == 7))[:, None], pick(accent, np.full(ctx.n, 3)), c)                # края каймы
        st = (prb == 9) & ((q[:, 0] + q[:, 2]) % 3 != 0)                                                  # строчка над каймой
        c = np.where(st[:, None], pick(accent, np.full(ctx.n, 0)), c)
    if info.get('trim') and h >= 2:
        c = np.where(((r0 == 0) | (r1 == 0))[:, None], pick(accent, np.full(ctx.n, 0)), c)
    if info.get('seam') and ctx.face in ('north', 'south') and w >= 4:
        W = int(round(w * K4))
        mid = (pc == W // 2) & (pr > 2)
        c = np.where(mid[:, None], pick(tones, np.full(ctx.n, 3)), c)
        st = ((pc == W // 2 - 2) | (pc == W // 2 + 2)) & (pr % 3 != 0) & (pr > 2)                      # строчка по обе стороны шва
        c = np.where(st[:, None], pick(tones, np.full(ctx.n, 0)), c)
    return c


def outline(ctx, c, col, k=1.0):
    e = edge_dist(ctx)
    return mix(c, col, (e < 0.5) * k)


def no_glow(n):
    return np.zeros((n, 3))


def mat_hat(ctx):
    info = ctx.cube.info
    c = shade(ctx, T_HAT, folds=not info.get('brim'), fold_step=3, blotch=1.0, seed=1)
    if info.get('band'):                                            # лиловая лента: 2 тёмные полосы и светлый кант (референс)
        y0, y1 = ctx.cube.frm[1], ctx.cube.to[1]
        r = np.floor(ctx.L[:, 1] - y0).astype(int)
        H = int(round(y1 - y0))
        c = shade(ctx, T_LIL, folds=True, blotch=0.4, seed=11, tex='satin')
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
    c = shade(ctx, T_BLU, fold_step=3, blotch=0.7, seed=2, tex='twill')
    c = trims(ctx, c, info, T_BLU, T_BLU)
    a = 1.0
    if ctx.face in ('south', 'east', 'west') and ctx.cube.info.get('shell'):
        r0, r1, c0, c1, w, h = rows(ctx)
        c = np.where((r0 <= 1)[:, None], pick(T_BLU, np.full(ctx.n, 3)), c)          # тень под полями шляпы
        c = np.where((r0 == 2)[:, None], pick(T_BLU, np.full(ctx.n, 2)), c)
        c = np.where((r1 <= 1)[:, None], pick(T_BLU, np.where(r1 == 0, 3, 0)), c)    # кайма внизу: светлый кант над тенью
    if ctx.face == 'south' and ctx.cube.info.get('hem') and not ctx.cube.info.get('shell'):
        r0, r1, c0, c1, w, h = rows(ctx)
        fold = (np.abs(c0 - c1) <= 1) & (r0 <= 1)                                    # складка у шеи
        c = np.where(fold[:, None], pick(T_BLU, np.full(ctx.n, 3)), c)
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
    c = shade(ctx, tones, fold_step=3, blotch=0.6, seed=3, tex='twill')
    if info.get('cuff') and not info.get('pale') and ctx.face not in ('up', 'down'):
        # раструб: две поперечные полосы темнее (как на референсе) + строчка
        yy = np.floor(ctx.P[:, 1] + 64).astype(int)
        band = (yy % 5 == 0) | (yy % 5 == 1)
        c = np.where(band[:, None], shade(ctx, T_LIL2, fold_step=3, blotch=0.5, seed=4, tex='twill'), c)
    if info.get('pale') and ctx.face not in ('up', 'down'):
        r0, r1, c0, c1, w, h = rows(ctx)
        c = np.where(((r0 == 0) & (c0 % 2 == 0))[:, None], pick(T_LIL, np.full(ctx.n, 2)), c)      # строчка каймы
    if info.get('cuff') and ctx.face == 'down':
        e = edge_dist(ctx)
        c = np.where((e < 0.6)[:, None], pick(T_LIL, np.full(ctx.n, 3)), pick(VOID, np.full(ctx.n, 0)))   # тёмный проём раструба
    c = trims(ctx, c, info, tones, T_PALE)
    return c, 1.0, None


def mat_gg(ctx):
    c = shade(ctx, T_GG, fold_step=3, fold_phase=1, blotch=0.9, seed=5, tex='knit')
    c = trims(ctx, c, ctx.cube.info, T_GG, T_LIL)
    return c, 1.0, None


def mat_boot(ctx):
    c = shade(ctx, T_LIL if ctx.cube.info.get('cuff') else T_BOOT, folds=False, blotch=0.6, seed=8)
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
    """Лента — один материал: 3 тона вдоль ленты (свет сверху, база, тень к хвосту) и тёмная кайма по краю; без случайных пикселей."""
    kind = ctx.cube.info.get('kind', 'lil')
    tones = {'gg': T_GG, 'lil_l': T_LIL, 'lil': T_LIL}[kind]
    r0, r1, c0, c1, w, h = rows(ctx)
    y = ctx.P[:, 1]
    tip = ctx.cube.info.get('tip')
    # по мировой высоте: верх ленты светлее, низ — в тени (две ступени, без градиента)
    yt = ctx.cube.frm[1]
    if tip:
        i = np.where(r1 <= 1, 3, 2) * 0 + np.where(r0 < h * 0.45, 1, 2)
        i = np.where(r1 == 0, 3, i)
    else:
        i = np.where(r0 < 2, 0, 1)
    i = np.where(ctx.N[:, 1] > 0.5, 0, np.where(ctx.N[:, 1] < -0.5, 3, i))
    pc, pr, q = pxy(ctx)
    W = int(round(w * K4))
    if w >= 2 and ctx.face in ('north', 'south'):
        i = i + weave(ctx, 'satin', 9)
        i = np.where((pc <= 0) | (pc >= W - 1), 3, i)                                   # тёмная кайма по краю (1 px)
        i = np.where(((pc == 1) | (pc == W - 2)) & (pr % 3 != 1), 0, i)                  # строчка вдоль каймы
    c = pick(tones, np.clip(i, 0, 3))
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
    m = IModel('irina', density=4, tex_w=128)          # ×4, как эталон (атлас 128 ед. → 512 px)
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
    m.box('torso', (-10.2, 23.0, -3.4), (10.2, 27.2, 3.4), 'gg', hem=True)                     # накидка-воротник шире плеч на 2 текселя
    m.box('torso', (-7.4, 27.2, -2.8), (7.4, 28.2, 2.8), 'gg', trim=True)
    m.bone('mantle', 'torso', (0, 27.2, 0))
    for k in range(12):
        a = TAU * (k + 0.5) / 12
        top = np.array([math.sin(a) * 8.6, 26.6, -math.cos(a) * 3.0])
        bot = np.array([math.sin(a) * 10.8, 19.8 + (k % 2) * 1.0, -math.cos(a) * 4.4])
        m.rod('mantle', top, bot, 4.2, 0.6, 'ribbon', roll=-math.degrees(a), kind=('gg', 'lil_l')[k % 2], tip=True)
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
    m.box('hood', (-5.0, 26.2, -4.8), (5.0, 36.6, 5.0), 'hood', shell=True, seam=True)                     # оболочка вокруг головы
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
    for (y0, y1, sx, sz) in ((10.0, 15.8, 10.4, 6.6), (3.0, 10.2, 15.6, 10.6)):
        m.cbox('skirt', (0, (y0 + y1) / 2, 0), (sx, y1 - y0, sz), 'gg', hem=True)
        m.cbox('skirt', (0, (y0 + y1) / 2, 0), (sx * 0.78, y1 - y0, sz * 1.18), 'gg', hem=True)
    N = 20
    kinds = ('lil_l', 'gg')
    for k in range(N):
        a = TAU * (k + 0.5) / N
        front = -math.cos(a)
        top = np.array([math.sin(a) * 5.6, 15.6, -math.cos(a) * 3.8])
        end_y = 1.4 + 1.6 * max(0.0, front) ** 2 - 1.0 * max(0.0, -front) + (k % 3 - 1) * 0.9
        rad = 11.0 + 0.6 * (k % 2)                                # нижний ярус шире верхнего (конус)
        bot = np.array([math.sin(a) * rad, end_y, -math.cos(a) * rad * 0.8])
        mid = top + (bot - top) * 0.5
        w = 3.8 + 0.4 * (k % 2)
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


EASES = {'io': ease_io, 'lin': lambda x: x, 'in': lambda x: x * x * (1.6 - 0.6 * x), 'out': lambda x: 1 - (1 - x) ** 3,
         'back': lambda x: 1 + 2.4 * (x - 1) ** 3 + 1.4 * (x - 1) ** 2}


def keys_track(t, keys):
    """keys: [(t, value_list[, кривая])], между ключами — smoothstep или кривая отрезка (кривая — у ключа, к которому идёт отрезок;
    по эталону Epic Fight, 21.11: удар — 'in'/'lin' без остановки на ключах, замах и остановка — 'out', перехлёст — 'back')."""
    if t <= keys[0][0]:
        return list(keys[0][1])
    for k0, k1 in zip(keys, keys[1:]):
        (t0, v0), (t1, v1) = k0[:2], k1[:2]
        if t <= t1:
            e = EASES[k1[2] if len(k1) > 2 else 'io']
            x = max(0.0, min(1.0, (t - t0) / (t1 - t0)))
            return lerp3(v0, v1, e(x)) if len(v0) == 3 else v0
    return list(keys[-1][1])


RIBS = ['rib_%02d' % k for k in range(20)]
# ---- поза покоя (оси Blockbench/Iron's, см. bb()). Правая рука держит посох (хват gen_irina_staff.DISPLAY): рука вперёд на 50° —
# древко наклонно перед ней, крюк впереди на уровне груди. Проверка 20.11 (tools/irina_anim_check.py): чистая зона правой руки с посохом —
# вперёд 10–55°, в сторону 5–60°; при наклоне головы вниз > 12° — вперёд не больше 25° (иначе поля шляпы ложатся на древко).
R_HOLD = [-50, 0, 12]
L_IDLE = [-36, 22, -4]
HEAD0 = [-3, 0, 4]
IDLE0 = {'body': {'pos': [0, 0, 0], 'rot': [0, 0, 0]}, 'torso': {'rot': [0, 0, 0]}, 'head': {'rot': list(HEAD0)}, 'hat': {'rot': [0, 0, 0]},
         'right_arm': {'rot': list(R_HOLD)}, 'left_arm': {'rot': list(L_IDLE)}, 'right_leg': {'rot': [0, 0, 0]}, 'left_leg': {'rot': [0, 0, 0]}}


def bb(pose):
    """Позы ниже записаны в осях Blockbench / GeckoLib-JSON, как у Iron's (casting_animations.json): рука вперёд и вверх — x минус
    (−90 — вперёд, −180 — над головой), правая рука в сторону — z плюс, левая — z минус; торс/голова вперёд-вниз — x плюс;
    поворот тела вправо — y плюс; свисающая ткань назад — x плюс; position: x плюс — влево от неё, z минус — вперёд.
    Anim.to_json (nightmare_geo) пишет JSON как (−x, −y, z) от внутренних осей — переводим сюда, чтобы в файле оказались ровно эти числа.
    (Проверка 20.11: до этого перевода X/Y уходили в файл с обратным знаком — касты и удары уходили за спину.)"""
    for ch in pose.values():
        if 'rot' in ch:
            r = ch['rot']
            ch['rot'] = [-r[0], -r[1], r[2]]
        if 'pos' in ch:
            q = ch['pos']
            ch['pos'] = [-q[0], q[1], q[2]]
    return pose


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
    return {'body': {'pos': [0, br * 0.25, 0], 'rot': [0, 0, 0]}, 'torso': {'rot': [br * 1.2, 0, 0]},
            'head': {'rot': [HEAD0[0] + br * 1.5, 6 * math.sin(t * TAU / (per * 2)), HEAD0[2]]}, 'hat': {'rot': [0, 0, 0]},
            'right_arm': {'rot': [R_HOLD[0] + br * 1.5, 0, R_HOLD[2]]}, 'left_arm': {'rot': [L_IDLE[0] - br * 2, L_IDLE[1], L_IDLE[2] - br * 2]},
            'right_leg': {'rot': [0, 0, 0]}, 'left_leg': {'rot': [0, 0, 0]}}


# стойка по эталону Epic Fight (21.11): тело вправо 26° (вполоборота), голова на цель, левая нога впереди, правая сзади (носок наружу)
STANCE_I = {'body': {'pos': [0, 0, 0], 'rot': [2, 26, 0]}, 'torso': {'rot': [0, 0, 0]}, 'head': {'rot': [HEAD0[0], -22, HEAD0[2]]},
            'hat': {'rot': [0, 0, 0]}, 'right_arm': {'rot': list(R_HOLD)}, 'left_arm': {'rot': list(L_IDLE)},
            'right_leg': {'rot': [8, -14, 0]}, 'left_leg': {'rot': [-8, -20, 0]}}


def stance_pose(t, per=2.8):
    br = math.sin(t * TAU / per)
    sw = math.sin(t * TAU / per + 1.1)
    p = {b: {c: list(v) for c, v in ch.items()} for b, ch in STANCE_I.items()}
    p['body']['pos'] = [0.15 * sw, br * 0.12, 0]
    p['body']['rot'][1] += 1.2 * sw
    p['torso']['rot'][0] += br * 0.6
    p['head']['rot'][0] += br * 0.8
    p['head']['rot'][1] += 3 * math.sin(t * TAU / per + 2.0)
    p['right_arm']['rot'][0] += br * 1.0
    p['left_arm']['rot'][0] -= br * 1.5
    p['left_arm']['rot'][2] -= br * 1.5
    return p


def keyed(t, keys, base=None):
    """Анимация ключевыми позами: keys = [(t, {кость: {'rot'|'pos': [x, y, z]}})], между ключами — smoothstep (без рывков и без
    переходов через ±180°). Кость, которой нет в ключе, берётся из позы покоя IDLE0 (все кости тела всегда с ключами)."""
    full = []
    for tk, p, *e in keys:
        q = {b: {c: list(v) for c, v in ch.items()} for b, ch in (base or IDLE0).items()}
        for b, ch in p.items():
            q.setdefault(b, {}).update({c: list(v) for c, v in ch.items()})
        full.append((tk, q, e[0] if e else 'io'))
    out = {}
    for b in full[0][1]:
        for c in full[0][1][b]:
            tr = [(tk, q[b][c], e) for tk, q, e in full]
            out.setdefault(b, {})[c] = keys_track(t, tr)
    return out


def P(**bones):
    """Короткая запись позы: P(right_arm=[x, y, z], body_pos=[…]) → {кость: {'rot'|'pos': …}}."""
    o = {}
    for k, v in bones.items():
        if k.endswith('_pos'):
            o.setdefault(k[:-4], {})['pos'] = list(v)
        else:
            o.setdefault(k, {})['rot'] = list(v)
    return o


def cloth_pose(t, wind=0.0, amp=1.0, per=4.0, swirl=1.0, thr_r=1.0, legs=None):
    """Ленты/рукава/завязки/кончик шляпы/нити (оси Blockbench, см. bb()). wind — ветер движения (градусы): ВСЯ ткань уходит назад и
    вниз (свисающая ткань назад — x плюс), передние ленты — слабее, чтобы не лечь на ноги; качание — со смещением назад на свою
    амплитуду, поэтому конец ленты не выходит вперёд дальше позы покоя. legs = (правая, левая) — насколько нога вынесена вперёд (°):
    передние ленты над этой ногой она подталкивает вперёд (не сквозь ногу)."""
    o = {}
    for k, bn in enumerate(RIBS):
        a = TAU * (k + 0.5) / 20
        fwd = math.cos(a)                    # 1 — лента спереди, −1 — сзади (модель смотрит на −z)
        side = math.sin(a)                   # + справа
        ph = t * TAU / per + k * 0.7
        sw = math.sin(ph) * 3.0 * amp
        tw = math.sin(ph * 0.5 + k) * 4 * amp
        back = wind * (0.35 if fwd > 0.3 else 1.0) + 3.0 * amp
        kick = 0.0
        if legs:
            cl = lambda v: max(0.0, min(1.0, v))
            kick = max(legs[0] * cl(0.75 + side), legs[1] * cl(0.75 - side)) * cl(1.3 * fwd) * 1.15
        o[bn] = {'rot': [back + sw - kick, tw * 0.3, sw * side * 0.8]}
        o[bn + '_b'] = {'rot': [0.4 * back + 5 * amp + math.sin(ph - 0.9) * 5 * amp - 0.3 * kick, 0, math.sin(ph - 0.9) * 3 * amp * side]}
    for sn in 'rl':
        s = 1 if sn == 'r' else -1
        o['sleeve_' + sn] = {'rot': [math.sin(t * TAU / per + s) * 3 * amp + 3 * amp + wind * 0.3, 0, s * math.sin(t * TAU / per * 0.5) * 2 * amp]}
        o['tie_' + sn] = {'rot': [math.sin(t * TAU / per + s * 0.5) * 2.5 * amp + 2.5 * amp + wind * 0.15, 0, s * 3]}
        o['tie_%s_b' % sn] = {'rot': [math.sin(t * TAU / per + s * 0.5 - 1) * 3 * amp + 3 * amp + wind * 0.1, 0, 0]}
        o['sash_' + sn] = {'rot': [math.sin(t * TAU / per * 1.3 + s) * 8 * amp + 8 * amp + wind, 0, s * (6 + 3 * math.sin(t * TAU / per))]}
    o['hat_tip'] = {'rot': [math.sin(t * TAU / per) * 3 * amp - wind * 0.3, 0, math.sin(t * TAU / per * 0.5) * 4 * amp]}
    o['hat_tip2'] = {'rot': [math.sin(t * TAU / per - 0.6) * 4 * amp - wind * 0.2, 0, math.sin(t * TAU / per * 0.5 - 0.6) * 5 * amp]}
    o['hat_tip3'] = {'rot': [math.sin(t * TAU / per - 1.2) * 6 * amp - wind * 0.2, 0, 0]}
    o['hood_drape'] = {'rot': [math.sin(t * TAU / per + 1) * 2 * amp + 2 * amp + wind * 0.4, 0, 0]}
    o['mantle'] = {'rot': [0, 0, 0]}
    # нити: вращение вокруг вертикали (знак и скорость свои), лёгкое «дыхание» радиуса
    L = per
    o['thread_a'] = {'rot': [0, -360 * t / L * swirl, 0], 'scale': [thr_r] * 3}
    o['thread_b'] = {'rot': [0, 360 * t / L * swirl, 0], 'scale': [thr_r] * 3}
    o['thread_c'] = {'rot': [0, -720 * t / L * swirl, 0], 'scale': [thr_r] * 3}
    o['thread_bits'] = {'rot': [0, 360 * t / L * swirl * 0.5, 0], 'pos': [0, math.sin(t * TAU / L) * 0.6, 0]}
    o['threads'] = {'pos': [0, math.sin(t * TAU / L * 2) * 0.4, 0]}
    return o


def walk_legs(t):
    s = math.sin(t / 1.2 * TAU)
    return s * 26, -s * 26                   # правая/левая нога: плюс — назад


# ---- шляпа в смерти: слетает назад-вправо и остаётся лежать на земле, пока Ирина падает (кость hat — дочь head, поэтому
# её ключи — обратное преобразование головы; считается по геометрии geo/entity/irina.geo.json тем же FK, что у GeckoLib)
HAT_LAND = ([14.0, 2.0, 16.0], [3, -35, -3])   # мир модели (x вправо, y вверх, z назад): точка кости hat и её поворот (внутренние оси, Z·Y·X)
DEATH_T = (2.3, 2.45, 2.9)                   # снялась — приподнялась — легла (событие 'hat' 2.4)


def anims():
    out = []

    def mk(name, length, fn, loop=False, dt=0.05, events=None, post=None):
        a = Anim(name, length, loop=loop)
        a.sample(lambda t: bb(post(t, fn(t)) if post else fn(t)), dt)
        for tt, ev in (events or {}).items():
            a.instruction(tt, ev)
        out.append(a)
        return a

    # ---------------- контроллер «тело» (body/torso/head/hat/руки/ноги); у каждой анимации ключи на ВСЕХ костях тела
    # ---- стойка и удары посохом — по эталону Epic Fight (21.11; docs/specs/anim_style_epicfight.md): вполоборота (тело вправо 26°,
    # голова на цель), левая нога впереди; дыхание 2.8 с, грудь ≈0.02 L. Удары начинаются и кончаются в этой стойке.
    mk('irina_idle', 2.8, lambda t: stance_pose(t), loop=True)

    def walk(t):
        ph = t / 1.2 * TAU
        s = math.sin(ph)
        rl, ll = walk_legs(t)
        return {'body': {'pos': [0, abs(math.cos(ph)) * 0.5, 0], 'rot': [0, s * 4, 0]}, 'torso': {'rot': [3, -s * 3, 0]},
                'head': {'rot': [-2, s * 2, 3]}, 'hat': {'rot': [0, 0, 0]},
                'right_arm': {'rot': [R_HOLD[0] + 4 + s * 4, 0, R_HOLD[2]]}, 'left_arm': {'rot': [-12 + s * 20, 0, -10]},
                'right_leg': {'rot': [rl, 0, 0]}, 'left_leg': {'rot': [ll, 0, 0]}}
    mk('irina_walk', 1.2, walk, loop=True)

    def cast_short(t):
        # левая ладонь выбрасывает каст вперёд (0.35), посох в правой — на месте
        return keyed(t, [(0, {}), (0.25, P(left_arm=[-88, -8, 6], torso=[2, 10, 0], head=[-5, 6, 0], right_arm=[-46, 0, 14])),
                         (0.45, P(left_arm=[-92, -8, 6], torso=[3, 10, 0], head=[-5, 6, 0], right_arm=[-46, 0, 14])), (0.8, {})])
    mk('irina_cast_short', 0.8, cast_short, dt=0.025, events={0.35: 'cast'})

    def cast_long_pose(t):
        ph = t / 2.0 * TAU
        return {'body': {'pos': [0, 0, 0], 'rot': [0, 0, 0]}, 'torso': {'rot': [-4, 0, 0]}, 'head': {'rot': [-8, 0, 4]}, 'hat': {'rot': [0, 0, 0]},
                'right_arm': {'rot': [-60 + math.sin(ph) * 3, 0, 16]},                       # посох поднят перед собой, навершие вверх
                'left_arm': {'rot': [-78 + math.sin(ph) * 10, -16 + math.cos(ph) * 14, -18 + math.sin(ph * 2) * 6]},  # ладонь ткёт нити
                'right_leg': {'rot': [0, 0, 0]}, 'left_leg': {'rot': [0, 0, 0]}}
    mk('irina_cast_long', 2.0, cast_long_pose, loop=True)

    def cast_long_end(t):
        return keyed(t, [(0, cast_long_pose(0)), (0.5, {})])
    mk('irina_cast_long_end', 0.5, cast_long_end, dt=0.025)

    def staff_attack(t):
        # удар крюком сверху (эталон Epic Fight, 21.11; тик hit прежний — 0.55): замах 0–0.30 (тело вправо 52°, отклон назад, вес на
        # правую ногу, посох над правым плечом, крюк за шляпой), взвод до 0.42 (левая нога отрывается), удар 0.42–0.58 без остановки
        # на ключах (левая нога шагает вперёд, таз вперёд и вниз, тело доворачивается влево, крюк — по дуге сверху вперёд-вниз),
        # перехлёст до 0.66, держит до 1.0, отшаг и стойка к 1.8.
        wind = P(body=[-4, 44, 0], body_pos=[0, 0, 0.8], torso=[-8, 8, 0], head=[-8, -8, 0], right_arm=[-88, 30, 74],
                 left_arm=[-40, 0, -30], right_leg=[10, -30, 0], left_leg=[-4, -30, 0])
        load = P(body=[-5, 50, 0], body_pos=[0, 0, 1.0], torso=[-9, 9, 0], head=[-8, -8, 0], right_arm=[-92, 32, 78],
                 left_arm=[-42, 0, -32], right_leg=[10, -32, 0], left_leg=[-12, -32, 0])
        mid = P(body=[6, 22, 0], body_pos=[0, -0.3, -1.2], torso=[4, 2, 0], head=[0, -14, 0], right_arm=[-92, 24, 34],
                left_arm=[-30, 0, -28], right_leg=[10, -14, 0], left_leg=[-14, -14, 0])
        hit = P(body=[16, -12, 0], body_pos=[0, -0.8, -3.6], torso=[14, -6, 0], head=[6, 12, 0], right_arm=[-40, 0, 8],
                left_arm=[-20, 0, -28], right_leg=[14, 10, 0], left_leg=[-16, 10, 0])
        fol = P(body=[20, -26, 0], body_pos=[0, -0.9, -4.2], torso=[18, -8, 0], head=[8, 22, 0], right_arm=[-12, -8, 6],
                left_arm=[-16, 0, -30], right_leg=[14, 18, 0], left_leg=[-16, 18, 0])
        hold = P(body=[17, -20, 0], body_pos=[0, -0.8, -4.0], torso=[15, -6, 0], head=[6, 18, 0], right_arm=[-20, -6, 6],
                 left_arm=[-18, 0, -28], right_leg=[14, 14, 0], left_leg=[-16, 14, 0])
        back = P(body=[6, 12, 0], body_pos=[0, -0.2, -1.6], torso=[4, 0, 0], head=[0, -10, 0], right_arm=[-40, 0, 10],
                 right_leg=[10, -6, 0], left_leg=[-10, -6, 0])
        side = P(body=[0, 30, 0], body_pos=[0, 0, 0.4], torso=[-4, 4, 0], head=[-4, -20, 0], right_arm=[-60, 20, 62], left_arm=[-38, 0, -28])
        return keyed(t, [(0, {}), (0.14, side, 'io'), (0.30, wind, 'out'), (0.42, load, 'lin'), (0.49, mid, 'in'), (0.56, hit, 'lin'), (0.66, fol, 'out'),
                         (0.78, hold, 'back'), (0.86, hold), (1.2, back), (1.8, {})], base=STANCE_I)
    mk('irina_staff_attack', 1.8, staff_attack, dt=0.0125, events={0.55: 'hit'})

    def staff_sweep(t):
        # горизонтальный взмах (эталон Epic Fight, 21.11; hit 0.46): замах вправо (тело 70°, посох в сторону и назад, вес на правую),
        # взвод, взмах справа налево без остановки (левая нога шагает, таз вперёд), перехлёст до тела −80°, отшаг и стойка к 1.6.
        wind = P(body=[0, 70, 0], body_pos=[0, 0, 0.6], head=[0, -46, 0], right_arm=[-36, 0, 88], left_arm=[-30, 0, -34], torso=[0, 6, 0],
                 right_leg=[8, -44, 0], left_leg=[-4, -44, 0])
        load = P(body=[0, 76, 0], body_pos=[0, 0, 0.8], head=[0, -48, 0], right_arm=[-34, 0, 94], left_arm=[-30, 0, -34], torso=[0, 7, 0],
                 right_leg=[8, -46, 0], left_leg=[-12, -46, 0])
        mid = P(body=[4, 30, 0], body_pos=[0, -0.3, -1.0], head=[0, -20, 0], right_arm=[-50, 0, 50], left_arm=[-28, 0, -32], torso=[4, 2, 0],
                right_leg=[10, -20, 0], left_leg=[-14, -20, 0])
        hit = P(body=[8, -22, 0], body_pos=[0, -0.6, -2.8], head=[2, 12, 0], right_arm=[-60, 0, 18], left_arm=[-24, 0, -36], torso=[6, -4, 0],
                right_leg=[12, 14, 0], left_leg=[-16, 14, 0])
        fol = P(body=[8, -74, 0], body_pos=[0, -0.6, -3.2], head=[0, 42, 0], right_arm=[-62, 0, -30], left_arm=[-20, 0, -40], torso=[6, -8, 0],
                right_leg=[12, 40, 0], left_leg=[-16, 40, 0])
        over = P(body=[7, -84, 0], body_pos=[0, -0.6, -3.3], head=[0, 46, 0], right_arm=[-60, 0, -36], left_arm=[-20, 0, -40],
                 torso=[6, -9, 0], right_leg=[12, 44, 0], left_leg=[-16, 44, 0])
        back = P(body=[2, 0, 0], body_pos=[0, -0.2, -1.2], head=[0, 0, 0], right_arm=[-46, 0, 14], right_leg=[8, 0, 0], left_leg=[-10, 0, 0])
        return keyed(t, [(0, {}), (0.26, wind, 'out'), (0.36, load, 'lin'), (0.42, mid, 'in'), (0.47, hit, 'lin'), (0.54, fol, 'out'),
                         (0.66, over, 'back'), (0.9, over), (1.15, back), (1.6, {})], base=STANCE_I)
    mk('irina_staff_sweep', 1.6, staff_sweep, dt=0.0125, events={0.46: 'hit'})

    def mark(t):
        # «Предмет ревности»: склоняет голову набок и указывает левой рукой на цель перед собой
        p = P(left_arm=[-90, -4, 4], head=[2, 10, 14], torso=[0, 10, 0], right_arm=[-44, 0, 14])
        return keyed(t, [(0, {}), (0.45, p), (1.0, p), (1.4, {})])
    mk('irina_mark', 1.4, mark, dt=0.025, events={0.7: 'mark'})

    def bind(t):
        # «Красные нити»: левая рука к груди, посох прижат (0.5), затем обе руки разводятся вперёд-в стороны — нити связывают пары (0.9)
        cross = P(left_arm=[-74, 34, 34], right_arm=[-46, -8, 10], torso=[6, 0, 0], head=[6, 0, 0], body_pos=[0, -0.5, 0])
        spread = P(left_arm=[-64, 0, -62], right_arm=[-36, 0, 52], torso=[-6, 0, 0], head=[-10, 0, 0], body_pos=[0, 0.3, 0])
        return keyed(t, [(0, {}), (0.5, cross), (0.75, cross), (1.05, spread), (1.3, spread), (1.6, {})])
    mk('irina_bind', 1.6, bind, dt=0.025, events={0.9: 'bind'})

    def whip(t):
        # фаза 3: нити хлещут — замах (левая вверх-внутрь), резкий взмах обеих рук вперёд-наружу (0.45)
        wind = P(left_arm=[-100, 0, 10], right_arm=[-54, 0, -2], torso=[-10, 0, 0], head=[-8, 0, 0], body_pos=[0, -0.6, 0])
        lash = P(left_arm=[-58, 0, -62], right_arm=[-30, 0, 54], torso=[12, 0, 0], head=[6, 0, 0], body_pos=[0, 0.2, -0.6])
        return keyed(t, [(0, {}), (0.26, wind), (0.45, lash), (0.6, lash), (1.0, {})])
    mk('irina_whip', 1.0, whip, dt=0.025, events={0.45: 'lash'})

    def steal(t):
        # кража эффектов: руки раскрыты вперёд к игрокам (0.3), затем стягивает свет к груди (1.2)
        opn = P(left_arm=[-80, 0, -36], right_arm=[-44, 0, 36], torso=[-6, 0, 0], head=[-8, 0, 0])
        clutch = P(left_arm=[-72, 34, 30], right_arm=[-44, -6, 10], torso=[10, 0, 0], head=[8, 0, 0])
        return keyed(t, [(0, {}), (0.3, opn), (0.85, opn), (1.2, clutch), (1.3, clutch), (1.5, {})])
    mk('irina_steal', 1.5, steal, dt=0.025, events={0.3: 'pull', 1.2: 'absorb'})

    def happiness(t):
        # «Чужое счастье» (6 с): поднимается над землёй (0.3–1.6), руки широко (1.4), с 3.6 стягивает свет к груди, 5.2 — вспышка
        up = P(body_pos=[0, 6, 0], right_leg=[0, 0, 4], left_leg=[6, 0, -4])
        spread = dict(up, **P(left_arm=[-26, 0, -80], right_arm=[-34, 0, 58], head=[-18, 0, 0], torso=[-10, 0, 0]))
        clutch = dict(up, **P(left_arm=[-74, 34, 30], right_arm=[-44, -6, 12], head=[10, 0, 0], torso=[12, 0, 0]))
        sway = lambda tt: dict(spread, body={'rot': [0, 4 * math.sin(tt * 2.2), 0], 'pos': [0, 6, 0]})
        return keyed(t, [(0, {}), (0.3, P()), (1.4, sway(1.4)), (2.4, sway(2.4)), (3.4, sway(3.4)), (4.4, clutch), (5.2, clutch),
                         (5.4, dict(clutch, **P(head=[-6, 0, 0]))), (6.0, {})])
    mk('irina_others_happiness', 6.0, happiness, events={0.0: 'begin', 1.4: 'spread', 3.6: 'gather', 5.2: 'absorb', 6.0: 'end'})

    def only_mine(t):
        # «Только мой» (6.2 с): тянется левой рукой к жертве перед собой (0.6), рывок к себе (1.0), обнимает кокон перед собой
        # (1.6–5.4, дышит), сжимает (5.4); посох в правой отведён в сторону
        reach = P(left_arm=[-96, 0, 2], torso=[10, 0, 0], head=[4, 0, 0], body_pos=[0, 0, -1.2], right_arm=[-36, 0, 20],
                  right_leg=[-8, 0, 0], left_leg=[8, 0, 0])
        yank = P(left_arm=[-70, 18, 16], torso=[-8, 0, 0], head=[-4, 0, 0], body_pos=[0, 0, 0.4], right_arm=[-36, 0, 24])
        hug = P(left_arm=[-82, 30, 26], right_arm=[-30, -10, 20], torso=[6, 0, 0], head=[10, 0, 14], body_pos=[0, 0, -0.4])
        hug2 = dict(hug, **P(torso=[9, 0, 0], left_arm=[-80, 32, 28]))
        crush = P(left_arm=[-78, 40, 34], right_arm=[-28, -10, 16], torso=[14, 0, 0], head=[14, 0, 14], body_pos=[0, -0.4, -0.4])
        return keyed(t, [(0, {}), (0.6, reach), (0.8, reach), (1.1, yank), (1.9, hug), (2.8, hug2), (3.7, hug), (4.6, hug2), (5.3, hug),
                         (5.5, crush), (5.8, crush), (6.2, {})])
    mk('irina_only_mine', 6.2, only_mine, events={0.6: 'reach', 1.0: 'yank', 1.6: 'cocoon', 5.4: 'crush', 6.2: 'end'})

    def only_mine_broken(t):
        # кокон разорван союзниками: отшатывается назад, левой рукой хватается за поля шляпы
        p = P(body_pos=[0, 0, 2.0], torso=[-14, 0, 6], head=[-12, 0, -10], hat=[-8, 0, 8], left_arm=[-124, 8, 4], right_arm=[-34, 0, 30])
        return keyed(t, [(0, {}), (0.25, p), (0.55, p), (1.2, {})])
    mk('irina_only_mine_broken', 1.2, only_mine_broken, dt=0.025, events={0.0: 'broken'})

    def phase2(t):
        # переход 66%: левой рукой тянет поля шляпы вниз (голова склонена, посох опущен), затем резко поднимает голову (1.45)
        d = P(head=[14, 0, 0], hat=[8, 0, 0], left_arm=[-102, 8, 2], right_arm=[-22, 0, 18], torso=[8, 0, 0])
        u = P(head=[-16, 0, 0], hat=[-4, 0, 0], left_arm=[-44, 0, -44], right_arm=[-42, 0, 44], torso=[-10, 0, 0])
        return keyed(t, [(0, {}), (0.6, d), (1.25, d), (1.55, u), (2.1, u), (2.5, {})])
    mk('irina_phase2', 2.5, phase2, events={1.45: 'burst'})

    def phase3(t):
        # переход 33%: ярость — запрокидывает голову, руки в стороны и вниз, шляпа съезжает набок
        def r(tt):
            sh = math.sin(tt * 40) * env(tt, 1.2, 1.4, 2.0, 2.3)
            return P(head=[-28, 0, sh * 3], hat=[-6, 0, -14], torso=[-12, 0, sh], body_pos=[0, 1.0, 0], right_arm=[-22, 0, 62],
                     left_arm=[-12, 0, -70], right_leg=[0, 0, 6], left_leg=[0, 0, -6])
        ks = [(0, {}), (0.2, {})] + [(round(0.9 + 0.1 * i, 2), r(0.9 + 0.1 * i)) for i in range(15)] + [(3.0, {})]
        return keyed(t, ks)
    mk('irina_phase3', 3.0, phase3, events={1.3: 'rage'})

    def finisher(t):
        # добивание (2.6 с), жертва ПЕРЕД ней (≈1.6 бл.): нити опутывают (0.2), левая рука тянет к себе (0.8), посох поднят (1.15),
        # крюк сверху вперёд-вниз в грудь жертвы (1.3), склоняется к ней — шёпот (1.7), отпускает (2.2 — kill)
        grab = P(left_arm=[-96, 0, 4], torso=[8, 0, 0], head=[4, 0, 0])
        pull = P(left_arm=[-86, 24, 18], body_pos=[0, 0, -0.8], head=[8, -8, 12], torso=[4, 0, 0])
        lift = dict(pull, **P(right_arm=[-96, 0, 40], torso=[-6, 0, 0], head=[-4, -8, 8]))
        pierce = dict(pull, **P(right_arm=[-24, 0, 6], torso=[16, 0, 0], body_pos=[0, -0.4, -1.6], head=[8, -6, 10]))
        whisper = dict(pierce, **P(head=[12, -10, 20]))
        release = P(left_arm=[-40, 0, -22], right_arm=[-36, 0, 16], torso=[2, 0, 0], head=[2, 0, 6])
        return keyed(t, [(0, {}), (0.3, grab), (0.8, pull), (1.15, lift), (1.32, pierce), (1.7, whisper), (2.1, whisper), (2.3, release), (2.6, {})])
    mk('irina_finisher', 2.6, finisher, dt=0.025, events={0.2: 'wrap', 0.8: 'pull_done', 1.3: 'pierce', 1.7: 'whisper', 2.2: 'kill'})

    def spawn(t):
        # появление (7 с): сидит в коконе, свернувшись (0–2.6; посох лежит вдоль бедра, над землёй), поднимается (2.6–4.4),
        # поправляет шляпу левой рукой (4.6), взмах посохом наружу вправо — нити расходятся кольцом (5.4), 7.0 — бой.
        # Посох всё время в хвате и не проходит через корпус: взмах — в сторону, без оборота.
        curl = P(body_pos=[0, -9, 0], torso=[40, 0, 0], head=[30, 0, 0], right_arm=[-6, 0, 44], left_arm=[-40, 0, 10],
                 right_leg=[-80, 0, 0], left_leg=[-80, 0, 0])
        hat = P(left_arm=[-122, 10, 6], head=[-6, 0, 4], hat=[0, 0, -4])
        flo = P(right_arm=[-40, 0, 70], body=[0, -10, 0], head=[-4, 8, 4], left_arm=[-30, 0, -30])
        return keyed(t, [(0, curl), (2.6, curl), (4.2, {}), (4.4, {}), (4.8, hat), (5.0, hat), (5.35, {}), (5.75, flo), (6.2, flo), (7.0, {})])
    mk('irina_spawn', 7.0, spawn, events={0.0: 'cocoon', 2.6: 'unravel', 4.6: 'pose', 5.4: 'flourish', 7.0: 'ready'})

    def death_body(t):
        # смерть (5 с): удар (0–0.6), опускается на колени, опираясь на посох (1.6), тянется к слетевшей шляпе (3.2),
        # ложится на левый бок (3.4–4.2); посох всё время над землёй
        hit = P(body=[-6, 0, 0], body_pos=[0, 0, 1.2], head=[-10, 0, 4], right_arm=[-36, 0, 30], left_arm=[-20, 0, -16])
        knee = P(body_pos=[0, -5.5, 0], torso=[16, 0, 0], head=[22, 0, 4], right_arm=[-58, 0, 22], left_arm=[-20, 0, -10],
                 right_leg=[-80, 0, 0], left_leg=[-80, 0, 0])
        reach = dict(knee, **P(left_arm=[-70, 20, -10], head=[10, 20, 4]))
        fallen = P(body=[0, 0, 74], body_pos=[0, -10, 4], torso=[6, 0, 0], head=[12, 0, -6], right_arm=[-80, -30, 15], left_arm=[-40, 0, -20],
                   right_leg=[-40, 0, 0], left_leg=[-50, 0, 0])
        return keyed(t, [(0, {}), (0.2, hit), (0.4, hit), (1.6, knee), (2.7, knee), (3.2, reach), (4.2, fallen), (5.0, fallen)])

    def death(t):
        p = death_body(t)
        if t > DEATH_T[0]:
            p['hat'] = death_hat(t, p, death_body(DEATH_T[0]))
        return p
    a = mk('irina_death', 5.0, death, events={0.0: 'hit', 1.6: 'knees', 2.4: 'hat', 3.4: 'fall', 4.2: 'unravel', 5.0: 'gone'})
    a.loop = 'hold'

    # ---------------- +4 заклинания (владелец 20.11)
    def gaze(t):
        # «Ревнивый взгляд»: левой рукой приподнимает поля шляпы — из тьмы капюшона «смотрит» (событие gaze — метка смотрящим)
        p = P(left_arm=[-122, 12, 6], head=[-10, 8, 0], hat=[-12, 0, 0], torso=[-4, 10, 0], right_arm=[-46, 0, 14])
        return keyed(t, [(0, {}), (0.35, p), (0.8, p), (1.2, {})])
    mk('irina_gaze', 1.2, gaze, dt=0.025, events={0.5: 'gaze'})

    def knots(t):
        # «Узлы»: приседает, левая ладонь к земле перед собой и ведёт по дуге — узлы прорастают (событие knots 0.9)
        d0 = P(body_pos=[0, -3, 0], torso=[24, -16, 0], head=[14, 0, 0], left_arm=[-34, -30, -10], right_arm=[-22, 0, 22],
               right_leg=[-4, 0, 0], left_leg=[12, 0, 0])
        d1 = dict(d0, **P(torso=[24, 16, 0], left_arm=[-34, 30, -10]))
        return keyed(t, [(0, {}), (0.45, d0), (1.0, d1), (1.1, d1), (1.6, {})])
    mk('irina_knots', 1.6, knots, dt=0.025, events={0.9: 'knots'})

    def swap(t):
        # «Подмена любимого»: руки скрещены у груди, резко разводит — двое меняются местами (событие swap 0.8)
        cross = P(left_arm=[-80, 40, 26], right_arm=[-46, -8, 10], body=[0, 14, 0], head=[6, 0, 0])
        spread = P(left_arm=[-70, 0, -64], right_arm=[-40, 0, 54], body=[0, -14, 0], head=[0, 0, 14])
        return keyed(t, [(0, {}), (0.5, cross), (0.7, cross), (0.9, spread), (1.05, spread), (1.4, {})])
    mk('irina_swap', 1.4, swap, dt=0.025, events={0.8: 'swap'})

    def puppet(t):
        # «Марионетка»: левая рука поднимается и «держит крестовину», посох в правой поднят перед собой, как дирижёрская палочка;
        # рывок нитей (0.7 — захват), дальше — irina_puppet_hold
        up = P(left_arm=[-124, 0, -26], right_arm=[-60, 0, 20], head=[-10, 0, 8], torso=[-6, 0, 0])
        jerk = P(left_arm=[-112, 0, -26], right_arm=[-54, 0, 20], head=[-10, 0, 8], torso=[0, 0, 0])
        return keyed(t, [(0, {}), (0.6, up), (0.7, jerk), (0.8, jerk), (1.0, up)])
    mk('irina_puppet', 1.0, puppet, dt=0.025, events={0.7: 'puppet'})

    def puppet_hold(t):
        # держит марионетку (loop 1 с): левая рука и посох поочерёдно подёргивают нити
        ph = t / 1.0 * TAU
        return {'body': {'pos': [0, 0, 0], 'rot': [0, 4 * math.sin(ph), 0]}, 'torso': {'rot': [-6, 0, 0]},
                'head': {'rot': [-10, 0, 8 + 3 * math.sin(ph)]}, 'hat': {'rot': [0, 0, 0]},
                'left_arm': {'rot': [-124 + 8 * math.sin(ph), 0, -26]}, 'right_arm': {'rot': [-60 + 5 * math.sin(ph + math.pi), 0, 20]},
                'right_leg': {'rot': [0, 0, 0]}, 'left_leg': {'rot': [0, 0, 0]}}
    mk('irina_puppet_hold', 1.0, puppet_hold, loop=True)

    # ---------------- контроллер «ткань и нити» (ленты, рукава, завязки, кончик шляпы, нити)
    mk('irina_cloth_idle', 4.0, lambda t: cloth_pose(t, per=4.0), loop=True)
    mk('irina_cloth_walk', 1.2, lambda t: cloth_pose(t, wind=12, amp=1.2, per=1.2, swirl=0.4,
                                                    legs=tuple(max(0.0, -v) for v in walk_legs(t))), loop=True)
    mk('irina_cloth_storm', 2.0, lambda t: cloth_pose(t, wind=14, amp=2.0, per=1.0, swirl=1.0, thr_r=1.25), loop=True)

    def cloth_spawn(t):
        # нити плотно обвиты (радиус 0.35) и быстро вращаются — кокон; на 2.6 разлетаются (радиус 1.5), к 7.0 — обычный
        k = env(t, 2.6, 3.2)
        r = 0.32 + (1.55 - 0.32) * k - 0.55 * env(t, 3.4, 6.5)
        lg = spawn(t)                        # ноги вперёд (сидит в коконе) — передние ленты лежат на коленях, а не сквозь них
        return cloth_pose(t, wind=12 * (1 - env(t, 4, 7)), amp=1 + 1.0 * k, per=1.0 + env(t, 3, 7) * 3, thr_r=r,
                          legs=(max(0.0, -lg['right_leg']['rot'][0]), max(0.0, -lg['left_leg']['rot'][0])))
    mk('irina_cloth_spawn', 7.0, cloth_spawn)

    def cloth_death(t):
        k = env(t, 3.6, 4.8)
        lg = death_body(t)                   # на коленях / лёжа: передние ленты ложатся на ноги
        return cloth_pose(t, amp=1 - 0.8 * k, per=2.0 + 4 * k, swirl=1 - 0.7 * k,
                          thr_r=max(0.001, 1.0 + 0.6 * env(t, 0, 1) - 1.6 * env(t, 3.8, 5.0)),
                          legs=(max(0.0, -lg['right_leg']['rot'][0]), max(0.0, -lg['left_leg']['rot'][0])))
    a = mk('irina_cloth_death', 5.0, cloth_death)
    a.loop = 'hold'

    def cloth_cocoon(t):
        # «Только мой»: нити вокруг неё уходят в кокон (сжимаются к 0 к 1.6, снова появляются к 5.8)
        r = 1.0 - env(t, 1.0, 1.6, 5.4, 5.9) * 0.999
        return cloth_pose(t, wind=8, amp=1.4, per=1.4, swirl=1.6, thr_r=max(0.001, r))
    mk('irina_cloth_cocoon', 6.2, cloth_cocoon)
    return out


def death_hat(t, pose, pose_off):
    """Ключи кости hat в irina_death (оси Blockbench): до 2.3 — на голове; 2.3→2.45 приподнимается и уходит назад над капюшоном
    (не задевая его), 2.45→2.9 падает назад-вправо на землю и дальше лежит в HAT_LAND, хотя голова падает вместе с телом.
    Кость hat — дочь head, поэтому ключ = (мир головы)⁻¹ · (нужное место шляпы); FK тот же, что у GeckoLib (tools/irina_anim_check.py)."""
    import irina_anim_check as CHK
    rig = CHK.rig_cached()
    t0, t1, t2 = DEATH_T
    on_head = rig.world_json(pose_off)['hat']
    lift = CHK.M4(on_head[:3, :3], on_head[:3, 3] + np.array([3.0, 6.0, 7.0]))
    land = CHK.M4(CHK.zyx([HAT_LAND[1][0], HAT_LAND[1][1], HAT_LAND[1][2]]), np.array(HAT_LAND[0], float))
    if t < t1:
        D = CHK.blend(on_head, lift, ease_io((t - t0) / (t1 - t0)))
    elif t < t2:
        k = (t - t1) / (t2 - t1)
        D = CHK.blend(lift, land, 1 - (1 - k) ** 2)     # в сторону — сразу (отлетает от капюшона), вниз — с ускорением
        D[1, 3] = lift[1, 3] + (land[1, 3] - lift[1, 3]) * k ** 3
    else:
        D = land
    return rig.local_json(rig.world_json(pose)['head'], 'hat', D)


# ================================================================== запись
def main(args):
    import gen_replica_break as RB          # «Реплика»: irina_replica_break + fx/печати (tools/gen_replica_break.py)
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
    allan = {a.name: a.to_json() for a in an}
    import guard_break_irina                 # T32 «Сломать блок»: нити рвут защиту, удар посохом (tools/guard_break_irina.py)
    allan['irina_guard_break'] = guard_break_irina.build()
    write_json(os.path.join(A, 'animations', 'entity', 'irina.animation.json'),
               {'format_version': '1.8.0', 'animations': RB.add_anims('irina', allan)}, compact=True)
    WRITTEN.append('animations/entity/irina.animation.json')
    nc = sum(len(b.cubes) for b in m.bones.values())
    print('irina: bones %d, cubes %d, tex %s, anims %d' % (len(m.bones), nc, m.tex_px, len(an)))
    import gen_irina_staff
    gen_irina_staff.main()
    if '--no-fx' not in args:
        import gen_irina_fx
        gen_irina_fx.run(sys.modules[__name__], args)
        RB.run_assets(('irina',))
    import irina_render
    if '--html' in args:
        irina_render.write_html()
    if '--shots' in args:
        irina_render.shots(args)
    return m, an


if __name__ == '__main__':
    main(sys.argv[1:])
