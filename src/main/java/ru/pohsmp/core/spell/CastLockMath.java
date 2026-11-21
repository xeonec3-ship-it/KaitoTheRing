package ru.pohsmp.core.spell;

import java.util.HashMap;
import java.util.Map;

/**
 * Owner 21.11 (cast lock): the pure part of {@link CastLock} (CastLockMathTest). While a player's spell with an animation / cutscene
 * runs (the cast, then the finish animation or the scene), no other spell may start. The window of one spell:
 * <ul>
 *   <li>the cast itself: as long as Iron's says the player casts this spell;</li>
 *   <li>after it took effect (Iron's onCast): {@code tail} more ticks (the finish animation);</li>
 *   <li>every cutscene the caster started: until its end (Cutscene.end) or its planned length, whichever comes first.</li>
 * </ul>
 * A cast that stops before it took effect (cancelled, stunned, «Сломать блок», death) ends the window at once.
 */
public final class CastLockMath {
    private CastLockMath() {}

    /** Finish animation of our animated spells (CastAnims.FINISH_TICKS). */
    public static final int TAIL = CastAnims.FINISH_TICKS;
    /** An instant spell from a Higher / Mythic / Divine scroll: its tier seal stands 2 s (SchoolSeals). */
    public static final int SEAL_INSTANT_TAIL = 40;
    /** No window ever lasts longer than this after its last renewal (safety: a lost Cutscene.end). */
    public static final long CAP = 20L * 120;

    public static final class State {
        String spell;
        boolean fired;
        long finishUntil;
        long capUntil;
        final Map<Integer, Long> scenes = new HashMap<>();

        public String spell() { return spell; }
        public boolean fired() { return fired; }
    }

    /**
     * How long the window stays after the spell took effect, or -1 if this cast takes no window at all.
     * ours: a pohsmp_core spell; animated: it has its own player animation or a cutscene (FixedCastSpell);
     * tieredScroll: cast from a Higher / Mythic / Divine scroll (any spell, Iron's too: the tier seal is its scene).
     */
    public static int tail(boolean ours, boolean animated, boolean tieredScroll, boolean instant) {
        if (ours && animated) return TAIL;
        if (tieredScroll) return instant ? SEAL_INSTANT_TAIL : 0;
        return -1;
    }

    /** A new animated cast began: a fresh window for it; scenes its own pre-cast already opened (this tick) are kept. */
    public static State begin(State old, String spell, long now) {
        State s = new State();
        s.spell = spell;
        s.capUntil = now + CAP;
        if (old != null) old.scenes.forEach((k, until) -> { if (until > now) s.scenes.put(k, until); });
        return s;
    }

    /** The spell took effect: the finish tail starts now. */
    public static void fired(State s, long now, int tail) {
        s.fired = true;
        s.finishUntil = Math.max(s.finishUntil, now + Math.max(0, tail));
        s.capUntil = Math.max(s.capUntil, now + CAP);
    }

    /** The caster started a cutscene of `dur` ticks (state may be new: the scene comes from onServerPreCast, before the cast is known). */
    public static State scene(State s, int key, long now, int dur) {
        if (s == null) {
            s = new State();
            s.capUntil = now + CAP;
        }
        s.scenes.put(key, now + Math.max(0, dur));
        s.capUntil = Math.max(s.capUntil, now + Math.min(CAP, Math.max(0, dur)) + 20);
        return s;
    }

    public static void sceneEnd(State s, int key) {
        if (s != null) s.scenes.remove(key);
    }

    /** True while the window holds. castingThis: Iron's says the player is casting s.spell right now. */
    public static boolean locked(State s, long now, boolean castingThis) {
        if (s == null || now >= s.capUntil) return false;
        if (castingThis && s.spell != null) return true;
        if (now < s.finishUntil) return true;
        for (long until : s.scenes.values()) if (now < until) return true;
        return false;
    }

    /** Once a tick: the state to keep, or null when the window is over (interrupted cast, tail and scenes done, cap reached). */
    public static State tick(State s, long now, boolean castingThis) {
        if (s == null) return null;
        if (s.spell != null && !s.fired && !castingThis) return null;   // stopped before it took effect: nothing more plays
        s.scenes.values().removeIf(until -> until <= now);
        return locked(s, now, castingThis) ? s : null;
    }

    /**
     * True if a new cast attempt is refused. recastOfLocked: the attempt is a recast (Iron's recasts) of the very spell
     * that holds the window — that is the same spell going on, not another one.
     */
    public static boolean refuses(State s, long now, boolean castingThis, boolean recastOfLocked) {
        return locked(s, now, castingThis) && !recastOfLocked;
    }
}
