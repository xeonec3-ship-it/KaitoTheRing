#!/usr/bin/env python3
"""
Проверка рывков косы Главы Культа (T26): 60 кадров/с, кинематика как в игре (anim_check.Model — второй поворот кисти GeckoLib).
По каждой анимации — поворот косы в мире R(t) и точки острия/подтока. Метрики кадр к кадру:
  * dω — скачок угловой скорости косы (вектор ω = ось·угол между соседними кадрами ×60), °/с за кадр;
  * da — скачок ускорения острия и подтока (вторая разность скорости), px/с² за кадр (норма третьей разности ×60³ / 1000).
Порог — «не больше, чем у Тироса Iron's»: у анимаций Iron's — та же анимация из jar так, как её играет Тирос в игре (его хват,
isAnimatingDampener на входе, сброс поз на выходе, tyros_seq), у наших — самые резкие удары косой Тироса внутри анимаций;
×1.1 + 30 °/с / +5 запаса на дискретизацию.
Переходы: покой → анимация → (0.25 с, как CultLeaderModel) → покой; ходьба → удар косой.
  python3 tools/scythe_jitter.py [файл анимаций] [--json out.json] [--anim a,b]
  python3 tools/scythe_jitter.py --boss ereb      (оружие Эреба: рывки внутри его анимаций)
"""
import json
import math
import os
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import anim_check as C  # noqa: E402

FPS = 60
TIP = np.array([3.55, 11.34, 8.0])
BUTT = np.array([0.5, 0.5, 8.0])


def _rotvec(R):
    c = max(-1.0, min(1.0, (np.trace(R) - 1) / 2))
    a = math.acos(c)
    if a < 1e-9:
        return np.zeros(3)
    v = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    n = np.linalg.norm(v)
    if n < 1e-9:                       # около 180°
        w, V = np.linalg.eigh((R + np.eye(3)) / 2)
        return V[:, -1] * a
    return v / n * a


def _ends(M):
    if M.name == 'cult_leader':
        return TIP, BUTT
    tip = M.item_pts[M.tip_i]
    return tip, M.item_pts[int(np.argmax(np.linalg.norm(M.item_pts - tip, axis=1)))]


def sample(M, an, ts):
    Rs, P = [], []
    tip, butt = _ends(M)
    for t in ts:
        W = M.world(an, t)
        m = W['bipedHandRight'] @ W[C.HAND2] @ M.item_m
        R = m[:3, :3] / np.cbrt(abs(np.linalg.det(m[:3, :3])))
        Rs.append(R)
        P.append([C.ap(m, tip), C.ap(m, butt)])
    return Rs, np.array(P)


def run_other(boss):
    """Эреб (и другие из anim_check.CFG): рывки оружия внутри его анимаций; порог — у анимаций Iron's та же анимация из jar на его
    модели, у своих — самые резкие удары косой Тироса (эталон «как у Тироса»). Переходы — у этих боссов вне анимаций кода нет."""
    M = C.Model(boss)
    anims = C.load_anims(boss)
    with zipfile.ZipFile(C.JAR) as z:
        iron = json.loads(z.read('assets/irons_spellbooks/animations/casting_animations.json'))['animations']
    Mc = C.Model('cult_leader')
    raw = [anim_jerk(Mc, iron[n])[:2] for n in C.PLAYS['cult_leader'] if n.startswith('scythe_') and n in iron]
    star = (max(v[0] for v in raw), max(v[1] for v in raw))
    rows, bad = [], 0
    for n, an in anims.items():
        if n in iron and n not in C.PLAYS[boss]:
            continue
        if not an.get('animation_length') or n in C.WEAPON_HIDDEN.get(boss, ()):   # оружие убрано в кулак (SheathPoses)
            continue
        a, b, t = anim_jerk(M, an)
        lim = anim_jerk(M, iron[n])[:2] if n in iron else star
        la, lb = lim[0] * 1.1 + 30, lim[1] * 1.1 + 5
        # масштаб (появление/исчезновение) — da не считается; только масштаб костей, на которых висит оружие (у Длани ghost_* масштабируются
        # почти всегда — раньше это выключало da у всех её анимаций)
        chain, k = set(), 'bipedHandRight'
        while k:
            chain.add(k)
            k = M.bones[k]['parent']
        def varies(sc):
            vs = [v.get('vector', v.get('post', v.get('pre'))) if isinstance(v, dict) else v for v in (sc.values() if isinstance(sc, dict) else [sc])]
            vs = [[x] * 3 if not isinstance(x, list) else x for x in vs]
            return any(abs(float(c) - 1.0) > 1e-3 for v in vs for c in v if not isinstance(c, str))
        if any('scale' in ch and varies(ch['scale']) for bn, ch in an['bones'].items() if bn in chain):
            b = 0.0
        ok = a <= la and b <= lb
        bad += not ok
        rows.append((n, a, la, b, lb, t, ok))
    return rows, bad


def jerk(Rs, P):
    """Скачки: dω (°/с за кадр) и da (тыс. px/с³ ~ скачок ускорения) — массивы по кадрам."""
    w = np.array([_rotvec(Rs[i].T @ Rs[i + 1]) * FPS for i in range(len(Rs) - 1)])       # рад/с, в осях косы
    # ω в мировых осях (чтобы сравнивать соседние кадры в одной системе)
    ww = np.array([Rs[i] @ w[i] for i in range(len(w))])
    dw = np.degrees(np.linalg.norm(np.diff(ww, axis=0), axis=1)) if len(ww) > 1 else np.zeros(0)
    v = np.diff(P, axis=0) * FPS
    a = np.diff(v, axis=0) * FPS
    j = np.linalg.norm(np.diff(a, axis=0), axis=2).max(axis=1) * FPS / 1000 if len(a) > 1 else np.zeros(0)
    return dw, j


def blend_out(an, hold, n=15):
    """Как CultLeaderModel после конца/обрыва анимации: рука и кисть из последней позы в позу хвата за 0.25 с (квинтика), прочие
    кости — в покой (у контроллеров Iron's нет перехода)."""
    L = float(an['animation_length'])
    b = {}
    for bone in ('right_arm', 'bipedHandRight'):
        for kind in ('rotation', 'position'):
            src = an['bones'].get(bone, {}).get(kind)
            v0 = C.chan_at(src, L) if src is not None else [0.0, 0.0, 0.0]
            v1 = C.chan_at(hold['bones'].get(bone, {}).get(kind, {'0.0': {'vector': [0, 0, 0]}}), 0)
            ch = {}
            for i in range(n + 1):
                x = i / n
                w = x * x * x * (x * (6 * x - 15) + 10)
                ch['%.4g' % (i / FPS) if i else '0.0'] = {'vector': [a + (c - a) * w for a, c in zip(v0, v1)]}
            b.setdefault(bone, {})[kind] = ch
    return {'animation_length': n / FPS, 'bones': b}


def anim_jerk(M, an, pre=None, post=None, pre_t=None):
    L = float(an['animation_length'])
    ts = [i / FPS for i in range(int(L * FPS) + 1)]
    Rs, P = sample(M, an, ts)
    off = 0
    if pre is not None:                         # поза кода до анимации (покой или шаг) → анимация
        pts = pre_t or [0, 0, 0]
        R0, P0 = sample(M, pre, pts)
        Rs, P = R0 + Rs, np.vstack([P0, P])
        off = len(pts)
    if post is not None:                        # конец анимации → плавно в позу хвата (код) → поза хвата
        bo = blend_out(an, post)
        R1, P1 = sample(M, bo, [(i + 1) / FPS for i in range(15)])
        R2, P2 = sample(M, post, [0, 0, 0])
        Rs, P = Rs + R1 + R2, np.vstack([P, P1, P2])
    dw, j = jerk(Rs, P)
    tdw = (int(np.argmax(dw)) + 1 - off) / FPS if len(dw) else 0
    return float(dw.max() if len(dw) else 0), float(j.max() if len(j) else 0), tdw


def hold_anim(arm, hand, pos=None):
    b = {'right_arm': {'rotation': {'0.0': {'vector': arm}}}, 'bipedHandRight': {'rotation': {'0.0': {'vector': hand}}}}
    if pos:
        b['bipedHandRight']['position'] = {'0.0': {'vector': pos}}
    return {'animation_length': 0, 'bones': b}


TYROS_ARM, TYROS_HAND = [30, 30, 10], [5, 0, -48]      # FireBossModel в осях анимаций


def snapshot(an, t, over=None):
    """Поза анимации в момент t как анимация из одного кадра; over — {(кость, канал): вектор} вместо её значений."""
    b = {}
    for bone, ch in (an['bones'] if an else {}).items():
        for kind in ('rotation', 'position', 'scale'):
            if kind in ch:
                b.setdefault(bone, {})[kind] = {'0.0': {'vector': list(C.chan_at(ch[kind], t)) if not isinstance(C.chan_at(ch[kind], t), (int, float)) else [C.chan_at(ch[kind], t)] * 3}}
    for (bone, kind), v in (over or {}).items():
        b.setdefault(bone, {})[kind] = {'0.0': {'vector': list(v)}}
    return {'animation_length': 0, 'bones': b}


def tyros_seq(M, an):
    """Тирос в игре: поза хвата (10 кадров) → анимация + dampener·поза хвата (dampener гаснет: lerp(0.15·pt) ≈ −7.5% за кадр при
    60 к/с) → конец: кости сразу в покой, поза хвата возвращается (lerp(0.05·pt) ≈ +2.5% за кадр), 0.5 с."""
    L = float(an['animation_length'])
    arm = lambda t: C.chan_at(an['bones']['right_arm']['rotation'], t) if 'rotation' in an['bones'].get('right_arm', {}) else [0, 0, 0]
    hand = lambda t: (C.chan_at(an['bones']['bipedHandRight']['rotation'], t) if 'rotation' in an['bones'].get('bipedHandRight', {})
                      else [0, 0, 0])
    frames = [snapshot(None, 0, {('right_arm', 'rotation'): TYROS_ARM, ('bipedHandRight', 'rotation'): TYROS_HAND})] * 10
    d = 1.0
    for i in range(int(L * FPS) + 1):
        t = i / FPS
        d *= 0.925
        a, h = arm(t), hand(t)
        frames.append(snapshot(an, t, {('right_arm', 'rotation'): [a[k] + d * TYROS_ARM[k] for k in range(3)],
                                       ('bipedHandRight', 'rotation'): [h[k] + d * TYROS_HAND[k] for k in range(3)]}))
    for i in range(30):
        d += 0.025 * (1 - d)
        frames.append(snapshot(None, 0, {('right_arm', 'rotation'): [d * x for x in TYROS_ARM],
                                         ('bipedHandRight', 'rotation'): [d * x for x in TYROS_HAND]}))
    return frames


def seq_jerk(M, frames):
    Rs, P = [], []
    for f in frames:
        r, p = sample(M, f, [0])
        Rs += r
        P.append(p[0])
    dw, j = jerk(Rs, np.array(P))
    return float(dw.max()), float(j.max())


def iron_ref(M):
    with zipfile.ZipFile(C.JAR) as z:
        iron = json.loads(z.read('assets/irons_spellbooks/animations/casting_animations.json'))['animations']
    ref = {}
    for n in C.PLAYS['cult_leader']:
        if n in iron:
            ref[n] = seq_jerk(M, tyros_seq(M, iron[n]))
    # наши анимации (у Тироса таких нет): порог — самые резкие удары косой Тироса ВНУТРИ его анимаций (без переходов)
    raw = [anim_jerk(M, iron[n])[:2] for n in C.PLAYS['cult_leader'] if n.startswith('scythe_') and n in iron]
    ref['*'] = (max(v[0] for v in raw), max(v[1] for v in raw))
    return ref



def run(path=None, only=None):
    from gen_cult_leader_extra import CARRY_ARM, CARRY_HAND, CARRY_POS
    M = C.Model('cult_leader')
    anims = json.load(open(path or os.path.join(C.A, C.CFG['cult_leader']['anim']), encoding='utf-8'))['animations']
    ref = iron_ref(M)
    hold = hold_anim(CARRY_ARM, CARRY_HAND, CARRY_POS)
    names = [n for n in anims if n.startswith('cult_leader_')] + [n for n in C.PLAYS['cult_leader'] if n in anims]
    if only:
        names = [n for n in names if n in only]
    rows, bad = [], 0
    import boss_video
    walk = boss_video.cult_hold_anims()['~walk']
    # цепочка «Пепла Меллисто»: перед разрезом — конец сборки; рассыпание кончается скрытием модели, сборка — замахом разреза
    chain_pre = {'cult_leader_ash_slash': ('cult_leader_ash_reform', None), 'cult_leader_ash_reform': None}
    no_post = ('fire_boss_death', 'cult_leader_ash_dissolve', 'cult_leader_ash_reform')
    for n in names:
        pre, pre_t = hold, None
        if n in chain_pre:
            c = chain_pre[n]
            pre = anims[c[0]] if c else None
            pre_t = [float(anims[c[0]]['animation_length'])] * 3 if c else None
        a, b, t = anim_jerk(M, anims[n], pre=pre, post=None if n in no_post else hold, pre_t=pre_t)
        if n.startswith('scythe_'):                # ходьба → удар
            wl = float(walk['animation_length'])
            a2, b2, t2 = anim_jerk(M, anims[n], pre=walk, pre_t=[wl * 0.3 + i / FPS for i in range(10)])
            if a2 > a:
                a, t = a2, t2
            b = max(b, b2)
        if any('scale' in ch for ch in anims[n]['bones'].values()):     # модель сжимается (рассыпание в пепел): ускорение не считаем
            b = 0.0
        lim = ref.get(n, ref['*'])
        la, lb = lim[0] * 1.1 + 30, lim[1] * 1.1 + 5          # +30 °/с, +5: шум дискретизации на медленных анимациях
        ok = a <= la and b <= lb
        bad += not ok
        rows.append((n, a, la, b, lb, t, ok))
    return rows, bad


if __name__ == '__main__':
    args = sys.argv[1:]
    path = args[0] if args and not args[0].startswith('--') else None
    only = set(args[args.index('--anim') + 1].split(',')) if '--anim' in args else None
    rows, bad = run_other(args[args.index('--boss') + 1]) if '--boss' in args else run(path, only)
    for n, a, la, b, lb, t, ok in rows:
        print('%-40s dω %6.0f (порог %5.0f, макс. в %.2f с)  da %6.1f (порог %5.1f)  %s' % (n, a, la, t, b, lb, 'ok' if ok else 'РЫВОК'))
    print('рывков сверх порога:', bad)
    if '--json' in args:
        json.dump([dict(anim=r[0], dw=r[1], dw_lim=r[2], da=r[3], da_lim=r[4], t=r[5], ok=r[6]) for r in rows],
                  open(args[args.index('--json') + 1], 'w'), ensure_ascii=False, indent=1)
