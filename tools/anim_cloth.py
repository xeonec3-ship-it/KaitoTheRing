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


def weapon(boss, anims, names, edge=0.25):
    """Кисть с оружием в анимациях Iron's, где правая рука ими не занята под наш предмет: в кадрах, где коса/рапира уходит в землю
    или сквозь тело/ноги, к кости bipedHandRight добавляется наименьший поворот (сетка 15°, ближе к соседнему кадру), с плавным
    входом/выходом 0.15 с. Края анимаций (первые/последние 0.25 с) не трогаем: там действует поза хвата из кода (FireBossModel)."""
    M = C.Model(boss)
    rep = {}
    for name in names:
        an = anims.get(name)
        if not an or not an.get('animation_length'):
            continue
        L = float(an['animation_length'])
        n = max(1, int(round(L / STEP)))
        ts = [min(L, i * STEP) for i in range(n + 1)]
        base = [_channel_val(an, 'bipedHandRight', t) for t in ts]
        off = []
        prev = (0, 0, 0)
        for t, b in zip(ts, base):
            edge_t = t < edge or t > L - edge
            if _weapon_bad(M, M.world(an, t), edge_t) == 0:
                off.append((0, 0, 0))
                prev = (0, 0, 0)
                continue
            best = None
            for g in GRID:
                o = [b[0] + g[0], b[1] + g[1], b[2] + g[2]]
                if _weapon_bad(M, M.world(an, t, {'bipedHandRight': o}), edge_t) == 0:
                    cost = math.dist(g, prev) + 0.3 * math.dist(g, (0, 0, 0))
                    if best is None or cost < best[0]:
                        best = (cost, g)
            g = best[1] if best else prev
            off.append(g)
            prev = g
        if not any(any(o) for o in off):
            continue
        # сгладить: удержание ±0.1 с вокруг ненулевых кадров, затем ключи через 0.05 с с линейным переходом 0.15 с
        w = int(round(0.1 / STEP))
        held = list(off)
        for i, o in enumerate(off):
            if any(o):
                for j in range(max(0, i - w), min(len(off), i + w + 1)):
                    if not any(held[j]):
                        held[j] = o
        r = int(round(0.15 / STEP))
        sm = []
        for i in range(len(held)):
            if any(held[i]):
                sm.append(held[i])
                continue
            # расстояние до ближайшего ненулевого → линейно к нулю
            near = None
            for d in range(1, r + 1):
                for j in (i - d, i + d):
                    if 0 <= j < len(held) and any(held[j]):
                        near = (d, held[j])
                        break
                if near:
                    break
            sm.append(tuple(v * (1 - near[0] / (r + 1)) for v in near[1]) if near else (0, 0, 0))
        ch = {}
        for i, t in enumerate(ts):
            v = [round(base[i][k] + sm[i][k], 2) for k in range(3)]
            ch['%.4g' % t if t else '0.0'] = {'vector': v}
        an['bones'].setdefault('bipedHandRight', {})['rotation'] = ch
        rep[name] = sum(1 for o in off if any(o))
    return rep
