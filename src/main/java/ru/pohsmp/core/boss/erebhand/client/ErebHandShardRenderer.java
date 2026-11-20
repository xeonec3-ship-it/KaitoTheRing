package ru.pohsmp.core.boss.erebhand.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.PlayerInfo;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.client.resources.DefaultPlayerSkin;
import net.minecraft.resources.ResourceLocation;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import ru.pohsmp.core.boss.erebhand.ErebHandShard;

/**
 * «Падение маски»: a shard of the mask. Its glass and golden frame are the fx ereb_hand_mask_shard (attached to it); this draws what the
 * fx engine's player_face slot would — the face of the player it belongs to (its skin's face and hat layer, from the tab list) on a
 * small quad turned to the camera — and that player's name over it (the entity's custom name).
 */
public class ErebHandShardRenderer extends EntityRenderer<ErebHandShard> {
    /** The face's half size (blocks) and its height in the shard's 0.8 box. */
    private static final float HALF = 0.22f, MID = 0.4f;

    public ErebHandShardRenderer(EntityRendererProvider.Context ctx) {
        super(ctx);
        shadowRadius = 0;
    }

    static ResourceLocation skin(UUID id) {
        var conn = Minecraft.getInstance().getConnection();
        PlayerInfo info = conn == null || id == null ? null : conn.getPlayerInfo(id);
        return info != null ? info.getSkinLocation() : DefaultPlayerSkin.getDefaultSkin(id == null ? new UUID(0, 0) : id);
    }

    @Override
    public void render(ErebHandShard e, float yaw, float pt, PoseStack ps, MultiBufferSource buf, int light) {
        ResourceLocation skin = skin(e.owner());
        ps.pushPose();
        ps.translate(0, MID, 0);
        ps.mulPose(entityRenderDispatcher.cameraOrientation());
        VertexConsumer vc = buf.getBuffer(RenderType.entityTranslucent(skin));
        Matrix4f m = ps.last().pose();
        Matrix3f n = ps.last().normal();
        int bright = 0xF000F0;   // a reflection in glass: lit evenly
        quad(vc, m, n, HALF, 8, 8, bright, 0);          // the face
        quad(vc, m, n, HALF * 1.12f, 40, 8, bright, -0.01f);   // the hat layer just in front
        ps.popPose();
        super.render(e, yaw, pt, ps, buf, light);   // the name over it
    }

    /** A square of the skin's 8×8 cell at (u,v) px (64×64 skin). */
    private static void quad(VertexConsumer vc, Matrix4f m, Matrix3f n, float h, int u, int v, int light, float z) {
        float u0 = u / 64f, u1 = (u + 8) / 64f, v0 = v / 64f, v1 = (v + 8) / 64f;
        vertex(vc, m, n, -h, -h, z, u1, v1, light);
        vertex(vc, m, n, h, -h, z, u0, v1, light);
        vertex(vc, m, n, h, h, z, u0, v0, light);
        vertex(vc, m, n, -h, h, z, u1, v0, light);
    }

    private static void vertex(VertexConsumer vc, Matrix4f m, Matrix3f n, float x, float y, float z, float u, float v, int light) {
        vc.vertex(m, x, y, z).color(255, 255, 255, 235).uv(u, v).overlayCoords(OverlayTexture.NO_OVERLAY).uv2(light).normal(n, 0, 1, 0).endVertex();
    }

    @Override
    public ResourceLocation getTextureLocation(ErebHandShard e) {
        return skin(e.owner());
    }
}
