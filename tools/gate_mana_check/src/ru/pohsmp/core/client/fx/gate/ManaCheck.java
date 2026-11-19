package ru.pohsmp.core.client.fx.gate;

import java.awt.image.BufferedImage;
import java.io.File;
import javax.imageio.ImageIO;
import net.minecraft.world.phys.Vec3;

/** Offline check of the ported Gate mana: atlas, clock, staff pose, emitted geometry, and a software render of frames. */
public class ManaCheck {
    static int fails;
    static void check(boolean ok, String what) { System.out.println((ok ? "OK   " : "FAIL ") + what); if (!ok) fails++; }

    public static void main(String[] args) throws Exception {
        String out = args[0];
        // ---- atlas
        long t0 = System.nanoTime();
        byte[] a = GateAtlasGen.alpha();
        System.out.printf("atlas built in %.0f ms%n", (System.nanoTime() - t0) / 1e6);
        check(a.length == GateAtlasGen.W * GateAtlasGen.H, "atlas size 512x256");
        check(a == GateAtlasGen.alpha(), "atlas cached");
        var G = GateAtlasGen.GLOW;
        check((a[(G.y() + 32) * 512 + G.x() + 32] & 255) > 220 && (a[(G.y() + 1) * 512 + G.x() + 1] & 255) == 0, "GLOW bright centre, empty corner");
        var S = GateAtlasGen.STAR;
        check((a[(S.y() + 32) * 512 + S.x() + 32] & 255) > 240 && (a[(S.y() + 32) * 512 + S.x() + 60] & 255) < 40 && (a[(S.y() + 5) * 512 + S.x() + 5] & 255) == 0, "STAR core, arms fade, corner empty");
        check((a[GateAtlasGen.SOLID.y() * 512 + GateAtlasGen.SOLID.x() + 3] & 255) == 255, "SOLID texel opaque");
        var Wp = GateAtlasGen.WISP;
        check((a[(Wp.y() + 64) * 512 + Wp.x()] & 255) < 20 && (a[(Wp.y() + 64) * 512 + Wp.x() + 128] & 255) > 60, "WISP fades at the ends, thick mid");
        BufferedImage atlas = new BufferedImage(512, 256, BufferedImage.TYPE_INT_RGB);
        for (int y = 0; y < 256; y++) for (int x = 0; x < 512; x++) { int g = a[y * 512 + x] & 255; atlas.setRGB(x, y, g << 16 | g << 8 | g); }
        ImageIO.write(atlas, "png", new File(out, "atlas.png"));

        // ---- clock
        check(GateMana.gain(new GateMana.Frame(0, -1)) == 0, "gain 0 at the start");
        check(Math.abs(GateMana.gain(new GateMana.Frame(200, -1)) - 1) < 1e-9, "gain 1 through the cast");
        check(Math.abs(GateMana.gain(new GateMana.Frame(1000, -1)) - .55) < 1e-9, "gain .55 in the wait");
        check(GateMana.gain(new GateMana.Frame(1100, 10)) >= .7 - 1e-9, "gain >= .7 after the command");
        check(GateMana.gain(new GateMana.Frame(1400, 302)) == 0, "gain 0 at the strike end");
        double prev = 0, jump = 0;
        for (double t = 0; t < 2000; t += .5) { double g = GateMana.gain(new GateMana.Frame(t, t < 1100 ? -1 : t - 1100)); jump = Math.max(jump, Math.abs(g - prev)); prev = g; }
        check(jump < .06, "gain continuous (max step per half tick " + String.format("%.3f", jump) + ")");

        // ---- staff pose: as GateStaff drew it before (t=0 float, t=800 fist), continuous over the take
        double[] l0 = GateStaffPose.local(0), l8 = GateStaffPose.local(800);
        check(Math.abs(l0[0] - .75) < 1e-9 && Math.abs(l0[1] - 1.15) < 1e-9 && Math.abs(l0[2] - .65) < 1e-9, "float pose = old GateStaff (0.75, 1.15, 0.65)");
        // owner 19.11 (anime frame): held across the body — fist STAFF_L (.14, .99, .35), roll 124.8 after the full turn, tilt 28.7
        check(Math.abs(l8[0] - .14) < 1e-9 && Math.abs(l8[1] - .99) < 1e-9 && Math.abs(l8[2] - .35) < 1e-9
                        && Math.abs(l8[3] % 360 - GateStaffPose.HOLD_ROLL) < 1e-9 && Math.abs(l8[4] - GateStaffPose.HOLD_TILT) < 1e-9,
                "fist pose (0.14, 0.99, 0.35), across the body (roll 360+124.8, tilt 28.7)");
        Vec3 hd = GateStaffPose.head(800, Vec3.ZERO, 0), ft = GateStaffPose.foot(800, Vec3.ZERO, 0);
        check(hd.x < 0 && hd.y < ft.y && hd.z > ft.z, "held: head low forward on her right, foot up behind on her left");
        Vec3 feet = new Vec3(10, 64, -5);
        double step = 0;
        for (double t = 700; t < 820; t += 1) step = Math.max(step, GateStaffPose.head(t + 1, feet, 30).distanceTo(GateStaffPose.head(t, feet, 30)));
        // owner 19.11: a 360+124.8° turn over TAKE_FROM..TAKE_TO (28 ticks, smootherstep peaks at 1.875x): the head (1.55 out) may move up to ~0.85/tick
        check(step < .9, "staff head moves < .9 block per tick over the take, no jump (" + String.format("%.3f", step) + ")");
        Vec3 h = GateStaffPose.head(0, feet, 0), f0 = GateStaffPose.foot(0, feet, 0);
        check(h.y > f0.y + 2.4 && h.x > feet.x, "yaw 0 (facing +z): staff upright, on the caster's left (+x)");

        // ---- geometry
        for (double[] fr : new double[][]{{100, -1}, {760, -1}, {1050, -1}, {1150, 50}}) {
            Count k = new Count();
            GateDraw.Ctx c = new GateDraw.Ctx(); c.v = k; c.eye = feet.add(4, 1.6, 2);
            int q = GateMana.emit(c, new GateMana.Frame(fr[0], fr[1]), feet, 30);
            check(q * 4 == k.n && !k.nan && q <= c.budget && q > 500, String.format("t=%.0f cmd=%.0f: %d quads, finite", fr[0], fr[1], q));
        }

        // ---- frames: our scene cameras (DownfallCut gateSide / circleShot), caster facing +z (yaw 0), gate ahead
        Vec3 dir = new Vec3(0, 0, 1), side = dir.cross(new Vec3(0, 1, 0)); // right
        render(out + "/f05s_side.png", 100, -1, feet, side(.25, feet, dir, side));
        render(out + "/f17s_side.png", 340, -1, feet, side(.4, feet, dir, side));
        render(out + "/f38s_take.png", 762, -1, feet, side(.6, feet, dir, side));
        render(out + "/f52s_strike.png", 1150, 50, feet, side(.5, feet, dir, side));
        render(out + "/f05s_front.png", 100, -1, feet, new Vec3[]{feet.add(dir.scale(5.2)).add(side.scale(.5)).add(0, 1.2, 0), feet.add(0, 1.6, 0)});
        System.out.println(fails == 0 ? "ALL OK" : fails + " FAILED");
        if (fails > 0) System.exit(1);
    }

    static double flow(double k) { k = Math.max(0, Math.min(1, k)); return .55 * k + .45 * k * k * (3 - 2 * k); }
    static Vec3[] side(double u, Vec3 c, Vec3 dir, Vec3 side) {
        u = flow(u);
        return new Vec3[]{c.add(dir.scale(1.5 - 1.3 * u)).add(side.scale(3.5 - .4 * u)).add(0, 1.35 + .15 * u, 0), c.add(dir.scale(.3 - .5 * u)).add(0, 1.45, 0)};
    }

    static class Count implements GateDraw.Sink {
        int n; boolean nan;
        public void vertex(float x, float y, float z, float u, float v, int r, int g, int b, int a) {
            n++; if (!Float.isFinite(x + y + z + u + v) || r < 0 || r > 255 || g < 0 || b < 0) nan = true;
        }
    }

    // ---- software rasteriser: additive, premultiplied colour x atlas grey (as the game's glow pass)
    static final int WW = 960, HH = 540;
    static void render(String file, double age, double cmd, Vec3 feet, Vec3[] cam) throws Exception {
        float[] img = new float[WW * HH * 3];
        Vec3 eye = cam[0], fw = cam[1].subtract(eye).normalize(), rt = fw.cross(new Vec3(0, 1, 0)).normalize(), up = rt.cross(fw);
        double fl = (HH / 2.0) / Math.tan(Math.toRadians(35));
        // backdrop: dusky teal sky, dark ground, the caster as a dark column, the staff as a gold line
        for (int y = 0; y < HH; y++) for (int x = 0; x < WW; x++) {
            Vec3 ray = fw.scale(fl).add(rt.scale(x - WW / 2.0)).add(up.scale(HH / 2.0 - y)).normalize();
            boolean ground = ray.y < 0 && (eye.y - feet.y) / -ray.y < 400;
            double k = ground ? .04 : .06 + .10 * Math.max(0, 1 - ray.y * 2);
            int i = (y * WW + x) * 3; img[i] = (float) (k * .5); img[i + 1] = (float) (k * 1.2); img[i + 2] = (float) (k * 1.5);
        }
        byte[] at = GateAtlasGen.alpha();
        GateDraw.Sink sink = new GateDraw.Sink() {
            final double[][] v = new double[4][7]; int n;
            public void vertex(float x, float y, float z, float u, float vv, int r, int g, int b, int a) {
                Vec3 p = new Vec3(x, y, z);
                double cz = p.dot(fw);
                v[n] = new double[]{WW / 2.0 + p.dot(rt) / cz * fl, HH / 2.0 - p.dot(up) / cz * fl, cz, u, vv, 0, 0};
                v[n][5] = r << 16 | g << 8 | b;
                if (++n == 4) { n = 0; if (v[0][2] > .05 && v[1][2] > .05 && v[2][2] > .05 && v[3][2] > .05) { tri(img, at, v[0], v[1], v[2]); tri(img, at, v[0], v[2], v[3]); } }
            }
        };
        // body and staff drawn under the light
        body(img, feet, eye, fw, rt, up, fl, age);
        GateDraw.Ctx c = new GateDraw.Ctx(); c.v = sink; c.eye = eye;
        GateMana.emit(c, new GateMana.Frame(age, cmd), feet, 0);
        BufferedImage bi = new BufferedImage(WW, HH, BufferedImage.TYPE_INT_RGB);
        for (int y = 0; y < HH; y++) for (int x = 0; x < WW; x++) {
            int i = (y * WW + x) * 3;
            int r = tone(img[i]), g = tone(img[i + 1]), b = tone(img[i + 2]);
            bi.setRGB(x, y, r << 16 | g << 8 | b);
        }
        ImageIO.write(bi, "png", new File(file));
        System.out.println("frame " + file + " (" + c.quads + " quads)");
    }
    static int tone(float v) { return (int) Math.round(255 * Math.min(1, v)); }
    static int[] px(Vec3 p, Vec3 eye, Vec3 fw, Vec3 rt, Vec3 up, double fl) {
        Vec3 q = p.subtract(eye); double cz = q.dot(fw);
        return new int[]{(int) (WW / 2.0 + q.dot(rt) / cz * fl), (int) (HH / 2.0 - q.dot(up) / cz * fl)};
    }
    static void body(float[] img, Vec3 feet, Vec3 eye, Vec3 fw, Vec3 rt, Vec3 up, double fl, double age) {
        // caster: a column 0.6 wide, 1.8 tall
        int[] lo = px(feet, eye, fw, rt, up, fl), hi = px(feet.add(0, 1.8, 0), eye, fw, rt, up, fl);
        int half = (int) Math.max(3, .3 / feet.subtract(eye).length() * fl);
        for (int y = Math.max(0, hi[1]); y < Math.min(HH, lo[1]); y++) for (int x = Math.max(0, lo[0] - half); x < Math.min(WW, lo[0] + half); x++) {
            int i = (y * WW + x) * 3; img[i] = .10f; img[i + 1] = .09f; img[i + 2] = .14f;
        }
        Vec3 a = GateStaffPose.foot(age, feet, 0), b = GateStaffPose.head(age, feet, 0);
        for (int s = 0; s <= 400; s++) {
            int[] p = px(a.lerp(b, s / 400.0), eye, fw, rt, up, fl);
            for (int d = -1; d <= 1; d++) if (p[0] + d >= 0 && p[0] + d < WW && p[1] >= 0 && p[1] < HH) { int i = (p[1] * WW + p[0] + d) * 3; img[i] = .85f; img[i + 1] = .7f; img[i + 2] = .3f; }
        }
    }
    static void tri(float[] img, byte[] at, double[] a, double[] b, double[] c) {
        int x0 = (int) Math.max(0, Math.floor(Math.min(a[0], Math.min(b[0], c[0])))), x1 = (int) Math.min(WW - 1, Math.ceil(Math.max(a[0], Math.max(b[0], c[0]))));
        int y0 = (int) Math.max(0, Math.floor(Math.min(a[1], Math.min(b[1], c[1])))), y1 = (int) Math.min(HH - 1, Math.ceil(Math.max(a[1], Math.max(b[1], c[1]))));
        double area = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]);
        if (Math.abs(area) < 1e-9 || x1 - x0 > 2000) return;
        for (int y = y0; y <= y1; y++) for (int x = x0; x <= x1; x++) {
            double px = x + .5, py = y + .5;
            double w0 = ((b[0] - px) * (c[1] - py) - (c[0] - px) * (b[1] - py)) / area, w1 = ((c[0] - px) * (a[1] - py) - (a[0] - px) * (c[1] - py)) / area, w2 = 1 - w0 - w1;
            if (w0 < 0 || w1 < 0 || w2 < 0) continue;
            double u = w0 * a[3] + w1 * b[3] + w2 * c[3], v = w0 * a[4] + w1 * b[4] + w2 * c[4];
            int tx = (int) Math.min(511, Math.max(0, u * 512)), ty = (int) Math.min(255, Math.max(0, v * 256));
            double t = (at[ty * 512 + tx] & 255) / 255.0;
            int i = (y * WW + x) * 3;
            for (int ch = 0; ch < 3; ch++) {
                int sh = 16 - 8 * ch;
                double col = w0 * (((int) a[5] >> sh) & 255) + w1 * (((int) b[5] >> sh) & 255) + w2 * (((int) c[5] >> sh) & 255);
                img[i + ch] += (float) (col / 255 * t);
            }
        }
    }
}
