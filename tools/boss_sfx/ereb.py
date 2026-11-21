"""Эреб (T30): стекло, звон, бабочки, рапира, шёпот иллюзий."""
from sfx import *  # noqa: F401,F403

B = "ereb"

EVENTS = {
    "ereb.aura": ("Эреб: звон стекла и шёпот", "Ereb: glass chimes, whispers", 16, 0.35),
    "ereb.spawn": ("Эреб складывается из осколков", "Ereb forms from shards", 64, 1.0),
    "ereb.appear": ("Эреб появляется", "Ereb appears", 32, 1.0),
    "ereb.vanish": ("Эреб исчезает", "Ereb vanishes", 32, 1.0),
    "ereb.blink": ("Мерцание иллюзии", "Illusion flickers", 20, 1.0),
    "ereb.glint": ("Блеск клинка", "Blade glints", 24, 1.0),
    "ereb.thrust": ("Укол рапиры", "Rapier thrusts", 24, 1.0),
    "ereb.swish": ("Свист рапиры", "Rapier swishes", 16, 1.0),
    "ereb.parry": ("Рапира парирует", "Rapier parries", 24, 1.0),
    "ereb.cast": ("Эреб плетёт иллюзию", "Ereb weaves an illusion", 32, 1.0),
    "ereb.shards": ("Осколки летят", "Shards fly", 32, 1.0),
    "ereb.shard_break": ("Осколок бьётся", "Shard shatters", 16, 1.0),
    "ereb.disguise": ("Чужое лицо", "A borrowed face", 32, 1.0),
    "ereb.phase": ("Зеркало трескается", "The mirror cracks", 64, 1.0),
    "ereb.butterfly": ("Стеклянные бабочки", "Glass butterflies", 32, 1.0),
    "ereb.dissolve": ("Иллюзия рассыпается", "Illusion dissolves", 40, 1.0),
    "ereb.rain": ("Стеклянный дождь", "Glass rain", 32, 1.0),
    "ereb.reflection_break": ("Отражение разбито", "Reflection shattered", 24, 1.0),
    "ereb.replica_break": ("Реплика разбита, как зеркало", "Replica shattered like a mirror", 32, 1.0),
    "ereb.step": ("Лёгкие шаги Эреба", "Ereb's light steps", 10, 0.6),
    "ereb.cloth": ("Шорох плаща", "Coat rustles", 10, 0.6),
    "ereb.whisper": ("Шёпот иллюзий", "Illusions whisper", 20, 0.9),
    "ereb.hurt": ("Эреб ранен: стекло трескается", "Ereb hurts: glass cracks", 16, 1.0),
}


# ---------------------------------------------------------------- shared glass kit (Ereb, Hand of Lies)

def chime(f=1800, d=1.6, n=3):
    """A few struck glass partials, slightly detuned (a wind chime)."""
    return norm(mix(*[(glass_ping(f * 2 ** (uni(-0.3, 0.6)), d, uni(0.3, 0.6)), uni(0, 0.12), -2 * k) for k in range(n)]))


def glass_break(i=0, size=1.0):
    g = src("sfx_breaking_and_falling/bfh1_glass_breaking_0%d.ogg" % (1 + i % 6))
    return mix((g, 0, 0), (shimmer(0.9, 2600, 10, 1.2, 0.12), 0.02, -10), (thump(150 / size, 80 / size, 0.2, 0.04), 0, -10 + 4 * (size - 1)))


def glass_tinkle(d=0.8, n=6, base=3000):
    return shimmer(d, base, n, 1.0, 0.08)


def rapier_swish(i=0):
    s = src("swishes/swishes/swish-%d.wav" % (1 + (i * 4) % 13))
    w = whoosh(0.25, 900, 3800, 1.0, 2.6, 0.7)
    return mix((s, 0, 0), (w, 0, -5), (glass_ping(3200 + 300 * i, 0.4, 0.08), 0.12, -20))


def rapier_hit(i=0):
    b = src("80-CC0-RPG-SFX_0/blade_0%d.ogg" % (1 + i % 3))
    return mix((b, 0, 0), (metal_ring(2100 + 150 * i, 0.7, 0.18), 0, -12), (glass_ping(2800, 0.6, 0.12), 0.01, -14))


def illusion_swell(d=1.2, up=True):
    """Airy reversed glass + whisper: the sound of something becoming (or stopping being) real."""
    s = shimmer(d, 2200, 12, 1.4, 0.4)
    w = whisper(d, 4, 1.0)
    x = mix((rev(s) if up else s, 0, 0), (lp(w, 4000), 0, -10), (sweep_filter(noise(d, "pink"), 400 if up else 2600, 2600 if up else 400, 1.0) * adsr(secs(d), 0.3, 0.1, 0.7, 0.3), 0, -10))
    return x


def build():
    F = {}

    def put(ev, name, x, **kw):
        F.setdefault(ev, []).append(write("%s/%s" % (B, name), x, **kw).split("sounds/boss/")[1][:-4])

    rng(501)
    d = 8.0
    ch = np.zeros(secs(d))
    for at in (0.4, 2.1, 3.3, 5.0, 6.6):
        c = chime(uni(1600, 2600), 1.6, 2) * uni(0.4, 0.9)
        ch[secs(at):secs(at) + len(c)] += c[: len(ch) - secs(at)]
    air = bp(noise(d, "pink"), 300, 3000) * (0.6 + 0.4 * np.sin(2 * np.pi * t_axis(d) / 4))
    F["ereb.aura"] = [write_loop("%s/aura" % B, mix((reverb(ch, 2.4, 0.5)[: secs(d)], 0, 0), (air, 0, -14),
                                                   (lp(whisper(d, 7, 0.9), 3000), 0, -20)), 1.0, 0.5).split("sounds/boss/")[1][:-4]]

    # spawn: shards gather (reversed shatter) into a body, a low bell, a salute glint
    rng(502)
    x = mix((illusion_swell(2.2, True), 0, 0), (rev(glass_break(2, 1.3)), 0.8, -2), (glass_tinkle(1.6, 14, 2400), 0.4, -8),
            (bell(196, 3.0, tau=1.2), 2.2, -6), (chime(2400, 2.0, 3), 2.25, -4), (whisper(1.5, 5, 0.9), 2.4, -12))
    put("ereb.spawn", "spawn", reverb(x, 2.6, 0.4))
    for i in range(2):
        rng(505 + i)
        put("ereb.appear", "appear_%d" % (i + 1), reverb(mix((illusion_swell(0.6, True), 0, 0), (chime(2600 + 300 * i, 1.0, 2), 0.5, -4)), 1.6, 0.35))
    for i in range(2):
        rng(507 + i)
        put("ereb.vanish", "vanish_%d" % (i + 1), reverb(mix((illusion_swell(0.7, False), 0, 0), (glass_tinkle(0.6, 6, 3200), 0, -6),
                                                           (whoosh(0.4, 3000, 600, 1.2, 1.0, 0.2), 0, -8)), 1.6, 0.35))
    for i in range(3):
        rng(509 + i)
        put("ereb.blink", "blink_%d" % (i + 1), reverb(mix((glass_ping(3600 + 400 * i, 0.5, 0.1), 0, 0), (whoosh(0.2, 2500, 800, 1.0, 1.0, 0.2), 0, -6)), 1.0, 0.3))
    for i in range(3):
        rng(512 + i)
        put("ereb.glint", "glint_%d" % (i + 1), reverb(mix((glass_ping(4200 + 500 * i, 1.0, 0.25), 0, 0), (chime(5200, 0.8, 2), 0.04, -8)), 1.6, 0.35))

    # rapier
    for i in range(4):
        rng(515 + i)
        put("ereb.swish", "swish_%d" % (i + 1), rapier_swish(i))
    for i in range(4):
        rng(519 + i)
        put("ereb.thrust", "thrust_%d" % (i + 1), reverb(mix((rapier_swish(i + 1), 0, -2), (rapier_hit(i), 0.1, 0)), 1.0, 0.2))
    for i in range(2):
        rng(523 + i)
        x = mix((src("sword_clash_-_starninjas_0/sword_clash.%d.ogg" % (1 + 4 * i)), 0, 0), (glass_ping(3000, 0.8, 0.2), 0, -8), (metal_ring(2600, 1.0, 0.3), 0, -10))
        put("ereb.parry", "parry_%d" % (i + 1), reverb(x, 1.2, 0.25))

    # illusions
    for i in range(2):
        rng(525 + i)
        x = mix((illusion_swell(1.0, True), 0, 0), (chime(2000 + 400 * i, 1.6, 4), 0.7, -2), (whisper(1.2, 4, 1.1), 0.1, -8))
        put("ereb.cast", "cast_%d" % (i + 1), reverb(x, 2.0, 0.4))
    for i in range(2):
        rng(528 + i)
        x = mix((glass_tinkle(0.6, 10, 3000), 0, 0), *[(whoosh(0.3, 1500, 4500, 0.9, 2.0, 0.6), 0.05 * k, -4 - 2 * k) for k in range(4)])
        put("ereb.shards", "shards_%d" % (i + 1), reverb(x, 1.2, 0.25))
    for i in range(3):
        rng(531 + i)
        put("ereb.shard_break", "shard_break_%d" % (i + 1), reverb(mix((src("sfx100v2_glass_0%d.ogg" % (1 + i)) if False else src("sfx_100_v2/sfx100v2_glass_0%d.ogg" % (1 + i)), 0, 0),
                                                                     (glass_tinkle(0.4, 4, 3800), 0, -8)), 0.9, 0.2))
    for i in range(2):
        rng(534 + i)
        x = mix((whisper(0.9, 3, 0.8 + 0.3 * i), 0, -2), (src("RPGsounds_Kenney/OGG/cloth%d.ogg" % (2 + i)), 0.2, -4), (rev(shimmer(0.6, 1800, 8, 1.0, 0.2)), 0.1, -6))
        put("ereb.disguise", "disguise_%d" % (i + 1), reverb(x, 1.8, 0.35))
    rng(537)
    x = mix((src("sfx_breaking_and_falling/bfh1_glass_breaking_05.ogg"), 0, 0), (semis(src("sfx_breaking_and_falling/bfh1_glass_breaking_02.ogg"), -7), 0.02, -2),
            (bell(110, 3.0, tau=1.2), 0, -6), (thump(60, 30, 1.0, 0.3), 0, -4), (glass_tinkle(1.6, 16, 2500), 0.1, -8), (whisper(1.5, 5, 0.7), 0.3, -12))
    put("ereb.phase", "phase", reverb(x, 2.6, 0.4))
    rng(538)
    d = 2.6
    flutter = np.zeros(secs(d))
    for k in range(14):
        a = secs(uni(0, d - 0.5))
        w = bp(noise(0.4), 1500, 5000) * (0.5 + 0.5 * np.sin(2 * np.pi * uni(18, 26) * t_axis(0.4))) * np.hanning(secs(0.4))
        flutter[a:a + len(w)] += w * uni(0.3, 1)
    x = mix((flutter, 0, -4), (glass_tinkle(d, 24, 3200), 0, 0), (chime(2400, 2.0, 3), 0.2, -8))
    put("ereb.butterfly", "butterfly", reverb(x, 2.2, 0.45))
    for i in range(2):
        rng(540 + i)
        x = mix((illusion_swell(1.6, False), 0, 0), (glass_tinkle(1.8, 20, 2600), 0.1, -4), (rev(chime(1600, 1.2, 3)), 0, -10))
        put("ereb.dissolve", "dissolve_%d" % (i + 1), reverb(x, 2.4, 0.45))
    for i in range(2):
        rng(543 + i)
        x = mix(*[(glass_break(k + i, 0.8), uni(0, 0.8), -3 - 2 * k) for k in range(5)], (whoosh(0.6, 3500, 800, 1.2, 1.4, 0.2), 0, -6))
        put("ereb.rain", "rain_%d" % (i + 1), reverb(x, 1.6, 0.3))
    for i in range(2):
        rng(546 + i)
        put("ereb.reflection_break", "reflection_break_%d" % (i + 1), reverb(mix((glass_break(3 + i), 0, 0), (illusion_swell(0.5, False), 0.05, -8)), 1.6, 0.3))
    rng(548)
    put("ereb.replica_break", "replica_break", reverb(mix((glass_break(4, 1.2), 0, 0), (chime(2200, 1.4, 3), 0.05, -6), (whisper(0.8, 3, 1.0), 0.3, -12)), 1.8, 0.35))

    for i in range(4):
        rng(550 + i)
        st = src("RPGsounds_Kenney/OGG/footstep0%d.ogg" % (i * 2 + 1))
        put("ereb.step", "step_%d" % (i + 1), mix((hp(st, 200), 0, 0), (glass_ping(4000 + 300 * i, 0.3, 0.04), 0.01, -22)))
    for i in range(3):
        rng(555 + i)
        put("ereb.cloth", "cloth_%d" % (i + 1), mix((src("RPGsounds_Kenney/OGG/cloth%d.ogg" % (1 + i)), 0, 0), (whoosh(0.25, 800, 2000), 0, -12)))
    for i in range(3):
        rng(558 + i)
        put("ereb.whisper", "whisper_%d" % (i + 1), reverb(mix((whisper(1.2 + 0.2 * i, 4 + i, 1.0 + 0.1 * i), 0, 0), (glass_ping(2400, 1.0, 0.3), 0.3, -16)), 2.0, 0.45))
    for i in range(3):
        rng(562 + i)
        crack = src("sfx_100_v2/sfx100v2_glass_0%d.ogg" % (4 + i))
        put("ereb.hurt", "hurt_%d" % (i + 1), reverb(mix((crack, 0, 0), (src("RPGsounds_Kenney/OGG/cloth%d.ogg" % (1 + i)), 0, -8)), 0.8, 0.15))
    return F


ANIMS = {"ereb.animation.json": {
    "ereb_walk": [(0.3, "ereb.step"), (0.9, "ereb.step")],
    "ereb_lunge": [(0.25, "ereb.cloth"), (0.32, "ereb.swish")],
    "ereb_flurry": [(0.3, "ereb.swish"), (0.65, "ereb.swish"), (1.0, "ereb.swish")],
    "ereb_parry": [(0.15, "ereb.parry"), (0.45, "ereb.swish")],
    "ereb_cast_illusion": [(0.3, "ereb.cloth")],
    "ereb_shard_cast": [(0.2, "ereb.cloth")],
    "ereb_disguise": [(0.1, "ereb.whisper")],
    "ereb_vanish": [(0.0, "ereb.cloth")],
    "ereb_backstab": [(0.3, "ereb.swish")],
    "ereb_phase": [(0.2, "ereb.whisper|1.5")],
    "ereb_spawn": [(0.5, "ereb.whisper|2"), (2.6, "ereb.cloth"), (3.9, "ereb.glint|1.5")],
    "ereb_blade_dance": [(0.05, "ereb.blink"), (0.4, "ereb.swish"), (1.15, "ereb.blink"), (1.5, "ereb.swish"), (2.25, "ereb.blink"), (2.6, "ereb.swish"),
                         (3.35, "ereb.blink"), (3.7, "ereb.swish")],
    "ereb_feint": [(0.3, "ereb.cloth"), (1.8, "ereb.cloth")],
    "ereb_glass_rain": [(0.1, "ereb.cloth")],
    "ereb_mirror_step_out": [(0.0, "ereb.blink")],
    "ereb_mirror_step_in": [(0.25, "ereb.swish")],
    "ereb_finale": [(0.3, "ereb.whisper|1.5"), (2.4, "ereb.cloth")],
    "ereb_finisher": [(0.95, "ereb.swish")],
    "ereb_guard_break": [(0.1, "ereb.glint|1.3"), (0.55, "ereb.swish|1.3")],
    "ereb_replica_break": [(0.55, "ereb.glint|1.3")],
}}

VIDEOS = {
    "ereb_sound_1": ("t30_finale", {
        "ereb_spawn": [(0, "ereb.spawn"), (2.2, "ereb.appear")],
        "ereb_finale": [(1.4, "ereb.butterfly"), (3.2, "ereb.cast"), (5.0, "ereb.dissolve")],
        "ereb_finisher": [(0.3, "ereb.vanish"), (0.7, "ereb.appear"), (1.1, "ereb.thrust"), (1.9, "ereb.dissolve")],
    }, []),
    "ereb_sound_2": ("t30_combat", {
        "ereb_lunge": [(0.5, "ereb.thrust")],
        "ereb_flurry": [(0.45, "ereb.thrust"), (0.8, "ereb.thrust"), (1.15, "ereb.thrust")],
        "ereb_parry": [(0.6, "ereb.thrust")],
        "ereb_shard_cast": [(0.55, "ereb.shards"), (1.0, "ereb.shard_break")],
        "ereb_cast_illusion": [(0.75, "ereb.cast")],
        "ereb_disguise": [(0.5, "ereb.disguise")],
        "ereb_vanish": [(0.0, "ereb.vanish")],
        "ereb_backstab": [(0.0, "ereb.appear"), (0.45, "ereb.thrust")],
        "ereb_phase": [(0.8, "ereb.phase")],
    }, []),
    "ereb_sound_3": ("t30_spells", {
        "ereb_vanish": [(0.0, "ereb.vanish")],
        "ereb_backstab": [(0.0, "ereb.appear"), (0.45, "ereb.thrust")],
        "ereb_blade_dance": [(0.55, "ereb.thrust"), (1.65, "ereb.thrust"), (2.75, "ereb.thrust"), (3.85, "ereb.thrust")],
        "ereb_feint_counter": [(0.1, "ereb.parry"), (0.45, "ereb.thrust")],
        "ereb_glass_rain": [(0.4, "ereb.glint"), (1.6, "ereb.rain")],
        "ereb_mirror_step_out": [(0.0, "ereb.vanish")],
        "ereb_mirror_step_in": [(0.0, "ereb.appear"), (0.4, "ereb.thrust")],
    }, []),
}
