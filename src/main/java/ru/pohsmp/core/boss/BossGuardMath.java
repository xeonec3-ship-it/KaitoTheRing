package ru.pohsmp.core.boss;

/**
 * Pure rules of the anti-cheese protection of the cult bosses (balance_bosses.md 1.2 / 1.3), no Minecraft classes — covered by
 * BossGuardMathTest. {@link BossGuard} feeds them the world.
 */
public final class BossGuardMath {
    private BossGuardMath() {}

    // ---------------------------------------------------------------- damage multipliers (1.3)

    /**
     * Range rule: the attacker farther than maxDistance from the boss → 0; outside the arena (beyond arenaRadius + margin from its
     * centre) → outsideMult; else 1. Distances in blocks.
     */
    public static double rangeMult(double distToBoss, double distToArenaCentre, double arenaRadius, double margin, double maxDistance,
                                   double outsideMult) {
        if (maxDistance > 0 && distToBoss > maxDistance) return 0;
        if (distToArenaCentre > arenaRadius + margin) return outsideMult;
        return 1;
    }

    /** The big hit cut (Tyros): the part of a hit above share·maxHealth goes ×excessMult. */
    public static float hitCap(float amount, float maxHealth, double share, double excessMult) {
        if (share <= 0 || amount <= 0) return amount;
        float cap = (float) (share * maxHealth);
        if (amount <= cap) return amount;
        return (float) (cap + (amount - cap) * excessMult);
    }

    /**
     * Phase clamp: while the boss is in phase `phase` (the transition to the next one has not begun) its health stays at the next
     * threshold or above. Returns the damage that may be dealt. thresholds as in {@link BossMath#phaseOf}.
     */
    public static float phaseClamp(float health, float maxHealth, float amount, double[] thresholds, int phase) {
        if (amount <= 0 || phase < 0 || phase >= thresholds.length) return amount;
        // a hair under the threshold: health / max (float) must read as <= the threshold, or the phase would never begin
        float floor = (float) (thresholds[phase] * maxHealth) - 0.05f;
        if (health <= floor) return amount;   // already under it: the transition starts this tick, never hold the boss there
        return Math.min(amount, health - floor);
    }

    /** The health fraction a phase began at (regen never goes above it): phase 0 → 1, phase k → thresholds[k-1]. */
    public static double phaseStart(double[] thresholds, int phase) {
        if (phase <= 0 || thresholds.length == 0) return 1;
        return thresholds[Math.min(phase, thresholds.length) - 1];
    }

    /** Regeneration this second: share·max, but not above the start of the current phase. 0 before `delayTicks` without damage. */
    public static float regen(float health, float maxHealth, double share, long ticksSinceDamage, long delayTicks, double[] thresholds, int phase) {
        if (share <= 0 || ticksSinceDamage < delayTicks) return 0;
        float cap = (float) (phaseStart(thresholds, phase) * maxHealth);
        if (health >= cap) return 0;
        return Math.min((float) (share * maxHealth), cap - health);
    }

    /** «Обратный отсчёт» and similar repeats: never more than share of the boss's max health. */
    public static float capShare(float amount, float maxHealth, double share) {
        if (share <= 0) return amount;
        return Math.min(amount, (float) (share * maxHealth));
    }

    // ---------------------------------------------------------------- control (1.2)

    /** A crowd control duration on a boss: ×mult, never longer than maxTicks (at least 1 tick if it applies at all). */
    public static int ccTicks(int ticks, double mult, int maxTicks) {
        if (ticks <= 0) return ticks;
        int t = (int) Math.round(ticks * mult);
        return Math.max(1, Math.min(t, maxTicks));
    }

    /**
     * Control windows of one boss, per kind (an effect id, "root", "frozen_hour"...). The first application opens a window of
     * ccTicks(ticks, mult, max); re-applications inside it (spells that refresh a hold every few ticks) get only what is left of
     * it; after it the boss is immune to that kind for immunityTicks.
     */
    public static final class CcWindows {
        private final java.util.Map<String, long[]> w = new java.util.HashMap<>();

        /** Ticks this application may last (0 = denied: immune). now in game ticks. */
        public int allow(String kind, long now, int ticks, double mult, int maxTicks, int immunityTicks) {
            if (ticks <= 0) return 0;
            long[] s = w.get(kind);
            if (s != null && now < s[0]) return (int) Math.min(ticks, s[0] - now);
            if (s != null && now < s[1]) return 0;
            int d = ccTicks(ticks, mult, maxTicks);
            w.put(kind, new long[] {now + d, now + d + Math.max(0, immunityTicks)});
            return d;
        }

        /** True while a window of this kind is open. */
        public boolean active(String kind, long now) {
            long[] s = w.get(kind);
            return s != null && now < s[0];
        }

        /** Ticks until the open window of this kind ends (0 if none). */
        public long left(String kind, long now) {
            long[] s = w.get(kind);
            return s == null ? 0 : Math.max(0, s[0] - now);
        }
    }

    // ---------------------------------------------------------------- players (1.2: recount)

    /**
     * The counted players N. Up at once; down only after the measured count stayed below N for dropDelay ticks in a row (then to
     * the highest count measured during that wait: a player dead for 50 s still counts). Never above max, never below 1.
     */
    public static final class PlayerCount {
        private int counted;
        private long belowSince = -1;
        private int peakWhileBelow;

        public PlayerCount(int initial) {
            counted = Math.max(1, initial);
        }

        public int get() {
            return counted;
        }

        /** Feeds a measurement taken at `now` (ticks); returns the counted N after it. */
        public int update(int measured, long now, long dropDelay, int max) {
            int m = Math.max(1, Math.min(measured, Math.max(1, max)));
            if (m >= counted) {
                counted = m;
                belowSince = -1;
                return counted;
            }
            if (belowSince < 0) {
                belowSince = now;
                peakWhileBelow = m;
            } else peakWhileBelow = Math.max(peakWhileBelow, m);
            if (now - belowSince >= dropDelay) {
                counted = peakWhileBelow;
                belowSince = -1;
            }
            return counted;
        }
    }

    /** New health after the max changed: the fraction is kept. */
    public static float rescaleHealth(float health, float oldMax, float newMax) {
        if (oldMax <= 0) return newMax;
        return Math.max(Math.min(health / oldMax, 1f) * newMax, Math.min(health, 1f));
    }

    // ---------------------------------------------------------------- pillar (1.3)

    /**
     * «Столб»: a target higher than `height` above the boss's feet that the boss cannot reach for `seconds` → its damage is cut and
     * the boss uses only ranged attacks on it. Feed it every check; returns true while the target counts as on a pillar.
     */
    public static final class PillarWatch {
        private long since = -1;

        public boolean update(boolean high, boolean unreachable, long now, long needTicks) {
            if (!high || !unreachable) {
                since = -1;
                return false;
            }
            if (since < 0) since = now;
            return now - since >= needTicks;
        }

        public boolean on(long now, long needTicks) {
            return since >= 0 && now - since >= needTicks;
        }
    }

    /** Leash: the boss farther than arenaRadius + extra (horizontally) from its spawn point goes back. */
    public static boolean leashed(double dx, double dz, double arenaRadius, double extra) {
        double r = arenaRadius + extra;
        return dx * dx + dz * dz > r * r;
    }
}
