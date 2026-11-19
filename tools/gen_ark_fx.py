"""Ковчег (Божественная): купол r=32 в новом виде, как купол «Закрытия пространства» (владелец, 19.11.2026).

Пишет: fx/ark.json (купол на минуту), fx/ark_cast.json (5 с каста), fx/meshes/ark_meridian.json,
sigils/ark_lat.json, ark_belt.json, ark_emblem.json, ark_cast_seal.json. Солнце в зените — старая sigils/ark_sky.json,
круг на земле — ark_ground.json. Запуск: python tools/gen_ark_fx.py
"""
import json, math, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
R, LIFE, CAST = 32.0, 1200, 100
GOLD, CREAM, WHITE = '#FFD36B', '#FFF4D6', '#FFFFFF'


def dump(rel, obj):
    with open(os.path.join(ROOT, rel), 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    print('wrote', rel)


def ap(delay, dur, modes, easing='easeOutCubic', **kw):
    a = {'delay': delay, 'duration': dur, 'easing': easing, 'modes': modes}
    a.update(kw)
    return a


DISSOLVE = {'modes': ['reverse', 'collapse'], 'duration': 30, 'stagger': 2}

# ---------------------------------------------------------------- the dome's frame
dump('fx/meshes/ark_meridian.json', {
    'comment': 'Ковчег: меридиан купола — вертикальное кольцо радиуса 32 (каркас дают шесть таких с разным yaw). Сгенерировано tools/gen_ark_fx.py.',
    'style': 'divine', 'center': 0, 'formedAt': 40, 'collapse': {'duration': 30, 'easing': 'easeInCubic'},
    'parts': [{'type': 'ring', 'radius': R, 'thickness': 0.09, 'color': '@primary', 'brightness': 0.6,
               'appear': {'delay': 0, 'duration': 40, 'easing': 'easeOutCubic'}}]})

dump('sigils/ark_lat.json', {
    'comment': 'Ковчег: широта купола (радиус задаёт scale элемента): золотое кольцо и бегущий пунктир. Сгенерировано tools/gen_ark_fx.py.',
    'size': 1.0, 'color': GOLD, 'orientation': 'ground', 'lifetime': -1, 'hold': -1,
    'layers': [
        {'id': 'ring', 'type': 'band', 'texture': 'thin_ring', 'radius': 1.0, 'heightOffset': 0.0, 'brightness': 0.85, 'inner': 0.993, 'repeat': 1,
         'appear': ap(0, 30, ['draw'])},
        {'id': 'dash', 'type': 'band', 'texture': 'orbit_dash', 'radius': 0.992, 'heightOffset': 0.0, 'color': CREAM, 'brightness': 0.55,
         'inner': 0.975, 'repeat': 16, 'appear': ap(10, 30, ['fade']), 'rotation': {'speed': 0.8}}],
    'dissolve': DISSOLVE})

dump('sigils/ark_belt.json', {
    'comment': 'Ковчег: пояс рун по краю купола на земле (scale = радиус купола). Сгенерировано tools/gen_ark_fx.py.',
    'size': 1.0, 'color': GOLD, 'orientation': 'ground', 'lifetime': -1, 'hold': -1,
    'layers': [
        {'id': 'rim', 'type': 'band', 'texture': 'thin_ring', 'radius': 1.0, 'heightOffset': 0.0, 'inner': 0.995, 'repeat': 1, 'brightness': 0.9,
         'appear': ap(0, 30, ['draw'], startAngle=90)},
        {'id': 'runes', 'type': 'band', 'texture': 'rune_band', 'radius': 0.99, 'heightOffset': 0.01, 'color': CREAM, 'inner': 0.955, 'repeat': 48,
         'appear': ap(10, 40, ['draw'], easing='easeInOutSine', startAngle=90, direction=1), 'rotation': {'speed': -0.5}},
        {'id': 'rim2', 'type': 'band', 'texture': 'thin_ring', 'radius': 0.95, 'heightOffset': 0.0, 'inner': 0.946, 'repeat': 1, 'brightness': 0.6,
         'appear': ap(20, 30, ['draw'], startAngle=270)}],
    'dissolve': DISSOLVE})

dump('sigils/ark_emblem.json', {
    'comment': 'Ковчег: святая печать, лежит на оболочке купола (касательно сфере, неподвижно): солнце, печать святости, обод. Сгенерировано tools/gen_ark_fx.py.',
    'size': 4.5, 'color': GOLD, 'orientation': 'outward', 'lifetime': -1, 'hold': -1,
    'layers': [
        {'id': 'glow', 'type': 'disc', 'texture': 'glow', 'radius': 0.85, 'heightOffset': -0.01, 'color': '#8A6420', 'brightness': 0.5,
         'appear': ap(0, 20, ['fade']), 'pulse': {'amp': 0.2, 'period': 60}},
        {'id': 'holy', 'type': 'disc', 'texture': 'holy_seal', 'radius': 1.0, 'heightOffset': 0.0, 'color': CREAM,
         'appear': ap(0, 30, ['draw'], startAngle=90), 'rotation': {'speed': 2}},
        {'id': 'sun', 'type': 'disc', 'texture': 'divine_sun', 'radius': 0.45, 'heightOffset': 0.01,
         'appear': ap(10, 24, ['grow', 'twist']), 'rotation': {'speed': -4}},
        {'id': 'rim', 'type': 'band', 'texture': 'thin_ring', 'radius': 1.05, 'heightOffset': 0.02, 'inner': 0.98, 'repeat': 1,
         'appear': ap(20, 20, ['draw'])}],
    'formedFlash': {'color': WHITE, 'size': 1.1, 'duration': 12, 'sparks': 16},
    'dissolve': DISSOLVE})

dump('sigils/ark_cast_seal.json', {
    'comment': 'Ковчег, каст (5 с): печать под магом прорисовывается слоями и медленно растёт; на касте — солнце, нимб, кольцо рун. Сгенерировано tools/gen_ark_fx.py.',
    'size': 3.2, 'color': GOLD, 'orientation': 'ground', 'lifetime': -1, 'hold': -1,
    'layers': [
        {'id': 'glow', 'type': 'disc', 'texture': 'glow', 'radius': 0.9, 'color': '#8A6420', 'brightness': 0.9,
         'appear': ap(0, 20, ['grow', 'fade']), 'pulse': {'amp': 0.25, 'period': 30}},
        {'id': 'rim', 'type': 'band', 'texture': 'thin_ring', 'radius': 1.0, 'heightOffset': 0.0, 'inner': 0.97, 'repeat': 1,
         'appear': ap(0, 20, ['draw'], startAngle=90)},
        {'id': 'runes', 'type': 'band', 'texture': 'rune_band', 'radius': 0.96, 'heightOffset': 0.01, 'color': CREAM, 'inner': 0.8, 'repeat': 10,
         'appear': ap(10, 30, ['draw'], easing='easeInOutSine', startAngle=90, direction=1), 'rotation': {'speed': 6}},
        {'id': 'holy', 'type': 'disc', 'texture': 'holy_seal', 'radius': 0.76, 'heightOffset': 0.02,
         'appear': ap(30, 30, ['draw'], startAngle=90), 'rotation': {'speed': -4}},
        {'id': 'sun', 'type': 'disc', 'texture': 'divine_sun', 'radius': 0.34, 'heightOffset': 0.03, 'color': WHITE,
         'appear': ap(55, 25, ['grow', 'twist']), 'rotation': {'speed': 10}}],
    'formedFlash': {'color': WHITE, 'size': 1.2, 'duration': 12, 'sparks': 30},
    'dissolve': {'modes': ['reverse', 'collapse'], 'duration': 12, 'stagger': 2}})

dump('fx/ark_cast.json', {
    'comment': 'Ковчег, каст 5 с (ArkSpell.CAST): печать под магом, золотые огни поднимаются вокруг, тонкий столб вверх. ArkSpell останавливает его на касте или отмене. Сгенерировано tools/gen_ark_fx.py.',
    'style': 'divine', 'duration': -1,
    'elements': [
        {'type': 'sigil', 'id': 'ark_cast_seal', 'delay': 0, 'at': 'caster+0,0.05,0', 'follow': True},
        {'type': 'sprites', 'delay': 0, 'at': 'caster+0,0.1,0', 'follow': True, 'texture': 'spark_soft', 'count': 2000, 'rate': 1.5, 'area': 2.6,
         'speed': 0.02, 'gravity': -0.006, 'size': [0.16, 0.04], 'life': 40, 'color': '@primary'},
        {'type': 'sprites', 'delay': 20, 'at': 'caster+0,0.1,0', 'follow': True, 'texture': 'feather', 'count': 2000, 'rate': 0.25, 'area': 2.2,
         'speed': 0.01, 'gravity': -0.004, 'sway': 1.0, 'tumble': 0.6, 'size': [0.3, 0.2], 'life': 50, 'color': '@secondary'},
        {'type': 'column', 'delay': 30, 'at': 'caster', 'duration': 9999, 'radius': 0.35, 'height': 12, 'rings': 2, 'ringSpeed': 3, 'fill': 0.6,
         'color': '@primary', 'in': {'duration': 40, 'easing': 'easeInSine'}}]})

# ---------------------------------------------------------------- the dome
E = [
    {'type': 'wave', 'delay': 0, 'at': 'caster+0,0.5,0', 'duration': 40, 'shape': 'sphere', 'radius': R, 'rim': 1.2, 'color': '@primary'},
    {'type': 'wave', 'delay': 0, 'at': 'caster', 'duration': 30, 'shape': 'ring', 'radius': R, 'color': '@primary'},
    {'type': 'flash', 'delay': 0, 'at': 'caster+0,1.5,0', 'duration': 16, 'size': 10, 'rays': 12, 'anamorphic': 24, 'screen': 0.45, 'color': CREAM},
]
for k in range(6):
    E.append({'type': 'mesh', 'delay': 0, 'at': 'caster', 'model': 'ark_meridian', 'yaw': k * 30, 'until': LIFE - 10})
E.append({'type': 'sigil', 'delay': 6, 'at': 'caster+0,0.3,0', 'id': 'ark_belt', 'scale': R, 'until': LIFE - 10})
for k, deg in enumerate((20, 40, 60, 75)):
    a = math.radians(deg)
    E.append({'type': 'sigil', 'delay': 14 + 6 * k, 'at': 'caster+0,%s,0' % round(R * math.sin(a), 2), 'id': 'ark_lat',
              'scale': round(R * math.cos(a), 2), 'until': LIFE - 10})
EL = math.radians(18)
for k in range(6):
    a = math.radians(60 * k)
    x, z = R * math.cos(EL) * math.cos(a), R * math.cos(EL) * math.sin(a)
    E.append({'type': 'sigil', 'delay': 24 + 4 * k, 'at': 'caster+%s,%s,%s' % (round(x, 2), round(R * math.sin(EL), 2), round(z, 2)),
              'id': 'ark_emblem', 'until': LIFE - 10})
E += [
    {'type': 'sigil', 'delay': 10, 'at': 'caster+0,%s,0' % R, 'id': 'ark_sky', 'scale': 0.55, 'until': LIFE - 10,
     'comment': 'солнце в зените, лицом вниз'},
    {'type': 'sigil', 'delay': 0, 'at': 'caster+0,0.06,0', 'id': 'ark_ground', 'until': LIFE - 10},
    {'type': 'column', 'delay': 10, 'at': 'caster', 'duration': LIFE - 20, 'radius': 0.6, 'height': R, 'rings': 3, 'ringSpeed': 4, 'fill': 1,
     'color': '@primary', 'in': {'duration': 20, 'easing': 'easeOutCubic'}, 'out': {'duration': 20, 'easing': 'easeOutCubic'}},
    {'type': 'curtain', 'delay': 10, 'at': 'caster', 'duration': LIFE - 20, 'radius': R, 'count': 48, 'height': 18, 'grow': 30, 'width': [0.05, 0.12],
     'brightness': [0.12, 0.3], 'flicker': 0.3, 'texture': 'beam_fade', 'color': '@primary', 'out': {'duration': 20, 'easing': 'easeOutCubic'}},
    {'type': 'sprites', 'delay': 10, 'at': 'caster+0,22,0', 'duration': LIFE - 20, 'texture': 'feather', 'count': LIFE - 20, 'rate': 1, 'area': 28,
     'speed': 0.003, 'gravity': 0.0015, 'sway': 1.2, 'tumble': 0.6, 'size': [0.45, 0.3], 'life': 180, 'color': '@secondary'},
]
dump('fx/ark.json', {
    'comment': 'Ковчег: купол света r=32 на минуту в новом виде (как купол Закрытия): пузырь, каркас из шести меридианов, четыре широты, '
               'пояс рун по краю, шесть святых печатей на оболочке, солнце в зените, круг на земле, столб и тонкая завеса, падают перья. '
               'Сгенерировано tools/gen_ark_fx.py.',
    'style': 'divine', 'duration': LIFE, 'elements': E})
