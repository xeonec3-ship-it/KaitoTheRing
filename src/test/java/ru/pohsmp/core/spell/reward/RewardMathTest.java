package ru.pohsmp.core.spell.reward;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import org.junit.jupiter.api.Test;

/** T34: numbers and geometry of the boss reward spells. */
class RewardMathTest {
    @Test
    void sixSpellsThreeLevels() {
        assertEquals(6, RewardMath.ALL.size());
        assertEquals(3, RewardMath.MAX_LEVEL);
    }

    /** Every per-level table has 3 values and never drops with the level. */
    @Test
    void levelTablesGrow() throws IllegalAccessException {
        int n = 0;
        for (Field f : RewardMath.class.getFields()) {
            if (!Modifier.isStatic(f.getModifiers()) || f.getType() != double[].class || f.getName().equals("MIR_TRIES")) continue;
            double[] t = (double[]) f.get(null);
            assertEquals(3, t.length, f.getName());
            for (int i = 1; i < t.length; i++) assertTrue(t[i] >= t[i - 1], f.getName());
            n++;
        }
        assertTrue(n >= 14, "tables: " + n);
    }

    @Test
    void atClampsLevels() {
        double[] t = {1, 2, 3};
        assertEquals(1, RewardMath.at(t, 0));
        assertEquals(1, RewardMath.at(t, 1));
        assertEquals(3, RewardMath.at(t, 3));
        assertEquals(3, RewardMath.at(t, 7));
        assertEquals(50, RewardMath.mana(50, 10, 1));
        assertEquals(70, RewardMath.mana(50, 10, 3));
    }

    /** Yaw 0 looks along +Z (Minecraft). */
    @Test
    void sectorFollowsTheLook() {
        assertTrue(RewardMath.inSector(0, 3, 0, 4, 150), "straight ahead");
        assertFalse(RewardMath.inSector(0, -3, 0, 4, 150), "behind");
        assertFalse(RewardMath.inSector(0, 5, 0, 4, 150), "too far");
        assertTrue(RewardMath.inSector(2.9, 0.9, 0, 4, 150), "~72° to the side: inside 150°");
        assertFalse(RewardMath.inSector(3, -0.5, 0, 4, 150), "~99°: outside");
        assertTrue(RewardMath.inSector(-3, 0.5, 90, 4, 150), "yaw 90 looks along -X");
        assertTrue(RewardMath.inSector(0.1, 0.1, 0, 4, 10), "inside the caster always counts");
    }

    @Test
    void behindIsOppositeTheLook() {
        double[] p = RewardMath.behind(10, 10, 0, 2, 0);   // faces +Z: behind is -Z
        assertEquals(10, p[0], 1e-9);
        assertEquals(8, p[1], 1e-9);
        p = RewardMath.behind(0, 0, 90, 2, 0);              // faces -X: behind is +X
        assertEquals(2, p[0], 1e-9);
        assertEquals(0, p[1], 1e-9);
        assertEquals(0, RewardMath.MIR_TRIES[0]);
        float yaw = RewardMath.yawTo(10, 8, 10, 10);        // from behind, looking at the target
        assertEquals(0, yaw, 1e-4);
    }

    @Test
    void pullStopsNearTheCaster() {
        assertEquals(0, RewardMath.pullSpeed(1.0));
        assertEquals(0, RewardMath.pullSpeed(RewardMath.EMB_STOP_AT));
        double v = RewardMath.pullSpeed(8);
        assertEquals(8 - RewardMath.EMB_STOP_AT, v * 2.2, 1e-9);
        assertEquals(3.0, RewardMath.pullSpeed(100));
    }

    @Test
    void bonusesMultiply() {
        assertEquals(1.0, RewardMath.mult(), 1e-9);
        assertEquals(1.2, RewardMath.mult(RewardMath.EMB_MARK_BONUS), 1e-9);
        assertEquals(1.2 * 1.25, RewardMath.mult(RewardMath.EMB_MARK_BONUS, 0, RewardMath.HAND_BONUS), 1e-9);
    }

    /** Spec: arc r4 150°, ranges 16 / 20 / 16 / 16, banner r8 with 2 soldiers, the hand: 2.5 s, 1.5 s in PvP, bosses slowed 2.5 s. */
    @Test
    void specNumbers() {
        assertEquals(4, RewardMath.ASH_RADIUS);
        assertEquals(150, RewardMath.ASH_ARC);
        assertEquals(3, RewardMath.ASH_TRAIL_SECONDS);
        assertEquals(16, RewardMath.EMB_RANGE);
        assertEquals(5, RewardMath.EMB_MARK[0]);
        assertEquals(0.20, RewardMath.EMB_MARK_BONUS);
        assertEquals(20, RewardMath.ANV_RANGE);
        assertEquals(3, RewardMath.ANV_RADIUS);
        assertEquals(15, RewardMath.ANV_TEMPER[0]);
        assertEquals(0.20, RewardMath.ANV_TEMPER_BONUS);
        assertEquals(20, RewardMath.BAN_SECONDS[0]);
        assertEquals(8, RewardMath.BAN_RADIUS);
        assertEquals(2, RewardMath.BAN_SOLDIERS);
        assertEquals(16, RewardMath.MIR_RANGE);
        assertEquals(2, RewardMath.MIR_INVIS[0]);
        assertEquals(16, RewardMath.HAND_RANGE);
        assertEquals(2.5, RewardMath.HAND_HOLD[0]);
        assertEquals(1.5, RewardMath.HAND_HOLD_PVP[0]);
        assertEquals(2.5, RewardMath.HAND_BOSS_SLOW);
        assertEquals(0.25, RewardMath.HAND_BONUS);
    }
}
