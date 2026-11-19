package ru.pohsmp.core.client.fx;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.mojang.blaze3d.vertex.VertexConsumer;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.SplittableRandom;
import net.minecraft.client.Minecraft;
import net.minecraft.world.phys.Vec3;
import ru.pohsmp.core.client.fx.FxDraw.Frame;
import ru.pohsmp.core.fx.FxDef;
import ru.pohsmp.core.fx.FxDef.Element;
import ru.pohsmp.core.fx.FxLib;
import ru.pohsmp.core.fx.FxMath;
import ru.pohsmp.core.fx.sigil.Easing;
import ru.pohsmp.core.fx.sigil.SigilDef;

/**
 * Element types of docs/fx.md drawn on the client: sigil, mesh, flash, wave, beam, beam_rain, sprites, curtain, column,
 * tint, decal (disc or crack), trail (slash). Random choices come from the effect seed, so every player sees the same. Unknown types are skipped.
 */
public final class ElementDraw {
    private ElementDraw() {}

    /** Kept between frames for one element. */
    public static final class State {
        Vec3 at, to;
        SigilRun sigil;
        MeshDraw.Run mesh;
        final Map<Integer, SigilRun> impacts = new HashMap<>();
    }

    /** Returns true while the element still has something to draw (sub-sigils dissolving after its end count). */
    public static boolean draw(Frame f, FxRun run, int idx, Element el, double t, FxDef.Context ctx) {
        double te = t - el.delay();
        if (te < 0) return true;
        State st = run.state.computeIfAbsent(idx, k -> new State());
        String type = el.type().toLowerCase(Locale.ROOT);
        if (type.equals("sigil")) return sigil(f, run, el, st, te, ctx);
        if (type.equals("mesh")) return mesh(f, run, el, st, te, ctx);
        double L = until(el);
        if (L >= 0 && te > L) return false;
        if (!Double.isNaN(run.stopAt) && t - run.stopAt > 12) return false;
        double env = env(el, te, L);
        if (!Double.isNaN(run.stopAt)) env *= Math.max(0, 1 - (t - run.stopAt) / 12);
        if (env <= 0.002) return true;
        Vec3 at = anchor(el, st, ctx);
        int col = run.color >= 0 && el.color() == null ? run.color : run.style.color(el.color());
        double a = env * el.brightness();
        double s = el.scale() * run.scale;
        long seed = run.seed * 1000003L + idx * 7919L;
        switch (type) {
            case "flash" -> flash(f, el, te, L, at, s, col, a);
            case "wave" -> wave(f, el, te, L, at, s, col, a);
            case "beam" -> beam(f, el, te, at, target(el, st, ctx, at), s, col, a);
            case "beam_rain" -> beamRain(f, run, el, st, te, L, at, s, col, a, seed);
            case "sprites" -> sprites(f, run, el, te, L, at, s, col, a, seed);
            case "curtain" -> curtain(f, el, te, at, s, col, a, seed);
            case "column" -> column(f, el, te, at, s, col, a);
            case "tint" -> tint(el, at, col, a);
            case "decal" -> decal(f, run, el, te, L, at, s, col, a, seed, ctx);
            case "trail", "ribbon" -> trail(f, run, el, te, L, at, s, col, a, seed, ctx);
            default -> {}
        }
        return true;
    }

    // ---------------------------------------------------------------- common

    /** Element length in ticks from its delay, or -1 for "until the effect stops". */
    static double until(Element el) {
        if (el.duration() >= 0) return el.duration();
        if (el.params().has("until")) return el.params().get("until").getAsDouble() - el.delay();
        return -1;
    }

    static double env(Element el, double te, double L) {
        double e = 1;
        JsonObject p = el.params();
        if (p.has("in") && p.get("in").isJsonObject()) {
            JsonObject in = p.getAsJsonObject("in");
            e *= Easing.byName(MeshDraw.str(in, "easing", "linear")).apply(te / Math.max(1, MeshDraw.num(in, "duration", 1)));
        }
        if (L >= 0 && p.has("out") && p.get("out").isJsonObject()) {
            JsonObject out = p.getAsJsonObject("out");
            e *= Easing.byName(MeshDraw.str(out, "easing", "linear")).apply((L - te) / Math.max(1, MeshDraw.num(out, "duration", 1)));
        }
        return e;
    }

    static Vec3 anchor(Element el, State st, FxDef.Context ctx) {
        if (el.follow() || st.at == null) {
            Vec3 p = FxRun.w(el.at().resolve(ctx));
            if (!el.follow()) st.at = p;
            return p;
        }
        return st.at;
    }

    static Vec3 target(Element el, State st, FxDef.Context ctx, Vec3 at) {
        JsonObject p = el.params();
        if (p.has("fromSky")) return at;
        if (el.to() == null) return at.add(0, 6, 0);
        if (el.follow() || st.to == null) {
            Vec3 v = FxRun.w(el.to().resolve(ctx));
            if (!el.follow()) st.to = v;
            return v;
        }
        return st.to;
    }

    /** A number, or [from, to] picked by r (0..1). */
    static double range(JsonObject p, String k, double def, double r) {
        if (!p.has(k)) return def;
        JsonElement e = p.get(k);
        if (e.isJsonArray()) {
            JsonArray a = e.getAsJsonArray();
            return a.get(0).getAsDouble() + (a.get(a.size() - 1).getAsDouble() - a.get(0).getAsDouble()) * r;
        }
        return e.getAsDouble();
    }

    // ---------------------------------------------------------------- sigil / mesh

    private static boolean sigil(Frame f, FxRun run, Element el, State st, double te, FxDef.Context ctx) {
        if (st.sigil == null) {
            SigilDef d = FxLib.sigil(el.str("id", ""));
            if (d == null) return false;
            SigilRun r = new SigilRun();
            r.def = d;
            Vec3 at = FxRun.w(el.at().resolve(ctx));
            r.base = at;
            r.caster = run.caster;
            if (el.follow() && el.at().kind().startsWith("caster") && run.caster != null) {
                r.follow = run.caster;
                r.offset = at.subtract(run.caster.position());
            } else if (el.follow() && el.at().kind().equals("target") && run.target != null) {
                r.follow = run.target;
                r.offset = at.subtract(run.target.position());
            }
            r.yaw = (float) ctx.yaw();
            r.start = run.start + el.delay();
            r.scale = el.scale() * run.scale * el.num("sigilScale", 1);
            if (el.color() != null) r.color = run.style.color(el.color());
            else if (run.color >= 0) r.color = run.color;
            String o = el.str("orientation", null);
            if (o != null) for (SigilDef.Orientation v : SigilDef.Orientation.values()) if (v.name().equalsIgnoreCase(o)) r.orient = v;
            r.seed = run.seed + el.delay();
            double L = until(el);
            if (L >= 0) r.stopAfter = L;
            st.sigil = r;
        }
        if (!Double.isNaN(run.stopAt)) st.sigil.stop(run.start + run.stopAt - st.sigil.start);
        return SigilDraw.draw(f, st.sigil);
    }

    private static boolean mesh(Frame f, FxRun run, Element el, State st, double te, FxDef.Context ctx) {
        if (st.mesh == null) {
            JsonObject d = FxLib.mesh(el.str("model", el.str("id", "")));
            if (d == null) return false;
            MeshDraw.Run m = new MeshDraw.Run();
            m.def = d;
            m.style = d.has("style") && el.color() == null ? FxLib.style(d.get("style").getAsString()) : run.style;
            m.base = FxRun.w(el.at().resolve(ctx));
            m.yaw = (float) (ctx.yaw() + el.num("yaw", 0));
            m.start = run.start + el.delay();
            m.scale = el.scale() * run.scale;
            st.mesh = m;
        }
        double L = until(el);
        if (L >= 0 && te >= L) st.mesh.stop(L);
        if (!Double.isNaN(run.stopAt)) st.mesh.stop(run.start + run.stopAt - st.mesh.start);
        return MeshDraw.draw(f, st.mesh);
    }

    // ---------------------------------------------------------------- flash

    private static void flash(Frame f, Element el, double te, double L, Vec3 at, double s, int col, double a) {
        double dur = L > 0 ? L : 10;
        double p = FxDraw.clamp01(te / dur);
        double k = p < 0.2 ? p / 0.2 : 1 - (p - 0.2) / 0.8;
        k = Math.max(0, k) * a;
        double size = el.num("size", 2) * s;
        FxDraw.billboard(f.add(FxDraw.tex("glow")), f, at, size * (0.6 + 0.4 * p), 0, col, k);
        FxDraw.billboard(f.add(FxDraw.tex("glow")), f, at, size * 0.3, 0, 0xFFFFFF, k);
        double ana = el.num("anamorphic", 0) * s;
        if (ana > 0) FxDraw.billboard(f.add(FxDraw.tex("spark_soft")), f, at, ana * (0.5 + 0.5 * p), size * 0.06, 0, col, k);
        int rays = (int) el.num("rays", 0);
        if (rays > 0) {
            VertexConsumer vc = f.add(FxDraw.tex("beam"));
            Vec3 l = f.left(), u = f.up();
            for (int i = 0; i < rays; i++) {
                double ang = Math.PI * 2 * i / rays + te * 0.02;
                Vec3 dir = l.scale(Math.cos(ang)).add(u.scale(Math.sin(ang)));
                FxDraw.line(vc, f, at, at.add(dir.scale(size * (0.9 + 0.3 * (i % 2)))), size * 0.06, col, k);
            }
        }
        double screen = el.num("screen", 0);
        if (screen > 0) FxClient.screenFlash(at, 0xFFFFFF, screen * k, 32);
    }

    // ---------------------------------------------------------------- wave

    private static void wave(Frame f, Element el, double te, double L, Vec3 at, double s, int col, double a) {
        double dur = L > 0 ? L : 20;
        double p = FxDraw.clamp01(te / dur);
        double R = el.num("radius", 4) * s * Easing.EASE_OUT_CUBIC.apply(p);
        if (R <= 1e-3) return;
        if ("sphere".equals(el.str("shape", "ring"))) {
            sphere(f, at, R, el.num("rim", 0.8), col, a * (1 - p * 0.6));
            return;
        }
        double fade = a * (1 - p);
        FxDraw.disc(f.add(FxDraw.tex("thin_ring")), f, at.add(0, 0.08, 0), new Vec3(1, 0, 0), new Vec3(0, 0, -1), R, 0, col, fade * 1.5);
        FxDraw.disc(f.add(FxDraw.tex("glow")), f, at.add(0, 0.06, 0), new Vec3(1, 0, 0), new Vec3(0, 0, -1), R, 0, col, fade * 0.25);
    }

    static void sphere(Frame f, Vec3 c, double R, double rim, int col, double a) {
        int lat = f.low() ? 8 : 14, lon = f.low() ? 14 : 26;
        VertexConsumer vc = f.add(FxDraw.WHITE);
        for (int i = 0; i < lat; i++) {
            double t0 = Math.PI * i / lat - Math.PI / 2, t1 = Math.PI * (i + 1) / lat - Math.PI / 2;
            for (int j = 0; j < lon; j++) {
                double p0 = Math.PI * 2 * j / lon, p1 = Math.PI * 2 * (j + 1) / lon;
                Vec3[] q = {sp(t0, p0), sp(t1, p0), sp(t1, p1), sp(t0, p1)};
                for (Vec3 n : q) {
                    Vec3 pos = c.add(n.scale(R));
                    Vec3 view = f.camPos().subtract(pos);
                    double fres = view.lengthSqr() < 1e-6 ? 0 : 1 - Math.abs(n.dot(view.normalize()));
                    FxDraw.vert(vc, f, pos, 0.5f, 0.5f, col, a * (0.08 + rim * fres * fres));
                }
            }
        }
    }

    private static Vec3 sp(double lat, double lon) {
        return new Vec3(Math.cos(lat) * Math.cos(lon), Math.sin(lat), Math.cos(lat) * Math.sin(lon));
    }

    // ---------------------------------------------------------------- beams

    private static void beam(Frame f, Element el, double te, Vec3 from, Vec3 to, double s, int col, double a) {
        JsonObject p = el.params();
        if (p.has("fromSky")) {
            to = from;
            from = from.add(0, p.get("fromSky").getAsDouble(), 0);
        }
        double grow = el.num("grow", 0);
        double k = grow > 0 ? FxDraw.clamp01(te / grow) : 1;
        Vec3 end = FxDraw.lerp(from, to, Easing.EASE_OUT_CUBIC.apply(k));
        double w = el.num("width", 0.4) * s, core = el.num("core", 0.35), taper = el.num("taper", 0);
        double fl = el.num("flicker", 0);
        double al = a * (1 - fl * 0.5 * (1 + Math.sin(te * 1.7)));
        FxDraw.line(f.add(FxDraw.tex("beam")), f, from, end, w, w * (1 - taper), col, al * 0.7, al * 0.7, 0, 1);
        FxDraw.line(f.add(FxDraw.WHITE), f, from, end, w * core, w * core * (1 - taper), col, al, al, 0, 1);
        FxDraw.billboard(f.add(FxDraw.tex("glow")), f, end, w * 1.6, 0, col, al * 0.6);
    }

    private static void beamRain(Frame f, FxRun run, Element el, State st, double te, double L, Vec3 at, double s, int col, double a, long seed) {
        int count = (int) el.num("count", 20), interval = (int) el.num("interval", 3);
        double area = el.num("area", 8) * s, h = el.num("height", 10) * s, w = el.num("width", 0.3) * s;
        List<FxMath.Strike> strikes = FxMath.beamRain(seed, FxRun.v(at), area, count, interval);
        String impact = el.str("impact", null);
        SigilDef impactDef = impact != null ? FxLib.sigil(impact) : null;
        VertexConsumer glow = f.add(FxDraw.tex("beam")), core = f.add(FxDraw.WHITE);
        for (int i = 0; i < strikes.size(); i++) {
            FxMath.Strike sk = strikes.get(i);
            double age = te - sk.tick();
            if (age < 0 || age > 14) continue;
            Vec3 ground = new Vec3(sk.x(), at.y, sk.z());
            double grow = FxDraw.clamp01(age / 3), fade = a * (age < 8 ? 1 : 1 - (age - 8) / 6);
            Vec3 top = ground.add(0, h, 0), bottom = FxDraw.lerp(top, ground, grow);
            FxDraw.line(glow, f, top, bottom, w, col, fade * 0.7);
            FxDraw.line(core, f, top, bottom, w * 0.35, col, fade);
            if (grow >= 1 && impactDef == null) FxDraw.billboard(f.add(FxDraw.tex("glow")), f, ground.add(0, 0.2, 0), w * 4, 0, col, fade);
            if (grow >= 1 && impactDef != null && !st.impacts.containsKey(i)) {
                SigilRun r = new SigilRun();
                r.def = impactDef;
                r.base = ground.add(0, 0.05, 0);
                r.orient = SigilDef.Orientation.GROUND;
                r.start = run.start + el.delay() + sk.tick() + 3;
                r.scale = s * 0.6;
                r.color = col;
                r.stopAfter = 14;
                r.seed = seed + i;
                st.impacts.put(i, r);
            }
        }
        st.impacts.values().removeIf(r -> !SigilDraw.draw(f, r));
    }

    // ---------------------------------------------------------------- sprites

    private static void sprites(Frame f, FxRun run, Element el, double te, double L, Vec3 at, double s, int col, double a, long seed) {
        JsonObject p = el.params();
        int count = (int) el.num("count", 30);
        double rate = el.num("rate", 0), life = Math.max(1, el.num("life", 40));
        double spread = el.num("spread", 0) * s, area = el.num("area", 0) * s, speed = el.num("speed", 0.03) * s;
        double grav = el.num("gravity", 0) * s, spin = el.num("spin", 0), sway = el.num("sway", 0), tumble = el.num("tumble", 0);
        double s0 = range(p, "size", 0.2, 0) * s, s1 = range(p, "size", 0.2, 1) * s;
        double emitEnd = L >= 0 ? L : Double.MAX_VALUE;
        VertexConsumer vc = f.add(FxDraw.tex(run.style.texture(el.str("texture", "@sparks"))));
        int step = f.low() ? 2 : 1;
        for (int i = 0; i < count; i += step) {
            double birth = rate > 0 ? i / rate : 0;
            if (birth > emitEnd) break;
            double age = te - birth;
            if (age < 0) break;
            if (age > life) continue;
            SplittableRandom r = new SplittableRandom(seed * 31 + i);
            Vec3 p0;
            if (area > 0) {
                double ang = r.nextDouble() * Math.PI * 2, d = Math.sqrt(r.nextDouble()) * area;
                p0 = at.add(Math.cos(ang) * d, r.nextDouble() * 0.4, Math.sin(ang) * d);
            } else {
                Vec3 u = unit(r);
                p0 = at.add(u.scale(spread * Math.cbrt(r.nextDouble())));
            }
            Vec3 v = unit(r).scale(speed * (0.5 + r.nextDouble()));
            double phase = r.nextDouble() * Math.PI * 2;
            Vec3 pos = p0.add(v.scale(age)).add(0, -0.5 * grav * age * age, 0);
            if (sway > 0) pos = pos.add(Math.sin(age * 0.12 + phase) * sway * 0.5, 0, Math.cos(age * 0.09 + phase) * sway * 0.3);
            double k = age / life;
            double size = s0 + (s1 - s0) * k;
            double al = a * Math.min(1, age / 3) * (1 - k * k);
            double rot = Math.toDegrees(phase) + spin * age / 20 + (tumble > 0 ? Math.sin(age * 0.2 + phase) * 40 * tumble : 0);
            double sy = tumble > 0 ? size * (0.4 + 0.6 * Math.abs(Math.cos(age * 0.15 * tumble + phase))) : size;
            FxDraw.billboard(vc, f, pos, size, sy, rot, col, al);
        }
    }

    private static Vec3 unit(SplittableRandom r) {
        double z = r.nextDouble() * 2 - 1, t = r.nextDouble() * Math.PI * 2, q = Math.sqrt(1 - z * z);
        return new Vec3(q * Math.cos(t), z, q * Math.sin(t));
    }

    // ---------------------------------------------------------------- curtain, column

    private static void curtain(Frame f, Element el, double te, Vec3 at, double s, int col, double a, long seed) {
        JsonObject p = el.params();
        int count = (int) el.num("count", 32);
        double h = el.num("height", 6) * s, grow = el.num("grow", 0), fl = el.num("flicker", 0);
        boolean fromTop = p.has("fromTop") && p.get("fromTop").getAsBoolean();
        double g = grow > 0 ? Easing.EASE_OUT_CUBIC.apply(te / grow) : 1;
        VertexConsumer vc = f.add(FxDraw.tex(el.str("texture", "beam_fade")));
        SplittableRandom r = new SplittableRandom(seed);
        int step = f.low() ? 2 : 1;
        for (int i = 0; i < count; i++) {
            double jr = r.nextDouble(), jw = r.nextDouble(), jb = r.nextDouble(), ja = r.nextDouble(), ph = r.nextDouble() * 10;
            if (i % step != 0) continue;
            double ang = Math.PI * 2 * (i + ja * 0.6) / count;
            double rad = range(p, "radius", 4, jr) * s, w = range(p, "width", 0.1, jw) * s, br = range(p, "brightness", 1, jb);
            double al = a * br * (1 - fl * 0.5 * (1 + Math.sin(te * 0.9 + ph)));
            Vec3 base = at.add(Math.cos(ang) * rad, 0, Math.sin(ang) * rad);
            double len = h * g;
            if (fromTop) FxDraw.pillar(vc, f, base.add(0, h - len, 0), len, w, col, al, al, 1, 0);
            else FxDraw.pillar(vc, f, base, len, w, col, al, al, 1, (float) (1 - g));
        }
    }

    private static void column(Frame f, Element el, double te, Vec3 at, double s, int col, double a) {
        JsonObject p = el.params();
        double R = el.num("radius", 1) * s, h = el.num("height", 8) * s;
        int fill = (int) el.num("fill", 2), seg = f.low() ? 16 : 28;
        VertexConsumer vc = f.add(FxDraw.WHITE);
        for (int k = 0; k <= fill; k++) {
            double r = R * (k + 1) / (fill + 1);
            double al = a * (fill == 0 ? 0.55 : 0.22);
            for (int i = 0; i < seg; i++) {
                double a0 = Math.PI * 2 * i / seg, a1 = Math.PI * 2 * (i + 1) / seg;
                Vec3 b0 = at.add(Math.cos(a0) * r, 0, Math.sin(a0) * r), b1 = at.add(Math.cos(a1) * r, 0, Math.sin(a1) * r);
                FxDraw.vert(vc, f, b0, 0, 1, col, al);
                FxDraw.vert(vc, f, b1, 1, 1, col, al);
                FxDraw.vert(vc, f, b1.add(0, h, 0), 1, 0, col, al * 0.35);
                FxDraw.vert(vc, f, b0.add(0, h, 0), 0, 0, col, al * 0.35);
            }
        }
        FxDraw.pillar(f.add(FxDraw.tex("beam")), f, at, h, R * 1.2, 0xFFFFFF, a * 0.8, a * 0.3, 1, 0);
        VertexConsumer ring = f.add(FxDraw.tex("thin_ring"));
        Vec3 ux = new Vec3(1, 0, 0), uz = new Vec3(0, 0, -1);
        if (p.has("ringHeights")) {
            for (JsonElement e : p.getAsJsonArray("ringHeights")) FxDraw.disc(ring, f, at.add(0, e.getAsDouble() * s, 0), ux, uz, R * 1.25, te * 3, col, a * 1.3);
        } else {
            int rings = (int) el.num("rings", 0);
            double speed = el.num("ringSpeed", 2);
            for (int k = 0; k < rings; k++) {
                double y = ((te * speed / 20 + (double) k / rings * h) % h + h) % h;
                FxDraw.disc(ring, f, at.add(0, y, 0), ux, uz, R * 1.25, te * 3, col, a * 1.3 * (1 - y / h));
            }
        }
    }

    // ---------------------------------------------------------------- tint, decal

    private static void tint(Element el, Vec3 at, int col, double a) {
        var p = Minecraft.getInstance().player;
        if (p == null) return;
        double R = el.num("radius", 32);
        if (p.position().distanceToSqr(at) > R * R) return;
        FxClient.tint(col, el.num("strength", 0.4) * a);
    }

    private static void decal(Frame f, FxRun run, Element el, double te, double L, Vec3 at, double s, int col, double a, long seed, FxDef.Context ctx) {
        double fade = el.num("fadeOut", 0);
        double k = L > 0 && fade > 0 ? FxDraw.clamp01((L - te) / fade) : 1;
        if ("crack".equals(el.str("shape", "disc"))) {
            crack(f, run, el, te, at, s, col, a * k, seed, ctx);
            return;
        }
        FxDraw.disc(f.add(FxDraw.tex(el.str("texture", "core"))), f, at.add(0, 0.04, 0), new Vec3(1, 0, 0), new Vec3(0, 0, -1),
                el.num("radius", 2) * s, 0, col, a * k);
    }

    /**
     * Ground crack across the view (along the caster's right axis): a jagged line of `length` blocks with short branches,
     * opening over `grow` ticks; `pulse` (0..1) makes the glow throb faster towards the element's end (for "about to burst").
     */
    private static void crack(Frame f, FxRun run, Element el, double te, Vec3 at, double s, int col, double a, long seed, FxDef.Context ctx) {
        double len = el.num("length", 4) * s, w = el.num("width", 0.12) * s, grow = el.num("grow", 4);
        double L = until(el), pulse = el.num("pulse", 0);
        double open = grow > 0 ? Easing.EASE_OUT_CUBIC.apply(FxDraw.clamp01(te / grow)) : 1;
        if (pulse > 0 && L > 0) {
            double p = FxDraw.clamp01(te / L);
            a *= 1 - pulse * 0.4 + pulse * 0.4 * Math.sin(te * (0.4 + 1.6 * p * p));
        }
        double yaw = ctx.yaw() + el.num("yaw", 0);
        FxMath.Vec rv = FxMath.right(yaw), fv = FxMath.forward(yaw);
        Vec3 right = new Vec3(rv.x(), 0, rv.z()).normalize(), fwd = new Vec3(fv.x(), 0, fv.z()).normalize();
        Vec3 base = at.add(0, 0.03, 0);
        SplittableRandom r = new SplittableRandom(seed);
        int n = Math.max(4, (int) Math.round(len / 0.35));
        Vec3[] pts = new Vec3[n + 1];
        for (int i = 0; i <= n; i++) {
            double x = (i / (double) n - 0.5) * len;
            double side = i == 0 || i == n ? 0 : (r.nextDouble() - 0.5) * 0.45 * s;
            pts[i] = base.add(right.scale(x)).add(fwd.scale(side));
        }
        VertexConsumer glow = f.add(FxDraw.tex("beam")), core = f.add(FxDraw.WHITE);
        int mid = n / 2;
        for (int i = 0; i < n; i++) {
            // opens from the middle outwards
            double reach = open * (mid + 1);
            if (Math.abs(i + 0.5 - mid) > reach) continue;
            double taper = 1 - Math.abs(i + 0.5 - mid) / (mid + 1.0);
            double ww = w * (0.4 + 0.6 * taper);
            ground(glow, f, pts[i], pts[i + 1], ww * 5, col, a * 0.55);
            ground(core, f, pts[i], pts[i + 1], ww, col, a);
            ground(core, f, pts[i], pts[i + 1], ww * 0.35, 0xFFFFFF, a * 0.8);
        }
        int branches = (int) el.num("branches", 5);
        for (int b = 0; b < branches; b++) {
            int i = 1 + r.nextInt(Math.max(1, n - 1));
            double side = r.nextBoolean() ? 1 : -1, bl = (0.3 + r.nextDouble() * 0.5) * s;
            if (Math.abs(i - mid) > open * (mid + 1)) continue;
            Vec3 end = pts[i].add(fwd.scale(side * bl)).add(right.scale((r.nextDouble() - 0.5) * bl));
            ground(core, f, pts[i], end, w * 0.4, col, a * 0.8);
            ground(glow, f, pts[i], end, w * 2, col, a * 0.35);
        }
    }

    /** Flat strip on the ground from a to b. */
    static void ground(VertexConsumer vc, Frame f, Vec3 a, Vec3 b, double w, int col, double al) {
        Vec3 d = b.subtract(a);
        Vec3 side = new Vec3(-d.z, 0, d.x);
        if (side.lengthSqr() < 1e-9) return;
        side = side.normalize().scale(w / 2);
        FxDraw.vert(vc, f, a.subtract(side), 0, 0, col, al);
        FxDraw.vert(vc, f, a.add(side), 1, 0, col, al);
        FxDraw.vert(vc, f, b.add(side), 1, 1, col, al);
        FxDraw.vert(vc, f, b.subtract(side), 0, 1, col, al);
    }

    // ---------------------------------------------------------------- trail / slash

    /**
     * Slash: an arc of `radius` and `arc` degrees whose middle is at the anchor, in the caster's view (yaw from ctx, plus `yaw`),
     * tilted by `roll` degrees around the forward axis (`rollAlt`: true flips the tilt by seed, so a series alternates).
     * The head sweeps over `sweep` ticks leaving a crescent `thickness` wide (thickest in the middle), then fades
     * over the rest of the duration. `bend` pushes the arc ends back (deeper crescent), `secondary` (0..1) adds a thin second arc inside.
     * Other trail shapes are not drawn yet.
     */
    private static void trail(Frame f, FxRun run, Element el, double te, double L, Vec3 at, double s, int col, double a, long seed, FxDef.Context ctx) {
        if (!"slash".equals(el.str("shape", "slash"))) return;
        double R = el.num("radius", 2.6) * s, arc = Math.toRadians(el.num("arc", 110)), th = el.num("thickness", 0.35) * s;
        double sweep = Math.max(1, el.num("sweep", 3)), bend = el.num("bend", 0), sec = el.num("secondary", 0);
        double dur = L > 0 ? L : 12;
        double roll = el.num("roll", 0);
        JsonObject p = el.params();
        if (p.has("rollAlt") && p.get("rollAlt").getAsBoolean() && (run.seed & 1) == 1) roll = -roll;
        double pitch = el.num("pitch", 0);
        double yaw = ctx.yaw() + el.num("yaw", 0);
        FxMath.Vec fv = FxMath.forward(yaw), rv = FxMath.right(yaw);
        Vec3 fwd = new Vec3(fv.x(), 0, fv.z()).normalize(), right = new Vec3(rv.x(), 0, rv.z()).normalize(), up = new Vec3(0, 1, 0);
        double pr = Math.toRadians(pitch);
        fwd = fwd.scale(Math.cos(pr)).add(up.scale(-Math.sin(pr)));
        double rr = Math.toRadians(roll);
        Vec3 side = right.scale(Math.cos(rr)).add(fwd.cross(right).normalize().scale(-Math.sin(rr)));
        Vec3 centre = at.subtract(fwd.scale(R));
        boolean reverse = p.has("reverse") && p.get("reverse").getAsBoolean() || (p.has("rollAlt") && p.get("rollAlt").getAsBoolean() && (run.seed & 2) == 2);
        double head = FxDraw.clamp01(te / sweep);
        double fade = te <= sweep ? 1 : FxDraw.clamp01(1 - (te - sweep) / Math.max(1, dur - sweep));
        fade *= fade;
        double tail = Math.max(0, head - el.num("tail", 1.0));        // visible part of the arc, 0..1
        int seg = f.low() ? 14 : 28;
        VertexConsumer glow = f.add(FxDraw.tex("beam")), core = f.add(FxDraw.WHITE);
        arcStrip(glow, f, centre, fwd, side, R, arc, bend, tail, head, th * 2.6, reverse, seg, col, a * fade * 0.6);
        arcStrip(core, f, centre, fwd, side, R, arc, bend, tail, head, th, reverse, seg, col, a * fade);
        arcStrip(core, f, centre, fwd, side, R, arc, bend, tail, head, th * 0.35, reverse, seg, 0xFFFFFF, a * fade * 1.2);
        if (sec > 0) {
            double h2 = FxDraw.clamp01((te - 1) / sweep), t2 = Math.max(0, h2 - 1);
            if (h2 > 0) arcStrip(core, f, centre.add(fwd.scale(-0.25 * s)), fwd, side, R * 0.88, arc * 0.85, bend, t2, h2,
                    th * 0.3, reverse, seg, col, a * fade * sec);
        }
        if (head < 1) {
            double ang = (reverse ? 1 : -1) * (arc / 2 - arc * head);
            Vec3 tip = arcPoint(centre, fwd, side, R, ang, bend, arc);
            FxDraw.billboard(f.add(FxDraw.tex("glow")), f, tip, th * 2.5, 0, col, a);
        }
    }

    private static Vec3 arcPoint(Vec3 c, Vec3 fwd, Vec3 side, double R, double ang, double bend, double arc) {
        double e = arc > 0 ? Math.abs(ang) / (arc / 2) : 0;
        double rr = R * (1 - bend * 0.25 * e * e);
        return c.add(fwd.scale(Math.cos(ang) * rr)).add(side.scale(Math.sin(ang) * rr));
    }

    /** Crescent from t0 to t1 (0..1 along the arc), flat in the arc plane; width w at the middle of the arc, thin at its ends. */
    private static void arcStrip(VertexConsumer vc, Frame f, Vec3 c, Vec3 fwd, Vec3 side, double R, double arc, double bend,
                                 double t0, double t1, double w, boolean reverse, int seg, int col, double a) {
        if (t1 - t0 < 1e-3 || a <= 0.002) return;
        int n = Math.max(2, (int) Math.ceil(seg * (t1 - t0)));
        Vec3 pi = null, po = null;
        double ai = 0;
        for (int i = 0; i <= n; i++) {
            double t = t0 + (t1 - t0) * i / n;
            double ang = (reverse ? 1 : -1) * (arc / 2 - arc * t);
            Vec3 pt = arcPoint(c, fwd, side, R, ang, bend, arc);
            Vec3 radial = pt.subtract(c).normalize();
            double shape = Math.sin(Math.PI * t);                               // thick in the middle of the arc
            double local = (t - t0) / Math.max(1e-3, t1 - t0);                  // fades toward the tail
            double ww = w * (0.15 + 0.85 * shape) / 2;
            double al = a * (0.25 + 0.75 * local);
            Vec3 in = pt.subtract(radial.scale(ww)), out = pt.add(radial.scale(ww));
            if (pi != null) {
                float v0 = (float) ((i - 1) / (double) n), v1 = (float) (i / (double) n);
                FxDraw.vert(vc, f, pi, 0, v0, col, ai);
                FxDraw.vert(vc, f, po, 1, v0, col, ai);
                FxDraw.vert(vc, f, out, 1, v1, col, al);
                FxDraw.vert(vc, f, in, 0, v1, col, al);
            }
            pi = in;
            po = out;
            ai = al;
        }
    }
}
