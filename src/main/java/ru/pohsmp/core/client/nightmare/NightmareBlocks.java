package ru.pohsmp.core.client.nightmare;

import com.mojang.blaze3d.platform.NativeImage;
import com.mojang.blaze3d.systems.RenderSystem;
import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.texture.MipmapGenerator;
import net.minecraft.client.renderer.texture.TextureAtlas;
import net.minecraft.client.renderer.texture.TextureAtlasSprite;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.inventory.InventoryMenu;
import ru.pohsmp.core.PohCore;

/**
 * T25, the world of stage 3: the helper's rotten textures (textures/block/nightmare, already coloured) put over the vanilla sprites
 * in the block atlas of this client only - no resource reload, no chunk changes; every mip level written, and the vanilla sprite
 * uploaded back when the nightmare is over. Water stays as it is (animated; it turns to ink by its tint).
 */
public final class NightmareBlocks {
    private NightmareBlocks() {}

    /** vanilla sprite -> our texture ("" = fully transparent: the grass side's green overlay goes) */
    private static final Map<String, String> SWAP = new LinkedHashMap<>();

    static {
        SWAP.put("block/grass_block_top", "grass_block_top");
        SWAP.put("block/grass_block_side", "grass_block_side");
        SWAP.put("block/grass_block_side_overlay", "");
        for (String w : new String[] {"oak", "birch", "spruce", "jungle", "acacia", "dark_oak", "mangrove", "cherry"}) {
            SWAP.put("block/" + w + "_leaves", "leaves_dead");
            SWAP.put("block/" + w + "_log", "log_dead");
        }
    }

    private static boolean applied;

    public static boolean applied() {
        return applied;
    }

    /** Puts the rotten sprites in (on) or the vanilla ones back (off). Render thread. */
    public static void set(boolean on) {
        if (on == applied && !on) return;
        Minecraft mc = Minecraft.getInstance();
        TextureAtlas atlas;
        try {
            atlas = mc.getModelManager().getAtlas(InventoryMenu.BLOCK_ATLAS);
        } catch (RuntimeException e) {
            return;
        }
        int mips = Math.max(0, mc.options.mipmapLevels().get());
        RenderSystem.bindTexture(atlas.getId());
        Map<String, NativeImage[]> cache = new java.util.HashMap<>();
        for (var en : SWAP.entrySet()) {
            TextureAtlasSprite s = atlas.getSprite(new ResourceLocation("minecraft", en.getKey()));
            if (s == null || s.contents().name().getPath().equals("missingno")) continue;
            try {
                if (!on) {
                    s.uploadFirstFrame();
                    continue;
                }
                int w = s.contents().width(), h = s.contents().height();
                NativeImage[] lv = cache.computeIfAbsent(en.getValue() + "@" + w + "x" + h, k -> load(en.getValue(), w, h, mips));
                if (lv == null) continue;
                for (int l = 0; l < lv.length; l++) lv[l].upload(l, s.getX() >> l, s.getY() >> l, false);
            } catch (RuntimeException ex) {
                PohCore.LOG.warn("[pohsmp] nightmare sprite {} failed: {}", en.getKey(), ex.toString());
            }
        }
        for (NativeImage[] lv : cache.values()) if (lv != null) for (NativeImage i : lv) i.close();
        applied = on;
    }

    /** Our texture at the sprite's size (scaled by nearest pixel if a resource pack made the sprite bigger) with its mip levels. */
    private static NativeImage[] load(String name, int w, int h, int mips) {
        NativeImage img = new NativeImage(w, h, true);
        if (name.isEmpty()) img.fillRect(0, 0, w, h, 0);
        else {
            var res = Minecraft.getInstance().getResourceManager().getResource(new ResourceLocation(PohCore.MODID, "textures/block/nightmare/" + name + ".png"));
            if (res.isEmpty()) {
                img.close();
                return null;
            }
            try (var in = res.get().open(); NativeImage src = NativeImage.read(in)) {
                for (int y = 0; y < h; y++)
                    for (int x = 0; x < w; x++) img.setPixelRGBA(x, y, src.getPixelRGBA(x * src.getWidth() / w, y * src.getHeight() / h));
            } catch (java.io.IOException e) {
                img.close();
                return null;
            }
        }
        return MipmapGenerator.generateMipLevels(new NativeImage[] {img}, mips);
    }
}
