package ru.pohsmp.core.boss;

/**
 * T32 «Сломать блок» and Epic Fight: the pure part (BossGuardBreakMathTest). Who «держит блок» (guard held longer than
 * guard_break_hold_seconds, or guard_break_blocks of the boss's hits blocked in a row), the boss's cooldown, the damage of the blow
 * (the strongest melee hit of the boss in its phase), the script ticks, and the re-cut of a hit Epic Fight made bigger after our
 * protection (BossGuard) had already cut it.
 */
public final class BossGuardBreakMath {
    private BossGuardBreakMath() {}

    /** Blocks «подряд»: a chain is forgotten when no boss hit was blocked for this long. */
    public static final int BLOCK_CHAIN_TICKS = 160;

    /** One player's guard as the bosses see it (shared by all bosses: the player's guard is one). */
    public static final class GuardWatch {
        private long since = -1, lastBlock = Long.MIN_VALUE / 2, seen;
        private int blocks;

        /** Every tick a boss looks at the player: is the Epic Fight guard held now. */
        public void update(boolean guarding, long now) {
            seen = now;
            if (!guarding) since = -1;
            else if (since < 0) since = now;
            if (now - lastBlock > BLOCK_CHAIN_TICKS) blocks = 0;
        }

        /** A boss hit was blocked (or parried). */
        public void blocked(long now) {
            if (now - lastBlock > BLOCK_CHAIN_TICKS) blocks = 0;
            blocks++;
            lastBlock = now;
        }

        /** A boss hit that could be blocked landed: the chain is broken. */
        public void landed() {
            blocks = 0;
        }

        /** After a Guard Break: everything from zero (a guard still held counts from now). */
        public void reset(long now) {
            blocks = 0;
            if (since >= 0) since = now;
        }

        public long held(long now) {
            return since < 0 ? 0 : now - since;
        }

        public int blocks() {
            return blocks;
        }

        public long seen() {
            return seen;
        }

        /** «Держит блок»: the guard is up longer than holdTicks, or blocksNeeded boss hits were blocked in a row. */
        public boolean wants(long now, int holdTicks, int blocksNeeded) {
            return since >= 0 && now - since >= holdTicks || blocksNeeded > 0 && blocks >= blocksNeeded;
        }
    }

    /** A boss's own Guard Break cooldown (guard_break_cooldown). */
    public static final class Cooldown {
        private long readyAt = Long.MIN_VALUE / 2;

        public boolean ready(long now) {
            return now >= readyAt;
        }

        public void use(long now, int ticks) {
            readyAt = now + Math.max(0, ticks);
        }

        public long readyAt() {
            return readyAt;
        }
    }

    /** The heavy blow's damage: the strongest of the boss's melee hits in its phase (non-numbers and negatives ignored; none = 0). */
    public static double heavy(double... hits) {
        double best = 0;
        for (double h : hits) if (h > best && Double.isFinite(h)) best = h;
        return best;
    }

    /**
     * Ticks of the script: the warning (flash + crack) starts warn ticks before the hit, never before the script's tick 0.
     * Returns {warnAt, hitAt, length}.
     */
    public static int[] timing(int hitAt, int length, int warn) {
        int hit = Math.max(0, hitAt);
        return new int[] {Math.max(0, hit - Math.max(0, warn)), hit, Math.max(hit + 1, length)};
    }

    /** Within the blow's reach: horizontal distance ≤ reach, height ≤ 3, inside the arc (degrees, full) in front of the boss's yaw. */
    public static boolean inBlow(double dx, double dy, double dz, float yaw, double reach, double arc) {
        double h = Math.sqrt(dx * dx + dz * dz);
        if (h > reach || Math.abs(dy) > 3) return false;
        if (h < 0.6) return true;
        double fx = -Math.sin(Math.toRadians(yaw)), fz = Math.cos(Math.toRadians(yaw));
        double cos = (dx * fx + dz * fz) / h;
        return cos >= Math.cos(Math.toRadians(arc / 2));
    }

    /**
     * Epic Fight scales a hit after our filter (animation multipliers, innate skills) and sets an execution to 2^31: the hit the boss
     * takes is what our filter would make of (the hit before our cut) × Epic Fight's multiplier. filtered: what our filter let
     * through; preCut: the hit before the cut; amount: Epic Fight's result. An execution (≥ 1e9) gets no multiplier. Returns the
     * hit to cut again (the caller keeps the result ≤ amount), or amount itself when Epic Fight did not raise it.
     */
    public static double beforeCut(double filtered, double preCut, double amount) {
        if (filtered <= 0 || amount <= filtered + 1e-4) return amount;
        double mult = amount >= 1e9 ? 1 : amount / filtered;
        return preCut * mult;
    }
}
