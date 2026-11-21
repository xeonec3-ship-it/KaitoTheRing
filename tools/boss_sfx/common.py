"""Shared boss sounds: «Сломать блок» (T32) — the guard of a boss breaks."""
from sfx import *  # noqa: F401,F403

EVENTS = {
    "boss.guard_break": ("Блок босса сломан", "Boss guard broken", 40, 1.0),
}
ANIMS = {}
VIDEOS = {}


def build():
    F = {}
    for i in range(3):
        rng(900 + i)
        clang = src("100-CC0-wood-metal-SFX/metal_hit_0%d.ogg" % (3 + i))
        crack = src("sfx_breaking_and_falling/bfh1_breaking_0%d.ogg" % (1 + i))
        x = mix((thump(75, 35, 0.7, 0.16, 0.6), 0, 0), (semis(clang, -3), 0, -2), (metal_ring(520 + 70 * i, 1.4, 0.45), 0, -12),
                (crack, 0.01, -5), (rev(whoosh(0.25, 600, 3000)), -0.0, -12))
        x = mix((x, 0, 0), (whoosh(0.5, 900, 200, 1.5, 1.2, 0.15), 0.05, -12))   # the stagger air
        F.setdefault("boss.guard_break", []).append(write("common/guard_break_%d" % (i + 1), reverb(x, 1.5, 0.28)).split("sounds/boss/")[1][:-4])
    return F
