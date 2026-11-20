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
        for i, (t, b) in enumerate(zip(ts, base)):
            edge_t = t < edge or t > L - edge or bool(ag and ag[0] <= t <= ag[1])
            # не быстрее исходного движения оружия (×2, но не меньше 25° за шаг) — иначе доворот виден как рывок
            lim = 25.0 if i == 0 else max(25.0, 2.0 * ang(orig_ax[i - 1], orig_ax[i]))

            def good(g):
                W = M.world(an, t, {'bipedHandRight': [b[0] + g[0], b[1] + g[1], b[2] + g[2]]}) if any(g) else M.world(an, t)
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
                W = M.world(an, t, {'bipedHandRight': [b[0] + g[0], b[1] + g[1], b[2] + g[2]]})
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
                if j in (lo, hi):
                    cands.append([off[j]])
                    continue
                cj = [g for g in GRID + GRID3
                      if not _weapon_bad(M, M.world(an, t, {'bipedHandRight': [b[0] + g[0], b[1] + g[1], b[2] + g[2]]}), e_t)]
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


# ------------------------------------------------------------------ поза хвата на краях анимаций (Глава Культа)
def hold_edges(anims, names, arm, hand, win=0.3, step=0.05):
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
            continue
        for b, v in (('right_arm', arm), ('bipedHandRight', hand)):
            bk = an['bones'].setdefault(b, {})
            orig = bk.get('rotation')
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
            bk['rotation'] = {('%.4g' % t if t else '0.0'): keys[t] for t in sorted(keys)}
