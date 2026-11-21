#!/usr/bin/env python3
"""
T32 п. 4 «Сломать блок» — Арис (animation.aris.guard_break): двуручный удар молотом сверху по блоку (искры — fx aris_guard_break).
В системе генератора Ариса (tools/gen_aris_anims.py: ключевые позы K, молот — хват + направление рукояти + боёк, руки — IK на
рукоять, ленты/коса — пружины), по правилам эталона Epic Fight (docs/specs/anim_style_epicfight.md). Вызывается из gen_aris_anims.main.

Тайминг: warn 0.10 (тик 2; вспышка на голове молота), hit 0.70 (тик 14) — боёк по верху блока; длина 1.8 с (36 тиков).
  0.10–0.30 молот поднимается вертикально у правого плеча; 0.30–0.52 замах за правое плечо (голова молота за спиной), корпус
  назад и вправо, вес на задней ноге, левое колено поднимается (готовит шаг); 0.52–0.62 взвод;
  0.62–0.74 удар: шаг левой, таз вперёд-вниз, корпус в наклон, молот по дуге через верх на блок (пик ~0.69);
  0.74–0.90 перехлёст — молот проваливается вниз (блок сломан), отдача вверх; 0.9–1.8 возврат в стойку с отшагом.
Ключи запекаются через 0.02 с (у ударов EF — не реже: GeckoLib интерполирует углы линейно).
"""
import numpy as np

WARN, HIT, LENGTH = 0.10, 0.70, 1.8


def build(rig, D, AN):
    K, S, GL_ = D.K, D.S, D.GUARD_LEGS
    gd = D.guard()
    wu = D.windup()
    wu2 = ((7.2, 27.4, 5.0), (0.32, 0.36, 0.88), (0.1, 0.9, -0.42))           # взвод: голова молота ещё чуть дальше за спину
    imp = (AN.ham_from_strike((0.8, 19.5, -25.0), (0.0, 0.1, -0.995), (0.0, -0.995, -0.1)), (0.0, 0.1, -0.995), (0.0, -0.995, -0.1))
    low = (AN.ham_from_strike((0.6, 7.5, -21.5), (0.0, -0.62, -0.78), (0.0, -0.78, 0.62)), (0.0, -0.62, -0.78), (0.0, -0.78, 0.62))
    reb = (AN.ham_from_strike((0.6, 10.0, -21.0), (0.0, -0.5, -0.86), (0.0, -0.86, 0.5)), (0.0, -0.5, -0.86), (0.0, -0.86, 0.5))
    STEP = dict(right_leg=(-10, 0, 10), left_leg=(46, 0, -8), right_shin=(-18, 0, 0), left_shin=(-40, 0, 0))

    def plant(legs, by):
        """Ноги — дети корпуса: поворот корпуса на by (Y > 0 — влево) гасится поворотом бёдер, стопы остаются на месте (скрутка)."""
        o = dict(legs)
        for n in ('right_leg', 'left_leg'):
            x, y, z = o[n]
            o[n] = (x, y - by, z)
        return o
    WU = dict(right_leg=(-16, 0, 8), left_leg=(30, 0, -6), right_shin=(-6, 0, 0), left_shin=(-36, 0, 0))
    WU2 = dict(right_leg=(-17, 0, 8), left_leg=(34, 0, -6), right_shin=(-6, 0, 0), left_shin=(-42, 0, 0))
    MID = dict(right_leg=(-16, 0, 8), left_leg=(40, 0, -8), right_shin=(-10, 0, 0), left_shin=(-30, 0, 0))
    k = [
        K(0.0, **S(ham=gd, lh=1, **GL_)),
        K(0.10, 'io', **S(ham=gd, lh=1, body=(1, -2, 0), **GL_)),
        K(0.30, 'out', **S(ham=D.RAISE, lh=0.35, body=(4, -10, 0), torso=(4, -4, 0), head=(2, 10, 0), rpole=(0.9, -0.2, 0.3),
                           lpole=(-0.7, -0.4, 0.5), **GL_)),
        K(0.52, 'out', **S(ham=wu, lh=0.3, body=(13, -32, 0), torso=(9, -14, 0), head=(8, 34, 0), bpos=(0, 0.4, 1.4), **plant(WU, -32),
                           rpole=(0.9, 0.1, 0.3), lpole=(-0.6, -0.3, -0.6))),
        K(0.62, 'linear', **S(ham=wu2, lh=0.3, body=(15, -36, 0), torso=(10, -16, 0), head=(9, 38, 0), bpos=(0, 0.3, 1.7), **plant(WU2, -36),
                              rpole=(0.9, 0.1, 0.3), lpole=(-0.6, -0.3, -0.6))),
        K(0.66, 'in3', **S(ham=D.FWD_UP, lh=1, body=(-2, -10, 0), torso=(-2, -4, 0), head=(4, 10, 0), bpos=(0, -0.8, -1.8), **plant(MID, -10),
                           rpole=(0.9, -0.2, 0.3), lpole=(-0.9, -0.2, 0.3))),
        K(0.705, 'out', **S(ham=imp, lh=1, body=(-16, 12, 0), torso=(-6, 8, 0), head=(12, -12, 0), bpos=(0, -2.2, -4.6),
                           rpole=(0.8, -0.4, 0.3), lpole=(-0.8, -0.4, 0.3), **plant(STEP, 12))),
        K(0.80, 'out', **S(ham=low, lh=1, body=(-24, 20, 0), torso=(-8, 10, 0), head=(18, -18, 0), bpos=(0, -3.2, -5.6),
                           rpole=(0.8, -0.4, 0.3), lpole=(-0.8, -0.4, 0.3), **plant(STEP, 20))),
        K(0.92, 'out', **S(ham=reb, lh=1, body=(-20, 15, 0), torso=(-7, 7, 0), head=(16, -14, 0), bpos=(0, -2.9, -5.2), **plant(STEP, 15))),
        K(1.25, 'io', **S(ham=((-1.0, 19.0, -9.0), (0.1, 0.9, -0.4), (1, 0, 0)), lh=1, body=(-6, 4, 0), torso=(-2, 2, 0), head=(4, -2, 0),
                          bpos=(0, -1.0, -2.0), right_leg=(-10, 0, 9), left_leg=(28, 0, -7), right_shin=(-10, 0, 0), left_shin=(-24, 0, 0),
                          rpole=(0.4, -0.8, 0.4), lpole=(-0.7, -0.6, 0.3))),
        K(1.8, 'io', **S(ham=gd, lh=1, **GL_)),
    ]
    old_dt, old_def = AN.DT, AN.Spring.step.__defaults__
    AN.DT = 0.02                                        # удар — ключи через 0.02 с; пружины лент — с тем же шагом
    AN.Spring.step.__defaults__ = (old_def[0], old_def[1], 0.02)
    try:
        return AN.bake(rig, 'guard_break', LENGTH, k, loop=False, ground='feet', events={WARN: 'warn', HIT: 'hit'})
    finally:
        AN.DT = old_dt
        AN.Spring.step.__defaults__ = old_def
