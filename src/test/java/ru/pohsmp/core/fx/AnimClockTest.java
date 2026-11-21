package ru.pohsmp.core.fx;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * The "slideshow" of spell effects on the dedicated server: a simulated client (60 fps, 20 client ticks per second) against a lagging
 * server whose time packets (every 20 server ticks) rewrite the client's level game time. The old timing (gameTime + partialTick)
 * jumps back; AnimClock does not.
 */
class AnimClockTest {
    /** One simulated run: frame times by the old way and by AnimClock. */
    private record Run(List<Double> old, List<Double> clock) {}

    /**
     * @param tps         server ticks per second
     * @param jitterTicks extra network delay of every other time packet, in ticks
     */
    private static Run simulate(double tps, int jitterTicks, int seconds) {
        AnimClock clock = new AnimClock();
        long gameTime = 1000;          // the client's level game time
        double serverTime = 1000;      // the server's game time (advances at tps)
        double nextPacket = 20;        // server ticks until the next time packet
        int packets = 0;
        List<Double> old = new ArrayList<>(), mono = new ArrayList<>();
        int ticks = seconds * 20;
        for (int t = 0; t < ticks; t++) {
            // client tick: the level adds 1 to its time, then our clock ticks
            gameTime++;
            clock.tick();
            // the server advances tps/20 ticks per client tick; every 20 server ticks it sends its time
            serverTime += tps / 20.0;
            nextPacket -= tps / 20.0;
            if (nextPacket <= 0) {
                nextPacket += 20;
                long sent = (long) serverTime;
                if (packets++ % 2 == 1) sent -= jitterTicks;   // late packet: an older value
                gameTime = sent;                               // ClientboundSetTimePacket: setGameTime
            }
            for (int f = 0; f < 3; f++) {   // three frames per tick
                float pt = f / 3f;
                old.add((double) gameTime + pt);
                mono.add(clock.now(pt));
            }
        }
        return new Run(old, mono);
    }

    private static double worstBackStep(List<Double> times) {
        double worst = 0;
        for (int i = 1; i < times.size(); i++) worst = Math.min(worst, times.get(i) - times.get(i - 1));
        return worst;
    }

    private static double worstForwardStep(List<Double> times) {
        double worst = 0;
        for (int i = 1; i < times.size(); i++) worst = Math.max(worst, times.get(i) - times.get(i - 1));
        return worst;
    }

    @Test
    void oldTimingJumpsBackOnLaggingServer() {
        Run r = simulate(14, 0, 10);
        // the fault reproduced: at 14 TPS the client's game time is pulled back about 8 ticks every packet
        assertTrue(worstBackStep(r.old()) < -5, "old timing should jump back, worst " + worstBackStep(r.old()));
    }

    @Test
    void clockIsMonotonicAndSmoothOnLaggingServer() {
        for (double tps : new double[]{20, 19, 14, 8, 25}) {
            Run r = simulate(tps, 2, 10);
            assertTrue(worstBackStep(r.clock()) >= 0, "clock went back at tps " + tps);
            assertTrue(worstForwardStep(r.clock()) <= 1.0 / 3 + 1e-6, "clock jumped forward at tps " + tps);
        }
    }

    @Test
    void jitterAloneMakesOldTimingStutterEvenAt20Tps() {
        Run r = simulate(20, 2, 10);
        assertTrue(worstBackStep(r.old()) < 0, "a late time packet pulls the old timing back");
        assertTrue(worstBackStep(r.clock()) >= 0);
    }

    @Test
    void effectAgeFromPacketIsPlacedOnTheClock() {
        AnimClock c = new AnimClock();
        for (int i = 0; i < 500; i++) c.tick();
        long start = c.ago(30);               // FxMsg START with age 30 (a late viewer)
        assertEquals(30.0, c.now(0) - start, 1e-9);
        for (int i = 0; i < 10; i++) c.tick();
        assertEquals(40.5, c.now(0.5f) - start, 1e-9);
    }

    @Test
    void partialTickIsClamped() {
        AnimClock c = new AnimClock();
        c.tick();
        assertEquals(1.0, c.now(-0.2f), 1e-9);
        assertEquals(2.0, c.now(1.7f), 1e-9);
    }

    @Test
    void precisionHoldsAfterManyHours() {
        AnimClock c = new AnimClock();
        for (long i = 0; i < 20L * 3600 * 30; i++) c.tick();   // 30 hours of play
        assertEquals(0.25, c.now(0.25f) - c.ticks(), 1e-6);
    }
}
