#!/usr/bin/env python3
"""
Кадр-лист «в игре было / стало» для ткани Эреба, Длани Лжи (накидка cape → cape_mid → cape_low, полы coat_*, призрачная рука).
Кадры берутся из симуляции теста ClothSwayTest (build/reports/cloth/cloth_sim.json: записанное движение, ванильный WalkAnimationState,
ноги Iron's): «стало» — углы ClothSway.solve, «было» — старый код (setRotX(getRotX() + …) каждый кадр, 60 FPS) в тот же момент.
Рендер — превью three.js (tools/ereb_hand_preview.template.html, та же кинематика GeckoLib, что в игре): углы и смещения кадра
подаются однокадровой анимацией (в осях анимаций: x и y поворота — со знаком минус к внутренним rotX GeckoLib).
  ./gradlew test --offline --tests '*ClothSwayTest'   →   python3 tools/cloth_fix_render.py [--three three.min.js]
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_ereb_hand_render as GH   # noqa: E402

ROOT = os.path.join(HERE, '..')
SIM = os.path.join(ROOT, 'build', 'reports', 'cloth', 'cloth_sim.json')
OUT = os.path.join(ROOT, 'docs', 'media', 'cloth_fix.jpg')
R2D = 180 / math.pi
NAMES = ['coat_front_r', 'coat_front_l', 'coat_back_r', 'coat_back_l', 'cape', 'cape_mid', 'cape_low']


def walk_bones(f):
    """Ноги и руки Iron's в кадре (оси анимаций)."""
    b = {}
    for side, key in (('right', 'r'), ('left', 'l')):
        rot, py, pz = f[key]
        b[side + '_leg'] = {'rotation': [-rot * R2D, 0, 0], 'position': [0, py, pz]}
    # руки Iron's: cos(φ + π)·2·amount·0.5 (правая), cos(φ)·… (левая) — фаза из поворота ног (правая нога = cos(φ)·1.05·amount)
    a = f['amount']
    c = f['r'][0] / (1.05 * a) if a > 1e-3 else 0
    b['right_arm'] = {'rotation': [c * a * R2D, 0, 0]}
    b['left_arm'] = {'rotation': [-c * a * R2D, 0, 0]}
    return b


def anim_new(f):
    b = walk_bones(f)
    for n, d in zip(NAMES, f['d']):
        b[n] = {'rotation': [-d * R2D, 0, 0]}
    return {'loop': False, 'animation_length': 0.05, 'bones': b}


REST = {'coat_front': 3, 'coat_back': -5, 'cape': -5}   # внутренние rotX покоя (градусы): из .geo (x −3 / 5 / 5)


def anim_old(o, f):
    b = walk_bones(f)
    fr, br = o['front'] * R2D - REST['coat_front'], o['back'] * R2D - REST['coat_back']
    for n in ('coat_front_r', 'coat_front_l'):
        b[n] = {'rotation': [-fr, 0, 0]}
    for n in ('coat_back_r', 'coat_back_l'):
        b[n] = {'rotation': [-br, 0, 0]}
    c0, c1, c2 = o['cape']
    b['cape'] = {'rotation': [-(c0 * R2D - REST['cape']), 0, 0]}
    b['cape_mid'] = {'rotation': [-c1 * R2D, 0, 0]}
    b['cape_low'] = {'rotation': [-c2 * R2D, 0, 0]}
    b['ghost_hand'] = {'position': [0, o['hand'], 0]}
    b['ghost_trail'] = {'position': [0, o['hand'], 0]}
    return {'loop': False, 'animation_length': 0.05, 'bones': b}


def main():
    three = sys.argv[sys.argv.index('--three') + 1] if '--three' in sys.argv else None
    sim = json.load(open(SIM, encoding='utf-8'))
    new = {round(f['t']): f for f in sim['fps']['60']}
    old = {o['t']: o for o in sim['old']}
    old144 = {o['t']: o for o in sim['old144']}
    moments = [(55, 'бег'), (95, 'разворот на месте'), (160, 'отбрасывание'), (180, 'после телепорта')]
    extra = {}
    cells = []
    for t, what in moments:
        f = new[t]
        ka, kb = 'old_%d' % t, 'new_%d' % t
        extra[ka], extra[kb] = anim_old(old[t], f), anim_new(f)
        o = old[t]
        sub_o = 'накидка %+.0f°, пола %+.0f° (накоплено)' % (-(o['cape'][0] * R2D - REST['cape']), -(o['front'] * R2D - REST['coat_front']))
        d = f['d']
        sub_n = 'накидка %.0f°/%.0f°/%.0f° назад, полы %.0f° / %.0f°' % (-d[4] * R2D, -d[5] * R2D, -d[6] * R2D, max(d[0], d[1]) * R2D,
                                                                        min(d[2], d[3]) * R2D)
        cells.append({'model': 'ereb_hand', 'anim': ka, 't': 0, 'yaw': 120, 'pitch': 6, 'variant': 'base',
                      'label': 'БЫЛО · ' + what, 'sub': sub_o})
        cells.append({'model': 'ereb_hand', 'anim': kb, 't': 0, 'yaw': 120, 'pitch': 6, 'variant': 'base',
                      'label': 'СТАЛО · ' + what, 'sub': sub_n})
    # призрачная рука: накопленный подъём при 140 FPS против покачивания ±0.6 px
    th = max(old144, key=lambda k: old144[k]['hand'])
    f = new[th]
    extra['old_hand'] = anim_old(old144[th], f)
    extra['new_hand'] = anim_new(f)
    extra['new_hand']['bones']['ghost_hand'] = {'position': [0, 0.6 * math.sin(th * 0.08), 0]}
    hb = old144[th]['hand'] / 16
    cells.append({'model': 'ereb_hand', 'anim': 'old_hand', 't': 0, 'yaw': 25, 'pitch': 4, 'dist': 2.1, 'h': 34 + old144[th]['hand'],
                  'ty': (34 + old144[th]['hand']) * 0.55, 'variant': 'base', 'label': 'БЫЛО · призрачная рука (140 FPS)',
                  'sub': 'накопленный сдвиг +%.1f бл. над плечом' % hb})
    cells.append({'model': 'ereb_hand', 'anim': 'new_hand', 't': 0, 'yaw': 25, 'pitch': 4, 'dist': 2.1, 'h': 34 + old144[th]['hand'],
                  'ty': (34 + old144[th]['hand']) * 0.55, 'variant': 'base', 'label': 'СТАЛО · призрачная рука',
                  'sub': 'над правым плечом, качается ±0.6 px'})
    # крупно сбоку: самый широкий шаг (полы на бедре, шарнир сдвинут бедром) и первый Эреб в тот же момент
    tw = max(new, key=lambda k: abs(new[k]['d'][7]) + abs(new[k]['d'][8]))
    extra['new_wide'] = anim_new(new[tw])
    d = new[tw]['d']
    cells.append({'model': 'ereb_hand', 'anim': 'new_wide', 't': 0, 'yaw': 90, 'pitch': 2, 'dist': 1.7, 'ty': 12, 'variant': 'base',
                  'item': False, 'label': 'СТАЛО · широкий шаг, сбоку',
                  'sub': 'полы %.0f° / %.0f°, верх полы сдвинут бедром на %.1f px' % (max(d[0], d[1]) * R2D, min(d[2], d[3]) * R2D,
                                                                                      max(abs(d[7]), abs(d[8])))})
    cells.append({'model': 'ereb', 'anim': 'new_wide', 't': 0, 'yaw': 115, 'pitch': 4, 'item': False,
                  'label': 'СТАЛО · первый Эреб (T30), тот же шаг', 'sub': 'те же полы и тот же модуль ClothSway'})
    orig = GH.anims
    GH.anims = lambda: dict(orig(), **extra)
    GH.sheet(OUT, {'cols': 4, 'cells': cells}, three, size=(1600, 1240))


if __name__ == '__main__':
    main()
