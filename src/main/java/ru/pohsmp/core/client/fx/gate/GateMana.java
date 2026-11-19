/*
 * Ported from God Wand by HyIsNoob, https://github.com/HyIsNoob/god-wand (common/src/main/java/net/godwand/client/GateMana.java and GatePose.manaGain), Java source under the MIT License.
 * Changes for pohsmp_core: flow, bands and wandTrail as they are; the staff pose (GateStaffPose) and the mana clock are ours; the undrawn silk strands are left out.
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
 * Mana of «Безмолвные врата» (T03), drawn the way God Wand draws the mana of its Silent Gate: a wind of fine sparks born before the
 * caster that streams back past them and away (flow, 2100 specks: white, mint, teal, every sixth with a halo), long bands of gauze on
 * the same wind (bands) and the staff writing in the air: ribbons from its head and foot along the path they have just travelled and
 * specks shed all the while, taken by the wind (wandTrail). All of it additive light; fixed to where the caster stands.
 * <p>
 * What differs from God Wand: the staff pose is ours ({@link GateStaffPose}: afloat front-left, then in the left fist; their wand spins in
 * the right hand) and the mana clock is ours ({@link #gain}: our 50 s cast, the wait for the command, the 15 s strike). Their eight
 * silk strands (a spring-chain simulation) are left out: God Wand steps them but no longer draws them (owner there, 2026-11-12).
 */
public final class GateMana {
    private GateMana() {}
    static final int FLOW = 2100, BANDS = 26, TRAIL = 44, SHED = 900;

    /** One frame of a running Gate scene: scene age in ticks (with partial), ticks since the command (-1 before it). */
    public record Frame(double age, double commandAge) {}

    // ---- the clock of our scene (SilentGateSpell: CAST 992, STRIKE_LAG 7, STRIKE_RAYS 260, STRIKE_END 300) ------------------------
    static final int CAST = 992, STRIKE_LAG = 7, STRIKE_RAYS = 260, STRIKE_END = 300;

    static double sm(double x) { x = Math.max(0, Math.min(1, x)); return x * x * (3 - 2 * x); }
    static double sm(double t, double a, double b) { return sm((t - a) / (b - a)); }

    /**
     * Mana strength (God Wand GatePose.manaGain on our clock): rises over the first second, strong through the cast, calmer (-45%) in the
     * last 4.5 s (45.1–49.6 s) and the wait, at least .7 from the command on, gone by the end of the strike.
     */
    public static double gain(Frame f) {
        double a = f.age(), g = sm(a, 0, 22) * (1 - .45 * sm(a, CAST - 90, CAST));
        if (f.commandAge() >= 0) {
            double end = STRIKE_LAG + STRIKE_RAYS - 20;
            g = Math.max(g, .7 * sm(f.commandAge(), 0, 8)) * (1 - sm(f.commandAge(), end, STRIKE_LAG + STRIKE_END - 5));
        }
        return Math.max(0, g);
    }

    static double hash(int k, int salt) { double h = Math.sin(k * 127.1 + salt * 311.7) * 43758.5453; return h - Math.floor(h); }

    /** Emits the mana of one caster; returns the quads added. {@code feet}, {@code yawDeg}: the caster's position and body yaw. */
    public static int emit(GateDraw.Ctx c, Frame f, Vec3 feet, double yawDeg) {
        if (c.fade <= 0 || f.age() < 0) return 0;
        double gain = gain(f);
        if (gain <= 0) return 0;
        int before = c.quads;
        double nMin = c.nearMin, nMax = c.nearMax;
        c.nearMin = .8; c.nearMax = 4;
        try {
            // Thick while the spell is built, thinned once the strike has begun (the frame is full of beams then).
            double load = f.commandAge() < 0 ? 1 : .4, time = f.age();
            Vec3 fwd = Vec3.directionFromRotation(0, (float) yawDeg);
            flow(c, feet, fwd, gain, time, (int) (FLOW * load));
            bands(c, feet, fwd, gain, time);
            // owner 19.11: the staff goes out after the command (its trail fades over 1 s); the wind of mana stays to the scene end
            double staff = f.commandAge() < 0 ? gain : gain * (1 - sm(f.commandAge(), 0, 20));
            if (staff > 0) wandTrail(c, f, feet, yawDeg, staff, time, load);
        } finally { c.nearMin = nMin; c.nearMax = nMax; }
        return c.quads - before;
    }

    static final int DUST_GREEN = 0x8CFFD0, DUST_TEAL = 0x9FE8FF;
    static int dustColor(int i) { return i % 4 == 0 ? 0xFFFFFF : i % 2 == 0 ? DUST_GREEN : DUST_TEAL; }

    /** The mana is a wind: born about the staff before the caster, it streams back past them and away behind, widening and lifting as it
     *  goes; a river of fine specks. Fixed to where the caster stands, so nothing the staff does can whip it. */
    static void flow(GateDraw.Ctx c, Vec3 feet, Vec3 f, double gain, double time, int count) {
        Vec3 r = f.cross(new Vec3(0, 1, 0));
        for (int i = 0; i < count && GateDraw.room(c); i++) {
            double h = hash(i, 61), life = (hash(i, 62) + time * (.006 + .006 * h)) % 1, back = -1.6 + 12 * life;
            double ring = hash(i, 63) * 6.2831853 + .6 * Math.sin(time * .02 + i), rad = (.25 + 1.5 * hash(i, 64)) * (.5 + 1.3 * life);
            Vec3 at = feet.add(f.scale(-back)).add(r.scale(Math.cos(ring) * rad + .25 * Math.sin(life * 9 + i * 1.7 + time * .05)))
                    .add(0, 1.45 + Math.sin(ring) * rad * .8 + .9 * life * life, 0);
            double alpha = gain * Math.sin(Math.PI * Math.pow(life, .7)) * (.45 + .55 * Math.abs(Math.sin(time * .13 + i)));
            GateDraw.sprite(c, at, .022 + .04 * hash(i, 65), alpha, dustColor(i));
            if (i % 6 == 0) GateDraw.halo(c, at, .3 + .25 * hash(i, 66), .35 * alpha, dustColor(i));
        }
    }
    /** And long bands of it, wide and thin as gauze, ride the same wind. */
    static void bands(GateDraw.Ctx c, Vec3 feet, Vec3 f, double gain, double time) {
        Vec3 r = f.cross(new Vec3(0, 1, 0));
        for (int i = 0; i < BANDS; i++) {
            double life = (hash(i, 91) + time * (.004 + .003 * hash(i, 92))) % 1, back = -1 + 11 * life, len = 3 + 3.5 * hash(i, 93);
            double side = (hash(i, 94) - .5) * 3.2 * (.5 + life), y = .5 + 2.4 * hash(i, 95) + .8 * life;
            Vec3 a = feet.add(f.scale(-back)).add(r.scale(side)).add(0, y, 0);
            Vec3 b = a.add(f.scale(-len)).add(r.scale(.5 * Math.sin(time * .03 + i))).add(0, .35 * Math.sin(time * .04 + i * 2), 0);
            GateDraw.streamer(c, a, b, .4 + .5 * hash(i, 96), i % 3 == 0 ? 0xFFFFFF : i % 3 == 1 ? DUST_GREEN : DUST_TEAL,
                    .42 * gain * Math.sin(Math.PI * life), (hash(i, 97) - .5) * 2);
        }
    }
    /** The staff writes in the air: its head and its foot each leave a ribbon of light along the path they have just travelled, and shed
     *  specks all the while, thickest at the head, thick at the foot, thin along the shaft; the specks drift off and are taken by the wind.
     *  Where the staff was is known exactly: its pose is a function of the scene clock ({@link GateStaffPose}). */
    static void wandTrail(GateDraw.Ctx c, Frame f, Vec3 feet, double yaw, double gain, double time, double load) {
        double dt = .65;
        Vec3[] tip = new Vec3[TRAIL], pom = new Vec3[TRAIL];
        for (int j = 0; j < TRAIL; j++) {
            double t = Math.max(0, f.age() - j * dt);
            tip[j] = GateStaffPose.head(t, feet, yaw); pom[j] = GateStaffPose.foot(t, feet, yaw);
        }
        // The ribbons: the last 16 samples of each end, bright at the staff and gone at their tails; nothing while the staff hangs still.
        int n = 16;
        for (int end = 0; end < 2; end++) {
            Vec3[] p = end == 0 ? tip : pom;
            double moved = Math.min(1, p[0].distanceTo(p[n - 1]) * 1.5);
            for (int j = 0; j + 1 < n && moved > .02; j++) {
                Vec3 side = p[j + 1].subtract(p[j]).cross(p[j].subtract(c.eye));
                if (side.lengthSqr() < 1e-10) continue;
                side = side.normalize();
                double k0 = 1 - (double) j / n, k1 = 1 - (double) (j + 1) / n, a = gain * moved;
                for (int layer = 0; layer < 2; layer++) {
                    double w = layer == 0 ? .22 : .06, al = layer == 0 ? .4 : .95;
                    int col = layer == 0 ? (end == 0 ? DUST_TEAL : DUST_GREEN) : 0xFFFFFF;
                    GateDraw.gradient(c, p[j].subtract(side.scale(w * k0)), p[j], p[j + 1], p[j + 1].subtract(side.scale(w * k1)), col, 0, al * a * k0, al * a * k1, 0);
                    GateDraw.gradient(c, p[j], p[j].add(side.scale(w * k0)), p[j + 1].add(side.scale(w * k1)), p[j + 1], col, al * a * k0, 0, 0, al * a * k1);
                }
            }
        }
        // The specks: each was shed some ticks ago from where the staff then was, and has drifted since.
        Vec3 fwd = Vec3.directionFromRotation(0, (float) yaw);
        double period = (TRAIL - 1) * dt;
        int count = (int) (SHED * load);
        for (int i = 0; i < count && GateDraw.room(c); i++) {
            double phase = (hash(i, 81) + time / period) % 1, since = phase * period;
            int j = Math.min(TRAIL - 1, (int) (since / dt));
            // 45% from the head, 35% from the foot, the rest from along the shaft.
            double pick = hash(i, 82), along = pick < .45 ? 0 : pick < .8 ? 1 : hash(i, 83);
            Vec3 from = tip[j].lerp(pom[j], along);
            double a = hash(i, 84) * 6.2831853, b = hash(i, 85) * 3.14159 - 1.5708, out = (.05 + .5 * hash(i, 86)) * Math.sqrt(phase);
            Vec3 at = from.add(Math.cos(a) * Math.cos(b) * out, Math.sin(b) * out + .25 * phase, Math.sin(a) * Math.cos(b) * out)
                    .add(fwd.scale(-(.6 * phase + 2.2 * phase * phase)));
            GateDraw.sprite(c, at, (along == 0 ? .03 : .022) + .045 * hash(i, 87) * (1 - .5 * phase), gain * (1 - phase) * (.5 + .5 * Math.abs(Math.sin(time * .2 + i))),
                    dustColor(i), i % 5 == 0 ? GateAtlasGen.STAR : GateAtlasGen.GLOW, time * .05 + i);
            if (i % 6 == 0) GateDraw.halo(c, at, .3 + .25 * hash(i, 88), .35 * gain * (1 - phase), dustColor(i));
        }
    }
}
