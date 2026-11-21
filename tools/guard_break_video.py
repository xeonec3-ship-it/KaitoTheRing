#!/usr/bin/env python3
"""
T32 «Сломать блок»: видео и кадр-лист шести боссов с fx и манекеном в блоке.
  python3 tools/guard_break_video.py [--three путь/three.min.js] [cult_leader irina aris martin ereb ereb_hand] [--sheet-only]
Выход: docs/media/video/t32_guard_break.mp4 (1280×720, 30 fps) и docs/media/t32_guard_break.jpg (6 боссов × 4 фазы).

Страница — как tools/boss_video.py: движок fx превью эффектов (tools/sigil_preview.template.html — те же fx/*.json, что в игре)
+ код модели из шаблона превью босса (tools/*_preview.template.html), модели/анимации/текстуры из assets как есть.
Манекен — Стив (каркас abstract_casting_mob, масштаб игрока 0.9375) в блоке: руки скрещены перед собой; на тике удара блок
ломается — руки разбрасывает, корпус откидывает, оглушение (как guard break EF, 1.2 с).
fx <boss>_guard_break стартует на тике 0 анимации (так его играет BossGuardBreak), caster — босс, target — манекен.
Раскадровка босса: стойка → удар в реальном времени → замедленный повтор (×0.35, fx тоже замедлены) → возврат.
"""
import json
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import boss_video as BV  # noqa: E402

A = BV.A
OUT = os.path.join(ROOT, 'docs', 'media', 'video')
MEDIA = os.path.join(ROOT, 'docs', 'media')
FPS, W, H = 30, 1280, 720
HIT, WARN = 0.70, 0.10
SLOW = 0.35

# босс: (подпись, анимация, ключ страницы, масштаб модели, рост в px модели для камеры, вид удара)
BOSSES = {
    'cult_leader': ('Глава Культа', 'cult_leader_guard_break', 'tyros', 1.75, 36, 'коса цепляет защиту крюком, рвёт в сторону, удар древком'),
    'irina': ('Ирина', 'irina_guard_break', 'irina', 1.0, 52, 'нити обвивают защиту и раздёргивают её, удар посохом'),
    'aris': ('Арис', 'animation.aris.guard_break', 'aris', 1.0, 40, 'двуручный удар молотом сверху по блоку'),
    'martin': ('Мартин', 'martin_guard_break', 'martin', 2.0, 33, 'удар навершием в блок, затем щитом'),
    'ereb': ('Эреб', 'ereb_guard_break', 'ereb', 1.0, 34, 'ложный финт рапирой, укол под защиту'),
    'ereb_hand': ('«Эреб, Длань Лжи»', 'ereb_hand_guard_break', 'ereb_hand', 1.0, 34, 'призрачная рука отводит защиту, укол рапирой'),
}
PHASES = [('вспышка', 0.25), ('замах', 0.58), ('удар', HIT), ('возврат', 1.25)]


# ---------------------------------------------------------------- манекен: анимации Стива (GeckoLib JSON, каркас Iron's)
def dummy_anims():
    blk = {'right_arm': [-100, -38, 0], 'left_arm': [-100, 38, 0], 'body': [6, 0, 0], 'head': [10, 0, 0],
           'right_leg': [-14, 0, 2], 'left_leg': [12, 0, -2]}

    def anim(keys, length, loop=False):
        bones = {}
        for t, p, e in keys:
            for b, v in p.items():
                ch = bones.setdefault(b, {}).setdefault('position' if b.endswith('_pos') else 'rotation', {})
                k = {'vector': v}
                if e and t > 0:
                    k['easing'] = e
                ch['%g' % t if t else '0.0'] = k
        bones = {b[:-4] if b.endswith('_pos') else b: v for b, v in bones.items()}
        return {'animation_length': length, 'loop': loop, 'bones': bones}
    fling = {'right_arm': [-150, -10, 40], 'left_arm': [-150, 10, -40], 'body': [-16, 0, 0], 'head': [-18, 0, 0],
             'right_leg': [-4, 0, 4], 'left_leg': [18, 0, -4]}
    slump = {'right_arm': [-10, 0, 14], 'left_arm': [-6, 0, -16], 'body': [22, 0, 0], 'head': [26, 6, 0],
             'right_leg': [-22, 0, 4], 'left_leg': [14, 0, -4]}
    return {
        'dummy_block': anim([(0, blk, None), (1.0, dict(blk, body=[7, 0, 0]), 'easeInOutSine'), (2.0, blk, 'easeInOutSine')], 2.0, True),
        # сломанный блок: 0 — удар (руки разбрасывает), 0.25 — откинут, 0.6–1.4 — оглушён (поникший), 1.8 — снова в стойку
        'dummy_broken': anim([(0, blk, None), (0.1, fling, 'easeOutQuart'), (0.3, dict(fling, body=[-10, 0, 0]), 'easeOutCubic'),
                              (0.6, slump, 'easeInOutSine'), (1.3, dict(slump, head=[30, -6, 0]), 'easeInOutSine'),
                              (1.8, blk, 'easeInOutSine')], 1.8, 'hold_on_last_frame'),
    }


def strike_point(boss):
    """Точка удара в момент hit (px модели, R-мир) — туда ставим манекен."""
    import guard_break_check as GC
    name = BOSSES[boss][1]
    if boss == 'martin':
        sig, _, _ = GC.martin_sig(name)
        return [x * 12.0 for x in sig(HIT)['tip']]
    import guard_break_lib as GL
    M = GL.model(boss)
    W = M.world(M.anims[name], HIT)
    return list(M.strike_pts(W)[1])


# ---------------------------------------------------------------- страница
def boss_lib(boss, names):
    key = BOSSES[boss][2]
    if key in ('tyros', 'irina', 'aris'):
        src = BV.boss_lib(key)                     # данные целиком (анимации — как в assets)
        return src
    if key == 'martin':
        import martin_render as MR
        d = MR.data(['martin'])
        d['martin']['anims'] = {k: v for k, v in d['martin']['anims'].items() if k in names}
        data = {'models': {'martin': d['martin']}, 'anims': d['martin']['anims']}
        tpl = 'martin_preview.template.html'
    elif key == 'ereb':
        import gen_ereb_render as ER
        an = ER.anims()
        data = {'models': {'ereb': ER.model_entry('ereb')}, 'anims': {k: v for k, v in an.items() if k in names}}
        tpl = 'ereb_preview.template.html'
    else:
        import gen_ereb_hand_render as HR
        an = HR.anims()
        data = {'models': {'ereb_hand': HR.model_entry('ereb_hand')}, 'anims': {k: v for k, v in an.items() if k in names}}
        tpl = 'ereb_hand_preview.template.html'
    src = open(os.path.join(HERE, tpl), encoding='utf-8').read()
    i0 = src.index('const DATA = /*DATA*/null;')
    i1 = src.index('const renderer')
    code = src[i0:i1].replace('const DATA = /*DATA*/null;', 'const DATA = %s;' % json.dumps(data, ensure_ascii=False, separators=(',', ':')), 1)
    for k in ('const CELLS = /*CELLS*/null;', 'const MESHES = /*MESHES*/null;', 'const TEXS = /*TEXS*/null;'):
        code = code.replace(k, k.split('=')[0] + '= null;')
    names_js = ['buildModel', 'pose', 'flameFrame']
    ret = ', '.join('%s: typeof %s === "undefined" ? null : %s' % (n, n, n) for n in names_js)
    return '<script>\nconst BL = (() => {\n%s\nreturn { DATA, %s };\n})();\n</script>\n' % (code, ret)


def adapter():
    js = BV.ADAPTER
    old_boss = """      if (CFG.boss === 'tyros') { m = BL.buildModel(BL.DATA.models.cult_leader, a.v === 'soul'); attachItem(m, CFG.scythe); }
      else if (CFG.boss === 'irina') { m = BL.buildModel(); BL.attachStaff(m); }
      else m = BL.buildModel(BL.DATA.models.aris, a.v || 'base');"""
    new_boss = """      if (CFG.boss === 'tyros') { m = BL.buildModel(BL.DATA.models.cult_leader, a.v === 'soul'); attachItem(m, CFG.scythe); }
      else if (CFG.boss === 'irina') { m = BL.buildModel(); BL.attachStaff(m); }
      else if (CFG.boss === 'aris') m = BL.buildModel(BL.DATA.models.aris, a.v || 'base');
      else m = BL.buildModel(BL.DATA.models[CFG.boss]);"""
    assert old_boss in js
    js = js.replace(old_boss, new_boss)
    old_pose = """    if (CFG.boss === 'tyros') BL.pose(m, an, t);
    else if (CFG.boss === 'irina') BL.pose(m, an, a.k === 'boss' ? AN(p.cloth || 'irina_cloth_idle') : null, t, p.tc);
    else BL.pose(m, an, t, p.hide);"""
    new_pose = """    if (CFG.boss === 'irina') BL.pose(m, an, a.k === 'boss' ? AN(p.cloth || 'irina_cloth_idle') : null, t, p.tc);
    else if (CFG.boss === 'aris') BL.pose(m, an, t, p.hide);
    else BL.pose(m, an, t);"""
    assert old_pose in js
    js = js.replace(old_pose, new_pose)
    # Ирина: превью (irina_preview.template.html) рисует посох с ОДНИМ поворотом кисти, GeckoLib — с двумя: оборачиваем посох группой
    # с поворотом кисти (как h2 в превью Эреба/Длани), поворот копируется каждый кадр
    old_irina = "else if (CFG.boss === 'irina') { m = BL.buildModel(); BL.attachStaff(m); }"
    assert old_irina in js
    js = js.replace(old_irina, "else if (CFG.boss === 'irina') { m = BL.buildModel(); BL.attachStaff(m); const hh = m.bones.bipedHandRight; "
                    "const st = hh.children.find(o => o.userData.staff); if (st) { const h2 = new THREE.Group(); hh.remove(st); h2.add(st); hh.add(h2); m.irinaH2 = h2; } }")
    old_pose_i = "    if (CFG.boss === 'irina') BL.pose(m, an, a.k === 'boss' ? AN(p.cloth || 'irina_cloth_idle') : null, t, p.tc);"
    assert old_pose_i in js
    js = js.replace(old_pose_i, "    if (CFG.boss === 'irina') { BL.pose(m, an, a.k === 'boss' ? AN(p.cloth || 'irina_cloth_idle') : null, t, p.tc); "
                    "if (m.irinaH2) m.irinaH2.quaternion.copy(m.bones.bipedHandRight.quaternion); }")
    old_an = "const AN = n => n ? (BL.DATA.anims[n] || VANIMS[n] || null) : null;"
    assert old_an in js
    js = js.replace(old_an, "const AN = n => n ? ((BL.DATA.anims && BL.DATA.anims[n]) || VANIMS[n] || null) : null;")
    old_tick = "const tick = f.i * 20 / CFG.fps, dt = tick - lastTick; lastTick = tick;"
    assert old_tick in js
    js = js.replace(old_tick, "const tick = f.tick !== undefined ? f.tick : f.i * 20 / CFG.fps, dt = tick - lastTick; lastTick = tick;")
    old_flame = "if (CFG.boss === 'tyros' && a.k === 'boss') BL.flameFrame(m, Math.floor(tick));"
    assert old_flame in js
    js = js.replace(old_flame, "if (a.k === 'boss' && BL.flameFrame) BL.flameFrame(m, Math.floor(tick));")
    return js


SCENE = dict(BV.SCENE)
SCENE.update({
    'martin': dict(bg='#1d1618', fog=True, hemi=['#e6dcd2', '#2a1816', 0.85], dirs=[['#fff2e2', 0.7, [30, 60, -40]], ['#e8b95a', 0.3, [-40, 20, 50]]],
                   g1='#3a3230', g2='#332b29'),
    'ereb': dict(bg='#141218', fog=True, hemi=['#e8e2f2', '#201a24', 0.85], dirs=[['#fff6e8', 0.7, [30, 60, -40]], ['#a8d8ff', 0.3, [-40, 20, 50]]],
                 g1='#302c34', g2='#2a262e'),
    'ereb_hand': dict(bg='#150f16', fog=True, hemi=['#ece0f0', '#24161f', 0.85], dirs=[['#fff0e0', 0.7, [30, 60, -40]], ['#d8a8ff', 0.3, [-40, 20, 50]]],
                      g1='#322a32', g2='#2c242c'),
})


def build_page(boss, three, cfg, names):
    key = BOSSES[boss][2]
    html = open(os.path.join(HERE, 'sigil_preview.template.html'), encoding='utf-8').read()
    html = html.replace('/*DATA*/null', json.dumps(BV.sigil_data(), ensure_ascii=False), 1)
    if three:
        html = html.replace(BV.CDN, 'file://' + os.path.abspath(three))
    html = '\n'.join(l for l in html.split('\n') if 'fonts.googleapis.com' not in l)
    html = html.replace('</head>', BV.PAGE_CSS + '</head>', 1)
    js = adapter().replace('VW', str(W)).replace('VH', str(H)).replace('VCFG', json.dumps(cfg, ensure_ascii=False))
    js = js.replace('<script>', '<script>\nconst VANIMS = %s;\n' % json.dumps(dummy_anims()), 1)
    return html + '\n' + boss_lib(boss, names) + js


# ---------------------------------------------------------------- раскадровка
def secs(x):
    return max(1, int(round(x * FPS)))


def reel(boss):
    title, anim, key, s, h, what = BOSSES[boss]
    L = json.load(open(os.path.join(A, 'animations', 'entity', ('aris' if boss == 'aris' else boss) + '.animation.json'),
                       encoding='utf-8'))['animations'][anim]['animation_length']
    sp = strike_point(boss)
    dz = (sp[2] * s - 6.0)                             # манекен — сразу за точкой удара (px мира, вперёд −z)
    dx = sp[0] * s * 0.5
    dummy_at = (dx, 0.0, dz)
    frames, runs = [], []
    head = 'T32 «Сломать блок» · %s' % title
    mid_z = dz * 0.5
    span = abs(dz) + h * s

    def cam(t, slow=False):
        yaw = 62 + 10 * math.sin(t * 0.5)
        return {'yaw': yaw, 'pitch': 9, 'dist': max(span * 2.3, h * s * 2.4) * (0.82 if slow else 1.0), 'tx': -6.0, 'ty': h * s * 0.45,
                'tz': mid_z, 'fov': 30}

    def boss_actor(t):
        return {'k': 'boss', 'anim': anim, 't': t, 's': s, 'id': 0}

    def dummy(t_rel):
        if t_rel is None or t_rel < 0:
            return {'k': 'steve', 'anim': 'dummy_block', 't': (len(frames) / FPS) % 2.0, 's': 0.9375, 'x': dummy_at[0], 'z': dummy_at[2],
                    'ry': 180, 'id': 1}
        return {'k': 'steve', 'anim': 'dummy_broken', 't': min(1.8, t_rel), 's': 0.9375, 'x': dummy_at[0], 'z': dummy_at[2] - min(6.0, 22 * t_rel),
                'ry': 180, 'id': 1}
    clock = [0.0]

    def add(t_anim, cap, sub, slow=False, fxtick=True):
        f = {'actors': [boss_actor(t_anim), dummy(None if t_anim < HIT else (t_anim - HIT))], 'cam': cam(len(frames) / FPS, slow),
             'cap': cap, 'sub': sub, 'head': head, 'tick': clock[0], 'tanim': t_anim}
        frames.append(f)
        clock[0] += (SLOW if slow else 1.0) * 20.0 / FPS

    for i in range(secs(0.6)):                         # стойка
        add(0.0, title, what)

    def run_fx(start_frame):
        runs.append({'id': boss + '_guard_break', 's': start_frame, 'e': start_frame + 10 ** 6, 'c': [0, 0, 0],
                     'tg': [dummy_at[0] / 16, 0, dummy_at[2] / 16], 'cId': 0, 'tgId': 1})
    run_fx(len(frames))
    n = secs(L)
    for i in range(n + 1):                             # реальная скорость
        t = min(L, i / FPS)
        ph = 'вспышка-предупреждение' if WARN <= t < 0.62 else ('удар — блок сломан' if 0.66 <= t < 0.95 else '')
        add(t, '%s · %s' % (title, 'реальная скорость'), 'тик %d%s' % (int(t * 20), (' · ' + ph) if ph else ''))
    runs[-1]['e'] = len(frames) + secs(0.4)
    for i in range(secs(0.5)):
        add(L, title, 'повтор ×%.2f' % SLOW)
    clock[0] += 200                                    # отдельная «эпоха» fx для повтора
    run_fx(len(frames))
    n = secs(1.3 / SLOW)
    for i in range(n + 1):                             # замедленный повтор (fx тоже замедлены)
        t = min(1.3, i * SLOW / FPS)
        add(t, '%s · замедленно ×%.2f' % (title, SLOW), 'тик %d · warn 2, hit 14' % int(t * 20), slow=True)
    runs[-1]['e'] = len(frames) + 2
    for i in range(secs(0.5)):
        add(1.3 + i / FPS * 0.5, title, '')
    for r in runs:
        r['e'] = min(r['e'], len(frames) - 1)
    return frames, runs, L


def render(boss, three, out):
    frames, runs, L = reel(boss)
    key = BOSSES[boss][2]
    names = {BOSSES[boss][1]} | ({'irina_cloth_idle'} if boss == 'irina' else set())
    cfg = dict(SCENE[key], boss=key, fps=FPS, runs=runs, preload=[{'k': 'boss'}, {'k': 'steve'}], steve=BV.steve_entry(), flashK=0.6,
               scythe=BV.scythe_item() if key == 'tyros' else None)
    for i, f in enumerate(frames):
        f['i'] = i
    with tempfile.TemporaryDirectory() as td:
        hp = os.path.join(td, 'page.html')
        open(hp, 'w', encoding='utf-8').write(build_page(boss, three, cfg, names))
        jp = os.path.join(td, 'job.json')
        json.dump({'html': hp, 'out': out, 'fps': FPS, 'w': W, 'h': H, 'crf': 22, 'frames': frames}, open(jp, 'w', encoding='utf-8'),
                  ensure_ascii=False)
        r = subprocess.run(['node', os.path.join(HERE, 'boss_video.js'), jp])
        if r.returncode:
            raise SystemExit('render failed: ' + boss)
    # кадры фаз для листа: номера кадров реального прохода
    idx = {}
    for name, tp in PHASES:
        best = min((abs(f['tanim'] - tp) + (0 if f['cap'].endswith('реальная скорость') else 9), i) for i, f in enumerate(frames))
        idx[name] = best[1]
    return idx


def grab(mp4, frame, out):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', mp4, '-vf', 'select=eq(n\\,%d)' % frame, '-vframes', '1', out], check=True)


def sheet(parts, out):
    from PIL import Image, ImageDraw, ImageFont
    cw, ch = 480, 270
    lw, th = 170, 34
    img = Image.new('RGB', (lw + cw * len(PHASES), th + ch * len(parts)), (20, 16, 18))
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 17)
        fs = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    except OSError:
        f = fs = ImageFont.load_default()
    for j, (name, tp) in enumerate(PHASES):
        d.text((lw + j * cw + 10, 8), '%s (%.2f с, тик %d)' % (name, tp, round(tp * 20)), fill=(242, 215, 154), font=f)
    for i, (boss, shots) in enumerate(parts):
        y = th + i * ch
        d.text((10, y + 10), BOSSES[boss][0], fill=(244, 236, 228), font=f)
        words, line, ly = BOSSES[boss][5].split(), '', y + 40
        for w in words:
            if d.textlength(line + ' ' + w, font=fs) > lw - 16:
                d.text((10, ly), line.strip(), fill=(200, 190, 180), font=fs)
                ly += 17
                line = ''
            line += ' ' + w
        d.text((10, ly), line.strip(), fill=(200, 190, 180), font=fs)
        for j, (name, _) in enumerate(PHASES):
            im = Image.open(shots[name]).convert('RGB').resize((cw, ch), Image.LANCZOS)
            img.paste(im, (lw + j * cw, y))
    img.save(out, quality=88)
    print('wrote', os.path.relpath(out, ROOT))


def main(args):
    three = args[args.index('--three') + 1] if '--three' in args else None
    bosses = [b for b in BOSSES if b in args] or list(BOSSES)
    os.makedirs(OUT, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='gb_video_')
    parts, segs = [], []
    for b in bosses:
        seg = os.path.join(tmp, b + '.mp4')
        idx = render(b, three, seg)
        shots = {}
        for name, fr in idx.items():
            p = os.path.join(tmp, '%s_%s.png' % (b, name))
            grab(seg, fr, p)
            shots[name] = p
        parts.append((b, shots))
        segs.append(seg)
    sheet(parts, os.path.join(MEDIA, 't32_guard_break.jpg'))
    lst = os.path.join(tmp, 'list.txt')
    open(lst, 'w').write(''.join("file '%s'\n" % s for s in segs))
    out = os.path.join(OUT, 't32_guard_break.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', '-movflags', '+faststart', out],
                   check=True)
    print('wrote %s (%.1f МБ)' % (os.path.relpath(out, ROOT), os.path.getsize(out) / 1e6))


if __name__ == '__main__':
    main(sys.argv[1:])
