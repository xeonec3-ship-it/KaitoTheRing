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
import ru.pohsmp.core.fx.sigil.SigilTimeline;
import ru.pohsmp.core.fx.sigil.SigilTimeline.LayerState;
import ru.pohsmp.core.fx.sigil.SigilTimeline.PieceState;

/**
 * Draws a sigil exactly as {@link SigilTimeline} describes it (docs/sigils.md): no shaders, the "draw" reveal is a triangle fan
 * up to the current angle, bands are rings with the texture repeated around, arcs are short ring strips, pieces are sectors
 * flying into place. The plane is (u, v) with normal n; layer tilt (unfold) turns v towards n.
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
        for (int i = 0; i < d.layers().size(); i++) {
            Layer l = d.layers().get(i);
            LayerState st = SigilTimeline.layer(d, i, t, r.stopAt);
            if (!st.visible()) continue;
            double R = gs * st.scale();
            Vec3 lc = c.add(bs.n.scale(l.heightOffset() * r.scale));
            double tl = Math.toRadians(st.tilt());
            Vec3 u = bs.u, v = bs.v.scale(Math.cos(tl)).add(bs.n.scale(Math.sin(tl))), n = bs.n.scale(Math.cos(tl)).subtract(bs.v.scale(Math.sin(tl)));
            int col = r.color >= 0 ? r.color : l.color();
            double a = st.alpha() * ga;
            VertexConsumer vc = f.add(FxDraw.tex(l.texture()));
            Plane pl = new Plane(lc, u, v, n);
            if (l.appear().modes().contains(AppearMode.PIECES)) pieces(f, vc, pl, d, l, i, t, r.stopAt, R, st.angle(), col, a);
            else switch (l.type()) {
                case DISC, SPOKES -> {
                    if (st.drawFraction() >= 0.999) FxDraw.disc(vc, f, lc, u, v, R, st.angle(), col, a);
                    else fan(f, vc, pl, R, st.angle(), st.drawStart(), st.drawDirection() * st.drawFraction() * 360, col, a);
                }
                case BAND -> band(f, vc, pl, R, l.inner(), l.repeat(), st.angle(), st.drawStart(),
                        st.drawDirection() * st.drawFraction() * 360, col, a);
                case ARCS -> arcs(f, vc, pl, l, st, SigilTimeline.assemble(d, i, t), R, col, a);
            }
        }
        flash(f, r, d, t, c, bs, gs, ga);
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
