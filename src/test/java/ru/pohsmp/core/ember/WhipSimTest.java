package ru.pohsmp.core.ember;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/** WhipSim (T14, the physics of the whip) without Minecraft: hanging, strikes, the crack, the body and the ground. */
class WhipSimTest {
    /** Feet at (0, 64, 0), hand in front-right at chest height, blade pointing forward and a little down. Facing +z (angle pi/2). */
    static final WhipSim.Body BODY = new WhipSim.Body(0, 64, 0, 0.3, 1.8);
    static final WhipSim.Pose HAND = new WhipSim.Pose(-0.35, 65.1, 0.45, 0, -0.4, 1);
    static final double FACING = Math.PI / 2;
    /** Grass floor: every block below y 64 is full. */
    static final WhipSim.Solid FLOOR = (x, y, z) -> y < 64 ? 1 : Double.NaN;

    static WhipSim settled(WhipSim.Solid solid) {
        WhipSim w = new WhipSim();
        for (int t = 0; t < 120; t++) w.step(HAND, BODY, solid);
        return w;
    }

    static double segMax(WhipSim w) {
        double m = 0;
        for (int i = 1; i < WhipSim.N - 1; i++) m = Math.max(m, dist(w.point(i), w.point(i + 1)));
        return m;
    }

    static double dist(double[] a, double[] b) {
        return Math.sqrt((a[0] - b[0]) * (a[0] - b[0]) + (a[1] - b[1]) * (a[1] - b[1]) + (a[2] - b[2]) * (a[2] - b[2]));
    }

    static double angleFromHand(WhipSim w, int i) {
        double[] p = w.point(i);
        return Math.atan2(p[2] - HAND.z(), p[0] - HAND.x());
    }

    static void finite(WhipSim w) {
        for (int i = 0; i < WhipSim.N; i++) for (double v : w.point(i)) assertTrue(Double.isFinite(v), "point " + i + " is not finite");
    }

    @Test
    void handleIsPinnedToTheHand() {
        WhipSim w = settled(WhipSim.Solid.NONE);
        double[] r = w.point(0), h = w.point(1);
        assertEquals(HAND.x(), r[0], 1e-9);
        assertEquals(HAND.y(), r[1], 1e-9);
        assertEquals(HAND.z(), r[2], 1e-9);
        // the second point lies along the blade direction
        double seg = w.length() / (WhipSim.N - 1), l = Math.sqrt(0.16 + 1);
        assertEquals(HAND.x() + 0 * seg, h[0], 1e-6);
        assertEquals(HAND.y() - 0.4 / l * seg, h[1], 1e-6);
        assertEquals(HAND.z() + 1 / l * seg, h[2], 1e-6);
    }

    @Test
    void hangsDownAtIdleLengthAndSwaysQuietly() {
        WhipSim w = new WhipSim();
        int cracks = 0;
        for (int t = 0; t < 400; t++) cracks += w.step(HAND, BODY, WhipSim.Solid.NONE).size();
        finite(w);
        assertEquals(0, cracks, "no crack while hanging");
        assertEquals(WhipSim.LEN_IDLE, w.length(), 1e-9);
        double[] tip = w.point(WhipSim.N - 1);
        assertTrue(tip[1] < HAND.y() - 1.0, "the tip hangs down to the floor at the feet: " + tip[1]);
        assertTrue(segMax(w) <= WhipSim.LEN_IDLE / (WhipSim.N - 1) * 1.041, "no stretch");
        assertTrue(w.tipSpeed() < 0.2, "almost still: " + w.tipSpeed());
    }

    @Test
    void lashSweepsTheArcAndTheTipCracks() {
        WhipSim w = settled(WhipSim.Solid.NONE);
        double half = Math.toRadians(50);
        w.lash(FACING, -half, half, 6, false);
        List<WhipSim.Crack> cracks = new ArrayList<>();
        double maxReach = 0, minAng = 9, maxAng = -9, maxLen = 0;
        for (int t = 0; t < 20; t++) {
            cracks.addAll(w.step(HAND, BODY, WhipSim.Solid.NONE));
            maxLen = Math.max(maxLen, w.length());
            finite(w);
            assertTrue(segMax(w) <= w.length() / (WhipSim.N - 1) * 1.041 + 1e-9, "stretch at tick " + t);
            double[] tip = w.point(WhipSim.N - 1);
            maxReach = Math.max(maxReach, Math.hypot(tip[0] - BODY.x(), tip[2] - BODY.z()));
            if (t > 2 && t < 14) {
                minAng = Math.min(minAng, angleFromHand(w, WhipSim.N - 1));
                maxAng = Math.max(maxAng, angleFromHand(w, WhipSim.N - 1));
            }
        }
        assertEquals(WhipSim.LEN_FULL, maxLen, 1e-9, "stretched out to full length");
        assertTrue(maxReach > 4.6, "the whip reaches out toward the 6-block lash of the server: " + maxReach);
        assertTrue(maxAng - minAng > Math.toRadians(70), "the tip sweeps the arc: " + Math.toDegrees(maxAng - minAng));
        assertEquals(1, cracks.size(), "one crack per lash");
        WhipSim.Crack c = cracks.get(0);
        assertTrue(c.speed() > WhipSim.CRACK_SPEED, "crack speed " + c.speed());
    }

    @Test
    void tipEndsOnTheFarSideOfTheArc() {
        WhipSim w = settled(WhipSim.Solid.NONE);
        double half = Math.toRadians(50);
        w.lash(FACING, half, -half, 6, true);   // left to right, rising
        for (int t = 0; t < 10; t++) w.step(HAND, BODY, WhipSim.Solid.NONE);
        double a = angleFromHand(w, WhipSim.N / 2);
        assertTrue(a < FACING, "middle of the whip went to the right of the facing: " + Math.toDegrees(a - FACING));
    }

    @Test
    void shortensBackAfterTheStrike() {
        WhipSim w = settled(WhipSim.Solid.NONE);
        w.lash(FACING, -1, 1, 6, false);
        for (int t = 0; t < 80; t++) w.step(HAND, BODY, WhipSim.Solid.NONE);
        assertFalse(w.striking());
        assertEquals(WhipSim.LEN_IDLE, w.length(), 1e-9);
    }

    @Test
    void vortexFlingsTheWhipAllRound() {
        WhipSim w = settled(WhipSim.Solid.NONE);
        w.vortex(FACING + Math.PI, 1, 10);
        double maxReach = 0, turned = 0, last = angleFromHand(w, WhipSim.N - 1);
        for (int t = 0; t < 14; t++) {
            w.step(HAND, BODY, WhipSim.Solid.NONE);
            finite(w);
            double[] tip = w.point(WhipSim.N - 1);
            maxReach = Math.max(maxReach, Math.hypot(tip[0] - BODY.x(), tip[2] - BODY.z()));
            double a = angleFromHand(w, WhipSim.N - 1), d = a - last;
            while (d > Math.PI) d -= 2 * Math.PI;
            while (d < -Math.PI) d += 2 * Math.PI;
            turned += d;
            last = a;
        }
        assertTrue(maxReach > 4.6 && maxReach < 6.3, "flung out to r ~5: " + maxReach);
        assertTrue(Math.abs(turned) > Math.toRadians(300), "a full turn: " + Math.toDegrees(turned));
    }

    @Test
    void neverInsideTheBody() {
        WhipSim w = settled(WhipSim.Solid.NONE);
        // the hand circles the body while the whip swings round it
        for (int t = 0; t < 200; t++) {
            double a = t * 0.31;
            WhipSim.Pose hand = new WhipSim.Pose(0.5 * Math.cos(a), 65.1, 0.5 * Math.sin(a), -Math.sin(a), -0.3, Math.cos(a));
            if (t % 25 == 0) w.lash(a, -0.9, 0.9, 6, t % 50 == 0);
            w.step(hand, BODY, WhipSim.Solid.NONE);
            for (int i = 4; i < WhipSim.N; i++) {
                double[] p = w.point(i);
                if (p[1] < BODY.y() - 0.1 || p[1] > BODY.y() + BODY.height() + 0.1) continue;
                assertTrue(Math.hypot(p[0], p[2]) >= BODY.halfWidth() + WhipSim.BODY_PAD - 0.02, "point " + i + " inside the body at tick " + t);
            }
        }
    }

    @Test
    void liesOnTheGroundNotUnderIt() {
        WhipSim w = new WhipSim();
        WhipSim.Pose low = new WhipSim.Pose(-0.35, 64.6, 0.45, 0, -0.6, 1);   // hand low: the whip lies on the grass
        for (int t = 0; t < 200; t++) {
            if (t == 100) w.lash(FACING, -0.8, 0.8, 6, false);
            w.step(low, BODY, FLOOR);
            for (int i = 0; i < WhipSim.N; i++) assertTrue(w.point(i)[1] >= 64 - 1e-6, "point " + i + " under the floor at tick " + t);
        }
        double[] tip = w.point(WhipSim.N - 1);
        assertTrue(tip[1] < 64.2, "the tip rests on the floor: " + tip[1]);
    }

    @Test
    void wallStopsTheLash() {
        WhipSim w = settled(WhipSim.Solid.NONE);
        WhipSim.Solid wall = (x, y, z) -> z >= 3 ? 1 : Double.NaN;   // a wall 2.5 blocks in front
        w.lash(FACING, -0.6, 0.6, 6, false);
        for (int t = 0; t < 20; t++) {
            w.step(HAND, BODY, wall);
            for (int i = 0; i < WhipSim.N; i++) assertTrue(w.point(i)[2] < 3 + 1e-6, "point " + i + " in the wall at tick " + t);
        }
    }

    @Test
    void teleportStartsHangingAgain() {
        WhipSim w = settled(WhipSim.Solid.NONE);
        WhipSim.Pose far = new WhipSim.Pose(100, 70, 100, 0, -1, 0);
        w.step(far, new WhipSim.Body(100, 69, 100, 0.3, 1.8), WhipSim.Solid.NONE);
        double[] tip = w.point(WhipSim.N - 1);
        assertTrue(Math.abs(tip[0] - 100) < 0.5 && Math.abs(tip[2] - 100) < 0.5 && tip[1] < 70, "rope moved with the holder");
        finite(w);
    }

    @Test
    void degenerateBladeDirection() {
        WhipSim w = new WhipSim();
        for (int t = 0; t < 50; t++) w.step(new WhipSim.Pose(0, 65, 0, 0, 0, 0), BODY, WhipSim.Solid.NONE);
        finite(w);
    }

    @Test
    void interpolationGoesBetweenTicks() {
        WhipSim w = settled(WhipSim.Solid.NONE);
        w.lash(FACING, -1, 1, 6, false);
        w.step(HAND, BODY, WhipSim.Solid.NONE);
        double[] a = w.point(WhipSim.N - 1);
        w.step(HAND, BODY, WhipSim.Solid.NONE);
        double[] b = w.point(WhipSim.N - 1), start = new double[3 * WhipSim.N], mid = new double[3 * WhipSim.N], end = new double[3 * WhipSim.N];
        w.sample(0, start);
        w.sample(0.5, mid);
        w.sample(1, end);
        int k = 3 * (WhipSim.N - 1);
        for (int j = 0; j < 3; j++) {
            assertEquals(a[j], start[k + j], 1e-9, "partial 0 is the previous tick");
            assertEquals(b[j], end[k + j], 1e-9, "partial 1 is now");
        }
        // half way goes through the substeps: the tip follows its curved path, not the straight chord between the ticks
        double chord = dist(a, b), viaMid = dist(a, new double[] {mid[k], mid[k + 1], mid[k + 2]}) + dist(new double[] {mid[k], mid[k + 1], mid[k + 2]}, b);
        assertTrue(viaMid >= chord - 1e-9);
    }

    @Test
    void survivesWildHandsAndStrikeAfterStrike() {
        java.util.Random rnd = new java.util.Random(14);
        WhipSim w = new WhipSim();
        double hx = -0.35, hz = 0.45, worst = 0;
        for (int t = 0; t < 1500; t++) {
            hx += (rnd.nextDouble() - 0.5) * 0.8;   // jerky hand (an animation at speed), kept near the body
            hz += (rnd.nextDouble() - 0.5) * 0.8;
            double r = Math.hypot(hx, hz);
            if (r > 0.9) {
                hx *= 0.9 / r;
                hz *= 0.9 / r;
            }
            WhipSim.Pose hand = new WhipSim.Pose(hx, 64.4 + rnd.nextDouble() * 1.4, hz, rnd.nextDouble() - 0.5, rnd.nextDouble() - 0.7, rnd.nextDouble() - 0.5);
            if (rnd.nextInt(9) == 0) w.lash(rnd.nextDouble() * 6.3, -0.87, 0.87, 4 + rnd.nextInt(4), rnd.nextBoolean());
            if (rnd.nextInt(60) == 0) w.vortex(rnd.nextDouble() * 6.3, rnd.nextBoolean() ? 1 : -1, 10);
            w.step(hand, BODY, FLOOR);
            finite(w);
            worst = Math.max(worst, segMax(w) / (w.length() / (WhipSim.N - 1)));
            for (int i = 0; i < WhipSim.N; i++) assertTrue(w.point(i)[1] >= 64 - 1e-6, "under the floor at tick " + t);
        }
        assertTrue(worst < 1.041, "worst stretch " + worst);
    }

    @Test
    void calmsDownAfterTheStrikeWithoutTwitching() {   // owner 19.11: "его постоянно дёргает"
        WhipSim w = new WhipSim();
        for (int t = 0; t < 120; t++) w.step(HAND, BODY, FLOOR);
        w.lash(FACING, -0.87, 0.87, 6, false);
        int cracks = 0;
        double later = 0;
        for (int t = 0; t < 60; t++) {
            cracks += w.step(HAND, BODY, FLOOR).size();
            if (t >= 20) later = Math.max(later, w.tipSpeed());
        }
        assertEquals(1, cracks, "one crack, none while it settles");
        assertTrue(later < 0.8, "settling and shortening are smooth, no tick-to-tick jumps: " + later);
    }

    /** The holder walks or runs +z (blocks per tick), the hilt pointing back and down as in whip_walk / whip_run; returns the tip. */
    static double[] move(double speed, double dirY) {
        WhipSim w = new WhipSim();
        double[] tip = null;
        for (int t = 0; t < 120; t++) {
            double z = t * speed;
            w.step(new WhipSim.Pose(-0.4, 64.9, z + 0.1, 0, dirY, -1), new WhipSim.Body(0, 64, z, 0.3, 1.8), FLOOR);
            tip = w.point(WhipSim.N - 1);
            tip[2] -= z;   // relative to the holder
            for (int i = 0; i < WhipSim.N; i++) assertTrue(w.point(i)[1] >= 64 - 1e-6, "under the floor while moving");
        }
        return tip;
    }

    @Test
    void streamsBehindAWalkingOrRunningHolder() {   // owner 19.11: behind the player, not in front; drags when walking, flies when running
        double[] walk = move(0.215, -0.8), run = move(0.375, -0.35);
        assertTrue(walk[2] < -1.0, "walking: the whip trails behind: " + walk[2]);
        assertTrue(walk[1] < 64.35, "walking: its end drags on the ground: " + walk[1]);
        assertTrue(run[2] < -1.5, "running: far behind: " + run[2]);
        assertTrue(run[1] > 64.3 && run[1] > walk[1], "running: higher, flying behind: " + run[1]);
    }

    @Test
    void splinePassesThroughThePoints() {
        double[] pts = {0, 0, 0, 1, 0, 0, 2, 1, 0, 3, 1, 1};
        double[] s = WhipSim.spline(pts, 4);
        assertEquals(3 * (3 * 4 + 1), s.length);
        for (int i = 0; i < 4; i++) for (int k = 0; k < 3; k++) assertEquals(pts[3 * i + k], s[3 * (i * 4) + k], 1e-9);
    }

    @Test
    void lookMatchesTheApprovedWhip() {
        assertEquals(0.15, WhipSim.thickness(0), 1e-9);
        assertEquals(0.03, WhipSim.thickness(1), 1e-9);
        assertEquals(0xC2470E, WhipSim.color(0));
        assertEquals(0xFFC27A, WhipSim.color(1));
        assertTrue(WhipSim.N >= 30 && WhipSim.N <= 40);
    }
}
