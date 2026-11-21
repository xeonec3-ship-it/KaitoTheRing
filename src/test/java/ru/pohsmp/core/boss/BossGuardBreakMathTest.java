package ru.pohsmp.core.boss;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

/** T32 «Сломать блок»: who holds the guard, the cooldown, the damage choice, the timings, the reach, the re-cut after Epic Fight. */
class BossGuardBreakMathTest {
    private static final int HOLD = 30, BLOCKS = 3;   // 1.5 s, 3 blocks (the defaults)

    @Test
    void holdLongerThanOneAndAHalfSeconds() {
        BossGuardBreakMath.GuardWatch w = new BossGuardBreakMath.GuardWatch();
        w.update(true, 100);
        w.update(true, 129);
        assertFalse(w.wants(129, HOLD, BLOCKS));
        w.update(true, 130);
        assertTrue(w.wants(130, HOLD, BLOCKS));
        assertEquals(30, w.held(130));
        // lowered and raised again: from zero
        w.update(false, 131);
        assertEquals(0, w.held(131));
        w.update(true, 132);
        assertFalse(w.wants(150, HOLD, BLOCKS));
        assertTrue(w.wants(162, HOLD, BLOCKS));
    }

    @Test
    void threeBlocksInARow() {
        BossGuardBreakMath.GuardWatch w = new BossGuardBreakMath.GuardWatch();
        w.update(false, 0);
        w.blocked(10);
        w.blocked(30);
        assertFalse(w.wants(30, HOLD, BLOCKS));
        w.blocked(50);
        assertTrue(w.wants(50, HOLD, BLOCKS), "a tap-guard player who blocked 3 hits");
        // a hit that landed breaks the chain
        w.landed();
        assertEquals(0, w.blocks());
        assertFalse(w.wants(51, HOLD, BLOCKS));
        // blocks too far apart are not «подряд»
        w.blocked(100);
        w.blocked(100 + BossGuardBreakMath.BLOCK_CHAIN_TICKS + 1);
        assertEquals(1, w.blocks());
        // the chain fades while the boss looks at the player
        w.blocked(500);
        w.update(false, 500 + BossGuardBreakMath.BLOCK_CHAIN_TICKS + 1);
        assertEquals(0, w.blocks());
        // guard_break_blocks = 0: only the hold time counts
        w.blocked(1000);
        w.blocked(1001);
        w.blocked(1002);
        assertFalse(w.wants(1002, HOLD, 0));
    }

    @Test
    void resetAfterABreak() {
        BossGuardBreakMath.GuardWatch w = new BossGuardBreakMath.GuardWatch();
        w.update(true, 0);
        w.blocked(5);
        w.blocked(6);
        w.blocked(7);
        assertTrue(w.wants(40, HOLD, BLOCKS));
        w.reset(40);
        assertEquals(0, w.blocks());
        assertFalse(w.wants(41, HOLD, BLOCKS), "the guard held through counts from the break");
        assertTrue(w.wants(70, HOLD, BLOCKS));
    }

    @Test
    void cooldownTwelveSeconds() {
        BossGuardBreakMath.Cooldown cd = new BossGuardBreakMath.Cooldown();
        assertTrue(cd.ready(0));
        cd.use(1000, 12 * 20);
        assertFalse(cd.ready(1000));
        assertFalse(cd.ready(1239));
        assertTrue(cd.ready(1240));
    }

    @Test
    void heavyIsTheStrongestMeleeHit() {
        // Martin, phase 1: swing 20+14, overhead 48, thrust 30
        assertEquals(48, BossGuardBreakMath.heavy(34, 48, 30, 0), 1e-9);
        // phase 3 with the shield dash bigger
        assertEquals(55, BossGuardBreakMath.heavy(34, 48, 30, 55), 1e-9);
        assertEquals(0, BossGuardBreakMath.heavy(), 1e-9);
        assertEquals(12, BossGuardBreakMath.heavy(Double.NaN, -3, 12, Double.POSITIVE_INFINITY), 1e-9);
    }

    @Test
    void timings() {
        // TEMP_GUARD_BREAK: warning 12 ticks, the blow on the 14th, 28 long
        assertArrayEquals(new int[] {2, 14, 28}, BossGuardBreakMath.timing(14, 28, 12));
        assertArrayEquals(new int[] {0, 8, 28}, BossGuardBreakMath.timing(8, 28, 12), "never before the script starts");
        assertArrayEquals(new int[] {14, 14, 15}, BossGuardBreakMath.timing(14, 10, 0), "the script outlives the blow");
    }

    @Test
    void reachAndArc() {
        // yaw 0 = facing +Z
        assertTrue(BossGuardBreakMath.inBlow(0, 0, 3, 0, 4.5, 150));
        assertFalse(BossGuardBreakMath.inBlow(0, 0, -3, 0, 4.5, 150), "behind");
        assertFalse(BossGuardBreakMath.inBlow(0, 0, 5, 0, 4.5, 150), "too far");
        assertFalse(BossGuardBreakMath.inBlow(0, 4, 3, 0, 4.5, 150), "too high");
        assertTrue(BossGuardBreakMath.inBlow(2.5, 0, 1, 0, 4.5, 150), "68° to the side");
        assertFalse(BossGuardBreakMath.inBlow(3, 0, 0.5, 0, 4.5, 150), "80° to the side");
        // yaw 90 = facing -X
        assertTrue(BossGuardBreakMath.inBlow(-3, 0, 0, 90, 4.5, 150));
        assertTrue(BossGuardBreakMath.inBlow(0.2, 0, 0.2, 180, 4.5, 150), "right at the boss");
    }

    @Test
    void epicFightScalingIsCutAgain() {
        // our filter: 300 before the cut → 248 through; Epic Fight ×1.5 → 372: the cut again on 300×1.5 = 450
        assertEquals(450, BossGuardBreakMath.beforeCut(248, 300, 372), 1e-6);
        // not raised: as is
        assertEquals(248, BossGuardBreakMath.beforeCut(248, 300, 248), 1e-6);
        assertEquals(100, BossGuardBreakMath.beforeCut(248, 300, 100), 1e-6);
        // an execution (2^31): no multiplier, the hit before our cut
        assertEquals(300, BossGuardBreakMath.beforeCut(248, 300, 2.1474836E9), 1e-6);
        // nothing passed our filter: Epic Fight's number stands (the filter already cancelled it earlier)
        assertEquals(50, BossGuardBreakMath.beforeCut(0, 300, 50), 1e-6);
        // ×2 on a hit our cut had brought from 100 to 5 (a phase clamp...): 200 to cut again; BossGuard keeps the result ≤ 10
        assertEquals(200, BossGuardBreakMath.beforeCut(5, 100, 10), 1e-6);
        // the hit cut of that: 450 on 9225 hp → ≈ 296, under Epic Fight's 372
        assertEquals(296.4f, BossGuardMath.hitCap(450, 9225, 0.025, 0.3), 0.1f);
    }
}
