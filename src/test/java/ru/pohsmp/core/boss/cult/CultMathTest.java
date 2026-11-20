package ru.pohsmp.core.boss.cult;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class CultMathTest {
    @Test
    void timingsMatchThePlans() {
        assertEquals(175, CultMath.INTRO);                    // 8.75 s, fire_boss_spawn
        assertEquals(130, CultMath.INTRO_TITLE);              // 6.5 s
        assertEquals(52, CultMath.DEATH_FLAME_OUT);           // fx cult_leader_death tick 52 (2.6 s)
        assertEquals(18, CultMath.FF_PLANT);                  // plant 0.9 s
        assertEquals(80, CultMath.FF_PILLAR);                 // pillar 4.0 s
        assertEquals(CultMath.ASH_SLASH_ANIM + 10, CultMath.ASH_SLASH);   // slash = 0.5 s of cult_leader_ash_slash
        assertEquals(44, CultMath.FINISHER_KILL);             // kill 2.2 s
        assertEquals(20, CultMath.SICKLE_THROW);              // throw 1.0 s
        assertEquals(36, CultMath.SICKLE_CATCH);              // catch 1.8 s
        assertEquals(36, CultMath.PILLARS_ERUPT);             // erupt 1.8 s
        assertEquals(11, CultMath.BRAND_AT);                  // brand 0.55 s
    }

    @Test
    void ring() {
        assertTrue(Double.isNaN(CultMath.ringRadius(79)));
        assertEquals(3, CultMath.ringRadius(80), 1e-9);
        assertEquals(15.5, CultMath.ringRadius(100), 1e-9);
        assertEquals(28, CultMath.ringRadius(120), 1e-9);
        assertTrue(CultMath.ringHits(15.2, 15.5, 0));
        assertFalse(CultMath.ringHits(15.2, 15.5, 1.2));   // jumped over
        assertFalse(CultMath.ringHits(10, 15.5, 0));
    }

    @Test
    void sickle() {
        double[] s0 = CultMath.sicklePath(0), half = CultMath.sicklePath(0.5), q = CultMath.sicklePath(0.25), end = CultMath.sicklePath(1);
        assertEquals(0, s0[0], 1e-9);
        assertEquals(0, s0[1], 1e-9);
        assertEquals(12, half[1], 1e-9);       // farthest point 12 ahead
        assertEquals(4, q[0], 1e-9);           // right on the way out
        assertTrue(CultMath.sicklePath(0.75)[0] < 0);   // left on the way back
        assertEquals(0, end[1], 1e-9);         // back in the hand
    }

    @Test
    void finisher() {
        assertEquals(0, CultMath.finisherHold(0)[0], 1e-9);
        assertEquals(1, CultMath.finisherHold(14)[0], 1e-9);
        assertEquals(0, CultMath.finisherHold(20)[1], 1e-9);
        assertEquals(2.3, CultMath.finisherHold(34)[1], 1e-9);
        assertEquals(2.3, CultMath.finisherHold(44)[1], 1e-9);
    }

    @Test
    void geometry() {
        assertEquals(1, CultMath.toSegment(5, 1, 0, 0, 10, 0), 1e-9);
        assertEquals(5, CultMath.toSegment(-3, 4, 0, 0, 10, 0), 1e-9);
        assertTrue(CultMath.wallCrossed(27, 29, 28));
        assertTrue(CultMath.wallCrossed(29, 27, 28));
        assertTrue(CultMath.wallCrossed(27.8, 27.8, 28));
        assertFalse(CultMath.wallCrossed(20, 21, 28));
    }
}
