package ru.pohsmp.core.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.silent.SilentWitch;
import ru.pohsmp.core.silent.SilentWitchArmor;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.model.GeoModel;
import software.bernie.geckolib.renderer.GeoArmorRenderer;

/**
 * GeckoLib armor renderer of the Silent Witch outfit: one model for the three pieces (geo/armor/silent_witch_outfit.geo.json),
 * cat bone "nero" shown only in the full set and not while running (effect 9), and the gold trim glowing at night (effect 8):
 * textures/armor/silent_witch_outfit_glowmask.png drawn full-bright at night, stronger the darker it is.
 */
public class SilentWitchRenderer extends GeoArmorRenderer<SilentWitchArmor> {
    public static final ResourceLocation GEO = new ResourceLocation(PohCore.MODID, "geo/armor/silent_witch_outfit.geo.json");
    public static final ResourceLocation TEXTURE = new ResourceLocation(PohCore.MODID, "textures/armor/silent_witch_outfit.png");
    public static final ResourceLocation GLOW = new ResourceLocation(PohCore.MODID, "textures/armor/silent_witch_outfit_glowmask.png");
    public static final ResourceLocation ANIM = new ResourceLocation(PohCore.MODID, "animations/armor/silent_witch_outfit.animation.json");

    public SilentWitchRenderer() {
        super(new GeoModel<>() {
            @Override
            public ResourceLocation getModelResource(SilentWitchArmor a) {
                return GEO;
            }

            @Override
            public ResourceLocation getTextureResource(SilentWitchArmor a) {
                return TEXTURE;
            }

            @Override
            public ResourceLocation getAnimationResource(SilentWitchArmor a) {
                return ANIM;
            }
        });
    }

    @Override
    public void preRender(PoseStack poseStack, SilentWitchArmor animatable, BakedGeoModel model, MultiBufferSource bufferSource, VertexConsumer buffer,
                          boolean isReRender, float partialTick, int packedLight, int packedOverlay, float red, float green, float blue, float alpha) {
        super.preRender(poseStack, animatable, model, bufferSource, buffer, isReRender, partialTick, packedLight, packedOverlay, red, green, blue, alpha);
        model.getBone("nero").ifPresent(b -> b.setHidden(!(currentEntity instanceof LivingEntity le && SilentWitch.fullSet(le) && OutfitAnim.neroHere(le))));
    }

    /** 0 by day, up to 0.85 at midnight; smooth through dusk and dawn. */
    public static float nightGlow(Level level, float partialTick) {
        if (level == null) return 0;
        if (!level.dimensionType().hasSkyLight()) return 0.6f;
        float angle = level.getTimeOfDay(partialTick);   // 0 = noon, 0.5 = midnight
        float c = Mth.cos(angle * Mth.TWO_PI);           // 1 noon, -1 midnight
        return Mth.clamp(0.15f - c * 0.9f, 0f, 0.85f);
    }

    /**
     * Second pass over the same pose (effect 8): the gold trim from the glow mask, full-bright and as strong as the night is dark
     * (see {@link GlowType}); skipped by day.
     */
    @Override
    public void actuallyRender(PoseStack poseStack, SilentWitchArmor animatable, BakedGeoModel model, RenderType renderType, MultiBufferSource bufferSource,
                               VertexConsumer buffer, boolean isReRender, float partialTick, int packedLight, int packedOverlay,
                               float red, float green, float blue, float alpha) {
        super.actuallyRender(poseStack, animatable, model, renderType, bufferSource, buffer, isReRender, partialTick, packedLight, packedOverlay,
                red, green, blue, alpha);
        if (isReRender || bufferSource == null) return;
        float g = nightGlow(currentEntity == null ? null : currentEntity.level(), partialTick);
        if (g <= 0.01f) return;
        RenderType glow = GlowType.of(GLOW);
        float c = 0.55f + 0.45f * g / 0.85f;   // never darker than the trim lit by the dusk sky
        super.actuallyRender(poseStack, animatable, model, glow, bufferSource, bufferSource.getBuffer(glow), true, partialTick,
                LightTexture.FULL_BRIGHT, OverlayTexture.NO_OVERLAY, c, c, c, 1f);
    }
}
