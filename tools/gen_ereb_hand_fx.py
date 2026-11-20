#!/usr/bin/env python3
"""
T31 «Эреб, Длань Лжи» — эффекты (fx/ereb_hand_*.json, стиль fx/styles/ereb_hand.json), меши (fx/meshes/ereb_hand_*.json),
рисунки (textures/sigil/ereb_hand_*.png), звуки (sounds.json: ereb_hand.*) и субтитры. Вызывается из tools/gen_ereb_hand.py (run(M)).
Время — тики, размеры — блоки, привязки — оси взгляда (x — вправо, y — вверх, z — вперёд), как в docs/fx.md.
Стиль — стекло иллюзий (бледное бело-фиолетовое, как призрачная рука) + золото и багрянец Культа; «ложное пламя» фиолетово-золотое.
Правило владельца: никаких лучей / нитей от босса к цели — связь с целью только знаком у самой цели.
Меши рук строятся из костей модели (прямая кинематика tools/ereb_hand_fk.py) — это та же рука, что над плечом, только огромная.
"""
import json
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import ereb_hand_fk as F
import gen_ereb_hand_anims as AN

M = None
GOLD, GOLD_HI, GLASS, GLASS_HI, CRIMSON, CRIMSON_HI, INK, WHITE = '#E8B84A', '#FFE7A0', '#D9CCFF', '#F4EEFF', '#A3323B', '#E0606A', '#1E0A12', '#FFFFFF'
FLAME, FLAME_HI = '#9A6BFF', '#E6C8FF'           # ложное пламя: фиолетовое стекло
HAND = 'caster+0.97,2.25,-0.34'                  # призрачная рука в покое (центр ладони), оси взгляда: x>0 — справа от него
FACE = 'caster+0.15,1.75,0.33'                   # маска (правая половина лица)
PALM_HOLD = 'caster+0.5,1.83,1.34'               # ладонь в хватке/удержании (FK: grab_hold)
SLAM = 'caster+0.6,0.05,0.9'                     # центр ладони при ударе по площади (FK: slam 0.8)
GAUNT = 'caster-0.3,2.2,0.3'                     # поднятая «Длань» (каст)
T_INTRO = 110


def E(type_, delay=0, at='caster', **kw):
    o = {'type': type_, 'delay': delay, 'at': at}
    o.update(kw)
    return o


def ease(d, e='easeOutCubic'):
    return {'duration': d, 'easing': e}


def fx(id_, comment, dur, els):
    M.write_json('fx/%s.json' % id_, {'comment': 'T31 ' + comment + ' Сгенерировано tools/gen_ereb_hand.py (gen_ereb_hand_fx.py).',
                                      'style': 'ereb_hand', 'duration': dur, 'elements': els})
    FX_LIST.append((id_, dur, comment))


FX_LIST = []


def glass(delay, at, count, rate=None, dur=2, spread=0.6, speed=0.08, gravity=0.006, life=18, size=(0.18, 0.05), color=GLASS_HI, **kw):
    return E('sprites', delay, at, duration=dur, texture='mote_glass', count=count, rate=rate or count, spread=spread, speed=speed,
             gravity=gravity, spin=140, tumble=True, size=list(size), life=life, color=color, **kw)


def butterflies(delay, at, count, rate, dur, spread=0.5, speed=0.05, gravity=-0.008, life=40, size=(0.32, 0.12), **kw):
    return [E('sprites', delay, at, duration=dur, texture='mote_butterfly', count=count, rate=rate, spread=spread, speed=speed, gravity=gravity,
              sway=0.6, size=list(size), life=life, color=GLASS, glow=0.45, **kw),
            E('sprites', delay, at, duration=dur, texture='mote_butterfly_side', count=max(1, count // 2), rate=max(0.5, rate / 2), spread=spread,
              speed=speed, gravity=gravity, sway=0.6, size=[size[0] * 0.9, size[1]], life=life, color=GOLD_HI, glow=0.35, **kw)]


def sparks(delay, at, count, color=GOLD, spread=0.3, speed=0.1, life=10, **kw):
    return E('sprites', delay, at, duration=1, texture='spark_soft', count=count, rate=count, spread=spread, speed=speed, gravity=0.015,
             size=[0.12, 0.02], life=life, color=color, **kw)


# ================================================================== рисунки (textures/sigil, 512, белый + альфа — красятся цветом элемента)
S = 512


def _save(img, name):
    img.save(M.out('textures/sigil/%s.png' % name))


def _mask_to_rgba(m):
    rgba = Image.new('RGBA', m.size, (255, 255, 255, 0))
    rgba.putalpha(m)
    return rgba


def tex_flame_ring():
    """Кольцо ложного пламени: языки внутрь и наружу от окружности r≈0.8, мягкие."""
    K = 2
    m = Image.new('L', (S * K, S * K), 0)
    d = ImageDraw.Draw(m)
    C = S * K / 2
    rng = random.Random(311)
    for i in range(36):
        a = 2 * math.pi * i / 36 + rng.random() * 0.05
        r0, ln, w = C * 0.78, C * (0.14 + 0.12 * rng.random()), C * 0.07
        bx, by = C + r0 * math.cos(a), C + r0 * math.sin(a)
        tx, ty = C + (r0 + ln) * math.cos(a), C + (r0 + ln) * math.sin(a)
        nx, ny = -math.sin(a) * w, math.cos(a) * w
        d.polygon([(bx + nx, by + ny), (tx, ty), (bx - nx, by - ny), (C + (r0 - ln * 0.4) * math.cos(a), C + (r0 - ln * 0.4) * math.sin(a))], fill=255)
    d.ellipse([C - C * 0.82, C - C * 0.82, C + C * 0.82, C + C * 0.82], outline=255, width=int(C * 0.05))
    m = m.filter(ImageFilter.GaussianBlur(6 * K)).resize((S, S), Image.LANCZOS)
    a = np.asarray(m, np.float32) / 255
    a = np.clip(a * 1.6, 0, 1)
    _save(_mask_to_rgba(Image.fromarray((a * 255).astype(np.uint8))), 'ereb_hand_flame_ring')


def tex_flame_rim():
    """Еле заметная золотая кромка настоящего круга: тонкое кольцо с насечками (подсказка внимательным)."""
    K = 2
    m = Image.new('L', (S * K, S * K), 0)
    d = ImageDraw.Draw(m)
    C = S * K / 2
    d.ellipse([C - C * 0.93, C - C * 0.93, C + C * 0.93, C + C * 0.93], outline=255, width=int(C * 0.018))
    for i in range(48):
        a = 2 * math.pi * i / 48
        r0, r1 = C * (0.885 if i % 4 else 0.86), C * 0.93
        d.line([(C + r0 * math.cos(a), C + r0 * math.sin(a)), (C + r1 * math.cos(a), C + r1 * math.sin(a))], fill=255, width=int(C * 0.01))
    _save(_mask_to_rgba(m.resize((S, S), Image.LANCZOS)), 'ereb_hand_flame_rim')


def tex_grip_cone():
    """Конус-предупреждение «Стеклянной хватки» (вид сверху, вершина в центре, раскрыт вверх по картинке = вперёд): 70°, тает к краю."""
    m = Image.new('L', (S, S), 0)
    px = m.load()
    C = S / 2
    for y in range(S):
        for x in range(S):
            dx, dy = x - C, C - y
            r = math.hypot(dx, dy) / C
            ang = abs(math.degrees(math.atan2(dx, dy)))
            if r <= 1 and ang <= 35:
                edge = min(1, (35 - ang) / 4) * min(1, (1 - r) / 0.05)
                fill = 0.25 + 0.75 * (r ** 2)
                band = 1.0 if (0.95 < r or ang > 32) else fill * 0.55
                px[x, y] = int(255 * edge * band)
    _save(_mask_to_rgba(m), 'ereb_hand_grip_cone')


def tex_oath_mark():
    """Метка «Чужой клятвы»: два сцепленных кольца (клятва двоих) и око культа между ними."""
    K = 2
    m = Image.new('L', (S * K, S * K), 0)
    d = ImageDraw.Draw(m)
    C = S * K / 2
    w = int(C * 0.05)
    for sx in (-1, 1):
        cx = C + sx * C * 0.28
        d.ellipse([cx - C * 0.5, C - C * 0.5, cx + C * 0.5, C + C * 0.5], outline=255, width=w)
    ew, eh = C * 0.22, C * 0.12
    d.chord([C - ew, C - eh, C + ew, C + eh], 0, 360, fill=255)
    d.ellipse([C - eh * 0.7, C - eh * 0.7, C + eh * 0.7, C + eh * 0.7], fill=0)
    d.ellipse([C - eh * 0.3, C - eh * 0.3, C + eh * 0.3, C + eh * 0.3], fill=255)
    for i in range(12):
        a = 2 * math.pi * i / 12
        d.ellipse([C + C * 0.9 * math.cos(a) - w, C + C * 0.9 * math.sin(a) - w, C + C * 0.9 * math.cos(a) + w, C + C * 0.9 * math.sin(a) + w], fill=255)
    _save(_mask_to_rgba(m.resize((S, S), Image.LANCZOS)), 'ereb_hand_oath_mark')


def tex_mirror_floor():
    """Пол «Полного Раскрытия»: зеркальные плиты-ромбы с золотыми швами, к краю — трещины; круг r = 1 (на decal радиус 30)."""
    K = 2
    m = Image.new('L', (S * K, S * K), 0)
    d = ImageDraw.Draw(m)
    C = S * K / 2
    step = C / 7
    for i in range(-8, 9):
        for sgn in (-1, 1):
            x0 = C + i * step * 1.3
            d.line([(x0 - sgn * C * 2, C - C * 2), (x0 + sgn * C * 2, C + C * 2)], fill=150, width=int(K * 2))
    for r in (0.3, 0.62, 0.96):
        d.ellipse([C - C * r, C - C * r, C + C * r, C + C * r], outline=255, width=int(K * 3))
    rng = random.Random(77)
    for _ in range(40):
        a = rng.random() * 2 * math.pi
        r = C * 0.96
        pts = [(C + r * math.cos(a), C + r * math.sin(a))]
        for _k in range(4):
            r -= C * (0.03 + 0.05 * rng.random())
            a += (rng.random() - 0.5) * 0.12
            pts.append((C + r * math.cos(a), C + r * math.sin(a)))
        d.line(pts, fill=230, width=int(K * 2))
    a = np.asarray(m, np.float32) / 255
    yy, xx = np.mgrid[0:S * K, 0:S * K]
    rr = np.hypot(xx - C, yy - C) / C
    a = a * (rr <= 1.0) * (0.55 + 0.45 * rr)
    img = Image.fromarray((a * 255).astype(np.uint8)).resize((S, S), Image.LANCZOS)
    _save(_mask_to_rgba(img), 'ereb_hand_mirror_floor')


def tex_shard_glass():
    """Стекло осколка маски (цветное): бледное фарфорово-золотое с бликом по диагонали — поверх него код кладёт лицо игрока (скин)."""
    W = 256
    img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    a = np.zeros((W, W, 4), np.float32)
    yy, xx = np.mgrid[0:W, 0:W] / W
    base = np.array([239, 232, 212], np.float32)
    a[..., :3] = base
    a[..., 3] = 120
    streak = np.exp(-((xx - yy - 0.15) ** 2) / 0.004) + 0.6 * np.exp(-((xx - yy + 0.25) ** 2) / 0.002)
    a[..., :3] = np.clip(base + streak[..., None] * 60, 0, 255)
    a[..., 3] = np.clip(120 + streak * 120, 0, 255)
    img = Image.fromarray(a.astype(np.uint8), 'RGBA')
    _save(img, 'ereb_hand_shard_glass')


def tex_butterfly_rim():
    """Золотая кромка крыльев НАСТОЯЩЕЙ бабочки «Роя лжи»: контур силуэта mote_butterfly (тот же размер — кладётся поверх)."""
    src = Image.open(os.path.join(M.A, 'textures', 'sigil', 'mote_butterfly.png')).convert('RGBA')
    a = src.getchannel('A')
    inner = a.filter(ImageFilter.MinFilter(15))
    rim = np.clip(np.asarray(a, np.float32) - np.asarray(inner, np.float32), 0, 255)
    rim = np.clip(rim * 1.6, 0, 255).astype(np.uint8)
    _save(_mask_to_rgba(Image.fromarray(rim).filter(ImageFilter.GaussianBlur(0.6))), 'ereb_hand_butterfly_rim')


# грани скина игрока 64×64 (внутренний и внешний слой): (u, v, w, h, d) — как у ванильного PlayerModel
SKIN_BOXES = [(0, 0, 8, 8, 8), (32, 0, 8, 8, 8), (16, 16, 8, 12, 4), (16, 32, 8, 12, 4), (40, 16, 4, 12, 4), (40, 32, 4, 12, 4),
              (32, 48, 4, 12, 4), (48, 48, 4, 12, 4), (0, 16, 4, 12, 4), (0, 32, 4, 12, 4), (16, 48, 4, 12, 4), (0, 48, 4, 12, 4)]


def tex_traitor_glass():
    """«Отражение-предатель»: стеклянный оверлей поверх скина игрока (UV 64×64 ванильного PlayerModel, оба слоя). Код рисует копию
    моделью игрока с его скином полупрозрачно (entityTranslucent, альфа ≈0.55) и вторым проходом — этот оверлей: бледно-фиолетовое стекло,
    светлые кромки граней, золотые трещины, диагональный блик. Глоумаска — трещины."""
    W = 64
    col = np.zeros((W, W, 4), np.float32)
    glow = np.zeros((W, W, 4), np.float32)
    rng = random.Random(3131)
    glass_rgb = np.array([217, 204, 255], np.float32)
    edge_rgb = np.array([246, 240, 255], np.float32)
    gold = np.array([248, 210, 96], np.float32)

    def face(x0, y0, w, h):
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                e = x in (x0, x0 + w - 1) or y in (y0, y0 + h - 1)
                k = (x - x0 + (y - y0)) / max(1, w + h)
                streak = 1.0 if abs(k - 0.42) < 0.07 else 0.0
                if e:
                    col[y, x] = [*edge_rgb, 120]
                else:
                    col[y, x] = [*(glass_rgb + streak * 30), 40 + 70 * streak]
        # трещина: ломаная от края грани внутрь
        if w * h >= 16 and rng.random() < 0.8:
            x, y = x0 + rng.randrange(w), y0
            for _ in range(h + w // 2):
                if not (x0 <= x < x0 + w and y0 <= y < y0 + h):
                    break
                col[y, x] = [*gold, 235]
                glow[y, x] = [*gold, 255]
                y += 1
                x += rng.choice((-1, 0, 0, 1))
    for u, v, w, h, d in SKIN_BOXES:
        face(u + d, v, w, d)                      # верх
        face(u + d + w, v, w, d)                  # низ
        face(u, v + d, d, h)                      # правый бок
        face(u + d, v + d, w, h)                  # перед
        face(u + d + w, v + d, d, h)              # левый бок
        face(u + 2 * d + w, v + d, w, h)          # зад
    Image.fromarray(col.astype(np.uint8), 'RGBA').save(M.out('textures/entity/ereb_hand/traitor_glass.png'))
    Image.fromarray(glow.astype(np.uint8), 'RGBA').save(M.out('textures/entity/ereb_hand/traitor_glass_glowmask.png'))


def textures():
    tex_butterfly_rim()
    tex_traitor_glass()
    tex_flame_ring()
    tex_flame_rim()
    tex_grip_cone()
    tex_oath_mark()
    tex_mirror_floor()
    tex_shard_glass()


# ================================================================== меши
def _euler_yxz(R):
    """R = Ry·Rx·Rz → (rx, ry, rz), градусы (как Euler «YXZ» three.js)."""
    x = math.asin(max(-1, min(1, -R[1][2])))
    if abs(R[1][2]) < 0.9999:
        y = math.atan2(R[0][2], R[2][2])
        z = math.atan2(R[1][0], R[1][1])
    else:
        y = math.atan2(-R[2][0], R[0][0])
        z = 0
    return [round(math.degrees(x), 2), round(math.degrees(y), 2), round(math.degrees(z), 2)]


def hand_boxes(pose_dict, scale, origin):
    """Бруски призрачной руки в позе pose_dict (поза генератора анимаций) → [x0..z1, тон, [rx, ry, rz]] в блоках, оси взгляда (z — вперёд),
    центр запястья → origin. Тона: 0 стекло, 1 стекло-тень, 2 золото (шов/кончик, светится), 3 осколки."""
    model = F.Model()
    pose = {}
    for k, v in pose_dict.items():
        if k.endswith('_pos'):
            pose.setdefault(k[:-4], [[0, 0, 0], [0, 0, 0], [1, 1, 1]])[1] = v
        elif k.endswith('_scale'):
            pose.setdefault(k[:-6], [[0, 0, 0], [0, 0, 0], [1, 1, 1]])[2] = v
        else:
            pose.setdefault(k, [[0, 0, 0], [0, 0, 0], [1, 1, 1]])[0] = v
    pose['ghost_hand'][1] = [0, 0, 0]
    pose['ghost_hand'][2] = [1, 1, 1]
    W = model.world(pose)
    Sz = np.diag([1.0, 1.0, -1.0])                   # кадр three (z назад) → оси взгляда (z вперёд)
    wrist = model.point(W, 'ghost_wrist', [-15.5, 30.0, 5.5])
    wrist3 = np.array([-wrist[0], wrist[1], wrist[2]])
    out = []
    for bn in AN.GHOST:
        for m, lo, hi in model.cubes(bn):
            mw = W[bn] @ m
            c3 = mw @ np.array([*(lo + hi) / 2, 1.0])
            size = (hi - lo)
            R = Sz @ mw[:3, :3] @ Sz
            c = Sz @ (c3[:3] - wrist3)
            c = c / 16 * scale + np.array(origin)
            half = size / 16 * scale / 2
            tip = bn.endswith('_3') or bn == 'ghost_thumb_2'
            eu = _euler_yxz(R)

            def slab(y0, y1, grow, tone_):             # кусок бруска по высоте (доли −1…1 от центра), чуть шире/уже
                hh = half.copy()
                hh[1] = half[1] * (y1 - y0) / 2
                hh[0] *= grow
                hh[2] *= grow
                off = R @ np.array([0, half[1] * (y0 + y1) / 2, 0])
                out.append([*(c + off - hh).round(3).tolist(), *(c + off + hh).round(3).tolist(), tone_, eu])
            if bn == 'ghost_hand':                       # тающие осколки запястья
                out.append([*(c - half).round(3).tolist(), *(c + half).round(3).tolist(), 3, eu])
                continue
            if tip:                                      # кончик: стекло + тонкая золотая шапочка (как на модели)
                slab(-1, 0.45, 1.0, 0)
                slab(0.45, 1.0, 1.04, 2)
            else:
                slab(-1, 1, 1.0, 1 if bn.endswith('_2') or bn == 'ghost_wrist' else 0)
            if bn.startswith(('ghost_index', 'ghost_middle', 'ghost_ring', 'ghost_pinky', 'ghost_thumb')):
                slab(-1, -0.86, 1.08, 2)                 # золотой шов сустава
            slab(-0.8, 0.8 if not tip else 0.3, 0.55, 4)  # светящаяся сердцевина стекла
    return out


HAND_TONES = ['#D9CFF7', '#B8A9EC', '#F8D260', '#F4EEFF', '#8E7BD6']


def mesh(name, comment, parts, formed=8, collapse=8, center=0):
    M.write_json('fx/meshes/%s.json' % name, {'comment': 'T31 ' + comment + ' Сгенерировано tools/gen_ereb_hand.py (gen_ereb_hand_fx.py).',
                                               'style': 'ereb_hand', 'center': center, 'formedAt': formed,
                                               'collapse': {'duration': collapse, 'easing': 'easeInCubic'}, 'parts': parts})
    MESHES.append(name)


MESHES = []


def _hand_parts(boxes):
    glass_ = [b for b in boxes if b[6] in (0, 1, 3)]
    glow_ = [b for b in boxes if b[6] in (2, 4)]
    return [{'type': 'boxes', 'tones': HAND_TONES, 'glowTones': [3], 'blend': 'translucent', 'opacity': 0.5, 'shade': True, 'boxes': glass_},
            {'type': 'boxes', 'tones': HAND_TONES, 'glowTones': [2, 4], 'blend': 'additive', 'opacity': 0.75, 'shade': False, 'boxes': glow_}]


def meshes():
    # огромная раскрытая рука ладонью вниз (пальцы вперёд), запястье в начале координат; ×5 (кисть ≈ 7 бл.)
    openp = AN.hand(rot=(90, 0, 0), curl=0.25, spread=0.8, thumb=0.1)
    mesh('ereb_hand_giant_open', 'ЗАПАСНОЙ вид «Длани» для движка fx (основной — модель geo/entity/ereb_hand_giant.geo.json с текстурой '
         'ereb_hand.png ×5, см. письмо): те же кости руки ×5 (кисть ≈ 7 бл.), ладонью вниз, пальцы вперёд (+z), запястье — в точке привязки; '
         'стекло, светящаяся сердцевина, золотые швы суставов и кончики.', _hand_parts(hand_boxes(openp, 5.0, [0, 0, 0])))
    fist = AN.hand(rot=(90, 0, 0), curl=1.0, thumb=1.0)
    mesh('ereb_hand_giant_fist', '«Длань Лжи»: та же рука, сжатая в кулак (поймала игрока) — меняется с ereb_hand_giant_open на тике поимки.',
         _hand_parts(hand_boxes(fist, 5.0, [0, 0, 0])))
    # осколок маски: фарфорово-золотое стекло в золотой раме; плоскость player_face — под лицо игрока (код подставляет скин)
    P = [(-0.32, 0.42), (0.34, 0.36), (0.4, -0.2), (0.02, -0.45), (-0.36, -0.12)]
    frame = []
    for (x0, y0), (x1, y1) in zip(P, P[1:] + P[:1]):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ln = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        frame.append([round(cx - ln / 2, 3), round(cy - 0.025, 3), -0.03, round(cx + ln / 2, 3), round(cy + 0.025, 3), 0.03, 0, [0, 0, round(ang, 2)]])
    quad = [[-0.3, 0.38, 0.0], [0.34, 0.33, 0.0], [0.36, -0.18, 0.0], [-0.32, -0.12, 0.0]]
    mesh('ereb_hand_mask_shard', '«Падение маски»: осколок маски ≈0.8 бл. — рама из золота (светится), бледное стекло и плоскость player_face '
         'с отражением игрока: часть quad со slot "player_face" — код подставляет текстуру лица/скина этого игрока (как карта лица 8×8 ×N); '
         'без поддержки слота рисуется стекло. Лицом к +z; код вращает осколок (Fx.move yaw) и двигает по кругу.',
         [{'type': 'boxes', 'tones': ['#F8D260', '#FFF2B0'], 'glowTones': [0, 1], 'blend': 'additive', 'opacity': 0.95, 'shade': False, 'boxes': frame},
          {'type': 'quad', 'texture': 'ereb_hand_shard_glass', 'blend': 'translucent', 'opacity': 0.85, 'doubleSided': True, 'corners': quad},
          {'type': 'quad', 'texture': 'white', 'slot': 'player_face', 'blend': 'translucent', 'opacity': 0.8, 'doubleSided': True,
           'corners': [[-0.17, 0.2, 0.01], [0.17, 0.2, 0.01], [0.17, -0.14, 0.01], [-0.17, -0.14, 0.01]]}], formed=6, collapse=6)
    # стрелка-подсказка к своему осколку: золотой шеврон, остриём к +z
    mesh('ereb_hand_mask_arrow', '«Падение маски»: стрелка-подсказка (первые 2 с) — золотой шеврон 0.6 бл., остриём к +z; код ставит её перед '
         'игроком и поворачивает к его осколку (Fx.move yaw/pitch).',
         [{'type': 'boxes', 'tones': ['#F8D260', '#FFF2B0'], 'glowTones': [0, 1], 'blend': 'additive', 'opacity': 0.9, 'shade': False,
           'boxes': [[-0.03, -0.03, -0.25, 0.03, 0.03, 0.12, 1, [0, 0, 0]],
                     [-0.025, -0.025, -0.16, 0.025, 0.025, 0.16, 0, [0, 38, 0]], [-0.025, -0.025, -0.16, 0.025, 0.025, 0.16, 0, [0, -38, 0]]]}],
         formed=4, collapse=4)
    # зеркало «Тысячи отражений»: рама 1.6×2.8 (золото, багрянец), стекло — рисунок illusion_mirror_wall, гребень со знаком культа
    fr = [[-0.85, 0, -0.08, -0.72, 2.8, 0.08, 0], [0.72, 0, -0.08, 0.85, 2.8, 0.08, 0], [-0.85, 2.7, -0.08, 0.85, 2.85, 0.08, 0],
          [-0.85, 0, -0.08, 0.85, 0.14, 0.08, 0], [-0.95, 0, -0.12, -0.8, 0.25, 0.12, 1], [0.8, 0, -0.12, 0.95, 0.25, 0.12, 1],
          [-0.25, 2.85, -0.06, 0.25, 3.25, 0.06, 0], [-0.12, 3.25, -0.05, 0.12, 3.45, 0.05, 2]]
    mesh('ereb_hand_mirror', '«Тысяча отражений»: зеркало 1.7×3.4 бл. (рама золото, ножки багрянец, гребень с камнем), стекло — плоскость '
         'ereb_hand_shard_glass (фарфоровое стекло с бликом). Лицом к +z (к центру арены); встаёт из земли (appear rise).',
         [{'type': 'boxes', 'tones': ['#D0952A', '#7E1F2B', '#E0606A'], 'glowTones': [2], 'blend': 'translucent', 'opacity': 1.0, 'shade': True, 'boxes': fr},
          {'type': 'quad', 'texture': 'ereb_hand_shard_glass', 'blend': 'translucent', 'opacity': 0.7, 'doubleSided': True,
           'corners': [[-0.72, 2.7, 0.0], [0.72, 2.7, 0.0], [0.72, 0.14, 0.0], [-0.72, 0.14, 0.0]]}], formed=12, collapse=10)


# ================================================================== эффекты
def effects():
    M.write_json('fx/styles/ereb_hand.json', {
        'comment': 'T31 Эреб, Длань Лжи: золото и багрянец Культа, бледное бело-фиолетовое стекло призрачной руки; ложное пламя — фиолетово-'
                   'золотое стекло. Сгенерировано tools/gen_ereb_hand.py.',
        'palette': {'primary': GOLD, 'secondary': GLASS, 'core': WHITE, 'shadow': INK},
        'textures': {'sparks': 'spark_soft', 'runes': 'school_illusion_band', 'shards': 'mote_glass', 'sigil': 'illusion_seal'},
        'blend': 'additive', 'motion': {'rotationScale': 0.8, 'jitter': 0.08, 'easing': 'easeOutSine', 'pulse': {'amp': 0.08, 'period': 20}}})
    # ---------------------------------------------------------------- появление (5.5 с = анимация ereb_hand_spawn)
    fx('ereb_hand_intro', 'Появление (110 тиков = ereb_hand_spawn 5.5 с). caster = Эреб на конечной точке. 0–12: над правым плечом стягиваются '
       'стеклянные осколки и бабочки; 12 (form_hand) — из них собирается рука (модель руки видна: в анимации масштаб 0.02 → 1); '
       '12–36: рой бабочек кружит воронкой, сжимается в его силуэт (модель Эреба НЕ рисовать 0–36); 36 (form) — звон стекла, он стоит; '
       '52 поклон; 68 (salute) — блик на клинке, титр; 86 (speak) — «Вот мы и снова встретились» (ui…ereb_hand.spawn), рука раскрыта к игрокам; '
       '110 (ready) — полоса.', T_INTRO + 10, [
        E('tint', 0, 'caster', duration=T_INTRO, radius=40, color='#20142E', strength=0.24, **{'in': ease(20), 'out': ease(24, 'easeInSine')}),
        E('sigil', 2, 'caster+0,0.05,0', id='illusion_seal', until=T_INTRO, comment='печать иллюзий под ним'),
        E('decal', 4, 'caster', duration=T_INTRO, texture='cult_emblem', radius=2.2, glow=0.4, fadeOut=20, color=CRIMSON, brightness=0.6,
          comment='знак Меллисто под печатью'),
        glass(0, HAND, 40, rate=4, dur=12, spread=1.6, speed=-0.06, gravity=0.0, life=12, comment='осколки стягиваются в руку'),
        E('flash', 12, HAND, duration=8, size=1.6, rays=6, color=GLASS_HI, brightness=1.0, comment='form_hand'),
        *butterflies(6, 'caster+0,1.2,0', 120, 4, 30, spread=6.0, speed=0.02, gravity=-0.002, life=44, size=(0.34, 0.2)),
        E('vortex', 12, 'caster+0,0.1,0', duration=24, radius=2.4, height=2.6, arms=4, speed=9, pull=0.55, texture='mote_butterfly',
          particles=60, life=24, size=0.3, color=GLASS, funnel=0.35, turns=1.4, out=ease(8)),
        E('aura', 26, 'caster', target='caster', duration=12, thickness=0.09, pulse=[0.6, 4], motes=6, texture='mote_glass', color=GLASS,
          brightness=0.8, **{'in': ease(8, 'easeInCubic'), 'out': ease(4)}),
        E('flash', 36, 'caster+0,1.1,0', duration=10, size=2.6, rays=8, color=WHITE, brightness=1.2, comment='form'),
        E('wave', 36, 'caster+0,1,0', duration=12, shape='sphere', radius=2.4, rim=1.0, color='@secondary', brightness=0.7),
        glass(36, 'caster+0,1.1,0', 30, spread=1.1, speed=0.14, gravity=0.012, life=22),
        *butterflies(36, 'caster+0,1.1,0', 24, 24, 2, spread=0.8, speed=0.11, gravity=-0.006, life=34),
        E('wave', 38, 'caster+0,0.05,0', duration=18, shape='ring', radius=8, color='@primary', brightness=0.5),
        E('flash', 68, 'caster+0.35,2.3,0.25', duration=7, size=0.5, rays=4, anamorphic=1.4, color=GOLD_HI, comment='salute: блик на клинке'),
        E('flash', 86, 'caster+0.6,1.9,0.5', duration=10, size=0.8, rays=6, color=GLASS_HI, brightness=0.8, comment='speak: рука раскрыта'),
    ])
    # ---------------------------------------------------------------- бой рукой
    fx('ereb_hand_slam', 'Удар рукой по площади (анимация ereb_hand_slam, событие slam 0.8 с): caster = Эреб, слать на slam. Ладонь бьёт о землю '
       '≈0.9 бл. вперёд и 0.6 бл. вправо: трещины стекла r2.5, кольцо r5 (зона урона — код, рекомендую r3.5 от точки удара), осколки и искры.', 40, [
        E('flash', 0, SLAM, duration=8, size=3.0, rays=8, color=WHITE, brightness=1.2),
        E('decal', 0, SLAM, duration=40, texture='higher_cracks', radius=2.5, grow=4, glow=0.5, fadeOut=30, color=GLASS, brightness=0.9),
        E('wave', 0, SLAM, duration=14, shape='ring', radius=5.0, color='@secondary', brightness=0.8),
        E('wave', 2, SLAM, duration=16, shape='ring', radius=3.5, color='@primary', brightness=0.6),
        glass(0, SLAM, 34, spread=1.6, speed=0.2, gravity=0.03, life=20, size=(0.22, 0.06)),
        sparks(0, SLAM, 16, spread=1.0, speed=0.16),
    ])
    fx('ereb_hand_grab', 'Хватка (ereb_hand_grab, событие grab 0.6 с; добивание — тот же fx на grab): caster = Эреб. Пальцы смыкаются у жертвы: '
       'звон стекла у ладони, золотые искры. Схваченного ставить в точку удержания (письмо).', 14, [
        E('flash', 0, PALM_HOLD, duration=6, size=1.2, rays=6, color=GLASS_HI, brightness=1.0),
        glass(0, PALM_HOLD, 12, spread=0.6, speed=0.1, gravity=0.01, life=12),
        sparks(0, PALM_HOLD, 8),
    ])
    fx('ereb_hand_hold', 'Удержание (петля, пока игрок в руке; duration −1 — остановить при отпускании): caster = схваченный игрок, follow. '
       'По нему едва бежит стеклянная корка, с руки сыплются блёстки — союзникам видно, кого спасать.', -1, [
        E('aura', 0, 'caster', target='caster', follow=True, duration=100000, thickness=0.05, pulse=[0.5, 12], motes=4, texture='mote_glass', ring=False,
          color=GLASS, brightness=0.5),
        glass(0, 'caster+0,1.6,0', 4, rate=0.2, dur=100000, spread=0.5, speed=0.0, gravity=0.01, life=16, follow=True, size=(0.12, 0.04)),
    ])
    fx('ereb_hand_squeeze', 'Сжатие (ereb_hand_squeeze, событие squeeze 0.35 с; добивание — squeeze 1.5 с): caster = схваченный игрок. Хруст стекла: '
       'трещины-печать на нём, багряно-золотые искры.', 16, [
        E('sigil', 0, 'caster+0,1.0,0', id='illusion_mirror_crack', scale=0.3, until=14, follow=True),
        E('flash', 0, 'caster+0,1.0,0', duration=6, size=1.0, rays=4, color=CRIMSON_HI, brightness=1.0),
        sparks(0, 'caster+0,1.0,0', 14, color=CRIMSON_HI, spread=0.5, speed=0.14),
        glass(0, 'caster+0,1.0,0', 10, spread=0.5, speed=0.12, gravity=0.02, life=14),
    ])
    fx('ereb_hand_release', 'Отпустить (ereb_hand_grab_release, событие release 0.2 с): caster = отпущенный игрок. Корка лопается, стекло осыпается.', 14, [
        glass(0, 'caster+0,1.0,0', 18, spread=0.6, speed=0.1, gravity=0.02, life=14),
        E('flash', 0, 'caster+0,1.0,0', duration=5, size=1.0, color=GLASS_HI, brightness=0.8),
    ])
    fx('ereb_hand_cast', 'Каст (ereb_hand_cast, событие cast 0.75 с — щелчок «Длани»): caster = Эреб. Блик стекла и кольцо-рябь над поднятой '
       'перчаткой, рука над плечом вспыхивает золотыми швами.', 22, [
        E('flash', 14, GAUNT, duration=8, size=0.8, rays=6, color=GLASS_HI, brightness=1.1),
        E('wave', 15, GAUNT, duration=10, shape='sphere', radius=0.9, rim=1.0, color='@secondary', brightness=0.6),
        E('flash', 15, HAND, duration=8, size=1.4, rays=4, color=GOLD_HI, brightness=0.7),
        sparks(15, HAND, 8, color=GOLD_HI, spread=0.6, speed=0.05),
    ])
    # ---------------------------------------------------------------- фазы
    fx('ereb_hand_phase2', 'Фаза 2 «Длань» (66%, ereb_hand_phase2, событие phase 0.8 с = 16 тик): caster = Эреб. Кулак руки бьёт в землю справа-впереди: '
       'трещины, кольцо r12, стекло в воздухе.', 46, [
        E('flash', 16, 'caster+0.3,0.3,1.0', duration=8, size=2.4, rays=8, color=WHITE, brightness=1.1),
        E('decal', 16, 'caster+0.3,0,1.0', duration=40, texture='higher_cracks', radius=2.0, grow=3, glow=0.4, fadeOut=30, color=GLASS),
        E('wave', 16, 'caster+0,0.05,0', duration=22, shape='ring', radius=12, color='@primary', brightness=0.5),
        E('sigil', 10, 'caster+0,1.2,0', id='illusion_mirror_crack', until=34),
        glass(16, 'caster+0,2.2,0', 40, rate=10, dur=6, spread=2.0, speed=0.04, gravity=0.02, life=30),
    ])
    fx('ereb_hand_phase3', 'Фаза 3 «Глава Культа» (33%, ereb_hand_phase3, событие crack 0.9 с = 18 тик): caster = Эреб. «Длань» у маски, '
       'маска трескается (на 18 код меняет текстуру на ereb_hand_cracked): рябь у лица, золотые трещины, мир на 2 с тускнеет, '
       'по краям — вспышка багрянца.', 50, [
        E('sigil', 12, FACE, id='illusion_face_ripple', until=30, follow=True),
        E('flash', 18, FACE, duration=8, size=1.0, rays=6, color=GOLD_HI, brightness=1.2, follow=True),
        sparks(18, FACE, 14, color=GOLD_HI, spread=0.25, speed=0.08),
        glass(18, FACE, 10, spread=0.2, speed=0.06, gravity=0.02, life=16),
        E('tint', 18, 'caster', duration=40, radius=32, color='#1A0A14', strength=0.35, **{'in': ease(6), 'out': ease(20)}),
        E('wave', 18, 'caster+0,0.05,0', duration=20, shape='ring', radius=12, color=CRIMSON, brightness=0.5),
    ])
    # ---------------------------------------------------------------- «Длань Лжи» (66%, особая)
    fx('ereb_hand_of_lies_sky', '«Длань Лжи», рука с неба (60 тиков): caster = ТОЧКА пойманного игрока (не follow). На ereb_hand_hand_of_lies descend '
       '(1.2 с). 0–24: на земле растёт тень ладони, сверху сквозь облака опускается огромная раскрытая рука (меш ereb_hand_giant_open ×1.0 = 7 бл., '
       'с +26 бл. до +3); 24 — ловит: меш меняется на кулак (ereb_hand_giant_fist), звон, вспышка; 24–56 держит и поднимается на +5, '
       '56 — тает. Сам игрок — в кулаке (код поднимает его на 2.5 бл. на 6 с и включает ложную арену ereb_hand_false_arena).', 64, [
        E('decal', 0, 'caster', duration=30, texture='illusion_seal', radius=4.0, grow=24, glow=0.2, fadeOut=8, color=GLASS, brightness=0.5,
          comment='тень ладони'),
        E('mesh', 0, 'caster+0,3,-1.8', model='ereb_hand_giant_open', scale=1.0, until=24,
          move={'from': [0, 23, 0], 'scaleFrom': 0.6, 'delay': 0, 'duration': 24, 'easing': 'easeInCubic'}),
        E('mesh', 24, 'caster+0,3,-1.8', model='ereb_hand_giant_fist', scale=1.0, until=58,
          move={'keys': [[0, [0, 0, 0], 'linear'], [32, [0, 5, 0], 'easeInOutSine']]}),
        E('flash', 24, 'caster+0,1.5,0', duration=10, size=3.0, rays=8, color=WHITE, brightness=1.3),
        E('wave', 24, 'caster+0,0.05,0', duration=16, shape='ring', radius=7, color='@secondary', brightness=0.7),
        glass(24, 'caster+0,2,0', 30, spread=2.0, speed=0.12, gravity=0.02, life=24),
        *butterflies(56, 'caster+0,6,0', 30, 30, 2, spread=2.0, speed=0.08, gravity=-0.01, life=40),
    ])
    fx('ereb_hand_false_arena', '«Длань Лжи», ложная арена (6 с = 120 тиков): caster = пойманный игрок, follow; слать ТОЛЬКО ему. Мир в фиолетовом '
       'стекле, по краю зрения трещины зеркала, мерцание; союзники в это время рисуются кодом как враги (по ТЗ). В конце — звон и мир «бьётся».', 124, [
        E('tint', 0, 'caster', duration=120, radius=64, color='#3A2A66', strength=0.4, **{'in': ease(10), 'out': ease(10)}),
        E('sprites', 0, 'caster+0,1.5,0', duration=120, texture='mote_glass', count=80, rate=0.7, spread=8, speed=0.0, gravity=-0.002,
          size=[0.16, 0.05], life=40, color=GLASS_HI, follow=True, wrap=8),
        E('sigil', 0, 'caster.eyes+0,0,1.2', id='illusion_mirror_crack', scale=0.8, until=118, follow=True, comment='трещины перед глазами'),
        E('flash', 116, 'caster.eyes+0,0,1', duration=8, size=3.0, rays=8, color=WHITE, brightness=1.0, screen=0.5, follow=True),
        glass(116, 'caster+0,1.6,0', 30, spread=1.5, speed=0.15, gravity=0.02, life=20),
    ])
    # ---------------------------------------------------------------- «Падение маски» (45%)
    fx('ereb_hand_mask_tear', '«Падение маски», срыв (44 тика = ereb_hand_mask_fall 2.2 с): caster = Эреб. 10 (grip) — блик у лица; 17 (tear) — '
       'золотые искры, маска отрывается; 22 (shatter) — над ним маска лопается: вспышка, осколки разлетаются по арене (сами осколки — '
       'ereb_hand_mask_shard на каждом игроке), бабочки. Титр «Падение маски».', 46, [
        E('flash', 10, FACE, duration=6, size=0.6, rays=4, color=GLASS_HI, follow=True),
        sparks(17, FACE, 14, color=GOLD_HI, spread=0.2, speed=0.1),
        E('flash', 22, 'caster-0.2,2.8,0.6', duration=10, size=3.2, rays=8, color=WHITE, brightness=1.3),
        E('wave', 22, 'caster-0.2,2.8,0.6', duration=12, shape='sphere', radius=3.0, rim=1.0, color='@secondary', brightness=0.6),
        glass(22, 'caster-0.2,2.8,0.6', 40, spread=0.6, speed=0.25, gravity=0.0, life=26, size=(0.3, 0.1)),
        *butterflies(22, 'caster-0.2,2.8,0.6', 12, 12, 2, spread=0.4, speed=0.1, gravity=-0.01, life=30),
        E('wave', 24, 'caster+0,0.05,0', duration=20, shape='ring', radius=14, color='@primary', brightness=0.5),
    ])
    fx('ereb_hand_mask_shard', '«Падение маски», осколок одного игрока (duration −1; 8 с — код стопит): caster = точка осколка (Fx.move — кружит по '
       'арене на 1.5–3 бл., медленно, yaw — к своему игроку). Меш ereb_hand_mask_shard (slot player_face = лицо игрока; ник над осколком — код/'
       'текст), мягкий ореол и блёстки. Видят все.', -1, [
        E('mesh', 0, 'caster', model='ereb_hand_mask_shard', scale=1.0, follow=True, until=100000),
        E('sprites', 0, 'caster', duration=100000, texture='glow', count=1, rate=0.05, spread=0, speed=0, size=[1.3, 1.2], life=40, color=GLASS,
          brightness=0.35, follow=True),
        glass(0, 'caster', 2, rate=0.15, dur=100000, spread=0.4, speed=0.0, gravity=0.004, life=16, follow=True, size=(0.1, 0.03)),
    ])
    fx('ereb_hand_mask_arrow', '«Падение маски», стрелка-подсказка (40 тиков = первые 2 с): caster = игрок, follow; слать ТОЛЬКО ему. Меш '
       'ereb_hand_mask_arrow в 1.2 бл. перед ним на высоте груди; код поворачивает его к своему осколку (Fx.move yaw/pitch). Пульсирует.', 40, [
        E('mesh', 0, 'caster+0,1.2,1.2', model='ereb_hand_mask_arrow', scale=1.0, follow=True, until=40),
        E('sprites', 0, 'caster+0,1.2,1.2', duration=40, texture='glow', count=1, rate=0.1, spread=0, speed=0, size=[0.5, 0.4], life=10,
          color=GOLD_HI, follow=True),
    ])
    fx('ereb_hand_mask_shard_ring', '«Падение маски», удар по ЧУЖОМУ осколку (10 тиков): caster = осколок. Только звенит: рябь и блик, не бьётся.', 10, [
        E('wave', 0, 'caster', duration=8, shape='sphere', radius=0.7, rim=1.0, color='@secondary', brightness=0.7),
        E('flash', 0, 'caster', duration=5, size=0.7, rays=4, color=GLASS_HI, brightness=0.9),
    ])
    fx('ereb_hand_mask_shard_break', '«Падение маски», свой осколок разбит (24 тика): caster = осколок. Вспышка, осколки и пара бабочек; меш убрать.', 24, [
        E('flash', 0, 'caster', duration=8, size=1.4, rays=6, color=WHITE, brightness=1.2),
        glass(0, 'caster', 22, spread=0.4, speed=0.16, gravity=0.02, life=18),
        *butterflies(0, 'caster', 4, 4, 1, spread=0.3, speed=0.06, gravity=-0.01, life=24),
    ])
    fx('ereb_hand_mask_shard_burst', '«Падение маски», осколок НЕ разбит за 8 с (30 тиков): caster = его игрок. Осколок влетает в игрока и взрывается: '
       'багряно-золотая вспышка, кольцо, стекло (урон — код).', 30, [
        E('flash', 0, 'caster+0,1,0', duration=10, size=2.4, rays=8, color=CRIMSON_HI, brightness=1.3, screen=0.25),
        E('wave', 0, 'caster+0,1,0', duration=12, shape='sphere', radius=2.0, rim=1.0, color=CRIMSON, brightness=0.8),
        E('wave', 0, 'caster+0,0.05,0', duration=14, shape='ring', radius=3.0, color='@primary', brightness=0.7),
        glass(0, 'caster+0,1,0', 30, spread=0.5, speed=0.22, gravity=0.02, life=20),
        sparks(0, 'caster+0,1,0', 18, color=CRIMSON_HI, spread=0.6, speed=0.18),
    ])
    fx('ereb_hand_mask_return', '«Падение маски», сборка маски (28 тиков = ereb_hand_mask_return 1.4 с): caster = Эреб. Уцелевшие осколки слетаются '
       'к лицу (сходящееся стекло), на 14 (mend) — вспышка: код показывает кость mask и ставит текстуру ereb_hand_mended.', 28, [
        glass(0, FACE, 30, rate=2, dur=14, spread=3.0, speed=-0.2, gravity=0.0, life=14, follow=True),
        E('flash', 14, FACE, duration=8, size=1.0, rays=6, color=GOLD_HI, brightness=1.1, follow=True),
        sparks(14, FACE, 10, color=GOLD_HI, spread=0.2, speed=0.05),
    ])
    # ---------------------------------------------------------------- +4 заклинания
    fx('ereb_hand_false_flame_mark', '«Ложное пламя», метка круга (20 тиков = 1 с предупреждения; слать на ereb_hand_false_flame marks 0.6 в каждом из '
       '5 кругов, и настоящих, и обманок — одинаково): caster = центр круга r2. Кольцо фиолетового стекла разгорается.', 20, [
        E('decal', 0, 'caster', duration=22, texture='ereb_hand_flame_ring', radius=2.0, grow=10, glow=0.3, color=FLAME, brightness=0.5),
        E('wave', 0, 'caster+0,0.05,0', duration=20, shape='ring', radius=2.0, color=FLAME, brightness=0.5),
    ])
    for real in (True, False):
        nm = 'ereb_hand_false_flame_' + ('real' if real else 'decoy')
        els = [E('decal', 0, 'caster', duration=60, texture='ereb_hand_flame_ring', radius=2.0, glow=0.5, fadeOut=14, color=FLAME, brightness=0.9,
                 pulse=12),
               E('curtain', 0, 'caster', duration=60, count=22, radius=[0.4, 1.9], height=[0.8, 1.8], grow=6, width=[0.25, 0.45], brightness=[0.6, 1.0],
                 texture='cult_flame_tongue', flicker=0.4, color=FLAME, **{'out': ease(12)}),
               E('sprites', 0, 'caster+0,0.3,0', duration=58, texture='mote_glass', count=40, rate=0.8, area=1.9, speed=0.02, gravity=-0.02,
                 size=[0.14, 0.04], life=20, color=FLAME_HI),
               E('sprites', 0, 'caster+0,0.3,0', duration=58, texture='spark_soft', count=30, rate=0.6, area=1.8, speed=0.02, gravity=-0.03,
                 size=[0.1, 0.02], life=16, color=GOLD_HI)]
        if real:
            els.append(E('decal', 0, 'caster', duration=60, texture='ereb_hand_flame_rim', radius=2.05, glow=0.15, fadeOut=14, color=GOLD, brightness=0.35,
                         comment='подсказка: еле заметная золотая кромка — только у настоящих'))
        fx(nm, '«Ложное пламя», ' + ('НАСТОЯЩИЙ круг (жжёт; урон — код)' if real else 'ОБМАНКА (не жжёт)') +
           ' (60 тиков = 3 с горения): caster = центр круга r2. Фиолетово-стеклянное пламя: языки (curtain), кольцо, искры стекла и золота. '
           + ('Отличие от обманки — тонкая золотая кромка с насечками по краю (ereb_hand_flame_rim, яркость 0.35).' if real else
              'Выглядит как настоящий, но без золотой кромки.'), 62, els)
    fx('ereb_hand_glass_grip_warn', '«Стеклянная хватка», предупреждение (20 тиков = 1 с; ereb_hand_glass_grip warn 0.0): caster = Эреб (не follow). '
       'Конус 70° на 6 бл. вперёд (ereb_hand_grip_cone, вершина у его ног), заполняется стеклом, по краю — золото.', 22, [
        E('decal', 0, 'caster+0,0,3', duration=22, texture='ereb_hand_grip_cone', radius=6.0, grow=14, glow=0.3, color=GLASS, brightness=0.7,
          rotation=0, comment='вершина конуса — у его ног (центр картинки), раскрыт вперёд; radius 6 → картинка 12×12 со смещением'),
        E('sprites', 0, 'caster+0,0.2,3', duration=20, texture='mote_glass', count=24, rate=1.2, area=2.5, speed=0.0, gravity=-0.004,
          size=[0.14, 0.05], life=14, color=GLASS_HI),
    ])
    fx('ereb_hand_glass_grip', '«Стеклянная хватка», удар (ereb_hand_glass_grip, событие grip 1.0 с): caster = Эреб. Рука сжимает область перед ним: '
       'стекло стягивается к кулаку (≈2 бл. вперёд), вспышка, кольцо сходится (урон и притяжение — код).', 24, [
        glass(0, 'caster+0.5,1.2,2.0', 34, spread=3.0, speed=-0.25, gravity=0.0, life=12, size=(0.22, 0.06)),
        E('flash', 4, 'caster+0.5,1.2,2.0', duration=8, size=2.2, rays=8, color=WHITE, brightness=1.2),
        E('wave', 0, 'caster+0,0.05,3', duration=10, shape='ring', radius=4.0, color='@secondary', brightness=0.7, reverse=True),
        sparks(4, 'caster+0.5,1.2,2.0', 14, color=GOLD_HI, spread=0.6, speed=0.14),
    ])
    fx('ereb_hand_oath_mark', '«Чужая клятва», метка (80 тиков = 4 с; ereb_hand_foreign_oath mark 0.6): caster = игрок с клятвой, follow. Над головой — '
       'знак двух колец с оком (багрянец), по телу — тонкая оболочка. Связь с союзником — только его меткой (ereb_hand_oath_bound), без нити.', 82, [
        E('sprites', 0, 'caster+0,2.5,0', duration=80, texture='ereb_hand_oath_mark', count=1, rate=0.03, spread=0, speed=0, size=[0.9, 0.9], life=80,
          color=CRIMSON_HI, glow=0.4, follow=True),
        E('aura', 0, 'caster', target='caster', follow=True, duration=80, thickness=0.05, pulse=[0.5, 10], motes=4, texture='spark_soft', ring=True,
          color=CRIMSON, brightness=0.6),
        E('flash', 0, 'caster+0,2.5,0', duration=8, size=1.2, rays=6, color=CRIMSON_HI, follow=True),
    ])
    fx('ereb_hand_oath_bound', '«Чужая клятва», союзник, на которого отражается урон (80 тиков): caster = ближайший союзник, follow. Тот же знак, '
       'меньше и стеклянный (кто из двоих «платит» — видно).', 82, [
        E('sprites', 0, 'caster+0,2.4,0', duration=80, texture='ereb_hand_oath_mark', count=1, rate=0.03, spread=0, speed=0, size=[0.6, 0.6], life=80,
          color=GLASS_HI, glow=0.3, follow=True),
        E('aura', 0, 'caster', target='caster', follow=True, duration=80, thickness=0.04, pulse=[0.4, 10], motes=2, ring=False, color=GLASS,
          brightness=0.4),
    ])
    fx('ereb_hand_oath_reflect', '«Чужая клятва», отражённый урон (10 тиков; каждый раз): caster = союзник, получивший половину. Багровая вспышка, '
       'стекло трескается.', 10, [
        E('flash', 0, 'caster+0,1.2,0', duration=6, size=1.0, rays=4, color=CRIMSON_HI, brightness=1.0),
        glass(0, 'caster+0,1.2,0', 8, spread=0.4, speed=0.1, gravity=0.02, life=10),
    ])
    fx('ereb_hand_mirror', '«Тысяча отражений», зеркало (duration −1; встаёт на mirrors 0.6 с ereb_hand_thousand_reflections, код стопит в конце): '
       'caster = точка зеркала на краю арены, yaw — к центру. Меш ereb_hand_mirror встаёт из земли, по стеклу бегут блики.', -1, [
        E('mesh', 0, 'caster', model='ereb_hand_mirror', scale=1.0, appear='rise', until=100000),
        E('decal', 0, 'caster', duration=100000, texture='illusion_seal', radius=1.2, glow=0.2, color=GLASS, brightness=0.4),
        E('sprites', 0, 'caster+0,1.4,0.1', duration=100000, texture='glint4', count=1, rate=0.08, spread=0.6, speed=0, size=[0.4, 0.1], life=12,
          color=WHITE),
    ])
    fx('ereb_hand_mirror_strike_real', '«Тысяча отражений», НАСТОЯЩИЙ удар из зеркала (24 тика): caster = зеркало, target = игрок. Стекло зеркала '
       'идёт рябью, из него выглядывает Эреб (код: сущность-отражение — модель ereb_hand полупрозрачно, анимация ereb_hand_reflection_strike, '
       'hit на 9 тике); на hit — золотой блик у цели. Без линии до цели.', 24, [
        E('wave', 0, 'caster+0,1.4,0.1', duration=10, shape='sphere', radius=1.2, rim=1.0, color='@secondary', brightness=0.7),
        E('flash', 0, 'caster+0,1.4,0.2', duration=6, size=1.4, rays=6, color=GLASS_HI),
        E('flash', 9, 'target+0,1.3,0', duration=6, size=0.6, rays=4, anamorphic=1.2, color=GOLD_HI, brightness=1.2),
        sparks(9, 'target+0,1.3,0', 8),
    ])
    fx('ereb_hand_mirror_strike_fake', '«Тысяча отражений», ложный удар (14 тиков): caster = зеркало. Лишь едва заметный стеклянный блик в стекле — '
       'отражение «замахнулось», но удара нет.', 14, [
        E('flash', 0, 'caster+0,1.6,0.2', duration=6, size=0.6, rays=4, color=GLASS_HI, brightness=0.5),
        E('wave', 0, 'caster+0,1.4,0.1', duration=8, shape='sphere', radius=0.8, rim=1.0, color='@secondary', brightness=0.3),
    ])
    fx('ereb_hand_mirror_break', '«Тысяча отражений», зеркало бьётся в конце (20 тиков): caster = зеркало. Вспышка, осколки.', 20, [
        E('flash', 0, 'caster+0,1.4,0', duration=6, size=1.8, rays=6, color=WHITE),
        glass(0, 'caster+0,1.4,0', 26, spread=0.8, speed=0.14, gravity=0.03, life=18, size=(0.22, 0.06)),
    ])
    # ---------------------------------------------------------------- «Сон Бабочки: Полное Раскрытие» (20%)
    fx('ereb_hand_full_reveal_cast', '«Сон Бабочки: Полное Раскрытие», каст (80 тиков = ereb_hand_full_reveal 4.0 с): caster = Эреб. 16 (butterflies) — '
       'вокруг него поднимается рой бабочек; 28 (open) — рука над головой раскрывается, на ладони свет; 52 (cast) — белая вспышка на весь экран '
       '(screen 0.9), мир «раскрывается» — код начинает заклинание (мир сна ereb_hand_dream_world, игроки во сне). Титр «Сон Бабочки: Полное Раскрытие».', 84, [
        E('tint', 0, 'caster', duration=60, radius=48, color='#2A1E44', strength=0.3, **{'in': ease(16), 'out': ease(6)}),
        *butterflies(16, 'caster+0,1.0,0', 80, 6, 36, spread=3.0, speed=0.04, gravity=-0.02, life=40),
        E('vortex', 16, 'caster+0,0.2,0', duration=36, radius=3.2, height=4.0, arms=5, speed=10, pull=0.3, texture='mote_butterfly',
          particles=70, life=26, size=0.3, color=GLASS),
        E('flash', 28, 'caster+0.7,3.4,0.2', duration=24, size=1.6, rays=8, color=GLASS_HI, brightness=0.9, comment='свет на раскрытой ладони'),
        E('flash', 52, 'caster+0,2,0', duration=16, size=8.0, rays=12, color=WHITE, brightness=1.5, screen=0.9),
        E('wave', 52, 'caster+0,1,0', duration=24, shape='sphere', radius=20, rim=1.0, color='@secondary', brightness=0.7),
        E('wave', 52, 'caster+0,0.05,0', duration=30, shape='ring', radius=32, color='@primary', brightness=0.6),
    ])
    fx('ereb_hand_dream_world', '«Полное Раскрытие», мир сна (duration −1 — до конца боя; caster = центр арены, не follow; слать игрокам во сне). '
       'Раскрытый зеркальный мир: пол — зеркальные плиты r30 (ereb_hand_mirror_floor, медленно вращается), небо — тусклый фиолетовый тон, '
       'над ареной на +22 бл. висит огромная Длань (меш ereb_hand_giant_open ×1.6 ≈ 11 бл.), медленно покачивается; в воздухе — поле '
       'стеклянной пыльцы и бабочек. Мобов нет (как T22). Удары Длани по площади — ereb_hand_dream_slam_warn → ereb_hand_dream_slam.', -1, [
        E('tint', 0, 'caster', duration=100000, radius=64, color='#2E2450', strength=0.32, **{'in': ease(20)}),
        E('decal', 0, 'caster', duration=100000, texture='ereb_hand_mirror_floor', radius=30, grow=20, glow=0.35, spin=0.05, color=GLASS, brightness=0.6,
          lift=0.02),
        E('mesh', 0, 'caster+0,22,0', model='ereb_hand_giant_open', scale=1.6, until=100000,
          move={'from': [0, 20, 0], 'scaleFrom': 0.3, 'delay': 0, 'duration': 40, 'easing': 'easeOutCubic',
                'keys': [[40, [0, 0, 0], 'easeInOutSine'], [140, [0, 1.2, 0], 'easeInOutSine'], [240, [0, 0, 0], 'easeInOutSine']]}),
        E('sprites', 0, 'caster+0,3,0', duration=100000, texture='mote_glass', count=400, rate=2, spread=26, speed=0.0, gravity=-0.002,
          size=[0.14, 0.04], life=80, color=GLASS_HI, wrap=26),
        E('sprites', 0, 'caster+0,3,0', duration=100000, texture='mote_butterfly', count=120, rate=0.6, spread=24, speed=0.02, gravity=-0.004,
          sway=0.6, size=[0.3, 0.2], life=100, color=GLASS, glow=0.4, wrap=24),
        E('curtain', 0, 'caster', duration=100000, count=48, radius=[29, 31], height=[10, 18], grow=30, width=[0.6, 1.2], brightness=[0.15, 0.35],
          texture='beam_fade', flicker=0.2, color=GLASS, comment='зеркальная стена-горизонт по краю'),
    ])
    fx('ereb_hand_dream_slam_warn', '«Полное Раскрытие», Длань бьёт (предупреждение, 30 тиков): caster = точка удара. На земле растёт тень ладони r4 '
       'и кольцо; через 30 тиков — ereb_hand_dream_slam.', 30, [
        E('decal', 0, 'caster', duration=32, texture='illusion_seal', radius=4.0, grow=26, glow=0.3, color=GLASS, brightness=0.6),
        E('wave', 0, 'caster+0,0.05,0', duration=30, shape='ring', radius=4.0, color='@primary', brightness=0.6),
    ])
    fx('ereb_hand_dream_slam', '«Полное Раскрытие», удар Длани (40 тиков): caster = точка удара. Огромная ладонь падает с высоты (меш ×1.2) и бьёт '
       'плашмя: трещины стекла r4, кольцо, осколки; рука тает (урон во сне — ненастоящий, по ТЗ).', 40, [
        E('mesh', 0, 'caster+0,1.5,-2.5', model='ereb_hand_giant_open', scale=1.2, until=24,
          move={'from': [0, 16, 0], 'delay': 0, 'duration': 6, 'easing': 'easeInCubic'}),
        E('flash', 6, 'caster+0,0.5,0', duration=8, size=4.0, rays=8, color=WHITE, brightness=1.2),
        E('decal', 6, 'caster', duration=34, texture='higher_cracks', radius=4.0, grow=4, glow=0.5, fadeOut=24, color=GLASS),
        E('wave', 6, 'caster+0,0.05,0', duration=14, shape='ring', radius=7.0, color='@secondary', brightness=0.8),
        glass(6, 'caster+0,0.5,0', 40, spread=2.5, speed=0.2, gravity=0.03, life=22, size=(0.24, 0.06)),
        *butterflies(20, 'caster+0,2,0', 16, 16, 2, spread=2.0, speed=0.06, gravity=-0.01, life=30),
    ])
    # ---------------------------------------------------------------- ложная смерть
    hb = 'caster+0.97,2.0,-0.3'
    fx('ereb_hand_false_death', 'Ложная смерть (100 тиков = ereb_hand_false_death 5.0 с): caster = Эреб (не follow). 8 (stagger) — блик; 14 (hand_break) — '
       'призрачная рука трескается и осыпается стеклом; 32 (speak) — «А вы...стали сильнее» (ui…ereb_hand.defeat: чат r48 + субтитр); '
       '52 (smile) — лёгкий поклон; 76 (vanish) — он распадается на множество бабочек: оболочка, вспышка, рой (модель скрыть на 78), '
       'бабочки улетают вверх и в стороны; сон рассыпается (код: игроки просыпаются, полоса исчезает).', 104, [
        E('flash', 8, 'caster+0,1.4,0', duration=5, size=1.0, rays=4, color=GLASS_HI),
        E('flash', 14, hb, duration=8, size=2.0, rays=6, color=GLASS_HI, brightness=1.1),
        glass(14, hb, 40, spread=0.9, speed=0.1, gravity=0.03, life=26, size=(0.24, 0.06)),
        sparks(14, hb, 12, color=GOLD_HI, spread=0.6, speed=0.08),
        E('aura', 70, 'caster', target='caster', duration=10, thickness=0.08, pulse=[0.6, 3], motes=6, texture='mote_butterfly', color=GLASS,
          brightness=0.8, **{'in': ease(4), 'out': ease(4)}),
        E('flash', 76, 'caster+0,1.1,0', duration=10, size=2.6, rays=8, color=WHITE, brightness=1.1),
        *butterflies(76, 'caster+0,1.0,0', 90, 45, 4, spread=0.5, speed=0.12, gravity=-0.02, life=60, size=(0.36, 0.16)),
        E('vortex', 78, 'caster+0,0.5,0', duration=24, radius=2.2, height=4.0, arms=4, speed=-8, pull=-0.4, texture='mote_butterfly', particles=40,
          life=24, size=0.32, color=GLASS),
    ])
    # ---------------------------------------------------------------- добивание
    fx('ereb_hand_finisher', 'Добивание (72 тика = ereb_hand_finisher 3.6 с): caster = Эреб на месте (не follow), target = жертва (код держит её в ладони: '
       'точка удержания). 12 (grab) — звон у ладони; 12–30 поднимает; 30 (squeeze) — хруст, по жертве бежит стеклянная корка; 42 (shatter) — жертва '
       'трескается и рассыпается стеклом и бабочками (код прячет её, смерть ereb_hand_finisher); 48 (release) — ладонь раскрывается, '
       'остатки стекла осыпаются.', 76, [
        E('flash', 12, 'target+0,1,0', duration=6, size=1.2, rays=6, color=GLASS_HI, brightness=1.0),
        glass(12, 'target+0,1,0', 12, spread=0.6, speed=0.1, gravity=0.01, life=12),
        E('aura', 30, 'target', target='target', follow=True, duration=12, thickness=0.09, pulse=[0.8, 3], motes=8, texture='mote_glass', color=GLASS_HI,
          brightness=0.9, **{'in': ease(8), 'out': ease(3)}),
        E('sigil', 30, 'target+0,1,0', id='illusion_mirror_crack', scale=0.35, until=42, follow=True),
        sparks(30, 'target+0,1,0', 14, color=CRIMSON_HI, spread=0.5, speed=0.14),
        E('flash', 42, 'target+0,1,0', duration=10, size=2.4, rays=8, color=WHITE, brightness=1.3),
        glass(42, 'target+0,1,0', 50, spread=0.6, speed=0.18, gravity=0.03, life=26, size=(0.26, 0.08)),
        *butterflies(42, 'target+0,1.2,0', 20, 20, 2, spread=0.5, speed=0.1, gravity=-0.012, life=40),
        glass(48, 'target+0,1.4,0', 16, spread=0.8, speed=0.04, gravity=0.03, life=20),
    ])


# ================================================================== вторая партия (владелец 20.11): +4 заклинания и «Ложный рассвет»
def effects2():
    G_WIND, G_THROW = 'caster-0.4,2.45,0.05', 'caster-0.1,1.35,0.7'          # «Длань» в замахе над головой / в броске (FK)
    # ---------------------------------------------------------------- «Пламя-подменыш»
    fx('ereb_hand_changeling_flame', '«Пламя-подменыш», каст (32 тика = ereb_hand_changeling_flame 1.6 с): caster = Эреб. 4 (charge) — в поднятой '
       '«Длани» собирается фиолетово-золотой огненный шар; 13 (throw) — бросок: вспышка у «Длани», снаряд летит (сам шар — '
       'ereb_hand_changeling_flame_orb на снаряде).', 32, [
        E('flash', 4, G_WIND, duration=9, size=0.9, rays=6, color=FLAME_HI, brightness=0.9, follow=True),
        E('vortex', 4, G_WIND, duration=9, radius=0.7, height=0, arms=3, speed=18, pull=0.6, texture='spark_soft', particles=18, life=8, size=0.12,
          color=FLAME, follow=True),
        E('sprites', 4, G_WIND, duration=9, texture='cult_flame_tongue', count=10, rate=1.2, spread=0.15, speed=0.01, gravity=-0.02,
          size=[0.4, 0.15], life=8, color=FLAME, glow=0.4, follow=True),
        E('flash', 13, G_THROW, duration=6, size=1.2, rays=6, anamorphic=1.0, color=FLAME_HI, brightness=1.1),
        sparks(13, G_THROW, 10, color=GOLD_HI, spread=0.3, speed=0.12),
    ])
    fx('ereb_hand_changeling_flame_orb', '«Пламя-подменыш», огненный шар (duration −1, код стопит на подмене): caster = снаряд, follow. Фиолетовое '
       'пламя со стеклянными искрами, золотое ядро, след.', -1, [
        E('sprites', 0, 'caster', duration=100000, texture='glow', count=1, rate=0.2, spread=0, speed=0, size=[0.9, 0.9], life=6, color=FLAME,
          glow=0.6, follow=True),
        E('sprites', 0, 'caster', duration=100000, texture='cult_flame_tongue', count=600, rate=2, spread=0.25, speed=0.01, gravity=-0.03,
          size=[0.45, 0.1], life=7, color=FLAME_HI),
        E('trail', 0, 'caster', duration=100000, width=0.35, length=8, fade=1.0, color=FLAME, follow=True),
        E('sprites', 0, 'caster', duration=100000, texture='spark_soft', count=300, rate=1, spread=0.2, speed=0.02, gravity=0.01,
          size=[0.1, 0.02], life=8, color=GOLD_HI),
    ])
    fx('ereb_hand_changeling_flame_warn', '«Пламя-подменыш», ПОДСКАЗКА (10 тиков = 0.5 с до подмены): caster = снаряд, follow. Шар мерцает золотом '
       '(3 вспышки), по краю — золотые искры.', 10, [
        E('flash', 0, 'caster', duration=3, size=1.1, rays=4, color=GOLD_HI, brightness=1.1, follow=True),
        E('flash', 4, 'caster', duration=3, size=1.1, rays=4, color=GOLD_HI, brightness=1.1, follow=True),
        E('flash', 8, 'caster', duration=2, size=1.2, rays=4, color=GOLD_HI, brightness=1.2, follow=True),
        sparks(0, 'caster', 8, color=GOLD_HI, spread=0.3, speed=0.06, follow=True),
    ])
    fx('ereb_hand_changeling_flame_swap', '«Пламя-подменыш», подмена на полпути (12 тиков): caster = точка подмены. Пламя схлопывается в стекло: '
       'кольцо-рябь, осколки, пара бабочек — дальше летит бабочка (ereb_hand_changeling_flame_butterfly) к союзнику цели.', 12, [
        E('flash', 0, 'caster', duration=5, size=1.4, rays=6, color=GLASS_HI, brightness=1.1),
        E('wave', 0, 'caster', duration=8, shape='sphere', radius=1.0, rim=1.0, color='@secondary', brightness=0.7),
        glass(0, 'caster', 14, spread=0.4, speed=0.1, gravity=0.02, life=12),
        *butterflies(0, 'caster', 3, 3, 1, spread=0.3, speed=0.06, life=16),
    ])
    fx('ereb_hand_changeling_flame_butterfly', '«Пламя-подменыш», стеклянная бабочка-снаряд (duration −1, код стопит при попадании): caster = снаряд, '
       'follow. Крупная стеклянная бабочка с золотой кромкой (это настоящий удар), фиолетовый след с угольками.', -1, [
        E('sprites', 0, 'caster', duration=100000, texture='mote_butterfly', count=1, rate=0.2, spread=0, speed=0, size=[0.7, 0.7], life=6,
          color=GLASS, glow=0.5, follow=True),
        E('sprites', 0, 'caster', duration=100000, texture='ereb_hand_butterfly_rim', count=1, rate=0.2, spread=0, speed=0, size=[0.7, 0.7], life=6,
          color=GOLD, glow=0.3, follow=True),
        E('trail', 0, 'caster', duration=100000, width=0.25, length=8, fade=1.0, color=FLAME, follow=True),
        E('sprites', 0, 'caster', duration=100000, texture='cult_flame_tongue', count=300, rate=1, spread=0.15, speed=0.0, gravity=-0.02,
          size=[0.25, 0.05], life=6, color=FLAME),
    ])
    fx('ereb_hand_changeling_flame_hit', '«Пламя-подменыш», попадание (16 тиков): caster = поражённый (союзник рядом с целью или сама цель). '
       'Вспышка фиолетового огня, стекло, бабочка рассыпается.', 16, [
        E('flash', 0, 'caster+0,1.1,0', duration=6, size=1.6, rays=6, color=FLAME_HI, brightness=1.1),
        E('sprites', 0, 'caster+0,1.0,0', duration=4, texture='cult_flame_tongue', count=16, rate=4, spread=0.5, speed=0.06, gravity=-0.03,
          size=[0.5, 0.1], life=12, color=FLAME),
        glass(0, 'caster+0,1.1,0', 16, spread=0.5, speed=0.12, gravity=0.03, life=14),
    ])
    # ---------------------------------------------------------------- «Ложное отступление»
    fx('ereb_hand_false_retreat', '«Ложное отступление» (26 тиков = ereb_hand_false_retreat 1.3 с): caster = Эреб на месте прыжка. 5 (leap) — '
       'от ног взлетают стеклянные бабочки и пыль; 13 (land) — на точке приземления (point:land, или caster, если код шлёт его там) тихая '
       'стеклянная рябь: тут настоящий исчезает, остаётся ДВОЙНИК. Подмену видно только по рябью и по отсутствию тени.', 26, [
        glass(5, 'caster+0,0.2,0', 10, spread=0.6, speed=0.06, gravity=0.02, life=12),
        *butterflies(5, 'caster+0,0.6,0', 4, 4, 1, spread=0.4, speed=0.06, life=20),
        E('wave', 13, 'point:land+0,1,0', duration=8, shape='sphere', radius=1.3, rim=0.8, color='@secondary', brightness=0.35),
        E('flash', 13, 'point:land+0,1.6,0', duration=4, size=0.6, rays=4, color=GLASS_HI, brightness=0.5),
    ])
    fx('ereb_hand_false_retreat_double', '«Ложное отступление», двойник (40 тиков = 2 с; код стопит раньше, если его раскрыли): caster = двойник, '
       'follow. Почти незаметно: редкий блик стекла на силуэте. ТЕНИ НЕТ (код: shadowRadius = 0 у двойника) — это главная подсказка.', 40, [
        E('sprites', 0, 'caster+0,1.3,0', duration=40, texture='glint4', count=4, rate=0.1, spread=0.5, speed=0, size=[0.3, 0.08], life=8,
          color=WHITE, follow=True),
    ])
    fx('ereb_hand_false_retreat_vanish', '«Ложное отступление», двойник рассыпается (20 тиков): caster = двойник. Стекло и бабочки уносит вверх; '
       'шлётся, когда настоящий бьёт, или через 2 с, когда настоящий появляется на месте двойника.', 20, [
        E('flash', 0, 'caster+0,1.2,0', duration=5, size=1.6, rays=6, color=GLASS_HI),
        glass(0, 'caster+0,1.2,0', 24, spread=0.6, speed=0.08, gravity=-0.01, life=16),
        *butterflies(0, 'caster+0,1.2,0', 14, 14, 1, spread=0.5, speed=0.08, life=24),
    ])
    fx('ereb_hand_false_retreat_strike', '«Ложное отступление», удар в спину (24 тика = ereb_hand_false_retreat_strike, hit 0.35 с = 7 тик): '
       'caster = настоящий Эреб (появляется за спиной цели), target = цель. 0 (appear) — из воздуха проступает стекло, вспышка; 7 (hit) — '
       'золотой блик у цели (урон — код). Без линии до цели.', 24, [
        E('wave', 0, 'caster+0,1.2,0', duration=6, shape='sphere', radius=1.4, rim=1.0, color='@secondary', brightness=0.6),
        E('flash', 0, 'caster+0,1.3,0', duration=4, size=1.4, rays=6, color=GLASS_HI),
        glass(0, 'caster+0,1.2,0', 16, spread=0.6, speed=-0.1, gravity=0.0, life=6),
        E('flash', 7, 'target+0,1.3,0', duration=6, size=0.7, rays=4, anamorphic=1.2, color=GOLD_HI, brightness=1.2),
        sparks(7, 'target+0,1.3,0', 10),
    ])
    # ---------------------------------------------------------------- «Отражение-предатель»
    fx('ereb_hand_traitor_reflection', '«Отражение-предатель», каст (40 тиков = ereb_hand_traitor_reflection 2.0 с): caster = Эреб. 10 (mirror) — '
       'блик на «Длани», указывающей на игрока (зеркало у игрока — ereb_hand_traitor_mirror); 24 (emerge) — призрачная рука сжимает '
       'отражение: звон, золотые искры у ладони.', 40, [
        E('flash', 10, 'caster-0.25,1.35,0.6', duration=6, size=0.8, rays=6, color=GLASS_HI, brightness=0.9),
        E('flash', 24, 'caster+0.5,1.95,0.6', duration=6, size=1.0, rays=6, color=GOLD_HI, brightness=1.0),
        sparks(24, 'caster+0.5,1.95,0.6', 10, color=GOLD_HI, spread=0.3, speed=0.08),
    ])
    fx('ereb_hand_traitor_mirror', '«Отражение-предатель», зеркало (40 тиков): caster = точка в 1.5 бл. перед игроком-«оригиналом», yaw — к игроку. '
       '0 — зеркало встаёт из земли (меш ereb_hand_mirror), в стекле — блики; 14 (= emerge каста) — стекло идёт рябью, из зеркала шагает '
       'копия (сущность — код); 30 — зеркало трескается и рассыпается.', 40, [
        E('mesh', 0, 'caster', model='ereb_hand_mirror', scale=0.8, appear='rise', until=30),
        E('decal', 0, 'caster', duration=34, texture='illusion_seal', radius=1.2, glow=0.2, color=GLASS, brightness=0.4),
        E('wave', 14, 'caster+0,1.2,0.1', duration=10, shape='sphere', radius=1.3, rim=1.0, color='@secondary', brightness=0.8),
        E('flash', 14, 'caster+0,1.2,0.2', duration=6, size=1.6, rays=6, color=GLASS_HI),
        E('flash', 30, 'caster+0,1.2,0', duration=6, size=1.6, rays=6, color=WHITE),
        glass(30, 'caster+0,1.2,0', 24, spread=0.7, speed=0.12, gravity=0.03, life=16, size=(0.22, 0.06)),
    ])
    fx('ereb_hand_traitor_copy', '«Отражение-предатель», копия (120 тиков = 6 с; код стопит раньше, если разбита): caster = копия, follow. '
       'Модель игрока с его скином полупрозрачно + стеклянный оверлей textures/entity/ereb_hand/traitor_glass.png (код). Здесь — блеск '
       'стекла по силуэту, осыпающаяся стеклянная пыль, кольцо под ногами.', 120, [
        E('aura', 0, 'caster', target='caster', follow=True, duration=120, thickness=0.05, pulse=[0.4, 14], motes=3, texture='mote_glass',
          ring=True, color=GLASS, brightness=0.5),
        E('sprites', 0, 'caster+0,1.4,0', duration=120, texture='glint4', count=12, rate=0.1, spread=0.5, speed=0, size=[0.3, 0.08], life=8,
          color=WHITE, follow=True),
        E('sprites', 0, 'caster+0,1.0,0', duration=120, texture='mote_glass', count=40, rate=0.35, spread=0.4, speed=0.0, gravity=0.01,
          size=[0.1, 0.03], life=16, color=GLASS_HI),
    ])
    fx('ereb_hand_traitor_hit', '«Отражение-предатель», удар по копии (8 тиков; оригиналу хватает 1, остальным — 3): caster = копия. Звон, '
       'на копии трещина, отлетает стекло.', 8, [
        E('flash', 0, 'caster+0,1.2,0', duration=4, size=0.8, rays=4, color=GLASS_HI),
        E('sigil', 0, 'caster+0,1.1,0', id='illusion_mirror_crack', scale=0.3, until=8, follow=True),
        glass(0, 'caster+0,1.2,0', 8, spread=0.3, speed=0.1, gravity=0.03, life=10),
    ])
    fx('ereb_hand_traitor_shatter', '«Отражение-предатель», копия разбита (20 тиков): caster = копия. Она лопается стеклом и бабочками (модель '
       'убрать на 0).', 20, [
        E('flash', 0, 'caster+0,1.0,0', duration=6, size=2.0, rays=8, color=WHITE),
        glass(0, 'caster+0,1.0,0', 40, spread=0.5, speed=0.16, gravity=0.03, life=20, size=(0.24, 0.07)),
        *butterflies(0, 'caster+0,1.2,0', 8, 8, 1, spread=0.4, speed=0.08, life=24),
    ])
    fx('ereb_hand_traitor_burst_warn', '«Отражение-предатель», копия вот-вот взорвётся (20 тиков = последняя 1 с из 6): caster = копия, follow. '
       'По копии бегут золотые трещины, на земле — кольцо r3 (зона урона).', 20, [
        E('sigil', 0, 'caster+0,1.0,0', id='illusion_mirror_crack', scale=0.4, until=20, follow=True),
        E('decal', 0, 'caster', duration=20, texture='ereb_hand_flame_rim', radius=3.0, grow=6, glow=0.4, color=GOLD, brightness=0.8, pulse=5,
          follow=True),
        E('wave', 0, 'caster+0,0.05,0', duration=20, shape='ring', radius=3.0, color=GOLD, brightness=0.5, reverse=True, follow=True),
    ])
    fx('ereb_hand_traitor_burst', '«Отражение-предатель», взрыв осколками (24 тика; урон по площади r3 — код): caster = копия. Вспышка, кольцо r3, '
       'осколки стекла веером.', 24, [
        E('flash', 0, 'caster+0,1.0,0', duration=8, size=3.0, rays=8, color=WHITE, brightness=1.3),
        E('wave', 0, 'caster+0,0.05,0', duration=10, shape='ring', radius=3.0, color='@secondary', brightness=0.9),
        glass(0, 'caster+0,1.0,0', 60, spread=0.6, speed=0.3, gravity=0.03, life=18, size=(0.26, 0.08)),
        sparks(0, 'caster+0,1.0,0', 16, color=GOLD_HI, spread=0.6, speed=0.2),
        E('decal', 0, 'caster', duration=24, texture='higher_cracks', radius=3.0, grow=3, glow=0.4, fadeOut=16, color=GLASS),
    ])
    # ---------------------------------------------------------------- «Рой лжи»
    CUP, REL = 'caster+0.5,1.9,0.45', 'caster+0.72,2.45,0.6'
    fx('ereb_hand_swarm_of_lies', '«Рой лжи», каст (32 тика = ereb_hand_swarm_of_lies 1.6 с): caster = Эреб. 6 (gather) — в сложенной чашей '
       'призрачной руке кружат бабочки; 15 (release) — рука раскрывается, вспышка: код выпускает 12 бабочек-снарядов (6 ложных, 6 настоящих).', 32, [
        E('vortex', 6, CUP, duration=9, radius=0.5, height=0.4, arms=3, speed=16, pull=0.4, texture='mote_butterfly', particles=16, life=9, size=0.22,
          color=GLASS, follow=True),
        E('flash', 15, REL, duration=6, size=1.4, rays=8, color=GLASS_HI, brightness=1.0),
        *butterflies(15, REL, 8, 8, 1, spread=0.4, speed=0.12, gravity=-0.01, life=16),
    ])
    for real in (True, False):
        els = [E('sprites', 0, 'caster', duration=100000, texture='mote_butterfly', count=1, rate=0.2, spread=0, speed=0, size=[0.55, 0.55], life=6,
                 color=GLASS, glow=0.4, follow=True),
               E('sprites', 0, 'caster', duration=100000, texture='mote_glass', count=200, rate=0.5, spread=0.1, speed=0, gravity=0.01,
                 size=[0.08, 0.02], life=10, color=GLASS_HI)]
        if real:
            els += [E('sprites', 0, 'caster', duration=100000, texture='ereb_hand_butterfly_rim', count=1, rate=0.2, spread=0, speed=0,
                      size=[0.55, 0.55], life=6, color=GOLD, glow=0.25, follow=True,
                      comment='подсказка: золото по краю крыльев только у настоящих'),
                    E('sprites', 0, 'caster', duration=100000, texture='spark_soft', count=200, rate=0.4, spread=0.12, speed=0, gravity=0.01,
                      size=[0.07, 0.02], life=8, color=GOLD_HI)]
        fx('ereb_hand_swarm_' + ('true' if real else 'false'), '«Рой лжи», ' + ('НАСТОЯЩАЯ бабочка (урон и слепота 1 с — код; тихо звенит — '
           'звук ereb_hand.swarm_chime раз в 10 тиков)' if real else 'ЛОЖНАЯ бабочка (проходит насквозь)') +
           ' (duration −1, код стопит): caster = снаряд, follow. Стеклянная бабочка с тонким следом стеклянной пыли' +
           ('; по краю крыльев — золотая кромка (ereb_hand_butterfly_rim) и золотые искры в следе.' if real else ', без золота.'), -1, els)
    fx('ereb_hand_swarm_hit', '«Рой лжи», настоящая бабочка попала (12 тиков): caster = игрок. Золотая вспышка у лица, стекло (слепота 1 с — код).', 12, [
        E('flash', 0, 'caster.eyes', duration=6, size=1.2, rays=6, color=GOLD_HI, brightness=1.2),
        glass(0, 'caster.eyes', 10, spread=0.3, speed=0.08, gravity=0.02, life=10),
    ])
    fx('ereb_hand_swarm_pass', '«Рой лжи», ложная бабочка прошла насквозь (8 тиков): caster = точка прохода. Бабочка тает рябью, без вспышки.', 8, [
        E('wave', 0, 'caster', duration=6, shape='sphere', radius=0.5, rim=0.8, color='@secondary', brightness=0.3),
        glass(0, 'caster', 6, spread=0.2, speed=0.04, gravity=-0.01, life=8),
    ])
    # ---------------------------------------------------------------- мифическое «Ложный рассвет»
    fx('ereb_hand_false_dawn', '«Ложный рассвет» (120 тиков = ereb_hand_false_dawn 6.0 с; 33%, раз за бой): caster = Эреб (не follow). '
       '10 (kneel) — он на колене: небо светлеет (тёплый рассветный тон на арену, свет восходящего солнца), «победная» фанфара '
       '(ereb_hand.false_victory), полоса скрыта (код), титра нет; бабочки вокруг него КРУЖАТ И НЕ УЛЕТАЮТ (подсказка: у настоящего поражения '
       'улетают); 90 (rise) — встаёт: рассвет гаснет, бабочки стягиваются к нему; 100 (wave) — волна по арене (≤6 бл. — 60% макс. ХП, '
       'дальше — 20%; урон — код): вспышка, кольцо до 24 бл., внутреннее золотое кольцо r6 (граница сильного урона).', 120, [
        E('tint', 10, 'caster', duration=90, radius=48, color='#FFD9A0', strength=0.32, **{'in': ease(24), 'out': ease(10)}),
        E('decal', 10, 'caster', duration=90, texture='dawn_sunrise', radius=6.0, grow=30, glow=0.4, color=GOLD_HI, brightness=0.6, fadeOut=12),
        E('curtain', 10, 'caster', duration=90, count=28, radius=[20, 24], height=[8, 14], grow=40, width=[0.8, 1.4], brightness=[0.2, 0.4],
          texture='beam_fade', flicker=0.15, color=GOLD_HI, comment='свет рассвета по краю арены'),
        E('vortex', 10, 'caster+0,0.3,0', duration=80, radius=2.0, height=2.6, arms=4, speed=3, pull=0.0, texture='mote_butterfly', particles=40,
          life=80, size=0.3, color=GLASS, comment='бабочки кружат вокруг и НЕ улетают'),
        E('sprites', 10, 'caster+0,1.2,0', duration=80, texture='mote_butterfly_side', count=24, rate=0.3, spread=1.6, speed=0.0, gravity=0.0,
          sway=0.6, size=[0.26, 0.2], life=80, color=GOLD_HI, glow=0.3),
        E('vortex', 90, 'caster+0,0.5,0', duration=10, radius=2.4, height=2.4, arms=4, speed=14, pull=0.8, texture='mote_butterfly', particles=40,
          life=10, size=0.3, color=GLASS, comment='встаёт: бабочки стягиваются к нему'),
        E('flash', 100, 'caster+0,1.6,0', duration=10, size=5.0, rays=12, color=WHITE, brightness=1.4, screen=0.5),
        E('wave', 100, 'caster+0,0.05,0', duration=18, shape='ring', radius=24, color=GOLD_HI, brightness=0.9),
        E('wave', 100, 'caster+0,0.05,0', duration=8, shape='ring', radius=6, color=CRIMSON_HI, brightness=0.9),
        E('wave', 100, 'caster+0,1,0', duration=14, shape='sphere', radius=8, rim=1.0, color='@secondary', brightness=0.5),
        glass(100, 'caster+0,1.2,0', 50, spread=1.0, speed=0.3, gravity=0.02, life=18, size=(0.24, 0.07)),
        *butterflies(100, 'caster+0,1.4,0', 24, 24, 1, spread=0.8, speed=0.2, life=24),
    ])


# ================================================================== звуки и субтитры
def S_(name, pitch, volume):
    return {'name': name, 'type': 'event', 'pitch': pitch, 'volume': volume}


SOUNDS = {   # ванильные стекло и аметист с другим pitch (как у T30; демо владельцу перед включением)
    'ereb_hand.slam': [S_('minecraft:block.glass.break', 0.55, 1.0), S_('minecraft:entity.iron_golem.damage', 0.7, 0.7)],
    'ereb_hand.grab': [S_('minecraft:block.amethyst_cluster.place', 0.7, 1.0), S_('minecraft:block.glass.place', 0.6, 0.9)],
    'ereb_hand.squeeze': [S_('minecraft:block.glass.break', 1.3, 0.7), S_('minecraft:block.amethyst_cluster.break', 0.6, 0.9)],
    'ereb_hand.crack': [S_('minecraft:block.glass.break', 0.75, 0.8), S_('minecraft:block.amethyst_block.resonate', 0.6, 1.0)],
    'ereb_hand.mask_shatter': [S_('minecraft:block.glass.break', 0.9, 1.0), S_('minecraft:block.amethyst_cluster.break', 1.2, 1.0)],
    'ereb_hand.shard_ring': [S_('minecraft:block.amethyst_block.chime', 1.8, 0.9), S_('minecraft:block.amethyst_block.chime', 2.0, 0.8)],
    'ereb_hand.shard_break': [S_('minecraft:block.glass.break', 1.6, 0.8), S_('minecraft:block.amethyst_cluster.break', 1.5, 0.8)],
    'ereb_hand.shard_burst': [S_('minecraft:entity.generic.explode', 1.4, 0.6), S_('minecraft:block.glass.break', 0.7, 1.0)],
    'ereb_hand.flame': [S_('minecraft:item.firecharge.use', 0.7, 0.8), S_('minecraft:block.amethyst_block.resonate', 1.2, 0.7)],
    'ereb_hand.grip': [S_('minecraft:block.amethyst_cluster.break', 0.5, 1.0), S_('minecraft:entity.iron_golem.attack', 0.8, 0.6)],
    'ereb_hand.oath': [S_('minecraft:block.amethyst_block.chime', 0.8, 1.0), S_('minecraft:entity.illusioner.cast_spell', 0.8, 0.8)],
    'ereb_hand.mirror': [S_('minecraft:entity.illusioner.mirror_move', 0.8, 0.9), S_('minecraft:block.amethyst_block.resonate', 0.9, 0.8)],
    'ereb_hand.sky_hand': [S_('minecraft:block.beacon.activate', 0.5, 1.0), S_('minecraft:block.amethyst_block.resonate', 0.5, 1.0)],
    'ereb_hand.reveal': [S_('minecraft:block.beacon.power_select', 0.6, 1.0), S_('minecraft:block.amethyst_block.resonate', 0.55, 1.2)],
    'ereb_hand.dissolve': [S_('minecraft:block.amethyst_cluster.break', 0.85, 1.0), S_('minecraft:block.glass.break', 0.75, 0.8)],
    # вторая партия
    'ereb_hand.changeling': [S_('minecraft:item.firecharge.use', 0.9, 0.9), S_('minecraft:block.amethyst_block.chime', 1.4, 0.8)],
    'ereb_hand.retreat': [S_('minecraft:entity.illusioner.mirror_move', 1.1, 0.8), S_('minecraft:block.amethyst_block.step', 0.8, 0.8)],
    'ereb_hand.reflection': [S_('minecraft:entity.illusioner.prepare_mirror', 0.9, 1.0), S_('minecraft:block.amethyst_block.resonate', 1.1, 0.9)],
    'ereb_hand.swarm': [S_('minecraft:block.amethyst_cluster.place', 1.3, 0.9), S_('minecraft:entity.allay.item_thrown', 0.9, 0.8)],
    'ereb_hand.swarm_chime': [S_('minecraft:block.amethyst_block.chime', 2.0, 0.35), S_('minecraft:block.amethyst_block.chime', 1.8, 0.35)],
    'ereb_hand.false_victory': [S_('minecraft:ui.toast.challenge_complete', 1.0, 0.9)],
    'ereb_hand.dawn_wave': [S_('minecraft:block.beacon.deactivate', 0.6, 1.0), S_('minecraft:block.glass.break', 0.5, 1.0)],
}
SUB = {'slam': ('Длань бьёт о землю', 'The Hand strikes the ground'), 'grab': ('Стеклянные пальцы смыкаются', 'Glass fingers close'),
       'squeeze': ('Хрустит стекло', 'Glass crunches'), 'crack': ('Маска трескается', 'The mask cracks'),
       'mask_shatter': ('Маска разбивается', 'The mask shatters'), 'shard_ring': ('Осколок звенит', 'A shard rings'),
       'shard_break': ('Осколок разбит', 'A shard breaks'), 'shard_burst': ('Осколок взрывается', 'A shard bursts'),
       'flame': ('Вспыхивает ложное пламя', 'False flame ignites'), 'grip': ('Стеклянная хватка', 'Glass grip'),
       'oath': ('Звучит чужая клятва', 'A borrowed oath rings'), 'mirror': ('Встают зеркала', 'Mirrors rise'),
       'sky_hand': ('Рука опускается с неба', 'A hand descends from the sky'), 'reveal': ('Сон раскрывается', 'The dream unfolds'),
       'dissolve': ('Эреб рассыпается бабочками', 'Ereb scatters into butterflies'),
       'changeling': ('Пламя оборачивается бабочкой', 'The flame turns into a butterfly'), 'retreat': ('Эреб отступает', 'Ereb falls back'),
       'reflection': ('Отражение выходит из зеркала', 'A reflection steps out of the mirror'), 'swarm': ('Взлетает рой бабочек', 'A swarm takes wing'),
       'swarm_chime': ('Тихо звенит бабочка', 'A butterfly chimes softly'), 'false_victory': ('Звучит победа', 'Victory sounds'),
       'dawn_wave': ('Ложный рассвет бьёт волной', 'The false dawn strikes')}


def sounds_lang():
    # точечно: дописать/заменить только свои события в конце файла, чужое форматирование не трогать
    p = os.path.join(M.A, 'sounds.json')
    txt = open(p, encoding='utf-8').read()
    d = json.loads(txt)
    if any(k in d for k in SOUNDS):
        start = min(txt.index('"%s"' % k) for k in SOUNDS if k in d)
        txt = txt[:start].rstrip().rstrip(',') + '\n}\n'           # наш блок всегда последний — срезаем его и пишем заново
    body = ',\n'.join('  %s: %s' % (json.dumps(k), json.dumps({'subtitle': 'subtitles.pohsmp_core.' + k, 'sounds': v}, ensure_ascii=False))
                       for k, v in SOUNDS.items())
    end = txt.rstrip().rindex('}')
    txt = txt[:end].rstrip() + ',\n' + body + '\n}\n'
    json.loads(txt)
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(txt)
    M.WRITTEN.append('sounds.json (+%d событий ereb_hand.*)' % len(SOUNDS))
    extra = {'subtitles.pohsmp_core.ereb_hand.' + k: v for k, v in SUB.items()}
    extra.update({'ui.pohsmp_core.ereb_hand.false_flame': ('«Ложное пламя» — жжёт лишь часть кругов', '"False Flame" — only some circles burn'),
                  'ui.pohsmp_core.ereb_hand.glass_grip': ('«Стеклянная хватка» — уйдите из конуса!', '"Glass Grip" — get out of the cone!'),
                  'ui.pohsmp_core.ereb_hand.foreign_oath': ('«Чужая клятва» — ваш урон по Эребу ранит союзника', '"Borrowed Oath" — your damage to Ereb hurts an ally'),
                  'ui.pohsmp_core.ereb_hand.thousand_reflections': ('«Тысяча отражений»', '"A Thousand Reflections"'),
                  'ui.pohsmp_core.ereb_hand.mask_fall_hint': ('Разбей СВОЙ осколок маски!', 'Break YOUR shard of the mask!'),
                  'ui.pohsmp_core.ereb_hand.false_arena': ('Мир лжёт тебе…', 'The world lies to you…'),
                  # вторая партия: названия приёмов и подсказки
                  'ui.pohsmp_core.ereb_hand.spell.changeling_flame': ('Пламя-подменыш', 'Changeling Flame'),
                  'ui.pohsmp_core.ereb_hand.spell.false_retreat': ('Ложное отступление', 'False Retreat'),
                  'ui.pohsmp_core.ereb_hand.spell.traitor_reflection': ('Отражение-предатель', 'Traitor Reflection'),
                  'ui.pohsmp_core.ereb_hand.spell.swarm_of_lies': ('Рой лжи', 'Swarm of Lies'),
                  'ui.pohsmp_core.ereb_hand.spell.false_dawn': ('Ложный рассвет', 'False Dawn'),
                  'ui.pohsmp_core.ereb_hand.changeling_flame': ('«Пламя-подменыш» — шар мерцает золотом, прежде чем стать бабочкой', '"Changeling Flame" — the fireball flickers gold before it turns'),
                  'ui.pohsmp_core.ereb_hand.false_retreat': ('«Ложное отступление» — у двойника нет тени', '"False Retreat" — the double casts no shadow'),
                  'ui.pohsmp_core.ereb_hand.traitor_reflection': ('«Отражение-предатель» — разбей свою копию!', '"Traitor Reflection" — break your own copy!'),
                  'ui.pohsmp_core.ereb_hand.swarm_of_lies': ('«Рой лжи» — настоящие звенят и горят золотом по краю', '"Swarm of Lies" — the real ones chime and glow gold at the edges')})
    for i, name in enumerate(('ru_ru', 'en_us')):
        p = os.path.join(M.A, 'lang', name + '.json')
        d = json.load(open(p, encoding='utf-8'))
        for k, v in extra.items():
            d[k] = v[i]
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')
        M.WRITTEN.append('lang/%s.json (+%d ключей fx)' % (name, len(extra)))


def run(mod):
    global M
    M = mod
    FX_LIST.clear()
    MESHES.clear()
    textures()
    meshes()
    effects()
    effects2()
    sounds_lang()
