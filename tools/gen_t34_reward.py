#!/usr/bin/env python3
"""
T34 «Наградные заклинания боссов» — визуал (помощник по визуалу): трофейные свитки, иконки, lang, fx и меши fx.
Анимации игрока — tools/gen_t34_anims.py, кадр-лист и видео — tools/t34_video.py.

  python3 tools/gen_t34_reward.py            # всё
  python3 tools/gen_t34_reward.py --sheet    # + лист сравнения свитков docs/media/t34_scrolls_compare.png

Свитки 32×32 (item/scroll_<id>, через client/ScrollModels — тот же силуэт, что у прочих свитков мода): чёрный пергамент, золотые
валики и золотая кайма, багровая сургучная печать Меллисто в центре, в печати — символ босса; по кайме бежит золотой блик
(анимированная текстура: 4 кадра по 4 тика, .mcmeta). Ни у одного свитка мода нет чёрного пергамента с золотом и печатью.
Иконки 16×16 — круглая красная рамка Высших (как gen_nightmare_fx.icons).
fx — на основе готовых fx боссов (cult_ash_*, irina_*, aris_slam / aris_last_blow, martin_banner_* / martin_soldier_*, ereb_blink /
ereb_thrust, ereb_hand_of_lies_sky), уменьшены под игрока. Правило «никаких лучей от заклинателя к цели» соблюдено.
Оси fx: смещения `caster+x,y,z` — x вправо, y вверх, z вперёд по взгляду заклинателя (docs/fx.md).
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
MEDIA = os.path.join(ROOT, 'docs', 'media')
IDS = ['ashen_harvest', 'jealous_embrace', 'anvil_strike', 'warlord_banner', 'mirror_step', 'hand_of_lies']
# свитки — только для четырёх (владелец 21.11: Жатва и Длань встроены в Накидку и Маску T35, свитков у них нет)
SCROLL_IDS = ['jealous_embrace', 'anvil_strike', 'warlord_banner', 'mirror_step']
BOSS = {'ashen_harvest': 'Глава Культа', 'jealous_embrace': 'Ирина', 'anvil_strike': 'Арис', 'warlord_banner': 'Мартин',
        'mirror_step': 'Эреб', 'hand_of_lies': 'Длань Лжи'}
WRITTEN = []


def hx(h, a=255):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)


def write(rel, obj):
    p = os.path.join(A, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    WRITTEN.append(rel)


# ================================================================== свитки
# силуэт — как у всех свитков мода (scroll_higher.png): валики в строках 3–8 и 23–28, пергамент 9–22 с волнистыми краями
GOLD = {'out': '#2A1606', 'hi': '#FFF2B8', 'lt': '#F2CC5C', 'mid': '#D09A2C', 'dk': '#8C5E14', 'deep': '#5A3608'}
GEM = {'hi': '#FF9AA8', 'mid': '#D0203A', 'dk': '#6A0614'}
INK = {'base': '#151017', 'b2': '#1C1520', 'b3': '#100C12', 'edge': '#07050A', 'fleck': '#2A2230'}
WAX = {'out': '#3A0208', 'dk': '#7A0A16', 'mid': '#B01426', 'lt': '#DA3444', 'hi': '#FF7A82'}
SYM = {'g': '#FFD860', 'd': '#2A0306', 'h': '#FFF6C8'}

# символы босса в печати: 7×7, центр (3, 3); 'g' — золото, 'h' — блик
SYMBOLS = {
    'ashen_harvest': [   # коса: древко по диагонали, лезвие серпом влево, остриё загнуто вниз
        '.ggggg.',
        'g....g.',
        '.....g.',
        '....g..',
        '....g..',
        '...g...',
        '..g....'],
    'jealous_embrace': [  # крюк посоха: древко и завиток вверху
        '..ggg..',
        '.g...g.',
        '.g..g..',
        '...g...',
        '...g...',
        '...g...',
        '...g...'],
    'anvil_strike': [     # молот: голова и рукоять
        'ggggggg',
        'ghggggg',
        'ggggggg',
        '...g...',
        '...g...',
        '...g...',
        '...g...'],
    'warlord_banner': [   # знамя: древко и полотнище с вырезом
        'g......',
        'gggggg.',
        'gghggg.',
        'gggggg.',
        'ggg.gg.',
        'g......',
        'g......'],
    'mirror_step': [      # рапира: клинок вверх, гарда-чашка, навершие
        '...h...',
        '...g...',
        '...g...',
        '...g...',
        '.ggggg.',
        '..g.g..',
        '...g...'],
    'hand_of_lies': [     # ладонь: пальцы вверх
        '.g.g.g.',
        '.g.g.g.',
        'gg.g.g.',
        'gggggg.',
        '.ggggg.',
        '.ggggg.',
        '..ggg..'],
}


def _template():
    """Маска и разметка силуэта из scroll_higher.png: 'rod' (валик), 'cap' (торцы валика), 'body' (пергамент), 'edge' (контур)."""
    im = Image.open(os.path.join(A, 'textures', 'item', 'scroll_higher.png')).convert('RGBA')
    a = np.asarray(im)
    alpha = a[..., 3] > 0
    kind = np.full((32, 32), '', dtype=object)
    for y in range(32):
        for x in range(32):
            if not alpha[y, x]:
                continue
            if 3 <= y <= 8 or 23 <= y <= 28:
                kind[y, x] = 'cap' if (x <= 5 or x >= 26) else 'rod'
            else:
                kind[y, x] = 'body'
    return alpha, kind


def scroll_frames(sid):
    alpha, kind = _template()
    rng = np.random.RandomState(abs(hash(sid)) % 2 ** 31 if False else sum(map(ord, sid)))
    base = np.zeros((32, 32, 4), np.uint8)

    def put(x, y, c):
        base[y, x] = hx(c)

    # --- валики: золото, торцы — багровые камни (у прочих свитков синие)
    for y0 in (3, 23):
        rows = {0: 'out', 1: 'hi', 2: 'lt', 3: 'mid', 4: 'dk', 5: 'out'}
        for dy, role in rows.items():
            y = y0 + dy
            for x in range(3, 29):
                if not alpha[y, x]:
                    continue
                if kind[y, x] == 'cap':
                    if dy in (0, 5) or x in (3, 28):
                        put(x, y, GOLD['out'])
                    else:
                        put(x, y, GEM['hi'] if dy == 1 else GEM['mid'] if dy in (2, 3) else GEM['dk'])
                        if x in (5, 26) and dy in (1, 2, 3, 4):
                            put(x, y, GOLD['out'] if dy == 4 else GOLD['dk'])
                else:
                    c = GOLD[role]
                    if role == 'lt' and (x - 6) % 4 == 3:     # насечки на валике
                        c = GOLD['hi']
                    if role == 'mid' and x == 27:
                        c = GOLD['dk']
                    put(x, y, c)
    # --- пергамент: чёрный, золотая кайма по волнистому краю
    for y in range(9, 23):
        xs = [x for x in range(32) if alpha[y, x]]
        if not xs:
            continue
        x0, x1 = xs[0], xs[-1]
        for x in xs:
            if x == x0 or x == x1:
                put(x, y, INK['edge'])
            elif x == x0 + 1 or x == x1 - 1:
                put(x, y, GOLD['mid'] if x == x0 + 1 else GOLD['dk'])
            else:
                v = rng.rand()
                put(x, y, INK['b2'] if v < 0.18 else INK['b3'] if v < 0.3 else INK['fleck'] if v < 0.34 else INK['base'])
    for x in range(32):                                   # кайма сверху и снизу пергамента
        for y in (9, 22):
            if alpha[y, x] and kind[y, x] == 'body' and base[y, x][3] and tuple(base[y, x][:3]) not in (hx(INK['edge'])[:3],):
                put(x, y, GOLD['dk'] if y == 22 else GOLD['mid'])
    # строки «письма» золотом, тускло (по бокам от печати)
    for y in (11, 13, 19, 21):
        for x in range(9, 23):
            if alpha[y, x] and not (10 <= x <= 21 and 10 <= y <= 21) and rng.rand() < 0.6:
                put(x, y, '#3E2E18')
    # --- печать Меллисто: багровый сургуч с неровным краем, золотой ободок-знак культа, символ босса
    cx, cy = 15.5, 15.5
    for y in range(9, 23):
        for x in range(7, 25):
            d = math.hypot(x - cx, y - cy)
            ang = math.atan2(y - cy, x - cx)
            r = 4.75 + 0.35 * math.sin(ang * 5 + 0.7)            # волна сургуча
            if d <= r + 0.5:
                if d > r - 0.5:
                    c = WAX['out']
                elif d > r - 1.4 and math.sin(ang) > -0.1:          # нижняя кромка темнее (объём)
                    c = WAX['dk']
                elif d > r - 1.4 and -2.4 < ang < -0.8:             # верх-лево — блик края
                    c = WAX['lt']
                else:
                    c = WAX['mid']
                put(x, y, c)
    put(17, 21, WAX['dk'])                                 # капля сургуча вниз
    put(17, 22, WAX['out'])
    sym = SYMBOLS[sid]
    for j, row in enumerate(sym):
        for i, ch in enumerate(row):
            if ch != '.':
                put(12 + i, 12 + j, SYM['h'] if ch == 'h' else SYM['g'])
    base[~alpha] = 0
    # --- мерцание: золотой блик бежит по кайме и валикам, 4 кадра
    loop = [(x, 4) for x in range(6, 26)] + [(x0b, y) for y in range(10, 22) for x0b in [_xs_right(alpha, y)]] + \
           [(x, 24) for x in range(25, 5, -1)] + [(x0b, y) for y in range(21, 9, -1) for x0b in [_xs_left(alpha, y)]]
    frames = []
    for f in range(4):
        fr = base.copy()
        for k in range(2):                                 # два блика навстречу друг другу по кругу
            c0 = (f * len(loop) // 4 + k * len(loop) // 2) % len(loop)
            for dk, col in ((0, '#FFFBE6'), (1, GOLD['hi']), (-1, GOLD['hi']), (2, GOLD['lt'])):
                x, y = loop[(c0 + dk) % len(loop)]
                if alpha[y, x]:
                    fr[y, x] = hx(col)
        # искра на печати: кадр 2
        if f == 2:
            fr[13, 18] = hx(SYM['h'])
        frames.append(fr)
    return frames


def _xs_right(alpha, y):
    xs = [x for x in range(32) if alpha[y, x]]
    return xs[-1] - 1


def _xs_left(alpha, y):
    xs = [x for x in range(32) if alpha[y, x]]
    return xs[0] + 1


def scrolls():
    for sid in SCROLL_IDS:
        fr = scroll_frames(sid)
        strip = np.concatenate(fr, 0)
        rel = 'textures/item/scroll_%s.png' % sid
        Image.fromarray(strip, 'RGBA').save(os.path.join(A, rel))
        WRITTEN.append(rel)
        with open(os.path.join(A, rel + '.mcmeta'), 'w', encoding='utf-8') as fh:
            json.dump({'animation': {'frametime': 4, 'interpolate': False}}, fh, indent=1)
            fh.write('\n')
        WRITTEN.append(rel + '.mcmeta')
        write('models/item/scroll_%s.json' % sid, {'parent': 'item/generated', 'textures': {'layer0': 'pohsmp_core:item/scroll_%s' % sid}})


def _font(sz):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def compare_sheet():
    """Лист сравнения: все свитки мода (×4) и шесть трофейных (кадр 0 + 4 кадра мерцания)."""
    import glob
    olds = sorted(f for f in glob.glob(os.path.join(A, 'textures', 'item', 'scroll_*.png'))
                  if os.path.splitext(os.path.basename(f))[0][7:] not in IDS)
    k, cell, cols = 3, 112, 12
    rows_old = (len(olds) + cols - 1) // cols
    W = cols * cell + 40
    H = 70 + rows_old * (cell + 18) + 60 + 2 * (cell * 2 + 40) + 30
    im = Image.new('RGB', (W, H), (40, 38, 44))
    d = ImageDraw.Draw(im)
    d.text((20, 16), 'Свитки мода (все %d, ×%d) — для сравнения' % (len(olds), k), font=_font(22), fill=(230, 226, 220))
    y0 = 60
    for i, f in enumerate(olds):
        s = Image.open(f).convert('RGBA')
        s = s.crop((0, 0, 32, 32))
        x, y = 20 + (i % cols) * cell, y0 + (i // cols) * (cell + 18)
        d.rectangle([x, y, x + 32 * k + 8, y + 32 * k + 8], fill=(58, 56, 62))
        im.paste(s.resize((32 * k, 32 * k), Image.NEAREST), (x + 4, y + 4), s.resize((32 * k, 32 * k), Image.NEAREST))
        d.text((x, y + 32 * k + 9), os.path.basename(f)[7:-4][:15], font=_font(10), fill=(170, 165, 160))
    y = y0 + rows_old * (cell + 18) + 16
    d.text((20, y), 'T34 — трофейные свитки (4 шт.; справа — 4 кадра мерцания); у Жатвы и Длани свитков нет (T35)',
           font=_font(22), fill=(255, 216, 96))
    y += 44
    for i, sid in enumerate(SCROLL_IDS):
        fr = scroll_frames(sid)
        x = 20 + (i % 3) * ((W - 40) // 3)
        yy = y + (i // 3) * (cell * 2 + 40)
        big = Image.fromarray(fr[0], 'RGBA').resize((192, 192), Image.NEAREST)
        d.rectangle([x, yy, x + 200, yy + 200], fill=(58, 56, 62))
        im.paste(big, (x + 4, yy + 4), big)
        for j, f_ in enumerate(fr):
            sm = Image.fromarray(f_, 'RGBA').resize((96, 96), Image.NEAREST)
            px, py = x + 210 + (j % 2) * 100, yy + (j // 2) * 100
            d.rectangle([px, py, px + 96, py + 96], fill=(58, 56, 62))
            im.paste(sm, (px, py), sm)
        d.text((x, yy + 206), '%s — %s' % (sid, BOSS[sid]), font=_font(14), fill=(230, 226, 220))
    out = os.path.join(MEDIA, 't34_scrolls_compare.png')
    im.save(out)
    print('wrote', os.path.relpath(out, ROOT))


# ================================================================== иконки 16×16 (круглая красная рамка Высших)
def _icon(draw, out, k=8):
    S = 16 * k
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([S * 0.04, S * 0.04, S * 0.96, S * 0.96], fill=hx('#10060E'), outline=hx('#FF3B3B'), width=int(S * 0.085))
    draw(d, S)
    sm = im.resize((16, 16), Image.LANCZOS)
    rel = 'textures/gui/spell_icons/%s.png' % out
    sm.save(os.path.join(A, rel))
    WRITTEN.append(rel)


def _L(d, S, pts, col, w):
    d.line([(S * x, S * y) for x, y in pts], fill=hx(col), width=max(1, int(S * w)), joint='curve')


def icon_ashen(d, S):
    """Пепельная Жатва: огненная дуга-серп косы над пеплом."""
    arc = [(0.5 + 0.34 * math.cos(a), 0.62 - 0.34 * math.sin(a)) for a in np.linspace(math.radians(160), math.radians(15), 18)]
    _L(d, S, arc, '#FF7A1E', 0.13)
    _L(d, S, arc, '#FFD24A', 0.06)
    _L(d, S, [(0.32, 0.86), (0.62, 0.3)], '#5A3A2A', 0.06)            # древко
    for x, y in ((0.3, 0.74), (0.5, 0.8), (0.68, 0.72), (0.44, 0.7)):
        d.ellipse([S * (x - 0.03), S * (y - 0.03), S * (x + 0.03), S * (y + 0.03)], fill=hx('#8A7A74'))


def icon_embrace(d, S):
    """Объятия Ревности: красные нити обвивают силуэт, сверху — крюк посоха."""
    d.ellipse([S * 0.42, S * 0.24, S * 0.58, S * 0.4], fill=hx('#3A2430'))
    d.polygon([(S * 0.36, S * 0.84), (S * 0.4, S * 0.42), (S * 0.6, S * 0.42), (S * 0.64, S * 0.84)], fill=hx('#3A2430'))
    for k in range(4):
        y = 0.46 + 0.1 * k
        _L(d, S, [(0.28, y + 0.05), (0.5, y - 0.03), (0.72, y + 0.05)], '#E0283A', 0.045)
    _L(d, S, [(0.74, 0.86), (0.74, 0.26), (0.66, 0.16), (0.56, 0.2), (0.6, 0.3)], '#E8B84A', 0.06)


def icon_anvil(d, S):
    """Удар Наковальни: бирюзовый призрачный молот бьёт вниз, искры."""
    d.rectangle([S * 0.28, S * 0.16, S * 0.72, S * 0.36], fill=hx('#3CD6E0'))
    d.rectangle([S * 0.28, S * 0.16, S * 0.72, S * 0.21], fill=hx('#BFF6FA'))
    d.rectangle([S * 0.46, S * 0.36, S * 0.54, S * 0.66], fill=hx('#1E8E98'))
    _L(d, S, [(0.2, 0.82), (0.8, 0.82)], '#F4A852', 0.06)
    for a in (-60, -30, 0, 30, 60):
        r = math.radians(a - 90)
        _L(d, S, [(0.5 + 0.12 * math.cos(r), 0.8 + 0.12 * math.sin(r)), (0.5 + 0.22 * math.cos(r), 0.8 + 0.22 * math.sin(r))], '#FFE0A0', 0.035)


def icon_banner(d, S):
    """Знамя Полководца: древко, кармин в золотой кайме, корона."""
    _L(d, S, [(0.3, 0.88), (0.3, 0.14)], '#C8A060', 0.06)
    d.polygon([(S * 0.32, S * 0.2), (S * 0.76, S * 0.2), (S * 0.76, S * 0.62), (S * 0.54, S * 0.52), (S * 0.32, S * 0.62)], fill=hx('#B0283A'),
              outline=hx('#F6D88A'))
    d.polygon([(S * 0.42, S * 0.42), (S * 0.44, S * 0.3), (S * 0.5, S * 0.36), (S * 0.54, S * 0.28), (S * 0.58, S * 0.36), (S * 0.64, S * 0.3),
               (S * 0.66, S * 0.42)], fill=hx('#F6D88A'))
    d.ellipse([S * 0.26, S * 0.1, S * 0.34, S * 0.18], fill=hx('#F6D88A'))


def icon_mirror(d, S):
    """Шаг сквозь отражение: рябь стекла кольцами и рапира сквозь неё."""
    for r, c in ((0.3, '#BFE6FF'), (0.21, '#7FB8E0'), (0.12, '#BFE6FF')):
        d.ellipse([S * (0.5 - r), S * (0.5 - r * 0.75), S * (0.5 + r), S * (0.5 + r * 0.75)], outline=hx(c), width=max(1, int(S * 0.035)))
    _L(d, S, [(0.2, 0.8), (0.82, 0.18)], '#F4F8FF', 0.05)
    _L(d, S, [(0.22, 0.66), (0.34, 0.78)], '#E8B84A', 0.06)
    d.ellipse([S * 0.13, S * 0.79, S * 0.21, S * 0.87], fill=hx('#E8B84A'))


def icon_hand(d, S):
    """Длань Лжи: стеклянная ладонь сжимается, золотые швы."""
    col, rim = '#D9CCFF', '#8E7BD6'
    d.rounded_rectangle([S * 0.3, S * 0.44, S * 0.7, S * 0.8], radius=S * 0.08, fill=hx(col), outline=hx(rim))
    for i, x in enumerate((0.33, 0.43, 0.53, 0.63)):
        top = 0.2 + (0.04 if i in (0, 3) else 0)
        d.rounded_rectangle([S * x, S * top, S * (x + 0.075), S * 0.48], radius=S * 0.03, fill=hx(col), outline=hx(rim))
        _L(d, S, [(x + 0.005, 0.34), (x + 0.07, 0.34)], '#F8D260', 0.025)
    d.rounded_rectangle([S * 0.18, S * 0.48, S * 0.32, S * 0.58], radius=S * 0.03, fill=hx(col), outline=hx(rim))


def icons():
    for sid, fn in zip(IDS, (icon_ashen, icon_embrace, icon_anvil, icon_banner, icon_mirror, icon_hand)):
        _icon(fn, sid)


# ================================================================== lang
LANG = {
    # id: (ru, en, ru guide, en guide, {ui-ключ: (ru, en)})
    'ashen_harvest': (
        'Пепельная Жатва', 'Ashen Harvest',
        'Призрачная огненная коса Главы Культа проходит широкой дугой перед заклинателем: ранит и поджигает всех на её пути. '
        'По дуге остаётся пепельный след, он жжёт каждого, кто в него войдёт.',
        'The Cult Leader\'s ghostly burning scythe sweeps a wide arc in front of the caster, wounding and igniting everyone in its path. '
        'It leaves a trail of ash along the arc that burns anyone who steps into it.',
        {'damage': ('Удар косы: %s урона, дуга %s° до %s бл.', 'Scythe: %s damage, %s° arc up to %s blocks'),
         'burn': ('Поджог: %s с', 'Sets on fire for %s s'),
         'trail': ('Пепельный след: %s с, %s урона в секунду', 'Ash trail: %s s, %s damage per second')}),
    'jealous_embrace': (
        'Объятия Ревности', 'Jealous Embrace',
        'Красные нити Ирины опутывают цель во взгляде и рывком притягивают её к заклинателю, а крюк посоха бьёт её. '
        'Метка ревности держится несколько секунд: всё время, пока она горит, заклинатель ранит цель сильнее.',
        'Irina\'s red threads bind the target in the caster\'s gaze and yank it close, where the staff\'s hook strikes it. '
        'A mark of jealousy lingers for a few seconds: while it burns, the caster deals more damage to the target.',
        {'range': ('Цель до %s бл. по взгляду', 'Target up to %s blocks along the gaze'),
         'damage': ('Удар крюком: %s урона', 'Hook strike: %s damage'),
         'mark': ('Метка ревности: %s с, урон заклинателя по цели +%s%%', 'Mark of jealousy: %s s, caster\'s damage to the target +%s%%'),
         'boss': ('Боссов не тянет, только метка', 'Bosses are not pulled, only marked')}),
    'anvil_strike': (
        'Удар Наковальни', 'Anvil Strike',
        'Призрачный бирюзовый молот Арис падает с неба в точку взгляда: ранит и отбрасывает всех вокруг. '
        'После удара оружие заклинателя закалено и бьёт сильнее.',
        'Aris\'s ghostly turquoise hammer falls from the sky onto the point in the caster\'s gaze, wounding and knocking back everyone around it. '
        'Afterwards the caster\'s weapon is tempered and hits harder.',
        {'damage': ('Удар молота: %s урона, радиус %s, до %s бл.', 'Hammer: %s damage, radius %s, up to %s blocks'),
         'temper': ('Закалка: %s с, урон оружием +%s%%', 'Tempered: %s s, weapon damage +%s%%')}),
    'warlord_banner': (
        'Знамя Полководца', 'Warlord\'s Banner',
        'Заклинатель вонзает в землю знамя Мартина. Пока оно стоит, союзники рядом сильнее и крепче, '
        'а двое призрачных солдат Мартина сражаются за заклинателя. Знамя падает — солдаты уходят вместе с ним.',
        'The caster plants Martin\'s banner in the ground. While it stands, nearby allies are stronger and tougher, '
        'and two of Martin\'s ghostly soldiers fight for the caster. When the banner falls, the soldiers go with it.',
        {'time': ('Знамя: %s с, радиус %s', 'Banner: %s s, radius %s'),
         'buff': ('Союзникам: Сила %s и Сопротивление %s', 'Allies: Strength %s and Resistance %s'),
         'soldiers': ('Призрачных солдат: %s', 'Ghostly soldiers: %s')}),
    'mirror_step': (
        'Шаг сквозь отражение', 'Mirror Step',
        'Заклинатель исчезает в стеклянной ряби и выходит из неё за спиной цели, сразу коля её рапирой Эреба. '
        'После укола он ненадолго невидим.',
        'The caster vanishes into a glass ripple and steps out of it behind the target, at once piercing it with Ereb\'s rapier. '
        'After the thrust the caster is briefly invisible.',
        {'range': ('Цель до %s бл.', 'Target up to %s blocks'),
         'damage': ('Укол: %s урона', 'Thrust: %s damage'),
         'invis': ('Невидимость: %s с', 'Invisibility: %s s')}),
    'hand_of_lies': (
        'Длань Лжи', 'Hand of Lies',
        'Призрачная стеклянная рука хватает цель и держит её: та не может двигаться, а союзники бьют её сильнее. '
        'Боссов рука не удерживает, только замедляет.',
        'A ghostly glass hand seizes the target and holds it: it cannot move, and allies hit it harder. '
        'The hand cannot hold bosses, it only slows them.',
        {'hold': ('Удержание: %s с (игроки — %s с)', 'Hold: %s s (players %s s)'),
         'vuln': ('Урон союзников по цели +%s%%', 'Allies deal +%s%% damage to the target'),
         'boss': ('Боссы: замедление %s с', 'Bosses: slowed for %s s')}),
}


def lang():
    for code, col in (('ru_ru', 0), ('en_us', 1)):
        p = os.path.join(A, 'lang', code + '.json')
        d = json.load(open(p, encoding='utf-8'))
        for sid, (ru, en, gru, gen, ui) in LANG.items():
            d['spell.pohsmp_core.%s' % sid] = (ru, en)[col]
            d['spell.pohsmp_core.%s.guide' % sid] = (gru, gen)[col]
            # строки уровней ui.pohsmp_core.<id>.* — у программиста (свои ключи под код), здесь не пишем
        d['ui.pohsmp_core.reward_scroll'] = ('Трофей босса культа Меллисто', 'Trophy of a Mellisto cult boss')[col]
        with open(p, 'w', encoding='utf-8') as fh:
            json.dump(d, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
        WRITTEN.append('lang/%s.json' % code)


# ================================================================== меши fx
def mesh_scythe():
    """Призрачная коса для «Пепельной Жатвы»: древко вдоль +z от точки привязки (хват у заклинателя), лезвие на конце загибается
    вправо-назад (по ходу взмаха справа налево ведёт остриё). Длина ~4 бл. Плоскость — горизонтальная (взмах по земле на высоте пояса)."""
    boxes = []
    L = 3.0
    boxes.append([-0.05, -0.05, 0.4, 0.05, 0.05, L, 1])                       # древко (пепел-уголь)
    boxes.append([-0.08, -0.08, L - 0.15, 0.08, 0.08, L + 0.1, 3])           # кольцо-оковка (светится)
    # лезвие: от конца древка уходит влево (−x: по ходу взмаха справа налево ведёт остриё) и загибается назад к заклинателю
    n, R = 9, 1.25
    pts = [(-R * math.sin(math.radians(105 * i / n)), L - R * (1 - math.cos(math.radians(105 * i / n)))) for i in range(n + 1)]
    for i in range(n):
        (x0, z0), (x1, z1) = pts[i], pts[i + 1]
        u0 = i / n
        mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
        seg = math.hypot(x1 - x0, z1 - z0)
        w = 0.5 * (1 - 0.75 * u0)                                             # лезвие сужается к острию
        yaw = math.degrees(math.atan2(x1 - x0, z1 - z0))
        # брусок вдоль своей оси z, повёрнут по yaw; режущая кромка (тон 2) — внутренняя сторона дуги
        boxes.append([round(v, 3) for v in (mx - w / 2, -0.05, mz - seg / 2 - 0.02, mx + w / 2, 0.05, mz + seg / 2 + 0.02)] + [0, [0, round(yaw, 2), 0]])
        boxes.append([round(v, 3) for v in (mx - 0.04, -0.045, mz - seg / 2, mx + 0.04, 0.045, mz + seg / 2)] + [2, [0, round(yaw, 2), 0]])
    write('fx/meshes/t34_ghost_scythe.json', {
        'comment': 'T34 «Пепельная Жатва»: призрачная огненная коса Главы Культа (уменьшена под игрока, ~4 бл.). Точка привязки — хват у '
                   'заклинателя, древко по +z, лезвие загибается вправо и назад. Взмах — mesh.hinge.keys (поворот вокруг вертикали) в fx '
                   'ashen_harvest. Сгенерировано tools/gen_t34_reward.py.',
        'style': 'cult_leader', 'center': 0, 'formedAt': 6, 'collapse': {'duration': 6, 'easing': 'easeInCubic'},
        'parts': [{'type': 'boxes', 'tones': ['@primary', '#C04A18', '@secondary', '@core'], 'glowTones': [0, 1, 2, 3], 'blend': 'additive',
                   'opacity': 0.85, 'shade': False, 'boxes': boxes,
                   'appear': {'delay': 0, 'duration': 6, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.3}, 'bounds': [-0.1, 0.1]}]})


def mesh_banner():
    """Призрачное знамя Мартина для игрока (~3.2 бл.): древко, перекладина, кармин в золотой кайме, корона над мечом, ленты."""
    b = []
    H = 3.2
    b.append([-0.06, 0, -0.06, 0.06, H, 0.06, 1])                                # древко
    b.append([-0.1, H, -0.1, 0.1, H + 0.22, 0.1, 2])                             # навершие
    b.append([-0.95, H - 0.3, -0.05, 0.95, H - 0.2, 0.05, 2])                    # перекладина
    top, bot = H - 0.3, 0.95
    b.append([-0.85, bot, -0.02, 0.85, top, 0.02, 0])                           # полотнище
    for x0, x1, y0, y1 in ((-0.9, 0.9, top - 0.08, top), (-0.9, -0.82, bot, top), (0.82, 0.9, bot, top)):
        b.append([x0, y0, -0.035, x1, y1, 0.035, 2])                             # кайма
    for i in range(6):                                                             # зубцы низа
        x = -0.85 + 0.34 * i
        b.append([x + 0.02, bot - 0.25, -0.02, x + 0.15, bot, 0.02, 0])
    b.append([-0.28, 1.95, 0.025, 0.28, 2.08, 0.05, 3])                          # корона
    for dx in (-0.22, 0.0, 0.22):
        b.append([dx - 0.04, 2.08, 0.025, dx + 0.04, 2.24, 0.05, 3])
    b.append([-0.3, 1.72, 0.025, 0.3, 1.8, 0.05, 3])                             # гарда
    b.append([-0.04, 1.1, 0.025, 0.04, 1.72, 0.05, 3])                           # меч остриём вниз
    write('fx/meshes/t34_banner.json', {
        'comment': 'T34 «Знамя Полководца»: призрачное знамя Мартина под игрока (3.4 бл.): древко, кармин в золотой кайме, корона над мечом '
                   '(как его щиты). Полотнище — в плоскости XY, лицом по +z. Сгенерировано tools/gen_t34_reward.py.',
        'style': 'martin', 'center': 0, 'formedAt': 12, 'collapse': {'duration': 14, 'easing': 'easeInCubic'},
        'parts': [{'type': 'boxes', 'tones': ['#C04858', '#D8C8A8', '#F6D88A', '#FFF1C4'], 'glowTones': [2, 3], 'blend': 'translucent',
                   'opacity': 0.62, 'shade': True, 'boxes': b,
                   'appear': {'delay': 0, 'duration': 12, 'easing': 'easeOutCubic', 'reveal': 'up', 'front': 0.5}, 'bounds': [0.0, 3.45]}]})


def meshes():
    mesh_scythe()
    mesh_banner()


# ================================================================== fx
def E(type_, delay=0, at='caster', **kw):
    e = {'type': type_, 'delay': delay, 'at': at}
    e.update(kw)
    return e


def ease(d, e='easeOutCubic'):
    return {'duration': d, 'easing': e}


def fx(id_, comment, dur, els, style):
    write('fx/%s.json' % id_, {'comment': comment, 'style': style, 'duration': dur, 'elements': els})


# тайминги fx = тайминги анимаций игрока (tools/gen_t34_anims.py TIMING): тик 0 fx = тик 0 анимации
def effects():
    # ---------------------------------------------------------------- Пепельная Жатва (Глава Культа)
    # анимация pohsmp_ashen_harvest: замах 0–9, взмах 9–13 (пик/урон 11), перехлёст до 15, длина 40
    R = 4.0
    arc_pts = []
    for k in range(9):                                     # точки дуги 150° (справа налево), r 1.6..4
        a = math.radians(-75 + 150 * k / 8)
        arc_pts.append((round(-math.sin(a) * 1.0, 3), round(math.cos(a), 3), k))
    els = [
        E('mesh', 0, 'caster+0,1.0,0', model='t34_ghost_scythe', until=17, scale=1.0,
          hinge={'pivot': [0, 0, 0], 'axis': 'y', 'keys': [[0, 95, 'linear'], [9, 115, 'easeOutSine'], [11, 20, 'easeInQuad'],
                                                           [13, -75, 'easeOutQuad'], [17, -95, 'easeOutCubic']]},
          comment='коса справа-сзади (замах, +95…+115°: в MeshDraw угол + — к правой руке), взмах справа налево 9–13 (−75°), перехлёст'),
        E('sprites', 0, 'caster+0.6,1.0,-0.4', duration=10, texture='mote_flame', count=100000, rate=1.5, spread=0.4, speed=0.02,
          gravity=-0.02, size=[0.35, 0.05], life=12, color='@primary', glow=0.6, comment='огонь собирается у косы в замахе'),
        E('trail', 9, 'caster+0,1.0,%g' % R, shape='slash', radius=R, arc=150, thickness=0.5, bend=1, secondary=0.6, sweep=4, tail=0.6,
          roll=0, reverse=True, duration=12, color='@primary',
          comment='огненный серп взмаха r4, 150°: at — СЕРЕДИНА дуги (4 бл. впереди), центр дуги — у игрока'),
        E('slash', 10, 'caster+0,0.9,%g' % (R - 0.3), radius=R - 0.3, arc=150, thickness=0.28, bend=1, secondary=0.4, tilt=0, grow=3, life=10,
          dir=-1, color='@secondary'),
        E('flash', 11, 'caster+0,1.0,2.6', duration=8, size=2.6, rays=8, screen=0.08, color='@secondary'),
    ]
    for x, z, k in arc_pts:
        d = 11 + (k - 4) * 0.25
        els.append(E('sprites', int(round(max(9, d))), 'caster+%g,0.4,%g' % (round(x * 3.2, 2), round(z * 3.2, 2)), duration=3, texture='mote_flame',
                     count=8, rate=4, spread=0.5, speed=0.15, gravity=-0.02, size=[0.45, 0.06], life=14, color='@secondary', glow=0.6))
    fx('ashen_harvest', 'T34 «Пепельная Жатва» (caster = заклинатель, 30 тиков, тик 0 = анимация pohsmp_ashen_harvest): призрачная огненная '
       'коса Главы проходит дугой 150° r4 перед игроком. Урон — тик 11; на тике 12 — ashen_harvest_trail.', 30, els, 'cult_leader')
    els = []
    for x, z, k in arc_pts:
        els.append(E('decal', 0, 'caster+%g,0,%g' % (round(x * 2.8, 2), round(z * 2.8, 2)), duration=60, shape='crack', length=2.2, width=1.0,
                     grow=4, branches=4, yaw=round(math.degrees(math.atan2(x, z)), 1), blend='translucent', color='#1A0E0C', fadeOut=20))
        els.append(E('sprites', 2, 'caster+%g,0.1,%g' % (round(x * 2.8, 2), round(z * 2.8, 2)), duration=56, texture='mote_flame', count=100000,
                     rate=0.5, area=0.7, speed=0.01, gravity=-0.03, size=[0.4, 0.06], life=16, color='@secondary', glow=0.5))
        if k % 2 == 0:
            els.append(E('sprites', 2, 'caster+%g,0.3,%g' % (round(x * 2.8, 2), round(z * 2.8, 2)), duration=56, texture='mote_ash',
                         count=100000, rate=0.2, area=0.7, speed=0.01, gravity=-0.01, spin=30, size=[0.25, 0.08], life=30, color='#62514E',
                         blend='translucent'))
    els.append(E('decal', 0, 'caster+0,0,0', duration=60, texture='cult_scorch_ring', radius=4.2, glow=0.35, fadeOut=24, color='@primary',
                 brightness=0.5, comment='тлеющий сектор (кольцо — подсказка зоны)'))
    fx('ashen_harvest_trail', 'T34 «Пепельная Жатва»: пепельный след по дуге (caster = заклинатель в момент удара, 60 тиков = 3 с, не follow): '
       'выжженные трещины и огонь на дуге r1.6–4 перед ним. Зона урона — сектор 150° r4 (код).', 60, els, 'cult_leader')

    # ---------------------------------------------------------------- Объятия Ревности (Ирина)
    # анимация pohsmp_jealous_embrace: бросок нитей 0–7 (нити на цели — тик 6), захват 7–12, рывок 12–14 (тянуть 14–20),
    # замах крюком 20–24, удар 26, длина 44
    fx('jealous_embrace', 'T34 «Объятия Ревности»: нити опутывают цель (caster = ЦЕЛЬ, follow, 20 тиков, тик 6 анимации). '
       'Нити только вокруг цели — без нити от заклинателя (правило «никаких лучей»).', 20, [
        E('trail', 0, 'caster', duration=8, width=0.13, length=8, fade=1.2, head=0, count=4,
          orbit={'radius': 0.75, 'speed': 32, 'rise': 0.9, 'risePeriod': 10}, color='@primary', follow=True),
        E('trail', 2, 'caster+0,0.4,0', duration=6, width=0.1, length=6, fade=1.2, head=0, count=3,
          orbit={'radius': 0.55, 'speed': -26, 'rise': 0.6, 'risePeriod': 8}, color='@secondary', follow=True),
        E('decal', 0, 'caster', duration=20, texture='irina_thread_ring', radius=1.2, grow=6, glow=0.4, fadeOut=8, color='@primary', follow=True),
        E('sprites', 0, 'caster+0,1,0', duration=10, texture='mote_thread', count=40, rate=5, spread=0.7, speed=0.06, spin=30,
          size=[0.28, 0.08], life=16, color='@primary', follow=True),
        E('flash', 8, 'caster+0,1.1,0', duration=6, size=1.4, ring=True, color='@core', follow=True, comment='нити затянулись (тик 14 анимации)'),
    ], 'irina')
    fx('jealous_embrace_pull', 'T34 «Объятия Ревности»: рывок (caster = ЦЕЛЬ, follow, 8 тиков, тик 14 — код тянет 14–20): нити натянуты, '
       'красный шлейф за целью.', 8, [
        E('flash', 0, 'caster+0,1.1,0', duration=6, size=1.2, ring=True, color='@primary', follow=True),
        E('aura', 0, 'caster', target='caster', duration=8, thickness=0.06, pulse=[0.5, 2], motes=6, texture='mote_thread', ring=False,
          color='@primary', follow=True),
        E('sprites', 0, 'caster+0,1,0', duration=6, texture='mote_thread', count=100000, rate=3, spread=0.4, speed=0.02, spin=30,
          size=[0.24, 0.06], life=10, color='@primary', follow=True),
    ], 'irina')
    fx('jealous_embrace_hit', 'T34 «Объятия Ревности»: удар крюком посоха (caster = заклинатель, 14 тиков; тик 26 анимации = урон): '
       'серп наискось сверху справа вниз влево перед ним, красная вспышка, обрывки нитей.', 14, [
        E('slash', 0, 'caster+0,1.0,1.5', radius=1.5, arc=150, thickness=0.55, bend=1.2, secondary=0.5, tilt=55, grow=3, life=10, dir=-1,
          color='@primary', brightness=1.4),
        E('slash', 1, 'caster+0,1.0,1.3', radius=1.3, arc=120, thickness=0.16, bend=1.2, secondary=0, tilt=55, grow=3, life=8, dir=-1, color='@core'),
        E('flash', 1, 'caster+0,1.1,1.6', duration=7, size=1.6, rays=6, color='@primary'),
        E('sprites', 1, 'caster+0,1.1,1.6', duration=3, texture='mote_thread', count=22, rate=8, spread=0.5, speed=0.18, gravity=0.02,
          spin=40, size=[0.3, 0.08], life=16, color='@primary'),
    ], 'irina')
    fx('jealous_embrace_mark', 'T34 «Метка ревности» (caster = ЦЕЛЬ, follow, до Fx.stop; 5 с = 100 тиков): красный глаз-печать над головой '
       '(как irina_gaze_mark), нити медленно кружат.', -1, [
        E('sigil', 0, 'caster+0,2.3,0', follow=True, id='irina_gaze_eye', scale=0.7),
        E('trail', 0, 'caster+0,0.3,0', duration=-1, width=0.05, length=12, fade=1.2, head=0, count=2,
          orbit={'radius': 0.6, 'speed': 10, 'rise': 0.9, 'risePeriod': 30}, color='@primary', follow=True),
        E('sprites', 0, 'caster+0,1,0', duration=-1, texture='mote_heart', count=100000, rate=0.08, spread=0.6, speed=0.01, gravity=-0.006,
          size=[0.22, 0.08], life=30, color='@primary', follow=True),
    ], 'irina')

    # ---------------------------------------------------------------- Удар Наковальни (Арис)
    # анимация pohsmp_anvil_strike: замах 0–12, удар вниз 12–15.5, удар/урон 15, длина 40
    S = 0.22
    fx('anvil_strike_warn', 'T34 «Удар Наковальни»: прицел (caster = ТОЧКА УДАРА на земле, взгляд до 20 бл.; 12 тиков, тик 0 = анимация '
       'pohsmp_anvil_strike): кольцо-печать на земле, над точкой собирается призрачный бирюзовый молот Арис (aris_giant_hammer ×%g ≈ 3 бл.) '
       'и медленно опускается. Без луча от игрока. На тике 12 — anvil_strike.' % S, 12, [
        E('decal', 0, 'caster', duration=16, texture='aris_forge_ring', radius=3.0, grow=10, glow=0.5, fadeOut=4, color='@primary', brightness=0.7),
        E('mesh', 0, 'caster', model='aris_giant_hammer', scale=S, follow=False, until=12,
          move={'keys': [[0, [0, 27, 0], 'linear'], [12, [0, 24, 0], 'easeOutSine']]},
          comment='move.keys — в единицах меша (× scale 0.22): 27 ≈ 6 бл. над точкой'),
        E('sprites', 4, 'caster+0,5.5,0', duration=8, texture='spark_soft', count=100000, rate=0.8, area=0.8, speed=0.0, gravity=0.04,
          size=[0.16, 0.03], life=20, color='@primary', glow=0.9),
    ], 'aris')
    fx('anvil_strike', 'T34 «Удар Наковальни»: удар (caster = ТОЧКА УДАРА, 30 тиков; запуск на тике 12 каста): молот рушится за 3 тика, '
       '**удар/урон/отброс r3 — тик 3 этого fx = тик 15 каста**.', 30, [
        E('mesh', 0, 'caster', model='aris_giant_hammer', scale=S, follow=False, until=10,
          move={'keys': [[0, [0, 24, 0], 'linear'], [3, [0, 0, 0], 'easeInCubic']]}),
        E('flash', 3, 'caster+0,0.8,0', duration=10, size=3.2, rays=10, screen=0.12, color='@core', ring=True),
        E('wave', 3, 'caster', duration=16, shape='ring', radius=3.2, thickness=0.8, followTerrain=True, texture='aris_molten_ring', color='@secondary'),
        E('decal', 3, 'caster', duration=25, texture='aris_molten_floor', radius=1.4, glow=0.8, fadeOut=18, color='@secondary', brightness=1.1),
        E('decal', 3, 'caster', duration=25, texture='higher_cracks', radius=3.0, glow=0.6, fadeOut=18, color='@primary'),
        E('sprites', 3, 'caster+0,0.3,0', duration=3, texture='spark_soft', count=50, rate=17, spread=0.5, speed=0.4, gravity=0.03,
          size=[0.14, 0.02], life=18, color='@secondary', glow=0.9),
        E('sprites', 3, 'caster+0,0.2,0', duration=5, texture='mote_ash', count=16, rate=4, spread=1.0, speed=0.06, gravity=-0.004, spin=40,
          size=[0.5, 0.18], life=26, color='#60606C', blend='translucent'),
    ], 'aris')
    fx('anvil_strike_temper', 'T34 «Закалка» (caster = заклинатель, follow, до Fx.stop; 15 с): оружие в руке тлеет бирюзой — искры '
       'и раскалённые отблески у правой руки.', -1, [
        E('sprites', 0, 'caster.hand', duration=-1, texture='spark_soft', count=100000, rate=0.5, spread=0.15, speed=0.01, gravity=0.02,
          size=[0.1, 0.02], life=12, color='@primary', glow=0.9, follow=True),
        E('sprites', 0, 'caster.hand', duration=-1, texture='mote_flame', count=100000, rate=0.15, spread=0.1, speed=0.005, gravity=-0.01,
          size=[0.2, 0.04], life=10, color='@secondary', glow=0.5, follow=True),
        E('aura', 0, 'caster', target='caster', duration=-1, thickness=0.04, pulse=[0.4, 20], motes=0, ring=False, color='@primary',
          brightness=0.35, follow=True),
    ], 'aris')

    # ---------------------------------------------------------------- Знамя Полководца (Мартин)
    # анимация pohsmp_warlord_banner: подъём 0–10, вонзить 10–14 (тик 14 — знамя в земле), клич 22–28 (солдаты — тик 30), длина 48
    fx('warlord_banner', 'T34 «Знамя Полководца»: вонзить (caster = основание знамени — 1.3 бл. перед игроком, 30 тиков; тик 14 '
       'анимации): вспышка, волна r8, трещины, пыль.', 30, [
        E('flash', 0, 'caster+0,1.2,0', duration=12, size=2.2, rays=8, screen=0.05, color='@secondary', ring=True),
        E('wave', 0, 'caster', duration=20, shape='ring', radius=8, thickness=1.2, followTerrain=True, color='@primary'),
        E('decal', 0, 'caster', texture='higher_cracks', radius=1.8, glow=0.4, fadeOut=20, duration=30, color='@primary'),
        E('sprites', 0, 'caster+0,0.2,0', duration=5, texture='mote_ash', count=26, rate=6, area=1.0, speed=0.06, gravity=-0.002,
          size=[0.4, 0.8], life=28, color='#8A8070', blend='translucent'),
    ], 'martin')
    fx('warlord_banner_aura', 'T34 «Знамя Полководца» стоит (caster = основание, до Fx.stop; 20 с = 400 тиков): призрачное знамя t34_banner, '
       'золотое кольцо r8 на земле, искры. Союзникам в r8 — warlord_banner_buff.', -1, [
        E('mesh', 0, 'caster', model='t34_banner', scale=1.0, follow=True, duration=100000),
        E('decal', 0, 'caster', follow=True, texture='martin_banner_ring', radius=8, glow=0.25, pulse=30, grow=14, color='@primary', brightness=0.7),
        E('curtain', 0, 'caster', radius=[7.8, 8.0], count=40, height=0.9, grow=14, width=[0.05, 0.1], brightness=[0.25, 0.45],
          texture='beam_fade', flicker=0.3, color='@primary'),
        E('sprites', 0, 'caster+0,0.2,0', follow=True, texture='spark_soft', count=100000, rate=0.3, area=8, speed=0.02, gravity=-0.012,
          size=[0.14, 0.02], life=40, color='@secondary'),
        E('sprites', 0, 'caster+0,3.3,0', follow=True, texture='spark_soft', count=100000, rate=0.25, spread=0.3, speed=0.01, gravity=-0.008,
          size=[0.18, 0.03], life=30, color='@secondary', glow=0.6),
    ], 'martin')
    fx('warlord_banner_buff', 'T34: союзник под знаменем (caster = союзник, follow, до Fx.stop): золотой ореол.', -1, [
        E('aura', 0, 'caster', follow=True, target='caster', thickness=0.08, pulse=[0.3, 16], color='@primary', motes=6, ring=False,
          brightness=0.7),
    ], 'martin')
    fx('warlord_banner_soldier_spawn', 'T34: призрачный солдат встаёт у знамени (caster = солдат, 30 тиков; тик 30 анимации, два солдата '
       'слева и справа от знамени).', 30, [
        E('decal', 0, 'caster', duration=30, texture='martin_banner_ring', radius=1.0, grow=6, glow=0.4, fadeOut=14, color='@primary'),
        E('sprites', 0, 'caster+0,0.2,0', duration=14, texture='mote_wisp', count=20, rate=2.0, area=0.7, speed=0.03, gravity=-0.01,
          size=[0.5, 1.0], life=26, color='#8FD8F0', blend='translucent'),
        E('flash', 4, 'caster+0,1,0', duration=8, size=1.1, color='@secondary'),
    ], 'martin_ghost')
    fx('warlord_banner_soldier', 'T34: призрачный солдат знамени (caster = солдат, follow, до Fx.stop): голубой ореол, золотые искры.', -1, [
        E('aura', 0, 'caster', follow=True, target='caster', thickness=0.06, pulse=[0.3, 20], color='@primary', motes=4, ring=False, brightness=0.5),
    ], 'martin_ghost')
    fx('warlord_banner_soldier_vanish', 'T34: солдат уходит со знаменем (caster = солдат, 20 тиков).', 20, [
        E('sprites', 0, 'caster+0,1,0', duration=10, texture='mote_wisp', count=26, rate=4, spread=0.5, speed=0.04, gravity=-0.012,
          size=[0.5, 1.0], life=22, color='#8FD8F0', blend='translucent'),
        E('sprites', 0, 'caster+0,1,0', duration=6, texture='spark_soft', count=16, rate=4, spread=0.4, speed=0.1, gravity=-0.01,
          size=[0.12, 0.02], life=14, color='@secondary'),
    ], 'martin_ghost')
    fx('warlord_banner_fall', 'T34: знамя исчезает (caster = основание, 24 тика; на 0 — Fx.stop warlord_banner и всех warlord_banner_buff).', 24, [
        E('sprites', 0, 'caster+0,1.6,0', duration=10, texture='spark_soft', count=40, rate=4, spread=0.8, speed=0.05, gravity=0.01,
          size=[0.16, 0.02], life=20, color='@primary'),
        E('wave', 0, 'caster', duration=18, shape='ring', radius=8, thickness=0.8, followTerrain=True, reverse=True, color='@primary', brightness=0.6),
        E('flash', 0, 'caster+0,1.6,0', duration=8, size=1.4, color='@secondary'),
    ], 'martin')

    # ---------------------------------------------------------------- Шаг сквозь отражение (Эреб)
    # анимация pohsmp_mirror_step: шаг в рябь 0–4 (тик 4 — исчезает, телепорт за спину цели), сжатие 4–7, укол 7–9 (урон 8), длина 28;
    # невидимость с тика 10
    fx('mirror_step_vanish', 'T34 «Шаг сквозь отражение»: уход в рябь (caster = заклинатель на старом месте, 14 тиков; тик 0 анимации, '
       'на тике 4 — телепорт): стеклянная рябь-сфера, осколки, бабочки.', 14, [
        E('wave', 0, 'caster+0,1,0.3', duration=6, shape='sphere', radius=1.0, rim=1.0, color='@secondary', brightness=0.6),
        E('wave', 3, 'caster+0,1,0', duration=8, shape='sphere', radius=1.3, rim=1.2, color='#E8FAFF', brightness=0.5),
        E('aura', 0, 'caster', target='caster', duration=5, thickness=0.06, pulse=[0.6, 2], motes=0, ring=False, color='#E8FAFF',
          brightness=0.6, in_=None),
        E('sprites', 4, 'caster+0,1,0', duration=2, texture='mote_glass', count=14, rate=8, spread=0.5, speed=0.07, gravity=0.006, spin=140,
          tumble=True, size=[0.18, 0.05], life=12, color='#E8FAFF'),
        E('sprites', 4, 'caster+0,1.2,0', duration=2, texture='mote_butterfly', count=5, rate=3, spread=0.4, speed=0.06, gravity=-0.01,
          sway=0.6, size=[0.3, 0.1], life=20, color='#BFE6FF', glow=0.4),
        E('flash', 4, 'caster+0,1.1,0', duration=5, size=1.0, color='#FFFFFF', brightness=0.7),
    ], 'ereb')
    fx('mirror_step_appear', 'T34 «Шаг сквозь отражение»: выход из ряби за спиной цели (caster = заклинатель на новом месте, 10 тиков, тик 4).', 10, [
        E('wave', 0, 'caster+0,1,0', duration=7, shape='sphere', radius=0.9, rim=1.0, color='@secondary', brightness=0.6),
        E('flash', 0, 'caster+0,1.1,0', duration=4, size=0.9, color='#FFFFFF', brightness=0.7),
        E('sprites', 0, 'caster+0,1,0', duration=2, texture='mote_glass', count=10, rate=8, spread=0.45, speed=0.05, gravity=0.006, spin=140,
          tumble=True, size=[0.16, 0.05], life=10, color='#E8FAFF'),
    ], 'ereb')
    fx('mirror_step', 'T34 «Шаг сквозь отражение»: укол рапирой (caster = ЦЕЛЬ, 10 тиков, тик 8 = урон): золотая искра в спине, '
       'стеклянная трещина.', 10, [
        E('flash', 0, 'caster+0,1.3,0', duration=5, size=0.7, anamorphic=1.4, rays=4, color='#FFE7A0', brightness=1.1),
        E('sprites', 0, 'caster+0,1.3,0', duration=1, texture='spark_soft', count=8, rate=8, spread=0.15, speed=0.08, gravity=0.01,
          size=[0.1, 0.02], life=8, color='#E8B84A'),
        E('sprites', 0, 'caster+0,1.3,0', duration=2, texture='mote_glass', count=8, rate=6, spread=0.3, speed=0.06, gravity=0.01, spin=140,
          tumble=True, size=[0.14, 0.04], life=10, color='#E8FAFF'),
    ], 'ereb')
    fx('mirror_step_veil', 'T34 «Шаг сквозь отражение»: заклинатель растворяется (caster = заклинатель, 12 тиков, тик 10; дальше 2 с '
       'невидимости — код).', 12, [
        E('aura', 0, 'caster', target='caster', duration=10, thickness=0.06, pulse=[0.5, 3], motes=0, ring=False, color='#BFE6FF', brightness=0.5),
        E('sprites', 2, 'caster+0,1.0,0', duration=3, texture='mote_glass', count=10, rate=6, spread=0.5, speed=0.04, gravity=0.004, spin=140,
          tumble=True, size=[0.16, 0.05], life=12, color='#E8FAFF'),
    ], 'ereb')

    # ---------------------------------------------------------------- Длань Лжи
    # анимация pohsmp_hand_of_lies: рука вверх-вперёд ладонью к цели 0–8, хват (кулак) 10, сжатие 10–30, длина 40
    HS = 0.5
    fx('hand_of_lies', 'T34 «Длань Лжи» (caster = ЦЕЛЬ, 24 тика; тик 0 = анимация pohsmp_hand_of_lies): стеклянная рука (ereb_hand_giant ×%g '
       '≈ 3.5 бл.) раскрытой ладонью опускается на цель и на тике 10 сжимается в кулак. Дальше — hand_of_lies_hold.' % HS, 24, [
        E('decal', 0, 'caster', duration=12, texture='illusion_seal', radius=1.6, grow=10, glow=0.2, fadeOut=4, color='#D9CCFF', brightness=0.5,
          comment='тень ладони'),
        E('mesh', 0, 'caster+0,1.5,-0.9', model='ereb_hand_giant_open', scale=HS, until=10,
          move={'from': [0, 8, 0], 'scaleFrom': 0.6, 'delay': 0, 'duration': 10, 'easing': 'easeInCubic'},
          comment='from — в единицах меша (× scale): 8 ≈ 4 бл. над целью'),
        E('flash', 10, 'caster+0,1.0,0', duration=8, size=1.6, rays=8, color='#FFFFFF', brightness=1.2),
        E('sprites', 10, 'caster+0,1.2,0', duration=2, texture='mote_glass', count=18, rate=18, spread=0.8, speed=0.08, gravity=0.02, spin=140,
          tumble=True, size=[0.16, 0.05], life=18, color='#F4EEFF'),
        E('wave', 10, 'caster+0,0.05,0', duration=12, shape='ring', radius=2.5, color='@secondary', brightness=0.6),
    ], 'ereb_hand')
    fx('hand_of_lies_hold', 'T34 «Длань Лжи»: держит (caster = ЦЕЛЬ, follow, до Fx.stop; 2.5 с, в PvP 1.5 с): стеклянный кулак вокруг цели, '
       'стеклянная оболочка, золотые блёстки.', -1, [
        E('mesh', 0, 'caster+0,1.5,-0.9', model='ereb_hand_giant_fist', scale=HS, follow=True, duration=100000),
        E('aura', 0, 'caster', target='caster', follow=True, duration=100000, thickness=0.05, pulse=[0.5, 12], motes=4, texture='mote_glass',
          ring=False, color='#D9CCFF', brightness=0.5),
        E('sprites', 0, 'caster+0,1.6,0', duration=100000, texture='mote_glass', count=100000, rate=0.2, spread=0.5, speed=0.0, gravity=0.01,
          spin=140, tumble=True, size=[0.12, 0.04], life=16, color='#F4EEFF', follow=True),
    ], 'ereb_hand')
    fx('hand_of_lies_release', 'T34 «Длань Лжи»: кулак разбивается (caster = ЦЕЛЬ, 30 тиков; на 0 — Fx.stop hand_of_lies_hold): осколки, '
       'бабочки.', 30, [
        E('flash', 0, 'caster+0,1.2,0', duration=6, size=1.4, color='#FFFFFF', brightness=1.0),
        E('sprites', 0, 'caster+0,1.2,0', duration=2, texture='mote_glass', count=26, rate=26, spread=0.9, speed=0.14, gravity=0.03, spin=140,
          tumble=True, size=[0.2, 0.06], life=20, color='#F4EEFF'),
        E('sprites', 2, 'caster+0,1.6,0', duration=2, texture='mote_butterfly', count=10, rate=10, spread=0.8, speed=0.06, gravity=-0.01,
          sway=0.6, size=[0.3, 0.1], life=26, color='#D9CCFF', glow=0.45),
    ], 'ereb_hand')
    fx('hand_of_lies_slow', 'T34 «Длань Лжи» по боссу (caster = босс, follow, до Fx.stop; 2.5 с): рука не держит — стеклянные пальцы '
       'скользят по ногам, осколки кружат у земли (замедление).', -1, [
        E('decal', 0, 'caster', follow=True, texture='illusion_seal', radius=1.6, glow=0.25, spin=2, color='#D9CCFF', brightness=0.5),
        E('trail', 0, 'caster+0,0.3,0', duration=-1, width=0.06, length=10, fade=1.2, head=0, count=3,
          orbit={'radius': 0.9, 'speed': 14, 'rise': 0.2, 'risePeriod': 20}, color='@secondary', follow=True),
        E('sprites', 0, 'caster+0,0.4,0', duration=-1, texture='mote_glass', count=100000, rate=0.3, area=1.0, speed=0.0, gravity=0.005,
          spin=140, tumble=True, size=[0.14, 0.04], life=16, color='#F4EEFF', follow=True),
    ], 'ereb_hand')


def _clean(o):
    """Убрать служебные поля со значением None (in_=None выше — заготовка)."""
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items() if v is not None and k != 'in_'}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o


def main(args):
    global fx
    _fx = fx

    def fx_clean(id_, comment, dur, els, style):
        _fx(id_, comment, dur, _clean(els), style)
    fx = fx_clean
    scrolls()
    icons()
    meshes()
    effects()
    lang()
    if '--sheet' in args:
        compare_sheet()
    for w in WRITTEN:
        print('wrote', w)


if __name__ == '__main__':
    main(sys.argv[1:])
