package ru.pohsmp.core.boss.martin;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class MartinMathTest {
    @Test
    void timingsMatchTheAnimations() {
        assertEquals(130, MartinMath.INTRO);                 // martin_spawn 6.5 s
        assertEquals(108, MartinMath.INTRO_TITLE);           // title 5.4 s
        assertEquals(20, MartinMath.CAV_CALL);               // call 1.0 s
        assertEquals(68, MartinMath.CAV_ANIM);               // martin_cavalry 3.4 s
        assertEquals(22, MartinMath.HOLD_WALL);              // wall 1.1 s
        assertEquals(4, MartinMath.YIELD_BLOCK);             // block 0.2 s
        assertEquals(48, MartinMath.YIELD_SPEAK);            // speak 2.4 s
        assertEquals(88, MartinMath.YIELD_TO_NPC);           // martin_to_npc 4.4 s
        assertEquals(74, MartinMath.P2_PLANT);               // 2.4 s + plant 1.3 s
        assertEquals(40, MartinMath.P3_ROAR);                // roar 2.0 s
        assertEquals(27, MartinMath.REPLICA_BREAK);          // break 1.35 s
        assertEquals(34, MartinMath.REPLICA_SPEAK);          // speak 1.7 s
        assertEquals(48, MartinMath.REPLICA_ANIM);           // 2.4 s
        assertEquals(15, MartinMath.SWING_HIT);              // hit 0.75 s
        assertEquals(19, MartinMath.OVERHEAD_HIT);           // hit 0.95 s
        assertEquals(20, MartinMath.WALL_SLAM);              // slam 1.0 s
        assertEquals(24, MartinMath.VOLLEY_LOOSE);           // loose 1.2 s
        assertEquals(18, MartinMath.DUEL_CHALLENGE);         // challenge 0.9 s
        assertEquals(12, MartinMath.WARCRY_CRY);             // cry 0.6 s
    }

    @Test
    void cavalryRidersFollowTheLaneFormula() {
        assertTrue(Double.isNaN(MartinMath.riderZ(0, 39)));                  // warning: no rider yet
        assertEquals(-4, MartinMath.riderZ(0, 40), 1e-9);
        assertEquals(48, MartinMath.riderZ(0, 68), 1e-9);                    // −4 + 52
        assertTrue(Double.isNaN(MartinMath.riderZ(0, 69)));
        assertTrue(Double.isNaN(MartinMath.riderZ(1, 41)));                  // rider 1 leaves on 42
        assertEquals(-7.2, MartinMath.riderZ(1, 42), 1e-9);
        assertEquals(-10.4 + 26, MartinMath.riderZ(2, 58), 1e-9);            // halfway
        // a player in the middle of the lane (z 20) is reached by rider 0 at t = 40 + 28·24/52
        double t = 40 + 28 * 24 / 52.0;
        assertTrue(MartinMath.laneHit(0, 20, t));
        assertTrue(MartinMath.laneHit(1.4, 20, t));
        assertFalse(MartinMath.laneHit(1.6, 20, t));                         // outside the 3-block lane
        assertFalse(MartinMath.laneHit(0, 20, 30));                          // during the warning
        assertFalse(MartinMath.laneHit(0, 20, 72));                          // all passed
    }

    @Test
    void counts() {
        assertEquals(3, MartinMath.lanes(1, 3));
        assertEquals(4, MartinMath.lanes(4, 3));
        assertEquals(5, MartinMath.lanes(6, 3));
        assertEquals(3, MartinMath.soldiers(1, 2, 8));
        assertEquals(6, MartinMath.soldiers(4, 2, 8));
        assertEquals(8, MartinMath.soldiers(10, 2, 8));
        assertEquals(2, MartinMath.volleyMarks(1, 1, 6));
        assertEquals(6, MartinMath.volleyMarks(8, 1, 6));
    }

    @Test
    void shieldWall() {
        assertEquals(0, MartinMath.wallZ(10), 1e-9);
        assertEquals(9, MartinMath.wallZ(100), 1e-9);
        assertEquals(18, MartinMath.wallZ(400), 1e-9);
        assertTrue(MartinMath.wallPushes(3, 9.5, 9));
        assertFalse(MartinMath.wallPushes(3, 8.5, 9));                       // behind it
        assertFalse(MartinMath.wallPushes(3, 10, 9));                        // not yet touched
        assertFalse(MartinMath.wallPushes(0.32, 9.5, 9));                    // in a gap
        assertFalse(MartinMath.wallPushes(-6.24 + 0.7, 9.5, 9));
        assertFalse(MartinMath.wallPushes(13, 9.5, 9));                      // beyond its end
    }

    @Test
    void geometry() {
        // yaw 0 faces +Z; the right hand is −X
        double[] l = MartinMath.local(0, 0, 0, -2, 5);
        assertEquals(2, l[0], 1e-9);
        assertEquals(5, l[1], 1e-9);
        assertTrue(MartinMath.inFront(0, 0, 3, 100));
        assertTrue(MartinMath.inFront(0, 1, 3, 100));
        assertFalse(MartinMath.inFront(0, 3, 0, 100));                       // to the side: 90° > 50°
        assertFalse(MartinMath.inFront(0, 0, -3, 100));                      // behind
        assertTrue(MartinMath.inFront(90, -3, 0, 100));                      // yaw 90 faces −X
        assertTrue(MartinMath.blocksLine(0, 0, 10, 0, 7, 0.5, 0.9));
        assertFalse(MartinMath.blocksLine(0, 0, 10, 0, 7, 2, 0.9));
        assertFalse(MartinMath.blocksLine(0, 0, 10, 0, 11, 0, 0.9));        // behind Martin
    }

    @Test
    void finisherHold() {
        double[] a = MartinMath.finisherHold(0);
        assertEquals(0, a[0], 1e-9);                                          // still where it was hit
        double[] b = MartinMath.finisherHold(MartinMath.FINISHER_PIERCE);
        assertEquals(1, b[0], 1e-9);
        assertEquals(3.2, b[1], 1e-9);                                        // pierced 3.2 before him
        double[] c = MartinMath.finisherHold(MartinMath.FINISHER_RAISED);
        assertEquals(4.8, c[2], 1e-9);                                        // over his head
        double[] d = MartinMath.finisherHold(MartinMath.FINISHER_KILL);
        assertEquals(0, d[2], 1e-9);                                          // at his feet when it dies
        assertTrue(MartinMath.FINISHER_KILL < MartinMath.FINISHER);
        assertTrue(MartinMath.FINISHER_CAM_FROM + MartinMath.FINISHER_CAM <= MartinMath.FINISHER);
    }
}
