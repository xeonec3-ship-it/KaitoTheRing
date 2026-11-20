package ru.pohsmp.core.boss.erebhand.client;

import com.mojang.authlib.GameProfile;
import com.mojang.blaze3d.vertex.PoseStack;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.player.RemotePlayer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
import ru.pohsmp.core.boss.erebhand.ErebHandTraitor;

/**
 * «Отражение-предатель»: the copy is drawn as its original — a client-only RemotePlayer with that player's profile (its skin and name
 * from the tab list), the copy's pose and steps, the weapon it took — with glass glints over it. Not added to the level. (A true glass
 * tint needs the visual assistant's fx ereb_hand_traitor_reflection over it; till then: glints.)
 */
public class ErebHandTraitorRenderer extends EntityRenderer<ErebHandTraitor> {
    private record Fake(UUID who, RemotePlayer body) {}

    private static final Map<Integer, Fake> FAKES = new HashMap<>();

    public ErebHandTraitorRenderer(EntityRendererProvider.Context ctx) {
        super(ctx);
        shadowRadius = 0.4f;
    }

    @Override
    public void render(ErebHandTraitor c, float yaw, float pt, PoseStack ps, MultiBufferSource buf, int light) {
        if (!(c.level() instanceof ClientLevel lvl) || c.original() == null) return;
        Fake f = FAKES.get(c.getId());
        if (f == null || !f.who().equals(c.original()) || f.body().level() != lvl) {
            f = new Fake(c.original(), new RemotePlayer(lvl, new GameProfile(c.original(), c.originalName())));
            FAKES.put(c.getId(), f);
            if (FAKES.size() > 16) FAKES.keySet().removeIf(id -> lvl.getEntity(id) == null);
        }
        RemotePlayer p = f.body();
        p.setPos(c.getX(), c.getY(), c.getZ());
        p.xo = c.xo;
        p.yo = c.yo;
        p.zo = c.zo;
        p.xOld = c.xOld;
        p.yOld = c.yOld;
        p.zOld = c.zOld;
        p.setYRot(c.getYRot());
        p.yRotO = c.yRotO;
        p.setXRot(c.getXRot());
        p.xRotO = c.xRotO;
        p.yBodyRot = c.yBodyRot;
        p.yBodyRotO = c.yBodyRotO;
        p.yHeadRot = c.yHeadRot;
        p.yHeadRotO = c.yHeadRotO;
        p.tickCount = c.tickCount;
        p.hurtTime = c.hurtTime;
        p.attackAnim = c.attackAnim;
        p.oAttackAnim = c.oAttackAnim;
        p.swinging = c.swinging;
        p.walkAnimation.setSpeed(c.walkAnimation.speed());
        float d = c.walkAnimation.position() - p.walkAnimation.position();
        if (d > 0) p.walkAnimation.update(d, 1f);
        ItemStack hand = c.getMainHandItem();
        if (!ItemStack.matches(hand, p.getMainHandItem())) p.setItemSlot(EquipmentSlot.MAINHAND, hand.copy());
        Minecraft.getInstance().getEntityRenderDispatcher().getRenderer(p).render(p, Mth.lerp(pt, c.yRotO, c.getYRot()), pt, ps, buf, light);
        if (c.tickCount % 3 == 0 && !Minecraft.getInstance().isPaused())   // glass glints over it
            lvl.addParticle(ParticleTypes.END_ROD, c.getX() + (c.getRandom().nextDouble() - 0.5) * 0.6, c.getY() + c.getRandom().nextDouble() * 1.8,
                    c.getZ() + (c.getRandom().nextDouble() - 0.5) * 0.6, 0, 0.01, 0);
    }

    @Override
    public ResourceLocation getTextureLocation(ErebHandTraitor c) {
        return ErebHandShardRenderer.skin(c.original());
    }
}
