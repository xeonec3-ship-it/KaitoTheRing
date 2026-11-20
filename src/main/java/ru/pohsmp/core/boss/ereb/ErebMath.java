package ru.pohsmp.core.boss.ereb;

/**
 * T30 Ereb: the timings (ticks, from the events of animations/entity/ereb.animation.json and the plans of
 * docs/specs/tasks/T30_ereb_boss.md — the events are not read by the code, the same moments are timers) and the pure geometry of his
 * moves. No Minecraft classes (ErebMathTest).
 */
public final class ErebMath {
    private ErebMath() {}

    // ---------------------------------------------------------------- the scenes
    /** «Появление» 5.0 s: the model is not drawn till `form` (2.2 s); title at `salute` 3.9 s; bar at `ready` 5.0 s. */
    public static final int INTRO = 100, INTRO_FORM = 44, INTRO_BOW = 52, INTRO_TITLE = 78, INTRO_TITLE_HOLD = 60;
    /** Finale 6.5 s: smile 0.3, butterfly 1.4, speak 2.4, cast 3.2 (ButterflyDreamSpell from his point), vanish 5.0, model off at 104. */
    public static final int FINALE = 130, FINALE_SMILE = 6, FINALE_BUTTERFLY = 28, FINALE_SPEAK = 48, FINALE_CAST = 64, FINALE_VANISH = 100,
            FINALE_HIDE = 104;
    /** «Ложный союзник»: glint 0 (0.7 s), gone 12 (ereb_vanish 0.6 s), behind the victim 16, stab 16 + 9 (0.45 s of ereb_backstab),
     * the mask falls 34 (ereb_disguise, swap +10), the end 52; the victim's camera from 16 for 36 ticks. */
    public static final int FA_GONE = 12, FA_APPEAR = 16, FA_STAB = 25, FA_MASK = 34, FA_SWAP = 44, FA = 52, FA_CAM = FA - FA_APPEAR;
    /** Phase change ereb_phase 1.6 s (`phase` 0.8). */
    public static final int PHASE = 32, PHASE_AT = 16;

    // ---------------------------------------------------------------- his animations
    public static final int SHARD_CAST = 24, SHARD_RELEASE = 11;
    public static final int LUNGE = 24, LUNGE_HIT = 10;
    public static final int FLURRY = 36;
    public static final int[] FLURRY_HITS = {9, 16, 23};
    public static final int CAST_ILLUSION = 28, CAST_AT = 15;
    public static final int DISGUISE = 20, DISGUISE_SWAP = 10;
    public static final int VANISH = 16, VANISH_GONE = 12;

    // ---------------------------------------------------------------- the four new spells
    /** «Танец клинков» 4.4 s: blinks 0.05 / 1.15 / 2.25 / 3.35, hits 0.55 / 1.65 / 2.75 / 3.85. */
    public static final int BLADE_DANCE = 88;
    public static final int[] BD_BLINK = {1, 23, 45, 67}, BD_HIT = {11, 33, 55, 77};
    /** «Обманная брешь» 2.4 s: open 0.3 … close 1.8; the counter 0.9 s (parry 0.1, hit 0.45). */
    public static final int FEINT = 48, FEINT_OPEN = 6, FEINT_CLOSE = 36, COUNTER = 18, COUNTER_PARRY = 2, COUNTER_HIT = 9;
    /** «Стеклянный дождь» 1.6 s: marks 0.4, they fall 1.2 s later (fx ereb_glass_rain_mark, 24 ticks). */
    public static final int RAIN = 32, RAIN_MARKS = 8, RAIN_FALL = RAIN_MARKS + 24;
    /** «Шаг сквозь отражение»: out 0.7 s (gone 0.5), 0.6 s of the glint behind the player, in 0.8 s (appear 0), the thrust 0.4 s in. */
    public static final int STEP_OUT = 14, STEP_GONE = 10, STEP_WARN = 12, STEP_APPEAR = STEP_GONE + STEP_WARN, STEP_IN = 16, STEP_STAB = 8,
            STEP = STEP_APPEAR + STEP_IN;
    /** «Дезинтеграция: Реплика»: ereb_replica_break 2.3 s, break 0.95, speak 1.55; 2 s after the hold began. */
    public static final int REPLICA_DELAY = 40, REPLICA_ANIM = 46, REPLICA_BREAK = 19, REPLICA_SPEAK = 31;

    /**
     * The finisher (owner 20.11, ТЗ «Добивание»; 2.4 s): he vanishes in a ripple (gone 0.6 s), comes out behind the victim (0.8 s), the
     * thrust in the back (0.45 s after: 1.25 s), the victim breaks into glass and butterflies and dies at 2.2 s; the victim's camera from
     * his coming out for 1.2 s. Until the visual assistant's ereb_finisher exists, his part is ereb_vanish + ereb_backstab (same events).
     */
    public static final int FINISHER = 48, FIN_GONE = 12, FIN_APPEAR = 16, FIN_STAB = FIN_APPEAR + 9, FIN_KILL = 44, FIN_CAM = 24;

    // ---------------------------------------------------------------- geometry (Minecraft yaw: forward = (-sin, cos))

    /** Flat forward of a yaw in degrees: {x, z}. */
    public static double[] forward(double yawDeg) {
        double a = Math.toRadians(yawDeg);
        return new double[] {-Math.sin(a), Math.cos(a)};
    }

    /** Yaw (degrees) looking from (x0,z0) to (x1,z1). */
    public static float yawTo(double x0, double z0, double x1, double z1) {
        return (float) (Math.toDegrees(Math.atan2(z1 - z0, x1 - x0)) - 90);
    }

    /** The point `dist` behind someone at (x,z) looking along yaw: {x, z}. */
    public static double[] behind(double x, double z, double yawDeg, double dist) {
        double[] f = forward(yawDeg);
        return new double[] {x - f[0] * dist, z - f[1] * dist};
    }

    /** The point `dist` in front of someone: {x, z}. */
    public static double[] inFront(double x, double z, double yawDeg, double dist) {
        return behind(x, z, yawDeg, -dist);
    }

    /** Yaw offsets (degrees) of a fan of n shards spread over `spread` degrees, symmetric round 0. */
    public static double[] fan(int n, double spread) {
        double[] out = new double[Math.max(0, n)];
        if (n == 1) return out;
        for (int i = 0; i < n; i++) out[i] = -spread / 2 + spread * i / (n - 1);
        return out;
    }

    /** True if one more shard of the same fan may hurt a target already hit `hits` times. */
    public static boolean shardMayHit(int hits, int cap) {
        return hits < cap;
    }

    /** «Стеклянный дождь»: how many marks each of `players` gets (perPlayer each, at most max over all, spread round-robin). */
    public static int[] rainMarks(int players, int perPlayer, int max) {
        int[] out = new int[Math.max(0, players)];
        int total = Math.min(players * perPlayer, max);
        for (int k = 0; k < total; k++) out[k % players]++;
        return out;
    }

    /** «Танец клинков»: the i-th thrust goes at player i mod n (fewer players: they repeat). */
    public static int danceTarget(int i, int players) {
        return players <= 0 ? -1 : i % players;
    }

    /** Ticks until the next swap with a copy: about `seconds`, ×0.7…1.3 (the T22 «Отражения» rule), at least 10. */
    public static int swapGap(double seconds, double rnd01) {
        return (int) Math.max(10, Math.round(seconds * (0.7 + rnd01 * 0.6) * 20));
    }

    /** A melee pause between min and max ticks. */
    public static int meleePause(int min, int max, double rnd01) {
        int lo = Math.min(min, max), hi = Math.max(min, max);
        return lo + (int) Math.floor(rnd01 * (hi - lo + 1 - 1e-9));
    }

    /** True if a point at (dx,dz) from someone looking along yaw is within `deg` degrees of its front (half-angle). */
    public static boolean inArc(double dx, double dz, double yawDeg, double deg) {
        double len = Math.sqrt(dx * dx + dz * dz);
        if (len < 1e-6) return true;
        double[] f = forward(yawDeg);
        double cos = (dx * f[0] + dz * f[1]) / len;
        return cos >= Math.cos(Math.toRadians(deg));
    }
}
