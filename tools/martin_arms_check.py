#!/usr/bin/env python3
"""Лист «до/после» правки рук и оружия Мартина (20.11): ключевые моменты атак → docs/media/t29_arms_fix.jpg.
  python3 tools/martin_arms_check.py --before старый.animation.json [--three путь/three.min.js] [--out файл.jpg] [--yaw 35]
«До» — файл анимаций до правки (например: git show 268e678^:src/main/resources/assets/pohsmp_core/animations/entity/martin.animation.json)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import martin_render as MR  # noqa: E402

MOMENTS = [('martin_walk', 0.4, 'шаг'), ('martin_swing', 0.55, 'размах: замах'), ('martin_swing', 0.75, 'размах: удар'),
           ('martin_overhead', 0.7, 'сверху: замах'), ('martin_overhead', 0.95, 'сверху: удар'), ('martin_thrust', 0.6, 'выпад'),
           ('martin_shield_bash', 0.75, 'рывок щитом'), ('martin_command', 0.85, 'приказ'), ('martin_cavalry', 1.0, '«Конница»: к небу'),
           ('martin_volley', 1.2, 'залп: «пли!»'), ('martin_duel', 0.9, 'дуэль'), ('martin_warcry', 0.62, 'клич'),
           ('martin_phase3', 1.6, 'фаза 3: выдернул меч'), ('martin_spawn', 5.0, 'появление: салют'), ('martin_npc_idle', 1.0, 'NPC'),
           ('martin_replica_break', 0.9, 'Реплика')]


def main(args):
    three = args[args.index('--three') + 1] if '--three' in args else None
    out = args[args.index('--out') + 1] if '--out' in args else os.path.join(MR.HERE, '..', 'docs', 'media', 't29_arms_fix.jpg')
    yaw = float(args[args.index('--yaw') + 1]) if '--yaw' in args else 35
    before = json.load(open(args[args.index('--before') + 1], encoding='utf-8'))['animations']
    d = MR.data(['martin'])
    an = d['martin']['anims']
    cells = []
    for a, t, lab in MOMENTS:
        an['before:' + a] = before[a]
        cells.append(dict(model='martin', anim='before:' + a, t=t, yaw=yaw, label='ДО · ' + lab, sub='%s %.2f с' % (a, t)))
        cells.append(dict(model='martin', anim=a, t=t, yaw=yaw, label='ПОСЛЕ · ' + lab, sub='%s %.2f с' % (a, t)))
    MR.shoot(MR.page(d, {'cols': 8, 'cells': cells}, three), out, (2400, 1200))


if __name__ == '__main__':
    main(sys.argv[1:])
