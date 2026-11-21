#!/usr/bin/env python3
"""
T32 п. 4 «Сломать блок» — Глава Культа (cult_leader_guard_break): коса цепляет защиту крюком лезвия и рвёт её в сторону,
перехват — удар древком (подтоком) в открытую грудь. Позы — целями в мире, углы — решателями tools/guard_break_lib.py.
Хват косы НЕ зашит: ось древка, голова (где лезвие) и подток берутся из ассетов (models/item/cult_scythe.json, display
thirdperson_righthand) — при смене хвата («как у Тироса Iron's», письмо docs/inbox/2026-11-21_mgr_t26_hold_tyros.md) удар
пересчитывается перезапуском генератора. Стойка (начало и конец) — поза POSE0_ANIM в момент 0 (анимация хвата из файла Главы).
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
POSE0_ANIM = 'scythe_backpedal'          # поза хвата косы в стойке (её t = 0); после письма о хвате Тироса — сменить при необходимости


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
    an = GL.JModel('cult_leader').anims.get(POSE0_ANIM)
    pose = {}
    if an:
        for b, bk in an['bones'].items():
            q = {}
            if 'rotation' in bk:
                q['rotation'] = GL.AC.chan_at(bk['rotation'], 0.0)
            if 'position' in bk:
                q['position'] = GL.AC.chan_at(bk['position'], 0.0)
            if q and b in M.bones:
                pose[b] = q
    return pose


def build():
    M = GL.JModel('cult_leader', anims={})
    head, butt, tip, up = scythe_axes(M)
    M.item_up = up
    sv = GL.Solver(M)
    p0 = pose0(M)
    st, W0 = GL.stance_targets(M, p0)
    h0 = st['hand_r']
    d0 = GL.nrm(GL.ap(W0['bipedHandRight'], head) - h0)
    u0 = GL.nrm(W0['bipedHandRight'][:3, :3] @ up)
    y0, q0 = float(np.degrees(np.arctan2(d0[0], -d0[2]))), float(np.degrees(np.arcsin(d0[1])))
    b0 = tuple(p0.get('body', {}).get('rotation', [0.0, 0.0, 0.0]))
    S0 = dict(body=b0, torso=(0.0, 0.0, 0.0), pel=(0.0, 0.0), drop=0.0, rf=st['rf'], lf=st['lf'])
    lam = 0.42                                                    # левая рука — на древке ближе к подтоку
    K = Keys([
        (0.0, dict(S0, lw=0.0)),
        (0.10, dict(body=(b0[0], b0[1] + 4.0, 0.0), lw=0.3), 'io'),
        (0.34, dict(body=(12.0, 10.0, 2.0), torso=(4.0, 2.0, 0.0), pel=(0.0, -2.0), drop=0.6, lw=1.0,
                    rf=(3.0, 0.5, 10.0, 0.0), lf=(-3.0, -4.5, -6.0, 0.0)), 'out'),
        (0.40, dict(body=(10.0, 8.0, 1.0)), 'io'),
        (0.50, dict(body=(-4.0, -38.0, -4.0), torso=(-3.0, -10.0, 0.0), pel=(0.4, 1.6), drop=1.2, lf=(-3.0, -2.5, -20.0, 1.0)), 'in'),
        (0.60, dict(body=(-6.0, -44.0, -5.0), torso=(-4.0, -12.0, 0.0), pel=(0.5, 2.0), drop=1.3), 'lin'),
        (0.66, dict(body=(4.0, -24.0, 0.0), torso=(0.0, -4.0, 0.0), pel=(0.2, -2.0), drop=1.6), 'in'),
        (0.71, dict(body=(16.0, -4.0, 3.0), torso=(5.0, 4.0, 0.0), pel=(0.0, -5.6), drop=2.2, rf=(3.0, 0.5, 14.0, 0.0),
                    lf=(-3.2, -12.0, -4.0, 0.0)), 'in'),
        (0.78, dict(body=(19.0, 2.0, 4.0), torso=(6.0, 6.0, 0.0), pel=(0.0, -6.4), drop=2.4), 'out2'),
        (0.88, dict(body=(16.0, 0.0, 2.0), torso=(5.0, 3.0, 0.0), pel=(0.0, -6.0), drop=2.2, rf=(3.0, 0.5, 14.0, 0.0),
                    lf=(-3.2, -12.0, -4.0, 0.0), lw=1.0), 'io'),
        (1.20, dict(body=(6.0, b0[1] - 4.0, 1.0), torso=(2.0, 0.0, 0.0), pel=(0.0, -2.6), drop=1.0, lf=(-3.0, -6.0, -6.0, 1.4)), 'io'),
        (1.42, dict(lf=st['lf'], pel=(0.0, -0.6), drop=0.3, lw=0.4), 'io'),
        (1.80, dict(S0, lw=0.0), 'io'),
    ])
    ST = GL.stime([(0, 0.0), (0.10, 0.0, 'lin'), (0.34, 0.18, 'out'), (0.40, 0.20, 'io'), (0.50, 0.30, 'in'), (0.62, 0.36, 'out'),
                   (0.735, 0.80, ('beta', 2.1, 2.0)), (0.82, 0.82, 'out'), (1.80, 1.0, 'io')])
    # кисть (R-мир) и направление «кисть → голова косы» (yaw, pitch); upw — куда смотрит «верх» древка (от лезвия)
    P = [(0.0, dict(hx=float(h0[0]), hy=float(h0[1]), hz=float(h0[2]), byaw=y0, bpit=q0, ux=float(u0[0]), uy=float(u0[1]), uz=float(u0[2]))),
         (0.10, dict(hx=8.0, hy=22.0, hz=-6.0, byaw=4.0, bpit=48.0, ux=0.0, uy=0.2, uz=1.0)),        # голова косы вверх-вперёд
         (0.18, dict(hx=6.0, hy=19.5, hz=-12.0, byaw=0.0, bpit=4.0, ux=0.0, uy=1.0, uz=0.0)),       # опустил за защиту: лезвие вниз
         (0.20, dict(hx=6.0, hy=19.0, hz=-12.4, byaw=0.0, bpit=3.0, ux=0.0, uy=1.0, uz=0.0)),
         (0.30, dict(hx=-3.0, hy=18.0, hz=-6.0, byaw=-50.0, bpit=4.0, ux=0.0, uy=1.0, uz=0.0)),     # рванул влево
         (0.36, dict(hx=-2.0, hy=18.5, hz=-3.0, byaw=-150.0, bpit=34.0, ux=-0.3, uy=0.5, uz=-0.8)),  # перехват: голова назад-влево, подток вперёд
         (0.80, dict(hx=3.0, hy=17.5, hz=-13.0, byaw=-178.0, bpit=9.0, ux=0.0, uy=0.6, uz=-0.8)),   # удар подтоком в грудь цели
         (0.82, dict(hx=3.0, hy=17.6, hz=-12.6, byaw=-178.0, bpit=10.0, ux=0.0, uy=0.6, uz=-0.8)),
         (0.92, dict(hx=8.0, hy=19.0, hz=-6.0, byaw=-120.0, bpit=70.0, ux=0.3, uy=0.0, uz=-1.0)),    # коса встаёт вертикально
         (1.0, dict(hx=float(h0[0]), hy=float(h0[1]), hz=float(h0[2]), byaw=y0, bpit=q0, ux=float(u0[0]), uy=float(u0[1]), uz=float(u0[2])))]

    def pose(t):
        pel = K.v(t, 'pel')
        o = {'body': {'rotation': K.v(t, 'body'), 'position': [pel[0], 0.0, pel[1]]}, 'torso': {'rotation': K.v(t, 'torso')}}
        sv.legs(o, {'right_leg': tuple(K.v(t, 'rf')), 'left_leg': tuple(K.v(t, 'lf'))}, drop=K.f(t, 'drop'))
        b = K.v(t, 'body')
        bl = K.v(max(0.0, t - 0.06), 'body')
        o['head'] = {'rotation': [-0.7 * b[0], -0.85 * bl[1], 0.0]}
        w = GL.path_at(P, ST(t))
        sv.arm(o, 'right', np.array([w['hx'], w['hy'], w['hz']]))
        sv.wrist(o, yaw_dir(w['byaw'], w['bpit']), up=(w['ux'], w['uy'], w['uz']), far=head)
        lw = K.f(t, 'lw')
        if lw > 0.01:                                            # левая рука на древке (между кистью и подтоком)
            Mh = M.chain(o, 'bipedHandRight')
            tgt = GL.ap(Mh, butt * lam)
            own = np.array(p0.get('left_arm', {}).get('rotation', [0.0, 0.0, 0.0]), float)
            sv.arm(o, 'left', np.asarray(tgt))
            o['left_arm']['rotation'] = list(own * (1 - lw) + np.array(o['left_arm']['rotation']) * lw)
        else:
            o['left_arm'] = {'rotation': list(p0.get('left_arm', {}).get('rotation', [0.0, 0.0, 0.0]))}
        return o

    sv.reset()
    for _ in range(2):
        pose(0.0)
    return GL.bake(GL.blend_edges(pose, p0, LENGTH), LENGTH, 0.02, events={WARN: 'warn', HIT: 'hit'})
