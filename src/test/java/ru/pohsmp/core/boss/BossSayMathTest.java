package ru.pohsmp.core.boss;

import static org.junit.jupiter.api.Assertions.*;

import java.util.List;
import java.util.function.ToIntFunction;
import org.junit.jupiter.api.Test;

class BossSayMathTest {
    /** 6 px a letter (a monospace stand-in for the font). */
    private static final ToIntFunction<String> W6 = s -> s.length() * 6;

    @Test
    void holdIsTwoAndAHalfSecondsPlusPerLetter() {
        assertEquals(50, BossSayMath.hold(0), 1e-9);
        assertEquals(50 + 1.2 * 40, BossSayMath.hold(40), 1e-9, "40 letters: 2.5 + 2.4 s");
        assertEquals(20, BossSayMath.typeTicks(40), 1e-9, "40 letters a second");
        double total = BossSayMath.total(26);
        assertEquals(BossSayMath.TYPE_DELAY + 13 + 50 + 1.2 * 26 + BossSayMath.OUT, total, 1e-9);
        assertTrue(BossSayMath.total(1) >= 50 + BossSayMath.OUT, "at least 2.5 s on screen");
    }

    @Test
    void typingAndFades() {
        assertEquals(0, BossSayMath.visible(0, 30));
        assertEquals(0, BossSayMath.visible(BossSayMath.TYPE_DELAY, 30));
        assertEquals(2, BossSayMath.visible(BossSayMath.TYPE_DELAY + 1, 30));
        assertEquals(30, BossSayMath.visible(1000, 30));
        double out = BossSayMath.outAt(30);
        assertEquals(0, BossSayMath.alpha(0, out), 1e-6);
        assertEquals(1, BossSayMath.alpha(BossSayMath.IN, out), 1e-6);
        assertEquals(1, BossSayMath.alpha(out, out), 1e-6);
        assertEquals(0, BossSayMath.alpha(out + BossSayMath.OUT, out), 1e-6);
        assertTrue(BossSayMath.alpha(out + BossSayMath.OUT / 2.0, out) > 0.2);
        assertEquals(BossSayMath.RISE, BossSayMath.rise(0, out), 1e-9);
        assertEquals(0, BossSayMath.rise(BossSayMath.IN, out), 1e-9);
        assertEquals(1, BossSayMath.sounds(4, 5));
        assertEquals(0, BossSayMath.sounds(5, 9));
        assertEquals(2, BossSayMath.sounds(0, 10));
    }

    @Test
    void wrapsByWords() {
        List<String> l = BossSayMath.wrap("  Хорошо, вы доказали   свою силу...Я помогу Эребу ", 60, W6);
        assertEquals(List.of("Хорошо, вы", "доказали", "свою", "силу...Я", "помогу", "Эребу"), l);
        for (String s : l) assertTrue(W6.applyAsInt(s) <= 60);
        assertEquals(List.of("Вот мы и снова встретились"), BossSayMath.wrap("Вот мы и снова встретились", 300, W6));
        assertTrue(BossSayMath.wrap("   ", 100, W6).isEmpty());
        assertTrue(BossSayMath.wrap(null, 100, W6).isEmpty());
    }

    @Test
    void cutsTooLongWords() {
        List<String> l = BossSayMath.wrap("ааааааааааааааа б", 30, W6);   // 15 letters, 5 fit
        assertEquals(List.of("ааааа", "ааааа", "ааааа", "б"), l);
        assertEquals(16, BossSayMath.chars(l));
    }

    @Test
    void typesLineAfterLine() {
        List<String> l = List.of("abc", "de");
        assertEquals(List.of("", ""), BossSayMath.typed(l, 0));
        assertEquals(List.of("ab", ""), BossSayMath.typed(l, 2));
        assertEquals(List.of("abc", "d"), BossSayMath.typed(l, 4));
        assertEquals(List.of("abc", "de"), BossSayMath.typed(l, 99));
    }

    @Test
    void layoutFitsTheScreen() {
        assertEquals(BossSayMath.MAX_TEXT, BossSayMath.maxTextWidth(640), "wide screen: capped");
        assertEquals(320 - 48, BossSayMath.maxTextWidth(320), "narrow: the whole width but margins and padding");
        assertEquals(BossSayMath.MIN_TEXT, BossSayMath.maxTextWidth(90));
        int w = BossSayMath.boxWidth(80, 300, 640);
        assertEquals(300 + 2 * BossSayMath.PAD_X, w);
        assertTrue(BossSayMath.boxWidth(80, 1000, 320) <= 320 - 2 * BossSayMath.SCREEN_MARGIN);
        assertTrue(BossSayMath.boxHeight(2) > BossSayMath.boxHeight(1));
        // over the hotbar, health and xp (39) and over the action bar line
        assertEquals(240 - BossSayMath.ACTIONBAR_CLEAR, BossSayMath.bottom(240, 39, 0));
        assertEquals(240 - 89, BossSayMath.bottom(240, 81, 0), "many HUD rows (absorption, armour): higher");
        assertEquals(240 - 29, BossSayMath.bottom(240, 0, 21), "in a scene: over the letterbox bar");
        assertEquals(240 - 24, BossSayMath.bottom(240, 0, 0));
    }

    @Test
    void styles() {
        assertEquals(6, BossSayMath.STYLES.size());
        for (String id : BossSayMath.STYLES) assertEquals(id, BossSayMath.styleName(BossSayMath.styleIndex(id)));
        assertEquals("default", BossSayMath.styleName(-1));
        assertEquals(-1, BossSayMath.styleIndex("zombie"));
        assertEquals(0xF2ECDF, BossSayMath.mix(0xF2ECDF, 0x000000, 0));
        assertEquals(0x000000, BossSayMath.mix(0xF2ECDF, 0x000000, 1));
    }

    private static BossSayMath.Line<String> line(String s) {
        return new BossSayMath.Line<>(s, s.length());
    }

    @Test
    void queueOneAfterAnother() {
        BossSayMath.Queue<String> q = new BossSayMath.Queue<>();
        assertNull(q.update(0));
        BossSayMath.Line<String> a = line("a".repeat(20)), b = line("b".repeat(10));
        q.push(a, 0);
        assertSame(a, q.update(1));
        assertEquals(BossSayMath.outAt(20), a.outAt(), 1e-9, "alone: the full hold");
        q.push(b, 5);   // while a is typing
        assertEquals(1, q.waiting());
        double typedA = BossSayMath.typedAt(20);
        assertEquals(typedA + BossSayMath.QUEUE_HOLD, a.outAt(), 1e-9, "something waits: a holds 1.5 s after it is typed");
        double aEnd = a.outAt() + BossSayMath.OUT;
        assertSame(a, q.update(aEnd - 0.01));
        assertSame(b, q.update(aEnd + 3), "b starts as soon as a is gone");
        assertEquals(aEnd, b.start(), 1e-9, "back to back");
        assertEquals(0, q.waiting());
        assertEquals(BossSayMath.outAt(10), b.outAt(), 1e-9, "nothing waits after b: its full hold");
        assertNull(q.update(b.start() + BossSayMath.total(10) + 1));
    }

    @Test
    void queueLatePushShortensTheHold() {
        BossSayMath.Queue<String> q = new BossSayMath.Queue<>();
        BossSayMath.Line<String> a = line("a".repeat(30));
        q.push(a, 100);
        q.push(line("b"), 100 + 40);   // well after a is typed
        assertEquals(40 + BossSayMath.QUEUE_HOLD, a.outAt(), 1e-9);
        assertTrue(a.outAt() < BossSayMath.outAt(30));
    }

    @Test
    void queueIsBounded() {
        BossSayMath.Queue<String> q = new BossSayMath.Queue<>();
        q.push(line("first"), 0);
        for (int i = 0; i < 10; i++) q.push(line("w" + i), 1);
        assertEquals(BossSayMath.QUEUE_MAX, q.waiting());
        q.clear();
        assertNull(q.update(2));
    }

    @Test
    void systemArgsRoundTrip() {
        assertEquals("", BossSayMath.packArgs());
        assertEquals(0, BossSayMath.unpackArgs("").length);
        String[] one = BossSayMath.unpackArgs(BossSayMath.packArgs("Steve"));
        assertEquals(1, one.length);
        assertEquals("Steve", one[0]);
        String[] two = BossSayMath.unpackArgs(BossSayMath.packArgs("A", ""));
        assertEquals(2, two.length);
        assertEquals("", two[1]);
        String big = "x".repeat(1000);
        assertTrue(BossSayMath.packArgs(big, big, big).length() <= BossSayMath.ARGS_MAX);
        assertEquals("a b", BossSayMath.unpackArgs(BossSayMath.packArgs("a" + BossSayMath.ARG_SEP + "b"))[0]);
    }

    @Test
    void systemLayout() {
        assertTrue(BossSayMath.systemBoxHeight(1) < BossSayMath.boxHeight(1));   // no name line
        assertTrue(BossSayMath.systemBoxHeight(2) > BossSayMath.systemBoxHeight(1));
        assertEquals(200 + 26 + 2 * BossSayMath.PAD_X, BossSayMath.systemBoxWidth(200, 640));
        assertTrue(BossSayMath.systemBoxWidth(1000, 320) <= 320 - 2 * BossSayMath.SCREEN_MARGIN);
        assertTrue(BossSayMath.SYSTEM != BossSayMath.SPEECH);
    }
}
