package ru.pohsmp.core.fx;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;
import ru.pohsmp.core.fx.FxMath.Vec;

/**
 * Shapes of the line-like elements of docs/fx.md without Minecraft classes: lightning bolts, slash arcs, sagging chains,
 * vortex spirals, wing flaps, slash timing. Everything random is taken from a seed, so every client builds the same shape.
 */
public final class FxShapes {
    private FxShapes() {}

    // ---------------------------------------------------------------- vectors

    public static Vec sub(Vec a, Vec b) {
        return new Vec(a.x() - b.x(), a.y() - b.y(), a.z() - b.z());
    }

    public static double len(Vec a) {
        return Math.sqrt(a.x() * a.x() + a.y() * a.y() + a.z() * a.z());
    }

    public static Vec norm(Vec a) {
        double l = len(a);
        return l < 1e-9 ? new Vec(0, 1, 0) : a.scale(1 / l);
    }

    public static Vec cross(Vec a, Vec b) {
        return new Vec(a.y() * b.z() - a.z() * b.y(), a.z() * b.x() - a.x() * b.z(), a.x() * b.y() - a.y() * b.x());
    }

    public static double dot(Vec a, Vec b) {
        return a.x() * b.x() + a.y() * b.y() + a.z() * b.z();
    }

    public static Vec lerp(Vec a, Vec b, double t) {
        return a.add(sub(b, a).scale(t));
    }

    /** Two unit vectors perpendicular to d and to each other. */
    public static Vec[] perp(Vec d) {
        Vec n = norm(d);
        Vec ref = Math.abs(n.y()) < 0.9 ? new Vec(0, 1, 0) : new Vec(1, 0, 0);
        Vec a = norm(cross(n, ref));
        return new Vec[] {a, norm(cross(n, a))};
    }

    // ---------------------------------------------------------------- lightning

    /** One straight piece of a bolt; depth 0 is the main channel, branches are 1 and deeper (thinner, dimmer). */
    public record Seg(Vec a, Vec b, int depth) {}

    /**
     * A bolt from `from` to `to` by midpoint displacement: `detail` halvings (2^detail pieces), each midpoint pushed sideways
     * by up to `jag` × the piece length; `branches` forks leave the main channel at random points and wander off at an angle.
     * Ends of the main channel are exactly `from` and `to`.
     */
    public static List<Seg> lightning(long seed, Vec from, Vec to, double jag, int branches, int detail) {
        SplittableRandom r = new SplittableRandom(seed);
        List<Vec> main = bolt(r, from, to, jag, detail);
        List<Seg> out = new ArrayList<>();
        for (int i = 0; i + 1 < main.size(); i++) out.add(new Seg(main.get(i), main.get(i + 1), 0));
        double total = len(sub(to, from));
        for (int b = 0; b < branches; b++) {
            int at = 1 + r.nextInt(Math.max(1, main.size() - 2));
            Vec start = main.get(Math.min(at, main.size() - 1));
            Vec dir = norm(sub(to, from));
            Vec[] side = perp(dir);
            double ang = (r.nextDouble() * 2 - 1) * Math.PI, spread = 0.5 + r.nextDouble() * 0.7;
            Vec off = side[0].scale(Math.cos(ang)).add(side[1].scale(Math.sin(ang)));
            Vec bdir = norm(dir.add(off.scale(spread)));
            double rest = total * (1 - (double) at / main.size());
            Vec end = start.add(bdir.scale(Math.max(0.3, rest * (0.25 + r.nextDouble() * 0.35))));
            List<Vec> br = bolt(r, start, end, jag * 1.2, Math.max(1, detail - 2));
            for (int i = 0; i + 1 < br.size(); i++) out.add(new Seg(br.get(i), br.get(i + 1), 1));
        }
        return out;
    }

    private static List<Vec> bolt(SplittableRandom r, Vec from, Vec to, double jag, int detail) {
        List<Vec> pts = new ArrayList<>(List.of(from, to));
        Vec[] side = perp(sub(to, from));
        for (int d = 0; d < detail; d++) {
            List<Vec> next = new ArrayList<>(pts.size() * 2);
            for (int i = 0; i + 1 < pts.size(); i++) {
                Vec a = pts.get(i), b = pts.get(i + 1);
                double l = len(sub(b, a));
                double ang = r.nextDouble() * Math.PI * 2, k = (r.nextDouble() * 2 - 1) * jag * l;
                Vec mid = lerp(a, b, 0.5).add(side[0].scale(Math.cos(ang) * k)).add(side[1].scale(Math.sin(ang) * k));
                next.add(a);
                next.add(mid);
            }
            next.add(pts.get(pts.size() - 1));
            pts = next;
        }
        return pts;
    }

    // ---------------------------------------------------------------- slash

    /**
     * Points of a slash arc around `centre` in the plane (u = sweep side, v = forward): `arcDeg` wide, centred on v,
     * at distance `radius`. `bend` bows it: 0 is the straight chord, 1 the circular arc, more is deeper.
     * Point 0 is where the sweep starts (the -u side when dir &gt; 0).
     */
    public static List<Vec> slashArc(Vec centre, Vec u, Vec v, double radius, double arcDeg, double bend, int n, int dir) {
        List<Vec> out = new ArrayList<>(n + 1);
        double half = Math.toRadians(arcDeg) / 2;
        Vec c0 = centre.add(u.scale(-Math.sin(half) * radius * dir)).add(v.scale(Math.cos(half) * radius));
        Vec c1 = centre.add(u.scale(Math.sin(half) * radius * dir)).add(v.scale(Math.cos(half) * radius));
        for (int i = 0; i <= n; i++) {
            double t = (double) i / n, a = (-half + 2 * half * t) * dir;
            Vec onArc = centre.add(u.scale(Math.sin(a) * radius)).add(v.scale(Math.cos(a) * radius));
            Vec chord = lerp(c0, c1, t);
            out.add(chord.add(sub(onArc, chord).scale(bend)));
        }
        return out;
    }

    /**
     * Visible span of a slash at time te (ticks) as {tail, head} fractions of the arc: the head runs out in `grow` ticks
     * (fast start, soft stop), the tail follows after `lag` ticks and catches up by the end `life`.
     */
    public static double[] slashSpan(double te, double grow, double life) {
        double g = Math.max(1, grow), lag = Math.max(1, Math.min(life - g, g * 0.6));
        double head = easeOut(clamp01(te / g));
        double tail = easeIn(clamp01((te - lag) / Math.max(1, life - lag)));
        return new double[] {Math.min(tail, head), head};
    }

    // ---------------------------------------------------------------- chains

    /**
     * n+1 points of a hanging chain from a to b: a parabola dropping `sag` blocks at the middle (less with `tension` 0..1).
     */
    public static List<Vec> chain(Vec a, Vec b, double sag, double tension, int n) {
        double s = sag * (1 - clamp01(tension));
        List<Vec> out = new ArrayList<>(n + 1);
        for (int i = 0; i <= n; i++) {
            double t = (double) i / n;
            out.add(lerp(a, b, t).add(new Vec(0, -4 * s * t * (1 - t), 0)));
        }
        return out;
    }

    // ---------------------------------------------------------------- vortex

    /**
     * Point of a vortex arm at height fraction h (0 bottom .. 1 top): `turns` around the axis over the height, radius from
     * `radius·funnel` at the bottom to `radius` at the top; `spinDeg` turns the whole vortex.
     */
    public static Vec spiral(Vec base, double radius, double height, double funnel, double turns, int arm, int arms, double h, double spinDeg) {
        double ang = Math.toRadians(spinDeg) + Math.PI * 2 * ((double) arm / Math.max(1, arms) + turns * h);
        double r = radius * (funnel + (1 - funnel) * h);
        return base.add(new Vec(Math.cos(ang) * r, height * h, Math.sin(ang) * r));
    }

    /** Radius factor of a vortex particle after a fraction k of its life: pull &gt; 0 draws it in, pull &lt; 0 throws it out. */
    public static double pull(double pull, double k) {
        return Math.max(0, 1 - pull * k);
    }

    // ---------------------------------------------------------------- wings, pulse

    /** Flap angle in degrees at time t: amplitude `amp`, `period` ticks; 0 period means no flapping. */
    public static double flap(double t, double amp, double period) {
        return period <= 0 ? 0 : amp * Math.sin(Math.PI * 2 * t / period);
    }

    /** Pulse factor around 1: 1 ± amp, period ticks (0 = steady). */
    public static double pulse(double t, double amp, double period) {
        return period <= 0 ? 1 : 1 + amp * Math.sin(Math.PI * 2 * t / period);
    }

    /** Flash envelope 0..1..0 over p in 0..1: quick rise (first `rise` share, ease-out) then a soft quadratic tail. */
    public static double flash(double p, double rise) {
        if (p <= 0 || p >= 1) return 0;
        if (p < rise) return easeOut(p / rise);
        double q = (p - rise) / (1 - rise);
        return (1 - q) * (1 - q);
    }

    static double clamp01(double x) {
        return Math.max(0, Math.min(1, x));
    }

    static double easeOut(double t) {
        return 1 - Math.pow(1 - t, 3);
    }

    static double easeIn(double t) {
        return t * t;
    }
}
