#!/usr/bin/env python3
"""
Генератор анимаций игрока для заклинаний pohsmp_core.

Формат — родной JSON PlayerAnimator (Emotecraft, version 3): по файлу на анимацию, со сгибами локтей,
колен и корпуса. Сгибы видны, если у игрока стоит bendy-lib; без него руки остаются прямыми, ничего не ломается.
Файлы кладутся в пространство имён Iron's (assets/irons_spellbooks/player_animation/), поэтому в заклинании
достаточно new AnimationHolder("<имя>", true).

Руки ставятся обратной кинематикой: задаём, где кисть (в пикселях модели) и куда смотрит посох, а плечо,
локоть и поворот предплечья скрипт подбирает сам. Вторая рука может держать посох в точке на его древке.

Оси модели (пиксели): +X — влево от игрока, +Y — вверх, +Z — вперёд; ступни на y=0, плечи на y=22.
Углы PlayerAnimator: pitch минус — рука вперёд и вверх; roll плюс у правой руки — в сторону вправо;
yaw плюс — поворот вправо; bend минус у руки — предплечье вперёд (как локоть), у ноги плюс — как колено.

Запуск:  python3 tools/gen_player_anims.py   (пишет JSON и tools/anim_preview.html)
"""
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'irons_spellbooks', 'player_animation')

TPS = 20
UPPER, LOWER = 4.0, 5.0                     # плечо -> локоть, локоть -> хват (пиксели; сгиб bendy-lib в середине руки)
SHOULDER = {'right': np.array([-5.0, 22.0, 0.0]), 'left': np.array([5.0, 22.0, 0.0])}
BODY_X = 4.0                                # полуширина корпуса: локоть не должен в него уходить


# ------------------------------------------------------------------ математика
def _n(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _euler(m):
    """m = Rz(c) Ry(b) Rx(a) -> углы PlayerAnimator [pitch, yaw, roll] в градусах."""
    b = math.asin(max(-1.0, min(1.0, -m[2, 0])))
    if abs(m[2, 0]) < 0.9999:
        a = math.atan2(m[2, 1], m[2, 2])
        c = math.atan2(m[1, 0], m[0, 0])
    else:
        a, c = math.atan2(-m[1, 2], m[1, 1]), 0.0
    return [math.degrees(a), -math.degrees(b), -math.degrees(c)]


def _perp(v, ref):
    """Единичный вектор, перпендикулярный v, как можно ближе к ref."""
    r = np.asarray(ref, dtype=float) - np.dot(ref, v) * v
    if np.linalg.norm(r) < 1e-6:
        r = np.cross([1.0, 0, 0], v) if abs(v[0]) < 0.9 else np.cross([0, 0, 1.0], v)
    return _n(r)


ITEM_FIX_MAX = 25.0   # на сколько градусов разрешено докручивать посох в кисти (rightItem roll) в статичных позах


def arm(side, hand, staff=None, elbow_out=1.0, fore=None, prev_u=None):
    """
    Кисть в точке hand (пиксели модели), посох в этой руке смотрит по staff, предплечье — примерно по fore.
    Перебираем, куда отвести локоть, и берём вариант, где посох ближе к нужному направлению,
    а локоть выглядит естественно: ниже кисти, снаружи от корпуса.
    Возвращает ({'pitch','yaw','roll','bend'}, info), где info: 'staff' — куда смотрит посох без докрутки,
    'fore' — направление предплечья, 'twist' — на сколько градусов докрутить посох вокруг предплечья
    (rightItem roll, плюс — против часовой, если смотреть со стороны локтя на кисть... см. item_twist).
    """
    sx = -1.0 if side == 'right' else 1.0
    h = np.asarray(hand, dtype=float) - SHOULDER[side]
    d = float(np.linalg.norm(h))
    d = min(max(d, abs(UPPER - LOWER) + 0.05), UPPER + LOWER - 0.05)
    hd = _n(h)
    hp = hd * d
    cos_g = (UPPER ** 2 + LOWER ** 2 - d ** 2) / (2 * UPPER * LOWER)
    bend = -(math.pi - math.acos(max(-1, min(1, cos_g))))          # минус: предплечье вперёд
    cos_a = (UPPER ** 2 + d ** 2 - LOWER ** 2) / (2 * UPPER * d)
    alpha = math.acos(max(-1, min(1, cos_a)))
    p0 = _perp(hd, (0, -1.0, 0) if abs(hd[1]) < 0.95 else (0, 0, -1.0))
    p1 = np.cross(hd, p0)
    best = None
    for k in range(180):
        phi = 2 * math.pi * k / 180
        pole = math.cos(phi) * p0 + math.sin(phi) * p1
        u = math.cos(alpha) * hd + math.sin(alpha) * pole       # плечо -> локоть
        elbow = u * UPPER
        f = _n(hp - elbow)                                       # локоть -> кисть
        # предплечье = плечо * Rx(bend): при bend < 0 оно уходит к локальной +Z плеча
        zu = _perp(u, f if abs(bend) > 1e-3 else (staff if staff is not None else (0, 0, 1.0)))
        yu = -u
        up = np.column_stack([np.cross(yu, zu), yu, zu])
        low = up @ _rx(bend)
        st = low[:, 2]                                           # посох торчит по локальной +Z предплечья
        e_abs = SHOULDER[side] + elbow
        score = 0.0
        if staff is not None:
            score += 4.0 * float(np.dot(st, _n(staff))) - 2.0 * abs(float(np.dot(f, _n(staff))))
        if fore is not None:
            score += 3.0 * float(np.dot(f, _n(fore)))
        if prev_u is not None:                                   # не перескакивать локтем между соседними позами
            score += 1.5 * float(np.dot(u, prev_u))
        score += elbow_out * (0.6 * (-u[1]) + 0.5 * (e_abs[0] * sx - BODY_X) / 4.0)
        if e_abs[0] * sx < BODY_X - 0.5 and e_abs[2] < 2.5:      # локоть внутри корпуса
            score -= 3.0
        if best is None or score > best[0]:
            best = (score, up, st, f, u)
    p, y, r = _euler(best[1])
    info = {'staff': best[2], 'fore': best[3], 'twist': 0.0, 'u': best[4]}
    if staff is not None:
        info['twist'] = item_twist(best[3], best[2], staff)
    return {'pitch': p, 'yaw': y, 'roll': r, 'bend': math.degrees(bend)}, info


def item_twist(fore, cur, want):
    """
    Угол (градусы) поворота предмета вокруг предплечья, который переводит посох из cur в want.
    rightItem roll крутит предмет вокруг оси «от кисти к локтю» (-fore) по правилу правой руки:
    если смотреть игроку в спину при предплечье вперёд, плюс — против часовой стрелки.
    """
    ax = -_n(fore)
    w = np.asarray(want, dtype=float)
    w = w - np.dot(w, ax) * ax
    c = cur - np.dot(cur, ax) * ax
    if np.linalg.norm(w) < 1e-6 or np.linalg.norm(c) < 1e-6:
        return 0.0
    w, c = _n(w), _n(c)
    return math.degrees(math.atan2(float(np.dot(np.cross(c, w), ax)), float(np.dot(c, w))))


def grip(hand, staff, dist):
    """Точка на древке в dist пикселях от хвата hand по направлению staff (для второй руки)."""
    return np.asarray(hand, dtype=float) + _n(staff) * dist


def _a(side, hand, staff=None, **kw):
    return arm(side, hand, staff, **kw)[0]


def _fix(info):
    """Небольшая докрутка посоха в кисти для статичной позы (не больше ITEM_FIX_MAX)."""
    return max(-ITEM_FIX_MAX, min(ITEM_FIX_MAX, info['twist']))


# ------------------------------------------------------------------ дорожки и вывод
class Anim:
    def __init__(self, name, seconds, hold=True):
        self.name, self.end, self.hold = name, int(round(seconds * TPS)), hold
        self.keys = {}                       # part -> [(tick, {channel: value}, easing)]

    def key(self, t, part, ease='easeInOutSine', **ch):
        self.keys.setdefault(part, []).append((int(round(t * TPS)), ch, ease))

    def pose(self, t, ease='easeInOutSine', **parts):
        for part, ch in parts.items():
            self.key(t, part, ease, **ch)

    def sway(self, t0, t1, period, part, base, channel, amp):
        """Медленное покачивание одного канала вокруг позы base; на t1 возвращается в base."""
        t, sign = t0, 1
        while t + period / 2 < t1 - 1e-6:
            t += period / 2
            ch = dict(base)
            ch[channel] = ch.get(channel, 0) + amp * sign
            self.key(t, part, **ch)
            sign = -sign
        self.key(t1, part, **base)

    def emotecraft(self):
        moves = []
        for part, ks in self.keys.items():
            ks.sort(key=lambda k: k[0])
            prev = {}
            for tick, ch, ease in ks:
                # углы частей тела берём ближайшие к предыдущему ключу; у предмета в руке — как задано (там +360 = оборот)
                if part not in ('rightItem', 'leftItem'):
                    ch = _nearest_euler(prev, ch)
                prev.update(ch)
                moves.append({'tick': tick, 'easing': ease, part: {c: round(float(v), 2) for c, v in ch.items()}})
        moves.sort(key=lambda m: m['tick'])
        emote = {'beginTick': 0, 'endTick': self.end, 'stopTick': self.end, 'degrees': True,
                 'easeBeforeKeyframe': True, 'moves': moves}
        if self.hold:
            emote.update({'isLoop': True, 'returnTick': self.end})
        return {'version': 3, 'name': self.name, 'author': 'pohsmp_core', 'emote': emote}


def _nearest_euler(prev, ch):
    """
    Одна и та же ориентация записывается двумя наборами углов: (p, y, r) и (p+180, -180-y, r-180), плюс любые ±360.
    Берём запись, ближайшую к предыдущему ключу: иначе между ключами часть тела крутится длинным путём.
    """
    if not all(c in ch for c in ('pitch', 'yaw', 'roll')) or not all(c in prev for c in ('pitch', 'yaw', 'roll')):
        return {c: (v + 360 * round((prev[c] - v) / 360)) if c in ('pitch', 'yaw', 'roll') and c in prev else v
                for c, v in ch.items()}
    p, y, r = ch['pitch'], ch['yaw'], ch['roll']
    best = None
    for cand in ((p, y, r), (p + 180, -180 - y, r - 180)):
        w = [v + 360 * round((prev[c] - v) / 360) for v, c in zip(cand, ('pitch', 'yaw', 'roll'))]
        d = sum(abs(a - prev[c]) for a, c in zip(w, ('pitch', 'yaw', 'roll')))
        if best is None or d < best[0]:
            best = (d, w)
    out = dict(ch)
    out['pitch'], out['yaw'], out['roll'] = best[1]
    return out


class Rig:
    """Обе руки с памятью о прошлой позе: локоть плавно переходит, а не прыгает между решениями."""
    def __init__(self):
        self.u = {'right': None, 'left': None}

    def arm(self, side, hand, staff=None, **kw):
        q, info = arm(side, hand, staff, prev_u=self.u[side], **kw)
        self.u[side] = info['u']
        return q

    def R(self, x, y, z, staff=None, **kw):
        return self.arm('right', (x, y, z), staff, **kw)

    def L(self, x, y, z, staff=None, **kw):
        return self.arm('left', (x, y, z), staff, **kw)


def merge(*dicts):
    out = {}
    for d in dicts:
        out.update(d)
    return out


# ================================================================== Низвержение
# Каст 25 с (DownfallSpell.CAST = 500 тиков). Хореография по видео (камера там смотрит игроку в спину):
#   0      — стоит неподвижно, руки вдоль тела; посох висит в воздухе справа (клиентский эффект, не эта анимация)
#   4а     — «Сосредоточение»: правая кисть у подбородка, предплечье поперёк корпуса, голова опущена
#   4б     — кисть падает влево вниз, посох появляется там и взмахом встаёт по диагонали: навершие вверху слева
#   4в     — посох встаёт горизонтально и делает полный оборот вокруг кисти перед грудью, во фронтальной
#            плоскости, как жезл (~0.75 с, медленнее в начале и в конце); кисть почти неподвижна
#   4г     — «Активация»: посох замирает горизонтально перед грудью навершием влево, левая рука берётся за древко
#   10, 15 с — толчки заклинания (разлом, нить): игрок упирается, посох подаётся вперёд
# Оборот делается поворотом предмета в кисти (rightItem roll) ровно на 360°: куда бы ни шло вращение в игре,
# посох закончит его там же, где начал.

T_FOCUS, T_FOCUS_END = 1.2, 2.45
T_DROP, T_DIAG, T_FLAT = 2.65, 2.95, 3.12       # кисть влево вниз -> диагональ -> горизонталь
T_TWIRL_END = 3.87                               # полный оборот за 0.75 с
T_GRAB, T_HOLD = 4.15, 4.4

S_DROP = (0.35, 0.85, 0.4)                       # посох слева внизу, навершие вверх (входит в кадр слева)
S_DIAG = (0.62, 0.76, 0.18)                      # навершие вверху слева
S_HORIZ = (1.0, 0.0, 0.0)                        # навершие влево

DROP_R = (0.8, 14.6, 5.6)                        # кисть перед животом слева
DIAG_R = (-1.4, 16.6, 5.8)
TWIRL_R = (-5.5, 20.0, 8.5)                      # рука вперёд, кисть на уровне верха груди (подобрано перебором)
FORE = (0.0, 0.0, 1.0)
GRIP_L = 10.0                                    # левая рука берётся за древко на 10 px ближе к навершию

REST_R = {'pitch': 0, 'yaw': 0, 'roll': 3, 'bend': -4}
REST_L = {'pitch': 0, 'yaw': 0, 'roll': -3, 'bend': -4}
STANCE_R, STANCE_L = {'roll': 4, 'pitch': 6, 'bend': 8}, {'roll': -5, 'pitch': -8, 'bend': 4}
LEGS_REST = {'roll': 0, 'pitch': 0, 'bend': 0}
BREATHE = {'pitch': -3, 'yaw': 0, 'bend': -3}


def _twirl_pose():
    """Рука для оборота и удержания: предплечье вперёд, посох горизонтально навершием влево."""
    q, info = arm('right', TWIRL_R, S_HORIZ, fore=FORE)
    staff = _n(info['staff'])
    # после докрутки посох смотрит по S_HORIZ, спроецированному на плоскость оборота
    ax = -_n(info['fore'])
    flat = _n(np.asarray(S_HORIZ) - np.dot(S_HORIZ, ax) * ax)
    return q, info['twist'], flat


def downfall_cast():
    a = Anim('pohsmp_downfall_cast', 25.0)
    a.pose(0, rightArm=REST_R, leftArm=REST_L, torso={'pitch': 0, 'yaw': 0, 'bend': 0}, head={'pitch': 0, 'yaw': 0},
           rightLeg={'roll': 2, 'pitch': 0, 'bend': 0}, leftLeg={'roll': -2, 'pitch': 0, 'bend': 0},
           rightItem={'roll': 0})
    a.sway(0, T_FOCUS - 0.4, 1.6, 'torso', {'pitch': 0, 'yaw': 0, 'bend': 0}, 'pitch', 1.0)

    # 4а — сосредоточение
    focus_r = _a('right', (0.6, 21.2, 4.2), staff=(0, 1, 0.2))
    a.pose(T_FOCUS - 0.4, rightArm=REST_R, leftArm=REST_L, head={'pitch': 0, 'yaw': 0})
    a.pose(T_FOCUS, rightArm=focus_r, leftArm={'pitch': 0, 'yaw': 0, 'roll': -5, 'bend': -8},
           torso={'pitch': 4, 'yaw': -4, 'bend': 6}, head={'pitch': 18, 'yaw': -6})
    a.pose(T_FOCUS_END, rightArm=merge(focus_r, {'pitch': focus_r['pitch'] - 4}),
           torso={'pitch': 5, 'yaw': -4, 'bend': 8}, head={'pitch': 22, 'yaw': -6})

    # 4б — кисть падает влево вниз (там посох появляется), взмах вверх в диагональ
    drop_q, drop_i = arm('right', DROP_R, S_DROP)
    diag_q, diag_i = arm('right', DIAG_R, S_DIAG, fore=FORE)
    a.pose(T_DROP, 'easeInQuad', rightArm=drop_q, rightItem={'roll': _fix(drop_i)},
           torso={'pitch': 3, 'yaw': -12, 'bend': 4}, head={'pitch': 10, 'yaw': -14})
    a.pose(T_DIAG, 'easeOutCubic', rightArm=diag_q, rightItem={'roll': _fix(diag_i)},
           torso={'pitch': -2, 'yaw': 4, 'bend': -2}, head={'pitch': -8, 'yaw': 4})
    a.pose(T_DIAG, leftArm=_a('left', (8.0, 13.0, 2.5), elbow_out=1.4))

    # 4в — горизонталь и полный оборот вокруг кисти
    tw_q, tw_fix, _ = _twirl_pose()
    a.pose(T_FLAT, 'easeInOutQuad', rightArm=tw_q, rightItem={'roll': tw_fix},
           torso={'pitch': 0, 'yaw': 0, 'bend': 0}, head={'pitch': -2, 'yaw': 0})
    a.key(T_TWIRL_END, 'rightItem', 'easeInOutSine', roll=tw_fix + 360)
    a.pose(T_TWIRL_END, rightArm=tw_q)
    # корпус чуть «провожает» посох
    a.pose((T_FLAT + T_TWIRL_END) / 2, torso={'pitch': -1, 'yaw': 3, 'bend': -1}, head={'pitch': -4, 'yaw': 2})
    a.pose(T_TWIRL_END, torso={'pitch': 0, 'yaw': 0, 'bend': 0}, head={'pitch': -2, 'yaw': 0},
           rightLeg={'roll': 2, 'pitch': 0, 'bend': 0}, leftLeg={'roll': -2, 'pitch': 0, 'bend': 0})

    # 4г — активация: левая рука берётся за древко ближе к навершию, стойка шире
    hold_r = tw_q
    _, _, flat = _twirl_pose()
    hold_l_pt = grip(TWIRL_R, flat, GRIP_L)
    hold_l = _a('left', hold_l_pt, flat)
    a.pose(T_GRAB, 'easeOutBack', leftArm=hold_l)
    a.pose(T_HOLD, torso=BREATHE, head={'pitch': -6, 'yaw': 0}, rightLeg=STANCE_R, leftLeg=STANCE_L)

    # удержание: дыхание и два толчка заклинания (10 с — разлом, 15 с — нить)
    push_r = _a('right', np.add(TWIRL_R, (0, 0.4, 1.4)), S_HORIZ, fore=FORE)
    push_l = _a('left', np.add(hold_l_pt, (0, 0.4, 1.4)), flat)
    a.sway(T_HOLD, 9.6, 3.2, 'torso', BREATHE, 'pitch', 1.2)
    a.sway(11.0, 14.6, 3.2, 'torso', BREATHE, 'pitch', 1.2)
    a.sway(16.0, 25.0, 3.2, 'torso', BREATHE, 'pitch', 1.2)
    for t in (10.0, 15.0):
        a.pose(t - 0.4, rightArm=hold_r, leftArm=hold_l, head={'pitch': -6, 'yaw': 0})
        a.pose(t, 'easeOutCubic', rightArm=push_r, leftArm=push_l, torso={'pitch': 4, 'yaw': 0, 'bend': 2},
               head={'pitch': -2, 'yaw': 0})
        a.pose(t + 1.0, rightArm=hold_r, leftArm=hold_l, torso=BREATHE, head={'pitch': -6, 'yaw': 0})
    a.pose(25.0, rightArm=hold_r, leftArm=hold_l, head={'pitch': -6, 'yaw': 0}, rightLeg=STANCE_R, leftLeg=STANCE_L,
           rightItem={'roll': tw_fix + 360})
    return a


def downfall_finish():
    """После каста: преграда резко толкается вперёд, затем руки опускаются."""
    a = Anim('pohsmp_downfall_finish', 1.5, hold=False)
    tw_q, tw_fix, flat = _twirl_pose()
    hold_l_pt = grip(TWIRL_R, flat, GRIP_L)
    a.pose(0, rightArm=tw_q, leftArm=_a('left', hold_l_pt, flat), torso=BREATHE, head={'pitch': -6, 'yaw': 0},
           rightLeg=STANCE_R, leftLeg=STANCE_L, rightItem={'roll': tw_fix})
    a.pose(0.18, 'easeOutCubic', rightArm=_a('right', np.add(TWIRL_R, (0, 0.6, 3.0)), S_HORIZ, fore=FORE),
           leftArm=_a('left', np.add(hold_l_pt, (0, 0.6, 3.0)), flat),
           torso={'pitch': 9, 'yaw': 0, 'bend': 4}, head={'pitch': 0, 'yaw': 0})
    a.pose(0.5, rightArm=_a('right', (-3.0, 15.5, 5.0), (0.2, 1, 0.3)),
           leftArm={'pitch': 0, 'yaw': 0, 'roll': -6, 'bend': -6}, torso={'pitch': 2, 'yaw': 0, 'bend': 0},
           rightItem={'roll': 0})
    a.pose(1.5, rightArm={'pitch': 0, 'yaw': 0, 'roll': 0, 'bend': 0}, leftArm={'pitch': 0, 'yaw': 0, 'roll': 0, 'bend': 0},
           torso={'pitch': 0, 'yaw': 0, 'bend': 0}, head={'pitch': 0, 'yaw': 0}, rightLeg=LEGS_REST, leftLeg=LEGS_REST)
    return a


# ================================================================== заклинания без посоха
# Для заклинаний с роликом камеры (кроме Низвержения) — анимации без посоха: предмет в руках на время
# анимации прячет клиент (client/HiddenHands). Планы камеры (client/DownfallCut) у сцен 1–4 меняются на долях
# каста 0 / .16 / .32 / .50 / .68 / .84, под них и поставлены движения.

CUTS = (0.0, 0.16, 0.32, 0.5, 0.68, 0.84, 1.0)
ZERO_T = {'pitch': 0, 'yaw': 0, 'roll': 0, 'bend': 0}
ZERO_H = {'pitch': 0, 'yaw': 0, 'roll': 0}
ZERO_LEG = {'pitch': 0, 'yaw': 0, 'roll': 0, 'bend': 0}
ARM_DOWN_R = {'pitch': 0, 'yaw': 0, 'roll': 3, 'bend': -5}
ARM_DOWN_L = {'pitch': 0, 'yaw': 0, 'roll': -3, 'bend': -5}
WIDE_R, WIDE_L = {'pitch': 0, 'yaw': 0, 'roll': 3, 'bend': 4}, {'pitch': 0, 'yaw': 0, 'roll': -3, 'bend': 4}


def _shots(total):
    return [total * c for c in CUTS]


def _start(a):
    a.pose(0, rightArm=ARM_DOWN_R, leftArm=ARM_DOWN_L, torso=ZERO_T, head=ZERO_H, body={'y': 0},
           rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)


def _finish(name, from_r, from_l, torso=None, head=None, legs=None, body_y=0.0, length=1.2):
    """Короткий финал: из последней позы каста руки опускаются, тело выпрямляется."""
    a = Anim(name, length, hold=False)
    first = dict(rightArm=from_r, leftArm=from_l, torso=torso or ZERO_T, head=head or ZERO_H, body={'y': body_y})
    if legs:
        first.update(rightLeg=legs[0], leftLeg=legs[1])
    a.pose(0, **first)
    a.pose(length, rightArm=ZERO_LEG, leftArm=ZERO_LEG, torso=ZERO_T, head=ZERO_H, body={'y': 0},
           rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)
    return a


# ---------------------------------------------------------------- Млечный Путь (10 с)
# Планы: облёт за спиной -> снизу сбоку, взгляд вверх -> сверху, вращение -> облёт на уровне груди ->
# из-за плеча по направлению потока -> спереди, тряска (поток уходит из ладони).
def _fk(pitch=0.0, yaw=0.0, roll=0.0, bend=0.0):
    """Рука углами суставов (без обратной кинематики): правая; левая — mirror()."""
    return {'pitch': pitch, 'yaw': yaw, 'roll': roll, 'bend': bend}


def mirror(q):
    """Та же поза для другой руки: yaw и roll с обратным знаком."""
    return {'pitch': q['pitch'], 'yaw': -q['yaw'], 'roll': -q['roll'], 'bend': q['bend']}


def milky_way_cast():
    T = 10.0
    c = _shots(T)
    a, r = Anim('pohsmp_milky_way_cast', T), Rig()
    _start(a)
    # «семя галактики» в ладонях перед животом, взгляд на руки
    cup_r, cup_l = r.R(-1.6, 14.2, 5.2), r.L(1.6, 14.2, 5.2)
    a.pose(c[1] * 0.55, rightArm=cup_r, leftArm=cup_l, torso={'pitch': 6, 'yaw': 0, 'roll': 0, 'bend': 6},
           head={'pitch': 24, 'yaw': 0, 'roll': 0})
    a.pose(c[1], rightArm=r.R(-1.8, 15.2, 5.4), leftArm=r.L(1.8, 15.2, 5.4))
    # дальше руки почти прямые и широко разведены — их задаём углами суставов, чтобы переходы были плавными:
    # руки медленно расходятся и поднимаются — галактика растёт; взгляд вверх (камера снизу)
    rise = _fk(pitch=-95, roll=38, bend=-30)
    a.pose(c[1] + 0.9, rightArm=rise, leftArm=mirror(rise),
           torso={'pitch': -2, 'yaw': 0, 'roll': 0, 'bend': -2}, head={'pitch': -8, 'yaw': 0, 'roll': 0})
    v_up = _fk(pitch=-25, roll=140, bend=-14)
    a.pose(c[2], rightArm=v_up, leftArm=mirror(v_up),
           torso={'pitch': -6, 'yaw': 0, 'roll': 0, 'bend': -6}, head={'pitch': -32, 'yaw': 0, 'roll': 0})
    # сверху: руки опускаются в стороны, корпус закручивает спираль, руки качаются, как рукава галактики
    t_pose = _fk(pitch=-8, roll=88, bend=-8)
    a.pose(c[2] + 0.7, rightArm=t_pose, leftArm=mirror(t_pose), head={'pitch': -10, 'yaw': 0, 'roll': 0},
           torso={'pitch': 0, 'yaw': -20, 'roll': 0, 'bend': 0})
    tilt_a, tilt_b = _fk(pitch=-12, roll=118, bend=-10), _fk(pitch=-4, roll=62, bend=-6)
    a.pose(c[2] + 1.35, rightArm=tilt_a, leftArm=mirror(tilt_b), torso={'pitch': 0, 'yaw': 16, 'roll': -3, 'bend': 0},
           head={'pitch': -8, 'yaw': 8, 'roll': 0})
    a.pose(c[3], rightArm=tilt_b, leftArm=mirror(tilt_a), torso={'pitch': 0, 'yaw': -12, 'roll': 3, 'bend': 0},
           head={'pitch': -8, 'yaw': -6, 'roll': 0})
    # облёт: правая дугой над головой, левая низко в сторону — рукава спирали
    over = _fk(pitch=-30, roll=158, bend=-38)
    low = _fk(pitch=-18, roll=38, bend=-10)
    a.pose(c[3] + 0.9, rightArm=over, leftArm=mirror(low),
           torso={'pitch': -3, 'yaw': 12, 'roll': -4, 'bend': -2}, head={'pitch': -14, 'yaw': 10, 'roll': 0})
    sweep = _fk(pitch=-78, roll=12, bend=-30)          # правая проходит перед грудью
    out_l = _fk(pitch=12, roll=62, bend=-10)
    a.pose(c[4], rightArm=sweep, leftArm=mirror(out_l),
           torso={'pitch': 2, 'yaw': -16, 'roll': 3, 'bend': 2}, head={'pitch': 0, 'yaw': -12, 'roll': 0})
    # из-за плеча: собирает силу — правая отведена назад к боку, левая вытянута вперёд, ладонь к цели
    gather = _fk(pitch=28, roll=14, bend=-70)
    aim = _fk(pitch=-86, yaw=-8, roll=4, bend=-6)
    a.pose(c[4] + 0.7, 'easeOutCubic', rightArm=gather, leftArm=mirror(aim),
           torso={'pitch': 0, 'yaw': -14, 'roll': 0, 'bend': 0}, head={'pitch': -2, 'yaw': -6, 'roll': 0},
           rightLeg={'pitch': 8, 'yaw': 0, 'roll': 3, 'bend': 10}, leftLeg={'pitch': -10, 'yaw': 0, 'roll': -3, 'bend': 6})
    a.pose(c[5], rightArm=_fk(pitch=34, roll=16, bend=-78), torso={'pitch': -2, 'yaw': -20, 'roll': 0, 'bend': -2})
    # спереди: правая ладонь бьёт вперёд — поток уходит из руки; левая отходит назад
    a.pose(c[5] + 0.9, 'easeInCubic', rightArm=_fk(pitch=30, roll=16, bend=-74), leftArm=mirror(_fk(pitch=-70, roll=10, bend=-20)))
    thrust, back = _fk(pitch=-88, yaw=6, roll=-4, bend=-6), mirror(_fk(pitch=30, roll=18, bend=-12))
    a.pose(c[5] + 1.2, 'easeOutBack', rightArm=thrust, leftArm=back,
           torso={'pitch': 8, 'yaw': 14, 'roll': 0, 'bend': 4}, head={'pitch': 0, 'yaw': 4, 'roll': 0})
    a.pose(T, rightArm=thrust, leftArm=back, torso={'pitch': 6, 'yaw': 12, 'roll': 0, 'bend': 3},
           head={'pitch': 0, 'yaw': 4, 'roll': 0},
           rightLeg={'pitch': 8, 'yaw': 0, 'roll': 3, 'bend': 10}, leftLeg={'pitch': -10, 'yaw': 0, 'roll': -3, 'bend': 6})
    return a, (thrust, back, {'pitch': 6, 'yaw': 12, 'roll': 0, 'bend': 3},
               ({'pitch': 8, 'yaw': 0, 'roll': 3, 'bend': 10}, {'pitch': -10, 'yaw': 0, 'roll': -3, 'bend': 6}), 0.0)


# ---------------------------------------------------------------- Пожирание душ (25 с)
# Планы: облёт цели -> облёт заклинателя вблизи -> сверху между ними -> сбоку на обоих -> снизу на цель ->
# у цели, тряска. Душу тянут к себе руками, перехватывая, как канат.
def soul_devour_cast():
    T = 25.0
    c = _shots(T)
    a, r = Anim('pohsmp_soul_devour_cast', T), Rig()
    _start(a)
    lean = {'pitch': 6, 'yaw': 0, 'roll': 0, 'bend': 6}
    claw_r = r.R(-3.2, 21.5, 8.6)
    a.pose(1.4, 'easeOutCubic', rightArm=claw_r, leftArm=r.L(6.5, 15.0, 1.0), torso=lean,
           head={'pitch': 6, 'yaw': 0, 'roll': 0},
           rightLeg={'pitch': 6, 'yaw': 0, 'roll': 3, 'bend': 6}, leftLeg={'pitch': -8, 'yaw': 0, 'roll': -3, 'bend': 4})
    a.sway(1.4, c[1], 1.3, 'head', {'pitch': 6, 'yaw': 0, 'roll': 0}, 'roll', 3)
    # крупно: пальцы «сжимают» — рука дрожит, левая поднимается к груди
    a.pose(c[1] + 0.8, rightArm=r.R(-3.4, 21.0, 8.2), leftArm=r.L(2.0, 19.0, 5.0),
           torso={'pitch': 9, 'yaw': -6, 'roll': 0, 'bend': 8}, head={'pitch': 14, 'yaw': -4, 'roll': 6})
    for i, t in enumerate([c[1] + 1.2 + 0.25 * k for k in range(10)]):
        a.key(t, 'rightArm', **r.R(-3.4 + (0.25 if i % 2 else -0.25), 21.0 + (0.2 if i % 2 else 0), 8.2))
    # сверху и сбоку: тянет душу на себя, перехватывая руками
    near, far = (-4.6, 18.4, 2.2), (-3.0, 20.6, 8.6)
    near_l, far_l = (4.6, 18.4, 2.2), (3.0, 20.6, 8.6)
    t = c[2]
    strain = 0
    while t < c[4] - 0.5:
        k = (t - c[2]) / (c[4] - c[2])
        lean_back = {'pitch': -4 - 6 * k, 'yaw': 6, 'roll': 0, 'bend': -3 - 4 * k}
        a.pose(t, rightArm=r.R(*far), leftArm=r.L(*near_l), torso=lean_back,
               head={'pitch': -2, 'yaw': 0, 'roll': 0})
        a.pose(t + 1.1, 'easeInOutQuad', rightArm=r.R(*near), leftArm=r.L(*far_l),
               torso=merge(lean_back, {'yaw': -6}))
        t += 2.2
        strain += 1
    a.pose(c[3], rightLeg={'pitch': 14, 'yaw': 0, 'roll': 3, 'bend': 18}, leftLeg={'pitch': -14, 'yaw': 0, 'roll': -3, 'bend': 10},
           body={'y': -0.06})
    # снизу на цель: обе ладони вперёд и вверх — душа поднимается
    up_r, up_l = r.R(-3.4, 24.5, 8.0), r.L(3.4, 24.5, 8.0)
    a.pose(c[4] + 0.4, rightArm=r.R(-3.4, 20.5, 8.4), leftArm=r.L(3.4, 20.5, 8.4),
           torso={'pitch': 2, 'yaw': 0, 'roll': 0, 'bend': 0}, head={'pitch': 0, 'yaw': 0, 'roll': 0})
    a.pose(c[5] - 0.3, rightArm=up_r, leftArm=up_l, torso={'pitch': -6, 'yaw': 0, 'roll': 0, 'bend': -6},
           head={'pitch': -18, 'yaw': 0, 'roll': 0})
    # у цели: руки дрожат, в конце резко прижимает душу к груди
    a.sway(c[5], T - 0.7, 0.4, 'torso', {'pitch': -6, 'yaw': 0, 'roll': 0, 'bend': -6}, 'roll', 2)
    a.pose(T - 0.7, rightArm=r.R(-3.0, 25.0, 8.6), leftArm=r.L(3.0, 25.0, 8.6))
    chest_r, chest_l = r.R(-1.2, 18.6, 4.6), r.L(1.2, 18.6, 4.6)
    a.pose(T - 0.2, 'easeOutBack', rightArm=chest_r, leftArm=chest_l,
           torso={'pitch': -10, 'yaw': 0, 'roll': 0, 'bend': -8}, head={'pitch': -26, 'yaw': 0, 'roll': 0})
    a.pose(T, rightArm=chest_r, leftArm=chest_l, torso={'pitch': -10, 'yaw': 0, 'roll': 0, 'bend': -8},
           head={'pitch': -26, 'yaw': 0, 'roll': 0},
           rightLeg={'pitch': 14, 'yaw': 0, 'roll': 3, 'bend': 18}, leftLeg={'pitch': -14, 'yaw': 0, 'roll': -3, 'bend': 10},
           body={'y': -0.06})
    return a, (chest_r, chest_l, {'pitch': -10, 'yaw': 0, 'roll': 0, 'bend': -8},
               ({'pitch': 14, 'yaw': 0, 'roll': 3, 'bend': 18}, {'pitch': -14, 'yaw': 0, 'roll': -3, 'bend': 10}), -0.06)


# ---------------------------------------------------------------- Божественное Табу (25 с)
# Планы: облёт вблизи -> снизу сбоку, взгляд вверх -> камера взлетает к печати -> печать издалека ->
# сверху, вращение -> облёт, взгляд поднимается. Молитва -> печать поднята над головой -> колено -> указ.
def taboo_cast():
    T = 25.0
    c = _shots(T)
    a, r = Anim('pohsmp_taboo_cast', T), Rig()
    _start(a)
    pray_r, pray_l = r.R(-0.5, 19.2, 5.0), r.L(0.5, 19.2, 5.0)
    a.pose(1.6, rightArm=pray_r, leftArm=pray_l, torso={'pitch': 6, 'yaw': 0, 'roll': 0, 'bend': 8},
           head={'pitch': 26, 'yaw': 0, 'roll': 0})
    a.sway(1.6, c[1], 2.0, 'torso', {'pitch': 6, 'yaw': 0, 'roll': 0, 'bend': 8}, 'pitch', 1.5)
    # сложенные руки медленно поднимаются над головой
    a.pose(c[1] + 1.4, rightArm=r.R(-0.6, 24.5, 6.5), leftArm=r.L(0.6, 24.5, 6.5),
           torso={'pitch': 0, 'yaw': 0, 'roll': 0, 'bend': 0}, head={'pitch': 0, 'yaw': 0, 'roll': 0})
    joined = _fk(pitch=-168, roll=-12, bend=-18)          # руки вверх, кисти сходятся над головой
    a.pose(c[2], rightArm=joined, leftArm=mirror(joined),
           torso={'pitch': -4, 'yaw': 0, 'roll': 0, 'bend': -5}, head={'pitch': -34, 'yaw': 0, 'roll': 0})
    # руки раскрываются V — держит печать на ладонях
    v_r, v_l = r.R(-9.5, 29.0, 2.0), r.L(9.5, 29.0, 2.0)
    a.pose(c[2] + 1.6, 'easeOutCubic', rightArm=v_r, leftArm=v_l, torso={'pitch': -6, 'yaw': 0, 'roll': 0, 'bend': -6},
           head={'pitch': -38, 'yaw': 0, 'roll': 0},
           rightLeg={'pitch': 0, 'yaw': 0, 'roll': 4, 'bend': 0}, leftLeg={'pitch': 0, 'yaw': 0, 'roll': -4, 'bend': 0})
    a.sway(c[2] + 1.6, c[4], 2.6, 'rightArm', v_r, 'roll', 3)
    a.sway(c[2] + 1.6, c[4], 2.6, 'leftArm', v_l, 'roll', -3)
    # сверху: опускается на колено, ладони вниз над землёй — освящает зону
    kneel_r_leg = {'pitch': 8, 'yaw': 0, 'roll': 2, 'bend': 92}
    kneel_l_leg = {'pitch': -84, 'yaw': 0, 'roll': -4, 'bend': 86}   # бедро почти горизонтально, голень вертикально
    bless_r, bless_l = r.R(-11.0, 16.5, 4.5), r.L(11.0, 16.5, 4.5)
    a.pose(c[4] + 1.2, 'easeOutCubic', rightLeg=kneel_r_leg, leftLeg=kneel_l_leg, body={'y': -0.34},
           rightArm=bless_r, leftArm=bless_l, torso={'pitch': 4, 'yaw': 0, 'roll': 0, 'bend': 4},
           head={'pitch': 16, 'yaw': 0, 'roll': 0})
    a.sway(c[4] + 1.2, c[5] + 0.4, 2.2, 'torso', {'pitch': 4, 'yaw': 0, 'roll': 0, 'bend': 4}, 'pitch', 2)
    # облёт: встаёт, правая рука вверх — указ; левая к груди
    a.pose(c[5] + 1.8, rightLeg=ZERO_LEG, leftLeg=ZERO_LEG, body={'y': 0},
           torso={'pitch': -2, 'yaw': 0, 'roll': 0, 'bend': -2}, head={'pitch': -12, 'yaw': 0, 'roll': 0},
           rightArm=r.R(-6.0, 19.0, 6.0), leftArm=r.L(1.5, 19.0, 4.8))
    decree_r, chest_l = _fk(pitch=-8, roll=168, bend=-4), r.L(1.5, 19.0, 4.8)   # рука вертикально вверх, чуть наружу
    a.pose(T - 0.6, 'easeOutBack', rightArm=decree_r, leftArm=chest_l,
           torso={'pitch': -5, 'yaw': 4, 'roll': 2, 'bend': -4}, head={'pitch': -28, 'yaw': 0, 'roll': 0})
    a.pose(T, rightArm=decree_r, leftArm=chest_l, torso={'pitch': -5, 'yaw': 4, 'roll': 2, 'bend': -4},
           head={'pitch': -28, 'yaw': 0, 'roll': 0})
    return a, (decree_r, chest_l, {'pitch': -5, 'yaw': 4, 'roll': 2, 'bend': -4}, None, 0.0)


# ---------------------------------------------------------------- Закрытие Пространства (20 с)
# Планы: облёт вблизи -> снизу, взгляд на печать Ковена -> камера уходит вверх и в сторону -> очень далеко ->
# сверху с поворотом -> приближение, взгляд вверх. Печать у лица -> руки вверх -> руки рисуют купол ->
# держит купол, медленно поворачиваясь -> хлопок, ладони вперёд: пространство закрыто.
def space_closure_cast():
    T = 20.0
    c = _shots(T)
    a, r = Anim('pohsmp_space_closure_cast', T), Rig()
    _start(a)
    seal_r, seal_l = r.R(-0.8, 24.6, 5.2), r.L(1.2, 18.6, 5.0)
    a.pose(1.4, rightArm=seal_r, leftArm=seal_l, torso={'pitch': 4, 'yaw': 0, 'roll': 0, 'bend': 4},
           head={'pitch': 14, 'yaw': 0, 'roll': 0})
    a.sway(1.4, c[1], 1.6, 'head', {'pitch': 14, 'yaw': 0, 'roll': 0}, 'pitch', 3)
    # руки вверх, ладонями к печати
    up_r = _fk(pitch=-20, roll=152, bend=-12)                 # руки вверх и в стороны, ладонями к печати
    up_l = mirror(up_r)
    a.pose(c[1] + 1.2, rightArm=up_r, leftArm=up_l, torso={'pitch': -6, 'yaw': 0, 'roll': 0, 'bend': -6},
           head={'pitch': -36, 'yaw': 0, 'roll': 0})
    a.sway(c[1] + 1.2, c[2], 1.4, 'torso', {'pitch': -6, 'yaw': 0, 'roll': 0, 'bend': -6}, 'pitch', 1.5)
    # руки широкой дугой через стороны вниз — рисует купол
    a.pose(c[2] + 1.0, rightArm=r.R(-13.0, 26.0, 3.0), leftArm=r.L(13.0, 26.0, 3.0),
           head={'pitch': -10, 'yaw': 0, 'roll': 0}, torso={'pitch': -2, 'yaw': 0, 'roll': 0, 'bend': -2})
    dome_r, dome_l = r.R(-11.5, 15.2, 2.5), r.L(11.5, 15.2, 2.5)
    a.pose(c[3], rightArm=dome_r, leftArm=dome_l, torso={'pitch': 2, 'yaw': 0, 'roll': 0, 'bend': 2},
           head={'pitch': 4, 'yaw': 0, 'roll': 0},
           rightLeg={'pitch': 0, 'yaw': 0, 'roll': 5, 'bend': 4}, leftLeg={'pitch': 0, 'yaw': 0, 'roll': -5, 'bend': 4})
    a.sway(c[3], c[4], 2.4, 'torso', {'pitch': 2, 'yaw': 0, 'roll': 0, 'bend': 2}, 'pitch', 1.2)
    # сверху: держит купол и медленно поворачивается
    a.pose(c[4] + 1.4, torso={'pitch': 2, 'yaw': -26, 'roll': 0, 'bend': 2}, head={'pitch': 4, 'yaw': -10, 'roll': 0})
    a.pose(c[5] - 0.2, torso={'pitch': 2, 'yaw': 24, 'roll': 0, 'bend': 2}, head={'pitch': 4, 'yaw': 10, 'roll': 0})
    # приближение: ладони сходятся у груди и резко толкаются вперёд — пространство закрыто
    a.pose(c[5] + 1.0, rightArm=r.R(-1.0, 19.0, 5.6), leftArm=r.L(1.0, 19.0, 5.6),
           torso={'pitch': 4, 'yaw': 0, 'roll': 0, 'bend': 4}, head={'pitch': 6, 'yaw': 0, 'roll': 0})
    a.sway(c[5] + 1.0, T - 0.8, 0.5, 'torso', {'pitch': 4, 'yaw': 0, 'roll': 0, 'bend': 4}, 'roll', 1.5)
    a.pose(T - 0.8, rightArm=r.R(-1.2, 19.4, 4.4), leftArm=r.L(1.2, 19.4, 4.4))
    push_r, push_l = r.R(-3.0, 21.0, 9.0), r.L(3.0, 21.0, 9.0)
    a.pose(T - 0.45, 'easeOutBack', rightArm=push_r, leftArm=push_l,
           torso={'pitch': 10, 'yaw': 0, 'roll': 0, 'bend': 6}, head={'pitch': 0, 'yaw': 0, 'roll': 0},
           rightLeg={'pitch': 10, 'yaw': 0, 'roll': 4, 'bend': 12}, leftLeg={'pitch': -12, 'yaw': 0, 'roll': -4, 'bend': 6})
    a.pose(T, rightArm=push_r, leftArm=push_l, torso={'pitch': 10, 'yaw': 0, 'roll': 0, 'bend': 6},
           head={'pitch': 0, 'yaw': 0, 'roll': 0},
           rightLeg={'pitch': 10, 'yaw': 0, 'roll': 4, 'bend': 12}, leftLeg={'pitch': -12, 'yaw': 0, 'roll': -4, 'bend': 6})
    return a, (push_r, push_l, {'pitch': 10, 'yaw': 0, 'roll': 0, 'bend': 6},
               ({'pitch': 10, 'yaw': 0, 'roll': 4, 'bend': 12}, {'pitch': -12, 'yaw': 0, 'roll': -4, 'bend': 6}), 0.0)


# ---------------------------------------------------------------- Появление Ковена (90 с)
# Задание: docs/specs/coven_arrival_spec.md. Без посоха (предметы в руках прячет HiddenHands).
# Все позы рук — углами суставов (без обратной кинематики): так переходы предсказуемы.
# Руки за спину убираются в два шага: сначала прямая рука разворачивается (у прямой руки разворот не виден),
# потом сгибается локоть; обратно — в обратном порядке.
#   0–8 с    пролог на арене: заклинатель стоит с закрытыми глазами (голова опущена), медленно дышит
#   8–16 с   у заклинателя: оборачивается к свите и кивает, правая рука чертит круг в воздухе, левая раскрывает портал
#   16–19 с  два шага назад в портал
#   19–38 с  невидим внутри портала на арене (портал формируется, выходит свита)
#   38–48 с  выходит: левая рука за спиной, правая свободно, медленный шаг; тело от -2.5 блока к 0
#   48–56 с  останавливается, оглядывает арену (голова влево, вправо), поправляет стойку
#   56–64 с  реплика: «Мы тоже примем участие» — ладонь вверх, рука раскрывается к арене;
#            «но для начала...» — пальцы сжимаются, рука опускается
#   64–69 с  титр: обе руки за спиной, подбородок вверх
#   69–80 с  ритуал: руки из-за спины в стороны, медленно вверх, дрожь силы
#   80–86 с  купол: руки дугой вниз и в стороны, толчок наружу, держит
#   86–90 с  руки опускаются, лёгкий кивок
COVEN_T = 90.0
COVEN_WALK_FROM = -2.5       # блоков назад от конечной точки (внутри портала)
COVEN_RITUAL_AT = 69.0       # когда свита начинает ритуал (pohsmp_coven_ritual)

CALM_R = _fk(roll=4, bend=-10)
TWIST_R = _fk(pitch=12, yaw=-150, roll=-8, bend=-4)          # прямая рука развёрнута назад-внутрь
BEHIND_R = _fk(pitch=14, yaw=-150, roll=-8, bend=-74)        # кисть за спиной
T_R = _fk(pitch=-5, roll=90, bend=-8)
V_R = _fk(pitch=-15, roll=150, bend=-12)
DOME_HI = _fk(pitch=-10, roll=115, bend=-8)
DOME_R = _fk(pitch=-12, roll=62, bend=-6)
PUSH_R = _fk(pitch=-30, roll=70, bend=-2)
HEAD0 = {'pitch': 0, 'yaw': 0, 'roll': 0}
TORSO0 = {'pitch': 0, 'yaw': 0, 'roll': 0, 'bend': 0}


def _behind(a, t, side, dur=1.2):
    """Убрать руку за спину: разворот прямой руки, затем сгиб."""
    tw, bh = (TWIST_R, BEHIND_R) if side == 'right' else (mirror(TWIST_R), mirror(BEHIND_R))
    part = side + 'Arm'
    a.key(t, part, **tw)
    a.key(t + dur * 0.55, part, **bh)


def _unbehind(a, t, side, to, dur=1.4):
    """Достать руку из-за спины: выпрямить, развернуть, поставить в позу to."""
    tw, bh = (TWIST_R, BEHIND_R) if side == 'right' else (mirror(TWIST_R), mirror(BEHIND_R))
    part = side + 'Arm'
    a.key(t, part, **bh)                                         # до t рука держится за спиной
    a.key(t + dur * 0.3, part, **tw)
    a.key(t + dur * 0.6, part, **merge(tw, {'yaw': 0, 'roll': to['roll'] * 0.3, 'pitch': 0}))
    a.key(t + dur, part, **to)


def _steps(a, t0, t1, step, body_from, body_to, swing_r=True):
    """Медленный шаг: ноги в противофазе, корпус чуть качается, тело переносится по z; правая рука качается, если swing_r."""
    n = max(1, int(round((t1 - t0) / step)))
    for i in range(n + 1):
        t = t0 + (t1 - t0) * i / n
        f = i / n
        side = 1 if i % 2 == 0 else -1
        last = i == n
        leg = 0 if last else 20
        a.pose(t, rightLeg={'pitch': -leg * side, 'yaw': 0, 'roll': 1, 'bend': 0 if last else (14 if side < 0 else 4)},
               leftLeg={'pitch': leg * side, 'yaw': 0, 'roll': -1, 'bend': 0 if last else (14 if side > 0 else 4)},
               body={'y': 0 if last else -0.02, 'z': body_from + (body_to - body_from) * f},
               torso={'pitch': 2, 'yaw': 0 if last else 3 * side, 'roll': 0, 'bend': 0})
        if swing_r:
            a.key(t, 'rightArm', **(CALM_R if last else _fk(pitch=12 * side, roll=4, bend=-12)))


def coven_arrival_cast():
    T = COVEN_T
    a = Anim('pohsmp_coven_arrival_cast', T)
    _start(a)
    a.pose(0, body={'y': 0, 'z': 0})
    # 0–8: стоит с закрытыми глазами, медленно дышит
    a.pose(1.5, rightArm=CALM_R, leftArm=mirror(CALM_R), head={'pitch': 16, 'yaw': 0, 'roll': 0})
    a.sway(1.5, 7.6, 2.6, 'torso', {'pitch': 2, 'yaw': 0, 'roll': 0, 'bend': 2}, 'pitch', 1.4)
    # 8–16: оборачивается к свите, кивает, чертит круг правой, раскрывает левой
    a.pose(8.8, head={'pitch': 2, 'yaw': -38, 'roll': 0}, torso={'pitch': 0, 'yaw': -10, 'roll': 0, 'bend': 0})
    a.pose(9.4, head={'pitch': 14, 'yaw': -38, 'roll': 0})
    a.pose(9.9, head={'pitch': 2, 'yaw': -34, 'roll': 0})
    a.pose(10.8, head={'pitch': -4, 'yaw': 8, 'roll': 0}, torso={'pitch': -1, 'yaw': 8, 'roll': 0, 'bend': 0},
           rightArm=_fk(pitch=-95, roll=20, bend=-22))
    a.pose(11.7, rightArm=_fk(pitch=-140, roll=55, bend=-15), head={'pitch': -12, 'yaw': 14, 'roll': 0})
    a.pose(12.6, rightArm=_fk(pitch=-105, roll=108, bend=-10), head={'pitch': -6, 'yaw': 22, 'roll': 0})
    a.pose(13.5, rightArm=_fk(pitch=-45, roll=95, bend=-10), head={'pitch': 0, 'yaw': 18, 'roll': 0})
    a.pose(14.3, 'easeOutCubic', leftArm=mirror(_fk(pitch=-62, roll=72, bend=-14)),
           rightArm=_fk(pitch=-62, roll=72, bend=-14), torso={'pitch': -3, 'yaw': 0, 'roll': 0, 'bend': -2},
           head={'pitch': -6, 'yaw': 0, 'roll': 0})
    a.pose(15.6, rightArm=_fk(pitch=-30, roll=40, bend=-12), leftArm=mirror(_fk(pitch=-30, roll=40, bend=-12)),
           torso=TORSO0, head=HEAD0)
    # 16–19: два шага назад в портал, руки чуть разведены
    a.pose(16.2, rightArm=_fk(pitch=8, roll=14, bend=-10), leftArm=mirror(_fk(pitch=8, roll=14, bend=-10)),
           rightLeg=ZERO_LEG, leftLeg=ZERO_LEG, body={'y': 0, 'z': 0})
    a.pose(17.0, rightLeg={'pitch': 20, 'yaw': 0, 'roll': 1, 'bend': 12}, body={'y': -0.02, 'z': -0.45})
    a.pose(17.8, rightLeg=ZERO_LEG, leftLeg={'pitch': 20, 'yaw': 0, 'roll': -1, 'bend': 12}, body={'y': -0.02, 'z': -0.95})
    a.pose(18.6, leftLeg=ZERO_LEG, body={'y': 0, 'z': -1.4})
    # 19–38: невидим в портале — нейтральная поза, тело стоит «внутри портала»
    a.pose(19.05, body={'y': 0, 'z': COVEN_WALK_FROM}, rightArm=CALM_R, leftArm=mirror(CALM_R))
    a.pose(37.0, rightArm=CALM_R, leftArm=mirror(CALM_R), head={'pitch': 6, 'yaw': 0, 'roll': 0}, torso=TORSO0,
           body={'y': 0, 'z': COVEN_WALK_FROM}, rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)
    # 38–48: выход — левая за спиной, правая свободно, медленный шаг
    _behind(a, 37.6, 'left')
    _steps(a, 38.4, 47.4, 0.95, COVEN_WALK_FROM, 0.0)
    a.pose(47.6, head={'pitch': -4, 'yaw': 0, 'roll': 0})
    # 48–56: оглядывает арену
    a.pose(49.6, head={'pitch': -2, 'yaw': -40, 'roll': 0}, torso={'pitch': 0, 'yaw': -8, 'roll': 0, 'bend': 0})
    a.pose(51.0, head={'pitch': -2, 'yaw': -40, 'roll': 0})
    a.pose(53.2, head={'pitch': -2, 'yaw': 38, 'roll': 0}, torso={'pitch': 0, 'yaw': 8, 'roll': 0, 'bend': 0})
    a.pose(54.6, head={'pitch': -2, 'yaw': 38, 'roll': 0})
    a.pose(55.8, head={'pitch': -6, 'yaw': 0, 'roll': 0}, torso={'pitch': -2, 'yaw': 0, 'roll': 0, 'bend': -1},
           rightLeg={'pitch': 0, 'yaw': 0, 'roll': 3, 'bend': 0}, leftLeg={'pitch': 0, 'yaw': 0, 'roll': -3, 'bend': 0})
    # 56–64: реплика
    present = _fk(pitch=-55, yaw=14, roll=8, bend=-42)          # ладонь вверх перед грудью
    reach = _fk(pitch=-72, yaw=4, roll=48, bend=-16)            # рука раскрывается к арене
    clench = _fk(pitch=-58, yaw=6, roll=26, bend=-62)           # «но для начала...» — сжимает
    a.pose(57.2, rightArm=present, head={'pitch': 0, 'yaw': -6, 'roll': -3}, torso={'pitch': -1, 'yaw': -5, 'roll': 0, 'bend': 0})
    a.pose(59.4, rightArm=reach, head={'pitch': -2, 'yaw': 10, 'roll': -2}, torso={'pitch': -1, 'yaw': 6, 'roll': 0, 'bend': 0})
    a.pose(60.6, rightArm=reach)
    a.pose(61.8, 'easeInOutCubic', rightArm=clench, head={'pitch': 6, 'yaw': 0, 'roll': 0}, torso={'pitch': 2, 'yaw': 0, 'roll': 0, 'bend': 1})
    a.pose(63.2, rightArm=_fk(pitch=-20, roll=10, bend=-30))
    # 64–69: титр — обе руки за спиной
    a.key(63.6, 'rightArm', **_fk(pitch=4, roll=4, bend=-6))
    _behind(a, 64.2, 'right')
    a.pose(65.4, head={'pitch': -8, 'yaw': 0, 'roll': 0}, torso={'pitch': -3, 'yaw': 0, 'roll': 0, 'bend': -2})
    a.sway(65.4, 68.4, 1.5, 'torso', {'pitch': -3, 'yaw': 0, 'roll': 0, 'bend': -2}, 'pitch', 0.8)
    # 69–80: ритуал
    _unbehind(a, 69.0, 'right', T_R, 1.8)
    _unbehind(a, 69.0, 'left', mirror(T_R), 1.8)
    a.pose(71.0, head={'pitch': -10, 'yaw': 0, 'roll': 0}, torso={'pitch': -1, 'yaw': 0, 'roll': 0, 'bend': -1},
           rightLeg={'pitch': 0, 'yaw': 0, 'roll': 5, 'bend': 0}, leftLeg={'pitch': 0, 'yaw': 0, 'roll': -5, 'bend': 0})
    a.pose(72.4, rightArm=T_R, leftArm=mirror(T_R))
    a.pose(76.4, rightArm=V_R, leftArm=mirror(V_R), head={'pitch': -32, 'yaw': 0, 'roll': 0},
           torso={'pitch': -6, 'yaw': 0, 'roll': 0, 'bend': -6})
    for i, t in enumerate([76.4 + 0.3 * k for k in range(12)]):          # дрожь силы
        j = 2.5 if i % 2 else -2.5
        a.key(t, 'rightArm', **merge(V_R, {'roll': V_R['roll'] + j}))
        a.key(t, 'leftArm', **mirror(merge(V_R, {'roll': V_R['roll'] - j})))
    a.pose(79.9, rightArm=V_R, leftArm=mirror(V_R))
    # 80–86: купол — дугой вниз и в стороны, толчок наружу
    a.pose(81.4, 'easeOutCubic', rightArm=DOME_HI, leftArm=mirror(DOME_HI), head={'pitch': -12, 'yaw': 0, 'roll': 0})
    a.pose(82.8, rightArm=DOME_R, leftArm=mirror(DOME_R), torso={'pitch': 1, 'yaw': 0, 'roll': 0, 'bend': 1},
           head={'pitch': 0, 'yaw': 0, 'roll': 0})
    a.pose(83.3, 'easeOutBack', rightArm=PUSH_R, leftArm=mirror(PUSH_R), torso={'pitch': 6, 'yaw': 0, 'roll': 0, 'bend': 4},
           rightLeg={'pitch': 8, 'yaw': 0, 'roll': 5, 'bend': 10}, leftLeg={'pitch': -10, 'yaw': 0, 'roll': -5, 'bend': 6})
    a.pose(85.6, rightArm=PUSH_R, leftArm=mirror(PUSH_R), torso={'pitch': 5, 'yaw': 0, 'roll': 0, 'bend': 3})
    # 86–90: руки опускаются, кивок
    a.pose(87.6, rightArm=CALM_R, leftArm=mirror(CALM_R), torso=TORSO0, head={'pitch': 10, 'yaw': 0, 'roll': 0},
           rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)
    a.pose(88.6, head={'pitch': -2, 'yaw': 0, 'roll': 0})
    a.pose(T, rightArm=CALM_R, leftArm=mirror(CALM_R), head={'pitch': -2, 'yaw': 0, 'roll': 0}, body={'y': 0, 'z': 0})
    return a, (CALM_R, mirror(CALM_R), None, None, 0.0)


def coven_ritual():
    """Поза ритуала для свиты-игроков: запускать в 69 с ролика (COVEN_RITUAL_AT), 19 с; та же хореография рук, что у заклинателя."""
    L = 19.0
    a = Anim('pohsmp_coven_ritual', L, hold=False)
    _start(a)
    a.pose(1.2, rightArm=_fk(pitch=-4, roll=40, bend=-8), leftArm=mirror(_fk(pitch=-4, roll=40, bend=-8)))
    a.pose(3.4, rightArm=T_R, leftArm=mirror(T_R), head={'pitch': -10, 'yaw': 0, 'roll': 0})
    a.pose(7.4, rightArm=V_R, leftArm=mirror(V_R), head={'pitch': -32, 'yaw': 0, 'roll': 0},
           torso={'pitch': -6, 'yaw': 0, 'roll': 0, 'bend': -6})
    a.pose(10.9, rightArm=V_R, leftArm=mirror(V_R))
    a.pose(12.4, 'easeOutCubic', rightArm=DOME_HI, leftArm=mirror(DOME_HI), head={'pitch': -12, 'yaw': 0, 'roll': 0})
    a.pose(13.8, rightArm=DOME_R, leftArm=mirror(DOME_R), torso={'pitch': 1, 'yaw': 0, 'roll': 0, 'bend': 1}, head=HEAD0)
    a.pose(14.3, 'easeOutBack', rightArm=PUSH_R, leftArm=mirror(PUSH_R), torso={'pitch': 6, 'yaw': 0, 'roll': 0, 'bend': 4})
    a.pose(16.6, rightArm=PUSH_R, leftArm=mirror(PUSH_R))
    a.pose(L, rightArm=ZERO_LEG, leftArm=ZERO_LEG, torso=ZERO_T, head=ZERO_H)
    return a


def _pair(fn, finish_name):
    """Анимация каста и финал из её последней позы."""
    def cast():
        return fn()[0]

    def fin():
        _, (fr, fl, torso, legs, by) = fn()
        return _finish(finish_name, fr, fl, torso=torso, legs=legs, body_y=by)
    return cast, fin


_MW = _pair(milky_way_cast, 'pohsmp_milky_way_finish')
_SD = _pair(soul_devour_cast, 'pohsmp_soul_devour_finish')
_TB = _pair(taboo_cast, 'pohsmp_taboo_finish')
_SC = _pair(space_closure_cast, 'pohsmp_space_closure_finish')
_CA = _pair(coven_arrival_cast, 'pohsmp_coven_arrival_finish')


ANIMS = [downfall_cast, downfall_finish, *_MW, *_SD, *_TB, *_SC, *_CA, coven_ritual]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    old = os.path.join(OUT_DIR, 'pohsmp_core_casting.json')
    if os.path.exists(old):
        os.remove(old)
    data = {}
    for f in ANIMS:
        a = f()
        js = a.emotecraft()
        with open(os.path.join(OUT_DIR, a.name + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(js, fh, ensure_ascii=False, indent=1)
        data[a.name] = js
        print('wrote', a.name, '-', len(js['emote']['moves']), 'keys')
    with open(os.path.join(HERE, 'anim_preview.template.html'), encoding='utf-8') as fh:
        page = fh.read().replace('/*ANIMS*/null', json.dumps(data, ensure_ascii=False))
    with open(os.path.join(HERE, 'anim_preview.html'), 'w', encoding='utf-8') as fh:
        fh.write(page)
    print('wrote tools/anim_preview.html')


if __name__ == '__main__':
    main()
