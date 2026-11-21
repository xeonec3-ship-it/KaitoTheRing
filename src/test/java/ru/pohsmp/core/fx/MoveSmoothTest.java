package ru.pohsmp.core.fx;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Random;
import org.junit.jupiter.api.Test;

/** FxMsg.MOVE glide: a seal of Eight Shields turning round the caster, moved by a lagging server with bunched packets. */
class MoveSmoothTest {
    /** Seal position at server tick t: a circle of radius 2, one turn per 80 ticks. */
    private static double[] seal(double t) {
        double a = t / 80 * Math.PI * 2;
        return new double[]{2 * Math.cos(a), 64, 2 * Math.sin(a), Math.toDegrees(a)};
    }

    @Test
    void glideHasNoStepsWhereSnappingHas() {
        Random rnd = new Random(7);
        double[] p0 = seal(0);
        MoveSmooth g = new MoveSmooth(p0[0], p0[1], p0[2], p0[3], 0);
        // server at ~14 TPS, packets arrive in bunches: the client clock times of arrival
        double clock = 0, serverT = 0, worstGlide = 0, worstSnap = 0;
        double[] prevGlide = null, prevSnap = p0, snap = p0;
        double nextArrival = 1.4;
        for (int frame = 0; frame < 3 * 20 * 20; frame++) {   // 20 s at 60 fps
            clock = frame / 3.0;
            while (clock >= nextArrival) {
                serverT += 1;
                double[] s = seal(serverT);
                g.move(nextArrival, s[0], s[1], s[2], s[3], 0);
                snap = s;
                nextArrival += 20.0 / 14 * (rnd.nextDouble() < 0.3 ? 0.2 : 1.3);   // jitter: some bunched, some late
            }
            double[] d = g.sample(clock);
            if (prevGlide != null) worstGlide = Math.max(worstGlide, dist(d, prevGlide));
            worstSnap = Math.max(worstSnap, dist(snap, prevSnap));
            prevGlide = d;
            prevSnap = snap;
        }
        // snapping jumps a whole server step (or two in a bunch) in one frame; the glide spreads it over the frames
        assertTrue(worstSnap > 0.3, "snap worst " + worstSnap);
        assertTrue(worstGlide < worstSnap * 0.6, "glide worst " + worstGlide + " vs snap " + worstSnap);
    }

    @Test
    void reachesTargetAfterTheGap() {
        MoveSmooth g = new MoveSmooth(0, 0, 0, 0, 0);
        g.move(10, 1, 0, 0, 0, 0);
        g.move(11, 2, 0, 0, 0, 0);   // gap measured ~1 tick
        double[] mid = g.sample(11 + g.gap() / 2);
        assertTrue(mid[0] > 1 && mid[0] < 2, "x " + mid[0]);
        assertEquals(2, g.sample(30)[0], 1e-9);
    }

    @Test
    void teleportSnaps() {
        MoveSmooth g = new MoveSmooth(0, 0, 0, 0, 0);
        g.move(5, 100, 0, 0, 0, 0);
        assertEquals(100, g.sample(5)[0], 1e-9);
    }

    @Test
    void yawTurnsTheShortWay() {
        MoveSmooth g = new MoveSmooth(0, 0, 0, 170, 0);
        g.move(0, 0, 0, 0, -170, 0);
        double half = g.sample(g.gap() / 2)[3];
        assertEquals(180, ((half % 360) + 360) % 360, 1e-6);
    }

    @Test
    void floatTimeLosesThePartialTickOnAnOldWorld() {
        // the old `level.getGameTime() + partialTick` is long + float = float: on a world 16.8M ticks old (~9.7 days of server uptime)
        // the fraction is gone - the animation moves once a tick, whatever the fps
        long gameTime = 16_800_000L;
        float pt = 0.5f;
        double old = gameTime + pt;
        assertEquals(0.0, old - gameTime, 1e-9);
        AnimClock c = new AnimClock();
        for (int i = 0; i < 100; i++) c.tick();
        assertEquals(0.5, c.now(pt) - c.ticks(), 1e-9);
    }

    private static double dist(double[] a, double[] b) {
        double dx = a[0] - b[0], dz = a[2] - b[2];
        return Math.sqrt(dx * dx + dz * dz);
    }
}
