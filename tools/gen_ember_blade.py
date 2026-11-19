#!/usr/bin/env python3
"""
T14 «Раскалённые угли» — иконки (они же вид в руке, item/handheld) 32×32 по референсу владельца «Ruination»:
длинный однолезвийный слегка изогнутый клинок с приподнятым остриём, тёмное кованое железо с рунами у основания,
небольшой крюк у пяты клинка, рукоять в спиральной обмотке чёрной кожей, расширенное навершие.
  ember_blade.png      — форма меча: холодный клинок, тёмный металл, светлая режущая кромка, тусклые руны.
  ember_blade_hot.png  — раскалён (форма хлыста / жар): клинок светится от тёмно-красного у пяты до жёлто-белого у кромки,
                         над обухом — языки пламени, с острия срываются искры; руны горят.
Ориентация как у мечей Minecraft: навершие внизу слева, остриё вверху справа. Запуск: python3 tools/gen_ember_blade.py
"""
import math
import os
import random
from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'textures', 'item')
N = 32
SS = 4                       # суперсэмплинг для формы

def hexc(h, a=255):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16), a)

# ось оружия: из навершия (2.5, 29.5) к острию (29.5, 2.5); u — вдоль (0..1), v — поперёк (+ к «животу»/кромке, вниз-вправо)
P0, P1 = (2.6, 29.4), (29.6, 2.2)
L = math.hypot(P1[0] - P0[0], P1[1] - P0[1])
AX = ((P1[0] - P0[0]) / L, (P1[1] - P0[1]) / L)
NV = (-AX[1], AX[0])        # нормаль: (+) — в сторону кромки (вниз-вправо)
U_GRIP, U_GUARD = 0.29, 0.34  # конец рукояти, пята клинка


def bend(u):
    """Изгиб: клинок выгибается обухом вверх-влево, остриё чуть приподнято (смещение по нормали, в пикселях)."""
    if u < U_GUARD:
        return 0.35 * math.sin(u / U_GUARD * math.pi)        # рукоять слегка изогнута
    k = (u - U_GUARD) / (1 - U_GUARD)
    return -2.6 * math.sin(k * math.pi * 0.95) * (1 - 0.25 * k) + 1.4 * k ** 3


def classify(x, y):
    """Что в точке: ('pommel'|'grip'|'guard'|'blade', u, v_norm, side) или None."""
    dx, dy = x - P0[0], y - P0[1]
    u = (dx * AX[0] + dy * AX[1]) / L
    v = dx * NV[0] + dy * NV[1] - bend(max(0, min(1, u)))
    if u < -0.01 or u > 1.0:
        return None
    if u < 0.05:                                              # навершие: расширенная головка
        w = 2.3 - 8 * abs(u - 0.025)
        return ('pommel', u, v / w, 0) if abs(v) <= w else None
    if u < U_GRIP:                                            # рукоять
        w = 1.55 + 0.2 * math.sin((u - 0.05) / (U_GRIP - 0.05) * math.pi)
        return ('grip', u, v / w, 0) if abs(v) <= w else None
    if u < U_GUARD:                                           # пята: шейка + крюк в сторону обуха
        k = (u - U_GRIP) / (U_GUARD - U_GRIP)
        top = -(1.6 + 1.9 * math.sin(k * math.pi) ** 2)       # крюк к обуху
        bot = 1.6 + 1.6 * k
        return ('guard', u, v, 0) if top <= v <= bot else None
    k = (u - U_GUARD) / (1 - U_GUARD)                         # клинок
    spine = -(1.5 - 0.7 * k ** 1.6)                         # обух (сторона −v)
    belly = 3.3 * (1 - k ** 2.4) + 0.2                      # кромка (+v), к острию сходится
    if k > 0.86:                                              # остриё: обух поднимается навстречу кромке
        t = (k - 0.86) / 0.14
        spine = spine * (1 - t) + belly * t * 0.15
        belly = belly * (1 - t ** 1.3)
    if spine <= v <= belly:
        return ('blade', u, (v - spine) / max(0.05, belly - spine), k)
    return None


def sample():
    """Карта N×N: для каждого пикселя — доминирующая часть и усреднённые параметры."""
    M = {}
    for py in range(N):
        for px in range(N):
            hits = []
            for sy in range(SS):
                for sx in range(SS):
                    c = classify(px + (sx + 0.5) / SS, py + (sy + 0.5) / SS)
                    if c:
                        hits.append(c)
            if len(hits) >= SS * SS * 0.42:
                kinds = {}
                for h in hits:
                    kinds.setdefault(h[0], []).append(h)
                kind = max(kinds, key=lambda k: len(kinds[k]))
                hs = kinds[kind]
                M[(px, py)] = (kind, sum(h[1] for h in hs) / len(hs), sum(h[2] for h in hs) / len(hs), sum(h[3] for h in hs) / len(hs))
    return M


IRON = ['#0C0C10', '#18181E', '#24242C', '#33333D', '#46464F', '#5E5E68', '#7E7E88', '#A8A8B0', '#D4D4DA']
LEATHER = ['#0C0A09', '#1A1615', '#2C2725', '#433C39', '#5C5450']
HOT = ['#3A0600', '#6A1004', '#A82408', '#E04A0C', '#FF7A1E', '#FFA83A', '#FFD27A', '#FFF2C0']


def draw(hot):
    rnd = random.Random(14 if hot else 7)
    M = sample()
    im = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    filled = lambda p: p in M
    for (px, py), (kind, u, v, k) in M.items():
        edge = not all(filled((px + dx, py + dy)) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        light = (px - py) / N * 0.5                                   # свет сверху-справа
        if kind == 'pommel':
            c = IRON[3 + (v < 0) + (abs(v) < 0.4)] if not edge else IRON[1]
        elif kind == 'grip':
            # спиральная обмотка: полосы под углом, между ними тёмные щели
            band = ((u - 0.05) * L + v * 1.6) % 2.6
            if edge:
                c = LEATHER[0]
            elif band < 0.75:
                c = LEATHER[0]
            else:
                c = LEATHER[2 + (v < -0.1) + (band > 1.6 and v < 0.3)]
        elif kind == 'guard':
            c = IRON[2] if edge else IRON[4 + (v < -1.0) + (v < -2.0)]
        else:  # blade
            if hot:
                t = v                                                  # 0 — обух, 1 — кромка
                heat = 0.25 + 0.55 * t + 0.35 * k
                i = int(max(0, min(len(HOT) - 1, heat * (len(HOT) - 1))))
                c = HOT[i]
                if edge and t < 0.3:
                    c = HOT[max(0, i - 2)]                            # обух темнее — контур
                elif edge:
                    c = HOT[-1]                                        # кромка — белый жар
            else:
                if edge and v < 0.35:
                    c = IRON[0]                                        # контур обуха
                elif edge:
                    c = IRON[8] if k > 0.15 else IRON[6]              # режущая кромка блестит
                elif v > 0.68:
                    c = IRON[6 + (light > 0)]                          # подвод к кромке (дол)
                elif v < 0.22:
                    c = IRON[2]                                        # обух
                else:
                    c = IRON[3 + (light > 0.05) + (rnd.random() < 0.18)]   # кованая поверхность, пятна
        im.putpixel((px, py), hexc(c))
    # руны у основания клинка: светлые (холодный — тусклые, горячий — горят) точки-штрихи вдоль середины
    for (px, py), (kind, u, v, k) in M.items():
        if kind == 'blade' and 0.05 < k < 0.4 and 0.3 < v < 0.62 and (px + py) % 2 == 0:
            im.putpixel((px, py), hexc('#FFF2C0' if hot else '#9C9CAA'))
    if hot:
        # языки пламени над обухом (сторона −v), выше к острию; искры у острия
        for (px, py), (kind, u, v, k) in list(M.items()):
            if kind != 'blade' or v > 0.16 or k < 0.1:
                continue
            h = int(1 + 4.6 * (0.35 + 0.65 * k) * (0.55 + 0.45 * math.sin(px * 1.9 + py * 0.7)))
            for s in range(1, h + 1):
                qx, qy = px - round(NV[0] * s), py - round(NV[1] * s)
                if (qx, qy) in M or not (0 <= qx < N and 0 <= qy < N):
                    continue
                if im.getpixel((qx, qy))[3] == 0:
                    f = s / (h + 0.01)
                    col = HOT[6] if f < 0.34 else (HOT[4] if f < 0.7 else HOT[3])
                    im.putpixel((qx, qy), hexc(col, 255 if f < 0.7 else 200))
        for x, y, c in ((30, 1, '#FFF2C0'), (28, 0, '#FFA83A'), (31, 4, '#FF7A1E'), (26, 2, '#FFD27A'), (30, 6, '#E04A0C')):
            if im.getpixel((x, y))[3] == 0:
                im.putpixel((x, y), hexc(c, 220))
    return im


if __name__ == '__main__':
    for hot, name in ((False, 'ember_blade.png'), (True, 'ember_blade_hot.png')):
        draw(hot).save(os.path.join(OUT, name))
        print('wrote', name)


def skill_icon():
    """Иконка навыка оружия Epic Fight (спецатака): изогнутый клинок наискось, вокруг — огненная петля хлыста, искры. 64×64."""
    from PIL import ImageDraw, ImageFilter
    S = 256
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    # огненная петля (спираль хлыста), от толстой к тонкой, оранжевый → жёлтый
    pts = []
    for i in range(160):
        t = i / 159
        a = math.radians(200 + 520 * t)
        r = 104 * (1 - 0.62 * t)
        pts.append((128 + r * math.cos(a), 132 + r * math.sin(a) * 0.92))
    for i in range(len(pts) - 1):
        t = i / len(pts)
        w = int(16 * (1 - 0.8 * t)) + 3
        c = (255, int(110 + 120 * t), int(30 + 90 * t), 255)
        dr.line([pts[i], pts[i + 1]], fill=c, width=w)
    glow = im.filter(ImageFilter.GaussianBlur(9))
    base = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    base.alpha_composite(glow); base.alpha_composite(glow); base.alpha_composite(im)
    d2 = ImageDraw.Draw(base)
    # клинок наискось: тёмная кромка обуха, раскалённое тело, белая кромка
    blade = [(58, 206), (72, 196), (196, 66), (214, 40), (186, 58), (62, 188)]
    d2.polygon(blade, fill=(255, 140, 50, 255))
    d2.line([(72, 196), (196, 66), (214, 40)], fill=(255, 242, 192, 255), width=6)
    d2.line([(62, 188), (186, 58), (214, 40)], fill=(110, 24, 6, 255), width=5)
    d2.line([(40, 228), (64, 202)], fill=(40, 32, 30, 255), width=16)   # рукоять
    d2.line([(52, 192), (76, 214)], fill=(70, 70, 80, 255), width=9)    # пята
    for (x, y, r) in ((200, 28, 5), (226, 54, 4), (176, 36, 3), (222, 22, 3)):
        d2.ellipse((x - r, y - r, x + r, y + r), fill=(255, 236, 170, 255))
    out = base.resize((64, 64), Image.LANCZOS)
    p = os.path.join(OUT, '..', 'gui', 'skills', 'weapon_innate', 'ember_special.png')
    out.save(p)
    print('wrote gui/skills/weapon_innate/ember_special.png')


if __name__ == '__main__':
    skill_icon()


def whip_hilt():
    """Форма хлыста В РУКЕ (физический хлыст T14, client/EmberWhipClient): клинок стал хлыстом, видна только раскалённая рукоять —
    навершие, обмотка, пята с крюком; в «устье» пяты, откуда выходит хлыст, тлеет жар. В инвентаре/на земле остаётся
    ember_blade_hot.png (models/item/ember_blade_hot.json, forge:separate_transforms). Корень хлыста в коде — u 0.35 оси иконки."""
    full = draw(True)
    M = sample()
    im = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    for (px, py), (kind, u, v, k) in M.items():
        if kind in ('pommel', 'grip', 'guard'):
            im.putpixel((px, py), full.getpixel((px, py)))
    # устье: раскалённая кромка пяты со стороны клинка и уголь посередине
    for (px, py), (kind, u, v, k) in M.items():
        if kind == 'guard' and u > U_GUARD - 0.018:
            im.putpixel((px, py), hexc(HOT[5] if abs(v) < 1.2 else HOT[3]))
    gx, gy = P0[0] + AX[0] * L * U_GUARD, P0[1] + AX[1] * L * U_GUARD
    for dx, dy, c in ((0, 0, HOT[7]), (1, 0, HOT[6]), (0, 1, HOT[6]), (1, -1, HOT[5]), (-1, 1, HOT[5])):
        x, y = int(gx) + dx, int(gy) + dy
        if 0 <= x < N and 0 <= y < N and im.getpixel((x, y))[3]:
            im.putpixel((x, y), hexc(c))
    return im


if __name__ == '__main__':
    whip_hilt().save(os.path.join(OUT, 'ember_blade_whip.png'))
    print('wrote ember_blade_whip.png')
