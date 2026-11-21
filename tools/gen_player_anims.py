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


def arm(side, hand, staff=None, elbow_out=1.0, fore=None, prev_u=None, free_twist=False):
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
        if staff is not None and free_twist:                      # посох докрутят в кисти: нужно лишь предплечье поперёк посоха
            score -= 8.0 * abs(float(np.dot(f, _n(staff))))
        elif staff is not None:
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
        self.loop_from = None                # hold: с какой секунды повторять (None — замереть в последней позе)
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
            ret = self.end if self.loop_from is None else int(round(self.loop_from * TPS))
            emote.update({'isLoop': True, 'returnTick': ret})
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

    def S(self, x, y, z, staff, search=3.0, **kw):
        """
        Правая рука с посохом: (углы руки, {'roll': докрутка посоха в кисти}) — для rightItem.
        Посох в кисти всегда поперёк предплечья, поэтому точное направление достижимо только при предплечье,
        перпендикулярном посоху: ищем хват в кубе ±search px вокруг (x, y, z), где это так, а остаток
        добираем поворотом посоха в кисти (полностью, без ограничения ITEM_FIX_MAX — жесты динамичные).
        """
        want = _n(staff)
        best = None
        steps = np.linspace(-search, search, 5) if search else [0.0]
        kw.setdefault('free_twist', True)
        for dx in steps:
            for dy in steps:
                for dz in steps:
                    h = (x + dx, y + dy, z + dz)
                    q, info = arm('right', h, staff, prev_u=self.u['right'], **kw)
                    err = math.degrees(math.asin(min(1.0, abs(float(np.dot(info['fore'], want))))))
                    score = err + 2.0 * math.sqrt(dx * dx + dy * dy + dz * dz)
                    if best is None or score < best[0]:
                        best = (score, q, info, h)
        _, q, info, _h = best
        self.u['right'] = info['u']
        self.hand = np.array(_h)
        return q, {'roll': info['twist']}


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
#   38–48 с  выходит: левая рука за спиной, правая свободно, медленный шаг; тело от портала (3 блока позади) вперёд к 0
#   48–56 с  останавливается, оглядывает арену (голова влево, вправо), поправляет стойку
#   56–64 с  реплика: «Мы тоже примем участие» — ладонь вверх, рука раскрывается к арене;
#            «но для начала...» — пальцы сжимаются, рука опускается
#   64–69 с  титр: обе руки за спиной, подбородок вверх
#   69–80 с  ритуал: руки из-за спины в стороны, медленно вверх, дрожь силы
#   80–86 с  купол: руки дугой вниз и в стороны, толчок наружу, держит
#   86–90 с  руки опускаются, лёгкий кивок
COVEN_T = 90.0
# В PlayerAnimator body.z < 0 — ВПЕРЁД по взгляду, > 0 — назад (вход в портал 16–19 с: z 0 → -1.4, шаги вперёд).
# Выход начинается позади конечной точки, у самого портала (сервер ставит заклинателя на 3.2 блока перед порталом),
# и идёт вперёд к 0. С -2.5 заклинатель появлялся впереди и пятился к точке спиной (владелец, 19.11).
COVEN_WALK_FROM = 3.0        # блоков назад от конечной точки (у плоскости портала)
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
    a.pose(19.05, body={'y': 0, 'z': -2.5}, rightArm=CALM_R, leftArm=mirror(CALM_R))   # ещё шаг вперёд, в портал
    a.pose(20.0, body={'y': 0, 'z': COVEN_WALK_FROM})   # уже скрыт (с 19 с): тело отводится к точке выхода у портала
    a.pose(35.0, rightArm=CALM_R, leftArm=mirror(CALM_R), head={'pitch': 6, 'yaw': 0, 'roll': 0}, torso=TORSO0,
           body={'y': 0, 'z': COVEN_WALK_FROM}, rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)
    # 38–48: выход — левая за спиной, правая свободно, медленный шаг.
    # Владелец 19.11: «при выходе из портала иногда ломается левая рука» — разворот руки за спину (yaw 0→150 со сгибом) шёл
    # в 37.6–38.3 с и при выходе в 38 с его было видно на полпути (рука вывернута). Теперь он целиком внутри портала (35.5–36.2 с),
    # к выходу рука уже спокойно за спиной.
    _behind(a, 35.5, 'left')
    a.key(37.0, 'leftArm', **mirror(BEHIND_R))
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


# ---------------------------------------------------------------- Дезинтеграция (10 с), канон «Слизи»
# Хината и Шуна кастуют её, сложив ладони в молитве у лица; на «Disintegration!» ладони толкаются вперёд.
#   0–1.5 с   ладони сходятся у подбородка, голова склоняется (глаза закрыты)
#   1.5–7 с   молитва: дыхание, лёгкое покачивание
#   7–9.4 с   голова поднимается (перед заклинателем встаёт печать), корпус чуть вперёд
#   9.4–9.8 с толчок ладонями вперёд — в 10 с удар
def disintegration_cast():
    T = 10.0
    a, r = Anim('pohsmp_disintegration_cast', T), Rig()
    _start(a)
    pray_r, pray_l = r.R(-0.55, 23.4, 4.6), r.L(0.55, 23.4, 4.6)
    a.pose(1.5, rightArm=pray_r, leftArm=pray_l, head={'pitch': 14, 'yaw': 0, 'roll': 0},
           torso={'pitch': 3, 'yaw': 0, 'roll': 0, 'bend': 4})
    a.sway(1.5, 7.0, 2.0, 'torso', {'pitch': 3, 'yaw': 0, 'roll': 0, 'bend': 4}, 'pitch', 1.2)
    a.pose(7.0, rightArm=r.R(-0.55, 23.0, 5.0), leftArm=r.L(0.55, 23.0, 5.0))
    a.pose(8.4, head={'pitch': -4, 'yaw': 0, 'roll': 0}, torso={'pitch': 5, 'yaw': 0, 'roll': 0, 'bend': 5},
           rightLeg={'pitch': 6, 'yaw': 0, 'roll': 3, 'bend': 6}, leftLeg={'pitch': -8, 'yaw': 0, 'roll': -3, 'bend': 4})
    a.pose(9.4, rightArm=r.R(-0.6, 22.2, 4.2), leftArm=r.L(0.6, 22.2, 4.2), head={'pitch': -2, 'yaw': 0, 'roll': 0})
    push_r, push_l = r.R(-1.6, 21.6, 9.0), r.L(1.6, 21.6, 9.0)
    a.pose(9.8, 'easeOutBack', rightArm=push_r, leftArm=push_l, torso={'pitch': 9, 'yaw': 0, 'roll': 0, 'bend': 6},
           head={'pitch': 0, 'yaw': 0, 'roll': 0})
    a.pose(T, rightArm=push_r, leftArm=push_l, torso={'pitch': 9, 'yaw': 0, 'roll': 0, 'bend': 6})
    return a, (push_r, push_l, {'pitch': 9, 'yaw': 0, 'roll': 0, 'bend': 6},
               ({'pitch': 6, 'yaw': 0, 'roll': 3, 'bend': 6}, {'pitch': -8, 'yaw': 0, 'roll': -3, 'bend': 4}), 0.0)


# ---------------------------------------------------------------- Врата (50 с, «Безмолвная ведьма»)
# По отрывку аниме: посох НЕ в руках — парит перед ведьмой (рисует код), руки свободны, жесты — правой рукой:
#   0–14   стоит спокойно, руки опущены, лёгкое дыхание, взгляд вперёд
#   14     указывает рукой вперёд-вверх (из руки к вратам тянутся потоки света — эффект), корпус чуть разворачивается
#   22     поднимает взгляд на врата, рука выше
#   26–38  рука опускается, смотрит вверх
#   38–42  палец к губам — «тсс», голова чуть опущена; ЛЕВОЙ рукой берёт посох (дальше он в левой руке, низко по диагонали) —
#          за спиной в это время складываются золотые круги и сферы (эффект)
#   49     палец вверх — команда; в момент удара (49.8–50) рука резко опускается и встаёт прямо вперёд; так она и держит её,
#          пока бьют лучи (финал 14 с: держит 12 с и опускает), посох всё ещё в левой
POINT_R = _fk(pitch=-100, yaw=8, roll=-6, bend=-4)
POINT_HI_R = _fk(pitch=-128, yaw=6, roll=-4, bend=-2)
SKY_R = _fk(pitch=-172, yaw=0, roll=-8, bend=-2)
FWD_R = _fk(pitch=-90, yaw=4, roll=-4, bend=0)          # рука прямо вперёд — момент удара
STAFF_L = Rig().L(2.0, 19.0, 6.0, elbow_out=1.4)      # после оборота (владелец 19.11, кадр аниме): левый кулак у груди почти по центру, посох наискось перед телом — навершие вниз-вправо, хвост за левое плечо; поднят, чтобы был в кадре крупного плана «тсс»


def silent_gate_cast():
    T = 49.6
    a, r = Anim('pohsmp_silent_gate_cast', T), Rig()
    _start(a)
    calm_t = {'pitch': 0, 'yaw': 0, 'roll': 0, 'bend': 0}
    a.sway(0.5, 13.4, 3.2, 'torso', calm_t, 'pitch', 1.0)
    a.pose(13.4, rightArm=ARM_DOWN_R, leftArm=ARM_DOWN_L, head={'pitch': 0, 'yaw': 0, 'roll': 0})
    # 14 — указ
    a.pose(14.6, 'easeOutBack', rightArm=POINT_R, leftArm=_fk(pitch=4, roll=-12, bend=-8),
           torso={'pitch': 2, 'yaw': -10, 'roll': 0, 'bend': 2}, head={'pitch': -6, 'yaw': -8, 'roll': 0})
    a.sway(14.6, 21.6, 1.8, 'rightArm', POINT_R, 'pitch', 2.5)
    # 22 — взгляд на врата
    a.pose(22.6, rightArm=POINT_HI_R, head={'pitch': -28, 'yaw': -4, 'roll': 0}, torso={'pitch': -3, 'yaw': -6, 'roll': 0, 'bend': 0})
    a.pose(25.8, rightArm=POINT_HI_R)
    # 26–38 — рука опускается, смотрит вверх
    a.pose(27.6, rightArm=ARM_DOWN_R, leftArm=ARM_DOWN_L, torso={'pitch': -2, 'yaw': 0, 'roll': 0, 'bend': 0},
           head={'pitch': -22, 'yaw': 0, 'roll': 0})
    a.sway(27.6, 37.6, 3.4, 'head', {'pitch': -22, 'yaw': 0, 'roll': 0}, 'yaw', 5)
    a.pose(37.6, rightArm=ARM_DOWN_R, leftArm=ARM_DOWN_L)
    # 38 — палец к губам
    lips = r.R(-0.4, 25.6, 4.4)
    a.pose(38.8, rightArm=lips, leftArm=STAFF_L, head={'pitch': 6, 'yaw': 0, 'roll': 0}, torso={'pitch': 3, 'yaw': 0, 'roll': 0, 'bend': 3})
    a.sway(38.8, 47.2, 2.2, 'leftArm', STAFF_L, 'pitch', 2)
    a.pose(47.2, rightArm=lips, head={'pitch': 2, 'yaw': 0, 'roll': 0})
    # 49 — палец вверх
    a.pose(48.4, rightArm=r.R(-1.0, 25.0, 3.0), head={'pitch': -14, 'yaw': 0, 'roll': 0})
    a.pose(49.1, 'easeOutBack', rightArm=SKY_R, head={'pitch': -24, 'yaw': 0, 'roll': 0}, torso={'pitch': -4, 'yaw': 0, 'roll': 0, 'bend': 0})
    a.pose(T, rightArm=SKY_R, leftArm=STAFF_L, head={'pitch': -24, 'yaw': 0, 'roll': 0}, torso={'pitch': -4, 'yaw': 0, 'roll': 0, 'bend': 0})
    return a, (SKY_R, STAFF_L, {'pitch': -4, 'yaw': 0, 'roll': 0, 'bend': 0}, None, 0.0)


def silent_gate_wait():
    """«Приказ» (владелец 19.11): врата готовы, ведьма держит палец вверх и ждёт ЛКМ — петля 3 с, лёгкое дыхание и покачивание кисти."""
    a = Anim('pohsmp_silent_gate_wait', 3.0, hold=True)
    head, torso = {'pitch': -24, 'yaw': 0, 'roll': 0}, {'pitch': -4, 'yaw': 0, 'roll': 0, 'bend': 0}
    a.pose(0, rightArm=SKY_R, leftArm=STAFF_L, head=head, torso=torso, body={'y': 0}, rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)
    a.sway(0, 3.0, 1.5, 'torso', torso, 'pitch', 1.2)
    a.sway(0, 3.0, 1.0, 'rightArm', SKY_R, 'roll', 2.5)
    a.sway(0, 3.0, 1.5, 'leftArm', STAFF_L, 'pitch', 1.5)
    return a


def silent_gate_command():
    """Приказ по ЛКМ: рука с пальцем вверх резко опускается и встаёт прямо вперёд (0.35 с), дальше — silent_gate_finish (удар)."""
    a = Anim('pohsmp_silent_gate_command', 0.5, hold=True)
    a.pose(0, rightArm=SKY_R, leftArm=STAFF_L, head={'pitch': -24, 'yaw': 0, 'roll': 0}, torso={'pitch': -4, 'yaw': 0, 'roll': 0, 'bend': 0},
           body={'y': 0}, rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)
    a.pose(0.35, 'easeInQuad', rightArm=FWD_R, head={'pitch': -4, 'yaw': 0, 'roll': 0}, torso={'pitch': 3, 'yaw': 0, 'roll': 0, 'bend': 2})
    a.pose(0.5, rightArm=FWD_R, leftArm=STAFF_L)
    return a


def silent_gate_finish():
    """После каста сцена идёт ещё 14 с (удар лучами): рука прямо вперёд, лёгкое покачивание, в конце опускается."""
    a = Anim('pohsmp_silent_gate_finish', 14.0, hold=False)
    a.pose(0, rightArm=FWD_R, leftArm=STAFF_L, torso={'pitch': 3, 'yaw': 0, 'roll': 0, 'bend': 2},
           head={'pitch': -4, 'yaw': 0, 'roll': 0}, body={'y': 0}, rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)
    a.sway(0, 11.6, 2.6, 'rightArm', FWD_R, 'yaw', 3)
    a.pose(11.6, leftArm=STAFF_L)
    a.pose(13.0, rightArm=ARM_DOWN_R, leftArm=ARM_DOWN_L, head={'pitch': -8, 'yaw': 0, 'roll': 0}, torso=ZERO_T)
    a.pose(14.0, rightArm=ZERO_LEG, leftArm=ZERO_LEG, head=ZERO_H)
    return a



# ---------------------------------------------------------------- Библиотека поз (T12)
# Именованные позы всего тела. Новое заклинание собирается списком шагов «поза → время → плавность»:
#   a = compose('pohsmp_x', 2.0, [('stand', 0), ('arms_sky', 0.6, 'easeOutBack'), ('palm_push', 1.4, 'easeInQuad')])
# Поза — словарь частей (rightArm, leftArm, torso, head, rightLeg, leftLeg, body); недостающие части берутся из 'stand'.
# Шаг может быть и словарём: {'pose': 'stance', 't': 1.0, 'ease': 'easeOutBack', 'sway': ('torso', 'pitch', 1.5, 2.0)} —
# sway: часть, канал, амплитуда, период — лёгкое покачивание до следующего шага.
_PR = Rig()
_HL = lambda **k: {'pitch': 0, 'yaw': 0, 'roll': 0, **k}
_TO = lambda **k: {'pitch': 0, 'yaw': 0, 'roll': 0, 'bend': 0, **k}
_STANCE_LEGS = dict(rightLeg=_TO(pitch=-10, roll=5, bend=12), leftLeg=_TO(pitch=12, roll=-5, bend=6))
SLASH_UP_R = _fk(pitch=-165, yaw=40, roll=-45, bend=-25)      # замах: кисть высоко справа над головой                      # замах: кисть над левым плечом
SLASH_DOWN_R = _fk(pitch=-50, yaw=30, roll=-60, bend=-8)      # конец взмаха: рука ушла наискось вниз-влево, через корпус
SNAP_UP_R = _fk(pitch=-78, yaw=6, roll=10, bend=-62)          # кисть у плеча, пальцы сложены для щелчка
SNAP_R = _fk(pitch=-96, yaw=4, roll=6, bend=-14)              # щелчок: рука выброшена вперёд
POSES = {
    'stand': dict(rightArm=ARM_DOWN_R, leftArm=ARM_DOWN_L, torso=ZERO_T, head=ZERO_H, rightLeg=ZERO_LEG, leftLeg=ZERO_LEG, body={'y': 0}),
    'prayer': dict(rightArm=_PR.R(-0.55, 23.4, 4.6), leftArm=_PR.L(0.55, 23.4, 4.6), head=_HL(pitch=14), torso=_TO(pitch=3, bend=4)),
    'staff_slam': dict(rightArm=_fk(pitch=-58, yaw=-8, roll=4, bend=-38), leftArm=_fk(pitch=-44, yaw=10, roll=-6, bend=-30),
                       torso=_TO(pitch=14, bend=8), head=_HL(pitch=8), body={'y': -0.12}, **_STANCE_LEGS),
    'arms_wide': dict(rightArm=T_R, leftArm=mirror(T_R), torso=_TO(pitch=-3), head=_HL(pitch=-6)),
    'arms_sky': dict(rightArm=V_R, leftArm=mirror(V_R), torso=_TO(pitch=-7, bend=-2), head=_HL(pitch=-32)),
    'slash_ready': dict(rightArm=SLASH_UP_R, leftArm=_fk(pitch=-20, roll=-14, bend=-30), torso=_TO(yaw=22, pitch=-2),
                        head=_HL(yaw=-10), **_STANCE_LEGS),
    'slash': dict(rightArm=SLASH_DOWN_R, leftArm=_fk(pitch=-6, roll=-22, bend=-20), torso=_TO(yaw=-24, pitch=8, bend=4),
                  head=_HL(yaw=12, pitch=4), **_STANCE_LEGS),
    'palm_push': dict(rightArm=_PR.R(-1.6, 21.6, 9.0), leftArm=_PR.L(1.6, 21.6, 9.0), torso=_TO(pitch=9, bend=6), head=_HL(),
                      rightLeg=_TO(pitch=6, roll=3, bend=6), leftLeg=_TO(pitch=-8, roll=-3, bend=4)),
    'bow': dict(rightArm=_PR.R(-0.9, 20.6, 3.8), leftArm=_fk(pitch=8, roll=-6, bend=-6), torso=_TO(pitch=32, bend=8), head=_HL(pitch=18)),
    'stance': dict(rightArm=_fk(pitch=-48, yaw=-6, roll=8, bend=-46), leftArm=_fk(pitch=-30, yaw=8, roll=-12, bend=-56),
                   torso=_TO(pitch=6, yaw=-14, bend=3), head=_HL(yaw=10), body={'y': -0.1}, **_STANCE_LEGS),
    'point': dict(rightArm=POINT_R, leftArm=_fk(pitch=4, roll=-12, bend=-8), torso=_TO(pitch=2, yaw=-10, bend=2), head=_HL(pitch=-6, yaw=-8)),
    'point_sky': dict(rightArm=SKY_R, torso=_TO(pitch=-4), head=_HL(pitch=-24)),
    'hush': dict(rightArm=_PR.R(-0.4, 25.6, 4.4), head=_HL(pitch=6), torso=_TO(pitch=3, bend=3)),
    'snap_ready': dict(rightArm=SNAP_UP_R, torso=_TO(yaw=-6), head=_HL(pitch=-2)),
    'snap': dict(rightArm=SNAP_R, torso=_TO(yaw=4, pitch=3), head=_HL()),
    'held': dict(rightArm=_fk(pitch=-12, roll=118, bend=-4), leftArm=mirror(_fk(pitch=-12, roll=118, bend=-4)),
                 torso=_TO(pitch=-12, bend=-6), head=_HL(pitch=-38), body={'y': 0.45},
                 rightLeg=_TO(pitch=8, roll=4, bend=14), leftLeg=_TO(pitch=-4, roll=-4, bend=8)),
}
POSE_NAMES = {'stand': 'стойка (спокойно)', 'prayer': 'молитва', 'staff_slam': 'удар посохом о землю', 'arms_wide': 'руки в стороны',
              'arms_sky': 'руки к небу', 'slash_ready': 'замах разреза', 'slash': 'взмах-разрез', 'palm_push': 'толчок ладонями',
              'bow': 'поклон', 'stance': 'боевая стойка', 'point': 'указ рукой', 'point_sky': 'палец к небу', 'hush': 'палец к губам',
              'snap_ready': 'щелчок: замах', 'snap': 'щелчок пальцами', 'held': 'скован (цель)'}


def pose(name, **over):
    """Поза из библиотеки (с частями 'stand' по умолчанию); over — заменить части."""
    return {**POSES['stand'], **POSES[name], **over}


def compose(anim_name, seconds, steps, hold=False):
    a = Anim(anim_name, seconds, hold=hold)
    steps = [s if isinstance(s, dict) else dict(zip(('pose', 't', 'ease'), s)) for s in steps]
    for i, st in enumerate(steps):
        p = st['pose'] if isinstance(st['pose'], dict) else pose(st['pose'])
        a.pose(st['t'], st.get('ease') or 'easeInOutSine', **p)
        if st.get('sway'):
            part, ch, amp, period = st['sway']
            t1 = steps[i + 1]['t'] if i + 1 < len(steps) else seconds
            a.sway(st['t'], t1, period, part, p[part], ch, amp)
    return a


def scarlet_cut_cast():
    """«Алый разрез» (T02): замах и 5 взмахов по одному в 4 тика (0.2 с), прямой и обратный по очереди; потом рука опускается."""
    st = [('stand', 0), ('slash_ready', 0.15, 'easeOutCubic')]
    t = 0.2
    for i in range(5):
        st.append(('slash' if i % 2 == 0 else 'slash_ready', t + 0.1, 'easeOutQuart'))
        t += 0.2
    st += [('stance', t + 0.3), ('stand', t + 0.9)]
    return compose('pohsmp_scarlet_cut_cast', t + 0.9, st)


def finger_snap():
    """Щелчок пальцами правой руки (T20, «Копья ветра» и др.): кисть к плечу — резкий выброс вперёд — опускается."""
    return compose('pohsmp_finger_snap', 1.1, [('stand', 0), ('snap_ready', 0.25, 'easeOutCubic'), ('snap', 0.38, 'easeOutBack'),
                                               ('snap', 0.7), ('stand', 1.1)])


def held_target():
    """Цель, которую держит Дезинтеграция/Реплика (T13): руки разведены и скованы, голова запрокинута, тело чуть парит;
    петля (hold) — играет, пока держат; дрожь и покачивание."""
    a = compose('pohsmp_held_target', 4.0, [('stand', 0), ('held', 0.8, 'easeOutCubic')], hold=True)
    h = pose('held')
    a.sway(0.8, 4.0, 0.8, 'rightArm', h['rightArm'], 'roll', 3)
    a.sway(0.8, 4.0, 0.9, 'leftArm', h['leftArm'], 'roll', -3)
    a.sway(0.8, 4.0, 2.0, 'head', h['head'], 'yaw', 6)
    a.sway(0.8, 4.0, 1.6, 'body', h['body'], 'y', 0.06)
    a.loop_from = 0.8   # петля — с 0.8 с (поза уже взята): дрожь и покачивание повторяются, пока держат
    return a


def cult_finisher_victim():
    """T26, добивание Главой Культа (2.4 с = анимация босса cult_leader_finisher): 0–0.7 жертву тянет к боссу (скована, как held),
    1.0 — пронзена косой: складывается пополам; 1.0–1.7 её поднимают (высоту даёт код), руки и ноги повисают; 1.7 — вспышка пламени:
    выгибается назад; 2.2 — обмякла (смерть). Без петли."""
    held = pose('held')
    pierce = pose('stand', rightArm=_fk(pitch=-28, roll=22, bend=-34), leftArm=mirror(_fk(pitch=-28, roll=22, bend=-34)),
                  torso=_TO(pitch=30, bend=14), head=_HL(pitch=34), body={'y': 0.45},
                  rightLeg=_TO(pitch=12, roll=3, bend=24), leftLeg=_TO(pitch=4, roll=-3, bend=30))
    hang = pose('stand', rightArm=_fk(pitch=8, roll=10, bend=-12), leftArm=mirror(_fk(pitch=8, roll=10, bend=-12)),
                torso=_TO(pitch=22, bend=10), head=_HL(pitch=42), body={'y': 0.45},
                rightLeg=_TO(pitch=6, roll=4, bend=18), leftLeg=_TO(pitch=-2, roll=-4, bend=22))
    arch = pose('stand', rightArm=_fk(pitch=-10, roll=70, bend=-20), leftArm=mirror(_fk(pitch=-10, roll=70, bend=-20)),
                torso=_TO(pitch=-14, bend=-6), head=_HL(pitch=-40), body={'y': 0.45},
                rightLeg=_TO(pitch=-6, roll=4, bend=10), leftLeg=_TO(pitch=-10, roll=-4, bend=14))
    return compose('pohsmp_cult_finisher_victim', 2.4, [
        {'pose': held, 't': 0}, {'pose': held, 't': 0.9}, {'pose': pierce, 't': 1.05, 'ease': 'easeOutQuart'},
        {'pose': hang, 't': 1.6}, {'pose': arch, 't': 1.8, 'ease': 'easeOutCubic'}, {'pose': hang, 't': 2.25, 'ease': 'easeInOutSine'}],
        hold=True)


def martin_finisher_victim():
    """T29, добивание Мартином (2.5 с = анимация босса martin_finisher; события impale 0.4, raise 0.8, throw 1.7, slam 2.0, kill 2.3).
    Высоту и место даёт код (MartinMath.finisherHold): 0–0.4 жертву тянет на выпад (скована), 0.4 — пронзена двуручником спереди:
    складывается; 0.8–1.7 висит на клинке над его головой, руки и ноги повисают; 1.7–2.0 сброшена ударом вниз — раскинуло;
    2.0 — удар о землю: рухнула на колени, корпус вперёд; 2.3 — смерть. Без петли."""
    held = pose('held')
    pierce = pose('stand', rightArm=_fk(pitch=-28, roll=22, bend=-34), leftArm=mirror(_fk(pitch=-28, roll=22, bend=-34)),
                  torso=_TO(pitch=30, bend=14), head=_HL(pitch=34), body={'y': 0.45},
                  rightLeg=_TO(pitch=12, roll=3, bend=24), leftLeg=_TO(pitch=4, roll=-3, bend=30))
    hang = pose('stand', rightArm=_fk(pitch=8, roll=10, bend=-12), leftArm=mirror(_fk(pitch=8, roll=10, bend=-12)),
                torso=_TO(pitch=22, bend=10), head=_HL(pitch=42), body={'y': 0.45},
                rightLeg=_TO(pitch=6, roll=4, bend=18), leftLeg=_TO(pitch=-2, roll=-4, bend=22))
    flung = pose('stand', rightArm=_fk(pitch=-60, roll=80, bend=-16), leftArm=mirror(_fk(pitch=-60, roll=80, bend=-16)),
                 torso=_TO(pitch=-12, bend=-4), head=_HL(pitch=-30), body={'y': 0.3},
                 rightLeg=_TO(pitch=-24, roll=6, bend=20), leftLeg=_TO(pitch=14, roll=-6, bend=26))
    slam = pose('stand', rightArm=_fk(pitch=-24, roll=14, bend=-20), leftArm=mirror(_fk(pitch=-24, roll=14, bend=-20)),
                torso=_TO(pitch=48, bend=18), head=_HL(pitch=36), body={'y': -0.36}, **KNEEL_LEGS)
    return compose('pohsmp_martin_finisher_victim', 2.5, [
        {'pose': held, 't': 0}, {'pose': held, 't': 0.32}, {'pose': pierce, 't': 0.45, 'ease': 'easeOutQuart'},
        {'pose': hang, 't': 1.0}, {'pose': hang, 't': 1.7}, {'pose': flung, 't': 1.85, 'ease': 'easeOutCubic'},
        {'pose': slam, 't': 2.02, 'ease': 'easeInQuad'}, {'pose': slam, 't': 2.5}], hold=True)


# ---------------------------------------------------------------- позы T05 и T20 (дополнение библиотеки)
# «Падение звезды» — без посоха (руки пустые, как у других заклинаний с роликом); жесты T20 — с посохом в правой руке
# (у этих поз есть rightItem — докрутка посоха в кисти, чтобы он смотрел куда нужно).
_SR = Rig()
AIM_R = _fk(pitch=-74, yaw=10, roll=-2, bend=-6)               # ладонь к точке на земле впереди, рука прямая
GATHER_L = _PR.L(1.2, 17.6, 4.6, elbow_out=1.6)                # левая кисть у груди собирает силу (локоть в сторону)
SKY_OPEN_R = _fk(pitch=-42, roll=146, bend=-10)                 # руки к небу широким V, ладони раскрыты
SKY_FLARE_R = _fk(pitch=-34, roll=128, bend=-4)                # вспышка звезды: руки распахиваются шире, корпус назад
GRAB_R = _fk(pitch=-158, yaw=-4, roll=14, bend=-18)            # хватает звезду: кисти почти сходятся над головой
PULL_MID_R = _PR.R(-8.5, 28.5, 5.5, elbow_out=1.6)             # тянет вниз: кулаки над головой по бокам, локти в стороны
PULL_LOW_R = _fk(pitch=-70, yaw=-8, roll=14, bend=-24)         # дотягивает: руки перед грудью вниз
SLAM_R = _fk(pitch=-38, yaw=-6, roll=8, bend=-6)               # удар: правая ладонь к земле (корпус наклонён — рука почти отвесно)
BRACE_L = _fk(pitch=42, yaw=-10, roll=-42, bend=-12)                    # левая — отведена назад-в сторону для равновесия
KNEEL_LEGS = dict(rightLeg=_TO(pitch=-78, roll=6, bend=82), leftLeg=_TO(pitch=6, roll=-6, bend=86))
CROUCH_LEGS = dict(rightLeg=_TO(pitch=-22, roll=6, bend=34), leftLeg=_TO(pitch=10, roll=-6, bend=22))

STAFF_REST = _SR.S(-6.4, 13.0, 4.6, (0.0, 0.25, 1.0), search=0, free_twist=False)        # посох в опущенной руке, навершием вперёд
STAFF_UP = _SR.S(-6.0, 27.0, 5.0, (0.08, 1.0, 0.12))          # посох поднят вертикально: кисть над плечом, предплечье поперёк
STAFF_BACK = _SR.S(-7.0, 27.0, 2.0, (0.1, 0.55, -0.83))       # замах: навершие за правым плечом, назад-вверх
STAFF_SWING = _SR.S(-4.0, 17.0, 6.0, (0.0, 0.08, 1.0))        # взмах: посох указывает вперёд, на врагов
STAFF_GUARD = _SR.S(-2.2, 19.0, 6.4, (0.0, 1.0, 0.0))         # посох вертикально перед собой
GUARD_L = _PR.L(*grip(_SR.hand, (0, 1, 0), 5.0), (0.0, 1.0, 0.0), elbow_out=1.4)   # левая берётся за древко над правой
STAFF_LIFT = _SR.S(-2.2, 23.0, 7.5, (0.0, 1.0, 0.0))          # приподнят перед ударом
LIFT_L = _PR.L(*grip(_SR.hand, (0, 1, 0), 5.0), (0.0, 1.0, 0.0), elbow_out=1.4)
STAFF_STRIKE = _SR.S(-2.4, 17.6, 7.0, (0.0, 1.0, 0.0), search=1.5)       # удар концом о землю (корпус и ноги опускают его ниже)
STRIKE_L = _PR.L(*grip(_SR.hand, (0, 1, 0), 5.0), (0.0, 1.0, 0.0), elbow_out=1.4)
STAFF_BOUNCE = _SR.S(-2.4, 18.6, 7.0, (0.0, 1.0, 0.0), search=1.5)       # отдача после удара
STAFF_LOW = _SR.S(-7.2, 12.4, 2.0, (-0.3, 0.28, -0.91))      # посох низко у правого бока, навершие назад-вверх (не мешает тени дракона)
PALM_BACK_L = _fk(pitch=38, yaw=-10, roll=-34, bend=-4)        # левая ладонь раскрыта за спину, низко
FAN_MID_L = _fk(pitch=30, yaw=-14, roll=-62, bend=-4)          # ведёт веер печатей вверх-в сторону
FAN_HI_L = _fk(pitch=14, yaw=-18, roll=-92, bend=-6)           # веер раскрыт: рука в сторону-назад на уровне плеча
DRAGON_POINT_L = mirror(_fk(pitch=-92, yaw=10, roll=-4, bend=-2))  # левая указывает вперёд (куда дохнёт тень)
DRAGON_AIM_L = mirror(_fk(pitch=-86, yaw=8, roll=-2, bend=-30))     # подтягивает руку перед выдохом
DRAGON_PUSH_L = mirror(_fk(pitch=-94, yaw=12, roll=-6, bend=0))     # выдох: ладонь вперёд
LEAN_L = _TO(roll=7, yaw=9, pitch=-1)                           # корпус отклонён влево (от тени над правым плечом)

POSES.update({
    'star_aim': dict(rightArm=AIM_R, leftArm=GATHER_L, torso=_TO(pitch=3, yaw=-12, bend=2), head=_HL(pitch=10, yaw=-6), **CROUCH_LEGS),
    'sky_open': dict(rightArm=SKY_OPEN_R, leftArm=mirror(SKY_OPEN_R), torso=_TO(pitch=-10, bend=-6), head=_HL(pitch=-40),
                     rightLeg=_TO(pitch=-6, roll=7, bend=6), leftLeg=_TO(pitch=6, roll=-7, bend=4)),
    'star_grab': dict(rightArm=GRAB_R, leftArm=mirror(GRAB_R), torso=_TO(pitch=-8, bend=-6), head=_HL(pitch=-36),
                      rightLeg=_TO(pitch=-6, roll=7, bend=6), leftLeg=_TO(pitch=6, roll=-7, bend=4)),
    'star_pull': dict(rightArm=PULL_LOW_R, leftArm=mirror(PULL_LOW_R), torso=_TO(pitch=16, bend=10), head=_HL(pitch=-10),
                      body={'y': -0.08}, **CROUCH_LEGS),
    'star_impact': dict(rightArm=SLAM_R, leftArm=BRACE_L, torso=_TO(pitch=32, yaw=-6, bend=10), head=_HL(pitch=-22, yaw=4),
                        body={'y': -0.36}, **KNEEL_LEGS),
    'staff_up': dict(rightArm=STAFF_UP[0], rightItem=STAFF_UP[1], leftArm=PALM_BACK_L, torso=_TO(pitch=-3, yaw=6), head=_HL(pitch=-8)),
    'staff_swing': dict(rightArm=STAFF_SWING[0], rightItem=STAFF_SWING[1], leftArm=_fk(pitch=22, roll=-40, bend=-10),
                        torso=_TO(pitch=8, yaw=-14, bend=4), head=_HL(yaw=10), **_STANCE_LEGS),
    'staff_guard': dict(rightArm=STAFF_GUARD[0], rightItem=STAFF_GUARD[1], leftArm=GUARD_L, torso=_TO(pitch=2), head=_HL(pitch=6)),
    'staff_strike': dict(rightArm=STAFF_STRIKE[0], rightItem=STAFF_STRIKE[1], leftArm=STRIKE_L, torso=_TO(pitch=2, bend=1),
                         head=_HL(pitch=12), body={'y': -0.24}, rightLeg=_TO(pitch=-30, roll=6, bend=46), leftLeg=_TO(pitch=12, roll=-6, bend=30)),
    'dragon_point': dict(rightArm=STAFF_LOW[0], rightItem=STAFF_LOW[1], leftArm=DRAGON_POINT_L, torso=LEAN_L, head=_HL(pitch=-2, yaw=6, roll=3),
                         rightLeg=_TO(pitch=8, roll=4, bend=4), leftLeg=_TO(pitch=-10, roll=-4, bend=8)),
})
POSE_NAMES.update({'star_aim': 'прицел: ладонь к точке, сила у груди', 'sky_open': 'руки к небу (печать)', 'star_grab': 'хватает звезду',
                   'star_pull': 'тянет звезду вниз', 'star_impact': 'удар: колено и ладонь к земле',
                   'staff_up': 'посох вверх, ладонь за спину', 'staff_swing': 'взмах посохом вперёд', 'staff_guard': 'посох вертикально',
                   'staff_strike': 'удар концом посоха о землю', 'dragon_point': 'указ левой, посох низко'})


# ---------------------------------------------------------------- Падение звезды (T05), 8 с = 160 тиков ровно
# Шкала эффекта fx/star_fall.json и ролика: 0–3.2 печать-прицел на земле; 3.2 звёздная печать в небе; 4.8 вспышка звезды;
# 5–8 звезда падает (easeInCubic); 8 — удар. Стиль властный: прямая рука-приказ, рывок вниз всем телом, удар на колено.
STAR_T = 8.0


def star_fall_cast():
    a = Anim('pohsmp_star_fall_cast', STAR_T)
    _start(a)
    P = {k: pose(k) for k in ('star_aim', 'sky_open', 'star_grab', 'star_pull', 'star_impact')}
    aim = P['star_aim']
    # 0–0.7 рука-приказ вскидывается к точке на земле, левая кисть идёт к груди, стойка шире
    a.pose(0.35, 'easeInQuad', rightArm=_fk(pitch=-40, yaw=6, roll=2, bend=-30), head=_HL(pitch=4, yaw=-4))
    a.pose(0.7, 'easeOutBack', rightArm=AIM_R, leftArm=GATHER_L, torso=aim['torso'], head=aim['head'],
           rightLeg=aim['rightLeg'], leftLeg=aim['leftLeg'], body={'y': -0.03})
    # 0.7–3.0 печать собирается по частям: три толчка ладонью (части печати встают), дрожь силы в левой
    for t in (1.25, 1.95, 2.65):
        a.pose(t - 0.12, rightArm=AIM_R, torso=aim['torso'])
        a.pose(t, 'easeOutCubic', rightArm=merge(AIM_R, {'pitch': AIM_R['pitch'] - 4, 'bend': 0}),
               torso=merge(aim['torso'], {'pitch': 5}))
        a.pose(t + 0.3, rightArm=AIM_R, torso=aim['torso'])
    a.sway(0.7, 2.9, 0.22, 'leftArm', GATHER_L, 'roll', 2.5)
    a.sway(0.7, 2.9, 1.1, 'head', aim['head'], 'pitch', 2)
    # 2.9–3.2 вдох: обе руки на миг опускаются к груди, голова вниз — набирает силу
    a.pose(3.05, 'easeInOutQuad', rightArm=_PR.R(-1.4, 18.4, 4.4), leftArm=_PR.L(1.4, 18.4, 4.4),
           torso=_TO(pitch=8, bend=6), head=_HL(pitch=22), body={'y': -0.06})
    # 3.2 звёздная печать раскрывается в небе: руки и взгляд вверх рывком, корпус прогибается
    sky = P['sky_open']
    a.pose(3.5, 'easeOutBack', rightArm=SKY_OPEN_R, leftArm=mirror(SKY_OPEN_R), torso=sky['torso'], head=sky['head'],
           rightLeg=sky['rightLeg'], leftLeg=sky['leftLeg'], body={'y': 0.02})
    a.sway(3.5, 4.55, 0.18, 'rightArm', SKY_OPEN_R, 'roll', 2)
    a.sway(3.5, 4.55, 0.2, 'leftArm', mirror(SKY_OPEN_R), 'roll', -2)
    # 4.8 вспышка звезды: руки распахиваются, голова откидывается
    a.pose(4.68, rightArm=merge(SKY_OPEN_R, {'roll': 156}), leftArm=mirror(merge(SKY_OPEN_R, {'roll': 156})),
           head=_HL(pitch=-42), torso=sky['torso'])
    a.pose(4.85, 'easeOutCubic', rightArm=SKY_FLARE_R, leftArm=mirror(SKY_FLARE_R), head=_HL(pitch=-48),
           torso=_TO(pitch=-14, bend=-8))
    # 5.0–5.3 хватает звезду: кисти сходятся над головой
    grab = P['star_grab']
    a.pose(5.3, 'easeOutBack', rightArm=GRAB_R, leftArm=mirror(GRAB_R), torso=grab['torso'], head=grab['head'])
    # 5.3–8 тянет вниз — ускоряется вместе со звездой (easeInCubic); корпус наклоняется, ноги сгибаются
    a.pose(6.5, 'easeInQuad', rightArm=PULL_MID_R, leftArm=mirror(PULL_MID_R), torso=_TO(pitch=4, bend=2),
           head=_HL(pitch=-26), rightLeg=_TO(pitch=-12, roll=7, bend=16), leftLeg=_TO(pitch=8, roll=-7, bend=10),
           body={'y': -0.03})
    pull = P['star_pull']
    a.pose(7.45, 'easeInCubic', rightArm=PULL_LOW_R, leftArm=mirror(PULL_LOW_R), torso=pull['torso'], head=pull['head'],
           rightLeg=pull['rightLeg'], leftLeg=pull['leftLeg'], body=pull['body'])
    # 7.45–8 последний рывок: на колено, правая ладонь в землю — удар ровно на 8 с
    imp = P['star_impact']
    a.pose(7.75, 'easeInQuad', rightArm=_fk(pitch=-58, yaw=-6, roll=10, bend=-20), leftArm=_fk(pitch=-30, roll=-40, bend=-30),
           torso=_TO(pitch=24, yaw=-4, bend=10), head=_HL(pitch=-16))
    a.pose(STAR_T, 'easeOutCubic', **{k: imp[k] for k in ('rightArm', 'leftArm', 'torso', 'head', 'rightLeg', 'leftLeg', 'body')})
    return a


def star_fall_finish():
    """После удара (1.5 с): держит упор, пока бьёт волна, потом встаёт и опускает руки, глядя на кратер."""
    a = Anim('pohsmp_star_fall_finish', 1.5, hold=False)
    imp = pose('star_impact')
    a.pose(0, **{k: imp[k] for k in ('rightArm', 'leftArm', 'torso', 'head', 'rightLeg', 'leftLeg', 'body')})
    a.pose(0.12, 'easeOutCubic', torso=merge(imp['torso'], {'pitch': 36}), body={'y': -0.38})   # отдача волны
    a.pose(0.45, rightArm=SLAM_R, leftArm=BRACE_L, torso=imp['torso'], head=_HL(pitch=-14, yaw=2))
    a.pose(1.0, 'easeInOutQuad', rightArm=_fk(pitch=-14, roll=6, bend=-12), leftArm=_fk(pitch=4, roll=-12, bend=-10),
           torso=_TO(pitch=10, bend=4), head=_HL(pitch=14), body={'y': -0.1}, **CROUCH_LEGS)
    a.pose(1.5, rightArm=ARM_DOWN_R, leftArm=ARM_DOWN_L, torso=ZERO_T, head=_HL(pitch=6), body={'y': 0},
           rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)
    return a


# ---------------------------------------------------------------- жесты посоха T20 (посох в правой руке)
def _staff_start(a):
    _start(a)
    a.pose(0, rightArm=STAFF_REST[0], rightItem=STAFF_REST[1])


def silent_volley_cast():
    """«Безмолвный залп», каст 3 с (VOLLEY_CAST 60 тиков): посох вверх, левая ладонь за спину — веер печатей встаёт
    за 80 % каста (2.4 с); замах и взмах посохом вперёд ровно к концу каста — стрелы вылетают."""
    T = 3.0
    a = Anim('pohsmp_silent_volley_cast', T)
    _staff_start(a)
    up = pose('staff_up')
    a.pose(0.45, 'easeOutBack', rightArm=STAFF_UP[0], rightItem=STAFF_UP[1], torso=up['torso'], head=up['head'])
    a.pose(0.6, 'easeOutCubic', leftArm=PALM_BACK_L, rightLeg=_TO(pitch=-6, roll=5, bend=6), leftLeg=_TO(pitch=8, roll=-5, bend=4))
    # левая ведёт веер: от низа за спиной вверх и в сторону; корпус чуть раскрывается влево, взгляд вскользь назад
    a.pose(1.4, leftArm=FAN_MID_L, torso=_TO(pitch=-4, yaw=10, roll=2), head=_HL(pitch=-6, yaw=14))
    a.pose(2.3, leftArm=FAN_HI_L, torso=_TO(pitch=-5, yaw=8, roll=3), head=_HL(pitch=-4, yaw=6))
    a.sway(0.45, 2.3, 0.9, 'rightArm', STAFF_UP[0], 'pitch', 2)
    a.pose(2.4, rightItem=STAFF_UP[1])                         # посох держится, пока встают печати
    # 2.4–2.72 замах за плечо (корпус закручивается вправо), 2.72–2.95 взмах вперёд — к 3.0 посох смотрит на врагов
    a.pose(2.72, 'easeOutQuad', rightArm=STAFF_BACK[0], rightItem=STAFF_BACK[1], torso=_TO(pitch=-6, yaw=20, bend=-3),
           head=_HL(yaw=-6), leftArm=FAN_HI_L)
    sw = pose('staff_swing')
    a.pose(2.95, 'easeInQuad', rightArm=STAFF_SWING[0], rightItem=STAFF_SWING[1], torso=sw['torso'], head=sw['head'],
           leftArm=sw['leftArm'], rightLeg=sw['rightLeg'], leftLeg=sw['leftLeg'])
    a.pose(T, rightArm=STAFF_SWING[0], rightItem=STAFF_SWING[1])
    return a


def silent_volley_finish():
    """0.9 с: посох задерживается вперёд, пока летят стрелы, и опускается."""
    a = Anim('pohsmp_silent_volley_finish', 0.9, hold=False)
    sw = pose('staff_swing')
    a.pose(0, **{k: sw[k] for k in ('rightArm', 'rightItem', 'leftArm', 'torso', 'head', 'rightLeg', 'leftLeg')}, body={'y': 0})
    a.pose(0.3, rightArm=STAFF_SWING[0], torso=merge(sw['torso'], {'pitch': 6}))
    a.pose(0.9, rightArm=STAFF_REST[0], rightItem=STAFF_REST[1], leftArm=ARM_DOWN_L, torso=ZERO_T, head=ZERO_H,
           rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)
    return a


def sage_barrier_cast():
    """«Барьер», каст 1.5 с (BARRIER_CAST 30 тиков): посох вертикально перед собой, вторая рука на древке, приподнять —
    удар концом о землю на 1.2 с, к 1.5 купол встаёт."""
    T = 1.5
    a = Anim('pohsmp_sage_barrier_cast', T)
    _staff_start(a)
    g = pose('staff_guard')
    a.pose(0.4, 'easeOutCubic', rightArm=STAFF_GUARD[0], rightItem=STAFF_GUARD[1], leftArm=GUARD_L, torso=g['torso'], head=g['head'])
    a.pose(0.9, 'easeInOutSine', rightArm=STAFF_LIFT[0], rightItem=STAFF_LIFT[1], leftArm=LIFT_L, torso=_TO(pitch=-3, bend=-2),
           head=_HL(pitch=-2), body={'y': 0.03})
    s = pose('staff_strike')
    a.pose(1.12, 'easeInQuad', rightArm=STAFF_STRIKE[0], rightItem=STAFF_STRIKE[1], leftArm=STRIKE_L, torso=s['torso'],
           head=s['head'], body=s['body'], rightLeg=s['rightLeg'], leftLeg=s['leftLeg'])
    # отдача: посох чуть подпрыгивает, и снова прижат
    a.pose(1.25, 'easeOutQuad', rightArm=STAFF_BOUNCE[0], rightItem=STAFF_BOUNCE[1], torso=merge(s['torso'], {'pitch': 6}))
    a.pose(T, rightArm=STAFF_STRIKE[0], rightItem=STAFF_STRIKE[1], leftArm=STRIKE_L, torso=s['torso'], body=s['body'])
    return a


def sage_barrier_finish():
    """1.0 с: держит посох у земли, пока купол собирается, выпрямляется, левая рука отпускает древко."""
    a = Anim('pohsmp_sage_barrier_finish', 1.0, hold=False)
    s = pose('staff_strike')
    a.pose(0, **{k: s[k] for k in ('rightArm', 'rightItem', 'leftArm', 'torso', 'head', 'body', 'rightLeg', 'leftLeg')})
    a.pose(0.35, head=_HL(pitch=-14), torso=_TO(pitch=4, bend=2))
    a.pose(0.6, rightArm=STAFF_GUARD[0], rightItem=STAFF_GUARD[1], leftArm=_fk(pitch=-6, roll=-10, bend=-12), body={'y': 0},
           torso=ZERO_T, rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)
    a.pose(1.0, rightArm=STAFF_REST[0], rightItem=STAFF_REST[1], leftArm=ARM_DOWN_L, head=ZERO_H)
    return a


def worgan_flame_cast():
    """«Чёрное пламя Ворганы», каст 2 с (FLAME_CAST 40 тиков): левая указывает вперёд, посох уходит низко к правому боку,
    над правым плечом встаёт тень дракона — корпус отклоняется влево; перед выдохом рука подтягивается."""
    T = 2.0
    a = Anim('pohsmp_worgan_flame_cast', T)
    _staff_start(a)
    d = pose('dragon_point')
    a.pose(0.3, 'easeInQuad', leftArm=mirror(_fk(pitch=-50, roll=-4, bend=-40)), head=_HL(pitch=-2, yaw=4))
    a.pose(0.6, 'easeOutBack', leftArm=DRAGON_POINT_L, rightArm=STAFF_LOW[0], rightItem=STAFF_LOW[1],
           torso=_TO(roll=3, yaw=8), head=d['head'], rightLeg=d['rightLeg'], leftLeg=d['leftLeg'])
    # тень дракона поднимается — заклинатель всё сильнее отклоняется от неё, взгляд мельком на неё (вправо-вверх) и снова вперёд
    a.pose(1.2, torso=_TO(roll=5, yaw=9, pitch=-2), head=_HL(pitch=-14, yaw=-22, roll=2))
    a.pose(1.6, torso=LEAN_L, head=d['head'])
    a.sway(0.6, 1.7, 0.3, 'leftArm', DRAGON_POINT_L, 'pitch', 1.5)
    a.pose(1.7, leftArm=DRAGON_POINT_L)
    a.pose(T, 'easeInOutQuad', leftArm=DRAGON_AIM_L, torso=merge(LEAN_L, {'pitch': 2}), head=_HL(pitch=2, yaw=6, roll=3))
    return a


def worgan_flame_finish():
    """3.5 с: выдох 3 с (FLAME_BREATH 60 тиков) — ладонь вперёд, корпус держит отдачу, лёгкая дрожь; потом рука опускается."""
    a = Anim('pohsmp_worgan_flame_finish', 3.5, hold=False)
    d = pose('dragon_point')
    a.pose(0, rightArm=STAFF_LOW[0], rightItem=STAFF_LOW[1], leftArm=DRAGON_AIM_L, torso=merge(LEAN_L, {'pitch': 2}),
           head=_HL(pitch=2, yaw=6, roll=3), rightLeg=d['rightLeg'], leftLeg=d['leftLeg'], body={'y': 0})
    push_torso = _TO(roll=8, yaw=10, pitch=-5, bend=-2)
    a.pose(0.18, 'easeOutBack', leftArm=DRAGON_PUSH_L, torso=push_torso, head=_HL(pitch=-2, yaw=6, roll=4))
    a.sway(0.18, 2.9, 0.16, 'leftArm', DRAGON_PUSH_L, 'yaw', -1.5)
    a.sway(0.18, 2.9, 1.0, 'torso', push_torso, 'pitch', 1.5)
    a.pose(3.0, leftArm=DRAGON_PUSH_L, torso=LEAN_L)
    a.pose(3.5, rightArm=STAFF_REST[0], rightItem=STAFF_REST[1], leftArm=ARM_DOWN_L, torso=ZERO_T, head=ZERO_H,
           rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)
    return a


# ---------------------------------------------------------------- T21: Печать души и Благословение (10 с = 200 тиков ровно)
# Шкала — docs/specs/tasks/T21_soul_seal_blessing.md и эффекты fx/soul_seal_cast.json, fx/blessing_cast.json (tools/gen_divine_t21.py).
# Без посоха: предмет в руках прячет клиент (как у других божественных с полной анимацией).
T21_T = 10.0
SEAL_PALM_R = _fk(pitch=-88, yaw=4, roll=-2, bend=-4)          # ладонь к цели: рука прямо вперёд на уровне плеча
SEAL_FIST_R = _fk(pitch=-84, yaw=4, roll=-2, bend=-16)         # пальцы сжимаются в кулак
SEAL_PULL_R = _fk(pitch=-70, yaw=8, roll=6, bend=-50)          # тянет цепи к себе: кулак идёт к груди
SEAL_WIND_R = _fk(pitch=-62, yaw=10, roll=10, bend=-72)        # замах перед рывком
SEAL_LOCK_R = _fk(pitch=-97, yaw=-6, roll=-12, bend=-4)        # рывок «запереть»: кулак вперёд с поворотом, как ключ в замке
SEAL_BACK_L = _fk(pitch=22, yaw=-6, roll=-26, bend=-14)        # левая отброшена назад-в сторону для равновесия
SEAL_LEGS = dict(rightLeg=_TO(pitch=-8, roll=4, bend=8), leftLeg=_TO(pitch=10, roll=-4, bend=4))


def soul_seal_cast():
    """«Печать души» (T21), 10 с: 0–2 руки собирают свет у груди; 2–6 ладонь к цели (над ней собирается замок), левая держит
    свет у груди; 6–9 пальцы сжимаются, кулак медленно тянет цепи к себе; 9.5 — рывок «запереть» (замок вдавливается в грудь цели)."""
    a, r = Anim('pohsmp_soul_seal_cast', T21_T), Rig()
    _start(a)
    orb_r, orb_l = r.R(-2.4, 17.6, 6.2), r.L(2.4, 17.6, 6.2)      # ладони друг к другу, между ними свет
    a.pose(0.9, rightArm=orb_r, leftArm=orb_l, torso=_TO(pitch=4, bend=5), head=_HL(pitch=16), **SEAL_LEGS)
    a.sway(0.9, 1.9, 0.5, 'rightArm', orb_r, 'roll', 2)
    a.sway(0.9, 1.9, 0.55, 'leftArm', orb_l, 'roll', -2)
    chest_l = r.L(1.6, 18.2, 5.4, elbow_out=1.5)
    a.pose(1.95, 'easeInQuad', rightArm=_fk(pitch=-60, yaw=4, roll=2, bend=-36), head=_HL(pitch=2))
    a.pose(2.4, 'easeOutBack', rightArm=SEAL_PALM_R, leftArm=chest_l, torso=_TO(pitch=2, yaw=-8, bend=2), head=_HL(pitch=-6, yaw=6))
    a.sway(2.4, 6.0, 0.45, 'rightArm', SEAL_PALM_R, 'pitch', 1.2)          # ладонь дрожит от силы
    a.sway(2.4, 6.0, 1.6, 'head', _HL(pitch=-6, yaw=6), 'pitch', -3)       # взгляд поднимается к замку над целью
    a.sway(2.4, 6.0, 0.6, 'leftArm', chest_l, 'roll', -2)
    a.pose(6.45, 'easeOutCubic', rightArm=SEAL_FIST_R, torso=_TO(pitch=3, yaw=-9, bend=3), head=_HL(pitch=-2, yaw=6))
    a.pose(9.0, 'easeInOutSine', rightArm=SEAL_PULL_R, torso=_TO(pitch=-4, yaw=-12, bend=-2), head=_HL(pitch=0, yaw=8))
    a.sway(6.45, 9.0, 0.22, 'rightArm', SEAL_PULL_R, 'yaw', 1.5)            # кулак дрожит, цепи сопротивляются
    a.pose(9.42, 'easeInOutQuad', rightArm=SEAL_WIND_R, leftArm=r.L(2.4, 17.0, 4.6, elbow_out=1.5),
           torso=_TO(pitch=-6, yaw=-16, bend=-3), head=_HL(pitch=2, yaw=10))
    lock_t = _TO(pitch=8, yaw=6, bend=5)
    a.pose(9.62, 'easeOutBack', rightArm=SEAL_LOCK_R, leftArm=SEAL_BACK_L, torso=lock_t, head=_HL(pitch=4, yaw=-2),
           rightLeg=_TO(pitch=-14, roll=4, bend=14), leftLeg=_TO(pitch=14, roll=-4, bend=6), body={'y': -0.05})
    a.pose(T21_T, rightArm=SEAL_LOCK_R, leftArm=SEAL_BACK_L, torso=lock_t)
    return a, (SEAL_LOCK_R, SEAL_BACK_L, lock_t, (_TO(pitch=-14, roll=4, bend=14), _TO(pitch=14, roll=-4, bend=6)), -0.05)


BLESS_SKY_R = _fk(pitch=-36, roll=132, bend=-10)               # ладони к небу широким V


def blessing_cast():
    """«Благословение» (T21), 10 с: 0–6 молитвенно сложенные руки у лица (голова склонена, к 5 с поднимается);
    6–8.8 руки раскрываются ладонями к цели (свет опускается на неё); 8.8–9.5 ладони поднимаются к небу — вспышка в 9.5."""
    a, r = Anim('pohsmp_blessing_cast', T21_T), Rig()
    _start(a)
    pray_r, pray_l = r.R(-0.55, 23.0, 6.0), r.L(0.55, 23.0, 6.0)   # ладони у подбородка, чуть впереди лица
    pray_t = _TO(pitch=3, bend=4)
    a.pose(1.4, rightArm=pray_r, leftArm=pray_l, head=_HL(pitch=10), torso=pray_t)
    a.sway(1.4, 4.6, 2.0, 'torso', pray_t, 'pitch', 1.2)
    hi_r, hi_l = r.R(-0.55, 24.4, 6.4), r.L(0.55, 24.4, 6.4)       # ладони чуть поднимаются, голова встаёт
    a.pose(5.6, rightArm=hi_r, leftArm=hi_l, head=_HL(pitch=-4), torso=_TO(pitch=0, bend=1))
    open_r, open_l = r.R(-5.0, 19.8, 8.6, elbow_out=1.3), r.L(5.0, 19.8, 8.6, elbow_out=1.3)
    open_t = _TO(pitch=4, bend=3)
    a.pose(6.0, rightArm=r.R(-1.8, 23.0, 7.4), leftArm=r.L(1.8, 23.0, 7.4))
    a.pose(6.9, 'easeOutCubic', rightArm=open_r, leftArm=open_l, torso=open_t, head=_HL(pitch=-2),
           rightLeg=_TO(pitch=-6, roll=3, bend=5), leftLeg=_TO(pitch=8, roll=-3, bend=3))
    a.sway(6.9, 8.8, 1.0, 'rightArm', open_r, 'pitch', 2)
    a.sway(6.9, 8.8, 1.1, 'leftArm', open_l, 'pitch', 2)
    a.pose(9.45, 'easeInOutCubic', rightArm=BLESS_SKY_R, leftArm=mirror(BLESS_SKY_R), torso=_TO(pitch=-6, bend=-4),
           head=_HL(pitch=-30), body={'y': 0.02})
    a.pose(T21_T, rightArm=BLESS_SKY_R, leftArm=mirror(BLESS_SKY_R), torso=_TO(pitch=-7, bend=-5), head=_HL(pitch=-32))
    return a, (BLESS_SKY_R, mirror(BLESS_SKY_R), _TO(pitch=-7, bend=-5), (_TO(pitch=-6, roll=3, bend=5), _TO(pitch=8, roll=-3, bend=3)), 0.02)



# ---------------------------------------------------------------- T22: школа «Иллюзии»
# Шкалы — docs/specs/tasks/T22_illusion_school.md и эффекты fx/illusion_*.json (tools/gen_illusion_fx.py). Без посоха (предмет прячет клиент).
# Короткие касты (0.5–1.2 с) кончаются в стойке (hold=False); Высшие (4 / 3.5 с) и «Сон бабочки» (12 с = 240 тиков) замирают
# в последней позе (hold), к ним — финалы *_finish.
def _end_stand(a, t):
    a.pose(t, rightArm=ARM_DOWN_R, leftArm=ARM_DOWN_L, torso=ZERO_T, head=ZERO_H, body={'y': 0}, rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)


def illusion_mirror_images_cast():
    """«Отражения», 1.0 с: правая ладонь проводит перед лицом слева направо, как по зеркалу (0.15–0.5),
    затем руки чуть в стороны ладонями наружу — копии разбегаются (0.6 = 12 тик эффекта), и в стойку."""
    a, r = Anim('pohsmp_illusion_mirror_images_cast', 1.0, hold=False), Rig()
    _start(a)
    a.pose(0.18, 'easeOutCubic', rightArm=r.R(1.0, 24.4, 10.4), leftArm=_fk(pitch=-8, roll=-10, bend=-12), torso=_TO(yaw=8), head=_HL(yaw=6))
    a.pose(0.5, 'easeInOutSine', rightArm=r.R(-9.5, 24.0, 8.6, elbow_out=1.3), torso=_TO(yaw=-10, pitch=1), head=_HL(yaw=-10))
    out_r = _fk(pitch=-28, yaw=-10, roll=42, bend=-14)
    a.pose(0.66, 'easeOutBack', rightArm=out_r, leftArm=mirror(out_r), torso=_TO(pitch=-3), head=_HL(pitch=-4))
    a.pose(0.8, rightArm=out_r, leftArm=mirror(out_r))
    _end_stand(a, 1.0)
    return a


def illusion_false_step_cast():
    """«Ложный шаг», 0.5 с: короткий рывок — корпус вперёд, руки отброшены назад, выпад; сразу в стойку."""
    a = Anim('pohsmp_illusion_false_step_cast', 0.5, hold=False)
    _start(a)
    back = _fk(pitch=38, yaw=4, roll=14, bend=-8)
    a.pose(0.12, 'easeOutCubic', rightArm=back, leftArm=mirror(back), torso=_TO(pitch=18, bend=6), head=_HL(pitch=-12),
           rightLeg=_TO(pitch=-24, bend=16), leftLeg=_TO(pitch=20, bend=6), body={'y': -0.08})
    a.pose(0.28, rightArm=back, leftArm=mirror(back), torso=_TO(pitch=14, bend=5), head=_HL(pitch=-10))
    _end_stand(a, 0.5)
    return a


def illusion_veil_cast():
    """«Пелена», 1.2 с: ладони скрещиваются перед грудью (0.3), разводятся в стороны ладонями вниз — «задёргивает занавес» (0.7),
    лёгкое колыхание, в стойку."""
    a, r = Anim('pohsmp_illusion_veil_cast', 1.2, hold=False), Rig()
    _start(a)
    a.pose(0.3, 'easeOutCubic', rightArm=r.R(1.4, 19.5, 8.8, elbow_out=1.4), leftArm=r.L(-1.4, 18.0, 8.2, elbow_out=1.4),
           torso=_TO(pitch=4, bend=4), head=_HL(pitch=8))
    wide_r, wide_l = r.R(-12.5, 19.5, 4.5), r.L(12.5, 19.5, 4.5)
    a.pose(0.7, 'easeOutCubic', rightArm=wide_r, leftArm=wide_l, torso=_TO(pitch=-2), head=_HL(pitch=-2))
    a.sway(0.7, 1.0, 0.15, 'rightArm', wide_r, 'pitch', 3)
    a.sway(0.7, 1.0, 0.15, 'leftArm', wide_l, 'pitch', 3)
    _end_stand(a, 1.2)
    return a


def illusion_phantom_pain_cast():
    """«Фантомная боль», 0.8 с: кисть к груди (0.2), выброс ладони к цели (0.4), поворот кисти «закручивает» боль (0.55), в стойку."""
    a, r = Anim('pohsmp_illusion_phantom_pain_cast', 0.8, hold=False), Rig()
    _start(a)
    a.pose(0.2, 'easeOutCubic', rightArm=r.R(-1.6, 19.0, 6.4, elbow_out=1.3), torso=_TO(yaw=-8), head=_HL(yaw=-4))
    palm = _fk(pitch=-90, yaw=4, roll=-4, bend=-6)
    a.pose(0.4, 'easeOutBack', rightArm=palm, leftArm=_fk(pitch=10, roll=-14, bend=-10), torso=_TO(yaw=-12, pitch=3), head=_HL(yaw=6))
    a.pose(0.56, 'easeInOutQuad', rightArm=_fk(pitch=-86, yaw=-6, roll=-38, bend=-22), torso=_TO(yaw=-10, pitch=3))
    a.pose(0.62, rightArm=_fk(pitch=-86, yaw=-6, roll=-38, bend=-22))
    _end_stand(a, 0.8)
    return a


def illusion_borrowed_face():
    """«Чужое лицо» (жест, 0.9 с): ладонь проводит по лицу сверху вниз — ото лба к подбородку (не касаясь, в ладони перед лицом),
    голова чуть отворачивается и возвращается — на 0.4 с (8 тик) облик сменился; рука опускается."""
    a, r = Anim('pohsmp_illusion_borrowed_face', 0.9, hold=False), Rig()
    _start(a)
    a.pose(0.07, 'easeInQuad', rightArm=r.R(-3.4, 21.0, 9.6, elbow_out=1.2))
    a.pose(0.18, 'easeOutCubic', rightArm=r.R(-2.6, 31.0, 9.4, elbow_out=1.2), head=_HL(pitch=4, yaw=10), torso=_TO(pitch=2))
    a.pose(0.42, 'easeInOutSine', rightArm=r.R(-2.4, 26.6, 10.2, elbow_out=1.2), head=_HL(pitch=6, yaw=6))
    a.pose(0.58, 'easeInOutSine', rightArm=r.R(-3.0, 22.4, 10.0, elbow_out=1.2), head=_HL(pitch=-2, yaw=-8), torso=_TO(yaw=-4))
    a.pose(0.7, head=_HL(pitch=-2, yaw=-8))
    _end_stand(a, 0.9)
    return a


LAB_T = 4.0
LAB_SLAM_R = _fk(pitch=-42, yaw=-14, roll=12, bend=-16)          # ладони вниз к земле перед собой
LAB_LEGS = dict(rightLeg=_TO(pitch=-30, roll=6, bend=40), leftLeg=_TO(pitch=12, roll=-6, bend=28))


def illusion_labyrinth_cast():
    """«Зеркальный лабиринт» (Высшее), 4 с: 0–0.4 руки к груди; 0.4–2.4 правая ладонь чертит перед собой квадрат (стенки растут),
    левая держит око у груди; 2.4–3.2 обе руки вверх; 3.2–3.75 ладони резко вниз — присед, удар ладонями к земле (76 тик — вспышка,
    волна до r14); держит упор до 4.0."""
    a, r = Anim('pohsmp_illusion_labyrinth_cast', LAB_T), Rig()
    _start(a)
    chest_l = r.L(1.6, 18.6, 6.4, elbow_out=1.4)
    a.pose(0.4, 'easeOutCubic', rightArm=r.R(1.0, 24.0, 10.6), leftArm=chest_l, torso=_TO(pitch=2), head=_HL(pitch=2))
    sq = [(-8.0, 24.0, 10.0), (-8.0, 16.0, 10.0), (1.0, 16.0, 10.6), (1.0, 24.0, 10.6)]   # квадрат перед собой, по часовой
    for k, p in enumerate(sq):
        a.pose(0.4 + 0.5 * (k + 1), 'linear', rightArm=r.R(*p, elbow_out=1.3), head=_HL(pitch=2 if p[1] > 20 else 10, yaw=-6 if p[0] < -3 else 2),
               torso=_TO(yaw=-6 if p[0] < -3 else 2, pitch=2))
    a.sway(0.4, 2.4, 0.5, 'leftArm', chest_l, 'roll', -2)
    up_r = _fk(pitch=-24, yaw=0, roll=142, bend=-10)              # руки вверх буквой V (как V_R)
    a.pose(3.1, 'easeInOutQuad', rightArm=up_r, leftArm=mirror(up_r), torso=_TO(pitch=-8, bend=-4), head=_HL(pitch=-24), body={'y': 0.02})
    a.pose(3.2, rightArm=merge(up_r, {'roll': 150}), leftArm=mirror(merge(up_r, {'roll': 150})), torso=_TO(pitch=-9, bend=-5))
    a.pose(3.75, 'easeInCubic', rightArm=LAB_SLAM_R, leftArm=mirror(LAB_SLAM_R), torso=_TO(pitch=34, bend=12), head=_HL(pitch=-20),
           body={'y': -0.32}, **LAB_LEGS)
    a.pose(LAB_T, rightArm=LAB_SLAM_R, leftArm=mirror(LAB_SLAM_R), torso=_TO(pitch=32, bend=12), head=_HL(pitch=-18), body={'y': -0.3}, **LAB_LEGS)
    return a, (LAB_SLAM_R, mirror(LAB_SLAM_R), _TO(pitch=32, bend=12), (LAB_LEGS['rightLeg'], LAB_LEGS['leftLeg']), -0.3)


NM_T = 3.5
NM_CLAW_R = _fk(pitch=-84, yaw=6, roll=-8, bend=-34)             # рука-коготь к цели, пальцы согнуты
NM_GRIP_R = _fk(pitch=-80, yaw=8, roll=-14, bend=-58)            # сжимает: кулак-коготь
NM_RIP_R = _fk(pitch=-60, yaw=24, roll=22, bend=-70)              # рывок к себе
NM_OFF_L = _fk(pitch=24, yaw=-8, roll=-34, bend=-20)              # левая отброшена от лица


def illusion_nightmare_cast():
    """«Кошмар наяву» (Высшее), 3.5 с: левая ладонь закрывает свои глаза, правая — коготь к цели (0.4); дрожь, пальцы медленно
    сжимаются (до 3.0); 3.15–3.3 левая резко отнимается от лица, голова вскидывается, правая рвёт к себе (66 тик — печать над целью
    вспыхивает)."""
    a, r = Anim('pohsmp_illusion_nightmare_cast', NM_T), Rig()
    _start(a)
    a.pose(0.18, 'easeInQuad', leftArm=r.L(2.4, 23.0, 10.6, elbow_out=1.4))   # кисть идёт вперёд, потом вверх — мимо лица
    eyes_l = r.L(0.4, 27.6, 9.4, elbow_out=1.4)                     # ладонь перед глазами (лицо — до z = 4)
    a.pose(0.4, 'easeOutCubic', rightArm=NM_CLAW_R, leftArm=eyes_l, torso=_TO(pitch=6, yaw=-6, bend=4), head=_HL(pitch=14, yaw=4),
           rightLeg=_TO(pitch=-8, roll=4, bend=8), leftLeg=_TO(pitch=10, roll=-4, bend=4))
    a.sway(0.4, 3.0, 0.14, 'rightArm', NM_CLAW_R, 'yaw', 1.6)
    a.pose(3.0, 'easeInOutSine', rightArm=NM_GRIP_R, torso=_TO(pitch=9, yaw=-8, bend=6), head=_HL(pitch=18, yaw=4))
    a.sway(0.4, 3.0, 1.1, 'head', _HL(pitch=14, yaw=4), 'roll', 3)
    rip_t = _TO(pitch=-6, yaw=-16, bend=-4)
    a.pose(3.3, 'easeOutBack', rightArm=NM_RIP_R, leftArm=NM_OFF_L, torso=rip_t, head=_HL(pitch=-10, yaw=8))
    a.pose(NM_T, rightArm=NM_RIP_R, leftArm=NM_OFF_L, torso=rip_t, head=_HL(pitch=-8, yaw=8))
    return a, (NM_RIP_R, NM_OFF_L, rip_t, (_TO(pitch=-8, roll=4, bend=8), _TO(pitch=10, roll=-4, bend=4)), 0.0)


BD_T = 12.0
BD_OPEN_R = _fk(pitch=-30, yaw=-8, roll=78, bend=-10)            # руки раскрыты в стороны ладонями вверх (10–12 с)
BD_SKY_R = _fk(pitch=-14, yaw=0, roll=148, bend=-10)           # руки над головой (переворот мира)


def illusion_butterfly_cast():
    """«Сон бабочки» (Мифическое), 12 с = 240 тиков ровно (планы ролика — ТЗ T22, «Ролик»):
    0–2 ладони лодочкой у груди, взгляд вниз (в них рождается бабочка); 2–4 ладони поднимаются к лицу и над головой, раскрываются —
    бабочка улетает, взгляд за ней; 4–6 правая ладонь касается невидимого зеркала перед собой (4.3 с — трещина), отдёргивается и
    снова кладётся; 6–8 обе ладони на «зеркале», давит, корпус вперёд, дрожь; 8–10 руки взмывают над головой, корпус прогибается —
    мир переворачивается (9 с вспышка); 10–12 руки медленно раскрываются в стороны ладонями вверх, тело чуть приподнято — спокойно."""
    a, r = Anim('pohsmp_illusion_butterfly_cast', BD_T), Rig()
    _start(a)
    cup_r, cup_l = r.R(-1.3, 18.2, 6.8, elbow_out=1.3), r.L(1.3, 18.2, 6.8, elbow_out=1.3)
    cup_t = _TO(pitch=5, bend=5)
    a.pose(0.8, rightArm=cup_r, leftArm=cup_l, torso=cup_t, head=_HL(pitch=22))
    a.sway(0.8, 2.0, 0.6, 'torso', cup_t, 'pitch', 1)
    a.sway(0.8, 2.0, 0.5, 'rightArm', cup_r, 'roll', 2)
    a.sway(0.8, 2.0, 0.55, 'leftArm', cup_l, 'roll', -2)
    face_r, face_l = r.R(-2.0, 24.2, 10.2, elbow_out=1.3), r.L(2.0, 24.2, 10.2, elbow_out=1.3)
    a.pose(2.6, 'easeInOutSine', rightArm=face_r, leftArm=face_l, torso=_TO(pitch=0), head=_HL(pitch=-4))
    rel_r = _fk(pitch=-30, yaw=0, roll=138, bend=-10)
    a.pose(3.3, 'easeOutCubic', rightArm=rel_r, leftArm=mirror(rel_r), torso=_TO(pitch=-8, bend=-4), head=_HL(pitch=-30), body={'y': 0.02})
    a.pose(3.9, 'easeInOutSine', rightArm=_fk(pitch=-60, yaw=-4, roll=40, bend=-14), leftArm=mirror(_fk(pitch=-50, yaw=-4, roll=44, bend=-14)),
           torso=_TO(pitch=-3), head=_HL(pitch=-18, yaw=-6), body={'y': 0})
    touch_r = r.R(-3.2, 22.4, 10.2)                                    # ладонь на «зеркале» (≈0.65 бл. перед грудью)
    a.pose(4.3, 'easeOutCubic', rightArm=touch_r, leftArm=_fk(pitch=6, roll=-12, bend=-10), torso=_TO(pitch=3, yaw=-4), head=_HL(pitch=2, yaw=-2))
    a.pose(4.45, 'easeOutQuad', rightArm=r.R(-3.4, 22.0, 8.2), torso=_TO(pitch=0, yaw=-4), head=_HL(pitch=0, yaw=4))   # отдёрнул: звон
    a.pose(5.2, 'easeInOutSine', rightArm=r.R(-3.2, 22.4, 10.0), torso=_TO(pitch=3, yaw=-4), head=_HL(pitch=4))
    push_r, push_l = r.R(-3.4, 22.2, 10.2), r.L(3.4, 22.2, 10.2)
    push_t = _TO(pitch=10, bend=6)
    push_legs = dict(rightLeg=_TO(pitch=-14, roll=4, bend=12), leftLeg=_TO(pitch=16, roll=-4, bend=6))
    a.pose(6.2, 'easeInOutSine', rightArm=push_r, leftArm=push_l, torso=push_t, head=_HL(pitch=6), body={'y': -0.04}, **push_legs)
    a.sway(6.2, 7.9, 0.16, 'rightArm', push_r, 'pitch', 1.4)
    a.sway(6.2, 7.9, 0.17, 'leftArm', push_l, 'pitch', 1.4)
    a.pose(7.9, 'easeInOutSine', torso=merge(push_t, {'pitch': 13}), head=_HL(pitch=8))
    a.pose(8.6, 'easeInOutCubic', rightArm=BD_SKY_R, leftArm=mirror(BD_SKY_R), torso=_TO(pitch=-8, bend=-5), head=_HL(pitch=-26),
           body={'y': 0.04}, rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)
    a.sway(8.6, 9.0, 0.2, 'rightArm', BD_SKY_R, 'roll', 3)
    a.pose(9.05, 'easeOutBack', rightArm=merge(BD_SKY_R, {'roll': 162}), leftArm=mirror(merge(BD_SKY_R, {'roll': 162})),
           torso=_TO(pitch=-9, bend=-6), head=_HL(pitch=-26), body={'y': 0.06})
    a.pose(10.0, 'easeInOutSine', rightArm=merge(BD_SKY_R, {'roll': 156}), leftArm=mirror(merge(BD_SKY_R, {'roll': 156})),
           torso=_TO(pitch=-7, bend=-4), head=_HL(pitch=-24), body={'y': 0.08})
    open_t = _TO(pitch=-4, bend=-2)
    a.pose(11.2, 'easeInOutSine', rightArm=BD_OPEN_R, leftArm=mirror(BD_OPEN_R), torso=open_t, head=_HL(pitch=-8), body={'y': 0.1})
    a.sway(11.2, 11.8, 0.6, 'body', {'y': 0.1}, 'y', 0.02)
    a.pose(BD_T, rightArm=BD_OPEN_R, leftArm=mirror(BD_OPEN_R), torso=open_t, head=_HL(pitch=-6), body={'y': 0.1})
    return a, (BD_OPEN_R, mirror(BD_OPEN_R), open_t, (ZERO_LEG, ZERO_LEG), 0.1)


def illusion_butterfly_wake():
    """«Сон бабочки», пробуждение (0.8 с; код играет у заклинателя в момент финала, если он жив): хлопок ладонями перед грудью
    (0.25 — бабочки рассыпаются, вспышка), ладони расходятся, в стойку."""
    a, r = Anim('pohsmp_illusion_butterfly_wake', 0.8, hold=False), Rig()
    _start(a)
    a.pose(0.14, 'easeOutCubic', rightArm=r.R(-4.6, 22.6, 8.8), leftArm=r.L(4.6, 22.6, 8.8), torso=_TO(pitch=-2), head=_HL(pitch=-4))
    a.pose(0.25, 'easeInQuad', rightArm=r.R(-1.1, 21.6, 9.6), leftArm=r.L(1.1, 21.6, 9.6), torso=_TO(pitch=4, bend=3), head=_HL(pitch=2))
    a.pose(0.42, 'easeOutCubic', rightArm=r.R(-6.0, 20.8, 7.4), leftArm=r.L(6.0, 20.8, 7.4), torso=_TO(pitch=0), head=_HL(pitch=-2))
    _end_stand(a, 0.8)
    return a


def _t22_finish(fn, name, length, head):
    def fin():
        _, (fr, fl, torso, legs, by) = fn()
        return _finish(name, fr, fl, torso=torso, head=head, legs=legs, body_y=by, length=length)
    return fin


_T22 = [illusion_mirror_images_cast, illusion_false_step_cast, illusion_veil_cast, illusion_phantom_pain_cast, illusion_borrowed_face,
        lambda: illusion_labyrinth_cast()[0], _t22_finish(illusion_labyrinth_cast, 'pohsmp_illusion_labyrinth_finish', 1.2, _HL(pitch=-18)),
        lambda: illusion_nightmare_cast()[0], _t22_finish(illusion_nightmare_cast, 'pohsmp_illusion_nightmare_finish', 1.0, _HL(pitch=-8, yaw=8)),
        lambda: illusion_butterfly_cast()[0], _t22_finish(illusion_butterfly_cast, 'pohsmp_illusion_butterfly_finish', 1.5, _HL(pitch=-6)),
        illusion_butterfly_wake]


# ---------------------------------------------------------------- T24: «Стёртое имя» (Запретная, «Мироздание»), 15 с = 300 тиков ровно
# Шкала — docs/specs/tasks/T24_erased_name.md (раздел «Ролик») и fx/erased_name_cast.json (tools/gen_forbidden_fx.py).
# Левая ладонь держит невидимую «книгу имён» у груди, правая — «перо»: пишет имя в воздухе, вычёркивает его (6 с), стирает
# ладонью строки (7–11.5 с), заносит руку (12–14 с), замирает в тишине (14.0–14.45) и последним росчерком рассекает воздух (14.5 с).
EN_T = 15.0
EN_POINT_R = _fk(pitch=-92, yaw=2, roll=-2, bend=-6)            # рука к цели
EN_SWEEP_END_R = _fk(pitch=-80, yaw=10, roll=46, bend=-6)       # конец первого росчерка: рука ушла вправо-вперёд
EN_PALM_R = _fk(pitch=-84, yaw=4, roll=8, bend=-8)              # ладонь вниз перед собой
EN_LEGS = dict(rightLeg=_TO(pitch=-10, roll=5, bend=10), leftLeg=_TO(pitch=12, roll=-5, bend=6))


def erased_name_cast():
    a, r = Anim('pohsmp_erased_name_cast', EN_T), Rig()
    _start(a)
    book_l = r.L(2.6, 16.8, 6.4, elbow_out=1.4)                  # левая ладонь вверх у груди — «книга»
    a.pose(0.9, 'easeInOutSine', rightArm=r.R(-2.2, 18.4, 6.2, elbow_out=1.3), leftArm=book_l, torso=_TO(pitch=4, bend=4),
           head=_HL(pitch=18))                                    # смотрит в «книгу»
    a.pose(1.55, 'easeOutCubic', rightArm=EN_POINT_R, torso=_TO(pitch=1, yaw=-4, bend=1), head=_HL(pitch=-2, yaw=4), **EN_LEGS)
    # 1.6–3.4 с: пишет имя в воздухе слева направо, мелкими дугами
    t, k = 1.7, 0
    while t < 3.4:
        prog = (t - 1.7) / 1.7
        a.pose(t, 'easeInOutSine', rightArm=_fk(pitch=-95 if k % 2 == 0 else -87, yaw=2, roll=-10 + 26 * prog, bend=-8 - 4 * (k % 2)),
               head=_HL(pitch=-3, yaw=4 - 6 * prog))
        t += 0.17
        k += 1
    a.sway(1.55, 5.6, 0.7, 'leftArm', book_l, 'roll', -2)
    # 3.4–5.6: рука уходит к левому плечу — замах
    wind_r = r.R(2.6, 20.4, 5.6, elbow_out=1.4)
    a.pose(4.6, 'easeInOutCubic', rightArm=wind_r, torso=_TO(pitch=-1, yaw=-16, bend=-1), head=_HL(pitch=-2, yaw=12))
    a.sway(4.6, 5.55, 0.3, 'rightArm', wind_r, 'pitch', 1.5)
    # 5.6–6.15: росчерк слева направо — черта по имени (fx: 114–123 тик)
    a.pose(5.85, 'easeInQuad', rightArm=_fk(pitch=-92, yaw=0, roll=4, bend=-10), torso=_TO(pitch=2, yaw=0, bend=2), head=_HL(pitch=-2, yaw=2))
    a.pose(6.1, 'easeOutCubic', rightArm=EN_SWEEP_END_R, torso=_TO(pitch=3, yaw=16, bend=2), head=_HL(pitch=-2, yaw=-10))
    a.pose(6.35, rightArm=EN_SWEEP_END_R)
    # 7–11.5: ладонь вниз, медленно стирает строки — два проведения
    a.pose(7.0, 'easeInOutSine', rightArm=EN_PALM_R, torso=_TO(pitch=3, yaw=2, bend=2), head=_HL(pitch=0, yaw=-2))
    for tt, roll, ty in ((8.4, -22, -8), (9.8, 30, 8), (11.2, -12, -4)):
        a.pose(tt, 'easeInOutSine', rightArm=_fk(pitch=-82, yaw=4, roll=roll, bend=-8), torso=_TO(pitch=3, yaw=ty, bend=2), head=_HL(pitch=0, yaw=-ty * 0.6))
    # 11.5–13.6: рука взлетает высоко вправо — замах; левая отпускает «книгу» вниз-в сторону
    up_t = _TO(yaw=22, pitch=-3)
    a.pose(13.2, 'easeInOutCubic', rightArm=SLASH_UP_R, leftArm=_fk(pitch=-20, roll=-14, bend=-30), torso=up_t, head=_HL(yaw=-14, pitch=-4),
           body={'y': 0.02})
    a.sway(13.2, 13.95, 0.12, 'rightArm', SLASH_UP_R, 'roll', 1.2)     # дрожь силы перед тишиной
    a.pose(14.0, rightArm=SLASH_UP_R, torso=up_t)
    a.pose(14.45, rightArm=SLASH_UP_R, torso=up_t, head=_HL(yaw=-14, pitch=-4))   # 14.0–14.45: тишина, полная неподвижность
    # 14.45–14.65: последний росчерк наискось вниз-влево (fx/erased_vanish на 290 тике)
    end_t = _TO(yaw=-24, pitch=8, bend=4)
    end_l = _fk(pitch=-6, roll=-22, bend=-20)
    a.pose(14.65, 'easeOutQuart', rightArm=SLASH_DOWN_R, leftArm=end_l, torso=end_t, head=_HL(yaw=12, pitch=4), body={'y': -0.06},
           rightLeg=_TO(pitch=-12, roll=5, bend=14), leftLeg=_TO(pitch=14, roll=-5, bend=6))
    a.pose(EN_T, rightArm=SLASH_DOWN_R, leftArm=end_l, torso=end_t, head=_HL(yaw=12, pitch=6), body={'y': -0.06})
    return a, (SLASH_DOWN_R, end_l, end_t, (_TO(pitch=-12, roll=5, bend=14), _TO(pitch=14, roll=-5, bend=6)), -0.06)


_T24 = [lambda: erased_name_cast()[0],
        lambda: _finish('pohsmp_erased_name_finish', *erased_name_cast()[1][:3], head=_HL(yaw=12, pitch=6), legs=erased_name_cast()[1][3],
                        body_y=-0.06, length=1.2)]


# ---------------------------------------------------------------- T23: Мифические — «Древо мира» (12 с), «Око бездны» (12 с), «Последний рассвет» (10 с)
# Шкалы — docs/specs/tasks/T23_mythic_four.md (раздел «Ролики») и fx/world_tree_cast.json, abyss_eye_cast.json, last_dawn_cast.json
# (tools/gen_mythic_t23_fx.py). Без посоха. Касты замирают в последней позе (hold), к каждому — финал *_finish.
KNEEL_R_LEG = _TO(pitch=8, roll=2, bend=92)
KNEEL_L_LEG = _TO(pitch=-84, roll=-4, bend=86)


def world_tree_cast():
    """«Древо мира», 12 с: 0–1.2 опускается на колено, правая ладонь к земле (1 с — росток); 1.2–3 ладонь прижата, левая на колене;
    3–6.5 встаёт, обе ладони вверх перед собой — «поднимает» дерево; 6.5–9.5 руки медленно расходятся в стороны (ветви);
    9.5–11.6 руки к небу буквой V, голова запрокинута (крона); 11.7 руки чуть раскрываются — вспышка кроны."""
    a, r = Anim('pohsmp_world_tree_cast', 12.0), Rig()
    _start(a)
    ground_r = _fk(pitch=-28, yaw=-4, roll=6, bend=-30)                  # ладонь к земле (с колена)
    knee_l = r.L(3.0, 13.0, 5.0, elbow_out=1.4)
    a.pose(1.1, 'easeOutCubic', rightLeg=KNEEL_R_LEG, leftLeg=KNEEL_L_LEG, body={'y': -0.34}, rightArm=ground_r, leftArm=knee_l,
           torso=_TO(pitch=24, bend=10), head=_HL(pitch=20))
    a.sway(1.1, 3.0, 0.8, 'torso', _TO(pitch=24, bend=10), 'pitch', 1.5)
    lift_r, lift_l = r.R(-3.0, 17.0, 7.0, elbow_out=1.3), r.L(3.0, 17.0, 7.0, elbow_out=1.3)
    a.pose(3.6, 'easeInOutSine', rightLeg=ZERO_LEG, leftLeg=ZERO_LEG, body={'y': 0}, rightArm=lift_r, leftArm=lift_l, torso=_TO(pitch=4, bend=3),
           head=_HL(pitch=4))
    up_r, up_l = r.R(-3.4, 25.5, 7.2, elbow_out=1.3), r.L(3.4, 25.5, 7.2, elbow_out=1.3)
    a.pose(6.4, 'easeInOutSine', rightArm=up_r, leftArm=up_l, torso=_TO(pitch=-4, bend=-2), head=_HL(pitch=-22))
    wide = _fk(pitch=-40, yaw=-6, roll=70, bend=-12)
    a.pose(9.3, 'easeInOutSine', rightArm=wide, leftArm=mirror(wide), torso=_TO(pitch=-5, bend=-3), head=_HL(pitch=-28),
           rightLeg=_TO(pitch=0, roll=5), leftLeg=_TO(pitch=0, roll=-5))
    a.sway(9.3, 9.6, 0.3, 'body', {'y': 0}, 'y', 0.02)
    sky = _fk(pitch=-18, roll=140, bend=-10)
    a.pose(11.5, 'easeInOutCubic', rightArm=sky, leftArm=mirror(sky), torso=_TO(pitch=-9, bend=-6), head=_HL(pitch=-36), body={'y': 0.03})
    end = _fk(pitch=-24, roll=118, bend=-8)
    a.pose(11.75, 'easeOutBack', rightArm=end, leftArm=mirror(end), torso=_TO(pitch=-8, bend=-5), head=_HL(pitch=-32), body={'y': 0.03})
    a.pose(12.0, rightArm=end, leftArm=mirror(end), torso=_TO(pitch=-8, bend=-5), head=_HL(pitch=-32), body={'y': 0.03})
    return a, (end, mirror(end), _TO(pitch=-8, bend=-5), (_TO(pitch=0, roll=5), _TO(pitch=0, roll=-5)), 0.03)


def abyss_eye_cast():
    """«Око бездны», 12 с: 0–2 ладони закрывают лицо, голова опущена; 2–6 пальцы медленно сползают с лица (когти), голова поднимается;
    6–8.5 правая рука-коготь к небу, левая прижата к груди; 8.5–11.3 обе руки вверх, ладони раскрыты, голова запрокинута (глаз
    раскрывается 8–11.5); 11.4–11.6 рывок: голова вперёд, руки вниз-в стороны — Око смотрит."""
    a, r = Anim('pohsmp_abyss_eye_cast', 12.0), Rig()
    _start(a)
    a.pose(0.2, 'easeInQuad', rightArm=r.R(-2.6, 21.0, 10.0, elbow_out=1.3), leftArm=r.L(2.6, 21.0, 10.0, elbow_out=1.3))
    face_r, face_l = r.R(-1.6, 27.0, 8.6, elbow_out=1.4), r.L(1.6, 27.0, 8.6, elbow_out=1.4)
    a.pose(0.9, 'easeOutCubic', rightArm=face_r, leftArm=face_l, torso=_TO(pitch=10, bend=6), head=_HL(pitch=22))
    a.sway(0.9, 2.0, 0.9, 'torso', _TO(pitch=10, bend=6), 'pitch', 2)
    claw_r, claw_l = r.R(-3.2, 21.0, 8.8, elbow_out=1.5), r.L(3.2, 21.0, 8.8, elbow_out=1.5)
    a.pose(5.8, 'easeInOutSine', rightArm=claw_r, leftArm=claw_l, torso=_TO(pitch=2, bend=1), head=_HL(pitch=-8))
    a.sway(2.0, 5.8, 0.16, 'head', _HL(pitch=4), 'roll', 2)
    sky_claw = _fk(pitch=-160, yaw=6, roll=-10, bend=-38)
    chest_l = r.L(1.4, 19.0, 5.0, elbow_out=1.5)
    a.pose(7.0, 'easeOutCubic', rightArm=sky_claw, leftArm=chest_l, torso=_TO(pitch=-6, bend=-3), head=_HL(pitch=-30))
    a.sway(7.0, 8.5, 0.14, 'rightArm', sky_claw, 'roll', 2)
    up = _fk(pitch=-20, roll=148, bend=-10)
    a.pose(9.2, 'easeInOutSine', rightArm=up, leftArm=mirror(up), torso=_TO(pitch=-12, bend=-8), head=_HL(pitch=-42), body={'y': 0.03})
    a.sway(9.2, 11.3, 0.2, 'body', {'y': 0.03}, 'y', 0.015)
    a.pose(11.35, rightArm=merge(up, {'roll': 152}), leftArm=mirror(merge(up, {'roll': 152})), torso=_TO(pitch=-13, bend=-9), head=_HL(pitch=-44))
    down = _fk(pitch=-12, yaw=6, roll=42, bend=-26)
    end_t = _TO(pitch=12, bend=6)
    legs = (_TO(pitch=-12, roll=6, bend=14), _TO(pitch=12, roll=-6, bend=8))
    a.pose(11.6, 'easeOutQuart', rightArm=down, leftArm=mirror(down), torso=end_t, head=_HL(pitch=-6), body={'y': -0.08},
           rightLeg=legs[0], leftLeg=legs[1])
    a.pose(12.0, rightArm=down, leftArm=mirror(down), torso=end_t, head=_HL(pitch=-4), body={'y': -0.08})
    return a, (down, mirror(down), end_t, legs, -0.08)


def last_dawn_cast():
    """«Последний рассвет», 10 с: 0–1.5 молитва у груди; 1.5–5 на колено, молитва, голова склонена (заря разгорается);
    5–7.5 встаёт, руки раскрываются вперёд-вверх навстречу солнцу; 7.5–9.5 руки к солнцу широкой V, голова поднята; 10 с — взошло."""
    a, r = Anim('pohsmp_last_dawn_cast', 10.0), Rig()
    _start(a)
    pray_r, pray_l = r.R(-0.55, 21.6, 5.6), r.L(0.55, 21.6, 5.6)
    a.pose(1.2, rightArm=pray_r, leftArm=pray_l, torso=_TO(pitch=4, bend=4), head=_HL(pitch=14))
    a.pose(2.4, 'easeOutCubic', rightLeg=KNEEL_R_LEG, leftLeg=KNEEL_L_LEG, body={'y': -0.34}, torso=_TO(pitch=8, bend=6), head=_HL(pitch=24))
    a.sway(2.4, 5.0, 1.3, 'torso', _TO(pitch=8, bend=6), 'pitch', 1.5)
    open_r, open_l = r.R(-5.0, 21.5, 8.4, elbow_out=1.3), r.L(5.0, 21.5, 8.4, elbow_out=1.3)
    a.pose(6.6, 'easeInOutSine', rightLeg=ZERO_LEG, leftLeg=ZERO_LEG, body={'y': 0}, rightArm=open_r, leftArm=open_l, torso=_TO(pitch=0),
           head=_HL(pitch=-8))
    a.sway(6.6, 7.6, 0.5, 'rightArm', open_r, 'pitch', 2)
    v = _fk(pitch=-70, yaw=-8, roll=58, bend=-6)
    a.pose(9.4, 'easeInOutCubic', rightArm=v, leftArm=mirror(v), torso=_TO(pitch=-8, bend=-5), head=_HL(pitch=-20), body={'y': 0.03})
    a.pose(10.0, rightArm=merge(v, {'pitch': -74}), leftArm=mirror(merge(v, {'pitch': -74})), torso=_TO(pitch=-9, bend=-6), head=_HL(pitch=-22),
           body={'y': 0.04})
    return a, (merge(v, {'pitch': -74}), mirror(merge(v, {'pitch': -74})), _TO(pitch=-9, bend=-6), (ZERO_LEG, ZERO_LEG), 0.04)


def _t23(fn, name, length, head):
    return [lambda: fn()[0], lambda: _finish(name, *fn()[1][:3], head=head, legs=fn()[1][3], body_y=fn()[1][4], length=length)]


_T23 = (_t23(world_tree_cast, 'pohsmp_world_tree_finish', 1.5, _HL(pitch=-32)) + _t23(abyss_eye_cast, 'pohsmp_abyss_eye_finish', 1.0, _HL(pitch=-4))
        + _t23(last_dawn_cast, 'pohsmp_last_dawn_finish', 1.5, _HL(pitch=-22)))


# ---------------------------------------------------------------- T25: школа «Кошмары»
# Шкалы — docs/specs/tasks/T25_nightmare_school.md (раздел «Ролик») и fx/nightmare_*.json (tools/gen_nightmare_fx.py). Без посоха.
# Касты Высших и Мифического замирают в последней позе (hold), к каждому — финал *_finish.
HOUSE_T = 2.5
HOUSE_KNOB_R = _fk(pitch=-80, yaw=4, roll=-6, bend=-14)          # рука к цели, ладонь вниз — «берётся за ручку двери»
HOUSE_PULL_R = _fk(pitch=-40, yaw=-6, roll=22, bend=-62)          # рывок к себе: дверь распахнута
HOUSE_DROP_R = _fk(pitch=-14, yaw=-4, roll=14, bend=-30)          # кисть отпущена вниз — цель «провалилась»


def nightmare_house_that_isnt_cast():
    """«Дом, которого нет» (Высшее), 2.5 с = 50 тиков: левый палец к губам («тсс», 0–0.5), правая рука к цели — берётся за невидимую
    ручку (0.5); медленно поворачивает кисть, как ключ (0.6–1.6, у ладони — око); тянет на себя (1.6–2.2) — дверь открыта; на 2.2 с
    (44 тик) кисть резко разжимается и падает — на 46 тике цель проваливается. Держит позу."""
    a, r = Anim('pohsmp_nightmare_house_cast', HOUSE_T), Rig()
    _start(a)
    hush_l = r.L(0.3, 26.4, 8.6, elbow_out=1.3)
    a.pose(0.45, 'easeOutCubic', leftArm=hush_l, head=_HL(pitch=6, yaw=4), torso=_TO(pitch=2))
    a.pose(0.6, 'easeOutCubic', rightArm=HOUSE_KNOB_R, torso=_TO(pitch=3, yaw=-6), head=_HL(pitch=2, yaw=6),
           rightLeg=_TO(pitch=-8, roll=4, bend=6), leftLeg=_TO(pitch=8, roll=-4, bend=4))
    for k, tt in enumerate((0.85, 1.1, 1.35, 1.6)):                                  # поворот «ключа» рывками
        a.pose(tt, 'easeInOutQuad', rightArm=merge(HOUSE_KNOB_R, {'roll': -6 - 22 * (k + 1) / 4, 'yaw': 4 + 2 * (k % 2)}))
    a.pose(2.15, 'easeInCubic', rightArm=HOUSE_PULL_R, torso=_TO(pitch=-4, yaw=-12, bend=-2), head=_HL(pitch=-4, yaw=10))
    a.pose(2.3, 'easeOutBack', rightArm=HOUSE_DROP_R, leftArm=_fk(pitch=8, roll=-12, bend=-14), torso=_TO(pitch=4, yaw=-6), head=_HL(pitch=10, yaw=4))
    a.pose(HOUSE_T, rightArm=HOUSE_DROP_R, leftArm=_fk(pitch=8, roll=-12, bend=-14), torso=_TO(pitch=4, yaw=-6), head=_HL(pitch=10, yaw=4))
    return a, (HOUSE_DROP_R, _fk(pitch=8, roll=-12, bend=-14), _TO(pitch=4, yaw=-6), (_TO(pitch=-8, roll=4, bend=6), _TO(pitch=8, roll=-4, bend=4)), 0.0)


NIGHT_T = 3.0
NIGHT_SKY_R = _fk(pitch=-172, yaw=0, roll=-8, bend=-6)            # правая рука к небу, ладонь вверх — «поднимает луну»
NIGHT_SLAM_R = _fk(pitch=-20, yaw=4, roll=34, bend=-40)           # кулак вниз-в сторону — «закат навсегда»


def nightmare_endless_night_cast():
    """«Ночь без рассвета» (Высшее), 3 с = 60 тиков: левая ладонь вперёд (око у ладони, 0–0.5), сжимается в кулак и уводится вниз —
    «гасит свет» (0.6–1.4); правая медленно поднимается к небу ладонью вверх, взгляд за ней (1.0–2.6) — всходит луна; на 2.8 с
    (56 тик) кулак правой падает вниз-в сторону, корпус клонится — тьма бежит по земле. Держит позу."""
    a, r = Anim('pohsmp_nightmare_night_cast', NIGHT_T), Rig()
    _start(a)
    palm_l = r.L(2.2, 22.0, 10.4, elbow_out=1.2)
    a.pose(0.5, 'easeOutCubic', leftArm=palm_l, torso=_TO(pitch=2, yaw=6), head=_HL(pitch=4, yaw=-4))
    fist_l = _fk(pitch=-30, yaw=-6, roll=-18, bend=-48)
    a.pose(1.0, 'easeInOutQuad', leftArm=merge(palm_l, {}))
    a.pose(1.4, 'easeInCubic', leftArm=fist_l, torso=_TO(pitch=4, yaw=2), head=_HL(pitch=6))
    a.pose(1.2, rightArm=ARM_DOWN_R)
    a.pose(2.6, 'easeInOutSine', rightArm=NIGHT_SKY_R, torso=_TO(pitch=-8, bend=-4), head=_HL(pitch=-34), body={'y': 0.02})
    a.sway(2.6, 2.72, 0.06, 'rightArm', NIGHT_SKY_R, 'roll', 2)
    end_t = _TO(pitch=14, yaw=-8, bend=8)
    legs = (_TO(pitch=-12, roll=6, bend=16), _TO(pitch=14, roll=-6, bend=8))
    a.pose(2.82, 'easeInQuart', rightArm=NIGHT_SLAM_R, leftArm=fist_l, torso=end_t, head=_HL(pitch=-4, yaw=6), body={'y': -0.1},
           rightLeg=legs[0], leftLeg=legs[1])
    a.pose(NIGHT_T, rightArm=NIGHT_SLAM_R, leftArm=fist_l, torso=end_t, head=_HL(pitch=-2, yaw=6), body={'y': -0.1})
    return a, (NIGHT_SLAM_R, fist_l, end_t, legs, -0.1)


ABYSS_T = 12.0


def nightmare_no_awakening_cast():
    """«Пробуждение не наступит» (Мифическое), 12 с = 240 тиков (планы ролика — ТЗ T25, «Ролик»):
    0–2 ладони зажимают уши, голова опущена, медленное покачивание, как над колыбелью (звучит сломанная колыбельная);
    2–4 ладони сползают и опускаются вниз ладонями к земле — «поднимает» чернила: руки медленно идут вверх до пояса ладонями вверх;
    4–6 голова запрокидывается к гаснущему небу, руки вверх широкой V;
    6–8 руки описывают дугу вниз и обнимают себя, корпус клонится — мир тонет;
    8–10 на 9 с удар сердца: тело дёргается, голова вскидывается, руки отброшены назад, грудь вперёд (облик меняется);
    10–11.8 тьма: стоит неподвижно, голова неестественно наклонена набок, руки висят;
    11.8 голова резко выпрямляется к зрителю, кисти скрючены когтями, полшага вперёд — «глаза открылись»."""
    a, r = Anim('pohsmp_nightmare_abyss_cast', ABYSS_T), Rig()
    _start(a)
    ear_r, ear_l = r.R(-5.4, 28.4, 0.8, elbow_out=1.6), r.L(5.4, 28.4, 0.8, elbow_out=1.6)
    bow = _TO(pitch=10, bend=6)
    a.pose(0.7, 'easeInOutSine', rightArm=ear_r, leftArm=ear_l, torso=bow, head=_HL(pitch=24))
    a.sway(0.7, 2.0, 0.65, 'torso', bow, 'roll', 3)
    a.sway(0.7, 2.0, 0.65, 'head', _HL(pitch=24), 'roll', 5)
    low_r, low_l = _fk(pitch=-30, yaw=-10, roll=24, bend=-10), _fk(pitch=-30, yaw=10, roll=-24, bend=-10)
    a.pose(2.6, 'easeInOutSine', rightArm=low_r, leftArm=low_l, torso=_TO(pitch=6, bend=4), head=_HL(pitch=16))
    lift_r, lift_l = r.R(-6.2, 17.5, 7.0, elbow_out=1.3), r.L(6.2, 17.5, 7.0, elbow_out=1.3)
    a.pose(3.9, 'easeInOutSine', rightArm=lift_r, leftArm=lift_l, torso=_TO(pitch=0), head=_HL(pitch=0))
    v_r = _fk(pitch=-30, yaw=0, roll=136, bend=-8)
    a.pose(5.6, 'easeInOutSine', rightArm=v_r, leftArm=mirror(v_r), torso=_TO(pitch=-10, bend=-6), head=_HL(pitch=-40), body={'y': 0.03})
    a.sway(5.6, 6.0, 0.2, 'rightArm', v_r, 'roll', 2)
    hug_r, hug_l = r.R(3.4, 19.4, 5.6, elbow_out=1.5), r.L(-3.4, 19.4, 5.6, elbow_out=1.5)
    hug_t = _TO(pitch=16, bend=12)
    hug_legs = dict(rightLeg=_TO(pitch=-10, roll=4, bend=12), leftLeg=_TO(pitch=10, roll=-4, bend=6))
    a.pose(7.0, 'easeInOutCubic', rightArm=hug_r, leftArm=hug_l, torso=hug_t, head=_HL(pitch=26), body={'y': -0.06}, **hug_legs)
    a.sway(7.0, 8.8, 0.18, 'torso', hug_t, 'roll', 1.5)
    a.pose(8.85, torso=merge(hug_t, {'pitch': 18}), head=_HL(pitch=28))
    back_r = _fk(pitch=40, yaw=10, roll=40, bend=-12)
    arch_t = _TO(pitch=-16, bend=-10)
    a.pose(9.05, 'easeOutBack', rightArm=back_r, leftArm=mirror(back_r), torso=arch_t, head=_HL(pitch=-30), body={'y': 0.04},
           rightLeg=ZERO_LEG, leftLeg=ZERO_LEG)
    a.pose(9.8, 'easeInOutSine', rightArm=merge(back_r, {'pitch': 30}), leftArm=mirror(merge(back_r, {'pitch': 30})), torso=_TO(pitch=-10, bend=-6),
           head=_HL(pitch=-20), body={'y': 0.02})
    hang_r, hang_l = _fk(pitch=4, yaw=0, roll=4, bend=-4), _fk(pitch=4, yaw=0, roll=-4, bend=-4)
    still_h = _HL(pitch=6, yaw=4, roll=34)
    a.pose(10.6, 'easeInOutSine', rightArm=hang_r, leftArm=hang_l, torso=_TO(pitch=2), head=still_h, body={'y': 0})
    a.pose(11.75, rightArm=hang_r, leftArm=hang_l, torso=_TO(pitch=2), head=still_h)
    claw_r, claw_l = _fk(pitch=-36, yaw=-8, roll=22, bend=-46), _fk(pitch=-36, yaw=8, roll=-22, bend=-46)
    end_t = _TO(pitch=8, bend=4)
    legs = (_TO(pitch=-16, roll=4, bend=10), _TO(pitch=12, roll=-4, bend=6))
    a.pose(11.9, 'easeOutQuart', rightArm=claw_r, leftArm=claw_l, torso=end_t, head=_HL(pitch=-4), body={'y': -0.04},
           rightLeg=legs[0], leftLeg=legs[1])
    a.pose(ABYSS_T, rightArm=claw_r, leftArm=claw_l, torso=end_t, head=_HL(pitch=-6), body={'y': -0.04})
    return a, (claw_r, claw_l, end_t, legs, -0.04)


def _t25(fn, name, length, head):
    return [lambda: fn()[0], lambda: _finish(name, *fn()[1][:3], head=head, legs=fn()[1][3], body_y=fn()[1][4], length=length)]


_T25 = (_t25(nightmare_house_that_isnt_cast, 'pohsmp_nightmare_house_finish', 1.0, _HL(pitch=10, yaw=4))
        + _t25(nightmare_endless_night_cast, 'pohsmp_nightmare_night_finish', 1.2, _HL(pitch=-2, yaw=6))
        + _t25(nightmare_no_awakening_cast, 'pohsmp_nightmare_abyss_finish', 1.5, _HL(pitch=-6)))


def pose_gallery():
    """Только для превью: по 1.4 с на каждую позу библиотеки."""
    out = []
    for k in POSES:
        a = compose(f'поза: {k} — {POSE_NAMES[k]}', 1.6, [('stand', 0), (k, 0.6, 'easeOutCubic'), (k, 1.6)])
        out.append(a)
    return out

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
_DI = _pair(disintegration_cast, 'pohsmp_disintegration_finish')
_SS = (lambda: soul_seal_cast()[0],
       lambda: _finish('pohsmp_soul_seal_finish', *soul_seal_cast()[1][:3], head=_HL(pitch=4, yaw=-2), legs=soul_seal_cast()[1][3],
                       body_y=-0.05, length=1.2))
_BL = (lambda: blessing_cast()[0],
       lambda: _finish('pohsmp_blessing_finish', *blessing_cast()[1][:3], head=_HL(pitch=-32), legs=blessing_cast()[1][3],
                       body_y=0.02, length=1.5))


ANIMS = [downfall_cast, downfall_finish, *_MW, *_SD, *_TB, *_SC, *_CA, coven_ritual, *_DI, lambda: silent_gate_cast()[0], silent_gate_wait, silent_gate_command, silent_gate_finish,
         scarlet_cut_cast, finger_snap, held_target, cult_finisher_victim, martin_finisher_victim, star_fall_cast, star_fall_finish,
         silent_volley_cast, silent_volley_finish, sage_barrier_cast, sage_barrier_finish, worgan_flame_cast, worgan_flame_finish,
         *_SS, *_BL, *_T22, *_T24, *_T23, *_T25]


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
    try:                       # T34: наградные заклинания боссов — свой генератор (tools/gen_t34_anims.py); в превью тоже показываем
        import gen_t34_anims as T34
        for a in (f() for f in T34.ANIMS):
            data[a.name] = a.emotecraft()
    except ImportError:
        pass
    for a in pose_gallery():   # библиотека поз — только в превью, в мод не пишется
        data[a.name] = a.emotecraft()
    with open(os.path.join(HERE, 'anim_preview.template.html'), encoding='utf-8') as fh:
        page = fh.read().replace('/*ANIMS*/null', json.dumps(data, ensure_ascii=False))
    with open(os.path.join(HERE, 'anim_preview.html'), 'w', encoding='utf-8') as fh:
        fh.write(page)
    print('wrote tools/anim_preview.html')


if __name__ == '__main__':
    main()
