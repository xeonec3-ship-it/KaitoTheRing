package ru.pohsmp.core.fx.sigil;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

/** groundLight / blockGlow flags (T10): parsing, defaults, fade-out profile and strength over time. */
class SigilLightTest {
    private static final Path DIR = Path.of("src/main/resources/assets/pohsmp_core/sigils");
    private static final double E = 1e-9;

    private static SigilDef load(String id) throws IOException {
        return SigilDef.parse(id, Files.readString(DIR.resolve(id + ".json"), StandardCharsets.UTF_8));
    }

    private static SigilDef json(String extra) {
        return SigilDef.parse("t", "{\"size\":2,\"layers\":[{\"type\":\"disc\",\"appear\":{\"delay\":0,\"duration\":10}}]" + extra + "}");
    }

    @Test
    void offUnlessAsked() {
        SigilDef d = json("");
        assertNull(d.groundLight());
        assertNull(d.blockGlow());
        d = json(",\"groundLight\":false,\"blockGlow\":null");
        assertNull(d.groundLight());
        assertNull(d.blockGlow());
    }

    @Test
    void trueOrEmptyObjectMeansDefaults() {
        SigilDef d = json(",\"groundLight\":true,\"blockGlow\":{}");
        assertEquals(SigilDef.GroundLight.DEFAULT, d.groundLight());
        assertEquals(SigilDef.BlockGlow.DEFAULT, d.blockGlow());
    }

    @Test
    void fieldsAreRead() {
        SigilDef d = json(",\"groundLight\":{\"radius\":0.5,\"strength\":0.9,\"reach\":12},"
                + "\"blockGlow\":{\"radius\":2,\"strength\":0.4,\"falloff\":1,\"reach\":20}");
        assertEquals(new SigilDef.GroundLight(0.5, 0.9, 12), d.groundLight());
        assertEquals(new SigilDef.BlockGlow(2, 0.4, 1, 20), d.blockGlow());
        // partial object: the rest from defaults; nonsense clamped
        d = json(",\"groundLight\":{\"strength\":-1},\"blockGlow\":{\"radius\":0,\"reach\":0}");
        assertEquals(new SigilDef.GroundLight(SigilDef.GroundLight.DEFAULT.radius(), 0, SigilDef.GroundLight.DEFAULT.reach()), d.groundLight());
        assertEquals(0.01, d.blockGlow().radius(), E);
        assertEquals(1, d.blockGlow().reach(), E);
    }

    @Test
    void blockGlowFadesToTheEdge() {
        SigilDef.BlockGlow lin = new SigilDef.BlockGlow(1, 0.4, 1, 32);
        assertEquals(0.4, lin.at(0), E);
        assertEquals(0.2, lin.at(0.5), E);
        assertEquals(0, lin.at(1), E);
        assertEquals(0, lin.at(3), E);
        SigilDef.BlockGlow soft = new SigilDef.BlockGlow(1, 0.4, 2, 32);
        assertEquals(0.1, soft.at(0.5), E);
        double prev = Double.MAX_VALUE;
        for (double x = 0; x <= 1; x += 0.05) {
            double v = SigilDef.BlockGlow.DEFAULT.at(x);
            assertTrue(v <= prev + E, "monotone at " + x);
            prev = v;
        }
    }

    @Test
    void lightRisesWithLayersAndDiesWithDissolve() {
        SigilDef d = json(",\"groundLight\":true,\"dissolve\":{\"mode\":\"fade\",\"duration\":20}");
        double run = Double.NaN;
        assertEquals(0, SigilTimeline.lightLevel(d, -1, run), E);
        assertEquals(0, SigilTimeline.lightLevel(d, 0, run), E);
        assertEquals(0.5, SigilTimeline.lightLevel(d, 5, run), E);   // layersEnd = 10
        assertEquals(1, SigilTimeline.lightLevel(d, 10, run), E);
        assertEquals(1, SigilTimeline.lightLevel(d, 500, run), E);
        assertEquals(0.5, SigilTimeline.lightLevel(d, 110, 100), E);
        assertEquals(0, SigilTimeline.lightLevel(d, 120, 100), E);
    }

    @Test
    void enabledOnTheBigSigils() throws IOException {
        for (String id : new String[] {"silent_gate_sky", "disintegration_field"}) {
            SigilDef d = load(id);
            assertNotNull(d.groundLight(), id);
            assertNotNull(d.blockGlow(), id);
            assertTrue(d.blockGlow().radius() >= d.groundLight().radius(), id + ": block glow reaches past the spot");
        }
        assertNull(load("golden_halo").groundLight());
    }
}
