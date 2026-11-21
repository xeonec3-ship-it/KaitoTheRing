"""«Эреб, Длань Лжи» (T31): стекло и золото, огромная рука (низкий гул), маска (треск), ложное пламя."""
from sfx import *  # noqa: F401,F403
from ereb import chime, glass_break, glass_tinkle, illusion_swell, rapier_swish  # noqa: F401

B = "ereb_hand"

EVENTS = {
    "ereb_hand.aura": ("Длань Лжи: гул руки и звон золота", "Hand of Lies: the hand hums, gold chimes", 24, 0.25),
    "ereb_hand.hum": ("Огромная рука гудит", "The giant hand hums", 48, 1.0),
    "ereb_hand.whoosh_big": ("Огромная рука рассекает воздух", "The giant hand sweeps", 40, 1.0),
    "ereb_hand.slam": ("Рука обрушивается", "The hand slams down", 64, 1.0),
    "ereb_hand.grab": ("Рука хватает", "The hand grabs", 40, 1.0),
    "ereb_hand.squeeze": ("Стеклянные пальцы сжимаются", "Glass fingers squeeze", 32, 1.0),
    "ereb_hand.grip": ("Стеклянная хватка", "Glass grip", 32, 1.0),
    "ereb_hand.crack": ("Маска трескается", "The mask cracks", 40, 1.0),
    "ereb_hand.mask": ("Маска скрипит", "The mask creaks", 20, 1.0),
    "ereb_hand.mask_shatter": ("Маска разбита", "The mask shatters", 56, 1.0),
    "ereb_hand.shard_ring": ("Осколки звенят", "Shards ring", 24, 1.0),
    "ereb_hand.shard_break": ("Осколок разбит", "Shard breaks", 24, 1.0),
    "ereb_hand.shard_burst": ("Осколки взрываются", "Shards burst", 40, 1.0),
    "ereb_hand.flame": ("Ложное пламя", "False flame", 40, 1.0),
    "ereb_hand.flame_charge": ("Ложное пламя набирается", "False flame gathers", 24, 1.0),
    "ereb_hand.changeling": ("Пламя-подменыш", "Changeling flame", 32, 1.0),
    "ereb_hand.oath": ("Чужая клятва", "Foreign oath", 32, 1.0),
    "ereb_hand.mirror": ("Зеркала встают", "Mirrors rise", 32, 1.0),
    "ereb_hand.reflection": ("Отражение предаёт", "A traitor reflection emerges", 32, 1.0),
    "ereb_hand.sky_hand": ("Рука в небе", "The hand in the sky", 80, 1.0),
    "ereb_hand.reveal": ("Длань раскрывается", "The Hand reveals itself", 64, 1.0),
    "ereb_hand.dissolve": ("Ложь рассыпается", "The lie dissolves", 48, 1.0),
    "ereb_hand.retreat": ("Ложное отступление", "False retreat", 24, 1.0),
    "ereb_hand.swarm": ("Рой лжи", "Swarm of lies", 32, 1.0),
    "ereb_hand.swarm_chime": ("Бабочки лжи звенят", "Butterflies of lies chime", 12, 0.5),
    "ereb_hand.false_victory": ("Ложная победа", "False victory", 48, 1.0),
    "ereb_hand.dawn_wave": ("Ложный рассвет", "False dawn", 80, 1.0),
    "ereb_hand.replica_break": ("Реплика раздавлена рукой", "Replica crushed by the hand", 32, 1.0),
    "ereb_hand.step": ("Шаги Длани", "The Hand's steps", 12, 0.7),
    "ereb_hand.hurt": ("Длань ранена: стекло и золото", "Hand of Lies hurts", 16, 1.0),
}


def gold(f=900, d=1.6):
    """Gold: a warmer, lower bell than glass."""
    return bell(f, d, ((1, 1, 1), (2.0, .5, .7), (3.01, .35, .5), (4.2, .2, .35), (5.4, .12, .25)), 0.6, 0.002)


def giant_hum(d=3.0, f=36.7):
    """The giant hand: a deep beating drone with glassy overtones."""
    t = t_axis(d)
    x = sine(f, d) + 0.6 * sine(f * 1.01, d) + 0.4 * sine(f * 2, d) + 0.2 * sine(f * 3.02, d)
    beat = 0.7 + 0.3 * np.sin(2 * np.pi * 0.8 * t)
    over = lp(drone(f * 4, d, 4, 0.008, 900), 900)
    return norm(mix((x * beat, 0, 0), (over, 0, -10), (shimmer(d, 1400, int(d * 3), 1.0, 0.5), 0, -22)))


def big_whoosh(d=0.9, i=0):
    return mix((whoosh(d, 60 + 10 * i, 500 + 80 * i, 2.0, 1.8, 0.6), 0, 0), (sine(45, d, 30) * adsr(secs(d), d * 0.5, 0.1, 0.6, d * 0.3), 0, -6),
               (glass_tinkle(d, 5, 2400), d * 0.4, -16))


def false_fire(d=1.4, fc=1100):
    """«Ложное пламя»: fire roar ring-modulated a little and with a glass shimmer — fire that isn't quite fire."""
    f = fire_roar(d, fc)
    f = mix((f, 0, 0), (bitcrush_ring(lp(f, 3000), 37), 0, -8), (shimmer(d, 2200, int(d * 6), 1.0, 0.2), 0, -12))
    return norm(f)


def mask_crack(i=0):
    c = src("100-CC0-wood-metal-SFX/wood_cracking_0%d.ogg" % (1 + i % 4))
    g = src("sfx_100_v2/sfx100v2_glass_0%d.ogg" % (1 + (i + 2) % 6))
    return mix((c, 0, 0), (g, 0.02, -4), (gold(700 + 60 * i, 0.8), 0.01, -12))


def build():
    F = {}

    def put(ev, name, x, **kw):
        F.setdefault(ev, []).append(write("%s/%s" % (B, name), x, **kw).split("sounds/boss/")[1][:-4])

    rng(601)
    d = 8.0
    g = np.zeros(secs(d))
    for at in (0.8, 3.5, 6.2):
        c = gold(uni(700, 1100), 2.0) * uni(0.4, 0.8)
        g[secs(at):secs(at) + len(c)] += c[: len(g) - secs(at)]
    F["ereb_hand.aura"] = [write_loop("%s/aura" % B, mix((giant_hum(d, 41.2), 0, 0), (reverb(g, 2.4, 0.5)[: secs(d)], 0, -10),
                                                        (lp(whisper(d, 6, 0.8), 2500), 0, -22)), 1.0, 0.5).split("sounds/boss/")[1][:-4]]

    for i in range(2):
        rng(603 + i)
        x = giant_hum(2.4, 36.7 + 4 * i) * adsr(secs(2.4), 0.5, 0.3, 0.8, 0.8)
        put("ereb_hand.hum", "hum_%d" % (i + 1), reverb(mix((x, 0, 0), (illusion_swell(1.6, True), 0.2, -10)), 2.0, 0.3))
    for i in range(3):
        rng(606 + i)
        put("ereb_hand.whoosh_big", "whoosh_big_%d" % (i + 1), reverb(big_whoosh(0.9 + 0.1 * i, i), 1.4, 0.25))
    for i in range(2):
        rng(609 + i)
        x = mix((thump(48, 24, 1.4, 0.4, 0.6), 0, 0), (glass_break(i, 1.6), 0, -2), (gold(420 + 40 * i, 2.0), 0, -8),
                (src("sfx_breaking_and_falling/bfh1_rock_breaking_0%d.ogg" % (1 + i)), 0, -4), (rumble(2.0, 70, 0.8), 0, -6))
        put("ereb_hand.slam", "slam_%d" % (i + 1), reverb(x, 2.4, 0.35))
    for i in range(2):
        rng(612 + i)
        x = mix((big_whoosh(0.5, i), 0, -4), (src("sfx_breaking_and_falling/bfh1_glass_hit_0%d.ogg" % (1 + i)), 0.4, 0), (thump(70, 35, 0.6, 0.15), 0.4, -4),
                (gold(800, 1.2), 0.42, -10))
        put("ereb_hand.grab", "grab_%d" % (i + 1), reverb(x, 1.6, 0.3))
    for i in range(2):
        rng(615 + i)
        cr = mix(*[(src("sfx_100_v2/sfx100v2_glass_0%d.ogg" % (1 + (k + i) % 6)), 0.08 * k, -3 * k) for k in range(4)])
        x = mix((string_creak(1.0, 90, 160, 25), 0, -4), (cr, 0.1, 0), (thump(80, 40, 0.5, 0.1), 0.3, -6))
        put("ereb_hand.squeeze", "squeeze_%d" % (i + 1), reverb(x, 1.4, 0.25))
    rng(618)
    put("ereb_hand.grip", "grip", reverb(mix((string_creak(0.8, 120, 200, 30), 0, -4), (glass_tinkle(0.8, 8, 2600), 0, -4), (src("sfx_breaking_and_falling/bfh1_glass_hit_02.ogg"), 0.5, 0)), 1.4, 0.25))
    for i in range(3):
        rng(620 + i)
        put("ereb_hand.crack", "crack_%d" % (i + 1), reverb(mask_crack(i), 1.6, 0.3))
    for i in range(2):
        rng(624 + i)
        put("ereb_hand.mask", "mask_%d" % (i + 1), reverb(mix((semis(src("RPGsounds_Kenney/OGG/creak%d.ogg" % (1 + i)), 4), 0, 0), (gold(1200, 0.6), 0.05, -14)), 1.0, 0.2))
    rng(626)
    x = mix((glass_break(4, 1.4), 0, 0), (glass_break(1, 1.0), 0.04, -3), (mask_crack(2), 0, -2), (gold(330, 3.0), 0.02, -6), (thump(55, 28, 1.2, 0.3), 0, -3),
            (glass_tinkle(2.0, 18, 2600), 0.15, -8))
    put("ereb_hand.mask_shatter", "mask_shatter", reverb(x, 2.6, 0.4))
    for i in range(2):
        rng(628 + i)
        put("ereb_hand.shard_ring", "shard_ring_%d" % (i + 1), reverb(mix((chime(2600 + 400 * i, 1.4, 3), 0, 0), (gold(1100, 1.2), 0, -10)), 1.8, 0.35))
    for i in range(3):
        rng(631 + i)
        put("ereb_hand.shard_break", "shard_break_%d" % (i + 1), reverb(glass_break(i + 2), 1.4, 0.25))
    for i in range(2):
        rng(634 + i)
        x = mix((semis(src("25-CC0-bang-sfx/bang_0%d.ogg" % (1 + 3 * i)), 3), 0, -4), (glass_break(i, 1.0), 0, 0), (glass_break(i + 3, 0.8), 0.05, -4),
                (glass_tinkle(1.2, 16, 3000), 0.05, -6))
        put("ereb_hand.shard_burst", "shard_burst_%d" % (i + 1), reverb(x, 1.8, 0.3))
    for i in range(2):
        rng(637 + i)
        x = mix((false_fire(1.8, 1000 + 200 * i) * adsr(secs(1.8), 0.05, 0.3, 0.7, 0.8), 0, 0), (src("flame.ogg"), 0, -4), (gold(600, 1.4), 0.05, -12))
        put("ereb_hand.flame", "flame_%d" % (i + 1), reverb(x, 1.8, 0.3))
    rng(640)
    put("ereb_hand.flame_charge", "flame_charge", reverb(rev(false_fire(1.0, 1200)) * np.linspace(0.3, 1, secs(1.0)), 1.0, 0.2))
    for i in range(2):
        rng(642 + i)
        x = mix((false_fire(0.9, 1500), 0, 0), (whoosh(0.5, 400, 2500), 0, -4), (illusion_swell(0.6, False), 0.3, -10))
        put("ereb_hand.changeling", "changeling_%d" % (i + 1), reverb(x, 1.4, 0.25))
    rng(645)
    put("ereb_hand.oath", "oath", reverb(mix((whisper(1.4, 5, 0.75), 0, 0), (gold(500, 2.0), 0.4, -4), (bell(250, 2.0, tau=0.8), 0.42, -10)), 2.2, 0.4))
    for i in range(2):
        rng(647 + i)
        x = mix((illusion_swell(1.0, True), 0, 0), (rev(src("sfx_breaking_and_falling/bfh1_glass_falling_0%d.ogg" % (1 + i))), 0.1, -4), (chime(1800, 1.4, 4), 0.8, -4))
        put("ereb_hand.mirror", "mirror_%d" % (i + 1), reverb(x, 2.0, 0.4))
    rng(650)
    put("ereb_hand.reflection", "reflection", reverb(mix((illusion_swell(1.2, True), 0, 0), (whisper(1.0, 4, 0.7), 0.3, -6), (rapier_swish(2), 1.0, -4)), 2.0, 0.4))
    rng(651)
    x = mix((giant_hum(4.0, 30.9) * adsr(secs(4.0), 1.0, 0.5, 0.8, 1.2), 0, 0), (big_whoosh(1.6, 2), 1.2, -2), (gold(260, 3.0), 1.0, -8), (rumble(3.5, 60, 1.6), 0.4, -4))
    put("ereb_hand.sky_hand", "sky_hand", reverb(x, 3.0, 0.4))
    rng(652)
    x = mix((illusion_swell(1.5, True), 0, 0), (gold(440, 3.0), 1.2, -2), (gold(660, 3.0), 1.25, -6), (chime(2200, 2.4, 5), 1.2, -4),
            (giant_hum(3.0, 41.2) * adsr(secs(3.0), 0.8, 0.4, 0.7, 1.0), 0.5, -6))
    put("ereb_hand.reveal", "reveal", reverb(x, 3.0, 0.45))
    for i in range(2):
        rng(654 + i)
        x = mix((illusion_swell(1.8, False), 0, 0), (glass_tinkle(2.0, 24, 2400), 0.1, -4), (rev(gold(700, 1.4)), 0, -10))
        put("ereb_hand.dissolve", "dissolve_%d" % (i + 1), reverb(x, 2.6, 0.45))
    rng(657)
    put("ereb_hand.retreat", "retreat", reverb(mix((src("RPGsounds_Kenney/OGG/cloth4.ogg"), 0, 0), (whoosh(0.5, 300, 1800), 0, -4), (illusion_swell(0.6, False), 0.2, -10)), 1.2, 0.25))
    rng(658)
    d = 1.6
    fl = np.zeros(secs(d))
    for k in range(18):
        a = secs(uni(0, d - 0.4))
        w = bp(noise(0.35), 1800, 6000) * (0.5 + 0.5 * np.sin(2 * np.pi * uni(18, 28) * t_axis(0.35))) * np.hanning(secs(0.35))
        fl[a:a + len(w)] += w * uni(0.3, 1)
    put("ereb_hand.swarm", "swarm", reverb(mix((fl, 0, 0), (glass_tinkle(d, 14, 3000), 0, -2), (gold(900, 1.0), 0, -10)), 1.8, 0.35))
    for i in range(3):
        rng(660 + i)
        put("ereb_hand.swarm_chime", "swarm_chime_%d" % (i + 1), glass_ping(3400 + 500 * i, 0.6, 0.12))
    rng(664)
    # false victory: a bright, too-sweet major chord of bells (the lie)
    x = mix(*[(gold(f, 3.0), 0.12 * k, -2 * k) for k, f in enumerate((523.3, 659.3, 784.0, 1046.5))], (chime(2600, 2.0, 4), 0.5, -8))
    put("ereb_hand.false_victory", "false_victory", reverb(x, 2.8, 0.45))
    rng(665)
    x = mix((whoosh(2.0, 80, 900, 2.2, 1.2, 0.35), 0, 0), (giant_hum(2.6, 36.7) * env_exp(secs(2.6), 1.0), 0, -4), (glass_break(5, 1.4), 0.3, -4),
            (gold(330, 3.0), 0.3, -6), (glass_tinkle(2.4, 26, 2800), 0.4, -6), (thump(50, 25, 1.4, 0.4), 0.3, -2))
    put("ereb_hand.dawn_wave", "dawn_wave", reverb(x, 3.0, 0.4))
    rng(667)
    put("ereb_hand.replica_break", "replica_break", reverb(mix((src("sfx_breaking_and_falling/bfh1_glass_hit_01.ogg"), 0, 0), (glass_break(5, 1.2), 0.05, 0),
                                                              (gold(600, 1.6), 0.05, -8)), 1.8, 0.35))
    for i in range(4):
        rng(670 + i)
        st = src("RPGsounds_Kenney/OGG/footstep0%d.ogg" % (i * 2))
        put("ereb_hand.step", "step_%d" % (i + 1), mix((hp(st, 150), 0, 0), (thump(100, 55, 0.2, 0.04), 0, -10), (gold(1300 + 150 * i, 0.4), 0.01, -24)))
    for i in range(3):
        rng(675 + i)
        put("ereb_hand.hurt", "hurt_%d" % (i + 1), reverb(mix((src("sfx_100_v2/sfx100v2_glass_0%d.ogg" % (1 + 2 * i % 6)), 0, 0), (gold(800 + 100 * i, 0.6), 0, -8)), 0.8, 0.15))
    return F


ANIMS = {
    "ereb_hand.animation.json": {
        "ereb_hand_walk": [(0.3, "ereb_hand.step"), (0.9, "ereb_hand.step")],
        "ereb_hand_lunge": [(0.25, "ereb.cloth"), (0.32, "ereb.swish")],
        "ereb_hand_flurry": [(0.3, "ereb.swish"), (0.65, "ereb.swish"), (1.0, "ereb.swish")],
        "ereb_hand_slam": [(0.45, "ereb_hand.whoosh_big|1.5")],
        "ereb_hand_grab": [(0.3, "ereb_hand.whoosh_big")],
        "ereb_hand_squeeze": [(0.05, "ereb_hand.mask")],
        "ereb_hand_grab_release": [(0.2, "ereb_hand.whoosh_big|0.8|1.2")],
        "ereb_hand_cast": [(0.3, "ereb.cloth")],
        "ereb_hand_spawn": [(0.3, "ereb_hand.hum|2"), (2.6, "ereb.cloth"), (3.4, "ereb.glint|1.5"), (4.3, "ereb.whisper|1.5")],
        "ereb_hand_phase2": [(0.3, "ereb.whisper|1.5")],
        "ereb_hand_phase3": [(0.3, "ereb_hand.hum|2")],
        "ereb_hand_hand_of_lies": [(0.5, "ereb_hand.hum|3"), (1.2, "ereb_hand.whoosh_big|3|0.8")],
        "ereb_hand_mask_fall": [(0.5, "ereb_hand.mask|2")],
        "ereb_hand_mask_return": [(0.3, "ereb_hand.mask")],
        "ereb_hand_full_reveal": [(1.4, "ereb_hand.hum|2")],
        "ereb_hand_false_death": [(0.4, "ereb.cloth"), (2.6, "ereb.whisper|1.5")],
        "ereb_hand_finisher": [(0.3, "ereb_hand.whoosh_big")],
        "ereb_hand_replica_break": [(0.55, "ereb.glint|1.3")],
        "ereb_hand_false_flame": [(0.2, "ereb_hand.flame_charge")],
        "ereb_hand_glass_grip": [(0.0, "ereb_hand.hum|1.5")],
        "ereb_hand_foreign_oath": [(0.2, "ereb.whisper")],
        "ereb_hand_thousand_reflections": [(0.2, "ereb.cloth")],
        "ereb_hand_reflection_strike": [(0.3, "ereb.swish")],
        "ereb_hand_changeling_flame": [(0.2, "ereb_hand.flame_charge")],
        "ereb_hand_false_retreat": [(0.65, "ereb_hand.step|2")],
        "ereb_hand_false_retreat_strike": [(0.2, "ereb.swish")],
        "ereb_hand_traitor_reflection": [(0.2, "ereb.whisper")],
        "ereb_hand_swarm_of_lies": [(0.3, "ereb.whisper")],
        "ereb_hand_false_dawn": [(0.5, "ereb_hand.step|1.5"), (4.5, "ereb.cloth")],
        "ereb_hand_guard_break": [(0.1, "ereb_hand.hum|1.3"), (0.55, "ereb.swish|1.3")],
    },
    "ereb_hand_giant.animation.json": {
        "ereb_hand_giant_descend": [(0.0, "ereb_hand.hum|3")],
        "ereb_hand_giant_slam": [(0.3, "ereb_hand.whoosh_big|3")],
        "ereb_hand_giant_release": [(0.2, "ereb_hand.whoosh_big|2|1.2")],
    },
}

VIDEOS = {
    "ereb_hand_sound_1": ("t31_finale", {
        "ereb_hand_spawn": [(0, "ereb.spawn"), (0.6, "ereb_hand.grab"), (1.8, "ereb.appear")],
        "ereb_hand_full_reveal": [(0.8, "ereb.butterfly"), (2.6, "ereb_hand.reveal")],
        "ereb_hand_giant:ereb_hand_giant_slam": [(0.0, "ereb_hand.sky_hand"), (0.55, "ereb_hand.slam")],
        "ereb_hand_false_death": [(0.4, "ereb_hand.crack"), (0.7, "ereb_hand.shard_break"), (3.8, "ereb_hand.dissolve")],
        "ereb_hand_finisher": [(0.6, "ereb_hand.grab"), (1.5, "ereb_hand.squeeze"), (2.1, "ereb_hand.dissolve")],
    }, []),
    "ereb_hand_sound_2": ("t31_combat", {
        "ereb_hand_lunge": [(0.5, "ereb.thrust")],
        "ereb_hand_flurry": [(0.45, "ereb.thrust"), (0.8, "ereb.thrust"), (1.15, "ereb.thrust")],
        "ereb_hand_slam": [(0.8, "ereb_hand.slam")],
        "ereb_hand_grab": [(0, "ereb_hand.grip"), (0.6, "ereb_hand.grab")],
        "ereb_hand_squeeze": [(0.35, "ereb_hand.squeeze")],
        "ereb_hand_grab_release": [(0.2, "ereb_hand.shard_break")],
        "ereb_hand_cast": [(0, "ereb.cast")],
        "ereb_hand_phase2": [(0.8, "ereb.phase")],
        "ereb_hand_phase3": [(0.9, "ereb_hand.crack"), (0.9, "ereb.phase"), (1.0, "ereb_hand.flame")],
    }, []),
    "ereb_hand_sound_3": ("t31_special", {
        "ereb_hand_hand_of_lies": [(0, "ereb.cast")],
        "ereb_hand_giant:ereb_hand_giant_descend": [(0.0, "ereb_hand.sky_hand")],
        "ereb_hand_giant:ereb_hand_giant_grab": [(0.25, "ereb_hand.grab")],
        "ereb_hand_mask_fall": [(0.85, "ereb_hand.crack"), (1.1, "ereb_hand.mask_shatter")],
        "ereb_hand_mask_return": [(0.7, "ereb_hand.crack")],
    }, []),
    "ereb_hand_sound_4": ("t31_spells", {
        "ereb_hand_false_flame": [(0.6, "ereb_hand.flame"), (1.0, "ereb_hand.flame")],
        "ereb_hand_glass_grip": [(1.0, "ereb_hand.grip")],
        "ereb_hand_foreign_oath": [(0.6, "ereb_hand.oath")],
        "ereb_hand_thousand_reflections": [(0.6, "ereb_hand.mirror")],
        "ereb_reflection:ereb_hand_reflection_strike": [(0.0, "ereb_hand.mirror|0.6"), (0.45, "ereb.thrust")],
    }, []),
    "ereb_hand_sound_5": ("t31_spells2", {
        "ereb_hand_changeling_flame": [(0.65, "ereb_hand.changeling")],
        "ereb_hand_false_retreat": [(0.25, "ereb_hand.retreat")],
        "ereb_hand_false_retreat_strike": [(0, "ereb.appear"), (0.35, "ereb.thrust")],
        "ereb_hand_traitor_reflection": [(0.5, "ereb_hand.mirror"), (1.2, "ereb_hand.reflection")],
        "traitor:instant_slash": [(0.1, "ereb.swish")],
        "ereb_hand_swarm_of_lies": [(0.75, "ereb_hand.swarm"), (1.2, "ereb_hand.swarm_chime"), (1.6, "ereb_hand.swarm_chime")],
        "ereb_hand_false_dawn": [(0.5, "ereb_hand.false_victory"), (4.5, "ereb.appear"), (5.0, "ereb_hand.dawn_wave")],
    }, []),
}
