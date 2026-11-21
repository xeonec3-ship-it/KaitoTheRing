#!/usr/bin/env python3
"""
Пилот T29 «Мартин по эталону Epic Fight» (21.11): кадр-лист и видео «старая / новая / эталон» по фазам удара + кадр-листы эталона.
  python3 tools/t29_epicfight_pilot.py [--sheets] [--video] [--three three.min.js]
Нужно: jar эталона (EF_REF_DIR, см. tools/ef_ref.py), Playwright + Chromium, ffmpeg.
Старые анимации — из git (OLD_REV, до пилота). Фазы считаются по метрикам tools/anim_style_check.py (у каждой анимации — свои):
стойка → конец замаха → середина удара → пик (контакт) → перехлёст/удержание → возврат.
Выход: docs/media/t29_epicfight_pilot.jpg, docs/media/video/t29_epicfight_pilot.mp4,
       docs/media/anim_ref_epicfight_heavy.jpg, docs/media/anim_ref_epicfight_thrust_idle.jpg (наши рендеры эталона для изучения).
"""
import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import anim_style_check as C  # noqa: E402
import ef_ref as R  # noqa: E402
import ef_ref_render as ER  # noqa: E402
import martin_render as MR  # noqa: E402

OLD_REV = 'e0ab4cf'          # последний коммит до пилота
ANIM_PATH = 'src/main/resources/assets/pohsmp_core/animations/entity/martin.animation.json'
MEDIA = os.path.join(ROOT, 'docs', 'media')
PAIRS = [   # (наша анимация, эталон, подпись)
    ('martin_swing', 'NF broadblade_auto1', 'Размах справа налево'),
    ('martin_overhead', 'NF ng_great_auto2', 'Рубящий сверху'),
    ('martin_thrust', 'EF mob_spear_twohand3', 'Выпад (укол)'),
    ('martin_shield_bash', None, 'Удар щитом (рывок — кодом)'),
    ('martin_idle', 'NF ng_great_idle', 'Стойка / дыхание'),
]
PHASES = ['стойка', 'конец замаха', 'середина удара', 'пик (контакт)', 'перехлёст / удержание', 'возврат']
K = math.sqrt(2.0)           # эталон показываем замедленным в √2 — как для роста Мартина (см. anim_style_check.normalize)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def font(n):
    for p in (os.path.join(HERE, 'fonts', 'Inter-Regular.ttf'), FONT):
        if os.path.exists(p):
            return ImageFont.truetype(p, n)
    return ImageFont.load_default()


def old_anims():
    raw = subprocess.run(['git', '-C', ROOT, 'show', '%s:%s' % (OLD_REV, ANIM_PATH)], capture_output=True, check=True).stdout
    return json.loads(raw)['animations']


def phase_times(m):
    s0, s1 = m['t_strike']
    rec0 = s1 + m['hold']
    return [0.0, s0, (s0 + m['t_peak']) / 2, m['t_peak'], s1 + max(0.06, m['hold'] * 0.5), rec0 + (m['length'] - rec0) * 0.55]


def our_phase_times(path_or_anims, name):
    tmp = None
    if isinstance(path_or_anims, dict):
        fd, tmp = tempfile.mkstemp(suffix='.json')
        with os.fdopen(fd, 'w') as fh:
            json.dump({'animations': path_or_anims}, fh)
        path_or_anims = tmp
    rig = C.MartinRig(path_or_anims)
    if tmp:
        os.remove(tmp)
    if name == 'martin_idle':
        L = float(rig.an[name]['animation_length'])
        return [L * k / 6 for k in range(6)], L
    ev, cls, weapon = C.MARTIN_ATTACKS[name]
    sig, L = rig.signals(name, weapon)
    th = [t for t, e in rig.events(name).items() if e == ev]
    m = C.metrics(sig, L, (th[0] - 0.3, th[0] + 0.12) if th else None, code_move=C.MARTIN_CODE_MOVE.get(name))
    return phase_times(m), L


def ref_phase_times(jars, key):
    an = ER.load(jars, key)
    if key in R.REF_IDLE:
        return [an.length * k / 6 for k in range(6)], an.length
    win = (an.trail[0][0] - 0.05, an.trail[0][1] + 0.05) if an.trail else None
    m = C.metrics(lambda t: R.ef_signals(jars, an, t), an.length, win)
    return phase_times(m), an.length


# ---------------------------------------------------------------- рендер ячеек
def martin_cells_png(cells, three, size, old):
    d = MR.data(['martin'])
    d['martin_old'] = dict(d['martin'], anims=old)
    fd, out = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    MR.shoot(MR.page(d, cells, three), out, size)
    im = Image.open(out).convert('RGB')
    os.remove(out)
    return im


def ref_cells_png(jars, cells, three, size):
    fd, out = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    ER.shoot(ER.html(jars, cells, three), out, size)
    im = Image.open(out).convert('RGB')
    os.remove(out)
    return im


def slice_grid(im, cols, n, cw, ch):
    return [im.crop(((i % cols) * cw, (i // cols) * ch, (i % cols + 1) * cw, (i // cols + 1) * ch)) for i in range(n)]


VIEW_M = dict(yaw=55, pitch=10, dist=2.5)
VIEW_R = dict(yaw=55, pitch=10, dist=2.5, follow=1)


# ---------------------------------------------------------------- кадр-лист пилота
def pilot_sheet(jars, three, old):
    cw, ch = 300, 330
    rows = []
    for name, ref, title in PAIRS[:3] + PAIRS[4:]:
        to, _ = our_phase_times(old, name)
        tn, _ = our_phase_times(os.path.join(ROOT, ANIM_PATH), name)
        cells = [dict(model='martin_old', anim=name, t=t, **VIEW_M) for t in to] + [dict(model='martin', anim=name, t=t, **VIEW_M) for t in tn]
        im = martin_cells_png({'cols': 6, 'cells': cells}, three, (6 * cw, 2 * ch), old)
        tiles = slice_grid(im, 6, 12, cw, ch)
        rows.append((title + ' — было', to, tiles[:6]))
        rows.append((title + ' — стало', tn, tiles[6:]))
        if ref:
            tr, _ = ref_phase_times(jars, ref)
            blade = 1.0 if 'spear' in ref else 1.4
            rim = ref_cells_png(jars, {'cols': 6, 'cells': [dict(ref=ref, t=t, blade=blade, **VIEW_R) for t in tr]}, three, (6 * cw, ch))
            rows.append(('эталон: ' + ref, tr, slice_grid(rim, 6, 6, cw, ch)))
    lw, hh = 210, 34
    W, H = lw + 6 * cw, hh + len(rows) * ch
    sheet = Image.new('RGB', (W, H), (22, 20, 26))
    dr = ImageDraw.Draw(sheet)
    f1, f2 = font(15), font(13)
    for j, p in enumerate(PHASES):
        dr.text((lw + j * cw + 8, 9), p, fill=(235, 230, 240), font=f1)
    for i, (lab, ts, tiles) in enumerate(rows):
        y = hh + i * ch
        for j, tl in enumerate(tiles):
            sheet.paste(tl, (lw + j * cw, y))
            dr.text((lw + j * cw + 6, y + ch - 20), '%.2f с' % ts[j], fill=(220, 215, 228), font=f2)
        col = (150, 150, 160) if 'было' in lab else ((240, 200, 120) if 'стало' in lab else (140, 190, 255))
        words, line, yy = lab.split(' '), '', y + 10
        for w in words:
            if dr.textlength(line + ' ' + w, font=f1) > lw - 16:
                dr.text((8, yy), line.strip(), fill=col, font=f1)
                yy += 19
                line = ''
            line += ' ' + w
        dr.text((8, yy), line.strip(), fill=col, font=f1)
        if 'эталон' in lab or (i + 1 < len(rows) and 'было' in rows[i + 1][0]):
            dr.line([(0, y + ch - 1), (W, y + ch - 1)], fill=(70, 66, 80), width=2)
    out = os.path.join(MEDIA, 't29_epicfight_pilot.jpg')
    sheet.save(out, quality=88)
    print('wrote', out, sheet.size)


# ---------------------------------------------------------------- кадр-листы эталона (для изучения)
REF_SHEETS = {
    'anim_ref_epicfight_heavy.jpg': ['EF greatsword_auto1', 'NF broadblade_auto1', 'NF ng_great_auto2', 'WoM ruine_auto_1', 'WoM torment_auto_2'],
    'anim_ref_epicfight_thrust_idle.jpg': ['EF mob_spear_twohand3', 'WoM moonless_auto_3', 'NF ng_great_idle', 'EF hold_greatsword'],
}


def ref_sheets(jars, three):
    cw, ch = 280, 300
    for fn, keys in REF_SHEETS.items():
        cells, times = [], []
        for k in keys:
            ts, _ = ref_phase_times(jars, k)
            times.append(ts)
            blade = 1.0 if ('spear' in k or 'moonless' in k) else 1.4
            cells += [dict(ref=k, t=t, blade=blade, **VIEW_R) for t in ts]
        im = ref_cells_png(jars, {'cols': 6, 'cells': cells}, three, (6 * cw, len(keys) * ch))
        lw, hh = 200, 34
        sheet = Image.new('RGB', (lw + 6 * cw, hh + len(keys) * ch), (22, 20, 26))
        dr = ImageDraw.Draw(sheet)
        f1, f2 = font(15), font(13)
        for j, p in enumerate(PHASES):
            dr.text((lw + j * cw + 8, 9), p if 'idle' not in fn else p, fill=(235, 230, 240), font=f1)
        tiles = slice_grid(im, 6, 6 * len(keys), cw, ch)
        for i, k in enumerate(keys):
            y = hh + i * ch
            for j in range(6):
                sheet.paste(tiles[i * 6 + j], (lw + j * cw, y))
                dr.text((lw + j * cw + 6, y + ch - 20), '%.2f с' % times[i][j], fill=(220, 215, 228), font=f2)
            dr.text((8, y + 10), 'эталон:', fill=(140, 190, 255), font=f1)
            dr.text((8, y + 30), k, fill=(140, 190, 255), font=f1)
            if k in R.REF_IDLE:
                dr.text((8, y + 52), '(стойка: 6 равных долей петли)', fill=(160, 160, 170), font=f2)
        out = os.path.join(MEDIA, fn)
        sheet.save(out, quality=86)
        print('wrote', out, sheet.size)


# ---------------------------------------------------------------- видео: старое | новое | эталон
def video(jars, three):
    old = old_anims()
    FPS, CW, CH = 30, 420, 560
    PAUSE = 0.5
    segs = []
    for name, ref, title in PAIRS:
        Lo = float(old[name]['animation_length'])
        Ln = float(json.load(open(os.path.join(ROOT, ANIM_PATH)))['animations'][name]['animation_length'])
        Lr = ER.load(jars, ref).length * K if ref else 0.0
        reps = 2 if name == 'martin_idle' else 1
        T = max(Lo, Ln, Lr) * reps + PAUSE
        segs.append((name, ref, title, Lo, Ln, Lr, T, reps))
    frames_m_old, frames_m_new, frames_r = [], [], []
    for name, ref, title, Lo, Ln, Lr, T, reps in segs:
        n = int(round(T * FPS))
        for i in range(n):
            t = i / FPS
            loop = name == 'martin_idle'
            frames_m_old.append(dict(model='martin_old', anim=name, t=(t % Lo) if loop else min(t, Lo), **VIEW_M))
            frames_m_new.append(dict(model='martin', anim=name, t=(t % Ln) if loop else min(t, Ln), **VIEW_M))
            if ref:
                tr = (t % Lr) / K if loop else min(t, Lr) / K
                frames_r.append(dict(ref=ref, t=tr, blade=1.0 if 'spear' in ref else 1.4, **VIEW_R))
            else:
                frames_r.append(None)
    cols, rows = 8, 4
    per = cols * rows

    def render_all(cells, fn):
        out = []
        for k in range(0, len(cells), per):
            chunk = cells[k:k + per]
            real = [c for c in chunk if c]
            if not real:
                out += [None] * len(chunk)
                continue
            im = fn({'cols': cols, 'cells': real}, (cols * CW, rows * CH))
            tiles = iter(slice_grid(im, cols, len(real), CW, CH))
            out += [next(tiles) if c else None for c in chunk]
            print('  %d/%d' % (min(k + per, len(cells)), len(cells)), flush=True)
        return out
    to = render_all(frames_m_old, lambda c, s: martin_cells_png(c, three, s, old))
    tn = render_all(frames_m_new, lambda c, s: martin_cells_png(c, three, s, old))
    tr = render_all(frames_r, lambda c, s: ref_cells_png(jars, c, three, s))
    W, H = 1280, 720
    f1, f2, f3 = font(24), font(17), font(15)
    out = os.path.join(MEDIA, 'video', 't29_epicfight_pilot.mp4')
    fd, tmp = tempfile.mkstemp(suffix='.mp4')
    os.close(fd)
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(FPS), '-c:v', 'mjpeg', '-i', '-',
                           '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmp],
                          stdin=subprocess.PIPE)
    i = 0
    for name, ref, title, Lo, Ln, Lr, T, reps in segs:
        n = int(round(T * FPS))
        for k in range(n):
            fr = Image.new('RGB', (W, H), (18, 16, 22))
            dr = ImageDraw.Draw(fr)
            dr.text((20, 12), 'T29 Мартин — %s' % title, fill=(240, 236, 245), font=f1)
            dr.text((20, 46), 't = %.2f с' % (k / FPS), fill=(180, 175, 190), font=f3)
            x0 = (W - 3 * CW - 2 * 10) // 2
            for j, (tile, lab, col) in enumerate(((to[i], 'было (%.1f с)' % Lo, (160, 160, 170)), (tn[i], 'стало (%.1f с)' % Ln, (240, 200, 120)),
                                                  (tr[i], ('эталон %s (×√2 медленнее)' % ref) if ref else 'эталона со щитом нет', (140, 190, 255)))):
                x = x0 + j * (CW + 10)
                if tile is not None:
                    fr.paste(tile, (x, 120))
                else:
                    dr.rectangle([x, 120, x + CW, 120 + CH], fill=(30, 28, 34))
                dr.text((x + 6, 92), lab, fill=col, font=f2 if len(lab) < 40 else f3)
            buf = io.BytesIO()
            fr.save(buf, 'JPEG', quality=92)
            ff.stdin.write(buf.getvalue())
            i += 1
    ff.stdin.close()
    ff.wait()
    os.makedirs(os.path.dirname(out), exist_ok=True)
    shutil.move(tmp, out)
    print('wrote', out, i, 'frames')


if __name__ == '__main__':
    a = sys.argv[1:]
    three = a[a.index('--three') + 1] if '--three' in a else None
    jars = R.find_jars()
    if '--sheets' in a:
        ref_sheets(jars, three)
        pilot_sheet(jars, three, old_anims())
    if '--video' in a:
        video(jars, three)
