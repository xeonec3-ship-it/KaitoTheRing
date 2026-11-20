#!/usr/bin/env python3
"""
T30 «Эреб» — анимации GeckoLib (наши ereb_*). Вызывается из tools/gen_ereb.py (write(M)).
Файл animations/entity/ereb.animation.json = все casting_animations.json Iron's (те же имена: их зовёт логика AbstractSpellCastingMob)
+ ereb_*. События — ключи timeline (GeckoLib CustomInstructionKeyframeEvent); коду можно заменить их таймерами по таблице в письме.

Оси (как у Iron's): rotation x < 0 — рука/нога вперёд-вверх, body x > 0 — наклон вперёд, body y > 0 — поворот к своей правой стороне,
right_arm z > 0 / left_arm z < 0 — руки в стороны. Кисть — кость bipedHandRight (в ней Iron's рисует предмет): x > 0 — клинок
опускается к земле, x < 0 — поднимается; при руке, поднятой вперёд (x ≈ −90), кисть x ≈ +85 — клинок продолжает руку (выпад).
Полы камзола — кости coat_front_r/l, coat_back_r/l (дочери body, ось у пояса): x < 0 — подол вперёд, z — в сторону.
"""
import json
import math

Z = [0, 0, 0]
IO, OC, OQ, IQ, IC = 'easeInOutSine', 'easeOutCubic', 'easeOutQuart', 'easeInQuart', 'easeInCubic'
BONES = ('body', 'torso', 'head', 'right_arm', 'left_arm', 'right_leg', 'left_leg', 'bipedHandRight', 'bipedHandLeft',
         'coat_front_r', 'coat_front_l', 'coat_back_r', 'coat_back_l')


def P(**kw):
    """Поза: кость → [rx, ry, rz]; позиция — ключ с суффиксом _pos; масштаб — _scale."""
    return kw


# ---------------------------------------------------------------- позы
STAND = P(head=[-3, 8, 0], right_arm=[-14, 12, 7], bipedHandRight=[52, 0, 0], left_arm=[20, -14, 10],
          right_leg=[-4, 0, 3], left_leg=[6, 0, -4], coat_front_r=[-3, 0, 2], coat_front_l=[2, 0, -2])
# стойка «ан гард»: правый бок к врагу, рука с рапирой вперёд, левая рука поднята за спиной, колени чуть согнуты
GUARD = P(body=[4, -38, 0], body_pos=[0, -1.2, 0], head=[0, 36, 0], torso=[0, 4, 0],
          right_arm=[-62, 34, 8], bipedHandRight=[48, 0, 0], left_arm=[-150, -10, -40], bipedHandLeft=[0, 0, 0],
          right_leg=[-24, 30, 2], left_leg=[16, 18, -8], coat_front_r=[-16, 0, 6], coat_front_l=[10, 0, -6],
          coat_back_r=[10, 0, 0], coat_back_l=[16, 0, -4])
LUNGE = P(body=[10, -42, 0], body_pos=[0, -2.4, -6], head=[-12, 38, 0], torso=[0, 4, 0],
          right_arm=[-90, 40, 0], bipedHandRight=[88, 0, 0], left_arm=[-60, -10, -95], bipedHandLeft=[0, 0, 0],
          right_leg=[-62, 34, 0], left_leg=[36, 20, -10], coat_front_r=[-40, 0, 8], coat_front_l=[22, 0, -8],
          coat_back_r=[30, 0, 0], coat_back_l=[40, 0, -6])
PARRY = P(body=[0, -30, 0], body_pos=[0, -1.4, 1], head=[-4, 28, 0], torso=[-4, 8, 0],
          right_arm=[-110, -10, -30], bipedHandRight=[30, 50, 0], left_arm=[-140, -10, -40],
          right_leg=[-14, 26, 4], left_leg=[22, 16, -8], coat_front_r=[-10, 0, 4], coat_front_l=[14, 0, -6], coat_back_r=[8, 0, 0], coat_back_l=[12, 0, 0])
CAST = P(body=[-2, 10, 0], head=[-6, -10, 0], torso=[-3, 0, 0], right_arm=[-8, 10, 14], bipedHandRight=[56, 0, 0],
         left_arm=[-168, 0, -36], bipedHandLeft=[0, 0, 0], right_leg=[-6, 0, 4], left_leg=[8, 0, -4],
         coat_front_r=[-2, 0, 4], coat_front_l=[4, 0, -4])
PALM = P(body=[2, 0, 0], head=[18, 4, 0], right_arm=[-10, 8, 10], bipedHandRight=[60, 0, 0],
         left_arm=[-62, 30, 4], bipedHandLeft=[0, 0, 0], right_leg=[-3, 0, 3], left_leg=[4, 0, -3])
BOW = P(body=[28, 0, 0], body_pos=[0, -0.4, 0], head=[10, 0, 0], right_arm=[-58, 8, -6], bipedHandRight=[70, 0, 0],
        left_arm=[18, -12, 12], right_leg=[-28, 0, 2], left_leg=[-28, 0, -2], coat_front_r=[-30, 0, 2], coat_front_l=[-30, 0, -2],
        coat_back_r=[-24, 0, 0], coat_back_l=[-24, 0, 0])
SALUTE = P(body=[-2, -10, 0], head=[-4, 10, 0], right_arm=[-102, 34, 0], bipedHandRight=[-52, 0, 0],
           left_arm=[20, -14, 10], right_leg=[-6, 0, 3], left_leg=[8, 0, -4])


def lerp_pose(a, b, k):
    keys = set(a) | set(b)
    o = {}
    for kk in keys:
        va = a.get(kk, [1, 1, 1] if kk.endswith('_scale') else Z)
        vb = b.get(kk, [1, 1, 1] if kk.endswith('_scale') else Z)
        o[kk] = [va[i] + (vb[i] - va[i]) * k for i in range(3)]
    return o


def mod(pose, **kw):
    o = dict(pose)
    o.update(kw)
    return o


def anim(length, keys, timeline=None, loop=False):
    """keys: [(t, поза, easing)] → каналы GeckoLib по всем костям, встречающимся в позах (недостающие — 0)."""
    names = set()
    for _t, p, *_e in keys:
        names |= set(p)
    bones = {}
    for nm in sorted(names):
        bone, kind = (nm.rsplit('_', 1) + [''])[:2] if nm.endswith(('_pos', '_scale')) else (nm, 'rot')
        kind = {'pos': 'position', 'scale': 'scale', 'rot': 'rotation'}[kind]
        dflt = [1, 1, 1] if kind == 'scale' else Z
        ch = {}
        for t, p, *e in keys:
            v = p.get(nm, dflt)
            k = {'vector': [round(x, 2) for x in v]}
            if e and e[0] and t > 0:
                k['easing'] = e[0]
            ch['%.4g' % t if t else '0.0'] = k
        bones.setdefault(bone, {})[kind] = ch
    o = {'animation_length': length, 'bones': bones}
    if loop:
        o['loop'] = True
    if timeline:
        o['timeline'] = {('%.4g' % t): v for t, v in timeline}
    return o


def build():
    an = {}
    # ---------------------------------------------------------------- покой: элегантная стойка (4 с, петля). Левая рука за спиной,
    # рапира опущена к земле; дыхание, лёгкий перенос веса, полы чуть колышутся.
    keys = []
    for i in range(5):
        t = i * 1.0
        ph = math.sin(i * math.pi / 2)
        p = mod(STAND, torso=[-1.5 * abs(ph), 0, 0], body_pos=[0, 0.12 * abs(ph), 0], head=[-3 + 1.5 * ph, 8 + 4 * ph, 0],
                coat_front_r=[-3, 0, 2 + 1.2 * ph], coat_front_l=[2, 0, -2 + 1.2 * ph], coat_back_r=[1.5 * ph, 0, 1.0 * ph],
                coat_back_l=[1.5 * ph, 0, 1.0 * ph], right_arm=[-14 + 2 * ph, 12, 7])
        keys.append((t, p, IO))
    an['ereb_idle'] = anim(4.0, keys, loop=True)
    # ---------------------------------------------------------------- шаг (1.2 с, петля): ноги ±26°, полы следуют за ногами с запаздыванием
    keys = []
    for i in range(9):
        t = i * 0.15
        s = math.sin(i * math.pi / 4)
        c = math.sin(i * math.pi / 4 - 0.6)
        keys.append((t, mod(STAND, right_leg=[-26 * s, 0, 2], left_leg=[26 * s, 0, -2], body_pos=[0, -0.35 * abs(math.cos(i * math.pi / 4)), 0],
                            right_arm=[-14 + 6 * s, 12, 7], bipedHandRight=[40, 0, 0], left_arm=[20, -14, 10], head=[-3, 4, 0], torso=[2, 0, 0],
                            coat_front_r=[-6 - 14 * max(0, c), 0, 3], coat_front_l=[-6 - 14 * max(0, -c), 0, -3],
                            coat_back_r=[6 + 10 * max(0, -c), 0, 2], coat_back_l=[6 + 10 * max(0, c), 0, -2]), 'linear'))
    an['ereb_walk'] = anim(1.2, keys, loop=True)
    # ---------------------------------------------------------------- фехтование
    an['ereb_guard'] = anim(1.0, [(0, GUARD), (0.5, mod(GUARD, body_pos=[0, -1.4, 0]), IO), (1.0, GUARD, IO)], loop=True)
    # выпад (1.2 с): 0.3 — сжался, 0.5 — укол (hit), 0.8–1.2 — возврат в стойку
    an['ereb_lunge'] = anim(1.2, [
        (0, GUARD), (0.3, mod(GUARD, body_pos=[0, -1.8, 2], right_arm=[-70, 40, 10], bipedHandRight=[70, 0, 0]), IO),
        (0.5, LUNGE, OQ), (0.75, LUNGE), (1.2, GUARD, IO)], [(0.5, 'hit')])
    # серия (1.8 с): три укола — 0.45, 0.8, 1.15 (вверх, в корпус, финт снизу)
    a1 = mod(LUNGE, right_arm=[-104, 36, 0], body_pos=[0, -2.6, -4], bipedHandRight=[92, 0, 0])
    a2 = mod(LUNGE, right_arm=[-86, 44, 4], body_pos=[0, -3.0, -5])
    a3 = mod(LUNGE, right_arm=[-72, 40, -6], bipedHandRight=[70, 0, 0], body=[22, -42, 0], body_pos=[0, -3.6, -6])
    back = mod(GUARD, body_pos=[0, -1.6, 1], right_arm=[-70, 36, 10])
    an['ereb_flurry'] = anim(1.8, [
        (0, GUARD), (0.25, back, IO), (0.45, a1, OQ), (0.62, back, IO), (0.8, a2, OQ), (0.97, back, IO), (1.15, a3, OQ),
        (1.4, a3), (1.8, GUARD, IO)], [(0.45, 'hit'), (0.8, 'hit'), (1.15, 'hit')])
    # парирование (1.0 с): 0.15 — клинок поперёк (parry, звон, искра), 0.6 — ответный укол (hit)
    an['ereb_parry'] = anim(1.0, [(0, GUARD), (0.15, PARRY, OQ), (0.35, mod(PARRY, body_pos=[0, -1.6, 1.6]), IO),
                                  (0.6, LUNGE, OQ), (1.0, GUARD, IO)], [(0.15, 'parry'), (0.6, 'hit')])
    # ---------------------------------------------------------------- каст иллюзий (1.4 с): левая рука вверх, щелчок пальцами (cast 0.75)
    an['ereb_cast_illusion'] = anim(1.4, [
        (0, STAND), (0.45, CAST, IO), (0.7, mod(CAST, left_arm=[-174, 0, -32], head=[-8, -12, 0]), IO),
        (0.78, mod(CAST, left_arm=[-160, 0, -40]), OQ), (1.0, CAST), (1.4, STAND, IO)], [(0.75, 'cast')])
    # магия руками — стеклянные осколки (1.2 с): правая (с рапирой) отведена, левая ладонь вперёд, стекло собирается, release 0.55
    gather = mod(STAND, body=[0, 18, 0], head=[0, -16, 0], left_arm=[-70, 30, -10], right_arm=[-6, 10, 18], right_leg=[-8, 0, 4], left_leg=[10, 0, -4])
    throw = mod(gather, body=[6, -14, 0], body_pos=[0, -0.6, -1.5], head=[-4, 12, 0], left_arm=[-92, -12, 0], right_arm=[10, 10, 24])
    an['ereb_shard_cast'] = anim(1.2, [(0, STAND), (0.4, gather, IO), (0.55, throw, OQ), (0.8, throw), (1.2, STAND, IO)], [(0.55, 'release')])
    # смена облика (1.0 с): ладонь проводит по лицу (swap 0.5) — «Чужое лицо», переход в фазу 2
    face = mod(STAND, left_arm=[-128, 42, 0], head=[6, 8, 0], torso=[3, 0, 0])
    an['ereb_disguise'] = anim(1.0, [(0, STAND), (0.35, face, IO), (0.5, mod(face, left_arm=[-108, 10, -24], head=[-4, 0, 0]), IO),
                                     (1.0, STAND, IO)], [(0.5, 'swap')])
    # ---------------------------------------------------------------- «Ложный союзник»
    # исчезновение (0.8 с): шаг назад, поклон головой, рассыпается (gone 0.6 — код прячет модель)
    an['ereb_vanish'] = anim(0.8, [(0, STAND), (0.3, mod(STAND, body_pos=[0, 0, 2], head=[12, 8, 0], right_arm=[-30, 12, 7]), IO),
                                   (0.6, mod(STAND, body_pos=[0, 0, 3], head=[12, 8, 0], body_scale=[0.96, 1.04, 0.96]), IO),
                                   (0.8, mod(STAND, body_pos=[0, 0, 3]))], [(0.6, 'gone')])
    # удар в спину (1.2 с): появляется уже в замахе (appear 0), укол сверху вниз в спину (stab 0.45), отходит
    pre = mod(GUARD, body=[-6, -20, 0], right_arm=[-160, 20, -10], bipedHandRight=[60, 0, 0], left_arm=[-30, 0, -30], body_pos=[0, 0, 1])
    stab = mod(LUNGE, body=[14, -20, 0], right_arm=[-70, 18, 0], bipedHandRight=[96, 0, 0], body_pos=[0, -1.6, -3],
               right_leg=[-40, 20, 0], left_leg=[24, 10, -6], coat_front_r=[-24, 0, 6], coat_front_l=[14, 0, -6])
    an['ereb_backstab'] = anim(1.2, [(0, pre), (0.3, mod(pre, right_arm=[-170, 20, -10]), IO), (0.45, stab, IQ), (0.75, stab),
                                     (1.2, STAND, IO)], [(0.0, 'appear'), (0.45, 'stab')])
    # ---------------------------------------------------------------- фаза (1.6 с): переход 66% / 33% — рапира описывает круг, салют
    an['ereb_phase'] = anim(1.6, [(0, STAND), (0.4, mod(SALUTE, right_arm=[-100, 60, -10], bipedHandRight=[0, 0, 0]), IO),
                                  (0.8, SALUTE, OC), (1.2, SALUTE), (1.6, STAND, IO)], [(0.8, 'phase')])
    # ---------------------------------------------------------------- появление (5.0 с): собирается из роя бабочек (код: модель не рисовать
    # 0–2.2 с), поклон, салют рапирой, стойка. form 2.2 (модель видна), bow 2.6, salute 3.9 (титр), ready 5.0 (полоса босса)
    an['ereb_spawn'] = anim(5.0, [(0, mod(STAND, body_scale=[0.9, 0.9, 0.9])), (2.2, mod(STAND, body_scale=[0.9, 0.9, 0.9])),
                                  (2.5, STAND, OC), (3.0, BOW, IO), (3.5, BOW), (3.9, SALUTE, IO), (4.5, SALUTE), (5.0, STAND, IO)],
                                 [(2.2, 'form'), (2.6, 'bow'), (3.9, 'salute'), (5.0, 'ready')])
    # ---------------------------------------------------------------- финал (6.5 с): «Сон бабочки» и исчезновение
    # 0.3 улыбка (smile: текстура ereb_smile), 0.8–1.4 подносит ладонь, 1.4 из ладони — стеклянная бабочка (butterfly),
    # 1.4–2.8 смотрит на неё, 3.2 поднимает руку — каст «Сна бабочки» (cast), 3.2–4.6 держит, 5.0 рассыпается бабочками (vanish)
    up = mod(PALM, left_arm=[-160, 18, -6], head=[-22, -6, 0], torso=[-6, 0, 0], body=[-4, 0, 0])
    an['ereb_finale'] = anim(6.5, [(0, STAND), (0.3, mod(STAND, head=[-6, 2, 0]), IO), (1.2, PALM, IO), (1.4, mod(PALM, left_arm=[-66, 30, 4]), OC),
                                   (2.2, mod(PALM, head=[14, 8, 0]), IO), (2.5, mod(PALM, head=[-4, -6, 0]), IO), (2.9, mod(PALM, head=[-4, -6, 0])), (3.2, up, OQ), (4.6, up), (5.0, mod(up, body_scale=[1.03, 1.03, 1.03])),
                                   (6.5, mod(up, body_scale=[1.03, 1.03, 1.03]))],
                                  [(0.3, 'smile'), (1.4, 'butterfly'), (2.4, 'speak'), (3.2, 'cast'), (5.0, 'vanish')])
    return an


def write(M):
    src = M.jar_json(M.I + 'animations/casting_animations.json')
    ours = build()
    doc = {'format_version': src['format_version'], 'geckolib_format_version': src['geckolib_format_version'],
           'comment': 'T30 Эреб: все анимации casting_animations.json Iron\'s (те же имена — их зовёт AbstractSpellCastingMob) + ereb_* (наши). '
                      'Сгенерировано tools/gen_ereb.py (tools/gen_ereb_anims.py) — правьте генератор.',
           'animations': {**src['animations'], **ours}}
    with open(M.out('animations/entity/ereb.animation.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')
    return ours
