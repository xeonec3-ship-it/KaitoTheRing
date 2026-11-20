package ru.pohsmp.core.boss.erebhand;

import static org.junit.jupiter.api.Assertions.*;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.Reader;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class ErebHandMathTest {
    private static JsonObject anims(String file) throws Exception {
        try (Reader r = Files.newBufferedReader(Path.of("src/main/resources/assets/pohsmp_core/animations/entity/" + file))) {
            return JsonParser.parseReader(r).getAsJsonObject().getAsJsonObject("animations");
        }
    }

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
        JsonObject a = anims("ereb_hand.animation.json");
        assertEquals(len(a, "ereb_hand_spawn"), ErebHandMath.INTRO);
        assertEquals(event(a, "ereb_hand_spawn", "form_hand", 0), ErebHandMath.INTRO_HAND);
        assertEquals(event(a, "ereb_hand_spawn", "form", 0), ErebHandMath.INTRO_FORM);
        assertEquals(event(a, "ereb_hand_spawn", "bow", 0), ErebHandMath.INTRO_BOW);
        assertEquals(event(a, "ereb_hand_spawn", "salute", 0), ErebHandMath.INTRO_TITLE);
        assertEquals(event(a, "ereb_hand_spawn", "speak", 0), ErebHandMath.INTRO_SPEAK);
        assertEquals(len(a, "ereb_hand_phase2"), ErebHandMath.PHASE2);
        assertEquals(event(a, "ereb_hand_phase2", "phase", 0), ErebHandMath.PHASE2_AT);
        assertEquals(len(a, "ereb_hand_phase3"), ErebHandMath.PHASE3);
        assertEquals(event(a, "ereb_hand_phase3", "crack", 0), ErebHandMath.PHASE3_CRACK);
        assertEquals(len(a, "ereb_hand_false_death"), ErebHandMath.DEATH);
        assertEquals(event(a, "ereb_hand_false_death", "hand_break", 0), ErebHandMath.DEATH_HAND);
        assertEquals(event(a, "ereb_hand_false_death", "speak", 0), ErebHandMath.DEATH_SPEAK);
        assertEquals(event(a, "ereb_hand_false_death", "smile", 0), ErebHandMath.DEATH_SMILE);
        assertEquals(event(a, "ereb_hand_false_death", "vanish", 0), ErebHandMath.DEATH_VANISH);
        assertTrue(ErebHandMath.DEATH_END >= ErebHandMath.DEATH_VANISH + 36);   // the T22 waking scene (34 + 2) runs before he is removed

        assertEquals(len(a, "ereb_hand_lunge"), ErebHandMath.LUNGE);
        assertEquals(event(a, "ereb_hand_lunge", "hit", 0), ErebHandMath.LUNGE_HIT);
        assertEquals(len(a, "ereb_hand_flurry"), ErebHandMath.FLURRY);
        for (int i = 0; i < 3; i++) assertEquals(event(a, "ereb_hand_flurry", "hit", i), ErebHandMath.FLURRY_HITS[i]);
        assertEquals(len(a, "ereb_hand_slam"), ErebHandMath.SLAM);
        assertEquals(event(a, "ereb_hand_slam", "raise", 0), ErebHandMath.SLAM_RAISE);
        assertEquals(event(a, "ereb_hand_slam", "slam", 0), ErebHandMath.SLAM_HIT);
        assertEquals(len(a, "ereb_hand_grab"), ErebHandMath.GRAB);
        assertEquals(event(a, "ereb_hand_grab", "grab", 0), ErebHandMath.GRAB_AT);
        assertEquals(len(a, "ereb_hand_squeeze"), ErebHandMath.SQUEEZE);
        assertEquals(event(a, "ereb_hand_squeeze", "squeeze", 0), ErebHandMath.SQUEEZE_AT);
        assertEquals(len(a, "ereb_hand_grab_release"), ErebHandMath.RELEASE);
        assertEquals(event(a, "ereb_hand_grab_release", "release", 0), ErebHandMath.RELEASE_AT);
        assertEquals(len(a, "ereb_hand_cast"), ErebHandMath.CAST);
        assertEquals(event(a, "ereb_hand_cast", "cast", 0), ErebHandMath.CAST_AT);

        assertEquals(len(a, "ereb_hand_hand_of_lies"), ErebHandMath.HOL);
        assertEquals(event(a, "ereb_hand_hand_of_lies", "descend", 0), ErebHandMath.HOL_DESCEND);
        assertEquals(event(a, "ereb_hand_hand_of_lies", "return", 0), ErebHandMath.HOL_RETURN);
        assertEquals(len(a, "ereb_hand_mask_fall"), ErebHandMath.MASK_FALL);
        assertEquals(event(a, "ereb_hand_mask_fall", "tear", 0), ErebHandMath.MASK_TEAR);
        assertEquals(event(a, "ereb_hand_mask_fall", "shatter", 0), ErebHandMath.MASK_SHATTER);
        assertEquals(len(a, "ereb_hand_mask_return"), ErebHandMath.MASK_RETURN);
        assertEquals(event(a, "ereb_hand_mask_return", "mend", 0), ErebHandMath.MASK_MEND);
        assertEquals(40, ErebHandMath.MASK_ARROW);   // the arrow: the first 2 s (ТЗ)
        assertEquals(len(a, "ereb_hand_full_reveal"), ErebHandMath.REVEAL);
        assertEquals(event(a, "ereb_hand_full_reveal", "open", 0), ErebHandMath.REVEAL_OPEN);
        assertEquals(event(a, "ereb_hand_full_reveal", "cast", 0), ErebHandMath.REVEAL_CAST);

        assertEquals(len(a, "ereb_hand_false_flame"), ErebHandMath.FLAME);
        assertEquals(event(a, "ereb_hand_false_flame", "marks", 0), ErebHandMath.FLAME_MARKS);
        assertEquals(ErebHandMath.FLAME_MARKS + 20, ErebHandMath.FLAME_IGNITE);   // the marks: 1 s of warning (fx ereb_hand_false_flame_mark)
        assertEquals(len(a, "ereb_hand_glass_grip"), ErebHandMath.GRIP);
        assertEquals(event(a, "ereb_hand_glass_grip", "grip", 0), ErebHandMath.GRIP_AT);
        assertEquals(20, ErebHandMath.GRIP_AT - event(a, "ereb_hand_glass_grip", "warn", 0));   // the cone: 1 s (ТЗ)
        assertEquals(len(a, "ereb_hand_foreign_oath"), ErebHandMath.OATH);
        assertEquals(event(a, "ereb_hand_foreign_oath", "mark", 0), ErebHandMath.OATH_AT);
        assertEquals(len(a, "ereb_hand_thousand_reflections"), ErebHandMath.THOUSAND);
        assertEquals(event(a, "ereb_hand_thousand_reflections", "mirrors", 0), ErebHandMath.MIRRORS_AT);
        assertEquals(event(a, "ereb_hand_thousand_reflections", "strikes", 0), ErebHandMath.STRIKES_AT);
        assertEquals(len(a, "ereb_hand_reflection_strike"), ErebHandMath.REFL);
        assertEquals(event(a, "ereb_hand_reflection_strike", "hit", 0), ErebHandMath.REFL_HIT);

        assertEquals(len(a, "ereb_hand_finisher"), ErebHandMath.FINISHER);
        assertEquals(event(a, "ereb_hand_finisher", "grab", 0), ErebHandMath.FIN_GRAB);
        assertEquals(event(a, "ereb_hand_finisher", "squeeze", 0), ErebHandMath.FIN_SQUEEZE);
        assertEquals(event(a, "ereb_hand_finisher", "shatter", 0), ErebHandMath.FIN_SHATTER);
        assertEquals(ErebHandMath.FIN_SHATTER + 1, ErebHandMath.FIN_KILL);
        assertEquals(len(a, "ereb_hand_replica_break"), ErebHandMath.REPLICA_ANIM);
        assertEquals(event(a, "ereb_hand_replica_break", "break", 0), ErebHandMath.REPLICA_BREAK);
        assertEquals(event(a, "ereb_hand_replica_break", "speak", 0), ErebHandMath.REPLICA_SPEAK);

        JsonObject g = anims("ereb_hand_giant.animation.json");
        assertEquals(len(g, "ereb_hand_giant_grab"), ErebHandMath.GIANT_GRAB);
        assertEquals(event(g, "ereb_hand_giant_grab", "catch", 0), ErebHandMath.GIANT_CATCH);
        assertEquals(len(g, "ereb_hand_giant_release"), ErebHandMath.GIANT_RELEASE);
        assertEquals(event(g, "ereb_hand_giant_release", "release", 0), ErebHandMath.GIANT_RELEASE_AT);
        assertEquals(len(g, "ereb_hand_giant_slam"), ErebHandMath.GIANT_SLAM);
        assertEquals(event(g, "ereb_hand_giant_slam", "slam", 0), ErebHandMath.GIANT_SLAM_AT);
    }

    @Test
    void sidesAndArcs() {
        double[] f = ErebHandMath.forward(0), r = ErebHandMath.right(0);   // yaw 0 looks south (+z); his right hand is west (-x)
        assertEquals(0, f[0], 1e-9);
        assertEquals(1, f[1], 1e-9);
        assertEquals(-1, r[0], 1e-9);
        assertEquals(0, r[1], 1e-9);
        double[] p = ErebHandMath.local(90, 0.5, 1.45);   // yaw 90 looks west (-x); right = north (-z)
        assertEquals(-1.45, p[0], 1e-9);
        assertEquals(-0.5, p[1], 1e-9);
        assertEquals(0, ErebHandMath.yawTo(0, 0, 0, 5), 1e-4);
        assertTrue(ErebHandMath.inCone(0, 5, 0, 70, 6));
        assertFalse(ErebHandMath.inCone(0, 7, 0, 70, 6));   // too far
        assertFalse(ErebHandMath.inCone(4, 1, 0, 70, 6));   // outside the 35° half-angle
        assertFalse(ErebHandMath.inCone(0, -2, 0, 70, 6));   // behind
    }

    @Test
    void realAndFalse() {
        boolean[] b = ErebHandMath.pickReal(5, 3, new double[] {0.9, 0.1, 0.5, 0.3, 0.7});
        assertArrayEquals(new boolean[] {false, true, true, true, false}, b);
        int real = 0;
        for (boolean x : ErebHandMath.pickReal(6, 2, new double[] {0.4, 0.2, 0.8, 0.6, 0.1, 0.9})) if (x) real++;
        assertEquals(2, real);
        assertEquals(0, count(ErebHandMath.pickReal(3, 0, new double[] {0.1, 0.2, 0.3})));
        assertEquals(3, count(ErebHandMath.pickReal(3, 9, new double[] {0.1, 0.2, 0.3})));
        assertEquals(1, ErebHandMath.flameOwner(4, 3));
        assertEquals(-1, ErebHandMath.flameOwner(0, 0));
    }

    private static int count(boolean[] b) {
        int n = 0;
        for (boolean x : b) if (x) n++;
        return n;
    }

    @Test
    void maskAndShards() {
        assertEquals(1, ErebHandMath.maskAfterMend(1));   // mended after «Падение маски» in phase 2
        assertEquals(2, ErebHandMath.maskAfterMend(2));   // phase 3 already cracked it
        for (int t = 0; t < 400; t += 7)
            for (int i = 0; i < 6; i++) {
                double[] o = ErebHandMath.shardOrbit(i, 6, t, 10);
                assertTrue(o[1] >= 1.5 - 1e-9 && o[1] <= 3.0 + 1e-9, "shards fly 1.5–3 blocks up");
                double rr = Math.hypot(o[0], o[2]);
                assertTrue(rr >= 5.4 && rr <= 9.1);
            }
        double[] a = ErebHandMath.shardOrbit(0, 4, 0, 10), b = ErebHandMath.shardOrbit(0, 4, 1, 10);
        assertTrue(Math.hypot(a[0] - b[0], a[2] - b[2]) < 0.3, "slowly");
    }

    @Test
    void mirrorsAndWalls() {
        double[] y = ErebHandMath.mirrorYaws(4, 45);
        assertArrayEquals(new double[] {45, 135, 225, 315}, y, 1e-9);
        assertTrue(ErebHandMath.facesMirror(50, y, 24));
        assertTrue(ErebHandMath.facesMirror(-40, y, 24));   // = 320
        assertFalse(ErebHandMath.facesMirror(0, y, 24));
        assertEquals(6, ErebHandMath.ring(6, 9, 0, 0, 0).size());
        double[] q = ErebHandMath.ring(6, 9, 0, 0, 1).get(3);
        assertEquals(9, Math.hypot(q[0], q[1]), 1e-9);
        assertTrue(ErebHandMath.wallCrossed(25.5, 26.2, 26));
        assertTrue(ErebHandMath.wallCrossed(26.2, 25.5, 26));
        assertFalse(ErebHandMath.wallCrossed(20, 21, 26));
    }

    @Test
    void holdsAndOath() {
        assertEquals(0, ErebHandMath.finisherLift(0));
        assertEquals(0, ErebHandMath.finisherLift(ErebHandMath.FIN_GRAB));
        assertEquals(1, ErebHandMath.finisherLift(ErebHandMath.FIN_LIFTED), 1e-9);
        assertEquals(1, ErebHandMath.finisherLift(ErebHandMath.FINISHER), 1e-9);
        assertEquals(ErebHandMath.GIANT_FROM, ErebHandMath.giantFall(0), 1e-9);
        assertEquals(0, ErebHandMath.giantFall(ErebHandMath.HOL_FALL), 1e-9);
        assertTrue(ErebHandMath.giantFall(12) < ErebHandMath.giantFall(6));
        assertEquals(ErebHandMath.HOL_DESCEND + ErebHandMath.HOL_FALL, ErebHandMath.HOL_CATCH);
        assertTrue(ErebHandMath.grabBroken(90, 90));
        assertFalse(ErebHandMath.grabBroken(89.9, 90));
        assertEquals(10, ErebHandMath.oathShare(20, 0.5, 30), 1e-9);
        assertEquals(30, ErebHandMath.oathShare(100, 0.5, 30), 1e-9);
        assertEquals(0, ErebHandMath.oathShare(-5, 0.5, 30), 1e-9);
    }

    @Test
    void secondFour() {
        // «Пламя-подменыш»: the swap at half way, the gold flicker 0.5 s before it
        assertEquals(5, ErebHandMath.changelingSwapTick(9, 0.9));
        assertEquals(0, ErebHandMath.changelingFlickerTick(5));
        assertEquals(10, ErebHandMath.changelingFlickerTick(20));
        assertEquals(1, ErebHandMath.changelingSwapTick(0, 0.9));
        double[][] xz = {{0, 0}, {4, 0}, {2, 0}, {20, 0}};
        assertEquals(2, ErebHandMath.nearestAlly(xz, 0, 6));   // the nearest within 6
        assertEquals(3, ErebHandMath.nearestAlly(new double[][] {{0, 0}, {30, 0}, {40, 0}, {20, 0}}, 3, 6));
        assertEquals(0, ErebHandMath.nearestAlly(new double[][] {{0, 0}, {7, 0}}, 0, 6));   // none in 6: the target itself
        // «Ложный рассвет»: 60% within 6 blocks, 20% the rest
        assertEquals(0.6, ErebHandMath.dawnShare(5.9, 6, 0.6, 0.2), 1e-9);
        assertEquals(0.6, ErebHandMath.dawnShare(6, 6, 0.6, 0.2), 1e-9);
        assertEquals(0.2, ErebHandMath.dawnShare(6.1, 6, 0.6, 0.2), 1e-9);
        assertEquals(80, ErebHandMath.DAWN_INVULN);   // invulnerable 4 s (ТЗ)
        assertTrue(ErebHandMath.DAWN_WAVE > ErebHandMath.DAWN_INVULN && ErebHandMath.DAWN_WAVE <= ErebHandMath.DAWN);
        // «Отражение-предатель»: 1 hit of its original, 3 of the others
        assertEquals(1, ErebHandMath.traitorHits(true, 1, 3));
        assertEquals(3, ErebHandMath.traitorHits(false, 1, 3));
        assertEquals(1, ErebHandMath.traitorHits(false, 1, 0));
        // «Ложное отступление»: 2 s unseen, 3 blocks
        assertEquals(40, ErebHandMath.RETREAT_WINDOW);
        assertEquals(3, ErebHandMath.RETREAT_NEAR, 1e-9);
        // «Рой лжи»: 12, 6 of them real
        assertEquals(6, count(ErebHandMath.pickReal(12, 6, new double[] {.1, .9, .2, .8, .3, .7, .4, .6, .5, .05, .95, .55})));
    }

    @Test
    void spellPoolsByPhase() {
        var all = new java.util.HashSet<String>();
        for (int ph = 0; ph < 3; ph++) all.addAll(ErebHandMath.spellPool(ph));
        assertEquals(8, all.size());   // every one of the eight is used somewhere
        assertEquals(8, ErebHandMath.spellPool(2).size());   // «Глава Культа» (and the dream): all eight
        assertTrue(ErebHandMath.spellPool(0).contains("changeling_flame") && ErebHandMath.spellPool(0).contains("swarm_of_lies"));
        assertTrue(ErebHandMath.spellPool(1).contains("false_retreat") && ErebHandMath.spellPool(1).contains("traitor_reflection"));
        for (int ph = 0; ph < 3; ph++)   // a target on a «столб» can still be reached in every phase
            assertTrue(ErebHandMath.spellPool(ph).stream().anyMatch(ErebHandMath::ranged));
        assertFalse(ErebHandMath.ranged("false_retreat"));
        assertFalse(ErebHandMath.ranged("glass_grip"));
    }
}
