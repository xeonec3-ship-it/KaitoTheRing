#!/usr/bin/env python3
"""
Перенос анимаций боссов на эталон Epic Fight (21.11): кадр-лист и видео «было / стало / эталон» по фазам удара — для любого босса
из BOSSES (T29 Мартин — tools/t29_epicfight_pilot.py, тот же формат).
  python3 tools/anim_pilot.py aris [--sheet] [--video] [--three three.min.js]
Нужно: jar эталона (EF_REF_DIR, tools/ef_ref.py), Playwright + Chromium, ffmpeg. «Было» — анимации из git (old_rev босса).
Выход: docs/media/<tag>_epicfight.jpg, docs/media/video/<tag>_epicfight.mp4.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import anim_style_check as C  # noqa: E402
import ef_ref as R  # noqa: E402
import ef_ref_render as ER  # noqa: E402
from t29_epicfight_pilot import PHASES, K, font, slice_grid, ref_cells_png, phase_times, ref_phase_times  # noqa: E402

MEDIA = os.path.join(ROOT, 'docs', 'media')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')


# ---------------------------------------------------------------- Арис (T28): превью tools/aris_preview.template.html
def aris_render(cells, size, old):
    import aris_render as AR
    d = AR.data()
    d['anims'].update({'old.' + k: v for k, v in old.items()})
    with open(os.path.join(HERE, 'aris_preview.template.html'), encoding='utf-8') as fh:
        html = fh.read()
    html = html.replace('/*DATA*/null', json.dumps(d, ensure_ascii=False, separators=(',', ':')))
    html = html.replace('/*CELLS*/null', json.dumps(cells, ensure_ascii=False))
    three = os.environ.get('THREE_JS')
    if three:
        html = html.replace(AR.CDN, 'file://' + os.path.abspath(three))
    fd, out = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    AR.shoot(html, out, size)
    im = Image.open(out).convert('RGB')
    os.remove(out)
    return im


# ---------------------------------------------------------------- Ирина (T27): превью tools/irina_preview.template.html (ткань — irina_cloth_idle)
def irina_render(cells, size, old):
    import irina_render as IR
    d = IR.data()
    d['anims'].update({'old.' + k: v for k, v in old.items()})
    html = open(os.path.join(HERE, 'irina_preview.template.html'), encoding='utf-8').read()
    html = html.replace('/*DATA*/null', json.dumps(d, ensure_ascii=False, separators=(',', ':')))
    html = html.replace('/*CELLS*/null', json.dumps(cells, ensure_ascii=False))
    three = os.environ.get('THREE_JS')
    if three:
        html = html.replace(IR.CDN, 'file://' + os.path.abspath(three))
    fd, out = tempfile.mkstemp(suffix='.png')
    os.close(fd)
    IR.shoot(html, out, size)
    im = Image.open(out).convert('RGB')
    os.remove(out)
    return im


# ---------------------------------------------------------------- Эреб (T30) и Длань Лжи (T31): превью gen_ereb_render / gen_ereb_hand_render
def geo_render(modname, model):
    def render(cells, size, old):
        import importlib
        M = importlib.import_module(modname)
        orig = M.anims
        M.anims = lambda: dict(orig(), **{'old.' + k: v for k, v in old.items()})
        try:
            html = M.page([model], cells, os.environ.get('THREE_JS'))
        finally:
            M.anims = orig
        fd, out = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        M.CR.shoot(html, out, size)
        im = Image.open(out).convert('RGB')
        os.remove(out)
        return im
    return render


# ---------------------------------------------------------------- игрок (T14, Epic Fight): наши анимации — тем же проигрывателем, что эталон
EMBER = os.path.join(A, 'animmodels', 'animations', 'biped', 'ember')


def player_render(jars, three, old_dir):
    def render(cells, size, old):
        cs = []
        for c in cells['cells']:
            name = c['anim'].split('.')[-1]
            path = os.path.join(old_dir if c['anim'].startswith('old.') else EMBER, name + '.json')
            cs.append(dict(c, ref='file:' + path, blade=1.0))
        return ref_cells_png(jars, {'cols': cells['cols'], 'cells': cs}, three, size)
    return render


BOSSES = {
    'aris': dict(tag='t28', title='T28 Арис', old_rev='82eaf87', path='animations/entity/aris.animation.json', prefix='animation.aris.',
                 render=aris_render, model='aris',
                 pairs=[('swing', 'EF greatsword_auto1', 'Размах молотом справа налево'), ('slam', 'NF ng_great_auto2', 'Удар молотом в землю'),
                        ('idle', 'EF hold_greatsword', 'Стойка / дыхание')]),
    'ereb': dict(tag='t30', title='T30 Эреб', old_rev='4220558', path='animations/entity/ereb.animation.json', prefix='ereb_',
                 render=geo_render('gen_ereb_render', 'ereb'), model='ereb',
                 pairs=[('lunge', 'EF mob_spear_twohand3', 'Выпад рапирой'), ('flurry', 'EF spear_onehand_auto', 'Серия из трёх уколов'),
                        ('idle', 'NF broadblade_idle', 'Стойка / дыхание')]),
    'ereb_hand': dict(tag='t31', title='T31 Эреб, Длань Лжи', old_rev='4220558', path='animations/entity/ereb_hand.animation.json',
                      prefix='ereb_hand_', render=geo_render('gen_ereb_hand_render', 'ereb_hand'), model='ereb_hand',
                      pairs=[('lunge', 'EF mob_spear_twohand3', 'Выпад рапирой'), ('flurry', 'EF spear_onehand_auto', 'Серия из трёх уколов'),
                             ('slam', 'NF ng_great_auto2', 'Удар призрачной ладонью о землю')]),
    'player': dict(tag='player', title='Игрок: меч-хлыст T14', old_rev=None, path=None, prefix='', model='player',
                   pairs=[('whip1', 'EF longsword_auto1', 'Хлёст справа налево'), ('sword1', 'EF longsword_auto2', 'Разрез мечом'),
                          ('whip_idle', 'EF hold_longsword', 'Стойка с хлыстом')]),
    'irina': dict(tag='t27', title='T27 Ирина', old_rev='dab42e3', path='animations/entity/irina.animation.json', prefix='irina_',
                  render=irina_render, model='irina',
                  pairs=[('staff_attack', 'NF ng_great_auto2', 'Удар крюком посоха сверху'),
                         ('staff_sweep', 'EF greatsword_auto1', 'Взмах посохом справа налево'),
                         ('idle', 'NF ng_great_idle', 'Стойка / дыхание')]),
}
VIEW = dict(yaw=55, pitch=10, dist=2.5)
VIEW_R = dict(yaw=55, pitch=10, dist=2.5, follow=1)
VID = dict(yaw=55, pitch=10, dist=3.4)
VID_R = dict(yaw=55, pitch=10, dist=3.6, follow=1)


def anims_of(B, rev=None):
    if rev:
        raw = subprocess.run(['git', '-C', ROOT, 'show', '%s:src/main/resources/assets/pohsmp_core/%s' % (rev, B['path'])],
                             capture_output=True, check=True).stdout
        return json.loads(raw)['animations']
    return json.load(open(os.path.join(A, B['path']), encoding='utf-8'))['animations']


def our_phases(boss, anims, name):
    B = BOSSES[boss]
    fd, tmp = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as fh:
        json.dump({'animations': anims}, fh)
    rig = C.BOSSES[boss]['rig'](tmp)
    os.remove(tmp)
    full = B['prefix'] + name
    L = float(anims[full]['animation_length'])
    att = C.BOSSES[boss]['attacks']
    if name not in att:
        return [L * k / 6 for k in range(6)], L
    ev, cls, weapon = att[name]
    sig, L = rig.signals(name, weapon)
    th = [t for t, e in rig.events(name).items() if e == ev]
    m = C.metrics(sig, L, (th[0] - 0.3, th[0] + 0.12) if th else None)
    return phase_times(m), L


def cell(B, name, t, old, view):
    return dict(model=B['model'], anim=('old.' if old else '') + B['prefix'] + name, t=t, **view)


def sheet(boss, jars, three):
    B = BOSSES[boss]
    old, new = anims_of(B, B['old_rev']), anims_of(B)
    cw, ch = 300, 330
    rows = []
    for name, ref, title in B['pairs']:
        to, _ = our_phases(boss, old, name)
        tn, _ = our_phases(boss, new, name)
        cells = [cell(B, name, t, True, VIEW) for t in to] + [cell(B, name, t, False, VIEW) for t in tn]
        tiles = slice_grid(B['render']({'cols': 6, 'cells': cells}, (6 * cw, 2 * ch), old), 6, 12, cw, ch)
        rows.append((title + ' — было', to, tiles[:6]))
        rows.append((title + ' — стало', tn, tiles[6:]))
        tr, _ = ref_phase_times(jars, ref)
        rim = ref_cells_png(jars, {'cols': 6, 'cells': [dict(ref=ref, t=t, blade=1.4, **VIEW_R) for t in tr]}, three, (6 * cw, ch))
        rows.append(('эталон: ' + ref, tr, slice_grid(rim, 6, 6, cw, ch)))
    lw, hh = 210, 34
    W, H = lw + 6 * cw, hh + len(rows) * ch
    im = Image.new('RGB', (W, H), (22, 20, 26))
    dr = ImageDraw.Draw(im)
    f1, f2 = font(15), font(13)
    for j, p in enumerate(PHASES):
        dr.text((lw + j * cw + 8, 9), p, fill=(235, 230, 240), font=f1)
    for i, (lab, ts, tiles) in enumerate(rows):
        y = hh + i * ch
        for j, tl in enumerate(tiles):
            im.paste(tl, (lw + j * cw, y))
            dr.text((lw + j * cw + 6, y + ch - 20), '%.2f с' % ts[j], fill=(220, 215, 228), font=f2)
        col = (150, 150, 160) if 'было' in lab else ((240, 200, 120) if 'стало' in lab else (140, 190, 255))
        line, yy = '', y + 10
        for w in lab.split(' '):
            if dr.textlength(line + ' ' + w, font=f1) > lw - 16:
                dr.text((8, yy), line.strip(), fill=col, font=f1)
                yy += 19
                line = ''
            line += ' ' + w
        dr.text((8, yy), line.strip(), fill=col, font=f1)
        if 'эталон' in lab:
            dr.line([(0, y + ch - 1), (W, y + ch - 1)], fill=(70, 66, 80), width=2)
    out = os.path.join(MEDIA, '%s_epicfight.jpg' % B['tag'])
    im.save(out, quality=88)
    print('wrote', out, im.size)


def video(boss, jars, three):
    B = BOSSES[boss]
    old, new = anims_of(B, B['old_rev']), anims_of(B)
    FPS, CW, CH, PAUSE = 30, 420, 560, 0.5
    segs, fo, fn, fr = [], [], [], []
    for name, ref, title in B['pairs']:
        Lo, Ln = float(old[B['prefix'] + name]['animation_length']), float(new[B['prefix'] + name]['animation_length'])
        Lr = ER.load(jars, ref).length * K
        loop = name == 'idle'
        T = max(Lo, Ln, Lr) * (2 if loop else 1) + PAUSE
        segs.append((name, ref, title, Lo, Ln, T))
        for i in range(int(round(T * FPS))):
            t = i / FPS
            fo.append(cell(B, name, (t % Lo) if loop else min(t, Lo), True, VID))
            fn.append(cell(B, name, (t % Ln) if loop else min(t, Ln), False, VID))
            fr.append(dict(ref=ref, t=((t % Lr) if loop else min(t, Lr)) / K, blade=1.4, **VID_R))
    cols, rows = 8, 4

    def render_all(cells, fn_):
        out = []
        for k in range(0, len(cells), cols * rows):
            chunk = cells[k:k + cols * rows]
            out += slice_grid(fn_({'cols': cols, 'cells': chunk}, (cols * CW, rows * CH)), cols, len(chunk), CW, CH)
            print('  %d/%d' % (min(k + cols * rows, len(cells)), len(cells)), flush=True)
        return out
    to = render_all(fo, lambda c, s: B['render'](c, s, old))
    tn = render_all(fn, lambda c, s: B['render'](c, s, old))
    tr = render_all(fr, lambda c, s: ref_cells_png(jars, c, three, s))
    W, H = 1280, 720
    f1, f2, f3 = font(24), font(17), font(15)
    out = os.path.join(MEDIA, 'video', '%s_epicfight.mp4' % B['tag'])
    fd, tmp = tempfile.mkstemp(suffix='.mp4')
    os.close(fd)
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(FPS), '-c:v', 'mjpeg', '-i', '-',
                           '-an', '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmp],
                          stdin=subprocess.PIPE)
    i = 0
    for name, ref, title, Lo, Ln, T in segs:
        for k in range(int(round(T * FPS))):
            frm = Image.new('RGB', (W, H), (18, 16, 22))
            dr = ImageDraw.Draw(frm)
            dr.text((20, 12), '%s — %s' % (B['title'], title), fill=(240, 236, 245), font=f1)
            dr.text((20, 46), 't = %.2f с' % (k / FPS), fill=(180, 175, 190), font=f3)
            x0 = (W - 3 * CW - 20) // 2
            for j, (tile, lab, col) in enumerate(((to[i], 'было (%.1f с)' % Lo, (160, 160, 170)), (tn[i], 'стало (%.1f с)' % Ln, (240, 200, 120)),
                                                  (tr[i], 'эталон %s (×√2 медленнее)' % ref, (140, 190, 255)))):
                x = x0 + j * (CW + 10)
                frm.paste(tile, (x, 120))
                dr.text((x + 6, 92), lab, fill=col, font=f2 if len(lab) < 40 else f3)
            buf = io.BytesIO()
            frm.save(buf, 'JPEG', quality=92)
            ff.stdin.write(buf.getvalue())
            i += 1
    ff.stdin.close()
    ff.wait()
    shutil.move(tmp, out)
    os.chmod(out, 0o644)
    print('wrote', out, i, 'frames')


def player_old_dir(rev='HEAD'):
    """Анимации меча-хлыста игрока из git (rev) во временную папку — «было»."""
    d = tempfile.mkdtemp(prefix='ember_old_')
    rel = 'src/main/resources/assets/pohsmp_core/animmodels/animations/biped/ember'
    names = subprocess.run(['git', '-C', ROOT, 'ls-tree', '--name-only', '%s:%s' % (rev, rel)], capture_output=True, text=True, check=True).stdout
    for n in names.split():
        if n.endswith('.json'):
            open(os.path.join(d, n), 'wb').write(subprocess.run(['git', '-C', ROOT, 'show', '%s:%s/%s' % (rev, rel, n)],
                                                                capture_output=True, check=True).stdout)
    return d


def player_phases(dirpath, name):
    rig = C.PlayerEFRig(dirpath)
    a = rig.anim(name)
    if name not in C.BOSSES['player']['attacks']:
        return [a.length * k / 6 for k in range(6)], a.length
    ev = rig.events(name)
    th = list(ev)
    sig, L = rig.signals(name)
    return phase_times(C.metrics(sig, L, (th[0] - 0.3, th[0] + 0.12) if th else None)), L


def player_media(jars, three, rev='HEAD', video_too=False):
    B = BOSSES['player']
    old_dir = player_old_dir(rev)
    cw, ch = 300, 330
    rows = []
    for name, ref, title in B['pairs']:
        to, _ = player_phases(old_dir, name)
        tn, _ = player_phases(EMBER, name)
        cells = [dict(ref='file:' + os.path.join(old_dir, name + '.json'), t=t, blade=1.0, **VIEW_R) for t in to] + \
                [dict(ref='file:' + os.path.join(EMBER, name + '.json'), t=t, blade=1.0, **VIEW_R) for t in tn]
        tiles = slice_grid(ref_cells_png(jars, {'cols': 6, 'cells': cells}, three, (6 * cw, 2 * ch)), 6, 12, cw, ch)
        rows.append((title + ' — было', to, tiles[:6]))
        rows.append((title + ' — стало', tn, tiles[6:]))
        tr, _ = ref_phase_times(jars, ref)
        rim = ref_cells_png(jars, {'cols': 6, 'cells': [dict(ref=ref, t=t, blade=1.0, **VIEW_R) for t in tr]}, three, (6 * cw, ch))
        rows.append(('эталон: ' + ref, tr, slice_grid(rim, 6, 6, cw, ch)))
    lw, hh = 210, 34
    W, H = lw + 6 * cw, hh + len(rows) * ch
    im = Image.new('RGB', (W, H), (22, 20, 26))
    dr = ImageDraw.Draw(im)
    f1, f2 = font(15), font(13)
    for j, p in enumerate(PHASES):
        dr.text((lw + j * cw + 8, 9), p, fill=(235, 230, 240), font=f1)
    for i, (lab, ts, tiles) in enumerate(rows):
        y = hh + i * ch
        for j, tl in enumerate(tiles):
            im.paste(tl, (lw + j * cw, y))
            dr.text((lw + j * cw + 6, y + ch - 20), '%.2f с' % ts[j], fill=(220, 215, 228), font=f2)
        col = (150, 150, 160) if 'было' in lab else ((240, 200, 120) if 'стало' in lab else (140, 190, 255))
        line, yy = '', y + 10
        for w in lab.split(' '):
            if dr.textlength(line + ' ' + w, font=f1) > lw - 16:
                dr.text((8, yy), line.strip(), fill=col, font=f1)
                yy += 19
                line = ''
            line += ' ' + w
        dr.text((8, yy), line.strip(), fill=col, font=f1)
    out = os.path.join(MEDIA, 'player_epicfight.jpg')
    im.save(out, quality=88)
    print('wrote', out, im.size)


if __name__ == '__main__':
    a = sys.argv[1:]
    boss = a[0]
    three = a[a.index('--three') + 1] if '--three' in a else None
    if three:
        os.environ['THREE_JS'] = three
    jars = R.find_jars()
    if boss == 'player':
        player_media(jars, three)
        sys.exit(0)
    if '--sheet' in a:
        sheet(boss, jars, three)
    if '--video' in a:
        video(boss, jars, three)
