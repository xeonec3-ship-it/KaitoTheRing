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


def arm(side, hand, staff=None, elbow_out=1.0):
    """
    Кисть в точке hand (пиксели модели), посох в этой руке смотрит по staff.
    Перебираем, куда отвести локоть, и берём вариант, где посох ближе к нужному направлению,
    а локоть выглядит естественно: ниже кисти, снаружи от корпуса.
    Возвращает ({'pitch','yaw','roll','bend'}, направление посоха).
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
            score += 4.0 * float(np.dot(st, _n(staff)))
        score += elbow_out * (0.6 * (-u[1]) + 0.5 * (e_abs[0] * sx - BODY_X) / 4.0)
        if e_abs[0] * sx < BODY_X - 0.5 and e_abs[2] < 2.5:      # локоть внутри корпуса
            score -= 3.0
        if best is None or score > best[0]:
            best = (score, up, st)
    p, y, r = _euler(best[1])
    return {'pitch': p, 'yaw': y, 'roll': r, 'bend': math.degrees(bend)}, best[2]


def grip(hand, staff, dist):
    """Точка на древке в dist пикселях от хвата hand по направлению staff (для второй руки)."""
    return np.asarray(hand, dtype=float) + _n(staff) * dist


def _a(side, hand, staff=None, **kw):
    return arm(side, hand, staff, **kw)[0]


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
# Каст 25 с (DownfallSpell.CAST = 500 тиков). Хореография по разбору видео:
#   0      — стоит неподвижно, руки вдоль тела; посох висит в воздухе справа (клиентский эффект, не эта анимация)
#   4а     — «Сосредоточение»: правая кисть у груди и подбородка, предплечье поперёк корпуса, голова опущена
#   4б     — посох в руках по диагонали поперёк тела: навершие вверху слева над головой, низ справа
#   4в     — прокрутка ~1.4 с: диагональ -> горизонталь у груди -> почти вертикаль -> горизонталь
#   4г     — «Активация»: посох горизонтально перед грудью, навершием влево, двумя руками, как преграда
#   10, 15 с — толчки заклинания (разлом, нить): игрок упирается, посох чуть подаётся вперёд
# Навершие — конец посоха по направлению staff.

T_FOCUS, T_FOCUS_END, T_DIAG = 1.2, 2.5, 2.9
T_SPIN = (2.9, 3.35, 3.8, 4.25)
T_HOLD = 4.6

S_DIAG = (0.6, 0.78, 0.18)
S_HORIZ = (1.0, 0.0, 0.06)
S_VERT = (0.1, 1.0, 0.12)

HOLD_R = (-5.9, 17.6, 6.6)           # правая кисть перед правой стороной груди (подобрано под горизонтальный посох)
HOLD_L = grip(HOLD_R, S_HORIZ, 8.0)   # левая держит древко ближе к навершию
DIAG_R = (-5.1, 16.3, 5.7)
DIAG_L = grip(DIAG_R, S_DIAG, 10.5)
SPIN_H = (-3.3, 15.2, 5.4)           # точки хвата при прокрутке: у каждой ориентации своя
SPIN_V = (-2.8, 17.7, 6.4)

REST_R = {'pitch': 0, 'yaw': 0, 'roll': 3, 'bend': -4}
REST_L = {'pitch': 0, 'yaw': 0, 'roll': -3, 'bend': -4}
STANCE_R, STANCE_L = {'roll': 4, 'pitch': 6, 'bend': 8}, {'roll': -5, 'pitch': -8, 'bend': 4}
LEGS_REST = {'roll': 0, 'pitch': 0, 'bend': 0}
BREATHE = {'pitch': -3, 'yaw': 0, 'bend': -3}


def downfall_cast():
    a = Anim('pohsmp_downfall_cast', 25.0)
    a.pose(0, rightArm=REST_R, leftArm=REST_L, torso={'pitch': 0, 'yaw': 0, 'bend': 0}, head={'pitch': 0, 'yaw': 0},
           rightLeg={'roll': 2, 'pitch': 0, 'bend': 0}, leftLeg={'roll': -2, 'pitch': 0, 'bend': 0})
    a.sway(0, T_FOCUS - 0.4, 1.6, 'torso', {'pitch': 0, 'yaw': 0, 'bend': 0}, 'pitch', 1.0)

    # 4а — сосредоточение
    focus_r = _a('right', (0.6, 21.2, 4.2), staff=(0, 1, 0.2))
    a.pose(T_FOCUS - 0.4, rightArm=REST_R, leftArm=REST_L, head={'pitch': 0, 'yaw': 0})
    a.pose(T_FOCUS, rightArm=focus_r, leftArm={'pitch': 0, 'yaw': 0, 'roll': -5, 'bend': -8},
           torso={'pitch': 4, 'yaw': -4, 'bend': 6}, head={'pitch': 18, 'yaw': -6})
    a.pose(T_FOCUS_END, rightArm=merge(focus_r, {'pitch': focus_r['pitch'] - 4}),
           torso={'pitch': 5, 'yaw': -4, 'bend': 8}, head={'pitch': 22, 'yaw': -6})

    # 4б — посох по диагонали, двумя руками
    a.pose(T_DIAG, 'easeOutBack', rightArm=_a('right', DIAG_R, S_DIAG), leftArm=_a('left', DIAG_L, S_DIAG))
    a.pose(T_DIAG, 'easeOutCubic', torso={'pitch': -2, 'yaw': 8, 'bend': -2}, head={'pitch': -10, 'yaw': 6})

    # 4в — прокрутка одной правой рукой, левая отпускает и уходит в сторону
    a.pose(T_SPIN[0] + 0.25, leftArm=_a('left', (8.2, 12.5, 2.5), elbow_out=1.4))
    for t, h, s in ((T_SPIN[1], SPIN_H, S_HORIZ), (T_SPIN[2], SPIN_V, S_VERT), (T_SPIN[3], SPIN_H, S_HORIZ)):
        a.pose(t, 'easeInOutQuad', rightArm=_a('right', h, s))
    a.pose(T_SPIN[1], torso={'pitch': 0, 'yaw': -5, 'bend': 0}, head={'pitch': 2, 'yaw': -3})
    a.pose(T_SPIN[2], torso={'pitch': -2, 'yaw': 5, 'bend': -2}, head={'pitch': -6, 'yaw': 3})
    a.pose(T_SPIN[3], torso={'pitch': 0, 'yaw': 0, 'bend': 0}, head={'pitch': 0, 'yaw': 0},
           rightLeg={'roll': 2, 'pitch': 0, 'bend': 0}, leftLeg={'roll': -2, 'pitch': 0, 'bend': 0})

    # 4г — активация: посох-преграда двумя руками, стойка шире
    hold_r, hold_l = _a('right', HOLD_R, S_HORIZ), _a('left', HOLD_L, S_HORIZ)
    a.pose(T_HOLD, 'easeOutBack', rightArm=hold_r, leftArm=hold_l)
    a.pose(T_HOLD, torso=BREATHE, head={'pitch': -6, 'yaw': 0}, rightLeg=STANCE_R, leftLeg=STANCE_L)

    # удержание: дыхание и два толчка заклинания (10 с — разлом, 15 с — нить)
    push_r = _a('right', np.add(HOLD_R, (0, 0.4, 1.4)), S_HORIZ)
    push_l = _a('left', np.add(HOLD_L, (0, 0.4, 1.4)), S_HORIZ)
    a.sway(T_HOLD, 9.6, 3.2, 'torso', BREATHE, 'pitch', 1.2)
    a.sway(11.0, 14.6, 3.2, 'torso', BREATHE, 'pitch', 1.2)
    a.sway(16.0, 25.0, 3.2, 'torso', BREATHE, 'pitch', 1.2)
    for t in (10.0, 15.0):
        a.pose(t - 0.4, rightArm=hold_r, leftArm=hold_l, head={'pitch': -6, 'yaw': 0})
        a.pose(t, 'easeOutCubic', rightArm=push_r, leftArm=push_l, torso={'pitch': 4, 'yaw': 0, 'bend': 2},
               head={'pitch': -2, 'yaw': 0})
        a.pose(t + 1.0, rightArm=hold_r, leftArm=hold_l, torso=BREATHE, head={'pitch': -6, 'yaw': 0})
    a.pose(25.0, rightArm=hold_r, leftArm=hold_l, head={'pitch': -6, 'yaw': 0}, rightLeg=STANCE_R, leftLeg=STANCE_L)
    return a


def downfall_finish():
    """После каста: преграда резко толкается вперёд, затем руки опускаются."""
    a = Anim('pohsmp_downfall_finish', 1.5, hold=False)
    hold_r, hold_l = _a('right', HOLD_R, S_HORIZ), _a('left', HOLD_L, S_HORIZ)
    a.pose(0, rightArm=hold_r, leftArm=hold_l, torso=BREATHE, head={'pitch': -6, 'yaw': 0},
           rightLeg=STANCE_R, leftLeg=STANCE_L)
    a.pose(0.18, 'easeOutCubic', rightArm=_a('right', np.add(HOLD_R, (0, 0.6, 3.0)), S_HORIZ),
           leftArm=_a('left', np.add(HOLD_L, (0, 0.6, 3.0)), S_HORIZ),
           torso={'pitch': 9, 'yaw': 0, 'bend': 4}, head={'pitch': 0, 'yaw': 0})
    a.pose(0.5, rightArm=_a('right', (-3.0, 15.5, 5.0), (0.2, 1, 0.3)),
           leftArm={'pitch': 0, 'yaw': 0, 'roll': -6, 'bend': -6}, torso={'pitch': 2, 'yaw': 0, 'bend': 0})
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
