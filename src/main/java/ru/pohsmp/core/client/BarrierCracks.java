package ru.pohsmp.core.client;

import com.mojang.blaze3d.platform.NativeImage;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.texture.DynamicTexture;
import net.minecraft.resources.ResourceLocation;
import ru.pohsmp.core.PohCore;

/**
 * Frames of textures/fx/barrier_cracks.png (manager 19.11, tools/gen_barrier_cracks.py) for the cracks on the Closing of Space dome
 * when the Milky Way presses on it. The PNG keeps the brightness in ALPHA and the distance from the centre in G (0 centre .. 255 edge).
 * The dome is drawn additively without shaders, so the "only pixels with G below the threshold" cut is baked here into FRAMES textures,
 * frame f showing the cracks out to (f + 1) / FRAMES of the radius; RGB = brightness, white (tinted with the dome's colour when drawn).
 */
public final class BarrierCracks {
    private BarrierCracks() {}

    public static final int FRAMES = 16;
    private static final ResourceLocation SRC = new ResourceLocation(PohCore.MODID, "textures/fx/barrier_cracks.png");
    private static ResourceLocation[] frames;
    private static boolean failed;

    /** Names of the frames for the render types (the textures themselves are made on first use). */
    public static ResourceLocation frameName(int f) {
        return new ResourceLocation(PohCore.MODID, "dyn/barrier_cracks_" + f);
    }

    /** The frame for the threshold k (0..1 of the radius), or null before the frames could be made. */
    public static ResourceLocation frame(double k) {
        if (frames == null && !failed) build();
        if (frames == null) return null;
        int f = (int) Math.round(Math.max(0, Math.min(1, k)) * FRAMES) - 1;
        return f < 0 ? null : frames[Math.min(FRAMES - 1, f)];
    }

    private static void build() {
        Minecraft mc = Minecraft.getInstance();
        try (var in = mc.getResourceManager().open(SRC); NativeImage src = NativeImage.read(in)) {
            int w = src.getWidth(), h = src.getHeight();
            ResourceLocation[] out = new ResourceLocation[FRAMES];
            for (int f = 0; f < FRAMES; f++) {
                int cut = (int) Math.round(255.0 * (f + 1) / FRAMES);
                NativeImage img = new NativeImage(w, h, false);
                for (int y = 0; y < h; y++)
                    for (int x = 0; x < w; x++) {
                        int p = src.getPixelRGBA(x, y);   // ABGR
                        int a = (p >>> 24) & 255, g = (p >>> 8) & 255;
                        int v = g <= cut ? a : 0;
                        img.setPixelRGBA(x, y, 0xFF000000 | (v << 16) | (v << 8) | v);
                    }
                out[f] = frameName(f);
                mc.getTextureManager().register(out[f], new DynamicTexture(img));
            }
            frames = out;
        } catch (Exception e) {
            failed = true;
            PohCore.LOG.warn("[pohsmp] barrier cracks texture: {}", e.toString());
        }
    }

    /** Dropped with the resources (F3+T): made again on next use. */
    public static void reset() {
        frames = null;
        failed = false;
    }
}
