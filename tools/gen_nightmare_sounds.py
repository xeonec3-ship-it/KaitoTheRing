#!/usr/bin/env python3
"""
T25 «Кошмары» — свои звуки школы и бестиария (владелец разрешил свои звуки, docs/inbox/README.md, «Свои звуки»).
Основа — **природные записи под CC0** с OpenGameArt (список SOURCES ниже: автор, страница, лицензия) — обработка: высота/скорость, реверс,
эхо, свёрточная реверберация (своя импульсная характеристика), фильтры, слои, огибающие. Голый синтез — только музыкальная шкатулка
(удары язычков — затухающие негармонические обертоны) и инфранизкий «удар» под сердцем.

Пишет:
  src/main/resources/assets/pohsmp_core/sounds/nightmare/<событие>_<n>.ogg   — моно (позиционные), 44.1 кГц, Vorbis q5
  sounds.json — события `nightmare.*` (ЖДУТ СОГЛАСОВАНИЯ владельцем: код их не подключает до одобрения)
  lang ru/en — субтитры `subtitles.pohsmp_core.nightmare.*` (только недостающие)
  docs/media/t25_sounds_demo.mp3 — все звуки подряд (перед каждым 0.5 с тишины), docs/media/t25_sounds_list.md — номер, время, что, где
Исходники качаются в tools/.cache/nightmare_snd (не в git). Запуск: python3 tools/gen_nightmare_sounds.py  (нужны ffmpeg, numpy, scipy, py7zr)
"""
import json
import math
import os
import subprocess
import sys
import urllib.request
import zipfile

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
OUT = os.path.join(A, 'sounds', 'nightmare')
CACHE = os.path.join(HERE, '.cache', 'nightmare_snd')
SR = 44100
OGA = 'https://opengameart.org/sites/default/files/'

# архив/файл на OGA -> (страница, автор). Все — CC0 (проверено на страницах 19.11.2026).
SOURCES = {
    'heartbeat_slow_0.wav': ('heartbeat-sounds', 'bart'),
    'heartbeat.mp3_.flac': ('heartbeat-single-sound', 'qubodup'),
    'group_giggling.ogg': ('group-giggling', 'Nocturnal_Vanguard (AuraVoice)'),
    'ghostbreath.flac': ('ghost-breath', 'qubodup'),
    'Creepychanting.zip': ('creepy-incoherent-chanting', 'OwlishMedia'),
    'ghostly_humming.ogg': ('ghostly-humming', 'Nocturnal_Vanguard (AuraVoice)'),
    'monster_roar.wav': ('cc0-deep-monster-roar', 'trazzz123'),
    'monster_-_starninjas.zip': ('16-monster-growls', 'StarNinjas'),
    'independent_nu_ljudbank-wet_squish_slurp_impacts.7z': ('8-wet-squish-slurp-impacts', 'qubodup / Independent.nu'),
    '25-CC0-mud-sfx.zip': ('25-cc0-mud-sfx', 'rubberduck'),
    'water-splash-slime-sfx.zip': ('40-cc0-water-splash-slime-sfx', 'rubberduck'),
    'wings_flap_large.zip': ('large-wings-flap', 'AntumDeluge'),
    'scrapes.zip': ('scrapes', 'AntumDeluge'),
    'tree_creak.flac': ('tree-creaking', 'AntumDeluge'),
    'qubodup-GhostMoans.zip': ('ghost-monster-voice-moaning-growling', 'qubodup'),
    'independent_nu_ljudbank-atmosphere_moody.7z': ('4-atmospheric-ghostly-loops', 'qubodup / Independent.nu'),
    'scaryhighpitchedghost.wav': ('scary-high-pitched-ghost', 'Fupi'),
    '80-CC0-creature-SFX_0.zip': ('80-cc0-creature-sfx', 'rubberduck'),
}


# ================================================================== исходники
def fetch():
    os.makedirs(CACHE, exist_ok=True)
    for f in SOURCES:
        p = os.path.join(CACHE, f)
        if not os.path.exists(p):
            req = urllib.request.Request(OGA + f, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=180) as r, open(p, 'wb') as fh:
                fh.write(r.read())
        d = os.path.join(CACHE, 'x_' + os.path.splitext(f)[0])
        if f.endswith('.zip') and not os.path.isdir(d):
            zipfile.ZipFile(p).extractall(d)
        if f.endswith('.7z') and not os.path.isdir(d):
            import py7zr
            py7zr.SevenZipFile(p).extractall(d)


_LOADED = {}


def load(rel, t0=0.0, t1=None):
    """Файл из кэша (путь относительно CACHE) -> моно float32 44.1 кГц, срез [t0, t1] с."""
    if rel not in _LOADED:
        path = os.path.join(CACHE, rel)
        if not os.path.exists(path):                         # в архивах бывают подпапки — ищем по имени файла
            top, base = rel.split('/')[0], os.path.basename(rel)
            for dp, dn, fn in os.walk(os.path.join(CACHE, top)):
                if base in fn:
                    path = os.path.join(dp, base)
                    break
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                             capture_output=True, check=True).stdout
        _LOADED[rel] = np.frombuffer(raw, np.float32).astype(np.float64)
    x = _LOADED[rel]
    a = int(t0 * SR)
    b = len(x) if t1 is None else int(t1 * SR)
    return x[a:b].copy()


# ================================================================== обработка
def norm(x, peak=0.89):
    m = np.max(np.abs(x)) + 1e-9
    return x * (peak / m)


def speed(x, k):
    """Скорость ×k (вместе с высотой: k < 1 — ниже и медленнее)."""
    if abs(k - 1) < 1e-4:
        return x
    n = int(len(x) / k)
    return signal.resample(x, n) if len(x) < 400000 else np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)


def semis(x, s):
    return speed(x, 2 ** (s / 12))


def lp(x, f, order=4):
    return signal.sosfilt(signal.butter(order, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, order=4):
    return signal.sosfilt(signal.butter(order, f, 'high', fs=SR, output='sos'), x)


def bp(x, f0, f1, order=3):
    return signal.sosfilt(signal.butter(order, [f0, f1], 'band', fs=SR, output='sos'), x)


def ir(t60=2.5, pre=0.012, bright=5000, seed=1, dense=True):
    """Импульсная характеристика «каменного зала»: шум с экспоненциальным спадом, темнеет к хвосту, ранние отражения."""
    rng = np.random.default_rng(seed)
    n = int((t60 + pre) * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    env = np.exp(-6.9 * np.maximum(t - pre, 0) / t60) * (t >= pre)
    h = lp(noise, bright, 2) * env
    for k, (d, g) in enumerate(((0.019, 0.5), (0.027, 0.4), (0.041, 0.35), (0.053, 0.3), (0.071, 0.22))):
        i = int(d * SR)
        if i < n:
            h[i] += g * (1 if k % 2 else -1)
    return h / np.sqrt(np.sum(h ** 2))


def reverb(x, wet=0.35, t60=2.5, bright=5000, seed=1, tail=True):
    h = ir(t60, bright=bright, seed=seed)
    y = signal.fftconvolve(x, h)
    xx = np.concatenate([x, np.zeros(len(y) - len(x))])
    out = xx * (1 - wet) + y * wet * (np.max(np.abs(xx)) / (np.max(np.abs(y)) + 1e-9))
    return out if tail else out[:len(x)]


def echo(x, d=0.33, fb=0.4, n=4, damp=3500):
    out = np.concatenate([x, np.zeros(int(d * SR * n))])
    tap = x
    for k in range(1, n + 1):
        tap = lp(tap, damp, 2) * fb
        i = int(d * SR * k)
        out[i:i + len(tap)] += tap
    return out


def fade(x, fi=0.01, fo=0.05):
    x = x.copy()
    a, b = int(fi * SR), int(fo * SR)
    if a:
        x[:a] *= np.linspace(0, 1, a) ** 2
    if b:
        x[-b:] *= np.linspace(1, 0, b) ** 2
    return x


def trem(x, rate=5.0, depth=0.6, jitter=0.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(len(x)) / SR
    ph = 2 * np.pi * rate * t + jitter * np.cumsum(rng.standard_normal(len(x))) / SR * 20
    return x * (1 - depth * (0.5 + 0.5 * np.sin(ph)))


def mix(*parts, length=None):
    """parts: (сигнал, сдвиг с, громкость)."""
    L = length or max(int(o * SR) + len(s) for s, o, g in parts)
    y = np.zeros(int(L) if length is None else int(length * SR))
    for s, o, g in parts:
        i = int(o * SR)
        if i >= len(y):
            continue
        n = min(len(s), len(y) - i)
        y[i:i + n] += fade(s[:n], 0.005, min(0.04, n / SR / 4)) * g          # края кусков — без щелчков
    return y


def sat(x, drive=2.0):
    return np.tanh(x * drive) / np.tanh(drive)


def sub_thump(f0=48, dur=0.22, drop=0.6):
    t = np.arange(int(dur * SR)) / SR
    f = f0 * (1 - drop * t / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18)


def music_box(notes, tempo=0.42, slow=0.0, detune=0.0, seed=3):
    """Музыкальная шкатулка: удар язычка — сумма негармонических затухающих обертонов (1, 2.76, 5.4, 8.9) + щелчок.
    slow — замедление (пружина кончается), detune — расстройка к концу (в центах)."""
    rng = np.random.default_rng(seed)
    t_cur = 0.0
    events = []
    for i, n in enumerate(notes):
        k = i / max(1, len(notes) - 1)
        dt = tempo * (1 + slow * k ** 2)
        if n is not None:
            f = 440 * 2 ** ((n - 69) / 12) * 2 ** (detune * k * rng.uniform(0.6, 1.2) / 1200)
            events.append((t_cur, f))
        t_cur += dt
    y = np.zeros(int((t_cur + 2.5) * SR))
    for t0, f in events:
        d = int(2.2 * SR)
        t = np.arange(d) / SR
        s = np.zeros(d)
        for ratio, amp, dec in ((1, 1.0, 2.2), (2.76, 0.35, 5.0), (5.40, 0.15, 9.0), (8.93, 0.06, 14.0)):
            s += amp * np.sin(2 * np.pi * f * ratio * t + rng.uniform(0, 6)) * np.exp(-t * dec)
        s[:80] += rng.standard_normal(80) * np.linspace(0.3, 0, 80)
        i = int(t0 * SR)
        y[i:i + d] += s[:len(y) - i]
    return y


# ================================================================== звуки
SOUNDS = []          # (событие, [сигналы], что, где, ru-субтитр, en-субтитр, stream)


def trim(x, thr_db=-46, maxlen=None):
    """Срезать тихий хвост (реверберация ниже порога) и ограничить длину; конец — плавное затухание."""
    env = np.convolve(np.abs(x), np.ones(2048) / 2048, 'same')
    loud = np.where(env > np.max(env) * 10 ** (thr_db / 20))[0]
    end = min(len(x), (loud[-1] + int(0.05 * SR)) if len(loud) else len(x))
    if maxlen:
        end = min(end, int(maxlen * SR))
    return x[:end]


def add(event, variants, what, where, ru, en, stream=False, maxlen=None):
    SOUNDS.append((event, [norm(fade(trim(v, maxlen=maxlen), 0.004, 0.25 if maxlen else 0.08)) for v in variants], what, where, ru, en, stream))


def build():
    C = 'x_'
    # 1. Сердцебиение — школа (каст, сгущение, стадии): медленное сердце, ниже и глуше, под ним — инфраудар
    hb = load('heartbeat_slow_0.wav')
    hb1 = load('heartbeat.mp3_.flac')
    v = []
    for k, (s, src) in enumerate(((-5, hb1[:int(1.3 * SR)]), (-7, hb1[int(1.3 * SR):int(2.6 * SR)]), (-4, hb[:int(1.6 * SR)]))):
        x = lp(semis(src, s), 900)
        th = sub_thump(52 - 4 * k)
        x = mix((x, 0, 1.0), (th, 0.02, 0.5), (th * 0.7, 0.32 + 0.04 * k, 0.4))
        v.append(reverb(x, 0.22, 1.6, 2500, seed=k))
    add('nightmare.heartbeat', v, 'Сердцебиение: глухое, медленное, с инфранизким ударом', 'стадии Погружения, касты, сгущение мифического',
        'Бьётся сердце', 'Heart pounding', maxlen=3.0)
    # 2. Далёкий детский смех — Пустой ребёнок: хихиканье выше (детское), полосой как «через стену», эхо, обратный предвестник
    gg = load('group_giggling.ogg')
    v = []
    for k, (a, b, s) in enumerate(((0.0, 1.6, 3), (1.3, 3.0, 4), (2.6, 4.4, 2))):
        x = semis(gg[int(a * SR):int(b * SR)], s)
        x = bp(x, 450, 3800)
        rev = reverb(x[::-1], 0.9, 2.2, 3000, seed=10 + k)[::-1]           # обратная реверберация — «наплывает» перед смехом
        x = mix((rev, 0, 0.35), (echo(x, 0.29 + 0.04 * k, 0.45, 4, 2600), len(rev) / SR - len(x) / SR, 1.0))
        v.append(reverb(x, 0.45, 2.8, 3200, seed=20 + k))
    add('nightmare.child_laugh', v, 'Далёкий детский смех: хихиканье выше тоном, глухо, с эхом и «наплывом» перед ним',
        'Пустой ребёнок (idle/laugh), галлюцинации стадии 2+', 'Где-то смеётся ребёнок', 'A child laughs somewhere', maxlen=5.5)
    # 3. Шёпот — школа: бормочущие распевы, выше и тише, только шипящие (полоса), слой задом наперёд, широкий зал
    v = []
    for k, (f, s) in enumerate((('chant3.wav', 3), ('chant7.wav', 2), ('chant12.wav', 4))):
        x = load(C + 'Creepychanting/' + f, 0.0, 3.2)
        x = hp(semis(x, s), 1500)
        rv = hp(semis(load(C + 'Creepychanting/' + f, 0.5, 3.0)[::-1], s - 1), 1800) * 0.5
        x = mix((x, 0, 1.0), (rv, 0.35, 0.6))
        v.append(reverb(trem(x, 3.0, 0.3, seed=k), 0.5, 3.0, 6000, seed=30 + k))
    add('nightmare.whisper', v, 'Шёпот: бормотание на непонятном языке, слоем задом наперёд, в пустом зале',
        'стадии 1–3 (вокруг жертвы), «Дом, которого нет»', 'Кто-то шепчет', 'Someone whispers', maxlen=4.5)
    # 4. Скрежет — школа: скрежет металла/камня вниз на октаву + скрип дерева
    cr = load('tree_creak.flac')
    v = []
    for k in range(3):
        x = load(C + 'scrapes/scrape-%d.wav' % (k + 2))
        x = semis(x, -9 - 2 * k)
        c = semis(cr[int(k * 0.9 * SR):int((k * 0.9 + 1.6) * SR)], -3 - k)
        v.append(reverb(mix((x, 0, 0.9), (c, 0.1, 0.6)), 0.35, 2.4, 3500, seed=40 + k))
    add('nightmare.scrape', v, 'Скрежет: когти по камню, ниже на октаву, со скрипом старого дерева', 'стадии 2–3, Ползун рядом',
        'Скрежет', 'Scraping', maxlen=3.6)
    # 5. Ползун — шаги (хруст суставов) и шорох
    v = []
    for k in range(3):
        cl = semis(load(C + 'scrapes/scrape-%d.wav' % (k + 1), 0.0, 0.18), 7 + 2 * k)
        mud = semis(load(C + '25-CC0-mud-sfx/mud_%02d.ogg' % (k + 3)), 5)[:int(0.3 * SR)]
        x = mix((hp(cl, 900), 0, 0.8), (mud, 0.01, 0.5), (hp(cl, 1200)[::-1][:int(0.08 * SR)], 0.09, 0.4))
        v.append(reverb(x, 0.15, 0.8, 5000, seed=50 + k))
    add('nightmare.crawler_step', v, 'Ползун: быстрые влажные шаги с хрустом суставов', 'Ползун — ходьба по земле/стенам',
        'Ползун крадётся', 'Crawler skitters')
    v = []
    for k, f in enumerate(('bug_01.ogg', 'bug_02.ogg', 'bug_03.ogg')):
        x = semis(load(C + '80-CC0-creature-SFX_0/' + f), -8)
        m = semis(load(C + 'monster_-_starninjas/monster.%d.ogg' % (k + 4)), 6)
        v.append(reverb(mix((x, 0, 0.8), (hp(m, 500), 0.05, 0.5)), 0.3, 1.5, 4000, seed=60 + k))
    add('nightmare.crawler_hiss', v, 'Ползун: щёлкающий хрип, голова раскрывается', 'Ползун — idle/attack/pounce',
        'Ползун хрипит', 'Crawler hisses')
    # 6. Пасть — рёв: глубокий рёв ниже, слой рыка, обратный нарастающий «вдох» перед ним
    roar = load('monster_roar.wav')
    v = []
    for k, s in enumerate((-4, -6, -3)):
        r = lp(semis(roar[int(k * 1.2 * SR):int((k * 1.2 + 2.6) * SR)], s), 5000)
        r = r * np.concatenate([np.ones(len(r) - int(0.6 * SR)), np.linspace(1, 0, int(0.6 * SR))])
        g = semis(load(C + 'monster_-_starninjas/monster.%d.ogg' % (k + 1)), -7)
        pre = hp(semis(roar[:int(1.2 * SR)], s - 5), 200)[::-1] * np.linspace(0, 1, len(semis(roar[:int(1.2 * SR)], s - 5))) ** 2
        x = mix((pre, 0, 0.5), (r, len(pre) / SR - 0.05, 1.0), (g, len(pre) / SR + 0.1, 0.6), (sub_thump(38, 0.5, 0.3), len(pre) / SR, 0.7))
        v.append(reverb(sat(x, 1.6), 0.3, 2.6, 2800, seed=70 + k))
    add('nightmare.maw_roar', v, 'Пасть: рёв — глубокий, с рыком и обратным «вдохом» перед ним, гул в груди', 'Пасть — roar',
        'Пасть ревёт', 'The Maw roars', maxlen=5.0)
    v = []
    for k in range(3):
        sp = semis(load(C + 'independent_nu_ljudbank-wet_squish_slurp_impacts/impsplat/impactsplat%02d.mp3.flac' % (k + 2)), -5)
        g = semis(load(C + 'monster_-_starninjas/monster.%d.ogg' % (k + 8)), -4)[:int(0.6 * SR)]
        v.append(reverb(mix((sat(sp, 2.0), 0, 1.0), (g, 0.0, 0.6), (sub_thump(45, 0.3), 0, 0.6)), 0.2, 1.2, 3000, seed=80 + k))
    add('nightmare.maw_bite', v, 'Пасть: укус-таран — тяжёлый влажный удар челюстей', 'Пасть — attack', 'Пасть кусает', 'The Maw bites')
    # 7. Плакальщица — плач (всхлипы) и вопль
    hum = load('ghostly_humming.ogg')
    v = []
    for k, (a, s) in enumerate(((0.5, 5), (4.0, 6), (8.0, 4))):
        x = semis(hum[int(a * SR):int((a + 3.2) * SR)], s)
        x = trem(x, 4.6 + 0.6 * k, 0.75, jitter=0.4, seed=k)                  # всхлипы
        br = hp(semis(load('ghostbreath.flac', 1.0 + k, 2.2 + k), 6), 1500)
        x = mix((x, 0, 1.0), (br, 0.0, 0.45), (br[::-1], 1.9, 0.35))
        v.append(reverb(x, 0.45, 3.2, 3500, seed=90 + k))
    add('nightmare.weeper_cry', v, 'Плакальщица: тихий плач — всхлипывающий напев с прерывистым дыханием, эхо', 'Плакальщица — idle (плачет)',
        'Кто-то плачет', 'Someone weeps', maxlen=4.8)
    gh = load('scaryhighpitchedghost.wav')
    v = []
    for k, (a, s) in enumerate(((0.0, -2), (6.0, -3), (12.0, -1))):
        x = gh[int(a * SR):int((a + 3.0) * SR)]
        x = semis(x, s)
        m = semis(load(C + 'qubodup-GhostMoans/qubodup-GhostMoan0%d.wav' % (k + 1)), 3)
        v.append(reverb(mix((x, 0, 1.0), (m, 0.2, 0.5)), 0.5, 3.5, 4500, seed=100 + k))
    add('nightmare.weeper_wail', v, 'Плакальщица: вопль — высокий призрачный вой со стоном', 'Плакальщица — wail', 'Вопль', 'A wail', maxlen=5.0)
    # 8. Мотыльки — шорох крыльев: большие крылья в 3 раза быстрее, слоями
    w = load(C + 'wings_flap_large/wings_flap_large.flac')
    v = []
    for k in range(3):
        layers = [(bp(speed(w, 2.6 + 0.4 * j + 0.2 * k), 600, 7000), 0.04 * j + 0.02 * k, 0.6) for j in range(5)]
        v.append(reverb(mix(*layers), 0.2, 1.0, 6000, seed=110 + k))
    add('nightmare.moths', v, 'Мотыльки: сухой шорох множества крыльев', 'Мотыльки-глаза — рой, атака', 'Шорох крыльев', 'Wings flutter')
    # 9. Руки из земли — хват: чавканье грязи + шлепок + низкий удар
    v = []
    for k in range(3):
        m1 = semis(load(C + '25-CC0-mud-sfx/mud_%02d.ogg' % (k + 10)), -3)
        sp = semis(load(C + 'independent_nu_ljudbank-wet_squish_slurp_impacts/impsplat/impactsplat%02d.mp3.flac' % (k + 5)), -2)
        v.append(reverb(mix((m1, 0, 0.8), (sp, 0.04, 0.9), (sub_thump(60, 0.2), 0.04, 0.5)), 0.2, 1.0, 3500, seed=120 + k))
    add('nightmare.hands_grab', v, 'Руки из земли: хватают — чавкающая грязь, шлепок', 'Руки из земли — grab', 'Руки хватают', 'Hands grab')
    # 10. Кошмар появляется / исчезает — чернила: пузыри вверх (обратный всплеск) / всплеск и стекание
    v = []
    for k in range(3):
        bub = semis(load(C + 'water-splash-slime-sfx/bubble_0%d.ogg' % (k + 1)), -6)
        sl = semis(load(C + 'water-splash-slime-sfx/slime_0%d.ogg' % (k + 1)), -4)
        x = mix((sl[::-1], 0, 0.8), (bub, len(sl) / SR * 0.7, 0.7))
        v.append(reverb(lp(x, 6000), 0.3, 1.6, 3000, seed=130 + k))
    add('nightmare.ink_rise', v, 'Кошмар появляется: чернила вздуваются и булькают (всплеск задом наперёд)', 'любой кошмар — appear (nm_spawn)',
        'Чернила вздуваются', 'Ink rises')
    v = []
    for k in range(3):
        sp = semis(load(C + 'independent_nu_ljudbank-wet_squish_slurp_impacts/impsplat/impactsplat0%d.mp3.flac' % (k + 1)), -6)
        bub = semis(load(C + 'water-splash-slime-sfx/bubble_0%d.ogg' % (3 - k)), -9)
        v.append(reverb(mix((sp, 0, 1.0), (lp(bub, 3000), 0.1, 0.6)), 0.3, 1.6, 3000, seed=140 + k))
    add('nightmare.ink_fall', v, 'Кошмар исчезает: рассыпается чернилами — всплеск и бульканье', 'любой кошмар — vanish/смерть (nm_despawn)',
        'Кошмар рассыпается', 'Nightmare dissolves')
    # 11. Касты Высших
    atm = load(C + 'independent_nu_ljudbank-atmosphere_moody/atmosmoody/atmoseerie02.mp3.flac')
    cr = load('tree_creak.flac')
    hb1 = load('heartbeat.mp3_.flac')
    v = []
    for k in range(2):
        creak = semis(cr[int((0.5 + k) * SR):int((2.3 + k) * SR)], -6 - k)          # дверь медленно открывается
        wh = hp(semis(load(C + 'Creepychanting/chant%d.wav' % (5 + k), 0, 2.4), 3), 1600)
        drone = lp(semis(atm[int(k * 4 * SR):int((k * 4 + 2.6) * SR)], -5), 1200)
        thud = lp(semis(hb1, -8), 700)
        x = mix((drone, 0, 0.6), (wh, 0.1, 0.5), (creak, 0.6, 0.9), (thud, 2.25, 1.0), (sub_thump(40, 0.6, 0.4), 2.3, 0.8), length=3.4)
        v.append(reverb(x, 0.35, 2.8, 3000, seed=150 + k))
    add('nightmare.cast_house', v, '«Дом, которого нет» (2.5 с): гул, шёпот, медленно скрипит дверь, на 2.3 с — глухой удар (цель провалилась)',
        'каст «Дома, которого нет»', 'Скрипит дверь, которой нет', 'A door that isn\'t there creaks', maxlen=4.0)
    v = []
    for k in range(2):
        drone = lp(semis(atm[int((2 + k * 3) * SR):int((5.2 + k * 3) * SR)], -9), 900)
        swell = drone * np.linspace(0.2, 1.0, len(drone)) ** 2
        bell = reverb(music_box([45, 52], 0.6), 0.6, 4.0, 2500)[:int(3.5 * SR)] * 0.5          # низкий «колокол» луны
        moan = semis(load(C + 'qubodup-GhostMoans/qubodup-GhostMoan0%d.wav' % (k + 3)), -6)
        x = mix((swell, 0, 1.0), (lp(semis(bell, -12), 1500), 1.0, 0.6), (moan, 1.4, 0.4), (sub_thump(36, 0.9, 0.3), 2.8, 1.0),
                (lp(semis(hb1, -9), 600), 2.8, 0.9), length=4.2)
        v.append(reverb(x, 0.4, 3.5, 2500, seed=160 + k))
    add('nightmare.cast_night', v, '«Ночь без рассвета» (3 с): нарастающий гул, низкий колокол восходящей луны, стон, на 2.8 с — удар «заката»',
        'каст «Ночи без рассвета»', 'Восходит красная луна', 'A red moon rises', maxlen=4.6)
    # 12. Мифическое — 12 с ролика (stream): сломанная колыбельная → чернила поднимаются → гул и стена → глаза, удар сердца → тишина → вспышка
    lullaby = [72, 76, 79, 76, 74, 71, 72, None, 72, 76, 79, 81, 79, 76, 74, None, 74, 71, 67, 71, 72]
    mb = music_box(lullaby, 0.27, slow=1.6, detune=-90)
    mb = reverb(hp(mb, 300), 0.45, 3.0, 5000, seed=170)[:int(5.0 * SR)]
    mb *= np.concatenate([np.ones(int(3.6 * SR)), np.linspace(1, 0, len(mb) - int(3.6 * SR))])
    bubbles = semis(load(C + 'water-splash-slime-sfx/loop_bubbles_02.ogg'), -10)[:int(4.5 * SR)]
    bubbles = lp(bubbles, 2500) * np.linspace(0, 1, len(bubbles)) ** 1.5
    drone = lp(semis(atm[:int(5 * SR)], -12), 700) * np.linspace(0.3, 1, int(semis(atm[:int(5 * SR)], -12).shape[0])) ** 2
    whisp = hp(semis(load(C + 'Creepychanting/chant9.wav', 0, 4), 2), 1500)
    beat = lp(semis(load('heartbeat.mp3_.flac'), -7), 800)
    roar = lp(semis(load('monster_roar.wav'), -8), 3000)
    x = mix((mb, 0.0, 0.8),
            (bubbles, 2.0, 0.6), (whisp, 3.5, 0.35),
            (drone, 4.0, 1.0), (semis(gh[:int(3 * SR)], -10), 6.0, 0.25),
            (beat, 9.0, 1.0), (sub_thump(36, 0.8, 0.4), 9.0, 1.0),
            (beat * 0.45, 11.0, 1.0), (sub_thump(34, 0.6, 0.4), 11.0, 0.5),
            (roar[::-1][-int(0.6 * SR):], 11.2, 0.6), (sat(roar[:int(2.5 * SR)], 1.5), 11.8, 0.9), (sub_thump(30, 1.0, 0.2), 11.8, 1.0),
            length=14.5)
    t = np.arange(len(x)) / SR                                            # 10–11.8 с — почти тишина
    duck = np.where((t > 10.1) & (t < 11.75), 0.08, 1.0)
    duck = np.convolve(duck, np.ones(2000) / 2000, 'same')
    x = reverb(x * duck, 0.3, 3.0, 3500, seed=171)[:int(15 * SR)]
    add('nightmare.cast_no_awakening', [x], '«Пробуждение не наступит» (12 с, под ролик): сломанная колыбельная шкатулки (замедляется, '
        'фальшивит) → чернила булькают, шёпот → нарастающий гул и вой → 9 с удар сердца → тишина, 11 с сердце тише → 11.8 с рёв-вспышка',
        'каст мифического — ролик (stream)', 'Мир тонет в чернилах', 'The world drowns in ink', stream=True)
    # 13. Сгущение (каждую минуту мифического): провал звука, два удара сердца, хор шёпота
    v = []
    for k in range(2):
        b = lp(semis(hb1, -7 - k), 800)
        ch = mix(*[(hp(semis(load(C + 'Creepychanting/chant%d.wav' % (10 + j + k), 0, 2.5), 2 + j), 1400), 0.05 * j, 0.4) for j in range(3)])
        dr = lp(semis(atm[int((6 + 2 * k) * SR):int((9 + 2 * k) * SR)], -12), 600)
        x = mix((dr * np.linspace(1, 0.2, len(dr)), 0, 0.8), (b, 0.5, 1.0), (sub_thump(38, 0.6), 0.5, 0.9), (b, 1.1, 1.0),
                (sub_thump(36, 0.6), 1.1, 0.9), (ch, 1.2, 0.6), length=3.6)
        v.append(reverb(x, 0.4, 3.0, 3000, seed=180 + k))
    add('nightmare.thicken', v, 'Сгущение: мир глохнет, два удара сердца, хор шёпота', 'мифическое — каждую минуту (nightmare_no_awakening_thicken)',
        'Кошмар сгущается', 'The nightmare thickens', maxlen=4.6)


# ================================================================== запись
def enc(x, path, fmt='ogg'):
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2').tobytes()
    args = ['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '-']
    args += ['-c:a', 'libvorbis', '-q:a', '5'] if fmt == 'ogg' else ['-c:a', 'libmp3lame', '-b:a', '160k']
    subprocess.run(args + [path], input=pcm, check=True)


def write_all():
    os.makedirs(OUT, exist_ok=True)
    sj_path = os.path.join(A, 'sounds.json')
    sj = json.load(open(sj_path, encoding='utf-8'))
    subs = {}
    demo, rows, t = [], [], 0.0
    gap = np.zeros(int(0.5 * SR))
    n = 0
    for event, variants, what, where, ru, en, stream in SOUNDS:
        names = []
        for i, x in enumerate(variants):
            fn = '%s_%d' % (event.split('.', 1)[1], i + 1)
            enc(x, os.path.join(OUT, fn + '.ogg'))
            names.append(fn)
            n += 1
            demo += [gap, x]
            t += 0.5
            rows.append((n, t, len(x) / SR, event, i + 1, what, where))
            t += len(x) / SR
        ev = {'subtitle': 'subtitles.pohsmp_core.' + event, 'sounds': [{'name': 'pohsmp_core:nightmare/' + f, **({'stream': True} if stream else {})}
                                                                         for f in names]}
        sj[event] = ev
        subs['subtitles.pohsmp_core.' + event] = (ru, en)
    with open(sj_path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(sj, fh, ensure_ascii=False, indent=2)
        fh.write('\n')
    for code, idx in (('ru_ru', 0), ('en_us', 1)):
        p = os.path.join(A, 'lang', code + '.json')
        d = json.load(open(p, encoding='utf-8'))
        for k, v in subs.items():
            d.setdefault(k, v[idx])
        with open(p, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(d, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
    media = os.path.join(ROOT, 'docs', 'media')
    enc(np.concatenate(demo + [gap]), os.path.join(media, 't25_sounds_demo.mp3'), 'mp3')
    with open(os.path.join(media, 't25_sounds_list.md'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('# T25 «Кошмары» — звуки на согласование (демо `t25_sounds_demo.mp3`)\n\n'
                 'Все звуки подряд, перед каждым — 0.5 с тишины. Генератор — `tools/gen_nightmare_sounds.py`; файлы — '
                 '`assets/pohsmp_core/sounds/nightmare/`. События `nightmare.*` в `sounds.json` **ждут согласования** — код их не подключает.\n\n'
                 '| № | время в демо | длина | событие (вариант) | что это | где звучит |\n|---|---|---|---|---|---|\n')
        for no, t0, L, ev, var, what, where in rows:
            fh.write('| %d | %d:%04.1f | %.1f с | `%s` (%d) | %s | %s |\n' % (no, int(t0 // 60), t0 % 60, L, ev, var, what, where))
        fh.write('\n## Источники (все CC0, opengameart.org) — обработаны: высота, скорость, реверс, эхо, реверберация, фильтры, слои\n\n')
        for f, (page, author) in SOURCES.items():
            fh.write('- `%s` — %s, https://opengameart.org/content/%s\n' % (f, author, page))
        fh.write('\nМузыкальная шкатулка (колыбельная, «колокол» луны) и инфранизкие удары — синтез.\n')
    print('звуков: %d файлов, %d событий; демо %.1f с' % (n, len(SOUNDS), t))


if __name__ == '__main__':
    fetch()
    build()
    write_all()
