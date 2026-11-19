/*
 * Ported from God Wand by HyIsNoob, https://github.com/HyIsNoob/god-wand (common/src/main/java/net/godwand/client/GateAtlas.java), Java source under the MIT License.
 * Changes for pohsmp_core: only the particle regions (GLOW, STAR, SILK, CLOUD, WISP, SOLID) in a 512x256 atlas, no Minecraft classes.
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

/**
 * Procedural 512x256 particle atlas of the Gate mana (no PNG shipped): white RGB, alpha carries the drawing, tinted with vertex colour.
 * Every quad samples a tile-local phase 0..1 of its region (inset half a texel). Pure Java (no Minecraft classes), so it can be built
 * on a background thread and checked offline; {@link GateManaRender} uploads it.
 */
public final class GateAtlasGen {
    private GateAtlasGen() {}

    public record Region(int x, int y, int w, int h) {
        public float u(double phase) { return (float) ((x + .5 + phase * (w - 1)) / W); }
        public float v(double t) { return (float) ((y + .5 + t * (h - 1)) / H); }
    }
    public static final int W = 512, H = 256;
    public static final Region SILK = new Region(0, 0, 256, 64), STAR = new Region(256, 0, 64, 64), GLOW = new Region(320, 0, 64, 64),
            SOLID = new Region(496, 0, 8, 8), WISP = new Region(0, 64, 256, 128), CLOUD = new Region(256, 64, 128, 128);
    public static final float SOLID_U = SOLID.u(.5), SOLID_V = SOLID.v(.5);
    private static final double TAU = Math.PI * 2;

    private static byte[] cache;

    /** Alpha of the whole atlas, row-major, W x H. Pure and deterministic. */
    public static synchronized byte[] alpha() {
        if (cache != null) return cache;
        float[] a = new float[W * H];
        glow(a); cloud(a); silk(a); star(a); wisp(a);
        for (int y = 0; y < SOLID.h; y++) for (int x = 0; x < SOLID.w; x++) a[(SOLID.y + y) * W + SOLID.x + x] = 1;
        byte[] out = new byte[W * H];
        for (int i = 0; i < out.length; i++) out[i] = (byte) Math.round(Math.max(0, Math.min(1, a[i])) * 255);
        return cache = out;
    }

    private static void glow(float[] a) {
        for (int y = 0; y < GLOW.h; y++) for (int x = 0; x < GLOW.w; x++) {
            double d = Math.hypot(x + .5 - GLOW.w / 2.0, y + .5 - GLOW.h / 2.0) / (GLOW.w / 2.0 - 1);
            double f = Math.max(0, 1 - d);
            a[(GLOW.y + y) * W + GLOW.x + x] = (float) (f * f * f);
        }
    }
    /** Silk: soft edges across, long creases and three bright warped fibres along. */
    private static void silk(float[] a) {
        for (int y = 0; y < SILK.h; y++) for (int x = 0; x < SILK.w; x++) {
            double u = (x + .5) / SILK.w, v = (y + .5) / SILK.h, m = Math.abs(2 * v - 1);
            double edge = Math.pow(Math.max(0, 1 - m), 1.6);
            double crease = .5 + .5 * Math.sin(TAU * (2 * u + .18 * Math.sin(TAU * u)) + v * 7 + 1.3 * Math.sin(v * 11));
            double fibres = 0;
            for (int k = 0; k < 3; k++) {
                double centre = .28 + .22 * k + .05 * Math.sin(TAU * (1.5 * u + k * .31)), d = (v - centre) / .028;
                fibres = Math.max(fibres, Math.exp(-d * d));
            }
            a[(SILK.y + y) * W + SILK.x + x] = (float) Math.min(1, edge * (.55 + .22 * crease + .28 * fibres));
        }
    }
    /** Four-point sparkle with a small round core. */
    private static void star(float[] a) {
        for (int y = 0; y < STAR.h; y++) for (int x = 0; x < STAR.w; x++) {
            double dx = Math.abs((x + .5) / STAR.w * 2 - 1), dy = Math.abs((y + .5) / STAR.h * 2 - 1);
            double arms = Math.max(0, 1 - Math.sqrt(dx) - Math.sqrt(dy)), core = Math.max(0, 1 - Math.hypot(dx, dy) * 2.6);
            a[(STAR.y + y) * W + STAR.x + x] = (float) Math.min(1, arms * arms * arms * 2.4 + core * core * core);
        }
    }
    /** Round puff: octaves of value noise carve a soft, uneven billow whose alpha falls smoothly to zero well inside the tile. */
    private static void cloud(float[] a) {
        for (int y = 0; y < CLOUD.h; y++) for (int x = 0; x < CLOUD.w; x++) {
            double dx = (x + .5 - 64) / 62, dy = (y + .5 - 64) / 62, d = Math.hypot(dx, dy);
            double n = .45 * vnoise(x / 22.0, y / 22.0, 1) + .25 * vnoise(x / 11.0, y / 11.0, 2) + .15 * vnoise(x / 5.5, y / 5.5, 3)
                    + .1 * vnoise(x / 2.7, y / 2.7, 4) + .05 * vnoise(x / 1.4, y / 1.4, 5);
            double f = clamp01((1 - d) * 1.5 + (n - .5) * .9);
            a[(CLOUD.y + y) * W + CLOUD.x + x] = (float) (f * f * (3 - 2 * f) * .95);
        }
    }
    /** A wisp: smoke drawn out along U, thick in the middle of the strip and torn at its edges; both ends fade to nothing. */
    private static void wisp(float[] a) {
        for (int y = 0; y < WISP.h; y++) for (int x = 0; x < WISP.w; x++) {
            double u = (x + .5) / WISP.w, v = (y + .5) / WISP.h * 2 - 1;
            double centre = .45 * (fbm(x / 70.0, 3, 71) - .5), strand = fbm(x / 90.0, y / 9.0, 73), fine = fbm(x / 20.0, y / 5.0, 79);
            double across = step01((.8 - Math.abs(v - centre) - .5 * (strand - .5)) / .55);
            a[(WISP.y + y) * W + WISP.x + x] = (float) (across * Math.pow(Math.sin(Math.PI * u), .7) * clamp01(.3 + .9 * strand * (.6 + .8 * fine)));
        }
    }

    private static double clamp01(double v) { return Math.max(0, Math.min(1, v)); }
    private static double step01(double x) { x = clamp01(x); return x * x * (3 - 2 * x); }
    /** Five octaves of value noise, 0..1. */
    private static double fbm(double x, double y, int salt) {
        double sum = 0, amp = .5, norm = 0;
        for (int o = 0; o < 5; o++) { sum += amp * vnoise(x, y, salt + o); norm += amp; x *= 2.03; y *= 2.03; amp *= .5; }
        return sum / norm;
    }
    private static double lattice(int x, int y, int salt) {
        double h = Math.sin(x * 127.1 + y * 311.7 + salt * 74.7) * 43758.5453;
        return h - Math.floor(h);
    }
    private static double vnoise(double x, double y, int salt) {
        int ix = (int) Math.floor(x), iy = (int) Math.floor(y);
        double fx = x - ix, fy = y - iy;
        fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy);
        double a = lattice(ix, iy, salt), b = lattice(ix + 1, iy, salt), d = lattice(ix, iy + 1, salt), e = lattice(ix + 1, iy + 1, salt);
        return a + (b - a) * fx + (d - a) * fy + (a - b - d + e) * fx * fy;
    }
}
