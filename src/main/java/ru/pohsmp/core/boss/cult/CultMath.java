package ru.pohsmp.core.boss.cult;

import ru.pohsmp.core.boss.BossMath;

/**
 * Pure numbers of T26 (CultMathTest): timings in ticks from the plans of docs/specs/tasks/T26_cult_leader_boss.md and
 * docs/inbox/2026-11-20_mgr_T26_visuals.md, the ring of «Первое Пламя», the path of «Огненный серп», the finisher hold, distances to
 * a strip on the ground.
 */
public final class CultMath {
    private CultMath() {}

    // ---- scenes (ticks)
    public static final int INTRO = 175, INTRO_HIDE = 30, INTRO_TITLE = 130, INTRO_TITLE_HOLD = 40, INTRO_MUSIC = 130;
    public static final int DEATH = 70, DEATH_FLAME_OUT = 52;
    public static final int FF = 120, FF_PLANT = 18, FF_SIGIL = 32, FF_WARN = 60, FF_PILLAR = 80, FF_RING_END = 120, FF_TITLE = 10, FF_TITLE_HOLD = 50;
    public static final int ASH = 120, ASH_TITLE = 6, ASH_TITLE_HOLD = 40, ASH_GONE = 24, ASH_REFORM = 60, ASH_SLASH_ANIM = 80, ASH_SLASH = 90;
    public static final double ASH_BEFORE = 5.0, ASH_LINE = 56;
    public static final int REPLICA_DELAY = 40, REPLICA_ANIM = 52, REPLICA_CRUSH = 18, REPLICA_SHATTER = 30, REPLICA_SPEAK = 38, REPLICA_TAUNT_COOLDOWN = 400;
    public static final int FINISHER = 48, FINISHER_KILL = 44, FINISHER_CAM_FROM = 6, FINISHER_CAM = 40;
    public static final double FINISHER_DIST = 3.0, FINISHER_LIFT = 2.3;
    public static final int SICKLE = 44, SICKLE_THROW = 20, SICKLE_CATCH = 36, SICKLE_FLIGHT = SICKLE_CATCH - SICKLE_THROW;
    public static final int TRAIL = 28, TRAIL_DASH = 10, TRAIL_DASH_TICKS = 8, TRAIL_BURN = 80;
    public static final double TRAIL_LEN = 12;
    public static final int BRAND = 24, BRAND_AT = 11;
    public static final int PILLARS = 46, PILLARS_MARK = 6, PILLARS_ERUPT = 36, PILLARS_COUNT = 5;
    public static final double PILLAR_R = 1.4, PILLAR_H = 9;
    public static final int VERDICT_WARN = 40, VERDICT_FX = 240;

    /** «Первое Пламя»: radius of the ring of fire at fx tick t (t − 80 since the pillar): 3 → 28 in 2 s; NaN outside. */
    public static double ringRadius(int t) {
        if (t < FF_PILLAR || t > FF_RING_END) return Double.NaN;
        return 3 + 25.0 * (t - FF_PILLAR) / (FF_RING_END - FF_PILLAR);
    }

    /** True if a body at horizontal distance d, height above the ground h, is hit by the ring of radius r (jumping over: h ≥ 1). */
    public static boolean ringHits(double d, double r, double h) {
        return !Double.isNaN(r) && Math.abs(d - r) < 0.8 && h < 1;
    }

    /**
     * «Огненный серп»: the sickle at s (0..1 of its flight) in the boss's axes at the throw: {right, forward}.
     * forward = 6·(1 − cos 2πs) (out to 12 and back), right = 4·sin 2πs (right on the way out, left on the way back).
     */
    public static double[] sicklePath(double s) {
        s = BossMath.clamp01(s);
        return new double[] {4 * Math.sin(2 * Math.PI * s), 6 * (1 - Math.cos(2 * Math.PI * s))};
    }

    /**
     * Finisher: where the victim is at tick t, as {towards (0 = where it was hit, 1 = the hold point 3.0 before the boss), lift}.
     * 0-0.7 s pulled in (easeInQuad), 1.0-1.7 s lifted 2.3 (easeInOutQuad), held after.
     */
    public static double[] finisherHold(int t) {
        double pull = BossMath.inQuad(t / 14.0);
        double lift = t <= 20 ? 0 : FINISHER_LIFT * BossMath.inOutQuad((t - 20) / 14.0);
        return new double[] {pull, lift};
    }

    /** Distance from point (px, pz) to the segment (ax, az)-(bx, bz) on the ground. */
    public static double toSegment(double px, double pz, double ax, double az, double bx, double bz) {
        double dx = bx - ax, dz = bz - az, l2 = dx * dx + dz * dz;
        double u = l2 < 1e-9 ? 0 : BossMath.clamp01(((px - ax) * dx + (pz - az) * dz) / l2);
        double cx = ax + u * dx - px, cz = az + u * dz - pz;
        return Math.sqrt(cx * cx + cz * cz);
    }

    /** The wall of fire: was it crossed between two horizontal distances from the centre (or is the body standing in it)? */
    public static boolean wallCrossed(double before, double now, double r) {
        return before < r && now >= r || before >= r && now < r || Math.abs(now - r) < 0.5;
    }
}
