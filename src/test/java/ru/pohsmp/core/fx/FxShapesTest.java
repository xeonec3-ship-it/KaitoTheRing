package ru.pohsmp.core.fx;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import ru.pohsmp.core.fx.FxMath.Vec;

/** Shapes of the line-like elements, trail memory, and the element types of docs/fx.md vs the effects shipped. No Minecraft. */
class FxShapesTest {
    private static final Path FX = Path.of("src/main/resources/assets/pohsmp_core/fx");
    private static final Vec A = new Vec(0, 64, 0), B = new Vec(10, 70, 4);

    @Test
    void lightningJoinsBothEndsAndIsDeterministic() {
        List<FxShapes.Seg> s = FxShapes.lightning(7, A, B, 0.3, 3, 5);
        List<FxShapes.Seg> main = s.stream().filter(g -> g.depth() == 0).toList();
        assertEquals(32, main.size());
        assertEquals(A, main.get(0).a());
        assertEquals(B, main.get(main.size() - 1).b());
        for (int i = 0; i + 1 < main.size(); i++) assertEquals(main.get(i).b(), main.get(i + 1).a(), "main channel is continuous");
        assertTrue(s.stream().anyMatch(g -> g.depth() == 1), "has branches");
        assertEquals(s, FxShapes.lightning(7, A, B, 0.3, 3, 5));
        assertNotEquals(s, FxShapes.lightning(8, A, B, 0.3, 3, 5));
        double d = FxShapes.len(FxShapes.sub(B, A));
        for (FxShapes.Seg g : main) assertTrue(distToLine(g.a(), A, B) < d * 0.6 + 1e-9, "stays near the line");
    }

    @Test
    void straightLightningWithoutJag() {
        for (FxShapes.Seg g : FxShapes.lightning(1, A, B, 0, 0, 3)) assertTrue(distToLine(g.a(), A, B) < 1e-9);
    }

    @Test
    void slashArcRadiusBendAndDirection() {
        Vec c = new Vec(0, 0, 0), u = new Vec(1, 0, 0), v = new Vec(0, 0, 1);
        List<Vec> arc = FxShapes.slashArc(c, u, v, 3, 120, 1, 12, 1);
        assertEquals(13, arc.size());
        for (Vec p : arc) assertEquals(3, FxShapes.len(p), 1e-9);
        assertTrue(arc.get(0).x() < 0 && arc.get(12).x() > 0, "sweeps from -u to +u");
        assertEquals(3, arc.get(6).z(), 1e-9);
        List<Vec> back = FxShapes.slashArc(c, u, v, 3, 120, 1, 12, -1);
        assertTrue(back.get(0).x() > 0, "dir -1 sweeps the other way");
        List<Vec> chord = FxShapes.slashArc(c, u, v, 3, 120, 0, 12, 1);
        for (Vec p : chord) assertEquals(chord.get(0).z(), p.z(), 1e-9);  // bend 0 = straight chord
    }

    @Test
    void slashSpanGrowsThenCloses() {
        double[] s0 = FxShapes.slashSpan(0, 4, 10), s1 = FxShapes.slashSpan(4, 4, 10), s2 = FxShapes.slashSpan(10, 4, 10);
        assertEquals(0, s0[1], 1e-9);
        assertEquals(1, s1[1], 1e-9);
        assertTrue(s1[0] < 0.5, "tail lags behind the head");
        assertEquals(1, s2[0], 1e-9);
        for (double t = 0; t <= 12; t += 0.5) {
            double[] s = FxShapes.slashSpan(t, 4, 10);
            assertTrue(s[0] <= s[1] && s[0] >= 0 && s[1] <= 1);
        }
    }

    @Test
    void chainSagsAtTheMiddleAndTensionStraightens() {
        Vec a = new Vec(0, 10, 0), b = new Vec(8, 10, 0);
        List<Vec> c = FxShapes.chain(a, b, 1.5, 0, 8);
        assertEquals(a, c.get(0));
        assertEquals(b, c.get(8));
        assertEquals(8.5, c.get(4).y(), 1e-9);
        for (Vec p : FxShapes.chain(a, b, 1.5, 1, 8)) assertEquals(10, p.y(), 1e-9);
    }

    @Test
    void spiralFunnelsAndArmsAreSpread() {
        Vec base = new Vec(0, 0, 0);
        Vec bottom = FxShapes.spiral(base, 2, 3, 0.25, 1, 0, 3, 0, 0), top = FxShapes.spiral(base, 2, 3, 0.25, 1, 0, 3, 1, 0);
        assertEquals(0.5, Math.hypot(bottom.x(), bottom.z()), 1e-9);
        assertEquals(2, Math.hypot(top.x(), top.z()), 1e-9);
        assertEquals(3, top.y(), 1e-9);
        Vec arm1 = FxShapes.spiral(base, 2, 3, 0.25, 1, 1, 3, 0, 0);
        assertEquals(120, Math.toDegrees(Math.atan2(arm1.z(), arm1.x())), 1e-6);
        assertTrue(FxShapes.pull(0.8, 1) < 1 && FxShapes.pull(-0.5, 1) > 1 && FxShapes.pull(2, 1) == 0);
    }

    @Test
    void flapPulseAndFlashEnvelope() {
        assertEquals(0, FxShapes.flap(0, 12, 40), 1e-9);
        assertEquals(12, FxShapes.flap(10, 12, 40), 1e-9);
        assertEquals(0, FxShapes.flap(10, 12, 0), 1e-9);
        assertEquals(1, FxShapes.pulse(5, 0.3, 0), 1e-9);
        assertEquals(1.3, FxShapes.pulse(5, 0.3, 20), 1e-9);
        assertEquals(1, FxShapes.flash(0.18, 0.18), 1e-9);
        assertEquals(0, FxShapes.flash(1, 0.18), 1e-9);
        assertTrue(FxShapes.flash(0.05, 0.18) > 0.5 && FxShapes.flash(0.6, 0.18) < FxShapes.flash(0.3, 0.18));
    }

    @Test
    void trailKeepsOnlyRecentMovement() {
        FxTrail t = new FxTrail(10, 0.05);
        for (int i = 0; i <= 30; i++) t.add(i, new Vec(i * 0.5, 0, 0));
        List<FxTrail.Sample> s = t.samples();
        assertEquals(30, s.get(0).time(), 1e-9);
        assertTrue(s.get(s.size() - 1).time() >= 19, "older than length is dropped");
        assertEquals(0, t.age(s.get(0), 30), 1e-9);
        for (int i = 31; i < 60; i++) t.add(i, new Vec(15, 0, 0));   // stands still
        assertTrue(t.size() <= 3, "a resting point does not pile up samples");
        t.add(5, new Vec(0, 0, 0));                                  // time went back
        assertEquals(1, t.size());
    }

    @Test
    void docTableTypesAreAllDrawnAndShippedEffectsUseKnownTypes() throws IOException {
        String doc = Files.readString(Path.of("docs/fx.md"), StandardCharsets.UTF_8);
        Set<String> inDoc = new TreeSet<>();
        Matcher m = Pattern.compile("(?m)^\\| `([a-z_]+)`(?: / `([a-z_]+)`)? \\|").matcher(doc.substring(doc.indexOf("## Типы элементов"), doc.indexOf("## Код")));
        while (m.find()) {
            inDoc.add(m.group(1));
            if (m.group(2) != null) inDoc.add(m.group(2));
        }
        assertTrue(inDoc.containsAll(Set.of("slash", "lightning", "halo", "chains")), inDoc.toString());
        for (String t : inDoc) assertTrue(FxDef.TYPES.contains(t), "drawn: " + t);
        try (Stream<Path> files = Files.list(FX)) {
            for (Path p : files.filter(f -> f.toString().endsWith(".json")).toList()) {
                String id = p.getFileName().toString().replace(".json", "");
                FxDef d = FxDef.parse(id, Files.readString(p, StandardCharsets.UTF_8));
                for (FxDef.Element e : d.elements()) assertTrue(FxDef.TYPES.contains(e.type()), id + ": " + e.type());
            }
        }
    }

    @Test
    void demoEffectsParse() throws IOException {
        FxDef slash = FxDef.parse("scarlet_slash", Files.readString(FX.resolve("scarlet_slash.json"), StandardCharsets.UTF_8));
        assertEquals("higher", slash.style());
        assertTrue(slash.elements().stream().filter(e -> e.type().equals("slash")).count() >= 2);
        assertTrue(slash.elements().stream().anyMatch(e -> e.type().equals("decal") && e.str("texture", "").equals("slash_crack")));
        FxDef pulse = FxDef.parse("deep_pulse", Files.readString(FX.resolve("deep_pulse.json"), StandardCharsets.UTF_8));
        assertEquals("sculk", pulse.style());
        assertTrue(pulse.elements().stream().filter(e -> e.type().equals("wave")).count() >= 4);
        for (String tex : List.of("strip_soft", "chain_link", "wing", "aura_shell", "sound_ring", "slash_crack"))
            assertTrue(Files.exists(Path.of("src/main/resources/assets/pohsmp_core/textures/fx/" + tex + ".png")), tex);
    }

    private static double distToLine(Vec p, Vec a, Vec b) {
        Vec d = FxShapes.norm(FxShapes.sub(b, a));
        return FxShapes.len(FxShapes.cross(FxShapes.sub(p, a), d));
    }
}
