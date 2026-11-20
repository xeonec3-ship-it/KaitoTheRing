package ru.pohsmp.core.boss.client;

import com.mojang.logging.LogUtils;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.MovementInputUpdateEvent;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.client.event.RenderGuiOverlayEvent;
import net.minecraftforge.client.event.RenderHandEvent;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.client.gui.overlay.VanillaGuiOverlay;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.util.ObfuscationReflectionHelper;
import org.slf4j.Logger;
import ru.pohsmp.core.boss.BossMath;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.client.CamGuardAccess;

/**
 * Camera of the boss scenes (intro, specials, death, the finisher victim's close-up). Each scene id has a {@link Plan}: shots by
 * tick, each shot a function of the scene context; shots glide into each other (easeInOutSine, 12 ticks) unless they open with a
 * cut. Every frame the wanted camera goes through CamGuard (out of the terrain, turned round the focus when it collapses). On the
 * server's stop or at the end the camera glides back to the player's eyes in 1 s. Only the intro / death lock movement
 * (SCENE_LOCK_INPUT); in the special scenes the player can move and fight while the camera plays (owner: the fight does not stop).
 * Never runs while DownfallCut does.
 */
public final class BossCam {
    private BossCam() {}

    private static final Logger LOG = LogUtils.getLogger();
    private static final int RELEASE = 20, BLEND = 12;

    /** What a shot gets: the boss (or its last known place), the scene's focus and yaw, the extra entity, time. */
    public static final class Ctx {
        public Entity boss, extra;
        /** Boss feet now (interpolated) and where it was when the scene began. */
        public Vec3 b, b0, focus;
        /** Forward (the scene's yaw, flat) and its left side. */
        public Vec3 fwd, side;
        public float yaw, pt;
        public int dur;
        public ClientLevel level;

        /** A point from the boss: f blocks forward, s to its left, up. */
        public Vec3 rel(Vec3 origin, double f, double s, double up) {
            return origin.add(fwd.scale(f)).add(side.scale(s)).add(0, up, 0);
        }

        /** A point on a circle round origin: angle in degrees from forward (positive = to the left), radius, height. */
        public Vec3 orbit(Vec3 origin, double deg, double r, double up) {
            double a = Math.toRadians(deg);
            return origin.add(fwd.scale(Math.cos(a) * r)).add(side.scale(Math.sin(a) * r)).add(0, up, 0);
        }
    }

    /** One frame of a shot. */
    public record Shot(Vec3 pos, Vec3 look, double shake, double roll) {
        public static Shot of(Vec3 pos, Vec3 look) {
            return new Shot(pos, look, 0, 0);
        }

        public Shot shake(double s) {
            return new Shot(pos, look, s, roll);
        }
    }

    @FunctionalInterface
    public interface ShotFn {
        /** k: 0..1 through the shot (linear; ease it yourself), t: ticks since the scene began. */
        Shot at(double k, double t, Ctx c);
    }

    /** Shots by start tick; built once per scene id with {@link #plan}. */
    public static final class Plan {
        private final List<int[]> at = new ArrayList<>();   // {start, cut?1:0}
        private final List<ShotFn> fns = new ArrayList<>();
        private final int length;

        private Plan(int length) {
            this.length = length;
        }

        /** A shot from tick `from` (until the next one / the end), glided into. */
        public Plan shot(int from, ShotFn f) {
            at.add(new int[] {from, 0});
            fns.add(f);
            return this;
        }

        /** A shot that opens with a hard cut. */
        public Plan cut(int from, ShotFn f) {
            at.add(new int[] {from, 1});
            fns.add(f);
            return this;
        }

        Shot frame(double t, Ctx c) {
            int i = 0;
            while (i < at.size() - 1 && t >= at.get(i + 1)[0]) i++;
            Shot now = eval(i, t, c);
            int s = at.get(i)[0];
            if (i == 0 || at.get(i)[1] == 1 || t - s >= BLEND) return now;
            Shot prev = eval(i - 1, s, c);
            double u = BossMath.sine((t - s) / BLEND);
            return new Shot(prev.pos.lerp(now.pos, u), prev.look.lerp(now.look, u), now.shake, now.roll);
        }

        private Shot eval(int i, double t, Ctx c) {
            int s = at.get(i)[0];
            int e = i + 1 < at.size() ? at.get(i + 1)[0] : Math.max(s + 1, length);
            return fns.get(i).at(BossMath.clamp01((t - s) / Math.max(1, e - s)), t, c);
        }
    }

    private static final Map<String, Plan> PLANS = new HashMap<>();

    /** Registers the shots of a scene (client setup). length: the scene's ticks (the last shot runs to it). */
    public static Plan plan(String sceneId, int length) {
        Plan p = new Plan(length);
        PLANS.put(sceneId, p);
        return p;
    }

    // ---------------------------------------------------------------- state

    private static boolean active;
    private static String scene = "";
    private static Plan plan;
    private static final Ctx CTX = new Ctx();
    private static int flags, bossId, extraId;
    private static long start, releaseAt = -1;
    private static Vec3 lastPos, lastB;
    private static float lastYaw, lastPitch;
    private static Method setPos;
    private static Field detached;
    private static boolean failed;

    static void onMsg(BossNet.Msg m) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || mc.player == null) return;
        if (m.kind == BossNet.SCENE_STOP) {
            if (active && m.s1.equals(scene) && releaseAt < 0) releaseAt = mc.level.getGameTime();
            return;
        }
        if (ru.pohsmp.core.client.DownfallCut.active()) return;
        Plan p = PLANS.get(m.s1);
        if (p == null) {
            LOG.warn("[boss] no camera plan for scene {}", m.s1);
            return;
        }
        plan = p;
        scene = m.s1;
        bossId = m.a;
        extraId = m.d;
        flags = m.c;
        CTX.dur = m.b;
        CTX.focus = new Vec3(m.x, m.y, m.z);
        CTX.yaw = m.f;
        double a = Math.toRadians(m.f);
        CTX.fwd = new Vec3(-Math.sin(a), 0, Math.cos(a));   // Minecraft yaw: 0 = +z (south)
        CTX.side = new Vec3(CTX.fwd.z, 0, -CTX.fwd.x);    // its left
        Entity b = mc.level.getEntity(bossId);
        CTX.b0 = b != null ? b.position() : CTX.focus;
        lastB = CTX.b0;
        start = mc.level.getGameTime();
        releaseAt = -1;
        CamGuardAccess.reset();
        active = true;
    }

    public static boolean active() {
        return active;
    }

    /** The intro hides the boss bars until the server shows them. */
    static boolean hidesBars() {
        return active && (flags & BossNet.SCENE_NO_HUD) != 0;
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) active = false;
    }

    @SubscribeEvent(priority = EventPriority.HIGH)
    public static void onCamera(ViewportEvent.ComputeCameraAngles e) {
        if (!active || failed) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || ru.pohsmp.core.client.DownfallCut.active()) {
            active = false;
            return;
        }
        float pt = (float) e.getPartialTick();
        double t = mc.level.getGameTime() + pt - start;
        Entity me = mc.getCameraEntity() != null ? mc.getCameraEntity() : mc.player;
        if (releaseAt < 0 && t >= CTX.dur) releaseAt = mc.level.getGameTime();
        if (releaseAt >= 0 && lastPos != null) {   // back to the player's eyes in 1 s
            double u = BossMath.sine((mc.level.getGameTime() + pt - releaseAt) / RELEASE);
            if (u >= 1 || me == null) {
                active = false;
                return;
            }
            if (!apply(e.getCamera(), lastPos.lerp(me.getEyePosition(pt), u))) return;
            e.setYaw((float) (lastYaw + Mth.wrapDegrees(me.getViewYRot(pt) - lastYaw) * u));
            e.setPitch((float) (lastPitch + (me.getViewXRot(pt) - lastPitch) * u));
            e.setRoll(0);
            return;
        }
        if (releaseAt >= 0) {
            active = false;
            return;
        }
        Entity b = mc.level.getEntity(bossId);
        if (b != null) lastB = b.getPosition(pt);
        CTX.boss = b;
        CTX.b = lastB;
        CTX.extra = extraId >= 0 ? mc.level.getEntity(extraId) : null;
        CTX.pt = pt;
        CTX.level = mc.level;
        Shot s = plan.frame(t, CTX);
        Vec3 pos = s.pos;
        if (s.shake > 0) pos = pos.add(Math.sin(t * 1.7) * s.shake, Math.sin(t * 2.3 + 1) * s.shake, Math.cos(t * 1.9) * s.shake);
        pos = CamGuardAccess.guard(mc.level, pos, s.look);
        Vec3 d = s.look.subtract(pos);
        double h = Math.sqrt(d.x * d.x + d.z * d.z);
        float yaw = (float) Math.toDegrees(Math.atan2(-d.x, d.z));
        float pitch = (float) Math.toDegrees(-Math.atan2(d.y, Math.max(1e-4, h)));
        if (!apply(e.getCamera(), pos)) return;
        e.setYaw(yaw);
        e.setPitch(pitch);
        e.setRoll((float) s.roll);
        lastPos = pos;
        lastYaw = yaw;
        lastPitch = pitch;
    }

    /** Camera.setPosition and detached = true (the same reflection as DownfallCut). */
    private static boolean apply(Camera cam, Vec3 pos) {
        try {
            if (setPos == null) {
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
            LOG.error("[boss] cannot move the camera: {}", t.toString());
            return false;
        }
    }

    @SubscribeEvent
    public static void onHand(RenderHandEvent e) {
        if (active) e.setCanceled(true);
    }

    @SubscribeEvent
    public static void onInput(MovementInputUpdateEvent e) {
        if (!active || (flags & BossNet.SCENE_LOCK_INPUT) == 0) return;
        e.getInput().forwardImpulse = 0;
        e.getInput().leftImpulse = 0;
        e.getInput().up = e.getInput().down = e.getInput().left = e.getInput().right = false;
        e.getInput().jumping = false;
        e.getInput().shiftKeyDown = false;
    }

    @SubscribeEvent
    public static void onOverlay(RenderGuiOverlayEvent.Pre e) {
        if (!active) return;
        if ((flags & BossNet.SCENE_NO_HUD) != 0 || e.getOverlay() == VanillaGuiOverlay.CROSSHAIR.type()) e.setCanceled(true);
    }

    /** Letterbox bars (SCENE_BARS), in 0.6 s and out with the camera. */
    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onGui(RenderGuiEvent.Post e) {
        if (!active || (flags & BossNet.SCENE_BARS) == 0) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) return;
        GuiGraphics g = e.getGuiGraphics();
        double t = mc.level.getGameTime() + e.getPartialTick() - start;
        double in = Math.min(1, t / 12.0);
        if (releaseAt >= 0) in *= 1 - BossMath.sine((mc.level.getGameTime() + e.getPartialTick() - releaseAt) / RELEASE);
        int bar = (int) (g.guiHeight() * 0.09 * in);
        g.fill(0, 0, g.guiWidth(), bar, 0xFF000000);
        g.fill(0, g.guiHeight() - bar, g.guiWidth(), g.guiHeight(), 0xFF000000);
    }
}
