#!/usr/bin/env python3
"""
T31 «Эреб, Длань Лжи» — проверочные кадры docs/media/t31_*.jpg (Playwright + three.js, шаблон tools/ereb_hand_preview.template.html).
Вызывается из tools/gen_ereb_hand.py --shots [--three путь/three.min.js] (three r128 локально: npm i three@0.128.0).
  t31_vs_t30.jpg           — рядом с принятым Эребом T30, один масштаб и свет (свет кадров T26 и дневной)
  t31_vs_cult_leader.jpg   — рядом с эталоном (Глава Культа T26), один масштаб и свет
  t31_model.jpg            — 4 стороны, лицо и маска (4 вида), в темноте (глоумаска), «Длань Лжи», призрачная рука, рапира
  t31_poses.jpg            — анимации: ключевые кадры с событиями
"""
import math
import os

import gen_ereb_hand_render as R

MEDIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'media')
N = {'neutral': True}


def shots(M, args):
    three = args[args.index('--three') + 1] if '--three' in args else None
    sh = lambda name, cells, cols, size: R.sheet(os.path.join(MEDIA, name), {'cols': cols, 'cells': cells}, three, size)
    # ---------------------------------------------------------------- рядом с T30 и с эталоном (один масштаб, один свет)
    for name, other, lab in (('t31_vs_t30.jpg', 'ereb', 'Эреб T30 (слева) и Длань Лжи T31'),
                             ('t31_vs_cult_leader.jpg', 'cult_leader', 'Длань Лжи T31 и Глава Культа (эталон)')):
        cells = []
        for light, ln in (({}, 'свет кадров T26'), (N, 'дневной свет')):
            for yaw, sub in ((20, 'три четверти'), (0, 'спереди'), (200, 'сзади')):
                if other == 'ereb':
                    c = dict(light, model='ereb', anim='ereb_idle', t=1.0, yaw=yaw, pitch=6, h=44, dist=3.0, ty=26, x=13,
                             label=lab, sub='%s, %s' % (ln, sub), **{'with': [{'model': 'ereb_hand', 'anim': 'ereb_hand_idle', 't': 1.0, 'x': -13}]})
                else:
                    c = dict(light, model='ereb_hand', anim='ereb_hand_idle', t=1.0, yaw=yaw, pitch=6, h=44, dist=3.0, ty=26, x=13,
                             label=lab, sub='%s, %s' % (ln, sub), **{'with': [{'model': 'cult_leader', 'x': -13}]})
                cells.append(c)
        sh(name, cells, 3, (1800, 1100))
    # ---------------------------------------------------------------- модель
    face = dict(N, model='ereb_hand_noitem', pitch=2, dist=0.8, ty=28.5)
    cells = [
        dict(N, model='ereb_hand_noitem', yaw=0, pitch=4, dist=3.0, ty=25, label='спереди', sub='камзол чёрно-багровый, знак Меллисто'),
        dict(N, model='ereb_hand_noitem', yaw=180, pitch=4, dist=3.0, ty=25, label='сзади', sub='накидка Главы, знак культа'),
        dict(N, model='ereb_hand_noitem', yaw=-90, pitch=4, dist=3.0, ty=25, label='правый бок', sub='призрачная рука над плечом'),
        dict(N, model='ereb_hand_noitem', yaw=90, pitch=4, dist=3.0, ty=25, label='левый бок', sub='«Длань Лжи» до локтя'),
        dict(face, yaw=12, label='маска', sub='ereb_hand.png: тонкие трещины'),
        dict(face, yaw=12, variant='mended', label='маска собрана', sub='_mended: после «Падения маски»'),
        dict(face, yaw=12, variant='cracked', label='маска треснула', sub='_cracked: фаза 3, трещины светятся'),
        dict(face, yaw=12, hideBones=['mask'], label='без маски', sub='кость mask скрыта (в «Падении маски»)'),
        dict(model='ereb_hand', anim='ereb_hand_idle', t=1.0, yaw=25, pitch=6, dist=1.9, ty=28, dim=0.2, label='в темноте',
             sub='глоумаска: глаза, знак, «Длань», рука'),
        dict(N, model='ereb_hand_noitem', yaw=-60, pitch=-4, dist=0.85, ty=14, label='«Длань Лжи»', sub='стекло в золоте, трещины, отражение'),
        dict(N, model='ereb_hand_noitem', yaw=-30, pitch=10, dist=1.05, ty=40, label='призрачная рука', sub='18 костей: кисть, фаланги, запястье'),
        dict(N, model='hand_rapier', yaw=0, pitch=6, dist=2.4, ty=2, label='рапира', sub='ereb_hand_rapier: стеклянный клинок'),
    ]
    sh('t31_model.jpg', cells, 4, (1800, 1350))
    # ---------------------------------------------------------------- анимации
    P = [('ereb_hand_idle', 1.0, 30, 'покой', 'рука парит, пальцы перебирают'),
         ('ereb_hand_walk', 0.3, 30, 'шаг', 'полы и накидка за ногами'),
         ('ereb_hand_lunge', 0.5, 60, 'выпад', 'hit 0.5'),
         ('ereb_hand_flurry', 1.15, 50, 'серия', 'hit 0.45 / 0.8 / 1.15'),
         ('ereb_hand_slam', 0.45, 40, 'удар рукой: замах', 'raise 0.45'),
         ('ereb_hand_slam', 0.8, 55, 'удар рукой по площади', 'slam 0.8 — ладонь ≈0.9 бл. впереди'),
         ('ereb_hand_grab', 0.6, 70, 'хватка', 'grab 0.6'),
         ('ereb_hand_grab_hold', 0.5, 70, 'держит игрока', 'петля 2 с'),
         ('ereb_hand_squeeze', 0.45, 70, 'сжатие', 'squeeze 0.35'),
         ('ereb_hand_cast', 0.75, 25, 'каст', '«Длань» вверх, щелчок: cast 0.75'),
         ('ereb_hand_spawn', 1.4, 25, 'появление 1/3', 'рука собирается (form_hand 0.6)'),
         ('ereb_hand_spawn', 2.8, 25, 'появление 2/3', 'поклон (bow 2.6)'),
         ('ereb_hand_spawn', 4.4, 25, 'появление 3/3', '«Вот мы и снова встретились» (speak 4.3)'),
         ('ereb_hand_phase2', 0.8, 40, 'фаза 2 (66%)', 'кулак в землю: phase 0.8'),
         ('ereb_hand_phase3', 0.95, 20, 'фаза 3 (33%)', 'маска трескается: crack 0.9'),
         ('ereb_hand_hand_of_lies', 0.7, 30, '«Длань Лжи» (66%)', 'рука уходит в небо: rise 0.5'),
         ('ereb_hand_mask_fall', 0.85, 20, '«Падение маски» (45%)', 'tear 0.85, shatter 1.1'),
         ('ereb_hand_full_reveal', 2.6, 25, '«Полное Раскрытие» (20%)', 'cast 2.6'),
         ('ereb_hand_false_death', 0.5, 20, 'ложная смерть 1/2', 'рука трескается (hand_break 0.7)'),
         ('ereb_hand_false_death', 1.8, 20, 'ложная смерть 2/2', '«А вы...стали сильнее» (speak 1.6)'),
         ('ereb_hand_finisher', 1.2, 70, 'добивание 1/2', 'поднял жертву'),
         ('ereb_hand_finisher', 2.0, 70, 'добивание 2/2', 'сжал: shatter 2.1'),
         ('ereb_hand_replica_break', 0.95, 30, '«Реплика»', 'сминает печать: break 0.95'),
         ('ereb_hand_rest', 0.0, 30, 'поза покоя', 'вне боя')]
    cells = [dict(N, model='ereb_hand', anim=a, t=t, yaw=y, pitch=6, dist=3.5, ty=25, label=lab, sub=sub, variant='cracked' if a.endswith(('phase3', 'false_death', 'full_reveal')) else None,
                  hideBones=['mask'] if a.endswith('mask_fall') and t > 1.1 else [])
             for a, t, y, lab, sub in P]
    for c in cells:
        if c['variant'] is None:
            c.pop('variant')
    sh('t31_poses.jpg', cells, 6, (2400, 1700))
    shots_fx(M, args)


# ================================================================== эффекты (кадры: условные спрайты и меши fx поверх модели — композиция)
GL, GH, GO, CR_, FL, WH = '#D9CCFF', '#F4EEFF', '#FFE7A0', '#E0606A', '#9A6BFF', '#FFFFFF'
VIOLET = 0x1d1730


def sp(tex, at, n=1, spread=(0, 0, 0), size=(0.5, 0.5), color=WH, op=0.9, seed=3, **kw):
    return dict(tex=tex, n=n, at=list(at), spread=list(spread), size=list(size), color=color, op=op, seed=seed, **kw)


def ground(tex, at, r, color=WH, op=0.8):
    return dict(tex=tex, n=1, at=[at[0], 0, at[2]], spread=[0, 0, 0], size=[2 * r, 2 * r], color=color, op=op, ground=True)


def gls(at, n, spread, seed=5, color=GH, size=(0.12, 0.28)):
    return sp('mote_glass', at, n, spread, size, color, 0.95, seed, spin=1.5)


def bfl(at, n, spread, seed=7):
    return [sp('mote_butterfly', at, n, spread, (0.25, 0.42), GL, 0.9, seed), sp('mote_butterfly_side', at, max(1, n // 2), spread, (0.22, 0.36), GO, 0.8, seed + 3)]


def flash(at, size, color=WH, op=0.85):
    return [sp('glow', at, 1, (0, 0, 0), (size, size), color, op, spin=0)]


def steve(x, z, ry=180, y=0, **kw):
    return dict({'model': 'steve', 'x': x * 16, 'z': -z * 16, 'ry': ry, 'y': y * 16}, **kw)      # единицы модели (16 на блок)


def giant(anim, x, y, z, t=0.0, scale=5, ry=0):
    """огромная рука (модель ereb_hand_giant ×scale), корень-запястье в точке (x, y, z) бл.; оси взгляда (z — вперёд)"""
    return {'model': 'ereb_hand_giant', 'anim': anim, 't': t, 'x': x * 16, 'y': y * 16, 'z': -z * 16, 'ry': ry, 'scale': scale}


# кулак ×5: середина кулака — на 1.1 бл. ниже и 2.5 бл. впереди запястья; торс игрока — на 1.1 бл. над ногами
FIST_DY, FIST_DZ = -1.1, 2.5


def shots_fx(M, args):
    three = args[args.index('--three') + 1] if '--three' in args else None
    sh = lambda name, cells, cols, size: R.sheet(os.path.join(MEDIA, name), {'cols': cols, 'cells': cells}, three, size)
    B = dict(N, model='ereb_hand', pitch=14, dist=4.2, ty=20)
    # ---------------------------------------------------------------- +4 заклинания
    circles = [(-3.2, 4.0, True), (0, 6.5, False), (3.2, 4.0, True), (-5.2, 1.0, False), (5.2, 1.5, True)]
    flame = []
    for i, (x, z, real) in enumerate(circles):
        flame.append(ground('ereb_hand_flame_ring', (x, 0, z), 2.0, FL, 0.95))
        flame.append(sp('cult_flame_tongue', (x, 0.7, z), 7, (1.2, 0.25, 1.2), (0.6, 1.1), FL, 0.75, 20 + i, spin=0.05))
        flame.append(gls((x, 0.6, z), 6, (1.2, 0.5, 1.2), 30 + i, FL))
        if real:
            flame.append(ground('ereb_hand_flame_rim', (x, 0, z), 2.05, GO, 0.45))
    oath_t = [steve(-2.2, 4.5), steve(2.4, 5.2)]
    mir = [dict(mesh='ereb_hand_mirror', pos=[7 * math.sin(a), 0, 7 * math.cos(a)], ry=math.degrees(a) + 180) for a in
           [i * math.pi / 3 for i in range(6)]]
    cells = [
        dict(B, anim='ereb_hand_false_flame', t=1.0, yaw=200, pitch=32, dist=6.0, ty=12, label='«Ложное пламя»',
             sub='5 кругов r2; 3 настоящих — с еле заметной золотой кромкой', fx=flame),
        dict(B, anim='ereb_hand_glass_grip', t=0.5, yaw=215, pitch=40, dist=5.0, ty=10, label='«Стеклянная хватка»: предупреждение',
             sub='конус 70° на 6 бл., 1 с', fx=[ground('ereb_hand_grip_cone', (0, 0, 0), 6.0, GL, 0.85), gls((0, 0.3, 3), 14, (2, 0.2, 2), 9)]),
        dict(B, anim='ereb_hand_glass_grip', t=1.08, yaw=60, label='«Стеклянная хватка»: сжатие', sub='grip 1.0 — стекло стягивается к кулаку',
             fx=[*flash((0.5, 1.4, 1.6), 2.0), gls((0.5, 1.3, 1.8), 22, (1.4, 0.8, 1.4), 11)]),
        dict(B, anim='ereb_hand_foreign_oath', t=0.6, yaw=40, pitch=14, dist=6.5, ty=22, label='«Чужая клятва»',
             sub='метка на игроке (багрянец) и на союзнике, который «платит» (стекло); нитей нет',
             fx=[sp('ereb_hand_oath_mark', (-2.2, 2.5, 4.5), 1, (0, 0, 0), (0.9, 0.9), CR_, 0.95, spin=0),
                 sp('ereb_hand_oath_mark', (2.4, 2.4, 5.2), 1, (0, 0, 0), (0.6, 0.6), GH, 0.9, spin=0), *flash((-2.2, 1.0, 4.5), 1.6, CR_, 0.35)],
             **{'with': oath_t}),
        dict(B, anim='ereb_hand_thousand_reflections', t=0.8, yaw=200, pitch=24, dist=9.5, ty=20, label='«Тысяча отражений»',
             sub='6 зеркал вокруг арены (меш ereb_hand_mirror), рапира к небу', meshes=mir),
        dict(N, model='ereb_hand', anim='ereb_hand_reflection_strike', t=0.45, yaw=120, pitch=10, dist=4.6, ty=20, label='отражение бьёт',
             sub='настоящий удар: рябь зеркала, блик у цели; ложный — лишь блик',
             meshes=[dict(mesh='ereb_hand_mirror', pos=[0, 0, -1.6], ry=0)], fx=[*flash((0.1, 1.4, 2.6), 0.9, GO), *flash((0, 1.5, -1.5), 2.2, GH, 0.4)],
             **{'with': [steve(0.1, 3.2)]}),
    ]
    sh('t31_spells.jpg', cells, 3, (1800, 1100))
    # ---------------------------------------------------------------- особые: «Длань Лжи», «Падение маски»
    shard_ring = []
    for i in range(5):
        a = i * 2 * math.pi / 5 + 0.3
        shard_ring.append(dict(mesh='ereb_hand_mask_shard', pos=[6 * math.sin(a), 1.8 + 0.6 * (i % 3), 6 * math.cos(a) + 3], ry=math.degrees(a) + 180,
                               scale=1.4))
    players = [steve(-3.0, 6.5, 200), steve(2.5, 7.0, 160), steve(0.0, 9.0, 180)]
    cells = [
        dict(N, model='steve', yaw=235, pitch=6, dist=11, ty=110, label='«Длань Лжи» (66%)', bg=VIOLET,
             sub='с неба опускается огромная рука — та же призрачная рука, ×5 (модель ereb_hand_giant); Эреб — за игроком, «Длань» к небу',
             fx=[ground('illusion_seal', (0, 0, 0), 4, GL, 0.6)],
             **{'with': [dict(model='ereb_hand', anim='ereb_hand_hand_of_lies', t=1.2, x=0, z=150, ry=0),
                         giant('ereb_hand_giant_descend', 0, 5.2, -1.7, 0.6)]}),
        dict(N, model='steve', y=44, yaw=330, pitch=10, dist=8.0, ty=70, label='поймала', bg=VIOLET,
             sub='игрок в кулаке (ereb_hand_giant_fist), поднят; 6 с видит ложную арену',
             fx=[*flash((0, 2.6, 0), 3.0, GH, 0.35), gls((0, 2.4, 0), 20, (2, 1.5, 2), 13)],
             **{'with': [dict(model='ereb_hand', anim='ereb_hand_hand_of_lies', t=2.0, x=0, z=150, ry=0),
                         giant('ereb_hand_giant_fist', 0, 1.5 + 1.1 - FIST_DY, -FIST_DZ, 0.3)]}),
        dict(N, model='ereb_hand', anim='ereb_hand_mask_fall', t=0.85, yaw=30, pitch=4, dist=2.2, ty=26, label='«Падение маски» (45%)',
             sub='«Длань» срывает маску (tear 0.85)', fx=[sp('spark_soft', (0.15, 1.9, 0.6), 10, (0.25, 0.25, 0.25), (0.08, 0.15), GO, 0.9)]),
        dict(N, model='ereb_hand', anim='ereb_hand_mask_fall', t=1.15, yaw=200, pitch=12, dist=3.4, ty=34, hideBones=['mask'], label='маска разбита',
             sub='shatter 1.1: осколки разлетаются по арене', fx=[*flash((-0.2, 2.8, 0.6), 3.0), gls((-0.2, 2.8, 0.6), 30, (2.5, 1.2, 2.5), 17),
                                                                  *bfl((-0.2, 2.8, 0.6), 6, (1.2, 0.6, 1.2))]),
        dict(N, model='ereb_hand', anim='ereb_hand_idle', t=1.0, yaw=200, pitch=18, dist=8.5, ty=24, hideBones=['mask'], label='осколки кружат',
             sub='по осколку на игрока (в нём — его лицо: slot player_face), стрелка к своему', meshes=shard_ring +
             [dict(mesh='ereb_hand_mask_arrow', pos=[-2.6, 1.2, 5.4], ry=150, scale=1.6)], **{'with': players}),
        dict(N, model='ereb_hand', anim='ereb_hand_idle', t=1.0, yaw=210, pitch=10, dist=5.0, ty=20, hideBones=['mask'], label='разбил свой / не успел',
             sub='слева — свой осколок бьётся (стекло, бабочки), справа — взрыв не разбитого',
             fx=[*flash((-2.4, 1.8, 4.0), 1.4), gls((-2.4, 1.8, 4.0), 18, (0.5, 0.5, 0.5), 19), *bfl((-2.4, 1.8, 4.0), 3, (0.3, 0.3, 0.3)),
                 *flash((2.6, 1.0, 4.6), 2.6, CR_, 0.8), gls((2.6, 1.0, 4.6), 24, (0.8, 0.8, 0.8), 21), ground('wave_ring', (2.6, 0, 4.6), 3, CR_, 0.7)],
             **{'with': [steve(-2.4, 4.6), steve(2.6, 4.6)]}),
        dict(N, model='ereb_hand', anim='ereb_hand_mask_return', t=0.6, yaw=25, pitch=4, dist=2.2, ty=26, variant='mended', label='маска собирается',
             sub='осколки слетаются к лицу, mend 0.7 → текстура _mended', fx=[gls((0.15, 1.75, 0.6), 18, (0.8, 0.6, 0.8), 23)]),
        dict(N, model='ereb_hand', anim='ereb_hand_phase3', t=0.95, yaw=20, pitch=4, dist=2.2, ty=26, variant='cracked', label='фаза 3: маска трескается',
             sub='crack 0.9 → _cracked, золото в трещинах', fx=[sp('spark_soft', (0.15, 1.8, 0.5), 12, (0.2, 0.2, 0.2), (0.06, 0.12), GO, 0.9)]),
    ]
    sh('t31_special.jpg', cells, 4, (2000, 1000))
    # ---------------------------------------------------------------- финал: «Полное Раскрытие», мир сна, ложная смерть, добивание
    world = [ground('ereb_hand_mirror_floor', (0, 0, 0), 22, GL, 0.55), gls((0, 3, 0), 60, (14, 3, 14), 31), *bfl((0, 3, 0), 16, (12, 2.5, 12))]
    cells = [
        dict(N, model='ereb_hand', anim='ereb_hand_full_reveal', t=1.6, yaw=20, pitch=8, dist=4.4, ty=30, variant='cracked', label='«Полное Раскрытие» (20%)',
             sub='рука над головой раскрывается (open 1.4), рой бабочек', fx=[*bfl((0, 1.6, 0), 18, (2.5, 1.5, 2.5))]),
        dict(N, model='ereb_hand', anim='ereb_hand_full_reveal', t=2.62, yaw=20, pitch=8, dist=4.4, ty=30, variant='cracked', label='каст',
             sub='cast 2.6 — белая вспышка, мир раскрывается', fx=[*flash((0, 2, 0), 9.0, WH, 0.7), *flash((0.7, 3.6, 0.2), 2.0, GH, 0.9)]),
        dict(N, model='ereb_hand', anim='ereb_hand_idle', t=1.0, yaw=200, pitch=6, dist=11, ty=120, variant='cracked', bg=VIOLET,
             label='мир сна', sub='зеркальный пол r30, Длань над ареной (в игре +22 бл., в кадре ниже), стекло и бабочки; бой внутри сна',
             fx=world, **{'with': [steve(-3, 6), steve(3.5, 7), giant('ereb_hand_giant_hover', -1, 9.5, 2, 1.5, scale=6)]}),
        dict(N, model='ereb_hand', anim='ereb_hand_guard', t=0.2, yaw=150, pitch=14, dist=9, ty=40, variant='cracked', bg=VIOLET,
             label='Длань бьёт во сне', sub='тень и кольцо 1.5 с, удар плашмя (урон ненастоящий)',
             fx=[ground('illusion_seal', (3.5, 0, 6.5), 4, GL, 0.7), ground('ereb_hand_mirror_floor', (0, 0, 0), 14, GL, 0.4)],
             **{'with': [steve(3.5, 6.5), giant('ereb_hand_giant_slam', 3.5, 3.0, 4.6, 0.4, scale=4)]}),
        dict(N, model='ereb_hand', anim='ereb_hand_false_death', t=0.75, yaw=25, pitch=6, dist=3.6, ty=24, variant='cracked', label='ложная смерть 1/3',
             sub='рука трескается и осыпается (hand_break 0.7)', fx=[*flash((0.97, 2.0, -0.3), 1.8, GH, 0.6), gls((0.97, 2.0, -0.3), 26, (0.9, 0.7, 0.9), 37)]),
        dict(N, model='ereb_hand', anim='ereb_hand_false_death', t=1.8, yaw=15, pitch=4, dist=2.4, ty=26, variant='cracked', label='ложная смерть 2/3',
             sub='«А вы...стали сильнее» (speak 1.6)'),
        dict(N, model='ereb_hand', anim='ereb_hand_false_death', t=3.85, yaw=20, pitch=6, dist=3.6, ty=24, variant='cracked', label='ложная смерть 3/3',
             sub='vanish 3.8 — распадается на множество бабочек', fx=[*flash((0, 1.1, 0), 2.6, WH, 0.6), *bfl((0, 1.1, 0), 40, (1.0, 1.2, 1.0))]),
        dict(N, model='ereb_hand', anim='ereb_hand_finisher', t=1.6, yaw=95, pitch=6, dist=4.4, ty=30, label='добивание 1/2',
             sub='рука обхватила жертву за торс и подняла на 1.4 бл., сжимает (squeeze 1.5) — по ней бежит стеклянная корка',
             fx=[sp('aura_shell', (0.5, 2.0, 1.35), 1, (0, 0, 0), (1.4, 2.2), GH, 0.55, spin=0), gls((0.5, 2.0, 1.35), 12, (0.4, 0.8, 0.4), 41)],
             **{'with': [steve(0.5, 1.38, y=1.45)]}),
        dict(N, model='ereb_hand', anim='ereb_hand_finisher', t=2.15, yaw=95, pitch=6, dist=4.4, ty=30, label='добивание 2/2',
             sub='shatter 2.1 — жертва трескается стеклом и рассыпается бабочками',
             fx=[*flash((0.5, 2.5, 1.35), 2.4), gls((0.5, 2.4, 1.35), 40, (0.7, 1.0, 0.7), 43), *bfl((0.5, 2.5, 1.35), 10, (0.6, 0.8, 0.6))]),
        dict(N, model='ereb_hand', anim='ereb_hand_spawn', t=1.4, yaw=25, pitch=8, dist=4.0, ty=26, label='появление',
             sub='рука собирается из стекла (form_hand 0.6), Эреб — из роя (form 1.8)', hideBones=[],
             fx=[gls((0.97, 2.3, -0.3), 20, (1.0, 0.8, 1.0), 47), *bfl((0, 1.2, 0), 26, (2.0, 1.2, 2.0))]),
    ]
    for c in cells:
        if c.get('label') == 'появление':
            c['op'] = 1
    sh('t31_finale.jpg', cells, 5, (2400, 1000))
    shots_spells2(M, args)


# ================================================================== вторая партия (владелец 20.11): +4 заклинания и «Ложный рассвет»
SHADOW = '#000000'


def shadow(x, z, r=0.5, op=0.55):
    """тень под ногами (в кадрах её нет — рисуем пятном, чтобы было видно: у двойника «Ложного отступления» её НЕТ)"""
    return dict(ground('glow', (x, 0, z), r, SHADOW, op), add=False)


GOLD = '#E8B84A'
_FK = {}


def fkp(anim, t, bone, local):
    """точка кости по прямой кинематике → координаты кадра (x — вправо от Эреба, y — вверх, z — вперёд), блоки"""
    import json
    import ereb_hand_fk as F
    if not _FK:
        _FK['an'] = json.load(open(os.path.join(F.A, 'animations', 'entity', 'ereb_hand.animation.json'), encoding='utf-8'))['animations']
        _FK['m'] = F.Model()
    m = _FK['m']
    p = m.point(m.world(F.sample(_FK['an'][anim], t)), bone, local)
    return (-p[0] / 16, p[1] / 16, -p[2] / 16)


def gauntlet(anim, t):
    return fkp(anim, t, 'left_arm', [6, 11.5, 0])


def palm(anim, t):
    return fkp(anim, t, 'ghost_palm', [-15.5, 35.5, 4.25])


def bfly(at, real, size=0.5, seed=1):
    o = [sp('mote_butterfly', at, 1, (0, 0, 0), (size, size), GL, 0.85, seed, spin=0)]
    if real:
        o.append(dict(sp('ereb_hand_butterfly_rim', at, 1, (0, 0, 0), (size * 1.02, size * 1.02), GOLD, 1.0, seed, spin=0), add=False))
    return o


def orb(at, s=1.0):
    return [*flash(at, 0.9 * s, FL, 0.9), sp('cult_flame_tongue', at, 7, (0.15, 0.15, 0.15), (0.35 * s, 0.55 * s), FL, 0.8, 61, spin=0.05),
            sp('spark_soft', at, 8, (0.25, 0.25, 0.25), (0.06, 0.12), GO, 0.9, 62), *flash(at, 0.35 * s, GO, 0.9)]


def shots_spells2(M, args):
    three = args[args.index('--three') + 1] if '--three' in args else None
    sh = lambda name, cells, cols, size: R.sheet(os.path.join(MEDIA, name), {'cols': cols, 'cells': cells}, three, size)
    B = dict(N, model='ereb_hand', pitch=8, dist=4.0, ty=22)
    path = [(0.05 + 0.02 * k, 1.5 - 0.02 * k, 1.0 + 0.35 * k) for k in range(7)]
    trail = [sp('glow', p, 1, (0, 0, 0), (0.5 - 0.04 * i, 0.5 - 0.04 * i), FL, 0.35, 70 + i, spin=0) for i, p in enumerate(path)]
    copy_ = dict(model='traitor', anim='instant_slash', t=0.25, op=0.6)
    cells = [
        # «Пламя-подменыш»
        dict(B, anim='ereb_hand_changeling_flame', t=0.45, yaw=35, pitch=6, dist=3.6, ty=26, label='«Пламя-подменыш»: шар в «Длани»',
             sub='charge 0.2 — огонь в поднятой «Длани»', fx=orb(gauntlet('ereb_hand_changeling_flame', 0.45))),
        dict(N, model='steve', hide=True, yaw=95, pitch=12, dist=6.8, ty=22, h=34, label='бросок → подмена → союзник',
             sub='throw 0.65; золотое мерцание, затем бабочка — в союзника',
             fx=[*[dict(f, at=[f['at'][0], f['at'][1], f['at'][2] - 3.2]) for f in trail], *orb((0.15, 1.4, 0.1), 0.9),
                 *flash((0.2, 1.35, 1.0), 1.3, GO, 0.8), gls((0.3, 1.35, 1.3), 10, (0.3, 0.3, 0.3), 63),
                 *bfly((1.1, 1.3, 2.2), True, 0.6), *flash((1.1, 1.3, 2.2), 0.7, FL, 0.4)],
             **{'with': [dict(model='ereb_hand', anim='ereb_hand_changeling_flame', t=0.9, z=3.2 * 16), steve(0, 4.0), steve(2.0, 3.4, 200)]}),
        # «Ложное отступление»
        dict(B, anim='ereb_hand_false_retreat', t=0.45, yaw=80, pitch=6, dist=4.6, ty=22, label='«Ложное отступление»: прыжок назад',
             sub='leap 0.25 — отскок ≈4 бл. (код); land 0.65 — двойник',
             fx=[shadow(0, 0), gls((0, 0.3, 0.3), 10, (0.5, 0.2, 0.5), 64), *bfl((0, 0.6, 0.5), 3, (0.4, 0.3, 0.4))]),
        dict(N, model='ereb_hand', anim='ereb_hand_false_retreat_open', t=0.5, yaw=-95, pitch=10, dist=8.5, ty=24,
             label='двойник без тени → удар в спину', sub='двойник «открыт», тени нет; настоящий бьёт в спину (hit 0.35)',
             fx=[shadow(0.2, 2.2), shadow(0.6, 4.0, 0.6), *flash((0.45, 1.3, 3.9), 1.6, GH, 0.5), gls((0.5, 1.2, 3.8), 14, (0.5, 0.8, 0.5), 65),
                 *flash((0.25, 1.4, 2.4), 0.6, GO, 0.9)],
             **{'with': [steve(0.2, 2.2, 180), dict(model='ereb_hand', anim='ereb_hand_false_retreat_strike', t=0.35, x=-0.6 * 16, z=-4.0 * 16 - 0,
                                                   ry=180)]}),
        # «Отражение-предатель»
        dict(N, model='steve', hide=True, yaw=125, pitch=10, dist=6.6, ty=22, h=34, label='«Отражение-предатель»: из зеркала',
             sub='mirror 0.5 — зеркало; emerge 1.2 — копия игрока выходит',
             meshes=[dict(mesh='ereb_hand_mirror', pos=[0.4, 0, 2.6], ry=180, scale=0.8)],
             fx=[*flash((0.4, 1.3, 2.4), 1.8, GH, 0.5), gls((0.4, 1.2, 2.1), 14, (0.5, 0.9, 0.3), 66),
                 *flash((lambda p: (p[0], p[1], p[2] - 2.8))(palm('ereb_hand_traitor_reflection', 1.2)), 0.8, GO, 0.8)],
             **{'with': [dict(model='ereb_hand', anim='ereb_hand_traitor_reflection', t=1.2, z=2.8 * 16), steve(-0.2, 3.8, 180),
                         dict(copy_, x=0.4 * 16, z=-1.8 * 16, ry=180, t=0.0, anim=None)]}),
    ]
    cells += [
        dict(N, model='traitor', anim='instant_slash', t=0.25, op=0.6, yaw=150, pitch=6, dist=5.0, ty=20, h=34,
             label='копия бьёт союзников (6 с)', sub='скин игрока + стекло traitor_glass.png, его меч',
             fx=[gls((0, 1.2, 0), 18, (0.4, 0.9, 0.4), 67), *flash((0.2, 1.3, 1.4), 0.8, GO, 0.7)],
             **{'with': [steve(0.3, 1.8, 180), steve(-1.8, -0.6, 30)]}),
        dict(N, model='traitor', op=0.55, yaw=20, pitch=8, dist=4.4, ty=20, h=34, label='разбита / взрыв',
             sub='оригинал — 1 удар, другие — 3; 6 с — взрыв r3',
             fx=[*flash((0, 1.0, 0), 2.0, GH, 0.6), gls((0, 1.0, 0), 34, (0.6, 0.9, 0.6), 68), *bfl((0, 1.2, 0), 6, (0.6, 0.6, 0.6)),
                 ground('wave_ring', (0, 0, 0), 3.0, GO, 0.8), ground('higher_cracks', (0, 0, 0), 3.0, GL, 0.6)]),
        # «Рой лжи»
        dict(B, anim='ereb_hand_swarm_of_lies', t=0.5, yaw=-30, pitch=4, dist=2.8, ty=24, label='«Рой лжи»: бабочки в «чаше»',
             sub='gather 0.3 — в сложенной призрачной руке кружат бабочки',
             fx=[*bfl(palm('ereb_hand_swarm_of_lies', 0.5), 6, (0.2, 0.15, 0.2)), *flash(palm('ereb_hand_swarm_of_lies', 0.5), 0.35, GH, 0.4)]),
        dict(B, anim='ereb_hand_swarm_of_lies', t=0.8, yaw=160, pitch=22, dist=8.5, ty=20, label='выпуск: 12 бабочек',
             sub='release 0.75 — 6 ложных и 6 настоящих',
             fx=[*flash(palm('ereb_hand_swarm_of_lies', 0.8), 1.4, GH, 0.6)] + [x for i in range(12) for x in bfly(
                 (-3.2 + 0.58 * i, 1.4 + 0.5 * math.sin(i * 1.7), 2.4 + 1.2 * abs(math.sin(i * 0.9)) + 0.25 * i), i % 2 == 0, 0.5, 80 + i)],
             **{'with': [steve(-2.5, 7.0), steve(2.8, 7.5)]}),
        dict(N, model='steve', hide=True, yaw=0, pitch=0, dist=0.75, ty=26, h=34, bg=VIOLET, label='ложная и настоящая',
             sub='слева настоящая — золотая кромка; справа ложная',
             fx=[*bfly((-0.45, 1.65, 0), False, 0.75, 91), *bfly((0.45, 1.65, 0), True, 0.75, 92),
                 sp('spark_soft', (0.45, 1.65, 0), 6, (0.3, 0.3, 0.1), (0.04, 0.08), GO, 0.9, 93)]),
    ]
    sh('t31_spells2.jpg', cells, 5, (2500, 1100))
    # ---------------------------------------------------------------- «Ложный рассвет»
    DAWN = 0x3a2c38
    orbit_ = [x for i in range(10) for x in bfly((1.8 * math.cos(i * 0.63), 0.6 + 0.22 * (i % 5), 1.8 * math.sin(i * 0.63)), False, 0.32, 100 + i)]
    dawn = [ground('dawn_sunrise', (0, 0, 0), 5.0, GO, 0.5), *flash((0, 6, -18), 14, '#FFD9A0', 0.35)]
    cells = [
        dict(N, model='ereb_hand', anim='ereb_hand_false_dawn', t=0.3, variant='mended', yaw=25, pitch=4, dist=3.4, ty=24, label='«Ложный рассвет» (33%)',
             sub='шатается (0–0.25 с)'),
        dict(N, model='ereb_hand', anim='ereb_hand_false_dawn', t=2.0, variant='mended', yaw=25, pitch=8, dist=4.0, ty=18, bg=DAWN,
             label='на колене (kneel 0.5)', sub='полоса скрыта, небо светлеет, фанфара «победы»; 4 с неуязвим', fx=dawn + orbit_),
        dict(N, model='ereb_hand', anim='ereb_hand_false_dawn', t=2.0, variant='mended', yaw=-90, pitch=2, dist=3.4, ty=16, bg=DAWN,
             label='колено сбоку', sub='колено и носок над землёй, накидка и полы — назад', fx=[shadow(0, 0, 0.7)]),
        dict(N, model='ereb_hand', anim='ereb_hand_false_dawn', t=2.5, variant='mended', yaw=200, pitch=30, dist=12, ty=20, bg=DAWN,
             label='подсказка: бабочки НЕ улетают', sub='кружат вокруг него все 4 с (у настоящего поражения — разлетаются)',
             fx=dawn + orbit_, **{'with': [steve(-3, 6), steve(3.5, 7), steve(0.5, 9)]}),
        dict(N, model='ereb_hand', anim='ereb_hand_false_dawn', t=4.75, variant='mended', yaw=25, pitch=4, dist=3.6, ty=24,
             label='встаёт (rise 4.5)', sub='бабочки стягиваются к нему', fx=[*bfl((0, 1.2, 0), 10, (1.0, 0.8, 1.0))]),
        dict(N, model='ereb_hand', anim='ereb_hand_false_dawn', t=5.05, variant='mended', yaw=200, pitch=30, dist=9, ty=20,
             label='волна (wave 5.0)', sub='≤6 бл. — 60% ХП (багряное r6), дальше — 20%; потом маска трескается',
             fx=[*flash((0, 1.6, 0), 4.0, WH, 0.6), ground('wave_ring', (0, 0, 0), 6, CR_, 0.9), ground('wave_ring', (0, 0, 0), 11, GO, 0.8),
                 gls((0, 1.2, 0), 40, (3, 1, 3), 110), *bfl((0, 1.4, 0), 12, (2.5, 1, 2.5))],
             **{'with': [steve(-3, 4), steve(3.5, 8.5), steve(0.5, 10)]}),
    ]
    sh('t31_false_dawn.jpg', cells, 3, (1800, 1100))
