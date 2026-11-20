#!/usr/bin/env python3
"""
T30 «Эреб» — проверочные кадры docs/media/t30_*.jpg (Playwright + three.js, шаблон tools/ereb_preview.template.html).
Вызывается из tools/gen_ereb.py --shots [--three путь/three.min.js] (three r128 локально: npm i three@0.128.0).
Эффекты на кадрах — условные (спрайты-маски T22 из textures/sigil, тонированные), чтобы увидеть композицию; в игре их рисует движок fx.
"""
import os

from PIL import Image, ImageDraw

import gen_ereb_render as R
import gen_ereb_fx as FX

MEDIA = FX.MEDIA
N = {'neutral': True}
GL, GH, GO, WH = FX.GLASS, FX.GLASS_HI, FX.GOLD_HI, '#ffffff'


def bfly(at, n, spread, size=(0.22, 0.38), seed=3, color=GL):
    return [{'tex': 'mote_butterfly', 'n': n, 'at': at, 'spread': spread, 'size': list(size), 'color': color, 'seed': seed, 'op': 0.9},
            {'tex': 'mote_butterfly_side', 'n': max(1, n // 2), 'at': at, 'spread': spread, 'size': list(size), 'color': GO, 'seed': seed + 5,
             'op': 0.8}]


def flash(at, size, color=WH, op=0.9):
    return [{'tex': 'glow', 'n': 1, 'at': at, 'spread': [0, 0, 0], 'size': [size, size], 'color': color, 'op': op, 'spin': 0}]


def shards(at, n, spread, seed=5):
    return [{'tex': 'mote_glass', 'n': n, 'at': at, 'spread': spread, 'size': [0.12, 0.26], 'color': GH, 'seed': seed, 'spin': 1.5}]


def seal(r, color=GL, op=0.55):
    return [{'tex': 'illusion_seal', 'n': 1, 'at': [0, 0, 0], 'spread': [0, 0, 0], 'size': [2 * r, 2 * r], 'color': color, 'ground': True, 'op': op}]


def shots(M, args):
    three = args[args.index('--three') + 1] if '--three' in args else None
    sh = lambda name, cells, cols, size: R.sheet(os.path.join(MEDIA, name), {'cols': cols, 'cells': cells}, three, size)
    # ---------------------------------------------------------------- модель
    cells = [
        dict(N, model='ereb_noitem', yaw=0, pitch=4, label='Эреб', sub='спереди'),
        dict(N, model='ereb_noitem', yaw=180, pitch=4, label='сзади', sub='шлица, полумесяц, кайма'),
        dict(N, model='ereb_noitem', yaw=-90, pitch=4, label='сбоку', sub='воротник-стойка, полы'),
        dict(N, model='ereb', anim='ereb_idle', t=1.0, yaw=30, pitch=6, label='покой', sub='рапира опущена, рука за спиной'),
        dict(N, model='ereb_noitem', yaw=20, pitch=2, dist=0.95, ty=27, label='лицо', sub='как на скине: голубые глаза'),
        dict(N, model='ereb_noitem', smile=True, yaw=20, pitch=2, dist=0.95, ty=27, label='улыбка', sub='текстура ereb_smile (финал)'),
        dict(model='ereb', anim='ereb_idle', t=0.5, yaw=15, pitch=4, dist=1.6, ty=22, dim=0.22, label='в темноте',
             sub='глоумаска: радужки, стекло броши и пряжек'),
        dict(model='ereb', anim='ereb_idle', t=1.0, yaw=150, pitch=8, label='покой сзади', sub='левая рука за спиной'),
    ]
    sh('t30_model.jpg', cells, 4, (1600, 1000))
    # ---------------------------------------------------------------- рядом с эталоном (один масштаб и свет)
    cells = []
    for light, lab in (({}, 'свет кадров T26'), (N, 'дневной свет')):
        for yaw, sub in ((20, 'три четверти'), (0, 'спереди'), (200, 'сзади')):
            c = dict(light, model='ereb', anim='ereb_idle', t=1.0, yaw=yaw, pitch=6, h=36, dist=3.1, x=-12,
                     label='Эреб и Глава Культа', sub='%s, %s' % (lab, sub), **{'with': [{'model': 'cult_leader', 'x': 12}]})
            cells.append(c)
    sh('t30_with_leader.jpg', cells, 3, (1800, 1000))
    # ---------------------------------------------------------------- сравнение со скином владельца
    ref_cells = [dict(N, model='ereb_noitem', yaw=y, pitch=0, fov=12, dist=2.3, label=lab)
                 for y, lab in ((0, 'спереди'), (180, 'сзади'), (-90, 'сбоку (правый)'), (90, 'сбоку (левый)'))]
    tmp = os.path.join(MEDIA, '_t30_ref.jpg')
    sh('_t30_ref.jpg', ref_cells, 4, (1600, 700))
    rend = Image.open(tmp).convert('RGB')
    os.remove(tmp)
    canvas = Image.new('RGB', (1600, 1420), (26, 27, 32))
    d = ImageDraw.Draw(canvas)
    f1 = FX.font(26)
    d.text((20, 12), 'Скин владельца (фото)  →  модель Эреба (дневной свет)', font=f1, fill=(235, 228, 212))
    for i, nm in enumerate(('front', 'back', 'side1', 'side2')):
        im = Image.open(os.path.join(FX.ROOT, 'docs', 'references', 't30', 'ereb_%s.jpg' % nm)).convert('RGB')
        im.thumbnail((380, 640))
        canvas.paste(im, (10 + i * 400 + (380 - im.width) // 2, 56))
    canvas.paste(rend, (0, 712))
    canvas.save(os.path.join(MEDIA, 't30_vs_skin.jpg'), quality=90)
    print('wrote docs/media/t30_vs_skin.jpg')
    # ---------------------------------------------------------------- анимации
    A_ = [('ereb_walk', 0.3, 30, 'шаг', 'полы следуют за ногами'), ('ereb_guard', 0.0, 50, 'стойка «ан гард»', 'правый бок к врагу'),
          ('ereb_lunge', 0.3, 70, 'выпад', '0.3 с — сжался'), ('ereb_lunge', 0.5, 70, 'выпад', '0.5 с — укол (hit)'),
          ('ereb_flurry', 0.8, 60, 'серия', '2-й укол (0.8 с)'), ('ereb_parry', 0.15, 40, 'парирование', 'parry 0.15 с'),
          ('ereb_shard_cast', 0.55, 30, 'магия руками', 'стеклянные осколки (release 0.55)'),
          ('ereb_cast_illusion', 0.75, 20, 'каст иллюзий', 'щелчок пальцами (cast 0.75)'), ('ereb_disguise', 0.4, 20, 'смена облика', 'ладонь по лицу (swap 0.5)'),
          ('ereb_vanish', 0.55, 30, '«Ложный союзник»', 'исчезает (gone 0.6)'), ('ereb_backstab', 0.45, 60, '«Ложный союзник»', 'удар в спину (stab 0.45)')]
    cells = [dict(N, model='ereb', anim=a, t=t, yaw=y, pitch=8, dist=3.2, ty=15, label=l, sub=s) for a, t, y, l, s in A_]
    sh('t30_anims.jpg', cells, 4, (1800, 1260))
    # ---------------------------------------------------------------- появление и финал (поза + условные эффекты)
    cells = [
        dict(model='ereb', anim='ereb_spawn', t=1.0, yaw=25, pitch=12, dist=2.8, ty=16, hide=True, label='появление 1.0 с',
             sub='рой стеклянных бабочек кружит, печать', fx=seal(2.4) + bfly([0, 1.3, 0], 40, [1.3, 1.1, 1.3], seed=4)),
        dict(model='ereb', anim='ereb_spawn', t=2.25, yaw=25, pitch=12, dist=2.8, ty=16, label='2.2 с — form', sub='звон стекла, бабочки разлетаются',
             fx=seal(2.4) + flash([0, 1.1, 0], 2.2, op=0.55) + shards([0, 1.1, 0], 26, [1.2, 1.0, 1.2]) + bfly([0, 1.2, 0], 18, [1.6, 1.0, 1.6], seed=8)),
        dict(model='ereb', anim='ereb_spawn', t=3.3, yaw=35, pitch=10, dist=2.8, ty=16, label='3.0 с — поклон', fx=seal(2.4, op=0.35)),
        dict(model='ereb', anim='ereb_spawn', t=4.3, yaw=25, pitch=6, dist=2.6, ty=17, label='3.9 с — салют рапирой', sub='титр, блик на клинке',
             fx=flash([0.3, 2.3, 0.3], 0.6, GO)),
        dict(model='ereb', anim='ereb_finale', t=0.8, smile=True, yaw=20, pitch=4, dist=1.4, ty=22, label='финал 0.3 с — улыбка',
             sub='текстура ereb_smile'),
        dict(model='ereb', anim='ereb_finale', t=2.2, smile=True, yaw=35, pitch=8, dist=1.6, ty=20, label='1.4 с — бабочка из ладони',
             sub='стеклянная бабочка T22', fx=bfly([-0.15, 1.27, 0.55], 1, [0, 0, 0], size=(0.34, 0.34), seed=2)[:1] +
             flash([-0.15, 1.27, 0.55], 0.7, GH, 0.5)),
        dict(model='ereb', anim='ereb_finale', t=3.6, smile=True, yaw=20, pitch=12, dist=2.4, ty=18, label='3.2 с — «Сон бабочки»',
             sub='вспорхнула; дальше — ролик заклинания T22', fx=flash([-0.3, 2.15, 0.2], 1.6, WH, 0.7) + bfly([-0.3, 2.6, 0.2], 10, [0.5, 0.5, 0.5], seed=6)),
        dict(model='ereb', anim='ereb_finale', t=5.15, smile=True, yaw=20, pitch=10, dist=2.6, ty=18, label='5.0 с — исчезает',
             sub='рассыпается бабочками', fx=flash([0, 1.1, 0], 2.4, GH, 0.5) + bfly([0, 1.1, 0], 60, [0.6, 1.1, 0.6], seed=11) +
             shards([0, 1.1, 0], 18, [0.6, 1.0, 0.6])),
    ]
    sh('t30_cinematics.jpg', cells, 4, (1800, 1000))
    # ---------------------------------------------------------------- эффекты боя
    cells = [
        dict(model='pyromancer', yaw=160, pitch=8, dist=2.4, ty=17, label='«Ложный союзник»: блик', sub='стекло звенит за спиной жертвы',
             fx=flash([0, 1.45, -0.9], 1.3, GH, 0.9) + shards([0, 1.45, -0.9], 4, [0.25, 0.2, 0.2])),
        dict(model='ereb', anim='ereb_vanish', t=0.65, yaw=30, pitch=8, dist=2.4, ty=17, label='исчезновение', sub='осколки и пара бабочек',
             fx=shards([0, 1.0, 0], 18, [0.5, 0.9, 0.5]) + bfly([0, 1.3, 0], 5, [0.4, 0.6, 0.4]) + flash([0, 1.0, 0], 1.2, GH, 0.4)),
        dict(model='ereb', anim='ereb_backstab', t=0.45, yaw=70, pitch=8, dist=2.6, ty=16, label='появление и удар', sub='вспышка, блик на острие',
             fx=flash([0, 1.1, 0], 1.0, WH, 0.4) + flash([0.1, 1.35, 2.0], 0.5, GO)),
        dict(model='ereb', anim='ereb_disguise', t=0.5, yaw=25, pitch=4, dist=1.8, ty=22, label='смена облика', sub='рябь зеркала у лица',
             fx=flash([0, 1.75, 0.35], 0.9, GH, 0.6) + shards([0, 1.2, 0], 8, [0.5, 0.8, 0.5])),
        dict(model='ereb', anim='ereb_phase', t=0.85, yaw=25, pitch=10, dist=2.8, ty=16, label='смена фазы', sub='стекло трескается вокруг',
             fx=flash([0, 1.2, 0], 2.2, WH, 0.5) + shards([0, 1.6, 0], 40, [1.6, 1.2, 1.6], seed=9)),
        dict(model='ereb', anim='ereb_cast_illusion', t=0.78, yaw=20, pitch=8, dist=2.4, ty=18, label='каст иллюзий', sub='блик над пальцами',
             fx=flash([-0.3, 2.15, 0.25], 0.8, GH, 0.8)),
        dict(model='ereb', anim='ereb_parry', t=0.15, yaw=40, pitch=6, dist=2.2, ty=18, label='парирование', sub='искры у гарды',
             fx=flash([0.2, 1.7, 0.6], 0.7, GO)),
        dict(model='ereb', anim='ereb_lunge', t=0.5, yaw=80, pitch=6, dist=2.8, ty=14, label='укол', sub='блик на острие — не луч',
             fx=flash([0.1, 1.35, 2.2], 0.5, GO)),
    ]
    sh('t30_fx.jpg', cells, 4, (1800, 1000))
    # ---------------------------------------------------------------- +4 заклинания
    rain = [{'tex': 'mote_glass', 'n': 3, 'at': [d, 2.5, 2.5], 'spread': [0.3, 1.5, 0.3], 'size': [0.4, 0.6], 'color': GH, 'seed': 7 + i, 'spin': 0.3}
            for i, d in enumerate((-2.5, 0.5, 3.0))]
    rings = [{'tex': 'illusion_seal', 'n': 1, 'at': [d, 0, 2.5], 'spread': [0, 0, 0], 'size': [2.4, 2.4], 'color': GH, 'ground': True, 'op': 0.5}
             for d in (-2.5, 0.5, 3.0)]
    cells = [
        dict(N, model='ereb', anim='ereb_blade_dance', t=0.12, yaw=40, pitch=8, dist=3.2, ty=15, label='«Танец клинков»', sub='шаг сквозь рябь (blink)',
             fx=flash([0, 1.1, 0], 1.6, GH, 0.5) + shards([0, 1.0, 0], 10, [0.5, 0.9, 0.5])),
        dict(N, model='ereb', anim='ereb_blade_dance', t=1.65, yaw=70, pitch=8, dist=3.4, ty=15, label='«Танец клинков»', sub='2-й укол (hit 1.65)',
             fx=flash([0.1, 1.35, 2.2], 0.5, GO)),
        dict(N, model='ereb', anim='ereb_feint', t=1.0, yaw=20, pitch=6, dist=3.0, ty=16, label='«Обманная брешь»', sub='нарочно открыт (окно 1.5 с)',
             fx=flash([0, 1.6, 0.3], 0.5, GH, 0.6)),
        dict(N, model='ereb', anim='ereb_feint_counter', t=0.12, yaw=40, pitch=6, dist=3.0, ty=16, label='контратака', sub='парирование (parry 0.1)',
             fx=flash([0.2, 1.6, 0.6], 0.8, GO) + shards([0.2, 1.5, 0.7], 8, [0.3, 0.3, 0.3])),
        dict(N, model='ereb', anim='ereb_glass_rain', t=0.9, yaw=150, pitch=14, dist=4.6, ty=20, label='«Стеклянный дождь»',
             sub='метки на земле 1.2 с, осколки сверху', fx=rings + rain),
        dict(N, model='ereb', anim='ereb_mirror_step_out', t=0.5, yaw=30, pitch=8, dist=3.0, ty=16, label='«Шаг сквозь отражение»',
             sub='уходит в рябь (gone 0.5)', fx=flash([0, 1.1, 0], 1.4, GH, 0.5) + shards([0, 1.0, 0], 12, [0.5, 0.9, 0.5])),
        dict(N, model='pyromancer', yaw=160, pitch=8, dist=2.4, ty=17, label='«Шаг сквозь отражение»', sub='блик за спиной 0.6 с',
             fx=flash([0, 1.45, -0.9], 1.3, GH, 0.9) + shards([0, 1.45, -0.9], 4, [0.25, 0.2, 0.2])),
        dict(N, model='ereb', anim='ereb_mirror_step_in', t=0.1, yaw=60, pitch=8, dist=3.0, ty=16, label='выход', sub='из ряби — в стойку',
             fx=flash([0, 1.1, 0], 1.2, WH, 0.4)),
    ]
    sh('t30_spells.jpg', cells, 4, (1800, 1000))
    # ---------------------------------------------------------------- рапира крупно
    cells = [dict(N, model='rapier', yaw=y, pitch=p, dist=d, ty=ty, x=x, ground=False, label=l, sub=sb, h=16) for y, p, d, ty, x, l, sb in
             ((0, 0, 3.6, 2.8, -2.8, 'рапира целиком', 'чёрный клинок, золотая кромка и дол'),
              (35, 20, 0.85, -1.4, 1.4, 'гарда-чашка', 'витая дужка, крестовина, стекло'),
              (-35, -12, 0.75, -3.6, 3.6, 'рукоять', 'чёрная витая, три золотых кольца, навершие'))]
    cells.append(dict(N, model='ereb', anim='ereb_guard', t=0, yaw=90, pitch=4, dist=2.6, ty=18, label='в руке', sub='стойка'))
    sh('t30_rapier.jpg', cells, 4, (1800, 560))
