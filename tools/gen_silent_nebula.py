#!/usr/bin/env python3
"""
«Безмолвные врата», момент указа рукой (14.6–26 с) — ТУМАННОСТЬ как в видео мода: большое мягкое светящееся облако-рукав галактики
перед ведьмой и над ней (белая сердцевина → розово-лиловое → бирюзовые края), внутри густая россыпь звёзд с ореолами и лучиками.
Текстуры (additive, чёрное = прозрачно):
  textures/sigil/silent_nebula_cloud.png  — облачный рукав дугой снизу-слева вверх-вправо, 512
  textures/sigil/silent_nebula_stars.png  — звёзды: россыпь мелких + крупные с ореолом и 4 лучами, 512
  textures/sigil/silent_nebula_wisp.png   — тонкие светлые струи-завитки вдоль рукава, 512
Печать sigils/silent_hand_nebula.json (billboard) — три облачных слоя на разной «глубине», звёзды и струи медленно вращаются.
Запуск: python3 tools/gen_silent_nebula.py
"""
import json
import math
import os
import random
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core')
N = 512


def arm(t):
    """Ось облака (как в видео мода): пышный столб снизу от центра вверх и вправо, слегка изогнутый (не дуга-радуга)."""
    return 220 + 120 * t + 30 * math.sin(t * 3.0), 430 - 360 * t


def blobs(rnd, n, size0, size1, spread):
    img = np.zeros((N, N), np.float32)
    yy, xx = np.mgrid[0:N, 0:N]
    for _ in range(n):
        t = rnd.random()
        cx, cy = arm(t)
        cx += rnd.gauss(0, spread * (0.6 + t)); cy += rnd.gauss(0, spread * (0.6 + t))
        s = rnd.uniform(size0, size1) * (0.7 + 0.6 * t)
        img += rnd.uniform(0.3, 1.0) * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s))
    return img


def colorize(I, core, mid, edge):
    I = np.clip(I / max(1e-6, np.percentile(I, 99.7)), 0, 1)
    core, mid, edge = [tuple(v / 255 for v in c) for c in (core, mid, edge)]
    c = np.zeros((N, N, 3), np.float32)
    for k in range(3):
        c[..., k] = np.where(I > 0.55, mid[k] + (core[k] - mid[k]) * (I - 0.55) / 0.45, edge[k] + (mid[k] - edge[k]) * I / 0.55)
    rgb = c * np.clip(I[..., None] * 1.25, 0, 1) ** 1.1
    return rgb


def save(rgb, name):
    a = np.clip(rgb.max(axis=2), 0, 255)
    out = np.dstack([np.clip(rgb, 0, 255), a]).astype(np.uint8)
    # мягкий край квадрата — чтобы не было видно границ текстуры
    yy, xx = np.mgrid[0:N, 0:N]
    d = np.sqrt(((xx - 255.5) / 255.5) ** 2 + ((yy - 255.5) / 255.5) ** 2)
    fade = np.clip((1.0 - d) / 0.25, 0, 1)
    out[..., :3] = (out[..., :3] * fade[..., None]).astype(np.uint8)
    out[..., 3] = (out[..., 3] * fade).astype(np.uint8)
    Image.fromarray(out, 'RGBA').save(os.path.join(A, 'textures', 'sigil', name + '.png'))
    print('wrote', name)


def main():
    rnd = random.Random(1514)
    core, mid, edge = (255, 255, 255), (246, 196, 238), (110, 214, 236)
    cloud = blobs(rnd, 320, 18, 56, 38) + 0.7 * blobs(rnd, 140, 40, 90, 55)
    def smooth_noise(res, seed, blur):
        a = (np.random.RandomState(seed).rand(res, res) * 255).astype(np.uint8)
        im = Image.fromarray(a).resize((N, N), Image.BICUBIC).filter(ImageFilter.GaussianBlur(blur))
        return np.array(im, np.float32) / 255
    noise = 0.5 * smooth_noise(12, 3, 18) + 0.3 * smooth_noise(28, 4, 9) + 0.2 * smooth_noise(64, 5, 4)
    cloud *= 0.35 + 1.3 * noise
    cloud = np.array(Image.fromarray(np.clip(cloud / cloud.max() * 255, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), np.float32)
    save(colorize(cloud, core, mid, edge) * 255, 'silent_nebula_cloud')
    haze = blobs(rnd, 60, 70, 140, 70)
    hz = colorize(haze, (255, 236, 250), (226, 160, 214), (150, 110, 170)) * 255 * 0.8
    save(hz, 'silent_nebula_haze')
    # струи-завитки: тонкие светлые нити вдоль рукава
    w = np.zeros((N, N), np.float32)
    im = Image.new('L', (N, N), 0)
    from PIL import ImageDraw
    dr = ImageDraw.Draw(im)
    for k in range(14):
        off = rnd.uniform(-38, 38); ph = rnd.uniform(0, 6.28)
        pts = []
        for i in range(60):
            t = i / 59
            x, y = arm(t)
            n_ = off * (0.5 + t) + 10 * math.sin(t * 9 + ph)
            pts.append((x + n_ * 0.6, y + n_))
        dr.line(pts, fill=int(rnd.uniform(90, 200)), width=rnd.choice((2, 3, 4)))
    im = im.filter(ImageFilter.GaussianBlur(2.2))
    w = np.array(im, np.float32)
    save(colorize(w, core, (210, 245, 255), edge) * 255, 'silent_nebula_wisp')
    # звёзды
    st = Image.new('RGB', (N, N), (0, 0, 0))
    dr = ImageDraw.Draw(st)
    for i in range(1500):
        t = rnd.random(); x, y = arm(t)
        x += rnd.gauss(0, 75 * (0.6 + t)); y += rnd.gauss(0, 40 * (0.6 + t))
        b = int(rnd.uniform(120, 255)); r = rnd.choice((0.6, 0.8, 1.0, 1.3))
        c = rnd.choice(((b, b, b), (int(b * 0.85), b, b), (b, int(b * 0.85), b)))
        dr.ellipse((x - r, y - r, x + r, y + r), fill=c)
    st = st.filter(ImageFilter.GaussianBlur(0.6))
    big = Image.new('RGB', (N, N), (0, 0, 0)); db = ImageDraw.Draw(big)
    for i in range(46):
        t = rnd.random(); x, y = arm(t)
        x += rnd.gauss(0, 45); y += rnd.gauss(0, 45)
        L = rnd.uniform(8, 22)
        for k, (dx, dy) in enumerate(((1, 0), (0, 1))):
            db.line((x - dx * L, y - dy * L, x + dx * L, y + dy * L), fill=(255, 255, 255), width=1)
        db.ellipse((x - 2.5, y - 2.5, x + 2.5, y + 2.5), fill=(255, 255, 255))
    halo = big.filter(ImageFilter.GaussianBlur(4))
    arr = np.array(st, np.float32) + np.array(big, np.float32) * 0.9 + np.array(halo, np.float32) * 1.6
    save(arr, 'silent_nebula_stars')
    sig = {
        'comment': '«Безмолвные врата», указ рукой (14.6–26 с): туманность как в видео мода — облачный рукав галактики перед ведьмой и над ней, '
                   'звёзды и светлые струи; billboard, слои медленно вращаются. Сгенерировано tools/gen_silent_nebula.py.',
        'size': 4.0, 'color': '#FFFFFF', 'orientation': 'billboard', 'lifetime': -1, 'hold': -1,
        'layers': [
            {'id': 'haze', 'type': 'disc', 'texture': 'silent_nebula_haze', 'radius': 1.7, 'heightOffset': -0.1, 'brightness': 0.65,
             'appear': {'delay': 0, 'duration': 36, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}, 'rotation': {'speed': 0.4}},
            {'id': 'cloud_back', 'type': 'disc', 'texture': 'silent_nebula_cloud', 'radius': 1.25, 'heightOffset': -0.06, 'brightness': 0.24,
             'appear': {'delay': 0, 'duration': 30, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade', 'twist'], 'twist': -40}, 'rotation': {'speed': 0.8}},
            {'id': 'cloud', 'type': 'disc', 'texture': 'silent_nebula_cloud', 'radius': 1.05, 'heightOffset': 0.0, 'brightness': 0.33,
             'appear': {'delay': 6, 'duration': 30, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade', 'twist'], 'twist': 50}, 'rotation': {'speed': -1.2}},
            {'id': 'wisp', 'type': 'disc', 'texture': 'silent_nebula_wisp', 'radius': 1.05, 'heightOffset': 0.03, 'brightness': 0.8,
             'appear': {'delay': 10, 'duration': 30, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}, 'rotation': {'speed': 2.0}},
            {'id': 'stars', 'type': 'disc', 'texture': 'silent_nebula_stars', 'radius': 1.1, 'heightOffset': 0.06,
             'appear': {'delay': 4, 'duration': 24, 'easing': 'easeOutCubic', 'modes': ['grow', 'fade']}, 'rotation': {'speed': -0.6},
             'pulse': {'amp': 0.18, 'period': 26}}],
        'dissolve': {'modes': ['fade', 'collapse'], 'duration': 24}}
    with open(os.path.join(A, 'sigils', 'silent_hand_nebula.json'), 'w', encoding='utf-8') as f:
        json.dump(sig, f, ensure_ascii=False, indent=1)
    print('wrote sigils/silent_hand_nebula.json')


if __name__ == '__main__':
    main()
