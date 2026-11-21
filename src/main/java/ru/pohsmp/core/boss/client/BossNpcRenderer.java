package ru.pohsmp.core.boss.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import java.util.HashMap;
import java.util.Map;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import ru.pohsmp.core.PohCore;
import ru.pohsmp.core.boss.BossNpc;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.model.GeoModel;
import software.bernie.geckolib.renderer.GeoEntityRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/**
 * The peaceful NPC after a surrender, drawn with the boss's own model. Default look of boss <id>: geo/entity/<id>.geo.json,
 * textures/entity/<id>/<id>_npc.png (falls back to <id>.png only if a look says so), animations/entity/<id>.animation.json, scale 1;
 * a boss registers its own with {@link #look} (texture of its NPC state — e.g. aris_dim — and its render scale).
 */
public class BossNpcRenderer extends GeoEntityRenderer<BossNpc> {
    public record Look(ResourceLocation model, ResourceLocation texture, ResourceLocation animation, float scale) {}

    private static final Map<String, Look> LOOKS = new HashMap<>();

    public static void look(String bossId, Look l) {
        LOOKS.put(bossId, l);
    }

    static Look lookOf(String bossId) {
        return LOOKS.computeIfAbsent(bossId, id -> new Look(new ResourceLocation(PohCore.MODID, "geo/entity/" + id + ".geo.json"),
                new ResourceLocation(PohCore.MODID, "textures/entity/" + id + "/" + id + "_npc.png"),
                new ResourceLocation(PohCore.MODID, "animations/entity/" + id + ".animation.json"), 1f));
    }

    public BossNpcRenderer(EntityRendererProvider.Context ctx) {
        super(ctx, new GeoModel<>() {
            @Override
            public ResourceLocation getModelResource(BossNpc e) {
                return lookOf(e.bossId).model();
            }

            @Override
            public ResourceLocation getTextureResource(BossNpc e) {
                return lookOf(e.bossId).texture();
            }

            @Override
            public ResourceLocation getAnimationResource(BossNpc e) {
                return lookOf(e.bossId).animation();
            }
        });
        addRenderLayer(new AutoGlowingGeoLayer<>(this));
        shadowRadius = 0.6f;
    }

    @Override
    public void preRender(PoseStack ps, BossNpc e, BakedGeoModel model, MultiBufferSource buf, VertexConsumer vc, boolean reRender, float pt,
                          int light, int overlay, float r, float g, float b, float a) {
        super.preRender(ps, e, model, buf, vc, reRender, pt, light, overlay, r, g, b, a);
        float s = lookOf(e.bossId).scale();
        if (s != 1 && !reRender) ps.scale(s, s, s);   // the glow mask layer re-renders through preRender: scale once (Martin's x2)
    }
}
