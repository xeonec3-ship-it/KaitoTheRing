#!/usr/bin/env python3
"""
Свои звуки всей магии мода (задача владельца «Делай звуки для всей магии кастомные», 19.11.2026).

Как устроено:
  1. Разбор кода: все вызовы ванильных SoundEvents.* в заклинаниях (spell/**, mythic/, erased/, ember/, illusion/, DivineEvents, Reg)
     -> место (файл, строка, метод), заклинание, школа, роль (каст/нарастание/выпуск/цикл/удар/конец/ошибка), «смысл» звука (KIND).
     Пропускаются уже свои: Кошмары (nightmare/*, nightmare.*), музыка Врат/Ковена/Сна бабочки; не магия — экипировка мантии.
  2. Событие на каждое (заклинание, роль, смысл): pohsmp_core:spell.<id>.<роль>[_<смысл>] — одно наше событие заменяет все
     ванильные звуки одного места (слой из 2–3 ванильных = один наш слоёный звук). Школьные события каста — school.<школа>.cast.
  3. Звук = «жест» по смыслу (взрыв, нарастание, звон, разрыв...) из записей (CC0 и др. с OpenGameArt, список SOURCES) +
     «подпись школы» (огонь — треск пламени, лёд — хрусталь, святая — колокол и хор...) + обработка школы. Вариации — разный выбор
     записей, высоты, смещений (зерно = имя события). Голого синтеза нет, кроме инфранизкого удара под взрывами.
Пишет:
  assets/pohsmp_core/sounds/spell/<школа>/<событие>_<n>.ogg (моно, 44.1 кГц, Vorbis q3), sounds.json (volume 0.5), lang ru/en,
  docs/sounds/catalog.md, docs/sounds/replacements.md, docs/sounds/sources.md, docs/sounds/review.json, docs/sounds/mp3/*.mp3
Запуск:  python3 tools/gen_spell_sounds.py [--school fire,ice,...] [--docs-only]
  (нужны ffmpeg, numpy, scipy, py7zr; исходники качаются в tools/.cache/spell_snd, не в git)
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
import zipfile

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_nightmare_sounds import (bp, echo, fade, hp, lp, mix, norm, reverb, sat, semis, speed, sub_thump, trem)  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, '..'))
JAVA = os.path.join(ROOT, 'src', 'main', 'java', 'ru', 'pohsmp', 'core')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
OUT = os.path.join(A, 'sounds', 'spell')
DOCS = os.path.join(ROOT, 'docs', 'sounds')
CACHE = os.path.join(HERE, '.cache', 'spell_snd')
SR = 44100
OGA = 'https://opengameart.org/sites/default/files/'
VOLUME = 0.5                                     # владелец (T25): «тише» — громкость по умолчанию

# ================================================================== источники: файл на OGA -> (страница, автор, лицензия)
SOURCES = {
    'fire-1.wav': ('fire-crackling', 'AntumDeluge', 'CC0'),
    'fire.wav': ('fireplace-sound-loop', 'PagDev', 'CC0'),
    'flame_0.ogg': ('catching-fire', 'themightyglider', 'CC0'),
    'qubodupFireLoop.ogg': ('fire-loop', 'qubodup', 'CC-BY 3.0'),
    'lava.flac': ('lava-splash', 'Michel Baradari', 'CC-BY 3.0'),
    '80-CC0-RPG-SFX_0.zip': ('80-cc0-rpg-sfx', 'rubberduck', 'CC0'),
    '25-CC0-bang-sfx.zip': ('25-cc0-bang-firework-sfx', 'rubberduck', 'CC0'),
    'explosions.7z': ('2-high-quality-explosions', 'Michel Baradari', 'CC-BY 3.0'),
    'IceShatters_0.zip': ('ice-breakingshattering', 'IgnasD', 'CC0'),
    'freeze.wav': ('freeze-spell-0', 'artisticdude', 'CC0'),
    'icespells.zip': ('ice-spells', 'bart', 'CC0'),
    'rain-thunder.ogg': ('rain-long-thunder', 'WuxiaScrub', 'CC0'),
    'thunderclap_0.ogg': ('thunder', 'Jerimee', 'CC-BY 3.0'),
    'thunder-seq.wav': ('thunder', 'Jerimee', 'CC-BY 3.0'),
    'buzz_0.ogg': ('electric-buzz', 'themightyglider', 'CC0'),
    'charge.wav': ('electricity-game-sound-pack', 'faxcorp', 'CC0'),
    'chargestart.wav': ('electricity-game-sound-pack', 'faxcorp', 'CC0'),
    'crackleelectricityloop.wav': ('electricity-game-sound-pack', 'faxcorp', 'CC0'),
    'deathboom.wav': ('electricity-game-sound-pack', 'faxcorp', 'CC0'),
    'groundhit.wav': ('electricity-game-sound-pack', 'faxcorp', 'CC0'),
    'hit.wav': ('electricity-game-sound-pack', 'faxcorp', 'CC0'),
    'hjm-shield_hum_50.wav': ('force-field-electric-hum', 'Varkalandar', 'CC-BY 3.0'),
    'bell_ding1.wav': ('bell-dingschimes', 'PWL', 'CC0'),
    'bell_ding2.wav': ('bell-dingschimes', 'PWL', 'CC0'),
    'bell_ding3.wav': ('bell-dingschimes', 'PWL', 'CC0'),
    'bell_ding4.wav': ('bell-dingschimes', 'PWL', 'CC0'),
    'pleasing-bell.wav': ('pleasing-bell-sound-effect', 'Spring Spring', 'CC0'),
    'sd_0.wav': ('point-bell', 'HaelDB', 'CC0'),
    'bell.wav': ('correct-bell', 'Fupi', 'CC0'),
    'Tolling%20Bell-Bright_3.mp3': ('tolling-bell-sfx', 'Fun Gi Development', 'CC-BY 4.0'),
    'Distant%20tolling%20bell_3.mp3': ('tolling-bell-sfx', 'Fun Gi Development', 'CC-BY 4.0'),
    'churchbell.flac': ('church-bell', 'Ulrich Metzner', 'CC-BY-SA 3.0'),
    'hjm-glass_bell_1.wav': ('glass-bell-sounds', 'Varkalandar', 'CC-BY 3.0'),
    'hjm-glass_bell_3.wav': ('glass-bell-sounds', 'Varkalandar', 'CC-BY 3.0'),
    'hjm-glass_bell_5.wav': ('glass-bell-sounds', 'Varkalandar', 'CC-BY 3.0'),
    'hjm-glass_bell_7.wav': ('glass-bell-sounds', 'Varkalandar', 'CC-BY 3.0'),
    '1_1.ogg': ('crystal-voices', 'Spellweaver', 'CC-BY-SA 3.0'),
    '2_0.ogg': ('crystal-voices', 'Spellweaver', 'CC-BY-SA 3.0'),
    '3_0.ogg': ('crystal-voices', 'Spellweaver', 'CC-BY-SA 3.0'),
    'ghostly_humming.ogg': ('ghostly-humming', 'Nocturnal_Vanguard (AuraVoice)', 'CC0'),
    'Creepychanting.zip': ('creepy-incoherent-chanting', 'OwlishMedia', 'CC0'),
    'ghostbreath.flac': ('ghost-breath', 'qubodup', 'CC0'),
    'heartbeat_slow_0.wav': ('heartbeat-sounds', 'bart', 'CC0'),
    'heartbeat.mp3_.flac': ('heartbeat-single-sound', 'qubodup', 'CC0'),
    'independent_nu_ljudbank-wet_squish_slurp_impacts.7z': ('8-wet-squish-slurp-impacts', 'qubodup / Independent.nu', 'CC0'),
    'rippingintomeat_0.mp3': ('ripping-into-meat', 'Eldritch Grim', 'CC0'),
    'water-splash-slime-sfx.zip': ('40-cc0-water-splash-slime-sfx', 'rubberduck', 'CC0'),
    'monster_roar.wav': ('cc0-deep-monster-roar', 'trazzz123', 'CC0'),
    'tree_creak.flac': ('tree-creaking', 'AntumDeluge', 'CC0'),
    'independent_nu_ljudbank-wood_crack_hit_destruction.7z': ('35-wooden-crackshitsdestructions', 'Independent.nu', 'CC0'),
    '100-CC0-wood-metal-SFX.zip': ('100-cc0-metal-and-wood-sfx', 'rubberduck', 'CC0'),
    'qubodup-rustle.7z': ('20-rustles-dry-leaves', 'qubodup', 'CC0'),
    'PortalSFX.zip': ('portal-sound', 'IgnasD', 'CC0'),
    'tts.zip': ('4-space-portal-sounds', 'Écrivain', 'CC0'),
    'teleport.wav': ('teleport-spell', 'Ogrebane', 'CC0'),
    'space-wind_0.mp3': ('space-winds', 'aquinn', 'CC0'),
    'qubodup-PowerDrain.7z': ('energy-drain', 'qubodup', 'CC0'),
    'dark_magic.7z': ('3-dark-magic-spells', 'qubodup', 'CC0'),
    'Dreamscape%20Drone.wav': ('dreamscape-drone', 'jdagenet', 'CC-BY 3.0'),
    'drone53.wav': ('droning-sound-effects', 'bretbernhoft', 'CC0'),
    'drone55.wav': ('droning-sound-effects', 'bretbernhoft', 'CC0'),
    'drone57.wav': ('droning-sound-effects', 'bretbernhoft', 'CC0'),
    'drone59.wav': ('droning-sound-effects', 'bretbernhoft', 'CC0'),
    'low-rumbling-176033.mp3': ('low-rumbling', 'Musheran', 'CC0'),
    'independent_nu_ljudbank-atmosphere_moody.7z': ('4-atmospheric-ghostly-loops', 'qubodup / Independent.nu', 'CC0'),
    'glass_breaking.wav': ('glass-break', 'Till Behrend', 'CC0'),
    'sfx_breaking_and_falling.zip': ('75-cc0-breaking-falling-hit-sfx', 'rubberduck', 'CC0'),
    '100-CC0-SFX_0.zip': ('100-cc0-sfx', 'rubberduck', 'CC0'),
    'sfx_100_v2.zip': ('100-cc0-sfx-2', 'rubberduck', 'CC0'),
    'sci-fi-sfx.zip': ('50-cc0-sci-fi-sfx', 'rubberduck', 'CC0'),
    'wind%20woosh%20loop.ogg': ('wind-whoosh-loop', 'SketchMan3', 'CC0'),
    'whoosh2_0.wav': ('air-whoosh', 'pyranostudios', 'CC0'),
    'swishes.zip': ('swishes-sound-pack', 'artisticdude', 'CC0'),
    '8_rpg_battle_magic_sfx_free_samples.zip': ('8-magic-attacks', 'leohpaz', 'CC-BY 4.0'),
    'Magic%20SFX%20Preview%20Pack.zip': ('magic-sfx-sample', 'ViRiX', 'CC-BY 3.0'),
    'shimmer_1.flac': ('shimmer-glitter-magic', 'The Berklee College of Music', 'CC-BY 3.0'),
    'Magic%20Shield.wav': ('magic-shield', 'spookymodem', 'CC-BY 3.0'),
    'Flipping%20Through%20Book.wav': ('book-pages', 'spookymodem', 'CC-BY 3.0'),
}


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


# ================================================================== пулы записей по смыслу (glob относительно CACHE)
POOLS = {
    'fire_tex': ['fire-1.wav', 'fire.wav', 'qubodupFireLoop.ogg'],
    'fire_burst': ['x_80-CC0-RPG-SFX_0/spell_fire_0[1-7].ogg', 'flame_0.ogg', 'x_Magic%20SFX%20Preview%20Pack/Fire impact 1.wav',
                   'x_8_rpg_battle_magic_sfx_free_samples/04_Fire_explosion_04_medium.wav'],
    'lava': ['lava.flac'],
    'boom': ['x_explosions/explosions/explode*.wav', 'x_25-CC0-bang-sfx/bang_0[1-9].ogg', 'x_25-CC0-bang-sfx/cannon_0[1-5].ogg',
             'deathboom.wav', 'x_100-CC0-SFX_0/explosion.ogg', 'x_sci-fi-sfx/explosion_0[12].ogg'],
    'firework': ['x_25-CC0-bang-sfx/fw_0[1-6].ogg'],
    'thunder': ['thunderclap_0.ogg', 'thunder-seq.wav', 'x_sfx_100_v2/sfx100v2_thunder_01.ogg',
                'x_8_rpg_battle_magic_sfx_free_samples/18_Thunder_02.wav'],
    'zap': ['hit.wav', 'groundhit.wav', 'buzz_0.ogg', 'crackleelectricityloop.wav'],
    'zap_tone': ['charge.wav', 'chargestart.wav', 'hjm-shield_hum_50.wav', 'crackleelectricityloop.wav'],
    'ice': ['x_IceShatters_0/IceShatters/*.ogg', 'x_icespells/*.wav', 'freeze.wav',
            'x_8_rpg_battle_magic_sfx_free_samples/13_Ice_explosion_01.wav', 'x_Magic%20SFX%20Preview%20Pack/Ice attack 2.wav'],
    'glass': ['glass_breaking.wav', 'x_sfx_breaking_and_falling/bfh1_glass_breaking_0*.ogg', 'x_100-CC0-SFX_0/glass_0[45].ogg',
              'x_sfx_100_v2/sfx100v2_glass_0*.ogg'],
    'glass_tick': ['x_100-CC0-SFX_0/glass_0[123].ogg', 'x_sfx_breaking_and_falling/bfh1_glass_hit_0*.ogg',
                   'x_80-CC0-RPG-SFX_0/item_gem_0*.ogg'],
    'bell': ['bell_ding*.wav', 'pleasing-bell.wav', 'sd_0.wav', 'bell.wav', 'x_100-CC0-SFX_0/bell_0[13].ogg'],
    'big_bell': ['Tolling%20Bell-Bright_3.mp3', 'Distant%20tolling%20bell_3.mp3', 'churchbell.flac'],
    'glass_bell': ['hjm-glass_bell_*.wav'],
    'gong': ['x_100-CC0-SFX_0/gong_0[12].ogg', 'x_100-CC0-wood-metal-SFX/metal_hit_0*.ogg', 'x_sfx_100_v2/sfx100v2_metal_hit_0*.ogg'],
    'choir': ['1_1.ogg', '2_0.ogg', '3_0.ogg', 'ghostly_humming.ogg'],
    'whisper': ['x_Creepychanting/chant*.wav', 'x_Creepychanting/ethereal_chant_Subclip*.wav'],
    'drone': ['drone5[3579].wav', 'Dreamscape%20Drone.wav', 'x_independent_nu_ljudbank-atmosphere_moody/atmosmoody/*.flac',
              'low-rumbling-176033.mp3'],
    'space': ['space-wind_0.mp3', 'x_sci-fi-sfx/loop_ambient_0*.ogg', 'x_sci-fi-sfx/loop_ambient_weird.ogg'],
    'portal': ['x_PortalSFX/PortalSFX/porta.ogg', 'x_tts/*.mp3', 'teleport.wav', 'x_sci-fi-sfx/teleport_0[12].ogg',
               'x_qubodup-PowerDrain/qubodup-PowerDrain/ogg/qubodup-PowerDrain.ogg'],
    'wind': ['wind%20woosh%20loop.ogg', 'whoosh2_0.wav', 'x_sfx_100_v2/sfx100v2_air_0*.ogg',
             'x_8_rpg_battle_magic_sfx_free_samples/25_Wind_01.wav', 'x_Magic%20SFX%20Preview%20Pack/Wind effects 5.wav'],
    'swish': ['x_swishes/swishes/swish-*.wav'],
    'wood': ['x_independent_nu_ljudbank-wood_crack_hit_destruction/wood_impact/*.flac', 'x_100-CC0-wood-metal-SFX/wood_hit_0*.ogg',
             'x_100-CC0-wood-metal-SFX/wood_breaking_0*.ogg', 'x_100-CC0-wood-metal-SFX/wood_cracking_0*.ogg'],
    'creak': ['tree_creak.flac', 'x_100-CC0-wood-metal-SFX/wood_squeak_0*.ogg'],
    'leaves': ['x_qubodup-rustle/rustle/*.flac'],
    'earth': ['x_8_rpg_battle_magic_sfx_free_samples/30_Earth_02.wav', 'x_sfx_breaking_and_falling/bfh1_rock_*.ogg',
              'x_80-CC0-RPG-SFX_0/stones_0*.ogg'],
    'wet': ['x_independent_nu_ljudbank-wet_squish_slurp_impacts/impsplat/*.flac', 'x_water-splash-slime-sfx/slime_*.ogg',
            'x_80-CC0-RPG-SFX_0/creature_slime_0*.ogg'],
    'meat': ['rippingintomeat_0.mp3'],
    'splash': ['x_water-splash-slime-sfx/splash_*.ogg', 'x_water-splash-slime-sfx/bubble_0*.ogg'],
    'heart': ['heartbeat_slow_0.wav', 'heartbeat.mp3_.flac'],
    'metal': ['x_100-CC0-wood-metal-SFX/metal_slam_01.ogg', 'x_100-CC0-wood-metal-SFX/hammer_0*.ogg', 'x_100-CC0-wood-metal-SFX/metal_sheet_0*.ogg',
              'x_100-CC0-SFX_0/slam_0*.ogg', 'x_100-CC0-SFX_0/metal_0*.ogg'],
    'chain': ['x_80-CC0-RPG-SFX_0/chain_0[1-3].ogg', 'x_100-CC0-wood-metal-SFX/keys_0*.ogg'],
    'blade': ['x_80-CC0-RPG-SFX_0/blade_0[1-3].ogg'],
    'paper': ['x_80-CC0-RPG-SFX_0/book_0[1-4].ogg', 'Flipping%20Through%20Book.wav', 'x_100-CC0-SFX_0/paper_0*.ogg'],
    'magic': ['x_80-CC0-RPG-SFX_0/spell_0[12].ogg', 'x_Magic%20SFX%20Preview%20Pack/Misc 02.wav',
              'x_8_rpg_battle_magic_sfx_free_samples/45_Charge_05.wav', 'Magic%20Shield.wav', 'shimmer_1.flac'],
    'heal': ['x_Magic%20SFX%20Preview%20Pack/Healing Full.wav', 'shimmer_1.flac'],
    'dark': ['x_dark_magic/dark_magic/*.flac', 'x_qubodup-PowerDrain/qubodup-PowerDrain/ogg/qubodup-PowerDrain.ogg'],
    'roar': ['monster_roar.wav', 'x_80-CC0-RPG-SFX_0/creature_roar_0[1-3].ogg', 'x_80-CC0-RPG-SFX_0/creature_monster_0*.ogg'],
    'soul': ['ghostbreath.flac'],
    'weird': ['x_100-CC0-SFX_0/weird_0*.ogg', 'x_sci-fi-sfx/weird_0*.ogg'],
    'poison': ['x_8_rpg_battle_magic_sfx_free_samples/46_Poison_01.wav'],
}
_FILES = {}
_LOADED = {}


def pool(name):
    if name not in _FILES:
        fs = []
        for g in POOLS[name]:
            fs += sorted(glob.glob(os.path.join(CACHE, g)))
        if not fs:
            raise SystemExit('пустой пул ' + name)
        _FILES[name] = fs
    return _FILES[name]


def load_file(path):
    if path not in _LOADED:
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                             capture_output=True, check=True).stdout
        x = np.frombuffer(raw, np.float32).astype(np.float64)
        x = x - np.mean(x)
        _LOADED[path] = x / (np.max(np.abs(x)) + 1e-9)
    return _LOADED[path]


def onset(x):
    """Индекс начала звука (первое превышение -30 дБ от пика)."""
    i = np.where(np.abs(x) > 0.03)[0]
    return int(i[0]) if len(i) else 0


def take(rng, name, dur=None, from_start=True):
    """Случайная запись пула; длинные — случайный кусок dur с; короткие — с начала звука."""
    fs = pool(name)
    x = load_file(fs[rng.integers(len(fs))])
    if dur is None:
        return x[onset(x):].copy()
    n = int(dur * SR)
    if len(x) <= n * 1.5 or from_start:
        a = onset(x) if len(x) <= n * 1.5 else rng.integers(0, max(1, len(x) - n))
    else:
        a = rng.integers(0, max(1, len(x) - n))
    y = x[a:a + n].copy()
    m = np.max(np.abs(y)) + 1e-9
    return y / m


# ================================================================== обработка
def env(x, a=0.01, r=0.1):
    return fade(x, a, min(r, len(x) / SR / 2))


def cut(x, dur):
    return x[:int(dur * SR)]


def glide(x, k0, k1):
    """Высота плавно от k0 до k1 (переменная скорость чтения)."""
    n = len(x)
    rates = np.linspace(k0, k1, n)
    pos = np.cumsum(rates)
    pos = pos[pos < n - 1]
    return np.interp(pos, np.arange(n), x)


def ringmod(x, f=180.0, depth=0.5):
    t = np.arange(len(x)) / SR
    return x * (1 - depth + depth * np.sin(2 * np.pi * f * t))


def crush(x, bits=6, keep=4):
    q = 2 ** bits
    y = np.round(x * q) / q
    y = np.repeat(y[::keep], keep)[:len(x)]
    return y


def flange(x, depth_ms=3.0, rate=0.4):
    n = len(x)
    t = np.arange(n) / SR
    d = (1 + np.sin(2 * np.pi * rate * t)) * depth_ms / 2000 * SR
    return 0.6 * x + 0.5 * np.interp(np.arange(n) - d, np.arange(n), x)


def shimmer(x, rng):
    up = semis(x, 12)
    return mix((x, 0, 1.0), (echo(hp(up, 1500), 0.18, 0.5, 4, 7000), 0.09, 0.35))


def rev_swell(x, t60=2.0, bright=5000, seed=0):
    """Обратная реверберация: звук «наплывает» из тишины."""
    return reverb(x[::-1], 1.0, t60, bright, seed=seed)[::-1]


def loudnorm(x, rms_db=-17.0, peak=0.89):
    x = norm(x, 1.0)
    r = np.sqrt(np.mean(x ** 2)) + 1e-9
    g = 10 ** (rms_db / 20) / r
    x = x * g
    return np.tanh(x / peak) * peak if np.max(np.abs(x)) > peak else x


def trim(x, thr_db=-44, maxlen=None):
    e = np.convolve(np.abs(x), np.ones(1024) / 1024, 'same')
    loud = np.where(e > np.max(e) * 10 ** (thr_db / 20))[0]
    a = max(0, loud[0] - 256) if len(loud) else 0
    b = min(len(x), loud[-1] + int(0.05 * SR)) if len(loud) else len(x)
    if maxlen:
        b = min(b, a + int(maxlen * SR))
    return x[a:b]


# ================================================================== школы: подпись (пулы ring/tone/hit/tex) и обработка
SCHOOLS = {
    'fire': dict(ru='Огонь', sig='треск и рёв пламени, жар', ring='fire_burst', tone='fire_tex', hit='fire_burst', tex='fire_tex', bias=-2),
    'ice': dict(ru='Лёд', sig='хрусталь, треск и звон льда, холодный ветер', ring='glass_bell', tone='wind', hit='ice', tex='ice', bias=3),
    'lightning': dict(ru='Молния', sig='разряд, треск электричества, гул и раскат грома', ring='zap', tone='zap_tone', hit='zap', tex='zap', bias=0),
    'holy': dict(ru='Святая', sig='колокольчики и светлый хор', ring='bell', tone='choir', hit='bell', tex='choir', bias=2),
    'blood': dict(ru='Кровь', sig='влажный пульс, сердцебиение, глухо', ring='heart', tone='drone', hit='wet', tex='wet', bias=-4),
    'ender': dict(ru='Эндер', sig='искажённый гул, пространство «плывёт», портал', ring='portal', tone='space', hit='portal', tex='portal', bias=-3),
    'nature': dict(ru='Природа', sig='дерево, корни, листва', ring='wood', tone='leaves', hit='wood', tex='leaves', bias=0),
    'eldritch': dict(ru='Мистическая', sig='шёпот и низкий гул', ring='gong', tone='whisper', hit='dark', tex='whisper', bias=-5),
    'evocation': dict(ru='Вызывание', sig='магический металл: гонг, щиты, вспышка заклятия', ring='gong', tone='magic', hit='metal', tex='magic', bias=0),
    'wind': dict(ru='Ветер', sig='порывы и свист воздуха', ring='swish', tone='wind', hit='swish', tex='wind', bias=1),
    'higher': dict(ru='Высшая', sig='алый звон: металлический гонг с обратным наплывом, кольцевое «дрожание»', ring='gong', tone='drone',
                   hit='gong', tex='glass_tick', bias=-1),
    'divine': dict(ru='Божественная', sig='золотой хор и большой колокол', ring='big_bell', tone='choir', hit='big_bell', tex='choir', bias=-2),
    'forbidden': dict(ru='Запретная (Мироздание)', sig='искажение реальности: реверс, «цифровой» распад, тишина и разрыв', ring='weird',
                      tone='drone', hit='meat', tex='weird', bias=-4),
    'silent': dict(ru='Безмолвная', sig='чистый хрустальный звон', ring='glass_bell', tone='glass_bell', hit='glass_tick', tex='glass_bell', bias=5),
    'illusion': dict(ru='Иллюзии', sig='стекло и зеркала, мерцающее эхо', ring='glass_bell', tone='whisper', hit='glass', tex='glass_tick', bias=2),
}


def school_fx(x, school, rng, seed):
    if school == 'fire':
        x = reverb(sat(x, 1.4), 0.22, 1.2, 4500, seed=seed)
    elif school == 'ice':
        x = reverb(hp(x, 180), 0.3, 1.6, 9000, seed=seed)
    elif school == 'lightning':
        x = reverb(sat(x, 2.2), 0.25, 1.4, 6000, seed=seed)
    elif school == 'holy':
        x = reverb(x, 0.42, 3.0, 7000, seed=seed)
    elif school == 'blood':
        x = reverb(lp(x, 3200), 0.25, 1.4, 2500, seed=seed)
    elif school == 'ender':
        x = reverb(flange(x, 4.0, 0.6), 0.38, 2.6, 4000, seed=seed)
    elif school == 'nature':
        x = reverb(x, 0.25, 1.5, 5000, seed=seed)
    elif school == 'eldritch':
        x = reverb(lp(x, 4500), 0.45, 3.5, 2800, seed=seed)
    elif school == 'evocation':
        x = reverb(x, 0.3, 1.8, 6000, seed=seed)
    elif school == 'wind':
        x = reverb(x, 0.22, 1.2, 6000, seed=seed)
    elif school == 'higher':
        x = reverb(ringmod(x, 90 + rng.uniform(0, 60), 0.25), 0.38, 2.6, 5000, seed=seed)
    elif school == 'divine':
        x = reverb(x, 0.45, 4.0, 5500, seed=seed)
    elif school == 'forbidden':
        x = 0.7 * x + 0.3 * crush(x, 5, 3)
        x = reverb(x, 0.4, 3.0, 3500, seed=seed)
    elif school == 'silent':
        x = reverb(hp(x, 300), 0.45, 3.5, 11000, seed=seed)
    elif school == 'illusion':
        x = reverb(shimmer(x, rng), 0.35, 2.4, 8000, seed=seed)
    return x


# ================================================================== жесты по смыслу звука (KIND)
# смысл: (ru-описание для каталога, ru-субтитр, en-субтитр)
KINDS = {
    'boom': ('взрыв / тяжёлый удар', 'грохот', 'blast'),
    'thunder': ('раскат грома', 'раскат', 'thunderclap'),
    'zap': ('разряд / вспышка удара', 'разряд', 'discharge'),
    'powerup': ('нарастание силы, «включение»', 'сила нарастает', 'power rises'),
    'powerdown': ('спад, «выключение»', 'сила угасает', 'power fades'),
    'hum': ('гул / фон', 'гул', 'hum'),
    'chime': ('звон, отсчёт, отметка', 'звон', 'chime'),
    'resonate': ('долгий резонанс', 'резонанс', 'resonance'),
    'bell': ('колокол', 'колокол', 'bell'),
    'shatter': ('раскол, осколки', 'раскалывается', 'shatters'),
    'form': ('кристалл/стекло встаёт', 'вырастает', 'forms'),
    'portal': ('разрыв пространства, переход', 'разрыв пространства', 'space tears'),
    'roar': ('рёв / грозный гул', 'рёв', 'roar'),
    'heart': ('удар сердца', 'бьётся сердце', 'heartbeat'),
    'whoosh': ('свист, взмах, порыв', 'свист', 'whoosh'),
    'fire': ('вспышка пламени', 'пламя', 'flames'),
    'hiss': ('пламя гаснет', 'шипит', 'hiss'),
    'soul': ('душа / вздох духа', 'вздох духа', 'spirit sighs'),
    'magic': ('заклятие плетётся', 'плетётся заклятие', 'spell weaves'),
    'chain': ('цепи, оковы', 'звенят цепи', 'chains rattle'),
    'slam': ('тяжёлый металлический удар', 'тяжёлый удар', 'heavy strike'),
    'wet': ('влажный удар, кровь', 'хлюпает', 'squelch'),
    'snow': ('снег и мороз', 'метёт снег', 'snow swirls'),
    'earth': ('земля, камень, корни', 'дрожит земля', 'earth rumbles'),
    'leaves': ('листва', 'шелест', 'rustle'),
    'wood': ('дерево', 'трещит дерево', 'wood creaks'),
    'buzz': ('треск-жужжание', 'трещит', 'crackle'),
    'paper': ('страницы', 'шелестят страницы', 'pages rustle'),
    'fanfare': ('торжество, исцеление', 'торжество', 'triumph'),
    'click': ('щелчок', 'щелчок', 'click'),
}

VANILLA_KIND = {
    'GENERIC_EXPLODE': 'boom', 'DRAGON_FIREBALL_EXPLODE': 'boom', 'FIREWORK_ROCKET_LARGE_BLAST': 'boom', 'FIREWORK_ROCKET_BLAST': 'boom',
    'WARDEN_SONIC_BOOM': 'boom', 'LIGHTNING_BOLT_THUNDER': 'thunder', 'TRIDENT_THUNDER': 'thunder', 'LIGHTNING_BOLT_IMPACT': 'zap',
    'BEACON_ACTIVATE': 'powerup', 'RESPAWN_ANCHOR_CHARGE': 'powerup', 'END_PORTAL_FRAME_FILL': 'powerup', 'WARDEN_SONIC_CHARGE': 'powerup',
    'BEACON_POWER_SELECT': 'powerup', 'RESPAWN_ANCHOR_SET_SPAWN': 'powerup', 'FIREWORK_ROCKET_LAUNCH': 'whoosh',
    'BEACON_DEACTIVATE': 'powerdown', 'BEACON_AMBIENT': 'hum', 'PORTAL_AMBIENT': 'hum', 'AMBIENT_CAVE': 'hum',
    'AMBIENT_SOUL_SAND_VALLEY_MOOD': 'hum', 'AMBIENT_BASALT_DELTAS_LOOP': 'hum',
    'AMETHYST_BLOCK_CHIME': 'chime', 'NOTE_BLOCK_CHIME': 'chime', 'NOTE_BLOCK_HAT': 'click', 'AMETHYST_CLUSTER_HIT': 'chime',
    'AMETHYST_BLOCK_HIT': 'chime', 'FIREWORK_ROCKET_TWINKLE': 'chime', 'AMETHYST_BLOCK_RESONATE': 'resonate', 'BELL_RESONATE': 'resonate',
    'BELL_BLOCK': 'bell', 'GLASS_BREAK': 'shatter', 'AMETHYST_CLUSTER_BREAK': 'shatter', 'AMETHYST_BLOCK_BREAK': 'shatter',
    'GLASS_PLACE': 'form', 'END_PORTAL_SPAWN': 'portal', 'END_GATEWAY_SPAWN': 'portal', 'ENDERMAN_TELEPORT': 'portal',
    'PORTAL_TRAVEL': 'portal', 'ENDER_EYE_DEATH': 'portal', 'WITHER_SPAWN': 'roar', 'WARDEN_ROAR': 'roar', 'WITHER_AMBIENT': 'roar',
    'ELDER_GUARDIAN_CURSE': 'roar', 'SCULK_SHRIEKER_SHRIEK': 'roar', 'WARDEN_HEARTBEAT': 'heart', 'ELYTRA_FLYING': 'whoosh',
    'PHANTOM_FLAP': 'whoosh', 'ENDER_DRAGON_FLAP': 'whoosh', 'PLAYER_ATTACK_SWEEP': 'whoosh', 'FISHING_BOBBER_RETRIEVE': 'whoosh',
    'FIRECHARGE_USE': 'fire', 'BLAZE_SHOOT': 'fire', 'FIRE_AMBIENT': 'fire', 'BLAZE_AMBIENT': 'fire', 'ENDER_DRAGON_SHOOT': 'fire',
    'LAVA_POP': 'fire', 'WITHER_SHOOT': 'fire', 'FIRE_EXTINGUISH': 'hiss', 'SOUL_ESCAPE': 'soul', 'ALLAY_AMBIENT_WITHOUT_ITEM': 'soul',
    'ENCHANTMENT_TABLE_USE': 'magic', 'ILLUSIONER_MIRROR_MOVE': 'magic', 'ILLUSIONER_PREPARE_BLINDNESS': 'magic',
    'ILLUSIONER_PREPARE_MIRROR': 'magic', 'ILLUSIONER_CAST_SPELL': 'magic', 'EVOKER_FANGS_ATTACK': 'slam',
    'CHAIN_PLACE': 'chain', 'CHAIN_STEP': 'chain', 'ZOMBIE_ATTACK_IRON_DOOR': 'slam', 'ANVIL_LAND': 'slam',
    'ARMOR_EQUIP_NETHERITE': 'slam', 'PLAYER_ATTACK_STRONG': 'slam', 'PLAYER_ATTACK_CRIT': 'slam',
    'PLAYER_HURT_SWEET_BERRY_BUSH': 'wet', 'HONEY_DRINK': 'wet', 'PLAYER_HURT': 'wet',
    'POWDER_SNOW_PLACE': 'snow', 'POWDER_SNOW_BREAK': 'snow', 'POWDER_SNOW_STEP': 'snow',
    'ROOTED_DIRT_BREAK': 'earth', 'ROOTED_DIRT_PLACE': 'earth', 'DRIPSTONE_BLOCK_BREAK': 'earth', 'WARDEN_DIG': 'earth',
    'AZALEA_LEAVES_BREAK': 'leaves', 'AZALEA_LEAVES_PLACE': 'leaves', 'AZALEA_PLACE': 'leaves', 'MOSS_STEP': 'leaves',
    'CHERRY_LEAVES_BREAK': 'leaves', 'SPORE_BLOSSOM_BREAK': 'leaves', 'PUFFER_FISH_BLOW_OUT': 'leaves', 'SCULK_CATALYST_BLOOM': 'wet',
    'WOOD_PLACE': 'wood', 'WOOD_HIT': 'wood', 'WOOD_BREAK': 'wood', 'BEEHIVE_WORK': 'buzz',
    'BOOK_PAGE_TURN': 'paper', 'BOOK_PUT': 'paper', 'SAND_BREAK': 'paper', 'PLAYER_LEVELUP': 'fanfare', 'TOTEM_USE': 'fanfare',
    'UI_BUTTON_CLICK': 'click',
}

MAXLEN = {'boom': 2.6, 'thunder': 3.2, 'zap': 1.4, 'powerup': 2.4, 'powerdown': 2.0, 'hum': 3.0, 'chime': 1.6, 'resonate': 2.8,
          'bell': 3.0, 'shatter': 1.8, 'form': 1.2, 'portal': 2.6, 'roar': 3.2, 'heart': 1.4, 'whoosh': 1.4, 'fire': 1.6, 'hiss': 1.4,
          'soul': 2.0, 'magic': 2.0, 'chain': 1.4, 'slam': 1.6, 'wet': 1.3, 'snow': 1.6, 'earth': 1.8, 'leaves': 1.4, 'wood': 1.4,
          'buzz': 1.4, 'paper': 1.2, 'fanfare': 2.6, 'click': 0.5}


def gesture(kind, sc, rng, seed):
    S = SCHOOLS[sc]
    b = S['bias'] + rng.uniform(-1.5, 1.5)
    R = lambda d=None: semis(take(rng, S['ring'], d), b)          # noqa: E731  звон школы
    T = lambda d: semis(take(rng, S['tone'], d, from_start=False), b)  # noqa: E731  тон / фон школы
    H = lambda: semis(take(rng, S['hit']), b)                     # noqa: E731  удар школы
    X = lambda d: semis(take(rng, S['tex'], d, from_start=False), b)   # noqa: E731  фактура школы
    if kind == 'boom':
        core = sat(semis(take(rng, 'boom'), b - 3), 1.6)
        return mix((core, 0, 1.0), (sub_thump(46 + rng.uniform(-6, 6), 0.45, 0.5), 0, 0.8), (H(), 0.02, 0.55), (X(1.6), 0.08, 0.35))
    if kind == 'thunder':
        th = semis(take(rng, 'thunder', 3.0), b - 2)
        return mix((semis(take(rng, 'zap'), b + 2), 0, 0.6), (th, 0.03, 1.0), (R(), 0.05, 0.4))
    if kind == 'zap':
        z = take(rng, 'zap')
        return mix((semis(z, b + 1), 0, 1.0), (H(), 0.01, 0.6), (sub_thump(70, 0.15), 0, 0.4))
    if kind == 'powerup':
        tone = T(2.2)
        tone = tone * np.linspace(0.1, 1, len(tone)) ** 2
        tone = glide(tone, 0.8, 1.15)
        sw = rev_swell(R(), 1.6, 6000, seed)
        return mix((tone, 0, 0.7), (sw, max(0, 2.0 - len(sw) / SR), 0.8), (H(), 1.95, 0.5))
    if kind == 'powerdown':
        x = glide(mix((R(), 0, 0.8), (T(1.8), 0, 0.6)), 1.0, 0.55)
        return x * np.linspace(1, 0.2, len(x))
    if kind == 'hum':
        x = mix((T(2.8), 0, 1.0), (lp(take(rng, 'drone', 2.8, from_start=False), 1500), 0, 0.5))
        return env(x, 0.5, 0.8)
    if kind == 'chime':
        return mix((R(), 0, 1.0), (semis(take(rng, 'glass_tick'), b + 5), 0, 0.25))
    if kind == 'click':
        return cut(semis(take(rng, 'glass_tick'), b + 3), 0.35)
    if kind == 'resonate':
        r = R()
        return mix((r, 0, 1.0), (semis(r, 7), 0.12, 0.45), (env(T(2.4), 0.4, 0.8), 0, 0.5))
    if kind == 'bell':
        big = 'big_bell' if sc in ('holy', 'divine', 'higher', 'silent') else S['ring']
        return mix((semis(take(rng, big, 2.8), b), 0, 1.0), (R(), 0.02, 0.4))
    if kind == 'shatter':
        sh = 'ice' if sc == 'ice' else 'glass'
        return mix((semis(take(rng, sh), b + 1), 0, 1.0), (H(), 0, 0.45), (R(), 0.03, 0.35))
    if kind == 'form':
        g = semis(take(rng, 'glass_tick'), b)
        return mix((g[::-1][-int(0.25 * SR):], 0, 0.6), (g, 0.24, 1.0), (R(), 0.25, 0.4))
    if kind == 'portal':
        p = semis(take(rng, 'portal', 2.2), b - 2)
        return mix((rev_swell(p, 1.0, 4000, seed), 0, 0.5), (p, 0.35, 1.0), (T(2.0), 0.2, 0.4))
    if kind == 'roar':
        if sc in ('holy', 'divine', 'silent', 'illusion', 'ice', 'wind'):
            body = env(T(2.6), 0.6, 0.6)
            return mix((body, 0, 1.0), (semis(body, -12), 0, 0.7), (sub_thump(36, 0.9, 0.3), 0.6, 0.6))
        r = semis(take(rng, 'roar', 3.0), b - 5)
        return mix((r, 0, 1.0), (env(T(2.6), 0.4, 0.8), 0, 0.5), (sub_thump(38, 0.8, 0.3), 0.05, 0.6))
    if kind == 'heart':
        h = lp(semis(take(rng, 'heart', 1.3), b - 5), 900)
        return mix((h, 0, 1.0), (sub_thump(50, 0.25), 0.01, 0.5), (R(), 0.02, 0.18))
    if kind == 'whoosh':
        w = semis(take(rng, 'swish' if rng.random() < 0.6 else 'wind', 1.2), b)
        return mix((w, 0, 1.0), (X(1.0), 0.05, 0.35))
    if kind == 'fire':
        return mix((semis(take(rng, 'fire_burst'), b), 0, 1.0), (semis(take(rng, 'fire_tex', 1.2, from_start=False), b), 0, 0.4),
                   (R(), 0.02, 0.3 if sc != 'fire' else 0.0))
    if kind == 'hiss':
        s = hp(semis(take(rng, 'splash'), b + 4), 1800)
        f = lp(semis(take(rng, 'fire_tex', 1.2, from_start=False), b), 3000)
        return mix((s, 0, 0.8), (f * np.linspace(1, 0, len(f)), 0, 0.8))
    if kind == 'soul':
        s = semis(take(rng, 'soul', 1.6), b + 2)
        return mix((s, 0, 1.0), (hp(T(1.6), 800), 0.1, 0.4))
    if kind == 'magic':
        return mix((semis(take(rng, 'magic', 1.8), b), 0, 0.9), (R(), 0.05, 0.6), (X(1.5), 0.1, 0.3))
    if kind == 'chain':
        return mix((semis(take(rng, 'chain'), b - 2), 0, 1.0), (R(), 0.03, 0.35))
    if kind == 'slam':
        return mix((semis(take(rng, 'metal'), b - 3), 0, 1.0), (sub_thump(55, 0.3), 0, 0.6), (H(), 0.02, 0.4))
    if kind == 'wet':
        return mix((semis(take(rng, 'wet'), b - 1), 0, 1.0), (X(0.8), 0.03, 0.3))
    if kind == 'snow':
        s = hp(semis(take(rng, 'wind', 1.4, from_start=False), b + 2), 600)
        return mix((env(s, 0.15, 0.4), 0, 0.8), (semis(take(rng, 'ice'), b + 4), 0.05, 0.4))
    if kind == 'earth':
        return mix((semis(take(rng, 'earth'), b - 2), 0, 1.0), (semis(take(rng, 'wood'), b - 4), 0.04, 0.4),
                   (sub_thump(48, 0.35), 0, 0.5))
    if kind == 'leaves':
        return mix((semis(take(rng, 'leaves', 1.2), b), 0, 1.0), (X(1.0), 0.05, 0.3))
    if kind == 'wood':
        return mix((semis(take(rng, 'wood'), b - 1), 0, 1.0), (semis(take(rng, 'creak', 1.0, from_start=False), b - 3), 0.05, 0.4))
    if kind == 'buzz':
        return mix((semis(take(rng, 'zap', 1.2), b), 0, 0.8), (X(1.2), 0, 0.5))
    if kind == 'paper':
        return mix((semis(take(rng, 'paper', 1.0), b), 0, 1.0), (R(), 0.05, 0.25))
    if kind == 'fanfare':
        base = R()
        return mix((base, 0, 0.8), (semis(base, 4), 0.14, 0.7), (semis(base, 7), 0.28, 0.7), (semis(base, 12), 0.42, 0.6),
                   (semis(take(rng, 'heal', 2.0), b), 0.1, 0.4))
    raise KeyError(kind)


def make(event, kind, sc, var):
    seed = int(hashlib.md5(('%s/%d' % (event, var)).encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    x = gesture(kind, sc, rng, seed % 997)
    x = school_fx(x, sc, rng, seed % 991)
    if sc == 'forbidden' and kind in ('boom', 'portal', 'roar', 'powerup', 'shatter') and len(x) > SR:
        k = int(len(x) * rng.uniform(0.45, 0.6))                     # «разрыв»: обрыв в тишину и рваный хвост
        g = int(0.18 * SR)
        x = np.concatenate([x[:k], np.zeros(g), x[k:][::-1][:int(0.35 * SR)] * 0.6])
    x = trim(x, maxlen=MAXLEN[kind])
    return loudnorm(env(x, 0.004, 0.12))


# ================================================================== разбор кода
SKIP_FILES = {'nightmare/NightmareMob.java': 'Кошмары — уже свои звуки (nightmare.*)',
              'nightmare/EndlessNightSpell.java': 'Кошмары — уже свои звуки (nightmare.cast_night)',
              'client/nightmare/NightmareClient.java': 'Кошмары — уже свои звуки (nightmare.heartbeat)',
              'silent/SilentWitchArmor.java': 'не магия: звук надевания мантии'}
SKIP_LINES = {('Reg.java', 'WARDEN_HEARTBEAT'): 'школа Кошмаров — уже свои звуки (nightmare.heartbeat)'}
# файлы без своего PATH: id «заклинания» и школа
EXTRA = {
    'spell/Marks.java': {'boom': ('illusion_decoy', 'evocation'), 'tickOverload': ('overload', 'lightning')},
    'spell/BarrierGuard.java': ('barrier_guard', 'silent'),
    'spell/SoulSeal.java': ('soul_seal', 'divine'),
    'spell/JointCast.java': ('joint_cast', 'higher'),
    'DivineEvents.java': ('divine_backlash', 'divine'),
    'ember/EmberBlade.java': ('ember_blade', 'fire'),
    'client/EmberWhipClient.java': ('ember_blade', 'fire'),
    'illusion/Illusions.java': ('illusion_copies', 'illusion'),
    'illusion/IllusionAllies.java': ('illusion_copies', 'illusion'),
    'client/illusion/Copies.java': ('illusion_copies', 'illusion'),
    'client/illusion/ErasedClient.java': ('erased_name', 'forbidden'),
    'client/PohHud.java': ('magic_madness', 'blood'),
    'silent/SilentWitchEvents.java': ('silent_witch', 'silent'),
}
SCHOOL_OF = {
    'explosion': 'fire', 'heaven_fall': 'fire', 'falling_sun': 'fire', 'fire_whip': 'fire',
    'glacial_tombs': 'ice', 'frost_spike_wall': 'ice',
    'lightning_rod': 'lightning', 'ground_shock': 'lightning', 'overload': 'lightning',
    'judgement': 'holy', 'living_shield': 'holy', 'sanctuary': 'holy', 'last_dawn': 'holy',
    'blood_gift': 'blood', 'blood_mark': 'blood', 'hemorrhage': 'blood', 'magic_madness': 'blood',
    'banishment': 'ender', 'swap': 'ender', 'space_closure': 'ender', 'frozen_hour': 'ender', 'coven_arrival': 'ender',
    'grasping_garden': 'nature', 'spore_cloud': 'nature', 'world_tree': 'nature',
    'eight_shields': 'evocation', 'phantom_trap': 'evocation', 'illusion': 'evocation',
    'abyss_eye': 'eldritch', 'gale_ward': 'wind', 'wind_mark': 'wind',
    'ark': 'divine', 'divine_taboo': 'divine', 'soul_devour': 'divine', 'blessing': 'divine', 'soul_seal': 'divine', 'disintegration': 'divine',
    'downfall': 'forbidden', 'erased_name': 'forbidden',
    'silent_staff': 'silent', 'wind_spears': 'silent', 'worgan_flame': 'silent', 'sage_barrier': 'silent',
}
HIGHER = ['ashless_flame', 'forbidding_seal', 'blood_moon', 'nightmare_cradle', 'world_rift', 'countdown', 'singularity', 'mirror_prison',
          'milky_way', 'wind_ascension', 'oblivion_blades', 'scarlet_cut', 'fate_star', 'star_fall', 'eternal_blizzard']
ILLUSION = ['borrowed_face', 'butterfly_dream', 'false_step', 'mirror_images', 'mirror_labyrinth', 'phantom_pain', 'veil', 'waking_nightmare']
for _s in HIGHER:
    SCHOOL_OF[_s] = 'higher'
for _s in ILLUSION:
    SCHOOL_OF[_s] = 'illusion'
SCHOOL_ORDER = ['fire', 'ice', 'lightning', 'holy', 'blood', 'ender', 'nature', 'eldritch', 'evocation', 'wind',
                'higher', 'divine', 'forbidden', 'silent', 'illusion']
SCHOOL_CAST = {'DIVINE': 'divine', 'HIGHER': 'higher', 'FORBIDDEN': 'forbidden', 'SILENT': 'silent', 'ILLUSION': 'illusion'}

ROLES = {   # роль: (ru, en)
    'cast': ('начало каста', 'cast'), 'charge': ('нарастание во время каста', 'charging'), 'release': ('выпуск заклинания', 'release'),
    'open': ('раскрытие (печать, купол, разрыв)', 'opening'), 'loop': ('пока действует (тики)', 'active'),
    'hit': ('удар / взрыв / попадание', 'impact'), 'end': ('конец / снятие / смерть', 'end'), 'fail': ('отказ / ошибка', 'denied'),
}
M_CAST = {'onCast', 'cast', 'start', 'begin', 'startHold', 'build', 'sleep', 'toggle', 'merge', 'rise', 'breathe', 'needsStaffOk'}
M_CHARGE = {'castTick', 'onServerCastTick', 'tickHold', 'tickFx', 'step', 'ritual'}
M_RELEASE = {'onServerCastComplete', 'launch', 'fall', 'erupt'}
M_OPEN = {'open', 'openRift', 'openPortal', 'openCasterPortal', 'seal'}
M_LOOP = {'tick', 'onTick', 'madTick', 'onServerTick', 'aura', 'onPlayerTick', 'inventoryTick', 'onClientTick', 'chase'}
M_END = {'end', 'close', 'release', 'stop', 'exit', 'wakeFx', 'dreamDeath', 'onDeath', 'guard'}
M_FAIL = {'deny', 'checkPreCastConditions', 'needsStaff', 'onUseItem'}

METH_RE = re.compile(r'^\s*(?:@\w+\s+)*(?:(?:public|private|protected|static|final|synchronized|abstract)\s+)*[\w<>\[\],.? ]+\s+(\w+)\s*\([^;]*$')
NONMETH = {'if', 'for', 'while', 'switch', 'catch', 'return', 'new', 'else', 'case'}


def role_of(meth, line, kind):
    if 'getCastStartSound' in line:
        return 'cast'
    if 'getCastFinishSound' in line:
        return 'release'
    if meth in M_CAST:
        return 'cast'
    if meth in M_CHARGE:
        return 'charge'
    if meth in M_RELEASE:
        return 'release'
    if meth in M_OPEN:
        return 'open'
    if meth in M_END:
        return 'end'
    if meth in M_FAIL:
        return 'fail'
    if meth in M_LOOP:
        if kind in ('boom', 'shatter', 'thunder', 'zap', 'slam', 'portal', 'earth', 'wet'):
            return 'hit'
        if kind == 'powerdown':
            return 'end'
        return 'loop'
    return 'hit'


def spell_meta():
    """PATH и ступень по файлам; ru/en имена по lang."""
    ru = json.load(open(os.path.join(A, 'lang', 'ru_ru.json'), encoding='utf-8'))
    en = json.load(open(os.path.join(A, 'lang', 'en_us.json'), encoding='utf-8'))
    names = {}
    for k, v in ru.items():
        if k.startswith('spell.pohsmp_core.') and k.count('.') == 2:
            names[k[18:]] = (v, en.get(k, v))
    names.update({'illusion_decoy': ('Иллюзия: приманка', 'Illusion: decoy'), 'barrier_guard': ('Барьер (страж оболочки)', 'Barrier guard'),
                  'joint_cast': ('Совместный каст', 'Joint cast'), 'divine_backlash': ('Божественная отдача', 'Divine backlash'),
                  'ember_blade': ('Раскалённые угли (клинок/плеть)', 'Ember blade'), 'illusion_copies': ('Иллюзорные копии', 'Illusory copies'),
                  'silent_witch': ('Безмолвная ведьма', 'Silent Witch'), 'silent_staff': ('Посох Безмолвной', 'Silent staff')})
    for sc, r in SCHOOL_CAST.items():
        names['school_' + r] = ('Школа: ' + SCHOOLS[r]['ru'], 'School: ' + r)
    return names


def scan():
    sites, skipped = [], []
    for dp, dn, fn in os.walk(JAVA):
        for f in sorted(fn):
            if not f.endswith('.java'):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, JAVA).replace(os.sep, '/')
            src = open(p, encoding='utf-8').read()
            L = src.split('\n')
            mpath = re.search(r'\b(?:PATH|ID)\s*=\s*(?:new ResourceLocation\(PohCore.MODID,\s*)?"(\w+)"', src)
            tier = re.search(r'SpellRarity\.(\w+)|Rank\.(\w+)', src)
            tier = (tier.group(1) or tier.group(2)) if tier else ''
            if 'extends MythicT23' in src:
                tier = 'MYTHIC'
            if 'extends HigherSpell' in src:
                tier = 'HIGHER'
            meth = '?'
            for i, l in enumerate(L):
                m = METH_RE.match(l)
                if m and m.group(1) not in NONMETH:
                    meth = m.group(1)
                for s in re.findall(r'SoundEvents\.([A-Z_0-9]+)', l):
                    site = dict(file=rel, line=i + 1, method=meth, vanilla=s, code=l.strip())
                    if 'getCastStartSound' in l:
                        site['method'] = 'getCastStartSound'
                    elif 'getCastFinishSound' in l:
                        site['method'] = 'getCastFinishSound'
                    why = SKIP_FILES.get(rel) or SKIP_LINES.get((rel, s))
                    if why:
                        skipped.append(dict(site, why=why))
                        continue
                    if rel == 'Reg.java':
                        sc = next((v for k, v in SCHOOL_CAST.items() if k + '_POWER' in l), None)
                        site.update(spell='school_' + sc, school=sc, tier='школа', role='cast')
                    else:
                        ex = EXTRA.get(rel)
                        if isinstance(ex, dict):
                            ex = ex.get(site['method'])
                        if ex:
                            sid, sc = ex
                        elif rel.endswith('SilentStaffSpell.java'):
                            sid, sc = 'silent_staff', 'silent'
                        elif mpath:
                            sid = mpath.group(1)
                            sc = SCHOOL_OF.get(sid)
                        else:
                            sid, sc = None, None
                        if not sc:
                            raise SystemExit('нет школы: %s:%d %s' % (rel, i + 1, sid))
                        site.update(spell=sid, school=sc, tier=tier)
                    sites.append(site)
    for s in sites:
        s['kind'] = VANILLA_KIND[s['vanilla']]
        if 'role' not in s:
            s['role'] = role_of(s['method'], s['code'], s['kind'])
    # события: (заклинание, роль, смысл); имя — роль, а при нескольких смыслах в одной роли — роль_смысл
    groups = {}
    for s in sites:
        groups.setdefault((s['spell'], s['role']), set()).add(s['kind'])
    for s in sites:
        pre = 'school.%s' % s['school'] if s['spell'].startswith('school_') else 'spell.%s' % s['spell']
        many = len(groups[(s['spell'], s['role'])]) > 1
        s['event'] = '%s.%s' % (pre, s['role'] + ('_' + s['kind'] if many else ''))
    return sites, skipped


# ================================================================== запись
def enc(x, path, fmt='ogg'):
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2').tobytes()
    args = ['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', '-']
    args += ['-c:a', 'libvorbis', '-q:a', '3'] if fmt == 'ogg' else ['-c:a', 'libmp3lame', '-b:a', '64k']
    subprocess.run(args + [path], input=pcm, check=True)


def events_of(sites):
    ev = {}
    for s in sites:
        e = ev.setdefault(s['event'], dict(event=s['event'], spell=s['spell'], school=s['school'], role=s['role'], kind=s['kind'],
                                           tier=s['tier'], sites=[]))
        e['sites'].append(s)
    return ev


def nvar(e):
    return 3 if e['role'] in ('hit', 'loop') and e['kind'] not in ('hum', 'powerup', 'powerdown', 'roar', 'resonate') else 2


def write_sounds(evs, schools, names):
    sj_path = os.path.join(A, 'sounds.json')
    sj = json.load(open(sj_path, encoding='utf-8'))
    langs = {c: json.load(open(os.path.join(A, 'lang', c + '.json'), encoding='utf-8')) for c in ('ru_ru', 'en_us')}
    mp3d = os.path.join(DOCS, 'mp3')
    os.makedirs(mp3d, exist_ok=True)
    rev_path = os.path.join(DOCS, 'review.json')
    review = json.load(open(rev_path, encoding='utf-8')) if os.path.exists(rev_path) else []
    review = [r for r in review if r['school'] not in schools]
    n = 0
    for name, e in sorted(evs.items()):
        if e['school'] not in schools:
            continue
        sc = e['school']
        d = os.path.join(OUT, sc)
        os.makedirs(d, exist_ok=True)
        files, mp3s = [], []
        base = name.split('.', 1)[1].replace('.', '_')
        for v in range(nvar(e)):
            x = make(name, e['kind'], sc, v)
            fn = '%s_%d' % (base, v + 1)
            enc(x, os.path.join(d, fn + '.ogg'))
            enc(x, os.path.join(mp3d, fn + '.mp3'), 'mp3')
            files.append(fn)
            mp3s.append('docs/sounds/mp3/%s.mp3' % fn)
            n += 1
        sj[name] = {'subtitle': 'subtitles.pohsmp_core.' + name,
                    'sounds': [{'name': 'pohsmp_core:spell/%s/%s' % (sc, f), 'volume': VOLUME} for f in files]}
        sp_ru, sp_en = names.get(e['spell'], (e['spell'], e['spell']))
        langs['ru_ru']['subtitles.pohsmp_core.' + name] = '%s: %s' % (sp_ru, KINDS[e['kind']][1])
        langs['en_us']['subtitles.pohsmp_core.' + name] = '%s: %s' % (sp_en, KINDS[e['kind']][2])
        where = '; '.join(sorted({'%s %s()' % (s['file'].split('/')[-1], s['method']) for s in e['sites']}))
        review.append(dict(school=sc, school_ru=SCHOOLS[sc]['ru'], spell=e['spell'], spell_ru=sp_ru, event='pohsmp_core:' + name,
                           role=e['role'], role_ru=ROLES[e['role']][0], files=['spell/%s/%s.ogg' % (sc, f) for f in files], mp3=mp3s,
                           what='%s — %s (подпись школы: %s)' % (KINDS[e['kind']][0], ROLES[e['role']][0], SCHOOLS[sc]['sig']),
                           where=where, replaces=sorted({s['vanilla'] for s in e['sites']})))
    with open(sj_path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(sj, fh, ensure_ascii=False, indent=2)
        fh.write('\n')
    for c, dct in langs.items():
        with open(os.path.join(A, 'lang', c + '.json'), 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(dct, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
    review.sort(key=lambda r: (SCHOOL_ORDER.index(r['school']), r['spell'], r['event']))
    with open(rev_path, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(review, fh, ensure_ascii=False, indent=1)
        fh.write('\n')
    return n


def write_docs(sites, skipped, names):
    os.makedirs(DOCS, exist_ok=True)
    evs = events_of(sites)
    by = {}
    for s in sites:
        by.setdefault(s['school'], {}).setdefault(s['spell'], []).append(s)
    with open(os.path.join(DOCS, 'catalog.md'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('# Каталог звуков магии (по коду, 19.11.2026)\n\n'
                 'Все места, где заклинания играют ванильные `SoundEvents.*`: заклинание → школа/ступень → место (файл:строка, метод) → '
                 'роль → текущий ванильный звук → наше событие. Собирается `tools/gen_spell_sounds.py --docs-only`.\n\n'
                 'Мест: **%d**, заклинаний: **%d**, наших событий: **%d**. Пропущено (уже свои / не магия): %d.\n\n'
                 'Роли: %s.\n\n' % (len(sites), len({s['spell'] for s in sites}), len(evs), len(skipped),
                                    '; '.join('`%s` — %s' % (k, v[0]) for k, v in ROLES.items())))
        for sc in SCHOOL_ORDER:
            if sc not in by:
                continue
            fh.write('## %s (`%s`) — %s\n\n' % (SCHOOLS[sc]['ru'], sc, SCHOOLS[sc]['sig']))
            for sid, ss in sorted(by[sc].items()):
                fh.write('### %s (`%s`) — ступень: %s\n\n| место | метод | роль | ванильный звук | наше событие |\n|---|---|---|---|---|\n'
                         % (names.get(sid, (sid,))[0], sid, ss[0]['tier'] or '—'))
                for s in sorted(ss, key=lambda s: (s['file'], s['line'])):
                    fh.write('| `%s:%d` | `%s` | %s | `%s` | `pohsmp_core:%s` |\n'
                             % (s['file'], s['line'], s['method'], ROLES[s['role']][0], s['vanilla'], s['event']))
                fh.write('\n')
        fh.write('## Пропущено\n\n| место | ванильный звук | почему |\n|---|---|---|\n')
        for s in skipped:
            fh.write('| `%s:%d` | `%s` | %s |\n' % (s['file'], s['line'], s['vanilla'], s['why']))
        fh.write('\nТакже уже свои и не трогаются: музыка Врат (`music.silent_gate*`), Ковена (`music.coven_arrival`), '
                 'Сна бабочки (`music.butterfly_dream`), все `nightmare.*`.\n')
    with open(os.path.join(DOCS, 'replacements.md'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('# Замены «ванильный SoundEvents → наше событие» (для чата Кодинга)\n\n'
                 'Одно наше событие заменяет **все** ванильные звуки строки/места с той же ролью: если в методе играют 2–3 ванильных '
                 'звука слоем (например `GENERIC_EXPLODE` + `WARDEN_SONIC_BOOM`), они заменяются ОДНИМ `playSound` с нашим событием '
                 '(лишние вызовы удалить). Громкость/высоту в коде можно оставить как есть, но pitch ставить 1.0 (±0.1 для разнообразия): '
                 'высота уже «зашита» в звук. Громкость 0.5 — в `sounds.json`.\n\n'
                 '| файл | метод | строка | было | стало |\n|---|---|---|---|---|\n')
        for s in sorted(sites, key=lambda s: (s['file'], s['line'])):
            fh.write('| `%s` | `%s` | %d | `SoundEvents.%s` | `pohsmp_core:%s` |\n' % (s['file'], s['method'], s['line'], s['vanilla'], s['event']))
    with open(os.path.join(DOCS, 'sources.md'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('# Источники звуков магии\n\nВсе записи — с OpenGameArt.org; обработаны в `tools/gen_spell_sounds.py` (высота/скорость, реверс, '
                 'реверберация, фильтры, кольцевая модуляция, «распад», слои). Владелец 19.11: «на лицензии не проверять, мод в интернет '
                 'не уйдёт» — источники записаны для себя (найти/заменить), лицензия — справочно.\n\n'
                 '| файл | автор | лицензия | страница |\n|---|---|---|---|\n')
        for f, (page, au, lic) in SOURCES.items():
            fh.write('| `%s` | %s | %s | https://opengameart.org/content/%s |\n' % (f.replace('%20', ' '), au, lic, page))
        fh.write('\nСинтез: только инфранизкий «удар» под взрывами/тяжёлыми ударами.\n')
    return evs


def main():
    args = sys.argv[1:]
    sites, skipped = scan()
    names = spell_meta()
    evs = write_docs(sites, skipped, names)
    print('мест %d, событий %d, пропущено %d' % (len(sites), len(evs), len(skipped)))
    if '--docs-only' in args:
        return
    schools = SCHOOL_ORDER
    if '--school' in args:
        schools = args[args.index('--school') + 1].split(',')
    fetch()
    n = write_sounds(evs, set(schools), names)
    print('школы %s: файлов %d' % (','.join(schools), n))


if __name__ == '__main__':
    main()
