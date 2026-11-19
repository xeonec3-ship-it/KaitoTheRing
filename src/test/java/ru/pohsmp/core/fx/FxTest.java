package ru.pohsmp.core.fx;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import ru.pohsmp.core.fx.FxMath.Vec;
import ru.pohsmp.core.fx.sigil.SigilDef;

/** Effect parsing, style references, anchors and placement math. Runs without Minecraft. */
class FxTest {
    private static final Path FX = Path.of("src/main/resources/assets/pohsmp_core/fx");

    private static String read(Path p) throws IOException {
        return Files.readString(p, StandardCharsets.UTF_8);
    }

    private static FxDef.Context ctx(double yaw) {
        Vec c = new Vec(10, 64, 20);
        return new FxDef.Context(c, c.add(new Vec(0, 1.62, 0)), c.add(new Vec(0, 1.2, 0)), yaw, new Vec(15, 64, 25), null,
                Map.of("rift", new Vec(0, 70, 0)), 1, 7L);
    }

    @Test
    void stylesParseAndResolveReferences() throws IOException {
        for (String s : List.of("divine", "higher", "sculk", "coven", "forbidden")) {
            FxStyle st = FxStyle.parse(s, read(FX.resolve("styles/" + s + ".json")));
            assertTrue(st.palette().containsKey("primary"), s);
        }
        FxStyle divine = FxStyle.parse("divine", read(FX.resolve("styles/divine.json")));
        FxStyle higher = FxStyle.parse("higher", read(FX.resolve("styles/higher.json")));
        assertEquals(0xFFD36B, divine.color("@primary"));
        assertEquals(0xFF2A3A, higher.color("@primary"));
        assertEquals(0x123456, divine.color("#123456"));
        assertEquals("feather", divine.texture("@shards"));
        assertEquals("shard", higher.texture("@shards"));
        assertEquals("glow", divine.texture("glow"));
        assertTrue(divine.additive());
        assertTrue(!FxStyle.parse("sculk", read(FX.resolve("styles/sculk.json"))).additive());
    }

    @Test
    void demoEffectParses() throws IOException {
        FxDef fx = FxDef.parse("light_rain", read(FX.resolve("light_rain.json")));
        assertEquals("divine", fx.style());
        assertEquals(220, fx.duration());
        FxDef.Element rain = fx.elements().stream().filter(e -> e.type().equals("beam_rain")).findFirst().orElseThrow();
        assertEquals(72, rain.delay());
        assertEquals(36, (int) rain.num("count", 0));
        assertEquals("golden_halo", rain.str("impact", null));
        assertTrue(rain.activeAt(100));
        assertTrue(!rain.activeAt(300));
    }

    @Test
    void everyEffectParsesAndGatePlaceholdersUseExistingSigils() throws IOException {
        Path sigils = Path.of("src/main/resources/assets/pohsmp_core/sigils");
        try (var files = Files.list(FX)) {
            for (Path p : files.filter(f -> f.toString().endsWith(".json")).toList()) {
                String id = p.getFileName().toString().replace(".json", "");
                FxDef fx = FxDef.parse(id, read(p));
                assertTrue(!fx.elements().isEmpty(), id);
                for (FxDef.Element e : fx.elements()) {
                    e.at().resolve(ctx(0));
                    if (id.startsWith("silent_gate") && e.type().equals("sigil"))
                        assertTrue(Files.exists(sigils.resolve(e.str("id", "") + ".json")), id + ": " + e.str("id", ""));
                }
            }
        }
        FxDef gate = FxDef.parse("silent_gate_placeholder", read(FX.resolve("silent_gate_placeholder.json")));
        assertEquals(1300, gate.duration());
    }

    @Test
    void anchorsParseWithOffsets() {
        FxDef.Anchor a = FxDef.Anchor.parse("caster+0,9,0");
        assertEquals("caster", a.kind());
        assertEquals(9, a.oy(), 1e-9);
        FxDef.Anchor p = FxDef.Anchor.parse("point:rift+1,2,3");
        assertEquals("point", p.kind());
        assertEquals("rift", p.arg());
        assertEquals(3, p.oz(), 1e-9);
        assertEquals("look", FxDef.Anchor.parse("look:24").kind());
    }

    @Test
    void offsetsAreInViewAxes() {
        // yaw 0 looks along +Z: "forward 2" is +Z, "right 1" is -X
        Vec p = FxDef.Anchor.parse("caster+1,0,2").resolve(ctx(0));
        assertEquals(new Vec(9, 64, 22), round(p));
        // yaw 90 looks along -X: forward 2 -> x - 2, right 1 -> z - 1
        Vec q = FxDef.Anchor.parse("caster+1,0,2").resolve(ctx(90));
        assertEquals(new Vec(8, 64, 19), round(q));
        assertEquals(new Vec(0, 70, 0), round(FxDef.Anchor.parse("point:rift").resolve(ctx(0))));
        Vec look = FxDef.Anchor.parse("look:10").resolve(ctx(0));
        assertEquals(30, look.z(), 1e-9);
    }

    @Test
    void childArcSitsBehindTheCasterSymmetrically() {
        SigilDef.Arc arc = new SigilDef.Arc(6, 1.5, 150, 1.55, true, 3);
        Vec c = new Vec(0, 0, 0);
        List<FxMath.Placed> ps = FxMath.arc(arc, c, 0);
        assertEquals(6, ps.size());
        for (FxMath.Placed p : ps) {
            assertTrue(p.pos().z() < 0, "behind: caster looks along +Z");
            assertEquals(1.5, Math.hypot(p.pos().x(), p.pos().z()), 1e-9);
        }
        assertEquals(-ps.get(0).pos().x(), ps.get(5).pos().x(), 1e-9);
        assertEquals(15, ps.get(5).delay());
    }

    @Test
    void beamRainIsDeterministicAndInsideTheArea() {
        Vec c = new Vec(100, 64, -50);
        List<FxMath.Strike> a = FxMath.beamRain(42, c, 14, 36, 3), b = FxMath.beamRain(42, c, 14, 36, 3);
        assertEquals(a, b);
        assertNotEquals(a, FxMath.beamRain(43, c, 14, 36, 3));
        for (FxMath.Strike s : a) assertTrue(Math.hypot(s.x() - c.x(), s.z() - c.z()) <= 14 + 1e-9);
        assertEquals(35 * 3, a.get(35).tick());
    }

    private static Vec round(Vec v) {
        return new Vec(Math.round(v.x() * 1e6) / 1e6, Math.round(v.y() * 1e6) / 1e6, Math.round(v.z() * 1e6) / 1e6);
    }
}
