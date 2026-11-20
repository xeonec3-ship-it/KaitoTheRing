#!/usr/bin/env python3
"""Проверочный лист плаща Мартина (правка 20.11): сбоку, ключевые позы → docs/media/t29_cape_fix.jpg.
  python3 tools/martin_cape_check.py [--three путь/three.min.js] [--out файл.jpg] [--yaw 90]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import martin_render as MR  # noqa: E402

POSES = [('martin_idle', 0.5, 'покой'), ('martin_walk', 0.4, 'шаг'), ('martin_swing', 0.75, 'размах (удар)'),
         ('martin_overhead', 1.0, 'удар сверху'), ('martin_shield_bash', 0.8, 'рывок щитом'), ('martin_command', 1.0, 'приказ'),
         ('martin_spawn', 1.5, 'появление: на колене'), ('martin_block_yield', 3.0, 'сдача'), ('martin_npc_idle', 1.0, 'NPC'),
         ('martin_phase3', 0.8, 'фаза 3: присед'), ('martin_cavalry', 2.2, '«Конница»: взмах'), ('martin_warcry', 0.8, '«+4» клич'),
         ('martin_replica_break', 0.95, 'Реплика'), ('martin_thrust', 0.65, 'выпад'), ('charge_raised_hand', 1.0, 'Iron\'s каст')]


def main(args):
    three = args[args.index('--three') + 1] if '--three' in args else None
    out = args[args.index('--out') + 1] if '--out' in args else os.path.join(MR.HERE, '..', 'docs', 'media', 't29_cape_fix.jpg')
    yaw = float(args[args.index('--yaw') + 1]) if '--yaw' in args else 90
    cells = [dict(model='martin', anim=a, t=t, yaw=yaw, pitch=4, dist=3.3, label=lab, sub='%s · %.2f с' % (a, t)) for a, t, lab in POSES]
    MR.sheet(out, {'cols': 5, 'cells': cells}, three, (2000, 1500))


if __name__ == '__main__':
    main(sys.argv[1:])
