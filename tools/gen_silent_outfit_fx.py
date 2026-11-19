#!/usr/bin/env python3
"""
Эффекты одежды безмолвной ведьмы (T19), стиль `silent`:
  sigils/silent_witch_feet.json  — малая печать под ногами при касте: спиральное кольцо, лента рун, свечение; медленно вращается
  fx/silent_witch_cast.json      — при касте в одежде (пункт 8): печать под ногами, кольцо искр вокруг ног (кружат),
                                   редкие огоньки поднимаются вдоль тела; следует за носителем, длится, пока идёт каст (код гасит stop)
  sigils/silent_barrier.json     — печать «Тихого барьера» (пункт 4): вертикальная, вокруг носителя, собирается по частям за мгновение,
                                   двойной обод, нимб-лоза, руны, вспышка формирования
  fx/silent_barrier.json         — срабатывание «Тихого барьера»: печать вокруг (лицом к взгляду), вторая — на земле, сфера-пузырь
                                   с ярким краем держится 3 с (неуязвимость), белая вспышка, перья-искры осыпаются; потом всё гаснет
Запуск: python3 tools/gen_silent_outfit_fx.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')


def dump(rel, doc):
    json.dump(doc, open(os.path.join(A, rel), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('wrote', rel)


def main():
    dump('sigils/silent_witch_feet.json', {
        'comment': 'Печать под ногами ведьмы при касте (T19, пункт 8). Сгенерировано tools/gen_silent_outfit_fx.py.',
        'size': 1.35, 'color': '#7FFFD0', 'orientation': 'ground', 'lifetime': -1, 'hold': -1,
        'layers': [
            {'id': 'glow', 'type': 'disc', 'texture': 'glow', 'radius': 1.1, 'heightOffset': -0.01, 'brightness': 0.45,
             'appear': {'delay': 0, 'duration': 8, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}, 'pulse': {'amp': 0.2, 'period': 40}},
            {'id': 'spiral', 'type': 'disc', 'texture': 'spiral_ring', 'radius': 0.9, 'heightOffset': 0.0,
             'appear': {'delay': 0, 'duration': 10, 'easing': 'easeOutBack', 'modes': ['grow', 'twist', 'fade'], 'twist': -120},
             'rotation': {'speed': 14, 'boost': 3.0}},
            {'id': 'runes', 'type': 'band', 'texture': 'rune_band', 'radius': 1.0, 'inner': 0.9, 'repeat': 6, 'heightOffset': 0.01,
             'appear': {'delay': 4, 'duration': 12, 'easing': 'easeInOutSine', 'modes': ['draw']}, 'rotation': {'speed': -8}},
            {'id': 'rim', 'type': 'disc', 'texture': 'thin_ring', 'radius': 1.04, 'heightOffset': 0.02,
             'appear': {'delay': 8, 'duration': 8, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}}],
        'dissolve': {'modes': ['reverse', 'collapse'], 'duration': 12, 'stagger': 2}})
    dump('fx/silent_witch_cast.json', {
        'comment': 'Каст в одежде безмолвной ведьмы (T19, пункт 8): печать под ногами, кольцо искр кружит у ног, огоньки поднимаются вдоль тела. '
                   'Следует за носителем; длится, пока идёт каст (код вызывает stop). Сгенерировано tools/gen_silent_outfit_fx.py.',
        'style': 'silent', 'duration': -1,
        'elements': [
            {'type': 'sigil', 'id': 'silent_witch_feet', 'delay': 0, 'at': 'caster', 'follow': True},
            {'type': 'sprites', 'delay': 0, 'at': 'caster+0,0.2,0', 'follow': True, 'texture': '@sparks', 'count': 2000, 'rate': 4, 'spread': 1.1,
             'speed': 0.004, 'gravity': -0.0008, 'spin': 160, 'size': [0.13, 0.03], 'life': 30, 'color': '@primary'},
            {'type': 'sprites', 'delay': 6, 'at': 'caster+0,0.3,0', 'follow': True, 'texture': '@sparks', 'count': 600, 'rate': 1, 'spread': 0.5,
             'speed': 0.02, 'gravity': -0.004, 'size': [0.1, 0.02], 'life': 34, 'color': '@core'}]})
    dump('sigils/silent_barrier.json', {
        'comment': 'Печать «Тихого барьера» (T19, пункт 4): вертикальная, вокруг носителя; собирается по частям за долю секунды. '
                   'Сгенерировано tools/gen_silent_outfit_fx.py.',
        'size': 1.6, 'color': '#7FFFD0', 'orientation': 'facing', 'lifetime': -1, 'hold': 40,
        'layers': [
            {'id': 'glow', 'type': 'disc', 'texture': 'glow', 'radius': 1.2, 'heightOffset': -0.02, 'brightness': 0.6,
             'appear': {'delay': 0, 'duration': 4, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}, 'pulse': {'amp': 0.25, 'period': 16}},
            {'id': 'nimbus', 'type': 'disc', 'texture': 'silent_nimbus', 'radius': 1.0,
             'appear': {'delay': 0, 'duration': 8, 'easing': 'easeOutBack', 'modes': ['pieces'],
                        'pieces': {'count': 10, 'order': 'scatter', 'pieceTime': 0.5, 'fly': 0.6, 'lift': 0.5, 'orbit': 50, 'tilt': 80, 'spin': 90}},
             'rotation': {'speed': 20, 'boost': 4.0}},
            {'id': 'hex', 'type': 'disc', 'texture': 'hex_ring', 'radius': 1.12, 'heightOffset': 0.01, 'color': '#CFE8FF',
             'appear': {'delay': 4, 'duration': 6, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}, 'rotation': {'speed': -12}},
            {'id': 'rim', 'type': 'disc', 'texture': 'rim', 'radius': 1.2, 'heightOffset': 0.02,
             'appear': {'delay': 6, 'duration': 4, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}}],
        'formedFlash': {'color': '#FFFFFF', 'size': 1.4, 'duration': 10, 'sparks': 40},
        'dissolve': {'modes': ['reverse', 'collapse'], 'duration': 14, 'stagger': 2}})
    dump('fx/silent_barrier.json', {
        'comment': '«Тихий барьер» сработал (T19, пункт 4): печать вокруг носителя и на земле, сфера-пузырь с ярким краем держится 3 с '
                   '(неуязвимость), белая вспышка, искры осыпаются. Следует за носителем. Сгенерировано tools/gen_silent_outfit_fx.py.',
        'style': 'silent', 'duration': 80,
        'elements': [
            {'type': 'flash', 'delay': 0, 'duration': 8, 'at': 'caster+0,1,0', 'follow': True, 'size': 4, 'anamorphic': 8, 'rays': 10, 'screen': 0.35,
             'color': '@core'},
            {'type': 'sigil', 'id': 'silent_barrier', 'delay': 0, 'at': 'caster+0,1,0', 'follow': True, 'orientation': 'facing'},
            {'type': 'sigil', 'id': 'silent_witch_feet', 'delay': 0, 'until': 64, 'at': 'caster', 'follow': True, 'sigilScale': 1.6},
            {'type': 'wave', 'shape': 'sphere', 'delay': 2, 'duration': 62, 'at': 'caster+0,1,0', 'follow': True, 'radius': 1.6, 'speed': 0, 'rim': 1.0,
             'color': '@primary', 'in': {'duration': 6, 'easing': 'easeOutBack'}, 'out': {'duration': 12, 'easing': 'easeInSine'}},
            {'type': 'sprites', 'delay': 2, 'duration': 60, 'at': 'caster+0,1.2,0', 'follow': True, 'texture': '@sparks', 'count': 240, 'rate': 4,
             'spread': 1.5, 'speed': 0.006, 'gravity': 0.003, 'size': [0.16, 0.04], 'life': 30, 'color': '@primary'},
            {'type': 'sprites', 'delay': 0, 'duration': 4, 'at': 'caster+0,1,0', 'follow': True, 'texture': '@sparks', 'count': 60, 'rate': 15,
             'spread': 0.3, 'speed': 0.22, 'gravity': 0.01, 'size': [0.2, 0.04], 'life': 18, 'color': '@core'}]})


if __name__ == '__main__':
    main()
