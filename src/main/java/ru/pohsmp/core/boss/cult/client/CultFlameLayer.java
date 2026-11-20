package ru.pohsmp.core.boss.cult.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.mojang.math.Axis;
import io.redspace.ironsspellbooks.entity.mobs.abstract_spell_casting_mob.AbstractSpellCastingMob;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import org.joml.Matrix4f;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.BossNet;
import ru.pohsmp.core.boss.client.BossClient;
import ru.pohsmp.core.boss.cult.CultLeaderEntity;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoEntityRenderer;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;
import software.bernie.geckolib.util.RenderUtils;

/**
 * The head flame of the soul form (Iron's FireBossFlameLayer with our cult_leader_flame.png: 64×512, 8 frames, the same UV per frame).
 * Goes out at 2.6 s of the death scene (BossNet.LOOK_FLAME_OUT).
 */
public class CultFlameLayer extends GeoRenderLayer<AbstractSpellCastingMob> {
    private static final ResourceLocation TEXTURE = new ResourceLocation(PohCore.MODID, "textures/entity/cult_leader/cult_leader_flame.png");
    private static final int FRAMES = 8;

    public CultFlameLayer(GeoEntityRenderer<AbstractSpellCastingMob> r) {
        super(r);
    }

    @Override
    public void renderForBone(PoseStack ps, AbstractSpellCastingMob e, GeoBone bone, RenderType rt, MultiBufferSource buf, VertexConsumer vc,
                              float pt, int light, int overlay) {
        if (!bone.getName().equals("head") || !(e instanceof CultLeaderEntity b) || !b.isSoulMode()) return;
        if (BossClient.look(b.getId(), BossNet.LOOK_FLAME_OUT) || BossClient.look(b.getId(), BossNet.LOOK_HIDDEN)) return;
        ps.pushPose();
        ps.mulPose(Axis.YP.rotationDegrees(45));
        RenderUtils.translateToPivotPoint(ps, bone);
        ps.scale(0.5f, 0.5f, 0.5f);
        VertexConsumer c = buf.getBuffer(RenderType.entityCutout(TEXTURE));
        Matrix4f m = ps.last().pose();
        int frame = e.tickCount % FRAMES;
        float v0 = frame / (float) FRAMES, v1 = (frame + 1) / (float) FRAMES, h = 0.7071f;
        for (int i = 0; i < 4; i++) {
            ps.mulPose(Axis.YP.rotationDegrees(90));
            c.vertex(m, 0, 0, -h).color(255, 255, 255, 255).uv(0, v1).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(0xF000F0).normal(0, 1, 0).endVertex();
            c.vertex(m, 0, 1, -h).color(255, 255, 255, 255).uv(0, v0).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(0xF000F0).normal(0, 1, 0).endVertex();
            c.vertex(m, 0, 1, h).color(255, 255, 255, 255).uv(1, v0).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(0xF000F0).normal(0, 1, 0).endVertex();
            c.vertex(m, 0, 0, h).color(255, 255, 255, 255).uv(1, v1).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(0xF000F0).normal(0, 1, 0).endVertex();
        }
        ps.popPose();
        buf.getBuffer(rt);
    }
}
