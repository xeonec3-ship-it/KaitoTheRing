package ru.pohsmp.core.boss.irina;

import static org.junit.jupiter.api.Assertions.*;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.Reader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

class IrinaMathTest {
    private static final Path ANIM = Path.of("src/main/resources/assets/pohsmp_core/animations/entity/irina.animation.json");

    /** Tick of an event (timeline key) of an animation of irina.animation.json, or -1. */
    private static int event(JsonObject anims, String anim, String event) {
        JsonObject a = anims.getAsJsonObject(anim);
        assertNotNull(a, anim);
        JsonObject tl = a.getAsJsonObject("timeline");
        if (tl == null) return -1;
        for (Map.Entry<String, com.google.gson.JsonElement> e : tl.entrySet())
            if (e.getValue().toString().contains("\"" + event + "\""))
                return (int) Math.round(Double.parseDouble(e.getKey()) * 20);
        return -1;
    }

    private static int length(JsonObject anims, String anim) {
        return (int) Math.round(anims.getAsJsonObject(anim).get("animation_length").getAsDouble() * 20);
    }

    @Test
    void timingsMatchTheAnimationEvents() throws Exception {
        JsonObject anims;
        try (Reader r = Files.newBufferedReader(ANIM)) {
            anims = JsonParser.parseReader(r).getAsJsonObject().getAsJsonObject("animations");
        }
        assertEquals(IrinaMath.INTRO, length(anims, "irina_spawn"));
        assertEquals(IrinaMath.INTRO_UNRAVEL, event(anims, "irina_spawn", "unravel"));
        assertEquals(IrinaMath.INTRO_POSE, event(anims, "irina_spawn", "pose"));
        assertEquals(IrinaMath.INTRO_FLOURISH, event(anims, "irina_spawn", "flourish"));
        assertEquals(IrinaMath.DEATH, length(anims, "irina_death"));
        assertEquals(IrinaMath.DEATH_KNEES, event(anims, "irina_death", "knees"));
        assertEquals(IrinaMath.DEATH_HAT, event(anims, "irina_death", "hat"));
        assertEquals(IrinaMath.DEATH_FALL, event(anims, "irina_death", "fall"));
        assertEquals(IrinaMath.DEATH_UNRAVEL, event(anims, "irina_death", "unravel"));
        assertEquals(IrinaMath.HAPPY, length(anims, "irina_others_happiness"));
        assertEquals(IrinaMath.HAPPY_SPREAD, event(anims, "irina_others_happiness", "spread"));
        assertEquals(IrinaMath.HAPPY_GATHER, event(anims, "irina_others_happiness", "gather"));
        assertEquals(IrinaMath.HAPPY_ABSORB, event(anims, "irina_others_happiness", "absorb"));
        assertEquals(IrinaMath.MINE, length(anims, "irina_only_mine"));
        assertEquals(IrinaMath.MINE_YANK, event(anims, "irina_only_mine", "yank"));
        assertEquals(IrinaMath.MINE_COCOON, event(anims, "irina_only_mine", "cocoon"));
        assertEquals(IrinaMath.MINE_CRUSH, event(anims, "irina_only_mine", "crush"));
        assertEquals(IrinaMath.FINISHER, length(anims, "irina_finisher"));
        assertEquals(IrinaMath.FINISHER_PULL, event(anims, "irina_finisher", "pull_done"));
        assertEquals(IrinaMath.FINISHER_PIERCE, event(anims, "irina_finisher", "pierce"));
        assertEquals(IrinaMath.FINISHER_WHISPER, event(anims, "irina_finisher", "whisper"));
        assertEquals(IrinaMath.FINISHER_KILL, event(anims, "irina_finisher", "kill"));
        assertEquals(IrinaMath.REPLICA_ANIM, length(anims, "irina_replica_break"));
        assertEquals(IrinaMath.REPLICA_BREAK, event(anims, "irina_replica_break", "break"));
        assertEquals(IrinaMath.REPLICA_SPEAK, event(anims, "irina_replica_break", "speak"));
        assertEquals(IrinaMath.STAFF, length(anims, "irina_staff_attack"));
        assertEquals(IrinaMath.STAFF_HIT, event(anims, "irina_staff_attack", "hit"));
        assertEquals(IrinaMath.MARK_AT, event(anims, "irina_mark", "mark"));
        assertEquals(IrinaMath.BIND_AT, event(anims, "irina_bind", "bind"));
        assertEquals(IrinaMath.WHIP_LASH - IrinaMath.WHIP_WARN, event(anims, "irina_whip", "lash"));
        assertEquals(IrinaMath.STEAL_PULL, event(anims, "irina_steal", "pull"));
        assertEquals(IrinaMath.STEAL_ABSORB, event(anims, "irina_steal", "absorb"));
        assertEquals(IrinaMath.GAZE_AT, event(anims, "irina_gaze", "gaze"));
        assertEquals(IrinaMath.KNOTS_AT, event(anims, "irina_knots", "knots"));
        assertEquals(IrinaMath.SWAP_AT, event(anims, "irina_swap", "swap"));
        assertEquals(IrinaMath.PUPPET_AT, event(anims, "irina_puppet", "puppet"));
        // the scene order of the plans
        assertTrue(IrinaMath.MINE_YANK < IrinaMath.MINE_COCOON && IrinaMath.MINE_COCOON < IrinaMath.MINE_CAM_END && IrinaMath.MINE_CAM_END < IrinaMath.MINE_CRUSH);
        assertEquals(80 - 4, IrinaMath.MINE_CRUSH - IrinaMath.MINE_COCOON);   // the cocoon fx lives 80 ticks; crush 4 s after it closes (+ yank)
        assertTrue(IrinaMath.FINISHER_CAM_FROM + IrinaMath.FINISHER_CAM <= IrinaMath.FINISHER);
    }

    @Test
    void phases() {
        assertEquals(IrinaMath.ENVY, IrinaMath.phaseAt(1.0));
        assertEquals(IrinaMath.ENVY, IrinaMath.phaseAt(0.67));
        assertEquals(IrinaMath.THREADS, IrinaMath.phaseAt(0.66));
        assertEquals(IrinaMath.THREADS, IrinaMath.phaseAt(0.34));
        assertEquals(IrinaMath.FURY, IrinaMath.phaseAt(0.33));
        assertEquals(IrinaMath.FURY, IrinaMath.phaseAt(0.0));
    }

    @Test
    void pairs() {
        List<String> four = List.of("a", "b", "c", "d");
        List<List<String>> p = IrinaMath.pairs(four, 42);
        assertEquals(2, p.size());
        Set<String> seen = new HashSet<>();
        for (List<String> pair : p) {
            assertNotEquals(pair.get(0), pair.get(1));
            assertTrue(seen.add(pair.get(0)) && seen.add(pair.get(1)));
        }
        assertEquals(new HashSet<>(four), seen);
        assertEquals(2, IrinaMath.pairs(List.of("a", "b", "c", "d", "e"), 1).size());   // odd one out
        assertTrue(IrinaMath.pairs(List.of("a"), 1).isEmpty());
        assertTrue(IrinaMath.pairs(new ArrayList<String>(), 1).isEmpty());
        assertEquals(IrinaMath.pairs(four, 7), IrinaMath.pairs(four, 7));   // seeded
    }

    @Test
    void bondsAndSplit() {
        assertEquals(0, IrinaMath.bondState(5, 12));
        assertEquals(1, IrinaMath.bondState(9, 12));
        assertEquals(1, IrinaMath.bondState(12, 12));
        assertEquals(2, IrinaMath.bondState(12.01, 12));
        float[] s = IrinaMath.split(30, 0.5);
        assertEquals(15, s[0], 1e-4);
        assertEquals(15, s[1], 1e-4);
        s = IrinaMath.split(10, 0.25);
        assertEquals(7.5, s[0], 1e-4);
        assertEquals(2.5, s[1], 1e-4);
        assertEquals(10, IrinaMath.split(10, 2)[1], 1e-4);   // clamped
    }

    @Test
    void knotsCocoonSteal() {
        assertEquals(4, IrinaMath.knotCount(1, 3, 6));
        assertEquals(4, IrinaMath.knotCount(2, 3, 6));
        assertEquals(5, IrinaMath.knotCount(4, 3, 6));
        assertEquals(6, IrinaMath.knotCount(6, 3, 6));
        assertEquals(6, IrinaMath.knotCount(12, 3, 6));
        assertEquals(60, IrinaMath.cocoonHealth(1, 40, 60));
        assertEquals(60, IrinaMath.cocoonHealth(2, 40, 60));
        assertEquals(120, IrinaMath.cocoonHealth(4, 40, 60));
        assertEquals(1, IrinaMath.stolenAmplifier(4, false, 1, 0));
        assertEquals(0, IrinaMath.stolenAmplifier(4, true, 1, 0));
        assertEquals(0, IrinaMath.stolenAmplifier(0, false, 1, 0));
    }

    @Test
    void gazeWhipPuppetMark() {
        assertEquals(0, IrinaMath.angleDeg(1, 0, 0, 5, 0, 0), 1e-6);
        assertEquals(90, IrinaMath.angleDeg(1, 0, 0, 0, 0, 3), 1e-6);
        int c = 0;
        for (int i = 0; i < 40; i++) c = IrinaMath.gazeTick(c, 10, 25);
        assertTrue(IrinaMath.gazeCaught(c, 2));
        assertEquals(0, IrinaMath.gazeTick(c, 40, 25));
        assertFalse(IrinaMath.gazeCaught(39, 2));
        assertTrue(IrinaMath.whipHits(1.5));
        assertTrue(IrinaMath.whipHits(7));
        assertFalse(IrinaMath.whipHits(0.5));
        assertFalse(IrinaMath.whipHits(8));
        assertTrue(IrinaMath.puppetBroken(185, 9020, 0.02));
        assertFalse(IrinaMath.puppetBroken(100, 9020, 0.02));
        assertEquals(5, IrinaMath.markFilter(10, true, false, 0.5), 1e-4);
        assertEquals(10, IrinaMath.markFilter(10, true, true, 0.5), 1e-4);
        assertEquals(10, IrinaMath.markFilter(10, false, false, 0.5), 1e-4);
        assertEquals(0, IrinaMath.finisherPull(0), 1e-9);
        assertEquals(1, IrinaMath.finisherPull(IrinaMath.FINISHER_PULL), 1e-9);
        assertEquals(1, IrinaMath.finisherPull(40), 1e-9);
    }
}
