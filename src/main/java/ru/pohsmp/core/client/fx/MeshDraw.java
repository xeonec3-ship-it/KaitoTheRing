package ru.pohsmp.core.client.fx;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import ru.pohsmp.core.client.fx.FxDraw.Frame;
import ru.pohsmp.core.fx.FxMath;
import ru.pohsmp.core.fx.FxStyle;
import ru.pohsmp.core.fx.sigil.Easing;
import ru.pohsmp.core.fx.sigil.SigilDef;
import ru.pohsmp.core.fx.sigil.SigilHit;

/**
 * Generated structures described by parts (docs/fx.md, "mesh"): seed polyhedron, rings that tumble into the plane,
 * polygon frames, flying facets, textured discs, volumes of boxes (the Gate). The structure plane is local XY (X to the right of `yaw`, Y up),
 * its centre `center` blocks above the anchor; stopping collapses it to a point.
 */
public final class MeshDraw {
    private MeshDraw() {}

    public static final class Run {
        public JsonObject def;
        public FxStyle style;
        public Vec3 base = Vec3.ZERO, offset = Vec3.ZERO;
        public Entity follow;
        public float yaw, pitch;
        public double start, scale = 1, alpha = 1, stopAt = Double.NaN;
        /** Optional (docs/fx.md, mesh): move - comes out of a point to its place; hinge - turns on a hinge (gate doors). */
        public JsonObject move, hinge;

        Vec3 pos(float pt) {
            return follow != null && follow.isAlive() ? follow.getPosition(pt).add(offset) : base;
        }

        public void stop(double t) {
            if (Double.isNaN(stopAt)) stopAt = Math.max(0, t);
        }

        /** T08: hits waiting to be placed (world point) and the placed ones (unit direction from the centre, local axes). */
        final java.util.List<Object[]> pending = new java.util.ArrayList<>();
        final java.util.List<DomeHit> hits = new java.util.ArrayList<>();

        /** A hit at world point {@code at}, {@code tick} ticks after the start (FxMsg HIT); only meshes with "hit" answer. */
        public void hit(Vec3 at, double tick, double power, int seed) {
            if (def != null && hitOf(def) != null && Double.isNaN(stopAt) && pending.size() < 16) pending.add(new Object[] {at, tick, power, seed});
        }
    }

    /** A hit on a dome-like mesh: direction from its centre (local, unit) and the timing/power/seed. */
    record DomeHit(Vector3f dir, SigilHit.Event e) {}

    private static final java.util.Map<JsonObject, java.util.Optional<SigilDef.Hit>> HIT_DEFS =
            java.util.Collections.synchronizedMap(new java.util.WeakHashMap<>());

    /** "hit" of a mesh file (same fields as a sigil's, docs/sigils.md), or null. */
    static SigilDef.Hit hitOf(JsonObject def) {
        return HIT_DEFS.computeIfAbsent(def, d -> java.util.Optional.ofNullable(SigilDef.parseHit(d))).orElse(null);
    }

    /** Ticks after the start at which the structure is complete ("formedAt" in the file). */
    public static int formedAt(JsonObject def) {
        return def.has("formedAt") ? def.get("formedAt").getAsInt() : 0;
    }

    /** Returns false once a stopped structure has collapsed. */
    public static boolean draw(Frame f, Run r) {
        if (r.def == null) return false;
        double t = f.time() - r.start;
        if (t < 0) return true;
        double s = r.scale;
        if (!Double.isNaN(r.stopAt)) {
            JsonObject col = r.def.has("collapse") ? r.def.getAsJsonObject("collapse") : new JsonObject();
            double dur = col.has("duration") ? col.get("duration").getAsDouble() : 20;
            double d = (t - r.stopAt) / Math.max(1, dur);
            if (d >= 1) return false;
            s *= 1 - Easing.byName(col.has("easing") ? col.get("easing").getAsString() : "easeInCubic").apply(d);
        }
        if (s <= 1e-3) return true;
        double center = r.def.has("center") ? r.def.get("center").getAsDouble() : 0;
        Vec3 o = r.pos(f.pt()).add(0, center * r.scale, 0);
        FxMath.Vec rt = FxMath.right(r.yaw), fw = FxMath.forward(r.yaw);
        // pitch (Minecraft sense, positive looks down) tilts forward and up around the right axis: a spear points along its flight
        double pr = Math.toRadians(r.pitch), cp = Math.cos(pr), sp = Math.sin(pr);
        Vec3 fwd = new Vec3(fw.x() * cp, -sp, fw.z() * cp), up = new Vec3(fw.x() * sp, cp, fw.z() * sp);
        Vec3 right = new Vec3(rt.x(), rt.y(), rt.z());
        if (r.move != null) {   // out of the point at + from (blocks, model axes: x right, y up, z forward) and scale scaleFrom
            JsonObject mv = r.move;
            double k = Easing.byName(str(mv, "easing", "easeOutCubic")).apply(FxDraw.clamp01((t - num(mv, "delay", 0)) / Math.max(1, num(mv, "duration", 1))));
            JsonArray from = mv.has("from") ? mv.getAsJsonArray("from") : null;
            if (from != null && from.size() >= 3) {
                double q = (1 - k) * r.scale;
                o = o.add(right.scale(from.get(0).getAsDouble() * q)).add(up.scale(from.get(1).getAsDouble() * q)).add(fwd.scale(from.get(2).getAsDouble() * q));
            }
            double sf = num(mv, "scaleFrom", 1);
            s *= sf + (1 - sf) * k;
        }
        double hc = 1, hs = 0, hx = 0, hz = 0;
        if (r.hinge != null) {   // turn about the vertical through pivot (model coordinates), as the preview: x' = x c + z s, z' = -x s + z c
            JsonObject h = r.hinge;
            double k = Easing.byName(str(h, "easing", "easeInOutCubic")).apply(FxDraw.clamp01((t - num(h, "delay", 0)) / Math.max(1, num(h, "duration", 1))));
            double ang = Math.toRadians(num(h, "angle", 0) * k);
            hc = Math.cos(ang);
            hs = Math.sin(ang);
            JsonArray pv = h.has("pivot") ? h.getAsJsonArray("pivot") : null;
            if (pv != null && pv.size() >= 3) {
                hx = pv.get(0).getAsDouble();
                hz = pv.get(2).getAsDouble();
            }
        }
        Axes ax = new Axes(o, right, up, fwd, s, hc, hs, hx, hz);
        SigilDef.Hit hit = hitOf(r.def);
        if (hit != null) {                       // T08: place new hits (directions on the dome), flinch while they last
            for (Object[] p : r.pending) {
                Vec3 d = ((Vec3) p[0]).subtract(o);
                Vector3f dir = new Vector3f((float) d.dot(ax.x()), (float) d.dot(ax.y()), (float) d.dot(ax.z()));
                if (dir.lengthSquared() < 1e-8) continue;
                dir.normalize();
                r.hits.removeIf(h -> !SigilHit.alive(hit, h.e(), t));
                while (r.hits.size() >= hit.max()) r.hits.remove(0);
                r.hits.add(new DomeHit(dir, new SigilHit.Event(0, 0, (double) p[1], (double) p[2], (int) p[3])));
            }
            r.pending.clear();
            r.hits.removeIf(h -> !SigilHit.alive(hit, h.e(), t));
            if (!r.hits.isEmpty()) {
                double k = 1;
                for (DomeHit h : r.hits) k *= SigilHit.flinch(hit, h.e(), t);
                ax = new Axes(o, right, up, fwd, s * k, hc, hs, hx, hz);
            }
        } else r.pending.clear();
        if (!r.def.has("parts")) return true;
        for (JsonElement pe : r.def.getAsJsonArray("parts")) {
            JsonObject p = pe.getAsJsonObject();
            JsonObject ap = p.has("appear") ? p.getAsJsonObject("appear") : new JsonObject();
            double delay = num(ap, "delay", 0), dur = Math.max(1, num(ap, "duration", 1));
            if (t < delay) continue;
            double e = Easing.byName(str(ap, "easing", "linear")).apply((t - delay) / dur);
            double lin = FxDraw.clamp01((t - delay) / dur);
            int col = r.style.color(str(p, "color", "@primary"));
            double a = num(p, "brightness", 1) * r.alpha;
            switch (str(p, "type", "")) {
                case "seed" -> seed(f, ax, p, t, e, r.style.color(str(p, "color", "@core")), a);
                case "facet" -> facet(f, ax, p, e, lin, col, a);
                case "ring" -> ring(f, ax, p, t, e, lin, col, a);
                case "polygon" -> polygon(f, ax, p, t, e, lin, col, a);
                case "disc" -> disc(f, ax, p, t, e, lin, col, a);
                case "boxes" -> boxes(f, ax, p, r.style, t >= delay ? e : 0, a, hit, r.hits, t);
                default -> {}
            }
        }
        if (hit != null && !r.hits.isEmpty()) domeHits(f, ax, r, hit, t);
        return true;
    }

    /** Flash where the dome was struck and sparks flying off its surface (outward along the normal there). */
    private static void domeHits(Frame f, Axes ax, Run r, SigilDef.Hit h, double t) {
        int col = h.color() >= 0 ? h.color() : r.style.color("@core");
        VertexConsumer glow = f.add(FxDraw.tex("glow"));
        for (DomeHit dh : r.hits) {
            double age = t - dh.e().at();
            FxDraw.billboard(glow, f, ax.at(dh.dir()), ax.s() * 0.18 * (1 + age / 6), 0, col, dh.e().power() * Math.exp(-age / 3) * r.alpha);
        }
        if (f.low()) return;
        VertexConsumer spark = f.add(FxDraw.tex("spark_soft"));
        for (DomeHit dh : r.hits) {
            Vec3 n = ax.x().scale(dh.dir().x).add(ax.y().scale(dh.dir().y)).add(ax.z().scale(dh.dir().z)).normalize();
            Vec3 u = n.cross(Math.abs(n.y) > 0.9 ? new Vec3(1, 0, 0) : new Vec3(0, 1, 0)).normalize(), v = n.cross(u);
            Vec3 at = ax.at(dh.dir());
            for (int i = 0, k = SigilHit.sparkCount(h, dh.e()); i < k; i++) {
                SigilHit.Spark s = SigilHit.spark(h, dh.e(), i, t);
                if (s.alpha() <= 0.002) continue;
                Vec3 q = at.add(u.scale(s.u())).add(v.scale(s.v())).add(n.scale(s.n())).add(0, -s.drop(), 0);
                FxDraw.billboard(spark, f, q, s.size(), 0, col, s.alpha() * r.alpha);
            }
        }
    }

    /** Local (x, y, z) -> world: x right, y up, z forward, scaled. */
    private record Axes(Vec3 o, Vec3 x, Vec3 y, Vec3 z, double s, double hc, double hs, double hx, double hz) {
        Axes(Vec3 o, Vec3 x, Vec3 y, Vec3 z, double s) {
            this(o, x, y, z, s, 1, 0, 0, 0);
        }

        Vec3 at(double lx, double ly, double lz) {
            if (hs != 0 || hc != 1) {   // hinge: turn around the vertical through (hx, hz)
                double dx = lx - hx, dz = lz - hz;
                lx = hx + dx * hc + dz * hs;
                lz = hz - dx * hs + dz * hc;
            }
            return o.add(x.scale(lx * s)).add(y.scale(ly * s)).add(z.scale(lz * s));
        }

        Vec3 at(Vector3f v) {
            return at(v.x, v.y, v.z);
        }
    }

    private static final Vec3[] OCTA = {new Vec3(1, 0, 0), new Vec3(-1, 0, 0), new Vec3(0, 1, 0), new Vec3(0, -1, 0), new Vec3(0, 0, 1), new Vec3(0, 0, -1)};
    private static final int[][] OCTA_F = {{0, 2, 4}, {2, 1, 4}, {1, 3, 4}, {3, 0, 4}, {2, 0, 5}, {1, 2, 5}, {3, 1, 5}, {0, 3, 5}};

    private static void seed(Frame f, Axes ax, JsonObject p, double t, double e, int col, double a) {
        double r = num(p, "radius", 0.3) * Math.max(0, e);
        if (p.has("vanish")) {   // as in the preview: the seed keeps its size and fades out
            JsonObject v = p.getAsJsonObject("vanish");
            a *= 1 - FxDraw.clamp01((t - num(v, "delay", 0)) / Math.max(1, num(v, "duration", 1)));
        }
        if (r <= 1e-3 || a <= 1e-3) return;
        JsonArray sp = p.has("spin") ? p.getAsJsonArray("spin") : null;
        double sec = t / 20;
        Quaternionf q = new Quaternionf().rotateXYZ(
                (float) Math.toRadians(sp != null ? sp.get(0).getAsDouble() * sec : 0),
                (float) Math.toRadians(sp != null ? sp.get(1).getAsDouble() * sec : 0),
                (float) Math.toRadians(sp != null && sp.size() > 2 ? sp.get(2).getAsDouble() * sec : 0));
        Vec3[] w = new Vec3[6];
        for (int i = 0; i < 6; i++) {
            Vector3f v = new Vector3f((float) (OCTA[i].x * r), (float) (OCTA[i].y * r), (float) (OCTA[i].z * r));
            q.transform(v);
            w[i] = ax.at(v);
        }
        VertexConsumer vc = f.add(FxDraw.WHITE);
        for (int[] fc : OCTA_F) FxDraw.tri(vc, f, w[fc[0]], w[fc[1]], w[fc[2]], col, a * 0.35);
        double lw = 0.025 * ax.s;
        for (int[] fc : OCTA_F) for (int k = 0; k < 3; k++)
            if (fc[k] < fc[(k + 1) % 3]) FxDraw.line(vc, f, w[fc[k]], w[fc[(k + 1) % 3]], lw, 0xFFFFFF, a);
    }

    private static void facet(Frame f, Axes ax, JsonObject p, double e, double lin, int col, double a) {
        JsonArray from = p.getAsJsonArray("from"), to = p.getAsJsonArray("to");
        if (from == null || to == null || from.size() < 3 || to.size() < 3) return;
        Vector3f[] pts = new Vector3f[3];
        Vector3f cen = new Vector3f();
        for (int i = 0; i < 3; i++) {
            Vector3f a0 = vec(from.get(i).getAsJsonArray()), b0 = vec(to.get(i).getAsJsonArray());
            pts[i] = a0.lerp(b0, (float) e, new Vector3f());
            cen.add(pts[i]);
        }
        cen.div(3);
        // as in the preview: the facet turns in the portal plane while it flies (a whole turn by the end)
        float spin = (float) Math.toRadians(num(p, "spinOnFly", 0) * e);
        Quaternionf q = new Quaternionf().rotateZ(spin);
        Vec3[] w = new Vec3[3];
        for (int i = 0; i < 3; i++) {
            Vector3f v = new Vector3f(pts[i]).sub(cen);
            q.transform(v);
            w[i] = ax.at(v.add(cen));
        }
        double al = a * Math.min(1, lin * 3);
        FxDraw.tri(f.add(FxDraw.WHITE), f, w[0], w[1], w[2], col, al);
    }

    /** A line of the structure: a coloured core (keeps its colour in daylight) with an additive glow on it, as thick as in the preview. */
    private static void bar(Frame f, Vec3 p0, Vec3 p1, double w, int col, double al) {
        FxDraw.line(f.trans(FxDraw.WHITE), f, p0, p1, w, col, Math.min(0.9, al * 0.85));
        FxDraw.line(f.add(FxDraw.WHITE), f, p0, p1, w, col, al * 0.5);
    }

    private static void ring(Frame f, Axes ax, JsonObject p, double t, double e, double lin, int col, double a) {
        double R = num(p, "radius", 1), th = num(p, "thickness", 0.05);
        JsonArray axis = p.has("tiltAxis") ? p.getAsJsonArray("tiltAxis") : null;
        Vector3f tAx = axis != null ? vec(axis) : new Vector3f(1, 0, 0);
        if (tAx.lengthSquared() < 1e-6) tAx.set(1, 0, 0);
        tAx.normalize();
        double settled = t - (num(p.getAsJsonObject("appear"), "delay", 0) + num(p.getAsJsonObject("appear"), "duration", 1));
        float tilt = (float) Math.toRadians(num(p, "tiltTurns", 0) * (1 - e));
        float spin = (float) Math.toRadians(num(p, "spin", 0) * Math.max(0, settled) / 20);
        Quaternionf q = new Quaternionf().rotationAxis(tilt, tAx).rotateZ(spin);
        double grow = Math.max(1e-3, e);   // as in the preview: the ring grows from a point
        int n = 64;
        Vec3[] pts = new Vec3[n];
        for (int i = 0; i < n; i++) {
            double k = Math.PI * 2 * i / n;
            Vector3f v = new Vector3f((float) (Math.cos(k) * R * grow), (float) (Math.sin(k) * R * grow), 0);
            q.transform(v);
            pts[i] = ax.at(v);
        }
        double al = a * Math.min(1, lin * 3);
        for (int i = 0; i < n; i++) bar(f, pts[i], pts[(i + 1) % n], th * 2 * grow * ax.s, col, al);
    }

    private static void polygon(Frame f, Axes ax, JsonObject p, double t, double e, double lin, int col, double a) {
        int sides = Math.max(3, (int) num(p, "sides", 6));
        double R = num(p, "radius", 1) * Math.max(0, e), th = num(p, "thickness", 0.04);
        double settled = t - (num(p.getAsJsonObject("appear"), "delay", 0));
        double rot = Math.toRadians(num(p, "rotation", 0) + num(p, "spin", 0) * settled / 20);
        Vec3[] v = new Vec3[sides];
        for (int i = 0; i < sides; i++) {
            double k = rot + Math.PI * 2 * i / sides;   // the first corner at `rotation`, as in the preview
            v[i] = ax.at(Math.cos(k) * R, Math.sin(k) * R, 0);
        }
        double al = a * Math.min(1, lin * 3);
        for (int i = 0; i < sides; i++) bar(f, v[i], v[(i + 1) % sides], th * Math.max(0, e) * ax.s, col, al);
    }

    private static void disc(Frame f, Axes ax, JsonObject p, double t, double e, double lin, int col, double a) {
        double R = num(p, "radius", 1) * ax.s;   // as in the preview: full size at once, it only fades in
        double rot = num(p, "spin", 0) * t / 20;
        double al = a * FxDraw.clamp01(e);
        if (al <= 1e-3) return;
        boolean dark = "translucent".equals(str(p, "blend", "additive"));
        VertexConsumer vc = dark ? f.trans(FxDraw.tex(str(p, "texture", "glow"))) : f.add(FxDraw.tex(str(p, "texture", "glow")));
        FxDraw.disc(vc, f, ax.o, ax.x, ax.y, R, rot, col, dark ? Math.min(0.85, al) : al);
    }

    // ---------------------------------------------------------------- boxes (volumes: the Gate of T03)

    /** One box, prepared once per part: 8 corners in local space (rotation applied), tone, centre height. */
    private record Box(Vector3f[] c, int tone, double y, float[] shade) {}

    private static final java.util.Map<JsonObject, Box[]> BOXES = java.util.Collections.synchronizedMap(new java.util.WeakHashMap<>());
    /** Faces as corner indices (bit 0 = x1, bit 1 = y1, bit 2 = z1) and their local normals. */
    private static final int[][] FACES = {{1, 3, 7, 5}, {0, 4, 6, 2}, {2, 6, 7, 3}, {0, 1, 5, 4}, {4, 5, 7, 6}, {0, 2, 3, 1}};
    private static final float[][] NORMALS = {{1, 0, 0}, {-1, 0, 0}, {0, 1, 0}, {0, -1, 0}, {0, 0, 1}, {0, 0, -1}};

    private static Box[] prepare(JsonObject p) {
        return BOXES.computeIfAbsent(p, k -> {
            JsonArray arr = p.getAsJsonArray("boxes");
            boolean shadeOn = !p.has("shade") || p.get("shade").getAsBoolean();
            Box[] out = new Box[arr == null ? 0 : arr.size()];
            for (int i = 0; i < out.length; i++) {
                JsonArray b = arr.get(i).getAsJsonArray();
                float x0 = b.get(0).getAsFloat(), y0 = b.get(1).getAsFloat(), z0 = b.get(2).getAsFloat();
                float x1 = b.get(3).getAsFloat(), y1 = b.get(4).getAsFloat(), z1 = b.get(5).getAsFloat();
                Vector3f cen = new Vector3f((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
                Quaternionf q = null;
                if (b.size() > 7 && b.get(7).isJsonArray()) {
                    JsonArray r = b.get(7).getAsJsonArray();
                    // three.js Euler "YXZ" as in the preview and docs/fx.md: R = Ry·Rx·Rz (roll first, then pitch, then yaw)
                    q = new Quaternionf().rotateY((float) Math.toRadians(r.get(1).getAsDouble()))
                            .rotateX((float) Math.toRadians(r.get(0).getAsDouble()))
                            .rotateZ((float) Math.toRadians(r.size() > 2 ? r.get(2).getAsDouble() : 0));
                }
                Vector3f[] c = new Vector3f[8];
                for (int j = 0; j < 8; j++) {
                    Vector3f v = new Vector3f((j & 1) != 0 ? x1 : x0, (j & 2) != 0 ? y1 : y0, (j & 4) != 0 ? z1 : z0).sub(cen);
                    if (q != null) q.transform(v);
                    c[j] = v.add(cen);
                }
                float[] shade = new float[6];
                for (int fi = 0; fi < 6; fi++) {
                    Vector3f n = new Vector3f(NORMALS[fi][0], NORMALS[fi][1], NORMALS[fi][2]);
                    if (q != null) q.transform(n);
                    float ax = Math.abs(n.x), ay = Math.abs(n.y), az = Math.abs(n.z);
                    // top x1.0, sides x0.82 / x0.7, bottom x0.55 (docs/fx.md), so the volume reads in full-bright light
                    shade[fi] = !shadeOn ? 1f : ay >= ax && ay >= az ? (n.y > 0 ? 1f : 0.55f) : ax >= az ? 0.82f : 0.7f;
                }
                out[i] = new Box(c, b.size() > 6 ? b.get(6).getAsInt() : 0, cen.y, shade);
            }
            return out;
        });
    }

    private static int mul(int rgb, float k) {
        return (Math.min(255, (int) (((rgb >> 16) & 255) * k)) << 16) | (Math.min(255, (int) (((rgb >> 8) & 255) * k)) << 8) | Math.min(255, (int) ((rgb & 255) * k));
    }

    private static int toWhite(int rgb, double k) {
        int r = (rgb >> 16) & 255, g = (rgb >> 8) & 255, b = rgb & 255;
        return ((int) (r + (255 - r) * k) << 16) | ((int) (g + (255 - g) * k) << 8) | (int) (b + (255 - b) * k);
    }

    /**
     * Volume of boxes [x0, y0, z0, x1, y1, z1, tone, [rx, ry, rz]?] (docs/fx.md, "boxes"). Glowing tones are additive at full brightness,
     * the others translucent with `opacity` and shaded by face. Appear "reveal: down": a front runs from bounds[1] to bounds[0], a box shows
     * once the front passes its centre ("up": from bounds[0] upwards, the crystal growing) (a band `front` blocks wide fades it in with a white flash), and a bright bar marks the front.
     */
    private static void boxes(Frame f, Axes ax, JsonObject p, FxStyle style, double e, double a, SigilDef.Hit hit,
                              java.util.List<DomeHit> hits, double t) {
        if (a <= 1e-3) return;
        Box[] bs = prepare(p);
        if (bs.length == 0) return;
        JsonArray tonesJ = p.getAsJsonArray("tones");
        int[] tones = new int[tonesJ == null ? 1 : tonesJ.size()];
        for (int i = 0; i < tones.length; i++) tones[i] = tonesJ == null ? 0xFFFFFF : style.color(tonesJ.get(i).getAsString());
        java.util.Set<Integer> glow = new java.util.HashSet<>();
        if (p.has("glowTones")) for (JsonElement g : p.getAsJsonArray("glowTones")) glow.add(g.getAsInt());
        JsonObject ap = p.has("appear") ? p.getAsJsonObject("appear") : new JsonObject();
        String reveal = str(ap, "reveal", "");
        boolean down = "down".equals(reveal), up = "up".equals(reveal), sweep = down || up;
        JsonArray bounds = p.has("bounds") ? p.getAsJsonArray("bounds") : null;
        double lo = bounds != null ? bounds.get(0).getAsDouble() : 0, hi = bounds != null ? bounds.get(1).getAsDouble() : 0;
        double band = Math.max(0.05, num(ap, "front", 0.8));
        double front = down ? hi - (hi - lo + 2) * FxDraw.clamp01(e) : lo + (hi - lo + 2) * FxDraw.clamp01(e);
        double opacity = num(p, "opacity", 1);
        VertexConsumer add = f.add(FxDraw.WHITE);
        // "blend": "additive" - the whole volume is light (the Barrier dome's glass cells); otherwise solid shaded faces
        VertexConsumer solid = "additive".equals(str(p, "blend", "")) ? add : f.solid(FxDraw.WHITE);
        Vec3[] w = new Vec3[8];
        for (Box b : bs) {
            double k = down ? FxDraw.clamp01((b.y() - front + band) / band) : up ? FxDraw.clamp01((front - b.y() + band) / band) : FxDraw.clamp01(e * 3);
            if (k <= 1e-3) continue;
            for (int j = 0; j < 8; j++) w[j] = ax.at(b.c()[j]);
            int base = tones[Math.max(0, Math.min(tones.length - 1, b.tone()))];
            boolean gl = glow.contains(b.tone());
            if (sweep && k < 1) base = toWhite(base, 0.85 * (1 - k));   // the white flash at the front
            double rip = 0;                                              // T08: ripple — the wave of SigilHit along the sphere
            if (hit != null && !hits.isEmpty()) {
                Vector3f c0 = b.c()[0], c7 = b.c()[7];
                Vector3f cen = new Vector3f((c0.x + c7.x) / 2, (c0.y + c7.y) / 2, (c0.z + c7.z) / 2);
                if (cen.lengthSquared() > 1e-8) {
                    cen.normalize();
                    for (DomeHit dh : hits) rip += SigilHit.wave(hit, dh.e(), Math.PI, Math.acos(Math.max(-1, Math.min(1, cen.dot(dh.dir())))), t);
                    rip = Math.min(rip, 2 * hit.strength());
                }
                if (rip > 0.01) base = toWhite(base, Math.min(0.8, 0.5 * rip));
            }
            double lit = 1 + rip * (gl ? 1.5 : 5);
            for (int fi = 0; fi < 6; fi++) {
                int[] q = FACES[fi];
                if (gl) FxDraw.quad(add, f, w[q[0]], w[q[1]], w[q[2]], w[q[3]], base, a * k * lit);
                else FxDraw.quad(solid, f, w[q[0]], w[q[1]], w[q[2]], w[q[3]], mul(base, b.shade()[fi]), Math.min(1, a * k * opacity * lit));
            }
        }
        if (sweep && e > 0 && e < 1)   // the light front sweeping down (or up: the crystal grows from the ground)
            FxDraw.line(add, f, ax.at(-6, front, 0), ax.at(6, front, 0), 0.25 * ax.s, 0xFFFFFF, 0.8 * a);
    }

    private static Vector3f vec(JsonArray a) {
        return new Vector3f(a.get(0).getAsFloat(), a.size() > 1 ? a.get(1).getAsFloat() : 0, a.size() > 2 ? a.get(2).getAsFloat() : 0);
    }

    static double num(JsonObject o, String k, double d) {
        return o != null && o.has(k) ? o.get(k).getAsDouble() : d;
    }

    static String str(JsonObject o, String k, String d) {
        return o != null && o.has(k) ? o.get(k).getAsString() : d;
    }
}
