package ru.pohsmp.core.boss.aris;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.Reader;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class ArisMathTest {
    private static final Path ASSETS = Path.of("src/main/resources/assets/pohsmp_core");

    /** Every animation the code triggers exists in aris.animation.json and its length matches ANIM_TICKS. */
    @Test
    void animationsMatchFile() throws Exception {
        JsonObject anims;
        try (Reader r = Files.newBufferedReader(ASSETS.resolve("animations/entity/aris.animation.json"))) {
            anims = JsonParser.parseReader(r).getAsJsonObject().getAsJsonObject("animations");
        }
        for (int i = 1; i < ArisMath.ANIMS.length; i++) {
            JsonObject a = anims.getAsJsonObject("animation.aris." + ArisMath.ANIMS[i]);
            if (a == null && ArisMath.PENDING.contains(ArisMath.ANIMS[i])) continue;   // not delivered yet
            assertTrue(a != null, ArisMath.ANIMS[i]);
            assertEquals(Math.round(a.get("animation_length").getAsDouble() * 20), ArisMath.ANIM_TICKS[i], ArisMath.ANIMS[i]);
        }
        assertTrue(anims.has("animation.aris.npc_sit"));
        assertTrue(anims.has("animation.aris.idle") && anims.has("animation.aris.walk"));
    }

    /** Timings agree with the animation events (timeline) — the code fires them by ticks, the file does not drive it. */
    @Test
    void eventsMatchTimeline() throws Exception {
        JsonObject anims;
        try (Reader r = Files.newBufferedReader(ASSETS.resolve("animations/entity/aris.animation.json"))) {
            anims = JsonParser.parseReader(r).getAsJsonObject().getAsJsonObject("animations");
        }
        assertEvent(anims, "slam", "impact", ArisMath.SLAM_IMPACT);
        assertEvent(anims, "swing", "hit", ArisMath.SWING_HIT);
        assertEvent(anims, "cast", "cast", ArisMath.CAST_AT);
        assertEvent(anims, "forge", "ignite", ArisMath.FORGE_IGNITE);
        assertEvent(anims, "last_blow", "blow", ArisMath.LAST_BLOW);
        assertEvent(anims, "last_blow", "peak", ArisMath.LAST_PEAK);
        assertEvent(anims, "phase2", "roar", ArisMath.PHASE2_ROAR);
        assertEvent(anims, "phase3", "ignite", ArisMath.PHASE3_IGNITE);
        assertEvent(anims, "spawn", "impact", ArisMath.INTRO_IMPACT);
        assertEvent(anims, "spawn", "horns", ArisMath.INTRO_HORNS);
        assertEvent(anims, "spawn", "kneel", ArisMath.INTRO_DIM);
        assertEvent(anims, "surrender", "hammer_drop", ArisMath.SURRENDER_HAMMER_DROP);
        assertEvent(anims, "surrender", "speak", ArisMath.SURRENDER_SPEAK);
        assertEvent(anims, "billet", "throw", ArisMath.BILLET_THROW);
        assertEvent(anims, "chains", "chains", ArisMath.CHAINS_AT);
        assertEvent(anims, "quench", "splash", ArisMath.QUENCH_SPLASH);
        assertEvent(anims, "bellows", "gust", ArisMath.BELLOWS_GUST);
        assertEvent(anims, "replica_break", "break", ArisMath.REPLICA_BREAK);
        assertEvent(anims, "replica_break", "speak", ArisMath.REPLICA_SPEAK);
        // the forge fx starts 0.3 s in, so its floor (tick 60) meets ignite
        assertEquals(ArisMath.FORGE_IGNITE, ArisMath.FORGE_FX + ArisMath.FORGE_FLOOR_FROM);
    }

    private static void assertEvent(JsonObject anims, String anim, String event, int tick) {
        JsonObject tl = anims.getAsJsonObject("animation.aris." + anim).getAsJsonObject("timeline");
        boolean found = false;
        for (var e : tl.entrySet()) {
            String v = e.getValue().isJsonArray() ? e.getValue().getAsJsonArray().toString() : e.getValue().getAsString();
            if (v.contains(event) && Math.abs(Double.parseDouble(e.getKey()) * 20 - tick) <= 1) found = true;
        }
        assertTrue(found, anim + "." + event + " at tick " + tick);
    }

    @Test
    void finisherTimings() {
        assertTrue(ArisMath.FINISHER_PULL < ArisMath.FINISHER_SLAM && ArisMath.FINISHER_SLAM < ArisMath.FINISHER_KILL);
        assertTrue(ArisMath.FINISHER_KILL < ArisMath.FINISHER && ArisMath.FINISHER_CAM_FROM + ArisMath.FINISHER_CAM <= ArisMath.FINISHER);
        assertEquals(0, ArisMath.finisherPull(0), 1e-9);
        assertEquals(1, ArisMath.finisherPull(ArisMath.FINISHER_PULL), 1e-9);
        assertTrue(Files.exists(Path.of("src/main/resources/data/pohsmp_core/damage_type/aris_finisher.json")));
    }

    @Test
    void slamRing() {
        assertEquals(0, ArisMath.slamRadius(0), 1e-9);
        assertEquals(8, ArisMath.slamRadius(22), 1e-9);
        assertTrue(ArisMath.slamHits(4, 11, 0));
        assertFalse(ArisMath.slamHits(4, 11, 1.5));   // jumped over
        assertFalse(ArisMath.slamHits(6, 11, 0));
        assertFalse(ArisMath.slamHits(8, 23, 0));
    }

    @Test
    void metalWave() {
        assertEquals(1, ArisMath.crestAt(0));
        assertEquals(0, ArisMath.crestAt(1));
        assertEquals(5, ArisMath.crestAt(8));
        assertEquals(0, ArisMath.crestAt(10));
        assertTrue(ArisMath.crestHits(3, 6.3, 1.2));
        assertFalse(ArisMath.crestHits(3, 6.3, 1.8));
        assertFalse(ArisMath.crestHits(3, 8.5, 0));
    }

    @Test
    void forgeIslands() {
        assertEquals(4, ArisMath.islandCount(1, 4, 6));
        assertEquals(4, ArisMath.islandCount(4, 4, 6));
        assertEquals(5, ArisMath.islandCount(5, 4, 6));
        assertEquals(6, ArisMath.islandCount(8, 4, 6));
        double[][] o = ArisMath.islandOffsets(5, 0.3, 24);
        for (int i = 0; i < 5; i++) {
            double r = Math.hypot(o[i][0], o[i][1]);
            assertTrue(r >= 8.9 && r <= 15.1);
            for (int j = 0; j < i; j++) assertTrue(Math.hypot(o[i][0] - o[j][0], o[i][1] - o[j][1]) > 2 * ArisMath.ISLAND_R);
        }
    }

    @Test
    void lastBlow() {
        assertEquals(75, ArisMath.lastBlowDamage(0, 14, 75, 30), 1e-9);
        assertEquals(30, ArisMath.lastBlowDamage(14, 14, 75, 30), 1e-9);
        assertEquals(52.5, ArisMath.lastBlowDamage(7, 14, 75, 30), 1e-9);
        assertEquals(0, ArisMath.lastBlowDamage(14.1, 14, 75, 30), 1e-9);
    }

    @Test
    void cone() {
        // yaw 0 looks to +z
        assertTrue(ArisMath.inCone(0, 5, 0, 30, 8));
        assertTrue(ArisMath.inCone(2, 5, 0, 30, 8));
        assertFalse(ArisMath.inCone(4, 4, 0, 30, 8));
        assertFalse(ArisMath.inCone(0, -5, 0, 30, 8));
        assertFalse(ArisMath.inCone(0, 9, 0, 30, 8));
        // yaw 90 looks to −x
        assertTrue(ArisMath.inCone(-5, 0, 90, 30, 8));
    }

    @Test
    void cover() {
        assertTrue(ArisMath.segmentHitsBox(0, 0, 10, 0, 5, 0, 1.3, 0.6));
        assertFalse(ArisMath.segmentHitsBox(0, 0, 10, 0, 5, 2, 1.3, 0.6));
        assertFalse(ArisMath.segmentHitsBox(0, 0, 3, 0, 5, 0, 1.3, 0.6));
    }

    @Test
    void textures() {
        assertEquals(ArisMath.TEX_SPENT, ArisMath.introTexture(0));
        assertEquals(ArisMath.TEX_DIM, ArisMath.introTexture(100));
        assertEquals(ArisMath.TEX_BASE, ArisMath.introTexture(130));
        assertEquals(ArisMath.TEX_MYTHIC, ArisMath.surrenderTexture(10, ArisMath.TEX_MYTHIC));
        assertEquals(ArisMath.TEX_BASE, ArisMath.surrenderTexture(30, ArisMath.TEX_MYTHIC));
        assertEquals(ArisMath.TEX_DIM, ArisMath.surrenderTexture(41, ArisMath.TEX_MYTHIC));
        assertEquals(ArisMath.TEX_SPENT, ArisMath.surrenderTexture(60, ArisMath.TEX_MYTHIC));
        for (int s = 0; s < 4; s++)
            assertTrue(Files.exists(ASSETS.resolve("textures/entity/aris/" + ArisMath.texture(s) + "_glowmask.png")));
    }

    @Test
    void billetArc() {
        double[] a = {0, 64, 0}, b = {10, 64, 0};
        assertEquals(0, ArisMath.billetArc(a, b, 0, 10)[0], 1e-9);
        assertEquals(67, ArisMath.billetArc(a, b, 5, 10)[1], 1e-9);
        assertEquals(64, ArisMath.billetArc(a, b, 10, 10)[1], 1e-9);
    }

    /** Every fx the code plays exists. */
    @Test
    void fxExist() {
        for (String f : new String[] {"aris_intro", "aris_slam", "aris_metal_wave", "aris_anvil_rise", "aris_anvil_break", "aris_blade_sword",
                "aris_blade_glaive", "aris_blade_shatter", "aris_blade_strike", "aris_blades_forge", "aris_phase2", "aris_phase3",
                "aris_mythic_aura", "aris_reforge", "aris_reforge_hit", "aris_forge", "aris_island", "aris_forge_burn", "aris_last_blow",
                "aris_surrender", "aris_billet_throw", "aris_billet", "aris_billet_explode", "aris_chains", "aris_chains_hit",
                "aris_chains_break", "aris_quench", "aris_bellows_warn", "aris_bellows", "aris_bellows_burn", "aris_replica_break"})
            assertTrue(Files.exists(ASSETS.resolve("fx/" + f + ".json")), f);
    }
}
