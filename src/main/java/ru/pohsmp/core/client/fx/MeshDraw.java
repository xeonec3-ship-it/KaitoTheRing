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

/**
 * Generated structures described by parts (docs/fx.md, "mesh"): seed polyhedron, rings that tumble into the plane,
 * polygon frames, flying facets, textured discs. The structure plane is local XY (X to the right of `yaw`, Y up),
 * its centre `center` blocks above the anchor; stopping collapses it to a point.
 */
public final class MeshDraw {
    private MeshDraw() {}

    public static final class Run {
        public JsonObject def;
        public FxStyle style;
        public Vec3 base = Vec3.ZERO, offset = Vec3.ZERO;
        public Entity follow;
        public float yaw;
        public double start, scale = 1, alpha = 1, stopAt = Double.NaN;

        Vec3 pos(float pt) {
            return follow != null && follow.isAlive() ? follow.getPosition(pt).add(offset) : base;
        }

        public void stop(double t) {
            if (Double.isNaN(stopAt)) stopAt = Math.max(0, t);
        }
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
        Axes ax = new Axes(o, new Vec3(rt.x(), rt.y(), rt.z()), new Vec3(0, 1, 0), new Vec3(fw.x(), fw.y(), fw.z()), s);
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
                default -> {}
            }
        }
        return true;
    }

    /** Local (x, y, z) -> world: x right, y up, z forward, scaled. */
    private record Axes(Vec3 o, Vec3 x, Vec3 y, Vec3 z, double s) {
        Vec3 at(double lx, double ly, double lz) {
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
