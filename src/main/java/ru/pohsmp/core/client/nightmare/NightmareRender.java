package ru.pohsmp.core.client.nightmare;

import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.SkeletonModel;
import net.minecraft.client.model.geom.ModelLayers;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.HumanoidMobRenderer;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.client.event.EntityRenderersEvent;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.nightmare.Bestiary;
import ru.pohsmp.core.nightmare.NightmareMob;

/**
 * T25: the nightmares on the clients that get them at all (only the immersed). Until the helper's models come, each is a black
 * wither-skeleton body at its own size; textures/entity/nightmare/<id>.png takes the place of the skeleton's skin when it exists.
 */
public final class NightmareRender {
    private NightmareRender() {}

    private static final ResourceLocation FALLBACK = new ResourceLocation("minecraft", "textures/entity/skeleton/wither_skeleton.png");

    public static void register(EntityRenderersEvent.RegisterRenderers e) {
        for (var t : Bestiary.TYPES.values()) e.registerEntityRenderer(t.get(), Stub::new);
    }

    static final class Stub extends HumanoidMobRenderer<NightmareMob, SkeletonModel<NightmareMob>> {
        Stub(EntityRendererProvider.Context ctx) {
            super(ctx, new SkeletonModel<>(ctx.bakeLayer(ModelLayers.WITHER_SKELETON)), 0f);
        }

        @Override
        protected void scale(NightmareMob m, PoseStack ps, float pt) {
            ps.scale(m.kind.scale, m.kind.scale, m.kind.scale);
        }

        @Override
        public ResourceLocation getTextureLocation(NightmareMob m) {
            return TEX.computeIfAbsent(m.kind, k -> {
                ResourceLocation own = new ResourceLocation(PohCore.MODID, "textures/entity/nightmare/" + k.id + ".png");
                return Minecraft.getInstance().getResourceManager().getResource(own).isPresent() ? own : FALLBACK;
            });
        }

        private static final java.util.Map<NightmareMob.Kind, ResourceLocation> TEX = new java.util.EnumMap<>(NightmareMob.Kind.class);
    }
}
