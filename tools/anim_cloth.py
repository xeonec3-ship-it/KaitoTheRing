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
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def hold_additive(anims, names, arm, hand, hand_pos=None, win=0.3, step=0.05, no_end=()):
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
                bk[kind] = {('%.4g' % t if t else '0.0'): keys[t] for t in sorted(keys)}
                continue
            rest0 = max(abs(x) for x in val(0)) < 1e-3 and (not akeys or max(abs(x) for x in akeys[0][1]) < 1e-3)
            restL = max(abs(x) for x in val(L)) < 1e-3 and (not akeys or max(abs(x) for x in akeys[-1][1]) < 1e-3)
            segs = []                                   # (t_from, t_to, вход?)
            if rest0 and t1:
                segs.append((0.0, t1, True))
            else:
                segs.append((0.0, min(win, 0.4 * L), None))
            if n in no_end:                             # смерть: тело лежит, поза хвата в конце не нужна
                pass
            elif restL and tn is not None and tn > (t1 or 0):
                segs.append((tn, L, False))
            else:
                segs.append((L - min(win, 0.4 * L), L, None))
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
                    else:                          # анимация не с покоя: поза хвата прибавляется и гаснет (как у Тироса)
                        kk = 1 - _smooth(x) if a0 == 0.0 else _smooth(x)
                        o = val(t)
                        vec = [o[j] + kk * v[j] for j in range(3)]
                    e = dict(keys.get(t, {}))
                    e.pop('easing', None)
                    e['vector'] = [round(y, 3) for y in vec]
                    keys[t] = e
            bk[kind] = {('%.4g' % t if t else '0.0'): keys[t] for t in sorted(keys)}
        rep[n] = 'always' if always else 'edges'
    return rep


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
