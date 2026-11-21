package ru.pohsmp.core.trophy;

import java.util.HashMap;
import java.util.Map;
import java.util.function.IntFunction;

/** T35: the pure logic of the boss armor (no Minecraft classes; src/test TrophyMathTest). */
public final class TrophyMath {
    private TrophyMath() {}

    public static final int PIECES = 4;

    /** How many of the four armor slots hold a piece of set (slot index -> set id of the piece there, or null). */
    public static int pieces(String set, IntFunction<String> setInSlot) {
        if (set == null) return 0;
        int n = 0;
        for (int i = 0; i < PIECES; i++) if (set.equals(setInSlot.apply(i))) n++;
        return n;
    }

    /** The full set of one boss is worn: all four slots hold its pieces. */
    public static boolean fullSet(String set, IntFunction<String> setInSlot) {
        return pieces(set, setInSlot) == PIECES;
    }

    /** The set whose four pieces are all worn, or null (slot 0 decides, the rest must match it). */
    public static String fullSetOf(IntFunction<String> setInSlot) {
        String s = setInSlot.apply(0);
        return s != null && fullSet(s, setInSlot) ? s : null;
    }

    /** Cooldowns by key (a player + an ability), in game ticks. */
    public static final class Cooldowns {
        private final Map<String, Long> until = new HashMap<>();

        public boolean ready(String key, long now) {
            Long u = until.get(key);
            return u == null || now >= u;
        }

        /** Starts the cooldown if it is ready; true when it was (the ability fires now). */
        public boolean tryUse(String key, long now, long ticks) {
            if (!ready(key, now)) return false;
            until.put(key, now + Math.max(0, ticks));
            return true;
        }

        public long left(String key, long now) {
            Long u = until.get(key);
            return u == null ? 0 : Math.max(0, u - now);
        }

        public void clear(String prefix) {
            until.keySet().removeIf(k -> k.startsWith(prefix));
        }

        /** Forgets cooldowns that ran out (keeps the map small on a long-running server). */
        public void prune(long now) {
            until.values().removeIf(u -> u <= now);
        }

        public int size() {
            return until.size();
        }
    }

    /** The Mask of Lies leaves a double: roll (uniform [0,1)) under chance, a hit that did damage, the cooldown ready. */
    public static boolean decoy(double roll, double chance, float damage, boolean cooldownReady) {
        return cooldownReady && damage > 0 && roll < chance;
    }

    /** Jealous Attire: the damage the threads give back to the attacker (share of the hit, at most cap; 0 for nothing). */
    public static float reflect(float damage, double share, double cap) {
        if (!(damage > 0) || share <= 0) return 0;
        return (float) Math.min(damage * share, cap);
    }

    /**
     * Warlord: «Стоять насмерть» starts on a hit that would leave the wearer under threshold of max health (that hit is already
     * halved, so it can save from death).
     */
    public static boolean standFast(float health, float damage, float maxHealth, double threshold) {
        return maxHealth > 0 && damage > 0 && health - damage < maxHealth * threshold;
    }

    /**
     * Traitor's Coat: a dash or roll (Epic Fight step, Iron's dash spells, a blink) seen as one tick of horizontal movement faster
     * than minSpeed blocks/tick and not a teleport (over maxSpeed); riding, gliding and falls are filtered by the caller.
     */
    public static boolean dash(double dx, double dz, double minSpeed, double maxSpeed) {
        double v = Math.sqrt(dx * dx + dz * dz);
        return v >= minSpeed && v <= maxSpeed;
    }

    /** Smith's Plate: weapon damage tempered. */
    public static float tempered(float damage, double bonus) {
        return damage > 0 ? (float) (damage * (1 + bonus)) : damage;
    }
}
