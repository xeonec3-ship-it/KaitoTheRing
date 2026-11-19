package ru.pohsmp.core.client;

import com.mojang.blaze3d.vertex.DefaultVertexFormat;
import com.mojang.blaze3d.vertex.VertexFormat;
import java.util.HashMap;
import java.util.Map;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;

/**
 * Glow mask pass for GeckoLib armor: the mask's opaque texels (alpha cutout) drawn full-bright over the model, pulled slightly toward
 * the camera so they win the depth test whichever batch is flushed first. No back-face culling: GeckoLib armor is drawn mirrored.
 * (Additive "eyes" types did not work here: their batch was flushed before the armor's own and got painted over.)
 */
public final class GlowType extends RenderType {
    private static final Map<ResourceLocation, RenderType> CACHE = new HashMap<>();

    private GlowType(String n, VertexFormat f, VertexFormat.Mode m, int b, boolean c, boolean s, Runnable a, Runnable z) {
        super(n, f, m, b, c, s, a, z);
    }

    public static RenderType of(ResourceLocation tex) {
        return CACHE.computeIfAbsent(tex, t -> create("pohsmp_glowmask", DefaultVertexFormat.NEW_ENTITY, VertexFormat.Mode.QUADS, 256, true, false,
                CompositeState.builder()
                        .setShaderState(RENDERTYPE_ARMOR_CUTOUT_NO_CULL_SHADER)
                        .setTextureState(new TextureStateShard(t, false, false))
                        .setTransparencyState(NO_TRANSPARENCY)
                        .setCullState(NO_CULL)
                        .setLightmapState(LIGHTMAP)
                        .setOverlayState(OVERLAY)
                        .setLayeringState(VIEW_OFFSET_Z_LAYERING)
                        .createCompositeState(true)));
    }
}
