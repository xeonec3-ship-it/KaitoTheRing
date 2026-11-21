#!/usr/bin/env python3
"""
Анимации Epic Fight для огненного меча-хлыста «Раскалённые угли» (T14).

Формат сверен по Epic Fight 20.14.16/20.14.17 (forge 1.20.1), класс yesman.epicfight.api.asset.JsonAssetLoader:
  * файл анимации — assets/<мод>/animmodels/animations/<id>.json, где <id> — то, что передано в
    AnimationBuilder.nextAccessor("<id>", ...) (у нас "biped/ember/last_heat" и т. п.);
  * {"animation": [{"name": <сустав>, "time": [сек...], "transform": [[16 чисел]...]}, ...]}, без ключа "format"
    (= MATRIX): каждая матрица 4×4 построчно (перенос — в элементах 3, 7, 11) — ЛОКАЛЬНАЯ поза сустава относительно
    родителя, в тех же осях, что и скелет animmodels/entity/biped.json. Загрузчик транспонирует матрицу, у первого сустава
    (Root) домножает слева на поворот −90° вокруг X (Blender Z-вверх -> Minecraft Y-вверх) и сам вычитает позу привязки:
    JointTransform = inverse(bindLocal) · keyframe. Если первым идёт сустав "Coord" (его нет в скелете), загрузчик берёт его
    как движение сущности (свойство COORD у ActionAnimation/AttackAnimation), а Root уже не поворачивает — тогда Root пишется
    сразу в осях Minecraft. Мы так и делаем: Coord с нулевым переносом, иначе EF превратил бы сдвиг таза по горизонтали
    в перемещение игрока (ActionAnimation.correctRootJoint). Позы считаются в осях Blender: +X — вправо от персонажа,
    +Y — вперёд (куда он смотрит), +Z — вверх, 1 = блок, подошвы на z = 0;
  * между ключами Epic Fight интерполирует сам (перенос — линейно, поворот — slerp); мы пишем ключ на каждый тик (0.05 с)
    уже сглаженной кривой;
  * доп. файл <папка>/data/<имя>.json (клиент): "trail_effects" — след клинка за суставом Tool_R.

Скелет biped (20 суставов): Root (таз) -> Thigh_R/L (бедро) -> Leg_R/L (голень), Knee_R/L (вспомогательный, только сдвиг);
Root -> Torso -> Chest -> Head, Shoulder_R/L -> Arm_R/L (плечо) -> Hand_R/L (предплечье) -> Tool_R/L (хват: предмет
смотрит по −Z этого сустава), Elbow_R/L (вспомогательный, только сдвиг). Вспомогательные Knee/Elbow в ванильных анимациях
не вращаются, а сдвигаются по своей −Z пропорционально сгибу — повторяем (подобрано по sweeping_edge, sword_auto1 и др.).

Позы задаются ключами (тик -> параметры, каждый ключ наследует предыдущий):
  root  — смещение таза (x вправо, y вперёд, z вверх) и yaw/pitch/roll в градусах (yaw + — поворот вправо, по часовой
          сверху; pitch + — наклон вперёд; roll + — крен вправо);
  torso, chest, head — (pitch, yaw, roll) относительно родителя;
  hand_r / hand_l — точка хвата (сустав Tool), куда смотрит клинок (blade) и его режущая кромка (edge), куда отводить
          локоть (pole); руки ставятся обратной кинематикой (плечо 0.30, предплечье 0.273);
          hand_l может перехватить ту же рукоять: 'gw' (0..1, плавно) — вес перехвата, 'grip' — на сколько ниже правой кисти;
  foot_r / foot_l — точка подошвы и куда смотрит колено (pole); ноги — тоже обратной кинематикой (бедро 0.375,
          голень 0.386).
Кадр (frame) рук и ног: 'body' — поворачивается вместе с yaw таза (для вихря), 'world' — неподвижен (стойка «Последнего жара»).
Сглаживание — монотонный кубический сплайн (PCHIP, без перелётов); ключ с 'hit': True — удар: в него входим с ускорением
и сразу останавливаемся (клинок втыкается, а не «приземляется»).

Запуск:  python3 tools/gen_epicfight_anims.py
Пишет:   src/main/resources/assets/pohsmp_core/animmodels/animations/biped/ember/*.json (+ data/*.json — следы клинка)
         tools/ember_anims_preview.html (превью из tools/ember_anims_preview.template.html, читает те же JSON)
Тайминги, которые должен знать код (тик начала эффекта, фазы ударов), печатаются в конце и записаны в TIMING ниже —
их же держит ru.pohsmp.core.ember.EmberEpicFight.
"""
import copy
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'src', 'main', 'resources', 'assets', 'pohsmp_core', 'animmodels', 'animations', 'biped', 'ember')
TPS = 20

# ------------------------------------------------------------------ скелет biped Epic Fight (animmodels/entity/biped.json)
# (сустав, родитель, локальная матрица 4×4 построчно, оси Blender) — взято из epicfight 20.14.17, не меняется между версиями 20.x
BIND = [
    ('Root', None, [1.0, 0.0, 0.0, -5e-06, 0.0, 0.0, -1.0, 0.000946, 0.0, 1.0, 0.0, 0.763972, 0.0, 0.0, 0.0, 1.0]),
    ('Thigh_R', 'Root', [1.0, 0.0, 0.0, 0.124994, 0.0, -1.0, 1e-06, -0.002831, 0.0, 0.0, -1.0, -1.2e-05, 0.0, 0.0, 0.0, 1.0]),
    ('Leg_R', 'Thigh_R', [1.0, 0.0, 1e-06, 0.0, 0.0, 1.0, 0.0, 0.37472, -1e-06, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Knee_R', 'Thigh_R', [1.0, 0.0, 0.0, 0.0, 0.0, 1e-06, -1.0, 0.37472, 0.0, 1.0, 1e-06, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Thigh_L', 'Root', [1.0, 0.0, 0.0, -0.125006, 0.0, -1.0, 1e-06, -0.002831, 0.0, 0.0, -1.0, -1.2e-05, 0.0, 0.0, 0.0, 1.0]),
    ('Leg_L', 'Thigh_L', [1.0, 0.0, 1e-06, 0.0, 0.0, 1.0, 0.0, 0.37472, -1e-06, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Knee_L', 'Thigh_L', [1.0, 0.0, 0.0, 0.0, 0.0, 1e-06, -1.0, 0.37472, 0.0, 1.0, 1e-06, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Torso', 'Root', [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.05, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Chest', 'Torso', [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.3, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Head', 'Chest', [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.4, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Shoulder_R', 'Chest', [0.0, 0.952114, 0.305743, 0.0, 0.0, -0.305743, 0.952114, 0.4, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Arm_R', 'Shoulder_R', [0.0, 0.0, -1.0, 0.0, 0.952114, 0.305743, 0.0, 0.39386, 0.305743, -0.952114, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Hand_R', 'Arm_R', [1.0, 0.0, 0.0, 0.0, 0.0, 0.993938, 0.109947, 0.3, 0.0, -0.109947, 0.993937, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Tool_R', 'Hand_R', [1.0, 0.0, 0.0, 0.0, 0.0, -0.999836, 0.018122, 0.272858, 0.0, -0.018122, -0.999244, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Elbow_R', 'Arm_R', [-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.3, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Shoulder_L', 'Chest', [0.0, -0.952114, -0.305743, 0.0, 0.0, -0.305743, 0.952114, 0.4, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Arm_L', 'Shoulder_L', [0.0, 0.0, 1.0, 0.0, -0.952114, 0.305743, 0.0, 0.39386, -0.305743, -0.952114, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Hand_L', 'Arm_L', [1.0, 0.0, 0.0, 0.0, 0.0, 0.993937, 0.109947, 0.3, 0.0, -0.109947, 0.993937, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Tool_L', 'Hand_L', [1.0, 0.0, 0.0, 0.0, 0.0, -0.999836, 0.018122, 0.272858, 0.0, -0.018122, -0.999247, 0.0, 0.0, 0.0, 0.0, 1.0]),
    ('Elbow_L', 'Arm_L', [-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.3, 0.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]),
]
NAMES = [b[0] for b in BIND]
PARENT = {b[0]: b[1] for b in BIND}
LOCAL = {b[0]: np.array(b[2], dtype=float).reshape(4, 4) for b in BIND}
BW = {}
for _n in NAMES:
    BW[_n] = LOCAL[_n] if PARENT[_n] is None else BW[PARENT[_n]] @ LOCAL[_n]

UPPER_ARM = float(LOCAL['Hand_R'][1, 3])                     # 0.30
FOREARM = float(LOCAL['Tool_R'][1, 3])                       # 0.273: локоть -> хват
THIGH = float(LOCAL['Leg_R'][1, 3])                          # 0.375
SHIN = float(BW['Leg_R'][2, 3])                              # 0.386: колено -> подошва
BLADE = 1.0                                                  # длина клинка от хвата до острия (как коллайдер меча EF, ~1.05)


# ------------------------------------------------------------------ математика
def _n(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=float)


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=float)


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)


def ypr(yaw=0.0, pitch=0.0, roll=0.0):
    """yaw + — вправо (по часовой сверху), pitch + — наклон вперёд, roll + — крен вправо; градусы."""
    return rz(-math.radians(yaw)) @ rx(-math.radians(pitch)) @ ry(math.radians(roll))


def mat(r, p):
    m = np.eye(4)
    m[:3, :3] = r
    m[:3, 3] = p
    return m


def perp(v, u):
    """Часть v, перпендикулярная единичному u (нормированная)."""
    return _n(np.asarray(v, float) - np.dot(v, u) * u)


def around(rel, r, z, ox=0.0, oy=0.0):
    """Точка в кадре тела на угле rel (градусы от «вперёд», + — вправо), на расстоянии r от оси, высоте z."""
    a = math.radians(rel)
    return (ox + math.sin(a) * r, oy + math.cos(a) * r, z)


def dir_at(rel, elev=0.0):
    """Направление на угле rel (+ вправо) и возвышении elev (градусы)."""
    a, e = math.radians(rel), math.radians(elev)
    return (math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e))


def ik(s, g, a, b, pole):
    """Двухзвенник: начало s, цель g, длины a, b; средний сустав уводится к pole. -> (средний сустав, конец, недотянулось)."""
    s, g = np.asarray(s, float), np.asarray(g, float)
    d_vec = g - s
    d = float(np.linalg.norm(d_vec))
    short = max(0.0, d - (a + b))
    dn = _n(d_vec)
    d = min(max(d, abs(a - b) + 1e-3), a + b - 1e-4)
    g = s + dn * d
    cos_a = (a * a + d * d - b * b) / (2 * a * d)
    sin_a = math.sqrt(max(0.0, 1 - cos_a * cos_a))
    side = perp(np.asarray(pole, float), dn)
    e = s + a * (cos_a * dn + sin_a * side)
    return e, g, short


def frame_yz(y, z):
    """Поворот с осями y и z (z ортогонализуется к y), x = y × z."""
    y = _n(y)
    z = perp(z, y)
    x = np.cross(y, z)
    return np.column_stack([x, y, z])


def knee_shift(deg):
    """Сдвиг вспомогательного Knee по сгибу (подобран по ванильным анимациям EF)."""
    pts = [(0, 0), (24.6, 0.003), (36.1, 0.02), (52.3, 0.046), (65.8, 0.067), (104, 0.105), (150, 0.13)]
    for (a0, v0), (a1, v1) in zip(pts, pts[1:]):
        if deg <= a1:
            return v0 + (v1 - v0) * (deg - a0) / (a1 - a0)
    return pts[-1][1]


def elbow_shift(deg):
    return 0.00164 * deg


# ------------------------------------------------------------------ поза -> мировые матрицы суставов
def pose_world(P):
    """P — параметры позы (см. докстринг). -> (dict сустав -> мировая 4×4 в осях Blender, info)."""
    info = {'short': []}
    W = {}
    rp = P['root']
    yaw = rp.get('yaw', 0.0)
    root_d = ypr(yaw, rp.get('pitch', 0.0), rp.get('roll', 0.0))
    W['Root'] = mat(root_d @ BW['Root'][:3, :3], BW['Root'][:3, 3] + np.asarray(rp.get('pos', (0, 0, 0)), float))
    body = rz(-math.radians(yaw))
    bpos = np.array([rp.get('pos', (0, 0, 0))[0], rp.get('pos', (0, 0, 0))[1], 0.0])

    def to_model(pt, frame):
        pt = np.asarray(pt, float)
        return body @ pt + bpos if frame == 'body' else pt

    def dir_model(v, frame):
        return body @ np.asarray(v, float) if frame == 'body' else np.asarray(v, float)

    def child(name, rot):
        par = W[PARENT[name]]
        W[name] = mat(rot, par[:3, :3] @ LOCAL[name][:3, 3] + par[:3, 3])

    t = ypr(*_ypr3(P.get('torso')))
    c = ypr(*_ypr3(P.get('chest')))
    h = ypr(*_ypr3(P.get('head')))
    child('Torso', root_d @ t @ BW['Torso'][:3, :3])
    child('Chest', root_d @ t @ c @ BW['Chest'][:3, :3])
    child('Head', root_d @ t @ c @ h @ BW['Head'][:3, :3])
    for side in 'RL':
        W['Shoulder_' + side] = W['Chest'] @ LOCAL['Shoulder_' + side]

    # ---- руки
    hands = {}
    for side in 'RL':
        hp = P['hand_' + side.lower()]
        sh = (W['Shoulder_' + side] @ LOCAL['Arm_' + side])[:3, 3]
        fr = hp.get('frame', 'body')
        g = to_model(hp['pos'], fr)
        aw = float(hp.get('aw', 0.0))
        if aw > 0:                                         # от плеча: aim = (угол вокруг тела, возвышение, доля длины руки)
            rel, elev, ext = hp['aim']
            g = g * (1 - aw) + (sh + dir_model(dir_at(rel, elev), fr) * ext * (UPPER_ARM + FOREARM)) * aw
        blade = _n(dir_model(hp.get('blade', (0, 1, 0)), fr))
        edge = dir_model(hp.get('edge', (0, 0, 1)), fr)
        gw = float(hp.get('gw', 0.0))
        if side == 'L' and gw > 0:                         # левая рука перехватывает ту же рукоять (ниже правой кисти)
            g = g * (1 - gw) + (hands['R']['g'] - hands['R']['blade'] * hp.get('grip', 0.13)) * gw
        pole = dir_model(hp.get('pole', (0.6 if side == 'R' else -0.6, -0.5, -0.6)), fr)
        e, g2, short = ik(sh, g, UPPER_ARM, FOREARM, sh + pole)
        if short > 0.01:
            info['short'].append(('hand_' + side, round(short, 3)))
        u, f = _n(e - sh), _n(g2 - e)
        bend_dir = f - np.dot(f, u) * u
        z_up = _n(bend_dir) if np.linalg.norm(bend_dir) > 1e-4 else -perp(pole, u)
        r_arm = frame_yz(u, z_up)
        x = r_arm[:, 0]
        r_hand = np.column_stack([x, f, np.cross(x, f)])
        W['Arm_' + side] = mat(r_arm, sh)
        W['Hand_' + side] = mat(r_hand, e)
        bend = math.degrees(math.acos(max(-1, min(1, float(np.dot(u, f))))))
        el = np.eye(4)
        el[2, 3] = -elbow_shift(bend)
        W['Elbow_' + side] = W['Arm_' + side] @ LOCAL['Elbow_' + side] @ el
        if side == 'L':                                    # в левой руке ничего нет: кисть по предплечью, как в привязке
            r_tool = r_hand @ LOCAL['Tool_L'][:3, :3]
        else:
            r_tool = frame_yz(edge, -blade)
        W['Tool_' + side] = mat(r_tool, g2)
        hands[side] = {'g': g2, 'blade': -r_tool[:, 2], 'edge': r_tool[:, 1]}

    # ---- ноги
    for side in 'RL':
        fp = P['foot_' + side.lower()]
        fr = fp.get('frame', 'body')
        hip = (W['Root'] @ LOCAL['Thigh_' + side])[:3, 3]
        target = to_model(fp['pos'], fr)
        pole = dir_model(fp.get('pole', (0.15 if side == 'R' else -0.15, 1.0, 0.0)), fr)
        k, f2, short = ik(hip, target, THIGH, SHIN, hip + pole)
        if short > 0.01:
            info['short'].append(('foot_' + side, round(short, 3)))
        u, f = _n(k - hip), _n(f2 - k)
        bd = f - np.dot(f, u) * u
        z_up = -_n(bd) if np.linalg.norm(bd) > 1e-4 else perp(pole, u)
        r_th = frame_yz(u, z_up)
        x = r_th[:, 0]
        W['Thigh_' + side] = mat(r_th, hip)
        W['Leg_' + side] = mat(np.column_stack([x, f, np.cross(x, f)]), k)
        bend = math.degrees(math.acos(max(-1, min(1, float(np.dot(u, f))))))
        kn = np.eye(4)
        kn[2, 3] = -knee_shift(bend)
        W['Knee_' + side] = W['Thigh_' + side] @ LOCAL['Knee_' + side] @ kn
    info['tip'] = hands['R']['g'] + hands['R']['blade'] * BLADE
    info['grip'] = hands['R']['g']
    return W, info


def _ypr3(v):
    if v is None:
        return (0.0, 0.0, 0.0)
    p, y, r = (list(v) + [0, 0, 0])[:3]
    return (y, p, r)        # в позах пишем (pitch, yaw, roll), ypr() принимает (yaw, pitch, roll)


def local_matrices(W):
    """Мировые -> локальные (то, что пишется в JSON)."""
    out = {}
    for n in NAMES:
        out[n] = W[n] if PARENT[n] is None else np.linalg.inv(W[PARENT[n]]) @ W[n]
    return out


# ------------------------------------------------------------------ ключи и сглаживание
def _merge(a, b):
    r = copy.deepcopy(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(r.get(k), dict):
            r[k] = _merge(r[k], v)
        else:
            r[k] = copy.deepcopy(v)
    return r


def _leaves(d, path=()):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from _leaves(v, path + (k,))
        else:
            yield path + (k,), v


def _get(d, path):
    for k in path:
        d = d[k]
    return d


def _set(d, path, v):
    for k in path[:-1]:
        d = d.setdefault(k, {})
    d[path[-1]] = v


def _pchip_slopes(x, y):
    h = np.diff(x)
    dl = np.diff(y) / h
    m = np.zeros_like(y)
    for i in range(1, len(y) - 1):
        if dl[i - 1] * dl[i] <= 0 or abs(dl[i - 1]) < 1e-12 or abs(dl[i]) < 1e-12:
            m[i] = 0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / dl[i - 1] + w2 / dl[i])
    m[0] = m[-1] = 0                   # из покоя и в покой
    return m


def sampler(keys):
    """keys: [(тик, параметры[, 'hit'])] -> функция тик -> полные параметры позы."""
    full, ticks, hits = [], [], []
    cur = {}
    for k in keys:
        cur = _merge(cur, k[1])
        full.append(cur)
        ticks.append(float(k[0]))
        hits.append(len(k) > 2 and k[2] == 'hit')
    ticks = np.array(ticks)
    assert all(np.diff(ticks) > 0), 'ключи должны идти по возрастанию тиков: %s' % ticks.tolist()
    paths = {}
    for i, f in enumerate(full):
        for p, v in _leaves(f):
            if isinstance(v, str):
                continue
            paths.setdefault(p, [None] * len(full))[i] = v
    curves = {}
    for p, vals in paths.items():
        # без значения в каком-то ключе (например, рука перешла на 'grip') — берём ближайшее заданное
        for i in range(len(vals)):
            if vals[i] is None:
                j = next((j for j in range(i - 1, -1, -1) if vals[j] is not None), None)
                j = j if j is not None else next(j for j in range(i + 1, len(vals)) if vals[j] is not None)
                vals[i] = vals[j]
        arr = np.array([np.atleast_1d(np.asarray(v, float)) for v in vals])
        ms = np.column_stack([_pchip_slopes(ticks, arr[:, c]) for c in range(arr.shape[1])])
        for i, hit in enumerate(hits):          # удар: входим с ускорением (касательная 2× секущей), выходим с нуля
            if hit and i > 0:
                ms[i] = 0
        curves[p] = (arr, ms, isinstance(vals[0], (list, tuple)))
    strings = {}
    for i, f in enumerate(full):
        for p, v in _leaves(f):
            if isinstance(v, str):
                strings.setdefault(p, []).append((ticks[i], v))

    def at(t):
        t = float(min(max(t, ticks[0]), ticks[-1]))
        i = int(np.searchsorted(ticks, t, side='right') - 1)
        i = min(i, len(ticks) - 2)
        h = ticks[i + 1] - ticks[i]
        s = (t - ticks[i]) / h
        out = {}
        for p, (arr, ms, vec) in curves.items():
            y0, y1 = arr[i], arr[i + 1]
            m0, m1 = ms[i] * h, ms[i + 1] * h
            if hits[i + 1]:
                m1 = 2.0 * (y1 - y0)
                m0 = np.minimum(np.abs(m0), np.abs(y1 - y0) * 0.5) * np.sign(y1 - y0)
            h00, h10, h01, h11 = 2 * s ** 3 - 3 * s ** 2 + 1, s ** 3 - 2 * s ** 2 + s, -2 * s ** 3 + 3 * s ** 2, s ** 3 - s ** 2
            v = h00 * y0 + h10 * m0 + h01 * y1 + h11 * m1
            _set(out, p, tuple(float(x) for x in v) if vec else float(v[0]))
        for p, lst in strings.items():
            val = [v for (tt, v) in lst if tt <= t + 1e-9]
            _set(out, p, val[-1] if val else lst[0][1])
        return out
    return at, ticks[-1]


# ------------------------------------------------------------------ общие позы
STANCE = {
    'root': {'pos': (0, 0, 0), 'yaw': 0, 'pitch': 0, 'roll': 0},
    'torso': (0, 0, 0), 'chest': (0, 0, 0), 'head': (0, 0, 0),
    'foot_r': {'pos': (0.14, 0.02, 0), 'frame': 'world'},
    'foot_l': {'pos': (-0.14, -0.02, 0), 'frame': 'world'},
}
# меч в правой руке у бедра, клинок вперёд-вниз (как стойка EF с мечом, чтобы переход в/из idle был мягким)
SWORD_REST_R = {'pos': (0.37, 0.12, 0.86), 'blade': (0.05, 0.85, -0.45), 'edge': (0, 0.45, 0.85), 'pole': (0.5, -0.6, -0.2), 'frame': 'world'}
FREE_REST_L = {'aim': (-20, -70, 0.9), 'aw': 0.0, 'pos': (-0.38, 0.04, 0.84), 'pole': (-0.5, -0.5, -0.3), 'gw': 0.0, 'grip': 0.13, 'frame': 'world'}


def P(**kw):
    return kw


# ------------------------------------------------------------------ «Последний жар» (форма меча)
LAST_HEAT_IMPACT = 7                 # тик анимации, когда клинок входит в землю = тик 0 fx/ember_last_heat.json
LAST_HEAT_WAVES = (4, 12, 20)        # волны fx (от его начала)
PLANT = np.array([0.0, 0.92, -0.22])  # острие в земле: 0.9 блока перед владельцем (код: position + look·0.9), на ~0.2 в глубину
PLANT_BLADE = _n((0.0, 0.30, -1.0))  # клинок почти отвесно, рукоять чуть к себе
PLANT_GRIP = PLANT - PLANT_BLADE * BLADE


def last_heat():
    W0 = LAST_HEAT_IMPACT
    up_r = {'pos': (0.03, -0.02, 1.84), 'blade': dir_at(0, 115), 'edge': (0, 1, 0.3), 'pole': (0.9, 0.1, 0.1), 'frame': 'world'}
    keys = [
        (0, _merge(STANCE, P(hand_r=SWORD_REST_R, hand_l=FREE_REST_L))),
        # 0-3: перехват двумя руками, замах над головой; корпус отклоняется назад, вес на правую ногу
        (2, P(root={'pos': (0.0, -0.03, 0.0), 'pitch': -4},
              chest=(-6, 0, 0), head=(-6, 0, 0),
              hand_r={'pos': (0.12, 0.18, 1.55), 'blade': dir_at(0, 70), 'edge': (0, -0.3, 1), 'pole': (0.8, -0.2, -0.3), 'frame': 'world'},
              hand_l={'pos': (-0.20, 0.25, 1.25), 'gw': 1.0, 'pole': (-0.8, -0.2, -0.3)})),
        (4, P(root={'pos': (0.0, -0.06, -0.01), 'pitch': -9},
              torso=(-4, 0, 0), chest=(-10, 0, 0), head=(-12, 0, 0),
              hand_r=up_r, hand_l={'gw': 1.0, 'pole': (-0.9, 0.1, 0.1)},
              foot_r={'pos': (0.15, 0.10, 0), 'frame': 'world'})),
        # 4-7: удар вниз: клинок описывает дугу вперёд и вонзается в землю; шаг правой вперёд, глубокий присед
        (5, P(root={'pos': (0.0, 0.02, -0.04), 'pitch': 6},
              torso=(8, 0, 0), chest=(4, 0, 0), head=(-6, 0, 0),
              hand_r={'pos': (0.04, 0.42, 1.62), 'blade': dir_at(0, 20), 'edge': (0, 0.4, -1), 'pole': (0.9, -0.1, -0.2), 'frame': 'world'},
              foot_r={'pos': (0.16, 0.30, 0.03), 'frame': 'world'})),
        (6, P(root={'pos': (0.0, 0.10, -0.17), 'pitch': 16},
              torso=(14, 0, 0), chest=(8, 0, 0), head=(-14, 0, 0),
              hand_r={'pos': (0.02, 0.62, 1.12), 'blade': (0.0, 0.62, -0.78), 'edge': (0, -0.8, -0.6), 'pole': (0.8, -0.3, -0.4), 'frame': 'world'},
              foot_r={'pos': (0.17, 0.40, 0), 'frame': 'world'}, foot_l={'pos': (-0.17, -0.24, 0), 'frame': 'world'})),
        (W0, P(root={'pos': (0.0, 0.14, -0.30), 'pitch': 22},
               torso=(18, 0, 0), chest=(10, 0, 0), head=(-22, 0, 0),
               hand_r={'pos': tuple(PLANT_GRIP + (0.02, 0, 0)), 'blade': tuple(PLANT_BLADE), 'edge': (0, -1, -0.3), 'pole': (0.9, -0.2, -0.3), 'frame': 'world'},
               hand_l={'gw': 1.0, 'pole': (-0.9, -0.2, -0.3)},
               foot_r={'pos': (0.18, 0.42, 0), 'frame': 'world'}, foot_l={'pos': (-0.18, -0.30, 0), 'frame': 'world'}), 'hit'),
        # отдача удара: тело проседает ещё на 4 см и возвращается
        (W0 + 2, P(root={'pos': (0.0, 0.15, -0.34), 'pitch': 25}, chest=(12, 0, 0), head=(-18, 0, 0))),
    ]
    # удержание: жар уходит в землю волнами; на каждой волне — толчок (плечи вниз, голова вздрагивает)
    for w in LAST_HEAT_WAVES:
        t = W0 + w
        if t - 1 > keys[-1][0]:
            keys.append((t - 1, P(root={'pos': (0.0, 0.14, -0.30), 'pitch': 22}, chest=(10, 0, 0), head=(-20, 0, 0))))
        keys.append((t, P(root={'pos': (0.0, 0.15, -0.335), 'pitch': 24}, chest=(13, 0, 2 if w == 12 else -2), head=(-14, 0, 0)), 'hit'))
        keys.append((t + 2, P(root={'pos': (0.0, 0.14, -0.305), 'pitch': 22}, chest=(10, 0, 0), head=(-19, 0, 0))))
    pull = W0 + LAST_HEAT_WAVES[-1] + 4          # 31: выдёргиваем клинок (последняя волна — на 27)
    keys += [
        (pull - 1, P(root={'pos': (0.0, 0.14, -0.30), 'pitch': 22}, chest=(10, 0, 0), head=(-18, 0, 0))),
        # клинок выходит из земли вверх по своей оси, корпус выпрямляется
        (pull + 2, P(root={'pos': (0.0, 0.08, -0.16), 'pitch': 10},
                     torso=(8, 0, 0), chest=(2, 0, 0), head=(-6, 0, 0),
                     hand_r={'pos': tuple(PLANT_GRIP - PLANT_BLADE * 0.42 + (0.03, -0.06, 0)), 'blade': (0.0, 0.42, -0.9), 'edge': (0, -1, -0.4), 'pole': (0.9, -0.2, -0.3), 'frame': 'world'},
                     foot_r={'pos': (0.18, 0.36, 0), 'frame': 'world'})),
        # клинок уходит в сторону и вниз — «остывает» у правого бедра, левая рука отпускает рукоять
        (pull + 5, P(root={'pos': (0.02, 0.03, -0.06), 'pitch': 3, 'yaw': 8},
                     torso=(3, 6, 0), chest=(0, 4, 0), head=(-2, -6, 0),
                     hand_r={'pos': (0.40, 0.30, 0.86), 'blade': (0.28, 0.75, -0.6), 'edge': (0.2, 0.55, 0.8), 'pole': (0.6, -0.6, -0.2), 'frame': 'world'},
                     hand_l=dict(FREE_REST_L, pos=(-0.40, 0.08, 0.80)),
                     foot_r={'pos': (0.16, 0.16, 0), 'frame': 'world'}, foot_l={'pos': (-0.16, -0.10, 0), 'frame': 'world'})),
        (40, _merge(STANCE, P(hand_r=SWORD_REST_R, hand_l=FREE_REST_L))),
    ]
    return keys


# ------------------------------------------------------------------ «Огненный вихрь» (форма хлыста)
VORTEX_LEAD = 3                      # тик анимации, когда начинается fx/ember_vortex.json (хлыст сзади, оборот за 8 тиков)
VORTEX_HIT = 4                       # удар fx (от его начала)


def whip_hand(rel, elev, ext, out=0.0, blade_elev=None, pole=None):
    """Рука с хлыстом от плеча: угол rel вокруг тела (+ вправо), возвышение elev, вытянута на долю ext; рукоять — наружу
    по руке (out — доворот, градусы), чуть вниз."""
    bl = dir_at(rel + out, elev - 10 if blade_elev is None else blade_elev)
    return {'aim': (rel, elev, ext), 'aw': 1.0, 'blade': bl, 'edge': (0, 0, 1), 'pole': pole or (0.4, -0.6, -0.6), 'frame': 'body'}


WHIP_REST_R = {'aim': (20, -70, 0.9), 'aw': 0.0, 'pos': (0.34, 0.20, 0.90), 'blade': (0.15, 0.7, -0.7), 'edge': (0, 0.7, 0.7), 'pole': (0.5, -0.6, -0.2), 'frame': 'body'}
FREE_BODY_L = dict(FREE_REST_L, frame='body')
STANCE_BODY = _merge(STANCE, P(foot_r={'pos': (0.14, 0.02, 0), 'frame': 'body'}, foot_l={'pos': (-0.14, -0.02, 0), 'frame': 'body'}))


def fire_vortex():
    """
    Полный оборот корпусом вправо (по часовой сверху, как идёт дуга хлыста в fx: сзади -> слева -> спереди -> справа).
    Голова дуги fx бежит с easeOut (тик 1: −61°, 2: 28°, 3: 96°, 4: 135°, 8: 180°), поэтому кисть раскручивается рывком
    в первые тики, а корпус докручивает оборот до 360° уже после удара и гасит инерцию шагом.
    """
    L = VORTEX_LEAD
    keys = [
        (0, _merge(STANCE_BODY, P(hand_r=WHIP_REST_R, hand_l=FREE_BODY_L))),
        # закрут: таз влево на 45°, грудь ещё на 28°, кисть с хлыстом у левого плеча (хлыст — за спиной); присед, широкая стойка
        (L, P(root={'pos': (0, 0, -0.12), 'yaw': -45, 'roll': 3},
              torso=(6, -10, 0), chest=(4, -18, 0), head=(-4, 22, 0),
              hand_r=whip_hand(-112, 10, 0.72, out=-30, pole=(0.3, -0.3, -0.9)),
              hand_l=dict(FREE_BODY_L, pos=(-0.30, -0.20, 0.95)),
              foot_r={'pos': (0.22, 0.06, 0), 'frame': 'body'}, foot_l={'pos': (-0.22, -0.06, 0), 'frame': 'body'})),
        # рывок: грудь раскручивается первой, рука выходит вперёд
        (L + 1, P(root={'pos': (0, 0, -0.10), 'yaw': 0, 'roll': 1},
                  torso=(5, -2, 0), chest=(3, 4, 0), head=(-4, 10, 0),
                  hand_r=whip_hand(-40, 6, 0.86, out=-10, pole=(0.3, -0.4, -0.85)))),
        (L + 2, P(root={'pos': (0, 0, -0.06), 'yaw': 38, 'roll': -3},
                  torso=(4, 6, -2), chest=(2, 12, -2), head=(-4, 0, 0),
                  hand_r=whip_hand(15, 2, 0.97, out=10, pole=(0.2, -0.5, -0.8)),
                  hand_l=dict(FREE_BODY_L, pos=(-0.42, -0.05, 0.98)))),
        # удар (тик 4 fx): рука вытянута вправо, тело кренится от хлыста, ступни чуть отрываются — разворот на носках
        (L + VORTEX_HIT, P(root={'pos': (0, 0, -0.03), 'yaw': 115, 'roll': -9},
                           torso=(2, 12, -4), chest=(0, 14, -4), head=(-2, -10, 0),
                           hand_r=whip_hand(68, -2, 0.99, out=12, pole=(0.0, -0.5, -0.9)),
                           hand_l=dict(FREE_BODY_L, pos=(-0.46, 0.05, 1.04)),
                           foot_r={'pos': (0.18, 0.04, 0.04), 'frame': 'body'}, foot_l={'pos': (-0.18, -0.04, 0.02), 'frame': 'body'})),
        (L + 6, P(root={'pos': (0, 0, -0.04), 'yaw': 200, 'roll': -9},
                  hand_r=whip_hand(72, -4, 0.99, out=16, pole=(0.0, -0.5, -0.9)),
                  foot_r={'pos': (0.20, 0.04, 0.02), 'frame': 'body'}, foot_l={'pos': (-0.20, -0.04, 0), 'frame': 'body'})),
        # хлыст замыкает круг (тик 8 fx), корпус докручивает
        (L + 8, P(root={'pos': (0, 0, -0.07), 'yaw': 270, 'roll': -6},
                  torso=(4, 8, -2), chest=(2, 10, -2), head=(-4, -6, 0),
                  hand_r=whip_hand(62, -12, 0.96, out=10, pole=(0.2, -0.5, -0.8)),
                  foot_r={'pos': (0.20, 0.04, 0), 'frame': 'body'})),
        # шаг: правая нога выносится в сторону, приземление в присед, рука опускает хлыст перед собой
        (L + 10, P(root={'pos': (0.05, 0.02, -0.15), 'yaw': 332, 'roll': 2},
                   torso=(10, 2, 0), chest=(6, 4, 0), head=(-10, -4, 0),
                   hand_r=whip_hand(38, -30, 0.9, out=5, blade_elev=-45, pole=(0.5, -0.4, -0.6)),
                   hand_l=dict(FREE_BODY_L, pos=(-0.40, 0.06, 0.86)),
                   foot_r={'pos': (0.34, 0.12, 0), 'frame': 'body'}, foot_l={'pos': (-0.16, -0.12, 0), 'frame': 'body'})),
        (L + 12, P(root={'pos': (0.06, 0.02, -0.17), 'yaw': 361, 'roll': 1},
                   hand_r=whip_hand(25, -45, 0.86, out=5, blade_elev=-60, pole=(0.5, -0.4, -0.6)))),
        (L + 16, P(root={'pos': (0.03, 0.01, -0.06), 'yaw': 361, 'roll': 0},
                   torso=(4, 0, 0), chest=(2, 0, 0), head=(-4, 0, 0),
                   hand_r=dict(WHIP_REST_R, pos=(0.36, 0.24, 0.92)),
                   foot_r={'pos': (0.20, 0.06, 0), 'frame': 'body'}, foot_l={'pos': (-0.15, -0.05, 0), 'frame': 'body'})),
        (22, _merge(STANCE_BODY, P(root={'pos': (0, 0, 0), 'yaw': 360, 'roll': 0}, hand_r=WHIP_REST_R, hand_l=FREE_BODY_L))),
    ]
    return keys


# ------------------------------------------------------------------ удары хлыстом (форма хлыста, серия из 3)
# Код хлёста (EmberBlade.lash) ведёт огненную дугу ±50° за 4 тика, начиная с попадания; направление берётся из TIMING ниже.
def whip1():
    """Хлёст справа налево на уровне груди: замах за правое плечо, рука проходит перед собой и уходит влево."""
    return [
        (0, _merge(STANCE_BODY, P(hand_r=WHIP_REST_R, hand_l=FREE_BODY_L))),
        (3, P(root={'pos': (0, -0.02, -0.04), 'yaw': 22, 'roll': 2}, torso=(0, 8, 0), chest=(-2, 16, 0), head=(-2, -30, 0),
              hand_r=whip_hand(125, 28, 0.9, out=25, pole=(0.3, -0.4, -0.9)),
              hand_l=dict(FREE_BODY_L, pos=(-0.30, 0.20, 1.00)),
              foot_r={'pos': (0.16, -0.04, 0), 'frame': 'body'}, foot_l={'pos': (-0.16, 0.10, 0), 'frame': 'body'})),
        (5, P(root={'pos': (0, 0.06, -0.08), 'yaw': 0, 'roll': -2}, torso=(6, 0, 0), chest=(4, -4, 0), head=(-6, 0, 0),
              hand_r=whip_hand(8, -4, 1.0, out=0, pole=(0.3, -0.5, -0.8)),
              hand_l=dict(FREE_BODY_L, pos=(-0.42, -0.02, 0.92)),
              foot_l={'pos': (-0.17, 0.22, 0), 'frame': 'body'}), 'hit'),
        (7, P(root={'pos': (0, 0.08, -0.08), 'yaw': -22, 'roll': -3}, torso=(8, -8, 0), chest=(6, -16, 0), head=(-6, 22, 0),
              hand_r=whip_hand(-55, -28, 0.85, out=-20, pole=(0.0, -0.4, -0.9)))),
        (12, _merge(STANCE_BODY, P(root={'pos': (0, 0.02, 0), 'yaw': 0, 'roll': 0}, hand_r=WHIP_REST_R, hand_l=FREE_BODY_L,
                                   foot_l={'pos': (-0.15, 0.08, 0), 'frame': 'body'}))),
    ]


def whip2():
    """Обратный хлёст слева направо снизу вверх: рука из-за левого бока уходит вправо-вверх."""
    return [
        (0, _merge(STANCE_BODY, P(hand_r=WHIP_REST_R, hand_l=FREE_BODY_L, foot_l={'pos': (-0.15, 0.08, 0), 'frame': 'body'}))),
        (3, P(root={'pos': (0, 0, -0.10), 'yaw': -30, 'roll': -2}, torso=(6, -10, 0), chest=(6, -16, 0), head=(-4, 36, 0),
              hand_r=whip_hand(-62, -35, 0.78, out=-30, pole=(0.4, -0.2, -0.9)),
              hand_l=dict(FREE_BODY_L, pos=(-0.36, -0.14, 0.92)),
              foot_r={'pos': (0.18, 0.10, 0), 'frame': 'body'})),
        (5, P(root={'pos': (0.02, 0.04, -0.05), 'yaw': 0, 'roll': 2}, torso=(2, 2, 0), chest=(0, 6, 0), head=(-4, 0, 0),
              hand_r=whip_hand(22, 2, 1.0, out=12, pole=(0.3, -0.5, -0.8)),
              hand_l=dict(FREE_BODY_L, pos=(-0.42, -0.06, 0.96))), 'hit'),
        (7, P(root={'pos': (0.04, 0.04, -0.02), 'yaw': 26, 'roll': 3}, torso=(-2, 10, 0), chest=(-4, 16, 0), head=(-6, -24, 0),
              hand_r=whip_hand(88, 38, 0.95, out=20, pole=(0.0, -0.3, -0.9)))),
        (12, _merge(STANCE_BODY, P(root={'pos': (0, 0, 0), 'yaw': 0, 'roll': 0}, hand_r=WHIP_REST_R, hand_l=FREE_BODY_L))),
    ]


def whip3():
    """Щелчок сверху: рука взлетает над головой, затем хлыст с шагом вперёд обрушивается вниз перед собой."""
    return [
        (0, _merge(STANCE_BODY, P(hand_r=WHIP_REST_R, hand_l=FREE_BODY_L))),
        (4, P(root={'pos': (0, -0.05, 0.0), 'pitch': -8, 'yaw': 6}, torso=(-4, 0, 0), chest=(-10, 6, 0), head=(-14, -4, 0),
              hand_r={'pos': (0.20, -0.10, 1.90), 'aw': 0.0, 'blade': dir_at(180, 40), 'edge': (0, 1, 0), 'pole': (0.9, 0.1, 0.0), 'frame': 'body'},
              hand_l=dict(FREE_BODY_L, pos=(-0.30, 0.22, 1.10)),
              foot_r={'pos': (0.15, -0.06, 0), 'frame': 'body'})),
        (6, P(root={'pos': (0, 0.10, -0.12), 'pitch': 14, 'yaw': 0}, torso=(10, 0, 0), chest=(8, 0, 0), head=(-14, 0, 0),
              hand_r={'pos': (0.12, 0.58, 1.30), 'blade': dir_at(4, -20), 'edge': (0, -0.2, 1), 'pole': (0.8, -0.2, -0.5), 'frame': 'body'},
              hand_l=dict(FREE_BODY_L, pos=(-0.42, -0.10, 0.88)),
              foot_r={'pos': (0.17, 0.36, 0), 'frame': 'body'}, foot_l={'pos': (-0.16, -0.18, 0), 'frame': 'body'}), 'hit'),
        (8, P(root={'pos': (0, 0.12, -0.16), 'pitch': 18}, torso=(12, 0, 0), chest=(10, 0, 0), head=(-16, 0, 0),
              hand_r={'pos': (0.16, 0.50, 0.92), 'blade': dir_at(10, -50), 'edge': (0, 0.4, 1), 'pole': (0.8, -0.3, -0.4), 'frame': 'body'})),
        (14, _merge(STANCE_BODY, P(root={'pos': (0, 0.06, 0), 'pitch': 0, 'yaw': 0}, hand_r=WHIP_REST_R, hand_l=FREE_BODY_L,
                                   foot_r={'pos': (0.15, 0.16, 0), 'frame': 'body'}))),
    ]


# ------------------------------------------------------------------ обычные удары формы меча (владелец 19.11: «сделай обычные, с вариациями»)
# Серия из четырёх разных ударов + удар на бегу + удар в прыжке. Клинок задаётся направлением от хвата (dir_at: угол вокруг тела,
# возвышение), режущая кромка — вектор edge (в осях тела: x вправо, y вперёд, z вверх).
def sword_hand(rel, elev, ext, b_rel, b_elev, edge, pole=(0.5, -0.5, -0.5)):
    return {'aim': (rel, elev, ext), 'aw': 1.0, 'blade': dir_at(b_rel, b_elev), 'edge': edge, 'pole': pole, 'frame': 'body'}


SWORD_REST_B = dict(SWORD_REST_R, frame='body')


def sword1():
    """Горизонтальный разрез справа налево на уровне груди: клинок отведён назад за правый бок, проходит перед собой, уходит влево."""
    return [
        (0, _merge(STANCE_BODY, P(hand_r=SWORD_REST_B, hand_l=FREE_BODY_L))),
        (3, P(root={'pos': (0, -0.03, -0.03), 'yaw': 28, 'roll': 2}, torso=(2, 10, 0), chest=(0, 18, 0), head=(-2, -32, 0),
              hand_r=sword_hand(95, 12, 0.8, 160, 8, (-0.2, 0, 1)), hand_l=dict(FREE_BODY_L, pos=(-0.32, 0.22, 1.02)),
              foot_r={'pos': (0.17, -0.06, 0), 'frame': 'body'}, foot_l={'pos': (-0.15, 0.12, 0), 'frame': 'body'})),
        (5, P(root={'pos': (0, 0.06, -0.06), 'yaw': 0, 'roll': -1}, torso=(6, 0, 0), chest=(2, -2, 0), head=(-4, 0, 0),
              hand_r=sword_hand(5, 6, 1.0, 0, 4, (-1, 0, 0.1)), hand_l=dict(FREE_BODY_L, pos=(-0.42, -0.02, 0.92)),
              foot_l={'pos': (-0.16, 0.22, 0), 'frame': 'body'}), 'hit'),
        (7, P(root={'pos': (0, 0.08, -0.07), 'yaw': -26, 'roll': -2}, torso=(8, -10, 0), chest=(4, -18, 0), head=(-4, 24, 0),
              hand_r=sword_hand(-70, -2, 0.85, -125, -6, (-0.2, -1, 0)))),
        (11, _merge(STANCE_BODY, P(root={'pos': (0, 0.02, 0), 'yaw': 0, 'roll': 0}, hand_r=SWORD_REST_B, hand_l=FREE_BODY_L,
                                   foot_l={'pos': (-0.15, 0.08, 0), 'frame': 'body'}))),
    ]


def sword2():
    """Обратный восходящий разрез: клинок из-за левого бедра снизу проходит вверх-вправо, корпус раскручивается."""
    return [
        (0, _merge(STANCE_BODY, P(hand_r=SWORD_REST_B, hand_l=FREE_BODY_L, foot_l={'pos': (-0.15, 0.08, 0), 'frame': 'body'}))),
        (3, P(root={'pos': (0, -0.02, -0.10), 'yaw': -32, 'roll': -2}, torso=(8, -12, 0), chest=(8, -18, 0), head=(-4, 36, 0),
              hand_r=sword_hand(-58, -38, 0.78, -110, -45, (0.6, 0.2, 0.8), pole=(0.4, -0.2, -0.9)),
              hand_l=dict(FREE_BODY_L, pos=(-0.36, -0.12, 0.92)), foot_r={'pos': (0.18, 0.10, 0), 'frame': 'body'})),
        (5, P(root={'pos': (0.02, 0.05, -0.05), 'yaw': 0, 'roll': 2}, torso=(2, 2, 0), chest=(0, 6, 0), head=(-4, 0, 0),
              hand_r=sword_hand(18, 12, 1.0, 20, 28, (0.6, 0.1, 0.8)), hand_l=dict(FREE_BODY_L, pos=(-0.42, -0.06, 0.96))), 'hit'),
        (7, P(root={'pos': (0.04, 0.05, -0.02), 'yaw': 28, 'roll': 3}, torso=(-2, 10, 0), chest=(-6, 16, 0), head=(-8, -24, 0),
              hand_r=sword_hand(80, 48, 0.92, 115, 68, (0.2, -0.3, 1)))),
        (12, _merge(STANCE_BODY, P(root={'pos': (0, 0, 0), 'yaw': 0, 'roll': 0}, hand_r=SWORD_REST_B, hand_l=FREE_BODY_L))),
    ]


def sword3():
    """Колющий выпад: клинок отводится к правому бедру остриём вперёд, затем выпад с шагом правой — укол перед собой."""
    tip_fwd = lambda pos: {'pos': pos, 'blade': dir_at(0, -4), 'edge': (0, 0, 1), 'pole': (0.6, -0.6, -0.3), 'frame': 'body'}
    return [
        (0, _merge(STANCE_BODY, P(hand_r=SWORD_REST_B, hand_l=FREE_BODY_L))),
        (3, P(root={'pos': (0, -0.06, -0.05), 'yaw': 18}, torso=(4, 8, 0), chest=(2, 10, 0), head=(-2, -16, 0),
              hand_r=tip_fwd((0.30, -0.12, 1.02)), hand_l=dict(FREE_BODY_L, pos=(-0.20, 0.30, 1.10)),
              foot_r={'pos': (0.16, -0.10, 0), 'frame': 'body'}, foot_l={'pos': (-0.15, 0.16, 0), 'frame': 'body'})),
        (5, P(root={'pos': (0, 0.20, -0.10), 'yaw': -6}, torso=(10, -4, 0), chest=(6, -4, 0), head=(-10, 4, 0),
              hand_r=tip_fwd((0.16, 0.62, 1.20)), hand_l=dict(FREE_BODY_L, pos=(-0.44, -0.18, 0.96)),
              foot_r={'pos': (0.17, 0.48, 0), 'frame': 'body'}, foot_l={'pos': (-0.16, -0.14, 0), 'frame': 'body'}), 'hit'),
        (7, P(root={'pos': (0, 0.22, -0.10), 'yaw': -6}, hand_r=tip_fwd((0.16, 0.66, 1.18)))),
        (12, _merge(STANCE_BODY, P(root={'pos': (0, 0.06, 0), 'yaw': 0}, hand_r=SWORD_REST_B, hand_l=FREE_BODY_L,
                                   foot_r={'pos': (0.15, 0.14, 0), 'frame': 'body'}))),
    ]


def sword4():
    """Добивающий удар сверху: клинок заносится за голову, шаг-подскок вперёд, рубящий удар вниз перед собой (завершает серию)."""
    return [
        (0, _merge(STANCE_BODY, P(hand_r=SWORD_REST_B, hand_l=FREE_BODY_L))),
        (4, P(root={'pos': (0, -0.04, 0.02), 'pitch': -8, 'yaw': 6}, torso=(-4, 0, 0), chest=(-10, 6, 0), head=(-14, -4, 0),
              hand_r={'pos': (0.16, -0.08, 1.88), 'blade': dir_at(180, 45), 'edge': (0, 1, 0.3), 'pole': (0.9, 0.1, 0.0), 'frame': 'body'},
              hand_l=dict(FREE_BODY_L, pos=(-0.28, 0.22, 1.12)), foot_r={'pos': (0.15, -0.06, 0), 'frame': 'body'})),
        (5, P(root={'pos': (0, 0.10, 0.06), 'pitch': -2}, hand_r={'pos': (0.14, 0.20, 1.92), 'blade': dir_at(0, 75), 'edge': (0, 1, -0.2),
              'pole': (0.9, 0.0, -0.1), 'frame': 'body'}, foot_r={'pos': (0.16, 0.20, 0.10), 'frame': 'body'})),
        (7, P(root={'pos': (0, 0.20, -0.14), 'pitch': 16}, torso=(12, 0, 0), chest=(8, 0, 0), head=(-14, 0, 0),
              hand_r={'pos': (0.12, 0.58, 1.22), 'blade': dir_at(2, -24), 'edge': (0, -0.2, -1), 'pole': (0.8, -0.2, -0.5), 'frame': 'body'},
              hand_l=dict(FREE_BODY_L, pos=(-0.42, -0.10, 0.88)),
              foot_r={'pos': (0.17, 0.40, 0), 'frame': 'body'}, foot_l={'pos': (-0.16, -0.18, 0), 'frame': 'body'}), 'hit'),
        (9, P(root={'pos': (0, 0.22, -0.18), 'pitch': 20}, torso=(14, 0, 0), chest=(10, 0, 0), head=(-16, 0, 0),
              hand_r={'pos': (0.16, 0.50, 0.92), 'blade': dir_at(8, -58), 'edge': (0, 0.4, -1), 'pole': (0.8, -0.3, -0.4), 'frame': 'body'})),
        (16, _merge(STANCE_BODY, P(root={'pos': (0, 0.08, 0), 'pitch': 0, 'yaw': 0}, hand_r=SWORD_REST_B, hand_l=FREE_BODY_L,
                                   foot_r={'pos': (0.15, 0.18, 0), 'frame': 'body'}))),
    ]


def sword_dash():
    """Удар на бегу: рывок вперёд с наклоном, клинок низко справа, широкий разрез справа налево на выходе из рывка."""
    return [
        (0, _merge(STANCE_BODY, P(root={'pos': (0, 0, -0.04), 'pitch': 10}, hand_r=SWORD_REST_B, hand_l=FREE_BODY_L,
                                  foot_r={'pos': (0.15, 0.22, 0.05), 'frame': 'body'}, foot_l={'pos': (-0.15, -0.20, 0), 'frame': 'body'}))),
        (3, P(root={'pos': (0, 0.20, -0.12), 'pitch': 16, 'yaw': 30}, torso=(10, 12, 0), chest=(6, 16, 0), head=(-14, -30, 0),
              hand_r=sword_hand(110, -10, 0.85, 165, -8, (-0.2, 0, 1)), hand_l=dict(FREE_BODY_L, pos=(-0.30, 0.30, 1.00)),
              foot_r={'pos': (0.18, 0.36, 0), 'frame': 'body'}, foot_l={'pos': (-0.16, -0.30, 0.06), 'frame': 'body'})),
        (5, P(root={'pos': (0, 0.42, -0.14), 'pitch': 12, 'yaw': 0}, torso=(10, 0, 0), chest=(4, -2, 0), head=(-10, 0, 0),
              hand_r=sword_hand(2, 0, 1.0, -4, -2, (-1, 0, 0.1)), hand_l=dict(FREE_BODY_L, pos=(-0.44, 0.0, 0.92)),
              foot_r={'pos': (0.18, 0.50, 0), 'frame': 'body'}, foot_l={'pos': (-0.16, -0.18, 0), 'frame': 'body'}), 'hit'),
        (7, P(root={'pos': (0, 0.46, -0.12), 'pitch': 8, 'yaw': -34}, torso=(8, -14, 0), chest=(4, -22, 0), head=(-6, 28, 0),
              hand_r=sword_hand(-85, -8, 0.85, -140, -10, (-0.2, -1, 0)))),
        (12, _merge(STANCE_BODY, P(root={'pos': (0, 0.10, 0), 'pitch': 0, 'yaw': 0}, hand_r=SWORD_REST_B, hand_l=FREE_BODY_L))),
    ]


def sword_air():
    """Удар в прыжке: ноги поджаты, корпус разворачивается, клинок рубит наискось вниз; приземление в присед."""
    tuck = {'foot_r': {'pos': (0.15, 0.10, 0.28), 'frame': 'body'}, 'foot_l': {'pos': (-0.15, -0.06, 0.22), 'frame': 'body'}}
    return [
        (0, _merge(STANCE_BODY, P(root={'pos': (0, 0, 0.0)}, hand_r=SWORD_REST_B, hand_l=FREE_BODY_L, **tuck))),
        (3, P(root={'pos': (0, -0.02, 0.04), 'pitch': -6, 'yaw': 40}, torso=(-4, 14, 0), chest=(-8, 20, 0), head=(-10, -34, 0),
              hand_r=sword_hand(120, 50, 0.9, 170, 40, (0, 0.3, 1)), hand_l=dict(FREE_BODY_L, pos=(-0.30, 0.24, 1.08)), **tuck)),
        (5, P(root={'pos': (0, 0.08, 0.0), 'pitch': 12, 'yaw': 0}, torso=(10, 0, 0), chest=(8, -4, 0), head=(-12, 0, 0),
              hand_r=sword_hand(10, -10, 1.0, 0, -30, (-0.8, 0, -0.6)), hand_l=dict(FREE_BODY_L, pos=(-0.42, -0.04, 0.94)), **tuck), 'hit'),
        (7, P(root={'pos': (0, 0.12, -0.20), 'pitch': 16, 'yaw': -14}, torso=(12, -6, 0), chest=(8, -10, 0), head=(-14, 10, 0),
              hand_r=sword_hand(-45, -45, 0.85, -60, -60, (-0.3, -0.6, -0.7)),
              foot_r={'pos': (0.17, 0.22, 0), 'frame': 'body'}, foot_l={'pos': (-0.17, -0.20, 0), 'frame': 'body'})),
        (12, _merge(STANCE_BODY, P(root={'pos': (0, 0.06, 0), 'pitch': 0, 'yaw': 0}, hand_r=SWORD_REST_B, hand_l=FREE_BODY_L))),
    ]


# ------------------------------------------------------------------ движение в форме хлыста без ударов (владелец 19.11)
# Петли (последний ключ = первый). Рука держит рукоять хлыста; сам хлыст рисует код (физика каната) — он висит, волочится, летит следом.
WHIP_HOLD_R = {'pos': (0.33, 0.12, 0.84), 'blade': (0.30, 0.05, -0.95), 'edge': (0, 1, 0.1), 'pole': (0.6, -0.5, -0.2), 'frame': 'body'}
WHIP_TRAIL_R = dict(WHIP_HOLD_R, blade=(0.25, -0.75, -0.6), edge=(0, -0.6, 0.8))   # при движении рукоять смотрит назад-вниз — хлыст тянется за игроком


def whip_idle():
    """Стойка с хлыстом: рука с рукоятью опущена чуть вбок и вперёд, кисть медленно покачивает хлыстом. 3 с.
    Эталон Epic Fight (21.11): вполоборота (таз вправо 32°, голова на цель), правая нога впереди, один вдох за петлю (3 с)."""
    base = _merge(STANCE_BODY, P(hand_r=WHIP_HOLD_R, hand_l=FREE_BODY_L, foot_r={'pos': (0.16, 0.17, 0), 'frame': 'body'},
                                 foot_l={'pos': (-0.15, -0.15, 0), 'frame': 'body'}, root={'pos': (0, 0, -0.01), 'yaw': 32},
                                 head=(0, -28, 0)))
    sway = lambda dx, dy, dz: dict(WHIP_HOLD_R, pos=(0.33 + dx, 0.12 + dy, 0.84 + dz))
    return [
        (0, base),
        (15, P(chest=(-0.8, 1, 0), head=(-0.5, -29.5, 0), root={'pos': (0, 0, -0.018), 'yaw': 33}, hand_r=sway(0.03, 0.06, 0.02))),
        (30, P(chest=(-1.5, 0, 0), head=(-1, -28, 0), root={'pos': (0, 0, -0.025), 'yaw': 32}, hand_r=sway(-0.02, -0.03, -0.01))),
        (45, P(chest=(-0.8, -1, 0), head=(-0.5, -26.5, 0), root={'pos': (0, 0, -0.018), 'yaw': 31}, hand_r=sway(0.02, 0.08, 0.03))),
        (60, base),
    ]


def _gait(n, stride, lift, bob, lean, hand_r_back, hand_r_fwd, arm_l, twist):
    """Цикл шага: правая нога вперёд на 0, левая на n/2; таз пружинит на контактах; рука с хлыстом и свободная — в противофазе."""
    def foot(side, ph):                       # ph 0..1: 0 — пятка впереди (контакт), 0.5 — нога сзади, 0.75 — перенос (подъём)
        x = 0.14 if side == 'r' else -0.14
        y = stride * math.cos(2 * math.pi * ph)
        z = lift * max(0.0, math.sin(2 * math.pi * (ph - 0.5))) if ph > 0.5 else 0.0
        return {'pos': (x, y, z), 'frame': 'body'}
    keys = []
    for k in range(n + 1):
        ph = k / n
        c = math.cos(2 * math.pi * ph)
        hr = tuple(hand_r_back[i] + (hand_r_fwd[i] - hand_r_back[i]) * (0.5 - 0.5 * c) for i in range(3))
        hl = (-0.36, arm_l * c, 0.84)
        keys.append((k * 1.0, P(root={'pos': (0, 0, -bob * abs(math.cos(2 * math.pi * ph))), 'yaw': twist * math.sin(2 * math.pi * ph), 'pitch': lean},
                                torso=(lean * 0.4, 0, 0), chest=(0, -twist * 0.6 * math.sin(2 * math.pi * ph), 0), head=(-lean * 0.5, 0, 0),
                                foot_r=foot('r', ph), foot_l=foot('l', (ph + 0.5) % 1.0),
                                hand_r=dict(WHIP_TRAIL_R, pos=hr), hand_l=dict(FREE_BODY_L, pos=hl))))
    return keys


def whip_walk():
    """Шаг с хлыстом: рука с рукоятью чуть отведена назад-вбок, хлыст волочится следом; 20 тиков на цикл."""
    return _gait(20, 0.22, 0.10, 0.025, 3, (0.36, -0.04, 0.84), (0.34, 0.10, 0.86), 0.16, 6)


def whip_run():
    """Бег с хлыстом: корпус вперёд, рука с рукоятью отведена в сторону и назад — хлыст летит за спиной; 12 тиков на цикл."""
    return _gait(12, 0.32, 0.18, 0.04, 12, (0.46, -0.22, 0.98), (0.44, -0.06, 1.00), 0.26, 10)


# ------------------------------------------------------------------ сборка
# Тайминги для кода (EmberEpicFight): фазы атаки EF — antic (начало окна попадания), contact (конец окна), recovery
# (можно бить дальше); lash — направление огненной дуги кода (+1 справа налево, как сейчас; −1 слева направо).
TIMING = {
    'last_heat': {'length': 2.0, 'fx_at_tick': LAST_HEAT_IMPACT, 'note': 'fx/ember_last_heat стартует на тике удара клинка'},
    'fire_vortex': {'length': 1.1, 'fx_at_tick': VORTEX_LEAD, 'note': 'fx/ember_vortex стартует на тике 3 (хлыст сзади)'},
    'whip1': {'length': 0.6, 'antic': 0.15, 'contact': 0.30, 'recovery': 0.45, 'lash': 1},
    'whip2': {'length': 0.6, 'antic': 0.15, 'contact': 0.30, 'recovery': 0.45, 'lash': -1},
    'whip3': {'length': 0.7, 'antic': 0.20, 'contact': 0.35, 'recovery': 0.55, 'lash': 1},
    'sword1': {'length': 0.55, 'antic': 0.15, 'contact': 0.30, 'recovery': 0.45},
    'sword2': {'length': 0.6, 'antic': 0.15, 'contact': 0.30, 'recovery': 0.45},
    'sword3': {'length': 0.6, 'antic': 0.15, 'contact': 0.30, 'recovery': 0.45},
    'sword4': {'length': 0.8, 'antic': 0.25, 'contact': 0.40, 'recovery': 0.60},
    'sword_dash': {'length': 0.6, 'antic': 0.15, 'contact': 0.30, 'recovery': 0.45},
    'sword_air': {'length': 0.6, 'antic': 0.15, 'contact': 0.30, 'recovery': 0.45},
    'whip_idle': {'length': 3.0, 'loop': True, 'motion': 'IDLE'},
    'whip_walk': {'length': 1.0, 'loop': True, 'motion': 'WALK'},
    'whip_run': {'length': 0.6, 'loop': True, 'motion': 'RUN'},
}
BEATS = {
    'last_heat': ('«Последний жар»', 'Спецатака в форме меча: клинок двумя руками в землю, жар уходит тремя волнами огненных столбов.',
                  [(0, 'перехват двумя руками'), (4, 'замах над головой'), (LAST_HEAT_IMPACT, 'клинок в земле · старт fx'),
                   (LAST_HEAT_IMPACT + 4, 'волна 1 (r 3)'), (LAST_HEAT_IMPACT + 12, 'волна 2 (r 5)'), (LAST_HEAT_IMPACT + 20, 'волна 3 (r 7)'),
                   (LAST_HEAT_IMPACT + 24, 'выдёргивает клинок'), (LAST_HEAT_IMPACT + 28, 'клинок остывает (пар)')]),
    'fire_vortex': ('«Огненный вихрь»', 'Спецатака в форме хлыста: полный оборот корпусом с вытянутой рукой, огненное кольцо r 5.',
                    [(0, 'стойка'), (VORTEX_LEAD, 'закрут · старт fx'), (VORTEX_LEAD + 2, 'рывок, рука вперёд'),
                     (VORTEX_LEAD + VORTEX_HIT, 'удар: урон, поджог, отброс'), (VORTEX_LEAD + 8, 'хлыст замкнул круг'),
                     (VORTEX_LEAD + 10, 'шаг, гасит инерцию'), (22, 'стойка')]),
    'whip1': ('Хлёст 1', 'Справа налево на уровне груди.', [(0, 'стойка'), (3, 'замах за правое плечо'), (5, 'хлёст'), (7, 'дотяг влево'), (12, 'стойка')]),
    'whip2': ('Хлёст 2', 'Обратный: слева направо, снизу вверх.', [(0, 'стойка'), (3, 'рука у левого бедра'), (5, 'хлёст'), (7, 'дотяг вправо-вверх'), (12, 'стойка')]),
    'whip3': ('Хлёст 3', 'Щелчок сверху с шагом вперёд.', [(0, 'стойка'), (4, 'рука над головой'), (6, 'щелчок вниз'), (8, 'дотяг'), (14, 'стойка')]),
    'sword1': ('Меч: удар 1', 'Горизонтальный разрез справа налево.', [(0, 'стойка'), (3, 'замах за правый бок'), (5, 'разрез'), (7, 'дотяг влево'), (11, 'стойка')]),
    'sword2': ('Меч: удар 2', 'Обратный восходящий: слева снизу вправо вверх.', [(0, 'стойка'), (3, 'клинок у левого бедра'), (5, 'разрез'), (7, 'дотяг вправо-вверх'), (12, 'стойка')]),
    'sword3': ('Меч: удар 3', 'Колющий выпад с шагом.', [(0, 'стойка'), (3, 'клинок к бедру'), (5, 'выпад, укол'), (7, 'удержание'), (12, 'стойка')]),
    'sword4': ('Меч: удар 4', 'Добивающий сверху с подскоком.', [(0, 'стойка'), (4, 'замах за голову'), (5, 'подскок'), (7, 'рубящий вниз'), (9, 'дотяг'), (16, 'стойка')]),
    'sword_dash': ('Меч: на бегу', 'Рывок и широкий разрез.', [(0, 'бег'), (3, 'рывок, замах'), (5, 'разрез'), (7, 'дотяг'), (12, 'стойка')]),
    'sword_air': ('Меч: в прыжке', 'Разворот и рубящий удар наискось вниз.', [(0, 'прыжок'), (3, 'разворот, замах'), (5, 'удар'), (7, 'приземление'), (12, 'стойка')]),
    'whip_idle': ('Стойка с хлыстом', 'Рука с рукоятью опущена, кисть покачивает хлыстом.', [(0, 'стойка'), (15, 'покачивание'), (45, 'покачивание'), (60, 'стойка')]),
    'whip_walk': ('Шаг с хлыстом', 'Хлыст волочится следом.', [(0, 'правая вперёд'), (10, 'левая вперёд'), (20, 'цикл')]),
    'whip_run': ('Бег с хлыстом', 'Рука отведена, хлыст летит за спиной.', [(0, 'правая вперёд'), (6, 'левая вперёд'), (12, 'цикл')]),
}
def ef_body(keys, yaw=1.45, chest=1.4, fwd=2.0, step=1.5):
    """Эталон Epic Fight (владелец 21.11; docs/specs/anim_style_epicfight.md): в тех же тиках и длинах (фазы удара заданы в Java —
    EmberEpicFight, менять их — баланс оружия) больше работы тела: разворот таза (root yaw) и груди (chest/torso yaw) шире, таз подаётся
    вперёд в пределах позы (Coord остаётся нулевым — игрок не перемещается), шаг стопы в удар длиннее (y стопы в осях тела)."""
    out = []
    for k in keys:
        t, p, *rest = k
        q = json.loads(json.dumps(p))
        r = q.get('root')
        if isinstance(r, dict):
            if 'yaw' in r:
                r['yaw'] = r['yaw'] * yaw
            if 'pos' in r and t > 0:
                x, y, z = r['pos']
                r['pos'] = (x, y * fwd, z)
        for part in ('chest', 'torso'):
            if part in q and isinstance(q[part], (list, tuple)):
                a_, b_, c_ = q[part]
                q[part] = (a_, b_ * chest, c_)
        for f in ('foot_r', 'foot_l'):
            if f in q and isinstance(q[f], dict) and q[f].get('frame') == 'body' and t > 0:
                x, y, z = q[f]['pos']
                base = 0.02 if f == 'foot_r' else -0.02
                q[f] = dict(q[f], pos=(x, base + (y - base) * step, z))
        out.append((t, q, *rest))
    return out


ANIMS = {
    'last_heat': last_heat,
    'fire_vortex': fire_vortex,
    'whip1': lambda: ef_body(whip1()),
    'whip2': lambda: ef_body(whip2()),
    'whip3': lambda: ef_body(whip3(), yaw=1.0, chest=1.0),
    'sword1': lambda: ef_body(sword1()),
    'sword2': lambda: ef_body(sword2()),
    'sword3': lambda: ef_body(sword3(), yaw=1.0, chest=1.0, fwd=1.0, step=1.0),
    'sword4': lambda: ef_body(sword4(), yaw=1.0, chest=1.0),
    'sword_dash': lambda: ef_body(sword_dash(), fwd=1.0, step=1.0),
    'sword_air': sword_air,
    'whip_idle': whip_idle,
    'whip_walk': whip_walk,
    'whip_run': whip_run,
}
# след клинка (клиент, data/<имя>.json): от хвата до острия по −Z сустава Tool_R, цвета углей
TRAILS = {
    'last_heat': [(0.18, 0.36)],
    'fire_vortex': [(0.10, 0.62)],
    'whip1': [(0.12, 0.32)],
    'whip2': [(0.12, 0.32)],
    'whip3': [(0.20, 0.38)],
    'sword1': [(0.15, 0.35)],
    'sword2': [(0.15, 0.35)],
    'sword3': [(0.18, 0.32)],
    'sword4': [(0.22, 0.48)],
    'sword_dash': [(0.15, 0.35)],
    'sword_air': [(0.15, 0.38)],
    'whip_idle': [],
    'whip_walk': [],
    'whip_run': [],
}


def bake(keys, step=1.0):
    at, end = sampler(keys)
    frames = []
    t = 0.0
    while t <= end + 1e-6:
        W, info = pose_world(at(t))
        frames.append((t, W, info))
        t += step
    return frames


COORD = rx(math.pi / 2)                  # сустав Coord ванильных анимаций EF: поворот +90° вокруг X, перенос — движение сущности
B2M = rx(-math.pi / 2)                   # Blender -> Minecraft (JsonAssetLoader.BLENDER_TO_MINECRAFT_COORD)


def to_json(frames):
    """
    Первым идёт Coord с нулевым переносом (как в ванильных анимациях с Coord): тогда ActionAnimation берёт движение из него
    (никакого), а не из Root, и сдвиги таза остаются чисто позой. Root при этом пишется уже в осях Minecraft (B2M · Root):
    загрузчик, встретив Coord, не поворачивает следующий сустав сам.
    """
    anim = []
    locs = [(t, local_matrices(W)) for t, W, _ in frames]
    times = [round(t / TPS, 4) for t, _ in locs]
    c = [round(float(v), 5) + 0.0 for v in mat(COORD, (0, 0, 0)).reshape(-1)]
    anim.append({'name': 'Coord', 'time': [times[0], times[-1]], 'transform': [c, c]})
    for n in NAMES:
        mats = []
        for t, L in locs:
            m = mat(B2M, (0, 0, 0)) @ L[n] if n == 'Root' else L[n]
            mats.append([round(float(v), 5) + 0.0 for v in m.reshape(-1)])
        anim.append({'name': n, 'time': times, 'transform': mats})
    return {'animation': anim}


def trail(name):
    out = []
    for a, b in TRAILS[name]:
        out.append({
            'start_time': a, 'end_time': b, 'fade_time': b + 0.12,
            'begin_pos': [0.0, 0.0, -0.15], 'end_pos': [0.0, 0.0, -1.05],
            'interpolations': 10, 'lifetime': 6, 'color': [255, 128, 32],
            'joint': 'Tool_R', 'item_skin_hand': 'main_hand',
        })
    return {'trail_effects': out}


def check(name, frames):
    notes = []
    short = [(round(t), s) for t, _, i in frames for s in i['short']]
    if short:
        notes.append('не дотянулось: %s' % short[:6])
    if name == 'last_heat':
        f = next(fr for fr in frames if round(fr[0]) == LAST_HEAT_IMPACT)
        notes.append('острие на тике удара: %s (цель %s)' % (np.round(f[2]['tip'], 3).tolist(), np.round(PLANT, 3).tolist()))
        lows = [round(float(fr[2]['tip'][2]), 2) for fr in frames if fr[0] < LAST_HEAT_IMPACT - 0.5]
        notes.append('острие до удара не ниже %.2f над землёй' % min(lows))
    return notes


def main():
    os.makedirs(os.path.join(RES, 'data'), exist_ok=True)
    preview = {}
    for name, fn in ANIMS.items():
        frames = bake(fn())
        doc = to_json(frames)
        with open(os.path.join(RES, name + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(doc, fh, separators=(',', ':'))
        with open(os.path.join(RES, 'data', name + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(trail(name), fh, indent=1)
        title, desc, beats = BEATS[name]
        preview[name] = {'json': doc, 'timing': TIMING[name], 'trail': trail(name)['trail_effects'],
                         'title': title, 'desc': desc, 'beats': beats, 'file': 'biped/ember/%s.json' % name}
        print('wrote animmodels/animations/biped/ember/%s.json  (%d ключей, %.2f с)' % (name, len(frames), frames[-1][0] / TPS))
        for n in check(name, frames):
            print('   ', n)
    tpl = os.path.join(HERE, 'ember_anims_preview.template.html')
    if os.path.exists(tpl):
        with open(tpl, encoding='utf-8') as fh:
            html = fh.read()
        bind = {n: {'parent': PARENT[n], 'local': [round(float(v), 6) for v in LOCAL[n].reshape(-1)]} for n in NAMES}
        html = html.replace('/*BIND*/null', json.dumps(bind, separators=(',', ':')))
        html = html.replace('/*ANIMS*/null', json.dumps(preview, separators=(',', ':'), ensure_ascii=False))
        with open(os.path.join(HERE, 'ember_anims_preview.html'), 'w', encoding='utf-8') as fh:
            fh.write(html)
        print('wrote tools/ember_anims_preview.html')
    print('тайминги для кода:', json.dumps(TIMING, ensure_ascii=False))


if __name__ == '__main__':
    main()
