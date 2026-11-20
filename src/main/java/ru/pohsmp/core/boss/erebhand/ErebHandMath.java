package ru.pohsmp.core.boss.erebhand;

import java.util.ArrayList;
import java.util.List;

/**
 * T31 «Эреб, Длань Лжи»: the timings (ticks, from the events of animations/entity/ereb_hand.animation.json and
 * ereb_hand_giant.animation.json — the events are not read by the code, the same moments are timers; ErebHandMathTest checks them
 * against the files) and the pure geometry / choices of his moves. No Minecraft classes.
 */
public final class ErebHandMath {
    private ErebHandMath() {}

    // ---------------------------------------------------------------- scenes
    /** «Появление» ereb_hand_spawn 5.5 s: nothing 0–0.6, the hand forms (form_hand 0.6), he is seen at form 1.8, bow 2.6, salute (title)
     * 3.4, speak 4.3 «Вот мы и снова встретились», ready (bar) 5.5. */
    public static final int INTRO = 110, INTRO_HAND = 12, INTRO_FORM = 36, INTRO_BOW = 52, INTRO_TITLE = 68, INTRO_SPEAK = 86, INTRO_TITLE_HOLD = 60;
    /** Phase changes: ereb_hand_phase2 1.6 s (`phase` 0.8), ereb_hand_phase3 2.0 s (`crack` 0.9 — the mask texture → _cracked). */
    public static final int PHASE2 = 32, PHASE2_AT = 16, PHASE3 = 40, PHASE3_CRACK = 18;
    /** Ложная смерть ereb_hand_false_death 5.0 s: stagger 0.4, hand_break 0.7, speak 1.6, smile 2.6, vanish 3.8 (model off 78). */
    public static final int DEATH = 100, DEATH_HAND = 14, DEATH_SPEAK = 32, DEATH_SMILE = 52, DEATH_VANISH = 76, DEATH_HIDE = 78;
    /** After the vanish the dream breaks: the T22 waking scene (34 ticks) runs to its end before he is removed. */
    public static final int DEATH_END = DEATH_VANISH + 38;

    // ---------------------------------------------------------------- his animations
    public static final int LUNGE = 28, LUNGE_HIT = 10;
    public static final int FLURRY = 42;
    public static final int[] FLURRY_HITS = {9, 16, 23};
    /** ereb_hand_slam: raise 0.45, slam 0.8 (the palm ≈0.9 forward, 0.6 to his right). */
    public static final int SLAM = 36, SLAM_RAISE = 9, SLAM_HIT = 16;
    public static final double SLAM_FWD = 0.9, SLAM_RIGHT = 0.6;
    /** ereb_hand_grab (grab 0.6) → grab_hold (loop 2.0) ↔ squeeze (squeeze 0.35) → grab_release (release 0.2). */
    public static final int GRAB = 24, GRAB_AT = 12, HOLD_LOOP = 40, SQUEEZE = 24, SQUEEZE_AT = 7, RELEASE = 20, RELEASE_AT = 4;
    /** Where the held one's FEET are in grab_hold, from his feet: right, up, forward (blocks). */
    public static final double HOLD_RIGHT = 0.5, HOLD_UP = 1.25, HOLD_FWD = 1.45;
    /** ereb_hand_cast 1.4 s: the snap at `cast` 0.75. */
    public static final int CAST = 28, CAST_AT = 15;

    // ---------------------------------------------------------------- specials
    /** «Длань Лжи» ereb_hand_hand_of_lies 3.2 s: rise 0.5, gone 0.95, descend 1.2, return 2.4. The giant hand comes down from +26 over
     * 24 ticks (shadow on the ground = the warning), catches (ereb_hand_giant_grab, catch 0.25), lifts the victim 2.5 blocks and holds
     * it 6 s (the false arena), then ereb_hand_giant_release (release 0.2) and melts. */
    public static final int HOL = 64, HOL_DESCEND = 24, HOL_RETURN = 48, HOL_FALL = 24, HOL_CATCH = HOL_DESCEND + HOL_FALL;
    public static final int GIANT_GRAB = 10, GIANT_CATCH = 5, GIANT_RELEASE = 16, GIANT_RELEASE_AT = 4, GIANT_SLAM = 28, GIANT_SLAM_AT = 11;
    public static final double GIANT_FROM = 26, GIANT_LIFT = 2.5;
    /** The fist of the ×5 hand: the held one's feet are 1.6 below the wrist (the entity's position) and 2.5 forward of it. */
    public static final double FIST_DOWN = 1.6, FIST_FWD = 2.5, GIANT_SCALE = 5, GIANT_SCALE_DREAM = 6;
    /** «Падение маски» ereb_hand_mask_fall 2.2 s: grip 0.5, tear 0.85, shatter 1.1; the arrow 2 s; the return ereb_hand_mask_return
     * 1.4 s (mend 0.7). */
    public static final int MASK_FALL = 44, MASK_TEAR = 17, MASK_SHATTER = 22, MASK_ARROW = 40, MASK_RETURN = 28, MASK_MEND = 14;
    /** «Полное Раскрытие» ereb_hand_full_reveal 4.0 s: butterflies 0.8, open 1.4, cast 2.6 (the dream falls). The palm's warning 30. */
    public static final int REVEAL = 80, REVEAL_OPEN = 28, REVEAL_CAST = 52, DREAM_SLAM_WARN = 30;

    // ---------------------------------------------------------------- the four spells
    /** «Ложное пламя» ereb_hand_false_flame 1.6 s: marks 0.6; the circles light 1 s after the marks (the mark fx is the warning). */
    public static final int FLAME = 32, FLAME_MARKS = 12, FLAME_IGNITE = FLAME_MARKS + 20;
    /** «Стеклянная хватка» ereb_hand_glass_grip 2.0 s: warn 0 (the cone, 1 s), grip 1.0. */
    public static final int GRIP = 40, GRIP_AT = 20;
    /** «Чужая клятва» ereb_hand_foreign_oath 1.4 s: mark 0.6. */
    public static final int OATH = 28, OATH_AT = 12;
    /** «Тысяча отражений» ereb_hand_thousand_reflections 2.6 s: mirrors 0.6, strikes 1.5; one mirror after another every STRIKE_GAP;
     * a reflection: ereb_hand_reflection_strike 1.0 s (hit 0.45). */
    public static final int THOUSAND = 52, MIRRORS_AT = 12, STRIKES_AT = 30, STRIKE_GAP = 6, REFL = 20, REFL_HIT = 9;
    /** «Дезинтеграция: Реплика»: ereb_hand_replica_break 2.3 s, break 0.95, speak 1.55; 2 s after the hold began. */
    public static final int REPLICA_DELAY = 40, REPLICA_ANIM = 46, REPLICA_BREAK = 19, REPLICA_SPEAK = 31;
    /** The finisher ereb_hand_finisher 3.6 s: grab 0.6, (lift till 1.2), squeeze 1.5, shatter 2.1 (dies the tick after), release 2.4. */
    public static final int FINISHER = 72, FIN_GRAB = 12, FIN_LIFTED = 24, FIN_SQUEEZE = 30, FIN_SHATTER = 42, FIN_KILL = 43, FIN_CAM = 44;
    /** The finisher's hold point after the lift (right, up, forward). */
    public static final double FIN_RIGHT = 0.5, FIN_UP = 1.45, FIN_FWD = 1.38;

    // ---------------------------------------------------------------- geometry (Minecraft yaw: forward = (-sin, cos), right = (-cos, -sin))

    public static double[] forward(double yawDeg) {
        double a = Math.toRadians(yawDeg);
        return new double[] {-Math.sin(a), Math.cos(a)};
    }

    /** His right hand side, flat. */
    public static double[] right(double yawDeg) {
        double a = Math.toRadians(yawDeg);
        return new double[] {-Math.cos(a), -Math.sin(a)};
    }

    /** Yaw (degrees) looking from (x0,z0) to (x1,z1). */
    public static float yawTo(double x0, double z0, double x1, double z1) {
        return (float) (Math.toDegrees(Math.atan2(z1 - z0, x1 - x0)) - 90);
    }

    /** A point relative to someone at (x,z) looking along yaw: `right` to its right, `fwd` forward: {dx, dz}. */
    public static double[] local(double yawDeg, double right, double fwd) {
        double[] f = forward(yawDeg), r = right(yawDeg);
        return new double[] {r[0] * right + f[0] * fwd, r[1] * right + f[1] * fwd};
    }

    /** True if a point at (dx,dz) from someone looking along yaw is within `halfDeg` of its front. */
    public static boolean inArc(double dx, double dz, double yawDeg, double halfDeg) {
        double len = Math.sqrt(dx * dx + dz * dz);
        if (len < 1e-6) return true;
        double[] f = forward(yawDeg);
        return (dx * f[0] + dz * f[1]) / len >= Math.cos(Math.toRadians(halfDeg));
    }

    /** «Стеклянная хватка»: inside the cone (full angle `deg`, length `range`) in front of him. */
    public static boolean inCone(double dx, double dz, double yawDeg, double deg, double range) {
        return dx * dx + dz * dz <= range * range && inArc(dx, dz, yawDeg, deg / 2);
    }

    /** A melee pause between min and max ticks. */
    public static int meleePause(int min, int max, double rnd01) {
        int lo = Math.min(min, max), hi = Math.max(min, max);
        return lo + (int) Math.floor(rnd01 * (hi - lo + 1 - 1e-9));
    }

    /** Ease in-out (sine) of k in 0..1. */
    public static double ease(double k) {
        k = Math.max(0, Math.min(1, k));
        return 0.5 - 0.5 * Math.cos(Math.PI * k);
    }

    /** The finisher: where the victim is at tick t, as a fraction 0..1 of the way from where it was struck to the hold point. */
    public static double finisherLift(int t) {
        if (t <= FIN_GRAB) return 0;
        return ease((t - FIN_GRAB) / (double) (FIN_LIFTED - FIN_GRAB));
    }

    /** «Длань Лжи»: the giant hand's height over its final place at tick t of its fall (GIANT_FROM → 0 in HOL_FALL ticks). */
    public static double giantFall(int t) {
        return GIANT_FROM * (1 - ease(t / (double) HOL_FALL));
    }

    // ---------------------------------------------------------------- choices

    /**
     * Which of n things are «real» (the rest are false): exactly min(real, n) of them, picked by the given random numbers (one per
     * thing, 0..1: the `real` smallest are real). Used by the doubles, «Ложное пламя» (real = circles − decoys), «Тысяча отражений».
     */
    public static boolean[] pickReal(int n, int real, double[] rnd) {
        boolean[] out = new boolean[Math.max(0, n)];
        int k = Math.max(0, Math.min(real, n));
        Integer[] idx = new Integer[n];
        for (int i = 0; i < n; i++) idx[i] = i;
        java.util.Arrays.sort(idx, (a, b) -> Double.compare(rnd[a], rnd[b]));
        for (int i = 0; i < k; i++) out[idx[i]] = true;
        return out;
    }

    /** «Ложное пламя»: circle i goes to player i mod players (the first circles under the players, the rest next to them); -1 if none. */
    public static int flameOwner(int i, int players) {
        return players <= 0 ? -1 : i % players;
    }

    /** The mask texture after the mend: cracked if phase 3 already came (phase index 2), else mended. 0 own, 1 mended, 2 cracked. */
    public static int maskAfterMend(int phase) {
        return phase >= 2 ? 2 : 1;
    }

    /** «Падение маски»: where shard i of n circles at tick t: {x, y, z} from the arena centre (radius r, height 1.5–3, slow). */
    public static double[] shardOrbit(int i, int n, int t, double r) {
        double a = Math.PI * 2 * i / Math.max(1, n) + t * 0.012 * (i % 2 == 0 ? 1 : -1);
        double rr = r * (0.55 + 0.35 * ((i * 7) % 5) / 4.0);
        double y = 2.25 + 0.75 * Math.sin(t * 0.05 + i * 1.7);
        return new double[] {Math.cos(a) * rr, y, Math.sin(a) * rr};
    }

    /** True if a direction at `angleDeg` (yaw of the point from him) faces one of the mirrors (yaws) within halfWidth degrees. */
    public static boolean facesMirror(double angleDeg, double[] mirrorYaws, double halfWidth) {
        for (double m : mirrorYaws) {
            double d = ((angleDeg - m) % 360 + 540) % 360 - 180;
            if (Math.abs(d) <= halfWidth) return true;
        }
        return false;
    }

    /** The mirror walls' yaws around him (count of them, evenly, turned by `turn`). */
    public static double[] mirrorYaws(int count, double turn) {
        double[] out = new double[Math.max(0, count)];
        for (int i = 0; i < out.length; i++) out[i] = turn + 360.0 * i / count;
        return out;
    }

    /** Points of n mirrors on a circle of radius r round (cx, cz): {x, z} each, the first at angle a0 (radians). */
    public static List<double[]> ring(int n, double r, double cx, double cz, double a0) {
        List<double[]> out = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            double a = a0 + Math.PI * 2 * i / n;
            out.add(new double[] {cx + Math.cos(a) * r, cz + Math.sin(a) * r});
        }
        return out;
    }

    /** True if moving from distance `before` to `after` (from the arena centre) crossed the wall at r (either way). */
    public static boolean wallCrossed(double before, double after, double r) {
        return before < r && after >= r || before >= r && after < r;
    }

    /** «Длань»: the grab breaks when the allies dealt at least `need` to him while it held. */
    public static boolean grabBroken(double dealtByAllies, double need) {
        return dealtByAllies >= need;
    }

    /** «Чужая клятва»: the share that goes to the ally, capped. */
    public static double oathShare(double dealt, double share, double cap) {
        return Math.max(0, Math.min(dealt * share, cap));
    }
}
