/*
 * Ported from God Wand by HyIsNoob, https://github.com/HyIsNoob/god-wand (common/src/main/java/net/godwand/client/GateDraw.java), Java source under the MIT License.
 * Changes for pohsmp_core: additive layer only (premultiplied vertices), a vertex Sink instead of VertexConsumer (1.20.1), per-context quad budget.
 * See docs/third_party/god-wand-MIT.txt.
 *
 * MIT License
 *
 * Copyright (c) 2026 HyIsNoob (God Wand contributors)
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
package ru.pohsmp.core.client.fx.gate;

import net.minecraft.world.phys.Vec3;

/**
 * Quad emitter of the Gate mana: budget, camera-relative vertices, proximity fade. Only the additive glow layer is ported (the mana is
 * all light): vertices are premultiplied (alpha into the colour, vertex opaque) and drawn over the glow atlas with SRC_ALPHA, ONE — the
 * vanilla position_tex_color shader discards fragments under alpha 0.1, which would cut every soft glow into a hard disc.
 */
public final class GateDraw {
    private GateDraw() {}

    /** Where the vertices go (BufferBuilder in the game, a software rasteriser in the offline check). Camera-relative position. */
    public interface Sink { void vertex(float x, float y, float z, float u, float v, int r, int g, int b, int a); }

    public static final class Ctx {
        public Sink v; public Vec3 eye; public double fade = 1, nearMin = NEAR_MIN, nearMax = NEAR_MAX; public int quads, budget = 6000;
    }
    /** Geometry is invisible closer than nearMin blocks to the camera and fully there from nearMax. */
    static final double NEAR_MIN = 3, NEAR_MAX = 12;

    static double clamp01(double x) { return Math.max(0, Math.min(1, x)); }
    static double smooth(double x) { x = clamp01(x); return x * x * (3 - 2 * x); }

    /** Opacity factor from the distance of the quad's nearest corner or centre to the camera. */
    static double proximity(Ctx c, Vec3 a, Vec3 b, Vec3 d, Vec3 e) {
        double lo = Math.min(Math.min(a.distanceToSqr(c.eye), b.distanceToSqr(c.eye)), Math.min(d.distanceToSqr(c.eye), e.distanceToSqr(c.eye)));
        lo = Math.min(lo, a.add(b).add(d).add(e).scale(.25).distanceToSqr(c.eye));
        if (lo >= c.nearMax * c.nearMax) return 1;
        return smooth((Math.sqrt(lo) - c.nearMin) / (c.nearMax - c.nearMin));
    }

    /** A soft halo of light round a point. */
    static void halo(Ctx c, Vec3 at, double size, double alpha, int color) { sprite(c, at, size, alpha, color, GateAtlasGen.GLOW, 0); }
    /** Quad with an alpha per corner on the solid texel: gradients. Always proximity-faded. */
    static void gradient(Ctx c, Vec3 a, Vec3 b, Vec3 d, Vec3 e, int color, double aa, double ab, double ad, double ae) {
        if (!room(c)) return;
        double k = c.fade * proximity(c, a, b, d, e);
        float su = GateAtlasGen.SOLID_U, sv = GateAtlasGen.SOLID_V;
        vertex(c, a, color, aa * k, su, sv); vertex(c, b, color, ab * k, su, sv);
        vertex(c, d, color, ad * k, su, sv); vertex(c, e, color, ae * k, su, sv);
        c.quads++;
    }
    /** Textured quad: corners a (u0,v0), b (u1,v0), d (u1,v1), e (u0,v1) of {@code r}, per-corner alpha, proximity-faded. */
    static void tex(Ctx c, Vec3 a, Vec3 b, Vec3 d, Vec3 e, GateAtlasGen.Region r, double u0, double u1, double v0, double v1,
                    int color, double aa, double ab, double ad, double ae) {
        if (!room(c)) return;
        double k = c.fade * proximity(c, a, b, d, e);
        float fu0 = r.u(u0), fu1 = r.u(u1), fv0 = r.v(v0), fv1 = r.v(v1);
        vertex(c, a, color, aa * k, fu0, fv0); vertex(c, b, color, ab * k, fu1, fv0);
        vertex(c, d, color, ad * k, fu1, fv1); vertex(c, e, color, ae * k, fu0, fv1);
        c.quads++;
    }
    /** A streamer of vapour or light from {@code a} to {@code b}: pointed at both ends, {@code half} wide at its middle, camera-facing,
     *  drawn with the wisp tile; {@code bend} bows it sideways (in half widths). */
    static void streamer(Ctx c, Vec3 a, Vec3 b, double half, int color, double alpha, double bend) {
        Vec3 axis = b.subtract(a), side = axis.cross(a.add(b).scale(.5).subtract(c.eye));
        if (side.lengthSqr() < 1e-8 || alpha <= 0) return;
        side = side.normalize();
        int n = 5;
        Vec3 pl = null, pr = null;
        for (int i = 0; i <= n; i++) {
            double t = (double) i / n, w = half * Math.pow(Math.sin(Math.PI * t), .8);
            Vec3 m = a.add(axis.scale(t)).add(side.scale(bend * half * Math.sin(Math.PI * t)));
            Vec3 l = m.subtract(side.scale(w)), r = m.add(side.scale(w));
            if (i > 0) tex(c, pl, l, r, pr, GateAtlasGen.WISP, t - 1.0 / n, t, 0, 1, color, alpha, alpha, alpha, alpha);
            pl = l; pr = r;
        }
    }
    /** Camera-facing soft sprite from the glow tile. */
    static void sprite(Ctx c, Vec3 at, double size, double alpha, int color) { sprite(c, at, size, alpha, color, GateAtlasGen.GLOW, 0); }
    static void sprite(Ctx c, Vec3 at, double size, double alpha, int color, GateAtlasGen.Region region, double roll) {
        Vec3 look = at.subtract(c.eye);
        if (look.lengthSqr() < 1e-6 || alpha <= 0) return;
        Vec3 right = look.cross(new Vec3(0, 1, 0)), up;
        right = (right.lengthSqr() < 1e-8 ? new Vec3(1, 0, 0) : right.normalize()).scale(size);
        up = right.cross(look).normalize().scale(size);
        if (roll != 0) { Vec3 r0 = right; right = r0.scale(Math.cos(roll)).add(up.scale(Math.sin(roll))); up = up.scale(Math.cos(roll)).subtract(r0.scale(Math.sin(roll))); }
        tex(c, at.subtract(right).subtract(up), at.add(right).subtract(up), at.add(right).add(up), at.subtract(right).add(up),
                region, 0, 1, 0, 1, color, alpha, alpha, alpha, alpha);
    }

    private static void vertex(Ctx c, Vec3 p, int color, double alpha, float u, float v) {
        double a = clamp01(alpha);
        c.v.vertex((float) (p.x - c.eye.x), (float) (p.y - c.eye.y), (float) (p.z - c.eye.z), u, v,
                (int) (((color >> 16) & 255) * a), (int) (((color >> 8) & 255) * a), (int) ((color & 255) * a), 255);
    }

    /** True while another quad fits the budget; callers check before emitting so a vertex run is never cut short. */
    static boolean room(Ctx c) { return c.quads < c.budget; }
}
