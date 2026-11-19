package ru.pohsmp.core.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.world.item.ItemDisplayContext;
import ru.pohsmp.core.AnimatedStaff;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.cache.object.GeoCube;
import software.bernie.geckolib.cache.object.GeoQuad;
import software.bernie.geckolib.cache.object.GeoVertex;
import software.bernie.geckolib.model.GeoModel;
import software.bernie.geckolib.renderer.GeoItemRenderer;

/**
 * GeckoLib staff renderer: in the hand (first and third person, both hands) every staff is held by the middle of its model,
 * not near the butt (owner, 19.11.2026). The middle is taken from the model's own height, so any staff, present or future,
 * is gripped the same way without touching its item JSON.
 */
public class StaffRenderer extends GeoItemRenderer<AnimatedStaff> {
    /** Item JSONs lift every staff by 2 px in the hand (translation y = 2); the centring adds to that. */
    private static final double JSON_LIFT = 2 / 16.0;

    private BakedGeoModel measured;
    private double middle;

    public StaffRenderer(GeoModel<AnimatedStaff> model) {
        super(model);
    }

    @Override
    public void preRender(PoseStack poseStack, AnimatedStaff animatable, BakedGeoModel model, MultiBufferSource bufferSource, VertexConsumer buffer,
                          boolean isReRender, float partialTick, int packedLight, int packedOverlay, float red, float green, float blue, float alpha) {
        super.preRender(poseStack, animatable, model, bufferSource, buffer, isReRender, partialTick, packedLight, packedOverlay, red, green, blue, alpha);
        if (!isReRender && inHand(renderPerspective)) poseStack.translate(0, -(middle(model) + JSON_LIFT), 0);
    }

    private static boolean inHand(ItemDisplayContext c) {
        return c == ItemDisplayContext.THIRD_PERSON_RIGHT_HAND || c == ItemDisplayContext.THIRD_PERSON_LEFT_HAND
                || c == ItemDisplayContext.FIRST_PERSON_RIGHT_HAND || c == ItemDisplayContext.FIRST_PERSON_LEFT_HAND;
    }

    /** Middle of the model's height in blocks (the model origin is at the hand). */
    private double middle(BakedGeoModel model) {
        if (model == measured) return middle;
        float[] mm = {Float.MAX_VALUE, -Float.MAX_VALUE};
        for (GeoBone b : model.topLevelBones()) bounds(b, mm);
        double lo = mm[0], hi = mm[1];
        if (lo > hi) lo = hi = 0;
        double m = (lo + hi) / 2;
        if (hi - lo > 8) m /= 16;   // vertex positions in pixels rather than blocks
        measured = model;
        middle = m;
        return m;
    }

    private static void bounds(GeoBone b, float[] mm) {
        for (GeoCube c : b.getCubes())
            for (GeoQuad q : c.quads()) {
                if (q == null) continue;
                for (GeoVertex v : q.vertices()) {
                    float y = v.position().y();
                    if (y < mm[0]) mm[0] = y;
                    if (y > mm[1]) mm[1] = y;
                }
            }
        for (GeoBone ch : b.getChildBones()) bounds(ch, mm);
    }
}
