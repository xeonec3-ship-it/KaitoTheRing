#!/usr/bin/env python3
"""
Иконки комплекта безмолвной ведьмы (T19) по палитре одежды (tools/gen_silent_outfit.py):
  textures/item/silent_witch_hood.png, _robe.png, _skirt.png   — 16×16
  textures/mob_effect/silent_barrier_cooldown.png               — 18×18 («Барьер восстанавливается»)
Форма — левая половина ASCII (8 столбцов), зеркалится; свет сверху-справа, контур — тёмный тон материала.
Запуск: python3 tools/gen_silent_icons.py
"""
import math
import os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'textures')
PAL = {
    'C': ['#0E0D14', '#17171F', '#22222C', '#2E2E3A', '#3C3C4B', '#4E4E60'],   # ткань
    'L': ['#2A0A12', '#3A0F1A', '#4E1624', '#621E2E', '#782838', '#8E3446'],   # подклад
    'S': ['#1C1F28', '#262A36', '#30353F', '#3C4250', '#4A5060', '#5A6172'],   # рукава
    'T': ['#4E380C', '#6E5014', '#946E24', '#B8923A', '#D6B25A', '#F2DA8E'],   # золото
    'G': ['#1A4024', '#245A30', '#2E7440', '#3C8E50', '#52A866', '#72C284'],   # лента
    'D': ['#050408', '#08070C', '#0B0A10', '#0E0D14', '#121019', '#16141C'],   # тень в капюшоне
}
FLAT = {'D'}


def hexc(h, a=255):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)


def shape(half):
    rows = [r + r[::-1] for r in half]
    assert all(len(r) == 16 for r in rows), [len(r) for r in rows]
    return rows


def paint(rows, out, extra=None):
    n = len(rows)
    im = Image.new('RGBA', (16, n), (0, 0, 0, 0))
    filled = lambda x, y: 0 <= x < 16 and 0 <= y < n and rows[y][x] != '.'
    for y in range(n):
        for x in range(16):
            m = rows[y][x]
            if m == '.':
                continue
            ramp = PAL[m]
            if m in FLAT:
                i = 1 + (y > 8)
            else:
                i = 3 + (x >= 10) - (x <= 4) - (y >= 13 and m == 'C')
                if not filled(x, y - 1) or rows[y - 1][x] != m:
                    i += 1                                     # верхняя кромка ловит свет
                if not filled(x + 1, y) and x >= 8:
                    i += 1                                     # правый край освещён
            if not all(filled(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                i = 0 if not (x >= 9 and not filled(x, y - 1)) else max(1, i - 2)   # контур
            im.putpixel((x, y), hexc(ramp[max(0, min(5, i))]))
    if extra:
        extra(im)
    im.save(os.path.join(TEX, out))
    print('wrote', out)


HOOD = shape([
    '........',
    '......CC',
    '....CCCC',
    '...CCCCC',
    '..CCCCTT',
    '..CCCTLL',
    '.CCCTLDD',
    '.CCCTLDD',
    '.CCCTLDD',
    '.CCCTLDD',
    'CCCCTLLD',
    'CCCCCTTT',
    'CCCCCCGT',
    'CCCCCGGC',
    'CCCCCGCC',
    'TTTTTTTT',
])
ROBE = shape([
    '......CC',
    '....CCLL',
    '...CCCTG',
    '..CCCCTG',
    '.CCCCCCT',
    'CCCCCCCT',
    'CCCCCCCT',
    'TTTTCCCT',
    '.SSSCCCT',
    '.SSSCCCT',
    '.SSSCCCT',
    '.TTCCCCT',
    '..CCCCCT',
    '.CCCCCCT',
    '.CCCCCCT',
    '.TTTTTTT',
])
SKIRT = shape([
    '........',
    '........',
    '....GGGG',
    '....CCCC',
    '...CCCCC',
    '...CCCCC',
    '...CCCCC',
    '..CCCCCC',
    '..CCCCCC',
    '..CCCCCL',
    '.CCCCCCL',
    '.CCCCCCL',
    'CCCCCCLL',
    'TTTTTTLL',
    'CCCCCCLL',
    'TTTTTTTT',
])


def hood_eyes(im):
    # в темноте капюшона — два едва заметных бирюзовых блика (взгляд ведьмы)
    for x in (6, 9):
        im.putpixel((x, 8), hexc('#5FC8A8'))


def robe_bow(im):
    # бант ленты на горле
    for x, y, c in ((6, 3, '#52A866'), (9, 3, '#52A866'), (7, 4, '#72C284'), (8, 4, '#3C8E50'), (6, 4, '#2E7440'), (9, 4, '#2E7440')):
        im.putpixel((x, y), hexc(c))


def skirt_glow(im):
    # кайма светится бирюзой (как ночью в игре): точки на нижнем поясе
    for x in range(1, 15, 3):
        im.putpixel((x, 15), hexc('#B8F5E0'))


def barrier_icon():
    """18×18: печать-барьер восстанавливается — бирюзовый круг заполнен на 3/4, голова дуги ярко светится, внутри шестигранник."""
    S = 18
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    cx = cy = 8.5
    ring = ['#1E4A44', '#2E7A6A', '#4FBF9F', '#7FFFD0', '#CFFFF0', '#FFFFFF']
    head = math.radians(-90 + 270)
    for y in range(S):
        for x in range(S):
            dx, dy = x - cx, y - cy
            r = math.hypot(dx, dy)
            a = (math.degrees(math.atan2(dy, dx)) + 90) % 360   # 0 — сверху, по часовой
            col = None
            if 6.6 <= r < 8.4:                                    # обод
                if a <= 270:
                    k = a / 270
                    col = ring[2 + int(k * 1.99)] if r < 7.8 else ring[1]
                else:
                    col = '#1A2E2C' if r < 7.8 else None
            elif 4.2 <= r < 5.3:                                  # внутренний шестигранник (по расстоянию до граней)
                pass
            if col:
                im.putpixel((x, y), hexc(col))
    # шестигранник
    pts = [(cx + 4.6 * math.cos(math.radians(30 + 60 * i)), cy + 4.6 * math.sin(math.radians(30 + 60 * i))) for i in range(6)]
    for i in range(6):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % 6]
        for t in range(12):
            u = t / 11
            px, py = int(round(x0 + (x1 - x0) * u)), int(round(y0 + (y1 - y0) * u))
            im.putpixel((px, py), hexc('#4FBF9F' if i < 4 else '#2E7A6A'))
    # центр — капля-перо тишины
    for x, y, c in ((8, 6, '#CFE8FF'), (9, 6, '#CFE8FF'), (8, 7, '#FFFFFF'), (9, 7, '#CFE8FF'), (8, 8, '#CFE8FF'), (9, 8, '#7FFFD0'),
                    (8, 9, '#7FFFD0'), (9, 9, '#4FBF9F'), (8, 10, '#4FBF9F'), (9, 11, '#2E7A6A')):
        im.putpixel((x, y), hexc(c))
    # голова дуги (270°, слева) — вспышка
    hx, hy = int(round(cx + 7.5 * math.cos(head - math.pi / 2 + math.pi / 2 * 0))), 0
    hx, hy = 1, 8
    for x, y, c in ((hx, hy, '#FFFFFF'), (hx, hy - 1, '#CFFFF0'), (hx + 1, hy, '#CFFFF0'), (hx, hy + 1, '#7FFFD0'), (hx - 1 if hx > 0 else hx, hy, '#7FFFD0')):
        im.putpixel((x, y), hexc(c))
    im.save(os.path.join(TEX, 'mob_effect', 'silent_barrier_cooldown.png'))
    print('wrote mob_effect/silent_barrier_cooldown.png')


if __name__ == '__main__':
    paint(HOOD, 'item/silent_witch_hood.png', hood_eyes)
    paint(ROBE, 'item/silent_witch_robe.png', robe_bow)
    paint(SKIRT, 'item/silent_witch_skirt.png', skirt_glow)
    barrier_icon()
