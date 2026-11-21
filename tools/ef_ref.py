#!/usr/bin/env python3
"""
Эталон анимаций (владелец 21.11): Epic Fight + аддоны Nightfall / Weapons of Miracles — ЧТЕНИЕ И ИЗМЕРЕНИЕ, без копирования.
Файлы и ключи кадров чужих анимаций в мод и в репозиторий НЕ попадают: jar'ы лежат вне репо, здесь только код, который их читает,
и наши измерения (числа) — для docs/specs/anim_style_epicfight.md и tools/anim_style_check.py.

Где брать jar'ы (держать ВНЕ репозитория, путь — переменная EF_REF_DIR или --ref-dir):
  epicfight-1.20.1-20.14.17.jar — libs/ (python3 tools/fetch_libs.py) или EF_REF_DIR
  WeaponsOfMiracles-2.0.14-mc1.20.1-forge.jar — Modrinth (проект weapons-of-miracles)
  EpicFight Nightfall-3.1.jar — CurseForge, файл 7681377 (edge.forgecdn.net/files/7681/377/EpicFight%20Nightfall-3.1.jar)

Формат анимации Epic Fight (assets/<ns>/animmodels/animations/biped/**.json): {"animation": [{name, time[], transform[][16]}]},
матрицы 4×4 построчно (перенос в [3], [7], [11]) — ПОЛНЫЕ локальные матрицы кости относительно родителя (как в armature).
Первый элемент массива (Coord, если он есть, иначе Root) записан в осях Blender (Z вверх) — EF поворачивает его на −90° вокруг X
(BLENDER_TO_MINECRAFT_COORD); остальные кости уже в своих локальных осях. Coord — смещение сущности (root motion), Root — таз.
Интерполяция EF между ключами: перенос — линейно, поворот — slerp (как здесь).
Оси результата: вперёд −Z, вверх +Y, вправо от персонажа +X (как у наших боссов в превью); единица — блок.

Общие «сигналы» скелета (одинаково для эталона и наших анимаций, см. anim_style_check.py): таз, линия плеч, линия бёдер,
голова, стопы, кисти, остриё оружия — в осях персонажа, длины в долях длины ноги L (EF: 0.75 бл.; Мартин: 12 ед.).
"""
import glob
import json
import math
import os
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
C_BLENDER = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)   # −90° вокруг X: (x, y, z) → (x, z, −y)
LEG_EF = 0.375 * 2                     # бедро + голень biped EF, блоки
FOOT_EF = 0.375
BLADE_EF = 1.0                         # длина «оружия» для острия эталона (бл.): вдоль оси Tool, см. TOOL_AXIS
TOOL_AXIS = np.array([0.0, 0.0, -1.0])  # ось клинка в осях Tool_R (проверено по выпадам и стойкам, см. spec)


# ---------------------------------------------------------------- источники
def ref_dir():
    return os.environ.get('EF_REF_DIR', '')


def find_jars(extra=None):
    """{'ef': путь, 'nf': путь, 'wom': путь} — что нашлось (libs/ и EF_REF_DIR / extra)."""
    dirs = [d for d in (extra, ref_dir(), os.path.join(ROOT, 'libs')) if d]
    pats = {'ef': ('epicfight-1.20.1-*.jar', 'epic-fight-*.jar'), 'nf': ('*Nightfall*.jar', '*nightfall*.jar'),
            'wom': ('WeaponsOfMiracles*.jar', '*wom*.jar')}
    out = {}
    for k, ps in pats.items():
        for d in dirs:
            for p in ps:
                hits = sorted(glob.glob(os.path.join(d, p)))
                if hits and k not in out:
                    out[k] = hits[-1]
    return out


class Jar:
    def __init__(self, path):
        self.path = path
        self.z = zipfile.ZipFile(path)
        self.names = set(self.z.namelist())

    def json(self, name):
        return json.loads(self.z.read(name).decode('utf-8', 'replace'))

    def has(self, name):
        return name in self.names


_ARM = None


def armature(jars):
    """Иерархия biped EF: {кость: родитель}, порядок обхода, локальные матрицы покоя (корень — уже в осях MC)."""
    global _ARM
    if _ARM is None:
        j = Jar(jars['ef'])
        h = j.json('assets/epicfight/animmodels/entity/biped.json')['armature']['hierarchy']
        parent, order, bind = {}, [], {}

        def walk(n, p, first):
            m = np.array(n['transform'], float).reshape(4, 4)
            bind[n['name']] = C_BLENDER @ m if first else m
            parent[n['name']] = p
            order.append(n['name'])
            for c in n['children']:
                walk(c, n['name'], False)
        for n in h:
            walk(n, None, True)
        _ARM = (parent, order, bind)
    return _ARM


# ---------------------------------------------------------------- кватернионы
def m2q(R):
    t = R[0, 0] + R[1, 1] + R[2, 2]
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        q = [0.25 * s, (R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s]
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        q = [(R[2, 1] - R[1, 2]) / s, 0.25 * s, (R[0, 1] + R[1, 0]) / s, (R[0, 2] + R[2, 0]) / s]
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        q = [(R[0, 2] - R[2, 0]) / s, (R[0, 1] + R[1, 0]) / s, 0.25 * s, (R[1, 2] + R[2, 1]) / s]
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        q = [(R[1, 0] - R[0, 1]) / s, (R[0, 2] + R[2, 0]) / s, (R[1, 2] + R[2, 1]) / s, 0.25 * s]
    q = np.array(q)
    return q / np.linalg.norm(q)


def q2m(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def slerp(a, b, k):
    d = float(a @ b)
    if d < 0:
        b, d = -b, -d
    if d > 0.9995:
        q = a + (b - a) * k
        return q / np.linalg.norm(q)
    th = math.acos(d)
    return (math.sin((1 - k) * th) * a + math.sin(k * th) * b) / math.sin(th)


def _ortho(M):
    """Матрицы из Blender бывают со слабым масштабом — для кватерниона берём чистый поворот."""
    U, _, Vt = np.linalg.svd(M)
    R = U @ Vt
    if np.linalg.det(R) < 0:
        U[:, -1] *= -1
        R = U @ Vt
    return R


# ---------------------------------------------------------------- анимация
class EFAnim:
    def __init__(self, jars, member, jar_key=None, path=None):
        """member — путь внутри jar; path — наш файл анимации EF (assets/pohsmp_core/animmodels/...), jar не нужен."""
        if path:
            d = json.load(open(path, encoding='utf-8'))
            self._init(d, path, None, None)
            dm = os.path.join(os.path.dirname(path), 'data', os.path.basename(path))
            if os.path.exists(dm):
                for t in json.load(open(dm, encoding='utf-8')).get('trail_effects', []):
                    self.trail.append((float(t['start_time']), float(t['end_time']), t.get('joint', 'Tool_R')))
            return
        jk = jar_key or next(k for k, p in jars.items() if Jar(p).has(member))
        d = Jar(jars[jk]).json(member)
        self._init(d, member, jk, jars)

    def _init(self, d, member, jk, jars):
        self.name = os.path.splitext(os.path.basename(member))[0]
        self.member, self.src = member, jk
        self.tracks = {}
        self.length = 0.0
        for i, a in enumerate(d['animation']):
            ts = np.array(a['time'], float)
            ms = [np.array(m, float).reshape(4, 4) for m in a['transform']]
            if i == 0:
                ms = [C_BLENDER @ m for m in ms]
            qs = [m2q(_ortho(m[:3, :3])) for m in ms]
            for k in range(1, len(qs)):               # одна полусфера — slerp без проворотов
                if qs[k] @ qs[k - 1] < 0:
                    qs[k] = -qs[k]
            self.tracks[a['name']] = (ts, np.array(qs), np.array([m[:3, 3] for m in ms]))
            self.length = max(self.length, float(ts[-1]))
        # окно удара — trail_effects из data/<имя>.json (если есть у источника)
        self.trail = []
        if jars is None:
            return
        dm = os.path.join(os.path.dirname(member), 'data', os.path.basename(member))
        j = Jar(jars[jk])
        if j.has(dm):
            try:
                for t in j.json(dm).get('trail_effects', []):
                    self.trail.append((float(t['start_time']), float(t['end_time']), t.get('joint', 'Tool_R')))
            except Exception:
                pass

    def local(self, name, t, bind):
        tr = self.tracks.get(name)
        if tr is None:
            return bind.get(name, np.eye(4)) if name != 'Coord' else np.eye(4)
        ts, qs, ps = tr
        if t <= ts[0]:
            q, p = qs[0], ps[0]
        elif t >= ts[-1]:
            q, p = qs[-1], ps[-1]
        else:
            i = int(np.searchsorted(ts, t)) - 1
            k = (t - ts[i]) / max(1e-9, ts[i + 1] - ts[i])
            q, p = slerp(qs[i], qs[i + 1], k), ps[i] * (1 - k) + ps[i + 1] * k
        M = np.eye(4)
        M[:3, :3] = q2m(q)
        M[:3, 3] = p
        return M

    def world(self, jars, t):
        """{кость: 4×4 в мире}; Coord (root motion) добавлен к Root как перенос."""
        parent, order, bind = armature(jars)
        W = {}
        coord = self.local('Coord', t, bind)
        for n in order:
            L = self.local(n, t, bind)
            W[n] = (W[parent[n]] @ L) if parent[n] else L.copy()
            if not parent[n]:
                W[n][:3, 3] += coord[:3, 3]
        W['Coord'] = coord
        return W


def ef_signals(jars, an, t):
    """Сигналы скелета эталона в момент t (единицы — доли длины ноги)."""
    W = an.world(jars, t)
    L = LEG_EF

    def P(n, v=(0, 0, 0)):
        return (W[n] @ np.array([v[0], v[1], v[2], 1.0]))[:3] / L

    def axis(n, v):
        return W[n][:3, :3] @ np.asarray(v, float)
    tool = P('Tool_R')
    tipw = (W['Tool_R'] @ np.append(TOOL_AXIS * BLADE_EF, 1.0))[:3] / L
    return {
        'pelvis': P('Root'), 'chest': P('Chest'), 'head': P('Head'),
        'sh_r': P('Arm_R'), 'sh_l': P('Arm_L'), 'hip_r': P('Thigh_R'), 'hip_l': P('Thigh_L'),
        'foot_r': P('Leg_R', (0, FOOT_EF, 0)), 'foot_l': P('Leg_L', (0, FOOT_EF, 0)),
        'hand_r': P('Tool_R'), 'hand_l': P('Tool_L'), 'tool': tool, 'tip': tipw,
        'head_fwd': axis('Head', (0, 0, -1)), 'chest_fwd': axis('Chest', (0, 0, -1)), 'root_fwd': axis('Root', (0, 0, -1)),
        'coord': W['Coord'][:3, 3] / L,
    }


def list_anims(jars, key, sub='animmodels/animations/biped'):
    j = Jar(jars[key])
    return sorted(n for n in j.names if '/' + sub + '/' in '/' + n and n.endswith('.json') and '/data/' not in n and '/pov/' not in n)


# Набор эталонов для разбора (имя в отчёте → (источник, файл)). Тяжёлое двуручное оружие — ближе всего к Мартину.
REF_SET = {
    'EF longsword_auto1': ('ef', 'assets/epicfight/animmodels/animations/biped/combat/longsword_auto1.json', 'light'),
    'EF longsword_auto2': ('ef', 'assets/epicfight/animmodels/animations/biped/combat/longsword_auto2.json', 'light'),
    'EF longsword_auto3': ('ef', 'assets/epicfight/animmodels/animations/biped/combat/longsword_auto3.json', 'light'),
    'EF greatsword_auto1': ('ef', 'assets/epicfight/animmodels/animations/biped/combat/greatsword_auto1.json', 'heavy'),
    'EF greatsword_auto2': ('ef', 'assets/epicfight/animmodels/animations/biped/combat/greatsword_auto2.json', 'heavy'),
    'EF mob_longsword1': ('ef', 'assets/epicfight/animmodels/animations/biped/combat/mob_longsword1.json', 'light'),
    'EF mob_longsword2': ('ef', 'assets/epicfight/animmodels/animations/biped/combat/mob_longsword2.json', 'light'),
    'NF ng_great_auto1': ('nf', 'assets/efn/animmodels/animations/biped/ng_greatsword/ng_great_auto1.json', 'heavy'),
    'NF ng_great_auto2': ('nf', 'assets/efn/animmodels/animations/biped/ng_greatsword/ng_great_auto2.json', 'heavy'),
    'NF ng_great_auto3': ('nf', 'assets/efn/animmodels/animations/biped/ng_greatsword/ng_great_auto3.json', 'heavy'),
    'NF broadblade_auto1': ('nf', 'assets/efn/animmodels/animations/biped/broadblade/broadblade_auto1.json', 'heavy'),
    'NF broadblade_auto2': ('nf', 'assets/efn/animmodels/animations/biped/broadblade/broadblade_auto2.json', 'heavy'),
    'NF broadblade_auto3': ('nf', 'assets/efn/animmodels/animations/biped/broadblade/broadblade_auto3.json', 'heavy'),
    'NF nf_sword_auto1': ('nf', 'assets/efn/animmodels/animations/biped/nf_sword/nf_sword_auto1.json', 'light'),
    'NF nf_sword_auto2': ('nf', 'assets/efn/animmodels/animations/biped/nf_sword/nf_sword_auto2.json', 'light'),
    'WoM ruine_auto_1': ('wom', 'assets/wom/animmodels/animations/biped/combat/ruine_auto_1.json', 'heavy'),
    'WoM ruine_auto_2': ('wom', 'assets/wom/animmodels/animations/biped/combat/ruine_auto_2.json', 'heavy'),
    'WoM ruine_auto_3': ('wom', 'assets/wom/animmodels/animations/biped/combat/ruine_auto_3.json', 'heavy'),
    'WoM torment_auto_1': ('wom', 'assets/wom/animmodels/animations/biped/combat/torment_auto_1.json', 'heavy'),
    'WoM torment_auto_2': ('wom', 'assets/wom/animmodels/animations/biped/combat/torment_auto_2.json', 'heavy'),
    'WoM napoleon_auto_1': ('wom', 'assets/wom/animmodels/animations/biped/combat/napoleon_auto_1.json', 'heavy'),
}
# уколы (дуга клинка < 90°): у Мартина — martin_thrust
REF_THRUST = {
    'EF longsword_liechtenauer_auto3': ('ef', 'assets/epicfight/animmodels/animations/biped/combat/longsword_liechtenauer_auto3.json', 'thrust'),
    'EF mob_spear_onehand': ('ef', 'assets/epicfight/animmodels/animations/biped/combat/mob_spear_onehand.json', 'thrust'),
    'EF mob_spear_twohand3': ('ef', 'assets/epicfight/animmodels/animations/biped/combat/mob_spear_twohand3.json', 'thrust'),
    'EF spear_dash': ('ef', 'assets/epicfight/animmodels/animations/biped/combat/spear_dash.json', 'thrust'),
    'EF spear_onehand_auto': ('ef', 'assets/epicfight/animmodels/animations/biped/combat/spear_onehand_auto.json', 'thrust'),
    'WoM moonless_auto_1': ('wom', 'assets/wom/animmodels/animations/biped/combat/moonless_auto_1.json', 'thrust'),
    'WoM moonless_auto_3': ('wom', 'assets/wom/animmodels/animations/biped/combat/moonless_auto_3.json', 'thrust'),
}
REF_IDLE = {
    'EF idle': ('ef', 'assets/epicfight/animmodels/animations/biped/living/idle.json'),
    'EF hold_greatsword': ('ef', 'assets/epicfight/animmodels/animations/biped/living/hold_greatsword.json'),
    'EF hold_longsword': ('ef', 'assets/epicfight/animmodels/animations/biped/living/hold_longsword.json'),
    'NF ng_great_idle': ('nf', 'assets/efn/animmodels/animations/biped/ng_greatsword/ng_great_idle.json'),
    'NF broadblade_idle': ('nf', 'assets/efn/animmodels/animations/biped/broadblade/broadblade_idle.json'),
    'WoM ruine_idle': ('wom', 'assets/wom/animmodels/animations/biped/living/ruine_idle.json'),
}


def load_set(jars, which):
    out = {}
    for k, (src, mem, *cls) in which.items():
        if src in jars and Jar(jars[src]).has(mem):
            out[k] = EFAnim(jars, mem, src)
            out[k].cls = cls[0] if cls else 'idle'
    return out
