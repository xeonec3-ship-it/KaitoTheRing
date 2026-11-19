package ru.pohsmp.core.client.illusion;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.blaze3d.pipeline.RenderTarget;
import com.mojang.blaze3d.pipeline.TextureTarget;
import com.mojang.blaze3d.platform.GlStateManager;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.BufferBuilder;
import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.Tesselator;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.blaze3d.vertex.VertexFormat;
import com.mojang.math.Axis;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.client.CameraType;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.renderer.GameRenderer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.client.event.ViewportEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Matrix4f;
import org.lwjgl.opengl.GL11;
import org.lwjgl.opengl.GL30;
import ru.pohsmp.core.PohCore;

/**
 * T22 «Сон бабочки», what the screen of a dreamer does (visual letter 19.11, docs/inbox/2026-11-19_mgr_T22_dream_visuals.md):
 * the entry and exit through the mirror (ripple from the centre, the picture folds over in ticks 2-8 and stays mirrored all the dream),
 * the pearl sky and fog, the dream «death» overlay with the camera stepping back, the wound butterflies around the dreamer (seen by it and
 * the caster) and the waking: the crack grid opening from the blow, then the last frame of the dream falls apart in glass shards.
 * Drawn from GameRendererMixin (after the level; over everything) - the HUD may be hidden in a scene, RenderGuiEvent then does not come.
 */
public final class DreamScreen {
    private DreamScreen() {}

    private static ResourceLocation tex(String n) {
        return new ResourceLocation(PohCore.MODID, "textures/fx/" + n + ".png");
    }

    private static final ResourceLocation RIPPLE = tex("illusion_dream_ripple"), DEATH = tex("illusion_dream_death"), GRID = tex("illusion_wake_grid"),
            SHARDS = tex("illusion_wake_shards"), WOUND = tex("illusion_wound_butterfly");

    private static final int FOLD_FROM = 2, FOLD_TO = 8, RIPPLE_TICKS = 10, BREAK = 34, WAKE_END = 50, DEATH_CAM = 24;

    private static long enterAt = -1, exitAt = -1, deathAt = -1, wakeAt = -1;
    private static int deathLen;
    private static boolean mirrored;
    private static CameraType camWas;
    /** entity id -> wound butterflies around it */
    private static final Map<Integer, Integer> WOUNDS = new HashMap<>();

    private static long now() {
        return IllusionClient.now();
    }

    private static float since(long at, float pt) {
        return at < 0 ? Float.MAX_VALUE : now() - at + pt;
    }

    // ---------------------------------------------------------------- from the server

    static void enter() {
        if (mirrored && exitAt < 0) return;
        enterAt = now();
        exitAt = -1;
        wakeAt = -1;
        mirrored = true;
    }

    /** The dream ended for this client; ripple and fold back unless the waking scene already broke it. */
    static void exit() {
        if (!mirrored) return;
        if (wakeAt >= 0 && now() - wakeAt >= BREAK) return;
        if (wakeAt >= 0) return;   // the waking scene ends it at its break
        exitAt = now();
    }

    static void wake() {
        wakeAt = now();
    }

    static void death(int ticks) {
        deathAt = now();
        deathLen = Math.max(10, ticks);
        Minecraft mc = Minecraft.getInstance();
        if (camWas == null) {
            camWas = mc.options.getCameraType();
            mc.options.setCameraType(CameraType.THIRD_PERSON_FRONT);   // it sees itself fall apart into butterflies
        }
    }

    static void wounds(int entity, int n) {
        if (n <= 0) WOUNDS.remove(entity);
        else WOUNDS.put(entity, Math.min(12, n));
    }

    static void clear() {
        enterAt = exitAt = deathAt = wakeAt = -1;
        mirrored = false;
        WOUNDS.clear();
        restoreCam();
        snap = null;
    }

    private static void restoreCam() {
        if (camWas != null) {
            Minecraft.getInstance().options.setCameraType(camWas);
            camWas = null;
        }
    }

    @SubscribeEvent
    public static void onTick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        if (camWas != null && now() - deathAt >= DEATH_CAM) restoreCam();
        if (deathAt >= 0 && now() - deathAt > deathLen) deathAt = -1;
        if (exitAt >= 0 && now() - exitAt > FOLD_TO + 2) {
            mirrored = false;
            exitAt = enterAt = -1;
        }
        if (wakeAt >= 0) {
            long t = now() - wakeAt;
            if (t >= BREAK && mirrored) {
                mirrored = false;
                enterAt = -1;
                WOUNDS.clear();
            }
            if (t > WAKE_END) {
                wakeAt = -1;
                snap = null;
            }
        }
    }

    // ---------------------------------------------------------------- the mirror

    private static float ease(float x) {
        x = Mth.clamp(x, 0, 1);
        return (float) (-(Math.cos(Math.PI * x) - 1) / 2);
    }

    /** Horizontal scale of the picture: 1 as is, -1 mirrored. */
    private static float fold(float pt) {
        if (!mirrored) return 1;
        if (exitAt >= 0) return -1 + 2 * ease((since(exitAt, pt) - FOLD_FROM) / (FOLD_TO - FOLD_FROM));
        if (enterAt >= 0) return 1 - 2 * ease((since(enterAt, pt) - FOLD_FROM) / (FOLD_TO - FOLD_FROM));
        return -1;
    }

    private static TextureTarget temp, snap;

    private static TextureTarget fit(TextureTarget t, RenderTarget main) {
        if (t == null) t = new TextureTarget(main.width, main.height, false, Minecraft.ON_OSX);
        else if (t.width != main.width || t.height != main.height) t.resize(main.width, main.height, Minecraft.ON_OSX);
        return t;
    }

    private static void copy(int from, int to, int w, int h, int x0, int x1) {
        GlStateManager._glBindFramebuffer(GL30.GL_READ_FRAMEBUFFER, from);
        GlStateManager._glBindFramebuffer(GL30.GL_DRAW_FRAMEBUFFER, to);
        GlStateManager._glBlitFrameBuffer(0, 0, w, h, x0, 0, x1, h, GL11.GL_COLOR_BUFFER_BIT, GL11.GL_LINEAR);
    }

    /** Right after the level is drawn (hand included): fold or mirror the picture; at the waking's break keep this frame for the shards. */
    public static void afterLevel(float pt) {
        Minecraft mc = Minecraft.getInstance();
        RenderTarget main = mc.getMainRenderTarget();
        int w = main.width, h = main.height;
        float s = fold(pt);
        if (s < 0.999f) {
            temp = fit(temp, main);
            copy(main.frameBufferId, temp.frameBufferId, w, h, 0, w);
            main.bindWrite(false);
            RenderSystem.clearColor(0.08f, 0.05f, 0.12f, 1f);
            RenderSystem.clear(GL11.GL_COLOR_BUFFER_BIT, Minecraft.ON_OSX);
            int half = Math.round(Math.abs(s) * w / 2f), cx = w / 2;
            if (half > 0) copy(temp.frameBufferId, main.frameBufferId, w, h, s > 0 ? cx - half : cx + half, s > 0 ? cx + half : cx - half);
        }
        if (wakeAt >= 0 && since(wakeAt, pt) >= BREAK && snap == null) {
            snap = fit(null, main);
            copy(main.frameBufferId, snap.frameBufferId, w, h, 0, w);
        }
        main.bindWrite(true);
    }

    // ---------------------------------------------------------------- the pearl sky (ClientLevelMixin) and fog

    private static float pearl(float pt) {
        if (!mirrored && exitAt < 0) return 0;
        float in = enterAt >= 0 ? Mth.clamp(since(enterAt, pt) / 30f, 0, 1) : 1;
        float out = exitAt >= 0 ? 1 - Mth.clamp(since(exitAt, pt) / 30f, 0, 1) : 1;
        if (wakeAt >= 0 && since(wakeAt, pt) >= BREAK) return 0;
        return Math.min(in, out);
    }

    public static Vec3 sky(Vec3 c, float pt) {
        float k = pearl(pt);
        return k <= 0 ? c : c.lerp(new Vec3(0xA8 / 255.0, 0x98 / 255.0, 0xDC / 255.0), k);
    }

    @SubscribeEvent
    public static void onFog(ViewportEvent.ComputeFogColor e) {
        float k = pearl((float) e.getPartialTick());
        if (k <= 0) return;
        e.setRed(Mth.lerp(k, e.getRed(), 0xE2 / 255f));
        e.setGreen(Mth.lerp(k, e.getGreen(), 0xD6 / 255f));
        e.setBlue(Mth.lerp(k, e.getBlue(), 0xF0 / 255f));
    }

    // ---------------------------------------------------------------- over everything

    public static void overlay(GuiGraphics g, float pt) {
        if (enterAt < 0 && exitAt < 0 && deathAt < 0 && wakeAt < 0) return;
        int w = g.guiWidth(), h = g.guiHeight();
        RenderSystem.enableBlend();
        RenderSystem.defaultBlendFunc();
        RenderSystem.disableDepthTest();
        float re = since(enterAt, pt), rx = since(exitAt, pt);
        float r = Math.min(re, rx);
        if (r < RIPPLE_TICKS) {
            float k = r / RIPPLE_TICKS, size = (0.2f + 2.2f * k) * h;
            RenderSystem.setShaderColor(1, 1, 1, 0.7f * (1 - k));
            blit(g, RIPPLE, w / 2f - size / 2, h / 2f - size / 2, size, size);
        }
        float d = since(deathAt, pt);
        if (d < deathLen) {
            float a = d < 4 ? 0 : d < 7 ? (d - 4) / 3 : d < 16 ? 1 : Math.max(0, 1 - (d - 16) / 10);
            if (a > 0) {
                float z = 1 + 0.05f * Math.min(1, d / deathLen);
                RenderSystem.setShaderColor(1, 1, 1, a);
                blit(g, DEATH, w / 2f - w * z / 2, h / 2f - h * z / 2, w * z, h * z);
                RenderSystem.setShaderColor(1, 1, 1, 1);
                Component line = Component.translatable("ui.pohsmp_core.butterfly_dream.died");
                var font = Minecraft.getInstance().font;
                g.drawString(font, line, (w - font.width(line)) / 2, h / 2 + h / 5, (Math.max(4, (int) (a * 255)) << 24) | 0xE8DEFF, false);
            }
        }
        float t = since(wakeAt, pt);
        if (t <= WAKE_END) wakeOverlay(g, w, h, t);
        RenderSystem.setShaderColor(1, 1, 1, 1);
        RenderSystem.enableDepthTest();
    }

    private static void blit(GuiGraphics g, ResourceLocation tex, float x, float y, float w, float h) {
        RenderSystem.setShader(GameRenderer::getPositionTexShader);
        RenderSystem.setShaderTexture(0, tex);
        Matrix4f m = g.pose().last().pose();
        BufferBuilder b = Tesselator.getInstance().getBuilder();
        b.begin(VertexFormat.Mode.QUADS, DefaultVertexFormat.POSITION_TEX);
        b.vertex(m, x, y + h, 0).uv(0, 1).endVertex();
        b.vertex(m, x + w, y + h, 0).uv(1, 1).endVertex();
        b.vertex(m, x + w, y, 0).uv(1, 0).endVertex();
        b.vertex(m, x, y, 0).uv(0, 0).endVertex();
        Tesselator.getInstance().end();
    }

    private static void flash(GuiGraphics g, int w, int h, float a) {
        if (a > 0) g.fill(0, 0, w, h, ((int) (Mth.clamp(a, 0, 1) * 255) << 24) | 0xFFFFFF);
    }

    private static void wakeOverlay(GuiGraphics g, int w, int h, float t) {
        Shards sh = shards();
        float ix = sh == null ? 0.5f : sh.ix, iy = sh == null ? 0.46f : sh.iy;
        if (t < BREAK) {   // the cracks run out from the blow
            float k = Mth.clamp(t / 24f, 0, 1);
            float rad = (float) (1 - Math.pow(1 - k, 3)) * 1.4f * h;
            float str = 0.65f + 0.35f * Mth.clamp(t / BREAK, 0, 1);
            g.fill(0, 0, w, h, ((int) (0.35f * Mth.clamp(t / BREAK, 0, 1) * 110) << 24));   // the edges darken
            RenderSystem.setShader(GameRenderer::getPositionTexShader);
            RenderSystem.setShaderTexture(0, GRID);
            RenderSystem.setShaderColor(1, 1, 1, str);
            Matrix4f m = g.pose().last().pose();
            BufferBuilder b = Tesselator.getInstance().getBuilder();
            b.begin(VertexFormat.Mode.TRIANGLE_FAN, DefaultVertexFormat.POSITION_TEX);
            float cx = ix * w, cy = iy * h;
            b.vertex(m, cx, cy, 0).uv(ix, iy).endVertex();
            for (int i = 48; i >= 0; i--) {
                double a = Math.PI * 2 * i / 48;
                float x = Mth.clamp(cx + (float) Math.cos(a) * rad, 0, w), y = Mth.clamp(cy + (float) Math.sin(a) * rad, 0, h);
                b.vertex(m, x, y, 0).uv(x / w, y / h).endVertex();
            }
            Tesselator.getInstance().end();
            RenderSystem.setShaderColor(1, 1, 1, 1);
            flash(g, w, h, t < 3 ? 0.35f * (1 - t / 3) : 0);
            return;
        }
        // the break: the kept frame falls in pieces, the real world under them
        float alpha = t < WAKE_END - 6 ? 1 : Math.max(0, (WAKE_END - t) / 6f);
        if (snap != null && sh != null && alpha > 0) {
            for (Shard s : sh.list) {
                float ft = Math.max(0, t - BREAK - s.delay);
                float ox = s.vx * ft * w, oy = (s.vy * ft + sh.g * ft * ft / 2) * h;
                float cx = (s.sx0 + s.sx1) / 2 * w, cy = (s.sy0 + s.sy1) / 2 * h;
                PoseStack ps = g.pose();
                ps.pushPose();
                ps.translate(cx + ox, cy + oy, 0);
                ps.mulPose(Axis.ZP.rotationDegrees(s.spin * ft));
                ps.scale((float) Math.cos(Math.toRadians(s.tilt * Math.min(1, ft / 10f))), 1, 1);
                ps.translate(-cx, -cy, 0);
                Matrix4f m = ps.last().pose();
                RenderSystem.setShader(GameRenderer::getPositionTexShader);
                RenderSystem.setShaderColor(1, 1, 1, alpha);
                RenderSystem.setShaderTexture(0, snap.getColorTextureId());
                poly(m, s.poly, w, h, true);
                RenderSystem.setShaderTexture(0, GRID);
                poly(m, s.poly, w, h, false);
                RenderSystem.setShaderTexture(0, SHARDS);
                BufferBuilder b = Tesselator.getInstance().getBuilder();
                b.begin(VertexFormat.Mode.QUADS, DefaultVertexFormat.POSITION_TEX);
                b.vertex(m, s.sx0 * w, s.sy1 * h, 0).uv(s.u0, s.v1).endVertex();
                b.vertex(m, s.sx1 * w, s.sy1 * h, 0).uv(s.u1, s.v1).endVertex();
                b.vertex(m, s.sx1 * w, s.sy0 * h, 0).uv(s.u1, s.v0).endVertex();
                b.vertex(m, s.sx0 * w, s.sy0 * h, 0).uv(s.u0, s.v0).endVertex();
                Tesselator.getInstance().end();
                ps.popPose();
            }
            RenderSystem.setShaderColor(1, 1, 1, 1);
        }
        flash(g, w, h, t < BREAK + 4 ? 0.55f * (1 - (t - BREAK) / 4) : 0);
    }

    /** A piece's outline, textured by screen position: the kept frame (GL rows go up: v flipped) or the crack grid. */
    private static void poly(Matrix4f m, float[] p, int w, int h, boolean frame) {
        BufferBuilder b = Tesselator.getInstance().getBuilder();
        b.begin(VertexFormat.Mode.TRIANGLE_FAN, DefaultVertexFormat.POSITION_TEX);
        for (int i = 0; i < p.length; i += 2) b.vertex(m, p[i] * w, p[i + 1] * h, 0).uv(p[i], frame ? 1 - p[i + 1] : p[i + 1]).endVertex();
        Tesselator.getInstance().end();
    }

    // ---------------------------------------------------------------- shards (textures/fx/illusion_wake_shards.json)

    private record Shard(float[] poly, float sx0, float sy0, float sx1, float sy1, float u0, float v0, float u1, float v1, float delay, float vx,
                         float vy, float spin, float tilt) {}

    private record Shards(float ix, float iy, float g, List<Shard> list) {}

    private static Shards shards;
    private static boolean shardsTried;

    private static Shards shards() {
        if (shardsTried) return shards;
        shardsTried = true;
        try {
            var res = Minecraft.getInstance().getResourceManager().getResource(new ResourceLocation(PohCore.MODID, "textures/fx/illusion_wake_shards.json"));
            if (res.isEmpty()) return null;
            JsonObject o;
            try (var in = new InputStreamReader(res.get().open(), StandardCharsets.UTF_8)) {
                o = JsonParser.parseReader(in).getAsJsonObject();
            }
            JsonArray imp = o.getAsJsonArray("impact");
            List<Shard> list = new ArrayList<>();
            for (var el : o.getAsJsonArray("shards")) {
                JsonObject s = el.getAsJsonObject();
                JsonArray pa = s.getAsJsonArray("poly");
                float[] poly = new float[pa.size() * 2];
                for (int i = 0; i < pa.size(); i++) {
                    poly[i * 2] = pa.get(i).getAsJsonArray().get(0).getAsFloat();
                    poly[i * 2 + 1] = pa.get(i).getAsJsonArray().get(1).getAsFloat();
                }
                JsonArray sc = s.getAsJsonArray("screen"), at = s.getAsJsonArray("atlas");
                list.add(new Shard(poly, sc.get(0).getAsFloat(), sc.get(1).getAsFloat(), sc.get(2).getAsFloat(), sc.get(3).getAsFloat(),
                        at.get(0).getAsFloat(), at.get(1).getAsFloat(), at.get(2).getAsFloat(), at.get(3).getAsFloat(), s.get("delay").getAsFloat(),
                        s.get("vx").getAsFloat(), s.get("vy").getAsFloat(), s.get("spin").getAsFloat(), s.get("tilt").getAsFloat()));
            }
            shards = new Shards(imp.get(0).getAsFloat(), imp.get(1).getAsFloat(), o.get("gravity").getAsFloat(), list);
        } catch (Exception ex) {
            PohCore.LOG.warn("[pohsmp] dream shards not loaded: {}", ex.toString());
        }
        return shards;
    }

    // ---------------------------------------------------------------- wound butterflies

    @SubscribeEvent
    public static void onLevel(RenderLevelStageEvent e) {
        if (WOUNDS.isEmpty() || e.getStage() != RenderLevelStageEvent.Stage.AFTER_TRANSLUCENT_BLOCKS) return;
        var lvl = Minecraft.getInstance().level;
        if (lvl == null) return;
        Vec3 cp = e.getCamera().getPosition();
        float pt = e.getPartialTick();
        double t = now() + pt;
        PoseStack ps = e.getPoseStack();
        MultiBufferSource.BufferSource buf = Minecraft.getInstance().renderBuffers().bufferSource();
        VertexConsumer vc = buf.getBuffer(RenderType.entityTranslucent(WOUND));
        for (var en : WOUNDS.entrySet()) {
            Entity ent = lvl.getEntity(en.getKey());
            if (ent == null) continue;
            Vec3 base = ent.getPosition(pt);
            for (int i = 0; i < en.getValue(); i++) {
                double ang = i * 2.3994 + t * (0.05 + 0.006 * (i % 4));
                double rad = 0.55 + 0.12 * (i % 3);
                double y = 0.6 + 1.3 * ((i * 0.618) % 1) + 0.12 * Math.sin(0.13 * t + i);
                int[] seq = {0, 1, 2, 3, 2, 1};
                int frame = seq[(int) Math.floor((t + i * 1.7) / 1.0) % 6];
                ps.pushPose();
                ps.translate(base.x + Math.cos(ang) * rad - cp.x, base.y + y - cp.y, base.z + Math.sin(ang) * rad - cp.z);
                ps.mulPose(e.getCamera().rotation());
                Matrix4f m = ps.last().pose();
                float s = 0.12f, u0 = frame / 4f, u1 = u0 + 0.25f;
                vc.vertex(m, -s, -s, 0).color(1f, 1f, 1f, 0.95f).uv(u1, 1).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(LightTexture.FULL_BRIGHT).normal(0, 0, 1).endVertex();
                vc.vertex(m, s, -s, 0).color(1f, 1f, 1f, 0.95f).uv(u0, 1).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(LightTexture.FULL_BRIGHT).normal(0, 0, 1).endVertex();
                vc.vertex(m, s, s, 0).color(1f, 1f, 1f, 0.95f).uv(u0, 0).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(LightTexture.FULL_BRIGHT).normal(0, 0, 1).endVertex();
                vc.vertex(m, -s, s, 0).color(1f, 1f, 1f, 0.95f).uv(u1, 0).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(LightTexture.FULL_BRIGHT).normal(0, 0, 1).endVertex();
                ps.popPose();
            }
        }
        buf.endBatch(RenderType.entityTranslucent(WOUND));
    }
}
