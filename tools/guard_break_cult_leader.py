#!/usr/bin/env python3
"""
T32 п. 4 «Сломать блок» — Глава Культа (cult_leader_guard_break): коса цепляет защиту крюком лезвия и рвёт её в сторону,
перехват — удар древком (подтоком) в открытую грудь. Позы — целями в мире, углы — решателями tools/guard_break_lib.py.
Хват — как у Тироса Iron's (письмо docs/inbox/2026-11-21_mgr_t26_hold_tyros.md): начало и конец — поза хвата вне анимаций
(gen_cult_leader_extra.CARRY_ARM / CARRY_HAND = числа Тироса; сдвиг хвата на 3 px — в модели предмета cult_scythe), коса считается
с ДВОЙНЫМ поворотом кисти, как её рисует GeckoLib (guard_break_lib, hand2): решатель подбирает ключ кисти так, что в игре коса
смотрит ровно куда задумано. Ось древка, голова (где лезвие) и подток — по точкам предмета models/item/cult_scythe.json.
Вызывается из tools/gen_cult_leader_extra.write_anims (плащ и проверку косы потом делает anim_cloth, как у всех cult_leader_*).

Тайминг: warn 0.10 (тик 2; вспышка на лезвии), hit 0.70 (тик 14) — удар древком; длина 1.8 с (36 тиков).
  0.10–0.38 замах-заброс: голова косы уходит вверх-вперёд и опускается за защиту цели (лезвие крюком вниз, к Главе);
  0.38–0.50 рывок: корпус влево, коса тянет защиту в сторону (влево от Главы), вес назад;
  0.50–0.60 перехват: голова косы уходит назад-влево за плечо — подток выходит вперёд (взвод);
  0.60–0.74 удар древком: шаг, таз вперёд-вниз, обе руки выталкивают подток в грудь цели (пик ~0.69); держит до 0.82;
  0.82–1.8 возврат: коса переворачивается в хват стойки, отшаг.
"""
import numpy as np

import guard_break_lib as GL
from guard_break_lib import Keys, yaw_dir

WARN, HIT, LENGTH = 0.10, 0.70, 1.8


def scythe_axes(M):
    """Голова (корень лезвия), подток и «верх» древка (от лезвия) — в осях кисти, по точкам предмета."""
    h = M.item_hand
    c = h.mean(axis=0)
    _, _, vt = np.linalg.svd(h - c)
    ax = vt[0]
    pr = (h - c) @ ax
    e1, e2 = h[int(np.argmax(pr))], h[int(np.argmin(pr))]
    tip = np.array(GL.ap(M.item_m, [3.55, 11.34, 8.0]))           # остриё лезвия (как tip в boss_video.scythe_item)
    head, butt = (e1, e2) if np.linalg.norm(e1 - tip) < np.linalg.norm(e2 - tip) else (e2, e1)
    a = GL.nrm(head - butt)
    blade = tip - head
    up = GL.nrm(-(blade - a * float(blade @ a)))                  # «верх» древка — против лезвия
    return head, butt, tip, up


def special(M):
    head, butt, tip, up = scythe_axes(M)
    M.item_up = up
    return {'strike': (np.zeros(3), butt)}                        # бьёт подток (удар древком)


def pose0(M):
    """Поза хвата вне анимаций (как держит код CultLeaderModel: числа Тироса) — JSON-поза: удар начинается и кончается в ней."""
    import gen_cult_leader_extra as X
    pose = {b: {'rotation': [0.0, 0.0, 0.0]} for b in ('body', 'torso', 'head', 'left_arm', 'right_leg', 'left_leg')}
    pose['body']['position'] = [0.0, 0.0, 0.0]
    pose['right_arm'] = {'rotation': list(X.CARRY_ARM)}
    pose['bipedHandRight'] = {'rotation': list(X.CARRY_HAND)}     # без сдвига в кулаке (HOLD_SLIDE): оружие — только поворотами
    return pose


def build():
    M = GL.JModel('cult_leader', anims={})
    head, butt, tip, up = scythe_axes(M)
    M.item_up = up
    sv = GL.Solver(M)
    p0 = pose0(M)
    ra = p0['right_arm']['rotation']
    RA0 = (GL.Rz(ra[2] * GL.D) @ GL.Ry(-ra[1] * GL.D) @ GL.Rx(-ra[0] * GL.D))[:3, :3]
    st, W0 = GL.stance_targets(M, p0)
    h0 = st['hand_r']
    d0 = GL.nrm(GL.ap(W0['~item'], head) - GL.ap(W0['~item'], (0, 0, 0)))
    u0 = GL.nrm(W0['~item'][:3, :3] @ up)
    y0, q0 = float(np.degrees(np.arctan2(d0[0], -d0[2]))), float(np.degrees(np.arcsin(d0[1])))
    b0 = tuple(p0.get('body', {}).get('rotation', [0.0, 0.0, 0.0]))
    S0 = dict(body=b0, torso=(0.0, 0.0, 0.0), pel=(0.0, 0.0), drop=0.0, rf=st['rf'], lf=st['lf'])
    lam = 0.42                                                    # левая рука — на древке ближе к подтоку
    K = Keys([
        (0.0, dict(S0, lw=0.0)),
        (0.12, dict(body=(b0[0] + 4.0, b0[1] + 8.0, 0.0), torso=(2.0, -2.0, 0.0), drop=0.4, pel=(0.2, 0.6), lw=0.3,
                    rf=(st['rf'][0] + 1.5, st['rf'][1] + 1.0, st['rf'][2], 0.0)), 'io'),   # подготовка: оседает, коса чуть назад
        (0.40, dict(body=(12.0, 10.0, 2.0), torso=(4.0, 2.0, 0.0), pel=(0.0, -2.0), drop=0.6, lw=1.0,
                    rf=(3.0, 0.5, 10.0, 0.0), lf=(-3.0, -4.5, -6.0, 0.0)), 'out'),
        (0.44, dict(body=(10.0, 8.0, 1.0)), 'io'),
        (0.51, dict(body=(-4.0, -38.0, -4.0), torso=(-3.0, -10.0, 0.0), pel=(0.4, 1.6), drop=1.2, lf=(-3.0, -2.5, -20.0, 1.0)), 'in'),
        (0.60, dict(body=(-6.0, -44.0, -5.0), torso=(-4.0, -12.0, 0.0), pel=(0.5, 2.0), drop=1.3), 'lin'),
        (0.66, dict(body=(4.0, -24.0, 0.0), torso=(0.0, -4.0, 0.0), pel=(0.2, -2.0), drop=1.6), 'in'),
        (0.71, dict(body=(16.0, -4.0, 3.0), torso=(5.0, 4.0, 0.0), pel=(0.0, -5.6), drop=2.2, rf=(3.0, 0.5, 14.0, 0.0),
                    lf=(-3.2, -12.0, -4.0, 0.0)), 'in'),
        (0.78, dict(body=(19.0, 2.0, 4.0), torso=(6.0, 6.0, 0.0), pel=(0.0, -6.4), drop=2.4), 'out2'),
        (0.88, dict(body=(16.0, 0.0, 2.0), torso=(5.0, 3.0, 0.0), pel=(0.0, -6.0), drop=2.2, rf=(3.0, 0.5, 14.0, 0.0),
                    lf=(-3.2, -12.0, -4.0, 0.0), lw=1.0), 'io'),
        (1.20, dict(body=(6.0, b0[1] - 4.0, 1.0), torso=(2.0, 0.0, 0.0), pel=(0.0, -2.6), drop=1.0, lf=(-3.0, -6.0, -6.0, 1.4)), 'io'),
        (1.10, dict(lw=0.0), 'io'),
        (1.42, dict(lf=st['lf'], pel=(0.0, -0.6), drop=0.3), 'io'),
        (1.80, dict(S0, lw=0.0), 'io'),
    ])
    ST = GL.stime([(0, 0.0), (0.12, 0.04, 'io'), (0.40, 0.18, 'io'), (0.44, 0.20, 'io'), (0.49, 0.30, 'io'), (0.64, 0.36, 'io'),
                   (0.735, 0.80, ('beta', 2.0, 2.0)), (0.82, 0.82, 'out'), (1.40, 1.0, 'io'), (1.80, 1.0, 'lin')])
    # кисть (R-мир) и направление «кисть → голова косы» (yaw, pitch); upw — куда смотрит «верх» древка (от лезвия)
    # правая рука — одна кость (локтя нет): путь — направление руки от плеча (ayaw — вправо +, apit — вверх +), направление
    # «кисть → голова косы» (byaw, bpit) и «верх» древка (от лезвия) u
    sh0 = GL.ap(W0['right_arm'], (0, 0, 0))
    a0 = GL.nrm(h0 - sh0)
    ARM = float(np.linalg.norm(h0 - sh0))
    A0 = dict(ayaw=float(np.degrees(np.arctan2(a0[0], -a0[2]))), apit=float(np.degrees(np.arcsin(a0[1]))))
    if abs(A0['ayaw']) > 90:                     # рука в хвате — назад-вниз: тот же вектор как «наклон за −90°», чтобы рука шла
        A0 = dict(ayaw=(A0['ayaw'] + 360) % 360 - 180, apit=-180.0 - A0['apit'])     # маятником через низ, а не через бок
    U0 = dict(ux=float(u0[0]), uy=float(u0[1]), uz=float(u0[2]))
    P = [(0.0, dict(A0, byaw=y0, bpit=q0, **U0)),
         (0.04, dict(ayaw=A0['ayaw'], apit=A0['apit'] - 5.0, byaw=y0 + 4.0, bpit=q0 + 2.0, **U0)),          # подготовка: коса чуть назад-вниз
         (0.085, dict(ayaw=30.0, apit=-25.0, byaw=10.0, bpit=18.0, ux=0.3, uy=0.4, uz=0.85)),       # рука дугой наружу — мимо бедра
         (0.13, dict(ayaw=20.0, apit=-12.0, byaw=-8.0, bpit=26.0, ux=0.0, uy=0.6, uz=0.8)),          # голова косы вверх-вперёд
         (0.18, dict(ayaw=6.0, apit=-16.0, byaw=-18.0, bpit=22.0, ux=0.0, uy=1.0, uz=0.0)),            # опустил за защиту: лезвие вниз
         (0.20, dict(ayaw=6.0, apit=-18.0, byaw=-20.0, bpit=22.0, ux=0.0, uy=1.0, uz=0.0)),
         (0.30, dict(ayaw=-40.0, apit=-26.0, byaw=-72.0, bpit=18.0, ux=0.0, uy=1.0, uz=0.0)),        # рванул влево
         (0.36, dict(ayaw=-85.0, apit=-27.0, byaw=-155.0, bpit=19.0, ux=0.8, uy=-0.6, uz=0.0)),    # перехват: голова косы назад-влево, лезвие вверх, подток вперёд
         (0.80, dict(ayaw=-12.0, apit=-4.0, byaw=-135.0, bpit=4.0, ux=0.8, uy=-0.6, uz=0.0)),     # удар подтоком в грудь цели (древко мимо корпуса слева)
         (0.82, dict(ayaw=-12.0, apit=-3.0, byaw=-135.0, bpit=5.0, ux=0.8, uy=-0.6, uz=0.0)),
         (0.88, dict(ayaw=-62.0, apit=-30.0, byaw=-150.0, bpit=12.0, ux=0.8, uy=-0.6, uz=0.0)),     # возврат — обратным ходом:
         (0.93, dict(ayaw=-40.0, apit=-22.0, byaw=-55.0, bpit=34.0, ux=0.0, uy=1.0, uz=0.0)),       # голова косы влево-вперёд…
         (0.97, dict(ayaw=18.0, apit=-2.0, byaw=8.0, bpit=32.0, ux=0.75, uy=0.35, uz=0.45)),           # …вперёд, лезвие вниз — в хват
         (1.0, dict(A0, byaw=y0, bpit=q0, **U0))]

    def pose(t):
        pel = K.v(t, 'pel')
        o = {'body': {'rotation': K.v(t, 'body'), 'position': [pel[0], 0.0, pel[1]]}, 'torso': {'rotation': K.v(t, 'torso')}}
        sv.legs(o, {'right_leg': tuple(K.v(t, 'rf')), 'left_leg': tuple(K.v(t, 'lf'))}, drop=K.f(t, 'drop'))
        b = K.v(t, 'body')
        bl = K.v(max(0.0, t - 0.06), 'body')
        o['head'] = {'rotation': [-0.7 * b[0], -0.85 * bl[1], 0.0]}
        # оружие — только поворотами (владелец 21.11: никаких ключей позиции на кисть/руку — коса в кулаке в каждом кадре)
        e = 1.0 - GL.ease(min(1.0, t / 0.12), 'io') if t < 0.12 else GL.ease(min(1.0, max(0.0, (t - 1.40) / 0.20)), 'io')
        sv.arm_ref = (RA0, 6.0 * e)                                   # скручивание руки на краях — как в позе хвата
        w = GL.path_at(P, ST(t))
        sh = GL.ap(M.chain(o, 'right_arm'), (0, 0, 0))
        sv.arm(o, 'right', sh + yaw_dir(w['ayaw'], w['apit']) * ARM)
        sv.wrist(o, yaw_dir(w['byaw'], w['bpit']), up=(w['ux'], w['uy'], w['uz']), far=head)
        lw = K.f(t, 'lw')
        if lw > 0.01:                                            # левая рука на древке (между кистью и подтоком)
            Mh = M.item_frame(o)
            tgt = np.asarray(GL.ap(Mh, butt * lam))
            shl = GL.ap(M.chain(o, 'left_arm'), (0, 0, 0))
            sa = GL.nrm(np.asarray(GL.ap(Mh, butt)) - np.asarray(GL.ap(Mh, (0, 0, 0))))
            off = shl - tgt
            off = off - sa * float(off @ sa)                          # от древка поперёк, к плечу: кулак у древка, не насквозь
            tgt = tgt + GL.nrm(off) * 2.6
            own = np.array(p0.get('left_arm', {}).get('rotation', [0.0, 0.0, 0.0]), float)
            sv.arm(o, 'left', tgt)
            o['left_arm']['rotation'] = list(own * (1 - lw) + np.array(o['left_arm']['rotation']) * lw)
        else:
            o['left_arm'] = {'rotation': list(p0.get('left_arm', {}).get('rotation', [0.0, 0.0, 0.0]))}
        return o

    sv.reset()
    for _ in range(2):
        pose(0.0)
    return GL.bake(GL.blend_edges(pose, p0, LENGTH, t_out=0.12), LENGTH, 0.02, events={WARN: 'warn', HIT: 'hit'})
