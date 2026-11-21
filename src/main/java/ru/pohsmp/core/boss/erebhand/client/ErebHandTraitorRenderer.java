package ru.pohsmp.core.boss.erebhand.client;

import com.mojang.authlib.GameProfile;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.player.RemotePlayer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.LivingEntityRenderer;
import net.minecraft.client.renderer.entity.player.PlayerRenderer;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.HumanoidArm;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.erebhand.ErebHandTraitor;

/**
 * «Отражение-предатель» (the visual letter docs/inbox/2026-11-20_mgr_T31_spells2.md): the copy is its original's player model (slim / wide
 * by its skin, through a client-only RemotePlayer with that player's profile — the skin comes from the tab list) in the copy's pose and
 * steps, drawn in glass: 1) the skin, translucent, alpha ≈0.55; 2) over it textures/entity/ereb_hand/traitor_glass.png (the 64×64 skin
 * layout, both layers: pale violet glass, light edges, golden cracks); 3) its glow mask (the cracks shine). In its hand — the weapon it
 * took (the original's main hand). The rest (glints, the burst warning) is the fx ereb_hand_traitor_copy on it.
 */
public class ErebHandTraitorRenderer extends EntityRenderer<ErebHandTraitor> {
    private static final ResourceLocation GLASS = new ResourceLocation(PohCore.MODID, "textures/entity/ereb_hand/traitor_glass.png");
    private static final ResourceLocation GLASS_GLOW = new ResourceLocation(PohCore.MODID, "textures/entity/ereb_hand/traitor_glass_glowmask.png");
    private static final float ALPHA = 0.55f;

    private record Fake(UUID who, RemotePlayer body) {}

    private static final Map<Integer, Fake> FAKES = new HashMap<>();

    public ErebHandTraitorRenderer(EntityRendererProvider.Context ctx) {
        super(ctx);
        shadowRadius = 0.4f;
    }

    private static RemotePlayer fake(ErebHandTraitor c, ClientLevel lvl) {
        Fake f = FAKES.get(c.getId());
        if (f == null || !f.who().equals(c.original()) || f.body().level() != lvl) {
            f = new Fake(c.original(), new RemotePlayer(lvl, new GameProfile(c.original(), c.originalName())));
            FAKES.put(c.getId(), f);
            if (FAKES.size() > 16) FAKES.keySet().removeIf(id -> lvl.getEntity(id) == null);
        }
        RemotePlayer p = f.body();
        p.setPos(c.getX(), c.getY(), c.getZ());
        p.tickCount = c.tickCount;
        return p;
    }

    @Override
    public void render(ErebHandTraitor c, float yaw, float pt, PoseStack ps, MultiBufferSource buf, int light) {
        if (!(c.level() instanceof ClientLevel lvl) || c.original() == null) return;
        RemotePlayer p = fake(c, lvl);
        if (!(entityRenderDispatcher.getRenderer(p) instanceof PlayerRenderer pr)) return;
        PlayerModel<AbstractClientPlayer> m = pr.getModel();
        ResourceLocation skin = p.getSkinTextureLocation();

        float bodyRot = Mth.rotLerp(pt, c.yBodyRotO, c.yBodyRot);
        float headRot = Mth.rotLerp(pt, c.yHeadRotO, c.yHeadRot);
        float pitch = Mth.lerp(pt, c.xRotO, c.getXRot());
        float limb = c.walkAnimation.position(pt), amount = Math.min(1, c.walkAnimation.speed(pt));
        ItemStack hand = c.getMainHandItem();

        ps.pushPose();
        // as LivingEntityRenderer does for a player
        ps.mulPose(Axis.YP.rotationDegrees(180 - bodyRot));
        ps.scale(-1, -1, 1);
        ps.scale(0.9375f, 0.9375f, 0.9375f);
        ps.translate(0, -1.501, 0);
        m.setAllVisible(true);
        m.crouching = false;
        m.young = false;
        m.riding = false;
        m.rightArmPose = hand.isEmpty() ? HumanoidModel.ArmPose.EMPTY : HumanoidModel.ArmPose.ITEM;
        m.leftArmPose = HumanoidModel.ArmPose.EMPTY;
        m.attackTime = c.getAttackAnim(pt);
        m.prepareMobModel(p, limb, amount, pt);
        m.setupAnim(p, limb, amount, c.tickCount + pt, headRot - bodyRot, pitch);
        int overlay = LivingEntityRenderer.getOverlayCoords(c, 0);
        m.renderToBuffer(ps, buf.getBuffer(RenderType.entityTranslucent(skin)), light, overlay, 0.85f, 0.85f, 1f, ALPHA);   // 1) the skin in glass
        m.renderToBuffer(ps, buf.getBuffer(RenderType.entityTranslucent(GLASS)), light, overlay, 1f, 1f, 1f, 0.9f);       // 2) the glass overlay
        m.renderToBuffer(ps, buf.getBuffer(RenderType.eyes(GLASS_GLOW)), light, OverlayTexture.NO_OVERLAY, 1f, 1f, 1f, 1f);   // 3) the cracks shine
        if (!hand.isEmpty()) {   // the weapon, as ItemInHandLayer holds it
            ps.pushPose();
            m.translateToHand(HumanoidArm.RIGHT, ps);
            ps.mulPose(Axis.XP.rotationDegrees(-90));
            ps.mulPose(Axis.YP.rotationDegrees(180));
            ps.translate(1 / 16f, 0.125, -0.625);
            Minecraft.getInstance().getEntityRenderDispatcher().getItemInHandRenderer().renderItem(p, hand, ItemDisplayContext.THIRD_PERSON_RIGHT_HAND,
                    false, ps, buf, light);
            ps.popPose();
        }
        ps.popPose();
        super.render(c, yaw, pt, ps, buf, light);
    }

    @Override
    protected boolean shouldShowName(ErebHandTraitor c) {
        return false;   // a copy, not the player: no name over it
    }

    @Override
    public ResourceLocation getTextureLocation(ErebHandTraitor c) {
        return GLASS;
    }
}
