package ru.pohsmp.core.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.Item;
import ru.pohsmp.core.trophy.TrophyArmor;
import ru.pohsmp.core.trophy.TrophyAssets;
import software.bernie.geckolib.animatable.GeoItem;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.model.GeoModel;
import software.bernie.geckolib.renderer.GeoArmorRenderer;

/**
 * T35 GeckoLib renderer of the boss sets and the Cult Heads' mantle / mask - a stub for the visual helpers' files ({@link TrophyAssets}):
 * the model's bones are the standard GeckoLib armor ones (armorHead, armorBody, armorRightArm, armorLeftArm, armorRightLeg,
 * armorLeftLeg, armorRightBoot, armorLeftBoot), each slot shows its own; animations idle / walk / run / cast (cloak and ribbons sway).
 * An optional textures/armor/&lt;id&gt;_glowmask.png is drawn full-bright over the model.
 */
public class TrophyRenderer<T extends Item & GeoItem> extends GeoArmorRenderer<T> {
    private final ResourceLocation glow;
    private Boolean hasGlow;

    public TrophyRenderer(String id) {
        super(new GeoModel<>() {
            @Override
            public ResourceLocation getModelResource(T a) {
                return TrophyAssets.geo(id);
            }

            @Override
            public ResourceLocation getTextureResource(T a) {
                return TrophyAssets.texture(id);
            }

            @Override
            public ResourceLocation getAnimationResource(T a) {
                return TrophyAssets.anim(id);
            }
        });
        this.glow = TrophyAssets.glow(id);
    }

    /** idle / walk / run / cast, as the Silent Witch outfit. */
    public static RawAnimation pick(Entity e) {
        if (!(e instanceof LivingEntity le)) return TrophyArmor.IDLE;
        if (OutfitAnim.casting(le)) return TrophyArmor.CAST;
        if (OutfitAnim.running(le)) return TrophyArmor.RUN;
        if (OutfitAnim.moving(le)) return TrophyArmor.WALK;
        return TrophyArmor.IDLE;
    }

    @Override
    public void actuallyRender(PoseStack poseStack, T animatable, BakedGeoModel model, RenderType renderType, MultiBufferSource bufferSource,
                               VertexConsumer buffer, boolean isReRender, float partialTick, int packedLight, int packedOverlay,
                               float red, float green, float blue, float alpha) {
        super.actuallyRender(poseStack, animatable, model, renderType, bufferSource, buffer, isReRender, partialTick, packedLight, packedOverlay,
                red, green, blue, alpha);
        if (isReRender || bufferSource == null) return;
        if (hasGlow == null) hasGlow = Minecraft.getInstance().getResourceManager().getResource(glow).isPresent();
        if (!hasGlow) return;
        RenderType g = GlowType.of(glow);
        super.actuallyRender(poseStack, animatable, model, g, bufferSource, bufferSource.getBuffer(g), true, partialTick,
                LightTexture.FULL_BRIGHT, OverlayTexture.NO_OVERLAY, 1f, 1f, 1f, 1f);
    }
}
