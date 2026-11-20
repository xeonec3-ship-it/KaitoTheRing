#!/usr/bin/env python3
"""
Видео-превью анимаций боссов T29 «Мартин» и T30 «Эреб» (T26–T28 — tools/boss_video.py) → docs/media/video/t29_*.mp4, t30_*.mp4 (+ GIF-turntable 480 px).
Покадровый рендер теми же превью, что и кадры docs/media (шаблоны tools/martin_preview.template.html и tools/ereb_preview.template.html,
модели/анимации/текстуры из assets как есть), драйвер — tools/boss_video_b_driver.js; Playwright + Chromium, сборка — ffmpeg (H.264, 1280×720, 30 fps).
Эффекты в роликах — условные (мэши fx/meshes и рисунки textures/sigil|fx, движение по таблицам писем), как на проверочных кадрах; в игре их рисует движок fx.

  python3 tools/boss_video_b.py [--three путь/three.min.js] [t29_turntable t30_finale ...]   (без имён — все ролики)
Перед запуском: python3 tools/fetch_libs.py (jar Iron's — анимации каста и каркас); three r128: npm i three@0.128.0 или скачать three.min.js.
"""
import base64
import json
import math
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import martin_render as MR  # noqa: E402
import gen_ereb_render as ER  # noqa: E402
import cult_leader_render as CR  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..'))
A = MR.A
OUT = os.path.join(ROOT, 'docs', 'media', 'video')
TMP = os.environ.get('BOSS_VIDEO_TMP', '/tmp/boss_video')
FPS, W, H = 30, 1280, 720
GOLD, GHOST, RED, WHITE = '#e8b95a', '#8fd8f0', '#c22a2c', '#ffffff'
GLASS, GLASS_HI, GOLD_HI = '#9fd8ff', '#d8f2ff', '#ffe08a'


# ================================================================== общее
def b64file(p):
    with open(p, 'rb') as fh:
        return 'data:image/png;base64,' + base64.b64encode(fh.read()).decode()


def vtex(names):
    out = {}
    for n in names:
        if n.startswith('title:'):
            out[n] = b64file(os.path.join(A, 'textures', 'gui', 'title', n[6:] + '.png'))
            continue
        for sub in ('sigil', 'fx'):
            p = os.path.join(A, 'textures', sub, n + '.png')
            if os.path.exists(p):
                out[n] = b64file(p)
                break
        else:
            raise FileNotFoundError(n)
    return out


def ease(k):
    k = max(0.0, min(1.0, k))
    return -(math.cos(math.pi * k) - 1) / 2


def lin(t, a, b):
    """0 до a, 1 после b, линейно между."""
    return max(0.0, min(1.0, (t - a) / (b - a))) if b > a else (1.0 if t >= b else 0.0)


def pulse(t, a, rise, hold, fall):
    """огибающая: 0 → 1 за rise с момента a, держит hold, спад за fall."""
    if t < a:
        return 0.0
    if t < a + rise:
        return ease((t - a) / rise)
    if t < a + rise + hold:
        return 1.0
    return 1.0 - ease((t - a - rise - hold) / fall) if fall > 0 else 0.0


def orbit(yaw, pitch, dist, look, fov=30):
    y, p = math.radians(yaw), math.radians(pitch)
    pos = [look[0] + math.sin(y) * math.cos(p) * dist, look[1] + math.sin(p) * dist, look[2] - math.cos(y) * math.cos(p) * dist]
    return {'pos': pos, 'look': list(look), 'fov': fov}


def camkeys(keys, t):
    """keys: [(t, yaw, pitch, dist, (lx, ly, lz))] — плавно (easeInOutSine) между ключами."""
    if t <= keys[0][0]:
        k = keys[0]
        return orbit(k[1], k[2], k[3], k[4])
    for a, b in zip(keys, keys[1:]):
        if t <= b[0]:
            u = ease((t - a[0]) / (b[0] - a[0]))
            m = lambda i: a[i] + (b[i] - a[i]) * u
            look = [a[4][j] + (b[4][j] - a[4][j]) * u for j in range(3)]
            return orbit(m(1), m(2), m(3), look)
    k = keys[-1]
    return orbit(k[1], k[2], k[3], k[4])


def rnd(seed):
    x = [seed * 9301 + 49297]

    def r():
        x[0] = (x[0] * 9301 + 49297) % 233280
        return x[0] / 233280
    return r


def glow(at, size, color=WHITE, op=1.0, tex='glow'):
    return {'tex': tex, 'at': list(at), 'size': size, 'color': color, 'op': op}


def decal(tex, at, r, color, op, rot=0):
    return {'tex': tex, 'at': [at[0], at[1] if len(at) > 2 else 0.03, at[-1]], 'size': 2 * r, 'color': color, 'op': op, 'ground': True, 'rot': rot}


def burst(tex, center, t, n, speed, size, color, seed, life=0.8, grav=0.0, up=0.0, spread=(1, 1, 1), op=1.0, spin=200, flap=False):
    """частицы вылетают из center в момент 0 (t — время от вспышки), гаснут за life."""
    if t < 0 or t > life:
        return []
    R = rnd(seed)
    out = []
    for i in range(n):
        d = [(R() * 2 - 1) * spread[0], (R() * 2 - 1) * spread[1] + up, (R() * 2 - 1) * spread[2]]
        ln = math.sqrt(sum(v * v for v in d)) or 1
        sp = speed * (0.5 + R())
        sz = size[0] + (size[1] - size[0]) * R()
        rot0, rs = R() * 360, (R() * 2 - 1) * spin
        ph = R() * 6.28
        p = [center[j] + d[j] / ln * sp * t for j in range(3)]
        p[1] -= grav * t * t / 2
        k = 1 - t / life
        s = {'tex': tex, 'at': p, 'size': sz, 'color': color, 'op': op * k, 'rot': rot0 + rs * t}
        if flap:
            s['w'] = sz * (0.35 + 0.65 * abs(math.cos(t * 16 + ph)))
            s['h'] = sz
            s['rot'] = 0
        out.append(s)
    return out


def butterflies(center, t, n, radius, height, seed, color=GLASS, size=(0.22, 0.38), op=0.9, speed=1.6, gold=True):
    """рой бабочек кружит вокруг center (radius/height — числа или функции от t)."""
    R = rnd(seed)
    out = []
    for i in range(n):
        ph, r0, h0, sz, w = R() * 6.28, 0.5 + R() * 0.5, R(), size[0] + (size[1] - size[0]) * R(), speed * (0.7 + R() * 0.6)
        g = gold and i % 3 == 0
        rr = radius * r0
        a = ph + w * t
        p = [center[0] + math.cos(a) * rr, center[1] + (h0 - 0.5) * height + 0.15 * math.sin(t * 3 + ph), center[2] + math.sin(a) * rr]
        out.append({'tex': 'mote_butterfly', 'at': p, 'h': sz, 'w': sz * (0.35 + 0.65 * abs(math.cos(t * 15 + ph))),
                    'color': GOLD_HI if g else color, 'op': op})
    return out


class Clip:
    def __init__(self, name, tag):
        self.name, self.tag, self.frames = name, tag, []

    def seg(self, dur, fn):
        n = int(round(dur * FPS))
        for i in range(n):
            f = fn(i / FPS)
            f.setdefault('tag', self.tag)
            self.frames.append(f)
        return self

    @property
    def dur(self):
        return len(self.frames) / FPS


def anim_len(kind, name):
    return ANIMS[kind][name]['animation_length']


ANIMS = {}


def load_anims():
    for k, f in (('martin', 'martin'), ('martin_soldier', 'martin_soldier'), ('martin_banner', 'martin_banner'), ('ereb', 'ereb')):
        ANIMS[k] = json.load(open(os.path.join(A, 'animations', 'entity', f + '.animation.json'), encoding='utf-8'))['animations']


def seq_anims(items, pause=0.3):
    """items: [(anim, длительность или None=длина анимации, подпись, под-подпись, extra(lt)->dict)] → список отрезков
    [(start, end, anim, ...)] и общая длина. Между анимациями — пауза pause с плавным переходом позы."""
    out, t = [], 0.0
    for it in items:
        anim, dur = it[0], it[1]
        out.append(dict(a=anim, t0=t, t1=t + dur, cap=it[2], sub=it[3], fx=it[4] if len(it) > 4 else None, model=it[5] if len(it) > 5 else None))
        t += dur + pause
    return out, t - pause


def seq_pose(segs, t, pause, loops):
    """поза (anim, время, mix) в момент t по списку отрезков; loops — множество зацикленных анимаций."""
    for i, s in enumerate(segs):
        if t < s['t1']:
            lt = t - s['t0']
            return s, (s['a'], lt % loops[s['a']] if s['a'] in loops else lt, None)
        if i + 1 < len(segs) and t < segs[i + 1]['t0']:
            nxt = segs[i + 1]
            L = s['t1'] - s['t0']
            ta = L % loops[s['a']] if s['a'] in loops else L
            k = ease((t - s['t1']) / pause)
            return nxt, (s['a'], ta, {'anim': nxt['a'], 't': 0, 'k': k})
    s = segs[-1]
    L = s['t1'] - s['t0']
    return s, (s['a'], L % loops[s['a']] if s['a'] in loops else L, None)


# ================================================================== рендер
def build_page(kind, three, texs, preload):
    if kind == 'martin':
        d = MR.data(['martin', 'martin_soldier', 'martin_banner'])
        st = CR.model_entry('steve')
        st.update(anims={}, scale=1, bg=0x231a1c)
        d['steve'] = st
        meshes = ['martin_cavalry_rider', 'martin_shield_wall', 'martin_shield_line', 'martin_archer_ghost', 'martin_arrow', 'martin_soldier_ghost']
        html = MR.page(d, None, three, meshes, [])
    else:
        html = ER.page(['ereb', 'pyromancer'], None, three)
    i = html.index('if (CELLS) {')
    j = html.rindex('</script>')
    drv = open(os.path.join(HERE, 'boss_video_b_driver.js'), encoding='utf-8').read()
    drv = drv.replace('/*VTEX*/null', json.dumps(vtex(texs))).replace('/*PRELOAD*/null', json.dumps(preload))
    return html[:i] + drv + html[j:]


RUNNER = r"""
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [html, framesFile, outDir] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'] });
  const pg = await b.newPage({ viewport: { width: %d, height: %d }, deviceScaleFactor: 1 });
  pg.on('pageerror', e => console.log('pageerror:', e.message));
  pg.on('console', m => { if (m.type() === 'error') console.log('console:', m.text()); });
  await pg.goto('file://' + html);
  await pg.waitForFunction('window.READY === true', null, { timeout: 240000 });
  const frames = JSON.parse(fs.readFileSync(framesFile, 'utf8'));
  for (let i = 0; i < frames.length; i++) {
    await pg.evaluate(f => window.frame(f), frames[i]);
    await pg.screenshot({ path: outDir + '/' + String(i).padStart(5, '0') + '.png' });
    if (i %% 150 === 0) console.log('frame', i, '/', frames.length);
  }
  await b.close();
})();
""" % (W, H)


def render(clip, kind, three, texs, preload):
    d = os.path.join(TMP, clip.name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    html = os.path.join(TMP, clip.name + '.html')
    with open(html, 'w', encoding='utf-8') as fh:
        fh.write(build_page(kind, three, texs, preload))
    fr = os.path.join(TMP, clip.name + '.json')
    with open(fr, 'w', encoding='utf-8') as fh:
        json.dump(clip.frames, fh, ensure_ascii=False, separators=(',', ':'))
    js = os.path.join(TMP, 'runner.js')
    with open(js, 'w') as fh:
        fh.write(RUNNER)
    print('render', clip.name, len(clip.frames), 'кадров', '%.1f с' % clip.dur, flush=True)
    r = subprocess.run(['node', js, html, fr, d], capture_output=True, text=True)
    print(r.stdout[-2000:], r.stderr[-2000:])
    os.makedirs(OUT, exist_ok=True)
    mp4 = os.path.join(OUT, clip.name + '.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(d, '%05d.png'), '-c:v', 'libx264',
                    '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', mp4], check=True)
    print('wrote', os.path.relpath(mp4, ROOT), '%.1f МБ' % (os.path.getsize(mp4) / 1e6))
    if clip.name.endswith('_turntable'):
        gif = os.path.join(OUT, clip.name + '.gif')
        pal = os.path.join(TMP, clip.name + '_pal.png')
        vf = 'fps=15,scale=480:-1:flags=lanczos'
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', mp4, '-vf', vf + ',palettegen=stats_mode=diff', pal], check=True)
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', mp4, '-i', pal, '-lavfi', vf + '[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=4',
                        '-loop', '0', gif], check=True)
        print('wrote', os.path.relpath(gif, ROOT), '%.1f МБ' % (os.path.getsize(gif) / 1e6))
    return mp4


# ================================================================== Т29 Мартин
M_TAG = 'T29 · Мартин, Последний Полководец'
M0 = [0, 0, 0]
M_LOOPS = {'martin_idle': 3.0, 'martin_walk': 1.6, 'martin_hold_loop': 2.0, 'martin_npc_idle': 4.0}


def m_obj(anim, t, mix=None, **kw):
    o = dict(model='martin', anim=anim, t=t, pos=kw.pop('pos', M0), ry=kw.pop('ry', 0))
    if mix:
        o['mix'] = mix
    o.update(kw)
    return o


def martin_turntable():
    c = Clip('t29_turntable', M_TAG)
    D = 7.0

    def f(t):
        return {'objs': [m_obj('martin_idle', t % 3.0, ry=-360 * t / D)], 'cam': orbit(0, 8, 14.5, (0, 2.0, 0)),
                'cap': 'Мартин — покой', 'sub': 'martin_idle · масштаб ×2, как в игре (рост ≈ 4.1 бл., рога ≈ 4.9 бл.)', 'groundSize': 200}
    return c.seg(D, f)


def martin_combat():
    c = Clip('t29_combat', M_TAG)
    P = 0.3

    def slam(lt):          # удар клинком в землю ≈ 4.5 бл. впереди
        t = lt - 0.95
        at = [0.0, 0.1, -4.4]
        s = burst('mote_ash', at, t, 18, 2.2, (0.25, 0.5), '#b8a890', 11, life=0.9, grav=3, up=1.2, spread=(1, 0.3, 1), op=0.8)
        s += burst('glow', [0, 0.4, -4.4], t, 6, 3.0, (0.12, 0.25), GOLD_HI, 12, life=0.5, grav=6, up=1.5)
        if 0 <= t < 0.6:
            s.append(decal('wave_ring', at, 0.6 + 3.5 * t, GOLD, 0.8 * (1 - t / 0.6)))
            s.append(glow([0, 0.6, -4.4], 2.2 * (1 - t / 0.6) + 0.4, GOLD_HI, 0.7 * (1 - t / 0.6)))
        return {'sprites': s}

    def trail(t_sw):
        def fx(lt):
            t = lt - t_sw
            if not (0 <= t < 0.3):
                return {}
            k = 1 - t / 0.3
            return {'sprites': [{'tex': 'glow', 'at': [math.sin(a) * 3.4, 2.4, -math.cos(a) * 3.4], 'size': 0.9 * k, 'color': GOLD_HI, 'op': 0.6 * k}
                                for a in [math.radians(x) for x in range(-70, 71, 12)]]}
        return fx

    def dash(lt):
        t = lt - 0.45
        if not (0 <= t < 0.6):
            return {}
        k = 1 - t / 0.6
        return {'sprites': [{'tex': 'mote_ash', 'at': [(i % 3 - 1) * 0.6, 0.3 + (i % 4) * 0.5, 1.0 + i * 0.35], 'size': 0.5, 'color': '#c8bca8', 'op': 0.5 * k}
                            for i in range(10)] + [glow([0, 2.2, -1.6], 1.6 * k, GOLD_HI, 0.5 * k)] * (1 if 0.25 < t < 0.45 else 0)}

    def command(lt):
        t = lt - 0.85
        s = burst('glow', [0.5, 5.2, -2.0], t, 12, 1.8, (0.12, 0.28), GOLD_HI, 21, life=0.8, grav=1.0)
        if 0 <= t < 0.7:
            s.append(glow([0.5, 5.2, -2.0], 1.8 * (1 - t / 0.7) + 0.3, GOLD_HI, 0.8 * (1 - t / 0.7)))
            s.append(decal('martin_emblem', M0, 2 + 3 * t, GOLD, 0.6 * (1 - t / 0.7)))
        return {'sprites': s}

    BAN = [-3.0, 0, -1.6]

    def banner(lt):
        ob = []
        if lt >= 1.3:
            bt = lt - 1.3
            ob.append(dict(model='martin_banner', anim='martin_banner_plant' if bt < 1.2 else 'martin_banner_idle',
                           t=bt if bt < 1.2 else (bt - 1.2) % 2.0, pos=BAN, ry=-10))
        s = []
        if lt >= 1.3:
            t = lt - 1.3
            s += burst('mote_ash', [BAN[0], 0.1, BAN[2]], t, 14, 1.8, (0.25, 0.45), '#b8a890', 31, life=0.8, grav=3, up=1, spread=(1, 0.2, 1), op=0.7)
            s.append(decal('martin_banner_ring', BAN, min(8, 1 + 14 * t), GOLD, 0.35 * min(1, t / 0.3)))
        return {'objs_extra': ob, 'sprites': s}

    def phase2(lt):
        s = []
        t = lt - 0.6
        s += burst('mote_ash', [0, 0.1, -1.8], t, 16, 2.0, (0.25, 0.45), '#b8a890', 41, life=0.9, grav=3, up=1, spread=(1, 0.2, 1), op=0.7)
        t2 = lt - 1.4
        if 0 <= t2 < 1.2:
            k = t2 / 1.2
            s.append(decal('wave_ring', M0, 1 + 11 * k, RED, 0.8 * (1 - k)))
            s.append(glow([0, 3.6, -0.4], 3 * (1 - k) + 0.5, '#ff6040', 0.5 * (1 - k)))
        return {'sprites': s, 'tintx': ('#5a0000', 0.18 * pulse(lt, 1.4, 0.15, 0.2, 0.6))}

    def phase3(lt):
        s = []
        t2 = lt - 2.0
        if 0 <= t2 < 1.2:
            k = t2 / 1.2
            s.append(decal('wave_ring', M0, 1 + 11 * k, GOLD, 0.8 * (1 - k)))
            s.append(glow([0, 5.5, -0.2], 3.5 * (1 - k) + 0.6, GOLD_HI, 0.6 * (1 - k)))
        s += burst('glow', [0, 5.2, 0], t2, 16, 2.4, (0.12, 0.28), GOLD_HI, 51, life=1.0, grav=1.5)
        t1 = lt - 1.4
        if 0 <= t1 < 0.5:
            s.append(decal('wave_ring', M0, 1 + 6 * t1, GOLD_HI, 0.6 * (1 - t1 / 0.5)))
        return {'sprites': s, 'tintx': ('#3a2400', 0.15 * pulse(lt, 2.0, 0.15, 0.2, 0.6))}

    items = [('martin_walk', 3.2, 'Тяжёлый шаг', 'martin_walk · меч на плече'),
             ('martin_swing', 1.6, 'Размах двуручником', 'martin_swing · удар 0.75 с', trail(0.62)),
             ('martin_overhead', 2.0, 'Рубящий удар сверху', 'martin_overhead · клинок в землю, удар 0.95 с', slam),
             ('martin_thrust', 1.4, 'Выпад', 'martin_thrust · удар 0.6 с', trail(0.5)),
             ('martin_shield_bash', 1.5, 'Рывок щитом', 'martin_shield_bash · рывок 0.45 с, удар 0.75 с', dash),
             ('martin_command', 2.2, 'Команда «В атаку!»', 'martin_command · баф солдатам', command),
             ('martin_banner_plant', 2.4, 'Вонзает знамя', 'martin_banner_plant · знамя встаёт на 1.3 с', banner),
             ('martin_phase2', 3.0, 'Переход в фазу 2 «Знамя» (66%)', 'martin_phase2 · меч в землю, рёв', phase2),
             ('martin_phase3', 3.2, 'Переход в фазу 3 «Последний полководец» (33%)', 'martin_phase3 · присед, оборот, меч над головой', phase3)]
    segs, L1 = seq_anims(items, P)
    loops = {'martin_walk': 1.6}
    banner_from = segs[6]['t0']

    def f1(t):
        s, (a, ta, mix) = seq_pose(segs, t, P, loops)
        fr = {'objs': [m_obj(a, ta, mix)], 'cap': s['cap'], 'sub': s['sub'], 'groundSize': 200,
              'cam': orbit(32 + 10 * math.sin(t / L1 * math.pi), 9, 15.5, (0, 2.5, -0.6))}
        sprites = []
        if s['fx'] and t >= s['t0']:
            x = s['fx'](t - s['t0'])
            sprites += x.get('sprites', [])
            fr['objs'] += x.get('objs_extra', [])
            if 'tintx' in x:
                fr['tint'] = list(x['tintx'])
        if t > segs[6]['t1'] + 0.01:          # знамя остаётся стоять до конца фаз
            bt = t - banner_from - 1.3
            fr['objs'].append(dict(model='martin_banner', anim='martin_banner_idle', t=(bt - 1.2) % 2.0, pos=BAN, ry=-10))
            sprites.append(decal('martin_banner_ring', BAN, 8, GOLD, 0.35))
        fr['sprites'] = sprites
        return fr
    c.seg(L1, f1)
    # ---- переход к войску
    c.seg(0.5, lambda t: dict(f1(L1), fade=ease(t / 0.5)))
    # ---- призрачные солдаты
    SOL = [(-2.2, 0.45), (0.0, 0.0), (2.2, 0.25)]   # x, сдвиг времени
    sitems = [('martin_soldier_spawn', 1.2, 'Призрачный солдат: появление', 'martin_soldier_spawn · встаёт из земли, туман'),
              ('martin_soldier_idle', 2.4, 'Призрачный солдат: покой', 'martin_soldier_idle · щит на предплечье, меч — кость'),
              ('martin_soldier_attack', 1.0, 'Призрачный солдат: укол из-за щита', 'martin_soldier_attack · удар 0.45 с'),
              ('martin_soldier_brace', 3.2, 'Призрачный солдат: «Строй»', 'martin_soldier_brace · плечом в щит, держит удар'),
              ('martin_soldier_vanish', 1.2, 'Призрачный солдат: исчезновение', 'martin_soldier_vanish · рассеивается (gone 0.8 с)')]
    ss, L2 = seq_anims(sitems, P)
    sl = {'martin_soldier_idle': 2.4, 'martin_soldier_brace': 1.6}

    def f2(t):
        s, _ = seq_pose(ss, t, P, sl)
        objs, spr = [], []
        for x, dt in SOL:
            tt = max(0.0, t - dt * (1 if t < ss[0]['t1'] + 0.3 else 0))
            _, (a, ta, mix) = seq_pose(ss, tt, P, sl)
            if a == 'martin_soldier_vanish':
                ta = min(ta, 0.8)
            o = dict(model='martin_soldier', key='sol%d' % x, anim=a, t=ta, pos=[x, 0, 0], ry=0)
            if mix:
                o['mix'] = mix
            if t >= ss[-1]['t0']:
                o['op'] = 1 - lin(t - ss[-1]['t0'], 0.3, 0.8)
            if t < dt:
                o['op'] = 0
            objs.append(o)
            # туман у ног (аура), вспышка появления, рассеивание
            au = 0.45 * (1 - lin(t - ss[-1]['t0'], 0.2, 0.8)) * lin(t - dt, 0, 0.5)
            spr.append(decal('glow', [x, 0.04, 0], 1.0, GHOST, au))
            spr += burst('mote_wisp', [x, 0.2, 0], t - dt, 8, 1.0, (0.3, 0.55), GHOST, 61 + int(x * 3), life=1.0, up=1.5, spread=(1, 0.3, 1), op=0.7)
            spr += burst('mote_wisp', [x, 1.0, 0], t - ss[-1]['t0'] - 0.2, 10, 1.2, (0.3, 0.6), GHOST, 71 + int(x * 3), life=0.9, up=1.2, op=0.7)
            if ss[2]['t0'] <= t < ss[2]['t1']:
                k = pulse(t - ss[2]['t0'], 0.4, 0.05, 0.05, 0.2)
                spr.append(glow([x + 0.15, 1.2, -1.3], 0.7 * k + 0.01, GHOST, 0.8 * k))
            if ss[3]['t0'] <= t < ss[3]['t1']:   # удары по щиту строя
                for hit in (0.6, 1.6, 2.6):
                    k = pulse(t - ss[3]['t0'], hit + 0.1 * x, 0.04, 0.04, 0.25)
                    spr.append(glow([x, 1.2, -0.75], 0.9 * k + 0.01, GOLD_HI, 0.8 * k))
        if ss[3]['t0'] <= t < ss[3]['t1']:
            spr.append(decal('martin_emblem', [0, 0.03, 0.2], 4.2, GHOST, 0.35 * pulse(t - ss[3]['t0'], 0, 0.4, 2.2, 0.5)))
        fr = {'objs': objs, 'sprites': spr, 'cap': s['cap'], 'sub': s['sub'], 'groundSize': 200,
              'cam': orbit(28 - 8 * t / L2, 10, 9.0, (0, 1.05, 0)), 'fade': 1 - lin(t, 0, 0.4)}
        return fr
    c.seg(L2 + 0.3, f2)
    c.seg(0.4, lambda t: dict(f2(L2 + 0.3), fade=ease(t / 0.4)))
    # ---- знамя
    bitems = [('martin_banner_plant', 1.2, 'Знамя: вонзание', 'martin_banner_plant · дрожь древка, полотнище взлетает'),
              ('martin_banner_idle', 2.0, 'Знамя: стоит', 'martin_banner_idle · волна полотнища, аура r8'),
              ('martin_banner_hit', 0.4, 'Знамя: удар', 'martin_banner_hit · на каждый удар'),
              ('martin_banner_hit', 0.4, 'Знамя: удар', 'martin_banner_hit · на каждый удар'),
              ('martin_banner_cut', 2.2, 'Знамя: срублено', 'martin_banner_cut · верх ломается и падает')]
    bs, L3 = seq_anims(bitems, P)

    def f3(t):
        s, (a, ta, mix) = seq_pose(bs, t, P, {'martin_banner_idle': 2.0})
        if a == 'martin_banner_cut':
            ta = min(ta, 1.6)
        o = dict(model='martin_banner', anim=a, t=ta, pos=M0, ry=-20)
        if mix:
            o['mix'] = mix
        spr = burst('mote_ash', [0, 0.1, 0], t, 14, 1.8, (0.25, 0.45), '#b8a890', 81, life=0.8, grav=3, up=1, spread=(1, 0.2, 1), op=0.7)
        ring = lin(t, 0, 0.4) * (1 - lin(t - bs[4]['t0'], 0, 0.6))
        spr.append(decal('martin_banner_ring', M0, 1 + 7 * lin(t, 0, 0.5), GOLD, 0.35 * ring))
        for k in (2, 3):
            tt = t - bs[k]['t0']
            spr += burst('glow', [0.2, 1.5, -0.2], tt, 10, 2.0, (0.1, 0.22), GOLD_HI, 90 + k, life=0.4, grav=3)
        tt = t - bs[4]['t0']
        spr += burst('glow', [0, 1.25, 0], tt, 18, 2.4, (0.1, 0.25), GOLD_HI, 95, life=0.6, grav=4)
        spr += burst('mote_ash', [0, 0.2, 0.6], tt - 1.0, 14, 1.6, (0.25, 0.45), '#b8a890', 96, life=0.8, grav=2, up=0.8, spread=(1.4, 0.2, 1), op=0.7)
        return {'objs': [o], 'sprites': spr, 'cap': s['cap'], 'sub': s['sub'], 'groundSize': 200,
                'cam': orbit(30 + 10 * t / L3, 8, 12.0, (0, 2.0, 0)), 'fade': 1 - lin(t, 0, 0.4)}
    c.seg(L3 + 0.5, f3)
    return c


def martin_spells():
    c = Clip('t29_spells', M_TAG)

    def title_env(t, a, b):
        return pulse(t, a, 0.5, b - a - 1.25, 0.75)

    # ---------------- «Атака конницы»
    LANES = [-9.0, -3.0, 3.0, 9.0]
    Z0, ZL = -46.0, 40.0          # начало полосы (край арены), длина; всадники несутся по +z к Мартину

    def cav(t):
        L = 3.4
        a = 'martin_cavalry' if t < L else 'martin_idle'
        ta = t if t < L else (t - L) % 3.0
        mix = {'anim': 'martin_idle', 't': 0, 'k': ease((t - L) / 0.3)} if L <= t < L + 0.3 else None
        if mix:
            a, ta = 'martin_cavalry', L
        spr, meshes = [], []
        # свет на меч, столб света (0–1)
        k0 = pulse(t, 0.2, 0.6, 0.6, 0.6)
        spr.append(glow([0.6, 5.6, -1.2], 1.2 * k0 + 0.01, GOLD_HI, 0.8 * k0))
        spr.append({'tex': 'glow', 'at': [0.6, 12, -1.2], 'w': 1.2, 'h': 16, 'color': GOLD_HI, 'op': 0.35 * k0})
        # рог: вспышка и волна r26 на 1.0
        tw = t - 1.0
        if 0 <= tw < 1.2:
            spr.append(decal('wave_ring', M0, 1 + 25 * ease(tw / 1.2), GOLD, 0.7 * (1 - tw / 1.2)))
        spr += burst('glow', [0.6, 5.6, -1.2], tw, 14, 3.0, (0.12, 0.3), GOLD_HI, 101, life=0.7, grav=2)
        # полосы: предупреждение 1.0–3.0 (мигают), всадники 3.0–4.4, гаснут
        lop = lin(t, 1.0, 1.4) * (1 - lin(t, 4.2, 4.8))
        blink = 0.65 + 0.35 * math.sin((t - 1.0) * 9) if t < 3.0 else 1.0
        for x in LANES:
            spr.append(decal('martin_lane', [x, 0.04, Z0 + ZL / 2], 1, '#8fd8f0', 0.9 * lop * blink))
            spr[-1].update(w=3, h=ZL)
            for k in range(3):
                tr = t - 3.0 - 0.1 * k
                if tr < 0 or tr > 1.4:
                    continue
                z = Z0 - 4 - 3.2 * k + 52 * tr / 1.4
                op = min(1, tr / 0.15) * (1 - lin(tr, 1.15, 1.4))
                meshes.append(dict(mesh='martin_cavalry_rider', key='rider%d_%d' % (LANES.index(x), k), pos=[x + (k - 1) * 0.5, 0, z], ry=0, op=op))
                for j in range(4):
                    spr.append({'tex': 'mote_ash', 'at': [x + (k - 1) * 0.5 + (j - 1.5) * 0.4, 0.3 + 0.15 * j, z - 1.5 - 0.8 * j], 'size': 0.8,
                                'color': '#a9c9d4', 'op': 0.35 * op * (1 - j / 4)})
        cam = camkeys([(0, -32, -4, 12.0, (0, 3.6, 0)), (1.6, -32, -4, 12.0, (0, 3.8, 0)), (2.7, -62, 30, 40.0, (0, 0, -17)),
                       (5.0, -56, 32, 40.0, (0, 0, -17))], t)
        fr = {'objs': [m_obj(a, ta, mix)], 'meshes': meshes, 'sprites': spr, 'cam': cam, 'groundSize': 200,
              'cap': 'Особое: «Атака конницы»', 'sub': 'martin_cavalry · рог (call 1.0 с) → полосы 2 с → три всадника по каждой полосе',
              'title': {'img': 'title:martin_cavalry_ru', 'op': title_env(t, 0.3, 2.8)}, 'dim': 1 - 0.35 * lin(t, 0, 1.0) * (1 - lin(t, 4.4, 5.0))}
        return fr
    c.seg(5.2, cav)

    # ---------------- «Приказ стоять насмерть»
    def hold(t):
        if t < 2.5:
            a, ta, mix = 'martin_hold_the_line', t, None
        elif t < 4.5:
            a, ta, mix = 'martin_hold_loop', (t - 2.5) % 2.0, None
        elif t < 5.3:
            a, ta, mix = 'martin_hold_end', t - 4.5, None
        else:
            a, ta = 'martin_hold_end', 0.8
            mix = {'anim': 'martin_idle', 't': 0, 'k': ease((t - 5.3) / 0.3)}
        tw = t - 1.1
        up = ease(lin(tw, 0, 0.35))
        op = up * (1 - lin(t, 4.6, 5.1))
        meshes = [dict(mesh='martin_shield_wall', pos=M0, ry=180, sy=max(0.02, up), op=op)] if op > 0 else []
        spr = []
        if 0 <= tw < 0.8:
            spr.append(decal('wave_ring', M0, 1 + 6 * tw / 0.8, GOLD, 0.8 * (1 - tw / 0.8)))
        spr += burst('glow', [0, 1.4, -2.6], tw, 20, 2.0, (0.1, 0.24), GOLD_HI, 111, life=0.7, spread=(2.5, 1, 0.6), grav=1)
        for i in range(6):       # искры по кромкам щитов
            ang = math.radians(-50 + 20 * i)
            k = pulse((t * 1.7 + i * 0.37) % 1.0, 0, 0.1, 0.05, 0.3) * op
            spr.append(glow([math.sin(ang) * 3.2, 2.8, -math.cos(ang) * 3.2], 0.5 * k + 0.01, GOLD_HI, 0.8 * k))
        spr.append(decal('martin_emblem', M0, 3.4, GOLD, 0.45 * op))
        cam = camkeys([(0, 20, 6, 15.5, (0, 2.3, 0)), (1.1, 22, 6, 15.5, (0, 2.3, 0)), (2.6, 150, 18, 16.0, (0, 2.0, -0.5)),
                       (5.6, 165, 18, 16.0, (0, 2.0, -0.5))], t)
        return {'objs': [m_obj(a, ta, mix)], 'meshes': meshes, 'sprites': spr, 'cam': cam, 'groundSize': 200,
                'cap': 'Особое: «Приказ стоять насмерть»', 'sub': 'щит в землю (wall 1.1 с) → дуга из 6 призрачных щитов только спереди — спина открыта',
                'title': {'img': 'title:martin_hold_ru', 'op': title_env(t, 0.3, 2.8)}}
    c.seg(5.6, hold)

    # ---------------- «Стена щитов»
    def swall(t):
        a = 'martin_shield_wall' if t < 2.0 else 'martin_idle'
        ta = t if t < 2.0 else (t - 2.0) % 3.0
        mix = {'anim': 'martin_idle', 't': 0, 'k': ease((t - 2.0) / 0.3)} if 2.0 <= t < 2.3 else None
        if mix:
            a, ta = 'martin_shield_wall', 2.0
        tw = t - 1.0
        up = ease(lin(tw, 0, 1.0))
        z = -3.5 - 14 * lin(tw, 1.0, 4.0)
        op = lin(tw, 0, 0.3) * (1 - lin(t, 5.0, 5.4))
        meshes = [dict(mesh='martin_shield_line', pos=[0, -3.2 * (1 - up), z], ry=180, op=op)] if tw >= 0 else []
        spr = []
        if tw >= 0:
            for i in range(12):
                spr.append({'tex': 'mote_ash', 'at': [-11 + 2 * i, 0.3, z - 0.6], 'size': 1.0, 'color': '#b8a890', 'op': 0.35 * op})
        spr += burst('mote_ash', [0.5, 0.1, -2.0], tw, 14, 2.0, (0.25, 0.45), '#b8a890', 121, life=0.8, grav=3, up=1, spread=(1, 0.2, 1), op=0.7)
        cam = camkeys([(0, 210, 26, 17.0, (0, 2.0, -1.0)), (1.2, 205, 32, 20.0, (0, 1.5, -3.0)), (4.0, 196, 38, 26.0, (0, 1.0, -8.0)),
                       (5.6, 194, 38, 26.0, (0, 1.0, -8.0))], t)
        return {'objs': [m_obj(a, ta, mix)], 'meshes': meshes, 'sprites': spr, 'cam': cam, 'groundSize': 200,
                'cap': 'Заклинание: «Стена щитов»', 'sub': 'martin_shield_wall · щит в землю (slam 1.0 с) → стена с просветами идёт на игроков',
                'title': {'text': 'Стена щитов', 'op': title_env(t, 0.3, 2.8)}}
    c.seg(5.6, swall)

    # ---------------- «Залп лучников»
    ARCH = [((k - 3) * 1.8, 5.0 + abs(k - 3) * 0.6) for k in range(7)]
    MARKS = [(-4.0, -6.0), (2.0, -8.0), (5.0, -4.5), (-1.0, -10.0)]

    def volley(t):
        a = 'martin_volley' if t < 2.2 else 'martin_idle'
        ta = t if t < 2.2 else (t - 2.2) % 3.0
        mix = {'anim': 'martin_idle', 't': 0, 'k': ease((t - 2.2) / 0.3)} if 2.2 <= t < 2.5 else None
        if mix:
            a, ta = 'martin_volley', 2.2
        meshes, spr = [], []
        ra = ease(lin(t, 0.8, 1.2))
        aop = lin(t, 0.8, 1.0) * (1 - lin(t, 3.4, 3.9))
        for i, (x, z) in enumerate(ARCH):
            if aop > 0:
                meshes.append(dict(mesh='martin_archer_ghost', key='arch%d' % i, pos=[x, -2.4 * (1 - ra), z], ry=180, op=aop))
            spr += burst('mote_wisp', [x, 0.2, z], t - 0.8, 4, 1.0, (0.3, 0.5), GHOST, 130 + i, life=0.7, up=1.5, spread=(1, 0.3, 1), op=0.6)
            ta_ = t - 1.2 - 0.03 * i        # стрела вверх
            if 0 <= ta_ < 0.5:
                meshes.append(dict(mesh='martin_arrow', key='up%d' % i, pos=[x, 2.2 + 18 * ta_, z - 0.5], rx=180, op=1 - ta_ / 0.5))
        for j, (x, z) in enumerate(MARKS):
            mk = lin(t, 1.2, 1.4) * (1 - lin(t, 2.9, 3.3))
            spr.append(decal('martin_arrow_mark', [x, 0.04, z], 1.6, RED, (0.6 + 0.4 * math.sin((t - 1.2) * 12)) * 0.9 * mk))
            for n in range(5):
                tf = t - 2.4 - 0.05 * n - 0.04 * j
                if 0 <= tf < 0.3:
                    ox, oz = math.cos(n * 1.3 + j) * 0.8, math.sin(n * 1.3 + j) * 0.8
                    meshes.append(dict(mesh='martin_arrow', key='dn%d_%d' % (j, n), pos=[x + ox, 9 * (1 - tf / 0.3), z + oz], op=1))
                elif 0.3 <= tf < 0.9:
                    ox, oz = math.cos(n * 1.3 + j) * 0.8, math.sin(n * 1.3 + j) * 0.8
                    meshes.append(dict(mesh='martin_arrow', key='dn%d_%d' % (j, n), pos=[x + ox, -0.6, z + oz], op=1 - lin(tf, 0.5, 0.9)))
            ti = t - 2.7 - 0.04 * j
            spr += burst('mote_ash', [x, 0.1, z], ti, 12, 1.6, (0.25, 0.45), '#c8b8a0', 140 + j, life=0.7, grav=3, up=1, spread=(1, 0.2, 1), op=0.7)
            if 0 <= ti < 0.4:
                spr.append(glow([x, 0.5, z], 2.0 * (1 - ti / 0.4), GHOST, 0.7 * (1 - ti / 0.4)))
        cam = camkeys([(0, -22, 18, 17.0, (0, 2.2, 0)), (1.2, -24, 26, 22.0, (0, 1.6, -2)), (2.4, -26, 34, 26.0, (0, 0.8, -4)),
                       (4.2, -28, 34, 26.0, (0, 0.8, -4))], t)
        return {'objs': [m_obj(a, ta, mix)], 'meshes': meshes, 'sprites': spr, 'cam': cam, 'groundSize': 200,
                'cap': 'Заклинание: «Залп лучников»', 'sub': 'martin_volley · лучники встают (draw 0.8 с) → «пли!» (loose 1.2 с) → красные метки 1.5 с → стрелы',
                'title': {'text': 'Залп лучников', 'op': title_env(t, 0.3, 2.8)}}
    c.seg(4.2, volley)

    # ---------------- «Вызов на дуэль»
    PL = [0.0, 0, -7.0]

    def duel(t):
        a = 'martin_duel' if t < 2.0 else 'martin_idle'
        ta = t if t < 2.0 else (t - 2.0) % 3.0
        mix = {'anim': 'martin_idle', 't': 0, 'k': ease((t - 2.0) / 0.3)} if 2.0 <= t < 2.3 else None
        if mix:
            a, ta = 'martin_duel', 2.0
        k = ease(lin(t, 0.9, 1.4))
        spr = [decal('martin_duel_ring', [0, 0.04, -3.5], 6.4, GOLD, 0.9 * k, rot=20 * t)]
        spr.append({'tex': 'thin_ring', 'at': [0, 1.6, -3.5], 'w': 12.8, 'h': 3.0, 'color': GOLD, 'op': 0.0})
        spr.append(decal('thin_ring', [PL[0], 0.05, PL[2]], 0.9, GOLD_HI, 0.9 * k))
        spr.append(glow([PL[0], 2.2, PL[2]], 0.9, GOLD_HI, 0.55 * k * (0.8 + 0.2 * math.sin(t * 6))))
        tw = t - 0.9
        if 0 <= tw < 0.6:
            spr.append(glow([0.4, 3.0, -3.2], 3 * (1 - tw / 0.6), GOLD_HI, 0.6 * (1 - tw / 0.6)))
            spr.append(decal('wave_ring', [0, 0.04, -3.5], 1 + 6 * tw / 0.6, GOLD, 0.8 * (1 - tw / 0.6)))
        for i in range(16):        # завеса по кольцу
            ang = i / 16 * 6.283 + t * 0.4
            spr.append({'tex': 'glow', 'at': [math.cos(ang) * 6.3, 1.0 + 0.4 * math.sin(t * 3 + i), -3.5 + math.sin(ang) * 6.3], 'w': 0.6, 'h': 2.4,
                        'color': GOLD, 'op': 0.35 * k})
        cam = camkeys([(0, -30, 10, 16.0, (0, 2.2, -2.5)), (0.9, -40, 14, 17.0, (0, 2.0, -3.0)), (2.0, -78, 24, 20.0, (0, 1.4, -3.5)),
                       (3.8, -84, 24, 20.0, (0, 1.4, -3.5))], t)
        return {'objs': [m_obj(a, ta, mix), dict(model='steve', pos=PL, ry=180)], 'sprites': spr, 'cam': cam, 'groundSize': 200,
                'cap': 'Заклинание: «Вызов на дуэль»', 'sub': 'martin_duel · остриё на игрока (challenge 0.9 с) → кольцо r6: внутри только двое',
                'title': {'text': 'Вызов на дуэль', 'op': title_env(t, 0.3, 2.8)}}
    c.seg(3.8, duel)

    # ---------------- «Боевой клич»
    def warcry(t):
        a = 'martin_warcry' if t < 1.8 else 'martin_idle'
        ta = t if t < 1.8 else (t - 1.8) % 3.0
        mix = {'anim': 'martin_idle', 't': 0, 'k': ease((t - 1.8) / 0.3)} if 1.8 <= t < 2.1 else None
        if mix:
            a, ta = 'martin_warcry', 1.8
        spr = []
        for i in range(3):
            tw = t - 0.6 - 0.18 * i
            if 0 <= tw < 1.0:
                spr.append(decal('wave_ring', M0, 1 + 11 * ease(tw), RED, 0.85 * (1 - tw)))
                spr.append({'tex': 'thin_ring', 'at': [0, 3.4, -0.2], 'size': 2 + 18 * ease(tw), 'color': '#ff6a50', 'op': 0.5 * (1 - tw)})
        tw = t - 0.6
        if 0 <= tw < 1.0:
            spr.append(glow([0, 3.6, -0.4], 2 + 10 * tw, '#ff5030', 0.35 * (1 - tw)))
        spr += burst('mote_ash', [0, 0.2, 0], tw, 18, 3.0, (0.3, 0.55), '#b8a890', 151, life=0.9, grav=1, up=0.3, spread=(1, 0.1, 1), op=0.6)
        cam = camkeys([(0, -20, 10, 13.0, (0, 2.6, -0.4)), (0.6, -20, 10, 13.0, (0, 2.6, -0.4)), (1.6, -24, 18, 19.0, (0, 2.0, -0.4)),
                       (3.0, -26, 18, 19.0, (0, 2.0, -0.4))], t)
        shake = 0.08 * pulse(t, 0.6, 0.05, 0.3, 0.3) * math.sin(t * 60)
        cam['look'][0] += shake
        return {'objs': [m_obj(a, ta, mix)], 'sprites': spr, 'cam': cam, 'groundSize': 200, 'tint': ['#7a0a00', 0.22 * pulse(t, 0.6, 0.08, 0.15, 0.6)],
                'cap': 'Заклинание: «Боевой клич»', 'sub': 'martin_warcry · рёв (cry 0.6 с): кольца до r12 — касты сорваны, солдаты сильнее',
                'title': {'text': 'Боевой клич', 'op': title_env(t, 0.3, 2.6)}}
    c.seg(3.0, warcry)
    # плавные склейки: затемнение 0.25 с на стыках
    _fade_joins(c, [5.2, 10.8, 16.4, 20.6, 24.4])
    return c


def _fade_joins(c, joins, half=0.25):
    for i, f in enumerate(c.frames):
        t = i / FPS
        k = 0.0
        for j in joins:
            if abs(t - j) < half:
                k = max(k, 1 - abs(t - j) / half)
        if t < half:
            k = max(k, 0.6 * (1 - t / half))
        if t > c.dur - half:
            k = max(k, 0.6 * (1 - (c.dur - t) / half))
        f['fade'] = max(f.get('fade', 0), k)


def martin_finale():
    c = Clip('t29_finale', M_TAG)
    ROWS = [(x, 4.2) for x in (-5, -3, -1, 1, 3, 5)] + [(x, 6.2) for x in (-6, -4, -2, 0, 2, 4, 6)]

    def spawn(t):
        a = 'martin_spawn' if t < 6.5 else 'martin_idle'
        ta = t if t < 6.5 else (t - 6.5) % 3.0
        mix = {'anim': 'martin_idle', 't': 0, 'k': ease((t - 6.5) / 0.3)} if 6.5 <= t < 6.8 else None
        if mix:
            a, ta = 'martin_spawn', 6.5
        spr, meshes = [], []
        spr.append(decal('martin_emblem', M0, 4.2, GOLD, 0.65 * lin(t, 0.5, 1.5)))
        for i in range(14):          # туман
            ang = i * 0.9
            spr.append({'tex': 'mote_cloud', 'at': [math.cos(ang + t * 0.1) * (3 + i % 4), 0.5, math.sin(ang + t * 0.1) * (3 + i % 4)], 'size': 3.0,
                        'color': '#6a7480', 'op': 0.22 * (1 - lin(t, 2.6, 4.5)), 'add': True})
        k = pulse(t, 1.0, 0.15, 0.3, 0.8)
        spr.append(glow([0, 2.55, -0.55], 0.6 * k + 0.01, '#bfe8ff', 0.9 * k))           # блик в щели забрала
        kb = pulse(t, 1.0, 0.4, 1.2, 1.0)
        spr.append({'tex': 'glow', 'at': [0, 10, 0], 'w': 3.0, 'h': 22, 'color': '#fff2c8', 'op': 0.35 * kb})
        for i, (x, z) in enumerate(ROWS):    # два ряда призрачных солдат встают за спиной
            tr = t - 1.0 - 0.07 * i
            up = ease(lin(tr, 0, 0.8))
            op = lin(tr, 0, 0.4) * (1 - lin(t, 7.4, 8.0))
            if op > 0:
                meshes.append(dict(mesh='martin_soldier_ghost', key='g%d' % i, pos=[x, -2.2 * (1 - up), z], ry=180, op=op))
                spr += burst('mote_wisp', [x, 0.2, z], tr, 3, 0.8, (0.3, 0.5), GHOST, 160 + i, life=0.7, up=1.5, spread=(1, 0.3, 1), op=0.5)
        tw = t - 2.6
        if 0 <= tw < 1.0:
            spr.append(decal('wave_ring', M0, 1 + 9 * tw, GOLD, 0.7 * (1 - tw)))
        tp = t - 4.0
        spr += burst('glow', [0, 0.4, -1.4], tp, 22, 2.6, (0.1, 0.25), GOLD_HI, 171, life=0.7, grav=5, up=1.2)
        spr += burst('mote_ash', [0, 0.1, -1.4], tp, 16, 1.6, (0.25, 0.5), '#b8a890', 172, life=1.0, grav=2, up=1, spread=(1, 0.2, 1), op=0.7)
        ts = t - 5.0
        if 0 <= ts < 0.8:
            spr.append(glow([0.3, 3.6, -0.8], 2.6 * (1 - ts / 0.8) + 0.3, GOLD_HI, 0.8 * (1 - ts / 0.8)))
            spr.append(decal('thin_ring', M0, 1 + 8 * ts, GOLD_HI, 0.9 * (1 - ts / 0.8)))
        cam = camkeys([(0, 0, 10, 17.0, (0, 1.6, 0)), (1.0, 0, 10, 14.5, (0, 1.6, 0)), (1.9, 155, 16, 13.0, (0, 2.2, -1.0)),
                       (2.6, 160, 16, 13.0, (0, 2.2, -1.0)), (4.0, 15, 2, 13.5, (0, 2.8, 0)), (4.5, 28, 5, 12.5, (0, 2.8, 0)),
                       (5.2, 28, 5, 12.5, (0, 3.0, 0)), (6.0, 18, 8, 14.5, (0, 2.8, 0)), (8.2, 14, 8, 15.0, (0, 2.8, 0))], t)
        return {'objs': [m_obj(a, ta, mix)], 'meshes': meshes, 'sprites': spr, 'cam': cam, 'groundSize': 200,
                'dim': 0.45 + 0.55 * lin(t, 0.8, 3.0), 'cap': 'Появление', 'sub': 'martin_spawn · на колене → встаёт (2.6 с) → выдёргивает меч (4.0 с) → салют (5.0 с)',
                'title': {'img': 'title:martin_ru', 'op': pulse(t, 5.4, 0.5, 1.6, 0.75)}, 'fade': 0.6 * (1 - lin(t, 0, 0.5))}
    c.seg(8.4, spawn)
    c.seg(0.4, lambda t: dict(spawn(8.4), fade=ease(t / 0.4)))
    SOLS = [(-3.0, -0.6), (3.0, -0.6)]
    BAN = [-4.8, 0, 1.4]
    SPEECH = 'Хорошо, вы доказали свою силу... Я помогу Эребу, если эта ваша просьба'

    def yld(t):
        t0 = 0.6                      # до блока — стойка со строем
        u = t - t0
        if u < 0:
            a, ta, mix = 'martin_idle', t % 3.0, None
            if u > -0.3:
                mix = {'anim': 'martin_block_yield', 't': 0, 'k': ease((u + 0.3) / 0.3)}
        elif u < 3.2:
            a, ta, mix = 'martin_block_yield', u, None
        elif u < 4.4:
            a, ta, mix = 'martin_to_npc', u - 3.2, None
        else:
            a, ta = 'martin_to_npc', 1.2
            mix = {'anim': 'martin_npc_idle', 't': (u - 4.4) % 4.0, 'k': ease((u - 4.4) / 0.4)}
        objs = [m_obj(a, ta, mix)]
        spr = []
        for i, (x, z) in enumerate(SOLS):
            tv = u - 1.2
            if tv < 0.8:
                sa, st = ('martin_soldier_brace', t % 1.6) if tv < 0 else ('martin_soldier_vanish', max(0.0, tv))
                objs.append(dict(model='martin_soldier', key='ys%d' % i, anim=sa, t=st, pos=[x, 0, z], ry=0, op=1 - lin(tv, 0.2, 0.8)))
            spr += burst('mote_wisp', [x, 1.0, z], tv, 10, 1.2, (0.3, 0.6), GHOST, 180 + i, life=0.9, up=1.2, op=0.7)
        bo = 1 - lin(u, 1.2, 2.0)
        if bo > 0:
            objs.append(dict(model='martin_banner', anim='martin_banner_idle', t=t % 2.0, pos=BAN, ry=-10, op=bo))
            spr.append(decal('martin_banner_ring', BAN, 8, GOLD, 0.6 * bo))
        tb = u - 0.2                  # блок: сноп искр от щита, звон-волна, засветка
        spr += burst('glow', [-0.6, 2.6, -1.6], tb, 26, 4.0, (0.08, 0.22), GOLD_HI, 191, life=0.6, grav=4, spread=(1, 0.8, 1))
        if 0 <= tb < 0.5:
            spr.append(glow([-0.6, 2.6, -1.6], 3 * (1 - tb / 0.5), WHITE, 0.8 * (1 - tb / 0.5)))
            spr.append({'tex': 'thin_ring', 'at': [-0.6, 2.6, -1.6], 'size': 1 + 8 * tb, 'color': GOLD_HI, 'op': 0.8 * (1 - tb / 0.5)})
        ky = pulse(u, 1.2, 0.8, 4.0, 1.0)     # мягкий свет сдачи
        spr.append(glow([0, 3.0, 0], 6, '#fff0c8', 0.12 * ky))
        cam = camkeys([(0, 6, 6, 13.0, (0, 2.6, -0.5)), (0.8, 6, 6, 13.0, (0, 2.6, -0.5)), (1.8, 25, 8, 14.5, (0, 2.8, 0)),
                       (5.0, 25, 7, 13.5, (0, 2.7, 0)), (8.6, 28, 7, 13.5, (0, 2.7, 0))], t)
        sh = 0.06 * pulse(u, 0.2, 0.03, 0.1, 0.15) * math.sin(t * 70)
        cam['look'][0] += sh
        sp_op = pulse(u, 2.4, 0.3, 3.6, 0.5)
        return {'objs': objs, 'sprites': spr, 'cam': cam, 'groundSize': 200,
                'cap': 'Блок-сдача → мирный NPC', 'sub': 'martin_block_yield (block 0.2, lower 1.2, speak 2.4 с) → martin_to_npc → martin_npc_idle',
                'speech': {'text': SPEECH, 'op': sp_op} if sp_op > 0 else None, 'tint': ['#ffffff', 0.15 * pulse(u, 0.2, 0.03, 0.04, 0.15)],
                'fade': max(1 - lin(t, 0, 0.4), 0.6 * lin(t, 8.6, 9.0))}
    c.seg(9.0, yld)
    return c


M_TEX = ['glow', 'mote_ash', 'mote_wisp', 'mote_cloud', 'wave_ring', 'thin_ring', 'martin_emblem', 'martin_banner_ring', 'martin_lane',
         'martin_arrow_mark', 'martin_duel_ring', 'title:martin_ru', 'title:martin_cavalry_ru', 'title:martin_hold_ru']
M_PRE = [{'model': 'martin'}, {'model': 'martin_soldier'}, {'model': 'martin_banner'}, {'model': 'steve'}]


# ================================================================== Т30 Эреб
E_TAG = 'T30 · Эреб, Первый Предатель'
E_LOOPS = {'ereb_idle': 4.0, 'ereb_walk': 1.2, 'ereb_guard': 1.0}
PALM = (-0.15, 1.27, -0.55)         # левая ладонь в покое финала (из кадров t30_cinematics)


def e_obj(anim, t, mix=None, **kw):
    o = dict(model='ereb', anim=anim, t=t, pos=kw.pop('pos', [0, 0, 0]), ry=kw.pop('ry', 0))
    if mix:
        o['mix'] = mix
    o.update(kw)
    return o


def rel(p, base, ry=0):
    """точка p (оси модели: x, y, z; вперёд = −z) от base с поворотом ry."""
    a = math.radians(ry)
    x, z = p[0] * math.cos(a) + p[2] * math.sin(a), -p[0] * math.sin(a) + p[2] * math.cos(a)
    return [base[0] + x, base[1] + p[1], base[2] + z]


def shards(at, t, n, seed, speed=1.6, life=0.7, spread=(1, 1, 1), up=0.3, op=0.9):
    return burst('mote_glass', at, t, n, speed, (0.12, 0.26), GLASS_HI, seed, life=life, grav=1.5, up=up, spread=spread, op=op, spin=300)


def bfly_burst(at, t, n, seed, speed=1.4, life=1.2, op=0.9, up=0.6):
    out = burst('mote_butterfly', at, t, n, speed, (0.22, 0.36), GLASS, seed, life=life, up=up, op=op, flap=True)
    out += burst('mote_butterfly', at, t, max(1, n // 3), speed, (0.22, 0.34), GOLD_HI, seed + 7, life=life, up=up, op=op, flap=True)
    return out


def glint(at, t, size=0.6, color=GOLD_HI, life=0.25):
    if not (0 <= t < life):
        return []
    k = 1 - t / life
    return [glow(at, size * (0.5 + k), color, 0.95 * k), glow(at, size * 2.2 * k, color, 0.35 * k, tex='glow')]


def ereb_turntable():
    c = Clip('t30_turntable', E_TAG)
    D = 7.0
    return c.seg(D, lambda t: {'objs': [e_obj('ereb_idle', t % 4.0, ry=-360 * t / D)], 'cam': orbit(0, 6, 6.6, (0, 1.12, 0)), 'groundSize': 96,
                               'cap': 'Эреб — покой', 'sub': 'ereb_idle · рапира опущена, левая рука за спиной'})


def ereb_combat():
    c = Clip('t30_combat', E_TAG)
    P = 0.3
    TIP = (0.1, 1.35, -2.2)

    def hits(times):
        def fx(lt):
            s = []
            for h in times:
                s += glint(list(TIP), lt - h)
            return {'sprites': s}
        return fx

    def parry(lt):
        s = glint([0.2, 1.6, -0.6], lt - 0.15, 0.9) + burst('glow', [0.2, 1.6, -0.6], lt - 0.15, 10, 1.8, (0.06, 0.14), GOLD_HI, 201, life=0.4, grav=3)
        return {'sprites': s + glint(list(TIP), lt - 0.6)}

    def shard_cast(lt):
        s = []
        if 0.1 <= lt < 0.55:
            k = (lt - 0.1) / 0.45
            s.append(glow([-0.35, 1.3, -0.5], 0.4 + 0.4 * k, GLASS_HI, 0.6 * k))
            s += burst('mote_glass', [-0.35, 1.3, -0.5], (lt - 0.1) % 0.3, 4, 0.6, (0.08, 0.16), GLASS_HI, 211, life=0.3, op=0.8)
        t = lt - 0.55
        s += glint([-0.35, 1.3, -0.6], t, 1.0, GLASS_HI, 0.3)
        if 0 <= t < 0.8:            # веер осколков конусом вперёд
            R = rnd(212)
            for i in range(14):
                ang, el, sp = (R() - 0.5) * 0.7, (R() - 0.3) * 0.25, 7 + 3 * R()
                d = sp * t
                s.append({'tex': 'mote_glass', 'at': [-0.35 + math.sin(ang) * d, 1.3 + el * d, -0.6 - math.cos(ang) * d], 'size': 0.22 + 0.1 * R(),
                          'color': GLASS_HI, 'op': 0.95 * (1 - t / 0.8), 'rot': R() * 360 + 400 * t})
        return {'sprites': s}

    def cast_ill(lt):
        t = lt - 0.75
        s = glint([-0.3, 2.15, -0.25], t, 0.8, GLASS_HI, 0.4)
        s += bfly_burst([-0.3, 2.15, -0.25], t, 5, 221, speed=0.8, life=1.0)
        if 0 <= t < 0.6:
            s.append(decal('illusion_seal', [0, 0.03, 0], 1.2 + 1.5 * t, GLASS, 0.4 * (1 - t / 0.6)))
        return {'sprites': s}

    def disguise(lt):
        t = lt - 0.5
        s = []
        if 0 <= t < 0.5:
            k = 1 - t / 0.5
            s.append({'tex': 'illusion_seal', 'at': [0, 1.75, -0.35], 'size': 0.9 + 0.6 * t, 'color': GLASS_HI, 'op': 0.7 * k})
        s += shards([0, 1.2, 0], t, 8, 231, speed=1.0, spread=(0.5, 0.8, 0.5))
        return {'sprites': s}

    def vanish(lt):
        t = lt - 0.6
        s = shards([0, 1.0, 0], t + 0.1, 18, 241, speed=1.8) + bfly_burst([0, 1.3, 0], t, 5, 242)
        if 0 <= t + 0.1 < 0.4:
            s.append(glow([0, 1.0, 0], 1.6, GLASS_HI, 0.5 * (1 - (t + 0.1) / 0.4)))
        return {'sprites': s, 'op': 1 - lin(lt, 0.5, 0.62)}

    def backstab(lt):
        s = []
        if lt < 0.3:
            s.append(glow([0, 1.1, 0], 1.6 * (1 - lt / 0.3), WHITE, 0.6 * (1 - lt / 0.3)))
        s += shards([0, 1.0, 0], lt, 10, 251, speed=1.4)
        return {'sprites': s + glint(list(TIP), lt - 0.45), 'op': lin(lt, 0.0, 0.08)}

    def phase(lt):
        t = lt - 0.8
        s = []
        if 0 <= t < 0.9:
            s.append(glow([0, 1.2, 0], 3 * (1 - t / 0.9), WHITE, 0.45 * (1 - t / 0.9)))
            s.append(decal('wave_ring', [0, 0.03, 0], 1 + 10 * t, GLASS, 0.8 * (1 - t / 0.9)))
            s.append({'tex': 'illusion_seal', 'at': [0, 1.2, 0], 'size': 2 + 3 * t, 'color': GLASS_HI, 'op': 0.4 * (1 - t / 0.9)})
        s += shards([0, 1.6, 0], t, 36, 261, speed=2.6, life=0.9, spread=(1.6, 1.2, 1.6))
        return {'sprites': s}

    items = [('ereb_walk', 2.4, 'Шаг', 'ereb_walk · полы камзола следуют за ногами'),
             ('ereb_guard', 2.0, 'Стойка «ан гард»', 'ereb_guard · правый бок к врагу'),
             ('ereb_lunge', 1.2, 'Выпад', 'ereb_lunge · укол 0.5 с, блик на острие', hits([0.5])),
             ('ereb_flurry', 1.8, 'Серия из трёх уколов', 'ereb_flurry · уколы 0.45 / 0.8 / 1.15 с', hits([0.45, 0.8, 1.15])),
             ('ereb_parry', 1.0, 'Парирование и ответный укол', 'ereb_parry · искры у гарды 0.15 с, укол 0.6 с', parry),
             ('ereb_shard_cast', 1.2, 'Магия руками: стеклянные осколки', 'ereb_shard_cast · веер осколков из левой ладони (release 0.55 с)', shard_cast),
             ('ereb_cast_illusion', 1.4, 'Каст иллюзий', 'ereb_cast_illusion · щелчок пальцами (cast 0.75 с)', cast_ill),
             ('ereb_disguise', 1.0, 'Смена облика', 'ereb_disguise · ладонь по лицу (swap 0.5 с)', disguise),
             ('ereb_vanish', 0.8, 'Исчезновение', 'ereb_vanish · осколки и бабочки (gone 0.6 с)', vanish),
             ('ereb_backstab', 1.2, 'Удар в спину', 'ereb_backstab · появился в замахе (stab 0.45 с)', backstab),
             ('ereb_phase', 1.6, 'Смена фазы (66% / 33%)', 'ereb_phase · круг рапирой и салют, стекло трескается', phase)]
    segs, L = seq_anims(items, P)
    loops = {'ereb_walk': 1.2, 'ereb_guard': 1.0}

    def f(t):
        s, (a, ta, mix) = seq_pose(segs, t, P, loops)
        o = e_obj(a, ta, mix)
        fr = {'objs': [o], 'cap': s['cap'], 'sub': s['sub'], 'groundSize': 96, 'cam': orbit(34 + 10 * math.sin(t / L * math.pi), 8, 6.6, (0, 1.12, -0.2))}
        if s['fx'] and t >= s['t0']:
            x = s['fx'](t - s['t0'])
            fr['sprites'] = x.get('sprites', [])
            if 'op' in x:
                o['op'] = x['op']
        elif s['a'] == 'ereb_backstab':          # пауза перед появлением — модели нет
            o['op'] = 0
        return fr
    c.seg(L, f)
    _fade_joins(c, [])
    return c


def ereb_spells():
    c = Clip('t30_spells', E_TAG)
    VIC = [0, 0, -4.0]                  # жертва (пиромант Iron's вместо игрока), лицом к Эребу

    def tenv(t, a, b):
        return pulse(t, a, 0.5, b - a - 1.25, 0.75)

    # ---------------- «Ложный союзник»
    BEH = rel([0, 0, 1.6], VIC, 180)        # за спиной жертвы (жертва смотрит на +z)

    def false_ally(t):
        objs = [dict(model='pyromancer', pos=VIC, ry=180)]
        spr = []
        if t < 0.8:
            objs.append(e_obj('ereb_vanish', t, op=1 - lin(t, 0.5, 0.62)))
        tv = t - 0.6
        spr += shards([0, 1.0, 0], tv + 0.1, 18, 301, speed=1.8) + bfly_burst([0, 1.3, 0], tv, 5, 302)
        tg = t - 1.0                  # блик стекла за спиной жертвы (0.7 с)
        if 0 <= tg < 0.7:
            k = math.sin(tg / 0.7 * math.pi)
            p = rel([0, 1.45, 0.9], VIC, 180)
            spr += [glow(p, 1.3 * k, GLASS_HI, 0.9 * k)] + shards(p, tg, 4, 303, speed=0.4, life=0.7)
        if t >= 1.7:                  # появился за спиной — удар
            u = t - 1.7
            ta = min(u, 1.2)
            objs.append(e_obj('ereb_backstab', ta, pos=BEH, ry=180, key='ereb2', op=lin(u, 0, 0.08)))
            if u < 0.3:
                spr.append(glow(rel([0, 1.1, 0], BEH, 180), 1.6 * (1 - u / 0.3), WHITE, 0.6 * (1 - u / 0.3)))
            spr += glint(rel([0.1, 1.35, -1.6], BEH, 180), u - 0.45, 0.8)
            spr += burst('glow', [VIC[0], 1.3, VIC[2]], u - 0.45, 10, 1.4, (0.06, 0.14), '#ff7070', 304, life=0.4, grav=3)
        cam = camkeys([(0, 30, 10, 8.5, (0, 1.1, -1.8)), (0.9, 45, 10, 8.5, (0, 1.1, -3.0)), (1.6, 85, 10, 7.0, (0, 1.1, -4.8)),
                       (3.4, 95, 10, 7.0, (0, 1.1, -4.8))], t)
        return {'objs': objs, 'sprites': spr, 'cam': cam, 'groundSize': 96,
                'cap': 'Особое: «Ложный союзник»', 'sub': 'ereb_vanish → блик стекла за спиной жертвы (0.7 с) → ereb_backstab: удар в спину',
                'title': {'img': 'title:ereb_false_ally_ru', 'op': tenv(t, 0.2, 2.9)}}
    c.seg(3.4, false_ally)

    # ---------------- «Танец клинков»
    BL = [0.05, 1.15, 2.25, 3.35]
    SPOTS = [(0, 2.4), (100, 2.4), (215, 2.4), (320, 2.4)]   # угол вокруг цели, радиус

    def dance(t):
        T = [0, 0, -3.0]
        i = sum(1 for b in BL if t >= b) - 1
        ang, r = SPOTS[max(0, i)]
        a = math.radians(ang)
        pos = [T[0] + math.sin(a) * r, 0, T[2] + math.cos(a) * r]
        ry = ang
        ta = min(t, 4.4)
        objs = [dict(model='pyromancer', pos=T, ry=180), e_obj('ereb_blade_dance', ta, pos=pos if i >= 0 else [0, 0, 0], ry=ry if i >= 0 else 0)]
        spr = []
        for j, b in enumerate(BL):
            u = t - b
            if j > 0:
                pa, pr = SPOTS[j - 1]
                pp = [T[0] + math.sin(math.radians(pa)) * pr, 1.0, T[2] + math.cos(math.radians(pa)) * pr]
                spr += shards(pp, u, 10, 310 + j, speed=1.3, life=0.5)
                if 0 <= u < 0.25:
                    spr.append(glow(pp, 1.4 * (1 - u / 0.25), GLASS_HI, 0.5 * (1 - u / 0.25)))
            np_ = [T[0] + math.sin(math.radians(SPOTS[j][0])) * SPOTS[j][1], 1.0, T[2] + math.cos(math.radians(SPOTS[j][0])) * SPOTS[j][1]]
            if 0 <= u < 0.25:
                spr.append(glow(np_, 1.6 * (1 - u / 0.25), WHITE, 0.5 * (1 - u / 0.25)))
            spr += glint([T[0], 1.35, T[2]], u - 0.5, 0.7)
        cam = camkeys([(0, 35, 20, 8.8, (0, 1.0, -2.8)), (4.6, 75, 22, 8.8, (0, 1.0, -3.0))], t)
        return {'objs': objs, 'sprites': spr, 'cam': cam, 'groundSize': 96,
                'cap': 'Заклинание: «Танец клинков»', 'sub': 'ereb_blade_dance · 4 шага сквозь рябь (blink) и укол после каждого',
                'title': {'text': '«Танец клинков»', 'op': tenv(t, 0.2, 2.7)}}
    c.seg(4.6, dance)

    # ---------------- «Обманная брешь»
    def feint(t):
        if t < 2.4:
            a, ta, mix = 'ereb_feint', t, None
        else:
            a, ta, mix = 'ereb_feint_counter', min(t - 2.4, 0.9), None
        spr = []
        if 0.3 <= t < 1.8:
            k = lin(t, 0.3, 0.5) * (1 - lin(t, 1.6, 1.8)) * (0.7 + 0.3 * math.sin(t * 8))
            spr.append(glow([0, 1.6, -0.3], 0.6, GLASS_HI, 0.6 * k))
        u = t - 2.4
        spr += glint([0.2, 1.6, -0.6], u - 0.1, 1.0) + shards([0.2, 1.5, -0.7], u - 0.1, 8, 321, speed=1.0, life=0.5)
        spr += glint([0.1, 1.35, -2.2], u - 0.45, 0.7)
        cam = camkeys([(0, 25, 8, 7.6, (0, 1.1, -0.3)), (3.5, 45, 8, 7.6, (0, 1.1, -0.5))], t)
        return {'objs': [e_obj(a, ta, mix)], 'sprites': spr, 'cam': cam, 'groundSize': 96,
                'cap': 'Заклинание: «Обманная брешь»', 'sub': 'ereb_feint · нарочно открыт (окно 0.3–1.8 с) → ereb_feint_counter: парирование и укол',
                'title': {'text': '«Обманная брешь»', 'op': tenv(t, 0.2, 2.7)}}
    c.seg(3.5, feint)

    # ---------------- «Стеклянный дождь»
    MK = [(-2.5, -3.5), (0.6, -4.5), (3.0, -3.0), (-0.8, -6.5)]

    def rain(t):
        ta = min(t, 1.6)
        objs = [e_obj('ereb_glass_rain', ta, mix={'anim': 'ereb_idle', 't': 0, 'k': ease((t - 1.6) / 0.3)} if t >= 1.6 else None)]
        spr = []
        for j, (x, z) in enumerate(MK):
            mk = lin(t, 0.4 + 0.05 * j, 0.6 + 0.05 * j) * (1 - lin(t, 2.0, 2.3))
            spr.append(decal('illusion_seal', [x, 0.04, z], 1.2, GLASS_HI, (0.45 + 0.25 * math.sin(t * 10)) * mk, rot=40 * t))
            for n in range(4):
                tf = t - 1.6 - 0.06 * n - 0.04 * j
                if 0 <= tf < 0.4:
                    ox, oz = math.cos(n * 1.7 + j) * 0.6, math.sin(n * 1.7 + j) * 0.6
                    spr.append({'tex': 'mote_glass', 'at': [x + ox, 6 * (1 - tf / 0.4) + 0.2, z + oz], 'size': 0.5, 'color': GLASS_HI, 'op': 0.95,
                                'rot': 200 * tf + n * 40})
            ti = t - 2.0 - 0.04 * j
            spr += shards([x, 0.2, z], ti, 14, 330 + j, speed=1.8, life=0.6, up=1.0)
            if 0 <= ti < 0.3:
                spr.append(glow([x, 0.4, z], 1.8 * (1 - ti / 0.3), GLASS_HI, 0.6 * (1 - ti / 0.3)))
        cam = camkeys([(0, -35, 26, 11.0, (0, 1.0, -2.2)), (2.9, -45, 28, 11.0, (0, 0.9, -2.6))], t)
        return {'objs': objs, 'sprites': spr, 'cam': cam, 'groundSize': 96,
                'cap': 'Заклинание: «Стеклянный дождь»', 'sub': 'ereb_glass_rain · метки на земле (marks 0.4 с) → осколки сверху (fall 1.6 с)',
                'title': {'text': '«Стеклянный дождь»', 'op': tenv(t, 0.2, 2.7)}}
    c.seg(2.9, rain)

    # ---------------- «Шаг сквозь отражение»
    def mirror(t):
        objs = [dict(model='pyromancer', pos=VIC, ry=180)]
        spr = []
        if t < 0.7:
            objs.append(e_obj('ereb_mirror_step_out', t, op=1 - lin(t, 0.45, 0.55)))
        u = t - 0.5
        if 0 <= u < 0.4:
            spr.append({'tex': 'illusion_seal', 'at': [0, 1.1, 0], 'size': 1.4 + 1.5 * u, 'color': GLASS_HI, 'op': 0.6 * (1 - u / 0.4)})
            spr.append(glow([0, 1.1, 0], 1.4, GLASS_HI, 0.5 * (1 - u / 0.4)))
        spr += shards([0, 1.0, 0], u, 12, 341, speed=1.4)
        tg = t - 0.7
        if 0 <= tg < 0.6:
            k = math.sin(tg / 0.6 * math.pi)
            p = rel([0, 1.45, 0.9], VIC, 180)
            spr.append(glow(p, 1.3 * k, GLASS_HI, 0.9 * k))
        if t >= 1.3:
            w = t - 1.3
            objs.append(e_obj('ereb_mirror_step_in', min(w, 0.8), pos=BEH, ry=180, key='ereb2',
                              mix={'anim': 'ereb_guard', 't': 0, 'k': ease((w - 0.8) / 0.3)} if w >= 0.8 else None))
            if w < 0.3:
                spr.append(glow(rel([0, 1.1, 0], BEH, 180), 1.2 * (1 - w / 0.3), WHITE, 0.5 * (1 - w / 0.3)))
                spr.append({'tex': 'illusion_seal', 'at': rel([0, 1.1, 0], BEH, 180), 'size': 2.2 - 2 * w, 'color': GLASS_HI, 'op': 0.6 * (1 - w / 0.3)})
        cam = camkeys([(0, 30, 10, 8.5, (0, 1.1, -1.8)), (0.8, 45, 10, 8.5, (0, 1.1, -3.0)), (1.4, 85, 10, 7.0, (0, 1.1, -4.8)),
                       (3.0, 95, 10, 7.0, (0, 1.1, -4.8))], t)
        return {'objs': objs, 'sprites': spr, 'cam': cam, 'groundSize': 96,
                'cap': 'Заклинание: «Шаг сквозь отражение»', 'sub': 'ereb_mirror_step_out (gone 0.5 с) → блик за спиной 0.6 с → ereb_mirror_step_in',
                'title': {'text': '«Шаг сквозь отражение»', 'op': tenv(t, 0.2, 2.7)}}
    c.seg(3.0, mirror)
    _fade_joins(c, [3.4, 8.0, 11.5, 14.4])
    return c


def ereb_finale():
    c = Clip('t30_finale', E_TAG)

    def spawn(t):
        spr = [decal('illusion_seal', [0, 0.03, 0], 2.4, GLASS, 0.3 * lin(t, 0, 0.6) * (1 - lin(t, 3.5, 4.5)), rot=12 * t)]
        if t < 2.25:                  # рой собирается: радиус 2.4 → 0.3
            r = 2.4 - 2.1 * ease(lin(t, 0.2, 2.2))
            h = 1.6 + 0.6 * (1 - lin(t, 0.2, 2.2))
            spr += butterflies([0, 1.1, 0], t, 44, r, h, 401, speed=1.4 + 1.6 * lin(t, 0, 2.2), op=0.9 * lin(t, 0, 0.4))
        u = t - 2.2
        if 0 <= u < 0.5:
            spr.append(glow([0, 1.1, 0], 2.2 * (1 - u / 0.5) + 0.3, WHITE, 0.6 * (1 - u / 0.5)))
        spr += shards([0, 1.1, 0], u, 26, 402, speed=2.4, life=0.8, spread=(1.2, 1.0, 1.2))
        spr += bfly_burst([0, 1.2, 0], u, 16, 403, speed=2.2, life=1.3)
        spr += glint([0.3, 2.3, -0.3], t - 3.9, 0.7, GOLD_HI, 0.4)
        ta = min(t, 5.0)
        mix = {'anim': 'ereb_idle', 't': 0, 'k': ease((t - 5.0) / 0.3)} if t >= 5.0 else None
        o = e_obj('ereb_spawn', ta, mix, op=lin(t, 2.2, 2.4))
        cam = camkeys([(0, 40, 14, 6.8, (0, 1.1, 0)), (2.2, 28, 10, 6.0, (0, 1.1, 0)), (3.9, 22, 6, 5.8, (0, 1.2, 0)), (6.2, 18, 6, 6.0, (0, 1.15, 0))], t)
        return {'objs': [o], 'sprites': spr, 'cam': cam, 'groundSize': 96, 'dim': 0.55 + 0.45 * lin(t, 1.8, 2.6),
                'cap': 'Появление', 'sub': 'ereb_spawn · рой стеклянных бабочек собирается в него (form 2.2 с) → поклон → салют рапирой',
                'title': {'img': 'title:ereb_ru', 'op': pulse(t, 3.9, 0.5, 1.0, 0.75)}, 'fade': 0.6 * (1 - lin(t, 0, 0.5))}
    c.seg(6.2, spawn)
    c.seg(0.4, lambda t: dict(spawn(6.2), fade=ease(t / 0.4)))
    SPEECH = 'В любом случае, от вас мне больше нет пользы.'

    def finale(t):
        ta = min(t, 6.5)
        smile = t >= 0.3
        o = e_obj('ereb_finale', ta, key='ereb_smile' if smile else 'ereb', smile=smile, op=1 - lin(t, 5.0, 5.2))
        spr = []
        # бабочка из ладони (1.4) → вспорхнула на «Сон бабочки» (cast 3.2)
        if 1.4 <= t < 3.4:
            u = t - 1.4
            if t < 3.2:
                p = [PALM[0], PALM[1] + 0.12 * math.sin(u * 3), PALM[2]]
            else:
                w = t - 3.2
                p = [PALM[0] - 0.75 * w, PALM[1] + 6 * w, PALM[2] + 1.6 * w]
            sz = 0.34 * min(1, u / 0.25)
            spr.append({'tex': 'mote_butterfly', 'at': p, 'h': sz, 'w': sz * (0.35 + 0.65 * abs(math.cos(u * 9))), 'color': GLASS, 'op': 0.95})
            spr.append(glow(p, 0.7, GLASS_HI, 0.35))
        u = t - 1.4
        if 0 <= u < 0.4:
            spr.append(glow(list(PALM), 0.9 * (1 - u / 0.4) + 0.2, GLASS_HI, 0.6 * (1 - u / 0.4)))
        w = t - 3.2
        if 0 <= w < 0.6:
            spr.append(glow([-0.3, 2.15, -0.2], 1.8 * (1 - w / 0.6) + 0.3, WHITE, 0.75 * (1 - w / 0.6)))
        spr += burst('mote_butterfly', [-0.3, 2.4, -0.2], w, 10, 1.0, (0.2, 0.32), GLASS, 411, life=1.6, up=2.0, flap=True)
        if 3.2 <= t < 6.0:          # «Сон бабочки» (T22) — условно: печать и мерцание
            spr.append(decal('illusion_seal', [0, 0.03, 0], 3.5, GLASS, 0.22 * pulse(t, 3.2, 0.4, 1.8, 0.6), rot=-10 * t))
        v = t - 5.0                   # рассыпается бабочками
        if 0 <= v < 0.4:
            spr.append(glow([0, 1.1, 0], 2.4 * (1 - v / 0.4) + 0.2, GLASS_HI, 0.5 * (1 - v / 0.4)))
        if v >= 0:
            R = rnd(421)
            for i in range(60):
                st = [(R() - 0.5) * 0.8, 0.1 + R() * 1.9, (R() - 0.5) * 0.5]
                ang, sp, ph = R() * 6.28, 0.7 + R() * 1.2, R() * 6.28
                life = 1.6 + R() * 0.8
                if v > life:
                    continue
                p = [st[0] + math.cos(ang) * sp * v, st[1] + 0.9 * v + 0.15 * math.sin(v * 4 + ph), st[2] + math.sin(ang) * sp * v]
                g = i % 3 == 0
                sz = 0.2 + 0.14 * R()
                spr.append({'tex': 'mote_butterfly', 'at': p, 'h': sz, 'w': sz * (0.35 + 0.65 * abs(math.cos(v * 15 + ph))),
                            'color': GOLD_HI if g else GLASS, 'op': 0.9 * (1 - lin(v, life - 0.5, life))})
            spr += shards([0, 1.1, 0], v, 18, 422, speed=1.2, life=0.9, spread=(0.6, 1.0, 0.6))
        cam = camkeys([(0, 20, 4, 3.6, (0, 1.6, 0)), (1.2, 22, 4, 3.8, (0, 1.55, 0)), (2.0, 32, 8, 4.6, (0, 1.4, -0.1)),
                       (3.2, 26, 10, 5.6, (0, 1.35, 0)), (5.0, 22, 10, 6.6, (0, 1.3, 0)), (7.4, 20, 10, 7.0, (0, 1.3, 0))], t)
        sp = pulse(t, 2.4, 0.3, 2.6, 0.5)
        return {'objs': [o], 'sprites': spr, 'cam': cam, 'groundSize': 96,
                'cap': 'Финал', 'sub': 'ereb_finale · улыбка (0.3 с) → бабочка из ладони (1.4) → фраза (2.4) → каст «Сна бабочки» (3.2) → рассыпается (5.0)',
                'speech': {'text': SPEECH, 'op': sp} if sp > 0 else None, 'fade': max(1 - lin(t, 0, 0.4), 0.6 * lin(t, 7.0, 7.4))}
    c.seg(7.4, finale)
    return c


E_TEX = ['glow', 'mote_glass', 'mote_butterfly', 'mote_butterfly_side', 'illusion_seal', 'wave_ring',
         'title:ereb_ru', 'title:ereb_false_ally_ru']
E_PRE = [{'model': 'ereb'}, {'model': 'ereb', 'key': 'ereb_smile', 'smile': True}, {'model': 'ereb', 'key': 'ereb2'}, {'model': 'pyromancer'}]

CLIPS = {
    't29_turntable': ('martin', martin_turntable), 't29_combat': ('martin', martin_combat), 't29_spells': ('martin', martin_spells),
    't29_finale': ('martin', martin_finale),
    't30_turntable': ('ereb', ereb_turntable), 't30_combat': ('ereb', ereb_combat), 't30_spells': ('ereb', ereb_spells), 't30_finale': ('ereb', ereb_finale),
}


def main(args):
    three = args[args.index('--three') + 1] if '--three' in args else None
    names = [a for a in args if a in CLIPS] or list(CLIPS)
    load_anims()
    os.makedirs(TMP, exist_ok=True)
    for n in names:
        kind, fn = CLIPS[n]
        clip = fn()
        render(clip, kind, three, M_TEX if kind == 'martin' else E_TEX, M_PRE if kind == 'martin' else E_PRE)


if __name__ == '__main__':
    main(sys.argv[1:])
