"""Глава Культа (T26): огонь, пепел, тяжёлая коса, гул культа."""
from sfx import *  # noqa: F401,F403

B = "cult_leader"

# event: (subtitle ru, subtitle en, attenuation distance, volume)
EVENTS = {
    "cult_leader.aura": ("Глава Культа: гул пламени", "Cult Leader: flames hum", 20, 0.35),
    "cult_leader.spawn": ("Глава Культа восходит из пламени", "Cult Leader rises from the flames", 64, 1.0),
    "cult_leader.firewall": ("Стена огня вспыхивает", "Wall of fire flares up", 48, 1.0),
    "cult_leader.phase": ("Глава Культа разгорается", "Cult Leader blazes up", 64, 1.0),
    "cult_leader.verdict": ("Приговор Меллисто: звон", "Mellisto's Verdict tolls", 48, 1.0),
    "cult_leader.verdict_lock": ("Приговор вынесен", "Verdict is sealed", 48, 1.0),
    "cult_leader.verdict_end": ("Приговор угасает", "Verdict fades", 24, 1.0),
    "cult_leader.summon": ("Культисты призваны", "Cultists summoned", 40, 1.0),
    "cult_leader.first_flame": ("Первое Пламя набирает силу", "First Flame gathers", 64, 1.0),
    "cult_leader.first_flame_impact": ("Столп пламени", "Pillar of flame", 64, 1.0),
    "cult_leader.ash": ("Глава Культа рассыпается пеплом", "Cult Leader crumbles to ash", 40, 1.0),
    "cult_leader.ash_reform": ("Пепел собирается", "Ash gathers", 32, 1.0),
    "cult_leader.ash_slash": ("Пепельный разрез", "Ash slash", 56, 1.0),
    "cult_leader.replica_break": ("Реплика сгорает", "Replica burns", 32, 1.0),
    "cult_leader.finisher": ("Коса цепляет жертву", "Scythe hooks the victim", 32, 1.0),
    "cult_leader.impale": ("Коса пронзает", "Scythe impales", 32, 1.0),
    "cult_leader.flame": ("Жертва вспыхивает", "Victim bursts into flame", 32, 1.0),
    "cult_leader.death_final": ("Пламя Главы Культа гаснет", "Cult Leader's flame dies", 64, 1.0),
    "cult_leader.scythe": ("Свист косы", "Scythe swings", 20, 1.0),
    "cult_leader.inhale": ("Пламя втягивается", "Flames draw in", 24, 1.0),
    "cult_leader.sickle_throw": ("Огненный серп летит", "Fire sickle whirls", 32, 1.0),
    "cult_leader.sickle_catch": ("Серп пойман", "Sickle caught", 20, 1.0),
    "cult_leader.dash": ("Пепельный рывок", "Ash dash", 32, 1.0),
    "cult_leader.brand": ("Клеймо шипит", "Brand sizzles", 24, 1.0),
    "cult_leader.brand_explode": ("Клеймо взрывается", "Brand explodes", 40, 1.0),
    "cult_leader.pillars_mark": ("Земля трескается от жара", "Ground cracks with heat", 32, 1.0),
    "cult_leader.plant": ("Коса вонзается в землю", "Scythe planted", 32, 1.0),
    "cult_leader.sigil": ("Знак Меллисто загорается", "Mellisto's sigil ignites", 40, 1.0),
}


def scythe_swish(i):
    """Heavy scythe: low long whoosh + fire trail + a faint blade ring."""
    d = 0.55 + 0.08 * i
    w = whoosh(d, 140 + 30 * i, 900 + 150 * i, 1.8, 2.0, 0.6)
    trail = lp(noise(d, "pink"), 700) * adsr(secs(d), 0.15, 0.1, 0.8, 0.25)
    ring = metal_ring(820 + 60 * i, 0.9, 0.25)
    sw = semis(src("swishes/swishes/swish-%d.wav" % (3 + 2 * i)), -7)
    return reverb(mix((w, 0, 0), (trail, 0.05, -9), (sw, 0.12, -4), (ring, d * 0.6, -20)), 0.9, 0.18)


def fire_burst(d=1.2, i=0):
    f = src("80-CC0-RPG-SFX_0/spell_fire_0%d.ogg" % (1 + i % 7))
    return mix((f, 0, 0), (fire_roar(d, 900) * env_exp(secs(d), d / 3), 0, -6), (thump(80, 40, 0.5, 0.1), 0, -8))


def chant(d=3.0, base=0.8):
    """Cult hum: low detuned vowel choir + whispers."""
    t = t_axis(d)
    body = np.zeros(len(t))
    for f in (55, 82.4, 110, 164.8):
        v = saw(f, d, 0.004, 3)
        body += bp(v, 200, 1200) * (0.6 if f < 100 else 0.4)
    body = peak_eq(body, 700, 8, 1.5)
    return norm(mix((norm(body) * adsr(len(t), 0.6, 0.3, 0.8, 0.8), 0, 0), (whisper(d, 8, base), 0, -13)))


def build():
    F = {}

    def put(ev, name, x, **kw):
        F.setdefault(ev, []).append(write("%s/%s" % (B, name), x, **kw).split("sounds/boss/")[1][:-4])

    rng(1)
    # aura: low fire hum, embers, slow breathing — quiet loop
    d = 8.0
    hum = drone(41.2, d, 5, 0.004, 220)
    t = t_axis(d)
    breath = 0.75 + 0.25 * np.sin(2 * np.pi * t / d * 2)
    fire = lp(noise(d, "pink"), 500) * (0.7 + 0.3 * np.sin(2 * np.pi * t / d * 3 + 1))
    emb = crackle(d, 6, 0.003, 2500)
    write_loop_ev = mix((hum * breath, 0, -4), (fire, 0, -8), (emb, 0, -28))
    F["cult_leader.aura"] = [write_loop("%s/aura" % B, write_loop_ev, 1.0, 0.45).split("sounds/boss/")[1][:-4]]

    # spawn: rumble swell -> choir -> flame eruption + gong + scythe ring
    rng(2)
    sw = rumble(5.5, 110) * np.concatenate([np.linspace(0, 1, secs(2.6)) ** 2, np.exp(-np.arange(secs(2.9)) / (1.2 * SR))])
    gong = semis(src("100-CC0-SFX_0/gong_01.ogg"), -5)
    x = mix((sw, 0, 0), (chant(4.0, 0.7), 0.4, -6), (fire_burst(2.0, 3), 2.6, 0), (gong, 2.6, -3),
            (thump(55, 30, 1.2, 0.35), 2.6, 0), (metal_ring(310, 2.5, 0.9), 2.75, -12), (fire_roar(2.5, 700) * env_exp(secs(2.5), 0.9), 2.7, -6))
    put("cult_leader.spawn", "spawn", reverb(x, 2.6, 0.35))

    # firewall: rising roar of a ring of flame
    for i in range(2):
        rng(10 + i)
        d = 2.4
        r = fire_roar(d, 1200) * np.concatenate([np.linspace(0.1, 1, secs(0.5)), np.exp(-np.arange(secs(d - 0.5)) / (0.9 * SR))])
        x = mix((r, 0, 0), (whoosh(1.0, 120, 1400, 2.0, 1.5, 0.7), 0, -4), (src("flame.ogg"), 0.05, -3),
                (src("80-CC0-RPG-SFX_0/spell_fire_0%d.ogg" % (4 + i)), 0.2, -4), (thump(70, 35, 0.6, 0.15), 0.3, -6))
        put("cult_leader.firewall", "firewall_%d" % (i + 1), reverb(x, 1.8, 0.3))

    # phase: gong + roar of fire + low impact
    for i in range(2):
        rng(20 + i)
        g = semis(src("100-CC0-SFX_0/gong_0%d.ogg" % (1 + i)), -7 - i)
        roar = semis(src("80-CC0-RPG-SFX_0/creature_roar_0%d.ogg" % (1 + i)), -7)
        x = mix((thump(60, 28, 1.4, 0.4, 0.5), 0, 0), (g, 0, -2), (fire_burst(2.0, 1 + i), 0.05, -1),
                (lp(roar, 1500), 0.1, -9), (rumble(2.5, 90, 0.8), 0, -6))
        put("cult_leader.phase", "phase_%d" % (i + 1), reverb(x, 2.4, 0.35))

    # verdict: a deep bell toll over the cult hum
    rng(30)
    g = semis(src("100-CC0-SFX_0/gong_02.ogg"), -10)
    x = mix((chant(3.2, 0.7), 0, -3), (g, 0, 0), (g, 1.4, -6), (rumble(3.0, 70, 1.2), 0, -8))
    put("cult_leader.verdict", "verdict", reverb(x, 2.8, 0.4))
    rng(31)
    ch = src("80-CC0-RPG-SFX_0/chain_02.ogg")
    x = mix((semis(g, 2), 0, 0), (semis(ch, -4), 0, -4), (thump(55, 30, 1.0, 0.3), 0, -2), (src("80-CC0-RPG-SFX_0/lock_02.ogg"), 0.02, -8))
    put("cult_leader.verdict_lock", "verdict_lock", reverb(x, 2.2, 0.3))
    rng(32)
    x = mix((fire_burst(0.9, 5), 0, 0), (hiss(1.2, 4000, 0.4), 0.1, -10), (rev(whoosh(0.6, 300, 1500)), 0, -10))
    put("cult_leader.verdict_end", "verdict_end", reverb(x, 1.4, 0.25))

    # summon: fire swirl + whispered chant
    rng(40)
    sw = sweep_filter(noise(1.8, "pink"), 180, 1400, 1.6) * adsr(secs(1.8), 0.6, 0.2, 0.8, 0.6)
    x = mix((sw, 0, 0), (chant(2.0, 0.9), 0, -5), (src("80-CC0-RPG-SFX_0/spell_fire_06.ogg"), 1.1, -3), (crackle(1.8, 20), 0.4, -16))
    put("cult_leader.summon", "summon", reverb(x, 1.8, 0.3))

    # first flame: 4 s charge (pitch rising roar + hum + whispers) peaking at 4.0 (the pillar)
    rng(50)
    d = 4.2
    t = t_axis(d)
    rise = np.linspace(0, 1, len(t)) ** 2.2
    hum = sine(55, d, 110) + 0.5 * sine(82.5, d, 165) + 0.3 * sine(110, d, 220)
    roar = sweep_filter(noise(d, "pink"), 150, 2200, 2.0)
    x = mix((hum * rise, 0, -6), (roar * rise, 0, 0), (whisper(3.0, 10, 0.8) * 0.8, 0.5, -10), (chant(3.5, 0.8), 0.2, -8))
    put("cult_leader.first_flame", "first_flame", reverb(x, 2.0, 0.3))
    for i in range(2):
        rng(55 + i)
        bang = semis(src("25-CC0-bang-sfx/cannon_0%d.ogg" % (2 + i)), -5)
        deb = src("sfx_breaking_and_falling/bfh1_rock_falling_0%d.ogg" % (3 + i))
        x = mix((bang, 0, 0), (thump(50, 25, 1.4, 0.45, 0.6), 0, -1), (fire_roar(2.4, 1100) * env_exp(secs(2.4), 0.7), 0.02, -2),
                (src("flame.ogg"), 0.0, -4), (deb, 0.25, -10))
        put("cult_leader.first_flame_impact", "pillar_%d" % (i + 1), reverb(x, 2.2, 0.3))

    # ash: dissolve (hiss + falling ash grains + reverse whoosh) and reform (reversed)
    rng(60)
    grains = hp(crackle(1.6, 90, 0.002, 4000), 2500) * np.linspace(1, 0.1, secs(1.6))
    x = mix((rev(whoosh(1.0, 400, 2500)), 0, -2), (hiss(1.6, 3500, 0.7), 0.2, -6), (grains, 0.3, -6),
            (fire_burst(1.0, 0), 0, -5), (lp(src("sfx_breaking_and_falling/bfh1_falling_02.ogg"), 3000), 0.4, -10))
    ash = reverb(x, 1.6, 0.3)
    put("cult_leader.ash", "ash", ash)
    rng(61)
    put("cult_leader.ash_reform", "ash_reform", mix((rev(ash[: secs(1.4)]), 0, 0), (thump(70, 40, 0.5, 0.12), 1.35, -3)))

    # ash slash: wide fire-whoosh + heavy blade + ring
    for i in range(2):
        rng(70 + i)
        x = mix((scythe_swish(i), 0, 0), (whoosh(0.8, 200, 3000, 2.2, 1.6, 0.4), 0.05, -2), (fire_burst(1.4, 2 + i), 0.2, -3),
                (src("sword_-_starninjas_1/sword - StarNinjas/sword.%d.ogg" % (3 + i)), 0.18, -6))
        put("cult_leader.ash_slash", "ash_slash_%d" % (i + 1), reverb(x, 1.8, 0.3))

    # replica break: glass + flare
    rng(80)
    x = mix((src("sfx_breaking_and_falling/bfh1_glass_breaking_03.ogg"), 0, 0), (fire_burst(1.0, 6), 0.0, -3), (thump(80, 40, 0.4, 0.1), 0, -6))
    put("cult_leader.replica_break", "replica_break", reverb(x, 1.6, 0.3))

    # finisher: hook pull (start), impale, burst of flame
    rng(90)
    x = mix((scythe_swish(1), 0, 0), (semis(src("80-CC0-RPG-SFX_0/blade_02.ogg"), -3), 0.35, -2), (src("80-CC0-RPG-SFX_0/chain_01.ogg"), 0.4, -10))
    put("cult_leader.finisher", "finisher", reverb(x, 1.2, 0.2))
    for i in range(2):
        rng(95 + i)
        x = mix((semis(src("80-CC0-RPG-SFX_0/blade_0%d.ogg" % (1 + 2 * i)), -4), 0, 0), (thump(65, 35, 0.6, 0.12), 0, -2),
                (lp(src("water-splash-slime-sfx/slime_0%d.ogg" % (4 + i)), 2500), 0.02, -12))
        put("cult_leader.impale", "impale_%d" % (i + 1), reverb(x, 1.0, 0.2))
    rng(98)
    put("cult_leader.flame", "flame", reverb(mix((fire_burst(1.6, 4), 0, 0), (src("flame.ogg"), 0, -2), (whoosh(0.7, 200, 2000), 0, -6)), 1.6, 0.3))

    # death: the flame dies out — roar sweeping down, embers, long gong tail
    rng(100)
    d = 3.5
    roar = sweep_filter(noise(d, "pink"), 1800, 120, 2.0) * np.exp(-np.arange(secs(d)) / (1.1 * SR))
    x = mix((roar, 0, 0), (rev(whoosh(0.8, 200, 1500)), 0, -6), (crackle(3.0, 12) * np.linspace(1, 0, secs(3.0)), 0.3, -14),
            (semis(src("100-CC0-SFX_0/gong_01.ogg"), -12), 0.1, -4), (hiss(2.5, 3000, 1.0), 0.4, -14), (thump(45, 25, 1.5, 0.5), 0, -4))
    put("cult_leader.death_final", "death_final", reverb(x, 3.0, 0.4))

    # scythe swings (4 variants)
    for i in range(4):
        rng(110 + i)
        put("cult_leader.scythe", "scythe_%d" % (i + 1), scythe_swish(i))

    # inhale (warning before dash / guard break): reversed flame
    for i in range(2):
        rng(120 + i)
        x = mix((rev(fire_burst(0.9, 1 + i)), 0, 0), (rev(whoosh(0.7, 300, 1800)), 0.1, -4))
        put("cult_leader.inhale", "inhale_%d" % (i + 1), x)

    # sickle: whirring spin (14 Hz flutter) + metal ring; catch: clank into the hand
    rng(130)
    d = 1.0
    t = t_axis(d)
    whirr = whoosh(d, 400, 900, 1.4, 1.0, 0.3) * (0.55 + 0.45 * np.sin(2 * np.pi * 14 * t))
    x = mix((whirr, 0, 0), (fire_roar(d, 900) * adsr(secs(d), 0.05, 0.1, 0.8, 0.3), 0, -6), (metal_ring(1300, 1.0, 0.2), 0, -14),
            (src("swishes/swishes/swish-9.wav"), 0, -3))
    put("cult_leader.sickle_throw", "sickle_throw", reverb(x, 1.0, 0.2))
    for i in range(2):
        rng(135 + i)
        x = mix((src("100-CC0-wood-metal-SFX/metal_hit_0%d.ogg" % (2 + i)), 0, 0), (metal_ring(700 + 90 * i, 1.0, 0.3), 0, -10),
                (src("RPGsounds_Kenney/OGG/handleSmallLeather.ogg"), 0.02, -8))
        put("cult_leader.sickle_catch", "sickle_catch_%d" % (i + 1), reverb(x, 0.9, 0.15))

    # ash trail dash: long fire whoosh + crackle trail
    for i in range(2):
        rng(140 + i)
        x = mix((whoosh(0.7, 160, 2400, 2.2, 1.4, 0.35), 0, 0), (fire_roar(1.2, 900) * env_exp(secs(1.2), 0.4), 0.05, -3),
                (crackle(1.2, 40) * env_exp(secs(1.2), 0.5), 0.1, -12), (src("swishes/swishes/swish-%d.wav" % (7 + i)), 0, -2))
        put("cult_leader.dash", "dash_%d" % (i + 1), reverb(x, 1.2, 0.2))

    # brand: sizzle; brand explode
    for i in range(2):
        rng(150 + i)
        sizz = hp(noise(1.2), 2500) * (0.6 + 0.4 * lp(np.abs(noise(1.2)), 30)) * adsr(secs(1.2), 0.02, 0.2, 0.6, 0.5)
        x = mix((sizz, 0, -3), (crackle(1.2, 50), 0, -8), (thump(90, 50, 0.3, 0.06), 0, -4), (src("80-CC0-RPG-SFX_0/spell_fire_03.ogg"), 0, -6))
        put("cult_leader.brand", "brand_%d" % (i + 1), reverb(x, 1.0, 0.2))
    for i in range(2):
        rng(155 + i)
        x = mix((semis(src("25-CC0-bang-sfx/bang_0%d.ogg" % (3 + 2 * i)), -3), 0, 0), (fire_burst(1.2, 5 + i), 0, -3),
                (thump(60, 30, 0.8, 0.2), 0, -3))
        put("cult_leader.brand_explode", "brand_explode_%d" % (i + 1), reverb(x, 1.6, 0.3))

    # pillars mark: ground cracks + hiss
    rng(160)
    x = mix((src("sfx_breaking_and_falling/bfh1_rock_breaking_02.ogg"), 0, 0), (rumble(1.6, 80, 0.6), 0, -4), (hiss(1.5, 3000, 0.6), 0.2, -10),
            (crackle(1.5, 25), 0.2, -14))
    put("cult_leader.pillars_mark", "pillars_mark", reverb(x, 1.6, 0.3))

    # plant (scythe into the ground) and sigil (ring of fire ignites)
    rng(170)
    x = mix((thump(70, 35, 0.8, 0.18, 0.5), 0, 0), (src("sfx_breaking_and_falling/bfh1_rock_hit_01.ogg"), 0, -4),
            (metal_ring(450, 1.6, 0.6), 0, -9), (src("100-CC0-wood-metal-SFX/metal_hit_01.ogg"), 0, -6))
    put("cult_leader.plant", "plant", reverb(x, 1.8, 0.3))
    rng(171)
    d = 1.6
    ring = sweep_filter(noise(d, "pink"), 300, 1600, 1.8) * adsr(secs(d), 0.1, 0.2, 0.7, 0.6)
    x = mix((ring, 0, 0), (src("flame.ogg"), 0, -2), (semis(src("100-CC0-SFX_0/bell_02.ogg"), -8), 0.05, -8))
    put("cult_leader.sigil", "sigil", reverb(x, 2.0, 0.35))
    return F


# ------------------------------------------------------------------ keyframes

def _iron_scythe_plan():
    import json, os, anim_sfx
    d = json.load(open(os.path.join(ROOT, "src/main/resources/assets/pohsmp_core/animations/entity/cult_leader.animation.json"),
                       encoding="utf-8"))["animations"]
    plan = {}
    for n in ("scythe_backpedal", "scythe_jump_combo", "scythe_sideslash_downslash", "scythe_downslash_pull", "scythe_downslash_sideslash",
              "scythe_low_rightward_sweep", "scythe_full_spin_clockwise", "scythe_horizontal_slash_spin", "scythe_dagger_double_horizontal",
              "scythe_sideslash_downslash_sideslash", "scythe_sideslash_downslash_spinslash", "scythe_dagger_combo_1"):
        pk = anim_sfx.swing_peaks(d[n], k=3, min_gap=0.4, rel=0.5)
        plan[n] = [(max(0, p - 0.12), "cult_leader.scythe|0.8") for _, p, _ in pk]
    return plan


ANIMS = {"cult_leader.animation.json": dict(_iron_scythe_plan(), **{
    "cult_leader_first_flame": [(0.9, "cult_leader.plant|2"), (1.6, "cult_leader.sigil|2.5")],
    "cult_leader_ash_reform": [(0.0, "cult_leader.ash_reform|2")],
    "cult_leader_ash_slash": [(0.3, "cult_leader.scythe|1.5|0.9")],
    "cult_leader_replica_break": [(0.9, "cult_leader.brand|1.5"), (0.55, "cult_leader.scythe")],
    "cult_leader_finisher": [(0.8, "cult_leader.scythe|1|0.9"), (1.0, "cult_leader.impale|2"), (1.7, "cult_leader.flame|2")],
    "cult_leader_sickle_throw": [(0.0, "cult_leader.inhale|1.5"), (0.85, "cult_leader.scythe|1.2"), (1.0, "cult_leader.sickle_throw|2"),
                                 (1.8, "cult_leader.sickle_catch|1.5")],
    "cult_leader_ash_trail_dash": [(0.0, "cult_leader.inhale|1.5"), (0.5, "cult_leader.dash|2")],
    "cult_leader_brand": [(0.35, "cult_leader.scythe")],
    "cult_leader_pillars": [(0.3, "cult_leader.pillars_mark|2")],
    "cult_leader_guard_break": [(0.1, "cult_leader.inhale|1.5"), (0.55, "cult_leader.scythe|1.3|0.9")],
})}

# Demo (code-timed sounds relative to the animation start, as in CultFight / CultLeaderEntity)
VIDEOS = {
    "cult_leader_sound_1": ("t26_finale", {
        "fire_boss_spawn": [(0, "cult_leader.spawn"), (1.1, "cult_leader.firewall"), (6.0, "cult_leader.phase")],
        "fire_boss_half_health_attack": [(10.6, "cult_leader.phase"), (11.0, "cult_leader.firewall"), (11.3, "cult_leader.summon")],
        "fire_boss_death": [(2.6, "cult_leader.death_final")],
        "cult_leader_finisher": [(0, "cult_leader.finisher")],
    }, []),
    "cult_leader_sound_2": ("t26_combat", {
        "fire_boss_break_stance": [(0.2, "boss.guard_break"), (0.1, "cult_leader.phase")],
    }, []),
    "cult_leader_sound_3": ("t26_special", {
        "charge_raised_hand": [(0, "cult_leader.verdict"), (2.0, "cult_leader.verdict_lock")],
        "cult_leader_first_flame": [(0, "cult_leader.first_flame"), (4.0, "cult_leader.first_flame_impact")],
        "cult_leader_ash_dissolve": [(0, "cult_leader.ash")],
        "cult_leader_ash_slash": [(0.5, "cult_leader.ash_slash")],
        "cult_leader_replica_break": [(1.5, "cult_leader.replica_break")],
        "cult_leader_brand": [(0.55, "cult_leader.brand"), (2.6, "cult_leader.brand_explode")],
        "cult_leader_pillars": [(1.8, "cult_leader.first_flame_impact|0.6")],
    }, []),
}
