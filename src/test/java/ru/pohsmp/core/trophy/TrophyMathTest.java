package ru.pohsmp.core.trophy;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Random;
import org.junit.jupiter.api.Test;

class TrophyMathTest {
    private static java.util.function.IntFunction<String> slots(String... s) {
        return i -> s[i];
    }

    @Test
    void fullSetNeedsAllFourOfOneBoss() {
        assertTrue(TrophyMath.fullSet("smith", slots("smith", "smith", "smith", "smith")));
        assertFalse(TrophyMath.fullSet("smith", slots("smith", "smith", "smith", null)));
        assertFalse(TrophyMath.fullSet("smith", slots("smith", "smith", "warlord", "smith")));
        assertEquals(3, TrophyMath.pieces("jealous", slots("jealous", null, "jealous", "jealous")));
        assertEquals("traitor", TrophyMath.fullSetOf(slots("traitor", "traitor", "traitor", "traitor")));
        assertNull(TrophyMath.fullSetOf(slots(null, "traitor", "traitor", "traitor")));
        assertNull(TrophyMath.fullSetOf(slots("traitor", "jealous", "traitor", "traitor")));
        assertEquals(0, TrophyMath.pieces(null, slots(null, null, null, null)));
    }

    @Test
    void cooldownBlocksUntilItRunsOut() {
        TrophyMath.Cooldowns cd = new TrophyMath.Cooldowns();
        assertTrue(cd.tryUse("p:warlord", 100, 2400));
        assertFalse(cd.tryUse("p:warlord", 101, 2400));
        assertFalse(cd.ready("p:warlord", 2499));
        assertEquals(1, cd.left("p:warlord", 2499));
        assertTrue(cd.ready("p:warlord", 2500));
        assertTrue(cd.tryUse("q:warlord", 101, 2400), "cooldowns are per player");
        assertTrue(cd.tryUse("p:traitor", 101, 400), "and per ability");
        cd.prune(3000);
        assertEquals(0, cd.size());
        assertTrue(cd.tryUse("p:warlord", 3000, 2400));
    }

    @Test
    void decoyChanceIsAboutFifteenPercent() {
        assertFalse(TrophyMath.decoy(0.0, 0.15, 5, false), "not on cooldown");
        assertFalse(TrophyMath.decoy(0.0, 0.15, 0, true), "not without damage");
        assertTrue(TrophyMath.decoy(0.149, 0.15, 5, true));
        assertFalse(TrophyMath.decoy(0.15, 0.15, 5, true));
        Random r = new Random(35);
        int hits = 0, n = 100_000;
        for (int i = 0; i < n; i++) if (TrophyMath.decoy(r.nextDouble(), 0.15, 1, true)) hits++;
        assertEquals(0.15, hits / (double) n, 0.005);
    }

    @Test
    void decoyWithCooldownAtMostOnePerWindow() {
        TrophyMath.Cooldowns cd = new TrophyMath.Cooldowns();
        Random r = new Random(1);
        int doubles = 0;
        for (long t = 0; t < 1600; t += 5)   // a hit every 5 ticks for 80 s, cooldown 160 ticks
            if (TrophyMath.decoy(r.nextDouble(), 0.15, 3, cd.ready("m", t)) && cd.tryUse("m", t, 160)) doubles++;
        assertTrue(doubles <= 10 && doubles >= 5, "doubles: " + doubles);
    }

    @Test
    void reflectShareAndCap() {
        assertEquals(1.0f, TrophyMath.reflect(10, 0.10, 20), 1e-6);
        assertEquals(20f, TrophyMath.reflect(1000, 0.10, 20), 1e-6);
        assertEquals(0f, TrophyMath.reflect(0, 0.10, 20));
        assertEquals(0f, TrophyMath.reflect(Float.NaN, 0.10, 20));
    }

    @Test
    void standFastUnderThreshold() {
        assertTrue(TrophyMath.standFast(10, 5, 20, 0.30));    // 5 left < 6
        assertFalse(TrophyMath.standFast(20, 5, 20, 0.30));   // 15 left
        assertTrue(TrophyMath.standFast(4, 10, 20, 0.30));    // a killing hit counts too (it gets halved)
        assertFalse(TrophyMath.standFast(10, 0, 20, 0.30));
    }

    @Test
    void dashIsAFastStepNotATeleport() {
        assertFalse(TrophyMath.dash(0.28, 0, 0.75, 6), "sprint");
        assertFalse(TrophyMath.dash(0.45, 0.2, 0.75, 6), "sprint jump");
        assertTrue(TrophyMath.dash(0.6, 0.6, 0.75, 6), "roll");
        assertFalse(TrophyMath.dash(20, 0, 0.75, 6), "teleport");
    }

    @Test
    void temperedWeapon() {
        assertEquals(11f, TrophyMath.tempered(10, 0.10), 1e-5);
        assertEquals(0f, TrophyMath.tempered(0, 0.10));
    }
}
