package ru.pohsmp.core.spell;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.function.LongPredicate;

/**
 * Pure logic of RemoteView (no Minecraft classes, unit tests: RemoteViewMathTest). A «window» is a square of chunks around a far
 * point (radius r in chunks) that one player's client gets and keeps while a scene shows that point, although the player stands far
 * away from it. Chunk keys are packed as ChunkPos.asLong: x in the low 32 bits, z in the high ones.
 */
public final class RemoteViewMath {
    private RemoteViewMath() {}

    /** Chunks sent per tick to one player (vanilla sends a whole view area at once on a teleport; this spreads ~50 over 3-4 ticks). */
    public static final int PER_TICK = 16;

    public static long key(int x, int z) {
        return (x & 0xFFFFFFFFL) | ((z & 0xFFFFFFFFL) << 32);
    }

    public static int x(long key) {
        return (int) key;
    }

    public static int z(long key) {
        return (int) (key >>> 32);
    }

    public static int cheb(int x1, int z1, int x2, int z2) {
        return Math.max(Math.abs(x1 - x2), Math.abs(z1 - z2));
    }

    /** True if chunk (x, z) lies in the square of radius r around (cx, cz). */
    public static boolean inSquare(int cx, int cz, int r, int x, int z) {
        return cheb(cx, cz, x, z) <= r;
    }

    /**
     * True if the whole square around (cx, cz) is already inside the player's own view area (player in chunk px, pz; server view
     * distance vd): vanilla sends it anyway, no window is needed.
     */
    public static boolean covered(int px, int pz, int cx, int cz, int r, int vd) {
        return cheb(px, pz, cx, cz) + r <= vd;
    }

    /** The square around (cx, cz), nearest to its centre first (the centre is in the shot, the edges only fill the view). */
    public static long[] square(int cx, int cz, int r) {
        List<long[]> l = new ArrayList<>();
        for (int dx = -r; dx <= r; dx++)
            for (int dz = -r; dz <= r; dz++) l.add(new long[] {key(cx + dx, cz + dz), Math.max(Math.abs(dx), Math.abs(dz)), dx * dx + dz * dz});
        l.sort(Comparator.<long[]>comparingLong(a -> a[1]).thenComparingLong(a -> a[2]));
        long[] out = new long[l.size()];
        for (int i = 0; i < out.length; i++) out[i] = l.get(i)[0];
        return out;
    }

    /** What the window must send: the square without the chunks the player's own view area already holds (vanilla keeps those). */
    public static long[] toSend(int px, int pz, int vd, int cx, int cz, int r) {
        return Arrays.stream(square(cx, cz, r)).filter(k -> cheb(px, pz, x(k), z(k)) > vd).toArray();
    }

    /** What happens to a window this tick. */
    public enum End {
        /** Goes on. */
        KEEP,
        /** Ends normally: the client is told to drop the far chunks, the ticket is removed. */
        CLOSE,
        /** Ends without packets: the client has no such chunks any more (left the level, logged out) - only the ticket is removed. */
        DROP
    }

    /**
     * online: the player is still connected; sameLevel: in the window's level; alive: not dead; now/until: game time and the
     * window's limit (a safety net if the scene's own end never comes); released: the scene ended or no longer needs it.
     */
    public static End end(boolean online, boolean sameLevel, boolean alive, long now, long until, boolean released) {
        if (!online || !sameLevel) return End.DROP;
        if (!alive || released || now > until) return End.CLOSE;
        return End.KEEP;
    }

    /**
     * Which places of «Появление Ковена» a watcher keeps in view at tick t of the scene. The arena all along (the camera starts and
     * ends there); the caster's spot until everyone has stepped into his portal (tPortal) and a second after, because the camera
     * shows him there at 8-19 s. Only places in the watcher's own dimension can be shown: the client holds one level.
     * Returns {arena, casterSpot}.
     */
    public static boolean[] covenPlaces(int t, int tPortal, boolean inArenaLevel, boolean inCastLevel) {
        return new boolean[] {inArenaLevel, inCastLevel && t < tPortal + 20};
    }

    /** The chunks of a window still to send, in order; the ones not loaded yet wait for their ticket. */
    public static final class Queue {
        private final LinkedHashSet<Long> pending = new LinkedHashSet<>();
        private final LinkedHashSet<Long> sent = new LinkedHashSet<>();

        public Queue(long[] keys) {
            for (long k : keys) pending.add(k);
        }

        /** Up to max loaded chunks to send now (marked sent). */
        public long[] next(int max, LongPredicate loaded) {
            List<Long> out = new ArrayList<>();
            for (var it = pending.iterator(); it.hasNext() && out.size() < max; ) {
                long k = it.next();
                if (!loaded.test(k)) continue;
                it.remove();
                sent.add(k);
                out.add(k);
            }
            return out.stream().mapToLong(Long::longValue).toArray();
        }

        public boolean done() {
            return pending.isEmpty();
        }

        public boolean wasSent(long k) {
            return sent.contains(k);
        }

        public int sentCount() {
            return sent.size();
        }
    }
}
