package ru.pohsmp.core.spell;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import java.util.function.Predicate;

/**
 * Owner 21.11, joint cast (T15), the pure part of {@link CoAuthors} (CoAuthorMathTest).
 * <ul>
 *   <li>Point 4 — co-authors: both mages of a merged cast own the spell. Its harm (damage, knockback, control, harmful effects) does not
 *       touch either of them; its help works on both. A link lives from the merge while they cast and {@link #LINGER} after the spell
 *       took effect (zones, rains, the Ark); entities the spell left behind carry the co-authors themselves (an NBT tag) and protect
 *       them for as long as they live.</li>
 *   <li>Point 5 — hostility: two players who hurt each other (either way, any attributed damage: melee, projectile, spell, zone, DoT,
 *       pet / summon, reflected, Epic Fight) cannot cast together for {@code memory} ticks after the last such hit (0 = until one of
 *       them leaves).</li>
 * </ul>
 */
public final class CoAuthorMath {
    private CoAuthorMath() {}

    /** How long the link outlives the moment the spell took effect: the longest joint spell field (the Ark, 60 s) and some margin. */
    public static final long LINGER = 20L * 75;

    /** One merged cast: a and b own spell; until = -1 while they still cast. */
    public static final class Link {
        public final UUID a, b;
        public final String spell;
        long until = -1;

        public Link(UUID a, UUID b, String spell) {
            this.a = a;
            this.b = b;
            this.spell = spell;
        }

        public boolean has(UUID x) {
            return a.equals(x) || b.equals(x);
        }

        public UUID other(UUID x) {
            return a.equals(x) ? b : b.equals(x) ? a : null;
        }

        public boolean alive(long now) {
            return until < 0 || now < until;
        }

        /** The spell took effect: the link stays LINGER more (zones and fields of the spell). */
        public void fired(long now) {
            until = now + LINGER;
        }
    }

    /** All live links of the pair (x, y), in either order. */
    public static List<Link> between(List<Link> links, UUID x, UUID y, long now) {
        List<Link> out = new ArrayList<>();
        if (x == null || y == null || x.equals(y)) return out;
        for (Link l : links) if (l.alive(now) && l.has(x) && y.equals(l.other(x))) out.add(l);
        return out;
    }

    /**
     * True if this harm on victim is stopped. attacker: who the damage is attributed to; spell: the spell of the damage source if known
     * (Iron's spell damage), null otherwise; magic: our own spell damage types (Higher, Divine, ...) or an Iron's spell source;
     * tagged: the co-authors written on the entity that dealt it (a zone, a projectile of the joint spell).
     */
    public static boolean shields(List<Link> links, UUID attacker, UUID victim, long now, String spell, boolean magic, List<UUID> tagged) {
        if (attacker == null || victim == null || attacker.equals(victim)) return false;
        if (tagged != null && tagged.contains(attacker) && tagged.contains(victim)) return true;
        for (Link l : between(links, attacker, victim, now)) {
            if (spell != null) {
                if (spell.equals(l.spell)) return true;
            } else if (magic) return true;
        }
        return false;
    }

    /** True if x and y are co-authors of a live joint cast (target choice of our spells, Iron's friendly fire). */
    public static boolean linked(List<Link> links, UUID x, UUID y, long now) {
        return !between(links, x, y, now).isEmpty();
    }

    public static void prune(List<Link> links, long now) {
        links.removeIf(l -> !l.alive(now));
    }

    // ---- point 5: hostility memory ----

    /** The key of an unordered pair. */
    public static String pair(UUID x, UUID y) {
        return x.compareTo(y) < 0 ? x + "|" + y : y + "|" + x;
    }

    public static void hurt(Map<String, Long> memory, UUID attacker, UUID victim, long now) {
        if (attacker == null || victim == null || attacker.equals(victim)) return;
        memory.put(pair(attacker, victim), now);
    }

    /** memoryTicks: 0 = forever (until one of them leaves: forget()). */
    public static boolean hostile(Map<String, Long> memory, UUID x, UUID y, long now, long memoryTicks) {
        if (x == null || y == null || x.equals(y)) return false;
        Long t = memory.get(pair(x, y));
        if (t == null) return false;
        return memoryTicks <= 0 || now - t < memoryTicks || now < t;
    }

    /** One of them left: every pair with him is forgotten. */
    public static void forget(Map<String, Long> memory, UUID who) {
        String s = who.toString();
        memory.keySet().removeIf(k -> k.startsWith(s + "|") || k.endsWith("|" + s));
    }

    /**
     * Who a hit is attributed to: walks owners (projectile -&gt; shooter, pet / summon -&gt; owner, zone -&gt; caster) from the entity until a
     * player; null if there is none. ownerOf returns the next owner or null; at most 8 steps (owner loops).
     */
    public static <T> T attribute(T e, Function<T, T> ownerOf, Predicate<T> isPlayer) {
        for (int i = 0; e != null && i < 8; i++) {
            if (isPlayer.test(e)) return e;
            e = ownerOf.apply(e);
        }
        return null;
    }

    /** The test helper for the pure part: a fresh memory. */
    public static Map<String, Long> memory() {
        return new HashMap<>();
    }
}
