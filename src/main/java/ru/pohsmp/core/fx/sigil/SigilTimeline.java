package ru.pohsmp.core.fx.sigil;

import ru.pohsmp.core.fx.sigil.SigilDef.AppearMode;
import ru.pohsmp.core.fx.sigil.SigilDef.DissolveMode;
import ru.pohsmp.core.fx.sigil.SigilDef.Layer;
import ru.pohsmp.core.fx.sigil.SigilDef.LayerType;

/**
 * How a sigil looks at a moment of its life: the formulas of docs/sigils.md, the same ones tools/sigil_preview.html uses.
 * Pure math (no Minecraft), so the client renderer only draws what this returns and the server can read the timings.
 * {@code t} is ticks since the sigil started (fractional, with partial ticks); {@code stopAt} is the tick the dissolve began
 * or {@code Double.NaN} while it has not been stopped.
 */
public final class SigilTimeline {
    private SigilTimeline() {}

    /** Key moments of a sigil (ticks from its start). */
    public record Timings(int layersEnd, int expandStart, int formedAt) {}

    /** What to draw for one layer. Angles in degrees. */
    public record LayerState(double alpha, double scale, double angle, double tilt, double drawFraction, double drawStart,
                             int drawDirection, double arcRadiusMul, double arcLength) {
        public boolean visible() {
            return alpha > 0.001 && scale > 0.0001;
        }

        /** Centre angle of arc k for ARCS layers (degrees). */
        public double arcOffset(int k, int count, double assemble) {
            return k * 360.0 / count + (1 - assemble) * (k % 2 == 1 ? 150 : -150);
        }
    }

    public static Timings timings(SigilDef def) {
        int layersEnd = 0;
        for (Layer l : def.layers()) layersEnd = Math.max(layersEnd, l.appear().end());
        if (def.expand() == null) return new Timings(layersEnd, layersEnd, layersEnd);
        int expandStart = layersEnd + def.expand().delay();
        return new Timings(layersEnd, expandStart, expandStart + def.expand().duration());
    }

    /** Tick when the sigil dissolves on its own (formedAt + hold), or -1 if it waits to be stopped. */
    public static int autoStopAt(SigilDef def) {
        return def.hold() < 0 ? -1 : timings(def).formedAt() + def.hold();
    }

    /** Whole-sigil scale (radius in blocks = this * layer radius): size, expand and collapse/shatter. */
    public static double globalScale(SigilDef def, double t, double stopAt, double instanceScale) {
        double s = instanceScale * def.size();
        if (def.expand() != null) {
            Timings tm = timings(def);
            double k = (t - tm.expandStart()) / Math.max(1, def.expand().duration());
            s *= 1 + (def.expand().scale() - 1) * def.expand().easing().apply(k);
        }
        double d = dissolveProgress(def, t, stopAt);
        if (def.dissolve().modes().contains(DissolveMode.COLLAPSE)) s *= 1 - Easing.EASE_IN_CUBIC.apply(d);
        return Math.max(0, s);
    }

    /** Whole-sigil opacity multiplier (fade dissolve). */
    public static double globalAlpha(SigilDef def, double t, double stopAt) {
        return def.dissolve().modes().contains(DissolveMode.FADE) ? 1 - dissolveProgress(def, t, stopAt) : 1;
    }

    public static double dissolveProgress(SigilDef def, double t, double stopAt) {
        if (Double.isNaN(stopAt)) return 0;
        return clamp01((t - stopAt) / Math.max(1, def.dissolve().duration()));
    }

    /** True once the dissolve has run its course. */
    public static boolean finished(SigilDef def, double t, double stopAt) {
        if (Double.isNaN(stopAt)) return def.lifetime() >= 0 && t >= def.lifetime();
        return t >= stopAt + def.dissolve().duration();
    }

    public static LayerState layer(SigilDef def, int index, double t, double stopAt) {
        Layer l = def.layers().get(index);
        SigilDef.Appear ap = l.appear();
        double p = clamp01((t - ap.delay()) / ap.duration());
        double e = ap.easing().apply(p);
        boolean started = t >= ap.delay();
        double alpha = !started ? 0 : ap.modes().contains(AppearMode.FADE) ? clamp01(e) : 1;
        double scale = ap.modes().contains(AppearMode.GROW) ? Math.max(0, e) : 1;

        var dis = def.dissolve();
        if (!Double.isNaN(stopAt)) {
            if (dis.modes().contains(DissolveMode.REVERSE)) {
                int n = def.layers().size(), rank = n - 1 - index;
                double span = Math.max(1, dis.duration() - dis.stagger() * (n - 1));
                alpha *= 1 - clamp01((t - stopAt - rank * dis.stagger()) / span);
            }
            if (dis.modes().contains(DissolveMode.SHATTER)) {
                double d = dissolveProgress(def, t, stopAt);
                scale *= 1 + 0.8 * d;
                alpha *= 1 - d;
            }
        }
        if (l.pulse() != null && l.pulse().amp() != 0) alpha *= 1 + l.pulse().amp() * Math.sin(2 * Math.PI * t / l.pulse().period());
        alpha = Math.max(0, alpha * l.brightness());

        double angle = rotation(l, t);
        if (ap.modes().contains(AppearMode.TWIST)) angle += ap.twist() * (1 - clamp01(e));
        double tilt = ap.modes().contains(AppearMode.UNFOLD) ? 90 * (1 - clamp01(e)) : 0;
        double draw = ap.modes().contains(AppearMode.DRAW) ? clamp01(e) : 1;

        double arcR = 1, arcLen = 360;
        if (l.type() == LayerType.ARCS) {
            double asm = ap.modes().contains(AppearMode.ASSEMBLE) ? clamp01(e) : 1;
            double closed = 360.0 / Math.max(1, l.count());
            arcLen = l.arcLength() + (closed - l.arcLength()) * asm;
            arcR = 1 + 0.9 * (1 - asm);
        }
        return new LayerState(alpha, scale * l.radius(), angle, tilt, draw, ap.startAngle(), ap.direction(), arcR, arcLen);
    }

    // ---------------------------------------------------------------- pieces

    /**
     * One flying piece of a PIECES layer. The piece is the sector [k·360/n, (k+1)·360/n] of the layer (plus the layer angle).
     * Draw it at its rest place, then: rotate by {@code spin} around the normal through its centre, by {@code tilt} around the
     * tangent through its centre, move its centre to radius {@code centerRadius · radialMul} at {@code centerAngle + orbit}, raise by
     * {@code lift} along the normal (all in layer units, i.e. times the layer radius). {@code u} is 0 far away, 1 locked.
     */
    public record PieceState(double u, double alpha, double centerAngle, double centerRadius, double radialMul, double orbit, double lift,
                             double tilt, double spin, double brightness) {}

    /** Arrival rank of piece k (0 = first): a permutation of 0..n-1, the same in the preview. */
    public static int pieceRank(SigilDef.PieceOrder order, int k, int n) {
        switch (order) {
            case AROUND: return k;
            case ALTERNATE: {
                int half = (n + 1) / 2;
                return k < half ? 2 * k : 2 * (k - half) + 1;
            }
            default: return (int) ((long) k * scatterStride(n) % n);
        }
    }

    /** Smallest stride ≥ round(0.382·n) coprime with n: pieces arrive spread around the circle. */
    public static int scatterStride(int n) {
        int s = Math.max(1, (int) Math.round(n * 0.382));
        while (gcd(s, n) != 1) s++;
        return s;
    }

    private static int gcd(int a, int b) {
        return b == 0 ? a : gcd(b, a % b);
    }

    public static PieceState piece(SigilDef def, int index, int k, double t, double stopAt) {
        Layer l = def.layers().get(index);
        SigilDef.Appear ap = l.appear();
        SigilDef.Pieces pc = ap.pieces() != null ? ap.pieces() : SigilDef.Pieces.DEFAULT;
        int n = pc.count(), rank = pieceRank(pc.order(), k, n);
        double fly = ap.duration() * pc.pieceTime(), gap = ap.duration() - fly;
        double start = ap.delay() + (n > 1 ? gap * rank / (n - 1) : 0), lockAt = start + fly;
        double u = ap.easing().apply(clamp01((t - start) / fly));
        if (t < start) u = 0;
        boolean stopped = !Double.isNaN(stopAt);          // разборка — общая для печати (reverse/collapse…), части не разлетаются
        double side = k % 2 == 0 ? 1 : -1, w = 1 - u;
        double sector = 360.0 / n, centerAngle = (k + 0.5) * sector;
        double centerRadius = l.type() == LayerType.BAND ? (l.inner() + 1) / 2 : 0.62;
        double flash = stopped ? 0 : Math.max(0, 1 - Math.abs(t - lockAt) / 5);
        return new PieceState(u, t < start ? 0 : clamp01(u * 2.5), centerAngle, centerRadius, 1 + pc.fly() * w, pc.orbit() * w * side,
                pc.lift() * w, pc.tilt() * w * side, pc.spin() * w * side, 1 + pc.lockFlash() * flash);
    }

    /** How far an ARCS layer has assembled (0..1), for {@link LayerState#arcOffset}. */
    public static double assemble(SigilDef def, int index, double t) {
        Layer l = def.layers().get(index);
        if (!l.appear().modes().contains(AppearMode.ASSEMBLE)) return 1;
        return clamp01(l.appear().easing().apply((t - l.appear().delay()) / l.appear().duration()));
    }

    /**
     * Rotation in degrees at tick t: speed (deg/s) integrated over time, faster while the layer appears:
     * angle = speed/20 * (t + boost * ∫0..t (1 - e(τ)) dτ). Closed form outside the appear window, Simpson inside.
     */
    static double rotation(Layer l, double t) {
        var r = l.rotation();
        if (r.speed() == 0 || t <= 0) return 0;
        double extra = 0;
        if (r.boost() != 0) {
            SigilDef.Appear ap = l.appear();
            double a = ap.delay(), b = ap.end();
            extra += Math.min(t, a);                                   // before the layer appears: (1 - e) = 1
            if (t > a) extra += integral(l, a, Math.min(t, b));
            extra *= r.boost();
        }
        return r.speed() / 20.0 * (t + extra);
    }

    private static double integral(Layer l, double from, double to) {
        if (to <= from) return 0;
        int n = 32;
        double h = (to - from) / n, sum = 0;
        for (int i = 0; i <= n; i++) {
            double x = from + i * h;
            double f = 1 - clamp01(l.appear().easing().apply((x - l.appear().delay()) / l.appear().duration()));
            sum += f * (i == 0 || i == n ? 1 : i % 2 == 1 ? 4 : 2);
        }
        return sum * h / 3;
    }

    static double clamp01(double x) {
        return Math.max(0, Math.min(1, x));
    }
}
