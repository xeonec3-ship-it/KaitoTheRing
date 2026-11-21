package ru.pohsmp.core.spell;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

/** Owner 21.11: no other spell while an animated one runs (CastLock). */
class CastLockMathTest {
    private static final String S = "pohsmp_core:taboo";

    @Test
    void whichCastsTakeAWindow() {
        assertEquals(CastLockMath.TAIL, CastLockMath.tail(true, true, false, false), "our animated spell");
        assertEquals(CastLockMath.TAIL, CastLockMath.tail(true, true, true, true), "our animated spell from a tiered scroll");
        assertEquals(-1, CastLockMath.tail(true, false, false, false), "our spell without animation");
        assertEquals(-1, CastLockMath.tail(false, false, false, true), "Iron's spell from a book");
        assertEquals(0, CastLockMath.tail(false, false, true, false), "Iron's long cast from a Higher scroll: only while it casts");
        assertEquals(CastLockMath.SEAL_INSTANT_TAIL, CastLockMath.tail(false, false, true, true), "instant from a tiered scroll: the seal");
    }

    @Test
    void castThenTailThenFree() {
        CastLockMath.State s = CastLockMath.begin(null, S, 100);
        assertTrue(CastLockMath.locked(s, 101, true), "casting");
        assertTrue(CastLockMath.refuses(s, 150, true, false));
        assertNotNull(CastLockMath.tick(s, 150, true));
        CastLockMath.fired(s, 200, 30);
        assertTrue(CastLockMath.locked(s, 200, false), "finish animation");
        assertNotNull(CastLockMath.tick(s, 229, false));
        assertTrue(CastLockMath.refuses(s, 229, false, false));
        assertFalse(CastLockMath.locked(s, 230, false), "tail over");
        assertNull(CastLockMath.tick(s, 230, false));
    }

    @Test
    void interruptedBeforeEffectEndsAtOnce() {
        CastLockMath.State s = CastLockMath.begin(null, S, 100);
        assertNotNull(CastLockMath.tick(s, 110, true));
        assertNull(CastLockMath.tick(s, 111, false), "cast cancelled / stunned before onCast: free at once");
    }

    @Test
    void interruptedCastAlsoDropsItsScene() {
        CastLockMath.State s = CastLockMath.scene(null, 7, 100, 400);   // the scene comes from onServerPreCast, before the cast is known
        s = CastLockMath.begin(s, S, 100);
        assertTrue(CastLockMath.locked(s, 120, false), "scene still plays");
        assertNull(CastLockMath.tick(s, 121, false), "but the cast stopped before it took effect");
    }

    @Test
    void sceneHoldsAfterTheTailUntilItEnds() {
        CastLockMath.State s = CastLockMath.scene(null, 7, 100, 1000);
        s = CastLockMath.begin(s, S, 100);
        CastLockMath.fired(s, 300, 30);
        assertNotNull(CastLockMath.tick(s, 500, false), "the Gate scene goes on long after the cast");
        assertTrue(CastLockMath.refuses(s, 500, false, false));
        CastLockMath.sceneEnd(s, 7);
        assertNull(CastLockMath.tick(s, 501, false), "Cutscene.end: free");
    }

    @Test
    void sceneEndsByItsLengthToo() {
        CastLockMath.State s = CastLockMath.scene(null, 3, 100, 200);
        s = CastLockMath.begin(s, S, 100);
        CastLockMath.fired(s, 200, 30);
        assertTrue(CastLockMath.locked(s, 299, false));
        assertNull(CastLockMath.tick(s, 300, false));
    }

    @Test
    void beginKeepsOnlyLiveScenes() {
        CastLockMath.State old = CastLockMath.scene(null, 1, 0, 50);
        CastLockMath.scene(old, 2, 100, 50);
        CastLockMath.State s = CastLockMath.begin(old, S, 100);
        CastLockMath.fired(s, 100, 0);
        assertTrue(CastLockMath.locked(s, 120, false), "this cast's scene");
        CastLockMath.sceneEnd(s, 2);
        assertFalse(CastLockMath.locked(s, 120, false), "the old scene was already over");
    }

    @Test
    void recastOfTheSameSpellPasses() {
        CastLockMath.State s = CastLockMath.begin(null, S, 0);
        CastLockMath.fired(s, 10, 30);
        assertFalse(CastLockMath.refuses(s, 20, false, true));
        assertTrue(CastLockMath.refuses(s, 20, false, false));
    }

    @Test
    void capEndsALostWindow() {
        CastLockMath.State s = CastLockMath.scene(null, 1, 0, Integer.MAX_VALUE);
        assertTrue(CastLockMath.locked(s, 10, false));
        assertFalse(CastLockMath.locked(s, CastLockMath.CAP + 100, false));
    }

    @Test
    void nothingLockedWithoutState() {
        assertFalse(CastLockMath.locked(null, 0, true));
        assertFalse(CastLockMath.refuses(null, 0, true, false));
        assertNull(CastLockMath.tick(null, 0, true));
    }

    /** The refusal and the window are wired: mixin, cutscenes, lang lines. */
    @Test
    void wiredIn() throws IOException {
        String mixin = Files.readString(Path.of("src/main/java/ru/pohsmp/core/mixin/AbstractSpellMixin.java"));
        assertTrue(mixin.contains("method = \"attemptInitiateCast\", at = @At(\"HEAD\")") && mixin.contains("CastLock.refuse("));
        assertTrue(mixin.contains("CastLock.begin("));
        String cut = Files.readString(Path.of("src/main/java/ru/pohsmp/core/spell/Cutscene.java"));
        assertTrue(cut.contains("CastLock.scene(") && cut.contains("CastLock.sceneEnd("));
        for (String lang : new String[] {"ru_ru", "en_us"})
            assertTrue(Files.readString(Path.of("src/main/resources/assets/pohsmp_core/lang/" + lang + ".json")).contains("\"message.pohsmp_core.cast_busy\""), lang);
    }
}
