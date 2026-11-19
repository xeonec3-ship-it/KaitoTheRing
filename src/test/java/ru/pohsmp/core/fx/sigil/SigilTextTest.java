package ru.pohsmp.core.fx.sigil;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import ru.pohsmp.core.fx.sigil.SigilText.Font;
import ru.pohsmp.core.fx.sigil.SigilText.Layout;
import ru.pohsmp.core.fx.sigil.SigilText.Letter;
import ru.pohsmp.core.fx.sigil.SigilText.LetterState;
import ru.pohsmp.core.fx.sigil.SigilText.Spec;

/** Inscriptions on sigils (T07): glyph atlases, letter layout on a circle / line, letter-by-letter writing. Runs without Minecraft. */
class SigilTextTest {
    private static final Path ASSETS = Path.of("src/main/resources/assets/pohsmp_core");
    private static final Map<String, Font> FONTS = new HashMap<>();

    private static Font font(String name) {
        return FONTS.computeIfAbsent(name, n -> {
            try {
                return Font.parse(Files.readString(ASSETS.resolve("textures/sigil/glyphs_" + n + ".json"), StandardCharsets.UTF_8));
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }
        });
    }

    private static Spec spec(String json) {
        JsonObject o = JsonParser.parseString(json).getAsJsonObject();
        return Spec.parse(o);
    }

    private static Layout lay(String json, double radius) {
        Spec s = spec(json);
        return SigilText.layout(s, s.text(), radius, font(s.font()), SigilTextTest::font);
    }

    private static double angle(Letter l) {
        return Math.toDegrees(Math.atan2(l.y(), l.x()));
    }

    private static double dist(Letter l) {
        return Math.hypot(l.x(), l.y());
    }

    /** Angle difference a − b folded into (−180, 180]. */
    private static double diff(double a, double b) {
        double d = (a - b) % 360;
        if (d > 180) d -= 360;
        if (d <= -180) d += 360;
        return d;
    }

    // ---------------------------------------------------------------- atlases

    @Test
    void atlasesParseAndCoverTheirAlphabets() {
        Font latin = font("latin"), cyr = font("cyrillic"), runic = font("runic");
        for (char c = 'A'; c <= 'Z'; c++) assertNotNull(SigilText.resolve(latin, c, SigilTextTest::font), "latin " + c);
        for (char c = 'a'; c <= 'z'; c++) assertNotNull(SigilText.resolve(latin, c, SigilTextTest::font), "latin " + c);
        for (char c = 'А'; c <= 'я'; c++) assertNotNull(SigilText.resolve(cyr, c, SigilTextTest::font), "cyrillic " + c);
        for (char c = '0'; c <= '9'; c++) {
            assertNotNull(SigilText.resolve(runic, c, SigilTextTest::font), "runic digit " + c);
            assertNotNull(SigilText.resolve(cyr, c, SigilTextTest::font), "cyrillic digit " + c);
        }
        for (Font f : List.of(latin, cyr, runic)) {
            for (var g : f.glyphs().values()) {
                assertTrue(g.cell() >= 0 && g.cell() < f.cols() * f.rows(), f.name() + " cell " + g.cell());
                assertTrue(g.advance() > 0 && g.advance() <= 1, f.name() + " advance " + g.advance());
            }
            assertNotNull(f.find('✦'), f.name() + " has the ornaments");
        }
    }

    @Test
    void uvOfACellIsItsSquareInTheAtlas() {
        Font f = font("latin");                                        // 16 columns
        float[] uv = f.uv(17);                                         // column 1, row 1
        assertEquals(1f / 16, uv[0], 1e-6);
        assertEquals(1f / f.rows(), uv[1], 1e-6);
        assertEquals(2f / 16, uv[2], 1e-6);
        assertEquals(2f / f.rows(), uv[3], 1e-6);
    }

    @Test
    void runesWriteOneRunePerSoundInBothAlphabetsAndIgnoreCase() {
        Font r = font("runic");
        assertEquals(r.find('A').cell(), r.find('А').cell());                 // латинская и русская «а» — одна руна
        assertEquals(r.find('V').cell(), r.find('В').cell());
        assertEquals(r.find('S').cell(), r.find('с').cell());                 // строчные — как прописные
        assertTrue(r.find('Ж').cell() != r.find('Z').cell());                 // у Ж своя руна
    }

    @Test
    void cyrillicFallsBackToLatinForWhatItLacks() {
        Font c = font("cyrillic");
        assertNull(c.find('Q'));
        var q = SigilText.resolve(c, 'Q', SigilTextTest::font);
        assertNotNull(q);
        assertEquals("glyphs_latin", q.font().texture());
        Layout l = lay("{\"text\":\"Ковен Q\",\"font\":\"cyrillic\"}", 1);
        assertEquals("glyphs_cyrillic", l.letters().get(0).texture());
        assertEquals("glyphs_latin", l.letters().get(5).texture());
    }

    // ---------------------------------------------------------------- layout on a circle

    @Test
    void outerTextIsCentredOnTheTopAndReadsClockwiseWithTopsOutwards() {
        Layout l = lay("{\"text\":\"HH\",\"font\":\"latin\",\"size\":0.1}", 1);
        assertEquals(2, l.letters().size());
        Letter a = l.letters().get(0), b = l.letters().get(1);
        assertTrue(angle(a) > 90 && angle(b) < 90, "first letter left of the top, second right of it (clockwise)");
        assertEquals(90 - angle(b), angle(a) - 90, 1e-9);                     // symmetric around the anchor
        assertEquals(angle(a), a.up(), 1e-9);                                 // top of the letter points outwards
        Font f = font("latin");
        double drop = (0.5 - (f.baseline() - f.capHeight() / 2)) * 0.1;
        assertEquals(1 - drop, dist(a), 1e-9);                                // middle of capitals on the radius
    }

    @Test
    void innerTextSitsAtTheBottomAndReadsCounterClockwiseWithTopsInwards() {
        Layout l = lay("{\"text\":\"AB\",\"font\":\"latin\",\"side\":\"inner\"}", 0.8);
        Letter a = l.letters().get(0), b = l.letters().get(1);
        double mid = (angle(a) + angle(b)) / 2;
        assertTrue(Math.abs(diff(mid, 270)) < 3, "near the bottom: " + mid);
        assertTrue(diff(angle(b), angle(a)) > 0, "counter-clockwise");
        assertEquals(0, diff(a.up(), angle(a) + 180), 1e-9);                 // top towards the centre
    }

    @Test
    void lettersAreSpacedByTheirAdvanceAlongTheArc() {
        double r = 1.2, size = 0.1, spacing = 0.2;
        Layout l = lay("{\"text\":\"HI\",\"font\":\"latin\",\"size\":0.1,\"spacing\":0.2}", r);
        Font f = font("latin");
        double h = f.find('H').advance(), i = f.find('I').advance();
        double arc = (h / 2 + spacing + i / 2) * size;                       // centre to centre
        assertEquals(Math.toDegrees(arc / r), diff(angle(l.letters().get(0)), angle(l.letters().get(1))), 1e-9);
    }

    @Test
    void alignStartPutsTheFirstLetterOnTheAnchor() {
        Layout l = lay("{\"text\":\"MAGIA\",\"font\":\"latin\",\"align\":\"start\",\"angle\":180}", 1);
        Letter first = l.letters().get(0);
        Font f = font("latin");
        double half = Math.toDegrees(f.find('M').advance() * Spec.DEFAULT_SIZE / 2 / 1);
        assertEquals(180 - half, (angle(first) + 360) % 360, 1e-6);           // begins at 180° and goes clockwise
    }

    @Test
    void repeatSpreadsCopiesEvenly() {
        Layout l = lay("{\"text\":\"ABC\",\"font\":\"latin\",\"repeat\":3}", 1);
        assertEquals(3, l.copies());
        assertEquals(9, l.letters().size());
        for (int k = 0; k < 3; k++) assertEquals(-120.0, diff(angle(l.letters().get(3 + k)), angle(l.letters().get(k))), 1e-9);
        assertEquals(3, l.perCopy());
    }

    @Test
    void repeatZeroFillsTheCircle() {
        Spec s = spec("{\"text\":\"TEMPUS\",\"font\":\"latin\",\"repeat\":0,\"size\":0.1}");
        Font f = font("latin");
        double units = 0;
        for (char c : "TEMPUS".toCharArray()) units += f.find(c).advance();
        units += s.spacing() * 5;
        int expected = (int) Math.floor(2 * Math.PI * 1.0 / ((units + f.space() + s.spacing()) * 0.1));
        Layout l = SigilText.layout(s, s.text(), 1.0, f, SigilTextTest::font);
        assertEquals(expected, l.copies());
        assertTrue(l.copies() >= 3);
    }

    @Test
    void tooLongTextShrinksToFit() {
        String text = "THIS INSCRIPTION IS FAR TOO LONG FOR SUCH A SMALL CIRCLE";
        Layout l = lay("{\"text\":\"" + text + "\",\"font\":\"latin\",\"size\":0.2}", 0.3);
        assertTrue(l.size() < 0.2);
        Letter first = l.letters().get(0), last = l.letters().get(l.letters().size() - 1);
        double span = (angle(first) - angle(last) + 720) % 360;
        assertTrue(span < 0.97 * 360, "span " + span);
        Layout noFit = lay("{\"text\":\"" + text + "\",\"font\":\"latin\",\"size\":0.2,\"fit\":false}", 0.3);
        assertEquals(0.2, noFit.size(), 1e-12);
    }

    @Test
    void spacesAndUnknownCharactersTakeRoomButAreNotDrawn() {
        Layout a = lay("{\"text\":\"A B\",\"font\":\"latin\"}", 1), b = lay("{\"text\":\"A中B\",\"font\":\"latin\"}", 1);
        assertEquals(2, a.letters().size());
        assertEquals(2, b.letters().size());
        assertEquals(1, a.letters().get(1).order());                          // reading order counts drawn letters only
    }

    // ---------------------------------------------------------------- straight line (counter on a clock face)

    @Test
    void lineTextIsHorizontalAndCentredAtTheOffset() {
        Layout l = lay("{\"text\":\"12\",\"font\":\"latin\",\"side\":\"line\",\"size\":0.3}", -0.3);
        Font f = font("latin");
        double drop = (0.5 - (f.baseline() - f.capHeight() / 2)) * 0.3;
        Letter a = l.letters().get(0), b = l.letters().get(1);
        assertEquals(-a.x(), b.x(), 1e-9);                                    // digits have the same width: symmetric
        assertEquals(-0.3 - drop, a.y(), 1e-9);
        assertEquals(90, a.up(), 1e-9);
        assertEquals(1, l.copies());
    }

    @Test
    void counterDoesNotJumpWhenADigitChanges() {
        Layout a = lay("{\"text\":\"18\",\"font\":\"latin\",\"side\":\"line\"}", 0), b = lay("{\"text\":\"11\",\"font\":\"latin\",\"side\":\"line\"}", 0);
        assertEquals(a.letters().get(0).x(), b.letters().get(0).x(), 1e-12);  // tabular figures
    }

    // ---------------------------------------------------------------- letter by letter

    @Test
    void revealWritesLettersOneByOne() {
        int n = 6;
        for (int k = 0; k < n; k++) {
            assertEquals(0, SigilText.reveal(k, n, 0, 1).alpha(), 1e-12);
            assertEquals(1, SigilText.reveal(k, n, 1, 1).alpha(), 1e-12);
        }
        assertTrue(SigilText.reveal(0, n, 0.05, 1).alpha() > 0);              // the first letter starts at once
        double p = 0.5;
        for (int k = 1; k < n; k++)
            assertTrue(SigilText.reveal(k, n, p, 1).alpha() <= SigilText.reveal(k - 1, n, p, 1).alpha(), "letter " + k);
        // the first letter is fully written before the last one starts
        double firstDone = SigilText.SOFT / (n + SigilText.SOFT), lastStarts = (n - 1) / (n + SigilText.SOFT);
        assertTrue(firstDone < lastStarts);
        assertEquals(1, SigilText.reveal(0, n, firstDone, 1).alpha(), 1e-9);
        assertEquals(0, SigilText.reveal(n - 1, n, lastStarts, 1).alpha(), 1e-9);
        // backwards: the last letter first
        assertTrue(SigilText.reveal(n - 1, n, 0.1, -1).alpha() > SigilText.reveal(0, n, 0.1, -1).alpha());
    }

    @Test
    void anAppearingLetterStartsLargerAndFlares() {
        LetterState half = SigilText.reveal(0, 1, 0.3, 1);
        assertTrue(half.alpha() > 0 && half.alpha() < 1);
        assertTrue(half.scale() > 1);
        assertTrue(half.brightness() > 1);
        assertEquals(LetterState.SHOWN, SigilText.reveal(0, 1, 1, 1));
    }

    @Test
    void replacedTextWritesItselfInAndFlares() {
        assertEquals(0, SigilText.changeProgress(0, 6), 1e-12);
        assertEquals(0.5, SigilText.changeProgress(3, 6), 1e-12);
        assertEquals(1, SigilText.changeProgress(Double.NaN, 6), 1e-12);
        assertEquals(1.8, SigilText.changeFlash(0, 6, 0.8), 1e-12);
        assertEquals(1, SigilText.changeFlash(6, 6, 0.8), 1e-12);
    }

    @Test
    void slotsReplaceTheText() {
        Spec s = spec("{\"text\":\"0\",\"slot\":\"count\",\"font\":\"latin\"}");
        assertEquals("0", SigilText.textFor(s, null));
        assertEquals("17", SigilText.textFor(s, Map.of("count", "17")));
        assertEquals("0", SigilText.textFor(s, Map.of("text", "x")));
        Spec fixed = spec("{\"text\":\"TEMPUS\",\"font\":\"latin\"}");
        assertEquals("TEMPUS", SigilText.textFor(fixed, Map.of("text", "x")));
    }

    // ---------------------------------------------------------------- in sigils

    private static SigilDef sigil(String id) throws IOException {
        return SigilDef.parse(id, Files.readString(ASSETS.resolve("sigils/" + id + ".json"), StandardCharsets.UTF_8));
    }

    private static int indexOf(SigilDef d, String id) {
        for (int i = 0; i < d.layers().size(); i++) if (d.layers().get(i).id().equals(id)) return i;
        throw new AssertionError("no layer " + id);
    }

    @Test
    void textLayersParseInTheDemoSigils() throws IOException {
        SigilDef clock = sigil("time_clock");
        var count = clock.layers().get(indexOf(clock, "count"));
        assertEquals(SigilDef.LayerType.TEXT, count.type());
        assertEquals("count", count.text().slot());
        assertEquals(SigilText.Side.LINE, count.text().side());
        assertEquals(SigilDef.LayerType.TEXT, clock.layers().get(indexOf(clock, "motto")).type());
        SigilDef coven = sigil("coven_seal");
        assertEquals("runic", coven.layers().get(indexOf(coven, "inscription")).text().font());
    }

    @Test
    void inscriptionsDoNotMoveTheMomentASigilIsFormed() throws IOException {
        // заклинания бьют по formedAt — надписи укладываются в старое время появления слоёв
        assertEquals(new SigilTimeline.Timings(36, 36, 36), SigilTimeline.timings(sigil("time_clock")));
        assertEquals(new SigilTimeline.Timings(32, 38, 62), SigilTimeline.timings(sigil("coven_seal")));
    }

    @Test
    void timelineWritesTheMottoLetterByLetterAndTheCounterOnChange() throws IOException {
        SigilDef clock = sigil("time_clock");
        int motto = indexOf(clock, "motto"), count = indexOf(clock, "count");
        var ap = clock.layers().get(motto).appear();
        assertEquals(0, SigilTimeline.letter(clock, motto, 0, 10, ap.delay(), Double.NaN).alpha(), 1e-12);
        assertTrue(SigilTimeline.letter(clock, motto, 0, 10, ap.delay() + ap.duration() * 0.3, Double.NaN).alpha()
                > SigilTimeline.letter(clock, motto, 9, 10, ap.delay() + ap.duration() * 0.3, Double.NaN).alpha());
        assertEquals(1, SigilTimeline.letter(clock, motto, 9, 10, ap.end(), Double.NaN).alpha(), 1e-12);
        assertEquals(1, SigilTimeline.layer(clock, motto, ap.end(), Double.NaN).scale(), 1e-12);      // TEXT: grow only, not × radius
        // counter: a new number writes itself in over `change` ticks with a flare
        int change = clock.layers().get(count).text().change();
        LetterState now = SigilTimeline.letter(clock, count, 0, 2, 100, 0);
        assertEquals(0, now.alpha(), 1e-12);
        LetterState mid = SigilTimeline.letter(clock, count, 0, 2, 100, change / 2.0);
        assertTrue(mid.alpha() > 0 && mid.brightness() > 1);
        assertEquals(1, SigilTimeline.letter(clock, count, 1, 2, 100, change).alpha(), 1e-12);
    }
}
