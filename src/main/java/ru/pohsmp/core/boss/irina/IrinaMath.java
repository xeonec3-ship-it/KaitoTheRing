package ru.pohsmp.core.boss.irina;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import ru.pohsmp.core.boss.BossMath;

/**
 * Pure numbers and rules of T27 «Ирина, Ведьма Ревности» (IrinaMathTest): timings in ticks from the plans of
 * docs/specs/tasks/T27_irina_boss.md «Визуал и ролики» and the animation events of docs/inbox/2026-11-20_mgr_T27_visuals.md
 * (event seconds × 20), the pairs of red threads, the damage split, the knot count, the cocoon, the stolen effect levels, the gaze cone.
 */
public final class IrinaMath {
    private IrinaMath() {}

    /** Phase indices (BossCore.phase()): 0 «Зависть», 1 «Красные нити», 2 «Ярость ревности». */
    public static final int ENVY = 0, THREADS = 1, FURY = 2;
    public static final double[] PHASES = {0.66, 0.33};

    // ---- scenes (ticks)
    /** Появление 7 s: unravel 2.6, pose 4.6 (title + music), flourish 5.4, ready 7.0; title out 6.6–7.1 → held 92..132. */
    public static final int INTRO = 140, INTRO_UNRAVEL = 52, INTRO_POSE = 92, INTRO_FLOURISH = 108, INTRO_TITLE_HOLD = 40;
    /** Смерть 5 s: knees 1.6, hat 2.4, fall 3.4, unravel 4.2 (death_final, music out), gone 5.0. */
    public static final int DEATH = 100, DEATH_KNEES = 32, DEATH_HAT = 48, DEATH_FALL = 68, DEATH_UNRAVEL = 84;
    /** «Чужое счастье» 6 s: title 0.4 (2.5 s), spread 1.4, gather 3.6, absorb 5.2. */
    public static final int HAPPY = 120, HAPPY_TITLE = 8, HAPPY_TITLE_HOLD = 50, HAPPY_SPREAD = 28, HAPPY_GATHER = 72, HAPPY_ABSORB = 104;
    /** «Только мой» 6.2 s: title 0.3 (2 s), yank 1.0, cocoon 1.6, camera back 2.0, crush 5.4. */
    public static final int MINE = 124, MINE_TITLE = 6, MINE_TITLE_HOLD = 40, MINE_YANK = 20, MINE_COCOON = 32, MINE_CAM_END = 40, MINE_CRUSH = 108;
    public static final double MINE_YANK_DIST = 2.0;
    /** Добивание 2.6 s: pulled in 0–0.8 (easeInQuad) to 1.6 before her, pierce 1.3, whisper 1.7, kill 2.2; victim camera 0.3–2.3. */
    public static final int FINISHER = 52, FINISHER_PULL = 16, FINISHER_PIERCE = 26, FINISHER_WHISPER = 34, FINISHER_KILL = 44,
            FINISHER_CAM_FROM = 6, FINISHER_CAM = 40;
    public static final double FINISHER_DIST = 1.6;
    /** «Реплика»: irina_replica_break 2.2 s, break 1.0, speak 1.25; 2 s after the hold began. */
    public static final int REPLICA_DELAY = 40, REPLICA_ANIM = 44, REPLICA_BREAK = 20, REPLICA_SPEAK = 25;

    // ---- attacks (animation lengths and their event ticks)
    public static final int STAFF = 24, STAFF_HIT = 11;
    public static final int MARK = 28, MARK_AT = 14;
    public static final int BIND = 32, BIND_AT = 18;
    public static final int WHIP_WARN = 16, WHIP = WHIP_WARN + 20, WHIP_LASH = WHIP_WARN + 9;
    public static final int STEAL = 30, STEAL_PULL = 6, STEAL_ABSORB = 24;
    public static final int PHASE2 = 50, PHASE3 = 60, PHASE3_FURY = 30;
    public static final int GAZE = 24, GAZE_AT = 10;
    public static final int KNOTS = 32, KNOTS_AT = 18;
    public static final int SWAP = 28, SWAP_AT = 16;
    public static final int PUPPET = 20, PUPPET_AT = 14;
    /** «Нитяной укол» (the base ranged attack, balance thread_bolt): a knot shows under the target, 0.8 s later it stabs there. */
    public static final int BOLT_WARN = 16;
    public static final double BOLT_RADIUS = 1.5;
    /** Плеть: the area round her (fx irina_whip_warn / irina_whip). */
    public static final double WHIP_IN = 1.5, WHIP_OUT = 7.0;
    /** Узел on the ground: stepping within this (horizontally) snares. */
    public static final double KNOT_RADIUS = 0.9;
    /** Bond strain shown this much before the break distance (balance: 9–12). */
    public static final double STRAIN_MARGIN = 3.0;

    // ---- rules

    /** The phase at a health fraction (same rule as the framework, here for the tests). */
    public static int phaseAt(double frac) {
        return BossMath.phaseOf(frac, PHASES);
    }

    /**
     * Pairs for the red threads: players shuffled (seeded), then taken two by two; with an odd count the last one has no pair.
     * Never pairs a player with itself; ids are compared with equals.
     */
    public static <T> List<List<T>> pairs(List<T> players, long seed) {
        List<T> l = new ArrayList<>(players);
        java.util.Collections.shuffle(l, new Random(seed));
        List<List<T>> out = new ArrayList<>();
        for (int i = 0; i + 1 < l.size(); i += 2) out.add(List.of(l.get(i), l.get(i + 1)));
        return out;
    }

    /** 0 = fine, 1 = strained (from breakAt − STRAIN_MARGIN), 2 = snapped (beyond breakAt). */
    public static int bondState(double dist, double breakAt) {
        if (dist > breakAt) return 2;
        if (dist >= breakAt - STRAIN_MARGIN) return 1;
        return 0;
    }

    /** Damage to a bonded player: {what it takes itself, what its partner takes}; share = the partner's part (balance 0.5). */
    public static float[] split(float amount, double share) {
        double s = BossMath.clamp01(share);
        float other = (float) (amount * s);
        return new float[] {amount - other, other};
    }

    /** «Узлы»: base + ⌈N/2⌉, at most max (balance 3 + ⌈N/2⌉ ≤ 6, so 4–6 for 1–6 players). */
    public static int knotCount(int players, int base, int max) {
        return Math.max(1, Math.min(max, base + (Math.max(1, players) + 1) / 2));
    }

    /** Health of the «Только мой» cocoon: perAlly × (N − 1), not less than min. */
    public static double cocoonHealth(int players, double perAlly, double min) {
        return Math.max(min, perAlly * Math.max(0, players - 1));
    }

    /** Level of a stolen effect on her: resistance not above resistanceMax, every other one not above max (0 = level I). */
    public static int stolenAmplifier(int amplifier, boolean resistance, int max, int resistanceMax) {
        return Math.max(0, Math.min(amplifier, resistance ? resistanceMax : max));
    }

    /** Angle in degrees between a look direction and the direction to a point (both as x, y, z). */
    public static double angleDeg(double lx, double ly, double lz, double dx, double dy, double dz) {
        double l = Math.sqrt(lx * lx + ly * ly + lz * lz), d = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (l < 1e-9 || d < 1e-9) return 180;
        double c = (lx * dx + ly * dy + lz * dz) / (l * d);
        return Math.toDegrees(Math.acos(Math.max(-1, Math.min(1, c))));
    }

    /** «Ревнивый взгляд»: one more tick of looking (inside the cone) or reset; returns the new counter. */
    public static int gazeTick(int counter, double angle, double cone) {
        return angle <= cone ? counter + 1 : 0;
    }

    /** True if somebody who looked `ticks` gets the mark (gaze_seconds). */
    public static boolean gazeCaught(int ticks, int seconds) {
        return ticks >= seconds * 20;
    }

    /** Плеть hits bodies between WHIP_IN and WHIP_OUT from her (horizontal). */
    public static boolean whipHits(double dist) {
        return dist >= WHIP_IN - 0.5 && dist <= WHIP_OUT + 0.3;
    }

    /** Finisher: how far the victim has been pulled from where it was hit (0..1) at tick t (easeInQuad over 0.8 s). */
    public static double finisherPull(int t) {
        return BossMath.inQuad(t / (double) FINISHER_PULL);
    }

    /** «Марионетка» breaks when the others dealt her at least share of her max health meanwhile. */
    public static boolean puppetBroken(double damageSince, double maxHealth, double share) {
        return damageSince >= maxHealth * share;
    }

    /** The damage of someone not marked while the mark is on another player: × mult (balance 0.5); the marked one hits in full. */
    public static float markFilter(float amount, boolean markActive, boolean attackerMarked, double mult) {
        return markActive && !attackerMarked ? (float) (amount * mult) : amount;
    }
}
