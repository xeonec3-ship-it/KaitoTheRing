package ru.pohsmp.core.boss;

import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class BossMathTest {
    private static final double[] T26 = {0.66, 0.33};

    @Test
    void phases() {
        assertEquals(0, BossMath.phaseOf(1.0, T26));
        assertEquals(0, BossMath.phaseOf(0.661, T26));
        assertEquals(1, BossMath.phaseOf(0.66, T26));
        assertEquals(1, BossMath.phaseOf(0.5, T26));
        assertEquals(2, BossMath.phaseOf(0.33, T26));
        assertEquals(2, BossMath.phaseOf(0.0, T26));
        assertEquals(0, BossMath.phaseOf(0.1, new double[0]));
    }

    @Test
    void crossedOnce() {
        assertTrue(BossMath.crossed(0.16, 0.15, 0.15));
        assertTrue(BossMath.crossed(0.5, 0.1, 0.15));
        assertFalse(BossMath.crossed(0.15, 0.10, 0.15));   // already at it: not again
        assertFalse(BossMath.crossed(0.2, 0.16, 0.15));
    }

    @Test
    void floor() {
        assertEquals(5f, BossMath.clipToFloor(100, 5, 50));
        assertEquals(10f, BossMath.clipToFloor(60, 30, 50));
        assertEquals(0f, BossMath.clipToFloor(50, 30, 50));
    }

    @Test
    void scaling() {
        assertEquals(1.0, BossMath.healthMultiplier(0, 0.4, 0.1, 0), 1e-9);
        assertEquals(1.0, BossMath.healthMultiplier(1, 0.4, 0.1, 0), 1e-9);
        assertEquals(1.5, BossMath.healthMultiplier(2, 0.4, 0.1, 0), 1e-9);    // Iron's formula for Tyros: 1 + 0.4e + 0.1e²
        assertEquals(2.2, BossMath.healthMultiplier(3, 0.4, 0.1, 0), 1e-9);
        assertEquals(2.0, BossMath.healthMultiplier(3, 0.4, 0.1, 2.0), 1e-9);  // capped
    }

    @Test
    void easings() {
        for (double u = 0; u <= 1; u += 0.125) {
            assertTrue(BossMath.sine(u) >= 0 && BossMath.sine(u) <= 1);
            assertTrue(BossMath.inOutQuad(u) >= 0 && BossMath.inOutQuad(u) <= 1);
        }
        assertEquals(0, BossMath.inQuad(-1), 1e-9);
        assertEquals(1, BossMath.outCubic(2), 1e-9);
        assertEquals(0.5, BossMath.sine(0.5), 1e-9);
        assertEquals(0.5, BossMath.inOutQuad(0.5), 1e-9);
    }

    @Test
    void bar() {
        assertEquals(3, BossMath.fillWidth(0));
        assertEquals(189, BossMath.fillWidth(1));
        assertEquals(96, BossMath.fillWidth(0.5f));
        assertEquals(189, BossMath.fillWidth(1.4f));
        assertEquals(0, BossMath.overlayFrame(0));
        assertEquals(0, BossMath.overlayFrame(1));
        assertEquals(1, BossMath.overlayFrame(2));
        assertEquals(0, BossMath.overlayFrame(16));
        assertEquals(1f, BossMath.flashAlpha(0), 1e-6);
        assertEquals(0f, BossMath.flashAlpha(6), 1e-6);
        assertTrue(BossMath.flashAlpha(3) < 0.2f);
        assertEquals(0.5f, BossMath.pulseAlpha(0), 1e-6);
        assertEquals(1f, BossMath.pulseAlpha(6), 1e-6);   // a quarter of 1.2 s
    }

    @Test
    void title() {
        assertEquals(0f, BossMath.titleAlpha(0, 60), 1e-6);
        assertEquals(1f, BossMath.titleAlpha(10, 60), 1e-6);
        assertEquals(1f, BossMath.titleAlpha(59, 60), 1e-6);
        assertTrue(BossMath.titleAlpha(67, 60) < 1 && BossMath.titleAlpha(67, 60) > 0);
        assertEquals(0f, BossMath.titleAlpha(75, 60), 1e-6);
    }

    @Test
    void timeline() {
        List<String> log = new ArrayList<>();
        BossTimeline tl = new BossTimeline("t", 5).at(3, () -> log.add("c")).at(0, () -> log.add("a")).at(3, () -> log.add("d"))
                .at(1, () -> log.add("b")).then(() -> log.add("end"));
        int ticks = 0;
        while (tl.tick()) ticks++;
        assertEquals(List.of("a", "b", "c", "d", "end"), log);
        assertEquals(5, ticks);   // ticks 0..4 return true, tick 5 ends
        assertTrue(tl.done());
    }

    @Test
    void timelineCancel() {
        List<String> log = new ArrayList<>();
        BossTimeline tl = new BossTimeline("t", 10).at(5, () -> log.add("x")).then(() -> log.add("end"));
        tl.tick();
        tl.cancel();
        assertFalse(tl.tick());
        assertTrue(log.isEmpty());
    }

    @Test
    void defs() {
        BossDef d = BossDef.builder("test_boss").phases(0.66, 0.33).standardBar().overlay(1, BossDef.Overlay.PULSE, "pulse")
                .overlay(2, BossDef.Overlay.FRAMES, "flames").surrender(0.05, "test_boss_npc").build();
        assertEquals(3, d.phaseCount());
        assertEquals("test_boss_bossbar", d.barPhase(0).sprite());
        assertEquals("test_boss_bossbar_p2_pulse", d.barPhase(1).overlaySprite());
        assertEquals("test_boss_bossbar_p3_flames", d.barPhase(2).overlaySprite());
        assertEquals("test_boss_bossbar_p3", d.barPhase(9).sprite());
        assertSame(d, BossDef.BossDefs.get("test_boss"));
        assertThrows(IllegalArgumentException.class, () -> BossDef.builder("x").phases(0.3, 0.6));
    }
}
