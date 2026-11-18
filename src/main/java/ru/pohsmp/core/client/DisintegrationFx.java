package ru.pohsmp.core.client;

import com.mojang.blaze3d.vertex.BufferBuilder;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Quaternionf;
import org.joml.Vector3f;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.net.Net;

/** Magic circles of Disintegration: around the caster, a closing dome around the target, then a flash and a pillar of light. */
public final class DisintegrationFx {
    private DisintegrationFx() {}

    private static final ResourceLocation CIRCLE_A = new ResourceLocation(PohCore.MODID, "textures/fx/circle_a.png");
    private static final ResourceLocation CIRCLE_B = new ResourceLocation(PohCore.MODID, "textures/fx/circle_b.png");
    private static final ResourceLocation FLARE = new ResourceLocation(PohCore.MODID, "textures/fx/flare.png");
    private static final ResourceLocation BEAM = new ResourceLocation(PohCore.MODID, "textures/fx/beam.png");

    private static final class Active {
        int caster, target, duration, variant;
        long start, fadeAt = -1;
        Vec3 lastTarget;
        float targetH = 1.8f;
    }

    private static final class Burst {
        Vec3 pos;
        long start;
        int variant;
    }

    private static final Map<Integer, Active> ACTIVE = new HashMap<>();
    private static MultiBufferSource.BufferSource SRC;

    /** Own buffers, one per texture, so quads of different textures can be interleaved and drawn in one endBatch. */
    private static MultiBufferSource.BufferSource src() {
        if (SRC == null) {
            Map<RenderType, BufferBuilder> m = new LinkedHashMap<>();
            for (ResourceLocation t : List.of(CIRCLE_A, CIRCLE_B, BEAM, FLARE)) m.put(RenderType.eyes(t), new BufferBuilder(16384));
            SRC = MultiBufferSource.immediateWithBuffers(m, new BufferBuilder(256));
        }
        return SRC;
    }
    private static final List<Burst> BURSTS = new ArrayList<>();

    public static void handle(Net.Fx m) {
        ClientLevel lvl = Minecraft.getInstance().level;
        if (lvl == null) return;
        long now = lvl.getGameTime();
        int kind = m.type & 15, variant = (m.type & 0xFF) >> 4;
        if (kind == 0) {
            Active a = new Active();
            a.caster = m.caster;
            a.target = m.target;
            a.duration = Math.max(20, m.duration);
            a.variant = variant;
            a.start = now;
            a.lastTarget = new Vec3(m.x, m.y, m.z);
            ACTIVE.put(m.caster, a);
        } else if (kind == 1) {
            ACTIVE.remove(m.caster);
            Burst b = new Burst();
            b.pos = new Vec3(m.x, m.y, m.z);
            b.start = now;
            b.variant = variant;
            BURSTS.add(b);
        } else {
            Active a = ACTIVE.get(m.caster);
            if (a != null && a.fadeAt < 0) a.fadeAt = now;
        }
    }

    @SubscribeEvent
    public static void onUnload(LevelEvent.Unload e) {
        if (e.getLevel().isClientSide()) {
            ACTIVE.clear();
            BURSTS.clear();
        }
    }

    @SubscribeEvent
    public static void onRender(RenderLevelStageEvent e) {
        if (e.getStage() != RenderLevelStageEvent.Stage.AFTER_PARTICLES) return;
        if (ACTIVE.isEmpty() && BURSTS.isEmpty()) return;
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
        PoseStack.Pose pose = ps.last();
        MultiBufferSource.BufferSource buf = src();

        Iterator<Active> it = ACTIVE.values().iterator();
        while (it.hasNext()) {
            Active a = it.next();
            double age = time - a.start;
            if (age > a.duration + 60 || (a.fadeAt >= 0 && time - a.fadeAt > 12)) {
                it.remove();
                continue;
            }
            scarlet = a.variant == 1;
            drawActive(lvl, buf, pose, a, age, time, pt, cam);
        }
        Iterator<Burst> bi = BURSTS.iterator();
        while (bi.hasNext()) {
            Burst b = bi.next();
            double age = time - b.start;
            if (age > 45) {
                bi.remove();
                continue;
            }
            scarlet = b.variant == 1;
            drawBurst(buf, pose, b, age, time, cam);
        }
        buf.endBatch();
        ps.popPose();
    }

    private static void drawActive(ClientLevel lvl, MultiBufferSource.BufferSource buf, PoseStack.Pose pose, Active a, double age, double time, float pt, Camera cam) {
        double p = Math.min(1.0, age / a.duration);
        float fade = (float) Math.min(1.0, age / 15.0);
        if (a.fadeAt >= 0) fade *= (float) Math.max(0, 1 - (time - a.fadeAt) / 12.0);
        double spinBoost = p > 0.8 ? 1 + 5 * (p - 0.8) / 0.2 : 1;
        double spin = time * 0.04 * spinBoost;

        Entity caster = lvl.getEntity(a.caster);
        if (caster != null) {
            Vec3 base = caster.getPosition(pt);
            Vec3 eye = caster.getEyePosition(pt);
            Vec3 look = caster.getViewVector(pt);
            VertexConsumer va = buf.getBuffer(RenderType.eyes(CIRCLE_A));
            flat(va, pose, base.add(0, 0.04, 0), up(), (float) (2.4 + 0.2 * Math.sin(time * 0.1)), (float) spin, 1f, 0.78f, 0.3f, fade);
            VertexConsumer vb = buf.getBuffer(RenderType.eyes(CIRCLE_B));
            flat(vb, pose, eye.add(look.scale(1.3)).add(0, -0.25, 0), look, 1.0f, (float) -spin * 1.5f, 1f, 0.85f, 0.45f, fade);
            flat(vb, pose, eye.add(look.scale(2.1)).add(0, -0.25, 0), look, 0.55f, (float) spin * 2.2f, 1f, 0.95f, 0.7f, fade * 0.9f);
        }

        Entity target = lvl.getEntity(a.target);
        if (target != null) {
            a.lastTarget = target.getPosition(pt);
            a.targetH = target.getBbHeight();
        }
        Vec3 tb = a.lastTarget;
        Vec3 c = tb.add(0, a.targetH / 2, 0);
        double close = Math.min(1.0, p / 0.85);
        VertexConsumer va = buf.getBuffer(RenderType.eyes(CIRCLE_A));
        VertexConsumer vb = buf.getBuffer(RenderType.eyes(CIRCLE_B));
        float groundR = (float) (4.5 - 2.3 * close);
        flat(va, pose, new Vec3(tb.x, tb.y - (target != null ? Math.min(0.75, age / 25.0 * 0.75) : 0) + 0.04, tb.z), up(), groundR, (float) -spin, 1f, 0.9f, 0.6f, fade);
        double topH = 5.0 - 2.6 * close + a.targetH / 2;
        flat(vb, pose, c.add(0, topH - a.targetH / 2, 0), up(), (float) (2.4 - 1.0 * close), (float) spin * 1.3f, 1f, 0.8f, 0.35f, fade);

        double R = 3.4 - 2.3 * close;
        float s = (float) (1.15 - 0.45 * close);
        for (int i = 0; i < 6; i++) {
            double appear = 0.04 + i * 0.09;
            if (p < appear) continue;
            float f = fade * (float) Math.min(1.0, (p - appear) / 0.06);
            double yaw = i * Math.PI / 3 + time * 0.012 * spinBoost;
            double pitch = (i % 2 == 0 ? 0.42 : -0.18);
            Vec3 dir = new Vec3(Math.cos(yaw) * Math.cos(pitch), Math.sin(pitch), Math.sin(yaw) * Math.cos(pitch));
            flat(i % 2 == 0 ? va : vb, pose, c.add(dir.scale(R)), dir, s, (float) (spin * (i % 2 == 0 ? 1.7 : -1.7)), 1f, 0.88f, 0.5f, f);
        }

        if (p > 0.75) {
            float k = (float) ((p - 0.75) / 0.25);
            VertexConsumer vf = buf.getBuffer(RenderType.eyes(FLARE));
            billboard(vf, pose, c, cam, 0.3f + 1.6f * k * k, 1f, 0.95f, 0.8f, fade * k);
        }
        if (caster != null && p > 0.15) {
            float k = (float) Math.min(1.0, (p - 0.15) / 0.2) * fade;
            Vec3 from = caster.getEyePosition(pt).add(caster.getViewVector(pt).scale(2.1)).add(0, -0.25, 0);
            VertexConsumer vbeam = buf.getBuffer(RenderType.eyes(BEAM));
            beamLine(vbeam, pose, from, c, cam, 0.06f + 0.1f * (float) p, 1f, 0.85f, 0.45f, k * 0.6f);
        }
    }

    private static void drawBurst(MultiBufferSource.BufferSource buf, PoseStack.Pose pose, Burst b, double age, double time, Camera cam) {
        Vec3 c = b.pos;
        if (age < 10) {
            float k = (float) (1 - age / 10.0);
            billboard(buf.getBuffer(RenderType.eyes(FLARE)), pose, c, cam, 2f + 6f * (float) (age / 10.0), 1f, 1f, 0.9f, k);
        }
        float pk = (float) Math.max(0, 1 - age / 40.0);
        float w = 1.8f * pk;
        VertexConsumer vbeam = buf.getBuffer(RenderType.eyes(BEAM));
        for (int i = 0; i < 4; i++) pillar(vbeam, pose, c.add(0, -2, 0), 48f, w, i * (float) Math.PI / 4, 1f, 0.92f, 0.65f, pk);
        float rk = (float) Math.max(0, 1 - age / 30.0);
        flat(buf.getBuffer(RenderType.eyes(CIRCLE_A)), pose, c, up(), 2f + 9f * (float) (age / 30.0), (float) (time * 0.1), 1f, 0.9f, 0.6f, rk);
    }

    // ---- geometry ----

    private static Vec3 up() {
        return new Vec3(0, 1, 0);
    }

    /** Square textured quad of half-size r centered at c, its plane facing normal n, spun around n. Additive: color is scaled by alpha. */
    private static void flat(VertexConsumer vc, PoseStack.Pose pose, Vec3 c, Vec3 n, float r, float spin, float cr, float cg, float cb, float alpha) {
        if (alpha <= 0.01f) return;
        Quaternionf q = new Quaternionf().rotationTo(0, 1, 0, (float) n.x, (float) n.y, (float) n.z).rotateY(spin);
        Vector3f[] v = {new Vector3f(-r, 0, -r), new Vector3f(-r, 0, r), new Vector3f(r, 0, r), new Vector3f(r, 0, -r)};
        for (Vector3f x : v) q.transform(x).add((float) c.x, (float) c.y, (float) c.z);
        quad(vc, pose, v, cr * alpha, cg * alpha, cb * alpha);
    }

    private static void billboard(VertexConsumer vc, PoseStack.Pose pose, Vec3 c, Camera cam, float r, float cr, float cg, float cb, float alpha) {
        if (alpha <= 0.01f) return;
        Quaternionf q = cam.rotation();
        Vector3f[] v = {new Vector3f(-r, -r, 0), new Vector3f(-r, r, 0), new Vector3f(r, r, 0), new Vector3f(r, -r, 0)};
        for (Vector3f x : v) q.transform(x).add((float) c.x, (float) c.y, (float) c.z);
        quad(vc, pose, v, cr * alpha, cg * alpha, cb * alpha);
    }

    private static void pillar(VertexConsumer vc, PoseStack.Pose pose, Vec3 base, float h, float w, float yaw, float cr, float cg, float cb, float alpha) {
        if (alpha <= 0.01f || w <= 0.01f) return;
        float dx = (float) Math.cos(yaw) * w, dz = (float) Math.sin(yaw) * w;
        float x = (float) base.x, y = (float) base.y, z = (float) base.z;
        Vector3f[] v = {new Vector3f(x - dx, y, z - dz), new Vector3f(x - dx, y + h, z - dz), new Vector3f(x + dx, y + h, z + dz), new Vector3f(x + dx, y, z + dz)};
        quad(vc, pose, v, cr * alpha, cg * alpha, cb * alpha);
    }

    /** Camera-facing ribbon from a to b. */
    private static void beamLine(VertexConsumer vc, PoseStack.Pose pose, Vec3 a, Vec3 b, Camera cam, float w, float cr, float cg, float cb, float alpha) {
        if (alpha <= 0.01f) return;
        Vec3 d = b.subtract(a);
        Vec3 toCam = cam.getPosition().subtract(a);
        Vec3 side = d.cross(toCam);
        if (side.lengthSqr() < 1e-6) return;
        side = side.normalize().scale(w);
        Vector3f[] v = {vec(a.subtract(side)), vec(b.subtract(side)), vec(b.add(side)), vec(a.add(side))};
        quad(vc, pose, v, cr * alpha, cg * alpha, cb * alpha);
    }

    private static Vector3f vec(Vec3 v) {
        return new Vector3f((float) v.x, (float) v.y, (float) v.z);
    }

    private static final float[][] UV = {{0, 0}, {0, 1}, {1, 1}, {1, 0}};

    /** Replica look: gold turns scarlet, the near-white core stays light. Set per drawn effect. */
    private static boolean scarlet;

    private static void quad(VertexConsumer vc, PoseStack.Pose pose, Vector3f[] v, float r, float g, float b) {
        if (scarlet) {
            float w = Math.max(0f, Math.min(1f, (g / Math.max(r, 1e-4f) - 0.85f) / 0.15f)); // colors come pre-scaled by alpha: judge by g/r
            g = g * (0.18f + 0.82f * w * w);
            b = b * (0.25f + 0.75f * w * w);
        }
        Matrix4f m = pose.pose();
        Matrix3f n = pose.normal();
        for (int i = 0; i < 4; i++) vert(vc, m, n, v[i], UV[i], r, g, b);
        for (int i = 3; i >= 0; i--) vert(vc, m, n, v[i], UV[i], r, g, b);
    }

    private static void vert(VertexConsumer vc, Matrix4f m, Matrix3f n, Vector3f p, float[] uv, float r, float g, float b) {
        vc.vertex(m, p.x, p.y, p.z).color(r, g, b, 1f).uv(uv[0], uv[1]).overlayCoords(OverlayTexture.NO_OVERLAY)
                .uv2(LightTexture.FULL_BRIGHT).normal(n, 0, 1, 0).endVertex();
    }
}
