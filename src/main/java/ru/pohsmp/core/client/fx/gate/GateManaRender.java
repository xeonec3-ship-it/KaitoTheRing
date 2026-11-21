package ru.pohsmp.core.client.fx.gate;

import com.mojang.blaze3d.platform.GlStateManager;
import com.mojang.blaze3d.platform.NativeImage;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.blaze3d.vertex.BufferBuilder;
import com.mojang.blaze3d.vertex.BufferUploader;
import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.mojang.blaze3d.vertex.Tesselator;
import com.mojang.blaze3d.vertex.VertexFormat;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.GameRenderer;
import net.minecraft.client.renderer.texture.DynamicTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import org.joml.Matrix4f;
import ru.pohsmp.core.client.GateOrder;
import ru.pohsmp.core.client.GateStaff;

/**
 * Draws the mana of «Безмолвные врата» ({@link GateMana}, ported from God Wand) for every running Gate scene (client/GateStaff knows
 * them: CUT packet of Cutscene SILENT_GATE, until its STOP), for everyone who sees the caster. Additive, no depth write, after particles.
 * The atlas ({@link GateAtlasGen}) is built on a background thread at the first scene and uploaded once ready (no freeze on the render thread).
 */
public final class GateManaRender {
    private GateManaRender() {}

    private static final ResourceLocation TEXTURE = new ResourceLocation("pohsmp_core", "dynamic/gate_mana_glow");
    private static CompletableFuture<byte[]> pending;
    private static boolean uploaded;

    /** True once the glow atlas is on the GPU; starts building it otherwise. */
    private static boolean atlas() {
        if (uploaded) return true;
        if (pending == null) pending = CompletableFuture.supplyAsync(GateAtlasGen::alpha);
        if (!pending.isDone()) return false;
        byte[] a = pending.join();
        // The glow copy of the atlas: opaque, grey = alpha (the vertices are premultiplied, see GateDraw).
        NativeImage img = new NativeImage(GateAtlasGen.W, GateAtlasGen.H, false);
        for (int y = 0; y < GateAtlasGen.H; y++) for (int x = 0; x < GateAtlasGen.W; x++) {
            int g = a[y * GateAtlasGen.W + x] & 255;
            img.setPixelRGBA(x, y, 0xFF000000 | g << 16 | g << 8 | g);
        }
        DynamicTexture tex = new DynamicTexture(img);
        tex.setFilter(true, false);
        Minecraft.getInstance().getTextureManager().register(TEXTURE, tex);
        uploaded = true;
        return true;
    }

    @SubscribeEvent
    public static void onRender(RenderLevelStageEvent e) {
        if (e.getStage() != RenderLevelStageEvent.Stage.AFTER_PARTICLES) return;
        List<GateStaff.GateRun> runs = GateStaff.gateRuns();
        if (runs.isEmpty()) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || !atlas()) return;
        float pt = e.getPartialTick();
        double now = ru.pohsmp.core.client.ClientClock.now(pt);
        Vec3 eye = e.getCamera().getPosition();
        Matrix4f m = e.getPoseStack().last().pose();

        RenderSystem.enableBlend();
        RenderSystem.blendFunc(GlStateManager.SourceFactor.SRC_ALPHA, GlStateManager.DestFactor.ONE);
        RenderSystem.enableDepthTest();
        RenderSystem.depthMask(false);
        RenderSystem.disableCull();
        RenderSystem.setShader(GameRenderer::getPositionTexColorShader);
        RenderSystem.setShaderTexture(0, TEXTURE);
        try {
            for (GateStaff.GateRun r : runs) {
                if (!(mc.level.getEntity(r.caster()) instanceof LivingEntity le) || !le.isAlive()) continue;
                long cmd = GateOrder.commandAt(r.key());
                GateMana.Frame f = new GateMana.Frame(now - r.start(), cmd < 0 ? -1 : Math.max(0, now - cmd));
                Vec3 feet = le.getPosition(pt);
                double yaw = Mth.rotLerp(pt, le.yBodyRotO, le.yBodyRot);
                BufferBuilder b = Tesselator.getInstance().getBuilder();
                b.begin(VertexFormat.Mode.QUADS, DefaultVertexFormat.POSITION_TEX_COLOR);
                GateDraw.Ctx c = new GateDraw.Ctx();
                c.eye = eye;
                // POSITION_TEX_COLOR: the elements must be written in this order (position, uv, colour).
                c.v = (x, y, z, u, v, rr, gg, bb, aa) -> b.vertex(m, x, y, z).uv(u, v).color(rr, gg, bb, aa).endVertex();
                GateMana.emit(c, f, feet, yaw);
                BufferUploader.drawWithShader(b.end());
            }
        } finally {
            RenderSystem.depthMask(true);
            RenderSystem.enableCull();
            RenderSystem.defaultBlendFunc();
            RenderSystem.disableBlend();
        }
    }
}
