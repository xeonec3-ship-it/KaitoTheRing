package ru.pohsmp.core.boss;

/**
 * T33 boss music by phases, the pure part (tested): which loop a phase plays, the fallbacks when a loop / the whole track is missing,
 * the fade curve. Loops are 1..3 (`<id>_p1`..`_p3`), 0 is the intro (`<id>_intro`, played once before loop 1).
 */
public final class BossMusicMath {
    private BossMusicMath() {}

    public static final int INTRO = 0, LOOPS = 3;
    /** The parts of a track, by index: 0 intro, 1..3 the phase loops. */
    public static final String[] PARTS = {"_intro", "_p1", "_p2", "_p3"};

    /** The loop of a fight phase (BossCore.phase(): 0 = first): 1..3. */
    public static int loopOfPhase(int phase) {
        return Math.max(1, Math.min(LOOPS, phase + 1));
    }

    /**
     * The loop to play for `want` (1..3) when only some loops exist (has[1..3]; has[0] = intro, ignored here): that one, else the
     * previous one(s), else the next one(s) (a track sent without its first loop); 0 = no loop at all (play the stub).
     */
    public static int pickLoop(int want, boolean[] has) {
        want = Math.max(1, Math.min(LOOPS, want));
        for (int i = want; i >= 1; i--) if (i < has.length && has[i]) return i;
        for (int i = want + 1; i <= LOOPS; i++) if (i < has.length && has[i]) return i;
        return 0;
    }

    /** No loop at all: the track is not there, the old one-sound stub (music.<id>, Iron's) plays instead. */
    public static boolean useStub(boolean[] has) {
        return pickLoop(1, has) == 0;
    }

    /** The intro plays only at the very start of the fight (loop 1 wanted) and only if it exists and a loop follows it. */
    public static boolean playIntro(int want, boolean[] has) {
        return want <= 1 && has.length > 0 && has[INTRO] && !useStub(has);
    }

    /** Seconds → ticks (at least 0). */
    public static int ticks(double seconds) {
        return (int) Math.max(0, Math.round(seconds * 20));
    }

    /**
     * Equal-power fade: the gain going from `from` to `to`, progress p 0..1 (sin rising, cos falling), so two tracks crossfading in
     * opposite directions keep the loudness (from 1 → 0 and 0 → 1: g1² + g2² = 1 all the way).
     */
    public static float fadeGain(float from, float to, float p) {
        p = Math.max(0, Math.min(1, p));
        if (to >= from) return from + (to - from) * (float) Math.sin(p * Math.PI / 2);
        return to + (from - to) * (float) Math.cos(p * Math.PI / 2);
    }
}
