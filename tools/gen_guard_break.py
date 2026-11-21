#!/usr/bin/env python3
"""
T32 п. 4 «Сломать блок» — fx, общий звук и lang для шести боссов (анимации — генераторы боссов, tools/guard_break_*.py).
  python3 tools/gen_guard_break.py
Запускать ПОСЛЕ генераторов боссов: точки вспышки берутся из готовых анимаций (FK как у проверки).

fx <boss>_guard_break (assets/pohsmp_core/fx): код (BossGuardBreak) играет его на тике 0 анимации, caster — босс, target — цель:
  тики 2–14 (warn → hit) — вспышка на оружии/руке: цепочка коротких вспышек в точках, где в эти тики оказывается оружие (смещения в осях
            взгляда босса, посчитаны по анимации с масштабом рендера), нарастает к удару; у Ирины — ещё нити вокруг защиты цели;
  тик 14   — удар (событие `hit`): треск блока у цели — вспышка с кольцом, лопается «пузырь» защиты, осколки/искры стиля босса.
Звук (sounds.json, общий у всех): pohsmp_core:boss.guard_break — «треск» (код играет его на warn, за 12 тиков до удара); собран
из ванильных событий (ломается щит, выбитая дверь, удар по наковальне), 3 вариации одного характера. Lang — у программиста
(ui.pohsmp_core.boss.guard_break «Сломать блок» / «Guard Break», subtitles.pohsmp_core.boss.guard_break) — здесь только проверяется.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
WARN_T, HIT_T = 0.10, 0.70
WARN_TICKS = 12
T0 = 2                       # warn — тик 2 анимации (fx стартует на тике 0)

# босс: (анимация, масштаб рендера, стиль fx, текстура осколков, цвет вспышки, что светится)
BOSSES = {
    'cult_leader': ('cult_leader_guard_break', 1.75, 'cult_leader', 'mote_flame', '@secondary', 'лезвие косы'),
    'irina': ('irina_guard_break', 1.0, 'irina', 'mote_thread', '@primary', 'левая ладонь (нити)'),
    'aris': ('animation.aris.guard_break', 1.0, 'aris', 'spark_soft', '@secondary', 'голова молота'),
    'martin': ('martin_guard_break', 2.0, 'martin', 'spark_soft', '@primary', 'навершие меча'),
    'ereb': ('ereb_guard_break', 1.0, 'ereb', 'mote_glass', '@secondary', 'остриё рапиры'),
    'ereb_hand': ('ereb_hand_guard_break', 1.0, 'ereb_hand', 'ereb_hand_shard_glass', '@secondary', 'призрачная ладонь'),
}


def glow_points(boss):
    """Точка свечения (пиксели модели, R-мир: x вправо, −z вперёд) в тики 0, 2, … 12 после warn."""
    ts = [WARN_T + k / 20.0 for k in range(0, WARN_TICKS + 1, 2)]
    if boss == 'martin':
        import guard_break_check as GC
        sig, _, _ = GC.martin_sig(BOSSES[boss][0])
        return [np.asarray(sig(t)['tip']) * 12.0 for t in ts]
    import guard_break_lib as GL
    M = GL.model(boss)
    an = M.anims[BOSSES[boss][0]]
    out = []
    for t in ts:
        W = M.world(an, t)
        if boss == 'irina':
            p = GL.ap(W['bipedHandLeft'], (0, 0, 0))
        elif boss == 'ereb_hand':
            p = GL.ap(W['ghost_palm'], (0, 5.0, 0))
        else:
            p = M.strike_pts(W)[1]
        out.append(np.asarray(p, float))
    return out


def off(p, scale):
    """Пиксели модели → смещение fx в осях взгляда (x — вправо, y — вверх, z — вперёд), блоки."""
    k = scale / 16.0
    return 'caster+%.2f,%.2f,%.2f' % (p[0] * k, p[1] * k, -p[2] * k)


def fx(boss):
    name, scale, style, shard, col, _ = BOSSES[boss]
    pts = glow_points(boss)
    el = []
    n = len(pts)
    for i, p in enumerate(pts):                         # вспышка ведёт оружие: каждые 2 тика, всё ярче к удару
        k = i / max(1, n - 1)
        el.append({'type': 'flash', 'delay': T0 + 2 * i, 'at': off(p, scale), 'duration': 4 if i < n - 1 else 3,
                   'size': round(0.35 + 0.55 * k, 2), 'rays': 4 if k < 0.5 else 6, 'color': col, 'brightness': round(0.8 + 0.6 * k, 2),
                   'comment': 'вспышка на оружии/руке, тик %d' % (2 * i)})
    el.append({'type': 'flash', 'delay': T0, 'at': off(pts[0], scale), 'duration': 6, 'size': 0.9, 'anamorphic': 1.6, 'rays': 6,
               'color': '@core', 'comment': 'блик-предупреждение (0.6 с до удара)'})
    el.append({'type': 'sprites', 'delay': T0, 'at': off(pts[0], scale), 'duration': WARN_TICKS, 'texture': 'spark_soft', 'count': 14,
               'rate': 2, 'spread': 0.18, 'speed': 0.04, 'gravity': -0.01, 'size': [0.14, 0.02], 'life': 8, 'color': col, 'glow': 0.8})
    if boss == 'irina':                                  # нити обвивают защиту цели и рвутся на рывке (тик 8–9)
        el.append({'type': 'vortex', 'delay': T0 + 3, 'at': 'target+0,1.05,0', 'duration': 7, 'radius': 0.75, 'height': 1.0, 'arms': 3,
                   'speed': 26, 'pull': 0.4, 'funnel': 0.8, 'turns': 1.6, 'width': 0.05, 'texture': 'mote_thread', 'color': '@primary',
                   'comment': 'нити обвивают защиту'})
        el.append({'type': 'sprites', 'delay': T0 + 8, 'at': 'target+0,1.2,0', 'duration': 2, 'texture': 'mote_thread', 'count': 16, 'rate': 8,
                   'spread': 0.5, 'speed': 0.3, 'gravity': 0.02, 'size': [0.3, 0.05], 'life': 12, 'color': '@primary',
                   'comment': 'рывок: нити раздёргивают защиту'})
    # удар (тик 14): треск блока у цели
    el += [
        {'type': 'flash', 'delay': T0 + WARN_TICKS, 'at': 'target+0,1.2,0', 'duration': 6, 'size': 1.8, 'rays': 8, 'anamorphic': 2.2, 'ring': True,
         'screen': 0.12, 'color': '@core', 'comment': 'треск блока: удар'},
        {'type': 'wave', 'delay': T0 + WARN_TICKS, 'at': 'target+0,1.0,0', 'duration': 7, 'shape': 'sphere', 'radius': 1.05, 'rim': 1.4,
         'color': col, 'out': {'duration': 5, 'easing': 'easeOutCubic'}, 'comment': 'защита лопается пузырём'},
        {'type': 'sprites', 'delay': T0 + WARN_TICKS, 'at': 'target+0,1.2,0', 'duration': 2, 'texture': shard, 'count': 22, 'rate': 11,
         'spread': 0.45, 'speed': 0.32, 'gravity': 0.045, 'spin': 30, 'tumble': 1, 'size': [0.26, 0.04], 'life': 16, 'color': col, 'glow': 0.5,
         'comment': 'осколки защиты'},
        {'type': 'sprites', 'delay': T0 + WARN_TICKS, 'at': 'target+0,1.2,0', 'duration': 2, 'texture': 'spark_soft', 'count': 26 if boss == 'aris' else 14,
         'rate': 13, 'spread': 0.3, 'speed': 0.45 if boss == 'aris' else 0.3, 'gravity': 0.05, 'size': [0.14, 0.02], 'life': 12,
         'color': '@primary' if boss != 'aris' else '#FFD27A', 'glow': 0.9, 'comment': 'искры'},
        {'type': 'decal', 'delay': T0 + WARN_TICKS, 'at': 'target', 'duration': 40, 'shape': 'crack', 'length': 2.2, 'width': 0.35, 'grow': 4,
         'branches': 6, 'yaw': 90, 'color': col, 'fadeOut': 26, 'lift': 0.02, 'comment': 'трещина под ногами цели'},
    ]
    return {'comment': 'T32 «Сломать блок» (%s): старт на тике 0 анимации %s, caster — босс, target — цель в блоке; '
                       'тики 2–14 (warn → hit) — вспышка на оружии (%s), тик 14 (событие hit) — треск блока у цели. '
                       'Сгенерировано tools/gen_guard_break.py.' % (boss, name, BOSSES[boss][5]),
            'style': style, 'duration': T0 + WARN_TICKS + 30, 'elements': el}


SOUNDS = {
    'boss.guard_break': {'subtitle': 'subtitles.pohsmp_core.boss.guard_break', 'sounds': [
        {'name': 'minecraft:item.shield.break', 'type': 'event', 'pitch': 0.65, 'volume': 1.3},
        {'name': 'minecraft:entity.zombie.break_wooden_door', 'type': 'event', 'pitch': 0.8, 'volume': 1.1},
        {'name': 'minecraft:item.shield.break', 'type': 'event', 'pitch': 0.55, 'volume': 1.3}]},
}
LANG_NEED = ('ui.pohsmp_core.boss.guard_break', 'subtitles.pohsmp_core.boss.guard_break')


def write_sounds():
    """Событие одной строкой: заменяет строку с этим ключом на месте (или дописывает в конец); остальной файл — как есть."""
    p = os.path.join(A, 'sounds.json')
    txt = open(p, encoding='utf-8').read()
    for k, v in SOUNDS.items():
        line = '  "%s": %s' % (k, json.dumps(v, ensure_ascii=False))
        lines = txt.split('\n')
        hit = [n for n, l in enumerate(lines) if l.lstrip().startswith('"%s"' % k)]
        if hit:
            n = hit[0]
            assert json.loads('{' + lines[n].strip().rstrip(',') + '}'), 'событие %s не в одну строку' % k
            lines[n] = line + (',' if lines[n].rstrip().endswith(',') else '')
            txt = '\n'.join(lines)
        else:
            body = txt.rstrip()[:-1].rstrip()
            txt = body + ',\n' + line + '\n}\n'
    json.loads(txt)
    open(p, 'w', encoding='utf-8', newline='\n').write(txt)


def check_lang():
    for lg in ('ru_ru', 'en_us'):
        d = json.load(open(os.path.join(A, 'lang', lg + '.json'), encoding='utf-8'))
        for k in LANG_NEED:
            print('  lang %s %s: %s' % (lg, k, d.get(k, 'НЕТ КЛЮЧА')))


def main(args):
    only = [a for a in args if a in BOSSES] or list(BOSSES)
    for b in only:
        an = BOSSES[b][0]
        try:
            d = fx(b)
        except KeyError:
            print('%s: нет анимации %s — пропуск' % (b, an))
            continue
        p = os.path.join(A, 'fx', b + '_guard_break.json')
        open(p, 'w', encoding='utf-8', newline='\n').write(json.dumps(d, ensure_ascii=False, indent=1) + '\n')
        print('fx', os.path.relpath(p, os.path.join(HERE, '..')), len(d['elements']), 'элементов')
    write_sounds()
    print('sounds: %s' % ', '.join(SOUNDS))
    check_lang()


if __name__ == '__main__':
    main(sys.argv[1:])
