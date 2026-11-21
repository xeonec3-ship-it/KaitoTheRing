"""Ирина (T27): натяжение и треск нитей, шорох ткани, ведьмин шёпот, кровь."""
from sfx import *  # noqa: F401,F403

B = "irina"

EVENTS = {
    "irina.aura": ("Ирина: шорох нитей и шёпот", "Irina: threads rustle, whispers", 16, 0.35),
    "irina.spawn": ("Кокон Ирины натягивается", "Irina's cocoon tightens", 64, 1.0),
    "irina.death": ("Нити Ирины рвутся", "Irina's threads tear", 48, 1.0),
    "irina.death_final": ("Ирина распускается нитями", "Irina unravels", 48, 1.0),
    "irina.mark": ("Метка ревности", "Mark of jealousy", 32, 1.0),
    "irina.bind": ("Нити связывают пары", "Threads bind pairs", 40, 1.0),
    "irina.snap": ("Нить лопается", "Thread snaps", 32, 1.0),
    "irina.steal": ("Ирина впитывает чужое", "Irina absorbs", 32, 1.0),
    "irina.whip": ("Хлёст нитей", "Thread whip lashes", 40, 1.0),
    "irina.cocoon": ("Нити оплетают кокон", "Threads weave a cocoon", 40, 1.0),
    "irina.cocoon_break": ("Кокон разорван", "Cocoon torn open", 40, 1.0),
    "irina.cocoon_crush": ("Кокон сжимается", "Cocoon crushes", 40, 1.0),
    "irina.happiness": ("Чужое счастье: шёпот", "Others' happiness: whispers", 56, 1.0),
    "irina.phase": ("Ирина впадает в ревность", "Irina grows jealous", 56, 1.0),
    "irina.finisher": ("Нити опутывают жертву", "Threads wrap the victim", 32, 1.0),
    "irina.staff": ("Удар посоха", "Staff strikes", 24, 1.0),
    "irina.gaze": ("Ревнивый взгляд", "Jealous gaze", 32, 1.0),
    "irina.knots": ("Нити завязываются узлами", "Threads knot", 32, 1.0),
    "irina.snare": ("Нити бьют из узла", "Threads stab from a knot", 24, 1.0),
    "irina.swap": ("Подмена", "Swap", 32, 1.0),
    "irina.puppet": ("Нити марионетки", "Puppet strings", 32, 1.0),
    "irina.replica_break": ("Реплика распорота", "Replica ripped apart", 32, 1.0),
    "irina.step": ("Шаги Ирины", "Irina steps", 12, 0.7),
    "irina.cloth": ("Шорох платья", "Dress rustles", 12, 0.6),
    "irina.swish": ("Свист посоха", "Staff swishes", 16, 1.0),
    "irina.thread": ("Нить натягивается", "Thread pulls taut", 20, 1.0),
    "irina.whisper": ("Ведьмин шёпот", "Witch whispers", 20, 0.9),
    "irina.burst": ("Нити разлетаются", "Threads burst out", 48, 1.0),
    "irina.rage": ("Ярость Ирины: сердце бьётся", "Irina's fury: heartbeat", 48, 1.0),
    "irina.thud": ("Ирина падает", "Irina falls", 20, 1.0),
    "irina.hurt": ("Ирина ранена", "Irina hurts", 16, 1.0),
}


def thread_pull(i=0, d=0.6):
    """Taut thread: rising buzz + stick-slip creak + a rope creak layer."""
    s = string_creak(d, 170 + 40 * i, 320 + 60 * i, 30 + 10 * i)
    cr = src("RPGsounds_Kenney/OGG/creak%d.ogg" % (1 + i % 3))
    return mix((s, 0, 0), (semis(cr, 3 + 2 * i), 0.02, -6), (hp(whoosh(d, 900, 2500, 1.2, 1.5, 0.8), 600), 0, -12))


def snap_hit(i=0):
    return mix((snap(2600 + 400 * i), 0, 0), (src("RPGsounds_Kenney/OGG/knifeSlice%s.ogg" % ("" if i % 2 == 0 else "2")), 0, -4),
               (thump(110, 60, 0.25, 0.05, 0.2), 0, -10))


def cloth(i):
    return src("RPGsounds_Kenney/OGG/cloth%d.ogg" % (1 + i % 4))


def blood(i=0):
    return lp(src("water-splash-slime-sfx/slime_%02d.ogg" % (3 + i)), 3000)


def build():
    F = {}

    def put(ev, name, x, **kw):
        F.setdefault(ev, []).append(write("%s/%s" % (B, name), x, **kw).split("sounds/boss/")[1][:-4])

    # aura: soft thread creaks, a breathy whisper bed, slow heartbeat far away
    rng(201)
    d = 9.0
    bed = lp(noise(d, "pink"), 900) * 0.25
    w = mix((whisper(4.0, 6, 1.1), 1.0, 0), (whisper(3.0, 5, 0.9), 5.5, -2), length=d)
    creaks = np.zeros(secs(d))
    for k, at in enumerate((0.7, 3.1, 6.4, 7.9)):
        c = string_creak(0.5, 200 + 50 * k, 260 + 40 * k, 25) * 0.6
        creaks[secs(at):secs(at) + len(c)] += c[: len(creaks) - secs(at)]
    hb = np.zeros(secs(d))
    for at in np.arange(0.2, d - 1, 1.5):
        h = heartbeat(1.0)
        hb[secs(at):secs(at) + len(h)] += h[: len(hb) - secs(at)]
    F["irina.aura"] = [write_loop("%s/aura" % B, mix((bed, 0, 0), (lp(w, 3000), 0, -17), (creaks, 0, -12), (lp(hb, 200), 0, -10)), 1.0, 0.5)
                       .split("sounds/boss/")[1][:-4]]

    # spawn: cocoon creaks tighter and tighter, whispers rise, then threads burst into a flourish
    rng(202)
    x = mix((thread_pull(0, 2.4) * np.linspace(0.3, 1, secs(2.4)), 0, 0), (thread_pull(1, 1.6), 1.0, -3), (whisper(3.0, 9, 1.0), 0.3, -6),
            (mix(*[(snap_hit(k), 2.5 + 0.09 * k, -3 - k) for k in range(4)]), 0, 0), (cloth(0), 2.6, -2), (cloth(2), 2.9, -4),
            (whoosh(0.8, 300, 2400), 2.55, -6), (heartbeat(1.0), 0.0, -8), (heartbeat(1.0), 1.2, -6))
    put("irina.spawn", "spawn", reverb(x, 2.0, 0.3))

    # death: threads tear (several snaps + cloth rip) / death_final: unravelling whisper and soft rustle fading
    rng(203)
    rip = semis(src("RPGsounds_Kenney/OGG/cloth4.ogg"), -2)
    x = mix((rip, 0, 0), (snap_hit(0), 0.05, -2), (snap_hit(1), 0.25, -5), (blood(0), 0.1, -8), (thump(80, 45, 0.5, 0.1), 0, -6),
            (whisper(1.2, 3, 0.9), 0.4, -10))
    put("irina.death", "death", reverb(x, 1.8, 0.3))
    rng(204)
    d = 2.8
    un = hp(crackle(d, 60, 0.002, 3000), 1500) * np.linspace(1, 0, secs(d)) ** 1.5
    x = mix((un, 0, 0), (whisper(2.0, 6, 0.8) * np.linspace(1, 0, secs(2.0)), 0.1, -4), (cloth(1), 0, -6), (cloth(3), 0.6, -8),
            (string_creak(1.2, 300, 150, 20), 0.2, -8))
    put("irina.death_final", "death_final", reverb(x, 2.4, 0.4))

    # mark: whisper + a thin high thread tone
    for i in range(2):
        rng(210 + i)
        x = mix((whisper(1.0, 4, 1.1 + 0.1 * i), 0, 0), (sine(1800 + 200 * i, 1.0, 1400) * env_exp(secs(1.0), 0.3), 0.05, -14),
                (snap(3400), 0.0, -8))
        put("irina.mark", "mark_%d" % (i + 1), reverb(x, 1.6, 0.35))

    # bind: two threads pulled taut and tied
    rng(212)
    x = mix((thread_pull(0, 0.8), 0, 0), (thread_pull(2, 0.8), 0.15, -2), (src("RPGsounds_Kenney/OGG/clothBelt.ogg"), 0.75, -2), (snap(2200), 0.8, -8))
    put("irina.bind", "bind", reverb(x, 1.4, 0.25))

    # snap (3 variants)
    for i in range(3):
        rng(215 + i)
        put("irina.snap", "snap_%d" % (i + 1), reverb(mix((snap_hit(i), 0, 0), (snap_hit(i + 1), 0.04, -8)), 1.0, 0.2))

    # steal: threads drawn in + a gulp of breath (reversed whisper)
    rng(220)
    x = mix((rev(whisper(1.2, 4, 1.0)), 0, 0), (rev(whoosh(0.8, 500, 2500)), 0.3, -4), (thread_pull(1, 0.7), 0.2, -6), (heartbeat(1.0), 1.0, -6))
    put("irina.steal", "steal", reverb(x, 1.5, 0.3))

    # whip (3): a ring of threads cracking outward
    for i in range(3):
        rng(225 + i)
        cr = mix((snap(2000 + 300 * i), 0, 0), (whoosh(0.35, 800, 3500, 1.4, 2.5, 0.7), -0.0, -2))
        x = mix((whoosh(0.4, 400, 2800, 1.6, 2.2, 0.75), 0, -2), (cr, 0.3, 0), (src("swishes/swishes/swish-%d.wav" % (10 + i)), 0.22, -2),
                (snap_hit(i), 0.36, -4))
        put("irina.whip", "whip_%d" % (i + 1), reverb(x, 1.2, 0.2))

    # cocoon: many threads wrapping round (fast creaks, cloth), break: rip open, crush: tightening + squelch
    rng(230)
    d = 1.8
    t = t_axis(d)
    wrap = string_creak(d, 180, 420, 45) * (0.6 + 0.4 * np.sin(2 * np.pi * 6 * t))
    x = mix((wrap, 0, 0), (cloth(0), 0.1, -3), (cloth(1), 0.6, -4), (cloth(2), 1.1, -4), (whoosh(1.4, 300, 1200, 1.4, 1.2, 0.3) * 0.7, 0, -8))
    put("irina.cocoon", "cocoon", reverb(x, 1.4, 0.25))
    rng(231)
    x = mix((semis(src("RPGsounds_Kenney/OGG/cloth4.ogg"), -3), 0, 0), (mix(*[(snap_hit(k), 0.03 * k, -2 * k) for k in range(5)]), 0, -1),
            (whoosh(0.5, 500, 3000), 0, -6), (thump(90, 50, 0.4, 0.08), 0, -6))
    put("irina.cocoon_break", "cocoon_break", reverb(x, 1.4, 0.3))
    rng(232)
    x = mix((string_creak(1.2, 140, 380, 60), 0, 0), (blood(2), 0.8, -2), (thump(70, 40, 0.6, 0.15), 0.85, -2), (snap_hit(2), 0.9, -4),
            (semis(src("RPGsounds_Kenney/OGG/creak3.ogg"), -4), 0.1, -4))
    put("irina.cocoon_crush", "cocoon_crush", reverb(x, 1.6, 0.3))

    # others' happiness: a crowd of whispers spreading, then drawn in
    rng(240)
    d = 5.5
    crowd = mix(*[(whisper(2.0, 6, 0.8 + 0.1 * k), 0.3 * k, -2 * (k % 3)) for k in range(8)], length=d)
    crowd *= np.interp(t_axis(d), [0, 1.4, 3.6, 5.2, 5.5], [0.2, 1, 1, 0.2, 0])
    x = mix((crowd, 0, 0), (drone(110, d, 4, 0.01, 900) * 0.5 * adsr(secs(d), 1.0, 0.5, 0.7, 1.5), 0, -10),
            (rev(whoosh(1.5, 300, 2000)), 3.6, -6), (glass_ping(2200, 1.5, 0.5), 5.2, -14))
    put("irina.happiness", "happiness", reverb(x, 2.4, 0.35))

    # phase: snarl of threads tightening everywhere + heartbeat
    for i in range(2):
        rng(245 + i)
        x = mix((thread_pull(i, 1.2), 0, 0), (thread_pull(i + 1, 1.0), 0.2, -2), (heartbeat(1.0), 0, -2), (heartbeat(1.0), 0.75, 0),
                (whisper(1.5, 5, 0.75), 0.3, -6), (thump(55, 30, 1.2, 0.3), 0, -4))
        put("irina.phase", "phase_%d" % (i + 1), reverb(x, 2.0, 0.35))

    # finisher start: threads wrap the victim
    rng(250)
    x = mix((thread_pull(0, 0.9), 0, 0), (cloth(1), 0.2, -4), (string_creak(0.8, 250, 500, 50), 0.3, -4))
    put("irina.finisher", "finisher", reverb(x, 1.2, 0.2))

    # staff hit (3): wooden crook + thread twang
    for i in range(3):
        rng(255 + i)
        wood = src("100-CC0-wood-metal-SFX/wood_hit_0%d.ogg" % (2 + 2 * i))
        x = mix((wood, 0, 0), (thump(110, 60, 0.3, 0.06), 0, -4), (snap(1800 + 250 * i), 0.01, -9))
        put("irina.staff", "staff_%d" % (i + 1), reverb(x, 1.0, 0.2))

    # gaze: a long whispered hiss + low throb
    rng(260)
    x = mix((whisper(1.2, 3, 0.7), 0, 0), (sine(70, 1.2, 55) * adsr(secs(1.2), 0.1, 0.3, 0.6, 0.6), 0, -6),
            (sine(2400, 1.0, 2000) * adsr(secs(1.0), 0.3, 0.2, 0.5, 0.4), 0.1, -18))
    put("irina.gaze", "gaze", reverb(x, 2.0, 0.4))

    # knots: threads twisting into knots (creaks + cloth pulls)
    rng(262)
    x = mix((string_creak(0.7, 200, 260, 70), 0, 0), (string_creak(0.6, 260, 200, 60), 0.35, -2), (src("RPGsounds_Kenney/OGG/clothBelt2.ogg"), 0.7, -2))
    put("irina.knots", "knots", reverb(x, 1.2, 0.25))

    # snare (3): threads stab up out of the ground
    for i in range(3):
        rng(265 + i)
        x = mix((rev(whoosh(0.15, 800, 3000)), 0, -6), (snap_hit(i), 0.1, 0), (src("RPGsounds_Kenney/OGG/drawKnife%d.ogg" % (1 + i)), 0.08, -4),
                (thump(100, 50, 0.3, 0.05), 0.1, -8))
        put("irina.snare", "snare_%d" % (i + 1), reverb(x, 1.0, 0.2))

    # swap: two people yanked through each other — whoosh pair + snap
    rng(270)
    x = mix((whoosh(0.5, 300, 2400), 0, 0), (rev(whoosh(0.5, 300, 2400)), 0.35, -2), (snap_hit(0), 0.45, -2), (whisper(0.6, 2, 1.2), 0.1, -10))
    put("irina.swap", "swap", reverb(x, 1.4, 0.3))

    # puppet: strings hooked into limbs — several taut plucks
    rng(272)
    pl = [(string_creak(0.25, 300 + 70 * k, 330 + 70 * k, 80) * env_exp(secs(0.25), 0.08), 0.12 * k, -2 * k) for k in range(4)]
    x = mix(*pl, (whisper(0.8, 3, 1.0), 0.2, -10), (cloth(3), 0.05, -6))
    put("irina.puppet", "puppet", reverb(x, 1.2, 0.25))

    # replica ripped apart
    rng(274)
    x = mix((semis(src("RPGsounds_Kenney/OGG/cloth4.ogg"), 2), 0, 0), (snap_hit(1), 0.02, -2), (src("sfx_breaking_and_falling/bfh1_glass_breaking_02.ogg"), 0.05, -8))
    put("irina.replica_break", "replica_break", reverb(x, 1.2, 0.25))

    # small things: steps (4), cloth (3), staff swish (3), thread pull (3), whispers (3)
    for i in range(4):
        rng(280 + i)
        st = src("footsteps/footsteps/step_lth%s.ogg" % ["1", "2", "33", "4"][i])
        x = mix((hp(st, 150), 0, 0), (cloth(i), 0.0, -12), (hp(src("RPGsounds_Kenney/OGG/footstep0%d.ogg" % (i * 2)), 300), 0, -8))
        put("irina.step", "step_%d" % (i + 1), x)
    for i in range(3):
        rng(285 + i)
        put("irina.cloth", "cloth_%d" % (i + 1), mix((cloth(i), 0, 0), (whoosh(0.3, 600, 1500), 0, -14)))
    for i in range(3):
        rng(288 + i)
        x = mix((src("swishes/swishes/swish-%d.wav" % (2 + 3 * i)), 0, 0), (whoosh(0.3, 400, 2200, 1.4, 2.0, 0.6), 0, -4), (cloth(i), 0.03, -10))
        put("irina.swish", "swish_%d" % (i + 1), x)
    for i in range(3):
        rng(291 + i)
        put("irina.thread", "thread_%d" % (i + 1), reverb(thread_pull(i, 0.5 + 0.1 * i), 0.9, 0.18))
    for i in range(3):
        rng(294 + i)
        put("irina.whisper", "whisper_%d" % (i + 1), reverb(whisper(1.1 + 0.2 * i, 4 + i, 0.9 + 0.1 * i), 1.8, 0.4))

    # burst (phase 2): a hundred threads whip outward
    rng(297)
    x = mix(*[(snap_hit(k), 0.02 * k, -1.5 * k) for k in range(6)], (whoosh(0.6, 300, 3000), 0, -2), (thump(70, 35, 0.8, 0.2), 0, -2),
            (cloth(2), 0.05, -6))
    put("irina.burst", "burst", reverb(x, 2.0, 0.3))
    # rage (phase 3): racing heartbeat + tearing + blood
    rng(298)
    hb = mix(*[(heartbeat(0.6), 0.45 * k, -1 + (k == 0) * -3) for k in range(5)])
    x = mix((hb, 0, 0), (semis(src("RPGsounds_Kenney/OGG/cloth4.ogg"), -4), 0.2, -4), (blood(1), 0.3, -8), (thread_pull(2, 1.2), 0.1, -6),
            (whisper(1.5, 6, 0.7), 0.3, -8))
    put("irina.rage", "rage", reverb(x, 1.8, 0.3))
    # thud: kneel / fall
    for i in range(2):
        rng(299 + i)
        x = mix((thump(85, 45, 0.5, 0.1, 0.3), 0, 0), (cloth(i + 2), 0, -3), (hp(src("RPGsounds_Kenney/OGG/dropLeather.ogg"), 120), 0, -4))
        put("irina.thud", "thud_%d" % (i + 1), reverb(x, 1.0, 0.2))
    # hurt (3): cloth tears + a thread twang + a sharp breath
    for i in range(3):
        rng(305 + i)
        x = mix((cloth(i + 1), 0, 0), (snap(2000 + 500 * i), 0, -6), (hp(noise(0.15), 2500) * adsr(secs(0.15), 0.01, 0.05, 0.5, 0.08), 0, -12))
        put("irina.hurt", "hurt_%d" % (i + 1), reverb(x, 0.8, 0.15))
    return F


ANIMS = {"irina.animation.json": {
    "irina_walk": [(0.3, "irina.step"), (0.9, "irina.step")],
    "irina_cloth_walk": [(0.1, "irina.cloth|0.6")],
    "irina_staff_attack": [(0.28, "irina.swish"), (0.3, "irina.cloth|0.7")],
    "irina_staff_sweep": [(0.2, "irina.swish"), (0.46, "irina.staff")],
    "irina_cast_short": [(0.1, "irina.cloth|0.6"), (0.3, "irina.thread")],
    "irina_cast_long": [(0.0, "irina.whisper")],
    "irina_cast_long_end": [(0.1, "irina.thread")],
    "irina_mark": [(0.35, "irina.cloth|0.7")],
    "irina_bind": [(0.5, "irina.thread"), (0.9, "irina.thread|1|1.2")],
    "irina_whip": [(0.2, "irina.swish|1.2")],
    "irina_steal": [(0.3, "irina.thread|1.2")],
    "irina_others_happiness": [(1.4, "irina.whisper|2"), (3.6, "irina.thread|2")],
    "irina_only_mine": [(0.6, "irina.thread|1.5"), (1.0, "irina.snap|1.5")],
    "irina_only_mine_broken": [(0.0, "irina.cloth"), (0.1, "irina.thud")],
    "irina_phase2": [(1.45, "irina.burst|3")],
    "irina_phase3": [(1.3, "irina.rage|3")],
    "irina_finisher": [(0.2, "irina.thread|1.5"), (0.8, "irina.cloth"), (1.7, "irina.whisper|1.5"), (2.2, "irina.snap|1.5")],
    "irina_spawn": [(3.5, "irina.whisper|2"), (4.6, "irina.cloth"), (5.2, "irina.swish")],
    "irina_death": [(1.6, "irina.thud"), (2.4, "irina.cloth"), (3.4, "irina.thud|1.5")],
    "irina_gaze": [(0.1, "irina.whisper")],
    "irina_knots": [(0.4, "irina.thread")],
    "irina_swap": [(0.3, "irina.thread")],
    "irina_puppet": [(0.2, "irina.thread")],
    "irina_guard_break": [(0.1, "irina.thread|1.3"), (0.5, "irina.swish|1.3")],
    "irina_replica_break": [(0.5, "irina.thread|1.3")],
}}

VIDEOS = {
    "irina_sound_1": ("t27_finale", {
        "irina_spawn": [(0, "irina.spawn"), (2.6, "irina.snap"), (5.4, "irina.staff")],
        "irina_finisher": [(0, "irina.finisher"), (1.3, "irina.staff")],
        "irina_death": [(0, "irina.death"), (4.2, "irina.death_final")],
    }, []),
    "irina_sound_2": ("t27_combat", {
        "irina_staff_attack": [(0.55, "irina.staff")],
        "irina_cast_short": [(0.8, "irina.snare")],
        "irina_mark": [(0, "irina.mark")],
        "irina_bind": [(0, "irina.bind")],
        "irina_whip": [(0.45, "irina.whip")],
        "irina_steal": [(1.2, "irina.steal")],
    }, []),
    "irina_sound_3": ("t27_special", {
        "irina_others_happiness": [(0, "irina.happiness"), (5.2, "irina.steal")],
        "irina_only_mine": [(0, "irina.cocoon"), (1.6, "irina.cocoon"), (5.4, "irina.cocoon_crush")],
        "irina_only_mine_broken": [(0, "irina.cocoon_break")],
        "irina_phase2": [(0, "irina.phase")],
        "irina_phase3": [(0, "irina.phase")],
        "irina_gaze": [(0.5, "irina.gaze")],
        "irina_knots": [(0.9, "irina.knots"), (1.7, "irina.snare")],
        "irina_swap": [(0.8, "irina.swap")],
        "irina_puppet": [(0.7, "irina.puppet")],
    }, []),
}
