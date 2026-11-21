"""Арис (T28): кузня, наковальня, мехи, шипение закалки, металл лат, тяжёлый молот."""
from sfx import *  # noqa: F401,F403

B = "aris"

EVENTS = {
    "aris.aura": ("Арис: гул горна", "Aris: forge roars", 20, 0.35),
    "aris.spawn": ("Горн Ариса разгорается", "Aris's forge flares", 64, 1.0),
    "aris.slam": ("Молот бьёт в землю", "Hammer slams the ground", 48, 1.0),
    "aris.swing": ("Свист молота", "Hammer swings", 20, 1.0),
    "aris.anvil": ("Наковальня падает", "Anvil drops", 40, 1.0),
    "aris.blade": ("Клинки выкованы", "Blades forged", 32, 1.0),
    "aris.blade_break": ("Клинок раскалывается", "Blade shatters", 24, 1.0),
    "aris.blade_dart": ("Клинок летит", "Blade darts", 24, 1.0),
    "aris.blade_hit": ("Клинок вонзается", "Blade strikes", 20, 1.0),
    "aris.forge": ("Горн ревёт", "Forge roars", 48, 1.0),
    "aris.last_blow": ("Последний удар: замах", "Last Blow: raising the hammer", 64, 1.0),
    "aris.phase": ("Арис раскаляется", "Aris heats up", 64, 1.0),
    "aris.reforge": ("Перековка", "Reforge", 24, 1.0),
    "aris.surrender": ("Арис сдаётся", "Aris yields", 32, 1.0),
    "aris.hammer_drop": ("Молот падает", "Hammer falls", 32, 1.0),
    "aris.billet": ("Раскалённая заготовка шипит", "Hot billet hisses", 24, 1.0),
    "aris.billet_explode": ("Заготовка взрывается", "Billet explodes", 40, 1.0),
    "aris.chains": ("Цепи кузни", "Forge chains", 32, 1.0),
    "aris.chain_rattle": ("Цепи звенят", "Chains rattle", 16, 1.0),
    "aris.chains_break": ("Цепи порваны", "Chains break", 24, 1.0),
    "aris.quench": ("Закалка: шипение пара", "Quench: steam hisses", 40, 1.0),
    "aris.bellows": ("Мехи дуют", "Bellows blow", 40, 1.0),
    "aris.bellows_draw": ("Мехи набирают воздух", "Bellows draw in", 24, 1.0),
    "aris.step": ("Тяжёлые шаги Ариса", "Aris's heavy steps", 16, 0.8),
    "aris.armor": ("Лязг лат", "Armor clanks", 12, 0.7),
    "aris.horns": ("Рога Ариса вспыхивают", "Aris's horns ignite", 40, 1.0),
    "aris.hiss": ("Металл остывает с шипением", "Metal cools with a hiss", 24, 1.0),
    "aris.anvil_ring": ("Звон наковальни", "Anvil rings", 32, 1.0),
    "aris.replica_break": ("Реплика перекована", "Replica reforged", 32, 1.0),
    "aris.hurt": ("Арис ранена", "Aris hurts", 16, 1.0),
}


def plate(i=0):
    """A clank of plate armor: two sheet hits + a short ring."""
    a = src("100-CC0-wood-metal-SFX/metal_sheet_0%d.ogg" % (1 + i % 6))
    b = src("100-CC0-wood-metal-SFX/metal_sheet_0%d.ogg" % (1 + (i + 3) % 6))
    return mix((lp(a, 6000), 0, 0), (lp(b, 5000), 0.03, -5), (metal_ring(900 + 140 * i, 0.4, 0.12), 0, -16))


def hammer_whoosh(i=0, d=0.5):
    w = whoosh(d, 110 + 20 * i, 700 + 120 * i, 1.8, 2.2, 0.62)
    sw = semis(src("swishes/swishes/swish-%d.wav" % (4 + 3 * i)), -9)
    return mix((w, 0, 0), (sw, d * 0.45, -3), (plate(i), 0, -10))


def anvil_hit(i=0, pitch=0):
    """Hammer on the anvil: blacksmith hit + a long bright ring + low body."""
    h = semis(src("blacksmithhammer.wav"), pitch)
    ring = metal_ring(1150 * 2 ** (pitch / 12) + 60 * i, 2.2, 0.9)
    return mix((h, 0, 0), (ring, 0, -7), (src("100-CC0-wood-metal-SFX/hammer_0%d.ogg" % (1 + i % 4)), 0, -6), (thump(90, 50, 0.4, 0.08), 0, -6))


def fire(d, fc=700):
    return fire_roar(d, fc)


def bellows(d=1.0, out=True):
    """A bellows breath: low-passed rush + a wooden creak."""
    t = t_axis(d)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** (0.6 if out else 1.5)
    rush = lp(noise(d, "pink"), 900 if out else 600) * env
    cr = semis(src("RPGsounds_Kenney/OGG/creak%d.ogg" % (2 if out else 1)), -5)
    return mix((rush, 0, 0), (cr, 0, -8), (sine(48, d, 40) * env, 0, -8))


def steam(d=1.6, tau=0.6):
    x = lp(hiss(d, 4500, tau), 10000)
    return mix((x, 0, 0), (bp(noise(d), 1500, 3500) * env_exp(secs(d), tau * 0.6), 0, -8))


def build():
    F = {}

    def put(ev, name, x, **kw):
        F.setdefault(ev, []).append(write("%s/%s" % (B, name), x, **kw).split("sounds/boss/")[1][:-4])

    # aura: a forge — low fire roar, slow bellows breathing, metal ticking as it cools
    rng(301)
    d = 8.0
    roar = lp(fire(d, 500), 900)
    br = np.zeros(secs(d))
    for at in (0.5, 4.5):
        b = bellows(2.0, True)
        br[secs(at):secs(at) + len(b)] += b[: len(br) - secs(at)]
    ticks = np.zeros(secs(d))
    for at in uni(0.2, d - 0.5, 7):
        p = metal_ring(uni(1800, 3200), 0.3, 0.05)
        ticks[secs(at):secs(at) + len(p)] += p[: len(ticks) - secs(at)] * uni(0.2, 0.6)
    F["aris.aura"] = [write_loop("%s/aura" % B, mix((roar, 0, 0), (br, 0, -6), (ticks, 0, -24), (drone(36.7, d, 4, 0.004, 160), 0, -8)), 1.0, 0.5)
                      .split("sounds/boss/")[1][:-4]]

    # spawn: the cold forge wakes — bellows, roar rising, anvil strike and the horns igniting
    rng(302)
    x = mix((bellows(1.6), 0, -2), (bellows(1.6), 1.8, -1), (fire(3.5, 900) * np.linspace(0.1, 1, secs(3.5)), 1.0, -2),
            (anvil_hit(0, -5), 3.6, 0), (rumble(3.0, 80, 1.0), 3.6, -4), (steam(1.4, 0.5), 3.7, -10))
    put("aris.spawn", "spawn", reverb(x, 2.4, 0.3))

    # slam (3): hammer into the ground — body thump, stone crack, plate, a ring
    for i in range(3):
        rng(305 + i)
        x = mix((thump(62 - 4 * i, 30, 0.9, 0.22, 0.6), 0, 0), (src("sfx_breaking_and_falling/bfh1_rock_breaking_0%d.ogg" % (1 + i)), 0, -4),
                (semis(src("blacksmithhammer.wav"), -9 - i), 0, -4), (metal_ring(380 + 50 * i, 1.4, 0.5), 0.01, -14),
                (src("sfx_breaking_and_falling/bfh1_rock_falling_0%d.ogg" % (5 + i)), 0.15, -12), (plate(i), 0.02, -10))
        put("aris.slam", "slam_%d" % (i + 1), reverb(x, 1.8, 0.28))

    # swing (4): heavy hammer whoosh
    for i in range(4):
        rng(310 + i)
        put("aris.swing", "swing_%d" % (i + 1), reverb(hammer_whoosh(i, 0.5 + 0.06 * i), 0.9, 0.15))

    # anvil drops from the sky / blades forged / blade shatters
    for i in range(2):
        rng(315 + i)
        x = mix((rev(whoosh(0.6, 300, 1800)), 0, -6), (thump(55, 28, 1.0, 0.3, 0.5), 0.6, 0), (semis(src("blacksmithhammer.wav"), -12 + i), 0.6, -2),
                (metal_ring(260 + 30 * i, 2.0, 0.8), 0.6, -8), (src("sfx_breaking_and_falling/bfh1_metal_falling_0%d.ogg" % (1 + i)), 0.62, -8))
        put("aris.anvil", "anvil_%d" % (i + 1), reverb(x, 1.8, 0.3))
    for i in range(2):
        rng(318 + i)
        x = mix((anvil_hit(i, 2), 0, 0), (anvil_hit(i + 1, 4), 0.22, -3), (steam(0.8, 0.3), 0.3, -10), (fire(0.8, 1200) * env_exp(secs(0.8), 0.3), 0, -10))
        put("aris.blade", "blade_%d" % (i + 1), reverb(x, 1.4, 0.25))
    for i in range(2):
        rng(321 + i)
        x = mix((src("sfx_breaking_and_falling/bfh1_metal_hit_0%d.ogg" % (2 + i)), 0, 0), (metal_ring(1700 + 300 * i, 0.8, 0.2), 0, -6),
                (src("sfx_breaking_and_falling/bfh1_glass_breaking_0%d.ogg" % (4 + i)), 0.01, -12), (steam(0.6, 0.2), 0.02, -14))
        put("aris.blade_break", "blade_break_%d" % (i + 1), reverb(x, 1.0, 0.2))
    for i in range(2):
        rng(324 + i)
        x = mix((whoosh(0.3, 900, 3500, 1.2, 2.5, 0.7), 0, 0), (metal_ring(2200 + 200 * i, 0.4, 0.1), 0.0, -14), (fire(0.3, 2000) * env_exp(secs(0.3), 0.1), 0, -12))
        put("aris.blade_dart", "blade_dart_%d" % (i + 1), x)
    for i in range(2):
        rng(326 + i)
        x = mix((src("80-CC0-RPG-SFX_0/blade_0%d.ogg" % (1 + i)), 0, 0), (metal_ring(1500 + 200 * i, 0.6, 0.15), 0, -10), (thump(120, 60, 0.2, 0.04), 0, -8))
        put("aris.blade_hit", "blade_hit_%d" % (i + 1), reverb(x, 0.8, 0.15))

    # forge (special): roar of the forge + a huge bellows gust
    for i in range(2):
        rng(330 + i)
        x = mix((bellows(1.4), 0, 0), (fire(2.6, 1100) * adsr(secs(2.6), 0.2, 0.3, 0.8, 1.2), 0.2, 0), (src("flame.ogg"), 0.25, -4),
                (src("80-CC0-RPG-SFX_0/spell_fire_0%d.ogg" % (2 + i)), 0.3, -4), (thump(60, 32, 0.8, 0.2), 0.25, -8))
        put("aris.forge", "forge_%d" % (i + 1), reverb(x, 2.0, 0.3))

    # last blow: a long charge — hammer raised, heat building, metal groaning
    rng(335)
    d = 4.2
    rise = np.linspace(0, 1, secs(d)) ** 1.8
    groan = string_creak(d, 60, 110, 8) * rise
    x = mix((fire(d, 1200) * rise, 0, 0), (groan, 0, -8), (sine(41, d, 82) * rise, 0, -6), (bellows(1.6), 0.4, -8), (bellows(1.6), 2.2, -6),
            (plate(1), 0.0, -4), (plate(3), 0.5, -6))
    put("aris.last_blow", "last_blow", reverb(x, 1.8, 0.25))

    # phase (2): forge roar + anvil toll + plates
    for i in range(2):
        rng(340 + i)
        x = mix((thump(55, 28, 1.3, 0.35, 0.5), 0, 0), (anvil_hit(i, -7), 0, -2), (fire(2.4, 900) * env_exp(secs(2.4), 0.9), 0.02, -2),
                (bellows(1.2), 0, -6), (plate(i + 2), 0.05, -6), (rumble(2.4, 80, 0.9), 0, -6))
        put("aris.phase", "phase_%d" % (i + 1), reverb(x, 2.4, 0.32))

    # reforge: two quick anvil hits + steam
    rng(345)
    put("aris.reforge", "reforge", reverb(mix((anvil_hit(2, 3), 0, 0), (anvil_hit(3, 5), 0.18, -3), (steam(1.0, 0.4), 0.25, -6)), 1.4, 0.25))

    # surrender: the forge dies down (fire falling, long hiss, cooling ticks)
    rng(347)
    d = 3.2
    fall = sweep_filter(noise(d, "pink"), 900, 120, 2.0) * np.exp(-np.arange(secs(d)) / (1.0 * SR))
    ticks = mix(*[(metal_ring(uni(1800, 3000), 0.3, 0.05), 0.4 + 0.35 * k, -10 - 2 * k) for k in range(6)])
    x = mix((fall, 0, 0), (steam(2.6, 1.0), 0.1, -6), (ticks, 0, -2), (bellows(1.8, False), 0, -8))
    put("aris.surrender", "surrender", reverb(x, 2.2, 0.35))
    rng(348)
    x = mix((thump(70, 35, 0.7, 0.18, 0.5), 0, 0), (semis(src("blacksmithhammer.wav"), -10), 0, -3), (metal_ring(340, 1.6, 0.6), 0, -10),
            (src("sfx_breaking_and_falling/bfh1_metal_falling_03.ogg"), 0.05, -6))
    put("aris.hammer_drop", "hammer_drop", reverb(x, 1.6, 0.3))

    # billet: red-hot metal sizzling in the air / exploding
    for i in range(2):
        rng(350 + i)
        x = mix((steam(1.2, 0.5), 0, 0), (crackle(1.2, 35), 0, -10), (fire(1.0, 1500) * env_exp(secs(1.0), 0.4), 0, -6),
                (src("100-CC0-wood-metal-SFX/metal_hit_0%d.ogg" % (3 + i)), 0, -4))
        put("aris.billet", "billet_%d" % (i + 1), reverb(x, 1.0, 0.2))
    for i in range(2):
        rng(353 + i)
        x = mix((semis(src("25-CC0-bang-sfx/bang_0%d.ogg" % (6 + i)), -2), 0, 0), (fire(1.4, 1200) * env_exp(secs(1.4), 0.5), 0, -3),
                (shimmer(1.0, 2800, 10, 1.0, 0.1), 0.02, -14), (steam(1.0, 0.4), 0.1, -10), (thump(70, 35, 0.6, 0.15), 0, -4))
        put("aris.billet_explode", "billet_explode_%d" % (i + 1), reverb(x, 1.8, 0.3))

    # chains: rattling out of the ground, locking; rattle (struggle); break
    rng(356)
    x = mix((src("winch/winch - Marker #7.wav"), 0, -2), (src("80-CC0-RPG-SFX_0/chain_01.ogg"), 0.2, 0), (src("80-CC0-RPG-SFX_0/chain_03.ogg"), 0.45, -2),
            (thump(80, 40, 0.5, 0.1), 0.5, -4), (src("80-CC0-RPG-SFX_0/lock_01.ogg"), 0.55, -4))
    put("aris.chains", "chains", reverb(x, 1.4, 0.25))
    for i in range(3):
        rng(358 + i)
        put("aris.chain_rattle", "chain_rattle_%d" % (i + 1), mix((src("80-CC0-RPG-SFX_0/chain_0%d.ogg" % (1 + i)), 0, 0),
                                                                  (src("winch/winch - Marker #%s.wav" % "235"[i]), 0, -14)))
    rng(362)
    x = mix((src("sfx_breaking_and_falling/bfh1_metal_hit_04.ogg"), 0, 0), (src("80-CC0-RPG-SFX_0/chain_02.ogg"), 0.02, -2), (metal_ring(1300, 0.9, 0.25), 0, -8),
            (src("sfx_breaking_and_falling/bfh1_metal_falling_04.ogg"), 0.1, -8))
    put("aris.chains_break", "chains_break", reverb(x, 1.2, 0.25))

    # quench: a big steam burst + water splash + cooling ticks
    for i in range(2):
        rng(365 + i)
        x = mix((src("water-splash-slime-sfx/splash_0%d.ogg" % (2 + 3 * i)), 0, 0), (steam(2.6, 1.0), 0.05, 0), (src("100-CC0-SFX_0/splash_0%d.ogg" % (1 + i)), 0, -6),
                (mix(*[(metal_ring(uni(2000, 3200), 0.3, 0.05), 0.8 + 0.3 * k, -6 - 3 * k) for k in range(4)]), 0, -6))
        put("aris.quench", "quench_%d" % (i + 1), reverb(x, 1.8, 0.3))

    # bellows (gust) and the draw before it
    for i in range(2):
        rng(370 + i)
        x = mix((bellows(1.2, True), 0, 0), (fire(1.6, 1300) * env_exp(secs(1.6), 0.6), 0.15, -3), (whoosh(0.8, 150, 1500, 2.0, 1.4, 0.4), 0.1, -4))
        put("aris.bellows", "bellows_%d" % (i + 1), reverb(x, 1.6, 0.3))
    rng(372)
    put("aris.bellows_draw", "bellows_draw", reverb(bellows(0.9, False), 1.0, 0.2))

    # steps (4): heavy plate boots — boot thud + plate + metal step
    for i in range(4):
        rng(375 + i)
        ms = src("footsteps/footsteps/step_metal%s.ogg" % ["", " (2)", " (3)", " (4)"][i])
        x = mix((thump(95, 55, 0.25, 0.05, 0.2), 0, 0), (lp(ms, 5000), 0, -3), (plate(i), 0.02, -12),
                (src("RPGsounds_Kenney/OGG/footstep0%d.ogg" % (1 + 2 * i)), 0, -8))
        put("aris.step", "step_%d" % (i + 1), x)
    for i in range(3):
        rng(380 + i)
        put("aris.armor", "armor_%d" % (i + 1), plate(i))

    # horns ignite: a whoomph of flame + rising tone
    rng(384)
    x = mix((src("flame.ogg"), 0, 0), (fire(1.6, 1400) * adsr(secs(1.6), 0.05, 0.2, 0.6, 0.8), 0, -3), (sine(220, 1.0, 440) * adsr(secs(1.0), 0.1, 0.3, 0.4, 0.5), 0, -16),
            (thump(80, 40, 0.5, 0.1), 0, -8))
    put("aris.horns", "horns", reverb(x, 1.6, 0.3))
    for i in range(2):
        rng(386 + i)
        put("aris.hiss", "hiss_%d" % (i + 1), reverb(mix((steam(1.4, 0.6), 0, 0), (crackle(1.2, 15), 0.1, -16)), 1.2, 0.2))
    for i in range(2):
        rng(388 + i)
        put("aris.anvil_ring", "anvil_ring_%d" % (i + 1), reverb(anvil_hit(i, 0), 1.8, 0.28))
    rng(390)
    put("aris.replica_break", "replica_break", reverb(mix((anvil_hit(1, -3), 0, 0), (steam(1.4, 0.6), 0.05, -4),
                                                          (src("sfx_breaking_and_falling/bfh1_glass_breaking_01.ogg"), 0.02, -8)), 1.6, 0.3))
    # hurt (3): plate clang + a muffled thud
    for i in range(3):
        rng(392 + i)
        x = mix((src("100-CC0-wood-metal-SFX/metal_hit_0%d.ogg" % (1 + 2 * i)), 0, 0), (plate(i + 1), 0.01, -4), (thump(100, 55, 0.25, 0.05), 0, -6))
        put("aris.hurt", "hurt_%d" % (i + 1), reverb(x, 0.8, 0.15))
    return F


A = "animation.aris."
ANIMS = {"aris.animation.json": {
    A + "walk": [(0.3, "aris.step"), (0.9, "aris.step"), (0.32, "aris.armor|0.6")],
    A + "slam": [(0.2, "aris.armor"), (0.5, "aris.swing|1.3|0.9")],
    A + "swing": [(0.15, "aris.armor"), (0.4, "aris.swing|1.3")],
    A + "cast": [(0.5, "aris.armor")],
    A + "forge": [(0.72, "aris.swing"), (1.52, "aris.swing"), (2.32, "aris.swing"), (3.3, "aris.horns|2")],
    A + "last_blow": [(0.6, "aris.armor"), (3.65, "aris.swing|2|0.8")],
    A + "phase2": [(0.25, "aris.swing"), (0.75, "aris.swing|1.5|0.85")],
    A + "phase3": [(0.3, "aris.armor"), (1.6, "aris.horns|3")],
    A + "spawn": [(2.0, "aris.armor|1.5"), (4.5, "aris.step|1.5"), (4.55, "aris.armor"), (6.0, "aris.horns|3"), (6.75, "aris.swing|1.5|0.85")],
    A + "surrender": [(0.4, "aris.armor"), (1.2, "aris.armor"), (2.0, "aris.hiss|2"), (2.6, "aris.hiss|1.5|0.8")],
    A + "billet": [(0.2, "aris.armor"), (0.45, "aris.swing")],
    A + "chains": [(0.4, "aris.chain_rattle"), (0.6, "aris.armor")],
    A + "quench": [(0.3, "aris.swing")],
    A + "bellows": [(0.0, "aris.bellows_draw|1.5")],
    A + "finisher": [(0.7, "aris.swing|1.5|0.85"), (2.2, "aris.hiss")],
    A + "guard_break": [(0.1, "aris.armor"), (0.5, "aris.swing|1.3")],
    A + "replica_break": [(0.45, "aris.swing")],
}}

VIDEOS = {
    "aris_sound_1": ("t28_finale", {
        "spawn": [(0.6, "aris.slam|0.5"), (1.2, "aris.slam|0.5"), (1.8, "aris.slam|0.5"), (0.0, "aris.spawn"), (7.0, "aris.slam"), (7.0, "aris.phase")],
        "surrender": [(0.4, "aris.swing"), (1.2, "aris.slam|0.6"), (3.2, "aris.hammer_drop"), (3.6, "aris.surrender")],
        "finisher": [(0, "aris.swing"), (1.5, "aris.slam")],
    }, []),
    "aris_sound_2": ("t28_combat", {
        "slam": [(0.75, "aris.slam")],
        "cast": [(0.8, "aris.anvil")],
    }, [(12.0, "aris.blade"), (12.6, "aris.blade_dart"), (13.1, "aris.blade_hit")]),
    "aris_sound_3": ("t28_special", {
        "phase2": [(1.0, "aris.phase")],
        "phase3": [(0.0, "aris.phase")],
        "forge": [(0, "aris.forge"), (1.0, "aris.slam"), (1.8, "aris.slam"), (2.6, "aris.slam"), (3.3, "aris.forge")],
        "last_blow": [(0, "aris.last_blow"), (3.1, "aris.forge"), (4.0, "aris.slam")],
        "billet": [(0.7, "aris.swing"), (1.2, "aris.billet"), (4.2, "aris.billet_explode")],
        "chains": [(0.8, "aris.chains"), (2.0, "aris.chain_rattle")],
        "quench": [(0.8, "aris.quench")],
        "bellows": [(0.8, "aris.bellows")],
    }, []),
}
