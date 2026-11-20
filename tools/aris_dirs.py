#!/usr/bin/env python3
"""
T28 «Арис» — проверочные листы направлений ударов и появления (правка 20.11):
  docs/media/t28_attack_dirs.jpg — каждая атака/каст в момент удара: сбоку (справа от неё) и сверху; жёлтая стрелка на полу — «вперёд»
                                   (взгляд модели, −z в осях Blockbench; в якорях fx это +z);
  docs/media/t28_spawn_fix.jpg  — кадры появления (spawn) и сдачи (surrender) с молотом.
  python3 tools/aris_dirs.py [--three путь/three.min.js] [--only dirs,spawn]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import aris_render as R          # noqa: E402

MEDIA = os.path.join(HERE, '..', 'docs', 'media')
A_ = 'animation.aris.'
HITS = [('slam', 0.75, 'удар по земле', 'impact 0.75'), ('swing', 0.62, 'размах', 'hit 0.62'), ('cast', 0.8, 'каст', 'cast 0.8'),
        ('forge', 1.0, '«Горн»', 'strike 1.0'), ('last_blow', 4.0, '«Последний удар»', 'blow 4.0'), ('phase2', 1.0, 'фаза 2', 'roar 1.0'),
        ('spawn', 7.0, 'появление', 'impact 7.0'), ('billet', 0.7, '«Заготовка»', 'throw 0.7'), ('chains', 0.8, '«Цепи кузни»', 'chains 0.8'),
        ('quench', 0.8, '«Закалка»', 'splash 0.8'), ('bellows', 0.8, '«Мехи»', 'gust 0.8'), ('replica_break', 1.5, 'Реплика', 'shatter 1.5')]


def cell(anim, t, label, sub, **kw):
    d = {'model': 'aris', 'anim': A_ + anim, 't': t, 'label': label, 'sub': sub, 'arrow': True}
    d.update(kw)
    return d


def run(three=None, only=None):
    if not only or 'dirs' in only:
        cells = []
        for a, t, lab, sub in HITS:
            cells.append(cell(a, t, lab, sub + ' · сбоку', yaw=90, pitch=6, dist=2.6))
            cells.append(cell(a, t, lab, sub + ' · сверху', yaw=0, pitch=88, dist=2.9, ty=10))
        R.sheet(os.path.join(MEDIA, 't28_attack_dirs.jpg'), {'cols': 6, 'cells': cells}, three, size=(2400, 1600))
    if not only or 'spawn' in only:
        cells = []
        for t in (4.5, 5.2, 5.8, 6.0, 6.3, 6.45, 6.55, 6.65, 6.75, 6.88, 7.0, 8.3):
            cells.append(cell('spawn', t, 'появление', '%g с' % t, yaw=40, pitch=6, variant='dim' if t < 6 else 'base', dist=3.0))
        for t in (6.3, 6.55, 6.8):
            cells.append(cell('spawn', t, 'появление', '%g с · спереди' % t, yaw=0, pitch=6, variant='base', dist=3.0))
        for t in (0.4, 0.8, 1.2, 2.6, 3.0, 3.2, 3.6, 5.0):
            cells.append(cell('surrender', t, 'сдача', '%.1f с' % t, yaw=55, pitch=10, variant='dim' if t < 2.6 else 'spent', dist=3.0))
        cells.append(cell('surrender', 5.0, 'сдача', '5.0 с · сверху', yaw=0, pitch=88, dist=2.9, ty=10, variant='spent'))
        R.sheet(os.path.join(MEDIA, 't28_spawn_fix.jpg'), {'cols': 6, 'cells': cells}, three, size=(2400, 1600))


if __name__ == '__main__':
    a = sys.argv[1:]
    run(a[a.index('--three') + 1] if '--three' in a else None, a[a.index('--only') + 1].split(',') if '--only' in a else None)
