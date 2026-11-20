#!/usr/bin/env python3
"""
Видео-превью анимаций боссов T26 (Тирос / Глава Культа), T27 (Ирина), T28 (Арис).
Модели, анимации и текстуры берутся как есть из assets (через страницы превью tools/*_render.py); здесь только раскадровка.
  python3 tools/boss_video.py [t26|t27|t28 ...] [--only turntable,combat,special,finale] [--three путь/three.min.js]
Нужно: jar Iron's в libs/ (python3 tools/fetch_libs.py), Playwright + Chromium, ffmpeg.
Выход: docs/media/video/t2X_{turntable,combat,special,finale}.mp4 (1280×720, 30 fps, H.264, без звука) + t2X_turntable.gif (480 px).
Fx-частиц в превью нет: показываются анимации, у Ариса — ещё объёмные меши fx (наковальня, слиток, исполинский молот).
"""
import json
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
OUT = os.path.join(ROOT, 'docs', 'media', 'video')
A = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'pohsmp_core')
FPS, W, H = 30, 1280, 720
PAUSE = 0.3
sys.path.insert(0, HERE)


# ---------------------------------------------------------------- общие помощники
def ease_io(x):
    x = max(0.0, min(1.0, x))
    return -(math.cos(math.pi * x) - 1) / 2


def ease_in_quad(x):
    x = max(0.0, min(1.0, x))
    return x * x


def victim_anim():
    """PlayerAnimator-эмоция pohsmp_cult_finisher_victim → ключи GeckoLib для каркаса abstract_casting_mob (Стив-жертва)."""
    p = os.path.join(ROOT, 'src', 'main', 'resources', 'assets', 'irons_spellbooks', 'player_animation', 'pohsmp_cult_finisher_victim.json')
    em = json.load(open(p, encoding='utf-8'))['emote']
    parts = {'rightArm': 'right_arm', 'leftArm': 'left_arm', 'head': 'head', 'rightLeg': 'right_leg', 'leftLeg': 'left_leg', 'torso': 'body'}
    keys = {}
    for mv in em['moves']:
        for k, v in mv.items():
            if k in parts and isinstance(v, dict):
                keys.setdefault(k, {})[mv['tick']] = v
    bones = {}
    for k, kk in keys.items():
        rot = {}
        for tick in sorted(kk):
            v = kk[tick]
            pitch, yaw, roll = v.get('pitch', 0), v.get('yaw', 0), v.get('roll', 0)
            if k in ('rightLeg', 'leftLeg'):                   # корпус наклоняется костью body (родитель ног) — ноги компенсируем
                pitch -= keys['torso'].get(tick, {}).get('pitch', 0)
            rot['%.4f' % (tick / 20)] = [-pitch, -yaw, roll]
        bones[parts[k]] = {'rotation': rot}
    return {'animation_length': em['endTick'] / 20, 'loop': 'hold_on_last_frame', 'bones': bones}


class Reel:
    """Набор кадров одного ролика."""

    def __init__(self, boss, head):
        self.boss, self.head, self.frames, self.marks = boss, head, [], []

    @property
    def t(self):
        return len(self.frames) / FPS

    def mark(self, text):
        self.marks.append((round(self.t, 1), text))

    def add(self, n, fn):
        for i in range(n):
            f = fn(i)
            f.setdefault('head', self.head)
            self.frames.append(f)


def secs(x):
    return max(1, int(round(x * FPS)))


# ---------------------------------------------------------------- страницы превью + адаптер VID
ADAPTER = r"""
<script>
window.VID = (() => {
  const D = Math.PI / 180, BOSS = VBOSS;
  let scene, cache = {}, cap, sub, head, fade, flash;
  function init() {
    scene = makeScene({});
    scene.traverse(o => {                                   // пол шире (для общих планов), клетка того же размера
      if (o.geometry && o.geometry.type === 'PlaneGeometry' && o.material && o.material.map) { o.scale.set(8, 8, 1); o.material.map.repeat.multiplyScalar(8); }
    });
    for (const el of document.querySelectorAll('.lab, #ui')) el.style.display = 'none';
    const css = document.createElement('style');
    css.textContent = `#vcap{position:fixed;left:0;right:0;bottom:34px;text-align:center;z-index:9;font:600 30px 'DejaVu Sans',system-ui,sans-serif;
      color:#f6eee6;text-shadow:0 0 6px #000,0 0 3px #000,0 2px 2px #000} #vcap small{display:block;font:400 17px 'DejaVu Sans Mono',monospace;color:#c8bcb4;margin-top:4px}
      #vhead{position:fixed;left:22px;top:16px;z-index:9;font:600 18px 'DejaVu Sans',system-ui,sans-serif;color:#e8dcd2;opacity:.85;text-shadow:0 0 4px #000}
      #vfade,#vflash{position:fixed;inset:0;z-index:8;pointer-events:none;opacity:0} #vfade{background:#000} #vflash{background:#fff6e8}`;
    document.head.appendChild(css);
    for (const id of ['vcap', 'vhead', 'vfade', 'vflash']) { const d = document.createElement('div'); d.id = id; document.body.appendChild(d); }
    cap = document.getElementById('vcap'); head = document.getElementById('vhead');
    fade = document.getElementById('vfade'); flash = document.getElementById('vflash');
    // заранее строим все модели (текстуры грузятся до первого кадра)
    for (const k of VPRELOAD) getModel(k);
  }
  function getModel(a) {
    const key = a.k + '|' + (a.v || '');
    if (cache[key]) return cache[key];
    let m;
    if (a.k === 'boss') {
      if (BOSS === 'tyros') m = buildModel(DATA.models.cult_leader, a.v === 'soul');
      else if (BOSS === 'irina') { m = buildModel(); attachStaff(m); }
      else m = buildModel(DATA.models.aris, a.v || 'base');
    } else if (a.k === 'steve') {
      if (BOSS === 'tyros') m = buildModel(DATA.models.steve, false);
      else if (BOSS === 'irina') m = buildModel(VSTEVE);
      else m = buildModel(VSTEVE, 'base');
    } else if (a.k.startsWith('mesh:')) {
      m = { root: buildMesh(DATA.meshes[a.k.slice(5)], 16), bones: {} };
    }
    m.holder = new THREE.Group(); m.holder.add(m.root); scene.add(m.holder); m.holder.visible = false;
    return cache[key] = m;
  }
  const AN = n => n ? (DATA.anims[n] || VANIMS[n] || null) : null;
  function doPose(m, a, p) {
    if (!m.bones || !Object.keys(m.bones).length) return;
    if (BOSS === 'tyros') pose(m, AN(p.anim), p.t || 0);
    else if (BOSS === 'irina') pose(m, AN(p.anim), a.k === 'boss' ? AN(p.cloth || 'irina_cloth_idle') : null, p.t || 0, p.tc);
    else pose(m, AN(p.anim), p.t || 0, p.hide);
  }
  function applyPose(m, a) {
    doPose(m, a, a);
    if (!a.blend) return;
    const s = {};
    for (const n in m.bones) { const g = m.bones[n]; s[n] = [g.position.clone(), g.quaternion.clone(), g.scale.clone()]; }
    doPose(m, a, a.blend);
    const w = a.blend.w;
    for (const n in m.bones) {
      const g = m.bones[n];
      g.position.lerpVectors(s[n][0], g.position.clone(), w);
      g.quaternion.copy(s[n][1].clone().slerp(g.quaternion.clone(), w));
      g.scale.lerpVectors(s[n][2], g.scale.clone(), w);
    }
  }
  function render(f) {
    for (const k in cache) cache[k].holder.visible = false;
    for (const a of f.actors) {
      const m = getModel(a);
      m.holder.visible = a.vis !== false;
      applyPose(m, a);
      m.holder.position.set(a.x || 0, a.y || 0, a.z || 0);
      m.holder.rotation.set((a.rx || 0) * D, (a.ry || 0) * D, (a.rz || 0) * D, 'YXZ');
      m.root.scale.setScalar(a.s || 1);
      if (BOSS === 'tyros' && a.k === 'boss') flameFrame(m, f.tick || 0);
    }
    const c = f.cam, W = window.innerWidth, H = window.innerHeight;
    const cam = new THREE.PerspectiveCamera(c.fov || 30, W / H, 0.5, 6000);
    const yaw = c.yaw * D, pitch = c.pitch * D;
    cam.position.set(c.tx + Math.sin(yaw) * Math.cos(pitch) * c.dist, c.ty + Math.sin(pitch) * c.dist, c.tz - Math.cos(yaw) * Math.cos(pitch) * c.dist);
    cam.lookAt(c.tx, c.ty, c.tz);
    if (scene.fog) { scene.fog.near = Math.max(200, c.dist * 1.3); scene.fog.far = scene.fog.near + 600; }   // туман по дистанции камеры
    renderer.setViewport(0, 0, W, H); renderer.setScissor(0, 0, W, H);
    renderer.render(scene, cam);
    cap.innerHTML = f.cap ? f.cap + (f.sub ? '<small>' + f.sub + '</small>' : '') : '';
    head.textContent = f.head || '';
    fade.style.opacity = f.fade || 0; flash.style.opacity = f.flash || 0;
  }
  return { init, render };
})();
</script>
"""


def steve_entry(fmt):
    import cult_leader_render as cr
    e = cr.model_entry('steve')
    if fmt == 'aris':
        return {'geo': e['geo'], 'tex': {'base': e['tex']}, 'glow': {}, 'height': 32}
    return {'geo': e['geo'], 'tex': e['tex'], 'height': 32}


def build_page(boss, three, preload):
    if boss == 'tyros':
        import cult_leader_render as cr
        html = cr.page(['cult_leader', 'steve'], {'cols': 1, 'cells': [{'model': 'cult_leader'}]}, three, anims=cr.iron_anims())
        steve = 'null'
    elif boss == 'irina':
        import irina_render as ir
        html = ir.page({'cols': 1, 'cells': [{'anim': 'irina_idle'}]}, three)
        steve = json.dumps(steve_entry('irina'))
    else:
        import aris_render as ar
        html = ar.page({'cols': 1, 'cells': [{'model': 'aris'}]}, three)
        steve = json.dumps(steve_entry('aris'))
    js = ADAPTER.replace('VBOSS', json.dumps(boss)).replace('VPRELOAD', json.dumps(preload))
    js = js.replace('<script>', '<script>\nconst VSTEVE = %s;\nconst VANIMS = %s;\n' % (steve, json.dumps({'victim': victim_anim()})), 1)
    return html.replace('</body>', js + '</body>')


def render(boss, reel, out, three, preload, crf=20):
    os.makedirs(OUT, exist_ok=True)
    sm = None
    for i, f in enumerate(reel.frames):
        f['tick'] = i * 20 // FPS
        c = f['cam']                                   # плавная камера: смены плана (наезд/отъезд) сглаживаются, без рывков
        if sm is None:
            sm = dict(c)
        for k in ('dist', 'ty', 'tz', 'tx', 'pitch', 'yaw'):
            sm[k] += (c[k] - sm[k]) * 0.09
        f['cam'] = dict(c, **{k: sm[k] for k in ('dist', 'ty', 'tz', 'tx', 'pitch', 'yaw')}) if not f.get('rawcam') else c
    with tempfile.TemporaryDirectory() as td:
        hp = os.path.join(td, 'page.html')
        with open(hp, 'w', encoding='utf-8') as fh:
            fh.write(build_page(boss, three, preload))
        jp = os.path.join(td, 'job.json')
        with open(jp, 'w', encoding='utf-8') as fh:
            json.dump({'html': hp, 'out': out, 'fps': FPS, 'w': W, 'h': H, 'crf': crf, 'frames': reel.frames}, fh, ensure_ascii=False)
        r = subprocess.run(['node', os.path.join(HERE, 'boss_video.js'), jp])
        if r.returncode:
            raise SystemExit('render failed: ' + out)
    mb = os.path.getsize(out) / 1e6
    print('wrote %s (%.1f с, %.1f МБ)' % (os.path.relpath(out, ROOT), reel.t, mb))
    return mb


def gif(mp4, out):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', mp4, '-vf',
                    'fps=15,scale=480:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160[p];[b][p]paletteuse=dither=bayer:bayer_scale=4',
                    out], check=True)
    print('wrote %s (%.1f МБ)' % (os.path.relpath(out, ROOT), os.path.getsize(out) / 1e6))


# ---------------------------------------------------------------- описание боссов
class Boss:
    key = ''
    title = ''
    s = 1.0             # масштаб рендера
    h = 40              # рост в единицах мира (px модели × масштаб), для кадра
    idle = None         # анимация покоя
    yaw0 = 32           # «3/4 спереди»

    def anim_len(self, name):
        return self.anims[name]['animation_length']

    def boss(self, anim, t, **kw):
        a = {'k': 'boss', 'anim': anim, 't': t, 's': self.s}
        a.update(kw)
        return a

    def idle_actor(self, t, **kw):
        return self.boss(self.idle, t % self.anim_len(self.idle) if self.idle else 0, **kw)

    def cam(self, t, zoom=1.0, ty=None, yaw=None, dz=0.0, pitch=7):
        """Плавная камера 3/4 спереди: медленное покачивание по азимуту."""
        y = (self.yaw0 if yaw is None else yaw) + 7 * math.sin(2 * math.pi * t / 18)
        return {'yaw': y, 'pitch': pitch, 'dist': 3.0 * self.h * zoom, 'tx': 0, 'ty': self.h * 0.52 if ty is None else ty, 'tz': dz, 'fov': 30}

    # -------- turntable
    def turntable(self, dur=7.0):
        r = Reel(self.key, self.title + ' · поворот 360°')
        n = secs(dur)
        r.mark('0–%.0f с: поворот 360° в покое' % dur)
        r.add(n, lambda i: {'actors': [self.idle_actor(i / FPS, ry=-360 * i / n)],
                            'cam': dict(self.cam(0, zoom=1.0), yaw=self.yaw0), 'rawcam': True, 'cap': 'Покой', 'sub': self.idle or '(поза покоя)'})
        return r

    # -------- последовательность анимаций с титрами и паузами-переходами
    def sequence(self, r, items, zoom=1.0, pause=PAUSE):
        """items: dict(anim, cap, dur?, t0?, cloth?, extra?(t)->(actors, frame-extras), zoom?, actor_kw?(t)->dict)"""
        prev = None
        for it in items:
            anim = it['anim']
            L = it.get('dur', self.anim_len(anim) - it.get('t0', 0))
            t0 = it.get('t0', 0)
            z = it.get('zoom', zoom)
            nxt = self.actor_for(it, t0)
            if prev is not None and pause:
                np_ = secs(pause)
                r.add(np_, lambda i, prev=prev, nxt=nxt, z=z: {
                    'actors': [dict(prev, blend=dict(nxt, w=ease_io((i + 1) / np_)))],
                    'cam': self.cam(r.t, zoom=z, **it.get('camkw', {}))})
            r.mark('%s (`%s`)' % (it['cap'], anim))
            n = secs(L)

            def fr(i, it=it, t0=t0, z=z):
                t = t0 + i / FPS
                a = self.actor_for(it, t)
                f = {'actors': [a], 'cam': self.cam(r.t, zoom=z, **it.get('camkw', {})), 'cap': it['cap'], 'sub': it.get('sub', anim)}
                if it.get('camf'):
                    f['cam'].update(it['camf'](t))
                if it.get('extra'):
                    it['extra'](t, f)
                return f
            r.add(n, fr)
            prev = self.actor_for(it, t0 + (n - 1) / FPS)
        return prev

    def actor_for(self, it, t):
        kw = dict(it.get('kw', {}))
        if it.get('kwf'):
            kw.update(it['kwf'](t))
        return self.boss(it['anim'], t, **kw)

    def hold(self, r, actor, dur, cap=None, sub=None, zoom=1.0, **fx):
        r.add(secs(dur), lambda i: dict({'actors': [actor], 'cam': self.cam(r.t, zoom=zoom), 'cap': cap, 'sub': sub}, **fx))

    def blend_to(self, r, frm, to, dur=PAUSE, zoom=1.0, cap=None):
        n = secs(dur)
        r.add(n, lambda i: {'actors': [dict(frm, blend=dict(to, w=ease_io((i + 1) / n)))], 'cam': self.cam(r.t, zoom=zoom), 'cap': cap})


# ================================================================ T26: Тирос / Глава Культа
class Tyros(Boss):
    key, title = 't26', 'Тирос, Глава Культа Меллисто'
    s = 1.75
    h = 36 * 1.75
    idle = None

    def __init__(self):
        self.anims = json.load(open(os.path.join(A, 'animations', 'entity', 'cult_leader.animation.json'), encoding='utf-8'))['animations']

    def combat(self):
        r = Reel(self.key, self.title + ' · бой')
        items = [
            dict(anim='scythe_backpedal', cap='Отскок назад с косой'),
            dict(anim='scythe_jump_combo', cap='Прыжок и комбо косой'),
            dict(anim='scythe_downslash_sideslash', cap='Удар сверху и боковой взмах'),
            dict(anim='scythe_horizontal_slash_spin', cap='Горизонтальный взмах с разворотом'),
            dict(anim='scythe_dagger_double_horizontal', cap='Двойной взмах: коса и кинжал'),
            dict(anim='summon_fiery_daggers', cap='Призыв огненных кинжалов'),
            dict(anim='fire_boss_acrobatic_dagger_throw', cap='Акробатический бросок кинжалов'),
            dict(anim='offhand_parry', cap='Парирование'),
            dict(anim='fire_boss_break_stance', cap='Слом стойки (оглушён)'),
        ]
        self.sequence(r, items, zoom=1.15)
        return r

    def special(self):
        r = Reel(self.key, self.title + ' · особые и новые заклинания')
        items = [
            dict(anim='charge_raised_hand', dur=2.0, cap='«Приговор Меллисто» — каст', sub='charge_raised_hand, первые 2 с'),
            dict(anim='cult_leader_first_flame', cap='«Первое Пламя»', zoom=1.15),
            dict(anim='cult_leader_ash_dissolve', cap='«Пепел Меллисто»: рассыпается в пепел'),
        ]
        last = self.sequence(r, items, zoom=1.15)
        # вихрь: босс невидим (в игре — fx cult_ash_vortex), сжато до 0.8 с
        r.mark('«Пепел Меллисто»: вихрь (босс скрыт, fx нет) ')
        self.hold(r, dict(last, vis=False), 0.8, cap='«Пепел Меллисто»: вихрь пепла', sub='босс скрыт; fx вихря в превью нет', zoom=1.15)
        items = [
            dict(anim='cult_leader_ash_reform', cap='«Пепел Меллисто»: собирается из пепла'),
            dict(anim='cult_leader_ash_slash', cap='«Пепел Меллисто»: разрез через арену'),
        ]
        r.mark('«Пепел Меллисто»: сборка (`cult_leader_ash_reform`)')
        n = secs(self.anim_len('cult_leader_ash_reform'))
        r.add(n, lambda i: {'actors': [self.boss('cult_leader_ash_reform', i / FPS)], 'cam': self.cam(r.t, zoom=1.15),
                            'cap': items[0]['cap'], 'sub': 'cult_leader_ash_reform'})
        last = self.sequence(r, items[1:], zoom=1.15)
        items = [
            dict(anim='cult_leader_replica_break', cap='Ломает «Дезинтеграцию: Реплику»'),
            dict(anim='cult_leader_sickle_throw', cap='Новое: «Огненный серп»', sub='cult_leader_sickle_throw (коса в превью остаётся в руке)'),
            dict(anim='cult_leader_ash_trail_dash', cap='Новое: «Пепельный след»'),
            dict(anim='cult_leader_brand', cap='Новое: «Клеймо культа»'),
            dict(anim='cult_leader_pillars', cap='Новое: «Столпы пламени»'),
        ]
        self.blend_to(r, last, self.boss(items[0]['anim'], 0), zoom=1.15)
        self.sequence(r, items, zoom=1.15)
        return r

    def finale(self):
        r = Reel(self.key, self.title + ' · финал')
        # появление: 0–1.5 с модель не рисуется (fx cult_leader_intro), потом выходит из огня в 6.56 бл. позади
        L = self.anim_len('fire_boss_spawn')
        r.mark('Появление (`fire_boss_spawn`, 8.75 с; 0–1.5 с босс скрыт, как в игре)')
        n = secs(L)
        r.add(n, lambda i: {'actors': [self.boss('fire_boss_spawn', i / FPS, vis=i / FPS >= 1.5)],
                            'cam': self.cam(r.t, zoom=1.45, dz=40, ty=self.h * 0.6), 'cap': 'Появление',
                            'sub': 'fire_boss_spawn' + (' — 0–1.5 с босс скрыт (пламя из земли — fx)' if i / FPS < 1.5 else '')})
        last = self.boss('fire_boss_spawn', L)
        # переход в облик души (фаза 3)
        L2 = self.anim_len('fire_boss_half_health_attack')
        self.blend_to(r, last, self.boss('fire_boss_half_health_attack', 0), zoom=1.2)
        r.mark('Переход в облик души (`fire_boss_half_health_attack`, 11.8 с) → облик души ×2.0125')
        n = secs(L2)
        r.add(n, lambda i: {'actors': [self.boss('fire_boss_half_health_attack', i / FPS)], 'cam': self.cam(r.t, zoom=1.2),
                            'cap': 'Переход в облик души', 'sub': 'fire_boss_half_health_attack',
                            'flash': max(0.0, 1 - (n - i) / 10) * 0.9})
        soul = dict(self.boss('fire_boss_half_health_attack', L2, v='soul'), s=2.0125)
        nf = secs(0.5)
        r.add(nf, lambda i: {'actors': [soul], 'cam': self.cam(r.t, zoom=1.25), 'cap': 'Облик души', 'sub': 'cult_leader_soul_mode, рендер ×2.0125',
                             'flash': 0.9 * (1 - (i + 1) / nf)})
        soul_idle = dict(self.boss(None, 0, v='soul'), s=2.0125)
        self.blend_to(r, soul, soul_idle, dur=0.6, zoom=1.25, cap='Облик души')
        self.hold(r, soul_idle, 1.0, cap='Облик души', sub='cult_leader_soul_mode, рендер ×2.0125', zoom=1.25)
        # смерть (в облике души): ролик — первые 3.5 с анимации
        r.mark('Смерть (`fire_boss_death`, первые 3.5 с — длина ролика) + затемнение')
        self.blend_to(r, soul_idle, dict(self.boss('fire_boss_death', 0, v='soul'), s=2.0125), zoom=1.25)
        n = secs(4.2)
        r.add(n, lambda i: {'actors': [dict(self.boss('fire_boss_death', min(i / FPS, 8.0), v='soul'), s=2.0125)],
                            'cam': self.cam(r.t, zoom=1.25), 'cap': 'Смерть', 'sub': 'fire_boss_death (ролик 0–3.5 с)',
                            'fade': max(0.0, (i / FPS - 3.5) / 0.7)})
        r.add(secs(0.4), lambda i: {'actors': [], 'cam': self.cam(r.t), 'fade': 1})
        # добивание с жертвой-Стивом
        r.mark('Добивание (`cult_leader_finisher` + жертва `pohsmp_cult_finisher_victim`)')
        L3 = self.anim_len('cult_leader_finisher')
        nf = secs(0.5)
        r.add(nf, lambda i: dict(self.finisher_frame(0, r.t), fade=1 - (i + 1) / nf))
        n = secs(L3 + 0.8)
        r.add(n, lambda i: self.finisher_frame(i / FPS, r.t))
        return r

    def finisher_frame(self, t, rt):
        boss = self.boss('cult_leader_finisher', min(t, 2.4))
        B = 16
        z0, z1 = -5.0 * B, -3.0 * B
        z = z0 + (z1 - z0) * ease_in_quad(t / 0.7)
        y = 2.3 * B * ease_io((t - 1.0) / 0.7)
        sc = 0.9375 * (1 - ease_in_quad((t - 2.2) / 0.45)) if t > 2.2 else 0.9375
        victim = {'k': 'steve', 'anim': 'victim', 't': min(t, 2.4), 's': max(sc, 0.001), 'x': 0, 'y': y, 'z': z, 'ry': 180, 'vis': t < 2.65}
        cam = self.cam(rt, zoom=1.35, ty=self.h * 0.62, dz=-22, yaw=48)
        return {'actors': [boss, victim], 'cam': cam, 'cap': 'Добивание',
                'sub': 'cult_leader_finisher: тянет 0–0.7 · пронзает 1.0 · поднимает · пепел 2.2' + ('' if t < 2.2 else ' (жертва рассыпается — fx пепла)')}


# ================================================================ T27: Ирина
class Irina(Boss):
    key, title = 't27', 'Ирина, Ведьма Ревности'
    s = 1.0
    h = 54
    idle = 'irina_idle'

    def __init__(self):
        self.anims = json.load(open(os.path.join(A, 'animations', 'entity', 'irina.animation.json'), encoding='utf-8'))['animations']

    def boss(self, anim, t, **kw):
        kw.setdefault('cloth', 'irina_cloth_storm' if anim not in (None, 'irina_idle', 'irina_walk') else
                      ('irina_cloth_walk' if anim == 'irina_walk' else 'irina_cloth_idle'))
        kw.setdefault('tc', t)
        return super().boss(anim, t, **kw)

    def combat(self):
        r = Reel(self.key, self.title + ' · бой')
        items = [
            dict(anim='irina_staff_attack', cap='Удар крюком посоха сверху'),
            dict(anim='irina_staff_sweep', cap='Взмах посохом по кругу'),
            dict(anim='irina_cast_short', cap='Короткий каст'),
            dict(anim='irina_cast_long', dur=2.0, cap='Длинный каст (цикл)'),
            dict(anim='irina_cast_long_end', cap='Длинный каст — завершение'),
            dict(anim='irina_mark', cap='«Предмет ревности» — метка'),
            dict(anim='irina_bind', cap='Связать пары (фаза 2)'),
            dict(anim='irina_whip', cap='Хлёст нитей (фаза 3)'),
            dict(anim='irina_steal', cap='Кража эффектов'),
        ]
        self.sequence(r, items, zoom=1.0)
        return r

    def special(self):
        r = Reel(self.key, self.title + ' · особые и новые заклинания')
        items = [
            dict(anim='irina_others_happiness', cap='«Чужое счастье»'),
            dict(anim='irina_only_mine', cap='«Только мой»', kw={'cloth': 'irina_cloth_cocoon'}),
            dict(anim='irina_only_mine_broken', cap='«Только мой»: кокон разорван'),
            dict(anim='irina_phase2', cap='Переход в фазу 2'),
            dict(anim='irina_phase3', cap='Переход в фазу 3'),
            dict(anim='irina_gaze', cap='Новое: «Ревнивый взгляд»'),
            dict(anim='irina_knots', cap='Новое: «Узлы»'),
            dict(anim='irina_swap', cap='Новое: «Подмена любимого»'),
            dict(anim='irina_puppet', cap='Новое: «Марионетка»'),
            dict(anim='irina_puppet_hold', dur=2.0, cap='Новое: «Марионетка» — удержание (цикл)'),
        ]
        self.sequence(r, items, zoom=1.0)
        return r

    def finale(self):
        r = Reel(self.key, self.title + ' · финал')
        r.mark('Появление (`irina_spawn` + ткань `irina_cloth_spawn`, 7 с)')
        L = self.anim_len('irina_spawn')
        r.add(secs(L), lambda i: {'actors': [self.boss('irina_spawn', i / FPS, cloth='irina_cloth_spawn')], 'cam': self.cam(r.t, zoom=1.05),
                                  'cap': 'Появление', 'sub': 'irina_spawn + irina_cloth_spawn'})
        last = self.boss('irina_spawn', L, cloth='irina_cloth_spawn')
        self.blend_to(r, last, self.idle_actor(0))
        self.hold(r, self.idle_actor(0), 0.4)
        nf = secs(0.4)
        r.add(nf, lambda i: {'actors': [self.idle_actor(0)], 'cam': self.cam(r.t), 'fade': (i + 1) / nf})
        r.mark('Добивание (`irina_finisher` + жертва, поза `pohsmp_cult_finisher_victim`)')
        r.add(nf, lambda i: dict(self.finisher_frame(0, r.t), fade=1 - (i + 1) / nf))
        r.add(secs(2.6 + 0.9), lambda i: self.finisher_frame(i / FPS, r.t))
        last = self.boss('irina_finisher', 2.6)
        r.add(nf, lambda i: dict(self.finisher_frame(3.5, r.t), fade=(i + 1) / nf))
        r.mark('Смерть (`irina_death` + `irina_cloth_death`, 5 с; на `gone` 5.0 сущность убирается)')
        L = self.anim_len('irina_death')
        r.add(nf, lambda i: {'actors': [self.boss('irina_death', 0, cloth='irina_cloth_death')], 'cam': self.cam(r.t, zoom=1.05),
                             'fade': 1 - (i + 1) / nf, 'cap': 'Смерть'})
        n = secs(L + 0.6)
        r.add(n, lambda i: {'actors': [self.boss('irina_death', min(i / FPS, L), cloth='irina_cloth_death')], 'cam': self.cam(r.t, zoom=1.05),
                            'cap': 'Смерть', 'sub': 'irina_death + irina_cloth_death', 'fade': max(0.0, (i / FPS - L) / 0.6)})
        return r

    def finisher_frame(self, t, rt):
        B = 16
        boss = self.boss('irina_finisher', min(t, 2.6))
        z = -3.6 * B + (3.6 - 1.6) * B * ease_in_quad(t / 0.8)
        fall = ease_io((t - 2.2) / 0.5)
        victim = {'k': 'steve', 'anim': 'victim', 't': min(t, 1.7), 's': 0.9375, 'x': 0, 'y': 0, 'z': z - fall * 4, 'ry': 180, 'rx': -88 * fall}
        return {'actors': [boss, victim], 'cam': self.cam(rt, zoom=1.0, ty=self.h * 0.45, dz=-14, yaw=55), 'cap': 'Добивание',
                'sub': 'irina_finisher: нити 0.2 · притянута 0.8 · крюк 1.3 · шёпот 1.7 · смерть 2.2'}


# ================================================================ T28: Арис
class Aris(Boss):
    key, title = 't28', 'Арис, Мифический Кузнец'
    s = 1.0             # письмо T28: масштаб рендера 1.0–1.15 — снято в 1.0
    h = 46
    idle = 'animation.aris.idle'

    def __init__(self):
        self.anims = json.load(open(os.path.join(A, 'animations', 'entity', 'aris.animation.json'), encoding='utf-8'))['animations']

    def combat(self):
        r = Reel(self.key, self.title + ' · бой')
        P = 'animation.aris.'
        B = 16

        def anvil(t, f):                                   # «каст»: наковальня вырастает справа-спереди (меш fx aris_anvil, 12 тиков)
            g = ease_io((t - 0.8) / 0.6)
            if t >= 0.8:
                f['actors'].append({'k': 'mesh:aris_anvil', 's': max(g, 0.001), 'x': -1.2 * B, 'z': -3.2 * B, 'ry': 30})
        items = [
            dict(anim=P + 'walk', dur=2.4, cap='Тяжёлый шаг, молот на плече', sub='walk (2 цикла)'),
            dict(anim=P + 'slam', cap='Удар молотом по земле', sub='slam'),
            dict(anim=P + 'swing', cap='Горизонтальный размах', sub='swing'),
            dict(anim=P + 'cast', cap='Каст: наковальня / клинки / перековка', sub='cast + меш fx aris_anvil', extra=anvil),
        ]
        self.sequence(r, items, zoom=1.1)
        return r

    def special(self):
        r = Reel(self.key, self.title + ' · особые и новые заклинания')
        P = 'animation.aris.'
        B = 16

        def billet(t, f):                                  # слиток летит из левой руки с 0.7 с (снаряд кода с мешем aris_billet)
            if 0.7 <= t <= 1.4:
                k = (t - 0.7) / 0.7
                f['actors'].append({'k': 'mesh:aris_billet', 's': 1.0, 'x': 0.5 * B, 'y': (1.4 + 2.2 * k - 3.2 * k * k) * B, 'z': -(0.8 + 9 * k) * B,
                                    'ry': 0, 'rx': 400 * k})

        def giant(t, f):                                   # исполинский молот: висит на +20, к 3.5 опускается до +18, 3.5–4.0 рушится
            tk = t * 20
            if tk <= 70:
                y = 20 - 2 * math.sin(tk / 70 * math.pi / 2)
            elif tk <= 80:
                k = (tk - 70) / 10
                y = 18 * (1 - k ** 3)
            else:
                y = 0
            if t <= 94 / 20:
                f['actors'].append({'k': 'mesh:aris_giant_hammer', 's': 1.0, 'x': 0, 'y': y * B, 'z': -14 * B, 'ry': 0})
            if 4.0 <= t < 4.2:
                f['flash'] = 0.7 * (1 - (t - 4.0) / 0.2)

        def mythic(t):
            return {'v': 'mythic' if t >= 1.6 else 'base'}
        items = [
            dict(anim=P + 'phase2', cap='Переход в фазу 2', sub='phase2'),
            dict(anim=P + 'phase3', cap='Переход в фазу 3: броня раскаляется', sub='phase3 (на 1.6 — текстура aris_mythic)', kwf=mythic),
            dict(anim=P + 'forge', cap='Особое: «Горн»', sub='forge (удары 1.0 / 1.8 / 2.6, вспышка пола 3.3 — fx)', kw={'v': 'mythic'}),
            dict(anim=P + 'last_blow', cap='Особое: «Последний удар молота»', sub='last_blow + меш fx aris_giant_hammer (падает 3.5–4.0)',
                 kw={'v': 'mythic'}, extra=giant, zoom=1.15, camf=lambda t: {} if t < 1.4 else
                 {'yaw': 75, 'pitch': 6, 'dist': 1250, 'tx': 0, 'ty': 19 * 16, 'tz': -7 * 16}),
            dict(anim=P + 'billet', cap='Новое: «Раскалённая заготовка»', sub='billet + меш fx aris_billet (бросок 0.7)', extra=billet, zoom=1.25,
                 camkw={'dz': -40}),
            dict(anim=P + 'chains', cap='Новое: «Цепи кузни»', sub='chains'),
            dict(anim=P + 'quench', cap='Новое: «Закалка»', sub='quench'),
            dict(anim=P + 'bellows', cap='Новое: «Мехи»', sub='bellows'),
        ]
        self.sequence(r, items, zoom=1.1)
        return r

    def finale(self):
        r = Reel(self.key, self.title + ' · финал')
        P = 'animation.aris.'

        def spawn_v(t):
            return 'spent' if t < 4.5 else ('dim' if t < 6.0 else 'base')
        L = self.anim_len(P + 'spawn')
        r.mark('Появление (`spawn`, 9 с; текстура spent → dim 4.5 → aris 6.0)')
        r.add(secs(L), lambda i: {'actors': [self.boss(P + 'spawn', i / FPS, v=spawn_v(i / FPS))], 'cam': self.cam(r.t, zoom=1.15),
                                  'cap': 'Появление', 'sub': 'spawn · рога: погасли → тлеют 4.5 → горят 6.0'})
        last = self.boss(P + 'spawn', L, v='base')
        TAB = [(1.2, 'base'), (2.0, 'dim'), (2.15, 'base'), (2.25, 'dim'), (2.45, 'base'), (2.5, 'dim'), (2.6, 'spent')]

        def sur_v(t):
            v = 'base'                                   # до 1.2 — «текущая»; после появления это aris
            for tt, vv in TAB:
                if t >= tt:
                    v = vv
            return v
        self.blend_to(r, last, self.boss(P + 'surrender', 0, v='base'), dur=0.5, zoom=1.15)
        L = self.anim_len(P + 'surrender')
        r.mark('Сдача (`surrender`, 5 с: на колено 1.2, рога/глаза гаснут 2.0–2.6, молот падает 3.2, фраза 3.6)')
        r.add(secs(L + 0.7), lambda i: {'actors': [self.boss(P + 'surrender', min(i / FPS, L), v=sur_v(i / FPS))], 'cam': self.cam(r.t, zoom=1.15),
                                        'cap': 'Сдача' if i / FPS < 3.6 else '«Чёрт! Я сдаюсь, прекращайте...я помогу вам..»',
                                        'sub': 'surrender · рога и глаза гаснут 2.0–2.6 · молот падает 3.2'})
        last = self.boss(P + 'surrender', L, v='spent')
        nf = secs(0.5)
        r.add(nf, lambda i: {'actors': [last], 'cam': self.cam(r.t, zoom=1.15), 'fade': (i + 1) / nf})
        r.mark('Мирный NPC: `npc_stand` (aris_dim), затем `npc_sit`')
        r.add(nf, lambda i: {'actors': [self.boss(P + 'npc_stand', 0, v='dim')], 'cam': self.cam(r.t, zoom=1.15), 'fade': 1 - (i + 1) / nf,
                             'cap': 'Мирный NPC: стоит у молота'})
        r.add(secs(4.0), lambda i: {'actors': [self.boss(P + 'npc_stand', i / FPS, v='dim')], 'cam': self.cam(r.t, zoom=1.15),
                                    'cap': 'Мирный NPC: стоит у молота', 'sub': 'npc_stand (текстура aris_dim)'})
        self.blend_to(r, self.boss(P + 'npc_stand', 4.0 - 1 / FPS, v='dim'), self.boss(P + 'npc_sit', 0, v='dim'), dur=0.5, zoom=1.15)
        r.add(secs(4.0), lambda i: {'actors': [self.boss(P + 'npc_sit', i / FPS, v='dim')], 'cam': self.cam(r.t, zoom=1.15),
                                    'cap': 'Мирный NPC: сидит на молоте', 'sub': 'npc_sit (текстура aris_dim)'})
        return r


BOSSES = {'t26': (Tyros, 'tyros', [{'k': 'boss'}, {'k': 'boss', 'v': 'soul'}, {'k': 'steve'}]),
          't27': (Irina, 'irina', [{'k': 'boss'}, {'k': 'steve'}]),
          't28': (Aris, 'aris', [{'k': 'boss', 'v': v} for v in ('base', 'dim', 'spent', 'mythic')]
                  + [{'k': 'mesh:aris_anvil'}, {'k': 'mesh:aris_billet'}, {'k': 'mesh:aris_giant_hammer'}])}


def main():
    args = sys.argv[1:]
    three = args[args.index('--three') + 1] if '--three' in args else None
    only = args[args.index('--only') + 1].split(',') if '--only' in args else ['turntable', 'combat', 'special', 'finale']
    keys = [a for a in args if a in BOSSES] or list(BOSSES)
    marks = {}
    for k in keys:
        cls, name, pre = BOSSES[k]
        b = cls()
        for what in only:
            reel = getattr(b, what)()
            out = os.path.join(OUT, '%s_%s.mp4' % (k, what))
            mb = render(name, reel, out, three, pre)
            if mb > 15:
                render(name, reel, out, three, pre, crf=26)
            marks['%s_%s' % (k, what)] = {'dur': round(reel.t, 1), 'marks': reel.marks}
            if what == 'turntable':
                gif(out, os.path.join(OUT, '%s_turntable.gif' % k))
    mp = os.path.join(OUT, 'marks.json')
    old = json.load(open(mp, encoding='utf-8')) if os.path.exists(mp) else {}
    old.update(marks)
    json.dump(old, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
