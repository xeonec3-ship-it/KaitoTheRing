package ru.pohsmp.core.boss;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class BossGuardMathTest {
    private static final double[] T26 = {0.66, 0.33};

    @Test
    void range() {
        // inside the arena (r28 + 4), close: full
        assertEquals(1, BossGuardMath.rangeMult(10, 20, 28, 4, 48, 0.2), 1e-9);
        assertEquals(1, BossGuardMath.rangeMult(10, 32, 28, 4, 48, 0.2), 1e-9);
        // outside the arena: x0.2
        assertEquals(0.2, BossGuardMath.rangeMult(30, 32.5, 28, 4, 48, 0.2), 1e-9);
        // farther than 48 from the boss: nothing, even inside the arena
        assertEquals(0, BossGuardMath.rangeMult(48.5, 10, 28, 4, 48, 0.2), 1e-9);
        assertEquals(0.2, BossGuardMath.rangeMult(48, 40, 28, 4, 48, 0.2), 1e-9);
        // max distance 0 = off
        assertEquals(0.2, BossGuardMath.rangeMult(500, 40, 28, 4, 0, 0.2), 1e-9);
    }

    @Test
    void hitCap() {
        // 9225 hp: cap 230.6; a 291 hit → 230.6 + 60.4*0.3 ≈ 248.7 (balance 1.2: «после среза ≈ 249»)
        assertEquals(248.7f, BossGuardMath.hitCap(291, 9225, 0.025, 0.3), 0.1f);
        assertEquals(100f, BossGuardMath.hitCap(100, 9225, 0.025, 0.3));
        assertEquals(500f, BossGuardMath.hitCap(500, 9225, 0, 0.3));   // share 0 = off
    }

    @Test
    void phaseClamp() {
        // phase 0 at 70%: a 20% hit stops at 66%
        assertEquals(40.05f, BossGuardMath.phaseClamp(700, 1000, 200, T26, 0), 1e-3);
        assertEquals(10f, BossGuardMath.phaseClamp(700, 1000, 10, T26, 0), 1e-4);
        // exactly 660/1000 still reads as phase 0 in floats: a hair more is let through, then the transition begins
        assertEquals(0, BossMath.phaseOf(660f / 1000f, T26));
        assertEquals(0.05f, BossGuardMath.phaseClamp(660, 1000, 50, T26, 0), 1e-3);
        // already under it (transition starts this tick): not held
        assertEquals(50f, BossGuardMath.phaseClamp(659, 1000, 50, T26, 0), 1e-4);
        // phase 1 → floor 33%
        assertEquals(130.05f, BossGuardMath.phaseClamp(460, 1000, 500, T26, 1), 1e-2);
        // last phase: no floor
        assertEquals(500f, BossGuardMath.phaseClamp(300, 1000, 500, T26, 2), 1e-4);
        // after the clamp the phase is reached exactly
        for (float max : new float[] {1000, 4500, 9225, 12375, 5200 * 1.35f}) {
            float h = max * 0.9f - BossGuardMath.phaseClamp(max * 0.9f, max, max, T26, 0);
            assertEquals(1, BossMath.phaseOf(h / max, T26), "max " + max);   // as BossCore reads it: float health / float max
            h -= BossGuardMath.phaseClamp(h, max, max, T26, 1);
            assertEquals(2, BossMath.phaseOf(h / max, T26), "max " + max);
        }
    }

    @Test
    void regen() {
        assertEquals(1.0, BossGuardMath.phaseStart(T26, 0), 1e-9);
        assertEquals(0.66, BossGuardMath.phaseStart(T26, 1), 1e-9);
        assertEquals(0.33, BossGuardMath.phaseStart(T26, 2), 1e-9);
        // 19 s without damage: nothing
        assertEquals(0f, BossGuardMath.regen(500, 1000, 0.01, 19 * 20, 400, T26, 1));
        // 20 s: 1%/s
        assertEquals(10f, BossGuardMath.regen(500, 1000, 0.01, 400, 400, T26, 1));
        // never above the phase start
        assertEquals(5f, BossGuardMath.regen(655, 1000, 0.01, 1000, 400, T26, 1), 1e-3);
        assertEquals(0f, BossGuardMath.regen(660, 1000, 0.01, 1000, 400, T26, 1));
        assertEquals(0f, BossGuardMath.regen(1000, 1000, 0.01, 1000, 400, T26, 0));
    }

    @Test
    void countdownCap() {
        assertEquals(461.25f, BossGuardMath.capShare(3690, 9225, 0.05), 1e-2);
        assertEquals(100f, BossGuardMath.capShare(100, 9225, 0.05));
    }

    @Test
    void cc() {
        // 8 s stun → 2 s (x0.25 = 2 s); 20 s → capped at 2 s; 2 s → 0.5 s
        assertEquals(40, BossGuardMath.ccTicks(160, 0.25, 40));
        assertEquals(40, BossGuardMath.ccTicks(400, 0.25, 40));
        assertEquals(10, BossGuardMath.ccTicks(40, 0.25, 40));
        assertEquals(1, BossGuardMath.ccTicks(1, 0.25, 40));
        assertEquals(0, BossGuardMath.ccTicks(0, 0.25, 40));
        // «Застывший час»: 1.5 s whatever the spell says
        assertEquals(30, BossGuardMath.ccTicks(160, 1, 30));
    }

    @Test
    void ccWindowsAndImmunity() {
        BossGuardMath.CcWindows w = new BossGuardMath.CcWindows();
        // «Колыбель» 90 ticks of sleep → 22 ticks (x0.25), then 10 s immunity to sleep
        assertEquals(23, w.allow("sleep", 0, 90, 0.25, 40, 200));
        assertTrue(w.active("sleep", 10));
        assertEquals(13, w.allow("sleep", 10, 90, 0.25, 40, 200));   // refresh inside the window: only what is left
        assertEquals(0, w.allow("sleep", 23, 90, 0.25, 40, 200));    // window over: immune
        assertEquals(0, w.allow("sleep", 222, 90, 0.25, 40, 200));
        assertEquals(23, w.allow("sleep", 223, 90, 0.25, 40, 200));  // immunity over
        // another kind is not affected
        assertEquals(10, w.allow("paralysis", 5, 40, 0.25, 40, 200));
        // a hold refreshed every 10 ticks with 15-tick paralysis: never longer than the window of the first one
        BossGuardMath.CcWindows h = new BossGuardMath.CcWindows();
        int total = 0;
        for (long t = 0; t < 200; t++) if (h.allow("trap", t, 80, 0.25, 40, 200) > 0) total++;
        assertEquals(20, total);   // 4 s hold → 1 s
        // «Застывший час»: 1.5 s, 30 s immunity
        BossGuardMath.CcWindows f = new BossGuardMath.CcWindows();
        assertEquals(30, f.allow("frozen_hour", 0, 160, 1, 30, 600));
        assertEquals(0, f.allow("frozen_hour", 100, 160, 1, 30, 600));
        assertEquals(30, f.allow("frozen_hour", 630, 160, 1, 30, 600));
        assertEquals(0, f.left("none", 0));
    }

    @Test
    void recountUpAtOnceDownAfterDelay() {
        BossGuardMath.PlayerCount n = new BossGuardMath.PlayerCount(2);
        assertEquals(2, n.get());
        assertEquals(4, n.update(4, 100, 1200, 8));         // up: at once
        assertEquals(4, n.update(2, 200, 1200, 8));         // down: waits
        assertEquals(4, n.update(3, 800, 1200, 8));
        assertEquals(4, n.update(2, 1300, 1200, 8));        // 1100 ticks below: still 4
        assertEquals(3, n.update(2, 1400, 1200, 8));        // 60 s below: to the peak during the wait (3)
        assertEquals(3, n.update(3, 1500, 1200, 8));
        // the wait resets when they come back
        assertEquals(3, n.update(1, 1600, 1200, 8));
        assertEquals(3, n.update(3, 1700, 1200, 8));
        assertEquals(3, n.update(1, 2000, 1200, 8));
        assertEquals(3, n.update(1, 3100, 1200, 8));
        assertEquals(1, n.update(1, 3200, 1200, 8));
        // cap 8, floor 1
        assertEquals(8, n.update(12, 3300, 1200, 8));
        assertEquals(1, new BossGuardMath.PlayerCount(0).get());
    }

    @Test
    void rescaleKeepsFraction() {
        assertEquals(5125f, BossGuardMath.rescaleHealth(2500, 4500, 9225), 1e-2);   // 55.6% stays 55.6%
        assertEquals(4500f, BossGuardMath.rescaleHealth(9225, 9225, 4500), 1e-2);
        assertEquals(9225f, BossGuardMath.rescaleHealth(10, 0, 9225), 1e-2);
    }

    @Test
    void pillar() {
        BossGuardMath.PillarWatch w = new BossGuardMath.PillarWatch();
        assertFalse(w.update(true, true, 0, 60));
        assertFalse(w.update(true, true, 59, 60));
        assertTrue(w.update(true, true, 60, 60));
        assertTrue(w.on(70, 60));
        assertFalse(w.update(true, false, 80, 60));   // reachable again: reset
        assertFalse(w.on(200, 60));
        assertFalse(w.update(false, true, 300, 60));
    }

    @Test
    void leash() {
        assertFalse(BossGuardMath.leashed(20, 20, 28, 8));   // 28.3 < 36
        assertTrue(BossGuardMath.leashed(30, 25, 28, 8));    // 39 > 36
    }
}
