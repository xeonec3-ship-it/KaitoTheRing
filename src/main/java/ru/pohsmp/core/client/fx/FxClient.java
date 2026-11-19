package ru.pohsmp.core.client.fx;

import com.mojang.blaze3d.vertex.BufferBuilder;
import com.mojang.blaze3d.vertex.PoseStack;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import ru.pohsmp.core.client.ClientConfig;
import ru.pohsmp.core.fx.FxDef;
import ru.pohsmp.core.fx.FxLib;
import ru.pohsmp.core.fx.FxStyle;
import ru.pohsmp.core.fx.sigil.SigilDef;
import ru.pohsmp.core.net.FxMsg;

/** Client side of ru.pohsmp.core.fx: keeps running instances from FxMsg, draws them after particles, screen tint/flash. */
public final class FxClient {
    private FxClient() {}

    private static final class Inst {
        FxRun fx;
        SigilRun sigil;
        MeshDraw.Run mesh;
        double start, meshStopAt = -1;

        Vec3 where(float pt) {
            if (fx != null) return fx.origin(pt);
            if (sigil != null) return sigil.pos(pt);
            return mesh.pos(pt);
        }

        void stop(double now) {
            double t = now - start;
            if (fx != null && Double.isNaN(fx.stopAt)) fx.stopAt = Math.max(0, t);
            if (sigil != null) sigil.stop(t);
            if (mesh != null) mesh.stop(t);
        }
    }

    private static final Map<Integer, Inst> LIVE = new LinkedHashMap<>();
    private static MultiBufferSource.BufferSource SRC;

    public static void handle(FxMsg m) {
        ClientLevel lvl = Minecraft.getInstance().level;
        if (m.op == FxMsg.RELOAD) {
            FxLib.reload();
            FxDraw.clearTextures();
            return;
        }
        if (lvl == null) return;
        double now = lvl.getGameTime();
        if (m.op == FxMsg.STOP) {
            Inst i = LIVE.get(m.inst);
            if (i != null) i.stop(now);
            return;
        }
        if (m.op == FxMsg.TEXT) {
            Inst i = LIVE.get(m.inst);
            if (i != null && i.sigil != null) i.sigil.setText(m.slot, m.text, now - i.start);
            return;
        }
        if (m.op == FxMsg.MOVE) {
            Inst i = LIVE.get(m.inst);
            if (i == null) return;
            Vec3 p = new Vec3(m.x, m.y, m.z);
            if (i.fx != null) {
                i.fx.base = p;
                i.fx.yaw = m.yaw;
                i.fx.pitch = m.pitch;
            }
            if (i.sigil != null) {
                i.sigil.base = p;
                i.sigil.yaw = m.yaw;
            }
            if (i.mesh != null) {
                i.mesh.base = p;
                i.mesh.yaw = m.yaw;
                i.mesh.pitch = m.pitch;
            }
            return;
        }
        if (m.op != FxMsg.START) return;
        if (LIVE.size() >= ClientConfig.FX_MAX.get()) {
            Iterator<Integer> it = LIVE.keySet().iterator();
            it.next();
            it.remove();
        }
        Inst i = new Inst();
        i.start = now - m.age;
        Vec3 base = new Vec3(m.x, m.y, m.z);
        Entity caster = m.caster >= 0 ? lvl.getEntity(m.caster) : null;
        Entity attach = m.attach >= 0 ? lvl.getEntity(m.attach) : null;
        if (m.kind == FxMsg.FX) {
            FxDef d = FxLib.fx(m.id);
            if (d == null) return;
            FxRun r = new FxRun();
            r.def = d;
            r.style = FxLib.style(m.style == null || m.style.isEmpty() ? d.style() : m.style);
            r.start = i.start;
            r.duration = m.duration;
            r.base = base;
            r.yaw = m.yaw;
            r.pitch = m.pitch;
            r.caster = caster;
            r.target = m.target >= 0 ? lvl.getEntity(m.target) : null;
            r.attach = attach;
            if (attach != null) r.attachOffset = base.subtract(attach.position());
            if (m.hasTarget) r.targetPos = new Vec3(m.tx, m.ty, m.tz);
            if (m.hasLook) r.look = new Vec3(m.lx, m.ly, m.lz);
            m.points.forEach((k, v) -> r.points.put(k, new Vec3(v[0], v[1], v[2])));
            r.scale = m.scale;
            r.seed = m.seed;
            r.color = m.color;
            i.fx = r;
        } else if (m.kind == FxMsg.SIGIL) {
            SigilDef d = FxLib.sigil(m.id);
            if (d == null) return;
            SigilRun r = new SigilRun();
            r.def = d;
            r.base = base;
            r.caster = caster;
            if (attach != null) {
                r.follow = attach;
                r.offset = base.subtract(attach.position());
            }
            r.yaw = m.yaw;
            r.color = m.color;
            r.scale = m.scale;
            if (m.orientation >= 0 && m.orientation < SigilDef.Orientation.values().length) r.orient = SigilDef.Orientation.values()[m.orientation];
            r.start = i.start;
            if (m.duration >= 0) r.stopAfter = m.duration;
            r.seed = m.seed;
            r.texts.putAll(m.texts);
            i.sigil = r;
        } else {
            var d = FxLib.mesh(m.id);
            if (d == null) return;
            MeshDraw.Run r = new MeshDraw.Run();
            r.def = d;
            String st = m.style != null && !m.style.isEmpty() ? m.style : d.has("style") ? d.get("style").getAsString() : "divine";
            r.style = FxLib.style(st);
            r.base = base;
            if (attach != null) {
                r.follow = attach;
                r.offset = base.subtract(attach.position());
            }
            r.yaw = m.yaw;
            r.pitch = m.pitch;
            r.start = i.start;
            r.scale = m.scale;
            if (m.duration >= 0 && m.age >= m.duration) r.stop(m.duration);
            i.mesh = r;
            if (m.duration >= 0) i.meshStopAt = m.duration;
        }
        Inst old = LIVE.put(m.inst, i);
        if (old != null) old.stop(now);
    }

    private static MultiBufferSource.BufferSource src() {
        if (SRC == null) SRC = MultiBufferSource.immediate(new BufferBuilder(1 << 18));
        return SRC;
    }

    @SubscribeEvent
    public static void onRender(RenderLevelStageEvent e) {
        if (e.getStage() != RenderLevelStageEvent.Stage.AFTER_PARTICLES) return;
        tintA = 0;
        flashA = 0;
        if (LIVE.isEmpty()) return;
        Minecraft mc = Minecraft.getInstance();
        ClientLevel lvl = mc.level;
        if (lvl == null) return;
        float pt = e.getPartialTick();
        double time = lvl.getGameTime() + pt;
        Camera cam = e.getCamera();
        Vec3 cp = cam.getPosition();
        PoseStack ps = e.getPoseStack();
        ps.pushPose();
        ps.translate(-cp.x, -cp.y, -cp.z);
        MultiBufferSource.BufferSource buf = src();
        boolean low = "low".equals(ClientConfig.FX_QUALITY.get());
        FxDraw.Frame f = new FxDraw.Frame(ps.last(), buf, cam, cp, time, pt, low);
        double max = ClientConfig.FX_DISTANCE.get();
        Iterator<Inst> it = LIVE.values().iterator();
        while (it.hasNext()) {
            Inst i = it.next();
            if (i.mesh != null && i.meshStopAt >= 0 && time - i.start >= i.meshStopAt) i.mesh.stop(i.meshStopAt);
            boolean far = i.where(pt).distanceToSqr(cp) > max * max;
            boolean alive;
            try {
                alive = far ? !expired(i, time) : draw(f, i, time, pt);
            } catch (RuntimeException ex) {
                alive = false;
            }
            if (!alive) it.remove();
        }
        buf.endBatch();
        ps.popPose();
    }

    /** Without drawing: is a far instance surely over? */
    private static boolean expired(Inst i, double time) {
        double t = time - i.start;
        if (i.fx != null) {
            int len = i.fx.length();
            return len >= 0 && t > len + 200 || !Double.isNaN(i.fx.stopAt) && t > i.fx.stopAt + 200;
        }
        if (i.sigil != null) return !Double.isNaN(i.sigil.stopAt) && t > i.sigil.stopAt + 200 || i.sigil.stopAfter >= 0 && t > i.sigil.stopAfter + 200;
        return !Double.isNaN(i.mesh.stopAt) && t > i.mesh.stopAt + 200;
    }

    private static boolean draw(FxDraw.Frame f, Inst i, double time, float pt) {
        if (i.sigil != null) return SigilDraw.draw(f, i.sigil);
        if (i.mesh != null) return MeshDraw.draw(f, i.mesh);
        FxRun r = i.fx;
        double t = time - r.start;
        int len = r.length();
        if (Double.isNaN(r.stopAt) && len >= 0 && t >= len) r.stopAt = len;
        FxDef.Context ctx = r.ctx(pt);
        boolean alive = false;
        var els = r.def.elements();
        for (int k = 0; k < els.size(); k++) alive |= ElementDraw.draw(f, r, k, els.get(k), t, ctx);
        return alive;
    }

    // ---------------------------------------------------------------- screen

    private static int tintC, flashC;
    private static double tintA, flashA;

    static void tint(int rgb, double a) {
        if (a > tintA) {
            tintA = Math.min(0.85, a);
            tintC = rgb;
        }
    }

    /** White-out from a flash at p, fading to nothing at `radius` blocks from the camera. */
    static void screenFlash(Vec3 p, int rgb, double a, double radius) {
        Camera cam = Minecraft.getInstance().gameRenderer.getMainCamera();
        double d = cam.getPosition().distanceTo(p);
        double k = a * Math.max(0, 1 - d / radius);
        if (k > flashA) {
            flashA = Math.min(1, k);
            flashC = rgb;
        }
    }

    @SubscribeEvent
    public static void onGui(RenderGuiEvent.Post e) {
        var g = e.getGuiGraphics();
        int w = e.getWindow().getGuiScaledWidth(), h = e.getWindow().getGuiScaledHeight();
        if (tintA > 0.004) g.fill(0, 0, w, h, (int) (tintA * 255) << 24 | tintC & 0xFFFFFF);
        if (flashA > 0.004) g.fill(0, 0, w, h, (int) (flashA * 255) << 24 | flashC & 0xFFFFFF);
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) {
            LIVE.clear();
            tintA = 0;
            flashA = 0;
        }
    }
}
