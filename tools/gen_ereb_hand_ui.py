#!/usr/bin/env python3
"""
T31 «Эреб, Длань Лжи» — полоса здоровья по фазам, титры, lang; вызывается из tools/gen_ereb_hand.py (run(M, args)).
Форматы — как у T26/T30: полоса 192×36 (формат tyros_bossbar: строки 0–17 пустая, 18–35 полная) + _flash 192×18; титры 1024×192.
Отрисовка титров — та же, что у T30 (tools/gen_ereb_fx.py: title_img, шрифт Cormorant), сами функции T30 только вызываются.
"""
import json
import os

import numpy as np
from PIL import Image

import gen_ereb_fx as FX

M = None
MEDIA = FX.MEDIA

# центральные знаки полос 15×7
EMB = ['.......r.......',
       '...r..rsr..r...',
       '..rs.rsLsr.sr..',
       '.rsrrsLOLsrrsr.',
       '..rssLOtOLssr..',
       '...rrsLOLsrr...',
       '.....rrrrr.....']
HAND = ['....h.h.h......',
        '....h.h.h.h....',
        '..h.nhnhnhh....',
        '...hnhhhhhh....',
        '....hhhhhhh....',
        '.....ghhhg.....',
        '......ggg......']
MASK = ['..rrrrrrrrrrr..',
        '.rsssszssssssr.',
        '.rsaaaszsaaasr.',
        '.rssssszsssssr.',
        '..rsssszssssr..',
        '...rrsszsssr...',
        '.....rrzrr.....']
COL = {'r': '#d0952a', 's': '#f8d260', 't': '#fff2b0', 'L': '#3a0d16', 'O': '#a3323b', 'a': '#0b0a0f', 'h': '#8eaeee', 'n': '#e6efff',
       'g': '#4a64b8', 'z': '#fff8d4', 'o': '#704612'}
FILL = {1: ['#f8d260', '#c95560', '#a3323b', '#7e1f2b', '#5c1420'],          # «Лживое слово»: багрянец под золотой кромкой
        2: ['#e6efff', '#8eaeee', '#4a64b8', '#28316a', '#1a1f48'],          # «Длань»: призрачное стекло
        3: ['#fff2b0', '#eab33c', '#c95560', '#7e1f2b', '#3a0d16']}          # «Глава Культа»: пламя Меллисто, золото в трещинах
EMPTY = ['#3a0d16', '#29252f', '#1d1a24', '#14121a', '#0b0a0f']
NAMES = {1: 'ereb_hand_bossbar', 2: 'ereb_hand_bossbar_p2', 3: 'ereb_hand_bossbar_p3'}


def _art(img, art, x0, y0):
    for j, r in enumerate(art):
        for i, ch in enumerate(r):
            if ch != '.':
                img.putpixel((x0 + i, y0 + j), M.hx(COL[ch]))


def bossbar(phase):
    src = M.jar_img(M.I + 'textures/gui/sprites/boss_bars/tyros_bossbar.png')
    a = np.asarray(src).copy()
    for half in (0, 18):
        a[half:half + 7, :] = 0
        for y in range(half + 7, half + 12):
            a[y, 88:104] = a[y, 80]
    img = Image.fromarray(a, 'RGBA').copy()
    px = img.load()
    for half, ramp in ((0, EMPTY), (18, FILL[phase])):
        rows = sorted({y for y in range(half, half + 18) for x in range(192) if px[x, y][3] and px[x, y][0] > px[x, y][1] + 40})
        for x in range(192):
            for y in range(half, half + 18):
                r, g, b, al = px[x, y]
                if al and r > g + 40:
                    k = rows.index(y) if y in rows else 0
                    c = ramp[min(len(ramp) - 1, int(k * len(ramp) / max(1, len(rows))))]
                    if half == 18 and phase == 2 and (x * 5 + y * 3) % 29 == 0:
                        c = '#ffffff'                                  # блики стекла
                    if half == 18 and phase == 3 and (x * 7 + y * 3) % 23 == 0:
                        c = '#fff2b0'                                  # искры пламени
                    px[x, y] = M.hx(c)
    for half in (0, 18):
        _art(img, {1: EMB, 2: HAND, 3: MASK}[phase], 96 - 7, half + 0)
        # филигрань: золотая цепь от знака к краям (как застёжка накидки), багряные бусины
        for sgn in (-1, 1):
            for dx in range(9, 50):
                x = 96 + sgn * dx - (1 if sgn < 0 else 0)
                img.putpixel((x, half + 5), M.hx(COL['s' if dx % 2 else 'r'] if dx < 34 else COL['o']))
            for dx, ch in ((15, 'O'), (25, 'O'), (35, 's')):
                x = 96 + sgn * dx - (1 if sgn < 0 else 0)
                img.putpixel((x, half + 4), M.hx(COL[ch]))
                img.putpixel((x, half + 6), M.hx(COL['r']))
        if phase >= 2:   # трещины по рамке (стекло), в фазе 3 — шире
            for cx in ((44, 140) if phase == 2 else (24, 44, 63, 130, 148, 168)):
                for (dx, dy) in ((0, 7), (1, 8), (1, 9), (0, 10), (1, 11), (2, 12)):
                    x, y = cx + dx, half + dy
                    if px[x, y][3]:
                        px[x, y] = M.hx('#fff8d4' if phase == 3 else '#e6efff')
    return img


def bossbars():
    bars = {}
    for p, nm in NAMES.items():
        im = bossbar(p)
        im.save(M.out('textures/gui/sprites/boss_bars/%s.png' % nm))
        bars[p] = im
    full = np.asarray(bars[1].crop((0, 18, 192, 36))).copy()
    m = full[..., 3] > 0
    fl = np.zeros_like(full)
    fl[m] = M.hx('#fff2e0')
    Image.fromarray(fl, 'RGBA').save(M.out('textures/gui/sprites/boss_bars/ereb_hand_bossbar_flash.png'))
    return bars


TITLES = {'': ('Эреб, Длань Лжи', 'Глава Культа Меллисто', 'Ereb, the Hand of Lies', 'Head of the Cult of Mellisto'),
          'hand_of_lies': ('Длань Лжи', None, 'The Hand of Lies', None),
          'mask_fall': ('Падение маски', None, 'The Mask Falls', None),
          'full_reveal': ('Сон Бабочки: Полное Раскрытие', None, 'Butterfly Dream: Full Revelation', None)}


def titles(bars):
    FX.M = M
    mark = bars[1].crop((89, 0, 104, 7)).resize((45, 21), Image.NEAREST)
    for key, (ru, ru_sub, en, en_sub) in TITLES.items():
        nm = 'ereb_hand' + ('_' + key if key else '')
        FX.title_img(ru, FX.CYR, ru_sub, FX.CYR, mark).save(M.out('textures/gui/title/%s_ru.png' % nm))
        FX.title_img(en, FX.LAT, en_sub, FX.LAT, mark).save(M.out('textures/gui/title/%s_en.png' % nm))


LANG = {
    'entity.pohsmp_core.ereb_hand': ('Эреб, Длань Лжи', 'Ereb, the Hand of Lies'),
    'item.pohsmp_core.ereb_hand_rapier': ('Стеклянная рапира Эреба', 'Ereb\'s Glass Rapier'),
    'ui.pohsmp_core.ereb_hand.title': ('Эреб, Длань Лжи', 'Ereb, the Hand of Lies'),
    'ui.pohsmp_core.ereb_hand.epithet': ('Глава Культа Меллисто', 'Head of the Cult of Mellisto'),
    'ui.pohsmp_core.ereb_hand.spawn': ('Вот мы и снова встретились', 'So we meet again'),
    'ui.pohsmp_core.ereb_hand.defeat': ('А вы...стали сильнее', 'You... have grown stronger'),
    'ui.pohsmp_core.ereb_hand.replica': ('Ложь во лжи - Становится правдой сама по себе', 'A lie within a lie becomes the truth by itself'),
    'ui.pohsmp_core.ereb_hand.phase1': ('«Лживое слово»', '"The Lying Word"'),
    'ui.pohsmp_core.ereb_hand.phase2': ('«Длань» — рука хватает. Бейте по руке, чтобы освободить союзника.',
                                        '"The Hand" — it grabs. Strike the hand to free your ally.'),
    'ui.pohsmp_core.ereb_hand.phase3': ('«Глава Культа» — маска трескается.', '"Head of the Cult" — the mask cracks.'),
    'ui.pohsmp_core.ereb_hand.hand_of_lies': ('Длань Лжи', 'The Hand of Lies'),
    'ui.pohsmp_core.ereb_hand.mask_fall': ('Падение маски', 'The Mask Falls'),
    'ui.pohsmp_core.ereb_hand.full_reveal': ('Сон Бабочки: Полное Раскрытие', 'Butterfly Dream: Full Revelation'),
    'ui.pohsmp_core.ereb_hand.vanish': ('Эреб рассыпался бабочками. Бой окончен.', 'Ereb scattered into butterflies. The battle is over.'),
    'death.attack.pohsmp_core.ereb_hand_finisher': ('%1$s раздавлен Дланью Лжи', '%1$s was crushed by the Hand of Lies'),
}


def lang():
    for i, name in enumerate(('ru_ru', 'en_us')):
        p = os.path.join(M.A, 'lang', name + '.json')
        d = json.load(open(p, encoding='utf-8'))
        for k, v in LANG.items():
            d[k] = v[i]
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write('\n')
        M.WRITTEN.append('lang/%s.json (+%d ключей)' % (name, len(LANG)))


def sheet_ui(bars):
    from PIL import ImageDraw
    Wd, Hd = 1600, 1180
    img = Image.new('RGBA', (Wd, Hd), M.hx('#16151b'))
    d = ImageDraw.Draw(img)
    f1, f2 = FX.font(24), FX.font(18)
    d.text((24, 14), 'T31 — полоса «Эреба, Длани Лжи» по фазам (×4) и титры ru/en', font=f1, fill=(240, 230, 210))

    def bar_at(src, x, y, p):
        e = src.crop((0, 0, 192, 18))
        f = src.crop((0, 18, 192, 36))
        w = int(3 + p * (192 - 6))
        e.alpha_composite(f.crop((0, 0, w, 18)), (0, 0))
        img.alpha_composite(e.resize((192 * 4, 72), Image.NEAREST), (x, y))
    rows = [(bars[1], 0.85, 'фаза 1 «Лживое слово» (100–66%) — 85%: багрянец, знак Меллисто'),
            (bars[2], 0.5, 'фаза 2 «Длань» (66–33%) — 50%: стекло, призрачная рука'),
            (bars[3], 0.25, 'фаза 3 «Глава Культа» (33–0%) — 25%: пламя, треснувшая маска')]
    for i, (b, p, lab) in enumerate(rows):
        bar_at(b.copy(), 24, 60 + i * 96, p)
        d.text((24 + 192 * 4 + 20, 84 + i * 96), lab, font=f2, fill=(210, 200, 185))
    fl = Image.open(os.path.join(M.A, 'textures/gui/sprites/boss_bars/ereb_hand_bossbar_flash.png')).convert('RGBA')
    img.alpha_composite(fl.resize((192 * 4, 72), Image.NEAREST), (24, 352))
    d.text((24 + 192 * 4 + 20, 376), 'ereb_hand_bossbar_flash — вспышка смены фазы', font=f2, fill=(210, 200, 185))
    for i, lang_ in enumerate(('ru', 'en')):
        t = Image.open(os.path.join(M.A, 'textures/gui/title/ereb_hand_%s.png' % lang_)).convert('RGBA')
        bg = Image.new('RGBA', (1024, 192), M.hx('#2a2833'))
        bg.alpha_composite(t)
        img.alpha_composite(bg.resize((768, 144)), (24, 450 + i * 160))
    for i, k in enumerate(('hand_of_lies_ru', 'mask_fall_ru', 'full_reveal_ru', 'hand_of_lies_en', 'mask_fall_en', 'full_reveal_en')):
        t = Image.open(os.path.join(M.A, 'textures/gui/title/ereb_hand_%s.png' % k)).convert('RGBA')
        bg = Image.new('RGBA', (1024, 192), M.hx('#2a2833'))
        bg.alpha_composite(t)
        img.alpha_composite(bg.resize((512, 96)), (820 + (i // 3) * 0, 450 + i * 112) if False else (24 + (i % 3) * 520, 800 + (i // 3) * 120))
    d.text((24, 1050), 'Особые: «Длань Лжи», «Падение маски», «Сон Бабочки: Полное Раскрытие» (ru/en). Показ — как у T30: вход 0.5 с, уход 0.75 с.',
           font=f2, fill=(210, 200, 185))
    img.convert('RGB').save(os.path.join(MEDIA, 't31_ui.jpg'), quality=92)
    print('wrote docs/media/t31_ui.jpg')


def run(mod, args):
    global M
    M = mod
    FX.M = mod
    bars = bossbars()
    titles(bars)
    lang()
    os.makedirs(MEDIA, exist_ok=True)
    sheet_ui(bars)
    if '--shots' in args:
        import gen_ereb_hand_shots as SH
        SH.shots(M, args)
    if '--html' in args:
        import gen_ereb_hand_render as R
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ereb_hand_preview.html'), 'w', encoding='utf-8') as fh:
            fh.write(R.page(['ereb_hand', 'ereb', 'cult_leader']))
        print('wrote tools/ereb_hand_preview.html')
