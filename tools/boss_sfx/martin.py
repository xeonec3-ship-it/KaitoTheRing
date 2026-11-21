"""Мартин (T29): латы, меч, щит, знамя на ветру, горн и барабаны войска, конница, призрачные солдаты."""
from sfx import *  # noqa: F401,F403

B = "martin"

EVENTS = {
    "martin.aura": ("Мартин: знамя на ветру, далёкие барабаны", "Martin: banner in the wind, distant drums", 20, 0.35),
    "martin.spawn": ("Мартин поднимается из строя", "Martin rises from the ranks", 64, 1.0),
    "martin.step": ("Шаги в латах", "Armored steps", 16, 0.8),
    "martin.armor": ("Лязг лат", "Armor clanks", 12, 0.7),
    "martin.swing": ("Свист меча", "Sword swings", 20, 1.0),
    "martin.hit": ("Меч бьёт", "Sword hits", 20, 1.0),
    "martin.slam": ("Меч бьёт в землю", "Sword slams the ground", 48, 1.0),
    "martin.bash": ("Удар щитом", "Shield bash", 32, 1.0),
    "martin.dash": ("Рывок со щитом", "Shield dash", 24, 1.0),
    "martin.block": ("Мартин принимает удар на щит", "Martin blocks", 48, 1.0),
    "martin.shield_hit": ("Удар о щит", "Shield is hit", 24, 1.0),
    "martin.command": ("Мартин отдаёт приказ", "Martin commands", 48, 1.0),
    "martin.drum": ("Барабаны войска", "War drums", 48, 1.0),
    "martin.horn": ("Горн войска", "War horn", 96, 1.0),
    "martin.gallop": ("Конница скачет", "Cavalry gallops", 80, 1.0),
    "martin.banner_plant": ("Знамя вонзается в землю", "Banner planted", 40, 1.0),
    "martin.banner_flap": ("Знамя хлопает на ветру", "Banner flaps", 16, 0.4),
    "martin.banner_hit": ("Удар по древку", "Banner pole hit", 20, 1.0),
    "martin.banner_cut": ("Знамя срублено", "Banner cut down", 40, 1.0),
    "martin.banner_fall": ("Знамя падает", "Banner falls", 24, 1.0),
    "martin.hold": ("«Держать строй!»", "«Hold the line!»", 48, 1.0),
    "martin.soldier": ("Призрачные солдаты встают", "Spectral soldiers rise", 32, 1.0),
    "martin.soldier_vanish": ("Солдат развеивается", "Soldier fades", 20, 1.0),
    "martin.soldier_step": ("Шаги призрачных солдат", "Spectral soldiers step", 12, 0.5),
    "martin.soldier_swing": ("Солдат бьёт", "Soldier strikes", 16, 1.0),
    "martin.phase": ("Мартин поднимает войско", "Martin rallies the army", 64, 1.0),
    "martin.shield_wall": ("Стена щитов", "Shield wall", 48, 1.0),
    "martin.volley": ("Залп стрел", "Arrow volley", 48, 1.0),
    "martin.arrow_hit": ("Стрелы падают", "Arrows land", 32, 1.0),
    "martin.duel": ("Вызов на поединок", "Duel challenge", 48, 1.0),
    "martin.sword_ring": ("Меч звенит", "Sword rings", 24, 1.0),
    "martin.warcry": ("Боевой клич войска", "War cry", 80, 1.0),
    "martin.pierce": ("Меч пронзает", "Sword pierces", 24, 1.0),
    "martin.replica_break": ("Реплика разрублена", "Replica cut down", 32, 1.0),
    "martin.hurt": ("Мартин ранен", "Martin hurts", 16, 1.0),
}


def plate(i=0, heavy=1.0):
    a = src("100-CC0-wood-metal-SFX/metal_sheet_0%d.ogg" % (1 + (i * 2) % 6))
    k = src("RPGsounds_Kenney/OGG/metalLatch.ogg") if i % 2 else src("RPGsounds_Kenney/OGG/metalClick.ogg")
    return mix((semis(lp(a, 5000), -2 * heavy), 0, 0), (k, 0.02, -6), (metal_ring(700 + 90 * i, 0.4, 0.1), 0, -18))


def sword_swish(i=0):
    s = src("sword_-_starninjas_1/sword - StarNinjas/sword.%d.ogg" % (1 + (i * 3) % 10))
    w = whoosh(0.4, 250, 1600 + 200 * i, 1.6, 2.2, 0.6)
    return mix((semis(s, -2), 0, 0), (w, 0, -4), (plate(i), 0, -14))


def shield_hit(i=0):
    wood = src("100-CC0-wood-metal-SFX/wood_hit_0%d.ogg" % (1 + 2 * i))
    met = src("100-CC0-wood-metal-SFX/metal_hit_0%d.ogg" % (1 + i))
    return mix((wood, 0, 0), (met, 0, -3), (thump(110, 60, 0.3, 0.06, 0.2), 0, -4), (metal_ring(620 + 80 * i, 0.8, 0.25), 0, -14))


def flap(d=2.0, rate=9.0, seed_amp=0.5):
    """Heavy cloth flapping in the wind: filtered noise with fast irregular flutter snaps."""
    t = t_axis(d)
    base = bp(noise(d, "pink"), 180, 2200)
    flutter = lp(np.abs(noise(d)), rate, 2)
    flutter = (flutter / (np.max(flutter) + 1e-9)) ** 2.0
    snaps = np.zeros(len(t))
    for at in np.sort(uni(0, d - 0.1, int(d * rate * 0.6))):
        s = hp(noise(0.05), 600) * env_exp(secs(0.05), 0.008) * uni(0.3, 1.0)
        snaps[secs(at):secs(at) + len(s)] += s[: len(snaps) - secs(at)]
    wind = lp(noise(d, "pink"), 500) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * t))
    return norm(mix((base * (0.3 + flutter), 0, 0), (snaps, 0, -8), (wind, 0, -10)))


def drums(start, d):
    x = src("horde_war_drums_by_william_hector.wav", start, d)
    return x * adsr(len(x), 0.02, 0.1, 1.0, 0.4)


def horn(i=0):
    if i == 0:
        return src("theircoming.ogg", 0.0, 2.6)
    return src("theircoming3.ogg", 0.0, 3.6)


def ghost(x, t60=2.4):
    """Spectral: shimmer + long airy reverb + slight pitch drift."""
    return reverb(mix((x, 0, 0), (shimmer(len(x) / SR, 1600, 10, 1.2, 0.3), 0, -16)), t60, 0.5, bright=6000)


def hooves(d=2.5, rate=7.0):
    out = np.zeros(secs(d))
    t = 0.0
    while t < d - 0.2:
        for k in range(3):
            h = thump(uni(95, 130), 60, 0.18, 0.03, 0.4) * uni(0.6, 1.0)
            a = secs(t + k * 0.07)
            out[a:a + len(h)] += h[: len(out) - a]
        t += 1 / rate * uni(0.85, 1.15) * 3
    return norm(out)


def build():
    F = {}

    def put(ev, name, x, **kw):
        F.setdefault(ev, []).append(write("%s/%s" % (B, name), x, **kw).split("sounds/boss/")[1][:-4])

    # aura: the banner in the wind, slow distant drums, the creak of armor
    rng(401)
    d = 8.0
    dr = lp(src("horde_war_drums_by_william_hector.wav", 2.0, d), 400)
    F["martin.aura"] = [write_loop("%s/aura" % B, mix((flap(d, 6), 0, 0), (dr, 0, -14), (lp(noise(d, "brown"), 120), 0, -12)), 1.0, 0.5)
                        .split("sounds/boss/")[1][:-4]]

    # spawn: drums from afar, the horn, armor rising, the sword drawn and saluted
    rng(402)
    x = mix((drums(0.0, 5.0) * np.linspace(0.2, 1, secs(5.0)), 0, -6), (horn(1), 0.4, -3), (plate(0, 1.5), 2.6, -2), (plate(2, 1.5), 2.9, -4),
            (src("RPGsounds_Kenney/OGG/drawKnife1.ogg"), 4.0, -3), (metal_ring(1250, 1.8, 0.7), 4.05, -10), (thump(70, 35, 0.8, 0.2), 2.6, -6),
            (flap(2.5, 8), 0.5, -10))
    put("martin.spawn", "spawn", reverb(x, 2.2, 0.3))

    # steps: plate boots on stone (metal_steps recording slices + body)
    starts = [0.33, 0.91, 1.59, 2.28, 2.95, 3.64]
    for i in range(4):
        rng(405 + i)
        st = fade(src("metal_steps.ogg", starts[i] - 0.02, 0.25), 0.001, 0.05)
        x = mix((st, 0, 0), (thump(90, 50, 0.22, 0.05, 0.1), 0, -6), (plate(i), 0.03, -12))
        put("martin.step", "step_%d" % (i + 1), x)
    for i in range(3):
        rng(410 + i)
        put("martin.armor", "armor_%d" % (i + 1), plate(i))

    # sword
    for i in range(4):
        rng(415 + i)
        put("martin.swing", "swing_%d" % (i + 1), reverb(sword_swish(i), 0.8, 0.12))
    for i in range(3):
        rng(420 + i)
        x = mix((src("sword_clash_-_starninjas_0/sword_clash.%d.ogg" % (2 + 2 * i)), 0, -4), (src("80-CC0-RPG-SFX_0/blade_0%d.ogg" % (1 + i)), 0, 0),
                (thump(100, 55, 0.3, 0.06), 0, -4))
        put("martin.hit", "hit_%d" % (i + 1), reverb(x, 0.8, 0.15))
    for i in range(2):
        rng(424 + i)
        x = mix((thump(60, 30, 1.0, 0.25, 0.6), 0, 0), (src("sfx_breaking_and_falling/bfh1_rock_breaking_0%d.ogg" % (2 + i)), 0, -4),
                (src("sword_clash_-_starninjas_0/sword_clash.%d.ogg" % (6 + i)), 0, -6), (plate(i), 0.02, -8),
                (src("sfx_breaking_and_falling/bfh1_rock_falling_0%d.ogg" % (1 + i)), 0.1, -12))
        put("martin.slam", "slam_%d" % (i + 1), reverb(x, 1.8, 0.28))
    for i in range(2):
        rng(427 + i)
        put("martin.sword_ring", "sword_ring_%d" % (i + 1), reverb(mix((src("RPGsounds_Kenney/OGG/drawKnife%d.ogg" % (2 + i)), 0, 0),
                                                                        (metal_ring(1400 + 150 * i, 2.0, 0.9), 0.02, -6)), 1.6, 0.3))
    rng(430)
    put("martin.pierce", "pierce", reverb(mix((src("80-CC0-RPG-SFX_0/blade_03.ogg"), 0, 0), (thump(80, 40, 0.5, 0.1), 0, -2), (plate(1), 0.02, -8)), 1.0, 0.2))

    # shield
    for i in range(3):
        rng(432 + i)
        put("martin.shield_hit", "shield_hit_%d" % (i + 1), reverb(shield_hit(i), 1.0, 0.2))
    for i in range(2):
        rng(436 + i)
        x = mix((shield_hit(i + 1), 0, 0), (thump(70, 35, 0.6, 0.14, 0.4), 0, 0), (whoosh(0.3, 200, 1200), -0.0, -8), (plate(i), 0.02, -6))
        put("martin.bash", "bash_%d" % (i + 1), reverb(x, 1.2, 0.2))
    for i in range(2):
        rng(438 + i)
        x = mix((whoosh(0.5, 120, 900, 2.0, 1.6, 0.5), 0, 0), (plate(i, 1.4), 0.05, -2), (thump(85, 45, 0.3, 0.06), 0.3, -4), (plate(i + 2), 0.32, -6))
        put("martin.dash", "dash_%d" % (i + 1), x)
    rng(440)
    x = mix((shield_hit(0), 0, 0), (semis(src("100-CC0-wood-metal-SFX/metal_slam_01.ogg"), -3), 0, -2), (metal_ring(500, 1.6, 0.6), 0, -9),
            (thump(65, 32, 0.9, 0.22, 0.5), 0, -2))
    put("martin.block", "block", reverb(x, 2.0, 0.3))

    # command: drums + armor + horn stab ; drums one-shot ; horn
    for i in range(2):
        rng(442 + i)
        x = mix((drums(3.5 * i + 1.0, 2.0), 0, 0), (plate(i, 1.3), 0, -4), (sword_swish(i + 1), 0.0, -8), (thump(60, 32, 0.8, 0.2), 0, -6))
        put("martin.command", "command_%d" % (i + 1), reverb(x, 1.6, 0.25))
    for i in range(3):
        rng(445 + i)
        put("martin.drum", "drum_%d" % (i + 1), reverb(drums(4.0 * i + 0.5, 2.4), 1.6, 0.25))
    for i in range(2):
        rng(448 + i)
        put("martin.horn", "horn_%d" % (i + 1), reverb(mix((horn(i), 0, 0), (lp(drums(6.0, 2.5), 900), 0.2, -10)), 2.6, 0.35))

    # cavalry: rolling hooves growing, armor and harness
    rng(450)
    d = 4.0
    hv = mix((hooves(d, 8), 0, 0), (hooves(d, 7), 0.05, -2), (src("Trot.ogg", 0.0, d), 0, -6), length=d)
    hv *= np.interp(t_axis(d), [0, 1.2, 3.0, 4.0], [0.25, 1, 1, 0])
    x = mix((hv, 0, 0), (rumble(d, 90) * np.interp(t_axis(d), [0, 2, 4], [0.2, 1, 0]), 0, -4), (src("80-CC0-RPG-SFX_0/chain_01.ogg"), 1.0, -12),
            (src("80-CC0-RPG-SFX_0/chain_03.ogg"), 2.2, -12), (whoosh(1.2, 120, 900, 2.0, 1.2, 0.5), 2.4, -6))
    put("martin.gallop", "gallop", reverb(x, 1.8, 0.25))

    # banner
    for i in range(2):
        rng(452 + i)
        x = mix((thump(70, 35, 0.7, 0.16, 0.5), 0, 0), (src("100-CC0-wood-metal-SFX/wood_slam_0%d.ogg" % (1 + i)), 0, -2),
                (src("sfx_breaking_and_falling/bfh1_rock_hit_01.ogg"), 0, -6), (flap(1.6, 10), 0.05, -6))
        put("martin.banner_plant", "banner_plant_%d" % (i + 1), reverb(x, 1.6, 0.28))
    for i in range(3):
        rng(455 + i)
        put("martin.banner_flap", "banner_flap_%d" % (i + 1), flap(1.6 + 0.3 * i, 8 + 2 * i) * adsr(secs(1.6 + 0.3 * i), 0.2, 0.2, 0.8, 0.5))
    for i in range(2):
        rng(459 + i)
        put("martin.banner_hit", "banner_hit_%d" % (i + 1), mix((src("100-CC0-wood-metal-SFX/wood_hit_0%d.ogg" % (5 + i)), 0, 0), (flap(0.6, 12), 0.02, -8)))
    rng(462)
    x = mix((src("100-CC0-wood-metal-SFX/wood_breaking_01.ogg"), 0, 0), (src("100-CC0-wood-metal-SFX/wood_cracking_02.ogg"), 0.05, -3),
            (src("80-CC0-RPG-SFX_0/blade_02.ogg"), 0, -4), (flap(1.5, 12), 0.1, -8))
    put("martin.banner_cut", "banner_cut", reverb(x, 1.4, 0.25))
    rng(463)
    x = mix((rev(flap(0.8, 14)) * np.linspace(0, 1, secs(0.8)), 0, 0), (src("100-CC0-wood-metal-SFX/wood_falling_0%d.ogg" % 3), 0.7, 0), (thump(80, 40, 0.5, 0.12), 0.72, -4))
    put("martin.banner_fall", "banner_fall", reverb(x, 1.4, 0.25))

    # hold the line: shields up (many plates + shield hits) + a drum strike
    rng(465)
    x = mix(*[(shield_hit(k % 3), 0.05 * k, -2 * k) for k in range(5)], (drums(8.0, 1.6), 0, -6), (thump(60, 30, 0.8, 0.2), 0, -4))
    put("martin.hold", "hold", reverb(x, 1.8, 0.3))
    rng(466)
    x = mix(*[(shield_hit(k % 3), 0.07 * k, -1.5 * k) for k in range(7)], (thump(55, 28, 1.0, 0.3, 0.5), 0, 0), (rumble(1.6, 80, 0.5), 0, -6))
    put("martin.shield_wall", "shield_wall", reverb(x, 2.0, 0.3))

    # spectral soldiers: rising airy shimmer + ghostly armor; vanish: reverse
    rng(468)
    x = ghost(mix((rev(whoosh(1.0, 300, 2000)), 0, 0), (plate(0), 0.9, -4), (plate(2), 1.0, -6), (whisper(1.0, 3, 0.7), 0.1, -12)))
    put("martin.soldier", "soldier", x)
    rng(469)
    put("martin.soldier_vanish", "soldier_vanish", ghost(mix((whoosh(0.8, 2000, 300), 0, 0), (shimmer(0.8, 2200, 8, 1, 0.15), 0, -6)), 1.6))
    for i in range(3):
        rng(470 + i)
        x = mix((lp(src("metal_steps.ogg", starts[i + 3] - 0.02, 0.3), 3000), 0, 0), (plate(i), 0.02, -10))
        put("martin.soldier_step", "soldier_step_%d" % (i + 1), reverb(x, 1.2, 0.35, bright=5000))
    for i in range(2):
        rng(474 + i)
        put("martin.soldier_swing", "soldier_swing_%d" % (i + 1), ghost(sword_swish(i + 2), 1.0))

    # phase (2): horn + drums + armor of an army rising
    for i in range(2):
        rng(476 + i)
        x = mix((horn(1 - i), 0, 0), (drums(9.0 + 2 * i, 3.0), 0.2, -4), (thump(55, 28, 1.2, 0.3, 0.5), 0, -2),
                (mix(*[(plate(k % 3, 1.3), 0.12 * k, -3 - k) for k in range(6)]), 0.5, -4), (rumble(2.5, 90, 1.0), 0, -6))
        put("martin.phase", "phase_%d" % (i + 1), reverb(x, 2.4, 0.32))

    # volley: many bows loosing + arrows whistling; arrows land
    rng(480)
    x = mix(*[(semis(src("RPGsounds_Kenney/OGG/creak%d.ogg" % (1 + k % 3)), 6), 0.03 * k, -6) for k in range(4)],
            *[(whoosh(0.7, 1500, 3500, 0.8, 1.4, 0.3), 0.1 + 0.05 * k, -4 - k) for k in range(6)])
    put("martin.volley", "volley", reverb(x, 1.6, 0.3))
    for i in range(2):
        rng(482 + i)
        x = mix(*[(src("100-CC0-wood-metal-SFX/wood_hit_0%d.ogg" % (1 + (k + i) % 9)), uni(0, 0.4), -2 - 2 * k) for k in range(6)],
                (rev(whoosh(0.4, 2500, 4000)), 0, -10))
        put("martin.arrow_hit", "arrow_hit_%d" % (i + 1), reverb(x, 1.2, 0.2))

    # duel: sword raised with a ring + drum stroke ; warcry: drums + horn + armor + crowd-ish roar
    rng(485)
    x = mix((src("RPGsounds_Kenney/OGG/drawKnife2.ogg"), 0, 0), (metal_ring(1500, 2.4, 1.0), 0.02, -6), (drums(11.0, 1.2), 0.1, -6))
    put("martin.duel", "duel", reverb(x, 2.0, 0.35))
    rng(486)
    crowd = mix(*[(bp(semis(src("80-CC0-creature-SFX_0/roar_0%d.ogg" % (1 + k % 3)), -3 - k), 150, 2500), 0.04 * k, -3 * (k % 3)) for k in range(5)])
    x = mix((crowd, 0, -4), (horn(0), 0.1, -4), (drums(12.0, 2.5), 0, -4), (mix(*[(plate(k % 3), 0.1 * k, -4) for k in range(5)]), 0.05, -6),
            (thump(55, 28, 1.0, 0.3), 0, -4))
    put("martin.warcry", "warcry", reverb(x, 2.4, 0.35))

    rng(490)
    x = mix((sword_swish(3), 0, 0), (src("sword_clash_-_starninjas_0/sword_clash.9.ogg"), 0.15, -2), (src("sfx_breaking_and_falling/bfh1_glass_breaking_06.ogg"), 0.18, -8))
    put("martin.replica_break", "replica_break", reverb(x, 1.4, 0.25))
    for i in range(3):
        rng(492 + i)
        put("martin.hurt", "hurt_%d" % (i + 1), reverb(mix((src("100-CC0-wood-metal-SFX/metal_hit_0%d.ogg" % (2 + i)), 0, 0), (plate(i + 1, 1.3), 0.01, -3),
                                                         (thump(95, 50, 0.25, 0.05), 0, -6)), 0.8, 0.15))
    return F


ANIMS = {
    "martin.animation.json": {
        "martin_walk": [(0.4, "martin.step"), (1.2, "martin.step"), (0.42, "martin.armor|0.6")],
        "martin_swing": [(0.3, "martin.armor")],
        "martin_overhead": [(0.4, "martin.armor")],
        "martin_thrust": [(0.3, "martin.armor")],
        "martin_shield_bash": [(0.12, "martin.armor"), (0.45, "martin.dash|1.3")],
        "martin_command": [(0.3, "martin.armor")],
        "martin_volley": [(0.8, "martin.drum|2")],
        "martin_cavalry": [(0.3, "martin.armor"), (2.0, "martin.drum|2")],
        "martin_duel": [(0.3, "martin.armor"), (0.85, "martin.sword_ring|1.5")],
        "martin_warcry": [(0.2, "martin.armor")],
        "martin_guard_break": [(0.1, "martin.armor"), (0.55, "martin.swing|1.3")],
        "martin_banner_plant": [(0.7, "martin.banner_flap|1.5")],
        "martin_hold_the_line": [(0.15, "martin.armor|1.2")],
        "martin_hold_end": [(0.1, "martin.armor")],
        "martin_phase2": [(0.6, "martin.slam|1.5")],
        "martin_phase3": [(0.8, "martin.armor|1.5"), (1.4, "martin.swing|1.5")],
        "martin_spawn": [(1.0, "martin.armor"), (4.0, "martin.sword_ring|2"), (5.0, "martin.armor")],
        "martin_block_yield": [(1.2, "martin.armor")],
        "martin_shield_wall": [(0.15, "martin.armor|1.2")],
        "martin_finisher": [(0.8, "martin.armor"), (2.3, "martin.armor")],
        "martin_replica_break": [(0.4, "martin.shield_hit|1.5")],
        "martin_to_npc": [(0.2, "martin.armor")],
    },
    "martin_soldier.animation.json": {
        "martin_soldier_walk": [(0.25, "martin.soldier_step"), (0.75, "martin.soldier_step")],
        "martin_soldier_attack": [(0.3, "martin.soldier_swing")],
    },
    "martin_banner.animation.json": {
        "martin_banner_idle": [(0.0, "martin.banner_flap|0.5")],
        "martin_banner_hit": [(0.0, "martin.banner_hit")],
        "martin_banner_cut": [(1.0, "martin.banner_fall|1.5")],
    },
}

VIDEOS = {
    "martin_sound_1": ("t29_finale", {
        "martin_spawn": [(0, "martin.spawn"), (2.6, "martin.step"), (4.0, "martin.slam|0.6"), (5.0, "martin.command")],
        "martin_block_yield": [(0.2, "martin.block")],
        "martin_finisher": [(0, "martin.swing"), (0.4, "martin.pierce"), (1.7, "martin.swing"), (2.0, "martin.slam"), (2.0, "martin.shield_hit")],
        "martin_soldier:martin_soldier_vanish": [(0, "martin.soldier_vanish")],
    }, []),
    "martin_sound_2": ("t29_combat", {
        "martin_swing": [(0.6, "martin.swing"), (0.75, "martin.hit")],
        "martin_overhead": [(0.8, "martin.swing"), (0.95, "martin.slam")],
        "martin_thrust": [(0.55, "martin.swing"), (0.6, "martin.hit")],
        "martin_shield_bash": [(0.75, "martin.bash")],
        "martin_command": [(0.85, "martin.command")],
        "martin_banner_plant": [(1.3, "martin.banner_plant")],
        "martin_phase2": [(1.4, "martin.phase")],
        "martin_phase3": [(2.0, "martin.phase")],
        "martin_soldier:martin_soldier_spawn": [(0, "martin.soldier")],
        "martin_soldier:martin_soldier_vanish": [(0, "martin.soldier_vanish")],
        "martin_banner:martin_banner_cut": [(0, "martin.banner_cut")],
    }, []),
    "martin_sound_3": ("t29_spells", {
        "martin_cavalry": [(1.0, "martin.horn"), (2.0, "martin.gallop")],
        "martin_hold_the_line": [(1.1, "martin.hold")],
        "martin_shield_wall": [(1.0, "martin.shield_wall")],
        "martin_volley": [(1.2, "martin.volley"), (1.5, "martin.arrow_hit")],
        "martin_duel": [(0.9, "martin.duel")],
        "martin_warcry": [(0.6, "martin.warcry")],
    }, []),
}
