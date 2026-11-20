#!/usr/bin/env python3
"""
Листы «до / после» проверки анимаций 20.11: docs/media/t26_anim_check.jpg, docs/media/t30_anim_check.jpg.
«До» — анимации из git (коммит до правки, по умолчанию 41e3672), «после» — текущие assets. Кадры — tools/anim_check_render.py
(жёлтая стрелка — «вперёд» по взгляду босса, красная точка — остриё, синий брусок — жертва, зелёный шар — точка удара).
  python3 tools/anim_check_sheets.py [--before <коммит>] [--three путь/three.min.js]
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from anim_check_render import sheet  # noqa: E402

ROOT = os.path.join(HERE, '..')
MEDIA = os.path.join(ROOT, 'docs', 'media')
REL = 'src/main/resources/assets/pohsmp_core/animations/entity/%s.animation.json'


def load(boss, rev=None):
    if rev:
        txt = subprocess.run(['git', 'show', '%s:%s' % (rev, REL % boss)], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    else:
        txt = open(os.path.join(ROOT, REL % boss), encoding='utf-8').read()
    return json.loads(txt)['animations']


def ease_q(k):
    k = max(0.0, min(1.0, k))
    return 2 * k * k if k < .5 else 1 - (-2 * k + 2) ** 2 / 2


def cult_victim(t):
    """Жертва добивания Главы (код, письмо T26): 0–0.7 с — к 3.0 бл. впереди, 1.0–1.7 — подъём на +2.3 бл.; оси модели (босс ×1.75)."""
    k = max(0.0, min(1.0, t / 0.7))
    z = -(5 - 2 * k * k) * 16 / 1.75
    y = 2.3 * 16 / 1.75 * ease_q((t - 1.0) / 0.7)
    return dict(marks=[[0, y + 11.4, z, 1.4]], boxes=[[0, y, z, 4.6, 17.1, 2.6]])


def pair(boss, before, after, anim, t, view, label, extra=None, **kw):
    cells = []
    for tag, src in (('до', before), ('после', after)):
        if anim not in src:
            continue
        c = dict(anim=anim + '#' + tag, anim_json=src[anim], t=t, view=view, label='%s — %s' % (label, tag),
                 sub='%s · %.2f с · %s' % (anim, t, view), bad=tag == 'до', ok=tag == 'после')
        c.update(extra or {})
        c.update(kw)
        cells.append(c)
    return cells


def t26(rev, three):
    b, a = load('cult_leader', rev), load('cult_leader')
    D = dict(dist=190, ty=24)
    cells = []
    cells += pair('cult_leader', b, a, 'cult_leader_finisher', 1.7, 'side', 'Добивание: жертва на острие', cult_victim(1.7), **D)
    cells += pair('cult_leader', b, a, 'cult_leader_finisher', 2.2, '34', 'Добивание: kill', cult_victim(2.2), **D)
    cells += pair('cult_leader', b, a, 'cult_leader_ash_slash', 0.5, 'top', '«Пепел»: разрез вперёд по линии', None, **D)
    cells += pair('cult_leader', b, a, 'cult_leader_ash_slash', 0.5, 'side', '«Пепел»: slash сбоку', None, **D)
    cells += pair('cult_leader', b, a, 'cult_leader_sickle_throw', 1.0, 'top', '«Огненный серп»: бросок', None, **D)
    cells += pair('cult_leader', b, a, 'cult_leader_replica_break', 1.5, 'side', 'Реплика: взмах вверх', None, **D)
    cells += pair('cult_leader', b, a, 'cult_leader_pillars', 0.9, 'side', '«Столпы»: руки к небу', None, **D)
    cells += pair('cult_leader', b, a, 'cult_leader_brand', 0.55, 'side', '«Клеймо»: коса не в земле', None, **D)
    cells += pair('cult_leader', b, a, 'cult_leader_ash_trail_dash', 0.5, 'side', '«Пепельный след»: рывок', None, **D)
    cells += pair('cult_leader', b, a, 'scythe_sideslash_downslash_spinslash', 2.2, 'side', 'Плащ (Iron\'s): не вперёд', None, **D)
    cells += pair('cult_leader', b, a, 'magma_throw', 1.35, '34', 'Коса (Iron\'s): не сквозь ногу', None, **D)
    cells += pair('cult_leader', b, a, 'summon_fiery_daggers', 0.6, 'side', 'Коса (Iron\'s): не в земле', None, **D)
    sheet(os.path.join(MEDIA, 't26_anim_check.jpg'), 'cult_leader', cells, cols=6, three=three, size=(2400, 1640),
          title='T26 Глава Культа — проверка анимаций 20.11: до (красная рамка) / после (зелёная). Стрелка — «вперёд», красная точка — остриё')


def t30(rev, three):
    b, a = load('ereb', rev), load('ereb')
    D = dict(dist=125, ty=16)
    vic = dict(boxes=[[0, 0, -16, 7.5, 28, 4]], marks=[[0, 19, -14, 1.2]])
    cells = []
    cells += pair('ereb', b, a, 'ereb_phase', 0.8, 'side', 'Салют: клинок вверх', None, **D)
    cells += pair('ereb', b, a, 'ereb_glass_rain', 0.4, 'side', '«Стеклянный дождь»: к небу', None, **D)
    cells += pair('ereb', b, a, 'ereb_backstab', 0.45, 'side', 'Удар в спину: остриё в спине', vic, **D)
    cells += pair('ereb', b, a, 'ereb_spawn', 4.2, 'side', 'Появление: салют', None, **D)
    cells += pair('ereb', b, a, 'ereb_walk', 0.3, 'side', 'Шаг: полы мимо ног', None, **D)
    cells += pair('ereb', b, a, 'ereb_idle', 0.0, 'side', 'Покой: остриё над полом', None, **D)
    cells += pair('ereb', b, a, 'charge_arrow', 1.0, 'side', 'Полы (Iron\'s): не вперёд', None, **D)
    cells += pair('ereb', b, a, 'shoot_one_handed_ray', 0.1, 'side', 'Полы (Iron\'s): мимо ног', None, **D)
    cells += pair('ereb', b, a, 'cross_arms', 0.4, '34', 'Рапира (Iron\'s): не сквозь корпус', None, **D)
    fin = dict(boxes=[[0, 0, -21, 7.5, 28, 4]])
    for t, lab in ((0.3, 'vanish'), (0.7, 'appear'), (1.1, 'stab'), (1.9, 'kill')):
        c = dict(anim='ereb_finisher', anim_json=a['ereb_finisher'], t=t, view='side', label='Добивание (новое) — ' + lab, ok=True,
                 sub='ereb_finisher · %.2f с · жертва в 1.3 бл. перед ним' % t, **fin, **D)
        cells.append(c)
    sheet(os.path.join(MEDIA, 't30_anim_check.jpg'), 'ereb', cells, cols=6, three=three, size=(2400, 1640),
          title='T30 Эреб — проверка анимаций 20.11: до (красная рамка) / после (зелёная). Стрелка — «вперёд», красная точка — остриё')


if __name__ == '__main__':
    args = sys.argv[1:]
    rev = args[args.index('--before') + 1] if '--before' in args else '41e3672'
    three = args[args.index('--three') + 1] if '--three' in args else None
    which = [x for x in args if x in ('t26', 't30')] or ['t26', 't30']
    if 't26' in which:
        t26(rev, three)
    if 't30' in which:
        t30(rev, three)
