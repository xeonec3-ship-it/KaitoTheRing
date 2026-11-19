package ru.pohsmp.core.fx.sigil;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import ru.pohsmp.core.fx.sigil.SigilDef.DissolveMode;
import ru.pohsmp.core.fx.sigil.SigilDef.Orientation;

/** The demo sigils parse and behave as docs/sigils.md says. Runs without Minecraft. */
class SigilTimelineTest {
    private static final Path DIR = Path.of("src/main/resources/assets/pohsmp_core/sigils");
    private static final double NOT_STOPPED = Double.NaN;

    private static SigilDef load(String id) throws IOException {
        return SigilDef.parse(id, Files.readString(DIR.resolve(id + ".json"), StandardCharsets.UTF_8));
    }

    @Test
    void allDemoSigilsParse() throws IOException {
        List<Path> files;
        try (Stream<Path> s = Files.list(DIR)) {
            files = s.filter(p -> p.toString().endsWith(".json")).toList();
        }
        assertTrue(files.size() >= 4);
        for (Path p : files) {
            String id = p.getFileName().toString().replace(".json", "");
            SigilDef def = load(id);
            assertFalse(def.layers().isEmpty(), id);
        }
    }

    @Test
    void formedAtFollowsTheDocumentedFormula() throws IOException {
        // layersEnd = max(delay + duration); formedAt = layersEnd + expand.delay + expand.duration
        assertEquals(new SigilTimeline.Timings(48, 52, 72), SigilTimeline.timings(load("silent_gate_sky")));
        assertEquals(new SigilTimeline.Timings(36, 36, 36), SigilTimeline.timings(load("silent_gate_ground")));
        assertEquals(new SigilTimeline.Timings(10, 10, 10), SigilTimeline.timings(load("golden_halo")));
        assertEquals(new SigilTimeline.Timings(32, 38, 62), SigilTimeline.timings(load("coven_seal")));
        assertEquals(72 + 120, SigilTimeline.autoStopAt(load("silent_gate_sky")));
    }

    @Test
    void fieldsAreRead() throws IOException {
        SigilDef sky = load("silent_gate_sky");
        assertEquals(Orientation.SKY, sky.orientation());
        assertEquals(0x8FF3FF, sky.color());
        assertTrue(sky.dissolve().modes().containsAll(List.of(DissolveMode.REVERSE, DissolveMode.COLLAPSE)));
        SigilDef ground = load("silent_gate_ground");
        assertEquals(1, ground.onFormed().size());
        assertEquals(6, ground.onFormed().get(0).arc().count());
        assertTrue(ground.onFormed().get(0).anchorCaster());
    }

    @Test
    void layerIsHiddenBeforeItsDelayAndFullAfterIt() throws IOException {
        SigilDef sky = load("silent_gate_sky");
        int core = indexOf(sky, "core");                     // delay 22, grow+fade
        assertEquals(0, SigilTimeline.layer(sky, core, 10, NOT_STOPPED).alpha(), 1e-9);
        var done = SigilTimeline.layer(sky, core, 40, NOT_STOPPED);
        assertEquals(1, done.alpha(), 1e-9);
        assertEquals(0.34, done.scale(), 1e-9);              // grow -> 1, times layer radius
    }

    @Test
    void drawGoesFromZeroToFullCircle() throws IOException {
        SigilDef sky = load("silent_gate_sky");
        int runes = indexOf(sky, "runes");                   // delay 34, duration 10, easeInOutSine
        assertEquals(0, SigilTimeline.layer(sky, runes, 34, NOT_STOPPED).drawFraction(), 1e-9);
        assertEquals(0.5, SigilTimeline.layer(sky, runes, 39, NOT_STOPPED).drawFraction(), 1e-9);
        assertEquals(1, SigilTimeline.layer(sky, runes, 44, NOT_STOPPED).drawFraction(), 1e-9);
    }

    @Test
    void arcsCloseIntoARing() throws IOException {
        SigilDef sky = load("silent_gate_sky");
        int arcs = indexOf(sky, "arcs");                     // 4 arcs of 55 deg
        var start = SigilTimeline.layer(sky, arcs, 0, NOT_STOPPED);
        assertEquals(55, start.arcLength(), 1e-9);
        assertEquals(1.9, start.arcRadiusMul(), 1e-9);
        var end = SigilTimeline.layer(sky, arcs, 22, NOT_STOPPED);
        assertEquals(90, end.arcLength(), 1e-9);             // 360 / 4: no gaps
        assertEquals(1, end.arcRadiusMul(), 1e-9);
        assertEquals(90, end.arcOffset(1, 4, 1), 1e-9);
    }

    @Test
    void expandGrowsTheWholeSigil() throws IOException {
        SigilDef sky = load("silent_gate_sky");
        assertEquals(3.0, SigilTimeline.globalScale(sky, 40, NOT_STOPPED, 1), 1e-9);
        assertEquals(12.0, SigilTimeline.globalScale(sky, 80, NOT_STOPPED, 1), 1e-9);
    }

    @Test
    void reverseDissolveFadesTheLastLayerFirstAndCollapseShrinksToAPoint() throws IOException {
        SigilDef sky = load("silent_gate_sky");
        double stop = 200;
        int first = 0, last = sky.layers().size() - 1;
        double t = stop + 5;
        assertTrue(SigilTimeline.layer(sky, last, t, stop).alpha() < SigilTimeline.layer(sky, first, t, stop).alpha());
        assertEquals(0, SigilTimeline.globalScale(sky, stop + sky.dissolve().duration(), stop, 1), 1e-9);
        assertTrue(SigilTimeline.finished(sky, stop + sky.dissolve().duration(), stop));
        assertFalse(SigilTimeline.finished(sky, stop + 1, stop));
    }

    @Test
    void rotationIsFasterWhileTheLayerAppears() throws IOException {
        SigilDef sky = load("silent_gate_sky");
        int core = indexOf(sky, "core");                     // speed 30 deg/s, boost 2
        double plain = 30.0 / 20 * 100;                     // without boost after 100 ticks
        double withBoost = SigilTimeline.layer(sky, core, 100, NOT_STOPPED).angle();
        assertTrue(withBoost > plain);
        // after the layer has appeared, angle grows exactly at the base speed
        double a1 = SigilTimeline.layer(sky, core, 100, NOT_STOPPED).angle();
        double a2 = SigilTimeline.layer(sky, core, 120, NOT_STOPPED).angle();
        assertEquals(30.0, a2 - a1, 1e-6);
    }

    @Test
    void easingNamesMapToCurves() {
        assertEquals(Easing.EASE_OUT_CUBIC, Easing.byName("easeOutCubic"));
        assertEquals(Easing.EASE_IN_OUT_SINE, Easing.byName("easeInOutSine"));
        assertEquals(Easing.LINEAR, Easing.byName("nonsense"));
        assertEquals(1, Easing.EASE_OUT_BACK.apply(1), 1e-9);
    }

    private static int indexOf(SigilDef def, String layerId) {
        for (int i = 0; i < def.layers().size(); i++) if (def.layers().get(i).id().equals(layerId)) return i;
        throw new AssertionError("no layer " + layerId);
    }

    @Test
    void piecesFlyInAndLock() throws Exception {
        SigilDef d = SigilDef.parse("silent_gate_pieces", java.nio.file.Files.readString(
                java.nio.file.Path.of("src/main/resources/assets/pohsmp_core/sigils/silent_gate_pieces.json")));
        int rim = 4;
        SigilDef.Pieces pc = d.layers().get(rim).appear().pieces();
        org.junit.jupiter.api.Assertions.assertEquals(16, pc.count());
        org.junit.jupiter.api.Assertions.assertEquals(SigilDef.PieceOrder.SCATTER, pc.order());
        // ranks are a permutation for every order and size
        for (SigilDef.PieceOrder o : SigilDef.PieceOrder.values())
            for (int n = 1; n <= 24; n++) {
                boolean[] seen = new boolean[n];
                for (int k = 0; k < n; k++) seen[SigilTimeline.pieceRank(o, k, n)] = true;
                for (boolean b : seen) org.junit.jupiter.api.Assertions.assertTrue(b, o + " " + n);
            }
        org.junit.jupiter.api.Assertions.assertEquals(1, SigilTimeline.pieceRank(SigilDef.PieceOrder.ALTERNATE, 3, 6)); // 0, 3, 1, 4, 2, 5
        org.junit.jupiter.api.Assertions.assertEquals(0, SigilTimeline.piece(d, rim, 0, 0, Double.NaN).alpha(), 1e-9);
        var ap = d.layers().get(rim).appear();
        var mid = SigilTimeline.piece(d, rim, 0, ap.delay() + 2, Double.NaN);   // easeOutBack overshoots past 1 later (bounce on lock)
        org.junit.jupiter.api.Assertions.assertTrue(mid.u() > 0 && mid.u() < 1 && mid.lift() > 0);
        for (int k = 0; k < pc.count(); k++) {
            var s = SigilTimeline.piece(d, rim, k, ap.end() + 20, Double.NaN);
            org.junit.jupiter.api.Assertions.assertEquals(1, s.u(), 1e-9);
            org.junit.jupiter.api.Assertions.assertEquals(1, s.radialMul(), 1e-9);
            org.junit.jupiter.api.Assertions.assertEquals(0, s.lift(), 1e-9);
            org.junit.jupiter.api.Assertions.assertEquals(0, s.tilt(), 1e-9);
            org.junit.jupiter.api.Assertions.assertEquals(1, s.brightness(), 1e-9);
        }
        // dissolve: pieces stay in place, the whole sigil collapses like the others
        double stop = 300;
        var after = SigilTimeline.piece(d, rim, 3, stop + 10, stop);
        org.junit.jupiter.api.Assertions.assertEquals(1, after.u(), 1e-9);
        org.junit.jupiter.api.Assertions.assertTrue(SigilTimeline.globalScale(d, stop + 10, stop, 1) < d.size());
        org.junit.jupiter.api.Assertions.assertEquals(0, SigilTimeline.globalScale(d, stop + 20, stop, 1), 1e-9);
    }
}
