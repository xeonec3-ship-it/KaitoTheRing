package ru.pohsmp.core.client.fx;

import com.google.gson.JsonObject;
import com.mojang.blaze3d.vertex.VertexConsumer;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.client.fx.FxDraw.Frame;
import ru.pohsmp.core.fx.FxDef;
import ru.pohsmp.core.fx.FxDef.Element;
import ru.pohsmp.core.fx.FxMath;
import ru.pohsmp.core.fx.FxShapes;
import ru.pohsmp.core.fx.FxTrail;

/**
 * Line-like element types of docs/fx.md: trail / ribbon, slash, lightning, vortex, chains. Every line is two layers
 * (soft halo in the colour + hot whitened core, {@link FxDraw#glowStrip}); shapes come from {@link FxShapes} by the effect seed.
 */
final class LineDraw {
    private LineDraw() {}

    // ---------------------------------------------------------------- trail / ribbon

    static void trail(Frame f, FxRun run, Element el, ElementDraw.State st, double te, FxDef.Context ctx, double s, int col, double a,
                      boolean ribbon) {
        JsonObject p = el.params();
        double width = el.num("width", ribbon ? 0.35 : 0.18) * s, length = Math.max(2, el.num("length", 12)), fade = el.num("fade", 1);
        Vec3 at = FxRun.w(el.at().resolve(ctx));
        int segs = f.low() ? 10 : 20;
        List<List<Vec3>> lines = new ArrayList<>();
        if (p.has("orbit") && p.get("orbit").isJsonObject()) {
            JsonObject o = p.getAsJsonObject("orbit");
            double R = MeshDraw.num(o, "radius", 1.2) * s, speed = MeshDraw.num(o, "speed", 8) * run.style.rotationScale();
            double rise = MeshDraw.num(o, "rise", 0) * s, risePeriod = Math.max(1, MeshDraw.num(o, "risePeriod", 40));
            double climb = MeshDraw.num(o, "climb", 0) * s;
            int count = Math.max(1, (int) el.num("count", 1));
            for (int c = 0; c < count; c++) {
                List<Vec3> pts = new ArrayList<>(segs + 1);
                for (int i = 0; i <= segs; i++) {
                    double tt = Math.max(0, te - length * i / segs);
                    double ang = Math.toRadians(speed * tt) + Math.PI * 2 * c / count;
                    double y = rise * Math.sin(Math.PI * 2 * tt / risePeriod + c * 1.7) + climb * tt / 20;
                    pts.add(at.add(Math.cos(ang) * R, y, Math.sin(ang) * R));
                }
                lines.add(pts);
            }
        } else {
            if (st.trail == null) st.trail = new FxTrail(length, 0.04);
            st.trail.add(f.time(), FxRun.v(at));
            List<Vec3> pts = new ArrayList<>();
            for (FxTrail.Sample sm : st.trail.samples()) pts.add(FxRun.w(sm.pos()));
            if (pts.size() < 2) return;
            lines.add(pts);
        }
        String texture = el.str("texture", null);
        for (List<Vec3> pts : lines) {
            int n = pts.size();
            double[] w = new double[n], al = new double[n];
            for (int i = 0; i < n; i++) {
                double k = (double) i / (n - 1);
                w[i] = width * (1 - 0.75 * k);
                al[i] = a * Math.pow(1 - k, fade) * Math.min(1, k * n * 0.8 + 0.6);
            }
            if (ribbon) {
                Vec3[] sides = new Vec3[n];
                for (int i = 0; i < n; i++) sides[i] = new Vec3(0, 1, 0);
                VertexConsumer vc = f.add(FxDraw.tex(texture != null ? run.style.texture(texture) : "strip_soft"));
                FxDraw.strip(vc, f, pts, w, al, col, sides);
                double[] wc = w.clone();
                for (int i = 0; i < n; i++) wc[i] *= 0.3;
                FxDraw.strip(f.add(FxDraw.tex("strip_soft")), f, pts, wc, al, FxDraw.mix(col, 0xFFFFFF, 0.6), null);
            } else {
                FxDraw.glowStrip(f, pts, w, al, col, null, 3);
            }
            double head = el.num("head", ribbon ? 0 : 1.6);
            if (head > 0) FxDraw.billboard(f.add(FxDraw.tex("glow")), f, pts.get(0), width * head, 0, col, a);
        }
    }

    // ---------------------------------------------------------------- slash

    /** A series of `count` arcs every `interval` ticks; each lives `life` ticks: the head runs out in `grow`, the tail catches up. */
    static void slash(Frame f, FxRun run, Element el, double te, Vec3 at, FxDef.Context ctx, double s, int col, double a, long seed) {
        JsonObject p = el.params();
        int count = Math.max(1, (int) el.num("count", 1));
        double interval = el.num("interval", 4), life = Math.max(2, el.num("life", 10)), grow = el.num("grow", 4);
        double radius = el.num("radius", 2.5) * s, arcDeg = el.num("arc", 150), thick = el.num("thickness", 0.35) * s;
        double bend = el.num("bend", 1), tilt0 = el.num("tilt", 0), pitch = el.num("pitch", 0);
        double second = p.has("secondary") ? (p.get("secondary").getAsJsonPrimitive().isBoolean()
                ? (p.get("secondary").getAsBoolean() ? 0.6 : 0) : p.get("secondary").getAsDouble()) : 0.6;
        int dir0 = el.num("dir", 1) < 0 ? -1 : 1;
        Vec3 fwd = FxRun.w(FxMath.forward(ctx.yaw())), right = FxRun.w(FxMath.right(ctx.yaw())), up = new Vec3(0, 1, 0);
        double pr = Math.toRadians(pitch);
        Vec3 v = fwd.scale(Math.cos(pr)).add(up.scale(Math.sin(pr)));
        Vec3 upP = up.scale(Math.cos(pr)).subtract(fwd.scale(Math.sin(pr)));
        int n = f.low() ? 12 : 26;
        SplittableRandom r = new SplittableRandom(seed);
        for (int k = 0; k < count; k++) {
            double jt = r.nextDouble(), jr = r.nextDouble();
            double ts = te - k * interval;
            if (ts < 0 || ts > life) continue;
            double tilt = tilt0 + (p.has("tiltStep") ? el.num("tiltStep", 0) * k : count > 1 ? (jt * 2 - 1) * 70 : 0);
            int dir = (p.has("alternate") && !p.get("alternate").getAsBoolean()) ? dir0 : (k % 2 == 0 ? dir0 : -dir0);
            double tr = Math.toRadians(tilt);
            Vec3 u = right.scale(Math.cos(tr)).add(upP.scale(Math.sin(tr)));
            double rad = radius * (0.9 + 0.2 * jr);
            arc(f, at, u, v, rad, arcDeg, bend, thick, dir, ts, grow, life, n, col, a);
            if (second > 0) arc(f, at, u, v, rad * 0.84, arcDeg * 0.9, bend, thick * 0.3, dir, ts - 1.5, grow, life, n, col, a * second);
        }
    }

    private static void arc(Frame f, Vec3 c, Vec3 u, Vec3 v, double radius, double arcDeg, double bend, double thick, int dir,
                            double ts, double grow, double life, int n, int col, double a) {
        if (ts <= 0) return;
        double[] span = FxShapes.slashSpan(ts, grow, life);
        if (span[1] - span[0] < 0.01) return;
        List<FxMath.Vec> full = FxShapes.slashArc(FxRun.v(c), FxRun.v(u), FxRun.v(v), radius, arcDeg, bend, n, dir);
        List<Vec3> pts = new ArrayList<>(n + 1);
        Vec3[] sides = new Vec3[n + 1];
        double[] w = new double[n + 1], al = new double[n + 1];
        double fade = ts > life * 0.6 ? 1 - (ts - life * 0.6) / (life * 0.4) : 1;
        for (int i = 0; i <= n; i++) {
            double t = span[0] + (span[1] - span[0]) * i / n;           // 0 at the tail .. 1 at the head
            double fi = t * n;
            int i0 = Math.min(n - 1, (int) fi);
            Vec3 pt = FxRun.w(FxShapes.lerp(full.get(i0), full.get(i0 + 1), fi - i0));
            pts.add(pt);
            Vec3 radial = pt.subtract(c);
            sides[i] = radial.lengthSqr() < 1e-9 ? u : radial.normalize();
            double local = (double) i / n;
            w[i] = thick * Math.pow(Math.sin(Math.PI * Math.min(1, 0.04 + local * 0.96)), 0.7) * (0.55 + 0.45 * local);
            al[i] = a * fade * (0.35 + 0.65 * local);
        }
        FxDraw.glowStrip(f, pts, w, al, col, sides, 2.6);
        if (ts < grow + 2) FxDraw.billboard(f.add(FxDraw.tex("spark_sharp")), f, pts.get(n), thick * 2.2, ts * 40, FxDraw.mix(col, 0xFFFFFF, 0.6), a * fade);
    }

    // ---------------------------------------------------------------- lightning

    static void lightning(Frame f, Element el, double te, Vec3 from, Vec3 to, double s, int col, double a, long seed) {
        JsonObject p = el.params();
        if (p.has("fromSky")) {
            to = from;
            from = from.add(0, p.get("fromSky").getAsDouble() * s, 0);
        }
        int branches = (int) el.num("branches", 2), count = Math.max(1, (int) el.num("count", 1));
        int detail = (int) Math.min(7, el.num("detail", f.low() ? 4 : 5));
        double jag = el.num("jaggedness", 0.3), regen = Math.max(1, el.num("regen", 3)), width = el.num("width", 0.12) * s;
        long gen = (long) Math.floor(te / regen);
        for (int b = 0; b < count; b++) {
            long sd = seed * 31 + gen * 131 + b * 17;
            SplittableRandom r = new SplittableRandom(sd);
            double flick = 0.55 + 0.45 * r.nextDouble();
            double since = te - gen * regen;
            double strike = since < 1 ? 1.4 : 1;                       // each new shape lands brighter
            List<FxShapes.Seg> segs = FxShapes.lightning(sd, FxRun.v(from), FxRun.v(to), jag, branches, detail);
            List<Vec3> run = new ArrayList<>();
            int depth = 0;
            for (FxShapes.Seg sg : segs) {
                Vec3 a0 = FxRun.w(sg.a());
                if (!run.isEmpty() && (sg.depth() != depth || run.get(run.size() - 1).distanceToSqr(a0) > 1e-8)) {
                    bolt(f, run, depth, width, col, a * flick * strike);
                    run.clear();
                }
                if (run.isEmpty()) run.add(a0);
                run.add(FxRun.w(sg.b()));
                depth = sg.depth();
            }
            bolt(f, run, depth, width, col, a * flick * strike);
        }
        VertexConsumer g = f.add(FxDraw.tex("glow"));
        FxDraw.billboard(g, f, to, width * 14, 0, col, a * 0.8);
        FxDraw.billboard(g, f, to, width * 4, 0, 0xFFFFFF, a * 0.7);
        FxDraw.billboard(g, f, from, width * 7, 0, col, a * 0.5);
    }

    private static void bolt(Frame f, List<Vec3> pts, int depth, double width, int col, double a) {
        if (pts.size() < 2) return;
        int n = pts.size();
        double[] w = new double[n], al = new double[n];
        double ww = depth == 0 ? width : width * 0.5, aa = depth == 0 ? a : a * 0.7;
        for (int i = 0; i < n; i++) {
            double k = (double) i / (n - 1);
            w[i] = depth == 0 ? ww : ww * (1 - 0.8 * k);
            al[i] = depth == 0 ? aa : aa * (1 - 0.7 * k);
        }
        FxDraw.glowStrip(f, pts, w, al, col, null, 4);
    }

    // ---------------------------------------------------------------- vortex

    static void vortex(Frame f, FxRun run, Element el, double te, Vec3 at, double s, int col, double a, long seed) {
        double R = el.num("radius", 2) * s, h = el.num("height", 3) * s, funnel = el.num("funnel", 0.35), turns = el.num("turns", 1.25);
        int arms = Math.max(1, (int) el.num("arms", 3));
        double speed = el.num("speed", 6) * run.style.rotationScale(), pull = el.num("pull", 0.6), width = el.num("width", 0.22) * s;
        double spin = speed * te;
        int segs = f.low() ? 14 : 28;
        for (int k = 0; k < arms; k++) {
            List<Vec3> pts = new ArrayList<>(segs + 1);
            double[] w = new double[segs + 1], al = new double[segs + 1];
            for (int i = 0; i <= segs; i++) {
                double hh = (double) i / segs;
                pts.add(FxRun.w(FxShapes.spiral(FxRun.v(at), R, h, funnel, turns, k, arms, hh, spin)));
                double env = Math.sin(Math.PI * hh);
                w[i] = width * (0.4 + 0.6 * hh);
                al[i] = a * env * (0.7 + 0.3 * Math.sin(te * 0.25 + k * 2.1 + hh * 6));
            }
            FxDraw.glowStrip(f, pts, w, al, col, null, 3);
        }
        int count = (int) el.num("particles", 18 * arms);
        double life = Math.max(4, el.num("life", 30));
        VertexConsumer vc = f.add(FxDraw.tex(run.style.texture(el.str("texture", "@sparks"))));
        double size = el.num("size", 0.12) * s;
        for (int i = 0; i < count; i += f.low() ? 2 : 1) {
            SplittableRandom r = new SplittableRandom(seed * 17 + i);
            double ph = r.nextDouble(), h0 = r.nextDouble(), a0 = r.nextDouble() * 360;
            double age = (te + ph * life) % life, k = age / life;
            double hh = pull >= 0 ? (h0 * 0.6 + k * 0.4) : h0;
            Vec3 c = FxRun.w(FxShapes.spiral(FxRun.v(at), R * FxShapes.pull(pull, k), h, funnel, turns, 0, 1, Math.min(1, hh), spin * 1.4 + a0 + k * 120));
            FxDraw.billboard(vc, f, c, size * (0.6 + 0.6 * r.nextDouble()), a0 + te * 9, col, a * Math.sin(Math.PI * k));
        }
        FxDraw.billboard(f.add(FxDraw.tex("glow")), f, at.add(0, h * 0.15, 0), R * funnel * 1.6, 0, col, a * 0.45);
    }

    // ---------------------------------------------------------------- chains

    static void chains(Frame f, Element el, double te, Vec3 from, Vec3 to, double s, int col, double a) {
        double link = Math.max(0.05, el.num("link", 0.35) * s), sag = el.num("sag", 0.5) * s, tension = el.num("tension", 0);
        double grow = el.num("grow", 0), rattle = el.num("rattle", 0.03) * s;
        double dist = from.distanceTo(to);
        int n = Math.max(2, Math.min(f.low() ? 40 : 90, (int) Math.ceil(dist / (link * 0.8))));
        List<FxMath.Vec> curve = FxShapes.chain(FxRun.v(from), FxRun.v(to), sag, tension, n);
        double shown = grow > 0 ? FxDraw.clamp01(te / grow) * n : n;
        VertexConsumer vc = f.add(FxDraw.tex("chain_link"));
        List<Vec3> halo = new ArrayList<>();
        int lastShown = 0;
        for (int i = 0; i < n; i++) {
            if (i >= shown) break;
            lastShown = i;
            Vec3 p0 = FxRun.w(curve.get(i)), p1 = FxRun.w(curve.get(i + 1));
            Vec3 d = p1.subtract(p0);
            if (d.lengthSqr() < 1e-9) continue;
            Vec3 dn = d.normalize();
            FxMath.Vec[] pp = FxShapes.perp(FxRun.v(dn));
            Vec3 side = FxRun.w(pp[i % 2]);
            double shake = rattle * tension * Math.sin(te * 2.3 + i * 1.7);
            Vec3 c = p0.add(p1).scale(0.5).add(FxRun.w(pp[(i + 1) % 2]).scale(shake));
            Vec3 hl = dn.scale(d.length() * 0.68), hw = side.scale(link * 0.3);
            double fresh = Math.max(0, 1 - (shown - i) / 3);                // the newest links flare
            int cc = fresh > 0 ? FxDraw.mix(col, 0xFFFFFF, fresh * 0.6) : col;
            double al = a * (1 + fresh * 0.6);
            FxDraw.vert(vc, f, c.subtract(hl).subtract(hw), 0, 0, cc, al);
            FxDraw.vert(vc, f, c.subtract(hl).add(hw), 1, 0, cc, al);
            FxDraw.vert(vc, f, c.add(hl).add(hw), 1, 1, cc, al);
            FxDraw.vert(vc, f, c.add(hl).subtract(hw), 0, 1, cc, al);
            if (halo.isEmpty()) halo.add(p0);
            halo.add(p1);
        }
        if (halo.size() >= 2) {
            int m = halo.size();
            double[] w = new double[m], al = new double[m];
            for (int i = 0; i < m; i++) {
                w[i] = link * 1.4;
                al[i] = a * 0.22;
            }
            FxDraw.strip(f.add(FxDraw.tex("strip_soft")), f, halo, w, al, col, null);
            if (grow > 0 && shown < n) FxDraw.billboard(f.add(FxDraw.tex("glow")), f, halo.get(m - 1), link * 2, 0, col, a);
        }
        if (lastShown >= n - 1 || grow <= 0) {
            VertexConsumer g = f.add(FxDraw.tex("glow"));
            FxDraw.billboard(g, f, from, link * 1.5, 0, col, a * 0.6);
            FxDraw.billboard(g, f, to, link * 1.5, 0, col, a * 0.6);
        }
    }
}
