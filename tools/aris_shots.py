#!/usr/bin/env python3
"""T28 «Арис» — проверочные и обзорные кадры docs/media/t28_*.jpg (Playwright + three.js; см. aris_render.py)."""
import os

from PIL import Image

import aris_render as R

HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.join(HERE, '..', 'docs', 'media')
A_ = 'animation.aris.'


def cell(anim=None, t=0, yaw=25, label='', **kw):
    d = {'model': 'aris', 'anim': A_ + anim if anim else None, 't': t, 'yaw': yaw, 'label': label}
    if not anim:
        d['hide'] = ['hammer_ground']
    d.update(kw)
    return d


def run(G, args):
    three = args[args.index('--three') + 1] if '--three' in args else None
    M = lambda n: os.path.join(MEDIA, n)
    # модель: ракурсы и варианты текстур
    R.sheet(M('t28_model.jpg'), {'cols': 4, 'cells': [
        cell('idle', 0, 25, 'Арис, Мифический Кузнец', sub='покой: голова молота на земле'),
        cell(None, 0, 160, 'сзади', sub='коса, воротник, юбка', hide=['hammer', 'hammer_ground']),
        cell(None, 0, 80, 'сбоку', hide=['hammer', 'hammer_ground']),
        cell(None, 0, 15, 'крупно', sub='×4: гравировка, потёртости, заклёпки', dist=0.75, ty=27, hide=['hammer', 'hammer_ground']),
        cell('idle', 0, 25, 'в темноте', sub='glowmask: рога, кайма', bg='#050608', dim=0.22, hide=['hammer_ground']),
        cell('idle', 0, 25, 'рога гаснут', sub='aris_dim (и мирный NPC)', variant='dim', bg='#050608', dim=0.35, hide=['hammer_ground']),
        cell('idle', 0, 25, 'рога погасли', sub='aris_spent (сдача)', variant='spent', hide=['hammer_ground']),
        cell('phase3', 2.5, 25, 'Мифический сплав', sub='aris_mythic (фаза 3)', variant='mythic', bg='#0a0706', dim=0.5),
    ]}, three)
    # эталон: рядом с Главой Культа, один масштаб и свет
    R.sheet(M('t28_vs_cult_leader.jpg'), {'cols': 2, 'cells': [
        {'model': 'aris', 'hide': ['hammer', 'hammer_ground'], 'yaw': 20, 'pitch': 4, 'h': 46, 'tx': 9, 'label': 'Арис рядом с Главой Культа (эталон)',
         'sub': 'один масштаб и свет', 'also': [{'model': 'cult_leader', 'x': 18}], 'dist': 2.4, 'ty': 22},
        {'model': 'aris', 'hide': ['hammer', 'hammer_ground'], 'yaw': 160, 'pitch': 4, 'h': 46, 'tx': 9, 'label': 'сзади',
         'also': [{'model': 'cult_leader', 'x': 18}], 'dist': 2.4, 'ty': 22},
    ]}, three, size=(1600, 800))
    # анимации
    R.sheet(M('t28_anims.jpg'), {'cols': 5, 'cells': [
        cell('walk', 0.3, 50, 'ходьба', sub='молот на плече'), cell('slam', 0.42, 70, 'удар по земле', sub='замах 0.42'),
        cell('slam', 0.75, 30, 'удар по земле', sub='impact 0.75'), cell('swing', 0.45, 25, 'размах', sub='замах 0.45'),
        cell('swing', 0.62, 25, 'размах', sub='hit 0.62'), cell('cast', 0.9, 30, 'каст', sub='cast 0.8'),
        cell('forge', 1.0, 60, '«Горн»', sub='strike 1.0'), cell('forge', 3.4, 30, '«Горн»', sub='ignite 3.3'),
        cell('last_blow', 3.3, 60, '«Последний удар»', sub='заряд'), cell('last_blow', 4.0, 60, '«Последний удар»', sub='blow 4.0'),
    ]}, three)
    R.sheet(M('t28_phases_spawn.jpg'), {'cols': 5, 'cells': [
        cell('phase2', 0.5, 40, 'фаза 2', sub='оборот'), cell('phase2', 1.0, 40, 'фаза 2', sub='roar 1.0'),
        cell('phase3', 1.2, 25, 'фаза 3', sub='сжимается'), cell('phase3', 1.8, 25, 'фаза 3', sub='ignite 1.6', variant='mythic'),
        cell('spawn', 3.5, 30, 'появление', sub='из расплава 3.5', variant='spent'),
        cell('spawn', 4.6, 30, 'появление', sub='на колене 4.5', variant='dim'),
        cell('spawn', 5.6, 30, 'появление', sub='встаёт', variant='dim'), cell('spawn', 6.7, 60, 'появление', sub='замах 6.7'),
        cell('spawn', 7.0, 40, 'появление', sub='impact 7.0'), cell('spawn', 9.0, 25, 'появление', sub='стойка 9.0'),
    ]}, three)
    R.sheet(M('t28_surrender.jpg'), {'cols': 4, 'cells': [
        cell('surrender', 0.4, 35, 'сдача', sub='0.4 пошатнулась'), cell('surrender', 1.6, 35, 'сдача', sub='1.2 на колено, молот в землю'),
        cell('surrender', 2.3, 35, 'сдача', sub='2.0 рога гаснут', variant='dim'), cell('surrender', 3.0, 35, 'сдача', sub='2.6–3.2 молот падает', variant='spent'),
        cell('surrender', 4.6, 35, 'сдача', sub='3.6 «Чёрт! Я сдаюсь…»', variant='spent'), cell('surrender', 4.6, 120, 'сдача', sub='сбоку', variant='spent'),
        cell('npc_stand', 0.5, 30, 'мирный NPC', sub='стоит у молота', variant='dim'), cell('npc_sit', 0.5, 35, 'мирный NPC', sub='сидит на молоте', variant='dim'),
    ]}, three)
    R.sheet(M('t28_hammer.jpg'), {'cols': 3, 'cells': [
        {'item': 'aris_hammer', 'yaw': 0, 'pitch': 0, 'h': 34, 'ty': 13, 'label': 'Молот Арис', 'sub': 'спереди (models/item/aris_hammer.json)'},
        {'item': 'aris_hammer', 'yaw': 35, 'pitch': 12, 'h': 34, 'ty': 13, 'label': '3/4'},
        {'item': 'aris_hammer', 'yaw': 90, 'pitch': 0, 'h': 34, 'ty': 13, 'label': 'сбоку'},
    ]}, three, size=(1500, 700))
    R.sheet(M('t28_meshes.jpg'), {'cols': 4, 'cells': [
        {'meshes': [{'id': 'aris_anvil'}], 'h': 60, 'ty': 14, 'yaw': 30, 'pitch': 15, 'label': 'наковальня-препятствие', 'sub': 'fx/meshes/aris_anvil'},
        {'meshes': [{'id': 'aris_blade_sword', 'at': [0, 1, 0]}], 'h': 34, 'ty': 16, 'yaw': 70, 'pitch': 10, 'label': 'клинок: меч'},
        {'meshes': [{'id': 'aris_blade_glaive', 'at': [0, 1, 0]}], 'h': 34, 'ty': 16, 'yaw': 70, 'pitch': 10, 'label': 'клинок: глефа'},
        {'meshes': [{'id': 'aris_giant_hammer'}], 'model': 'aris', 'hide': ['hammer_ground'], 'h': 240, 'ty': 110, 'yaw': 25, 'pitch': 8,
         'label': 'исполинский молот', 'sub': '«Последний удар», рядом Арис', 'bg': '#05080a', 'dim': 0.5},
    ]}, three, size=(1600, 600))
    # сравнение с референсом
    R.sheet(M('t28_tmp.jpg'), {'cols': 2, 'cells': [
        cell(None, 0, 8, 'спереди', pitch=4, bg='#2c2c33', hide=['hammer', 'hammer_ground']), cell('idle', 0, 35, 'с молотом, 3/4', pitch=6, bg='#2c2c33')]},
        three, size=(1472, 736))
    ref = Image.open(os.path.join(HERE, '..', 'docs', 'references', 't28', 'aris_look.jpg')).convert('RGB').resize((736, 736))
    b = Image.open(M('t28_tmp.jpg')).convert('RGB')
    c = Image.new('RGB', (2208, 736))
    c.paste(ref, (0, 0))
    c.paste(b, (736, 0))
    c.save(M('t28_vs_reference.jpg'), quality=90)
    os.remove(M('t28_tmp.jpg'))
    href = Image.open(os.path.join(HERE, '..', 'docs', 'references', 't28', 'aris_hammer.jpg')).convert('RGB')
    hm = Image.open(M('t28_hammer.jpg')).convert('RGB')
    w = 1500
    hr = href.resize((w, int(href.height * w / href.width)))
    c = Image.new('RGB', (w, hr.height + hm.height))
    c.paste(hr, (0, 0))
    c.paste(hm, (0, hr.height))
    c.save(M('t28_hammer.jpg'), quality=90)
