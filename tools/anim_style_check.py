#!/usr/bin/env python3
"""
Проверка стиля анимаций по эталону Epic Fight (владелец 21.11; правила — docs/specs/anim_style_epicfight.md).
Считает ОДНИ И ТЕ ЖЕ метрики для эталона (Epic Fight / Nightfall / Weapons of Miracles, читаются из jar вне репо — tools/ef_ref.py)
и для наших анимаций (готовый animation.json, как его читает GeckoLib), и показывает отставание от эталона.

  python3 tools/anim_style_check.py                         # наши (Мартин) против эталонных порогов (jar не нужны)
  python3 tools/anim_style_check.py --file old.json         # другой файл анимаций Мартина (например, из git: «до»)
  python3 tools/anim_style_check.py --measure-ref [--ref-dir DIR] [--json out.json]   # пересчитать эталон из jar
  python3 tools/anim_style_check.py --anim martin_swing -v  # одна анимация, подробно (фазы по времени)
  python3 tools/anim_style_check.py --boss aris             # другой босс (martin, aris, irina)

Метрики (длины — в долях длины ноги L: у EF 0.75 бл., у Мартина 12 ед. модели; углы — градусы; время — секунды):
  фазы: замах (0 → начало удара), удар (скорость острия ≥ 30% пика), удержание (после удара острие не ушло дальше 0.3 L),
        возврат (остальное); доли от длины анимации;
  speed  — пик скорости острия (L/с) и пик угловой скорости клинка (°/с), дуга удара (°);
  accel  — доля разгона в фазе удара (от начала удара до пика / длина удара): ≈0.5 — симметрично, больше — «копит и рвёт»;
  root   — смещение таза вперёд к удару (L) и просадка таза (L); перенос веса: таз относительно середины стоп (L);
  feet   — путь передней стопы за удар (L) — шаг в удар;
  twist  — размах поворота плеч и таза (°), скрутка плечи−таз в конце замаха и на ударе (°; знаки разные = контр-поворот),
           цепочка: пик скорости таза → пик скорости плеч → пик острия (мс);
  overlap— запаздывание головы за плечами (мс, по взаимной корреляции); у Мартина ещё низ плаща за тазом (мс);
  follow — перехлёст: дуга клинка после пика скорости до остановки / дуга до пика.
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
DT = 1.0 / 60
UP = np.array([0.0, 1.0, 0.0])


# ================================================================== общие метрики
def yaw_of(f):
    """Поворот направления f вокруг вертикали: 0 — вперёд (−z), + — влево (против часовой сверху)."""
    return math.degrees(math.atan2(-f[0], -f[2]))


def line_yaw(l, r):
    return yaw_of(np.cross(UP, np.asarray(r) - np.asarray(l)))


def unwrap_deg(a):
    return np.degrees(np.unwrap(np.radians(np.asarray(a, float))))


def contiguous(mask, i):
    a = b = i
    while a > 0 and mask[a - 1]:
        a -= 1
    while b < len(mask) - 1 and mask[b + 1]:
        b += 1
    return a, b


def xcorr_lag(lead, follow, dt, maxlag=0.4):
    """Запаздывание follow за lead (с) по максимуму взаимной корреляции производных."""
    x, y = np.gradient(lead), np.gradient(follow)
    if np.std(x) < 1e-9 or np.std(y) < 1e-9:
        return None
    x, y = (x - x.mean()) / x.std(), (y - y.mean()) / y.std()
    best, lag = -9, 0
    for k in range(0, int(maxlag / dt) + 1):
        c = float(np.mean(x[:len(x) - k] * y[k:])) if k else float(np.mean(x * y))
        if c > best:
            best, lag = c, k
    return lag * dt


def metrics(sig, length, window=None, dt=DT, code_move=None):
    """sig(t) -> dict сигналов (см. ef_ref.ef_signals); window — (t0, t1), где искать пик удара (окно trail EF / тик hit ± у нас)."""
    ts = np.arange(0.0, length + 1e-9, dt)
    S = [sig(float(t)) for t in ts]
    if code_move:                            # перемещение сущности кодом (рывок): (t0, t1, длина в L) — вперёд (−z) всем точкам
        t0, t1, dist = code_move
        for t, s_ in zip(ts, S):
            dz = -dist * min(1.0, max(0.0, (t - t0) / (t1 - t0)))
            for k, v in s_.items():
                if k in ('pelvis', 'chest', 'head', 'sh_r', 'sh_l', 'hip_r', 'hip_l', 'foot_r', 'foot_l', 'tool', 'tip', 'cape'):
                    s_[k] = np.asarray(v, float) + [0, 0, dz]
    g = lambda k: np.array([s[k] for s in S], float)
    tip, hand = g('tip'), g('tool')
    v = np.linalg.norm(np.gradient(tip, dt, axis=0), axis=1)
    bd = tip - hand
    bd /= np.linalg.norm(bd, axis=1)[:, None]
    ang = np.degrees(np.arccos(np.clip(np.sum(bd[1:] * bd[:-1], axis=1), -1, 1)))
    k3 = int(round(0.05 / dt))                     # угловая скорость — по окну 50 мс (у EF ключи редкие, между ними линейно)
    wa = np.degrees(np.arccos(np.clip(np.sum(bd[k3:] * bd[:-k3], axis=1), -1, 1))) / (k3 * dt)
    w = np.concatenate([np.zeros(k3 // 2), wa, np.zeros(k3 - k3 // 2)])
    if window:
        sel = (ts >= window[0]) & (ts <= window[1])
    else:
        sel = np.ones_like(ts, bool)
    ip = int(np.argmax(np.where(sel, v, -1)))
    vp = float(v[ip])
    a, b = contiguous(v >= 0.3 * vp, ip)
    t_s, t_e = float(ts[a]), float(ts[b])
    c = b                                    # удержание: острие после удара не ушло дальше 0.3 L от точки конца удара
    while c < len(ts) - 1 and np.linalg.norm(tip[c + 1] - tip[b]) < 0.3:
        c += 1
    hold = float(ts[c] - ts[b]) if c > b else 0.0
    # «пауза в замахе»: перед началом удара острие почти стоит
    d = a
    while d > 0 and v[d - 1] < 0.15 * vp:
        d -= 1
    cock = float(ts[a] - ts[d]) if d < a else 0.0
    arc = float(np.sum(ang[a:b]))
    # перехлёст: дуга от пика до остановки (< 15% пика) / дуга от начала удара до пика
    e = ip
    while e < len(ts) - 1 and v[e] >= 0.15 * vp:
        e += 1
    pre, post = float(np.sum(ang[a:ip])), float(np.sum(ang[ip:e]))
    pel = g('pelvis')
    fl, fr = g('foot_l'), g('foot_r')
    mid = (fl + fr) / 2
    rel = pel - mid
    shy = unwrap_deg([line_yaw(s['sh_l'], s['sh_r']) for s in S])
    hpy = unwrap_deg([s['hip_yaw'] for s in S]) if 'hip_yaw' in S[0] else unwrap_deg([line_yaw(s['hip_l'], s['hip_r']) for s in S])
    hdy = unwrap_deg([yaw_of(s['head_fwd']) for s in S])
    tw = shy - hpy
    shv, hpv = np.abs(np.gradient(shy, dt)), np.abs(np.gradient(hpy, dt))
    lo, hi = max(0, a - int(0.35 / dt)), min(len(ts) - 1, b + int(0.1 / dt))
    t_hp = float(ts[lo + int(np.argmax(hpv[lo:hi + 1]))])
    t_sh = float(ts[lo + int(np.argmax(shv[lo:hi + 1]))])
    fstep = max(float(np.max(np.linalg.norm((f - f[max(0, a - int(0.25 / dt))])[:, [0, 2]], axis=1)[a:b + 1])) for f in (fl, fr))
    out = {
        'length': length, 't_peak': float(ts[ip]), 't_strike': [t_s, t_e],
        'windup': t_s, 'strike': t_e - t_s, 'hold': hold, 'recover': max(0.0, length - t_e - hold), 'cock': cock,
        'f_windup': t_s / length, 'f_strike': (t_e - t_s) / length, 'f_hold': hold / length, 'f_recover': max(0.0, length - t_e - hold) / length,
        'tip_peak': vp, 'ang_peak': float(np.max(w[a:b + 1])), 'arc': arc, 'accel': (ts[ip] - t_s) / max(dt, t_e - t_s),
        'follow': post / max(1.0, pre),
        'root_fwd': float(-(pel[ip, 2] - pel[0, 2])), 'root_fwd_max': float(np.max(-(pel[:, 2] - pel[0, 2]))),
        'decel': float(ts[e] - ts[ip]),
        'root_drop': float(pel[0, 1] - np.min(pel[a:b + 1 + int(0.2 / dt), 1])),
        'weight_shift': float(-(rel[ip, 2] - rel[a, 2])),
        'step': fstep,
        'sh_range': float(np.ptp(shy)), 'hip_range': float(np.ptp(hpy)),
        'twist_windup': float(tw[a] - tw[0]), 'twist_hit': float(tw[ip] - tw[0]), 'twist_range': float(np.ptp(tw)),
        'chain_hip_sh': (t_sh - t_hp) * 1000, 'chain_sh_tip': (float(ts[ip]) - t_sh) * 1000,
        'head_lag': None, 'cape_lag': None,
    }
    lag = xcorr_lag(shy[lo:], hdy[lo:], dt)
    out['head_lag'] = None if lag is None else lag * 1000
    if 'cape' in S[0]:
        cz = g('cape')[:, 2] - pel[:, 2]
        lag = xcorr_lag(-pel[:, 2], -cz, dt)
        out['cape_lag'] = None if lag is None else lag * 1000
    return out


def idle_metrics(sig, length, dt=DT):
    ts = np.arange(0.0, length + 1e-9, dt)
    S = [sig(float(t)) for t in ts]
    g = lambda k: np.array([s[k] for s in S], float)
    ch, pel = g('chest'), g('pelvis')
    fl, fr = g('foot_l'), g('foot_r')
    cy = ch[:, 1] - ch[:, 1].mean()
    f = np.abs(np.fft.rfft(cy))
    fr_ = np.fft.rfftfreq(len(cy), dt)
    k = int(np.argmax(f[1:])) + 1 if len(f) > 1 else 0
    period = 1.0 / fr_[k] if k and fr_[k] > 0 else None
    pitch = unwrap_deg([math.degrees(math.atan2(s['chest_fwd'][1], math.hypot(s['chest_fwd'][0], s['chest_fwd'][2]))) for s in S])
    sw = (fr - fl)[0]
    return {
        'length': length, 'breath_period': period, 'breath_amp': float(np.ptp(ch[:, 1])), 'breath_pitch': float(np.ptp(pitch)),
        'pelvis_h': float(np.mean(pel[:, 1])), 'stance_w': float(abs(sw[0])), 'stance_split': float(abs(sw[2])),
        'stance_yaw': float(np.mean([line_yaw(s['sh_l'], s['sh_r']) for s in S])),
        'sway': float(np.ptp(pel[:, 0]) + np.ptp(pel[:, 2])),
    }


# ================================================================== эталон: числа (пересчитываются --measure-ref → tools/anim_style_ref.json)
# Классы: heavy — тяжёлое двуручное (EF greatsword, Nightfall ng_greatsword/broadblade, WoM ruine/torment/napoleon) — эталон для Мартина;
# light — длинный/одноручный меч (EF longsword/mob_longsword, Nightfall nf_sword); thrust — уколы (EF spear/liechtenauer, WoM moonless).
REF = {}
REF_IDLE = {}
REF_FILE = os.path.join(HERE, 'anim_style_ref.json')
if os.path.exists(REF_FILE):
    _r = json.load(open(REF_FILE, encoding='utf-8'))
    REF, REF_IDLE = _r.get('attack', {}), _r.get('idle', {})

# какие метрики проверяем и как: (ключ, подпись, режим: 'band' — в коридоре p25..p75 (допуск 15%), 'min' — не меньше p25,
# 'max' — не больше p75)
CHECKS_SLASH = [
    ('windup', 'замах (до начала удара), с', 'band'), ('strike', 'удар, с', 'max'), ('f_recover', 'доля возврата', 'band'),
    ('ang_peak', 'пик угл. скорости клинка, °/с', 'min'), ('arc', 'дуга удара, °', 'min'),
    ('accel', 'доля разгона в ударе', 'band'), ('follow', 'перехлёст после пика', 'min'), ('decel', 'торможение после пика, с', 'max'),
    ('root_fwd_max', 'таз вперёд (макс), L', 'min'), ('root_drop', 'просадка таза, L', 'min'),
    ('step', 'шаг стопы в удар, L', 'min'), ('sh_range', 'размах плеч, °', 'min'), ('twist_range', 'скрутка плечи−таз, °', 'min'),
]
CHECKS_THRUST = [
    ('windup', 'замах (до начала удара), с', 'band'), ('strike', 'удар, с', 'max'), ('f_recover', 'доля возврата', 'band'),
    ('tip_peak', 'пик скорости острия, L/с', 'min'), ('accel', 'доля разгона в ударе', 'band'), ('decel', 'торможение после пика, с', 'max'),
    ('root_fwd_max', 'таз вперёд (макс), L', 'min'), ('root_drop', 'просадка таза, L', 'min'),
    ('step', 'шаг стопы в удар, L', 'min'), ('sh_range', 'размах плеч, °', 'min'),
]
CHECKS = {'heavy': CHECKS_SLASH, 'light': CHECKS_SLASH, 'thrust': CHECKS_THRUST}
IDLE_CHECKS = [('breath_period', 'период дыхания, с', 'band'), ('breath_amp', 'амплитуда дыхания (грудь), L', 'band'),
               ('pelvis_h', 'высота таза (стойка), L', 'max'), ('stance_w', 'ширина стойки, L', 'min'),
               ('stance_split', 'разнос стоп вперёд-назад, L', 'min'), ('stance_yaw', 'разворот плеч в стойке, °', 'band_abs')]


# Приведение к росту игрока (эталон — biped EF, нога 0.75 бл.): крупное тело движется медленнее — время ×√(рост), скорость
# ÷√(рост). Мартин рисуется ×2 (нога 12 ед. = 1.5 бл.) → множитель времени √2 ≈ 1.41: замах 0.6 с Мартина ≈ 0.42 с игрока.
TIME_KEYS = ('windup', 'strike', 'hold', 'cock', 'decel')
SPEED_KEYS = ('ang_peak', 'tip_peak')
# Смещение тела в самой анимации ограничено хитбоксом (у EF это перемещение сущности — 1–3 бл.): в модели босса не больше
# 0.5 L таза и 0.5 L шага, остальное — рывком в коде (как martin_shield_bash). Порог проверки = min(эталон p25, CAP).
BOSS_CAP = {'root_fwd_max': 0.5, 'step': 0.5}


def normalize(m, scale):
    k = math.sqrt(scale)
    n = dict(m)
    for key in TIME_KEYS:
        if n.get(key) is not None:
            n[key] = n[key] / k
    for key in SPEED_KEYS:
        if n.get(key) is not None:
            n[key] = n[key] * k
    return n


def summarize(rows):
    keys = [k for k in rows[0] if isinstance(rows[0][k], (int, float)) and not isinstance(rows[0][k], bool)]
    out = {}
    for k in keys:
        vals = [r[k] for r in rows if r.get(k) is not None]
        if vals:
            out[k] = {'p25': float(np.percentile(vals, 25)), 'med': float(np.median(vals)), 'p75': float(np.percentile(vals, 75))}
    return out


def verdict(val, ref, mode, cap=None):
    if val is None or ref is None:
        return '—', 0.0
    lo, hi = ref['p25'], ref['p75']
    if cap is not None and mode == 'min':
        lo = min(lo, cap)
    if mode == 'band_abs':
        val = abs(val)
        lo, hi = sorted((abs(ref['p25']), abs(ref['p75'])))
    tol = 0.15 * max(abs(hi - lo), abs(ref['med']) * 0.2, 1e-6)
    if mode in ('band', 'band_abs'):
        ok = lo - tol <= val <= hi + tol
        gap = 0 if ok else (lo - val if val < lo else val - hi)
    elif mode == 'min':
        ok = val >= lo - tol
        gap = 0 if ok else lo - val
    else:
        ok = val <= hi + tol
        gap = 0 if ok else val - hi
    return ('ok' if ok else 'ОТСТАЁТ'), gap


# ================================================================== эталон из jar
def measure_ref(ref_dir=None, verbose=False):
    import ef_ref as R
    J = R.find_jars(ref_dir)
    if 'ef' not in J:
        raise SystemExit('нет jar Epic Fight (libs/ или EF_REF_DIR)')
    atk, idl = [], []
    for name, an in list(R.load_set(J, R.REF_SET).items()) + list(R.load_set(J, R.REF_THRUST).items()):
        win = (an.trail[0][0] - 0.05, an.trail[0][1] + 0.05) if an.trail else None
        m = metrics(lambda t: R.ef_signals(J, an, t), an.length, win)
        m['name'], m['cls'] = name, an.cls
        atk.append(m)
        if verbose:
            print_row(name, m)
    for name, an in R.load_set(J, R.REF_IDLE).items():
        m = idle_metrics(lambda t: R.ef_signals(J, an, t), an.length)
        m['name'] = name
        idl.append(m)
    return atk, idl, J


# ================================================================== наши: Мартин (модель генератора + JSON как в GeckoLib)
class MartinRig:
    def __init__(self, path=None):
        import gen_martin as G
        import martin_anim_audit as AU
        self.G, self.AU = G, AU
        self.m = G.build_martin()
        self.blade = AU.blade_local(self.m)
        self.file = path or os.path.join(A, 'animations', 'entity', 'martin.animation.json')
        self.an = json.load(open(self.file, encoding='utf-8'))['animations']
        self.L = 12.0

    def signals(self, name, weapon='sword'):
        G, m, an, L = self.G, self.m, self.an[name], self.L

        def sig(t):
            p = self.AU.pose_at(an, t)
            W = lambda b, pt: G.world_pt(m, p, b, pt) / L
            Ms, os_ = G.fk(m, p, 'sword')
            fw = lambda b: G.fk(m, p, b)[0] @ np.array([0.0, 0.0, -1.0])
            hy = [yaw_of(fw(b)) for b in ('right_leg', 'left_leg')]
            return {
                'pelvis': W('body', m.bones['body'].pivot), 'chest': W('torso', [0, 20.0, 0]), 'head': W('head', m.bones['head'].pivot),
                'sh_r': W('right_arm', m.bones['right_arm'].pivot), 'sh_l': W('left_arm', m.bones['left_arm'].pivot),
                'hip_yaw': math.degrees(math.atan2(sum(math.sin(math.radians(x)) for x in hy), sum(math.cos(math.radians(x)) for x in hy))),
                'foot_r': W('right_leg', m.bones['right_leg'].pivot - [0, 12, 0]), 'foot_l': W('left_leg', m.bones['left_leg'].pivot - [0, 12, 0]),
                'tool': (Ms @ self.blade[0] + os_) / L, 'tip': (Ms @ self.blade[-1] + os_) / L,
                **({'tool': W('shield_hand', [-5.6, 12.5, -2.0]), 'tip': W('shield_hand', [-5.6, 12.5, -4.5])} if weapon == 'shield' else {}),
                'head_fwd': fw('head'), 'chest_fwd': fw('torso'),
                'cape': W('cape_low', [0, 1.0, 4.5]),
            }
        return sig, float(an['animation_length'])

    def events(self, name):
        return {float(k): v for k, v in self.an[name].get('timeline', {}).items()}

    def key(self, name):
        return name


# удары Мартина: анимация -> (событие удара — окно поиска пика, класс эталона, оружие). Приказы (cavalry, volley), добивание и касты —
# не удары по цели, их проверяем глазами (кадр-листы), метрики к ним не применяются.
MARTIN_ATTACKS = {'martin_swing': ('hit', 'heavy', 'sword'), 'martin_overhead': ('hit', 'heavy', 'sword'),
                  'martin_thrust': ('hit', 'thrust', 'sword'), 'martin_shield_bash': ('hit', 'thrust', 'shield')}
MARTIN_SCALE = 2.0                    # рост относительно игрока (нога 1.5 бл. / 0.75 бл.)
# рывок кодом (MartinFight.bash: от BASH_DASH до BASH_HIT, до 8 бл.; типично ~5 бл. = 3.3 L)
MARTIN_CODE_MOVE = {'martin_shield_bash': (0.45, 0.75, 5.0 / 1.5)}
MARTIN_IDLE = ['martin_idle']


# ================================================================== наши: Арис (T28; свой риг с коленями и молотом, масштаб 1.0 — рост игрока)
class ArisRig:
    def __init__(self, path=None):
        import gen_aris as GA
        import gen_aris_anims as AN
        import aris_check as AC
        AN.G = GA
        self.GA, self.AN, self.AC = GA, AN, AC
        self.m = GA.build_model()
        self.rig = AN.Rig(self.m)
        self.file = path or os.path.join(A, 'animations', 'entity', 'aris.animation.json')
        self.an = json.load(open(self.file, encoding='utf-8'))['animations']
        self.L = 12.0
        self.head_off = np.array([0.0, 0.0, -(GA.HAM_HEAD - GA.HAM_GRIP) * GA.HAM_S])

    def key(self, name):
        return name if name in self.an else 'animation.aris.' + name

    def signals(self, name, weapon='hammer'):
        an, L, AN, GA = self.an[self.key(name)], self.L, self.AN, self.GA

        def sig(t):
            W = self.rig.world(self.AC.pose_at(an, t))
            P = lambda b, pt: AN.apply(W[b], pt) / L
            fw = lambda b: W[b][0] @ np.array([0.0, 0.0, -1.0])
            hy = [yaw_of(fw(b)) for b in ('right_leg', 'left_leg')]
            return {
                'pelvis': P('body', (0, 12, 0)), 'chest': P('torso', (0, 20, 0)), 'head': P('head', (0, 24, 0)),
                'sh_r': P('right_arm', GA.SHOULDER_R), 'sh_l': P('left_arm', GA.SHOULDER_R * [-1, 1, 1]),
                'hip_yaw': math.degrees(math.atan2(sum(math.sin(math.radians(x)) for x in hy), sum(math.cos(math.radians(x)) for x in hy))),
                'foot_r': P('right_shin', (2, 0, 0)), 'foot_l': P('left_shin', (-2, 0, 0)),
                'tool': P('hammer', GA.FIST_R), 'tip': P('hammer', GA.FIST_R + self.head_off),
                'head_fwd': fw('head'), 'chest_fwd': fw('torso'),
            }
        return sig, float(an['animation_length'])

    def events(self, name):
        return {float(k): v for k, v in self.an[self.key(name)].get('timeline', {}).items()}


# ================================================================== наши: Ирина (T27; маг Iron's, посох — предмет в правой руке, ×1)
class IrinaRig:
    def __init__(self, path=None):
        import irina_anim_check as IC
        self.IC = IC
        self.r = IC.Rig()
        if path:
            self.r.anims = json.load(open(path, encoding='utf-8'))['animations']
        self.an = self.r.anims
        self.L = 14.0                         # нога Ирины: таз на 14 ед. (у мага Iron's 12)

    def key(self, name):
        return name if name in self.an else 'irina_' + name

    def signals(self, name, weapon='staff'):
        r, L = self.r, self.L
        body = self.key(name)
        cloth = self.IC.COMBOS.get(body, 'irina_cloth_idle')
        piv = lambda b: r.bones[b]['piv']

        def sig(t):
            W, _ = r.pose(body, cloth, t)
            P = lambda b, pt: r.pt(W, b, pt) / L
            fw = lambda b: W[b][:3, :3] @ np.array([0.0, 0.0, -1.0])
            hy = [yaw_of(fw(b)) for b in ('right_leg', 'left_leg')]
            return {
                'pelvis': P('body', piv('body')), 'chest': P('torso', piv('torso') - [0, 4, 0]), 'head': P('head', piv('head')),
                'sh_r': P('right_arm', piv('right_arm')), 'sh_l': P('left_arm', piv('left_arm')),
                'hip_yaw': math.degrees(math.atan2(sum(math.sin(math.radians(x)) for x in hy), sum(math.cos(math.radians(x)) for x in hy))),
                'foot_r': P('right_leg', piv('right_leg') - [0, 14, 0]), 'foot_l': P('left_leg', piv('left_leg') - [0, 14, 0]),
                'tool': r.staff_world(W, r.staff_pts['grip']) / L, 'tip': r.staff_world(W, r.staff_pts['head']) / L,
                'head_fwd': fw('head'), 'chest_fwd': fw('torso'),
            }
        return sig, float(self.an[body]['animation_length'])

    def events(self, name):
        return {float(k): v for k, v in self.an[self.key(name)].get('timeline', {}).items()}


# ================================================================== наши: Эреб (T30; маг Iron's, рапира — предмет в правой руке; FK — tools/anim_check.py)
class GeoRig:
    """Боссы, которых проверяет tools/anim_check.py (cult_leader, ereb): FK по geo.json + предмет в правой руке как у Iron's."""

    def __init__(self, path=None, name='ereb', prefix='ereb_', leg=12.0):
        import anim_check as AK
        self.AK, self.prefix = AK, prefix
        self.m = AK.Model(name)
        self.an = json.load(open(path or os.path.join(A, AK.CFG[name]['anim']), encoding='utf-8'))['animations']
        self.L = leg

    def key(self, name):
        return name if name in self.an else self.prefix + name

    def signals(self, name, weapon='item'):
        m, AK, L = self.m, self.AK, self.L
        an = self.an[self.key(name)]
        piv = lambda b: m.bones[b]['piv']

        def sig(t):
            W = m.world(an, t)
            P = lambda b, pt: AK.ap(W[b], np.asarray(pt, float) - piv(b)) / L
            fw = lambda b: W[b][:3, :3] @ np.array([0.0, 0.0, -1.0])
            hy = [yaw_of(fw(b)) for b in ('right_leg', 'left_leg')]
            it = m.item_world(W)
            return {
                'pelvis': P('body', piv('body')), 'chest': P('torso', piv('torso') - [0, 4, 0]), 'head': P('head', piv('head')),
                'sh_r': P('right_arm', piv('right_arm')), 'sh_l': P('left_arm', piv('left_arm')),
                'hip_yaw': math.degrees(math.atan2(sum(math.sin(math.radians(x)) for x in hy), sum(math.cos(math.radians(x)) for x in hy))),
                'foot_r': P('right_leg', piv('right_leg') - [0, L, 0]), 'foot_l': P('left_leg', piv('left_leg') - [0, L, 0]),
                'tool': it[m.grip_i] / L, 'tip': it[m.tip_i] / L,
                'head_fwd': fw('head'), 'chest_fwd': fw('torso'),
            }
        return sig, float(an['animation_length'])

    def events(self, name):
        return {float(k): v for k, v in self.an[self.key(name)].get('timeline', {}).items()}


# ================================================================== наши: Эреб, Длань Лжи (T31; тело Эреба + призрачная рука; FK — tools/ereb_hand_fk.py)
class ErebHandRig:
    def __init__(self, path=None):
        import ereb_hand_fk as F
        self.F = F
        self.m = F.Model()
        self.an = json.load(open(path or os.path.join(A, 'animations', 'entity', 'ereb_hand.animation.json'), encoding='utf-8'))['animations']
        self.L = 12.0

    def key(self, name):
        return name if name in self.an else 'ereb_hand_' + name

    def signals(self, name, weapon='rapier'):
        F, m, L = self.F, self.m, self.L
        an = self.an[self.key(name)]
        piv = lambda b: np.array(m.bones[b]['pivot'], float)
        flip = np.array([-1.0, 1.0, 1.0])                       # x модели — к левому боку; у нас +x — вправо

        def sig(t):
            W = m.world(F.sample(an, t))
            P = lambda b, pt: m.point(W, b, pt) * flip / L
            fw = lambda b: (W[b][:3, :3] @ np.array([0.0, 0.0, -1.0])) * flip
            hy = [yaw_of(fw(b)) for b in ('right_leg', 'left_leg')]
            if weapon == 'ghost':
                tool, tip = P('ghost_wrist', piv('ghost_wrist')), P('ghost_palm', piv('ghost_palm') - [0, 0, 3.0])
            else:
                rp = F.rapier_points(W, m)
                tool, tip = rp[0] * flip / L, rp[-1] * flip / L
            return {
                'pelvis': P('body', piv('body')), 'chest': P('torso', piv('torso') - [0, 4, 0]), 'head': P('head', piv('head')),
                'sh_r': P('right_arm', piv('right_arm')), 'sh_l': P('left_arm', piv('left_arm')),
                'hip_yaw': math.degrees(math.atan2(sum(math.sin(math.radians(x)) for x in hy), sum(math.cos(math.radians(x)) for x in hy))),
                'foot_r': P('right_leg', piv('right_leg') - [0, 12, 0]), 'foot_l': P('left_leg', piv('left_leg') - [0, 12, 0]),
                'tool': tool, 'tip': tip, 'head_fwd': fw('head'), 'chest_fwd': fw('torso'),
            }
        return sig, float(an['animation_length'])

    def events(self, name):
        return {float(k): v for k, v in self.an[self.key(name)].get('timeline', {}).items()}


def ereb_rig(path=None):
    return GeoRig(path, 'ereb', 'ereb_')


BOSSES = {
    'martin': dict(rig=MartinRig, scale=MARTIN_SCALE, code_move=MARTIN_CODE_MOVE, idle=['martin_idle'],
                   attacks={k: v for k, v in MARTIN_ATTACKS.items()}),
    'aris': dict(rig=ArisRig, scale=1.0, code_move={}, idle=['idle'],
                 attacks={'swing': ('hit', 'heavy', 'hammer'), 'slam': ('impact', 'heavy', 'hammer')}),
    # посох Ирины — древко почти в её рост, крюк на конце: эталон — тяжёлое древковое (heavy), не лёгкий меч;
    # рост ×14/12 (нога 14 ед. = 0.875 бл.)
    'ereb': dict(rig=ereb_rig, scale=1.0, code_move={}, idle=['idle'],
                 attacks={'lunge': ('hit', 'thrust', 'item'), 'flurry': ('hit', 'thrust', 'item')}),        # рапира: уколы
    'ereb_hand': dict(rig=ErebHandRig, scale=1.0, code_move={}, idle=['idle'],
                      attacks={'lunge': ('hit', 'thrust', 'rapier'), 'flurry': ('hit', 'thrust', 'rapier'),
                               'slam': ('slam', 'heavy', 'ghost')}),       # удар призрачной ладонью о землю: «клинок» — запястье → ладонь
    'irina': dict(rig=IrinaRig, scale=14.0 / 12.0, code_move={}, idle=['idle'],
                  attacks={'staff_attack': ('hit', 'heavy', 'staff'), 'staff_sweep': ('hit', 'heavy', 'staff')}),
}


def our_metrics(rig, names=None, idle=None, boss='martin'):
    B = BOSSES[boss]
    res, ires = {}, {}
    for name, (ev, cls, weapon) in B['attacks'].items():
        if names and name not in names or rig.key(name) not in rig.an:
            continue
        sig, L = rig.signals(name, weapon)
        evs = rig.events(name)
        th = [t for t, e in evs.items() if e == ev]
        win = (th[0] - 0.3, th[0] + 0.12) if th else None
        m = normalize(metrics(sig, L, win, code_move=B['code_move'].get(name)), B['scale'])
        m['event'] = (ev, th[0] if th else None)
        m['cls'] = cls
        m['scale'] = B['scale']
        res[name] = m
    for name in (idle or B['idle']):
        if rig.key(name) in rig.an and (not names or name in names):
            sig, L = rig.signals(name)
            ires[name] = idle_metrics(sig, L)
    return res, ires


# ================================================================== вывод
def fmt(x):
    if x is None:
        return '—'
    if isinstance(x, (list, tuple)):
        return '[' + ', '.join(fmt(y) for y in x) + ']'
    if isinstance(x, str):
        return x
    return ('%.0f' % x) if abs(x) >= 100 else ('%.2f' % x)


def print_row(name, m):
    print('%-24s len %.2f  замах %.2f  удар %.2f  удерж %.2f  возврат %.2f | пик %s°/с дуга %s° разгон %.2f перехлёст %.2f | '
          'таз %+.2f/%.2f вес %+.2f шаг %.2f | плечи %s° скрутка %s° (%+.0f→%+.0f) цепь %+.0f/%+.0f мс голова %s мс' % (
              name, m['length'], m['windup'], m['strike'], m['hold'], m['recover'], fmt(m['ang_peak']), fmt(m['arc']), m['accel'], m['follow'],
              m['root_fwd_max'], m['root_drop'], m['weight_shift'], m['step'], fmt(m['sh_range']), fmt(m['twist_range']),
              m['twist_windup'], m['twist_hit'], m['chain_hip_sh'], m['chain_sh_tip'], fmt(m['head_lag'])))


def report(res, ires, out=print):
    fails = 0
    for name, m in res.items():
        out('\n%s  [эталон: %s; время ÷√%g] (длина %.2f с, событие %s @ %s, пик острия @ %.2f, удар %.2f–%.2f)' % (
            name, m['cls'], m.get('scale', 1.0), m['length'], m['event'][0], fmt(m['event'][1]), m['t_peak'], *m['t_strike']))
        for k, label, mode in CHECKS[m['cls']]:
            v, r = m.get(k), REF.get(m['cls'], {}).get(k)
            st, gap = verdict(v, r, mode, BOSS_CAP.get(k))
            fails += st == 'ОТСТАЁТ'
            if k in BOSS_CAP:
                label = label + ' (босс ≥%.1f)' % BOSS_CAP[k]
            out('   %-34s %8s   эталон %s..%s (мед. %s)  %s' % (label, fmt(v), fmt(r and r['p25']), fmt(r and r['p75']), fmt(r and r['med']),
                                                         st + ('' if st != 'ОТСТАЁТ' else ' на %s' % fmt(gap))))
    for name, m in ires.items():
        out('\n%s (стойка/дыхание)' % name)
        for k, label, mode in IDLE_CHECKS:
            v, r = m.get(k), REF_IDLE.get(k)
            st, gap = verdict(v, r, mode)
            fails += st == 'ОТСТАЁТ'
            out('   %-34s %8s   эталон %s..%s (мед. %s)  %s' % (label, fmt(v), fmt(r and r['p25']), fmt(r and r['p75']), fmt(r and r['med']),
                                                         st + ('' if st != 'ОТСТАЁТ' else ' на %s' % fmt(gap))))
    return fails


def score(res, ires):
    """Сводка: сколько проверок в норме из всех."""
    ok = tot = 0
    for m in res.values():
        for k, _, mode in CHECKS[m['cls']]:
            st, _ = verdict(m.get(k), REF.get(m['cls'], {}).get(k), mode, BOSS_CAP.get(k))
            if st != '—':
                tot += 1
                ok += st == 'ok'
    for m in ires.values():
        for k, _, mode in IDLE_CHECKS:
            st, _ = verdict(m.get(k), REF_IDLE.get(k), mode)
            if st != '—':
                tot += 1
                ok += st == 'ok'
    return ok, tot


def main(args):
    if '--measure-ref' in args:
        rd = args[args.index('--ref-dir') + 1] if '--ref-dir' in args else None
        atk, idl, J = measure_ref(rd, verbose=True)
        for m in idl:
            print('%-22s %s' % (m['name'], ' '.join('%s=%s' % (k, fmt(v)) for k, v in m.items() if k != 'name')))
        cls = sorted({m['cls'] for m in atk})
        ref = {'sources': {k: os.path.basename(v) for k, v in J.items()},
               'attack': {c: summarize([m for m in atk if m['cls'] == c]) for c in cls}, 'idle': summarize(idl),
               'attack_rows': atk, 'idle_rows': idl}
        path = args[args.index('--json') + 1] if '--json' in args else REF_FILE
        json.dump(ref, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('эталон: %d атак, %d стоек → %s' % (len(atk), len(idl), path))
        return 0
    f = args[args.index('--file') + 1] if '--file' in args else None
    only = [args[args.index('--anim') + 1]] if '--anim' in args else None
    boss = args[args.index('--boss') + 1] if '--boss' in args else 'martin'
    rig = BOSSES[boss]['rig'](f)
    res, ires = our_metrics(rig, only, boss=boss)
    if '-v' in args:
        for n, m in res.items():
            print_row(n, m)
    fails = report(res, ires)
    ok, tot = score(res, ires)
    print('\nв норме эталона: %d из %d проверок (%.0f%%)' % (ok, tot, 100.0 * ok / max(1, tot)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
