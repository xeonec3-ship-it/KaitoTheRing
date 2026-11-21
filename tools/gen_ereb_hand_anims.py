#!/usr/bin/env python3
"""
T31 «Эреб, Длань Лжи» — анимации GeckoLib (ereb_hand_*). Вызывается из tools/gen_ereb_hand.py (write(M)).
Файл animations/entity/ereb_hand.animation.json = все casting_animations.json Iron's (те же имена: их зовёт AbstractSpellCastingMob)
+ ereb_hand_*. События — ключи timeline (GeckoLib CustomInstructionKeyframeEvent); коду можно заменить их таймерами (таблица в письме).

Оси — как у T30 (tools/gen_ereb_anims.py): rotation x < 0 — рука вперёд-вверх; body y > 0 — поворот к своей правой стороне.
Призрачная рука (ghost_*, дочь body): position x > 0 — к левому боку модели, y — вверх, z < 0 — ВПЕРЁД; rotation x > 0 — пальцы к ладони
(«вперёд»), y < 0 — ладонь к середине тела, z > 0 — кисть наклоняется к голове. Фаланги: x > 0 — сгиб к ладони.
Накидка (cape, ось у плеч сзади): x > 0 — подол назад. Маска (mask, дочь head): её срывают в «Падении маски».

Правило: КАЖДЫЙ ключ — полная поза (все кости), поэтому промежуточные ключи не «проваливаются» к нулю; каждая анимация начинается и
кончается позой покоя (IDLE0) или позой той анимации, из которой/в которую переходит (хватка → удержание → сжатие → отпустить).
Проверка покадрово (0.1 с): python3 tools/check_ereb_hand_anims.py.
"""
import json
import math

import gen_ereb_anims as EA

IO, OC, OQ, IQ, IC, OB = 'easeInOutSine', 'easeOutCubic', 'easeOutQuart', 'easeInQuart', 'easeInCubic', 'easeOutBack'
LIN = 'linear'
FINGERS = ('index', 'middle', 'ring', 'pinky')
SPREAD = {'index': 7, 'middle': 2, 'ring': -3, 'pinky': -9}
CURL = (58, 80, 62)                                    # кулак: сгиб фаланг 1–3
BODY = ('body', 'torso', 'head', 'right_arm', 'left_arm', 'right_leg', 'left_leg', 'bipedHandRight', 'bipedHandLeft',
        'coat_front_r', 'coat_front_l', 'coat_back_r', 'coat_back_l', 'cape', 'mask')
GHOST = ['ghost_hand', 'ghost_wrist', 'ghost_palm'] + ['ghost_%s_%d' % (f, k) for f in FINGERS for k in (1, 2, 3)] + ['ghost_thumb_1', 'ghost_thumb_2']
Z3 = [0, 0, 0]
ONE = [1, 1, 1]


# ================================================================== позы
def hand(pos=(0, 0, 0), rot=(14, -18, -6), curl=0.2, spread=0.0, thumb=0.15, wrist=(0, 0, 0), scale=1.0, ripple=0.0, point=False):
    """Поза призрачной руки. curl 0 — раскрыта, 1 — кулак; spread — веер пальцев; thumb 0 — отведён, 1 — прижат к ладони;
    ripple — сдвиг сгиба по пальцам (волна «перебирает пальцами»)."""
    p = {'ghost_hand': list(rot), 'ghost_hand_pos': list(pos), 'ghost_hand_scale': [scale] * 3, 'ghost_wrist': list(wrist), 'ghost_palm': Z3}
    for i, f in enumerate(FINGERS):
        c = max(0.0, min(1.1, curl + ripple * math.sin(i * 1.3)))
        if point and f == 'index':
            c = 0.05                                    # указующий палец прямой («Чужая клятва»)
        for k in (1, 2, 3):
            p['ghost_%s_%d' % (f, k)] = [round(c * CURL[k - 1] + (3 if k > 1 else 0), 2), 0, round(spread * SPREAD[f], 2) if k == 1 else 0]
    p['ghost_thumb_1'] = [thumb * 18, thumb * 38, -thumb * 6]
    p['ghost_thumb_2'] = [0, thumb * 34, 0]
    return p


# тело — позы T30 + новая левая рука (перчатка «Длани» видна: рука у бедра, а не за спиной), накидка
STAND = EA.mod(EA.STAND, left_arm=[-10, -6, -8], bipedHandLeft=Z3, cape=[4, 0, 0])
GUARD = EA.mod(EA.GUARD, cape=[12, 0, 0])
LUNGE = EA.mod(EA.LUNGE, cape=[34, 0, 0])
PARRY = EA.mod(EA.PARRY, cape=[14, 0, 0])
CAST = EA.mod(EA.CAST, cape=[6, 0, 0], bipedHandRight=[44, 0, 0])
BOW = EA.mod(EA.BOW, cape=[10, 0, 0], left_arm=[18, -12, 12], bipedHandRight=[44, 0, 0])
SALUTE = EA.mod(EA.SALUTE, cape=[6, 0, 0])
HOVER = hand()


def full(body, gh=None, **kw):
    """Полная поза: все кости тела (недостающие — 0) + рука + правки."""
    p = {b: Z3 for b in BODY}
    p.update({'body_pos': Z3, 'body_scale': ONE, 'mask_pos': Z3, 'mask_scale': ONE})
    p.update(body)
    p.update(gh if gh is not None else HOVER)
    p.update(kw)
    # накидка — три кости: общий угол cape раскладывается волной (верх ведёт, середина догоняет, низ отстаёт и провисает)
    if 'cape_mid' not in p:
        c = p['cape']
        if c[0] > 15:
            p['cape'], p['cape_mid'], p['cape_low'] = ([c[0] * 0.6, c[1], c[2] * 0.5], [c[0] * 0.38, 0, c[2] * 0.3],
                                                       [-c[0] * 0.12, 0, c[2] * 0.2])
        else:
            p['cape'], p['cape_mid'], p['cape_low'] = ([c[0] * 0.55, c[1], c[2] * 0.5], [c[0] * 0.3, 0, c[2] * 0.3],
                                                       [c[0] * 0.15, 0, c[2] * 0.2])
    p['ghost_trail_scale'] = list(p.get('ghost_hand_scale', ONE))
    return p


def lerp(a, b, k):
    return EA.lerp_pose(a, b, k)


def anim(length, keys, timeline=None, loop=False):
    return EA.anim(length, keys, timeline, loop)


def idle_pose(t):
    """Поза покоя в момент t (петля 4 с): дыхание, перенос веса, рука парит (±0.6), пальцы медленно перебирают, накидка колышется."""
    ph = math.sin(t * math.pi / 2)
    ph2 = math.sin(t * math.pi / 2 + 1.1)
    body = EA.mod(STAND, torso=[-1.5 * abs(ph), 0, 0], body_pos=[0, 0.12 * abs(ph), 0], head=[-3 + 1.5 * ph, 8 + 4 * ph, 0],
                  coat_front_r=[-3, 0, 2 + 1.2 * ph], coat_front_l=[2, 0, -2 + 1.2 * ph], coat_back_r=[1.5 * ph, 0, 1.0 * ph],
                  coat_back_l=[1.5 * ph, 0, 1.0 * ph], right_arm=[-14 + 2 * ph, 12, 7], cape=[2.4 + 0.8 * ph2, 0, 0.4 * ph],
                  cape_mid=[1.2 + 1.0 * math.sin(t * math.pi / 2 + 1.9), 0, 0.3 * ph2], cape_low=[0.6 + 1.2 * math.sin(t * math.pi / 2 + 2.7), 0, 0.3 * ph])
    gh = hand(pos=(0, 0.6 * ph2, 0), rot=(14 + 2 * ph, -18 + 3 * ph2, -6 + 2 * ph), curl=0.22 + 0.06 * ph2, ripple=0.08 * ph, thumb=0.15)
    return full(body, gh)


IDLE0 = idle_pose(0)


def build():
    an = {}
    # ---------------------------------------------------------------- покой (4 с, петля)
    an['ereb_hand_idle'] = anim(4.0, [(i * 0.5, idle_pose(i * 0.5), IO) for i in range(9)], loop=True)
    # поза покоя (2 с, петля, без колыхания рук — для ожидания вне боя / заставки)
    still = full(STAND, hand(pos=(0, -0.5, 0.5), rot=(18, -18, -6), curl=0.35, thumb=0.3))
    an['ereb_hand_rest'] = anim(2.0, [(0, still), (1.0, full(EA.mod(STAND, torso=[-1, 0, 0]), hand(pos=(0, -0.2, 0.5), rot=(18, -18, -6),
                                                                                                   curl=0.38, thumb=0.3)), IO), (2.0, still, IO)],
                                loop=True)
    # ---------------------------------------------------------------- шаг (1.2 с, петля): полы и накидка следуют за ногами
    keys = []
    for i in range(9):
        t = i * 0.15
        s = math.sin(i * math.pi / 4)
        c = math.sin(i * math.pi / 4 - 0.6)
        body = EA.mod(STAND, right_leg=[-26 * s, 0, 2], left_leg=[26 * s, 0, -2], body_pos=[0, -0.35 * abs(math.cos(i * math.pi / 4)), 0],
                      right_arm=[-14 + 6 * s, 12, 7], bipedHandRight=[40, 0, 0], left_arm=[-10 - 8 * s, -6, -8], head=[-3, 4, 0], torso=[2, 0, 0],
                      coat_front_r=[-6 - 14 * max(0, c), 0, 3], coat_front_l=[-6 - 14 * max(0, -c), 0, -3],
                      coat_back_r=[6 + 10 * max(0, -c), 0, 2], coat_back_l=[6 + 10 * max(0, c), 0, -2], cape=[12 + 5 * abs(c), 0, 1.5 * s])
        keys.append((t, full(body, hand(pos=(0, 0.5 * math.cos(i * math.pi / 4), 0.6), rot=(18, -18, -6 + 2 * s), curl=0.25)), LIN))
    an['ereb_hand_walk'] = anim(1.2, keys, loop=True)
    # ---------------------------------------------------------------- фехтование (позы T30; рука держится над плечом, чуть впереди)
    HG = hand(pos=(1, -1, -2), rot=(24, -10, -4), curl=0.3, thumb=0.2)
    HG_back = hand(pos=(1, 1, 1), rot=(8, -14, -6), curl=0.25)
    guard = full(GUARD, HG)
    an['ereb_hand_guard'] = anim(1.0, [(0, guard), (0.5, full(EA.mod(GUARD, body_pos=[0, -1.4, 0]), HG), IO), (1.0, guard, IO)], loop=True)
    # прежние позы выпада — ими пользуются reflection_strike / false_retreat_strike / build_spells2 (не входят в перенос)
    pre = full(EA.mod(GUARD, body_pos=[0, -1.8, 2], right_arm=[-70, 40, 10], bipedHandRight=[70, 0, 0]), HG_back)
    lunge = full(LUNGE, hand(pos=(2, -2, 2), rot=(10, -6, -4), curl=0.4))
    # ---- выпад и серия — по эталону Epic Fight (21.11; тики прежние: LUNGE_HIT 10, FLURRY_HITS 9/16/23), как у T30 (gen_ereb_anims):
    # сжатие с весом на задней ноге → взвод → укол без остановки на ключах (пик скорости у hit) → перехлёст → отшаг; призрачная рука
    # отстаёт от тела (сзади на оттяжке, догоняет после укола)
    coil = full(EA.mod(GUARD, body=[2, -30, 0], body_pos=[0, -2.0, 2.6], right_arm=[-58, 44, 14], bipedHandRight=[66, 0, 0],
                       right_leg=[-12, 30, 2], left_leg=[22, 18, -8], left_arm=[-100, -10, -46], coat_front_r=[6, 0, 6]), HG_back)
    load = full(EA.mod(GUARD, body=[2, -30, 0], body_pos=[0, -2.2, 3.0], right_arm=[-56, 46, 15], bipedHandRight=[66, 0, 0],
                       right_leg=[-8, 30, 2], left_leg=[22, 18, -8], left_arm=[-110, -10, -46], coat_front_r=[8, 0, 8]),
                hand(pos=(1, 1.5, 2), rot=(6, -14, -6), curl=0.25))
    ext = full(EA.mod(LUNGE, body=[12, -50, 0], body_pos=[0, -2.8, -10.5], right_arm=[-92, 40, 0], bipedHandRight=[90, 0, 0],
                      right_leg=[-70, 34, 0], left_leg=[42, 20, -10], left_arm=[-50, -10, -100], cape=[36, 0, 0]),
               hand(pos=(2, -1, 4), rot=(8, -6, -4), curl=0.4))
    rec = lerp(ext, full(EA.mod(LUNGE, body=[12, -50, 0], body_pos=[0, -2.6, -9.6], right_arm=[-88, 40, 2], bipedHandRight=[90, 0, 0],
                                right_leg=[-70, 34, 0], left_leg=[42, 20, -10], left_arm=[-50, -10, -100], cape=[30, 0, 0]),
                         hand(pos=(2, -2, 2), rot=(10, -6, -4), curl=0.4)), 1.0)
    step_back = full(EA.mod(GUARD, body_pos=[0, -1.6, -4.0], right_leg=[-30, 30, 2]), HG)
    an['ereb_hand_lunge'] = anim(1.6, [(0, IDLE0), (0.28, coil, IO), (0.37, load, LIN), (0.44, lerp(load, ext, 0.35), 'easeInQuad'),
                                       (0.505, ext, LIN), (0.6, rec, 'easeOutQuad'), (0.8, rec), (1.1, step_back, IO), (1.6, IDLE0, IO)],
                                 [(0.5, 'hit')])

    def strike(body, gh_curl):
        return full(body, hand(pos=(2, -2, 3), rot=(10, -6, -4), curl=gh_curl))
    a1 = strike(EA.mod(LUNGE, body=[10, -48, 0], right_arm=[-104, 36, 0], body_pos=[0, -2.6, -5], bipedHandRight=[92, 0, 0],
                       right_leg=[-52, 34, 0], left_leg=[34, 20, -9]), 0.4)
    a2 = strike(EA.mod(LUNGE, body=[12, -50, 0], right_arm=[-88, 44, 4], body_pos=[0, -3.0, -7], right_leg=[-60, 34, 0], left_leg=[38, 20, -10]), 0.45)
    a3 = strike(EA.mod(LUNGE, right_arm=[-72, 40, -6], bipedHandRight=[70, 0, 0], body=[22, -54, 0], body_pos=[0, -3.6, -9],
                       right_leg=[-68, 34, 0], left_leg=[42, 20, -10], cape=[40, 0, 0]), 0.5)
    b1 = full(EA.mod(GUARD, body=[0, -24, 0], body_pos=[0, -1.8, 2.6], right_arm=[-40, 40, 18], bipedHandRight=[56, 0, 0], left_arm=[-100, -10, -40]), HG_back)
    b2 = full(EA.mod(GUARD, body=[2, -26, 0], body_pos=[0, -2.2, -0.5], right_arm=[-42, 42, 18], bipedHandRight=[56, 0, 0],
                     right_leg=[-30, 32, 2], left_leg=[26, 18, -8]), HG_back)
    b3 = full(EA.mod(GUARD, body=[4, -26, 0], body_pos=[0, -2.4, -2.5], right_arm=[-40, 40, 16], bipedHandRight=[54, 0, 0],
                     right_leg=[-40, 32, 2], left_leg=[30, 18, -8]), HG_back)
    over = lambda a, dz: dict(a, body_pos=[0, a['body_pos'][1], dz])          # перехлёст: таз догоняет вперёд
    an['ereb_hand_flurry'] = anim(2.3, [
        (0, IDLE0), (0.32, b1, IO), (0.40, lerp(b1, a1, 0.35), 'easeInQuad'), (0.455, a1, LIN), (0.52, over(a1, -4.6), 'easeOutQuad'),
        (0.68, b2, IO), (0.75, lerp(b2, a2, 0.35), 'easeInQuad'), (0.805, a2, LIN), (0.87, over(a2, -6.6), 'easeOutQuad'),
        (1.03, b3, IO), (1.10, lerp(b3, a3, 0.35), 'easeInQuad'), (1.155, a3, LIN), (1.24, over(a3, -8.4), 'easeOutQuad'),
        (1.45, a3), (1.8, step_back, IO), (2.3, IDLE0, IO)], [(0.45, 'hit'), (0.8, 'hit'), (1.15, 'hit')])
    # ---------------------------------------------------------------- удар рукой по площади (1.8 с): замах вверх, удар ладонью о землю ВПЕРЕДИ
    # (slam 0.8 — центр удара ≈ 1.6 бл. перед Эребом, см. письмо), рука лежит, возвращается
    point = EA.mod(STAND, left_arm=[-70, 10, -10], head=[8, 0, 0], torso=[4, 0, 0], body=[4, 0, 0], bipedHandRight=[38, 0, 0])
    wind = full(EA.mod(STAND, head=[-14, 10, 0], torso=[-6, 0, 0], left_arm=[-30, -6, -14], cape=[2, 0, 0]),
                hand(pos=(3, 8, 3), rot=(-12, -14, 4), curl=0.0, spread=1.0, thumb=0.0))
    over = full(EA.mod(point, cape=[10, 0, 0]), hand(pos=(6, 4, -12), rot=(48, -4, 8), curl=0.05, spread=0.8, thumb=0.0))
    slam = full(EA.mod(point, body_pos=[0, -0.8, 0], cape=[12, 0, 0], left_arm=[-60, 10, -10]),
                hand(pos=(6, -27.5, -15), rot=(90, 0, 4), curl=0.08, spread=0.7, thumb=0.0))
    slam2 = full(EA.mod(point, body_pos=[0, -0.6, 0], cape=[10, 0, 0], left_arm=[-60, 10, -10]),
                 hand(pos=(6, -26.5, -15), rot=(86, 0, 4), curl=0.15, spread=0.6, thumb=0.0))
    lift = full(STAND, hand(pos=(1, -4, -13), rot=(40, -8, 0), curl=0.2, spread=0.3))
    lift2 = full(STAND, hand(pos=(-2, 1, -5), rot=(24, -14, -4), curl=0.2, spread=0.2))
    # эталон Epic Fight (21.11; тики прежние: SLAM_RAISE 9, SLAM_HIT 16): замах 0–0.45 (тело вправо 20°, отклон назад, рука высоко сзади),
    # взвод до 0.60 (рука выше, пальцы раскрываются), удар 0.60–0.80 (тело доворачивается и наклоняется в удар, левая нога шагает, ладонь
    # разгоняется сверху вперёд-вниз), жёсткий стоп о землю с отскоком, ладонь лежит до 1.2, поднимается, покой к 2.0
    wind2 = full(EA.mod(STAND, body=[-6, 20, 0], head=[-16, -12, 0], torso=[-8, 0, 0], left_arm=[-36, -6, -16], cape=[6, 0, 0],
                        right_leg=[6, -14, 3], left_leg=[-2, -14, -4]),
                 hand(pos=(4, 12, 6), rot=(-20, -14, 6), curl=0.0, spread=1.0, thumb=0.0))
    load2 = full(EA.mod(STAND, body=[-8, 22, 0], head=[-18, -12, 0], torso=[-9, 0, 0], left_arm=[-38, -6, -16], cape=[6, 0, 0],
                        right_leg=[4, -14, 3], left_leg=[-6, -14, -4]),
                 hand(pos=(4, 13.5, 7), rot=(-26, -14, 6), curl=0.0, spread=1.1, thumb=0.0))
    slam_b = EA.mod(point, body=[12, -6, 0], body_pos=[0, -1.4, -2.0], cape=[14, 0, 0], left_arm=[-60, 10, -10],
                    right_arm=[-26, 12, 10], bipedHandRight=[16, 0, 0],
                    right_leg=[10, 4, 3], left_leg=[-26, 4, -4])
    slam = full(slam_b, hand(pos=(6, -27.5, -15), rot=(90, 0, 4), curl=0.08, spread=0.7, thumb=0.0))
    bounce = full(EA.mod(slam_b, body_pos=[0, -1.2, -2.0]), hand(pos=(6, -25.0, -15), rot=(82, 0, 4), curl=0.12, spread=0.65, thumb=0.0))
    slam2 = full(EA.mod(slam_b, body_pos=[0, -1.3, -2.0]), hand(pos=(6, -26.5, -15), rot=(86, 0, 4), curl=0.15, spread=0.6, thumb=0.0))
    lift = full(EA.mod(STAND, body_pos=[0, -0.4, -1.0], left_leg=[-12, 0, -4]), hand(pos=(1, -4, -13), rot=(40, -8, 0), curl=0.2, spread=0.3))
    an['ereb_hand_slam'] = anim(2.0, [(0, IDLE0), (0.45, wind2, OC), (0.60, load2, LIN), (0.72, lerp(load2, slam, 0.4), 'easeInQuad'),
                                      (0.80, slam, LIN), (0.86, bounce, 'easeOutQuad'), (0.93, slam2, 'easeInQuad'), (1.2, slam2),
                                      (1.5, lift, IO), (1.75, full(STAND, hand(pos=(-2, 1, -5), rot=(24, -14, -4), curl=0.2, spread=0.2)), IO),
                                      (2.0, IDLE0, IO)], [(0.45, 'raise'), (0.8, 'slam')])
    # ---------------------------------------------------------------- хватка: тянется вперёд (grab 0.6), держит, сжимает, отпускает
    reach_b = EA.mod(STAND, left_arm=[-40, 6, -12], head=[4, 0, 0], torso=[3, 0, 0])
    reach = full(reach_b, hand(pos=(7, -11, -25), rot=(8, -2, 4), curl=0.0, spread=1.0, thumb=0.0))
    reach_pre = full(reach_b, hand(pos=(2, -8, -12), rot=(24, -6, 0), curl=0.0, spread=0.9, thumb=0.0))
    HOLD_H = hand(pos=(7, 2, -24), rot=(4, -2, 4), curl=0.78, spread=0.0, thumb=0.8)
    hold_b = EA.mod(STAND, left_arm=[-26, 4, -12], head=[-6, 0, 0], torso=[-2, 0, 0], cape=[5, 0, 0])
    HOLD = full(hold_b, HOLD_H)
    closed = full(reach_b, hand(pos=(7, -10, -25), rot=(6, -2, 4), curl=0.8, spread=0.0, thumb=0.8))
    an['ereb_hand_grab'] = anim(1.2, [(0, IDLE0), (0.3, reach_pre, IO), (0.5, reach, OC), (0.62, closed, OQ), (0.9, lerp(closed, HOLD, 0.5), IO),
                                      (1.2, HOLD, IO)], [(0.6, 'grab')])
    hold2 = full(EA.mod(hold_b, head=[-4, 4, 0]), hand(pos=(7, 2.6, -24), rot=(4, -2, 6), curl=0.8, thumb=0.8))
    an['ereb_hand_grab_hold'] = anim(2.0, [(0, HOLD), (1.0, hold2, IO), (2.0, HOLD, IO)], loop=True)
    sq = full(EA.mod(hold_b, left_arm=[-60, 20, -30], bipedHandLeft=Z3, head=[-10, 6, 0], torso=[-4, 0, 0]),
              hand(pos=(7, 3, -23), rot=(4, -2, 4), curl=1.0, thumb=1.0, wrist=(0, 0, 4)))
    sq2 = full(EA.mod(hold_b, left_arm=[-62, 22, -32], head=[-10, 6, 0], torso=[-4, 0, 0]),
               hand(pos=(7, 3, -23), rot=(4, -2, 4), curl=1.05, thumb=1.0, wrist=(0, 0, -3)))
    an['ereb_hand_squeeze'] = anim(1.2, [(0, HOLD), (0.3, sq, IQ), (0.45, sq2, LIN), (0.6, sq, LIN), (0.8, sq), (1.2, HOLD, IO)], [(0.35, 'squeeze')])
    opened = full(hold_b, hand(pos=(7, 1, -24), rot=(6, -2, 4), curl=0.0, spread=1.0, thumb=0.0))
    an['ereb_hand_grab_release'] = anim(1.0, [(0, HOLD), (0.2, opened, OQ), (0.5, full(STAND, hand(pos=(1, -6, -12), rot=(30, -10, 0), curl=0.1, spread=0.5)), IO), (0.75, full(STAND, hand(pos=(-2, 0, -5), rot=(22, -14, -4), curl=0.2)), IO), (1.0, IDLE0, IO)], [(0.2, 'release')])
    # ---------------------------------------------------------------- каст (1.4 с): «Длань» вверх, щелчок пальцами перчатки (cast 0.75);
    # призрачная рука вторит жесту — раскрывается над плечом
    cast_h = hand(pos=(3, 5, 1), rot=(-6, -22, 4), curl=0.0, spread=1.0, thumb=0.0)
    an['ereb_hand_cast'] = anim(1.4, [(0, IDLE0), (0.45, full(CAST, cast_h), IO), (0.7, full(EA.mod(CAST, left_arm=[-174, 0, -32], head=[-8, -12, 0]),
                                                                                          hand(pos=(3, 6, 1), rot=(-8, -22, 4), curl=0.0, spread=1.1, thumb=0.0)), IO),
                                      (0.78, full(EA.mod(CAST, left_arm=[-160, 0, -40]), hand(pos=(3, 5, 1), rot=(-4, -22, 4), curl=0.3, spread=0.6)), OQ),
                                      (1.0, full(CAST, cast_h)), (1.4, IDLE0, IO)], [(0.75, 'cast')])
    # ---------------------------------------------------------------- появление (5.5 с): собирается из стекла и бабочек — сначала рука
    # (form_hand 0.6), потом он (form 1.8: модель видна); поклон (bow 2.6), рука раскрывается к игрокам, салют рапирой (salute 3.4),
    # «Вот мы и снова встретились» (speak 4.3), стойка (ready 5.5)
    h0 = hand(pos=(0, 6, 0), rot=(14, -18, -6), curl=0.0, spread=0.6, thumb=0.0, scale=0.02)
    hf = hand(pos=(0, 4, 0), rot=(10, -18, -6), curl=0.0, spread=0.8, thumb=0.0, scale=1.0)
    small = EA.mod(STAND, body_scale=[0.9, 0.9, 0.9])
    bow = full(BOW, hand(pos=(0, -2, 2), rot=(30, -18, -6), curl=0.35, thumb=0.3))
    sal = full(SALUTE, hand(pos=(2, 2, -1), rot=(18, -26, -2), curl=0.1, spread=0.5, thumb=0.1))
    speak = full(EA.mod(STAND, head=[-4, 4, 0], left_arm=[-34, 20, -26], bipedHandLeft=Z3),
                 hand(pos=(-1, 1, -8), rot=(30, -26, -4), curl=0.05, spread=0.6, thumb=0.0))
    speak2 = full(EA.mod(STAND, head=[-6, 2, 0], left_arm=[-30, 18, -24]), hand(pos=(-1, 0.5, -8), rot=(28, -26, -4), curl=0.1, spread=0.5))
    an['ereb_hand_spawn'] = anim(5.5, [(0, full(small, h0)), (0.6, full(small, h0)), (1.4, full(small, hf), OC), (1.8, full(small, hf)),
                                       (2.2, full(STAND, hf), OC), (2.6, bow, IO), (3.0, bow), (3.4, sal, IO), (3.9, sal), (4.3, speak, IO),
                                       (5.0, speak2, IO), (5.5, IDLE0, IO)],
                                 [(0.6, 'form_hand'), (1.8, 'form'), (2.6, 'bow'), (3.4, 'salute'), (4.3, 'speak'), (5.5, 'ready')])
    # ---------------------------------------------------------------- переход в фазу 2 (66%, 1.6 с): рука сжимается в кулак и бьёт в землю рядом
    fist_up = full(EA.mod(SALUTE, head=[-10, 0, 0], right_arm=[-62, 40, 12], bipedHandRight=[40, 0, 0]), hand(pos=(2, 7, 2), rot=(-8, -14, 0), curl=1.0, thumb=1.0))
    fist_dn = full(EA.mod(SALUTE, body_pos=[0, -0.6, 0], head=[10, 6, 0], cape=[10, 0, 0], right_arm=[-34, 22, 24], bipedHandRight=[50, 0, 0]), hand(pos=(-1, -21, -15), rot=(46, -10, -4), curl=1.0, thumb=1.0))
    an['ereb_hand_phase2'] = anim(1.6, [(0, IDLE0), (0.45, fist_up, IO), (0.6, fist_up), (0.8, fist_dn, IC), (1.0, fist_dn), (1.25, full(STAND, hand(pos=(-3, -8, -10), rot=(34, -12, -6), curl=0.6, thumb=0.5)), IO), (1.6, IDLE0, IO)],
                                  [(0.8, 'phase')])
    # ---------------------------------------------------------------- переход в фазу 3 (33%, 2.0 с): ладонь «Длани» к маске (0.6), маска
    # трескается (crack 0.9: текстура → ereb_hand_cracked), голова дёргается, рука вздрагивает и раскрывается
    face = full(EA.mod(STAND, left_arm=[-128, 42, 0], head=[6, 8, 0], torso=[3, 0, 0]), hand(pos=(0, 1, 1), rot=(16, -18, -6), curl=0.6, thumb=0.5))
    jerk = full(EA.mod(STAND, left_arm=[-100, 20, -20], head=[-16, -10, 6], torso=[-6, 0, 0], body_pos=[0, 0, 1]),
                hand(pos=(1, 4, 2), rot=(-6, -24, -4), curl=0.0, spread=1.2, thumb=0.0))
    an['ereb_hand_phase3'] = anim(2.0, [(0, IDLE0), (0.6, face, IO), (0.85, face), (0.95, jerk, OQ), (1.3, jerk), (2.0, IDLE0, IO)],
                                  [(0.9, 'crack')])
    # ---------------------------------------------------------------- «Длань Лжи» (66%, особая, 3.0 с): «Длань» к небу, рука улетает вверх
    # (rise 0.3; gone 0.9 — рука уменьшилась до нуля), descend 1.2 — код: огромная рука опускается с неба (fx), держит позу,
    # return 2.4 — рука возвращается над плечом
    sky_b = EA.mod(STAND, left_arm=[-172, 6, -10], head=[-28, 0, 0], torso=[-6, 0, 0], right_arm=[-10, 12, 10], bipedHandRight=[42, 0, 0], cape=[2, 0, 0])
    up1 = full(sky_b, hand(pos=(2, 14, 1), rot=(-10, -18, 0), curl=0.0, spread=1.0, thumb=0.0))
    up2 = full(sky_b, hand(pos=(3, 60, 2), rot=(-10, -18, 0), curl=0.0, spread=1.0, thumb=0.0, scale=0.02))
    hold_sky = full(EA.mod(sky_b, head=[-24, 6, 0]), hand(pos=(0, 6, 0), rot=(14, -18, -6), curl=0.0, spread=0.6, thumb=0.0, scale=0.02))
    down = full(EA.mod(STAND, left_arm=[-80, 30, -10], head=[10, 10, 0]), hand(pos=(0, 6, 0), rot=(14, -18, -6), curl=0.0, spread=0.6, thumb=0.0,
                                                                              scale=0.02))
    an['ereb_hand_hand_of_lies'] = anim(3.2, [(0, IDLE0), (0.5, up1, IO), (0.95, up2, IC), (1.2, lerp(up2, hold_sky, 1.0), IO), (2.2, hold_sky),
                                              (2.4, down, IO), (2.9, full(STAND, hand(pos=(0, 2, 0), curl=0.0, spread=0.5, thumb=0.0)), OC),
                                              (3.2, IDLE0, IO)],
                                        [(0.5, 'rise'), (0.95, 'gone'), (1.2, 'descend'), (2.4, 'return')])
    # ---------------------------------------------------------------- «Падение маски» (45%, 2.2 с): «Длань» берётся за маску (grip 0.5),
    # срывает и отбрасывает вверх-вперёд (tear 0.85), маска разлетается осколками (shatter 1.1: код — fx осколков, кость mask скрыть
    # до ereb_hand_mask_return), рука раскрыта к игрокам
    grip = full(EA.mod(STAND, left_arm=[-132, 46, 2], head=[4, 8, 0], torso=[2, 0, 0]), hand(pos=(1, 2, 1), rot=(10, -20, -6), curl=0.5, thumb=0.4))
    tear_b = EA.mod(STAND, left_arm=[-150, -10, -40], head=[-12, -8, 0], torso=[-4, 0, 0], body_pos=[0, 0, 0.5])
    tear = full(tear_b, hand(pos=(2, 5, 1), rot=(-4, -22, 0), curl=0.0, spread=1.1, thumb=0.0),
                mask=[-30, 20, 0], mask_pos=[3, 6, -6])
    flung = full(tear_b, hand(pos=(2, 5, 1), rot=(-4, -22, 0), curl=0.0, spread=1.1, thumb=0.0),
                 mask=[-60, 40, 10], mask_pos=[5, 12, -10], mask_scale=[0.02, 0.02, 0.02])
    an['ereb_hand_mask_fall'] = anim(2.2, [(0, IDLE0), (0.45, grip, IO), (0.55, grip), (0.85, tear, OQ), (1.1, flung, IC),
                                           (1.5, full(tear_b, hand(pos=(2, 4, 1), rot=(0, -22, 0), curl=0.1, spread=0.8), mask_scale=[0.02] * 3)),
                                           (2.2, full(STAND, HOVER, mask_scale=[0.02] * 3), IO)],
                                     [(0.5, 'grip'), (0.85, 'tear'), (1.1, 'shatter')])
    # возвращение маски (1.4 с): осколки летят обратно (код: fx), рука проводит над лицом, mend 0.7 — маска снова на лице
    # (кость mask показать, текстура → ereb_hand_mended)
    pass_ = full(EA.mod(STAND, left_arm=[-120, 40, 0], head=[4, 6, 0]), hand(pos=(0, 2, 0), rot=(12, -18, -6), curl=0.3), mask_scale=[0.02] * 3)
    pass2 = full(EA.mod(STAND, left_arm=[-112, 16, -16], head=[0, 2, 0]), hand(pos=(0, 1, 0), rot=(12, -18, -6), curl=0.3))
    an['ereb_hand_mask_return'] = anim(1.4, [(0, full(STAND, HOVER, mask_scale=[0.02] * 3)), (0.5, pass_, IO), (0.68, pass_),
                                             (0.7, pass2, LIN), (1.0, pass2, IO), (1.4, IDLE0, IO)], [(0.7, 'mend')])
    # ---------------------------------------------------------------- «Сон Бабочки: Полное Раскрытие» (20%, 4.0 с): руки в стороны,
    # призрачная рука поднимается над головой и раскрывается (open 1.4), каст (cast 2.6 — код запускает заклинание), стойка
    spread_b = EA.mod(STAND, left_arm=[-30, 0, -70], right_arm=[-30, 0, 66], bipedHandRight=[30, 0, 0], head=[-12, 0, 0], torso=[-6, 0, 0],
                      body_pos=[0, 0.4, 0], cape=[8, 0, 0])
    high = hand(pos=(10, 14, 3), rot=(-4, -40, 18), curl=0.3, thumb=0.3)
    openh = hand(pos=(11, 18, 3), rot=(-14, -44, 22), curl=0.0, spread=1.3, thumb=0.0)
    castp = full(EA.mod(spread_b, left_arm=[-176, 0, -18], right_arm=[-24, 0, 52], bipedHandRight=[36, 0, 0], head=[-30, 0, 0]),
                 hand(pos=(11, 20, 3), rot=(-18, -44, 22), curl=0.0, spread=1.4, thumb=0.0))
    an['ereb_hand_full_reveal'] = anim(4.0, [(0, IDLE0), (0.8, full(spread_b, high), IO), (1.4, full(spread_b, openh), OC), (1.9, full(spread_b, openh)),
                                             (2.6, castp, IO), (3.3, castp), (4.0, IDLE0, IO)],
                                       [(0.8, 'butterflies'), (1.4, 'open'), (2.6, 'cast')])
    # ---------------------------------------------------------------- ложная смерть (5.0 с): шатается (0.4), рука трескается и тает
    # (hand_break 0.7), выпрямляется, «А вы...стали сильнее» (speak 1.6), лёгкая улыбка-поклон (smile 2.6), распадается бабочками
    # (vanish 3.8: код — fx бабочек, модель скрыть, полоса исчезает)
    stag = full(EA.mod(STAND, body=[8, 0, -4], body_pos=[0, -1.2, 1.5], head=[16, -6, 0], torso=[8, 0, 0], right_arm=[-4, 12, 16], bipedHandRight=[10, 0, 0],
                       left_arm=[-30, -6, -20], right_leg=[-12, 0, 4], left_leg=[14, 0, -4], cape=[-2, 0, 0]),
                hand(pos=(0, -3, 2), rot=(30, -18, -10), curl=0.6, thumb=0.5))
    broke = full(EA.mod(STAND, body=[4, 0, -2], body_pos=[0, -0.6, 1], head=[10, -2, 0], right_arm=[0, 12, 10], bipedHandRight=[30, 0, 0],
                        left_arm=[-20, -6, -14], cape=[2, 0, 0]),
                 hand(pos=(0, -6, 3), rot=(40, -18, -12), curl=0.8, thumb=0.7, scale=0.02))
    up = full(EA.mod(STAND, head=[-6, 4, 0], left_arm=[-24, 10, -16], right_arm=[-6, 12, 8], bipedHandRight=[40, 0, 0]),
              hand(pos=(0, -6, 3), curl=0.8, scale=0.02))
    talk = full(EA.mod(STAND, head=[-4, 6, 0], left_arm=[-44, 24, -24], right_arm=[-6, 12, 8], bipedHandRight=[40, 0, 0]),
                hand(pos=(0, -6, 3), curl=0.8, scale=0.02))
    bow2 = full(EA.mod(STAND, body=[14, 0, 0], head=[10, 0, 0], left_arm=[-60, 30, -6], right_arm=[-20, 12, 6], bipedHandRight=[28, 0, 0],
                       coat_front_r=[-14, 0, 2], coat_front_l=[-14, 0, -2], cape=[10, 0, 0]),
                hand(pos=(0, -6, 3), curl=0.8, scale=0.02))
    an['ereb_hand_false_death'] = anim(5.0, [(0, IDLE0), (0.4, stag, OQ), (0.7, broke, IO), (1.2, up, IO), (1.6, talk, IO), (2.4, talk),
                                             (2.9, bow2, IO), (3.6, bow2), (3.8, full(EA.mod(STAND, body_scale=[1.03, 1.03, 1.03]),
                                                                                       hand(curl=0.8, scale=0.02)), IO),
                                             (5.0, full(EA.mod(STAND, body_scale=[1.03, 1.03, 1.03]), hand(curl=0.8, scale=0.02)))],
                                       [(0.4, 'stagger'), (0.7, 'hand_break'), (1.6, 'speak'), (2.6, 'smile'), (3.8, 'vanish')])
    # ---------------------------------------------------------------- добивание (3.6 с): хватает (grab 0.6), поднимает, сжимает (squeeze 1.5),
    # жертва трескается стеклом (shatter 2.1: код — fx стекла и бабочек, урон ereb_hand_finisher), рука раскрывается (release 2.4)
    lift_h = hand(pos=(7, 5, -22), rot=(0, -2, 4), curl=0.82, thumb=0.85)
    crush = hand(pos=(7, 6, -21), rot=(-2, -2, 4), curl=1.08, thumb=1.0, wrist=(0, 0, 5))
    look = EA.mod(STAND, head=[-14, 4, 0], left_arm=[-40, 20, -20], torso=[-3, 0, 0])
    an['ereb_hand_finisher'] = anim(3.6, [(0, IDLE0), (0.3, reach_pre, IO), (0.5, reach, OC), (0.62, closed, OQ), (1.2, full(look, lift_h), IO),
                                          (1.5, full(EA.mod(look, left_arm=[-70, 24, -30]), crush), IQ), (1.8, full(EA.mod(look, left_arm=[-72, 26, -32]),
                                                                                                                   hand(pos=(7, 6, -21), rot=(-2, -2, 4), curl=1.1,
                                                                                                                        thumb=1.0, wrist=(0, 0, -4))), LIN),
                                          (2.1, full(EA.mod(look, left_arm=[-70, 24, -30]), crush), LIN),
                                          (2.4, full(look, hand(pos=(7, 6, -22), rot=(0, -2, 4), curl=0.0, spread=1.2, thumb=0.0)), OQ),
                                          (2.9, full(look, hand(pos=(4, 0, -10), rot=(12, -10, 0), curl=0.2, spread=0.6)), IO), (3.6, IDLE0, IO)],
                                    [(0.6, 'grab'), (1.5, 'squeeze'), (2.1, 'shatter'), (2.4, 'release')])
    # ---------------------------------------------------------------- «Реплика» (2.3 с): рука хватает печать над ним (snap 0.55 — как у T30,
    # fx ereb_replica_break), сминает (break 0.95), «Ложь во лжи — становится правдой сама по себе» (speak 1.55)
    rb_up = full(EA.mod(STAND, head=[-24, 0, 0], torso=[-4, 0, 0], left_arm=[-40, 0, -20]), hand(pos=(6, 10, -6), rot=(-20, -10, 10), curl=0.0, spread=1.2,
                                                                                                   thumb=0.0))
    rb_grip = full(EA.mod(STAND, head=[-24, 0, 0], torso=[-4, 0, 0], left_arm=[-40, 0, -20]), hand(pos=(6, 11, -7), rot=(-20, -10, 10), curl=0.95,
                                                                                                     thumb=0.9))
    rb_crush = full(EA.mod(STAND, head=[-18, 4, 0], torso=[-3, 0, 0], left_arm=[-36, 0, -18]), hand(pos=(5, 8, -5), rot=(-10, -10, 6), curl=1.1, thumb=1.0,
                                                                                                      wrist=(0, 0, 6)))
    rb_talk = full(EA.mod(STAND, head=[-2, 6, 0], left_arm=[-46, 22, -26]), hand(pos=(3, 2, -2), rot=(10, -18, -4), curl=0.0, spread=0.9, thumb=0.0))
    an['ereb_hand_replica_break'] = anim(2.3, [(0, IDLE0), (0.4, rb_up, IO), (0.55, rb_grip, OQ), (0.8, rb_grip), (0.95, rb_crush, IQ), (1.2, rb_crush),
                                               (1.55, rb_talk, IO), (1.95, rb_talk), (2.3, IDLE0, IO)],
                                         [(0.55, 'snap'), (0.95, 'break'), (1.55, 'speak')])
    # ================================================================ +4 заклинания (владелец 20.11: приняты как предложено)
    # «Ложное пламя» (1.6 с): «Длань» проводит над землёй дугу перед собой, рука прижимает воздух ладонью вниз — на земле загораются
    # 5 кругов (marks 0.6: код ставит круги, fx ereb_hand_false_flame_real/decoy), вспышка огня (ignite 1.0)
    ff_a = full(EA.mod(STAND, left_arm=[-50, 40, -10], head=[10, 10, 0], torso=[4, 0, 0], body=[0, 10, 0]),
                hand(pos=(2, 4, -4), rot=(40, -10, 0), curl=0.0, spread=0.8, thumb=0.0))
    ff_b = full(EA.mod(STAND, left_arm=[-60, -20, -40], head=[14, -10, 0], torso=[6, 0, 0], body=[0, -12, 0], body_pos=[0, -0.4, 0]),
                hand(pos=(3, -6, -10), rot=(78, -6, 2), curl=0.05, spread=1.0, thumb=0.0))
    an['ereb_hand_false_flame'] = anim(1.6, [(0, IDLE0), (0.35, ff_a, IO), (0.6, ff_b, OQ), (1.0, ff_b), (1.3, full(STAND, hand(pos=(-2, -2, -8), rot=(40, -14, -6), curl=0.2)), IO), (1.6, IDLE0, IO)],
                                       [(0.6, 'marks'), (1.0, 'ignite')])
    # «Стеклянная хватка» (2.0 с): warn 0.0 — конус-предупреждение перед ним (1 с, fx ereb_hand_glass_grip_warn), рука отводится назад
    # раскрытой, на grip 1.0 — бросок вперёд и сжатие кулака в 2 бл. перед ним (урон и притяжение — код), отпускает
    gg_back = full(EA.mod(STAND, left_arm=[-30, 10, -20], head=[2, 0, 0]), hand(pos=(1, 6, 4), rot=(-10, -20, 0), curl=0.0, spread=1.2, thumb=0.0))
    gg_fwd = full(EA.mod(STAND, left_arm=[-70, 20, -16], head=[6, 0, 0], torso=[5, 0, 0], body_pos=[0, -0.4, -0.5]),
                  hand(pos=(8, -10, -22), rot=(20, -2, 4), curl=0.0, spread=1.1, thumb=0.0))
    gg_fist = full(EA.mod(STAND, left_arm=[-70, 22, -18], head=[6, 0, 0], torso=[5, 0, 0], body_pos=[0, -0.4, -0.5]),
                   hand(pos=(8, -10, -21), rot=(20, -2, 4), curl=1.05, thumb=1.0, wrist=(0, 0, 4)))
    an['ereb_hand_glass_grip'] = anim(2.0, [(0, IDLE0), (0.6, gg_back, IO), (0.85, gg_back), (1.0, gg_fwd, IC), (1.08, gg_fist, OQ), (1.4, gg_fist),
                                            (1.7, full(STAND, hand(pos=(2, -2, -8), rot=(30, -10, 0), curl=0.5, thumb=0.4)), IO), (2.0, IDLE0, IO)],
                                      [(0.0, 'warn'), (1.0, 'grip')])
    # «Чужая клятва» (1.4 с): указывает «Дланью» на жертву, рука вторит — указующий палец; mark 0.6 — код ставит метку (fx ereb_hand_oath_mark)
    oath = full(EA.mod(STAND, left_arm=[-88, 8, -6], head=[0, -4, 0], torso=[0, -6, 0], body=[0, -10, 0]),
                hand(pos=(2, -2, -8), rot=(60, -6, 0), curl=1.0, thumb=0.9, point=True))
    an['ereb_hand_foreign_oath'] = anim(1.4, [(0, IDLE0), (0.45, oath, IO), (0.6, full(EA.mod(STAND, left_arm=[-92, 8, -6], head=[0, -4, 0], torso=[0, -6, 0],
                                                                                                 body=[0, -10, 0]),
                                                                                         hand(pos=(2, -2, -9), rot=(64, -6, 0), curl=1.0, thumb=0.9,
                                                                                              point=True)), OQ),
                                              (0.95, oath), (1.4, IDLE0, IO)], [(0.6, 'mark')])
    # «Тысяча отражений» (2.6 с): рапира к небу (клинок вертикально), «Длань» в сторону — вокруг арены встают зеркала (mirrors 0.6);
    # рапира опускается остриём на арену — из зеркал начинают бить отражения (strikes 1.4: код по очереди шлёт fx и анимацию отражения)
    tr_up = full(EA.mod(STAND, right_arm=[-172, 6, -6], bipedHandRight=[78, 0, -6], left_arm=[-40, 0, -60], head=[-20, 0, 0], torso=[-4, 0, 0]),
                 hand(pos=(4, 8, 2), rot=(-8, -26, 8), curl=0.0, spread=1.1, thumb=0.0))
    tr_dn = full(EA.mod(STAND, right_arm=[-84, 20, 6], bipedHandRight=[60, 0, 0], left_arm=[-36, 0, -50], head=[4, 0, 0]),
                 hand(pos=(3, 4, 0), rot=(10, -22, 2), curl=0.3, spread=0.4))
    an['ereb_hand_thousand_reflections'] = anim(2.6, [(0, IDLE0), (0.6, tr_up, IO), (1.0, tr_up), (1.5, tr_dn, IO), (2.0, tr_dn), (2.6, IDLE0, IO)],
                                                [(0.6, 'mirrors'), (1.5, 'strikes')])
    # отражение из зеркала (1.0 с; модель ereb_hand, полупрозрачно — рисует код): появляется уже в выпаде (appear 0), укол (hit 0.45), тает (gone 0.9)
    pre_r = full(EA.mod(GUARD, body_pos=[0, -1.8, 2], right_arm=[-70, 40, 10], bipedHandRight=[70, 0, 0]), HG_back)
    an['ereb_hand_reflection_strike'] = anim(1.0, [(0, pre_r), (0.45, lunge, OQ), (0.7, lunge), (1.0, guard, IO)],
                                             [(0.0, 'appear'), (0.45, 'hit'), (0.9, 'gone')])
    an.update(build_spells2(pre_r, lunge, guard))
    # T32 «Сломать блок»: призрачная рука отводит защиту, укол стеклянной рапирой (tools/guard_break_ereb_hand.py)
    import guard_break_ereb_hand
    an['ereb_hand_guard_break'] = guard_break_ereb_hand.build()
    return an


def build_spells2(pre_r, lunge, guard):
    """Вторая партия (владелец 20.11): «Пламя-подменыш», «Ложное отступление», «Отражение-предатель», «Рой лжи» и мифическое
    «Ложный рассвет». Касты — «Длань» (левая рука) и призрачная рука строго ВПЕРЁД (x < 0 у руки, z < 0 у призрачной руки);
    накидка и полы — назад; ничего не уходит в землю (проверка check_ereb_hand_anims.py)."""
    an = {}
    # ---------------------------------------------------------------- «Пламя-подменыш» (1.6 с): в «Длани» над головой собирается огненный шар
    # (charge 0.2 — fx шара в кулаке), бросок вперёд (throw 0.65 — снаряд вылетает из «Длани»), призрачная рука хитро «переворачивает»
    # ладонь (подмена шара на бабочку делает код на полпути, подсказка — мерцание золотом за 0.5 с до неё)
    cf_wind = full(EA.mod(STAND, left_arm=[-152, 8, -22], bipedHandLeft=Z3, torso=[-6, 0, 0], head=[-10, -8, 0], body=[0, -14, 0], cape=[6, 0, 0]),
                   hand(pos=(1, 3, 3), rot=(10, -20, -4), curl=0.5, thumb=0.4))
    cf_throw = full(EA.mod(STAND, left_arm=[-84, 14, -4], torso=[6, 0, 0], head=[4, -10, 0], body=[0, 12, 0], body_pos=[0, 0, -0.5],
                           cape=[16, 0, 0]),
                    hand(pos=(3, -2, -10), rot=(40, -8, 0), curl=0.0, spread=1.0, thumb=0.0))
    cf_follow = full(EA.mod(STAND, left_arm=[-70, 14, -8], torso=[4, 0, 0], head=[2, -8, 0], body=[0, 10, 0], cape=[12, 0, 0]),
                     hand(pos=(3, -1, -9), rot=(36, -8, 0), curl=0.05, spread=0.9, thumb=0.0))
    cf_flip = full(EA.mod(STAND, left_arm=[-40, 8, -10], head=[0, -4, 0], body=[0, 4, 0], cape=[8, 0, 0]),
                   hand(pos=(2, 0, -6), rot=(24, -14, -4), curl=0.15, spread=0.5, thumb=0.1, wrist=(0, 0, -22)))
    an['ereb_hand_changeling_flame'] = anim(1.6, [(0, IDLE0), (0.4, cf_wind, IO), (0.52, cf_wind), (0.65, cf_throw, OQ), (0.9, cf_follow, IO),
                                                  (1.15, cf_flip, IO), (1.6, IDLE0, IO)],
                                            [(0.2, 'charge'), (0.65, 'throw')])
    # ---------------------------------------------------------------- «Ложное отступление» (1.3 с): присед (0–0.25), прыжок назад (leap 0.25 —
    # код даёт скорость назад ≈4 бл.), приземление (land 0.65 — код ставит ДВОЙНИКА без тени на точку приземления, настоящего прячет на 2 с),
    # двойник «открывается»: руки опущены и разведены, подбородок вверх → петля ereb_hand_false_retreat_open
    fr_crouch = full(EA.mod(GUARD, body_pos=[0, 0.9, 0], torso=[10, 0, 0], head=[-8, 0, 0], right_leg=[-12, 0, 2], left_leg=[10, 0, -2], cape=[12, 0, 0]),
                     hand(pos=(1, -1, 0), rot=(20, -14, -4), curl=0.4, thumb=0.3))
    fr_air = full(EA.mod(GUARD, body_pos=[0, 3.0, 2.0], torso=[-8, 0, 0], head=[8, 0, 0], right_leg=[-34, 0, 4], left_leg=[-8, 0, -4],
                         left_arm=[-120, -6, -40], cape=[6, 0, 0]),
                  hand(pos=(1, 3, 2), rot=(6, -18, -6), curl=0.2, spread=0.6, thumb=0.1))
    fr_land = full(EA.mod(GUARD, body_pos=[0, 0.9, 0], torso=[12, 0, 0], head=[-8, 0, 0], right_leg=[-12, 0, 2], left_leg=[10, 0, -2],
                          left_arm=[-30, 0, -36], cape=[14, 0, 0]),
                   hand(pos=(1, -1, 1), rot=(22, -14, -4), curl=0.3, thumb=0.2))
    OPEN_B = EA.mod(STAND, left_arm=[-18, 0, -38], right_arm=[-22, 10, 36], bipedHandRight=[30, 0, 0], head=[-10, 0, 0], torso=[-4, 0, 0],
                    cape=[5, 0, 0])
    OPEN_H = hand(pos=(1, -1, 2), rot=(-6, -20, -6), curl=0.0, spread=0.7, thumb=0.0)
    OPEN = full(OPEN_B, OPEN_H)
    an['ereb_hand_false_retreat'] = anim(1.3, [(0, IDLE0), (0.25, fr_crouch, IO), (0.45, fr_air, OC), (0.6, lerp(fr_air, fr_land, 0.6), IC),
                                               (0.7, fr_land, OQ), (1.1, lerp(fr_land, OPEN, 0.85), IO), (1.3, OPEN, IO)],
                                         [(0.25, 'leap'), (0.65, 'land')])
    open2 = full(EA.mod(OPEN_B, head=[-12, 4, 0], torso=[-5, 0, 0], body_pos=[0, 0.2, 0]),
                 hand(pos=(1, -0.4, 2), rot=(-8, -20, -6), curl=0.05, spread=0.8, thumb=0.0))
    an['ereb_hand_false_retreat_open'] = anim(2.0, [(0, OPEN), (1.0, open2, IO), (2.0, OPEN, IO)], loop=True)
    # настоящий появляется за спиной того, кто подошёл к двойнику (appear 0 — уже в замахе, как отражение), удар в спину (hit 0.35)
    def up(p, dy):                                     # корпус выше на dy ед.: ступни и полы не уходят в землю
        q = dict(p)
        q['body_pos'] = [p['body_pos'][0], p['body_pos'][1] + dy, p['body_pos'][2]]
        return q
    an['ereb_hand_false_retreat_strike'] = anim(1.4, [(0, up(pre_r, 1.7)), (0.35, up(lunge, 0.3), OQ), (0.6, up(lunge, 0.3)), (0.95, up(guard, 1.4), IO),
                                                      (1.4, IDLE0, IO)],
                                                [(0.0, 'appear'), (0.35, 'hit')])
    # ---------------------------------------------------------------- «Отражение-предатель» (2.0 с): «Длань» указывает на игрока — у него встаёт
    # зеркало (mirror 0.5), призрачная рука тянется в зеркало, хватает отражение и вытягивает (emerge 1.2 — из зеркала выходит стеклянная
    # копия игрока), рапира «посылает» копию вперёд
    tr_point = full(EA.mod(STAND, left_arm=[-88, 18, -8], head=[2, -6, 0], torso=[3, 0, 0], body=[0, -6, 0], cape=[8, 0, 0]),
                    hand(pos=(6, -4, -18), rot=(12, -4, 4), curl=0.0, spread=1.0, thumb=0.0))
    tr_reach = full(EA.mod(STAND, left_arm=[-92, 18, -8], head=[4, -6, 0], torso=[4, 0, 0], body=[0, -6, 0], body_pos=[0, 0, -0.4], cape=[10, 0, 0]),
                    hand(pos=(7, -5, -21), rot=(10, -2, 4), curl=0.1, spread=0.9, thumb=0.0))
    tr_pull = full(EA.mod(STAND, left_arm=[-52, 12, -18], head=[-4, -4, 0], torso=[-4, 0, 0], body=[0, -2, 0], body_pos=[0, 0, 0.6], cape=[4, 0, 0]),
                   hand(pos=(4, -1, -8), rot=(20, -10, 2), curl=0.9, thumb=0.85))
    tr_send = full(EA.mod(STAND, right_arm=[-84, 20, 6], bipedHandRight=[60, 0, 0], left_arm=[-30, 10, -20], head=[2, 0, 0], cape=[8, 0, 0]),
                   hand(pos=(3, 1, -4), rot=(18, -16, -2), curl=0.1, spread=0.7, thumb=0.0))
    an['ereb_hand_traitor_reflection'] = anim(2.0, [(0, IDLE0), (0.5, tr_point, IO), (0.95, tr_reach, IO), (1.2, tr_pull, OQ), (1.4, tr_pull),
                                                    (1.65, tr_send, IO), (2.0, IDLE0, IO)],
                                              [(0.5, 'mirror'), (1.2, 'emerge')])
    # ---------------------------------------------------------------- «Рой лжи» (1.6 с): призрачная рука сложена «чашей» перед грудью —
    # в ней собираются бабочки (gather 0.3), рука раскрывается вперёд-вверх и выпускает 12 бабочек (release 0.75), «Длань» отводит их взмахом
    sw_cup = full(EA.mod(STAND, left_arm=[-54, 22, -6], head=[6, 0, 0], torso=[3, 0, 0], cape=[6, 0, 0]),
                  hand(pos=(4, -9, -14), rot=(46, -10, -2), curl=0.72, thumb=0.6))
    sw_open = full(EA.mod(STAND, left_arm=[-112, 0, -40], head=[-6, 0, 0], torso=[-3, 0, 0], body=[0, 4, 0], cape=[10, 0, 0]),
                   hand(pos=(4, 4, -14), rot=(8, -6, 4), curl=0.0, spread=1.3, thumb=0.0))
    sw_hold = full(EA.mod(STAND, left_arm=[-100, 0, -46], head=[-4, 0, 0], torso=[-2, 0, 0], body=[0, 4, 0], cape=[8, 0, 0]),
                   hand(pos=(4, 4, -13), rot=(10, -6, 4), curl=0.05, spread=1.2, thumb=0.0))
    an['ereb_hand_swarm_of_lies'] = anim(1.6, [(0, IDLE0), (0.35, sw_cup, IO), (0.6, sw_cup), (0.75, sw_open, OQ), (1.05, sw_hold, IO),
                                               (1.6, IDLE0, IO)],
                                         [(0.3, 'gather'), (0.75, 'release')])
    # ---------------------------------------------------------------- мифическое «Ложный рассвет» (33%, 6.0 с): шатается, падает на одно колено
    # (kneel 0.5: полоса скрыта, небо светлеет, «победная» фанфара; 4 с неуязвим), тяжело дышит (бабочки вокруг НЕ улетают), встаёт
    # (rise 4.5), волна по арене (wave 5.0: ≤6 бл. — 60% макс. ХП, дальше — 20%), стойка → затем код играет ereb_hand_phase3 (маска трескается)
    fd_stag = full(EA.mod(STAND, body=[2, 0, -4], body_pos=[0, 0, 1.2], head=[14, -6, 0], torso=[6, 0, 0], right_arm=[-6, 12, 16],
                          bipedHandRight=[20, 0, 0], left_arm=[-30, -6, -20], right_leg=[-8, 0, 4], left_leg=[8, 0, -4], cape=[4, 0, 0]),
                   hand(pos=(0, -2, 2), rot=(30, -18, -10), curl=0.6, thumb=0.5))

    def kneel_b(br, by=-4.5):
        return EA.mod(STAND, body_pos=[0, by, 0], body=[0, 0, 0], torso=[10 + 2 * br, 0, 0], head=[22 - 3 * br, 4, 0],
                      right_leg=[-64, 0, 3], left_leg=[62, 0, -3], right_arm=[-44, 14, 10], bipedHandRight=[64, 0, 0],
                      left_arm=[-44, 26, 8], bipedHandLeft=Z3, coat_front_r=[-70, 0, 4], coat_front_l=[-45, 0, -4],
                      coat_back_r=[75, 0, 2], coat_back_l=[78, 0, -2], cape=[30 + 2 * br, 0, 0])
    KH = hand(pos=(0, -4, 3), rot=(36, -18, -10), curl=0.55, thumb=0.45)
    fd_kneel = full(kneel_b(0), KH)
    fd_kneel2 = full(kneel_b(1), hand(pos=(0, -3.4, 3), rot=(34, -18, -8), curl=0.5, thumb=0.45))
    fd_up = full(EA.mod(STAND, body_pos=[0, 0, 0], torso=[4, 0, 0], head=[-6, 0, 0], right_leg=[-14, 0, 2], left_leg=[12, 0, -2],
                        right_arm=[-30, 12, 20], bipedHandRight=[40, 0, 0], left_arm=[-40, 0, -30], cape=[10, 0, 0]),
                 hand(pos=(2, 4, 1), rot=(4, -22, 0), curl=0.3, spread=0.6, thumb=0.2))
    WAVE_B = EA.mod(STAND, body_pos=[0, 0.4, 0], torso=[-6, 0, 0], head=[-14, 0, 0], left_arm=[-150, 0, -40], right_arm=[-60, 0, 70],
                    bipedHandRight=[30, 0, 0], cape=[14, 0, 0])
    fd_wave = full(WAVE_B, hand(pos=(6, 9, -7), rot=(-20, -30, 14), curl=0.0, spread=1.3, thumb=0.0))
    fd_wave2 = full(EA.mod(WAVE_B, left_arm=[-140, 0, -44], head=[-10, 0, 0]), hand(pos=(6, 8, -6), rot=(-16, -30, 12), curl=0.05, spread=1.2, thumb=0.0))
    an['ereb_hand_false_dawn'] = anim(6.0, [(0, IDLE0), (0.25, fd_stag, OQ), (0.38, full(kneel_b(0, -1.0), KH), IO), (0.5, fd_kneel, IC), (1.5, fd_kneel2, IO), (2.5, fd_kneel, IO),
                                            (3.5, fd_kneel2, IO), (4.5, fd_kneel, IO), (4.65, full(kneel_b(0, -1.8), KH), IO), (4.85, fd_up, OC), (5.0, fd_wave, OQ), (5.5, fd_wave2, IO),
                                            (6.0, IDLE0, IO)],
                                      [(0.5, 'kneel'), (4.5, 'rise'), (5.0, 'wave')])
    return an


SPELLS2 = ('ereb_hand_changeling_flame', 'ereb_hand_false_retreat', 'ereb_hand_false_retreat_open', 'ereb_hand_false_retreat_strike',
           'ereb_hand_traitor_reflection', 'ereb_hand_swarm_of_lies', 'ereb_hand_false_dawn')

# что за чем играет (для проверки стыков): анимация → (откуда приходит, куда уходит); None — поза покоя IDLE0
CHAIN = {'ereb_hand_grab': (None, 'ereb_hand_grab_hold'), 'ereb_hand_grab_hold': ('ereb_hand_grab', 'ereb_hand_squeeze'),
         'ereb_hand_squeeze': ('ereb_hand_grab_hold', 'ereb_hand_grab_hold'), 'ereb_hand_grab_release': ('ereb_hand_grab_hold', None),
         'ereb_hand_spawn': ('hidden', None), 'ereb_hand_false_death': (None, 'hidden'), 'ereb_hand_mask_fall': (None, 'maskless'),
         'ereb_hand_mask_return': ('maskless', None), 'ereb_hand_hand_of_lies': (None, None),
         'ereb_hand_reflection_strike': ('hidden', 'hidden'),
         'ereb_hand_false_retreat': (None, 'ereb_hand_false_retreat_open'), 'ereb_hand_false_retreat_strike': ('hidden', None)}


def build_giant():
    """Анимации огромной руки (geo/entity/ereb_hand_giant.geo.json): кости ghost_*, корень ghost_hand — у запястья.
    Ладонь вниз, пальцы вперёд — ghost_hand x = 90."""
    def G(**kw):
        p = hand(**kw)
        p['ghost_hand_pos'] = list(kw.get('pos', (0, 0, 0)))
        return {k: v for k, v in p.items()}
    an = {}
    opn = G(rot=(90, 0, 0), curl=0.12, spread=0.9, thumb=0.05)
    opn2 = G(rot=(86, 0, 2), curl=0.2, spread=0.8, thumb=0.1, ripple=0.1)
    fist = G(rot=(90, 0, 0), curl=1.05, thumb=1.0)
    fist2 = G(rot=(88, 0, -2), curl=1.0, thumb=0.95, wrist=(0, 0, 3))
    # спуск с неба: раскрыта, пальцы чуть перебирают (петля 2 с)
    an['ereb_hand_giant_descend'] = anim(2.0, [(0, opn), (1.0, opn2, IO), (2.0, opn, IO)], loop=True)
    # поимка: смыкается в кулак (catch 0.25)
    an['ereb_hand_giant_grab'] = anim(0.5, [(0, opn), (0.25, G(rot=(90, 0, 0), curl=0.8, thumb=0.7), IQ), (0.5, fist, OQ)], [(0.25, 'catch')])
    # держит в кулаке (петля 2 с) — игрок внутри кулака
    an['ereb_hand_giant_fist'] = anim(2.0, [(0, fist), (1.0, fist2, IO), (2.0, fist, IO)], loop=True)
    # раскрывается и тает (код — прозрачность/масштаб): release 0.2
    an['ereb_hand_giant_release'] = anim(0.8, [(0, fist), (0.25, G(rot=(80, 0, 0), curl=0.0, spread=1.2, thumb=0.0), OQ),
                                               (0.8, G(rot=(70, 0, 0), curl=0.1, spread=1.0, thumb=0.0, scale=0.02), IC)], [(0.2, 'release')])
    # над миром сна: парит ладонью вниз, медленно покачивается (петля 6 с)
    keys = []
    for i in range(7):
        t = i * 1.0
        ph = math.sin(t * math.pi / 3)
        keys.append((t, G(pos=(0, 4 * ph, 0), rot=(84 + 4 * ph, 3 * ph, 3 * math.cos(t * math.pi / 3)), curl=0.2 + 0.08 * ph, spread=0.8,
                          thumb=0.1, ripple=0.1 * ph), IO))
    an['ereb_hand_giant_hover'] = anim(6.0, keys, loop=True)
    # удар по площади: замах вверх, падение плашмя (slam 0.55), лежит, тает
    an['ereb_hand_giant_slam'] = anim(1.4, [(0, opn), (0.3, G(pos=(0, 10, 0), rot=(70, 0, 0), curl=0.0, spread=1.0, thumb=0.0), IO),
                                           (0.55, G(pos=(0, -2, 0), rot=(94, 0, 0), curl=0.05, spread=1.0, thumb=0.0), IC),
                                           (1.0, G(pos=(0, -2, 0), rot=(94, 0, 0), curl=0.15, spread=0.9, thumb=0.0)),
                                           (1.4, G(pos=(0, -2, 0), rot=(94, 0, 0), curl=0.2, spread=0.9, thumb=0.0, scale=0.02), IC)], [(0.55, 'slam')])
    return an


def write(M):
    src = M.jar_json(M.I + 'animations/casting_animations.json')
    ours = build()
    doc = {'format_version': src['format_version'], 'geckolib_format_version': src['geckolib_format_version'],
           'comment': 'T31 Эреб, Длань Лжи: все анимации casting_animations.json Iron\'s (те же имена — их зовёт AbstractSpellCastingMob) + '
                      'ereb_hand_* (наши). Сгенерировано tools/gen_ereb_hand.py (tools/gen_ereb_hand_anims.py) — правьте генератор.',
           'animations': {**src['animations'], **ours}}
    # 21.11: GeckoLib 4.8.4 поворачивает рапиру кистью дважды — ключи кисти (подобраны по превью с одним поворотом) → видимый поворот.
    # ereb_hand_guard_break (T32) — не трогаю: его считает guard_break_lib, автор правит сам.
    import anim_cloth
    anim_cloth.visible_hand(doc['animations'], [k for k in ours if k != 'ereb_hand_guard_break'])
    with open(M.out('animations/entity/ereb_hand.animation.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')
    gd = {'format_version': src['format_version'], 'geckolib_format_version': src['geckolib_format_version'],
          'comment': 'T31: огромная рука (geo/entity/ereb_hand_giant.geo.json) — «Длань Лжи» и Длань над миром «Полного Раскрытия». '
                     'Сгенерировано tools/gen_ereb_hand.py (gen_ereb_hand_anims.build_giant).', 'animations': build_giant()}
    with open(M.out('animations/entity/ereb_hand_giant.animation.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(gd, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')
    return ours
