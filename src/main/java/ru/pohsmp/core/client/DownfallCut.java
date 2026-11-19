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
        boolean rite = scene == RITE_SEAL || scene == RITE_BLESS;
        targetId = rite ? m.i : -1;   // T21: i = the target's entity id (the other scenes: a time offset)
        start = rite ? now : now - Math.max(0, m.i);
        releaseAt = -1;
        rift = new Vec3(m.x, m.y, m.z);
        Entity c = mc.level.getEntity(casterId);
        casterPos = c != null ? c.position() : mc.player.position();
        Vec3 d = rift.subtract(casterPos).multiply(1, 0, 1);
        dir = d.lengthSqr() < 1e-4 ? new Vec3(-Math.cos(m.f), 0, -Math.sin(m.f)) : d.normalize();
        if (scene == STAR) dir = new Vec3(Math.cos(m.f), 0, Math.sin(m.f));   // the server's caster -> impact, so the star path matches the fx
        if (rite && d.lengthSqr() < 1e-4) dir = new Vec3(Math.cos(m.f), 0, Math.sin(m.f));   // Blessing on oneself: the way the caster looks
        portalYaw = m.f;
        retinue = 2;   // until the server says (older servers: two exits)
        CamGuard.reset();
        active = true;
    }

    /** Coven Arrival: how many of the retinue step out (all but the last in 30-38 s, each an equal share; the last after the caster). */
    private static int retinue = 2;

    public static void covenRetinue(int forKey, int n) {
        if (forKey == key) retinue = Math.max(0, Math.min(ru.pohsmp.core.spell.CovenArrivalSpell.MAX_RETINUE, n));
    }

    public static void stop(int k) {
        if (!active || k != key) return;
        if (scene != RITE_SEAL && scene != RITE_BLESS && scene != BUTTERFLY) {
            active = false;
            return;
        }
        ClientLevel lvl = Minecraft.getInstance().level;   // T21: the camera glides back to the player in 1 s
        if (releaseAt < 0 && lvl != null) releaseAt = lvl.getGameTime();
    }

    // ---- T21 «Печать души» / «Благословение» (docs/specs/tasks/T21_soul_seal_blessing.md, «Ролики камеры») ----

    private static final int RITE_SEAL = ru.pohsmp.core.spell.Cutscene.SOUL_SEAL, RITE_BLESS = ru.pohsmp.core.spell.Cutscene.BLESSING;
    private static final int RELEASE = 20, BLEND = 12;
    private static int targetId = -1;
    private static long releaseAt = -1;
    private static Vec3 lastPos;
    private static float lastYaw, lastPitch;

    private static double sine(double u) {
        u = Math.max(0, Math.min(1, u));
        return 0.5 - 0.5 * Math.cos(Math.PI * u);
    }

    /** Shot starts (ticks) and which starts are hard cuts (no glide into them). */
    private static final int[] SEAL_AT = {0, 40, 80, 120, 160, 190, 200}, BLESS_AT = {0, 40, 80, 120, 180, 200};
    private static final boolean[] SEAL_CUT = {false, false, false, true, false, false, false}, BLESS_CUT = {false, false, false, false, false, false};

    /**
     * The rite camera at tick t: the shot it is in, glided (easeInOutSine, BLEND ticks) from the end of the previous one unless it opens
     * with a cut. c: caster, tg: target (the caster himself for a Blessing on oneself), dir: caster -> target (flat), side: its left.
     * Returns pos, look and (shake, 0, 0).
     */
    private static Vec3[] rite(double t, Vec3 c, Vec3 tg, Vec3 dir, Vec3 side) {
        boolean seal = scene == RITE_SEAL;
        int[] at = seal ? SEAL_AT : BLESS_AT;
        boolean[] cut = seal ? SEAL_CUT : BLESS_CUT;
        int i = 0;
        while (i < at.length - 1 && t >= at[i + 1]) i++;
        Vec3[] now = riteShot(seal, i, t, c, tg, dir, side);
        if (i == 0 || cut[i] || t - at[i] >= BLEND) return now;
        Vec3[] prev = riteShot(seal, i - 1, at[i], c, tg, dir, side);
        double u = sine((t - at[i]) / BLEND);
        return new Vec3[] {prev[0].lerp(now[0], u), prev[1].lerp(now[1], u), now[2]};
    }

    private static Vec3[] riteShot(boolean seal, int i, double t, Vec3 c, Vec3 tg, Vec3 dir, Vec3 side) {
        int[] at = seal ? SEAL_AT : BLESS_AT;
        double end = i + 1 < at.length ? at[i + 1] : at[i] + 30;
        double k = sine((t - at[i]) / Math.max(1, end - at[i]));
        Vec3 mid = c.lerp(tg, 0.5);
        double yaw = Math.atan2(dir.z, dir.x);
        Vec3 pos, look;
        double shake = 0;
        if (seal) {
            switch (i) {
                case 0 -> {   // wide from the side: both in frame, the seal opening under the caster; slow push 9 -> 7
                    pos = mid.add(side.scale(9 - 2 * k)).add(0, 3, 0);
                    look = mid.add(0, 1, 0);
                }
                case 1 -> {   // the caster close: face and the open palm towards the target, a light orbit of 20°
                    double a = yaw + Math.toRadians(70 + 20 * k);
                    pos = c.add(Math.cos(a) * 2.2, 1.35, Math.sin(a) * 2.2);
                    look = c.add(dir.scale(0.9)).add(0, 1.45, 0);
                }
                case 2 -> {   // from the target's feet up: the lock gathering over its head in the top third
                    pos = tg.subtract(dir.scale(2.2)).add(side.scale(1.9)).add(0, 0.6 + 0.5 * k, 0);
                    look = tg.add(0, 2.4, 0);
                }
                case 3 -> {   // cut: over the caster's shoulder at the target, a slow push along the axis
                    double len = Math.max(2, tg.distanceTo(c));
                    pos = c.subtract(dir.scale(3)).subtract(side.scale(0.5)).add(0, 1.9, 0).add(dir.scale(Math.min(len * 0.45, 4) * k));
                    look = tg.add(0, 1.3, 0);
                }
                case 4 -> {   // the target close, chest high: the chains tighten, the camera trembles more and more
                    pos = tg.subtract(dir.scale(2)).add(0, 1.3, 0);
                    look = tg.add(0, 1.25, 0);
                    shake = 0.015 + 0.08 * k;
                }
                default -> {   // the strike: a jerk back 2 -> 4 in 0.2 s, the shake; then the same shot, still
                    double back = 2 + 2 * Math.min(1, (t - 190) / 4.0);
                    pos = tg.subtract(dir.scale(back)).add(0, 1.3, 0);
                    look = tg.add(0, 1.2, 0);
                    shake = t < 200 ? 0.06 : 0.3 * Math.max(0, 1 - (t - 200) / 14.0);
                }
            }
        } else {
            switch (i) {
                case 0 -> {   // high over the middle, looking down at 60°, a slow turn of 25°
                    double a = yaw + Math.PI / 2 + Math.toRadians(25 * k);
                    pos = mid.add(Math.cos(a) * 6.9, 12, Math.sin(a) * 6.9);
                    look = mid;
                }
                case 1 -> {   // the caster close: hands folded, eyes down; still, the camera breathes
                    pos = c.add(dir.scale(1.8)).add(0, 1.6 + 0.03 * Math.sin(t * 0.15), 0);
                    look = c.add(0, 1.55, 0);
                }
                case 2 -> {   // the halo over the target, the pillar: from below and the side, rising along the light
                    pos = tg.add(side.scale(2.5)).add(0, 0.8 + 1.4 * k, 0);
                    look = tg.add(0, 4 + 3 * k, 0);
                }
                case 3 -> {   // the darkness leaves: an orbit of 120° round the target at 3.5, chest high
                    double a = yaw + Math.PI + Math.toRadians(-60 + 120 * k);
                    pos = tg.add(Math.cos(a) * 3.5, 1.3, Math.sin(a) * 3.5);
                    look = tg.add(0, 1.2, 0);
                }
                default -> {   // the flash and the ring: back and up to the wide shot (6 away, 3 up), then still
                    double a = yaw + Math.PI + Math.toRadians(60);
                    Vec3 from = tg.add(Math.cos(a) * 3.5, 1.3, Math.sin(a) * 3.5), to = tg.subtract(dir.scale(6)).add(0, 3, 0);
                    pos = from.lerp(to, i == 4 ? k : 1);
                    look = tg.add(0, 1.2 - 0.7 * (i == 4 ? k : 1), 0);
                }
            }
        }
        return new Vec3[] {pos, look, new Vec3(shake, 0, 0)};
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
        boolean riteScene = scene == RITE_SEAL || scene == RITE_BLESS;
        boolean glide = riteScene || scene == BUTTERFLY;   // these glide back to the player on the server's stop
        if (t > dur + (riteScene ? ru.pohsmp.core.spell.RiteSpell.HOLD + 40 : scene == BUTTERFLY ? 40 : 20) || t < 0) {
            active = false;
            return;
        }
        Entity ce = mc.level.getEntity(casterId);
        Vec3 c = ce != null ? ce.getPosition(pt) : casterPos;
        Vec3 side = new Vec3(-dir.z, 0, dir.x), r = rift, rc = rift.add(0, 2.6, 0);
        double baseYaw = Math.atan2(dir.z, dir.x);
        Vec3 pos, look;
        double roll = 0, shake = 0;
        if (glide && releaseAt >= 0) {   // T21: back to the player's own eyes in 1 s
            double u = sine((mc.level.getGameTime() + pt - releaseAt) / RELEASE);
            Entity me = mc.getCameraEntity() != null ? mc.getCameraEntity() : mc.player;
            if (u >= 1 || lastPos == null || me == null) {
                active = false;
                return;
            }
            Vec3 eye = me.getEyePosition(pt);
            if (!apply(e.getCamera(), lastPos.lerp(eye, u))) return;
            e.setYaw((float) (lastYaw + net.minecraft.util.Mth.wrapDegrees(me.getViewYRot(pt) - lastYaw) * u));
            e.setPitch((float) (lastPitch + (me.getViewXRot(pt) - lastPitch) * u));
            e.setRoll(0);
            return;
        }
        if (riteScene) {
            Entity te = targetId >= 0 ? mc.level.getEntity(targetId) : null;
            Vec3 tg = te != null ? te.getPosition(pt) : rift;
            Vec3[] pl = rite(t, c, tg, dir, side);
            pos = pl[0];
            look = pl[1];
            shake = pl[2].x;
        } else if (scene == BUTTERFLY) {
            Vec3[] pl = butterfly(t, c, dir, side, baseYaw);
            pos = pl[0];
            look = pl[1];
            shake = pl[2].x;
            roll = pl[2].y;
        } else if (scene == STAR) {
            Vec3[] pl = star(t, c, rift, dir, side, baseYaw);
            pos = pl[0];
            look = pl[1];
            shake = pl[2].x;
        } else if (scene == 5) {
            Vec3[] pl = coven(t / 20.0, ce, pt);
            pos = pl[0];
            look = pl[1];
            shake = pl[2].x;
        } else if (scene == ru.pohsmp.core.spell.Cutscene.SILENT_GATE) {
            // «Приказ»: the cast as it was, then the wait camera until the hand comes down, then the strike timed from the command
            double gs = GateOrder.sceneSeconds(key, t, mc.level.getGameTime() + pt);
            Vec3[] pl = Double.isNaN(gs) ? gateWait(GateOrder.waitSeconds(mc.level.getGameTime() + pt), c, side) : gate(gs, c, side, baseYaw);
            pos = pl[0];
            look = pl[1];
            shake = pl[2].x;
            roll = pl[2].y;
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
        pos = CamGuard.guard(mc.level, pos, look);
        Vec3 d = look.subtract(pos);
        double h = Math.sqrt(d.x * d.x + d.z * d.z);
        float yaw = (float) Math.toDegrees(Math.atan2(-d.x, d.z));
        float pitch = (float) Math.toDegrees(-Math.atan2(d.y, Math.max(1e-4, h)));
        if (!apply(e.getCamera(), pos)) return;
        e.setYaw(yaw);
        e.setPitch(pitch);
        e.setRoll((float) roll);
        lastPos = pos;
        lastYaw = yaw;
        lastPitch = pitch;
    }

    private static double portalYaw;

    // ---- T22 «Сон бабочки» (docs/specs/tasks/T22_illusion_school.md, «Ролик»): 240 ticks of cast + 20 after ----

    private static final int BUTTERFLY = ru.pohsmp.core.spell.Cutscene.BUTTERFLY_DREAM;
    private static final int[] BF_AT = {0, 40, 80, 120, 160, 200, 236};
    private static final boolean[] BF_CUT = {false, true, true, false, false, false, false};

    private static double cubic(double u) {
        u = Math.max(0, Math.min(1, u));
        return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
    }

    /** dir: the caster's look when it began (flat), side: its left. Returns pos, look, (shake, roll, 0). */
    private static Vec3[] butterfly(double t, Vec3 c, Vec3 dir, Vec3 side, double baseYaw) {
        int i = 0;
        while (i < BF_AT.length - 1 && t >= BF_AT[i + 1]) i++;
        Vec3[] now = bfShot(i, t, c, dir, side, baseYaw);
        if (i == 0 || BF_CUT[i] || t - BF_AT[i] >= BLEND) return now;
        Vec3[] prev = bfShot(i - 1, BF_AT[i], c, dir, side, baseYaw);
        double u = sine((t - BF_AT[i]) / BLEND);
        return new Vec3[] {prev[0].lerp(now[0], u), prev[1].lerp(now[1], u), now[2]};
    }

    private static Vec3[] bfShot(int i, double t, Vec3 c, Vec3 dir, Vec3 side, double baseYaw) {
        double end = i + 1 < BF_AT.length ? BF_AT[i + 1] : BF_AT[i] + 24;
        double k = sine((t - BF_AT[i]) / Math.max(1, end - BF_AT[i]));
        Vec3 right = side.scale(-1);
        Vec3 pos, look;
        double shake = 0, roll = 0;
        switch (i) {
            case 0 -> {   // the palms close, from the front and below; a very slow push 1.6 -> 1.3, the camera breathes
                pos = c.add(dir.scale(1.6 - 0.3 * k)).add(0, 1.1 + 0.025 * Math.sin(t * 0.18), 0);
                look = c.add(dir.scale(0.4)).add(0, 1.15, 0);
            }
            case 1 -> {   // cut: from the side at 4; the camera rises with the butterflies to 6 and tilts up to the sky seal
                pos = c.add(side.scale(4)).add(0, 1.2 + 4.8 * k, 0);
                look = c.add(0, 2.5 + 9.5 * k, 0);
            }
            case 2 -> {   // cut: over the caster's shoulder along the arm to the touch; a push back 0.15 at 4.3 s and 5.2 s
                double jolt = 0.15 * (Math.max(0, 1 - Math.abs(t - 88) / 6.0) + Math.max(0, 1 - Math.abs(t - 106) / 6.0));
                pos = c.subtract(dir.scale(2.2 + jolt)).add(right.scale(0.5)).add(0, 1.8, 0);
                look = c.add(dir.scale(0.65)).add(0, 1.4, 0);
            }
            case 3 -> {   // the world cracks: a 90° orbit at 6, rising 2.5 -> 5, a light tremble towards 8 s
                double a = baseYaw + Math.toRadians(-45 + 90 * k);
                pos = c.add(Math.cos(a) * 6, 2.5 + 2.5 * k, Math.sin(a) * 6);
                look = c.add(0, 1.3, 0);
                shake = 0.03 * k;
            }
            case 4 -> {   // the turn: wide, 9 away and 3 up; the camera rolls 180° in 8.0-9.4 s round its own axis
                pos = c.add(dir.scale(9)).add(0, 3, 0);
                look = c.add(0, 1.5, 0);
                roll = 180 * cubic((t - 160) / 28.0);
                shake = t < 182 ? 0.03 : 0;
            }
            case 5 -> {   // the reflection: the roll goes back 180° -> 0 in 10.0-11.2 s while the camera comes down to the face at 3.5
                pos = c.add(dir.scale(9 - 5.5 * k)).add(0, 3 - 1.4 * k, 0);
                look = c.add(0, 1.5, 0);
                roll = 180 * (1 - cubic((t - 200) / 24.0));
            }
            default -> {   // the step into the reflection, then the same shot, still
                pos = c.add(dir.scale(3.5)).add(0, 1.6, 0);
                look = c.add(0, 1.5, 0);
            }
        }
        return new Vec3[] {pos, look, new Vec3(shake, roll, 0)};
    }

    private static final net.minecraft.resources.ResourceLocation WORLD_CRACKS =
            new net.minecraft.resources.ResourceLocation(ru.pohsmp.core.PohCore.MODID, "textures/fx/illusion_world_cracks.png");

    /** The cracks over the screen in the butterfly scene: from 6.5 s (0 -> 0.6), gone by 11 s. */
    private static void butterflyOverlay(GuiGraphics g, int w, int h, double t) {
        double a = t < 130 ? 0 : t < 190 ? 0.6 * (t - 130) / 60.0 : t < 200 ? 0.6 : Math.max(0, 0.6 * (1 - (t - 200) / 20.0));
        if (a <= 0.01) return;
        com.mojang.blaze3d.systems.RenderSystem.enableBlend();
        g.setColor(1f, 1f, 1f, (float) a);
        g.blit(WORLD_CRACKS, 0, 0, w, h, 0, 0, 1024, 1024, 1024, 1024);
        g.setColor(1f, 1f, 1f, 1f);
        com.mojang.blaze3d.systems.RenderSystem.disableBlend();
    }

    /**
     * Scene 5, Coven Arrival (90 s, by seconds s). rift = the arena mark, portalYaw = the portal's facing (degrees, MC yaw):
     * people step out along forward(yaw). The caster is followed while the client knows him; otherwise the arena is shown.
     * Returns camera position, look point and (shake, 0, 0).
     */
    private static Vec3[] coven(double s, Entity ce, float pt) {
        Vec3 a = rift, pc = a.add(0, ru.pohsmp.core.spell.CovenArrivalSpell.PORTAL_Y, 0);
        Vec3 fw = new Vec3(-Math.sin(Math.toRadians(portalYaw)), 0, Math.cos(Math.toRadians(portalYaw)));
        Vec3 rt = new Vec3(-fw.z, 0, fw.x);
        Vec3 g = a.add(fw.scale(2.2));
        boolean hasC = ce != null && ce.isAlive();
        Vec3 c = hasC ? ce.getPosition(pt) : a.add(fw.scale(3));
        int before = Math.max(0, retinue - 1);   // who steps out before the caster: all but the last (CovenArrivalSpell.exitTick)
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
        } else if (s < (before == 0 ? 38 : 30)) {           // the portal unfolds: orbit (nobody before the caster: on to his exit)
            double k = smooth((s - 19) / (before == 0 ? 19 : 11)), an = base + Math.toRadians(-70 + 140 * k);
            pos = a.add(Math.cos(an) * (11 - 3 * k), 3 + 2 * k, Math.sin(an) * (11 - 3 * k));
            look = pc;
            shake = 0.02;
        } else if (s < 38) {                                // the retinue but the last steps out one by one, 8 s shared equally
            double span = 8.0 / before;
            int i = Math.min(before - 1, (int) ((s - 30) / span));
            double k = smooth((s - 30 - i * span) / span);
            if (i == 0) {                                   // №1 to the left: low angle from the right
                pos = a.add(fw.scale(6)).add(rt.scale(4)).add(0, 0.4, 0);
                look = a.add(fw.scale(1.2 + k)).subtract(rt.scale(1.3 + 1.3 * k)).add(0, 1.3, 0);
            } else {                                        // №2 to the right: the other side
                pos = a.add(fw.scale(6)).subtract(rt.scale(4)).add(0, 0.4, 0);
                look = a.add(fw.scale(1.2 + k)).add(rt.scale(1.3 + 1.3 * k)).add(0, 1.3, 0);
            }
        } else if (s < 48) {                                // the caster walks out (the last of the retinue behind him at 42 s): slow dolly from below
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
        } else if (s < 86) {                                // the dome unfolds (at 83 s): the camera sees it whole
            // The camera must stay inside the client's render distance: it was ~160 blocks out, where everything is in fog and
            // the arena chunks are not drawn, so the shot looked into empty fog (owner, 19.11: "смотрит не туда").
            double k = smooth((s - 80) / 6);
            double rd = Minecraft.getInstance().options.getEffectiveRenderDistance() * 16.0;
            double out = Math.min(ru.pohsmp.core.spell.SpaceClosureSpell.R + 22, rd * 0.7);
            if (out > ru.pohsmp.core.spell.SpaceClosureSpell.R + 8) {             // outside the shell: the whole dome against the sky
                pos = a.add(fw.scale(out - 6 * k)).add(rt.scale(out * 0.25)).add(0, 26 + 6 * k, 0);
                look = a.add(0, ru.pohsmp.core.spell.SpaceClosureSpell.R * 0.3, 0);
            } else {                                        // short render distance: from inside, up at the closing zenith
                pos = a.add(fw.scale(14 - 2 * k)).add(0, 3, 0);
                look = a.add(fw.scale(-10)).add(0, ru.pohsmp.core.spell.SpaceClosureSpell.R * 0.8, 0);
            }
            shake = s > 83 && s < 84.5 ? 0.15 : 0;
        } else {                                            // the portal collapses
            double k = smooth((s - 86) / 4);
            pos = g.add(fw.scale(6 + k)).add(0, 2, 0);
            look = pc;
            shake = 0.05 * (1 - k);
        }
        return new Vec3[] {pos, look, new Vec3(shake, 0, 0)};
    }

    /**
     * Scene 7, Gate (65 s, by seconds s, = time in the music track). c: caster, rift: strike point, dir: from the caster to it.
     * Shots as in the anime: wide shot of the land, the hand close, the gate from below, the gate with its halo, the face ("shh"),
     * the row of circles from above, the finger up from below, the sky full of seals, the rays close, the wide shot, the crystal (no main beam).
     * Returns camera position, look point and (shake, roll, 0).
     */
    /**
     * «Приказ», the wait: the camera before the witch, a little to the right of her and low, the face and the raised finger in frame;
     * a slow push-in over the 30 s of the wait. w: seconds of the wait.
     */
    private static Vec3[] gateWait(double w, Vec3 c, Vec3 side) {
        double k = smooth(w / 30);
        Vec3 pos = c.add(dir.scale(3.6 - 1.3 * k)).add(side.scale(0.7 - 0.2 * k)).add(0, 1.2 + 0.15 * k, 0);
        Vec3 look = c.add(side.scale(0.15)).add(0, 1.85, 0);
        return new Vec3[] {pos, look, new Vec3(0, 0, 0)};
    }

    /** God Wand SilentGateCinematic.raiseShot (MIT): at u 0..1, camera {1.5-1.3u fwd, 3.5-0.4u right, 1.35+0.15u up}, look {0.3-0.5u fwd, 1.45 up}. */
    private static Vec3[] gateSide(double u, Vec3 c, Vec3 side) {
        Vec3 pos = c.add(dir.scale(1.5 - 1.3 * u)).add(side.scale(3.5 - 0.4 * u)).add(0, 1.35 + 0.15 * u, 0);
        Vec3 look = c.add(dir.scale(0.3 - 0.5 * u)).add(0, 1.45, 0);
        return new Vec3[] {pos, look};
    }

    /** God Wand's FLOW curve: a move already under way when the shot opens and still going when it is cut (speed .55 of the mean at the ends). */
    private static double flow(double k) {
        k = Math.max(0, Math.min(1, k));
        return 0.55 * k + 0.45 * k * k * (3 - 2 * k);
    }

    private static double smoother(double x) {
        x = Math.max(0, Math.min(1, x));
        return x * x * x * (x * (6 * x - 15) + 10);
    }

    /** «Тсс» of the gate scene (seconds): the camera stands still (owner 19.11: the staff was hardly seen in the push-in). */
    private static final double HUSH_FROM = 38.8, HUSH_TO = 47.2;

    /**
     * The still «тсс» shot: in front of her and a touch to her right (where the staff's head hangs low), 2.9 blocks out at chest
     * height, looking between the lips and the staff on the chest — face, finger and the staff across her chest all in frame.
     */
    private static Vec3[] hush(Vec3 c, Vec3 side) {
        Vec3 pos = c.add(dir.scale(2.9)).add(side.scale(0.35)).add(0, 1.3, 0);   // side = her right (dir x up)
        Vec3 look = c.add(dir.scale(0.2)).add(side.scale(0.1)).add(0, 1.22, 0);
        return new Vec3[] {pos, look};
    }

    private static Vec3[] gate(double s, Vec3 c, Vec3 side, double yaw) {
        Vec3 f = rift, g = f.add(0, ru.pohsmp.core.spell.silent.SilentGateSpell.GATE_H, 0), face = c.add(0, 1.6, 0);
        Vec3 pos, look;
        double shake = 0, roll = 0;
        // 0–9 s and 14–21 s: the side shot of God Wand's Silent Gate (SilentGateCinematic.raiseShot, MIT, docs/third_party/god-wand-MIT.txt):
        // beside the caster on the right and a little before them, low — the witch whole, the staff afloat and the wind of mana streaming
        // back past her across the frame; the camera drifts back with the stream (their FLOW curve: never at rest).
        if (s < 9) {
            Vec3[] r = gateSide(flow(s / 9), c, side);
            pos = r[0];
            look = r[1];
        } else if (s < 14) {                            // quiet intro: slow wide orbit, the caster small in the land
            double k = smooth((s - 9) / 5), a = yaw + Math.PI + Math.toRadians(-20 + 60 * k);
            pos = c.add(Math.cos(a) * (19 - 3 * k), 7.5 - 1.5 * k, Math.sin(a) * (19 - 3 * k));
            look = c.add(0, 1.2, 0);
        } else if (s < 21) {                            // the finger points: the side shot again (owner 19.11: «сбоку», as in the mod's video)
            Vec3[] r = gateSide(flow((s - 14) / 7), c, side);
            pos = r[0];
            look = r[1];
        } else if (s < 26) {
            // the gate comes out of the circle: God Wand's circleShot — over the caster's shoulder from the ground, one glide of a tilt up
            // into the sky (their 28→52°, here to 60° so the gate 48 up and 26 ahead ends in frame)
            double u = smoother((s - 21) / 5);
            pos = c.add(dir.scale(-7 + 2.5 * u)).add(side.scale(3)).add(0, 1.2 + 1.5 * u, 0);
            look = c.add(dir.scale(26)).add(side.scale(-0.5)).add(0, 1.2 + 26 * Math.tan(Math.toRadians(28 + 32 * u)), 0);
        } else if (s < 36) {                            // the gate hangs, the halo behind it: slow orbit, gentle sway
            double k = smooth((s - 26) / 10), a = yaw + Math.PI + Math.toRadians(-35 + 70 * k);
            pos = g.add(Math.cos(a) * 40, -14 + 3 * k, Math.sin(a) * 40);
            look = g;
            roll = 3 * Math.sin(s * 0.6);
        } else if (s < HUSH_FROM) {                     // pause: the camera comes round to the front of her
            double k = smooth((s - 36) / (HUSH_FROM - 36));
            Vec3[] h = hush(c, side);
            pos = c.add(0, 1.6, 0).add(dir.scale(3.6)).add(side.scale(0.6)).lerp(h[0], k);
            look = face.lerp(h[1], k);
        } else if (s < HUSH_TO) {                       // the finger to the lips (manager 19.11): a still shot from the front, wide
            Vec3[] h = hush(c, side);                   // enough for the face, the finger and the staff across her chest
            pos = h[0];
            look = h[1];
        } else if (s < 49) {                            // green threads rise, golden circles and spheres line up in an arc: from above
            double k = smooth((s - HUSH_TO) / (49 - HUSH_TO)), a = yaw + k * 0.8;
            Vec3 mid = c.add(dir.scale(2.5));
            pos = mid.add(Math.cos(a) * 0.05, 11 - 3 * k, Math.sin(a) * 0.05);
            look = mid;
            roll = 25 * k;
        } else if (s < 50) {                            // the finger up: low angle behind the caster, looking up
            double k = smooth(s - 49);
            pos = c.subtract(dir.scale(2.2)).add(side.scale(0.9)).add(0, 0.35, 0);
            look = c.add(0, 5 + 10 * k, 0);
        } else if (s < 52) {                            // the music bursts: the whole sky of seals and their rays
            double k = smooth((s - 50) / 2);
            pos = f.subtract(dir.scale(34 - 4 * k)).add(0, 9, 0);
            look = f.add(0, 16, 0);
            shake = 0.05;
        } else if (s < 56) {                            // rays pierce the area: low, side on, tilting up from the hits to the seals
            double k = smooth((s - 52) / 4);
            pos = f.subtract(dir.scale(12 - 2 * k)).add(side.scale(8)).add(0, 2.5, 0);
            look = f.add(0, 3 + 15 * k, 0);
            shake = 0.06;
        } else if (s < 63) {                            // wide: the gate glowing in the centre, the field of seals, the rays go on
            double k = smooth((s - 56) / 7), a = yaw + Math.PI * 0.6 + k * 0.9;
            pos = f.add(Math.cos(a) * 58, 26 - 4 * k, Math.sin(a) * 58);
            look = f.add(0, 24, 0);
            shake = 0.03;
        } else {                                        // the crystal mountain; the caster stands before it
            double k = smooth((s - 63) / 2);
            pos = c.subtract(dir.scale(4.5 - k)).add(side.scale(1.6)).add(0, 2 + 0.5 * k, 0);
            look = f.add(0, 5, 0);
        }
        return new Vec3[] {pos, look, new Vec3(shake, roll, 0)};
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
            // owner 19.11: radius x3 (crater 24, light column 60 up) — the side camera ~2.7x farther, so the whole crater fits the frame
            pos = p.add(side.scale(44 + 10 * k)).subtract(dir.scale(6)).add(0, 6 + 4 * k, 0);
            look = p.add(0, 5 + 9 * k, 0);
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
            "fx.pohsmp_core.space_closure.title", "fx.pohsmp_core.coven_arrival.title", "fx.pohsmp_core.star_fall.title", "fx.pohsmp_core.silent_gate.title",
            "fx.pohsmp_core.soul_seal.title", "fx.pohsmp_core.blessing.title", "fx.pohsmp_core.butterfly_dream.title"};
    private static final int[] TITLE_COLORS = {0xD4A017, 0xB89CFF, 0x7FF2EA, 0xFFE38A, 0xA890FF, 0xB49BFF, 0xFF2A3A, 0x7FFFD0, 0x9A7BFF, 0xFFE38A, 0xC9A8FF};

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

    private static boolean hidHud, hudWas;

    /**
     * Owner 19.11: during every cutscene the HUD is off for all who watch, as with F1 (other mods' HUDs too). Called each frame from
     * GameRendererMixin before anything is drawn; F1 pressed during a scene does nothing, after it the player's own choice comes back.
     */
    public static void syncHud() {
        Minecraft mc = Minecraft.getInstance();
        if (active) {
            if (!hidHud) {
                hudWas = mc.options.hideGui;
                hidHud = true;
            }
            mc.options.hideGui = true;
        } else if (hidHud) {
            hidHud = false;
            mc.options.hideGui = hudWas;
        }
    }

    /** Fallback if the mixin did not apply: the HUD then stays on and RenderGuiEvent still runs, so the bars are drawn here. */
    @SubscribeEvent(priority = EventPriority.LOW)
    public static void onGui(net.minecraftforge.client.event.RenderGuiEvent.Post e) {
        if (!hidHud) drawBars(e.getGuiGraphics(), e.getPartialTick());
    }

    /** The bars and titles: drawn by GameRendererMixin after the (hidden) HUD, so they show with hideGui on. */
    public static void drawBars(GuiGraphics g, float pt) {
        if (!active) return;
        int w = g.guiWidth(), h = g.guiHeight();
        double t = now(pt);
        float in = (float) Math.min(1, t / 12.0);
        if (releaseAt >= 0 && Minecraft.getInstance().level != null)   // T21: the bars go with the camera
            in *= (float) (1 - sine((Minecraft.getInstance().level.getGameTime() + pt - releaseAt) / RELEASE));
        int bar = (int) (h * 0.11 * in);
        if (scene == BUTTERFLY) butterflyOverlay(g, w, h, t);
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
        // Star Fall: the title appears while the star is in flight (owner, 19.11.2026), not after the impact
        double tt = scene == 6 ? ru.pohsmp.core.spell.StarFallSpell.FALL_AT : dur * 0.88;
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
