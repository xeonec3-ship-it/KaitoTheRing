#!/usr/bin/env python3
"""
Ткань в анимациях T26/T30 (проверка анимаций 20.11): плащ Главы Культа (кость cape) и полы камзола Эреба (coat_*) по каждой
анимации файла — и нашей, и Iron's (их зовут под теми же именами) — получают ключи X так, чтобы ткань
  * не уходила вперёд: плащ и задние полы — не впереди вертикали (наклон корпуса назад, ноги назад);
  * не проходила сквозь ноги: задняя ткань отходит назад за ногу, передняя пола — вперёд перед ногой ровно настолько, насколько её толкает нога.
Добавка считается покадрово (0.05 с) по кинематике tools/anim_check.py, затем сглаживается (максимум в окне ±0.1 с) и пишется ключами
через 0.1 с; где добавка не нужна — ключей не добавляется. Знак: у задней ткани + по X (Bedrock) — назад, у передней − — вперёд.
Вызывается генераторами анимаций (gen_cult_leader_extra.write_anims, gen_ereb_anims.write).
"""
import math

import numpy as np

import anim_check as C

STEP, KEY = 0.05, 0.1
TRIES = list(range(0, 72, 3))


def _channel_val(an, bone, t):
    bk = an['bones'].get(bone, {})
    return C.chan_at(bk['rotation'], t) if 'rotation' in bk else [0.0, 0.0, 0.0]


def _leg_fwd(W, f, leg):
    v = C.ap(W[leg], (0, -10, 0)) - C.ap(W[leg], (0, 0, 0))
    return float(v @ f) / (np.linalg.norm(v) + 1e-9)


def _ok(M, an, t, bone, kind, extra, base, strict=True):
    """extra — добавка по X (Bedrock): у задней ткани + назад; у передней — со знаком (− вперёд, + назад)."""
    r = [base[0] + extra, base[1], base[2]]
    W = M.world(an, t, {bone: r})
    bw = W[bone]
    top, bot = C.ap(bw, (0, 0, 0)), C.ap(bw, (0, -10, 0))
    v = bot - top
    f = W['body'][:3, :3] @ np.array([0.0, 0.0, -1.0])          # «вперёд» — по взгляду корпуса (в разворотах и вращениях тоже)
    f[1] = 0
    f /= np.linalg.norm(f) + 1e-9
    fwd = float(v @ f) / (np.linalg.norm(v) + 1e-9)
    if kind == 'back' and fwd > -math.sin(math.radians(3)):
        return False
    if kind == 'front' and strict:                               # передняя пола — вперёд не дальше, чем её толкает нога (+15°)
        leg = 'right_leg' if bone.endswith('_r') else 'left_leg'
        lim = max(math.sin(math.radians(8)), _leg_fwd(W, f, leg) + math.sin(math.radians(15)))
        if fwd > lim:
            return False
    pts = np.array([C.ap(bw, (x, y, z)) for x in (-1.6, 0, 1.6) for y in (-2, -4.5, -7, -9.5, -12) for z in (0.0,)])
    for leg in ('right_leg', 'left_leg'):
        if M.inside(W, leg, pts, margin=0.15).any():
            return False
    return True


def need(M, an, bone, kind):
    L = float(an.get('animation_length') or 0)
    n = max(1, int(round(L / STEP)))
    ts = [min(L, i * STEP) for i in range(n + 1)]
    out = []
    for t in ts:
        base = _channel_val(an, bone, t)
        cands = TRIES if kind == 'back' else [v for x in TRIES for v in ((x, -x) if x else (0,))]
        e = None
        for strict in (True, False):                 # не нашлось — хотя бы не сквозь ноги (вперёд ровно на сколько нужно)
            for x in cands:
                if _ok(M, an, t, bone, kind, x, base, strict):
                    e = x
                    break
            if e is not None:
                break
        if e is None:
            e = 0
        out.append(e)
    return ts, out


SKIP = ('dead_king_', 'rise_from_ground_', 'keeper_')     # лёжа/из-под земли — на боссах T26/T30 не играют


def bake(boss, anims, only=None):
    """Дописывает/правит каналы ткани во всех анимациях словаря anims (на месте). Возвращает {анимация: макс. добавка}."""
    M = C.Model(boss)
    report = {}
    for name, an in anims.items():
        if (only and name not in only) or name.startswith(SKIP):
            continue
        if not an.get('animation_length'):
            continue
        for bone, kind in M.cloth.items():
            if bone not in M.bones:
                continue
            ts, ex = need(M, an, bone, kind)
            if not any(ex):
                continue
            w = int(round(0.1 / STEP))
            sm = [max(ex[max(0, i - w):i + w + 1], key=abs) for i in range(len(ex))]
            L = ts[-1]
            kts = sorted(set([round(i * KEY, 4) for i in range(int(L / KEY) + 1)] + [round(L, 4)]))
            bk = an['bones'].setdefault(bone, {})
            old = bk.get('rotation')
            ch = {}
            for t in kts:
                i = min(len(ts) - 1, int(round(t / STEP)))
                base = _channel_val(an, bone, t) if old is not None else [0.0, 0.0, 0.0]
                d = sm[i]
                ch['%.4g' % t if t else '0.0'] = {'vector': [round(base[0] + d, 2), round(base[1], 2), round(base[2], 2)]}
            bk['rotation'] = ch
            report.setdefault(name, {})[bone] = max(ex, key=abs)
    return report


def explicit(anims, names, bones):
    """Явные ключи (проверка 20.11): у наших анимаций каждая основная кость задана в начале и в конце — кость без ключей
    не берёт позу прошлой анимации. Недостающие каналы rotation — нулём в 0 и в конце (нуль = поза покоя модели)."""
    for n in names:
        an = anims[n]
        L = float(an['animation_length'])
        for b in bones:
            bk = an['bones'].setdefault(b, {})
            if 'rotation' not in bk:
                bk['rotation'] = {'0.0': {'vector': [0, 0, 0]}, '%.4g' % L: {'vector': [0, 0, 0]}}


# ------------------------------------------------------------------ оружие в анимациях Iron's
GRID = [(x, 0, z) for x in range(-90, 91, 15) for z in range(-90, 91, 15)]
GRID3 = [(x, y, z) for x in range(-120, 121, 20) for y in range(-80, 81, 20) for z in range(-120, 121, 20)]   # если в плоской сетке нет
PARTS = ('torso', 'head', 'armor_head', 'right_leg', 'left_leg')


def _weapon_bad(M, W, edge):
    ip = M.item_world(W)
    if np.linalg.det(W['bipedHandRight'][:3, :3]) < 1e-6:
        return 0
    bad = 0
    for bp in PARTS:
        if bp in M.bones:
            bad += int(M.inside(W, bp, ip, margin=0.6).sum() >= 2)
    if not edge and ip[:, 1].min() < -0.5:
        bad += 1
    return bad


def strike_windows(name, an, half=0.12):
    """Окна ударов (события timeline с оружием и тики AttackKeyframe Iron's) ±half с: там поворот косы не трогаем — он задаёт
    плоскость лезвия и остриё по ходу удара (как у Тироса)."""
    return [(t - half, t + half) for t, e in C.hit_times(name, an) if e in C.WEAPON_EVENTS]


def weapon(boss, anims, names, edge=0.25, allow_ground=None, step=0.025):
    """Кисть с оружием: в кадрах, где коса/рапира уходит в землю или сквозь тело/ноги, к кости bipedHandRight добавляется наименьший
    поворот (сетка 15° по X/Z, при неудаче — 20° по трём осям; ближе к соседнему кадру). Ключи — каждые 0.025 с (полтика: между ними GeckoLib интерполирует по кадрам), сглаживание
    принимается только в кадрах, которые после него остаются чистыми. edge — сколько секунд с краёв не проверять землю."""
    M = C.Model(boss)
    rep = {}
    for name in names:
        an = anims.get(name)
        if not an or not an.get('animation_length'):
            continue
        L = float(an['animation_length'])
        n = max(1, int(round(L / step)))
        ts = [min(L, i * step) for i in range(n + 1)]
        base = [_channel_val(an, 'bipedHandRight', t) for t in ts]
        ag = (allow_ground or {}).get(name)

        def axis(W):
            ip = M.item_world(W)
            d = ip[M.tip_i] - ip[M.grip_i]
            return d / (np.linalg.norm(d) + 1e-9)

        def ang(u, v):
            return math.degrees(math.acos(max(-1.0, min(1.0, float(u @ v)))))

        orig_ax = [axis(M.world(an, t)) for t in ts]
        off, prev, prev_ax, fails = [], (0, 0, 0), None, []
        prot = strike_windows(name, an)
        for i, (t, b) in enumerate(zip(ts, base)):
            edge_t = t < edge or t > L - edge or bool(ag and ag[0] <= t <= ag[1])
            W0 = M.world(an, t)
            if any(a <= t <= z for a, z in prot):            # удар: поворот косы как в анимации
                off.append((0, 0, 0))
                prev, prev_ax = (0, 0, 0), axis(W0)
                continue
            # не быстрее исходного движения оружия (×2, но не меньше 25° за шаг) — иначе доворот виден как рывок
            lim = 25.0 if i == 0 else max(25.0, 2.0 * ang(orig_ax[i - 1], orig_ax[i]))

            def good(g):
                W = M.with_hand(W0, an, t, [b[0] + g[0], b[1] + g[1], b[2] + g[2]]) if any(g) else W0
                if _weapon_bad(M, W, edge_t):
                    return None
                ax = axis(W)
                return ax if prev_ax is None or ang(prev_ax, ax) <= lim else None

            ax = good((0, 0, 0))
            if ax is not None and not any(prev):
                off.append((0, 0, 0))
                prev, prev_ax = (0, 0, 0), ax
                continue
            best = None
            for grid in ([(0, 0, 0)], GRID, GRID3):
                for g in grid:
                    a2 = good(g)
                    if a2 is not None:
                        cost = math.dist(g, prev) + 0.3 * math.dist(g, (0, 0, 0))
                        if best is None or cost < best[0]:
                            best = (cost, g, a2)
                if best:
                    break
            if best is None:                     # чистого и плавного нет — плавность важнее: ближайшее к прошлому кадру
                fails.append(i)
                g = prev
                W = M.with_hand(W0, an, t, [b[0] + g[0], b[1] + g[1], b[2] + g[2]])
                best = (0, g, axis(W))
            off.append(best[1])
            prev, prev_ax = best[1], best[2]
        # путь через трудные кадры: в окне ±0.25 с вокруг кадра без плавного чистого решения ищется цепочка чистых положений кисти
        # (динамическое программирование), доворот между соседними кадрами — не больше 20° по каждой оси (на быстром взмахе — не больше
        # исходного поворота оружия за шаг); края окна — как были
        W8 = int(round(0.25 / step))
        done = set()
        for i in fails:
            if i in done:
                continue
            lo, hi = max(0, i - W8), min(len(ts) - 1, i + W8)
            cands = []
            for j in range(lo, hi + 1):
                t, b = ts[j], base[j]
                e_t = t < edge or t > L - edge or bool(ag and ag[0] <= t <= ag[1])
                if j in (lo, hi) or any(a <= t <= z for a, z in prot):
                    cands.append([off[j]])
                    continue
                Wj = M.world(an, t)
                cj = [g for g in GRID + GRID3
                      if not _weapon_bad(M, M.with_hand(Wj, an, t, [b[0] + g[0], b[1] + g[1], b[2] + g[2]]), e_t)]
                cands.append(cj or [off[j]])
            # доворот за шаг — не больше 20° или, на быстром взмахе, не больше исходного поворота оружия за этот шаг
            lims = [20.0] + [max(20.0, ang(orig_ax[lo + j - 1], orig_ax[lo + j])) for j in range(1, len(cands))]
            INF = float('inf')
            cost = [[0.3 * math.dist(g, (0, 0, 0)) for g in cands[0]]]
            back = [[-1] * len(cands[0])]
            for j in range(1, len(cands)):
                cj, cp = cands[j], cands[j - 1]
                row, br = [], []
                for g in cj:
                    best_c, best_k = INF, -1
                    for k2, h in enumerate(cp):
                        if cost[-1][k2] < INF and max(abs(g[q] - h[q]) for q in range(3)) <= lims[j]:
                            c = cost[-1][k2] + 0.3 * math.dist(g, (0, 0, 0)) + 0.1 * math.dist(g, h)
                            if c < best_c:
                                best_c, best_k = c, k2
                    row.append(best_c)
                    br.append(best_k)
                cost.append(row)
                back.append(br)
            if cost[-1][0] < INF:
                k2 = 0
                for j in range(len(cands) - 1, -1, -1):
                    off[lo + j] = cands[j][k2]
                    k2 = back[j][k2]
                done.update(range(lo, hi + 1))
        if not any(any(o) for o in off):
            continue
        sm = off
        ch = {}
        for i, t in enumerate(ts):
            v = [round(base[i][k] + sm[i][k], 2) for k in range(3)]
            ch['%.4g' % t if t else '0.0'] = {'vector': v}
        an['bones'].setdefault('bipedHandRight', {})['rotation'] = ch
        rep[name] = sum(1 for o in off if any(o))
    return rep


# ------------------------------------------------------------------ коса над землёй сдвигом вдоль древка (ориентация не меняется)
SHAFT = np.array([1.0, 1.0, 0.0]) / math.sqrt(2)     # древко косы в осях предмета (cult_scythe: от подтока к головке)


def lift(boss, anims, names, target=0.3, max_slide=6.0, step=0.025, allow_ground=None):
    """Где лезвие/подток ниже земли (точки предмета y < −0.5 px), коса сдвигается в кулаке вдоль древка (ключи position кости
    bipedHandRight) ровно настолько, чтобы нижняя точка была на target px над землёй, — поворот косы при этом тот же, что в анимации
    (Тирос держит так же). Сдвиг сглаживается (максимум в окне ±0.1 с, вход/выход 0.1 с), не больше max_slide px.
    Возвращает {анимация: макс. сдвиг}."""
    M = C.Model(boss)
    rot_item = M.item_m[:3, :3] @ SHAFT
    rep = {}
    for name in names:
        an = anims.get(name)
        if not an or not an.get('animation_length'):
            continue
        L = float(an['animation_length'])
        n = max(1, int(round(L / step)))
        ts = [min(L, i * step) for i in range(n + 1)]
        ag = (allow_ground or {}).get(name)
        need = []
        for t in ts:
            if ag and ag[0] <= t <= ag[1]:
                need.append(0.0)
                continue
            W = M.world(an, t)
            if np.linalg.det(W['bipedHandRight'][:3, :3]) < 1e-6:
                need.append(0.0)
                continue
            y = M.item_world(W)[:, 1].min()
            if y >= -0.5:
                need.append(0.0)
                continue
            R2 = W[C.HAND2][:3, :3]
            d_loc = R2 @ R2 @ rot_item                          # древко в осях кисти до её поворота = в осях руки
            d_loc = d_loc / (np.linalg.norm(d_loc) + 1e-9)
            d_w = W['right_arm'][:3, :3] @ d_loc
            s = (target - y) / d_w[1] if abs(d_w[1]) > 0.3 else 0.0
            if abs(s) > max_slide:
                s = 0.0
            if s:                                               # сдвиг не должен завести косу в тело
                ip = M.item_world(W) + d_w * s
                if any(M.inside(W, bp, ip, margin=0.6).sum() >= 2 for bp in PARTS if bp in M.bones):
                    s = 0.0
            need.append(float(s))
        if not any(need):
            continue
        w = int(round(0.1 / step))
        sm = [max(need[max(0, i - w):i + w + 1], key=abs) for i in range(len(need))]
        # вход/выход: линейно за 0.1 с к ненулевому участку
        out = list(sm)
        for i in range(len(sm)):
            if sm[i] == 0:
                near = [(abs(j - i), sm[j]) for j in range(max(0, i - w), min(len(sm), i + w + 1)) if sm[j]]
                if near:
                    dist, v = min(near)
                    out[i] = v * (1 - dist / (w + 1))
        bk = an['bones'].setdefault('bipedHandRight', {})
        orig = bk.get('position')
        val = (lambda t: C.chan_at(orig, t)) if orig is not None else (lambda t: [0.0, 0.0, 0.0])
        keys = {}
        if isinstance(orig, dict) and 'vector' not in orig:
            for k, e in orig.items():
                keys[round(float(k), 4)] = e if isinstance(e, dict) else {'vector': e}
        for i, t in enumerate(ts):
            lo, hi = max(0, i - 1), min(len(out) - 1, i + 1)
            if not (out[lo] or out[i] or out[hi]):
                continue
            W = M.world(an, t)
            R2 = W[C.HAND2][:3, :3]
            d = R2 @ R2 @ rot_item
            d = d / (np.linalg.norm(d) + 1e-9) * out[i]
            o = val(t)
            keys[round(t, 4)] = {'vector': [round(o[0] - d[0], 3), round(o[1] + d[1], 3), round(o[2] + d[2], 3)]}
        bk['position'] = {('%.4g' % t if t else '0.0'): keys[t] for t in sorted(keys)}
        rep[name] = round(max(out, key=abs), 2)
    return rep


# ------------------------------------------------------------------ коса мимо тела и земли сдвигом (поворот косы не меняется)
NUDGE = sorted({(x, y, z) for x in range(-8, 9, 2) for y in range(0, 11, 2) for z in range(-10, 9, 2)},
               key=lambda v: (v[0] ** 2 + v[1] ** 2 + v[2] ** 2, v))


def nudge(boss, anims, names, step=0.025, allow_ground=None, win=0.1):
    """Где коса в земле или сквозь тело, она целиком сдвигается в кулаке (ключи position кости bipedHandRight, до 8–10 px по осям,
    вверх до 10 px) — наименьшим сдвигом, при котором кадр чистый. Поворот косы — ровно как в анимации: плоскость лезвия и остриё
    на ударах не меняются (доворот кисти их ломал). Сдвиг держится по участку нарушений (максимум в окне ±0.1 с) и плавно
    уходит в ноль за 0.1 с по краям. Возвращает {анимация: макс. сдвиг px}."""
    M = C.Model(boss)
    rep = {}
    for name in names:
        an = anims.get(name)
        if not an or not an.get('animation_length'):
            continue
        L = float(an['animation_length'])
        n = max(1, int(round(L / step)))
        ts = [min(L, i * step) for i in range(n + 1)]
        ag = (allow_ground or {}).get(name)
        hb = an['bones'].get('bipedHandRight', {})
        need = []
        for t in ts:
            W = M.world(an, t)
            if np.linalg.det(W['bipedHandRight'][:3, :3]) < 1e-6:
                need.append((0, 0, 0))
                continue
            gr = not (ag and ag[0] <= t <= ag[1])
            if not _weapon_bad(M, W, not gr):
                need.append((0, 0, 0))
                continue
            r = C.chan_at(hb['rotation'], t) if 'rotation' in hb else [0.0, 0.0, 0.0]
            best = (0, 0, 0)
            for d in NUDGE[1:]:
                if not _weapon_bad(M, M.with_hand(W, an, t, r, d), not gr):
                    best = d
                    break
            need.append(best)
        if not any(any(v) for v in need):
            continue
        w = max(1, int(round(win / step)))
        sm = [max(need[max(0, i - w):i + w + 1], key=lambda v: v[0] ** 2 + v[1] ** 2 + v[2] ** 2) for i in range(len(need))]
        out = list(sm)
        for i in range(len(sm)):
            if not any(sm[i]):
                near = [(abs(j - i), sm[j]) for j in range(max(0, i - w), min(len(sm), i + w + 1)) if any(sm[j])]
                if near:
                    dist, v = min(near, key=lambda q: q[0])
                    out[i] = tuple(x * (1 - dist / (w + 1)) for x in v)
        orig = hb.get('position')
        val = (lambda t: C.chan_at(orig, t)) if orig is not None else (lambda t: [0.0, 0.0, 0.0])
        keys = {}
        if isinstance(orig, dict) and 'vector' not in orig:
            for k, e in orig.items():
                keys[round(float(k), 4)] = e if isinstance(e, dict) else {'vector': e}
        for i, t in enumerate(ts):
            lo, hi = max(0, i - 1), min(len(out) - 1, i + 1)
            if not (any(out[lo]) or any(out[i]) or any(out[hi])):
                continue
            o = val(t)
            keys[round(t, 4)] = {'vector': [round(o[k] + out[i][k], 3) for k in range(3)]}
        an['bones'].setdefault('bipedHandRight', {})['position'] = {('%.4g' % t if t else '0.0'): keys[t] for t in sorted(keys)}
        rep[name] = round(max(math.dist(v, (0, 0, 0)) for v in out), 1)
    return rep


# ------------------------------------------------------------------ коса мимо земли и тела без рывков (21.11, проверка рывков)
def _clusters(flags, ts, gap=0.15):
    out, cur = [], None
    for f, t in zip(flags, ts):
        if f:
            if cur and t - cur[1] <= gap:
                cur[1] = t
            else:
                cur = [t, t]
                out.append(cur)
    return out


def _apply(an, bone, kind, off, a0, a1, ramp, step=0.025):
    """К каналу кости прибавляется постоянное смещение off на [a0, a1] с плавным входом/выходом ramp с (ключи через step внутри)."""
    bk = an['bones'].setdefault(bone, {})
    orig = bk.get(kind)
    val = (lambda t: C.chan_at(orig, t)) if orig is not None else (lambda t: [0.0, 0.0, 0.0])
    L = float(an['animation_length'])
    lo, hi = max(0.0, a0 - ramp), min(L, a1 + ramp)
    keys = {}
    if isinstance(orig, dict) and 'vector' not in orig:
        for k, e in orig.items():
            t = round(float(k), 4)
            if not (lo < t < hi):
                keys[t] = e if isinstance(e, dict) else {'vector': e}
    elif orig is not None:
        keys[0.0] = {'vector': list(val(0))}
    n = max(2, int(math.ceil((hi - lo) / step)))
    for i in range(n + 1):
        t = round(lo + (hi - lo) * i / n, 4)
        w = 1.0 if a0 <= t <= a1 else (_smooth((t - lo) / max(1e-6, a0 - lo)) if t < a0 else _smooth((hi - t) / max(1e-6, hi - a1)))
        if (t <= 0 and a0 <= 0) or (t >= L and a1 >= L):
            w = 1.0
        o = val(t)
        keys[t] = {'vector': [round(o[j] + w * off[j], 3) for j in range(3)]}
    bk[kind] = {('%.4g' % t if t else '0.0'): keys[t] for t in sorted(keys)}


POS_GRID = sorted({(x, y, z) for x in range(-12, 13, 2) for y in range(0, 17, 2) for z in range(-12, 13, 2)},
                  key=lambda v: (v[0] ** 2 + v[1] ** 2 + v[2] ** 2, v))[1:]
ROT_GRID = sorted(set(GRID + GRID3) - {(0, 0, 0)}, key=lambda v: (v[0] ** 2 + v[1] ** 2 + v[2] ** 2, v))


def clear(boss, anims, names, step=0.025, ramp=0.15, allow_ground=None, passes=4):
    """Коса в земле или сквозь тело → на каждый участок нарушений ОДНО постоянное смещение с плавным входом/выходом (квинтика,
    ramp с): сначала сдвиг косы в кулаке (position кисти, поворот косы как в анимации), если сдвиг не помогает и участок не
    в окне удара — поворот кисти. Смещение подбирается так, чтобы был чист весь участок вместе с подъёмом и спуском.
    Раньше (weapon/nudge) поправка менялась каждые 0.025 с — коса дёргалась. Возвращает {анимация: [(t0, t1, 'pos'|'rot', смещение)]}."""
    M = C.Model(boss)
    rep = {}
    for name in names:
        an = anims.get(name)
        if not an or not an.get('animation_length'):
            continue
        L = float(an['animation_length'])
        ag = (allow_ground or {}).get(name)
        prot = strike_windows(name, an)
        for _ in range(passes):
            n = max(1, int(round(L / step)))
            ts = [min(L, i * step) for i in range(n + 1)]

            def bad_at(t, W):
                if np.linalg.det(W['bipedHandRight'][:3, :3]) < 1e-6:
                    return False
                return bool(_weapon_bad(M, W, bool(ag and ag[0] <= t <= ag[1])))
            flags = [bad_at(t, M.world(an, t)) for t in ts]
            cl = _clusters(flags, ts)
            if not cl:
                break
            todo = [tuple(c) for c in cl]
            while todo:
                a0, a1 = todo.pop(0)
                lo, hi = max(0.0, a0 - ramp), min(L, a1 + ramp)
                fr = [t for t in ts if lo <= t <= hi]
                Ws = [(t, M.world(an, t)) for t in fr]
                hb = an['bones'].get('bipedHandRight', {})

                def wgt(t):
                    if a0 <= t <= a1:
                        return 1.0
                    return _smooth((t - lo) / max(1e-6, a0 - lo)) if t < a0 else _smooth((hi - t) / max(1e-6, hi - a1))

                def ok(kind, d):
                    for t, W in Ws:
                        w = wgt(t)
                        r = C.chan_at(hb['rotation'], t) if 'rotation' in hb else [0.0, 0.0, 0.0]
                        if kind == 'pos':
                            W2 = M.with_hand(W, an, t, r, [w * x for x in d])
                        else:
                            W2 = M.with_hand(W, an, t, [r[k] + w * d[k] for k in range(3)])
                        if bad_at(t, W2):
                            return False
                    return True
                found = None
                for d in POS_GRID:
                    if ok('pos', d):
                        found = ('pos', d)
                        break
                in_strike = any(not (hi < s0 or lo > s1) for s0, s1 in prot)
                if found is None and not in_strike:
                    for d in ROT_GRID:
                        if ok('rot', d):
                            found = ('rot', d)
                            break
                if found is None and a1 - a0 > 0.06:          # одного смещения на весь участок нет — пополам
                    m = round((a0 + a1) / 2 / step) * step
                    todo[:0] = [(a0, m), (min(a1, m + step), a1)]
                    continue
                if found is None and in_strike:                # удар: последнее средство — малый доворот (до 30°)
                    for d in ROT_GRID:
                        if max(abs(x) for x in d) <= 30 and ok('rot', d):
                            found = ('rot', d)
                            break
                if found is None:
                    continue
                _apply(an, 'bipedHandRight', 'position' if found[0] == 'pos' else 'rotation', found[1], a0, a1, ramp)
                rep.setdefault(name, []).append((round(a0, 3), round(a1, 3), found[0], found[1]))
    return rep


def _gauss(v, sigma):
    if sigma <= 0:
        return v
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.pad(v, ((r, r), (0, 0)), mode='edge')
    return np.stack([np.convolve(pad[:, j], k, mode='valid') for j in range(v.shape[1])], axis=1)


def smooth_clear(boss, anims, names, step=0.025, allow_ground=None, ncand=120, grow=6, sigma=3.0, tries=1, cont=2.0, kind='pos',
                 free_start=()):
    """Коса в земле или сквозь тело → плавный сдвиг косы в кулаке (position кисти; поворот косы как в анимации):
    по кадрам — допустимые сдвиги (наименьшие), выбор с непрерывностью (динамическое программирование: |d| + 0.7·|d − d_пред|),
    расширение на grow кадров, гауссово сглаживание σ = sigma кадров (кривая без ступенек — без рывков); кадры, что после
    сглаживания снова плохи, получают сдвиг ×1.3 (до tries раз). Где сдвига нет — остаётся (видно в проверке).
    Возвращает {анимация: макс. сдвиг px}."""
    M = C.Model(boss)
    rep = {}
    for name in names:
        an = anims.get(name)
        if not an or not an.get('animation_length'):
            continue
        L = float(an['animation_length'])
        ag = (allow_ground or {}).get(name)
        n = max(1, int(round(L / step)))
        ts = [min(L, i * step) for i in range(n + 1)]
        hb = an['bones'].setdefault('bipedHandRight', {})
        rot = lambda t: C.chan_at(hb['rotation'], t) if 'rotation' in hb else [0.0, 0.0, 0.0]
        Ws = [M.world(an, t) for t in ts]
        gr = [not (ag and ag[0] <= t <= ag[1]) for t in ts]

        prot = strike_windows(name, an)

        def bad(i, d):
            if not any(d):
                W = Ws[i]
            elif kind == 'pos':
                W = M.with_hand(Ws[i], an, ts[i], rot(ts[i]), list(d))
            else:
                r = rot(ts[i])
                W = M.with_hand(Ws[i], an, ts[i], [r[k] + d[k] for k in range(3)])
            if np.linalg.det(W['bipedHandRight'][:3, :3]) < 1e-6:
                return False
            return bool(_weapon_bad(M, W, not gr[i]))
        B = [bad(i, (0, 0, 0)) for i in range(len(ts))]
        if not any(B):
            continue
        cands = []
        for i in range(len(ts)):
            if not B[i]:
                cands.append([(0, 0, 0)])
                continue
            c = []
            strike = any(a <= ts[i] <= z for a, z in prot)
            grid = POS_GRID if kind == 'pos' else [d for d in ROT_GRID if not strike or max(abs(x) for x in d) <= 30]
            for d in grid:
                if not bad(i, d):
                    c.append(d)
                    if len(c) >= ncand:
                        break
            cands.append(c or [(0, 0, 0)])
        # непрерывность: DP по всем кадрам
        cost = [[math.dist(d, (0, 0, 0)) for d in cands[0]]]
        back = [[-1] * len(cands[0])]
        for i in range(1, len(ts)):
            row, br = [], []
            for d in cands[i]:
                best, bk = float('inf'), 0
                for k, e in enumerate(cands[i - 1]):
                    c = cost[-1][k] + cont * math.dist(d, e)
                    if c < best:
                        best, bk = c, k
                row.append(best + math.dist(d, (0, 0, 0)))
                br.append(bk)
            cost.append(row)
            back.append(br)
        k = int(np.argmin(cost[-1]))
        off = [None] * len(ts)
        for i in range(len(ts) - 1, -1, -1):
            off[i] = cands[i][k]
            k = back[i][k]
        off = np.array(off, float)
        mult = np.ones(len(ts))
        for _ in range(tries):
            o = off * mult[:, None]
            dil = o.copy()
            for i in range(len(ts)):                        # расширение: держим сдвиг ±grow кадров вокруг плохих кадров
                lo, hi = max(0, i - grow), min(len(ts), i + grow + 1)
                j = lo + int(np.argmax(np.linalg.norm(o[lo:hi], axis=1)))
                dil[i] = o[j]
            sm = _gauss(dil, sigma)
            if name not in free_start:                  # первый кадр — ровно поза кода (хват): поправка с нуля за 0.1 с
                sm = sm * np.array([_smooth(t / 0.1) for t in ts])[:, None]
            still = [i for i in range(len(ts)) if B[i] and bad(i, tuple(sm[i]))]
            if not still:
                break
            hit = np.zeros(len(ts), bool)
            for i in still:
                hit[max(0, i - grow):i + grow + 1] = True
            mult = np.where(hit, np.minimum(2.0, mult * 1.3), mult)
        if not np.abs(sm).max() > 1e-3:
            continue
        chn = 'position' if kind == 'pos' else 'rotation'
        orig = hb.get(chn)
        val = (lambda t: C.chan_at(orig, t)) if orig is not None else (lambda t: [0.0, 0.0, 0.0])
        idx = [i for i in range(len(ts)) if np.abs(sm[i]).max() > 1e-3]
        lo_t, hi_t = ts[max(0, idx[0] - 1)], ts[min(len(ts) - 1, idx[-1] + 1)]
        keys = {}
        if isinstance(orig, dict) and 'vector' not in orig:
            for kk, e in orig.items():
                t = round(float(kk), 4)
                if not (lo_t - 0.002 < t < hi_t + 0.002):     # ключи ±0.002 с от новых — заменяются (иначе «2.292» и 2.2917 —
                    keys[t] = e if isinstance(e, dict) else {'vector': e}   # два ключа на одном кадре, и последний прыгает назад)
        for i, t in enumerate(ts):
            if lo_t <= t <= hi_t:
                v = val(t)
                keys[round(t, 4)] = {'vector': [round(v[j] + sm[i][j], 3) for j in range(3)]}
        hb[chn] = {('%.6g' % t if t else '0.0'): keys[t] for t in sorted(keys)}
        rep[name] = round(float(np.linalg.norm(sm, axis=1).max()), 1)
    return rep


STRIKE_EV = ('slash', 'impale', 'throw', 'shatter', 'dash', 'erupt', 'stab', 'hit')
SNAP = ('easeOutQuart', 'easeOutCubic')


def strike_ease(anims, names):
    """Удар без толчка (проверка рывков 21.11): сегмент В момент удара (ключ на событии timeline) с easeOut* — коса стартует с
    максимальной скорости из покоя замаха, это рывок — заменяется на easeInCubic: разгон, пик скорости ровно на ударе (как у ударов
    Тироса). Сегмент ПОСЛЕ удара с easeInOut* (старт с нуля после пика) → easeOutQuad: гашение с той же скорости. Остальные сегменты
    easeOut*, что стартуют из покоя (предыдущий сегмент кончается без скорости), → easeInOutSine. Возвращает число правок."""
    zero_end = (None, 'linear', 'easeInOutSine', 'easeInOutQuad', 'easeInOutCubic', 'easeOutQuart', 'easeOutCubic', 'easeOutQuad')
    cnt = 0
    for n in names:
        an = anims.get(n)
        if not an:
            continue
        ev = [float(t) for t, e in an.get('timeline', {}).items() if e in STRIKE_EV]
        for bone, chs in an['bones'].items():
            for kind, ch in chs.items():
                if not isinstance(ch, dict) or 'vector' in ch:
                    continue
                ks = sorted(ch, key=float)
                for i in range(1, len(ks)):
                    t = float(ks[i])
                    e = ch[ks[i]]
                    if not isinstance(e, dict):
                        continue
                    ez = e.get('easing')
                    at_strike = any(abs(t - x) < 0.03 for x in ev)
                    after_strike = any(abs(float(ks[i - 1]) - x) < 0.03 for x in ev)
                    prev = ch[ks[i - 1]] if isinstance(ch[ks[i - 1]], dict) else {}
                    same = prev.get('vector') == e.get('vector')
                    if at_strike and ez in SNAP:
                        e['easing'] = 'easeInCubic'
                        cnt += 1
                    elif after_strike and ez in ('easeInOutQuad', 'easeInOutSine'):
                        e['easing'] = 'easeOutQuad'
                        cnt += 1
                    elif ez in SNAP and not at_strike and not after_strike and i >= 2:
                        pe = prev.get('easing')
                        if pe in zero_end and not same:
                            e['easing'] = 'easeInOutSine'
                            cnt += 1
    return cnt


def unwrap(anims, names, bones=('right_arm', 'bipedHandRight')):
    """Эйлеровы углы соседних ключей — без перескока через ±180° (GeckoLib интерполирует углы линейно)."""
    for n in names:
        an = anims.get(n)
        if not an:
            continue
        for b in bones:
            ch = an['bones'].get(b, {}).get('rotation')
            if not isinstance(ch, dict) or 'vector' in ch:
                continue
            prev = None
            for k in sorted(ch, key=float):
                e = ch[k]
                if not isinstance(e, dict) or 'vector' not in e:
                    continue
                v = e['vector']
                if prev is not None:
                    v = [x + 360 * round((p - x) / 360) for x, p in zip(v, prev)]
                    e['vector'] = [round(x, 3) for x in v]
                prev = e['vector']


# ------------------------------------------------------------------ кисть с предметом: видимый поворот → ключ (GeckoLib поворачивает дважды)
def _euler_m(h):
    D = math.pi / 180
    return (C.Rz(h[2] * D) @ C.Ry(-h[1] * D) @ C.Rx(-h[0] * D))[:3, :3]


def _m_euler(R):
    b = math.asin(max(-1.0, min(1.0, -R[2, 0])))
    a = math.atan2(R[2, 1], R[2, 2])
    c = math.atan2(R[1, 0], R[0, 0])
    return [round(-math.degrees(a), 2), round(-math.degrees(b), 2), round(math.degrees(c), 2)]


def V(h):
    """Ключ bipedHandRight по ВИДИМОМУ повороту предмета в кисти. GeckoLib 4.8.4 (BlockAndItemGeoLayer.renderForBone) поворачивает
    предмет поворотом кости кисти дважды (matrix кости уже повёрнута, затем translateAndRotateMatrixForBone ещё раз), поэтому в ключ
    пишется половина поворота: R(ключ)·R(ключ) = R(h). Оси — как у ключей анимаций (x, y — с обратным знаком к осям модели)."""
    R = _euler_m(h)
    w = math.sqrt(max(0.0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2           # кватернион → половина угла
    if w < 1e-6:
        raise ValueError('поворот на 180°: половина неоднозначна')
    x, y, z = (R[2, 1] - R[1, 2]) / (4 * w), (R[0, 2] - R[2, 0]) / (4 * w), (R[1, 0] - R[0, 1]) / (4 * w)
    ang = 2 * math.acos(max(-1.0, min(1.0, w)))
    n = math.sqrt(x * x + y * y + z * z) or 1.0
    ha = ang / 2
    q = [math.cos(ha / 2)] + [v / n * math.sin(ha / 2) for v in (x, y, z)]
    qw, qx, qy, qz = q
    Rh = np.array([[1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
                   [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
                   [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)]])
    return _m_euler(Rh)


def visible_hand(anims, names):
    """Ключи поворота bipedHandRight, подобранные по превью с ОДНИМ поворотом предмета (до 21.11), переводятся в ключи для игры:
    каждый ключ k → V(k), тогда в игре (двойной поворот GeckoLib) предмет повёрнут ровно как на превью. Вызывать ОДИН раз на свежесобранных
    анимациях (повторный вызов снова уполовинит поворот)."""
    def conv(v, prev=None):
        try:
            return V_near(v, prev)                          # 21.11: ближайший к соседнему ключу набор углов (без «длинного пути»)
        except ValueError:                                   # ровно 180°: половина неоднозначна — берём покомпонентно
            return [round(x / 2, 2) for x in v]
    n = 0
    for name in names:
        ch = anims.get(name, {}).get('bones', {}).get('bipedHandRight', {}).get('rotation')
        if not isinstance(ch, dict):
            if isinstance(ch, list):
                anims[name]['bones']['bipedHandRight']['rotation'] = conv(ch)
                n += 1
            continue
        prev = None
        for t in sorted(ch, key=float):
            k = ch[t]
            if isinstance(k, list):
                ch[t] = conv(k, prev)
                prev = ch[t]
            elif isinstance(k, dict):
                for f in ('pre', 'vector', 'post'):
                    if isinstance(k.get(f), list):
                        k[f] = conv(k[f], prev)
                        prev = k[f]
            n += 1
    return n


# ------------------------------------------------------------------ поза хвата как у Тироса (isAnimatingDampener FireBossModel)
def _uses_arm(an):
    """Анимация работает правой рукой (коса в деле): у кисти есть ненулевые ключи поворота или рука уходит дальше 45°."""
    bk = an['bones']
    for b, lim in (('bipedHandRight', 1.0), ('right_arm', 45.0)):
        ch = bk.get(b, {}).get('rotation')
        if ch is not None and any(max(abs(x) for x in v) > lim for _, v, _ in C._keys(ch)):
            return True
    return False


def _smooth(x):
    """Плавный переход 0 → 1 (квинтика: нулевые скорость и ускорение на концах — без толчка на стыке)."""
    x = max(0.0, min(1.0, x))
    return x * x * x * (x * (6 * x - 15) + 10)


def hold_additive(anims, names, arm, hand, hand_pos=None, win=0.3, step=0.05, no_end=(), still=(), no_start=(), win_end=0.45):
    """Поза хвата Тироса в ключах анимаций (Iron's: FireBossModel прибавляет позу хвата к анимации с множителем isAnimatingDampener,
    он гаснет за ~0.3 с). Два случая:
      * правая рука с косой в анимации не работает (касты, кинжалы левой рукой) — поза хвата прибавляется на всю длину: рука держит
        косу как вне анимаций (у Тироса в них лезвие лежит в земле: множитель гаснет, кисть уходит в позу покоя);
      * рука работает (удары, замахи) — вход: из позы хвата прямо в первый ключ анимации (у Iron's рука начинает с позы покоя,
        а в позе покоя лезвие в земле), выход: из последнего ключа прямо в позу хвата; если анимация начинается не с покоя —
        поза хвата прибавляется и гаснет за win с, как у Тироса.
    Код вне анимаций держит ту же позу (CultLeaderModel), поэтому на входе и выходе нет рывка. Возвращает {анимация: 'edges'|'always'}."""
    rep = {}
    for n in names:
        an = anims.get(n)
        if not an or not an.get('animation_length'):
            continue
        L = float(an['animation_length'])
        if n in still:                                   # короткий каст: правая рука держит косу, кастует левая (без рывка руки)
            an['bones']['right_arm'] = dict(an['bones'].get('right_arm', {}), rotation={'0.0': {'vector': list(arm)}})
            hb = dict(an['bones'].get('bipedHandRight', {}), rotation={'0.0': {'vector': list(hand)}})
            if hand_pos is not None:
                hb['position'] = {'0.0': {'vector': list(hand_pos)}}
            an['bones']['bipedHandRight'] = hb
            rep[n] = 'still'
            continue
        always = not _uses_arm(an)
        akeys = C._keys(an['bones']['right_arm']['rotation']) if 'rotation' in an['bones'].get('right_arm', {}) else []
        # опорные времена — по ключам руки: первый ключ после начала, последний перед концом
        t1 = next((t for t, _, _ in akeys if t > 1e-6), None)
        tn = next((t for t, _, _ in reversed(akeys) if t < L - 1e-6), None)
        chans = [('right_arm', 'rotation', arm), ('bipedHandRight', 'rotation', hand)]
        if hand_pos is not None:
            chans.append(('bipedHandRight', 'position', hand_pos))
        for b, kind, v in chans:
            bk = an['bones'].setdefault(b, {})
            orig = bk.get(kind)
            val = (lambda t, o=orig: C.chan_at(o, t)) if orig is not None else (lambda t: [0.0, 0.0, 0.0])
            keys = {}
            if isinstance(orig, dict) and 'vector' not in orig:
                for kk, e in orig.items():
                    e = dict(e) if isinstance(e, dict) else {'vector': e}
                    vec = e.get('vector') or e.get('post') or e.get('pre')
                    e = {x: y for x, y in e.items() if x not in ('pre', 'post')}
                    e['vector'] = list(vec)
                    keys[round(float(kk), 4)] = e
            elif orig is not None:
                keys[0.0] = {'vector': list(val(0))}
            if always:
                for t in list(keys):
                    keys[t]['vector'] = [round(keys[t]['vector'][i] + v[i], 3) for i in range(3)]
                if not keys:
                    keys[0.0] = {'vector': list(v)}
                bk[kind] = {('%.6g' % t if t else '0.0'): keys[t] for t in sorted(keys)}
                continue
            rest0 = max(abs(x) for x in val(0)) < 1e-3 and (not akeys or max(abs(x) for x in akeys[0][1]) < 1e-3)
            restL = max(abs(x) for x in val(L)) < 1e-3 and (not akeys or max(abs(x) for x in akeys[-1][1]) < 1e-3)
            segs = []                                   # (t_from, t_to, вход?)
            if n in no_start:                           # цепочка: начало — конец предыдущей анимации (не поза хвата)
                pass
            elif rest0 and t1 and t1 >= 0.2:
                segs.append((0.0, t1, True))
            else:
                segs.append((0.0, min(win, 0.4 * L), None))
            if n in no_end:                             # смерть: тело лежит, поза хвата в конце не нужна
                pass
            elif restL and tn is not None and tn > (t1 or 0) and L - tn >= 0.3:
                segs.append((tn, L, False))
            else:
                segs.append((L - min(win_end, 0.45 * L), L, None))
            for a0, a1, enter in segs:
                for t in list(keys):
                    if a0 < t < a1:
                        del keys[t]
                m = max(2, int(round((a1 - a0) / step)))
                for i in range(m + 1):
                    t = round(a0 + (a1 - a0) * i / m, 4)
                    x = (t - a0) / (a1 - a0) if a1 > a0 else 1.0
                    if enter is True:              # поза хвата → первый ключ анимации
                        tgt = val(a1)
                        vec = [v[j] + (tgt[j] - v[j]) * _smooth(x) for j in range(3)]
                    elif enter is False:           # последний ключ → поза хвата
                        src = val(a0)
                        vec = [src[j] + (v[j] - src[j]) * _smooth(x) for j in range(3)]
                    else:                          # анимация не с покоя: из позы хвата в её позу / из её позы в позу хвата
                        kk = 1 - _smooth(x) if a0 == 0.0 else _smooth(x)
                        o = val(t)
                        vec = [o[j] + kk * (v[j] - o[j]) for j in range(3)]
                    e = dict(keys.get(t, {}))
                    if t > a0:                   # ключ в начале участка описывает сегмент ДО него (у Iron's бывает step: 411° → 51°) —
                        e.pop('easing', None)   # его easing не трогаем, иначе рука прокрутится на 360° за пару кадров
                        e.pop('easingArgs', None)
                    e['vector'] = [round(y, 3) for y in vec]
                    keys[t] = e
            if not keys:                               # ни входа, ни выхода (цепочка) и канала не было — не создаём пустой
                if orig is None:
                    bk.pop(kind, None)
                continue
            bk[kind] = {('%.6g' % t if t else '0.0'): keys[t] for t in sorted(keys)}
        rep[n] = 'always' if always else 'edges'
    return rep


def V_near(h, prev=None):
    """V(h), но из эквивалентных наборов эйлеровых углов (x, y, z) / (x − 180, −180 − y, z + 180), с поправками ±360°, — ближайший
    к ключу prev: GeckoLib интерполирует углы линейно, без этого соседние ключи могут пойти «длинным путём» (переворот косы)."""
    v = V(h)
    if prev is None:
        return v
    alts = [v, [v[0] - 180, -180 - v[1], v[2] + 180]]
    best = None
    for a in alts:
        a = [x + 360 * round((p - x) / 360) for x, p in zip(a, prev)]
        d = max(abs(x - p) for x, p in zip(a, prev))
        if best is None or d < best[0]:
            best = (d, [round(x, 2) for x in a])
    return best[1]


# ------------------------------------------------------------------ поза хвата на краях анимаций (Глава Культа)
def hold_edges(anims, names, arm, hand, win=0.3, step=0.05, hand_pos=None):
    """Каждая анимация из names начинается и заканчивается в позе хвата (right_arm = arm, bipedHandRight = hand) — той же, что код
    держит вне анимаций. Вход и выход — плавное смешение за win с (не длиннее 0.4 длины анимации); середина анимации не меняется.
    Без этого правая рука в начале и конце уходит в позу покоя модели, а при опущенной руке коса лежит лезвием в земле."""
    for n in names:
        an = anims.get(n)
        if not an or not an.get('animation_length'):
            continue
        L = float(an['animation_length'])
        w = min(win, 0.4 * L)
        if w < step:
            for b, v in (('right_arm', arm), ('bipedHandRight', hand)):
                an['bones'].setdefault(b, {})['rotation'] = {'0.0': {'vector': list(v)}}
            if hand_pos is not None:
                an['bones']['bipedHandRight']['position'] = {'0.0': {'vector': list(hand_pos)}}
            continue
        chans = [('right_arm', 'rotation', arm), ('bipedHandRight', 'rotation', hand)]
        if hand_pos is not None:
            chans.append(('bipedHandRight', 'position', hand_pos))
        for b, kind, v in chans:
            bk = an['bones'].setdefault(b, {})
            orig = bk.get(kind)
            val = (lambda t: C.chan_at(orig, t)) if orig is not None else (lambda t: [0.0, 0.0, 0.0])
            keys = {}
            if isinstance(orig, dict) and 'vector' not in orig:      # ключи середины — как были
                for k, e in orig.items():
                    if w < float(k) < L - w:
                        keys[round(float(k), 4)] = e if isinstance(e, dict) else {'vector': e}
            ts = [i * step for i in range(int(round(w / step)) + 1)]
            for t in ts + [L - x for x in ts]:
                t = round(max(0.0, min(L, t)), 4)
                d = min(t, L - t)
                k = 1 - max(0.0, min(1.0, d / w))
                k = k * k * (3 - 2 * k)                           # гладкий вход/выход
                o = val(t)
                keys[t] = {'vector': [round(o[i] + (v[i] - o[i]) * k, 2) for i in range(3)]}
            if orig is None:
                keys.setdefault(round(w, 4), {'vector': [0, 0, 0]})
                keys.setdefault(round(L - w, 4), {'vector': [0, 0, 0]})
            bk[kind] = {('%.4g' % t if t else '0.0'): keys[t] for t in sorted(keys)}
