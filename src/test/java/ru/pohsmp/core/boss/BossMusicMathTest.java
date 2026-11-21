package ru.pohsmp.core.boss;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

class BossMusicMathTest {
    private static boolean[] has(boolean intro, boolean p1, boolean p2, boolean p3) {
        return new boolean[] {intro, p1, p2, p3};
    }

    @Test
    void loopByPhase() {
        assertEquals(1, BossMusicMath.loopOfPhase(0));
        assertEquals(2, BossMusicMath.loopOfPhase(1));
        assertEquals(3, BossMusicMath.loopOfPhase(2));
        assertEquals(3, BossMusicMath.loopOfPhase(7));
        assertEquals(1, BossMusicMath.loopOfPhase(-1));
        assertEquals(3, BossMusicMath.loopOfPhase(BossMath.phaseOf(0.2, new double[] {0.66, 0.33})));
    }

    @Test
    void allLoops() {
        boolean[] all = has(true, true, true, true);
        for (int i = 1; i <= 3; i++) assertEquals(i, BossMusicMath.pickLoop(i, all));
        assertFalse(BossMusicMath.useStub(all));
        assertTrue(BossMusicMath.playIntro(1, all));
        assertFalse(BossMusicMath.playIntro(2, all), "a late viewer / phase 2: no intro");
    }

    @Test
    void missingPhaseLoopFallsBackToPrevious() {
        boolean[] noP3 = has(true, true, true, false);
        assertEquals(2, BossMusicMath.pickLoop(3, noP3));
        boolean[] onlyP1 = has(false, true, false, false);
        assertEquals(1, BossMusicMath.pickLoop(2, onlyP1));
        assertEquals(1, BossMusicMath.pickLoop(3, onlyP1));
        assertFalse(BossMusicMath.playIntro(1, onlyP1), "no intro file: straight into the loop");
        boolean[] noP2 = has(true, true, false, true);
        assertEquals(1, BossMusicMath.pickLoop(2, noP2));
        assertEquals(3, BossMusicMath.pickLoop(3, noP2));
    }

    @Test
    void missingFirstLoopTakesTheNext() {
        boolean[] onlyP3 = has(false, false, false, true);
        assertEquals(3, BossMusicMath.pickLoop(1, onlyP3));
        assertFalse(BossMusicMath.useStub(onlyP3));
    }

    @Test
    void noTrackAtAll() {
        assertTrue(BossMusicMath.useStub(has(false, false, false, false)));
        assertTrue(BossMusicMath.useStub(has(true, false, false, false)), "an intro alone is not a track");
        assertFalse(BossMusicMath.playIntro(1, has(true, false, false, false)));
        assertEquals(0, BossMusicMath.pickLoop(2, has(false, false, false, false)));
        assertEquals(0, BossMusicMath.pickLoop(1, new boolean[0]));
    }

    @Test
    void ticks() {
        assertEquals(30, BossMusicMath.ticks(1.5));
        assertEquals(40, BossMusicMath.ticks(2));
        assertEquals(10, BossMusicMath.ticks(0.5));
        assertEquals(0, BossMusicMath.ticks(-1));
    }

    @Test
    void crossfadeCurve() {
        assertEquals(0, BossMusicMath.fadeGain(0, 1, 0), 1e-6);
        assertEquals(1, BossMusicMath.fadeGain(0, 1, 1), 1e-6);
        assertEquals(1, BossMusicMath.fadeGain(1, 0, 0), 1e-6);
        assertEquals(0, BossMusicMath.fadeGain(1, 0, 1), 1e-6);
        float prevIn = -1, prevOut = 2;
        for (int i = 0; i <= 30; i++) {
            float p = i / 30f;
            float in = BossMusicMath.fadeGain(0, 1, p), out = BossMusicMath.fadeGain(1, 0, p);
            assertEquals(1, in * in + out * out, 1e-5, "equal power at " + p);
            assertTrue(in >= prevIn && out <= prevOut, "monotonic");
            prevIn = in;
            prevOut = out;
        }
        assertEquals(Math.sqrt(0.5), BossMusicMath.fadeGain(0, 1, 0.5f), 1e-5);
        // a fade from a part-way gain ends where asked, clamped outside 0..1
        assertEquals(0.4f, BossMusicMath.fadeGain(0.4f, 0, 0), 1e-6);
        assertEquals(0, BossMusicMath.fadeGain(0.4f, 0, 2), 1e-6);
        assertEquals(0.4f, BossMusicMath.fadeGain(0.4f, 1, -1), 1e-6);
    }
}
