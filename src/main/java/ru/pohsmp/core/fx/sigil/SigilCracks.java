package ru.pohsmp.core.fx.sigil;

import ru.pohsmp.core.fx.sigil.SigilDef.Cracks;

/**
 * Dissolve mode {@code cracks} (T09, docs/sigils.md "Распад трещинами"): cracks spread from the centre, the sigil breaks into
 * shards along them, the shards part a little, then fall one after another (outer ring first), tumbling, and go out; dust
 * trickles from the cracks. Pure math, the same in tools/sigil_preview.html.
 *
 * <p>Plane units as everywhere: (x, y) / angles in the sigil plane, unit = sigil radius (layer radius 1). {@code reach} =
 * {@link SigilDef#reach()} — the cracks run to the outermost layer. Angles in degrees, counter-clockwise from +u.
 * Shards are the same for every layer (the sigil breaks as one slab): shard (k, j) is the region between radial cracks k and k+1,
 * from {@link #ringRadius ringRadius(j)} to ringRadius(j + 1). Times: ticks since the sigil started; {@code stopAt} = dissolve start.
 */
public final class SigilCracks {
    private SigilCracks() {}

    /** Knots along a radial crack (zigzag points), evenly from the centre to reach. */
    public static final int KNOTS = 8;

    public static int shardCount(Cracks c) {
        return c.count() * (c.rings() + 1);
    }

    private static double sector(Cracks c) {
        return 360.0 / c.count();
    }

    /** Base angle of radial crack k (0..count; k = count is crack 0 one turn later): even spacing, shifted by ±irregular/2 sector. */
    public static double edge(Cracks c, int seed, int k) {
        int kk = Math.floorMod(k, c.count()), turns = Math.floorDiv(k, c.count());
        double s = sector(c);
        return (SigilHit.rnd(seed, 999) + kk + c.irregular() * (SigilHit.rnd(seed, 1000 + kk) - 0.5)) * s + 360.0 * turns;
    }

    /** Effective jag (share of a sector): never so large that neighbour cracks cross. */
    public static double jag(Cracks c) {
        return Math.min(c.jag(), (1 - c.irregular()) * 0.9);
    }

    /** Angle of radial crack k at radius r: the base angle plus a zigzag (knots linearly joined; 0 at the centre). */
    public static double crackAngle(Cracks c, int seed, int k, double r, double reach) {
        int kk = Math.floorMod(k, c.count());
        double x = Math.max(0, Math.min(KNOTS, r / reach * KNOTS));
        int i = Math.min(KNOTS - 1, (int) Math.floor(x));
        double f = x - i;
        double o = knot(c, seed, kk, i) * (1 - f) + knot(c, seed, kk, i + 1) * f;
        return edge(c, seed, k) + o * jag(c) * sector(c);
    }

    private static double knot(Cracks c, int seed, int k, int i) {
        return i == 0 ? 0 : SigilHit.rnd(seed, 2000 + k * 16 + i) - 0.5;
    }

    /** Radius of ring boundary j (0 = centre, rings + 1 = reach); ring cracks are circles at j = 1..rings. */
    public static double ringRadius(Cracks c, int j, double reach) {
        return reach * j / (c.rings() + 1);
    }

    private static double crackTicks(SigilDef def, Cracks c) {
        return c.crackTime() * def.dissolve().duration();
    }

    /** Ticks after the stop when radial crack k starts from the centre (scatter order, all within the first 45 % of crackTime). */
    public static double crackStart(SigilDef def, Cracks c, int k) {
        int n = c.count();
        return 0.45 * crackTicks(def, c) * SigilTimeline.pieceRank(SigilDef.PieceOrder.SCATTER, k, n) / Math.max(1, n - 1);
    }

    /** How far radial crack k has run, share of reach 0..1 (easeOutCubic over 55 % of crackTime). */
    public static double crackReach(SigilDef def, int k, double t, double stopAt) {
        Cracks c = def.dissolve().cracksOrNull();
        if (c == null || Double.isNaN(stopAt)) return 0;
        double grow = 0.55 * crackTicks(def, c);
        return Easing.EASE_OUT_CUBIC.apply(SigilHit.clamp01((t - stopAt - crackStart(def, c, Math.floorMod(k, c.count()))) / grow));
    }

    /**
     * Ring crack j (1..rings): share 0..1 of every arc between two radial cracks that is open; it opens from both radial
     * cracks towards the middle of the arc (easeInOutSine from crackTime·(0.25 + 0.35·j/(rings+1)) for 40 % of crackTime).
     */
    public static double ringCrack(SigilDef def, int j, double t, double stopAt) {
        Cracks c = def.dissolve().cracksOrNull();
        if (c == null || Double.isNaN(stopAt) || j < 1 || j > c.rings()) return 0;
        double ct = crackTicks(def, c), start = ct * (0.25 + 0.35 * j / (c.rings() + 1));
        return Easing.EASE_IN_OUT_SINE.apply(SigilHit.clamp01((t - stopAt - start) / (0.4 * ct)));
    }

    /**
     * Brightness of the crack lines 0..glow: up in the first quarter of crackTime, flickers a little (±12 %, sin(1.7 t)), out over
     * the first half of the falling time.
     */
    public static double crackGlow(SigilDef def, double t, double stopAt) {
        Cracks c = def.dissolve().cracksOrNull();
        if (c == null || Double.isNaN(stopAt) || t < stopAt) return 0;
        double ct = crackTicks(def, c), d = def.dissolve().duration();
        double in = SigilHit.clamp01((t - stopAt) / Math.max(1, 0.25 * ct));
        double out = 1 - SigilHit.clamp01((t - stopAt - ct) / Math.max(1, 0.5 * (d - ct)));
        return c.glow() * in * out * (0.88 + 0.12 * Math.sin(1.7 * t));
    }

    /**
     * A shard: draw its region at rest, rotate by {@code spin} around the normal and by {@code tilt} around the tangent (both
     * through its centre at angle {@code centerAngle}, radius {@code centerRadius}), move it {@code radial} outward along
     * centerAngle and {@code drop} straight down in the world (negative = up); all in plane units (× current sigil radius).
     */
    public record Shard(double alpha, double centerAngle, double centerRadius, double radial, double drop, double tilt, double spin,
                        double brightness, double fall) {}

    /** Ticks after the stop when shard (k, j) starts to fall: outer ring first, scatter order inside a ring, spread over the rest. */
    public static double fallStart(SigilDef def, Cracks c, int k, int j) {
        double d = def.dissolve().duration(), ct = crackTicks(def, c), ft = c.fallTime() * d;
        double window = Math.max(0, d - ct - ft);
        int n = shardCount(c), rank = (c.rings() - j) * c.count() + SigilTimeline.pieceRank(SigilDef.PieceOrder.SCATTER, k, c.count());
        return ct + (n > 1 ? window * rank / (n - 1) : 0);
    }

    /**
     * s = (t − stop − fallStart) / (fallTime · duration), 0..1:
     * radial = gap · easeOutCubic(parting over the last 40 % of crackTime) + push · s · (0.7..1.3);
     * drop = fall · s² − pop · 4s(1 − s) · (0.6..1.4)  (hops up first, then falls);
     * tilt = tumble · (0.55..1) · s^1.3 · (±1); spin = spin · (−1..1) · s;
     * alpha = 1 − ((s − 0.3) / 0.7)² after s = 0.3; brightness = 1 + 0.4 · crackGlow/glow + 0.6 · (flash for 4 ticks as it breaks off).
     */
    public static Shard shard(SigilDef def, int seed, int k, int j, double t, double stopAt) {
        Cracks c = def.dissolve().cracksOrNull();
        double reach = def.reach();
        double r0 = ringRadius(c, j, reach), r1 = ringRadius(c, j + 1, reach), rm = (r0 + r1) / 2;
        double ca = (crackAngle(c, seed, k, rm, reach) + crackAngle(c, seed, k + 1, rm, reach)) / 2;
        if (Double.isNaN(stopAt) || t < stopAt) return new Shard(1, ca, rm, 0, 0, 0, 0, 1, 0);
        double ct = crackTicks(def, c), ft = c.fallTime() * def.dissolve().duration();
        double since = t - stopAt, start = fallStart(def, c, k, j);
        double s = SigilHit.clamp01((since - start) / ft);
        int id = k * 4 + j;
        double ra = SigilHit.rnd(seed, 3000 + id), rb = SigilHit.rnd(seed, 3100 + id), rc = SigilHit.rnd(seed, 3200 + id),
                rd = SigilHit.rnd(seed, 3300 + id);
        double part = Easing.EASE_OUT_CUBIC.apply(SigilHit.clamp01((since - 0.6 * ct) / (0.4 * ct)));
        double radial = c.gap() * part + c.push() * s * (0.7 + 0.6 * ra);
        double drop = c.fall() * s * s - c.pop() * 4 * s * (1 - s) * (0.6 + 0.8 * rb);
        double side = rc < 0.5 ? -1 : 1;
        double tilt = c.tumble() * (0.55 + 0.45 * rd) * Math.pow(s, 1.3) * side;
        double spin = c.spin() * (2 * rc - 1) * s;
        double fade = SigilHit.clamp01((s - 0.3) / 0.7);
        double g = c.glow() > 0 ? crackGlow(def, t, stopAt) / c.glow() : 0;
        double snap = since >= start ? Math.max(0, 1 - (since - start) / 4) : 0;
        return new Shard(1 - fade * fade, ca, rm, radial, drop, tilt, spin, 1 + 0.4 * g + 0.6 * snap, s);
    }

    /**
     * Dust mote i (0..dust−1): born on crack (i mod count) when the crack reaches its spot (share u = 0.15..1 of reach, plus up
     * to 0.35·crackTime later), then drifts outward and falls (drop = fall · 0.6 · (age / fallTicks)²), lives 10..20 ticks.
     * Position in plane units: angle, radius; drop straight down in the world. size — half-size in plane units.
     */
    public record Mote(double angle, double radius, double drop, double alpha, double size) {}

    public static Mote dust(SigilDef def, int seed, int i, double t, double stopAt) {
        Cracks c = def.dissolve().cracksOrNull();
        if (c == null || Double.isNaN(stopAt)) return new Mote(0, 0, 0, 0, 0);
        double reach = def.reach(), ct = crackTicks(def, c), ft = c.fallTime() * def.dissolve().duration();
        int k = i % c.count();
        double u = 0.15 + 0.85 * SigilHit.rnd(seed, 5000 + i);
        double born = crackStart(def, c, k) + 0.55 * ct * (1 - Math.cbrt(1 - u)) + 0.35 * ct * SigilHit.rnd(seed, 5100 + i);
        double life = 10 + 10 * SigilHit.rnd(seed, 5200 + i), age = t - stopAt - born;
        if (age < 0 || age > life) return new Mote(0, 0, 0, 0, 0);
        double r = u * reach + 0.06 * age / life;
        double a = crackAngle(c, seed, k, u * reach, reach);
        double fade = 1 - age / life;
        return new Mote(a, r, c.fall() * 0.6 * (age / ft) * (age / ft), fade * Math.min(1, age / 2 + 0.3), 0.012 + 0.012 * SigilHit.rnd(seed, 5300 + i));
    }

    /** Shard index k·(rings+1) + j that holds plane point (x, y); for geometry that is not drawn shard by shard (arcs). */
    public static int shardAt(SigilDef def, int seed, double x, double y) {
        Cracks c = def.dissolve().cracksOrNull();
        double reach = def.reach(), r = Math.hypot(x, y);
        int j = Math.min(c.rings(), (int) Math.floor(r / reach * (c.rings() + 1)));
        double a = Math.toDegrees(Math.atan2(y, x));
        double a0 = crackAngle(c, seed, 0, r, reach);
        a = a0 + Math.floorMod((long) Math.floor((a - a0) * 1e6), 360_000_000L) / 1e6;   // into [a0, a0 + 360)
        int k = c.count() - 1;
        for (int q = 1; q < c.count(); q++)
            if (a < crackAngle(c, seed, q, r, reach)) {
                k = q - 1;
                break;
            }
        return k * (c.rings() + 1) + j;
    }

    /** True while the sigil is breaking: the renderer draws shards instead of whole layers. */
    public static boolean breaking(SigilDef def, double t, double stopAt) {
        return def.dissolve().cracksOrNull() != null && !Double.isNaN(stopAt) && t >= stopAt;
    }
}
