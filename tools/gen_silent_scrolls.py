#!/usr/bin/env python3
"""
Свитки безмолвных заклинаний (владелец 19.11: «сделай для безмолвных заклинаний свитки», кроме Врат):
textures/item/scroll_<spell>.png 32×32 + models/item/scroll_<spell>.json. Каркас — как у scroll_space_closure (те же ролики и рваные края),
цвета школы Безмолвной ведьмы: тёмно-синие ролики с золотыми кольцами и бирюзовыми камнями, бледно-мятная бумага, бирюзовая эмблема.
Эмблемы: sage_barrier — купол-шестигранник; wind_spears — три копья ветра наискось; silent_volley — веер малых печатей;
worgan_flame — тёмное пламя дракона с глазом. Запуск: python3 tools/gen_silent_scrolls.py
"""
import json, os
from PIL import Image

A = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
h = lambda s: (int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16), 255)

ROD = ["AAAAAAAAAAAAAAAAAAAAAAAAAA",
       "ABACCCCCCCCCCCCCCCCCCCCABA",
       "DEDFFFGFFFGFFFGFFFGFFFFDED",
       "HEHDDDDDDDDDDDDDDDDDDDDHEH",
       "AIAHHHHHHHHHHHHHHHHHHHHAIA",
       "AAAAAAAAAAAAAAAAAAAAAAAAAA"]
# бумага строки 9..22: (левый край x, правый край x) — как у образца
PAPER = [(7, 25), (7, 24), (8, 24), (8, 24), (7, 23), (7, 23), (6, 24), (6, 24), (7, 24), (7, 25), (7, 24), (8, 24), (8, 24), (7, 23)]
ROD_PAL = {'A': '#070B1A', 'B': '#FFE9A8', 'C': '#2A3458', 'D': '#141A30', 'E': '#45E0C8', 'F': '#1E2644', 'G': '#D8A93E', 'H': '#0B0F1E', 'I': '#1C7A70'}
EDGE, SHADE1, SHADE2, BASE, LIGHT = h('#070B1A'), h('#5E8F8A'), h('#9CC7C0'), h('#D6EEE8'), h('#EEF9F6')
INK = {'1': h('#14564F'), '2': h('#1F8C7E'), '3': h('#13A893'), '4': h('#0A3F3A'), '5': h('#D8A93E'), '6': h('#3A1E5A'), '7': h('#7A3FC0'), '8': h('#0E1430')}

EMBLEMS = {
    'sage_barrier': [
        "......3333......",
        "....33....33....",
        "...3..2222..3...",
        "..3..2....2..3..",
        "..3.2..44..2.3..",
        ".3..2.4334.2..3.",
        ".3..2..44..2..3.",
        ".1222222222222..",
        "..1111111111111.",
        "................"],
    'wind_spears': [
        "..........4.....",
        ".........3..4...",
        "....4...3..3....",
        "...3...2..3...4.",
        "..3...2..2...3..",
        ".2...1..2...3...",
        "1...1..1...2....",
        "...1..1...2.....",
        "..1...1..1......",
        ".....1..1......."],
    'silent_volley': [
        "....5........5..",
        "...323......323.",
        "....5...5....5..",
        "...5...323...5..",
        "..323...5...323.",
        "...5....3....5..",
        ".......2.2......",
        "......2.4.2.....",
        ".......2.2......",
        "........1......."],
    'worgan_flame': [
        ".....7....7.....",
        "....77...76.....",
        "...767..767.....",
        "...7667.6677....",
        "..76666666667...",
        "..7663366666....",
        ".76634366667....",
        ".7666336666667..",
        "..76666666667...",
        "...777777777...."],
}


def make(name):
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    for y0 in (3, 23):
        for dy, row in enumerate(ROD):
            for dx, c in enumerate(row):
                im.putpixel((3 + dx, y0 + dy), h(ROD_PAL[c]))
    for i, (l, r) in enumerate(PAPER):
        y = 9 + i
        for x in range(l, r + 1):
            if x in (l, r):
                c = EDGE
            elif x == l + 1:
                c = SHADE1
            elif x == l + 2:
                c = SHADE2
            elif (x + y * 3) % 11 == 0:
                c = LIGHT
            else:
                c = BASE
            im.putpixel((x, y), c)
    for x in range(8, 24):                       # тень под верхним роликом
        if im.getpixel((x, 9))[3]:
            im.putpixel((x, 9), SHADE2)
    em = EMBLEMS[name]
    ox, oy = 8, 11
    for dy, row in enumerate(em):
        for dx, c in enumerate(row):
            if c != '.' and im.getpixel((ox + dx, oy + dy))[3]:
                im.putpixel((ox + dx, oy + dy), INK[c])
    for x in range(9, 23, 3):                    # строка «текста» внизу
        if im.getpixel((x, 21))[3]:
            im.putpixel((x, 21), INK['1']); im.putpixel((x + 1, 21), INK['2'])
    im.save(os.path.join(A, 'textures', 'item', f'scroll_{name}.png'))
    with open(os.path.join(A, 'models', 'item', f'scroll_{name}.json'), 'w', encoding='utf-8') as f:
        json.dump({'parent': 'item/generated', 'textures': {'layer0': f'pohsmp_core:item/scroll_{name}'}}, f, indent=2)
        f.write('\n')
    print('wrote scroll_%s' % name)


if __name__ == '__main__':
    for n in EMBLEMS:
        make(n)
