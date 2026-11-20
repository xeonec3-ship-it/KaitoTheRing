package ru.pohsmp.core.boss.erebhand.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.Mth;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.erebhand.ErebHandGiant;
import software.bernie.geckolib.model.GeoModel;
import software.bernie.geckolib.renderer.GeoEntityRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/**
 * The giant hand: geo/entity/ereb_hand_giant.geo.json (only the ghost_* bones of the model, the wrist at the origin), the model's own
 * texture ereb_hand.png and its glow mask, animations/entity/ereb_hand_giant.animation.json; ×scale of the entity (5 for «Длань Лжи»),
 * turned by the entity's yaw (GeckoLib turns only living entities), translucent glass.
 */
public class ErebHandGiantRenderer extends GeoEntityRenderer<ErebHandGiant> {
    private static final ResourceLocation MODEL = new ResourceLocation(PohCore.MODID, "geo/entity/ereb_hand_giant.geo.json");
    private static final ResourceLocation TEXTURE = new ResourceLocation(PohCore.MODID, "textures/entity/ereb_hand/ereb_hand.png");
    private static final ResourceLocation ANIMATIONS = new ResourceLocation(PohCore.MODID, "animations/entity/ereb_hand_giant.animation.json");

    public ErebHandGiantRenderer(EntityRendererProvider.Context ctx) {
        super(ctx, new GeoModel<>() {
            @Override
            public ResourceLocation getModelResource(ErebHandGiant e) {
                return MODEL;
            }

            @Override
            public ResourceLocation getTextureResource(ErebHandGiant e) {
                return TEXTURE;
            }

            @Override
            public ResourceLocation getAnimationResource(ErebHandGiant e) {
                return ANIMATIONS;
            }
        });
        shadowRadius = 0;
        addRenderLayer(new AutoGlowingGeoLayer<>(this));
    }

    @Override
    public void render(ErebHandGiant e, float yaw, float pt, PoseStack ps, MultiBufferSource buf, int light) {
        ps.pushPose();
        // GeckoLib turns a non-living entity by 180° only: undo it and turn by its own yaw, as a living one would be
        ps.mulPose(Axis.YP.rotationDegrees(-Mth.rotLerp(pt, e.yRotO, e.getYRot())));
        float s = e.scale();
        ps.scale(s, s, s);
        super.render(e, yaw, pt, ps, buf, light);
        ps.popPose();
    }

    @Override
    public RenderType getRenderType(ErebHandGiant e, ResourceLocation texture, MultiBufferSource buf, float pt) {
        return RenderType.entityTranslucent(texture);
    }
}
