#!/usr/bin/env python3
"""
T31 «Эреб, Длань Лжи» — проверочные кадры docs/media/t31_*.jpg (Playwright + three.js, шаблон tools/ereb_hand_preview.template.html).
Вызывается из tools/gen_ereb_hand.py --shots [--three путь/three.min.js] (three r128 локально: npm i three@0.128.0).
  t31_vs_t30.jpg           — рядом с принятым Эребом T30, один масштаб и свет (свет кадров T26 и дневной)
  t31_vs_cult_leader.jpg   — рядом с эталоном (Глава Культа T26), один масштаб и свет
  t31_model.jpg            — 4 стороны, лицо и маска (4 вида), в темноте (глоумаска), «Длань Лжи», призрачная рука, рапира
  t31_poses.jpg            — анимации: ключевые кадры с событиями
"""
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
