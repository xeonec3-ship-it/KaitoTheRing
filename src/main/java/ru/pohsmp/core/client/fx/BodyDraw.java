package ru.pohsmp.core.client.fx;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.mojang.blaze3d.vertex.VertexConsumer;
import java.util.SplittableRandom;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.client.fx.FxDraw.Frame;
import ru.pohsmp.core.fx.FxDef;
import ru.pohsmp.core.fx.FxDef.Element;
import ru.pohsmp.core.fx.FxMath;
import ru.pohsmp.core.fx.FxShapes;

/** Element types that dress a body (docs/fx.md): aura around an entity, wings of light and a halo over the head. */
final class BodyDraw {
    private BodyDraw() {}

    /** {amp, period} from a number (period, default amp), [amp, period] or {"amp", "period"}. */
    static double[] wave(JsonObject p, String key, double amp, double period) {
        if (!p.has(key)) return new double[] {amp, period};
        JsonElement e = p.get(key);
        if (e.isJsonArray()) {
            JsonArray a = e.getAsJsonArray();
            return new double[] {a.get(0).getAsDouble(), a.size() > 1 ? a.get(1).getAsDouble() : period};
        }
        if (e.isJsonObject()) return new double[] {MeshDraw.num(e.getAsJsonObject(), "amp", amp), MeshDraw.num(e.getAsJsonObject(), "period", period)};
        return new double[] {amp, e.getAsDouble()};
    }

    /** Offset x,y,z in view axes: "0,1.3,-0.3" or [0, 1.3, -0.3]; def when absent. */
    static double[] offset(JsonObject p, double[] def) {
        if (!p.has("offset")) return def;
        JsonElement e = p.get("offset");
        double[] o = new double[3];
        if (e.isJsonArray()) {
            JsonArray a = e.getAsJsonArray();
            for (int i = 0; i < 3 && i < a.size(); i++) o[i] = a.get(i).getAsDouble();
        } else {
            String[] s = e.getAsString().split(",");
            for (int i = 0; i < 3 && i < s.length; i++) o[i] = Double.parseDouble(s[i].trim());
        }
        return o;
    }

    private static boolean plainAnchor(Element el) {
        return el.at().ox() == 0 && el.at().oy() == 0 && el.at().oz() == 0;
    }

    private static Vec3 place(Element el, Vec3 at, double yaw, double[] def, double s) {
        double[] o = offset(el.params(), plainAnchor(el) ? def : new double[3]);
        return FxRun.w(FxMath.offset(FxRun.v(at), yaw, o[0] * s, o[1] * s, o[2] * s));
    }

    // ---------------------------------------------------------------- aura

    static void aura(Frame f, FxRun run, Element el, double te, Vec3 at, double s, int col, double a, long seed) {
        JsonObject p = el.params();
        String who = el.str("target", el.at().kind().startsWith("target") ? "target" : "caster");
        Entity e = "target".equals(who) ? run.target : run.caster;
        Vec3 feet;
        double bw, bh;
        if (e != null && e.isAlive()) {
            feet = e.getPosition(f.pt());
            bw = e.getBbWidth();
            bh = e.getBbHeight();
        } else {
            feet = at;
            bw = 0.6;
            bh = 1.8;
        }
        double th = el.num("thickness", 0.25) * s;
        double[] pw = wave(p, "pulse", 0.25, 30);
        double pulse = FxShapes.pulse(te, pw[0], pw[1]);
        double w = (bw + th * 2) * 1.9 * (0.96 + 0.04 * pulse), h = (bh + th * 2) * 1.3;
        Vec3 base = feet.add(0, -bh * 0.13 - th, 0);
        VertexConsumer shell = f.add(FxDraw.tex("aura_shell"));
        FxDraw.pillar(shell, f, base, h, w, col, a * 0.7 * pulse, a * 0.7 * pulse, 1, 0);
        FxDraw.pillar(shell, f, base.add(0, h * 0.06, 0), h * 0.88, w * 0.78, FxDraw.mix(col, 0xFFFFFF, 0.45), a * 0.35 * pulse, a * 0.35 * pulse, 1, 0);
        if (!p.has("ring") || p.get("ring").getAsBoolean()) {
            Vec3 ux = new Vec3(1, 0, 0), uz = new Vec3(0, 0, -1);
            FxDraw.disc(f.add(FxDraw.tex("thin_ring")), f, feet.add(0, 0.05, 0), ux, uz, bw * 1.1 + th, te * 2, col, a * 0.9 * pulse);
            FxDraw.disc(f.add(FxDraw.tex("glow")), f, feet.add(0, 0.04, 0), ux, uz, bw * 1.3 + th, 0, col, a * 0.3);
        }
        int motes = (int) el.num("motes", 12);
        double life = 30;
        VertexConsumer vc = f.add(FxDraw.tex(run.style.texture(el.str("texture", "@sparks"))));
        for (int i = 0; i < motes; i += f.low() ? 2 : 1) {
            SplittableRandom r = new SplittableRandom(seed * 13 + i);
            double ph = r.nextDouble(), ang = r.nextDouble() * Math.PI * 2, rr = (0.4 + 0.5 * r.nextDouble()) * (bw / 2 + th);
            double age = (te + ph * life) % life, k = age / life;
            Vec3 c = feet.add(Math.cos(ang + k) * rr, k * bh * 1.1, Math.sin(ang + k) * rr);
            FxDraw.billboard(vc, f, c, 0.07 * s * (1 - k * 0.5), age * 8, col, a * Math.sin(Math.PI * k));
        }
    }

    // ---------------------------------------------------------------- wings

    /** Hinge of the wing texture (tools/gen_fx_elements.ps1): uv (0.06, 0.59). */
    private static final double HU = 0.06, HV = 0.59;

    static void wings(Frame f, FxRun run, Element el, double te, Vec3 at, FxDef.Context ctx, double s, int col, double a) {
        JsonObject p = el.params();
        double size = el.num("size", 2) * s, spread = el.num("spread", 25);
        double[] fl = wave(p, "flap", 12, 40);
        double yaw = ctx.yaw();
        Vec3 hinge = place(el, at, yaw, new double[] {0, 1.35, -0.25}, s);
        Vec3 fwd = FxRun.w(FxMath.forward(yaw)), right = FxRun.w(FxMath.right(yaw)), up = new Vec3(0, 1, 0);
        double phi = Math.toRadians(spread + FxShapes.flap(te, fl[0], fl[1]));
        double lift = Math.toRadians(FxShapes.flap(te - fl[1] * 0.15, fl[0] * 0.5, fl[1]));
        String tex = el.str("texture", "wing");
        VertexConsumer vc = f.add(FxDraw.tex(tex));
        int core = FxDraw.mix(col, 0xFFFFFF, 0.5);
        for (int side = -1; side <= 1; side += 2) {
            Vec3 out = right.scale(side * Math.cos(phi)).subtract(fwd.scale(Math.sin(phi)));
            Vec3 upW = up.scale(Math.cos(lift)).subtract(out.scale(Math.sin(lift)));
            Vec3 outW = out.scale(Math.cos(lift)).add(up.scale(Math.sin(lift)));
            Vec3 h = hinge.add(right.scale(side * 0.12 * s));
            wing(vc, f, h, outW, upW, size * 1.05, col, a * 0.55);
            wing(vc, f, h.subtract(fwd.scale(0.02)), outW, upW, size, core, a * 0.7);
        }
        FxDraw.billboard(f.add(FxDraw.tex("glow")), f, hinge.subtract(fwd.scale(0.2)), size * 0.7, 0, col, a * 0.25);
    }

    private static void wing(VertexConsumer vc, Frame f, Vec3 hinge, Vec3 out, Vec3 up, double S, int col, double a) {
        Vec3[] q = new Vec3[4];
        double[][] uv = {{0, 0}, {0, 1}, {1, 1}, {1, 0}};
        for (int i = 0; i < 4; i++) q[i] = hinge.add(out.scale((uv[i][0] - HU) * S)).add(up.scale((HV - uv[i][1]) * S));
        for (int i = 0; i < 4; i++) FxDraw.vert(vc, f, q[i], (float) uv[i][0], (float) uv[i][1], col, a);
    }

    // ---------------------------------------------------------------- halo

    static void halo(Frame f, FxRun run, Element el, double te, Vec3 at, FxDef.Context ctx, double s, int col, double a) {
        JsonObject p = el.params();
        double R = el.num("size", 0.42) * s, tilt = Math.toRadians(el.num("tilt", 12));
        double[] fl = wave(p, "flap", 0.04, 50);
        double yaw = ctx.yaw();
        Vec3 c = place(el, at, yaw, new double[] {0, 2.15, -0.08}, s).add(0, FxShapes.flap(te, fl[0], fl[1]) * s, 0);
        Vec3 fwd = FxRun.w(FxMath.forward(yaw)), right = FxRun.w(FxMath.right(yaw)), up = new Vec3(0, 1, 0);
        Vec3 v = fwd.scale(Math.cos(tilt)).add(up.scale(Math.sin(tilt)));
        double spin = el.num("spin", 1) * run.style.rotationScale() * te;
        double pulse = 0.88 + 0.12 * Math.sin(te * 0.15);
        FxDraw.disc(f.add(FxDraw.tex("glow")), f, c, right, v, R * 1.7, 0, col, a * 0.3 * pulse);
        FxDraw.disc(f.add(FxDraw.tex(el.str("texture", "thin_ring"))), f, c, right, v, R, spin, col, a * 1.3 * pulse);
        FxDraw.disc(f.add(FxDraw.tex("thin_ring")), f, c, right, v, R * 0.97, 0, FxDraw.mix(col, 0xFFFFFF, 0.6), a * 0.7);
        FxDraw.disc(f.add(FxDraw.tex("rim")), f, c, right, v, R * 1.22, -spin * 0.6, col, a * 0.45 * pulse);
    }
}
