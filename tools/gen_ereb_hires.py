#!/usr/bin/env python3
"""
T30 «Эреб» — текстура ×4, как у эталона (Глава Культа: атлас UV 128 → картинка 512, 4 пикселя на единицу UV).
Вызывается из tools/gen_ereb.py (hires(M, atlas, smile)). Без шума и сглаживания: только цвета ручных ступеней палитры
(и середины между соседними ступенями одного материала), узоры — по правилам, детерминированно.

Порядок: пиксель-арт 1:1 (gen_ereb.paint_skin/paint_new) → Scale2x×2 по каждой грани отдельно (без новых цветов, лицо — без него:
чёткие глаза) → фактура материала → ручные узоры ×4: золотое шитьё по подолу, у разреза и шлицы, филигрань на рукавах,
пуговицы застёжек, швы, строчка манжет, пряди волос, блики глаз.
  ткань (чёрное сукно и тёмно-серое): саржа — диагональ через 4 px на полтона светлее; мягкие вертикальные складки на полах и спине;
      блик на плечах (верх рукавов, наплечников, мантии); тёмная кромка граней — объём;
  золото: «нить» — верхняя строка каждого текселя светлее, нижняя темнее (шитьё рядами);
  волосы: пряди — тёмная линия через 4 px со сдвигом, блик у корня;  стекло: диагональный блик.
"""
import math

import numpy as np
from PIL import Image

import gen_cult_leader as CL

K = 4
M = None
FAM = {'cloth': 'abcde', 'grey': 'uvVW', 'gold': 'opqrst', 'glass': 'xyzZ', 'skin': '12345', 'hair': 'ABCDEF', 'glove': 'GHJK'}
RAMP = {}         # семейство → [rgb …] (ступени + середины)
INDEX = {}        # rgb → (семейство, индекс)


def build_ramps():
    RAMP.clear()
    INDEX.clear()
    for f, letters in FAM.items():
        cs = [M.hx(M.PAL[c])[:3] for c in letters]
        st = []
        for i, c in enumerate(cs):
            if i:
                p = cs[i - 1]
                st.append(tuple((a + b) // 2 for a, b in zip(p, c)))
            st.append(c)
        RAMP[f] = st
        for i, c in enumerate(st):
            INDEX.setdefault(c, (f, i))


def shift(c, d):
    f, i = INDEX.get(tuple(c[:3]), (None, None))
    if f is None or not d:
        return tuple(c[:3])
    st = RAMP[f]
    return st[max(0, min(len(st) - 1, i + d))]


def col(ch):
    return M.hx(M.PAL[ch])


def rects_all(geo):
    """[(x0, y0, x1, y1, кость, грань, деталь)] в единицах атласа: скин (box UV) + новые бруски."""
    out = []
    for (x0, y0, x1, y1, bone, face, tag) in CL.face_rects(geo):
        out.append((x0, y0, x1, y1, bone, face, 'skin%s' % (tag,)))
    for (bone, name, f, x, y, w, h) in M.NEW:
        out.append((x, y, x + w, y + h, bone, f, name))
    return out


def hires(mod, atl, geo, smile=False):
    global M
    M = mod
    build_ramps()
    rects = rects_all(geo)
    W, H = atl.size
    big = atl.resize((W * K, H * K), Image.NEAREST)
    bp = CL.pack(big)
    ap = CL.pack(atl)
    face_box = (8, 8, 16, 16)          # лицо — без Scale2x (глаза чёткими квадратами, как на скине)
    for (x0, y0, x1, y1, *_r) in rects:
        X0, Y0, X1, Y1 = int(math.floor(x0)), int(math.floor(y0)), int(math.ceil(x1)), int(math.ceil(y1))
        if (X0, Y0, X1, Y1) == face_box:
            continue
        sub = ap[Y0:Y1, X0:X1]
        if sub.size:
            bp[Y0 * K:Y1 * K, X0 * K:X1 * K] = CL.scale2x(CL.scale2x(sub))
    img = CL.unpack(bp)
    o = img.copy()
    for ri, (x0, y0, x1, y1, bone, face, name) in enumerate(rects):
        X0, Y0, X1, Y1 = int(round(x0 * K)), int(round(y0 * K)), int(round(x1 * K)), int(round(y1 * K))
        w, h = X1 - X0, Y1 - Y0
        if w < 2 or h < 2:
            continue
        vertical = face in ('north', 'south', 'east', 'west')
        coat = name.startswith('coat_')
        upper = bone in ('torso', 'right_arm', 'left_arm') and vertical and not name.startswith(('cuff', 'fringe', 'strap'))
        ph = (ri * 2.399) % 6.28
        for y in range(h):
            for x in range(w):
                px = img[Y0 + y, X0 + x]
                if px[3] == 0:
                    continue
                c = tuple(int(v) for v in px[:3])
                f = INDEX.get(c, (None,))[0]
                if f is None:
                    continue
                d = 0
                X, Y = X0 + x, Y0 + y
                edge = min(x, y, w - 1 - x, h - 1 - y)
                if f in ('cloth', 'grey'):
                    if (X + Y) % 4 == 0:
                        d += 1                                                   # саржа
                    if vertical and (coat or bone == 'torso' and face == 'south') and h > 24:
                        s = math.sin(x / w * math.pi * 4 + ph + 0.35 * math.sin(y / h * 3 + ph))
                        d += 1 if s > 0.95 else (-1 if s < -0.93 else 0)         # складки
                    if face == 'up' and bone in ('torso', 'right_arm', 'left_arm'):
                        d += 1                                                   # блик на плечах
                    if upper and y < 5:
                        d += 1
                    if edge == 0:
                        d -= 1
                elif f == 'gold':
                    if y % 4 == 0:
                        d += 1                                                   # нить шитья: ряды
                    elif y % 4 == 3:
                        d -= 1
                    if (X // 2 + Y // 4) % 5 == 0 and y % 4 == 1:
                        d += 1                                                   # искра на нити
                elif f == 'hair':
                    if vertical:
                        if (x + (y // 6) * 2) % 4 == 0:
                            d -= 1                                               # прядь
                        elif (x + (y // 6) * 2) % 4 == 2 and y < h // 3:
                            d += 1                                               # блик у корня
                        if y >= h - 2:
                            d -= 1
                    elif face == 'up' and (X * 3 + Y * 5) % 7 == 0:
                        d += 1
                elif f == 'glass':
                    if (x - y) % 6 == 0:
                        d += 3
                elif f == 'glove':
                    if (X + Y) % 4 == 0:
                        d -= 1
                if d:
                    o[Y, X, :3] = shift(c, d)
    out = Image.fromarray(o, 'RGBA')
    ornaments(out, rects, smile)
    return out


# ================================================================== узоры ×4
def put(img, x, y, ch):
    if 0 <= x < img.width and 0 <= y < img.height and img.getpixel((x, y))[3]:
        img.putpixel((x, y), col(ch) if isinstance(ch, str) else ch)


def ornaments(img, rects, smile):
    for (x0, y0, x1, y1, bone, face, name) in rects:
        X0, Y0, X1, Y1 = int(round(x0 * K)), int(round(y0 * K)), int(round(x1 * K)), int(round(y1 * K))
        w, h = X1 - X0, Y1 - Y0
        if name.startswith('coat_') and not name.endswith('_side'):
            front = name.startswith('coat_front')
            right = name.endswith('_r')
            outer = (front and face == 'north') or (not front and face == 'south')
            if not outer:
                continue
            # кайма-лоза над подолом: волна золотой нитью с бутонами
            yb = Y1 - 14
            for x in range(X0, X1):
                t = (x - X0) / 6.0
                yy = yb + int(round(1.5 * math.sin(t * math.pi)))
                put(img, x, yy, 'r')
                put(img, x, yy + 1, 'p')
                if (x - X0) % 12 == 3:
                    for (dx, dy, ch) in ((0, -3, 's'), (-1, -2, 'r'), (1, -2, 'r'), (0, -2, 't'), (0, -1, 'q')):
                        put(img, x + dx, yb + dy, ch)
            # у разреза / шлицы: завитки вдоль золотого галуна
            ie = X1 - 1 - 4 if (front and right) or (not front and right) else X0 + 4
            dirx = -1 if ie > X0 + w // 2 else 1
            for k, yc in enumerate(range(Y0 + 10, Y1 - 22, 10)):
                cx = ie + dirx * 3
                for (dx, dy, ch) in ((0, 0, 's'), (dirx, -1, 'r'), (2 * dirx, -1, 'r'), (3 * dirx, 0, 'q'), (2 * dirx, 1, 'q'),
                                     (dirx, 1, 'p'), (dirx, 3, 'r'), (0, 4, 'q')):
                    put(img, cx + dx, yc + dy, ch)
        elif name.startswith('cuff') and face in ('north', 'south', 'east', 'west'):
            for x in range(X0, X1):                                            # строчка-зигзаг под золотой кромкой
                put(img, x, Y0 + 5 + (x % 4 == 1) - (x % 4 == 3), 'q')
            if face in ('east', 'west'):
                bx, by = X0 + w // 2, Y0 + 7                                   # пуговица
                button(img, bx, by)
        elif name.startswith('epaulet') and face == 'up':
            for x in range(X0 + 2, X1 - 2):
                put(img, x, Y0 + 2, 'p') if x % 3 == 0 else None
        elif name == 'belt' and face == 'north':
            for x in range(X0, X1, 4):
                put(img, x, Y0 + 2, 'e')                                       # строчка ремня
    # --- скин: рукава (филигрань вокруг «креста»), застёжки с пуговицами, швы
    rs = M.box_regions
    for (ou, ov, outer) in ((40, 32, 'east'), (48, 48, 'west')):
        r = rs(ou, ov, 4, 12, 4)
        for fc in (outer, 'north', 'south'):
            x, y = r[fc][0] * K, r[fc][1] * K
            for yy in range(y + 2 * K, y + 6 * K):                                  # блочный «крест» 1:1 → тонкая филигрань ×4
                for xx in range(x, x + 4 * K):
                    img.putpixel((xx, yy), (0, 0, 0, 0))
            filigree(img, x, y + 2 * K, outer=(fc == outer))
    r = rs(16, 32, 8, 12, 4)['north']                                          # слой камзола — грудь
    x, y = r[0] * K, r[1] * K
    for row in (6, 8):
        for cx in (10, 22):
            button(img, x + cx, y + row * K + 2)
    r = rs(16, 16, 8, 12, 4)
    for fc in ('east', 'west'):
        x, y = r[fc][0] * K, r[fc][1] * K
        for yy in range(y, y + 12 * K):
            put(img, x + 8, yy, 'a') if (yy // 2) % 2 == 0 else None           # боковой шов (стежки)
    x, y = r['south'][0] * K, r['south'][1] * K
    for yy in range(y + 4, y + 16):
        put(img, x + 16, yy, 'a')                                              # шов спинки
    # --- лицо: блики в глазах (по 1 px), реснички
    fx, fy = 8 * K, 8 * K
    for ex in ((2, 5) if not smile else ()):
        put(img, fx + ex * K + 1, fy + 4 * K + 1, 'k')                          # блик на тёмной радужке
        put(img, fx + ex * K + 2, fy + 4 * K + 1, 'k')
    for ex in (1, 6):
        for i in range(K):
            put(img, fx + ex * K + i, fy + 4 * K, 'l' if not smile else 'l')    # ресницы над белком


def button(img, cx, cy):
    for (dx, dy, ch) in ((0, -1, 's'), (-1, 0, 's'), (0, 0, 't'), (1, 0, 'r'), (0, 1, 'q'), (-1, -1, 'r'), (1, 1, 'p'), (1, -1, 'r'), (-1, 1, 'q')):
        put(img, cx + dx, cy + dy, ch)


def filigree(img, x, y, outer):
    """Филигрань рукава ×4 поверх «креста» (слой рукава, 16×16 px от ряда 2): ромб тонкой нитью, точки, сердцевина."""
    pts = []
    for k in range(8):
        pts += [(8 + k, k), (8 - k, k), (8 + k, 15 - k), (8 - k, 15 - k)]
    for (dx, dy) in pts:
        if 0 <= dx < 16 and 0 <= dy < 16:
            px, py = x + dx, y + dy
            if 0 <= px < img.width and 0 <= py < img.height:
                img.putpixel((px, py), col('r' if (dx + dy) % 2 else 's'))
    for (dx, dy, ch) in ((7, 7, 't'), (8, 7, 's'), (7, 8, 's'), (8, 8, 'q'), (7, 3, 'q'), (7, 12, 'q'), (3, 7, 'q'), (12, 7, 'q')):
        img.putpixel((x + dx, y + dy), col(ch))
    if not outer:
        return


def glow(mod, big):
    """Глоумаска ×4: стекло (броши, пряжек) и едва — радужки."""
    a = np.asarray(big)
    g = np.zeros_like(a)
    glass = np.zeros(a.shape[:2], bool)
    for c in RAMP['glass']:
        glass |= (a[..., 0] == c[0]) & (a[..., 1] == c[1]) & (a[..., 2] == c[2])
    glass &= a[..., 3] > 0
    g[glass] = a[glass]
    fx, fy = 8 * K, 8 * K
    for ex in (2, 5):
        g[fy + 4 * K + 1:fy + 6 * K, fx + ex * K:fx + (ex + 1) * K] = mod.hx('#164f63')
        g[fy + 5 * K:fy + 6 * K, fx + ex * K:fx + (ex + 1) * K] = mod.hx('#1d6a80')
    return Image.fromarray(g, 'RGBA')
