package ru.pohsmp.core.fx.sigil;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import ru.pohsmp.core.fx.sigil.SigilDef.Cracks;
import ru.pohsmp.core.fx.sigil.SigilDef.DissolveMode;

/** T09: the "cracks" dissolve follows docs/sigils.md "Распад трещинами". Runs without Minecraft. */
class SigilCracksTest {
    private static final int SEED = 12345;

    private static SigilDef blades() throws Exception {
        return SigilDef.parse("higher_blades", Files.readString(Path.of("src/main/resources/assets/pohsmp_core/sigils/higher_blades.json")));
    }

    private static SigilDef plain(String dissolve) {
        return SigilDef.parse("t", "{\"size\":2,\"layers\":[{\"type\":\"disc\",\"radius\":1,\"rotation\":{\"speed\":40}}],\"dissolve\":" + dissolve + "}");
    }

    @Test
    void modeAndParametersAreRead() throws Exception {
        assertNull(plain("{\"modes\":[\"fade\"]}").dissolve().cracksOrNull());
        assertEquals(Cracks.DEFAULT, plain("{\"modes\":[\"cracks\"]}").dissolve().cracksOrNull());
        Cracks c = plain("{\"modes\":[\"cracks\"],\"duration\":30,\"cracks\":{\"count\":2,\"rings\":9,\"jag\":3,\"color\":\"#FFEEAA\"}}").dissolve().cracksOrNull();
        assertEquals(3, c.count());                                    // at least 3
        assertEquals(3, c.rings());                                    // at most 3
        assertEquals(0.45, c.jag(), 1e-12);
        assertEquals(0xFFEEAA, c.color());
        SigilDef b = blades();
        assertTrue(b.dissolve().modes().contains(DissolveMode.CRACKS));
        assertNotNull(b.dissolve().cracksOrNull());
    }

    @Test
    void cracksDoNotCrossAndCoverTheCircle() throws Exception {
        for (SigilDef def : new SigilDef[] {blades(), plain("{\"modes\":[\"cracks\"],\"cracks\":{\"irregular\":0.8,\"jag\":0.45,\"count\":14}}")}) {
            Cracks c = def.dissolve().cracksOrNull();
            double reach = def.reach();
            for (int seed : new int[] {0, 1, SEED, -77})
                for (int k = 0; k < c.count(); k++)
                    for (double r = 0; r <= reach; r += reach / 37) {
                        double a = SigilCracks.crackAngle(c, seed, k, r, reach), b = SigilCracks.crackAngle(c, seed, k + 1, r, reach);
                        assertTrue(b > a, "crack " + k + " at r=" + r);
                        assertTrue(b - a < 360.0 / c.count() * 2.2);
                    }
            // crack `count` is crack 0 one turn later
            assertEquals(SigilCracks.crackAngle(c, SEED, 0, 0.7, reach) + 360, SigilCracks.crackAngle(c, SEED, c.count(), 0.7, reach), 1e-9);
            assertEquals(0, SigilCracks.ringRadius(c, 0, reach), 1e-12);
            assertEquals(reach, SigilCracks.ringRadius(c, c.rings() + 1, reach), 1e-12);
        }
    }

    @Test
    void cracksRunThenShardsFallAndGoOut() throws Exception {
        SigilDef def = blades();
        Cracks c = def.dissolve().cracksOrNull();
        int dur = def.dissolve().duration();
        double stop = 200, ct = c.crackTime() * dur;
        // before the stop: nothing
        assertEquals(0, SigilCracks.crackReach(def, 0, 150, Double.NaN), 1e-12);
        assertFalse(SigilCracks.breaking(def, 150, Double.NaN));
        assertTrue(SigilCracks.breaking(def, stop, stop));
        // all radial and ring cracks are complete by the end of crackTime
        for (int k = 0; k < c.count(); k++) {
            assertEquals(0, SigilCracks.crackReach(def, k, stop, stop), 1e-12);
            assertEquals(1, SigilCracks.crackReach(def, k, stop + ct, stop), 1e-9);
        }
        for (int j = 1; j <= c.rings(); j++) assertEquals(1, SigilCracks.ringCrack(def, j, stop + ct, stop), 1e-9);
        // shards hold still while cracking (only part a little), then each falls in its own window and is gone by the end
        for (int k = 0; k < c.count(); k++)
            for (int j = 0; j <= c.rings(); j++) {
                var still = SigilCracks.shard(def, SEED, k, j, stop + ct * 0.5, stop);
                assertEquals(1, still.alpha(), 1e-12);
                assertEquals(0, still.drop(), 1e-12);
                assertTrue(still.radial() <= c.gap() + 1e-12);
                double start = SigilCracks.fallStart(def, c, k, j);
                assertTrue(start >= ct - 1e-9 && start <= dur - c.fallTime() * dur + 1e-9);
                var mid = SigilCracks.shard(def, SEED, k, j, stop + start + c.fallTime() * dur * 0.8, stop);
                assertTrue(mid.drop() > 0, "falls");
                assertTrue(mid.alpha() < 1 && mid.alpha() > 0);
                assertEquals(0, SigilCracks.shard(def, SEED, k, j, stop + dur, stop).alpha(), 1e-9);
            }
        // the outer ring goes first
        assertTrue(SigilCracks.fallStart(def, c, 0, c.rings()) < SigilCracks.fallStart(def, c, 0, 0));
        // the crack glow rises, then dies out
        assertTrue(SigilCracks.crackGlow(def, stop + ct, stop) > 0.5 * c.glow());
        assertEquals(0, SigilCracks.crackGlow(def, stop + dur, stop), 1e-9);
        assertTrue(SigilTimeline.finished(def, stop + dur, stop));
    }

    @Test
    void shardsHopUpBeforeFalling() throws Exception {
        SigilDef def = blades();
        Cracks c = def.dissolve().cracksOrNull();
        double stop = 0, start = SigilCracks.fallStart(def, c, 2, 0), ft = c.fallTime() * def.dissolve().duration();
        assertTrue(SigilCracks.shard(def, SEED, 2, 0, stop + start + ft * 0.1, stop).drop() < 0);
        assertTrue(SigilCracks.shard(def, SEED, 2, 0, stop + start + ft * 0.95, stop).drop() > 0.3);
    }

    @Test
    void shardAtFindsTheShardOfAPoint() throws Exception {
        SigilDef def = blades();
        Cracks c = def.dissolve().cracksOrNull();
        double reach = def.reach();
        for (int k = 0; k < c.count(); k++)
            for (int j = 0; j <= c.rings(); j++) {
                var s = SigilCracks.shard(def, SEED, k, j, 0, Double.NaN);
                double a = Math.toRadians(s.centerAngle());
                assertEquals(k * (c.rings() + 1) + j, SigilCracks.shardAt(def, SEED, Math.cos(a) * s.centerRadius(), Math.sin(a) * s.centerRadius()));
            }
        assertTrue(SigilCracks.shardAt(def, SEED, reach * 2, 0) < SigilCracks.shardCount(c));
    }

    @Test
    void dustTricklesFromTheCracks() throws Exception {
        SigilDef def = blades();
        Cracks c = def.dissolve().cracksOrNull();
        double stop = 0;
        int seen = 0;
        for (int i = 0; i < c.dust(); i++)
            for (double t = 0; t <= def.dissolve().duration() + 20; t += 1) {
                var m = SigilCracks.dust(def, SEED, i, t, stop);
                if (m.alpha() <= 0) continue;
                seen++;
                assertTrue(m.radius() <= def.reach() + 0.1);
                assertTrue(m.drop() >= 0);
            }
        assertTrue(seen > c.dust() * 5);
    }

    @Test
    void layersStopTurningWhenTheSigilBreaks() {
        SigilDef def = plain("{\"modes\":[\"cracks\"],\"duration\":30}");
        double stop = 100;
        double atStop = SigilTimeline.layer(def, 0, stop, stop).angle();
        assertEquals(atStop, SigilTimeline.layer(def, 0, stop + 20, stop).angle(), 1e-9);
        assertEquals(1, SigilTimeline.layer(def, 0, stop + 20, stop).alpha(), 1e-9);  // shards carry the fade, not the layer
        assertEquals(def.size(), SigilTimeline.globalScale(def, stop + 20, stop, 1), 1e-9);
    }
}
