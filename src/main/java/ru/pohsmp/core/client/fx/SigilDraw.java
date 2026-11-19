package ru.pohsmp.core.client.fx;

import com.mojang.blaze3d.vertex.VertexConsumer;
import java.util.SplittableRandom;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.client.fx.FxDraw.Frame;
import ru.pohsmp.core.fx.FxLib;
import ru.pohsmp.core.fx.FxMath;
import ru.pohsmp.core.fx.sigil.Easing;
import ru.pohsmp.core.fx.sigil.SigilDef;
import ru.pohsmp.core.fx.sigil.SigilDef.AppearMode;
import ru.pohsmp.core.fx.sigil.SigilDef.Layer;
import ru.pohsmp.core.fx.sigil.SigilDef.LayerType;
import ru.pohsmp.core.fx.sigil.SigilCracks;
import ru.pohsmp.core.fx.sigil.SigilHit;
import ru.pohsmp.core.fx.sigil.SigilText;
import ru.pohsmp.core.fx.sigil.SigilTimeline;
import ru.pohsmp.core.fx.sigil.SigilTimeline.LayerState;
import ru.pohsmp.core.fx.sigil.SigilTimeline.PieceState;

/**
 * Draws a sigil exactly as {@link SigilTimeline} describes it (docs/sigils.md): no shaders, the "draw" reveal is a triangle fan
 * up to the current angle, bands are rings with the texture repeated around, arcs are short ring strips, pieces are sectors
 * flying into place, inscriptions are one textured square per letter from a glyph atlas ({@link SigilText}). The plane is (u, v) with normal n; layer tilt (unfold) turns v towards n.
 * T08: hits ({@link SigilHit}) — a wave of light over every layer and a light sheet, the flinch and wobble of the plane, a flash and
 * sparks at the point. T09: the {@code cracks} dissolve ({@link SigilCracks}) — layers are drawn shard by shard, plus glowing cracks
 * and dust.
 */
public final class SigilDraw {
    private SigilDraw() {}

    private static final ResourceLocation GLOW = FxDraw.tex("glow"), RING = FxDraw.tex("thin_ring"), SPARK = FxDraw.tex("spark_soft");

    /** Draws the sigil and its children; returns false once everything has finished (the run can be dropped). */
    public static boolean draw(Frame f, SigilRun r) {
        SigilDef d = r.def;
        if (d == null) return false;
        double t = f.time() - r.start;
        if (t < 0) return true;
        if (r.stopAfter >= 0 && Double.isNaN(r.stopAt) && t >= r.stopAfter) r.stop(r.stopAfter);
        int auto = SigilTimeline.autoStopAt(d);
        if (auto >= 0 && Double.isNaN(r.stopAt) && t >= auto) r.stop(auto);
        boolean alive = !SigilTimeline.finished(d, t, r.stopAt);
        Vec3 c = r.pos(f.pt());
        if (alive) drawSelf(f, r, d, t, c);
        boolean anyChild = false;
        var tm = SigilTimeline.timings(d);
        if (!r.spawned && t >= tm.formedAt() && Double.isNaN(r.stopAt)) {
            r.spawned = true;
            spawnChildren(r, d, c, tm.formedAt());
        }
        for (SigilRun ch : r.children) anyChild |= draw(f, ch);
        return alive || anyChild;
    }

    private static void spawnChildren(SigilRun r, SigilDef d, Vec3 c, int formedAt) {
        for (SigilDef.Child ch : d.onFormed()) {
            SigilDef cd = FxLib.sigil(ch.id());
            if (cd == null) continue;
            Vec3 anchor = ch.anchorCaster() && r.caster != null ? r.caster.position() : c;
            float yaw = ch.anchorCaster() && r.caster != null ? r.caster.getYRot() : r.yaw;
            boolean onCaster = ch.anchorCaster() && r.caster != null;
            if (ch.arc() == null) {
                r.children.add(child(r, cd, anchor, formedAt, yaw, onCaster));
                continue;
            }
            for (FxMath.Placed p : FxMath.arc(ch.arc(), new FxMath.Vec(anchor.x, anchor.y, anchor.z), yaw))
                r.children.add(child(r, cd, new Vec3(p.pos().x(), p.pos().y(), p.pos().z()), formedAt + p.delay(), yaw, onCaster));
        }
    }

    private static SigilRun child(SigilRun parent, SigilDef cd, Vec3 at, int delay, float yaw, boolean onCaster) {
        SigilRun c = new SigilRun();
        c.def = cd;
        c.base = at;
        c.yaw = yaw;
        c.start = parent.start + delay;
        c.scale = parent.scale;
        c.caster = parent.caster;
        c.seed = parent.seed * 31 + parent.children.size();
        c.texts.putAll(parent.texts);
        if (onCaster) {
            c.follow = parent.caster;
            c.offset = at.subtract(parent.caster.position());
        }
        return c;
    }

    // ---------------------------------------------------------------- frame of the plane

    /** n, u, v of the sigil plane. */
    private record Basis(Vec3 n, Vec3 u, Vec3 v) {}

    private static Basis basis(Frame f, SigilRun r, SigilDef.Orientation o, Vec3 c) {
        return switch (o) {
            case GROUND -> new Basis(new Vec3(0, 1, 0), new Vec3(1, 0, 0), new Vec3(0, 0, -1));
            case SKY -> new Basis(new Vec3(0, -1, 0), new Vec3(1, 0, 0), new Vec3(0, 0, 1));
            case FACING -> {
                FxMath.Vec fw = FxMath.forward(r.yaw), rt = FxMath.right(r.yaw);
                yield new Basis(new Vec3(fw.x(), fw.y(), fw.z()), new Vec3(rt.x(), rt.y(), rt.z()), new Vec3(0, 1, 0));
            }
            case BILLBOARD -> {
                Vec3 n = f.camPos().subtract(c);
                n = n.lengthSqr() < 1e-6 ? new Vec3(0, 0, 1) : n.normalize();
                yield new Basis(n, f.left().scale(-1), f.up());
            }
            case OUTWARD -> {
                Vec3 n = r.normal == null || r.normal.lengthSqr() < 1e-6 ? new Vec3(0, 1, 0) : r.normal.normalize();
                Vec3 u = n.cross(new Vec3(0, 1, 0));
                u = u.lengthSqr() < 1e-6 ? new Vec3(1, 0, 0) : u.normalize();
                yield new Basis(n, u, u.cross(n));
            }
        };
    }

    // ---------------------------------------------------------------- the sigil itself

    private static void drawSelf(Frame f, SigilRun r, SigilDef d, double t, Vec3 c) {
        SigilDef.Orientation o = r.orient != null ? r.orient : d.orientation();
        Basis bs = basis(f, r, o, c);
        double gs = SigilTimeline.globalScale(d, t, r.stopAt, r.scale);
        double ga = SigilTimeline.globalAlpha(d, t, r.stopAt) * r.alpha;
        if (gs <= 1e-4 || ga <= 0.002) return;
        SigilLight.draw(f, r, d, t, c, gs);
        if (SigilCracks.breaking(d, t, r.stopAt)) {      // T09: the sigil breaks into shards
            r.hits.clear();
            r.pending.clear();
            cracks(f, r, d, t, c, bs, gs, ga);
            return;
        }
        // T08: place new hits on the plane, then flinch (scale) and wobble (turn the plane) while they last
        placeHits(r, d, t, bs, gs);
        if (!r.hits.isEmpty()) {
            gs *= SigilHit.scale(d, r.hits, t);
            bs = wobble(bs, SigilHit.wobble(d, r.hits, t));
        }
        layers(f, r, d, t, c, bs, gs, ga, false);
        // joint cast (T15): a second outline, raised, wider, turned and spinning the other way
        if (ru.pohsmp.core.client.JointFx.isJoint(r.caster != null ? r.caster : r.follow)) layers(f, r, d, t, c, bs, gs, ga, true);
        if (!r.hits.isEmpty()) hits(f, r, d, t, c, bs, gs, ga);
        flash(f, r, d, t, c, bs, gs, ga);
    }

    // ---------------------------------------------------------------- T08: hits

    /** Pending world hits -> plane coordinates (unit = current radius); drops dead hits and hits that missed the sigil. */
    private static void placeHits(SigilRun r, SigilDef d, double t, Basis bs, double gs) {
        SigilDef.Hit h = d.hit();
        if (h == null) {
            r.pending.clear();
            return;
        }
        for (SigilRun.Pending p : r.pending) {
            double x = p.offset().dot(bs.u) / gs, y = p.offset().dot(bs.v) / gs;
            if (Math.hypot(x, y) > d.reach() * 1.3) continue;                       // not on this sigil (e.g. another sigil of the effect)
            SigilHit.accept(h, r.hits, new SigilHit.Event(x, y, p.at(), p.power(), p.seed()));
        }
        r.pending.clear();
        r.hits.removeIf(e -> !SigilHit.alive(h, e, t));
    }

    /** The plane turned by the wobble around the in-plane axis (ax·u + ay·v). */
    private static Basis wobble(Basis b, SigilHit.Wobble w) {
        if (Math.abs(w.angle()) < 1e-4) return b;
        Vec3 axis = b.u.scale(w.ax()).add(b.v.scale(w.ay())).normalize();
        double a = Math.toRadians(w.angle());
        return new Basis(rotate(b.n, axis, a), rotate(b.u, axis, a), rotate(b.v, axis, a));
    }

    /** Rodrigues: p turned by angle a (radians) around the unit axis k. */
    private static Vec3 rotate(Vec3 p, Vec3 k, double a) {
        double cs = Math.cos(a), sn = Math.sin(a);
        return p.scale(cs).add(k.cross(p).scale(sn)).add(k.scale(k.dot(p) * (1 - cs)));
    }

    /**
     * Wave over each formed disc/spokes/band layer (its own texture on a dense polar grid, vertex alpha = layer alpha ·
     * SigilHit.glow there, colour towards the hit colour), the light sheet (white, sheen), the flash at the point and the sparks.
     */
    private static void hits(Frame f, SigilRun r, SigilDef d, double t, Vec3 c, Basis bs, double gs, double ga) {
        SigilDef.Hit h = d.hit();
        int hitCol = h.color() >= 0 ? h.color() : FxDraw.mix(r.color >= 0 ? r.color : d.color(), 0xFFFFFF, 0.5);
        int rings = f.low() ? 8 : 16, sectors = f.low() ? 40 : 72;
        double top = 0;
        for (int i = 0; i < d.layers().size(); i++) {
            Layer l = d.layers().get(i);
            top = Math.max(top, l.heightOffset());
            if (l.type() == LayerType.ARCS || l.type() == LayerType.TEXT || t < l.appear().end()) continue;   // надписи (T07) волной не светятся
            LayerState st = SigilTimeline.layer(d, i, t, r.stopAt);
            if (!st.visible()) continue;
            double rho = st.scale(), R = gs * rho, a = st.alpha() * ga;
            boolean band = l.type() == LayerType.BAND;
            double inner = band ? (l.inner() >= 0.9999 ? 0.86 : l.inner()) : 0;
            int col = FxDraw.mix(r.color >= 0 ? r.color : l.color(), hitCol, 0.45);
            Plane p = new Plane(c.add(bs.n.scale(l.heightOffset() * r.scale + 0.004)), bs.u, bs.v, bs.n);
            VertexConsumer vc = f.add(FxDraw.tex(l.texture()));
            int nr = band ? 3 : rings;
            double[][] g = new double[nr + 1][sectors + 1];                       // glow at the grid nodes, once per frame
            for (int ri = 0; ri <= nr; ri++)
                for (int si = 0; si <= sectors; si++) g[ri][si] = glowAt(d, r, (inner + (1 - inner) * ri / nr) * rho, 360.0 * si / sectors, t);
            for (int ri = 0; ri < nr; ri++) {
                double q0 = inner + (1 - inner) * ri / nr, q1 = inner + (1 - inner) * (ri + 1) / nr;   // shares of the layer radius
                for (int si = 0; si < sectors; si++) {
                    double a0 = 360.0 * si / sectors, a1 = 360.0 * (si + 1) / sectors;
                    double g00 = g[ri][si], g01 = g[ri][si + 1], g11 = g[ri + 1][si + 1], g10 = g[ri + 1][si];
                    if (g00 + g01 + g11 + g10 < 0.004) continue;
                    if (band) {
                        float u0 = (float) ((a0 - st.angle()) / 360 * l.repeat()), u1 = (float) ((a1 - st.angle()) / 360 * l.repeat());
                        float v0 = (float) ((1 - q0) / (1 - inner)), v1 = (float) ((1 - q1) / (1 - inner));
                        FxDraw.vert(vc, f, p.polar(R * q1, a0), u0, v1, col, a * g10);
                        FxDraw.vert(vc, f, p.polar(R * q0, a0), u0, v0, col, a * g00);
                        FxDraw.vert(vc, f, p.polar(R * q0, a1), u1, v0, col, a * g01);
                        FxDraw.vert(vc, f, p.polar(R * q1, a1), u1, v1, col, a * g11);
                    } else {
                        FxDraw.vert(vc, f, p.polar(R * q1, a0), du(R * q1, a0, R, st.angle()), dv(R * q1, a0, R, st.angle()), col, a * g10);
                        FxDraw.vert(vc, f, p.polar(R * q0, a0), du(R * q0, a0, R, st.angle()), dv(R * q0, a0, R, st.angle()), col, a * g00);
                        FxDraw.vert(vc, f, p.polar(R * q0, a1), du(R * q0, a1, R, st.angle()), dv(R * q0, a1, R, st.angle()), col, a * g01);
                        FxDraw.vert(vc, f, p.polar(R * q1, a1), du(R * q1, a1, R, st.angle()), dv(R * q1, a1, R, st.angle()), col, a * g11);
                    }
                }
            }
        }
        // light sheet over the whole disc (so the ring reads on sparse patterns too)
        double reach = d.reach();
        Plane sp = new Plane(c.add(bs.n.scale(top * r.scale + 0.012)), bs.u, bs.v, bs.n);
        if (h.sheen() > 0) {
            VertexConsumer vc = f.add(FxDraw.WHITE);
            int sheetCol = FxDraw.mix(r.color >= 0 ? r.color : d.color(), hitCol, 0.5);
            double[][] g = new double[rings + 1][sectors + 1];
            for (int ri = 0; ri <= rings; ri++)
                for (int si = 0; si <= sectors; si++) g[ri][si] = sheenAt(d, r, reach * 1.02 * ri / rings, 360.0 * si / sectors, t);
            for (int ri = 0; ri < rings; ri++) {
                double q0 = reach * 1.02 * ri / rings, q1 = reach * 1.02 * (ri + 1) / rings;
                for (int si = 0; si < sectors; si++) {
                    double a0 = 360.0 * si / sectors, a1 = 360.0 * (si + 1) / sectors;
                    double g10 = g[ri + 1][si], g00 = g[ri][si], g01 = g[ri][si + 1], g11 = g[ri + 1][si + 1];
                    if (g00 + g01 + g11 + g10 < 0.004) continue;
                    FxDraw.vert(vc, f, sp.polar(gs * q1, a0), 0.5f, 0.5f, sheetCol, ga * g10);
                    FxDraw.vert(vc, f, sp.polar(gs * q0, a0), 0.5f, 0.5f, sheetCol, ga * g00);
                    FxDraw.vert(vc, f, sp.polar(gs * q0, a1), 0.5f, 0.5f, sheetCol, ga * g01);
                    FxDraw.vert(vc, f, sp.polar(gs * q1, a1), 0.5f, 0.5f, sheetCol, ga * g11);
                }
            }
        }
        // flash at the point, then sparks (in blocks, they fall in the world); one buffer at a time — taking another ends the first
        VertexConsumer glow = f.add(GLOW);
        for (SigilHit.Event e : r.hits) {
            double age = t - e.at();
            Vec3 at = sp.at(e.x() * gs, e.y() * gs, 0.02);
            FxDraw.billboard(glow, f, at, gs * 0.32 * (0.6 + 0.4 * e.power()) * (1 + age / 6), 0, hitCol, e.power() * Math.exp(-age / 3) * ga);
        }
        if (f.low()) return;
        VertexConsumer spark = f.add(SPARK);
        for (SigilHit.Event e : r.hits) {
            Vec3 at = sp.at(e.x() * gs, e.y() * gs, 0.02);
            for (int i = 0, n = SigilHit.sparkCount(h, e); i < n; i++) {
                SigilHit.Spark s = SigilHit.spark(h, e, i, t);
                if (s.alpha() <= 0.002) continue;
                Vec3 q = at.add(bs.u.scale(s.u())).add(bs.v.scale(s.v())).add(bs.n.scale(s.n())).add(0, -s.drop(), 0);
                FxDraw.billboard(spark, f, q, s.size(), 0, hitCol, s.alpha() * ga);
            }
        }
    }

    private static double glowAt(SigilDef d, SigilRun r, double rho, double deg, double t) {
        double k = Math.toRadians(deg);
        return SigilHit.glow(d, r.hits, Math.cos(k) * rho, Math.sin(k) * rho, t);
    }

    private static double sheenAt(SigilDef d, SigilRun r, double rho, double deg, double t) {
        double k = Math.toRadians(deg);
        return SigilHit.sheen(d, r.hits, Math.cos(k) * rho, Math.sin(k) * rho, t);
    }

    // ---------------------------------------------------------------- T09: cracks

    /**
     * The sigil broken into shards (SigilCracks): every layer is cut along the same cracks (shard (k, j) = between radial cracks
     * k and k+1, from ring j to j+1; the outer ring takes everything beyond reach), each shard moves as one piece; then the glowing
     * cracks (radial run from the centre, ring cracks open from the radial ones), bright tips of running cracks, and dust.
     */
    private static void cracks(Frame f, SigilRun r, SigilDef d, double t, Vec3 c, Basis bs, double gs, double ga) {
        SigilDef.Cracks cr = d.dissolve().cracksOrNull();
        int seed = (int) r.seed, nk = cr.count(), nj = cr.rings() + 1;
        double reach = d.reach();
        SigilCracks.Shard[] sh = new SigilCracks.Shard[nk * nj];
        for (int k = 0; k < nk; k++) for (int j = 0; j < nj; j++) sh[k * nj + j] = SigilCracks.shard(d, seed, k, j, t, r.stopAt);
        Vec3 down = new Vec3(0, -1, 0);
        double top = 0;
        for (int i = 0; i < d.layers().size(); i++) {
            Layer l = d.layers().get(i);
            top = Math.max(top, l.heightOffset());
            if (l.type() == LayerType.TEXT) continue;                  // надписи (T07) на осколки не режутся — гаснут с трещинами
            LayerState st = SigilTimeline.layer(d, i, t, r.stopAt);   // the angle stays as it was at the stop
            if (!st.visible()) continue;
            double rho = st.scale(), a = st.alpha() * ga, ang = st.angle();
            int col = r.color >= 0 ? r.color : l.color();
            VertexConsumer vc = f.add(FxDraw.tex(l.texture()));
            double lift = l.heightOffset() * r.scale;
            double inner = switch (l.type()) {
                case BAND -> l.inner() >= 0.9999 ? 0.86 : l.inner();
                case ARCS -> 1 - l.width() / 2;
                default -> 0;
            };
            double outer = l.type() == LayerType.ARCS ? 1 + l.width() / 2 : 1;
            for (int k = 0; k < nk; k++)
                for (int j = 0; j < nj; j++) {
                    SigilCracks.Shard s = sh[k * nj + j];
                    double sa = a * s.alpha() * s.brightness();
                    if (sa <= 0.002) continue;
                    double ra = Math.max(SigilCracks.ringRadius(cr, j, reach), inner * rho);
                    double rb = Math.min(j == nj - 1 ? Double.MAX_VALUE : SigilCracks.ringRadius(cr, j + 1, reach), outer * rho);
                    if (rb - ra < 1e-4) continue;
                    shard(f, vc, l, cr, seed, k, s, ra, rb, rho, inner, outer, ang, reach, c.add(bs.n.scale(lift)), bs, gs, down, col, sa);
                }
        }
        // glowing cracks
        double g = SigilCracks.crackGlow(d, t, r.stopAt) * ga;
        if (g <= 0.004) {
            dust(f, r, d, cr, seed, t, c, bs, gs, top, down, ga);
            return;
        }
        int lineCol = cr.color() >= 0 ? cr.color() : FxDraw.mix(r.color >= 0 ? r.color : d.color(), 0xFFFFFF, 0.6);
        Plane p = new Plane(c.add(bs.n.scale(top * r.scale + 0.014)), bs.u, bs.v, bs.n);
        java.util.List<Vec3> tips = new java.util.ArrayList<>();
        for (int k = 0; k < nk; k++) {
            double rr = SigilCracks.crackReach(d, k, t, r.stopAt) * reach;
            if (rr <= 1e-3) continue;
            java.util.List<Vec3> pts = new java.util.ArrayList<>();
            int n = 16;
            for (int i = 0; i <= n; i++) {
                double rad = rr * i / n;
                pts.add(p.polar(gs * rad, SigilCracks.crackAngle(cr, seed, k, rad, reach)));
            }
            crackLine(f, pts, bs, gs, lineCol, g);
            if (rr < reach * 0.999) tips.add(pts.get(n));
        }
        for (int j = 1; j <= cr.rings(); j++) {
            double open = SigilCracks.ringCrack(d, j, t, r.stopAt);
            if (open <= 1e-3) continue;
            double rad = SigilCracks.ringRadius(cr, j, reach);
            for (int k = 0; k < nk; k++) {
                double a0 = SigilCracks.crackAngle(cr, seed, k, rad, reach), a1 = SigilCracks.crackAngle(cr, seed, k + 1, rad, reach);
                double w = (a1 - a0) / 2 * open;
                for (double[] arc : new double[][] {{a0, a0 + w}, {a1 - w, a1}}) {
                    java.util.List<Vec3> pts = new java.util.ArrayList<>();
                    for (int i = 0; i <= 6; i++) pts.add(p.polar(gs * rad, arc[0] + (arc[1] - arc[0]) * i / 6));
                    crackLine(f, pts, bs, gs, lineCol, g);
                }
            }
        }
        if (!tips.isEmpty()) {                                      // bright heads of the cracks still running
            VertexConsumer vc = f.add(GLOW);
            for (Vec3 q : tips) FxDraw.billboard(vc, f, q, gs * 0.07, 0, 0xFFFFFF, g * 1.2);
        }
        dust(f, r, d, cr, seed, t, c, bs, gs, top, down, ga);
    }

    /** One crack: a flat glowing strip in the plane (halo + white core), width relative to the sigil. */
    private static void crackLine(Frame f, java.util.List<Vec3> pts, Basis bs, double gs, int col, double g) {
        int n = pts.size();
        Vec3[] sides = new Vec3[n];
        double[] w = new double[n], a = new double[n];
        for (int i = 0; i < n; i++) {
            Vec3 tan = pts.get(Math.min(n - 1, i + 1)).subtract(pts.get(Math.max(0, i - 1)));
            Vec3 side = bs.n.cross(tan);
            sides[i] = side.lengthSqr() < 1e-12 ? bs.u : side.normalize();
            w[i] = Math.max(0.03, gs * 0.022);
            a[i] = g * 0.9;
        }
        FxDraw.glowStrip(f, pts, w, a, col, sides, 3.2);
    }

    /**
     * One shard of one layer: the region between radial cracks k and k+1, radius ra..rb (plane units), as a grid of quads
     * (radial steps at the crack knots, angular steps of ≤ 4°), moved and turned as SigilCracks.Shard says.
     */
    private static void shard(Frame f, VertexConsumer vc, Layer l, SigilDef.Cracks cr, int seed, int k, SigilCracks.Shard s,
                              double ra, double rb, double rho, double inner, double outer, double ang, double reach, Vec3 c, Basis bs,
                              double gs, Vec3 down, int col, double alpha) {
        java.util.List<Double> radii = new java.util.ArrayList<>();
        radii.add(ra);
        for (int i = 1; i < SigilCracks.KNOTS; i++) {
            double q = reach * i / SigilCracks.KNOTS;
            if (q > ra + 1e-6 && q < rb - 1e-6) radii.add(q);
        }
        radii.add(rb);
        java.util.List<Double> fine = new java.util.ArrayList<>();
        fine.add(radii.get(0));
        for (int i = 1; i < radii.size(); i++) {
            double r0 = radii.get(i - 1), r1 = radii.get(i);
            int steps = Math.max(1, (int) Math.ceil((r1 - r0) / (reach / 14)));
            for (int q = 1; q <= steps; q++) fine.add(r0 + (r1 - r0) * q / steps);
        }
        double mid = (ra + rb) / 2;
        int m = Math.max(3, (int) Math.ceil((SigilCracks.crackAngle(cr, seed, k + 1, mid, reach) - SigilCracks.crackAngle(cr, seed, k, mid, reach)) / 4));
        double ca = Math.toRadians(s.centerAngle()), cx = Math.cos(ca) * s.centerRadius(), cy = Math.sin(ca) * s.centerRadius();
        double tx = -Math.sin(ca), ty = Math.cos(ca);
        double spin = Math.toRadians(s.spin()), tilt = Math.toRadians(s.tilt()), cs = Math.cos(tilt), sn = Math.sin(tilt);
        double ox = cx + Math.cos(ca) * s.radial(), oy = cy + Math.sin(ca) * s.radial();
        Vec3 drop = down.scale(s.drop() * gs);
        int nr = fine.size();
        Vec3[] pos = new Vec3[nr * (m + 1)];
        float[] uu = new float[pos.length], vv = new float[pos.length];
        double closed = 360.0 / Math.max(1, l.count());
        for (int ri = 0; ri < nr; ri++) {
            double r = fine.get(ri);
            double a0 = SigilCracks.crackAngle(cr, seed, k, r, reach), a1 = SigilCracks.crackAngle(cr, seed, k + 1, r, reach);
            for (int q = 0; q <= m; q++) {
                double th = a0 + (a1 - a0) * q / m, kk = Math.toRadians(th);
                double x = Math.cos(kk) * r - cx, y = Math.sin(kk) * r - cy;
                double xs = x * Math.cos(spin) - y * Math.sin(spin), ys = x * Math.sin(spin) + y * Math.cos(spin);
                double dot = xs * tx + ys * ty;                                     // tilt around the tangent (tx, ty, 0)
                double rx = xs * cs + tx * dot * (1 - cs), ry = ys * cs + ty * dot * (1 - cs), rz = (tx * ys - ty * xs) * sn;
                int idx = ri * (m + 1) + q;
                pos[idx] = c.add(bs.u.scale((ox + rx) * gs)).add(bs.v.scale((oy + ry) * gs)).add(bs.n.scale(rz * gs)).add(drop);
                double ph = th - ang, lr = r / rho;
                switch (l.type()) {
                    case BAND -> {
                        uu[idx] = (float) (ph / 360 * l.repeat());
                        vv[idx] = (float) ((1 - lr) / (1 - inner));
                    }
                    case ARCS -> {
                        double nArc = Math.round(ph / closed);
                        uu[idx] = (float) ((ph - (nArc * closed - closed / 2)) / closed);
                        vv[idx] = (float) ((outer - lr) / (outer - inner));
                    }
                    default -> {
                        uu[idx] = du(lr, th, 1, ang);
                        vv[idx] = dv(lr, th, 1, ang);
                    }
                }
            }
        }
        for (int ri = 0; ri + 1 < nr; ri++)
            for (int q = 0; q < m; q++) {
                int a = ri * (m + 1) + q, b = (ri + 1) * (m + 1) + q;
                FxDraw.vert(vc, f, pos[b], uu[b], vv[b], col, alpha);
                FxDraw.vert(vc, f, pos[a], uu[a], vv[a], col, alpha);
                FxDraw.vert(vc, f, pos[a + 1], uu[a + 1], vv[a + 1], col, alpha);
                FxDraw.vert(vc, f, pos[b + 1], uu[b + 1], vv[b + 1], col, alpha);
            }
    }

    /** Dust trickling from the cracks (SigilCracks.dust): small sparks that fall in the world. */
    private static void dust(Frame f, SigilRun r, SigilDef d, SigilDef.Cracks cr, int seed, double t, Vec3 c, Basis bs, double gs, double top,
                             Vec3 down, double ga) {
        if (f.low() || cr.dust() <= 0) return;
        int col = cr.color() >= 0 ? cr.color() : FxDraw.mix(r.color >= 0 ? r.color : d.color(), 0xFFFFFF, 0.6);
        Plane p = new Plane(c.add(bs.n.scale(top * r.scale + 0.016)), bs.u, bs.v, bs.n);
        VertexConsumer vc = f.add(SPARK);
        for (int i = 0; i < cr.dust(); i++) {
            SigilCracks.Mote m = SigilCracks.dust(d, seed, i, t, r.stopAt);
            if (m.alpha() <= 0.002) continue;
            Vec3 q = p.polar(gs * m.radius(), m.angle()).add(down.scale(m.drop() * gs));
            FxDraw.billboard(vc, f, q, Math.max(0.025, m.size() * gs), 0, col, m.alpha() * ga);
        }
    }

    private static void layers(Frame f, SigilRun r, SigilDef d, double t, Vec3 c, Basis bs, double gs, double ga, boolean echo) {
        double lift = echo ? ru.pohsmp.core.client.JointFx.LIFT : 0, sc = echo ? ru.pohsmp.core.client.JointFx.SCALE : 1;
        double turn = echo ? Math.toDegrees(ru.pohsmp.core.client.JointFx.TURN) : 0, am = echo ? ru.pohsmp.core.client.JointFx.ALPHA : 1;
        for (int i = 0; i < d.layers().size(); i++) {
            Layer l = d.layers().get(i);
            LayerState st = SigilTimeline.layer(d, i, t, r.stopAt);
            if (!st.visible()) continue;
            double R = gs * st.scale() * sc;
            Vec3 lc = c.add(bs.n.scale(l.heightOffset() * r.scale + lift));
            double tl = Math.toRadians(st.tilt());
            Vec3 u = bs.u, v = bs.v.scale(Math.cos(tl)).add(bs.n.scale(Math.sin(tl))), n = bs.n.scale(Math.cos(tl)).subtract(bs.v.scale(Math.sin(tl)));
            int col = r.color >= 0 ? r.color : l.color();
            double a = st.alpha() * ga * am;
            double ang = echo ? -st.angle() * 1.3 + turn : st.angle();
            Plane pl = new Plane(lc, u, v, n);
            if (l.type() == LayerType.TEXT) {
                text(f, r, d, l, i, t, pl, gs * st.scale() * sc, ang, col, a);
                continue;
            }
            VertexConsumer vc = f.add(FxDraw.tex(l.texture()));
            if (l.appear().modes().contains(AppearMode.PIECES)) pieces(f, vc, pl, d, l, i, t, r.stopAt, R, ang, col, a);
            else switch (l.type()) {
                case DISC, SPOKES -> {
                    if (st.drawFraction() >= 0.999) FxDraw.disc(vc, f, lc, u, v, R, ang, col, a);
                    else fan(f, vc, pl, R, ang, st.drawStart(), st.drawDirection() * st.drawFraction() * 360, col, a);
                }
                case BAND -> band(f, vc, pl, R, l.inner(), l.repeat(), ang, st.drawStart(),
                        st.drawDirection() * st.drawFraction() * 360, col, a);
                case ARCS -> arcs(f, vc, pl, l, st, SigilTimeline.assemble(d, i, t), R, col, a);
                default -> {}
            }
        }
    }

    private record Plane(Vec3 c, Vec3 u, Vec3 v, Vec3 n) {
        Vec3 at(double x, double y, double z) {
            return c.add(u.scale(x)).add(v.scale(y)).add(n.scale(z));
        }

        Vec3 polar(double rho, double deg) {
            double k = Math.toRadians(deg);
            return at(Math.cos(k) * rho, Math.sin(k) * rho, 0);
        }
    }

    /** Texture coordinate of a disc point at polar (rho, deg) when the texture is turned by rot. */
    private static float du(double rho, double deg, double R, double rot) {
        return (float) (0.5 + Math.cos(Math.toRadians(deg - rot)) * rho / (2 * R));
    }

    private static float dv(double rho, double deg, double R, double rot) {
        return (float) (0.5 - Math.sin(Math.toRadians(deg - rot)) * rho / (2 * R));
    }

    /** Partial disc: sector from `from` sweeping `sweep` degrees (sign = direction). */
    private static void fan(Frame f, VertexConsumer vc, Plane p, double R, double rot, double from, double sweep, int col, double a) {
        if (Math.abs(sweep) < 0.5) return;
        int n = Math.max(3, (int) Math.ceil(Math.abs(sweep) / 7.5));
        for (int i = 0; i < n; i++) {
            double a0 = from + sweep * i / n, a1 = from + sweep * (i + 1) / n;
            FxDraw.vert(vc, f, p.c, 0.5f, 0.5f, col, a);
            FxDraw.vert(vc, f, p.c, 0.5f, 0.5f, col, a);
            FxDraw.vert(vc, f, p.polar(R, a0), du(R, a0, R, rot), dv(R, a0, R, rot), col, a);
            FxDraw.vert(vc, f, p.polar(R, a1), du(R, a1, R, rot), dv(R, a1, R, rot), col, a);
        }
    }

    /** Ring from inner·R to R, texture repeated `repeat` times around (u along, v 0 outside → 1 inside). */
    private static void band(Frame f, VertexConsumer vc, Plane p, double R, double inner, int repeat, double rot, double from, double sweep,
                             int col, double a) {
        if (Math.abs(sweep) < 0.5) return;
        double ri = R * inner;
        if (ri >= R - 1e-4) ri = R * 0.86;
        int n = Math.max(8, (int) Math.ceil(Math.abs(sweep) / 360 * Math.max(48, repeat * 8)));
        for (int i = 0; i < n; i++) {
            double a0 = from + sweep * i / n, a1 = from + sweep * (i + 1) / n;
            float u0 = (float) ((a0 - rot) / 360 * repeat), u1 = (float) ((a1 - rot) / 360 * repeat);
            FxDraw.vert(vc, f, p.polar(R, a0), u0, 0, col, a);
            FxDraw.vert(vc, f, p.polar(ri, a0), u0, 1, col, a);
            FxDraw.vert(vc, f, p.polar(ri, a1), u1, 1, col, a);
            FxDraw.vert(vc, f, p.polar(R, a1), u1, 0, col, a);
        }
    }

    private static void arcs(Frame f, VertexConsumer vc, Plane p, Layer l, LayerState st, double asm, double R, int col, double a) {
        int count = Math.max(1, l.count());
        double ra = R * st.arcRadiusMul(), w = Math.max(0.02, l.width() * R);
        double len = st.arcLength();
        for (int k = 0; k < count; k++) {
            double mid = st.arcOffset(k, count, asm) + st.angle();
            int seg = Math.max(4, (int) (len / 6));
            for (int i = 0; i < seg; i++) {
                double a0 = mid - len / 2 + len * i / seg, a1 = mid - len / 2 + len * (i + 1) / seg;
                float u0 = (float) i / seg, u1 = (float) (i + 1) / seg;
                FxDraw.vert(vc, f, p.polar(ra + w / 2, a0), u0, 0, col, a);
                FxDraw.vert(vc, f, p.polar(ra - w / 2, a0), u0, 1, col, a);
                FxDraw.vert(vc, f, p.polar(ra - w / 2, a1), u1, 1, col, a);
                FxDraw.vert(vc, f, p.polar(ra + w / 2, a1), u1, 0, col, a);
            }
        }
    }

    // ---------------------------------------------------------------- inscriptions (T07)

    private record TextCache(String text, SigilText.Layout layout) {}

    /**
     * Text layer: letters laid out by {@link SigilText#layout} (sigil units, so × G = gs · grow), turned with the layer by rot,
     * each a square with its atlas cell, written in letter by letter ({@link SigilTimeline#letter}). Letters of one atlas go in one batch.
     */
    private static void text(Frame f, SigilRun r, SigilDef d, Layer l, int index, double t, Plane p, double G, double rot, int col, double a) {
        SigilText.Spec sp = l.text();
        if (sp == null || G <= 1e-5) return;
        String txt = SigilText.textFor(sp, r.texts);
        TextCache tc = r.textCache.get(index) instanceof TextCache c && c.text.equals(txt) ? c : null;
        if (tc == null) {
            tc = new TextCache(txt, SigilText.layout(sp, txt, l.radius(), FxLib.font(sp.font()), FxLib::font));
            r.textCache.put(index, tc);
        }
        SigilText.Layout lay = tc.layout;
        if (lay.letters().isEmpty()) return;
        Double changed = sp.slot() == null ? null : r.textChanged.get(sp.slot());
        double since = changed == null ? Double.NaN : t - changed;
        double k = Math.toRadians(rot), cs = Math.cos(k), sn = Math.sin(k);
        // one batch per atlas (usually one; a fallback font adds a second): switching buffers per letter would flush every time
        java.util.LinkedHashSet<String> atlases = new java.util.LinkedHashSet<>();
        for (SigilText.Letter le : lay.letters()) atlases.add(le.texture());
        for (String want : atlases) {
            VertexConsumer vc = f.add(FxDraw.tex(want));
            for (SigilText.Letter le : lay.letters()) {
                if (!le.texture().equals(want)) continue;
                SigilText.LetterState ls = SigilTimeline.letter(d, index, le.order(), lay.perCopy(), t, since);
                double la = a * ls.alpha() * ls.brightness();
                if (la <= 0.002) continue;
                double x = (le.x() * cs - le.y() * sn) * G, y = (le.x() * sn + le.y() * cs) * G, h = le.size() * G * ls.scale() / 2;
                double up = Math.toRadians(le.up() + rot), ux = Math.cos(up), uy = Math.sin(up), rx = uy, ry = -ux;   // right = up − 90°
                float[] uv = le.uv();
                FxDraw.vert(vc, f, p.at(x + (-rx + ux) * h, y + (-ry + uy) * h, 0), uv[0], uv[1], col, la);        // top left
                FxDraw.vert(vc, f, p.at(x + (-rx - ux) * h, y + (-ry - uy) * h, 0), uv[0], uv[3], col, la);        // bottom left
                FxDraw.vert(vc, f, p.at(x + (rx - ux) * h, y + (ry - uy) * h, 0), uv[2], uv[3], col, la);          // bottom right
                FxDraw.vert(vc, f, p.at(x + (rx + ux) * h, y + (ry + uy) * h, 0), uv[2], uv[1], col, la);          // top right
            }
        }
    }

    // ---------------------------------------------------------------- pieces

    private static void pieces(Frame f, VertexConsumer vc, Plane p, SigilDef d, Layer l, int index, double t, double stopAt, double R,
                               double rot, int col, double a) {
        SigilDef.Pieces pc = l.appear().pieces() != null ? l.appear().pieces() : SigilDef.Pieces.DEFAULT;
        int n = pc.count();
        double sector = 360.0 / n;
        boolean band = l.type() == LayerType.BAND;
        double ri = band ? R * l.inner() : 0;
        for (int k = 0; k < n; k++) {
            PieceState ps = SigilTimeline.piece(d, index, k, t, stopAt);
            double pa = a * ps.alpha() * ps.brightness();
            if (pa <= 0.002) continue;
            double s0 = k * sector + rot, s1 = (k + 1) * sector + rot;
            double cAng = ps.centerAngle() + rot, cR = ps.centerRadius() * R;
            double ck = Math.toRadians(cAng);
            double cx = Math.cos(ck) * cR, cy = Math.sin(ck) * cR;
            double nk = Math.toRadians(cAng + ps.orbit()), nr = cR * ps.radialMul();
            double nx = Math.cos(nk) * nr, ny = Math.sin(nk) * nr, nz = ps.lift() * R;
            double spin = Math.toRadians(ps.spin() + ps.orbit()), tilt = Math.toRadians(ps.tilt());
            double tx = -Math.sin(ck), ty = Math.cos(ck);                       // tangent at the rest centre
            int seg = Math.max(2, (int) Math.ceil(sector / 8));
            for (int i = 0; i < seg; i++) {
                double a0 = s0 + (s1 - s0) * i / seg, a1 = s0 + (s1 - s0) * (i + 1) / seg;
                double[][] pts = band
                        ? new double[][] {{R, a0}, {ri, a0}, {ri, a1}, {R, a1}}
                        : new double[][] {{0, a0}, {0, a0}, {R, a0}, {R, a1}};
                for (double[] q : pts) {
                    double qk = Math.toRadians(q[1]);
                    double x = Math.cos(qk) * q[0] - cx, y = Math.sin(qk) * q[0] - cy, z = 0;
                    double xs = x * Math.cos(spin) - y * Math.sin(spin), ys = x * Math.sin(spin) + y * Math.cos(spin);
                    // tilt around the tangent (tx, ty, 0): Rodrigues
                    double dot = xs * tx + ys * ty, cs = Math.cos(tilt), sn = Math.sin(tilt);
                    double crx = ty * z, cry = -tx * z, crz = tx * ys - ty * xs;
                    double rx = xs * cs + crx * sn + tx * dot * (1 - cs);
                    double ry = ys * cs + cry * sn + ty * dot * (1 - cs);
                    double rz = z * cs + crz * sn;
                    Vec3 w = p.at(nx + rx, ny + ry, nz + rz);
                    float uu, vv;
                    if (band) {
                        uu = (float) ((q[1] - rot) / 360 * l.repeat());
                        vv = q[0] >= R - 1e-6 ? 0 : 1;
                    } else {
                        uu = du(q[0], q[1], R, rot);
                        vv = dv(q[0], q[1], R, rot);
                    }
                    FxDraw.vert(vc, f, w, uu, vv, col, pa);
                }
            }
        }
    }

    // ---------------------------------------------------------------- formed flash

    private static void flash(Frame f, SigilRun r, SigilDef d, double t, Vec3 c, Basis bs, double gs, double ga) {
        SigilDef.Flash fl = d.formedFlash();
        if (fl == null) return;
        double since = t - SigilTimeline.timings(d).formedAt();
        if (since < 0 || since > fl.duration()) return;
        double p = since / Math.max(1, fl.duration());
        double e = Easing.EASE_OUT_CUBIC.apply(p);
        double fade = (1 - p) * ga;
        FxDraw.disc(f.add(RING), f, c.add(bs.n.scale(0.06)), bs.u, bs.v, gs * fl.size() * (0.25 + 0.75 * e), 0, fl.color(), fade * 1.4);
        FxDraw.billboard(f.add(GLOW), f, c, gs * 0.7 * (1 - 0.5 * p), 0, fl.color(), fade);
        if (f.low() || fl.sparks() <= 0) return;
        SplittableRandom rnd = new SplittableRandom(r.seed ^ 0x51A1L);
        VertexConsumer vc = f.add(SPARK);
        for (int i = 0; i < fl.sparks(); i++) {
            double ang = rnd.nextDouble() * Math.PI * 2, sp = 0.5 + rnd.nextDouble() * 0.8, up = (rnd.nextDouble() - 0.3) * 0.6;
            double dist = gs * fl.size() * sp * e;
            Vec3 pos = c.add(bs.u.scale(Math.cos(ang) * dist)).add(bs.v.scale(Math.sin(ang) * dist)).add(bs.n.scale(up * gs * e));
            FxDraw.billboard(vc, f, pos, 0.08 + 0.06 * (1 - p), 0, fl.color(), fade);
        }
    }
}
