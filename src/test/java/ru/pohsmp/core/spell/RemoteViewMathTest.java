package ru.pohsmp.core.spell;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;
import ru.pohsmp.core.spell.RemoteViewMath.End;

/** Owner 21.11: «Появление Ковена» - the far arena / caster spot chunks for players far from them (RemoteView). */
class RemoteViewMathTest {
    @Test
    void keysPackLikeChunkPos() {
        for (int[] p : new int[][] {{0, 0}, {5, -7}, {-1, -1}, {1875000, -1875000}}) {
            long k = RemoteViewMath.key(p[0], p[1]);
            assertEquals(p[0], RemoteViewMath.x(k));
            assertEquals(p[1], RemoteViewMath.z(k));
        }
        // ChunkPos.asLong(x, z) = x & 0xFFFFFFFFL | (z & 0xFFFFFFFFL) << 32
        assertEquals(3L | (4L << 32), RemoteViewMath.key(3, 4));
    }

    @Test
    void squareIsWholeAndNearestFirst() {
        long[] s = RemoteViewMath.square(10, -3, 3);
        assertEquals(49, s.length);
        assertEquals(49, Arrays.stream(s).distinct().count());
        assertEquals(RemoteViewMath.key(10, -3), s[0], "the centre first");
        int last = 0;
        for (long k : s) {
            int d = RemoteViewMath.cheb(10, -3, RemoteViewMath.x(k), RemoteViewMath.z(k));
            assertTrue(d <= 3);
            assertTrue(d >= last, "rings go outwards");
            last = d;
        }
        assertEquals(1, RemoteViewMath.square(0, 0, 0).length);
    }

    @Test
    void nearPlacesNeedNoWindow() {
        // view distance 10: a radius-3 square up to 7 chunks away is in the player's own view
        assertTrue(RemoteViewMath.covered(0, 0, 7, 0, 3, 10));
        assertTrue(RemoteViewMath.covered(0, 0, -7, 7, 3, 10));
        assertFalse(RemoteViewMath.covered(0, 0, 8, 0, 3, 10));
        assertFalse(RemoteViewMath.covered(0, 0, 200, -40, 3, 10), "the arena 3 km away");
    }

    @Test
    void sendsOnlyWhatTheViewLacks() {
        // far away: the whole square
        assertEquals(49, RemoteViewMath.toSend(0, 0, 10, 100, 100, 3).length);
        // on the edge of the view: only the chunks beyond view distance (x 11..13 at vd 10)
        long[] edge = RemoteViewMath.toSend(0, 0, 10, 10, 0, 3);
        assertEquals(3 * 7, edge.length);
        for (long k : edge) assertTrue(RemoteViewMath.x(k) > 10);
        assertEquals(0, RemoteViewMath.toSend(0, 0, 10, 2, 2, 3).length);
    }

    @Test
    void queueSendsLoadedChunksInOrderAndWaitsForTheRest() {
        long[] s = RemoteViewMath.square(0, 0, 1);   // 9 chunks
        Set<Long> loaded = new HashSet<>();
        for (int i = 0; i < 9; i += 2) loaded.add(s[i]);
        RemoteViewMath.Queue q = new RemoteViewMath.Queue(s);
        long[] a = RemoteViewMath.square(0, 0, 0);
        long[] first = q.next(2, loaded::contains);
        assertArrayEquals(new long[] {s[0], s[2]}, first, "skips the unloaded one, keeps the order");
        assertEquals(a[0], first[0]);
        long[] second = q.next(16, loaded::contains);
        assertEquals(3, second.length);
        assertFalse(q.done(), "the unloaded four wait");
        assertEquals(0, q.next(16, loaded::contains).length);
        for (long k : s) loaded.add(k);
        assertEquals(4, q.next(16, loaded::contains).length);
        assertTrue(q.done());
        assertEquals(9, q.sentCount());
        assertTrue(q.wasSent(s[1]));
    }

    @Test
    void whenAWindowEnds() {
        assertEquals(End.KEEP, RemoteViewMath.end(true, true, true, 100, 200, false));
        assertEquals(End.CLOSE, RemoteViewMath.end(true, true, true, 100, 200, true), "the scene ended");
        assertEquals(End.CLOSE, RemoteViewMath.end(true, true, false, 100, 200, false), "died: the death screen shows his own place");
        assertEquals(End.CLOSE, RemoteViewMath.end(true, true, true, 201, 200, false), "safety limit");
        assertEquals(End.DROP, RemoteViewMath.end(false, true, true, 100, 200, false), "logged out: nothing to send");
        assertEquals(End.DROP, RemoteViewMath.end(true, false, true, 100, 200, false), "other dimension: the client dropped the level");
        assertEquals(End.DROP, RemoteViewMath.end(false, false, false, 999, 200, true));
    }

    @Test
    void covenWatchersKeepTheArenaAndTheCasterSpotUntilThePortal() {
        int tp = 380;
        assertArrayEquals(new boolean[] {true, true}, RemoteViewMath.covenPlaces(0, tp, true, true));
        assertArrayEquals(new boolean[] {true, true}, RemoteViewMath.covenPlaces(399, tp, true, true), "a second after the portal");
        assertArrayEquals(new boolean[] {true, false}, RemoteViewMath.covenPlaces(400, tp, true, true), "everyone is at the arena now");
        assertArrayEquals(new boolean[] {false, true}, RemoteViewMath.covenPlaces(100, tp, false, true), "arena in another dimension");
        assertArrayEquals(new boolean[] {true, false}, RemoteViewMath.covenPlaces(100, tp, true, false));
        assertArrayEquals(new boolean[] {false, false}, RemoteViewMath.covenPlaces(1700, tp, false, true));
    }
}
