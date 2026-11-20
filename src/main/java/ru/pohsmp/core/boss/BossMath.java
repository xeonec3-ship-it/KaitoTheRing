package ru.pohsmp.core.boss;

/**
 * Pure helpers of the boss framework (no Minecraft classes, covered by BossMathTest): phases by health, health scaling by players,
 * easings, the boss bar geometry and the title fades.
 */
public final class BossMath {
    private BossMath() {}

    // ---------------------------------------------------------------- phases

    /**
     * Phase (0-based) for a health fraction. thresholds: where each next phase starts, descending ({0.66, 0.33} = three phases:
     * 1.0..0.66 → 0, 0.66..0.33 → 1, below → 2). A fraction exactly on a threshold already belongs to the next phase.
     */
    public static int phaseOf(double frac, double[] thresholds) {
        int p = 0;
        for (double t : thresholds) if (frac <= t) p++;
        return p;
    }

    /** True if health went from above t to t or below in this step (a one-time trigger: «особое» at 15%, surrender at 5%). */
    public static boolean crossed(double before, double after, double t) {
        return before > t && after <= t;
    }

    /**
     * Damage clipped so the health stays at floor or above (the boss surrenders / leaves at floor instead of dying).
     * Returns the damage that may be dealt.
     */
    public static float clipToFloor(float health, float damage, float floor) {
        if (damage <= 0) return damage;
        return Math.max(0, Math.min(damage, health - floor));
    }

    // ---------------------------------------------------------------- scaling

    /**
     * Health multiplier for the number of players in the fight: 1 + e·perExtra + e²·perExtraSq, e = players − 1 (none below one
     * player), never above max (max ≤ 1 means no cap).
     */
    public static double healthMultiplier(int players, double perExtra, double perExtraSq, double max) {
        int e = Math.max(0, players - 1);
        double m = 1 + e * perExtra + (double) e * e * perExtraSq;
        if (max > 1) m = Math.min(m, max);
        return Math.max(1, m);
    }

    // ---------------------------------------------------------------- easings (u in 0..1, clamped)

    public static double clamp01(double u) {
        return u < 0 ? 0 : u > 1 ? 1 : u;
    }

    public static double sine(double u) {
        u = clamp01(u);
        return 0.5 - 0.5 * Math.cos(Math.PI * u);
    }

    public static double inQuad(double u) {
        u = clamp01(u);
        return u * u;
    }

    public static double inOutQuad(double u) {
        u = clamp01(u);
        return u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
    }

    public static double outCubic(double u) {
        u = clamp01(u);
        return 1 - Math.pow(1 - u, 3);
    }

    // ---------------------------------------------------------------- boss bar (sprites 192 wide, rows 0-17 empty, 18-35 full)

    public static final int BAR_W = 192, BAR_H = 18, BAR_BUFFER = 3, FRAME_H = 14, FRAMES = 8, FLASH_TICKS = 6;

    /** Width of the full half: 3 + progress·186 (the frame ends stay as they are). */
    public static int fillWidth(float progress) {
        float p = progress < 0 ? 0 : Math.min(1, progress);
        return BAR_BUFFER + Math.round(p * (BAR_W - 2 * BAR_BUFFER));
    }

    /** Frame of an 8-frame overlay (flames, threads, heat): one frame per 2 ticks. */
    public static int overlayFrame(long tick) {
        return (int) ((tick / 2) % FRAMES);
    }

    /** Pulse of the phase-2 overlay while a lock is on: 0.5 + 0.5·sin(2π·t/1.2 s). t in ticks. */
    public static float pulseAlpha(double ticks) {
        return (float) (0.5 + 0.5 * Math.sin(2 * Math.PI * ticks / 24.0));
    }

    /** The phase change flash: alpha 1 → 0 over 6 ticks (easeOutCubic); 0 after. age in ticks since the change. */
    public static float flashAlpha(double age) {
        if (age < 0 || age >= FLASH_TICKS) return 0;
        return (float) (1 - outCubic(age / FLASH_TICKS));
    }

    // ---------------------------------------------------------------- titles (1024×192, in 0.5 s, out 0.75 s)

    public static final int TITLE_IN = 10, TITLE_OUT = 15;

    /** Alpha of a title shown for hold ticks (in included), then fading out over 15 ticks. age in ticks since it was shown. */
    public static float titleAlpha(double age, int hold) {
        if (age < 0 || age >= hold + TITLE_OUT) return 0;
        if (age < TITLE_IN) return (float) sine(age / TITLE_IN);
        if (age < hold) return 1;
        return (float) (1 - sine((age - hold) / TITLE_OUT));
    }
}
