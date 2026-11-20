package ru.pohsmp.core.boss.martin.client;

import javax.annotation.Nullable;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.martin.MartinBannerEntity;
import ru.pohsmp.core.boss.martin.MartinEntity;
import ru.pohsmp.core.boss.martin.MartinSoldierEntity;
import software.bernie.geckolib.constant.DataTickets;
import software.bernie.geckolib.core.animatable.model.CoreGeoBone;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.core.object.Color;
import software.bernie.geckolib.model.GeoModel;
import software.bernie.geckolib.model.data.EntityModelData;
import software.bernie.geckolib.renderer.GeoEntityRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/**
 * T29 renderers: Martin ×2 (sword and shields are bones; no item layer — it would double the sword), the ghost soldiers
 * (entityTranslucent α0.65 + glow mask), the banner (cutout: the swallowtail is cut by alpha).
 */
public final class MartinRenderers {
    private MartinRenderers() {}

    static ResourceLocation rl(String path) {
        return new ResourceLocation(PohCore.MODID, path);
    }

    public static final ResourceLocation GEO = rl("geo/entity/martin.geo.json"), TEX = rl("textures/entity/martin/martin.png"),
            ANIM = rl("animations/entity/martin.animation.json");

    // ---------------------------------------------------------------- Martin

    static final class Model extends GeoModel<MartinEntity> {
        @Override
        public ResourceLocation getModelResource(MartinEntity e) {
            return GEO;
        }

        @Override
        public ResourceLocation getTextureResource(MartinEntity e) {
            return TEX;
        }

        @Override
        public ResourceLocation getAnimationResource(MartinEntity e) {
            return ANIM;
        }

        /** The head follows the look while no action animation drives it. */
        @Override
        public void setCustomAnimations(MartinEntity e, long id, AnimationState<MartinEntity> s) {
            super.setCustomAnimations(e, id, s);
            if (e.actionPlaying()) return;
            CoreGeoBone head = getAnimationProcessor().getBone("head");
            EntityModelData d = s.getData(DataTickets.ENTITY_MODEL_DATA);
            if (head == null || d == null) return;
            head.setRotX(head.getRotX() + Mth.clamp(d.headPitch(), -30, 30) * Mth.DEG_TO_RAD);
            head.setRotY(head.getRotY() + Mth.clamp(d.netHeadYaw(), -45, 45) * Mth.DEG_TO_RAD);
        }
    }

    public static final class Boss extends GeoEntityRenderer<MartinEntity> {
        public Boss(EntityRendererProvider.Context ctx) {
            super(ctx, new Model());
            withScale(2f);
            shadowRadius = 1.0f;
            addRenderLayer(new AutoGlowingGeoLayer<>(this));
        }

        @Override
        protected float getDeathMaxRotation(MartinEntity e) {
            return 0;
        }
    }

    // ---------------------------------------------------------------- ghost soldier

    public static final class Soldier extends GeoEntityRenderer<MartinSoldierEntity> {
        public Soldier(EntityRendererProvider.Context ctx) {
            super(ctx, new GeoModel<>() {
                @Override
                public ResourceLocation getModelResource(MartinSoldierEntity e) {
                    return rl("geo/entity/martin_soldier.geo.json");
                }

                @Override
                public ResourceLocation getTextureResource(MartinSoldierEntity e) {
                    return rl("textures/entity/martin/martin_soldier.png");
                }

                @Override
                public ResourceLocation getAnimationResource(MartinSoldierEntity e) {
                    return rl("animations/entity/martin_soldier.animation.json");
                }
            });
            shadowRadius = 0.3f;
            shadowStrength = 0.4f;
            addRenderLayer(new AutoGlowingGeoLayer<>(this));
        }

        @Override
        public RenderType getRenderType(MartinSoldierEntity e, ResourceLocation tex, @Nullable MultiBufferSource buf, float pt) {
            return RenderType.entityTranslucent(tex);
        }

        @Override
        public Color getRenderColor(MartinSoldierEntity e, float pt, int light) {
            return Color.ofRGBA(1f, 1f, 1f, e.ghostAlpha(pt));
        }

        @Override
        protected float getDeathMaxRotation(MartinSoldierEntity e) {
            return 0;
        }
    }

    // ---------------------------------------------------------------- banner

    public static final class Banner extends GeoEntityRenderer<MartinBannerEntity> {
        public Banner(EntityRendererProvider.Context ctx) {
            super(ctx, new GeoModel<>() {
                @Override
                public ResourceLocation getModelResource(MartinBannerEntity e) {
                    return rl("geo/entity/martin_banner.geo.json");
                }

                @Override
                public ResourceLocation getTextureResource(MartinBannerEntity e) {
                    return rl("textures/entity/martin/martin_banner.png");
                }

                @Override
                public ResourceLocation getAnimationResource(MartinBannerEntity e) {
                    return rl("animations/entity/martin_banner.animation.json");
                }
            });
            shadowRadius = 0.4f;
        }

        @Override
        public RenderType getRenderType(MartinBannerEntity e, ResourceLocation tex, @Nullable MultiBufferSource buf, float pt) {
            return RenderType.entityCutoutNoCull(tex);
        }

        @Override
        protected float getDeathMaxRotation(MartinBannerEntity e) {
            return 0;
        }
    }
}
