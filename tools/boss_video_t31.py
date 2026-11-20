#!/usr/bin/env python3
"""
Видео-превью T31 «Эреб, Длань Лжи» → docs/media/video/t31_*.mp4 (+ GIF-turntable 480 px) — тем же генератором, что у T29/T30:
инфраструктура tools/boss_video_b.py (Clip, покадровый рендер Playwright + ffmpeg, H.264 1280×720 30 fps) и тот же драйвер кадров
tools/boss_video_b_driver.js, только страница — шаблон T31 (tools/ereb_hand_preview.template.html: полупрозрачная рука, меши fx).
Эффекты в роликах условные (спрайты textures/sigil|fx и меши fx/meshes T31, движение — по таблицам письма), как на кадрах docs/media/t31_*.jpg;
в игре их рисует движок fx.

  python3 tools/boss_video_t31.py [--three путь/three.min.js] [t31_turntable t31_combat t31_spells t31_special t31_finale]
Координаты кадра — как у драйвера (кадр модели three.js): x — вправо от Эреба, y — вверх, ВПЕРЁД = −z (Эреб стоит в начале, смотрит в −z).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boss_video_b as VB  # noqa: E402
import gen_ereb_hand_render as HR  # noqa: E402
import cult_leader_render as CR  # noqa: E402

A = VB.A
Clip, orbit, camkeys, ease, lin, pulse, rnd = VB.Clip, VB.orbit, VB.camkeys, VB.ease, VB.lin, VB.pulse, VB.rnd
glow, decal, burst, swarm = VB.glow, VB.decal, VB.burst, VB.butterflies
TAG = 'T31 · Эреб, Длань Лжи'
GL, GH, GO, CRM, FL, WH = '#D9CCFF', '#F4EEFF', '#FFE7A0', '#E0606A', '#9A6BFF', '#FFFFFF'
LOOPS = {'ereb_hand_idle': 4.0, 'ereb_hand_walk': 1.2, 'ereb_hand_guard': 1.0, 'ereb_hand_grab_hold': 2.0, 'ereb_hand_rest': 2.0}
HAND = [0.97, 2.25, 0.34]         # рука над правым плечом (кадр: вперёд = −z)
FACE = [0.15, 1.75, -0.33]
HOLD = [0.5, 1.83, -1.34]
SLAM = [0.6, 0.05, -0.9]
TEXS = ['glow', 'mote_glass', 'mote_butterfly', 'spark_soft', 'wave_ring', 'illusion_seal', 'higher_cracks', 'ereb_hand_flame_ring',
        'ereb_hand_flame_rim', 'ereb_hand_grip_cone', 'ereb_hand_oath_mark', 'ereb_hand_mirror_floor', 'cult_flame_tongue', 'aura_shell',
        'cult_emblem', 'title:ereb_hand_ru', 'title:ereb_hand_hand_of_lies_ru', 'title:ereb_hand_mask_fall_ru', 'title:ereb_hand_full_reveal_ru']
MESHES = ['ereb_hand_giant_open', 'ereb_hand_giant_fist', 'ereb_hand_mask_shard', 'ereb_hand_mask_arrow', 'ereb_hand_mirror']


def build_page(kind, three, texs, preload):
    html = HR.page(['ereb_hand', 'steve'], {'cols': 1, 'cells': [{'model': 'ereb_hand', 'meshes': [{'mesh': m, 'pos': [0, 0, 0]} for m in MESHES]}]},
                   three)
    # варианты текстуры — отдельными моделями (драйвер берёт модель по имени)
    d0 = HR.model_entry('ereb_hand')
    extra = {}
    for v in ('mended', 'cracked'):
        e = dict(d0)
        e['tex'], e['glow'] = d0['variants'][v]['tex'], d0['variants'][v]['glow']
        e.pop('variants')
        extra['ereb_hand_' + v] = e
    extra['ereb_reflection'] = dict(d0)
    html = html.replace('"models":{', '"models":{%s,' % json.dumps(extra, ensure_ascii=False, separators=(',', ':'))[1:-1], 1)
    an = HR.anims()
    html = html.replace('"anims":{', '"anims":{%s,' % json.dumps({k: v for k, v in an.items() if k.startswith('ereb_hand')},
                                                                 separators=(',', ':'))[1:-1], 1)
    i = html.index('if (CELLS) {')
    j = html.rindex('</script>')
    drv = open(os.path.join(HERE, 'boss_video_b_driver.js'), encoding='utf-8').read()
    drv = drv.replace('/*VTEX*/null', json.dumps(VB.vtex(texs))).replace('/*PRELOAD*/null', json.dumps(preload))
    return html[:i] + drv + html[j:]


VB.build_page = build_page


def E(anim, t, mix=None, model='ereb_hand', **kw):
    o = dict(model=model, anim=anim, t=t, pos=kw.pop('pos', [0, 0, 0]), ry=kw.pop('ry', 0))
    if mix:
        o['mix'] = mix
    o.update(kw)
    return o


def ST(pos, ry=0, key=None, **kw):
    o = dict(model='steve', anim=None, t=0, pos=list(pos), ry=ry, key=key or 'steve%.1f_%.1f' % (pos[0], pos[2]))
    o.update(kw)
    return o


def gls(at, t, n, seed, speed=1.6, life=0.7, spread=(1, 1, 1), up=0.3, op=0.9, color=GH, grav=1.5):
    return burst('mote_glass', at, t, n, speed, (0.12, 0.26), color, seed, life=life, grav=grav, up=up, spread=spread, op=op, spin=300)


def bfl(at, t, n, seed, speed=1.4, life=1.2, op=0.9, up=0.6):
    return burst('mote_butterfly', at, t, n, speed, (0.22, 0.36), GL, seed, life=life, up=up, op=op, flap=True) + \
        burst('mote_butterfly', at, t, max(1, n // 3), speed, (0.22, 0.34), GO, seed + 7, life=life, up=up, op=op, flap=True)


def flash(at, t, size, color=WH, life=0.35, op=0.9):
    if not (0 <= t < life):
        return []
    k = 1 - t / life
    return [glow(at, size * (0.4 + 0.6 * k), color, op * k)]


def tenv(t, a, b):
    return pulse(t, a, 0.5, max(0.01, b - a - 1.25), 0.75)


def seq(items, pause=0.35):
    return VB.seq_anims(items, pause)


def run_seq(c, items, cam_fn, extra_objs=None, pause=0.35, model_fn=None):
    segs, L = seq(items, pause)

    def f(t):
        s, (a, ta, mix) = VB.seq_pose(segs, t, pause, LOOPS)
        o = E(a, ta, mix, model=(s['model'] or 'ereb_hand'))
        fr = {'objs': [o] + (extra_objs(t, s) if extra_objs else []), 'cap': s['cap'], 'sub': s['sub'], 'groundSize': 96, 'cam': cam_fn(t, L)}
        if s['fx'] and t >= s['t0']:
            x = s['fx'](t - s['t0'])
            fr['sprites'] = x.get('sprites', [])
            for k in ('meshes', 'title', 'speech', 'tint'):
                if k in x:
                    fr[k] = x[k]
            if 'objs' in x:
                fr['objs'] += x['objs']
            if 'op' in x:
                o['op'] = x['op']
        return fr
    c.seg(L, f)
    return c


# ================================================================== ролики
def turntable():
    c = Clip('t31_turntable', TAG)
    D = 8.0
    return c.seg(D, lambda t: {'objs': [E('ereb_hand_idle', t % 4.0, ry=-360 * t / D)], 'cam': orbit(0, 8, 8.4, (0, 1.6, 0)), 'groundSize': 96,
                               'cap': 'Эреб, Длань Лжи — покой', 'sub': 'ereb_hand_idle · рука парит над плечом, пальцы перебирают; маска, венец, накидка'})


def combat():
    c = Clip('t31_combat', TAG)
    VIC = [0.5, 0, -2.6]

    def hits(times):
        def fx(lt):
            s = []
            for h in times:
                s += flash([0.1, 1.35, -2.3], lt - h, 0.8, GO, 0.25)
            return {'sprites': s}
        return fx

    def slam(lt):
        u = lt - 0.8
        s = flash(SLAM, u, 3.0) + gls(SLAM, u, 26, 501, speed=2.6, life=0.8, up=0.6)
        if u >= 0:
            s.append(decal('higher_cracks', SLAM, 2.5, GL, 0.9 * max(0, 1 - u / 1.5)))
            if u < 0.6:
                s.append(decal('wave_ring', SLAM, 1 + 7 * u, GL, 0.8 * (1 - u / 0.6)))
        return {'sprites': s}

    def victim(lt, anim):                         # игрок в руке: стоит до хватки, потом в точке удержания
        if anim == 'ereb_hand_grab':
            k = ease(lin(lt, 0.6, 1.2))
            p = [VIC[0] + (HOLD[0] - VIC[0]) * k, 0.9 * k, VIC[2] + (HOLD[2] - VIC[2]) * k]
        elif anim == 'ereb_hand_grab_release':
            k = ease(lin(lt, 0.2, 0.7))
            p = [HOLD[0], 0.9 * (1 - k), HOLD[2] - 1.0 * k]
        else:
            p = [HOLD[0], 0.9, HOLD[2]]
        return p

    def grab_fx(anim):
        def fx(lt):
            p = victim(lt, anim)
            s = []
            if anim == 'ereb_hand_grab':
                s += flash([p[0], 1.6, p[2]], lt - 0.6, 1.2, GH) + gls([p[0], 1.6, p[2]], lt - 0.6, 10, 511, speed=1.2)
            if anim == 'ereb_hand_squeeze':
                s += flash([p[0], 1.8, p[2]], lt - 0.35, 1.0, CRM) + burst('spark_soft', [p[0], 1.8, p[2]], lt - 0.35, 12, 1.6, (0.06, 0.14), CRM, 512, life=0.5)
            if anim == 'ereb_hand_grab_hold':
                s.append(glow([p[0], 1.8, p[2]], 1.6, GL, 0.25))
            if anim == 'ereb_hand_grab_release':
                s += gls([p[0], 1.6, p[2]], lt - 0.2, 14, 513, speed=1.2)
            return {'sprites': s, 'objs': [ST(p, 180, key='vic')]}
        return fx

    def cast(lt):
        return {'sprites': flash([-0.3, 2.2, -0.3], lt - 0.75, 0.9, GH, 0.4) + flash(HAND, lt - 0.76, 1.4, GO, 0.4)}

    def phase2(lt):
        u = lt - 0.8
        s = flash([0.3, 0.3, -1.0], u, 2.4) + gls([0, 2.0, 0], u, 30, 521, speed=2.2, life=1.0, spread=(1.6, 1, 1.6))
        if 0 <= u < 1.0:
            s.append(decal('wave_ring', [0, 0.03, 0], 1 + 11 * u, GO, 0.7 * (1 - u)))
            s.append(decal('higher_cracks', [0.3, 0.03, -1.0], 2.0, GL, 0.8 * (1 - u)))
        return {'sprites': s}

    def phase3(lt):
        u = lt - 0.9
        s = flash(FACE, u, 1.0, GO) + burst('spark_soft', FACE, u, 12, 1.0, (0.05, 0.12), GO, 531, life=0.5)
        if 0 <= u < 1.2:
            s.append(decal('wave_ring', [0, 0.03, 0], 1 + 10 * u, CRM, 0.6 * (1 - u / 1.2)))
        return {'sprites': s, 'tint': ['#1a0a14', 0.35 * pulse(lt, 0.9, 0.2, 0.6, 0.6)]}

    items = [('ereb_hand_walk', 2.4, 'Шаг', 'ereb_hand_walk · накидка волной (3 кости), рука парит'),
             ('ereb_hand_guard', 1.6, 'Стойка «ан гард»', 'ereb_hand_guard'),
             ('ereb_hand_lunge', 1.4, 'Выпад', 'ereb_hand_lunge · hit 0.5', hits([0.5])),
             ('ereb_hand_flurry', 2.1, 'Серия из трёх уколов', 'ereb_hand_flurry · hit 0.45 / 0.8 / 1.15', hits([0.45, 0.8, 1.15])),
             ('ereb_hand_slam', 1.8, 'Удар рукой по площади', 'ereb_hand_slam · slam 0.8 — ладонь ≈0.9 бл. впереди, трещины r2.5', slam),
             ('ereb_hand_grab', 1.2, 'Хватка', 'ereb_hand_grab · grab 0.6', grab_fx('ereb_hand_grab')),
             ('ereb_hand_grab_hold', 2.0, 'Держит игрока', 'ereb_hand_grab_hold · союзники отбивают уроном по руке', grab_fx('ereb_hand_grab_hold')),
             ('ereb_hand_squeeze', 1.2, 'Сжатие', 'ereb_hand_squeeze · squeeze 0.35', grab_fx('ereb_hand_squeeze')),
             ('ereb_hand_grab_release', 1.0, 'Отпускает', 'ereb_hand_grab_release · release 0.2', grab_fx('ereb_hand_grab_release')),
             ('ereb_hand_cast', 1.4, 'Каст', 'ereb_hand_cast · щелчок «Длани» (cast 0.75)', cast),
             ('ereb_hand_phase2', 1.6, 'Фаза 2 «Длань» (66%)', 'ereb_hand_phase2 · кулак в землю (phase 0.8)', phase2),
             ('ereb_hand_phase3', 2.0, 'Фаза 3 «Глава Культа» (33%)', 'ereb_hand_phase3 · маска трескается (crack 0.9)', phase3)]
    items = [it + (None,) * (5 - len(it)) + ('ereb_hand_cracked' if it[0] == 'ereb_hand_phase3' else None,) for it in items]
    def cam(t, L):                       # хватка/удержание (≈11–17 с) — сбоку, чтобы жертва не закрывала Эреба
        k = pulse(t, 10.3, 0.8, 6.2, 0.8)
        return orbit(30 + 30 * math.sin(t / L * math.pi) + 50 * k, 10, 8.2 + 1.5 * k, (0.2, 1.4, -0.8 - 0.4 * k))
    return run_seq(c, items, cam)


def spells():
    c = Clip('t31_spells', TAG)
    circles = [(-3.2, -4.0, True), (0, -6.5, False), (3.2, -4.0, True), (-5.2, -1.0, False), (5.2, -1.5, True)]

    def flame(lt):
        s = []
        for i, (x, z, real) in enumerate(circles):
            m = lin(lt, 0.6, 0.9)
            on = lt >= 1.0
            if m > 0:
                s.append(decal('ereb_hand_flame_ring', [x, 0.03, z], 2.0 * (0.4 + 0.6 * m), FL, 0.9 * (1 if on else 0.6)))
            if on:
                R = rnd(600 + i)
                for k in range(7):
                    a, r = R() * 6.28, 1.4 * R()
                    h = 0.8 + 0.6 * abs(math.sin(lt * 7 + k))
                    s.append({'tex': 'cult_flame_tongue', 'at': [x + math.cos(a) * r, h / 2, z + math.sin(a) * r], 'w': 0.6, 'h': h, 'color': FL, 'op': 0.7})
                if real:
                    s.append(decal('ereb_hand_flame_rim', [x, 0.04, z], 2.05, GO, 0.45))
        return {'sprites': s, 'title': {'text': '«Ложное пламя»', 'op': tenv(lt, 0.1, 2.6)}}

    def grip(lt):
        s = []
        if lt < 1.05:
            s.append(decal('ereb_hand_grip_cone', [0, 0.03, 0], 6.0 * (0.3 + 0.7 * lin(lt, 0, 0.7)), GL, 0.8))
        u = lt - 1.0
        if 0 <= u < 0.4:
            R = rnd(611)
            for k in range(26):
                a, r0 = R() * 6.28, 1 + 2.5 * R()
                r = r0 * (1 - u / 0.4)
                s.append({'tex': 'mote_glass', 'at': [0.5 + math.cos(a) * r, 1.2 + (R() - 0.5) * r, -2 + math.sin(a) * r], 'size': 0.22, 'color': GH, 'op': 0.9})
        s += flash([0.5, 1.3, -2.0], u - 0.08, 2.2)
        return {'sprites': s, 'title': {'text': '«Стеклянная хватка»', 'op': tenv(lt, 0.1, 2.0)}}

    P1, P2 = [-2.2, 0, -4.5], [2.4, 0, -5.2]

    def oath(lt):
        k = lin(lt, 0.6, 0.8)
        s = []
        if k > 0:
            s.append({'tex': 'ereb_hand_oath_mark', 'at': [P1[0], 2.5, P1[2]], 'size': 0.9, 'color': CRM, 'op': 0.95 * k})
            s.append({'tex': 'ereb_hand_oath_mark', 'at': [P2[0], 2.4, P2[2]], 'size': 0.6, 'color': GH, 'op': 0.9 * k})
            s.append(glow([P1[0], 1.0, P1[2]], 1.8, CRM, 0.25 * k))
        s += flash([P1[0], 2.5, P1[2]], lt - 0.6, 1.4, CRM)
        return {'sprites': s, 'objs': [ST(P1, 180), ST(P2, 200)], 'title': {'text': '«Чужая клятва»', 'op': tenv(lt, 0.1, 2.0)}}

    MIR = [(7 * math.sin(i * math.pi / 3), -7 * math.cos(i * math.pi / 3), math.degrees(i * math.pi / 3)) for i in range(6)]

    def mirrors(lt):
        ms = []
        k = ease(lin(lt, 0.6, 1.1))
        for i, (x, z, a) in enumerate(MIR):
            ms.append({'mesh': 'ereb_hand_mirror', 'key': 'mir%d' % i, 'pos': [x, -3.4 * (1 - k), z], 'ry': -a, 'op': k})
        s, objs = [], []
        for j, mi in enumerate((0, 2, 4)):           # из трёх зеркал по очереди — отражения
            u = lt - 1.6 - j * 0.35
            if 0 <= u < 1.0:
                x, z, a = MIR[mi]
                ra = math.radians(a)
                pos = [x - math.sin(ra) * 0.8, 0, z + math.cos(ra) * 0.8]
                objs.append(E('ereb_hand_reflection_strike', u, pos=pos, ry=-a + 180, key='refl%d' % j, model='ereb_reflection',
                              op=0.55 * (1 - lin(u, 0.8, 1.0))))
                s += flash([x, 1.4, z], u, 2.0, GH, 0.3)
        return {'sprites': s, 'meshes': ms, 'objs': objs, 'title': {'text': '«Тысяча отражений»', 'op': tenv(lt, 0.1, 2.6)}}

    items = [('ereb_hand_false_flame', 3.0, '«Ложное пламя»', '5 кругов r2: 3 жгут (еле заметная золотая кромка), 2 — обманки', flame),
             ('ereb_hand_glass_grip', 2.2, '«Стеклянная хватка»', 'конус 70° на 6 бл. (1 с) → grip 1.0: сжатие и притяжение', grip),
             ('ereb_hand_foreign_oath', 2.4, '«Чужая клятва»', 'метка на игроке (багрянец) и на союзнике, которому уйдёт половина урона', oath),
             ('ereb_hand_thousand_reflections', 3.4, '«Тысяча отражений»', '6 зеркал; из зеркал бьют отражения (настоящие и ложные)', mirrors)]
    return run_seq(c, items, lambda t, L: orbit(200 if t < 8.2 else 200, 26 if t < 8.2 else 30, 11 if t < 8.2 else 15.5, (0, 0.8, -2.5)), pause=0.4)


def special():
    c = Clip('t31_special', TAG)
    V = [0, 0, -7.0]

    def sky(t):
        objs = [E('ereb_hand_hand_of_lies', min(t, 3.2))]
        ms, s = [], []
        u = t - 1.2
        if u >= 0:
            if u < 1.2:
                k = ease(u / 1.2)
                ms.append({'mesh': 'ereb_hand_giant_open', 'pos': [V[0], 3 + 23 * (1 - k) * (1 - k), V[2] + 1.8], 'ry': 180, 'op': min(1, u * 3)})
                s.append(decal('illusion_seal', V, 4 * (0.3 + 0.7 * k), GL, 0.6))
                pv = [V[0], 0, V[2]]
            else:
                w = u - 1.2
                lift = 2.5 * ease(min(1, w / 1.4))
                ms.append({'mesh': 'ereb_hand_giant_fist', 'pos': [V[0], 3 + lift, V[2] + 1.8], 'ry': 180, 'op': 1 - lin(w, 2.6, 3.0)})
                s += flash([V[0], 2, V[2]], w, 3.0, GH) + gls([V[0], 2, V[2]], w, 24, 701, speed=2.4, life=0.8)
                pv = [V[0], 1.6 + lift, V[2]]
            objs.append(ST(pv, 0, key='vic'))
        else:
            objs.append(ST(V, 0, key='vic'))
        cam = camkeys([(0, 160, 8, 13, (0, 2.0, -3.5)), (2.4, 200, 14, 18, (0, 5.0, -6.0)), (5.6, 215, 8, 14, (0, 3.5, -6.5))], t)
        return {'objs': objs, 'meshes': ms, 'sprites': s, 'cam': cam, 'groundSize': 96, 'bg': 0x1d1730,
                'cap': 'Особое: «Длань Лжи» (66%)', 'sub': 'рука уходит в небо (rise 0.5) → огромная рука опускается на игрока (descend 1.2) → кулак; 6 с ложной арены',
                'title': {'img': 'title:ereb_hand_hand_of_lies_ru', 'op': tenv(t, 0.3, 3.0)},
                'tint': ['#3a2a66', 0.3 * lin(t, 2.4, 2.8) * (1 - lin(t, 5.2, 5.6))]}
    c.seg(5.6, sky)
    PL = [(-3.0, -6.5), (2.5, -7.0), (0.0, -9.0)]

    def mask(t):
        objs = []
        s, ms = [], []
        if t < 2.2:
            objs.append(E('ereb_hand_mask_fall', t))
            s += [glow([0.15, 1.9, -0.6], 0.6, GO, 0.8)] if 0.85 <= t < 1.0 else []
            u = t - 1.1
            s += flash([-0.2, 2.8, -0.6], u, 3.0) + gls([-0.2, 2.8, -0.6], u, 30, 711, speed=4.0, life=1.0, spread=(1.5, 0.6, 1.5)) + \
                bfl([-0.2, 2.8, -0.6], u, 6, 712)
        else:
            objs.append(E('ereb_hand_idle', (t - 2.2) % 4.0, mask_scale=True))
            objs[-1]['anim'] = 'ereb_hand_mask_return'
            objs[-1]['t'] = 0.0
        for i, (x, z) in enumerate(PL):
            objs.append(ST([x, 0, z], 0, key='pl%d' % i))
        if t >= 1.4:
            w = t - 1.4
            for i, (x, z) in enumerate(PL):
                a = w * 0.5 + i * 2.1
                pos = [3.5 * math.sin(a), 1.8 + 0.5 * math.sin(w * 1.3 + i), -5 + 3.5 * math.cos(a)]
                broken = (i == 0 and w > 3.2) or (i == 1 and w > 4.0)
                if not broken:
                    ms.append({'mesh': 'ereb_hand_mask_shard', 'key': 'sh%d' % i, 'pos': pos, 'ry': math.degrees(a) + 180, 'scale': 1.3,
                               'op': min(1, w * 3)})
                if i == 0:
                    s += flash(pos, w - 3.2, 1.4) + gls(pos, w - 3.2, 18, 720, speed=1.6) + bfl(pos, w - 3.2, 3, 721)
                if i == 1:
                    s += flash(pos, w - 4.0, 1.4) + gls(pos, w - 4.0, 18, 722, speed=1.6)
                if i == 2 and w > 4.6:
                    u = w - 4.6
                    s += flash([x, 1.0, z], u, 2.6, CRM) + gls([x, 1.0, z], u, 22, 723, speed=2.2)
                    if u < 0.6:
                        s.append(decal('wave_ring', [x, 0.03, z], 1 + 3 * u / 0.6, CRM, 0.7 * (1 - u / 0.6)))
            if w < 2.0:
                x, z = PL[0]
                ms.append({'mesh': 'ereb_hand_mask_arrow', 'pos': [x, 1.2, z + 1.2], 'ry': 200, 'scale': 1.6, 'op': 0.6 + 0.4 * math.sin(w * 8)})
        cam = camkeys([(0, 20, 6, 4.0, (0.1, 1.7, -0.3)), (1.3, 200, 18, 13, (0, 1.4, -4.5)), (6.4, 215, 18, 13, (0, 1.4, -4.5))], t)
        sub = ('«Длань» срывает маску (tear 0.85), маска разбивается (shatter 1.1)' if t < 1.4 else
               'осколок на каждого игрока, в нём — его лицо; стрелка к своему 2 с; свой — разбить, чужой только звенит; не успел — взрыв')
        return {'objs': objs, 'meshes': ms, 'sprites': s, 'cam': cam, 'groundSize': 96, 'cap': 'Особое: «Падение маски» (45%)', 'sub': sub,
                'title': {'img': 'title:ereb_hand_mask_fall_ru', 'op': tenv(t, 0.9, 3.4)}}
    c.seg(6.4, mask)

    def ret(t):
        o = E('ereb_hand_mask_return', min(t, 1.4), model='ereb_hand_mended' if t >= 0.7 else 'ereb_hand')
        s = []
        if t < 0.7:
            R = rnd(731)
            for k in range(20):
                a, r0 = R() * 6.28, 1 + 3 * R()
                r = r0 * (1 - t / 0.7)
                s.append({'tex': 'mote_glass', 'at': [FACE[0] + math.cos(a) * r, FACE[1] + (R() - 0.5) * r, FACE[2] + math.sin(a) * r], 'size': 0.2,
                          'color': GH, 'op': 0.9})
        s += flash(FACE, t - 0.7, 1.0, GO)
        return {'objs': [o], 'sprites': s, 'cam': orbit(25, 4, 3.4, (0.1, 1.7, -0.3)), 'groundSize': 96,
                'cap': 'Маска собирается', 'sub': 'ereb_hand_mask_return · осколки слетаются к лицу, mend 0.7 → текстура ereb_hand_mended'}
    c.seg(2.0, ret)
    return c


def finale():
    c = Clip('t31_finale', TAG)

    def spawn(t):
        o = E('ereb_hand_spawn', min(t, 5.5), op=lin(t, 1.7, 1.9))
        s = []
        if t < 0.6:
            R = rnd(801)
            for k in range(24):
                a, r0 = R() * 6.28, 0.5 + 2.5 * R()
                r = r0 * (1 - t / 0.6)
                s.append({'tex': 'mote_glass', 'at': [HAND[0] + math.cos(a) * r, HAND[1] + (R() - 0.5) * r, HAND[2] + math.sin(a) * r], 'size': 0.2,
                          'color': GH, 'op': 0.9})
        s += flash(HAND, t - 0.6, 1.6, GH)
        if 0.3 < t < 1.9:
            s += swarm([0, 1.2, 0], t, 36, 2.2 - 0.9 * lin(t, 0.8, 1.8), 2.4, 802)
        s += flash([0, 1.1, 0], t - 1.8, 2.6) + bfl([0, 1.1, 0], t - 1.8, 16, 803)
        s.append(decal('illusion_seal', [0, 0.03, 0], 2.4, GL, 0.5 * (1 - lin(t, 5.0, 5.5))))
        sp = {'text': '«Вот мы и снова встретились»', 'op': pulse(t, 4.3, 0.2, 1.4, 0.4)} if t > 4.2 else None
        fr = {'objs': [o], 'sprites': s, 'cam': camkeys([(0, 15, 6, 9, (0.3, 1.8, 0)), (5.5, 30, 6, 6.5, (0.2, 1.6, 0))], t), 'groundSize': 96,
              'cap': 'Появление', 'sub': 'ereb_hand_spawn · рука из стекла (form_hand 0.6), он из роя (form 1.8), поклон, салют, фраза (speak 4.3)',
              'title': {'img': 'title:ereb_hand_ru', 'op': tenv(t, 2.2, 4.25)}}
        if sp:
            fr['speech'] = sp
        return fr
    c.seg(6.0, spawn)

    def reveal(t):
        o = E('ereb_hand_full_reveal', min(t, 4.0), model='ereb_hand_cracked')
        s = swarm([0, 1.4, 0], t, 40, 2.6, 3.0, 811) if t > 0.8 else []
        s += flash([0.3, 3.4, -0.2], t - 1.4, 1.6, GH, 1.0)
        s += flash([0, 2, 0], t - 2.6, 10.0, WH, 0.9)
        return {'objs': [o], 'sprites': s, 'cam': camkeys([(0, 20, 8, 8, (0, 1.8, 0)), (4.0, 35, 10, 9.5, (0, 2.2, 0))], t), 'groundSize': 96,
                'cap': '«Сон Бабочки: Полное Раскрытие» (20%)', 'sub': 'ereb_hand_full_reveal · рой бабочек, рука раскрывается (open 1.4), каст (cast 2.6)',
                'title': {'img': 'title:ereb_hand_full_reveal_ru', 'op': tenv(t, 0.4, 3.6)}, 'tint': ['#ffffff', 0.85 * pulse(t, 2.6, 0.08, 0.15, 0.6)]}
    c.seg(4.0, reveal)

    def world(t):
        objs = [E('ereb_hand_guard', t % 1.0, model='ereb_hand_cracked'), ST([-3, 0, -6], 0, key='p1'), ST([3.5, 0, -7], 0, key='p2')]
        ms = [{'mesh': 'ereb_hand_giant_open', 'pos': [0, 8.5 + 0.6 * math.sin(t * 0.8), -9], 'ry': 0, 'scale': 1.3}]
        s = [decal('ereb_hand_mirror_floor', [0, 0.03, 0], 24, GL, 0.55, rot=t * 3)]
        R = rnd(821)
        for k in range(70):
            x, y, z = (R() - 0.5) * 30, R() * 6, (R() - 0.5) * 30
            s.append({'tex': 'mote_glass', 'at': [x, y + 0.2 * math.sin(t + k), z], 'size': 0.15, 'color': GH, 'op': 0.7})
        s += swarm([0, 3, -2], t, 24, 8, 4, 822)
        if t > 2.2:                                     # удар Длани во сне
            u = t - 2.2
            P = [3.5, 0, -7]
            if u < 1.5:
                s.append(decal('illusion_seal', [P[0], 0.03, P[2]], 4 * (0.3 + 0.7 * u / 1.5), GL, 0.7))
            if 1.5 <= u < 2.6:
                w = u - 1.5
                ms.append({'mesh': 'ereb_hand_giant_open', 'key': 'slam', 'pos': [P[0], 1.5 + 14 * max(0, 1 - w / 0.3) ** 2, P[2] + 2.5], 'ry': 180, 'scale': 1.0,
                           'op': 1 - lin(w, 0.8, 1.1)})
                s += flash([P[0], 0.5, P[2]], w - 0.3, 4.0) + gls([P[0], 0.5, P[2]], w - 0.3, 26, 823, speed=3.0)
                if w >= 0.3:
                    s.append(decal('higher_cracks', [P[0], 0.03, P[2]], 4.0, GL, 0.9 * (1 - lin(w, 0.6, 1.1))))
        cam = camkeys([(0, 175, 12, 17, (0, 5.0, -5)), (5.0, 200, 16, 19, (0, 6.0, -5))], t)
        return {'objs': objs, 'meshes': ms, 'sprites': s, 'cam': cam, 'groundSize': 96, 'bg': 0x1d1730, 'tint': ['#2e2450', 0.25],
                'cap': 'Мир сна: «Полное Раскрытие»', 'sub': 'зеркальный пол r30, огромная Длань над ареной бьёт по площади; бой с Эребом внутри сна до конца'}
    c.seg(5.0, world)

    def death(t):
        o = E('ereb_hand_false_death', min(t, 5.0), model='ereb_hand_cracked', op=1 - lin(t, 3.8, 3.95))
        s = flash([0.97, 2.0, 0.3], t - 0.7, 2.0, GH) + gls([0.97, 2.0, 0.3], t - 0.7, 30, 831, speed=1.4, life=1.2)
        s += flash([0, 1.1, 0], t - 3.8, 2.6) + bfl([0, 1.1, 0], t - 3.8, 40, 832, speed=2.0, life=1.6, up=1.0)
        fr = {'objs': [o], 'sprites': s, 'cam': camkeys([(0, 20, 6, 6.5, (0.1, 1.6, 0)), (2.0, 15, 4, 4.0, (0.1, 1.8, 0)), (5.0, 25, 8, 7.5, (0, 1.8, 0))], t),
              'groundSize': 96, 'cap': 'Ложная смерть', 'sub': 'ereb_hand_false_death · рука трескается (0.7), фраза (speak 1.6), распадается на бабочек (vanish 3.8)'}
        if t > 1.5:
            fr['speech'] = {'text': '«А вы...стали сильнее»', 'op': pulse(t, 1.6, 0.2, 1.6, 0.4)}
        return fr
    c.seg(5.0, death)

    def fin(t):
        o = E('ereb_hand_finisher', min(t, 3.6))
        V0 = [0.5, 0, -2.6]
        if t < 0.6:
            vp = V0
        else:
            k = ease(lin(t, 0.6, 1.2))
            vp = [V0[0] + (HOLD[0] - V0[0]) * k, 1.0 * k, V0[2] + (HOLD[2] - V0[2]) * k]
        objs = [o]
        s = flash([vp[0], 1.6, vp[2]], t - 0.6, 1.2, GH)
        if t < 2.1:
            objs.append(ST(vp, 180, key='vic'))
        if 1.5 <= t < 2.1:
            s.append({'tex': 'aura_shell', 'at': [vp[0], vp[1] + 1.0, vp[2]], 'w': 1.4, 'h': 2.2, 'color': GH, 'op': 0.5 * lin(t, 1.5, 1.9)})
        s += flash([vp[0], 2.0, vp[2]], t - 2.1, 2.4) + gls([vp[0], 2.0, vp[2]], t - 2.1, 40, 841, speed=2.2) + bfl([vp[0], 2.0, vp[2]], t - 2.1, 12, 842)
        return {'objs': objs, 'sprites': s, 'cam': orbit(105, 8, 7.5, (0.4, 1.6, -1.2)), 'groundSize': 96,
                'cap': 'Добивание', 'sub': 'ereb_hand_finisher · рука хватает (0.6), сжимает (1.5), жертва трескается стеклом и рассыпается бабочками (2.1)'}
    c.seg(3.6, fin)
    return c


CLIPS = {'t31_turntable': turntable, 't31_combat': combat, 't31_spells': spells, 't31_special': special, 't31_finale': finale}


def main(args):
    three = args[args.index('--three') + 1] if '--three' in args else None
    names = [a for a in args if a in CLIPS] or list(CLIPS)
    pre = [{'model': m} for m in ('ereb_hand', 'ereb_hand_mended', 'ereb_hand_cracked', 'ereb_reflection', 'steve')]
    for n in names:
        clip = CLIPS[n]()
        VB.render(clip, 'ereb_hand', three, TEXS, pre)


if __name__ == '__main__':
    main(sys.argv[1:])
