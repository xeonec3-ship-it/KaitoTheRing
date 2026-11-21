package ru.pohsmp.core.boss.aris.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.aris.ArisEntity;
import ru.pohsmp.core.boss.aris.ArisMath;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.core.animatable.model.CoreGeoBone;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.model.DefaultedEntityGeoModel;
import software.bernie.geckolib.renderer.GeoEntityRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/**
 * Aris: her own GeckoLib model (geo/entity/aris.geo.json, animation.aris.*), scale 1.0 (the fx heights are made for it), the glow
 * masks of the four textures (horns, trim, eyes: the texture is chosen by the synced state, the glow mask follows its name). The
 * dropped hammer (bone hammer_ground) is hidden except in the surrender, as the visual letter asks.
 */
public class ArisRenderer extends GeoEntityRenderer<ArisEntity> {
    public ArisRenderer(EntityRendererProvider.Context ctx) {
        super(ctx, new Model());
        addRenderLayer(new AutoGlowingGeoLayer<>(this) {
            @Override
            public void render(PoseStack pose, ArisEntity e, BakedGeoModel model, RenderType type, MultiBufferSource buf,
                               VertexConsumer vc, float pt, int light, int overlay) {
                // aris_spent: eyes and horns are out, its glow mask is empty and GeckoLib crashes on an empty mask
                if ("aris_spent".equals(ArisMath.texture(e.tex()))) return;
                super.render(pose, e, model, type, buf, vc, pt, light, overlay);
            }
        });
        shadowRadius = 0.7f;
    }

    static ResourceLocation texture(int state) {
        String n = ArisMath.texture(state);
        return new ResourceLocation(PohCore.MODID, "textures/entity/aris/" + n + ".png");
    }

    static final class Model extends DefaultedEntityGeoModel<ArisEntity> {
        Model() {
            super(new ResourceLocation(PohCore.MODID, "aris"));
        }

        @Override
        public ResourceLocation getTextureResource(ArisEntity e) {
            return texture(e.tex());
        }

        @Override
        public void setCustomAnimations(ArisEntity e, long instanceId, AnimationState<ArisEntity> state) {
            super.setCustomAnimations(e, instanceId, state);
            CoreGeoBone g = getAnimationProcessor().getBone("hammer_ground");
            if (g != null) g.setHidden(!e.hammerOnGround());
        }
    }
}
