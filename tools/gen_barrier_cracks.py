#!/usr/bin/env python3
"""
Трещины на оболочке барьера от «Млечного пути» (владелец 19.11): textures/fx/barrier_cracks.png, 256×256, белые (красит код цветом
купола) — от точки удара в центре расходятся 9–11 ломаных трещин с ветвлениями, у центра — выбитое «звёздное» пятно и паутина
коротких поперечных трещин (как скол стекла). Яркость линии убывает к концам, вокруг линий мягкий ореол.
Альфа = насколько ярко; канал G дополнительно хранит «расстояние от центра» (0 у центра → 255 у края) — код может
затягивать трещины от краёв к центру порогом по G (см. письмо коду). Запуск: python3 tools/gen_barrier_cracks.py
"""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

S = 1024
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'textures', 'fx', 'barrier_cracks.png')
rnd = random.Random(1907)
C = S / 2
line = Image.new('L', (S, S), 0)
d = ImageDraw.Draw(line)


RAYS = []


def crack(x, y, ang, length, w, depth, pts=None):
    pts = pts if pts is not None else [(x, y)]
    while length > 0 and w > 0.6:
        step = rnd.uniform(26, 60)
        ang += rnd.gauss(0, 0.09)                           # стекло: почти прямые, с изломами
        nx, ny = x + math.cos(ang) * step, y + math.sin(ang) * step
        if math.hypot(nx - C, ny - C) / (S / 2) > 0.97:
            break
        d.line([(x, y), (nx, ny)], fill=int(255 * min(1, 0.4 + w / 7)), width=max(1, int(w)))
        x, y = nx, ny
        pts.append((x, y))
        length -= step
        w *= 0.94
        if depth < 1 and rnd.random() < 0.16:
            crack(x, y, ang + rnd.choice((-1, 1)) * rnd.uniform(0.35, 0.7), length * rnd.uniform(0.3, 0.5), w * 0.65, depth + 1)
    return pts


n = rnd.randint(10, 12)
for i in range(n):
    a = i / n * 2 * math.pi + rnd.uniform(-0.18, 0.18)
    RAYS.append((a, crack(C + math.cos(a) * 18, C + math.sin(a) * 18, a, rnd.uniform(360, 470), rnd.uniform(6, 8.5), 0)))
# паутина: прямые перемычки между соседними лучами на нескольких «кольцах», с пропусками — как скол стекла
for ring, wd in ((70, 4), (140, 3), (215, 2), (300, 2)):
    for i in range(n):
        if rnd.random() < (0.12 if ring < 150 else 0.4):
            continue
        (a0, p0), (a1, p1) = RAYS[i], RAYS[(i + 1) % n]
        def at(pts, rr):
            for q in pts:
                if math.hypot(q[0] - C, q[1] - C) >= rr:
                    return q
            return pts[-1]
        q0, q1 = at(p0, ring * rnd.uniform(0.9, 1.1)), at(p1, ring * rnd.uniform(0.9, 1.1))
        mid = ((q0[0] + q1[0]) / 2 + rnd.uniform(-8, 8), (q0[1] + q1[1]) / 2 + rnd.uniform(-8, 8))
        d.line([q0, mid, q1], fill=170 if ring < 150 else 120, width=wd)
# выбитое пятно в центре
d.ellipse((C - 26, C - 26, C + 26, C + 26), fill=255)

L = np.asarray(line, dtype=np.float32) / 255
glow = np.asarray(line.filter(ImageFilter.GaussianBlur(10)), dtype=np.float32) / 255
yy, xx = np.mgrid[0:S, 0:S]
r = np.hypot(xx - C, yy - C) / (S / 2)
alpha = np.clip(np.maximum(L, glow * 1.6) * (1 - 0.55 * r), 0, 1)
centre = np.exp(-(r / 0.09) ** 2)
alpha = np.clip(alpha + 0.6 * centre, 0, 1)
rgb_white = np.clip(0.75 + 0.25 * L + 0.3 * centre, 0, 1)
img = np.zeros((S, S, 4), dtype=np.uint8)
img[..., 0] = (rgb_white * 255).astype(np.uint8)
img[..., 1] = (np.clip(r, 0, 1) * 255).astype(np.uint8)          # расстояние от центра для «затягивания»
img[..., 2] = (rgb_white * 255).astype(np.uint8)
img[..., 3] = (alpha * 255).astype(np.uint8)
Image.fromarray(img, 'RGBA').resize((256, 256), Image.LANCZOS).save(OUT)
print('wrote textures/fx/barrier_cracks.png')
