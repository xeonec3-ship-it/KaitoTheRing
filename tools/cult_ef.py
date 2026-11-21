#!/usr/bin/env python3
"""
T26 Глава Культа — удары косой FireBoss (Iron's) по эталону Epic Fight (владелец 21.11; правила — docs/specs/anim_style_epicfight.md).

Позы Iron's (хват Тироса, коса по ходу лезвием) не трогаем — меняем РАСПРЕДЕЛЕНИЕ ВРЕМЕНИ внутри анимации, как у эталона:
замах дотягивается медленнее (замедление в позу), сам удар — быстрее (0.1–0.25 с, пик скорости на тике урона), возврат — длиннее.
Тики урона (FireBossEntity, anim_check.IRON_HITS) и длины анимаций НЕ меняются: время ключей переводится монотонной гладкой
кривой g(t) (кубическая Эрмита с монотонными наклонами, Фрич—Карлсон), неподвижные точки — 0, тики ударов, конец. Около удара
наклон g = k < 1 (сжатие), между ударами > 1 (растяжение). Изинг каждого участка (в т.ч. easeInElastic с аргументами, step) сохраняется
— сдвигаются только времена ключей; наклон g меняется плавно, поэтому на стыках участков скорость почти не скачет (проверщик рывков
tools/scythe_jitter.py).
Вызывается из gen_cult_leader_extra.write_anims ДО позы хвата и поправок косы (hold_additive, smooth_clear), чтобы те работали
уже по новым временам.
"""
import math

import anim_check

# сжатие удара: окно [hit − A, hit + B] (с) → [hit − A·K, hit + B·K]
A, B, K = 0.15, 0.12, 0.6
NAMES = ('scythe_dagger_double_horizontal', 'scythe_backpedal', 'scythe_sideslash_downslash_sideslash', 'scythe_jump_combo',
         'scythe_downslash_sideslash', 'scythe_horizontal_slash_spin', 'scythe_dagger_combo_1')


def _pchip(xs, ys):
    """Монотонная кубическая Эрмита (Фрич—Карлсон) через точки (xs, ys) → функция."""
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(j for j in range(n - 1) if xs[j] <= x)
        t = (x - xs[i]) / h[i]
        h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        return h00 * ys[i] + h10 * h[i] * m[i] + h01 * ys[i + 1] + h11 * h[i] * m[i + 1]
    return f


def _quintic(x0, x1, y0, y1, m0, m1):
    """Квинтика Эрмита на [x0, x1]: значения, наклоны, вторые производные = 0 на концах (C2-стык — без рывка на узле)."""
    h = x1 - x0

    def f(x):
        t = (x - x0) / h
        h0 = 1 - 10 * t ** 3 + 15 * t ** 4 - 6 * t ** 5
        h1 = t - 6 * t ** 3 + 8 * t ** 4 - 3 * t ** 5
        h4 = 10 * t ** 3 - 15 * t ** 4 + 6 * t ** 5
        h5 = -4 * t ** 3 + 7 * t ** 4 - 3 * t ** 5
        return h0 * y0 + h1 * h * m0 + h4 * y1 + h5 * h * m1
    return f


def warp_fn(L, knots, k=K):
    """g: старое время → новое через узлы [(старое, новое)]: 0 → 0, пик скорости косы у каждого удара → тик урона, конец → конец.
    Наклон в узлах удара k (удар быстрее), на концах 1; между узлами — квинтика Эрмита (g, g', g'' непрерывны)."""
    pts = [(0.0, 0.0, 1.0)] + [(kn[0], kn[1], kn[2] if len(kn) > 2 else k) for kn in sorted(knots)] + [(L, L, 1.0)]
    segs = [(p0[0], p1[0], _quintic(p0[0], p1[0], p0[1], p1[1], p0[2], p1[2])) for p0, p1 in zip(pts, pts[1:])]

    def g(t):
        for x0, x1, f in segs:
            if t <= x1:
                return f(max(t, x0))
        return L
    return g


def peaks(an, hits, win=0.2):
    """Пик угловой скорости НАПРАВЛЕНИЯ клинка (рукоять → остриё; как в tools/anim_style_check — проворот косы вокруг древка не
    в счёт) около каждого тика урона. Кинематика как в игре (двойной поворот кисти)."""
    import numpy as np
    M = anim_check.Model('cult_leader')
    L = float(an['animation_length'])
    out = []
    for h in hits:
        ts = list(np.arange(max(0.0, h - win), min(L, h + win) + 1e-9, 1 / 60.0))
        ds = []
        for t in ts:
            it = M.item_world(M.world(an, t))
            d = it[M.tip_i] - it[M.grip_i]
            ds.append(d / np.linalg.norm(d))
        w = [math.acos(max(-1.0, min(1.0, float(ds[i] @ ds[i + 1])))) for i in range(len(ds) - 1)]
        i_ = int(np.argmax(w))
        out.append(float((ts[i_] + ts[i_ + 1]) / 2))
    return out


def _fmt(t):
    return ('%.6g' % t) if t > 0 else '0.0'


def _inv(g, L, u):
    lo, hi = 0.0, L
    for _ in range(50):
        mid = (lo + hi) / 2
        if g(mid) < u:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def warp_anim(an, knots, k=K, win=0.25, step=1 / 40.0):
    """Ключи вне окон удара — на новое время g(t) с тем же изингом; в окне [пик − win, пик + win] (расширенном до ключей
    канала, чтобы крайние участки не резались) — частая выборка исходной кривой (anim_check.chan_at) на новом времени: так
    удар действительно сжимается, а не только средняя длительность длинного участка."""
    L = float(an['animation_length'])
    g = warp_fn(L, knots, k)
    wins = [(kn[0] - win, kn[0] + win) for kn in knots if (kn[2] if len(kn) > 2 else k) < 1.0]
    for bone in an.get('bones', {}).values():
        for kind, ch in list(bone.items()):
            if not isinstance(ch, dict) or 'vector' in ch:
                continue
            ts = sorted(float(t) for t in ch)
            byt = {float(t): v for t, v in ch.items()}
            bake = []
            for a, b in wins:
                lo = max([t for t in ts if t <= a] or [0.0])
                hi = min([t for t in ts if t >= b] or [L])
                if hi > lo:
                    bake.append((lo, hi))
            out = {}
            for t in ts:
                if any(lo < t < hi for lo, hi in bake):
                    continue
                out[_fmt(g(t))] = byt[t]
            for lo, hi in bake:
                u0, u1 = g(lo), g(hi)
                n = max(2, int(round((u1 - u0) / step)))
                for q in range(1, n):
                    u = u0 + (u1 - u0) * q / n
                    v = anim_check.chan_at(ch, _inv(g, L, u))
                    out[_fmt(u)] = {'vector': [round(float(x), 4) for x in v]}
                # ключ на правой границе окна — исходный; его изинг относился к длинному участку, теперь до него — частая выборка
                kr = _fmt(g(hi))
                if kr in out and isinstance(out[kr], dict) and out[kr].get('easing'):
                    out[kr] = {'vector': out[kr].get('vector') or out[kr].get('post') or out[kr].get('pre')}
            bone[kind] = dict(sorted(out.items(), key=lambda x: float(x[0])))
    for key in ('sound_effects', 'particle_effects', 'timeline'):
        if isinstance(an.get(key), dict):
            an[key] = {_fmt(g(float(t))): v for t, v in an[key].items()}
    return g


# k по анимации — самое сильное сжатие, при котором рывки косы в пороге Тироса (tools/scythe_jitter.py); подбор — find_k()
KS = {'scythe_dagger_double_horizontal': 0.5, 'scythe_backpedal': 0.45, 'scythe_sideslash_downslash_sideslash': 0.55,
      'scythe_jump_combo': 0.45, 'scythe_downslash_sideslash': 0.6, 'scythe_horizontal_slash_spin': 1.0}
# scythe_dagger_combo_1 — не трогаем: даже один сдвиг пиков на тики (k = 1) даёт рывок сверх порога Тироса


def apply(anims, names=None, ks=None):
    """Пик удара → тик урона, удар быстрее (k); возвращает {анимация: [(тик, пик был), ...], k}."""
    rep = {}
    ks = KS if ks is None else ks
    names = tuple(ks) if names is None else names
    for n in names:
        if n not in anims:
            continue
        hits = [t / 20.0 for t in anim_check.IRON_HITS.get(n, [])]
        if not hits:
            continue
        k = ks.get(n, K)
        pk = peaks(anims[n], hits)
        # узлы строго по порядку и не ближе 0.12 с (удары кинжалом левой — у косы там пика нет, пик соседнего удара не берём)
        knots = []
        for p_, h in zip(pk, hits):
            if abs(p_ - h) > 0.15:                 # пик у края окна — это соседнее движение: тик неподвижен, без сжатия
                p_, m = h, 1.0
            else:
                m = k
            if knots and (p_ <= knots[-1][0] + 0.12 or h <= knots[-1][1] + 0.12):
                continue
            knots.append((p_, h, m))
        warp_anim(anims[n], knots, k)
        rep[n] = ([(h, round(p_, 3), m) for p_, h, m in knots], k)
    return rep
