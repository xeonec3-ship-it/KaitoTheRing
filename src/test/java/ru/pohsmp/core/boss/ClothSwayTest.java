package ru.pohsmp.core.boss;

import static org.junit.jupiter.api.Assertions.*;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.junit.jupiter.api.Test;

/**
 * The cloth of both Erebs on a recorded motion: run, turn on the spot, jump, knockback, teleport («Шаг сквозь отражение»), strafe, walk
 * backwards — vanilla's WalkAnimationState (LivingEntity.calculateEntityAnimation: min(dist·4, 1), lerp 0.4) and Iron's leg formulas, at
 * 60 and 144 frames a second. Every frame: angles finite and in limits, the cloth behind the body, no leg through a tail or the cape
 * (checked by plain transforms, not by the solver's formula). Also the old code (setRotX(getRotX() + …) every frame) replayed: it spins.
 * Writes build/reports/cloth/cloth_sim.json (frames for tools/cloth_fix_render.py).
 */
class ClothSwayTest {
    static final float D = ClothSway.DEG;

    /** One tick of recorded motion: horizontal step (blocks), its direction vs facing (forward component, −1..1). */
    record Tick(String what, float dist, float forward) {}

    static List<Tick> recording() {
        List<Tick> t = new ArrayList<>();
        for (int i = 0; i < 20; i++) t.add(new Tick("стоит", 0, 1));
        for (int i = 0; i < 60; i++) t.add(new Tick("бег", 0.3f, 1));
        for (int i = 0; i < 30; i++) t.add(new Tick("разворот на месте", 0, 0));
        for (int i = 0; i < 12; i++) t.add(new Tick("прыжок с места", 0, 1));
        for (int i = 0; i < 30; i++) t.add(new Tick("бег с прыжком", 0.36f, 1));
        for (int i = 0; i < 12; i++) t.add(new Tick("отбрасывание", (float) (0.9 * Math.pow(0.6, i)), -1));
        for (int i = 0; i < 10; i++) t.add(new Tick("стоит", 0, 1));
        t.add(new Tick("телепорт (Шаг сквозь отражение)", 14, 1));
        for (int i = 0; i < 20; i++) t.add(new Tick("после телепорта", 0, 1));
        for (int i = 0; i < 30; i++) t.add(new Tick("бег боком", 0.25f, 0));
        for (int i = 0; i < 30; i++) t.add(new Tick("пятится", 0.15f, -1));
        for (int i = 0; i < 30; i++) t.add(new Tick("стоит", 0, 1));
        return t;
    }

    /** vanilla WalkAnimationState */
    static final class Walk {
        float speedOld, speed, position;

        void update(float dist) {
            float target = Math.min(dist * 4, 1);
            speedOld = speed;
            speed += (target - speed) * 0.4f;
            position += speed;
        }

        float speed(float pt) {
            return speedOld + (speed - speedOld) * pt;
        }

        float position(float pt) {
            return position - speed * (1 - pt);
        }
    }

    record Frame(String what, float tick, float amount, float pos, float forward, ClothSway.Leg r, ClothSway.Leg l, float[] d) {}

    static List<Frame> simulate(int fps) {
        List<Frame> out = new ArrayList<>();
        Walk w = new Walk();
        int n = fps / 20, tick = 0;
        for (Tick t : recording()) {
            w.update(t.dist());
            for (int f = 0; f < n; f++) {
                float pt = (float) f / n;
                float amount = Math.min(1, w.speed(pt)), pos = w.position(pt);
                ClothSway.Leg r = ClothSway.ironWalk(amount, pos, true, t.forward()), l = ClothSway.ironWalk(amount, pos, false, t.forward());
                out.add(new Frame(t.what(), tick + pt, amount, pos, t.forward(), r, l, ClothSway.solve(r, l)));
            }
            tick++;
        }
        return out;
    }

    // ------------------------------------------------------------------ independent geometry (side view: y up, z back, pixels)
    /** World point of a bone-local point (pivot, offset, rotX: GeckoLib XP rotation in a y-up, front −z frame). */
    static float[] world(float py, float pz, float rot, float ly, float lz) {
        float c = (float) Math.cos(rot), s = (float) Math.sin(rot);
        return new float[] {py + ly * c - lz * s, pz + ly * s + lz * c};
    }

    static float[] local(float py, float pz, float rot, float[] p) {
        float c = (float) Math.cos(rot), s = (float) Math.sin(rot), dy = p[0] - py, dz = p[1] - pz;
        return new float[] {dy * c + dz * s, -dy * s + dz * c};
    }

    static boolean insideLeg(ClothSway.Leg leg, float[] p) {
        float[] q = local(ClothSway.LEG_PIVOT_Y + leg.posY(), leg.posZ(), leg.rotX(), p);
        float half = -q[0] >= ClothSway.BOOT_TOP ? ClothSway.BOOT_HALF : ClothSway.LEG_HALF;
        return q[0] < 0 && q[0] > -ClothSway.LEG_LEN && Math.abs(q[1]) < half;
    }

    /** Signed side of a leg point against a panel: its local z (panel frame), when within the panel's span; NaN otherwise. */
    static float sideOf(float py, float pz, float rot, float len, float[] p) {
        float[] q = local(py, pz, rot, p);
        return q[0] <= 0 && q[0] >= -len ? q[1] : Float.NaN;
    }

    static List<float[]> legPoints(ClothSway.Leg leg) {
        List<float[]> pts = new ArrayList<>();
        for (int i = 0; i <= 48; i++) {
            float y = -ClothSway.LEG_LEN * i / 48;
            float half = -y >= ClothSway.BOOT_TOP ? ClothSway.BOOT_HALF : ClothSway.LEG_HALF;
            for (float z : new float[] {-half, half})
                pts.add(world(ClothSway.LEG_PIVOT_Y + leg.posY(), leg.posZ(), leg.rotX(), y, z));
        }
        return pts;
    }

    static void checkFrame(Frame f, List<String> bad) {
        float[] d = f.d();
        String at = String.format(Locale.ROOT, "%s t=%.2f", f.what(), f.tick());
        for (float v : d) if (!Float.isFinite(v)) bad.add(at + ": NaN");
        if (d[0] < 0 || d[0] > ClothSway.COAT_LIMIT + 1e-4 || d[1] < 0 || d[1] > ClothSway.COAT_LIMIT + 1e-4) bad.add(at + ": front out of range");
        if (d[2] > 0 || d[2] < -ClothSway.COAT_LIMIT - 1e-4 || d[3] > 0 || d[3] < -ClothSway.COAT_LIMIT - 1e-4) bad.add(at + ": back out of range");
        if (d[4] > 0 || d[4] < -ClothSway.CAPE_LIMIT - 1e-4 || d[5] > 0 || d[6] > 0) bad.add(at + ": cape forward / out of range");
        ClothSway.Leg[] legs = {f.r(), f.l()};
        for (int k = 0; k < 2; k++) {
            ClothSway.Leg leg = legs[k];
            float front = ClothSway.FRONT_REST + d[k], back = ClothSway.BACK_REST + d[2 + k];
            float fz = ClothSway.FRONT_Z + d[7 + k], bz = ClothSway.BACK_Z + d[9 + k];
            if (Math.abs(d[7 + k]) > ClothSway.HINGE_MAX + 1e-4 || d[7 + k] > 0 || d[9 + k] < 0) bad.add(at + ": hinge slide " + k);
            // the panels never enter the leg
            for (int i = 0; i <= 30; i++) {
                float y = -i / 30f;
                for (float z : new float[] {-ClothSway.PANEL, ClothSway.PANEL}) {
                    if (insideLeg(leg, world(ClothSway.FRONT_Y, fz, front, y * ClothSway.FRONT_LEN, z))) bad.add(at + ": leg in front tail " + k);
                    if (insideLeg(leg, world(ClothSway.BACK_Y, bz, back, y * ClothSway.BACK_LEN, z))) bad.add(at + ": leg in back tail " + k);
                }
            }
            // and the leg stays on its side: behind the front tail, in front of the back tail
            for (float[] p : legPoints(leg)) {
                float sf = sideOf(ClothSway.FRONT_Y, fz, front, ClothSway.FRONT_LEN, p);
                if (sf < ClothSway.PANEL) bad.add(at + ": leg before front tail " + k);
                float sb = sideOf(ClothSway.BACK_Y, bz, back, ClothSway.BACK_LEN, p);
                if (sb > -ClothSway.PANEL) bad.add(at + ": leg behind back tail " + k);
            }
        }
        // the cape: behind the torso (its front face behind z 2 along the torso), every leg and back tail point in front of it
        float[][] chain = ClothSway.capeChain(d[4], d[5], d[6]);
        for (float[] seg : chain) if (seg[2] > 0) bad.add(at + ": cape tilts into the back");
        List<float[]> pts = new ArrayList<>(legPoints(f.r()));
        pts.addAll(legPoints(f.l()));
        for (int k = 0; k < 2; k++)
            for (int i = 0; i <= 30; i++)
                pts.add(world(ClothSway.BACK_Y, ClothSway.BACK_Z + d[9 + k], ClothSway.BACK_REST + d[2 + k], -ClothSway.BACK_LEN * i / 30, ClothSway.PANEL));
        for (int s = 0; s < 3; s++)
            for (float[] p : pts) {
                float side = sideOf(chain[s][0], chain[s][1], chain[s][2], ClothSway.CAPE_LEN[s], p);
                if (side > -ClothSway.PANEL) bad.add(at + ": through the cape (" + s + ")");
            }
        for (int i = 0; i <= 10; i++) {   // top panel vs the torso's back (z = 2, y 12..24)
            float[] p = world(chain[0][0], chain[0][1], chain[0][2], -ClothSway.CAPE_LEN[0] * i / 10, -ClothSway.PANEL);
            if (p[0] >= 12 && p[1] < 2) bad.add(at + ": cape in the torso");
        }
    }

    @Test
    void recordedMotion() throws IOException {
        StringBuilder json = new StringBuilder("{\"fps\":{");
        for (int fps : new int[] {60, 140}) {
            List<Frame> frames = simulate(fps);
            List<String> bad = new ArrayList<>();
            float maxStep = 0, maxFront = 0, maxBack = 0, maxCape = 0;
            float[] last = null;
            for (Frame f : frames) {
                checkFrame(f, bad);
                if (last != null) for (int i = 0; i < 7; i++) maxStep = Math.max(maxStep, Math.abs(f.d()[i] - last[i]));
                last = f.d();
                maxFront = Math.max(maxFront, Math.max(f.d()[0], f.d()[1]));
                maxBack = Math.min(maxBack, Math.min(f.d()[2], f.d()[3]));
                maxCape = Math.min(maxCape, f.d()[4] + f.d()[5] + f.d()[6]);
            }
            assertTrue(bad.isEmpty(), fps + " fps: " + bad.size() + " problems, first: " + bad.subList(0, Math.min(8, bad.size())));
            // nothing spins: a step between frames is bounded by the leg's own speed (≤ 0.7 rad a tick at a full run)
            assertTrue(maxStep < 25 * D * 60 / fps + 5 * D, fps + " fps: step " + maxStep / D + "°");
            assertTrue(maxFront < 70 * D && maxBack > -70 * D && maxCape > -75 * D, "range");
            System.out.printf(Locale.ROOT, "cloth %d fps: front ≤ %.1f°, back ≥ %.1f°, cape sum ≥ %.1f°, max step %.1f°%n", fps,
                    maxFront / D, maxBack / D, maxCape / D, maxStep / D);
            // teleport and standing: back to rest within a second (stateless, no reset needed)
            Frame end = frames.get(frames.size() - 1);
            assertEquals(0, end.d()[0], 0.5 * D);
            assertEquals(0, end.d()[2], 0.5 * D);
            assertEquals(-2 * D, end.d()[5], 0.01);
            if (fps == 60) json.append(dump(frames));
        }
        json.append("}, \"old\":").append(old(60)).append(", \"old144\":").append(old(140)).append('}');
        Path out = Path.of("build", "reports", "cloth", "cloth_sim.json");
        Files.createDirectories(out.getParent());
        Files.writeString(out, json.toString(), StandardCharsets.UTF_8);
    }

    @Test
    void staticPoses() {
        float[] rest = ClothSway.solve(ClothSway.Leg.REST, ClothSway.Leg.REST);
        assertArrayEquals(new float[] {0, 0, 0, 0, 0, -2 * D, -1 * D, 0, 0, 0, 0}, rest, 1e-4f, "rest: the model's own pose (+ the cape's sag)");
        ClothSway.Leg sit = new ClothSway.Leg(ClothSway.LEG_SIT, 0, 0);   // a rider: thighs forward, no leg through a tail
        List<String> bad = new ArrayList<>();
        checkFrame(new Frame("сидит", 0, 0, 0, 1, sit, sit, ClothSway.solve(sit, sit)), bad);
        for (float rot = -ClothSway.LEG_MAX; rot <= ClothSway.LEG_MAX; rot += D) {   // Iron's casts: any leg angle at rest position
            ClothSway.Leg l = new ClothSway.Leg(rot, 0, 0), o = new ClothSway.Leg(-rot, 0, 0);
            checkFrame(new Frame("каст", rot / D, 0, 0, 1, l, o, ClothSway.solve(l, o)), bad);
        }
        assertTrue(bad.isEmpty(), bad.subList(0, Math.min(8, bad.size())).toString());
        float[] nan = ClothSway.solve(new ClothSway.Leg(Float.NaN, Float.POSITIVE_INFINITY, 0), null);
        for (float v : nan) assertTrue(Float.isFinite(v));
        assertEquals(0.6f, ClothSway.handFloat((float) (Math.PI / 2 / 0.08)), 1e-4);
        assertEquals(0, ClothSway.handFloat(Float.NaN));
    }

    /** The old code, frame by frame: rotX += rest + swing (Bedrock signs) on top of the last frame; the hand's y += 0.6·sin. */
    static String old(int fps) {
        Walk w = new Walk();
        int n = fps / 20, tick = 0;
        float fr = 3 * D, br = -5 * D, cape = -5 * D, mid = 0, low = 0, hand = 0, maxHand = 0;
        StringBuilder sb = new StringBuilder("[");
        for (Tick t : recording()) {
            w.update(t.dist());
            for (int f = 0; f < n; f++) {
                float pt = (float) f / n, amount = Math.min(1, w.speed(pt)), pos = w.position(pt);
                float right = (float) Math.cos(pos * 0.6662f) * 1.4f * amount;
                fr += -3 * D + Math.min(0, right) * 0.55f;
                br += 5 * D + Math.max(0, right) * 0.4f;
                float legs = Math.max(right, -right);
                cape += 3 * D + Math.max(0, legs) * 0.25f;
                mid += 2 * D + Math.max(0, legs) * 0.15f;
                low += 1 * D;
                hand += 0.6f * (float) Math.sin((tick + pt) * 0.08f);
                maxHand = Math.max(maxHand, hand);
                if (f == 0 && tick % 5 == 0)
                    sb.append(String.format(Locale.ROOT, "%s{\"t\":%d,\"what\":\"%s\",\"front\":%.4f,\"back\":%.4f,\"cape\":[%.4f,%.4f,%.4f],\"hand\":%.3f}",
                            sb.length() > 1 ? "," : "", tick, t.what(), fr, br, cape, mid, low, hand));
            }
            tick++;
        }
        // the old code spun: after a few seconds the cape has gone round several times, the hand drifted by blocks
        assertTrue(Math.abs(cape) > 4 * Math.PI, "old cape " + cape);
        assertTrue(maxHand > 16 * 2, "old hand drift " + maxHand + " px");
        System.out.printf(Locale.ROOT, "old code %d fps: cape turned %.0f°, the hand rose up to %.1f px (%.1f blocks)%n", fps, cape / D, maxHand,
                maxHand / 16);
        return sb.append(']').toString();
    }

    static String dump(List<Frame> frames) {
        StringBuilder sb = new StringBuilder("\"60\":[");
        for (int i = 0; i < frames.size(); i += 3) {
            Frame f = frames.get(i);
            StringBuilder d = new StringBuilder();
            for (float v : f.d()) d.append(d.length() > 0 ? "," : "").append(String.format(Locale.ROOT, "%.4f", v));
            sb.append(String.format(Locale.ROOT,
                    "%s{\"t\":%.2f,\"what\":\"%s\",\"amount\":%.3f,\"r\":[%.4f,%.3f,%.3f],\"l\":[%.4f,%.3f,%.3f],\"d\":[%s]}",
                    i > 0 ? "," : "", f.tick(), f.what(), f.amount(), f.r().rotX(), f.r().posY(), f.r().posZ(), f.l().rotX(), f.l().posY(),
                    f.l().posZ(), d));
        }
        return sb.append(']').toString();
    }
}
