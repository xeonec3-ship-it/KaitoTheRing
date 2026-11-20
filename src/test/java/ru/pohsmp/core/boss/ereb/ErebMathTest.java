package ru.pohsmp.core.boss.ereb;

import static org.junit.jupiter.api.Assertions.*;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.Reader;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class ErebMathTest {
    private static JsonObject anims() throws Exception {
        try (Reader r = Files.newBufferedReader(Path.of("src/main/resources/assets/pohsmp_core/animations/entity/ereb.animation.json"))) {
            return JsonParser.parseReader(r).getAsJsonObject().getAsJsonObject("animations");
        }
    }

    /** Ticks of an animation's length. */
    private static int len(JsonObject a, String name) {
        return (int) Math.round(a.getAsJsonObject(name).get("animation_length").getAsDouble() * 20);
    }

    /** Ticks of the n-th event called `event` of an animation (its timeline keys are seconds). */
    private static int event(JsonObject a, String name, String event, int n) {
        var tl = a.getAsJsonObject(name).getAsJsonObject("timeline");
        var keys = tl.keySet().stream().filter(k -> tl.get(k).getAsString().equals(event)).mapToDouble(Double::parseDouble).sorted().toArray();
        return (int) Math.round(keys[n] * 20);
    }

    @Test
    void timingsMatchTheAnimations() throws Exception {
        JsonObject a = anims();
        assertEquals(len(a, "ereb_spawn"), ErebMath.INTRO);
        assertEquals(event(a, "ereb_spawn", "form", 0), ErebMath.INTRO_FORM);
        assertEquals(event(a, "ereb_spawn", "salute", 0), ErebMath.INTRO_TITLE);
        assertEquals(len(a, "ereb_finale"), ErebMath.FINALE);
        assertEquals(event(a, "ereb_finale", "smile", 0), ErebMath.FINALE_SMILE);
        assertEquals(event(a, "ereb_finale", "butterfly", 0), ErebMath.FINALE_BUTTERFLY);
        assertEquals(event(a, "ereb_finale", "speak", 0), ErebMath.FINALE_SPEAK);
        assertEquals(event(a, "ereb_finale", "cast", 0), ErebMath.FINALE_CAST);
        assertEquals(event(a, "ereb_finale", "vanish", 0), ErebMath.FINALE_VANISH);
        assertEquals(len(a, "ereb_shard_cast"), ErebMath.SHARD_CAST);
        assertEquals(event(a, "ereb_shard_cast", "release", 0), ErebMath.SHARD_RELEASE);
        assertEquals(len(a, "ereb_lunge"), ErebMath.LUNGE);
        assertEquals(event(a, "ereb_lunge", "hit", 0), ErebMath.LUNGE_HIT);
        assertEquals(len(a, "ereb_flurry"), ErebMath.FLURRY);
        for (int i = 0; i < 3; i++) assertEquals(event(a, "ereb_flurry", "hit", i), ErebMath.FLURRY_HITS[i]);
        assertEquals(event(a, "ereb_cast_illusion", "cast", 0), ErebMath.CAST_AT);
        assertEquals(event(a, "ereb_disguise", "swap", 0), ErebMath.DISGUISE_SWAP);
        assertEquals(event(a, "ereb_vanish", "gone", 0), ErebMath.FA_GONE);
        assertEquals(ErebMath.FA_APPEAR + event(a, "ereb_backstab", "stab", 0), ErebMath.FA_STAB);
        assertEquals(event(a, "ereb_phase", "phase", 0), ErebMath.PHASE_AT);
        assertEquals(len(a, "ereb_blade_dance"), ErebMath.BLADE_DANCE);
        for (int i = 0; i < 4; i++) {
            assertEquals(event(a, "ereb_blade_dance", "blink", i), ErebMath.BD_BLINK[i]);
            assertEquals(event(a, "ereb_blade_dance", "hit", i), ErebMath.BD_HIT[i]);
        }
        assertEquals(len(a, "ereb_feint"), ErebMath.FEINT);
        assertEquals(event(a, "ereb_feint", "open", 0), ErebMath.FEINT_OPEN);
        assertEquals(event(a, "ereb_feint", "close", 0), ErebMath.FEINT_CLOSE);
        assertEquals(ErebMath.FEINT_CLOSE - ErebMath.FEINT_OPEN, 30);   // the window: 1.5 s (ТЗ)
        assertEquals(event(a, "ereb_feint_counter", "hit", 0), ErebMath.COUNTER_HIT);
        assertEquals(event(a, "ereb_glass_rain", "marks", 0), ErebMath.RAIN_MARKS);
        assertEquals(event(a, "ereb_glass_rain", "fall", 0), ErebMath.RAIN_FALL);   // marks + 1.2 s
        assertEquals(event(a, "ereb_mirror_step_out", "gone", 0), ErebMath.STEP_GONE);
        assertEquals(12, ErebMath.STEP_WARN);   // the glint behind the player: 0.6 s (ТЗ)
        // the finisher (ТЗ «Добивание»: 2–2.5 s): vanish → behind the victim → the thrust of ereb_backstab → death
        assertEquals(event(a, "ereb_vanish", "gone", 0), ErebMath.FIN_GONE);
        assertEquals(ErebMath.FIN_APPEAR + event(a, "ereb_backstab", "stab", 0), ErebMath.FIN_STAB);
        assertTrue(ErebMath.FIN_STAB < ErebMath.FIN_KILL && ErebMath.FIN_KILL < ErebMath.FINISHER);
        assertTrue(ErebMath.FINISHER >= 40 && ErebMath.FINISHER <= 50);
        assertEquals(len(a, "ereb_replica_break"), ErebMath.REPLICA_ANIM);
        assertEquals(event(a, "ereb_replica_break", "break", 0), ErebMath.REPLICA_BREAK);
        assertEquals(event(a, "ereb_replica_break", "speak", 0), ErebMath.REPLICA_SPEAK);
    }

    @Test
    void geometry() {
        double[] f = ErebMath.forward(0);   // yaw 0 looks south (+z)
        assertEquals(0, f[0], 1e-9);
        assertEquals(1, f[1], 1e-9);
        double[] b = ErebMath.behind(10, 10, 0, 2);
        assertEquals(10, b[0], 1e-9);
        assertEquals(8, b[1], 1e-9);
        double[] front = ErebMath.inFront(0, 0, 90, 3);   // yaw 90 looks west (-x)
        assertEquals(-3, front[0], 1e-9);
        assertEquals(0, front[1], 1e-9);
        assertEquals(0, ErebMath.yawTo(0, 0, 0, 5), 1e-4);
        assertEquals(90, ErebMath.yawTo(0, 0, -5, 0), 1e-4);
        assertTrue(ErebMath.inArc(0, 3, 0, 70));
        assertFalse(ErebMath.inArc(0, -3, 0, 70));   // behind him
    }

    @Test
    void fanAndShards() {
        double[] fan = ErebMath.fan(7, 50);
        assertEquals(7, fan.length);
        assertEquals(-25, fan[0], 1e-9);
        assertEquals(0, fan[3], 1e-9);
        assertEquals(25, fan[6], 1e-9);
        assertEquals(0, ErebMath.fan(1, 50)[0], 1e-9);
        assertTrue(ErebMath.shardMayHit(2, 3));
        assertFalse(ErebMath.shardMayHit(3, 3));   // 3 × 9 = 27 at most from one fan
    }

    @Test
    void rainAndDance() {
        assertArrayEquals(new int[] {2, 2, 2}, ErebMath.rainMarks(3, 2, 10));
        int[] six = ErebMath.rainMarks(6, 2, 10);   // 12 wanted, 10 at most
        assertEquals(10, java.util.Arrays.stream(six).sum());
        assertArrayEquals(new int[] {2, 2, 2, 2, 1, 1}, six);
        assertEquals(0, ErebMath.danceTarget(0, 2));
        assertEquals(1, ErebMath.danceTarget(1, 2));
        assertEquals(0, ErebMath.danceTarget(2, 2));   // fewer players: they repeat
        assertEquals(0, ErebMath.danceTarget(3, 1));
    }

    @Test
    void pauses() {
        assertEquals(84, ErebMath.swapGap(6, 0));    // 6 s × 0.7
        assertEquals(156, ErebMath.swapGap(6, 1));   // 6 s × 1.3
        assertEquals(10, ErebMath.swapGap(0.1, 0));
        assertEquals(8, ErebMath.meleePause(8, 16, 0));
        assertEquals(16, ErebMath.meleePause(8, 16, 0.999999));
    }
}
