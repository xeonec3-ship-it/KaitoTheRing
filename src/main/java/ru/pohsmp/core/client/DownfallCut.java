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
        start = now;
        rift = new Vec3(m.x, m.y, m.z);
        Entity c = mc.level.getEntity(casterId);
        casterPos = c != null ? c.position() : mc.player.position();
        Vec3 d = rift.subtract(casterPos).multiply(1, 0, 1);
        dir = d.lengthSqr() < 1e-4 ? new Vec3(-Math.cos(m.f), 0, -Math.sin(m.f)) : d.normalize();
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
        if (scene != 0) {
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
            "fx.pohsmp_core.space_closure.title"};
    private static final int[] TITLE_COLORS = {0xD4A017, 0xB89CFF, 0x7FF2EA, 0xFFE38A, 0xA890FF};

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
