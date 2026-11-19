package ru.pohsmp.core.client;

import com.mojang.logging.LogUtils;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.MovementInputUpdateEvent;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.client.event.RenderGuiOverlayEvent;
import net.minecraftforge.client.event.RenderHandEvent;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.util.ObfuscationReflectionHelper;
import org.slf4j.Logger;
import ru.pohsmp.core.net.Net.HFx;

/**
 * "Downfall" cutscene for players near the caster: the camera leaves the player and runs seven shots
 * (caster close-up, low angle on the seals, top-down, flight to the rift, orbit of the rift, wide shot, push-in),
 * with letterbox bars, no HUD and no movement. The server freezes these players; this only moves the view.
 */
public final class DownfallCut {
    private DownfallCut() {}

    private static final Logger LOG = LogUtils.getLogger();
    private static boolean active;
    private static int key, casterId, dur, scene;
    private static long start;
    private static Vec3 rift, casterPos, dir;
    private static Method setPos;
    private static Field detached;
    private static boolean failed;

    public static void start(HFx m, long now) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.level == null) return;
        key = m.key;
        casterId = m.a;
        scene = Math.max(0, m.b);
        dur = m.dur;
        start = now - Math.max(0, m.i);
        rift = new Vec3(m.x, m.y, m.z);
        Entity c = mc.level.getEntity(casterId);
        casterPos = c != null ? c.position() : mc.player.position();
        Vec3 d = rift.subtract(casterPos).multiply(1, 0, 1);
        dir = d.lengthSqr() < 1e-4 ? new Vec3(-Math.cos(m.f), 0, -Math.sin(m.f)) : d.normalize();
        if (scene == STAR) dir = new Vec3(Math.cos(m.f), 0, Math.sin(m.f));   // the server's caster -> impact, so the star path matches the fx
        portalYaw = m.f;
        active = true;
    }

    public static void stop(int k) {
        if (active && k == key) active = false;
    }

    public static boolean active() {
        return active;
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) active = false;
    }

    private static double now(float pt) {
        ClientLevel lvl = Minecraft.getInstance().level;
        return lvl == null ? 0 : lvl.getGameTime() + pt - start;
    }

    private static double smooth(double k) {
        k = Math.max(0, Math.min(1, k));
        return k * k * (3 - 2 * k);
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onCamera(ViewportEvent.ComputeCameraAngles e) {
        if (!active || failed) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) return;
        float pt = (float) e.getPartialTick();
        double t = now(pt);
        if (t > dur + 20 || t < 0) {
            active = false;
            return;
        }
        Entity ce = mc.level.getEntity(casterId);
        Vec3 c = ce != null ? ce.getPosition(pt) : casterPos;
        Vec3 side = new Vec3(-dir.z, 0, dir.x), r = rift, rc = rift.add(0, 2.6, 0);
        double baseYaw = Math.atan2(dir.z, dir.x);
        Vec3 pos, look;
        double roll = 0, shake = 0;
        if (scene == STAR) {
            Vec3[] pl = star(t, c, rift, dir, side, baseYaw);
            pos = pl[0];
            look = pl[1];
            shake = pl[2].x;
        } else if (scene == 5) {
            Vec3[] pl = coven(t / 20.0, ce, pt);
            pos = pl[0];
            look = pl[1];
            shake = pl[2].x;
        } else if (scene != 0) {
            Vec3[] pl = new Vec3[2];
            double[] rs = new double[2];
            shot(scene, t / dur, c, rift, dir, side, baseYaw, pl, rs);
            pos = pl[0];
            look = pl[1];
            roll = rs[0];
            shake = rs[1];
        } else if (t < 70) {            // 1: close orbit around the caster
            double k = smooth(t / 70), a = baseYaw + Math.toRadians(70 * k), rad = 3.2 - 0.6 * k;
            pos = c.add(Math.cos(a) * rad, 1.7, Math.sin(a) * rad);
            look = c.add(0, 1.4, 0);
        } else if (t < 140) {    // 2: low angle, rising, looking up at the seals over the caster
            double k = smooth((t - 70) / 70);
            pos = c.add(side.scale(2.2)).add(dir.scale(-0.8)).add(0, 0.3 + 0.8 * k, 0);
            look = c.add(0, 4 + 2 * k, 0);
        } else if (t < 210) {    // 3: top-down, the circles turning under the camera
            double k = smooth((t - 140) / 70), a = baseYaw + k * Math.PI * 0.5;
            pos = c.add(Math.cos(a) * 0.05, 15 - 5 * k, Math.sin(a) * 0.05);
            look = c;
            roll = 40 * k;
        } else if (t < 290) {    // 4: flight from the caster to the rift
            double k = smooth((t - 210) / 80);
            Vec3 from = c.add(dir.scale(-2)).add(0, 2.2, 0), to = r.subtract(dir.scale(6)).add(0, 3, 0);
            pos = from.lerp(to, k);
            look = rc;
            shake = 0.04;
        } else if (t < 380) {    // 5: orbit around the rift
            double k = smooth((t - 290) / 90), a = baseYaw + Math.PI + Math.toRadians(-100 + 200 * k);
            pos = r.add(Math.cos(a) * 9, 2.5 + 1.5 * k, Math.sin(a) * 9);
            look = rc;
        } else if (t < 450) {    // 6: wide shot over the caster's shoulder, both in frame
            double k = smooth((t - 380) / 70);
            pos = c.add(dir.scale(-4 + 1.5 * k)).add(side.scale(1.5)).add(0, 2.2, 0);
            look = rc;
            shake = 0.06;
        } else {                 // 7: push into the rift
            double k = smooth((t - 450) / 50);
            pos = r.subtract(dir.scale(10 - 6.5 * k)).add(0, 3 - 0.4 * k, 0);
            look = rc;
            shake = 0.08 + 0.2 * k;
        }
        if (shake > 0) pos = pos.add(Math.sin(t * 1.7) * shake, Math.sin(t * 2.3 + 1) * shake, Math.cos(t * 1.9) * shake);
        pos = free(mc.level, pos);
        Vec3 d = look.subtract(pos);
        double h = Math.sqrt(d.x * d.x + d.z * d.z);
        float yaw = (float) Math.toDegrees(Math.atan2(-d.x, d.z));
        float pitch = (float) Math.toDegrees(-Math.atan2(d.y, Math.max(1e-4, h)));
        if (!apply(e.getCamera(), pos)) return;
        e.setYaw(yaw);
        e.setPitch(pitch);
        e.setRoll((float) roll);
    }

    private static double portalYaw;

    /**
     * Scene 5, Coven Arrival (90 s, by seconds s). rift = the arena mark, portalYaw = the portal's facing (degrees, MC yaw):
     * people step out along forward(yaw). The caster is followed while the client knows him; otherwise the arena is shown.
     * Returns camera position, look point and (shake, 0, 0).
     */
    private static Vec3[] coven(double s, Entity ce, float pt) {
        Vec3 a = rift, pc = a.add(0, 2.9, 0);
        Vec3 fw = new Vec3(-Math.sin(Math.toRadians(portalYaw)), 0, Math.cos(Math.toRadians(portalYaw)));
        Vec3 rt = new Vec3(-fw.z, 0, fw.x);
        Vec3 g = a.add(fw.scale(2.2));
        boolean hasC = ce != null && ce.isAlive();
        Vec3 c = hasC ? ce.getPosition(pt) : a.add(fw.scale(3));
        double base = Math.atan2(fw.z, fw.x);
        Vec3 pos, look;
        double shake = 0;
        if (s < 8 || (s < 19 && !hasC)) {                    // prologue: wide orbit of the arena, the seed over its centre
            double k = smooth(s / 19), an = base + Math.toRadians(-50 + 100 * k);
            pos = a.add(Math.cos(an) * 16, 6 - 2 * k, Math.sin(an) * 16);
            look = pc;
        } else if (s < 16) {                                // at the caster: he turns, nods, draws the circle
            double k = smooth((s - 8) / 8), an = Math.toRadians(-60 + 90 * k);
            pos = c.add(Math.cos(an) * 3.2, 1.6, Math.sin(an) * 3.2);
            look = c.add(0, 1.4, 0);
        } else if (s < 19) {                                // he steps back into the portal: pull back
            double k = smooth((s - 16) / 3), an = Math.toRadians(30 + 20 * k);
            pos = c.add(Math.cos(an) * (3.2 + 2.5 * k), 1.7 + 0.6 * k, Math.sin(an) * (3.2 + 2.5 * k));
            look = c.add(0, 1.4, 0);
        } else if (s < 30) {                                // the portal unfolds: orbit
            double k = smooth((s - 19) / 11), an = base + Math.toRadians(-70 + 140 * k);
            pos = a.add(Math.cos(an) * (11 - 3 * k), 3 + 2 * k, Math.sin(an) * (11 - 3 * k));
            look = pc;
            shake = 0.02;
        } else if (s < 34) {                                // retinue 1 steps out to the left: low angle
            double k = smooth((s - 30) / 4);
            pos = a.add(fw.scale(6)).add(rt.scale(4)).add(0, 0.4, 0);
            look = a.add(fw.scale(1.2 + k)).subtract(rt.scale(1.5 + 1.5 * k)).add(0, 1.3, 0);
        } else if (s < 38) {                                // retinue 2 to the right: the other side
            double k = smooth((s - 34) / 4);
            pos = a.add(fw.scale(6)).subtract(rt.scale(4)).add(0, 0.4, 0);
            look = a.add(fw.scale(1.2 + k)).add(rt.scale(1.5 + 1.5 * k)).add(0, 1.3, 0);
        } else if (s < 48) {                                // the caster walks out: slow dolly from below
            double k = smooth((s - 38) / 10);
            pos = a.add(fw.scale(7.5 - 2 * k)).add(rt.scale(1.4)).add(0, 0.3 + 0.4 * k, 0);
            look = c.add(0, 1.5, 0);
        } else if (s < 56) {                                // the three: orbit
            double k = smooth((s - 48) / 8), an = base + Math.toRadians(-70 + 140 * k);
            pos = g.add(Math.cos(an) * 6.5, 2.2, Math.sin(an) * 6.5);
            look = g.add(0, 1.2, 0);
        } else if (s < 64) {                                // close-up, slow push-in: the line
            double k = smooth((s - 56) / 8);
            pos = c.add(fw.scale(3.2 - 1.3 * k)).add(rt.scale(0.4)).add(0, 1.6, 0);
            look = c.add(0, 1.55, 0);
        } else if (s < 69) {                                // the three, wide: the title
            double k = smooth((s - 64) / 5);
            pos = g.add(fw.scale(9 - k)).add(0, 2.5, 0);
            look = g.add(0, 1.4, 0);
        } else if (s < 80) {                                // the ritual: the camera rises with the triangle
            double k = smooth((s - 69) / 11);
            pos = g.add(fw.scale(9 + 6 * k)).add(0, 2.5 + 14 * k, 0);
            look = g.add(0, 2 + 16 * k, 0);
            shake = 0.02 * k;
        } else if (s < 86) {                                // very far outside: the dome unfolds
            double k = smooth((s - 80) / 6);
            pos = a.add(fw.scale(150 - 10 * k)).add(rt.scale(60)).add(0, 40, 0);
            look = a.add(0, 20, 0);
            shake = s > 83 && s < 84.5 ? 0.15 : 0;
        } else {                                            // the portal collapses
            double k = smooth((s - 86) / 4);
            pos = g.add(fw.scale(6 + k)).add(0, 2, 0);
            look = pc;
            shake = 0.05 * (1 - k);
        }
        return new Vec3[] {pos, look, new Vec3(shake, 0, 0)};
    }

    /** Scene 6, Star Fall. Timeline and sky point as in spell/StarFallSpell (CAST 160, the star from 100, impact at 160, 40 more). */
    private static final int STAR = 6, SF_CAST = 160, SF_FALL_AT = 100;
    private static final double SF_SKY_BACK = 45, SF_SKY_UP = 90;

    /** The star's head at tick t (ease-in-cubic from the sky point to the impact, like the fx beam). */
    private static Vec3 starHead(double t, Vec3 p, Vec3 dir) {
        Vec3 s = p.add(dir.scale(SF_SKY_BACK)).add(0, SF_SKY_UP, 0);
        double k = Math.max(0, Math.min(1, (t - SF_FALL_AT) / (SF_CAST - SF_FALL_AT)));
        return s.lerp(p, k * k * k);
    }

    /**
     * Star Fall shots by tick t. c: caster, p: impact point, dir: caster -> impact. 1: close-up of the caster (hands to the sky);
     * 2: the camera climbs behind the caster into the sky; 3: from the side, following the falling star and its trail;
     * 4: low side view of the impact, shaking after the hit. Returns camera position, look point and (shake, 0, 0).
     */
    private static Vec3[] star(double t, Vec3 c, Vec3 p, Vec3 dir, Vec3 side, double yaw) {
        Vec3 s = p.add(dir.scale(SF_SKY_BACK)).add(0, SF_SKY_UP, 0);
        Vec3 pos, look;
        double shake = 0;
        if (t < 40) {
            double k = smooth(t / 40), a = yaw + Math.toRadians(-70 + 100 * k);
            pos = c.add(Math.cos(a) * 3.2, 1.5 + 0.3 * k, Math.sin(a) * 3.2);
            look = c.add(0, 1.5 + 0.6 * k, 0);
        } else if (t < SF_FALL_AT) {
            double k = smooth((t - 40) / (SF_FALL_AT - 40));
            pos = c.subtract(dir.scale(3 + 6 * k)).add(side.scale(1.5)).add(0, 1.6 + 42 * k, 0);
            look = c.add(0, 2.5, 0).lerp(s, k);
            shake = 0.02;
        } else if (t < 150) {
            double u = smooth((t - SF_FALL_AT) / (150.0 - SF_FALL_AT));
            pos = s.lerp(p, 0.25 + 0.45 * u).add(side.scale(38)).subtract(dir.scale(8));
            look = starHead(t, p, dir);
        } else {
            double k = smooth((t - 150) / 50.0);
            pos = p.add(side.scale(16 + 4 * k)).subtract(dir.scale(3)).add(0, 2.5 + 1.5 * k, 0);
            look = p.add(0, 2 + 3 * k, 0);
            if (t >= SF_CAST) shake = 0.4 * Math.max(0, 1 - (t - SF_CAST) / 18.0);
        }
        return new Vec3[] {pos, look, new Vec3(shake, 0, 0)};
    }

    /** Shot boundaries (fractions of the cast) shared by the scenes 1-3. */
    private static final double[] CUTS = {0, 0.16, 0.32, 0.5, 0.68, 0.84, 1.0001};

    /**
     * Scenes 1 Milky Way, 2 Soul Devour, 3 Divine Taboo; u: 0..1 of the cast. c: caster, f: focus (point ahead / target / sky seal).
     * Writes camera position and look point to pl, roll and shake to rs.
     */
    private static void shot(int sc, double u, Vec3 c, Vec3 f, Vec3 dir, Vec3 side, double yaw, Vec3[] pl, double[] rs) {
        int i = 0;
        while (i < CUTS.length - 2 && u >= CUTS[i + 1]) i++;
        double k = smooth((u - CUTS[i]) / (CUTS[i + 1] - CUTS[i]));
        Vec3 pos, look;
        double roll = 0, shake = 0;
        if (sc == 1) {   // Milky Way: f = a point 14 blocks ahead
            switch (i) {
                case 0 -> { double a = yaw + Math.PI + Math.toRadians(-60 + 120 * k); pos = c.add(Math.cos(a) * 3, 1.5, Math.sin(a) * 3); look = c.add(0, 1.3, 0); }
                case 1 -> { pos = c.add(side.scale(1.8)).add(0, 0.25 + 0.5 * k, 0); look = c.add(0, 3 + 2 * k, 0); roll = -10 * k; }
                case 2 -> { double a = yaw + k * Math.PI; pos = c.add(Math.cos(a) * 0.05, 18 - 6 * k, Math.sin(a) * 0.05); look = c; roll = 60 * k; }
                case 3 -> { double a = yaw + Math.PI / 2 + k * Math.PI; pos = c.add(0, 1.4, 0).add(Math.cos(a) * (6 - 2 * k), 0.8 + 2 * k, Math.sin(a) * (6 - 2 * k)); look = c.add(0, 1.2, 0); }
                case 4 -> { pos = c.add(dir.scale(-3.5)).add(side.scale(1.2)).add(0, 2.4 - 0.6 * k, 0); look = f.lerp(c.add(dir.scale(4)).add(0, 1.6, 0), 1 - k); shake = 0.03; }
                default -> { pos = c.add(dir.scale(5 - 2 * k)).add(side.scale(-2.5)).add(0, 1.6, 0); look = c.add(dir.scale(0.6)).add(0, 1.4, 0); shake = 0.05 + 0.1 * k; }
            }
        } else if (sc == 2) {   // Soul Devour: f = the target
            Vec3 tc = f.add(0, 1.2, 0), mid = c.lerp(f, 0.5).add(0, 1.2, 0);
            Vec3 ts = new Vec3(-(f.z - c.z), 0, f.x - c.x);
            ts = ts.lengthSqr() < 1e-4 ? side : ts.normalize();
            switch (i) {
                case 0 -> { double a = yaw + Math.PI + Math.toRadians(-80 + 160 * k); pos = f.add(Math.cos(a) * 3.2, 1.6, Math.sin(a) * 3.2); look = tc; }
                case 1 -> { double a = yaw + Math.toRadians(-40 + 80 * k); pos = c.add(Math.cos(a) * 2.6, 1.5, Math.sin(a) * 2.6); look = c.add(0, 1.4, 0); }
                case 2 -> { pos = mid.add(0, 14 - 4 * k, 0).add(ts.scale(0.05)); look = mid.add(0, -1.2, 0); roll = 30 * k; }
                case 3 -> { pos = mid.add(ts.scale(7 - k)).add(0, 0.6, 0); look = mid; shake = 0.02; }
                case 4 -> { pos = f.add(0, 0.3, 0).add(ts.scale(2.5)).add(dir.scale(1)); look = f.add(0, 8, 0).lerp(tc, 1 - k * 0.6); roll = -8 * k; }
                default -> { pos = tc.add(dir.scale(-(3.5 - 2.2 * k))).add(0, 0.2, 0); look = tc; shake = 0.04 + 0.12 * k; }
            }
        } else if (sc == 4) {   // Closing of Space: f = the Coven seal 40 blocks over the caster; the dome is 86 around
            switch (i) {
                case 0 -> { double a = yaw + Math.PI + Math.toRadians(-90 + 120 * k); pos = c.add(Math.cos(a) * (3.6 - 0.6 * k), 1.6, Math.sin(a) * (3.6 - 0.6 * k)); look = c.add(0, 1.4, 0); }
                case 1 -> { pos = c.add(side.scale(-1.6)).add(dir.scale(-1)).add(0, 0.25, 0); look = c.add(0, 8 + 30 * k, 0); roll = 8 * k; }
                case 2 -> { double a = yaw + k * Math.PI * 0.8; pos = c.add(Math.cos(a) * (6 + 30 * k), 2 + 30 * k, Math.sin(a) * (6 + 30 * k)); look = c.add(0, 4 + 30 * k, 0); }
                case 3 -> { double a = yaw + Math.PI * 0.8 + k * Math.PI * 0.5; pos = c.add(Math.cos(a) * 125, 34 - 10 * k, Math.sin(a) * 125); look = c.add(0, 18, 0); }
                case 4 -> { pos = c.add(0, 150 - 40 * k, 0).add(side.scale(0.05)); look = c; roll = -70 * k; }
                default -> { double a = yaw + Math.PI + k * 0.5; pos = c.add(Math.cos(a) * (14 - 9 * k), 2.5 + 1.5 * k, Math.sin(a) * (14 - 9 * k)); look = c.add(0, 1.6 + 4 * k, 0); shake = 0.03 + 0.12 * k; }
            }
        } else {   // Divine Taboo: f = the seal 56 blocks over the caster
            switch (i) {
                case 0 -> { double a = yaw + Math.toRadians(-70 + 140 * k); pos = c.add(Math.cos(a) * 3.4, 1.4 + 0.4 * k, Math.sin(a) * 3.4); look = c.add(0, 1.4, 0); }
                case 1 -> { pos = c.add(side.scale(2)).add(0, 0.3, 0); look = c.add(0, 6 + 20 * k, 0); }
                case 2 -> { double a = yaw + k * 1.2; pos = c.add(Math.cos(a) * 4, 2 + 40 * k, Math.sin(a) * 4); look = c.add(0, 4 + 46 * k, 0); }
                case 3 -> { double a = yaw + k * Math.PI * 0.6; pos = f.add(Math.cos(a) * 30, -6 + 4 * k, Math.sin(a) * 30); look = f; }
                case 4 -> { pos = c.add(0, 70 - 20 * k, 0).add(side.scale(0.05)); look = c; roll = 90 * k; }
                default -> { double a = yaw + Math.PI + k * 0.6; pos = c.add(Math.cos(a) * (12 - 6 * k), 3 + 2 * k, Math.sin(a) * (12 - 6 * k)); look = c.add(0, 2.5 + 6 * k, 0); shake = 0.03 + 0.08 * k; }
            }
        }
        pl[0] = pos;
        pl[1] = look;
        rs[0] = roll;
        rs[1] = shake;
    }

    private static final String[] TITLES = {"fx.pohsmp_core.downfall.title", "fx.pohsmp_core.milky_way.title", "fx.pohsmp_core.soul_devour.title", "fx.pohsmp_core.divine_taboo.title",
            "fx.pohsmp_core.space_closure.title", "fx.pohsmp_core.coven_arrival.title", "fx.pohsmp_core.star_fall.title"};
    private static final int[] TITLE_COLORS = {0xD4A017, 0xB89CFF, 0x7FF2EA, 0xFFE38A, 0xA890FF, 0xB49BFF, 0xFF2A3A};

    /** Lift the camera out of solid blocks (up to 6). */
    private static Vec3 free(ClientLevel lvl, Vec3 p) {
        for (int i = 0; i < 6; i++) {
            BlockPos bp = BlockPos.containing(p);
            if (lvl.getBlockState(bp).getCollisionShape(lvl, bp).isEmpty()) return p;
            p = p.add(0, 1, 0);
        }
        return p;
    }

    private static boolean apply(Camera cam, Vec3 pos) {
        try {
            if (setPos == null) {
                // Camera.setPosition(double, double, double): the only void method of Camera taking exactly three doubles
                for (Method m : Camera.class.getDeclaredMethods()) {
                    Class<?>[] p = m.getParameterTypes();
                    if (m.getReturnType() == void.class && p.length == 3 && p[0] == double.class && p[1] == double.class && p[2] == double.class
                            && !java.lang.reflect.Modifier.isStatic(m.getModifiers()) && (m.getName().equals("m_90584_") || m.getName().equals("setPosition"))) setPos = m;
                }
                if (setPos == null) setPos = ObfuscationReflectionHelper.findMethod(Camera.class, "m_90584_", double.class, double.class, double.class);
                setPos.setAccessible(true);
                detached = ObfuscationReflectionHelper.findField(Camera.class, "f_90560_");
            }
            setPos.invoke(cam, pos.x, pos.y, pos.z);
            detached.setBoolean(cam, true);
            return true;
        } catch (Throwable t) {
            failed = true;
            active = false;
            LOG.error("[downfall] cannot move the camera: {}", t.toString());
            return false;
        }
    }

    @SubscribeEvent
    public static void onHand(RenderHandEvent e) {
        if (active) e.setCanceled(true);
    }

    @SubscribeEvent
    public static void onInput(MovementInputUpdateEvent e) {
        if (!active) return;
        e.getInput().forwardImpulse = 0;
        e.getInput().leftImpulse = 0;
        e.getInput().up = e.getInput().down = e.getInput().left = e.getInput().right = false;
        e.getInput().jumping = false;
        e.getInput().shiftKeyDown = false;
    }

    @SubscribeEvent
    public static void onOverlay(RenderGuiOverlayEvent.Pre e) {
        if (active) e.setCanceled(true);
    }

    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onGui(RenderGuiEvent.Post e) {
        if (!active) return;
        GuiGraphics g = e.getGuiGraphics();
        int w = g.guiWidth(), h = g.guiHeight();
        double t = now(e.getPartialTick());
        float in = (float) Math.min(1, t / 12.0);
        int bar = (int) (h * 0.11 * in);
        g.fill(0, 0, w, bar, 0xFF000000);
        g.fill(0, h - bar, w, h, 0xFF000000);
        if (scene == 5) {
            Font font = Minecraft.getInstance().font;
            if (t >= 1120 && t < 1290) {   // the line: first part at 56 s, the rest at 61.8 s
                Component line = Component.translatable("fx.pohsmp_core.coven_arrival.line1");
                if (t >= 1236) line = line.copy().append(" ").append(Component.translatable("fx.pohsmp_core.coven_arrival.line2"));
                float a = (float) Math.min(1, Math.min((t - 1120) / 8.0, (1290 - t) / 8.0));
                int alpha = Math.max(8, (int) (a * 255));
                g.pose().pushPose();
                g.pose().translate(w / 2f, h - bar - 26, 0);
                g.pose().scale(1.5f, 1.5f, 1f);
                g.drawString(font, line, -font.width(line) / 2, 0, (alpha << 24) | 0xEDE6FF, true);
                g.pose().popPose();
            }
            if (t >= 1280 && t < 1390) {   // the title, with lines at the sides
                float a = (float) Math.min(1, Math.min((t - 1280) / 15.0, (1390 - t) / 10.0));
                int alpha = Math.max(8, (int) (a * 255));
                Component title = Component.translatable("fx.pohsmp_core.coven_arrival.title");
                g.pose().pushPose();
                g.pose().translate(w / 2f, h * 0.66f, 0);
                g.pose().scale(2.6f, 2.6f, 1f);
                int tw = font.width(title);
                g.drawString(font, title, -tw / 2, 0, (alpha << 24) | 0xB49BFF, true);
                int lw = (int) (40 * a);
                g.fill(-tw / 2 - 6 - lw, 4, -tw / 2 - 6, 5, (alpha << 24) | 0xB49BFF);
                g.fill(tw / 2 + 6, 4, tw / 2 + 6 + lw, 5, (alpha << 24) | 0xB49BFF);
                g.pose().popPose();
            }
            return;
        }
        double tt = dur * 0.88;
        if (t > tt) {
            float a = (float) Math.min(1, (t - tt) / 15.0);
            Font font = Minecraft.getInstance().font;
            int sc = Math.min(scene, TITLES.length - 1);
            Component title = Component.translatable(TITLES[sc]);
            g.pose().pushPose();
            g.pose().translate(w / 2f, h * 0.70f, 0);
            g.pose().scale(3f, 3f, 1f);
            int alpha = Math.max(8, (int) (a * 255));
            g.drawString(font, title, -font.width(title) / 2, 0, (alpha << 24) | TITLE_COLORS[sc], true);
            g.pose().popPose();
        }
    }
}
