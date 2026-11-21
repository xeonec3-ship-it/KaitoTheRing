package ru.pohsmp.core.boss;

/**
 * Procedural cloth on Iron's walk (the coat tails of both Erebs, the cape of the Hand of Lies): pure math, GeckoLib axes, radians.
 * <p>
 * GeckoLib bakes a .geo/.animation rotation x as {@code rotX = −x} and renders {@code Axis.XP.rotation(rotX)} with the model front at
 * −z, so for a bone hanging from its pivot <b>rotX &gt; 0 swings its lower end forward</b>, rotX &lt; 0 — back. The visual letters
 * (T30, T31) give their formulas in Bedrock/Blockbench axes (+ = back) and with the rest angles included; the rest angles already sit in
 * the .geo, so here only the walk deltas are returned, with the sign turned to GeckoLib's.
 * <p>
 * Every value is a pure function of this frame's walk (no state): the deltas are pushed through Iron's {@code transformStack}, which
 * puts the bones back to their rest pose before the next frame — nothing piles up frame after frame, nothing needs a reset on spawn,
 * teleport or when an animation starts, and every delta is clamped.
 */
public final class ClothSway {
    private ClothSway() {}

    public static final float DEG = (float) (Math.PI / 180);
    /** Iron's legs: {@code cos(speed·0.6662 [+π])·1.4·amount·0.75}, amount ≤ 1 — at most 60° either way. */
    public static final float LEG_MAX = 1.4f * 0.75f;
    /** Iron's legs of a rider who sits (81° forward). */
    public static final float LEG_SIT = 1.4137167f;
    /** Clamp for the coat tails: they follow a leg, never further than it goes (45°). */
    public static final float COAT_MAX = 45 * DEG;
    /** Clamp for the cape (and its two lower bones): it only ever lifts back, at most 20°. */
    public static final float CAPE_MAX = 20 * DEG;

    /** Iron's procedural rotX of a leg (GeckoLib axes, + = forward) for a walk amount (0..1, clamped) and walk position. */
    public static float ironLeg(float amount, float position, boolean right) {
        float a = clamp01(amount);
        float phase = position * 0.6662f + (right ? 0 : (float) Math.PI);
        return finite((float) Math.cos(phase) * 1.4f * a * 0.75f);
    }

    /**
     * Iron's procedural leg as rendered: rotX as {@link #ironLeg} plus its offset — up {@code cos(φ)·4·0.75·amount}, back
     * {@code −sin(φ)·4·amount·forward} (φ = position·0.6662, +π for the left leg; forward = facing·motion, −1..1).
     */
    public static Leg ironWalk(float amount, float position, boolean right, float forward) {
        float a = clamp01(amount);
        float phase = position * 0.6662f - (right ? 0 : (float) Math.PI);
        float lateral = -(float) Math.sin(phase) * 4 * a;
        return new Leg(ironLeg(amount, position, right), finite((float) Math.cos(phase) * 4 * 0.75f * a),
                finite(lateral * clamp(finite(forward), -1, 1)));
    }

    /** Front tail: only after a leg going forward (rotX &gt; 0), 0.55 of it — the thigh pushes it, it never cuts through the leg. */
    public static float coatFront(float legRotX) {
        return clamp(Math.max(0, finite(legRotX)) * 0.55f, 0, COAT_MAX);
    }

    /** Back tail: only after a leg going back (rotX &lt; 0), 0.4 of it. */
    public static float coatBack(float legRotX) {
        return clamp(Math.min(0, finite(legRotX)) * 0.4f, -COAT_MAX, 0);
    }

    /**
     * The three cape bones (cape → cape_mid → cape_low, each a child of the one above): the walk lifts the top back (0.25 of the leg
     * swing), the middle follows (0.15), the low part sags 1° and the middle 2° more back than the rest pose — a wave, always back,
     * away from the torso. GeckoLib axes: all ≤ 0.
     */
    public static float[] cape(float rightLeg, float leftLeg) {
        float legs = Math.max(Math.abs(finite(rightLeg)), Math.abs(finite(leftLeg)));
        return new float[] {
                -clamp(legs * 0.25f, 0, CAPE_MAX),
                -clamp(2 * DEG + legs * 0.15f, 0, CAPE_MAX),
                -1 * DEG};
    }

    // ------------------------------------------------------------------ geometry: the side view (y up, z back), model pixels
    /** A leg as rendered: Iron's/animation rotX (GeckoLib axes) and the bone offset (posY up, posZ back). */
    public record Leg(float rotX, float posY, float posZ) {
        public static final Leg REST = new Leg(0, 0, 0);
    }

    /** Leg bones of both Erebs (.geo): pivot y 12, z 0; 12 px long; the leg ±2 px deep, the boot (its lower 5 px) ±2.3 px. */
    public static final float LEG_PIVOT_Y = 12, LEG_LEN = 12, LEG_HALF = 2, BOOT_HALF = 2.3f, BOOT_TOP = 7;
    /** coat_front_r/l: pivot (y 12.75, z −2.6), the panel z −2.85..−2.35 down to y 1.5; rest x −3° (Bedrock) = rotX +3°. */
    public static final float FRONT_Y = 12.75f, FRONT_Z = -2.6f, FRONT_LEN = 11.25f, FRONT_REST = 3 * DEG;
    /** coat_back_r/l: pivot (12.75, 2.6), the panel z 2.35..2.85 down to y 1.0; rest x 5° = rotX −5°. */
    public static final float BACK_Y = 12.75f, BACK_Z = 2.6f, BACK_LEN = 11.75f, BACK_REST = -5 * DEG;
    /** Half thickness of every panel (0.5 px cubes around the pivot line). */
    public static final float PANEL = 0.25f;
    /** cape → cape_mid → cape_low (Hand of Lies): pivots y 23 / 16.5 / 10.5 at z 3.25, the low panel down to y 4.5; rest x 5° on cape. */
    public static final float CAPE_Y = 23, CAPE_Z = 3.25f, CAPE_REST = -5 * DEG;
    public static final float[] CAPE_LEN = {6.5f, 6.0f, 6.0f};
    /** Clearance kept between cloth and a leg / tail (px). */
    public static final float GAP = 0.25f;
    /** Hard limits of the solved angles (GeckoLib axes, deltas from rest). */
    public static final float COAT_LIMIT = 80 * DEG, CAPE_LIMIT = 75 * DEG;

    /**
     * Everything for one frame: deltas from the rest pose — rotX of coat_front_r, coat_front_l, coat_back_r, coat_back_l, cape,
     * cape_mid, cape_low (GeckoLib axes, radians), then the z offsets (px, + back) of coat_front_r, coat_front_l, coat_back_r,
     * coat_back_l. The letter's swing first ({@link #coatFront}, {@link #coatBack}, {@link #cape}). Iron's walk also slides a leg up to
     * 4 px forward and back at the hip and lifts the leg going forward by up to 3 px — the thigh then stands right at a tail's hinge,
     * where no turn can clear it: the thigh pushes the tail's top along (only to its own side: the front ones forward, the back ones
     * back, {@link #hingeShift}), so it lies on the thigh instead of flipping up. Then each panel turns just as far as it must so no point of its leg (as rendered) is on its side
     * of the panel — the front tails before the shin, the back tails and the cape behind the calf and the back tails. Pure and clamped.
     */
    public static float[] solve(Leg right, Leg left) {
        right = sane(right);
        left = sane(left);
        float zfr = hingeShift(right, FRONT_Y, FRONT_Z, -1), zfl = hingeShift(left, FRONT_Y, FRONT_Z, -1);
        float zbr = hingeShift(right, BACK_Y, BACK_Z, 1), zbl = hingeShift(left, BACK_Y, BACK_Z, 1);
        float fr = front(right, zfr), fl = front(left, zfl), br = back(right, zbr), bl = back(left, zbl);
        float[] cape = cape(right.rotX(), left.rotX());
        cape[0] = capeClear(cape, right, left, br, bl, zbr, zbl);
        return new float[] {fr, fl, br, bl, cape[0], cape[1], cape[2], zfr, zfl, zbr, zbl};
    }

    /** Front tail delta over its leg (hinge slid by dz): the letter's swing, or the least turn that keeps the shin behind it. */
    static float front(Leg leg, float dz) {
        float want = FRONT_REST + clamp(coatFront(leg.rotX()), 0, COAT_LIMIT);
        float a = want;
        for (float[] q : legFace(leg, -1)) a = Math.max(a, need(q[0] - FRONT_Y, q[1] - (FRONT_Z + dz), FRONT_LEN, want));
        return clamp(a - FRONT_REST, 0, COAT_LIMIT);
    }

    /** Soft edge (px) past a panel's reach and above its hinge where a leg point's demand fades out — no snap when the toe passes the hem. */
    public static final float FADE = 2;

    /**
     * What one point (dy, dz from the hinge) demands of a panel hanging there (its far face {@link #PANEL} behind the pivot line): the
     * least rotX leaving the point {@link #GAP} beyond that face — f(θ) = dz·cosθ − dy·sinθ ≥ PANEL + GAP — continuous in the point:
     * in full within the panel's reach and below the hinge, fading to {@code base} over {@link #FADE} px past them.
     */
    static float need(float dy, float dz, float len, float base) {
        float m = PANEL + GAP;
        float rho = (float) Math.hypot(dy, dz);
        float reach = (float) Math.hypot(len, BOOT_HALF + m);
        float w = Math.min(clamp01(1 - (rho - reach) / FADE), clamp01(1 - dy / FADE));
        if (w <= 0) return base;
        float t = rho <= m ? COAT_LIMIT + FRONT_REST : -(float) Math.atan2(dy, dz) - (float) Math.acos(m / rho);
        return t <= base ? base : base + (t - base) * w;
    }

    /** Hinge zone: leg points from this far below a tail's hinge to this far above it push the hinge along (px). */
    public static final float HINGE_ZONE = 3;
    /** Most a hinge slides with the thigh (px): Iron's slide (4) plus a thigh lifted and swung to the hinge's height. */
    public static final float HINGE_MAX = 10;

    /**
     * How far a tail's hinge (y, z) must slide along z — toward its side (−1 front, +1 back), never the other way: at least Iron's slide
     * of the leg, and so far that the leg face on that side keeps {@link #PANEL} + {@link #GAP} off the panel within {@link #HINGE_ZONE}
     * of the hinge's height.
     */
    static float hingeShift(Leg leg, float y, float z, int side) {
        float need = side < 0 ? Math.min(0, leg.posZ()) : Math.max(0, leg.posZ());   // Iron's slide of the whole leg
        for (float[] q : legFace(leg, side)) {
            if (q[0] < y - HINGE_ZONE || q[0] > y + HINGE_ZONE) continue;
            float shift = q[1] + side * (PANEL + GAP) - z;   // where the hinge must be for this point to sit just beyond the panel
            need = side < 0 ? Math.min(need, shift) : Math.max(need, shift);
        }
        return clamp(need, -HINGE_MAX, HINGE_MAX);
    }

    /** Back tail delta: the letter's swing, or the least turn back that keeps the calf in front of it. Mirror of front (z → −z). */
    static float back(Leg leg, float dz) {
        float want = BACK_REST + clamp(coatBack(leg.rotX()), -COAT_LIMIT, 0);
        float a = -want;
        for (float[] q : legFace(leg, 1)) a = Math.max(a, need(q[0] - BACK_Y, -(q[1] - (BACK_Z + dz)), BACK_LEN, -want));
        return clamp(-a - BACK_REST, -COAT_LIMIT, 0);
    }

    /**
     * Is any point, within the panel's length, not at least {@link #GAP} beyond its face on the given side (+1: behind it, -1: in front)?
     * The panel hangs from (py, pz) at absolute rotX a, {@link #PANEL} thick each way. Points above the hinge or below the hem never
     * touch it.
     */
    static boolean wrongSide(float py, float pz, float a, float len, int side, float[][] pts) {
        float c = (float) Math.cos(a), s = (float) Math.sin(a);
        for (float[] q : pts) {
            float dy = q[0] - py, dz = q[1] - pz;
            float ly = dy * c + dz * s, lz = -dy * s + dz * c;   // into the panel's frame (rotation by -a)
            if (ly <= 0 && ly >= -len && side * lz < PANEL + GAP) return true;
        }
        return false;
    }

    /** Points of a leg face (side −1 front, +1 back) from the hip to the sole, as rendered (pivot + offset + rotation): {y, z}. */
    public static float[][] legFace(Leg leg, int side) {
        int n = 25;
        float[][] out = new float[n][];
        float c = (float) Math.cos(leg.rotX()), s = (float) Math.sin(leg.rotX());
        for (int i = 0; i < n; i++) {
            float y = -LEG_LEN * i / (n - 1);
            float z = side * (-y >= BOOT_TOP ? BOOT_HALF : LEG_HALF);
            out[i] = new float[] {LEG_PIVOT_Y + leg.posY() + y * c - z * s, leg.posZ() + y * s + z * c};
        }
        return out;
    }

    /** Side view of the cape chain for the three deltas: {start y, start z, absolute rotX} of each panel. */
    public static float[][] capeChain(float c0, float c1, float c2) {
        float[][] out = new float[3][];
        float y = CAPE_Y, z = CAPE_Z, a = CAPE_REST;
        float[] d = {c0, c1, c2};
        for (int i = 0; i < 3; i++) {
            a += d[i];
            out[i] = new float[] {y, z, a};
            y -= CAPE_LEN[i] * (float) Math.cos(a);
            z -= CAPE_LEN[i] * (float) Math.sin(a);
        }
        return out;
    }

    /** The cape's top delta, turned back (1° steps) until no point of a leg back face or a back tail is behind its front face. */
    static float capeClear(float[] cape, Leg right, Leg left, float br, float bl, float zbr, float zbl) {
        java.util.List<float[]> pts = new java.util.ArrayList<>();
        java.util.Collections.addAll(pts, legFace(right, 1));
        java.util.Collections.addAll(pts, legFace(left, 1));
        java.util.Collections.addAll(pts, panel(BACK_Y, BACK_Z + zbr, BACK_REST + br, BACK_LEN, PANEL));
        java.util.Collections.addAll(pts, panel(BACK_Y, BACK_Z + zbl, BACK_REST + bl, BACK_LEN, PANEL));
        float[][] arr = pts.toArray(new float[0][]);
        float c0 = cape[0];
        while (c0 > -CAPE_LIMIT && capeHit(capeChain(c0, cape[1], cape[2]), arr)) c0 -= DEG;
        return clamp(c0, -CAPE_LIMIT, 0);
    }

    static boolean capeHit(float[][] chain, float[][] pts) {
        for (int i = 0; i < 3; i++)
            if (wrongSide(chain[i][0], chain[i][1], chain[i][2], CAPE_LEN[i], -1, pts)) return true;
        return false;
    }

    /** Points of a panel's face (local z = face) hanging from (y, z) at absolute rotX a: {y, z}. */
    public static float[][] panel(float py, float pz, float a, float len, float face) {
        int n = 13;
        float[][] out = new float[n][];
        float c = (float) Math.cos(a), s = (float) Math.sin(a);
        for (int i = 0; i < n; i++) {
            float y = -len * i / (n - 1);
            out[i] = new float[] {py + y * c - face * s, pz + y * s + face * c};
        }
        return out;
    }

    static Leg sane(Leg l) {
        if (l == null) return Leg.REST;
        return new Leg(clamp(finite(l.rotX()), -LEG_SIT, LEG_SIT), clamp(finite(l.posY()), -8, 8), clamp(finite(l.posZ()), -8, 8));
    }

    /** The ghost hand's float over the shoulder: ±0.6 px (an offset, not added to the last frame's position). */
    public static float handFloat(float ageTicks) {
        return 0.6f * (float) Math.sin(finite(ageTicks) * 0.08f);
    }

    static float clamp(float v, float lo, float hi) {
        return v < lo ? lo : Math.min(v, hi);
    }

    static float clamp01(float v) {
        return clamp(finite(v), 0, 1);
    }

    static float finite(float v) {
        return Float.isFinite(v) ? v : 0;
    }
}
