package ru.pohsmp.core.trophy;

import net.minecraft.resources.ResourceLocation;
import ru.pohsmp.core.PohCore;
import software.bernie.geckolib.cache.GeckoLibCache;

/**
 * Where the visual helpers put the T35 files (one model per set, each slot shows its own bones, like the Silent Witch outfit):
 * geo/armor/&lt;id&gt;.geo.json, textures/armor/&lt;id&gt;.png (+ optional _glowmask.png), animations/armor/&lt;id&gt;.animation.json
 * (idle / walk / run / cast). Until the files exist nothing breaks: the sets look like netherite, the mantle and mask are not drawn.
 * GeckoLib's caches are filled on the client only, so these answer false on a server (they are asked on the client).
 */
public final class TrophyAssets {
    private TrophyAssets() {}

    public static ResourceLocation geo(String id) {
        return new ResourceLocation(PohCore.MODID, "geo/armor/" + id + ".geo.json");
    }

    public static ResourceLocation texture(String id) {
        return new ResourceLocation(PohCore.MODID, "textures/armor/" + id + ".png");
    }

    public static ResourceLocation glow(String id) {
        return new ResourceLocation(PohCore.MODID, "textures/armor/" + id + "_glowmask.png");
    }

    public static ResourceLocation anim(String id) {
        return new ResourceLocation(PohCore.MODID, "animations/armor/" + id + ".animation.json");
    }

    public static boolean hasGeo(String id) {
        return GeckoLibCache.getBakedModels().containsKey(geo(id));
    }

    public static boolean hasAnim(String id) {
        return GeckoLibCache.getBakedAnimations().containsKey(anim(id));
    }

    /** The texture the vanilla armor layer is given: ours once the model exists, netherite until then. */
    public static String armorTexture(String id, boolean legs) {
        if (hasGeo(id)) return texture(id).toString();
        return "minecraft:textures/models/armor/netherite_layer_" + (legs ? 2 : 1) + ".png";
    }
}
