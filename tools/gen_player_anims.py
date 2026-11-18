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


def arm(side, hand, staff=None, elbow_out=1.0, fore=None):
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
        score += elbow_out * (0.6 * (-u[1]) + 0.5 * (e_abs[0] * sx - BODY_X) / 4.0)
        if e_abs[0] * sx < BODY_X - 0.5 and e_abs[2] < 2.5:      # локоть внутри корпуса
            score -= 3.0
        if best is None or score > best[0]:
            best = (score, up, st, f)
    p, y, r = _euler(best[1])
    info = {'staff': best[2], 'fore': best[3], 'twist': 0.0}
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
                    ch = {c: (v + 360 * round((prev[c] - v) / 360)) if c in ('pitch', 'yaw', 'roll') and c in prev else v
                          for c, v in ch.items()}
                prev.update(ch)
                moves.append({'tick': tick, 'easing': ease, part: {c: round(float(v), 2) for c, v in ch.items()}})
        moves.sort(key=lambda m: m['tick'])
        emote = {'beginTick': 0, 'endTick': self.end, 'stopTick': self.end, 'degrees': True,
                 'easeBeforeKeyframe': True, 'moves': moves}
        if self.hold:
            emote.update({'isLoop': True, 'returnTick': self.end})
        return {'version': 3, 'name': self.name, 'author': 'pohsmp_core', 'emote': emote}


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


ANIMS = [downfall_cast, downfall_finish]


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
